# -*- coding: utf-8 -*-
"""
footprint_monitor.py — 우리가 서버에 주는 부하를 **계속 기록한다** (2026-08-20)
================================================================================

왜 만들었나
-----------
랩 서버(A6000)가 오늘 두 번 느려졌고, 서버 담당자가 원인으로 «명령마다 스레드 200 개 ·
30 개 명령 = 6,000 스레드» 를 짚었다. 우리도 아침에 **워커 87 개 × 322 스레드 ≈ 28,000**
을 띄웠으니 주범 중 하나였다.

⛔**담당자 지시(2026-08-19)**
   «종료하는 것도 클로드로 명령하지 마십시오. 그러면 좀비 프로세스가 생깁니다.
     직접 불가능하다고 판단되면 성은씨한테 부탁하고 컨테이너 재시작 or 재생성 추천드립니다.»
   ⇒ **이 저장소는 이제 kill 을 쓰지 않는다.** 줄이려면 «배수(drain)» 를 쓴다 —
     큐 줄을 무력화해 새로 안 뜨게 하고, 돌던 것은 스스로 끝나게 둔다.

무엇을 기록하나 (30 초마다)
---------------------------
  · 우리 컨테이너의 **프로세스 수 · 스레드 수** (담당자가 본 바로 그 지표)
  · 우리 계산 워커만 따로
  · cgroup CPU 사용률 · cgroup 메모리
  · GPU 문맥 수와 메모리
  · ⚠문턱을 넘으면 로그에 **⛔** 를 찍는다(죽이지는 않는다 — 보고만)

산출: runners/logs/footprint.log (한 줄에 한 시점, 사람이 읽는 형식)
실행: nohup setsid python runners/footprint_monitor.py &
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

ROOT = "/workspace/sionna"
LOG = os.path.join(ROOT, "runners", "logs", "footprint.log")
PERIOD = 30

#: ⚠문턱 — 넘으면 로그에 표시한다(담당자가 본 «명령당 200 스레드» 를 기준으로 잡았다)
WARN_PROCS = 20          # ⭐**우리 계산** 프로세스 수 (하네스는 안 센다 — OURS 참조)
WARN_THREADS = 600       # 우리 컨테이너 스레드 총수
WARN_WORKER_THREADS = 40  # 워커 하나가 이보다 많으면 thread_guard 가 안 걸린 것이다
WARN_CPU = 0.90          # cgroup CPU 사용률


def sh(c: str) -> str:
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout


def cgroup_cpus() -> float:
    try:
        q, per = open("/sys/fs/cgroup/cpu.max").read().split()
        if q != "max":
            return float(q) / float(per)
    except Exception:                                           # noqa: BLE001
        pass
    return float(os.cpu_count() or 1)


CPUS = cgroup_cpus()
_prev = {"t": 0.0, "u": 0}


def cpu_frac() -> float:
    try:
        u = 0
        for ln in open("/sys/fs/cgroup/cpu.stat"):
            if ln.startswith("usage_usec"):
                u = int(ln.split()[1]); break
        now = time.time()
        pt, pu = _prev["t"], _prev["u"]
        _prev["t"], _prev["u"] = now, u
        if pt <= 0:
            return 0.0
        return (u - pu) / 1e6 / max(1e-6, now - pt) / max(1.0, CPUS)
    except Exception:                                           # noqa: BLE001
        return -1.0


def mem_gb():
    try:
        mx = open("/sys/fs/cgroup/memory.max").read().strip()
        cur = int(open("/sys/fs/cgroup/memory.current").read())
        tot = None if mx == "max" else int(mx) / 2 ** 30
        return cur / 2 ** 30, tot
    except Exception:                                           # noqa: BLE001
        return -1.0, None


#: ⭐**우리 계산**으로 볼 이름들 — 여기 없는 것(Claude 하네스·셸·에디터)은 안 센다.
#   ⛔2026-08-20: 하네스까지 세는 바람에 «프로세스 52>24» 경고가 계속 떴다(우리 계산은 8 개뿐).
#   경고가 늑대소년이 되면 진짜 폭주를 놓친다.
OURS = ("elevation_sweep_md.py", "worker_supervisor.py", "coverage_verify_0820.py",
        "verify_optimization.py", "worker_scaling_0819.py", "env_scene_cost",
        "render_builtin_scenes", "run_gaps_", "start_supervisor.sh", "footprint_monitor.py")


def snap() -> dict:
    procs = threads = 0                    # ⭐우리 계산만
    all_procs = all_threads = 0            # 컨테이너 전체(참고용)
    wn = wt = wmax = 0
    zom = 0
    for ln in sh("ps -eo stat,nlwp,args --no-headers").splitlines():
        f = ln.split(None, 2)
        if len(f) < 3:
            continue
        st, nl, args = f[0], int(f[1]), f[2]
        if st.startswith("Z"):
            zom += 1
            continue
        all_procs += 1
        all_threads += nl
        if not any(k in args for k in OURS):
            continue
        procs += 1
        threads += nl
        if "elevation_sweep_md.py" in args:
            wn += 1
            wt += nl
            wmax = max(wmax, nl)
    gm = gn = 0
    for ln in sh("nvidia-smi --query-compute-apps=pid,used_memory "
                 "--format=csv,noheader,nounits").splitlines():
        try:
            gn += 1
            gm += int(ln.split(",")[1])
        except Exception:                                       # noqa: BLE001
            pass
    cur, tot = mem_gb()
    return dict(procs=procs, threads=threads,
                all_procs=all_procs, all_threads=all_threads, zombies=zom,
                workers=wn, worker_threads=wt, worker_thread_max=wmax,
                gpu_ctx=gn, gpu_mb=gm, cpu=cpu_frac(), mem_gb=cur, mem_max=tot)


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"\n===== 시작 {time.strftime('%m-%d %H:%M:%S', time.gmtime(time.time()+9*3600))} "
                f"(KST) · CPU 할당 {CPUS:.0f} · 문턱 프로세스 {WARN_PROCS} "
                f"스레드 {WARN_THREADS} 워커스레드 {WARN_WORKER_THREADS} =====\n")
    cpu_frac()                                                  # 기준점
    while True:
        s = snap()
        w = []
        if s["procs"] > WARN_PROCS:
            w.append(f"프로세스 {s['procs']}>{WARN_PROCS}")
        if s["threads"] > WARN_THREADS:
            w.append(f"스레드 {s['threads']}>{WARN_THREADS}")
        if s["worker_thread_max"] > WARN_WORKER_THREADS:
            w.append(f"워커스레드 {s['worker_thread_max']}>{WARN_WORKER_THREADS} "
                     f"(thread_guard 미적용 의심)")
        if s["cpu"] > WARN_CPU:
            w.append(f"CPU {s['cpu']:.2f}>{WARN_CPU}")
        if s["zombies"]:
            w.append(f"⛔좀비 {s['zombies']}")
        line = (f"[{time.strftime('%m-%d %H:%M:%S', time.gmtime(time.time()+9*3600))}] "
                f"우리 {s['procs']:2d}p/{s['threads']:4d}t "
                f"(컨테이너 {s['all_procs']:3d}p/{s['all_threads']:5d}t) · "
                f"워커 {s['workers']:2d}(스레드 {s['worker_threads']:4d}, 최대 {s['worker_thread_max']:3d}) · "
                f"CPU {s['cpu']:.2f}/{CPUS:.0f} · RAM {s['mem_gb']:.1f}"
                + (f"/{s['mem_max']:.0f}G" if s["mem_max"] else "G")
                + f" · GPU 문맥 {s['gpu_ctx']}({s['gpu_mb']:,}MB) · 좀비 {s['zombies']}"
                + ("  ⛔" + " · ".join(w) if w else ""))
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        time.sleep(PERIOD)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
