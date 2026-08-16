# -*- coding: utf-8 -*-
"""PX4 공개 로그에서 **실제로 esc_status 를 기록한** 로그 사냥 (수정판).

⚠1차 시도의 오류: 파일 앞머리에 b"esc_status" 가 있는지만 봤더니 적중률 32 % 로 나왔다.
   그건 거짓이다 — PX4 는 **구독하지 않은 토픽의 포맷 정의('F')까지** 앞머리에 전부 적는다.
   실제로 기록됐다는 증거는 `ADD_LOGGED_MSG`('A', 0x41) 레코드다:
       [size(2)] [0x41] [multi_id(1)] [msg_id(2)] "esc_status"
   그래서 b"esc_status" 를 찾은 뒤 **4바이트 앞이 0x41 인지**를 본다.
"""
import concurrent.futures as cf
import gzip
import json
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DL = f"{HERE}/px4_logs"
os.makedirs(DL, exist_ok=True)

with gzip.open(f"{HERE}/dbinfo.json") as fh:
    db = json.load(fh)

cand = [d for d in db
        if d.get("mav_type") in ("Quadrotor", "Hexarotor")
        and 90 <= (d.get("duration_s") or 0) <= 1500
        and (d.get("log_date") or "") >= "2021-01-01"
        and d.get("download_url")]
random.seed(20260816)
random.shuffle(cand)
print("candidates:", len(cand), flush=True)
N_PROBE = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
N_DL = int(sys.argv[2]) if len(sys.argv) > 2 else 60


def probe(d):
    try:
        p = subprocess.run(["curl", "-sL", "--max-time", "60", "-r", "0-786431",
                            d["download_url"]], capture_output=True)
        b = p.stdout
        for m in re.finditer(b"esc_status", b):
            h = m.start()
            if h >= 4 and b[h - 4] == 0x41:
                return d
    except Exception:
        pass
    return None


hits, seen_uuid = [], set()
with cf.ThreadPoolExecutor(max_workers=24) as ex:
    for r in ex.map(probe, cand[:N_PROBE]):
        if r:
            hits.append(r)
            print("HIT", len(hits), r["log_id"], (r.get("airframe_name") or "?")[:28],
                  r["duration_s"], "s", (r.get("vehicle_uuid") or "")[:12], flush=True)
print("PROBED", N_PROBE, "HITS", len(hits), flush=True)
with open(f"{HERE}/esc_hits2.json", "w") as fh:
    json.dump(hits, fh, indent=1)

# 기체 다양성 우선: vehicle_uuid 당 1건
pick = []
for d in hits:
    u = d.get("vehicle_uuid") or d["log_id"]
    if u in seen_uuid:
        continue
    seen_uuid.add(u)
    pick.append(d)
    if len(pick) >= N_DL:
        break
print("PICK", len(pick), "distinct vehicles", flush=True)


def fetch(d):
    out = f"{DL}/{d['log_id']}.ulg"
    if os.path.exists(out) and os.path.getsize(out) > 10000:
        return
    subprocess.run(["curl", "-sL", "--max-time", "900", "-o", out, d["download_url"]])


with cf.ThreadPoolExecutor(max_workers=10) as ex:
    list(ex.map(fetch, pick))
with open(f"{HERE}/esc_pick.json", "w") as fh:
    json.dump(pick, fh, indent=1)
print("DOWNLOADED", len(os.listdir(DL)), flush=True)
