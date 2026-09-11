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

#: ⭐⭐**게재지 층**(2026-09-11(3) 사용자 지적 ⓒ) — 「탑티어 조사」인데 Access 가 가장 많으면
#: 이름이 무색해진다. 층을 나눠 적고, 원장·문서가 층을 함께 싣는다.
#:   정본 — 저장소가 정한 탑티어(dl_toptier_anchors.md) + 이 주제의 정본 학술지·학회
#:   일반 — 분야의 정식 게재지이지만 탑티어로 세지 않는다(양이 많아 따로 본다)
TIER_CORE = {
    "IEEE TAP", "IEEE TAES", "IEEE TGRS", "IEEE TSP", "IEEE JSTSP", "Proc. IEEE",
    "IEEE JSAC", "IEEE TWC", "IEEE TCOM", "IEEE COMST", "IEEE TMTT", "IEEE OJAP",
    "IET RSN", "IEEE TRS", "IEEE WCL", "IEEE TMC", "Nature Comms", "Sci. Data",
    "MobiCom", "SenSys", "SIGCOMM", "MobiSys", "IPSN", "HotMobile",
    "IEEE ICASSP", "IEEE INFOCOM", "ACM IMWUT", "IEEE RadarConf", "EuCAP",
}


def tier_of(venue: str) -> str:
    return "정본" if venue in TIER_CORE else "일반"


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
    #: ⛔2026-09-11 재현율 시험에서 **저장소가 이미 아는 편 3 종이 안 걸렸다** — 그 학술지가
    #  목록에 아예 없어서였다. Das/Yuan(WCL) · Semkin(Access) · Sun LIPASE(OJ-COMS).
    ("2162-2337", "IEEE WCL",     "무선 레터 — Das/Yuan 의 드론 σ 계측 앵커가 여기 실렸다"),
    ("2644-125X", "IEEE OJ-COMS", "통신 오픈 — LIPASE(패시브 LTE 드론 공개셋)가 여기다"),
    ("2169-3536", "IEEE Access",  "Semkin 의 드론 RCS 계측이 여기다. 양이 많아 제목 거르기가 더 중요"),
    ("1530-437X", "IEEE Sensors J", "센서 — 드론 검출 응용이 많다"),
    ("0018-9456", "IEEE TIM",     "계측 정본 — 챔버·계측 절차 근거"),
    ("2832-7357", "IEEE TRS",     "IEEE Trans. Radar Systems(신설) — 레이다 전용 정본"),
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
    ("ieee", "IEEE RadarConf", "RadarConf IEEE Radar Conference",
     "레이다 정본 학회 — 드론 마이크로도플러가 실제로 실리는 자리"),
    ("ieee", "EuCAP", "EuCAP European Conference on Antennas and Propagation",
     "안테나·전파 정본 학회 — Yuan 의 드론 σ 계측이 여기 실렸다"),
    ("issn", "ACM IMWUT", "2474-9567",
     "UbiComp 정본지 — 무선 센싱 응용의 주 무대"),
]

#: ⭐⭐**닻 — 저장소가 이미 아는 편.** 조사가 이것들을 도로 찾아오는지가 재현율이다.
#  ⛔⛔2026-09-12 정정 — 전에는 이 목록이 **어디에도 없었다.** INDEX 가 「재현율 4/6」
#    이라고 적어 놨는데 그 여섯이 무엇인지 적힌 자리가 없고, 검사하는 코드도 없었다.
#    ⛔실측(2026-09-12): 그 여섯을 이름·DOI 로 원장에서 찾아보니 **0/6** 이다. 「4/6」은
#      재현할 수 없는 수였다. ⇒ 목록을 코드에 박고 **굽을 때마다 검사해 원장에 적는다.**
ANCHORS = [
    ("Zhang JSAC «Typical Targets»", "10.1109/jsac.2025.3608732",
     "3GPP ISAC 표준화용 표적 RCS 모형 — 우리와 가장 가까운 축"),
    ("Khawaja/Semkin COMST 조사", "10.1109/comst.2025.3554613",
     "UAV 전파 채널 조사. ⚠IEEE 가 제목에서 UAV 를 AAV 로 고쳐 실었다"),
    ("Ziganshin EuCAP «Curved Bodies»", "10.23919/eucap63536.2025.10999367",
     "곡면체 RCS — 동체 근사의 대조군"),
    ("Sun OJ-COMS LIPASE", "", "패시브 센싱 — 제목 낱말이 우리와 다르다"),
    ("Semkin IEEE Access 드론 σ 계측", "", "실측 σ — 우리에게 없는 축"),
    ("Das/Yuan WCL", "", "드론 마이크로도플러"),
]


def check_anchors(rows: dict) -> list[dict]:
    """닻이 원장에 들어왔는지 본다. ⛔못 찾은 것을 «없는 셈» 치지 않는다 — 원장에 적는다."""
    got = []
    for nm, doi, why in ANCHORS:
        hit = None
        if doi:
            hit = rows.get(doi.lower()) or next(
                (r for k, r in rows.items() if k.lower() == doi.lower()), None)
        if hit is None:
            key = re.sub(r"[^a-z0-9]+", "", nm.split("«")[-1].strip("»").lower())
            if key:
                hit = next((r for r in rows.values()
                            if key and key in re.sub(r"[^a-z0-9]+", "", r["title"].lower())), None)
        got.append(dict(name=nm, doi=doi or None, why_ko=why,
                        found=hit is not None,
                        found_as=(hit or {}).get("title"),
                        found_venue=(hit or {}).get("venue")))
    return got


#: 물음 축 — 저장소가 실제로 답하려는 것에 맞춘다
TOPICS = {
    "drone_rcs":      "drone UAV radar cross section",
    "microdoppler":   "micro-Doppler drone rotor blade",
    "isac_sensing":   "integrated sensing and communication",
    "raytracing":     "ray tracing channel sensing simulation",
    "passive_comms":  "passive radar communication signal illuminator",
    "sim2real":       "synthetic training data sim-to-real radar",
}

#: 제목 거르기 — ⛔2026-09-11 정밀도 시험에서 **14 %(52/366)가 제어·비전·점검**이었다
#: (「Mars Helicopter 로터 공력설계」가 걸렸다). 「드론이 나온다」만으로는 부족하다.
#: ⇒ **표적·물음 낱말(TARGET)** 과 **전파·레이다 낱말(SENSE)** 이 **둘 다** 있어야 담는다.
TARGET = [r"micro-?doppler", r"rotor", r"blade", r"\bUAV\b", r"drone", r"unmanned aerial",
          r"quadcopter", r"multirotor", r"\bsUAS\b"]
SENSE  = [r"radar", r"doppler", r"scatter", r"\bRCS\b", r"radar cross.?section", r"sensing",
          r"\bISAC\b", r"passive (radar|bistatic)", r"ray.?trac", r"physical optics",
          r"electromagnetic", r"propagat", r"channel", r"antenna", r"backscatter",
          r"millimeter.?wave", r"\bmmWave\b", r"spectrogram", r"clutter"]
#: ⛔이 낱말만 있으면 우리 물음이 아니다 — 비행제어·영상·구조점검 계열
OFFTOPIC = [r"flight control", r"trajectory", r"formation control", r"aerodynam", r"thrust",
            r"path plan", r"\bPID\b", r"fault diagnos", r"defect", r"crack", r"inspect",
            r"imagery", r"photogramm", r"segmentation", r"waste", r"crop", r"soil moisture",
            r"light pollution", r"edge computing", r"video streaming",
            #: ⛔⛔2026-09-12 — 원장에 **제목이 광학·영상인 편이 35 편** 들어와 있었다
            #  (SODA-Net·SDS-YOLO·HazyDet·CODrone·RGB-T…). 두 군데가 열려 있었다:
            #    ⓐ SENSE 에 `detect` 가 있어 「드론 + 객체검출」이면 다 통과했다
            #      ⇒ 뺐다. 진짜 레이다 편은 radar·sensing·doppler 로 이미 걸린다.
            #    ⓑ OFFTOPIC 에 `imagery` 는 있는데 `images` · `optical` · `YOLO` 가 없었다.
            r"\bimages?\b", r"\boptical\b", r"\bYOLO\b", r"\bRGB\b", r"\bvisual\b",
            r"\bcamera\b", r"object detection", r"semantic", r"image.?domain",
            r"\bvision\b", r"super.?resolution image"]


#: ⛔⛔2026-09-11(2) — TARGET(드론 낱말)을 **반드시** 요구했더니 저장소가 아는 편 셋이 떨어졌다
#: (Ziganshin «Curved Bodies» · Zhang «Typical Targets» · Clutter-Aware ISAC — 제목에 드론이 없다).
#: ⇒ 이 낱말이 제목에 있으면 드론 낱말이 없어도 담는다. 우리 물음의 **핵심 물리**다.
CORE = [r"radar cross.?section", r"\bRCS\b", r"micro-?doppler", r"physical optics",
        r"\bSBR\b", r"shooting and bouncing", r"scattering (model|center|centre|coefficient)",
        r"ISAC channel", r"sensing channel", r"target channel"]


#: ⛔⛔2026-09-12 정정 — **대문자가 든 패턴이 전부 죽어 있었다.**
#  옛 코드는 `b = t.lower()` 로 제목을 소문자로 바꾼 뒤 `re.search(p, b)` 를 **re.I 없이**
#  돌렸다. 그래서 패턴에 대문자가 하나라도 있으면 영원히 안 맞는다:
#      TARGET  \bUAV\b · \bsUAS\b
#      SENSE   \bRCS\b · \bISAC\b · \bmmWave\b
#      CORE    \bRCS\b · \bSBR\b · ISAC channel
#      OFFTOPIC \bPID\b
#  곧 **이 주제의 핵심 약어 아홉 개가 죽은 코드**였다.
#  ⛔실측(2026-09-12): 「A Unified RCS Modeling of Typical Targets for 3GPP ISAC Channel
#    Standardization」(Zhang, JSAC 2025)이 **버려진다**. re.I 를 넣으면 담긴다.
#    INDEX 는 이것을 「제목에 우리 낱말이 없다 — 제목·초록 검색의 한계」로 적어 놨는데,
#    한계가 아니라 **버그**였다. 진단이 반대 방향으로 닫혀 있었다.
#  ⇒ 이제 **원문 제목에 re.I 로** 찾는다. 소문자 사본은 안 쓴다.
#: ⭐복수형도 받는다 — \bUAV\b 는 "UAVs" 를 못 맞춘다. IEEE 가 UAV 를 AAV 로 고쳐 실은
#  편도 있다(Khawaja COMST 2025).
TARGET = TARGET + [r"\bUAVs\b", r"\bAAVs?\b", r"\bUAS\b"]

#: ⭐**전파·레이다 «좁은» 낱말** — 모바일·네트워킹 정본 학회용.
#  그 학회 논문은 제목에 «drone» 을 거의 안 적는다(사람·손동작·눈을 잰다). 그렇다고 SENSE
#  전부를 허용하면 «channel»·«detect»·«propagat» 때문에 네트워킹 논문이 쏟아진다.
#  ⇒ 그 자리에서는 **RF 낱말 하나**를 요구한다.
RF_SENSE = [r"radar", r"micro-?doppler", r"\bdoppler\b", r"backscatter", r"\bmmWave\b",
            r"millimeter.?wave", r"\bRCS\b", r"radar cross.?section", r"\bISAC\b",
            r"integrated sensing", r"wireless sensing", r"\bRF\b.{0,12}sens",
            r"ray.?trac", r"physical optics", r"scatter", r"spectrogram", r"\bWi-?Fi sens"]

#: 위 RF 낱말 하나로 담아 주는 게재지 — 사용자가 탑티어로 지목한 계열이다(2026-09-11).
#  ⛔여기 없는 게재지에는 안 쓴다. 레이다 학술지에 이 규칙을 쓰면 드론과 무관한 편이 쏟아진다.
SYSTEMS_VENUES = {"MobiCom", "SenSys", "SIGCOMM", "MobiSys", "IPSN", "HotMobile",
                  "ACM IMWUT", "IEEE ICASSP", "IEEE INFOCOM"}


def title_ok(t: str, venue: str | None = None) -> bool:
    """제목만 보고 «우리 물음인가» 를 가른다. ⭐원문에 re.I 로 찾는다(소문자 사본 안 쓴다)."""
    def has(pats):
        return any(re.search(p, t, re.I) for p in pats)
    #: ⭐모바일·신호처리 정본 학회 — RF 낱말 하나면 담는다(드론 낱말을 요구하지 않는다)
    if venue in SYSTEMS_VENUES:
        if not has(RF_SENSE):
            return False
        if has(OFFTOPIC) and not has([r"radar", r"doppler", r"scatter", r"\bRCS\b",
                                      r"backscatter", r"\bmmWave\b"]):
            return False
        return True
    if has(CORE):
        return True                       # 핵심 물리 낱말은 그 자체로 우리 물음이다
    if not has(TARGET):
        return False
    if not has(SENSE):
        return False
    #: 전파 낱말이 있어도 제목이 통째로 제어·비전이면 뺀다
    if has(OFFTOPIC) and not has([r"radar", r"doppler", r"scatter", r"\bRCS\b", r"sensing"]):
        return False
    return True


#: ⭐⭐**둘째 채널 — OpenAlex**(2026-09-11(3) 사용자 지적 ⓑ).
#: Crossref 는 **제목**으로만 걸러야 해서, 제목에 우리 낱말이 없는 편을 놓쳤다
#: (실측: Zhang «Unified RCS Modeling of **Typical Targets**» · Clutter-Aware ISAC).
#: OpenAlex 는 `search=` 가 **제목+초록**을 보므로 그 구멍을 메운다.
#: ⛔학회는 OpenAlex 에서 source 가 **연도별로 쪼개져** 있어 ID 필터를 못 쓴다(실측) —
#:   그래서 학회는 Crossref 채널이 맡고, OpenAlex 는 게재지 이름을 되짚어 고른다.
OA_TOPICS = {
    "drone_rcs":      'drone UAV "radar cross section"',
    "microdoppler":   '"micro-Doppler" drone rotor blade',
    "raytracing":     '"ray tracing" ISAC sensing channel',
    "rcs_model":      '"RCS modeling" ISAC channel target',
    "passive_comms":  '"passive radar" 5G LTE illuminator drone',
    "sim2real":       '"sim-to-real" OR "reality gap" radar synthetic training',
}
#: 돌려받은 게재지 이름이 우리 목록의 어느 자리인가 — OpenAlex 는 이름이 길게 온다
OA_VENUE = [
    (r"transactions on antennas and propagation", "IEEE TAP"),
    (r"transactions on aerospace and electronic", "IEEE TAES"),
    (r"transactions on geoscience and remote", "IEEE TGRS"),
    (r"transactions on signal processing", "IEEE TSP"),
    (r"journal of selected topics in signal", "IEEE JSTSP"),
    (r"proceedings of the ieee\b", "Proc. IEEE"),
    (r"journal on selected areas in communications", "IEEE JSAC"),
    (r"transactions on wireless communications", "IEEE TWC"),
    (r"transactions on communications", "IEEE TCOM"),
    (r"communications surveys", "IEEE COMST"),
    (r"microwave theory and tech", "IEEE TMTT"),
    (r"open journal of antennas", "IEEE OJAP"),
    (r"radar, sonar|radar sonar", "IET RSN"),
    (r"transactions on radar systems", "IEEE TRS"),
    (r"wireless communications letters", "IEEE WCL"),
    (r"transactions on mobile computing", "IEEE TMC"),
    (r"nature communications", "Nature Comms"),
    (r"scientific data", "Sci. Data"),
    (r"scientific reports", "Sci. Reports"),
    (r"ieee access", "IEEE Access"),
    (r"sensors journal", "IEEE Sensors J"),
    (r"internet of things journal", "IEEE IoT-J"),
    (r"instrumentation and measurement", "IEEE TIM"),
    (r"vehicular technology", "IEEE TVT"),
    (r"open journal of the communications", "IEEE OJ-COMS"),
    (r"antennas and propagation \(eucap\)|european conference on antennas", "EuCAP"),
    (r"radar conference|radarconf", "IEEE RadarConf"),
    (r"acoustics, speech|icassp", "IEEE ICASSP"),
    (r"mobile computing and networking|mobicom", "MobiCom"),
    (r"embedded networked sensor|sensys", "SenSys"),
    (r"infocom", "IEEE INFOCOM"),
]


def openalex(params: dict) -> dict:
    params = dict(params, mailto=MAILTO)
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": f"sionna2-prior-survey/0911 (mailto:{MAILTO})"})
    for a in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=90).read())
        except Exception as e:                                   # noqa: BLE001
            if a == 3:
                raise
            print(f"    ⚠OpenAlex 재시도 {a+1}/3 — {type(e).__name__}")
            time.sleep(5 * (a + 1))
    raise RuntimeError("unreachable")


def oa_venue(name: str | None) -> str | None:
    if not name:
        return None
    low = name.lower()
    for pat, short in OA_VENUE:
        if re.search(pat, low):
            return short
    return None


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


#: 돌려받은 container-title 이 노린 게재지가 맞는지 보는 낱말. ⛔퍼지 매칭이 엉뚱한 논문집을
#: 물어 온다 — 실측 2026-09-11: "Radar Conference" 로 조회했더니 MMAR(자동화·로보틱스 학회)
#: 논문이 «IEEE RadarConf» 로 찍혔다. 그래서 이름을 되짚어 거른다.
VENUE_GUARD = {
    "MobiCom":   r"mobile computing and networking",
    "SenSys":    r"embedded networked sensor",
    "SIGCOMM":   r"sigcomm",
    "MobiSys":   r"mobile systems, applications",
    "IPSN":      r"information processing in sensor networks",
    "HotMobile": r"mobile computing systems and applications",
    "IEEE ICASSP":   r"icassp|acoustics, speech",
    "IEEE INFOCOM":  r"infocom",
    "IEEE RadarConf": r"radar conference",
    "EuCAP":     r"antennas and propagation \(eucap\)|european conference on antennas",
    "ACM IMWUT": r"interactive, mobile, wearable",
}


def venue_ok(name: str, container: str | None) -> bool:
    pat = VENUE_GUARD.get(name)
    if not pat:
        return True                      # ISSN 으로 잡은 학술지는 되짚을 필요가 없다
    return bool(container and re.search(pat, container, re.I))


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


def fetch_abstracts(rows: dict, limit: int | None = None) -> dict:
    """OpenAlex 에서 DOI 로 초록을 받아 채운다.

    ⛔⛔2026-09-12 정정 — 원장 275 행에 **초록이 한 줄도 없었다**(`abstract` 열쇠 자체가
    없었다). 그런데 INDEX 는 「초록을 다 못 읽었다」고만 적어 «일부는 읽었다» 로 읽혔다.
    제목과 서지만 보고 내린 판정이었다. ⇒ 받아서 원장에 싣는다.

    OpenAlex 는 초록을 `abstract_inverted_index`(낱말 → 자리 목록)로 준다. 되돌려 붙인다.
    ⚠저작권 때문에 안 주는 편이 있다 — 그 행은 abstract=None 으로 남고, 그 사실을
      `n_abstract` 로 센다. ⛔없는 것을 «못 읽었다» 가 아니라 «없다» 로 적는다.
    """
    dois = [d for d in rows if rows[d].get("abstract") is None]
    if limit:
        dois = dois[:limit]
    got = 0
    for i in range(0, len(dois), 40):
        chunk = dois[i:i + 40]
        try:
            r = openalex({"filter": "doi:" + "|".join(f"https://doi.org/{d}" for d in chunk),
                          "per-page": 50,
                          "select": "doi,abstract_inverted_index"})
        except Exception as e:                                     # noqa: BLE001
            print(f"  ⛔초록 {i}-{i+len(chunk)} — {type(e).__name__}"); time.sleep(2); continue
        for w in r.get("results", []):
            inv = w.get("abstract_inverted_index")
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            if not inv or doi not in rows:
                continue
            pos = {}
            for word, idxs in inv.items():
                for j in idxs:
                    pos[j] = word
            rows[doi]["abstract"] = " ".join(pos[k] for k in sorted(pos))[:4000]
            got += 1
        time.sleep(0.4)
        print(f"  초록 {min(i+40, len(dois))}/{len(dois)} 조회 · 받은 것 {got}", flush=True)
    return dict(asked=len(dois), got=got)


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

    #: ⭐2026-09-11(3) — ⓐ쪽 수를 5 → 20 으로 늘리고, **가드를 통과하는 것이 없는 쪽이
    #: 두 번 이어지면** 멈춘다. 전에는 5 쪽에서 끊겨 「더 있을 수 있다」 경고가 95 건이었다.
    PAGE, MAX_PAGES, DRY_STOP = 100, 20, 2

    def sweep(name: str, why: str, filt: str, extra: dict | None = None,
              venue_hint: str | None = None) -> int:
        n_v, n_guard = 0, 0
        for tkey, q in TOPICS.items():
            dry = 0
            for page in range(MAX_PAGES):
                #: 학회는 이름을 **주제어에 섞는다**(container-title 퍼지 매칭은 못 쓴다)
                _q = f"{q} {venue_hint}" if venue_hint else q
                params = {"query.bibliographic": _q, "rows": PAGE, "offset": page * PAGE,
                          "filter": filt, "select": SEL, "sort": "relevance" if venue_hint else "published",
                          "order": "desc"}
                params.update(extra or {})
                try:
                    r = crossref(params)
                except Exception as e:                            # noqa: BLE001
                    print(f"  ⛔{name}/{tkey} p{page} — {type(e).__name__}")
                    break
                items = r.get("message", {}).get("items", [])
                _kept_here = 0
                for it in items:
                    d = norm(it, name)
                    if not d["doi"] or not d["title"]:
                        continue
                    if not venue_ok(name, d["container"]):
                        n_guard += 1              # 엉뚱한 논문집 — 딱지를 붙이지 않는다
                        continue
                    if not title_ok(d["title"], name):
                        continue
                    rows.setdefault(d["doi"], dict(d, topics=[], venue_why=why,
                                                   tier=tier_of(name), channel="crossref"))
                    if tkey not in rows[d["doi"]]["topics"]:
                        rows[d["doi"]]["topics"].append(tkey); n_v += 1
                    _kept_here += 1
                time.sleep(1.0)
                dry = dry + 1 if _kept_here == 0 else 0
                if len(items) < PAGE or dry >= DRY_STOP:
                    break
            else:
                print(f"    ⚠{name}/{tkey} — {MAX_PAGES} 쪽을 다 썼다. 더 있을 수 있다")
        print(f"  {name:<20} {n_v:>3} 편" + (f"   (딴 논문집 {n_guard} 건 걸러냄)" if n_guard else ""))
        return n_v

    print("■ 학술지")
    for issn, name, why in VENUES:
        sweep(name, why, f"issn:{issn},from-pub-date:{SINCE},type:journal-article")

    #: ⭐둘째 채널 — 제목에 우리 낱말이 없어도 **초록**에 있으면 잡는다
    print("■ OpenAlex (초록까지 검색 · 게재지 이름을 되짚어 고른다)")
    n_oa, n_oa_new = 0, 0
    for tkey, q in OA_TOPICS.items():
        cursor = "*"
        for _page in range(8):
            try:
                r = openalex({"search": q, "per-page": 100, "cursor": cursor,
                              "filter": f"from_publication_date:{SINCE},type:article|review",
                              "select": ("id,doi,title,publication_year,publication_date,"
                                         "primary_location,authorships,type")})
            except Exception as e:                                # noqa: BLE001
                print(f"  ⛔OpenAlex/{tkey} — {type(e).__name__}")
                break
            res = r.get("results", [])
            for w in res:
                src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
                v = oa_venue(src)
                if not v:
                    continue                     # 우리 목록 밖 게재지
                doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
                t = " ".join((w.get("title") or "").split())
                if not doi or not t or not title_ok(t):
                    continue
                n_oa += 1
                if doi not in rows:
                    n_oa_new += 1
                    rows[doi] = dict(
                        doi=doi, venue=v, container=src, title=t,
                        published=w.get("publication_date") or str(w.get("publication_year") or ""),
                        year=w.get("publication_year"),
                        authors=[(a.get("author") or {}).get("display_name")
                                 for a in (w.get("authorships") or [])][:6],
                        volume=None, issue=None, page=None, type=w.get("type"),
                        url=f"https://doi.org/{doi}", topics=[], tier=tier_of(v),
                        venue_why="OpenAlex 초록 검색으로 찾았다", channel="openalex")
                if tkey not in rows[doi]["topics"]:
                    rows[doi]["topics"].append(tkey)
                rows[doi].setdefault("channels", set())
            cursor = (r.get("meta") or {}).get("next_cursor")
            time.sleep(0.8)
            if not cursor or len(res) < 100:
                break
        print(f"  OpenAlex/{tkey:<14} 누적 {n_oa} 건 (새것 {n_oa_new})")

    print("■ 학회 (사용자 지시 — ICASSP·MobiCom·SIGCOMM·SenSys·MobiSys 계열)")
    for kind, name, key, why in CONFS:
        #: ⛔⛔2026-09-11(2) — `query.container-title` 은 **필터가 아니라 퍼지 검색**이라
        #  엉뚱한 논문집을 돌려준다(실측: "IEEE Radar Conference" 로 조회했더니 LCN·NordPac).
        #  그래서 VENUE_GUARD 가 전부 걸러내 RadarConf·EuCAP 이 0 편이 됐다.
        #  ⇒ **주제어에 학회 이름을 섞어** query.bibliographic 으로 묻고 가드로 고른다.
        #    실측: 이 길로 RadarConf 142 · EuCAP 157 편이 가드를 통과한다.
        if kind in ("acm", "ieee"):
            #: ⛔⛔2026-09-12 — ACM 학회라고 **다 10.1145 가 아니다.** IPSN 은 IEEE 가
            #  펴내 10.1109 에 들어 있어, 10.1145 로만 물으면 **구조적으로 0 편**이다.
            #  ⇒ 애매한 것은 두 접두사를 다 본다. 가드가 엉뚱한 것을 걸러 준다.
            prefs = (["10.1145", "10.1109"] if name in ("IPSN", "HotMobile")
                     else ["10.1145"] if kind == "acm"
                     else ["10.23919"] if name == "EuCAP" else ["10.1109"])
            for pref in prefs:
                sweep(name, why, f"prefix:{pref},from-pub-date:{SINCE},type:proceedings-article",
                      venue_hint=key)
        else:
            sweep(name, why, f"issn:{key},from-pub-date:{SINCE}")

    for d in rows.values():
        key = re.sub(r"[^a-z0-9]+", "", d["title"].lower())[:60]
        d["maybe_in_store"] = bool(key in have_titles)
        d.pop("channels", None)
        d.setdefault("tier", tier_of(d.get("venue", "")))
        d.setdefault("abstract", None)

    print("■ 초록 받기 (OpenAlex · DOI 로)")
    abs_stat = fetch_abstracts(rows)
    n_abs = sum(1 for d in rows.values() if d.get("abstract"))
    print(f"  초록이 있는 행 {n_abs}/{len(rows)}")

    print("■ 닻 검사 (저장소가 아는 편을 도로 찾아오나)")
    anchors = check_anchors(rows)
    n_found = sum(a["found"] for a in anchors)
    for a in anchors:
        print(f"  {'✅' if a['found'] else '⛔'} {a['name']}"
              + (f"  ← {a['found_venue']}" if a["found"] else ""))
    print(f"  재현율 {n_found}/{len(anchors)}")

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
        "topics": TOPICS, "openalex_topics": OA_TOPICS, "n_rows": len(rows),
        #: ⭐⭐**재현율을 수로 싣는다.** 옛 판은 INDEX 에 손으로 «4/6» 이라고만 적혀 있었고
        #  그 여섯이 무엇인지도, 검사하는 코드도 없었다(실측하니 0/6 이었다).
        "anchors": anchors,
        "recall": {"found": n_found, "total": len(anchors),
                   "how_ko": "ANCHORS 의 DOI·제목으로 원장을 찾는다. 굽을 때마다 다시 잰다."},
        "abstracts": {"rows_with_abstract": n_abs, "asked": abs_stat["asked"],
                      "got": abs_stat["got"],
                      "how_ko": ("OpenAlex 에서 DOI 로 받아 역색인을 되돌려 붙였다. "
                                 "⚠저작권 때문에 안 주는 편이 있다 — 그 행은 null 이다.")},
        "venue_counts": {k: sum(1 for d in rows.values() if d.get("venue") == k)
                         for k in sorted({d.get("venue", "") for d in rows.values()})},
        "tiers_ko": {"정본": sorted(TIER_CORE),
                     "how_ko": ("정본 = 저장소가 정한 탑티어(dl_toptier_anchors.md) + 이 주제의 "
                                "정본 학술지·학회. 일반 = 분야의 정식 게재지이지만 탑티어로 세지 "
                                "않는다. ⛔층은 우리가 정한 것이지 객관 지표가 아니다.")},
        "channels_ko": {"crossref": "ISSN·DOI 앞자리로 조회 — 제목만 본다",
                        "openalex": "search= 가 제목+초록을 본다 — 제목에 우리 낱말이 없는 편을 메운다"},
        "limits_ko": [
            "⛔NeurIPS·CVPR·ICLR 은 Crossref 색인이 고르지 않아 여기 안 잡힌다 — 그쪽은 "
            "prior_work/dl_toptier_anchors.md 가 이미 원문 페이지로 확인해 두었다.",
            "⚠ACM 학회는 ISSN 이 없어 DOI 앞자리(10.1145)+논문집 이름으로 잡았다 — 논문집 이름이 "
            "해마다 바뀌므로 빠짐이 있을 수 있다.",
            "⭐2026-09-12 부터 초록을 OpenAlex 에서 DOI 로 받는다(위 abstracts 참고). "
            "⚠저작권 때문에 안 주는 편이 있고 그 행은 null 이다 — «없는 것» 이지 «못 읽은 것» 이 아니다.",
            "⛔⛔2026-09-12 정정 — 제목 거르기가 **소문자 사본에 re.I 없이** 찾고 있어 "
            "대문자가 든 패턴 아홉 개(RCS·ISAC·SBR·mmWave·UAV·sUAS·PID)가 **죽은 코드**였다. "
            "그래서 「A Unified RCS Modeling … 3GPP ISAC Channel …」(Zhang JSAC 2025) 같은 편이 "
            "버려졌고, 옛 INDEX 는 그것을 「제목에 우리 낱말이 없다 — 제목·초록 검색의 한계」로 "
            "적어 진단이 반대 방향으로 닫혀 있었다. 한계가 아니라 버그였다.",
            "⛔⛔2026-09-12 정정 — SENSE 에 `detect` 가 있어 「드론 + 객체검출」이면 다 통과했고, "
            "OFFTOPIC 에 `images`·`optical`·`YOLO` 가 없었다 ⇒ 제목이 광학·영상인 편이 "
            "옛 원장에 35 편 들어와 있었다(옛 INDEX 는 「오염 0 %」라고 적었다).",
            "⭐2026-09-12 — 모바일·신호처리 정본 학회(MobiCom·SenSys·SIGCOMM·MobiSys·IPSN·"
            "HotMobile·IMWUT·ICASSP·INFOCOM)에서는 **드론 낱말을 요구하지 않는다.** 그 자리의 "
            "논문은 사람·손동작·눈을 재느라 제목에 드론을 안 적는다 ⇒ RF 낱말 하나로 담는다.",
            "⛔NSDI 는 USENIX 라 Crossref 에 없다 — 이 조사가 **덮지 못한다**. MobiHoc 도 안 물었다.",
            "⛔제목 낱말로 걸렀다 — 표적 낱말과 전파·레이다 낱말이 **둘 다** 있어야 담는다. "
            "낱말이 없어도 관련 있을 수 있다(재현율 손해).",
            "⭐2026-09-11(2) 두 번째 자기감사 — ⓐ`query.container-title` 이 필터가 아니라 "
            "퍼지 검색이라 엉뚱한 논문집을 돌려줬고(LCN·NordPac) 가드가 전부 걸러 RadarConf·"
            "EuCAP 이 0 편이 됐다 ⇒ 학회 이름을 **주제어에 섞어** 묻고 가드로 고른다 "
            "ⓑ드론 낱말을 반드시 요구했더니 저장소가 아는 편 셋(Ziganshin·Zhang·Clutter-Aware)이 "
            "떨어졌다 ⇒ 핵심 물리 낱말(CORE)만 있어도 담는다.",
            "⭐2026-09-11 자기감사로 고친 것 넷 — ⓐ학술지 6 종이 빠져 저장소가 아는 편 3 개가 "
            "안 걸렸다(WCL·OJ-COMS·Access 등 추가) ⓑ논문집 이름 퍼지 매칭이 엉뚱한 학회를 물어 "
            "MMAR 논문이 «IEEE RadarConf» 로 찍혔다(VENUE_GUARD 로 되짚음) ⓒ제목 거르기가 "
            "느슨해 제어·비전이 14 % 섞였다(TARGET×SENSE 로 조임) ⓓ60 행 한 장이라 조용히 "
            "잘렸다(100 행 × 최대 5 쪽 페이징).",
            "⛔«읽을 목록» 이지 «읽었다» 가 아니다. maybe_in_store 는 파일명 대조라 어림이다.",
            "⛔실기 계측 대조는 0 건이고 이 조사로도 생기지 않는다."]},
        "rows": sorted(rows.values(), key=lambda r: (r["published"] or ""), reverse=True)}
    with open(f"{STORE}/toptier_0911.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n■ 게재판 {len(rows)} 편 → {STORE}/toptier_0911.json")
    write_index(out)
    return 0


def write_index(out: dict) -> None:
    """⭐INDEX.md 를 **생성기가 굽는다**.

    ⛔⛔2026-09-12 정정 — INDEX.md 에 빌더가 없어 손으로 쓰여 있었고, 그래서 수치가
    원장과 어긋났다. ⛔실측으로 확인된 어긋남:
        «RadarConf · EuCAP 63 · 66» → 실제 16 · 18 (63/66 은 논문 수가 아니라 주제태그 합)
        «제어·비전 오염 0 %»        → 제목이 광학·영상인 편 35 편
        «정본 48 편»                → 실제 123
        «재현율 4/6»                → 실제 0/6
        §1ⓒ 가 «원장에서 찾았다» 고 적은 DOI 둘이 원장에 없다
    ⇒ 사람이 적는 자리를 없앤다. 수는 전부 원장에서 꺼내 쓴다.
    """
    m = out["_meta"]; R = out["rows"]
    vc = m["venue_counts"]
    named = ["IEEE ICASSP", "MobiCom", "SIGCOMM", "SenSys", "MobiSys",
             "IPSN", "IEEE INFOCOM", "ACM IMWUT", "HotMobile"]
    n_named = sum(vc.get(k, 0) for k in named)
    tiers = {t: sum(1 for r in R if r.get("tier") == t) for t in ("정본", "일반")}
    L = []
    L.append("# 선행 연구 — 게재지를 정본으로")
    L.append("")
    L.append(f"> ⛔**이 문서는 손으로 쓰지 않는다.** `{m['generator']}` 가 굽는다.")
    L.append(f"> 옛 판은 손으로 쓰여 수가 원장과 어긋나 있었다(정정 기록 R33).")
    L.append("")
    L.append(f"- 구운 때 `{m['made_utc']}` · 구간 `{m['since']}` 이후")
    L.append(f"- 원장 [`toptier_0911.json`](toptier_0911.json) — **{m['n_rows']} 편**")
    L.append(f"- 층: 정본 {tiers['정본']} · 일반 {tiers['일반']}  "
             f"(⛔층은 우리가 정한 것이지 객관 지표가 아니다)")
    L.append("")
    L.append("## 재현율 — 저장소가 아는 편을 도로 찾아오나")
    L.append("")
    L.append(f"**{m['recall']['found']}/{m['recall']['total']}** · {m['recall']['how_ko']}")
    L.append("")
    L.append("| | 닻 | 찾음 | 어디서 |")
    L.append("|---|---|---|---|")
    for a in m["anchors"]:
        L.append(f"| {'✅' if a['found'] else '⛔'} | {a['name']} | "
                 f"{'예' if a['found'] else '**아니오**'} | {a.get('found_venue') or '—'} |")
    L.append("")
    L.append("## 게재지별 편 수")
    L.append("")
    L.append("| 게재지 | 편 | 층 |")
    L.append("|---|---:|---|")
    for k, v in sorted(vc.items(), key=lambda kv: -kv[1]):
        if not v:
            continue
        t = "정본" if k in m["tiers_ko"]["정본"] else "일반"
        L.append(f"| {k} | {v} | {t} |")
    L.append("")
    L.append(f"### ⭐사용자가 탑티어로 지목한 계열 — **{n_named} 편 / {m['n_rows']}** "
             f"({100*n_named/max(m['n_rows'],1):.1f} %)")
    L.append("")
    L.append("| 게재지 | 편 |")
    L.append("|---|---:|")
    for k in named:
        L.append(f"| {k} | {vc.get(k, 0)} |")
    L.append("")
    L.append("## 초록")
    L.append("")
    a = m["abstracts"]
    L.append(f"초록이 있는 행 **{a['rows_with_abstract']}/{m['n_rows']}** "
             f"(물어본 {a['asked']} · 받은 {a['got']}). {a['how_ko']}")
    L.append("")
    L.append("## ⛔이 조사가 **말하지 않는** 것")
    L.append("")
    for x in m["limits_ko"]:
        L.append(f"- {x}")
    L.append("")
    with open(f"{STORE}/INDEX.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"■ 목차 → {STORE}/INDEX.md")


if __name__ == "__main__":
    raise SystemExit(main())
