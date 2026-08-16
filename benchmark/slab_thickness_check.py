# -*- coding: utf-8 -*-
"""
slab_thickness_check.py — **셸 두께 1·2·3 mm 대 10 cm, CPU 로만 재는 판**
==========================================================================
GPU 를 사지 말지 이 표가 그 자리에서 정한다. `sionna.rt` 도 `mitsuba` 도 부르지 않는다
— 설치본 소스에 있는 **식을 그대로 옮겨** 넘파이로 푼다(아래 출처 참조).

■ 무엇이 결함인가
  `src/materials.py:make_material()` 의 **비-ITU 분기**가 `thickness` 를 안 넘겨서
  Sionna 상수 기본값 `DEFAULT_THICKNESS = 0.1`(=10 cm)이 쓰인다
  (`sionna/rt/constants.py:80`, `sionna/rt/radio_materials/radio_material.py:94·134`).
  드론 셸은 실제로 **1~3 mm** 다. 즉 지금까지 모든 PathSolver 팔이 «10 cm 플라스틱 판»
  위에서 반사·굴절을 계산했다.

■ Sionna 가 두께를 쓰는 식 (출처: `sionna/rt/utils/electromagnetics.py:60-112`,
  ITU-R P.2040 식 (43)·(44) — 단층 슬래브, 입사는 진공)
      η   = εr − j·σ/(ω ε0)                       # electromagnetics.py:30-31
      q   = 2π·d/λ · √(η − sin²θ)                 # (44)
      r'_TE = (cosθ − a)/(cosθ + a),  a = √(η − sin²θ)
      r'_TM = (η cosθ − a)/(η cosθ + a)           # :49-56
      R = r'(1 − e^{−j2q}) / (1 − r'² e^{−j2q})   # (43a)
      T = (1 − r'²) e^{−jq} / (1 − r'² e^{−j2q})  # (43b)
  ⇒ **두께는 굴절만이 아니라 정반사 R 도 바꾼다.** 이게 이 결함이 굴절 팔에만
    걸리지 않는 이유다.

■ 우리 커널(rcs_sbr)의 규약과 무엇을 견주나
  우리 커널에는 두께가 없다. 셸은
      반사  |Γ| = gamma_po('plastic') = 0.28        (materials.MATERIALS)
      투과  τ  = 1 − |Γ|² = 0.9216 = **−0.71 dB**   (rcs_sbr:327-333 «왕복 투과 진폭»)
  이 둘을 슬래브 예측과 나란히 놓는다:
      · 반사: |R(d)| 대 0.28
      · 투과: 셸을 **들어갔다 나오는** 두 번 통과 |T(d)|² 대 τ

■ 판정 문턱 (사전 등록)
  ⓪ 격자 흔들림 밴드 **AC 3.86 dB** (`outputs/grid_convergence_check.json`).
  두께를 고쳤을 때 움직이는 양이 이 밴드 **안**이면 GPU 실험은 값어치가 없다.
  **밖**이면 산다.

실행:  python benchmark/slab_thickness_check.py
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = f"{ROOT}/outputs/slab_thickness_check.json"

EPS0 = 8.8541878128e-12
C0 = 2.998e8
FC = 3.5e9

#: 우리 커널의 셸 규약 — materials.MATERIALS['plastic'] / rcs_sbr τ
GAMMA_PO_SHELL = 0.28          # 반사 실효 |Γ|
GAMMA_PO_PROP = 0.25          # 프로펠러
TAU_SHELL = 1.0 - GAMMA_PO_SHELL ** 2      # 0.9216 → −0.71 dB

#: ⓪ 격자 흔들림 밴드 — grid_convergence_check.json (AC 절대전력)
BAND_AC_DB = 3.86

#: 두께 축 — 1·2·3 mm 는 «드론 셸» 어림, 100 mm 는 지금 실제로 쓰이는 Sionna 기본값
THICK_MM = (0.5, 1.0, 2.0, 3.0, 5.0, 100.0)
ANGLES = (0.0, 30.0, 45.0, 60.0, 75.0, 85.0)

MATS = {
    # 키: (εr, σ[S/m], 설명) — src/materials.py MATERIALS 의 **비-ITU** 항목만.
    "plastic":      (2.7, 0.02, "드론 셸(ABS/PC) — body·canopy·gear·accent"),
    "prop_plastic": (2.7, 0.02, "프로펠러 — 재질은 plastic 과 동일(εr·σ 같음)"),
    "carbon":       (5.0, 3.0e3, "탄소섬유 — arm·deck·gear_cf"),
    "absorber":     (1.4, 1.2, "전파흡수체 — 챔버 전용(앙각 스윕 씬엔 없다)"),
}


# ─── Sionna 와 같은 식 (넘파이 판) ─────────────────────────────────────────────
def eta_c(er: float, sigma: float, fc: float) -> complex:
    """복소 상대유전율 η = εr − j σ/(ω ε0)  — electromagnetics.py:30-31 과 같은 부호."""
    return complex(er, -sigma / (2 * np.pi * fc * EPS0))


def slab(er: float, sigma: float, d_m, theta_deg, fc: float = FC):
    """ITU-R P.2040 (43)·(44) 단층 슬래브 → (R_TE, R_TM, T_TE, T_TM). 배열 가능."""
    eta = eta_c(er, sigma, fc)
    lam = C0 / fc
    ct = np.cos(np.radians(np.asarray(theta_deg, float)))
    st2 = 1.0 - ct ** 2
    a = np.sqrt(eta - st2)                       # 주치(principal) — Im(a)<0 → 감쇠
    q = 2 * np.pi * np.asarray(d_m, float) / lam * a
    rte = (ct - a) / (ct + a)
    rtm = (eta * ct - a) / (eta * ct + a)
    e1, e2 = np.exp(-1j * q), np.exp(-2j * q)
    out = []
    for rp in (rte, rtm):
        den = 1.0 - rp ** 2 * e2
        out.append(rp * (1.0 - e2) / den)        # R  — (43a)
    for rp in (rte, rtm):
        den = 1.0 - rp ** 2 * e2
        out.append((1.0 - rp ** 2) * e1 / den)   # T  — (43b)
    return out[0], out[1], out[2], out[3]


def pavg(x_te, x_tm) -> np.ndarray:
    """편파 전력평균 √((|TE|²+|TM|²)/2) — 우리 커널이 스칼라라 쓰는 규약
    (materials.gamma_shape 과 같은 평균)."""
    return np.sqrt((np.abs(x_te) ** 2 + np.abs(x_tm) ** 2) / 2.0)


def db(x) -> float:
    return float(20.0 * np.log10(np.maximum(np.abs(x), 1e-300)))


# ─── 자가검사 — 식을 옳게 옮겼는지 ───────────────────────────────────────────
def selftest() -> list[dict]:
    ok = []

    def chk(name, got, want, tol, unit=""):
        good = abs(got - want) <= tol
        ok.append(dict(check=name, got=round(float(got), 6),
                       want=round(float(want), 6), tol=tol, unit=unit, pass_=bool(good)))
        return good

    er, sg = MATS["plastic"][0], MATS["plastic"][1]
    # (1) d→0 이면 판이 없다 — R→0, T→1
    r, _, t, _ = slab(er, sg, 1e-9, 0.0)
    chk("d→0 이면 |R|→0", abs(r), 0.0, 1e-5)
    chk("d→0 이면 |T|→1", abs(t), 1.0, 1e-5)
    # (2) d→∞(손실 있음)이면 반무한 프레넬 — |R|→|r'|, |T|→0
    r, _, t, _ = slab(er, sg, 50.0, 0.0)
    rp = abs((1 - np.sqrt(eta_c(er, sg, FC))) / (1 + np.sqrt(eta_c(er, sg, FC))))
    chk("d→∞ 이면 |R|→벌크 프레넬", abs(r), rp, 1e-4)
    chk("d→∞ 이면 |T|→0", abs(t), 0.0, 1e-6)
    # (3) 수직입사에서는 TE 와 TM 이 같아야 한다(부호 규약 차이만)
    rte, rtm, tte, ttm = slab(er, sg, 0.002, 0.0)
    chk("θ=0 에서 |R_TE|=|R_TM|", abs(rte), abs(rtm), 1e-9)
    chk("θ=0 에서 |T_TE|=|T_TM|", abs(tte), abs(ttm), 1e-9)
    # (4) 에너지 보존 — 무손실 판(σ=0)이면 |R|²+|T|²=1
    rte, _, tte, _ = slab(er, 0.0, 0.002, 40.0)
    chk("무손실 판 |R|²+|T|²=1", abs(rte) ** 2 + abs(tte) ** 2, 1.0, 1e-9)
    # (5) 우리 커널 규약 재확인 — τ = 1−|Γ|² = −0.71 dB
    chk("우리 τ(=1−0.28²) [dB]", db(TAU_SHELL), -0.71, 0.01, "dB")
    # (6) 사분파 두께 λ/(4√εr) 에서 |R| 이 최대 — 1~3 mm 가 그 **아래**임을 확인
    dq = (C0 / FC) / (4 * np.sqrt(er))
    grid = np.linspace(1e-4, dq * 1.5, 4001)
    rr, _, _, _ = slab(er, sg, grid, 0.0)
    # ⚠ 손실(σ)과 내부 다중반사 분모 때문에 최대점이 λ/(4√εr) 에서 조금 **앞으로** 밀린다
    #   (실측 12.94 대 13.03 mm) — 그래서 허용오차를 0.2 mm 로 둔다. 확인하려는 것은
    #   «1~3 mm 가 이 최대점의 훨씬 아래(=|R| 이 두께에 가파르게 늘어나는 구간)» 라는 사실이다.
    chk("|R| 최대 두께 ≈ λ/(4√εr) [mm]", grid[int(np.argmax(np.abs(rr)))] * 1e3,
        dq * 1e3, 0.2, "mm")
    return ok


# ─── 본 계산 ────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fc", type=float, default=FC)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    fc = float(a.fc)
    lam = C0 / fc

    st = selftest()
    n_bad = sum(1 for s in st if not s["pass_"])

    rows = []
    for mk, (er, sg, note) in MATS.items():
        for d_mm in THICK_MM:
            d = d_mm * 1e-3
            for th in ANGLES:
                rte, rtm, tte, ttm = slab(er, sg, d, th, fc)
                R = float(pavg(rte, rtm))
                T = float(pavg(tte, ttm))
                rows.append(dict(
                    material=mk, thickness_mm=d_mm, theta_deg=th,
                    R_abs=round(R, 6), R_db=round(db(R), 3),
                    T_abs=round(T, 6), T_db_oneway=round(db(T), 3),
                    T_db_twoway=round(2 * db(T), 3)))

    # ── 표 A: 셸(plastic) 수직입사 — 헤드라인 ──────────────────────────────
    def get(mk, d_mm, th):
        return next(r for r in rows if r["material"] == mk
                    and r["thickness_mm"] == d_mm and r["theta_deg"] == th)

    ref = get("plastic", 100.0, 0.0)          # 지금 실제로 돌고 있는 판
    tableA = []
    for d_mm in THICK_MM:
        r = get("plastic", d_mm, 0.0)
        tableA.append(dict(
            thickness_mm=d_mm,
            R_db=r["R_db"], R_abs=r["R_abs"],
            two_way_T_db=r["T_db_twoway"],
            d_over_lambda=round(d_mm * 1e-3 / lam, 5),
            delta_R_vs_100mm_db=round(r["R_db"] - ref["R_db"], 3),
            delta_twoway_T_vs_100mm_db=round(r["T_db_twoway"] - ref["T_db_twoway"], 3),
            delta_R_vs_ours_db=round(r["R_db"] - db(GAMMA_PO_SHELL), 3),
            delta_twoway_T_vs_ours_tau_db=round(r["T_db_twoway"] - db(TAU_SHELL), 3)))

    # ── 각도 평균 — PathSolver 는 온갖 입사각을 본다 ─────────────────────────
    #   반구 위 균등 조명 가정의 세기 평균: ∫|R|² sinθcosθ dθ / ∫ sinθcosθ dθ
    th_fine = np.linspace(0.0, 89.9, 900)
    w = np.sin(np.radians(th_fine)) * np.cos(np.radians(th_fine))
    ang_avg = {}
    for mk in MATS:
        er, sg, _ = MATS[mk]
        row = {}
        for d_mm in THICK_MM:
            rte, rtm, tte, ttm = slab(er, sg, d_mm * 1e-3, th_fine, fc)
            R2 = pavg(rte, rtm) ** 2
            T2 = pavg(tte, ttm) ** 2
            row[f"{d_mm:g}mm"] = dict(
                R_db=round(10 * float(np.log10((R2 * w).sum() / w.sum())), 3),
                #: 카본은 두 번 통과가 사실상 0 이라 log 가 −inf 로 간다 → 바닥을 깐다
                twoway_T_db=round(20 * float(np.log10(
                    max((T2 * w).sum() / w.sum(), 1e-30))), 3))
        ang_avg[mk] = row

    # ── 우리 커널의 각도평균 |Γ| — 사과 대 사과로 견주려면 각도 모양을 얹어야 한다 ──
    #   `materials.gamma_po_angle` 규약: |Γ(θ)| = 0.28 · |Γ_벌크(θ)|/|Γ_벌크(0)|  (전력평균)
    er_p, sg_p, _ = MATS["plastic"]
    eta_p = eta_c(er_p, sg_p, fc)
    ct = np.cos(np.radians(th_fine))
    ap_ = np.sqrt(eta_p - (1 - ct ** 2))
    shape = pavg((ct - ap_) / (ct + ap_), (eta_p * ct - ap_) / (eta_p * ct + ap_))
    ap0 = np.sqrt(eta_p - 0.0)
    shape0 = pavg((1 - ap0) / (1 + ap0), (eta_p - ap0) / (eta_p + ap0))
    g_ours = GAMMA_PO_SHELL * shape / shape0
    ours_angavg_db = round(10 * float(np.log10(((g_ours ** 2) * w).sum() / w.sum())), 3)

    # ── 판정 ────────────────────────────────────────────────────────────────
    d2 = get("plastic", 2.0, 0.0)
    dR_norm = d2["R_db"] - ref["R_db"]
    dR_ang = (ang_avg["plastic"]["2mm"]["R_db"] - ang_avg["plastic"]["100mm"]["R_db"])
    dT_norm = d2["T_db_twoway"] - ref["T_db_twoway"]
    span13 = get("plastic", 3.0, 0.0)["R_db"] - get("plastic", 1.0, 0.0)["R_db"]
    carbon_d = (ang_avg["carbon"]["2mm"]["R_db"] - ang_avg["carbon"]["100mm"]["R_db"])

    verdict = dict(
        band_ac_db=BAND_AC_DB,
        delta_R_2mm_vs_100mm_normal_db=round(dR_norm, 3),
        delta_R_2mm_vs_100mm_angleavg_db=round(dR_ang, 3),
        delta_twoway_T_2mm_vs_100mm_db=round(dT_norm, 3),
        span_1mm_to_3mm_R_db=round(span13, 3),
        carbon_delta_R_2mm_vs_100mm_db=round(carbon_d, 3),
        buy_gpu=bool(abs(dR_ang) > BAND_AC_DB or abs(dR_norm) > BAND_AC_DB),
        verdict_ko=(
            "⭐**GPU 를 산다.** 셸 정반사가 2 mm 로 고치면 "
            f"수직입사 {dR_norm:+.2f} dB · 각도평균 {dR_ang:+.2f} dB 움직이는데, "
            f"⓪ 격자 흔들림 밴드 {BAND_AC_DB} dB **밖**이다. "
            f"게다가 1↔3 mm 안에서만 {span13:+.2f} dB 가 갈리므로 두께는 "
            "단일값이 아니라 **민감도 축**이어야 한다."
            if (abs(dR_ang) > BAND_AC_DB or abs(dR_norm) > BAND_AC_DB) else
            "GPU 를 사지 않는다 — 두께를 고쳐도 움직이는 양이 ⓪ 밴드 안이다."),
        tau_gap_1_3mm_db=[round(r["delta_twoway_T_vs_ours_tau_db"], 3)
                          for r in tableA if r["thickness_mm"] in (1.0, 2.0, 3.0)],
        ours_gamma_angleavg_db=ours_angavg_db,
        tau_note_ko=(
            f"우리 커널 τ(−0.71 dB)는 «셸을 들어갔다 나오는» 두 번 통과를 뜻한다. "
            f"1~3 mm 슬래브의 두 번 통과 손실은 "
            f"{get('plastic',1.0,0.0)['T_db_twoway']:+.2f} ~ "
            f"{get('plastic',3.0,0.0)['T_db_twoway']:+.2f} dB 라 τ 와 "
            f"{min(abs(r['delta_twoway_T_vs_ours_tau_db']) for r in tableA if r['thickness_mm'] in (1.0,2.0,3.0)):.2f}~"
            f"{max(abs(r['delta_twoway_T_vs_ours_tau_db']) for r in tableA if r['thickness_mm'] in (1.0,2.0,3.0)):.2f} dB "
            f"차이다 — **투과 축은 결함이 아니다**(우리 τ 가 조금 짜다). 반대로 **100 mm 판**의 "
            f"두 번 통과는 {ref['T_db_twoway']:+.2f} dB 라 τ 와 "
            f"{abs(next(r for r in tableA if r['thickness_mm'] == 100.0)['delta_twoway_T_vs_ours_tau_db']):.2f}"
            f" dB 어긋난다 — 지금 PathSolver 팔은 "
            f"셸 안쪽(배터리·PCB)을 우리 커널보다 그만큼 어둡게 보고 있다."),
        ours_gamma_note_ko=(
            f"⚠**우리 커널도 같은 방향으로 세다.** 셸 |Γ|=0.28 에 각도 모양을 얹은 각도평균이 "
            f"{ours_angavg_db:+.2f} dB 인데, 슬래브는 1 mm {ang_avg['plastic']['1mm']['R_db']:+.2f} · "
            f"2 mm {ang_avg['plastic']['2mm']['R_db']:+.2f} · "
            f"3 mm {ang_avg['plastic']['3mm']['R_db']:+.2f} · "
            f"100 mm {ang_avg['plastic']['100mm']['R_db']:+.2f} dB 다. 즉 우리 «대표 실효값» 은 "
            f"**두꺼운 판(벌크)에 해당**하고, 2 mm 를 믿는다면 우리 커널이 "
            f"{ours_angavg_db - ang_avg['plastic']['2mm']['R_db']:+.2f} dB 세게 반사하고 있다. "
            f"⚠이건 이번 라운드의 산출이 아니라 **다음 라운드로 넘기는 열린 항목**이다 — "
            f"gamma_po 를 건드리면 앵커·리포트 전부가 흔들린다. 지금 적어 두는 이유는 "
            f"«PathSolver 만 오염됐다» 고 읽히면 안 되기 때문이다."),
        carbon_note_ko=(
            "탄소섬유는 두께를 안 타는 게 맞다 — σ=3000 S/m 의 표피깊이가 "
            f"{np.sqrt(2/(2*np.pi*fc*4e-7*np.pi*3.0e3))*1e3:.3f} mm 라 1 mm 도 이미 "
            "여러 표피깊이다. 그래서 arm·deck·gear_cf 는 손잡이가 필요 없다."),
    )

    doc = dict(_meta=dict(
        generator="benchmark/slab_thickness_check.py",
        question_ko="셸 두께 1·2·3 mm 와 Sionna 기본값 10 cm 가 반사·투과에서 몇 dB 갈리나",
        formula_source=("sionna/rt/utils/electromagnetics.py:60-112 "
                        "(ITU-R P.2040 식 43·44) 를 넘파이로 옮김 — GPU·mitsuba 미사용"),
        defect=("src/materials.py:make_material() 비-ITU 분기가 thickness 를 안 넘겨 "
                "sionna/rt/constants.py:80 DEFAULT_THICKNESS=0.1 m 가 쓰인다"),
        provenance_ko=("⚠**두께는 출처가 없는 값이다** — docs/RETRACTION_LOG.md A3 이 "
                       "«진짜 출처 없는 건 셸 두께» 라고 적어 뒀다. DJI 는 부품 두께를 "
                       "공개하지 않는다. 그러므로 1·2·3 mm 는 **측정값이 아니라 민감도 축**이고, "
                       "결과는 «두께 d 를 가정하면» 이라는 조건문으로만 인용한다."),
        fc_hz=fc, lambda_m=round(lam, 6),
        ours_convention=dict(gamma_po_shell=GAMMA_PO_SHELL, gamma_po_prop=GAMMA_PO_PROP,
                             tau_shell=round(TAU_SHELL, 6),
                             tau_shell_db=round(db(TAU_SHELL), 3),
                             note_ko="우리 커널에는 두께 개념이 없다 — |Γ| 와 τ 만 있다"),
        band_source="outputs/grid_convergence_check.json (AC 3.86 dB)",
        selftest_failed=n_bad),
        selftest=st, verdict=verdict,
        table_shell_normal_incidence=tableA,
        angle_averaged=ang_avg, rows=rows)
    json.dump(doc, open(a.out, "w"), ensure_ascii=False, indent=1)

    # ── 사람이 읽는 표 ──────────────────────────────────────────────────────
    print(f"\n═══ 자가검사 ({len(st)-n_bad}/{len(st)} 통과) ═══")
    for s in st:
        print(f"  {'✅' if s['pass_'] else '⛔'} {s['check']:34s} "
              f"got {s['got']:>10.5f} want {s['want']:>10.5f}")
    if n_bad:
        raise SystemExit("⛔ 자가검사 실패 — 표를 믿지 마라")

    print(f"\n═══ 플라스틱 셸 · 수직입사 · {fc/1e9:.1f} GHz (λ={lam*1e3:.1f} mm) ═══")
    print(f"{'두께':>8} {'d/λ':>8} {'|R| ':>7} {'R[dB]':>8} {'왕복T[dB]':>10} "
          f"{'ΔR vs 10cm':>11} {'ΔR vs 우리0.28':>14} {'Δ왕복T vs τ':>12}")
    for r in tableA:
        print(f"{r['thickness_mm']:>7.1f}mm {r['d_over_lambda']:>8.4f} "
              f"{r['R_abs']:>7.4f} {r['R_db']:>8.2f} {r['two_way_T_db']:>10.2f} "
              f"{r['delta_R_vs_100mm_db']:>11.2f} {r['delta_R_vs_ours_db']:>14.2f} "
              f"{r['delta_twoway_T_vs_ours_tau_db']:>12.2f}")

    print(f"\n═══ 각도평균(반구 균등 조명 sinθcosθ 가중) R [dB] ═══")
    print(f"{'재질':>13} " + " ".join(f"{k:>9}" for k in ang_avg['plastic']))
    for mk, row in ang_avg.items():
        print(f"{mk:>13} " + " ".join(f"{v['R_db']:>9.2f}" for v in row.values()))

    print(f"\n═══ 판정 ═══\n{verdict['verdict_ko']}\n{verdict['tau_note_ko']}\n{verdict['ours_gamma_note_ko']}\n"
          f"{verdict['carbon_note_ko']}\n\n✅ {a.out}")


if __name__ == "__main__":
    main()
