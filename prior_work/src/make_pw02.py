# -*- coding: utf-8 -*-
"""make_pw02.py — pw02_opensource_tools.ipynb 생성기. ⚠ 이 파일이 소스다.

pw02 — "오픈소스 센싱/ISAC 시뮬·실험 도구 지도 — 무엇을 채택할까"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pw_common import TOOLS, SYN, BADGE, md, code, srclinks, write_nb  # noqa: E402

HIGH = ["pyapril", "radarsimpy", "openisac", "5gnrad"]
MED = ["stonesoup", "openems", "gnuradio", "isacplm", "matlab"]
LOW = ["oai", "ns3sionna", "msvan3t"]
ORDER = HIGH + MED + LOW


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
    passive = k in ("openisac", "pyapril", "isacplm")     # 패시브/바이스태틱 처리
    rcs_mesh = k in ("radarsimpy", "openems")             # 메쉬에서 RCS
    detect = ("✅" in t["detection"]) or k == "pyapril"
    layer = {"pyapril": "검출체인(ECA/CAF/CFAR)", "radarsimpy": "RCS·μD", "openisac": "실측 SDR",
             "5gnrad": "5G NR 검출", "stonesoup": "추적", "openems": "full-wave RCS",
             "gnuradio": "실측 I/O", "isacplm": "WiFi(60G) 검출", "matlab": "종합",
             "oai": "실 5G RAN", "ns3sionna": "네트워크", "msvan3t": "V2X"}[k]
    return (f"| **{t['name'].split('(')[0].strip()}** | {t['license'].split('(')[0].strip()} | "
            f"{layer} | {y(rcs_mesh)} | {y(detect)} | {y(passive)} | "
            f"{t['adopt'].split('(')[0].strip()} |")


cells = [
    md(
        "# pw02 — 오픈소스 센싱/ISAC 도구 지도",
        "",
        "> ⚠ **이 노트북은 생성물이다. 수정은 `prior_work/src/make_pw02.py` 에서** 하고 재실행할 것.",
        "> 모든 사실·라이선스는 `prior_work/outputs/prior_work.json`(직접 GitHub/arXiv 확인) 에서 주입한다.",
        "",
        "질문: **이미 존재하는 오픈소스가 우리 조각(패시브 바이스태틱 + SBR+PO 드론 RCS + ECA/CAF/CFAR)을 "
        "대신 해 주는가?** 답 — **통째로 해 주는 한 도구는 없지만, 조각마다 검증된 오픈소스가 있다.** "
        "사용자 방침(‘직접 만든 것을 최대한 오픈소스로 대체’)에 맞춰, 각 조각의 대체 도구를 확정한다.",
        "",
        "> ⚠️ **1차 조사 정정.** 앞서 '패시브 바이스태틱 ECA 는 드롭인 오픈소스가 없다'고 적었는데, "
        "**틀렸다** — **pyAPRiL**(GPLv3, DVB-T/FM 실측 검증)이 정확히 그 드롭인이다(ECA/ECA-B/ECA-S·CAF·"
        "CA-CFAR·DoA). 사용자 심화 서베이가 이를 지목했고, GitHub 로 직접 확인했다.",
    ),
    md(
        "## §1. 능력 매트릭스 (한눈에)",
        "",
        "| 도구 | 라이선스 | 담당 계층 | 메쉬 RCS | 검출/처리 | 패시브·바이스태틱 | 채택 |",
        "|---|---|---|---|---|---|---|",
        cap_row("pyapril"),
        cap_row("radarsimpy"),
        cap_row("openisac"),
        cap_row("5gnrad"),
        cap_row("stonesoup"),
        cap_row("openems"),
        cap_row("gnuradio"),
        cap_row("isacplm"),
        cap_row("matlab"),
        cap_row("oai"),
        cap_row("ns3sionna"),
        cap_row("msvan3t"),
        "",
        "> **읽는 법.** 한 도구가 6칸을 다 채우진 못하지만, **계층마다 대체 도구가 있다** — "
        "검출체인=**pyAPRiL**, RCS=**RadarSimPy/openEMS**, 추적=**Stone Soup**, 실측=**OpenISAC+GNU Radio**. "
        "이게 '직접 만든 것을 오픈소스로 대체'의 실제 지도다(→§4·OPENSOURCE.md).",
    ),
    md("---", "## §2. 채택도 HIGH — 실제로 쓸 것 (우리 코드의 직접 대체/검증)"),
    tool_block("pyapril"),
    tool_block("radarsimpy"),
    tool_block("openisac"),
    tool_block("5gnrad"),
    md(
        "> 🔑 **네 도구의 역할 분담(대체 지도).**",
        "> - **pyAPRiL** (GPLv3) — *검출체인 드롭인*. 우리 손으로 만든 **ECA/CAF/CFAR**(`passive_process.py`)를 "
        "**직접 대체**하는 라이브러리. Sionna 가 만든 r_ref/r_surv 를 넘기면 ECA→CAF→CFAR 를 실측 검증된 "
        "코드로 수행한다. '검증 후 대체' 원칙: 우리 결과와 대조 → 일치 시 권위 소스를 pyAPRiL 로 이관.",
        "> - **RadarSimPy** (GPLv3) — *RCS 검증 오라클*. 3D 메쉬 RCS·마이크로도플러를 독립 재계산해 "
        "SBR+PO(report07/08)와 대조.",
        "> - **OpenISAC** — *실측 다리*. USRP **X410 + 바이스태틱 OTA 동기** — sim→real 골격.",
        "> - **NIST 5GNRad** — *아키텍처 참조*. `h=h_bg+h_target` 가 우리 report12 구조와 동일함을 확인.",
        "",
        "> ⚠️ **단, GPU 몬테카를로는 우리 커널 유지.** pyAPRiL 은 NumPy(CPU) 단일실현 중심이라, report12 의 "
        "수천 회 배치 MC(K=6000)는 우리 `detection_gpu.py`(torch 배치)가 필요하다. **역할: pyAPRiL=기준/검증 "
        "구현·단일실현 분석, 우리 GPU 커널=대량 MC(단 pyAPRiL 로 정합성 검증).**",
    ),
    md("---", "## §3. 채택도 MEDIUM — 특정 단계에서 도입"),
    tool_block("stonesoup"),
    tool_block("openems"),
    tool_block("gnuradio"),
    tool_block("isacplm"),
    tool_block("matlab"),
    md(
        "> **언제 쓰나.** **Stone Soup**=추적 단계(우리 future work — 바이스태틱 custom 측정모델 필요). "
        "**openEMS**=RCS 를 full-wave 로 한 번 더 앵커(느리므로 오프라인 룩업). **GNU Radio**=실측 I/Q 를 "
        "**SigMF** 로 시뮬과 통일. **ISAC-PLM**=WiFi 센싱 참조(단 60GHz DMG 대역). **MATLAB**=1차 baseline 참조.",
    ),
    md("---", "## §3b. 채택도 LOW — 초기 제외"),
    tool_block("oai"),
    tool_block("ns3sionna"),
    tool_block("msvan3t"),
    md(
        "> **왜 초기 제외인가.** **OAI**(실 5G RAN)는 난이도 최고 — 표준 NR 실측 최종단계에서만. "
        "**ns3sionna·ms-van3t** 는 ns-3 **네트워크층** 채널결합이라 CSI 만 내보내고 레이더 RCS/CFAR 이 없다. "
        "지금 넣으면 연구 핵심보다 시스템 통합에 시간이 쏠린다.",
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
        "요컨대 **직접 만든 조각을 계층별로 오픈소스로 대체**한다(‘검증 후 대체’, `OPENSOURCE.md`): "
        "**검출 ECA/CAF/CFAR → pyAPRiL**, **RCS → RadarSimPy(+openEMS 앵커)**, **추적 → Stone Soup**, "
        "**실측 → OpenISAC+GNU Radio+X410(SigMF)**. **파형/채널은 이미 Sionna PHY 로 검증**(report05)돼 유지. "
        "이렇게 하면 우리가 검증 부담을 지던 코드를 실측·표준 검증된 도구가 나눠 져 **신뢰성이 오르고 반복 "
        "수작업이 준다** — 사용자 방침 그대로다.",
        "",
        "> **다음** → [pw03 — 우리 방법의 위치와 선행 방법론 수용](pw03_positioning.ipynb).",
    ),
]

write_nb(cells, "pw02_opensource_tools.ipynb", "pw02")
