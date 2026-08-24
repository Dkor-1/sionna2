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
import re
import subprocess
import sys
import time

ROOT = "/workspace/sionna"
LOG = os.path.join(ROOT, "runners", "logs", "footprint.log")
PERIOD = 30

#: ⚠문턱 — 넘으면 로그에 표시한다(담당자가 본 «명령당 200 스레드» 를 기준으로 잡았다)
WARN_PROCS = 20          # ⭐**우리 계산** 프로세스 수 (하네스는 안 센다 — OURS 참조)
WARN_THREADS = 600       # 우리 컨테이너 스레드 총수
WARN_WORKER_THREADS = 40  # (미사용 — 총 스레드 수는 판정 근거가 못 된다. nt_threads 주석 참조)
#: ⭐워커 하나의 Dr.Jit 나노스레드 상한. THREADS_PER_WORKER=2 이므로 여유를 둬 4 로 잡는다.
#   ⛔이것이 thread_guard 가 실제로 통제하는 유일한 수다(2026-08-24 실측).
WARN_WORKER_NT = 4
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


#: ⭐cgroup 이 «max» 로 풀린 상자에서는 cgroup_cpus() 가 호스트 전체(64)를 돌려준다.
#   그러면 WARN_CPU=0.90 이 «57.6 CPU 를 넘어야 경고» 가 되어 **사실상 죽는다**
#   (2026-08-24 실측: 우리가 3.2 CPU 를 쓰는데 «0.05» 로 찍혔다).
#   감독자와 같은 예산을 보도록 SIONNA2_CPUS 를 따른다 — 안 주면 기존 동작 그대로.
_c = os.environ.get("SIONNA2_CPUS", "").strip()
CPUS = float(_c) if re.fullmatch(r"\d+(\.\d+)?", _c or "") else cgroup_cpus()
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


def our_gpu() -> tuple[int, list[str]]:
    """⭐**우리** 프로세스가 실제로 연 GPU 문맥 수와 그 카드들.

    ⛔`nvidia-smi --query-compute-apps` 는 **호스트 PID** 를 준다. 우리는 PID 네임스페이스
      안이라 그 PID 를 우리 프로세스와 맞출 수 없다 — 그래서 그 목록을 그냥 세면
      **남의 컨테이너 것까지 우리 부하로 기록된다.**
      실측(2026-08-24): nvidia-smi 12 문맥·15,452 MB 였는데 우리 것은 **3 문맥**뿐이었고
      나머지는 다른 사용자 것이었다. 이 도구의 존재 이유가 «우리가 주는 부하» 인데
      4 배 부풀려 적고 있었다.
    ⇒ 우리가 확인할 수 있는 유일한 근거는 `/proc/<pid>/maps` 에 잡힌 `/dev/nvidiaN` 이다.
    """
    n, cards = 0, set()
    for q in os.listdir("/proc"):
        if not q.isdigit():
            continue
        try:
            with open(f"/proc/{q}/maps") as fh:
                got = set(re.findall(r"/dev/nvidia(\d+)", fh.read()))
        except Exception:                                       # noqa: BLE001
            continue
        if got:
            n += 1
            cards |= got
    return n, sorted(cards, key=int)


def nt_threads(pid: str) -> int:
    """워커 하나의 **Dr.Jit 나노스레드** 수 — thread_guard 가 실제로 통제하는 유일한 풀.

    ⛔총 스레드 수로 판정하면 안 된다. 실측(2026-08-24): 워커 한 개가 73 스레드였는데
      그 구성은 `nt [1]`·`nt [2]` **2 개**(= thread_guard 가 건 값 그대로) + CUDA 드라이버
      2 개 + OptiX 가 만든 주차 스레드 69 개였다. 69 개는 전부 futex 대기였고 10 분 동안
      개당 0.1 초 미만을 썼다. 즉 «73>40 이니 thread_guard 미적용» 은 **오경보**다.
      (같은 파일 위쪽 주석 — 「경고가 늑대소년이 되면 진짜 폭주를 놓친다」)
    """
    n = 0
    try:
        for t in os.listdir(f"/proc/{pid}/task"):
            try:
                if open(f"/proc/{pid}/task/{t}/comm").read().startswith("nt ["):
                    n += 1
            except Exception:                                   # noqa: BLE001
                pass
    except Exception:                                           # noqa: BLE001
        pass
    return n


def snap() -> dict:
    procs = threads = 0                    # ⭐우리 계산만
    all_procs = all_threads = 0            # 컨테이너 전체(참고용)
    wn = wt = wmax = 0
    wnt = 0                                # ⭐나노스레드 최대 — thread_guard 의 실제 관할
    zom = 0
    for ln in sh("ps -eo stat,nlwp,pid,args --no-headers").splitlines():
        f = ln.split(None, 3)
        if len(f) < 4:
            continue
        st, nl, pid_s, args = f[0], int(f[1]), f[2], f[3]
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
            wnt = max(wnt, nt_threads(pid_s))
    gm = gn = 0                            # ⚠카드 전체(남의 컨테이너 포함) — 우리 것이 아니다
    for ln in sh("nvidia-smi --query-compute-apps=pid,used_memory "
                 "--format=csv,noheader,nounits").splitlines():
        try:
            gn += 1
            gm += int(ln.split(",")[1])
        except Exception:                                       # noqa: BLE001
            pass
    our_n, our_cards = our_gpu()           # ⭐우리 것만
    cur, tot = mem_gb()
    return dict(procs=procs, threads=threads,
                all_procs=all_procs, all_threads=all_threads, zombies=zom,
                workers=wn, worker_threads=wt, worker_thread_max=wmax,
                gpu_ctx=gn, gpu_mb=gm, our_gpu_ctx=our_n, our_gpu_cards=our_cards,
                worker_nt_max=wnt, cpu=cpu_frac(), mem_gb=cur, mem_max=tot)


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
        if s["worker_nt_max"] > WARN_WORKER_NT:
            w.append(f"나노스레드 {s['worker_nt_max']}>{WARN_WORKER_NT} "
                     f"(thread_guard 미적용)")
        if s["cpu"] > WARN_CPU:
            w.append(f"CPU {s['cpu']:.2f}>{WARN_CPU}")
        if s["zombies"]:
            w.append(f"⛔좀비 {s['zombies']}")
        line = (f"[{time.strftime('%m-%d %H:%M:%S', time.gmtime(time.time()+9*3600))}] "
                f"우리 {s['procs']:2d}p/{s['threads']:4d}t "
                f"(컨테이너 {s['all_procs']:3d}p/{s['all_threads']:5d}t) · "
                f"워커 {s['workers']:2d}(스레드 {s['worker_threads']:4d}, 최대 {s['worker_thread_max']:3d}, nt {s['worker_nt_max']}) · "
                f"CPU {s['cpu']:.2f}/{CPUS:.0f} · RAM {s['mem_gb']:.1f}"
                + (f"/{s['mem_max']:.0f}G" if s["mem_max"] else "G")
                + f" · GPU 우리 {s['our_gpu_ctx']}문맥[카드{','.join(s['our_gpu_cards']) or '-'}]"
                + f"/카드전체 {s['gpu_ctx']}({s['gpu_mb']:,}MB) · 좀비 {s['zombies']}"
                + ("  ⛔" + " · ".join(w) if w else ""))
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        time.sleep(PERIOD)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
