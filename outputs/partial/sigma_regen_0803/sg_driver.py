# -*- coding: utf-8 -*-
"""σ 격자 재생성 드라이버 — (드론×밴드) 21칸을 GPU 슬롯에 뿌린다.

슬롯마다 GPU 를 박고(SIONNA2_GPU) 예산을 준다(SIONNA2_GPU_MEM). 비싼 칸(WiFi·큰 기체)부터
꺼내 쓰는 최장작업 우선 큐라 꼬리가 짧다. 슬롯은 `--slots` 로 `gpu:mem:n` 형식으로 받는다.
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time

SCRATCH = os.path.dirname(os.path.abspath(__file__))
PY = "/home/yunjung/.venvs/py312/bin/python"
ROOT = "/home/yunjung/workspace/sionna2"
WORKER = os.path.join(SCRATCH, "sg_worker.py")

DRONES = ["s1000plus", "typhoonh480", "matrice4e", "mavic4pro", "phantom4", "mini5pro", "x500v2"]
BANDS = ["wifi", "nr", "lte"]          # 비싼 순
COST = {"wifi": 3.0, "nr": 1.4, "lte": 1.0}


def units():
    out = []
    for b in BANDS:
        for i, d in enumerate(DRONES):
            out.append((COST[b] * (1.0 + 0.3 * (len(DRONES) - i)), d, b))
    out.sort(key=lambda x: -x[0])
    return [(d, b) for _, d, b in out]


def main():
    slots = []
    for spec in sys.argv[1].split(","):
        g, mem, n = spec.split(":")
        slots += [(g, mem)] * int(n)
    q: queue.Queue = queue.Queue()
    for u in units():
        out = os.path.join(SCRATCH, f"sigma_{u[0]}_{u[1]}.json")
        if os.path.exists(out):
            print(f"[skip] {u[0]}/{u[1]} 이미 있음", flush=True)
            continue
        q.put(u)
    lock = threading.Lock()
    fails = []

    def run(slot_i, gpu, mem):
        while True:
            try:
                drone, band = q.get_nowait()
            except queue.Empty:
                return
            out = os.path.join(SCRATCH, f"sigma_{drone}_{band}.json")
            log = os.path.join(SCRATCH, f"log_{drone}_{band}.txt")
            env = dict(os.environ)
            env["SIONNA2_GPU"] = gpu
            env["SIONNA2_GPU_MEM"] = mem
            env["PYTHONPATH"] = f"{ROOT}/src:{ROOT}/benchmark"
            t0 = time.time()
            with lock:
                print(f"[slot{slot_i} gpu{gpu}] START {drone}/{band}", flush=True)
            with open(log, "w") as lf:
                r = subprocess.run([PY, WORKER, "--drone", drone, "--band", band, "--out", out],
                                   cwd=ROOT, env=env, stdout=lf, stderr=subprocess.STDOUT)
            with lock:
                ok = (r.returncode == 0)
                print(f"[slot{slot_i} gpu{gpu}] {'OK ' if ok else 'FAIL'} {drone}/{band} "
                      f"{time.time()-t0:.0f}s", flush=True)
                if not ok:
                    fails.append((drone, band))

    ths = [threading.Thread(target=run, args=(i, g, m), daemon=True)
           for i, (g, m) in enumerate(slots)]
    t0 = time.time()
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    print(f"ALL DONE {time.time()-t0:.0f}s  실패={fails}", flush=True)


if __name__ == "__main__":
    main()
