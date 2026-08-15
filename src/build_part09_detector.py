# -*- coding: utf-8 -*-
"""
build_part09_detector.py — 부 9 「검출기」 5편(51~55)을 짓는다
==========================================================================================
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part09_detector.py

산출
    reports/51_chain.ipynb           수신 → ECA → 거리도플러 → CFAR, 사슬의 형상은 파형이 정한다
    reports/52_eca.ipynb             탭을 늘리면 환경이 정한 바닥에서 멈추고, 그 대가가 0-도플러 노치다
    reports/53_cfar-calib.ipynb      운용 형상에서 경험 Pfa 를 재니 명목값의 1.52~2.66 배였다
    reports/54_cfar-why.ipynb        그 배율의 원인은 셀 상관이고, 교정표는 형상마다 다시 재야 한다
    reports/55_observability.ipynb   한 순간의 (R_b, f_d) 는 랭크 2 이고, 수신기를 하나 더하면 위치가 풀린다
    docs/paper/04_detector.md        논문 조각(옛 report04 의 논문 부록)
    outputs/reports_index/<anchor>.json

⚠ 행 인덱스를 하드코딩하지 않는다 — `_row()` 가 (훈련창, 0-도플러 마스크 폭, 명목 Pfa)
  조건으로 행을 찾고, 하나로 특정되지 않으면 예외를 낸다. JSON 이 다시 생성돼 행 순서가
  바뀌어도 리포트가 조용히 틀린 숫자를 싣지 않는다.
⚠ 이 파일은 서술을 옮길 뿐 아무것도 새로 계산하지 않는다. GPU·Sionna 를 쓰지 않는다.

서술 출처 — 옛 `report04_detector.ipynb` 의 셀
    c2~c4 → 51 · c5~c8 → 52 · c9~c11 → 53 · c13~c16 → 54 · c17~c21 → 55 ·
    c22 → docs/paper/04_detector.md · c12(코드) → 재현(색인 샤드의 `repro.snippet`)
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from report_registry import index_shard, nb_path, ref  # noqa: E402
from report_style import (ContractError, build_notebook, caption, fetch,  # noqa: E402
                          header, md, next_steps, num, table, table_from)

CFAR = "outputs/verify_cfar.json"
ECA = "outputs/verify_eca.json"
OBS = "outputs/verify_observability.json"
CENSUS = "outputs/prior_census.json"

FIG = "../outputs/figures"

#: 파형 3종. (verify_cfar 밴드 키, verify_eca 셋업 이름, 표에 쓸 짧은 이름)
WFS = [("WiFi80", "WiFi 80MHz", "WiFi"),
       ("LTE20", "LTE 20MHz", "LTE"),
       ("NR100", "5G NR 100MHz", "5G")]

GT = fetch(f"{CFAR}:meta.gt_default")               # guard 2x2 / train 6x6
ZD = fetch(f"{CFAR}:meta.zd_mask_operational")      # 운용 0-도플러 마스크 폭
PFA_OP = 1e-4                                       # 운용 명목 Pfa

CMD = ["cd /workspace/sionna",
       "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_cfar.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_eca.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_observability.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part09_detector.py"]


# --------------------------------------------------------------------------- #
#  인덱스 해석기 — 그 행이 정말 우리가 말한 행인지 확인하고 키를 만든다
# --------------------------------------------------------------------------- #
def _find(rows, **kw) -> int:
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
    return _rows_key(f"chain.{band}.{mode}.{win}.rows", pfa, mask)


def _white_row(pfa: float = PFA_OP, mask: int = ZD) -> str:
    return _rows_key("white.48x24.rows", pfa, mask)


def _ctrl_row(key: str, pfa: float = PFA_OP, mask: int = ZD) -> str:
    return _rows_key(f"{key}.op.rows", pfa, mask)


def _setup(name: str) -> int:
    return _find(fetch(f"{ECA}:meta.setups"), name=name)


def _s1_deepest(name: str) -> str:
    i = _find(fetch(f"{ECA}:S1_depth_vs_taps"), name=name)
    rows = fetch(f"{ECA}:S1_depth_vs_taps[{i}].rows")
    j = max(range(len(rows)), key=lambda k: rows[k]["n_taps"])
    return f"S1_depth_vs_taps[{i}].rows[{j}]"


def _s3(name: str, occ: str = "G3") -> str:
    return f"S3_pilot_vs_tx[{_find(fetch(f'{ECA}:S3_pilot_vs_tx'), occ=occ, name=name)}]"


def _s4(name: str, M: int) -> str:
    return f"S4_target_loss[{_find(fetch(f'{ECA}:S4_target_loss'), name=name, M=M)}]"


def _clutter_max() -> str:
    rows = fetch(f"{ECA}:S5_clutter_dead.sweep")
    j = max(range(len(rows)), key=lambda k: rows[k]["scale"])
    return f"S5_clutter_dead.sweep[{j}]"


def _calib(band: str, target: float) -> str:
    base = f"chain.{band}.dpi_eca.calib_op_mask1.points"
    return f"{base}[{_find(fetch(f'{CFAR}:{base}'), pfa_target_emp=target)}]"


def _paper(key: str) -> str:
    return f"papers[{_find(fetch(f'{CENSUS}:papers'), key=key)}]"


def fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/report04_{stem}.png)", "", caption(no, question)]


# ── 자주 쓰는 값 ─────────────────────────────────────────────────────────── #
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

_ratio_raw = {b: num(None, f"{CFAR}:{_row(b, 'dpi_eca', 'op')}.ratio", "{:.2f}")
              for b, _e, _l in WFS}
RATIO = {b: v + "배" for b, v in _ratio_raw.items()}
#: 제목에 들어가는 배율 구간 — 손으로 적지 않는다(제목에는 출처 태그를 달 수 없으므로
#: 값만 원장에서 읽어 끼운다. 세 파형의 운용 형상 경험/명목 비의 최소·최대다).
_RATIO_F = {b: float(fetch(f"{CFAR}:{_row(b, 'dpi_eca', 'op')}.ratio")) for b, _e, _l in WFS}
RATIO_LO = f"{min(_RATIO_F.values()):.2f}"
RATIO_HI = f"{max(_RATIO_F.values()):.2f}"
CALIB = {b: num(None, f"{CFAR}:{_calib(b, 1e-4)}.pfa_nominal_needed", "{:.2e}")
         for b, _e, _l in WFS}
DNR = {e: num(None, f"{ECA}:meta.setups[{_setup(e)}].dnr_db", "{:.1f}", "dB")
       for _b, e, _l in WFS}
TAPS = {e: num(None, f"{ECA}:meta.setups[{_setup(e)}].n_taps", "{:.0f}")
        for _b, e, _l in WFS}
DEEP_DPI = {e: num(None, f"{ECA}:{_s1_deepest(e)}.depth_dpi_db", "{:.1f}", "dB")
            for _b, e, _l in WFS}
DEEP_FULL = {e: num(None, f"{ECA}:{_s1_deepest(e)}.depth_full_db", "{:.1f}", "dB")
             for _b, e, _l in WFS}
#: 이 부의 ECA 값이 선 점유 격자 — `benchmark/verify_eca.py:505` 가 G3(풀로드)로 셋업을 짓는다.
#  그 격자에서 LTE·5G 의 기준신호는 상시 CRS·SSB 자리에 PRS·NR-PRS 가 선다(`src/waveforms.py:181`).
OCC = "G3"
REF_NAME = {e: num(None, f"{ECA}:{_s3(e)}.ref_name") for _b, e, _l in WFS}
#: 직접파를 송신 파형 전체(파일럿+데이터)로 합성했을 때의 같은 소거기 깊이와, 그 잔류가
#  RD 맵의 비-0도플러 칸에 남긴 첨두(잡음 플로어 대비).
TX_DEPTH = {e: num(None, f"{ECA}:{_s3(e)}.depth_tx_dpi_db", "{:.2f}", "dB")
            for _b, e, _l in WFS}
RD_OFF = {e: num(None, f"{ECA}:{_s3(e)}.rd_offzero_peak_over_nfloor_db", "{:.1f}", "dB")
          for _b, e, _l in WFS}
#: 다중경로의 출처 — 실측이 아니라 레이 트레이싱이라는 것을 원장에서 직접 읽는다.
CLUTTER_SRC = num(None, f"{ECA}:meta.setups[{_setup('5G NR 100MHz')}].clutter_src")
FD3DB = num(None, f"{ECA}:{_s4('5G NR 100MHz', 48)}.fd_3db_over_dfd", "{:.3f}")
M48 = num(None, f"{ECA}:{_s4('WiFi 80MHz', 48)}.M", "{:.0f}")
V3 = {e: num(None, f"{ECA}:{_s4(e, 48)}.v_3db_ms", "{:.2f}", "m/s") for _b, e, _l in WFS}
RANK1 = num(None, f"{OBS}:summary.snapshot_fim_rank", "{:.0f}")
RANK2 = num(None, f"{OBS}:summary.fix_2rx_rank", "{:.0f}")
RMS2 = num(None, f"{OBS}:summary.fix_2rx_pos_rms_m", "{:.2f}", "m")
#: 그램행렬·CRLB 를 푼 기준 셀과 관측창 — 랭크 표의 절대값이 어디에 매달려 있는지가 이 둘이다.
REF_CFG = num(None, f"{OBS}:gramian.ref_cfg")
T_OBS = num(None, f"{OBS}:gramian.t_obs_s", "{:.0f}", "s")
#: 랭크 표의 허용오차 두 판. 열 이름에 넣을 값은 원장에서 읽어 끼운다(제목·열 이름에는
#: 출처 태그를 달 수 없으므로 값만 주입한다). 표 밑 한 줄이 다른 판의 값을 병기한다.
PTOL_F = float(fetch(f"{OBS}:gramian.practical_tol"))
PTOL = num(None, f"{OBS}:gramian.practical_tol", "{:.0e}")
RTOL = num(None, f"{OBS}:gramian.rank_tol", "{:.0e}")
RANK_1RX_TIGHT = num(None, f"{OBS}:fixes.1RX (baseline).rank", "{:.0f}")
OI = _paper("openisac")
N_PAPERS = num(None, f"{CENSUS}:meta.n_papers", "{:.0f}")
TOT_PAGES = num(None, f"{CENSUS}:counts.total_pages", "{:.0f}")
ZERO_CFAR = num(None, f"{CENSUS}:counts.zero_cfar_and_falsealarm", "{:.0f}")
N_DETECT = num(None, f"{CENSUS}:counts.claims_detection", "{:.0f}")


# =========================================================================== #
#  편 51 — 사슬
# =========================================================================== #
def r51():
    return [
        header(
            num=51,
            title="수신 → ECA → 거리도플러 → CFAR, 사슬의 형상은 파형이 정한다",
            did="세 조명원을 하나의 동일한 검출 사슬에 물리고, 사슬의 각 단계가 파형마다 어떤 "
                "형상(거리 빈 수 · ECA 탭 수 · 도플러 빈)을 갖는지를 표로 고정했다.",
            results=[
                "사슬은 네 단계다 — 2채널 수신 → ECA 로 직접파 제거 → 거리-도플러 상관 → "
                "CA-CFAR 판정. 각 단계는 앞 단계의 잔류물을 물려받는다.",
                f"직접파-에코 비 DNR 은 WiFi {DNR['WiFi 80MHz']} · LTE {DNR['LTE 20MHz']} · "
                f"5G {DNR['5G NR 100MHz']} 다 — 수신단에서 가장 큰 신호이고 2단계가 지울 대상이다.",
                f"ECA 탭 수는 파형이 정한다 — WiFi {TAPS['WiFi 80MHz']} · LTE {TAPS['LTE 20MHz']} · "
                f"5G {TAPS['5G NR 100MHz']}.",
                f"도플러 빈은 세 파형 모두 {M_CPI}개다(CPI 당 프레임 수). 거리 빈 수와 PRF 는 "
                f"파형마다 다르고, 아래 표가 그 형상을 한 자리에 모은다.",
            ],
            method=[
                ("사슬 구현",
                 "네 단계가 한 파일에 있다 — `src/passive_process.py:42`(수신) · `:93,124`(ECA) · "
                 "`:133`(거리-도플러) · `:153`(CA-CFAR)"),
                ("형상 표",
                 "선언값을 옮겨 적지 않고 검증 산출물 `outputs/verify_eca.json:meta.setups` 에서 "
                 "직접 뽑는다"),
                ("세 파형 동일 사슬",
                 "코드 경로가 하나다 — 파형이 바꾸는 것은 형상 파라미터뿐이다"),
            ],
            prereq=[(ref("illuminators", short=True),
                     "세 표준의 상시 기준신호와 대역 — 이 편의 형상 표는 그 중 "
                     "G3(풀로드) 격자에서 뽑은 셋업이다"),
                    (ref("range-convention", short=True), "거리 규약 $\\Delta R_b = c/B_{ref}$")],
            repro=dict(cmd=CMD[:1] + CMD[2:3] + CMD[-2:], out=[ECA],
                       runtime="ECA 검증 · 그림은 각각 수 분 (GPU 1장)"),
        ),

        md("## 수신 신호가 판정이 되기까지", "",
           "패시브 검출은 네 단계다. 각 단계는 앞 단계의 잔류물을 물려받는다.", "",
           table(["단계", "하는 일", "코드"],
                 [["1. 수신",
                   "서베일런스(표적 쪽을 보는 채널) + 레퍼런스(조명원을 직접 받는 채널) 2채널",
                   "`src/passive_process.py:42`"],
                  ["2. ECA", "직접파를 서베일런스에서 투영 제거", "`src/passive_process.py:93,124`"],
                  ["3. 거리-도플러(CAF)", "레퍼런스와 지연 · 도플러 상관",
                   "`src/passive_process.py:133`"],
                  ["4. CA-CFAR", "이웃 셀로 문턱을 세우고 판정", "`src/passive_process.py:153`"]])),

        md(*fig(1, "f1_chain", "수신 신호는 어떤 단계를 거쳐 검출 판정이 되는가?")),

        md("## 사슬의 형상 — 파형이 정하는 것", "",
           f"직접파는 수신단에서 가장 큰 신호이고, 2단계가 지울 대상이다. 그것이 표적 에코보다 "
           f"몇 dB 큰지가 DNR 이다. "
           f"거리 빈 수와 ECA 탭 수는 파형이 정하고, 도플러 빈은 세 파형 모두 {M_CPI}개다.", "",
           table_from(f"{ECA}:meta.setups",
                      [("파형", "name"), ("DNR", "dnr_db"), ("ECA 탭", "n_taps"),
                       ("거리 빈", "n_range"), ("PRF", "prf_hz"), ("Δf_d", "dfd_hz")],
                      fmt={"dnr_db": "{:.1f} dB", "n_taps": "{:.0f}", "n_range": "{:.0f}",
                           "prf_hz": "{:.0f} Hz", "dfd_hz": "{:.2f} Hz"},
                      order=[_setup("WiFi 80MHz"), _setup("LTE 20MHz"),
                             _setup("5G NR 100MHz")]), "",
           f"이 표는 {OCC}(풀로드) 점유 격자의 셋업이다(`benchmark/verify_eca.py:505`). "
           f"숫자 열 다섯은 점유 체제에 불변이다 — DNR 은 직접파/에코 비라 기하와 반송파별 "
           f"표적 σ 가 정하고(`benchmark/link_budget.py:86`), 거리 빈·ECA 탭은 표본율이"
           f"(`benchmark/geometry.py:146`), PRF·Δf_d 는 표본율·프레임 길이·CPI 프레임 수가 "
           f"정한다(`benchmark/verify_eca.py:107` · `benchmark/run_min_cell.py:74`). "
           f"점유가 바꾸는 것은 기준신호의 이름이다.", "",
           f"이 표의 PRF 는 **검출기 프레임률**이다 — 사슬이 한 프레임으로 끊어 읽는 속도이지 "
           f"조명원의 물리 반복률이 아니다. 5G 상시 SSB 에서 두 양이 얼마나 벌어지고 그것이 "
           f"도플러를 어디서 접는지는 {ref('doppler-fold', short=True)} 가 잰다."),

        md("## 이 사슬 위에서 무엇이 결정되나", "",
           f"2단계의 소거 깊이와 그 대가는 {ref('eca', short=True)} 가, 4단계 문턱의 눈금은 "
           f"{ref('cfar-calib', short=True)} 가 든다. 3단계가 만드는 응답의 모양은 "
           f"{ref('ambiguity', short=True)} 가 이미 쟀다.", "",
           "세 파형이 같은 코드 경로를 지나므로, 뒤 편들이 재는 격차는 사슬 차이가 아니라 "
           "파형 차이다.", "",
           "이 사슬의 레퍼런스 채널에는 **송신 파형 그 자체**가 들어간다 — 잡음 0 · 다중경로 0 "
           "이라는 상한 가정이다. 그 가정 하나만 풀어 손실을 재는 편이 "
           "[리포트 8-2 «기준채널이 현실이면 얼마를 잃는가»](08_2_two_channel.ipynb) 다."),

        next_steps([
            ("회전 블레이드 산란을 이 사슬에 넣는 조건을 세운다",
             "마이크로도플러를 검출 판정에 쓰는 조건이 결정된다",
             ref("md-prf", short=True)),
            ("2채널 수신을 실제 X410 캡처로 바꿔 같은 사슬을 돌린다",
             "시뮬 사슬과 실측 사슬이 같은 형상 표 위에 선다",
             ref("hardware", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 52 — ECA
# =========================================================================== #
def r52():
    return [
        header(
            num=52,
            title="탭을 늘리면 환경이 정한 바닥에서 멈추고, 그 대가가 0-도플러 노치다",
            did="ECA 탭 수를 1~96 으로 스윕하며 소거 깊이를 재고, 같은 소거기가 표적의 느린 "
                "도플러를 얼마나 함께 지우는지를 속도 문턱으로 환산했다.",
            results=[
                f"{OCC}(풀로드) 격자에서 직접파를 기준신호로 합성해 같은 소거기를 걸면 float64 "
                f"한계까지 내려간다 — 5G {DEEP_DPI['5G NR 100MHz']}. 레이 트레이싱으로 푼 챔버 "
                f"다중경로를 넣으면 {DEEP_FULL['5G NR 100MHz']} 에서 멈춘다.",
                f"그 합성에서 바닥을 정하는 것은 탭 수가 아니라 환경이다 — 탭 1~96 스윕에서 깊이가 "
                f"포화한다. 직접파를 송신 파형 전체로 합성하면 같은 격자의 깊이가 5G "
                f"{TX_DEPTH['5G NR 100MHz']} 다.",
                f"대가는 0-도플러 노치다. 3 dB 손실 지점은 $f_d/\\Delta f_d$ = {FD3DB} 이고 "
                f"세 파형이 같다.",
                f"프레임 {M48}개에서 속도 문턱은 WiFi {V3['WiFi 80MHz']} · LTE {V3['LTE 20MHz']} · "
                f"5G {V3['5G NR 100MHz']} 다 — 그보다 빠른 표적이 무는 노치 손실은 3 dB 아래다.",
                f"정적 산란체는 ECA 뒤에서 죽은 파라미터다 — 클러터를 "
                f"{num(None, f'{ECA}:{_clutter_max()}.scale', '{:.0f}')}배까지 키워도 SCR 변화폭은 "
                f"{num(None, f'{ECA}:S5_clutter_dead.scr_span_db', '{:.1e}', 'dB')} 다.",
            ],
            method=[
                ("소거기",
                 "CPI 1회 최소제곱 사영의 standard ECA — 레퍼런스의 지연 사본이 치는 부분공간에 "
                 "서베일런스를 통째로 사영한다(`src/passive_process.py:13`)"),
                ("점유 격자",
                 f"{OCC}(풀로드) 한 판이다(`benchmark/verify_eca.py:505`) — 그 격자의 기준신호는 "
                 f"WiFi {REF_NAME['WiFi 80MHz']} · LTE {REF_NAME['LTE 20MHz']} · "
                 f"5G {REF_NAME['5G NR 100MHz']} 라, LTE·5G 는 상시 CRS·SSB 자리에 측위 세션 "
                 f"신호가 선다"),
                ("깊이 스윕",
                 f"탭 수 1~96 × (직접파만 / 다중경로 포함) 두 조건. 다중경로는 챔버 장면을 "
                 f"레이 트레이싱으로 푼 것이고 실측이 아니다(출처 {CLUTTER_SRC}). 두 조건의 차이가 "
                 "«바닥을 무엇이 정하는가» 를 가른다"),
                ("노치 환산",
                 "3 dB 손실 지점을 $f_d/\\Delta f_d$ 무차원으로 재고, 파형별 $\\lambda$ 로 "
                 "속도 문턱으로 옮긴다"),
                ("클러터 대조",
                 "정적 산란체 세기를 배수로 키우며 SCR 변화폭을 잰다"),
            ],
            prereq=[(ref("chain", short=True), "사슬의 네 단계와 파형별 형상")],
            repro=dict(cmd=CMD[:1] + CMD[2:3] + CMD[-2:], out=[ECA],
                       runtime="ECA 검증 · 그림은 각각 수 분 (GPU 1장)"),
        ),

        md("## 직접파를 얼마나 지울 수 있는가", "",
           f"탭을 늘리면 소거가 깊어지다가 멈춘다. 멈추는 자리를 정하는 것이 탭 수인지 환경인지를 "
           f"가르려고 {OCC}(풀로드) 격자에서 두 조건을 나란히 돌렸다.", "",
           table(["파형", "직접파(=기준신호로 합성)", "직접파(=기준신호) + 다중경로(포화)"],
                 [[label, DEEP_DPI[ename], DEEP_FULL[ename]] for _b, ename, label in WFS]),
           "",
           "왼쪽은 float64 산술의 한계이고, 오른쪽이 이 장면의 다중경로가 정하는 바닥이다"
           "(실측 채널이 아니라 레이 트레이싱으로 푼 챔버 장면이다). 두 열의 간격이 곧 "
           "**환경이 정하는 몫**이다.", "",
           f"두 열 모두 직접파를 기준신호로 합성한 판이다(`benchmark/verify_eca.py:146,147`). "
           f"헤드라인 사슬은 직접파를 송신 파형 전체(파일럿+데이터)로 합성하고"
           f"(`benchmark/run_min_cell.py:164`), 그 판의 깊이는 WiFi {TX_DEPTH['WiFi 80MHz']} · "
           f"LTE {TX_DEPTH['LTE 20MHz']} · 5G {TX_DEPTH['5G NR 100MHz']} 다 — 데이터 잔류가 "
           f"0-도플러 행에 앉으므로 RD 맵의 비-0도플러 첨두는 잡음 플로어 대비 WiFi "
           f"{RD_OFF['WiFi 80MHz']} · LTE {RD_OFF['LTE 20MHz']} · "
           f"5G {RD_OFF['5G NR 100MHz']} 다."),

        md(*fig(1, "f2_eca_depth", "ECA 소거 깊이의 바닥을 정하는 것은 무엇인가?")),

        md("## 대가 — 0-도플러 노치", "",
           f"ECA 는 지연만 다른 성분을 함께 지운다. 느리게 움직이는 표적은 그 성분과 구분되지 "
           f"않으므로 같이 깎인다. 3 dB 손실 지점은 $f_d/\\Delta f_d$ = {FD3DB} 이고 세 파형이 "
           f"같다 — 속도 문턱은 $\\lambda$ 가 가른다.", "",
           table(["파형", "3 dB 속도 문턱 (프레임 " + M48 + "개)"],
                 [[label, V3[ename]] for _b, ename, label in WFS])),

        md(*fig(2, "f3_eca_notch", "ECA 가 클러터와 함께 지우는 표적의 속도는 얼마인가?")),

        md("## 정적 클러터는 ECA 뒤에서 죽은 파라미터다", "",
           f"클러터 세기를 {num(None, f'{ECA}:{_clutter_max()}.scale', '{:.0f}')}배까지 키워도 "
           f"SCR 변화폭은 {num(None, f'{ECA}:S5_clutter_dead.scr_span_db', '{:.1e}', 'dB')} 다. "
           f"소거기가 직접파와 함께 정적 성분을 통째로 가져가기 때문이다.", "",
           f"그래서 이 사슬에서 남는 위협은 정적 클러터가 아니라 **표적을 거쳐 오는 성분**이고, "
           f"느린 표적은 노치가 먼저 지운다 — 그 축의 결과는 {ref('cpi-sweep', short=True)} 가 든다."),

        next_steps([
            ("실외에서 잰 채널로 소거 바닥을 다시 잰다",
             "환경이 정하는 바닥이 실측 채널에서 몇 dB 인지 확정된다",
             "`benchmark/verify_eca.py` → " + ref("hardware", short=True)),
            ("노치 폭을 CPI 와 함께 스윕한다",
             "느린 표적이 노치 밖으로 나오는 CPI 가 수치로 정해진다",
             "`benchmark/verify_eca.py` → " + ref("cpi-sweep", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 53 — CFAR 교정
# =========================================================================== #
def r53():
    return [
        header(
            num=53,
            title=f"운용 형상에서 경험 Pfa 를 재니 명목값의 {RATIO_LO}~{RATIO_HI} 배였다",
            did="운용 형상의 검출 사슬에서 거리-도플러 맵을 대량으로 다시 만들어 경험적 "
                "오경보율을 세고, 세 파형의 CFAR 문턱을 그 측정값에 맞춰 교정했다.",
            results=[
                f"GPU {RUNTIME} 동안 파형·모드마다 거리-도플러 맵 {N_CHAIN}장을 돌려 경험 Pfa 를 "
                f"측정했다.",
                f"검출기 구현의 눈금을 먼저 확정했다 — 문턱 상수는 이론값과 상대오차 {REL_ERR} "
                f"안에서 같고, 이상적 백색 맵 {N_WHITE}장(셀 {W_CELLS}개)에서 경험/명목 = "
                f"{W_RATIO} 다.",
                f"운용 형상(CPI 프레임 {M_CPI} · `{GT}` · 0-도플러 마스크 {ZDN}빈)에서 명목 {NOM} 를 "
                f"주면 WiFi {RATIO['WiFi80']} · LTE {RATIO['LTE20']} · 5G {RATIO['NR100']}로 울린다.",
                f"그 형상의 교정표를 만들었다 — 경험 {NOM} 를 얻는 명목값은 WiFi {CALIB['WiFi80']} · "
                f"LTE {CALIB['LTE20']} · 5G {CALIB['NR100']} 다.",
                f"선행 census {N_PAPERS}편 · 전문 {TOT_PAGES}쪽에서 `CFAR` 와 `false alarm` 이 모두 "
                f"0회인 논문이 {ZERO_CFAR}편이고, 검출을 주장한 논문은 {N_DETECT}편이다.",
            ],
            method=[
                ("경험 Pfa",
                 f"파형·명목값마다 거리-도플러 맵 {N_CHAIN}장에 CA-CFAR 를 걸어 오경보 셀을 "
                 f"세었다 (GPU, {RUNTIME})"),
                ("문턱 상수",
                 f"CA-CFAR α 를 이론식과 대조했다 — 상대오차 {REL_ERR} · 훈련셀 {N_INT}개"),
                ("측정 구간",
                 f"명목 {PFA_LO} ~ {PFA_HI} 아홉 점. 그 밖의 운용점은 외삽이라 표에서 뺀다"),
                ("교정표",
                 "측정한 명목–경험 곡선을 역보간한다. 자유공간 기하는 형상이 달라 "
                 "`src/freespace_detect.py:711` 이 거기서 다시 잰다"),
                ("왜 통제 시뮬레이션인가",
                 "오경보율을 명목값과 대조하려면 같은 배경을 수만 번 다시 만들어 세어야 한다. "
                 "실외 실측은 배경을 주어진 대로 받는다"),
            ],
            prereq=[(ref("chain", short=True), "사슬의 네 단계와 파형별 형상")],
            repro=dict(cmd=CMD[:2] + CMD[-2:], out=[CFAR, CENSUS],
                       runtime=f"CFAR 측정이 {RUNTIME} (GPU 1장)",
                       note="맵 수는 `--maps` / `--white` 로 줄인다. 줄이면 신뢰구간이 넓어진다."),
        ),

        md("## 왜 배경을 다시 만드는가", "",
           "⭐ 오경보율을 명목값과 대조하려면 같은 배경을 수만 번 다시 만들어 세어야 한다. "
           "통제 시뮬레이션이 그 일을 한다.", "",
           f"선행 census {N_PAPERS}편 · 전문 {TOT_PAGES}쪽에서 `CFAR` 와 `false alarm` 이 모두 0회인 "
           f"논문이 {ZERO_CFAR}편이고, 검출을 주장한 논문은 {N_DETECT}편이다. "
           f"OpenISAC(`arXiv:2601.03535v2`, preprint)은 전문 "
           f"{num(None, f'{CENSUS}:{OI}.pages', '{:.0f}')}쪽에서 `CFAR` "
           f"{num(None, f'{CENSUS}:{OI}.terms.cfar', '{:.0f}')}회 · `false alarm` "
           f"{num(None, f'{CENSUS}:{OI}.terms.false_alarm', '{:.0f}')}회 · `detection probability` "
           f"{num(None, f'{CENSUS}:{OI}.terms.detection_probability', '{:.0f}')}회다."),

        md("## 눈금부터 확정한다", "",
           f"이 절의 모든 수는 **운용 형상** 하나에서 나온다 — DPI+ECA · 운용 거리창 · "
           f"CPI 프레임 {M_CPI} · 훈련창 `{GT}` · 0-도플러 마스크 {ZDN}빈.", "",
           f"검출기 구현이 먼저 맞아야 배율을 사슬 탓으로 돌릴 수 있다. 문턱 상수는 이론값과 "
           f"상대오차 {REL_ERR} 안에서 같고, 잡음 추정/실제 전력 = "
           f"{num(None, f'{CFAR}:alpha_audit.{GT}.noise_est_over_power', '{:.3f}')} 다. "
           f"이상적 백색 맵 {N_WHITE}장에서 경험/명목 = {W_RATIO} 로 눈금이 1 에 선다."),

        md(*fig(1, "f4_pfa", "명목 Pfa 를 요구하면 실제로는 몇 배가 울리는가?")),

        md("## 운용 형상 교정표", "",
           f"운용 명목값은 {NOM} 다. 왼쪽 열이 그 값에서 측정된 배율이고, 오른쪽 열이 교정된 "
           f"명목값이다.", "",
           table(["파형", "명목 1e-4 에서 경험/명목", "경험 1e-4 를 얻을 명목 Pfa"],
                 [[label, RATIO[b], CALIB[b]] for b, _e, label in WFS]),
           "",
           "세 파형의 배율이 서로 다르다. 교정이 셋을 같은 실제 오경보율 위에 올린다.", "",
           "`src/passive_process.py:283` 이 이 JSON 을 읽고, `pfa_nominal_for()`"
           "(`src/passive_process.py:338`)가 파형별 명목값을 돌려준다."),

        md("## 이 표를 읽는 곳", "",
           "`src/experiment_detection.py:358` 과 `src/experiment_x410.py:175` 가 "
           "`src/passive_process.py:283` 을 거쳐 이 표를 읽는다.", "",
           f"교정이 없으면 세 파형 비교가 서로 다른 실제 오경보율 위에서 이뤄진다. "
           f"그 위에서 선 비교가 {ref('shared-threshold')} 다.", "",
           "이 표는 **레퍼런스 채널이 이상적일 때**의 형상에서 잰 값이다. 레퍼런스가 오염되면 "
           "거리-도플러 맵의 통계가 달라져 이 교정이 그대로 서지 않는다 — 그 형상에서 팔마다 "
           "경험 Pfa 를 다시 센 것이 "
           "[리포트 8-2 «기준채널이 현실이면 얼마를 잃는가»](08_2_two_channel.ipynb) 다.", "",
           f"배율이 왜 1 이 아닌지, 이 표가 어디까지 쓰이는지는 {ref('cfar-why')} 가 든다."),

        next_steps([
            ("실외 클러터 배경 위에서 같은 Pfa 스윕을 돌린다",
             "교정 배율이 배경에 따라 얼마나 움직이는지 수치로 확정된다",
             "`benchmark/verify_cfar.py` → " + ref("hardware", short=True)),
            (f"맵 수를 한 자릿수 올려 명목 {PFA_1E6} 구간까지 측정한다",
             "저 Pfa 운용점의 교정값이 측정 구간 안으로 들어온다",
             "`benchmark/verify_cfar.py --maps` · `calib_op_mask1.points`"),
            ("표적 σ 를 앵커 위에서 읽어 Pd 절대값을 다시 푼다",
             "Pd 절대값이 교정된 Pfa 와 같은 근거 위에 선다",
             ref("r90", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 54 — 배율의 원인
# =========================================================================== #
def r54():
    return [
        header(
            num=54,
            title="그 배율의 원인은 셀 상관이고, 교정표는 형상마다 다시 재야 한다",
            did="명목과 경험 사이의 배율을 만드는 항을 대조군 두 종으로 하나씩 꺼 확정하고, "
                "그 배율이 형상에 얼마나 의존하는지를 창 폭을 바꿔 재었다.",
            results=[
                f"CA-CFAR 는 훈련셀이 서로 독립이라고 가정한다. 사슬은 slow-time Hann 창으로 "
                f"도플러축 셀을 묶는다 — Hann 을 rect 창으로 바꾸면 5G 배율이 {RECT} 로 내려온다.",
                f"거리축 항까지 끄면 {BOTH} 로 눈금이 1 로 돌아온다 — 두 항이 배율의 전부다.",
                f"형상이 배율을 정한다 — 같은 파형이 운용 창에서 {RATIO['NR100']}, 넓은 창"
                f"({N_WIDE} 빈)에서 {WIDE_NR}배다.",
                f"그래서 교정표는 형상마다 다시 잰다. `check_detector_config()`"
                f"(`src/passive_process.py:383`)가 거리창과 0-도플러 마스크 두 조건을 강제한다.",
            ],
            method=[
                ("대조군 2종",
                 "slow-time Hann 제거(도플러축) · 백색화 정합필터(거리축). 하나씩 끄고 배율이 "
                 "어디로 가는지를 본다"),
                ("사다리 읽기",
                 "이상적 백색 맵 → 잡음 맵 → 항을 하나씩 뺀 대조군 → 전체 사슬 순서로 읽으면 "
                 "각 항의 몫이 갈린다"),
                ("형상 의존",
                 f"운용 창과 넓은 창({N_WIDE} 빈)에서 같은 파형을 다시 재 배율의 형상 의존을 "
                 f"크기로 적는다"),
                ("두 형상의 쓰임",
                 "운용 형상의 표는 챔버 기하가 읽고, 자유공간 기하는 "
                 "`src/freespace_detect.py:711` 이 자기 형상에서 다시 잰다"),
            ],
            prereq=[(ref("cfar-calib", short=True), "운용 형상에서 잰 경험 Pfa 와 교정표")],
            repro=dict(cmd=CMD[:2] + CMD[-2:], out=[CFAR],
                       runtime=f"CFAR 측정이 {RUNTIME} (GPU 1장)"),
        ),

        md("## 원인 — 셀 상관", "",
           "CA-CFAR 는 훈련셀이 서로 독립이라고 가정한다. 사슬은 slow-time Hann 창으로 도플러축 "
           "셀을 묶고, 정합필터로 거리축 셀을 묶는다. 대조군이 그 두 항을 원인으로 확정한다"
           "(5G NR, 명목 1e-4).", "",
           table(["조건", "경험/명목"],
                 [["이상적 백색 맵", W_RATIO],
                  ["잡음 맵 (Hann + 정합필터)",
                   num(None, f"{CFAR}:{_row('NR100', 'noise', 'op')}.ratio", "{:.2f}")],
                  ["  └ Hann 제거 (rect 창)", RECT],
                  ["  └ 백색화 정합필터 (거리축 평탄)",
                   num(None, f"{CFAR}:{_ctrl_row('control_whitened_mf_NR100')}.ratio", "{:.2f}")],
                  ["  └ 둘 다 제거", BOTH],
                  ["전체 사슬 (직접파 + ECA)", _ratio_raw["NR100"]]])),

        md(*fig(1, "f5_cause", "명목과 경험 사이의 배율을 만드는 것은 무엇인가?")),

        md("## 셀 상관은 어느 검출기에나 있다 — 그래서 대조군이 필요하다", "",
           f"«상관이 있다» 만으로는 원인 지목이 서지 않는다. 항을 하나씩 꺼서 눈금이 1 로 "
           f"돌아오는 것을 보여야 확정된다. Hann 을 rect 로 바꾸면 {RECT}, 백색화 정합필터까지 "
           f"끄면 {BOTH} 다.", "",
           "그 사다리가 위 표이고, 마지막 줄과 첫 줄 사이의 간격이 곧 두 항의 몫이다."),

        md("## 형상 규약 — 교정표가 성립하는 조건", "",
           f"거리창은 ECA 탭 안에 두고, 0-도플러 행 {ZDN}개를 마스킹한다. "
           f"`check_detector_config()`(`src/passive_process.py:383`)가 두 조건을 검사한다.", "",
           table(["파형", "운용 창", "넓은 창"],
                 [[label, RATIO[b],
                   num(None, f"{CFAR}:{_row(b, 'dpi_eca', 'wide')}.ratio", "{:.1f}") + "배"]
                  for b, _e, label in WFS]),
           "",
           f"창을 {N_WIDE} 빈으로 넓히면 배율이 두 자릿수가 된다. 교정표는 운용 창 형상에서 "
           f"측정한 값이다."),

        md("## 어느 형상의 교정표가 어디에 쓰이나", "",
           table(["형상", "무엇을 재나", "재는 코드", "그 값을 읽는 곳"],
                 [[f"운용 형상 — CPI 프레임 {M_CPI} · `{GT}` · 마스크 {ZDN}빈 · 운용 거리창",
                   "이 부의 교정표", "`benchmark/verify_cfar.py`",
                   "`src/experiment_detection.py:358` · `src/experiment_x410.py:175`"],
                  ["자유공간 형상 — 모드별 프레임 수 · 자유공간 거리창 · 0-도플러 가드",
                   "자유공간 명목 Pfa", "`src/freespace_detect.py:711`",
                   "`src/experiment_freespace_range.py:206`"]]),
           "",
           f"{ref('shared-threshold', short=True)} 가 싣는 명목 Pfa 는 둘째 줄에서 나온 수다 — "
           f"이 부의 교정표와 형상이 달라 값도 다르다."),

        next_steps([
            ("훈련셀에서도 0-도플러 행을 빼는 CFAR 변형을 만든다",
             f"넓은 창에서 마스크 폭 3 이 만드는 배율 "
             f"{num(None, f'{CFAR}:{_row('LTE20', 'dpi_eca', 'wide', mask=3)}.ratio', '{:.2f}')}배가 "
             f"마스크 폭과 분리된다",
             "`src/passive_process.py:352`"),
            ("표적모형 민감도를 이 배율 위에서 다시 푼다",
             "세 표적모형의 절대 소요이득이 경험 Pfa 위에 선다 — CA-CFAR 문턱은 세 팔에 같은 "
             "오프셋을 주므로 모형 간 차이는 문턱 규약에 불변이다",
             ref("target-model-swap", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 55 — 관측가능성
# =========================================================================== #
def r55():
    return [
        header(
            num=55,
            title="한 순간의 (R_b, f_d) 는 랭크 2 이고, 수신기를 하나 더하면 위치가 풀린다",
            did="송수신 한 쌍이 한 순간에 담는 정보량을 Fisher 정보행렬의 랭크로 세고, "
                "수신기를 더하거나 도래각을 더했을 때 위치 오차가 어디로 가는지를 계산했다.",
            results=[
                f"TX–RX 기저선 {num(None, f'{OBS}:meta.L_m', '{:.2f}', 'm')} 형상에서 한 순간의 "
                f"$(R_b, f_d)$ 는 3차원 위치에 대해 랭크 {RANK1} 를 만든다.",
                f"기저선을 축으로 표적을 돌리면 $R_b$ 변화가 최대 "
                f"{num(None, f'{OBS}:summary.exact_rotation_max_dRb_m', '{:.1e}', 'm')} 다 — "
                f"그 방향의 정보량은 SNR 과 관측시간에 무관하게 0 이다.",
                f"수신기를 하나 더 놓으면 랭크 {RANK2} · 위치 RMS {RMS2} 가 된다 — 그 절대값은 "
                f"측위 세션 옵션인 PRS 셀({REF_CFG})에서 푼 값이다.",
                f"분해능과 정확도는 다른 양이다 — 5G SSB 는 기준 대역폭 "
                f"{num(None, f'{OBS}:cells[2].ref_bw_mhz', '{:.2f}', 'MHz')} 라 셀이 "
                f"{num(None, f'{OBS}:cells[2].drb_bw_m', '{:.2f}', 'm')} 인데, 같은 반송파에서 "
                f"PRS 로 가면 {num(None, f'{OBS}:cells[3].drb_bw_m', '{:.2f}', 'm')} 가 된다.",
                f"도플러 분해능은 $\\Delta f_d = 1/T_{{CPI}}$ 다 — $T_{{CPI}}$ "
                f"{num(None, f'{OBS}:cells[0].t_cpi', '{:.3f}', 's')} 에서 "
                f"{num(None, f'{OBS}:cells[0].dfd_hz', '{:.2f}', 'Hz')}.",
            ],
            method=[
                ("정보량",
                 "관측이 미지수에 담은 정보량을 Fisher 정보행렬로 세고, 그 랭크로 «무엇이 "
                 "풀리는가» 를 읽는다"),
                ("정확도 하한",
                 "CRLB — 추정 오차가 내려갈 수 있는 이론 하한이다. 대역폭이 분해능을, SNR 이 "
                 "정확도를 정한다"),
                ("거리 규약",
                 "$R_b = c\\tau$ 에 계수 2 가 없고 분해능은 $c/B_{ref}$ 다 — 조명원 편과 같은 정의다"),
                ("두 열을 가른다",
                 "$\\Delta R_b$ 는 선언 규약이고, 거리 빈 $c/f_s$ 는 표본율이 정하는 격자 간격이다"),
            ],
            prereq=[(ref("range-convention", short=True), "$\\Delta R_b$ 와 잡음대역 규약"),
                    (ref("chain", short=True), "판정이 나는 셀이 무엇인가")],
            repro=dict(cmd=CMD[:1] + CMD[3:], out=[OBS],
                       runtime="관측가능성 계산 · 그림은 각각 수 분"),
        ),

        md("## 분해능과 정확도는 다른 양이다", "",
           "분해능은 두 표적을 **가르는** 능력이고, 정확도는 한 표적을 **찍는** 정밀도다. "
           "대역폭이 분해능을, SNR 이 정확도를 정한다.", "",
           "바이스태틱 규약은 $\\Delta R_b = c/B_{ref}$ 다($R_b = c\\tau$, 계수 2 없이). "
           "아래 표가 그 규약으로 조명원별 셀 크기와 정확도 하한을 나란히 싣는다."),

        md(*fig(1, "f6_resolution", "대역폭이 정하는 것은 분해능인가 정확도인가?")),

        md("## 조명원별 셀 크기와 CRLB", "",
           f"5G 의 상시 기준신호 SSB 는 기준 대역폭 "
           f"{num(None, f'{OBS}:cells[2].ref_bw_mhz', '{:.2f}', 'MHz')} 라 셀이 "
           f"{num(None, f'{OBS}:cells[2].drb_bw_m', '{:.2f}', 'm')} 다. 같은 반송파에서 PRS 로 가면 "
           f"{num(None, f'{OBS}:cells[3].ref_bw_mhz', '{:.2f}', 'MHz')} · "
           f"{num(None, f'{OBS}:cells[3].drb_bw_m', '{:.2f}', 'm')} 가 된다.", "",
           table_from(f"{OBS}:cells",
                      [("조명원 / 기준신호", "label"), ("기준 대역폭 B_ref", "ref_bw_mhz"),
                       ("ΔR_b = c/B_ref", "drb_bw_m"), ("거리 빈 c/f_s", "bin_m"),
                       ("σ_Rb (정확도)", "sigma_rb_m"), ("σ_fd", "sigma_fd_hz")],
                      fmt={"ref_bw_mhz": "{:.2f} MHz", "drb_bw_m": "{:.2f} m",
                           "bin_m": "{:.2f} m",
                           "sigma_rb_m": "{:.4f} m", "sigma_fd_hz": "{:.3f} Hz"}), "",
           f"오른쪽 두 열은 CRLB 이고, 그 안의 SNR 은 선언값이 아니라 **챔버 동작점에서 잰 "
           f"SCR** 이다 ⟨{OBS} : meta.note⟩. 그래서 두 열은 대역폭만의 함수가 아니라 이 "
           f"기하·이 표적에 매달린 값이다."),

        md("## 두 열을 갈라 읽는다", "",
           "$\\Delta R_b$ 열이 선언 규약이고, 거리 빈은 표본율이 정하는 격자 간격이다. "
           "검출기가 실제로 내는 주엽 폭은 그 닫힌형 대비 비율로 "
           + ref("ambiguity", short=True) + " 가 싣는다.", "",
           f"도플러 분해능은 $\\Delta f_d = 1/T_{{CPI}}$ 다 — $T_{{CPI}}$ "
           f"{num(None, f'{OBS}:cells[0].t_cpi', '{:.3f}', 's')} 에서 "
           f"{num(None, f'{OBS}:cells[0].dfd_hz', '{:.2f}', 'Hz')}. 그 아래 속도는 "
           + ref("eca", short=True) + " 의 노치가 먼저 지운다."),

        md("## 관측가능성 — 수신기 2대면 위치가 풀린다", "",
           f"검출 판정은 $(R_b, f_d)$ 셀에서 난다. 그 두 양이 3차원 위치로 풀리는지가 검출 결과가 "
           f"말할 수 있는 범위를 정한다.", "",
           f"기저선을 축으로 표적을 돌리면 $R_b$ 변화가 최대 "
           f"{num(None, f'{OBS}:summary.exact_rotation_max_dRb_m', '{:.1e}', 'm')} 다 — 그 방향의 "
           f"정보량은 SNR 과 관측시간에 무관하게 0 이다. 더 오래 보거나 더 세게 쏘아도 그 축은 "
           f"풀리지 않는다.", "",
           table_from(f"{OBS}:fixes",
                      [("형상", None),
                       (f"유효 랭크(정규화 고윳값 ≥ {PTOL_F:.0e}, /6)", "rank_practical"),
                       ("위치 RMS 오차", "pos_rms_m")],
                      fmt={"rank_practical": "{:.0f}", "pos_rms_m": "{:.2f} m"},
                      order=["1RX (baseline)", "2RX",
                             "1RX + AoA(1deg)", "1RX + AoA(5deg)"]), "",
           f"랭크 열의 허용오차는 {PTOL} 다 — {RTOL} 판에서는 1RX 행이 "
           f"{RANK_1RX_TIGHT} 이고, 원장 요약이 그 판의 값을 싣는다"
           f"(`summary.gramian_rank_radial`). 2RX 부터 6 이 되는 결론은 두 판에서 같다.", "",
           f"표의 랭크는 위치 3 + 속도 3 = **6 차원 상태**에 대한 값이고, 관측창 {T_OBS} 를 "
           f"누적한 그램행렬에서 센다 — 머리줄의 «랭크 {RANK1}» 는 **한 순간 · 위치 3차원**에 "
           f"대한 값이라 다른 양이다."),

        md("## 이 표의 절대값이 매달린 것", "",
           f"랭크는 셀을 갈아도 그대로지만, 위치 RMS 는 아니다. 표의 절대값은 기준 셀 "
           f"{REF_CFG} — 위 표의 마지막 줄인 **PRS**, 즉 측위 세션에서만 켜지는 신호에서 푼 "
           f"값이다. 상시 기준신호 셀은 같은 표에서 $\\sigma_{{R_b}}$ 가 더 크므로 위치 RMS 도 "
           f"그만큼 커진다.", "",
           f"기하도 함께 매달려 있다 — 기저선 "
           f"{num(None, f'{OBS}:meta.L_m', '{:.2f}', 'm')} · EIRP "
           f"{num(None, f'{OBS}:meta.eirp_dbm', '{:.0f}', 'dBm')} · CPI "
           f"{num(None, f'{OBS}:meta.t_cpi_s', '{:.2f}', 's')} 의 챔버 통제 기하다."),

        md(*fig(2, "f7_observability", "송수신 한 쌍에 무엇을 더하면 표적 위치가 풀리는가?")),

        next_steps([
            ("수신기 2대 형상으로 검출 실험을 재설계한다",
             f"위치 RMS {RMS2} 가 검출 실험에서 확인된다",
             ref("rx-elements", short=True)),
            ("도래각 오차를 실제 배열 교정오차로 바꿔 랭크를 다시 센다",
             "1RX + AoA 형상이 실제 하드웨어에서 몇 랭크인지 확정된다",
             ref("hardware", short=True)),
        ]),
    ]


# =========================================================================== #
#  논문 조각 — 옛 report04 c22
# =========================================================================== #
def write_paper_doc() -> str:
    nb = os.path.join(_ROOT, "report04_detector.ipynb")
    with open(nb, encoding="utf-8") as f:
        cells = json.load(f)["cells"]
    if len(cells) <= 22:
        # 옛 노트북(report04_detector.ipynb)이 비워져 논문 부록 셀(c22)이 없다 —
        # 마지막으로 생성된 docs/paper/04_detector.md 를 그대로 보존하고 재생성만 건너뛴다.
        p = os.path.join(_ROOT, "docs", "paper", "04_detector.md")
        print(f"⚠ {os.path.relpath(nb, _ROOT)} 에 셀 23개가 없다({len(cells)}개) — "
              f"논문 조각 재생성을 건너뛰고 기존 {os.path.relpath(p, _ROOT)} 를 보존한다")
        return p

    figs = []
    for c in cells:
        t = "".join(c["source"])
        if t.startswith("<!--pk:figure"):
            meta = json.loads(t.split("\n")[0][len("<!--pk:figure "):-len("-->")])
            figs.append((meta.get("figure_no"), meta.get("path"), meta.get("caption", "")))

    out = ["<!-- 생성물 — `src/build_part09_detector.py:write_paper_doc()` 가 쓴다. -->",
           "<!-- from: 옛 report04_detector.ipynb c22(논문 부록) -->",
           "", "# 논문 조각 — IV. Detection Chain", "",
           "부 9 「검출기」 5편(51~55)이 본문이고, 이 문서는 그 편들에서 **논문으로만** 가는 "
           "조각이다.", "",
           "| 편 | 무엇을 대는가 |", "|---|---|",
           "| 51 chain | 네 단계 사슬과 파형별 형상 |",
           "| 52 eca | 소거 깊이의 바닥과 0-도플러 노치 |",
           "| 53 cfar-calib | 경험 Pfa 측정과 운용 형상 교정표 |",
           "| 54 cfar-why | 배율의 원인(셀 상관)과 형상 의존 |",
           "| 55 observability | FIM 랭크 · CRLB · 수신기 2대 |",
           "", "---", "", "## 그림의 논문 캡션 (완결 문장)", "",
           "| Fig. | 파일 | 캡션 |", "|---|---|---|"]
    for n, p, cap in figs:
        out.append(f"| {n} | `{p}` | {cap} |")
    out += ["", "---", "", "## 논문 부록 — 방법 문단 · 방어선 · 인용 (옛 report04 c22)", "",
            "".join(cells[22]["source"]).strip(), ""]

    d = os.path.join(_ROOT, "docs", "paper")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "04_detector.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return p


#: 편 53 이 리포트 밖으로 보낸 재현 코드(옛 report04 c12).
REPRO_SNIPPET = "\n".join([
    "# 교정표를 실제로 소비하는 지점 — src/passive_process.py:283,338",
    "import os, sys",
    "sys.path.insert(0, os.path.join(os.getcwd(), 'src'))",
    "from passive_process import pfa_nominal_for",
    "",
    "for std in ('wifi', 'lte', 'nr'):",
    "    print(f'{std:4s}  경험 1e-4 목표 → 명목 {pfa_nominal_for(std, 1e-4):.3e}')",
])

BUILD = [
    ("chain", r51, [ECA, CFAR], ["report04_f1_chain"]),
    ("eca", r52, [ECA], ["report04_f2_eca_depth", "report04_f3_eca_notch"]),
    ("cfar-calib", r53, [CFAR, CENSUS], ["report04_f4_pfa"]),
    ("cfar-why", r54, [CFAR], ["report04_f5_cause"]),
    ("observability", r55, [OBS], ["report04_f6_resolution", "report04_f7_observability"]),
]


def main() -> int:
    bad = 0
    for anchor, fn, ev, figs in BUILD:
        rep = build_notebook(nb_path(anchor), fn(), strict=True)
        index_shard(anchor, evidence=ev, figures=figs,
                    md_cells=rep["md_cells"], provenance_tags=rep["provenance_tags"],
                    repro=dict(cmd=CMD, out=ev,
                               snippet=(REPRO_SNIPPET if anchor == "cfar-calib" else None)),
                    builder="src/build_part09_detector.py")
        bad += 0 if rep["ok"] else 1
    print("논문 조각:", os.path.relpath(write_paper_doc(), _ROOT))
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
