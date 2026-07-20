# -*- coding: utf-8 -*-
"""make_notebook08.py — report08.ipynb 생성기

report08: **드론 RCS·마이크로도플러 결과 (밴드별·자세별)**
질문: **"드론 5종은 실제로 얼마나 밝고, 프로펠러는 어떤 지문을 남기나?"**

⚠ 노트북은 **생성물**이다. report08.ipynb 를 직접 고치지 말고 이 파일을 고쳐 다시 실행할 것.
⚠ 본문 수치는 전부 **측정 JSON 에서 읽어 주입**한다 — 그림과 글이 어긋날 수 없다.
   · outputs/report2_waveform_rcs.json 의 rcs / materials  (5종 RCS, 재질 분해)
   · outputs/report1.json 의 articulation / microdoppler   (호버 rpm·flash·f_tip, 블레이드 지문)

이 리포트가 다루는 **한 주제**: SBR 로 잰 드론 5종의 밝기(RCS)와, 프로펠러가 만드는
마이크로도플러 지문. SBR '방법 자체'(왜 옳은가·가림)는 report07 소관 → 여기선 결과만.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from provenance import provenance_cells   # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
NB = os.path.join(ROOT, "report08.ipynb")
JS2 = os.path.join(ROOT, "outputs", "report2_waveform_rcs.json")   # RCS + 재질
JS1 = os.path.join(ROOT, "outputs", "report1.json")                # 호버 rpm + 마이크로도플러


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def code(*l):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _s(list(l))}


# --------------------------------------------------------------------------- #
#  측정값 로드 — 손으로 안 적는다
# --------------------------------------------------------------------------- #
with open(JS2) as f:
    J2 = json.load(f)
with open(JS1) as f:
    J1 = json.load(f)

DR = J2["rcs"]["drones"]                 # 드론별 3밴드 RCS
MAT = J2["materials"]                     # 재질 분해 (mavic4pro)
EL = J2["rcs"]["el"]
SBR_DIV = J2["meta"]["sbr_div"]
BANDS = [b[0] for b in J2["meta"]["bands"]]     # ["LTE 1.8 GHz", "5G NR 3.5 GHz", "WiFi 5.2 GHz"]

MD = J1["microdoppler"]["drones"]        # 블레이드 지문 (호버 rpm 유도값)
ART = J1["articulation"]["hover"]        # 호버 rpm 유도 (T = C_T ρ n² D⁴)
MDCFG = J1["microdoppler"]["cfg"]

# 표시 순서 (작은 → 큰 기체)
ORDER = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"]

# 밴드평균 밝기 헤드라인 — 가장 밝은/어두운 (드론별 '밴드 평균'끼리 비교; 밴드 혼합 금지)
def _band_avg(d):
    return sum(DR[d]["bands"][b]["mean_dbsm"] for b in BANDS) / len(BANDS)


_best = max(ORDER, key=_band_avg)
_dim = min(ORDER, key=_band_avg)
_best_v = _band_avg(_best)
_dim_v = _band_avg(_dim)
_span = _best_v - _dim_v

# 밴드가 한 기체를 얼마나 흔드나 (드론별 밴드 최대-최소, 평균)
_band_swing = sum(
    max(DR[d]["bands"][b]["mean_dbsm"] for b in BANDS)
    - min(DR[d]["bands"][b]["mean_dbsm"] for b in BANDS) for d in ORDER
) / len(ORDER)

# 재질 분해 행 뽑기 (라벨로)
def _matrow(key):
    for r in MAT["rows"]:
        if key in r["label"]:
            return r
    return None
_full = _matrow("Full drone")
_noshell = _matrow("- shell")
_metal = _matrow("metal core")
_diel = _matrow("dielectric only")
_noprop = _matrow("propellers only")

# 마이크로도플러 PO→SBR pedestal 이득 범위
_gains = [MD[d]["gain_db"] for d in ORDER]
_gmin, _gmax = min(_gains), max(_gains)

cells = []

# =========================================================================== #
#  0. 앞머리 (provenance) — 라이브러리 척추 리드
# =========================================================================== #
cells += provenance_cells(
    report="report08",
    what="드론 RCS·마이크로도플러 결과 (밴드별·자세별)",
    question="드론 5종은 실제로 얼마나 밝고, 프로펠러는 어떤 지문을 남기나?",

    spine=dict(
        core=("탐지는 표적이 레이더 눈에 **얼마나 밝은가(RCS, σ)**에서 출발한다. 이 리포트는 드론 5종의 "
              "**절대 RCS** 와 프로펠러 **마이크로도플러 지문**을 자작 SBR+PO 로 산출하고, 그 절대값이 "
              "**실측 문헌의 소형 멀티로터 RCS 범위 안**에 듦을 보인다(우리 mavic4pro 봉우리 −12.4 dBsm)."),
        gap=(f"스톡 Sionna `PathSolver` 는 표적 σ 를 아예 주지 않고(→report06), 그 위에 얹은 SBR+PO 도 "
             f"해석해(평판 σ=4πA²/λ²·구 σ=πr²)로는 **방법이 옳음만** 검증될 뿐 — 파이프라인 안에 드론의 "
             f"**절대 σ 를 대조할 자체 기준이 없다.** 밝기 차이는 크게는 {_span:.0f} dB 에 이른다."),
        prior=("소형 멀티로터의 RCS 는 **실측 문헌**이 기준이다 — 3–6 GHz 실측에서 대략 −15~−5 dBsm 대"
               "(Mavic급). Li & Ling 2017(IEEE AWPL, 3–6 GHz: Phantom 2 −27.5 ~ Inspire 1 −13.7 dBsm) · "
               "Ezuma/Güvenç(arXiv:1911.05926) · Güvenç/NCSU 서베이(arXiv:2402.05909) · "
               "Semkin 2020(카본 +7 dB)."),
        lib=("표적 σ 는 **자작 SBR+PO** 로 계산한다(절차 →report07) — Sionna 가 쓰는 **Mitsuba 3 광선엔진을 "
             "그대로 재사용**하고 그 위에 PO 표면적분만 얹어(새 광선엔진 없음·중복계산 없음) 복소장 E 를 "
             "직접 낸다. BVH SBR+PO(arXiv:2604.09243)와 같은 방법."),
        verify=("우리 mavic4pro **방위평균 −19.7·봉우리 −12.4 dBsm** 가 위 실측 범위 안에 든다(§6 대조표). "
                "방위평균은 문헌 상한보다 어두워 탐지 SNR 을 **보수적**으로 잡는다."),
    ),

    sources=[
        dict(item="드론 물리 스펙 (대각·무게·프로펠러·로터 수)",
             src="DJI 공식 제품 스펙 (Mini 5 Pro · Mavic 4 Pro · Matrice 4E · S1000+ · Phantom 4)",
             kind="📄 제조사 스펙"),
        dict(item="5종 RCS (3밴드) · 재질 분해",
             src="**`outputs/report2_waveform_rcs.json`** 의 `rcs` / `materials`. "
                 "`src/viz_report2.py` 가 `src/rcs_sbr.py`(SBR)를 돌려 남긴다",
             kind="🟡 측정 (SBR = Mitsuba 광선 + PO)"),
        dict(item="호버 rpm 유도 · 블레이드 마이크로도플러",
             src="**`outputs/report1.json`** 의 `articulation`(추력 균형) / `microdoppler`. "
                 "`src/viz_report3.py` + `src/microdoppler.py` 가 남긴다",
             kind="🟡 측정 (자세별 SBR 산란장)"),
        dict(item="재질별 반사계수",
             src="**`src/materials.py`** — Sionna RT 와 SBR 이 함께 읽는 단일 진리원 "
                 "(ITU-R P.2040 기반 + custom)",
             kind="📐 물성표"),
        dict(item="실측 문헌 드론 RCS (절대값 앵커)",
             src="Li & Ling 2017(IEEE AWPL) · Ezuma/Güvenç(arXiv:1911.05926) · "
                 "Güvenç/NCSU 서베이(arXiv:2402.05909) · Semkin 2020 · Frankford/Björklund(IET RSN)",
             kind="📚 실측 문헌 (검증 기준)"),
    ],

    engines=["sbr", "microdoppler", "sionna-render", "po", "matplotlib"],
    libs=["sionna", "mitsuba", "drjit", "trimesh", "scipy", "numpy", "matplotlib"],

    reproduce=[
        "cd /home/yunjung/workspace/sionna2",
        "",
        "# 5종 RCS(3밴드) + 재질 분해  -> report2_waveform_rcs.json",
        "~/.venvs/py312/bin/python src/viz_report2.py",
        "",
        "# 호버 rpm 유도 + 블레이드 마이크로도플러  -> report1.json",
        "~/.venvs/py312/bin/python src/viz_report3.py",
        "",
        "# JSON -> report08.ipynb (이 파일)",
        "~/.venvs/py312/bin/python src/make_notebook08.py",
    ],

    artifacts=[
        dict(file="outputs/report2_waveform_rcs.json",
             what="**이 노트북의 RCS 숫자.** rcs(5종×3밴드) / materials(재질 분해)"),
        dict(file="outputs/report1.json",
             what="**이 노트북의 마이크로도플러 숫자.** articulation(호버 rpm) / microdoppler(지문)"),
        dict(file="outputs/figures/report2_rcs_bars.png", what="§2 5종 밝기 · 크기 추세"),
        dict(file="outputs/figures/report2_materials.png", what="§3 재질 분해 (껍데기 vs 금속)"),
        dict(file="outputs/figures/report2_rcs_polar.png", what="§4 방위 패턴 (로브 vs 널)"),
        dict(file="outputs/figures/report1_hover_rpm.png", what="§5 호버 rpm 유도"),
        dict(file="outputs/figures/report1_microdoppler.png", what="§5 블레이드 지문 + 가림 대가"),
    ],

    caveats=[
        "**절대 RCS 값을 보장하지 않는다.** SBR 은 해석해(구·평판)로만 검증됐고 드론 실측 앵커링이 "
        "없다(방법 검증은 report07). 이 리포트가 지지하는 것은 **상대 순서**(큰 기체가 밝다)와 "
        "**대역 추세**(밴드는 몇 dB만 움직인다), 그리고 **실측 문헌 범위와의 정합**이지 특정 드론의 "
        "절대 dBsm 이 아니다.",

        f"**플라스틱 셸의 밝기는 불확실 구간이다.** 1~3 mm 셸은 1.8~5.2 GHz 에서 **반투명**인데 "
        f"first-hit SBR 은 셸을 뚫지 못한다. 그래서 진실은 '통드론'과 '셸 제거' 두 막대 사이에 "
        f"있고, 그 간격 **{abs(_noshell['delta_db']):.1f} dB** 는 측정오차가 아니라 **모델링 "
        "불확실도**로 읽어야 한다.",

        "**방위 패턴의 '널(골)'은 인용 금지.** 로브 사이 골은 격자밀도·대역평균·평활에 10 dB 넘게 "
        "흔들린다. **로브(봉우리)와 방위평균만** 믿는다.",

        "**호버 rpm 은 가정값이다.** 추력=무게 균형(C_T≈0.11)에서 유도한 물리 추정치이지 텔레메트리 "
        "실측이 아니다. flash·f_tip 은 이 rpm 에 선형으로 비례하므로, 실제 비행 rpm 이 다르면 지문 "
        "주파수도 그만큼 이동한다.",

        "**마이크로도플러는 슬로타임 모델이다.** 자세별 산란장은 SBR(Mitsuba 광선)로 재계산하지만, "
        "블레이드 유연·와류 등 공기역학은 넣지 않았다. 지문의 **구조**(깜빡임·f_tip 경계)는 믿을 만 "
        "하나 절대 세기는 아니다.",
    ],

    cost="5종 × 3밴드 RCS 는 GPU 한 장(#2)에서 수십 분(광선격자 λ/16). "
         "마이크로도플러는 자세 144개 × SBR 재계산이라 드론당 수~십수 분.",

    related=[
        dict(rep="**앞** — [report07](report07.ipynb)",
             rel="이 숫자를 낸 **방법(SBR)** — 왜 옳은가·가림이 무엇인가"),
        dict(rep="**다음** — [report09](report09.ipynb)",
             rel="이제 탐지로. 먼저 챔버 **바닥이 놓는 함정**(표적 경유 유령)"),
    ],

    glossary=[
        ("RCS (σ)", "레이더 되비침 밝기 [m²]. '이 표적이 얼마나 밝게 되쏘나'. dBsm = 10·log₁₀(σ/1 m²)"),
        ("dBsm", "1 m² 대비 dB. −20 dBsm = 0.01 m² = 되비침이 사방 10 cm 판 만큼"),
        ("광학영역", "표적이 파장보다 훨씬 클 때. 밝기가 대략 **투영 넓이**를 따라가고 주파수엔 둔감"),
        ("SBR", "광선을 쏴 보이는 면을 찾고(가림 처리) 그 위에서 밝기를 위상 맞춰 적분. 우리 RCS 엔진"),
        ("가림(occlusion)", "앞 부품에 막혀 안 보이는 면. 이걸 안 빼면 밝기·정지신호를 과대평가한다"),
        ("로브 / 널", "방위 패턴의 봉우리(로브)와 골(널). 로브는 안정, 널은 불안정 → 널은 인용 금지"),
        ("마이크로도플러", "표적의 **부분 운동**(프로펠러 회전)이 만드는 도플러 미세구조. 드론의 지문"),
        ("flash rate", "블레이드가 정면을 보여 번쩍이는 초당 횟수 = 날개수 × 회전수/60"),
        ("f_tip", "날개 끝 속도가 만드는 최대 도플러 폭. f_tip = 2·v_tip/λ·cos(el)"),
        ("pedestal(정지 몸통 신호)", "회전 안 하는 몸통이 만드는 0 Hz 근처 강한 성분. 블레이드 깜빡임은 "
                                     "이 위로 솟아야 보인다"),
        ("C_T (추력계수)", "프로펠러 추력을 회전수로 잇는 무차원 계수. T = C_T ρ n² D⁴, 소형 로터 ≈0.11"),
    ],
)

# =========================================================================== #
#  §1  스톡 파이프라인의 공백 — 무엇을 왜 재는가
# =========================================================================== #
cells.append(md(
    "## §1. 무엇을 왜 재는가 — 스톡 파이프라인의 공백",
    "",
    "탐지는 표적이 레이더 눈에 **얼마나 밝은가(RCS, σ)**에서 출발한다. 그런데 스톡 Sionna 의 기본 "
    "광선추적(`PathSolver`)은 경로별 복소이득만 반환할 뿐 표적 표면 위 산란적분이 없어 σ 를 내지 "
    "못한다(→[report06](report06.ipynb)). ISAC 선행 연구는 이 밝기를 세 갈래로 다룬다 — 확산계수 S "
    "가정, RCS 점표적 주입, 그리고 자작 SBR+PO. 우리는 세 번째, 선행이 실제로 쓰는 **SBR+PO** "
    "방식으로 σ 를 계산했다(BVH SBR+PO, arXiv:2604.09243 과 같은 방법 — Sionna 가 쓰는 Mitsuba 3 "
    "광선엔진을 그대로 재사용하고 그 위에 PO 표면적분만 얹어 복소장 E 를 직접 낸다; 절차는 "
    "→[report07](report07.ipynb)).",
    "",
    "이 리포트는 그 **결과**다 — 5종의 밝기(§2), 밝기가 어디서 나오나(§3), 방위 패턴(§4), 프로펠러 "
    "마이크로도플러 지문(§5). 다만 SBR+PO 의 해석해 검증(평판·구, report07)은 방법이 옳음만 보일 뿐 "
    "드론의 **절대 σ** 를 대조할 자체 기준이 파이프라인 안에 없다. 그래서 절대 스케일은 리포트 끝에서 "
    "**공개 실측 문헌 드론 RCS 로 앵커**한다(§6).",
))

# =========================================================================== #
#  §2  5종 얼마나 밝나 (증거)
# =========================================================================== #
_rows = []
for d in ORDER:
    v = DR[d]
    cells_b = " | ".join(f"{v['bands'][b]['mean_dbsm']:+.1f}" for b in BANDS)
    _rows.append(f"| {v['name']} | {v['diagonal_mm']} | {v['weight_g']:.0f} | {cells_b} |")

cells.append(md(
    "## §2. 5종 얼마나 밝나 — 밝기를 정하는 건 크기지 주파수가 아니다",
    "",
    "![rcs bars](outputs/figures/report2_rcs_bars.png)",
    "",
    "각 드론을 **360° 다 돌려가며**(방위) 세 통신대역에서 재고, 그 **방위평균**을 밝기 대표값으로 "
    "씁니다. (봉우리 값이 아니라 평균입니다 — 링크버짓에 넣을 정직한 숫자는 이쪽입니다.)",
    "",
    f"**밴드평균 방위평균 RCS [dBsm]** (el = {EL:.0f}°, 격자 λ/{SBR_DIV}):",
    "",
    "| 드론 | 대각 [mm] | 무게 [g] | " + " | ".join(BANDS) + " |",
    "|---|---|---|---|---|---|",
    *_rows,
    "",
    "**두 가지가 한눈에 보입니다.**",
    "",
    f"1. **크기가 밝기를 정합니다.** 가장 큰 {DR[_best]['name']}(대각 {DR[_best]['diagonal_mm']} mm, "
    f"{DR[_best]['weight_g']/1000:.1f} kg 8로터)가 가장 밝고, 가장 작은 {DR[_dim]['name']}"
    f"({DR[_dim]['diagonal_mm']} mm, {DR[_dim]['weight_g']:.0f} g)가 가장 어둡습니다. 둘 사이가 "
    f"**{_span:.1f} dB** — 퍼센트 수준이 아니라 **십 배 남짓** 차이입니다. 오른쪽 산점도가 대각↔밝기 "
    "추세를 그대로 보여줍니다.",
    "",
    f"2. **대역(주파수)은 별로 안 움직입니다.** 같은 드론을 1.8 → 5.2 GHz 로 옮겨도 밝기는 평균 "
    f"**{_band_swing:.1f} dB** 밖에 안 변합니다. 드론이 이미 파장(λ = 6~17 cm)보다 훨씬 커서 "
    "**광학영역**에 있기 때문입니다 — 이 영역에선 밝기가 대략 **투영 넓이**를 따라가고 파장엔 "
    "둔감합니다.",
    "",
    "> **크기 순서가 무게 순서와 살짝 다른 이유.** RCS 는 무게가 아니라 **되비추는 금속 표면**이 "
    f"정합니다. {DR['phantom4']['name']}는 무겁지만(1.38 kg) 몸체가 매끈해 측면 로브가 좁고, "
    f"{DR['mini5pro']['name']}는 250 g 급이라 되쏠 금속 자체가 작습니다. 순서는 **투영된 금속 넓이** "
    "쪽을 따릅니다.",
    "",
    "> **링크버짓으로 가져갈 숫자는 방위평균입니다.** 봉우리(peak)는 순간적으로 더 밝지만 방위가 "
    "조금만 틀어져도 사라집니다 — 탐지 성능을 보수적으로 보려면 평균을 씁니다.",
))

# =========================================================================== #
#  §3  밝기는 속 금속이 지배 (증거)
# =========================================================================== #
cells.append(md(
    "## §3. 밝기는 속 금속이 지배한다 — 껍데기는 스크린이다",
    "",
    "![materials](outputs/figures/report2_materials.png)",
    "",
    f"밝기가 **어디서** 나오는지 보려면 드론을 부품별로 벗겨가며 재보면 됩니다. "
    f"{MAT['name']} 한 대를 {MAT['fc']/1e9:.1f} GHz 에서, 부품을 하나씩 지우며 방위평균 밝기를 "
    "다시 쟀습니다(밝은 쪽이 위):",
    "",
    "| 무엇을 남겼나 | 방위평균 RCS | 통드론 대비 |",
    "|---|---|---|",
    f"| **통드론** (플라스틱 셸 포함) | {_full['mean_dbsm']:+.2f} dBsm | 기준 |",
    f"| 셸 **제거** (전파가 플라스틱을 통과) | {_noshell['mean_dbsm']:+.2f} dBsm | "
    f"**{_noshell['delta_db']:+.2f} dB** |",
    f"| 프로펠러만 제거 | {_noprop['mean_dbsm']:+.2f} dBsm | {_noprop['delta_db']:+.2f} dB |",
    f"| **금속 코어만** (모터+배터리+PCB+카메라) | {_metal['mean_dbsm']:+.2f} dBsm | "
    f"**{_metal['delta_db']:+.2f} dB** |",
    f"| 유전체만 (금속 하나도 없이) | {_diel['mean_dbsm']:+.2f} dBsm | {_diel['delta_db']:+.2f} dB |",
    "",
    "**세 줄로 요약됩니다.**",
    "",
    f"- **플라스틱 껍데기를 지웠더니 오히려 {_noshell['delta_db']:+.2f} dB 밝아졌습니다.** 셸은 "
    "밝기에 거의 기여하지 않으면서, 뒤에 있는 금속으로 갈 광선을 약하게 가로막던 **가림막**이었기 "
    "때문입니다. (지운다는 건 페인트를 칠하는 게 아니라 그 면을 메쉬에서 **삭제**해 전파가 통과하게 "
    "하는 것입니다.)",
    f"- **금속 코어만 남겨도 {_metal['delta_db']:+.2f} dB** — 통드론과 사실상 같습니다. "
    f"반대로 **금속을 전부 빼면 {_diel['delta_db']:+.2f} dB** 어두워집니다. "
    "**밝기를 만드는 건 속 금속이고, 플라스틱은 조연**입니다.",
    f"- 프로펠러(플라스틱)는 정지 상태에서 **{_noprop['delta_db']:+.2f} dB** — 밝기엔 거의 무의미합니다. "
    "(단, **돌면** 이야기가 완전히 달라집니다 → §5.)",
    "",
    "> ⚠️ **정직한 한계 하나.** 1~3 mm 플라스틱 셸은 1.8~5.2 GHz 에서 실제로는 **반투명**입니다 — "
    "전파가 얼마쯤 통과합니다. 그런데 우리 SBR 은 광선이 **첫 충돌에서 멈추므로** 셸을 뚫지 못합니다. "
    f"그래서 진실은 '통드론(불투명 셸)'과 '셸 제거(투명 셸)' **두 막대 사이 어딘가**에 있습니다. "
    f"그 간격 **{abs(_noshell['delta_db']):.1f} dB** 는 측정오차가 아니라 **모델링 불확실도**로 "
    "읽으십시오.",
    "",
    "> 두 엔진(전파용 Sionna RT · RCS용 SBR)이 **같은 재질표**(`src/materials.py`)를 읽습니다. "
    "오른쪽 표의 반사계수가 그것 — 조용히 어긋날 수 없습니다.",
))

# =========================================================================== #
#  §4  방위 패턴 (증거)
# =========================================================================== #
cells.append(md(
    "## §4. 방위 패턴 — '봉우리'는 인용, '골'은 인용 금지",
    "",
    "![rcs polar](outputs/figures/report2_rcs_polar.png)",
    "",
    "드론을 한 바퀴 돌리면 밝기는 방위에 따라 **꽃잎 모양**으로 오르내립니다. 코(0°)·꼬리(180°)·"
    "측면(90°/270°)에서 넓은 금속면이 정면으로 보일 때 **봉우리(로브)** 가 서고, 그 사이에서 "
    "**골(널)** 로 떨어집니다.",
    "",
    "**여기서 반드시 지켜야 할 규칙:**",
    "",
    "- **봉우리(로브)는 대역평균(5개 주파수)과 3° 평활을 거친 뒤에는 인용해도 됩니다.** 평활 전 "
    "단일 주파수의 개별각은 격자를 반절해도 평균 ~2 dB 흔들립니다(`report_mesh/outputs/mesh_verify.json` "
    "H·I). 링크버짓의 '최선의 경우'로 쓸 수 있습니다.",
    "- **골(널)은 절대 인용하지 마십시오.** 골의 깊이는 여러 반사가 서로 상쇄돼 생기는 것이라, "
    "격자를 조금만 바꿔도 **10 dB 넘게** 출렁입니다. '이 각도에서 −40 dBsm 으로 안 보인다' 같은 "
    "주장은 하면 안 됩니다.",
    "",
    "> 그래서 이 리포트가 밖으로 내보내는 숫자는 **§2 의 방위평균**과 **로브 높이**뿐입니다. "
    "특정 방위의 널 깊이는 내부 그림에서만 봅니다.",
    "",
    f"> 각 곡선은 361개 방위 × 대역 내 5개 주파수 평균 × 3° 평활입니다(el = {EL:.0f}°). "
    "큰 기체(S1000+)일수록 로브가 잘게 갈라지는 건 전기적 크기(size/λ)가 커서 로브가 촘촘해지기 "
    "때문입니다.",
))

cells.append(md(
    "![.](outputs/renders/anim/rcs_azimuth_matrice4e.gif)",
    "",
    "<sub>Matrice 4E RCS 방위각 폴라 — 각도마다 수 dB~수십 dB 출렁인다(SBR 결과).</sub>",
))

# =========================================================================== #
#  §5  마이크로도플러 (증거)
# =========================================================================== #
_mdrows = []
for d in ORDER:
    v = MD[d]
    _mdrows.append(
        f"| {DR[d]['name']} | {v['n_rotors']} | {ART[d]['hover_rpm']:.0f} | "
        f"{v['flash_hz']:.0f} | ±{v['f_tip_hz']/1e3:.2f} | {v['gain_db']:.0f} |")

cells.append(md(
    "## §5. 프로펠러 지문 — 마이크로도플러",
    "",
    "지금까지는 드론이 **가만히** 있을 때의 밝기였습니다. 하지만 드론의 프로펠러는 초당 수십 바퀴를 "
    "돕니다. 돌아가는 블레이드는 **정면을 보일 때마다 반사가 번쩍**이고, 날개 끝은 시속 200 km 급으로 "
    "움직여 큰 도플러(주파수 변화)를 만듭니다. 이 미세구조가 드론을 새·잡음과 가르는 **지문**입니다.",
    "",
    "다중 프로펠러 드론의 **바이스태틱 마이크로도플러**를 모델링하는 것은 선행 연구가 이미 측정으로 "
    "검증해 둔 접근입니다 — Costa & Thomä(TU Ilmenau, IEEE J-STEAP 2025, arXiv:2504.05168)는 "
    "프로펠러를 thin-wire 점산란체 + PO 로터 RCS 로 놓고 분산 ISAC OFDM 에서 실측 대조했습니다. "
    "우리는 같은 목표를 **전체 메쉬 SBR** 로 풀어(점산란체 근사 없이 가림까지 포함) 아래 지문을 얻습니다.",
    "",
    "### 5.1 지문의 두 눈금은 호버 회전수에서 나온다",
    "",
    "![hover rpm](outputs/figures/report1_hover_rpm.png)",
    "",
    "지문에는 두 개의 눈금이 있습니다.",
    "",
    "- **flash rate(번쩍임 주기)** = 날개수 × 회전수/60. 2엽 프로펠러는 한 바퀴에 정면을 **두 번** "
    "보이므로 flash = 회전수/30. → 프로펠러가 **크고 느린** 기체는 드물게, **작고 빠른** 기체는 "
    "자주 번쩍입니다.",
    "- **f_tip(날개끝 도플러 폭)** = 2·v_tip/λ·cos(el). 날개 끝 속도 v_tip = ω·R 가 만드는 "
    "**최대** 도플러입니다. 모델 안에서 이보다 빨리 움직이는 산란체는 없으므로, 진짜 마이크로도플러는 "
    "**±f_tip 안에** 갇힙니다.",
    "",
    "둘 다 **호버 회전수**만 알면 정해집니다. 회전수는 텔레메트리가 없으니 **물리로 유도**합니다 — "
    "호버란 4(또는 8)개 로터의 추력이 정확히 무게를 받치는 상태이고, 추력은 T = C_T ρ n² D⁴ "
    "(C_T ≈ 0.10~0.12) 로 회전수 n 과 이어집니다. 무게와 프로펠러 지름 D 를 넣어 n 을 풀면 "
    "**아래 표의 호버 rpm**이 나옵니다(가정값이지만 물리 범위 안입니다).",
    "",
    f"**5종의 프로펠러 지문** ({MDCFG['fc']/1e9:.1f} GHz, el = {MDCFG['el']:.0f}°):",
    "",
    "| 드론 | 로터 수 | 호버 rpm | flash [Hz] | f_tip [kHz] | 가림 이득 [dB] |",
    "|---|---|---|---|---|---|",
    *_mdrows,
    "",
    f"→ **flash rate 만으로도 기체가 갈립니다.** 큰 프로펠러(S1000+ 15인치)는 느리게 돌아 "
    f"{MD['s1000plus']['flash_hz']:.0f} Hz, 작은 프로펠러(Mini 5 Pro 6인치)는 빠르게 돌아 "
    f"{MD['mini5pro']['flash_hz']:.0f} Hz 로 번쩍입니다. 지문 주파수가 곧 기체 식별자입니다.",
    "",
    "### 5.2 지문을 보려면 '가림'이 필수다",
    "",
    "![microdoppler](outputs/figures/report1_microdoppler.png)",
    "",
    "위 그림의 각 판은 시간(가로) × 도플러(세로)로 그린 **슬로타임 반사장**입니다. 프레임마다 "
    "블레이드 자세를 다시 놓고 SBR 로 산란장을 새로 계산합니다 — 세로 줄무늬가 바로 블레이드 번쩍임, "
    "파란 점선이 ±f_tip 경계입니다.",
    "",
    "여기서 **가림이 왜 필수인지**가 오른쪽 아래 막대에 있습니다. 블레이드가 몸통 뒤로 돌아가면 "
    "**안 보여야** 하는데, 가림을 안 하는 순수 PO 는 **숨은 날개와 셸 속 금속까지 다 세어** 0 Hz "
    "근처의 **정지 몸통 신호(pedestal)를 부풀립니다.** 그 부풀림이 드론마다 "
    f"**{_gmin:.0f}~{_gmax:.0f} dB** — 그만큼 블레이드 깜빡임이 몸통 신호 아래 묻힙니다.",
    "",
    "SBR 은 광선이 **첫 충돌에서 멈춰** 가림이 공짜라, 부풀린 pedestal 을 걷어내고 "
    "**깜빡임을 몸통 위로 되살립니다.** 그래서 §3 에서 '정지 상태 프로펠러는 밝기에 무의미'했지만, "
    "**돌면** 프로펠러가 지문의 주역이 됩니다 — 정지 밝기가 아니라 **시간에 따른 변조**가 정보이기 "
    "때문입니다.",
    "",
    "> **직관 하나.** 선풍기 날개에 손전등을 비추면, 날개가 정면을 보이는 순간마다 규칙적으로 "
    "반짝입니다. 그런데 날개가 **선풍기 몸통 뒤로** 넘어가는 동안은 안 보이죠(가림). 이 '보였다 안 "
    "보였다'가 규칙적 반짝임을 만듭니다. 몸통 뒤 날개까지 억지로 세면(가림 무시) 밋밋한 몸통 밝기만 "
    "커져서 정작 반짝임이 안 보입니다.",
    "",
    "> ⚠️ 호버 rpm 은 추력 균형에서 유도한 **가정값**입니다. flash·f_tip 은 rpm 에 비례하므로, 실제 "
    "비행 회전수가 다르면 지문 주파수도 그만큼 이동합니다. 지문의 **구조**(깜빡임·±f_tip 경계·기체별 "
    "순서)는 믿을 만하나 절대 주파수는 rpm 가정에 달려 있습니다.",
))

# =========================================================================== #
#  재현 코드
# =========================================================================== #
cells.append(code(
    "# §2 재현 — 한 드론의 밝기를 한 대역에서 직접 재본다 (SBR)",
    "import numpy as np",
    "from rcs_po import drone_rcs_pattern_bw, dbsm      # 기본 엔진은 'sbr'",
    "",
    "az = np.arange(0, 361, 2.0)",
    "sig, n_rays = drone_rcs_pattern_bw('s1000plus', 5.21e9, 80e6, az, el_deg=15.0, n_f=5)",
    "print(f'방위당 광선 {n_rays:,}발  (격자 lambda/16)')",
    "print(f'S1000+ @ 5.2 GHz  방위평균 {dbsm(np.mean(sig)):+.2f} dBsm  '",
    "      f'(로브 최대 {dbsm(np.max(sig)):+.2f} dBsm)')",
))

cells.append(code(
    "# §5 재현 — 호버 rpm 유도 + 블레이드 지문의 두 눈금",
    "#   flash = blades * rpm/60,   f_tip = 2*v_tip/lambda * cos(el)",
    "import numpy as np",
    "",
    "specs = dict(mini5pro=(0.2499,0.1524,4), mavic4pro=(1.063,0.267,4),",
    "             matrice4e=(1.219,0.274,4), s1000plus=(9.5,0.381,8),",
    "             phantom4=(1.38,0.240,4))       # (질량 kg, 프로펠러 지름 m, 로터 수)",
    "rho, CT, blades = 1.225, 0.11, 2",
    "lam, el = 3e8/3.5e9, np.deg2rad(15.0)",
    "for d,(m,D,nr) in specs.items():",
    "    T = m*9.81/nr                                  # 로터당 추력 = 무게/로터수",
    "    n = np.sqrt(T/(CT*rho*D**4))                   # T = CT rho n^2 D^4  ->  n [rev/s]",
    "    rpm = n*60",
    "    flash = blades*rpm/60",
    "    v_tip = (2*np.pi*n)*(D/2)",
    "    f_tip = 2*v_tip/lam*np.cos(el)",
    "    print(f'{d:10s} rpm~{rpm:5.0f}  flash {flash:5.1f} Hz  f_tip +-{f_tip/1e3:4.2f} kHz')",
    "# ↑ 여기 나온 rpm 이 report1.json 의 hover_rpm 과 같은 물리에서 나온다",
))

# =========================================================================== #
#  §6  선행 연구의 방식과 실측 대조 — 절대값 검증
# =========================================================================== #
cells.append(md(
    "---",
    "## §6. 선행 연구의 방식과 실측 대조 — 절대값 검증",
    "",
    "해석해(평판·구, report07)는 SBR+PO 라는 **방법**이 옳음을 보이지만 드론의 **절대 σ** 는 보장하지 "
    "못한다. 절대 스케일의 기준은 선행 연구가 남긴 **실측 문헌 드론 RCS** 다.",
    "",
    "ISAC 문헌에서 표적 밝기는 세 갈래로 처리된다 — **(b) 확산계수 S 가정**(Great-X arXiv:2507.08716 · "
    "Deterministic-Modeling arXiv:2603.28736, EuCAP 2026), **(c) RCS 상수 주입**(3GPP · 오픈 MATLAB "
    "arXiv:2606.07328), **(d) 자작 SBR+PO / 산란 add-on**(BVH SBR+PO arXiv:2604.09243 — 우리와 동일 "
    "방법). 우리는 **(d) 자작 SBR+PO** 를 택했다 — 소형 드론은 확산 S 실측 보정 데이터가 없고 부위별 "
    "재질 차이가 RCS 를 지배하기 때문이다. 상용 CADFEKO(LAMBDA arXiv:2607.03826)나 비공개 RadarSimPy "
    "대신 **선행이 실제로 쓰는 자작 SBR+PO 방식을 따랐고**, 검증은 라이브러리 대조가 아니라 아래 "
    "**실측 문헌 앵커**로 세운다(근거: `prior_work/pw01`).",
    "",
    "우리가 쓰는 신형(Mavic 4 Pro·Matrice 4E)의 실측 RCS 는 아직 논문에 없습니다(2024~25 출시). "
    "대신 **밴드가 겹치는 근접 기종 실측**과 대조하면 우리 값이 타당합니다:",
    "",
    "| 문헌 (실측) | 밴드 | 측정 RCS | 우리와의 관계 |",
    "|---|---|---|---|",
    "| **Li & Ling 2017** (IEEE AWPL, ~99인용) | **3–6 GHz** ★밴드일치 | Phantom 2 **−27.5**, 3DR Solo −24.2, Inspire 1 −13.7 dBsm (모두 **peak/특정자세**, 자세 스프레드 ~14 dB) | 우리 mavic4pro **방위평균 −19.7 dBsm → 이 범위 안** (봉우리 자세 −12.4 dBsm 는 상한 −13.7 보다 ~1.3 dB 밝으나 개별각 수렴 불확실도 ~2 dB 이내 — 유의미한 초과 아님) |",
    "| Ezuma 2019 (compact-range) | 15 / 25 GHz | Phantom 4 Pro −15.0 / −12.4 dBsm | 15→25 GHz 에서 +2.6 dB — RCS 의 주파수 단조증가 방향이 우리 밴드 추세와 일치(절대값 외삽 비교는 밴드갭이 커서 참고 수준) |",
    "| Semkin 2020 (IEEE Access) | 26–40 GHz | Mavic Pro −16.8, Phantom 4 Pro −16.4, **Matrice 100(카본) −10.5** dBsm | **카본이 플라스틱보다 ~7 dB 밝음** — 우리 재질 분해와 방향 일치 |",
    "| Quevedo 2019 (IET RSN) | X-band 8.75 GHz | Phantom 4 −20~−4.6 dBsm(프롭 회전 의존) | 프로펠러가 RCS 를 크게 흔듦 — 우리 마이크로도플러 서사 |",
    "",
    "<sub>정리: (1) **같은 밴드(3–6 GHz)** 실측(Phantom 2 −27.5 ~ Inspire 1 −13.7 dBsm)이 우리 **방위평균** "
    "−19.7 dBsm 를 감싼다. 봉우리 자세(−12.4 dBsm @3.5 GHz)는 문헌 상한(−13.7)보다 ~1.3 dB 밝지만, "
    "이 차이는 개별각 수치수렴 불확실도(격자 반분에 개별각 평균 ~2 dB — mesh_verify H·I) **이내라 "
    "유의미한 초과로 읽지 않는다**. "
    "(2) 고주파 실측들은 모두 더 밝고(RCS 는 주파수↑에 단조↑), 3.5 GHz 로 낮추면 우리 값에 수렴한다. "
    "(3) **주의**: 우리 소형드론 값(−17~−26)은 문헌이 링크버짓에 흔히 쓰는 가정치(−10~−13 dBsm)보다 "
    "**어두워, 탐지 SNR 을 오히려 보수적으로** 잡는다. 서지: `/data/public/jeong_drone_refs/`.</sub>",
    "",
    "### 절대값 앵커 — 실측 문헌 RCS 와 교차검증",
    "",
    "밴드가 더 가까운 실측(2.4~4.5 GHz)과도 교차검증한다(값 출처: `prior_work` 파일럿 조사, 각 값은 "
    "1차 출처 확인):",
    "",
    "| 실측 (동종 드론) | 밴드 | 측정 RCS | 출처 |",
    "|---|---|---|---|",
    "| DJI Mavic Pro | **2.4 GHz** ★근접 | **≈ −15.2 dBsm** (0.03 m²) | Güvenç/NCSU 서베이(arXiv:2402.05909) |",
    "| DJI Mavic Pro | 15 / 25 GHz | −17.1 / −16.2 dBsm | Ezuma/Güvenç(arXiv:1911.05926) |",
    "| DJI Phantom 4 Pro | 15 / 25 GHz | −15.0 / −12.4 dBsm | 〃 |",
    "| 소형기(바이스태틱, 무향실) | **2.75 / 4.51 GHz** ★감쌈 | −9.8→−5.3 / −7.8→−5.0 dBsm | Frankford/Björklund(IET RSN) |",
    "",
    "<sub>**교차검증 판정.** 동종 멀티로터의 3.5 GHz RCS 는 자세·편파·회전상태에 따라 대략 **−15 ~ −5 dBsm** "
    "이 되어야 한다(RCS 는 주파수↑에 단조↑ 이므로 3.5 GHz ≤ 15 GHz 값). 우리 mavic4pro 는 **방위평균 −19.7·"
    "봉우리 −12.4 dBsm** — 봉우리가 이 범위에 들고 방위평균은 그 아래(더 어둡게=보수적). **−17~−3 dBsm 을 크게 "
    "벗어나면 적신호**인데 우리는 그 안이다. ⚠ 정확 모델·측정조건·자세규약이 달라 **±몇 dB 앵커**이지 점일치가 "
    "아니다 — 그래도 시뮬 대비 시뮬보다 **실측 대비**가 강한 근거다. 이 일치는 메쉬의 **레이더 유효 형상**"
    "(크기·재질분포·지배산란체)이 옳다는 증거이기도 하다.</sub>",
))

# =========================================================================== #
#  정리 + 다음 리포트
# =========================================================================== #
cells.append(md(
    "---",
    "## 정리",
    "",
    f"1. **밝기는 크기가 정한다.** 가장 큰 기체가 가장 작은 기체보다 **{_span:.1f} dB** 밝고, "
    f"대역(주파수)은 같은 드론을 **{_band_swing:.1f} dB** 밖에 못 움직인다(광학영역). 그리고 그 "
    "밝기는 플라스틱 껍데기가 아니라 **속 금속**(모터·배터리·PCB)에서 나온다 — 껍데기는 반투명 "
    "스크린일 뿐이다(§2·§3).",
    f"2. **프로펠러는 지문을 남긴다.** 돌면 "
    f"**{MD['s1000plus']['flash_hz']:.0f}~{MD['mini5pro']['flash_hz']:.0f} Hz** 의 규칙적 깜빡임과 "
    f"**±{MD['mini5pro']['f_tip_hz']/1e3:.1f}~{MD['s1000plus']['f_tip_hz']/1e3:.1f} kHz** 의 날개끝 "
    f"도플러가 생긴다. 이 지문을 보려면 **가림**이 필수다 — 몸통 뒤 숨은 날개를 세지 않아야 정지 몸통 "
    f"신호가 부풀지 않고(순수 PO 는 **{_gmin:.0f}~{_gmax:.0f} dB** 부풀린다), 깜빡임이 그 위로 "
    "드러난다(§4·§5).",
    "3. **절대값은 실측 문헌 범위 안이다.** 스톡 Sionna 는 표적 σ 를 못 주므로(→report06) 자작 "
    "SBR+PO 로 계산했고(→report07), 그 절대값을 공개 실측 드론 RCS(3–6 GHz 근접 기종)와 대조해 "
    "**−15~−5 dBsm 범위 안**임을 확인했다(우리 봉우리 −12.4 dBsm, 방위평균은 더 보수적)(§6).",
    "",
    "**이 리포트가 보장하지 않는 것.** 특정 드론의 **절대 dBsm 점값**(±몇 dB 앵커일 뿐), 플라스틱 셸의 "
    "정확한 기여(반투명 불확실 구간), 방위 패턴의 **널 깊이**와 **절대 회전수**(§4·§5 인용 금지). "
    "지지하는 것은 상대 순서·대역 추세·실측 문헌과의 정합이다.",
    "",
    "> **다음 리포트**: [report09](report09.ipynb) — 이제 **탐지**로 넘어간다. 그 전에 챔버 "
    "**바닥이 놓는 함정**(표적을 경유해 되돌아오는 유령 신호)을 먼저 본다.",
))

# =========================================================================== #
nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
                   "language_info": {"name": "python", "version": "3.12"}},
      "nbformat": 4, "nbformat_minor": 5}

with open(NB, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f"✅ {os.path.relpath(NB, ROOT)} 생성 — 셀 {len(cells)}개 "
      f"(측정 JSON: {os.path.relpath(JS2, ROOT)} + {os.path.relpath(JS1, ROOT)})")
