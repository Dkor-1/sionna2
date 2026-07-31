# -*- coding: utf-8 -*-
"""
make_report05_results.py — 리포트 05(검출 결과) 노트북 생성기
==========================================================================================
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report05_results.py

산출: `report05_results.ipynb`. 그림은 `src/viz_report05.py` 가 만든 PNG 8장을 끼운다
(그림이 없으면 이 스크립트가 먼저 그린다).

서술 규약은 `docs/REBUILD_2026-07-30.md` §5 이고, 그 규약의 실행 구현이 `src/report_style.py` 다.
숫자는 전부 `num()`(JSON 대조) 또는 `dnum()`(JSON 에서 계산) 을 통과한다 — 손으로 친 숫자는 없다.

이 편의 주장 경계(다른 편에 흩지 말 것)
------------------------------------------------------------------------------------------
① **밴드 간 비교는 앵커 σ 위에서만** 말한다. 우리 기하의 σ 주파수 기울기는 측정보다 가파르다(02편).
② **바이스태틱은 β≤45°** 안에서만 말한다. 그 밖에서는 상반성(정리) 잔차가 두 자리 dB 다.
③ 절대 검지거리는 **선언 예산 아래의 수**다. EIRP·NF 에 근거문서가 없다(JSON 이 그렇게 적고 있다).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np                                                    # noqa: E402

from report_style import (build_notebook, caption, fetch, from_json,   # noqa: E402
                          header, limits, md, num, table, table_from)

ROOT = os.path.abspath(os.path.join(_HERE, ".."))

# 근거 JSON — 이 편의 모든 숫자가 여기서 나온다
J_FS = "outputs/report13_freespace.json"      # 자유공간 검지거리 4단계
J_SG = "outputs/report13_sigma_grid.json"     # σ 격자(자세 × 밴드) + 바이스태틱 Δσ
J_RX = "outputs/detection_rx_sweep.json"      # 파형 9모드 × 수신소자 N 몬테카를로
J_VF = "outputs/verify_freespace.json"        # 기하·규약 게이트
J_LB = "outputs/verify_linkbudget.json"       # 사슬 항등식 · 파형별 손실항
J_AN = "outputs/sigma_anchor.json"            # 측정 앵커(02편 §4)
J_DF = "outputs/sbr_defect_fixes.json"        # 상반성 잔차(β 창의 근거)

FIGDIR = "outputs/figures"
MODES = ("W1", "L1", "G1")
DRONES = ("mini5pro", "mavic4pro", "matrice4e", "phantom4", "s1000plus")
#: 앵커 JSON 의 밴드 키 ↔ 검출 모드 코드
ANCHOR_BAND = {"W1": "WiFi 5.21 GHz", "L1": "LTE 1.843 GHz", "G1": "5G 3.5 GHz"}
MODE_NAME = {"W1": "WiFi", "L1": "LTE", "G1": "5G"}
CELL = "ranges.{d}.{m}.equal_psd.full_waveform_capture.by_N.1"


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


def derived() -> dict:
    """이 편이 쓰는 파생량을 한 곳에서 계산한다(전부 JSON 입력)."""
    D: dict = {}

    # ── 기하: β=45° · el=−20° 를 넘는 거리 ─────────────────────────────────
    d = np.array(fetch((J_FS, "solve.W1.d_grid_m")), float)
    beta = np.array(fetch((J_FS, "solve.W1.beta_deg")), float)
    el = np.array(fetch((J_FS, "solve.W1.el_look_deg")), float)
    snr = np.array(fetch((J_FS, "solve.W1.snr_d_db")), float)
    D["d_beta45"] = float(np.interp(45.0, beta[::-1], d[::-1]))
    D["snr_at_beta45"] = float(np.interp(D["d_beta45"], d, snr))
    D["d_el20"] = float(np.interp(-20.0, el, d))
    D["el_grid_min"] = float(min(fetch((J_SG, "meta.el_deg"))))

    # ── R90 범위(5기종 × 3밴드) ──────────────────────────────────────────
    R = {(dr, m): cell(dr, m, "R90_C50_m") / 1e3 for dr in DRONES for m in MODES}
    D["R90"] = R
    D["R90_min"], D["R90_max"] = min(R.values()), max(R.values())
    D["R90_min_key"] = min(R, key=R.get)
    D["R90_max_key"] = max(R, key=R.get)

    # ── 헤딩 평균 Pd 의 최댓값(= 가장 잘 버틴 칸) ───────────────────────────
    E = {(dr, m): cell(dr, m, "E_psi_Pd_at_R90") for dr in DRONES for m in MODES}
    D["E_max"] = max(E.values())
    D["E_max_key"] = max(E, key=E.get)

    # ── 앵커 σ 로 옮긴 R90 (국소 지수 1차 전이) ─────────────────────────────
    A = {}
    for dr in DRONES:
        for m in MODES:
            n = cell(dr, m, "n_local_at_R90")
            dd = fetch((J_AN, f"drones.{dr}.modes.slope_only.delta_db.{ANCHOR_BAND[m]}"))
            A[(dr, m)] = R[(dr, m)] * 10 ** (dd / (10 * n))
    D["R90_anch"] = A
    D["n_local"] = float(np.mean([cell(dr, m, "n_local_at_R90")
                                  for dr in DRONES for m in MODES]))
    sp = {dr: 10 * D["n_local"] * np.log10(max(A[(dr, m)] for m in MODES)
                                           / min(A[(dr, m)] for m in MODES))
          for dr in DRONES}
    D["band_spread"] = sp
    D["spread_phantom4"] = sp["phantom4"]
    D["spread_max"] = max(sp.values())
    D["spread_max_drone"] = max(sp, key=sp.get)

    # ── 다중 수신기: 이상적 상한 대비 초과분 ────────────────────────────────
    ns = [int(n) for n in fetch((J_RX, "meta.n_list"))]
    ex, gain = [], {}
    for mo in fetch((J_RX, "meta.modes")):
        s = [fetch((J_RX, f"modes.{mo}.curves.{n}.snr50")) for n in ns]
        for v, n in zip(s, ns):
            ex.append((s[0] - v) - 10 * np.log10(n))
        gain[mo] = [s[0] - v for v in s]
    D["ns"] = ns
    D["rx_gain_W1"] = gain["W1"]
    D["rx_bound"] = [10 * np.log10(n) for n in ns]
    D["rx_excess_max"] = float(max(ex))
    D["rx_excess_min"] = float(min(ex))

    # ── 상반성 잔차: β≤45° 안 / 전체 ───────────────────────────────────────
    rows = fetch((J_DF, "d2_reciprocity_drone.rows"))
    D["recip_in"] = max(r["worst_db"] for r in rows if r["beta_deg"] <= 45)
    D["recip_all"] = max(r["worst_db"] for r in rows)

    # ── 감도사슬: σ 항이 밴드 사이에서 만드는 폭 ────────────────────────────
    sg = {m: cell("mavic4pro", m, "budget_terms_db.sigma") for m in MODES}
    D["sigma_span"] = max(sg.values()) - min(sg.values())
    return D


# --------------------------------------------------------------------------- #
#  블록
# --------------------------------------------------------------------------- #
def build_blocks(D: dict):
    FS, RX, AN = from_json(J_FS), from_json(J_RX), from_json(J_AN)
    VF, LB = from_json(J_VF), from_json(J_LB)

    def C(dr, m, key, fmt=None, unit=""):
        """짧은 키에는 칸마다 출처 태그를 붙인다."""
        return num(None, (J_FS, CELL.format(d=dr, m=m) + "." + key), fmt, unit)

    def V(dr, m, key, fmt):
        """긴 키(ranges.…by_N.1.…)의 표는 **표 하나에 태그 하나**로 간다 — 칸이 읽히도록."""
        return fmt.format(cell(dr, m, key))

    #: V() 로 만든 표 밑에 붙이는 출처 한 줄
    SRC_RANGE = (f"출처 ⟨{J_FS} : "
                 + CELL.format(d="mavic4pro", m="*") + ".{}⟩")

    blocks = []

    # ── 6블록 서두 ────────────────────────────────────────────────────────── #
    blocks.append(header(
        num=5,
        title="검출 결과: 어느 조명원으로 어느 거리까지 보이나",
        question="자유공간에서 어느 조명원으로, 수신소자 몇 개로, 드론이 어느 거리까지 보이는가?",
        conclusion_lines=[
            f"선언 예산(EIRP {FS.num('meta.link_budget.eirp_dbm', 63.0, '{:.0f}', 'dBm')}) · "
            f"베이스라인 {FS.num('solve.W1.L_m', 500.0, '{:.0f}', 'm')} · CPI "
            f"{FS.num('solve.W1.T_cpi_s', 0.1, '{:.1f}', 's')} 에서 공칭 자세 R90"
            "(Pd=0.9 가 유지되는 최대 수평거리)은 "
            f"{dnum(D['R90_min'], '{:.2f}', 'km', f'{J_FS} : ranges.*.R90_C50_m', '5기종×3밴드 최소')}"
            f" ~ {dnum(D['R90_max'], '{:.2f}', 'km', f'{J_FS} : ranges.*.R90_C50_m', '최대')} 다.",
            f"그 R90 은 **자세 한 점**의 수다. 헤딩을 균일 평균하면 같은 거리의 Pd 가 "
            f"{dnum(D['E_max'], '{:.2f}', '', f'{J_FS} : ranges.*.E_psi_Pd_at_R90', '15칸 최대')} "
            "이하로 내려간다.",
            f"5G SSB 는 PRF {FS.num('waveforms.G1.prf_hz', 50.0, '{:.0f}', 'Hz')} → 프레임 "
            f"{FS.num('waveforms.G1.M', 5, '{:.0f}')}개라 0-도플러 가드가 도플러 축 전체를 덮는다"
            f" — 눈먼 헤딩 비율 {C('mavic4pro', 'G1', 'blind_heading_frac', '{:.3f}')}.",
            f"파형 우열이 결판나는 축은 σ 를 곱하기 **전**, 기준신호 대역이다(§3.4) — Pd=0.5 에 "
            "필요한 출력 SNR 은 WiFi "
            f"{RX.num('modes.W1.curves.1.snr50', None, '{:.2f}', 'dB')} · LTE "
            f"{RX.num('modes.L1.curves.1.snr50', None, '{:.2f}', 'dB')} · 5G "
            f"{RX.num('modes.G1.curves.1.snr50', None, '{:.2f}', 'dB')}.",
            f"수신소자 N 의 이득 상한은 10log₁₀N 이고 측정 초과분은 최대 "
            f"{dnum(D['rx_excess_max'], '{:.2f}', 'dB', f'{J_RX} : modes.*.curves.*.snr50', '9모드×N 최대')}"
            " — 실이득이 아니라 추정 편향이다.",
        ],
        claims=[
            "**같은 표적·같은 기하·같은 검출기**에서 잰 세 파형의 상대 비교 — Pfa 를 경험적으로 교정했다",
            "감도사슬의 **항별 분해** — dB 로 닫힌다(합이 출력 SNR 과 일치)",
            "**β≤45°** 안의 바이스태틱 검지거리 구조와 그 구속 벽(직접파 잔차)",
            "수신소자 N 의 **이상적 상한**과 측정치가 그 상한에서 벗어난 크기",
            "밴드 간 비교는 **앵커 σ 위에서만**(§3.3) — 우리 기하의 σ(f) 기울기는 쓰지 않는다",
        ],
        non_claims=[
            "**절대 검지거리** — σ 레벨이 우리 기하에서 왔다(02 §4). 예산도 선언값이다",
            "**β>45°** 바이스태틱 — 상반성 잔차가 두 자리 dB 다(§1.1)",
            "**분산 배치 다중 수신기** — N 은 한 지점 λ/2 ULA 소자 수다(§4)",
            "지면 반사·클러터·환경 — 이 편은 자유공간만 푼다",
            "마이크로도플러·추적 — future work",
        ],
        prereq=[("02 §4", "σ 의 레벨과 주파수 기울기가 왜 측정 앵커에서 오는지"),
                ("03 §2", "조명원 선택의 dB 원장 — 점유 · λ² · 듀티 · PRF"),
                ("04", "CFAR 문턱, 명목 Pfa 와 경험 Pfa 의 차이, ECA 잔차")],
        repro=dict(
            cmd=["cd /home/yunjung/workspace/sionna2",
                 "# ① σ 격자(자세 × 밴드) — 05 는 읽기만 한다",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py",
                 "# ② 검지거리 4단계 — 기종마다 1회(결과는 add-only 로 쌓인다)",
                 "for D in mini5pro mavic4pro matrice4e phantom4 s1000plus; do \\",
                 "  PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_range.py \\",
                 "    --stage all --mode W1,L1,G1 --drone $D; done",
                 "# ③ 기하·규약 게이트",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_freespace.py",
                 "# ④ 파형 9모드 × 수신소자 N 몬테카를로",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_detection.py",
                 "# ⑤ 그림 8장 + 이 노트북",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report05.py",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report05_results.py"],
            out=[J_FS, J_SG, J_RX, J_VF],
            runtime=f"② 기종당 {FS.num('meta.runtime_s', None, '{:.0f}', 's')}"
                    f"(GPU {FS.num('meta.gpus', None)}장) · "
                    f"③ {VF.num('meta.runtime_s', None, '{:.2f}', 's')} · "
                    f"④ K={RX.num('meta.K', None, '{:.0f}')} 로 GPU 수십 분 · ⑤ 초 단위",
            note="②는 add-only 다 — 한 기종만 다시 돌려도 나머지 칸은 남는다.",
        ),
    ))

    # ── §1 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §1. 기하 — 무엇을 어디에 두었나",
        "",
        "조명원(TX)과 패시브 수신기(RX)는 지상에 고정, 표적은 두 점의 중점에서 수평거리 `d` 만큼 "
        "떨어진 공중에 있다. 아래 값은 전부 **선언**이며 근거문서가 없다. "
        "따라서 이 편의 거리는 *참값*이 아니라 **이 예산 아래의 거리**다.",
        "",
        table(["항목", "값", "무엇을 정하나"],
              [["베이스라인 $L$", FS.num("solve.W1.L_m", 500.0, "{:.0f}", "m"), "β(d) 와 직접파 세기"],
               ["표적 고도", FS.num("solve.W1.alt_m", 60.0, "{:.0f}", "m"), "이등분선 앙각 el"],
               ["장면 방위 $\\varphi$", FS.num("solve.W1.phi_deg", 90.0, "{:.0f}", "°"), "R1·R2 의 비"],
               ["EIRP", FS.num("meta.link_budget.eirp_dbm", 63.0, "{:.0f}", "dBm"),
                FS.num("meta.link_budget.provenance", None)],
               ["수신이득 · NF", FS.num("meta.link_budget.rx_gain_dbi", 10.0, "{:.0f}", "dBi")
                + " · " + FS.num("meta.link_budget.noise_figure_db", 5.0, "{:.0f}", "dB"), "잡음바닥"],
               ["CPI", FS.num("solve.W1.T_cpi_s", 0.1, "{:.1f}", "s"), "프레임 수 M = CPI·PRF"],
               ["기준채널",
                FS.num("meta.link_budget.power_normalization.canonical_reference", None),
                "상관에 쓸 수 있는 에너지 — 파일럿만 받는 수신기는 §5 를 볼 것"]]),
        "",
        "좌표 상수는 `src/freespace_scene.py:72`, 기하 함수는 `src/freespace_scene.py:117`. "
        f"기하·규약 게이트 {VF.num('summary.n_ran', None, '{:.0f}')}건 중 실패 "
        f"{VF.num('summary.n_fail', 0, '{:.0f}')}건이다.",
    ))

    blocks.append(md(
        "### §1.1 유효창 — 왜 근거리는 주장에서 뺐나",
        "",
        f"β 는 근거리에서 커진다. β>45° 인 구간은 `d` < "
        f"{dnum(D['d_beta45'], '{:.0f}', 'm', f'{J_FS} : solve.W1.beta_deg', 'β=45° 보간')} 이고, "
        f"거기서 SNR 은 이미 "
        f"{dnum(D['snr_at_beta45'], '{:.0f}', 'dB', f'{J_FS} : solve.W1.snr_d_db', '위 거리에서 보간')} "
        "라 검출이 문제되지 않는다. 그 구간을 뺀 이유는 둘 다 **커널 쪽**이다.",
        "",
        table(["빼는 이유", "수치", "어디서"],
              [["상반성(정리) 잔차가 크다",
                "β≤45° 최대 " + dnum(D["recip_in"], "{:.2f}", "dB",
                                    f"{J_DF} : d2_reciprocity_drone.rows", "β≤45 행 최대")
                + " · 전체 최대 " + dnum(D["recip_all"], "{:.2f}", "dB",
                                       f"{J_DF} : d2_reciprocity_drone.rows", "전 행 최대"),
                "`src/rcs_sbr.py`"],
               ["σ 격자의 고도 행 밖으로 나간다",
                "el 하한 " + dnum(D["el_grid_min"], "{:.0f}", "°", f"{J_SG} : meta.el_deg", "최솟값")
                + " · `d` < " + dnum(D["d_el20"], "{:.0f}", "m",
                                    f"{J_FS} : solve.W1.el_look_deg", "el=−20° 보간") + " 에서 이탈",
                "`src/experiment_freespace_sigma.py:70`"]]),
        "",
        f"헤드라인 거리에서는 β = {dnum(float(np.interp(fetch((J_FS, 'solve.W1.R_m')), np.array(fetch((J_FS, 'solve.W1.d_grid_m')), float), np.array(fetch((J_FS, 'solve.W1.beta_deg')), float))), '{:.2f}', '°', f'{J_FS} : solve.W1.beta_deg', 'R90 에서 보간')}"
        f" 로 **준모노스태틱**이다. σ 는 이등분선 방향의 모노스태틱 값을 쓴다"
        f"(`src/experiment_freespace_sigma.py:227`).",
    ))

    blocks.append(md(
        f"![geometry]({FIGDIR}/report05_f1_geometry.png)", "",
        caption(1, "헤드라인 거리는 바이스태틱 유효창(β≤45°) 안에 있는가?"),
    ))

    # ── §2 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §2. 감도사슬 — 출력 SNR 이 어떤 항들의 합인가",
        "",
        f"d = 1 km · Mavic 4 Pro · 수신소자 1개에서 각 항을 dB 로 적는다. 합이 출력 SNR 이다"
        f"(점유 규약 {FS.num('meta.link_budget.power_normalization.canonical_occupancy', None)}"
        " — 같은 RE 당 전력).",
        "",
        table(["항", "WiFi", "LTE", "5G"],
              [[name] + [V("mavic4pro", m, f"budget_terms_db.{k}", "{:+.2f}") for m in MODES]
               for name, k in [("$\\lambda^2$", "lambda2"), ("$\\sigma$(공칭 자세)", "sigma"),
                               ("확산 $1/(4\\pi)^3R_1^2R_2^2$", "spread"), ("$1/N_0$", "n0"),
                               ("CPI", "t_cpi"), ("**출력 SNR**", "total")]]),
        "",
        SRC_RANGE.format("budget_terms_db"),
        "",
        f"⭐ 밴드 간 격차를 만드는 것은 λ² 가 아니라 **σ 항**이다 — 같은 기체·같은 자세에서 세 밴드의 σ 가 "
        f"{dnum(D['sigma_span'], '{:.1f}', 'dB', f'{J_FS} : ranges.mavic4pro.*.budget_terms_db.sigma', '3밴드 최대−최소')}"
        " 벌어진다. 이것은 파형의 우열이 아니라 **자세 로브 구조**다(§3.3).",
    ))

    blocks.append(md(
        f"![budget]({FIGDIR}/report05_f2_budget.png)", "",
        caption(2, "1 km 에서 출력 SNR 은 어떤 항들의 합으로 만들어지는가?"),
    ))

    blocks.append(md(
        "### §2.1 어느 벽이 거리를 정하나",
        "",
        f"헤드라인 칸의 구속 벽은 열잡음이 아니라 **직접파 잔차**다"
        f"({FS.num('solve.W1.limit', None)}). ECA 억압 깊이를 바꾸면 거리가 이렇게 움직인다.",
        "",
        table(["ECA 깊이", "R90"],
              [[f"{k} dB" if k != "inf" else "완전 억압",
                num(None, (J_FS, f"solve.W1.sensitivity_eca_depth.{k}.R_m"), "{:.0f}", "m")]
               for k in ("40", "60", "90", "inf")]),
        "",
        f"예산을 키우면: EIRP 를 "
        f"{num(None, (J_FS, 'solve.W1.sensitivity_eirp.eirp_dbm[6]'), '{:.0f}', 'dBm')} 으로 "
        f"올리면 {num(None, (J_FS, 'solve.W1.sensitivity_eirp.R_thermal_m[6]'), '{:.0f}', 'm')}, "
        f"CPI 를 {num(None, (J_FS, 'solve.W1.sensitivity_cpi.t_cpi_s[3]'), '{:.1f}', 's')} 로 "
        f"늘리면 {num(None, (J_FS, 'solve.W1.sensitivity_cpi.R90_m[3]'), '{:.0f}', 'm')} 다"
        " — 둘 다 열잡음 축이라 직접파 잔차가 먼저 물리면 소용이 없다.",
    ))

    blocks.append(md(
        f"![walls]({FIGDIR}/report05_f7_walls.png)", "",
        caption(3, "베이스라인을 바꾸면 어느 한계가 검지거리를 구속하는가?"),
    ))

    # ── §3 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §3. 세 파형 벤치마크",
        "",
        "세 조명원은 각 표준이 **늘 켜 두는 기준신호**다 — WiFi VHT-LTF(W1) · LTE CRS(L1) · "
        "5G SSB(G1). 제원은 03 §1, 여기서는 그 셋을 같은 검출기에 물린다.",
        "",
        "### §3.1 먼저 문턱을 교정한다",
        "",
        "명목 Pfa 를 그대로 쓰면 파형 비교가 성립하지 않는다. CFAR 문턱을 **경험 Pfa 가 목표에 "
        "수렴하도록** 잡고, 그 문턱에서 Pd 곡선을 잰다.",
        "",
        table(["모드", "명목 Pfa", "경험 Pfa", "경험/명목"],
              [[lab, num(None, (J_FS, f"threshold.pfa.{m}.nominal"), "{:.2e}"),
                num(None, (J_FS, f"threshold.pfa.{m}.empirical"), "{:.2e}"),
                num(None, (J_FS, f"threshold.pfa.{m}.ratio_emp_over_nominal"), "{:.3f}")]
               for lab, m in (("WiFi", "W1"), ("LTE", "L1"), ("5G", "G1"))]),
        "",
        f"목표는 {FS.num('threshold.pfa.W1.target', 1e-4, '{:.0e}')} 다. 5G 의 명목 Pfa 는 "
        f"경험값의 "
        f"{dnum(1.0 / fetch((J_FS, 'threshold.pfa.G1.ratio_emp_over_nominal')), '{:.0f}', '배',
               f'{J_FS} : threshold.pfa.G1.ratio_emp_over_nominal', '역수')} 다(04편).",
        "",
        "⚠ 5G 의 Pd 곡선 자체는 이 실행에서 재지 못했다 — 그림 4 와 §5 를 볼 것.",
    ))

    blocks.append(md(
        f"![detector]({FIGDIR}/report05_f3_detector.png)", "",
        caption(4, "교정된 문턱에서 각 파형이 Pd=0.9 에 필요로 하는 출력 SNR 은 몇 dB 인가?"),
    ))

    blocks.append(md(
        "### §3.2 공칭 자세의 R90, 그리고 그 수가 견디지 못하는 것",
        "",
        f"5기종 × 3밴드의 R90 은 {dnum(D['R90_min'], '{:.2f}', 'km', f'{J_FS} : ranges.*.R90_C50_m', '최소')}"
        f"({D['R90_min_key'][0]} · {MODE_NAME[D['R90_min_key'][1]]}) 에서 "
        f"{dnum(D['R90_max'], '{:.2f}', 'km', f'{J_FS} : ranges.*.R90_C50_m', '최대')}"
        f"({D['R90_max_key'][0]} · {MODE_NAME[D['R90_max_key'][1]]}) 사이다. "
        "그러나 이 수는 **자세 한 점**에서 나온다.",
        "",
        table(["모드", "눈먼 헤딩 비율", "커버리지 상한", "같은 R90 의 헤딩평균 Pd(Mavic 4 Pro)"],
              [[lab, V("mavic4pro", m, "blind_heading_frac", "{:.3f}"),
                V("mavic4pro", m, "coverage_ceiling", "{:.3f}"),
                V("mavic4pro", m, "E_psi_Pd_at_R90", "{:.3f}")]
               for lab, m in (("WiFi", "W1"), ("LTE", "L1"), ("5G", "G1"))]),
        "",
        SRC_RANGE.format("blind_heading_frac · coverage_ceiling · E_psi_Pd_at_R90"),
        "",
        "⭐ 5G 는 **모든 헤딩에서 눈이 먼다**. 거리가 아니라 도플러에서 먼저 죽는다는 뜻이라, "
        f"5G 의 R90 은 형식적인 수다. 이 판정의 표적 속도 규약은 "
        f"{VF.num('checks.nyquist_fold_check.v_ms', 5.0, '{:.0f}', 'm/s')} 다.",
    ))

    blocks.append(md(
        f"![range bars]({FIGDIR}/report05_f4_range_bars.png)", "",
        caption(5, "공칭 자세에서 기종별·밴드별로 Pd=0.9 가 유지되는 거리는 몇 km 인가?"),
    ))

    blocks.append(md(
        f"![heading]({FIGDIR}/report05_f5_heading.png)", "",
        caption(6, "R90 한 숫자가 표적 헤딩을 균일 평균해도 살아남는가?"),
    ))

    # ── §3.3 밴드 비교 ─────────────────────────────────────────────────────── #
    blocks.append(md(
        "### §3.3 ⭐ 밴드 간 비교 — 앵커 σ 위에서만",
        "",
        "우리 기하의 σ 주파수 기울기는 측정보다 가파르다(02 §4). 그래서 밴드 비교는 **앵커로 "
        "재보정한 σ** 위에서만 말한다. 재보정은 기울기만 측정값으로 돌리고 각도 패턴은 건드리지 "
        f"않는다 — 정규화 패턴 변화 "
        f"{AN.num('drones.phantom4.shape_invariance_max_abs_db', None, '{:.1e}', 'dB')}.",
        "",
        table_from(f"{J_AN}:drones",
                   [("기체", None),
                    ("Δσ WiFi", "modes.slope_only.delta_db.WiFi 5.21 GHz"),
                    ("Δσ LTE", "modes.slope_only.delta_db.LTE 1.843 GHz"),
                    ("Δσ 5G", "modes.slope_only.delta_db.5G 3.5 GHz"),
                    ("보정 후 기울기", "modes.slope_only.slope_after_db_per_ghz"),
                    ("앵커 비교가능성", "comparability.verdict")],
                   fmt={"modes.slope_only.delta_db.LTE 1.843 GHz": "{:+.2f} dB",
                        "modes.slope_only.delta_db.5G 3.5 GHz": "{:+.2f} dB",
                        "modes.slope_only.delta_db.WiFi 5.21 GHz": "{:+.2f} dB",
                        "modes.slope_only.slope_after_db_per_ghz": "{:.3f} dB/GHz"},
                   order=list(DRONES)),
    ))

    blocks.append(md(
        f"이 Δσ 를 R90 으로 옮길 때는 R90 근방의 **국소 지수** "
        f"{dnum(D['n_local'], '{:.3f}', '', f'{J_FS} : ranges.*.n_local_at_R90', '15칸 평균')} "
        "를 쓴다(`d` 축에서 R ∝ σ^¼ 는 전역적으로 성립하지 않는다, `src/freespace_scene.py:56`).",
        "",
        table(["기체", "WiFi", "LTE", "5G"],
              [[dr] + [f"{D['R90_anch'][(dr, m)]:.2f} km" for m in MODES] for dr in DRONES]),
        "",
        f"출처 ⟨{J_AN} : drones.*.modes.slope_only.delta_db⟩",
        "",
        f"⚠ 결판나지 않는다. 앵커와 **직접 비교 가능한** 유일한 기체(Phantom 4)에서 세 밴드의 폭은 "
        f"{dnum(D['spread_phantom4'], '{:.2f}', 'dB', f'{J_AN} : drones.phantom4.modes.slope_only', 'σ등가 폭')}"
        f" 인데, 앵커가 통제하지 못한 항 하나가 "
        f"{num(None, (J_AN, 'uncontrolled[2].size_db'), '{:.2f}', 'dB')} 다.",
    ))

    blocks.append(md(
        "밴드 순서는 기체마다 바뀐다. 순서를 만드는 것은 파형이 아니라 **자세별 로브 구조**이고, "
        "앵커는 밴드 평균 레벨만 옮기지 로브를 고치지 않는다.",
        "",
        table_from(f"{J_AN}:uncontrolled",
                   [("앵커가 통제하지 못한 항", "term"), ("상태", "status"), ("크기", "size_db")],
                   fmt={"size_db": "{:+.2f} dB"}, null="미상"),
    ))

    blocks.append(md(
        f"![anchored bands]({FIGDIR}/report05_f8_anchored_bands.png)", "",
        caption(7, "밴드 격차가 앵커의 미통제 항보다 커서 파형의 우열로 읽히는가?"),
    ))

    blocks.append(md(
        "### §3.4 그래서 무엇이 파형 비교로 남나",
        "",
        "σ 를 곱하기 **전** 축은 남는다. 같은 표적·같은 기하·같은 검출기에서 Pd=0.5 에 필요한 "
        "출력 SNR 이 그것이고, 이 차이는 기준신호 대역과 프레임 수에서 나온다.",
        "",
        table_from(f"{J_RX}:modes",
                   [("모드", None), ("기준신호", "ref_name"), ("$B_{ref}$", "ref_bw_mhz"),
                    ("프레임 M", "M"), ("Pd=0.5 필요 SNR", "curves.1.snr50")],
                   fmt={"ref_bw_mhz": "{:.1f} MHz", "M": "{:.0f}",
                        "curves.1.snr50": "{:.2f} dB"},
                   order=["W1", "L1", "G1"]),
        "",
        f"5G 를 세션 신호(NR-PRS, {RX.num('modes.G3.ref_bw_mhz', None, '{:.1f}', 'MHz')})까지 "
        f"열어주면 {RX.num('modes.G3.curves.1.snr50', None, '{:.2f}', 'dB')} 로 내려간다 — "
        "상시 신호만 쓰는 체제의 대가다(03 §1.1).",
        "",
        f"⚠ 이 스윕의 CPI·PRF 규약은 §1 과 다르다 — SSB 를 PRF "
        f"{RX.num('modes.G1.prf', None, '{:.0f}', 'Hz')} 로 타일링한다(물리값은 "
        f"{FS.num('waveforms.G1.prf_hz', 50.0, '{:.0f}', 'Hz')}, §3.2). "
        "그래서 여기서 인용하는 것은 **같은 조건에서의 모드 간 상대 비교**뿐이다.",
    ))

    # ── §4 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §4. 수신소자를 늘리면",
        "",
        f"N 은 **한 지점의 λ/2 ULA 소자 수**다(`src/experiment_detection.py:181`) — 흩어놓은 "
        "N 개의 패시브 수신기가 아니다. 조향벡터는 참 표적 방향에 정확히 맞춰지므로 결과는 "
        "**이상적 상한**이다.",
        "",
        table(["N"] + [str(n) for n in D["ns"]],
              [["측정 이득 (WiFi) = SNR50(1)−SNR50(N)"]
               + [f"{g:+.2f} dB" for g in D["rx_gain_W1"]],
               ["상한 10log₁₀N"] + [f"{b:+.2f} dB" for b in D["rx_bound"]]]),
        "",
        f"출처 ⟨{J_RX} : modes.W1.curves.*.snr50⟩",
        "",
        f"9모드 전체에서 상한 초과분은 "
        f"{dnum(D['rx_excess_min'], '{:+.2f}', '', f'{J_RX} : modes.*.curves.*.snr50', '최소')} ~ "
        f"{dnum(D['rx_excess_max'], '{:+.2f}', 'dB', f'{J_RX} : modes.*.curves.*.snr50', '최대')} 다. "
        f"결합 잡음전력/σ² = {RX.num('modes.W1.combine_ratio', None, '{:.5f}')} 로 잡음 보존을 확인했다.",
    ))

    blocks.append(md(
        f"![multi rx]({FIGDIR}/report05_f6_multirx.png)", "",
        caption(8, "수신소자를 늘렸을 때 얻는 감도는 코히어런트 상한에 얼마나 붙는가?"),
    ))

    blocks.append(md(
        "> ⚠ 이 스윕은 **짧은 베이스라인 벤치 기하**에서 돌았다(`src/experiment_x410.py:101`). "
        "여기서 인용하는 것은 N 사이의 **상대 이득**뿐이고, 절대 SNR50 은 §1 의 자유공간 배치가 아니다.",
    ))

    # ── 한계 ──────────────────────────────────────────────────────────────── #
    blocks.append(limits([
        ("앵커 σ 로 자유공간 해를 다시 풀지 않았다 — §3.3 은 국소 지수로 옮긴 1차 전이다",
         "`src/sigma_anchor.py` 의 보정 σ 를 격자로 써서 "
         "`src/experiment_freespace_range.py --stage solve` 재실행"),
        (f"σ 격자 판({num(None, (J_SG, 'meta.generated'))})이 자유공간 해"
         f"({num(None, (J_FS, 'meta.generated'))})보다 나중이다",
         "같은 격자로 ②를 다시 돌려 두 시각을 맞춘다"),
        (f"5G 의 Pd=0.9 문턱은 측정되지 않았다 — "
         f"{num(None, (J_FS, 'detector_transfer.S_G.G1.N.1.dopoff.3.reason'))}",
         "`src/experiment_freespace_range.py` 의 dopoff 격자를 M 인식으로 고치고 재측정. "
         "지금 5G 는 WiFi 에서 잰 문턱을 빌려 쓴다"),
        ("파형·수신소자 스윕이 자유공간 배치가 아니고 CPI·PRF 규약도 §1 과 다르다(§3.4 · §4 주의)",
         "`src/experiment_detection.py` 의 X410Scenario 를 `src/freespace_scene.py` 기하로, "
         "`CPI_CFG` 를 물리 반복률(`src/freespace_scene.py:233`)로 바꾸면 절대값도 이 편에 들어온다"),
        ("β>45° 바이스태틱 σ 는 주장 밖이다",
         "`src/rcs_sbr.py` 의 출사 가시성·대칭화가 정착한 뒤 "
         "`benchmark/verify_sbr_defect_fixes.py` 로 잔차 재측정"),
        ("기준채널이 full-waveform capture 다 — 파일럿만 받는 수신기는 WiFi 에서 "
         f"{num(None, (J_LB, 'BE_processing_gain.waveforms[0].pilot_power_frac_db'), '{:.2f}', 'dB')} "
         "를 잃는다(이 항은 파형 수준 양이라 배치와 무관하다)",
         "`src/experiment_freespace_range.py` 의 CANON_REF 를 pilot_only 로 두고 두 열 병기"),
        ("지면 반사·클러터가 빠져 있다(자유공간 FS-1)",
         "`sensitivity.baseline` 의 F⁴ 항을 켜고 FS-3 사다리로 올라간다"),
    ], sec="§5."))

    return blocks


# --------------------------------------------------------------------------- #
def main():
    fig1 = os.path.join(ROOT, FIGDIR, "report05_f8_anchored_bands.png")
    if not os.path.exists(fig1):
        print("그림이 없다 — src/viz_report05.py 를 먼저 돌린다")
        import viz_report05
        viz_report05.main()

    D = derived()
    rep = build_notebook("report05_results.ipynb", build_blocks(D), strict=True)
    print(f"\n생성: report05_results.ipynb  "
          f"(마크다운 {rep['md_cells']}셀 · 그림 {rep['figures']} · "
          f"출처태그 {rep['provenance_tags']}개)")
    return rep


if __name__ == "__main__":
    main()
