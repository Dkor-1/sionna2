# -*- coding: utf-8 -*-
"""
build_part10_results.py — 부 10 「검출 결과」 편 56~66 을 만든다
==========================================================================================
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py

⭐ 이 파일이 하는 일 — **서술 재배치**다. 계산을 새로 하지 않는다.
   `src/make_report05_results.py` 가 조립하던 노트북 하나(마크다운 25셀)를 **편 11개**로 쪼갠다.
   숫자·출처 태그·그림은 그 빌더에서 그대로 들고 온다 — 파생량은 그 모듈의 `derived()` 를
   **임포트해서** 부르므로 값이 한 자리도 갈리지 않는다.

편성표 — `outputs/restruct_exec_plan.json` (부 10)
------------------------------------------------------------------------------------------
| 편 | 앵커 | 한 문장 | 어디서 왔나 |
|---|---|---|---|
| 56 | `geometry`          | TX·RX·표적 배치와 β·앙각·원거리장이 유효창을 연다 | report05 c2·c3 |
| 57 | `sensitivity-chain` | 세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다 | c4·c5·c6·c7 |
| 58 | `shared-threshold`  | 문턱을 다시 재니 세 밴드가 SNR90 하나를 공유한다 | c8·c9·c10 |
| 59 | `slope-anchor`      | 레벨을 맞추려면 크기전이 법칙을 골라야 하므로 기울기만 받는다 | c11·c12 |
| 60 | `r90`               | 앵커 σ 위의 R90 과 밴드 순서 | c13·c14 |
| 61 | `rank-durability`   | 그 순위는 자세평균이면 σ 오차 아래에서 하나로 모인다 | c15 |
| 62 | `cpi-sweep`         | CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다 | c16·c17 |
| 63 | `cpi-residual`      | 모호속도는 표본화율의 성질이라 CPI 로 바뀌지 않는다 | c18 |
| 64 | `sigma-free-axis`   | σ 를 곱하기 전에 이미 순서를 정하는 축이 있다 | c19 |
| 65 | `target-model-swap` | 표적 모형을 갈아끼우면 요구 이득이 이만큼 달라진다 | c20 |
| 66 | `rx-elements`       | 코히어런트 배열이득은 10log₁₀N 상한에 붙는다 | c21·c22 |

옮기지 않은 셀
    report05 c0·c1  여는 블록 → 각 편의 `header()` 로 흩어졌다(결과 줄·방법 행 단위)
    report05 c23    논문 원고 → `docs/paper/05_results.md` (별도 단계)
    report05 c24    다음 단계 14행 → 아래 `NEXT` 가 편마다 나눠 받는다(한 행도 안 버린다)
    그림 영문 논문 캡션 → `docs/paper/figs_part10.md` (이 파일이 쓴다)

⚠ GPU 도 Sionna 도 필요 없다. `derived()` 가 JSON 에서 파생량을 계산하는 데 1초가 안 걸린다.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_style import (ContractError, build_notebook, caption,       # noqa: E402
                          from_json, header, load_json, md, next_steps,
                          num, table, table_from)

import make_report05_results as R5                                      # noqa: E402

# ── 근거 JSON — 옛 빌더의 이름을 그대로 쓴다(같은 파일을 가리킨다) ──────────────
J_FS, J_SG_USED, J_RX = R5.J_FS, R5.J_SG_USED, R5.J_RX
J_VF, J_LB, J_AN, J_DF = R5.J_VF, R5.J_LB, R5.J_AN, R5.J_DF
J_SS, J_CG, J_DV, J_TM, J_TA = R5.J_SS, R5.J_CG, R5.J_DV, R5.J_TM, R5.J_TA
J_PH, J_SV, J_LFA, J_MFX, J_MFX_ATK = R5.J_PH, R5.J_SV, R5.J_LFA, R5.J_MFX, R5.J_MFX_ATK
J_LFQ = "outputs/lowfreq_anchor.json"

MODES, DRONES, MODE_NAME = R5.MODES, R5.DRONES, R5.MODE_NAME
CELL = R5.CELL
dnum = R5.dnum

PLAN = "outputs/restruct_exec_plan.json"
OUTDIR = os.path.join(_ROOT, "reports")
SHARDDIR = os.path.join(_ROOT, "outputs", "reports_index")
FIG = "../outputs/figures"


# --------------------------------------------------------------------------- #
#  앵커 참조 — 편 사이 링크는 번호가 아니라 **앵커**로 건다
#  ⚠ 정본 해결기는 `src/report_registry.py`(Wire 단계)다. 그 파일이 생기기 전까지
#    계획 JSON 이 정본이다 — 같은 사전에서 읽으므로 번호가 갈리지 않는다.
# --------------------------------------------------------------------------- #
def _registry() -> dict:
    try:
        import report_registry                      # Wire 단계가 만들면 그쪽이 이긴다
        R = getattr(report_registry, "REPORTS", None)
        if isinstance(R, dict) and R:
            return {a: dict(no=str(v["no"]), title=v.get("title") or v.get("title_ko", a))
                    for a, v in R.items()}
    except Exception:                               # noqa: BLE001  (아직 없으면 계획으로)
        pass
    return {r["anchor"]: dict(no=r["no"], title=r["title_ko"])
            for r in load_json(PLAN)["reports"]}


REPORTS = _registry()


def ref(anchor: str, short: str | None = None) -> str:
    """`[편 60 «앵커 σ 위의 R90 …»](60_r90.ipynb)`. 없는 앵커면 빌드가 멈춘다."""
    if anchor not in REPORTS:
        raise ContractError(
            f"없는 앵커다: {anchor!r}\n"
            f"  → 계획({PLAN})의 reports[].anchor 에 있는 이름만 걸 수 있다.")
    r = REPORTS[anchor]
    return f"[편 {r['no']} «{short or r['title']}»]({r['no']}_{anchor}.ipynb)"


def _n(src: str, key: str, fmt: str | None = None, unit: str = "") -> str:
    return num(None, (src, key), fmt, unit)


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


# --------------------------------------------------------------------------- #
#  그림의 **논문 캡션** — 리포트 본문에서 빠지되 지워지지 않는다
# --------------------------------------------------------------------------- #
PAPER_CAPS = [
    ("57", "sensitivity-chain", 1, "report05_pf1_gap",
     "Per-band cost decomposition on one target and one geometry: only the wavelength "
     "term and the target cross section differ between the three illuminators, and the "
     "cross-section difference dominates 9 of 15 band pairs."),
    ("58", "shared-threshold", 1, "report05_pf6_detector",
     "Detection curves for the three always-on reference signals at an empirically "
     "calibrated false-alarm rate, and the sensitivity cost of restricting a receiver "
     "to always-on references."),
    ("59", "slope-anchor", 1, "report05_pf7_anchor",
     "The slope anchor applies one scalar per band and airframe, and the resulting band "
     "spread is compared with the size-transfer term the anchor leaves open."),
    ("60", "r90", 1, "report05_pf2_ranking",
     "Three-waveform comparison normalised per airframe: five airframes give three "
     "different orders at a single aspect and one common order on aspect-averaged, "
     "slope-anchored cross sections."),
    ("61", "rank-durability", 1, "report05_pf3_robust",
     "Ranking robustness: a common-mode cross-section error preserves the order at every "
     "offset within 10 dB and moves only the absolute range, while a per-band "
     "differential error reorders the waveforms above an airframe-specific threshold."),
    ("63", "cpi-residual", 1, "report05_pf4_cpi",
     "The 5G always-on-reference penalty as a CPI sweep: the blind-heading fraction falls "
     "with CPI under both guard conventions, and the CPI needed for parity with LTE or "
     "WiFi is bounded by the coherent-integration limit of the moving target."),
    ("66", "rx-elements", 1, "report05_pf5_multirx",
     "Multi-receiver gain measured against the idealised coherent bound of 10 log10 N, "
     "which holds for thermal noise alone under perfect steering; the measured excess "
     "comes from the N-independent cancellation residual."),
]


def write_paper_figs() -> str:
    L = ["# 논문 조각 — 부 10 그림 캡션", "",
         "리포트 본문은 그림마다 **질문 캡션** 한 줄을 단다(하우스 규약). 논문에 그대로 붙일 ",
         "**완결 문장 캡션**은 본문에서 빠지므로 여기 모은다 — 출처는 옛 "
         "`src/make_report05_results.py` 의 `figure_md(paper_caption=…)` 다.", ""]
    for no, anchor, k, stem, cap in PAPER_CAPS:
        L += [f"<!-- from: 편 {no} {anchor} · 그림 {k} · outputs/figures/{stem}.png -->",
              f"**Fig. ({no}-{k})** {cap}", ""]
    p = os.path.join(_ROOT, "docs", "paper", "figs_part10.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return p


# --------------------------------------------------------------------------- #
#  재현 명령 — 옛 여는 블록의 bash 를 편마다 필요한 줄만 갖고 온다
# --------------------------------------------------------------------------- #
CMD_SIGMA = "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py"
CMD_RANGE = ("for D in mini5pro mavic4pro matrice4e phantom4 s1000plus; do "
             "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_range.py "
             "--stage all --mode W1,L1,G1 --drone $D; done")
CMD_VF = ("PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_freespace.py")
CMD_DEF = ("PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
           "benchmark/verify_sbr_defect_fixes.py")
CMD_LB = ("PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_linkbudget.py")
CMD_DET = "PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_detection.py"
CMD_SS = ("PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/sigma_sensitivity.py")
CMD_CG = ("PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/cpi_guard_sweep.py")
CMD_AN = "PYTHONPATH=src ~/.venvs/py312/bin/python src/sigma_anchor.py"
CMD_PH = ("PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/phi_sweep.py")
CMD_TM = "PYTHONPATH=src ~/.venvs/py312/bin/python scratchpad/tm_result.py"
CMD_NB = "PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py"


# --------------------------------------------------------------------------- #
#  편 하나 = 함수 하나. 각 함수는 (번호, 앵커, 블록목록) 을 돌려준다.
# --------------------------------------------------------------------------- #
def r56_geometry(D, S):
    FS, PH = S["FS"], S["PH"]
    return "56", "geometry", [
        header(
            num=56,
            title="TX·RX·표적 배치와 β·앙각·원거리장이 유효창을 연다",
            did="조명원과 패시브 수신기를 지상에 고정하고 표적을 그 중점 위 공중에 두어, "
                "이 부의 모든 수치가 성립하는 β·앙각·방위 창을 수치로 고정했다.",
            results=[
                f"헤드라인 거리의 바이스태틱 각은 "
                f"{dnum(D['beta_at_R'], '{:.2f}', '°', f'{J_FS} : solve.W1.beta_deg', 'R90 에서 보간')}"
                f" 로 준모노스태틱이고, σ 는 이등분선 방향의 모노스태틱 값을 쓴다.",

                f"상반성 rms 잔차는 β ≤ 45° 에서 "
                f"{dnum(D['recip_in'], '{:.2f}', 'dB', f'{J_DF} : d2_reciprocity_drone.rows', 'β≤45 행 최대')}"
                f", β 60~90° 에서 "
                f"{dnum(D['recip_out'], '{:.2f}', 'dB', f'{J_DF} : d2_reciprocity_drone.rows', 'β>45 행 최대')}"
                f" 다 — 그래서 창을 β ≤ 45° 로 방법 조건에 박는다.",

                f"σ 격자의 앙각 하한은 "
                f"{dnum(D['el_grid_min'], '{:.0f}', '°', f'{J_SG_USED} : meta.el_deg', '최솟값')}"
                f"(격자 행 "
                f"{dnum(D['n_el'], '{:.0f}', '개', f'{J_SG_USED} : meta.el_deg', '길이')}"
                f") 이고, 그 앙각에 닿는 수평거리는 "
                f"{dnum(D['d_el20'], '{:.0f}', 'm', f'{J_FS} : solve.W1.el_look_deg', 'el=−20° 보간')}"
                f" 다.",

                f"장면 방위 {PH.num('meta.n_phi', None, '{:.0f}')}방위 전수 스윕에서 σ 를 고정한 "
                f"순수기하의 R90 span 은 "
                f"{PH.num('verdict.claims[2].range_over_phi.constant_sigma_control.W1.span_pct_of_phi90', None, '{:.2f}', '%')}"
                f" 이고, 이 부가 쓰는 φ=90° 는 그 스윕의 보수적인 끝이다.",
            ],
            method=[
                ("좌표", "`src/freespace_scene.py:72` 의 상수 하나, 기하 함수는 "
                        "`src/freespace_scene.py:117`"),
                ("β 창", "PEC 이면각 상반성 잔차를 β 행마다 재고, 잔차가 뛰는 자리를 창의 "
                        "경계로 삼았다 — `benchmark/verify_sbr_defect_fixes.py`"),
                ("σ 조회", "발표된 solve 가 읽은 σ 격자를 아카이브에서 그대로 인용한다 — "
                          "그 신원은 φ 스윕이 기록한 생성시각과 일치로 확정된다"),
                ("원거리장", "파면이 평면으로 보일 만큼 먼 거리를 유효 게이트로 두고, "
                            "게이트를 통과한 칸에서만 해를 찾는다"),
            ],
            repro=dict(cmd=[CMD_SIGMA, CMD_RANGE, CMD_DEF, CMD_PH, CMD_NB],
                       out=[J_FS, J_DF, J_PH, J_SG_USED],
                       runtime="σ 격자 워커 CPU "
                               + _n(J_DV, "runtime.sigma_grid_s", "{:.0f}", "s")
                               + " · 기종당 "
                               + _n(J_DV, "runtime.range_per_drone_s", "{:.0f}", "s")),
        ),

        md("## 기하 — TX · RX · 표적을 어디에 두었나", "",
           "조명원(TX)과 패시브 수신기(RX)를 지상에 고정하고, 표적을 두 점의 중점에서 수평거리 "
           "`d` 만큼 떨어진 공중에 둔다. 좌표 상수 `src/freespace_scene.py:72`, "
           "기하 함수 `src/freespace_scene.py:117`.",
           "",
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
           f"헤드라인 거리에서 β = "
           f"{dnum(D['beta_at_R'], '{:.2f}', '°', f'{J_FS} : solve.W1.beta_deg', 'R90 에서 보간')} "
           "로 준모노스태틱이고, σ 는 이등분선 방향의 모노스태틱 값을 쓴다"
           "(`src/experiment_freespace_sigma.py:227`). 아래 창이 이 부의 **방법 조건**이다.",
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
                   + dnum(D["d_el20"], "{:.0f}", "m", f"{J_FS} : solve.W1.el_look_deg",
                          "el=−20° 보간") + ")",
                   "격자 앙각 행 "
                   + dnum(D["n_el"], "{:.0f}", "개", f"{J_SG_USED} : meta.el_deg", "길이")
                   + ", 헤드라인 거리의 el = "
                   + _n(J_FS, "meta.ranges_el_look_deg", "{:.2f}", "°")],
                  ["β = 45° 지점",
                   "`d` = " + dnum(D["d_beta45"], "{:.0f}", "m", f"{J_FS} : solve.W1.beta_deg",
                                   "β=45° 보간"),
                   "그 지점의 SNR = "
                   + dnum(D["snr_at_beta45"], "{:.0f}", "dB", f"{J_FS} : solve.W1.snr_d_db",
                          "d=β45 에서 보간")],
                  ["장면 방위 φ",
                   PH.num("meta.n_phi", None, "{:.0f}") + "방위 전수 — 5° 간격의 전 원주",
                   "σ 를 고정한 순수기하에서 R90 span "
                   + PH.num("verdict.claims[2].range_over_phi.constant_sigma_control.W1"
                            ".span_pct_of_phi90", None, "{:.2f}", "%")
                   + " · 자세평균 "
                   + PH.num("verdict.claims[2].range_over_phi.aspect_averaged.W1"
                            ".span_pct_of_phi90", None, "{:.2f}", "%")
                   + " · 세 팔 모두 φ=90° 가 "
                   + PH.num("verdict.claims[2].range_over_phi.constant_sigma_control.W1"
                            ".phi90_is", None)
                   + " 이라 이 부의 φ 는 보수적인 끝이다"]])),

        md(f"같은 스윕이 σ 조회의 앙각도 잰다 — 스윕이 읽은 격자"
           f"(생성 {PH.num('meta.sigma_file_generated', None)}, 앙각 0~−20°)에서 조회의 "
           f"{PH.num('geometry.rows[18].frac_el_outside_sigma_grid', None, '{:.1%}')}(φ=90°) ~ "
           f"{PH.num('geometry.rows[0].frac_el_outside_sigma_grid', None, '{:.1%}')}(φ=0°) 가 "
           f"경계 행으로 클램프됐다 — 격자 밖 값을 가장자리 값으로 눌러 붙였다는 뜻이다. "
           f"근거리 SNR 천장이 그 조회 위에 서므로, 확장된 앙각 격자 위에서 다시 푸는 일을 "
           f"다음 단계에 건다."),

        next_steps([
            ("앙각을 확장한 σ 격자 위에서 R90 과 SNR 천장을 다시 푼다",
             "φ 축에서 "
             + S["PH"].num("geometry.rows[18].frac_el_outside_sigma_grid", None, "{:.1%}")
             + " ~ "
             + S["PH"].num("geometry.rows[0].frac_el_outside_sigma_grid", None, "{:.1%}")
             + " 이던 클램프 조회가 격자 안으로 들어오고, 근거리 SNR 천장이 격자 위에 선다",
             "`src/experiment_freespace_sigma.py` 의 el 축 → "
             "`src/experiment_freespace_range.py --stage solve`"),
            ("β > 45° 의 출사 가시성·대칭화 잔차를 다시 잰다",
             "바이스태틱 유효창의 폭이 확정된다",
             "`benchmark/verify_sbr_defect_fixes.py` → " + ref("bistatic-exit", "수신 방향 그림자")),
        ]),
    ]


def r57_sensitivity_chain(D, S):
    FS, SS, DV = S["FS"], S["SS"], S["DV"]

    def B(m, k, f="{:+.2f}"):
        return f.format(D["budget"][m][k])

    SRC_A = f"출처 ⟨{J_AN} : drones.*.modes.slope_only.delta_db⟩"
    SRC_B = f"출처 ⟨{J_FS} : " + CELL.format(d="mavic4pro", m="*") + ".budget_terms_db⟩"

    return "57", "sensitivity-chain", [
        header(
            num=57,
            title="세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다",
            did="d = 1 km 한 점에서 세 조명원의 출력 SNR 을 항별로 분해하고, "
                "밴드 쌍의 격차를 그 항으로 쪼갰다.",
            results=[
                f"WiFi−LTE 격차 "
                f"{DV.num('gap_1km.by_pair.W1-L1.d_total', None, '{:+.2f}', 'dB')} 는 λ² 항 "
                f"{DV.num('gap_1km.by_pair.W1-L1.d_lambda2', None, '{:+.2f}', 'dB')} 와 σ 항 "
                f"{DV.num('gap_1km.by_pair.W1-L1.d_sigma', None, '{:+.2f}', 'dB')} 의 합이다.",

                f"공통항(EIRP·수신이득·확산·1/N₀·CPI·듀티·손실)은 세 밴드가 같은 값 "
                f"{DV.num('gap_1km.by_mode.W1.common', None, '{:+.2f}', 'dB')} 를 쓴다 — "
                f"밴드 쌍의 공통항 차는 "
                f"{DV.num('gap_1km.by_pair.W1-L1.d_common', None, '{:+.2f}', 'dB')} 다.",

                f"5기체 × 3쌍 15칸 중 σ 항이 λ² 항보다 큰 칸은 "
                f"{SS.num('gap_decomposition.n_pairs_sigma_dominates', None, '{:.0f}')}칸이고, "
                f"σ-무관 축의 격차는 λ² 스프레드로 고정이다.",

                f"헤드라인 칸을 구속하는 벽은 직접파 잔차이고"
                f"({FS.num('solve.W1.limit', None)}), 레이더 방정식 항등식 검사는 코드 경로와 "
                f"dB 산술의 차이를 "
                f"{dnum(D['lb_resid'], '{:.1e}', 'dB', f'{J_LB} : A_radar_equation.rows', '|d_echo_dbarith_db| 최대')}"
                f" 로 잡는다.",

                f"기준신호가 CPI 를 다 채운다는 규약을 풀면 듀티 항이 살아난다 — 5G 는 LTE 대비 "
                f"{SS.num('unapplied_duty_axis.pair_gaps_db.L1-G1', None, '{:.2f}', 'dB')} 를 "
                f"더 치른다.",
            ],
            method=[
                ("동작점", "d = 1 km · Mavic 4 Pro · 수신소자 1개. 점유 규약은 "
                          + FS.num("meta.link_budget.power_normalization.canonical_occupancy",
                                   None) + " 다"),
                ("σ 항", "기울기 앵커의 밴드별 Δσ 를 우리 PO 출력 위에 더한 값 — 앵커의 범위는 "
                        + ref("anchor-mode", "앵커가 받는 축") + " 이 든다"),
                ("항등식 검사", "파형 3종 × 기체 2종에서 코드 경로와 dB 산술을 맞대 본다 — "
                              "`benchmark/verify_linkbudget.py`"),
                ("듀티 축", "R90 경로에서 호출되지 않는 항이라 크기만 따로 싣는다 — "
                          "그 항을 켠 설정의 순위는 " + ref("rank-durability", "순위 강건성")
                          + " 이 든다"),
            ],
            repro=dict(cmd=[CMD_RANGE, CMD_LB, CMD_SS, CMD_AN, CMD_NB],
                       out=[J_FS, J_LB, J_SS, J_AN, J_DV],
                       runtime="링크버짓 선언 예산 "
                               + _n(J_DV, "runtime.declared_s", "{:.0f}", "s")
                               + " · σ 민감도 "
                               + _n(J_DV, "runtime.sigma_sensitivity_s", "{:.1f}", "s")),
            prereq=[(ref("anchor-mode", "앵커가 받는 축"),
                     "A(f) 기울기는 측정에서, 레벨과 자세 패턴은 우리 계산에서 온다"),
                    (ref("cost-ledger", "조명원 dB 원장"),
                     "점유 · λ² · 듀티 · PRF 의 항별 크기")],
        ),

        md("## 감도사슬 — 밴드 격차를 항으로 분해한다", "",
           f"d = 1 km · Mavic 4 Pro · 수신소자 1개. 점유 규약은 "
           f"{FS.num('meta.link_budget.power_normalization.canonical_occupancy', None)}"
           "(자원요소 RE 하나당 같은 전력)이고, σ 항은 기울기 앵커의 밴드별 Δσ 를 더한 값이다. "
           "**세 밴드에서 값이 다른 항은 λ² 와 σ 둘뿐이다** — 나머지는 세 밴드가 같은 값을 쓴다.",
           "",
           table(["항", "WiFi", "LTE", "5G"],
                 [[nm] + [B(m, k) for m in MODES] for nm, k in
                  [("공통항 합 (EIRP·수신이득·확산·1/N₀·CPI·듀티·손실)", "common"),
                   ("$\\lambda^2$", "lambda2"),
                   ("$\\sigma$ (기울기 앵커, 공칭 헤딩)", "sigma_anch"),
                   ("**출력 SNR**", "total_anch")]]),
           "", SRC_B, SRC_A),

        md("밴드 쌍의 격차를 그 두 항으로 쪼갠다. λ² 는 정의로 정확하고, σ 는 자세 로브 구조"
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
           f"{SS.num('gap_decomposition.axes_pair_gaps_db.L1-G1', None, '{:+.2f}', 'dB')} 로 "
           f"고정이다."),

        md(*_fig(1, "report05_pf1_gap", "밴드 격차를 만드는 항은 λ² 와 σ 중 무엇인가?")),

        md("## 어느 벽이 거리를 정하나", "",
           f"헤드라인 칸을 구속하는 것은 직접파 잔차다({FS.num('solve.W1.limit', None)}). "
           "ECA 억압 깊이를 바꾸면 거리가 이렇게 움직인다.",
           "",
           table(["ECA 깊이"] + [f"{k} dB" if k != "inf" else "완전 억압"
                                for k in ("40", "60", "90", "inf")],
                 [["R90"] + [_n(J_FS, f"solve.W1.sensitivity_eca_depth.{k}.R_m", "{:.0f}", "m")
                             for k in ("40", "60", "90", "inf")]]),
           "",
           f"레이더 방정식 항등식 검사는 파형 3종 × 기체 2종 "
           f"{dnum(D['lb_rows'], '{:.0f}', '행', f'{J_LB} : A_radar_equation.rows', '길이')}"
           f" 에서 코드 경로와 dB 산술의 차이를 "
           f"{dnum(D['lb_resid'], '{:.1e}', 'dB', f'{J_LB} : A_radar_equation.rows', '|d_echo_dbarith_db| 최대')}"
           f" 로 잡는다."),

        md("## 듀티 축의 크기", "",
           "위 사슬은 기준신호가 CPI 전체를 채운다는 규약에서 풀린다. 실제 점유가 만드는 듀티 "
           "항은 밴드마다 다르고, 그 크기를 여기 적는다 — 이 항을 켠 설정의 순위는 "
           + ref("rank-durability", "순위 강건성") + " 이 든다.",
           "",
           table(["모드", "기준신호 길이 T_ref", "프레임 M", "듀티 항"],
                 [[MODE_NAME[m],
                   SS.num(f"unapplied_duty_axis.by_mode.{m}.T_ref_s", None, "{:.2e}", "s"),
                   SS.num(f"unapplied_duty_axis.by_mode.{m}.M", None, "{:.0f}"),
                   SS.num(f"unapplied_duty_axis.by_mode.{m}.duty_db", None, "{:+.2f}", "dB")]
                  for m in MODES]),
           "",
           f"이 항을 넣으면 5G 는 LTE 대비 "
           f"{SS.num('unapplied_duty_axis.pair_gaps_db.L1-G1', None, '{:.2f}', 'dB')} 를 더 "
           f"치른다. 같은 값이 집안의 다른 산출물에도 있다 — WiFi 의 "
           f"{SS.num('unapplied_duty_axis.duty_db.W1', None, '{:.2f}', 'dB')} 는 "
           "`outputs/report4_fixups.json : packet_duty_db` 와 일치한다."),

        next_steps([
            ("듀티 항을 R90 경로에 켜고 세 밴드를 다시 푼다",
             "위 표의 "
             + SS.num("unapplied_duty_axis.duty_db.G1", None, "{:.2f}", "dB")
             + " 가 순위에 주는 영향이 확정되고, 거리표의 듀티 행이 실측값이 된다",
             "`src/freespace_link.py` 의 duty_db_from_cpi → " + ref("r90", "R90 표")),
        ]),
    ]


def r58_shared_threshold(D, S):
    FS, DV = S["FS"], S["DV"]
    return "58", "shared-threshold", [
        header(
            num=58,
            title="자유공간 형상에서 문턱을 다시 재니 세 밴드가 SNR90 하나를 공유한다",
            did="자유공간 형상에서 경험 오경보율을 목표값에 고정해 문턱을 다시 잡고, "
                "그 문턱 하나를 세 밴드 solve 가 공유할 때의 대가를 수치로 냈다.",
            results=[
                f"세 밴드의 solve 는 WiFi 에서 잰 문턱 SNR90 = "
                f"{DV.num('threshold.snr90_shared_db', None, '{:.2f}', 'dB')} 하나를 공유한다.",

                f"LTE 가 자기 문턱을 쓰면 "
                f"{DV.num('threshold.l1_own_snr90_db', None, '{:.2f}', 'dB')} 로 "
                f"{DV.num('threshold.l1_delta_db', None, '{:+.3f}', 'dB')} 어긋나고, R90 은 "
                f"{DV.num('threshold.l1_range_shift_pct', None, '{:+.2f}', '%')} 움직인다.",

                f"5G 의 요구 명목 Pfa 는 경험값의 "
                f"{dnum(D['pfa_g1_ratio'], '{:.0f}', '배', f'{J_FS} : threshold.pfa.G1.ratio_emp_over_nominal', '역수')}"
                f" 다 — 프레임 {FS.num('waveforms.G1.M', 5, '{:.0f}')}개짜리 도플러 축이 그만큼 "
                f"좁다.",

                f"5G 의 dopoff 격자 "
                f"{DV.num('threshold.g1_total_cells', None, '{:.0f}')}칸은 M="
                f"{DV.num('threshold.g1_M', None, '{:.0f}')} 의 도플러 축 밖에 떨어져 자기 "
                f"문턱을 못 세운다 — 그 행을 다음 단계로 넘긴다.",
            ],
            method=[
                ("문턱", "자유공간 형상에서 경험 Pfa 를 목표 "
                        + FS.num("threshold.pfa.W1.target", 1e-4, "{:.0e}")
                        + " 에 고정하고 그때 요구되는 명목 Pfa 를 기록한다 — "
                          "`src/freespace_detect.py:711`"),
                ("형상 의존", "거리창·오버샘플·가드 규약이 챔버와 다르므로 형상마다 다시 잰다 — "
                            "챔버 형상의 배율은 " + ref("cfar-calib", "경험 Pfa 교정") + " 이 든다"),
                ("공유", "stage_threshold 는 모드 목록의 첫 모드에서 SNR90 을 뽑아 세 밴드 "
                        "solve 전부에 넘긴다 — `src/experiment_freespace_range.py:856`"),
            ],
            repro=dict(cmd=[CMD_RANGE, CMD_VF, CMD_NB],
                       out=[J_FS, J_VF, J_DV],
                       runtime="기하·규약 게이트 "
                               + _n(J_DV, "runtime.verify_freespace_s", "{:.2f}", "s")),
            prereq=[(ref("cfar-calib", "경험 Pfa 교정"),
                     "명목 Pfa 를 경험 Pfa 로 교정하는 절차와 그 배율이 형상마다 다른 이유")],
        ),

        md("## 세 파형 벤치마크 — 문턱을 경험 Pfa 로 교정한다", "",
           "세 조명원은 각 표준이 늘 켜 두는 기준신호다 — WiFi VHT-LTF(W1) · LTE CRS(L1) · "
           "5G SSB(G1). 제원은 " + ref("illuminators", "상시 기준신호") + " 가 들고, "
           "여기서는 그 셋을 같은 검출기에 물린다.",
           "",
           f"경험 Pfa 를 목표 {FS.num('threshold.pfa.W1.target', 1e-4, '{:.0e}')} 에 고정하고, "
           "그때 요구되는 명목 Pfa 를 기록한다(`src/freespace_detect.py:711`). 자유공간 형상은 "
           "거리창 · 오버샘플 · 가드 규약이 챔버와 다르므로 형상마다 다시 잰다.",
           "",
           table(["모드", "요구 명목 Pfa", "경험 Pfa", "경험/명목"],
                 [[MODE_NAME[m], _n(J_FS, f"threshold.pfa.{m}.nominal", "{:.2e}"),
                   _n(J_FS, f"threshold.pfa.{m}.empirical", "{:.2e}"),
                   _n(J_FS, f"threshold.pfa.{m}.ratio_emp_over_nominal", "{:.3f}")]
                  for m in MODES]),
           "",
           f"5G 의 요구 명목 Pfa 는 경험값의 "
           f"{dnum(D['pfa_g1_ratio'], '{:.0f}', '배', f'{J_FS} : threshold.pfa.G1.ratio_emp_over_nominal', '역수')}"
           f" 다 — 프레임 {FS.num('waveforms.G1.M', 5, '{:.0f}')}개짜리 도플러 축이 그만큼 좁다."),

        md(f"세 밴드의 solve 는 이 중 W1 에서 잰 문턱 SNR90 = "
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
                   "—", "— (다음 단계 1행)"]])),

        md(*_fig(1, "report05_pf6_detector",
                 "교정된 오경보율 위에서 세 파형이 요구하는 SNR 은 몇 dB 인가?")),

        next_steps([
            ("5G 의 dopoff 격자를 M 인식으로 고쳐 Pd=0.9 문턱을 직접 잰다",
             "5G 의 R90 이 자기 문턱 위에 서고, 세 밴드가 문턱을 공유하는 위 표의 행이 닫힌다",
             "`src/experiment_freespace_range.py:856` → " + ref("r90", "R90 표")),
        ]),
    ]


def r59_slope_anchor(D, S):
    AN, DV = S["AN"], S["DV"]
    return "59", "slope-anchor", [
        header(
            num=59,
            title="레벨을 맞추려면 크기전이 법칙을 골라야 하므로 기울기만 받는다",
            did="σ = A(f)·B₁(φ,θ) 에서 A(f) 의 주파수 기울기만 측정에 맞추고, 레벨과 자세 "
                "패턴은 우리 PO 출력으로 둔 원장 위에 밴드 비교를 세웠다.",
            results=[
                f"생산 모드 `slope_only` 의 세 밴드 평균 레벨이동은 "
                f"{DV.num('anchor_scope.level_shift_abs_max_db', None, '{:.2f}', 'dB')} 다 — "
                f"레벨은 우리 PO 출력 그대로다.",

                f"레벨까지 맞추려면 크기전이 법칙을 하나 골라야 하고, L² 와 L⁴ 가 기체에 따라 "
                f"최대 "
                f"{DV.num('anchor_scope.size_law_spread_max_db', None, '{:.2f}', 'dB')} 갈린다 "
                f"— 측정이 그 대가 없이 제약하는 양이 기울기뿐이라 기울기만 받는다.",

                f"재보정은 밴드별 스칼라 Δσ 하나씩이고, 정규화 각도 패턴은 "
                f"{AN.num('drones.phantom4.shape_invariance_max_abs_db', None, '{:.1e}', 'dB')} "
                f"안에서 그대로 남는다.",

                f"앵커가 통제한 것 밖의 항은 셋이다 — 규약 불확도 "
                f"{_n(J_AN, 'uncontrolled[1].size_db', '{:.2f}', 'dB')}, 크기전이 항, 그리고 "
                f"PO 유효성 항이다.",

                f"PO 오차가 1 dB 아래로 내려가려면 부품 폭이 파장의 "
                f"{_n(J_LFQ, 'thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam', '{:.3f}')}"
                f" 배 이상이어야 하는데, 우리 세 밴드는 전부 그 문턱 아래에 부품을 남긴다.",
            ],
            method=[
                ("앵커", "Das 측정(IEEE WCL 2026 15:3731)의 주파수 기울기 하나를 받는다 — "
                        "생산 모드는 `slope_only`"),
                ("우리 몫", "절대 레벨 A(f)|_mean 과 자세 패턴 B₁(φ,θ) 는 우리 PO 출력이다"),
                ("미통제 항", "규약 불확도 · 크기전이 · PO 유효성 셋을 원장에 크기와 함께 남긴다 — "
                            "그 셋의 상세는 " + ref("anchor-ledger", "앵커 원장") + " 이 든다"),
                ("편파", "우리 적분은 전기장의 흔들리는 방향을 가르지 않고 세기 하나를 낸다 — "
                        "그래서 PO 유효성 항의 부호를 이 부에서 정하지 않는다"),
            ],
            repro=dict(cmd=[CMD_AN, CMD_NB], out=[J_AN, J_DV, J_LFQ],
                       runtime="앵커 재보정 약 20 초 (CPU)"),
            prereq=[(ref("po-knee", "PO 유효 무릎"),
                     "부품 폭이 파장의 몇 배부터 PO 오차가 1 dB 안에 드는가"),
                    (ref("anchor-mode", "앵커가 받는 축"),
                     "σ 의 어느 축을 측정에서 받고 어느 축이 우리 계산인가")],
        ),

        md("## 밴드 비교의 바닥 — 기울기 앵커 σ", "",
           "σ = A(f)·B₁(φ,θ) 에서 **A(f) 의 기울기**를 Das 측정(IEEE WCL 2026 15:3731)에 맞춘다. "
           "**절대 레벨은 우리 PO 출력**이고, 생산 모드 `slope_only` 의 세 밴드 평균 레벨이동은 "
           + DV.num("anchor_scope.level_shift_abs_max_db", None, "{:.2f}", "dB")
           + " 다. 레벨까지 맞추려면 크기전이 법칙을 골라야 하고 L² 와 L⁴ 가 최대 "
           + DV.num("anchor_scope.size_law_spread_max_db", None, "{:.2f}", "dB")
           + " 갈리므로, 측정이 그 대가 없이 제약하는 기울기만 받는다."),

        md(f"재보정은 밴드별 스칼라(방향 구분 없이 값 하나) Δσ 하나씩이고, 정규화 각도 패턴은 "
           f"{AN.num('drones.phantom4.shape_invariance_max_abs_db', None, '{:.1e}', 'dB')} "
           "안에서 그대로 남는다. 앵커가 통제한 것 밖의 항은 **셋**이다 — 규약 불확도 "
           + _n(J_AN, "uncontrolled[1].size_db", "{:.2f}", "dB")
           + ", 크기전이 항, 그리고 **PO 유효성 항**이다"
           + f"(⟨{J_AN} : uncontrolled⟩). 세 번째가 크기를 얻었다 — PO 오차가 1 dB 아래로 "
           + "내려가려면 부품의 폭이 파장의 "
           + _n(J_LFQ, "thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam", "{:.3f}")
           + " 배 이상이어야 하는데, 우리 세 밴드는 전부 그 문턱 아래에 부품을 남긴다("
           + ref("po-knee", "PO 유효 무릎") + ")."),

        md("그 항의 **부호는 이 부에서 정하지 않는다** — 우리 적분이 편파(전파의 전기장이 흔들리는 "
           "방향)를 가르지 않기 때문이다"
           + f"(⟨{J_LFA} : q5_blast_radius.po_validity_blast_radius_the_real_one⟩). "
           + "참값은 두 편파에서 서로 다른 값을 주는데 우리 커널은 그 둘을 구분 없이 하나로 내므로, "
           + "한쪽 편파를 기준으로 보면 낮고 다른 쪽을 기준으로 보면 높다. 두 쪽 중 어느 쪽이 더 "
           + "그럴듯한지는 " + ref("kernel-open-items", "커널의 열린 항목") + " 이 두 편파의 크기 "
           + "차이로 적는다 — 이 편은 그 개연성을 결과에 넣지 않고 순위만 든다. 이 사실은 원장에 "
           + "「VV 측정 대 무편파 커널」 로 기록되어 있다.",
           "",
           f"⚠ 이 절이 든 앵커 수(정규화 잔차 · 아래 Δσ 표)와 거리표는 `{J_AN}` 에서 오고, 그 "
           f"사슬은 {S['MFX'].num('_meta.date', None)} 형상 정정 전 메쉬 위에 서 있다 — 다섯 기체 "
           f"중 Matrice 4E 가 그 정정을 받았다(" + ref("mesh-vs-real", "형상 정정")
           + f") ⟨{J_MFX_ATK} : Q6_invalidated_outputs.critical[3]⟩."),

        md(table_from(f"{J_AN}:drones",
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

        md(*_fig(1, "report05_pf7_anchor",
                 "앵커가 옮긴 밴드 격차는 앵커 자신의 미통제 항보다 큰가?")),

        next_steps([
            ("기준 구를 함께 재서 자체 앵커를 세운다",
             "지금 우리 PO 출력인 σ 절대 레벨이 측정에 앵커되고, 크기전이 항 "
             + DV.num("anchor_scope.size_law_spread_max_db", None, "{:.2f}", "dB") + " 가 닫힌다",
             ref("calibration-sphere", "교정 기준체")),
            ("VV/HH 2편파를 잰다", "앵커의 편파 항 크기가 수치로 확정된다",
             ref("sigma-checklist", "세션 체크리스트")),
        ]),
    ]


def r60_r90(D, S):
    AN, SS, DV = S["AN"], S["SS"], S["DV"]
    SRC_R = f"출처 ⟨{J_FS} : " + CELL.format(d="*", m="*") + ".R90_C50_m⟩"
    SRC_A = f"출처 ⟨{J_AN} : drones.*.modes.slope_only.delta_db⟩"
    return "60", "r90", [
        header(
            num=60,
            title="앵커 σ 위의 R90 은 3.69~11.10 km 이고, 밴드 순서는 기체마다 바뀐다",
            did="기울기 앵커의 Δσ 를 R90 근방 국소 지수로 옮겨 다섯 기체 × 세 밴드의 검출거리를 "
                "내고, 그 순서가 인용 방식에 따라 어떻게 갈리는지를 한 표에 놓았다.",
            results=[
                f"다섯 기체 × 세 밴드 15칸의 R90 은 "
                f"{DV.num('r90.span_comparable_min_km', None, '{:.2f}', 'km')} ~ "
                f"{DV.num('r90.excluded_max_km', None, '{:.2f}', 'km')} 이고, 위 끝은 앵커 "
                f"비교가능성이 `{DV.num('r90.excluded[0]', None)}` 인 기체가 갖는다 — 앵커 "
                f"비교가능 "
                f"{DV.num('r90.n_cells_comparable', None, '{:.0f}')}칸만 보면 "
                f"{DV.num('r90.span_comparable_min_km', None, '{:.2f}', 'km')} ~ "
                f"{DV.num('r90.span_comparable_max_km', None, '{:.2f}', 'km')} 다.",

                f"국소 지수는 "
                f"{dnum(D['n_local'], '{:.2f}', '', f'{J_FS} : ' + CELL.format(d='*', m='*') + '.n_local_at_R90', '15칸 평균')}"
                f" 이고, `d` 축에서 국소적으로 R ∝ σ^(1/n) 이다.",

                f"단일 자세 ψ=0 에서는 다섯 기체가 "
                f"{SS.num('configurations.by_config.as_published.n_distinct_orders', None, '{:.0f}')}"
                f"가지 순위를 내고, 자세를 평균하면 "
                f"{DV.num('ranking.consensus_order_aspect_avg', None)} 한 순위로 모인다.",

                f"공통모드 σ 오차 ±10 dB 가 이 열 전체를 "
                f"{SS.num('common_mode.abs_range_shift_at_10db_pct.minus10', None, '{:+.1f}', '%')}"
                f" ~ "
                f"{SS.num('common_mode.abs_range_shift_at_10db_pct.plus10', None, '{:+.1f}', '%')}"
                f" 옮긴다 — 그래서 km 열은 순위를 읽는 표로 쓴다.",
            ],
            method=[
                ("R90 정의", "공칭 헤딩 ψ=0 의 σ 로 SNR(d) 를 만들고, 유효 게이트를 통과한 칸에서 "
                            "교정 문턱과의 최외곽 하강교차를 찾는다 — `src/freespace_link.py:448`"),
                ("Δσ 전이", "밴드별 스칼라 Δσ 를 R90 근방 국소 지수로 1차 전이한다 — "
                          "`src/freespace_scene.py:56`"),
                ("헤드라인 폭", "앵커 비교가능성 판정이 `not_comparable` 인 기체를 폭에서 뺀다 — "
                              "그 판정의 원장은 " + ref("anchor-ledger", "앵커 원장") + " 이 든다"),
                ("봉투", "km 열은 공통모드 민감도 봉투와 함께 읽는다 — 그 봉투는 "
                        + ref("rank-durability", "순위 강건성") + " 이 든다"),
            ],
            repro=dict(cmd=[CMD_SIGMA, CMD_RANGE, CMD_AN, CMD_SS, CMD_NB],
                       out=[J_FS, J_AN, J_SS, J_DV],
                       runtime="기종당 "
                               + _n(J_DV, "runtime.range_per_drone_s", "{:.0f}", "s")
                               + " × "
                               + _n(J_DV, "runtime.n_drones", "{:.0f}") + "기종"),
            prereq=[(ref("shared-threshold", "공유 문턱"),
                     "세 밴드가 하나의 교정 문턱 위에서 풀린다는 것"),
                    (ref("slope-anchor", "기울기 앵커"),
                     "Δσ 가 무엇을 옮기고 무엇을 남기는가")],
        ),

        md("## 기울기 앵커 σ 위의 R90", "",
           f"Δσ 를 R90 근방 국소 지수 "
           f"{dnum(D['n_local'], '{:.2f}', '', f'{J_FS} : ' + CELL.format(d='*', m='*') + '.n_local_at_R90', '15칸 평균')}"
           " 로 옮긴다 — `d` 축에서 국소적으로 $R \\propto \\sigma^{1/n}$ 이다"
           "(`src/freespace_scene.py:56`). 아래 표의 R90 은 전부 공칭 헤딩 ψ=0 의 수이고, "
           "**민감도 봉투와 함께 읽는다** — 공통모드 σ 오차 ±10 dB 가 이 열 전체를 "
           + SS.num("common_mode.abs_range_shift_at_10db_pct.minus10", None, "{:+.1f}", "%")
           + " ~ " + SS.num("common_mode.abs_range_shift_at_10db_pct.plus10", None, "{:+.1f}", "%")
           + " 옮긴다."),

        md("⚠ 그 봉투가 어디서 오는지도 함께 적는다 — 우리 세 밴드는 전부 PO 근사가 1 dB 안에 "
           "든다고 보장되는 부품 폭 문턱 아래에 부품을 남긴다(" + ref("po-knee", "PO 유효 무릎")
           + "). 즉 σ 절대 레벨의 불확도는 **선언된 ±10 dB 봉투와 별개로 크기가 아직 정해지지 "
           "않은 항**을 하나 더 갖는다"
           + f"(⟨{J_LFA} : q5_blast_radius.po_validity_blast_radius_the_real_one⟩). 그래서 아래 "
           "km 열은 **순위를 읽는 표**로 쓴다.",
           "",
           table(["기체"] + [MODE_NAME[m] for m in MODES] + ["앵커 비교가능성"],
                 [[dr] + [f"{D['R90_anch'][(dr, m)]:.2f} km" for m in MODES]
                  + [AN.get(f"drones.{dr}.comparability.verdict")] for dr in DRONES]),
           "", SRC_R, SRC_A),

        md("밴드 순서는 기체마다 바뀐다 — 그 순서를 만드는 것은 자세별 로브 구조이고, 앵커는 "
           "밴드별 스칼라를 옮기면서 밴드 평균 레벨은 그대로 둔다. 자세를 평균하면 다섯 기체가 "
           "한 순위로 모인다.",
           "",
           table(["인용 방식", "서로 다른 순위 수", "합의 순위", "최악 뒤집힘 문턱"],
                 [["단일 자세 ψ=0",
                   SS.num("configurations.by_config.as_published.n_distinct_orders", None,
                          "{:.0f}"),
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

        md(*_fig(1, "report05_pf2_ranking",
                 "세 파형의 순위는 자세 인용 방식에 따라 어떻게 달라지는가?")),

        next_steps([
            ("σ 전격자를 현재 메쉬로 재생성해 `--stage solve` 를 다시 돌린다",
             "절대 R90 · 백분위 · 기체간 순위가 현재 기하 위에 선다 — 동일설정 재생성 대조에서 "
             "기체당 최대 "
             + S["SV"].num("overstated[0].결과_표[0].max_abs_delta_db", None, "{:.2f}", "dB")
             + " · rms "
             + S["SV"].num("overstated[0].결과_표[0].rms_delta_db", None, "{:.2f}", "dB") + " 다",
             "`src/experiment_freespace_sigma.py` → 이 편의 R90 표"),
            ("헤딩 격자 전체에서 R90(ψ) 를 풀어 P_ψ[Pd≥0.9]=0.50 지점을 낸다",
             "`R90_C50` 키가 이름 그대로의 커버리지 백분위 값을 담는다",
             "`src/experiment_freespace_range.py:703` → 이 편의 R90 표"),
        ]),
    ]


def r61_rank_durability(D, S):
    SS = S["SS"]
    return "61", "rank-durability", [
        header(
            num=61,
            title="그 순위는 자세평균이면 σ 오차 아래에서 하나로 모인다",
            did="σ 오차를 공통모드와 밴드별 차분 둘로 갈라 넣고, 파형 순위가 각각 어디까지 "
                "버티는지를 기체마다 문턱으로 냈다.",
            results=[
                f"공통모드 ±10 dB 에서 15칸 전부 순위가 유지되고 절대거리만 "
                f"{SS.num('common_mode.abs_range_shift_at_10db_pct.minus10', None, '{:+.1f}', '%')}"
                f" ~ "
                f"{SS.num('common_mode.abs_range_shift_at_10db_pct.plus10', None, '{:+.1f}', '%')}"
                f" 움직인다.",

                f"밴드별 차분 오차의 뒤집힘 문턱은 "
                f"{SS.num('differential.smallest_flip_span_db_overall', None, '{:.2f}')} ~ "
                f"{SS.num('differential.largest_flip_span_db_overall', None, '{:.2f}', 'dB')} "
                f"이고, 현실 봉투는 "
                f"{SS.num('differential.realistic_span_db', None, '{:.2f}', 'dB')} 다.",

                f"밴드별 독립 오차 2 dB 몬테카를로에서 순위 보존 확률은 "
                f"{dnum(D['mc_p2db_min'], '{:.2f}', '', f'{J_SS} : monte_carlo_per_band_error', '5기체 최소')}"
                f" ~ "
                f"{dnum(D['mc_p2db_max'], '{:.2f}', '', f'{J_SS} : monte_carlo_per_band_error', '5기체 최대')}"
                f" 다.",

                f"취약성을 정하는 것은 기체 크기가 아니라 밴드 간 σ 로브 산포다 — 크기와 뒤집힘 "
                f"문턱의 상관은 "
                f"{SS.num('size_vs_fragility.corr_extent_vs_flip_single', None, '{:+.2f}')} 다.",

                f"σ 격자를 블레이드 형상 갱신본으로 바꾸는 것만으로 R90 이 최대 "
                f"{dnum(D['stale_max_pct'], '{:.1f}', '%', f'{J_SS} : staleness_and_mesh_update.by_drone', '5기체 max_range_change_pct 최대')}"
                f" 움직이고 순위쌍 "
                f"{SS.num('staleness_and_mesh_update.n_orders_changed', None, '{:.0f}')}개가 "
                f"달라진다.",
            ],
            method=[
                ("두 오차", "공통모드는 세 밴드를 함께 옮기고, 차분은 밴드마다 다르게 옮긴다"),
                ("선형성", "σ 는 SNR 에 선형이라 σ 오프셋 Δ dB 가 곧 SNR 오프셋 Δ dB 다 — "
                          "선형성 잔차 "
                          + SS.num("_meta.sigma_linearity_check", None, "{:.1e}")),
                ("몬테카를로", "밴드마다 독립 오차를 뿌리고 순위 보존 확률을 센다 — "
                             "`benchmark/sigma_sensitivity.py`"),
                ("메쉬 세대", "표의 문턱은 형상 정정 전 메쉬 위의 값이다 — 그 정정을 받은 기체는 "
                            "Matrice 4E 하나다"),
            ],
            repro=dict(cmd=[CMD_SS, CMD_NB], out=[J_SS, J_DV],
                       runtime=_n(J_DV, "runtime.sigma_sensitivity_s", "{:.1f}", "s")),
            prereq=[(ref("r90", "R90 표"), "그 순위가 어느 표에서 읽힌 것인가")],
        ),

        md("## 그 순위는 σ 오차 아래에서 어디까지 버티나", "",
           "σ 오차를 두 종류로 나눠 넣는다. **공통모드**는 세 밴드를 함께 옮기고, **차분**은 "
           "밴드마다 다르게 옮긴다. σ 는 SNR 에 선형이라 σ 오프셋 Δ dB 가 곧 SNR 오프셋 Δ dB 다"
           f"(선형성 잔차 {SS.num('_meta.sigma_linearity_check', None, '{:.1e}')}).",
           "",
           table(["오차 종류", "무엇이 움직이나", "크기"],
                 [["공통모드 ±10 dB",
                   "순위 유지 · 절대거리만 이동",
                   "15칸 전부 순위 불변 · 거리 "
                   + SS.num("common_mode.abs_range_shift_at_10db_pct.minus10", None,
                            "{:+.1f}", "%")
                   + " ~ "
                   + SS.num("common_mode.abs_range_shift_at_10db_pct.plus10", None,
                            "{:+.1f}", "%")],
                  ["차분(밴드별)",
                   "순위가 뒤집힐 수 있는 축",
                   "뒤집힘 문턱 "
                   + SS.num("differential.smallest_flip_span_db_overall", None, "{:.2f}")
                   + " ~ "
                   + SS.num("differential.largest_flip_span_db_overall", None, "{:.2f}", "dB")
                   + " (현실 봉투 "
                   + SS.num("differential.realistic_span_db", None, "{:.2f}", "dB") + ")"],
                  ["밴드별 독립 오차 2 dB (몬테카를로)",
                   "순위 보존 확률",
                   dnum(D["mc_p2db_min"], "{:.2f}", "", f"{J_SS} : monte_carlo_per_band_error",
                        "5기체 최소") + " ~ "
                   + dnum(D["mc_p2db_max"], "{:.2f}", "",
                          f"{J_SS} : monte_carlo_per_band_error", "5기체 최대")]])),

        md(f"취약성을 정하는 것은 기체 크기가 아니라 **밴드 간 σ 로브 산포**다 — 가장 작은 "
           f"{SS.num('size_vs_fragility.smallest_airframe', None)}(전장 "
           f"{SS.num('size_vs_fragility.by_drone.mini5pro.extent_m', None, '{:.3f}', 'm')}, "
           f"LTE 에서 D/λ = "
           f"{SS.num('size_vs_fragility.by_drone.mini5pro.D_over_lambda_lte', None, '{:.2f}')})"
           f" 가 가장 견고하고, 크기와 뒤집힘 문턱의 상관은 "
           f"{SS.num('size_vs_fragility.corr_extent_vs_flip_single', None, '{:+.2f}')} 다."),

        md(f"또 하나의 실측 사실을 같은 자리에 적는다: σ 격자를 블레이드 형상 갱신본으로 바꾸는 "
           f"것만으로 R90 이 최대 "
           + dnum(D["stale_max_pct"], "{:.1f}", "%",
                  f"{J_SS} : staleness_and_mesh_update.by_drone",
                  "5기체 max_range_change_pct 최대")
           + f" 움직이고 순위쌍 "
           f"{SS.num('staleness_and_mesh_update.n_orders_changed', None, '{:.0f}')}개가 바뀌었다 "
           f"— 통제되지 않은 σ 변화의 파급을 관측한 값이다.",
           "",
           f"⚠ 위 표의 뒤집힘 문턱은 {S['MFX'].num('_meta.date', None)} 형상 정정 전 메쉬 위에 "
           f"있다 — 하한 "
           f"{SS.num('differential.smallest_flip_span_db_overall', None, '{:.2f}', 'dB')} 를 내는 "
           f"행이 그 정정을 받은 Matrice 4E 다(" + ref("mesh-vs-real", "형상 정정")
           + "). 이 하한은 **단일 자세** 기준이고, 같은 기체를 **자세평균**으로 읽으면 "
           + SS.num("aspect_averaged.by_drone.matrice4e.smallest_flip_span_db", None,
                    "{:.2f}", "dB")
           + " 다 — 캠페인 판정 문턱으로 드는 수가 그것이다("
           + ref("sim-vs-meas", "캠페인이 결판내는 양") + ")."),

        md(*_fig(1, "report05_pf3_robust",
                 "σ 오차가 공통모드일 때와 밴드별일 때 순위는 각각 어디까지 버티는가?")),

        next_steps([
            ("자세평균 σ 격자로 `--stage solve` 를 다시 돌린다",
             "합의 순위가 국소 지수 1차 전이 없이 정본 경로에서 확정된다",
             "`src/experiment_freespace_range.py` → " + ref("r90", "R90 표")),
        ]),
    ]


def r62_cpi_sweep(D, S):
    CG = S["CG"]
    return "62", "cpi-sweep", [
        header(
            num=62,
            title="CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다",
            did="0-도플러 가드가 지우는 헤딩 비율을 CPI 축에서 스윕해, 5G 가 치르는 대가가 "
                "적분시간으로 줄어드는 부분과 배수로 남는 부분을 갈랐다.",
            results=[
                f"5G 의 눈먼 헤딩 비율은 CPI "
                f"{CG.num('equal_cpi_penalty[0].T_cpi_s', None, '{:.1f}', 's')} 에서 "
                f"{CG.num('verdict.artifact.blind_hard_same_cpi', None, '{:.3f}')}, CPI "
                f"{CG.num('equal_cpi_penalty[1].T_cpi_s', None, '{:.1f}', 's')} 에서 "
                f"{CG.num('verdict.artifact.blind_hard_at_200ms', None, '{:.3f}')} 로 내려간다.",

                f"WiFi 대비 배수는 CPI 전 구간에서 "
                f"{CG.num('equal_cpi_penalty[0].ratio_G1_over_W1', None, '{:.1f}')}~"
                f"{CG.num('equal_cpi_penalty[3].ratio_G1_over_W1', None, '{:.1f}', '배')} 로 "
                f"남는다 — 이것이 이 대가를 구조로 만드는 첫 번째 사실이다.",

                f"도플러 축을 지우는 기구는 둘이다 — 표본화 쪽은 가드가 접힘 축 전체를 덮는 "
                f"구조식 `{CG.num('structural.formula', None)}` 이고, 진폭 쪽은 짧은 CPI 에서 "
                f"가드가 도플러 진폭을 덮는 파형 공통 현상이다.",

                f"5G 의 alias 비율 "
                f"{CG.num('verdict.structural.s2_alias_floor.alias_frac_G1', None, '{:.3f}')} 는 "
                f"CPI 와 무관한 상수이고, WiFi·LTE 는 "
                f"{CG.num('verdict.structural.s2_alias_floor.alias_frac_W1', None, '{:.3f}')} 다.",
            ],
            method=[
                ("가드 규약", "가드 반폭 = g빈 × PRF/M 이고 g 는 검출기 적용값 1.5빈과 선언값 "
                            "2.5빈 둘 다 잰다"),
                ("격자", "헤딩 "
                        + CG.num("meta.psi_n_fine", None, "{:.0f}") + "점 · 표적 속도 "
                        + CG.num("meta.geometry.speed_ms", None, "{:.0f}", "m/s") + " — "
                        "`benchmark/cpi_guard_sweep.py`"),
                ("두 기구", "표본화(접힘 축 전체를 가드가 덮는가)와 진폭(도플러 진폭이 가드 안에 "
                          "드는가)을 따로 센다"),
            ],
            repro=dict(cmd=[CMD_CG, CMD_NB], out=[J_CG],
                       runtime=_n(J_DV, "runtime.cpi_guard_sweep_s", "{:.1f}", "s")),
        ),

        md("## 5G 의 상시기준 대가 — CPI 스윕", "",
           "5G 의 상시 기준신호(SSB)는 20 ms 주기라 PRF 50 Hz 를 준다. 도플러 축을 지우는 기구는 "
           f"둘이다 — **A. 표본화**: `{CG.num('structural.formula', None)}` 로 가드가 접힘 축 "
           "전체를 덮는다(반송파·속도·거리 무관). **B. 진폭**: 짧은 CPI 에서 가드가 도플러 "
           "진폭을 덮는다(파형 공통). 1.5빈 규약에서 LTE 도 CPI ≤ "
           f"{CG.num('structural.two_mechanisms.observed.L1.hard.T_max_total_blind_s', None, '{:.3f}', 's')}"
           " 에서 전 헤딩 블라인드가 된다.",
           "",
           table(["모드", "PRF",
                  f"CPI {S['cg_T0']} s 의 M",
                  "접힘 축 ±", "블라인드(1.5빈)", "블라인드(2.5빈)"],
                 [[MODE_NAME[m],
                   CG.num(f"waveform_facts.{m}.prf_hz", None, "{:.0f}", "Hz"),
                   CG.num(f"anchor.reproduction.{m}.M", None, "{:.0f}"),
                   CG.num(f"anchor.reproduction.{m}.fold_half_hz", None, "{:.1f}", "Hz"),
                   CG.num(f"anchor.reproduction.{m}.blind_hard", None, "{:.3f}"),
                   CG.num(f"anchor.reproduction.{m}.blind_declared", None, "{:.3f}")]
                  for m in MODES])),

        md(f"5G 의 커버리지 0 은 선언가드 2.5빈 · CPI ≤ "
           f"{CG.num('structural.by_mode.G1.T_max_total_blind_declared_s', None, '{:.2f}', 's')} "
           f"에서 성립한다. 검출기가 적용하는 1.5빈 규약의 경계는 "
           f"{CG.num('structural.by_mode.G1.T_max_total_blind_hard_s', None, '{:.2f}', 's')} 이고, "
           f"CPI {CG.num('equal_cpi_penalty[0].T_cpi_s', None, '{:.1f}', 's')} 의 블라인드율은 "
           f"{CG.num('verdict.artifact.blind_hard_same_cpi', None, '{:.3f}')} 다."),

        md("CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다. 5G 가 치르는 **배수**는 그대로 "
           "남는다 — 이것이 이 대가를 구조로 만드는 첫 번째 사실이다.",
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
           f"{CG.num('verdict.structural.s2_alias_floor.alias_frac_G1', None, '{:.3f}')} 는 "
           f"적분시간이 아니라 표본화율의 성질이라 CPI 와 무관한 상수이고, WiFi·LTE 는 "
           f"{CG.num('verdict.structural.s2_alias_floor.alias_frac_W1', None, '{:.3f}')} 다."),

        next_steps([
            ("CPI 를 0.1 s 에서 1.0 s 까지 정본 solve 에 넣어 R90(CPI) 를 낸다",
             "이 편의 커버리지 회복이 거리 축에서도 확정된다",
             "`benchmark/cpi_guard_sweep.py` → `src/experiment_freespace_range.py`"),
        ]),
    ]


def r63_cpi_residual(D, S):
    CG = S["CG"]
    return "63", "cpi-residual", [
        header(
            num=63,
            title="모호속도는 표본화율의 성질이라 CPI 로 바뀌지 않는다",
            did="세 파형의 모호속도를 표본화율에서 직접 내고, 커버리지를 WiFi·LTE 수준으로 "
                "끌어올리는 데 드는 CPI 와 그 CPI 가 무는 재방문 시간을 함께 적었다.",
            results=[
                f"모호속도는 5G "
                f"{CG.num('unambiguous_speed.G1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · "
                f"WiFi "
                f"{CG.num('unambiguous_speed.W1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · "
                f"LTE "
                f"{CG.num('unambiguous_speed.L1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} 다.",

                f"커버리지를 WiFi 수준으로 올리는 CPI 는 "
                f"{CG.num('cost_of_long_cpi.required_cpi_s.to_WiFi_parity', None, '{:.2f}', 's')}"
                f", LTE 수준은 "
                f"{CG.num('cost_of_long_cpi.required_cpi_s.to_LTE_parity', None, '{:.2f}', 's')} "
                f"이고 그 대가는 재방문 시간이다.",

                f"그 CPI 가 코히어런스 한계 안에 머무는 구간은 표적 속도 "
                f"{CG.num('cost_of_long_cpi.by_speed[6].speed_ms', None, '{:.0f}', 'm/s')} "
                f"까지이고, "
                f"{CG.num('cost_of_long_cpi.by_speed[7].speed_ms', None, '{:.0f}', 'm/s')} "
                f"에서 WiFi 패리티 CPI 가 한계 "
                f"{CG.num('cost_of_long_cpi.by_speed[7].T_coh_s', None, '{:.2f}', 's')} 를 "
                f"넘어선다.",

                f"거리·속도 격자 "
                f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_cells', None, '{:.0f}')}칸 중 "
                f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_WiFi_parity_feasible', None, '{:.0f}')}"
                f"칸이 WiFi 패리티를 허용한다.",
            ],
            method=[
                ("모호속도", "접힘 후 도플러 축 ±PRF/2 를 파장으로 속도로 옮긴다 — 적분시간이 "
                            "들어가지 않는 양이다"),
                ("패리티 CPI", "5G 의 블라인드율이 WiFi·LTE 값과 같아지는 CPI 를 스윕에서 "
                             "역으로 읽는다"),
                ("코히어런스 한계", "표적 속도와 거리에서 나오는 코히어런트 적분 상한과 그 CPI 를 "
                                "맞대 본다"),
            ],
            repro=dict(cmd=[CMD_CG, CMD_NB], out=[J_CG],
                       runtime=_n(J_DV, "runtime.cpi_guard_sweep_s", "{:.1f}", "s")),
            prereq=[(ref("cpi-sweep", "CPI 스윕"), "블라인드율이 CPI 로 내려가는 부분")],
        ),

        md("## CPI 로도 안 바뀌는 것", "",
           f"세 번째 사실이 결정적이다: 모호속도는 표본화율의 성질이라 CPI 로 바뀌지 않는다 — "
           f"5G {CG.num('unambiguous_speed.G1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · WiFi "
           f"{CG.num('unambiguous_speed.W1.v_unambiguous_ms', None, '{:.2f}', 'm/s')} · LTE "
           f"{CG.num('unambiguous_speed.L1.v_unambiguous_ms', None, '{:.2f}', 'm/s')}. "
           f"커버리지를 WiFi 수준으로 올리는 CPI 는 "
           f"{CG.num('cost_of_long_cpi.required_cpi_s.to_WiFi_parity', None, '{:.2f}', 's')}, "
           f"LTE 수준은 "
           f"{CG.num('cost_of_long_cpi.required_cpi_s.to_LTE_parity', None, '{:.2f}', 's')} 이고 "
           "그 대가는 재방문 시간이다.",
           "",
           table(["패리티 목표 (5 m/s)", "필요 CPI", "SSB 버스트", "헤드라인 대비 경과", "거리워크",
                  "코히어런트 이득"],
                 [[nm,
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.T_required_s", None,
                          "{:.2f}", "s"),
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.ssb_bursts_needed", None,
                          "{:.0f}"),
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.elapsed_vs_headline", None,
                          "{:.2f}", "배"),
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.range_walk_bins_median", None,
                          "{:.3f}", "빈"),
                   CG.num(f"cost_of_long_cpi.at_required_cpi.{k}.snr_gain_db_if_coherent", None,
                          "{:.2f}", "dB")]
                  for nm, k in (("LTE 수준", "v5_LTE_parity"),
                                ("WiFi 수준", "v5_WiFi_parity"))])),

        md(f"그 CPI 가 코히어런스 한계 안에 머무는 구간은 "
           f"{CG.num('cost_of_long_cpi.by_speed[6].speed_ms', None, '{:.0f}', 'm/s')} 까지이고, "
           f"{CG.num('cost_of_long_cpi.by_speed[7].speed_ms', None, '{:.0f}', 'm/s')} 에서 WiFi "
           f"패리티 CPI 가 한계"
           f"({CG.num('cost_of_long_cpi.by_speed[7].T_coh_s', None, '{:.2f}', 's')}) 를 넘어선다 "
           f"— 거리·속도 격자 "
           f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_cells', None, '{:.0f}')}칸 중 "
           f"{CG.num('cost_of_long_cpi.coherence_map_summary.n_WiFi_parity_feasible', None, '{:.0f}')}"
           f"칸이 WiFi 패리티를 허용한다."),

        md(*_fig(1, "report05_pf4_cpi",
                 "5G 의 눈먼 헤딩 비율은 CPI 와 표적 속도에 따라 어떻게 움직이는가?")),

        next_steps([
            ("표적 속도와 헤딩을 격자로 놓고 접히는 칸을 센다",
             "5G 가 모호 없이 재는 속도 구간이 수치로 확정된다",
             "`benchmark/cpi_guard_sweep.py` 의 by_speed → 이 편의 모호속도 표"),
        ]),
    ]


def r64_sigma_free_axis(D, S):
    DV = S["DV"]
    return "64", "sigma-free-axis", [
        header(
            num=64,
            title="σ 를 곱하기 전에 이미 세 파형의 순서를 정하는 축이 있다",
            did="같은 표적·같은 기하·같은 검출기에서 Pd = 0.5 에 필요한 출력 SNR 을 기준신호 "
                "대역과 점유 등급으로만 갈라, σ 와 무관하게 정해지는 순서를 냈다.",
            results=[
                f"상시 기준신호만 쓰는 제약의 대가는 5G 에서 "
                f"{DV.num('always_on_cost.G.cost_db', None, '{:+.2f}', 'dB')} 이고, WiFi 는 "
                f"{DV.num('always_on_cost.W.cost_db', None, '{:+.2f}', 'dB')} · LTE 는 "
                f"{DV.num('always_on_cost.L.cost_db', None, '{:+.2f}', 'dB')} 다.",

                f"그 대가는 거리분해능으로도 읽힌다 — 5G 는 "
                f"{DV.num('always_on_cost.G.dr_g1_m', None, '{:.2f}', 'm')} 대 "
                f"{DV.num('always_on_cost.G.dr_g3_m', None, '{:.2f}', 'm')} 다.",

                f"이 스윕은 단일 반송파 "
                f"{DV.num('bench.fc_ghz', None, '{:.1f}', 'GHz')} · 바이스태틱 거리 "
                f"{DV.num('bench.Rb_m', None, '{:.1f}', 'm')} · 고정 σ "
                f"{DV.num('bench.sigma_dbsm', None, '{:.2f}', 'dBsm')} 라 표적·기하·σ 가 한 값에 "
                f"묶여 있다.",

                f"그래서 여기서 읽는 것은 파형 축 하나의 상대 비교다 — 절대 거리는 "
                f"{DV.num('bench.drone', None)} 한 기체의 벤치 배치에서 나온다.",
            ],
            method=[
                ("배치", "X410 벤치(`src/experiment_x410.py:101`) — 9모드 전부 단일 반송파·단일 "
                        "기하·단일 σ 다"),
                ("등급", "상시 기준(등급 1)과 세션 기준(등급 3)을 같은 검출기에 물려 Pd=0.5 "
                        "요구 SNR 을 비교한다"),
                ("읽는 범위", "이 축은 σ 를 곱하기 전이라 표적 모형과 무관하다 — 절대 SNR 은 "
                            "이 벤치 배치 안에서만 읽는다"),
            ],
            repro=dict(cmd=[CMD_DET, CMD_NB], out=[J_RX, J_DV],
                       runtime="검출 스윕 선언 예산 "
                               + _n(J_DV, "runtime.declared_breakdown_s.experiment_detection",
                                    "{:.0f}", "s")),
        ),

        md("## σ 를 곱하기 전 축 — 기준신호 대역과 점유 등급", "",
           "같은 표적·같은 기하·같은 검출기에서 Pd = 0.5 에 필요한 출력 SNR 은 기준신호 대역과 "
           "프레임 수가 정한다. 이 축은 σ 와 무관하게 세 파형의 순서를 정한다.",
           "",
           table(["표준", "상시 기준(등급 1)", "세션 기준(등급 3)", "상시 제약의 대가",
                  "거리분해능 대비"],
                 [[nm,
                   DV.num(f"always_on_cost.{c}.snr50_g1", None, "{:.2f}", "dB"),
                   DV.num(f"always_on_cost.{c}.snr50_g3", None, "{:.2f}", "dB"),
                   DV.num(f"always_on_cost.{c}.cost_db", None, "{:+.2f}", "dB"),
                   DV.num(f"always_on_cost.{c}.dr_g1_m", None, "{:.2f}", "m") + " ↔ "
                   + DV.num(f"always_on_cost.{c}.dr_g3_m", None, "{:.2f}", "m")]
                  for nm, c in (("WiFi", "W"), ("LTE", "L"), ("5G NR", "G"))])),

        md(f"이 스윕은 거리 표와 **다른 배치**에서 돈다 — X410 벤치"
           f"(`src/experiment_x410.py:101`), 단일 반송파 "
           f"{DV.num('bench.fc_ghz', None, '{:.1f}', 'GHz')} 를 9모드 전부에 쓰고, 바이스태틱 "
           f"거리 {DV.num('bench.Rb_m', None, '{:.1f}', 'm')}, 고정 σ "
           f"{DV.num('bench.sigma_dbsm', None, '{:.2f}', 'dBsm')} 다. 표적·기하·σ 를 한 값으로 "
           f"묶었으므로 여기서 읽는 것은 **파형 축 하나**의 상대 비교다."),

        next_steps([
            ("파형·수신소자 스윕을 자유공간 기하와 물리 PRF 로 옮긴다",
             "이 편과 " + ref("rx-elements", "수신소자 이득") + " 의 절대 SNR 이 거리 표와 같은 "
             "축에 놓인다",
             "`src/experiment_detection.py` 의 X410Scenario → `src/freespace_scene.py`"),
        ]),
    ]


def r65_target_model_swap(D, S):
    TM, TA = S["TM"], S["TA"]
    TAE = "Q1_normalisation.recomputed_spread_db_by_matching_estimator"
    return "65", "target-model-swap", [
        header(
            num=65,
            title="평판·큐브·우리 격자를 같은 동작점에서 갈아끼우면 요구 이득이 이만큼 달라진다",
            did="같은 기하·같은 검출기·같은 동작점에서 표적만 세 모형으로 갈아끼우고, 자세평균을 "
                "맞춘 뒤 남는 요구 추가이득을 추정량별로 적었다.",
            results=[
                f"자세 앙상블은 셀당 "
                f"{TM.num('statistics.n_aspect_realisations_per_cell', None, '{:.0f}')}자세 "
                f"전수이고, (기체×밴드) 셀은 "
                f"{TM.num('statistics.n_drone_band_cells', None, '{:.0f}')}개다 — 재현편차는 "
                f"{TA.num('meta.reproduction.E0_extra_gain_max_abs_dev_db', None, '{:.2f}', 'dB')}"
                f" 다.",

                f"낙차의 소유자는 정육면체다 — 자유공간에서 최대가 M2 인 셀이 "
                f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmax_counts.M2', None, '{:.0f}')}"
                f"개, 최소가 M1 인 셀이 "
                f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmin_counts.M1', None, '{:.0f}')}"
                f"개로 전수다.",

                f"우리 격자(M3)의 몫은 다섯 앙상블에서 "
                f"{TA.num('Q3_staleness.argmax_argmin_counts.E2_outdoor_canyon.m3_share_of_spread', None, '{:.1%}')}"
                f" ~ "
                f"{TA.num('Q3_staleness.argmax_argmin_counts.E1_chamber_floor.m3_share_of_spread', None, '{:.1%}')}"
                f" 다.",

                f"각 다양성이 낙차를 줄인다 — 각 다양성이 0 인 자유공간에서 "
                f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E0_freespace', None, '{:.2f}', 'dB')}"
                f", 가장 큰 앙상블에서 "
                f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E2b_outdoor_shadowed', None, '{:.2f}', 'dB')}"
                f" 다.",

                f"크기는 추정량이 정한다 — 검출기가 읽는 p10 에서 맞추면 낙차가 "
                f"{TA.num(f'{TAE}.p10.spread_mean', None, '{:.2f}', 'dB')} 로 줄고 세 팔의 순서가 "
                f"뒤집혀 M1 이 가장 어려운 팔이 된다.",
            ],
            method=[
                ("세 모형", "자세무관 평판 σ "
                          + TM.num("protocol.operating_point.sigma_reference_dbsm", None,
                                   "{:.2f}", "dBsm")
                          + "(3GPP, M1) · 정육면체(M2) · 우리 SBR+PO 격자(M3)"),
                ("정규화", "자세평균을 맞춘 뒤 남는 **요구 추가이득**을 읽는다 — 추정량 네 가지를 "
                          "나란히 싣는다"),
                ("문턱", "잡음전력 기지 이상문턱이고 CA-CFAR 문턱은 세 팔에 같은 오프셋을 준다 — "
                        "교정표는 세 팔의 절대 소요이득만 옮긴다"),
            ],
            repro=dict(cmd=[CMD_TM, CMD_NB], out=[J_TM, J_TA],
                       runtime="약 6 분 (CPU)"),
            prereq=[(ref("box-sphere-control", "상자·구 대조군"),
                     "레벨만 맞추는 단순 모형이 σ 축에서 어디까지 가는가"),
                    (ref("cfar-calib", "경험 Pfa 교정"),
                     "CA-CFAR 문턱이 세 팔에 같은 오프셋을 준다는 것")],
        ),

        md("## 표적모형이 검출을 얼마나 바꾸나", "",
           f"같은 기하·같은 검출기·같은 동작점에서 표적만 세 모형으로 갈아끼웠다 — 자세무관 평판 "
           f"σ {TM.num('protocol.operating_point.sigma_reference_dbsm', None, '{:.2f}', 'dBsm')}"
           f"(3GPP, M1) · 정육면체(M2) · 우리 SBR+PO 격자(M3). 자세 앙상블은 셀당 "
           f"{TM.num('statistics.n_aspect_realisations_per_cell', None, '{:.0f}')}자세 전수, "
           f"(기체×밴드) 셀은 "
           f"{TM.num('statistics.n_drone_band_cells', None, '{:.0f}')}개이고, 자세평균을 맞춘 뒤 "
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
                                ("p10 — 검출기가 읽는 분위수", "p10"))])),

        md(f"낙차의 소유자는 정육면체다 — 자유공간에서 최대가 M2 인 셀이 "
           f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmax_counts.M2', None, '{:.0f}')}"
           f"개, 최소가 M1 인 셀이 "
           f"{TA.num('Q3_staleness.argmax_argmin_counts.E0_freespace.argmin_counts.M1', None, '{:.0f}')}"
           f"개로 전수이고, M3 몫은 다섯 앙상블에서 "
           f"{TA.num('Q3_staleness.argmax_argmin_counts.E2_outdoor_canyon.m3_share_of_spread', None, '{:.1%}')}"
           f" ~ "
           f"{TA.num('Q3_staleness.argmax_argmin_counts.E1_chamber_floor.m3_share_of_spread', None, '{:.1%}')}"
           f" 다.",
           "",
           f"각 다양성이 그 낙차를 줄인다 — 각 다양성이 0 인 자유공간(N_eff "
           f"{TM.num('verdicts.Q3_environment_dependence.predictor.E0_freespace.n_eff_pairs', None, '{:.1f}')}"
           f")에서 "
           f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E0_freespace', None, '{:.2f}', 'dB')}"
           f", 각 다양성이 가장 큰 앙상블(N_eff "
           f"{TM.num('verdicts.Q3_environment_dependence.predictor.E2b_outdoor_shadowed.n_eff_pairs', None, '{:.2f}')}"
           f")에서 "
           f"{TM.num('verdicts.Q3_environment_dependence.pure_pattern_spread_db_by_env.E2b_outdoor_shadowed', None, '{:.2f}', 'dB')}"
           f" 다."),

        md(f"⚠ 크기는 **추정량이 정한다** — 검출기가 읽는 p10 에서 맞추면 낙차가 "
           f"{TA.num(f'{TAE}.p10.spread_mean', None, '{:.2f}', 'dB')} 로 줄고 세 팔의 순서가 "
           f"뒤집혀 M1 이 가장 어려운 팔이 된다. 문턱은 잡음전력 기지 이상문턱이고 CA-CFAR "
           f"문턱은 세 팔에 같은 오프셋을 주므로, 교정표는 세 팔의 절대 소요이득만 옮긴다"
           f"(⟨{J_TM} : protocol.pfa_convention⟩).",
           "",
           "⚠ 이 표에 **구 대조군은 없다.** 구는 **부피를 맞게 고르면** σ 의 절대 레벨을 맞출 수 "
           "있는 단순 모형이면서 자세에 따른 변화를 0 으로 낸다 — 레벨에서 우리 메쉬를 앞선 그 "
           "구는 논문이 적어 둔 상자 치수로 잡은 부피이고, 메쉬 부피로 잡으면 두 잣대 모두에서 "
           "우리 메쉬보다 나쁘다(" + ref("box-sphere-control", "상자·구 대조군")
           + "). 그래서 이 표의 낙차는 «자세 구조를 얼마나 담는가» 의 낙차로 읽는다."),

        next_steps([
            ("표적모형 민감도의 M3 팔을 재생성 격자로 다시 푼다",
             "우리 팔의 요구 추가이득 "
             + TA.num("Q3_staleness.m3_own_number.base_db", None, "{:.2f}", "dB")
             + " 와 낙차 몫 "
             + TA.num("Q3_staleness.argmax_argmin_counts.E0_freespace.m3_share_of_spread", None,
                      "{:.1%}") + " 가 현재 메쉬 위에 선다",
             "`scratchpad/tm_result.py` → 이 편의 세 팔 표"),
            ("표적모형 민감도에 **구 팔(M4)** 을 더한다",
             "레벨만 맞추는 모형과 자세 구조를 담는 모형의 검출 낙차가 갈라진다",
             "`scratchpad/tm_result.py` → 이 편의 세 팔 표"),
        ]),
    ]


def r66_rx_elements(D, S):
    RX, DV = S["RX"], S["DV"]
    return "66", "rx-elements", [
        header(
            num=66,
            title="코히어런트 배열이득은 10log₁₀N 상한에 −0.11~+0.47 dB 로 붙는다",
            did="한 지점 λ/2 배열의 소자 수를 늘려 가며 Pd=0.5 요구 SNR 을 재고, 그 이득을 "
                "열잡음만 상대할 때의 코히어런트 상한과 맞대 봤다.",
            results=[
                f"9모드 × N 전체에서 측정 이득은 상한 10log₁₀N 대비 "
                f"{DV.num('rx_gain.excess_min_db', None, '{:+.2f}')} ~ "
                f"{DV.num('rx_gain.excess_max_db', None, '{:+.2f}', 'dB')} 다.",

                f"결합 잡음전력/σ² = "
                f"{RX.num('modes.W1.combine_ratio', None, '{:.5f}')} 로 잡음 보존을 확인했다 — "
                f"그래서 10log₁₀N 은 이상적 상한이다.",

                f"초과분의 출처는 ECA 잔차다 — 감시신호가 `surv = √N·echo + dpi + noise` 이고 "
                f"`dpi` 가 N 에 무관하게 고정이라 √N 이 잡음과 잔차 양쪽 대비로 표적을 올린다.",

                f"로지스틱 재적합에서도 같은 부호가 나온다 — "
                f"{DV.num('rx_gain.excess_fit_min_db', None, '{:+.2f}')} ~ "
                f"{DV.num('rx_gain.excess_fit_max_db', None, '{:+.2f}', 'dB')} 이고, 최대 "
                f"초과분은 SNR50 몬테카를로 표준편차의 "
                f"{DV.num('rx_gain.excess_in_sigma', None, '{:.1f}', 'σ')} 배다.",

                f"기하·규약 게이트 "
                f"{S['VF'].num('summary.n_ran', None, '{:.0f}')}건이 전부 통과했다"
                f"(실패 {S['VF'].num('summary.n_fail', 0, '{:.0f}')}건).",
            ],
            method=[
                ("배열", "한 지점 λ/2 ULA 소자 N 개, 조향벡터는 참 표적 방향 — "
                        "`src/experiment_detection.py:181`"),
                ("상한", "10log₁₀N 은 **열잡음만** 상대할 때의 코히어런트 배열이득이고, 소자 간 "
                        "결합·교정오차·위치오차가 0 인 이상적 값이다"),
                ("대조군", "격자 보간 대신 Pd 곡선에 로지스틱을 다시 적합해 같은 양을 두 번 잰다"),
                ("몬테카를로", "K = " + DV.num("rx_gain.K", None, "{:.0f}")
                            + " 회에서 SNR50 의 표준편차를 내고 초과분을 그 배수로 읽는다"),
            ],
            repro=dict(cmd=[CMD_DET, CMD_VF, CMD_NB], out=[J_RX, J_VF, J_DV],
                       runtime="검출 스윕 선언 예산 "
                               + _n(J_DV, "runtime.declared_breakdown_s.experiment_detection",
                                    "{:.0f}", "s")
                               + " · 게이트 "
                               + _n(J_DV, "runtime.verify_freespace_s", "{:.2f}", "s")),
        ),

        md("## 수신소자를 늘리면", "",
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
           f"출처 ⟨{J_RX} : modes.W1.curves.*.snr50⟩"),

        md(f"9모드 × N 전체에서 측정 이득은 그 상한 대비 "
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
                   DV.num("rx_gain.excess_in_sigma", None, "{:.1f}", "σ")]])),

        md(*_fig(1, "report05_pf5_multirx",
                 "수신소자를 늘렸을 때 얻는 감도는 이상적 코히어런트 상한에 얼마나 붙는가?")),

        next_steps([
            ("`SIONNA2_DPI_AMP=0` 대조군으로 Rx 스윕을 다시 돌린다",
             "위 초과분이 ECA 잔차 대비 이득임이 대조군으로 확정된다",
             "`src/experiment_detection.py:115` → 이 편의 초과분 표"),
        ]),
    ]


BUILDERS = [r56_geometry, r57_sensitivity_chain, r58_shared_threshold, r59_slope_anchor,
            r60_r90, r61_rank_durability, r62_cpi_sweep, r63_cpi_residual,
            r64_sigma_free_axis, r65_target_model_swap, r66_rx_elements]


# --------------------------------------------------------------------------- #
def sources() -> dict:
    S = {k: from_json(v) for k, v in
         dict(FS=J_FS, RX=J_RX, AN=J_AN, VF=J_VF, SS=J_SS, CG=J_CG, DV=J_DV,
              TM=J_TM, TA=J_TA, PH=J_PH, SV=J_SV, LFA=J_LFA, MFX=J_MFX).items()}
    from_json(J_MFX_ATK)                      # 경로로 가리키는 파일 — 존재 검사
    from_json(J_LFQ)
    S["cg_T0"] = f"{S['CG'].get('equal_cpi_penalty[0].T_cpi_s'):.1f}"
    return S


def shard(no: str, anchor: str, rep: dict, blocks) -> str:
    os.makedirs(SHARDDIR, exist_ok=True)
    p = os.path.join(SHARDDIR, f"{anchor}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(dict(no=no, anchor=anchor, part=10, part_name="검출 결과",
                       title=REPORTS[anchor]["title"],
                       file=f"reports/{no}_{anchor}.ipynb",
                       builder="src/build_part10_results.py",
                       md_cells=rep["md_cells"], figures=rep["figures"],
                       provenance_tags=rep["provenance_tags"],
                       negatives=rep["n_negatives"], hedges=rep["n_hedges"],
                       ok=rep["ok"]), f, ensure_ascii=False, indent=1)
    return p


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    D = R5.derived()
    S = sources()
    print(f"논문 캡션: {write_paper_figs()}")
    tot = {"md": 0, "fig": 0, "prov": 0}
    for fn in BUILDERS:
        no, anchor, blocks = fn(D, S)
        path = os.path.join(OUTDIR, f"{no}_{anchor}.ipynb")
        rep = build_notebook(path, blocks, strict=True, quiet=True)
        shard(no, anchor, rep, blocks)
        tot["md"] += rep["md_cells"]
        tot["fig"] += rep["figures"]
        tot["prov"] += rep["provenance_tags"]
        print(f"✅ 편 {no} {anchor:<20} md {rep['md_cells']:>2}셀 · 그림 {rep['figures']} · "
              f"출처 {rep['provenance_tags']:>3}개 · 부정문 {rep['n_negatives']} · "
              f"완충어 {rep['n_hedges']}")
    print(f"\n부 10 — 편 {len(BUILDERS)}개 · 마크다운 {tot['md']}셀 · 그림 {tot['fig']} · "
          f"출처태그 {tot['prov']}개")


if __name__ == "__main__":
    main()
