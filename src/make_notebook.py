# -*- coding: utf-8 -*-
"""make_notebook.py — report1.ipynb(한글 단계별 설명서) 생성기.
outputs/ 의 그림을 markdown 상대경로로 링크해, 커널을 안 돌려도 VSCode 미리보기에서 바로 보인다.
실행하면 sionna2/report1.ipynb 를 새로 만든다.

2026-07-14 개편 — **matplotlib 3D 도식 → Sionna 렌더러**로 갈아엎었다.
  · 챔버/드론/경로/라디오맵 그림은 전부 src/viz_report1.py 가 Sionna RT 로 렌더한다.
  · 오늘 고친 메쉬 버그(높이 −25~−47 %, 프로펠러 법선)를 본문에 서술한다.
  · 치수 도면(카드·크기비교·시설도면)만 matplotlib 로 남는다 — 공학 도면은 렌더로 대체 불가.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
NB = os.path.abspath(os.path.join(HERE, "..", "report1.ipynb"))


def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": _split(list(lines))}


def code(*lines):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _split(list(lines))}


def _split(lines):
    txt = "\n".join(lines)
    out = txt.splitlines(keepends=True)
    return out if out else [""]


cells = []

cells.append(md(
    "# 📦 report1 — 무대 만들기 (Environment Setup)",
    "",
    "> **이 노트북 = 1단계: 무대.** 뒤따르는 모든 레이더 실험(report2~6)이 서 있는 바닥입니다.",
    "> **차폐시설(30 × 20 × 11 m) + DJI 드론 5종**을 3D로 만들고, 그것을 **Sionna 가 직접 렌더**했습니다.",
    "",
    "**2026-07-14 개편 — 그림이 바뀌었습니다.**",
    "예전 report1 의 3D 그림은 전부 matplotlib 도식이었습니다. 그건 *우리가 그린 그림*이지",
    "*시뮬레이터가 본 것*이 아닙니다. 이제 챔버·드론·경로·라디오맵은 모두",
    "**`sionna.rt.Scene.render_to_file`** 이 그립니다 — report2~6 이 실제로 계산에 쓰는",
    "**바로 그 메쉬·그 재질**을 촬영한 것입니다. 치수 도면(카드·크기비교·시설도면)만",
    "matplotlib 로 남았습니다(공학 도면은 사진으로 대체할 수 없습니다).",
    "",
    "**같은 날 고친 메쉬 버그도 함께 기록합니다** — 드론이 전 기종 **25~47 % 납작**했습니다(§4).",
    "",
    "> 그림은 `outputs/` 의 파일을 **상대경로로 링크**해 두어, 저장소를 받으면 셀을 실행하지 않아도 보입니다.",
    "> 직접 돌려보려면 커널을 **py312 (Python 3.12)** 로 고르세요.",
))

cells.append(md(
    "## 0. 무엇을 만들었나 — 한눈에",
    "",
    "| 대상 | 무엇 | 누가 그렸나 |",
    "|---|---|---|",
    "| 차폐시설 | 30 × 20 × 11 m **semi-anechoic** 챔버 (벽4면+천장 흡수체, **바닥은 반사성 콘크리트**) | **Sionna 렌더** |",
    "| 드론 5종 | Mini 5 Pro / Mavic 4 Pro / Matrice 4E / S1000+ / Phantom 4 — **공식 외형에 정합** | **Sionna 렌더** |",
    "| 전파 경로 | TX→RX 광선 (직접파 · 바닥반사 · 흡수체 반사) | **Sionna PathSolver** |",
    "| 전력 분포 | 바닥면 / 드론면 라디오맵 | **Sionna RadioMapSolver** |",
    "| 치수 도면 | 드론 카드 · 크기비교 · 시설 도면 | matplotlib (도면은 렌더 불가) |",
    "| 메쉬 검증 | trimesh 부품단위 (watertight / 법선 / winding) | matplotlib 표 |",
    "",
    "```",
    "sionna2/",
    "├─ src/",
    "│  ├─ geom.py            # 삼각형으로 3D 도형을 쌓는 미니 도구",
    "│  ├─ chamber.py         # 차폐시설 모델 (바닥·흡수체·골조·문)",
    "│  ├─ drones.py          # 드론 5종 제원 + 파라메트릭 생성기 + **공식 외형 정합**",
    "│  ├─ materials.py       # 재질 단일 진리원 (Sionna 전파 = PO/SBR 이 같은 표를 읽음)",
    "│  ├─ mesh_check.py      # trimesh 메쉬 검증 (회귀 방지)",
    "│  ├─ render_rt.py       # Sionna 렌더러 래퍼 (make_scene / cam / shot)",
    "│  ├─ viz_report1.py     # ★ report1 그림 — Sionna 렌더 + 몽타주",
    "│  ├─ viz_diagram.py     # 치수 도면 (카드·크기비교·시설도면)",
    "│  └─ build_all.py       # 한 번에 전부 생성",
    "├─ assets/meshes/        # 부위별 OBJ",
    "├─ outputs/figures/      # report1_*.png (이 노트북이 링크하는 그림)",
    "└─ outputs/renders/      # Sionna 원본 렌더 (r1_*.png)",
    "```",
    "",
    "**한 번에 다시 만들기**:",
    "```bash",
    "PY=/home/yunjung/.venvs/py312/bin/python",
    "cd sionna2 && $PY src/build_all.py          # GPU 는 src/gpu.py 가 가장 한가한 것을 자동 선택",
    "```",
))

cells.append(md(
    "## 1. 무대 — Sionna 가 본 챔버",
    "",
    "![chamber sionna](outputs/figures/report1_chamber_sionna.png)",
    "",
    "**이 방은 anechoic 이 아니라 semi-anechoic 입니다.** 용어를 정확히 씁시다:",
    "흡수체는 **벽 4면 + 천장**에만 있고 **바닥은 콘크리트 타일(반사성)** 입니다.",
    "이건 말장난이 아니라 **뒤의 모든 리포트를 지배하는 사실**입니다 —",
    "방 안에 남은 **유일한 강한 반사면이 바닥**이고, 표적을 경유한 바닥 반사는",
    "표적과 같은 도플러를 실어 오므로 **정지 클러터 제거(ECA)로 지워지지 않습니다**(report4/6).",
    "",
    "### 1-a) 치수 도면 (matplotlib — 도면은 렌더로 대체 불가)",
    "![chamber schematic](outputs/figures/chamber_schematic.png)",
))

cells.append(md(
    "## 2. Sionna 가 실제로 추적한 광선",
    "",
    "여기부터가 예전 report1 에 없던 것입니다. **PathSolver 를 돌려 TX→RX 광선을 찾고,",
    "그 광선을 Sionna 렌더러가 그대로 그립니다.** 그림 속 숫자는 캡션이 아니라 **솔버의 출력**입니다.",
    "",
    "![paths](outputs/figures/report1_paths.png)",
    "",
    "**max_depth = 1 에서 솔버가 준 4개 경로** (TX (4, 2.5, 8) → RX (4, 17.5, 6.5), 3.5 GHz):",
    "",
    "| 부딪힌 면 | 지연 | 직접파 대비 초과지연 | 직접파 대비 이득 |",
    "|---|---|---|---|",
    "| 직접파 (LOS) | 50.3 ns | — | 0.0 dB |",
    "| 천장 흡수체 | 63.3 ns | +13.0 ns | **−9.8 dB** |",
    "| 좌측벽 흡수체 | 65.2 ns | +14.9 ns | −17.2 dB |",
    "| **바닥 (콘크리트 타일)** | 69.6 ns | **+19.3 ns** | **−14.7 dB** |",
    "",
    "**바닥 반사 +19.3 ns / −14.7 dB** — report6 이 측정한 값과 같고, 프레넬 예측과 0.02 dB 로 일치합니다.",
    "**RT 는 환경에서는 믿을 수 있다**는 근거입니다. (RT 가 못 주는 것은 *표적의 σ* 입니다 — report6.)",
    "",
    "> ⚠ **흡수체 행은 조심해서 읽으세요.** 천장 행이 바닥 행보다 큰 것은 *방*의 성질이 아니라 *모델*의 성질입니다.",
    "> 우리 흡수체 재질의 **평평한 단일면 반사는 −5.2 dB** 밖에 안 됩니다(`materials.py` 가 스스로 그렇게 적어 둡니다 —",
    "> 실측치가 아니라 모델값). 실제 −25~−30 dB 무반사는 **피라미드 골짜기에서 4~5회 튕기는 기하 효과**라,",
    "> 얕은 max_depth 로는 재현되지 않습니다. 즉 여기 흡수체 경로는 **상한(비관적)** 입니다.",
    "> 다행히 **뒤의 결론은 이 경로들에 기대지 않습니다** — 정지(0-도플러)라서 ECA 가 지웁니다.",
    "> 바닥은 다릅니다: 평평한 콘크리트 1회 반사이고, **표적을 경유하면 도플러가 실려 ECA 를 통과**합니다.",
))

cells.append(md(
    "## 3. 라디오맵 — 에너지가 어디로 가나",
    "",
    "![radiomap](outputs/figures/report1_radiomap.png)",
    "",
    "`RadioMapSolver` 로 **바닥면(z = 0.05 m)** 과 **드론면(z = 5.5 m)** 의 수신전력 분포를 냈습니다.",
    "벽 메아리에 의한 정상파 무늬가 없습니다(흡수체가 일합니다). 바닥면의 어두운 줄무늬 두 개는",
    "뒷벽에서 튀어나온 **출입문 패널의 기하학적 그림자**입니다.",
    "드론면은 표적이 나는 높이이고, 바닥면은 그 에너지를 **다시 위로 되돌려 보내는 면**입니다.",
))

cells.append(md(
    "## 4. ⚠ 오늘 고친 메쉬 버그 — 드론이 25~47 % 납작했다",
    "",
    "![envelope fit](outputs/figures/report1_envelope_fit.png)",
    "",
    "### 무엇이 틀렸나",
    "프레임 생성기가 동체 두께를 `body_z = 0.35 · H_spec` 이라는 **임의의 비율**로 잡고,",
    "그 결과를 **공식 외형과 한 번도 대조하지 않았습니다**. 결과:",
    "",
    "| 기종 | 옛 메쉬 높이 | 공식 H | 오차 |",
    "|---|---|---|---|",
    "| Mini 5 Pro | 48.1 mm | 91.0 mm | **−47 %** |",
    "| Mavic 4 Pro | 75.8 mm | 135.2 mm | **−44 %** |",
    "| Matrice 4E | 93.7 mm | 149.5 mm | **−37 %** |",
    "| Phantom 4 | 148.2 mm | 198.0 mm | **−25 %** |",
    "| S1000+ | 454.9 mm | 462.0 mm | −2 % |",
    "",
    "### 왜 중요한가",
    "챔버 기하는 **저앙각(el ≈ 15°)** 관측입니다. 저앙각에서는 **높이가 측면 투영면적을 지배**하고,",
    "평판 극한에서 σ ∝ (투영면적)² 이므로 높이 −44 % 는 σ 를 **−5 dB** 로 과소평가합니다.",
    "즉 RCS·검출확률(Pd)까지 그대로 전파되는 버그였습니다. 수정 후 RCS 가 **+2.4 ~ +4.6 dB** 올라갔습니다.",
    "",
    "### 어떻게 고쳤나",
    "실루엣(파라메트릭)은 그대로 두고, **프레임 바운딩박스가 공식 L×W×H 와 같아지도록 축별 배율**을 겁니다",
    "(`drones.frame_fit_scale`). 프로펠러는 제원 지름이 따로 있으므로 **스케일하지 않습니다**.",
    "",
    "### 방법론이 옳다는 **독립 검증**",
    "**Matrice 4E 는 DJI 가 외형과 대각선을 둘 다 공개한 유일 기종**입니다.",
    "메쉬는 **외형(307 × 387.5 × 149.5 mm)만 보고** 맞췄는데, 그 결과 나온 모터-모터 대각선이",
    "**433.1 mm** — 공식 **438.8 mm** 대비 **−1.3 %** 입니다.",
    "**한 번도 보지 않은 숫자를 맞혔습니다.** 정합 방법이 독립적으로 검증된 것입니다.",
    "",
    "### 덤으로 드러난 모순 — Mavic 4 Pro 의 대각선 400 mm 는 **불가능**하다",
    "400 mm 는 DJI 미공개값에 대한 우리 **추정치**였습니다. 그런데 공식 외형 **328.7 × 390.5 mm** 는",
    "**400 mm 모터 대각선으로는 펼쳐질 수 없습니다**(기하학적 모순). 외형에 맞추면 **440.9 mm** 가 유도됩니다.",
    "→ **공식 외형이 이깁니다.** 카탈로그 대각선은 이제 암/모터 두께 스케일로만 쓰입니다.",
    "(같은 이유로 Mini 5 Pro 도 250 mm 추정 → **274.6 mm**.)",
    "",
    "> 그래서 이 노트북의 모든 그림은 **메쉬 대각선**(공식 외형에서 유도)을 씁니다 — 카탈로그 추정치가 아니라.",
))

cells.append(md(
    "## 5. 메쉬 검증 — trimesh (프로펠러 법선 버그)",
    "",
    "![mesh check](outputs/figures/report1_mesh_check.png)",
    "",
    "`geom.py` 는 의존성 없이 삼각형을 쌓는 도구라 **메쉬가 옳은지 검사할 능력이 없습니다.**",
    "그 사이에 조용히 살아 있던 버그: **`prop_blade` 의 캡 2장이 안쪽으로 감겨 있었습니다**",
    "(주석에는 \"outward\" 라고 적혀 있었습니다).",
    "PO 의 조명 판정은 `n̂ · û > 0` 이라 **뒤집힌 법선은 엉뚱한 면을 골라 넣습니다** —",
    "그것도 하필 **프로펠러**, 즉 **마이크로도플러 신호 그 자체**에서요.",
    "trimesh 는 이걸 1초 만에 잡았습니다. 이제 `mesh_check.assert_ok()` 를 빌드에 넣어 회귀를 막습니다.",
))

cells.append(code(
    "# (선택 실행) 메쉬 검증을 직접 돌려보기 — 5종 × 전 부위",
    "import sys; sys.path.insert(0, 'src')",
    "from mesh_check import check_all, report",
    "res = check_all(verbose=False)",
    "for k, r in res.items():",
    "    print(f\"[{k}] {'✅ 통과' if r['ok'] else '❌ 결함'}\")",
    "print()",
    "print(report(res['mavic4pro']))",
))

cells.append(md(
    "## 6. 드론 5종 — Sionna 렌더 3뷰",
    "",
    "각 드론을 **Sionna 가 iso / side / top 3뷰**로 촬영했습니다.",
    "**side 뷰를 보세요** — 오늘 고친 높이(공식 외형)가 바로 거기서 보입니다.",
    "표의 `mesh` 열은 렌더된 그 메쉬를 실제로 재서 적은 값입니다.",
    "",
    "![gallery](outputs/figures/report1_gallery.png)",
    "",
    "### 6-1. DJI Mini 5 Pro  (초소형, sub-250 g)",
    "![mini5pro](outputs/figures/report1_drone_mini5pro.png)",
    "",
    "### 6-2. DJI Mavic 4 Pro  (대형 소비자 플래그십 — 대각선 모순 기종)",
    "![mavic4pro](outputs/figures/report1_drone_mavic4pro.png)",
    "",
    "### 6-3. DJI Matrice 4E  (엔터프라이즈 RTK — **정합 방법의 독립 검증 기종**)",
    "![matrice4e](outputs/figures/report1_drone_matrice4e.png)",
    "",
    "### 6-4. DJI S1000+  (8암 옥토콥터, 단종)",
    "![s1000plus](outputs/figures/report1_drone_s1000plus.png)",
    "",
    "### 6-5. DJI Phantom 4  (고정암 클래식)",
    "![phantom4](outputs/figures/report1_drone_phantom4.png)",
))

cells.append(md(
    "## 7. 제원 표 (원자료)",
    "",
    "제원은 **공식 DJI 페이지 + 리뷰 사이트를 웹 조사하고 독립적으로 교차검증**했습니다",
    "(원자료: `docs/drone_research.json`). 주의사항:",
    "",
    "- **Matrice 4E** 프로펠러 지름은 검증으로 292 → **274 mm** 로 정정했습니다.",
    "- **S1000+** 는 4암이 아니라 **8암 옥토콥터**입니다. **무게 4400 g 은 기체(airframe) 자중**이라",
    "  실제 권장 이륙중량은 **6.0~11.0 kg** 입니다 — 나머지 4종(이륙중량 기준)과 같은 잣대가 아닙니다.",
    "- **대각거리는 Mini 5 Pro / Mavic 4 Pro 두 기종을 DJI 가 공개하지 않습니다.** §4 에서 보았듯",
    "  카탈로그 추정치(250 / 400 mm)는 공식 외형과 어긋나며, 이제 **외형에서 유도한 값**(274.6 / 440.9 mm)을 씁니다.",
    "- 표의 **신뢰도(confidence)는 제원 세트 전체**에 대한 등급이지 개별 항목의 등급이 아닙니다.",
))

cells.append(code(
    "import sys; sys.path.insert(0, 'src')",
    "import pandas as pd",
    "from drones import DRONES, frame_envelope_mm",
    "rows = []",
    "for k, s in DRONES.items():",
    "    e = frame_envelope_mm(s)",
    "    rows.append(dict(키=k, 이름=s.name, 출시=s.release, 로터=s.num_rotors,",
    "                     대각_카탈로그_mm=s.diagonal_mm,",
    "                     대각_메쉬_mm=round(e['diagonal_effective_mm'], 1),",
    "                     공식외형_mm=s.envelope_mm,",
    "                     무게_g=s.weight_g, 프롭_mm=s.prop_dia_mm, 날=s.prop_blades,",
    "                     RTK=s.rtk, 신뢰도=s.confidence))",
    "pd.DataFrame(rows).set_index('키')",
))

cells.append(md(
    "## 8. 크기 비교 · 상세 카드 (치수 도면)",
    "",
    "여기 두 절은 **matplotlib 도면**입니다 — 치수선·화살표·제원표는 사진 렌더로 대체할 수 없습니다.",
    "단, **모터 위치는 렌더와 같은 메쉬**(`rotor_layout`)에서 읽으므로 렌더와 도면이 어긋나지 않습니다.",
    "",
    "### 8-a) 5종 크기 비교 (같은 축척)",
    "![size compare](outputs/figures/size_compare.png)",
    "",
    "### 8-b) 드론별 상세 카드",
    "각 카드는 **① Sionna 렌더 · ② 위에서 본 도면(대각/프롭원/공식외형) · ③ 옆면도(공식 H 밴드) · ④ 제원표** 입니다.",
    "",
    "| | |",
    "|---|---|",
    "| ![mini5pro](outputs/figures/card_mini5pro.png) | ![mavic4pro](outputs/figures/card_mavic4pro.png) |",
    "| ![matrice4e](outputs/figures/card_matrice4e.png) | ![s1000plus](outputs/figures/card_s1000plus.png) |",
    "| ![phantom4](outputs/figures/card_phantom4.png) | |",
))

cells.append(md(
    "## 9. 회전 애니메이션 (Sionna 턴테이블)",
    "",
    "형상을 가장 직관적으로 보는 방법 — 빙 돌려 보기.",
    "**예전엔 matplotlib 3D 회전이었지만, 이제 Sionna 카메라를 방위각으로 36스텝 돌려 렌더한 프레임**입니다.",
    "",
    "![all](outputs/figures/report1_turntable_all.gif)",
    "",
    "개별 GIF: `outputs/figures/report1_turntable_<키>.gif`",
    "(mini5pro / mavic4pro / matrice4e / s1000plus / phantom4).",
))

cells.append(md(
    "## 10. 여기서 이어지는 것 (report2~6)",
    "",
    "이 노트북은 **무대(기하 + 재질 + 시각화)** 까지입니다. 모델에는 **부위별 전파재질**이 붙어 있고",
    "(`materials.py` 가 Sionna 와 PO/SBR 의 **단일 진리원**), 그대로 전파 시뮬레이션에 쓰입니다:",
    "",
    "- 🎯 **report2** — 모노스태틱 RCS (SBR = Mitsuba 광선 + PO 적분, 가림 포함) + WiFi/LTE/5G 파형·점유",
    "- 🌀 **report3** — 분절 드론(몸체 ⟂ 로터) + 회전 블레이드 마이크로도플러",
    "- 📡 **report4** — 챔버 내부 바이스태틱 패시브 레이더 탐지 (ECA → CAF → CFAR → Pd)",
    "- ⚖️ **report5** — 링크버짓 기반 공정 벤치마크 + Sionna RT 교차검증",
    "- 🔬 **report6** — 검증: RT 는 표적 σ 를 못 준다 / 바닥 유령은 ECA 를 통과한다",
    "",
    "**하이브리드가 강제되는 이유**(report6 이 측정으로 보인 것):",
    "환경(경로·지연·도플러)은 **RT** 가 정확하다(§2 의 바닥반사 19.3 ns / −14.7 dB).",
    "그러나 표적 σ 는 **산란적분**에서 나온다 — Sionna 기본 solver 에는 그 단계가 없어",
    "광선을 4억 발 쏘아도 수렴하지 않는다. 그래서 σ 는 **SBR**(광선 + PO 적분)이 계산한다.",
    "",
    "> 주의: \"레이트레이싱은 RCS 를 못 낸다\"는 **거짓**입니다 — SBR 은 레이트레이싱이고 σ 를 계산합니다.",
    "> 참인 명제는 좁습니다: *산란적분 단계가 없는 전파용 레이트레이서(Sionna RT 기본 solver)에서는 σ 가 창발하지 않는다.*",
))


def main():
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3.12 (py312)", "language": "python",
                            "name": "py312"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4, "nbformat_minor": 5,
    }
    with open(NB, "w") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print("notebook 생성:", os.path.relpath(NB), f"({len(cells)} cells)")


if __name__ == "__main__":
    main()
