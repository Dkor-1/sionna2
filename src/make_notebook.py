# -*- coding: utf-8 -*-
"""make_notebook.py — report.ipynb(한글 단계별 설명서) 생성기.
이미지를 markdown 으로 박아 넣어, 커널을 안 돌려도 VSCode 미리보기에서 바로 보인다.
실행하면 sionna2/report.ipynb 를 새로 만든다."""
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
    "# 📦 report1 — 환경 세팅 (Environment Setup)",
    "",
    "> **이 노트북 = 1단계: 환경 세팅.** 레이더 실험을 하기 위한 '무대'를 만든 단계입니다.",
    "> 여기서는 **차폐시설 + DJI 드론 5종**을 3D로 만들고 시각화했습니다.",
    "> 실제 레이더(송수신·RCS·검출) 실험은 다음 노트북 **report2, report3 …** 으로 이어집니다.",
    "",
    "> 이 노트북은 **처음 보는 사람도 차근차근 이해**할 수 있도록 만든 안내서입니다.",
    "> 셀을 실행하지 않아도 아래 그림들은 바로 보입니다(이미지를 박아 두었기 때문).",
    "> 직접 코드를 돌려보고 싶으면, 오른쪽 위에서 커널을 **py312 (Python 3.12)** 로 고르고 셀을 실행하세요.",
    "",
    "**무엇을 만들었나요?**",
    "1. 사진 속 **대형 차폐시설(전파무반사실, 30 m × 20 m × 11 m)** 의 3D 모델",
    "2. **DJI 드론 5종**(Mini 5 Pro / Mavic 4 Pro / Matrice 4E / S1000+ / Phantom 4)을",
    "   **실제 제원(웹 조사 + 교차검증)** 그대로 반영한 치수 정확 3D 모델",
    "3. 위 둘을 **그림으로 최대한 많이** — 도면 · 크기비교 · 회전GIF · Sionna 렌더",
    "",
    "**왜 이렇게 나눴나요?** 예전 작업이 너무 복잡해서, 여기서는 **딱 두 가지(시설 + 드론)**만",
    "아주 단순하고 투명하게 다시 만들었습니다. 코드도 외부 3D 라이브러리 없이 *삼각형부터* 직접 쌓았습니다.",
))

cells.append(md(
    "## 0. 폴더 구조 한눈에 보기",
    "",
    "```",
    "sionna2/",
    "├─ src/                  # 코드 (전부 한글 주석)",
    "│  ├─ geom.py            # ① 삼각형으로 3D 도형 만드는 미니 도구 (의존성 없음)",
    "│  ├─ chamber.py         # ② 차폐시설 모델 (바닥·흡수체·골조·문)",
    "│  ├─ drones.py          # ③ 드론 5종 실측 제원 + 파라메트릭 생성기",
    "│  ├─ materials.py       # ④ Sionna 전파재질(금속/콘크리트/흡수체…)",
    "│  ├─ scene_build.py     # ⑤ 부위 OBJ → Sionna 장면 조립 + 렌더 엔진",
    "│  ├─ viz_diagram.py     # ⑥ 도면식 그림(카드·크기비교·시설도면)",
    "│  ├─ viz_anim.py        # ⑦ 회전 GIF",
    "│  ├─ render_drones.py   # ⑧ Sionna 사진풍 렌더(시설/스튜디오/장면)",
    "│  ├─ viz_montage.py     # ⑨ 렌더 모아 카탈로그",
    "│  └─ build_all.py       # ⓪ 한 번에 전부 생성",
    "├─ assets/meshes/        # 만들어진 OBJ (부위별로 분리)",
    "├─ outputs/figures/      # 도면·그래프·GIF",
    "├─ outputs/renders/      # Sionna 렌더 PNG",
    "└─ docs/                 # 제원 조사 원자료 등",
    "```",
    "",
    "**한 번에 다시 만들기** (터미널):",
    "```bash",
    "PY=/home/yunjung/.venvs/py312/bin/python",
    "cd sionna2/src && CUDA_VISIBLE_DEVICES=0 $PY build_all.py",
    "```",
))

cells.append(md(
    "## 1. 대형 차폐시설 (전파무반사실)",
    "",
    "**차폐시설**은 두 가지 기능을 합니다 (사진과 똑같이 모델링했습니다):",
    "",
    "| 구성 | 역할 | 모델에서 |",
    "|---|---|---|",
    "| 🧱 **금속 차폐벽** | 바깥 전파를 막음(안↔밖 차단) | 흡수체 뒤의 금속판 |",
    "| 🔺 **피라미드 전파흡수체** | 안에서 쏜 전파의 **메아리 제거**(무반사) | 4면 벽 + 천장 |",
    "| ▦ 체커보드 바닥 | 작업 공간 | 밝은/어두운 타일 교차 |",
    "| 🟦 파란 트림 / 🏗️ 강철 골조 / 🚪 출입문 | 사진의 외형 요소 | 그대로 |",
    "",
    "> 왜 무반사가 중요? 드론의 미세한 전파반사(RCS)를 재려면 벽 메아리가 없어야 합니다.",
    "> 피라미드 모양이 전파를 **여러 번 튕기며 가둬** 흡수하므로, 평평한 벽보다 훨씬 잘 흡수합니다.",
    "",
    "### 1-a) 시설 도면 (치수)",
    "![chamber schematic](outputs/figures/chamber_schematic.png)",
    "",
    "### 1-b) Sionna RT 렌더 (사진풍)",
    "![facility](outputs/renders/facility_hero.png)",
))

cells.append(code(
    "# (선택 실행) 차폐시설을 직접 만들어 통계 보기",
    "import sys, os; sys.path.insert(0, 'src')",
    "import chamber",
    "m, info = chamber.build_chamber()",
    "print('실내 크기 (W×D×H):', info['W'], '×', info['D'], '×', info['H'], 'm')",
    "print('전체 삼각형 수     :', info['n_tris'])",
    "print('부위 그룹          :', ', '.join(info['groups']))",
))

cells.append(md(
    "## 2. DJI 드론 5종 — 실측 제원",
    "",
    "각 드론의 제원은 **공식 DJI 페이지 + 리뷰 사이트를 웹 조사하고, 독립적으로 한 번 더 교차검증**해서",
    "얻었습니다(원자료: `docs/drone_research.json`). 핵심 주의사항:",
    "",
    "- **Mavic 4 Pro** 는 2025년 출시작입니다(무게 1063 g, 언폴드 328.7×390.5×135.2 mm 공식).",
    "  전방 3카메라 짐벌(360° 무한회전)이 특징입니다.",
    "- **Matrice 4E** 프로펠러 지름은 검증으로 292 → **274 mm** 로 정정했습니다.",
    "- **S1000+** 는 4암이 아니라 **8암 옥토콥터**(암당 로터 1개)입니다.",
    "- Mini 5 Pro 의 '대각거리'는 DJI 비공개라 외형에서 **추정(±20 mm)** 한 값입니다.",
    "",
    "아래 셀을 실행하면 제원 표가 나옵니다.",
))

cells.append(code(
    "import sys; sys.path.insert(0, 'src')",
    "import pandas as pd",
    "from drones import DRONES",
    "rows = []",
    "for k, s in DRONES.items():",
    "    rows.append(dict(키=k, 이름=s.name, 출시=s.release, 로터=s.num_rotors,",
    "                     대각_mm=s.diagonal_mm, 무게_g=s.weight_g,",
    "                     프롭_mm=s.prop_dia_mm, 날=s.prop_blades,",
    "                     RTK=s.rtk, 신뢰도=s.confidence))",
    "df = pd.DataFrame(rows).set_index('키')",
    "df",
))

cells.append(md(
    "### 2-a) 5종 크기 비교 (같은 축척)",
    "",
    "프로펠러 회전영역(점선원)까지 **같은 축척**으로 그렸습니다. S1000+ 가 압도적으로 크고,",
    "Mini 5 Pro 는 손바닥만 합니다(250 g). 오른쪽 아래 무게는 250 g ~ 4400 g 라 **로그축**입니다.",
    "",
    "![size compare](outputs/figures/size_compare.png)",
))

cells.append(md(
    "## 3. 드론별 상세 카드 (도면 + 제원)",
    "",
    "각 카드는 **① 3D 모델 · ② 위에서 본 도면(대각거리/프로펠러원) · ③ 옆에서 본 도면(높이) · ④ 제원표**",
    "로 구성됩니다. 색은 부위(동체/암/모터/프로펠러/짐벌/착륙장치)를 뜻합니다.",
    "",
    "### 3-1. DJI Mini 5 Pro  (초소형, sub-250 g)",
    "![mini5pro](outputs/figures/card_mini5pro.png)",
    "",
    "### 3-2. DJI Mavic 4 Pro  (대형 소비자 플래그십)",
    "![mavic4pro](outputs/figures/card_mavic4pro.png)",
    "",
    "### 3-3. DJI Matrice 4E  (엔터프라이즈, RTK)",
    "![matrice4e](outputs/figures/card_matrice4e.png)",
    "",
    "### 3-4. DJI S1000+  (8암 옥토콥터, 단종)",
    "![s1000plus](outputs/figures/card_s1000plus.png)",
    "",
    "### 3-5. DJI Phantom 4  (고정암 클래식)",
    "![phantom4](outputs/figures/card_phantom4.png)",
))

cells.append(md(
    "## 4. 회전 애니메이션 (turntable)",
    "",
    "형상을 가장 직관적으로 보는 방법 — 빙 돌려 보기. (GIF)",
    "",
    "**5종 동시 회전**",
    "![all](outputs/figures/turntable_all.gif)",
    "",
    "개별 GIF 는 `outputs/figures/turntable_<키>.gif` 에 있습니다",
    "(mini5pro / mavic4pro / matrice4e / s1000plus / phantom4).",
))

cells.append(md(
    "## 5. Sionna RT 사진풍 렌더",
    "",
    "Sionna 의 광선추적 렌더러로 만든 '사진 같은' 그림입니다. (전파 시뮬레이션이 아니라 **외형 렌더**)",
    "",
    "### 5-a) 드론 카탈로그",
    "![catalog](outputs/figures/catalog.png)",
    "",
    "### 5-b) 차폐시설 시점 모음",
    "![facility views](outputs/figures/facility_views.png)",
    "",
    "> 참고: 드론은 30 m 방 안에서는 정말 작게 보입니다(현실 그대로). 그래서 **세부 형상은 위의 카드/카탈로그**,",
    "> **크기 감각은 시설 렌더**로 나눠서 보여줍니다.",
))

cells.append(md(
    "## 6. 다음에 할 수 있는 것 (아직 안 한 것)",
    "",
    "지금까지는 **'기하 + 외형 + 시각화'** 까지만 했습니다(요청하신 범위). 이 모델은 그대로",
    "전파 시뮬레이션에 쓸 수 있게 **부위별 전파재질**까지 붙어 있습니다. 원하시면 다음을 이어서:",
    "",
    "- 📡 송신기/수신기 안테나를 시설 안에 놓고 **광선추적(PathSolver)** 실행",
    "- 🎯 드론을 표적으로 한 **RCS / 패시브 레이더** 시뮬레이션",
    "- 🌀 흡수체가 실제로 '무반사'인지 **반사량(-dB) 측정**으로 검증",
    "",
    "원하시는 것만 말씀해 주시면 **한 단계씩** 추가하겠습니다.",
))

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
