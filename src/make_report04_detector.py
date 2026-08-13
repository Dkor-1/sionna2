# -*- coding: utf-8 -*-
"""make_report04_detector.py — 리포트 04(검출기) 노트북을 만든다

    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report04_detector.py
    → report04_detector.ipynb

계약서 두 장이 동시에 걸린다.
  · `docs/REBUILD_2026-07-30.md` §5  — 서술 규약(구현 `src/report_style.py`)
      여는 블록 = 한 일 / 결과 / 방법 / 재현 / 앞 편에서.
      숫자는 전부 `num()`/`table_from()` 으로 JSON 에서 뽑는다. 손으로 친 숫자 0개.
      마지막 절은 `next_steps()` — 다음에 할 일 | 그러면 결정되는 것 | 어디서.
  · `docs/PAPER_SPEC.md` §4 — 논문 참고자료 규격(구현 `src/paper_kit.py`)
      §4.1 편 머리 `논문 대응` 블록 → `attach(header(…), paper_map(…))` 로 **셀을 안 늘리고** 붙인다.
      §4.2 편 끝 `방어선` 표 · §4.4 `방법 문단` · §4.5 논문 형식 인용 → `paper_appendix()` 셀 하나.
      §4.3 게재 품질 그림 → `src/viz_report04_detector.py` 가 벡터 PDF + 400 dpi PNG 로 낸다.

이 편이 먹이는 논문 절: **IV. Detection Chain**. 공급물은 ECA · 거리-도플러 CAF · **Pfa 교정**이다.

근거 JSON
    outputs/verify_cfar.json          §3 CFAR 교정 (GPU 측정 2717 s)
    outputs/verify_eca.json           §1 사슬 형상 · §2 ECA
    outputs/verify_observability.json §4 분해능 · 관측가능성
    outputs/prior_census.json         §3 선행 census 의 용어 빈도

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

from paper_kit import (                                          # noqa: E402
    attach, cite, cite_ref, defence, figure_md, methods, paper_appendix, paper_map,
)
from report_style import (                                       # noqa: E402
    ContractError, build_notebook, code, fetch, header, md, next_steps,
    num, table, table_from,
)
from viz_report04_detector import PAPER_CAPTIONS                 # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NB = os.path.join(ROOT, "report04_detector.ipynb")

CFAR = "outputs/verify_cfar.json"
ECA = "outputs/verify_eca.json"
OBS = "outputs/verify_observability.json"
CENSUS = "outputs/prior_census.json"
FIGDIR = "outputs/figures"
REPORT = "report04_detector"

#: 파형 3종. (verify_cfar 밴드 키, verify_eca 셋업 이름, 표에 쓸 짧은 이름)
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
    """탭을 가장 많이 준 행 = 측정된 소거 깊이의 바닥."""
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


def _paper(key: str) -> str:
    return f"papers[{_find(fetch(f'{CENSUS}:papers'), key=key)}]"


def _img(name: str, fig_no: int, question: str):
    """그림 한 장 — 노트북엔 **질문 캡션**, 논문엔 **완결 문장 캡션**(§4.3)."""
    return figure_md(f"{FIGDIR}/report04_{name}.png", fig_no, question,
                     paper_caption=PAPER_CAPTIONS[name], report=REPORT)


# --------------------------------------------------------------------------- #
#  블록
# --------------------------------------------------------------------------- #
def blocks():
    M_CPI = num(None, f"{CFAR}:meta.M_cpi", "{:.0f}")
    ZDN = num(None, f"{CFAR}:meta.zd_mask_operational", "{:.0f}")
    N_WIDE = num(None, f"{CFAR}:meta.n_range_wide", "{:.0f}")
    N_CHAIN = num(None, f"{CFAR}:meta.n_maps_chain", "{:,.0f}")
    N_WHITE = num(None, f"{CFAR}:meta.n_maps_white", "{:,.0f}")
    RUNTIME = num(None, f"{CFAR}:meta.runtime_s", "{:.0f}", "s")
    NOM = num(None, f"{CFAR}:{_row('NR100', 'dpi_eca', 'op')}.pfa_nom", "{:.0e}")
    PFA_1E6 = num(None, f"{CFAR}:{_calib('NR100', 1e-6)}.pfa_target_emp", "{:.0e}")
    REL_ERR = num(None, f"{CFAR}:alpha_audit.{GT}.rel_err", "{:.1e}")
    N_INT = num(None, f"{CFAR}:alpha_audit.{GT}.N_interior", "{:.0f}")
    W_RATIO = num(None, f"{CFAR}:{_white_row()}.ratio", "{:.3f}")
    W_CELLS = num(None, f"{CFAR}:{_white_row()}.cells", "{:,.0f}")
    RECT = num(None, f"{CFAR}:{_ctrl_row('control_rect_window_NR100')}.ratio", "{:.2f}")
    BOTH = num(None, f"{CFAR}:{_ctrl_row('control_whitened_mf_rect_NR100')}.ratio", "{:.2f}")
    WIDE_NR = num(None, f"{CFAR}:{_row('NR100', 'dpi_eca', 'wide')}.ratio", "{:.2f}")
    PFA_HI = num(None, f"{CFAR}:meta.pfa_nominal[0]", "{:.0e}")
    PFA_LO = num(None, f"{CFAR}:meta.pfa_nominal[8]", "{:.0e}")
    DTYPE = fetch(f"{CFAR}:meta.dtype")

    #: 명목 1e-4 에서 파형별 경험/명목 배율. '배' 는 태그 **뒤에** 붙인다(태그가 값을 덮도록).
    ratio_raw = {b: num(None, f"{CFAR}:{_row(b, 'dpi_eca', 'op')}.ratio", "{:.2f}")
                 for b, _e, _l in WFS}
    ratio = {b: v + "배" for b, v in ratio_raw.items()}
    #: 경험 1e-4 를 얻으려면 줘야 할 명목 Pfa
    calib = {b: num(None, f"{CFAR}:{_calib(b, 1e-4)}.pfa_nominal_needed", "{:.2e}")
             for b, _e, _l in WFS}
    #: 사슬 형상 — DNR 과 ECA 탭
    DNR = {e: num(None, f"{ECA}:meta.setups[{_setup(e)}].dnr_db", "{:.1f}", "dB")
           for _b, e, _l in WFS}
    TAPS = {e: num(None, f"{ECA}:meta.setups[{_setup(e)}].n_taps", "{:.0f}")
            for _b, e, _l in WFS}
    #: ECA 소거 바닥 — 직접파만 / 측정된 다중경로 포함
    DEEP_DPI = {e: num(None, f"{ECA}:{_s1_deepest(e)}.depth_dpi_db", "{:.1f}", "dB")
                for _b, e, _l in WFS}
    DEEP_FULL = {e: num(None, f"{ECA}:{_s1_deepest(e)}.depth_full_db", "{:.1f}", "dB")
                 for _b, e, _l in WFS}

    OI = _paper("openisac")
    N_PAPERS = num(None, f"{CENSUS}:meta.n_papers", "{:.0f}")
    TOT_PAGES = num(None, f"{CENSUS}:counts.total_pages", "{:.0f}")
    ZERO_CFAR = num(None, f"{CENSUS}:counts.zero_cfar_and_falsealarm", "{:.0f}")
    N_DETECT = num(None, f"{CENSUS}:counts.claims_detection", "{:.0f}")

    #: §2 노치 — 3 dB 지점(무차원)과 파형별 속도 문턱
    FD3DB = num(None, f"{ECA}:{_s4('5G NR 100MHz', 48)}.fd_3db_over_dfd", "{:.3f}")
    M48 = num(None, f"{ECA}:{_s4('WiFi 80MHz', 48)}.M", "{:.0f}")
    V3 = {e: num(None, f"{ECA}:{_s4(e, 48)}.v_3db_ms", "{:.2f}", "m/s")
          for _b, e, _l in WFS}

    #: §4 관측가능성
    RANK1 = num(None, f"{OBS}:summary.snapshot_fim_rank", "{:.0f}")
    RANK2 = num(None, f"{OBS}:summary.fix_2rx_rank", "{:.0f}")
    RMS2 = num(None, f"{OBS}:summary.fix_2rx_pos_rms_m", "{:.2f}", "m")

    # ── §4.1 논문 대응 — 여는 블록 안으로 들어간다(셀 +0) ───────────────────
    PMAP = paper_map(
        "IV. Detection Chain",
        claim="세 파형의 CFAR 문턱을 GPU 몬테카를로로 측정한 경험 오경보율에 맞춰 교정해, "
              "세 조명원이 같은 실제 오경보율 위에서 비교되게 했다.",
        evidence=["그림 1", "그림 4", "그림 5", "§3 운용 형상 교정표",
                  f"{CFAR}:chain.NR100.dpi_eca.calib_op_mask1.points",
                  f"{CFAR}:alpha_audit.{GT}.rel_err",
                  f"{ECA}:S1_depth_vs_taps",
                  f"{CENSUS}:counts.zero_cfar_and_falsealarm"],
        qualifications=[
            "교정 배율은 형상이 정한다 — 운용 창과 넓은 창의 값이 달라 형상마다 다시 잰다(§3)",
            f"측정 구간은 명목 {PFA_LO} ~ {PFA_HI} 다. 그 밖의 운용점은 외삽으로 표시된다",
        ],
        report=REPORT)

    # ── §4.4 방법 문단 — 논문(영문)으로 그대로 옮겨가는 유일한 산문 ─────────
    METHOD_PARA = methods(
        "All three illuminators are processed by one identical chain. "
        "The surveillance channel carries the target echo, the direct-path interference at "
        f"DNR = {DNR['WiFi 80MHz']} / {DNR['LTE 20MHz']} / {DNR['5G NR 100MHz']} "
        "for WiFi / LTE / 5G NR, static clutter and thermal noise, while the reference "
        "channel carries the transmitted frame. "
        "A standard extensive cancellation algorithm removes the direct path by a single "
        "least-squares projection of the whole CPI onto the subspace spanned by delayed "
        f"copies of the reference, with n_taps = {TAPS['WiFi 80MHz']} / "
        f"{TAPS['LTE 20MHz']} / {TAPS['5G NR 100MHz']}. "
        "The cross-ambiguity function is then formed frame by frame: a fast-time matched "
        "filter against the reference gives one range profile per frame, and a Hann-windowed "
        f"slow-time FFT over M = {M_CPI} frames gives the Doppler axis, so the Doppler bin is "
        "PRF / M and the unambiguous Doppler span is plus or minus PRF / 2. "
        "Bistatic range follows R_b = c tau with no factor of two, and the declared range "
        "resolution is c / B_ref. "
        f"Detection uses a two-dimensional cell-averaging CFAR with the {GT} guard and "
        f"training region (N = {N_INT} interior training cells) and the {ZDN} zero-Doppler "
        "row masked; the threshold constant reproduces its analytic value to a relative "
        f"error of {REL_ERR}. "
        f"Calibration runs {N_CHAIN} independent range-Doppler maps per waveform at each of "
        f"nine nominal rates from {PFA_LO} to {PFA_HI}, counts false-alarm cells, and inverts "
        "the measured log-log nominal-to-empirical curve to obtain the nominal rate that "
        f"delivers a target empirical rate; the measurement costs {RUNTIME} on one GPU and "
        f"the arithmetic is {DTYPE} throughout.",
        tools=["Python 3.12.13", "PyTorch 2.12.1", "CUDA 13.0"],
        report=REPORT)

    # ── §4.2 방어선 — 심사자가 때릴 지점과 우리 답 ──────────────────────────
    DEFENCE = defence([
        ("명목 오경보율과 경험 오경보율은 파형마다 다른 배율로 어긋나고, 그 배율을 재서 "
         "CFAR 문턱을 교정했다.",
         f"그림 4 · `{CFAR}:chain.NR100.dpi_eca.op.rows`",
         "그 배율은 CFAR 구현이 틀린 흔적이다.",
         f"문턱 상수는 이론식과 상대오차 {REL_ERR} 안에서 같고, 이상적 백색 맵 {N_WHITE}장 "
         f"(셀 {W_CELLS}개)에서 경험/명목 = {W_RATIO} 로 눈금이 1 에 선다."),

        ("교정 없는 세 파형 비교는 서로 다른 실제 오경보율 위에서 이뤄진다.",
         f"그림 4 · `{CFAR}:chain.LTE20.dpi_eca.calib_op_mask1.points`",
         "배율이 두 배 안팎이면 순위가 뒤집힐 만큼 큰가.",
         f"명목 {NOM} 에서 실제 오경보율이 WiFi {ratio['WiFi80']} · LTE {ratio['LTE20']} · "
         f"5G {ratio['NR100']} 로 갈리고, 교정은 명목값을 WiFi {calib['WiFi80']} · "
         f"LTE {calib['LTE20']} · 5G {calib['NR100']} 로 바꿔 셋을 같은 경험 {NOM} 위에 올린다."),

        ("배율의 원인은 slow-time Hann 창이 만드는 도플러축 셀 상관이다.",
         f"그림 5 · `{CFAR}:control_rect_window_NR100`",
         "셀 상관은 어느 검출기에나 있다 — 원인 지목의 근거가 약하다.",
         f"대조군이 확정한다 — Hann 을 rect 창으로 바꾸면 {RECT}, 백색화 정합필터까지 끄면 "
         f"{BOTH} 로 눈금이 1 로 돌아온다."),

        ("ECA 소거 깊이의 바닥은 환경이 정한다.",
         f"그림 2 · `{ECA}:S1_depth_vs_taps`",
         "탭이 부족해서 얕게 나온 것이다.",
         f"탭 1~96 스윕에서 깊이가 포화한다 — 직접파만 든 신호에 같은 소거기를 걸면 "
         f"{DEEP_DPI['5G NR 100MHz']}(float64 한계)까지 내려가고, 측정된 다중경로를 넣으면 "
         f"{DEEP_FULL['5G NR 100MHz']} 에서 멈춘다."),

        ("ECA 는 0-도플러 노치를 대가로 내며, 3 dB 지점은 세 파형이 같다.",
         f"그림 3 · `{ECA}:S4_target_loss`",
         "노치가 드론 속도대를 통째로 먹으면 비교 자체가 무의미하다.",
         f"3 dB 지점은 f_d/Δf_d = {FD3DB} 이고, 프레임 {M48}개에서 속도 문턱은 "
         f"WiFi {V3['WiFi 80MHz']} · LTE {V3['LTE 20MHz']} · 5G {V3['5G NR 100MHz']} 다 — "
         "그 위 속도는 온전히 남는다."),

        ("오경보율 교정은 같은 배경을 수만 번 다시 만드는 통제 시뮬레이션이 한다.",
         f"§3 · `{CENSUS}:counts.zero_cfar_and_falsealarm`",
         "실측 플랫폼이 더 현실적인 근거다.",
         f"census {N_PAPERS}편 · 전문 {TOT_PAGES}쪽에서 `CFAR` 와 `false alarm` 이 모두 0회인 "
         f"논문이 {ZERO_CFAR}편이고 검출을 주장한 논문은 {N_DETECT}편이다. 실외 실측은 배경을 "
         f"주어진 대로 받고, 이 편은 맵 {N_CHAIN}장을 다시 만들어 그 대조를 세운다."),

        ("교정표는 형상마다 다시 잰다.",
         f"§3 · `src/passive_process.py:383` · `{CFAR}:chain.NR100.dpi_eca.wide`",
         "그럼 이 표는 이 형상 하나에서만 쓰는 값이다.",
         f"그렇다 — 같은 파형이 운용 창에서 {ratio['NR100']}, 넓은 창({N_WIDE} 빈)에서 "
         f"{WIDE_NR}배다. `check_detector_config()`(`src/passive_process.py:383`)가 형상 조건을 "
         "강제하고, 자유공간 형상은 `src/freespace_detect.py:711` 이 다시 잰다."),

        ("송수신 한 쌍의 한 순간 관측량은 3차원 위치에 대해 랭크 2 를 만들고, 수신기 2대가 "
         "랭크 6 을 만든다.",
         f"그림 7 · `{OBS}:summary`",
         "그건 기하 문제이고 검출기 성능과 별개다.",
         f"검출 판정은 (R_b, f_d) 셀에서 난다 — 두 양이 위치로 풀리는 조건을 FIM 랭크 "
         f"{RANK1} → {RANK2} 로 적어두면 검출 결과가 말하는 범위가 정해진다(2 Rx 위치 RMS "
         f"{RMS2})."),
    ], report=REPORT)

    # ── §4.5 논문 형식 인용 (게재상태 포함) ─────────────────────────────────
    CITES = [
        cite("F. Colone, C. Palmarini, T. Martelli, E. Tilli",
             "Sliding Extensive Cancellation Algorithm for Disturbance Removal in Passive Radar",
             "IEEE Transactions on Aerospace and Electronic Systems",
             volume="52(3)", pages="1309-1326", year=2016, status="published",
             note="ECA-S. 이 편의 제거단은 CPI 1회 최소제곱 사영의 standard ECA 다 "
                  "— src/passive_process.py:13"),
        cite("Z. Zhou et al.",
             "OpenISAC: An Open-Source Real-Time Experimentation Platform for OFDM-ISAC",
             "arXiv preprint", year=2026, status="preprint", arxiv="2601.03535v2",
             note="전문에서 CFAR · false alarm · detection probability 0회"),
        cite("R. Liu et al.",
             "Clutter-Aware Integrated Sensing and Communication: Models, Methods, "
             "and Future Directions",
             "Proceedings of the IEEE", volume="114(1)", pages="52-91", year=2026,
             status="published", note="census 에서 CFAR 를 쓴 게재 논문"),
        cite("H. Liu et al.",
             "DMSNet: Cross-Band Learning for Multi-Target Sensing in Multi-Band ISAC",
             "arXiv preprint", year=2026, status="preprint", arxiv="2607.17655v1",
             note="census 에서 CFAR 빈도가 가장 높은 프리프린트"),
        cite_ref("rzewuski",
                 note="패시브 WiFi 드론 검출의 종단 산출물 — FDTD RCS → 커버리지 → 50 m OTA"),
    ]

    return [
        # ── 여는 블록 (+ §4.1 논문 대응) ────────────────────────────────────
        attach(header(
            num=4,
            title="검출기: CFAR 를 경험 Pfa 로 교정했다",
            did="운용 형상의 검출 사슬에서 경험적 오경보율을 GPU 몬테카를로로 측정하고, "
                "세 파형의 CFAR 문턱(둘레 잡음을 보고 스스로 오르내려 오경보율을 일정하게 "
                "붙잡는 문턱)을 그 측정값에 맞춰 교정했다.",
            results=[
                f"GPU {RUNTIME} 동안 파형·모드마다 거리-도플러 맵 {N_CHAIN}장을 돌려 "
                f"경험 Pfa 를 측정했다.",
                f"이상적 백색 맵 {N_WHITE}장(셀 {W_CELLS}개)에서 경험/명목 = {W_RATIO} — "
                f"CFAR 구현의 눈금을 먼저 확정했다.",
                f"운용 형상(CPI 프레임 {M_CPI} · `{GT}` · 0-도플러 마스크 {ZDN}빈)에서 명목 "
                f"{NOM} 를 주면 WiFi {ratio['WiFi80']} · LTE {ratio['LTE20']} · "
                f"5G {ratio['NR100']}로 울린다.",
                f"그 형상의 교정표를 만들었다 — 경험 {NOM} 를 얻는 명목값은 WiFi "
                f"{calib['WiFi80']} · LTE {calib['LTE20']} · 5G {calib['NR100']} 다. "
                f"`src/experiment_detection.py:358` 과 `src/experiment_x410.py:175` 가 "
                f"`src/passive_process.py:283` 을 거쳐 그 표를 읽는다.",
                f"배율의 원인은 slow-time Hann 창이 만드는 도플러축 셀 상관이다 — "
                f"rect 창으로 두면 5G 가 {RECT}배로 내려온다.",
            ],
            method=[
                ("경험 Pfa",
                 f"파형·명목값마다 거리-도플러 맵 {N_CHAIN}장에 CA-CFAR 를 걸어 "
                 f"오경보 셀을 세었다 (GPU, {RUNTIME})"),
                ("문턱 상수",
                 f"CA-CFAR α 를 이론식과 대조 — 상대오차 {REL_ERR}"),
                ("배율의 원인",
                 "대조군 2종 — slow-time Hann 제거(도플러축), 백색화 정합필터(거리축)"),
                ("운용 형상 교정표",
                 "측정한 명목–경험 곡선을 역보간. 측정 구간 안의 점만 남긴다. "
                 "자유공간 기하는 형상이 달라 `src/freespace_detect.py:711` 이 거기서 다시 잰다"),
                ("ECA(직접파를 빼내는 소거기) 소거 깊이",
                 "탭 수 1~96 스윕 × (직접파만 / 측정된 다중경로 포함) 두 조건"),
                ("분해능 · 관측가능성",
                 "Fisher 정보행렬(관측이 미지수에 담은 정보량)의 랭크와 "
                 "CRLB(추정 오차가 내려갈 수 있는 이론 하한)를 기하에서 계산"),
            ],
            prereq=[
                ("리포트 03", "세 조명원(WiFi · LTE · 5G NR)의 대역폭 · 기준신호 · 점유 모드"),
                ("리포트 01", "게재 선행 census — 각 논문이 표적 산란을 어떻게 다뤘는가"),
            ],
            repro=dict(
                cmd=["cd /workspace/sionna",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_cfar.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_eca.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_observability.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report04_detector.py"],
                out=[CFAR, ECA, OBS],
                runtime=f"CFAR 측정이 {RUNTIME} (GPU 1장). ECA · 관측가능성 · 그림은 각각 수 분.",
                note="맵 수는 `--maps` / `--white` 로 줄인다. 줄이면 신뢰구간이 넓어진다.",
            ),
        ), PMAP),

        # ── §1 사슬 ─────────────────────────────────────────────────────────
        md("## §1. 사슬 — 수신 신호가 판정이 되기까지", "",
           "패시브 검출은 네 단계다. 각 단계는 앞 단계의 잔류물을 물려받는다.", "",
           table(["단계", "하는 일", "코드"],
                 [["1. 수신", "서베일런스(표적 쪽을 보는 채널) + 레퍼런스(조명원을 직접 받는 채널) "
                            "2채널", "`src/passive_process.py:42`"],
                  ["2. ECA", "직접파를 서베일런스에서 투영 제거", "`src/passive_process.py:93,124`"],
                  ["3. 거리-도플러(CAF)", "레퍼런스와 지연 · 도플러 상관", "`src/passive_process.py:133`"],
                  ["4. CA-CFAR", "이웃 셀로 문턱을 세우고 판정", "`src/passive_process.py:153`"]]),
           "",
           "직접파는 수신단에서 가장 큰 신호다. 그 크기가 DNR(직접파 대 잡음비)이고, "
           "2단계가 지울 대상이다."),

        _img("f1_chain", 1, "수신 신호는 어떤 단계를 거쳐 검출 판정이 되는가?"),

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
           "탭을 늘리면 소거가 깊어지다가 환경이 정한 바닥에서 멈춘다. "
           "직접파만 든 신호에 같은 소거기를 걸면 float64 한계까지 내려가고, "
           "측정된 다중경로를 넣으면 오른쪽 값에서 포화한다.", "",
           table(["파형", "직접파만", "직접파 + 다중경로(포화)"],
                 [[label, DEEP_DPI[ename], DEEP_FULL[ename]]
                  for _b, ename, label in WFS])),

        _img("f2_eca_depth", 2, "ECA 소거 깊이의 바닥을 정하는 것은 무엇인가?"),

        md("### ECA 의 대가 — 0-도플러 노치", "",
           "ECA 는 지연만 다른 성분을 함께 지운다. 3 dB 손실 지점은 f_d/Δf_d = "
           f"{FD3DB} 이고, 세 파형이 같다. 속도 문턱은 λ 가 가른다.", "",
           f"CPI 프레임 {M48}개에서 WiFi {V3['WiFi 80MHz']} · LTE {V3['LTE 20MHz']} · "
           f"5G {V3['5G NR 100MHz']} 아래가 노치 안에 들어간다(그림 3b).", "",
           "정적 산란체는 ECA 뒤에서 죽은 파라미터다 — 클러터를 "
           f"{num(None, f'{ECA}:{_clutter_max()}.scale', '{:.0f}')}배까지 키워도 SCR 변화폭은 "
           f"{num(None, f'{ECA}:S5_clutter_dead.scr_span_db', '{:.1e}', 'dB')} 다."),

        _img("f3_eca_notch", 3, "ECA 가 클러터와 함께 지우는 표적의 속도는 얼마인가?"),

        # ── §3 CFAR 교정 ────────────────────────────────────────────────────
        md("## §3. CFAR 교정 — 운용 형상에서 경험 Pfa 를 재고 문턱을 그 값에 맞췄다", "",
           "⭐ 오경보율을 명목값과 대조하려면 같은 배경을 수만 번 다시 만들어 세어야 한다. "
           "통제 시뮬레이션이 그 일을 한다. 실외 실측은 배경을 주어진 대로 받는다.", "",
           f"이 절의 모든 수는 **운용 형상** 하나에서 나온다 — DPI+ECA · 운용 거리창(§1 표) · "
           f"CPI 프레임 {M_CPI} · 훈련창 `{GT}` · 0-도플러 마스크 {ZDN}빈.", "",
           f"선행 census {N_PAPERS}편 · 전문 {TOT_PAGES}쪽에서 `CFAR` 와 `false alarm` 이 모두 "
           f"0회인 논문이 {ZERO_CFAR}편이고, 검출을 주장한 논문은 {N_DETECT}편이다. "
           f"OpenISAC(`arXiv:2601.03535v2`, preprint)은 전문 "
           f"{num(None, f'{CENSUS}:{OI}.pages', '{:.0f}')}쪽에서 `CFAR` "
           f"{num(None, f'{CENSUS}:{OI}.terms.cfar', '{:.0f}')}회 · `false alarm` "
           f"{num(None, f'{CENSUS}:{OI}.terms.false_alarm', '{:.0f}')}회 · "
           f"`detection probability` "
           f"{num(None, f'{CENSUS}:{OI}.terms.detection_probability', '{:.0f}')}회다.", "",
           f"검출기 구현의 눈금부터 확정했다 — 문턱 상수는 이론값과 상대오차 {REL_ERR} 안에서 "
           f"같고, 잡음 추정/실제 전력 = "
           f"{num(None, f'{CFAR}:alpha_audit.{GT}.noise_est_over_power', '{:.3f}')} 다. "
           f"이상적 백색 맵 {N_WHITE}장에서 경험/명목 = {W_RATIO} 다."),

        _img("f4_pfa", 4, "명목 Pfa 를 요구하면 실제로는 몇 배가 울리는가?"),

        md("### 운용 형상 교정표 — 목표 경험 Pfa 에 필요한 명목값", "",
           f"운용 명목값은 {NOM} 다. 왼쪽 열이 그 값에서 측정된 배율이고, "
           "오른쪽 열이 교정된 명목값이다.", "",
           table(["파형", "명목 1e-4 에서 경험/명목", "경험 1e-4 를 얻을 명목 Pfa"],
                 [[label, ratio[b], calib[b]] for b, _e, label in WFS]),
           "",
           "세 파형의 배율이 서로 다르다. 교정이 셋을 같은 실제 오경보율 위에 올리고, "
           "05편 §3 의 모드별 필요 SNR 표가 그 위에서 선다.", "",
           "`src/passive_process.py:283` 이 이 JSON 을 읽고, `pfa_nominal_for()`"
           "(`src/passive_process.py:338`)가 파형별 명목값을 돌려준다."),

        code("# 교정표를 실제로 소비하는 지점 — src/passive_process.py:283,338",
             "import os, sys",
             "sys.path.insert(0, os.path.join(os.getcwd(), 'src'))",
             "from passive_process import pfa_nominal_for",
             "",
             "for std in ('wifi', 'lte', 'nr'):",
             "    print(f'{std:4s}  경험 1e-4 목표 → 명목 {pfa_nominal_for(std, 1e-4):.3e}')"),

        md("### 원인 — 셀 상관", "",
           "CA-CFAR 는 훈련셀이 서로 독립이라고 가정한다. 사슬은 slow-time Hann 창으로 "
           "도플러축 셀을 묶는다 — 대조군이 그 항을 원인으로 확정한다(5G NR, 명목 1e-4).", "",
           table(["조건", "경험/명목"],
                 [["이상적 백색 맵", W_RATIO],
                  ["잡음 맵 (Hann + 정합필터)",
                   num(None, f"{CFAR}:{_row('NR100', 'noise', 'op')}.ratio", "{:.2f}")],
                  ["  └ Hann 제거 (rect 창)", RECT],
                  ["  └ 백색화 정합필터 (거리축 평탄)",
                   num(None, f"{CFAR}:{_ctrl_row('control_whitened_mf_NR100')}.ratio", "{:.2f}")],
                  ["  └ 둘 다 제거", BOTH],
                  ["전체 사슬 (직접파 + ECA)", ratio_raw["NR100"]]])),

        _img("f5_cause", 5, "명목과 경험 사이의 배율을 만드는 것은 무엇인가?"),

        md("### 형상 규약 — 교정표가 성립하는 조건", "",
           "거리창은 ECA 탭 안에 두고, 0-도플러 행 "
           f"{num(None, f'{CFAR}:meta.zd_mask_operational', '{:.0f}')}개를 마스킹한다. "
           "`check_detector_config()`(`src/passive_process.py:383`)가 두 조건을 검사한다.", "",
           table(["파형", "운용 창", "넓은 창"],
                 [[label, ratio[b],
                   num(None, f"{CFAR}:{_row(b, 'dpi_eca', 'wide')}.ratio", "{:.1f}") + "배"]
                  for b, _e, label in WFS]),
           "",
           f"창을 {N_WIDE} 빈으로 넓히면 배율이 두 자릿수가 된다. "
           "교정표는 운용 창 형상에서 측정한 값이다."),

        md("### 어느 형상의 교정표가 어디에 쓰이나", "",
           f"형상이 배율을 정한다 — 같은 파형이 운용 창에서 {ratio['NR100']}, "
           f"넓은 창에서 {WIDE_NR}배다(바로 위 표). "
           "그래서 명목–경험 관계는 형상마다 다시 잰다.", "",
           table(["형상", "무엇을 재나", "재는 코드", "그 값을 읽는 곳"],
                 [[f"운용 형상 — CPI 프레임 {M_CPI} · `{GT}` · 0-도플러 마스크 {ZDN}빈 · "
                   "운용 거리창", "이 편의 교정표", "`benchmark/verify_cfar.py`",
                   "`src/experiment_detection.py:358` · `src/experiment_x410.py:175` "
                   "→ 05편 §3 모드별 필요 SNR 표"],
                  ["자유공간 형상 — 모드별 프레임 수 · 자유공간 거리창 · 0-도플러 가드",
                   "자유공간 명목 Pfa", "`src/freespace_detect.py:711`",
                   "`src/experiment_freespace_range.py:206` → 05편 §3 R90 표"]]),
           "",
           "05편 §3 의 첫 표에 실린 명목 Pfa 는 둘째 줄에서 나온 수다 — 이 편의 교정표와 "
           "형상이 달라 값도 다르다."),

        # ── §4 분해능 · 관측가능성 ──────────────────────────────────────────
        md("## §4. 분해능 · 정확도 · 관측가능성", "",
           "분해능은 두 표적을 가르는 능력이고, 정확도는 한 표적을 찍는 정밀도다. "
           "대역폭이 분해능을, SNR 이 정확도를 정한다.", "",
           "바이스태틱 규약은 ΔR_b = c/B_ref 다 (R_b = c·τ, 계수 2 없이). "
           "03편 §1 · §2 의 거리 눈금이 같은 정의이고, 아래 표가 같은 값을 싣는다."),

        _img("f6_resolution", 6, "대역폭이 정하는 것은 분해능인가 정확도인가?"),

        md("### 조명원별 셀 크기와 CRLB", "",
           "5G 의 상시 기준신호 SSB 는 기준 대역폭 "
           f"{num(None, f'{OBS}:cells[2].ref_bw_mhz', '{:.2f}', 'MHz')} 라 셀이 "
           f"{num(None, f'{OBS}:cells[2].drb_bw_m', '{:.2f}', 'm')} 다. "
           "같은 반송파에서 PRS 로 가면 "
           f"{num(None, f'{OBS}:cells[3].ref_bw_mhz', '{:.2f}', 'MHz')} · "
           f"{num(None, f'{OBS}:cells[3].drb_bw_m', '{:.2f}', 'm')} 가 된다.", "",
           "도플러 분해능은 Δf_d = 1/T_CPI 다 — T_CPI "
           f"{num(None, f'{OBS}:cells[0].t_cpi', '{:.3f}', 's')} 에서 "
           f"{num(None, f'{OBS}:cells[0].dfd_hz', '{:.2f}', 'Hz')}. "
           "그 아래 속도는 §2 의 노치가 먼저 지운다.", "",
           table_from(f"{OBS}:cells",
                      [("조명원 / 기준신호", "label"), ("기준 대역폭 B_ref", "ref_bw_mhz"),
                       ("ΔR_b = c/B_ref", "drb_bw_m"), ("거리 빈 c/f_s", "bin_m"),
                       ("σ_Rb (정확도)", "sigma_rb_m"), ("σ_fd", "sigma_fd_hz")],
                      fmt={"ref_bw_mhz": "{:.2f} MHz", "drb_bw_m": "{:.2f} m",
                           "bin_m": "{:.2f} m",
                           "sigma_rb_m": "{:.4f} m", "sigma_fd_hz": "{:.3f} Hz"}),
           "",
           "ΔR_b 열이 선언 규약이고, 거리 빈은 표본율이 정하는 격자 간격이다. "
           "검출기가 실제로 내는 주엽 폭은 03편 §4 가 이 닫힌형 대비 비율로 싣는다."),

        md("### 관측가능성 — 수신기 2대면 위치가 풀린다", "",
           f"TX–RX 기저선 {num(None, f'{OBS}:meta.L_m', '{:.2f}', 'm')} 형상에서 한 순간의 "
           f"(R_b, f_d) 는 3차원 위치에 대해 랭크 {RANK1} 를 만든다.", "",
           "기저선을 축으로 표적을 돌리면 R_b 변화가 최대 "
           f"{num(None, f'{OBS}:summary.exact_rotation_max_dRb_m', '{:.1e}', 'm')} 다 — "
           "그 방향의 정보량은 SNR 과 관측시간에 무관하게 0 이다. 수신기를 하나 더 놓으면 "
           f"랭크 {RANK2} · 위치 RMS {RMS2} 가 된다.", "",
           table_from(f"{OBS}:fixes",
                      [("형상", None), ("유효 랭크 (/6)", "rank_practical"),
                       ("위치 RMS 오차", "pos_rms_m")],
                      fmt={"rank_practical": "{:.0f}", "pos_rms_m": "{:.2f} m"},
                      order=["1RX (baseline)", "2RX",
                             "1RX + AoA(1deg)", "1RX + AoA(5deg)"])),

        _img("f7_observability", 7, "송수신 한 쌍에 무엇을 더하면 표적 위치가 풀리는가?"),

        # ── 논문 부록 — 방법 문단 · 방어선 · 인용 (셀 하나, §5.7 예산) ──────
        paper_appendix(defence_block=DEFENCE, methods_block=METHOD_PARA,
                       citations=CITES),

        # ── 다음 단계 ───────────────────────────────────────────────────────
        next_steps([
            ("실외 클러터 배경 위에서 같은 Pfa 스윕을 돌린다",
             "교정 배율이 배경에 따라 얼마나 움직이는지 수치로 확정된다",
             "`benchmark/verify_cfar.py` · 06편 §2 측정 조건"),
            (f"맵 수를 한 자릿수 올려 명목 {PFA_1E6} 구간까지 측정한다",
             "저 Pfa 운용점의 교정값이 측정 구간 안으로 들어온다",
             "`benchmark/verify_cfar.py --maps` · `calib_op_mask1.points`"),
            ("훈련셀에서도 0-도플러 행을 빼는 CFAR 변형을 만든다",
             f"넓은 창에서 마스크 폭 3 이 만드는 배율 "
             f"{num(None, f'{CFAR}:{_row('LTE20', 'dpi_eca', 'wide', mask=3)}.ratio', '{:.2f}')}배가 "
             f"마스크 폭과 분리된다",
             "`src/passive_process.py:352`"),
            ("수신기 2대 형상으로 검출 실험을 재설계한다",
             f"위치 RMS {RMS2} 가 검출 실험에서 확인된다",
             "05편 검출 결과 · §4 표의 2RX 행"),
            ("표적 σ 를 리포트 02 의 앵커 위에서 읽는다",
             "Pd 절대값이 교정된 Pfa 와 같은 근거 위에 선다",
             "05편 검출 결과"),
            ("표적모형 민감도 실험을 이 편의 교정 배율 위에서 다시 푼다",
             "세 표적모형의 절대 소요이득이 경험 Pfa 위에 선다 — CA-CFAR 문턱은 세 팔에 같은 "
             "오프셋을 주므로 모형 간 차이는 문턱 규약에 불변이다",
             "`benchmark/verify_cfar.py` 교정표 → 05편 §3 표적모형 민감도"),
            ("회전 블레이드 산란을 별도 검증으로 세운다",
             "마이크로도플러를 검출기에 넣는 조건이 결정된다",
             "future work"),
        ]),
    ]


if __name__ == "__main__":
    rep = build_notebook(NB, blocks(), strict=True)
    print(f"\n→ {os.path.relpath(NB, ROOT)}  "
          f"(md {rep['md_cells']}/{rep['caps']['md_cells']} · "
          f"code {rep['code_cells']} · 그림 {rep['figures']}/{rep['caps']['figures']} · "
          f"출처태그 {rep['provenance_tags']}개 · 부정문 {rep['n_negatives']} · "
          f"완충어 {rep['n_hedges']} · 권고 {len(rep['advisories'])}건)")
