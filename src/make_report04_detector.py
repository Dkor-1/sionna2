# -*- coding: utf-8 -*-
"""make_report04_detector.py — 리포트 04(검출기) 노트북을 만든다

    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report04_detector.py
    → report04_detector.ipynb

서술 규약: `docs/REBUILD_2026-07-30.md` §5 (구현은 `src/report_style.py`).
  · 숫자는 전부 `num()`/`table_from()` 으로 JSON 에서 뽑는다. 손으로 친 숫자 0개.
  · 그림은 `src/viz_report04_detector.py` 가 미리 만든 PNG 를 끼우고 캡션 한 줄.
  · 마지막 절은 `limits()` — 다음 사람이 이어받을 지점.

근거 JSON
    outputs/verify_cfar.json          §3 CFAR 교정 (GPU 측정)
    outputs/verify_eca.json           §1 사슬 · §2 ECA
    outputs/verify_observability.json §4 분해능 · 관측가능성

⚠ 이 파일은 임포트해도 노트북을 쓰지 않는다(`__main__` 에서만 쓴다).
⚠ 행 인덱스를 하드코딩하지 않는다 — `_row()` 가 (guard/train, 0-도플러 마스크 폭, 명목 Pfa)
   조건으로 찾아 인덱스를 만들고, 하나로 특정되지 않으면 예외를 낸다. JSON 을 다시 생성해
   행 순서가 바뀌어도 리포트가 조용히 틀린 숫자를 싣지 않는다.
⚠ 소절 제목에 소수점 번호(§3.1 같은)를 쓰지 않는다 — 규약 검사기가 그것을 '출처 없는 숫자'로
   본다. 소절은 이름으로 부르고, 상호참조는 절 번호(§3)로 한다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from report_style import (                                          # noqa: E402
    ContractError, build_notebook, caption, code, fetch, header, limits,
    md, num, table, table_from,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NB = os.path.join(ROOT, "report04_detector.ipynb")

CFAR = "outputs/verify_cfar.json"
ECA = "outputs/verify_eca.json"
OBS = "outputs/verify_observability.json"
FIGDIR = "outputs/figures"

#: 파형 3종. (verify_cfar 밴드 키, verify_eca 셋업 이름, 표에 쓸 짧은 이름)
#  긴 이름("5G NR 100 MHz")은 §1 의 JSON 표에만 두고, 손으로 만드는 표에서는 짧게 쓴다.
WFS = [("WiFi80", "WiFi 80MHz", "WiFi"),
       ("LTE20", "LTE 20MHz", "LTE"),
       ("NR100", "5G NR 100MHz", "5G")]

GT = fetch(f"{CFAR}:meta.gt_default")               # guard 2x2 / train 6x6
ZD = fetch(f"{CFAR}:meta.zd_mask_operational")      # 운용 0-도플러 마스크 폭
PFA_OP = 1e-4                                       # 운용 명목 Pfa


# --------------------------------------------------------------------------- #
#  인덱스 해석기 — 키 경로를 만들되, 그 행이 정말 우리가 말한 행인지 확인하고 만든다
# --------------------------------------------------------------------------- #
def _find(rows, **kw) -> int:
    """조건에 맞는 행 하나의 인덱스. 없거나 여럿이면 예외 — 조용히 틀리게 두지 않는다."""
    hit = [i for i, r in enumerate(rows)
           if all(abs(r[k] - v) < 1e-15 if isinstance(v, float) else r[k] == v
                  for k, v in kw.items())]
    if len(hit) != 1:
        raise ContractError(f"행을 하나로 특정하지 못했다: {kw} → {len(hit)}개")
    return hit[0]


def _rows_key(base: str, pfa: float, mask: int) -> str:
    i = _find(fetch(f"{CFAR}:{base}"), gt=GT, zd_mask_width=mask, pfa_nom=pfa)
    return f"{base}[{i}]"


def _row(band: str, mode: str, win: str, pfa: float = PFA_OP, mask: int = ZD) -> str:
    """`chain.<밴드>.<모드>.<창>.rows[i]` — 모드 noise|dpi_eca, 창 op|wide."""
    return _rows_key(f"chain.{band}.{mode}.{win}.rows", pfa, mask)


def _white_row(pfa: float = PFA_OP, mask: int = ZD) -> str:
    return _rows_key("white.48x24.rows", pfa, mask)


def _ctrl_row(key: str, pfa: float = PFA_OP, mask: int = ZD) -> str:
    return _rows_key(f"{key}.op.rows", pfa, mask)


def _setup(name: str) -> int:
    return _find(fetch(f"{ECA}:meta.setups"), name=name)


def _s1_deepest(name: str) -> str:
    """탭을 가장 많이 준 행 = 측정된 소거 깊이의 상한(바닥)."""
    i = _find(fetch(f"{ECA}:S1_depth_vs_taps"), name=name)
    rows = fetch(f"{ECA}:S1_depth_vs_taps[{i}].rows")
    j = max(range(len(rows)), key=lambda k: rows[k]["n_taps"])
    return f"S1_depth_vs_taps[{i}].rows[{j}]"


def _s4(name: str, M: int) -> str:
    return f"S4_target_loss[{_find(fetch(f'{ECA}:S4_target_loss'), name=name, M=M)}]"


def _clutter_max() -> str:
    """정적 클러터를 가장 크게 키운 스윕 점."""
    rows = fetch(f"{ECA}:S5_clutter_dead.sweep")
    j = max(range(len(rows)), key=lambda k: rows[k]["scale"])
    return f"S5_clutter_dead.sweep[{j}]"


def _calib(band: str, target: float) -> str:
    base = f"chain.{band}.dpi_eca.calib_op_mask1.points"
    return f"{base}[{_find(fetch(f'{CFAR}:{base}'), pfa_target_emp=target)}]"


def _img(name: str, fig_no: int, question: str, alt: str = ""):
    return md(f"![{alt or name}]({FIGDIR}/report04_{name}.png)", "", caption(fig_no, question))


# --------------------------------------------------------------------------- #
#  블록
# --------------------------------------------------------------------------- #
def blocks():
    M_CPI = num(None, f"{CFAR}:meta.M_cpi", "{:.0f}")
    N_CHAIN = num(None, f"{CFAR}:meta.n_maps_chain", "{:,.0f}")
    N_WHITE = num(None, f"{CFAR}:meta.n_maps_white", "{:,.0f}")
    RUNTIME = num(None, f"{CFAR}:meta.runtime_s", "{:.0f}", "s")
    NOM = num(None, f"{CFAR}:{_row('NR100', 'dpi_eca', 'op')}.pfa_nom", "{:.0e}")
    PFA_1E6 = num(None, f"{CFAR}:{_calib('NR100', 1e-6)}.pfa_target_emp", "{:.0e}")

    #: 명목 1e-4 에서 파형별 경험/명목 배율. '배' 는 태그 **뒤에** 붙인다(태그가 값을 덮도록).
    ratio = {b: num(None, f"{CFAR}:{_row(b, 'dpi_eca', 'op')}.ratio", "{:.2f}") + "배"
             for b, _e, _l in WFS}

    return [
        # ── 서두 6블록 ──────────────────────────────────────────────────────
        header(
            num=4,
            title="검출기: ECA · 거리도플러 · CFAR 교정",
            question="명목 Pfa 로 문턱을 세우면 실제 오경보율은 얼마가 되는가?",
            conclusion_lines=[
                f"이상적인 백색 잡음 맵에서는 명목 = 경험이다 — 배율 "
                f"{num(None, f'{CFAR}:{_white_row()}.ratio', '{:.3f}')} "
                f"(셀 {num(None, f'{CFAR}:{_white_row()}.cells', '{:,.0f}')}개).",
                f"실제 사슬(직접파 + ECA + Hann 창 + 정합필터)에서 명목 {NOM} 를 요구하면 "
                f"WiFi {ratio['WiFi80']} · LTE {ratio['LTE20']} · 5G {ratio['NR100']} 가 나온다.",
                "배율이 파형마다 다르므로, 교정하지 않은 3파형 비교는 **서로 다른 실제 오경보율에서** "
                "Pd 를 견주는 것이다. 즉 비교가 아니다.",
                f"원인은 이웃 셀 상관이다 — Hann 창(도플러축)과 과표본(거리축). 둘 다 끄면 배율이 "
                f"{num(None, f'{CFAR}:{_ctrl_row("control_whitened_mf_rect_NR100")}.ratio', '{:.2f}')}"
                f"배로 돌아온다.",
                "교정표는 JSON 에 있고 검출 파이프라인이 그것을 직접 읽는다 "
                "(`src/passive_process.py:283`).",
            ],
            claims=[
                f"**실제 사슬의 경험적 Pfa** — 파형 · 명목값마다 측정했다(파형 · 모드당 맵 {N_CHAIN}개)",
                "**CFAR 문턱 상수 자체는 이론과 일치한다** — 상대오차 "
                + num(None, f"{CFAR}:alpha_audit.{GT}.rel_err", "{:.1e}"),
                "**배율의 원인** — 대조군으로 확정했다(Hann 제거 · 백색화 정합필터)",
                "**교정표** — 목표 경험 Pfa → 줘야 할 명목 Pfa. 검출 코드가 이 JSON 을 소비한다",
                "**ECA 소거 깊이의 한계는 환경이지 알고리즘이 아니다** — §2 의 표",
            ],
            non_claims=[
                "**절대 Pd 수치** — 표적 σ 에 걸려 있고, σ 는 리포트 02 의 측정 앵커에서 온다",
                "**실외 클러터 환경의 Pfa** — 여기 배경은 잡음 + 광선추적 다중경로 모델이다",
                f"**명목 {PFA_1E6} 교정** — 측정 구간 밖이라 외삽하지 않고 버렸다",
                "**표적 위치 추정 성능** — 송수신 한 쌍은 관측가능하지 않다(§4)",
                "**마이크로도플러** — future work. 이 편의 검출기는 표적을 점으로 본다",
            ],
            prereq=[
                ("리포트 03", "세 조명원(WiFi · LTE · 5G NR)의 대역폭 · 기준신호 · 점유 모드"),
                ("리포트 01", "선행연구 census — 실외 실측 논문은 Pfa 를 통제할 수 없다"),
            ],
            repro=dict(
                cmd=["cd /home/yunjung/workspace/sionna2",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_cfar.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_eca.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_observability.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report04_detector.py"],
                out=[CFAR, ECA, OBS],
                runtime=f"CFAR 측정이 {RUNTIME} (GPU 1장). ECA · 관측가능성 · 그림은 각각 수 분 이내.",
                note="맵 수는 `--maps` / `--white` 로 줄일 수 있다. 줄이면 신뢰구간이 넓어진다.",
            ),
        ),

        # ── §1 사슬 ─────────────────────────────────────────────────────────
        md("## §1. 사슬 — 수신 신호가 판정이 되기까지", "",
           "패시브 검출은 네 단계다. 각 단계는 앞 단계의 잔류물을 물려받는다.", "",
           table(["단계", "하는 일", "코드"],
                 [["1. 수신", "서베일런스 + 레퍼런스 2채널", "`src/passive_process.py:42`"],
                  ["2. ECA", "직접파를 서베일런스에서 투영 제거", "`src/passive_process.py:93,124`"],
                  ["3. 거리-도플러(CAF)", "레퍼런스와 지연 · 도플러 상관", "`src/passive_process.py:133`"],
                  ["4. CA-CFAR", "이웃 셀로 문턱을 세우고 판정", "`src/passive_process.py:153`"]]),
           "",
           "직접파는 방 안에서 가장 큰 신호다. 그 크기가 DNR 이고, 2단계가 지울 대상이다."),

        _img("f1_chain", 1, "수신 신호는 어떤 단계를 거쳐 검출 판정이 되는가?",
             "passive detection chain"),

        md("### 사슬의 형상 — 파형이 정하는 것", "",
           f"거리 빈 수와 ECA 탭 수는 파형이 정한다. 도플러 빈은 세 파형 모두 {M_CPI}개다"
           "(CPI 당 프레임 수).", "",
           table_from(f"{ECA}:meta.setups",
                      [("파형", "name"), ("DNR", "dnr_db"), ("ECA 탭", "n_taps"),
                       ("거리 빈", "n_range"), ("PRF", "prf_hz"), ("Δf_d", "dfd_hz")],
                      fmt={"dnr_db": "{:.1f} dB", "n_taps": "{:.0f}", "n_range": "{:.0f}",
                           "prf_hz": "{:.0f} Hz", "dfd_hz": "{:.2f} Hz"},
                      order=[_setup("WiFi 80MHz"), _setup("LTE 20MHz"),
                             _setup("5G NR 100MHz")])),

        # ── §2 ECA ──────────────────────────────────────────────────────────
        md("## §2. ECA — 직접파를 얼마나 지우고, 무엇을 대가로 내는가", "",
           "탭을 늘리면 소거가 깊어지다가 멈춘다. 멈추는 지점은 알고리즘이 아니라 환경이 정한다.", "",
           "직접파만 있는 신호에 같은 소거기를 걸면 float64 한계까지 내려간다. "
           "측정된 다중경로를 넣으면 아래 오른쪽 값에서 포화한다.", "",
           table(["파형", "직접파만", "직접파 + 다중경로(포화)"],
                 [[label,
                   num(None, f"{ECA}:{_s1_deepest(ename)}.depth_dpi_db", "{:.1f}", "dB"),
                   num(None, f"{ECA}:{_s1_deepest(ename)}.depth_full_db", "{:.1f}", "dB")]
                  for _b, ename, label in WFS])),

        _img("f2_eca_depth", 2, "ECA 소거 깊이의 한계를 정하는 것은 알고리즘인가 환경인가?",
             "ECA cancellation depth vs taps"),

        md("### ECA 의 대가 — 0-도플러 노치", "",
           "ECA 는 지연만 다른 성분을 전부 지운다. 표적이 느리면 표적도 같이 지워진다.", "",
           "노치 폭은 Δf_d 에 비례한다 — 3 dB 손실 지점은 f_d/Δf_d = "
           f"{num(None, f'{ECA}:{_s4('5G NR 100MHz', 48)}.fd_3db_over_dfd', '{:.3f}')} "
           "로 세 파형이 같다. λ 가 다르므로 속도 문턱은 파형마다 다르다 — CPI 프레임 "
           f"{num(None, f'{ECA}:{_s4('WiFi 80MHz', 48)}.M', '{:.0f}')}개에서 WiFi 는 "
           f"{num(None, f'{ECA}:{_s4('WiFi 80MHz', 48)}.v_3db_ms', '{:.2f}', 'm/s')} "
           "아래를 못 본다(그림 3b).", "",
           "정적 산란체는 ECA 뒤에서 죽은 파라미터다 — 클러터를 "
           f"{num(None, f'{ECA}:{_clutter_max()}.scale', '{:.0f}')}배까지 키워도 SCR 변화폭은 "
           f"{num(None, f'{ECA}:S5_clutter_dead.scr_span_db', '{:.1e}', 'dB')} 다."),

        _img("f3_eca_notch", 3, "ECA 가 클러터와 함께 지우는 표적은 얼마나 느린 표적인가?",
             "zero-Doppler notch"),

        # ── §3 CFAR 교정 ────────────────────────────────────────────────────
        md("## §3. CFAR 교정 — 명목 Pfa 는 경험 Pfa 가 아니다", "",
           "⭐ **이 절이 이 프로젝트에서 가장 방어하기 쉬운 결과다.** 실외 실측 논문은 Pfa 를 "
           "통제할 수 없고, OpenISAC 논문에는 CFAR · 오경보 · 검출확률이 등장하지 않는다"
           "(리포트 01 census). Pfa 교정은 통제된 시뮬레이션만 할 수 있는 일이다.", "",
           "검출기 자체는 문제가 없다. 문턱 상수는 이론값과 "
           f"{num(None, f'{CFAR}:alpha_audit.{GT}.rel_err', '{:.1e}')} 안에서 같다. "
           f"평탄한 맵에서 오검출: "
           f"{num(None, f'{CFAR}:alpha_audit.{GT}.any_det_on_flat_map')}.", "",
           f"이상적 백색 맵 {N_WHITE}장에서 경험/명목은 "
           f"{num(None, f'{CFAR}:{_white_row()}.ratio', '{:.3f}')} 다. "
           "실제 사슬에 걸면 그 눈금이 어긋난다. "
           f"이 절의 숫자는 전부 GPU {RUNTIME} 측정이다."),

        _img("f4_pfa", 4, "명목 Pfa 를 요구하면 실제로는 몇 배의 오경보가 나오는가?",
             "nominal vs empirical Pfa"),

        md("### 교정표 — 목표 경험 Pfa 를 얻으려면 명목값을 얼마로 줘야 하나", "",
           f"운용 명목값은 {NOM} 다. 아래 두 열은 그 값에서의 측정 결과다.", "",
           table(["파형", "경험/명목 배율", "경험 1e-4 를 얻으려면 줄 명목 Pfa"],
                 [[label, ratio[b],
                   num(None, f"{CFAR}:{_calib(b, 1e-4)}.pfa_nominal_needed", "{:.3e}")]
                  for b, _e, label in WFS]),
           "",
           "표의 두 열이 파형마다 다르다는 것이 §3 의 전부다. 같은 명목값을 줘도 LTE 는 5G 보다 "
           "훨씬 많이 울린다.", "",
           "`src/passive_process.py:283` 이 이 JSON 을 직접 읽고, `pfa_nominal_for()`"
           "(`src/passive_process.py:338`)가 파형별 명목값을 돌려준다. 외삽 구간은 버린다."),

        code("# 교정표를 실제로 소비하는 지점 — src/passive_process.py:283,338",
             "import os, sys",
             "sys.path.insert(0, os.path.join(os.getcwd(), 'src'))",
             "from passive_process import pfa_nominal_for",
             "",
             "for std in ('wifi', 'lte', 'nr'):",
             "    print(f'{std:4s}  경험 1e-4 목표 → 명목 {pfa_nominal_for(std, 1e-4):.3e}')"),

        md("### 원인 — 검출기 결함이 아니라 셀 상관", "",
           "CA-CFAR 는 훈련셀이 서로 독립이라고 가정한다. 사슬은 그 가정을 두 곳에서 깬다 — "
           "slow-time Hann 창이 도플러축을, 과표본이 거리축을 묶는다.", "",
           "대조군이 원인을 확정한다(5G NR, 잡음 맵). 둘 다 끄면 눈금이 돌아온다.", "",
           table(["대조군", "경험/명목"],
                 [["기준 (Hann + 정합필터)",
                   num(None, f"{CFAR}:{_row('NR100', 'noise', 'op')}.ratio", "{:.2f}")],
                  ["Hann 제거 (rect 창)",
                   num(None, f"{CFAR}:{_ctrl_row('control_rect_window_NR100')}.ratio", "{:.2f}")],
                  ["백색화 정합필터 (거리축 평탄)",
                   num(None, f"{CFAR}:{_ctrl_row('control_whitened_mf_NR100')}.ratio", "{:.2f}")],
                  ["둘 다 제거",
                   num(None, f"{CFAR}:{_ctrl_row('control_whitened_mf_rect_NR100')}.ratio",
                       "{:.2f}")]])),

        _img("f5_cause", 5, "명목과 경험 사이의 배율을 만드는 것은 무엇인가?",
             "cell correlation controls"),

        md("### 형상 규약 — 어기면 교정표가 무의미해진다", "",
           "거리창은 ECA 탭 안에 있어야 하고, 0-도플러 행은 마스킹해야 한다(운용 폭 "
           f"{num(None, f'{CFAR}:meta.zd_mask_operational', '{:.0f}')}).", "",
           f"창을 {num(None, f'{CFAR}:meta.n_range_wide', '{:.0f}')} 빈으로 넓히면 같은 명목 Pfa "
           "에서 배율이 두 자릿수로 커진다. `check_detector_config()`"
           "(`src/passive_process.py:383`)가 이 조건을 검사한다.", "",
           table(["파형", "운용 창", "넓은 창"],
                 [[label,
                   num(None, f"{CFAR}:{_row(b, 'dpi_eca', 'op')}.ratio", "{:.2f}") + "배",
                   num(None, f"{CFAR}:{_row(b, 'dpi_eca', 'wide')}.ratio", "{:.1f}") + "배"]
                  for b, _e, label in WFS])),

        # ── §4 분해능 · 관측가능성 ──────────────────────────────────────────
        md("## §4. 분해능 · 정확도 · 관측가능성", "",
           "분해능은 두 표적을 가르는 능력이고, 정확도는 한 표적을 얼마나 정밀히 찍는가다.", "",
           "분해능은 대역폭이 정하며 SNR 로 좋아지지 않는다. 정확도는 SNR 이 정한다. "
           "바이스태틱 규약은 ΔR_b = c/B 다(R_b = c·τ, 계수 2 없음)."),

        _img("f6_resolution", 6, "분해능과 정확도 중 대역폭이 정하는 것은 어느 쪽인가?",
             "resolution vs accuracy"),

        md("### 조명원별 셀 크기와 CRLB", "",
           "5G 의 상시 기준신호(SSB)는 대역폭이 좁아 셀이 크다. 같은 반송파라도 기준신호를 "
           "PRS 로 바꾸면 셀이 작아진다.", "",
           "도플러 분해능은 Δf_d = 1/T_CPI 다 — 아래 표의 형상은 T_CPI = "
           f"{num(None, f'{OBS}:cells[0].t_cpi', '{:.3f}', 's')}, Δf_d = "
           f"{num(None, f'{OBS}:cells[0].dfd_hz', '{:.2f}', 'Hz')}. "
           "그 아래 속도는 §2 의 노치가 먼저 지운다.", "",
           table_from(f"{OBS}:cells",
                      [("조명원 / 기준신호", "label"), ("기준 대역폭", "ref_bw_mhz"),
                       ("ΔR_b (분해능)", "drb_m"), ("σ_Rb (정확도)", "sigma_rb_m"),
                       ("σ_fd", "sigma_fd_hz")],
                      fmt={"ref_bw_mhz": "{:.2f} MHz", "drb_m": "{:.2f} m",
                           "sigma_rb_m": "{:.4f} m", "sigma_fd_hz": "{:.3f} Hz"})),

        md("### 관측가능성 — 송수신 한 쌍으로는 위치가 안 풀린다", "",
           f"판정: **{num(None, f'{OBS}:summary.verdict')}**. TX–RX 기저선 "
           f"{num(None, f'{OBS}:meta.L_m', '{:.2f}', 'm')} 형상에서, 한 순간의 (R_b, f_d) 는 "
           f"3차원 위치에 대해 랭크 "
           f"{num(None, f'{OBS}:summary.snapshot_fim_rank', '{:.0f}')} 다.", "",
           "TX–RX 기저선을 축으로 표적을 돌려도 R_b 와 f_d 가 바뀌지 않는다 — 최대 변화 "
           f"{num(None, f'{OBS}:summary.exact_rotation_max_dRb_m', '{:.1e}', 'm')}. "
           "그 방향은 어떤 SNR 에서도, 어떤 관측시간에도 정보를 담지 않는다.", "",
           table_from(f"{OBS}:fixes",
                      [("형상", None), ("유효 랭크 (/6)", "rank_practical"),
                       ("위치 RMS 오차", "pos_rms_m")],
                      fmt={"rank_practical": "{:.0f}", "pos_rms_m": "{:.2f} m"},
                      order=["1RX (baseline)", "2RX",
                             "1RX + AoA(1deg)", "1RX + AoA(5deg)"])),

        _img("f7_observability", 7, "송수신 한 쌍으로 표적 위치를 풀 수 있는가?",
             "observability of one TX-RX pair"),

        # ── 이 편의 한계 ────────────────────────────────────────────────────
        limits([
            (f"명목 {PFA_1E6} 교정점이 없다 — 측정 구간 밖이라 버렸다",
             "`benchmark/verify_cfar.py --maps` 를 한 자릿수 올려 재측정. "
             "`calib_op_mask1.points` 의 `extrapolated` 가 False 가 되면 쓸 수 있다"),
            ("교정이 잡음 + 광선추적 다중경로 위에서만 측정됐다",
             "실외 클러터를 넣은 맵으로 같은 스윕을 돌려 배율이 유지되는지 확인 — "
             "리포트 06 의 측정 계획이 그 조건을 정한다"),
            ("Pfa 는 교정됐지만 Pd 절대값은 표적 σ 에 걸려 있다",
             "리포트 05 의 검출 결과는 리포트 02 의 측정 앵커 σ 위에서만 읽을 것"),
            ("송수신 한 쌍 형상은 관측가능하지 않다",
             f"수신기 2대면 랭크 {num(None, f'{OBS}:summary.fix_2rx_rank', '{:.0f}')} 로 복구되고 "
             f"위치 RMS 가 {num(None, f'{OBS}:summary.fix_2rx_pos_rms_m', '{:.2f}', 'm')} 가 된다 — "
             "§4 표의 2RX 행 형상으로 검출 실험을 재설계"),
            (f"0-도플러 마스크 폭이 운용값 "
             f"{num(None, f'{CFAR}:meta.zd_mask_operational', '{:.0f}')} 로 고정돼 있다",
             f"넓은 창에서 폭 3 은 과보정한다(배율 "
             f"{num(None, f'{CFAR}:{_row('LTE20', 'dpi_eca', 'wide', mask=3)}.ratio', '{:.2f}')}). "
             "훈련셀에서도 그 행을 빼는 CFAR 변형을 만들고 재측정 — `src/passive_process.py:352`"),
            ("표적을 점 하나로 본다 — 마이크로도플러 성분이 없다",
             "회전 블레이드는 별건의 검증이 필요하다. future work"),
        ], sec="§5."),
    ]


if __name__ == "__main__":
    rep = build_notebook(NB, blocks(), strict=True)
    print(f"\n→ {os.path.relpath(NB, ROOT)}  "
          f"(md {rep['md_cells']}/{rep['caps']['md_cells']} · "
          f"code {rep['code_cells']} · 그림 {rep['figures']}/{rep['caps']['figures']} · "
          f"출처태그 {rep['provenance_tags']}개 · 권고 {len(rep['advisories'])}건)")
