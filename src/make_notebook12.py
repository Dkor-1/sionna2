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
# ─────────────────────────────────────────────────────────────────────────────
# ⚠ 이 파일은 **스크립트**다 (main() 없이 최상위에서 전부 실행된다).
#   임포트하면 그 자리에서 리포트 노트북을 **덮어쓴다**. 2026-07-29 실제로 검증 에이전트가
#   "임포트 되는지" 점검하다가 report07/08/13 을 덮어썼고 복구해야 했다. linter·문서도구·
#   테스트수집기도 같은 사고를 낸다 — 게다가 계산이 도는 중이면 **중간 숫자**가 박힌다.
#   → 실행은 `python src/make_notebook12.py` 로만.
if __name__ != "__main__":
    raise RuntimeError(
        "make_notebook12.py 는 스크립트다 — 임포트하면 리포트를 덮어쓴다. "
        "`python src/make_notebook12.py` 로 실행할 것. (2026-07-29 실사고)")
# ─────────────────────────────────────────────────────────────────────────────

ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from provenance import provenance_cells                      # noqa: E402

NB = os.path.join(ROOT, "report12.ipynb")
J = json.load(open(os.path.join(ROOT, "outputs", "detection_rx_sweep.json"), encoding="utf-8"))
M = J["meta"]

# report08 이 내는 방위평균 σ 를 **같은 출처에서** 읽어온다 — 산문에 손으로 적으면 재생성 때 조용히 어긋난다.
_J2 = json.load(open(os.path.join(ROOT, "outputs", "report2_waveform_rcs.json"), encoding="utf-8"))
_B2 = _J2["rcs"]["drones"]["mavic4pro"]["bands"]
AZAVG_35 = _B2["5G NR 3.5 GHz"]["mean_dbsm"]                       # 방위평균 @3.5 GHz
AZAVG_BAND = sum(v["mean_dbsm"] for v in _B2.values()) / len(_B2)  # 3밴드 평균

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
_pfa_mean = {}
for _c in CODES:
    _vals = [p for _cv in MD[_c]["curves"].values() for p in _cv["Pfa_emp"]]
    if _vals:
        _pfa_mean[_c] = sum(_vals) / len(_vals)
PFA_LO_C = min(_pfa_mean, key=_pfa_mean.get)          # 경험 Pfa 최저 = 문턱이 가장 빡센 모드
PFA_HI_C = max(_pfa_mean, key=_pfa_mean.get)
PFA_RATIO_MIN = _pfa_mean[PFA_LO_C] / _pfa_t
PFA_RATIO_MAX = _pfa_mean[PFA_HI_C] / _pfa_t

# CA-CFAR 문턱 α = N_tr(Pfa^(−1/N_tr)−1) — guard/train 은 passive_process.ca_cfar_2d 및
# detection_gpu.cfar_batch 의 기본값 (2,2)/(6,6). 내부 셀의 학습셀 수를 그 규약대로 계산한다.
_GUARD, _TRAIN = (2, 2), (6, 6)
NTR = ((2 * (_GUARD[0] + _TRAIN[0]) + 1) * (2 * (_GUARD[1] + _TRAIN[1]) + 1)
       - (2 * _GUARD[0] + 1) * (2 * _GUARD[1] + 1))


def _alpha(pfa):
    return NTR * (pfa ** (-1.0 / NTR) - 1.0)


# 경험 Pfa 불균일 → 문턱 차[dB] (모드 간 SNR50 차이 중 '교정 잔차' 몫)
PFA_TH_SPREAD_DB = 10 * np.log10(_alpha(_pfa_mean[PFA_LO_C]) / _alpha(_pfa_mean[PFA_HI_C]))
# x축 SNR 의 잡음 기준: 셀 전력 **중앙값**. 지수분포면 중앙값 = ln2 × 평균 → 평균 기준과의 오프셋
MEDIAN_REF_DB = 10 * np.log10(1.0 / np.log(2.0))
SNAME = {"wifi": "WiFi", "lte": "LTE", "nr": "5G"}
FULL = [c for c in ("W3", "L3", "G3") if c in MD]              # 제어/풀 (X410 실험 레짐)
ON = [c for c in ("W1", "L1", "G1") if c in MD]                # 상시 (기회주의 하한)
STD2FULL = {"nr": "G3", "wifi": "W3", "lte": "L3"}
K = M["K"]

# 다중 Rx 코히어런트 이득(1→4) 범위 — JSON 에서 주입(§6, 손으로 적지 않음)
def _gain14(c):
    cu = MD[c]["curves"]
    return cu["1"]["snr50"] - cu["4"]["snr50"]
GAIN_LO = min(_gain14(c) for c in CODES)
GAIN_HI = max(_gain14(c) for c in CODES)
CORR = np.mean([MD[c].get("corr_sionna", 1.0) for c in CODES])
CRAT = np.mean([MD[c].get("combine_ratio", 1.0) for c in CODES])

# 코히어런트 배열이득의 이론 상한 10log10(N_max) 과, 주입 이득이 그것을 넘는 양
NMAX = max(M["n_list"])
IDEAL_GAIN_DB = 10 * np.log10(NMAX)
EXCESS = {c: _gain14(c) - IDEAL_GAIN_DB for c in CODES}
EXC_C = max(EXCESS, key=EXCESS.get)
EXC_MAX = EXCESS[EXC_C]
N_EXCEED = sum(1 for v in EXCESS.values() if v > 0.05)   # 0.05 dB 넘게 상한 초과한 모드 수


def s50(code, N=1):
    return MD[code]["curves"][str(N)]["snr50"]


def gain4(code):
    b, f = s50(code, 1), s50(code, 4)
    return (b - f) if (b is not None and f is not None) else None


NR_G4 = gain4(STD2FULL["nr"])
# 상시 3인방 SNR50(N=1)
ON_S = {c: s50(c) for c in ON}
FULL_S = {c: s50(c) for c in FULL}

# 9모드 SNR50(N=1) 의 실제 스팬 — 산문에 손으로 적지 않고 여기서 뽑아 쓴다
_S50 = {c: s50(c) for c in CODES if s50(c) is not None}
S50_WORST = max(_S50, key=_S50.get)
S50_BEST = min(_S50, key=_S50.get)
SPAN50 = _S50[S50_WORST] - _S50[S50_BEST]
# 상시(G1급) 모드의 점유율은 표준마다 다르다 — '직교 요인설계' 가 아님을 §3 에서 밝히는 데 사용
ON_OCC = {SNAME[MD[c]["std"]]: MD[c]["occupancy"] * 100 for c in ON}


def _pm(v):
    """부호를 유니코드 −/+ 로 (그림·본문 표기 통일)."""
    return ("+" if v >= 0 else "−") + f"{abs(v):.2f}"


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
    ("패시브(수동) 바이스태틱 레이더",
     "자기 송신기 없이 **이미 켜진 통신 신호**(WiFi·LTE·5G)를 조명으로 빌려, 떨어진 수신기로 "
     "표적 메아리를 듣는 레이더."),
    ("ISAC (통합 센싱·통신)",
     "송신기를 **통신+센싱 겸용으로 설계·제어**하는 것. 파형을 센싱에 맞게 빚을 수 있다. "
     "패시브(제어 못 함)와 대비된다. 이 프로젝트의 X410 실험은 송신을 **제어**하므로 ISAC 에 가깝다."),
    ("상시(always-on) vs 세션/제어 기준신호",
     "상시 = 아무 셀이나 늘 내보내는 신호(WiFi 프리앰블·LTE CRS·5G SSB) — 협조 없이 패시브가 "
     "얻는 것. 세션/제어 = PRS(측위세션 필요) 또는 송신 전체 캡처(협조/제어) — 더 넓은 대역을 준다."),
    ("검출확률 Pd / 오경보율 Pfa",
     "Pd=표적 있을 때 잡을 확률, Pfa=없는데 잘못 외칠 확률. **같은 Pfa 에서** Pd 를 비교해야 공정."),
    ("RD 맵 (거리-도플러 지도)",
     "수신 신호를 가로=거리, 세로=속도(도플러)로 펼친 2차원 지도. 표적은 자기 칸에 밝은 점."),
    ("코히어런트 빔포밍",
     "여러 수신 소자를 표적 방향으로 위상 맞춰 더하기. 표적 √N 배·잡음 그대로 → SNR N배(+10log10 N dB)."),
    ("거리분해능 (바이스태틱 vs 모노스태틱)",
     "두 물체를 거리로 가르는 능력. 대역폭이 넓을수록 작아진다(좋다). ⚠ **바이스태틱**(우리 시스템)은 "
     "거리가 왕복이 아니므로 $\\Delta R_b = c/B$, **모노스태틱**은 왕복이라 $\\Delta R = c/2B$(절반). "
     "두 값을 구분해 관리한다(report11 §2 도 바이스태틱 c/B)."),
    ("Sionna PHY / SBR",
     "Sionna PHY=파형·채널(여기서 표적 에코 생성). SBR=Mitsuba 광선+우리 PO 로 표적 밝기 σ. "
     "[[report06]][[report07]]"),
]

cells = []
cells += provenance_cells(
    report="report12",
    what="다중 수신기 디텍션 + 9-모드 벤치마크",
    question="어떤 통신 신호(9모드)로, 수신기 몇 개로 드론이 실제로 잡히나?",
    spine=dict(
        core=(f"앞 리포트의 무대·표적(SBR σ)·신호(Sionna PHY)·검출기를 하나로 합쳐, **어떤 통신 신호로 · "
              f"수신기 몇 개로 드론이 실제로 잡히는지**를 몬테카를로로 못박는다 — 9모드(3표준×3점유) × 감시 "
              f"배열 1→4, K={K:,}회. 이 프로젝트의 **결과편**이다(탐지까지 — 추적은 future work)."),
        gap=(f"탐지 한 번은 네 재료를 요구한다: **① 조명 파형 · ② 채널(τ·f_d) · ③ 표적 밝기 σ · "
             f"④ 검출 체인**(직접파 제거 ECA → 거리-도플러 → CFAR → 빔포밍). Sionna 는 **①②만** 담보하고"
             f"(PHY·RT), **③ σ 는 산란적분 부재로 못 내며**(report06), **④ 패시브 레이더 검출 파이프라인은 "
             f"아예 없다**(Sionna 에 레이더 DSP 부재). 셋을 밖에서 채워 결합해야 한다."),
        prior=("패시브 바이스태틱 드론탐지 선행은 표적 산란을 **외부에서 구해 채널에 주입**"
               "($h=h_{bg}+h_{target}$; NIST 5GNRad · 3GPP Rel-19 오픈구현(arXiv:2606.07328) · "
               "LAMBDA=Sionna+CADFEKO(arXiv:2607.03826))하고, 표준 검출 체인(ECA/CAF/CFAR)으로 잡는다"
               "(Wypich & Zielinski, *Sensors* 2026 — 단 **표적은 차량**·5.8 GHz·원문 PDF 미확보; LTE450 쪽은 "
               "우리가 원문을 연 Demissie 외 *2024 International Radar Conference (RADAR)* 판을 쓴다 — "
               "후속 *IET RSN* 2025 판은 페이월이라 읽지 못해 귀속하지 않는다). 단 조사한 선행은 대개 **단일 조명원**이라 "
               "**표준 간 공정 비교가 비어 있다**. 다소자 감시 배열 실측 자체는 이미 있고(LIPASE, IEEE "
               "OJ-COMS 2025 — 감시 ULA 중앙 8소자 활성·기준 4소자, 12안테나 디지털 빔포밍), 조사 범위에서 "
               "비어 있는 것은 **소자 수 N 에 대한 이득 곡선**이다(§6)."),
        lib=(f"검출 체인은 **pyAPRiL**(GPLv3, 실측 검증된 패시브 레이더 ECA/CAF/CFAR)로 정확성을 검증하고, "
             f"대량 Pd 곡선은 그 검증된 체인을 **GPU(torch)로 K={K:,}회 반복**한다(`detection_gpu.py`). 표적 "
             f"에코의 지연 펄스정형은 **Sionna PHY `cir_to_time_channel`** 커널을 그대로, 표적 밝기 σ 는 "
             f"**SBR+PO** — 새 파형·산란 엔진을 만들지 않고 검증된 조각만 결합한다(중복계산 없음)."),
        verify=(f"**GPU 배치 몬테카를로 K={K:,}회**(각 SNR·N·모드)로 Pd. pyAPRiL 로 NR/WiFi/LTE 3모드 모두 "
                f"**CAF 봉우리 거리빈이 정답과 일치**하고 **CA-CFAR 이 정답 거리셀에서 발화**함(모드당 5셀)을 확인(`verify_pyapril.py`); 지연 연산자는 해석식과 상관 {CORR:.3f}"
                f"(지연만), 배열이득 √N 은 잡음전력 보존 {CRAT:.3f}만 독립 실측. 절대 σ 는 실측 문헌 드론 "
                f"RCS 로 앵커(report08)."),
    ),
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
        f"**배열이득은 측정이 아니라 주입이다.** 몬테카를로는 감시 소자를 개별 합성하지 않고 표적 에코 진폭에 "
        f"√N 을 곱하며(`experiment_detection.py:270` `surv = sqrtN*echo + dpi + noise`), 잡음 전력보존만 "
        f"독립 실측한다 — 소자별 채널·패턴·상호결합·조향오차가 없다. 게다가 같은 식에서 직접파 잔차(dpi)는 "
        f"N 과 무관하게 고정이라, §4 표의 이득이 이론 상한 10log10 N = {IDEAL_GAIN_DB:.2f} dB 를 넘는 모드가 "
        f"있다(최대 {EXC_C} +{EXC_MAX:.2f} dB). 따라서 이 곡선은 **실측 배열이득이 아니라 설계 상한**이며, "
        f"실측(X410)은 조향 불일치·상호결합·동기오차로 그 이하다.",
        f"**Pfa 공정성 미완(적대적 검증이 짚음).** 파형(std)별 명목 Pfa 만 교정해서 **모드 간 경험적 Pfa 가 "
        f"완전히 같지 않다**(특히 5G 상시 SSB 는 대역이 좁아 미교정). CA-CFAR 문턱으로 환산하면 두 극단 모드 "
        f"사이 **{PFA_TH_SPREAD_DB:.2f} dB** 차이이므로(§5), 그 규모의 모드 간 차이는 이 한계를 감안해 읽어야 "
        f"한다 — 9모드 SNR50 스팬 {SPAN50:.2f} dB 중 그만큼은 물리가 아니다. 완전 공정 비교는 경험적 Pfa 축 "
        f"ROC 가 필요(향후 과제).",
        "**5G 이중고 중 '저반복' 축은 이 실험에 안 들어갔다(정직).** CPI 는 표준별 고정 PRF(fs/Lf)로 "
        "타일링하는데, 5G 상시신호(SSB)의 **실제 반복률은 그보다 훨씬 낮다**(SSB 는 20 ms 주기라 무모호 "
        "속도 ~1 m/s — **모노스태틱 등가 표기**이고, 이 리포트의 거리축과 같은 거리합 좌표로 적으면 그 "
        "2배인 ~2.1 m/s 다; 좌표 규약은 report04 §2.3). 즉 '5G 이중고 = 좁은 대역 + 낮은 반복' 중 **대역(거리분해능) 쪽만** 실험에 반영됐고 "
        "**반복(빠른 표적 접힘) 쪽은 낙관적**이다. 표적이 느려(도플러 64 Hz) **이 실험에 쓴 높은 PRF 에서는** 안 접히므로 (실 SSB 반복률 20 ms 에서는 접힌다 — 그건 G1 을 더 불리하게 하므로 헤드라인 결론은 오히려 강화된다) "
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

# =========================================================================== #
#  §1. Sionna 의 공백 — 검출 파이프라인이 없다
# =========================================================================== #
cells.append(md(
    "# §1. Sionna 의 공백 — 검출 파이프라인이 없다",
    "",
    "탐지 한 번은 네 재료를 요구한다: **① 조명 파형**, **② 표적까지의 채널**(지연 τ·도플러 f_d), "
    "**③ 표적 밝기 σ**, **④ 검출 체인**(직접파 제거 ECA → 거리-도플러 → CFAR → 빔포밍). Sionna 는 이 중 "
    "**①②만** 담보한다 — PHY 파형·`cir_to_time_channel` 지연커널과 RT 챔버 전파(report05 NMSE −135 dB). "
    "**③ σ 는 산란적분이 없어 못 내고**(report06), **④ 패시브 레이더 검출 파이프라인은 아예 없다**"
    f"(Sionna 에 레이더 DSP 부재). 이 리포트는 ③을 SBR+PO 로, ④를 검증된 표준 체인으로 채워 넷을 결합한 "
    f"뒤 K={K:,}회 몬테카를로로 탐지를 측정한다.",
    "",
    "그래서 \"Sionna 로 디텍션을 했다\"는 정확하지 않다. 정확히는 **Sionna 가 담보하는 전파 환경·파형 위에 "
    "표준 레이더 검출 체인을 올렸다**이다. 검출 몬테카를로의 각 층이 어디서 오는지 펼치면:",
    "",
    "| 층 | 출처 | Sionna 관여 |",
    "|---|---|---|",
    "| 조명 파형(WiFi/LTE/5G OFDM) | Sionna PHY 뉴머롤로지(`sionna.phy.nr`) | ✅ 검증됨 — NMSE −135 dB(report05) |",
    "| 표적 기하(R₁·R₂·L → τ·f_d) | 해석 기하 | RT 경로 기하와 일치 검증(report01·09) |",
    "| 표적 밝기 σ | SBR+PO(선행 BVH SBR+PO 와 같은 계열 — 적용범위 차이는 report06 §4) | "
    "**스톡 경로 솔버로는 불가**(표면 산란적분 단계가 없다 — report06) |",
    "| 표적 에코 진폭 | 바이스태틱 레이더 방정식 | — |",
    "| 지연 펄스정형 | **Sionna PHY** `cir_to_time_channel` | ✅ 진짜 Sionna |",
    "| 도플러 | 위상램프(시변 채널과 동등) | — |",
    "| 직접파(DPI)·클러터 | 반무향 챔버 → 백색잡음+DPI(정적 클러터는 ECA 가 차단, report09) | 챔버 전파·바닥유령은 RT 로 별도 검증 |",
    "| ECA → 거리-도플러 → CFAR → 빔포밍 | **표준 패시브 레이더 체인**(오픈소스 pyAPRiL 로 검증) | 시뮬레이터가 제공하지 않는 층 |",
    "",
    "이 구조(σ 를 외부에서 주입 + 표적/배경 채널 분리 + 표준 검출 체인)는 **레이더 시뮬레이션의 표준**이다. "
    "다른 부류의 도구가 각각 어디까지 하는지 보면 분명하다:",
    "",
    "| 도구 부류 | ① 표적 밝기 σ | ② 채널(τ·f_d·감쇠) | ③ 검출 체인 |",
    "|---|---|---|---|",
    "| 드론 시뮬(Gazebo·AirSim·Isaac) | ✗ | ✗ | ✗ '광선 맞으면 탐지'로 **가정**(전파 물리 없음) |",
    "| 레이더 시뮬 표준(MATLAB Radar Toolbox·NIST 5GNRad) | 상수/외부 EM 입력(`MeanRCS=`) | 해석식(자유공간) 또는 점산란체 | 블록 조립(CFAR 등) |",
    "| EM 솔버(HFSS SBR+·Feko) | ✅ 이것만 | ✗ | ✗ |",
    "| **이 스택** | SBR+PO(평판/구 이론 + 실측 문헌 앵커로 검증, report07·08) | 해석식 + **Sionna RT 가 챔버 물리를 담보** | 표준 ECA/CAF/CFAR(pyAPRiL 검증) |",
    "",
    "즉 'σ 주입 + 표적/배경 채널 분리 + 표준 신호처리'는 편법이 아니라 **MATLAB·NIST 5GNRad 와 동일한 "
    "주류 구조**이고, 차이는 ②에서 자유공간 가정 대신 **Sionna RT 검증**을 얹은 것이다.",
    "",
    "**Sionna 를 쓴 의미**는 검출 루프 안이 아니라 그 밖 세 곳에 있다. "
    "① **환경 담보** — 이 시뮬의 채널이 '직접파+에코+잡음'뿐이어도 되는 근거는 가정이 아니라 RT 로 챔버를 "
    "추적한 결론이다(벽·천장 흡수·잔향 무시 가능·반사 경로는 바닥뿐, report01). "
    "② **구멍 발견** — 해석 모델로는 몰랐을 표적경유 바닥 유령을 RT 가 찾아냈고(report09), 그것이 "
    "'전대역 5G 100% 오검출'이라는 결론이 됐다. "
    "③ **실측 준비** — 실외 X410 은 멀티패스가 풍부해 해석 탭으로 안 되고, 그때 RT 가 채널 탭을 공급한다. "
    "정확한 문장은 \"Sionna 가 검출을 해줬다\"가 아니라 **\"Sionna 가 검출 시뮬의 전제를 검증하고 "
    "구멍(유령)을 찾았다\"**이다.",
    "",
    "> ⚠️ **남은 정직한 갭:** 이 몬테카를로의 채널은 '해석 탭(에코+직접파)+백색잡음'이다 — report09 의 "
    "바닥 유령 탭·잔향 꼬리는 이 MC 채널에 넣지 않았다(유령은 기하·위협 정량화까지). 실측 X410 대조에서 "
    "이 미모델 성분이 첫 용의자다.",
))

# =========================================================================== #
#  §2. 무대와 신호 — 증거를 만드는 재료
# =========================================================================== #
g0 = MD[FULL[0] if FULL else CODES[0]]
cells.append(md(
    "# §2. 무대와 신호 — 증거를 만드는 재료",
    "",
    "송신기(TX, 조명원)와 수신기가 **떨어져** 있다. 수신기는 두 몫: **기준 채널**(직접파를 받아 '무슨 신호를 "
    "쐈는지' 앎)과 **감시 배열**(표적 쪽을 보는 여러 소자, λ/2 균일선형배열). 감시 소자 수 **N 을 1→4** 로 "
    "늘리는 것이 실험 변수다.",
    "",
    f"표적 = **{M['drone']}**(방위 az={M['az']:.0f}°), SBR(Mitsuba) 밝기 **σ={M['sigma_dbsm']:.1f} dBsm** "
    f"(이 **특정 자세**의 값 — 방위평균은 {AZAVG_35:.1f} dBsm(3.5 GHz)·밴드평균 {AZAVG_BAND:.1f} dBsm, "
    f"report08; RCS 는 자세에 ~14 dB 출렁인다), "
    f"속도 {abs(M['vel'][0]):.0f} m/s → 도플러 ≈{g0['fd_true']:.0f} Hz, 바이스태틱 거리 R_b≈{g0['Rb_true']:.1f} m.",
    "",
    "<sub>⚠ **σ 의 적용범위.** 이 값은 **모노스태틱 후방산란 등가**다 — 방위평균·대역평균·앙각 15° 기준이고 "
    "편파는 분리하지 않는다(스칼라 |Γ|). 즉 여기 설정이 바이스태틱인데도 표적 밝기는 모노스태틱 값을 "
    "그대로 쓴다(바이스태틱 일반형의 적용범위 한계 — 전방산란 σ≡0, 비볼록 표적 상반성 부분성립 — 는 "
    "report07 §5 에 기록돼 있다). 아래 결론은 **모드 간 상대 비교**라 σ 가 밴드 안에서 움직여도 불변이지만, "
    "절대 검지거리로 환산할 때는 이 한정이 함께 따라와야 한다.</sub>",
))
cells.append(gif("rx_array", "감시배열 Rx 1→4 증설",
                 f"감시 배열을 1→2→3→4 소자로 늘리는 모습(시각화용으로 간격 과장). 실제 λ/2={100*(3e8/M['fc'])/2:.1f} cm."))
cells.append(md(
    "**표적 에코 만들기.** 표적 메아리 = 송신 파형이 표적에 맞고(지연 τ) 되쏘며(도플러 f_d), 세기는 SBR σ "
    "로 정해진다. 파형과 지연 채널은 **Sionna PHY** 가 담당한다(검증됨, report05 NMSE −135 dB).",
    "",
    "지연 τ 의 **분수지연 sinc 커널을 Sionna `cir_to_time_channel` 이 생성**하고, 표적 에코는 이 커널로 "
    "만든다. 도플러·진폭은 위상램프로 얹는데, 고정지연·협대역에서 시변 채널과 동등하다. 해석식과의 상관 "
    f"**{CORR:.3f}** 로 **지연 연산자**를 교차검증한다(도플러·진폭은 양쪽이 같은 식이라 자명).",
    "",
    "> **ISAC 접점:** 통신 쪽(C)은 Sionna PHY 의 파형·지연 펄스정형이 담보하고, 센싱 쪽(S)의 표적 밝기 "
    "σ 는 Sionna 가 못 내므로(산란적분 부재, report06) SBR+PO 로 얹는다 — LAMBDA·3GPP 가 쓰는 "
    "'Sionna 전파 + 외부 RCS 주입'과 같은 아키텍처. ([[report06]][[report07]])",
))

# =========================================================================== #
#  §3. 9-모드 벤치마크 (헤드라인)
# =========================================================================== #
def _mode_row(c):
    w = MD[c]
    v = s50(c)
    drb = w["range_res_m"]                                # 바이스태틱 c/B (JSON 에 저장된 값)
    drm = drb / 2.0                                       # 모노스태틱 등가 c/2B
    return (f"| {c} | {SNAME[w['std']]} | {w['ref_name']} | {w['ref_bw_mhz']:.2f} MHz | "
            f"{drb:.1f} m | {drm:.1f} m | {'상시' if w['always_on'] else '세션/제어'} | "
            f"{('%.1f' % v) if v is not None else '—'} dB |")


tbl = ["# §3. 9-모드 벤치마크 — 어떤 신호가 드론을 잘 비추나", "",
       "3표준 각각의 **상시 → 제어/풀** 경로를 3단계로 잘라 9모드. 필요한 SNR(단일 Rx, 낮을수록 좋음):", "",
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
    "> **거리분해능 규약(정합성 확인, 결과 비교 아님):** 이 표의 $\\Delta R_b = c/B_{ref}$ 는 "
    "**바이스태틱** 거리분해능이다(바이스태틱 거리는 왕복이 아니므로 $c/2B$ 가 아니라 $c/B$ — report11 §2, "
    "그리고 Maksymiuk 외(Warsaw Univ. of Technology), *UAV Intrusion Detection with Passive Radar Based "
    "on the 5G Network* **식 (5) $\\Delta R_b = c/B$** 와 같은 규약). 모노스태틱 등가값은 이 절반이다. "
    "이 대조는 **정의가 어긋나 2배 오차가 나는 것을 막는 규약 점검**이지 성능 비교가 아니다. ⚠ 우리 "
    "$\\Delta R_b$ 는 공식 출력이지 RD 맵 메인로브 폭 실측이 아니다.",
    "",
    f"- **WiFi 는 상시라도 광대역**(프리앰블 {MD['W1']['ref_bw_mhz']:.1f} MHz) → 셋 다 거리분해능 "
    f"~{MD['W1']['range_res_m']:.1f} m 로 좋다. 데이터 점유(W1→W3)는 분해능을 거의 안 바꾼다"
    f"(프리앰블이 고정 기준이라).",
    f"- **5G 는 상시(G1=SSB)면 {MD['G1']['ref_bw_mhz']:.1f} MHz 로 병적으로 좁다**"
    f"($\\Delta R_b$ {MD['G1']['range_res_m']:.1f} m, 모노 등가 {MD['G1']['range_res_m'] / 2:.1f} m) — 진짜 "
    f"'5G 이중고'. 하지만 **G2·G3(NR-PRS)로 가면 {MD['G3']['ref_bw_mhz']:.0f} MHz** 전대역 → "
    f"$\\Delta R_b$ {MD['G3']['range_res_m']:.1f} m 로 급반전.",
    "- **LTE 는 L1=CRS(상시) → L2·L3=PRS(측위세션)** 로 기준신호가 바뀐다.",
    "",
    "> **9모드는 '표준 × 점유' 직교 요인설계가 아니다.** 점유 레벨이 표준 간 공통이 아니고"
    f"(상시 모드 점유율: " + " · ".join(f"{k} {v:.2f}%" for k, v in ON_OCC.items()) + "), 단계를 올릴 때 "
    "**기준신호 자체가 바뀐다**(LTE CRS→PRS, 5G SSB→NR-PRS; WiFi 만 셋 다 프리앰블). 즉 각 표준의 "
    "**상시→제어 경로를 나란히 놓은 것**이지 같은 점유 축 위의 요인 비교가 아니다.",
    "",
    f"> **SNR 축 정의.** 이 표·그림의 SNR 은 RD 맵에서 **무잡음 표적 피크 전력 ÷ 잡음셀 전력의 중앙값**이다"
    f"(`experiment_detection.py:224-233`). 셀 전력이 지수분포면 중앙값 = ln2 × 평균이므로, 같은 상황을 "
    f"**평균 기준**으로 재는 관례와는 {MEDIAN_REF_DB:.2f} dB 어긋난다(우리 축의 값이 그만큼 크게 매겨진다). "
    f"문헌의 검출문턱(D0)과 나란히 놓을 때는 이 오프셋을 먼저 환산해야 한다.",
    "",
    "> **실증(X410)은 어디에?** X410 은 후보 파형을 **직접 송신(제어)** 하므로 전대역 상시 = **풀 모드(G3/L3/"
    "W3)** 에 해당한다. 상시(G1/L1/W1)는 '비협조 조명원일 때의 하한선'으로 읽으면 된다.",
))

# =========================================================================== #
#  §4. 수신기 증설 — 코히어런트 배열 이득
# =========================================================================== #
cells.append(md(
    "# §4. 수신기를 늘리면 — 코히어런트 배열 이득 (이상적 상한)",
    "",
    f"감시 배열 N 소자를 표적 방향으로 위상 맞춰 더하면 표적 √N 배·잡음 그대로 → **출력 SNR N배"
    f"(+10log10 N dB)**. N={NMAX} 면 +{IDEAL_GAIN_DB:.2f} dB. (직관: 여러 사람이 같은 소리를 방향 맞춰 "
    f"함께 들으면 소리는 커지고 잡음은 그대로여서 더 또렷해진다.) 이는 **교과서적 배열이득이며, 여기서는 "
    f"이상적 상한**이다: **완벽 조향**(표적 방위를 정확히 앎)·**소자 간 등분산 독립잡음**·보정오차 0 을 "
    f"가정한다. 몬테카를로는 이 정합 빔포머와 동치인 형태로 √N 을 신호에 **주입**하고, 잡음쪽 전력보존(σ²)"
    f"만 독립 실측한다. 실측 X410 은 조향 불일치·상호결합·동기오차로 **이 상한 이하**다.",
))
cells.append(gif("rd_rxbuildup_nr", "Rx 증설 RD 맵(5G 풀)",
                 "거리-도플러 지도. 수신기 1→4 로 표적(흰 네모)이 잡음 위로 떠오른다. 0-도플러 세로 능선은 "
                 "직접파 잔차(가드로 제외)."))
cells.append(md("빔패턴도 N 으로 날카로워진다:"))
cells.append(gif("beampattern", "배열 빔패턴",
                 "감시 ULA 빔패턴이 N=1→4 로 좁아진다(표적 방위로 조향, 점선)."))
cells.append(md("**검출확률 곡선(풀 모드).** 수신기를 늘릴수록 곡선이 왼쪽으로(더 약한 표적도 탐지) 이동:"))
cells.append(fig("report12_pd_curves", "Pd vs SNR, N=1..4, 풀 모드"))
cells.append(gif("pd_build_nr", "Pd 곡선 그려짐", "N=1→4 순으로 그려가는 애니(5G 풀)."))
# SNR50 이득 표 (풀 모드)
gtbl = [f"**필요 SNR(SNR50)과 수신기 증설 이득 — 풀 모드:**", "",
        f"| 모드 | N=1 | N=2 | N=3 | N={NMAX} | N={NMAX} 이득 | 이론 상한 |",
        "|---|---|---|---|---|---|---|"]
for c in FULL:
    vals = [s50(c, N) for N in M["n_list"]]
    g4 = gain4(c)
    gtbl.append(f"| {c} ({SNAME[MD[c]['std']]}) | " +
                " | ".join(f"{v:.1f}" if v is not None else "—" for v in vals) +
                f" | **−{g4:.2f} dB** | −{IDEAL_GAIN_DB:.2f} dB |")
gtbl += ["",
         f"⚠ **이 열은 측정된 배열이득이 아니다.** 몬테카를로는 감시 소자를 개별 합성하지 않고 표적 에코 "
         f"진폭에 √N 을 곱한다(`experiment_detection.py:270`: `surv = sqrtN*echo + dpi + noise`). 따라서 "
         f"이 표가 말하는 것은 '주입한 가정이 검출 체인을 통과해 얼마나 되돌아오나'이지 배열 물리의 측정이 "
         f"아니다.",
         "",
         f"그리고 되돌아온 값이 상한을 넘는다 — 9모드 중 **{N_EXCEED}개가 이론 상한 "
         f"10log10 N = {IDEAL_GAIN_DB:.2f} dB 를 0.05 dB 넘게 초과**하며 최대는 {EXC_C} 의 "
         f"+{EXC_MAX:.2f} dB 다. 같은 "
         f"식에서 직접파 잔차 `dpi` 는 N 과 무관하게 고정이고 x축 SNR 은 잡음만으로 정의되므로(§3 'SNR 축 "
         f"정의'), 표적 대 DPI 잔차 비가 √N 만큼 함께 좋아지는 몫이 이득에 얹힌다 — 초과분의 유력한 원인 "
         f"후보다. 다만 **DPI 를 끈 대조 실행으로 확정하기 전까지는 원인 미규명**으로 남긴다. 이 표의 값은 "
         f"**설계 상한**으로 읽어야 하고, 배열이득이 조명원 종류와 무관한 순수 배열 물리라고는 "
         f"(상한 대비 편차가 모드마다 {_pm(min(EXCESS.values()))}~{_pm(EXC_MAX)} dB 로 갈리므로) "
         f"아직 말할 수 없다."]
cells.append(md(*gtbl))
cells.append(fig("report12_snr50_vs_n", "감도 이득 vs 수신기 수"))

# =========================================================================== #
#  §5. 몬테카를로 · Pfa — 얼마나 믿나 (검증)
# =========================================================================== #
cells.append(md(
    "# §5. 몬테카를로 · Pfa — 얼마나 믿나 (검증)",
    "",
    f"Pd 는 확률이라 잡음을 **{K:,}번** 새로 뽑아(각 SNR·N·모드마다) 추정한다. 이 Pd 곡선은 **§6 에서 "
    "pyAPRiL 로 정확성을 검증한 그 표준 체인(ECA→거리도플러→CFAR)** 을, GPU 구현(`detection_gpu.py`)으로 "
    "대량 반복해 얻은 것이다 — pyAPRiL 자체가 Pd 곡선을 낸 것이 아니다. GPU 에 수십 트라이얼을 "
    "**배치로 한꺼번에** 올려(torch) 빠르게 반복한다(배치를 키우면 GPU 메모리를 많이 쓴다).",
))
cells.append(gif("mc_converge_nr", "몬테카를로 수렴", "시행수↑ 로 Pd 추정·95% 신뢰구간이 좁아진다."))
cells.append(md(
    "**오경보율 — 정직하게(적대적 검증 반영).** report10 의 **파형(std)별** Pfa 교정을 적용했다. 하지만 "
    f"이 교정은 표준별로만 되어 있어(점유/기준신호별 아님), 특히 **5G 상시(G1=SSB "
    f"{MD['G1']['ref_bw_mhz']:.1f} MHz)** 처럼 대역이 아주 좁은 모드는 완전히 교정되지 않는다. 표적 없는 "
    f"트라이얼로 잰 **경험적 Pfa 는 모드마다 다르고 목표 10⁻⁴ 와 정확히 같지 않다**"
    f"(목표 대비 {PFA_RATIO_MIN:.2f}~{PFA_RATIO_MAX:.2f}배 — 최저 {PFA_LO_C}, 최고 {PFA_HI_C}). "
    f"CA-CFAR 문턱은 $\\alpha = N_{{tr}}(P_{{fa}}^{{-1/N_{{tr}}}}-1)$ 이므로(내부 셀 $N_{{tr}}$={NTR}), "
    f"이 불균일은 두 극단 모드 사이 **{PFA_TH_SPREAD_DB:.2f} dB 의 문턱 차**로 환산된다 — 즉 §3 의 모드 간 "
    f"SNR50 차이 중 그만큼은 물리가 아니라 **교정 잔차**다. 따라서 **{PFA_TH_SPREAD_DB:.1f} dB 규모의 "
    f"차이는 이 한계를 감안해 읽어야 한다**. 반면 9모드 SNR50 스팬은 {SPAN50:.2f} dB"
    f"({S50_WORST} vs {S50_BEST})로 그보다 훨씬 크고, 그 몫은 대역폭 물리가 지배하므로 견고하다. "
    "완전한 공정 비교는 각 모드의 **경험적 Pfa 축에 ROC 를 그려** 맞춰야 하며, 이는 향후 과제다.",
))
cells.append(fig("report12_pfa", "경험적 Pfa (9모드) — 목표 10⁻⁴ 대비 (완전 균일 아님)"))

# =========================================================================== #
#  §6. 선행 연구 속 위치 — 그리고 검증된 라이브러리 결합
# =========================================================================== #
cells.append(md(
    "# §6. 선행 연구 속 위치 — 그리고 검증된 라이브러리 결합",
    "",
    "패시브 레이더 드론탐지 논문 21편(WiFi·LTE·5G)을 정독해 보면, 이 프로젝트가 채우는 빈틈이 분명하다 "
    "(정직하게: 아래는 '아무도 정확히 이렇게 하지 않았다'는 뜻이지, 각 조각이 세계 최초라는 뜻은 아니다):",
    "",
    "| 문헌의 빈틈 | 문헌 현황 | 이 프로젝트 |",
    "|---|---|---|",
    "| **조명원 간 공정 비교** | 조사한 21편은 **모두 단일 조명원**(5G만/LTE만/WiFi만). 표준 간 head-to-head 없음 | 9모드 W/L/G 공통 프로토콜 |",
    "| **표적 RCS 를 실제로 모델** | **이 21편 안에서는** 드론 RCS 를 계산한 편이 없다 — 외생 스칼라/Swerling 가정(−10~−13 dBsm). ⚠ 패시브 드론탐지 밖에는 있다(LAMBDA=CADFEKO, Ziganshin=UTD, BVH SBR+PO) | SBR+PO, NACA-4 익형 프롭, 재질별 \\|Γ\\| |",
    "| **점유율→Pd (고정 Pfa)** | LaSen 이 최선이나 monostatic·RMSE 채점 | G1/G2/G3 = SSB/PRS/CRS, '5G 이중고' 정량화 |",
    f"| **다중 Rx 이득 곡선** | 다소자 감시 배열 실측은 이미 있다(LIPASE: 감시 ULA 중앙 8소자 활성 + 기준 4소자 = 12안테나 디지털 빔포밍). 조사 범위에서 없는 것은 **소자 수 N 에 대한 이득 곡선** | N=1→{NMAX} 곡선 {GAIN_LO:.1f}~{GAIN_HI:.1f} dB. ⚠ √N **해석 주입**이라 실측이 아니라 **설계 상한**(§4) |",
    f"| **통제·재현** | 조사 범위에서는 1회성 야외이고 신뢰구간·공개데이터가 없다 | 반무향 챔버 + K={K:,} MC + 재생성 파이프라인 |",
    "| **정직한 결함 기록** | **명목-vs-경험 Pfa 교정 곡선**을 잰 선행이 조사 범위에 없다(LTE450 실측은 참조셀의 99% 경험분위수를 문턱으로 쓴다 — report10 §3) | 경험적 Pfa 불균일을 **결함으로 기록**(§5) |",
    "",
    "<sub>⚠ **과장하지 않기**: 'SSB 가 상시신호'라는 관찰은 이미 문헌에 있다(예: Jopanya & Osorio, "
    "SPAWC 2025 · arXiv:2504.02641 — 5G NR SSB 패시브 바이스태틱 드론) — 우리 기여가 아니다. 우리 RCS 절대값"
    f"(방위평균 **{AZAVG_35:.1f} dBsm**@3.5 GHz — 위 §2 의 이 자세값 {M['sigma_dbsm']:.1f} dBsm 은 **널이라 아래쪽 끝**이니 구분)도 새 측정이 아니다 — "
    "크기가 맞는 짝끼리 aspect-peak ↔ aspect-peak 으로 문헌 실측과 견주면 **우리 쪽이 위로 치우친다**"
    "(few-λ 공진영역에서 PO 가 절대레벨을 낙관적으로 잡을 소지; 정량치·짝짓기 규약은 report08 §6). "
    "⚠ '소형드론 방위평균 포락선 −28~−16 dBsm' 은 문헌이 보고한 값이 아니라 우리가 유도한 2차 산물이라 "
    "판정 근거로 쓰지 않는다. **다행히 헤드라인(5G 이중고·모드 비교)은 상대 결론이라 σ 가 밴드 내에서 움직여도 불변**이다. "
    "이 프로젝트의 성격은 **통제된 재현가능 벤치마크 + 정직한 결함 노출**이다.</sub>",
))
cells.append(md(
    "**뼈대는 주류 ISAC 아키텍처다.** 위 층별 구조(σ 외부 주입 + 표적/배경 채널 분리 + 표준 검출 체인)가 "
    "**선행의 주류**임을 확인했다(근거·출처: `prior_work/` pw01~03, `OPENSOURCE.md`):",
    "",
    "| 구성 요소 | 같은 구조의 주류 선행 | 판정 |",
    "|---|---|---|",
    "| 표적/배경 채널 분리 `h = h_bg + h_target` | **NIST 5GNRad**·**3GPP Rel-19 ISAC**(오픈 MATLAB Putirf, arXiv:2606.07328)·**LAMBDA**(arXiv:2607.03826) | 동일 |",
    "| 표적 밝기를 외부 σ 로 주입 | NIST 5GNRad·MATLAB·LAMBDA(CADFEKO) | 동일 |",
    "| 환경 전파를 Sionna RT 로 담보 | Deterministic-Modeling(EuCAP 2026, arXiv:2603.28736)·SimART | 동일 |",
    "| 검출 체인 ECA/CAF/CFAR | Wypich & Zielinski(Sensors 2026, USRP — **표적은 차량**, 원문 미확보)·"
    "Demissie 외(2024 International Radar Conference (RADAR), 표적 UAV — 원문 확인) | 골격은 같다"
    "(문턱 규칙은 논문마다 다르다 — report10 §3) |",
    "| σ 를 확산계수 가정 대신 **드론 메쉬에서 SBR+PO 로 산출** | 대개 확산 S(Great-X, arXiv:2507.08716) 또는 점산란체 | **차이(강화)** |",
    "",
    "즉 뼈대는 **NIST 5GNRad·3GPP·LAMBDA 와 같은 주류 ISAC 아키텍처**다. 덜 점유된 틈새는 세 결합 — "
    "①상용 신호(WiFi/LTE/5G) **패시브 바이스태틱**(선행은 대개 능동/모노 또는 CSI 기반), ②드론 RCS 를 "
    "**SBR+PO 로 산출**(확산 S 가정 아님), ③**상시 vs 세션 9모드** 벤치마크.",
    "",
    "> 🔧 **선행 방식·오픈소스로 검증(계층별, 전체 지도 `OPENSOURCE.md`·`prior_work/pw02`):**",
    f"> - **검출 체인 → pyAPRiL**(GPLv3, DVB-T/FM 실측 검증된 패시브 레이더 라이브러리). ECA/CAF/CFAR 는 "
    f"**파형 무관**(reference I/Q 만 사용)이라 WiFi/LTE/5G 에 그대로 적합하다. 실제로 pyAPRiL 을 돌려 "
    f"**NR/WiFi/LTE 3모드 모두 RD 맵 최강 봉우리의 거리빈이 정답과 일치**하고 **CA-CFAR 이 "
    f"정답 거리셀에서 발화**(모드당 5셀)함을 확인했다(`benchmark/verify_pyapril.py`). "
    f"⚠ 단 §3~§5 의 **대량 몬테카를로 Pd 곡선은 pyAPRiL 이 아니라 GPU 구현(`detection_gpu.py`)**이 낸 "
    f"것이다 — pyAPRiL 은 그 **표준 체인의 정확성을 검증**하고, Pd 곡선은 검증된 그 체인을 K={K:,}회 "
    "GPU 로 대량 반복한 결과다.",
    "> - **RCS → 자작 SBR+PO**(선행 BVH SBR+PO arXiv:2604.09243 과 같은 계열; 상용 CADFEKO·비공개 "
    "RadarSimPy 불채택), 절대값은 **실측 문헌 드론 RCS 로 앵커**(report08). **추적 → Stone Soup**, "
    "**실측 → OpenISAC+GNU Radio+X410**.",
    "> - **파형·지연채널 → Sionna PHY**(report05, NMSE −135 dB). **아키텍처**(h=h_bg+h_target)는 "
    "**NIST 5GNRad·3GPP Rel-19**(오픈 구현 Putirf)와 동일.",
    "",
    "> **실증(USRP X410)으로의 연결**: X410(TX4·RX4·400 MHz·12-bit)은 후보 파형을 **직접 송신**하므로 "
    "위 9모드를 통제 재현할 수 있고, 다중 RX 채널로 이 리포트의 Rx 이득을 실측 검증하는 자연스러운 "
    "테스트베드다. 단 시뮬(통제 챔버)↔실측(외부)은 환경이 1:1 이 아니라 **구조**(바이스태틱·기준+감시·"
    "같은 파형·디텍션 체인)만 같다.",
))

# =========================================================================== #
#  §7. 결론
# =========================================================================== #
cells.append(md(
    "# §7. 결론 — 탐지는 된다, 추적은 다음 일",
    "",
    "1. **탐지가 된다.** 9모드 모두 충분한 SNR 에서 드론을 잡는다(Pd→1.0).",
    "2. **조명원이 중요하다.** 상시라면 WiFi(광대역)가 유리, 5G(SSB)는 불리 — 단 PRS·제어면 5G 도 전대역. "
    "실증(X410 제어)은 풀 모드에 해당.",
    f"3. **수신기를 늘리면 감도가 오른다 — 설계 상한으로.** Rx 1→{NMAX} 로 필요한 SNR 이 5G 풀 기준 "
    f"**{NR_G4:.2f} dB** 낮아진다(이론 상한 {IDEAL_GAIN_DB:.2f} dB). 단 이 이득은 코드가 √N 을 주입한 "
    f"결과이지 소자별 합성의 측정이 아니고, 9모드 중 {N_EXCEED}개는 그 상한을 0.05 dB 넘게 초과한다(§4).",
    "4. **정직성.** 에코 지연은 Sionna `cir_to_time_channel`(상관 "
    f"{CORR:.3f} 는 지연만 검증), 배열이득은 이상적 상한(√N 주입·잡음보존만 실측 {CRAT:.3f}, 상한 초과분 "
    f"원인 미규명), Pfa 는 std별 명목 교정(모드 간 불균일 = 문턱 차 {PFA_TH_SPREAD_DB:.2f} dB). "
    "모두 리포트에 명시했다.",
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
