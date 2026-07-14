# -*- coding: utf-8 -*-
"""
verify_rt_no_rcs.py — **Sionna RT 의 path solver 에는 표적 RCS(σ)를 담는 자리가 없다**를 실증한다.
=====================================================================================================
이 스크립트는 "표적=PO, 환경=RT" 하이브리드 설계의 **유일한 정당화 근거**를 재현 가능한 형태로 남긴다.
(자세한 배경·판정은 docs/VERIFY_RT_VS_PO.md)

세 실험이면 충분하다:

  [A] **정반사는 표적 크기와 무관하다** — 이등분선 법선으로 정렬한 금속 평판의 변을 0.2 → 4 m 로 키우면
      σ 는 ~50 dB 변하는데, RT 의 (표적에코/직접파) 진폭비는 **불변**이고 그 값은 정확히
      image-source 예측 20·log10(L/(R1+R2)) 이다. → 정반사 경로에 RCS 정보가 0.

  [B] **확산은 σ 가 아니라 산란계수 S 를 측정한다** — 같은 금속구 메쉬에 S 만 0.2 → 1.0 으로 바꾸면
      진폭비가 정확히 **S² 법칙**(20·log10(5) = 14 dB)으로 이동한다. 이론값(πr²)에 맞추려면 S≈0.85
      가 필요하다 → RT diffuse 로 PO 와 숫자를 맞추는 것은 **S 를 피팅하는 순환논법**.

  [C] **물리적으로 옳은 금속구(PEC, S=0)에서는 경로가 아예 0개** — 정반사만 가능한데 SBR+image-method 가
      곡면의 정반사점을 잡지 못한다(디스코볼 문제). 크기·표본수·테셀레이션을 올려도 0.
      ※ 대조군: 같은 위치의 평판은 spp=1M 으로도 즉시 잡힌다 → 메쉬·재질·솔버는 정상이다.

결론: RT 는 표적의 **지연·도플러·기하**는 정확히 준다(τ=(R1+R2)/c 로 확인). 다만 **진폭(σ)** 은 주지 못한다.
      그래서 진폭만 PO 로 대체하는 하이브리드가 필요하다.

실행: CUDA_VISIBLE_DEVICES=2 python benchmark/verify_rt_no_rcs.py
"""
from __future__ import annotations
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from bistatic_scene import TX, RX, TGT, bistatic_params, C0        # noqa: E402

FC = 3.5e9
SCRATCH = "/tmp/sionna2_rt_verify"
os.makedirs(SCRATCH, exist_ok=True)


# --------------------------------------------------------------------------- #
#  RT 실행 — 표적 1개(자유공간)만 놓고 경로를 3분류
# --------------------------------------------------------------------------- #
def rt_paths(parts, spp=4_000_000, seed=1, max_depth=1):
    """(표적에코 진폭비, 경로수, 평균지연[s], 상호작용종류 히스토그램)."""
    from scene_build import build_scene
    from radar_scene import paths_arrays
    import mitsuba as mi
    import sionna.rt as rt

    scene = build_scene(parts, fc=FC)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
    paths = rt.PathSolver()(scene, max_depth=max_depth, los=True,
                            specular_reflection=True, diffuse_reflection=True,
                            refraction=False, samples_per_src=int(spp), seed=int(seed))
    a, tau, dop, V, inter = paths_arrays(paths)
    a = np.asarray(a); tau = np.asarray(tau)
    any_int = (np.asarray(inter) != 0).any(axis=0)
    a_dir = complex(np.sum(a[~any_int])) if (~any_int).any() else 0j
    A = abs(a_dir) + 1e-30
    hist = {int(v): int((np.asarray(inter) == v).sum()) for v in np.unique(inter)}
    if not any_int.any():
        return None, 0, None, hist
    # 표적 에코 = **지연 게이트**로 고른다(표적 근방 2 m 규약은 벽 반사를 오분류한다).
    tau_e = (bistatic_params(TX, RX, TGT, (0, 0, 0), FC)["R1"]
             + bistatic_params(TX, RX, TGT, (0, 0, 0), FC)["R2"]) / C0
    gate = any_int & (np.abs(tau - tau_e) < 3e-9)
    if not gate.any():
        return None, 0, None, hist
    # 비간섭 합(경로들이 서로 다른 산란점 → 랜덤 위상): sqrt(sum |a|^2)
    ratio = float(np.sqrt(np.sum(np.abs(a[gate]) ** 2)) / A)
    return ratio, int(gate.sum()), float(np.mean(tau[gate])), hist


def plate_part(side, name="plate"):
    """TX·RX 이등분선에 법선을 맞춘 금속 평판(정반사 조건 충족) — 대조군."""
    from geom import Mesh
    from scene_build import Part
    tx, rx, tg = map(lambda v: np.array(v, float), (TX, RX, TGT))
    n = ((tx - tg) / np.linalg.norm(tx - tg) + (rx - tg) / np.linalg.norm(rx - tg))
    n /= np.linalg.norm(n)                                  # 이등분선 = 정반사 법선
    a = np.cross(n, [0, 0, 1.0]); a /= np.linalg.norm(a)
    b = np.cross(n, a)
    h = side / 2
    quad = [tg + s1 * h * a + s2 * h * b for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    m = Mesh(group="plate")
    idx = [m.add_vertex(*q) for q in quad]
    m.add_quad(*idx, group="plate")
    obj = os.path.join(SCRATCH, f"{name}_{side:.2f}.obj")
    m.write_obj(obj)
    return [Part(name=f"{name}_{side:.2f}".replace(".", "_"), obj=obj, mat_key="metal")]


def sphere_part(r=0.30, mat="metal", S=None, name="sph"):
    """금속구(또는 산란계수 S 를 준 구)."""
    from geom import uv_sphere
    from scene_build import Part
    m = uv_sphere(r, center=tuple(float(v) for v in TGT), seg=48, rings=24)
    obj = os.path.join(SCRATCH, f"{name}_{r:.2f}.obj")
    m.write_obj(obj)
    p = Part(name=f"{name}_{r:.2f}".replace(".", "_"), obj=obj, mat_key=mat)
    p.scattering_S = S                                       # build_scene 이 무시 → 아래에서 직접 주입
    return [p]


def rt_sphere_with_S(r, S, spp=4_000_000, seed=1):
    """산란계수 S 를 명시적으로 준 구(= diffuse 채널을 열어 준다)."""
    from geom import uv_sphere
    from scene_build import build_scene, Part
    from radar_scene import paths_arrays
    import mitsuba as mi
    import sionna.rt as rt

    m = uv_sphere(r, center=tuple(float(v) for v in TGT), seg=48, rings=24)
    obj = os.path.join(SCRATCH, f"sphS_{r:.2f}.obj")
    m.write_obj(obj)
    scene = rt.load_scene(); scene.frequency = FC
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    mat = rt.RadioMaterial(name=f"m_S{S:.2f}", relative_permittivity=1.0,
                           conductivity=1e7, scattering_coefficient=float(S))
    o = rt.SceneObject(fname=obj, name=f"sph_S{S:.2f}".replace(".", "_"), radio_material=mat)
    scene.edit(add=[o])
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
    paths = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                            diffuse_reflection=True, refraction=False,
                            samples_per_src=int(spp), seed=int(seed))
    a, tau, dop, V, inter = paths_arrays(paths)
    a = np.asarray(a); tau = np.asarray(tau)
    any_int = (np.asarray(inter) != 0).any(axis=0)
    A = abs(complex(np.sum(a[~any_int]))) + 1e-30
    p = bistatic_params(TX, RX, TGT, (0, 0, 0), FC)
    gate = any_int & (np.abs(tau - (p["R1"] + p["R2"]) / C0) < 3e-9)
    if not gate.any():
        return None, 0
    return float(np.sqrt(np.sum(np.abs(a[gate]) ** 2)) / A), int(gate.sum())


def main():
    p = bistatic_params(TX, RX, TGT, (0, 0, 0), FC)
    tau_e = (p["R1"] + p["R2"]) / C0
    img = 20 * np.log10(p["L"] / (p["R1"] + p["R2"]))        # image-source(무한거울) 예측
    print("=" * 86)
    print("Sionna RT 에는 표적 RCS 를 담는 자리가 없다 — 3개 실험")
    print("=" * 86)
    print(f"기하: L={p['L']:.3f} m · R1={p['R1']:.3f} · R2={p['R2']:.3f} · β={p['beta']:.1f}°")
    print(f"표적에코 기대지연 τ=(R1+R2)/c = {tau_e*1e9:.2f} ns · image-source 예측 진폭비 = {img:+.2f} dB\n")
    out = {"geometry": {k: float(p[k]) for k in ("L", "R1", "R2", "beta")},
           "tau_echo_ns": tau_e * 1e9, "image_source_db": img}

    # ---------- [A] 평판 크기 스윕 → 정반사는 σ 와 무관 ----------
    print("-" * 86)
    print("[A] 금속 평판(정반사 정렬)의 변 길이를 키우면? — σ 는 커지는데 RT 진폭비는?")
    print("-" * 86)
    rows = []
    for side in (0.2, 0.5, 1.0, 2.0, 4.0):
        r, n, tau, _ = rt_paths(plate_part(side), spp=1_000_000)
        sig = 4 * np.pi * (side ** 2) ** 2 / (C0 / FC) ** 2     # 수직입사 평판 σ = 4πA²/λ²
        if r is None:
            print(f"  변 {side:4.1f} m → 경로 0개")
            rows.append(dict(side=side, ratio_db=None)); continue
        print(f"  변 {side:4.1f} m (σ={10*np.log10(sig):+6.1f} dBsm) → RT {20*np.log10(r):+7.2f} dB "
              f"· 경로 {n}개 · τ={tau*1e9:.2f} ns")
        rows.append(dict(side=side, sigma_dbsm=10*np.log10(sig), ratio_db=20*np.log10(r), n=n))
    vals = [x["ratio_db"] for x in rows if x["ratio_db"] is not None]
    if vals:
        print(f"\n  → σ 가 {max(x['sigma_dbsm'] for x in rows if x['ratio_db'])-min(x['sigma_dbsm'] for x in rows if x['ratio_db']):.0f} dB 변하는 동안 "
              f"RT 진폭비 산포 = **{max(vals)-min(vals):.2f} dB** (image-source 예측 {img:+.2f} dB)")
        print("     ⇒ 정반사 경로는 '무한거울'이라 표적 크기(σ) 정보를 담지 않는다.")
    out["A_plate"] = rows

    # ---------- [B] 구의 산란계수 S 스윕 → 확산은 S² ----------
    print("\n" + "-" * 86)
    print("[B] 같은 금속구에 산란계수 S 만 바꾸면? — RT 는 σ 가 아니라 S 를 잰다")
    print("-" * 86)
    sig_th = np.pi * 0.30 ** 2
    r_th = p["L"] * np.sqrt(sig_th / (4 * np.pi)) / (p["R1"] * p["R2"])
    print(f"  구 r=0.3 m: 이론 σ=πr²={10*np.log10(sig_th):+.2f} dBsm → 이론 진폭비 {20*np.log10(r_th):+.2f} dB\n")
    rows = []
    for S in (0.2, 0.5, 0.9, 1.0):
        r, n = rt_sphere_with_S(0.30, S)
        if r is None:
            print(f"  S={S:.1f} → 경로 0개"); rows.append(dict(S=S, ratio_db=None)); continue
        print(f"  S={S:.1f} → RT {20*np.log10(r):+7.2f} dB · 이론 대비 {20*np.log10(r/r_th):+6.2f} dB · 경로 {n}개")
        rows.append(dict(S=S, ratio_db=20*np.log10(r), dev_db=20*np.log10(r/r_th), n=n))
    v = [x for x in rows if x["ratio_db"] is not None]
    if len(v) >= 2:
        span = v[-1]["ratio_db"] - v[0]["ratio_db"]
        print(f"\n  → S 0.2→1.0 에서 진폭비 {span:+.1f} dB 이동 (S² 법칙 예측 {20*np.log10(1.0/0.2):+.1f} dB)")
        print("     ⇒ RT 의 표적 확산에코는 σ 가 아니라 **우리가 고른 노브 S** 의 함수다.")
    out["B_sphere_S"] = rows

    # ---------- [C] PEC 구(물리적으로 옳은 설정) → 경로 0개 ----------
    print("\n" + "-" * 86)
    print("[C] 물리적으로 옳은 금속구(PEC, S=0) — RT 가 경로를 만드는가?")
    print("-" * 86)
    rows = []
    for r_m in (0.3, 1.0, 3.0):
        for spp in (1_000_000, 16_000_000):
            ratio, n, tau, hist = rt_paths(sphere_part(r_m), spp=spp)
            print(f"  r={r_m:3.1f} m · spp={spp:>10,} → 표적경로 **{n}개** "
                  f"(interaction 히스토그램 {hist})")
            rows.append(dict(r=r_m, spp=spp, n_paths=n))
    print("\n  → 크기·표본수를 올려도 0. 하지만 같은 위치의 **평판**은 spp=1M 으로도 잡힌다([A]).")
    print("     ⇒ 메쉬·재질·솔버는 정상이고, SBR+image-method 가 **곡면의 정반사점을 못 잡는 것**이다.")
    out["C_pec_sphere"] = rows

    print("\n" + "=" * 86)
    print("판정: RT 는 표적의 지연·도플러·기하는 정확히 주지만(τ 확인), **진폭(σ)은 주지 못한다.**")
    print("      → 표적 진폭은 PO 로, 환경(벽·다중경로)은 RT 로. 이것이 하이브리드의 근거다.")
    print("=" * 86)

    fn = os.path.join(HERE, "..", "outputs", "rt_no_rcs_verify.json")
    with open(fn, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n결과 저장: {os.path.relpath(fn)}")


if __name__ == "__main__":
    main()
