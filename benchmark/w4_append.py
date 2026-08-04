#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""outputs/r2_read_w4.json 에 논문 레코드를 한 편씩 덧붙이는 증분 기록기.

한 편을 다 읽을 때마다 호출한다. 중간에 세션이 죽어도 읽은 만큼은 남는다.
같은 pdf_path 로 다시 부르면 덮어쓴다(재독 후 정정용).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

OUT = "/home/yunjung/workspace/sionna2/outputs/r2_read_w4.json"

META = {
    "file": "outputs/r2_read_w4.json",
    "wave": "WAVE 4 (deepread_backlog ranks 19-24) - 전편 정독 + H8/C2/C4 적대적 검증",
    "instruction_ko": "새로운 논문 검색도 더 하고 선행 연구 한 편 한 편 다 제대로 읽고 검증하고 적대적 검증도 하고",
    "rule_ko": (
        "주장에는 PDF 경로 + 페이지 + 축자 인용문이 붙는다. 못 붙이면 UNVERIFIED 이고 "
        "UNVERIFIED 는 정직한 결과다. 칸을 그럴듯하게 채우는 것이 이 라운드가 막으려는 실패다."
    ),
    "page_convention": "page 는 1-base (PDF 첫 장 = 1). 인용문은 fitz get_text 추출본 기준.",
    "claims_under_test": {
        "H8": "출판된 논문 중 드론 MESH 의 산란 서명을 Sionna 급 GPU 광선 엔진 '안에서' 계산하고 진폭까지 검증한 사례 0 (4갈래 전부 충족해야 반증)",
        "C2": "Sionna 파이프라인에서 dBsm 을 찍은 논문은 Ziganshin EuCAP 2025 단 한 편이고 대상은 자동차",
        "C4": "교정된 오경보율에서 조명원(illuminator)을 통제 비교한 사례 없음",
    },
    "generated": datetime.now().isoformat(timespec="seconds"),
}


def load():
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            return json.load(f)
    return {"meta": META, "papers": [], "corrections_to_our_records": [], "claim_status": {}}


def save(doc):
    doc["meta"] = {**META, "records": len(doc["papers"])}
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)


def append(record: dict):
    doc = load()
    doc["papers"] = [p for p in doc["papers"] if p.get("pdf_path") != record.get("pdf_path")]
    doc["papers"].append(record)
    save(doc)
    print("appended:", record.get("pdf_path"), "| total:", len(doc["papers"]))


def put_top(key: str, value):
    doc = load()
    doc[key] = value
    save(doc)
    print("set:", key)


if __name__ == "__main__":
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    if isinstance(payload, dict) and payload.get("_top_key"):
        put_top(payload["_top_key"], payload["value"])
    else:
        append(payload)
