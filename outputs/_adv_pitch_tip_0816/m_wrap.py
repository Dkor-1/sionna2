# -*- coding: utf-8 -*-
"""마무리 측정 3종 — (1) 기준 반경의 «분해 가능성» (2) 팁 밴드 면적 (3) 3DR Solo 실측."""
import json
import sys
import numpy as np
import trimesh
from scipy.spatial import ConvexHull

sys.path[:0] = ["/workspace/sionna/src", "/workspace/sionna/benchmark"]
import drone_cad                                     # noqa: E402

RAW = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/dji_blade_raw.json"
OUT = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/wrap.json"
res = {}

# ── (1) 기준 반경 0.75R 은 이 데이터로 «가려낼 수» 있는가 ────────────────────────────
d = json.load(open(RAW))
rows = [b for b in d["blades"] if b["axis"] == "hub"]
grid = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
K = np.array([[b["rows"][str(x)]["k_cal"] for x in grid] for b in rows])
argmax_r = [grid[int(np.argmax(k))] for k in K]
res["A_reference_station"] = dict(
    per_blade_argmax_r_over_R=argmax_r,
    mean_k=dict(zip(map(str, grid), np.round(K.mean(0), 4).tolist())),
    sd_k=dict(zip(map(str, grid), np.round(K.std(0), 4).tolist())),
    flat_band_ko="평균 k 가 최대의 2 % 안에 드는 r/R 구간",
    flat_band=[x for x, v in zip(grid, K.mean(0)) if v >= 0.98 * K.mean(0).max()],
    audit_k_at_0p75=1.015, mine_k_at_0p75=float(K.mean(0)[grid.index(0.75)]),
)
#  P_nom 을 ±5 % 흔들면 k=1 이 어디로 가나 (k 가 평평해서 조건수가 나쁘다)
mk = K.mean(0)
for pct in (-5, -3, -2, 0, 2, 3, 5):
    kk = mk / (1 + pct / 100.0)
    cross = [grid[i] for i in range(len(grid) - 1)
             if (kk[i] - 1) * (kk[i + 1] - 1) < 0]
    res["A_reference_station"][f"k_eq_1_crossings_Pnom{pct:+d}pct"] = cross
res["A_reference_station"]["legacy_k_at_0p75R"] = float(
    np.interp(0.75, drone_cad.PITCH_RR, drone_cad.PITCH_K))
res["A_reference_station"]["dji_code_k_at_0p75R"] = float(
    np.interp(0.75, drone_cad.PITCH_RR_DJI_MINI2, drone_cad.PITCH_K_DJI_MINI2))

# ── (2) 팁 밴드 면적: legacy / 코드의 dji 표 / 내 실측 ────────────────────────────
meas_rr = np.arange(0.88, 1.0001, 0.01)
meas_fr = np.array([0.611, 0.593, 0.575, 0.556, 0.536, 0.511, 0.490,
                    0.468, 0.445, 0.422, 0.402, 0.370, 0.292])
rr = np.linspace(0.90, 1.00, 401)
cur = dict(
    legacy=np.interp(rr, drone_cad.CHORD_RR, drone_cad.CHORD_FRAC),
    dji_code=np.interp(rr, drone_cad.CHORD_RR_DJI_MINI2, drone_cad.CHORD_FRAC_DJI_MINI2),
    measured=np.interp(rr, meas_rr, meas_fr),
)
cur["legacy_tip0.20"] = np.interp(rr, drone_cad.CHORD_RR,
                                  list(drone_cad.CHORD_FRAC[:-1]) + [0.20])
area = {k: float(np.trapezoid(v, rr)) for k, v in cur.items()}
res["B_tip_band_area"] = dict(
    band="0.90–1.00R, 정규화 시위 c/c_max 의 적분(∫c dr)",
    area=area,
    ratio_to_measured={k: round(v / area["measured"], 4) for k, v in area.items()},
    db_if_flatplate_translation={k: round(20 * np.log10(v / area["measured"]), 2)
                                 for k, v in area.items()},
    node_by_node={f"{x:.2f}": dict(legacy=round(float(np.interp(x, drone_cad.CHORD_RR, drone_cad.CHORD_FRAC)), 3),
                                   dji_code=round(float(np.interp(x, drone_cad.CHORD_RR_DJI_MINI2, drone_cad.CHORD_FRAC_DJI_MINI2)), 3),
                                   measured=round(float(np.interp(x, meas_rr, meas_fr)), 3))
                  for x in (0.90, 0.95, 0.96, 0.97, 0.98, 0.99, 1.00)},
)

# ── (3) 3DR Solo 참조 CAD — 우리 «0.5R 기준» 의 출처 ─────────────────────────────
m = trimesh.load("/workspace/sionna/assets/meshes/reference/solo_prop_cw.stl")
V = np.array(m.vertices, float)
V = V - V.mean(0)
ev, evec = np.linalg.eigh(np.cov(V.T))
a = evec[:, 0]                                     # 납작한 프롭의 대칭축 = 회전축
z = V @ a
Xp = V - np.outer(z, a)
r = np.linalg.norm(Xp, axis=1)
R = r.max()
e1 = np.array([1.0, 0, 0]) - a[0] * a
e1 /= np.linalg.norm(e1)
e2 = np.cross(a, e1)
phi = np.arctan2(Xp @ e2, Xp @ e1)
P_nom_solo = 4.5 * 25.4                            # 10x4.5 제원 [mm]
solo = {}
for x in (0.30, 0.50, 0.70, 0.75, 0.80, 0.90):
    r0 = x * R
    sel = np.abs(r - r0) <= 0.006 * R
    ph = phi[sel]
    ph0 = ph[np.abs(np.angle(np.exp(1j * (ph - np.median(ph))))) < np.pi / 3]
    m2 = sel & (np.abs(np.angle(np.exp(1j * (phi - np.median(ph0))))) < np.pi / 3)
    if m2.sum() < 8:
        continue
    pp = np.angle(np.exp(1j * (phi[m2] - np.median(phi[m2]))))
    Q = np.c_[r0 * pp, z[m2] - np.median(z[m2])]
    H = Q[ConvexHull(Q).vertices]
    D = H[:, None, :] - H[None, :, :]
    L = np.linalg.norm(D, axis=-1)
    i, j = np.unravel_index(np.argmax(L), L.shape)
    v = H[j] - H[i]
    beta = np.arctan2(abs(v[1]), abs(v[0]))
    solo[f"{x:.2f}"] = dict(P_local_in=round(float(2 * np.pi * r0 * np.tan(beta) / 25.4), 3),
                            k=round(float(2 * np.pi * r0 * np.tan(beta) / P_nom_solo), 3),
                            beta_deg=round(float(np.degrees(beta)), 2))
res["C_solo_reference"] = dict(
    R_mm=round(float(R), 2), dia_mm=round(float(2 * R), 2),
    designation="3DR Solo 순정 프롭 = 10 x 4.5 in (제원)",
    stations=solo,
    ledger_PITCH_K_at=dict(zip(map(str, drone_cad.PITCH_RR), drone_cad.PITCH_K)),
)

json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, ensure_ascii=False, indent=1))
