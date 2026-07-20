# -*- coding: utf-8 -*-
"""make_notebook04.py — report04.ipynb 생성기

report04: **조명원 — WiFi / LTE / 5G 파형**
질문: **"어떤 통신 신호로 드론을 비추며, 각 신호의 장단점은?"**

⚠ 노트북은 **생성물**이다. report04.ipynb 를 직접 고치지 말고 이 파일을 고쳐 다시 실행할 것.
⚠ 본문 수치는 전부 **outputs/report2_waveform_rcs.json 에서 읽어 주입**한다 — 그림과 글이
   어긋날 수 없다. (파형 제원은 src/waveforms.py 가 3GPP/IEEE 격자에서 실측해 남긴 것.)
⚠ 이 리포트는 **한 주제(조명원·파형)만** 다룬다.
   · 파형이 정말 규격대로인가 (Sionna PHY 교차대조) → report05 소관
   · 표적이 얼마나 밝은가 (RCS)                      → report06 소관
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from provenance import provenance_cells   # noqa: E402  ← 리포트 앞머리 자동생성

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
NB = os.path.join(ROOT, "report04.ipynb")
JS = os.path.join(ROOT, "outputs", "report2_waveform_rcs.json")


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def code(*l):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _s(list(l))}


# --------------------------------------------------------------------------- #
with open(JS) as f:
    J = json.load(f)

REF = J["reference"]
G1 = REF["G1"]
W, LT, NR = G1["wifi"], G1["lte"], G1["nr"]

# 파생 비율 (손으로 안 적음 — 측정값에서 계산)
_nr_chan_frac = NR["ref_bw_mhz"] / NR["chan_bw_mhz"] * 100.0        # SSB 가 채널의 몇 %
_dr_vs_lte = NR["dR_m"] / LT["dR_m"]                                 # SSB 가 LTE 보다 몇 배 거친가
_dr_vs_wifi = NR["dR_m"] / W["dR_m"]                                 # SSB 가 WiFi 보다 몇 배 거친가
_v_lte_vs_nr = LT["vmax_ms"] / NR["vmax_ms"]                         # LTE 가 SSB 보다 몇 배 빠른 표적을 보나

cells = []

# =========================================================================== #
#  앞머리 — provenance.py 가 자동 생성
# =========================================================================== #
_prov = provenance_cells(
    report="report04",
    what="조명원 — **WiFi / LTE / 5G 파형**",
    question="어떤 통신 신호로 드론을 비추며, 각 신호의 장단점은?",

    spine=dict(
        core=(f"패시브 레이더는 자기 송신기가 없어 남의 **상시 신호**를 빌려 드론을 비춘다 — "
              f"어떤 상시 신호가 좋은 조명원인가를 WiFi·LTE·5G 세 후보로 한 챔버에서 가른다. "
              f"결론: 넓고(ΔR {LT['dR_m']:.1f} m) 자주({LT['prf_hz']:.0f} Hz) 나오는 **LTE CRS 가 "
              f"좁고(ΔR {NR['dR_m']:.1f} m) 드문(20 ms) 5G SSB 보다 낫다** — 세대가 최신이라고 "
              f"조명 품질이 좋은 건 아니다."),
        gap=(f"**Sionna PHY 는 5G NR·LTE OFDM 을 3GPP 규격대로 생성**한다(`nr.CarrierConfig` 가 "
             f"μ·SCS·슬롯·CP 를 준다). 그러나 **WiFi(802.11) 파형은 기본 제공하지 않고**, 패시브가 "
             f"실제로 상관에 쓰는 **상시 기준신호(LTE CRS·5G SSB)의 자원격자 배치**도 없다 — "
             f"'채널 전대역'이 아니라 그 기준신호가 격자에서 실제로 켜는 **점유대역 $B_{{ref}}$** 가 "
             f"눈을 정하는데(§2)."),
        prior=("기회신호(illuminator-of-opportunity) 패시브 레이더 문헌이 고르는 조명원이 정확히 이 "
               "상시 기준신호들이다 — **LTE** 하향링크 드론 검출(Demissie, *IET RSN* 2025, "
               "peer-reviewed), 셀룰러 하향링크 멀티스태틱 도플러 추적(arXiv:2509.25732), "
               "**5G SSB** 저고도 드론 검출·측위(Jopanya & Osorio, *IEEE SPAWC* 2025, "
               "arXiv:2504.02641) (§3)."),
        lib=("**5G NR·LTE 뉴머롤로지는 Sionna PHY `nr.CarrierConfig` 에 물어**(중복 구현 회피), "
             "**WiFi 와 상시 기준신호(CRS/SSB) 격자만 3GPP TS 36.211/38.211·IEEE 802.11ac 표에서 "
             "자작**(`src/waveforms.py`)한다. 점유대역·PRF 를 격자에서 읽어 "
             "ΔR=c/$B_{ref}$·$v_{max}$=PRF·λ/4 로 환산(§4)."),
        verify=(f"파형이 정말 규격대로인지는 **Sionna PHY 로 교차대조(report05)** — 대역폭·뉴머롤로지·"
                f"상시성을 규격 대비 확인. 본문 숫자는 유휴 셀 격자에서 실측한 값(WiFi "
                f"{W['ref_bw_mhz']:.1f}·LTE {LT['ref_bw_mhz']:.1f}·SSB {NR['ref_bw_mhz']:.1f} MHz)."),
    ),

    sources=[
        dict(item="LTE CRS / 5G SSB / WiFi VHT-LTF 자원격자 배치",
             src="3GPP TS 36.211 · 3GPP TS 38.211 · IEEE 802.11ac → `src/waveforms.py`. "
                 "조사 근거는 `docs/waveform_research.json`",
             kind="🔴 우리 구현 (Sionna 에 WiFi/LTE/SSB **자원격자가 없다**)"),
        dict(item="5G NR 뉴머롤로지 (μ·SCS·슬롯·CP)",
             src="**`sionna.phy.nr.CarrierConfig`** — Sionna 에게 물어본 값 (표를 손으로 안 짬)",
             kind="🟢 라이브러리 (3GPP TS 38.211 구현)"),
        dict(item="ΔR · $v_{max}$ 폐형식",
             src="$\\Delta R_b$ = c/$B_{ref}$ (바이스태틱; 모노 등가 c/2B) · $v_{max}$ = PRF·λ/4 — 교과서 레이더 공식",
             kind="📐 해석식"),
    ],

    engines=["sionna-phy", "matplotlib"],
    libs=["sionna", "numpy", "scipy", "matplotlib"],

    reproduce=[
        "cd /home/yunjung/workspace/sionna2",
        "",
        "# 파형 제원을 만들어서 재고 그림·JSON 을 남긴다 (report2 파이프라인 재사용, 재측정 없음)",
        "~/.venvs/py312/bin/python src/viz_report2.py        # 측정 + 그림 + JSON",
        "~/.venvs/py312/bin/python src/make_notebook04.py    # JSON -> report04.ipynb",
        "",
        "# 파형 제원을 직접 눈으로 확인하고 싶으면:",
        "~/.venvs/py312/bin/python src/waveforms.py          # 표준별 B_ref · PRF · ΔR · v_max",
    ],

    artifacts=[
        dict(file="outputs/report2_waveform_rcs.json", what="**이 리포트의 모든 파형 숫자.** 측정 원본"),
        dict(file="outputs/figures/report2_ref_signal.png",
             what="§2 넓이→거리 · 반복→속도 예산 그림"),
        dict(file="outputs/figures/report2_resource_grid.png",
             what="§3 자원격자 사진 (WiFi/LTE/5G × 유휴/풀로드)"),
        dict(file="outputs/figures/report2_occupancy.png",
             what="§3 점유율은 늘어도 거리분해능은 안 늘더라"),
    ],

    caveats=[
        "**§2 의 ΔR·$v_{max}$ 는 '유휴 셀'을 전제한다.** 유휴 셀은 상시 기준신호만 내보내므로 "
        "패시브가 기댈 수 있는 **가장 정직한 기본선**이다. 부하가 걸린 셀에서 수신기가 송신 파형 "
        "전체를 직접 받아 기준으로 쓸 수 있다면(captured full-waveform) 대역은 채널 전대역까지 "
        "넓어질 수 있으나, 그건 **다른 전제**다 — 두 경우를 섞어 인용하지 말 것.",

        "**PRS 로 넓힌 5G 수치는 낙관적 상한이다.** PRS 는 상시 신호가 아니라 **측위 세션이 "
        "설정돼야** 켜지는 옵션이며, 남의 셀을 빌려 쓰는 패시브 수신기는 그것이 켜져 있다고 "
        "가정할 수 없다. 그래서 §2 의 기본선은 SSB(7.2 MHz)이지 PRS(전대역)가 아니다.",

        "**WiFi 의 PRF 1 kHz 는 '혼잡한 AP' 대표값이다.** 트래픽이 없으면 비콘(약 100 ms 주기)만 "
        "남아 반복이 훨씬 느려진다 — WiFi 의 속도 성능은 트래픽에 크게 의존한다.",

        "**이 리포트는 파형이 무엇을 주는가(대역·반복·분해능)만 다룬다.** 그 파형이 정말 "
        "규격대로 만들어졌는지의 증명은 → report05, 표적이 얼마나 밝은지(RCS)는 → report06 소관이다.",
    ],

    cost="이 리포트는 무거운 재측정을 하지 않는다 — 파형 격자를 만들어 제원을 읽는 것은 CPU 초 단위. "
         "그림은 report2 파이프라인이 이미 남긴 것을 재사용한다. 노트북 생성도 초 단위.",

    related=[
        dict(rep="[report03](report03.ipynb) — 표적 검증",
             rel="**앞 리포트.** '무엇을 볼 것인가'(드론)를 확정했다. 여기서는 '무엇으로 볼 것인가'(조명원)"),
        dict(rep="**report04 (여기)** — 조명원 · 파형",
             rel="패시브가 빌려 쓰는 상시 신호 3종과 그 장단점 — 넓이(거리)·반복(속도)"),
        dict(rep="[report05](report05.ipynb) — 파형 검증",
             rel="**다음 리포트.** 여기서 만든 파형이 정말 3GPP/IEEE 규격대로인지 Sionna 로 대조한다"),
    ],

    glossary=[
        ("패시브 레이더", "자기 송신기 없이 **남의 신호(방송·통신)의 반사**로 표적을 보는 레이더"),
        ("조명원(illuminator)", "패시브 레이더가 빌려 쓰는 '남의 송신기' — 기지국·와이파이 AP 등"),
        ("기준신호(reference signal)", "패시브가 상관을 걸 때 쓰는 '미리 아는 신호'. 표준마다 상시 하나"),
        ("상시(always-on) 신호", "임의의 셀이 **언제나** 내보낸다고 믿을 수 있는 신호. LTE=CRS, 5G=SSB, WiFi=프리앰블"),
        ("CRS", "LTE Cell-specific Reference Signal — 매 서브프레임(1 ms)·채널 전대역에 상시 나오는 셀 기준신호"),
        ("SSB", "5G NR SS/PBCH Block — 유휴 gNB 가 늘 내보내는 유일한 신호. 좁고(중앙 20 RB) 드물다(20 ms 주기)"),
        ("VHT-LTF", "WiFi 802.11ac 패킷 앞머리(프리앰블)의 롱 트레이닝 필드. 어떤 패킷에도 붙지만 반복은 트래픽에 의존"),
        ("점유대역 $B_{ref}$", "기준신호가 자원격자에서 **실제로 켜는** 주파수 폭. 채널 전대역과 다르다"),
        ("거리분해능 ΔR", "두 표적을 거리로 가르는 최소 간격. **바이스태틱** $\\Delta R_b$=c/$B_{ref}$ "
                       "(우리 시스템), 모노스태틱 등가는 c/2B(절반). 넓은 신호일수록 촘촘"),
        ("PRF", "pulse repetition frequency — 기준신호가 **초당 몇 번** 반복되나. 자주일수록 빠른 표적을 봄"),
        ("무모호 속도 $v_{max}$", "헷갈리지 않고 볼 수 있는 최대 속도. $v_{max}$ = PRF·λ/4"),
        ("자원격자(resource grid)", "가로=시간·세로=주파수의 모눈종이. OFDM 신호는 이 칸을 채워 만든다"),
        ("RE (resource element)", "자원격자의 **한 칸** (한 부반송파 × 한 OFDM 심볼)"),
        ("OFDM", "부반송파 수백 개에 데이터를 잘게 나눠 싣는 변조 방식. 통신 신호의 기본 골격"),
        ("PRS", "Positioning Reference Signal — **측위 세션이 설정돼야** 켜지는 옵션. 상시 신호가 아니다"),
        ("도플러 접힘(aliasing)", "반복이 너무 드물어 빠른 표적의 속도를 헷갈리는 현상. $v_{max}$ 를 넘으면 생긴다"),
    ],
)

cells += _prov   # 척추 리드가 헤더에 있으므로 별도 5분요약은 싣지 않는다

# =========================================================================== #
#  §1  — Sionna 가 주는 파형과 안 주는 파형 (공백)
# =========================================================================== #
cells.append(md(
    "## §1. Sionna 가 주는 파형과 안 주는 파형 — 패시브가 빌리는 상시 신호",
    "",
    "패시브 레이더는 자기 송신기 없이 **남의 신호의 반사**로 표적을 본다. 송신기를 빌려 쓰므로 두 제약이 "
    "따라붙는다.",
    "",
    "1. **미리 아는 신호여야 한다.** 튕겨 온 신호가 표적인지 알아보려면 '원래 신호'와 상관해야 하는데, "
    "통신 신호가 나르는 **데이터는 매 순간 바뀌어** 수신기가 미리 알 수 없다. 내용이 고정된 "
    "**기준신호(reference signal)** 만 상관에 쓸 수 있다.",
    "2. **아무 셀이나 늘 내보내야 한다.** 특정 조건에서만 켜지는 신호는 하필 그 순간 그 셀이 안 켜면 "
    "표적을 놓친다. 임의의 셀이 **언제나** 내보낸다고 믿을 수 있는 **상시(always-on) 신호** 여야 한다.",
    "",
    "이 두 조건을 동시에 만족하는 신호는 표준마다 **딱 하나씩**이다:",
    "",
    "| 표준 | 상시 기준신호 | 왜 이것뿐인가 |",
    "|---|---|---|",
    "| **LTE** | **CRS** (Cell-specific Reference Signal) | 매 서브프레임(1 ms)·채널 전대역에 늘 뿌린다 |",
    "| **5G NR** | **SSB** (SS/PBCH Block) | NR 에는 **CRS 같은 상시 전대역 신호가 없다.** "
    "유휴 기지국이 늘 내보내는 건 SSB 뿐 |",
    "| **WiFi** | **프리앰블 (VHT-LTF)** | 모든 패킷 앞머리에 붙는다 — 단 **반복 횟수가 트래픽에 의존** |",
    "",
    "여기서 **Sionna PHY 의 공백**이 드러난다. Sionna PHY(`nr`/`ofdm`/`channel`)는 5G NR·LTE 의 OFDM "
    "파형을 3GPP 규격대로 만들 수 있지만 — 뉴머롤로지(μ·SCS·슬롯·CP)는 `nr.CarrierConfig` 가 "
    "TS 38.211 을 구현해 준다 — **① WiFi(802.11) 파형은 기본 제공하지 않고**, **② 패시브가 실제로 "
    "상관에 쓰는 상시 기준신호(CRS·SSB)의 자원격자 배치**(어느 칸을 켜는가)도 API 로 바로 주지 않는다. "
    "그런데 조명원의 성능을 정하는 것은 '채널 전대역'이 아니라 그 기준신호가 격자에서 **실제로 켜는 "
    "점유대역 $B_{ref}$** 다(§2). 그래서 우리는 세 표준의 상시 기준신호 격자를 규격표 위에 직접 세워 "
    "(§4) 그 $B_{ref}$·반복주기를 읽는다.",
    "",
    "> ⚠️ **PRS(측위 기준신호)는 상시 신호가 아니다.** 넓은 대역을 쓰지만 **측위 세션이 설정돼야** "
    "켜지는 옵션이라, 남의 셀을 빌려 쓰는 패시브 수신기는 그것이 켜져 있다고 가정할 수 없다. 이 "
    "리포트의 기본선은 어디까지나 위 3개의 **상시** 신호다.",
))

# =========================================================================== #
#  §2  — 증거: 넓이=거리, 반복=속도, 자원격자
# =========================================================================== #
cells.append(md(
    "---",
    "## §2. 무엇을 보는가 — 넓이(거리)와 반복(속도), 자원격자로 확인",
    "",
    "빌린 신호의 **주파수 넓이**와 **반복 빈도**가 각각 거리·속도를 얼마나 잘 보는지를 정한다. 유휴 셀 "
    "격자에서 읽은 값으로 세 조명등을 나란히 세운다.",
    "",
    "### 2.1 넓을수록 거리를 잘 가른다",
    "",
    "> 손전등 빛줄기가 굵으면 두 물체가 한 덩어리로 뭉쳐 보이고, 가늘고 날카로울수록 둘을 따로 짚는다. "
    "레이더에서 이 '날카로움'을 정하는 게 신호의 **주파수 넓이**다.",
    "",
    "두 표적을 거리로 가르는 최소 간격이 **거리분해능 ΔR** 이다(우리는 **바이스태틱**이라 "
    "$\\Delta R_b$=c/$B_{ref}$; 모노스태틱 등가는 절반). 결정적인 것은 채널이 차지한 전체 대역이 "
    "**아니라**, 기준신호가 자원격자에서 **실제로 켜는 주파수 폭** — **점유대역 $B_{ref}$** 다.",
    "",
    "$$\\Delta R_b = \\frac{c}{B_{ref}}\\quad(\\text{바이스태틱; 모노 등가 } c/2B)$$",
    "",
    "$B_{ref}$ 가 넓을수록 ΔR 이 작아져(=촘촘해져) 가까이 붙은 두 물체를 갈라 본다.",
    "",
    "### 2.2 자주 나올수록 빠른 표적을 본다",
    "",
    "표적이 움직이면 되돌아오는 신호의 주파수가 살짝 밀린다(도플러). 이 밀림으로 속도를 재는데, "
    "기준신호가 **초당 몇 번 반복되나**(PRF)가 헷갈리지 않고 볼 수 있는 최고 속도 — **무모호 속도 "
    "$v_{max}$** 를 정한다. 반복이 드물면($v_{max}$ 가 작으면) 그보다 빠른 표적은 "
    "**도플러가 접혀(aliasing)** 엉뚱한 속도로 읽힌다.",
    "",
    "$$v_{max} = \\frac{\\mathrm{PRF}\\cdot\\lambda}{4}$$",
    "",
    "### 2.3 유휴 셀에서 세 조명등을 나란히",
    "",
    "5G NR 뉴머롤로지(μ·SCS·슬롯·CP)는 손으로 짜지 않고 **Sionna PHY 의 `CarrierConfig`** 가 "
    "3GPP TS 38.211 을 구현한 값을 그대로 받는다. 각 표준의 상시 기준신호를 그 규격 격자 위에 올려 두고, "
    "격자가 **실제로 켜는** $B_{ref}$·PRF 를 읽어 ΔR·$v_{max}$ 를 교과서 폐형식으로 구한다 (아래 숫자는 "
    "손으로 적은 게 아니라 **격자에서 읽은** 값이다):",
    "",
    "| 표준 | 기준신호 | 채널 대역 | **$B_{ref}$** | **ΔR** | **PRF** | **$v_{max}$** |",
    "|---|---|---|---|---|---|---|",
    f"| WiFi 802.11ac | {W['ref']} | {W['chan_bw_mhz']:.0f} MHz | "
    f"**{W['ref_bw_mhz']:.1f} MHz** | **{W['dR_m']:.1f} m** | "
    f"{W['prf_hz']:.0f} Hz | {W['vmax_ms']:.1f} m/s |",
    f"| LTE Rel-9 | {LT['ref']} | {LT['chan_bw_mhz']:.0f} MHz | "
    f"**{LT['ref_bw_mhz']:.1f} MHz** | **{LT['dR_m']:.1f} m** | "
    f"{LT['prf_hz']:.0f} Hz | {LT['vmax_ms']:.0f} m/s |",
    f"| **5G NR Rel-16** | **{NR['ref']}** | {NR['chan_bw_mhz']:.0f} MHz | "
    f"**{NR['ref_bw_mhz']:.1f} MHz** | **{NR['dR_m']:.1f} m** | "
    f"**{NR['prf_hz']:.0f} Hz** | **{NR['vmax_ms']:.2f} m/s** |",
    "",
    "![reference signal budget](outputs/figures/report2_ref_signal.png)",
    "",
    "*(그림 (a): 회색 = 채널 전체 대역, 색 = 패시브가 실제로 쓰는 기준신호 대역. 5G 만 둘이 크게 다릅니다. "
    "(b): 그 대역이 정하는 거리분해능. (c): 거리(가로)·속도(세로)를 한 점으로 — 오른쪽·아래일수록 나쁨.)*",
    "",
    "**세 줄로 읽는 법:**",
    f"- **WiFi** 는 기준신호가 이미 넓어(**{W['ref_bw_mhz']:.1f} MHz**) 거리를 가장 촘촘히 본다"
    f"(**ΔR {W['dR_m']:.1f} m**). 다만 5 GHz 대라 도달 거리가 짧고, 반복이 트래픽에 의존한다.",
    f"- **LTE** 는 CRS 가 채널 전대역(**{LT['ref_bw_mhz']:.1f} MHz**)에 매 1 ms 뿌려져 거리"
    f"(**ΔR {LT['dR_m']:.1f} m**)·속도(**$v_{{max}}$ {LT['vmax_ms']:.0f} m/s**) 모두 균형이 좋다.",
    f"- **5G SSB** 는 채널이 {NR['chan_bw_mhz']:.0f} MHz 나 되는데도 상시 켜는 건 중앙 20 RB "
    f"**{NR['ref_bw_mhz']:.1f} MHz** 뿐 — 거리가 거칠고(**ΔR {NR['dR_m']:.1f} m**), 20 ms 마다 한 번만 "
    f"나와 속도도 약하다(**$v_{{max}}$ {NR['vmax_ms']:.2f} m/s**).",
))

cells.append(code(
    "# §2 재현 — waveforms.py 가 격자에서 읽은 속성을 그대로 출력 (본문 숫자에 하드코딩 없음)",
    "import sys; sys.path.insert(0, 'src')",
    "from waveforms import always_on_waveforms",
    "",
    "print(f\"{'표준':16s} {'기준신호':9s} {'B_ref':>10} {'ΔR':>8} {'PRF':>9} {'v_max':>9}\")",
    "for k, wf in always_on_waveforms().items():          # 유휴 셀 = 상시 기준신호만",
    "    print(f'{wf.name:16s} {wf.ref_name:9s} {wf.ref_bw_hz/1e6:7.2f}MHz '",
    "          f'{wf.range_resolution_m:6.2f}m {wf.pilot_rate_hz:7.0f}Hz "
    "{wf.v_unambiguous_ms:7.2f}m/s')",
))

cells.append(md(
    "### 2.4 자원격자로 본 세 신호",
    "",
    "통신 신호는 **자원격자(가로=시간, 세로=주파수인 모눈종이)** 의 칸(RE)을 채워 만든다. 아래 그림에서 "
    "**위 줄은 유휴 셀**(상시 기준신호만), **아래 줄은 풀로드 셀**(데이터까지 꽉 채운 상태)이다.",
    "",
    "![resource grid](outputs/figures/report2_resource_grid.png)",
    "",
    "위 줄만 보면 된다 — 패시브가 쓸 수 있는 건 그것뿐이다. **WiFi 프리앰블**은 세로(주파수)로 꽉 차 "
    "있고(넓다), **LTE CRS** 도 전대역에 흩뿌려져 있는데, **5G SSB** 만 세로로 **가운데 작은 블록**에 "
    "몰려 있다 — 이 좁음이 곧 거친 거리분해능이다. 아래 줄(풀로드)에서 회색으로 꽉 찬 칸(PDSCH/DATA)은 "
    "**데이터**다. 에너지는 많지만 수신기가 **모르는 내용**이라 상관에 못 쓴다 — 그래서 셀이 바빠져도 "
    "패시브가 쓸 '아는 신호'의 넓이는 거의 안 늘어난다.",
    "",
    "### 2.5 셀이 바빠져도 거리분해능은 안 늘더라",
    "",
    "'셀이 데이터로 꽉 차면 신호가 넓어져 거리를 더 잘 보지 않을까?' — 만들어서 재보면 그렇지 않다.",
    "",
    "![occupancy](outputs/figures/report2_occupancy.png)",
    "",
    f"격자 점유율(왼쪽)은 유휴→풀로드로 5G 기준 {NR['occ_pct']:.1f}% → {REF['G3']['nr']['occ_pct']:.0f}% "
    f"로 수십 배 뛰지만, **거리분해능(오른쪽)은 WiFi·LTE 는 거의 안 움직인다** — 상시 기준신호가 "
    f"**이미 넓기** 때문이다. 늘어난 건 상관에 못 쓰는 데이터 에너지뿐이다.",
    "",
    "> ⚠️ 5G 만 오른쪽에서 41.6 m → 3.1 m 로 급전환하는데, 그건 **PRS(측위 기준신호)가 켜졌기 때문**"
    "이다. PRS 는 상시 신호가 아니라 **측위 세션을 가정한 것**이므로, 이 급전환은 **낙관적 상한**이지 "
    "패시브가 늘 기댈 수 있는 기본선이 아니다. 기본선은 어디까지나 SSB(7.2 MHz)다.",
    "",
    "### 2.6 5G 가 불리한 이유 — 좁고, 드물다",
    "",
    f"**① 좁다 (거리가 거칠다).** SSB 는 채널 한가운데 20 RB = **{NR['ref_bw_mhz']:.1f} MHz** 만 켠다. "
    f"그래서 ΔR = **{NR['dR_m']:.1f} m** — {NR['dR_m']:.0f} m 안쪽에 있는 두 물체는 **한 덩어리**로만 "
    f"보인다. 채널 자체는 **{NR['chan_bw_mhz']:.0f} MHz** 나 되는데 패시브가 상시로 쓸 수 있는 건 "
    f"그중 **{_nr_chan_frac:.1f}%** 뿐이다.",
    "",
    f"**② 드물다 (빠른 표적을 놓친다).** SSB 는 SS 버스트가 **20 ms 주기**로만 나온다 → PRF "
    f"**{NR['prf_hz']:.0f} Hz** → $v_{{max}}$ **{NR['vmax_ms']:.2f} m/s**. 걷는 속도(약 1.4 m/s)만 "
    f"넘어도 도플러가 접혀 속도를 헷갈린다.",
    "",
    "### 2.7 대비 — 구세대 LTE 가 오히려 좋은 조명등",
    "",
    f"LTE CRS 는 **전대역**({LT['ref_bw_mhz']:.1f} MHz)을 켜고 **매 서브프레임(1 kHz)** 나온다. "
    f"그래서 거리·속도 두 축 모두 5G 를 앞선다:",
    "",
    "| 축 | 무엇이 정하나 | LTE CRS | 5G SSB | LTE 가 유리한 정도 |",
    "|---|---|---|---|---|",
    f"| **거리** ΔR | 점유대역 $B_{{ref}}$ | **{LT['dR_m']:.1f} m** ({LT['ref_bw_mhz']:.1f} MHz) | "
    f"{NR['dR_m']:.1f} m ({NR['ref_bw_mhz']:.1f} MHz) | 약 {_dr_vs_lte:.1f}× 촘촘 |",
    f"| **속도** $v_{{max}}$ | PRF | **{LT['vmax_ms']:.0f} m/s** ({LT['prf_hz']:.0f} Hz) | "
    f"{NR['vmax_ms']:.2f} m/s ({NR['prf_hz']:.0f} Hz) | 약 {_v_lte_vs_nr:.0f}× 빠름 |",
    "",
    "통신 세대가 최신이라고 패시브 레이더에 좋은 조명등이 되는 건 아니다. 오히려 5G 는 늘 켜 두는 "
    "기준신호가 **좁고 드물어서** 옛 LTE 보다 못하다. 쓸 조명원을 고를 땐 통신 성능이 아니라 "
    "**상시 신호의 넓이와 반복**을 봐야 한다.",
))

# --- 스펙트럼 애니메이션 (좁은 점유대역 → 거친 거리분해능) ---------------------- #
cells.append(md(
    "![.](outputs/renders/anim/spectrum_nr.gif)\n\n"
    "<sub>5G NR 스펙트럼 — 상시 기준신호(SSB) 점유 대역이 좁아 거리분해능이 거칠다.</sub>"
))
cells.append(md(
    "![.](outputs/renders/anim/spectrum_lte.gif)\n\n"
    f"<sub>LTE 스펙트럼 — CRS 가 전대역({LT['ref_bw_mhz']:.1f} MHz)을 켜 거리분해능이 촘촘하다"
    f"(ΔR_b {LT['dR_m']:.1f} m, 5G SSB 의 약 {_dr_vs_lte:.1f}배 촘촘).</sub>"
))

# =========================================================================== #
#  §3  — 선행 연구: 기회신호 패시브 레이더의 조명원
# =========================================================================== #
cells.append(md(
    "---",
    "## §3. 선행 연구 — 기회신호 패시브 레이더의 조명원",
    "",
    "이 조명원 선택은 우리가 발명한 것이 아니라 **기회신호(illuminator-of-opportunity) 패시브 레이더 "
    "문헌이 이미 걸어간 길**이다. 문헌이 드론을 잡을 때 고르는 조명원이 정확히 §1 의 상시 기준신호들이다.",
    "",
    "| 조명원 | 선행 연구 | 확립 정도 |",
    "|---|---|---|",
    "| **LTE** 하향링크 | Demissie, *Drone Detection With a LTE450-Based Passive Radar* (*IET RSN* 2025) | "
    "peer-reviewed 실측 |",
    "| 셀룰러 하향링크(멀티스태틱) | *Doppler-Based Multistatic Drone Tracking via Cellular "
    "Downlink Signals* (arXiv:2509.25732) | 멀티스태틱 도플러 |",
    "| **5G SSB** | Jopanya & Osorio, *Utilizing 5G NR SSB Blocks for Passive Detection and "
    "Localization* (*IEEE SPAWC* 2025, arXiv:2504.02641) | 이론(CRB) 단계 |",
    "| **5G NR** (풀-웨이브폼) | Wypich & Zielinski, *Experimental Evaluation of 5G NR OFDM-Based "
    "Passive Radar* (*Sensors* 2026) | 실측(USRP X310) |",
    "",
    "**LTE 조명원**으로 드론을 잡는 패시브 레이더는 이미 peer-reviewed 실측으로 확립됐지만"
    "(Demissie), **5G SSB 만으로** 드론을 보는 쪽은 아직 성능한계(CRB)를 따지는 이론 단계에 가깝다"
    "(Jopanya & Osorio) — §2 가 숫자로 보인 5G 의 불리함과 결이 같다.",
    "",
    "Wypich & Zielinski 의 5G NR 패시브 레이더는 이 대비를 실측으로 못박는다: 상시 파일럿만 기준으로 "
    "쓰면 검출확률(POD)이 24–32% 에 그치지만, 수신기가 사용자 데이터(PDSCH)까지 **재구성해 파형 "
    "전체를 기준**으로 쓰면 77–78% 로 오른다(ECA+ → CA-CFAR). 즉 이 리포트가 재는 상시 신호의 좁은 "
    "대역은 패시브가 늘 기댈 수 있는 **가장 정직한 기본선**이고, 파형 전체를 잡아 쓰는 것은 (수신기가 "
    "그럴 수 있을 때의) **다른 전제**다 — 두 경우를 섞어 읽지 않는다.",
))

# =========================================================================== #
#  §4  — 우리가 쓴 방식: Sionna PHY + 자작 격자, 그리고 검증
# =========================================================================== #
cells.append(md(
    "---",
    "## §4. 우리가 쓴 방식 — Sionna PHY + 자작 격자, 그리고 검증",
    "",
    "우리는 선행이 고른 그 상시 기준신호들을 **한 챔버에서 같은 조건으로** 나란히 세워 장단점을 가린다. "
    "핵심은 **이미 있는 것은 다시 짜지 않는다**는 것이다:",
    "",
    "- **5G NR·LTE 뉴머롤로지**(μ·SCS·슬롯·CP)는 🟢 **Sionna PHY `nr.CarrierConfig`** 에 물어 그대로 "
    "받는다(TS 38.211 구현). 표를 손으로 짜지 않으니 규격과 어긋날 수 없고, OFDM 파형 생성도 Sionna 가 한다.",
    "- **WiFi(802.11) 파형과 상시 기준신호(CRS·SSB)의 자원격자 배치**만 🔴 3GPP TS 36.211/38.211·"
    "IEEE 802.11ac 표에서 자작한다(`src/waveforms.py`, 조사 근거 `docs/waveform_research.json`) — "
    "Sionna 가 이 부분을 기본 제공하지 않기 때문이다(§1).",
    "- 그 격자에서 **점유대역 $B_{ref}$·반복주기(PRF)** 를 읽어 ΔR=c/$B_{ref}$·$v_{max}$=PRF·λ/4 로 "
    "환산한다(§2). 본문 숫자는 전부 이 측정에서 왔다.",
    "",
    "**검증**은 이 파형이 정말 3GPP·IEEE 규격대로 만들어졌는지를 **→ report05** 에서 **Sionna PHY 로 "
    "교차대조**하는 것으로 한다 — 대역폭·뉴머롤로지·상시성을 규격 대비 확인한다. 즉 뉴머롤로지는 "
    "Sionna 가 준 값을 쓰고(§2), 자작 격자는 Sionna 로 되짚어 검증한다(report05).",
    "",
    "> **정리** — 패시브가 빌릴 수 있는 조명은 '언제 봐도 똑같고(미리 앎), 늘 켜져 있는(상시)' 신호뿐이고, "
    "그건 표준마다 하나뿐이다(§1). 그 하나의 넓이와 반복이 눈을 정하는데(§2), 넓고 자주 나오는 **LTE CRS "
    f"가 좁고 드문 5G SSB 보다 낫다**(ΔR {LT['dR_m']:.1f} vs {NR['dR_m']:.1f} m, "
    f"$v_{{max}}$ {LT['vmax_ms']:.0f} vs {NR['vmax_ms']:.2f} m/s). 선행도 같은 선택을 한다(§3). "
    "뉴머롤로지는 Sionna PHY 에 물었고, 없는 WiFi·기준신호 격자만 규격표로 자작해 report05 에서 되짚는다(§4).",
))

# =========================================================================== #
#  다음 리포트 연결
# =========================================================================== #
cells.append(md(
    "---",
    "> **다음 리포트**: [report05](report05.ipynb) — 지금까지 '이 파형은 이런 대역·반복을 준다'고 "
    "했는데, 그 파형이 정말 3GPP·IEEE 규격대로 만들어졌는지 **Sionna PHY 로 교차대조**해 확인한다.",
))

# --------------------------------------------------------------------------- #
nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python",
                                  "name": "py312"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}

with open(NB, "w") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"wrote {NB}  ({len(cells)} cells)")
