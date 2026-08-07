# -*- coding: utf-8 -*-
"""
build_part08_illuminators.py — 부 8 「조명원」 7편(44~50)을 짓는다
==========================================================================================
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py

산출
    reports/44_illuminators.ipynb       상시이면서 내용을 미리 아는 신호는 표준마다 하나씩 있다
    reports/45_5g-double-cost.ipynb     5G 는 좁고 드물다 — 두 배의 대가를 치른다
    reports/46_cost-ledger.ipynb        여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자에서 읽는다
    reports/47_range-convention.ipynb   바이스태틱 거리 분해능은 c/B, 잡음대역은 √(B/fs) 로 고정한다
    reports/48_waveform-check.ipynb     같은 자원격자를 독립 변조기에 넣어 상관 1.0000 을 얻었다
    reports/49_ambiguity.ipynb          검출기가 실제로 쓰는 커널 그대로 모호함수를 그렸다
    reports/50_doppler-fold.ipynb       5G SSB 는 걷는 드론에서 접힌다
    docs/paper/03_illuminators.md       논문 조각(옛 report03 의 §0 + 논문 부록)
    outputs/reports_index/<anchor>.json 편마다 색인 샤드

⭐ 한 편 = 중심 메시지 하나. 제목이 곧 그 편의 결론 문장이다.
⚠ 이 파일은 **서술을 옮길 뿐** 아무것도 새로 계산하지 않는다 — 숫자는 전부 `num()` 이
  근거 JSON 에서 읽고 값을 대조한다. GPU·Sionna 를 쓰지 않는다.
⚠ 근거 JSON(`outputs/*.json`)은 한 줄도 고치지 않는다.

서술 출처 — 옛 `report03_illuminators.ipynb` 의 셀
    c3·c4 → 44 · c5·c6 → 45 · c7~c10 → 46 · c11 → 47 · c13~c15 → 48 ·
    c16~c18 → 49 · c19·c20 → 50 · c2·c21 → docs/paper/03_illuminators.md ·
    c12(코드) → 재현 문서(색인 샤드의 `repro.snippet`)
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
from report_style import (build_notebook, caption, fetch, header, md,  # noqa: E402
                          next_steps, num, table)

# ── 근거 JSON ────────────────────────────────────────────────────────────── #
J_WAVE = "outputs/report2_waveform_rcs.json"     # 파형 제원 + Sionna 교차대조
J_AMB = "outputs/verify_ambiguity.json"          # 모호함수(검출기와 같은 커널)
J_FIX = "outputs/report4_fixups.json"            # 링크버짓 규약 상수
J_LED = "outputs/report03_illuminators.json"     # 대가 원장(파생)
J_MTX = "outputs/report5_results.json"           # 점유 × EIRP 몬테카를로

FIG = "../outputs/figures"
STDS = ("wifi", "lte", "nr")

CMD_ALL = ["cd /home/yunjung/workspace/sionna2",
           "~/.venvs/py312/bin/python src/viz_report2.py",
           "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ambiguity.py",
           "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/report4_fixups.py",
           "PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py"]


def W1(k, f=None, u=""):
    return num(None, (J_WAVE, f"reference.G1.{k}"), f, u)


def A(k, f=None, u=""):
    return num(None, (J_AMB, f"waveforms.{k}"), f, u)


def L(k, f=None, u=""):
    return num(None, (J_LED, k), f, u)


def X(k, f=None, u=""):
    return num(None, (J_WAVE, f"crosscheck.{k}"), f, u)


def F(k, f=None, u=""):
    return num(None, (J_FIX, f"F4_linkbudget.{k}"), f, u)


def fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


# =========================================================================== #
#  편 44 — 상시이면서 내용을 미리 아는 신호는 표준마다 하나씩 있다
# =========================================================================== #
def r44():
    return [
        header(
            num=44,
            title="상시이면서 내용을 미리 아는 신호는 표준마다 하나씩 있다",
            did="WiFi · LTE · 5G NR 세 표준의 자원격자를 규격서대로 세우고, 패시브가 상관에 "
                "걸 수 있는 상시 기준신호를 표준마다 하나씩 골라 제원을 격자에서 직접 쟀다.",
            results=[
                f"두 조건(내용을 미리 안다 · 아무 셀이나 늘 켠다)을 함께 만족하는 신호는 "
                f"표준마다 하나다 — WiFi VHT-LTF($B_{{ref}}$ "
                f"{W1('wifi.ref_bw_mhz', '{:.2f}', 'MHz')}) · "
                f"LTE CRS({W1('lte.ref_bw_mhz', '{:.2f}', 'MHz')}) · "
                f"5G SSB({W1('nr.ref_bw_mhz', '{:.2f}', 'MHz')}).",
                f"거리 눈금 $\\Delta R_b = c/B_{{ref}}$ 는 "
                f"{W1('wifi.dR_m', '{:.1f}')} · {W1('lte.dR_m', '{:.1f}')} · "
                f"{W1('nr.dR_m', '{:.1f}', 'm')} 로 세 표준이 한 자릿수 배 이상 갈린다.",
                f"$B_{{ref}}$ 는 기준신호가 차지한 부반송파의 양끝 span 이라 안쪽 널 톤을 "
                f"포함한다 — WiFi 는 span {W1('wifi.ref_bw_mhz', '{:.3f}', 'MHz')} 가 "
                f"채널 점유대역 {W1('wifi.chan_bw_mhz', '{:.3f}', 'MHz')} 보다 넓다.",
                f"프레임 안에서 기준신호가 실제로 차지하는 몫은 "
                f"{W1('wifi.occ_pct', '{:.2f}', '%')}(WiFi) · "
                f"{W1('lte.occ_pct', '{:.2f}', '%')}(LTE) · "
                f"{W1('nr.occ_pct', '{:.2f}', '%')}(5G) 다.",
            ],
            method=[
                ("자원격자",
                 "`TS 36.211`(CRS) · `TS 38.211`(SSB) · `IEEE 802.11ac`(VHT-LTF) 를 읽어 세웠다 "
                 "— `src/waveforms.py:258`(WiFi) · `:313`(LTE) · `:370`(5G)"),
                ("제원 측정",
                 "선언값을 옮겨 적지 않고 **생성한 격자에서 직접 쟀다** — "
                 "$B_{ref}$ 는 `src/waveforms.py:237`, $\\Delta R_b$ 는 `:144`"),
                ("거리 규약",
                 "바이스태틱 거리합 $R_b = R_1 + R_2 - L$ 이라 분해능은 $c/B_{ref}$ 다 — "
                 "모노스태틱 교과서 값의 두 배다"),
            ],
            repro=dict(cmd=CMD_ALL[:2] + CMD_ALL[-1:], out=[J_WAVE, J_LED],
                       runtime=f"① {num(None, (J_WAVE, 'meta.runtime_s'), '{:.0f}', 's')} "
                               f"(대부분 같은 스크립트의 RCS 스윕) · ② CPU 20초 안쪽"),
        ),

        md("## 패시브가 상관을 걸 수 있는 신호는 어떤 것인가", "",
           "패시브 수신기는 남이 쏘는 신호를 빌려 쓴다. 그 신호에 상관을 걸려면 두 조건이 "
           "**동시에** 서야 한다.", "",
           "**① 내용을 미리 안다.** 데이터는 매 순간 바뀌므로 규격이 고정한 기준신호가 그 자리를 맡는다.", "",
           "**② 아무 셀이나 늘 켠다.** 상시 신호라야 표적이 지나가는 그 순간에도 공중에 있다.", "",
           "두 조건을 다 만족하는 신호는 표준마다 **하나씩**이다."),

        md("## 격자에서 잰 제원", "",
           table(["표준", "상시 기준신호", "반송파", "채널 점유대역", "$B_{ref}$",
                  "$\\Delta R_b=c/B_{ref}$"],
                 [["WiFi 802.11ac", "VHT-LTF", W1("wifi.carrier_ghz", "{:.2f}", "GHz"),
                   W1("wifi.chan_bw_mhz", "{:.1f}", "MHz"), W1("wifi.ref_bw_mhz", "{:.1f}", "MHz"),
                   W1("wifi.dR_m", "{:.1f}", "m")],
                  ["LTE Rel-9", "CRS", W1("lte.carrier_ghz", "{:.3f}", "GHz"),
                   W1("lte.chan_bw_mhz", "{:.1f}", "MHz"), W1("lte.ref_bw_mhz", "{:.1f}", "MHz"),
                   W1("lte.dR_m", "{:.1f}", "m")],
                  ["5G NR Rel-16", "SSB", W1("nr.carrier_ghz", "{:.2f}", "GHz"),
                   W1("nr.chan_bw_mhz", "{:.1f}", "MHz"), W1("nr.ref_bw_mhz", "{:.1f}", "MHz"),
                   W1("nr.dR_m", "{:.1f}", "m")]])),

        md("## $B_{ref}$ 는 span 이다", "",
           "$B_{ref}$ 는 기준신호가 차지한 부반송파의 **양끝 span** 이다"
           "(`src/waveforms.py:237`). 안쪽 널 톤이 그 안에 들어오므로 WiFi 는 span 이 "
           "점유대역보다 넓게 나온다.", "",
           "이 정의가 거리 눈금을 정한다. 채널 대역이 아니라 **상관에 쓰는 대역**이 "
           f"분해능을 만들기 때문이다 — 5G 채널은 {W1('nr.chan_bw_mhz', '{:.1f}', 'MHz')} 인데 "
           f"상시 SSB 체제의 거리 눈금은 {W1('nr.dR_m', '{:.1f}', 'm')} 다. "
           f"채널 대역이 다 열린 체제의 값 {W1('nr.chan_dR_m', '{:.2f}', 'm')} 는 "
           f"{ref('cost-ledger', short=True)} 가 낙관적 상한으로 함께 싣는다.", "",
           f"규약의 정확한 형태는 {ref('range-convention')} 가 든다."),

        md(*fig(1, "report03_f1_grid",
                "유휴 셀이 실제로 켜는 칸은 어디이고, 그중 패시브가 상관에 쓰는 것은 무엇인가?")),

        next_steps([
            ("`src/waveforms.py:112` 의 `PILOT_RATE_HZ` 를 트래픽 시나리오 파라미터로 올린다",
             "WiFi PRF 가 유휴 AP ~ 혼잡 AP 범위로 확정되고 이 편의 제원표가 시나리오별로 선다",
             "`src/waveforms.py:112`"),
            ("X410 으로 실제 셀을 캡처해 격자 좌표를 대조한다",
             "CRS · SSB · VHT-LTF 의 자원요소 좌표가 실측으로 확정된다",
             ref("hardware", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 45 — 5G 는 좁고 드물다
# =========================================================================== #
def r45():
    return [
        header(
            num=45,
            title="5G 는 좁고 드물다 — 두 배의 대가를 치른다",
            did="상시 기준신호 체제에서 LTE CRS 와 5G SSB 를 거리 축과 속도 축 두 곳에서 "
                "나란히 재고, 두 축의 격차를 배수로 적었다.",
            results=[
                f"거리 축 — SSB 는 $B_{{ref}}$ 가 좁아 $\\Delta R_b$ 가 "
                f"{W1('nr.dR_m', '{:.1f}', 'm')} 로 LTE CRS "
                f"{W1('lte.dR_m', '{:.1f}', 'm')} 의 "
                f"{L('ratios.drb_nr_over_lte', '{:.1f}')}배로 거칠다.",
                f"속도 축 — SSB 의 물리 반복률이 {W1('nr.prf_hz', '{:.0f}', 'Hz')} 라 무모호 속도가 "
                f"{W1('nr.vmax_ms', '{:.2f}', 'm/s')} 다. LTE CRS 는 "
                f"{W1('lte.vmax_ms', '{:.1f}', 'm/s')} 로 "
                f"{L('ratios.vmax_lte_over_nr', '{:.0f}')}배 넓다.",
                f"두 축 위에 반송파 항이 하나 더 얹힌다 — LTE→5G 의 $\\lambda^2$ 는 "
                f"{L('lambda2.lte_to_nr_db', '{:.2f}', 'dB')} 다.",
                "PRS 는 측위 세션이 설정될 때 켜지는 옵션이고, 남의 셀을 빌리는 수신기의 "
                "기본선은 상시 SSB 다 — PRS 를 켠 수치는 낙관적 상한으로 읽는다.",
            ],
            method=[
                ("두 축의 정의",
                 "거리 축은 $B_{ref}$ 가, 속도 축은 물리 반복률이 정한다 — 둘 다 규격이 고정한 "
                 "자원격자에서 나오는 닫힌형이다"),
                ("비교 체제",
                 "상시 기준신호 체제(G1)에서 잰다. PRS 체제(G2·G3)는 같은 그림에 함께 싣고 "
                 "낙관적 상한으로 읽는다"),
                ("$\\lambda^2$ 항",
                 "EIRP 고정 · 수신 안테나 **이득** 고정 전제에서 선다 — `src/freespace_link.py:371`"),
            ],
            prereq=[(ref("illuminators", short=True), "세 표준의 상시 기준신호와 그 제원")],
            repro=dict(cmd=CMD_ALL[:2] + CMD_ALL[-1:], out=[J_WAVE, J_LED],
                       runtime="CPU 20초 안쪽 (JSON 을 읽어 노트북을 조립한다)"),
        ),

        md("## 세대가 최신일수록 조명원으로 유리하다는 통념", "",
           "이 통념을 세 항목이 뒤집는다. 5G 는 채널이 넓지만 **상시로 켜는 부분**은 좁고, "
           "그 부분이 다시 오는 간격은 길다. 패시브가 빌려 쓰는 것은 채널이 아니라 그 좁은 "
           "상시 부분이다.", "",
           "**PRS 는 측위 세션이 설정될 때 켜지는 옵션**이고, 남의 셀을 빌리는 패시브 수신기의 "
           "기본선은 상시 신호인 **SSB** 다."),

        md("## 두 축에서 각각 얼마인가", "",
           table(["축", "정하는 것", "LTE CRS", "5G SSB", "격차"],
                 [["거리 $\\Delta R_b$", "$B_{ref}$", W1("lte.dR_m", "{:.1f}", "m"),
                   W1("nr.dR_m", "{:.1f}", "m"),
                   f"{L('ratios.drb_nr_over_lte', '{:.1f}')}배 거칢"],
                  ["속도 $v_{max}$ (물리 PRF)", "PRF", W1("lte.vmax_ms", "{:.1f}", "m/s"),
                   W1("nr.vmax_ms", "{:.2f}", "m/s"),
                   f"{L('ratios.vmax_lte_over_nr', '{:.0f}')}배 넓음"]]),
           "",
           f"여기에 반송파가 $\\lambda^2$ {L('lambda2.lte_to_nr_db', '{:.2f}', 'dB')} 를 더한다 "
           f"— 그 항의 성립 조건과 크기는 {ref('cost-ledger', short=True)} 가 든다."),

        md(*fig(1, "report03_f2_reference",
                "기준신호의 넓이와 반복이 거리·속도 눈금을 각각 얼마로 정하는가?")),

        md("## 속도 축의 대가는 접힘으로 나타난다", "",
           f"SSB 의 반복률 {W1('nr.prf_hz', '{:.0f}', 'Hz')} 는 걷는 속도의 드론에서도 도플러를 "
           f"접는다. 그 접힘을 실제 커널에서 잰 값이 "
           f"{ref('doppler-fold', short=True)} 에 있다.", "",
           f"거리 축의 대가는 조명원 선택의 dB 원장에 다른 항목과 함께 들어간다 — "
           f"{ref('cost-ledger', short=True)}."),

        next_steps([
            ("PRS 를 켠 체제에서 같은 두 축을 다시 잰다",
             "낙관적 상한과 상시 기준선이 거리·속도 축에서 각각 몇 배 갈리는지 확정된다",
             "`src/waveforms.py:370` → " + ref("cost-ledger", short=True)),
            ("실측 설계에서 수신 안테나를 확정하고 $\\lambda^2$ 항의 전제를 다시 잰다",
             f"$\\lambda^2$ {L('lambda2.span_db', '{:.2f}', 'dB')} 의 부호가 실제 안테나에서 확정된다",
             "`src/freespace_link.py:371` → " + ref("hardware", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 46 — 대가 원장
# =========================================================================== #
def r46():
    return [
        header(
            num=46,
            title="여섯 항목은 닫힌형이고, 점유 대가만 몬테카를로 격자에서 읽는다",
            did="조명원 선택이 무는 dB 격차를 항목별로 모아 원장을 만들고, 항목마다 그 값을 "
                "닫는 방식이 무엇인지를 함께 적었다.",
            results=[
                f"원장 항목은 전부 **같은 표적·같은 기하에서 잰 두 양의 비**라 표적 σ 가 "
                f"분자와 분모에서 상쇄된다 — 반송파 $\\lambda^2$ "
                f"{L('lambda2.span_db', '{:.2f}', 'dB')}(밴드 양끝) · WiFi 패킷 듀티 "
                f"{F('wifi_pilot_fraction.packet_duty_db', '{:.2f}', 'dB')} · CPI 규약 "
                f"{F('cpi_asymmetry.span_db', '{:.2f}', 'dB')}.",
                f"여섯 항목은 자원격자 · 반송파 · 관측시간에서 **닫힌형**으로 나온다.",
                f"점유 대가만 검출 몬테카를로의 EIRP 격자에서 **읽은** 값이다 — 격자점 차 "
                f"{L('occupancy_cost.value_db', '{:.0f}', 'dB')}, 참값 구간 "
                f"{L('occupancy_cost.bracket_lo_db', '{:.0f}')}~"
                f"{L('occupancy_cost.bracket_hi_db', '{:.0f}', 'dB')}, $P_d$ 선형보간 "
                f"{L('occupancy_cost.interp_db', '{:.1f}', 'dB')}.",
                f"그 격자는 눈금 {L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')} · 시행 "
                f"{L('occupancy_cost.n_trials', '{:.0f}')}회 · 표적 {L('occupancy_cost.drone')} · "
                f"{L('occupancy_cost.scen')} 한 점에서 읽었다.",
            ],
            method=[
                ("항목의 형태",
                 "전부 두 양의 비다 — $\\lambda^2$ 는 반송파 비, 듀티는 시간 비, "
                 "기준신호 에너지는 자원격자 위의 에너지 비"),
                ("점유 대가",
                 f"같은 표적·같은 기하에서 $P_d$ {L('occupancy_cost.pd_threshold', '{:.1f}')} 를 "
                 f"넘기는 EIRP 차를 "
                 f"{L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')} 격자에서 읽는다"),
                ("부호 규약",
                 "표의 부호는 원본 JSON 그대로이고, 그림은 **음수 = 손해**로 부호를 맞춰 "
                 "다시 그린 것이다"),
                ("점유 대가 안에 든 것",
                 "G1→G3 은 점유율과 함께 기준신호 대역도 "
                 f"{L('occupancy_cost.ref_bw_G1_mhz', '{:.1f}', 'MHz')} → "
                 f"{L('occupancy_cost.ref_bw_G3_mhz', '{:.2f}', 'MHz')} 로 넓어진 값이다 — "
                 "두 항을 가르는 대역고정 스윕은 다음 단계에 있다"),
            ],
            prereq=[(ref("5g-double-cost", short=True), "5G 가 거리·속도 두 축에서 무는 대가")],
            repro=dict(cmd=CMD_ALL, out=[J_WAVE, J_FIX, J_MTX, J_LED],
                       runtime=f"③ {num(None, (J_FIX, '_meta.runtime_s'), '{:.0f}', 's')} · "
                               f"④ CPU 20초 안쪽",
                       note=f"`{J_MTX}` 는 검출 몬테카를로가 이미 남긴 것이다 — 이 편은 그중 "
                            f"`A_occupancy` 만 인용한다(재실행 불필요)."),
        ),

        md("## 원장 — 무엇이 각 항목의 유효숫자를 정하나", "",
           "조명원 선택이 만드는 dB 격차를 한 표에 모은다. 오른쪽 열이 그 항목을 **닫는 방식**이다."),

        md(table(["항목", "값", "무엇의 비인가", "닫는 방식"],
                 [["점유 대가 (5G · 상시 vs 풀로드)", L("occupancy_cost.value_db", "{:.0f}", "dB"),
                   f"같은 표적·같은 기하에서 $P_d$ "
                   f"{L('occupancy_cost.pd_threshold', '{:.1f}')} 를 넘기는 EIRP 차",
                   "몬테카를로 격자 읽기"],
                  ["기준신호 에너지 격차 (같은 쌍)",
                   L("ref_energy_gap_G1_to_G3_db.nr", "{:.2f}", "dB"),
                   "$E_{ref}$(G3) / $E_{ref}$(G1) — 상관에 쓰는 에너지만", "닫힌형 — 자원격자"],
                  ["반송파 $\\lambda^2$ (LTE→WiFi)", L("lambda2.lte_to_wifi_db", "{:.2f}", "dB"),
                   "$20\\log_{10}(\\lambda/\\lambda_{ref})$ — EIRP·수신이득 고정", "닫힌형 — 반송파"],
                  ["반송파 $\\lambda^2$ (LTE→5G)", L("lambda2.lte_to_nr_db", "{:.2f}", "dB"),
                   "위와 같음", "닫힌형 — 반송파"],
                  ["WiFi 파일럿 / 총 송신 에너지",
                   F("wifi_pilot_fraction.pilot_over_tx_energy_db", "{:.2f}", "dB"),
                   "G3 격자에서 상관에 쓰는 몫", "닫힌형 — 자원격자"],
                  ["WiFi 패킷 듀티", F("wifi_pilot_fraction.packet_duty_db", "{:.2f}", "dB"),
                   "패킷이 공중에 있는 시간 비율", "닫힌형 — 시간"],
                  ["CPI 규약 격차", F("cpi_asymmetry.span_db", "{:.2f}", "dB"),
                   "같은 프레임 수 M 이 5G 에 주는 관측시간이 절반", "닫힌형 — 관측시간"]])),

        md("## 각 항목이 서는 조건", "",
           table(["항목", "성립 조건", "크기"],
                 [["반송파 $\\lambda^2$",
                   "EIRP 고정 · 수신 안테나 **이득** 고정 (`src/freespace_link.py:371`)",
                   "수신 **개구면적**을 고정하면 부호가 뒤집힌다"],
                  ["CPI 규약", "같은 M 이 5G 에 주는 관측시간이 절반",
                   F("cpi_asymmetry.span_db", "{:.2f}", "dB") + " — 뒤 편들은 관측시간을 맞춘 뒤 비교한다"],
                  ["WiFi 두 항목", "에너지 비 · 시간 비 — 서로 다른 양이다",
                   F("wifi_pilot_fraction.pilot_over_tx_energy_db", "{:.2f}", "dB") + " · "
                   + F("wifi_pilot_fraction.packet_duty_db", "{:.2f}", "dB")]])),

        md("## 점유 대가는 왜 격자에서 읽는가", "",
           f"이 항목만 닫힌형이 없다. 같은 표적·같은 기하에서 $P_d$ "
           f"{L('occupancy_cost.pd_threshold', '{:.1f}')} 를 넘기는 EIRP 를 상시 체제와 풀로드 "
           f"체제에서 각각 찾아 그 차를 읽는다. 격자 눈금이 유효숫자를 정한다.", "",
           table(["무엇", "값"],
                 [["격자점 차", L("occupancy_cost.value_db", "{:.0f}", "dB")],
                  ["참값 구간", L("occupancy_cost.bracket_lo_db", "{:.0f}") + "~"
                   + L("occupancy_cost.bracket_hi_db", "{:.0f}", "dB")],
                  ["$P_d$ 선형보간", L("occupancy_cost.interp_db", "{:.1f}", "dB")],
                  ["격자 눈금 · 시행", L("occupancy_cost.eirp_grid_step_db", "{:.0f}", "dB")
                   + " · " + L("occupancy_cost.n_trials", "{:.0f}") + "회"],
                  ["기준신호 대역 (G1 → G3)",
                   L("occupancy_cost.ref_bw_G1_mhz", "{:.1f}", "MHz") + " → "
                   + L("occupancy_cost.ref_bw_G3_mhz", "{:.2f}", "MHz")]])),

        md(*fig(1, "report03_f3_occupancy",
                "셀이 데이터로 바빠지면 패시브의 거리분해능도 같이 좋아지는가?")),

        md(*fig(2, "report03_f4_ledger",
                "조명원 선택이 무는 대가는 항목별로 몇 dB 인가?")),

        md("## 이 원장이 σ 논의와 독립인 이유", "",
           "항목마다 분자와 분모가 같은 표적·같은 기하에서 나온다. 그래서 표적 σ 의 절대레벨이 "
           "X dB 움직여도 세 조명원의 **순위와 격차는 그대로**이고, 움직이는 것은 절대 검출거리뿐이다.", "",
           f"검출 결과 편들이 여기에 σ 와 기하를 곱해 절대 거리를 낸다 — "
           f"{ref('sensitivity-chain')}."),

        next_steps([
            (f"EIRP 격자를 {L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')} 에서 2 dB 로 "
             f"좁히고 기준신호 대역을 고정한 점유 스윕을 돌린다",
             f"{L('occupancy_cost.value_db', '{:.1f}', 'dB')} 안에서 점유 항과 대역 항의 크기가 갈린다",
             "`benchmark/run_matrix.py:300`"),
            (f"표적 {L('occupancy_cost.drone')} · 시나리오 {L('occupancy_cost.scen')} 한 점에서 "
             f"읽은 점유 대가를 기체·기하로 넓힌다",
             "점유 대가가 표적·기하에 얼마나 의존하는지가 수치로 확정된다",
             ref("r90", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 47 — 거리·잡음대역 규약
# =========================================================================== #
def r47():
    return [
        header(
            num=47,
            title="바이스태틱 거리 분해능은 c/B, 잡음대역은 √(B/fs) 로 고정한다",
            did="이 프로젝트가 쓰는 거리 분해능과 잡음대역 정규화의 정의를 하나로 고정하고, "
                "모노스태틱 교과서 값과의 배수를 표에 적었다.",
            results=[
                f"거리축은 바이스태틱 거리합 $R_b = R_1 + R_2 - L$ 이라 분해능이 "
                f"$\\Delta R_b = c/B_{{ref}}$ 다. 모노스태틱 교과서 값 $c/2B$ 는 그 절반이고, 비는 "
                f"{num(None, (J_FIX, 'F3_ambiguity.resolution_convention_conflict.rows[0].factor'), '{:.0f}')}"
                f"배다.",
                f"세 파형의 값은 {A('wifi_G1.dR_theory_m', '{:.2f}')} · "
                f"{A('lte_G1.dR_theory_m', '{:.2f}')} · "
                f"{A('nr_G1.dR_theory_m', '{:.2f}', 'm')} 이고, 모노 등가는 각각 "
                f"{A('wifi_G1.dR_mono_theory_m', '{:.2f}')} · "
                f"{A('lte_G1.dR_mono_theory_m', '{:.2f}')} · "
                f"{A('nr_G1.dR_mono_theory_m', '{:.2f}', 'm')} 다.",
                f"잡음대역 정규화는 $\\sqrt{{B/f_s}}$ 로 고정한다 — 세 파형의 $B/f_s$ 는 "
                f"{F('straddle.rows[0].b_over_fs', '{:.4f}')} · "
                f"{F('straddle.rows[1].b_over_fs', '{:.4f}')} · "
                f"{F('straddle.rows[2].b_over_fs', '{:.4f}')} 다.",
                "두 규약을 섞으면 분해능을 그 배수만큼 낙관하게 된다 — 그래서 한 곳에서 정의하고 "
                "모든 편이 그 정의를 인용한다.",
            ],
            method=[
                ("거리 규약",
                 "$R_b = c\\tau$ 에 계수 2 가 없다. 그래서 $\\Delta R_b = c/B_{ref}$ 이고, "
                 "모노스태틱 $c/2B$ 는 그 절반이다"),
                ("잡음대역 정규화",
                 "선언 대역 $B$ 와 표본율 $f_s$ 가 다르면 주입 진폭을 $\\sqrt{B/f_s}$ 만큼 "
                 "낮춘다 — `benchmark/run_min_cell.py:131`"),
                ("행 순서 검사",
                 "$B/f_s$ 행이 (WiFi, LTE, 5G) 순서인지 격자에서 다시 계산해 대조한다. "
                 "행이 뒤섞이면 빌드가 멈춘다"),
            ],
            prereq=[(ref("illuminators", short=True), "$B_{ref}$ 가 어떻게 정의되는가")],
            repro=dict(cmd=CMD_ALL[2:], out=[J_AMB, J_FIX],
                       runtime="② GPU 1장 수 분 · ③ "
                               + num(None, (J_FIX, "_meta.runtime_s"), "{:.0f}", "s")),
        ),

        md("## 거리 규약 — 바이스태틱 $c/B$", "",
           "송신기와 수신기가 다른 자리에 있으면 표적이 만드는 지연은 두 경로의 합에서 "
           "직접경로를 뺀 값이다. 그 축에서 분해능은 $c/B_{ref}$ 이고, 모노스태틱 교과서 값 "
           "$c/2B$ 는 그 절반이다.", "",
           table(["파형", "$B/f_s$", "$\\Delta R_b = c/B_{ref}$", "모노 등가 $c/2B$"],
                 [[fetch((J_FIX, f"F4_linkbudget.straddle.rows[{i}].name")),
                   num(None, (J_FIX, f"F4_linkbudget.straddle.rows[{i}].b_over_fs"), "{:.4f}"),
                   num(None, (J_AMB, f"waveforms.{k}_G1.dR_theory_m"), "{:.2f}", "m"),
                   num(None, (J_AMB, f"waveforms.{k}_G1.dR_mono_theory_m"), "{:.2f}", "m")]
                  for i, k in enumerate(STDS)])),

        md("## 분해능과 격자 간격은 다른 양이다", "",
           "$\\Delta R_b$ 는 **선언 규약**이고, 표본율이 정하는 거리 빈 $c/f_s$ 는 격자 간격이다. "
           "두 값을 한 표에 병기해 섞이지 않게 둔다.", "",
           f"검출기 쪽에서 같은 규약을 쓰고 같은 값을 싣는 표가 "
           f"{ref('observability')} 에 있다."),

        md("## 잡음대역 정규화 — $\\sqrt{B/f_s}$", "",
           "선언 대역 $B$ 와 표본율 $f_s$ 가 다르면 표본당 잡음이 그만큼 달라진다. 주입 진폭을 "
           "$\\sqrt{B/f_s}$ 로 낮춰야 매치드필터 출력 SNR 이 파형 간 공정해진다"
           "(`benchmark/run_min_cell.py:131`).", "",
           "이 규약이 있어야 대역이 다른 세 파형을 하나의 SNR 축에 올릴 수 있다. "
           f"그 축 위에서 세 파형을 비교한 결과가 {ref('shared-threshold')} 다."),

        next_steps([
            ("두 거리 규약이 섞이지 않았는지 검출기 설정 검사에 한 줄로 넣는다",
             "규약 혼용이 조용히 지나가지 않고 빌드에서 멈춘다",
             "`src/passive_process.py:383`"),
            ("$\\sqrt{B/f_s}$ 규약을 X410 캡처 경로에도 건다",
             "실측 SNR 축이 시뮬 축과 같은 정규화 위에 선다",
             "`src/experiment_x410.py` → " + ref("hardware", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 48 — 파형 검증
# =========================================================================== #
def r48():
    return [
        header(
            num=48,
            title="같은 자원격자를 독립 변조기에 넣어 상관 1.0000 을 얻었다",
            did="우리 변조기와 Sionna PHY 의 `OFDMModulator` 에 같은 자원격자를 넣고 두 시간파형의 "
                "상관과 NMSE 를 재, 변조 단계를 독립 구현으로 채점했다.",
            results=[
                f"세 파형 모두 상관이 소수 넷째 자리까지 1 이다 — WiFi {X('wifi.corr', '{:.4f}')} · "
                f"LTE {X('lte.corr', '{:.4f}')} · 5G {X('nr.corr', '{:.4f}')}.",
                f"NMSE 는 WiFi {X('wifi.nmse_db', '{:.1f}')} · LTE {X('lte.nmse_db', '{:.1f}')} · "
                f"5G {X('nr.nmse_db', '{:.1f}', 'dB')} 로 float32 반올림 바닥에 붙는다.",
                f"대조의 **분해력**을 같은 표에 싣는다 — 심볼별 CP 배열 대신 첫 CP 스칼라만 넘기면 "
                f"LTE 상관이 {X('lte.corr_bug', '{:.2f}')}, 5G 가 {X('nr.corr_bug', '{:.2f}')} 로 "
                f"무너진다. CP 가 심볼마다 같은 WiFi 는 {X('wifi.corr_bug', '{:.4f}')} 로 남는다.",
                f"대조는 G3(풀로드) 격자에서 돈다 — 표본 수 {X('nr.n', '{:.0f}')} · $f_s$ "
                f"{X('nr.fs_mhz', '{:.2f}', 'MHz')}(5G 기준).",
            ],
            method=[
                ("무엇을 채점하나",
                 "격자를 신호로 바꾸는 **변조 단계**다 — IFFT 규약(fftshift 방향·정규화), CP 복사, "
                 "심볼별 이어붙이기 순서"),
                ("상대 구현",
                 "`sionna.phy.ofdm.OFDMModulator`(Sionna 2.0.1) — 우리 코드를 한 줄도 공유하지 않는다"),
                ("분해력 시험",
                 "재변조 쪽에 심볼별 CP 배열 대신 첫 CP 스칼라만 넘기는 대조군을 함께 돌려, "
                 "대조가 무엇을 잡아낼 수 있는지를 같은 표에 적는다"),
                ("자원격자 자체",
                 "파일럿 좌표·가드밴드·DC 널은 규격서를 읽어 `src/waveforms.py` 에 세웠고, "
                 "X410 캡처 대조는 실측 캠페인이 한다"),
            ],
            prereq=[(ref("illuminators", short=True), "세 표준의 자원격자와 상시 기준신호")],
            repro=dict(cmd=CMD_ALL[:2] + CMD_ALL[-1:], out=[J_WAVE],
                       runtime=f"① {num(None, (J_WAVE, 'meta.runtime_s'), '{:.0f}', 's')} · "
                               f"② CPU 20초 안쪽"),
        ),

        md("## 무엇을 채점하는가", "",
           "격자를 신호로 바꾸는 **변조 단계**를 독립 구현으로 채점한다. 같은 자원격자를 "
           "Sionna PHY 의 `sionna.phy.ofdm.OFDMModulator` 에 넣고, 우리 변조기 출력과 "
           "상관·NMSE 를 잰다.", "",
           table(["이 대조가 확인하는 것", "무엇으로"],
                 [["IFFT 규약 — fftshift 방향 · 정규화", "두 구현의 시간파형 상관"],
                  ["CP 복사와 심볼별 이어붙이기 순서", "심볼별 CP 배열을 뺀 대조군과 비교"],
                  ["두 독립 구현의 시간파형 일치", "NMSE 바닥"]])),

        md(*fig(1, "report03_f5_crosscheck",
                "같은 자원격자를 두 변조기에 넣으면 같은 시간파형이 나오는가?")),

        md("## 채점 결과", "",
           table(["표준", "표본 수", "$f_s$", "상관", "NMSE", "CP 앞머리", "CP 배열을 뺀 대조군"],
                 [["WiFi 802.11ac", X("wifi.n", "{:.0f}"), X("wifi.fs_mhz", "{:.2f}", "MHz"),
                   X("wifi.corr", "{:.4f}"), X("wifi.nmse_db", "{:.1f}", "dB"),
                   f"`{fetch((J_WAVE, 'crosscheck.wifi.cp_head'))}`", X("wifi.corr_bug", "{:.4f}")],
                  ["LTE Rel-9", X("lte.n", "{:.0f}"), X("lte.fs_mhz", "{:.2f}", "MHz"),
                   X("lte.corr", "{:.4f}"), X("lte.nmse_db", "{:.1f}", "dB"),
                   f"`{fetch((J_WAVE, 'crosscheck.lte.cp_head'))}`", X("lte.corr_bug", "{:.4f}")],
                  ["5G NR Rel-16", X("nr.n", "{:.0f}"), X("nr.fs_mhz", "{:.2f}", "MHz"),
                   X("nr.corr", "{:.4f}"), X("nr.nmse_db", "{:.1f}", "dB"),
                   f"`{fetch((J_WAVE, 'crosscheck.nr.cp_head'))}`", X("nr.corr_bug", "{:.4f}")]])),

        md("## 마지막 열이 대조의 분해력이다", "",
           "두 구현이 같은 오해를 공유하면 대조가 통과해도 정보가 0 이다. 그 반론에 미리 답하려고 "
           "**일부러 틀린 대조군**을 같은 표에 싣는다.", "",
           "재변조 쪽에 심볼별 CP 배열 대신 첫 CP 스칼라만 넘기면 두 번째 심볼부터 시간축이 "
           "어긋난다. CP 길이가 심볼마다 다른 LTE·5G 에서 상관이 무너지고, CP 가 심볼마다 같은 "
           "WiFi 는 그대로 1 이다 — 대조가 무엇을 잡아내는지가 그 열에 적혀 있다."),

        next_steps([
            ("X410 으로 실제 셀을 캡처해 `src/waveforms.py` 의 격자와 대조한다",
             "CRS · SSB · VHT-LTF 의 격자 좌표가 실측으로 확정된다",
             ref("hardware", short=True)),
            ("복조·등화 단계까지 같은 방식으로 채점한다",
             "변조 밖 사슬의 독립 대조가 어디까지 서는지가 확정된다",
             "`src/waveforms_sionna.py`"),
        ]),
    ]


# =========================================================================== #
#  편 49 — 모호함수
# =========================================================================== #
def r49():
    return [
        header(
            num=49,
            title="검출기가 실제로 쓰는 커널 그대로 모호함수를 그렸다",
            did="기준신호 하나가 거리-도플러 평면에 만드는 응답을 검출기와 같은 커널로 계산하고, "
                "검출기의 거리도플러 출력과 대조해 두 값의 최대 편차를 쟀다.",
            results=[
                f"모호함수와 검출기 거리도플러 출력은 최대 "
                f"{L('detector_af_max_err_db.value', '{:.3f}', 'dB')} 안에서 같다 "
                f"({L('detector_af_max_err_db.n_cases', '{:.0f}')}개 경우, −45 dB 이상 셀).",
                f"거리 주엽은 $c/B_{{ref}}$ 예측의 {A('wifi_G1.dR_ratio', '{:.0%}')} ~ "
                f"{A('nr_G1.dR_ratio', '{:.0%}')} 다(G1 세 파형).",
                f"도플러 주엽은 여섯 경우 모두 $1/T_{{CPI}}$ 의 "
                f"{A('wifi_G1.dF_ratio', '{:.2f}')}배 근처이고, 이 배수는 파형이 아니라 "
                f"slow-time Hann 창이 정한다(`src/passive_process.py:142`).",
                f"부엽과 ±PRF 레플리카는 표준마다 다르다 — 2D 부엽 최대가 "
                f"LTE {A('lte_G1.psl_2d_db', '{:.1f}')} · 5G {A('nr_G1.psl_2d_db', '{:.1f}', 'dB')} 이고, "
                f"레플리카는 WiFi {A('wifi_G1.doppler_replica_db', '{:.2f}')} · "
                f"LTE {A('lte_G1.doppler_replica_db', '{:.2f}', 'dB')} 다.",
            ],
            method=[
                ("커널",
                 "검출기가 쓰는 것과 **같은 커널**로 계산한다 — `benchmark/verify_ambiguity.py:150`, "
                 "검출기는 `src/passive_process.py:133`"),
                ("대조 방식",
                 "표준 × 점유 경우마다 −45 dB 이상 셀의 최대 편차를 재고 그 최대값을 싣는다"),
                ("슬로타임 창",
                 "프레임과 프레임 사이 축에 Hann 창을 씌운다 — 도플러 주엽의 배수를 정하는 것이 "
                 "이 창이다(`src/passive_process.py:142`)"),
                ("이 표의 PRF",
                 "**검출기 프레임률**이다. 물리 주기 기준의 접힘은 따로 잰다"),
            ],
            prereq=[(ref("range-convention", short=True), "$\\Delta R_b$ 와 잡음대역 규약")],
            repro=dict(cmd=CMD_ALL[2:3] + CMD_ALL[-1:], out=[J_AMB, J_LED],
                       runtime="② GPU 1장 수 분 · ④ CPU 20초 안쪽"),
        ),

        md("## 모호함수는 검출기의 눈이다", "",
           "모호함수 $\\chi(\\tau, f_d)$ 는 기준신호 하나가 거리-도플러 평면에 만드는 응답이다. "
           "표적이 점 하나여도 검출기 화면에는 이 모양이 찍힌다.", "",
           f"우리가 그리는 것은 **검출기가 쓰는 것과 같은 커널**이고, 검출기의 거리도플러 출력과 "
           f"최대 {L('detector_af_max_err_db.value', '{:.3f}', 'dB')} "
           f"({L('detector_af_max_err_db.n_cases', '{:.0f}')}개 경우, −45 dB 이상 셀) 안에서 같다. "
           f"따로 계산한 그림이 아니라 **검출기 자신의 눈**이라는 뜻이다."),

        md("## 주엽 — 닫힌형과 대조", "",
           f"거리 주엽(응답에서 가장 높이 솟은 가운데 봉우리)은 $c/B_{{ref}}$ 예측의 "
           f"{A('wifi_G1.dR_ratio', '{:.0%}')} ~ {A('nr_G1.dR_ratio', '{:.0%}')} 다(G1 세 파형).", "",
           f"도플러 주엽은 여섯 경우 모두 $1/T_{{CPI}}$ 의 {A('wifi_G1.dF_ratio', '{:.2f}')}배 "
           f"근처이고, 이 배수는 파형이 아니라 **slow-time Hann 창**(프레임과 프레임 사이 축에 "
           f"씌워 가장자리를 깎는 창)이 정한다."),

        md(*fig(1, "report03_f6_af_mainlobe",
                "측정한 모호함수 주엽이 닫힌형 예측과 몇 % 안에서 맞는가?")),

        md("## 부엽과 도플러 레플리카", "",
           "주엽 밖으로 새는 에너지는 두 가지로 나타난다. **부엽**은 강한 표적이 평면 다른 곳의 "
           "약한 표적을 덮는 정도이고, **±PRF 레플리카**는 무모호 속도를 넘은 표적이 되접혀 "
           "들어오는 세기다.", "",
           table(["기준신호", "2D 부엽 최대", "±PRF 레플리카", "프레임 내 시간점유"],
                 [["WiFi VHT-LTF", A("wifi_G1.psl_2d_db", "{:.1f}", "dB"),
                   A("wifi_G1.doppler_replica_db", "{:.2f}", "dB"),
                   A("wifi_G1.ref_time_duty", "{:.1%}")],
                  ["LTE CRS", A("lte_G1.psl_2d_db", "{:.1f}", "dB"),
                   A("lte_G1.doppler_replica_db", "{:.2f}", "dB"),
                   A("lte_G1.ref_time_duty", "{:.1%}")],
                  ["5G SSB", A("nr_G1.psl_2d_db", "{:.1f}", "dB"),
                   A("nr_G1.doppler_replica_db", "{:.2f}", "dB"),
                   A("nr_G1.ref_time_duty", "{:.1%}")]])),

        md("## 레플리카를 정하는 것은 점유율이 아니다", "",
           "레플리카의 세기를 정하는 것은 **에너지가 프레임 안에 얼마나 퍼져 있는가**다. "
           "CRS 처럼 프레임 전체에 흩어지면 위상이 상쇄돼 레플리카가 죽고, LTF·SSB 처럼 앞쪽에 "
           "뭉치면 그대로 남는다.", "",
           "이 표의 PRF 는 **검출기 프레임률**이다. 물리 주기 기준의 접힘은 "
           + ref("doppler-fold", short=True) + " 가 따로 잰다 — 그 편이 같은 표를 "
           "물리 반복률로 다시 세운다."),

        next_steps([
            (f"`benchmark/run_min_cell.py:74` 의 `frame_len()` 을 물리 SSB 주기"
             f"({A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')})로 확장한다",
             f"검출기 프레임률({A('nr_G1.physical.prf_model_hz', '{:.0f}', 'Hz')})과 "
             f"{A('nr_G1.physical.ratio', '{:.0f}')}배 벌어진 이 편의 표가 한 규약 위에 선다",
             "`benchmark/verify_ambiguity.py:108`"),
            ("부엽 최대를 표적 두 개가 있는 장면에서 다시 잰다",
             "강한 표적이 약한 표적을 덮는 거리가 수치로 확정된다",
             "`benchmark/verify_ambiguity.py`"),
        ]),
    ]


# =========================================================================== #
#  편 50 — 접힘
# =========================================================================== #
def r50():
    return [
        header(
            num=50,
            title="5G SSB 는 걷는 드론에서 접힌다",
            did="세 기준신호의 **물리** 반복률에서 무모호 도플러를 계산하고, 기준 표적 속도의 참 "
                "도플러가 어디로 접히는지를 같은 표에 적었다.",
            results=[
                f"SSB 의 물리 반복률은 {A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')} 이고 "
                f"무모호 속도가 {A('nr_G1.physical.v_unamb_phys_ms', '{:.2f}', 'm/s')} 다 — "
                f"걷는 속도의 드론이 그 위에 있다.",
                f"기준 표적 속도에서 참 도플러 "
                f"{A('nr_G1.physical.fd_true_hz', '{:.1f}', 'Hz')} 가 "
                f"{A('nr_G1.physical.fd_aliased_phys_hz', '{:.1f}', 'Hz')} 로 접힌다.",
                f"같은 조건에서 WiFi 는 무모호 속도 "
                f"{A('wifi_G1.physical.v_unamb_phys_ms', '{:.1f}', 'm/s')}, LTE 는 "
                f"{A('lte_G1.physical.v_unamb_phys_ms', '{:.1f}', 'm/s')} 로 참 도플러를 그대로 "
                f"유지한다.",
                f"접힘을 정하는 것은 물리 반복률 하나다 — CPI 는 도플러 가드 폭을 정하고, "
                f"모호속도는 표본화율의 성질이라 CPI 로 안 움직인다.",
            ],
            method=[
                ("물리 반복률",
                 "`TS 38.213` 의 기본 SSB 주기가 반복률을 고정한다. 검출기 프레임률과 다른 양이라 "
                 "이름을 갈라 싣는다"),
                ("접힘 계산",
                 "무모호 도플러 ±PRF/2 를 넘는 참 도플러를 그 구간으로 되접어 아래 표에 적는다"),
                ("기준 표적 속도",
                 "이 프로젝트의 기준 표적 속도 하나에서 계산한다 — 속도를 바꾸면 접힌 자리도 바뀐다"),
            ],
            prereq=[(ref("5g-double-cost", short=True), "5G 가 거리·속도 두 축에서 무는 대가"),
                    (ref("ambiguity", short=True), "검출기 커널이 만드는 응답의 모양")],
            repro=dict(cmd=CMD_ALL[2:3] + CMD_ALL[-1:], out=[J_AMB],
                       runtime="② GPU 1장 수 분 · ④ CPU 20초 안쪽"),
        ),

        md(*fig(1, "report03_f7_af_sidelobe",
                "각 기준신호는 표적 에너지를 부엽과 도플러 레플리카에 얼마나 남기는가?")),

        md("## 물리 반복률이 무모호 속도를 정한다", "",
           table(["기준신호", "물리 PRF", "무모호 속도", "접히는가"],
                 [["WiFi VHT-LTF", A("wifi_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                   A("wifi_G1.physical.v_unamb_phys_ms", "{:.1f}", "m/s"),
                   A("wifi_G1.physical.aliased")],
                  ["LTE CRS", A("lte_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                   A("lte_G1.physical.v_unamb_phys_ms", "{:.1f}", "m/s"),
                   A("lte_G1.physical.aliased")],
                  ["5G SSB", A("nr_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                   A("nr_G1.physical.v_unamb_phys_ms", "{:.2f}", "m/s"),
                   A("nr_G1.physical.aliased")]])),

        md("## 접힌 자리는 어디인가", "",
           f"기준 표적 속도에서 5G 의 참 도플러 "
           f"{A('nr_G1.physical.fd_true_hz', '{:.1f}', 'Hz')} 가 무모호 구간 "
           f"±{A('nr_G1.physical.fd_unamb_phys_hz', '{:.0f}', 'Hz')} 안으로 되접혀 "
           f"{A('nr_G1.physical.fd_aliased_phys_hz', '{:.1f}', 'Hz')} 에 나타난다.", "",
           "접힌 표적은 사라지는 것이 아니라 **엉뚱한 속도로 보고된다**. 그래서 이 대가는 "
           "감도가 아니라 판정의 정합성에 든다."),

        md("## 두 배의 대가의 나머지 절반", "",
           f"5G 는 좁아서 거리 눈금이 거칠고, 드물어서 속도 눈금이 접힌다 — "
           f"{ref('5g-double-cost')} 가 든 두 축의 뒤쪽이 여기다.", "",
           f"접힘을 정하는 것은 물리 반복률 "
           f"{A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')} 하나이고, CPI 가 정하는 것은 "
           f"도플러 가드 폭이다. 그 CPI 스윕은 {ref('cpi-sweep', short=True)} 가 싣고, CPI 로도 안 움직이는 "
           f"잔여분은 {ref('cpi-residual', short=True)} 가 든다."),

        next_steps([
            (f"검출기 CPI {A('nr_G1.physical.cpi_model_ms', '{:.0f}', 'ms')} 를 스윕해 SSB 도플러 "
             f"가드 폭을 PRF 대비로 잰다",
             "5G 상시 기준신호의 접힘이 단일 CPI 결과인지 체제인지가 수치로 갈린다",
             "`outputs/cpi_guard_sweep.json` → " + ref("cpi-sweep", short=True)),
            ("표적 속도를 격자로 넓혀 접히는 속도 구간을 지도로 만든다",
             "어느 속도대가 5G 에서 엉뚱한 속도로 보고되는지가 확정된다",
             "`benchmark/verify_ambiguity.py:108`"),
        ]),
    ]


# =========================================================================== #
#  논문 조각 — 옛 report03 의 §0(c2) + 논문 부록(c21)
# =========================================================================== #
def write_paper_doc() -> str:
    nb = os.path.join(_ROOT, "report03_illuminators.ipynb")
    with open(nb, encoding="utf-8") as f:
        cells = json.load(f)["cells"]

    def src(i):
        return "".join(cells[i]["source"]).strip()

    figs = []
    for c in cells:
        t = "".join(c["source"])
        if t.startswith("<!--pk:figure"):
            meta = json.loads(t.split("\n")[0][len("<!--pk:figure "):-len("-->")])
            figs.append((meta.get("figure_no"), meta.get("path"), meta.get("caption", "")))

    out = ["<!-- 생성물 — `src/build_part08_illuminators.py:write_paper_doc()` 가 쓴다. -->",
           "<!-- from: 옛 report03_illuminators.ipynb c2(논문이 가져가는 것) + c21(논문 부록) -->",
           "", "# 논문 조각 — III-B. Illuminators", "",
           "부 8 「조명원」 7편(44~50)이 본문이고, 이 문서는 그 편들에서 **논문으로만** 가는 "
           "조각이다. 사용자 지시로 논문·재현 문단을 리포트 본문에서 뺐다.", "",
           "| 편 | 무엇을 대는가 |", "|---|---|",
           "| 44 illuminators | 세 표준의 상시 기준신호와 격자에서 잰 제원 |",
           "| 45 5g-double-cost | 5G 가 거리·속도 두 축에서 무는 대가 |",
           "| 46 cost-ledger | 조명원 선택의 dB 원장과 그 닫는 방식 |",
           "| 47 range-convention | 바이스태틱 거리 규약과 잡음대역 정규화 |",
           "| 48 waveform-check | 변조 단계의 독립 구현 대조 |",
           "| 49 ambiguity | 검출기 커널 그대로의 모호함수 |",
           "| 50 doppler-fold | 물리 반복률이 만드는 접힘 |",
           "", "---", "", "## σ 와 무관하게 정확한 양 (옛 report03 c2)", "", src(2),
           "", "---", "", "## 그림의 논문 캡션 (완결 문장)", "",
           "| Fig. | 파일 | 캡션 |", "|---|---|---|"]
    for n, p, cap in figs:
        out.append(f"| {n} | `{p}` | {cap} |")
    out += ["", "---", "", "## 논문 부록 — 방법 문단 · 방어선 · 인용 (옛 report03 c21)", "",
            src(21), ""]

    d = os.path.join(_ROOT, "docs", "paper")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "03_illuminators.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return p


# =========================================================================== #
#: 편 47 이 리포트 밖으로 보낸 재현 코드(옛 report03 c12) — 색인 샤드가 들고 간다.
REPRO_SNIPPET = "\n".join([
    "# 대가 원장을 JSON 에서 그대로 읽어 찍는다 — 본문 숫자에 하드코딩이 없음을 확인한다.",
    "import json",
    "L = json.load(open('outputs/report03_illuminators.json'))",
    "print('점유 대가', f\"{L['occupancy_cost']['value_db']:+.1f} dB\")",
    "for k in ('wifi', 'lte', 'nr'):",
    "    g1 = L['grids']['G1'][k]",
    "    print(f\"{k:5s} B_ref={g1['ref_bw_hz']/1e6:6.2f} MHz  dRb={g1['drb_m']:6.2f} m\")",
])

BUILD = [
    ("illuminators", r44, [J_LED, J_WAVE], ["report03_f1_grid"]),
    ("5g-double-cost", r45, [J_LED, J_WAVE], ["report03_f2_reference"]),
    ("cost-ledger", r46, [J_LED, J_FIX, J_MTX], ["report03_f3_occupancy", "report03_f4_ledger"]),
    ("range-convention", r47, [J_LED, J_FIX, J_AMB], []),
    ("waveform-check", r48, [J_WAVE], ["report03_f5_crosscheck"]),
    ("ambiguity", r49, [J_LED, J_AMB], ["report03_f6_af_mainlobe"]),
    ("doppler-fold", r50, [J_LED, J_AMB], ["report03_f7_af_sidelobe"]),
]


def main() -> int:
    bad = 0
    for anchor, fn, ev, figs in BUILD:
        p = nb_path(anchor)
        rep = build_notebook(p, fn(), strict=True)
        index_shard(anchor, evidence=ev, figures=figs,
                    md_cells=rep["md_cells"], provenance_tags=rep["provenance_tags"],
                    repro=dict(cmd=CMD_ALL, out=ev,
                               snippet=(REPRO_SNIPPET if anchor == "range-convention" else None)),
                    builder="src/build_part08_illuminators.py")
        bad += 0 if rep["ok"] else 1
    print("논문 조각:", os.path.relpath(write_paper_doc(), _ROOT))
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
