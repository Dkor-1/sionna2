# -*- coding: utf-8 -*-
"""
thread_guard.py — ⭐**코드 안에서** 스레드 수를 못 박는다 (2026-08-20)
================================================================================

왜 환경변수만으로는 부족한가
-----------------------------
`runners/cpu12_env.sh` 가 OMP·MKL 등을 걸어 주지만 **두 구멍**이 남는다:

  ⛔① `os.cpu_count()` 는 여전히 **192** 를 돌려준다(cgroup 할당은 12 다).
     라이브러리가 이 값을 직접 읽어 풀을 만들면 환경변수를 안 볼 수도 있다.
  ⛔② Dr.Jit 은 판마다 환경변수 이름이 달라 `DRJIT_NUM_THREADS` 가 안 먹을 수 있다.
     ⇒ **API 로 직접 세팅**해야 확실하다.

그래서 이 모듈은
  · cgroup 에서 **진짜 CPU 할당**을 읽고
  · Dr.Jit·Mitsuba 스레드 수를 API 로 못 박고
  · 지금 몇 개가 걸렸는지 **되읽어 확인**한다(선언만 하고 안 걸리는 사고를 막는다)

⛔**import 만으로는 아무 일도 안 한다** — `apply()` 를 명시적으로 불러야 한다
   (조용히 전역 상태를 바꾸는 모듈은 나중에 원인 추적을 불가능하게 만든다).

사용:
    from thread_guard import apply, report
    apply(2)            # 프로세스당 스레드 2 개
    print(report())     # 실제로 몇 개가 걸렸나
"""
from __future__ import annotations

import os


def cgroup_cpus() -> float:
    """cgroup 이 실제로 준 CPU 개수. 못 읽으면 os.cpu_count() 로 물러선다."""
    for p in ("/sys/fs/cgroup/cpu.max",):                       # cgroup v2
        try:
            q, per = open(p).read().split()
            if q != "max":
                return float(q) / float(per)
        except Exception:                                       # noqa: BLE001
            pass
    try:                                                        # cgroup v1
        q = int(open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read())
        per = int(open("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read())
        if q > 0:
            return q / per
    except Exception:                                           # noqa: BLE001
        pass
    return float(os.cpu_count() or 1)


#: 환경변수로 거는 것들 — ⚠라이브러리를 import 하기 **전에** 걸려야 먹는다
_ENV_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
             "DRJIT_NUM_THREADS", "MI_NUM_THREADS", "RAYON_NUM_THREADS")


def apply(n: int | None = None, *, verbose: bool = True) -> dict:
    """스레드 수를 못 박는다. n 을 안 주면 **cgroup 할당의 1/4** 을 쓴다(최소 1).

    ⭐1/4 인 이유: 이 저장소는 프로세스를 여러 개 띄우는 구조라, 프로세스마다 할당을
    통째로 잡으면 다시 과점유가 된다. 프로세스 4 개 × 스레드 3 개 ≈ 12 가 되게 맞춘다.
    """
    cpus = cgroup_cpus()
    if n is None:
        n = max(1, int(cpus // 4))
    n = int(max(1, n))

    for k in _ENV_KEYS:
        os.environ[k] = str(n)
    os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
    os.environ.setdefault("KMP_BLOCKTIME", "0")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    got = {}
    # ⛔⛔**환경변수는 Dr.Jit 에 안 먹는다** — `DRJIT_NUM_THREADS`·`MI_NUM_THREADS` 는
    #   drjit 1.3.1 · mitsuba 3.8.0 어디에도 **없는 이름**이다(패키지 전체 grep 0 건, 2026-08-20).
    #   실측: env 로 2 를 걸어도 `dr.thread_count()` 가 **192** 이고, 병렬 작업을 한 번 하면
    #   프로세스 스레드가 **200 개**로 뛴다. API 로 불러야만 걸린다.
    # ── Dr.Jit — 반드시 API 로 ────────────────────────────────────────
    try:
        import drjit as dr
        for fn in ("set_thread_count", "thread_count"):
            f = getattr(dr, fn, None)
            if callable(f):
                try:
                    f(n)
                    got["drjit_api"] = fn
                    break
                except TypeError:
                    pass
        rd = getattr(dr, "thread_count", None)
        if callable(rd):
            try:
                got["drjit_readback"] = int(rd())
            except TypeError:
                pass
    except Exception as e:                                      # noqa: BLE001
        got["drjit_err"] = str(e)[:120]

    # ── Mitsuba ────────────────────────────────────────────────────────
    try:
        import mitsuba as mi
        for fn in ("set_thread_count",):
            f = getattr(mi, fn, None)
            if callable(f):
                try:
                    f(n)
                    got["mitsuba_api"] = fn
                except TypeError:
                    pass
        th = getattr(mi, "Thread", None)
        if th is not None and hasattr(th, "thread_count"):
            try:
                got["mitsuba_readback"] = int(th.thread_count())
            except Exception:                                   # noqa: BLE001
                pass
    except Exception as e:                                      # noqa: BLE001
        got["mitsuba_err"] = str(e)[:120]

    info = dict(cgroup_cpus=round(cpus, 2), os_cpu_count=os.cpu_count(),
                requested=n, **got)
    if verbose:
        print(f"[thread_guard] cgroup {cpus:.0f} CPU · os.cpu_count() {os.cpu_count()} "
              f"→ 스레드 {n} 로 고정 {got}", flush=True)
    return info


def report() -> dict:
    """지금 이 프로세스가 실제로 띄운 스레드 수(선언이 아니라 **실측**)."""
    try:
        n = int(open(f"/proc/{os.getpid()}/status").read().split("Threads:")[1].split()[0])
    except Exception:                                           # noqa: BLE001
        n = -1
    return dict(pid=os.getpid(), threads_now=n,
                cgroup_cpus=round(cgroup_cpus(), 2),
                env={k: os.environ.get(k) for k in _ENV_KEYS})


if __name__ == "__main__":
    import json
    print(json.dumps(apply(), ensure_ascii=False, indent=1))
    print(json.dumps(report(), ensure_ascii=False, indent=1))
