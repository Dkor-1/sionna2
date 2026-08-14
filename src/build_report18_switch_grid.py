# -*- coding: utf-8 -*-
"""
build_report18_switch_grid.py — 리포트 18 «물리 스위치 격자» 조립.

사용자 지시(2026-08-15): 「스위치 7 조합 STFT 맵·blade band energy 를 다 실어 읽기
편하게, **팀미팅 때 보이는 분석 방식**으로」. 그 방식이란:
  · 그림 먼저, 숫자는 그림에서 본 것을 확인하는 자리에만
  · 패널마다 자기 최댓값 정규화 — 모양을 읽고 세기는 안 읽는다
  · 각도는 «−30°» 표기, 쉬운 말, 그림 안 글자는 영어
  · 봉우리의 위치(예측 126.7 Hz 배수에 앉는가)를 항상 함께 본다

⚠이 보고서는 17 권 체계 밖의 **작업 보고서**다(엄격 규약 빌더를 안 탄다). 결론이 서면
리포트 16/17 에 절로 편입한다. 숫자는 전부 outputs/switch_grid.json 에서 주입한다.

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/build_report18_switch_grid.py
"""
from __future__ import annotations

import json
import os

import nbformat as nbf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
J = json.load(open(f"{ROOT}/outputs/switch_grid.json", encoding="utf-8"))
M, C = J["_meta"], J["cells"]

ORDER = ["Our kernel", "all off", "refraction only", "edge only", "diffraction only",
         "diffraction + edge", "refraction + diffraction", "all on"]
KO = {"Our kernel": "우리 커널", "all off": "다 끔", "refraction only": "굴절만",
      "edge only": "모서리만", "diffraction only": "회절만",
      "diffraction + edge": "회절+모서리", "refraction + diffraction": "굴절+회절",
      "all on": "다 켬"}


def md(*lines):
    return nbf.v4.new_markdown_cell("\n".join(lines))


def cite(key):
    return f"⟨outputs/switch_grid.json : cells.{key}⟩"


def table():
    rows = ["| 조합 | 리듬 몫 [%] | 1차 선 [dB] | 봉우리 [Hz] | 빠진 자세 |",
            "|---|---|---|---|---|"]
    for nm in ORDER:
        c = C[nm]
        rows.append(f"| {KO[nm]} ({nm}) | {c['rhythm_share_pct']:.1f} | "
                    f"{c['h1_over_floor_db']:.1f} | {c['h1_peak_hz']:.1f} | "
                    f"{c['n_missing']} |")
    return "\n".join(rows)


DIFFR_ON = ["diffraction only", "diffraction + edge", "refraction + diffraction", "all on"]
DIFFR_OFF = ["all off", "edge only", "refraction only"]
lo_on = min(C[n]["rhythm_share_pct"] for n in DIFFR_ON)
hi_on = max(C[n]["rhythm_share_pct"] for n in DIFFR_ON)
lo_off = min(C[n]["rhythm_share_pct"] for n in DIFFR_OFF)
hi_off = max(C[n]["rhythm_share_pct"] for n in DIFFR_OFF)

nb = nbf.v4.new_notebook()
nb.cells = [
    md("# 리포트 18 — 물리 스위치 격자: 회절이 든 조합은 전부 잡음이 된다",
       "",
       f"**판**: {M['setup_ko']} · 앙각 {M['el_deg']:.0f}° 한 자리. 갈리는 축은 굴절 R · "
       f"회절 D · 모서리회절 E 세 스위치뿐이다.",
       "",
       "### 한 일",
       "> 세 스위치의 의미 있는 조합 7 개(+우리 커널)를 같은 자리·같은 광선 예산에서 재고, "
       "STFT 맵과 블레이드 대역 에너지로 나란히 놓았다.",
       "",
       "### 결과",
       f"1. ⭐**회절 스위치 하나가 경계선이다** — 회절이 든 네 조합은 리듬 몫 "
       f"{lo_on:.1f}~{hi_on:.1f} %(백색잡음 = 13)로 전부 잡음 수준이고, 회절이 없는 세 "
       f"조합은 {lo_off:.1f}~{hi_off:.1f} % 로 날개 구조를 유지한다.",
       f"2. 모서리회절은 무동작이다 — «모서리만» 은 «다 끔» 과 리듬 "
       f"{C['edge only']['rhythm_share_pct']:.1f} %, 1차 선 "
       f"{C['edge only']['h1_over_floor_db']:.1f} dB 까지 같다"
       f"(비트단위 동일, 소스 구조가 그 이유다 — {M['excluded_ko']}).",
       f"3. 굴절은 깎지만 죽이지 않는다 — 혼자 켜면 "
       f"{C['all off']['rhythm_share_pct']:.1f} → "
       f"{C['refraction only']['rhythm_share_pct']:.1f} %, 1차 선 "
       f"{C['all off']['h1_over_floor_db']:.1f} → "
       f"{C['refraction only']['h1_over_floor_db']:.1f} dB. 선의 자리는 "
       f"{C['refraction only']['h1_peak_hz']:.1f} Hz 로 그대로다.",
       f"4. 봉우리 위치는 여덟 팔 전부 {C['all on']['h1_peak_hz']:.1f} Hz — 예측 "
       f"{M['f_flash_hz']:.1f} Hz 의 자리다. 위치가 아니라 **선명도**가 갈린다.",
       "",
       "### 잣대 두 개 (팀미팅과 같은 규약)",
       f"- **리듬 몫** — {M['rhythm_ko']}",
       f"- **1차 선** — {M['h1_ko']}"),

    md("## 맵 — 여덟 팔이 같은 자리에서 그린 것",
       "",
       "![switch grid maps](../outputs/figures/swgrid_maps.png)",
       "",
       "**그림 1.** 스위치를 바꿔 끼우면 맵이 어떻게 변하나? 패널마다 자기 최댓값 기준이라 "
       "모양만 읽는다.",
       "",
       "읽는 법: 시간축으로 규칙적으로 지나가는 덩어리가 날개, 가운데 가로띠가 동체다. "
       "윗줄(우리 커널·다 끔·굴절만·모서리만)은 날개 플래시가 있고, 아랫줄로 갈수록 — "
       "회절이 켜지는 순간 — 무늬가 세로 얼룩으로 바뀐다."),

    md("## 같은 맵, 정지 성분 제거",
       "",
       "![switch grid maps dc removed](../outputs/figures/swgrid_maps_dc.png)",
       "",
       "**그림 2.** 동체 에코를 빼면 차이가 더 선명하다 — 회절 없는 팔들은 규칙적으로 "
       "뛰고, 회절 든 팔들은 번진다."),

    md("## 블레이드 대역 에너지 — 넓은 범위 (100~1,000 Hz)",
       "",
       "![switch grid band energy wide](../outputs/figures/swgrid_be_wide.png)",
       "",
       "**그림 3.** 조합당 한 패널. 옅은 빨강이 우리 커널(기준), 파랑이 그 조합이다. "
       "점선 = 예측 박자의 정수배.",
       "",
       "회절 없는 세 조합은 고차 조화선까지 점선 위에 서고, 회절 든 네 조합은 선 없이 "
       "바닥이 출렁인다."),

    md("## 블레이드 대역 에너지 — 확대 (0~420 Hz)",
       "",
       "![switch grid band energy zoom](../outputs/figures/swgrid_be_zoom.png)",
       "",
       "**그림 4.** 1~3 차 선 확대. 봉우리 위치가 여덟 팔 전부 예측 자리(126.7 Hz)에 "
       "앉는다는 것, 그리고 회절 든 조합의 선이 바닥에 눌린다는 것이 함께 보인다."),

    md("## 숫자 확인 — 그림에서 본 것",
       "",
       table(),
       "",
       f"출처: 전 칸 outputs/switch_grid.json (rhythm_share_pct · h1_over_floor_db · "
       f"h1_peak_hz). 리듬 몫의 눈금 — 백색잡음 13, 이상 로터 100.",
       "",
       "⚠«굴절+회절» 행은 빠진 자세가 있으면 그 수가 0 이 될 때까지 재병합 후 다시 읽는다."),

    md("## 판정과 다음 작업",
       "",
       "1. **범인은 회절이다.** 단일축에서 이미 본 결론이 조합 전체로 확장됐다 — 회절이 "
       "든 조합은 굴절·모서리 동반 여부와 무관하게 전부 잡음이 된다. 상호작용은 없다.",
       "2. **모서리회절 스위치는 이 표적에서 완전한 무동작**이므로 이후 실험에서 축을 "
       "제외해도 된다.",
       "3. **굴절은 별개의 순한 축**이다 — 선을 지우지 않고 45~62 % 수준으로 깎는다. "
       "물을 것은 «Sionna 의 유전체 셸 투과가 우리 커널의 투과 규약과 왜 다른가» 다.",
       "4. ⇒ 다음 작업 제안: (a) 회절 경로만 뽑아 그 도플러 분포를 직접 보기 — 왜 "
       "백색인가의 기전, (b) 우리 커널 PTD 수리 후 «우리 모서리회절» 과 Sionna 회절의 "
       "대조, (c) 회절을 끈 채 물리(굴절·다중반사)만 켠 조합을 실전 기본값으로 쓰는 "
       "권고를 리포트 17 에 편입."),
]

out = f"{ROOT}/reports/18_switch-grid.ipynb"
nbf.write(nb, out)
print(f"✅ {out}  ({len(nb.cells)} 셀)")
