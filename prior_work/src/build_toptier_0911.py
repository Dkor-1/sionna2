#!/usr/bin/env python
"""build_toptier_0911.py — **게재지를 정본으로** 하는 선행 연구 조사. ⛔웹만 읽는다.

■ 왜 다시 하나 (사용자 지적 2026-09-11)
  「선행 연구는 아카이브뿐만 아니라 **탑티어 논문**을 찾는 것을 주 목표로 해야 한다」
  ⇒ 09-11 의 첫 조사(`build_survey_0911.py`)는 arXiv 만 훑었다 — 조사 설계가 틀렸다.
    프리프린트는 «누가 무엇을 주장했나» 만 주고, 「게재됐나·어디에」는 안 준다.
  ⇒ 이 생성기는 **Crossref 를 ISSN 으로 조회**해 학술지별로 훑는다. 게재 사실·권·쪽·DOI 가
    응답에 들어 있으므로 «게재판이 있다» 를 지어낼 수 없다.

■ 탑티어 기준 — 저장소가 이미 정한 것을 따른다
  `prior_work/dl_toptier_anchors.md` 머리말(사용자 지시 2026-08-16):
    IEEE TAES·TGRS·TSP·JSTSP·Proc. IEEE / NeurIPS·ICML·ICLR·CVPR / JMLR·Patterns·Science·Nature
  여기에 **이 주제의 정본 학술지**를 더한다 — 안테나·전파(TAP·TMTT·OJAP), 통신(JSAC·TWC·TCOM·
  COMST), 레이다(IET RSN). ⛔더한 까닭을 VENUES 에 한 줄씩 적었다.
  ⭐**사용자 지시(2026-09-11)**: 「ICASSP · MobiCom · SIGCOMM · SenSys · MobiSys 등 계열도
    우리 목표 탑티어 계열로 봐 달라」 ⇒ CONFS 로 따로 훑는다.
    ⛔첫 판은 `type:journal-article` 로 걸러 **학회가 통째로 빠졌다** — 그 자리를 메운다.

■ ⛔이 생성기가 못 하는 것
  · Crossref 는 **학술지 위주**다. NeurIPS·CVPR·ICLR 같은 학회는 색인이 고르지 않다
    (그쪽은 `dl_toptier_anchors.md` 가 이미 원문 페이지로 확인해 두었다).
  · 초록이 Crossref 에 없는 편이 많다(IEEE 는 대체로 없다) — 제목·서지까지만 받는다.
  · ⛔따라서 이 원장은 «읽을 목록» 이지 «읽었다» 가 아니다.
  · ⛔실기 계측 대조는 이 저장소에 0 건이고 이 조사로도 생기지 않는다.

쓰는 법 (⛔CPU 전용):
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python prior_work/src/build_toptier_0911.py
"""
from __future__ import annotations
import json, os, re, time, urllib.parse, urllib.request

STORE = "/data/public/sionna_jeong/toptier_0911"
HAVE_ROOT = "/data/public/sionna_jeong"
SINCE = "2025-01-01"          # 소장본에 게재판이 거의 없어 두 해를 훑는다
MAILTO = "irslabpublic3@gmail.com"      # Crossref 예의 — 요청에 연락처를 적는다

#: (ISSN, 짧은 이름, 왜 이 학술지인가)
VENUES = [
    ("0018-926X", "IEEE TAP",    "안테나·전파의 정본. RCS·산란 계산이 여기 실린다"),
    ("0018-9251", "IEEE TAES",   "저장소가 정한 탑티어. 레이다 표적·추적"),
    ("0196-2892", "IEEE TGRS",   "저장소가 정한 탑티어. 원격탐사·산란"),
    ("1053-587X", "IEEE TSP",    "저장소가 정한 탑티어. 신호처리 정본"),
    ("1932-4553", "IEEE JSTSP",  "저장소가 정한 탑티어. 특집호로 ISAC 이 자주 실린다"),
    ("0018-9219", "Proc. IEEE",  "저장소가 정한 탑티어. 개관"),
    ("0733-8716", "IEEE JSAC",   "통신 정본. ISAC 특집의 주 무대"),
    ("1536-1276", "IEEE TWC",    "통신 정본"),
    ("0090-6778", "IEEE TCOM",   "통신 정본"),
    ("1553-877X", "IEEE COMST",  "서베이 정본 — 분야 지도를 여기서 받는다"),
    ("0018-9480", "IEEE TMTT",   "마이크로파. 계측·챔버 쪽 근거가 여기 있다"),
    ("2637-6431", "IEEE OJAP",   "안테나·전파 오픈. Ziganshin 게재판이 여기다"),
    ("1751-8784", "IET RSN",     "레이다 전용. 드론 마이크로도플러가 실리는 자리"),
    ("0018-9545", "IEEE TVT",    "차량·UAV 통신"),
    ("2327-4662", "IEEE IoT-J",  "저고도·센싱 응용이 많다"),
    ("1536-1233", "IEEE TMC",    "모바일 컴퓨팅 — 무선 센싱이 여기 실린다"),
    ("2041-1723", "Nature Comms","저장소가 정한 탑티어"),
    ("2045-2322", "Sci. Reports","Nature 계열"),
    ("2052-4463", "Sci. Data",   "Nature 계열 — 공개 데이터셋이 여기 실린다"),
]

#: 학회 — 시스템·모바일·신호처리 계열(사용자 지시 2026-09-11).
#: ⛔학회 논문집은 Crossref 에서 type 이 `proceedings-article` 이라 학술지 조회로는 안 걸린다.
#: ⛔ACM 논문집은 ISSN 이 없다 — DOI 앞자리(10.1145) + 논문집 이름으로 잡는다.
CONFS = [
    ("acm",  "MobiCom",  "Mobile Computing and Networking",
     "모바일·무선 센싱의 정본 학회 — 무선 센싱 실측이 여기 실린다"),
    ("acm",  "SenSys",   "Embedded Networked Sensor Systems",
     "센서 시스템 정본 — 실기 계측·배치가 여기 실린다"),
    ("acm",  "SIGCOMM",  "SIGCOMM",
     "네트워킹 정본"),
    ("acm",  "MobiSys",  "Mobile Systems, Applications and Services",
     "모바일 시스템 정본"),
    ("acm",  "IPSN",     "Information Processing in Sensor Networks",
     "센서망 신호처리 — 무선 센싱이 자주 실린다"),
    ("acm",  "HotMobile","Workshop on Mobile Computing Systems and Applications",
     "MobiCom 계열 — 초기 아이디어가 먼저 나온다"),
    #: ⛔IEEE 논문집은 ISSN 필터가 안 먹는다(실측 2026-09-11: ICASSP issn 조회 = 0 건).
    #  DOI 앞자리(10.1109) + 논문집 이름으로 잡아야 걸린다(ICASSP 7,901 · INFOCOM 1,438).
    ("ieee", "IEEE ICASSP", "ICASSP",
     "신호처리 정본 학회 — 사용자가 탑티어로 지정(2026-09-11)"),
    ("ieee", "IEEE INFOCOM", "INFOCOM",
     "네트워킹 정본 학회"),
    ("ieee", "IEEE RadarConf", "Radar Conference",
     "레이다 정본 학회 — 드론 마이크로도플러가 실제로 실리는 자리"),
    ("issn", "ACM IMWUT", "2474-9567",
     "UbiComp 정본지 — 무선 센싱 응용의 주 무대"),
]

#: 물음 축 — 저장소가 실제로 답하려는 것에 맞춘다
TOPICS = {
    "drone_rcs":      "drone UAV radar cross section",
    "microdoppler":   "micro-Doppler drone rotor blade",
    "isac_sensing":   "integrated sensing and communication",
    "raytracing":     "ray tracing channel sensing simulation",
    "passive_comms":  "passive radar communication signal illuminator",
    "sim2real":       "synthetic training data sim-to-real radar",
}

HI = [r"micro-?doppler", r"rotor", r"blade", r"radar cross.?section", r"\bRCS\b", r"\bUAV\b",
      r"drone", r"passive (radar|bistatic)", r"physical optics", r"ray.?trac", r"scatter"]


def crossref(params: dict) -> dict:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": f"sionna2-prior-survey/0911 (mailto:{MAILTO})"})
    for a in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=90).read())
        except Exception as e:                                   # noqa: BLE001
            if a == 3:
                raise
            print(f"    ⚠재시도 {a+1}/3 — {type(e).__name__}")
            time.sleep(5 * (a + 1))
    raise RuntimeError("unreachable")


def norm(it: dict, venue: str) -> dict:
    def first(k):
        v = it.get(k) or []
        return v[0] if v else None
    dt = it.get("published-print") or it.get("published-online") or it.get("created") or {}
    parts = (dt.get("date-parts") or [[None]])[0]
    return dict(
        doi=it.get("DOI"), venue=venue, container=first("container-title"),
        title=" ".join((first("title") or "").split()),
        published="-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts) if p),
        year=parts[0] if parts else None,
        authors=[f"{a.get('given','')} {a.get('family','')}".strip()
                 for a in (it.get("author") or [])][:6],
        volume=it.get("volume"), issue=it.get("issue"), page=it.get("page"),
        type=it.get("type"), url=f"https://doi.org/{it.get('DOI')}" if it.get("DOI") else None)


def main() -> int:
    os.makedirs(STORE, exist_ok=True)
    #: 소장본에 이미 있는 DOI — 파일명에는 DOI 가 거의 없으므로 제목 대조로도 본다
    have_titles = set()
    for root, _d, files in os.walk(HAVE_ROOT):
        for f in files:
            have_titles.add(re.sub(r"[^a-z0-9]+", "", os.path.splitext(f)[0].lower())[:60])

    rows: dict = {}
    SEL = ("DOI,title,container-title,author,volume,issue,page,"
           "published-print,published-online,created,type")

    def sweep(name: str, why: str, filt: str, extra: dict | None = None) -> int:
        n_v = 0
        for tkey, q in TOPICS.items():
            params = {"query.bibliographic": q, "rows": 60, "filter": filt,
                      "select": SEL, "sort": "published", "order": "desc"}
            params.update(extra or {})
            try:
                r = crossref(params)
            except Exception as e:                                # noqa: BLE001
                print(f"  ⛔{name}/{tkey} — {type(e).__name__}")
                continue
            for it in r.get("message", {}).get("items", []):
                d = norm(it, name)
                if not d["doi"] or not d["title"]:
                    continue
                if not any(re.search(p, d["title"].lower()) for p in HI):
                    continue                    # 물음과 먼 편은 담지 않는다
                rows.setdefault(d["doi"], dict(d, topics=[], venue_why=why))
                if tkey not in rows[d["doi"]]["topics"]:
                    rows[d["doi"]]["topics"].append(tkey); n_v += 1
            time.sleep(1.2)
        print(f"  {name:<20} {n_v:>3} 편")
        return n_v

    print("■ 학술지")
    for issn, name, why in VENUES:
        sweep(name, why, f"issn:{issn},from-pub-date:{SINCE},type:journal-article")

    print("■ 학회 (사용자 지시 — ICASSP·MobiCom·SIGCOMM·SenSys·MobiSys 계열)")
    for kind, name, key, why in CONFS:
        if kind == "acm":
            sweep(name, why, f"prefix:10.1145,from-pub-date:{SINCE},type:proceedings-article",
                  {"query.container-title": key})
        elif kind == "ieee":
            sweep(name, why, f"prefix:10.1109,from-pub-date:{SINCE},type:proceedings-article",
                  {"query.container-title": key})
        else:
            sweep(name, why, f"issn:{key},from-pub-date:{SINCE}")

    for d in rows.values():
        key = re.sub(r"[^a-z0-9]+", "", d["title"].lower())[:60]
        d["maybe_in_store"] = bool(key in have_titles)

    out = {"_meta": {
        "generator": "prior_work/src/build_toptier_0911.py",
        "made_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "why_ko": ("사용자 지적(2026-09-11) 「선행 연구는 아카이브뿐 아니라 탑티어 논문을 찾는 것이 "
                   "주 목표여야 한다」. 09-11 첫 조사가 arXiv 만 훑어 설계가 틀렸다. "
                   "이 생성기는 Crossref 를 ISSN 으로 조회해 **게재지별로** 훑는다."),
        "toptier_rule_ko": ("prior_work/dl_toptier_anchors.md 의 사용자 지시(2026-08-16) 기준을 "
                            "따르고, 이 주제의 정본 학술지(안테나·전파·레이다·통신)를 더했다. "
                            "더한 까닭은 각 행의 venue_why 에 적었다."),
        "since": SINCE, "venues": [{"issn": i, "name": n, "why_ko": w} for i, n, w in VENUES],
        "conferences": [{"kind": k, "name": n, "key": v, "why_ko": w} for k, n, v, w in CONFS],
        "topics": TOPICS, "n_rows": len(rows),
        "limits_ko": [
            "⛔NeurIPS·CVPR·ICLR 은 Crossref 색인이 고르지 않아 여기 안 잡힌다 — 그쪽은 "
            "prior_work/dl_toptier_anchors.md 가 이미 원문 페이지로 확인해 두었다.",
            "⚠ACM 학회는 ISSN 이 없어 DOI 앞자리(10.1145)+논문집 이름으로 잡았다 — 논문집 이름이 "
            "해마다 바뀌므로 빠짐이 있을 수 있다.",
            "⛔초록을 안 받았다(IEEE 는 Crossref 에 초록이 대체로 없다). 제목·서지까지다.",
            "⛔제목 낱말로 걸렀다 — 낱말이 없어도 관련 있을 수 있다.",
            "⛔«읽을 목록» 이지 «읽었다» 가 아니다. maybe_in_store 는 파일명 대조라 어림이다.",
            "⛔실기 계측 대조는 0 건이고 이 조사로도 생기지 않는다."]},
        "rows": sorted(rows.values(), key=lambda r: (r["published"] or ""), reverse=True)}
    with open(f"{STORE}/toptier_0911.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n■ 게재판 {len(rows)} 편 → {STORE}/toptier_0911.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
