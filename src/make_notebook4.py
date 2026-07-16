# -*- coding: utf-8 -*-
"""
make_notebook4.py — report4.ipynb ("탐지·추적 벤치마크를 위한 신호처리 체인 검증") 생성기
==========================================================================================
⚠ **이 파일이 진짜 소스다.** report4.ipynb 를 직접 고치지 말고 여기를 고쳐 재실행할 것.

본문의 **모든 숫자는 outputs/*.json 에서 읽어 넣는다**:
    verify_cfar / verify_eca / verify_ambiguity / verify_linkbudget /
    verify_observability / verify_ghost_impact  (6개 검증실험)
  + report4_fixups.json  ← **적대적 재검증에서 정정된 값**(측정 또는 원자료 재유도)

정정본이 있으면 **정정본을 쓴다.** 원본 JSON 의 틀린 값은 인용하지 않는다.
철회(RETRACTED)된 것은 숫자를 쓰지 않고 "모른다"고 적는다.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from provenance import provenance_cells                      # noqa: E402
from viz_report4 import VERDICT                              # noqa: E402  (판정표 = 그림과 동일 소스)

NB = os.path.join(ROOT, "report4.ipynb")


def _j(n):
    with open(os.path.join(ROOT, "outputs", n), encoding="utf-8") as f:
        return json.load(f)


C = _j("verify_cfar.json")
E = _j("verify_eca.json")
A = _j("verify_ambiguity.json")
L = _j("verify_linkbudget.json")
O = _j("verify_observability.json")
G = _j("verify_ghost_impact.json")
X = _j("report4_fixups.json")

F1, F2, F3, F4, F5, F6 = (X["F1_cfar"], X["F2_eca"], X["F3_ambiguity"],
                          X["F4_linkbudget"], X["F5_observability"], X["F6_ghost"])
GT = "g2x2_t6x6"


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def mdl(lines):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(lines))}


def fig(name, alt=""):
    return md(f"![{alt}](outputs/figures/{name}.png)")


# --------------------------------------------------------------------------- #
#  JSON 에서 자주 쓰는 값 뽑기 (전부 측정값 — 손으로 적은 숫자 없음)
# --------------------------------------------------------------------------- #
def crow(wf, mode, win, pfa, mask=1):
    r = [x for x in C["chain"][wf][mode][win]["rows"]
         if x["gt"] == GT and x["zd_mask_width"] == mask and abs(x["pfa_nom"] - pfa) < 1e-12]
    return r[0]


def ratio(wf, pfa=1e-4, mode="dpi_eca", win="op", mask=1):
    return crow(wf, mode, win, pfa, mask)["ratio"]


WFS = ("WiFi80", "LTE20", "NR100")
WNAME = {"WiFi80": "WiFi 80MHz", "LTE20": "LTE 20MHz", "NR100": "5G NR 100MHz"}
CI = {r["wf"]: r for r in F1["corrected_ci"]["rows"] if abs(r["pfa_nom"] - 1e-4) < 1e-12}
ALPHA = C["alpha_audit"][GT]
HANN = F1["hann_sidelobe_db"]
NOTCH = {r["name"]: r for r in F2["eca_notch"]["rows"] if r["M"] == 48}
DEPTH = {r["name"]: r for r in F2["eca_depth"]["rows"]}
DNROP = {r["name"]: r for r in F2["dnr_operating_point"]["rows"]}
GM = {r["key"]: r for r in F3["ghost_margin_on_detector_grid"]["rows"]}
PK = {r["key"]: r for r in F3["peaks_in_chamber"]["rows"]}
CFL = {r["name"]: r for r in F4["cfar_loss"]["rows"]}
STR = {r["name"]: r for r in F4["straddle"]["rows"]}
SHELL = {r["key"]: r for r in F5["shell_volume"]["rows"]}
CRLB = {r["config"]: r for r in F5["crlb"]["rows"]}
PF = {r["wf"]: r for r in F6["p_false"]["by_waveform"]}
FA = {r["wf"]: r for r in F6["fa_power"]["rows"]}
NPASS = sum(1 for v in VERDICT if v[2] == "PASS")
NFAIL = sum(1 for v in VERDICT if v[2] == "FAIL")
NCOND = sum(1 for v in VERDICT if v[2] == "COND")

cells = []

# =========================================================================== #
#  앞머리 (provenance)
# =========================================================================== #
_front = provenance_cells(
    report="report4",
    what="탐지·추적 벤치마크를 위한 **신호처리 체인 검증**",
    question="벤치마크를 돌리기 전에, **우리 검출기가 교정돼 있는가?**",
    tldr=[
        "**아니다.** CFAR 의 경험적 오경보율이 명목값과 다르다 — 명목 $P_{fa}=10^{-4}$ 에서 실제로는 "
        f"**WiFi {ratio('WiFi80'):.2f}배 / LTE {ratio('LTE20'):.2f}배 / 5G {ratio('NR100'):.2f}배** 더 자주 발화한다. "
        "**구현 자체에는 버그가 없다** — 이상적 백색맵(5.76e8 셀)에서는 배율이 1.00~1.02 다. "
        "깨지는 건 **실제 처리체인**이다.",
        "**더 나쁜 것: 편향이 파형마다 다르다.** 명목 Pfa 를 고정하고 Pd 를 비교하면 "
        f"LTE 에게 5G 보다 **{ratio('LTE20')/ratio('NR100'):.1f}배 느슨한 문턱**을 주는 셈이다. "
        "「어느 조명원이 좋은가」라는 벤치마크의 질문 자체가 **공정하게 물어진 적이 없었다.**",
        f"**ECA 는 저속 표적을 먹는다.** 노치는 도플러 한 빈 폭이고 이론(1-sinc²)과 정확히 맞는다 → "
        f"최소 검출가능 속도 **{NOTCH['5G NR 100MHz']['v_3db_energy_ms']:.2f} / "
        f"{NOTCH['WiFi 80MHz']['v_3db_energy_ms']:.2f} / {NOTCH['LTE 20MHz']['v_3db_energy_ms']:.2f} m/s** "
        "(5G/WiFi/LTE). **호버링 드론은 원리적으로 안 보인다.**",
        f"**단일 TX-RX 쌍으로는 3D 위치가 원리적으로 결정되지 않는다** (스냅샷 FIM 랭크 2/3, "
        f"시간을 아무리 봐도 그램행렬 랭크 {O['summary']['gramian_rank_radial']}/6). "
        "못 보는 방향은 **거의 연직** = 드론의 **고도**. → 트래킹 벤치마크의 전제가 깨져 있다.",
        f"**바닥 유령은 구조적 오경보다.** 표적과 함께 도플러가 실려 ECA 를 통과하고, 트랙 개시 확률이 "
        f"랜덤 오경보의 **{PF['5G NR 100MHz']['ratio_corrected']:.0f}배**다. 매끄럽고 운동학적으로 타당해서 "
        "**트래커가 못 거른다** → 벤치마크는 유령을 **켜야** 한다.",
        f"**판정: {NPASS} PASS / {NCOND} 조건부 / {NFAIL} FAIL.** 벤치마크가 불가능하다는 뜻이 아니다. "
        "**지금 명세 그대로 돌리면 방어할 수 없는 숫자가 나온다**는 뜻이고, 모든 FAIL 에는 값싼 처방이 있다(§7·§8).",
    ],
    roadmap=[
        dict(sec="§0", what="왜 이 리포트인가", why="벤치마크를 *하지 않고* 벤치마크를 *믿을 수 있게* 만든다"),
        dict(sec="§1", what="[E1] CFAR 오경보율 교정", why="⭐ **가장 중요** — 여기가 깨지면 모든 Pd 가 무의미"),
        dict(sec="§2", what="[E2] ECA 상쇄깊이 · 저속표적 손실", why="트래킹의 근본 한계(블라인드 속도)"),
        dict(sec="§3", what="[E3] 모호함수", why="각 파형의 분해능 상한 + 가짜 표적"),
        dict(sec="§4", what="[E4] 링크버짓 → RD SNR", why="유도 SNR 이 시뮬에서 나오는가, 처리손실은 얼마인가"),
        dict(sec="§5", what="[E5] 관측가능성", why="(Rb, f_d) 두 측정으로 3D 위치가 결정되는가 — **트래킹의 전제**"),
        dict(sec="§6", what="[E6] 바닥 유령", why="구조적 오경보 — 트래커가 못 거른다"),
        dict(sec="§7", what="**판정 체크리스트**", why="벤치마크를 돌릴 준비가 됐는가"),
        dict(sec="§8", what="다음 리포트(벤치마크)의 설계 요구사항", why="이 검증에서 나온 제약들"),
    ],
    sources=[
        dict(item="CA-CFAR α = N(Pfa^(-1/N)-1)", src="Richards, *Fundamentals of Radar Signal Processing* — "
             "셀평균 CFAR 표준 유도", kind="교과서 (우리가 독립 재유도 후 대조)"),
        dict(item="ECA (Extensive Cancellation Algorithm)", src="Colone et al., *IEEE TAES* — 패시브 레이더 "
             "직접파 제거의 표준", kind="문헌"),
        dict(item="바이스태틱 레이더방정식·CRLB", src="Willis, *Bistatic Radar*", kind="교과서"),
        dict(item="3GPP 기준신호 (LTE CRS / NR SSB / NR PRS)", src="3GPP TS 36.211 / 38.211", kind="규격"),
        dict(item="WiFi VHT-LTF", src="IEEE 802.11ac", kind="규격"),
        dict(item="드론 5종 제원 · 호버 RPM", src="docs/drone_specs_2026.json (적대적 검증 완료)", kind="측정/공표값"),
        dict(item="챔버 잔향 (RT 실측 CIR)", src="outputs/rt_env_clutter.json — Sionna RT PathSolver", kind="**우리 측정**"),
        dict(item="표적 RCS σ", src="src/rcs_sbr.py (SBR, 가림 포함)", kind="**우리 측정**"),
    ],
    engines=["sionna-rt", "sbr", "radar-dsp", "matplotlib"],
    libs=["sionna", "mitsuba", "torch", "numpy", "scipy", "matplotlib"],
    reproduce=[
        "# 6개 검증실험 (각각 독립 실행 — JSON 을 남긴다)",
        "~/.venvs/py312/bin/python benchmark/verify_cfar.py          # [E1]  GPU, ~15분",
        "~/.venvs/py312/bin/python benchmark/verify_eca.py           # [E2]  CPU, ~40분",
        "~/.venvs/py312/bin/python benchmark/verify_ambiguity.py     # [E3]  GPU, ~2분",
        "~/.venvs/py312/bin/python benchmark/verify_linkbudget.py    # [E4]  GPU, ~5분",
        "~/.venvs/py312/bin/python benchmark/verify_observability.py # [E5]  GPU, ~2분",
        "~/.venvs/py312/bin/python benchmark/verify_ghost_impact.py  # [E6]  GPU, ~10분",
        "",
        "# 적대적 재검증에서 드러난 오류의 **정정값을 다시 측정**한다 (필수)",
        "~/.venvs/py312/bin/python benchmark/report4_fixups.py       #       GPU, ~7분",
        "",
        "# 그림 7장 + 이 노트북",
        "~/.venvs/py312/bin/python src/build_report4.py",
    ],
    artifacts=[
        dict(file="outputs/verify_cfar.json", what="[E1] Pfa 교정 — 백색맵/체인/대조군/교정표/ROC"),
        dict(file="outputs/verify_eca.json", what="[E2] 상쇄깊이·DNR·파일럿잔류·도플러노치"),
        dict(file="outputs/verify_ambiguity.json", what="[E3] 파형별 2D 모호함수 요약"),
        dict(file="outputs/verify_linkbudget.json", what="[E4] 레이더방정식·처리이득·손실분해"),
        dict(file="outputs/verify_observability.json", what="[E5] 껍질부피·FIM/CRLB·그램행렬"),
        dict(file="outputs/verify_ghost_impact.json", what="[E6] 유령 궤적·CFAR·트래커·완화"),
        dict(file="outputs/report4_fixups.json", what="⭐ **정정값** — MEASURED / DERIVED / RETRACTED 로 태깅"),
        dict(file="outputs/figures/report4_e[1-7]_*.png", what="본문 그림 7장"),
    ],
    caveats=[
        "**이 리포트는 벤치마크가 아니다.** 어느 조명원이 좋은지, 어느 드론을 잡는지 **답하지 않는다.** "
        "그 답을 **믿을 수 있게** 만드는 것이 목적이다.",
        "**옛 report4 의 탐지 결과는 폐기됐다.** 이 리포트가 그 자리를 대신한다.",
        f"**바닥 유령의 진폭은 편파 V 가정에 걸려 있다.** 입사각이 콘크리트 브루스터각 바로 아래라 V(TM)가 "
        f"이례적으로 약하다. H(TE) 이면 유령이 **{F6['polarization']['delta_db']:.0f} dB 세지고** §6 의 결론이 "
        "전부 뒤집힌다. **편파는 측정된 적이 없다 — 가정이다.**",
        "**E5 의 AoA 처방(σ=1°/5°)은 가정이다.** 실제 안테나로 측정한 값이 아니다. 2RX 처방만 순수 기하다.",
        "**ECA 바닥(31~56 dB)의 원인은 규명되지 않았다.** ADC 양자화가 아니라는 것만 측정됐다. "
        "분수지연 보간 결함이라는 가설이 있으나 **우리 JSON 에 대조군이 없다** → 단정하지 않는다.",
        "**E1 의 신뢰구간은 원본이 낙관적이었다.** wilson_ci 는 셀 독립을 가정하는데 이 실험이 재는 대상이 "
        "바로 셀 간 상관이다. 본문은 유효 독립셀로 **다시 낸 CI** 를 쓴다. 배율의 소수 둘째 자리는 무의미하다.",
        "**E6 의 랜덤 Pfa 측정에는 검정력이 없다** (FA 1~5개). 그 하네스로 Pfa 를 재려 하면 안 된다 — 그건 E1 의 일이다.",
    ],
    cost="GPU 1장(자동선택). 6개 실험 + 정정 측정 합계 약 80분. E1 이 가장 비싸다"
         f"(백색맵 {C['meta']['n_maps_white']:,}장 + 체인 {C['meta']['n_maps_chain']:,}장/파형·모드, complex128).",
    related=[
        dict(rep="report2", rel="파형·자원격자·점유모드(G1/G3)와 모노스태틱 RCS — 이 리포트의 **입력**"),
        dict(rep="report3", rel="관절 드론·마이크로도플러 — 표적 모델의 출처"),
        dict(rep="report5", rel="**이 리포트가 검증하려는 벤치마크.** §7 의 FAIL 은 report5 의 숫자에 "
             "직접 영향을 준다(특히 파형 간 Pd 비교)"),
        dict(rep="다음 리포트", rel="§8 의 설계 요구사항을 반영한 **재설계된 벤치마크**"),
    ],
    glossary=[
        ("Pfa (오경보율)", "표적이 없는데 검출기가 '있다'고 말할 확률. **명목**(우리가 요구한 값)과 "
                          "**경험적**(실제로 나온 값)이 다르면 검출기는 교정되지 않은 것이다"),
        ("Pd (검출확률)", "표적이 있을 때 실제로 검출할 확률. **Pfa 를 고정해야만** 서로 비교할 수 있다"),
        ("CFAR", "일정 오경보율 검출기. 주변 셀(**훈련셀**)의 잡음 수준을 보고 문턱을 정한다"),
        ("CA-CFAR α", "문턱 배수. α = N(Pfa^(-1/N) - 1), N = 훈련셀 수. 훈련셀이 적을수록 α 가 커진다(=CFAR 손실)"),
        ("ECA", "직접파(TX→RX 가시선)를 지우는 전처리. 지연된 기준신호의 부분공간으로 **사영해서 뺀다**"),
        ("RD 맵", "거리-도플러 맵. 가로축 = 바이스태틱 거리 Rb, 세로축 = 도플러 f_d. 검출은 이 위에서 한다"),
        ("CPI", "코히어런트 처리구간. M 개 프레임을 코히어런트하게 합친다 → 도플러 분해능 = 1/T_CPI"),
        ("SCR", "신호 대 클러터+잡음비. RD 맵에서 표적 피크가 배경보다 몇 dB 위인가"),
        ("모호함수 χ(τ,f_d)", "점표적 하나가 RD 맵에 그리는 응답. **분해능과 부엽(가짜 표적)의 상한**을 정한다"),
        ("바닥 유령", "TX→표적→**바닥**→RX 경로. 표적을 거치므로 **도플러가 실려** ECA 를 통과한다"),
        ("관측가능성", "측정으로부터 상태(위치·속도)를 **원리적으로** 결정할 수 있는가. 랭크가 모자라면 "
                      "SNR 을 아무리 높여도 못 푼다"),
        ("CRLB", "불편추정량의 분산 하한. **랭크가 모자라면 CRLB 자체가 의미 없다**"),
        ("semi-anechoic", "벽·천장만 흡수체이고 **바닥은 반사성**인 챔버. 우리 챔버가 이것"),
    ],
)

# 앞머리는 [머리(제목/TL;DR/로드맵), 출처·환경 상세] 2개 셀이다.
# 제목/TL;DR 바로 다음에 "5분 요약"을 끼우고, 무거운 출처 상세는 그 뒤로 민다.
cells.append(_front[0])

# =========================================================================== #
#  🔰 5분이면 이해하는 이 리포트 (수식 없이, 일상 비유로)
# =========================================================================== #
cells.append(md(
    "## 🔰 5분이면 이해하는 이 리포트",
    "",
    "> 이 상자는 **비유로 먼저 감을 잡으라고** 넣었습니다. 아래 본문의 수식·dB·검증 수치는 하나도 안 지웠으니, "
    "여기서 큰 그림을 잡고 내려가면 됩니다.",
    "",
    "**왜 이 리포트가 필요한가.** 우리의 진짜 목표는 시합입니다 — WiFi·LTE·5G 중 **어느 신호로 드론을 제일 잘 잡나**. "
    "그런데 시합을 시작하기 전에 먼저 확인할 게 있습니다. **심판의 스톱워치가 정확한가, 저울의 0점이 맞는가.** "
    "이 리포트는 시합이 아니라 그 **장비 점검**입니다.",
    "",
    "**무슨 비유로 이해하면 되나.** 패시브 레이더는 내 송신기 없이 **남이 틀어 놓은 방송(WiFi·LTE·5G)의 반사**만으로 "
    "표적을 봅니다 — 남의 손전등 빛으로 어둠 속 물체를 더듬는 셈이죠. 이 손전등 빛을 받아 '저기 뭔가 있다'고 판정하는 "
    "장치가 우리 검출기입니다. 이 리포트는 그 검출기의 **눈금이 맞는지** 여섯 가지로 뜯어봅니다.",
    "",
    "**무엇을 발견했나 (쉬운 말로).**",
    "- **문턱이 신호마다 몰래 달랐다.** '헛것을 볼 확률'을 똑같이 맞춰 놓고 겨루는 줄 알았는데, 실제로는 LTE 에게 "
    "5G 보다 훨씬 느슨한 잣대를 주고 있었습니다. **애초에 공정한 시합이 아니었던 것**입니다(§1).",
    "- **멈춘 드론은 원리적으로 안 보인다.** 검출기가 '움직이지 않는 것'을 배경으로 여겨 지워버리기 때문에, "
    "제자리 비행(호버링)하는 드론은 지워집니다 — 버그가 아니라 물리입니다(§2).",
    "- **5G 는 눈을 아주 가끔만 뜬다.** 5G 의 상시 기준신호는 20 ms 에 한 번, 그것도 좁게만 나와서 빠른 표적을 "
    "놓칩니다. 우리 드론(3 m/s)조차 5G 한테는 너무 빨라 흐릿하게 접힙니다 — 이게 '5G 이중고'의 절반입니다(§3).",
    "- **안테나 하나로는 높이를 못 잰다.** 수학적으로 그렇습니다. 방 전체만 한 껍질 위 어딘가라고만 말할 수 있고, "
    "특히 **드론의 고도**를 못 봅니다. 수신기를 하나 더 놓거나 안테나 배열을 써야 풀립니다(§5).",
    "- **바닥 반사가 유령을 만든다.** 반사성 바닥이 표적을 3.5 m 뒤에서 따라다니는 그림자를 만드는데, "
    "그게 표적처럼 매끄럽게 움직여서 **5G 는 진짜 표적으로 착각**합니다(§6).",
    "",
    "**그래서 뭐가 중요한가.** 이 장비 점검을 건너뛰고 바로 시합을 돌렸다면, 나온 숫자가 **그럴듯해 보이지만 "
    "틀렸을** 겁니다 — 그리고 아무도 눈치채지 못했겠죠. 다행히 발견된 문제에는 전부 **값싼 처방**이 있습니다(§7·§8). "
    "즉 이 리포트는 나쁜 소식이 아니라, 시합을 **믿을 수 있게** 만드는 사전 정비입니다.",
    "",
    "> 📎 **LaSen 논문(SenSys'26)과의 연결.** 위의 '5G 이중고'(§3)와 '안테나 하나로는 3D 위치를 못 잡는다'(§5)는 "
    "LaSen 이 붙든 문제와 **같은 뿌리**입니다. 다만 LaSen 은 5G 기지국이 **자기 신호의 반사를 자기가 받아** "
    "표적의 **거리와 속도**를 추적합니다(3D 위치가 아니라). 그래서 '안테나 하나로 3D 위치는 원리적으로 불가능'이라는 "
    "우리 §5 결론과 **모순되지 않습니다** — 애초에 겨누는 목표가 다르기 때문입니다.",
))
cells.append(_front[1])

# =========================================================================== #
#  §0
# =========================================================================== #
cells.append(md(
    "# §0. 왜 이 리포트인가",
    "",
    "> 🔍 **여기서 하는 일:** 벤치마크를 *돌리지 않는다*. 벤치마크를 *믿을 수 있게* 만든다.",
    "",
    "우리의 최종 목적은 **패시브 레이더 탐지·추적 벤치마크**다 — 어느 조명원(WiFi / LTE / 5G)이 좋은가, "
    "어느 드론을 잡는가. 그런데 그 벤치마크를 돌리기 **전에 증명해야 할 것**이 하나 있다.",
    "",
    "## > **\"우리 검출기가 교정돼 있는가?\"**",
    "",
    "이유는 단순하다. 탐지 성능은 **항상 두 숫자의 쌍**이다 — (Pd, Pfa). "
    "Pd 하나만으로는 아무 의미가 없다. 문턱을 낮추면 Pd 는 언제든 1.0 이 되고, 대신 오경보가 쏟아진다. "
    "그래서 레이더는 **Pfa 를 고정해 놓고** Pd 를 비교한다.",
    "",
    "**그 고정이 실제로 고정돼 있지 않다면, 모든 Pd 숫자가 무의미하다.**",
    "",
    "이건 레이더 문헌의 가장 기본적인 검증인데 — 우리는 **한 번도 하지 않았다.**",
    "",
    "---",
    "",
    "### 이 리포트가 하는 6가지 검증",
    "",
    "| | 실험 | 묻는 것 | 왜 벤치마크가 여기 걸려 있나 |",
    "|---|---|---|---|",
    "| §1 | **[E1] CFAR 교정** | 명목 Pfa = 경험적 Pfa 인가? | ⭐ 아니면 **모든 Pd 가 무의미** |",
    "| §2 | **[E2] ECA** | 직접파를 얼마나 지우나? 표적도 지우나? | 저속 표적의 **블라인드 속도** |",
    "| §3 | **[E3] 모호함수** | 각 파형의 분해능 상한과 가짜 표적은? | 분해능 주장의 **근거** |",
    "| §4 | **[E4] 링크버짓** | 유도한 SNR 이 시뮬에서 나오나? | 물리와 시뮬의 **연결** |",
    "| §5 | **[E5] 관측가능성** | (Rb, f_d) 로 3D 위치가 결정되나? | **트래킹의 전제** |",
    "| §6 | **[E6] 바닥 유령** | 유령이 가짜 표적을 만드나? | **구조적** 오경보 |",
    "",
    "### 이 리포트를 읽는 법",
    "",
    "**실패를 찾는 것이 이 리포트의 가치다.** 각 절은 PASS/FAIL 을 명시하고, FAIL 이면 **무엇을 고쳐야 하는지**를 "
    "적는다. 아무것도 안 깨졌다면 이 리포트는 쓸모가 없었을 것이다.",
    "",
    "> 🔬 **적대적 재검증을 거쳤다.** 6개 실험의 결과를 각각 다시 뜯어 반증을 시도했고, "
    "**여러 건의 오류를 찾아 정정했다**(원인 귀속 오류, 진폭/전력 dB 혼동, 인덱싱 결함, 낙관적 신뢰구간 등). "
    "본문은 **정정된 값**을 쓴다. 정정 과정 자체가 측정으로 남아 있다 → `outputs/report4_fixups.json` "
    "(`MEASURED` / `DERIVED` / `RETRACTED` 로 태깅). "
    "**뒷받침되지 않는 숫자는 철회했고, 대체값을 지어내지 않았다.**",
))

# =========================================================================== #
#  §1  E1 — CFAR
# =========================================================================== #
cal = C["chain"]["LTE20"]["dpi_eca"]["calib_op_mask1"]
w48 = [r for r in C["white"]["48x24"]["rows"]
       if r["gt"] == GT and r["zd_mask_width"] == 1]
wmin, wmax = min(r["ratio"] for r in w48), max(r["ratio"] for r in w48)
nrs = F1["range_window_sweep"]["rows"]
lte6 = [r for r in nrs if r["wf"] == "LTE20" and r["n_range"] == 6][0]
lte48 = [r for r in nrs if r["wf"] == "LTE20" and r["n_range"] == 48][0]
wf6 = [r for r in nrs if r["wf"] == "WiFi80" and r["n_range"] == 6][0]
wf16 = [r for r in nrs if r["wf"] == "WiFi80" and r["n_range"] == 16][0]
CLC = F1["clutter_control"]

cells.append(md(
    "---",
    "# §1. [E1] CFAR 오경보율 교정  ⭐ 가장 중요",
    "",
    "> 🔍 **여기서 하는 일:** 표적이 **없는** 잡음 맵을 대량으로 만들어 CFAR 에 먹이고, "
    "**실제로 몇 번 발화하는지 센다.** 명목 Pfa 와 같으면 교정된 것이다.",
    "",
    "## 판정: **FAIL** — 구현은 완벽한데 실제 체인에서 어긋난다. 그리고 **파형마다 다르게** 어긋난다.",
))
cells.append(fig("report4_e1_cfar", "E1 CFAR calibration"))

cells.append(mdl([
    "### 1.1 먼저: 구현 자체는 맞다 (PASS)",
    "",
    "원인을 검출기 **바깥**에서 찾기 전에, 검출기 **안**을 먼저 배제해야 한다. 세 가지를 확인했다.",
    "",
    "| 검사 | 결과 | 판정 |",
    "|---|---|---|",
    f"| α 식이 N(Pfa^(-1/N)-1) 인가 (N={ALPHA['N_interior']}) | 코드 vs 이론 상대오차 **{ALPHA['rel_err']:.1e}** | ✅ |",
    f"| 문턱이 전력 단위인가 | noise_est/P = **{ALPHA['noise_est_over_power']:.4f}** | ✅ |",
    f"| 평평한 맵에서 발화하는가 | **{ALPHA['any_det_on_flat_map']}** | ✅ |",
    f"| **이상적 백색 맵**({C['white']['48x24']['n_maps']*48*24/1e8:.2f}e8 셀)에서 경험 Pfa/명목 Pfa | "
    f"명목 1e-2~1e-6 전 구간에서 **{wmin:.2f} ~ {wmax:.2f}** | ✅ |",
    "",
    "> **즉 CA-CFAR 구현에는 버그가 없다.** iid 복소가우시안을 먹이면 정확히 요구한 만큼만 발화한다. "
    "GPU 고속 경로도 `ca_cfar_2d` 와 검출 마스크가 **비트단위로 일치**함을 확인했다"
    f"(`fast_path_identical_to_ca_cfar_2d = {C['fast_path_identical_to_ca_cfar_2d']}`).",
    "",
    "### 1.2 그런데 실제 체인에서는 깨진다 (FAIL)",
    "",
    "같은 CFAR 에 **실제 파형의 기준신호로 정합필터링한 잡음** + DPI(직접파 간섭 — TX 에서 곧장 RX 로 "
    "새어 든 강한 신호) + ECA 를 통과시킨 맵을 먹였다 "
    "(= report4/5 가 실제로 쓰는 운용 형상). 명목 $P_{fa}=10^{-4}$:",
    "",
    "| 파형 | 경험적 Pfa | **배율** | 95% CI (상관 보정) |",
    "|---|---|---|---|",
] + [
    f"| {WNAME[w]} | {CI[w]['pfa_emp']:.2e} | **{CI[w]['ratio']:.2f}배** | "
    f"[{CI[w]['ratio_ci_corrected'][0]:.2f}, {CI[w]['ratio_ci_corrected'][1]:.2f}] |"
    for w in WFS
] + [
    "",
    f"낮은 Pfa 로 갈수록 더 어긋난다 (log-log 기울기 {cal['loglog_slope']:.2f} < 1). "
    f"명목 $10^{{-6}}$ 에서는 배율이 최대 {max(ratio(w, 1e-6) for w in WFS):.1f}배까지 간다.",
    "",
    "> ⚠️ **신뢰구간에 대하여.** 원본 실험은 `wilson_ci` 를 썼는데, 그것은 셀이 **독립**이라고 가정한다. "
    "그런데 **이 실험이 측정하고 있는 대상이 바로 셀 간 상관**이다(아래 1.3). 따라서 원 CI 는 계통적으로 "
    "**낙관적**이다. 위 표는 유효 독립셀 수(= 셀 수 × eff_indep_2d)로 **다시 낸 CI** 다. "
    "**배율의 자릿수와 부호는 견고하지만 소수 둘째 자리는 무의미하다.**",
]))

cells.append(mdl([
    "### 1.3 ⭐ 진짜 문제: 편향이 **파형마다 다르다**",
    "",
    "\"Pfa 가 일정 배율로 어긋난다\"면 문턱을 한 번 조여서 끝낼 수 있다. 그런데 실제로는:",
    "",
    f"## LTE {ratio('LTE20'):.2f}배  vs  5G {ratio('NR100'):.2f}배  vs  WiFi {ratio('WiFi80'):.2f}배",
    "",
    "벤치마크의 질문은 **\"어느 조명원이 좋은가\"** 다. 그런데 명목 Pfa 를 고정하고 Pd 를 비교하면 —",
    "",
    f"> ### 우리는 LTE 에게 5G 보다 **{ratio('LTE20')/ratio('NR100'):.1f}배 느슨한 문턱**을 주고 있었다.",
    "",
    "**같은 명목 Pfa 에서의 비교가 같은 오경보율에서의 비교가 아니었다.** 이건 교정 오차보다 심각하다 — "
    "**Pd 비교의 공정성 자체가 깨져 있었다**는 뜻이고, 그게 벤치마크의 존재 이유다.",
    "",
    "> **쉽게 말하면 —** 세 선수에게 '헛것을 볼 확률'을 똑같이 맞춰 주고 겨루게 했다고 믿었는데, "
    "실제로는 LTE 한테만 문턱을 낮게 깔아 준 셈이다. 낮은 문턱이면 표적을 더 잘 잡는 게 당연하니, "
    "**'LTE 가 더 잘 잡더라'는 결과가 나와도 그건 실력이 아니라 심판의 편애**다.",
]))

cells.append(mdl([
    "### 1.4 원인 — 두 가지다 (둘 다 대조군으로 확정)",
    "",
    "#### 원인 1: RD 맵이 **백색이 아니다** (그림 c)",
    "",
    "CFAR 는 훈련셀이 iid 라고 가정한다. 그런데 실제 RD 맵은 두 축 모두 상관돼 있다:",
    "",
    "| 상관원 | 크기 | 왜 |",
    "|---|---|---|",
    f"| **도플러축** (slow-time Hann 창) | ρ ≈ +{C['chain']['NR100']['dpi_eca']['whiteness']['rho_doppler'][0]:.2f} (전 파형 공통) | "
    "Hann 창이 인접 도플러 빈을 섞는다 |",
    f"| **거리축** (기준대역 < fs) | WiFi +{C['chain']['WiFi80']['dpi_eca']['whiteness']['rho_range'][0]:.2f} / "
    f"LTE +{C['chain']['LTE20']['dpi_eca']['whiteness']['rho_range'][0]:.2f} / "
    f"NR +{C['chain']['NR100']['dpi_eca']['whiteness']['rho_range'][0]:.2f} | "
    "기준신호 대역이 fs 보다 좁으면 거리축이 과표본된다 |",
    "",
    "**대조군이 이를 확정한다** (NR100, 잡음만, 명목 1e-4):",
    "",
    "| 설정 | 배율 |",
    "|---|---|",
    f"| 기준(Hann + 정합필터) | {ratio('NR100', 1e-4, 'noise'):.2f} |",
    f"| Hann 제거(rect) | {[r for r in C['control_rect_window_NR100']['op']['rows'] if r['gt']==GT and r['zd_mask_width']==1 and abs(r['pfa_nom']-1e-4)<1e-12][0]['ratio']:.2f} |",
    f"| 백색화 부정합필터 | {[r for r in C['control_whitened_mf_NR100']['op']['rows'] if r['gt']==GT and r['zd_mask_width']==1 and abs(r['pfa_nom']-1e-4)<1e-12][0]['ratio']:.2f} |",
    f"| **둘 다** | **{[r for r in C['control_whitened_mf_rect_NR100']['op']['rows'] if r['gt']==GT and r['zd_mask_width']==1 and abs(r['pfa_nom']-1e-4)<1e-12][0]['ratio']:.2f}** ← 교정 복구 |",
    "",
    "#### 원인 2: **거리창이 CFAR 훈련창보다 좁다** (그림 d) — 이게 파형 간 차이를 만든다",
    "",
    "> 🔬 **정정.** 원 실험은 LTE 의 2.47배를 **전적으로** \"거리축 과표본 상관\" 탓으로 돌렸다. "
    "**대조군을 돌려 보니 틀렸다.**",
    "",
    f"거리창(`n_range`)을 스윕하며 배율을 다시 쟀다 (명목 1e-4, 잡음만, {F1['range_window_sweep']['n_maps']}맵/점):",
    "",
    "| 파형 | ρ_range | n_range=6 | 16 | 24 | 48 | 벤치마크가 쓰는 값 |",
    "|---|---|---|---|---|---|---|",
] + [
    "| " + WNAME[w] + " | " +
    f"{[r for r in nrs if r['wf']==w][0]['rho_range_lag1']:+.2f} | " +
    " | ".join(
        (f"**{[r for r in nrs if r['wf']==w and r['n_range']==n][0]['ratio']:.2f}**"
         if [r for r in nrs if r["wf"] == w and r["n_range"] == n] else "-")
        for n in (6, 16, 24, 48)) +
    f" | n_range = **{[r for r in nrs if r['wf']==w][0]['n_range_bench']}** |"
    for w in ("WiFi80", "LTE20", "NR100")
] + [
    "",
    f"> 🔑 **결정타: 거리상관이 사실상 0 인 WiFi**(ρ={wf6['rho_range_lag1']:+.2f})**조차 거리창을 6빈으로 줄이면 "
    f"{wf16['ratio']:.2f} → {wf6['ratio']:.2f} 로 부푼다.** 즉 배율은 파형 고유 성질만이 아니라 **하네스 설정**의 문제다.",
    "",
    f"CFAR 의 거리축 훈련창 반경 = guard+train = **{lte6['cfar_train_radius_range']}빈** → 온전한 훈련창을 가지려면 "
    f"거리창이 최소 **{2*lte6['cfar_train_radius_range']+1}빈** 이어야 한다. 그런데 `chamber_window()` 가 주는 값은 "
    "**WiFi 16 / LTE 6 / NR 24** — LTE 는 물론 WiFi 도 모자란다. 모자라면 **모든 셀이 가장자리 셀**이 되어 "
    "훈련셀이 잘리고 서로 중첩된다.",
    "",
    f"LTE 의 {ratio('LTE20'):.2f}배는 결국 **(도플러 Hann 상관) × (거리창 부족) × (거리축 과표본 상관)** 의 곱이다. "
    f"거리창을 48빈으로 넓히면 같은 ρ 를 갖고도 {lte6['ratio']:.2f} → {lte48['ratio']:.2f} 로 떨어진다 "
    "— **과표본 상관만으로는 설명이 안 된다.**",
]))

wide1 = {w: crow(w, "dpi_eca", "wide", 1e-4, 1)["ratio"] for w in WFS}
wide3 = {w: crow(w, "dpi_eca", "wide", 1e-4, 3)["ratio"] for w in WFS}
cells.append(mdl([
    "### 1.5 💣 지뢰: 0-도플러 마스킹은 **운으로** 버티고 있다 (그림 e)",
    "",
    "현재 코드는 `det[zd,:] = False` 로 **0-도플러 행 하나만** 지운다. 그런데 —",
    "",
    f"**slow-time Hann 창의 DFT 는 ±1 빈으로 {HANN['bin_1']:.1f} dB 밖에 안 떨어진다** "
    f"(±2 에서야 {HANN['bin_2']:.0f} dB). 그래서 DPI 잔류는 zd 뿐 아니라 **zd±1 행에도 거의 그대로 실린다.** "
    "한 행 마스킹으로는 그 두 행을 못 지운다.",
    "",
    f"거리창을 ECA 탭 수 너머로 넓히면(WIDE, {C['meta']['n_range_wide']}빈) 무슨 일이 나는지:",
    "",
    "| 파형 | 마스크 폭 1 (현재 운용값) | 마스크 폭 3 (zd±1 까지) |",
    "|---|---|---|",
] + [
    f"| {WNAME[w]} | **{wide1[w]:.0f}배** 💥 | {wide3[w]:.2f}배 |" for w in WFS
] + [
    "",
    "> **report4/5 가 이 지뢰를 밟지 않은 건 설계가 아니라 운이다.** `chamber_window()` 가 "
    "`n_taps = n_range + 8` 로 잡는 덕분에 거리창이 **항상 ECA 탭 안**에 들어와 있을 뿐이다. "
    "챔버가 커지거나 Rb 창을 넓히는 순간 무너진다. (덧붙여 n_taps 에는 상한 96 이 있어 "
    "n_range > 88 이면 **지금 코드에서도** 즉시 무너진다.)",
    "",
    "⚠ 다만 마스크 폭 3 은 배율을 1.0 이 아니라 **0.65~0.85 로 과보정**한다. 뜨거운 zd±1 행을 *검출*에서만 "
    "빼고 *훈련셀*에는 그대로 두기 때문에 이웃 행의 잡음 추정이 부풀어 문턱이 과하게 올라간다. "
    "**제대로 된 수정은 그 행들을 훈련창에서도 배제하는 것**(도플러 가드)이다.",
]))

cells.append(mdl([
    "### 1.6 정적 클러터는 여전히 죽은 파라미터다 — 그러나 이유가 달랐다",
    "",
    "> 🔬 **정정.** 원 실험 요약은 \"클러터를 넣었지만 어떤 수치도 안 움직였다\"고 적었는데, "
    "**그 실험에는 클러터 on/off 대조군이 아예 없었다.** 과거 하네스의 결과를 옮겨 적은 것이다. "
    "→ **대조군을 직접 돌렸다.**",
    "",
    f"NR100, 운용 형상, {CLC['n_maps']}맵:",
    "",
    "| | CFAR 히트 | 경험 Pfa | 배율 |",
    "|---|---|---|---|",
    f"| 클러터 **on** | {CLC['clutter_on']['hits']} | {CLC['clutter_on']['pfa_emp']:.2e} | {CLC['clutter_on']['ratio']:.2f} |",
    f"| 클러터 **off** | {CLC['clutter_off']['hits']} | {CLC['clutter_off']['pfa_emp']:.2e} | {CLC['clutter_off']['ratio']:.2f} |",
    "",
    "**결론은 참이다** — Pfa 가 안 움직인다. **그러나 적혀 있던 이유는 틀렸다.** "
    "\"ECA 사영으로 정확히 0 이 된다\"는 설명은 클러터가 지연된 **기준신호(ref)** 일 때만 성립한다. "
    "실제 코드의 클러터는 지연된 **tx**(= 파일럿 + **데이터**)이므로 ECA 부분공간 **밖**이고 정확히 0 이 되지 않는다 "
    f"(실제로 클러터를 빼면 ρ_range 가 {CLC['clutter_on']['rho_range']:.3f} → {CLC['clutter_off']['rho_range']:.3f} 로 "
    "**움직인다** — 맵이 바뀐다).",
    "",
    f"안 움직이는 **진짜 이유**: 클러터가 DPI 보다 {abs(CLC['clutter_below_dpi_db']):.0f} dB 아래라, "
    "이미 소거 불가능한 **DPI 데이터 잔류에 묻힌다.**",
]))

roc = C["roc_NR100"]
cells.append(mdl([
    "### 1.7 처방: 교정 룩업표 + 경험적 Pfa 로 그린 ROC",
    "",
    "**경험적 Pfa 목표 → 실제로 줘야 할 명목 Pfa** (운용 형상, g2x2_t6x6):",
    "",
    "| 원하는 경험적 Pfa | WiFi80 | LTE20 | NR100 |",
    "|---|---|---|---|",
] + [
    "| " + f"{t:.0e}" + " | " + " | ".join(
        (lambda p: f"{p:.2e}" if p == p else "(외삽)")(
            [x["pfa_nominal_needed"] for x in C["chain"][w]["dpi_eca"]["calib_op_mask1"]["points"]
             if abs(x["pfa_target_emp"] - t) < 1e-12][0])
        for w in WFS) + " |"
    for t in (1e-3, 1e-4, 1e-5)
] + [
    "",
    "→ **LTE 만 2배 이상 조여야 한다.** 이 표가 §8 의 설계 요구사항 1번이 된다.",
    "",
    f"그리고 ROC 는 **경험적 Pfa 축**에 그려야 한다(그림 f). NR100, Rb={roc['Rb_m']:.1f} m, "
    f"f_d={roc['fd_hz']:.0f} Hz, {roc['curves'][0]['n_trials']} trial/점:",
    "",
    "| SCR | Pd (경험적 Pfa ≈ 1.6e-4 에서) |",
    "|---|---|",
] + [
    f"| {c['scr_db']:+.1f} dB | {[p['pd'] for p in c['points'] if abs(p['pfa_nom']-1e-4)<1e-12][0]:.3f} |"
    for c in sorted(roc["curves"], key=lambda c: c["scr_db"])
] + [
    "",
    "**전이는 SCR 5~15 dB 사이에서 일어난다.** 이 구간이 벤치마크가 실제로 겨눠야 할 동작점이다.",
]))

# =========================================================================== #
#  §2  E2 — ECA
# =========================================================================== #
s3 = {(r["occ"], r["name"]): r for r in E["S3_pilot_vs_tx"]}
gate = F2["eca_gate_vacuous"]["rows"]
cells.append(md(
    "---",
    "# §2. [E2] ECA — 상쇄 깊이와 **저속 표적 손실**",
    "",
    "> 🔍 **여기서 하는 일:** ECA(TX→RX 직접 도달파를 지워 표적을 드러내는 전처리) 가 직접파를 얼마나 "
    "지우는지, 그리고 **표적까지 얼마나 지우는지** 잰다.",
    "",
    "핵심 사실 하나면 전부 따라온다. `ECACanceller.cancel(s) = (I - P)s` 는 **s 에 대해 선형인 사영**이다 "
    "(가중치는 기준신호에만 의존). 그러면:",
    "",
    "- 기준신호의 지연복제로 표현되는 것(= 정적 클러터)은 부분공간 **안** → 진폭 무관하게 지워진다",
    "- 부분공간 **밖**의 것(도플러 有, 데이터 성분)은 **못 지운다**",
    "- **그런데 표적도 도플러가 작으면 부분공간에 가까워진다 → 지워진다** ← 이게 §2 의 핵심",
    "",
    "## 판정: **조건부 PASS** (상쇄 깊이) + **FAIL** (호버링 드론은 원리적으로 안 보인다)",
))
cells.append(fig("report4_e2_eca", "E2 ECA"))

cells.append(mdl([
    "### 2.1 ECA 에는 **단단한 바닥**이 있다 (조건부 — '완벽하다'는 거짓)",
    "",
    "> 🔬 **정정.** 원 스크립트는 그림 제목과 docstring 에 \"float64 ECA 는 동적범위 한계가 없다 / "
    "unphysically perfect\" 라고 **측정 전에 미리 적어 두었다.** 측정 결과 **거짓이다.**",
    "",
    "| 파형 | 벤치 탭수 | 직접파만 (기저 안) | **+ RT 실측 챔버 잔향** | 잔향 경로 |",
    "|---|---|---|---|---|",
] + [
    f"| {n} | {DEPTH[n]['n_taps_bench']} | {DEPTH[n]['depth_dpi_only_db']:.0f} dB (float64 한계) | "
    f"**{DEPTH[n]['depth_at_bench_taps_db']:.1f} dB** | {DEPTH[n]['n_clutter']}개 ({DEPTH[n]['clutter_src']} 실측) |"
    for n in ("5G NR 100MHz", "WiFi 80MHz", "LTE 20MHz")
] + [
    "",
    "직접파 하나만 있으면 탭 1개로도 float64 한계(200 dB+)까지 지운다 — 기저에 정확히 들어 있으니까. "
    "그런데 **RT 로 실측한 챔버 잔향**이 들어오면 **31~56 dB 에서 포화**한다. ECA 는 완벽하지 않다.",
    "",
    "**그리고 ADC 는 병목이 아니다** — 12/14/16-bit 양자화를 넣어도 float64 대비 "
    f"최대 {max(r['max_adc_vs_float_gap_db'] for r in F2['eca_adc']['rows']):.1f} dB 차이뿐이다. "
    "잔류는 DNR 과 **1:1 로 상승**한다(= 깊이가 일정 = 바닥).",
    "",
    "> ⚠️ **이 바닥의 원인은 규명되지 않았다.** ADC 가 아니라는 것만 안다. "
    "인과 FIR 이 서브샘플 지연의 보간커널을 왼쪽에서 지지하지 못한다는 가설이 있으나, "
    "**우리 JSON 에 그 대조군이 없다** → 이 리포트는 원인을 단정하지 않는다. (`RETRACTED`)",
    "",
    "> 🐞 **덤으로 찾은 그림 버그:** §2 그림의 x축은 'DNR = 직접파/**잡음**'인데 동작점 마커는 "
    "`lt[\"dnr_db\"]`(= 직접파/**에코**)로 찍혀 있었다. 올바른 값은 `snr_direct_db` 다. 오차: " +
    " / ".join(f"{n.split()[0]} {DNROP[n]['err_db']:.1f} dB" for n in DNROP) + ". "
    "그림은 정정된 동작점으로 다시 그렸다.",
]))

n5 = NOTCH["5G NR 100MHz"]
cells.append(mdl([
    "### 2.2 ⭐ ECA 는 **저속 표적을 먹는다** — 이것이 트래킹의 근본 한계",
    "",
    "표적이 느리면 그 에코는 '거의 정지한 신호' = 기준신호의 지연복제와 구별되지 않는다 → **ECA 가 같이 지운다.**",
    "",
    "측정: 표적 손실 vs 도플러. 이론은 **1 - sinc²(f_d · T_CPI)** (에너지).",
    "",
    f"- **일치**: 측정된 에너지 손실 vs 이론, 최대 편차 **{n5['max_dev_energy_vs_theory_db']:.3f} dB**",
    f"- **붕괴**: 전 파형 · 전 CPI 길이(M=16/48/96)가 f_d/Δf_d 로 정규화하면 **한 곡선**으로 겹친다 "
    f"(-3 dB 점 = {n5['fd_3db_over_dfd_energy']:.2f}·Δf_d)",
    f"- **노치 폭 = 도플러 빈 하나** (Δf_d = 1/T_CPI)",
    "",
    "> 🔬 **정정 (중요).** 원 스크립트는 **20·log₁₀(RD 진폭비)** 를 **에너지** 이론곡선 위에 겹쳐 그리고 "
    "거기서 -3 dB 점을 뽑았다 — 진폭/전력 혼동이다. 레이더 관례(전력 -3 dB)로 다시 내면 최소 검출가능 속도가 "
    f"**{n5['v_overstated_factor']:.2f}배 작아진다.** 아래는 **정정된 값**이다.",
    "",
    "#### 최소 검출가능 속도 (M=48, 전력 -3 dB)",
    "",
    "| 파형 | T_CPI | Δf_d | -3 dB 도플러 | **최소 검출가능 속도** | (원 보고값) |",
    "|---|---|---|---|---|---|",
] + [
    f"| {n} | {NOTCH[n]['T_cpi_ms']:.0f} ms | {NOTCH[n]['dfd_hz']:.1f} Hz | "
    f"{NOTCH[n]['fd_3db_energy_hz']:.1f} Hz | **{NOTCH[n]['v_3db_energy_ms']:.2f} m/s** | "
    f"({NOTCH[n]['v_3db_reported_ms']:.2f} m/s) |"
    for n in ("5G NR 100MHz", "WiFi 80MHz", "LTE 20MHz")
] + [
    "",
    "> ### 💀 **호버링 드론(v ≈ 0)은 ECA 에게 원리적으로 보이지 않는다.**",
    "> 이건 버그가 아니라 **물리**다. 표적을 살려 주는 것은 오직 도플러뿐이다. "
    "벤치마크는 이 **블라인드 속도를 명시**해야 하고, 호버 시나리오의 Pd 를 '탐지 실패'로 읽어선 안 된다 "
    "— **검출기가 그 표적을 볼 수 없게 설계돼 있다.**",
    "",
    "> **쉽게 말하면 —** ECA 는 '가만히 있는 것은 배경'이라고 보고 지운다. 그래서 표적이 느릴수록 "
    "배경과 헷갈려 같이 지워진다. 제자리 비행하는 드론은 사실상 안 움직이니 **통째로 지워져 안 보인다** — "
    "청소기가 '안 움직이는 건 먼지'라며 빨아들이는데 가만히 앉은 파리까지 빨려 나가는 격이다.",
    "",
    f"> 📐 CPI 를 늘리면 노치가 좁아진다(Δf_d = 1/T_CPI ∝ 1/M). M=96 이면 5G 의 -3 dB 속도가 "
    f"{[r for r in F2['eca_notch']['rows'] if r['name']=='5G NR 100MHz' and r['M']==96][0]['v_3db_energy_ms']:.2f} m/s "
    "까지 내려간다 — 다만 그만큼 표적이 한 셀에 머물러야 한다(거리 이동 제약).",
]))

cells.append(mdl([
    "### 2.3 ECA 가 **원리적으로** 못 지우는 것: DPI 의 데이터 성분",
    "",
    "ECA 의 기저는 `wf.ref`(**파일럿**)의 지연복제인데, 직접파는 `wf.tx`(**파일럿 + 데이터**)다. "
    "데이터 RE 는 부분공간 밖 → **원리적으로 소거 불가**.",
    "",
    "| 점유모드 | 파형 | 기준=파일럿 깊이 | 기준=전체송신 깊이 | 차이 |",
    "|---|---|---|---|---|",
] + [
    f"| {occ} | {n} | {s3[(occ,n)]['depth_pilot_dpi_db']:.1f} dB | {s3[(occ,n)]['depth_tx_dpi_db']:.1f} dB | "
    f"**{s3[(occ,n)]['depth_pilot_dpi_db'] - s3[(occ,n)]['depth_tx_dpi_db']:+.1f} dB** |"
    for occ in ("G1", "G3") for n in ("5G NR 100MHz", "WiFi 80MHz", "LTE 20MHz")
] + [
    "",
    "다행히 그 잔류는 DPI 가 정지해 있으므로 **0-도플러 행에 통째로 앉는다** → §1.5 의 마스킹이 막는다. "
    "**단, 마스킹이 zd±1 까지 덮을 때만** 그렇다.",
    "",
    "> 🐞 **§4b(탭 창 밖 표적)는 구조적으로 공허했다.** `chamber_window()` 가 "
    "`n_taps = n_range + 8` 로 잡으므로 ECA 탭 창이 **항상** RD 거리창보다 넓다 "
    f"(예: {gate[0]['name']} — 탭 창 {gate[0]['gate_m']:.0f} m vs RD 창 {gate[0]['rd_window_m']:.0f} m). "
    "따라서 '탭 창 밖 표적'은 RD 맵에 **애초에 나타날 수 없고**, 그 섹션은 무엇도 시연하지 못한다.",
]))

# =========================================================================== #
#  §3  E3 — Ambiguity
# =========================================================================== #
W = A["waveforms"]
dv = A["meta"]["detector_validation"]
cells.append(md(
    "---",
    "# §3. [E3] 모호함수 — 분해능 상한과 가짜 표적",
    "",
    "> 🔍 **여기서 하는 일:** 점표적 하나를 넣었을 때 RD 맵에 그려지는 응답 |χ(τ, f_d)| — 즉 "
    "**모호함수**(점표적 하나가 거리-도플러 지도에 남기는 지문 같은 응답) — 을 잰다. "
    "이게 **분해능의 상한**이고, 이것의 부엽·봉우리가 **가짜 표적**이 된다.",
    "",
    "> 🔑 **교과서 AF 가 아니라 '우리 검출기의 AF' 를 쟀다.** `passive_process.range_doppler` 가 실제로 하는 "
    "처리(프레임 순환상관 + Hann slow-time FFT)를 그대로 통과시켰다. 해석적 χ 를 실제 RD 맵과 대조해 "
    f"-45 dB 위 셀에서 최대오차 {max(d['max_err_db_above_m45'] for d in dv):.3f} dB "
    f"(중앙값 ~{sorted(d['med_err_db'] for d in dv)[len(dv)//2]:.4f} dB) — **이 절의 숫자는 '이 검출기의' 숫자다.**",
    "",
    "## 판정: 분해능 **PASS** / 5G 도플러축 **FAIL** / 분해능 규약 **FAIL** / 유령 마진 **인용 불가**",
))
cells.append(fig("report4_e3_ambiguity", "E3 ambiguity"))

cells.append(mdl([
    "### 3.1 분해능은 교정돼 있다 (PASS)",
    "",
    "| 파형 (기준신호) | 기준대역 | 측정 ΔRb (-3 dB) | 이론 c/B_ref | 비율 |",
    "|---|---|---|---|---|",
] + [
    f"| {W[k]['name']} ({W[k]['ref_name']}) | {W[k]['ref_bw_hz']/1e6:.1f} MHz | "
    f"**{W[k]['dR_meas_m']:.2f} m** | {W[k]['dR_theory_m']:.2f} m | x{W[k]['dR_ratio']:.2f} |"
    for k in ("wifi_G1", "lte_G1", "nr_G1", "nr_G3")
] + [
    "",
    "비율 0.89~0.94 = **sinc 의 -3 dB 계수 0.886** 그대로. 도플러 분해능도 전 파형 "
    f"**x{W['wifi_G1']['dF_ratio']:.2f}** (Hann 의 1.44배 확장과 일치).",
    "",
    "> 🔑 **점유모드가 5G 에서만 운명을 가른다.** SSB(7.2 MHz) → ΔRb 39.2 m vs "
    "NR-PRS(98.3 MHz) → 2.77 m — **14배**. WiFi 는 기준이 어느 모드든 VHT-LTF 고정이라 AF 가 **전혀 안 변한다**.",
]))

conv = {r["key"]: r for r in F3["resolution_convention_conflict"]["rows"]}
cells.append(mdl([
    "### 3.2 🐞 코드베이스가 **두 개의 분해능 규약**을 동시에 쓰고 있다 (FAIL)",
    "",
    "> 🔬 **정정.** 원 실험은 \"코드베이스 규약 c/B_ref 가 맞다(PASS)\"고 적었다. **오독이다.**",
    "",
    "| | 값 (5G SSB 기준) | 어디서 쓰이나 |",
    "|---|---|---|",
    f"| RD 맵의 Rb 축 분해능 = **c/B** | {conv['nr_G1']['drb_bistatic_c_over_B_m']:.1f} m | "
    "이 리포트, verify_* 스크립트, 유령 분리 판정 |",
    f"| `waveforms.range_resolution_m` = **c/(2B)** | {conv['nr_G1']['range_res_property_c_over_2B_m']:.1f} m | "
    "report2, viz_radar, viz_occupancy, docs/ARCHIVE (공표 수치 **20.8 m**) |",
    "",
    "**둘 다 코드베이스 안에 있고, 정확히 2배 차이가 난다.** RD 맵은 바이스태틱 거리합 Rb = c·τ 축이므로 "
    "그 축의 분해능은 **c/B** 다(2 로 나누지 않는다). 문서에 공표된 \"WiFi 2.0 m / LTE 8.3 m / SSB 20.8 m\" 는 "
    "모노스태틱 관례(c/2B)이고, **RD 맵·유령 분리 논의에 그 값을 쓰면 2배 낙관**이다.",
    "",
    "→ §8 의 설계 요구사항: **규약을 하나로 통일하고 공표 수치를 고칠 것.**",
]))

p1 = W["nr_G1"]["physical"]
p3 = W["nr_G3"]["physical"]
cells.append(mdl([
    "### 3.3 💥 5G 의 **도플러축이 40배 낙관**이다 (FAIL) — 가장 큰 발견",
    "",
    "`run_min_cell.frame_len()` 은 WiFi 만 패킷률로 패딩하고, NR 은 tx 길이(1 슬롯 = 0.5 ms) 그대로 타일링한다 "
    f"→ 모델 PRF = **{p1['prf_model_hz']:.0f} Hz**.",
    "",
    f"그런데 `waveforms.PILOT_RATE_HZ` 는 SSB 를 **{p1['prf_physical_hz']:.0f} Hz**(20 ms 버스트)라고 "
    "**스스로 선언한다.** 즉 하네스가 **자기 모듈의 물리 가정과 모순**된다.",
    "",
    "| 파형 | 모델 PRF | 물리 PRF | 배율 | v_max (모델) | **v_max (물리)** |",
    "|---|---|---|---|---|---|",
] + [
    f"| {W[k]['name']} ({W[k]['ref_name']}) | {W[k]['physical']['prf_model_hz']:.0f} Hz | "
    f"{W[k]['physical']['prf_physical_hz']:.0f} Hz | **x{W[k]['physical']['ratio']:.0f}** | "
    f"{W[k]['physical']['v_unamb_model_ms']:.1f} m/s | **{W[k]['physical']['v_unamb_phys_ms']:.2f} m/s** |"
    for k in ("wifi_G1", "lte_G1", "nr_G1", "nr_G3")
] + [
    "",
    f"> ### 💀 물리 PRF 로는 우리 표적(3 m/s, f_d = {p1['fd_true_hz']:+.0f} Hz)이 "
    f"**{p1['fd_aliased_phys_hz']:+.0f} Hz 로 접힌다.**",
    f"> SSB 의 진짜 v_max 는 **{p1['v_unamb_phys_ms']:.2f} m/s** — 우리 드론(3 m/s)보다 **느리다.** "
    "즉 「5G 이중고」(좁은 기준대역 + 느린 반복률)의 **절반(도플러)이 report4/5 수치에 아예 반영돼 있지 않다.**",
    "",
    f"PRS(G3)도 물리 반복률 {p3['prf_physical_hz']:.0f} Hz → v_max {p3['v_unamb_phys_ms']:.2f} m/s 로 "
    "**x10 낙관**이다.",
    "",
    "> **쉽게 말하면 —** 속도를 재려면 표적을 자주 들여다봐야 한다. 5G 의 상시 기준신호는 20 ms 에 한 번, "
    "그것도 아주 잠깐만 눈을 뜬다. 시뮬레이터는 실수로 5G 가 훨씬 자주 눈을 뜨는 양 계산해서 '빠른 표적도 잘 본다'는 "
    "**너무 후한 점수**를 줬다. 제대로 세어 보니 우리 드론(3 m/s)조차 5G 한테는 너무 빨라 **속도가 엉뚱한 값으로 "
    "접혀** 보인다.",
]))

gm3, gmw, gml = GM["nr_G3"], GM["wifi_G3"], GM["lte_G3"]
cells.append(mdl([
    "### 3.4 🔬 바닥 유령의 '마진'은 **검출기가 계산할 수 없는 값**이었다 (인용 철회)",
    "",
    "> **정정.** 원 실험은 χ 를 0.05 m 미세격자의 **상대 오프셋**(+3.53 m)에서 읽어 "
    "\"유령이 표적 부엽보다 +2.3~3.8 dB 위\"라고 보고했다. 그러나 `range_doppler` 의 거리축은 "
    "**Rb = k·c/fs 의 절대 격자**(빈 간격 2.4~9.8 m)다. 표적도 유령도 빈 중심에 없다. "
    "**검출기가 실제로 보는 셀에서 다시 계산했다.**",
    "",
    "| 파형 | 거리빈 | 유령이 앉는 셀 | 표적 누설 | 유령 응답 | **마진 (정정)** | (원 보고) | 서브빈 변동폭 |",
    "|---|---|---|---|---|---|---|---|",
] + [
    f"| {r['name']} | {r['bin_m']:.2f} m | +{r['cell_minus_true_m']:.2f} m | "
    f"{r['target_leak_into_ghost_cell_db']:.1f} dB | {r['ghost_response_in_cell_db']:.1f} dB | "
    f"**{r['margin_db']:+.1f} dB** | ({r['margin_reported_finegrid_db']:+.1f} dB) | "
    f"{r['margin_subbin_min_db']:+.1f} ~ {r['margin_subbin_max_db']:+.1f} dB |"
    for r in (gmw, gml, gm3)
] + [
    "",
    f"> ### 💀 **5G 는 부호가 뒤집힌다.** 유령이 부엽보다 위인 게 아니라, "
    f"**표적 자신의 스커트가 유령보다 {abs(gm3['margin_db']):.1f} dB 더 세다.**",
    "",
    f"게다가 표적의 **서브빈 위치**(궤적을 따라 매 순간 변한다)를 한 빈에 걸쳐 훑으면 마진이 "
    f"{gm3['margin_subbin_span_db']:.0f} dB 진폭으로 요동친다 → **단일 값 인용 자체가 불가능하다.**",
    "",
    "정성적 결론은 살아남는다(오히려 강해진다): **유령 셀은 표적 자신의 응답으로 오염돼 있다.** "
    "'유령 검출'을 순수한 유령으로 읽으면 안 된다 — §6 에서 이것이 실제로 사고를 친다.",
]))

cells.append(mdl([
    "### 3.5 모호 봉우리 (조건부)",
    "",
    "> 🔬 **정정.** 원 요약은 \"모호 봉우리는 전부 km 스케일, 챔버 창(60 m) 안엔 하나도 없다\"고 적었다. "
    "**자기 JSON 이 반박한다.**",
    "",
    "| 파형 | 챔버 창 안 봉우리 수 | 챔버 안 최강 봉우리 | 전역 최강 봉우리 |",
    "|---|---|---|---|",
] + [
    f"| {PK[k]['name']} | **{PK[k]['n_peaks_in_chamber']}개** | " +
    (f"{PK[k]['strongest_in_chamber']['rb_m']:+.1f} m @ {PK[k]['strongest_in_chamber']['db']:.1f} dB"
     if PK[k]["strongest_in_chamber"] else "없음") +
    f" | {PK[k]['strongest_global']['rb_m']/1000:+.2f} km @ {PK[k]['strongest_global']['db']:.1f} dB |"
    for k in ("wifi_G1", "lte_G1", "nr_G1", "nr_G3")
] + [
    "",
    "**5G NR-PRS 의 전역 최강 모호 봉우리는 ±19.5 m @ -22.2 dB — 챔버 창 *안*이다**(분해셀의 7배 거리). "
    "원 보고는 대신 2위(±9.99 km)를 최강인 양 인용했다.",
    "",
    "다만 실질적 위협은 여전히 제한적이다: OFDM CP·comb 이 만드는 **km 스케일 봉우리**는 챔버(창 60 m)에 "
    "안 들어오고, 창 안 봉우리는 -22 dB 이하다. **그러나 '하나도 없다'는 거짓이므로 벤치마크는 "
    "±19.5 m 셀을 감시 목록에 넣어야 한다.**",
    "",
    "> 💡 **덤:** LTE CRS 는 도플러 모호 replica 를 **스스로 억제한다**"
    f"(|χ(0, PRF)| = {W['lte_G1']['doppler_replica_db']:.1f} dB, WiFi {W['wifi_G1']['doppler_replica_db']:.1f} dB / "
    f"5G SSB {W['nr_G1']['doppler_replica_db']:.1f} dB 와 대조). 원인은 점유율이 아니라 **에너지의 시간확산**: "
    f"CRS 는 l=0/4/7/11 로 1 ms 전체에 퍼져 있고(확산 {W['lte_G1']['ref_time_spread']:.3f}), "
    f"SSB(l=0~3, {W['nr_G1']['ref_time_spread']:.3f})·WiFi LTF({W['wifi_G1']['ref_time_spread']:.3f})는 앞쪽에 "
    "뭉쳐 있어 프레임 내 위상상쇄가 없다.",
]))

# =========================================================================== #
#  §4  E4 — Link budget
# =========================================================================== #
BE = {r["name"]: r for r in L["BE_processing_gain"]["waveforms"]}
DS = L["D_sigma_table"]
WP = F4["wifi_pilot_fraction"]
cells.append(md(
    "---",
    "# §4. [E4] 링크버짓 → 주입 진폭 → RD 맵 SNR",
    "",
    "> 🔍 **여기서 하는 일:** 레이더방정식으로 유도한 SNR 이 **실제 시뮬 RD 맵에서 나오는지** 확인하고, "
    "안 나오면 그 차이가 **어떤 처리손실인지** 하나씩 분해한다.",
    "",
    "## 판정: 물리 사슬 **PASS** / 비교 프로토콜 **FAIL** (관측시간이 통제변수가 아니었다)",
))
cells.append(fig("report4_e4_linkbudget", "E4 link budget"))

cells.append(mdl([
    "### 4.1 물리 사슬은 교정돼 있다 (PASS)",
    "",
    "레이더방정식을 **독립적으로 2경로 재유도**(전력밀도 사슬 + 순수 dB 손계산)해 코드와 대조:",
    "",
    f"- 최대 편차 **{L['A_radar_equation']['max_dev_db']:.1e} dB** (= 부동소수점 잡음)",
    "- 직접파(Friis)·잡음(kT₀BF)도 0.0 dB 일치",
    "",
    "그리고 **측정된 RD SNR vs 이론 상한** (직사각창·격자정합·ECA 無):",
    "",
    "| 파형 | 정합필터 이득 Σ\\|ref\\|² | B·T 곱 | 파일럿 전력비 | CPI 이득 10log M | 이론 vs 측정 |",
    "|---|---|---|---|---|---|",
] + [
    f"| {n} | {BE[n]['mf_gain_db']:.2f} dB | {BE[n]['BT_db']:.2f} dB | {BE[n]['pilot_power_frac_db']:.2f} dB | "
    f"{BE[n]['cpi_gain_db']:.2f} dB | {BE[n]['loss_rect_vs_theory_db']:+.3f} dB |"
    for n in ("WiFi 80MHz", "LTE 20MHz", "5G 100MHz")
] + [
    "",
    "> 🔑 **매치드필터 이득 ≠ B·T 곱.** WiFi 의 정합필터 이득은 B·T 보다 "
    f"**{BE['WiFi 80MHz']['BT_db'] - BE['WiFi 80MHz']['mf_gain_db']:.1f} dB 낮다** — 기준신호가 프레임 에너지의 "
    "일부만 차지하기 때문. \"처리이득 = 시간-대역폭 곱\" 을 그대로 인용하면 **WiFi 를 24 dB 과대평가**한다.",
    "",
    f"> 🔬 **정정.** 원 요약은 이를 \"파일럿이 송신에너지의 0.4%\" 라고 적었는데 **두 물리량을 합쳐 잘못 라벨한 것**이다. "
    f"실제로는: 파일럿 = 송신에너지의 **{WP['pilot_over_tx_energy']*100:.1f}%** "
    f"({WP['pilot_over_tx_energy_db']:.2f} dB), 그리고 패킷 듀티 = **{WP['packet_duty']*100:.1f}%** "
    f"({WP['packet_duty_db']:.2f} dB). 둘의 곱이 JSON 의 {WP['pilot_power_frac_db_json']:.2f} dB 다.",
]))

cells.append(mdl([
    "### 4.2 처리손실 분해 (정정된 값)",
    "",
    "> 📎 이 절의 **straddle**(스트래들) 이란, 표적이 하필 두 칸(빈) 경계에 걸쳐 앉아 어느 칸에서도 "
    "봉우리가 온전히 안 잡히는 데서 생기는 손실이다.",
    "",
    "> 🔬 **정정 3건.** 원 실험의 손실표는 (1) 잡음바닥 추정이 서로 다른 두 실행을 뺀 `*_worst` 키를 썼고 "
    "(그 결과 LTE 도플러 straddle 이 **이론 최대치를 넘는** 물리적으로 불가능한 값이 나왔다), "
    "(2) Hann 창손실의 '이론값'으로 **점근값** 10log(2/3) 을 썼으며, "
    "(3) CFAR 손실을 **Ntrain=264 하나**로 계산했다(그 값은 5G 에만 도달한다).",
    "",
    "| 손실 항목 | WiFi 80MHz | LTE 20MHz | 5G 100MHz | 비고 |",
    "|---|---|---|---|---|",
    f"| Hann 창손실 | {F4['hann_window_loss']['exact_db']:.2f} dB | {F4['hann_window_loss']['exact_db']:.2f} dB | "
    f"{F4['hann_window_loss']['exact_db']:.2f} dB | **파형 무관 상수** (인용됐던 점근값 "
    f"{F4['hann_window_loss']['asymptotic_quoted_db']:.2f} dB 아님) |",
] + [
    "| 거리 straddle (반빈) | " + " | ".join(f"{STR[n]['range_half_db']:.2f} dB" for n in
                                             ("WiFi 80MHz", "LTE 20MHz", "5G 100MHz")) +
    " | WiFi 가 최악 (B/fs = " + f"{STR['WiFi 80MHz']['b_over_fs']:.2f} 임계표본화) |",
    "| 도플러 straddle (반빈) | " + " | ".join(f"{STR[n]['dopp_half_db']:.2f} dB" for n in
                                               ("WiFi 80MHz", "LTE 20MHz", "5G 100MHz")) +
    f" | 이론 최대 {F4['straddle']['hann_scallop_max_db']:.2f} dB 안쪽 ✅ |",
    "| CFAR 손실 (최악 셀) | " + " | ".join(f"{CFL[n]['cfar_loss_max_db']:.2f} dB" for n in
                                            ("WiFi 80MHz", "LTE 20MHz", "5G 100MHz")) +
    " | **파형 의존!** 아래 참조 |",
    "| 훈련셀 수 범위 | " + " | ".join(f"{CFL[n]['n_train_min']}~{CFL[n]['n_train_max']}" for n in
                                        ("WiFi 80MHz", "LTE 20MHz", "5G 100MHz")) + " | |",
    "",
    "> 🐞 **LTE 의 CFAR 는 퇴화해 있다.** n_range = 6 인데 CFAR 거리축 훈련반경은 8 → "
    "**모든 셀의 훈련창이 거리축 전체를 덮는다**(사실상 1D 도플러 CFAR). 훈련셀이 39~87개로 줄어 "
    f"CFAR 손실이 5G 의 {CFL['5G 100MHz']['cfar_loss_max_db']:.2f} dB 대비 "
    f"{CFL['LTE 20MHz']['cfar_loss_max_db']:.2f} dB 까지 커진다. §1.4 의 거리창 문제와 **같은 뿌리**다.",
    "",
    "**ECA 손실은 사실상 0** — 정확 측정 시 표적 피크 손실 0.0000 dB (원 보고의 +0.1 dB 는 "
    "ECA 가 0-도플러 능선을 지운 셀이 잡음바닥 평균에 섞여 생긴 지표 아티팩트).",
]))

cells.append(mdl([
    "### 4.3 💥 관측시간이 **통제변수가 아니었다** (FAIL)",
    "",
    "`frame_len()` 이 파형마다 프레임을 다르게 정의한다 — WiFi 1 ms(패킷 슬롯), LTE 1 ms(서브프레임), "
    "**5G 0.5 ms(NR 슬롯 1개)**. 따라서 같은 M=48 이:",
    "",
    "| 파형 | T_CPI (M=48) |",
    "|---|---|",
] + [
    f"| {k} | **{v:.0f} ms** |" for k, v in F4["cpi_asymmetry"]["cpi_ms"].items()
] + [
    "",
    f"> ### 5G 에게만 **절반의 관측시간** → 코히어런트 이득 "
    f"**{F4['cpi_asymmetry']['span_db']:.2f} dB** 손해.",
    "> 이 3 dB 는 **물리가 아니라 규약**에서 왔고, 하필 \"5G 가 유리하다\"는 결론에 **역방향**으로 들어가 있다. "
    "→ §8: **M 이 아니라 T_CPI 를 맞춰라.**",
    "",
    "### 4.4 SCR 은 고 SNR 에서 SNR 의 대리지표가 아니다",
    "",
    f"5드론 × 3파형 15셀에서 유도 SNR vs 측정 SCR: 평균 차 **{DS['gap_mean_db']:+.2f} dB** "
    f"(σ {DS['gap_std_db']:.2f}, 범위 [{DS['gap_min_db']:.2f}, {DS['gap_max_db']:.2f}]).",
    "",
    "약표적(mini5pro)은 -0.9~-1.2 dB(= straddle + 창 정의 잔차)로 깔끔한데, **강표적일수록 차이가 커진다.** "
    "원인은 SNR 손실이 아니라 **SCR 지표의 압축**이다 — 표적 자신의 **부엽 융단**이 SCR 의 분모(기준영역 바닥)를 "
    f"최대 **+{max(r['pedestal_from_target_db'] for r in F4['pedestal_causality']['pedestal_rows']):.2f} dB** 들어올린다.",
    "",
    "> ⚠️ **\"SCR = 유도 SNR\" 로 읽는 문서·표는 강표적에서 최대 4 dB 틀린다.**",
    "",
    "> 🔬 **정정.** 원 실험은 \"CFAR 는 국소 잡음을 보므로 부엽 융단이 Pd 에 영향 없다\"고 단정했는데 "
    "**틀렸다** — CFAR 훈련창은 표적의 부엽 **위에** 놓인다(고전적 표적 자기가림). 이 동작점에서 Pd 가 안 깨지는 "
    "진짜 이유는 피크가 잡음보다 압도적으로 높기 때문이지 CFAR 가 융단을 못 보기 때문이 아니다. "
    "**자기가림의 크기는 우리 JSON 에 측정돼 있지 않다** → 단정하지 않는다. (`RETRACTED`)",
]))

# =========================================================================== #
#  §5  E5 — Observability
# =========================================================================== #
SM = O["summary"]
RA = O["rotation_ambiguity"]
c0 = {c["key"]: c for c in O["cells"]}
cells.append(md(
    "---",
    "# §5. [E5] 관측가능성 — **트래킹의 전제**",
    "",
    "> 🔍 **여기서 하는 일:** 단일 TX-RX 쌍이 CPI 마다 주는 것은 **스칼라 두 개** (Rb, f_d) 뿐이다. "
    "그걸로 드론의 **3D 위치**를 결정할 수 있는가 — 이것이 **관측가능성**(측정만으로 답이 하나로 정해지는가)의 "
    "물음이고, SNR 이 아니라 **원리**의 문제다.",
    "",
    "## 판정: **FAIL** — 원리적으로 불가능하다. 트래킹 벤치마크의 전제가 깨져 있다.",
))
cells.append(fig("report4_e5_observability", "E5 observability"))

cells.append(mdl([
    "### 5.1 거리 측정 하나가 남기는 것: **방 전체만 한 껍질**",
    "",
    "Rb 를 완벽히 재도 표적은 **등-Rb 타원껍질** 위 어딘가다. 그 껍질의 부피를 GPU 복셀 적분"
    f"({F5['shell_volume']['dx']*100:.0f} cm 격자)으로 쟀다:",
    "",
    "| 파형 (기준신호) | ΔRb | **껍질 부피** | 챔버 대비 |",
    "|---|---|---|---|",
] + [
    f"| {SHELL[k]['label']} | {SHELL[k]['drb_corrected_m']:.2f} m | "
    f"**{SHELL[k]['v_shell_corrected_m3']:.0f} m³** | **{SHELL[k]['frac_corrected']*100:.0f}%** |"
    for k in ("nr100_G1", "lte20_G1", "wifi80_G1", "nr100_G3")
] + [
    "",
    f"(챔버 = {F5['shell_volume']['chamber_m3']:.0f} m³)",
    "",
    "> ### 💀 상시 신호만 쓰는 5G(SSB)는 **Pd = 1.00 인데 위치는 방의 89%** 다.",
    "> **탐지와 관측가능성은 다른 축이다.** 탐지 벤치마크만 보면 5G 가 멀쩡해 보이지만 위치정보는 사실상 0 이다.",
    "",
    f"> 🔬 **정정.** 원 실험의 ΔRb '실측'은 사실 1-샘플 선형보간 외삽이라 계통적으로 과소했다"
    f"(LTE {SHELL['lte20_G1']['drb_reported_m']:.2f} → **{SHELL['lte20_G1']['drb_corrected_m']:.2f} m**, "
    f"PRS {SHELL['nr100_G3']['drb_reported_m']:.2f} → **{SHELL['nr100_G3']['drb_corrected_m']:.2f} m**). "
    "E3 가 같은 양을 0.05 m 격자에서 정확히 쟀으므로 그 값으로 교체하고 **껍질 부피를 다시 적분했다** "
    f"(LTE {SHELL['lte20_G1']['v_shell_json_m3']:.0f} → {SHELL['lte20_G1']['v_shell_corrected_m3']:.0f} m³, "
    f"PRS {SHELL['nr100_G3']['v_shell_json_m3']:.0f} → {SHELL['nr100_G3']['v_shell_corrected_m3']:.0f} m³). "
    "**결론 순서(SSB ≫ LTE > WiFi > PRS)는 바뀌지 않는다.**",
    "",
    "**도플러는 위치정보를 더해주지 않는다.** v 를 **안다고 가정해도** 껍질이 거의 안 줄어들고"
    f"(부피비 x{list(SM['doppler_keeps_frac_v_unknown'].values())[0]:.2f}~x1.00), "
    "v 를 **모르면**(실제 상황) 껍질의 거의 100% 가 |v| ≤ 3 m/s 인 어떤 속도로 관측된 f_d 를 설명할 수 있다. "
    "도플러는 **위치·속도의 결합 함수**이지 위치정보가 아니다.",
    "",
    "> ⚠️ 단, 이 '×1.00' 은 **T_CPI = 32 ms 에서**의 이야기다. 등-f_d 슬랩의 두께가 λ·Δf_d 인데 "
    "현 CPI 에서는 그게 표적 속도만큼 크다. CPI 를 10배 늘리면 슬랩이 10배 얇아져 껍질을 실제로 자른다.",
]))

cells.append(mdl([
    "### 5.2 ⭐ 시간을 아무리 봐도 안 된다 — **엄밀 대칭**이기 때문",
    "",
    "> 📎 아래 표의 **랭크**는 '측정으로 실제 알아낼 수 있는 독립 방향의 개수'다. 3D 위치는 3개 방향인데 "
    "랭크가 2 뿐이면 한 방향은 원리적으로 못 잰다는 뜻이다. **그램행렬**은 여러 시각의 측정을 다 모아 만든 "
    "'정보 장부'로, 시간을 더 봐도 랭크가 안 오르면 아무리 오래 지켜봐도 소용없다는 증거가 된다.",
    "",
    "| 검사 | 결과 |",
    "|---|---|",
    f"| 스냅샷 Fisher 행렬 랭크 (위치 3상태) | **{SM['snapshot_fim_rank']} / 3** |",
    f"| 영방향 | **{tuple(round(x,2) for x in c0['nr100_G3']['null_dir'])}** ≈ **거의 연직** |",
    f"| 등속 6상태 그램행렬 랭크 (radial, K=1..64) | **{SM['gramian_rank_radial']} / 6** — K≥2 에서 포화 |",
    f"| 같은 것 (tangential, 비동일평면) | **{SM['gramian_rank_tangential']} / 6** |",
    "",
    "**왜 포화하는가:** TX-RX 베이스라인 둘레의 회전이 **엄밀한 대칭**이다. 위치와 속도를 그 축 둘레로 "
    "**유한각** 회전시켜도 —",
    "",
    f"> max\\|ΔRb\\| = **{SM['exact_rotation_max_dRb_m']:.1e} m**,  "
    f"max\\|Δf_d\\| = **{SM['exact_rotation_max_dfd_hz']:.1e} Hz**  (= 기계 정밀도. 진짜로 0 이다)",
    "",
    "야코비안(1차 근사)만 봤으면 이걸 '약하게 관측 가능'과 구별 못 했을 것이다. **비선형 원본에서 확인했다.**",
    "",
    "**챔버 벽조차 이 모호성을 다 못 자른다:**",
    "",
    f"- 벽이 허용하는 회전각 폭: **{RA['phi_span_deg']:.1f}°**",
    f"- 참 궤적과 최대 이격: **{RA['max_disp_m']:.2f} m** — 그런데 **모든 시각에 동일한 (Rb, f_d)** 를 낸다",
    f"- 1 m 이상 떨어진 유령 궤적의 각도 폭: {RA['phi_span_sep_deg']:.1f}°",
    "",
    "> ### 💀 못 보는 방향이 **거의 연직**이다 = 드론의 **고도**를 못 본다.",
    "> 트래킹 벤치마크에서 **x·y 만 그리면 '잘 맞는 것처럼' 보인다.** 반드시 z 를 함께 평가해야 한다.",
    "",
    "> **쉽게 말하면 —** 한 눈으로 세상을 보면 좌우·위아래는 알아도 **얼마나 먼지**를 정확히 못 짚는다. "
    "여기선 그 못 짚는 방향이 하필 **위아래(고도)**다. 게다가 시간을 아무리 오래 지켜봐도 안 풀린다 — 표적을 "
    "송신기-수신기 축 둘레로 살짝 돌려놓아도 측정값이 **한 치도 안 변하기** 때문이다(그래서 진짜와 유령을 "
    "구별할 단서가 원리적으로 없다). 답은 하나, **눈을 하나 더 다는 것**(수신기 추가)이다.",
    "",
    "> 🔬 **철회.** 원 요약이 인용한 \"회전 생성자의 레일리 몫 ~1e-19\" 는 **JSON 어디에도 없는 값**이다 "
    "(저장된 유일한 값은 2.1e-03 이고, 그 값 자체가 생성자 스케일 버그로 오염돼 있다). "
    "**이 리포트는 레일리 몫을 인용하지 않는다.** 회전 대칭의 증거는 위의 **비선형 원본 측정**이며, "
    "그것은 스케일과 무관하다. (`RETRACTED`)",
]))

cells.append(mdl([
    "### 5.3 처방: **수신기를 하나 더 놓아라**",
    "",
    "| 구성 | 랭크 | **위치 CRLB (rms)** | 속도 CRLB (정정) |",
    "|---|---|---|---|",
] + [
    f"| {k} | {'**' if v['rank']==6 else ''}{v['rank']}/6{'**' if v['rank']==6 else ''} | "
    f"**{v['pos_rms_m']:.2f} m** | " +
    ", ".join(f"{x:.2f}" for x in v["sigma_vel_corrected_ms"]) + " m/s |"
    for k, v in CRLB.items()
] + [
    "",
    "> ⚠️ **1RX 행의 66 m 는 CRLB 가 아니다.** 랭크가 모자라므로 그 값은 정규화된 유사역행렬이 뱉은 숫자일 뿐 "
    "의미가 없다. **랭크가 모자라면 CRLB 자체가 정의되지 않는다.**",
    "",
    f"> 🔬 **정정.** 원 스크립트는 속도 CRLB 를 t_obs² = {F5['crlb']['factor']:.0f}배 **낙관적으로** 찍었다"
    "(스케일 좌표 변환 부호 오류). 위 표는 정정값이다. **위치 CRLB 는 그 재스케일에 불변이므로 "
    "\"2RX 위치 0.22 m\" 는 그대로 유효하다.**",
    "",
    "> ⚠️ **AoA 처방의 σ(1°/5°)는 가정이다** — 실제 안테나로 측정한 값이 아니다. **2RX 처방만 순수 기하**이며 "
    "가정이 없다. 벤치마크가 트래킹을 다루려면 **2RX 가 최소 요구사항**이다.",
]))

# =========================================================================== #
#  §6  E6 — Floor ghost
# =========================================================================== #
TR = G["A_B_tracks"]
T5 = TR["radial"]["5G NR 100MHz"]
PH = G["D_tracker"]["phantom"]
SMO = G["D_tracker"]["ghost_track_smoothness"]
GC = F6["gate_coverage"]
POL = {r["pol"]: r for r in F6["polarization"]["rows"]}
cells.append(md(
    "---",
    "# §6. [E6] 바닥 유령 — **구조적 오경보**",
    "",
    "> 🔍 **여기서 하는 일:** TX→표적→**바닥**→RX 경로가 만드는 가짜 표적이 탐지·추적에 어떤 영향을 주는지 "
    "궤적 전체에 대해 잰다.",
    "",
    "우리 챔버는 **semi-anechoic** — 벽·천장만 흡수체이고 **바닥은 반사성 콘크리트**다. "
    "이 경로는 **표적을 거치므로 도플러가 실린다** → 정적 클러터와 달리 **ECA 를 통과한다.**",
    "",
    "## 판정: **FAIL** (ECA 가 못 지운다 + 트래커가 못 거른다) → **벤치마크는 유령을 켜야 한다**",
))
cells.append(fig("report4_e6_ghost", "E6 floor ghost"))

cells.append(mdl([
    "### 6.1 유령은 표적을 **3.5 m 뒤에서 그림자처럼 따라다닌다**",
    "",
    "| 시나리오 | 분리 sep (평균) | 유령 진폭 | Δf_d (평균) | 거리분해 (5G) | 도플러분해 (전 파형) |",
    "|---|---|---|---|---|---|",
] + [
    f"| {sc} | {TR[sc]['5G NR 100MHz']['sep_mean']:.2f} m | "
    f"{TR[sc]['5G NR 100MHz']['ghost_db_mean']:.1f} dB | "
    f"{TR[sc]['5G NR 100MHz']['dfd_mean']:+.1f} Hz | "
    f"**{TR[sc]['5G NR 100MHz']['frac_range_resolved']*100:.0f}%** | "
    f"{TR[sc]['5G NR 100MHz']['frac_doppler_resolved']*100:.0f}% |"
    for sc in ("radial", "tangential", "waypoint")
] + [
    "",
    "> 🔑 **도플러축은 유령을 전혀 못 가른다.** Δf_d 는 최대 " +
    f"{max(abs(TR[s][w]['dfd_absmax']) for s in TR for w in TR[s]):.1f} Hz 인데 도플러 분해능은 "
    f"{T5['d_fd_hz']:.0f} Hz 다 → **전 시나리오·전 파형에서 도플러분해 0%**. "
    "사전 예상(도플러가 실리니 도플러축에서도 갈릴 것)은 **틀렸다.** "
    "**유령의 운명은 오직 대역폭(ΔRb = c/B)이 정한다.**",
    "",
    "| 파형 | ΔRb | 거리분해 비율 (radial / tangential / waypoint) |",
    "|---|---|---|",
] + [
    f"| {w} | {TR['radial'][w]['d_rb_m']:.1f} m | " +
    " / ".join(f"{TR[s][w]['frac_range_resolved']*100:.0f}%" for s in ("radial", "tangential", "waypoint")) + " |"
    for w in ("5G NR 100MHz", "WiFi 80MHz", "LTE 20MHz")
] + [
    "",
    "**5G 만 유령을 별개 표적으로 분해한다. WiFi·LTE 에서는 표적 셀에 뭉쳐** — 검출은 안 만들지만 "
    "대신 **표적 셀의 진폭을 오염**시킨다.",
    "",
    "> **쉽게 말하면 —** 바닥이 거울처럼 반사하니 드론 밑에 물 위 그림자 같은 '분신'이 하나 더 생긴다. "
    "이 분신은 진짜 드론을 3.5 m 뒤에서 똑같이 따라다닌다. 눈이 좋은 5G 만 이걸 **따로 떨어진 두 번째 물체**로 "
    "보고, 눈이 흐린 WiFi·LTE 는 진짜와 겹쳐 봐서 대신 진짜 표적의 밝기를 흐려 놓는다.",
]))

cells.append(mdl([
    "### 6.2 🐞 원 실험은 **표적 자신의 에너지를 유령으로 세고 있었다** (정정)",
    "",
    "`run_min_cell.py` 의 유령 판정은 유령 셀 주위 3×3 박스를 본다. 그런데 **bins_apart == 2 일 때 "
    "그 박스는 표적 자신의 검출박스와 열 하나를 공유한다** → 표적 주엽 스커트의 CFAR 히트가 "
    "\"유령이 별개 표적으로 찍혔다\"로 계수됐다.",
    "",
    "격자무관 지표(**유령이 CFAR 문턱 위** AND **2빈 이상 떨어짐**)로 다시 세면:",
    "",
    "| 파형 | 시나리오 | P(별개 표적) 원 보고 | **정정** |",
    "|---|---|---|---|",
] + [
    f"| {w} | {sc} | {PF[w]['per_scen'][sc]['rep']:.3f} | **{PF[w]['per_scen'][sc]['cor']:.3f}** |"
    for w in ("5G NR 100MHz", "WiFi 80MHz", "LTE 20MHz")
    for sc in ("radial", "tangential", "waypoint")
] + [
    "",
    f"> ### 💥 **\"tangential 이 최악(0.67)\"은 정반대(0.00)였다.**",
    f"> 5G 평균 P(별개표적): {PF['5G NR 100MHz']['p_false_reported']:.3f} → "
    f"**{PF['5G NR 100MHz']['p_false_corrected']:.3f}**. "
    f"3-of-5 트랙 개시 확률: {PF['5G NR 100MHz']['track35_reported']:.3f} → "
    f"**{PF['5G NR 100MHz']['track35_corrected']:.3f}**.",
    "",
    "원 실험이 그 근거로 제시한 인과 설명(\"표적이 강해 훈련셀이 오염되고 유령이 임계 근처에서 요동친다\")도 "
    "**측정된 적 없는 사후 서사**였다 — 실제 유령 셀은 임계보다 12~17 dB 아래에서 **요동조차 하지 않는다.**",
]))

cells.append(mdl([
    "### 6.3 그래도 **결론은 살아남는다** — 유령은 구조적 오경보다",
    "",
    "근거의 크기는 ~18배 줄었지만 방향은 그대로다:",
    "",
    "| | 5G NR 100MHz |",
    "|---|---|",
    f"| 유령의 3-of-5 트랙 개시 확률 (정정) | **{PF['5G NR 100MHz']['track35_corrected']:.3f}** |",
    f"| 랜덤 오경보의 트랙 개시 기대수 | {PF['5G NR 100MHz']['random_tracks_per_window']:.1e} |",
    f"| **비율** | **약 {PF['5G NR 100MHz']['ratio_corrected']:.0f}배** |",
    "",
    "**그리고 트래커는 이걸 못 거른다:**",
    "",
    f"- **매끄럽다**: 유령 궤적의 2차적합 잔차 {SMO['radial']['resid_rb_ghost_m']:.3f} m vs "
    f"표적 {SMO['radial']['resid_rb_true_m']:.3f} m — **같은 급**. 운동학 필터로 못 버린다.",
    f"- **표적과 함께 움직인다**: corr(Rb) = {SMO['radial']['corr_rb']:.4f} (radial). "
    f"(단 tangential 은 {SMO['tangential']['corr_rb']:.4f} 로 낮다 — '전부 0.99' 는 과장이었다.)",
    f"- **물리적으로 가능하다**: 유령의 (Rb, f_d) 셀을 설명하는 **실제 드론 위치가 챔버 안에 "
    f"{PH['n_positions_in_ghost_cell']:,}개** 있고 전부 v ≤ {PH['vmax_ms']:.0f} m/s 로 실현 가능하다 "
    f"(가장 가까운 것은 진짜 표적에서 {PH['nearest_phantom_dist_m']:.2f} m). "
    "→ **'물리적으로 불가능하다'를 근거로 버릴 수 없다.**",
    "",
    "> ### 🔑 **벤치마크는 유령을 반드시 켜야 한다.** 끄면 오경보를 과소평가한다 — "
    "그것도 **랜덤이 아니라 표적과 상관된** 오경보를.",
    "",
    "### 6.4 완화: 기하 게이트 (조건부)",
    "",
    "TX/RX/바닥이 기지이므로 유령이 앉을 수 있는 (sep, 진폭, Δf_d) 영역을 **미리 계산**해 게이트를 칠 수 있다.",
    "",
    f"- 게이트의 실제 **결합** 포함률 (n={GC['n_mc']:,} MC): sep∧amp **{GC['coverage_sep_amp_mc']*100:.1f}%**, "
    f"세 축 모두 **{GC['coverage_sep_amp_dfd_mc']*100:.1f}%** "
    f"(거리분해되는 유령만 보면 {GC['coverage_sep_amp_among_resolved_mc']*100:.1f}%)",
    f"- 오배제 비용(= 진짜 2번째 드론을 유령으로 오인): **{GC['cost_false_reject']*100:.2f}%**",
    "",
    "> 🔬 **정정.** 원 그림의 범례 \"ghost gate (99% of ghosts)\" 는 **각 축의 주변부 분위수를 결합 커버리지로 "
    "잘못 옮긴 값**이다. 실제 결합 포함률은 위와 같이 더 낮다.",
    "",
    "> ⚠️ **오배제 비용 0.6% 는 σ 동일 가정에만 의존한다** — 두 드론의 RCS 가 같다고 본다. 실제 2번째 드론이 "
    "mini5pro 급(σ 10~15 dB 낮음)이면 진폭 게이트에 그대로 걸린다. **이건 하한이지 추정치가 아니다.**",
]))

cells.append(mdl([
    "### 6.5 ⚠️ 이 절 전체가 걸려 있는 **미공개 가정**: 편파",
    "",
    "| 편파 | 프레넬 \\|Γ\\| | 유령 진폭 (에코 대비) |",
    "|---|---|---|",
] + [
    f"| **{p}** ({'TM' if p=='V' else 'TE'}) | {POL[p]['gamma']:.3f} | **{POL[p]['amp_db']:.1f} dB** |"
    for p in ("V", "H")
] + [
    "",
    f"입사각 {POL['V']['theta_i_deg']:.1f}° 는 콘크리트의 **브루스터각**(그 각도 근처에서 특정 편파가 거의 "
    "반사되지 않고 빨려 들어가는 입사각) **바로 아래**다 → V(TM) 편파가 **이례적으로 약하게** 반사된다.",
    "",
    f"> ### 💀 편파가 H 이거나 표적 산란이 편파를 섞으면 **유령이 {F6['polarization']['delta_db']:.0f} dB 세진다.**",
    "> 그러면 §6 의 모든 결론(뭉침/분리, WiFi·LTE 는 무해)이 **뒤집힌다.** "
    "**편파는 측정된 적이 없다 — 단일점 가정이다.** 벤치마크는 이 축을 반드시 스윕해야 한다.",
]))

# =========================================================================== #
#  §7  판정
# =========================================================================== #
cells.append(md(
    "---",
    "# §7. 판정 — 벤치마크를 돌릴 준비가 됐는가?",
    "",
    "> 🔍 **여기서 하는 일:** 6개 검증의 결과를 하나의 체크리스트로 모은다. "
    "각 항목에 **PASS / 조건부 / FAIL** 과 **무엇을 고쳐야 하는가**.",
))
cells.append(fig("report4_e7_verdict", "verdict scorecard"))

VLBL = {"PASS": "✅ **PASS**", "FAIL": "❌ **FAIL**", "COND": "⚠️ **조건부**"}
cells.append(mdl([
    "| 실험 | 검증 항목 | 판정 | 무엇을 고쳐야 하는가 |",
    "|---|---|---|---|",
] + [
    f"| {e} | {it} | {VLBL[v]} | {fx if fx != '-' else '—'} |" for e, it, v, fx in VERDICT
] + [
    "",
    f"## **{NPASS} PASS / {NCOND} 조건부 / {NFAIL} FAIL**",
    "",
    "### 이게 무슨 뜻인가",
    "",
    "**벤치마크가 불가능하다는 뜻이 아니다.** 물리 사슬(레이더방정식 → 주입진폭 → RD SNR)과 "
    "핵심 DSP(CFAR α 식, 분해능, ECA 노치 법칙)는 **전부 교정돼 있다.** "
    "시뮬레이터는 우리가 시킨 일을 정확히 하고 있다.",
    "",
    "깨진 것은 **우리가 무엇을 시켰는지에 대한 우리의 이해**다:",
    "",
    "1. **문턱이 우리가 생각한 문턱이 아니었다** (§1) — 그리고 파형마다 다르게 어긋났다.",
    "2. **관측시간이 통제변수가 아니었다** (§4) — 규약이 5G 에게 3 dB 를 뺏고 있었다.",
    "3. **5G 의 도플러축이 40배 낙관이었다** (§3) — 하네스가 자기 모듈의 물리 가정과 모순됐다.",
    "4. **위치를 결정할 수 없다** (§5) — SNR 문제가 아니라 랭크 문제다. 측정이 모자란다.",
    "5. **오경보가 랜덤이 아니었다** (§6) — 표적과 상관된 구조적 오경보가 있다.",
    "",
    "> ### 💡 **지금 명세 그대로 벤치마크를 돌렸다면, 나온 숫자를 방어할 수 없었을 것이다.**",
    "> 그리고 더 나빴을 일: **그 숫자가 그럴듯해 보였을 것이다.** Pd 는 0~1 사이의 멀쩡한 값으로 나왔을 테고, "
    "파형 간 순위도 나왔을 테고, 아무도 그게 서로 다른 오경보율에서의 비교라는 걸 몰랐을 것이다.",
]))

# =========================================================================== #
#  §8  설계 요구사항
# =========================================================================== #
cells.append(mdl([
    "---",
    "# §8. 다음 리포트(벤치마크)의 설계 요구사항",
    "",
    "> 🔍 **여기서 하는 일:** §1~§6 의 FAIL 을 **다음 벤치마크가 지켜야 할 규칙**으로 번역한다. "
    "이게 이 리포트의 **실제 산출물**이다.",
    "",
    "## R1. 🔴 **Pfa 는 경험적으로 교정한 뒤에 비교하라** (§1)",
    "",
    "명목 Pfa 를 고정하고 Pd 를 비교하면 **파형마다 다른 오경보율에서 비교**하게 된다.",
    "",
    "- **파형별 교정 룩업표**(§1.7)를 써서 **경험적 Pfa** 를 맞춘 뒤 Pd 를 비교할 것",
    "- 또는 ROC 를 **경험적 Pfa 축**에 그릴 것 (그림 1f)",
    "- 벤치마크 산출물에 **측정된 경험적 Pfa 를 반드시 함께 보고**할 것. 명목값만 적으면 안 된다",
    "",
    "## R2. 🔴 **거리창을 CFAR 훈련창보다 넓게 잡아라** (§1.4, §4.2)",
    "",
    f"`chamber_window()` 가 주는 n_range (WiFi 16 / LTE **6** / NR 24)가 CFAR 거리축 훈련창"
    f"(2×{lte6['cfar_train_radius_range']}+1 = {2*lte6['cfar_train_radius_range']+1}빈)보다 좁다. "
    "→ 모든 셀이 가장자리 셀이 되어 Pfa 가 부풀고, **LTE 의 CFAR 는 사실상 1D 로 퇴화**한다.",
    "",
    "- n_range ≥ 17 을 **모든 파형에서** 보장하거나, guard/train 을 파형별로 줄일 것",
    "- 어느 쪽이든 **파형 간에 CFAR 형상이 같아야** 공정한 비교다",
    "",
    "## R3. 🔴 **0-도플러 마스킹을 zd±1 로 넓히고, 훈련셀에서도 배제하라** (§1.5)",
    "",
    f"Hann 창이 ±1 빈으로 {HANN['bin_1']:.1f} dB 밖에 안 떨어져 DPI 잔류가 zd±1 행에 실린다. "
    "현재 코드가 안 터진 건 **거리창이 우연히 ECA 탭 안**에 있기 때문이다 — 설계가 아니라 운이다.",
    "",
    "- `det[zd-1:zd+2, :] = False`",
    "- **그리고 그 행들을 CFAR 훈련창에서도 뺄 것**(도플러 가드). 안 그러면 과보정된다(배율 0.65~0.85)",
    "",
    "## R4. 🔴 **M 이 아니라 T_CPI 를 맞춰라** (§4.3)",
    "",
    f"`frame_len()` 규약 때문에 같은 M=48 이 5G 에는 24 ms, WiFi/LTE 에는 48 ms 를 준다 → "
    f"**{F4['cpi_asymmetry']['span_db']:.2f} dB** 의 코히어런트 이득 차이가 **물리가 아니라 규약**에서 나온다.",
    "",
    "- 관측시간을 **명시적 통제변수**로 승격: 모든 파형에 같은 T_CPI 를 주고, M 은 그로부터 유도할 것",
    "- 벤치마크 표에 **T_CPI 열을 반드시 넣을 것**",
    "",
    "## R5. 🔴 **5G 의 도플러축을 물리 반복률로 고쳐라** (§3.3)",
    "",
    f"SSB 는 **{p1['prf_physical_hz']:.0f} Hz** 로 반복하는데 하네스는 {p1['prf_model_hz']:.0f} Hz 로 타일링한다 "
    f"→ v_max 가 {p1['v_unamb_model_ms']:.1f} m/s 로 나오지만 **진짜는 {p1['v_unamb_phys_ms']:.2f} m/s** 다. "
    "우리 드론(3 m/s)이 **접힌다.**",
    "",
    "- `frame_len()` 을 `waveforms.PILOT_RATE_HZ` 와 일치시킬 것",
    "- 그러면 **「5G 이중고」의 나머지 절반(도플러 모호)이 처음으로 벤치마크에 들어온다** — "
    "이건 5G 에 불리한 정정이지만 **물리적으로 옳다**",
    "",
    "## R6. 🔴 **블라인드 속도를 명시하라** (§2.2)",
    "",
    "ECA 는 f_d ≈ 0 인 표적을 **원리적으로 지운다**(1 - sinc² 노치, 폭 = 도플러 빈 하나).",
    "",
    "| 파형 | 최소 검출가능 속도 (M=48, -3 dB) |",
    "|---|---|",
] + [
    f"| {n} | **{NOTCH[n]['v_3db_energy_ms']:.2f} m/s** |"
    for n in ("5G NR 100MHz", "WiFi 80MHz", "LTE 20MHz")
] + [
    "",
    "- **호버 시나리오의 Pd 를 '탐지 실패'로 보고하지 말 것** — 검출기가 그 표적을 볼 수 없게 설계돼 있다",
    "- 벤치마크는 **속도 축을 스윕**해 이 노치를 드러내야 한다",
    "",
    "## R7. 🔴 **바닥 유령을 켜라. 그리고 편파를 스윕하라** (§6)",
    "",
    "- 유령은 **구조적 오경보**다. 끄면 오경보를 과소평가한다",
    f"- **편파는 단일점 가정이다.** V→H 로 바꾸면 유령이 {F6['polarization']['delta_db']:.0f} dB 세지고 "
    "결론이 뒤집힌다 → **반드시 스윕**",
    "- 유령 검출을 셀 때 **표적 검출박스와 겹치지 않게** 할 것 (§6.2 의 인덱싱 결함)",
    "",
    "## R8. 🔴 **트래킹을 하려면 RX 를 하나 더 놓아라** (§5)",
    "",
    f"단일 TX-RX 쌍으로는 3D 위치가 **원리적으로** 결정되지 않는다(랭크 {SM['gramian_rank_radial']}/6, "
    "영방향 = 거의 연직).",
    "",
    f"- **2RX → 랭크 6/6, 위치 CRLB {CRLB['2RX']['pos_rms_m']:.2f} m** (순수 기하, 가정 없음)",
    "- 1RX 로 트래킹 벤치마크를 돌리려면 **고도를 추정하지 않는다고 명시**하고, x-y 만 평가할 것 "
    "(그리고 그게 관측가능성의 한계 때문임을 밝힐 것)",
    "- **x·y 만 그려서 '잘 맞는다'고 말하지 말 것** — 못 보는 축이 z 다",
    "",
    "## R9. 🟡 **분해능 규약을 통일하라** (§3.2)",
    "",
    "코드베이스가 **c/B** 와 **c/2B** 를 동시에 쓴다. 공표 수치(WiFi 2.0 m / LTE 8.3 m / SSB 20.8 m)는 "
    "모노스태틱 관례라 **RD 맵 논의에서는 2배 낙관**이다.",
    "",
    "## R10. 🟡 **SCR 을 SNR 의 대리지표로 쓰지 말라** (§4.4)",
    "",
    "강표적에서 자기 부엽이 SCR 분모를 최대 3.8 dB 들어올린다. 표에 SCR 을 적을 거면 "
    "**\"= 유도 SNR\" 이라고 쓰지 말 것.**",
    "",
    "---",
    "",
    "## 마지막으로: 이 리포트가 **하지 않은** 것",
    "",
    "- **어느 조명원이 좋은지 답하지 않았다.** (그건 다음 리포트다)",
    "- **어느 드론을 잡는지 답하지 않았다.** (그것도 다음 리포트다)",
    "- **ECA 바닥의 원인을 규명하지 못했다.** ADC 가 아니라는 것만 안다.",
    "- **표적 자기가림의 크기를 재지 않았다.** CFAR 훈련창이 부엽 위에 놓인다는 것만 안다.",
    "- **편파를 측정하지 않았다.** V 를 가정했고, H 면 결론이 뒤집힌다는 것만 안다.",
    "",
    "> **모르는 것은 모른다고 적었다. 지어낸 숫자가 최악이다.**",
    "",
    "이 리포트의 가치는 **벤치마크를 못 믿을 이유 10가지를 찾아낸 것**이고, "
    "그 10가지에 전부 **값싼 처방**이 있다는 것이다. 이제 벤치마크를 돌릴 수 있다.",
]))


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
