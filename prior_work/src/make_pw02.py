# -*- coding: utf-8 -*-
"""make_pw02.py — pw02_opensource_tools.ipynb 생성기. ⚠ 이 파일이 소스다.

pw02 — "오픈소스 센싱/ISAC 시뮬·실험 도구 지도 — 무엇을 채택할까"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pw_common import TOOLS, SYN, BADGE, md, code, srclinks, write_nb  # noqa: E402

ORDER = ["5gnrad", "radarsimpy", "openisac", "matlab", "ns3sionna", "msvan3t"]


def tool_block(k):
    t = TOOLS[k]
    return md(
        f"### {BADGE[t['grade']]}  {t['name']}  —  채택도 판정: **{t['adopt'].split('(')[0].strip()}**",
        f"- **저장소·출처**: {t['repo']}  ({srclinks(t)})",
        f"- **라이선스**: {t['license']}",
        f"- **무엇을 하나**: {t['does']}",
        f"- **표적 산란 처리**: {t['target_scatter']}",
        f"- **검출체인?** {t['detection']}",
        f"- **우리 프로젝트 채택**: {t['adopt']}",
    )


# 능력 매트릭스 (JSON 필드에서 규칙 유도)
def cap_row(k):
    t = TOOLS[k]
    def y(s):
        return "✅" if s else "—"
    passive = "openisac" == k  # 바이스태틱 OTA 지원
    rcs_mesh = k in ("radarsimpy",)
    detect = "✅" in t["detection"]
    ill = "WiFi/LTE/5G" if k in ("5gnrad", "matlab") and False else \
          ("연속 OFDM" if k == "openisac" else ("5G NR" if k in ("5gnrad", "matlab") else "—"))
    return (f"| {t['name']} | {t['license'].split('(')[0].strip()} | "
            f"{ill} | {y(rcs_mesh)} | {y(detect)} | {y(passive)} | "
            f"{t['adopt'].split('(')[0].strip()} |")


cells = [
    md(
        "# pw02 — 오픈소스 센싱/ISAC 도구 지도",
        "",
        "> ⚠ **이 노트북은 생성물이다. 수정은 `prior_work/src/make_pw02.py` 에서** 하고 재실행할 것.",
        "> 모든 사실·라이선스는 `prior_work/outputs/prior_work.json`(직접 GitHub/arXiv 확인) 에서 주입한다.",
        "",
        "질문: **이미 존재하는 오픈소스가 우리 조각(패시브 바이스태틱 + SBR+PO 드론 RCS + ECA/CAF/CFAR)을 "
        "대신 해 주는가?** 답을 미리 말하면 — **통째로 해 주는 도구는 없지만, 조각별로 빌려 쓸 좋은 것이 "
        "있다**(OpenISAC·RadarSimPy). 무엇을 어떻게 채택할지 정한다.",
    ),
    md(
        "## §1. 능력 매트릭스 (한눈에)",
        "",
        "| 도구 | 라이선스 | 조명 파형 | 메쉬 RCS | 검출체인(CFAR) | 패시브 바이스태틱 | 채택 |",
        "|---|---|---|---|---|---|---|",
        cap_row("5gnrad"),
        cap_row("radarsimpy"),
        cap_row("openisac"),
        cap_row("matlab"),
        cap_row("ns3sionna"),
        cap_row("msvan3t"),
        "",
        "> **읽는 법.** 어떤 한 도구도 6칸을 다 채우지 못한다 — 이게 우리가 스택을 **직접 조립한** 이유다. "
        "다만 **RadarSimPy 는 메쉬 RCS**, **OpenISAC 은 X410 바이스태틱**, **NIST 5GNRad 은 검출체인 "
        "아키텍처**를 각각 잘 해 준다.",
    ),
    md("---", "## §2. 채택도 HIGH — 실제로 쓸 것"),
    tool_block("5gnrad"),
    tool_block("radarsimpy"),
    tool_block("openisac"),
    md(
        "> 🔑 **세 도구의 역할 분담(우리 프로젝트에서).**",
        "> - **NIST 5GNRad** — *아키텍처 참조*. `h = h_background + h_target`(표적/배경 채널 분리)이 "
        "우리 report12 구조와 **동일**하다는 강력한 방증. 검출체인(range-Doppler·CFAR·clustering) 설계를 "
        "대조한다. (능동/PRS 기반이라 코드 이식은 아님.)",
        "> - **RadarSimPy** (GPLv3) — *검증 오라클*. 3D STL 메쉬에서 RCS·프로펠러 마이크로도플러를 "
        "**독립 도구로 다시 계산**해 우리 SBR+PO(report07/08)와 대조한다. 완전 오픈이라 자유 사용.",
        "> - **OpenISAC** — *실측 다리*. **USRP X410 + 바이스태틱 OTA 동기**가 사용자 하드웨어 계획과 "
        "직결. sim→real 단계에서 실제 OTA 실험 골격으로 채택.",
    ),
    md("---", "## §3. 채택도 MEDIUM / LOW — 참조 또는 불채택"),
    tool_block("matlab"),
    tool_block("ns3sionna"),
    tool_block("msvan3t"),
    md(
        "> **왜 ns3sionna·ms-van3t 는 불채택인가.** 둘 다 Sionna 를 ns-3 **네트워크/MAC 층**에 붙이는 "
        "채널결합이다 — CSI 를 내보낼 뿐 레이더 표적산란·RCS·CFAR 이 전무하다. 우리 물리레이어 패시브 "
        "레이더와 다른 층의 도구다.",
    ),
    code(
        "# 도구별 채택 판정 — prior_work.json 에서",
        "import json",
        "J = json.load(open('outputs/prior_work.json', encoding='utf-8'))",
        "for t in J['tools']:",
        "    tag = t['adopt'].split('(')[0].strip()",
        "    print(f\"{tag:8s} | {t['name']:26s} | {t['license'][:22]:22s} | {t['repo'][:40]}\")",
    ),
    md(
        "---",
        "## §4. 정리 — 채택 계획",
        "",
        f"{SYN['adoption_plan']}",
        "",
        "요컨대 **시뮬 단계**는 우리 스택(Sionna 챔버 + SBR+PO + 자체 검출)을 유지하되 "
        "**RadarSimPy 로 RCS·마이크로도플러를 교차검증**하고, **실측 단계**는 **OpenISAC+X410** 골격을 "
        "빌려 OTA 바이스태틱을 실현한다. **NIST 5GNRad** 는 검출체인 설계의 표준 레퍼런스로 둔다.",
        "",
        "> **다음** → [pw03 — 우리 방법의 위치와 선행 방법론 수용](pw03_positioning.ipynb).",
    ),
]

write_nb(cells, "pw02_opensource_tools.ipynb", "pw02")
