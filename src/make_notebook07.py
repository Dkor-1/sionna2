# -*- coding: utf-8 -*-
"""make_notebook07.py — report07.ipynb 생성기

report07 — **SBR: 표적을 조준해 밝기를 계산하다**
질문: **"Sionna 가 못 내는 RCS 를 어떻게 계산했나?"**

⚠ 노트북은 **생성물**이다. report07.ipynb 를 직접 고치지 말고 이 파일을 고쳐 다시 실행할 것.
⚠ 본문 수치는 전부 **측정 JSON 에서 읽어 주입**한다 — 그림과 글이 어긋날 수 없다.
   · outputs/report2_waveform_rcs.json 의 sbr_validation / occlusion
     (그림 report2_sbr_validate.png · report2_occlusion.png 과 같은 소스)
   · outputs/report6_sbr.json 의 kernel — **같은 커널을 같은 인자로 다시 부른 값**
     (viz_report2.py:588-589 ↔ viz_verify_sbr.py:107-108 이 동일 호출) → 독립 검증이 아니라 회귀 확인
   · report_mesh/outputs/mesh_verify.json 의 I_sbr_subdiv (광선격자·삼각형 세분 민감도)
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
JSM = os.path.join(ROOT, "report_mesh", "outputs", "mesh_verify.json")


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
with open(JSM) as f:
    JM = json.load(f)

M = J["meta"]
V = J["sbr_validation"]      # 커널 해석해 검증 + 격자수렴 + 디더 + 드론수렴
OCC = J["occlusion"]         # 가림의 대가 (한 표적, 한 실험)
K6 = J6["kernel"]            # report6 이 **같은 커널을 같은 인자로** 다시 부른 값 (회귀 확인)

# 광선격자 / 삼각형 세분 민감도 (report_mesh 원장)
ISB = JM["I_sbr_subdiv"]
RAY = ISB["ray_spacing_convergence"]     # λ/12 → λ/24
SUB = ISB["subdivision_invariance"]      # 삼각형 4배 세분

SBR_DIV = M["sbr_div"]       # 실제 드론 측정에 쓰는 격자밀도 (λ/16)
FC = V["fc"]
LAM = V["lam"]

# 대표 격자에서의 오차 (검증 헤드라인)
_plate_err = V["plate_err"][V["divs"].index(6)]         # 평판 @ λ/6
_sphere_err = V["sphere_err"][V["divs"].index(10)]      # 금속구 @ λ/10
# 우리가 실제로 드론에 쓰는 격자(λ/16)에서의 값 — 체리픽 방지용으로 함께 싣는다
_plate_ours = V["plate_err"][V["divs"].index(SBR_DIV)]
_sphere_ours = V["sphere_err"][V["divs"].index(SBR_DIV)]
# λ/8 이상(실사용 후보 격자)에서 구 오차가 가장 큰 지점 — 단조수렴이 아님을 정직히 보인다
_sphere_worst_div, _sphere_worst = max(
    [(d, e) for d, e in zip(V["divs"], V["sphere_err"]) if d >= 8], key=lambda t: abs(t[1]))
# report6 이 같은 커널을 같은 인자로 다시 부른 값 (독립 구현이 아니다 → 회귀 확인)
_p6_plate = K6["plate_err"][K6["divs"].index(6)]
_p6_sphere = K6["sphere_err"][K6["divs"].index(10)]

# 평판 오차가 격자밀도에 대해 **비트 단위로 반복**되는 짝 — 위상항이 상수라는 지문
def _plate_twin(div, tol=1e-9):
    ref = V["plate_err"][V["divs"].index(div)]
    return [d for d, e in zip(V["divs"], V["plate_err"]) if abs(e - ref) < tol]


_ptwin_a = _plate_twin(6)     # {6, 12, 30}
_ptwin_b = _plate_twin(8)     # {8, 16}

# 같은 가림 대가를 다른 조건(방위 36점 · SBR 격자 λ/12)에서 잰 report6 원장
OCC6 = J6["compare"][OCC["drone"]]
NAZ6 = J6["n_az"]

# 디더(정렬만 흔들기) 산포
_dith = {d["div"]: d for d in V["dither"]}
_lam8, _lam24 = _dith[8], _dith[24]
_lam_ours = _dith[SBR_DIV]

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

# 같은 격자 반절(λ/12→λ/24)을 방위 180점 평균에서 재면 얼마나 움직이나 (drone_conv 원장)
_d1224 = [abs(_s["mean_dbsm"][_s["divs"].index(12)] - _s["mean_dbsm"][_s["divs"].index(24)])
          for _s in V["drone_conv"].values()]
_dc_1224_lo, _dc_1224_hi = min(_d1224), max(_d1224)

# 기체 대각 범위 [cm] — §6 UTD 유효조건(facet E > 1.5λ) 대조용 (JSON diagonal_mm → cm)
_diags = [v["diagonal_mm"] for v in J["rcs"]["drones"].values()]
_diag_lo_cm, _diag_hi_cm = min(_diags) / 10.0, max(_diags) / 10.0

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
               "[Ziganshin=Sionna-RT+UTD, arXiv:2604.05991] (§2)."),
        lib=("**(d)** 를 택했다 — 새 광선엔진을 만들지 않는다. Sionna 가 쓰는 **Mitsuba 3 / OptiX 광선을 "
             "그대로 재사용**(중복계산 회피)하고 그 위에 **자작 PO 표면적분**(`src/rcs_sbr.py`, 가림 포함)만 "
             "얹는다. GPU BVH SBR+PO(arXiv:2604.09243)와 **같은 계열**이다(적용범위는 다르다 — 그들은 PEC·"
             "모노스태틱 후방산란 전용, 우리는 다중재질·바이스태틱; report06 §4)(§3)."),
        verify=(f"답을 아는 정준 표적에 **단일 입사방향 후방산란**으로 대고 재본다 — 금속 평판 "
                f"σ=4πA²/λ² 오차 **{_plate_err:+.2f} dB**(정면입사라 위상항이 상수 → 이건 *면적 구적* "
                f"확인이지 위상·파장 검증이 아니다), 곡면인 금속구 σ=πr² 오차 **{_sphere_err:+.2f} dB** "
                f"@λ/10 이지만 격자밀도에 **단조롭지 않아** λ/{_sphere_worst_div} 에서 "
                f"{_sphere_worst:+.2f} dB, 우리 설정 λ/{SBR_DIV} 에서 {_sphere_ours:+.2f} dB "
                f"(@{FC/1e9:.1f} GHz). report6 원장의 {_p6_plate:+.2f}/{_p6_sphere:+.2f} dB 는 **같은 "
                f"커널을 같은 인자로 다시 부른 회귀 확인**이지 독립 재현이 아니다(§4). 절대값 앵커는 report08."),
    ),

    sources=[
        dict(item="검증 기준 (정답)",
             src="교과서 폐형식 — 금속구 σ = πr² (광학영역) · 금속평판 σ = 4πA²/λ² (정면 조사)",
             kind="📐 해석해"),
        dict(item="SBR 검증·격자수렴·가림 측정값",
             src="**`outputs/report2_waveform_rcs.json`** 의 `sbr_validation` / `occlusion` "
                 "(그림 `report2_sbr_validate.png` · `report2_occlusion.png` 과 같은 소스)",
             kind="🟡 측정 (SBR = 우리 구현, Mitsuba 광선)"),
        dict(item="같은 커널의 회귀(재현) 확인",
             src="**`outputs/report6_sbr.json`** 의 `kernel` — 다른 스크립트에서 **같은 함수를 같은 "
                 "인자로** 다시 부른 값(`viz_report2.py:588-589` ↔ `viz_verify_sbr.py:107-108`). "
                 "결정론적 동일 코드경로라 값이 같은 것이 당연하다 — **독립 구현 대조가 아니다**",
             kind="🟡 회귀 확인 (독립 검증 아님)"),
        dict(item="광선격자·삼각형 세분 민감도",
             src="**`report_mesh/outputs/mesh_verify.json`** 의 `I_sbr_subdiv` "
                 "(λ/12→λ/24 재계산 · 삼각형 4배 세분)",
             kind="🟡 측정 (report_mesh 원장)"),
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
        "# 같은 커널을 같은 인자로 다시 부르는 회귀 확인 (report6_sbr.json kernel)",
        "~/.venvs/py312/bin/python src/viz_verify_sbr.py",
        "",
        "# JSON -> report07.ipynb (이 파일)",
        "~/.venvs/py312/bin/python src/make_notebook07.py",
    ],

    artifacts=[
        dict(file="outputs/report2_waveform_rcs.json",
             what="**이 노트북의 SBR 숫자.** sbr_validation / occlusion 블록"),
        dict(file="outputs/report6_sbr.json",
             what="같은 커널을 같은 인자로 다시 부른 회귀 확인 (kernel 블록)"),
        dict(file="report_mesh/outputs/mesh_verify.json",
             what="§4 광선격자 민감도 · 삼각형 세분 불변성 (I_sbr_subdiv 블록)"),
        dict(file="outputs/figures/report2_sbr_validate.png",
             what="§4 SBR 검증 · 격자 수렴"),
        dict(file="outputs/figures/report2_occlusion.png",
             what="§5 가림 — 순수 PO vs SBR"),
        dict(file="outputs/figures/report2_po_vs_sbr.png",
             what="§5 방위 패턴 비교"),
    ],

    caveats=[
        "**절대 RCS 는 문헌 실측보다 밝은 쪽으로 치우친다 — 신뢰의 중심에 두지 않는다.** SBR 은 "
        "해석해(구·평판)로 교정되지만, 절대 dBsm 을 문헌과 견주면 **크기가 맞는 짝끼리 aspect-peak ↔ "
        "aspect-peak** 으로 보아 우리 쪽이 위로 치우친다(정량치와 짝짓기 규약은 report08 §6). "
        "few-λ(공진영역)에서 PO 가 절대레벨을 밝은 쪽으로 잡는 경향이 유력한 설명이다. "
        "이 리포트가 지지하는 것은 방법의 정합성·상대 패턴이지 절대 dBsm 의 정밀값이 "
        "아니며, 검출 결과는 σ 밴드로 제시해 상대 결론의 robust 함을 보인다. "
        "⚠ '소형드론 방위평균 포락선 −28~−16 dBsm' 은 문헌이 직접 보고한 값이 아니라 aspect-peak 과 자세 "
        "스프레드에서 우리가 유도한 2차 산물이므로 판정 근거로 쓰지 않는다(report08 §6).",

        "**격자 위상 진동은 지터평균으로 잡되, 완전히 없어지지는 않는다.** 곡면은 광선격자를 어디에 "
        f"맞추느냐에 절대레벨이 흔들린다 — 정렬만 흔든 산포가 λ/8 {_lam8['spread']:.2f} dB, "
        f"우리 설정 λ/{SBR_DIV} {_lam_ours['spread']:.2f} dB, λ/24 {_lam24['spread']:.2f} dB. "
        f"서브셀 오프셋 격자를 평균하면 잔차가 λ/8 {_lam8['avg_err']:+.2f} → "
        f"λ/{SBR_DIV} {_lam_ours['avg_err']:+.2f} → λ/24 {_lam24['avg_err']:+.2f} dB 로 줄지만, "
        f"**우리 격자에서는 아직 {abs(_lam_ours['avg_err']):.2f} dB 남아 있다.** 절대 dBsm 은 측정 "
        "앵커에 맡긴다 — §4.",

        "**오목한 곳의 다중반사(2·3차) 값은 규모(작다)만 신뢰한다.** SBR 이 실제로 고치는 것은 "
        "가림이고, 다중반사는 부차적이고 작은 항이다. 그 정확한 dB 값은 이 리포트의 주장이 아니다.",

        "**유전체 셸 투과는 1차 근사로 반영한다** — 준투명 플라스틱 셸(body·canopy)을 통과시켜 "
        "내부 금속(배터리·PCB)을 왕복 투과계수 τ=1−|Γ|² 로 코히런트 합산한다(안 하면 지배 산란체가 "
        "삭제되어 σ 가 ~1.3 dB 낮아진다). 단 셸의 굴절 굴곡·유전체 내부 위상지연은 무시하는 1차 투과다.",

        "**모서리·정점 회절은 비운다.** SBR+PO 는 정반사(specular) 항만 채우고 에지·정점 회절"
        "(E_edge·E_vertex)을 계산하지 않아 그림자 영역·깊은 널이 부정확하다. 우리와 가장 가까운 선행"
        "(Ziganshin, arXiv:2604.05991)은 SBR+PO 의 이 한계를 명시적으로 비판하며 UTD 로 그 항을 "
        "채우지만, 그 유효조건 facet E>1.5λ 는 few-λ 유전체 드론에서 성립하지 않는다 — 자세한 원장은 §6.",

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
    "이것은 우리만의 진단이 아니라 **NVIDIA 가 직접 확인**한 사실이다 — Sionna RT 창설논문"
    "(arXiv:2303.11103)은 이 솔버가 경로별 복소이득만 반환한다고 명시하고, Sionna 개발 메인테이너"
    "(J. Hoydis)는 커뮤니티 질문('광선을 대량 쏴 금속체 RCS 를 낼 수 있나')에 "
    "**\"This is currently not supported\"**(GitHub Discussion #844)라고 답했다. 즉 상세 mesh 표적 "
    "RCS 는 Sionna 기본 기능이 아니라 **사용자가 직접 얹어야 하는 부분**이다. **앞 리포트 "
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
    "| **(d)** | 자작 **산란 add-on**(SBR+PO·UTD) | Ziganshin=**Sionna-RT+UTD**(arXiv:2604.05991) · GPU BVH SBR+PO(arXiv:2604.09243·독립엔진) |",
    "",
    "<sub>같은 (d) 안에서도 **붙이는 층이 다르다** — Ziganshin 은 Sionna-RT 솔버 자체를 확장해 UTD 회절을 그 "
    "안에 넣고, 우리는 Sionna 가 쓰는 Mitsuba 광선엔진 위에 PO 표면적분을 따로 얹는다(`PathSolver` 는 상속 "
    "확장점이 아니다 — report06 §3).</sub>",
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
    "**⚠ 이 식이 채우는 것은 완전한 σ 의 한 단면뿐이다.** RCS 의 일반형은 입사방향과 산란방향의 "
    "**네 각도 함수** $\\sigma_{\\text{RCS}}(\\theta_{\\text{in}},\\phi_{\\text{in}};\\,"
    "\\theta_{\\text{out}},\\phi_{\\text{out}})$ 다. 위에서 입사와 산란을 **하나의 $\\hat u$** 로 함께 "
    "쓴 것은 $\\theta_{\\text{out}}=\\theta_{\\text{in}},\\ \\phi_{\\text{out}}=\\phi_{\\text{in}}$ 인 "
    "**후방산란(모노스태틱) 단면 한 장**만 채운다는 뜻이다 — 바이스태틱 일반형(임의 "
    "$\\hat u_{\\text{out}}\\neq\\hat u_{\\text{in}}$)의 경계는 §5·§6 에서 다룬다.",
    "",
    "> **직관적으로** — 어두운 방에서 손전등 빔으로 물건을 통째로 덮고(①), 밝게 빛나는 점 하나하나가 "
    "내 쪽으로 되쏘는 양을 그 자리에서 계산해 합산한다(②). 그 합이 표적의 밝기다.",
    "",
    "그리고 **가림이 공짜로 따라온다.** 광선은 맨 앞에 처음 부딪힌 곳에서 멈추므로, 뒤에 가려진 "
    "면은 애초에 합에 끼지 못한다(§5 가 이 이득을 잰다).",
    "",
    "**③ 준투명 셸은 통과시켜 안쪽 금속까지 본다.** 드론 후방산란을 실제로 지배하는 건 플라스틱 "
    "껍데기가 아니라 그 **안에 든 금속**(배터리 팩·PCB 그라운드플레인)이다. 플라스틱 셸은 반쯤 "
    "투명해서(|Γ|≈0.28 → 전력의 ~92% 가 통과) 파가 셸을 지나 내부 금속에 닿고 되돌아 나온다. "
    "그래서 셸에 맞은 광선은 **셸을 지운 장면으로 한 번 더 쏴** 내부 금속을 찾고, 왕복 투과계수 "
    "$\\tau=1-|\\Gamma_{\\text{shell}}|^2\\;(\\approx 0.92)$ 로 세기를 줄여 외부 기여와 **위상 맞춰 "
    "합산**한다. 이 단계가 빠지면 광선이 첫 충돌(셸)에서 멈춰 **지배적 산란체인 내부 금속이 통째로 "
    "빠지고**(직접 확인: 배터리·PCB 히트 0), 밝기가 약 **1.3 dB 낮게** 나온다 — 재질 모델이 셸 |Γ| 를 "
    "0.28 로 낮춘 전제('셸 통과 → 내부 금속 지배') 와 엔진이 어긋나던 자기모순을 이 투과가 없앤다. "
    "⚠ 얇은 셸의 굴절 굴곡·유전체 내부 위상지연은 아직 무시하는 1차 투과 근사다.",
    "",
    "핵심은 **새 광선엔진을 만들지 않는다**는 것이다. 광선추적 자체는 **Sionna 의 전파 솔버가 쓰는 "
    "Mitsuba 3 / OptiX 엔진을 그대로** GPU 에서 재사용하고(중복계산 없음), 그 위에 선행이 오래 검증해 "
    "온 표준 산란적분(자작 PO 표면적분, `src/rcs_sbr.py`)만 얹는다. 스칼라 σ 를 통째로 주입하는 대신 "
    "면 조각별 기여를 **복소장 E** 로 더해 **위상을 보존**하므로, 외생 σ 를 넣는 (c) 방식보다 한 단계 "
    "앞선다(⚠ 편파는 보존하지 않는다 — E 는 복소 스칼라이고 재질 반사도 스칼라 |Γ| 다). 이 표준 방법이 "
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
    "대고 재보는 것**이다 — Sionna-RT 에 커스텀 산란(UTD) add-on 을 얹는 선행 연구(예: Ziganshin, "
    "arXiv:2604.05991)도 "
    "구·원통 같은 정준체를 해석해·상용 솔버(FEKO)·실측과 대조해 검증한다. 레이더 교과서는 두 물건의 "
    "밝기를 폐형식(닫힌 공식)으로 준다: 정면으로 조사한 **금속 평판**은 σ = 4πA²/λ², **금속구**는 "
    "σ = πr².",
    "",
    "**검증 조건을 먼저 못박는다.** 이 대조는 **단일 입사방향의 후방산란 한 점**이다 — 구는 "
    "az = 0°·el = 0°, 평판은 정면(el = 90°)으로 한 방향만 쏜다"
    "(`viz_report2.py` `measure_sbr_validation()`). 방위평균도, 각도응답 곡선의 MAE 도 아니다. "
    "여기서 재는 것은 커널이 **한 방향에서** 옳은 크기를 내느냐이고, 방위 의존성은 아래 드론 "
    "수렴표와 report08 이 맡는다.",
    "",
    "![sbr validate](outputs/figures/report2_sbr_validate.png)",
    "",
    f"**@ {FC/1e9:.1f} GHz (λ = {LAM*100:.2f} cm) 대조:**",
    "",
    f"| 표적 | 교과서 값 | SBR 오차 | 우리 설정 λ/{SBR_DIV} | report6 재호출 |",
    "|---|---|---|---|---|",
    f"| 금속 평판 {V['a']} × {V['a']} m (정면) | {V['plate_exact_dbsm']:+.2f} dBsm | "
    f"**{_plate_err:+.2f} dB** (λ/6) | {_plate_ours:+.2f} dB | {_p6_plate:+.2f} dB |",
    f"| 금속구 r = {V['r']} m | {V['sphere_exact_dbsm']:+.2f} dBsm | "
    f"**{_sphere_err:+.2f} dB** (λ/10) | {_sphere_ours:+.2f} dB | {_p6_sphere:+.2f} dB |",
    "",
    "**이 표를 읽는 법 — 두 줄의 무게가 다르다.**",
    "",
    "**① 평판은 '엔진 검증' 이 아니라 '면적 구적(quadrature) 확인' 이다.** 정면입사(el = 90°)에서는 "
    "모든 히트의 위상항 $e^{j2k\\vec p\\cdot\\hat u}$ 가 **상수**가 되어 $E = |\\Gamma|Nd^2$, "
    "$\\sigma = (4\\pi/\\lambda^2)(Nd^2)^2$ 이고 기준 $4\\pi A^2/\\lambda^2$ 와의 비에서 **λ 가 항등적으로 "
    "소거된다.** 즉 이 줄이 재는 것은 '광선격자가 정사각형을 얼마나 잘 타일링하나' 뿐이고, 위상도 "
    "파장 의존도 들어가지 않는다. 실제로 오차가 격자밀도에 대해 **비트 단위로 반복**된다 — "
    f"λ/{'·λ/'.join(str(d) for d in _ptwin_a)} 가 {_plate_err:.6f} dB 로 동일, "
    f"λ/{'·λ/'.join(str(d) for d in _ptwin_b)} 가 "
    f"{V['plate_err'][V['divs'].index(8)]:.6f} dB 로 동일한 정수 정합성 지문이다. "
    "우리 커널 주석도 같은 말을 한다(`rcs_sbr.py`: *평판 정면은 위상항이 상수라 이 진동을 진단 못 "
    "한다*). **위상항이 살아 있는 비스듬한 입사로 다시 재는 것은 남은 과제다.**",
    "",
    f"**② 위상까지 검증하는 줄은 곡면인 구뿐이고, 그 값은 격자밀도에 단조롭지 않다.** λ/10 에서 "
    f"{_sphere_err:+.2f} dB 로 잘 맞지만 λ/{_sphere_worst_div} 에서는 {_sphere_worst:+.2f} dB, "
    f"실제로 드론에 쓰는 λ/{SBR_DIV} 에서는 {_sphere_ours:+.2f} dB 다. 즉 **'1 dB 이내' 는 특정 "
    "격자에서의 값이지 방법의 보증이 아니다** — 실루엣 근처 grazing 광선의 위상 에일리어싱이 남긴 "
    "진동이며, 아래 디더 표가 그 정체를 직접 보인다.",
    "",
    f"**③ report6 원장의 {_p6_plate:+.2f}/{_p6_sphere:+.2f} dB 는 독립 재현이 아니다.** 두 스크립트가 "
    "**같은 함수를 같은 인자로** 부른다(`viz_report2.py:588-589` ↔ `viz_verify_sbr.py:107-108`). "
    "결정론적 동일 코드경로라 값이 같은 것은 당연하고, 이것이 보증하는 것은 **다른 실행·다른 "
    "파이프라인에서도 같은 값이 나온다는 회귀 재현성**뿐이다. 독립 구현 대조로 읽으면 안 된다.",
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
    f"→ 거친 λ/8 에서는 격자 위치만으로 **{_lam8['spread']:.2f} dB** 가 움직이고, 우리 설정 "
    f"λ/{SBR_DIV} 에서도 {_lam_ours['spread']:.2f} dB 가 남으며, 촘촘한 λ/24 에서 "
    f"{_lam24['spread']:.2f} dB 로 닫힌다. 여러 오프셋 격자를 평균한 잔차도 같은 방향이다 — "
    f"λ/8 {_lam8['avg_err']:+.2f} → λ/{SBR_DIV} {_lam_ours['avg_err']:+.2f} → "
    f"λ/24 {_lam24['avg_err']:+.2f} dB. 즉 **매끈한 곡면의 단일 격자 값은 λ/24 급에서만 안정되고, "
    f"우리 격자에서는 정렬 산포 {_lam_ours['spread']:.2f} dB · 디더평균 잔차 "
    f"{_lam_ours['avg_err']:+.2f} dB 가 절대레벨에 남아 있다.**",
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
    "정확히 하면 이 수렴은 **촘촘한 방위 샘플(180개)의 평균**에서 성립한다. 같은 드론을 "
    f"λ/12 와 λ/24 로 각각 다시 계산해 보면(`report_mesh/outputs/mesh_verify.json` I_sbr_subdiv, "
    f"방위 {ISB['n_az']}점 · el {ISB['el_deg']:.0f}° · {ISB['fc_ghz']:.1f} GHz) **개별 방위각 하나의 "
    f"값**은 최대 {RAY['per_angle_absdiff_db']['max']:.2f} dB 흔들리고"
    f"(p95 {RAY['per_angle_absdiff_db']['p95']:.2f} · 평균 "
    f"{RAY['per_angle_absdiff_db']['mean']:.2f} dB), 그 방위 {ISB['n_az']}점 **평균**은 "
    f"{abs(RAY['azavg_dbsm']['diff']):.2f} dB 만 움직인다(같은 λ/12→λ/24 를 방위 180점으로 재면 "
    f"{_dc_1224_lo:.2f}~{_dc_1224_hi:.2f} dB). 즉 평균이 개별각 진동을 눌러 준다. 그러므로 "
    "**개별각 σ 값은 수렴한 숫자가 아니며 인용하지 않는다** — 우리가 밖으로 내보내는 것은 촘촘한 "
    "방위평균뿐이다.",
    "",
    f"덧붙여 삼각형을 4배({SUB['faces_base']:,}→{SUB['faces_fine']:,}면) 잘게 쪼개도 방위평균 σ 변화는 "
    f"{abs(SUB['azavg_dbsm']['diff']):.1e} dB(개별각 최대 "
    f"{SUB['per_angle_absdiff_db']['max']:.1e} dB, 같은 파일 subdivision_invariance)다. 다만 이것을 "
    "**광선격자 수렴의 증거로 읽어서는 안 된다** — PO 합의 구적점은 삼각형이 아니라 **광선 히트**라서, "
    "면을 중점분할해도 같은 표면·같은 히트가 남는다. 값이 같은 것은 표면이 같으므로 그렇고, 이 검사가 "
    "실제로 지키는 것은 **구현이 면 수에 의존하지 않는다**는 것이다(면별 가중이나 면별 지터가 섞여 "
    "들어갔다면 깨진다 — `report_mesh/src/verify_mesh_suite.py:376` 이 이 검사를 그 목적으로 적어 둔다). "
    "수치 놉은 삼각형 수가 아니라 위의 광선격자다.",
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
    f"**단, 가림 대가의 절대 dB 는 샘플링에 따라 갈린다 — 그래서 방향과 규모만 주장한다.** 같은 "
    f"기체·같은 올려본각을 조건만 바꿔(방위 {NAZ6}점, SBR 광선격자 λ/12) 다시 재면 "
    f"{OCC6['po_el15']:+.2f} → {OCC6['sbr_el15']:+.2f} dBsm 으로 가림이 "
    f"{OCC6['occl_el15']:+.2f} dB 다(`report6_sbr.json compare`). 위 표({OCC['n_az']}점, λ/{SBR_DIV})의 "
    f"{OCC['occlusion_db']:+.2f} dB 와 {abs(OCC['occlusion_db']-OCC6['occl_el15']):.2f} dB 차이가 나며, "
    "이는 §4 가 보인 광선격자·방위샘플 민감도와 같은 급이다. 우리가 주장하는 것은 **가림이 σ 를 "
    "내린다는 방향과 수 dB 급 규모**이지 특정 dB 값이 아니다.",
    "",
    "> 이것이 SBR 이 순수 PO 대비 실제로 고치는 지점이다. 광선을 쏘아 **레이더에 실제로 보이는 "
    "면만** 밝기에 넣으니, 뒤에 숨은 면까지 세는 순수 PO 보다 값이 낮아진다.",
    "",
    "**⚠ 스코프 — 여기서 다루는 가림도, 위의 σ 도 전부 '모노스태틱' 이다.** 이 절의 가시성 판정은 "
    "송·수신이 같은 방향($\\hat u_s = \\hat u_i$)이라는 전제 위에 서 있다. 우리 프로젝트는 패시브 "
    "**바이스태틱**이므로 이 전제는 자동으로 이어지지 않는다 — 조명원 쪽에서 보이는 면과 수신기 쪽에서 "
    "보이는 면이 갈리기 때문이다. 바이스태틱 일반형(`rcs_sbr.py` `rcs_sbr_multistatic()`)은 구현되어 "
    "있고 그 독스트링이 적용범위를 명시한다: 전방산란(β→180°)에서는 조명 게이트와 수신 게이트가 "
    "상호배타가 되어 **σ ≡ 0** 이 되고(그림자 복사 = Babinet 전방로브를 lit-PO 가 못 낸다), 비볼록 "
    "표적의 깊은 널에서는 **상반성 σ(û_i,û_s) = σ(û_s,û_i) 가 깨진다**. 따라서 이 리포트의 σ 는 "
    "**모노스태틱 등가값**으로 읽어야 하며, 바이스태틱 결론(report12)으로 그대로 상속되지 않는다.",
))

# =========================================================================== #
#  §6  선행의 비판 — 회절 항·이산화 기준
# =========================================================================== #
#  문헌 상수 (출처: Ziganshin, arXiv:2604.05991 — 원문 PDF 로 직접 확인한 절을 병기):
#    · SBR+PO 비판 원문 인용(§I) · E_total = E_direct + ΣE_specular + ΣE_edge + ΣE_vertex 분해
#    · UTD 유효조건 facet E > 1.5λ(§III-C·§V) · 후방산란 수렴 무릎 E²/(Rλ) ≈ 0.5(§V-C) · 차량 facet ≈ 0.4–0.6(§V-B)
#    ⚠ 원문 §III-C 는 최적 구간이 응용·산란기구에 따라 달라 "경험적으로 정해야 한다"고 명시 → ≈0.5 는
#      보편 임계값이 아니라 그들의 후방산란 수렴 무릎으로만 쓴다(노트는 0.4–0.6·E>1.5λ 만 인용).
#  ⚠ 우리 5기종 메쉬의 E²/(Rλ) 수치는 미산출(mesh_verify.json 에 없음) → 다음 단계에서 계산.
#    여기서는 기준을 소개·프레이밍만 하고, 확정 가능한 값(1.5λ·격자 mm·대각 cm)만 JSON 에서 유도해 넣는다.
cells.append(md(
    "---",
    "## §6. 선행이 우리 방법을 비판한다 — 회절 항과 이산화 기준",
    "",
    "§5 가 스스로 밝힌 한계(전방산란 σ≡0 · 상반성 부분성립 · 모노스태틱 등가)는 우연이 아니라 "
    "**SBR+PO 라는 방법 계열이 원래 갖는 경계**다. 같은 'Sionna-RT 확장' 계열에서 우리와 가장 가까운 "
    "선행인 Ziganshin(arXiv:2604.05991)은 바로 이 경계를 겨냥해 **SBR+PO 를 자기 방법"
    "(Sionna-RT + UTD 회절)의 대척점으로 명시적으로 비판**한다. 원문 그대로:",
    "",
    "> *\"This SBR+PO approach ... is limited to the illuminated region and is not suitable to "
    "predict the scattered field in the shadow region of the obstacle. Furthermore, the need to "
    "cascade PO after RT negates the computational advantages of RT.\"* — Ziganshin §I "
    "(arXiv:2604.05991)",
    "",
    "이 비판은 **절반은 정확하다.** §5 가 이미 자발적으로 공개했듯, lit-PO 는 **조명된 영역만** "
    "적분하므로 그림자 영역의 회절장(전방로브 = Babinet)을 못 내고 전방산란에서 σ≡0 이 된다. "
    "우리에게 빠져 있던 것은 **물리 인식이 아니라 이 선행을 인용해 그 경계를 명명하는 프레이밍**이었다 "
    "— 그 물리 자체는 `rcs_sbr.py` `rcs_sbr_multistatic()` 독스트링과 §5 가 이미 적고 있었다. "
    "(덧붙여 Ziganshin 은 자기 future work 로 *\"time-varying substructures (micro-Doppler)\"* 와 "
    "*\"drones\"* 를 지목하므로, 두 방법의 적용 영역이 겹치는 것도 사실이다.)",
    "",
    "### 전계 항목 원장 — 무엇을 채우고 무엇을 비우나",
    "",
    "Ziganshin 은 표적 산란장을 **네 항의 합**으로 분해한다. 우리 SBR+PO 가 어느 항을 채우는지 "
    "그 원장에 나란히 놓으면 우리 방법의 경계가 한눈에 보인다:",
    "",
    "$$E_{\\text{total}} = E_{\\text{direct}} + \\sum E_{\\text{specular}} + "
    "\\sum E_{\\text{edge}} + \\sum E_{\\text{vertex}}$$",
    "",
    "| 항 | 물리 | 우리 SBR+PO | Ziganshin RT+UTD |",
    "|---|---|---|---|",
    "| $E_{\\text{direct}}$ | 표적을 조명하는 입사장 / 직접경로 | ✅ (Sionna 광선 = `h_direct`) | ✅ |",
    "| $\\sum E_{\\text{specular}}$ | 표면 정반사·다중반사 (PO 표면적분) | ✅ **채운다** (§3·§5) | ✅ |",
    "| $\\sum E_{\\text{edge}}$ | 모서리 회절 (UTD wedge) | ❌ **비운다** | ✅ |",
    "| $\\sum E_{\\text{vertex}}$ | 정점(꼭짓점) 회절 | ❌ **비운다** | ✅ |",
    "",
    "즉 우리는 **정반사 항(specular)** 을 위상까지 맞춰 채우고 **회절 두 항(edge · vertex)은 비운다.** "
    "§5 가 자발적으로 공개한 '그림자 영역·깊은 널 부정확' 은 정확히 이 두 빈 항의 결과다.",
    "",
    "### 우리 반론 — few-λ 유전체 드론에서는 UTD 유효조건이 성립하지 않는다",
    "",
    "그러나 **그들의 처방(UTD 로 회절 항을 채우기)이 우리 표적에는 유효하지 않다.** Ziganshin 의 "
    "UTD 는 **facet 이 파장보다 충분히 커야**(유효 하한 E > 1.5λ) 성립하는 고주파 근사이고, 그들의 "
    "검증 대상은 **PEC 차량 · 구 · 원기둥**(2–10 GHz, 차량 facet 의 E²/(Rλ) ≈ 0.4–0.6)이다. 우리 "
    f"표적은 **부위별 유전체 소형 드론**으로, 기체 대각이 {_diag_lo_cm:.0f}~{_diag_hi_cm:.0f} cm 이고 "
    f"3.5 GHz 에서 UTD 유효 하한은 1.5λ ≈ {1.5 * LAM * 100:.0f} cm 다. 프로펠러 시위 · 암 폭 · 모터 · "
    "랜딩기어 같은 **개별 산란 특징의 대부분이 이 1.5λ 하한보다 작아**(공진영역), 회절 두 항을 UTD 로 "
    "채우는 것도 우리 영역에서는 원리적으로 정당화되지 않는다. 소형 유전체 드론의 few-λ 회절은 UTD 가 "
    "아니라 full-wave(MoM/FEKO)나 측정으로 앵커링해야 하며(report08), 그것이 이 프로젝트의 열린 "
    "과제다. (⚠ 이는 우리 lit-PO 가 회절을 낸다는 뜻이 아니다 — 우리도 그 두 항은 비어 있고, 다만 "
    "그들의 대안조차 이 영역에선 유효하지 않다는 것이다.)",
    "",
    "### 이산화 품질 — E²/(Rλ)",
    "",
    "Ziganshin 은 곡면을 facet 으로 쪼갤 때의 품질을 무차원 지표 **E²/(Rλ)** (E = facet 크기, "
    "R = 국소 곡률반경, λ = 파장)로 재고, 후방산란 정확도가 이 값이 작을수록 좋아지되 **≈0.5 부근에서 "
    "수렴(개선이 미미해지는 무릎)** 한다고 보고한다(자기 차량 facet ≈ 0.4–0.6). 원문은 최적 구간이 응용에 "
    "따라 달라 경험적으로 정해야 한다고 밝히므로 ≈0.5 는 보편 임계값이 아니라 그들의 수렴 무릎이다. 우리 "
    "PO 는 삼각형이 아니라 "
    "**광선 히트**를 구적점으로 쓰므로(§4 세분 불변성이 이를 직접 보인다), 실질 이산화 눈금은 삼각형 "
    f"크기가 아니라 **광선격자 간격**이다 — 3.5 GHz 에서 λ/{SBR_DIV} ≈ {LAM / SBR_DIV * 1000:.1f} mm"
    f"(수렴 연구는 λ/12 ≈ {LAM / 12 * 1000:.2f} mm → λ/24). 이 몇 mm 격자가 드론 facet 크기와 "
    "**같은 자릿수**이므로 **수치 병목은 삼각형 수가 아니라 광선격자 쪽**이다(§4 가 삼각형을 4배 "
    "세분해도 σ 가 사실상 불변임을 이미 보였다 — 놉은 격자다).",
    "",
    "⚠ **우리 5기종 메쉬의 E²/(Rλ) 값 자체는 아직 산출하지 않았다** — facet 별 모서리 길이 대 국소 "
    "곡률반경을 재는 이 지표는 현재 원장(`mesh_verify.json`)에 없고 **다음 단계에서 계산**한다. 지금 "
    "확정적으로 말할 수 있는 것은 **UTD 유효 하한 E > 1.5λ 가 우리 few-λ 특징에서 성립하지 않는다**는 "
    "정성적 사실까지다.",
))

# =========================================================================== #
#  §7  재현 코드
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
    "자작 PO 표면적분만 얹는다 — GPU BVH SBR+PO(arXiv:2604.09243)와 같은 계열이다"
    "(적용범위 차이는 report06 §4).",
    f"3. **옳은가?** 단일 입사방향에서 금속 평판({_plate_err:+.2f} dB @λ/6)·금속구"
    f"({_sphere_err:+.2f} dB @λ/10)이 교과서 값과 1 dB 이내였다(§4). 단 **평판 정면은 위상항이 상수라 "
    "면적 구적 확인**이고, 위상까지 거는 구는 격자밀도에 단조롭지 않다"
    f"(λ/{_sphere_worst_div} 에서 {_sphere_worst:+.2f} dB, 우리 λ/{SBR_DIV} 에서 "
    f"{_sphere_ours:+.2f} dB). report6 원장의 같은 값은 **같은 함수·같은 인자 재호출**이라 회귀 "
    f"확인이다. 드론 쪽은 방위평균이 저절로 안정돼 λ/{SBR_DIV} 가 수렴 구간 안이다.",
    f"4. **무엇을 고치나?** 순수 PO 는 뒤에 숨어 안 보이는 면(이 방위에서 "
    f"{OCC['hidden_frac']*100:.0f}%)까지 세어 밝기를 부풀렸다. 가려진 면을 빼자 밝기가 "
    f"**{OCC['po_dbsm']:+.2f} → {OCC['sbr1_dbsm']:+.2f} dBsm** 으로 내려갔다 — 다중반사가 아니라 "
    "**가림이 진짜 이득**이었다(§5).",
    "",
    "**이 리포트가 보장하지 않는 것:** **절대 RCS 값**(정준 표적 해석해로만 검증·드론 실측 앵커 "
    "없음 → report08 — 방법의 정합성과 가림의 방향·규모만 주장), **매끈한 구의 단일 격자 값**·"
    "**다중반사의 정확한 dB**(인용 금지), **위상·파장에 대한 평판 검증**(정면입사라 λ 가 소거된다 — "
    "비스듬한 입사 재측정은 남은 과제), **바이스태틱 σ**(여기 값은 모노스태틱 등가이고 전방산란·"
    "상반성 한계는 §5 에 명시), **모서리·정점 회절**(E_edge·E_vertex 두 항을 비운다 — §6; 선행의 "
    "UTD 처방도 유효 하한 E>1.5λ 가 few-λ 드론에서 불성립), **유전체 셸의 2차 효과**(셸 투과는 넣었지만 "
    "굴절 굴곡·내부 위상지연을 무시하는 1차 근사다).",
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
      f"(측정 JSON: {os.path.relpath(JS, ROOT)} + {os.path.relpath(JS6, ROOT)} + "
      f"{os.path.relpath(JSM, ROOT)})")
