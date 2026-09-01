# -*- coding: utf-8 -*-
"""
build_part10_results.py — 부 10 「검출 결과」 11편(56~66)을 짓는다
==========================================================================================
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py

산출
    reports/56_geometry.ipynb            TX·RX·표적 배치와 β·앙각·원거리장이 유효창을 연다
    reports/57_sensitivity-chain.ipynb   세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다
    reports/58_shared-threshold.ipynb    자유공간 형상에서 문턱을 다시 재니 세 밴드가 SNR90 하나를 공유한다
    reports/59_slope-anchor.ipynb        레벨을 맞추려면 크기전이 법칙을 골라야 하므로 기울기만 받는다
    reports/60_r90.ipynb                 앵커 σ 위의 R90 과 기체별 밴드 순서
    reports/61_rank-durability.ipynb     그 순위는 자세평균이면 하나로 모이고, 문턱은 봉투 안이다
    reports/62_cpi-sweep.ipynb           CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다
    reports/63_cpi-residual.ipynb        모호속도는 표본화율의 성질이라 CPI 와 무관한 상한이다
    reports/64_sigma-free-axis.ipynb     σ 를 곱하기 전에 이미 세 파형의 순서를 정하는 축이 있다
    reports/65_target-model-swap.ipynb   표적 모형을 갈아끼우면 요구 이득이 이만큼 달라진다
    reports/66_rx-elements.ipynb         코히어런트 배열이득은 10log₁₀N 상한에 바짝 붙는다
    docs/paper/05_results.md             논문 조각(옛 report05 의 논문 부록)
    outputs/reports_index/<anchor>.json

⚠ 파생 수치는 `make_report05_results.derived()` 를 **읽기 전용으로 임포트해서** 받는다 —
  같은 함수가 낸 같은 값이라야 옛 편과 새 편의 숫자가 어긋나지 않는다.
  그 함수는 JSON 만 읽고 아무 파일도 쓰지 않는다(파일 쓰기는 `write_derived()` 가 한다).
⚠ 이 파일은 서술을 옮길 뿐 아무것도 새로 계산하지 않는다. GPU·Sionna 를 쓰지 않는다.

서술 출처 — 옛 `report05_results.ipynb` 의 셀
    c2·c3 → 56 · c4~c7 → 57 · c8~c10 → 58 · c11·c12 → 59 · c13·c14 → 60 ·
    c15 → 61 · c16·c17 → 62 · c18 → 63 · c19 → 64 · c20 → 65 · c21·c22 → 66 ·
    c23 → docs/paper/05_results.md
"""
from __future__ import annotations

import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import make_report05_results as R5                                    # noqa: E402
from freespace_scene import BETA_VALID_MAX_DEG as _BETA_MAX           # noqa: E402
from report_registry import index_shard, nb_path, ref                 # noqa: E402
from report_style import (build_notebook, caption, fetch, from_json,   # noqa: E402
                          header, md, next_steps, num, table, table_from)

# ── 근거 JSON (옛 빌더와 같은 이름을 그대로 쓴다) ──────────────────────────── #
J_FS, J_SG, J_SG_USED = R5.J_FS, R5.J_SG, R5.J_SG_USED
J_RX, J_VF, J_LB = R5.J_RX, R5.J_VF, R5.J_LB
J_AN, J_DF, J_SS, J_CG, J_DV = R5.J_AN, R5.J_DF, R5.J_SS, R5.J_CG, R5.J_DV
J_TM, J_TA, J_PH, J_SV = R5.J_TM, R5.J_TA, R5.J_PH, R5.J_SV
J_LFA, J_MFX, J_MFX_ATK = R5.J_LFA, R5.J_MFX, R5.J_MFX_ATK
J_LFN = "outputs/lowfreq_anchor.json"

MODES, MODE_NAME, DRONES, CELL = R5.MODES, R5.MODE_NAME, R5.DRONES, R5.CELL
dnum = R5.dnum

FIG = "../outputs/figures"
PF = {n: f"{FIG}/report05_pf{i}_{n}.png" for i, n in
      enumerate(("gap", "ranking", "robust", "cpi", "multirx", "detector", "anchor"), start=1)}

FS, RX, AN = from_json(J_FS), from_json(J_RX), from_json(J_AN)
VF, SS, CG = from_json(J_VF), from_json(J_SS), from_json(J_CG)
DV, TM, TA = from_json(J_DV), from_json(J_TM), from_json(J_TA)
PH, SV = from_json(J_PH), from_json(J_SV)
LFA, MFX = from_json(J_LFA), from_json(J_MFX)

D = R5.derived()                      # 파생 수치 — JSON 만 읽는다

PHC = "verdict.claims[2].range_over_phi"

# ── φ 스윕은 세 팔을 다 냈는데 본문은 W1 한 팔만 인용해 «세 팔 모두» 를 말했다.
#    세 팔을 실제로 읽어 판정하고, 인용도 세 팔의 폭으로 싣는다. ─────────────────── #
_PHI_MIN_ALL = all(
    str(fetch(("outputs/phi_sweep.json", f"{PHC}.constant_sigma_control.{m}.phi90_is")))
    == "minimum" for m in ("W1", "L1", "G1"))
_PHI_SPANS = {m: float(fetch(("outputs/phi_sweep.json",
                              f"{PHC}.constant_sigma_control.{m}.span_pct_of_phi90")))
              for m in ("W1", "L1", "G1")}
PHI90_VERDICT = ("세 팔(W1·L1·G1) 모두 φ=90° 가 최솟값"
                 if _PHI_MIN_ALL else "φ=90° 가 최솟값인 팔과 아닌 팔이 섞인 상태")
TAE = "Q1_normalisation.recomputed_spread_db_by_matching_estimator"

#: M1 을 3GPP 규정대로(σ_S 를 경로마다 뽑아) 돌린 분기 — 편 65 가 인용한다.
Q5R = "Q5_shape_vs_aspect_dependence.evidence[4].result"
#: M1 의 자세분산. 정규화 (b) 의 다섯 앙상블 전부에서 0 이다 — M1 이 눈금이라 그렇다.
M1_STD = "summary.E0_freespace.b_matched_mean.per_model.M1.snr_spread_std_db.max"
#: p10 정규화의 «순서 계수». 셀 수가 아니라 이 두 계수가 «M1 이 마지막» 을 담은 원장이다.
P10_ORD = "Q1_normalisation.circular_diagnostic_p10.order_counts"

# ── «근거리 SNR 천장» 은 SNR(d) 의 봉우리가 아니라 valid 게이트를 적용한 뒤 남은 격자의
#    argmax 다(`src/freespace_link.py:637`). 그 칸을 원장 배열에서 직접 찾아 게이트 상수
#    의존 · 격자 눈금 · 앙각을 함께 싣는다. ⛔ 손으로 적은 숫자는 쓰지 않는다. ──────────── #
_D_GRID = list(FS.get("solve.W1.d_grid_m"))
_SNR_D = list(FS.get("solve.W1.snr_d_db"))
_BETA_D = list(FS.get("solve.W1.beta_deg"))
_EL_D = list(FS.get("solve.W1.el_look_deg"))
_N_D = len(_D_GRID)
_I_GATE = next(i for i, b in enumerate(_BETA_D) if b <= _BETA_MAX)   # 게이트가 열리는 첫 칸
assert abs(_SNR_D[_I_GATE] - float(FS.get("solve.W1.snr_ceiling_db"))) < 1e-9, (
    "게이트 첫 칸과 원장의 snr_ceiling_db 가 갈라졌다 — 아래 산문을 다시 쓸 것")
_D_STEP_PCT = (_D_GRID[_I_GATE + 1] / _D_GRID[_I_GATE] - 1.0) * 100.0
_CEIL_BY_GATE = " · ".join(
    f"{g:.0f}° → {_SNR_D[next(i for i, b in enumerate(_BETA_D) if b <= g)]:.2f} dB"
    for g in (88.0, _BETA_MAX, 95.0, 100.0))

# ── 클램프 비율의 분모는 **게이트 이전** d 격자 전체다(`benchmark/phi_sweep.py:152`).
#    게이트 뒤에 몇 칸이 남는지는 φ=90° 면 solve 배열로 직접 세고, 다른 방위는 원장이 싣는
#    두 비율의 포함배제 하한까지가 이 원장으로 정해지는 자리다. ───────────────────────── #
_N_VALID = round(PH.get("geometry.rows[18].beta_gate_frac") * _N_D)
_N_CLAMP = sum(1 for e in _EL_D if e < D["el_grid_min"])
_N_CLAMP_GATED = sum(1 for i, e in enumerate(_EL_D)
                     if e < D["el_grid_min"] and i >= _I_GATE)
_D_CLAMP_MAX = max(x for x, e in zip(_D_GRID, _EL_D) if e < D["el_grid_min"])
_N_CLAMP_PHI0 = round(PH.get("geometry.rows[0].frac_el_outside_sigma_grid") * _N_D)
_N_C0_GATED_MIN = max(0, _N_CLAMP_PHI0 + _N_VALID - _N_D)            # 포함배제 하한
_KEY_C0 = f"{J_PH} : geometry.rows[0].frac_el_outside_sigma_grid"

# ── 문턱 차의 잣대 — 두 SNR90 은 K 시행의 Pd 곡선을 SNR 격자에서 보간해 뽑은 값이고,
#    원장이 Wilson 띠와 dopoff 칸들을 함께 싣는다. 차는 그 잣대와 나란히 놓는다.
#    ⚠ 두 반폭의 quadrature 는 **차에 대한 신뢰구간이 아니라 눈금**이다. ─────────────── #
_THR_OFF = {m: FS.get(f"threshold.S_G.{m}.1.dopoff") for m in ("W1", "L1")}
_THR_DOP = int(_THR_OFF["W1"]["3"]["dopoff_bins"])
assert (abs(_THR_OFF["W1"]["3"]["snr90_db"]
            - float(DV.get("threshold.snr90_shared_db"))) < 1e-9
        and abs(_THR_OFF["L1"]["3"]["snr90_db"]
                - float(DV.get("threshold.l1_own_snr90_db"))) < 1e-9), (
    "표의 두 SNR90 이 dopoff 3빈 칸의 값과 갈라졌다 — 아래 산문을 다시 쓸 것")
_THR_K = FS.num("threshold.S_G.W1.1.dopoff.3.K", None, "{:.0f}")
_THR_GRID = list(FS.get("threshold.S_G.W1.1.dopoff.3.snr_grid_db"))
_THR_GRID_STEP = _THR_GRID[1] - _THR_GRID[0]
_THR_QUAD = math.hypot(*(0.5 * (_THR_OFF[m]["3"]["snr90_hi_db"]
                                - _THR_OFF[m]["3"]["snr90_lo_db"])
                         for m in ("W1", "L1")))
_THR_DELTA = float(DV.get("threshold.l1_delta_db"))
_THR_L1_LO = min(v["snr90_db"] for v in _THR_OFF["L1"].values())
_THR_L1_HI = max(v["snr90_db"] for v in _THR_OFF["L1"].values())
_THR_N_OFF = len(_THR_OFF["L1"])
_KEY_L1 = f"{J_FS} : threshold.S_G.L1.1.dopoff.*.snr90_db"
_KEY_QUAD = f"{J_FS} : threshold.S_G.*.1.dopoff.3.snr90_lo_db/hi_db"


def _thr_r90_pct(delta_db: float) -> float:
    """문턱 차 [dB] → R90 차 [%]. `make_report05_results.derived()` 와 같은 식이다."""
    return (10 ** (-delta_db / (10 * D["n_local"])) - 1.0) * 100.0


_THR_R90_LO = _thr_r90_pct(_THR_DELTA + _THR_QUAD)
_THR_R90_HI = _thr_r90_pct(_THR_DELTA - _THR_QUAD)

# 표 밑 «출처» 줄용(태그 통째)과 `dnum()` 안에 넣을 알맹이용을 나눠 둔다 —
# dnum 이 이미 ⟨…⟩ 를 씌우므로 통째를 넘기면 태그가 겹쳐 들어가 출처가 안 열린다.
KEY_R = f"{J_FS} : " + CELL.format(d="*", m="*") + ".R90_C50_m"
KEY_A = f"{J_AN} : drones.*.modes.slope_only.delta_db"
SRC_R = f"출처 ⟨{KEY_R}⟩"
SRC_A = f"출처 ⟨{KEY_A}⟩"
SRC_B = f"출처 ⟨{J_FS} : " + CELL.format(d="mavic4pro", m="*") + ".budget_terms_db⟩"

CMD = ["cd /workspace/sionna",
       "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py",
       "for D in mini5pro mavic4pro matrice4e phantom4 s1000plus; do \\",
       "  PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_range.py \\",
       "    --stage all --mode W1,L1,G1 --drone $D; done",
       "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_freespace.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_detection.py",
       "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/sigma_sensitivity.py",
       "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/cpi_guard_sweep.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python src/sigma_anchor.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py"]

RUNTIME = ("σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 "
           + DV.num("runtime.total_h", None, "{:.1f}", "h")
           + " (GPU " + FS.num("meta.gpus", None) + "장). 이 빌더 자신은 CPU 수 초다")

MESH_WARN = ("⚠ 이 사슬은 " + MFX.num("_meta.date", None) + " 형상 정정 **전** 메쉬 위에 있다 — "
             "다섯 기체 중 Matrice 4E 가 그 정정을 받았다 "
             f"⟨{J_MFX_ATK} : Q6_invalidated_outputs.critical[3]⟩.")

# ── Γ(θ) 세대 판정(조건형) — σ 사슬(report13_freespace)이 Γ(θ) 커널 투입 이후에 다시
#    풀렸으면 이 경고는 빈 문자열이 되어 본문에서 사라진다. 원장이 곧 스위치다. ──────── #
J_AGI = "outputs/angle_gamma_impact.json"
AGI = from_json(J_AGI)
_GAMMA_ON = str(fetch((J_AGI, "_meta.generated"))).replace("T", " ")
_FS_GEN = str(fetch((J_FS, "meta.generated"))).replace("T", " ")

# ⚠ 2026-08-10 적대적 감사가 잡은 **거짓 해제**: 위 한 줄(σ 사슬의 생성 시각)만 보면,
#   σ 격자의 **일부 기체만** Γ(θ) 이후로 재계산돼도 경고가 통째로 사라진다.
#   실제로 σ 격자는 기체별 증분 저장이라 «2기 post + 5기 pre» 혼합 세대가 될 수 있고,
#   meta.generated 는 setdefault 라 첫 세대 시각을 그대로 들고 있다.
#   → 기체별로 세대를 따져 **한 기체라도 이전 세대면 경고를 남긴다**.
_J_SG = "outputs/report13_sigma_grid.json"


def _stale_gamma_drones() -> list:
    """σ 격자에서 Γ(θ) 투입 시각보다 오래된 기체 목록. 판정 불가면 보수적으로 전부 반환."""
    import json as _json
    import os as _os
    p = _os.path.join(_ROOT, _J_SG) if "_ROOT" in globals() else _J_SG
    try:
        g = _json.load(open(p))["sigma"]["grid"]
    except Exception:
        return ["(판정불가)"]
    out = []
    for k, v in g.items():
        gen = str((v or {}).get("generated", "")).replace("T", " ")
        if not gen or gen < _GAMMA_ON:
            out.append(k)
    return out


_STALE = _stale_gamma_drones()
GAMMA_WARN = "" if (_FS_GEN >= _GAMMA_ON and not _STALE) else (
    "⚠ 이 σ 원장은 Γ(θ) 각도 모양(기본 켬, " + AGI.num("_meta.generated", None)
    + ") 이전 커널의 산출이다 — 방위평균 전체 드론 σ 이동은 "
    + AGI.num("whole_drone_sigma_az24_el_-15.mini5pro.delta_db", None, "{:+.2f}") + " ~ "
    + AGI.num("whole_drone_sigma_az24_el_-15.matrice4e.delta_db", None, "{:+.2f}", "dB")
    + ", 프롭 채널 레벨 이동은 "
    + AGI.num("propeller_channel_el_-15_3p5GHz.matrice4e.level_delta_db", None, "{:+.2f}") + " ~ "
    + AGI.num("propeller_channel_el_-15_3p5GHz.mini5pro.level_delta_db", None, "{:+.2f}", "dB")
    + " 다. σ 격자를 Γ(θ) 켠 커널로 재생성한 뒤 이 편을 다시 짓는다.")

# ── M3(우리 SBR+PO 격자) 팔이 선 판 — 형상 정정 시각과 Γ(θ) 도입 시각을 함께 찍는다. ── #
M3_STAMP = ("⚠ 판: " + MFX.num("_meta.date", None) + " 형상 정정 전 메쉬 · "
            + AGI.num("_meta.generated", None) + " Γ(θ) 이전 커널")
M3_STAMP_PLAIN = "⚠ 판: 형상 정정 전 메쉬 · Γ(θ) 이전 커널"

# ── solve 축의 신원 — `solve.*` 는 재현 루프의 마지막 기체 하나가 남긴 판이다.
#    편 60 의 헤드라인 폭(앵커 비교가능 12칸)과 **다른 대상**이라 이름을 함께 찍는다. ──── #
SOLVE_ARM = ("기체 " + FS.num("solve.W1.drone", None) + " · 모드 "
             + FS.num("solve.W1.mode", None))
SOLVE_ARM_PLAIN = (f"기체 {fetch((J_FS, 'solve.W1.drone'))} · "
                   f"모드 {fetch((J_FS, 'solve.W1.mode'))}")     # 제목·표 라벨용(태그 없이)
SOLVE_R90 = "solve 판 R90(" + SOLVE_ARM + ")"

# ── 팔 표시 — S=Sionna PathSolver · B=우리 SBR+PO(광선 격자로 가림을 켠다) ·
#    P=순수 PO 대조군. σ 레벨을 낸 팔의 이름은 σ 격자 원장의 엔진 문자열이 든다. ───────── #
_J_SG_CUR = "outputs/report13_sigma_grid.json"


def arm_b(src: str = _J_SG_CUR) -> str:
    return "우리 SBR+PO 커널(팔 B — " + num(None, (src, "meta.engine")) + ")"


# ── 푸는 게이트와 상반성 창은 서로 다른 각이다 — 게이트 상수는 기하 모듈이 든다. ──────── #
BETA_GATE_DEG = f"{_BETA_MAX:.0f}"
BETA_GATE = (f"β ≤ {BETA_GATE_DEG}° (`src/freespace_scene.py:81` `BETA_VALID_MAX_DEG` 를 "
             f"`beta_gate()` 가 그대로 쓴다 — `:398`)")

# ── 앵커가 통제하지 못한 항 — 개수와 이름을 원장의 status 에서 센다.
#    RESOLVED_EMPIRICALLY 행(규약 불확도)은 해결된 항으로 따로 든다. ──────────────────── #
_UNC_KO = {"polarisation": "편파", "statistic convention (Das mu)": "규약 불확도",
           "size transfer law": "크기전이", "single platform / single lab": "단일 실험실",
           "elevation matching": "앙각 정합", "near-field": "근거리장"}
_UNC = fetch((J_AN, "uncontrolled"))
_UNC_IDX = {u["term"]: i for i, u in enumerate(_UNC)}      # 인덱스는 원장 순서에서 읽는다


def unc(term: str, fmt: str = "{:.2f}") -> str:
    return num(None, (J_AN, f"uncontrolled[{_UNC_IDX[term]}].size_db"), fmt, "dB")


# ── CPI 스윕의 5G/WiFi 배수 — 인용 폭은 스윕의 전 칸에서 센다. ──────────────────────── #
_CPI_ROWS = fetch((J_CG, "equal_cpi_penalty"))
CPI_N_ROWS = len(_CPI_ROWS)
CPI_RATIO_MIN = min(float(r["ratio_G1_over_W1"]) for r in _CPI_ROWS)
CPI_RATIO_MAX = max(float(r["ratio_G1_over_W1"]) for r in _CPI_ROWS)
CPI_T_MIN = min(float(r["T_cpi_s"]) for r in _CPI_ROWS)
CPI_T_MAX = max(float(r["T_cpi_s"]) for r in _CPI_ROWS)
# 칸 수를 말로 쓸 때도 센 값을 쓴다 — 스윕이 칸을 더하면 문장이 같이 따라간다.
CPI_SPAN_KO = f"{CPI_N_ROWS}칸"
CPI_NOTE_MIN, CPI_NOTE_MAX = f"{CPI_SPAN_KO} 최소", f"{CPI_SPAN_KO} 최대"

# ⛔ 그 배수의 «폭» 이 무엇 위에 서 있는지는 원장 자신이 답한다 — 분모 `blind_hard_W1` 은
#    헤딩 격자 psi_n_fine 위의 **칸 수**이고, 다섯 칸에서 38·18·6·2·2 로 내려간다. 뒤 두 칸의
#    분모는 2칸이라 한 칸(=1/psi_n)만 달라져도 배수가 2/3배~2배로 갈린다. 그래서 이 격자가
#    정하는 것은 칸 수이고, 배수의 폭은 격자를 올려 다시 세어야 정해진다. 칸 수는 원장에서 센다.
CPI_PSI_N = int(fetch((J_CG, "meta.psi_n_fine")))
CPI_CELLS_W1 = [int(round(float(r["blind_hard_W1"]) * CPI_PSI_N)) for r in _CPI_ROWS]
CPI_CELLS_G1 = [int(round(float(r["blind_hard_G1"]) * CPI_PSI_N)) for r in _CPI_ROWS]
CPI_CELLS_W1_KO = "·".join(str(n) for n in CPI_CELLS_W1)
CPI_CELLS_G1_KO = "·".join(str(n) for n in CPI_CELLS_G1)
CPI_W1_MIN_CELLS = min(CPI_CELLS_W1)
CPI_CELL_FRAC = 1.0 / CPI_PSI_N
# 마지막 두 칸이 같은 칸 수에 머무는지도 원장이 정한다 — 아니면 그 절은 문장에서 사라진다.
CPI_W1_TIE_KO = (f", WiFi 열은 마지막 두 칸에서 같은 {CPI_CELLS_W1[-1]}칸에 머문다"
                 if len(CPI_CELLS_W1) > 1 and CPI_CELLS_W1[-1] == CPI_CELLS_W1[-2] else "")

# ── 패리티 CPI 는 «칸 수가 같아지는 자리» 로 읽힌 값이다 ───────────────────────────── #
# `parity_cpi()` 는 blind_hard_G1(T) ≤ 목표(기준 CPI 에서의 WiFi 블라인드율) 를 T 격자에서
# 읽고, 그 판정은 `≤` 다 — 두 값이 같은 정수 칸 수면 등호로 통과한다. 원장이 그 자리에 서 있다.
PARITY_T_W = float(fetch((J_CG, "cost_of_long_cpi.required_cpi_s.to_WiFi_parity")))
PARITY_TGT_CELLS = int(round(float(fetch((J_CG, "parity.hard.to_WiFi_parity.target")))
                             * CPI_PSI_N))
_PAR_ROW = [i for i, r in enumerate(_CPI_ROWS)
            if abs(float(r["T_cpi_s"]) - PARITY_T_W) < 1e-9]
PARITY_G1_CELLS = CPI_CELLS_G1[_PAR_ROW[0]] if _PAR_ROW else None
PARITY_EDGE_KO = (
    f"5G 의 눈먼 칸 수({PARITY_G1_CELLS}칸)와 목표인 CPI {CPI_T_MIN:.1f} s 의 WiFi 칸 수"
    f"({PARITY_TGT_CELLS}칸)가 **같은 정수**라 `≤` 판정이 등호로 통과한 자리다"
    f"(5G 쪽이 한 칸 = {CPI_CELL_FRAC:.4f} 만 더 컸으면 이 CPI 는 통과 목록에서 빠진다)"
    if PARITY_G1_CELLS == PARITY_TGT_CELLS else
    f"5G 의 눈먼 칸 수는 {PARITY_G1_CELLS}칸이고 목표는 {PARITY_TGT_CELLS}칸이다")

# 거리·속도 지도에서 패리티를 허용하는 칸 중 «가장 여유가 얇은» 칸 — 여유를 %로 든다.
_CM_OK = [c for c in fetch((J_CG, "cost_of_long_cpi.coherence_map_d_v"))
          if bool(c.get("WiFi_parity_feasible"))]
_CM_TIGHT = min(_CM_OK, key=lambda c: float(c["T_coh_s"]))
CM_TIGHT_KO = (f"{float(_CM_TIGHT['d_m']) / 1000.0:.1f} km · "
               f"{float(_CM_TIGHT['speed_ms']):.0f} m/s")
CM_TIGHT_TCOH = float(_CM_TIGHT["T_coh_s"])
CM_TIGHT_MARGIN_PCT = (CM_TIGHT_TCOH / PARITY_T_W - 1.0) * 100.0

# ── R90 규약 — 원장이 «단일 헤딩 solve» 라 적고, 헤딩 축은 형제 키가 따로 든다. ───────── #
R90_N_CELLS = len(DRONES) * len(MODES)
_R90_EPSI = [float(fetch((J_FS, CELL.format(d=d, m=m) + ".E_psi_Pd_at_R90")))
             for d in DRONES for m in MODES]
R90_EPSI_MIN, R90_EPSI_MAX = min(_R90_EPSI), max(_R90_EPSI)
R90_EPSI_G1_MAX = max(float(fetch((J_FS, CELL.format(d=d, m="G1") + ".E_psi_Pd_at_R90")))
                      for d in DRONES)
R90_T_CPI_S = (float(fetch((J_DV, "r90.doppler.5G.M")))
               / float(fetch((J_DV, "r90.doppler.5G.prf"))))
R90_GUARD_HARD_HZ = float(fetch((J_DV, "r90.doppler.5G.guard_hz"))) * 1.5 / 2.5
# ⛔ 아래 한 줄만 원장 밖이다 — 2026-09-01 재계산:
#      freespace_scene._fd_of_heading(ψ=0, φ=90°, d=각 칸의 R90_C50_m, L=500 m, alt=60 m,
#      v=5 m/s) 의 |f_d| 최대가 3.05e-4 Hz(15칸 전부)이고,
#      blind_fractions(ψ=[0], T=0.1 s) 는 15칸 전부 blind_hard = blind_declared = 1.0 이다.
#    인쇄하는 것은 그 최대보다 **큰** 쪽으로 잡은 상한 한 낱말뿐이라 서식이 값을 깎지 않는다.
R90_FD0_BOUND_KO = "1 mHz"

# ── 취약성 상관 — 세 상관을 다 싣고 인과는 세우지 않는다. ─────────────────────────── #
CORR_N = len(fetch((J_SS, "size_vs_fragility.by_drone")))
# ⛔ p 값과 순위상관은 원장에 없다 — 원장의 size_vs_fragility.by_drone 5행에서 scipy.stats 로
#    직접 낸 값이다(2026-09-01):
#      크기(extent_m) vs 단일자세 문턱 : pearson -0.618 p=0.266 / spearman -0.900 p=0.037
#      σ 로브 산포 vs 단일자세 문턱     : pearson -0.315 p=0.606 / spearman -0.100 p=0.873
#      크기 vs σ 로브 산포              : pearson +0.091 p=0.884 / spearman +0.200 p=0.747
CORR_P = dict(extent_flip=0.27, spread_flip=0.61, extent_spread=0.88)
CORR_RHO = dict(extent_flip=(-0.90, 0.04), spread_flip=(-0.10, 0.87))

# ── 자세평균 판의 뒤집힘 문턱 — 기체별 최댓값은 원장의 by_drone 에서 센다. ──────────── #
ASP_FLIP = {k: float(v["smallest_flip_span_db"])
            for k, v in fetch((J_SS, "aspect_averaged.by_drone")).items()}
ASP_FLIP_MAX = max(ASP_FLIP.values())
ASP_FLIP_MIN_DRONE = min(ASP_FLIP, key=ASP_FLIP.get)
ASP_N = len(ASP_FLIP)
_ASP_REAL = float(fetch((J_SS, "differential.realistic_span_db")))
ASP_N_INSIDE = sum(1 for v in ASP_FLIP.values() if v <= _ASP_REAL)
# 봉투 안/밖 판정도 원장이 한다 — 값이 바뀌면 문장이 «몇/몇» 으로 갈라진다.
ASP_ENVELOPE = (f"{ASP_N}기체가 모두 현실 봉투 안에 든다" if ASP_N_INSIDE == ASP_N
                else f"{ASP_N_INSIDE}/{ASP_N}기체가 현실 봉투 안에 든다")
ASP_NOTE_MAX = f"{ASP_N}기체 smallest_flip_span_db 최대"

_UNC_OPEN = [u for u in _UNC if str(u.get("status", "")) in ("UNRESOLVED", "PARTIAL")]
_UNC_RESOLVED = [u for u in _UNC if str(u.get("status", "")) == "RESOLVED_EMPIRICALLY"]
UNC_N = dnum(len(_UNC_OPEN), "{:.0f}", "개", f"{J_AN} : uncontrolled",
             "status 가 UNRESOLVED·PARTIAL 인 행 세기")
UNC_LIST = " · ".join(f"{_UNC_KO.get(u['term'], u['term'])}({u['status']})" for u in _UNC_OPEN)
UNC_RESOLVED_LIST = " · ".join(f"{_UNC_KO.get(u['term'], u['term'])}({u['status']})"
                               for u in _UNC_RESOLVED)
UNC_RESOLVED_STATUS = " · ".join(str(u["status"]) for u in _UNC_RESOLVED)

# ── H1 정정(조건형) — solve 판이 어느 억압 가정에서 풀렸는지를 원장에서 직접 판정한다.
#    solve.W1.R_m 이 완전 억압(inf) 행과 같으면 그 동작점의 DPI 잔류는 0 이다.
#    limit 라벨(solve.*.limit)은 고정 60 dB 깊이에서 계산된 별도 축이라 인용하지 않는다. ── #
_ECA_IDEAL = abs(float(fetch((J_FS, "solve.W1.R_m")))
                 - float(fetch((J_FS, "solve.W1.sensitivity_eca_depth.inf.R_m")))) < 1e-6
ECA_HEADLINE = (SOLVE_R90 + " 은 완전 억압(ECA ∞) 행과 같은 값이다"
                if _ECA_IDEAL else
                SOLVE_R90 + " 은 유한 ECA 깊이 팔에서 풀렸다")
ECA_HEADLINE_LONG = (
    SOLVE_R90 + " 은 완전 억압(ECA ∞) 행과 같은 값이라, 그 동작점의 직접파 잔차 항은 "
    "0 이다" if _ECA_IDEAL else
    SOLVE_R90 + " 은 유한 ECA 깊이 팔에서 풀렸다 — 벽의 정체는 원장에서 다시 읽는다")


def B(m, k, f="{:+.2f}"):
    return f.format(D["budget"][m][k])


def fig(no: int, path: str, question: str) -> list[str]:
    return [f"![fig{no}]({path})", "", caption(no, question)]


# =========================================================================== #
#  편 56 — 기하
# =========================================================================== #
def r56():
    return [
        header(
            num=56,
            title="TX·RX·표적 배치와 β·앙각·원거리장이 유효창을 연다",
            did="조명원과 패시브 수신기를 지상에 고정하고 표적을 공중에 두는 자유공간 배치를 "
                "좌표로 못 박은 뒤, 그 배치에서 결과가 성립하는 창을 세 축으로 재었다.",
            results=[
                f"베이스라인 {FS.num('solve.W1.L_m', 500.0, '{:.0f}', 'm')} · 표적 고도 "
                f"{FS.num('solve.W1.alt_m', 60.0, '{:.0f}', 'm')} · 장면 방위 "
                f"{FS.num('solve.W1.phi_deg', 90.0, '{:.0f}', '°')} 에서 푼다.",
                f"{SOLVE_R90} 의 바이스태틱 각은 "
                f"{dnum(D['beta_at_R'], '{:.2f}', '°', f'{J_FS} : solve.W1.beta_deg', 'R90 에서 보간')}"
                f" 라 준모노스태틱이고, σ 는 이등분선 방향의 모노스태틱 값을 쓴다.",
                f"푸는 게이트는 {BETA_GATE} 이고, 상반성 rms 잔차가 β ≤ 45° 안에서 "
                + dnum(D["recip_in"], "{:.2f}", "dB", f"{J_DF} : d2_reciprocity_drone.rows",
                       "β≤45 행 최대")
                + ", β 60~90° 에서 "
                + dnum(D["recip_out"], "{:.2f}", "dB", f"{J_DF} : d2_reciprocity_drone.rows",
                       "β>45 행 최대") + " 다.",
                f"장면 방위 {PH.num('meta.n_phi', None, '{:.0f}')}방위 전수 스윕에서 σ 를 고정한 "
                f"순수기하의 R90 span 은 W1 에서 "
                f"{PH.num(f'{PHC}.constant_sigma_control.W1.span_pct_of_phi90', None, '{:.2f}', '%')}"
                f" 이고 세 팔을 다 세면 "
                + dnum(min(_PHI_SPANS.values()), "{:.2f}", "", f"{J_PH} : {PHC}.*.span_pct_of_phi90",
                       "세 팔 최소") + " ~ "
                + dnum(max(_PHI_SPANS.values()), "{:.2f}", "%",
                       f"{J_PH} : {PHC}.*.span_pct_of_phi90", "세 팔 최대")
                + f" 다 — {PHI90_VERDICT}이라 이 배치의 φ 는 보수적인 끝이다.",
                f"σ 격자의 앙각 행은 "
                + dnum(D["n_el"], "{:.0f}", "개", f"{J_SG_USED} : meta.el_deg", "길이")
                + " 이고 최솟값이 "
                + dnum(D["el_grid_min"], "{:.0f}", "°", f"{J_SG_USED} : meta.el_deg", "최솟값")
                + " 다 — 조회의 일부가 경계 행으로 클램프된다.",
            ],
            method=[
                ("좌표",
                 "조명원(TX)과 패시브 수신기(RX)를 지상에 고정하고, 표적을 두 점의 중점에서 "
                 "수평거리 `d` 만큼 떨어진 공중에 둔다 — `src/freespace_scene.py:72`, 기하 함수 `:117`"),
                ("바이스태틱 게이트와 상반성 창",
                 f"푸는 게이트는 {BETA_GATE} 다. 상반성 rms 잔차는 β ≤ 45° 행에서 최대 "
                 + dnum(D["recip_in"], "{:.2f}", "dB", f"{J_DF} : d2_reciprocity_drone.rows",
                        "β≤45 행 최대")
                 + " 이고 β 60~90° 행에서 최대 "
                 + dnum(D["recip_out"], "{:.2f}", "dB", f"{J_DF} : d2_reciprocity_drone.rows",
                        "β>45 행 최대")
                 + " 라, 두 각을 나란히 실어 그 차이의 크기를 숫자로 둔다"),
                ("σ 조회",
                 "이등분선 방향의 모노스태틱 값을 격자에서 조회한다 — "
                 "`src/experiment_freespace_sigma.py:227`"),
                ("발표된 격자의 신원",
                 "이 결과가 실제로 읽은 σ 격자판은 아카이브에 그대로 있고, φ 스윕이 기록한 "
                 "생성시각과 일치하는 것으로 특정한다(빌드마다 확인한다)"),
            ],
            prereq=[(ref("range-convention", short=True), "거리·잡음대역 규약")],
            repro=dict(cmd=CMD[:5] + CMD[-1:], out=[J_FS, J_VF, J_DF, J_PH], runtime=RUNTIME),
        ),

        md("## 배치 — TX · RX · 표적을 어디에 두었나", "",
           "조명원(TX)과 패시브 수신기(RX)를 지상에 고정하고, 표적을 두 점의 중점에서 수평거리 "
           "`d` 만큼 떨어진 공중에 둔다. 좌표 상수 `src/freespace_scene.py:72`, "
           "기하 함수 `src/freespace_scene.py:117`.", "",
           table(["항목", "값", "무엇을 정하나"],
                 [["베이스라인 $L$", FS.num("solve.W1.L_m", 500.0, "{:.0f}", "m"),
                   "β(d) 와 직접파 세기"],
                  ["표적 고도", FS.num("solve.W1.alt_m", 60.0, "{:.0f}", "m"), "이등분선 앙각 el"],
                  ["장면 방위 $\\varphi$", FS.num("solve.W1.phi_deg", 90.0, "{:.0f}", "°"),
                   "R1 · R2 의 비"],
                  ["EIRP · 수신이득 · NF",
                   FS.num("meta.link_budget.eirp_dbm", 63.0, "{:.0f}", "dBm") + " · "
                   + FS.num("meta.link_budget.rx_gain_dbi", 10.0, "{:.0f}", "dBi") + " · "
                   + FS.num("meta.link_budget.noise_figure_db", 5.0, "{:.0f}", "dB"),
                   "선언 예산 — 잡음바닥과 절대 거리 축"],
                  ["CPI", FS.num("solve.W1.T_cpi_s", 0.1, "{:.1f}", "s"), "프레임 수 M = CPI·PRF"],
                  ["기준채널",
                   FS.num("meta.link_budget.power_normalization.canonical_reference", None),
                   "상관에 쓸 수 있는 에너지"]])),

        md("## 유효창 — β 와 앙각이 어디까지 열려 있나", "",
           f"{SOLVE_R90} 에서 β = "
           f"{dnum(D['beta_at_R'], '{:.2f}', '°', f'{J_FS} : solve.W1.beta_deg', 'R90 에서 보간')} "
           "라 준모노스태틱이고, σ 는 이등분선 방향의 모노스태틱 값을 쓴다"
           "(`src/experiment_freespace_sigma.py:227`). 그 거리축은 재현 루프의 마지막 기체가 "
           "남긴 판이고, 편 60 의 헤드라인 폭은 앵커 비교가능 기체 쪽에서 읽는다"
           f"({ref('r90', short=True)}). 아래 표가 게이트와 창을 가른다."),

        md(table(["창", "성립 범위", "크기"],
                 [["바이스태틱 각", f"푸는 게이트 β ≤ {BETA_GATE_DEG}° · 상반성 창 β ≤ 45°",
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
                   + dnum(D["d_el20"], "{:.0f}", "m", f"{J_FS} : solve.W1.el_look_deg",
                          "el=−20° 보간") + ")",
                   "격자 앙각 행 "
                   + dnum(D["n_el"], "{:.0f}", "개", f"{J_SG_USED} : meta.el_deg", "길이")
                   + ", solve 판 R90 의 el = "
                   + num(None, (J_FS, "meta.ranges_el_look_deg"), "{:.2f}", "°")
                   + " (⚠ 이 키는 마지막으로 푼 모드 G1 이 덮어쓴 값이다)"],
                  ["β = 45° 지점 (기하만의 함수)",
                   "`d` = " + dnum(D["d_beta45"], "{:.0f}", "m", f"{J_FS} : solve.W1.beta_deg",
                                   "β=45° 보간"),
                   f"그 지점의 SNR({SOLVE_ARM_PLAIN}) = "
                   + dnum(D["snr_at_beta45"], "{:.0f}", "dB", f"{J_FS} : solve.W1.snr_d_db",
                          "d=β45 에서 보간")],
                  ["장면 방위 φ",
                   PH.num("meta.n_phi", None, "{:.0f}") + "방위 전수 — 5° 간격의 전 원주",
                   "σ 고정 순수기하 R90 span "
                   + PH.num(f"{PHC}.constant_sigma_control.W1.span_pct_of_phi90", None,
                            "{:.2f}", "%")
                   + " · 자세평균 "
                   + PH.num(f"{PHC}.aspect_averaged.W1.span_pct_of_phi90", None, "{:.2f}", "%")]])),

        md("## 앙각 클램프 — 이 창의 열린 끝", "",
           f"같은 스윕이 σ 조회의 앙각도 잰다. 스윕이 읽은 격자(생성 "
           f"{PH.num('meta.sigma_file_generated', None)}, 앙각 0~−20°)에서 조회의 "
           f"{PH.num('geometry.rows[18].frac_el_outside_sigma_grid', None, '{:.1%}')}(φ=90°) ~ "
           f"{PH.num('geometry.rows[0].frac_el_outside_sigma_grid', None, '{:.1%}')}(φ=0°) 가 "
           f"경계 행으로 클램프됐다 — 격자 밖 값을 가장자리 값으로 눌러 붙였다는 뜻이다.", "",
           f"이 두 비율의 분모는 **게이트 이전** `d` 격자 {_N_D}칸 전체다"
           f"(`benchmark/phi_sweep.py:152` 의 `np.mean(el < -20.0)`). 같은 격자에서 β 게이트가 "
           f"남기는 칸은 "
           + dnum(_N_VALID, "{:.0f}", "칸", f"{J_PH} : geometry.rows[18].beta_gate_frac",
                  f"×{_N_D}칸, 72방위가 모두 같은 값")
           + f" 이고, 헤드라인 방위 φ=90° 의 클램프 칸은 `d` ≤ "
           + dnum(_D_CLAMP_MAX, "{:.0f}", "m", f"{J_FS} : solve.W1.el_look_deg",
                  "el<격자최솟값 마지막 칸")
           + f" 로 게이트가 빼는 앞 {_I_GATE}칸 안에 모두 들어간다 — 그 {_N_VALID}칸에 남는 클램프 "
           f"칸은 "
           + dnum(_N_CLAMP_GATED, "{:.0f}", "칸", f"{J_FS} : solve.W1.el_look_deg",
                  "el<격자최솟값 ∧ β게이트 통과")
           + " 이다.", "",
           f"φ=0° 쪽 클램프 {_N_CLAMP_PHI0}칸이 게이트 어느 쪽에 놓이는지는 이 원장이 방위별 "
           f"인덱스 없이 비율만 싣는 자리라, 두 비율의 포함배제로 "
           f"게이트 뒤 하한 "
           + dnum(_N_C0_GATED_MIN, "{:.0f}", "칸", _KEY_C0,
                  f"×{_N_D}칸 + 유효 {_N_VALID}칸 − {_N_D}칸(포함배제)")
           + " 까지가 정해진다 — 그 방위의 정확한 개수는 앙각 격자를 넓혀 다시 푸는 쪽에서 읽는다."),

        md("## 그 «천장» 은 게이트가 열리는 첫 칸의 값이다", "",
           f"{FS.num('solve.W1.snr_ceiling_db', None, '{:.2f}', 'dB')} 은 SNR(`d`) 의 봉우리가 "
           f"아니라 valid 게이트를 적용한 뒤 남은 격자의 argmax 다(`src/freespace_link.py:637`). "
           f"이 배치에서 그 argmax 는 β 게이트가 열리는 첫 칸이다 — {_N_D}칸 중 "
           f"{_I_GATE + 1}번째, `d` = "
           + FS.num("solve.W1.snr_peak_d_m", None, "{:.0f}", "m") + ", β = "
           + dnum(_BETA_D[_I_GATE], "{:.2f}", "°", f"{J_FS} : solve.W1.beta_deg", "게이트 첫 칸")
           + f" 로 게이트({BETA_GATE_DEG}°) 안 · 상반성 창(β ≤ 45°) 밖이다.", "",
           f"그래서 이 값은 게이트 상수 `BETA_VALID_MAX_DEG` 가 서 있는 자리의 함수다 — 상수를 "
           f"옮기면 {_CEIL_BY_GATE} 로 따라 움직인다"
           f"⟨{J_FS} : solve.W1.snr_d_db → β 게이트 상수를 옮겨 첫 칸 재선택⟩. 그 첫 칸의 이웃 "
           "눈금은 "
           + dnum(_D_STEP_PCT, "{:.2f}", "%", f"{J_FS} : solve.W1.d_grid_m",
                  "게이트 첫 칸 이웃 간격")
           + " 다.", "",
           f"그 칸의 앙각은 el = "
           + dnum(_EL_D[_I_GATE], "{:.2f}", "°", f"{J_FS} : solve.W1.el_look_deg", "게이트 첫 칸")
           + " 로 σ 격자(0 ~ "
           + dnum(D["el_grid_min"], "{:.0f}", "°", f"{J_SG_USED} : meta.el_deg", "최솟값")
           + ") 안쪽이고, 클램프 칸은 `d` ≤ "
           + dnum(_D_CLAMP_MAX, "{:.0f}", "m", f"{J_FS} : solve.W1.el_look_deg",
                  "el<격자최솟값 마지막 칸")
           + " 에서 끝나 이 칸(`d` = "
           + FS.num("solve.W1.snr_peak_d_m", None, "{:.0f}", "m")
           + ")과 격자 위에서 떨어져 있다 — 앙각 격자를 넓히는 일이 이 값을 옮기는지는 다시 "
           "풀어야 안다."),

        next_steps([
            ("앙각을 확장한 σ 격자 위에서 R90 과 SNR 천장을 다시 푼다",
             "헤드라인 방위 φ=90° 는 R90 해에 들어오는 클램프 칸이 "
             + dnum(_N_CLAMP_GATED, "{:.0f}", "칸", f"{J_FS} : solve.W1.el_look_deg",
                    "el<격자최솟값 ∧ β게이트 통과")
             + " 이라 값이 그대로 서고, 클램프가 "
             + PH.num("geometry.rows[0].frac_el_outside_sigma_grid", None, "{:.1%}")
             + " 인 φ=0° 쪽에서 게이트 뒤에 남는 칸(포함배제 하한 "
             + dnum(_N_C0_GATED_MIN, "{:.0f}", "칸", _KEY_C0,
                    f"×{_N_D}칸 + 유효 {_N_VALID}칸 − {_N_D}칸(포함배제)")
             + ")의 개수와 그 칸들의 값이 확정된다",
             "`src/experiment_freespace_sigma.py` → `--stage solve`"),
            ("β > 45° 의 출사 가시성·대칭화 잔차를 다시 잰다",
             "바이스태틱 유효창의 폭이 확정된다",
             "`benchmark/verify_sbr_defect_fixes.py` → " + ref("bistatic-exit", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 57 — 감도사슬
# =========================================================================== #
def r57():
    return [
        header(
            num=57,
            title="세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다",
            did="1 km · Mavic 4 Pro · 수신소자 1개에서 출력 SNR 을 항별로 분해하고, 밴드 쌍의 "
                "격차를 그 항들로 쪼개 어느 항이 격차를 만드는지를 세었다.",
            results=[
                f"공통항(EIRP·수신이득·확산·1/N₀·CPI·듀티·손실)은 세 밴드가 같은 값을 쓴다 — "
                f"값이 다른 항은 $\\lambda^2$ 와 σ 둘뿐이다.",
                f"WiFi−LTE 격차 "
                f"{DV.num('gap_1km.by_pair.W1-L1.d_total', None, '{:+.2f}', 'dB')} 는 "
                f"$\\lambda^2$ {DV.num('gap_1km.by_pair.W1-L1.d_lambda2', None, '{:+.2f}', 'dB')} 와 "
                f"σ {DV.num('gap_1km.by_pair.W1-L1.d_sigma', None, '{:+.2f}', 'dB')} 의 합이다.",
                f"5기체 × 3쌍 15칸에서 σ 항이 더 큰 칸이 "
                f"{SS.num('gap_decomposition.n_pairs_sigma_dominates', None, '{:.0f}')}칸이다 — "
                f"그 셈은 `d` = "
                f"{SS.num('gap_decomposition.d_ref_m', None, '{:.0f}', 'm')} · 앵커 전 σ 판이고, "
                f"σ-무관 축의 격차는 $\\lambda^2$ 스프레드로 고정이다.",
                f"유한 ECA 깊이에서는 직접파 잔차가 벽이 된다 — {SOLVE_ARM} 판에서 40 dB 의 R90 이 "
                f"{num(None, (J_FS, 'solve.W1.sensitivity_eca_depth.40.R_m'), '{:.0f}')}, 완전 "
                f"억압이 "
                f"{num(None, (J_FS, 'solve.W1.sensitivity_eca_depth.inf.R_m'), '{:.0f}', 'm')} "
                f"이고, {ECA_HEADLINE}.",
                f"듀티 항은 이 사슬에서 꺼져 있다 — 그 크기는 5G 가 LTE 대비 "
                f"{SS.num('unapplied_duty_axis.pair_gaps_db.L1-G1', None, '{:.2f}', 'dB')} 다.",
            ],
            method=[
                ("동작점",
                 "d = 1 km · Mavic 4 Pro · 수신소자 1개. 점유 규약은 "
                 + FS.num("meta.link_budget.power_normalization.canonical_occupancy", None)
                 + "(자원요소 RE 하나당 같은 전력)"),
                ("σ 항",
                 "기울기 앵커의 밴드별 Δσ 를 더한 값이다 — 레벨은 " + arm_b(J_SG_USED)
                 + " 이 낸 것이고 기울기만 측정에서 받는다"),
                ("σ 우세 칸의 셈",
                 "15칸 판정은 `d` = "
                 + SS.num("gap_decomposition.d_ref_m", None, "{:.0f}", "m")
                 + " 의 **앵커 전** σ(원 sigma_dbsm)로 센다 — 표의 σ 행(1 km · 앵커 적용)과 "
                   "규약이 다르므로 두 수를 각각의 규약과 함께 읽는다"),
                ("항등식 검사",
                 "파형 3종 × 기체 2종 "
                 + dnum(D["lb_rows"], "{:.0f}", "행", f"{J_LB} : A_radar_equation.rows", "길이")
                 + " 에서 코드 경로와 dB 산술의 차이를 "
                 + dnum(D["lb_resid"], "{:.1e}", "dB", f"{J_LB} : A_radar_equation.rows",
                        "|d_echo_dbarith_db| 최대") + " 로 잡는다"),
                ("듀티 축",
                 "이 사슬은 기준신호가 CPI 전체를 채운다는 규약에서 풀린다. 실제 점유가 만드는 "
                 "듀티 항은 크기만 적고 켜지 않는다"),
            ],
            prereq=[(ref("geometry", short=True), "이 값들이 서 있는 배치와 유효창"),
                    (ref("cost-ledger", short=True), "조명원 선택의 dB 원장")],
            repro=dict(cmd=CMD[:5] + CMD[-1:], out=[J_FS, J_LB, J_SS, J_DV], runtime=RUNTIME),
        ),

        md("## 항별 분해", "",
           "d = 1 km · Mavic 4 Pro · 수신소자 1개. **세 밴드에서 값이 다른 항은 $\\lambda^2$ 와 "
           "σ 둘뿐이다** — 나머지는 세 밴드가 같은 값을 쓴다.", "",
           table(["항", "WiFi", "LTE", "5G"],
                 [[nm] + [B(m, k) for m in MODES] for nm, k in
                  [("공통항 합 (EIRP·수신이득·확산·1/N₀·CPI·듀티·손실)", "common"),
                   ("$\\lambda^2$", "lambda2"),
                   ("σ (기울기 앵커, 공칭 헤딩)", "sigma_anch"),
                   ("**출력 SNR**", "total_anch")]]),
           "", SRC_B, SRC_A),

        md("## σ 행이 서 있는 원장 세대", "",
           "$\\lambda^2$ 는 정의로 정해지지만 σ 행은 격자 원장에서 조회한 값이다 — 그 격자의 "
           "세대가 이렇다.", "", MESH_WARN, "", GAMMA_WARN),

        md("## 밴드 쌍의 격차를 그 두 항으로 쪼갠다", "",
           "$\\lambda^2$ 는 정의로 정확하고, σ 는 자세 로브 구조(방위를 돌릴 때 σ 가 솟는 봉우리와 "
           "꺼지는 골)가 만든다.", "",
           table(["쌍", "출력 SNR 차", "$\\lambda^2$ 항", "σ 항"],
                 [[p,
                   DV.num(f"gap_1km.by_pair.{p}.d_total", None, "{:+.2f}", "dB"),
                   DV.num(f"gap_1km.by_pair.{p}.d_lambda2", None, "{:+.2f}", "dB"),
                   DV.num(f"gap_1km.by_pair.{p}.d_sigma", None, "{:+.2f}", "dB")]
                  for p in ("W1-L1", "W1-G1", "L1-G1")]),
           "",
           f"위 표의 σ 행은 `d` = "
           f"{DV.num('gap_1km.d_ref_m', None, '{:.0f}', 'm')} · 앵커 적용 판이다. 15칸을 세는 "
           f"아래 문장은 다른 규약 위에 선다 — `d` = "
           f"{SS.num('gap_decomposition.d_ref_m', None, '{:.0f}', 'm')} · 앵커 전 σ 다.", "",
           f"그 판에서 5기체 × 3쌍 15칸 중 σ 항이 더 큰 칸은 "
           f"{SS.num('gap_decomposition.n_pairs_sigma_dominates', None, '{:.0f}')}칸이고, "
           f"σ-무관 축의 격차는 $\\lambda^2$ 스프레드 "
           f"{SS.num('gap_decomposition.axes_pair_gaps_db.W1-L1', None, '{:+.2f}')} / "
           f"{SS.num('gap_decomposition.axes_pair_gaps_db.W1-G1', None, '{:+.2f}')} / "
           f"{SS.num('gap_decomposition.axes_pair_gaps_db.L1-G1', None, '{:+.2f}', 'dB')} 로 고정이다."),

        md(*fig(1, PF["gap"], "밴드 격차를 만드는 항은 $\\lambda^2$ 와 σ 중 무엇인가?")),

        md(f"## 어느 벽이 거리를 정하나 — solve 판({SOLVE_ARM_PLAIN})", "",
           f"{ECA_HEADLINE_LONG}. 유한 ECA 깊이에서는 직접파 잔차가 벽이 되고, 깊이에 따라 "
           f"거리가 이렇게 움직인다. 이 감도는 solve 축 한 판의 값이고, 편 60 의 헤드라인 폭은 "
           f"앵커 비교가능 기체 쪽에서 읽는다({ref('r90', short=True)}).", "",
           table(["ECA 깊이"] + [f"{k} dB" if k != "inf" else "완전 억압"
                                for k in ("40", "60", "90", "inf")],
                 [[f"R90 ({SOLVE_ARM_PLAIN})"]
                  + [num(None, (J_FS, f"solve.W1.sensitivity_eca_depth.{k}.R_m"),
                         "{:.0f}", "m") for k in ("40", "60", "90", "inf")]]),
           "",
           f"레이더 방정식 항등식 검사는 "
           + dnum(D["lb_rows"], "{:.0f}", "행", f"{J_LB} : A_radar_equation.rows", "길이")
           + " 에서 코드 경로와 dB 산술의 차이를 "
           + dnum(D["lb_resid"], "{:.1e}", "dB", f"{J_LB} : A_radar_equation.rows",
                  "|d_echo_dbarith_db| 최대") + " 로 잡는다."),

        md("## 듀티 축의 크기", "",
           "위 사슬은 기준신호가 CPI 전체를 채운다는 규약에서 풀린다. 실제 점유가 만드는 듀티 항은 "
           "밴드마다 다르고, 그 크기를 여기 적는다.", "",
           table(["모드", "기준신호 길이 T_ref", "프레임 M", "듀티 항"],
                 [[MODE_NAME[m],
                   SS.num(f"unapplied_duty_axis.by_mode.{m}.T_ref_s", None, "{:.2e}", "s"),
                   SS.num(f"unapplied_duty_axis.by_mode.{m}.M", None, "{:.0f}"),
                   SS.num(f"unapplied_duty_axis.by_mode.{m}.duty_db", None, "{:+.2f}", "dB")]
                  for m in MODES]),
           "",
           f"이 항을 넣으면 5G 는 LTE 대비 "
           f"{SS.num('unapplied_duty_axis.pair_gaps_db.L1-G1', None, '{:.2f}', 'dB')} 를 더 치른다. "
           f"WiFi 의 {SS.num('unapplied_duty_axis.duty_db.W1', None, '{:.2f}', 'dB')} 는 "
           f"조명원 원장의 패킷 듀티와 같은 값이다."),

        next_steps([
            ("듀티 항을 R90 경로에 켜고 세 밴드를 다시 푼다",
             "위 표의 " + SS.num("unapplied_duty_axis.duty_db.G1", None, "{:.2f}", "dB")
             + " 가 순위에 주는 영향이 확정된다",
             "`src/freespace_link.py` 의 duty_db_from_cpi → " + ref("r90", short=True)),
            ("ECA 억압 깊이를 실측 채널 값으로 바꿔 solve 판의 벽을 다시 잰다",
             "거리를 구속하는 벽이 직접파 잔차인지 열잡음인지가 실측에서 갈린다",
             ref("eca", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 58 — 공유 문턱
# =========================================================================== #
def r58():
    return [
        header(
            num=58,
            title="자유공간 형상에서 문턱을 다시 재니 세 밴드가 SNR90 하나를 공유한다",
            did="자유공간 형상에서 경험 Pfa 를 목표값에 고정해 문턱을 다시 잡고, 세 밴드가 문턱 "
                "하나를 공유하는 선택이 거리에 얼마를 주는지를 계산했다.",
            results=[
                f"경험 Pfa 를 목표 {FS.num('threshold.pfa.W1.target', 1e-4, '{:.0e}')} 에 고정하고 "
                f"그때 요구되는 명목 Pfa 를 기록한다 — 자유공간 형상은 거리창·오버샘플·가드 규약이 "
                f"챔버와 달라 형상마다 다시 잰다.",
                f"5G 의 요구 명목 Pfa 는 경험값의 "
                + dnum(D["pfa_g1_ratio"], "{:.0f}", "배",
                       f"{J_FS} : threshold.pfa.G1.ratio_emp_over_nominal", "역수")
                + f" 다 — 프레임 {FS.num('waveforms.G1.M', 5, '{:.0f}')}개짜리 도플러 축이 그만큼 좁다.",
                f"세 밴드의 solve 는 W1 에서 잰 문턱 SNR90 = "
                f"{DV.num('threshold.snr90_shared_db', None, '{:.2f}', 'dB')} 하나를 공유한다.",
                f"그 선택의 크기 — 같은 dopoff {_THR_DOP}빈에서 LTE 자기 문턱은 "
                f"{DV.num('threshold.l1_own_snr90_db', None, '{:.2f}', 'dB')} 로 공유 문턱과 "
                f"{DV.num('threshold.l1_delta_db', None, '{:+.3f}', 'dB')} 차이이고, R90 에 주는 차는 "
                f"{DV.num('threshold.l1_range_shift_pct', None, '{:+.2f}', '%')} 다. 그 차를 두 "
                f"Wilson 반폭의 quadrature(제곱합의 제곱근) "
                + dnum(_THR_QUAD, "{:.3f}", "dB", _KEY_QUAD, "두 반폭의 제곱합의 제곱근")
                + " 만큼 흔들면 R90 차는 "
                + dnum(_THR_R90_LO, "{:+.2f}", "", _KEY_QUAD, "차+눈금을 R90 로 환산") + " ~ "
                + dnum(_THR_R90_HI, "{:+.2f}", "%", _KEY_QUAD, "차−눈금을 R90 로 환산")
                + " 로 옮겨 다닌다.",
            ],
            method=[
                ("문턱 잡는 법",
                 "자유공간 형상에서 경험 Pfa 를 목표에 맞춰 문턱을 잡는다 — "
                 "`src/freespace_detect.py:711`"),
                ("왜 형상마다 다시 재나",
                 "거리창·오버샘플·가드 규약이 챔버 형상과 다르다. 챔버 형상의 배율을 그대로 쓰면 "
                 "세 밴드가 서로 다른 실제 오경보율 위에 선다"),
                ("문턱 공유",
                 "W1 에서 잰 SNR90 하나를 세 밴드가 함께 쓴다 — 그 선택의 크기를 LTE 자기 문턱과의 "
                 "차로 같은 표에 싣는다(`src/experiment_freespace_range.py:856`)"),
                ("5G 의 자기 문턱",
                 f"dopoff 격자 {DV.num('threshold.g1_total_cells', None, '{:.0f}')}칸이 "
                 f"M={DV.num('threshold.g1_M', None, '{:.0f}')} 의 도플러 축 밖이라 자기 문턱을 "
                 f"직접 재지 못한다 — 다음 단계에 건다"),
            ],
            prereq=[(ref("cfar-calib", short=True), "경험 Pfa 교정이 왜 필요한가"),
                    (ref("geometry", short=True), "자유공간 배치와 유효창")],
            repro=dict(cmd=CMD[:5] + CMD[-1:], out=[J_FS, J_DV], runtime=RUNTIME),
        ),

        md("## 세 파형을 같은 검출기에 물린다", "",
           "세 조명원은 각 표준이 늘 켜 두는 기준신호다 — WiFi VHT-LTF(W1) · LTE CRS(L1) · "
           "5G SSB(G1). 제원은 " + ref("illuminators", short=True) + " 가 들고, 여기서는 그 셋을 "
           "같은 검출기에 물린다.", "",
           f"경험 Pfa 를 목표 {FS.num('threshold.pfa.W1.target', 1e-4, '{:.0e}')} 에 고정하고, "
           f"그때 요구되는 명목 Pfa 를 기록한다(`src/freespace_detect.py:711`)."),

        md("## 자유공간 형상에서 다시 잰 문턱", "",
           table(["모드", "요구 명목 Pfa", "경험 Pfa", "경험/명목"],
                 [[MODE_NAME[m], num(None, (J_FS, f"threshold.pfa.{m}.nominal"), "{:.2e}"),
                   num(None, (J_FS, f"threshold.pfa.{m}.empirical"), "{:.2e}"),
                   num(None, (J_FS, f"threshold.pfa.{m}.ratio_emp_over_nominal"), "{:.3f}")]
                  for m in MODES]),
           "",
           f"5G 의 요구 명목 Pfa 는 경험값의 "
           + dnum(D["pfa_g1_ratio"], "{:.0f}", "배",
                  f"{J_FS} : threshold.pfa.G1.ratio_emp_over_nominal", "역수")
           + f" 다 — 프레임 {FS.num('waveforms.G1.M', 5, '{:.0f}')}개짜리 도플러 축이 그만큼 좁다.",
           "",
           "이 문턱은 **기준신호가 이상적일 때**의 형상에서 잰 값이다 — 기준채널이 측정된 "
           "신호이면 맵 통계가 달라져 같은 명목값이 같은 경험값을 주지 않는다. 그 축을 단일축으로 "
           "흔들어 손실을 잰 편이 "
           "[리포트 8-2 «기준채널이 현실이면 얼마를 잃는가»](08_2_two_channel.ipynb) 다."),

        md("## 세 밴드가 문턱 하나를 공유한다", "",
           f"세 밴드의 solve 는 W1 에서 잰 문턱 SNR90 = "
           f"{DV.num('threshold.snr90_shared_db', None, '{:.2f}', 'dB')} 하나를 공유한다"
           f"(`src/experiment_freespace_range.py:856`). 그 선택의 크기는 이렇다.", "",
           table(["모드", f"자기 문턱 SNR90 (dopoff {_THR_DOP}빈)", "공유 문턱과의 차",
                  "R90 에 주는 차"],
                 [["WiFi", DV.num("threshold.snr90_shared_db", None, "{:.2f}", "dB"),
                   "기준", "기준"],
                  ["LTE", DV.num("threshold.l1_own_snr90_db", None, "{:.2f}", "dB"),
                   DV.num("threshold.l1_delta_db", None, "{:+.3f}", "dB"),
                   DV.num("threshold.l1_range_shift_pct", None, "{:+.2f}", "%")],
                  ["5G", f"dopoff 격자 {DV.num('threshold.g1_total_cells', None, '{:.0f}')}칸이 "
                         f"M={DV.num('threshold.g1_M', None, '{:.0f}')} 의 도플러 축 밖", "—", "—"]]),
           "",
           f"«차» 두 열은 dopoff {_THR_DOP}빈 한 자리에서 잰 값이다. 두 SNR90 은 K={_THR_K} "
           f"시행의 Pd 곡선을 SNR 격자({_THR_GRID_STEP:.0f} dB 눈금 {len(_THR_GRID)}점)에서 "
           f"보간해 뽑았고(`src/freespace_detect.py:1124`), 원장이 함께 싣는 Wilson 띠가 W1 ["
           + FS.num("threshold.S_G.W1.1.dopoff.3.snr90_lo_db", None, "{:.2f}") + ", "
           + FS.num("threshold.S_G.W1.1.dopoff.3.snr90_hi_db", None, "{:.2f}") + "] · L1 ["
           + FS.num("threshold.S_G.L1.1.dopoff.3.snr90_lo_db", None, "{:.2f}") + ", "
           + FS.num("threshold.S_G.L1.1.dopoff.3.snr90_hi_db", None, "{:.2f}")
           + "] dB 로 서로 겹친다. 두 반폭을 quadrature(제곱합의 제곱근)로 합친 "
           + dnum(_THR_QUAD, "{:.3f}", "dB", _KEY_QUAD, "두 반폭의 제곱합의 제곱근")
           + " 을 차에 얹으면 "
           + dnum(_THR_DELTA - _THR_QUAD, "{:+.3f}", "", _KEY_QUAD, "차 − quadrature 눈금")
           + " ~ "
           + dnum(_THR_DELTA + _THR_QUAD, "{:+.3f}", "dB", _KEY_QUAD, "차 + quadrature 눈금")
           + " 로 0 을 품는 폭이 된다.", "",
           f"dopoff 칸도 자유변수다. 원장이 싣는 {_THR_N_OFF}칸"
           f"({'·'.join(sorted(_THR_OFF['L1'], key=float))}빈) 안에서 LTE 자기 "
           f"문턱은 "
           + dnum(_THR_L1_LO, "{:.2f}", "", _KEY_L1, f"{_THR_N_OFF}칸 최솟값") + " ~ "
           + dnum(_THR_L1_HI, "{:.2f}", "dB", _KEY_L1, f"{_THR_N_OFF}칸 최댓값")
           + " 로 흔들리고, 8빈 칸에서는 "
           + dnum(_THR_OFF["L1"]["8"]["snr90_db"], "{:.2f}", "dB", _KEY_L1, "dopoff 8빈")
           + " 로 공유 문턱 아래에 서 부호가 뒤집힌다 — 이 표의 «차» 두 열이 갖는 부호는 dopoff "
           "칸이 정한다."),

        md(*fig(1, PF["detector"],
                "교정된 오경보율 위에서 세 파형이 요구하는 SNR 은 몇 dB 인가?")),

        next_steps([
            ("5G 의 dopoff 격자를 M 인식으로 고쳐 Pd=0.9 문턱을 직접 잰다",
             "5G 의 R90 이 자기 문턱 위에 서고, 위 표의 마지막 줄이 닫힌다",
             "`src/experiment_freespace_range.py:856`"),
            ("자유공간 형상의 명목–경험 곡선을 챔버 형상과 나란히 싣는다",
             "형상이 배율에 주는 크기가 두 형상 사이에서 확정된다",
             ref("cfar-why", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 59 — 기울기 앵커
# =========================================================================== #
def r59():
    return [
        header(
            num=59,
            title="레벨을 맞추려면 크기전이 법칙을 골라야 하므로 기울기만 받는다",
            did="σ = A(f)·B₁(φ,θ) 에서 A(f) 의 **기울기만** 측정에 맞추고, 레벨을 함께 맞추려면 "
                "무엇을 더 골라야 하는지와 그 대가의 크기를 원장에 적었다.",
            results=[
                f"재보정은 밴드별 스칼라 Δσ 하나씩이고, 정규화 각도 패턴은 "
                f"{AN.num('drones.phantom4.shape_invariance_max_abs_db', None, '{:.1e}', 'dB')} "
                f"안에서 그대로 남는다.",
                f"생산 모드 `slope_only` 의 세 밴드 평균 레벨이동은 "
                f"{DV.num('anchor_scope.level_shift_abs_max_db', None, '{:.2f}', 'dB')} 다 — "
                f"절대 레벨은 {arm_b()} 이 낸 값이다.",
                f"레벨까지 맞추려면 크기전이 법칙을 골라야 하고 L² 와 L⁴ 가 최대 "
                f"{DV.num('anchor_scope.size_law_spread_max_db', None, '{:.2f}', 'dB')} 갈린다 — "
                f"측정이 그 대가 없이 제약하는 것은 기울기뿐이다.",
                f"앵커가 통제한 것 밖의 항은 {UNC_N} 다 — {UNC_LIST}. 규약 불확도 "
                f"{unc('statistic convention (Das mu)')} 는 원장에서 {UNC_RESOLVED_STATUS} 이고, "
                f"채택 변환과 탈락 변환의 차로 앵커에 딸린다.",
                f"PO 오차가 1 dB 아래로 내려가려면 부품 폭이 파장의 "
                f"{num(None, (J_LFN, 'thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam'), '{:.3f}')}"
                f"배 이상이어야 하는데, 우리 세 밴드는 전부 그 문턱 아래에 부품을 남긴다.",
            ],
            method=[
                ("무엇을 받나",
                 "σ = A(f)·B₁(φ,θ) 에서 **A(f) 의 기울기**를 Das 측정(IEEE WCL 2026 15:3731)에 "
                 "맞춘다. 절대 레벨과 각패턴은 " + arm_b() + " 의 출력이다"),
                ("통제 밖 항을 세는 법",
                 f"원장 `uncontrolled` 의 status 로 센다 — UNRESOLVED·PARTIAL 인 {UNC_N} 를 "
                 f"통제 밖으로 두고, RESOLVED_EMPIRICALLY 행은 잔차 크기로 따로 든다"),
                ("재보정의 형태",
                 "밴드별 스칼라(방향 구분 없이 값 하나) Δσ 하나씩이다 — 그래서 정규화 각도 패턴이 "
                 "그대로 남는다"),
                ("왜 레벨을 안 받나",
                 "레벨을 맞추려면 측정 표적과 우리 표적 사이의 크기전이 법칙을 골라야 하고, "
                 "L² 와 L⁴ 가 갈리는 폭이 그 선택의 대가다"),
                ("PO 유효성 항의 부호",
                 "우리 적분이 편파를 가르지 않아 부호를 아직 정하지 못한다 — 참값은 두 편파에서 "
                 "다른 값을 주는데 커널은 그 둘을 하나로 낸다"),
            ],
            prereq=[(ref("anchor-mode", short=True), "σ 분해와 앵커가 받는 축"),
                    (ref("sensitivity-chain", short=True), "σ 항이 밴드 격차에서 차지하는 몫")],
            repro=dict(cmd=CMD[:1] + CMD[-2:], out=[J_AN, J_LFA, J_DV], runtime=RUNTIME),
        ),

        md("## 밴드 비교의 바닥 — 기울기 앵커 σ", "",
           "σ = A(f)·B₁(φ,θ) 에서 **A(f) 의 기울기**를 Das 측정(IEEE WCL 2026 15:3731)에 맞춘다. "
           "**절대 레벨은 " + arm_b() + " 이 낸 값**이고, 생산 모드 `slope_only` 의 세 밴드 평균 "
           "레벨이동은 "
           + DV.num("anchor_scope.level_shift_abs_max_db", None, "{:.2f}", "dB") + " 다.", "",
           "레벨까지 맞추려면 크기전이 법칙을 골라야 하고 L² 와 L⁴ 가 최대 "
           + DV.num("anchor_scope.size_law_spread_max_db", None, "{:.2f}", "dB")
           + " 갈리므로, 측정이 그 대가 없이 제약하는 기울기만 받는다."),

        md("## 재보정은 밴드별 스칼라 하나씩이다", "",
           f"그래서 정규화 각도 패턴은 "
           f"{AN.num('drones.phantom4.shape_invariance_max_abs_db', None, '{:.1e}', 'dB')} "
           f"안에서 그대로 남는다 — 앵커가 옮기는 것은 레벨이지 모양이 아니다.", "",
           f"앵커가 통제한 것 밖의 항은 **{UNC_N}** 다 — {UNC_LIST}. 개수는 원장 "
           f"`uncontrolled`⟨{J_AN} : uncontrolled⟩ 의 status 로 센다.", "",
           f"규약 불확도 "
           f"{unc('statistic convention (Das mu)')} 는 같은 원장에서 {UNC_RESOLVED_STATUS} "
           f"이고, 채택 변환과 탈락 변환의 차로 앵커에 딸려 다닌다. "
           f"앙각 정합 항의 크기는 "
           f"{unc('elevation matching')}, 크기전이 항은 "
           f"{unc('size transfer law')} 다."),

        md("## PO 유효성 항이 이번에 크기를 얻었다", "",
           f"PO 오차가 1 dB 아래로 내려가려면 부품의 폭이 파장의 "
           f"{num(None, (J_LFN, 'thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam'), '{:.3f}')}"
           f"배 이상이어야 하는데, 우리 세 밴드는 전부 그 문턱 아래에 부품을 남긴다.", "",
           f"그 항의 **부호는 아직 정하지 못한다** — 우리 적분이 편파(전파의 전기장이 흔들리는 "
           f"방향)를 가르지 않기 때문이다"
           f"(⟨{J_LFA} : q5_blast_radius.po_validity_blast_radius_the_real_one⟩). "
           f"참값은 두 편파에서 서로 다른 값을 주는데 우리 커널은 그 둘을 구분 없이 하나로 내므로, "
           f"한쪽 편파를 기준으로 보면 낮고 다른 쪽을 기준으로 보면 높다.", "",
           "이 사실은 원장에 「VV 측정 대 무편파 커널」 로 기록되어 있다. 이 부는 그 개연성을 "
           "결과에 넣지 않고 순위만 든다."),

        md("## 기체별 Δσ 와 앵커 비교가능성", "",
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
                      order=list(DRONES))),

        md(*fig(1, PF["anchor"], "앵커가 옮긴 밴드 격차는 앵커 자신의 미통제 항보다 큰가?")),

        md("## 이 사슬이 서 있는 원장 세대", "",
           MESH_WARN, "", GAMMA_WARN, "",
           f"이 절의 앵커 수(정규화 잔차 · Δσ 표)와 뒤 편들의 R90 표가 같은 사슬 위에 있다 — "
           f"{ref('r90', short=True)} · {ref('rank-durability', short=True)}."),

        next_steps([
            ("기준 구를 함께 재서 자체 앵커를 세운다",
             "지금 팔 B(우리 SBR+PO 커널)가 낸 σ 절대 레벨이 측정에 앵커되고, 크기전이 항 "
             + DV.num("anchor_scope.size_law_spread_max_db", None, "{:.2f}", "dB") + " 가 닫힌다",
             ref("calibration-sphere", short=True)),
            ("VV/HH 2편파를 잰다", "앵커의 편파 항 크기가 수치로 확정된다",
             ref("sigma-checklist", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 60 — R90
# =========================================================================== #
def r60():
    return [
        header(
            num=60,
            title=f"앵커 σ 위의 R90 은 비교가능 {D['n_cells_comp']}칸에서 "
                  f"{D['A_min']:.2f}~{D['A_max']:.2f} km 이고, 밴드 순서는 기체마다 바뀐다",
            did="기울기 앵커의 Δσ 를 R90 근방 국소 지수로 옮겨 다섯 기체 × 세 밴드의 검출거리를 "
                "내고, 그 표에서 밴드 순서가 기체마다 어떻게 바뀌는지를 읽었다.",
            results=[
                f"Δσ 를 R90 근방 국소 지수 "
                + dnum(D["n_local"], "{:.2f}", "",
                       f"{J_FS} : " + CELL.format(d="*", m="*") + ".n_local_at_R90", "15칸 평균")
                + " 로 옮긴다 — `d` 축에서 국소적으로 $R \\propto \\sigma^{1/n}$ 이다.",
                f"앵커 비교가능 기체 {D['n_cells_comp']}칸의 R90 은 "
                + DV.num("r90.span_comparable_min_km", None, "{:.2f}")
                + " ~ "
                + DV.num("r90.span_comparable_max_km", None, "{:.2f}", "km")
                + f" 다 — 원키 `R90_C50_m`⟨{KEY_R}⟩ 에 앵커 Δσ⟨{KEY_A}⟩ 를 R90 근방 국소 지수로 "
                + f"옮긴 값이고, **공칭 헤딩 ψ=0 한 점**에서 푼 거리다⟨{J_DV} : r90.definition⟩.",
                "밴드 순서는 기체마다 바뀐다 — 그 순서를 만드는 것은 자세별 로브 구조이고, 앵커는 "
                "밴드별 스칼라를 옮기면서 밴드 평균 레벨은 그대로 둔다.",
                f"자세를 평균하면 다섯 기체가 한 순위 "
                f"({DV.num('ranking.consensus_order_aspect_avg', None)}) 로 모인다 — 단일 자세에서는 "
                f"{SS.num('ranking_consensus.single_aspect_n_distinct', None, '{:.0f}')}가지 순위가 나온다.",
                f"아래 km 열은 **순위를 읽는 표**로 쓴다 — 공통모드 σ 오차 ±10 dB 가 이 열 전체를 "
                f"{SS.num('common_mode.abs_range_shift_at_10db_pct.minus10', None, '{:+.1f}', '%')} ~ "
                f"{SS.num('common_mode.abs_range_shift_at_10db_pct.plus10', None, '{:+.1f}', '%')} "
                f"옮긴다. ⚠ 같은 리프의 형제 키 `E_psi_Pd_at_R90` 는 그 거리에서의 헤딩 평균 "
                f"검출확률을 {R90_N_CELLS}칸에서 {R90_EPSI_MIN:.2f} ~ {R90_EPSI_MAX:.2f}(5G 다섯 칸은 "
                f"전부 {R90_EPSI_G1_MAX:.1f}) 로 적으므로, 이 km 열은 **한 헤딩의 도달거리**로 읽는다.",
            ],
            method=[
                # ⛔ 옛 정의는 «P_d 가 0.9 로 떨어지는 거리» 였지만, 이 해가 통과시키는 유효 게이트는
                #    β 와 원거리장 둘이고 헤딩 축은 형제 키가 따로 든다 — 원장이 그렇게 적는다.
                ("R90 정의",
                 "**공칭 헤딩 ψ=0 한 점**의 σ 로 만든 SNR(d) 가 교정 문턱과 **최외곽 하강교차**하는 "
                 "수평거리 `d` 다 — 거리축은 송·수신 기선의 중점에서 표적까지의 수평거리이고, 해를 "
                 f"찾는 칸을 고르는 유효 게이트는 β ≤ {BETA_GATE_DEG}° 와 원거리장 둘이다"
                 f"⟨{J_DV} : r90.definition⟩. 헤딩 축은 같은 리프의 형제 키 `coverage_ceiling` · "
                 "`E_psi_Pd_at_R90` 가 따로 든다"),
                ("앵커 전이",
                 "Δσ 를 R90 근방 국소 지수로 1차 전이한다 — `src/freespace_scene.py:56`"),
                ("순위를 읽는 표",
                 "km 열의 절대값은 공통모드 σ 봉투와 함께 읽는다. 이 부가 헤드라인으로 드는 것은 "
                 "순위다"),
                ("자세 인용 방식",
                 "단일 자세 · 자세평균 · 자세평균+앵커 · 듀티까지 켠 설정 네 가지를 나란히 싣는다"),
            ],
            prereq=[(ref("slope-anchor", short=True), "기울기 앵커가 무엇을 받고 무엇을 남기는가"),
                    (ref("shared-threshold", short=True), "세 밴드가 공유하는 문턱")],
            repro=dict(cmd=CMD[:5] + CMD[-2:], out=[J_FS, J_AN, J_SS, J_DV], runtime=RUNTIME),
        ),

        md("## R90 이 무엇인가", "",
           # ⛔ 규약(공칭 헤딩 한 점 · 게이트 둘)을 정의 자리에 그대로 적는다 — 원장이 그렇게 적는다.
           "**공칭 헤딩 ψ=0 한 점**의 σ 로 만든 SNR(d) 가 교정 문턱을 마지막으로 아래로 뚫는 "
           "수평거리다. 거리축은 송신국과 수신국을 잇는 기선의 중점에서 표적까지의 수평거리이고, "
           f"해를 찾는 칸을 고르는 유효 게이트는 β ≤ {BETA_GATE_DEG}° 와 원거리장 둘이다"
           f"⟨{J_DV} : r90.definition⟩.", "",
           f"⛔ 키 이름의 `C50` 은 스펙 §2.3 의 커버리지 백분위(P_ψ[Pd≥0.9] ≥ 0.50)를 가리키지만, 이 "
           f"실행이 그 자리에 적은 값은 단일 헤딩 solve 의 거리다 — 원장의 `key_note` 가 그렇게 적고 "
           f"있다⟨{J_DV} : r90.key_note⟩. 헤딩 축은 형제 키가 따로 든다: `E_psi_Pd_at_R90` 는 "
           f"{R90_N_CELLS}칸에서 {R90_EPSI_MIN:.2f} ~ {R90_EPSI_MAX:.2f} 이고, 5G 다섯 칸은 전부 "
           f"{R90_EPSI_G1_MAX:.1f} 다.", "",
           f"⚠ 그 ψ=0 은 이 권의 헤드라인 방위 φ=90° 에서 도플러가 0 인 헤딩이다 — 2026-09-01 "
           f"재계산으로 |f_d(ψ=0)| 는 {R90_N_CELLS}칸 전부 {R90_FD0_BOUND_KO} 아래이고, CPI "
           f"{R90_T_CPI_S:.1f} s 의 가드 반폭은 선언 2.5빈 "
           + DV.num("r90.doppler.5G.guard_hz", None, "{:.0f}", "Hz")
           + f" · 검출기 적용 1.5빈 {R90_GUARD_HARD_HZ:.0f} Hz 다. 이 표는 그 가드를 끄고 푼 거리이고, "
           f"가드를 켜고 세는 몫은 위의 형제 키 쪽에 있다.", "",
           "표의 오른쪽 끝 «앵커 비교가능성» 은 그 기체의 σ 를 앵커 기체(Phantom 3)에서 "
           "얼마나 곧장 옮길 수 있나를 세 낱말로 적은 것이다.", "",
           table(["값", "무슨 뜻인가"],
                 [["`direct`", "앵커 기체와 크기·로터 수가 같은 급이라 그대로 비교한다"],
                  ["`scaled`", "크기법칙으로 전이한 뒤 비교한다"],
                  ["`not_comparable`",
                   "크기보정 자체가 결론을 지배해 헤드라인 폭에서 뺀다"]])),

        md("## 앵커 σ 위의 R90", "",
           f"Δσ 를 R90 근방 국소 지수 "
           + dnum(D["n_local"], "{:.2f}", "",
                  f"{J_FS} : " + CELL.format(d="*", m="*") + ".n_local_at_R90", "15칸 평균")
           + " 로 옮긴다 — `d` 축에서 국소적으로 $R \\propto \\sigma^{1/n}$ 이다"
             "(`src/freespace_scene.py:56`).", "",
           "아래 표의 R90 은 전부 공칭 헤딩 ψ=0 의 수이고, **σ 민감도 봉투와 함께 읽는다** — "
           + ref("rank-durability") + " 가 그 봉투를 든다."),

        md(table(["기체"] + [MODE_NAME[m] for m in MODES] + ["앵커 비교가능성"],
                 [[dr] + [f"{D['R90_anch'][(dr, m)]:.2f} km" for m in MODES]
                  + [fetch((J_AN, f"drones.{dr}.comparability.verdict"))] for dr in DRONES]),
           "",
           f"헤드라인이 드는 {D['n_cells_comp']}칸은 비교가능 기체 "
           f"{len(D['comparable'])}대 × 세 밴드다 — `{D['X_name']}` 의 세 칸은 "
           f"`not_comparable` 이라 폭에서 뺐고, 표에는 그대로 싣는다.", "",
           # ⛔ 형제 키가 이 표의 km 열이 무엇을 재는 거리인지를 정한다 — 같은 자리에 나란히 싣는다.
           f"⛔ 위 {R90_N_CELLS}칸은 전부 **공칭 헤딩 ψ=0 한 점**에서 푼 거리다. 헤딩 축을 함께 세는 "
           f"형제 키는 밴드별 `blind_heading_frac` (WiFi "
           + DV.num("r90.blind_heading_frac_by_mode.WiFi", None, "{:.3f}") + " · LTE "
           + DV.num("r90.blind_heading_frac_by_mode.LTE", None, "{:.2f}") + " · 5G "
           + DV.num("r90.blind_heading_frac_by_mode.5G", None, "{:.1f}")
           + ") 와 5G 의 `coverage_ceiling` "
           + DV.num("r90.coverage_ceiling_by_mode.5G", None, "{:.1f}")
           + f", 그리고 칸별 `E_psi_Pd_at_R90` ({R90_EPSI_MIN:.2f} ~ {R90_EPSI_MAX:.2f}) 다 — 이 km "
           + "열은 그 한 헤딩의 도달거리로 읽고, 헤딩 축을 CPI 로 되찾는 몫은 "
           + ref("cpi-sweep", short=True) + " 가 든다.", "",
           SRC_R + " · " + SRC_A),

        md("## 이 표가 서 있는 두 규약", "",
           f"전력 규약은 "
           f"`{FS.num('meta.link_budget.power_normalization.canonical_occupancy', None)}` 다 — "
           f"자원요소(RE) 하나당 같은 전력으로 세 파형을 묶는다.", "",
           f"기준채널 규약은 "
           f"`{FS.num('meta.link_budget.power_normalization.canonical_reference', None)}` 다 — "
           f"기준안테나가 조명원의 **파형 전체**를 받아 상관에 쓴다는 뜻이고, 잡음도 다중경로도 "
           f"0 인 상한이다. 그 가정 하나만 풀어 잃는 양을 재는 편이 "
           f"[리포트 8-2 «기준채널이 현실이면 얼마를 잃는가»](08_2_two_channel.ipynb) 이고, "
           f"거기서 잰 손실은 X410 벤치 기하의 값이므로 위 km 열로 옮기려면 같은 기하에서 다시 "
           f"풀어야 한다."),

        md("## 왜 km 열을 순위로 읽는가", "",
           f"공통모드 σ 오차 ±10 dB 가 이 열 전체를 "
           f"{SS.num('common_mode.abs_range_shift_at_10db_pct.minus10', None, '{:+.1f}', '%')} ~ "
           f"{SS.num('common_mode.abs_range_shift_at_10db_pct.plus10', None, '{:+.1f}', '%')} 옮긴다.", "",
           f"그 봉투가 어디서 오는지도 함께 적는다 — 우리 세 밴드는 전부 PO 근사가 1 dB 안에 든다고 "
           f"보장되는 부품 폭 문턱 아래에 부품을 남긴다({ref('slope-anchor', short=True)}). "
           f"σ 절대 레벨의 불확도는 선언된 ±10 dB 봉투와 별개로 크기가 아직 정해지지 않은 항을 "
           f"하나 더 갖는다(⟨{J_LFA} : q5_blast_radius.po_validity_blast_radius_the_real_one⟩)."),

        md("## 밴드 순서는 자세 인용 방식이 정한다", "",
           "밴드 순서는 기체마다 바뀐다. 그 순서를 만드는 것은 자세별 로브 구조이고, 앵커는 "
           "밴드별 스칼라를 옮기면서 밴드 평균 레벨은 그대로 둔다. 자세를 평균하면 다섯 기체가 "
           "한 순위로 모인다."),

        md(table(["인용 방식", "서로 다른 순위 수", "합의 순위", "최악 뒤집힘 문턱"],
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
                          None, "{:.2f}", "dB")]])),

        md(*fig(1, PF["ranking"], "세 파형의 순위는 자세 인용 방식에 따라 어떻게 달라지는가?")),

        md("## 이 표가 서 있는 원장 세대", "", MESH_WARN, "", GAMMA_WARN),

        next_steps([
            ("자세평균 σ 격자로 `--stage solve` 를 다시 돌린다",
             "합의 순위가 국소 지수 1차 전이 없이 정본 경로에서 확정된다",
             "`src/experiment_freespace_range.py`"),
            ("헤딩 격자 전체에서 R90(ψ) 를 풀어 P_ψ[Pd≥0.9]=0.50 지점을 낸다",
             "`R90_C50` 키가 이름 그대로의 커버리지 백분위 값을 담는다",
             "`src/experiment_freespace_range.py:703`"),
            ("σ 전격자를 현재 메쉬·Γ(θ) 켠 커널로 재생성해 `--stage solve` 를 다시 돌린다",
             "절대 R90 · 백분위 · 기체간 순위가 현재 기하 위에 선다 — 동일설정 재생성 대조에서 "
             "기체당 최대 "
             + SV.num("overstated[0].결과_표[0].max_abs_delta_db", None, "{:.2f}", "dB")
             + " · rms " + SV.num("overstated[0].결과_표[0].rms_delta_db", None, "{:.2f}", "dB")
             + " 다",
             "`src/experiment_freespace_sigma.py`"),
        ]),
    ]


# =========================================================================== #
#  편 61 — 순위 강건성
# =========================================================================== #
def r61():
    return [
        header(
            num=61,
            title="그 순위는 자세평균이면 하나로 모이고, 자세평균 뒤집힘 문턱은 현실 봉투 안이다",
            did="σ 오차를 공통모드와 차분 두 종류로 나눠 넣고, 각각에서 밴드 순위가 어디까지 "
                "버티는지를 단일 자세·자세평균 두 인용 방식의 뒤집힘 문턱과 몬테카를로 "
                "보존확률로 재었다.",
            results=[
                f"σ 는 SNR 에 선형이라 σ 오프셋 Δ dB 가 곧 SNR 오프셋 Δ dB 다 — 선형성 잔차 "
                f"{SS.num('_meta.sigma_linearity_check', None, '{:.1e}')}.",
                f"공통모드 ±10 dB 에서 15칸 전부 순위가 유지되고, 절대거리만 "
                f"{SS.num('common_mode.abs_range_shift_at_10db_pct.minus10', None, '{:+.1f}', '%')} ~ "
                f"{SS.num('common_mode.abs_range_shift_at_10db_pct.plus10', None, '{:+.1f}', '%')} "
                f"움직인다.",
                f"뒤집는 것은 차분 오차다 — 단일 자세 뒤집힘 문턱은 "
                f"{SS.num('differential.smallest_flip_span_db_overall', None, '{:.2f}')} ~ "
                f"{SS.num('differential.largest_flip_span_db_overall', None, '{:.2f}', 'dB')}, "
                f"자세평균 문턱은 "
                f"{SS.num('aspect_averaged.smallest_flip_span_db_overall', None, '{:.2f}')} ~ "
                + dnum(ASP_FLIP_MAX, "{:.2f}", "dB", f"{J_SS} : aspect_averaged.by_drone",
                       ASP_NOTE_MAX)
                + f" 이고, 현실 봉투는 "
                f"{SS.num('differential.realistic_span_db', None, '{:.2f}', 'dB')} 다.",
                # ⛔ n=5 에서 «산포가 정한다» 는 세울 수 없다 — 기각하는 쪽(크기)의 상관이 채택하는
                #    쪽(산포)보다 오히려 강하다. 세 상관을 다 싣고 인과는 세우지 않는다.
                f"작은 기체가 더 취약하다는 예상은 뒤집힌다 — 가장 작은 "
                f"{SS.num('size_vs_fragility.smallest_airframe', None)} 가 단일자세·자세평균 양쪽에서 "
                f"가장 견고하다. 단일자세 뒤집힘 문턱과의 상관은 크기 쪽 "
                f"{SS.num('size_vs_fragility.corr_extent_vs_flip_single', None, '{:+.2f}')}, 밴드 간 σ "
                f"로브 산포 쪽 "
                f"{SS.num('size_vs_fragility.corr_sigma_spread_vs_flip_single', None, '{:+.2f}')}, 두 "
                f"열 사이는 "
                f"{SS.num('size_vs_fragility.corr_extent_vs_sigma_spread', None, '{:+.2f}')} 이고, 기체 "
                f"{CORR_N} 대의 상관계수라 어느 열이 취약성을 정하는지는 이 표본으로 정할 수 없다.",
                f"σ 격자를 블레이드 형상 갱신본으로 바꾸는 것만으로 R90 이 최대 "
                + dnum(D["stale_max_pct"], "{:.1f}", "%",
                       f"{J_SS} : staleness_and_mesh_update.by_drone",
                       "5기체 max_range_change_pct 최대")
                + f" 움직이고 순위쌍 "
                f"{SS.num('staleness_and_mesh_update.n_orders_changed', None, '{:.0f}')}개가 뒤집힌다.",
            ],
            method=[
                ("두 종류의 오차",
                 "**공통모드**는 세 밴드를 함께 옮기고, **차분**은 밴드마다 다르게 옮긴다. "
                 "순위를 뒤집을 수 있는 것은 차분뿐이다"),
                ("선형성",
                 "σ 는 SNR 에 선형이라 dB 오프셋이 그대로 옮겨간다 — 그 사실을 잔차로 확인하고 쓴다"),
                ("몬테카를로",
                 "밴드별 독립 오차 2 dB 를 넣고 순위 보존 확률을 기체마다 잰다"),
                ("관측된 파급",
                 "메쉬 갱신 하나가 옮긴 R90 과 바뀐 순위쌍 수를 함께 적는다 — 통제되지 않은 σ 변화의 "
                 "크기를 관측값으로 두기 위해서다"),
            ],
            prereq=[(ref("r90", short=True), "앵커 σ 위의 R90 표와 밴드 순서")],
            repro=dict(cmd=CMD[:1] + CMD[6:7] + CMD[-1:], out=[J_SS], runtime=RUNTIME),
        ),

        md("## 오차를 두 종류로 나눈다", "",
           "**공통모드**는 세 밴드를 함께 옮기고, **차분**은 밴드마다 다르게 옮긴다. σ 는 SNR 에 "
           "선형이라 σ 오프셋 Δ dB 가 곧 SNR 오프셋 Δ dB 다"
           f"(선형성 잔차 {SS.num('_meta.sigma_linearity_check', None, '{:.1e}')})."),

        md(table(["오차 종류", "무엇이 움직이나", "크기"],
                 [["공통모드 ±10 dB", "순위 유지 · 절대거리만 이동",
                   "15칸 전부 순위 불변 · 거리 "
                   + SS.num("common_mode.abs_range_shift_at_10db_pct.minus10", None, "{:+.1f}", "%")
                   + " ~ "
                   + SS.num("common_mode.abs_range_shift_at_10db_pct.plus10", None, "{:+.1f}", "%")],
                  ["차분(밴드별) — 단일 자세 ψ=0", "순위가 뒤집힐 수 있는 축",
                   "뒤집힘 문턱 "
                   + SS.num("differential.smallest_flip_span_db_overall", None, "{:.2f}")
                   + " ~ "
                   + SS.num("differential.largest_flip_span_db_overall", None, "{:.2f}", "dB")
                   + " (현실 봉투 "
                   + SS.num("differential.realistic_span_db", None, "{:.2f}", "dB") + ") · 봉투 안에서 "
                   + SS.num("differential.n_drones_flipping_inside_realistic", None, "{:.0f}")
                   + "/" + SS.num("differential.n_drones", None, "{:.0f}") + "기체가 뒤집힌다"],
                  ["차분(밴드별) — 자세평균 σ", "합의 순위가 뒤집히는 축",
                   "뒤집힘 문턱 "
                   + SS.num("aspect_averaged.smallest_flip_span_db_overall", None, "{:.2f}")
                   + " ~ "
                   + dnum(ASP_FLIP_MAX, "{:.2f}", "dB", f"{J_SS} : aspect_averaged.by_drone",
                          ASP_NOTE_MAX)
                   + f" — {ASP_ENVELOPE}"],
                  ["밴드별 독립 오차 2 dB (몬테카를로)", "순위 보존 확률",
                   dnum(D["mc_p2db_min"], "{:.2f}", "", f"{J_SS} : monte_carlo_per_band_error",
                        "5기체 최소") + " ~ "
                   + dnum(D["mc_p2db_max"], "{:.2f}", "", f"{J_SS} : monte_carlo_per_band_error",
                          "5기체 최대")]])),

        # ⛔ 옛 제목 «취약성을 정하는 것은 크기가 아니다» 는 바로 아래 인용한 상관 자신이 부정한다.
        #    제목을 관측으로 내리고, 세 상관을 나란히 싣고, 원인은 표본을 늘린 뒤로 미룬다.
        md("## 작은 기체가 더 취약하다는 예상은 뒤집힌다", "",
           f"가장 작은 {SS.num('size_vs_fragility.smallest_airframe', None)}(전장 "
           f"{SS.num('size_vs_fragility.by_drone.mini5pro.extent_m', None, '{:.3f}', 'm')}, LTE 에서 "
           f"D/λ = {SS.num('size_vs_fragility.by_drone.mini5pro.D_over_lambda_lte', None, '{:.2f}')})"
           f" 가 단일자세·자세평균 양쪽에서 가장 견고하다.", "",
           f"단일자세 뒤집힘 문턱은 최대 치수 열과 밴드 간 σ 로브 산포 열 둘 다에 걸린다 — 상관은 "
           f"크기 쪽 {SS.num('size_vs_fragility.corr_extent_vs_flip_single', None, '{:+.2f}')}, 산포 쪽 "
           f"{SS.num('size_vs_fragility.corr_sigma_spread_vs_flip_single', None, '{:+.2f}')} 로 크기 "
           f"쪽이 더 강하고, 두 열 사이 상관은 "
           f"{SS.num('size_vs_fragility.corr_extent_vs_sigma_spread', None, '{:+.2f}')} 다.", "",
           f"⚠ 기체가 {CORR_N} 대라 이 세 수는 서술용이다 — 같은 5행에서 순위상관을 내면 크기-문턱이 "
           f"{CORR_RHO['extent_flip'][0]:+.2f}(p={CORR_RHO['extent_flip'][1]:.2f}), 산포-문턱이 "
           f"{CORR_RHO['spread_flip'][0]:+.2f}(p={CORR_RHO['spread_flip'][1]:.2f}) 로 갈리고, 피어슨 "
           f"p 는 각각 {CORR_P['extent_flip']:.2f} · {CORR_P['spread_flip']:.2f} 다(⛔ p 와 순위상관은 "
           f"원장 밖의 재계산값이다). 원장 `size_vs_fragility.finding` 은 산포를 단독 원인으로 들지만, "
           f"이 편은 세 상관계수를 그대로 읽고 원인은 표본을 늘린 뒤로 미룬다."),

        md(*fig(1, PF["robust"],
                "σ 오차가 공통모드일 때와 밴드별일 때 순위는 각각 어디까지 버티는가?")),

        md("## 통제되지 않은 σ 변화의 관측된 파급", "",
           f"σ 격자를 블레이드 형상 갱신본으로 바꾸는 것만으로 R90 이 최대 "
           + dnum(D["stale_max_pct"], "{:.1f}", "%",
                  f"{J_SS} : staleness_and_mesh_update.by_drone",
                  "5기체 max_range_change_pct 최대")
           + f" 움직이고 순위쌍 "
             f"{SS.num('staleness_and_mesh_update.n_orders_changed', None, '{:.0f}')}개가 뒤집힌다.", "",
           MESH_WARN, "", GAMMA_WARN, "",
           f"하한 {SS.num('differential.smallest_flip_span_db_overall', None, '{:.2f}', 'dB')} 를 "
           f"내는 행이 그 정정을 받은 Matrice 4E 다. 이 하한은 **단일 자세** 기준이고, 같은 기체를 "
           f"**자세평균**으로 읽으면 "
           f"{SS.num('aspect_averaged.by_drone.matrice4e.smallest_flip_span_db', None, '{:.2f}', 'dB')}"
           f" 다 — 실측 캠페인이 판정 문턱으로 드는 수가 그것이다"
           f"({ref('session-drift', short=True)}).", "",
           f"자세평균 판에서 문턱이 가장 얇은 기체는 {ASP_FLIP_MIN_DRONE} 이고 그 값은 "
           f"{SS.num(f'aspect_averaged.by_drone.{ASP_FLIP_MIN_DRONE}.smallest_flip_span_db', None, '{:.2f}', 'dB')}"
           f" 다 — 합의 순위의 아래 두 밴드가 그만큼 붙어 있다."),

        next_steps([
            ("형상 정정 후 메쉬로 σ 민감도를 다시 돌린다",
             "뒤집힘 문턱의 하한이 현재 메쉬 위에 서고, 위 표의 차분 행이 갱신된다",
             "`benchmark/sigma_sensitivity.py`"),
            # ⛔ 옛 문장은 «산포가 정한다» 를 이미 참으로 놓고 있었다. 표본 수로 다시 적는다.
            (f"기체 수를 {CORR_N} 대 위로 늘려 크기·산포·문턱 세 열의 상관을 다시 낸다",
             "추정량(피어슨·순위상관)에 따라 갈리는 지금의 상관이 하나의 값으로 좁혀진다",
             "`benchmark/sigma_sensitivity.py`"),
        ]),
    ]


# =========================================================================== #
#  편 62 — CPI 스윕
# =========================================================================== #
def r62():
    return [
        header(
            num=62,
            title="CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다",
            did="도플러 가드가 헤딩 축을 얼마나 지우는지를 CPI 격자에서 재고, 세 파형의 "
                "블라인드 헤딩 비율과 5G 가 치르는 배수를 같은 표에 실었다.",
            results=[
                f"도플러 축을 지우는 기구는 둘이다 — **표본화**: `{CG.num('structural.formula', None)}` "
                f"로 가드가 접힘 축 전체를 덮는다(반송파·속도·거리 무관). **진폭**: 짧은 CPI 에서 "
                f"가드가 도플러 진폭을 덮는다(파형 공통).",
                f"5G 의 눈먼 헤딩 비율은 CPI "
                f"{CG.num('equal_cpi_penalty[0].T_cpi_s', None, '{:.1f}', 's')} 에서 "
                f"{CG.num('verdict.artifact.blind_hard_same_cpi', None, '{:.3f}')}, CPI "
                f"{CG.num('equal_cpi_penalty[1].T_cpi_s', None, '{:.1f}', 's')} 에서 "
                f"{CG.num('verdict.artifact.blind_hard_at_200ms', None, '{:.3f}')} 로 내려간다.",
                f"WiFi 대비 배수는 CPI "
                + dnum(CPI_T_MIN, "{:.1f}", "", f"{J_CG} : equal_cpi_penalty[*].T_cpi_s", "최소")
                + " ~ "
                + dnum(CPI_T_MAX, "{:.1f}", "s", f"{J_CG} : equal_cpi_penalty[*].T_cpi_s", "최대")
                + f" {CPI_SPAN_KO}에서 "
                + dnum(CPI_RATIO_MIN, "{:.1f}", "",
                       f"{J_CG} : equal_cpi_penalty[*].ratio_G1_over_W1", CPI_NOTE_MIN)
                + " ~ "
                + dnum(CPI_RATIO_MAX, "{:.1f}", "",
                       f"{J_CG} : equal_cpi_penalty[*].ratio_G1_over_W1", CPI_NOTE_MAX)
                + "배 로 남는다 — 이것이 이 대가를 구조로 만드는 첫 번째 사실이다.",
                # ⛔ 그 «폭» 은 물리가 아니라 헤딩 격자의 칸 수다 — 분모가 두 칸까지 내려간다.
                f"⚠ 그 폭은 헤딩 격자 {CPI_PSI_N}점 위의 **칸 수**에서 나온다 — 분모 "
                f"`blind_hard_W1` 이 {CPI_SPAN_KO}에서 {CPI_CELLS_W1_KO} 칸이고, 가장 작은 칸에서 "
                f"{CPI_W1_MIN_CELLS}칸까지 내려간다. 그 칸에서는 분모가 한 칸(={CPI_CELL_FRAC:.4f})만 "
                f"달라져도 배수가 2/3배~2배로 갈린다 — 이 격자가 정하는 것은 칸 수이고, 배수의 폭은 "
                f"이 격자로 정하지 못한다.",
                f"1.5빈 규약에서 LTE 도 CPI ≤ "
                f"{CG.num('structural.two_mechanisms.observed.L1.hard.T_max_total_blind_s', None, '{:.3f}', 's')}"
                f" 에서 전 헤딩 블라인드가 된다 — 5G 만의 성질이 아니라 CPI 가 짧을 때의 성질이다.",
            ],
            method=[
                ("가드 규약",
                 "가드 반폭 = g빈 × PRF/M 이고 g 는 검출기 적용값 1.5빈과 선언값 2.5빈 **둘 다** 잰다"),
                ("헤딩 격자",
                 f"격자가 둘이다 — 발표된 앵커를 재현하는 "
                 f"{CG.num('meta.psi_n_published', None, '{:.0f}', '점')} 과 스윕이 쓰는 "
                 f"{CG.num('meta.psi_n_fine', None, '{:.0f}', '점')} 이다. 속도는 5 m/s 로 "
                 f"고정한다 — `benchmark/cpi_guard_sweep.py`"),
                ("두 기구를 가른다",
                 "표본화가 만드는 접힘 축과 진폭이 만드는 덮임을 분리해 각각의 CPI 의존을 적는다"),
            ],
            prereq=[(ref("doppler-fold", short=True), "물리 반복률이 만드는 접힘"),
                    (ref("eca", short=True), "0-도플러 노치가 지우는 속도")],
            repro=dict(cmd=CMD[:1] + CMD[7:8] + CMD[-1:], out=[J_CG], runtime=RUNTIME),
        ),

        md("## 도플러 축을 지우는 기구는 둘이다", "",
           "5G 의 상시 기준신호(SSB)는 20 ms 주기라 PRF 50 Hz 를 준다. 그 축이 지워지는 경로가 둘이다.", "",
           f"**A. 표본화** — `{CG.num('structural.formula', None)}` 로 가드가 접힘 축 전체를 덮는다"
           "(반송파·속도·거리 무관).", "",
           "**B. 진폭** — 짧은 CPI 에서 가드가 도플러 진폭을 덮는다(파형 공통). "
           f"1.5빈 규약에서 LTE 도 CPI ≤ "
           f"{CG.num('structural.two_mechanisms.observed.L1.hard.T_max_total_blind_s', None, '{:.3f}', 's')}"
           " 에서 전 헤딩 블라인드가 된다."),

        md("## 기준 CPI 에서의 값 — 앵커 재현 격자", "",
           f"기준 CPI 는 "
           f"{CG.num('equal_cpi_penalty[0].T_cpi_s', None, '{:.1f}', 's')} 다. 아래 표는 발표된 "
           f"앵커를 그대로 재현하는 헤딩 격자 "
           f"{CG.num('meta.psi_n_published', None, '{:.0f}', '점')} 위의 값이다.", "",
           table(["모드", "PRF", "기준 CPI 의 M",
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
           f"{CG.num('structural.by_mode.G1.T_max_total_blind_hard_s', None, '{:.2f}', 's')} 다.", "",
           f"두 수는 **표본화(A) 하나로** 정한 경계다. 진폭(B)까지 함께 관측한 경계는 각각 "
           f"{CG.num('structural.two_mechanisms.observed.G1.declared.T_max_total_blind_s', None, '{:.3f}', 's')}"
           f" · "
           f"{CG.num('structural.two_mechanisms.observed.G1.hard.T_max_total_blind_s', None, '{:.3f}', 's')}"
           f" 이고, 아래 LTE 의 "
           f"{CG.num('structural.two_mechanisms.observed.L1.hard.T_max_total_blind_s', None, '{:.3f}', 's')}"
           f" 가 그 관측 잣대의 수다."),

        md("## CPI 를 늘리면 — 촘촘한 격자", "",
           f"세 파형 모두 블라인드율이 내려간다. 5G 가 치르는 **배수**는 {CPI_SPAN_KO} 전부에서 "
           + dnum(CPI_RATIO_MIN, "{:.1f}", "",
                  f"{J_CG} : equal_cpi_penalty[*].ratio_G1_over_W1", CPI_NOTE_MIN)
           + " ~ "
           + dnum(CPI_RATIO_MAX, "{:.1f}", "",
                  f"{J_CG} : equal_cpi_penalty[*].ratio_G1_over_W1", CPI_NOTE_MAX)
           + "배 로 남는다 — 이것이 이 대가를 구조로 만드는 첫 번째 사실이다.", "",
           f"아래 표는 헤딩 격자 "
           f"{CG.num('meta.psi_n_fine', None, '{:.0f}', '점')} 위의 값이라, 같은 CPI 라도 앞의 "
           f"앵커 재현 표와 값이 갈린다 — 격자가 촘촘하면 가드에 걸리는 헤딩 구간의 경계가 "
           f"더 곱게 세어진다. 본문이 드는 수는 이 촘촘한 격자 쪽이다.", "",
           table(["CPI", "WiFi", "LTE", "5G", "5G/WiFi", "5G/LTE"],
                 [[CG.num(f"equal_cpi_penalty[{i}].T_cpi_s", None, "{:.1f}", "s"),
                   CG.num(f"equal_cpi_penalty[{i}].blind_hard_W1", None, "{:.3f}"),
                   CG.num(f"equal_cpi_penalty[{i}].blind_hard_L1", None, "{:.3f}"),
                   CG.num(f"equal_cpi_penalty[{i}].blind_hard_G1", None, "{:.3f}"),
                   CG.num(f"equal_cpi_penalty[{i}].ratio_G1_over_W1", None, "{:.1f}") + "배",
                   CG.num(f"equal_cpi_penalty[{i}].ratio_G1_over_L1", None, "{:.1f}") + "배"]
                  for i in range(CPI_N_ROWS)]),
           "",
           # ⛔ 표의 블라인드 열은 실수가 아니라 격자 위의 «칸 수» 다. 그 칸 수를 그대로 적는다.
           f"⛔ 두 블라인드 열은 헤딩 격자 {CPI_PSI_N}점 위의 **칸 수**다 — WiFi 열이 "
           f"{CPI_CELLS_W1_KO} 칸, 5G 열이 {CPI_CELLS_G1_KO} 칸이다. 두 열 다 CPI 와 함께 칸 수가 "
           f"내려가고{CPI_W1_TIE_KO}. 5G/WiFi 열의 분모는 가장 작은 칸에서 {CPI_W1_MIN_CELLS}칸이라 "
           f"한 칸(={CPI_CELL_FRAC:.4f})만 달라져도 그 칸의 배수가 2/3배~2배로 갈린다 — 이 격자가 "
           f"정하는 것은 칸 수이고, 배수의 폭과 그 아래 WiFi 열의 움직임은 격자를 올려 다시 세어야 "
           f"정해진다."),

        md("## 두 번째 사실 — 접힘 비율은 CPI 와 무관하다", "",
           f"5G 의 alias 비율 "
           f"{CG.num('verdict.structural.s2_alias_floor.alias_frac_G1', None, '{:.3f}')} 는 "
           f"적분시간이 아니라 표본화율의 성질이라 CPI 와 무관한 상수이고, WiFi·LTE 는 "
           f"{CG.num('verdict.structural.s2_alias_floor.alias_frac_W1', None, '{:.3f}')} 다.", "",
           f"세 번째 사실이 결정적이고, 그것은 {ref('cpi-residual', short=True)} 가 든다."),

        next_steps([
            ("CPI 를 0.1 s 에서 1.0 s 까지 정본 solve 에 넣어 R90(CPI) 를 낸다",
             "위 표의 커버리지 회복이 거리 축에서도 확정된다",
             "`benchmark/cpi_guard_sweep.py` → `src/experiment_freespace_range.py`"),
            ("헤딩 격자를 표적 기동 모형으로 바꿔 블라인드율을 다시 잰다",
             "균일 헤딩 가정이 실제 비행에서 얼마나 낙관인지가 확정된다",
             "`benchmark/cpi_guard_sweep.py`"),
        ]),
    ]


# =========================================================================== #
#  편 63 — CPI 로도 안 지워지는 것
# =========================================================================== #
def r63():
    return [
        header(
            num=63,
            title="모호속도는 표본화율의 성질이라 CPI 와 무관한 상한이다",
            did="CPI 를 늘려 커버리지를 회복하는 길의 끝을 재고, 그 길이 무모호 속도와 코히어런스 "
                "한계에서 어디서 막히는지를 값으로 적었다.",
            results=[
                f"모호속도는 5G "
                f"{CG.num('unambiguous_speed.G1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · WiFi "
                f"{CG.num('unambiguous_speed.W1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · LTE "
                f"{CG.num('unambiguous_speed.L1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} 이고, "
                f"CPI 를 늘려도 그대로다.",
                f"커버리지를 WiFi 수준으로 올리는 CPI 는 "
                f"{CG.num('cost_of_long_cpi.required_cpi_s.to_WiFi_parity', None, '{:.2f}', 's')}, "
                f"LTE 수준은 "
                f"{CG.num('cost_of_long_cpi.required_cpi_s.to_LTE_parity', None, '{:.2f}', 's')} 이고 "
                f"그 대가는 재방문 시간이다.",
                f"그 CPI 가 코히어런스 한계 안에 머무는 구간은 "
                f"{CG.num('cost_of_long_cpi.by_speed[6].speed_ms', None, '{:.0f}', 'm/s')} 까지다 — "
                f"{CG.num('cost_of_long_cpi.by_speed[7].speed_ms', None, '{:.0f}', 'm/s')} 에서 WiFi "
                f"패리티 CPI 가 한계 "
                f"({CG.num('cost_of_long_cpi.by_speed[7].T_coh_s', None, '{:.2f}', 's')}) 를 넘어선다.",
                f"거리·속도 격자 "
                f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_cells', None, '{:.0f}')}칸 중 "
                f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_WiFi_parity_feasible', None, '{:.0f}')}"
                f"칸이 WiFi 패리티를 허용한다 — 그중 여유가 가장 얇은 칸은 {CM_TIGHT_KO} 로, "
                f"코히어런스 한계 {CM_TIGHT_TCOH:.2f} s 가 필요 CPI "
                f"{CG.num('cost_of_long_cpi.required_cpi_s.to_WiFi_parity', None, '{:.2f}', 's')} 보다 "
                f"{CM_TIGHT_MARGIN_PCT:.0f} % 높다.",
                # ⛔ 그 필요 CPI 는 칸 수 두 개가 같아지는 자리에서 등호로 읽힌 값이다.
                f"⚠ 그 필요 CPI 는 헤딩 격자 {CPI_PSI_N}점의 눈먼 **칸 수**를 견줘 읽은 값이다 — "
                f"{PARITY_EDGE_KO}. 여유 {CM_TIGHT_MARGIN_PCT:.0f} % 인 칸이 통과 쪽에 남는지는 이 "
                f"원장으로 정할 수 없다.",
            ],
            method=[
                ("모호속도",
                 "PRF 와 λ 가 정한다. 적분시간을 늘려도 표본화율은 그대로이므로 이 상한은 안 움직인다"),
                ("패리티 CPI",
                 "5G 의 블라인드율을 다른 파형 수준으로 내리는 데 필요한 CPI 를 스윕에서 읽는다"),
                ("코히어런스 한계",
                 "표적이 움직이는 동안 위상이 유지되는 시간이다. 패리티 CPI 가 그 한계를 넘으면 "
                 "코히어런트 적분이 성립하지 않는다"),
                ("대가 열",
                 "필요 CPI · SSB 버스트 수 · 헤드라인 CPI 대비 경과 · 거리워크 · 코히어런트 이득을 "
                 "같은 표에 실어 대가의 형태를 갈라 놓는다"),
            ],
            prereq=[(ref("cpi-sweep", short=True), "CPI 를 늘렸을 때 회복되는 몫")],
            repro=dict(cmd=CMD[:1] + CMD[7:8] + CMD[-1:], out=[J_CG], runtime=RUNTIME),
        ),

        md("## 세 번째 사실이 결정적이다", "",
           f"모호속도는 표본화율의 성질이라 CPI 로 바뀌지 않는다 — 5G "
           f"{CG.num('unambiguous_speed.G1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · WiFi "
           f"{CG.num('unambiguous_speed.W1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · LTE "
           f"{CG.num('unambiguous_speed.L1.v_unambiguous_ms', None, '{:.2f}', 'm/s')}.", "",
           f"커버리지를 WiFi 수준으로 올리는 CPI 는 "
           f"{CG.num('cost_of_long_cpi.required_cpi_s.to_WiFi_parity', None, '{:.2f}', 's')}, LTE "
           f"수준은 {CG.num('cost_of_long_cpi.required_cpi_s.to_LTE_parity', None, '{:.2f}', 's')} "
           f"이고 그 대가는 재방문 시간이다.", "",
           # ⛔ 그 필요 CPI 가 어디서 왔는지 — `parity_cpi()` 는 칸 수 두 개를 `≤` 로 견준다.
           f"⛔ WiFi 패리티 CPI 는 `parity_cpi()` 가 헤딩 격자 {CPI_PSI_N}점의 눈먼 **칸 수**를 `≤` "
           f"로 견줘 읽은 값이다 — {PARITY_EDGE_KO}. 그래서 이 원장이 정하는 것은 «칸 수가 같아지는 "
           f"자리» 다."),

        md("## 패리티의 대가", "",
           table(["패리티 목표 (5 m/s)", "필요 CPI", "SSB 버스트", "헤드라인 CPI 대비 경과", "거리워크",
                  "코히어런트 이득"],
                 [[nm,
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.T_required_s", None, "{:.2f}", "s"),
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.ssb_bursts_needed", None, "{:.0f}"),
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.elapsed_vs_headline", None,
                          "{:.2f}") + "배",
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.range_walk_bins_median", None,
                          "{:.3f}") + "빈",
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.snr_gain_db_if_coherent", None,
                          "{:.2f}", "dB")]
                  for nm, k in (("LTE 수준", "v5_LTE_parity"), ("WiFi 수준", "v5_WiFi_parity"))]),
           "",
           # ⛔ WiFi 행의 «10.00배 · 10.00 dB» 는 필요 CPI 가 정확히 1.00 s 로 읽힌 데서 나온다.
           f"⛔ WiFi 행의 경과·이득이 딱 떨어지는 것은 그 행의 필요 CPI 가 헤드라인 CPI "
           f"{CPI_T_MIN:.1f} s 의 "
           + CG.num("cost_of_long_cpi.at_required_cpi.v5_WiFi_parity.elapsed_vs_headline",
                    None, "{:.0f}")
           + f"배로 읽혔기 때문이다 — {PARITY_EDGE_KO}. 두 열은 그 CPI "
           f"에서 따라 나오는 산수다(경과 = T / 헤드라인 CPI, 코히어런트 이득 = 10log₁₀ 그 배수)."),

        md("## 그 길이 막히는 자리", "",
           f"패리티 CPI 가 코히어런스 한계 안에 머무는 구간은 "
           f"{CG.num('cost_of_long_cpi.by_speed[6].speed_ms', None, '{:.0f}', 'm/s')} 까지이고, "
           f"{CG.num('cost_of_long_cpi.by_speed[7].speed_ms', None, '{:.0f}', 'm/s')} 에서 WiFi "
           f"패리티 CPI 가 한계 "
           f"({CG.num('cost_of_long_cpi.by_speed[7].T_coh_s', None, '{:.2f}', 's')}) 를 넘어선다.", "",
           f"거리·속도 격자 "
           f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_cells', None, '{:.0f}')}칸 중 "
           f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_WiFi_parity_feasible', None, '{:.0f}')}"
           f"칸이 WiFi 패리티를 허용한다 — 그 밖의 칸에서는 CPI 로 메우는 길이 닫힌다.", "",
           # ⛔ 통과하는 칸의 가장자리가 필요 CPI 가 등호로 읽힌 자리 바로 옆에 있다.
           f"⛔ 통과하는 칸 중 여유가 가장 얇은 것은 {CM_TIGHT_KO} 로, 코히어런스 한계 "
           f"{CM_TIGHT_TCOH:.4f} s 가 필요 CPI "
           f"{CG.num('cost_of_long_cpi.required_cpi_s.to_WiFi_parity', None, '{:.2f}', 's')} 보다 "
           f"{CM_TIGHT_MARGIN_PCT:.1f} % 높을 뿐이다. 그 필요 CPI 는 {PARITY_EDGE_KO} — 그래서 이 한 "
           f"칸이 통과 쪽에 남는지는 격자를 올려 다시 세어야 정해진다."),

        md(*fig(1, PF["cpi"],
                "5G 의 눈먼 헤딩 비율은 CPI 와 표적 속도에 따라 어떻게 움직이는가?")),

        next_steps([
            ("재방문 시간 예산을 세워 긴 CPI 의 대가를 값으로 적는다",
             "패리티 CPI 가 운용에서 감당되는 값인지가 확정된다",
             ref("three-layers", short=True)),
            ("거리워크 보상을 켠 뒤 패리티 CPI 를 다시 잰다",
             "코히어런스 한계가 보상으로 얼마나 밀리는지가 확정된다",
             "`benchmark/cpi_guard_sweep.py`"),
        ]),
    ]


# =========================================================================== #
#  편 64 — σ 를 곱하기 전 축
# =========================================================================== #
def r64():
    return [
        header(
            num=64,
            title="σ 를 곱하기 전에 이미 세 파형의 순서를 정하는 축이 있다",
            did="같은 표적·같은 기하·같은 σ 로 묶은 벤치에서 Pd = 0.5 에 필요한 출력 SNR 을 재고, "
                "두 점유 등급 사이의 요구 SNR 차를 표준마다 dB 로 적었다.",
            results=[
                f"WiFi 는 상시 기준(등급 1)에서 "
                f"{DV.num('always_on_cost.W.snr50_g1', None, '{:.2f}', 'dB')}, 세션 기준(등급 3)에서 "
                f"{DV.num('always_on_cost.W.snr50_g3', None, '{:.2f}', 'dB')} 라 두 등급의 차가 "
                f"{DV.num('always_on_cost.W.cost_db', None, '{:+.2f}', 'dB')} 다.",
                "⛔ 그 차는 기준신호 대역의 몫이 아니다 — W1·W3 의 기준신호 대역은 "
                + RX.num("modes.W1.ref_bw_mhz", None, "{:.2f}", "MHz") + " ↔ "
                + RX.num("modes.W3.ref_bw_mhz", None, "{:.2f}", "MHz") + " 로 같고, 데이터 점유가 "
                + RX.num("modes.W1.occupancy", None, "{:.1%}") + " → "
                + RX.num("modes.W3.occupancy", None, "{:.1%}") + " 로 갈린다.",
                f"LTE 의 차는 {DV.num('always_on_cost.L.cost_db', None, '{:+.2f}', 'dB')}, 5G 는 "
                f"{DV.num('always_on_cost.G.cost_db', None, '{:+.2f}', 'dB')} 다 — 셋 다 K = "
                f"{DV.num('rx_gain.K', None, '{:.0f}')} 몬테카를로 SNR50 두 값의 차이고, 이 원장의 "
                f"표준편차 {DV.num('rx_gain.snr50_mc_sigma_db', None, '{:.3f}', 'dB')} 는 벤치 전 "
                f"모드·전 N 의 최댓값이라(`src/make_report05_results.py:290`) 모드 쌍별 유의성은 이 "
                f"원장 밖에 있다.",
                f"이 축은 σ 와 무관하다 — 표적·기하·σ 를 한 값으로 묶었으므로 여기서 읽는 것은 "
                f"파형 축 하나의 상대 비교다.",
                f"벤치 배치는 단일 반송파 {DV.num('bench.fc_ghz', None, '{:.1f}', 'GHz')} · "
                f"바이스태틱 거리 {DV.num('bench.Rb_m', None, '{:.1f}', 'm')} · 고정 σ "
                f"{DV.num('bench.sigma_dbsm', None, '{:.2f}', 'dBsm')} 다.",
            ],
            method=[
                ("무엇을 고정했나",
                 "9모드 전부에 단일 반송파·단일 기하·단일 σ 를 쓴다 — `src/experiment_x410.py:101`"),
                ("무엇을 읽나",
                 "기준신호 대역 · 프레임 수 · 데이터 점유가 함께 정하는 파형 축 하나다. 그래서 이 "
                 "순서는 σ 를 곱하기 앞에서 이미 정해진다"),
                ("상관 기준 규약",
                 "기지 기준신호가 아니라 그 모드의 **송신파형 전체**를 상관 기준으로 쓴다 — "
                 "`src/experiment_detection.py:145` 의 `ref_cpi = np.tile(block, b * M)`, 규약은 "
                 "같은 파일 `:124` 주석에 «full-waveform capture 상한» 으로 적혀 있다"),
                ("다른 절과의 관계",
                 "이 스윕은 자유공간 배치와 **다른 배치**에서 돈다 — 절대 SNR 을 그 배치의 거리와 "
                 "같은 축에 놓는 일은 다음 단계에 있다"),
            ],
            prereq=[(ref("cost-ledger", short=True), "점유 등급과 기준신호 대역의 대가")],
            repro=dict(cmd=CMD[:1] + CMD[6:7] + CMD[-1:], out=[J_RX, J_DV], runtime=RUNTIME),
        ),

        md("## 기준신호 대역과 점유 등급이 만드는 축", "",
           "같은 표적·같은 기하·같은 검출기에서 Pd = 0.5 에 필요한 출력 SNR 은 기준신호 대역 · "
           "프레임 수 · 데이터 점유가 정한다. 이 축은 σ 와 무관하게 세 파형의 순서를 정한다.", "",
           "⚠ 상시(등급 1) ↔ 세션(등급 3) 사이에서 셋 중 무엇이 갈리는지는 표준마다 다르다 — "
           "아래 표의 차이 열은 그래서 표준마다 다른 입력을 잰다."),

        md(table(["표준", "상시 기준(등급 1)", "세션 기준(등급 3)", "등급 1 − 등급 3",
                  "거리분해능 대비"],
                 [[nm,
                   DV.num(f"always_on_cost.{c}.snr50_g1", None, "{:.2f}", "dB"),
                   DV.num(f"always_on_cost.{c}.snr50_g3", None, "{:.2f}", "dB"),
                   DV.num(f"always_on_cost.{c}.cost_db", None, "{:+.2f}", "dB"),
                   DV.num(f"always_on_cost.{c}.dr_g1_m", None, "{:.2f}", "m") + " ↔ "
                   + DV.num(f"always_on_cost.{c}.dr_g3_m", None, "{:.2f}", "m")]
                  for nm, c in (("WiFi", "W"), ("LTE", "L"), ("5G NR", "G"))]),
           "",
           f"⛔ 차이 열은 표준마다 다른 입력을 잰다 — 두 등급 사이에서 갈린 입력이 행마다 다르다. "
           f"5G 는 기준신호 대역이 {RX.num('modes.G1.ref_bw_mhz', None, '{:.1f}', 'MHz')} → "
           f"{RX.num('modes.G3.ref_bw_mhz', None, '{:.2f}', 'MHz')} 로 갈리고, LTE 는 대역이 "
           f"{RX.num('modes.L1.ref_bw_mhz', None, '{:.3f}', 'MHz')} → "
           f"{RX.num('modes.L3.ref_bw_mhz', None, '{:.3f}', 'MHz')} 이고 기준신호가 "
           f"{RX.num('modes.L1.ref_name')} → {RX.num('modes.L3.ref_name')} 로 바뀌며, "
           f"WiFi 는 두 등급이 "
           f"{RX.num('modes.W1.ref_bw_mhz', None, '{:.2f}', 'MHz')} 로 같다.", "",
           "⚠ 데이터 점유는 송신파형 자체를 바꾸고, 이 벤치는 그 송신파형 전체를 상관 기준으로 "
           "쓴다(`src/experiment_detection.py:145`). "
           + ref("cost-ledger", short=True) + " 는 「데이터 심볼 자체는 수신기가 내용을 몰라 "
           "정합필터 템플릿이 못 된다」 고 적었다 — 두 편의 규약이 갈린 자리이고, 어느 쪽이 "
           "야외에서 서는지는 실측 몫이다."),

        md("## 이 스윕이 서 있는 배치", "",
           f"이 스윕은 자유공간 배치와 **다른 배치**에서 돈다 — X410 벤치"
           f"(`src/experiment_x410.py:101`), 단일 반송파 "
           f"{DV.num('bench.fc_ghz', None, '{:.1f}', 'GHz')} 를 9모드 전부에 쓰고, 바이스태틱 거리 "
           f"{DV.num('bench.Rb_m', None, '{:.1f}', 'm')}, 고정 σ "
           f"{DV.num('bench.sigma_dbsm', None, '{:.2f}', 'dBsm')} 다.", "",
           "표적·기하·σ 를 한 값으로 묶었으므로 여기서 읽는 것은 **파형 축 하나**의 상대 비교다. "
           "그래서 이 순서는 σ 논의가 어떻게 끝나든 그대로 남는다."),

        next_steps([
            ("파형·수신소자 스윕을 자유공간 배치와 물리 PRF 로 옮긴다",
             "이 축의 절대 SNR 이 자유공간 거리와 같은 축에 놓인다",
             "`src/experiment_detection.py` 의 X410Scenario → `src/freespace_scene.py`"),
            ("등급 2(세션 일부) 를 같은 표에 넣는다",
             "상시와 풀로드 사이의 중간 체제가 대가 축에서 어디에 앉는지가 확정된다",
             ref("cost-ledger", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 65 — 표적모형 민감도
# =========================================================================== #
def r65():
    return [
        header(
            num=65,
            title="평판·큐브·우리 격자를 같은 동작점에서 갈아끼우면 요구 이득이 이만큼 달라진다",
            did="같은 기하·같은 검출기·같은 동작점에서 표적만 세 모형으로 갈아끼우고, 자세평균을 "
                "맞춘 뒤 남는 요구 추가이득을 추정량별로 적었다.",
            results=[
                f"세 모형은 자세무관 평판 σ "
                f"{TM.num('protocol.operating_point.sigma_reference_dbsm', None, '{:.2f}', 'dBsm')}"
                f"(3GPP TR 38.901 RCS model 1 의 σ_M 상수, M1 — 확률항 σ_S 는 우리가 평균에 "
                f"얼렸다) · 정육면체(M2) · 우리 SBR+PO 격자(M3, {M3_STAMP}) 다.",
                f"자세 앙상블은 셀당 "
                f"{TM.num('statistics.n_aspect_realisations_per_cell', None, '{:.0f}')}자세 전수, "
                f"(기체×밴드) 셀은 "
                f"{TM.num('statistics.n_drone_band_cells', None, '{:.0f}')}개이고 재현편차는 "
                f"{TA.num('meta.reproduction.E0_extra_gain_max_abs_dev_db', None, '{:.2f}', 'dB')} 다.",
                f"낙차의 소유자는 정육면체다 — 자유공간에서 최대가 M2 인 셀이 "
                f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmax_counts.M2', None, '{:.0f}')}"
                f"개, 최소가 M1 인 셀이 "
                f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmin_counts.M1', None, '{:.0f}')}"
                f"개로 전수다.",
                f"크기는 **추정량이 정한다** — 검출기가 읽는 p10 에서 맞추면 낙차가 "
                f"{TA.num(f'{TAE}.p10.spread_mean', None, '{:.2f}', 'dB')} 로 줄어든다. ⛔ 이때 "
                f"M1 이 «가장 어려운 팔» 로 올라서는 것은 M1 의 자세분산이 "
                f"{TM.num(M1_STD, None, '{:.1f}', 'dB')} 라 어느 분위수로 맞춰도 M1 이 같은 값인 "
                f"산술이고, p10 순서 계수는 `M3<M2<M1` "
                f"{TA.num(f'{P10_ORD}.M3<M2<M1', None, '{:.0f}')}셀 · `M2<M3<M1` "
                f"{TA.num(f'{P10_ORD}.M2<M3<M1', None, '{:.0f}')}셀 둘뿐이다.",
                f"각 다양성이 낙차를 줄인다 — 각 다양성이 0 인 자유공간에서 "
                f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E0_freespace', None, '{:.2f}', 'dB')}"
                f", 가장 큰 앙상블에서 "
                f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E2b_outdoor_shadowed', None, '{:.2f}', 'dB')}"
                f" 다.",
            ],
            method=[
                ("갈아끼우는 것",
                 "기하·검출기·동작점을 고정하고 표적 모형만 셋으로 바꾼다 — 그래서 남는 차이는 "
                 "표적 모형의 몫이다"),
                ("자세 앙상블",
                 "셀당 자세 전수를 돌리고 자세평균을 맞춘 뒤 남는 **요구 추가이득**을 읽는다"),
                ("추정량",
                 "선형평균(이 실험의 규약) · 중앙값 · dB 평균 · p10(검출기가 읽는 분위수) 넷을 "
                 "나란히 싣는다"),
                ("문턱 규약",
                 "잡음전력 기지 이상문턱이다. CA-CFAR 문턱은 세 팔에 같은 오프셋을 주므로 모형 간 "
                 "차이는 문턱 규약에 불변이다"),
            ],
            prereq=[(ref("r90", short=True), "우리 격자 위의 검출거리와 순위"),
                    (ref("cfar-calib", short=True), "교정된 오경보율 위의 절대 소요이득")],
            repro=dict(cmd=CMD[:1] + CMD[-1:], out=[J_TM, J_TA], runtime=RUNTIME),
        ),

        md("## 표적만 세 모형으로 갈아끼운다", "",
           f"같은 기하·같은 검출기·같은 동작점에서 표적만 셋으로 갈아끼운다 — 자세무관 평판 σ "
           f"{TM.num('protocol.operating_point.sigma_reference_dbsm', None, '{:.2f}', 'dBsm')}"
           f"(3GPP TR 38.901 RCS model 1 의 σ_M 상수, M1) · 정육면체(M2) · "
           f"우리 SBR+PO 격자(M3).", "",
           f"M3 팔이 선 판을 함께 찍는다 — {M3_STAMP}. σ 격자의 신원은 "
           f"「{TM.num('staleness.what_is_stale', None)}」 다. M1 은 3GPP 표값 상수이고 M2 는 "
           f"현재 메쉬 bbox 로 잡은 모서리라, 이 판 표시는 M3 열에만 붙는다.", "",
           f"⚠ M1 의 «평평함» 은 절반만 3GPP 다 — TR 38.901 은 σ_M 과 함께 로그정규 σ_S 를 주고 "
           f"그것을 경로마다 뽑는데, 헤드라인은 그것을 평균(=1)에 얼렸다. "
           f"원장이 규정대로 다시 뽑으니 M1 도 "
           f"{TA.num(f'{Q5R}.m1_penalty_if_drawn_db', None, '{:.2f}', 'dB')} 를 물어 M3−M1 이 "
           f"{TA.num(f'{Q5R}.m3_minus_m1_frozen_db', None, '{:.2f}', 'dB')} → "
           f"{TA.num(f'{Q5R}.m3_minus_m1_live_db', None, '{:.2f}', 'dB')} 로, 3모형 낙차가 "
           f"{TA.num(f'{Q5R}.spread_frozen_mean_db', None, '{:.2f}', 'dB')} → "
           f"{TA.num(f'{Q5R}.spread_live_mean_db', None, '{:.2f}', 'dB')} 로 내려간다.", "",
           f"⛔ M1 열은 측정이 아니라 **눈금**이다 — 동작점 A_ref 를 «평판 "
           f"{TM.num('protocol.operating_point.sigma_reference_dbsm', None, '{:.2f}', 'dBsm')} 이 "
           f"앙상블평균 Pd = 0.9 에 정확히 앉도록» 정의했고, 원장이 그 자리에 «it is the ruler, "
           f"not a result» 라고 적었다⟨{J_TM} : protocol.operating_point.definition⟩.", "",
           f"자세 앙상블은 셀당 "
           f"{TM.num('statistics.n_aspect_realisations_per_cell', None, '{:.0f}')}자세 전수, "
           f"(기체×밴드) 셀은 {TM.num('statistics.n_drone_band_cells', None, '{:.0f}')}개이고, "
           f"자세평균을 맞춘 뒤 남는 **요구 추가이득**을 추정량별로 적는다(재현편차 "
           f"{TA.num('meta.reproduction.E0_extra_gain_max_abs_dev_db', None, '{:.2f}', 'dB')})."),

        md(table(["무엇을 맞추나", "M1 평판 [dB] — 눈금(동작점 정의)", "M2 정육면체 [dB]",
                  f"M3 우리 SBR+PO 격자 [dB] ({M3_STAMP_PLAIN})"],
                 [[nm,
                   TA.num(f"{TAE}.{k}.per_model_extra_gain_db.M1", None, "{:+.2f}"),
                   TA.num(f"{TAE}.{k}.per_model_extra_gain_db.M2", None, "{:+.2f}"),
                   TA.num(f"{TAE}.{k}.per_model_extra_gain_db.M3", None, "{:+.2f}")]
                  for nm, k in (("선형평균 — 이 실험의 규약", "mean_lin"),
                                ("중앙값", "median"),
                                ("dB 평균", "mean_db"),
                                ("p10 — 검출기가 읽는 분위수", "p10"))]),
           "",
           f"⛔ M1 열의 네 개 +0.00 은 네 번의 독립 확인이 아니라 같은 항등식 하나다 — 원장이 "
           f"재계산한 추정량 일곱 갈래(무정규화·선형평균·중앙값·dB 평균·p10·p95·최대) 전부에서 "
           f"M1 이 부동소수 잡음까지 같은 값이다⟨{J_TA} : {TAE}⟩."),

        md("## 낙차의 소유자는 정육면체다", "",
           f"자유공간에서 최대가 M2 인 셀이 "
           f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmax_counts.M2', None, '{:.0f}')}"
           f"개, 최소가 M1 인 셀이 "
           f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmin_counts.M1', None, '{:.0f}')}"
           f"개로 전수이고, M3 몫은 다섯 앙상블에서 "
           f"{TA.num('Q3_staleness.argmax_argmin_counts.E2_outdoor_canyon.m3_share_of_spread', None, '{:.1%}')}"
           f" ~ "
           f"{TA.num('Q3_staleness.argmax_argmin_counts.E1_chamber_floor.m3_share_of_spread', None, '{:.1%}')}"
           f" 다.", "",
           f"각 다양성이 그 낙차를 줄인다 — 각 다양성이 0 인 자유공간(N_eff "
           f"{TM.num('verdicts.Q3_environment_dependence.predictor.E0_freespace.n_eff_pairs', None, '{:.1f}')})"
           f"에서 "
           f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E0_freespace', None, '{:.2f}', 'dB')}"
           f", 각 다양성이 가장 큰 앙상블(N_eff "
           f"{TM.num('verdicts.Q3_environment_dependence.predictor.E2b_outdoor_shadowed.n_eff_pairs', None, '{:.2f}')})"
           f"에서 "
           f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E2b_outdoor_shadowed', None, '{:.2f}', 'dB')}"
           f" 다."),

        md("## 크기는 추정량이 정한다", "",
           f"⚠ 낙차의 크기는 레벨을 무엇으로 맞추느냐가 정한다 — 선형평균 "
           f"{TA.num(f'{TAE}.mean_lin.spread_mean', None, '{:.2f}', 'dB')} · 중앙값 "
           f"{TA.num(f'{TAE}.median.spread_mean', None, '{:.2f}', 'dB')} · dB 평균 "
           f"{TA.num(f'{TAE}.mean_db.spread_mean', None, '{:.2f}', 'dB')} · p10 "
           f"{TA.num(f'{TAE}.p10.spread_mean', None, '{:.2f}', 'dB')} 다. 헤드라인은 선형평균 "
           f"일치를 쓴다.", "",
           f"⛔ p10 에서 M1 이 «가장 어려운 팔» 로 올라서는 것은 분산 0 의 산술이다 — M1 의 "
           f"자세분산이 {TM.num(M1_STD, None, '{:.1f}', 'dB')} 라 M1 은 p10 에서도 "
           f"{TA.num(f'{TAE}.p10.per_model_extra_gain_db.M1', None, '{:+.2f}', 'dB')} 인데 M2 는 "
           f"{TA.num(f'{TAE}.p10.per_model_extra_gain_db.M2', None, '{:+.2f}', 'dB')} · M3 는 "
           f"{TA.num(f'{TAE}.p10.per_model_extra_gain_db.M3', None, '{:+.2f}', 'dB')} 로 내려간다. "
           f"이 정규화는 순환적이라 정본이 되지 못한다.", "",
           f"문턱은 잡음전력 기지 이상문턱이고 CA-CFAR 문턱은 세 팔에 같은 오프셋을 주므로, "
           f"교정표는 세 팔의 절대 소요이득만 옮긴다(⟨{J_TM} : protocol.pfa_convention⟩)."),

        md("## 이 표에 구 대조군은 없다", "",
           "구는 **부피를 맞게 고르면** σ 의 절대 레벨을 맞출 수 있는 단순 모형이면서 자세에 따른 "
           "변화를 0 으로 낸다. 레벨에서 우리 메쉬를 앞선 그 구는 논문이 적어 둔 상자 치수로 잡은 "
           "부피이고, 메쉬 부피로 잡으면 두 잣대 모두에서 우리 메쉬보다 나쁘다.", "",
           "그래서 이 표의 낙차는 «자세 구조를 얼마나 담는가» 의 낙차로 읽는다. 구 팔을 넣는 일은 "
           "다음 단계에 있다."),

        next_steps([
            ("M1 을 3GPP 규정대로 σ_S 를 뽑아 돌린 M1c 분기를 정본으로 세운다",
             "M3−M1 이 "
             + TA.num(f"{Q5R}.m3_minus_m1_frozen_db", None, "{:.2f}", "dB") + " 인지 "
             + TA.num(f"{Q5R}.m3_minus_m1_live_db", None, "{:.2f}", "dB")
             + " 인지가 우리 규약이 아니라 표준 규정으로 정해진다",
             "`scratchpad/tm_result.py`"),
            ("표적모형 민감도의 M3 팔을 재생성 격자(형상 정정 + Γ(θ) 켠 커널)로 다시 푼다",
             "우리 팔의 요구 추가이득 "
             + TA.num("Q3_staleness.m3_own_number.base_db", None, "{:.2f}", "dB")
             + " 와 낙차 몫 "
             + TA.num("Q3_staleness.argmax_argmin_counts.E0_freespace.m3_share_of_spread", None,
                      "{:.1%}")
             + " 가 현재 메쉬 위에 선다",
             "`scratchpad/tm_result.py`"),
            ("표적모형에 **구 팔(M4)** 을 더한다",
             "레벨만 맞추는 모형과 자세 구조를 담는 모형의 검출 낙차가 갈라진다",
             "`scratchpad/tm_result.py` → " + ref("box-sphere-control", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 66 — 수신소자
# =========================================================================== #
def r66():
    return [
        header(
            num=66,
            title=f"코히어런트 배열이득은 10log₁₀N 상한에 "
                  f"{fetch((J_DV, 'rx_gain.excess_min_db')):+.2f}~"
                  f"{fetch((J_DV, 'rx_gain.excess_max_db')):+.2f} dB 로 붙는다",
            did="한 지점 λ/2 배열의 소자 수 N 을 늘려가며 SNR50 을 재고, 그 이득이 열잡음 "
                "코히어런트 상한 10log₁₀N 에서 얼마나 벗어나는지를 두 방식으로 확인했다.",
            results=[
                f"9모드 × N 전체에서 측정 이득은 상한 대비 "
                f"{DV.num('rx_gain.excess_min_db', None, '{:+.2f}')} ~ "
                f"{DV.num('rx_gain.excess_max_db', None, '{:+.2f}', 'dB')} 다.",
                f"결합 잡음전력/σ² = {RX.num('modes.W1.combine_ratio', None, '{:.5f}')} 로 잡음 "
                f"보존을 확인했다 — 10log₁₀N 은 **열잡음만** 상대할 때의 이상적 상한이다.",
                f"초과분의 출처는 ECA 잔차다 — 감시신호가 `surv = √N·echo + dpi + noise` 이고 "
                f"`dpi` 는 N 에 무관하게 고정이라 √N 이 잡음과 잔차 양쪽 대비로 표적을 올린다.",
                f"격자 보간의 대조군으로 Pd 곡선에 로지스틱을 다시 적합해도 초과분이 "
                f"{DV.num('rx_gain.excess_fit_min_db', None, '{:+.2f}')} ~ "
                f"{DV.num('rx_gain.excess_fit_max_db', None, '{:+.2f}', 'dB')} 로 같다.",
                f"몬테카를로 표준편차(K = {DV.num('rx_gain.K', None, '{:.0f}')})는 "
                f"{DV.num('rx_gain.snr50_mc_sigma_db', None, '{:.3f}', 'dB')} 이고, 최대 초과분은 "
                f"단일 추정 σ 의 {DV.num('rx_gain.excess_in_sigma', None, '{:.1f}')}σ · 이득(두 "
                f"SNR50 추정의 차)의 √2σ 로는 "
                + dnum(D["rx_excess_in_sigma"] / math.sqrt(2.0), "{:.1f}", "σ",
                       f"{J_DV} : rx_gain.excess_in_sigma", "÷√2 — 두 추정의 차") + " 다.",
            ],
            method=[
                ("배열",
                 "한 지점 λ/2 ULA 소자 N 개, 조향은 참 표적 방향 — `src/experiment_detection.py:181`"),
                ("상한의 뜻",
                 "10log₁₀N 은 **열잡음만** 상대할 때의 코히어런트 배열이득이고, 소자 간 결합·"
                 "교정오차·위치오차가 0 인 이상적 값이다"),
                ("초과분 두 방식",
                 "격자 보간으로 읽은 SNR50 과 로지스틱 재적합으로 읽은 SNR50 을 나란히 재, "
                 "초과분이 보간 방식의 산물인지 확인한다"),
                ("잡음 보존",
                 "결합 잡음전력/σ² 을 재 배열 결합이 잡음을 키우거나 줄이지 않았음을 확인한다"),
            ],
            prereq=[(ref("observability", short=True), "수신기를 늘렸을 때 풀리는 것"),
                    (ref("sigma-free-axis", short=True), "이 스윕이 서 있는 벤치 배치")],
            repro=dict(cmd=CMD[:1] + CMD[6:7] + CMD[-1:], out=[J_RX, J_DV], runtime=RUNTIME),
        ),

        md("## 수신소자를 늘리면", "",
           "N 은 한 지점 λ/2 ULA 소자 수다(`src/experiment_detection.py:181`). 조향벡터를 참 표적 "
           "방향에 맞추고, 결합 잡음전력/σ² = "
           + RX.num("modes.W1.combine_ratio", None, "{:.5f}")
           + " 로 잡음 보존을 확인했다.", "",
           "그래서 10log₁₀N 은 **열잡음만** 상대할 때의 코히어런트 배열이득이고, 소자 간 결합·"
           "교정오차·위치오차가 0 인 **이상적 상한**이다."),

        md(table(["N"] + [str(n) for n in D["ns"]],
                 [["측정 이득 (WiFi) = SNR50(1)−SNR50(N)"]
                  + [f"{g:+.2f} dB" for g in D["rx_gain_W1"]],
                  ["열잡음 기준선 10log₁₀N"] + [f"{b:+.2f} dB" for b in D["rx_bound"]],
                  ["차 (WiFi)"] + [f"{g - b:+.2f} dB"
                                   for g, b in zip(D["rx_gain_W1"], D["rx_bound"])]]),
           "",
           f"출처 ⟨{J_RX} : modes.W1.curves.*.snr50⟩"),

        md("## 초과분은 어디서 오나", "",
           f"9모드 × N 전체에서 측정 이득은 상한 대비 "
           f"{DV.num('rx_gain.excess_min_db', None, '{:+.2f}')} ~ "
           f"{DV.num('rx_gain.excess_max_db', None, '{:+.2f}', 'dB')} 다.", "",
           "감시신호가 `surv = √N·echo + dpi + noise` 이고 ECA 잔차 `dpi` 는 N 에 무관하게 고정이라"
           "(`src/experiment_detection.py:284`), √N 이 잡음과 잔차 양쪽 대비로 표적을 올린다 — "
           "x 축 SNR 은 잡음 기준 정의다(`:238`)."),

        md("## 그 초과분이 보간의 산물인지 확인한다", "",
           table(["검사", "값"],
                 [["Pd 곡선에 로지스틱을 다시 적합해 잰 초과분",
                   DV.num("rx_gain.excess_fit_min_db", None, "{:+.2f}") + " ~ "
                   + DV.num("rx_gain.excess_fit_max_db", None, "{:+.2f}", "dB")],
                  ["SNR50 의 몬테카를로 표준편차 (K = "
                   + DV.num("rx_gain.K", None, "{:.0f}") + ")",
                   DV.num("rx_gain.snr50_mc_sigma_db", None, "{:.3f}", "dB")],
                  ["최대 초과분 / 몬테카를로 σ",
                   DV.num("rx_gain.excess_in_sigma", None, "{:.1f}") + "σ (단일 추정 기준) · "
                   + dnum(D["rx_excess_in_sigma"] / math.sqrt(2.0), "{:.1f}", "σ",
                          f"{J_DV} : rx_gain.excess_in_sigma", "÷√2 — 두 추정의 차")
                   + " (이득 = 두 추정의 차 기준)"]])),

        md(*fig(1, PF["multirx"],
                "수신소자를 늘렸을 때 얻는 감도는 이상적 코히어런트 상한에 얼마나 붙는가?")),

        next_steps([
            ("`SIONNA2_DPI_AMP=0` 대조군으로 Rx 스윕을 다시 돌린다",
             "초과분이 ECA 잔차 대비 이득임이 대조군으로 확정된다",
             "`src/experiment_detection.py:115`"),
            ("소자 간 결합과 교정오차를 넣어 상한 대비 손실을 잰다",
             "이상적 상한과 실제 배열 사이의 간격이 수치로 확정된다",
             ref("hardware", short=True)),
        ]),
    ]


# =========================================================================== #
#  논문 조각 — 옛 report05 c23
# =========================================================================== #
def write_paper_doc() -> str:
    nb = os.path.join(_ROOT, "archive", "legacy_reports", "report05_results.ipynb")
    with open(nb, encoding="utf-8") as f:
        cells = json.load(f)["cells"]
    if len(cells) <= 23:
        # 옛 노트북(report05_results.ipynb)이 비워져 논문 부록 셀(c23)이 없다 —
        # 마지막으로 생성된 docs/paper/05_results.md 를 그대로 보존하고 재생성만 건너뛴다.
        p = os.path.join(_ROOT, "docs", "paper", "05_results.md")
        print(f"⚠ {os.path.relpath(nb, _ROOT)} 에 셀 24개가 없다({len(cells)}개) — "
              f"논문 조각 재생성을 건너뛰고 기존 {os.path.relpath(p, _ROOT)} 를 보존한다")
        return p

    figs = []
    for c in cells:
        t = "".join(c["source"])
        for line in t.splitlines():
            if line.startswith("<!--pk:figure"):
                meta = json.loads(line[len("<!--pk:figure "):-len("-->")])
                figs.append((meta.get("figure_no"), meta.get("path"), meta.get("caption", "")))

    out = ["<!-- 생성물 — `src/build_part10_results.py:write_paper_doc()` 가 쓴다. -->",
           "<!-- from: 옛 report05_results.ipynb c23(논문 부록) -->",
           "", "# 논문 조각 — V. Results", "",
           "부 10 「검출 결과」 11편(56~66)이 본문이고, 이 문서는 그 편들에서 **논문으로만** 가는 "
           "조각이다.", "",
           "| 편 | 무엇을 대는가 |", "|---|---|",
           "| 56 geometry | 자유공간 배치와 β·앙각·φ 유효창 |",
           "| 57 sensitivity-chain | 밴드 격차의 항별 분해 |",
           "| 58 shared-threshold | 자유공간 형상의 문턱과 공유 SNR90 |",
           "| 59 slope-anchor | 기울기 앵커의 범위와 미통제 항 |",
           "| 60 r90 | 앵커 σ 위의 R90 과 밴드 순서 |",
           "| 61 rank-durability | 순위의 σ 오차 강건성 |",
           "| 62 cpi-sweep | CPI 가 회복하는 커버리지 |",
           "| 63 cpi-residual | CPI 로 못 지우는 모호속도와 그 대가 |",
           "| 64 sigma-free-axis | σ 무관 파형 축 |",
           "| 65 target-model-swap | 표적 모형 세 팔의 요구 추가이득 |",
           "| 66 rx-elements | 다중 수신소자 이득과 상한 |",
           "", "---", "", "## 그림의 논문 캡션 (완결 문장)", "",
           "| Fig. | 파일 | 캡션 |", "|---|---|---|"]
    for n, p, cap in figs:
        out.append(f"| {n} | `{p}` | {cap} |")
    out += ["", "---", "", "## 논문 부록 — 방법 문단 · 방어선 · 인용 (옛 report05 c23)", "",
            "".join(cells[23]["source"]).strip(), ""]

    d = os.path.join(_ROOT, "docs", "paper")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "05_results.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return p


BUILD = [
    ("geometry", r56, [J_FS, J_VF, J_DF, J_PH, J_SG_USED], []),
    ("sensitivity-chain", r57, [J_FS, J_LB, J_SS, J_DV], ["report05_pf1_gap"]),
    ("shared-threshold", r58, [J_FS, J_DV], ["report05_pf6_detector"]),
    ("slope-anchor", r59, [J_AN, J_LFA, J_LFN, J_DV, J_MFX], ["report05_pf7_anchor"]),
    ("r90", r60, [J_FS, J_AN, J_SS, J_DV, J_SV], ["report05_pf2_ranking"]),
    ("rank-durability", r61, [J_SS, J_DV], ["report05_pf3_robust"]),
    ("cpi-sweep", r62, [J_CG], []),
    ("cpi-residual", r63, [J_CG], ["report05_pf4_cpi"]),
    ("sigma-free-axis", r64, [J_RX, J_DV], []),
    ("target-model-swap", r65, [J_TM, J_TA], []),
    ("rx-elements", r66, [J_RX, J_DV], ["report05_pf5_multirx"]),
]


def main() -> int:
    bad = 0
    for anchor, fn, ev, figs in BUILD:
        rep = build_notebook(nb_path(anchor), fn(), strict=True)
        index_shard(anchor, evidence=ev, figures=figs,
                    md_cells=rep["md_cells"], provenance_tags=rep["provenance_tags"],
                    repro=dict(cmd=CMD, out=ev),
                    builder="src/build_part10_results.py")
        bad += 0 if rep["ok"] else 1
    print("논문 조각:", os.path.relpath(write_paper_doc(), _ROOT))
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
