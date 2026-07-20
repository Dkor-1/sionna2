# -*- coding: utf-8 -*-
"""make_pw01.py — pw01_sionna_isac_papers.ipynb 생성기. ⚠ 이 파일이 소스다.

pw01 — "Sionna 로 ISAC 센싱을 한 선행 논문들, 그리고 그들이 표적 산란을 어떻게 처리했나"
모든 사실은 prior_work/outputs/prior_work.json 에서 읽어 주입(검증등급 배지 포함).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pw_common import PAPERS, SYN, BADGE, md, code, srclinks, write_nb  # noqa: E402


def paper_block(k):
    p = PAPERS[k]
    return md(
        f"### {BADGE[p['grade']]}  {p['title']}",
        f"- **저자·출처**: {p['authors']} — {p['venue']}  ({srclinks(p)})",
        f"- **무엇을 센싱?** {p['sensed']}",
        f"- **표적 산란 처리**: {p['target_scatter']}",
        f"- **검출체인?** {p['detection']}",
        f"- **우리와의 관계**: {p['vs_us']}",
    )


cells = [
    md(
        "# pw01 — Sionna 로 ISAC 센싱을 한 선행 논문들",
        "",
        "> ⚠ **이 노트북은 생성물이다. 수정은 `prior_work/src/make_pw01.py` 에서** 하고 재실행할 것.",
        "> 모든 사실·인용은 `prior_work/outputs/prior_work.json`(2× 딥리서치 + 직접 웹확인) 에서 주입한다.",
        "",
        "**두 질문에 답한다:** ① *Sionna 로 ISAC(센싱)을 한 선행 논문이 실제로 존재하나?* ",
        "② 존재한다면 *우리가 마주한 간극(스톡 Sionna 는 소형 표적의 코히어런트 RCS 를 메쉬에서 못 낸다, "
        "report06)을 그들은 어떻게 우회했나?*",
        "",
        "**검증 등급(정직성 장치):** "
        + " · ".join(f"{v}={k}" for k, v in {kk: BADGE[kk] for kk in BADGE}.items()),
        "— 다른 AI 답변에 나온 논문명은 환각 가능성이 있어, **실재를 1차 출처로 확인한 것만** 싣는다.",
    ),
    md(
        "## §1. 한 줄 답",
        "",
        "**① 존재한다 — 다수.** 아래 6건은 전부 실재를 확인했다(arXiv/GitHub 1차 출처). ",
        "**② 소형 표적 코히어런트 RCS 를 스톡 Sionna 로 푼 선행은 없다.** 표준 우회는 세 갈래다:",
        "",
        "| 우회 | 뜻 | 대표 선행 |",
        "|---|---|---|",
        "| **(b) 확산 산란계수 S** | 표면에 S∈[0,1] 를 주고 산란전력을 S² 로 배분(재질별, 실측 보정) | Great-X, Deterministic-Modeling |",
        "| **(c) RCS 점표적 주입** | 표적을 점으로 보고 σ(상수)를 채널에 넣음 (h = h_bg + h_target) | NIST 5GNRad·3GPP·MATLAB(→pw02) |",
        "| **(d) 커스텀 산란 add-on** | Sionna 를 기저엔진으로만 쓰고 산란모델을 직접 얹음 | Ziganshin(UTD 회절), **우리(SBR+PO)** |",
        "",
        "우리는 (d)로 **값을 계산**(SBR+PO)해 (c)로 **채널에 주입**한다 — 뒤에서 자세히(§4·pw03).",
    ),
    md("---", "## §2. Sionna 로 드론/차량을 센싱한 선행 (표적 산란이 핵심)"),
    paper_block("great_x"),
    paper_block("det_isac"),
    paper_block("ziganshin"),
    md(
        "> 🔑 **읽는 법.** 셋 다 '표적을 메쉬에서 코히어런트 RCS 로 계산'하지 **않는다**. Great-X·"
        "Deterministic-Modeling 은 **확산계수 S**(b)로, Ziganshin 은 **커스텀 UTD**(d)로 우회한다. "
        "우리와 정신이 가장 가까운 건 Ziganshin(‘Sionna + 직접 만든 산란’)이지만, 그들은 UTD·대형표적, "
        "우리는 PO/SBR·소형 드론이다.",
    ),
    md("---", "## §3. Sionna 를 ISAC 에 쓰지만 '표적 RCS'는 안 하는 선행 (문맥용)"),
    paper_block("cissir"),
    paper_block("simart"),
    md(
        "> **왜 이 둘도 싣나.** CISSIR 은 **NVIDIA 공식 'Made with Sionna' 쇼케이스의 유일한 ISAC "
        "등재작**인데도 물리 표적 RCS 를 다루지 않는다 — 소형표적 RCS ISAC 이 스톡 Sionna 의 표준 용례가 "
        "아니라는 방증이다. SimART 는 다른 AI 답변이 'Sionna ISAC'으로 든 예지만, 실제 '센싱'은 "
        "카메라(YOLOv8)+GPS 라 우리 패시브 레이더 조각과 겹치지 않는다(정직한 구분).",
    ),
    md("---", "## §4. 우리 주장은 선행에 의해 **지지**된다"),
    paper_block("sionna_rt"),
    md(
        f"**{SYN['support_for_our_claim']}**",
        "",
        "즉 report06 이 다섯 방식으로 실증한 'PathSolver 에 산란적분 없음'은 우리만의 발견이 아니라, "
        "**Sionna 창설 논문이 문서화**하고 **EuCAP 2026 논문이 재확인**한 사실이다. 우리가 한 일은 그 "
        "한계를 인정하고 **SBR+PO 를 부분적으로 더한 것**(report07)이다.",
    ),
    code(
        "# 이 리포트가 인용한 선행 논문 — 전부 prior_work.json 에서 (손으로 안 적음)",
        "import json, os",
        "J = json.load(open('outputs/prior_work.json', encoding='utf-8'))",
        "for p in J['papers']:",
        "    print(f\"[{p['grade']:9s}] {p['venue']}\")",
        "    print(f\"           {p['title'][:70]}\")",
    ),
    md(
        "---",
        "## §5. 정리",
        "",
        "1. **Sionna-ISAC 선행은 많다** — 드론(Great-X)·차량(Deterministic-Modeling·Ziganshin)·"
        "NVIDIA 공식(CISSIR)까지.",
        f"2. **{SYN['q2_gap_workarounds']}**",
        "3. 우리 위치와 '덜 점유된 틈새'는 다음 편에서 — **도구 지도(pw02)** 와 **포지셔닝(pw03)**.",
        "",
        "> **다음** → [pw02 — 오픈소스 센싱/ISAC 도구 지도](pw02_opensource_tools.ipynb): "
        "NIST 5GNRad·RadarSimPy·OpenISAC 가 무엇을 해 주고, 우리 프로젝트에 무엇을 채택할까.",
    ),
]

write_nb(cells, "pw01_sionna_isac_papers.ipynb", "pw01")
