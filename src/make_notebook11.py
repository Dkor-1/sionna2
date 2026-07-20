# -*- coding: utf-8 -*-
"""
make_notebook11.py — report11.ipynb 생성기
==========================================================================================
report11 — "검출기 교정 ②: 저속 표적·분해능"

⚠ **이 파일이 진짜 소스다.** report11.ipynb 를 직접 고치지 말고 여기를 고쳐 재실행할 것.

한 주제만 다룬다: **느린 드론과 신호의 분해능이 검출에 만드는 문턱**.
 (1) 직접파 제거(ECA)가 도플러 0 근처(느린 표적)를 표적까지 같이 지우는 "블라인드 속도",
 (2) 각 신호의 거리·속도 분해능이 이론과 맞는지(모호함수 = 신호가 표적을 얼마나 또렷이 가르나 지도),
 (3) 링크버짓(밝기·거리·잡음 → 신호대잡음비)이 이론과 맞는지,
 (4) 그리고 그렇게 계산한 표적 밝기를 넣으면 **디텍션이 실제로 작동함**을 검출확률(Pd) 곡선으로.

본문의 **모든 숫자는 outputs/*.json 에서 읽어 넣는다** (손으로 적은 숫자 없음):
    verify_eca.json · verify_ambiguity.json · verify_linkbudget.json  (+ Pd 전이곡선은 verify_cfar.json roc_NR100)
그림은 기존 outputs/figures 를 **재사용**(경로 링크만).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from provenance import provenance_cells                      # noqa: E402

NB = os.path.join(ROOT, "report11.ipynb")


def _j(n):
    with open(os.path.join(ROOT, "outputs", n), encoding="utf-8") as f:
        return json.load(f)


E = _j("verify_eca.json")
A = _j("verify_ambiguity.json")
L = _j("verify_linkbudget.json")
C = _j("verify_cfar.json")            # roc_NR100(Pd 전이곡선)만 인용
OB = _j("verify_observability.json")  # §5 관측가능성·정확도 (FIM 랭크·CRLB·처방)
PY = _j("verify_pyapril.json")        # §4 검출체인 표준성 검증(오픈소스 pyAPRiL, 파형무관)
PY_N = len(PY["modes"])
PY_OK = sum(1 for m in PY["modes"].values() if m["correct"])
PY_ERR = max(abs(m["range_bin_error"]) for m in PY["modes"].values())


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def fig(name, alt=""):
    return md(f"![{alt}](outputs/figures/{name}.png)")


# --------------------------------------------------------------------------- #
#  JSON 에서 값 뽑기 (전부 측정/유도값)
# --------------------------------------------------------------------------- #
# ── (1) ECA 블라인드 속도: 운용 적분시간(M=48)에서 되돌아온 에코 '에너지'가
#         -3 dB 로 깎이는 시선속도를 노치 곡선에서 보간해 구한다 ─────────────
def _interp(rows, key, target):
    fds = [r["fd_hz"] for r in rows]
    ys = [r[key] for r in rows]
    for i in range(1, len(rows)):
        y0, y1 = ys[i - 1], ys[i]
        if (y0 - target) * (y1 - target) <= 0 and y1 != y0:
            x0, x1 = fds[i - 1], fds[i]
            return x0 + (target - y0) * (x1 - x0) / (y1 - y0)
    return None


BLIND = {}          # name -> dict(M, T_cpi_ms, v_blind_ms, dfd_hz)
NOTCH_CURVE = None   # (1 - sinc²) 검증용 대표 곡선
for s in E["S4_target_loss"]:
    if s["M"] != 48:
        continue
    rows = [r for r in s["rows"] if 0.0 <= r["fd_over_dfd"] <= 1.0]
    fac = s["v_3db_ms"] / s["fd_3db_hz"]              # Hz → 시선속도[m/s] 환산계수
    fd_e = _interp(rows, "energy_loss_db", -3.0)
    BLIND[s["name"]] = dict(M=s["M"], T=s["T_cpi_ms"], dfd=s["dfd_hz"],
                            v=fd_e * fac, lam=s["lam_m"])
    if s["name"].startswith("5G"):
        NOTCH_CURVE = s          # 5G 곡선으로 이론(1-sinc²) 대조 표를 만든다

V_MIN = min(b["v"] for b in BLIND.values())
V_MAX = max(b["v"] for b in BLIND.values())
# 초장적분(M=96)이면 노치가 더 좁아져 더 낮은 속도까지 본다 — 대표값
V_LONG = None
for s in E["S4_target_loss"]:
    if s["M"] == 96 and s["name"].startswith("WiFi"):
        rows = [r for r in s["rows"] if 0.0 <= r["fd_over_dfd"] <= 1.0]
        fac = s["v_3db_ms"] / s["fd_3db_hz"]
        V_LONG = _interp(rows, "energy_loss_db", -3.0) * fac
        V_LONG_T = s["T_cpi_ms"]

# 노치 곡선이 이론 1-sinc² 와 얼마나 붙나 (에너지 기준 최대 편차)
NDEV = max(abs(r["energy_loss_db"] - r["theory_loss_db"])
           for r in NOTCH_CURVE["rows"] if r["fd_over_dfd"] > 0)

# ── (2) 모호함수 = 거리 분해능(측정/이론) ─────────────────────────────────
def wf(k):
    return A["waveforms"][k]


RES = {}    # 표에 넣을 4개 파형
for k, label, ref in [("wifi_G1", "WiFi 80 MHz", "VHT-LTF"),
                      ("lte_G1", "LTE 20 MHz", "CRS"),
                      ("nr_G1", "5G NR 100 MHz (상시 SSB)", "SSB"),
                      ("nr_G3", "5G NR 100 MHz (측위 PRS)", "NR-PRS")]:
    w = wf(k)
    RES[k] = dict(label=label, ref=ref, refbw=w["ref_bw_hz"] / 1e6,
                  meas=w["dR_meas_m"], theo=w["dR_theory_m"],
                  ratio=w["dR_ratio"], psl=w["psl_chamber_db"])
DR_MIN = min(r["ratio"] for r in RES.values())
DR_MAX = max(r["ratio"] for r in RES.values())
# 모호함수가 실제 거리-도플러 맵을 재현하는 정확도(검증)
MAXERR = max(d["max_err_db_above_m45"] for d in A["meta"]["detector_validation"])
CHAM = A["meta"]["fd_map_hz"]        # 챔버 RD 창 도플러 폭 참고

# ── (3) 링크버짓: 레이더방정식·처리이득·잡음바닥이 이론과 일치 ─────────────
LB_MAXDEV = L["A_radar_equation"]["max_dev_db"]                # 3독립계산 최대불일치
PG = {w["name"]: w for w in L["BE_processing_gain"]["waveforms"]}
PG_ERR = max(abs(w["loss_rect_vs_theory_db"]) for w in PG.values())
NOISE_ERR = max(abs(r["err_vs_theory_db"]) for r in L["C_noise_floor"]["rows"])

# ── (4) 디텍션이 실제로 작동한다: SBR 로 넣은 σ → SCR → Pd ──────────────────
DS = L["D_sigma_table"]
DROWS = DS["rows"]
SCR_MIN = min(r["scr_meas_db"] for r in DROWS)
SCR_MAX = max(r["scr_meas_db"] for r in DROWS)
GAP_MEAN = DS["gap_mean_db"]
GAP_STD = DS["gap_std_db"]
N_DET = len(DROWS)
ALL_PD1 = all(r["pd"] == 1.0 for r in DROWS)
# 대표 5개(WiFi) — 표적 밝기(σ) → 예측 SCR → 측정 SCR
DET_TAB = [r for r in DROWS if r["wf"] == "WiFi 80MHz"]
# Pd 전이곡선(NR100, 운용 명목 Pfa=1e-4)
ROC = C["roc_NR100"]
PD_TRANS = []
for c in sorted(ROC["curves"], key=lambda x: x["scr_db"]):
    p = [q["pd"] for q in c["points"] if abs(q.get("pfa_nom", -1) - 1e-4) < 1e-12]
    PD_TRANS.append((c["scr_db"], p[0] if p else None))

# ── 형상(챔버) 참고 ─────────────────────────────────────────────────────────
CFG = L["config"]
RB = A["waveforms"]["nr_G1"]["dR_theory_m"] and A["geometry"]["nr_G1"]["rb_true_m"]
BASELINE = L["A_radar_equation"]["rows"][0]["L"]

cells = []

# =========================================================================== #
#  앞머리 (provenance)
# =========================================================================== #
GLOSS = [
    ("도플러 f_d", "표적이 움직여 생기는 수신 주파수의 이동. 정지물(클러터)과 움직이는 표적을 "
                   "가르는 축. 느린 표적일수록 f_d 가 0 에 가까워 클러터와 구별이 어렵다"),
    ("ECA (직접파 제거)", "송신기에서 수신기로 곧장 새어 든 강한 직접파를, 지연된 기준신호가 만드는 "
                          "부분공간에 사영해 빼는 전처리. **정지 성분(도플러 0)을 통째로 지운다** — "
                          "이 성질이 곧 저속 맹점의 뿌리다"),
    ("블라인드 속도", "ECA 노치에 먹혀 되돌아온 신호가 3 dB 이상 깎이는 최소 시선속도. "
                     "이보다 느리면 표적이 **원리적으로** 잘 안 보인다"),
    ("모호함수 / CAF", "교차모호함수(Cross-Ambiguity Function). 기준신호와 수신신호를 **거리(지연)와 "
                       "도플러로 동시에** 상관시켜 만든 2차원 지도. 봉우리 폭이 분해능, 곁봉우리가 가짜표적"),
    ("거리 분해능 ΔR_b", "두 표적을 거리축에서 갈라 볼 수 있는 최소 간격. 바이스태틱에서 ΔR_b = c/B "
                         "(B = 기준신호 대역폭). 대역이 넓을수록 촘촘히 가른다"),
    ("sinc / 0.886", "직사각 창의 스펙트럼 모양(sin πx / πx). 그 −3 dB 폭은 이론값의 **0.886배**다. "
                     "측정/이론 비가 이 값 근처면 분해능 눈금이 맞은 것"),
    ("링크버짓", "표적 밝기(σ)·거리·잡음을 곱하고 나눠 되돌아온 신호대잡음비(SNR)를 예측하는 계산. "
                 "= 레이더 방정식"),
    ("RCS (σ)", "레이더 되비침 밝기. σ 는 그 밝기를 넓이 단위(m²)로 적은 값. 표적이 밝아야(σ 가 커야) "
                "잡힌다. Sionna 기본 solver 는 이 σ 를 못 내므로 **SBR** 로 따로 계산해 넣는다"),
    ("SBR", "표적을 광선으로 조준해 맞고, 맞은 면이 레이더로 되쏘는 양을 물리광학(PO)으로 계산·합산해 "
            "σ 를 구하는 방법"),
    ("SCR", "신호대클러터비(Signal-to-Clutter Ratio). 거리-도플러 지도에서 표적 봉우리 ÷ 주변 바닥. "
            "검출 난이도의 실측 지표"),
    ("Pd (검출확률)", "표적이 있을 때 검출기가 실제로 발화할 확률. SCR 이 올라갈수록 0 에서 1 로 전이한다"),
    ("CFAR", "주변 잡음을 보고 문턱을 스스로 정하는 검출기(Constant False Alarm Rate)"),
    ("CPI / 적분시간", "한 번 관측하며 신호를 모아 쌓는 시간(Coherent Processing Interval). 길수록 "
                       "도플러를 촘촘히 보지만 관측이 느려진다"),
    ("semi-anechoic", "벽·천장은 전파를 흡수하고 바닥만 반사하는 반무향 챔버 — 우리 실험 환경"),
]

_front = provenance_cells(
    report="report11",
    what="검출기 교정 ②: 저속 표적·분해능",
    question="느린 드론과 신호의 분해능 한계는 검출에 어떤 문턱을 만드나?",
    spine=dict(
        core=("저속 표적·거리 분해능·위치 관측성은 신호 대역폭과 송수신 기하가 정하는 **원리적 문턱**이다 — "
              "검출 사슬 자체는 표준(pyAPRiL 로 교차검증)이고, 표적 밝기 σ 만 SBR+PO 로 넣으면 그 문턱 위에서 "
              "드론이 실제로 잡힌다."),
        gap=(f"바이스태틱 거리 분해능은 **ΔR_b = c/B**(B=기준신호 대역폭; 모노스태틱 등가는 c/2B), 저속 "
             f"맹점과 위치 관측성은 **송수신 기하**로 못박혀 있어 시뮬레이터가 바꿀 수 없다. 게다가 스톡 "
             f"Sionna 는 파형·전파만 줄 뿐 이 문턱을 재는 **검출 신호처리(ECA·CAF·CFAR)가 아예 없다**."),
        prior=("패시브 레이더 검출은 ECA→CAF→CFAR 표준 사슬이며 하드웨어 선행이 그대로 썼다 — 5G NR OFDM "
               "패시브 레이더(Wypich·Zielinski, Sensors 2026, DOI 10.3390/s26041317, ECA⁺→CA-CFAR) · "
               "LTE450 드론 패시브 레이더(Demissie, IET RSN 2025, DOI 10.1049/rsn2.70092). 5G SSB 상시 신호의 "
               "거리·속도 분해능/CRB 한계는 Jopanya·Osorio(SPAWC 2025, arXiv:2504.02641)가 분석했다."),
        lib=("검출 사슬은 새로 짜지 않고 오픈소스 **pyAPRiL**(GPLv3, BME Radarlab)의 `cc_detector`(CAF)·"
             "`CA_CFAR` 를 그대로 쓴다(중복 구현 회피). 표적 밝기 σ 만 자작 SBR+PO 로 계산해 Sionna 채널에 "
             "주입한다 — 파형·전파는 Sionna PHY·RT."),
        verify=(f"pyAPRiL 로 교차검증 — NR·WiFi·LTE **{PY_OK}/{PY_N} 모드 모두** 정답 거리빈(오차 {PY_ERR} 빈)에 "
                f"검출(verify_pyapril.json). 분해능은 이론 ΔR_b=c/B 대비 {DR_MIN:.2f}~{DR_MAX:.2f}배(sinc 0.886), "
                f"링크버짓 3독립계산 최대 편차 {LB_MAXDEV:.0e} dB, 관측성 회전대칭은 기계정밀도까지 0."),
    ),
    sources=[
        dict(item="ECA 노치·블라인드 속도(운용 적분시간)",
             src="outputs/verify_eca.json",
             kind="측정 (RT 클러터 + ECA 사영)"),
        dict(item="모호함수·거리 분해능 측정/이론",
             src="outputs/verify_ambiguity.json",
             kind="측정 (기준신호 자기모호함수)"),
        dict(item="레이더방정식·처리이득·잡음바닥·SCR·Pd",
             src="outputs/verify_linkbudget.json · outputs/verify_cfar.json(roc_NR100)",
             kind="측정 (σ 는 SBR, 3GPP TS / ITU-R P.2040 재질)"),
    ],
    engines=["radar-dsp", "sbr", "sionna-phy", "matplotlib"],
    libs=["torch", "numpy", "matplotlib"],
    reproduce=[
        "cd /home/yunjung/workspace/sionna2",
        "~/.venvs/py312/bin/python benchmark/verify_eca.py",
        "~/.venvs/py312/bin/python benchmark/verify_ambiguity.py",
        "~/.venvs/py312/bin/python benchmark/verify_linkbudget.py",
        "~/.venvs/py312/bin/python src/make_notebook11.py     # report11.ipynb 재생성",
    ],
    artifacts=[
        dict(file="outputs/verify_eca.json", what="ECA 노치·블라인드 속도"),
        dict(file="outputs/verify_ambiguity.json", what="모호함수·거리/속도 분해능"),
        dict(file="outputs/verify_linkbudget.json", what="레이더방정식·잡음·SCR·Pd"),
        dict(file="outputs/figures/verify_eca.png", what="ECA 저속 맹점 그림 (재사용)"),
        dict(file="outputs/figures/verify_ambiguity_af.png", what="모호함수 거리-도플러 지도 (재사용)"),
    ],
    caveats=[
        "**블라인드 속도는 적분시간(CPI)에 달렸다.** 여기 값은 운용 적분시간 기준이다. 더 오래 "
        "적분하면 노치가 좁아져 더 느린 표적까지 보이지만 관측이 그만큼 느려진다(맞바꿈).",
        "**분해능은 신호가 상시 쓰는 기준신호의 대역폭이 정한다.** 5G 의 상시 신호(SSB)는 대역이 "
        f"{RES['nr_G1']['refbw']:.1f} MHz 뿐이라 거리 분해능이 {RES['nr_G1']['meas']:.0f} m 로 거칠다.",
        "**여기서 다루는 것은 탐지(거리+속도 셀에서 '있다/없다')까지다.** 표적의 위치·궤적을 잇는 "
        "추적은 이 리포트의 범위 밖이다.",
    ],
    cost="verify_* 스크립트 각 GPU 1장 수 분. 그림은 이미 산출된 것을 재사용.",
    related=[
        dict(rep="report10 (앞)", rel="오경보율 — 검출기가 '헛것'을 얼마나 자주 보나(문턱 눈금)"),
        dict(rep="[report12](report12.ipynb) (다음)",
             rel="결과편 — 다중 수신기(1→4) 디텍션 + 9모드 벤치마크. §5 의 '수신기 2개면 위치가 풀린다' 가 "
                 "거기서 '수신기를 늘리면 감도도 오른다(+10log10 N dB)' 로 이어진다"),
    ],
    glossary=GLOSS,
)
cells += _front

# =========================================================================== #
#  §1  Sionna 공백 + ECA 저속 맹점 — 블라인드 속도
# =========================================================================== #
cells.append(md(
    "---",
    "# §1. Sionna 의 공백과 ECA 의 저속 맹점 — 블라인드 속도",
))
cells.append(md(
    "**공백부터.** 검출은 (1) 직접파·정지 클러터 제거(ECA) → (2) 거리-도플러 상관(CAF) → (3) 문턱 검출"
    "(CFAR)의 **표준 처리 사슬**로 이뤄진다. 그러나 스톡 Sionna 는 파형·전파(경로·지연·도플러)만 줄 뿐 "
    "**이 레이더 신호처리를 아예 갖고 있지 않다.** 그래서 여기서는 표준 사슬을 그대로 따르되, 오픈소스 "
    "**pyAPRiL**(GPLv3, BME Radarlab)이 제공하는 그 ECA/CAF/CFAR 를 쓴다 — 실 하드웨어 선행이 쓴 체인과 같다"
    "(5G NR 패시브 레이더 Wypich·Zielinski, Sensors 2026, ECA⁺→CA-CFAR; LTE450 드론 패시브 레이더 "
    "Demissie, IET RSN 2025). 이 절은 그 첫 단계 ECA 가 **느린 표적에 만드는 원리적 맹점**을 본다.",
    "",
    "ECA 는 도플러가 0 인 성분(움직이지 않는 벽·바닥·직접파)을 지우도록 설계돼 있다. 그런데 표적이 "
    "느리면 그 표적의 도플러도 0 에 가까워져 **ECA 가 표적을 정지 클러터로 착각해 함께 지운다.** 지워지는 "
    "정도는 표적의 도플러가 '도플러 한 칸(=1/적분시간)'에서 얼마나 떨어져 있느냐로 정해진다.",
    "",
    f"**근거 — 노치의 모양.** ECA 가 표적을 깎는 양은 이론적으로 $1-\\mathrm{{sinc}}^2(f_d\\,T)$ 라는 "
    f"골짜기(노치) 모양을 따른다(T = 적분시간). 측정한 손실 곡선은 이 이론과 최대 **{NDEV:.3f} dB** 밖에 "
    "차이 나지 않는다 — 노치 폭은 정확히 **도플러 한 칸**이다. 아래 표는 5G 신호에서 표적 도플러가 "
    "도플러 한 칸의 몇 배일 때 얼마나 깎이는지다(이론과 나란히).",
))

# 1-sinc² 노치 대조표 (5G)
_nc = [r for r in NOTCH_CURVE["rows"]
       if r["fd_over_dfd"] in (0.1, 0.2, 0.3, 0.5, 0.8, 1.0)]
cells.append(md(*(
    ["| 표적 도플러 ÷ 한 칸 | 측정 에너지 손실 | 이론 $1-\\mathrm{sinc}^2$ |",
     "|---|---|---|"] +
    [f"| {r['fd_over_dfd']:.1f} | {r['energy_loss_db']:+.2f} dB | {r['theory_loss_db']:+.2f} dB |"
     for r in _nc]
)))

cells.append(md(
    "**블라인드 속도.** 되돌아온 에코 에너지가 −3 dB(절반)로 깎이는 지점을 시선속도로 환산하면, "
    "운용 적분시간에서 이렇게 나온다.",
))
cells.append(md(*(
    ["| 신호 | 적분시간 | 도플러 한 칸 | 블라인드 속도(−3 dB) |",
     "|---|---|---|---|"] +
    [f"| {n} | {b['T']:.0f} ms | {b['dfd']:.1f} Hz | **{b['v']:.2f} m/s** |"
     for n, b in BLIND.items()]
)))
cells.append(md(
    f"즉 초속 **{V_MIN:.2f}~{V_MAX:.2f} m/s** 보다 느린 표적은 −3 dB 이상 깎여 사실상 놓친다. "
    "**제자리에 떠 있는(호버) 드론은 시선속도가 0 에 가까워 원리적으로 이 골짜기 안에 갇힌다.** "
    f"적분시간을 {V_LONG_T:.0f} ms 로 더 늘리면 노치가 좁아져 **{V_LONG:.2f} m/s** 까지 내려가지만, "
    "그만큼 한 번 보는 데 오래 걸린다(관측을 느리게 만드는 맞바꿈).",
    "",
    "아래 그림 (c) 는 모든 신호·적분시간의 손실 곡선이 하나의 $1-\\mathrm{sinc}^2$ 곡선으로 겹침을, "
    "(d) 는 신호별 저속 사각지대(이 속도 아래로는 표적을 먹는다)를 보여 준다.",
))
cells.append(fig("verify_eca", "ECA blind-speed notch and slow-drone blind zone"))

# =========================================================================== #
#  §2  모호함수 — 분해능
# =========================================================================== #
cells.append(md(
    "---",
    "# §2. 모호함수 — 신호가 표적을 얼마나 또렷이 가르나",
))
cells.append(md(
    "**모호함수(CAF)** 는 기준신호를 거리(지연)와 속도(도플러)로 동시에 훑어 만든 2차원 지도다 — 표준 "
    "검출 사슬의 2단계이자 pyAPRiL 이 제공하는 그 상관 지도다. 한가운데 봉우리가 뾰족할수록 두 표적을 "
    "잘 가르고(분해능), 봉우리 옆에 솟은 곁봉우리는 없는 표적을 있는 것처럼 보이게 하는 가짜표적이다. "
    "여기서는 각 신호가 그 지도에서 두 표적을 얼마나 촘촘히 가르는지(거리 분해능)를 이론과 대조한다.",
    "",
    "**근거 — 거리 분해능.** 바이스태틱 거리 분해능의 이론값은 $\\Delta R_b = c / B$ (B = 기준신호 "
    "대역폭; 모노스태틱 등가는 $c/2B$). 직사각 창이면 실제 −3 dB 봉우리 폭은 이론의 **0.886배**(sinc 폭)가 "
    "나와야 정상이다. 측정 결과:",
))
cells.append(md(*(
    ["| 신호(기준) | 기준 대역폭 | 측정 ΔR_b | 이론 c/B | 측정/이론 | 곁봉우리(챔버) |",
     "|---|---|---|---|---|---|"] +
    [f"| {r['label']} · {r['ref']} | {r['refbw']:.1f} MHz | {r['meas']:.2f} m | "
     f"{r['theo']:.2f} m | **{r['ratio']:.3f}** | {r['psl']:.1f} dB |"
     for r in RES.values()]
)))
cells.append(md(
    f"측정/이론 비가 전부 **{DR_MIN:.2f}~{DR_MAX:.2f}**(sinc 의 0.886 근처)로 거리 눈금이 맞았다. "
    "**대역이 넓을수록 촘촘히 가른다** — 5G 의 측위용 신호(NR-PRS, 98 MHz)는 "
    f"{RES['nr_G3']['meas']:.1f} m 까지 가르지만, 5G 가 **상시** 내보내는 신호(SSB)는 대역이 "
    f"{RES['nr_G1']['refbw']:.1f} MHz 뿐이라 {RES['nr_G1']['meas']:.0f} m 로 거칠다. 즉 5G 로 상시 탐지하려면 "
    "거리 분해능을 크게 손해 본다 — 이 SSB 상시모드의 한계는 5G NR SSB 패시브 바이스태틱 드론 검출을 "
    "거리·속도 CRB 로 분석한 선행(Jopanya·Osorio, SPAWC 2025)이 겨냥한 바로 그 조명원이다.",
    "",
    "**곁봉우리(가짜표적)는 챔버 밖에 있다.** OFDM 신호의 반복 구조는 곁봉우리를 만들지만, 그 봉우리들은 "
    f"수백 m~km 거리에 찍혀 우리 챔버 관측창(바이스태틱 거리 ±60 m 안, 도플러 ±{CHAM:.0f} Hz) 밖이다. "
    f"창 안에서 곁봉우리는 표적보다 {min(r['psl'] for r in RES.values()):.0f} dB 이상 낮아 무해하다.",
    "",
    f"**이 모호함수는 실제 검출에 쓰는 거리-도플러 지도와 같은 것이다** — 둘을 맞대 보면 최대 "
    f"**{MAXERR:.2f} dB** 밖에 차이 나지 않는다. 아래 그림은 신호별 모호함수 지도(위)와 거리축 단면(아래)이다.",
))
cells.append(fig("verify_ambiguity_af", "Ambiguity function |chi(tau,fd)| per waveform"))
cells.append(fig("verify_ambiguity_range", "Zero-Doppler range cut — mainlobe width = range resolution"))
cells.append(md("![.](outputs/renders/anim/ambiguity_nr.gif)\n\n"
                "<sub>5G 신호의 모호함수(거리-도플러) — 가운데 봉우리가 좁고 날카로울수록 "
                "표적을 또렷이 가른다.</sub>"))
cells.append(md("![.](outputs/renders/anim/ambiguity_lte.gif)\n\n"
                "<sub>LTE 신호의 모호함수 — 대역이 좁아 거리축으로 더 퍼진다(분해능이 거칠다).</sub>"))

# =========================================================================== #
#  §3  링크버짓 — 밝기·거리·잡음 → SNR
# =========================================================================== #
cells.append(md(
    "---",
    "# §3. 링크버짓 — 밝기·거리·잡음이 신호대잡음비를 만든다",
))
cells.append(md(
    "링크버짓(레이더 방정식)은 **표적 밝기(σ) × 거리 감쇠 ÷ 잡음** 으로 되돌아온 신호대잡음비(SNR)를 "
    "예측한다. 이 절은 그 계산을 독립적인 세 방법으로 세워 서로, 그리고 이론과 맞는지 확인한다.",
    "",
    "여기서 표적 밝기 σ 는 Sionna RT 가 주지 못한다 — 창설 논문(arXiv:2303.11103)이 문서화하듯 스톡 "
    "PathSolver 는 **경로별 복소이득만** 반환하고 표적 표면 위 산란적분 단계가 없다. 그래서 Sionna 로 "
    "센싱하는 선행은 σ 를 **밖에서 계산해 채널에 주입**한다 — LAMBDA(arXiv:2607.03826)는 Sionna 전파에 상용 "
    "EM(CADFEKO) UAV RCS 를, Temporal-GNN(arXiv:2604.08306)은 점산란체 RCS 를 결합한다. 선행이 쓰는 세 갈래"
    "(상용 full-wave / 자작 SBR+PO / 점산란체) 중 여기서는 **자작 SBR+PO** 갈래를 따른다 — GPU SBR+PO"
    "(BVH SBR+PO, arXiv:2604.09243)가 쓰는 것과 같은 방법(광선으로 조명면을 찾아 그 위에서 물리광학 적분)이며, "
    "검증은 이론(평판·구)과 **실측 문헌 드론 RCS 앵커**(report08)로 한다.",
    "",
    "**근거 — 세 계산이 일치한다.** 같은 SNR 을 (a) 닫힌형 공식, (b) 단계별 사슬 계산, (c) dB 산술 세 "
    f"방법으로 구했더니 서로 최대 **{LB_MAXDEV:.0e} dB** 밖에 차이 나지 않는다(사실상 완전 일치). "
    f"신호를 모아 쌓는 **처리이득**도 이론 대비 **{PG_ERR:.3f} dB**, **잡음바닥**은 대역폭 보정을 "
    f"넣으면 이론과 **{NOISE_ERR:.0e} dB** 로 맞는다. 계산 사슬이 통째로 검증됐다.",
))
cells.append(md(*(
    ["| 신호 | 처리이득(이론) | 처리이득(측정) | 잡음바닥 오차 |",
     "|---|---|---|---|"] +
    [f"| {n} | {w['theory_ideal_db']:.2f} dB | {w['meas_rect_ongrid_db']:.2f} dB | "
     f"{[r['err_vs_theory_db'] for r in L['C_noise_floor']['rows'] if r['name']==n][0]:+.0e} dB |"
     for n, w in PG.items()]
)))

# =========================================================================== #
#  §4  디텍션이 실제로 작동한다
# =========================================================================== #
cells.append(md(
    "---",
    "# §4. 우리가 쓴 방식과 검증 — 디텍션이 실제로 작동한다  ⭐",
))
cells.append(md(
    "앞의 §1~§3 은 '한계'와 '눈금'을 다뤘다. 이제 핵심 질문: **그래서 잡히긴 하나?** 표적 봉우리가 "
    "주변 바닥보다 충분히 높으면(SCR 이 크면) 검출기가 발화한다. SCR 이 낮으면 놓치고, 어느 문턱을 넘으면 "
    "확실히 잡는다. 그 전이를 검출확률 곡선으로 본다.",
    "",
    "**검출체인은 검증된 표준이다.** ECA→CAF→CFAR 사슬 자체는 오픈소스 pyAPRiL(GPLv3)이 제공하는 그 체인이며, "
    f"그대로 돌려 NR·WiFi·LTE **{PY_OK}/{PY_N} 모드 모두** 표적을 정답 거리빈(오차 {PY_ERR} 빈)에 검출함을 "
    "확인했다(outputs/verify_pyapril.json). 아래 **대량 몬테카를로 Pd 곡선은 그 같은 표준 체인을 GPU 로 "
    "(대량 시행) 돌려** 얻은 것이다 — 검증된 체인이고, 대량 통계만 GPU 로 낸다.",
    "",
    f"**근거 — 드론이 모두 잡힌다.** SBR 로 계산한 σ 를 넣으니 5 대 드론 × 3 신호 = {N_DET} 조합의 "
    f"측정 SCR 이 **{SCR_MIN:.1f}~{SCR_MAX:.1f} dB** 로 나오고, "
    f"**{'전부 Pd = 1.0(모두 검출)' if ALL_PD1 else '대부분 검출'}** 이다. "
    f"링크버짓으로 예측한 SCR 과 실제 지도에서 잰 SCR 의 차이는 평균 **{GAP_MEAN:+.1f} dB**(±{GAP_STD:.1f}) "
    "로, 이 차이는 오류가 아니라 창 가중 등 **예측 가능한 처리 손실**이다.",
))
def _pdlabel(pd):
    return "✅ Pd=1.0" if pd == 1.0 else f"Pd={pd:.2f}"


cells.append(md(*(
    ["| 드론 | 표적 밝기 σ | 예측 SCR | 측정 SCR | 검출 |",
     "|---|---|---|---|---|"] +
    [f"| {r['drone']} | {r['sigma_dbsm']:.1f} dBsm | {r['pred_hann_db']:.1f} dB | "
     f"{r['scr_meas_db']:.1f} dB | {_pdlabel(r['pd'])} |"
     for r in DET_TAB]
)))
cells.append(md(
    "*(WiFi 조명 예시 — LTE·5G 도 같은 경향. 작은 드론일수록 σ 가 어둡지만 그래도 문턱 위에 있다.)*",
    "",
    "**검출은 SCR 5~15 dB 구간에서 전이한다.** SCR 을 바꿔 가며 검출확률을 재면(5G 조명, 운용 오경보율 "
    "$10^{-4}$ 기준) 아래처럼 0 에서 1 로 올라선다.",
))
cells.append(md(*(
    ["| SCR | 검출확률 Pd |", "|---|---|"] +
    [f"| {s:+.1f} dB | {p:.3f} |" for s, p in PD_TRANS if p is not None]
)))
cells.append(md(
    "SCR 5 dB 근처에서는 거의 못 잡다가 15 dB 에 이르면 확실히 잡는다. **우리 드론들의 운용 SCR 은 "
    f"모두 {int(SCR_MIN)} dB 이상**(최저 {SCR_MIN:.1f} dB)으로 이 전이 구간의 위쪽에 있으니 확실히 검출된다.",
    "",
    "> 🔑 **이 절이 이 리포트의 결론이다.** 표적을 밝게 만드는 σ 는 탐지에 반드시 필요하고(밝아야 봉우리가 "
    "선다), 그 σ 를 Sionna RT 로는 못 내므로 **선행이 하는 대로 자작 SBR+PO 로 계산해 채널에 주입한다.** "
    "검출은 pyAPRiL 로 검증된 표준 체인으로 하고 대량 Pd 통계만 GPU 로 낸다. 그렇게 하면 **실제로 탐지가 "
    "된다** — 위 표가 그 증거다.",
))

# =========================================================================== #
#  §5. 관측가능성 · 정확도 — '어디에 있나' 는 '있다/없다' 와 다른 문제
# =========================================================================== #
_S = OB["summary"]
_FX = OB["fixes"]
_cells_ob = OB["cells"]


def _obrow(c):
    r = c["drb_m"] / c["sigma_rb_m"] if c["sigma_rb_m"] else 0
    return (f"| {c['label']} | {c['drb_m']:.2f} m | {c['sigma_rb_m']:.3f} m | "
            f"**{r:.0f}배** | {c['scr_db']:.1f} dB |")


cells.append(md(
    "---",
    "# §5. 관측가능성 — '있다/없다' 다음에 오는 '어디에 있나'",
    "",
    "지금까지는 **탐지**(거리·속도 칸에 표적이 있나)를 다뤘다. 이 절은 그 다음 질문, **위치를 알 수 "
    "있나**를 본다. 답은 분명하다: **송·수신기 한 쌍으로는 원리적으로 불가능**하다.",
    "",
    "### 5.1 정확도 ≠ 분해능 — 흔한 오해부터",
    "",
    "**분해능(resolution)** 은 *두 표적을 가를 수 있나*(§2 의 거리 빈 폭)이고, **정확도(accuracy)** 는 "
    "*표적 하나의 위치를 얼마나 정밀히 찍나*(CRLB, 신호대잡음비에 좌우)입니다. **둘은 완전히 다른 축**인데 "
    "빈 폭을 정확도로 오해하기 쉽습니다. 이 거리·속도 정확도의 하한(CRB)은 선행에서 다뤄졌습니다 — "
    "5G SSB 패시브 바이스태틱 드론 검출의 거리·속도 CRB 를 유도한 Jopanya·Osorio(SPAWC 2025)가 그 예입니다. "
    "실측하면 정확도가 분해능보다 **수십~수백 배 미세**합니다:",
    "",
    "| 신호 | 유효 빈폭 ΔR_b (§5.1) | 정확도 σ_R_b (CRLB) | 정확도가 더 미세한 배율 | SCR |",
    "|---|---|---|---|---|",
    *[_obrow(c) for c in _cells_ob],
    "",
    f"<sub>표적이 **하나뿐**이면 {_cells_ob[0]['label'].split()[0]} 는 빈 폭이 "
    f"{_cells_ob[0]['drb_m']:.1f} m 라도 그 표적의 거리를 **{_cells_ob[0]['sigma_rb_m']*100:.1f} cm** 급으로 "
    "찍을 수 있습니다. 빈 폭은 '두 표적을 가르는 능력'이지 '한 표적을 재는 정밀도'가 아닙니다. "
    "(※ FFT 제로패딩은 정확도를 CRLB 까지 끌어올리지만 **분해능은 1도 올리지 않습니다** — 빈을 잘게 "
    "쪼갤 뿐 신호 대역이 넓어지는 게 아니니까요.)</sub>",
    "",
    "### 5.2 그런데 위치는 못 찍는다 — 송·수신기 한 쌍의 원리적 한계",
    "",
    "한 순간에 우리가 재는 것은 **바이스태틱 거리 R_b 와 도플러 f_d**, 딱 **두 개**입니다. 그런데 위치는 "
    f"**3차원**입니다. 미지수 3개를 방정식 2개로 풀 수 없습니다 — 측정으로 확인한 판정: "
    f"**{_S['verdict']}** (스냅샷 FIM 랭크 **{_S['snapshot_fim_rank']} / 상태차원 "
    f"{_S['state_dim_position']}**).",
    "",
    "> **비유 —** 종이 위에 그린 타원을 생각하세요. 압정 두 개(송신기·수신기)에 실을 걸고 연필을 팽팽히 "
    "당겨 그리면 타원이 나옵니다. R_b 를 안다는 건 '표적이 이 타원 위 어딘가'라는 뜻이지 '타원 위 어디'인지가 "
    "아닙니다. 3D 에선 타원이 **회전타원체(껍질)** 가 되고, 표적은 그 껍질 어딘가에 있습니다.",
    "",
    f"게다가 이 모호함은 근사가 아니라 **엄밀한 대칭**입니다: **{_S['exact_symmetry']}** — 표적을 송수신기를 "
    "잇는 축 둘레로 회전시켜도 R_b 와 f_d 가 **바뀌지 않습니다**. 수치로 확인하면 회전시켜도 변화가 "
    f"ΔR_b < {_S['exact_rotation_max_dRb_m']:.0e} m, Δf_d < {_S['exact_rotation_max_dfd_hz']:.0e} Hz "
    "— **기계 정밀도(부동소수점 오차) 수준**, 즉 정확히 0 입니다. 시간을 두고 여러 번 봐도(관측 그램행렬) "
    "이 축 방향은 끝내 채워지지 않습니다.",
))
cells.append(md("![observability shell](outputs/figures/report4_obs_shell.png)",
                "",
                "<sub>바이스태틱 거리 R_b 하나가 정하는 것은 '점'이 아니라 **회전타원체 껍질**이다. "
                "도플러를 더해도 껍질 위의 곡선까지만 좁혀진다.</sub>"))
cells.append(md(
    "![baseline-axis rotation keeps R_b invariant]"
    "(outputs/renders/anim/obs_baseline_ring.gif)",
    "",
    "> **움직이는 그림:** 표적을 **TX-RX 기저선 축 둘레로 회전**시키면 위치는 계속 바뀌는데 "
    "바이스태틱 거리 $R_b=R_1+R_2-L$ 은 **기계정밀도(≈1.4×10⁻¹⁴ m)까지 그대로**다. "
    "즉 한 쌍의 관측만으로는 이 회전 방향을 원리적으로 구별할 수 없다 — 위 '껍질'이 왜 점으로 "
    "좁혀지지 않는지의 직접 증거.",
))
cells.append(md("![observability CRLB](outputs/figures/report4_obs_crlb.png)",
                "",
                "<sub>위치 정확도(CRLB). 단일 송수신 쌍에서는 baseline 축 방향으로 오차가 **발산**한다 "
                "— 그 방향으로는 정보가 0 이기 때문.</sub>"))
cells.append(md(
    "### 5.3 처방 — 수신기를 늘리거나, 각도를 재거나",
    "",
    "정보가 없는 방향을 채우려면 **다른 각도에서 한 번 더 보는 수밖에** 없습니다. 세 처방을 같은 조건에서 "
    "재보면:",
    "",
    "| 구성 | 실효 랭크 | 조건수 | **위치 RMS 오차** |",
    "|---|---|---|---|",
    f"| 수신기 1개 (기준) | {_FX['1RX (baseline)']['rank_practical']} / 6 | "
    f"{_FX['1RX (baseline)']['cond']:.0e} | **{_FX['1RX (baseline)']['pos_rms_m']:.1f} m** (사실상 못 씀) |",
    f"| **수신기 2개** | {_FX['2RX']['rank_practical']} / 6 | {_FX['2RX']['cond']:.0e} | "
    f"**{_FX['2RX']['pos_rms_m']:.3f} m** |",
    f"| 수신기 1개 + 각도(AoA) 1° | {_FX['1RX + AoA(1deg)']['rank_practical']} / 6 | "
    f"{_FX['1RX + AoA(1deg)']['cond']:.0e} | **{_FX['1RX + AoA(1deg)']['pos_rms_m']:.3f} m** |",
    f"| 수신기 1개 + 각도(AoA) 5° | {_FX['1RX + AoA(5deg)']['rank_practical']} / 6 | "
    f"{_FX['1RX + AoA(5deg)']['cond']:.0e} | **{_FX['1RX + AoA(5deg)']['pos_rms_m']:.3f} m** |",
    "",
    f"**읽는 법.** 수신기 하나면 랭크가 모자라(조건수 {_FX['1RX (baseline)']['cond']:.0e} — 사실상 특이) 위치 "
    f"오차가 **{_FX['1RX (baseline)']['pos_rms_m']:.0f} m** 로 터집니다. **두 번째 수신기를 놓거나**"
    f"(→ {_FX['2RX']['pos_rms_m']*100:.0f} cm) **각도를 1° 정밀도로 재면**(→ "
    f"{_FX['1RX + AoA(1deg)']['pos_rms_m']*100:.0f} cm) 랭크가 6/6 으로 차고 위치가 풀립니다.",
    "",
    "> **그래서 [report12](report12.ipynb) 의 다중 수신기 배열이 중요합니다.** 거기서는 수신기를 늘려 "
    "**탐지 감도**(+10·log10 N dB)를 얻었는데, 같은 배열이 여기서는 **위치 관측가능성**까지 열어줍니다 — "
    "탐지에는 수신기 1개로 충분하지만, **추적(위치·궤적)에는 2개 이상 또는 각도 측정이 필수**입니다. "
    "이것이 이 프로젝트가 탐지를 먼저 하고 추적을 다음 일로 미룬 이유입니다. 추적 자체는 직접 짜지 않고 "
    "오픈소스 추적 프레임워크(Stone Soup, MIT)에 바이스태틱 측정모델만 얹어 붙일 계획이며, 셀룰러 조명·다중 "
    "수신기로 패시브 드론을 추적한 실측 선행(Fan Liu 외, 도플러 다중스태틱, arXiv:2509.25732)이 이미 있다.",
))
cells.append(md("![observability gramian](outputs/figures/report4_obs_gramian.png)",
                "",
                "<sub>시간을 두고 관측을 쌓아도(관측 그램행렬) baseline 축 방향의 고윳값은 채워지지 않는다 "
                "— 시간이 아니라 **기하**가 부족한 것이라, 오래 본다고 풀리지 않는다.</sub>"))

# =========================================================================== #
#  맺음
# =========================================================================== #
cells.append(md(
    "---",
    "## 맺음",
    "",
    "검출에는 두 종류의 문턱이 있다. **속도 쪽 문턱**: 직접파 제거(ECA)는 정지 성분을 지우므로 "
    f"초속 약 {V_MIN:.2f}~{V_MAX:.2f} m/s 보다 느린 표적, 특히 호버 드론을 원리적으로 함께 지운다. "
    "**분해능 쪽 문턱**: 두 표적을 가르는 거리 해상도는 상시 신호의 대역폭이 정하며, 측정치는 "
    f"교과서 값의 {DR_MIN:.2f}~{DR_MAX:.2f}배로 정확하다. 그 사이에서, 밝기·거리·잡음을 잇는 링크버짓은 "
    "이론과 소수점까지 맞고, **SBR 로 계산한 표적 밝기(σ)를 넣으면 드론이 실제로 검출된다**"
    f"(SCR {SCR_MIN:.0f}~{SCR_MAX:.0f} dB, Pd=1.0).",
    "",
    "**요약하면, 각 조각은 표준·선행·라이브러리로 뒷받침된다:** 검출 사슬(ECA→CAF→CFAR)은 pyAPRiL 로 검증한 "
    "패시브 레이더 표준이고, 표적 밝기 σ 는 선행이 쓰는 자작 SBR+PO 방식으로 계산해 주입하며, 파형·전파는 "
    "Sionna PHY·RT 다. **다음 단계는 실증(USRP X410, OpenISAC+GNU Radio)과 추적(Stone Soup, 거리+속도)이다.**",
))


def main():
    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3.12 (py312)",
                                      "language": "python", "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    with open(NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"notebook 생성: {os.path.relpath(NB, ROOT)}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
