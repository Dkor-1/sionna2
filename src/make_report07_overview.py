# -*- coding: utf-8 -*-
"""
make_report07_overview.py — 리포트 07 「마이크로도플러 한눈에 보기」

왜 다시 쓰나
------------
재구성으로 마이크로도플러가 `reports/34~43` **10편**으로 갈라졌다. 그런데 옛
`report07_microdoppler.ipynb` 가 그대로 남아 ① 내용이 중복되고 ② 그림 하나를 두 절이
겹쳐 쓰고 ③ 가장 새로운 결과(세 엔진 맵)가 빠져 있었다.

그래서 이 편의 역할을 바꾼다 — **부 7 의 표지**다.
그림 다섯 장을 한자리에 놓고, 각 장이 무엇을 말하는지 한 줄로 적고, 자세한 편으로 보낸다.

⭐ **그림을 노트북 안에 박는다(base64).** 상대 경로로 걸면 보는 환경에 따라 안 뜬다.
   박아 넣으면 노트북 파일 하나만 열어도, 어디로 옮겨도 보인다.

    python src/make_report07_overview.py
"""
from __future__ import annotations

import base64
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)

FIG = os.path.join(_ROOT, "outputs", "figures")
OUT = os.path.join(_ROOT, "report07_microdoppler.ipynb")

MDB = json.load(open(f"{_ROOT}/outputs/report15b_microdoppler.json"))
TRI = json.load(open(f"{_ROOT}/outputs/report07_three_engines.json"))
MDP = json.load(open(f"{_ROOT}/outputs/report00_microdoppler.json"))
HOV = json.load(open(f"{_ROOT}/outputs/report07_hover_long.json"))["_meta"]
LEAD = MDB["cells"]["matrice4e/belly"]
PH = LEAD["physics"]
FND = LEAD["findings"]
TM = TRI["_meta"]


def embed(stem: str) -> str:
    """그림을 base64 로 박는다 — 경로에 안 매이게."""
    with open(os.path.join(FIG, f"{stem}.png"), "rb") as f:
        b = base64.b64encode(f.read()).decode()
    return f"![{stem}](data:image/png;base64,{b})"


def md(*lines):
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in "\n".join(lines).split("\n")]}


R = FND["rpm_spread_makes_it_time_varying"]
V = TRI["verdict"]["cosine_in_ftip"]
CEN = MDP["specular_census"]["total"]

cells = [
    md("# 리포트 07 — 마이크로도플러 한눈에 보기", "",
       "> **도는 로터가 만드는 무늬는 회전수·가림·자세가 정한다.**", "",
       "이 편은 **부 7 의 표지**다. 그림 다섯 장을 한자리에 놓고 각각이 무엇을 말하는지 "
       "한 줄로 적는다. 자세한 것은 각 절이 가리키는 편에 있다.", "",
       "| 그림 | 무엇을 말하나 | 자세히 |",
       "|---|---|---|",
       "| 1 | 회전수가 같으면 무늬가 시간에 안 변한다 | `reports/37_md-rpm.ipynb` |",
       "| 2 | 두 엔진이 날개끝 아래에서 겹치고 위에서 갈린다 | `reports/36_md-two-engines.ipynb` |",
       "| 3 | ⭐세 엔진을 같은 격자에 태우면 | `reports/36_md-two-engines.ipynb` |",
       "| 4 | 블레이드는 강하고 동체가 덮는다 | `reports/39_md-blade-vs-body.ipynb` |",
       "| 5 | 동체가 막으면 무엇이 달라지나 | `reports/38_md-occlusion.ipynb` |",
       "| ⭐6 | **블레이드 플래시가 7.9 ms 마다 번쩍인다** | 아래 |",
       "| ⭐7 | 2초 호버링 — 능선과 로터 회전수 | 아래 |",
       "",
       f"헤드라인 칸은 **{LEAD['name']}** 를 배 쪽에서 본 것이다 — "
       f"방위 {LEAD['az_deg']:.0f}° · 앙각 {LEAD['el_deg']:.0f}° · "
       f"호버 {PH['rpm']:.0f} rpm · 날개끝 주파수 {PH['f_tip']:.0f} Hz · "
       f"블레이드 통과율 {PH['f_flash']:.1f} Hz.", "",
       "⚠ 이 편의 숫자는 각도의존 Γ(θ) 수정 **이전** 계산에서 나왔다. "
       "재계산 뒤 다시 짓는다."),

    md("## 그림 1 — 회전수가 같으면 무늬가 시간에 안 변한다", "",
       embed("report07_f1"), "",
       f"왼쪽은 네 로터를 같은 회전수로 돌린 것이다. 줄무늬가 시간축 내내 같은 자리에 선다 — "
       f"창을 반으로 갈라 두 스펙트럼의 상관을 재면 **{R['locked_half_corr']:.4f}** 다.", "",
       "⭐ 우연이 아니라 **원리**다. 네 로터가 같은 속도로 위상까지 맞춰 돌면 신호가 완전한 "
       "주기함수가 되고, 주기함수의 스펙트로그램은 창 내내 자기 모습을 지킨다. "
       "그건 물리가 아니라 **가정의 성질**이다.", "",
       f"오른쪽은 로터마다 회전수를 {MDB['_meta']['rpm_spread_frac']:.0%} 흩뜨린 것이다. "
       f"상관이 **{R['spread_half_corr']:.4f}** 로 내려가고 줄이 숨쉬듯 흔들린다.", "",
       "⚠ 흩어짐 폭은 **선언된 가정**이다 — 실측 비행 로그는 앞으로 확보한다."),

    md("## 그림 2 — 두 엔진이 날개끝 아래에서 겹치고 위에서 갈린다", "",
       embed("report07_f2"), "",
       "로터 위상을 스텝하고 매번 다시 추적하는 같은 절차를 **서로 다른 두 엔진**에 태웠다 — "
       "하나는 Sionna 의 PathSolver 이고 하나는 우리 PO 커널이다.", "",
       "운동학이 예측한 날개끝 주파수 **아래**에서 두 빗살이 겹친다. "
       "⭐ 그 위에서 Sionna 의 꼬리가 20~30 dB 높게 남는다 — 그 꼬리는 블레이드가 만든 것이 "
       "아니므로, 가장자리를 자동으로 찾는 검출기는 물리적이지 않은 자리를 가장자리라고 보고한다."),

    md("## 그림 3 — ⭐세 엔진을 같은 격자에 태우면", "",
       embed("report07_f5"), "",
       f"같은 기체·자세·주파수·PRF·로터별 회전수로 세 엔진을 돌렸다 — "
       f"{TM['n']} 표본 @ PRF {TM['prf_hz']:.0f} Hz = {TM['blade_periods']:.0f} 블레이드 주기.", "",
       "| 엔진 | 변조 p-p | 무늬 |",
       "|---|---|---|",
       f"| Sionna PathSolver | {TRI['ptp_db']['sionna']:.1f} dB | 능선이 성기고 날개끝 근처에서 잦아든다 |",
       f"| 우리 SBR | {TRI['ptp_db']['sbr']:.1f} dB | ⚠능선이 대역을 채우고 날개끝 밖에도 남는다 |",
       f"| 우리 순수 PO | {TRI['ptp_db']['po']:.1f} dB | 능선이 몇 가닥에 그친다 |",
       "",
       f"⭐ 셋 다 **(a) 0 도플러 동체 선 · (b) 통과율 간격 능선 · (c) 날개끝 근처 감쇠**를 "
       f"낸다 — 구조가 일치한다. 날개끝 안 스펙트럼 코사인은 "
       f"Sionna↔SBR **{V['sionna_vs_sbr']:.3f}** · Sionna↔PO **{V['sionna_vs_po']:.3f}** · "
       f"SBR↔PO **{V['sbr_vs_po']:.3f}** 다.", "",
       "⚠ 다만 0.65~0.70 은 «닮았다» 까지다. 능선의 세기·밀도가 갈리고 이유가 각각 있다 — "
       "순수 PO 는 가림을 빼고 계산하므로 변조가 씻기고, Sionna 는 경로가 열 개 남짓이라 "
       "성기고, ⚠**우리 SBR 은 날개끝 주파수 밖에도 능선을 낸다**(운동학이 금지한 자리). "
       "그 하나가 남은 의심이고 `reports/42_md-ray-budget.ipynb` 가 그것을 잰다."),

    md("## 그림 4 — 블레이드는 강하고 동체가 덮는다", "",
       embed("report07_f3"), "",
       "같은 자세·같은 주파수에서 전체 드론과 프로펠러 채널을 따로 쟀다. "
       "3.5 GHz 에서 전체 드론의 변조는 **2.84 dB**, 프로펠러만은 **32.32 dB** 다.", "",
       "⭐ 블레이드 신호가 약한 것이 아니라 **동체 정적 반사가 덮고 있다**. "
       "이것이 전처리에서 정적 성분을 지우는 이유다.", "",
       "⚠ 우리 대역에서 블레이드 폭은 파장의 0.09~0.24 배로 전기적으로 작은데, 그래도 변조 "
       "자체는 충분히 크다. 어려운 것은 «블레이드가 약하다» 가 아니라 «동체와 블레이드를 "
       "가르는 일» 이다."),

    md("## 그림 5 — 동체가 막으면 무엇이 달라지나", "",
       embed("report07_f4"), "",
       "가림만 남기고 다른 것을 전부 묶었다. 한쪽은 동체를 완전흡수로 두어 **광선은 막되 "
       "산란은 안 하게** 하고, 다른 쪽은 동체 면만 빼되 정점 배열은 남겨 두었다 — "
       "정점을 남기면 경계상자가 같아서 두 팔의 광선 수와 간격이 같아진다.", "",
       f"헤드라인 칸에서 가림이 변조 깊이를 **{FND['occlusion_ptp_db']:+.2f} dB**, "
       f"레벨을 **{FND['occlusion_level_db']:+.2f} dB** 바꾼다.", "",
       "⚠ 부호를 물리로 단정하지 않는다 — 합이 코히런트라 항이 줄어도 남은 항끼리 상쇄가 "
       "덜 되면 레벨이 올라갈 수 있고, 실제로 그런 칸이 있다.", "",
       "⚠ 프로펠러가 동체 **위**에 있어 위에서 내려다보면 날개가 통째로 드러난다. "
       "지상 레이더는 기체를 **아래에서** 보므로 이 편의 자세는 배 쪽이다."),

    md("## 그림 6 — ⭐블레이드 플래시가 보인다", "",
       embed("report07_f8"), "",
       f"같은 데이터를 **조각 길이만 바꿔** 두 번 그렸다. 왼쪽은 조각이 블레이드 한 주기보다 "
       f"짧아(0.61 주기) **플래시 아치가 {1000/HOV['f_flash_hz']:.1f} ms 마다 또렷하다**. "
       f"오른쪽은 조각이 6.5 주기라 그 아치가 시간평균으로 지워지고 능선만 남는다.", "",
       "⭐ 이것이 시간·주파수 분해능의 **맞바꿈**이다. 둘 다 동시에는 원리적으로 못 본다 — "
       "짧은 조각은 플래시를 보여주고 주파수를 뭉개고, 긴 조각은 그 반대다.", "",
       "⚠ 그동안 우리 그림에 플래시가 안 보였던 이유가 조각을 6.5 주기로 잡은 것이었다. "
       "물리가 아니라 표시 설정이었다."),

    md("## 그림 7 — 2 초 호버링, 능선과 로터 회전수", "",
       embed("report07_f7"), "",
       f"{HOV['seconds']:.0f} 초 · {HOV['n']:,} 표본 · {HOV['blade_periods']:.0f} 블레이드 주기. "
       f"아래 패널이 네 로터의 회전수다 — 능선이 어떻게 움직이는지의 원인이 거기 있다.", "",
       f"⭐ 로터별 산포를 **{HOV['static_spread']:.2%}** 로 뒀다. 이것은 추측이 아니라 "
       f"선배(홍지혁)의 PX4 텔레메트리를 직접 재서 나온 값이다(모터 간 0.07~0.29 %).", "",
       "⚠ 한때 나는 그 실측을 «너무 작아 비현실적» 이라 여기고 ±2 % 를 넣었다. "
       "그러자 네 로터의 빗살이 고조파마다 어긋나 **맵이 뭉개졌다**. "
       "문헌 그림의 능선이 가늘고 선명한 이유가 로터들이 거의 같은 속도이기 때문이다.", "",
       f"⚠ 제어루프 흔들림(±{HOV['wobble_amp']:.2%} @ {HOV['wobble_hz']:.1f} Hz)은 아직 "
       f"**선언된 가정**이다 — 실측 비행 로그가 그 자리를 채운다."),

    md("## 이 편이 서 있는 자리", "",
       f"자세×로터위상 **{CEN['n_cells']:,}칸** 전수에서 프로펠러에 떨어진 정반사 경로는 "
       f"**{CEN['n_with_prop_specular']}칸** 이다. 위상은 광선 엔진이, 세기는 PO 커널이 "
       f"맡는 이유가 여기 있다.", "",
       "| 다음에 할 것 | 그러면 결정되는 것 |",
       "|---|---|",
       "| ⭐SBR 의 날개끝 밖 능선을 규명한다 | 광선 격자의 이산화 산물인지 물리인지 갈린다 |",
       "| 각도의존 Γ(θ) 로 재계산한다 | 이 편의 모든 숫자가 갱신된다 |",
       "| 비행 로그의 모터별 회전수를 넣는다 | 선언된 가정이 측정값으로 바뀐다 |",
       "| 가림을 자세 전면으로 넓힌다 | 분류기가 배울 대비 지도가 선다 |",
       "",
       "**세부 편** — `reports/34_md-paths-doppler` · `35_md-slowtime` · `36_md-two-engines` · "
       "`37_md-rpm` · `38_md-occlusion` · `39_md-blade-vs-body` · `40_md-attitude` · "
       "`41_md-calibration` · `42_md-ray-budget` · `43_md-prf`"),
]

nb = {"cells": cells, "metadata": {
    "kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
    "language_info": {"name": "python"}},
    "nbformat": 4, "nbformat_minor": 5}

with open(OUT, "w") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

sz = os.path.getsize(OUT) / 1e6
print(f"  ✅ {os.path.basename(OUT)} — 셀 {len(cells)}개 · 그림 5장 **박아 넣음** · {sz:.1f} MB")
