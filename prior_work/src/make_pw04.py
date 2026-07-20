# -*- coding: utf-8 -*-
"""make_pw04.py — pw04_rcs_solution_by_target.ipynb 생성기. ⚠ 이 파일이 소스다.

pw04 — "Sionna 를 쓴 센싱 연구는 표적 RCS 문제를 어떻게 해결했나"
  · Sionna(RT/PHY)를 직접 쓰거나 재구현한 연구만 대상.
  · RCS 부재를 어떻게 우회·해결했는지에 집중, A1/A2/B/C/D 다섯 갈래로 분류.
  · 모든 인용은 1차 출처 검증 완료(검증 데이터: prior_work/src/pw04_data.py).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pw_common import md, write_nb  # noqa: E402
import pw04_data as D  # noqa: E402


def table(cols, rows):
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "／") for c in r) + " |")
    return out


cells = []

# ── 헤드 + 조사결론 ──────────────────────────────────────────────────────────
cells.append(md(
    "# pw04 — Sionna 로 센싱한 연구는 표적 RCS 문제를 어떻게 해결했나",
    "",
    "> ⚠ **이 노트북은 생성물이다. 수정은 `prior_work/src/make_pw04.py`·`pw04_data.py` 에서** 하고 재실행할 것.",
    f"> 조사 방법: {D.METHOD}",
    "",
    "## 조사 결론",
    "",
    f"> {D.CONCLUSION['headline']}",
    "",
    D.CONCLUSION["detail"],
    "",
    D.CONCLUSION["nuance"],
))

# ── §1 taxonomy ─────────────────────────────────────────────────────────────
cells.append(md(
    "## §1. 표적 RCS 문제 해결 방식 — 다섯 갈래 (A1/A2/B/C/D)",
    "",
    *table(["갈래", "해결 방식", "의미"],
           [(g, name, desc) for g, name, desc in D.TAXONOMY]),
    "",
    f"**물리적 신뢰도 순서** — {D.CREDIBILITY_ORDER}",
))

# ── §2 표1 (A1/A2/B) ────────────────────────────────────────────────────────
cells.append(md(
    "## §2. Sionna 를 직접 쓰며 RCS 를 **명시적으로 해결하거나 외생 모델로 보완**한 연구",
    "",
    "### 표 1 — A1(외부 EM solver 결합) · A2(Sionna 확장) · B(외생 통계/점산란체)",
    "",
    *table(["연도", "논문 (갈래)", "Sionna 역할", "Sionna 만으론 부족했던 것", "RCS 해결 방법", "해결 수준·한계", "검증"],
           [(r["year"], f"**{r['study']}**<br>`{r['arxiv']}`", r["sionna"], r["gap"], r["how"], r["level"], r["verify"])
            for r in D.TABLE1]),
))

# ── 표2 (C/D) ───────────────────────────────────────────────────────────────
cells.append(md(
    "### 표 2 — C(3D mesh 반사로 우회) · D(RCS 언급하나 구현 미보고)",
    "",
    *table(["연도", "논문 (갈래)", "센싱 태스크·Sionna 역할", "RCS 처리", "가능한 주장", "남는 문제", "검증"],
           [(r["year"], f"**{r['study']}**<br>`{r['arxiv']}`", r["task"], r["how"], r["claim"], r["problem"], r["verify"])
            for r in D.TABLE2]),
    "",
    "> **검증에서 제외·정정한 것 (정직성 기록)**",
    *[f"> - {e}" for e in D.EXCLUDED],
))

# ── §3 표3 (외부 RCS 모델·설계 근거) ─────────────────────────────────────────
cells.append(md(
    "## §3. Sionna 에 부족한 표적 산란을 채울 후보·설계 근거 문헌",
    "",
    "아래는 **Sionna 를 직접 쓰진 않지만** 부족한 target scattering 을 메우거나 설계를 정당화하는 문헌이다. "
    "⚠ aux 검증 결과 아래 **하단 3편(3GPP Framework·SSCR·6G Survey)은 '바로 붙일 RCS 모델'이 아니라 "
    "설계 정당화 인용**임을 명시한다.",
    "",
    "### 표 3 — 외부 RCS / micro-Doppler 모델·설계 근거",
    "",
    *table(["연도", "논문", "제공하는 모델·데이터", "Sionna 결합 방법", "우리 연구에서의 가치", "성격"],
           [(r["year"], f"**{r['study']}**<br>`{r['arxiv']}`", r["model"], r["attach"], r["value"], r["kind"])
            for r in D.TABLE3]),
))

# ── §4 비교 ─────────────────────────────────────────────────────────────────
cells.append(md(
    "## §4. 해결 방식별 비교",
    "",
    *table(["방식", "대표", "물리 정확도", "계산 효율", "Bistatic", "Micro-Doppler", "장점", "핵심 약점"],
           D.COMPARISON),
))

# ── §5 조심할 점 ────────────────────────────────────────────────────────────
cells.append(md(
    "## §5. 특히 조심할 점 — RCS 를 '곱하기만' 하면 끝나는가?",
    "",
    f"### 5.1 이중 계산(double counting)",
    "",
    D.CAUTION_DOUBLE,
    "",
    f"$$ {D.CAUTION_DOUBLE_EQ} $$",
    "",
    "### 5.2 스칼라 RCS 만으론 위상이 없다",
    "",
    D.CAUTION_SCALAR,
))

# ── §6 패턴 ─────────────────────────────────────────────────────────────────
cells.append(md(
    "## §6. 문헌에서 드러난 핵심 패턴",
    "",
    *[f"**{t}** — {d}\n" for t, d in D.PATTERNS],
))

# ── §7 권장 구조(우리) ──────────────────────────────────────────────────────
cells.append(md(
    "## §7. 우리 드론 패시브 센싱에 적용할 권장 구조",
    "",
    "목표: Wi-Fi/LTE/5G illuminator 비교 · passive bistatic · 드론 탐지/추적 · Sionna 시뮬 · X410 sim-to-real. "
    "→ 가장 합리적인 구조:",
    "",
    "```",
    *D.RECOMMENDED_ARCH,
    "```",
    "",
    "**권장 표적 모델**",
    "",
    f"- {D.BODY_MODEL}",
    f"- {D.ROTOR_MODEL}",
))

# ── §8 연구 공백 + 우리 위치 ────────────────────────────────────────────────
cells.append(md(
    "## §8. 연구 공백과 우리 위치",
    "",
    f"{D.GAP_TARGET}",
    "",
    "**가장 가까운 문헌들 — 각각 일부만 해결**",
    "",
    *table(["가장 가까운 문헌", "해결한 부분", "빠진 부분"], D.GAP_NEAREST),
    "",
    f"> **우리(sionna2) 위치.** {D.OUR_POSITION}",
))

# ── §9 우선순위 + 한 문장 ───────────────────────────────────────────────────
cells.append(md(
    "## §9. 우선순위로 읽어야 할 논문",
    "",
    *[f"{i+1}. **{s}** — {why}" for i, (s, why) in enumerate(D.PRIORITY)],
    "",
    "---",
    "",
    f"> **한 문장 요약.** {D.ONE_LINER}",
))

write_nb(cells, "pw04_rcs_solution_by_target.ipynb", "pw04")
