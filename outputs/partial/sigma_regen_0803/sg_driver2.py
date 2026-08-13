# -*- coding: utf-8 -*-
"""σ 격자 재생성 드라이버 v2 — 원자적 claim 파일로 **여러 드라이버를 동시에** 띄울 수 있다.

v1 은 큐가 프로세스 안에만 있어 두 번 띄우면 같은 칸을 두 번 계산한다. v2 는 칸마다
`claim_{drone}_{band}` 를 O_EXCL 로 만들어 성공한 쪽만 계산한다 — GPU 여유를 보며 슬롯을
증설할 때 안전하다. 실행: python sg_driver2.py "3:4600:6,2:3000:3"
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

SCRATCH = os.path.dirname(os.path.abspath(__file__))
PY = "/workspace/.venvs/py312/bin/python"
ROOT = "/workspace/sionna"
WORKER = os.path.join(SCRATCH, "sg_worker.py")

DRONES = ["s1000plus", "typhoonh480", "matrice4e", "mavic4pro", "phantom4", "mini5pro", "x500v2"]
BANDS = ["wifi", "nr", "lte"]
COST = {"wifi": 3.0, "nr": 1.4, "lte": 1.0}
lock = threading.Lock()


def units():
    out = []
    for b in BANDS:
        for i, d in enumerate(DRONES):
            out.append((COST[b] * (1.0 + 0.3 * (len(DRONES) - i)), d, b))
    out.sort(key=lambda x: -x[0])
    return [(d, b) for _, d, b in out]


def claim(drone, band):
    """O_EXCL 로 칸을 찜한다. 이미 찜됐거나 산출물이 있으면 False."""
    if os.path.exists(os.path.join(SCRATCH, f"sigma_{drone}_{band}.json")):
        return False
    try:
        fd = os.open(os.path.join(SCRATCH, f"claim_{drone}_{band}"),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def main():
    slots = []
    for spec in sys.argv[1].split(","):
        g, mem, n = spec.split(":")
        slots += [(g, mem)] * int(n)
    todo = units()
    idx = [0]
    fails = []

    def take():
        while True:
            with lock:
                if idx[0] >= len(todo):
                    return None
                u = todo[idx[0]]
                idx[0] += 1
            if claim(*u):
                return u

    def run(slot_i, gpu, mem):
        while True:
            u = take()
            if u is None:
                return
            drone, band = u
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
