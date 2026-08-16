# -*- coding: utf-8 -*-
"""
mesh_fix_i4_m4_0816.py — 2층 메쉬 수리 **I4(묻힌 캐노피) · m4(x500v2 클램프 관통)** 의
                         수리 전/후를 **같은 PO 커널로 재서** 원장에 싣는다.
==========================================================================================

무엇을 재나 (수리마다 세 수)
  ① 결함의 크기 — 면적[mm²]·면 수·비율[%]
  ② 수리 전후 **σ 변화[dB]** — 우리 커널(rcs_po)로 CPU 에서 직접
  ③ 그 변화가 판정 밴드 밖인가 — 무해 <0.1 / 보임 0.1~1.0 / 결론을 바꿈 >1.0 dB
     (밴드는 기준선 원장이 고른 것을 그대로 쓴다. 새 잣대를 지어내지 않는다.)

두 가지 판을 **따로** 잰다 — 이게 이 스크립트의 핵심 설계다
  · **예측(mask)**  결함 메쉬에서 «수리가 없앨 면» 만 빼고 잰다. 남은 면의 점구름은
                    글자 그대로 같으므로, 차이는 **오직 뺀 면** 때문이다.
  · **실제(rebuild)** 수리를 켜고 메쉬를 다시 지어서 잰다. 불리언이 남은 부분을 다시
                    삼각분할하므로 여기엔 **재이산화**도 섞인다.
  두 값이 같으면 «수리가 의도한 것만 했다» 는 뜻이고, 벌어지면 그 차이가 재이산화의 몫이다.

규약(기준선 원장과 동일)
  3.5 GHz · 점간격 λ/7 · 방위 0~358° 2° 간격 · 고각 0° 와 −30° · 바이스태틱 β=120°(el −30°)
  방위별 dB 는 5G 100 MHz·9점 **대역평균**. (+) = 결함이 σ 를 밝게 만든다(과대계상).
  ⚠ 전부 CPU. GPU 는 안 쓴다(ITU 'metal' 만 Sionna 씬이 필요해 캐시값을 주입한다).

산출: outputs/mesh_layer2_buried_canopy_0816.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ⭐ GPU 금지 규약 — ITU 'metal' 의 (εr, σ) 만 Sionna RT 씬(OptiX)이 필요하다.
#   저장소가 이미 캐시해 둔 3.5 GHz 값을 주입해 CPU 로만 돈다.
#   출처: outputs/mesh_compare_material.json :: materials.metal.{eps_r_5g, sigma_S_per_m_5g}
import materials as _MAT                                                    # noqa: E402
_METAL_5G = (1.0, 1.0e7, 0.0)
for _f in (3.5e9,):
    _MAT._PARAM_CACHE[("metal", round(float(_f)))] = _METAL_5G

from drones import DRONES, build_drone, drone_gamma_map                     # noqa: E402
from geom import Mesh                                                       # noqa: E402
from rcs_po import mesh_to_points, rcs_from_points, C0                      # noqa: E402
import trimesh                                                              # noqa: E402

FC = 3.5e9
LAM = C0 / FC
SPACING = LAM / 7.0
BAND_HZ = 100e6
N_F = 9
FREQS = np.linspace(FC - BAND_HZ / 2, FC + BAND_HZ / 2, N_F)
AZ = np.arange(0.0, 360.0, 2.0)
CONFIGS = (("mono_el0", 0.0, 0.0), ("mono_el-30", -30.0, 0.0), ("bi_b120_el-30", -30.0, 120.0))
OUT = os.path.join(ROOT, "outputs", "mesh_layer2_buried_canopy_0816.json")

BAND = {"무해": 0.1, "보임": 1.0}
SRC_STATE: dict = {}


def verdict(db: float) -> str:
    a = abs(float(db))
    return "무해(<0.1 dB)" if a < BAND["무해"] else ("보임(0.1~1.0 dB)" if a < BAND["보임"]
                                                    else "결론을_바꿈(>1 dB)")


# --------------------------------------------------------------------------- #
#  PO — 출하 커널(rcs_po)과 같은 식. 바이스태틱만 확장(β=0 에서 모노로 되돌아간다)
# --------------------------------------------------------------------------- #
def _look(az_deg, el_deg):
    az = np.radians(np.atleast_1d(az_deg)); el = np.radians(el_deg)
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az),
                     np.full_like(az, np.sin(el))], axis=-1)


def sigma_band(P, N, dA, w, el_deg, beta_deg, chunk=24):
    """대역평균 σ(az)[m²]. beta=0 이면 rcs_po.rcs_from_points 와 같은 식(회귀로 확인)."""
    out = np.zeros(len(AZ))
    for f in FREQS:
        k = 2 * np.pi * f / C0
        s = np.empty(len(AZ))
        for i in range(0, len(AZ), chunk):
            az = AZ[i:i + chunk]
            ui = _look(az - beta_deg / 2.0, el_deg)
            us = _look(az + beta_deg / 2.0, el_deg)
            NI = N @ ui.T
            g = np.where(NI > 0, NI, 0.0)
            if beta_deg:
                g = np.where((N @ us.T) > 0, g, 0.0)
            PH = P @ (ui + us).T
            E = (g * (dA * w)[:, None] * np.exp(1j * k * PH)).sum(axis=0)
            s[i:i + chunk] = (4 * np.pi / (C0 / f) ** 2) * np.abs(E) ** 2
        out += s
    return out / len(FREQS)


def compare(sig_def, sig_rep):
    """결함판 ↔ 수리판. (+) = 결함이 밝다."""
    d = 10 * np.log10(sig_def / np.maximum(sig_rep, 1e-300))
    w3 = np.ones(3) / 3.0                                  # 3° 창 = 방위 3점(2° 간격)
    sd = np.convolve(np.r_[sig_def[-1], sig_def, sig_def[0]], w3, "valid")
    sr = np.convolve(np.r_[sig_rep[-1], sig_rep, sig_rep[0]], w3, "valid")
    d3 = 10 * np.log10(sd / np.maximum(sr, 1e-300))
    i, i3 = int(np.argmax(np.abs(d))), int(np.argmax(np.abs(d3)))
    return dict(
        azimuth_mean_db=round(float(10 * np.log10(sig_def.mean() / sig_rep.mean())), 4),
        worst_az_db=round(float(d[i]), 3), worst_az_deg=float(AZ[i]),
        worst_az_db_3deg_window=round(float(d3[i3]), 3),
        p95_abs_db=round(float(np.percentile(np.abs(d), 95)), 3),
        sigma_with_defect_azmean_dbsm=round(float(10 * np.log10(sig_def.mean())), 3),
        sigma_repaired_azmean_dbsm=round(float(10 * np.log10(sig_rep.mean())), 3))


# --------------------------------------------------------------------------- #
#  메쉬 도우미
# --------------------------------------------------------------------------- #
def points(mesh, spec):
    return mesh_to_points(mesh, SPACING, gamma=drone_gamma_map(spec))


def drop_faces(mesh: Mesh, keep: np.ndarray) -> Mesh:
    """면 부분집합만 남긴 새 Mesh(정점은 그대로 — 점구름의 나머지가 **글자 그대로 같다**)."""
    out = Mesh()
    out.v = list(mesh.v)
    F = np.asarray(mesh.f, int)[keep]
    G = np.asarray(mesh.g)[keep]
    out.f = [tuple(int(x) for x in r) for r in F]
    out.g = list(G.tolist())
    return out


def group_solid(mesh: Mesh, groups) -> trimesh.Trimesh:
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g)
    sel = np.isin(G, list(groups))
    f = F[sel]
    used = np.unique(f)
    remap = {int(o): i for i, o in enumerate(used)}
    return trimesh.Trimesh(vertices=V[used],
                           faces=np.vectorize(remap.get)(f), process=False)


def buried_mask(mesh: Mesh, victim: str, container: str):
    """victim 그룹의 면 중 **중심이 container 솔리드 안**인 것 → (마스크, 면적[mm²], 총면적)."""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g)
    vi = np.where(G == victim)[0]
    tri = V[F[vi]]
    cen = tri.mean(axis=1)
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    cont = group_solid(mesh, [container])
    inside = np.zeros(len(vi), bool)
    for c in cont.split(only_watertight=False):
        if c.is_watertight:
            inside |= c.contains(cen)
    m = np.ones(len(F), bool)
    m[vi[inside]] = False
    return m, float(area[inside].sum()) * 1e6, float(area.sum()) * 1e6, int(inside.sum()), len(vi)


def coplanar_area(mesh: Mesh, ga: str, gb: str, tol_m: float):
    """ga 면 중 gb 표면에서 tol 안에 있는 면적[mm²]·면 수 (동일평면 잣대)."""
    A = group_solid(mesh, [ga]); B = group_solid(mesh, [gb])
    d = np.abs(trimesh.proximity.ProximityQuery(B).signed_distance(A.triangles_center))
    sel = d < tol_m
    return round(float(A.area_faces[sel].sum()) * 1e6, 3), int(sel.sum())


def solid_of(mesh: Mesh, group: str) -> trimesh.Trimesh:
    return group_solid(mesh, [group])


def merge_groups_in_mesh(mesh: Mesh, groups, new_group: str) -> Mesh:
    """⚠**기각된 수리안을 재기 위한 도구**(제품 코드 아님) — 두 그룹을 불리언 합집합해서
    통째로 `new_group` 이름으로 되돌린다. 재질이 하나로 통일되는 것이 요점이다."""
    sol = [solid_of(mesh, g) for g in groups]
    u = trimesh.boolean.union(sol, engine="manifold")
    u.update_faces(u.nondegenerate_faces()); u.merge_vertices()
    trimesh.repair.fix_normals(u)
    G = np.asarray(mesh.g)
    keep = ~np.isin(G, list(groups))
    out = drop_faces(mesh, keep)
    base = len(out.v)
    out.v += [tuple(float(x) for x in v) for v in np.asarray(u.vertices)]
    for f in np.asarray(u.faces, int):
        out.f.append((int(f[0]) + base, int(f[1]) + base, int(f[2]) + base))
        out.g.append(new_group)
    return out


def shift_seat(mesh: Mesh, dz_m: float) -> Mesh:
    """⚠**기각된 수리안**(0.1 mm 띄우기) — x500v2 나일론 시트(accent 중 z 윗면이 카본판
    아랫면과 같은 부품)를 dz 만큼 내린다. 정점을 직접 옮기므로 다른 부품은 안 건드린다."""
    V = np.asarray(mesh.v, float).copy()
    F = np.asarray(mesh.f, int); G = np.asarray(mesh.g)
    acc = np.where(G == "accent")[0]
    A = group_solid(mesh, ["accent"])
    moved = set()
    for c in A.split(only_watertight=False):
        b = c.bounds
        r = np.hypot(c.triangles_center[:, 0], c.triangles_center[:, 1])
        #  시트 = 반경 0.20~0.28 m · 윗면이 카본판 아랫면(z≈+0.004 m)인 부품
        if 0.20 < r.max() < 0.29 and abs(b[1][2] - 0.004) < 5e-4:
            for v in np.asarray(c.vertices):
                moved.add((round(v[0], 12), round(v[1], 12), round(v[2], 12)))
    sel = np.array([(round(v[0], 12), round(v[1], 12), round(v[2], 12)) in moved for v in V])
    #  accent 가 쓰는 정점만 옮긴다(다른 그룹과 좌표가 겹칠 수 있으므로 사용면으로 제한)
    used = np.zeros(len(V), bool); used[np.unique(F[acc])] = True
    sel &= used
    V[sel, 2] -= dz_m
    out = Mesh(); out.v = [tuple(float(x) for x in v) for v in V]
    out.f = [tuple(int(x) for x in r) for r in F]; out.g = list(G.tolist())
    return out, int(sel.sum())


def build_with(spec, ids=()):
    """전역 스위치(MESH_FIX)로 지은 드론 메쉬 — cadkit(i5)·drone_cad(i4·m4)가 **같은 것**을 본다."""
    from geom import set_mesh_fix
    set_mesh_fix(*ids)
    try:
        return build_drone(spec)
    finally:
        set_mesh_fix()


def measure(spec, meshes: dict, ref: str):
    """meshes = {이름: Mesh}. ref 를 «결함판» 으로 두고 나머지와 비교."""
    pts = {k: points(m, spec) for k, m in meshes.items()}
    out = {k: {} for k in meshes if k != ref}
    sig_ref = {}
    for cname, el, beta in CONFIGS:
        P, N, dA, w = pts[ref]
        sig_ref[cname] = sigma_band(P, N, dA, w, el, beta)
        for k in out:
            P, N, dA, w = pts[k]
            out[k][cname] = compare(sig_ref[cname], sigma_band(P, N, dA, w, el, beta))
    return out, {c: round(float(10 * np.log10(s.mean())), 4) for c, s in sig_ref.items()}, \
        {k: len(v[2]) for k, v in pts.items()}


def source_state() -> dict:
    """⭐**트리 지문** — 오늘은 다른 수리자 셋이 같은 파일을 동시에 고치고 있다. 한 번의 실행은
    import 시점의 코드로 끝까지 돌므로 **실행 하나 = 스냅샷 하나**이고, 그 스냅샷을 여기 박아
    둔다. (드론 메쉬 지문도 같이 뜬다 — 절대 σ 가 어느 메쉬의 것인지 나중에 알 수 있도록.)"""
    import hashlib
    out = {}
    for f in ("drone_cad.py", "drones.py", "cadkit.py", "geom.py", "rcs_po.py", "materials.py"):
        p = os.path.join(ROOT, "src", f)
        out[f] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    return out


def mesh_digest(mesh) -> str:
    import hashlib
    v = np.asarray(mesh.v, float); f = np.asarray(mesh.f, np.int64)
    return hashlib.sha256(v.tobytes() + f.tobytes() + "|".join(mesh.g).encode()).hexdigest()[:16]


def area_by_group(mesh: Mesh) -> dict:
    V = np.asarray(mesh.v, float); F = np.asarray(mesh.f, int); G = np.asarray(mesh.g)
    tri = V[F]
    a = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    return {g: round(float(a[G == g].sum()) * 1e6, 3) for g in sorted(set(G.tolist()))}


SHELL = ("mavic4pro", "phantom3", "phantom4", "mini2", "mini5pro", "typhoonh480", "matrice4e")
#  ⚠ mini2 는 감사 I5 의 구멍 때문에 body 가 비수밀이라 i4 가 **단독으로 못 돈다.**
#    그래서 이 기체만 «i5 를 켠 상태» 를 결함판으로 둔다 — 그래야 Δ 가 i4 만의 몫이다.
BASE_IDS = {"mini2": ("i5",)}


def run_i4():
    res = {}
    for key in SHELL:
        t0 = time.time()
        spec = DRONES[key]
        base = BASE_IDS.get(key, ())
        m_def = build_with(spec, base)
        m_rep = build_with(spec, tuple(base) + ("i4",))
        keep, bur_mm2, can_mm2, n_bur, n_can = buried_mask(m_def, "canopy", "body")
        m_pred = drop_faces(m_def, keep)
        cmp_, sig_ref, npts = measure(spec, {"결함": m_def, "예측_묻힌면만_뺌": m_pred,
                                             "실제_수리후": m_rep}, "결함")
        ab, aa = area_by_group(m_def), area_by_group(m_rep)
        #  ⚠ 로그도 **전역 스위치**로 뽑는다 — mini2 는 i5(cadkit)가 같이 켜져 있어야
        #    body 가 수밀이라 불리언이 돈다. 명시 인자만 주면 cadkit 이 그걸 못 본다.
        from drone_cad import build_frame_cad
        from geom import set_mesh_fix
        set_mesh_fix(*(tuple(base) + ("i4",)))
        try:
            log = build_frame_cad(spec).mesh_fix_log.get("i4", {})
        finally:
            set_mesh_fix()
        res[key] = {
            "크기": dict(canopy_면수=n_can, canopy_면적_mm2=round(can_mm2, 3),
                       묻힌_면수=n_bur, 묻힌_면적_mm2=round(bur_mm2, 3),
                       묻힌_비율_pct=round(100 * bur_mm2 / can_mm2, 2),
                       canopy_가_전체면적_pct=round(100 * can_mm2 / sum(ab.values()), 4)),
            "수리_방식": log.get("mode"), "수리_상세": log,
            "면수": dict(전체_전=len(m_def.f), 전체_후=len(m_rep.f),
                       body_전=int((np.asarray(m_def.g) == "body").sum()),
                       body_후=int((np.asarray(m_rep.g) == "body").sum())),
            "그룹면적_mm2": dict(전=ab, 후=aa),
            "σ": cmp_, "σ_결함_azmean_dbsm": sig_ref, "점수": npts,
            "판정": {c: verdict(cmp_["실제_수리후"][c]["azimuth_mean_db"]) for c, _, _ in CONFIGS},
            "메쉬지문": dict(결함=mesh_digest(m_def), 수리후=mesh_digest(m_rep)),
        }
        print(f"  I4 {key:12s} {log.get('mode'):5s} 묻힘 {100*bur_mm2/can_mm2:6.2f} % "
              f"Δazmean {[cmp_['실제_수리후'][c]['azimuth_mean_db'] for c, _, _ in CONFIGS]} "
              f"({time.time()-t0:.0f}s)", flush=True)
    return res


def run_m4():
    key = "x500v2"
    spec = DRONES[key]
    m_def = build_with(spec, ())
    m_rep = build_with(spec, ("m4",))
    keep, bur, tot, n_bur, n_arm = buried_mask(m_def, "arm", "accent")
    m_pred = drop_faces(m_def, keep)
    #  기각안 두 개를 **실제로 지어서** 잰다
    m_union_arm = merge_groups_in_mesh(m_def, ("arm", "accent"), "arm")
    m_union_acc = merge_groups_in_mesh(m_def, ("arm", "accent"), "accent")
    m_gap, n_moved = shift_seat(m_def, 1e-4)
    cmp_, sig_ref, npts = measure(spec, {
        "결함": m_def, "예측_묻힌_튜브만_뺌": m_pred, "실제_수리후_m4": m_rep,
        "기각안_union_carbon": m_union_arm, "기각안_union_plastic": m_union_acc,
        "기각안_0.1mm_띄움": m_gap}, "결함")
    cop_before = {f"{t*1000:g} mm": coplanar_area(m_def, "accent", "arm", t)
                  for t in (1e-6, 1e-5, 1e-4)}
    cop_after = {f"{t*1000:g} mm": coplanar_area(m_rep, "accent", "arm", t)
                 for t in (1e-6, 1e-5, 1e-4)}
    ab, aa = area_by_group(m_def), area_by_group(m_rep)
    keep2, bur2, tot2, n2, _ = buried_mask(m_rep, "arm", "accent")
    print(f"  m4 {key} Δazmean {[cmp_['실제_수리후_m4'][c]['azimuth_mean_db'] for c, _, _ in CONFIGS]}",
          flush=True)
    return {
        "크기": dict(arm_면수=n_arm, arm_면적_mm2=round(tot, 3),
                   arm이_accent_안_면수=n_bur, arm이_accent_안_면적_mm2=round(bur, 3),
                   그_비율_pct_of_arm=round(100 * bur / tot, 2),
                   동일평면_accent면적_mm2=cop_before, 수리후_동일평면=cop_after,
                   수리후_arm이_accent_안_면적_mm2=round(bur2, 3),
                   시트_이동_정점수=n_moved),
        "그룹면적_mm2": dict(전=ab, 후=aa),
        "면수": dict(전체_전=len(m_def.f), 전체_후=len(m_rep.f),
                   arm_전=int((np.asarray(m_def.g) == "arm").sum()),
                   arm_후=int((np.asarray(m_rep.g) == "arm").sum())),
        "σ": cmp_, "σ_결함_azmean_dbsm": sig_ref, "점수": npts,
        "판정": {c: verdict(cmp_["실제_수리후_m4"][c]["azimuth_mean_db"]) for c, _, _ in CONFIGS},
        "메쉬지문": dict(결함=mesh_digest(m_def), 수리후=mesh_digest(m_rep)),
    }


def main():
    t0 = time.time()
    SRC_STATE.update(source_state())
    print("소스 지문:", SRC_STATE, flush=True)
    print("I4 — 묻힌 캐노피 (셸형 7기체)", flush=True)
    i4 = run_i4()
    print("m4 — x500v2 accent/arm", flush=True)
    m4 = run_m4()
    payload = dict(_run=dict(generated_utc=time.strftime("%Y-%m-%d %H:%M:%S"),
                             seconds=round(time.time() - t0, 1),
                             소스지문=SRC_STATE),
                   I4=i4, m4=m4)
    tmp = OUT + ".part"
    json.dump(payload, open(tmp, "w"), ensure_ascii=False, indent=1)
    print("wrote", tmp, round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
