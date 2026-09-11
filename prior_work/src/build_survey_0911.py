#!/usr/bin/env python
"""build_survey_0911.py — 선행 연구 공백 구간 조사 (2026-07-01 ~ 09-11). ⛔웹만 읽는다.

■ 왜
  소장본 `/data/public/sionna_jeong/` 은 **2026-08-11 에서 멈춰 있고** arXiv 번호는 2607 까지다
  (PDF 373 편 · 그 가운데 arXiv 번호가 파일명에 있는 것 202 편). 오늘이 09-11 이니 약 두 달
  공백이 있다. 이 생성기는 그 구간을 **arXiv API 로 체계적으로 훑어** 소장에 없는 것만 고른다.
  ⛔웹 검색만으로는 빠짐이 많아 API 목록 조회를 정본으로 쓴다(검색은 교차 확인용).

■ ⛔지어내지 않는다
  · 모든 편은 **arXiv API 응답**에서 제목·날짜·저자·초록·저널을 받아 적는다. 손으로 안 적는다.
  · 관련도 딱지는 **초록 낱말**로 매긴다(규칙은 AXES 에 있다) — 읽은 척하지 않는다.
  · 「우리 자리」 판정은 여기서 안 한다. 그것은 사람이 PDF 를 읽고 할 일이다.

■ 무엇을 내나
  · `/data/public/sionna_jeong/survey_0911/survey_0911.json`  — 원장(실재 검증 + 분류)
  · `/data/public/sionna_jeong/survey_0911/pdfs/`             — 관련도 상·중만 내려받는다
  · `INDEX.md` 는 사람이 쓴다(이 생성기는 원장까지).

쓰는 법 (⛔CPU 전용):
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python prior_work/src/build_survey_0911.py
"""
from __future__ import annotations
import json, os, re, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET

NS = {"a": "http://www.w3.org/2005/Atom"}
ARX = "{http://arxiv.org/schemas/atom}"
STORE = "/data/public/sionna_jeong/survey_0911"
HAVE_ROOT = "/data/public/sionna_jeong"
SINCE = "2026-07-01"            # 소장본이 멈춘 자리 바로 뒤부터

#: 훑는 축 — 저장소가 실제로 쓰는 물음에 맞춘다
QUERIES = {
    "drone_isac":      'all:"integrated sensing and communication" AND (all:UAV OR all:drone)',
    "microdoppler":    'all:"micro-Doppler" AND (all:drone OR all:UAV OR all:rotor)',
    "raytracing_isac": 'all:"ray tracing" AND (all:ISAC OR all:sensing) AND all:channel',
    "sionna":          'all:Sionna',
    "rcs_uav":         'all:"radar cross section" AND (all:UAV OR all:drone)',
    "passive_comms":   '(all:"passive radar" OR all:"passive bistatic") AND (all:5G OR all:LTE OR all:WiFi)',
    "sim2real":        '(all:"sim-to-real" OR all:"reality gap" OR all:"synthetic training") AND (all:radar OR all:wireless)',
}

#: 관련도 — **초록·제목의 낱말**로만 매긴다. 저장소의 물음에 가까운 순.
#: ⚠이것은 «읽어 보라» 는 분류지 «중요하다» 는 판정이 아니다.
HI = [r"micro-?doppler", r"rotor", r"blade", r"radar cross.?section", r"\bRCS\b",
      r"passive (radar|bistatic|sensing)", r"physical optics", r"scatter(ing|er)",
      r"sim-to-real", r"reality gap", r"sionna", r"ray.?trac"]
MID = [r"digital twin", r"channel model", r"3GPP", r"TR 38\.901", r"testbed",
       r"measurement", r"dataset", r"benchmark", r"O-RAN", r"calibrat"]
#: ⛔이 낱말만 있으면 우리 물음과 멀다 — 자원배분·궤적최적화 계열
LO = [r"resource allocation", r"trajectory optimiz", r"secrecy", r"beamforming design",
      r"energy (minimiz|efficien)", r"reinforcement learning", r"federated"]


def _api(params: dict) -> ET.Element:
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            return ET.fromstring(urllib.request.urlopen(url, timeout=90).read())
        except Exception as e:                                    # noqa: BLE001
            if attempt == 3:
                raise
            print(f"   ⚠재시도 {attempt+1}/3 — {type(e).__name__}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def entry(e: ET.Element) -> dict:
    def txt(tag, ns=NS):
        n = e.find(tag, ns) if ns else e.find(tag)
        return " ".join(n.text.split()) if n is not None and n.text else None
    aid = e.find("a:id", NS).text.rsplit("/", 1)[-1]
    return dict(
        arxiv_id=aid, base=aid.split("v")[0],
        title=txt("a:title"), published=e.find("a:published", NS).text[:10],
        updated=e.find("a:updated", NS).text[:10],
        authors=[a.find("a:name", NS).text for a in e.findall("a:author", NS)],
        primary=e.find(ARX + "primary_category").get("term"),
        summary=txt("a:summary"),
        comment=txt(ARX + "comment", None), doi=txt(ARX + "doi", None),
        journal_ref=txt(ARX + "journal_ref", None),
        pdf_url=f"https://arxiv.org/pdf/{aid}")


def grade(r: dict) -> tuple[str, list]:
    """초록 낱말로 관련도를 매긴다. ⛔읽고 판단한 것이 아니다."""
    blob = f"{r['title']} {r['summary']}".lower()
    hi = sorted({p for p in HI if re.search(p, blob)})
    mid = sorted({p for p in MID if re.search(p, blob)})
    lo = sorted({p for p in LO if re.search(p, blob)})
    if hi:
        return ("상", hi + mid)
    if mid and not lo:
        return ("중", mid)
    return ("하", lo or mid)


def have_arxiv_ids() -> set:
    """소장본 파일명에서 arXiv 번호를 뽑는다."""
    out = set()
    for root, _d, files in os.walk(HAVE_ROOT):
        if root.startswith(STORE):
            continue                       # 이번 조사분은 «소장» 으로 안 센다
        for f in files:
            for m in re.finditer(r"(?<!\d)(\d{4}\.\d{4,5})(?!\d)", f):
                out.add(m.group(1))
    return out


def main() -> int:
    os.makedirs(f"{STORE}/pdfs", exist_ok=True)
    have = have_arxiv_ids()
    print(f"■ 소장 arXiv 번호 {len(have)} 개 · 공백 구간 {SINCE} ~")

    rows: dict = {}
    for key, q in QUERIES.items():
        root = _api({"search_query": q, "start": 0, "max_results": 150,
                     "sortBy": "submittedDate", "sortOrder": "descending"})
        n = 0
        for e in root.findall("a:entry", NS):
            r = entry(e)
            if r["published"] < SINCE or r["base"] in have:
                continue
            rows.setdefault(r["base"], dict(r, axes=[]))
            rows[r["base"]]["axes"].append(key)
            n += 1
        print(f"  {key:<17} {n:>3} 편")
        time.sleep(3)

    for r in rows.values():
        r["relevance"], r["matched"] = grade(r)
    by = {g: [r for r in rows.values() if r["relevance"] == g] for g in ("상", "중", "하")}
    print(f"\n■ 소장에 없는 것 {len(rows)} 편 — 상 {len(by['상'])} · 중 {len(by['중'])} · 하 {len(by['하'])}")

    got, failed = [], []
    for r in sorted(by["상"] + by["중"], key=lambda x: x["published"], reverse=True):
        slug = re.sub(r"[^a-z0-9]+", "-", r["title"].lower())[:58].strip("-")
        p = f"{STORE}/pdfs/{r['base']}__{slug}.pdf"
        r["local_pdf"] = os.path.relpath(p, STORE)
        if os.path.exists(p) and os.path.getsize(p) > 20_000:
            got.append(r["base"]); continue
        try:
            req = urllib.request.Request(r["pdf_url"], headers={
                "User-Agent": "sionna2-prior-survey/0911 (research; contact via repo)"})
            data = urllib.request.urlopen(req, timeout=120).read()
            if not data.startswith(b"%PDF"):
                raise ValueError("PDF 가 아니다")
            with open(p, "wb") as f:
                f.write(data)
            got.append(r["base"]); print(f"  ↓ {r['base']}  {len(data)/1e6:.1f} MB")
            time.sleep(3)
        except Exception as e:                                    # noqa: BLE001
            failed.append(dict(base=r["base"], why=f"{type(e).__name__}: {e}"))
            r["local_pdf"] = None
            print(f"  ⛔{r['base']} — {type(e).__name__}")

    out = {"_meta": {
        "generator": "prior_work/src/build_survey_0911.py",
        "made_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "why_ko": ("소장본이 2026-08-11 에서 멈춰 있어 그 뒤 공백을 메운다. "
                   "arXiv API 목록 조회가 정본이고 웹 검색은 교차 확인용이다."),
        "since": SINCE, "queries": QUERIES,
        "n_have_arxiv_ids": len(have), "n_new": len(rows),
        "relevance_rule_ko": ("초록·제목 낱말로만 매긴다 — 상: 마이크로도플러·로터·RCS·패시브·"
                              "산란·광선추적·Sionna·sim-to-real 이 하나라도 있음 / "
                              "중: 트윈·채널모형·3GPP·실측·데이터셋 등만 있고 자원배분 계열 낱말이 없음 / "
                              "하: 그 밖. ⛔읽고 내린 판정이 아니다 — «열어 보라» 는 분류다."),
        "limits_ko": [
            "⛔arXiv 만 훑었다 — IEEE·MDPI·Nature 등 arXiv 에 없는 편은 이 원장에 없다.",
            "⛔초록 낱말 분류다. 낱말이 없어도 관련 있을 수 있고, 있어도 무관할 수 있다.",
            "⛔실기 계측 대조는 이 저장소에 0 건이고 이 조사로도 생기지 않는다.",
            "⚠검색어에 걸리지 않는 축(예: 기체 CAD·메쉬 충실도)은 안 훑었다."],
        "n_downloaded": len(got), "n_failed": len(failed), "failed": failed},
        "rows": sorted(rows.values(), key=lambda r: (r["relevance"] != "상",
                                                     r["relevance"] != "중",
                                                     r["published"]), reverse=False)}
    with open(f"{STORE}/survey_0911.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n  내려받음 {len(got)} · 실패 {len(failed)}")
    print(f"  원장 → {STORE}/survey_0911.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
