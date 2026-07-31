# -*- coding: utf-8 -*-
"""make_notebook03.py — report03.ipynb 생성기.

**주제: 표적 검증 — 우리 드론 모형을 실물·커뮤니티 3D 모델과 대조한다.**
한 편 = 한 주제. 여기서는 오직 "우리가 만든 드론을 얼마나 믿어도 되나"만 다룬다.

숫자는 손으로 적지 않는다:
  · outputs/real_cad_compare.json     ← benchmark/compare_real_cad.py 가 남김 (Typhoon H480 실물 CAD, Holybro 1345 프롭)
  · outputs/community_compare.json    ← benchmark/compare_community.py 가 남김 (커뮤니티 M100·M600 메쉬)
  · docs/GAZEBO_PX4_MODELS.md         ← Gazebo/PX4 내보내기 조사

노트북은 **생성물**이다. report03.ipynb 를 직접 고치지 말고 이 파일을 고쳐 다시 돌릴 것.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
NB = os.path.join(ROOT, "report03.ipynb")

from provenance import provenance_cells   # noqa: E402
from drones import DRONES                 # noqa: E402  ← 표적 개수의 유일한 출처(len(DRONES))


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


with open(os.path.join(ROOT, "outputs", "real_cad_compare.json")) as f:
    REAL = json.load(f)
with open(os.path.join(ROOT, "outputs", "community_compare.json")) as f:
    COMM = json.load(f)

TY = REAL["typhoon"]      # 실물 CAD (Yuneec Typhoon H480, Apache-2.0)
PROP = REAL["prop"]       # 실물 프롭 CAD (Holybro 1345, BSD-3)
M100 = COMM["m100"]       # 커뮤니티 메쉬 (DJI Matrice 100, 2015 쿼드)
M600 = COMM["m600"]       # 커뮤니티 메쉬 (DJI Matrice 600 Pro, 2016 헥사)
with open(os.path.join(ROOT, "outputs", "phantom4_scan_compare.json")) as f:
    PH4 = json.load(f)    # 실물 0.4mm 3D 스캔 (DJI Phantom 4, Thingiverse thing:1456295, CC-BY NeverDun)

FC_GHZ = TY["fc"] / 1e9
EL = TY["el"]

# 대조 기체 **네 대**의 평균 밝기 차 · 방향별 RMS — 전부 JSON 에서 읽는다(손으로 적지 않는다)
D4 = [("Typhoon H480", TY), ("DJI Phantom 4", PH4),
      ("Matrice 100", M100), ("Matrice 600 Pro", M600)]
_worst_raw = max(abs(d["d_sigma_db"]) for _, d in D4)               # 최대 |Δ평균 σ|
# 본문은 "모두 ±X dB 안" 이라고 쓰므로 **올림**해야 참이 된다(1.7931 을 1.79 로 내리면 자기 JSON 이 반증).
worst_mean = math.ceil(_worst_raw * 100.0) / 100.0
comm_worst = max(abs(M100["d_sigma_db"]), abs(M600["d_sigma_db"]))  # 커뮤니티 두 대 중 최악
rms_vals = [d["d_sigma_rms_db"] for _, d in D4] + [PROP["d_sigma_rms_db"]]
rms_lo, rms_hi = min(rms_vals), max(rms_vals)
# 투영면적: 커뮤니티 메쉬 두 대에서 우리가 얼마나 작은가(크기만, 양수 dB)
comm_area_lo = min(abs(M100["d_area_db"]), abs(M600["d_area_db"]))
comm_area_hi = max(abs(M100["d_area_db"]), abs(M600["d_area_db"]))
# Typhoon 투영면적 차이의 **방위별** 산포 (JSON 배열에서 직접 — 하드코딩 금지)
_ty_da = [10.0 * math.log10(o / r) for o, r in zip(TY["area_ours"], TY["area_real"])]
ty_area_lo, ty_area_hi = min(_ty_da), max(_ty_da)
# 방위 미정합의 물증: 프롭 대조에서 bbox 긴 축이 서로 다른 축에 있다
_AX = "XYZ"
prop_long_real = _AX[max(range(3), key=lambda i: PROP["bbox_real_mm"][i])]
prop_long_ours = _AX[max(range(3), key=lambda i: PROP["bbox_ours_mm"][i])]

FIG = "outputs/figures/report03_confidence.png"

cells = []

# ─────────────────────────────────────────────────────────────────────────────
#  §0 앞머리 (provenance)
# ─────────────────────────────────────────────────────────────────────────────
cells += provenance_cells(
    report="report03",
    what="방법 검증 — 공개 3D 모델이 있는 드론을 우리 방식으로 다시 만들어 원본과 대조한다",
    question="우리가 만든 드론 모형을 얼마나 믿어도 되나?",
    spine=dict(
        core=(f"우리 타깃 DJI 드론은 **공개 CAD 가 없다**(제조사 미공개). 그래서 **방법 자체**를 검증한다 — "
              f"공개 3D 모델을 구할 수 있는 **다른 실물 드론**(제조사 CAD·커뮤니티 메쉬·실물 0.4 mm 스캔)을 "
              f"**우리와 똑같은 파라메트릭 방식으로 다시 만들어** 같은 조건에서 나란히 잰다. 평균 밝기(σ)가 네 기체 모두 "
              f"**±{worst_mean:.2f} dB 안**에 들고(가장 큰 이탈은 Phantom 4 실측 스캔의 σ {PH4['d_sigma_db']:+.2f} dB — "
              f"같은 스캔의 투영면적은 {PH4['d_area_db']:+.2f} dB), 방향별 뾰족값({rms_lo:.1f}~{rms_hi:.1f} dB)은 인용하지 않는다. "
              f"단 네 대 중 Typhoon 만은 외곽을 실물 CAD 바운딩박스에 맞춘 뒤 형상을 비교한 것이라 "
              f"**'제원만으로 독립 재현'에 들지 않는다**(§3). 같은 방식이면 타깃 드론 메쉬도 그만큼 믿을 수 있다."),
        gap=(f"Sionna RT 는 표적 메쉬를 받아 전파를 계산하지만 **그 메쉬가 실물을 닮았는지는 검증하지 "
             f"않는다.** 파라메트릭 메쉬의 형상 충실도를 보장할 표준 절차가 스톡 파이프라인엔 없다 — "
             f"공식 치수(L×W×H) 준수는 필요조건일 뿐(치수표 숫자 몇 개를 지켰다는 것) 표적 충실도의 "
             f"증명이 아니다."),
        prior=("선행은 표적 충실도를 **파이프라인 밖의 독립 기준**에 앵커한다 — 외부 EM/CAD 로 계산한 "
               "UAV RCS 를 가져오거나(LAMBDA=Sionna+CADFEKO, arXiv:2607.03826; Temporal-GNN=점산란체, "
               "arXiv:2604.08306), 무향실 실측 드론 RCS(NCSU Ezuma·Güvenç · BUPT 3GPP unified RCS)로 "
               "눈금을 맞춘다. '표적은 바깥 기준으로 검증한다'가 표준(§4)."),
        lib=("**trimesh** 로 외부 실물 CAD·커뮤니티 메쉬를 로드해 **미터 단위·바운딩박스 중심 원점**으로 "
             "맞춘 뒤, 우리 메쉬를 **같은 방위각·앙각·주파수**로 훑어 투영면적과 σ 를 나란히 잰다(널리 쓰는 "
             "메쉬 라이브러리를 재사용, 중복 구현 없음). **두 메쉬를 회전시켜 방위를 맞추는 정합 단계는 없다** "
             "(실물 스캔만 자기 주축으로 z-up 을 세우는 축 정렬을 거친다 — §3) "
             "— 그래서 방향별 값은 인용하지 않는다(§3 결과②). 밝기 σ 는 선행과 같은 SBR+PO 로 계산해 비교한다(§5)."),
        verify=(f"제조사 실물 CAD(Yuneec Typhoon H480)·커뮤니티 메쉬(M100·M600)·실물 스캔(Phantom 4) 대조 + 주요 "
                f"치수(대각·프롭경) 대조. 평균 σ 차이 {TY['d_sigma_db']:+.2f}·{PH4['d_sigma_db']:+.2f}·"
                f"{M100['d_sigma_db']:+.2f}·{M600['d_sigma_db']:+.2f} dB(최대 편차 {worst_mean:.2f} dB), "
                f"방향별 RMS {rms_lo:.1f}~{rms_hi:.1f} dB. 절대 눈금은 실측 문헌 RCS 로 report08."),
    ),
    sources=[
        dict(item="Yuneec Typhoon H480 **실물 CAD** (동체)",
             src="ethz-asl/rotors_simulator (Apache-2.0). `benchmark/compare_real_cad.py` 가 우리 파라메트릭과 대조",
             kind="제조사 실물 형상 (오픈 라이선스). **우리가 만들지 않은 외부 모형**"),
        dict(item="Holybro 1345 **프로펠러 실물 CAD**",
             src="PX4/PX4-gazebo-models (BSD-3). 우리 NACA-4 익형 프롭과 대조",
             kind="실물 부품 CAD. 부품 단위 보조 점검"),
        dict(item="DJI Matrice 100·600 Pro **커뮤니티 메쉬**",
             src="github: TareqAlqutami/dji_ros_simulator (DJI Onboard-SDK 시뮬용). `benchmark/compare_community.py` 가 대조",
             kind="커뮤니티 3D 모델 (구형 기체). **방법 점검용**"),
        dict(item="Gazebo/PX4 모델 조사",
             src="`docs/GAZEBO_PX4_MODELS.md` — PX4-gazebo-models · PX4-SITL_gazebo-classic · 커뮤니티 저장소 목록",
             kind="공개 저장소 조사"),
    ],
    engines=["trimesh-cad", "sbr", "matplotlib"],
    libs=["trimesh", "numpy", "matplotlib"],
    reproduce=[
        "# 실물 CAD 대조 (Typhoon H480 + Holybro 1345 프롭) → outputs/real_cad_compare.json",
        "~/.venvs/py312/bin/python benchmark/compare_real_cad.py",
        "",
        "# 커뮤니티 메쉬 대조 (M100 · M600) → outputs/community_compare.json",
        "~/.venvs/py312/bin/python benchmark/compare_community.py",
        "",
        "# Phantom 4 실물 0.4mm 스캔 대조 (스캔 STL 필요 — prep_cad_scan.py 참조) → phantom4_scan_compare.json",
        "~/.venvs/py312/bin/python src/compare_phantom_scan.py",
        "",
        "# 통일 비교 그림 (실물 CAD·실물 스캔 원본 vs 우리 재현 vs 일치도)",
        "~/.venvs/py312/bin/python src/viz_report3_compare_all.py",
        "",
        "# Gazebo/PX4 SDF 내보내기",
        "~/.venvs/py312/bin/python src/gazebo_export.py",
        "",
        "# 노트북 재생성",
        "~/.venvs/py312/bin/python src/make_notebook03.py",
    ],
    artifacts=[
        dict(file="outputs/real_cad_compare.json", what="Typhoon H480·Holybro 프롭 대조의 모든 숫자 (방위별 σ·면적·평균차)"),
        dict(file="outputs/community_compare.json", what="Matrice 100·600 대조의 모든 숫자"),
        dict(file="outputs/phantom4_scan_compare.json", what="Phantom 4 실물 0.4mm 스캔 vs 우리 메쉬 대조 숫자 (σ·면적·방위별)"),
        dict(file="outputs/figures/report03_compare_all.png", what="실물 CAD·실물 스캔 원본 vs 우리 재현 통일 비교 — 형상 일치도(결과)"),
        dict(file="outputs/gazebo/<key>/model.sdf", what="드론 전 기종의 Gazebo/PX4 비행 시뮬 모델 (SDF)"),
    ],
    caveats=[
        "**대조 기체는 대부분 우리 신형 타깃이 아니다.** M100·M600 은 DJI 이지만 2015~2016 **구형**이고, "
        "Phantom 4·Typhoon H480 은 우리 타깃이자 실물 자료가 있는 두 경우다 "
        "(Phantom 4 = 실물 0.4 mm 스캔이지만 프롭·짐벌이 없어 그 부분은 못 본다; "
        "Typhoon H480 = 제조사 실물 CAD. **2026-07-30 부터 표적 레지스트리에 등록**되어 대조 기체이면서 타깃이다). "
        "⚠ 단 **여기서 비교하는 Typhoon 메쉬는 레지스트리 표적 메쉬가 아니다** — 아래 경고대로 외곽을 실물 CAD "
        "바운딩박스에 맞춘 변형이고, 레지스트리 표적은 공표 제원에서 파라메트릭으로 짓는다(`src/drones.py` note). "
        "우리 신형 타깃(Mavic 4 Pro·Matrice 4E·Mini 5 Pro)은 2025 신형이라 공개 실물 3D 모델이 아직 없다. "
        "→ 이 대조가 검증하는 것은 **'우리 방법이 대략 맞나'이지 '이 특정 신형 기체가 정확하다'가 아니다.**",
        f"**방향별(각도별) σ 뾰족값은 인용 금지.** 평균은 ±{worst_mean:.2f} dB 안으로 맞지만 각도별 RMS 는 "
        f"{rms_lo:.1f}~{rms_hi:.1f} dB 어긋난다. 널·글린트의 **위치**는 잔가지 형상에 민감해 재현되지 않고, "
        "게다가 **두 메쉬의 방위를 맞추는 정합 단계가 파이프라인에 없다**(§3 결과②) — 이 RMS 는 형상 차이와 "
        "방위 미정합이 섞인 값이다. 우리는 **평균 밝기와 그 분포**만 인용한다.",
        "**Typhoon 은 '제원만으로 독립 재현'이 아니다.** 네 대 중 Typhoon 재현만 실물 STL 의 바운딩박스를 "
        "외곽 파라미터로 받아 축별로 다시 스케일한다(`benchmark/compare_real_cad.py` `ours_body_only()`) — "
        "그래서 결과 JSON 의 `bbox_ours_mm` 이 `bbox_real_mm` 과 끝자리까지 같다. Typhoon 행은 "
        "**'실물 외곽에 맞춘 뒤 형상만 비교'** 로 읽어야 한다. 나머지 세 대(Phantom 4·M100·M600)는 공개 제원표 "
        "숫자만으로 지었다.",
        f"**투영면적은 체계적으로 작다**(커뮤니티 메쉬 대비 {M100['d_area_db']:+.1f}~{M600['d_area_db']:+.1f} dB). "
        "착륙다리·GPS 마스트 같은 가는 돌출부를 덜 그린 결과다. 알려진 편향이며, 실측이 아니라 모형 간 상대비교다.",
        "**Gazebo/PX4 SDF 는 형상·질량까지다.** 실제로 '날리려면' 관성텐서·추력계수·모터 시상수 등 동역학 파라미터가 더 필요하고, "
        "그 상당수는 어느 제조사도 공개하지 않아 추정이다. 이 리포트의 태스크(디텍션)에는 비행 시뮬이 필수가 아니다.",
    ],
    cost="대조는 CPU 로 방위 각도마다 그림자 투영·표면 적분을 도는 수 초~수 분 규모. "
         "종합 그림은 CPU 초 단위. (표적 밝기 σ 의 본 계산 물리는 → report06.)",
    related=[
        dict(rep="**report02** (드론 제작)", rel="앞 리포트 — 여기서 대조할 그 모형을 스펙시트에서 깎았다. 그 리포트의 '외형 0.00 % 일치'가 왜 증명이 아닌지를 이 리포트가 이어받는다"),
        dict(rep="**report04** (조명 파형)", rel="다음 리포트 — 믿을 만한 표적을 세웠으니, 이제 그 표적을 **무엇으로 비출지**(상시 통신 신호)로 넘어간다"),
        dict(rep="**report06** (RCS·SBR 물리)", rel="여기서 '평균 밝기 눈금이 맞다'고 확인한 그 σ 를 어떻게 계산하는지의 물리를 다룬다"),
    ],
    glossary=[
        ("RCS (σ)", "레이더 되비침 밝기 [m²]. '이 표적이 얼마나 밝게 되쏘는가'. dBsm = 10·log₁₀(σ/1 m²)"),
        ("투영면적", "표적을 한 방향에서 봤을 때의 그림자 넓이. 클수록 대체로 더 밝게 되쏜다"),
        ("CAD", "컴퓨터로 그린 정밀 3D 도면. 여기선 제조사·커뮤니티가 공개한 진짜 3D 모델을 뜻한다"),
        ("메쉬(mesh)", "3D 형상을 삼각형 그물로 표현한 것. 정점 + 면"),
        ("파라메트릭 모형", "치수·곡률 같은 파라미터로 규칙에 따라 깎은 우리 모형(앞 리포트에서 제작)"),
        ("널(null)", "특정 각도에서 되쏨이 서로 상쇄돼 밝기가 뚝 떨어지는 지점"),
        ("글린트(glint)", "특정 각도에서 되쏨이 겹쳐 밝기가 확 튀는 지점(거울에 햇빛 반짝하듯)"),
        ("RMS 차이", "각도별 오차를 제곱평균한 값. 방향별로 얼마나 들쭉날쭉 어긋나는지의 척도"),
        ("PO", "물리광학 — 빛 닿은 표면 조각의 되쏨을 위상 맞춰 적분해 밝기를 낸다"),
        ("SBR", "광선 쏘고 튕기기 — 표적을 광선으로 조준해 어느 면이 보이는지(가림·다중반사 포함)를 찾는 기하 단계. 그 보이는 면 위에서 되쏨을 위상 맞춰 적분해 밝기를 내는 건 PO 가 한다"),
        ("SDF", "Simulation Description Format — Gazebo/PX4 가 읽는 로봇·기체 모델 파일"),
        ("dBsm", "dB relative to 1 m². 밝기 σ 를 로그 눈금으로 적은 것"),
    ],
)

# ─────────────────────────────────────────────────────────────────────────────
#  앞 리포트 연결
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(
    "---",
    "",
    f"**앞 리포트**에서 드론 {len(DRONES)}종의 3D 모형을 세웠고, 그 외형은 제조사 공식 L×W×H 에 맞춰져 있다. "
    "이 모형이 그대로 Sionna RT 의 표적 메쉬로 들어간다. 다만 **치수표 준수는 필요조건일 뿐, 표적 충실도의 증명은 아니다** — "
    "시뮬레이터는 넣은 메쉬가 실물을 닮았는지 검증하지 않기 때문이다. "
    "그래서 이 리포트는 표적을 **시뮬레이터 밖의 독립 기준(외부 실물 CAD·커뮤니티 3D 모델·측정 RCS 문헌)** 과 대봄으로써 검증한다 — "
    "선행 연구가 표적을 검증하는 바로 그 방식이다.",
))

# ─────────────────────────────────────────────────────────────────────────────
#  §1 Sionna 의 공백
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(
    "## §1. Sionna 의 공백 — 넣은 메쉬가 실물을 닮았는지 검증되지 않는다",
    "",
    "전파 시뮬레이터에 넣는 표적 메쉬는 시뮬레이터가 **검증해 주지 않는다.** "
    "외형을 공식 치수(전체 길이·폭·높이)에 맞추는 것은 필요조건이지만, 그것이 보장하는 것은 딱 하나 — "
    "**'치수표의 숫자 몇 개를 지켰다'** 뿐이다.",
    "",
    "치수표에 없는 것 — 동체의 곡률, 짐벌의 모양, 팔의 굵기, 착륙다리의 유무 — 은 치수표만으로 정해지지 않는다. "
    "그런데 레이더 밝기(RCS)는 바로 그 세부에 반응한다. 따라서 **공식 치수를 지킨 파라메트릭 메쉬라도 실물 형상을 닮았다는 보장은 없고**, "
    "그 형상 충실도를 담보할 표준 절차가 스톡 파이프라인엔 없다.",
    "",
    "그래서 표적 충실도는 **파이프라인 밖의 독립 기준**으로 세운다. 이 리포트는 우리와 아무 관계 없는 "
    "**외부 3D 모델(실물 CAD·커뮤니티 메쉬)**과 같은 조건에서 나란히 재 봄으로써 그 빠진 절차를 채운다(선행이 이 기준을 어디서 찾는지는 §4).",
))

# ─────────────────────────────────────────────────────────────────────────────
#  §2 세 외부 기준과 두 잣대
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(
    "## §2. 무엇을·어떻게 대보나 — 네 외부 기준과 두 잣대",
    "",
    "우리와 무관하게 **공개된** 실기체 3D 자료 네 개를 모았다. 넷 다 우리 파이프라인 밖에서, 다른 사람이 다른 목적으로 만든 것이다. "
    "형상 라이브러리 **trimesh** 로 이들을 읽어 미터 단위·바운딩박스 중심으로 맞추고, 그 기체를 우리 방식으로 다시 만든 메쉬를 "
    "**같은 방위각·앙각·주파수**로 훑어 나란히 잰다. (두 메쉬를 회전시켜 방위를 맞추는 정합은 하지 않는다 — 그래서 "
    "**평균만** 인용하고 방향별 값은 인용하지 않는다. §3 결과②.)",
    "",
    "| 잣대 | 기체 | 성격 | 규모 |",
    "|---|---|---|---|",
    f"| **A. 실물 CAD** | {TY['name_real']} | 제조사(Yuneec) 헥사콥터의 **실물 3D 도면**, 오픈 라이선스. "
    f"⚠ 이 한 대만 우리 재현의 **외곽을 이 CAD 바운딩박스에 맞춘다**(§3) | 면 {TY['n_faces_real']:,} |",
    f"| **B. 커뮤니티** | {M100['name_real']} | 커뮤니티가 만든 구형 DJI 쿼드 메쉬 | 대각 {M100['diagonal_mm']} mm |",
    f"| **C. 커뮤니티** | {M600['name_real']} | 커뮤니티가 만든 구형 DJI 헥사 메쉬 | 대각 {M600['diagonal_mm']} mm |",
    "| **D. 실물 스캔** | DJI Phantom 4 | 실물 기체를 **0.4 mm 3D 스캔**(Thingiverse, CC-BY) — 우리 타깃이자 유일하게 원본 스캔이 있는 기체 | 휠베이스 349 mm ≈ 스펙 350 mm |",
    "",
    "**왜 이들인가.** 우리 타깃 대부분(Mavic 4 Pro·Matrice 4E·Mini 5 Pro)은 **2025 신형**이라 **공개된 실물 3D 모델이 아직 없다** "
    "— 제조사 CAD 는 미공개(또는 독점)이고, 나도는 건 AI 로 뽑은 껍데기뿐이라 치수 기준으로 못 쓴다. "
    "그래서 **구할 수 있는 실기체 자료 — 타사 실물 CAD(Typhoon)·구형 DJI 커뮤니티 메쉬(2015·2016)·Phantom 4 실물 스캔 — 로 "
    "방법 자체를 검증**한다. 이 대조가 확인하는 것은 **'스펙시트 → 형상 → 밝기' 파이프라인의 눈금이 맞나**이지, "
    "'이 특정 신형 기체가 정확하다'가 아니다. (같은 파이프라인이면 신형 타깃 메쉬도 그만큼 믿을 수 있다.)",
    "",
    f"*(부품 단위 보조 점검으로 {PROP['name_real']} 실물 프롭도 우리 NACA-4 익형 프롭과 대봤다 — 방향별 RMS {PROP['d_sigma_rms_db']:.1f} dB.)*",
))

cells.append(md(
    "![.](outputs/renders/anim/spin_matrice4e.gif)\n\n"
    "<sub>Matrice 4E 3D 모델 회전 — 실물·커뮤니티 CAD 로 파이프라인을 교차검증한 실측 실험용 드론.</sub>"
))

cells.append(md(
    "**두 잣대로 잰다.** 같은 방향(방위각 0°→360°, 낮은 앙각 "
    f"el={EL:.0f}°, {FC_GHZ:.1f} GHz)에서 두 모형을 각각 조명해 두 값을 잰다:",
    "",
    "1. **겉모양 = 투영면적.** 그 방향에서 본 표적의 **그림자 넓이**. 크면 대체로 더 밝게 되쏜다. "
    "순수 기하 — 형상만 다르면 값이 갈린다.",
    "2. **밝기 = RCS(σ).** 표면 조각들이 위상을 맞춰 되쏘는 양을 다 더한 값. "
    "선행(예: BVH SBR+PO, arXiv:2604.09243)과 **같은 계열의 SBR+PO** 방식 — 광선으로 보이는 면을 찾고(SBR) 그 위에서 물리광학 적분(PO) — 으로 계산한다"
    "(적용범위 차이는 report06 §4). "
    "형상뿐 아니라 표면의 곡률·정렬까지 반영한다. (밝기 계산의 물리 상세는 report06·07, 절대값 앵커는 report08.)",
    "",
    "<sub>**재질은?** 다운로드 CAD 엔 재질이 없으므로 **원본·우리 메쉬 양쪽을 전부 PEC(완전도체)로** 두고 잰다 — "
    "재질 차이를 지우고 **순수 형상**만 본다. 그래서 이 값은 '이 드론의 진짜 σ'가 아니라 **'같은 재질이면 형상이 얼마나 닮았나'**다"
    "(실제 재질 가중 σ 는 report08 실측 앵커). **거리는?** RCS(σ)는 **원거리장·평면파** 기준의 **표적 고유값이라 거리에 안 변한다** — "
    r"거리에 변하는 건 수신 전력($P_r\propto\sigma/R^4$)이지 σ 가 아니다. 여기선 **모노스태틱**(후방산란) σ 를 방위각마다 하나씩 낸다.</sub>",
    "",
    "그리고 두 모형의 차이를 **두 가지 방식으로** 요약한다 — 이 구분이 이 리포트의 핵심이다:",
    "",
    "- **평균 차이 (Δ평균 σ)**: 360° 전체를 평균한 밝기가 얼마나 다른가. → **눈금이 맞는가**를 본다.",
    "- **방향별 RMS 차이**: 각도마다의 밝기가 얼마나 들쭉날쭉 어긋나는가. → **세부 패턴이 맞는가**를 본다.",
    "",
    "다음 §3 에서 보겠지만 **이 둘의 성적표가 완전히 다르다** — 그리고 그 차이가 '무엇을 인용하고 무엇을 인용하지 않을지'를 정한다.",
))

# ─────────────────────────────────────────────────────────────────────────────
#  §3 증거 — 네 외부 기준과 나란히 잰 결과
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(
    "## §3. 증거 — 다운로드한 실기체를 우리 방식으로 다시 만들어 나란히 잰 결과",
    "",
    "다운로드한 실기체 **네 대**를 우리 방식으로 다시 만들어 원본과 같은 조건에서 잰다. 위 둘 — **DJI Phantom 4 실물 "
    "0.4 mm 3D 스캔**(Thingiverse thing:1456295, CC-BY)과 **Yuneec Typhoon H480 실물 제조사 CAD**(프레임) — 은 "
    "실물에서 나온 정밀 자료라 군더더기가 없다. 아래 둘 — 구형 **DJI M100·M600 커뮤니티 메쉬** — 은 프로펠러를 "
    "**회전 원판으로 그린 시각용 껍데기**(다운로드 원본의 실제 상태)라 형상이 거칠지만, 그래도 평균은 맞는지 함께 본다:",
    "",
    "![downloaded drones rebuilt our way](outputs/figures/report03_compare_all.png)",
    "",
    f"각 행: **왼쪽** 다운로드 원본(Phantom 은 스캔 점구름, M100·M600 은 프롭이 회전 원판) · **가운데** 스펙시트로 "
    f"다시 만든 우리 메쉬 · **오른쪽** 형상 일치도. 평균 밝기 σ 는 네 기체 모두 **±{worst_mean:.2f} dB 안**"
    f"(Typhoon {TY['d_sigma_db']:+.2f}·Phantom {PH4['d_sigma_db']:+.2f}·M100 {M100['d_sigma_db']:+.2f}·M600 {M600['d_sigma_db']:+.2f} dB). "
    f"특히 **Phantom 실측 스캔**은 방위평균 투영면적이 **{PH4['d_area_db']:+.2f} dB** 로 사실상 같아(몸통·아치형 착륙다리까지), "
    f"스펙시트 숫자만으로 지은 우리 메쉬가 실물의 실루엣 규모를 그대로 재현함을 보인다. "
    f"*(그림 오른쪽 패널의 초록 띠는 ±1 dB 참조선이다 — Phantom 4 의 Δσ {PH4['d_sigma_db']:+.2f} dB 는 그 밖에 있고, "
    f"우리가 주장하는 범위는 ±{worst_mean:.2f} dB 다. 그림 제목에 구워진 \"matches to ~1 dB\" 도 같은 이유로 "
    f"본문 범위(±{worst_mean:.2f} dB)로 읽어야 한다 — 그림 재생성 때 문구를 맞춘다.)*",
    "",
    f"> **거친 커뮤니티 시각모델도 평균은 맞다.** M100·M600 은 프로펠러를 회전 원판으로 그린 껍데기라 투영면적이 "
    f"{M100['d_area_db']:+.1f}~{M600['d_area_db']:+.1f} dB 갈리지만(그림 오른쪽 Δarea), 평균 σ 는 "
    f"{M100['d_sigma_db']:+.2f}·{M600['d_sigma_db']:+.2f} dB 로 ±{comm_worst:.2f} dB 안이다. "
    f"바로 이 거칢 — 공개 모델은 눈요기용이라 치수·형상을 못 믿는다 — 이 **우리 신형 타깃을 정밀 파라메트릭 메쉬로 직접 짓는 이유**다.",
    "",
    "> ⚠ **네 대 중 세 대는 원본을 보지 않고 제원표만으로 짓는다 — 그런데 Typhoon 한 대는 예외다.** "
    "원본을 보고 깎으면 '닮았다'는 건 순환논리(그냥 베낀 것)라 검증이 안 된다. 그래서 Phantom 4·M100·M600 은 "
    "**공개 제원표 숫자(대각·프롭경·공식 엔벨로프)만으로 독립적으로** 짓는다(`compare_community.py` 의 "
    "`envelope_mm=None`, `drones.py` 의 phantom4 엔벨로프 = DJI 공식 Quick Start Guide 값). "
    "**Typhoon 재현은 그렇지 않다** — `benchmark/compare_real_cad.py` 의 `ours_body_only()` 가 실물 STL 의 "
    "바운딩박스를 읽어 외곽 파라미터로 넣고 축별로 다시 스케일한다. 그래서 결과 JSON 의 외곽이 실물과 끝자리까지 같다"
    f"({TY['bbox_real_mm'][0]:.1f}×{TY['bbox_real_mm'][1]:.1f}×{TY['bbox_real_mm'][2]:.1f} mm). "
    "즉 Typhoon 행은 **'제원만으로 독립 재현'이 아니라 '실물 외곽에 맞춘 뒤 그 안의 형상을 비교'** 로 읽어야 한다"
    "(제원만으로 짓는 경로 `ours_typhoon()` 은 코드에 있으나 이 비교에서는 호출되지 않는다).",
    "",
    "> ⚠ **세부 형상은 당연히 다르다** — 우리는 매끈한 파라메트릭 동체라 시각적으로 더 통통해 "
    "보이고, 원본은 실물의 얇은 프레임·잔디테일을 담는다. **그런데도 평균 σ 가 맞는 건, RCS 평균이 세부 곡률이 "
    "아니라 전체 크기(투영면적 규모)가 지배하고 우리가 제원으로 맞추는 게 바로 그 전체 치수이기 때문이다.** "
    f"'통통함'은 정직하게 드러나 있다 — 그 세부 차이가 **각도별 RMS({rms_lo:.1f}~{rms_hi:.1f} dB, 인용 안 함)** 와 "
    f"**Δ투영면적(커뮤니티 메쉬 대비 {M100['d_area_db']:+.1f}~{M600['d_area_db']:+.1f} dB — 회전원판 프롭·안테나 돌기까지 "
    "그린 원본이 오히려 실루엣이 넓다)** 로 나타난다.",
    "",
    "> ⚠ **핵심은 '세부 형상이 똑같다'가 아니다.** 우리가 확인하는 것은 하나 — **같은 로터 수·크기의 기체를 우리 "
    f"파이프라인으로 지으면 되쏘는 평균 밝기(RCS)가 원본과 ±{worst_mean:.2f} dB 안으로 맞느냐**이다(각 행 오른쪽 Δσ). "
    "양쪽 모두 PEC 로 통일해 형상만 본다(재질은 report08 실측 앵커). 세부가 다르므로 **각도별** RCS 는 어긋나고"
    f"({rms_lo:.1f}~{rms_hi:.1f} dB, 결과②) **평균만** 인용한다. 우리 타깃 DJI 신형은 공개 CAD 가 없어 이렇게 "
    "**방법을 대리 검증**한다.",
    "",
    f"### 결과 ① 평균 밝기는 네 기체 모두 ±{worst_mean:.2f} dB 안으로 맞는다",
    "",
    "| drone | source | reference mean σ | our mesh mean σ | Δ (ours − ref) |",
    "|---|---|---|---|---|",
    f"| Yuneec Typhoon H480 | real CAD (frame) | {TY['sigma_mean_real_dbsm']:.2f} dBsm | {TY['sigma_mean_ours_dbsm']:.2f} dBsm | **{TY['d_sigma_db']:+.2f} dB** |",
    f"| **DJI Phantom 4** | **real 0.4 mm scan** | {PH4['sigma_mean_real_dbsm']:.2f} dBsm | {PH4['sigma_mean_ours_dbsm']:.2f} dBsm | **{PH4['d_sigma_db']:+.2f} dB** |",
    f"| DJI Matrice 100 | community mesh | {M100['sigma_mean_real_dbsm']:.2f} dBsm | {M100['sigma_mean_ours_dbsm']:.2f} dBsm | **{M100['d_sigma_db']:+.2f} dB** |",
    f"| DJI Matrice 600 Pro | community mesh | {M600['sigma_mean_real_dbsm']:.2f} dBsm | {M600['sigma_mean_ours_dbsm']:.2f} dBsm | **{M600['d_sigma_db']:+.2f} dB** |",
    "",
    f"⚠ Typhoon 행은 우리 재현의 **외곽이 그 실물 CAD 바운딩박스에 맞춰져 있다**(위 경고). 나머지 세 행"
    f"(Phantom 4·M100·M600)만 제원표만으로 지은 독립 재현이다.",
    "",
    f"네 기체의 평균 밝기 차이가 모두 **±{worst_mean:.2f} dB 안**({TY['d_sigma_db']:+.2f} · {M100['d_sigma_db']:+.2f} · "
    f"{M600['d_sigma_db']:+.2f} · {PH4['d_sigma_db']:+.2f} dB)이다. "
    "제조사 실물 CAD·커뮤니티 메쉬·실물 스캔, 쿼드와 헥사, 다른 크기·다른 회사 — 그런데도 평균은 일관되게 붙는다.",
    "",
    "네 잣대는 서로 무관하게, 서로 다른 사람이, 서로 다른 기체를 모델링한 것이다(실물 스캔 포함). "
    "만약 SBR+PO 방식에 체계적 눈금 오류가 있었다면 네 대조에서 **같은 방향으로 크게** 어긋났을 것이다. "
    f"그런데 부호가 갈리고({TY['d_sigma_db']:+.2f}·{M100['d_sigma_db']:+.2f}·{M600['d_sigma_db']:+.2f} vs "
    f"{PH4['d_sigma_db']:+.2f} dB) 크기도 모두 {worst_mean:.2f} dB 안이라는 것은, "
    "**'스펙시트 → 형상 → SBR+PO 밝기' 파이프라인이 평균적으로 올바른 양의 에너지를 되쏜다**는 뜻이다. "
    "(다만 이 결론의 독립 표본은 넷이 아니라 **셋**이다 — Typhoon 은 외곽이 실물에서 왔다.)",
    "",
    "이 대조는 **모형끼리의 상대비교**로 방식의 눈금을 본다. 이 평균 σ 의 **절대값**이 무향실에서 실제로 잰 동종 멀티로터 드론 RCS 문헌"
    "(NCSU Ezuma·Güvenç, BUPT 3GPP unified RCS) 범위 안에 드는지 — 즉 절대 눈금까지 맞는지 — 는 **report08 에서 실측 RCS 앵커**로 확인한다. "
    "→ 그래서 우리는 표적의 **평균 밝기 σ 를 인용한다.**",
))

cells.append(md(
    f"### 결과 ② 방향별 뾰족값은 {rms_lo:.1f}~{rms_hi:.1f} dB 어긋난다 (그래서 인용하지 않는다)",
    "",
    "평균은 붙었지만, **특정 각도에서의** 밝기는 얘기가 다르다:",
    "",
    "| drone | per-azimuth RMS Δ |",
    "|---|---|",
    f"| Yuneec Typhoon H480 | **{TY['d_sigma_rms_db']:.1f} dB** |",
    f"| DJI Phantom 4 (scan) | **{PH4['d_sigma_rms_db']:.1f} dB** |",
    f"| DJI Matrice 100 | **{M100['d_sigma_rms_db']:.1f} dB** |",
    f"| DJI Matrice 600 Pro | **{M600['d_sigma_rms_db']:.1f} dB** |",
    "",
    f"각도별로 보면 **{rms_lo:.1f}~{rms_hi:.1f} dB** 나 들쭉날쭉 어긋난다(위 통일 그림 각 행 아래의 per-az RMS). "
    "**평균 레벨은 맞지만, 뾰족한 급락(널)·급등(글린트)이 어느 각도에 오는지는 서로 안 맞는다.**",
    "",
    "이 뾰족한 봉우리와 골짜기는 **간섭** 때문이다. 표면의 여러 조각이 되쏜 파동이 어떤 각도에선 마루끼리 겹쳐 확 밝아지고(글린트), "
    "어떤 각도에선 마루와 골이 만나 서로 지워진다(널). 이건 **잔잔한 호수에 돌 여러 개를 던졌을 때** 생기는 물결 무늬와 같아서 — "
    "돌의 위치를 몇 cm만 옮겨도 무늬가 만나는 지점(밝고 어두운 자리)이 확 바뀐다.",
    "",
    "두 모형은 **잔가지 형상이 다르다**(곡률·이음매·돌기). 그 미세한 차이가 '돌의 위치'를 조금 옮기고, "
    "그 결과 널·글린트가 **어느 각도에 오는지**가 통째로 달라진다. **전체 물결 에너지(=평균 밝기)는 보존되지만, 무늬의 위치는 재현되지 않는다.**",
    "",
    "> ⚠ **원인이 하나 더 있다 — 방위 정합을 하지 않았다.** 비교 루틴은 두 메쉬를 각자의 바운딩박스 중심에 놓고 "
    "**같은 방위각 목록**을 그대로 훑을 뿐, 두 메쉬를 회전시켜 코 방향을 맞추는 단계가 없다"
    "(`src/mesh_compare.py` 의 `compare()`). 물증은 프롭 대조에 있다 — 실물 Holybro 1345 의 바운딩박스는 "
    f"{PROP['bbox_real_mm'][0]:.0f}×{PROP['bbox_real_mm'][1]:.0f}×{PROP['bbox_real_mm'][2]:.0f} mm 로 긴 축이 "
    f"**{prop_long_real}**, 우리 프롭은 {PROP['bbox_ours_mm'][0]:.0f}×{PROP['bbox_ours_mm'][1]:.0f}×"
    f"{PROP['bbox_ours_mm'][2]:.0f} mm 로 긴 축이 **{prop_long_ours}** 다(≈90° 어긋남). "
    f"따라서 표의 per-az RMS {rms_lo:.1f}~{rms_hi:.1f} dB 는 **형상 차이와 방위 미정합이 섞인 값**이며 "
    "형상 충실도의 상한으로 읽어서는 안 된다. 이 리포트가 방향별 값을 인용하지 않는 두 번째 이유다.",
    "",
    "> <sub>예외 하나를 정확히 적는다 — **Phantom 4 실물 스캔만** 비교 전에 좌표축을 한 번 세운다"
    "(`src/compare_phantom_scan.py:26-32`: 정점 공분산의 고유벡터로 큰 축→x·y, 작은 축→z). 이는 "
    "**스캔을 z-up 으로 세우는 축 정렬**이지 우리 메쉬와 코 방향을 맞추는 방위 정합이 아니며, 부호와 "
    "90° 모호성은 그대로 남는다(다리 방향 뒤집기 판정 `:33-36` 은 분기 본문이 `pass` 라 아무 일도 하지 "
    "않는다). 그 밖의 세 대조에는 회전 단계 자체가 없다.</sub>",
    "",
    "그래서 우리는 '이 각도에서 σ 는 몇 dBsm' 같은 방향별 뾰족값을 **인용하지 않는다.** "
    "인용하는 것은 **평균 밝기와 그 분포(널이 얼마나 깊고 얼마나 자주 오는지의 통계)** 까지다. "
    "이건 특정 모형만의 약점이 아니라 **어떤 근사 형상이든 갖는 성질**이다 — 실물과 나사 하나까지 같지 않으면 뾰족값의 위치는 옮겨간다. "
    "선행의 측정 드론 RCS 연구가 σ 를 각도별 값이 아니라 **통계 분포(예: GEV·Swerling 요동 모델)** 로 다루는 것도 같은 이유다.",
))

cells.append(md(
    "### 결과 ③ 모형은 가는 돌출부를 덜 그려 살짝 홀쭉하다",
    "",
    "| drone | Δ projected area (ours − ref) | direction |",
    "|---|---|---|",
    f"| **DJI Phantom 4** (real scan) | **{PH4['d_area_db']:+.2f} dB** | near-perfect |",
    f"| Yuneec Typhoon H480 (real CAD) | {TY['d_area_db']:+.2f} dB | ours slightly larger |",
    f"| DJI Matrice 100 (community) | **{M100['d_area_db']:+.2f} dB** | ours smaller |",
    f"| DJI Matrice 600 Pro (community) | **{M600['d_area_db']:+.2f} dB** | ours smaller |",
    "",
    f"커뮤니티 실측 메쉬 두 개에서 우리 모형의 그림자 넓이가 **{comm_area_lo:.1f}~{comm_area_hi:.1f} dB 작다.** "
    "원인은 분명하다 — **착륙다리·GPS 안테나 마스트·튀어나온 센서** 같은 **가는 돌출부가 덜 그려져 있다.** "
    "Matrice 100 커뮤니티 메쉬는 위로 솟은 GPS 마스트와 아래로 뻗은 착륙다리를 세밀히 담고 있지만, 파라메트릭 실루엣은 그런 잔가지를 단순화한다.",
    "",
    f"(Typhoon 실물 CAD 에서는 반대로 우리가 {TY['d_area_db']:+.2f} dB **크게** 나왔다 — 실물 CAD 는 접이식 팔·틈이 있어 "
    "그림자에 빈 곳이 많은데, 매끈한 동체가 그 실루엣을 더 꽉 채우기 때문이다. 여기서 **외곽 바운딩박스는 실물과 같게 "
    "맞춰져 있으므로**(결과① 아래 경고) 이 차이는 순수한 **실루엣 채움 정도**다. 방위별로도 "
    f"{ty_area_lo:+.2f}~{ty_area_hi:+.2f} dB 로 부호가 뒤집히지 않는다.)",
    "",
    "이건 '어느 쪽이 더 정직한 밝기냐'의 판정이 아니라, 모형의 **알려진 편향**으로 기록해 두는 것이다 — "
    "가는 돌출부를 덜 그린다 → 투영면적이 조금 작다 → 그 방향의 밝기도 그만큼 달라질 수 있다"
    f"(기체에 따라 작게도·크게도 — Typhoon 은 {TY['d_area_db']:+.2f} dB 로 오히려 크다). "
    "실측 안테나 측정이 아니라 **모형끼리의 상대비교**라는 점도 함께 기억해 둔다.",
))

cells.append(md(
    "### 요약 — 무엇을 인용하고, 무엇을 인용하지 않나",
    "",
    "| what | agreement | citable? |",
    "|---|---|---|",
    f"| mean σ (azimuth-averaged) | within {worst_mean:.2f} dB (4 aircraft) | ✅ **cite** |",
    "| σ distribution (null depth / frequency) | mostly agrees | ✅ cite as statistics |",
    f"| **per-angle σ peak** (this angle = ? dBsm) | {rms_lo:.1f}–{rms_hi:.1f} dB off (+ no azimuth registration) | ❌ **do NOT cite** |",
    f"| projected area (silhouette) | community meshes {M100['d_area_db']:+.1f}…{M600['d_area_db']:+.1f} dB (ours smaller) | ⚠️ known bias only |",
    "",
    "평균 밝기 σ 는 인용하고(절대 눈금은 report08 실측 앵커), 방향별 뾰족값은 인용하지 않는다. "
    "Typhoon 행은 외곽을 실물에 맞춘 비교이므로 '제원만으로 독립 재현' 근거로는 쓰지 않는다.",
))

# ─────────────────────────────────────────────────────────────────────────────
#  §4 선행 연구 방식
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(
    "## §4. 선행 연구는 표적 충실도를 어떻게 세우나",
    "",
    "이 한계(시뮬레이터가 표적 메쉬를 검증하지 않는다)를 다루는 방식은 우리만의 것이 아니다. "
    "Sionna·RF 디지털트윈을 센싱에 쓰는 선행은 표적 충실도를 **파이프라인 밖의 독립 기준**에 앵커한다:",
    "",
    "- **외부 EM/CAD 로 계산한 UAV RCS 를 가져와** 채널에 주입한다 — LAMBDA(Sionna+CADFEKO UAV RCS, arXiv:2607.03826), "
    "Temporal-GNN(점산란체 RCS 주입, arXiv:2604.08306). 표적 산란만 외부 물리로 구해 두 전파 구간 사이에 끼워 넣는 구조($h=h_{bg}+h_{target}$)다.",
    "- **무향실에서 실제로 잰 드론 RCS 문헌으로 눈금을 맞춘다** — NCSU Ezuma·Güvenç, BUPT 3GPP unified RCS 등. "
    "이들은 σ 를 각도별 값이 아니라 **통계 분포**로 제공한다(결과 ②에서 본 이유와 같다).",
    "",
    "요컨대 **'표적은 모델 파이프라인과 무관한 바깥 기준으로 검증한다'가 이 분야의 표준 관행**이다. "
    "이 리포트는 바로 그 표준을 따라, 우리와 아무 관계 없는 외부 실물 CAD·커뮤니티 메쉬·실물 스캔과 나란히 잰다.",
))

# ─────────────────────────────────────────────────────────────────────────────
#  §5 우리가 쓴 방식 + 검증
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(
    "## §5. 우리가 쓴 방식 — trimesh 로 나란히 재기 + SBR+PO, 그리고 검증",
    "",
    "**형상 대조는 표준 메쉬 라이브러리 `trimesh` 로 한다** — 외부 실물 CAD·커뮤니티 메쉬를 로드해 "
    "**미터 단위·바운딩박스 중심 원점**으로 맞춘 뒤, 원본과 우리 메쉬에 **같은 방위각 목록**을 돌리며 "
    "투영면적(그림자 넓이)을 잰다. 새 기하 커널을 짜지 않고 널리 쓰이는 라이브러리를 그대로 재사용하므로 "
    "중복 구현이 없다. **두 메쉬를 회전시켜 방위를 맞추는 정합 단계는 넣지 않았다** — 그래서 이 절차가 "
    "보증하는 것은 **방위평균 값**이고, 방향별 값은 인용하지 않는다(§3 결과②).",
    "",
    "**밝기(σ)는 선행이 쓰는 것과 같은 SBR+PO 로 계산해 비교한다** — 광선으로 보이는 면을 찾고(SBR) 그 위에서 물리광학 적분(PO). "
    "선행의 RCS 처리 세 갈래(① 상용 full-wave CADFEKO=LAMBDA · ② 자작 SBR+PO=BVH SBR+PO arXiv:2604.09243 · ③ 점산란체/UTD 근사) 중 "
    "**②**를 따른 것으로, 상용툴 없이 재현 가능하다.",
    "",
    "**검증 요약 — 무엇을 어디까지 확인했나:**",
    "",
    "| 확인 | 방법 | 결과 |",
    "|---|---|---|",
    "| 형상 충실도 | 실물 CAD·커뮤니티 메쉬·**Phantom 4 실물 스캔**과 나란히 렌더·계측 | 실루엣 규모 일치(방위 정합 없음) |",
    f"| 평균 밝기 눈금 | 네 기체 평균 σ 차이 | **{TY['d_sigma_db']:+.2f}·{M100['d_sigma_db']:+.2f}·{M600['d_sigma_db']:+.2f}·{PH4['d_sigma_db']:+.2f} dB** (최대 편차 {worst_mean:.2f} dB) |",
    f"| 실물 스캔 직접 대조 | Phantom 4 0.4mm 스캔 vs 우리 메쉬 | 투영면적 **{PH4['d_area_db']:+.2f} dB**·σ **{PH4['d_sigma_db']:+.2f} dB** |",
    f"| 방향별 패턴 | 방향별 RMS 차이 | **{rms_lo:.1f}~{rms_hi:.1f} dB** → 평균만 인용 |",
    f"| 투영면적 편향 | 커뮤니티 메쉬 대비 | **{M100['d_area_db']:+.1f}~{M600['d_area_db']:+.1f} dB** (우리가 작다) |",
    f"| 독립 재현 범위 | 제원표만으로 지은 기체 | **3/4** (Phantom 4·M100·M600). Typhoon 은 외곽을 실물 CAD 에 맞춤 |",
    "",
    "이 리포트의 검증은 **모형끼리의 상대비교**로 방법의 눈금을 세운다. σ 의 **절대 눈금**(무향실 실측 문헌 RCS 앵커)은 **report08**, "
    "밝기 계산의 물리 상세는 **report06·07** 소관이다.",
))

# ─────────────────────────────────────────────────────────────────────────────
#  §6 보너스 — Gazebo / PX4 내보내기
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(
    "## §6. 보너스 — 드론을 비행 시뮬(Gazebo/PX4)로 내보내기",
    "",
    "표적 모형은 앞 리포트에서 **몸통과 프로펠러를 따로 움직이는 관절 구조**로 세워졌다. "
    "그 구조는 비행 시뮬레이터 Gazebo 가 원하는 '동체 링크 하나 + 로터마다 회전 관절 하나'와 **같은 형태**라, "
    f"드론 {len(DRONES)}종을 그대로 표준 모델 파일 **SDF**(Gazebo/PX4 가 읽는 형식)로 내보낼 수 있다 (→ `outputs/gazebo/<key>/model.sdf`).",
    "",
    "조사 결과(`docs/GAZEBO_PX4_MODELS.md`):",
    "- 공식 PX4/Gazebo 에 **완제품 DJI 드론은 없다.** DJI 는 PX4 가 아니라 자체 비행스택을 쓰기 때문이다.",
    "- 커뮤니티 DJI 모델은 있지만 전부 **구형**(Matrice 100·600·Phantom 4·Tello)이고, PX4 가 아니라 DJI 자체 SDK 시뮬용이다.",
    "- **Mavic 4 Pro·Matrice 4E(2025 신형)는 어디에도 없다** — 너무 새로워서.",
    "",
    "→ 즉 이 내보내기는 **세상에 준비된 적 없는 신형 기체의 비행 모델** 빈틈을 채운다. "
    "각 부위 밀도로 관성텐서를, 호버 조건에서 추력계수를, 볼록껍질로 충돌메쉬를 붙여 SDF 를 채운다.",
    "",
    "다만 디텍션에는 이게 필수가 아니다. 레이더가 보는 것(표적의 밝기·마이크로도플러)은 이미 Sionna RT + SBR 이 담당한다. "
    "Gazebo/PX4 가 더해 줄 수 있는 건 **현실적인 비행 궤적**뿐인데, 디텍션 실험에는 직선/저속 궤적이면 충분하다. "
    "실제로 '날리려면' SDF 형상 위에 관성·추력계수·모터 시상수 같은 **동역학 파라미터**가 더 필요하고, "
    "그 상당수는 어느 제조사도 공개하지 않아 추정에 기댄다. 그래서 비행 시뮬은 **열어 둔 선택지**로 남겨 둔다.",
))

# ─────────────────────────────────────────────────────────────────────────────
#  정리 & 다음
# ─────────────────────────────────────────────────────────────────────────────
cells.append(md(
    "## 정리 & 다음",
    "",
    "### 답한 질문: *검출 실험에 넣을 이 드론 모형을 얼마나 믿어도 되나?*",
    "",
    "표적 충실도를 시뮬레이터 밖의 독립 기준으로 세웠다 — 공개된 실기체 자료 **네 개**"
    "(실물 CAD Typhoon H480 + 커뮤니티 M100·M600 + **Phantom 4 실물 0.4mm 스캔**)를 각각 우리 방식으로 다시 만들어 "
    "trimesh 로 같은 조건에서 나란히 재고, 밝기는 선행이 쓰는 SBR+PO 로 비교했다. 프로펠러는 Holybro 1345 실물 CAD 로 보조 점검했다.",
    "",
    "| 주장 | 근거 | 값 |",
    "|---|---|---|",
    f"| 평균 밝기 눈금이 맞다 | 네 기체 평균 σ 차이 | **{TY['d_sigma_db']:+.2f} · {M100['d_sigma_db']:+.2f} · {M600['d_sigma_db']:+.2f} · {PH4['d_sigma_db']:+.2f} dB** (모두 ±{worst_mean:.2f} dB 안) |",
    f"| 방향별 뾰족값은 못 믿는다 | 방향별 RMS 차이 | **{rms_lo:.1f}~{rms_hi:.1f} dB** (+ 방위 정합 없음) → 평균만 인용 |",
    f"| 우리 모형이 살짝 홀쭉하다 | 투영면적 차이 | 커뮤니티 대비 **{M100['d_area_db']:+.1f}~{M600['d_area_db']:+.1f} dB** |",
    "| 제원만으로 독립 재현된 기체 | 외곽 파라미터의 출처 | **3/4** — Typhoon 은 외곽을 실물 CAD 에 맞춤 |",
    "",
    "**믿으면 안 되는 것** (앞머리 8️⃣ 참조): 방향별 σ 뾰족값(널·글린트 위치 — 방위 정합도 하지 않았다) · "
    "Typhoon 행을 '제원만으로 독립 재현' 근거로 쓰기 · 대조 기체가 신형 타깃과 같다는 착각(대부분 구형/타사) · "
    "투영면적을 실측 밝기로 오해하기.",
    "",
    "**핵심 한 줄**: 우리 모형은 **평균 밝기의 눈금은 믿어도 되고, 방향별 뾰족값과 가는 돌출부는 믿으면 안 된다.** "
    "그리고 이 대조는 신형 한 대의 완벽함이 아니라 **방법의 타당성**을 재는 것이다.",
    "",
    "| 다음 리포트 | 무엇을 이어받나 |",
    "|---|---|",
    "| **report04** — 조명 파형 | 믿을 만한 표적을 세웠으니, 이제 그 표적을 **무엇으로 비출지**(상시 통신 신호)로 넘어간다. |",
    "| **report06** — RCS·SBR 물리 | 여기서 '평균 눈금이 맞다'고 확인한 그 σ 를 **어떻게 계산하는지**의 물리를 다룬다. |",
))


def main():
    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3.12 (py312)",
                                      "language": "python", "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    with open(NB, "w") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"notebook 생성: {os.path.relpath(NB, ROOT)}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
