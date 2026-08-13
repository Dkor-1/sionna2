# -*- coding: utf-8 -*-
"""
report01_paper_facts.py — 리포트 01 의 **논문 참고자료용 파생 원장**  →  outputs/report01_paper.json
============================================================================================
계약서 두 장이 걸린다: `docs/REBUILD_2026-07-30.md` §5(서술) · `docs/PAPER_SPEC.md` §4(논문 규격).

이 파일이 만드는 것
    리포트 01 이 **논문 I. Introduction / II. Related Work 의 소스**가 되려면 세 가지가 더 필요하다.
      ① H8 을 **관문 단위로 집계한 수** — 네 관문을 동시에 통과한 편이 몇 편인가
      ② **논문 형식 인용 목록** — 저자·제목·지면·권·쪽·연도 + **게재상태**
      ③ **조달 카탈로그의 게재상태 열** — 갈래마다 게재본이 몇 편인가

    ①은 `outputs/prior_work_survey.json` 에 없다. 그 파일의 `funnel.*` 은 21편 전체에 G1~G4 를
    누적 적용한 다른 검사이고(모집단도 다르고 P1·P4 성분도 없다), H8 은 후보별 4관문 판정이다.
    두 수가 오늘 같은 값이라는 사실은 모집단의 우연이므로, 여기서 **관문 집계를 직접 센다**.

    ②의 제목은 PDF 1쪽의 가장 큰 글자에서 기계로 뽑고, 저자는 survey 의 `first_author` 를 쓰되
    `outputs/report01_citation_audit.json` P08 이 정정한 4건을 적용한다.

정산 원장(입력)
    outputs/prior_work_survey.json        — 21편 판정 · 갈래 · 낱말 빈도 · 앵커
    outputs/prior_settled_h8.json         — 후보 11편의 4관문 판정 + Rzewuski 관문표
    outputs/report01_citation_audit.json  — 인용 감사(P01 Hoydis 판 · P03 P1 규칙 · P08 저자명)

P1 규칙을 좁힌다 (인용 감사 P03)
    survey 의 P1 문구는 "본문에 명명된 지면 채택을 적은 원고는 포함한다" 인데, 실제 집계는
    Sagitta(ICCS 2026)·FWA cube(ICC Workshops 2026)를 프리프린트로 세었다. 여기서는 **적용된
    규칙 쪽으로** 문구를 맞춘다 — 지면 기록이 있는 프로시딩만 P1 통과, 본문 채택 문장은 `partial`.
    이 좁힘은 H8 판정을 바꾸지 않는다(Sagitta 는 P2·P3 에서, FWA cube 는 P2 에서 걸린다).

실행
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/report01_paper_facts.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

SURVEY = os.path.join(_ROOT, "outputs/prior_work_survey.json")
SETTLED = os.path.join(_ROOT, "outputs/prior_settled_h8.json")
AUDIT = os.path.join(_ROOT, "outputs/report01_citation_audit.json")
OUT = os.path.join(_ROOT, "outputs/report01_paper.json")

# --------------------------------------------------------------------------- #
#  0) 손으로 정하는 것 — 규약뿐이다. 값은 전부 위 세 JSON 과 PDF 에서 온다.
# --------------------------------------------------------------------------- #
#: 지면 이름을 인용에 쓸 정식 표기로. 근거는 survey `venue_en` + `locator`(PDF 메타 subject).
VENUE_FULL = {
    "EuCAP": "Proc. European Conf. Antennas and Propagation (EuCAP)",
    "IEEE WCL": "IEEE Wireless Communications Letters",
    "IEEE JSAC": "IEEE Journal on Selected Areas in Communications",
    "NATO STO": "NATO STO Meeting Proceedings STO-MP-MSG-SET-183, paper 13",
    "IEEE RadarConf": "Proc. IEEE Radar Conference (RadarConf)",
    "IEEE JSTEAP": "IEEE Journal on Sensing, Telecommunication and Emerging Applied Physics",
    "IEEE TWC": "IEEE Transactions on Wireless Communications",
    "IEEE ICCT": "Proc. IEEE Int. Conf. Communication Technology (ICCT)",
    "Proc. IEEE": "Proceedings of the IEEE",
    "IEEE TMLCN": "IEEE Transactions on Machine Learning in Communications and Networking",
    "arXiv": "arXiv preprint",
}

#: 인용 감사 P08 — survey 의 `first_author` 가 PDF 1쪽 저자줄과 어긋나는 4건.
AUTHOR_FIX = {
    "zhang": ("Y. Zhang et al.",
              "감사 P08: survey 는 'P. Zhang'(Das 편의 공저자)을 적었다. JSAC 1쪽 저자줄은 Yuxiang Zhang"),
    "lambda": ("L. Zhou et al.", "감사 P08: PDF 1쪽 저자줄 Lin Zhou 외 6인"),
    "openisac": ("Z. Zhou et al.", "감사 P08: PDF 1쪽 저자줄 Zhiwen Zhou 외 3인"),
    "sagitta": ("M. Pasquale et al.",
                "감사 P08: PDF 1쪽 저자줄 Marco Pasquale 외 4인 (SagittaSBR 은 소프트웨어 이름)"),
}

#: 인용 감사 P01 — Hoydis 는 게재본이 디스크에 있는데 survey 가 arXiv 판 PDF 를 가리킨다.
PDF_FIX = {
    "hoydis": ("/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/"
               "Learning_Radio_Environments_by_Differentiable_Ray_.pdf",
               "감사 P01: 게재본(12쪽 · PDF subject 가 IEEE TMLCN)을 인용 대상으로 삼는다"),
}

#: 본문에 지면 채택 문장을 적은 프리프린트 — 좁힌 P1 아래서 `partial` 이고 인용은 프리프린트다.
IN_BODY_ACCEPT = {
    "sagitta": "본문 p.1 에 ICCS 2026 채택 문장",
    "fwa_cube": "본문 p.1 에 IEEE ICC Workshops 2026 부분 채택 문장",
}

#: 같은 저작의 두 판 — 문서 수와 저작 수를 가르는 짝.
VERSION_PAIRS = [("costa_c", "costa_j"), ("zig_c", "zig_j")]

#: 좁힌 P1(감사 P03). survey 문구를 **집계가 실제로 적용한 쪽**으로 맞춘다.
PRONGS = [
    {"prong": "P1 게재",
     "test_ko": "지면 기록이 있는 프로시딩·저널에 실렸다. 본문에 지면 채택을 적은 arXiv 원고는 "
                "`일부` 로 세고 프리프린트로 남긴다"},
    {"prong": "P2 드론 메쉬",
     "test_ko": "표적이 기체의 3-D 표면 메쉬다. 큐브·점산란체·블레이드 1장·추상 복소계수는 제외한다"},
    {"prong": "P3 Sionna 계열 엔진",
     "test_ko": "산란전계를 미분가능 GPU 광선엔진 **안에서** 계산한다. FEKO·FDTD 로 낸 σ 를 "
                "경로에 곱하는 것은 주입이다"},
    {"prong": "P4 진폭 검증",
     "test_ko": "계산한 산란 **진폭**을 측정 또는 기준해와 맞댄다. 도플러 위치·회전주기·능선 모양 "
                "일치는 운동학이라 여기 못 든다"},
]

#: 정착 JSON 의 후보 문자열 → 표·그림에 쓸 짧은 이름(영어. 그림 글자는 영어다).
LABELS = [
    ("md-rt", "md-rt"),
    ("Clutter-Aware", "Clutter-Aware"),
    ("journal version", "Ziganshin jour."),
    ("conference version", "Ziganshin conf."),
    ("LAMBDA", "LAMBDA"),
    ("SagittaSBR", "SagittaSBR"),
    ("Great-X", "Great-X"),
    ("FWA cooperative", "FWA cube"),
    ("CellSense", "CellSense"),
    ("Temporal-GNN", "Temporal-GNN"),
    ("OpenISAC", "OpenISAC"),
]


# --------------------------------------------------------------------------- #
#  1) 관문 판정 정규화
# --------------------------------------------------------------------------- #
def grade(text: str) -> str:
    """정착 JSON 의 관문 문장을 `yes` · `partial` · `no` 로 정규화한다.

    `likely YES` · `not established` 처럼 근거가 문장 안에 미완인 것은 **`partial`** 이다 —
    좁힌 P1(본문 채택 문장은 지면 기록이 아니다)과 같은 처분을 받는다.
    """
    t = str(text).strip()
    head = t.split("-")[0].strip().lower()
    if head.startswith("yes"):
        return "yes"
    if head.startswith("no"):
        return "no"
    if head.startswith("partial"):
        return "partial"
    if head.startswith("likely") or head.startswith("not established"):
        return "partial"
    raise SystemExit(f"모르는 관문 판정이다: {t!r} — grade() 에 규칙을 추가하라")


def label_of(paper: str) -> str:
    for needle, short in LABELS:
        if needle.lower() in paper.lower():
            return short
    raise SystemExit(f"후보 이름에 짧은 라벨이 없다: {paper!r} — LABELS 에 추가하라")


def scorecard(settled: dict) -> list[dict]:
    """후보 12편(정착 11 + Rzewuski)의 4관문 표. Rzewuski 를 같은 모집단에 넣는다(감사 P04)."""
    rows: list[dict] = []
    for c in settled["h8_candidates"]:
        if "P1" not in c:              # 관문 판정이 없는 항목은 후보가 아니라 코퍼스 처분 기록이다
            continue
        g = {k: grade(c[k]) for k in ("P1", "P2", "P3", "P4")}
        rows.append({"label": label_of(c["paper"]), "paper": c["paper"],
                     "verdict_en": c.get("verdict", ""), **g,
                     "raw": {k: c[k] for k in ("P1", "P2", "P3", "P4")}})
    q1 = settled["H8"]["mandatory_qualification_1"]
    sc = q1["prong_scorecard"]
    g = {k: grade(sc[k]) for k in ("P1", "P2", "P3", "P4")}
    rows.append({"label": "Rzewuski", "paper": q1["counter_paper"],
                 "verdict_en": "does NOT refute H8; the engine prong is the whole gap",
                 **g, "raw": {k: sc[k] for k in ("P1", "P2", "P3", "P4")}})
    for r in rows:
        r["blocked_at"] = [k for k in ("P1", "P2", "P3", "P4") if r[k] != "yes"]
        r["first_block"] = r["blocked_at"][0] if r["blocked_at"] else None
        r["passes_all"] = not r["blocked_at"]
    rows.sort(key=lambda r: r["label"].lower())
    return rows


# --------------------------------------------------------------------------- #
#  2) 제목 — PDF 1쪽의 가장 큰 글자에서 기계로 뽑는다
# --------------------------------------------------------------------------- #
def pdf_title(pdf: str) -> str:
    """1쪽 위 42% 안에서 글자 크기가 큰 순으로 25자가 찰 때까지 모아 제목으로 삼는다.

    세로로 찍힌 arXiv 스탬프는 폭/높이 비로 걸러내고, IEEE 조판이 본문 첫 글자를 키운
    드롭캡(끝에 홀로 남는 대문자 한 글자)은 잘라낸다.
    """
    import fitz
    doc = fitz.open(pdf)
    try:
        page = doc[0]
        H = page.rect.height
        spans = []
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for sp in ln.get("spans", []):
                    t = " ".join(sp["text"].split())
                    x0, y0, x1, y1 = sp["bbox"]
                    if not t or "arXiv:" in t or y0 > 0.42 * H:
                        continue
                    if len(t) > 2 and (x1 - x0) < (y1 - y0) * 0.55:   # 세로 스탬프
                        continue
                    if len(t) <= 2 and (y1 - y0) > (x1 - x0) * 6:     # 세로 구두점
                        continue
                    spans.append((round(float(sp["size"]), 1), round(y0, 1), x0, t))
    finally:
        doc.close()
    by = defaultdict(list)
    for sz, y, x, t in spans:
        by[sz].append((y, x, t))
    picked: list[tuple] = []
    for sz in sorted(by, reverse=True):
        picked += by[sz]
        if len(" ".join(t for _, _, t in sorted(picked)).strip()) >= 25:
            break
    txt = " ".join(t for _, _, t in sorted(picked))
    txt = " ".join(txt.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("’", "'").split())
    txt = re.sub(r"\s+[A-Z]$", "", txt)                        # 드롭캡
    return txt


_VOL = re.compile(r"vol\.\s*(\d+)")
_PP = re.compile(r"pp\.\s*([\d]+)\s*[–\-]\s*([\d]+)")
_DOI = re.compile(r"DOI\s*(10\.[^\s,]+)")
_AX = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?)")


def citation(p: dict, audit_note: list[str]) -> dict:
    """논문 한 편을 **논문 형식 인용의 부품**으로 바꾼다 — 게재상태를 반드시 달고."""
    key = p["key"]
    loc = p.get("locator") or ""
    authors, a_note = p["first_author"], None
    if key in AUTHOR_FIX:
        authors, a_note = AUTHOR_FIX[key]
    elif not authors.endswith("et al."):
        authors = f"{authors} et al."
    pdf, p_note = p["pdf"], None
    if key in PDF_FIX:
        pdf, p_note = PDF_FIX[key]

    venue_key = re.sub(r"\s*\d{4}$", "", p["venue_en"]).strip()
    venue_key = re.sub(r"\s*\(.*\)$", "", venue_key).strip()
    venue = VENUE_FULL.get(venue_key, p["venue_en"])
    status = p["status"]
    note_bits = []
    if key in IN_BODY_ACCEPT:
        note_bits.append(IN_BODY_ACCEPT[key] + " · 좁힌 P1 아래서 프리프린트")
    if a_note:
        note_bits.append(a_note)
    if p_note:
        note_bits.append(p_note)

    m = _PP.search(loc)
    out = {
        "n": None, "key": key, "short_ko": p["short_ko"], "authors": authors,
        "title": pdf_title(pdf), "venue": venue, "year": p["year"],
        "volume": (_VOL.search(loc).group(1) if _VOL.search(loc) else None),
        "pages": (f"{m.group(1)}-{m.group(2)}" if m else None),
        "doi": (_DOI.search(loc).group(1) if _DOI.search(loc) else None),
        "arxiv": (_AX.search(loc).group(1) if _AX.search(loc) else None),
        "status": status, "status_ko": p["status_ko"],
        "route": p["route"], "route_tag": p["route_tag"],
        "venue_evidence": p.get("venue_evidence"),
        "pdf": pdf, "title_source": "PDF 1쪽 최대 글자 (PyMuPDF)",
        "note": " · ".join(note_bits) or None,
    }
    if status == "preprint" and not out["arxiv"]:
        raise SystemExit(f"{key}: 프리프린트인데 arXiv ID 를 못 뽑았다 — locator={loc!r}")
    if a_note or p_note:
        audit_note.append(f"{key}: " + " / ".join(x for x in (a_note, p_note) if x))
    return out


# --------------------------------------------------------------------------- #
def build() -> dict:
    S = json.load(open(SURVEY, encoding="utf-8"))
    H = json.load(open(SETTLED, encoding="utf-8"))
    A = json.load(open(AUDIT, encoding="utf-8"))

    rows = scorecard(H)
    n_pass = sum(1 for r in rows if r["passes_all"])
    blocked = defaultdict(int)
    for r in rows:
        if r["first_block"]:
            blocked[r["first_block"]] += 1

    audit_note: list[str] = []
    cites = [citation(p, audit_note) for p in S["papers"]]
    for i, c in enumerate(cites, 1):
        c["n"] = i

    pairs = [[a, b] for a, b in VERSION_PAIRS]
    n_docs = len(S["papers"])
    n_works = n_docs - len(pairs)

    by_route = defaultdict(lambda: {"papers": 0, "published": 0})
    for c in cites:
        by_route[c["route"]]["papers"] += 1
        by_route[c["route"]]["published"] += int(c["status"] == "published")

    return {
        "meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "producer": "src/report01_paper_facts.py",
            "purpose": "리포트 01 → 논문 I. Introduction / II. Related Work 파생 원장",
            "inputs": ["outputs/prior_work_survey.json", "outputs/prior_settled_h8.json",
                       "outputs/report01_citation_audit.json"],
            "rule": "값은 입력 JSON 과 PDF 원문에서만 온다. 이 파일이 새로 정하는 것은 규약뿐이다.",
            "audit_fixes_applied": audit_note,
            "audit_items_consumed": ["P01 Hoydis 판", "P02 관문 집계", "P03 P1 규칙",
                                     "P04 Rzewuski 를 같은 모집단에", "P08 저자명"],
        },
        "corpus": {
            "documents": n_docs,
            "distinct_works": n_works,
            "version_pairs": pairs,
            "version_pairs_ko": "Costa 와 Ziganshin 은 회의판·저널판을 따로 센다 — "
                                "판마다 게재상태와 보고량이 다르다",
            "corpus_swept_pdfs": S["meta"]["corpus_swept_pdfs"],
        },
        "h8": {
            "claim_ko": H["H8"]["claim_as_stated"],
            "prongs": PRONGS,
            "p1_rule_ko": PRONGS[0]["test_ko"],
            "n_adjudicated": len(rows),
            "n_passing_all_prongs": n_pass,
            "blocked_at_counts": dict(blocked),
            "scorecard": rows,
            "q1_counter_paper": H["H8"]["mandatory_qualification_1"]["counter_paper"],
            "q1_why_ko": S["h8"]["qualification_1"]["text_ko"],
            "q2_why_ko": S["h8"]["qualification_2"]["text_ko"],
            "rzewuski_venue_note_ko": "NATO STO 회의 프로시딩 수록본이다. 이 처분은 우리 신규성을 "
                                      "좁히는 쪽이라 보수적이다",
        },
        "route_status": {k: dict(v, label_ko=S["routes"][k]["label_ko"],
                                 bought_ko=S["routes"][k]["bought_ko"])
                         for k, v in sorted(by_route.items())},
        "citations": cites,
        "anchor_provenance": {
            "das_slope_db_per_ghz": S["anchors"]["das"]["mu_a_db_per_ghz"],
            "das_data_origin_ko": "Das 는 Phantom 3 를 직접 재지 않았다 — 원 측정은 참고문헌 [7]"
                                  "(Wang 외, China Commun., 2025)이고 Das 는 그것을 다시 적합했다",
            "das_data_origin_evidence": "outputs/report01_citation_audit.json : problems[4] (P05)",
            "what_we_use_ko": "기울기 하나. 절대 레벨은 세 밴드 공통이라 파형 순위에서 상쇄된다",
        },
        "audit_summary": {
            "pdfs_opened": A["meta"]["pdfs_opened"],
            "quote_records_re_verified": A["meta"]["quote_records_re_verified"],
            "quote_records_failing": A["meta"]["quote_records_failing"],
        },
    }


def main() -> int:
    D = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1)
    print(f"── 리포트 01 논문 원장 ──")
    print(f"  문서 {D['corpus']['documents']}건 · 저작 {D['corpus']['distinct_works']}편")
    print(f"  H8 후보 {D['h8']['n_adjudicated']}편 · 4관문 동시 통과 "
          f"{D['h8']['n_passing_all_prongs']}편 · 첫 탈락 관문 {D['h8']['blocked_at_counts']}")
    print(f"  인용 {len(D['citations'])}건 (게재 "
          f"{sum(1 for c in D['citations'] if c['status'] == 'published')}건)")
    for x in D["meta"]["audit_fixes_applied"]:
        print(f"  · 감사 반영 — {x}")
    print(f"✅ {os.path.relpath(OUT, _ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
