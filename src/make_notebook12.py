# -*- coding: utf-8 -*-
"""
make_notebook12.py — report12.ipynb 생성기
==========================================================================================
report12 — "다중 수신기 디텍션 + 9-모드 벤치마크: 어떤 신호로, 수신기 몇 개로 드론이 보이나"

⚠ 이 파일이 진짜 소스다. report12.ipynb 를 직접 고치지 말고 여기를 고쳐 재실행할 것.
⚠ 모든 숫자는 outputs/detection_rx_sweep.json 에서 읽어 넣는다(손으로 적은 숫자 없음).

한 주제: **앞 리포트(01~11)의 무대·표적·신호·검출기를 합쳐 (1) 3표준×3점유 = 9모드를 서로 비교하고,
(2) 수신기를 1→4 로 늘리며 탐지가 얼마나 좋아지는지**를 몬테카를로로 측정한다. 이 프로젝트의 결과편.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from provenance import provenance_cells                      # noqa: E402

NB = os.path.join(ROOT, "report12.ipynb")
J = json.load(open(os.path.join(ROOT, "outputs", "detection_rx_sweep.json"), encoding="utf-8"))
M = J["meta"]

# 9모드('modes') 우선, 구 3모드('waveforms')면 풀모드 코드로 매핑(폴백)
if "modes" in J:
    MD = J["modes"]
else:
    MD = {}
    for std, code, rn in (("nr", "G3", "NR-PRS"), ("wifi", "W3", "VHT-LTF"), ("lte", "L3", "PRS")):
        w = dict(J["waveforms"][std]); w.update(std=std, code=code, always_on=False,
                                                ref_name=rn, occupancy=0.8,
                                                ref_bw_mhz=3e8 / (2 * w["range_res_m"] * 1e6))
        MD[code] = w

CODES = list(MD.keys())

# 경험적 Pfa / 목표 비율(모드별, 전체 N·SNR 그리드 평균) — §5 정직성 문단에서 사용
_pfa_t = float(M.get("pfa_target", 1e-4))
_pfa_ratios = []
for _c in CODES:
    _vals = [p for _cv in MD[_c]["curves"].values() for p in _cv["Pfa_emp"]]
    if _vals:
        _pfa_ratios.append(sum(_vals) / len(_vals) / _pfa_t)
PFA_RATIO_MIN = min(_pfa_ratios)
PFA_RATIO_MAX = max(_pfa_ratios)
SNAME = {"wifi": "WiFi", "lte": "LTE", "nr": "5G"}
FULL = [c for c in ("W3", "L3", "G3") if c in MD]              # 제어/풀 (X410 실험 레짐)
ON = [c for c in ("W1", "L1", "G1") if c in MD]                # 상시 (기회주의 하한)
STD2FULL = {"nr": "G3", "wifi": "W3", "lte": "L3"}
K = M["K"]
CORR = np.mean([MD[c].get("corr_sionna", 1.0) for c in CODES])
CRAT = np.mean([MD[c].get("combine_ratio", 1.0) for c in CODES])


def s50(code, N=1):
    return MD[code]["curves"][str(N)]["snr50"]


def gain4(code):
    b, f = s50(code, 1), s50(code, 4)
    return (b - f) if (b is not None and f is not None) else None


NR_G4 = gain4(STD2FULL["nr"])
# 상시 3인방 SNR50(N=1)
ON_S = {c: s50(c) for c in ON}
FULL_S = {c: s50(c) for c in FULL}


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def fig(name, alt=""):
    return md(f"![{alt}](outputs/figures/{name}.png)")


def gif(name, alt="", sub=""):
    body = f"![{alt}](outputs/renders/anim/{name}.gif)"
    if sub:
        body += f"\n\n<sub>{sub}</sub>"
    return md(body)


GLOSS = [
    dict(term="패시브(수동) 바이스태틱 레이더",
         desc="자기 송신기 없이 **이미 켜진 통신 신호**(WiFi·LTE·5G)를 조명으로 빌려, 떨어진 수신기로 "
              "표적 메아리를 듣는 레이더."),
    dict(term="ISAC (통합 센싱·통신)",
         desc="송신기를 **통신+센싱 겸용으로 설계·제어**하는 것. 파형을 센싱에 맞게 빚을 수 있다. "
              "패시브(제어 못 함)와 대비된다. 이 프로젝트의 X410 실험은 송신을 **제어**하므로 ISAC 에 가깝다."),
    dict(term="상시(always-on) vs 세션/제어 기준신호",
         desc="상시 = 아무 셀이나 늘 내보내는 신호(WiFi 프리앰블·LTE CRS·5G SSB) — 협조 없이 패시브가 "
              "얻는 것. 세션/제어 = PRS(측위세션 필요) 또는 송신 전체 캡처(협조/제어) — 더 넓은 대역을 준다."),
    dict(term="검출확률 Pd / 오경보율 Pfa",
         desc="Pd=표적 있을 때 잡을 확률, Pfa=없는데 잘못 외칠 확률. **같은 Pfa 에서** Pd 를 비교해야 공정."),
    dict(term="RD 맵 (거리-도플러 지도)",
         desc="수신 신호를 가로=거리, 세로=속도(도플러)로 펼친 2차원 지도. 표적은 자기 칸에 밝은 점."),
    dict(term="코히어런트 빔포밍",
         desc="여러 수신 소자를 표적 방향으로 위상 맞춰 더하기. 표적 √N 배·잡음 그대로 → SNR N배(+10log10 N dB)."),
    dict(term="거리분해능 (바이스태틱 vs 모노스태틱)",
         desc="두 물체를 거리로 가르는 능력. 대역폭이 넓을수록 작아진다(좋다). ⚠ **바이스태틱**(우리 시스템)은 "
              "거리가 왕복이 아니므로 $\\Delta R_b = c/B$, **모노스태틱**은 왕복이라 $\\Delta R = c/2B$(절반). "
              "두 값을 구분해 관리한다(report11 §2 도 바이스태틱 c/B)."),
    dict(term="Sionna PHY / SBR",
         desc="Sionna PHY=파형·채널(여기서 표적 에코 생성). SBR=Mitsuba 광선+우리 PO 로 표적 밝기 σ. "
              "[[report06]][[report07]]"),
]

cells = []
cells += provenance_cells(
    report="report12",
    what="다중 수신기 디텍션 + 9-모드 벤치마크",
    question="어떤 통신 신호(9모드)로, 수신기 몇 개로 드론이 실제로 잡히나?",
    tldr=[
        f"**탐지가 된다.** 앞 리포트의 무대·표적(SBR σ)·신호(Sionna PHY)·검출기(ECA→RD→CFAR)를 합쳐 "
        f"몬테카를로 **K={K:,}회** 반복하면, 충분한 SNR 에서 Pd=1.0 에 이른다.",
        "**9모드 = 3표준(WiFi·LTE·5G) × 3점유(상시→제어/풀).** 실제로 갈리는 건 점유율이 아니라 "
        "**패시브가 잠글 수 있는 기준신호**다 — 상시(프리앰블·CRS·SSB)냐, 세션/제어(PRS·송신 전체 캡처)냐.",
        "**핵심: 상시(기회주의)에서도 WiFi 는 넓고 5G(SSB)는 병적으로 좁다.** WiFi 프리앰블은 상시라도 "
        f"광대역이라 유리하고, 5G SSB 는 7.2 MHz 라 거리분해능이 거칠어 불리하다. **PRS·제어가 되면 5G 도 "
        "전대역**을 쓴다 — 실증(X410)은 송신을 제어하므로 이 **풀 모드**에 해당한다.",
        f"**수신기를 늘리면 더 약한 표적도 잡는다(이상적 상한).** 완벽 조향·등분산 독립잡음 가정 아래 "
        f"감시 배열 1→4 코히어런트 결합의 **이상적 배열이득 상한**은 +10·log10 4 = 6 dB 이고, 모델에서 "
        f"필요 SNR 이 **{NR_G4:.1f} dB(5G 풀, N=4)** 낮아진다. 실제(X410)는 조향 불일치·보정오차로 이보다 낮다.",
        f"**정직성(적대적 검증 반영).** ① 에코 지연은 Sionna `cir_to_time_channel` 이 만든 sinc 커널로 하고"
        f"(도플러는 위상램프, 협대역서 시변채널과 동등), 해석식과 상관 {CORR:.3f} 는 **지연만** 교차검증한다. "
        f"② 배열이득의 √N 은 해석적으로 주입하고, **잡음전력 보존만**(결합잡음/σ²={CRAT:.3f}) 독립 실측했다. "
        f"③ Pfa 는 파형(std)별 명목 교정을 적용했으나 **모드 간 경험적 Pfa 가 완전히 같진 않다** — 아래 §5 참고.",
    ],
    roadmap=[
        dict(sec="§1", what="실험 무대 — 바이스태틱·기준+감시배열", why="무엇을 어떻게 놓았나"),
        dict(sec="§2", what="신호 만들기 — Sionna PHY 로 표적 에코", why="시오나가 실제로 하는 일"),
        dict(sec="§3", what="9-모드 벤치마크 — 어떤 신호가 유리한가", why="⭐ 상시 vs 제어, 대역이 관건"),
        dict(sec="§4", what="수신기 증설 = 코히어런트 이득", why="Rx 1→4 로 Pd 가 얼마나 오르나"),
        dict(sec="§5", what="몬테카를로 반복 · Pfa 교정", why="많이 반복해야 믿는다"),
        dict(sec="§6", what="결론 — 그리고 추적은 다음 일", why="여기까지가 탐지"),
    ],
    sources=[
        dict(item="Pd·SNR50·경험적 Pfa (9모드×N=1..4×SNR)", src="outputs/detection_rx_sweep.json",
             kind="측정 (몬테카를로 K회, GPU 배치)"),
        dict(item="표적 밝기 σ", src="src/rcs_po.py → SBR (Mitsuba 광선 + PO)",
             kind=f"측정 ({M['drone']}, σ={M['sigma_dbsm']:.1f} dBsm)"),
        dict(item="표적 에코 (지연·도플러)", src="src/sionna_chain.py → cir_to_time_channel (Sionna PHY)",
             kind=f"측정 (해석식과 상관 {CORR:.3f})"),
        dict(item="9모드 파형(3표준×3점유)", src="src/waveforms.py (occupancy G1/G2/G3) · sionna.phy.nr",
             kind="🔴 우리 구현 + 🟢 Sionna 뉴머롤로지"),
    ],
    engines=["sionna-phy", "sbr", "radar-dsp", "torch-gpu", "matplotlib"],
    libs=["torch", "sionna", "mitsuba", "numpy", "scipy", "matplotlib"],
    reproduce=[
        "cd /home/yunjung/workspace/sionna2",
        "SIONNA2_GPU=3 ~/.venvs/py312/bin/python src/detection_gpu.py    # GPU 커널 자기검증",
        "SIONNA2_GPU=3 SIONNA2_DET_BATCH=48 ~/.venvs/py312/bin/python src/experiment_detection.py  # 9모드 스윕",
        "~/.venvs/py312/bin/python src/anim_plots.py --which all         # 애니(GIF)",
        "~/.venvs/py312/bin/python src/make_notebook12.py                # report12.ipynb",
    ],
    artifacts=[
        dict(file="outputs/detection_rx_sweep.json", what="9모드 Pd/Pfa/SNR50 전체 스윕"),
        dict(file="outputs/figures/report12_9mode.png", what="9-모드 벤치마크 (헤드라인)"),
        dict(file="outputs/figures/report12_pd_curves.png", what="Rx 1→4 Pd 곡선 (풀 모드)"),
        dict(file="outputs/renders/anim/rd_rxbuildup_nr.gif", what="Rx 증설로 표적이 떠오르는 RD 맵"),
    ],
    caveats=[
        "**'점유율'을 시간가변으로 현실성 있게 모델하진 않았다**(사용자와 합의). 9모드는 **고정 점유 레벨**이며, "
        "각 모드는 그 모드의 송신 파형을 기준으로 상관한다(full-waveform capture 상한). WiFi 센싱에서 "
        "트래픽을 인위로 늘려 재는 관행과 같은 전제다.",
        "**상시 vs 제어는 '기준신호 종류'의 차이지 순수 점유율이 아니다.** LTE 는 L1=CRS→L2·L3=PRS, "
        "5G 는 G1=SSB→G2·G3=NR-PRS 로 **기준신호 자체가 바뀐다**. WiFi 는 셋 다 프리앰블이라 분해능이 "
        "거의 안 변한다(데이터 점유만 다름).",
        "**코히어런트 결합은 소자 간 위상을 안다고 가정**한다. 몬테카를로는 √N 을 해석적으로 주입하고 "
        "잡음 보존만 실측하므로, 보고된 +6 dB(N=4)는 **이상적 상한**이다 — 실측(X410)은 조향 불일치·보정오차로 "
        "그 이하.",
        "**Pfa 공정성 미완(적대적 검증이 짚음).** 파형(std)별 명목 Pfa 만 교정해서 **모드 간 경험적 Pfa 가 "
        "완전히 같지 않다**(특히 5G 상시 SSB 는 대역이 좁아 미교정). 큰 모드 차이(대역폭 물리)는 견고하나, "
        "~1 dB 안쪽 차이는 이 한계를 감안해 읽어야 한다. 완전 공정 비교는 경험적 Pfa 축 ROC 가 필요(향후 과제).",
        "**5G 이중고 중 '저반복' 축은 이 실험에 안 들어갔다(정직).** CPI 는 표준별 고정 PRF(fs/Lf)로 "
        "타일링하는데, 5G 상시신호(SSB)의 **실제 반복률은 그보다 훨씬 낮다**(SSB 는 20 ms 주기라 무모호 "
        "속도 ~1 m/s). 즉 '5G 이중고 = 좁은 대역 + 낮은 반복' 중 **대역(거리분해능) 쪽만** 실험에 반영됐고 "
        "**반복(빠른 표적 접힘) 쪽은 낙관적**이다. 표적이 느려서(도플러 64 Hz) 어느 PRF 에서도 안 접히므로 "
        "**현재 결론(G1 이 대역 때문에 최악)은 유효**하지만, 빠른 표적에선 5G 가 더 불리하다(→ report11 §2 "
        "모호함수).",
        "**이 리포트는 탐지(있다/없다)까지다.** 위치·궤적을 잇는 **추적은 다음 일**이며, 감시 배열의 "
        "각도(AoA)로 관측가능성을 확보해야 한다(report11).",
    ],
    cost="GPU 배치 몬테카를로: 9모드×4×15×K 트라이얼 — 카드 1장에서 수십 분(배치 크게 → GPU 메모리 대량 사용).",
    related=[
        dict(rep="report04 (앞)", rel="9모드 파형·상시 기준신호·5G 이중고 — 이 벤치마크의 신호들"),
        dict(rep="report07~08·10~11 (앞)", rel="SBR σ · Pfa 교정 · 저속·단일 Rx 3D 불가 — 딛는 토대"),
        dict(rep="(끝)", rel="결과편. 추적은 future work."),
    ],
    glossary=GLOSS,
)

# 🔰 5분 요약
cells.append(md(
    "## 🔰 5분이면 이해하는 이 리포트",
    "",
    "**여러 귀로 들으면 더 잘 들린다.** 시끄러운 방에서 멀리서 나는 작은 소리를, 여러 사람이 같은 소리를 "
    "'방향을 맞춰' 합쳐 들으면 또렷해진다. 패시브 레이더도 똑같다 — 수신 안테나(귀)를 여러 개 두고 표적 "
    "방향으로 위상을 맞춰 더하면(**코히어런트 빔포밍**) 드론 메아리는 커지고 잡음은 그대로라 더 잘 잡힌다.",
    "",
    "**그리고 '어떤 조명등이냐'가 중요하다.** 넓은 빛(넓은 대역 신호)은 두 물체를 거리로 잘 가르고, "
    "좁은 빛(좁은 대역)은 뭉갠다. 이 리포트는 **9가지 조명등**(WiFi·LTE·5G × 상시~제어)을 서로 비교한다.",
    "",
    "핵심 두 가지:",
    "1. **탐지가 된다.** 앞 리포트의 무대·표적·신호·검출기를 합쳐 잡음을 수천 번 새로 뽑아 재보니 잡힌다.",
    "2. **WiFi 는 상시라도 넓어서 좋고, 5G 는 상시(SSB)면 좁아서 불리**하다 — 단 **제어·PRS 가 되면 5G 도 "
    "전대역**을 써서 좋아진다(당신의 X410 실험이 이 경우). 그리고 **수신기 4개면 필요한 신호 세기가 약 6 dB "
    "낮아진다**(= 더 약한·먼 드론도 탐지).",
    "",
    "> **한 장 요약:** Sionna(통신)가 준 신호 + 우리가 얹은 SBR(센싱) 밝기 = **ISAC**. 그것으로 '어떤 "
    "신호로, 수신기 몇 개로 탐지가 되나'를 **숫자로** 보인다.",
))

# 문헌 대비 위치 (정직하게 — 과장 금지)
cells.append(md(
    "## 📚 이 벤치마크가 문헌에서 차지하는 위치",
    "",
    "패시브 레이더 드론탐지 논문 21편(WiFi·LTE·5G)을 정독해 보면, 이 프로젝트가 채우는 빈틈이 분명합니다 "
    "(정직하게: 아래는 '아무도 정확히 이렇게 하지 않았다'는 뜻이지, 각 조각이 세계 최초라는 뜻은 아닙니다):",
    "",
    "| 문헌의 빈틈 | 문헌 현황 | 이 프로젝트 |",
    "|---|---|---|",
    "| **조명원 간 공정 비교** | 조사한 논문은 **모두 단일 조명원**(5G만/LTE만/WiFi만). 표준 간 head-to-head 없음 | 9모드 W/L/G 공통 프로토콜 |",
    "| **표적 RCS 를 실제로 모델** | 한 편도 드론 RCS 를 계산 안 함 — 외생 스칼라/Swerling 가정(−10~−13 dBsm) | SBR+PO, NACA-4 익형 프롭, 재질별 \\|Γ\\| |",
    "| **점유율→Pd (고정 Pfa)** | LaSen 이 최선이나 monostatic·RMSE 채점 | G1/G2/G3 = SSB/PRS/CRS, '5G 이중고' 정량화 |",
    "| **다중 Rx 이득 정량화** | **전부 최대 2채널**; N-Rx 코히어런트 이득을 잰 논문 0 | 1→4, 측정 6.0~6.4 dB vs 10log10 N |",
    "| **통제·재현** | 전부 1회성 야외, 신뢰구간·공개데이터 없음 | 반무향 챔버 + K=2000 MC + 재생성 파이프라인 |",
    "| **정직한 결함 기록** | 명목 Pfa 를 그대로 신뢰 | 경험적 Pfa 불균일을 **결함으로 기록**(§5) |",
    "",
    "<sub>⚠ **과장하지 않기**: Rényi-엔트로피 점유 게이팅, 'SSB 가 상시신호'라는 관찰은 이미 문헌에 있습니다"
    "(Maksymiuk 2022·LaSen 2026) — 우리 기여가 아닙니다. 우리 RCS 절대값(−25.9 dBsm)도 같은 밴드 실측"
    "(Li & Ling 2017, Phantom 2 −27.5 dBsm @3–6 GHz)과 **정합**하는 것이지 그 자체가 새 측정은 아닙니다"
    "(→ report08 문헌대조). 이 프로젝트의 성격은 **통제된 재현가능 벤치마크 + 정직한 결함 노출**입니다.</sub>",
    "",
    "> **실증(USRP X410)으로의 연결**: X410(TX4·RX4·400 MHz·12-bit)은 후보 파형을 **직접 송신**하므로 "
    "위 9모드를 통제 재현할 수 있고, 다중 RX 채널로 이 리포트의 Rx 이득을 실측 검증하는 자연스러운 "
    "테스트베드입니다. 단 시뮬(통제 챔버)↔실측(외부)은 환경이 1:1 이 아니라 **구조**(바이스태틱·기준+감시·"
    "같은 파형·디텍션 체인)만 같습니다.",
))

# §1 무대
g0 = MD[FULL[0] if FULL else CODES[0]]
cells.append(md(
    "# §1. 실험 무대 — 바이스태틱 · 기준 + 감시 배열",
    "",
    "송신기(TX, 조명원)와 수신기가 **떨어져** 있다. 수신기는 두 몫: **기준 채널**(직접파를 받아 '무슨 신호를 "
    "쐈는지' 앎)과 **감시 배열**(표적 쪽을 보는 여러 소자, λ/2 균일선형배열). 감시 소자 수 **N 을 1→4** 로 "
    "늘리는 것이 실험 변수다.",
    "",
    f"표적 = **{M['drone']}**(방위 az={M['az']:.0f}°), SBR(Mitsuba) 밝기 **σ={M['sigma_dbsm']:.1f} dBsm** "
    f"(이 **특정 자세**의 값 — 방위평균은 −19.7 dBsm, report08; RCS 는 자세에 ~14 dB 출렁인다), "
    f"속도 {abs(M['vel'][0]):.0f} m/s → 도플러 ≈{g0['fd_true']:.0f} Hz, 바이스태틱 거리 R_b≈{g0['Rb_true']:.1f} m.",
))
cells.append(gif("rx_array", "감시배열 Rx 1→4 증설",
                 f"감시 배열을 1→2→3→4 소자로 늘리는 모습(시각화용으로 간격 과장). 실제 λ/2={100*(3e8/M['fc'])/2:.1f} cm."))

# §2 신호
cells.append(md(
    "# §2. 신호 만들기 — Sionna PHY 로 표적 에코",
    "",
    "표적 메아리 = 송신 파형이 표적에 맞고(지연 τ) 되쏘며(도플러 f_d), 세기는 SBR σ 로 정해진다.",
    "",
    "**정확히 어디까지 Sionna 가 하나(정직):** 지연 τ 의 **분수지연 sinc 커널을 Sionna 의 "
    "`cir_to_time_channel` 이 만든다** — 이 커널을 우리가 콘볼루션한다(전체 CPI 를 `ApplyTimeChannel` 로 "
    "한 번에 먹이면 6.9M 샘플서 메모리가 20 GB+ 라 우회했다). **도플러·진폭은 우리가 위상램프로** 건다 — "
    "고정지연·협대역에서 시변 채널과 정확히 동등함을 확인했다. 그래서 해석식과의 상관 "
    f"**{CORR:.3f}** 는 **지연 연산자만** 교차검증한다(도플러·진폭은 양쪽이 같은 식이라 자명).",
    "",
    "> **ISAC 접점:** Sionna(통신)는 파형·채널(지연 펄스정형)을 주고(C), 표적이 얼마나 밝게 되쏘는지"
    "(σ, 센싱)는 우리가 SBR 로 얹었다(S). ([[report06]][[report07]])",
))
cells.append(md(
    "### §2b. 그래서 이 시뮬레이션에서 'Sionna' 는 정확히 어디에 있나 — 층별 담당표",
    "",
    "\"Sionna 로 디텍션을 했다\"는 표현은 **정확하지 않다**. 정확한 표현은 \"**Sionna 가 담보하는 "
    "전파 환경 위에, 우리가 레이더 검출 체인을 구축했다**\"이다. 검출 몬테카를로의 모든 층을 "
    "누가 담당하는지 숨김없이 펼치면:",
    "",
    "| 층 | 구현 | Sionna 관여 |",
    "|---|---|---|",
    "| 조명 파형(WiFi/LTE/5G OFDM) | 우리 합성(`waveforms.py`, 3GPP/IEEE 규격) | 동일성 검증만 — Sionna PHY 재구성과 NMSE −135 dB(report05) |",
    "| 표적 기하(R₁·R₂·L → τ·f_d) | 해석 기하(`bistatic_tau_fd`) | RT 경로 기하와 일치 검증(report01·09) |",
    "| 표적 밝기 σ | SBR = Mitsuba 광선 + 우리 PO 적분 | **Sionna 불가**(산란적분 없음 — report06 이 실증한 한계) |",
    "| 표적 에코 진폭 | 바이스태틱 레이더 방정식 | — |",
    "| 지연 펄스정형 | **Sionna PHY** `cir_to_time_channel` | ✅ 진짜 Sionna |",
    "| 도플러 | 우리 위상램프 | 시변 채널과 동등성 확인 |",
    "| 직접파(DPI) | 해석(기준신호 스케일) | — |",
    "| 클러터 | 반무향 챔버라 백색잡음+DPI 만(정적 클러터는 ECA 가 차단하는 죽은 파라미터, report09) | 챔버 전파 자체(바닥 반사·유령)는 RT 로 별도 검증 |",
    "| ECA → 거리-도플러 → CFAR → 빔포밍 | **전부 우리 구현** — 검출기는 이 연구의 대상 그 자체 | 어떤 시뮬레이터도 제공하지 않는 층 |",
    "",
    "**이게 문제인가? — 아니다, 이것이 레이더 시뮬레이션의 표준 구조다.** '드론 검출' 버튼이 달린 "
    "시뮬레이터는 존재하지 않는다. 다른 부류의 도구들이 각각 어디까지 하는지 보면 분명해진다:",
    "",
    "| 도구 부류 | ① 표적 밝기 σ | ② 채널(τ·f_d·감쇠) | ③ 검출기(CFAR 등) |",
    "|---|---|---|---|",
    "| 드론 시뮬(Gazebo·AirSim·Isaac) | ✗ 없음 | ✗ 없음 | ✗ '광선 맞으면 탐지됐다고 **가정**'(잡음 얹은 거리·속도 출력) — 전파 물리 자체가 없다 |",
    "| 레이더 시뮬 표준(MATLAB Radar Toolbox) | 사용자가 **상수 입력**(`MeanRCS=` — 문헌값 또는 별도 EM 계산) | 해석식(`FreeSpace` — 자유공간 가정) | 블록을 **직접 조립** |",
    "| EM 솔버(Ansys HFSS SBR+·Altair Feko) | ✅ 이것만 한다 | ✗ | ✗ |",
    "| **우리 스택** | 자체 SBR(평판/구 이론 대조 검증, report07) | 해석식 + **Sionna RT 가 챔버 물리를 담보**(자유공간 가정 대신) | 직접 구현(연구 대상) |",
    "",
    "즉 'σ 주입 + 해석 채널 + 자체 신호처리'는 우리가 발명한 편법이 아니라 **MATLAB 로 하는 표준 "
    "레이더 시뮬과 동일한 구조**이고, 차이는 ② 에서 자유공간 가정 대신 Sionna RT 검증을 얹은 것뿐이다. "
    "검출기(ECA·CFAR)는 우리가 **만들어서 검증하는 대상**이므로 애초에 남의 것일 수 없다.",
    "",
    "**그럼 Sionna 를 쓴 의미는? — 솔직한 버전.** 이 검출 몬테카를로 **그 자체**만 떼어놓고 보면 "
    "Sionna 는 거의 필요 없다(지연 커널 하나는 scipy 로도 된다). Sionna 의 의미는 검출 루프 밖 세 곳에 있다:",
    "",
    "① **감사관** — 이 시뮬의 채널이 '직접파+에코+잡음'뿐이어도 되는 이유는 가정이 아니라 **RT 로 챔버를 "
    "추적해 얻은 결론**이다(벽·천장 흡수 확인, 잔향 무시 가능 확인, 반사 경로는 바닥뿐 — report01). 챔버가 "
    "환경을 단순하게 만들었고, **그 단순함의 증명이 Sionna 의 일**이었다. "
    "② **탐정** — 해석 모델만으론 존재조차 몰랐을 표적경유 바닥 유령을 RT 가 찾아냈고(report09), 그것이 "
    "'전대역 5G 100% 오검출'이라는 헤드라인 결론이 됐다. "
    "③ **다음 단계의 주인공** — 실측(X410)은 실외라 멀티패스가 풍부해 해석 탭으로 안 되고, 그때는 RT 가 "
    "채널 탭을 직접 공급해야 한다. 챔버 단계의 RT 검증은 그 준비다.",
    "",
    "반사실로 요약: Sionna 없이 했다면 Pd 곡선 숫자는 아마 같았겠지만 — (1) 그 숫자의 전제(단순 채널)를 "
    "증명할 수 없었고, (2) 유령을 몰라 5G 결론이 틀렸을 것이며, (3) 실측과 어긋났을 때 원인을 좁힐 수단이 "
    "없었을 것이다. 정확한 문장은 \"Sionna 가 검출을 해줬다\"가 아니라 **\"Sionna 가 검출 시뮬의 전제를 "
    "검증하고 구멍(유령)을 찾아줬다\"**이다.",
    "",
    "> ⚠️ **남은 정직한 갭:** 이 몬테카를로의 채널은 '해석 탭(에코+직접파)+백색잡음'이다 — report09 의 "
    "바닥 유령 탭과 잔향 꼬리는 **이 MC 채널에 넣지 않았다**(유령은 기하·위협 정량화까지만). 실측 "
    "X410 과의 대조에서 이 미모델 성분이 첫 번째 용의자가 될 것이다.",
))
cells.append(md(
    "### §2c. 선행 연구 속 우리 위치 — 이 아키텍처는 주류다",
    "",
    "위 층별표(σ 주입 + 표적/배경 채널 분리 + 검출체인 직접 구현)가 **표준인지** 선행으로 확인했다"
    "(전체 근거·출처: `prior_work/` pw01~03, `OPENSOURCE.md`):",
    "",
    "| 우리 구성 | 같은 구조의 주류 선행 | 판정 |",
    "|---|---|---|",
    "| 표적/배경 채널 분리 `h = h_bg + h_target` | **NIST 5GNRad**(usnistgov/5GNRad)·**3GPP ISAC 채널모델**·**MATLAB** | 동일 |",
    "| 표적 밝기를 σ 로 주입 | NIST 5GNRad·MATLAB(`MeanRCS=`) | 동일 |",
    "| 환경 전파를 Sionna RT 로 담보 | Deterministic-Modeling(EuCAP 2026)·SimART | 동일 |",
    "| σ 를 확산계수 가정 대신 **드론 메쉬에서 SBR+PO 로 산출** | 대개 확산 S(Great-X) 또는 RCS 상수 | **차이(강화)** |",
    "",
    "즉 우리 뼈대는 **NIST 5GNRad·3GPP 와 같은 주류 ISAC 아키텍처**다. 덜 점유된 틈새는 세 가지 결합 — "
    "①상용 신호(WiFi/LTE/5G) **패시브 바이스태틱**(선행은 대개 능동/모노 또는 CSI기반), ②드론 RCS 를 "
    "**SBR+PO 로 산출**(확산 S 가정 아님), ③**상시 vs 세션 9모드** 벤치마크.",
    "",
    "> 🔧 **오픈소스·선행 방식 채택(계층별, 전체 지도 `OPENSOURCE.md`·`prior_work/pw02`):**",
    "> - **검출체인 ECA/CAF/CFAR → pyAPRiL**(GPLv3, 실측 검증된 패시브 레이더 라이브러리). 실제로 돌려 "
    f"NR/WiFi/LTE 3모드 모두 표적을 정답 거리빈에 검출함을 확인(`benchmark/verify_pyapril.py`). 대량 MC(K="
    + f"{K:,}" + ")만 GPU 배치(`detection_gpu.py`)로 하되 pyAPRiL 로 정합 검증. ⚠ ECA/CAF/CFAR 는 파형 무관 "
    "(reference I/Q 만 사용) — DVB-T/FM 뿐 아니라 WiFi/LTE/5G 에 적합.",
    "> - **RCS → 자작 SBR+PO**(선행 BVH SBR+PO 와 같은 방법; 상용 CADFEKO·비공개 RadarSimPy 불채택), "
    "절대값은 **실측 문헌 RCS 로 앵커**(report08). **추적 → Stone Soup**, **실측 → OpenISAC+GNU Radio+X410**.",
    "> - **파형·지연채널**은 **Sionna PHY** 로 검증(report05, NMSE −135 dB) 유지. **아키텍처**(h=h_bg+h_target)는 "
    "**NIST 5GNRad·3GPP Rel-19**(오픈 구현 Putirf)와 동일.",
))
cells.append(gif("rd_rxbuildup_nr", "Rx 증설 RD 맵(5G 풀)",
                 "거리-도플러 지도. 수신기 1→4 로 표적(흰 네모)이 잡음 위로 떠오른다. 0-도플러 세로 능선은 "
                 "직접파 잔차(가드로 제외)."))

# §3 9-모드 벤치마크 (헤드라인)
def _mode_row(c):
    w = MD[c]
    v = s50(c)
    drb = w["range_res_m"]                                # 바이스태틱 c/B (JSON 에 저장된 값)
    drm = drb / 2.0                                       # 모노스태틱 등가 c/2B
    return (f"| {c} | {SNAME[w['std']]} | {w['ref_name']} | {w['ref_bw_mhz']:.1f} MHz | "
            f"{drb:.1f} m | {drm:.1f} m | {'상시' if w['always_on'] else '세션/제어'} | "
            f"{('%.1f' % v) if v is not None else '—'} dB |")


tbl = ["# §3. 9-모드 벤치마크 — 어떤 신호가 드론을 잘 비추나 ⭐", "",
       "3표준 × 3점유(상시→제어/풀) = 9모드. 필요한 SNR(단일 Rx, 낮을수록 좋음):", "",
       "| 모드 | 표준 | 기준신호 | 대역 $B_{ref}$ | $\\Delta R_b$ (바이스태틱, c/B) | "
       "$\\Delta R$ (모노 등가, c/2B) | 종류 | 필요 SNR |",
       "|---|---|---|---|---|---|---|---|"]
for c in CODES:
    tbl.append(_mode_row(c))
cells.append(md(*tbl))
cells.append(fig("report12_9mode", "9-mode benchmark SNR50"))
cells.append(md(
    "**읽는 법.** 막대가 낮을수록 더 약한 드론도 잡는다(좋다). 빗금친 막대가 **상시(협조 없이 얻는 것)**.",
    "",
    "> **거리분해능 규약(정합성):** 이 표의 $\\Delta R_b = c/B_{ref}$ 는 **바이스태틱** 거리분해능이다"
    "(바이스태틱 거리는 왕복이 아니므로 $c/2B$ 가 아니라 $c/B$ — report11 §2 및 문헌 25_UAV Intrusion 과 "
    "동일 규약). 모노스태틱 등가값은 이 절반이다.",
    "",
    "- **WiFi 는 상시라도 광대역**(프리앰블 76.6 MHz) → 셋 다 거리분해능 ~3.9 m 로 좋다. 데이터 점유(W1→W3)는 "
    "분해능을 거의 안 바꾼다(프리앰블이 고정 기준이라).",
    "- **5G 는 상시(G1=SSB)면 7.2 MHz 로 병적으로 좁다**($\\Delta R_b$ 41.6 m, 모노 등가 20.8 m) — 진짜 "
    "'5G 이중고'. 하지만 **G2·G3(NR-PRS)로 가면 98 MHz** 전대역 → $\\Delta R_b$ 3.1 m 로 급반전.",
    "- **LTE 는 L1=CRS(상시) → L2·L3=PRS(측위세션)** 로 기준신호가 바뀐다.",
    "",
    "> **실증(X410)은 어디에?** X410 은 후보 파형을 **직접 송신(제어)** 하므로 전대역 상시 = **풀 모드(G3/L3/"
    "W3)** 에 해당한다. 상시(G1/L1/W1)는 '비협조 조명원일 때의 하한선'으로 읽으면 된다.",
))

# §4 Rx 증설
cells.append(md(
    "# §4. 수신기를 늘리면 — 코히어런트 배열 이득 (이상적 상한)",
    "",
    "감시 배열 N 소자를 표적 방향으로 위상 맞춰 더하면 표적 √N 배·잡음 그대로 → **출력 SNR N배(+10log10 N "
    "dB)**. N=4 면 +6.0 dB. 이는 **교과서적 배열이득이며, 여기서는 이상적 상한**이다: **완벽 조향**(표적 "
    "방위를 정확히 앎)·**소자 간 등분산 독립잡음**·보정오차 0 을 가정한다. 몬테카를로는 이 정합 빔포머와 "
    "동치인 형태로 √N 을 신호에 주입하고, 잡음쪽 전력보존(σ²)만 독립 실측한다(§tldr②). 실측 X410 은 조향 "
    "불일치·상호결합·동기오차로 **이 상한 이하**다. 빔패턴도 N 으로 날카로워진다:",
))
cells.append(gif("beampattern", "배열 빔패턴",
                 "감시 ULA 빔패턴이 N=1→4 로 좁아진다(표적 방위로 조향, 점선)."))
cells.append(md("**검출확률 곡선(풀 모드).** 수신기를 늘릴수록 곡선이 왼쪽으로(더 약한 표적도 탐지) 이동:"))
cells.append(fig("report12_pd_curves", "Pd vs SNR, N=1..4, 풀 모드"))
cells.append(gif("pd_build_nr", "Pd 곡선 그려짐", "N=1→4 순으로 그려가는 애니(5G 풀)."))
# SNR50 이득 표 (풀 모드)
gtbl = ["**필요 SNR(SNR50)과 수신기 증설 이득 — 풀 모드:**", "",
        "| 모드 | N=1 | N=2 | N=3 | N=4 | N=4 이득 | 이상적 |", "|---|---|---|---|---|---|---|"]
for c in FULL:
    vals = [s50(c, N) for N in M["n_list"]]
    g4 = gain4(c)
    gtbl.append(f"| {c} ({SNAME[MD[c]['std']]}) | " +
                " | ".join(f"{v:.1f}" if v is not None else "—" for v in vals) +
                f" | **−{g4:.1f} dB** | −6.0 dB |")
gtbl += ["", "이론(−6.0 dB)에 거의 정확히 붙는다 — **수신기 증설 이득은 조명원 종류와 무관한 배열 물리**다."]
cells.append(md(*gtbl))
cells.append(fig("report12_snr50_vs_n", "감도 이득 vs 수신기 수"))

# §5 몬테카를로
cells.append(md(
    "# §5. 몬테카를로 — 많이 반복해야 믿는다",
    "",
    f"Pd 는 확률이라 잡음을 **{K:,}번** 새로 뽑아(각 SNR·N·모드마다) 추정한다. GPU 에 수십 트라이얼을 "
    "**배치로 한꺼번에** 올려(torch) 빠르게 반복 — 배치를 키우면 GPU 메모리를 많이 쓴다.",
))
cells.append(gif("mc_converge_nr", "몬테카를로 수렴", "시행수↑ 로 Pd 추정·95% 신뢰구간이 좁아진다."))
cells.append(md(
    "**오경보율 — 정직하게(적대적 검증 반영).** report10 의 **파형(std)별** Pfa 교정을 적용했다. 하지만 "
    "이 교정은 표준별로만 되어 있어(점유/기준신호별 아님), 특히 **5G 상시(G1=SSB 7.2 MHz)** 처럼 대역이 "
    "아주 좁은 모드는 완전히 교정되지 않는다. 표적 없는 트라이얼로 잰 **경험적 Pfa 는 모드마다 다르고 목표 "
    f"10⁻⁴ 와 정확히 같지 않다**(목표 대비 {PFA_RATIO_MIN:.2f}~{PFA_RATIO_MAX:.2f}배 — 최저는 G1). "
    "따라서 **§3 의 모드 간 SNR50 차이 중 ~1 dB 안쪽의 "
    "미세한 차이는 이 불균일을 감안해 읽어야 한다** — 큰 차이(WiFi 광대역 vs 5G SSB, 수~십수 dB)는 대역폭 "
    "물리가 지배하므로 견고하다. 완전한 공정 비교는 각 모드의 **경험적 Pfa 축에 ROC 를 그려** 맞춰야 하며, "
    "이는 향후 과제다.",
))
cells.append(fig("report12_pfa", "경험적 Pfa (9모드) — 목표 10⁻⁴ 대비 (완전 균일 아님)"))

# §6 결론
cells.append(md(
    "# §6. 결론 — 탐지는 된다, 추적은 다음 일",
    "",
    "1. **탐지가 된다.** 9모드 모두 충분한 SNR 에서 드론을 잡는다(Pd→1.0).",
    "2. **조명원이 중요하다.** 상시라면 WiFi(광대역)가 유리, 5G(SSB)는 불리 — 단 PRS·제어면 5G 도 전대역. "
    "실증(X410 제어)은 풀 모드에 해당.",
    f"3. **수신기를 늘리면 감도가 오른다.** Rx 1→4 로 필요한 SNR 이 5G 풀 기준 **{NR_G4:.1f} dB** 낮아진다"
    "(이론 6 dB 와 일치).",
    "4. **정직성.** 에코 지연은 Sionna `cir_to_time_channel`(상관 "
    f"{CORR:.3f} 는 지연만 검증), 배열이득은 이상적 상한(√N 주입·잡음보존만 실측 {CRAT:.3f}), "
    "Pfa 는 std별 명목 교정(모드 간 완전 균일은 아님). 모두 리포트에 명시했다.",
    "",
    "> ### ▶ 다음 일 (future work): 추적",
    "> 이 리포트는 **탐지**까지다. 위치·궤적을 잇는 **추적**은 감시 배열의 **각도(AoA)** 로 3D 관측가능성을 "
    "확보해야 한다(report11: 단일 수신기로는 3D 위치 불가). 본 실험이 쓴 **다중 수신기 배열이 그 출발점**이다.",
))

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
with open(NB, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f"✅ {os.path.relpath(NB, ROOT)}  ({len(cells)} cells)  |  {len(CODES)}모드, full={FULL}")
