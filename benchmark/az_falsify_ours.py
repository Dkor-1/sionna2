# -*- coding: utf-8 -*-
"""az_falsify_ours.py — ⭐«방위 45° 판» 반증 계산 (CPU 전용, 저장 원장만 읽는다).

검증 대상 주장
  «드론을 방위 45° 돌리면 PathSolver 의 el0 에코가 25~51 dB 사라진다. 우리 커널은 둔감하다(3 dB 안).»

여기서 하는 네 가지
  ① 단위 다리 — 우리 E [m²] 와 Sionna a [무차원] 를 **같은 σ [dBsm]** 로 환산해 비교 성립 여부를 판정
  ② 거리 법칙 — 15 m ↔ 30 m 팔로 «σ 가 거리에 불변인가» 를 재서 값의 성격을 가른다
  ③ 격자·거리 대비 방위 — 우리 커널의 방위 효과가 자기 수치 산포보다 큰가
  ④ 기하 — 메쉬에서 시선에 **정확히 수직인 삼각형**을 세어 두 팔의 차이를 귀속

⛔GPU 안 쓴다 (mitsuba·sionna.rt import 없음).
"""
from __future__ import annotations
import json
import sys
import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/src")

C0, FC, R15, R30 = 299792458.0, 3.5e9, 15.0, 30.0
LAM = C0 / FC
K_OURS = 4 * np.pi / LAM ** 2                    # σ = K|E|² , E [m²]
MIR15 = LAM / (4 * np.pi * 2 * R15)              # 무한거울 진폭 λ/(4π(R1+R2)), 크기 무관


def k_ps(R):                                     # σ = K|a|² , a 는 등방 Friis 규약(무차원)
    return (4 * np.pi) ** 3 * R ** 4 / LAM ** 2


def d10(x):
    return float(10 * np.log10(x + 1e-300))


def main():
    z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")
    out = {"_meta": {
        "generator": "benchmark/az_falsify_ours.py",
        "gpu_used": False,
        "question_ko": "방위 45° 에서 두 엔진의 차이는 물리인가 아티팩트인가 — 그리고 우리 커널이 로브를 못 그리는가",
        "unit_bridge_ko": ("우리 커널의 E 는 **면적 차원 [m²]**(투영면적분 Σ|Γ|e^{j2kp·û}d²) 이고 "
                           "Sionna 의 a 는 **무차원 채널계수**(등방 Friis λ/4πd — outputs/facet_mechanism.json "
                           "convention_check 에서 −23.32914474 dB ↔ 이론 −23.32914411 dB 로 확정). "
                           "따라서 원장의 level_db 를 두 엔진 사이에서 직접 빼면 **차원이 다른 수의 뺄셈**이다."),
        "sigma_from_ours": "sigma = 4*pi/lam^2 * |E|^2",
        "sigma_from_ps": "sigma = (4*pi)^3 * R^4 / lam^2 * |a|^2   (단일 모노스태틱 등방안테나, baseline 0)",
        "mirror_amp_15m": MIR15,
        "lambda_m": LAM,
    }}

    # ── ① 단위 다리 ────────────────────────────────────────────────────────
    arms = {
        "ours_az0": ("ours_r15_n8192", "ours", R15),
        "ours_az45": ("ours_r15_n8192_az45", "ours", R15),
        "ps_physoff_az0": ("sionna_p4000000000_r15_n8192_d1", "ps", R15),
        "ps_physoff_az45": ("sionna_p4000000000_r15_n8192_az45_d1", "ps", R15),
        "ps_physon_az0": ("sionna_p4000000000_phys_r15_n8192_d1", "ps", R15),
        "ps_physon_az45": ("sionna_p4000000000_phys_r15_n8192_az45_d1", "ps", R15),
        "ps_stockdef_az0": ("sionna_p4000000000_stockdef_r15_n8192", "ps", R15),
        "ours_div24_az0": ("ours_r15_n8192_div24", "ours", R15),
        "ours_ptd_az0": ("ours_ptd_r15_n8192", "ours", R15),
    }
    tab = {}
    for lab, (arm, kind, R) in arms.items():
        K = K_OURS if kind == "ours" else k_ps(R)
        for el in ("el+0", "el-30", "el-60", "el-90"):
            key = f"{arm}/{el}"
            if key not in z.files:
                continue
            E = z[key]
            dc = complex(E.mean())
            ac = float(np.mean(np.abs(E - dc) ** 2))
            tab[f"{lab}/{el}"] = dict(
                sigma_total_dbsm=round(d10(K * float(np.mean(np.abs(E) ** 2))), 2),
                sigma_dc_dbsm=round(d10(K * abs(dc) ** 2), 2),
                sigma_ac_dbsm=round(d10(K * ac), 2),
                raw_level_db=round(20 * float(np.log10(abs(E).mean() + 1e-300)), 2),
                dc_over_mirror=(round(abs(dc) / MIR15, 4) if kind == "ps" else None))
    out["sigma_table"] = tab

    deltas = {}
    for el in ("el+0", "el-30", "el-60", "el-90"):
        for eng, a, b in (("ours", "ours_az0", "ours_az45"),
                          ("ps_physoff", "ps_physoff_az0", "ps_physoff_az45"),
                          ("ps_physon", "ps_physon_az0", "ps_physon_az45")):
            ka, kb = f"{a}/{el}", f"{b}/{el}"
            if ka in tab and kb in tab:
                deltas[f"{eng}/{el}"] = {
                    m: round(tab[kb][m] - tab[ka][m], 2)
                    for m in ("sigma_total_dbsm", "sigma_dc_dbsm", "sigma_ac_dbsm")}
    out["az45_minus_az0_db"] = deltas

    # ── ② 거리 법칙 (15 m ↔ 30 m, el0) ─────────────────────────────────────
    rng = {}
    for lab, (a15, a30, kind) in {
            "ps_physoff": ("sionna_p4000000000_r15_n8192_d1",
                           "sionna_p4000000000_r30_n8192_d1", "ps"),
            "ours": ("ours_r15_n8192", "ours_r30_n8192", "ours")}.items():
        E1, E2 = z[f"{a15}/el+0"], z[f"{a30}/el+0"]
        s1 = d10((K_OURS if kind == "ours" else k_ps(R15)) * abs(E1.mean()) ** 2)
        s2 = d10((K_OURS if kind == "ours" else k_ps(R30)) * abs(E2.mean()) ** 2)
        rng[lab] = dict(amp_ratio_db=round(20 * float(np.log10(abs(E2.mean()) / abs(E1.mean()))), 2),
                        sigma15_dbsm=round(s1, 2), sigma30_dbsm=round(s2, 2),
                        sigma_shift_db=round(s2 - s1, 2))
    rng["_reading_ko"] = ("PathSolver 진폭이 1/R²(−12.04 dB) 로 떨어져 σ 가 거리에 **불변**이다 — "
                          "즉 그 값은 «표적의 σ» 로 행세한다. 우리 커널의 E 는 원래 거리 무관이어야 "
                          "하는데 −6.15 dB 움직였다 — 근거리장 곡률(15 m 는 2D²/λ=14.2 m 바로 밖) 이 "
                          "**상쇄 잔차**를 흔든 몫이다. 그만큼 el0 절대레벨은 우리 쪽도 무르다.")
    out["range_law_el0"] = rng

    # ── ③ 우리 커널: 방위 효과 vs 자기 수치 산포 ────────────────────────────
    band = json.load(open(f"{ROOT}/outputs/grid_convergence_check.json"))
    b = {x["metric"]: x for x in band["grid_dispersion_bands"]["bands"]["layer2_statistics"]}
    cmpr = {}
    for el in ("el+0", "el-30"):
        a = tab[f"ours_az0/{el}"]; c = tab[f"ours_div24_az0/{el}"]
        cmpr[el] = dict(
            az45_minus_az0_ac_db=deltas[f"ours/{el}"]["sigma_ac_dbsm"],
            az45_minus_az0_dc_db=deltas[f"ours/{el}"]["sigma_dc_dbsm"],
            div24_minus_div12_ac_db=round(c["sigma_ac_dbsm"] - a["sigma_ac_dbsm"], 2),
            div24_minus_div12_dc_db=round(c["sigma_dc_dbsm"] - a["sigma_dc_dbsm"], 2))
    cmpr["_bands"] = dict(ac_power_db=b["ac_power_db"]["band"], dc_power_db=b["dc_power_db"]["band"])
    cmpr["_reading_ko"] = ("el0·el−30 에서 방위 효과(AC 0.55·0.36 dB)가 같은 팔의 **격자 사다리** "
                           "효과(−3.87·−0.38 dB)보다 작거나 비슷하다 → 밴드 3.861 dB 안이라 판정 불가. "
                           "el−60 의 DC +18.05 dB 만 DC 밴드 6.613 dB 를 넘는다 — 즉 우리 커널은 "
                           "«방위에 둔감» 하지 않다. 거기서는 방위에 크게 반응한다.")
    out["ours_azimuth_vs_own_noise"] = cmpr

    # ── ④ 기하 — 시선에 수직인 삼각형 ──────────────────────────────────────
    from drones import DRONES
    from articulated_fast import FastPoser, rotor_phases
    TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
    fp = FastPoser(DRONES["matrice4e"])
    ph = rotor_phases(np.arange(1) / float(TJ["prf_hz"]),
                      np.asarray(TJ["rpm_per_rotor"], float), fp.dirs)
    mv = fp.pose(ph[0])
    V, F, G = np.asarray(mv.v, float), np.asarray(mv.f, int), np.asarray(mv.g)
    Nv = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    area = 0.5 * np.linalg.norm(Nv, axis=1)
    nrm = Nv / (np.linalg.norm(Nv, axis=1, keepdims=True) + 1e-300)
    geo = {}
    for az, el in ((0, 0), (45, 0), (0, -60), (45, -60), (0, -90)):
        a_, e_ = np.radians(az), np.radians(el)
        u = np.array([np.cos(e_) * np.cos(a_), np.cos(e_) * np.sin(a_), np.sin(e_)])
        m = np.abs(nrm @ u) > np.cos(np.radians(0.2))
        geo[f"az{az}_el{el}"] = dict(n_tri_perp=int(m.sum()),
                                     area_cm2=round(float(area[m].sum()) * 1e4, 2),
                                     groups=sorted(set(G[m].tolist())))
    geo["_reading_ko"] = ("az0/el0 에서 시선에 **정확히 수직인** 삼각형이 106 장(139 cm²·battery·camera·pcb "
                          "= 축정렬 금속 상자면)이고, az45 에서는 4 장(0.19 cm²·플라스틱 캐노피)뿐이다. "
                          "PathSolver 의 붕괴는 이 정렬이 꺼지는 사건이다.")
    out["mesh_perpendicular_facets"] = geo

    with open(f"{ROOT}/outputs/az_falsify_ours.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("═══ ① σ [dBsm] — 같은 단위로 놓았을 때 ═══")
    print(f"{'arm/el':34s} {'σ_tot':>8s} {'σ_DC':>8s} {'σ_AC':>8s} {'raw level_db':>13s}")
    for k, v in tab.items():
        print(f"{k:34s} {v['sigma_total_dbsm']:8.2f} {v['sigma_dc_dbsm']:8.2f} "
              f"{v['sigma_ac_dbsm']:8.2f} {v['raw_level_db']:13.2f}")
    print("\n═══ ② 거리 법칙 (el0) ═══")
    for k, v in rng.items():
        if k.startswith("_"):
            continue
        print(f"  {k:12s} amp(30m)/amp(15m) {v['amp_ratio_db']:+7.2f} dB | "
              f"σ 15m {v['sigma15_dbsm']:8.2f} → 30m {v['sigma30_dbsm']:8.2f} dBsm "
              f"({v['sigma_shift_db']:+.2f})")
    print("\n═══ ③ 우리 커널: 방위 vs 격자 ═══")
    for k, v in cmpr.items():
        if k.startswith("_"):
            continue
        print(f"  {k}: az45−az0 AC {v['az45_minus_az0_ac_db']:+6.2f} / DC {v['az45_minus_az0_dc_db']:+6.2f}"
              f" | div24−div12 AC {v['div24_minus_div12_ac_db']:+6.2f} / DC {v['div24_minus_div12_dc_db']:+6.2f}")
    print(f"  밴드: AC {cmpr['_bands']['ac_power_db']} dB · DC {cmpr['_bands']['dc_power_db']} dB")
    print("\n═══ ④ 시선에 수직인 삼각형 ═══")
    for k, v in geo.items():
        if k.startswith("_"):
            continue
        print(f"  {k:12s} n={v['n_tri_perp']:5d}  area={v['area_cm2']:9.2f} cm²  {v['groups']}")
    print("\n✅ outputs/az_falsify_ours.json")


if __name__ == "__main__":
    main()
