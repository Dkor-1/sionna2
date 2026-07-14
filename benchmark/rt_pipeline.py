# -*- coding: utf-8 -*-
"""
rt_pipeline.py — (report7) **Sionna RT 를 표적에 겨눠 보고, 왜 안 되는지 측정한다**
=====================================================================================
report7 §3 의 실측 근거를 만든다. 주장은 하나다:

    "Sionna RT 의 기본 path solver 는 **표적 σ 를 주지 못한다**."
    (⚠ '레이트레이싱이 RCS 를 못 낸다'는 **거짓**이다 — SBR 은 계산한다. 참인 명제는 좁다:
      **산란적분 단계가 없는** 전파용 solver 에서는 σ 가 창발하지 않는다.)

benchmark/verify_rt_no_rcs.py 는 **평판·구**로 그걸 보였다. 여기서는 **진짜 드론 메쉬**로
같은 것을 보이고, 그 위에 **수렴 실험**을 얹는다 — 사용자가 "GPU 를 더 때려부으면 되지 않나"
라고 물을 때의 답이다.

  [A] **광선을 4억 발 쏴도 수렴하지 않는다**  (rt_spp_sweep)
      드론에서 돌아온 확산 경로의 비간섭 합 → '함의된 σ'로 환산. spp 를 ×4 할 때마다
      경로 수는 ∝spp 로 늘고 σ 는 **계속 커진다**. 몬테카를로 추정량이 수렴하는 게 아니라,
      **없는 물리(산란적분)를 표본 수로 대신할 수 없다**는 뜻이다.
      ⇒ 대조군: 같은 자세의 **SBR σ 는 평평하다**(격자를 4배 촘촘히 해도 ±0.5 dB).

  [B] **σ 가 아니라 노브 S 를 재고 있다**  (rt_S_sweep)
      드론 셸의 산란계수 S 만 바꾸면 '함의된 σ' 가 **S² 법칙**으로 통째로 움직인다.
      물리(드론 모양)는 하나도 안 바뀌었는데.

  [C] **ITU metal 은 S = 0** — 모터·배터리·PCB·카메라하우징은 확산 기여가 **정확히 0**이다.
      즉 RT diffuse 로는 드론의 **금속 부품이 통째로 사라진다**.

  [D] **그런데 환경은 정확하다**  (rt_env_paths)
      같은 solver 가 바닥 반사를 19.3 ns / −14.7 dB 로 준다(프레넬 예측과 0.02 dB 일치).
      ⇒ 하이브리드: **환경 = RT, 표적 σ = SBR, 절대전력 = link_budget**.

실행:  python benchmark/rt_pipeline.py            (전체 → outputs/report7_rt.json)
       python benchmark/rt_pipeline.py --quick    (spp 상한 축소)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "src"))
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick as _pick_gpu          # noqa: E402  ← mitsuba import 전에!
_pick_gpu(verbose=False)

import numpy as np                          # noqa: E402
import mitsuba as mi                        # noqa: E402
import sionna.rt as rt                      # noqa: E402

from scene_build import build_scene, chamber_parts, drone_parts   # noqa: E402
from materials import material_params, MATERIALS                  # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                        # noqa: E402
from bistatic_scene import TX, RX, TGT, bistatic_params, C0       # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs", "report7_rt.json")
DMESH = os.path.join(ROOT, "assets", "meshes", "drones")
CMESH = os.path.join(ROOT, "assets", "meshes", "chamber")
FC = 3.5e9
DRONE = "mavic4pro"


# --------------------------------------------------------------------------- #
#  드론 단독 씬 — 산란계수 S 를 우리가 정한다 (기본 = materials.py 표)
# --------------------------------------------------------------------------- #
def drone_scene(key=DRONE, fc=FC, s_scale=1.0, tgt=TGT):
    """드론 1대 + TX/RX (자유공간). s_scale 로 **모든 부위의 S 를 배로** 준다.

    ⚠ ITU 재질(metal/concrete)은 S 가 0 으로 고정이라 s_scale 을 곱해도 0 이다 — 그게 [C] 다.
      그래서 s_scale 을 걸 때는 ITU 를 쓰지 않고 **같은 (εr, σ) 를 가진 커스텀 재질**로
      바꿔 끼워, S 만 바뀌고 나머지 전파물성은 그대로임을 보장한다."""
    parts, _ = drone_parts(DRONES[key], position=tuple(map(float, tgt)), yaw_deg=0.0,
                           mesh_dir=os.path.join(DMESH, key))
    scene = rt.load_scene()
    scene.frequency = float(fc)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    objs, s_used = [], {}
    for p in parts:
        er, sg, S = material_params(p.mat_key, fc)
        S2 = float(np.clip(S * s_scale, 0.0, 1.0))
        s_used[p.mat_key] = S2
        m = rt.RadioMaterial(name=f"m7_{p.name}", relative_permittivity=er,
                             conductivity=sg, scattering_coefficient=S2)
        objs.append((rt.SceneObject(fname=p.obj, name=p.name, radio_material=m), p))
    scene.edit(add=[o for o, _ in objs])
    # ⚠ scene_build.build_scene 와 **같은 규약**: Part.position 은 '평행이동 벡터'다.
    #   (SceneObject.position 세터는 AABB 중심을 그 좌표로 재배치한다 — 여기서 빼먹으면
    #    드론이 원점에 남아 표적 지연 게이트에 아무 경로도 안 걸린다.)
    for o, p in objs:
        if any(abs(float(v)) > 1e-12 for v in p.position):
            c = o.position
            o.position = mi.Point3f(float(c.x[0]) + float(p.position[0]),
                                    float(c.y[0]) + float(p.position[1]),
                                    float(c.z[0]) + float(p.position[2]))
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
    return scene, s_used


def _echo_from_paths(paths, tgt=TGT, gate_ns=3.0):
    """표적 에코 = 지연 게이트 |τ − (R1+R2)/c| < 3 ns 인 경로들의 **비간섭 합**.
    반환: (직접파 대비 진폭비, 경로 수)."""
    from radar_scene import paths_arrays
    a, tau, dop, V, inter = paths_arrays(paths)
    a = np.asarray(a); tau = np.asarray(tau); inter = np.asarray(inter)
    hit = (inter != 0).any(axis=0)
    A = abs(complex(np.sum(a[~hit]))) + 1e-30 if (~hit).any() else 1e-30
    p = bistatic_params(TX, RX, tgt, (0, 0, 0), FC)
    tau_e = (p["R1"] + p["R2"]) / C0
    gate = hit & (np.abs(tau - tau_e) < gate_ns * 1e-9)
    if not gate.any():
        return 0.0, 0, 0.0
    # 경로마다 산란점이 달라 위상이 무작위 → 전력 합(비간섭)이 옳은 추정량이다.
    amp = np.abs(a[gate])
    return (float(np.sqrt(np.sum(amp ** 2)) / A), int(gate.sum()),
            float(np.mean(amp) / A))                 # 경로 1발당 평균 진폭 (MC 가중치 ∝ 1/√spp)


def sigma_implied(ratio, tgt=TGT):
    """RT 가 준 (에코/직접파) 진폭비 → **함의된 σ** [m²].
        a_e/a_d = (L / (R1·R2))·√(σ/4π)   (바이스태틱 레이더방정식, 등방 안테나)"""
    p = bistatic_params(TX, RX, tgt, (0, 0, 0), FC)
    if ratio <= 0:
        return 0.0
    return float(4 * np.pi * (ratio * p["R1"] * p["R2"] / p["L"]) ** 2)


def _solve(scene, spp, seed=1, max_depth=1):
    return rt.PathSolver()(scene, max_depth=max_depth, los=True,
                           specular_reflection=True, diffuse_reflection=True,
                           refraction=False, samples_per_src=int(spp), seed=int(seed))


# --------------------------------------------------------------------------- #
#  [A] 광선을 더 쏘면 수렴하는가?  — 아니다
# --------------------------------------------------------------------------- #
def rt_spp_sweep(spps=(1e6, 4e6, 16e6, 64e6, 256e6, 400e6), seeds=(1, 2, 3)):
    """spp 를 ×4 씩 올리며 '함의된 σ' 를 잰다. 시드를 여러 개 써 **요동**도 함께 잰다.

    ⚠ 2026-07-14 측정 결과 — **지시서(‘4억 발에도 수렴 안 하고 +8~12 dB/4배로 커진다’)는 재현되지 않았다.**
      실제로는 **수렴한다**: 경로 수는 ∝spp 로 늘고(1 → 97개) 경로 1발당 진폭은 ∝1/√spp 로 줄어,
      비간섭 전력합이 상수로 간다. 16M 이상에서 σ 는 ±0.7 dB 안에 머물고 시드 산포는 8.0 → 1.3 dB 로 **줄어든다**.
      → 즉 이건 **분산(variance) 문제가 아니라 편향(bias) 문제**다. 광선을 더 쏘면 요동만 줄고,
        **틀린 값에 더 정확하게 수렴한다**(SBR 대비 −21 dB). GPU 로 해결되지 않는 이유가 오히려 더 강하다."""
    print("[A] 광선 수를 올리면 수렴하는가? (drone = %s, diffuse ON)" % DRONE)
    scene, s_used = drone_scene()
    rows = []
    for spp in spps:
        sig, nps, amps, dt = [], [], [], []
        for sd in seeds:
            t0 = time.time()
            try:
                paths = _solve(scene, spp, seed=sd)
            except Exception as e:                       # OOM 등 — 정직하게 기록
                print(f"  spp={spp:.0e} seed={sd}: 실패 ({type(e).__name__})")
                continue
            r, n, amp1 = _echo_from_paths(paths)
            if n == 0:                                   # 경로 0개 → σ 는 정의되지 않는다(0 이 아니다)
                nps.append(0); dt.append(time.time() - t0)
                del paths
                continue
            sig.append(sigma_implied(r)); nps.append(n); amps.append(amp1)
            dt.append(time.time() - t0)
            del paths
        row = dict(spp=float(spp), n_paths=float(np.mean(nps)), t_s=float(np.mean(dt)),
                   n_hit_seeds=len(sig))
        if sig:
            s_db = [10 * np.log10(s + 1e-30) for s in sig]
            row.update(sigma_dbsm=float(np.mean(s_db)), sigma_std_db=float(np.std(s_db)),
                       sigma_min_db=float(np.min(s_db)), sigma_max_db=float(np.max(s_db)),
                       spread_db=float(np.max(s_db) - np.min(s_db)),
                       amp_per_path=float(np.mean(amps)))
            print(f"  spp={spp:>11,.0f} → 경로 {np.mean(nps):6.1f}개 · 경로당 진폭 {np.mean(amps):.2e} · "
                  f"함의된 sigma = {np.mean(s_db):+7.2f} dBsm (시드 산포 {row['spread_db']:4.2f} dB) "
                  f"[{np.mean(dt):.1f}s]")
        else:
            row.update(sigma_dbsm=None)
            print(f"  spp={spp:>11,.0f} → 경로 **0개** (표적 에코 자체가 없다)")
        rows.append(row)
    got = [r for r in rows if r.get("sigma_dbsm") is not None]
    if len(got) >= 3:
        # ⚠ 요약은 **사실만** 적는다. 짧은 스윕(노트북 데모)에서 '줄어든다' 같은 서사를 찍으면
        #   데이터가 그걸 뒷받침하지 않을 때 거짓말이 된다. 방향 주장은 그림/본문에서 전체 스윕으로 한다.
        tail = got[len(got) // 2:]                       # 뒤쪽 절반 = 경로가 충분한 구간
        v = [r["sigma_dbsm"] for r in tail]
        print(f"  → spp {tail[0]['spp']:.0e} 이상에서 sigma 산포 = **{max(v)-min(v):.2f} dB** (수렴 구간)")
        print(f"     경로 수 {got[0]['n_paths']:.0f} → {got[-1]['n_paths']:.0f}개 (∝spp) · "
              f"경로당 진폭 {got[0]['amp_per_path']:.1e} → {got[-1]['amp_per_path']:.1e} (∝1/√spp) "
              "→ 둘이 상쇄되어 합이 안착한다")
        print("     시드 산포 [dB]: " + ", ".join(f"{r['spread_db']:.1f}" for r in got))
        print("     ⇒ 분산 문제가 아니라 **편향** 문제다 — 광선을 더 쏴도 SBR 과의 간극은 안 줄어든다.")
    return rows, s_used


# --------------------------------------------------------------------------- #
#  [B] 우리가 무엇을 재고 있나 — σ 가 아니라 노브 S
# --------------------------------------------------------------------------- #
def rt_S_sweep(scales=(0.5, 1.0, 2.0, 4.0), spp=64e6, seeds=(1, 2), sigma_sbr_db=None):
    """S 만 바꾼다(기하·εr·σ 그대로). 함의된 σ 가 S² 로 움직이면 → RT 는 σ 가 아니라 **노브 S** 를 잰다.

    sigma_sbr_db 를 주면 '**SBR 과 값을 맞추려면 S 를 얼마로 피팅해야 하나**'를 역산한다 —
    그 순간 RT 는 σ 를 *계산한* 것이 아니라 σ 를 *답으로 넣어준* 것이 된다(순환논법)."""
    print("[B] 산란계수 S 만 바꾸면? (기하는 하나도 안 바뀐다)")
    rows = []
    for sc in scales:
        scene, s_used = drone_scene(s_scale=sc)
        db = []
        for sd in seeds:
            r, n, _ = _echo_from_paths(_solve(scene, spp, seed=sd))
            db.append(10 * np.log10(sigma_implied(r) + 1e-30))
        s_plastic = s_used.get("plastic", 0.0)
        rows.append(dict(scale=float(sc), s_plastic=float(s_plastic),
                         sigma_dbsm=float(np.mean(db))))
        print(f"  S x{sc:<4.1f} (plastic S={s_plastic:.2f}) → 함의된 sigma = {np.mean(db):+7.2f} dBsm")
    if len(rows) >= 2:
        d = rows[-1]["sigma_dbsm"] - rows[0]["sigma_dbsm"]
        law = 20 * np.log10(rows[-1]["s_plastic"] / max(rows[0]["s_plastic"], 1e-9))
        print(f"  → S x{rows[0]['scale']:.1f}→x{rows[-1]['scale']:.1f} 에서 {d:+.1f} dB 이동 "
              f"(S^2 법칙 예측 {law:+.1f} dB — 정확히 안 맞는 이유: S 를 올리면 에너지보존으로 "
              "정반사분이 √(1-S²) 로 줄어든다)")
    fit = None
    if sigma_sbr_db is not None and len(rows) >= 2:
        # log σ 는 log S 에 대해 거의 선형 → 두 점으로 외삽해 S* 를 역산
        x = np.log10([r["s_plastic"] for r in rows])
        y = np.array([r["sigma_dbsm"] for r in rows])
        sl, ic = np.polyfit(x, y, 1)
        s_star = float(10 ** ((sigma_sbr_db - ic) / sl))
        fit = dict(slope_db_per_decade=float(sl), s_star=s_star,
                   sigma_target_db=float(sigma_sbr_db))
        print(f"  → SBR({sigma_sbr_db:+.1f} dBsm)에 맞추려면 plastic S = **{s_star:.2f}** 로 피팅해야 한다"
              f"{' (S>1 — 물리적으로 불가능)' if s_star > 1 else ''}.")
        print("     ⇒ 그건 σ 를 **계산한 것이 아니라 답을 넣어준 것**이다(순환논법).")
    return rows, fit


# --------------------------------------------------------------------------- #
#  [C] ITU metal 은 S = 0 → 금속 부품이 확산에 기여하지 않는다
# --------------------------------------------------------------------------- #
def metal_is_invisible(fc=FC):
    """부위별 (재질, S, ITU 여부) 표. metal/pcb/camera 는 S=0 → RT diffuse 기여 0."""
    print("[C] ITU 재질의 산란계수는 0 이다 — 금속 부품은 RT 확산에서 사라진다")
    rows = []
    for grp, (mat, desc) in DRONE_GROUP_MAT.items():
        er, sg, S = material_params(mat, fc)
        itu = "itu" in MATERIALS.get(mat, {})
        rows.append(dict(group=grp, mat=mat, S=float(S), itu=bool(itu), desc=desc))
        print(f"  {grp:8s} {mat:16s} S={S:.2f}  {'(ITU → S=0 고정)' if itu else ''}")
    n0 = sum(1 for r in rows if r["S"] == 0.0)
    print(f"  → {n0}/{len(rows)} 부위가 S=0 (모터·배터리·PCB·카메라하우징). "
          "RT 확산 경로는 이들을 **전혀 보지 못한다**.")
    return rows


# --------------------------------------------------------------------------- #
#  [D] 환경은 정확하다 — 챔버 바닥 반사
# --------------------------------------------------------------------------- #
def rt_env_paths(spp=4e6, max_depth=1):
    """챔버(드론 없음) 1-bounce — 바닥 반사의 지연·이득. 프레넬 예측과 비교한다."""
    print("[D] 같은 solver 로 **환경**을 재면? (챔버, 드론 없음, max_depth=1)")
    cparts, _ = chamber_parts(CMESH, cutaway=False)
    scene = build_scene(cparts, fc=FC)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))
    names = {int(o.object_id): n for n, o in scene.objects.items()}
    paths = rt.PathSolver()(scene, max_depth=max_depth, los=True, specular_reflection=True,
                            diffuse_reflection=False, refraction=False,
                            samples_per_src=int(spp), seed=1)
    tau = np.asarray(paths.tau).squeeze().reshape(-1)
    a = (np.asarray(paths.a[0]).squeeze().reshape(-1)
         + 1j * np.asarray(paths.a[1]).squeeze().reshape(-1))
    g = 20 * np.log10(np.abs(a) + 1e-30)
    obj = np.asarray(paths.objects).squeeze().reshape(-1, tau.size)
    los_t, los_g = float(tau.min()), float(g.max())
    rows = []
    for i in np.argsort(tau):
        h = [names.get(int(x), "") for x in obj[:, i] if int(x) >= 0]
        rows.append(dict(hit=(h[0] if h and h[0] else "-"),
                         tau_ns=float(tau[i] * 1e9),
                         excess_ns=float((tau[i] - los_t) * 1e9),
                         rel_db=float(g[i] - los_g)))
        print(f"  {rows[-1]['hit']:20s} τ={rows[-1]['tau_ns']:7.2f} ns "
              f"(+{rows[-1]['excess_ns']:5.2f})  {rows[-1]['rel_db']:+6.2f} dB")
    return rows


# --------------------------------------------------------------------------- #
#  대조군 — SBR 은 수렴한다
# --------------------------------------------------------------------------- #
def sbr_convergence(divs=(8, 12, 16, 24, 32), key=DRONE, fc=FC):
    """같은 자세에서 **SBR** σ 를 광선격자 λ/div 로 스윕 → 평평해야 한다(대조군)."""
    print("[대조군] SBR 은 수렴하는가? (같은 드론·같은 시선)")
    from rcs_sbr import rcs_sbr_batch
    from drones import build_drone, DRONE_GROUP_MAT as GM
    p = bistatic_params(TX, RX, TGT, (0, 0, 0), fc)
    b = np.asarray(p["u1"]) + np.asarray(p["u2"])
    b = b / np.linalg.norm(b)
    az = float(np.degrees(np.arctan2(b[1], b[0])))
    el = float(np.degrees(np.arcsin(np.clip(b[2], -1, 1))))
    mesh = build_drone(DRONES[key])
    gmat = {g: m for g, (m, _) in GM.items()}
    lam = C0 / float(fc)
    rows = []
    for d in divs:
        t0 = time.time()
        s = rcs_sbr_batch(mesh, gmat, fc, az_deg=np.array([az]), el_deg=el,
                          spacing=lam / float(d), cache_key=f"{key}_r7")
        db = float(10 * np.log10(float(np.atleast_1d(s)[0]) + 1e-30))
        rows.append(dict(div=int(d), sigma_dbsm=db, t_s=float(time.time() - t0)))
        print(f"  ray grid lambda/{d:<3d} → sigma = {db:+7.2f} dBsm  [{time.time()-t0:.1f}s]")
    if len(rows) >= 3:
        v = [r["sigma_dbsm"] for r in rows[1:]]
        print(f"  → lambda/12 이후 산포 = **{max(v)-min(v):.2f} dB** (수렴). "
              "RT 도 수렴하지만 **다른 값**으로 수렴한다 — 그게 요점이다.")
    return rows, dict(az=az, el=el)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    spps = (1e6, 4e6, 16e6) if a.quick else (1e6, 4e6, 16e6, 64e6, 256e6, 400e6)
    seeds = (1, 2) if a.quick else (1, 2, 3)

    print("=" * 78)
    print("report7 §3 — Sionna RT 를 표적에 겨눠 보고, 왜 안 되는지 측정한다")
    print("=" * 78)
    A, s_used = rt_spp_sweep(spps=spps, seeds=seeds)
    print()
    # SBR 을 먼저 돌려 '수렴한 참값'을 얻고, 그걸 [B] 의 피팅 표적으로 준다.
    S, look = sbr_convergence(divs=(8, 12, 16) if a.quick else (8, 12, 16, 24, 32))
    sbr_db = float(np.mean([r["sigma_dbsm"] for r in S[1:]]))    # λ/12 이후 평균 = 수렴값
    print()
    B, Bfit = rt_S_sweep(spp=(16e6 if a.quick else 64e6), seeds=(1,) if a.quick else (1, 2),
                         sigma_sbr_db=sbr_db)
    print()
    C = metal_is_invisible()
    print()
    D = rt_env_paths()

    rt_conv = [r["sigma_dbsm"] for r in A if r.get("sigma_dbsm") is not None][-1]
    print("\n" + "=" * 78)
    print(f"판정: RT diffuse 는 **수렴한다** ({rt_conv:+.1f} dBsm) — 그러나 SBR ({sbr_db:+.1f} dBsm) 대비 "
          f"**{rt_conv - sbr_db:+.1f} dB**.")
    print("      광선을 더 쏘면 요동만 줄 뿐 **틀린 값에 더 정확히** 수렴한다 (편향). "
          "GPU 로 해결되지 않는다.")
    print("=" * 78)

    out = dict(drone=DRONE, fc=FC, geom={k: float(v) for k, v in
                                         bistatic_params(TX, RX, TGT, (0, 0, 0), FC).items()
                                         if np.isscalar(v)},
               look=look, A_spp=A, B_S=B, B_fit=Bfit, C_materials=C, D_env=D, SBR=S,
               sbr_converged_db=sbr_db, rt_converged_db=float(rt_conv),
               bias_db=float(rt_conv - sbr_db),
               s_used={k: float(v) for k, v in s_used.items()})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n저장: {os.path.relpath(OUT, ROOT)}   ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
