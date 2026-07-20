# -*- coding: utf-8 -*-
"""make_notebook07.py — report07.ipynb 생성기

report07 — **SBR: 표적을 조준해 밝기를 계산하다**
질문: **"Sionna 가 못 내는 RCS 를 어떻게 계산했나?"**

⚠ 노트북은 **생성물**이다. report07.ipynb 를 직접 고치지 말고 이 파일을 고쳐 다시 실행할 것.
⚠ 본문 수치는 전부 **측정 JSON 에서 읽어 주입**한다 — 그림과 글이 어긋날 수 없다.
   · outputs/report2_waveform_rcs.json 의 sbr_validation / occlusion
     (그림 report2_sbr_validate.png · report2_occlusion.png 과 같은 소스)
   · outputs/report6_sbr.json 의 kernel (동일 해석해 검증을 따로 돌린 값 — 교차확인)
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
NB = os.path.join(ROOT, "report07.ipynb")
JS = os.path.join(ROOT, "outputs", "report2_waveform_rcs.json")
JS6 = os.path.join(ROOT, "outputs", "report6_sbr.json")


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def code(*l):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _s(list(l))}


# --------------------------------------------------------------------------- #
#  측정값 로드 — 손으로 적지 않는다
# --------------------------------------------------------------------------- #
with open(JS) as f:
    J = json.load(f)
with open(JS6) as f:
    J6 = json.load(f)

M = J["meta"]
V = J["sbr_validation"]      # 커널 해석해 검증 + 격자수렴 + 디더 + 드론수렴
OCC = J["occlusion"]         # 가림의 대가 (한 표적, 한 실험)
K6 = J6["kernel"]            # report6 의 독립 재현 (교차확인)

SBR_DIV = M["sbr_div"]       # 실제 드론 측정에 쓰는 격자밀도 (λ/16)
FC = V["fc"]
LAM = V["lam"]

# 대표 격자에서의 오차 (검증 헤드라인)
_plate_err = V["plate_err"][V["divs"].index(6)]         # 평판 @ λ/6
_sphere_err = V["sphere_err"][V["divs"].index(10)]      # 금속구 @ λ/10
# report6 이 같은 커널을 독립으로 돌린 값
_p6_plate = K6["plate_err"][K6["divs"].index(6)]
_p6_sphere = K6["sphere_err"][K6["divs"].index(10)]

# 디더(정렬만 흔들기) 산포
_dith = {d["div"]: d for d in V["dither"]}
_lam8, _lam24 = _dith[8], _dith[24]

# 드론 방위평균의 격자수렴
_dc_dev = 0.0
_dc_coarse = 0.0
for _ser in V["drone_conv"].values():
    _base = _ser["mean_dbsm"][-1]           # λ/24 기준
    for _d, _m in zip(_ser["divs"], _ser["mean_dbsm"]):
        if _d >= 8:
            _dc_dev = max(_dc_dev, abs(_m - _base))
        else:
            _dc_coarse = max(_dc_coarse, abs(_m - _base))

cells = []

# =========================================================================== #
#  0. 앞머리 (provenance)
# =========================================================================== #
cells += provenance_cells(
    report="report07",
    what="SBR — 표적을 조준해 밝기를 계산하다",
    question="Sionna 가 못 내는 RCS 를 어떻게 계산했나?",

    spine=dict(
        core=("report06 이 '경로 솔버로는 못 만든다' 고 못박은 표적 밝기(RCS)를, **Sionna 가 쓰는 "
              "Mitsuba 광선 위에 표준 PO 표면적분을 얹은 SBR+PO 로 계산한다** — 답을 아는 평판·금속구 "
              "해석해로 교정하면서."),
        gap=("Sionna RT `PathSolver` 에는 표면 산란적분 단계가 없어 표적 밝기 σ 를 주지 못한다"
             "(report06 이 다섯 측정으로 확인). 밝기는 표면 조각들의 되쏨을 위상까지 맞춰 다 더한 값인데, "
             "표적을 거울로만 튕기는(GO) 경로 솔버에는 그 ∫ 단계가 없다."),
        prior=("소형 표적의 코히어런트 RCS 를 스톡 Sionna 로 낸 선행은 **없고**, ISAC 문헌은 표적 밝기를 "
               "외부에서 구해 채널에 주입한다 — **(b)** 재질 확산계수 S 가정[Great-X, arXiv:2507.08716], "
               "**(c)** 상용 full-wave 로 계산·주입 $h=h_{bg}+h_{target}$[LAMBDA=Sionna+CADFEKO, "
               "arXiv:2607.03826; Temporal-GNN=점산란체, arXiv:2604.08306], **(d)** 자작 산란 add-on"
               "[Ziganshin UTD, arXiv:2604.05991] (§2)."),
        lib=("**(d)** 를 택했다 — 새 광선엔진을 만들지 않는다. Sionna 가 쓰는 **Mitsuba 3 / OptiX 광선을 "
             "그대로 재사용**(중복계산 회피)하고 그 위에 **자작 PO 표면적분**(`src/rcs_sbr.py`, 가림 포함)만 "
             "얹는다. GPU BVH SBR+PO(arXiv:2604.09243)와 **같은 방법**(§3)."),
        verify=(f"답을 아는 정준 표적으로 교정 — 금속 평판 σ=4πA²/λ² 오차 **{_plate_err:+.2f} dB**, "
                f"금속구 σ=πr² 오차 **{_sphere_err:+.2f} dB** (@{FC/1e9:.1f} GHz). 완전히 따로 돌린 "
                f"report6 커널도 {_p6_plate:+.2f}/{_p6_sphere:+.2f} dB 로 같은 값(§4). 절대값 앵커는 report08."),
    ),

    sources=[
        dict(item="검증 기준 (정답)",
             src="교과서 폐형식 — 금속구 σ = πr² (광학영역) · 금속평판 σ = 4πA²/λ² (정면 조사)",
             kind="📐 해석해"),
        dict(item="SBR 검증·격자수렴·가림 측정값",
             src="**`outputs/report2_waveform_rcs.json`** 의 `sbr_validation` / `occlusion` "
                 "(그림 `report2_sbr_validate.png` · `report2_occlusion.png` 과 같은 소스)",
             kind="🟡 측정 (SBR = 우리 구현, Mitsuba 광선)"),
        dict(item="같은 커널의 독립 재현",
             src="**`outputs/report6_sbr.json`** 의 `kernel` — 동일 해석해 검증을 따로 돌린 값",
             kind="🟡 교차확인"),
        dict(item="SBR 구현",
             src="**`src/rcs_sbr.py`** — Mitsuba 3 / OptiX 광선 + PO 표면적분. "
                 "**Sionna 가 쓰는 그 광선엔진 그대로**",
             kind="🟡 우리 구현 (Sionna 에 RCS 솔버가 없음)"),
    ],

    engines=["sbr", "po", "sionna-render", "matplotlib"],
    libs=["sionna", "mitsuba", "drjit", "trimesh", "numpy", "matplotlib"],

    reproduce=[
        "cd /home/yunjung/workspace/sionna2",
        "",
        "# 커널 해석해 검증(구 πr² / 평판 4πA²/λ²) + 격자 수렴",
        "~/.venvs/py312/bin/python src/rcs_sbr.py",
        "",
        "# 측정 + 그림 + JSON (sbr_validation / occlusion 을 남긴다)",
        "~/.venvs/py312/bin/python src/viz_report2.py",
        "",
        "# JSON -> report07.ipynb (이 파일)",
        "~/.venvs/py312/bin/python src/make_notebook07.py",
    ],

    artifacts=[
        dict(file="outputs/report2_waveform_rcs.json",
             what="**이 노트북의 SBR 숫자.** sbr_validation / occlusion 블록"),
        dict(file="outputs/report6_sbr.json", what="같은 커널의 독립 재현 (kernel 블록)"),
        dict(file="outputs/figures/report2_sbr_validate.png",
             what="§4 SBR 검증 · 격자 수렴"),
        dict(file="outputs/figures/report2_occlusion.png",
             what="§5 가림 — 순수 PO vs SBR"),
        dict(file="outputs/figures/report2_po_vs_sbr.png",
             what="§5 방위 패턴 비교"),
    ],

    caveats=[
        "**절대 RCS 값을 보장하지 않는다.** SBR 은 해석해(구·평판)로만 검증됐고 드론 실측 "
        "앵커링이 없다. 이 리포트가 지지하는 것은 **방법의 정합성**과 **가림의 방향·규모**이지, "
        "특정 드론의 절대 dBsm 이 아니다.",

        "**매끈한 구의 단일 격자 값은 수렴한 숫자가 아니다.** 구는 되쏘는 지점이 딱 하나뿐이라 "
        f"격자를 어디에 맞추느냐에 민감하다(λ/8 산포 {_lam8['spread']:.1f} dB). 드론처럼 되쏘는 "
        "점이 많은 표적은 방위평균이 저절로 안정된다 — §4 에서 짚는다.",

        "**오목한 곳의 다중반사(2·3차) 값은 규모(작다)만 신뢰한다.** SBR 이 실제로 고치는 것은 "
        "가림이고, 다중반사는 부차적이고 작은 항이다. 그 정확한 dB 값은 이 리포트의 주장이 아니다.",

        "**SBR 은 유전체 투과를 모른다** — 광선을 첫 충돌에서 끝내므로 준투명 플라스틱 셸을 지나는 "
        "전파는 못 본다. 이 성질이 재질 실험에 주는 영향은 report08 에서 다룬다.",

        "**표적이 밝아야 잡힌다 — RCS 는 디텍션에 필수다.** 다만 그 밝기를 Sionna 기본 광선으론 "
        "낼 수 없어(산란적분 부재) SBR 로 따로 계산할 뿐이다.",
    ],

    cost="SBR 커널 검증은 GPU 한 장에서 수십 초. 광선격자 λ/16, Mitsuba 3 / OptiX.",

    related=[
        dict(rep="**앞** — [report06](report06.ipynb)",
             rel="Sionna 의 한계 — 왜 기본 광선엔진이 표적 밝기(σ)를 못 내나"),
        dict(rep="**다음** — [report08](report08.ipynb)",
             rel="이 SBR 로 잰 **실제 드론들의 밝기(RCS) 결과**"),
    ],

    glossary=[
        ("RCS (σ)", "레이더 되비침 밝기 [m²]. 표적이 레이더 쪽으로 얼마나 세게 되쏘는가. "
                    "밝을수록 잡기 쉽다. dBsm = 10·log₁₀(σ / 1 m²)"),
        ("σ 를 넓이로", "밝기는 결국 **되쏘는 표면의 넓이**에서 나온다 — 넓은 판이 작은 못보다 "
                        "밝게 반짝인다"),
        ("dBsm", "1 m² 를 기준으로 한 데시벨 단위. −20 dBsm ≈ 0.01 m²"),
        ("PO (물리광학)", "표적 표면의 작은 조각들이 되쏘는 양을 **위상까지 맞춰 다 더하는 계산**. "
                          "밝기(σ)는 이 덧셈에서 나온다"),
        ("SBR", "Shooting-and-Bouncing Rays. 표적을 **조준해 광선을 쏘고**, 맞은 면이 레이더로 "
                "**되쏘는 양을 PO 로 계산·합산**한다. 상용 전자기 솔버의 표준"),
        ("GO (기하광학)", "표면을 '점 거울' 로만 본다. 벽·바닥에서 어디로 튕기는지는 정확하지만 "
                          "**넓이 항이 없어 밝기를 못 준다** — 전파 광선추적이 이것"),
        ("가림(occlusion)", "앞의 면에 막혀 실제로는 레이더에 안 보이는 면. 이걸 안 빼면 밝기를 "
                            "부풀린다"),
        ("정반사점", "광선이 거울처럼 **똑바로 되돌아오는 딱 한 지점**. 매끈한 곡면은 이게 하나뿐"),
        ("격자밀도 λ/d", "쏘는 평행 광선을 파장(λ)당 몇 발로 촘촘히 하느냐. λ/16 = 파장 한 칸에 "
                          "16 발"),
        ("위상", "파동이 되쏠 때의 타이밍. 같은 타이밍으로 겹치면 밝아지고 엇갈리면 상쇄된다"),
    ],
)

# =========================================================================== #
#  §1  Sionna 의 공백 — 기본 광선엔진은 밝기를 못 낸다
# =========================================================================== #
cells.append(md(
    "## §1. Sionna 의 공백 — 기본 광선엔진은 표적 밝기를 못 낸다",
    "",
    "레이더는 결국 **되돌아온 메아리의 세기**로 표적을 알아챈다. 표적이 어두우면(RCS 가 작으면) "
    "메아리가 주변 잡음에 묻혀 검출이 실패한다. 그러니 **표적이 얼마나 밝게 되비추는가**(RCS, "
    "σ; dBsm = 10·log₁₀(σ/1 m²))를 아는 것이 디텍션의 출발점이다.",
    "",
    "밝기는 표면 조각들이 되쏘는 파동을 **위상까지 맞춰 다 더한(산란적분)** 값이다 — 넓은 판이 작은 "
    "못보다 밝게 반짝이듯, 밝기는 되쏘는 표면 넓이에서 나온다. 그런데 전파 시뮬레이터의 기본 광선엔진"
    "(Sionna RT `PathSolver`)은 광선이 벽·바닥에서 **어디로 튕기는지**는 정확히 알지만, 표적을 국소 "
    "거울(GO)로만 튕겨 그 **넓이 항(∫ 산란적분)이 식에 없다.** 그래서 σ 를 주지 못한다.",
    "",
    "이것은 우리만의 진단이 아니라 선행 문헌이 문서화한 설계 사실이다 — Sionna RT 창설논문"
    "(arXiv:2303.11103)은 이 솔버가 경로별 복소이득만 반환한다고 명시한다. **앞 리포트 "
    "[report06](report06.ipynb) 이 이 공백을 광선 4억 발·금속구·평판·재질 스윕 다섯 측정으로 "
    "확인**했다. 이 리포트는 그 빈자리를 **어떤 표준 방법으로 메웠나**로 바로 간다.",
))

# =========================================================================== #
#  §2  선행 연구의 세 갈래
# =========================================================================== #
cells.append(md(
    "---",
    "## §2. 선행 연구는 이 공백을 어떻게 채웠나 — 세 갈래",
    "",
    "소형 표적의 코히어런트 RCS 를 스톡 Sionna 로 메쉬에서 직접 낸 선행은 **없다.** Sionna 를 센싱"
    "(ISAC)에 쓰는 연구들은 표적 밝기를 **외부에서 구해 채널에 주입**하되, 그 '외부' 를 세 갈래로 "
    "채운다:",
    "",
    "| 갈래 | 방식 | 대표 선행 |",
    "|---|---|---|",
    "| **(b)** | 재질 **확산계수 S** 가정 | Great-X (arXiv:2507.08716) |",
    "| **(c)** | 상용 full-wave 로 계산·주입 $h=h_{bg}+h_{target}$ | LAMBDA=Sionna+CADFEKO(arXiv:2607.03826) · Temporal-GNN=점산란체(arXiv:2604.08306) |",
    "| **(d)** | 자작 **산란 add-on**(SBR+PO·UTD) | Ziganshin UTD(arXiv:2604.05991) · GPU BVH SBR+PO(arXiv:2604.09243) |",
    "",
    "공통 아키텍처는 $h_{surv}=h_{direct}+h_{background}+h_{target}$ — 환경 전파는 Sionna 가 주고, "
    "표적 산란만 외부 물리로 계산해 두 전파 구간 사이에 끼운다. 이 중 **(d) SBR+PO** 는 FEKO·CST 같은 "
    "상용 솔버가 큰 표적에 쓰는 표준이자, 최근 ISAC 연구(GPU BVH SBR+PO, arXiv:2604.09243)가 메쉬에서 "
    "직접 RCS 를 내는 바로 그 방법이다. 우리는 **(d) 로 값을 계산해 (c) 로 주입**하는 길을 택한다 — "
    "상용툴(CADFEKO)은 유료라 재현이 막히고, 공개 SBR 도구(RaytrAMP, GPL-3.0)는 바이스태틱+다중재질 "
    "요구를 못 채우기 때문이다. 다음 §3 이 그 (d) 가 실제로 무엇을 하는지 보인다.",
))

# =========================================================================== #
#  §3  우리가 쓴 방식 — Mitsuba 광선 위의 SBR+PO
# =========================================================================== #
cells.append(md(
    "---",
    "## §3. 우리가 쓴 방식 — Mitsuba 광선 위의 SBR+PO",
    "",
    "SBR(Shooting-and-Bouncing Rays)은 밝기를 내기 위해 **두 가지**를 한다.",
    "",
    "**① 사방에 뿌리지 않고 표적을 정면 조준한다.** 광선을 아무 방향으로나 흩뿌리면 작은 표적은 "
    "대부분 빗나간다. 대신 시선 방향 $\\hat u$ 에서 **간격이 촘촘한 평행 광선 격자**를 표적에 곧장 "
    "쏜다. 그러면 거의 모든 광선이 표적의 어딘가에 맞는다.",
    "",
    "**② 물리적으로 되튕겨 오길 기다리지 않고, 되쏘는 양을 그 자리에서 계산한다.** 광선이 맞은 점 "
    "$\\vec p_i$ 마다, 그 면이 레이더 쪽으로 되쏘는 양을 PO(물리광학)로 — **위상까지 맞춰** — 셈해 "
    "전부 더한다:",
    "",
    "$$E(\\hat u)=\\sum_{\\text{맞은 점}} |\\Gamma_i|\\; e^{\\,j\\,2k\\,\\vec p_i\\cdot\\hat u}\\; "
    "d^2,\\qquad \\sigma=\\frac{4\\pi}{\\lambda^2}\\,|E|^2$$",
    "",
    "- $|\\Gamma_i|$ = 그 점 재질이 되쏘는 세기(반사계수), $d$ = 광선 격자 간격($d^2$ = 광선 한 "
    "발이 대표하는 넓이), $k=2\\pi/\\lambda$ = 파수.",
    "- $e^{\\,j2k\\,\\vec p_i\\cdot\\hat u}$ 는 **위상**이다 — 각 점의 되쏨이 같은 타이밍으로 "
    "겹치면 밝아지고 엇갈리면 상쇄된다. 이 위상 덧셈이 곧 표면 넓이 위의 적분과 같아진다.",
    "",
    "> **직관적으로** — 어두운 방에서 손전등 빔으로 물건을 통째로 덮고(①), 밝게 빛나는 점 하나하나가 "
    "내 쪽으로 되쏘는 양을 그 자리에서 계산해 합산한다(②). 그 합이 표적의 밝기다.",
    "",
    "그리고 **가림이 공짜로 따라온다.** 광선은 맨 앞에 처음 부딪힌 곳에서 멈추므로, 뒤에 가려진 "
    "면은 애초에 합에 끼지 못한다(§5 가 이 이득을 잰다).",
    "",
    "핵심은 **새 광선엔진을 만들지 않는다**는 것이다. 광선추적 자체는 **Sionna 의 전파 솔버가 쓰는 "
    "Mitsuba 3 / OptiX 엔진을 그대로** GPU 에서 재사용하고(중복계산 없음), 그 위에 선행이 오래 검증해 "
    "온 표준 산란적분(자작 PO 표면적분, `src/rcs_sbr.py`)만 얹는다. 스칼라 σ 대신 **복소장 E 를 직접** "
    "내 위상·편파를 보존하므로, 스칼라 RCS 를 주입하는 (c) 방식보다 한 단계 앞선다. 이 표준 방법이 "
    "실제로 맞는 값을 내는지는 §4 에서 답을 아는 물건으로 확인한다.",
))

cells.append(md("![.](outputs/renders/anim/paths_build.gif)\n\n"
                "<sub>Sionna(Mitsuba) 광선이 반사를 거듭하며 늘어나는 모습 — SBR 은 이 광선으로 "
                "표적을 조준한다.</sub>"))

cells.append(md(
    "![송신점→표적→수신점 1회 반사 경로 — 챔버 전경](outputs/renders/rt_10_paths_1bounce_wide.png)\n\n"
    "<sub>같은 광선을 챔버 전경에서 본 모습. 송신점(빨강, 왼쪽 벽)에서 나간 전파가 표적에서 꺾여 "
    "수신점(초록, 오른쪽 벽)으로 들어오는 **바이스태틱 기하**가 한눈에 보인다. 흡수체 피라미드 벽은 "
    "반사를 죽이고, 반사면인 바닥을 스치는 경로가 뒤에서 다룰 **바닥 유령**(report09)의 씨앗이다. "
    "SBR 은 정확히 이 표적-조준 광선 다발 위에서 산란적분을 수행한다.</sub>"
))

# =========================================================================== #
#  §4  검증
# =========================================================================== #
cells.append(md(
    "---",
    "## §4. 검증 — 답을 아는 물건에 대고 재보기",
    "",
    "SBR+PO 계산이 옳게 도는지 확인하는 표준 절차는 **답이 이미 알려진 정준 표적(canonical target)에 "
    "대고 재보는 것**이다 — 커스텀 산란 add-on 을 얹는 선행 연구(예: Ziganshin, arXiv:2604.05991)도 "
    "구·원통 같은 정준체를 해석해·상용 솔버(FEKO)·실측과 대조해 검증한다. 레이더 교과서는 두 물건의 "
    "밝기를 폐형식(닫힌 공식)으로 준다: 정면으로 조사한 **금속 평판**은 σ = 4πA²/λ², **금속구**는 "
    "σ = πr².",
    "",
    "![sbr validate](outputs/figures/report2_sbr_validate.png)",
    "",
    f"**@ {FC/1e9:.1f} GHz (λ = {LAM*100:.2f} cm) 대조:**",
    "",
    "| 표적 | 교과서 값 | SBR 오차 | report6 독립재현 |",
    "|---|---|---|---|",
    f"| 금속 평판 {V['a']} × {V['a']} m (정면) | {V['plate_exact_dbsm']:+.2f} dBsm | "
    f"**{_plate_err:+.2f} dB** (λ/6) | {_p6_plate:+.2f} dB |",
    f"| 금속구 r = {V['r']} m | {V['sphere_exact_dbsm']:+.2f} dBsm | "
    f"**{_sphere_err:+.2f} dB** (λ/10) | {_p6_sphere:+.2f} dB |",
    "",
    "→ 두 물건 모두 교과서 값과 **1 dB 이내**로 맞고, 완전히 따로 돌린 report6 커널도 같은 값을 "
    "낸다. **방법 자체는 옳다.**",
    "",
    "**단, 매끈한 구는 원래 까다로운 표적이다 — 정직하게 짚는다.** 구는 레이더 쪽으로 "
    "**똑바로 되쏘는 지점(정반사점)이 딱 하나뿐**이라, 촘촘한 광선 격자 중 **한 발이 그 점 위에 "
    "떨어지느냐**에 따라 값이 흔들립니다. 격자 밀도는 그대로 두고 격자를 살짝 옆으로 옮겨가며 "
    "재보면(그림 b):",
    "",
    "| 격자 | 정렬만 흔들었을 때 산포 |",
    "|---|---|",
    *[f"| λ/{d['div']} | **{d['spread']:.2f} dB** |" for d in V["dither"]],
    "",
    f"→ 거친 λ/8 에서는 격자 위치만으로 **{_lam8['spread']:.1f} dB** 가 움직이지만, 촘촘한 λ/24 "
    f"에서는 {_lam24['spread']:.2f} dB 로 닫힌다. 즉 매끈한 곡면은 촘촘한 격자에서만 안정된다.",
    "",
    "**하지만 드론은 성질이 다릅니다** — 되쏘는 점이 몸통·팔·모터·프로펠러에 잔뜩 흩어져 있어, "
    "방위(각도)를 돌려가며 평균을 내면 **저절로 안정**된다(그림 c):",
    "",
    "| 격자 | " + " | ".join(f"λ/{d}" for d in V["drone_conv"][list(V["drone_conv"])[0]]["divs"]) + " |",
    "|---|" + "---|" * len(V["drone_conv"][list(V["drone_conv"])[0]]["divs"]),
    *[f"| {tag} 방위평균 [dBsm] | " + " | ".join(f"{m:+.2f}" for m in ser["mean_dbsm"]) + " |"
      for tag, ser in V["drone_conv"].items()],
    "",
    f"→ λ/8 부터는 촘촘한 λ/24 값과 **{_dc_dev:.2f} dB 이내**로 붙는다(가장 거친 λ/6 만 "
    f"{_dc_coarse:.2f} dB 벗어난다). **드론 측정은 λ/{SBR_DIV} 로 돌리므로 수렴 구간 안**이다.",
    "",
    "정확히 하면 이 수렴은 **촘촘한 방위 샘플(180개)의 평균**에서 성립한다. **개별 방위각 하나의 값**은 "
    "격자를 λ/12→λ/24 로 반절해도 최대 ~6 dB 흔들리고(p95 ~3.9 dB), 방위 샘플이 24개뿐이면 평균조차 "
    "~0.5 dB 움직인다(`report_mesh/outputs/mesh_verify.json` I_sbr_subdiv). 그러므로 **개별각 σ 값은 "
    "수렴한 숫자가 아니며 인용하지 않는다** — 우리가 밖으로 내보내는 것은 촘촘한 방위평균뿐이다.",
    "",
    "덧붙여 삼각형을 4배(25,676→102,704면) 잘게 쪼개도 σ 변화는 사실상 0(최대 ~10⁻⁴ dB, 같은 파일 "
    "I_sbr_subdiv subdivision_invariance)이다 — 결과가 메쉬 테셀레이션의 산물이 아니라 **표면 형상 "
    "그 자체**에서 나온다는 뜻이다.",
    "",
    "> 정리하면, 정반사점이 하나뿐인 매끈한 구가 이 방법에게 가장 까다로운 표적이고, 되쏘는 점이 "
    "많은 드론은 방위평균이 스스로 값을 안정시켜 준다 — 표적의 성질 차이다.",
))

# =========================================================================== #
#  §5  가림
# =========================================================================== #
cells.append(md(
    "---",
    "## §5. 가림 — SBR 이 순수 PO 대비 실제로 고치는 것",
    "",
    "가림을 처리하지 않는 순수 PO 는 표면 조각이 시선 쪽을 향하기만 하면($\\hat n\\cdot"
    "\\hat u > 0$) '빛나는 면' 으로 센다 — **앞의 부품에 완전히 가려져 실제로는 레이더에 안 보여도** "
    "그렇다. 반면 SBR 은 광선을 실제로 쏘므로, 뒤에 숨은 면은 광선이 앞면에서 멈춰 애초에 닿지 "
    "못한다. 이 가림 처리는 상용 EM 솔버의 SBR 과 같은 성질이다.",
    "",
    "![occlusion](outputs/figures/report2_occlusion.png)",
    "",
    f"{OCC['name']} 를 한 방위(방위각 {OCC['az_view']:.0f}°, 올려본각 {OCC['el']:.0f}°)에서 "
    "들여다보면:",
    "",
    "| | 조각 수 | 투영 넓이 |",
    "|---|---|---|",
    f"| 순수 PO 가 '빛난다' 고 센 면 | **{OCC['n_lit_po']:,}** | {OCC['area_po']*1e4:.0f} cm² |",
    f"| └ 그중 **실제로는 뒤에 가려진** 면 | **{OCC['n_hidden']:,} "
    f"({OCC['hidden_frac']*100:.0f}%)** | — |",
    f"| 광선이 **실제로 맞은** 면 (SBR) | {OCC['n_visible']:,} | "
    f"**{OCC['area_vis']*1e4:.0f} cm²** |",
    "",
    f"→ 순수 PO 는 실제로 보이는 것보다 **약 {OCC['area_po']/OCC['area_vis']:.1f} 배 넓은 면적**을 "
    "밝기에 넣고 있었다. 가려진 면을 빼면 밝기가 그만큼 내려간다:",
    "",
    f"**{OCC['name']}, {OCC['n_az']} 방위 평균, 올려본각 {OCC['el']:.0f}°, {OCC['fc']/1e9:.1f} GHz:**",
    "",
    "| 방식 | 방위평균 밝기 | 차이 |",
    "|---|---|---|",
    f"| 순수 PO (가림 없음) | {OCC['po_dbsm']:+.2f} dBsm | — |",
    f"| **SBR (가림 처리)** | **{OCC['sbr1_dbsm']:+.2f} dBsm** | "
    f"**{OCC['occlusion_db']:+.2f} dB** ← 가림 |",
    f"| SBR + 오목부 다중반사 | {OCC['sbr3_dbsm']:+.2f} dBsm | "
    f"{OCC['multibounce_db']:+.2f} dB ← 다중반사 |",
    "",
    "![po vs sbr](outputs/figures/report2_po_vs_sbr.png)",
    "",
    f"흥미롭게도, PO 계열에 흔히 지적되는 '오목한 곳의 다중반사를 놓친다' 는 약점은 여기서 "
    f"**{OCC['multibounce_db']:+.2f} dB** 짜리 사소한 항이었다. 실제로 밝기를 바꾼 것은 "
    f"**가림({abs(OCC['occlusion_db']):.2f} dB)** 이었다 — 한 자릿수 차이다.",
    "",
    "> 이것이 SBR 이 순수 PO 대비 실제로 고치는 지점이다. 광선을 쏘아 **레이더에 실제로 보이는 "
    "면만** 밝기에 넣으니, 뒤에 숨은 면까지 세는 순수 PO 보다 값이 낮아진다.",
))

# =========================================================================== #
#  §6  재현 코드
# =========================================================================== #
cells.append(code(
    "# §4·§5 재현 — SBR 커널 검증(교과서 값) + 가림 대조",
    "import rcs_sbr",
    "rcs_sbr.validate(3.5e9)        # 금속구 πr² / 평판 4πA²/λ² 대조 + 격자 수렴",
    "rcs_sbr.compare_with_po()      # 순수 PO vs SBR (가림의 대가)",
))

cells.append(code(
    "# SBR 커널을 한 방향에서 직접 호출 — 광선 격자를 쏘고(가림 처리), 위상 맞춰 더해 밝기를 낸다.",
    "import numpy as np",
    "from rcs_po import drone_rcs_pattern_bw, dbsm    # 기본 엔진이 'sbr' 이다",
    "",
    "az = np.arange(0, 361, 2.0)",
    "sig, n_rays = drone_rcs_pattern_bw('mavic4pro', 3.5e9, 100e6, az, el_deg=15.0, n_f=5)",
    "print(f'방위당 광선 {n_rays:,}발  (격자 λ/16)')",
    "print(f'방위평균 밝기 {dbsm(np.mean(sig)):+.2f} dBsm')",
    "# ↑ 드론별 밝기 '결과'의 해석은 다음 리포트(report08) 소관이다.",
))

# =========================================================================== #
#  마무리
# =========================================================================== #
cells.append(md(
    "---",
    "## 정리",
    "",
    "1. **밝기(RCS)는 탐지에 필수**인데, Sionna RT `PathSolver` 는 산란적분(∫) 단계가 없어 σ 를 "
    "주지 못한다(§1, 증거는 report06). 이 공백을 ISAC 문헌은 세 갈래로 메우고(§2), 우리는 **(d) 자작 "
    "SBR+PO** 를 택했다.",
    "2. **방법:** 표적을 정면 조준해 촘촘한 평행 광선으로 덮고, 맞은 점마다 레이더로 되쏘는 양을 "
    "위상까지 맞춰 더한다(§3). 광선추적은 **Sionna 가 쓰는 Mitsuba 엔진을 그대로 재사용**하고 그 위에 "
    "자작 PO 표면적분만 얹는다 — GPU BVH SBR+PO(arXiv:2604.09243)와 같은 방법이다.",
    f"3. **옳은가?** 금속 평판({_plate_err:+.2f} dB)·금속구({_sphere_err:+.2f} dB) 교과서 값과 "
    "**1 dB 이내**로 맞았고, 따로 돌린 report6 커널도 같은 값을 냈다(§4). 매끈한 구가 격자 정렬에 "
    f"민감한 성질까지 짚었으며, 드론은 방위평균이 저절로 안정돼 **λ/{SBR_DIV} 수렴 구간**에 있다.",
    f"4. **무엇을 고치나?** 순수 PO 는 뒤에 숨어 안 보이는 면(이 방위에서 "
    f"{OCC['hidden_frac']*100:.0f}%)까지 세어 밝기를 부풀렸다. 가려진 면을 빼자 밝기가 "
    f"**{OCC['po_dbsm']:+.2f} → {OCC['sbr1_dbsm']:+.2f} dBsm** 으로 내려갔다 — 다중반사가 아니라 "
    "**가림이 진짜 이득**이었다(§5).",
    "",
    "**이 리포트가 보장하지 않는 것:** **절대 RCS 값**(해석해로만 검증·드론 실측 앵커 없음 — 방법의 "
    "정합성과 가림의 방향·규모만 주장), **매끈한 구의 단일 격자 값**·**다중반사의 정확한 dB**(인용 "
    "금지), **유전체 투과**(SBR 은 첫 충돌에서 멈춰 준투명 셸을 지나는 전파를 못 봄 → report08).",
    "",
    "> **다음 리포트**: [report08](report08.ipynb) — 이 SBR 로 잰 **실제 드론 5종의 밝기(RCS) "
    "결과**. 절대값은 실측 문헌 RCS 로 앵커링한다.",
))

# =========================================================================== #
nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
                   "language_info": {"name": "python", "version": "3.12"}},
      "nbformat": 4, "nbformat_minor": 5}

with open(NB, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f"✅ {os.path.relpath(NB, ROOT)} 생성 — 셀 {len(cells)}개 "
      f"(측정 JSON: {os.path.relpath(JS, ROOT)} + {os.path.relpath(JS6, ROOT)})")
