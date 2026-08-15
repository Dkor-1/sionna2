# -*- coding: utf-8 -*-
"""az_falsify_facets.py — «45° 돌리면 거울 반사가 사라진다» 를 메쉬로 직접 검산.
방위를 훑으며 **정확히 시선 쪽을 보는 삼각형**의 면적을 잰다.
GPU 안 씀(mitsuba/sionna 임포트 없음). 메쉬는 src 의 파라메트릭 생성기로 만든다."""
import json, sys
import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/src")
from drones import DRONES                                       # noqa: E402
from articulated_fast import FastPoser, rotor_phases            # noqa: E402

FC = 3.5e9
LAM = 2.998e8 / FC
spec = DRONES["matrice4e"]
fp = FastPoser(spec)
RPM = np.array([3808.36, 3791.64, 3795.402, 3804.598])
ph = rotor_phases(np.array([0.0]), RPM, fp.dirs)
mv = fp.pose(ph[0])
V, F, G = mv.v, mv.f, np.asarray(mv.g)

a = V[F[:, 0]]; b = V[F[:, 1]]; c = V[F[:, 2]]
nrm = np.cross(b - a, c - a)
area = 0.5 * np.linalg.norm(nrm, axis=1)
ok = area > 0
n_hat = np.zeros_like(nrm); n_hat[ok] = nrm[ok] / (2 * area[ok])[:, None]
cen = (a + b + c) / 3.0


def los(az, el):
    az, el = np.radians(az), np.radians(el)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def aligned(u, tol_deg, groups=None):
    """시선 u 쪽을 tol_deg 안으로 정면으로 보는 삼각형의 개수·면적."""
    m = (n_hat @ u) >= np.cos(np.radians(tol_deg))
    if groups is not None:
        m &= np.isin(G, list(groups))
    return int(m.sum()), float(area[m].sum())


def plate_null_deg(L):
    """폭 L 인 평판의 단상태 거울 로브 첫 영점 각도 [deg]: 2L sinθ = λ."""
    s = LAM / (2 * L)
    return float(np.degrees(np.arcsin(s))) if s < 1 else 90.0


def plate_sidelobe_db(L, th_deg):
    """평판 sinc 패턴의 세기 [dB, 정점 대비]: cos²θ·sinc²(2L sinθ/λ)."""
    th = np.radians(th_deg)
    x = 2 * L * np.sin(th) / LAM
    s = 1.0 if x == 0 else np.sin(np.pi * x) / (np.pi * x)
    return float(10 * np.log10(max(np.cos(th) ** 2 * s ** 2, 1e-300)))


out = {"_meta": {
    "generator": "benchmark/az_falsify_facets.py",
    "gpu_ko": "⛔GPU 안 씀. mitsuba·sionna 임포트 없음 — src 의 파라메트릭 메쉬만 만든다.",
    "fc_hz": FC, "lambda_m": round(LAM, 5), "drone": "matrice4e",
    "n_faces": int(F.shape[0]),
    "recipe_ko": "삼각형 법선이 시선과 tol 안으로 맞는 면적을 방위별로 잰다. "
                 "PathSolver 의 단상태 거울 경로는 «법선이 정확히 시선» 인 삼각형에서만 난다.",
}}

# ── 동체 치수(거울 로브 폭 계산용) ───────────────────────────────────────
bb = {}
for g in sorted(set(G.tolist())):
    idx = np.unique(F[G == g].ravel()); P = V[idx]
    bb[g] = dict(size_m=[round(float(x), 4) for x in (P.max(0) - P.min(0))])
out["group_bbox_m"] = bb
out["spec_body_mm"] = dict(body_l_mm=spec.body_l_mm, body_w_mm=spec.body_w_mm,
                           body_h_mm=spec.body_h_mm, diagonal_mm=spec.diagonal_mm,
                           note_ko="⚠drones.py 주석 — body_* 는 '비율 참고용'. "
                                   "실제 외형은 메쉬 bbox(group_bbox_m) 로 잰다.")

# ── 거울 로브 폭 어림 ────────────────────────────────────────────────────
body_sz = np.array(bb["body"]["size_m"])
lobes = {}
for nm, L in [("body_width_y_0.371m", body_sz[1]), ("body_len_x_0.305m", body_sz[0]),
              ("body_height_z_0.104m", body_sz[2]), ("flat_front_guess_0.10m", 0.10),
              ("flat_front_guess_0.05m", 0.05), ("one_triangle_0.02m", 0.02)]:
    lobes[nm] = dict(L_m=round(float(L), 4),
                     first_null_deg=round(plate_null_deg(float(L)), 3),
                     at_45deg_db=round(plate_sidelobe_db(float(L), 45.0), 2),
                     L_over_lambda=round(float(L) / LAM, 2))
out["specular_lobe_estimate"] = lobes

# ── 방위 훑기: el 0 · −30 · −60 에서 정렬 면적 ───────────────────────────
sweep = {}
azs = np.arange(0, 90.5, 1.0)
for el in (0.0, -30.0, -60.0, -90.0):
    rows = []
    for az in azs:
        u = los(az, el)
        n05, a05 = aligned(u, 0.5)
        n2, a2 = aligned(u, 2.0)
        nb05, ab05 = aligned(u, 0.5, groups={"body", "canopy", "camera", "gear", "motor", "accent"})
        rows.append(dict(az=float(az), n_tol0p5=n05, area_tol0p5_m2=round(a05, 8),
                         n_tol2=n2, area_tol2_m2=round(a2, 8),
                         nonprop_n_tol0p5=nb05, nonprop_area_tol0p5_m2=round(ab05, 8)))
    sweep[f"el{el:+.0f}"] = rows
out["azimuth_sweep"] = sweep

# ── 요약: az0 vs az45 ───────────────────────────────────────────────────
summ = {}
for el in (0.0, -30.0, -60.0, -90.0):
    r = {x["az"]: x for x in sweep[f"el{el:+.0f}"]}
    for tol, key in ((0.5, "area_tol0p5_m2"), (2.0, "area_tol2_m2")):
        A0, A45 = r[0.0][key], r[45.0][key]
        summ[f"el{el:+.0f}|tol{tol}"] = dict(
            az0_m2=A0, az45_m2=A45,
            ratio_db=(None if (A0 <= 0 or A45 <= 0)
                      else round(20 * np.log10(A45 / A0), 2)),
            note_ko=("az45 에 정렬 삼각형이 **하나도 없다**" if A45 <= 0 else
                     ("az0 에 정렬 삼각형이 하나도 없다" if A0 <= 0 else "")))
    summ[f"el{el:+.0f}|nonprop_tol0.5"] = dict(
        az0_m2=r[0.0]["nonprop_area_tol0p5_m2"], az45_m2=r[45.0]["nonprop_area_tol0p5_m2"])
out["az0_vs_az45"] = summ

json.dump(out, open(f"{ROOT}/outputs/az_falsify_facets.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out["specular_lobe_estimate"], ensure_ascii=False, indent=1))
print(json.dumps(out["az0_vs_az45"], ensure_ascii=False, indent=1))
for el in ("el+0", "el-60"):
    print(el, [(r["az"], r["n_tol0p5"], round(r["area_tol0p5_m2"] * 1e4, 3))
               for r in sweep[el] if r["n_tol0p5"] > 0][:40])
