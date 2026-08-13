# -*- coding: utf-8 -*-
"""
make_report05_results.py — 리포트 05(검출 결과) 노트북 생성기
==========================================================================================
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report05_results.py

산출: `report05_results.ipynb`. 그림은 `src/viz_report05_paper.py` 가 만든 **게재 규격**
7장(벡터 PDF + 400 dpi PNG)을 끼운다(없으면 이 스크립트가 먼저 그린다).

계약서 두 장이 동시에 걸린다.

| 계약 | 무엇을 정하나 | 강제하는 곳 |
|---|---|---|
| `docs/REBUILD_2026-07-30.md` §5 | 서술 규약(여는 블록·톤·분량) | `src/report_style.py` |
| `docs/PAPER_SPEC.md` §4 | 논문 참고자료 규격(대응·방어선·그림·방법·인용) | `src/paper_kit.py` |

숫자는 전부 `num()`(JSON 대조) 또는 `dnum()`(JSON 에서 계산) 을 통과한다 — 손으로 친 숫자는 없다.

이 편이 하는 일 — 논문 **V. Results** 의 소스
------------------------------------------------------------------------------------------
같은 표적·같은 기하·하나의 교정 문턱에서 세 조명원(WiFi VHT-LTF · LTE CRS · 5G SSB)을 비교하고,
① 밴드 격차를 항별로 분해하고 ② 5G 의 상시기준 대가를 **CPI 스윕**으로 내고 ③ 수신소자 이득을
열잡음 코히어런트 상한과 대조한다.

⭐ 좁힌 지점(PAPER_SPEC §5 순서대로) — 본문 §3.3·§3.4·§3.5 가 같은 말을 수치로 한다
------------------------------------------------------------------------------------------
1. **파형 순위**는 자세 인용 방식이 정한다. 단일 자세에서 다섯 기체가 3가지 순위를 내고,
   자세평균 σ + 기울기 앵커에서 다섯 기체가 하나의 순위(LTE > 5G > WiFi)에 합의한다
   ⟨outputs/sigma_sensitivity.json : ranking_consensus⟩. 그래서 헤드라인은 **자세평균 설정**의
   순위 + 기체별 뒤집힘 문턱이다.
2. **절대 검출거리는 헤드라인에서 뺀다**(PAPER_SPEC §2). §3.3 의 km 표는 공통모드 민감도 봉투
   (±10 dB → −43.3%/+76.4%)를 같은 절에 달고 읽는다.
3. **듀티 축**은 R90 경로에서 호출되지 않는다 — 그 크기(WiFi −12.84 · LTE 0 · 5G −16.02 dB)를
   §2.2 에 수치로 싣고, 그 항을 켠 설정에서 순위 합의가 갈리는 것까지 §3.4 표가 적는다.
4. 바이스태틱은 **β ≤ 45°** 에서 성립한다(방법 조건).

수치의 성립 조건(전부 여는 블록의 **방법** 칸에 조건절로 들어간다)
------------------------------------------------------------------------------------------
① 밴드 비교의 σ 는 **A(f) 의 기울기만** Das 측정(IEEE WCL 2026 15:3731) 에 맞춘 원장이다
   — `outputs/sigma_anchor.json`, 생산 모드 `slope_only`. **절대 레벨은 우리 PO 출력**이고
   세 밴드 평균 레벨이동은 0 이다(02 §4 와 같은 말).
② R90 은 **공칭 헤딩 ψ=0** 에서 SNR(d) 가 교정 문턱을 마지막으로 하강교차하는 수평거리다
   (`src/freespace_link.py:448`). 헤딩 축은 §3.5 의 CPI 스윕이 든다.
③ 세 밴드의 solve 는 W1 에서 잰 문턱 SNR90 하나를 공유한다(`experiment_freespace_range.py:856`).
④ 예산은 선언값이다(EIRP 63 dBm · NF 5 dB). `meta.link_budget.provenance` 가 그렇게 적고 있다.
⑤ §3.6·§4 의 절대 SNR 은 X410 벤치 배치(단일 반송파 3.5 GHz · R_b 22.3 m)에서 나온다 —
   같은 조건에서의 **모드 간 상대 비교**가 그 두 절이 읽는 것이다.

옛 13편 번호 ↔ 이 편
------------------------------------------------------------------------------------------
`report13_freespace.json` · `report13_sigma_grid.json` 은 이 편(05)의 자유공간 산출이고,
`report5_results.json` 은 옛 번호의 잔재다(이 편은 읽지 않는다).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np                                                    # noqa: E402

import report_style as _rs                                            # noqa: E402
from report_style import (build_notebook, fetch, from_json,            # noqa: E402
                          header, md, next_steps, num, table, table_from)
from paper_kit import (attach, cite, cite_ref, defence, figure_md,     # noqa: E402
                       methods, paper_appendix, paper_map)

ROOT = os.path.abspath(os.path.join(_HERE, ".."))

# 근거 JSON — 이 편의 모든 숫자가 여기서 나온다
J_FS = "outputs/report13_freespace.json"      # 자유공간 검지거리 4단계
J_SG = "outputs/report13_sigma_grid.json"     # σ 격자(자세 × 밴드) — 현재판(앙각 확장 후)
#: ⭐ 발표된 solve 가 실제로 읽은 σ 격자판. 현재판은 2026-08-03 재생성으로 앙각이 −90° 까지
#:   넓어졌지만 이 편의 검지거리는 그 전 판 위에서 풀렸다 — 유효창은 그 판을 인용한다(§1.1).
J_SG_USED = "outputs/archive/report13_sigma_grid_pre0803.json"
J_RX = "outputs/detection_rx_sweep.json"      # 파형 9모드 × 수신소자 N 몬테카를로
J_VF = "outputs/verify_freespace.json"        # 기하·규약 게이트
J_LB = "outputs/verify_linkbudget.json"       # 사슬 항등식 · 파형별 손실항
J_AN = "outputs/sigma_anchor.json"            # 측정 앵커(02편 §4)
J_DF = "outputs/sbr_defect_fixes.json"        # 상반성 잔차(β 창의 근거)
J_SS = "outputs/sigma_sensitivity.json"       # σ 민감도 · 순위 강건성 · 격차 분해
J_CG = "outputs/cpi_guard_sweep.json"         # 5G 도플러 가드 CPI 스윕
J_DV = "outputs/report05_derived.json"        # 이 빌더가 쓰는 파생 원장(아래 derived())
J_TM = "outputs/tm_result.json"               # 표적모형 민감도 — 3모형 × 환경(§3.7)
J_TA = "outputs/tm_attack.json"               # 그 실험의 적대검증 — 추정량 · 낙차 소유권(§3.7)
J_PH = "outputs/phi_sweep.json"               # 장면 방위 φ 전수 스윕(§1.1)
J_SV = "outputs/s2r_assets_verify.json"       # σ 격자 재생성 1:1 대조(여는 블록 · 다음 단계)
#: ⭐ 2026-08-04 라운드 — σ 불확도의 **출처**를 밝히는 두 원장(인용만 한다).
J_LFA = "outputs/lowfreq_attack.json"         # PO 유효 하한과 그 파급 · 금칙(§3.2 · §3.3)
J_MFX = "outputs/meshfix_applied.json"        # 형상 정정이 σ 격자를 몇 세대 낡게 했나(방법 표)
J_MFX_ATK = "outputs/meshfix_attack.json"     # 그 정정이 어느 산출물을 낡게 했나(앵커 사슬 단서)

FIGDIR = "outputs/figures"
MODES = ("W1", "L1", "G1")
DRONES = ("mini5pro", "mavic4pro", "matrice4e", "phantom4", "s1000plus")

#: 재현 소요 — 측정치가 JSON 에 없는 단계의 **선언 예산**(초).
#: 출처: `benchmark/regen_mesh_dependents.py:77`(결함정정) `:101`(링크버짓) `:113`(검출 스윕).
DECLARED_S = {"verify_sbr_defect_fixes": 900.0,
              "verify_linkbudget": 2400.0,
              "experiment_detection": 1800.0}
#: 앵커 JSON 의 밴드 키 ↔ 검출 모드 코드
ANCHOR_BAND = {"W1": "WiFi 5.21 GHz", "L1": "LTE 1.843 GHz", "G1": "5G 3.5 GHz"}
MODE_NAME = {"W1": "WiFi", "L1": "LTE", "G1": "5G"}
CELL = "ranges.{d}.{m}.equal_psd.full_waveform_capture.by_N.1"

#: 앵커 Δσ 경로(짧게 쓰려고 한 번만 적는다)
DSIG = "drones.{d}.modes.slope_only.delta_db." + "{b}"

#: 게재 규격 그림 7장 — `src/viz_report05_paper.py` 가 만든다(벡터 PDF 가 짝으로 있다).
PF = {n: f"{FIGDIR}/report05_pf{i}_{n}.png" for i, n in
      enumerate(("gap", "ranking", "robust", "cpi", "multirx", "detector",
                 "anchor"), start=1)}


# --------------------------------------------------------------------------- #
#  파생 수치 — JSON 에서 **계산**한 값. 값과 태그를 한 함수가 같이 만든다.
# --------------------------------------------------------------------------- #
def dnum(value, fmt: str, unit: str, src: str, how: str) -> str:
    """`값 ⟨경로 : 키 → 어떻게⟩`. 값은 반드시 `fetch()` 로 읽은 것에서 계산한다."""
    s = fmt.format(value)
    if unit:
        s = f"{s}{unit}" if unit in "%°" else f"{s} {unit}"
    return f"{s} ⟨{src} → {how}⟩"


def cell(drone: str, mode: str, key: str):
    return fetch((J_FS, CELL.format(d=drone, m=mode) + "." + key))


def _snr50_logistic(grid, pd, p0: float) -> float:
    """Pd 곡선에 로지스틱을 적합해 SNR50 을 다시 뽑는다(격자 보간의 대조군, §4)."""
    from scipy.optimize import curve_fit
    (a, _b), _ = curve_fit(lambda x, a, b: 1.0 / (1.0 + np.exp(-(x - a) / b)),
                           np.asarray(grid, float), np.asarray(pd, float),
                           p0=[float(p0), 1.0], maxfev=40000)
    return float(a)


def dsigma(drone: str, mode: str) -> float:
    return fetch((J_AN, DSIG.format(d=drone, b=ANCHOR_BAND[mode])))


def derived() -> dict:
    """이 편이 쓰는 파생량을 한 곳에서 계산한다(전부 JSON 입력)."""
    D: dict = {}

    # ── 기하: β · 앙각이 열려 있는 창 ────────────────────────────────────────
    d = np.array(fetch((J_FS, "solve.W1.d_grid_m")), float)
    beta = np.array(fetch((J_FS, "solve.W1.beta_deg")), float)
    el = np.array(fetch((J_FS, "solve.W1.el_look_deg")), float)
    snr = np.array(fetch((J_FS, "solve.W1.snr_d_db")), float)
    D["d_beta45"] = float(np.interp(45.0, beta[::-1], d[::-1]))
    D["snr_at_beta45"] = float(np.interp(D["d_beta45"], d, snr))
    D["d_el20"] = float(np.interp(-20.0, el, d))
    #  ⭐ 유효창은 **이 편의 결과가 실제로 읽은 격자**를 말한다 — 디스크의 최신 파일이 아니다.
    #     σ 격자는 2026-08-03 에 앙각 −90° 까지 확장돼 재생성됐고, 그 새 격자 위에서 다시
    #     푸는 일은 §1.1 끝 문단과 `다음 단계` 표에 걸려 있다. 발표된 solve 가 읽은 판은
    #     아카이브에 그대로 있고, 그 신원은 `phi_sweep.json : meta.sigma_file_generated` 와
    #     `meta.generated` 가 일치하는 것으로 확정된다(아래 assert 가 매 빌드 확인한다).
    used_gen = fetch((J_SG_USED, "meta.generated"))
    assert used_gen == fetch((J_PH, "meta.sigma_file_generated")), (
        f"발표 solve 가 읽은 σ 격자를 특정하지 못했다: 아카이브 {used_gen} vs "
        f"φ 스윕 기록 {fetch((J_PH, 'meta.sigma_file_generated'))}")
    D["el_grid_min"] = float(min(fetch((J_SG_USED, "meta.el_deg"))))
    D["n_el"] = len(fetch((J_SG_USED, "meta.el_deg")))
    D["beta_at_R"] = float(np.interp(fetch((J_FS, "solve.W1.R_m")), d, beta))

    # ── 상반성 rms 잔차: β≤45° 안 / 창 밖 ──────────────────────────────────
    rows = fetch((J_DF, "d2_reciprocity_drone.rows"))
    D["recip_in"] = max(r["rms_db"] for r in rows if r["beta_deg"] <= 45)
    D["recip_out"] = max(r["rms_db"] for r in rows if r["beta_deg"] > 45)

    # ── R90: 기하 σ 해 → 앵커 Δσ 를 국소 지수로 1차 전이 ─────────────────────
    R = {(dr, m): cell(dr, m, "R90_C50_m") / 1e3 for dr in DRONES for m in MODES}
    n_loc = {(dr, m): cell(dr, m, "n_local_at_R90") for dr in DRONES for m in MODES}
    A = {k: R[k] * 10 ** (dsigma(*k) / (10 * n_loc[k])) for k in R}
    D["R90"], D["R90_anch"] = R, A
    D["n_local"] = float(np.mean(list(n_loc.values())))

    # ── 헤드라인 폭은 **앵커 비교가능 기체**에서 읽는다(02 §4.3 원장의 verdict) ──
    D["verdict"] = {dr: fetch((J_AN, f"drones.{dr}.comparability.verdict")) for dr in DRONES}
    D["comparable"] = [dr for dr in DRONES if D["verdict"][dr] != "not_comparable"]
    D["excluded"] = [dr for dr in DRONES if D["verdict"][dr] == "not_comparable"]
    Ac = {k: v for k, v in A.items() if k[0] in D["comparable"]}
    Ax = {k: v for k, v in A.items() if k[0] in D["excluded"]}
    D["A_min"], D["A_max"] = min(Ac.values()), max(Ac.values())
    D["A_min_key"], D["A_max_key"] = min(Ac, key=Ac.get), max(Ac, key=Ac.get)
    D["n_cells_comp"] = len(Ac)
    D["X_min"], D["X_max"] = min(Ax.values()), max(Ax.values())
    D["X_name"] = D["excluded"][0]
    D["X_spread"] = fetch((J_AN, f"drones.{D['X_name']}.comparability.size_law_spread_db"))

    # ── 헤딩 커버리지: 모드마다 한 값(기하·PRF·CPI 의 함수, 기체 무관) ─────────
    D["cov"] = {m: cell(DRONES[0], m, "coverage_ceiling") for m in MODES}
    D["blind"] = {m: cell(DRONES[0], m, "blind_heading_frac") for m in MODES}
    for m in MODES:                       # 기체 무관을 실제로 확인하고 쓴다
        assert len({round(cell(dr, m, "coverage_ceiling"), 9) for dr in DRONES}) == 1
    D["dop"] = {m: dict(prf=fetch((J_FS, f"waveforms.{m}.prf_hz")),
                        M=fetch((J_FS, f"waveforms.{m}.M")),
                        lam=fetch((J_FS, f"waveforms.{m}.lam_m"))) for m in MODES}
    for m in MODES:
        D["dop"][m]["guard_hz"] = 2.5 * D["dop"][m]["prf"] / D["dop"][m]["M"]
        D["dop"][m]["fold_hz"] = D["dop"][m]["prf"] / 2.0

    # ── 문턱: 세 밴드가 W1 문턱 하나를 공유한다 ────────────────────────────────
    thr = fetch((J_FS, "threshold.S_G"))
    D["snr90_shared"] = fetch((J_FS, "solve.W1.snr90_db"))
    D["snr90_L1_own"] = fetch((J_FS, "threshold.S_G.L1.1.dopoff.3.snr90_db"))
    D["snr90_L1_delta"] = D["snr90_L1_own"] - D["snr90_shared"]
    D["R_shift_L1_pct"] = (10 ** (-D["snr90_L1_delta"] / (10 * D["n_local"])) - 1.0) * 100.0
    g1 = thr["G1"]["1"]["dopoff"]
    D["G1_skipped"] = sum(1 for v in g1.values() if v.get("skipped"))
    D["G1_cells"] = len(g1)
    D["G1_M"] = fetch((J_FS, "detector_transfer.S_G.G1.N.1.dopoff.3.M"))

    # ── σ 앵커의 범위: 기울기만 옮기고 밴드 평균 레벨은 그대로 둔다 ────────────
    lv = {dr: float(np.mean([fetch((J_AN, DSIG.format(d=dr, b=b)))
                             for b in ANCHOR_BAND.values()])) for dr in DRONES}
    D["level_shift_abs_max"] = max(abs(v) for v in lv.values())
    D["size_law_spread_max"] = max(
        fetch((J_AN, f"drones.{dr}.comparability.size_law_spread_db"))
        for dr in fetch((J_AN, "drones")))

    # ── 감도사슬: 앵커 σ 를 얹은 항별 분해(Mavic 4 Pro · 1 km) ───────────────
    B = {m: cell("mavic4pro", m, "budget_terms_db") for m in MODES}
    D["budget"] = {m: dict(B[m]) for m in MODES}
    for m in MODES:
        D["budget"][m]["dsigma"] = dsigma("mavic4pro", m)
        D["budget"][m]["sigma_anch"] = B[m]["sigma"] + dsigma("mavic4pro", m)
        D["budget"][m]["total_anch"] = B[m]["total"] + dsigma("mavic4pro", m)
        D["budget"][m]["common"] = sum(
            float(B[m][k]) for k in ("eirp", "grx", "spread", "n0", "t_cpi",
                                     "eta_ref", "duty", "losses", "k_mode"))
    sa = {m: D["budget"][m]["sigma_anch"] for m in MODES}
    D["sigma_span"] = max(sa.values()) - min(sa.values())
    #   1 km 에서 밴드 쌍의 격차를 **항으로 쪼갠다** — 세 밴드에서 다른 항은 λ² 와 σ 뿐이다.
    D["gap1km"] = {}
    for a, b in (("W1", "L1"), ("W1", "G1"), ("L1", "G1")):
        D["gap1km"][f"{a}-{b}"] = dict(
            d_total=D["budget"][a]["total_anch"] - D["budget"][b]["total_anch"],
            d_lambda2=D["budget"][a]["lambda2"] - D["budget"][b]["lambda2"],
            d_sigma=D["budget"][a]["sigma_anch"] - D["budget"][b]["sigma_anch"],
            d_common=D["budget"][a]["common"] - D["budget"][b]["common"])

    # ── 순위 강건성(파생은 문자열 하나뿐: 합의 순위를 사람이 읽는 이름으로) ────
    order = fetch((J_SS, "aspect_averaged.consensus_order"))
    D["consensus_order"] = " > ".join(MODE_NAME[m] for m in order)
    D["mc"] = {dr: fetch((J_SS, f"monte_carlo_per_band_error.by_drone.{dr}.by_sigma_e_db"))
               for dr in DRONES}
    D["mc_p2db_min"] = min(float(v["2.0"]["p_order_preserved"]) for v in D["mc"].values())
    D["mc_p2db_max"] = max(float(v["2.0"]["p_order_preserved"]) for v in D["mc"].values())
    #   메쉬 갱신 하나가 옮긴 R90 — 통제되지 않은 σ 변화의 관측된 파급
    st = fetch((J_SS, "staleness_and_mesh_update.by_drone"))
    D["stale_max_pct"] = max(float(v["max_range_change_pct"]) for v in st.values())
    D["stale_flip"] = fetch((J_SS, "staleness_and_mesh_update.n_orders_changed"))

    # ── 다중 수신기: 열잡음 기준선 10log₁₀N 대비 ─────────────────────────────
    #   기준선은 **열잡음만** 상대할 때의 코히어런트 배열이득이다. 감시신호는
    #   `surv = √N·echo + dpi + noise`(`src/experiment_detection.py:284`) 이고 ECA 잔차 dpi 는
    #   N 에 무관하게 고정이라, √N 은 잡음과 잔차 양쪽 대비로 표적을 올린다. x 축 SNR 은
    #   잡음 기준 정의(`:238`)이므로 측정 이득이 기준선 위에 앉는다 — 그 초과분을 여기서 잰다.
    ns = [int(n) for n in fetch((J_RX, "meta.n_list"))]
    K = fetch((J_RX, "meta.K"))
    dev, dev_fit, mc_sig, gain = [], [], [], {}
    for mo in fetch((J_RX, "meta.modes")):
        g = np.array(fetch((J_RX, f"modes.{mo}.snr_grid")), float)
        s = [fetch((J_RX, f"modes.{mo}.curves.{n}.snr50")) for n in ns]
        sf = []
        for n in ns:                        # 로지스틱 재적합 — 격자 보간의 대조군
            p = np.array(fetch((J_RX, f"modes.{mo}.curves.{n}.Pd")), float)
            sf.append(_snr50_logistic(g, p, s[ns.index(n)]))
            j = min(max(int(np.searchsorted(p, 0.5)), 1), len(p) - 1)
            mc_sig.append(0.5 / np.sqrt(K) / max((p[j] - p[j - 1]) / (g[j] - g[j - 1]), 1e-9))
        dev += [(s[0] - v) - 10 * np.log10(n) for v, n in zip(s, ns)]
        dev_fit += [(sf[0] - v) - 10 * np.log10(n) for v, n in zip(sf, ns)]
        gain[mo] = [s[0] - v for v in s]
    D["ns"] = ns
    D["rx_K"] = int(K)
    D["rx_gain_W1"] = gain["W1"]
    D["rx_bound"] = [10 * np.log10(n) for n in ns]
    D["rx_dev_max"], D["rx_dev_min"] = float(max(dev)), float(min(dev))
    D["rx_dev_fit_max"], D["rx_dev_fit_min"] = float(max(dev_fit)), float(min(dev_fit))
    D["rx_mc_sigma"] = float(max(mc_sig))
    D["rx_excess_in_sigma"] = D["rx_dev_max"] / D["rx_mc_sigma"]

    # ── 상시 기준신호 제약의 대가(9모드 벤치, §3.6) ──────────────────────────
    D["always_on_cost"] = {}
    for std, code in (("wifi", "W"), ("lte", "L"), ("nr", "G")):
        s1 = fetch((J_RX, f"modes.{code}1.curves.1.snr50"))
        s3 = fetch((J_RX, f"modes.{code}3.curves.1.snr50"))
        D["always_on_cost"][code] = dict(
            snr50_g1=s1, snr50_g3=s3, cost_db=s1 - s3,
            bw_g1_mhz=fetch((J_RX, f"modes.{code}1.ref_bw_mhz")),
            bw_g3_mhz=fetch((J_RX, f"modes.{code}3.ref_bw_mhz")),
            dr_g1_m=fetch((J_RX, f"modes.{code}1.range_res_m")),
            dr_g3_m=fetch((J_RX, f"modes.{code}3.range_res_m")))

    # ── 벤치 스윕(§3.6·§4)의 배치 — 본문이 배치를 밝히고 인용하도록 ──────────
    D["bench"] = dict(
        fc_ghz=fetch((J_RX, "meta.fc")) / 1e9,
        Rb_m=fetch((J_RX, "modes.W1.Rb_true")),
        sigma_dbsm=fetch((J_RX, "meta.sigma_dbsm")),
        drone=fetch((J_RX, "meta.drone")),
        note="9모드 전부 단일 반송파·단일 기하·단일 σ 다 — 이 스윕이 여는 축은 파형 하나다 "
             "(src/experiment_detection.py:342).")

    # ── 링크버짓 항등식: 코드 경로 vs dB 산술 ────────────────────────────────
    lb = fetch((J_LB, "A_radar_equation.rows"))
    D["lb_rows"] = len(lb)
    D["lb_resid"] = max(abs(r["d_echo_dbarith_db"]) for r in lb)

    # ── 5G 명목 Pfa 가 경험값의 몇 배인가 ────────────────────────────────────
    D["pfa_g1_ratio"] = 1.0 / fetch((J_FS, "threshold.pfa.G1.ratio_emp_over_nominal"))

    # ── 재현 소요: 측정치 + 선언 예산 ────────────────────────────────────────
    #  ⚠ σ 격자는 2026-08-03 재생성부터 **샤드 워커**로 돈다 — 생산자가 기록하는 양이
    #     벽시계 `runtime_s` 에서 워커 CPU 시간 `worker_cpu_hours` 로 바뀌었다.
    #     둘은 다른 양이라 이름도 바꿔 싣는다(재현 블록이 "워커 CPU" 라고 말한다).
    D["t_sigma_grid"] = fetch((J_SG, "meta.worker_cpu_hours")) * 3600.0
    D["t_range_drone"] = fetch((J_FS, "meta.runtime_s"))
    D["t_verify"] = fetch((J_VF, "meta.runtime_s"))
    D["t_cpi_sweep"] = fetch((J_CG, "meta.runtime_s"))
    D["t_sigma_sens"] = fetch((J_SS, "_meta.runtime_s"))
    D["t_declared"] = float(sum(DECLARED_S.values()))
    D["t_total"] = (D["t_sigma_grid"] + D["t_range_drone"] * len(DRONES)
                    + D["t_verify"] + D["t_cpi_sweep"] + D["t_sigma_sens"]
                    + D["t_declared"])
    return D


# --------------------------------------------------------------------------- #
#  파생 원장 — 본문이 인용하는 파생 수치를 JSON 으로 내보낸다(손으로 친 숫자 0개)
# --------------------------------------------------------------------------- #
def write_derived(D: dict, t0: float) -> str:
    """`outputs/report05_derived.json` 을 쓴다. 본문의 `num()` 이 이 파일을 읽는다."""
    t_derive = round(time.time() - t0, 1)
    out = {
        "_meta": dict(
            producer="src/make_report05_results.py",
            generated=_dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            reads=[J_FS, J_SG, J_RX, J_VF, J_LB, J_AN, J_DF, J_SS, J_CG],
            paper_section="V. Results",
            runtime_s=t_derive),
        "r90": dict(
            definition="공칭 헤딩 ψ=0 에서 출력 SNR(d) 가 교정 문턱 SNR90 을 마지막으로 "
                       "하강교차하는 수평거리 d [m] (src/freespace_link.py:448 solve_range). "
                       "유효 게이트 β≤90°·원거리장을 통과한 칸에서만 해를 찾는다.",
            key=CELL + ".R90_C50_m",
            key_note="키의 `C50` 은 스펙 §2.3 의 커버리지 백분위(P_ψ[Pd≥0.9]≥0.50) 이름이고, "
                     "이 실행이 그 자리에 적은 값은 단일 헤딩 solve 의 R_m 이다 — 같은 리프의 "
                     "`note` 가 그렇게 적고 있다. 헤딩 축은 coverage_ceiling·E_psi_Pd_at_R90 "
                     "열이 따로 든다.",
            n_local_mean=D["n_local"],
            anchored_km={dr: {m: D["R90_anch"][(dr, m)] for m in MODES} for dr in DRONES},
            verdict=D["verdict"],
            comparable=D["comparable"], excluded=D["excluded"],
            n_cells_comparable=D["n_cells_comp"],
            span_comparable_min_km=D["A_min"],
            span_comparable_min_cell=f"{D['A_min_key'][0]} · {MODE_NAME[D['A_min_key'][1]]}",
            span_comparable_max_km=D["A_max"],
            span_comparable_max_cell=f"{D['A_max_key'][0]} · {MODE_NAME[D['A_max_key'][1]]}",
            excluded_min_km=D["X_min"], excluded_max_km=D["X_max"],
            excluded_size_law_spread_db=D["X_spread"],
            coverage_ceiling_by_mode={MODE_NAME[m]: D["cov"][m] for m in MODES},
            blind_heading_frac_by_mode={MODE_NAME[m]: D["blind"][m] for m in MODES},
            doppler={MODE_NAME[m]: D["dop"][m] for m in MODES},
            doppler_note="가드 반폭 = 2.5빈 × Δf_d(=PRF/M), 선언값 "
                         "(src/freespace_scene.py:82 · :222). 접힘 후 도플러 축 = ±PRF/2. "
                         "CPI 의존성은 outputs/cpi_guard_sweep.json 이 스윕으로 든다."),
        "threshold": dict(
            snr90_shared_db=D["snr90_shared"], snr90_source_mode="W1",
            note="stage_threshold 는 --mode 목록의 첫 모드에서 SNR90 을 뽑아 세 밴드 solve "
                 "전부에 넘긴다 (src/experiment_freespace_range.py:856).",
            l1_own_snr90_db=D["snr90_L1_own"], l1_delta_db=D["snr90_L1_delta"],
            l1_range_shift_pct=D["R_shift_L1_pct"],
            g1_skipped_cells=D["G1_skipped"], g1_total_cells=D["G1_cells"], g1_M=D["G1_M"]),
        "anchor_scope": dict(
            from_measurement="A(f) 의 주파수 기울기 [dB/GHz]",
            from_ours="절대 레벨 A(f)|_mean · 자세 패턴 B₁(φ,θ)",
            production_mode="slope_only",
            level_shift_abs_max_db=D["level_shift_abs_max"],
            size_law_spread_max_db=D["size_law_spread_max"],
            why=("레벨까지 앵커에 맞추려면 크기전이 법칙을 하나 골라야 하고, 그 선택이 "
                 f"기체에 따라 최대 {D['size_law_spread_max']:.2f} dB 를 정한다. 측정이 그 "
                 "대가 없이 제약하는 양은 기울기뿐이므로 기울기만 받는다 "
                 "(02 §4.1 과 같은 문장).")),
        "gap_1km": dict(
            d_ref_m=D["budget"]["W1"]["d_ref_m"],
            drone="mavic4pro",
            by_mode={m: {k: D["budget"][m][k] for k in
                         ("common", "lambda2", "sigma_anch", "total_anch")}
                     for m in MODES},
            by_pair=D["gap1km"],
            note="세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다 — 나머지(EIRP·수신이득·확산·"
                 "1/N₀·CPI·듀티·손실·모드보정)는 세 밴드가 같은 값을 쓴다."),
        "ranking": dict(
            consensus_order_aspect_avg=D["consensus_order"],
            mc_p_order_preserved_at_2db_min=D["mc_p2db_min"],
            mc_p_order_preserved_at_2db_max=D["mc_p2db_max"],
            note="설정별 순위·뒤집힘 문턱의 원장은 outputs/sigma_sensitivity.json 이다 "
                 "(configurations.by_config)."),
        "always_on_cost": dict(D["always_on_cost"],
                               note="9모드 벤치(단일 반송파·단일 σ)에서 상시 기준신호(등급 1) "
                                    "대비 세션 기준신호(등급 3)의 Pd=0.5 요구 SNR 차이."),
        "bench": dict(D["bench"]),
        "rx_gain": dict(
            reference_line="10log10(N) — 열잡음만 상대할 때의 코히어런트 배열이득",
            measured="SNR50(1) − SNR50(N), x 축 SNR 은 잡음 기준 정의",
            why_above="surv = √N·echo + dpi + noise 에서 ECA 잔차 dpi 가 N 에 무관하게 "
                      "고정이라 √N 이 잔차 대비로도 표적을 올린다 "
                      "(src/experiment_detection.py:284 · 238).",
            idealisation="조향벡터는 참 표적 방향에 정확히 맞고, 소자 간 결합·교정오차·"
                         "위치오차는 0 이다 — 상한이 '이상적'인 이유가 이것이다.",
            K=D["rx_K"], n_list=D["ns"],
            excess_min_db=D["rx_dev_min"], excess_max_db=D["rx_dev_max"],
            excess_fit_min_db=D["rx_dev_fit_min"], excess_fit_max_db=D["rx_dev_fit_max"],
            snr50_mc_sigma_db=D["rx_mc_sigma"], excess_in_sigma=D["rx_excess_in_sigma"]),
        "runtime": dict(
            sigma_grid_s=D["t_sigma_grid"], range_per_drone_s=D["t_range_drone"],
            n_drones=len(DRONES), verify_freespace_s=D["t_verify"],
            cpi_guard_sweep_s=D["t_cpi_sweep"], sigma_sensitivity_s=D["t_sigma_sens"],
            declared_s=D["t_declared"], declared_breakdown_s=dict(DECLARED_S),
            declared_source="benchmark/regen_mesh_dependents.py:77 · :101 · :113",
            derive_s=t_derive,
            total_s=D["t_total"] + t_derive, total_h=(D["t_total"] + t_derive) / 3600.0),
        "legacy_numbering": {
            "report13_freespace.json": "05편 자유공간 검지거리 (옛 13편 번호)",
            "report13_sigma_grid.json": "05편 σ 격자 (옛 13편 번호)",
            "report2_waveform_rcs.json": "02편 RCS 스윕 (옛 2편 번호)",
            "report5_results.json": "옛 5편 잔재 — 이 편은 읽지 않는다"},
    }
    p = os.path.join(ROOT, J_DV)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    _rs._JSON_CACHE.pop(os.path.normpath(p), None)      # 방금 쓴 파일을 다시 읽게
    return p


# --------------------------------------------------------------------------- #
#  논문 부품 (PAPER_SPEC §4) — 대응 · 방어선 · 방법 문단 · 인용
# --------------------------------------------------------------------------- #
def paper_blocks(D: dict):
    """§4.1 대응 블록과 §4.2·4.4·4.5 부록 블록을 만든다."""
    SS, CG = from_json(J_SS), from_json(J_CG)
    DV, RX = from_json(J_DV), from_json(J_RX)

    #: 방어선 표가 쓰는 파생 두 개 — 값은 전부 JSON 에서 읽어 계산한다(손입력 0).
    #  ① 공통모드 봉투가 순위를 지키는 칸 수 = 기체 수 × 밴드 수
    n_cm_cells = len(SS.get("common_mode.by_drone")) * len(MODES)
    #  ② R90 경로가 실제로 적용한 듀티 항 — 세 밴드가 같은 값이라는 것까지 확인하고 쓴다
    duty_applied = [fetch((J_FS, CELL.format(d="mavic4pro", m=m) + ".budget_terms_db.duty"))
                    for m in MODES]
    assert len(set(duty_applied)) == 1, f"듀티 항이 밴드마다 다르다: {duty_applied}"
    SRC_DUTY = (f"{J_FS} : " + CELL.format(d="mavic4pro", m="*")
                + ".budget_terms_db.duty")

    pmap = paper_map(
        "V. Results",
        claim="같은 표적·같은 기하·하나의 교정 문턱에서 세 조명원을 비교하면, 자세평균 σ 와 "
              "측정 기울기 위에서 다섯 기체가 하나의 파형 순위에 합의하고 그 순위는 공통모드 "
              "σ 오차 ±10 dB 에서 불변이다.",
        evidence=["그림 1", "그림 4", "그림 5",
                  "outputs/sigma_sensitivity.json:aspect_averaged.all_drones_agree",
                  "outputs/sigma_sensitivity.json:common_mode.order_invariant_everywhere",
                  "outputs/cpi_guard_sweep.json:equal_cpi_penalty[0].ratio_G1_over_W1"],
        qualifications=[
            "순위는 **자세평균 + 기울기 앵커** 설정의 것이다 — 단일 자세에서는 다섯 기체가 "
            + SS.num("ranking_consensus.single_aspect_n_distinct", None, "{:.0f}")
            + " 가지 순위를 낸다",
            "밴드별 차분 σ 오차가 "
            + SS.num("configurations.by_config.aspect_avg_anchored.worst_flip_span_db", None,
                     "{:.2f}", "dB")
            + " 를 넘으면 순위가 바뀐다 — 기체별 문턱을 §3.4 표에 싣는다",
            "듀티 축을 켠 설정은 순위 합의가 "
            + SS.num("configurations.by_config.aspect_avg_anchored_duty.n_distinct_orders",
                     None, "{:.0f}")
            + " 가지로 갈린다 — 그 크기를 §2.2 에 적는다",
            "바이스태틱은 β ≤ 45° 에서 성립한다"],
        report="report05_results")

    meth = methods(
        "Detection range is solved in free space for a bistatic pair with baseline "
        f"L = {fetch((J_FS, 'solve.W1.L_m')):.0f} m, target altitude "
        f"{fetch((J_FS, 'solve.W1.alt_m')):.0f} m, scene azimuth "
        f"{fetch((J_FS, 'solve.W1.phi_deg')):.0f} deg, declared EIRP "
        f"{fetch((J_FS, 'meta.link_budget.eirp_dbm')):.0f} dBm, receive gain "
        f"{fetch((J_FS, 'meta.link_budget.rx_gain_dbi')):.0f} dBi, noise figure "
        f"{fetch((J_FS, 'meta.link_budget.noise_figure_db')):.0f} dB, CPI "
        f"{fetch((J_FS, 'solve.W1.T_cpi_s')) * 1e3:.0f} ms and N = 1 receive element. "
        "The three illuminators are the always-on reference signal of each standard "
        "(WiFi VHT-LTF at " + f"{fetch((J_FS, 'waveforms.W1.fc_hz')) / 1e9:.2f} GHz, "
        "LTE CRS at " + f"{fetch((J_FS, 'waveforms.L1.fc_hz')) / 1e9:.3f} GHz, "
        "5G NR SSB at " + f"{fetch((J_FS, 'waveforms.G1.fc_hz')) / 1e9:.1f} GHz), each "
        "correlated over its own reference bandwidth, at equal power spectral density. "
        "The threshold is set by driving the empirical false-alarm rate to "
        f"{fetch((J_FS, 'threshold.pfa.W1.target')):.0e} in the same free-space geometry, "
        "and the threshold measured for WiFi is shared by all three solves. Cross "
        "sections come from a per-part material physical-optics kernel with ray-traced "
        "occlusion evaluated on an aspect grid; the frequency slope of the azimuth-mean "
        "level is anchored to the measured "
        f"{fetch((J_AN, 'sources.anchors.das_phantom3_mono.a')):.3f} dB/GHz of Das et al. "
        "while the aspect "
        "pattern and the three-band mean level are computed. Bistatic results hold for "
        "beta <= 45 deg. Doppler blindness is evaluated over "
        f"{fetch((J_CG, 'meta.psi_n_fine')):.0f} headings at "
        f"{fetch((J_CG, 'meta.geometry.speed_ms')):.0f} m/s with a zero-Doppler guard of "
        f"{fetch((J_CG, 'structural.guard_bins_hard')):.1f} bins (applied) and "
        f"{fetch((J_CG, 'structural.guard_bins_declared')):.1f} bins (declared).",
        tools=["Python 3.12.13", "NumPy 2.5.0", "Matplotlib 3.11.0", "PyTorch 2.12.1",
               "Sionna 2.0.1"],
        report="report05_results")

    dfn = defence([
        ("동일 점유 규약에서 밴드 간 출력 SNR 차이는 λ² 와 σ 두 항에서만 나온다.",
         "그림 1 · `outputs/report05_derived.json:gap_1km.by_pair`",
         "점유·듀티 대가를 뺀 비교이므로 SSB 의 낮은 점유가 5G 에 유리하게 작용했다",
         "이 사슬은 기준신호가 CPI 전체를 채운다는 규약에서 풀려 듀티 항이 세 밴드 모두 "
         + dnum(duty_applied[0], "{:.0f}", "dB", SRC_DUTY, "세 밴드 같은 값")
         + " 다. 그 항을 켜면 5G 가 LTE 대비 "
         + SS.num("unapplied_duty_axis.pair_gaps_db.L1-G1", None, "{:.2f}", "dB")
         + " 를 더 치르고, 그 설정의 순위까지 §3.3 표가 든다 "
         "⟨outputs/sigma_sensitivity.json : unapplied_duty_axis⟩"),
        ("자세평균 σ 와 측정 기울기 위에서 다섯 기체가 하나의 파형 순위에 합의한다.",
         "그림 4 · `outputs/sigma_sensitivity.json:aspect_averaged.all_drones_agree`",
         "단일 자세 결과에서는 기체마다 순위가 달랐다 — 어느 쪽이 결론인가",
         "결론은 자세평균 설정의 순위다. 단일 자세는 "
         + SS.num("ranking_consensus.single_aspect_n_distinct", None, "{:.0f}")
         + " 가지 순위를 내고, 그 차이를 만드는 것이 "
         "자세별 로브 구조라는 것을 같은 표가 보여준다"),
        ("공통모드 σ 오차 ±10 dB 에서 순위는 "
         + dnum(n_cm_cells, "{:.0f}", "", f"{J_SS} : common_mode.by_drone", "기체 × 밴드")
         + " 칸 전부 유지되고 절대거리만 dB/4 로 움직인다.",
         "그림 5(a) · `outputs/sigma_sensitivity.json:common_mode.order_invariant_everywhere`",
         "σ 절대레벨이 측정으로 검증되지 않았는데 거리를 인용할 수 있나",
         "공통으로 움직이는 부분은 순위에서 상쇄되고 거리만 옮긴다 — ±10 dB 에서 "
         + num(None, (J_SS, "common_mode.abs_range_shift_at_10db_pct.minus10"), "{:+.1f}", "%")
         + " / "
         + num(None, (J_SS, "common_mode.abs_range_shift_at_10db_pct.plus10"), "{:+.1f}", "%")
         + " 다. ⚠ 다만 σ 오차를 **완전한** 공통모드로 볼 근거는 아직 "
         "얇다 — PO 근사가 무너지는 문턱은 부품마다 다른 주파수에 있어서(02 §3.1a) 밴드마다 "
         "다르게 들어간다 ⟨outputs/lowfreq_attack.json : q5_blast_radius."
         "po_validity_blast_radius_the_real_one⟩. 그 밴드 간 차이의 크기를 재는 것이 06편 "
         "캠페인 §4-1 이고, 그때까지 km 표는 순위용으로만 읽는다"),
        ("밴드별 차분 σ 오차가 순위를 뒤집는 문턱은 기체 속성이고 자세평균 앵커 설정에서 "
         + SS.num("configurations.by_config.aspect_avg_anchored.worst_flip_span_db", None,
                  "{:.2f}", "dB")
         + " 다.",
         "그림 5(b) · `outputs/sigma_sensitivity.json:configurations.by_config."
         "aspect_avg_anchored.worst_flip_span_db`",
         "현실 차분오차 봉투 "
         + SS.num("differential.realistic_span_db", None, "{:.2f}", "dB")
         + " 가 그 문턱보다 크다",
         "그래서 순위를 기체별 문턱과 함께 싣는다 — 그 봉투 안에 들어가는 것은 다섯 중 "
         + SS.num("configurations.by_config.aspect_avg_anchored."
                  "n_drones_flipping_inside_realistic", None, "{:.0f}")
         + " 기체이고, "
         "몬테카를로 순위보존 확률이 같은 순서를 준다 "
         "⟨outputs/sigma_sensitivity.json : monte_carlo_per_band_error⟩. ⚠ 이 문턱들은 "
         + num(None, (J_MFX, "_meta.date"))
         + " 형상 정정 전 메쉬 위의 값이다 — 다섯 기체 중 Matrice 4E 가 그 정정을 받았다"
         "(방법 «밴드 비교» · 02 §5)"),
        ("5G 의 도플러 가드 대가는 CPI 의 함수이고 전 헤딩 블라인드는 M ≤ 2g 에서 성립한다.",
         "그림 6 · `outputs/cpi_guard_sweep.json:structural.formula`",
         "CPI " + CG.num("equal_cpi_penalty[0].T_cpi_s", None, "{:.1f}", "s")
         + " 한 점에서 커버리지 0 이라고 적은 결과는 규약이 만든 인공물이다",
         "그 점은 " + CG.num("structural.guard_bins_declared", None, "{:.1f}")
         + " 빈 선언가드에서 CPI "
         + CG.num("structural.by_mode.G1.T_max_total_blind_declared_s", None, "{:.2f}", "s")
         + " 이하일 때 성립하고, 검출기가 적용하는 "
         + CG.num("structural.guard_bins_hard", None, "{:.1f}")
         + " 빈 규약에서는 같은 CPI 에서 가려지는 헤딩 비율이 "
         + CG.num("verdict.artifact.blind_hard_same_cpi", None, "{:.3f}")
         + ", CPI " + CG.num("equal_cpi_penalty[1].T_cpi_s", None, "{:.1f}", "s")
         + " 에서 " + CG.num("verdict.artifact.blind_hard_at_200ms", None, "{:.3f}")
         + " 다 — WiFi 대비 배수 "
         + CG.num("equal_cpi_penalty[0].ratio_G1_over_W1", None, "{:.2f}")
         + " 는 CPI 전 구간에 남으므로 스윕으로 싣는다"),
        ("5G 가 WiFi 수준의 헤딩 커버리지에 도달하려면 CPI "
         + CG.num("cost_of_long_cpi.required_cpi_s.to_WiFi_parity", None, "{:.1f}", "s")
         + " 가 필요하고, 그 CPI 는 표적 속도 "
         + CG.num("cost_of_long_cpi.by_speed[6].speed_ms", None, "{:.0f}", "m/s")
         + " 까지 코히어런스 한계 안에 있다.",
         "그림 6(b) · `outputs/cpi_guard_sweep.json:cost_of_long_cpi`",
         "CPI 를 늘리면 되는 문제라면 구조적 대가가 아니다",
         "대가는 재방문 시간이다 — LTE 패리티에 "
         + CG.num("cost_of_long_cpi.at_required_cpi.v5_LTE_parity.elapsed_vs_headline",
                  None, "{:.2f}")
         + " 배, WiFi 패리티에 "
         + CG.num("cost_of_long_cpi.at_required_cpi.v5_WiFi_parity.elapsed_vs_headline",
                  None, "{:.0f}")
         + " 배의 경과시간을 치르고, "
         + CG.num("cost_of_long_cpi.by_speed[7].speed_ms", None, "{:.0f}", "m/s")
         + " 이상에서 WiFi 패리티는 코히어런스 한계를 넘어선다"),
        ("수신소자 이득은 열잡음 코히어런트 상한 10log₁₀N 위에 "
         + DV.num("rx_gain.excess_min_db", None, "{:+.2f}")
         + " ~ " + DV.num("rx_gain.excess_max_db", None, "{:+.2f}", "dB")
         + " 로 앉는다.",
         "그림 7 · `outputs/report05_derived.json:rx_gain.excess_max_db`",
         "상한을 넘는 이득은 계산 오류다",
         "그 상한은 열잡음만 상대할 때의 값이고, ECA 잔차가 N 에 무관하게 고정이라 √N 이 "
         "잔차 대비로도 표적을 올린다(`src/experiment_detection.py:284`). 최대 초과분은 "
         "SNR50 몬테카를로 표준편차의 "
         + DV.num("rx_gain.excess_in_sigma", None, "{:.1f}")
         + " 배이고 로지스틱 재적합에서도 같은 부호다"),
        ("상시 기준신호만 쓰는 제약의 대가는 5G 에서 "
         + DV.num("always_on_cost.G.cost_db", None, "{:.2f}", "dB")
         + " 이고 거리분해능 "
         + DV.num("always_on_cost.G.dr_g1_m", None, "{:.2f}", "m") + " 대 "
         + DV.num("always_on_cost.G.dr_g3_m", None, "{:.2f}", "m") + " 다.",
         "그림 2(b) · `outputs/report05_derived.json:always_on_cost.G`",
         "그 벤치는 단일 반송파·단일 σ 라 자유공간 결과와 축이 다르다",
         "그래서 그 절은 파형 축 하나의 상대 비교로 읽는다 — 표적·기하·σ 를 한 값으로 묶은 "
         "배치를 §3.6 이 밝힌다 ⟨outputs/report05_derived.json : bench⟩"),
        ("바이스태틱 결과는 β ≤ 45° 에서 성립하고 헤드라인 거리의 β 는 "
         + dnum(D["beta_at_R"], "{:.2f}", "°", f"{J_FS} : solve.W1.beta_deg", "R90 에서 보간")
         + " 다.",
         "표 · `outputs/sbr_defect_fixes.json:d2_reciprocity_drone.rows`",
         "β 창 밖의 자세는 어떻게 되나",
         "창 밖(β > 45°) 행에서 상반성 rms 잔차가 최대 "
         + dnum(D["recip_out"], "{:.2f}", "dB", f"{J_DF} : d2_reciprocity_drone.rows",
                "β>45 행 최대")
         + " 로 창 안의 "
         + dnum(D["recip_in"], "{:.2f}", "dB", f"{J_DF} : d2_reciprocity_drone.rows",
                "β≤45 행 최대")
         + " 보다 크므로 그 창을 방법 조건으로 "
         "명시하고, 창을 넓히는 일을 다음 단계 표에 둔다"),
    ], report="report05_results")

    cites = [
        cite_ref("das", note="Table III · "
                 f"{fetch((J_AN, 'sources.anchors.das_phantom3_mono.a')):.3f} dB/GHz "
                 "기울기 앵커 (§3.2)"),
        cite("3GPP", "Evolved Universal Terrestrial Radio Access (E-UTRA); "
                     "Physical channels and modulation", "3GPP TS 36.211",
             status="standard",
             note="CRS §6.10.1.2 · PRS §6.10.4.2 — `src/waveforms.py:344·351`"),
        cite("3GPP", "NR; Physical channels and modulation", "3GPP TS 38.211",
             status="standard", note="SSB §5.3.1 — `src/waveforms.py:378`"),
        cite("IEEE", "Wireless LAN Medium Access Control (MAC) and Physical Layer "
                     "(PHY) Specifications", "IEEE Std 802.11-2016", status="standard",
             note="VHT-LTF §21.3.7 — `src/waveforms.py:263`"),
        cite_ref("rzewuski",
                 note="같은 산출물(드론 RCS → 패시브 커버리지)을 FDTD 로 낸 선행 — 이 편의 "
                      "기여는 엔진과 통합, 그리고 교정된 Pfa 위의 통제 비교다"),
    ]
    return pmap, paper_appendix(defence_block=dfn, methods_block=meth, citations=cites)


# --------------------------------------------------------------------------- #
#  블록
# --------------------------------------------------------------------------- #
def build_blocks(D: dict):
    FS, RX, AN = from_json(J_FS), from_json(J_RX), from_json(J_AN)
    VF, SS, CG = from_json(J_VF), from_json(J_SS), from_json(J_CG)
    DV = from_json(J_DV)
    TM, TA, PH, SV = (from_json(J_TM), from_json(J_TA),
                      from_json(J_PH), from_json(J_SV))
    LFA, MFX = from_json(J_LFA), from_json(J_MFX)
    from_json(J_MFX_ATK)              # 형상 정정 단서가 경로로 가리킨다 — 존재 검사

    #: φ 스윕에서 이 편이 읽는 가지 — 경로가 길어 한 번만 적는다
    PHC = "verdict.claims[2].range_over_phi"
    #: 표적모형 세 팔의 요구 추가이득 경로(추정량별)
    TAE = "Q1_normalisation.recomputed_spread_db_by_matching_estimator"

    SRC_R = f"출처 ⟨{J_FS} : " + CELL.format(d="*", m="*") + ".R90_C50_m⟩"
    SRC_A = f"출처 ⟨{J_AN} : drones.*.modes.slope_only.delta_db⟩"
    SRC_B = f"출처 ⟨{J_FS} : " + CELL.format(d="mavic4pro", m="*") + ".budget_terms_db⟩"

    def B(m, k, f="{:+.2f}"):
        return f.format(D["budget"][m][k])

    pmap, appendix = paper_blocks(D)
    blocks = []

    # ── 여는 블록 (+ §4.1 논문 대응: 셀을 늘리지 않고 여는 블록 안으로) ────── #
    blocks.append(attach(header(
        num=5,
        title="검출 결과: 세 조명원을 하나의 교정 문턱 위에서 비교했다",
        did="같은 표적·같은 기하·하나의 교정 문턱에서 세 조명원의 검출거리를 재고, 그 순위가 "
            "σ 오차와 CPI 아래에서 어디까지 유지되는지 스윕으로 확정했다.",
        results=[
            f"밴드 간 출력 SNR 차이를 만드는 항은 λ² 와 σ 둘뿐이다 — 1 km·Mavic 4 Pro 에서 "
            f"WiFi−LTE 격차 {DV.num('gap_1km.by_pair.W1-L1.d_total', None, '{:+.2f}', 'dB')} 는 "
            f"λ² {DV.num('gap_1km.by_pair.W1-L1.d_lambda2', None, '{:+.2f}', 'dB')} 와 "
            f"σ {DV.num('gap_1km.by_pair.W1-L1.d_sigma', None, '{:+.2f}', 'dB')} 의 합이고, "
            f"15개 밴드쌍 중 "
            f"{SS.num('gap_decomposition.n_pairs_sigma_dominates', None, '{:.0f}')}쌍에서 σ 항이 더 크다.",
            f"자세평균 σ 와 측정 기울기 위에서 다섯 기체가 하나의 순위 "
            f"({DV.num('ranking.consensus_order_aspect_avg', None)}) 에 합의한다 — 단일 자세에서는 "
            f"{SS.num('ranking_consensus.single_aspect_n_distinct', None, '{:.0f}')}가지 순위가 나온다.",
            f"그 순위는 공통모드(세 밴드가 같은 방향으로 같은 만큼 틀리는 경우) σ 오차 "
            f"±10 dB 에서 15칸 전부 유지되고, 절대거리만 "
            f"{SS.num('common_mode.abs_range_shift_at_10db_pct.minus10', None, '{:+.1f}', '%')} ~ "
            f"{SS.num('common_mode.abs_range_shift_at_10db_pct.plus10', None, '{:+.1f}', '%')} 움직인다. "
            f"밴드별 차분 오차의 뒤집힘 문턱은 "
            f"{SS.num('configurations.by_config.aspect_avg_anchored.worst_flip_span_db', None, '{:.2f}', 'dB')} 다. "
            f"⚠ 위 세 줄이 든 σ 민감도와 §3.2·§3.3 의 앵커 σ 는 {MFX.num('_meta.date', None)} 형상 정정 "
            f"전 메쉬 위에 있다 — 다섯 기체 중 Matrice 4E 가 그 정정을 받았다(방법 «밴드 비교»).",
            f"5G SSB 의 눈먼 헤딩 비율은 CPI "
            f"{CG.num('equal_cpi_penalty[0].T_cpi_s', None, '{:.1f}', 's')} 에서 "
            f"{CG.num('verdict.artifact.blind_hard_same_cpi', None, '{:.3f}')}, CPI "
            f"{CG.num('equal_cpi_penalty[1].T_cpi_s', None, '{:.1f}', 's')} 에서 "
            f"{CG.num('verdict.artifact.blind_hard_at_200ms', None, '{:.3f}')} 로 내려가고, WiFi "
            f"대비 배수는 CPI 전 구간에서 "
            f"{CG.num('equal_cpi_penalty[0].ratio_G1_over_W1', None, '{:.1f}')}~"
            f"{CG.num('equal_cpi_penalty[3].ratio_G1_over_W1', None, '{:.1f}', '배')} 로 남는다 — "
            f"모호속도 {CG.num('unambiguous_speed.G1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} 는 "
            f"CPI 와 무관한 상한이다.",
            f"수신소자 N 의 측정 이득은 이상적 코히어런트 상한 10log₁₀N 대비 "
            f"{DV.num('rx_gain.excess_min_db', None, '{:+.2f}')} ~ "
            f"{DV.num('rx_gain.excess_max_db', None, '{:+.2f}', 'dB')} 이고, 기하·규약 게이트 "
            f"{VF.num('summary.n_ran', None, '{:.0f}')}건이 전부 통과했다"
            f"(실패 {VF.num('summary.n_fail', 0, '{:.0f}')}건).",
        ],
        method=[
            ("R90 정의",
             "공칭 헤딩 ψ=0 의 σ 로 SNR(d) 를 만들고, 유효 게이트"
             "(β≤90°·원거리장 — 파면이 평면으로 보일 만큼 먼 거리)를 통과한 칸에서 "
             "교정 문턱과의 **최외곽 하강교차**를 찾는다 — 헤딩 축은 §3.5 의 CPI 스윕이 든다"),
            #: ⭐ 이 다섯 수는 영문 방법 문단이 쓰는 것과 같은 원장 자리에서 받는다 — 손입력 0.
            ("검출거리",
             "선언 예산(EIRP "
             + FS.num("meta.link_budget.eirp_dbm", None, "{:.0f}", "dBm") + " · 수신이득 "
             + FS.num("meta.link_budget.rx_gain_dbi", None, "{:.0f}", "dBi") + " · NF "
             + FS.num("meta.link_budget.noise_figure_db", None, "{:.0f}", "dB")
             + " — NF 는 수신기가 스스로 더하는 잡음의 양) · 베이스라인 "
             + FS.num("solve.W1.L_m", None, "{:.0f}", "m") + " · CPI "
             + FS.num("solve.W1.T_cpi_s", None, "{:.1f}", "s") + " 아래에서 푼다"),
            ("밴드 비교",
             "σ = A(f)·B₁(φ,θ) 에서 **A(f) 의 기울기만** Das 측정(IEEE WCL 2026 15:3731)에 맞춘 "
             "원장 위에서 한다. 절대 레벨은 우리 PO 출력이고, 생산 모드 `slope_only` 의 세 밴드 평균 "
             "레벨이동은 " + DV.num("anchor_scope.level_shift_abs_max_db", None, "{:.2f}", "dB")
             + f" 다(02 §4). ⚠ **이 앵커 원장(`{J_AN}`)과 순위 민감도(`{J_SS}`)도 "
             + MFX.num("_meta.date", None)
             + " 형상 정정 전 메쉬 위에 서 있다** — 다섯 기체 중 Matrice 4E 가 그 정정을 받았고, "
             "§2 의 σ 항 · §3.2 의 Δσ 표 · §3.3 의 R90 표 · §3.4 의 뒤집힘 문턱이 같은 사슬 "
             f"위에 있다(02 §4.2 · §5) ⟨{J_MFX_ATK} : Q6_invalidated_outputs.critical[3]⟩"),
            ("σ 격자 출처",
             "R90 은 " + FS.num("meta.generated", None)
             + " 산출이고 그때의 `outputs/report13_sigma_grid.json` 을 읽었다"
             + f"(⟨{J_FS} : meta.sigma_file⟩). 같은 설정으로 재생성한 1:1 대조에서 기체당 최대 "
             + SV.num("overstated[0].결과_표[0].max_abs_delta_db", None, "{:.2f}", "dB")
             + " · rms " + SV.num("overstated[0].결과_표[0].rms_delta_db", None, "{:.2f}", "dB")
             + " 로 갈리고, 평균이동은 기체마다 "
             + SV.num("overstated[0].결과_표[0].mean_delta_db", None, "{:+.2f}") + " ~ "
             + SV.num("overstated[0].결과_표[2].mean_delta_db", None, "{:+.2f}", "dB")
             + " 로 방향이 갈린다 — 그래서 절대 R90 과 기체간 순위는 재생성 격자 위에서 다시 "
             "세운다(다음 단계). ⚠ 그 뒤로 형상 정정이 한 번 더 있었다("
             + MFX.num("_meta.date", None)
             + ", Matrice 4E · Mini 2 · X500 V2). 즉 이 격자는 **두 세대** 낡았고, 다섯 기체 중 "
             "Matrice 4E 가 그 정정을 받은 기체다 ⟨outputs/meshfix_applied.json : per_drone⟩. "
             "순위 비교의 규약과 봉투는 §3.4 가 든다"),
            ("순위",
             "**자세평균 σ + 측정 기울기** 설정에서 읽는다. 단일 자세·듀티 적용 등 5개 설정의 "
             "순위와 뒤집힘 문턱을 §3.4 표가 나란히 싣는다"),
            ("문턱",
             "자유공간 형상에서 경험 Pfa 를 1e-4 에 맞춰 문턱을 잡는다 — 04편의 교정표는 챔버 형상 "
             "값이라 형상마다 다시 잰다(`src/freespace_detect.py:711`)"),
            ("바이스태틱",
             "β ≤ 45° 에서 푼다 — 헤드라인 거리의 β 는 "
             + dnum(D["beta_at_R"], "{:.2f}", "°", f"{J_FS} : solve.W1.beta_deg", "R90 에서 보간")),
            ("도플러 가드",
             "가드 반폭 = g빈 × PRF/M 이고 g 는 검출기 적용값 1.5빈과 선언값 2.5빈 둘 다 잰다. "
             "헤딩 격자 720점 · 속도 5 m/s(`benchmark/cpi_guard_sweep.py`)"),
            ("다중 수신기",
             "한 지점 λ/2 ULA 소자 N 개, 조향은 참 표적 방향. 10log₁₀N 은 **열잡음만** 상대할 때의 "
             "코히어런트 배열이득이고, 측정량은 그 위에서 읽는다(§4)"),
        ],
        prereq=[("02 §4", "A(f) 기울기는 측정에서, 레벨과 B₁ 은 우리 계산에서 오는 경계"),
                ("03 §2", "조명원의 dB 원장 — 점유 · λ² · 듀티 · PRF"),
                ("04", "CFAR 문턱, 경험 Pfa 교정, ECA 잔차")],
        repro=dict(
            cmd=["cd /workspace/sionna",
                 "# ① σ 격자(자세 × 밴드)",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py",
                 "# ② 검지거리 4단계 — 기종마다 1회(결과는 add-only 로 쌓인다)",
                 "for D in mini5pro mavic4pro matrice4e phantom4 s1000plus; do \\",
                 "  PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_range.py \\",
                 "    --stage all --mode W1,L1,G1 --drone $D; done",
                 "# ③ 기하·규약 게이트 · 레이더 방정식 항등식 · β 창",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_freespace.py",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/verify_sbr_defect_fixes.py",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_linkbudget.py",
                 "# ④ 파형 9모드 × 수신소자 N 몬테카를로",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_detection.py",
                 "# ⑤ σ 민감도(순위 강건성) · 5G 도플러 가드 CPI 스윕",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/sigma_sensitivity.py",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/cpi_guard_sweep.py",
                 "# ⑥ 앵커 재보정 · 게재규격 그림 7장 · 이 노트북(+ report05_derived.json)",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/sigma_anchor.py",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report05_paper.py",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report05_results.py"],
            out=[J_FS, J_SG, J_RX, J_VF, J_LB, J_DF, J_AN, J_SS, J_CG, J_DV],
            runtime="① 워커 CPU " + DV.num("runtime.sigma_grid_s", None, "{:.0f}", "s")
                    + " · ② 기종당 " + DV.num("runtime.range_per_drone_s", None, "{:.0f}", "s")
                    + f" × {DV.num('runtime.n_drones', None, '{:.0f}')}기종"
                    + f"(GPU {FS.num('meta.gpus', None)}장) · ③ "
                    + DV.num("runtime.verify_freespace_s", None, "{:.2f}", "s")
                    + " · ④ 선언 예산 " + DV.num("runtime.declared_s", None, "{:.0f}", "s")
                    + "⟨`benchmark/regen_mesh_dependents.py:77·101·113`⟩ · ⑤ "
                    + DV.num("runtime.sigma_sensitivity_s", None, "{:.1f}", "s") + " + "
                    + DV.num("runtime.cpi_guard_sweep_s", None, "{:.1f}", "s")
                    + " · ⑥ 파생계산 " + DV.num("runtime.derive_s", None, "{:.1f}", "s")
                    + " — **합계 " + DV.num("runtime.total_h", None, "{:.1f}", "h") + "**",
            note="②는 add-only 다 — 한 기종만 다시 돌려도 나머지 칸은 남는다. 파일명의 "
                 "`report13_*` 는 옛 13편 번호이고 이 편(05)의 자유공간 산출이다 — 대응표는 "
                 "`outputs/report05_derived.json : legacy_numbering` 에 있다.",
        ),
    ), pmap))

    # ── §1 기하 ───────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §1. 기하 — TX · RX · 표적을 어디에 두었나",
        "",
        "조명원(TX)과 패시브 수신기(RX)를 지상에 고정하고, 표적을 두 점의 중점에서 수평거리 "
        "`d` 만큼 떨어진 공중에 둔다. 좌표 상수 `src/freespace_scene.py:72`, "
        "기하 함수 `src/freespace_scene.py:117`.",
        "",
        table(["항목", "값", "무엇을 정하나"],
              [["베이스라인 $L$", FS.num("solve.W1.L_m", 500.0, "{:.0f}", "m"), "β(d) 와 직접파 세기"],
               ["표적 고도", FS.num("solve.W1.alt_m", 60.0, "{:.0f}", "m"), "이등분선 앙각 el"],
               ["장면 방위 $\\varphi$", FS.num("solve.W1.phi_deg", 90.0, "{:.0f}", "°"), "R1 · R2 의 비"],
               ["EIRP · 수신이득 · NF",
                FS.num("meta.link_budget.eirp_dbm", 63.0, "{:.0f}", "dBm") + " · "
                + FS.num("meta.link_budget.rx_gain_dbi", 10.0, "{:.0f}", "dBi") + " · "
                + FS.num("meta.link_budget.noise_figure_db", 5.0, "{:.0f}", "dB"),
                "선언 예산 — 잡음바닥과 절대 거리 축"],
               ["CPI", FS.num("solve.W1.T_cpi_s", 0.1, "{:.1f}", "s"), "프레임 수 M = CPI·PRF"],
               ["기준채널",
                FS.num("meta.link_budget.power_normalization.canonical_reference", None),
                "상관에 쓸 수 있는 에너지"]]),
        "<!--cell-->",
        "### §1.1 유효창 — β 와 앙각이 어디까지 열려 있나",
        "",
        f"헤드라인 거리에서 β = "
        f"{dnum(D['beta_at_R'], '{:.2f}', '°', f'{J_FS} : solve.W1.beta_deg', 'R90 에서 보간')} "
        "로 준모노스태틱이고, σ 는 이등분선 방향의 모노스태틱 값을 쓴다"
        "(`src/experiment_freespace_sigma.py:227`). 아래 창이 이 편의 **방법 조건**이다.",
        "",
        table(["창", "성립 범위", "크기"],
              [["바이스태틱 각", "β ≤ 45°",
                "상반성 rms 잔차 β≤45° "
                + dnum(D["recip_in"], "{:.2f}", "dB", f"{J_DF} : d2_reciprocity_drone.rows",
                       "β≤45 행 최대")
                + " · β 60~90° "
                + dnum(D["recip_out"], "{:.2f}", "dB", f"{J_DF} : d2_reciprocity_drone.rows",
                       "β>45 행 최대")],
               ["σ 격자 앙각",
                "el ≥ " + dnum(D["el_grid_min"], "{:.0f}", "°",
                               f"{J_SG_USED} : meta.el_deg", "최솟값")
                + " (`d` ≥ "
                + dnum(D["d_el20"], "{:.0f}", "m", f"{J_FS} : solve.W1.el_look_deg", "el=−20° 보간")
                + ")",
                "격자 앙각 행 "
                + dnum(D["n_el"], "{:.0f}", "개", f"{J_SG_USED} : meta.el_deg", "길이")
                + ", 헤드라인 거리의 el = "
                + num(None, (J_FS, "meta.ranges_el_look_deg"), "{:.2f}", "°")],
               ["β = 45° 지점",
                "`d` = " + dnum(D["d_beta45"], "{:.0f}", "m", f"{J_FS} : solve.W1.beta_deg",
                                "β=45° 보간"),
                "그 지점의 SNR = "
                + dnum(D["snr_at_beta45"], "{:.0f}", "dB", f"{J_FS} : solve.W1.snr_d_db",
                       "d=β45 에서 보간")],
               ["장면 방위 φ",
                PH.num("meta.n_phi", None, "{:.0f}") + "방위 전수 — 5° 간격의 전 원주",
                "σ 를 고정한 순수기하에서 R90 span "
                + PH.num(f"{PHC}.constant_sigma_control.W1.span_pct_of_phi90", None,
                         "{:.2f}", "%")
                + "(" + PH.num(f"{PHC}.constant_sigma_control.W1.span_db_equiv", None,
                               "{:.3f}", "dB")
                + " 등가) · 자세평균 "
                + PH.num(f"{PHC}.aspect_averaged.W1.span_pct_of_phi90", None, "{:.2f}", "%")
                + " · 세 팔 모두 φ=90° 가 "
                + PH.num(f"{PHC}.constant_sigma_control.W1.phi90_is", None)
                + " 이라 이 편의 φ 는 보수적인 끝이다"]]),
        "",
        f"같은 스윕이 σ 조회의 앙각도 잰다 — 스윕이 읽은 격자"
        f"(생성 {PH.num('meta.sigma_file_generated', None)}, 앙각 0~−20°)에서 조회의 "
        f"{PH.num('geometry.rows[18].frac_el_outside_sigma_grid', None, '{:.1%}')}(φ=90°) ~ "
        f"{PH.num('geometry.rows[0].frac_el_outside_sigma_grid', None, '{:.1%}')}(φ=0°) 가 "
        f"경계 행으로 클램프됐다 — 격자 밖 값을 가장자리 값으로 눌러 붙였다는 뜻이다. "
        f"근거리 SNR 천장이 그 조회 위에 서므로, 확장된 앙각 격자 위에서 "
        f"다시 푸는 일을 다음 단계에 건다.",
    ))

    # ── §2 감도사슬 ───────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §2. 감도사슬 — 밴드 격차를 항으로 분해한다",
        "",
        f"d = 1 km · Mavic 4 Pro · 수신소자 1개. 점유 규약은 "
        f"{FS.num('meta.link_budget.power_normalization.canonical_occupancy', None)}"
        "(자원요소 RE 하나당 같은 전력)이고, σ 항은 기울기 앵커의 밴드별 Δσ 를 더한 값이다. **세 밴드에서 "
        "값이 다른 항은 λ² 와 σ 둘뿐이다** — 나머지는 세 밴드가 같은 값을 쓴다.",
        "",
        table(["항", "WiFi", "LTE", "5G"],
              [[nm] + [B(m, k) for m in MODES] for nm, k in
               [("공통항 합 (EIRP·수신이득·확산·1/N₀·CPI·듀티·손실)", "common"),
                ("$\\lambda^2$", "lambda2"),
                ("$\\sigma$ (기울기 앵커, 공칭 헤딩)", "sigma_anch"),
                ("**출력 SNR**", "total_anch")]]),
        "", SRC_B, SRC_A,
    ))

    blocks.append(md(
        "밴드 쌍의 격차를 그 두 항으로 쪼갠다. λ² 는 정의로 정확하고, σ 는 자세 로브 구조"
        "(방위를 돌릴 때 σ 가 솟는 봉우리와 꺼지는 골)가 만든다.",
        "",
        table(["쌍", "출력 SNR 차", "λ² 항", "σ 항"],
              [[p,
                DV.num(f"gap_1km.by_pair.{p}.d_total", None, "{:+.2f}", "dB"),
                DV.num(f"gap_1km.by_pair.{p}.d_lambda2", None, "{:+.2f}", "dB"),
                DV.num(f"gap_1km.by_pair.{p}.d_sigma", None, "{:+.2f}", "dB")]
               for p in ("W1-L1", "W1-G1", "L1-G1")]),
        "",
        f"5기체 × 3쌍 15칸에서 σ 항이 더 큰 칸은 "
        f"{SS.num('gap_decomposition.n_pairs_sigma_dominates', None, '{:.0f}')}칸이고, "
        f"σ-무관 축의 격차는 λ² 스프레드 "
        f"{SS.num('gap_decomposition.axes_pair_gaps_db.W1-L1', None, '{:+.2f}')} / "
        f"{SS.num('gap_decomposition.axes_pair_gaps_db.W1-G1', None, '{:+.2f}')} / "
        f"{SS.num('gap_decomposition.axes_pair_gaps_db.L1-G1', None, '{:+.2f}', 'dB')} 로 고정이다.",
        "",
        figure_md(PF["gap"], 1,
                  "밴드 격차를 만드는 항은 λ² 와 σ 중 무엇인가?",
                  paper_caption="Per-band cost decomposition on one target and one "
                                "geometry: only the wavelength term and the target "
                                "cross section differ between the three illuminators, "
                                "and the cross-section difference dominates 9 of 15 "
                                "band pairs.",
                  report="report05_results"),
    ))

    blocks.append(md(
        "### §2.1 어느 벽이 거리를 정하나",
        "",
        f"헤드라인 칸을 구속하는 것은 직접파 잔차다({FS.num('solve.W1.limit', None)}). "
        "ECA 억압 깊이를 바꾸면 거리가 이렇게 움직인다.",
        "",
        table(["ECA 깊이"] + [f"{k} dB" if k != "inf" else "완전 억압"
                             for k in ("40", "60", "90", "inf")],
              [["R90"] + [num(None, (J_FS, f"solve.W1.sensitivity_eca_depth.{k}.R_m"),
                              "{:.0f}", "m") for k in ("40", "60", "90", "inf")]]),
        "",
        f"레이더 방정식 항등식 검사는 파형 3종 × 기체 2종 "
        f"{dnum(D['lb_rows'], '{:.0f}', '행', f'{J_LB} : A_radar_equation.rows', '길이')}"
        f" 에서 코드 경로와 dB 산술의 차이를 "
        f"{dnum(D['lb_resid'], '{:.1e}', 'dB', f'{J_LB} : A_radar_equation.rows', '|d_echo_dbarith_db| 최대')}"
        f" 로 잡는다.",
    ))

    blocks.append(md(
        "### §2.2 듀티 축의 크기",
        "",
        "위 사슬은 기준신호가 CPI 전체를 채운다는 규약에서 풀린다. 실제 점유가 만드는 듀티 항은 "
        "밴드마다 다르고, 그 크기를 여기 적는다 — 이 항을 켠 설정의 순위는 §3.4 표가 든다.",
        "",
        table(["모드", "기준신호 길이 T_ref", "프레임 M", "듀티 항"],
              [[MODE_NAME[m],
                SS.num(f"unapplied_duty_axis.by_mode.{m}.T_ref_s", None, "{:.2e}", "s"),
                SS.num(f"unapplied_duty_axis.by_mode.{m}.M", None, "{:.0f}"),
                SS.num(f"unapplied_duty_axis.by_mode.{m}.duty_db", None, "{:+.2f}", "dB")]
               for m in MODES]),
        "",
        f"이 항을 넣으면 5G 는 LTE 대비 "
        f"{SS.num('unapplied_duty_axis.pair_gaps_db.L1-G1', None, '{:.2f}', 'dB')} 를 더 치른다. "
        f"같은 값이 집안의 다른 산출물에도 있다 — WiFi 의 "
        f"{SS.num('unapplied_duty_axis.duty_db.W1', None, '{:.2f}', 'dB')} 는 "
        "`outputs/report4_fixups.json : packet_duty_db` 와 일치한다.",
    ))

    # ── §3 세 파형 ────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §3. 세 파형 벤치마크",
        "",
        "세 조명원은 각 표준이 늘 켜 두는 기준신호다 — WiFi VHT-LTF(W1) · LTE CRS(L1) · "
        "5G SSB(G1). 제원은 03 §1, 여기서는 그 셋을 같은 검출기에 물린다.",
        "",
        "### §3.1 문턱을 경험 Pfa 로 교정한다",
        "",
        f"경험 Pfa 를 목표 {FS.num('threshold.pfa.W1.target', 1e-4, '{:.0e}')} 에 고정하고, 그때 "
        "요구되는 명목 Pfa 를 기록한다(`src/freespace_detect.py:711`). 자유공간 형상은 거리창 · "
        "오버샘플 · 가드 규약이 챔버와 다르므로 형상마다 다시 잰다 — 04 §3 의 배율은 챔버 형상 값이다.",
        "",
        table(["모드", "요구 명목 Pfa", "경험 Pfa", "경험/명목"],
              [[MODE_NAME[m], num(None, (J_FS, f"threshold.pfa.{m}.nominal"), "{:.2e}"),
                num(None, (J_FS, f"threshold.pfa.{m}.empirical"), "{:.2e}"),
                num(None, (J_FS, f"threshold.pfa.{m}.ratio_emp_over_nominal"), "{:.3f}")]
               for m in MODES]),
        "",
        f"5G 의 요구 명목 Pfa 는 경험값의 "
        f"{dnum(D['pfa_g1_ratio'], '{:.0f}', '배', f'{J_FS} : threshold.pfa.G1.ratio_emp_over_nominal', '역수')}"
        f" 다 — 프레임 {FS.num('waveforms.G1.M', 5, '{:.0f}')}개짜리 도플러 축이 그만큼 좁다.",
        "<!--cell-->",
        f"세 밴드의 solve 는 이 중 W1 에서 잰 문턱 SNR90 = "
        f"{DV.num('threshold.snr90_shared_db', None, '{:.2f}', 'dB')} 하나를 공유한다"
        f"(`src/experiment_freespace_range.py:856`). 그 선택의 크기는 이렇다.",
        "",
        table(["모드", "자기 문턱 SNR90", "공유 문턱과의 차", "R90 에 주는 차"],
              [["WiFi", DV.num("threshold.snr90_shared_db", None, "{:.2f}", "dB"),
                "기준", "기준"],
               ["LTE", DV.num("threshold.l1_own_snr90_db", None, "{:.2f}", "dB"),
                DV.num("threshold.l1_delta_db", None, "{:+.3f}", "dB"),
                DV.num("threshold.l1_range_shift_pct", None, "{:+.2f}", "%")],
               ["5G", f"dopoff 격자 {DV.num('threshold.g1_total_cells', None, '{:.0f}')}칸이 "
                      f"M={DV.num('threshold.g1_M', None, '{:.0f}')} 의 도플러 축 밖",
                "—", "— (다음 단계 1행)"]]),
    ))

    blocks.append(md(
        figure_md(PF["detector"], 2,
                  "교정된 오경보율 위에서 세 파형이 요구하는 SNR 은 몇 dB 인가?",
                  paper_caption="Detection curves for the three always-on reference "
                                "signals at an empirically calibrated false-alarm "
                                "rate, and the sensitivity cost of restricting a "
                                "receiver to always-on references.",
                  report="report05_results"),
    ))

    # ── §3.2 앵커 σ ───────────────────────────────────────────────────────── #
    blocks.append(md(
        "### §3.2 밴드 비교의 바닥 — 기울기 앵커 σ",
        "",
        "σ = A(f)·B₁(φ,θ) 에서 **A(f) 의 기울기**를 Das 측정(IEEE WCL 2026 15:3731)에 맞춘다. "
        "**절대 레벨은 우리 PO 출력**이고, 생산 모드 `slope_only` 의 세 밴드 평균 레벨이동은 "
        + DV.num("anchor_scope.level_shift_abs_max_db", None, "{:.2f}", "dB")
        + " 다. 레벨까지 맞추려면 크기전이 법칙을 골라야 하고 L² 와 L⁴ 가 최대 "
        + DV.num("anchor_scope.size_law_spread_max_db", None, "{:.2f}", "dB")
        + " 갈리므로, 측정이 그 대가 없이 제약하는 기울기만 받는다(02 §4.1).",
        "",
        f"재보정은 밴드별 스칼라(방향 구분 없이 값 하나) Δσ 하나씩이고, 정규화 각도 패턴은 "
        f"{AN.num('drones.phantom4.shape_invariance_max_abs_db', None, '{:.1e}', 'dB')} "
        "안에서 그대로 남는다. 앵커가 통제한 것 밖의 항은 **셋**이다 — 규약 불확도 "
        + num(None, (J_AN, "uncontrolled[1].size_db"), "{:.2f}", "dB")
        + ", 크기전이 항, 그리고 **PO 유효성 항**이다"
        + f"(⟨{J_AN} : uncontrolled⟩). 세 번째가 이번에 크기를 얻었다 — PO 오차가 1 dB 아래로 "
        + "내려가려면 부품의 폭이 파장의 "
        + num(None, ("outputs/lowfreq_anchor.json",
                     "thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam"), "{:.3f}")
        + " 배 이상이어야 하는데, 우리 세 밴드는 전부 그 문턱 아래에 부품을 남긴다(02 §3.1a). "
        + "그 항의 **부호는 아직 정하지 못한다** — 우리 적분이 편파(전파의 전기장이 흔들리는 방향)를 "
        + "가르지 않기 때문이다"
        + f"(⟨{J_LFA} : q5_blast_radius.po_validity_blast_radius_the_real_one⟩). "
        + "참값은 두 편파에서 서로 다른 값을 주는데 우리 커널은 그 둘을 구분 없이 하나로 내므로, "
        + "한쪽 편파를 기준으로 보면 낮고 다른 쪽을 기준으로 보면 높다. 두 쪽 중 어느 쪽이 더 "
        + "그럴듯한지는 02 §4.5 가 두 편파의 크기 차이로 적는다 — 이 편은 그 개연성을 결과에 "
        + "넣지 않고 순위만 든다. 이 사실은 원장에 "
        + "「VV 측정 대 무편파 커널」 로 기록되어 있다. "
        + f"⚠ 이 절이 든 앵커 수(정규화 잔차 · 아래 Δσ 표)와 §3.3 의 R90 표는 `{J_AN}` 에서 "
        + "오고, 그 사슬은 "
        + MFX.num("_meta.date", None)
        + " 형상 정정 전 메쉬 위에 서 있다 — 다섯 기체 중 Matrice 4E 가 그 정정을 받았다"
        + f"(02 §4.2 · §5) ⟨{J_MFX_ATK} : Q6_invalidated_outputs.critical[3]⟩.",
        "<!--cell-->",
        table_from(f"{J_AN}:drones",
                   [("기체", None),
                    ("Δσ WiFi", "modes.slope_only.delta_db.WiFi 5.21 GHz"),
                    ("Δσ LTE", "modes.slope_only.delta_db.LTE 1.843 GHz"),
                    ("Δσ 5G", "modes.slope_only.delta_db.5G 3.5 GHz"),
                    ("보정 후 기울기", "modes.slope_only.slope_after_db_per_ghz"),
                    ("앵커 비교가능성", "comparability.verdict")],
                   fmt={"modes.slope_only.delta_db.WiFi 5.21 GHz": "{:+.2f} dB",
                        "modes.slope_only.delta_db.LTE 1.843 GHz": "{:+.2f} dB",
                        "modes.slope_only.delta_db.5G 3.5 GHz": "{:+.2f} dB",
                        "modes.slope_only.slope_after_db_per_ghz": "{:.3f} dB/GHz"},
                   order=list(DRONES)),
        "",
        figure_md(PF["anchor"], 3,
                  "앵커가 옮긴 밴드 격차는 앵커 자신의 미통제 항보다 큰가?",
                  paper_caption="The slope anchor applies one scalar per band and "
                                "airframe, and the resulting band spread is compared "
                                "with the size-transfer term the anchor leaves open.",
                  report="report05_results"),
    ))

    # ── §3.3 앵커 R90 ─────────────────────────────────────────────────────── #
    blocks.append(md(
        "### §3.3 기울기 앵커 σ 위의 R90",
        "",
        f"Δσ 를 R90 근방 국소 지수 "
        f"{dnum(D['n_local'], '{:.2f}', '', f'{J_FS} : ' + CELL.format(d='*', m='*') + '.n_local_at_R90', '15칸 평균')}"
        " 로 옮긴다 — `d` 축에서 국소적으로 $R \\propto \\sigma^{1/n}$ 이다"
        "(`src/freespace_scene.py:56`). 아래 표의 R90 은 전부 공칭 헤딩 ψ=0 의 수이고, "
        "**§3.4 의 민감도 봉투와 함께 읽는다** — 공통모드 σ 오차 ±10 dB 가 이 열 전체를 "
        + SS.num("common_mode.abs_range_shift_at_10db_pct.minus10", None, "{:+.1f}", "%")
        + " ~ " + SS.num("common_mode.abs_range_shift_at_10db_pct.plus10", None, "{:+.1f}", "%")
        + " 옮긴다. ⚠ 그 봉투가 어디서 오는지도 함께 적는다 — 우리 세 밴드는 전부 PO 근사가 "
        "1 dB 안에 든다고 보장되는 부품 폭 문턱 아래에 부품을 남긴다(02 §3.1a). 즉 σ 절대 "
        "레벨의 불확도는 **선언된 ±10 dB 봉투와 별개로 크기가 아직 정해지지 않은 항**을 하나 더 "
        f"갖는다(⟨{J_LFA} : q5_blast_radius.po_validity_blast_radius_the_real_one⟩). 그래서 아래 "
        "km 열은 **순위를 읽는 표**로 쓴다.",
        "",
        table(["기체"] + [MODE_NAME[m] for m in MODES] + ["앵커 비교가능성"],
              [[dr] + [f"{D['R90_anch'][(dr, m)]:.2f} km" for m in MODES]
               + [fetch((J_AN, f"drones.{dr}.comparability.verdict"))] for dr in DRONES]),
        "", SRC_R, SRC_A,
    ))

    blocks.append(md(
        "밴드 순서는 기체마다 바뀐다 — 그 순서를 만드는 것은 자세별 로브 구조이고, 앵커는 밴드별 "
        "스칼라를 옮기면서 밴드 평균 레벨은 그대로 둔다. 자세를 평균하면 다섯 기체가 한 순위로 모인다.",
        "",
        table(["인용 방식", "서로 다른 순위 수", "합의 순위", "최악 뒤집힘 문턱"],
              [["단일 자세 ψ=0",
                SS.num("configurations.by_config.as_published.n_distinct_orders", None, "{:.0f}"),
                "기체마다 다름",
                SS.num("configurations.by_config.as_published.worst_flip_span_db", None,
                       "{:.2f}", "dB")],
               ["자세평균 σ",
                SS.num("configurations.by_config.aspect_avg.n_distinct_orders", None, "{:.0f}"),
                DV.num("ranking.consensus_order_aspect_avg", None),
                SS.num("configurations.by_config.aspect_avg.worst_flip_span_db", None,
                       "{:.2f}", "dB")],
               ["자세평균 + 기울기 앵커",
                SS.num("configurations.by_config.aspect_avg_anchored.n_distinct_orders", None,
                       "{:.0f}"),
                DV.num("ranking.consensus_order_aspect_avg", None),
                SS.num("configurations.by_config.aspect_avg_anchored.worst_flip_span_db", None,
                       "{:.2f}", "dB")],
               ["자세평균 + 앵커 + 듀티",
                SS.num("configurations.by_config.aspect_avg_anchored_duty.n_distinct_orders",
                       None, "{:.0f}"),
                "기체마다 다름",
                SS.num("configurations.by_config.aspect_avg_anchored_duty.worst_flip_span_db",
                       None, "{:.2f}", "dB")]]),
        "",
        figure_md(PF["ranking"], 4,
                  "세 파형의 순위는 자세 인용 방식에 따라 어떻게 달라지는가?",
                  paper_caption="Three-waveform comparison normalised per airframe: "
                                "five airframes give three different orders at a "
                                "single aspect and one common order on "
                                "aspect-averaged, slope-anchored cross sections.",
                  report="report05_results"),
    ))

    # ── §3.4 σ 민감도 ─────────────────────────────────────────────────────── #
    blocks.append(md(
        "### §3.4 그 순위는 σ 오차 아래에서 어디까지 버티나",
        "",
        "σ 오차를 두 종류로 나눠 넣는다. **공통모드**는 세 밴드를 함께 옮기고, **차분**은 밴드마다 "
        "다르게 옮긴다. σ 는 SNR 에 선형이라 σ 오프셋 Δ dB 가 곧 SNR 오프셋 Δ dB 다"
        f"(선형성 잔차 {SS.num('_meta.sigma_linearity_check', None, '{:.1e}')}).",
        "",
        table(["오차 종류", "무엇이 움직이나", "크기"],
              [["공통모드 ±10 dB",
                "순위 유지 · 절대거리만 이동",
                "15칸 전부 순위 불변 · 거리 "
                + SS.num("common_mode.abs_range_shift_at_10db_pct.minus10", None, "{:+.1f}", "%")
                + " ~ "
                + SS.num("common_mode.abs_range_shift_at_10db_pct.plus10", None, "{:+.1f}", "%")],
               ["차분(밴드별)",
                "순위가 뒤집힐 수 있는 축",
                "뒤집힘 문턱 "
                + SS.num("differential.smallest_flip_span_db_overall", None, "{:.2f}")
                + " ~ "
                + SS.num("differential.largest_flip_span_db_overall", None, "{:.2f}", "dB")
                + " (현실 봉투 — 실제로 있을 법한 오차 폭 "
                + SS.num("differential.realistic_span_db", None, "{:.2f}", "dB") + ")"],
               ["밴드별 독립 오차 2 dB (몬테카를로)",
                "순위 보존 확률",
                dnum(D["mc_p2db_min"], "{:.2f}", "", f"{J_SS} : monte_carlo_per_band_error",
                     "5기체 최소") + " ~ "
                + dnum(D["mc_p2db_max"], "{:.2f}", "",
                       f"{J_SS} : monte_carlo_per_band_error", "5기체 최대")]]),
        "",
        f"취약성을 정하는 것은 기체 크기가 아니라 **밴드 간 σ 로브 산포**다 — 가장 작은 "
        f"{SS.num('size_vs_fragility.smallest_airframe', None)}(전장 "
        f"{SS.num('size_vs_fragility.by_drone.mini5pro.extent_m', None, '{:.3f}', 'm')}, LTE 에서 "
        f"D/λ = {SS.num('size_vs_fragility.by_drone.mini5pro.D_over_lambda_lte', None, '{:.2f}')})"
        f" 가 가장 견고하고, 크기와 뒤집힘 문턱의 상관은 "
        f"{SS.num('size_vs_fragility.corr_extent_vs_flip_single', None, '{:+.2f}')} 다.",
        "",
        f"또 하나의 실측 사실을 같은 자리에 적는다: σ 격자를 블레이드 형상 갱신본으로 바꾸는 것만으로 "
        f"R90 이 최대 "
        + dnum(D["stale_max_pct"], "{:.1f}", "%",
               f"{J_SS} : staleness_and_mesh_update.by_drone", "5기체 max_range_change_pct 최대")
        + f" 움직이고 순위쌍 "
        f"{SS.num('staleness_and_mesh_update.n_orders_changed', None, '{:.0f}')}개가 바뀌었다 "
        f"— 통제되지 않은 σ 변화의 파급을 관측한 값이다. ⚠ 그리고 위 표의 뒤집힘 문턱은 "
        f"{MFX.num('_meta.date', None)} 형상 정정 전 메쉬 위에 있다 — 하한 "
        f"{SS.num('differential.smallest_flip_span_db_overall', None, '{:.2f}', 'dB')} 를 내는 "
        f"행이 그 정정을 받은 Matrice 4E 다(02 §5 · 방법 «밴드 비교»). 이 하한은 **단일 자세** 기준이고, "
        f"같은 기체를 **자세평균**으로 읽으면 "
        f"{SS.num('aspect_averaged.by_drone.matrice4e.smallest_flip_span_db', None, '{:.2f}', 'dB')} "
        f"다 — 06편 §3 이 캠페인 판정 문턱으로 드는 수가 그것이다.",
        "",
        figure_md(PF["robust"], 5,
                  "σ 오차가 공통모드일 때와 밴드별일 때 순위는 각각 어디까지 버티는가?",
                  paper_caption="Ranking robustness: a common-mode cross-section error "
                                "preserves the order at every offset within 10 dB and "
                                "moves only the absolute range, while a per-band "
                                "differential error reorders the waveforms above an "
                                "airframe-specific threshold.",
                  report="report05_results"),
    ))

    # ── §3.5 CPI 스윕 ─────────────────────────────────────────────────────── #
    blocks.append(md(
        "### §3.5 5G 의 상시기준 대가 — CPI 스윕",
        "",
        "5G 의 상시 기준신호(SSB)는 20 ms 주기라 PRF 50 Hz 를 준다. 도플러 축을 지우는 기구는 둘이다 "
        f"— **A. 표본화**: `{CG.num('structural.formula', None)}` 로 가드가 접힘 축 전체를 덮는다"
        "(반송파·속도·거리 무관). **B. 진폭**: 짧은 CPI 에서 가드가 도플러 진폭을 덮는다(파형 공통). "
        f"1.5빈 규약에서 LTE 도 CPI ≤ "
        f"{CG.num('structural.two_mechanisms.observed.L1.hard.T_max_total_blind_s', None, '{:.3f}', 's')}"
        " 에서 전 헤딩 블라인드가 된다.",
        "",
        #  ⭐ 열 이름의 CPI 와 아래 문장의 CPI 는 같은 원장 자리에서 받는다.
        table(["모드", "PRF",
               f"CPI {fetch((J_CG, 'equal_cpi_penalty[0].T_cpi_s')):.1f} s 의 M",
               "접힘 축 ±", "블라인드(1.5빈)", "블라인드(2.5빈)"],
              [[MODE_NAME[m],
                CG.num(f"waveform_facts.{m}.prf_hz", None, "{:.0f}", "Hz"),
                CG.num(f"anchor.reproduction.{m}.M", None, "{:.0f}"),
                CG.num(f"anchor.reproduction.{m}.fold_half_hz", None, "{:.1f}", "Hz"),
                CG.num(f"anchor.reproduction.{m}.blind_hard", None, "{:.3f}"),
                CG.num(f"anchor.reproduction.{m}.blind_declared", None, "{:.3f}")]
               for m in MODES]),
        "",
        f"5G 의 커버리지 0 은 선언가드 2.5빈 · CPI ≤ "
        f"{CG.num('structural.by_mode.G1.T_max_total_blind_declared_s', None, '{:.2f}', 's')} 에서 "
        f"성립한다. 검출기가 적용하는 1.5빈 규약의 경계는 "
        f"{CG.num('structural.by_mode.G1.T_max_total_blind_hard_s', None, '{:.2f}', 's')} 이고, "
        f"CPI {CG.num('equal_cpi_penalty[0].T_cpi_s', None, '{:.1f}', 's')} 의 블라인드율은 "
        f"{CG.num('verdict.artifact.blind_hard_same_cpi', None, '{:.3f}')} 다.",
    ))

    blocks.append(md(
        "CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다. 5G 가 치르는 **배수**는 그대로 남는다 — "
        "이것이 이 대가를 구조로 만드는 첫 번째 사실이다.",
        "",
        table(["CPI", "WiFi", "LTE", "5G", "5G/WiFi", "5G/LTE"],
              [[CG.num(f"equal_cpi_penalty[{i}].T_cpi_s", None, "{:.1f}", "s"),
                CG.num(f"equal_cpi_penalty[{i}].blind_hard_W1", None, "{:.3f}"),
                CG.num(f"equal_cpi_penalty[{i}].blind_hard_L1", None, "{:.3f}"),
                CG.num(f"equal_cpi_penalty[{i}].blind_hard_G1", None, "{:.3f}"),
                CG.num(f"equal_cpi_penalty[{i}].ratio_G1_over_W1", None, "{:.1f}", "배"),
                CG.num(f"equal_cpi_penalty[{i}].ratio_G1_over_L1", None, "{:.1f}", "배")]
               for i in range(5)]),
        "",
        f"두 번째 사실은 접힘이다 — 5G 의 alias 비율 "
        f"{CG.num('verdict.structural.s2_alias_floor.alias_frac_G1', None, '{:.3f}')} 는 적분시간이 "
        f"아니라 표본화율의 성질이라 CPI 와 무관한 상수이고, WiFi·LTE 는 "
        f"{CG.num('verdict.structural.s2_alias_floor.alias_frac_W1', None, '{:.3f}')} 다.",
    ))

    blocks.append(md(
        f"세 번째 사실이 결정적이다: 모호속도는 표본화율의 성질이라 CPI 로 바뀌지 않는다 — 5G "
        f"{CG.num('unambiguous_speed.G1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · WiFi "
        f"{CG.num('unambiguous_speed.W1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · LTE "
        f"{CG.num('unambiguous_speed.L1.v_unambiguous_ms', None, '{:.2f}', 'm/s')}. 커버리지를 "
        f"WiFi 수준으로 올리는 CPI 는 "
        f"{CG.num('cost_of_long_cpi.required_cpi_s.to_WiFi_parity', None, '{:.2f}', 's')}, LTE "
        f"수준은 {CG.num('cost_of_long_cpi.required_cpi_s.to_LTE_parity', None, '{:.2f}', 's')} 이고 "
        "그 대가는 재방문 시간이다.",
        "",
        table(["패리티 목표 (5 m/s)", "필요 CPI", "SSB 버스트", "헤드라인 대비 경과", "거리워크",
               "코히어런트 이득"],
              [[nm,
                CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.T_required_s", None, "{:.2f}", "s"),
                CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.ssb_bursts_needed", None, "{:.0f}"),
                CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.elapsed_vs_headline", None,
                       "{:.2f}", "배"),
                CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.range_walk_bins_median", None,
                       "{:.3f}", "빈"),
                CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.snr_gain_db_if_coherent", None,
                       "{:.2f}", "dB")]
               for nm, k in (("LTE 수준", "v5_LTE_parity"), ("WiFi 수준", "v5_WiFi_parity"))]),
        "",
        f"그 CPI 가 코히어런스 한계 안에 머무는 구간은 "
        f"{CG.num('cost_of_long_cpi.by_speed[6].speed_ms', None, '{:.0f}', 'm/s')} 까지이고, "
        f"{CG.num('cost_of_long_cpi.by_speed[7].speed_ms', None, '{:.0f}', 'm/s')} 에서 WiFi 패리티 "
        f"CPI 가 한계 "
        f"({CG.num('cost_of_long_cpi.by_speed[7].T_coh_s', None, '{:.2f}', 's')}) 를 넘어선다 — "
        f"거리·속도 격자 {CG.num('cost_of_long_cpi.coherence_map_summary.n_cells', None, '{:.0f}')}칸 중 "
        f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_WiFi_parity_feasible', None, '{:.0f}')}칸이 "
        "WiFi 패리티를 허용한다.",
        "",
        figure_md(PF["cpi"], 6,
                  "5G 의 눈먼 헤딩 비율은 CPI 와 표적 속도에 따라 어떻게 움직이는가?",
                  paper_caption="The 5G always-on-reference penalty as a CPI sweep: "
                                "the blind-heading fraction falls with CPI under both "
                                "guard conventions, and the CPI needed for parity with "
                                "LTE or WiFi is bounded by the coherent-integration "
                                "limit of the moving target.",
                  report="report05_results"),
    ))

    # ── §3.6 기준신호 대역 축 ─────────────────────────────────────────────── #
    blocks.append(md(
        "### §3.6 σ 를 곱하기 전 축 — 기준신호 대역과 점유 등급",
        "",
        "같은 표적·같은 기하·같은 검출기에서 Pd = 0.5 에 필요한 출력 SNR 은 기준신호 대역과 "
        "프레임 수가 정한다. 이 축은 σ 와 무관하게 세 파형의 순서를 정한다.",
        "",
        table(["표준", "상시 기준(등급 1)", "세션 기준(등급 3)", "상시 제약의 대가", "거리분해능 대비"],
              [[nm,
                DV.num(f"always_on_cost.{c}.snr50_g1", None, "{:.2f}", "dB"),
                DV.num(f"always_on_cost.{c}.snr50_g3", None, "{:.2f}", "dB"),
                DV.num(f"always_on_cost.{c}.cost_db", None, "{:+.2f}", "dB"),
                DV.num(f"always_on_cost.{c}.dr_g1_m", None, "{:.2f}", "m") + " ↔ "
                + DV.num(f"always_on_cost.{c}.dr_g3_m", None, "{:.2f}", "m")]
               for nm, c in (("WiFi", "W"), ("LTE", "L"), ("5G NR", "G"))]),
        "",
        f"이 스윕은 §1~§3.5 와 **다른 배치**에서 돈다 — X410 벤치(`src/experiment_x410.py:101`), "
        f"단일 반송파 {DV.num('bench.fc_ghz', None, '{:.1f}', 'GHz')} 를 9모드 전부에 쓰고, "
        f"바이스태틱 거리 {DV.num('bench.Rb_m', None, '{:.1f}', 'm')}, 고정 σ "
        f"{DV.num('bench.sigma_dbsm', None, '{:.2f}', 'dBsm')} 다. 표적·기하·σ 를 한 값으로 "
        "묶었으므로 여기서 읽는 것은 **파형 축 하나**의 상대 비교다.",
    ))

    # ── §3.7 표적모형 민감도 — 이 순위표가 서 있는 표적 가정 ────────────────── #
    blocks.append(md(
        "### §3.7 표적모형이 검출을 얼마나 바꾸나",
        "",
        f"같은 기하·같은 검출기·같은 동작점에서 표적만 세 모형으로 갈아끼웠다 — 자세무관 평판 "
        f"σ {TM.num('protocol.operating_point.sigma_reference_dbsm', None, '{:.2f}', 'dBsm')}(3GPP, "
        f"M1) · 정육면체(M2) · 우리 SBR+PO 격자(M3). 자세 앙상블은 셀당 "
        f"{TM.num('statistics.n_aspect_realisations_per_cell', None, '{:.0f}')}자세 전수, (기체×밴드) "
        f"셀은 {TM.num('statistics.n_drone_band_cells', None, '{:.0f}')}개이고, 자세평균을 맞춘 뒤 "
        f"남는 **요구 추가이득**을 추정량별로 적는다(재현편차 "
        f"{TA.num('meta.reproduction.E0_extra_gain_max_abs_dev_db', None, '{:.2f}', 'dB')}).",
        "",
        table(["무엇을 맞추나", "M1 평판 [dB]", "M2 정육면체 [dB]", "M3 우리 격자 [dB]"],
              [[nm,
                TA.num(f"{TAE}.{k}.per_model_extra_gain_db.M1", None, "{:+.2f}"),
                TA.num(f"{TAE}.{k}.per_model_extra_gain_db.M2", None, "{:+.2f}"),
                TA.num(f"{TAE}.{k}.per_model_extra_gain_db.M3", None, "{:+.2f}")]
               for nm, k in (("선형평균 — 이 실험의 규약", "mean_lin"),
                             ("중앙값", "median"),
                             ("dB 평균", "mean_db"),
                             ("p10 — 검출기가 읽는 분위수", "p10"))]),
        "",
        f"낙차의 소유자는 정육면체다 — 자유공간에서 최대가 M2 인 셀이 "
        f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmax_counts.M2', None, '{:.0f}')}개, "
        f"최소가 M1 인 셀이 "
        f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmin_counts.M1', None, '{:.0f}')}개로 "
        f"전수이고, M3 몫은 다섯 앙상블에서 "
        f"{TA.num('Q3_staleness.argmax_argmin_counts.E2_outdoor_canyon.m3_share_of_spread', None, '{:.1%}')} ~ "
        f"{TA.num('Q3_staleness.argmax_argmin_counts.E1_chamber_floor.m3_share_of_spread', None, '{:.1%}')} 다. "
        f"각 다양성이 그 낙차를 줄인다 — 각 다양성이 0 인 자유공간(N_eff "
        f"{TM.num('verdicts.Q3_environment_dependence.predictor.E0_freespace.n_eff_pairs', None, '{:.1f}')})에서 "
        f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E0_freespace', None, '{:.2f}', 'dB')}, "
        f"각 다양성이 가장 큰 앙상블(N_eff "
        f"{TM.num('verdicts.Q3_environment_dependence.predictor.E2b_outdoor_shadowed.n_eff_pairs', None, '{:.2f}')})에서 "
        f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E2b_outdoor_shadowed', None, '{:.2f}', 'dB')} 다.",
        "",
        f"⚠ 크기는 **추정량이 정한다** — 검출기가 읽는 p10 에서 맞추면 낙차가 "
        f"{TA.num(f'{TAE}.p10.spread_mean', None, '{:.2f}', 'dB')} 로 줄고 세 팔의 순서가 뒤집혀 "
        f"M1 이 가장 어려운 팔이 된다. 문턱은 잡음전력 기지 이상문턱이고 CA-CFAR 문턱은 세 팔에 "
        f"같은 오프셋을 주므로, 04 의 교정표는 세 팔의 절대 소요이득만 옮긴다"
        f"(⟨{J_TM} : protocol.pfa_convention⟩).",
        "",
        "⚠ 이 표에 **구 대조군은 없다.** 02 §4.6 이 보인 것처럼 구는 **부피를 맞게 고르면** σ 의 "
        "절대 레벨을 맞출 수 있는 단순 모형이면서 자세에 따른 변화를 0 으로 낸다 — 레벨에서 우리 "
        "메쉬를 앞선 그 구는 논문이 적어 둔 상자 치수로 잡은 부피이고, 메쉬 부피로 잡으면 두 잣대 "
        "모두에서 우리 메쉬보다 나쁘다. 그래서 이 표의 낙차는 «자세 구조를 얼마나 담는가» 의 "
        "낙차로 읽는다. 구 팔을 넣는 일은 다음 단계에 있다.",
    ))

    # ── §4 다중 수신기 ────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §4. 수신소자를 늘리면",
        "",
        "N 은 한 지점 λ/2 ULA 소자 수다(`src/experiment_detection.py:181`). 조향벡터를 참 표적 "
        "방향에 맞추고, 결합 잡음전력/σ² = "
        f"{RX.num('modes.W1.combine_ratio', None, '{:.5f}')} 로 잡음 보존을 확인했다 — 그래서 "
        "10log₁₀N 은 **열잡음만** 상대할 때의 코히어런트 배열이득이고, 소자 간 결합·교정오차·"
        "위치오차가 0 인 **이상적 상한**이다.",
        "",
        table(["N"] + [str(n) for n in D["ns"]],
              [["측정 이득 (WiFi) = SNR50(1)−SNR50(N)"]
               + [f"{g:+.2f} dB" for g in D["rx_gain_W1"]],
               ["열잡음 기준선 10log₁₀N"] + [f"{b:+.2f} dB" for b in D["rx_bound"]],
               ["차 (WiFi)"] + [f"{g - b:+.2f} dB"
                                for g, b in zip(D["rx_gain_W1"], D["rx_bound"])]]),
        "",
        f"출처 ⟨{J_RX} : modes.W1.curves.*.snr50⟩",
        "<!--cell-->",
        f"9모드 × N 전체에서 측정 이득은 그 상한 대비 "
        f"{DV.num('rx_gain.excess_min_db', None, '{:+.2f}')} ~ "
        f"{DV.num('rx_gain.excess_max_db', None, '{:+.2f}', 'dB')} 다. 감시신호가 "
        "`surv = √N·echo + dpi + noise` 이고 ECA 잔차 `dpi` 는 N 에 무관하게 고정이라"
        "(`src/experiment_detection.py:284`), √N 이 잡음과 잔차 양쪽 대비로 표적을 올린다 — "
        "x 축 SNR 은 잡음 기준 정의다(`:238`).",
        "",
        table(["검사", "값"],
              [["Pd 곡선에 로지스틱을 다시 적합해 잰 초과분",
                DV.num("rx_gain.excess_fit_min_db", None, "{:+.2f}") + " ~ "
                + DV.num("rx_gain.excess_fit_max_db", None, "{:+.2f}", "dB")],
               ["SNR50 의 몬테카를로 표준편차 (K = "
                + DV.num("rx_gain.K", None, "{:.0f}") + ")",
                DV.num("rx_gain.snr50_mc_sigma_db", None, "{:.3f}", "dB")],
               ["최대 초과분 / 그 표준편차",
                DV.num("rx_gain.excess_in_sigma", None, "{:.1f}", "σ")]]),
        "",
        figure_md(PF["multirx"], 7,
                  "수신소자를 늘렸을 때 얻는 감도는 이상적 코히어런트 상한에 얼마나 붙는가?",
                  paper_caption="Multi-receiver gain measured against the idealised "
                                "coherent bound of 10 log10 N, which holds for thermal "
                                "noise alone under perfect steering; the measured "
                                "excess comes from the N-independent cancellation "
                                "residual.",
                  report="report05_results"),
    ))

    # ── 논문 부록 (§4.2 방어선 · §4.4 방법 문단 · §4.5 인용) ────────────────── #
    blocks.append(appendix)

    # ── 다음 단계 ─────────────────────────────────────────────────────────── #
    blocks.append(next_steps([
        ("5G 의 dopoff 격자를 M 인식으로 고쳐 Pd=0.9 문턱을 직접 잰다",
         "5G 의 R90 이 자기 문턱 위에 서고, 세 밴드가 문턱을 공유하는 §3.1 의 행이 닫힌다",
         "`src/experiment_freespace_range.py:856` → 05편 §3.1"),
        ("듀티 항을 R90 경로에 켜고 세 밴드를 다시 푼다",
         "§2.2 의 "
         + SS.num("unapplied_duty_axis.duty_db.G1", None, "{:.2f}", "dB")
         + " 가 순위에 주는 영향이 확정되고, §3.3 표의 듀티 행이 실측값이 된다",
         "`src/freespace_link.py` 의 duty_db_from_cpi → 05편 §3.3"),
        ("자세평균 σ 격자로 `--stage solve` 를 다시 돌린다",
         "합의 순위가 국소 지수 1차 전이 없이 정본 경로에서 확정된다",
         "`src/experiment_freespace_range.py` → 05편 §3.3"),
        ("CPI 를 0.1 s 에서 1.0 s 까지 정본 solve 에 넣어 R90(CPI) 를 낸다",
         "§3.5 의 커버리지 회복이 거리 축에서도 확정된다",
         "`benchmark/cpi_guard_sweep.py` → `src/experiment_freespace_range.py`"),
        ("헤딩 격자 전체에서 R90(ψ) 를 풀어 P_ψ[Pd≥0.9]=0.50 지점을 낸다",
         "`R90_C50` 키가 이름 그대로의 커버리지 백분위 값을 담는다",
         "`src/experiment_freespace_range.py:703` → 05편 §3.3"),
        ("`SIONNA2_DPI_AMP=0` 대조군으로 Rx 스윕을 다시 돌린다",
         "§4 의 초과분이 ECA 잔차 대비 이득임이 대조군으로 확정된다",
         "`src/experiment_detection.py:115` → 05편 §4"),
        ("파형·수신소자 스윕을 §1 자유공간 기하와 물리 PRF 로 옮긴다",
         "§3.6 · §4 의 절대 SNR 이 이 편의 거리와 같은 축에 놓인다",
         "`src/experiment_detection.py` 의 X410Scenario → `src/freespace_scene.py`"),
        ("σ 전격자를 현재 메쉬로 재생성해 `--stage solve` 를 다시 돌린다",
         "절대 R90 · 백분위 · 기체간 순위가 현재 기하 위에 선다 — 동일설정 재생성 대조에서 "
         "기체당 최대 "
         + SV.num("overstated[0].결과_표[0].max_abs_delta_db", None, "{:.2f}", "dB")
         + " · rms " + SV.num("overstated[0].결과_표[0].rms_delta_db", None, "{:.2f}", "dB")
         + " 다",
         "`src/experiment_freespace_sigma.py` → 05편 §3.3"),
        ("앙각을 확장한 σ 격자 위에서 R90 과 SNR 천장을 다시 푼다",
         "φ 축에서 "
         + PH.num("geometry.rows[18].frac_el_outside_sigma_grid", None, "{:.1%}") + " ~ "
         + PH.num("geometry.rows[0].frac_el_outside_sigma_grid", None, "{:.1%}")
         + " 이던 클램프 조회가 격자 안으로 들어오고, 근거리 SNR 천장이 격자 위에 선다",
         "`src/experiment_freespace_sigma.py` 의 el 축 → "
         "`src/experiment_freespace_range.py --stage solve`"),
        ("표적모형 민감도의 M3 팔을 재생성 격자로 다시 푼다",
         "우리 팔의 요구 추가이득 "
         + TA.num("Q3_staleness.m3_own_number.base_db", None, "{:.2f}", "dB")
         + " 와 낙차 몫 "
         + TA.num("Q3_staleness.argmax_argmin_counts.E0_freespace.m3_share_of_spread", None,
                  "{:.1%}")
         + " 가 현재 메쉬 위에 선다",
         "`scratchpad/tm_result.py` → 05편 §3.7"),
        ("표적모형 민감도에 **구 팔(M4)** 을 더한다",
         "레벨만 맞추는 모형과 자세 구조를 담는 모형의 검출 낙차가 갈라진다 — 02 §4.6 이 σ 쪽에서 "
         "보인 것을 검출 쪽에서 다시 읽는다",
         "`scratchpad/tm_result.py` → 05편 §3.7"),
        ("기준 구를 함께 재서 자체 앵커를 세운다",
         "지금 우리 PO 출력인 σ 절대 레벨이 측정에 앵커되고, 크기전이 항 "
         + DV.num("anchor_scope.size_law_spread_max_db", None, "{:.2f}", "dB") + " 가 닫힌다",
         "06편 §3"),
        ("VV/HH 2편파를 잰다", "앵커의 편파 항 크기가 수치로 확정된다", "06편 §2"),
        ("β > 45° 의 출사 가시성·대칭화 잔차를 다시 잰다",
         "바이스태틱 유효창의 폭이 확정된다",
         "`benchmark/verify_sbr_defect_fixes.py` → 02편"),
    ]))

    return blocks


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    fig = os.path.join(ROOT, PF["cpi"])
    if not os.path.exists(fig):
        print("게재규격 그림이 없다 — src/viz_report05_paper.py 를 먼저 돌린다")
        import viz_report05_paper
        viz_report05_paper.main()

    D = derived()
    print(f"파생 원장: {write_derived(D, t0)}")
    rep = build_notebook("report05_results.ipynb", build_blocks(D), strict=True)
    print(f"\n생성: report05_results.ipynb  "
          f"(마크다운 {rep['md_cells']}셀 · 그림 {rep['figures']} · "
          f"출처태그 {rep['provenance_tags']}개 · 부정문 {rep['n_negatives']})")
    return rep


if __name__ == "__main__":
    main()
