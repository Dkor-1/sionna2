# -*- coding: utf-8 -*-
"""
proc_audit.py — 우리가 남긴 프로세스를 **전수 조사**한다 (2026-08-20)
================================================================================

왜 필요한가
-----------
랩 공용 서버가 오늘 두 번 느려졌고, 원인이 **고아 프로세스**였다.
좀비(zombie)와 고아(orphan)는 다르고, **위험한 쪽은 고아**다:

  | | 좀비 | **고아** |
  |---|---|---|
  | 상태 | 이미 죽었는데 부모가 안 거둠 | **살아서 계속 CPU·GPU 를 씀** |
  | ps 표시 | `Z` — 눈에 띈다 | `S`/`R` — **정상으로 보인다** |
  | 위험 | 낮음(자리만 차지) | **높음** |

그리고 이 저장소에는 «⛔프로세스 자동 kill 금지» 규칙이 있다(2026-08-11 에 자동 청소기가
**계산 중인 워커 9 개를 죽였다**). 그래서 이 도구는 **기본이 «보고만»** 이다.

무엇을 보나
-----------
  · 우리 것으로 보이는 프로세스 전부 — 계보(부모), 나이, **스레드 수**, GPU 메모리
  · 좀비 · 고아(ppid=1) · **스레드 폭주**(캡이 안 걸린 것)
  · GPU 문맥과 프로세스의 대응 — «껍데기»(작업 없이 문맥만) 검출

사용:
    python runners/proc_audit.py            # 보고만 (기본)
    python runners/proc_audit.py --kill-orphans   # ⛔고아만 정리(확인 문구 출력 후)
    python runners/proc_audit.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time

#: 우리 것으로 볼 이름들 — 여기 없는 것은 **남의 것으로 보고 절대 안 건드린다**
OURS = ("elevation_sweep_md.py", "worker_supervisor.py", "coverage_verify_0820.py",
        "verify_optimization.py", "mesh_inmem.py", "run_gaps_", "start_supervisor.sh",
        "worker_scaling_0819.py", "env_scene_cost", "render_builtin_scenes")
#: 스레드가 이보다 많으면 «캡이 안 걸렸다» 로 본다 (정상은 6~20)
THREAD_WARN = 48


def sh(c: str) -> str:
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout


def gpu_mem() -> dict:
    """{pid: MB} — 우리 컨테이너에서 보이는 GPU 프로세스."""
    d = {}
    for ln in sh("nvidia-smi --query-compute-apps=pid,used_memory "
                 "--format=csv,noheader,nounits").splitlines():
        try:
            p, m = [x.strip() for x in ln.split(",")]
            d[int(p)] = d.get(int(p), 0) + int(m)
        except Exception:                                       # noqa: BLE001
            pass
    return d


def scan() -> dict:
    gm = gpu_mem()
    rows, zombies = [], []
    out = sh("ps -eo pid,ppid,pgid,stat,etimes,nlwp,args")
    for ln in out.splitlines()[1:]:
        f = ln.split(None, 6)
        if len(f) < 7:
            continue
        pid, ppid, pgid, stat, ets, nlwp, args = f
        if stat.startswith("Z"):
            zombies.append(dict(pid=int(pid), ppid=int(ppid), args=args[:90]))
            continue
        if not any(k in args for k in OURS):
            continue
        try:
            cvd = [x.split("=", 1)[1] for x in
                   open(f"/proc/{pid}/environ").read().split("\0")
                   if x.startswith("CUDA_VISIBLE_DEVICES=")]
        except Exception:                                       # noqa: BLE001
            cvd = []
        rows.append(dict(pid=int(pid), ppid=int(ppid), pgid=int(pgid), stat=stat,
                         age_min=round(int(ets) / 60, 1), threads=int(nlwp),
                         gpu_mb=gm.get(int(pid), 0), cvd=(cvd[0] if cvd else ""),
                         orphan=(int(ppid) == 1), args=args[:110]))
    live = {r["pid"] for r in rows}
    for r in rows:
        # ⭐부모가 우리 목록에 있으면 «관리되는 것», 없고 ppid=1 이면 고아
        r["managed"] = (r["ppid"] in live)
    return dict(procs=rows, zombies=zombies,
                gpu_pids_unknown=[p for p in gm if p not in live])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kill-orphans", action="store_true",
                    help="⛔고아(ppid=1이고 부모가 우리 목록에 없는 것)를 정리한다. "
                         "기본은 보고만 — 저장소 규칙 «자동 kill 금지» 때문이다.")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    s = scan()
    rows = sorted(s["procs"], key=lambda r: (-r["threads"], -r["age_min"]))
    print(f"═══ 우리 프로세스 {len(rows)} 개 ═══")
    if rows:
        print(f"  {'pid':>7s}{'ppid':>7s}{'상태':>5s}{'나이':>7s}{'스레드':>7s}"
              f"{'GPU MB':>8s}{'카드':>5s}  구분")
        for r in rows:
            kind = ("⛔고아" if r["orphan"] and not r["managed"]
                    else ("자식" if r["managed"] else "최상위"))
            warn = "  ⚠스레드 많음" if r["threads"] >= THREAD_WARN else ""
            print(f"  {r['pid']:7d}{r['ppid']:7d}{r['stat']:>5s}{r['age_min']:7.1f}"
                  f"{r['threads']:7d}{r['gpu_mb']:8d}{r['cvd']:>5s}  {kind}{warn}")
            print(f"          {r['args'][:100]}")
    print(f"\n═══ 좀비 {len(s['zombies'])} 개 ═══")
    for z in s["zombies"]:
        print(f"  pid {z['pid']} (부모 {z['ppid']}) {z['args']}")
    if s["gpu_pids_unknown"]:
        print(f"\n⚠ GPU 를 쓰는데 우리 목록에 없는 pid: {s['gpu_pids_unknown']} "
              f"(다른 컨테이너 것일 수 있다 — 건드리지 않는다)")

    orphans = [r for r in rows if r["orphan"] and not r["managed"]]
    big = [r for r in rows if r["threads"] >= THREAD_WARN]
    print(f"\n  ⭐요약 — 전체 {len(rows)} · 고아 {len(orphans)} · 좀비 {len(s['zombies'])} "
          f"· 스레드 폭주 {len(big)}")
    if big:
        print(f"  ⚠스레드 폭주: {[r['pid'] for r in big]} — thread_guard 가 안 걸린 프로세스다")

    if a.kill_orphans and orphans:
        print(f"\n⛔고아 {len(orphans)} 개를 정리한다:")
        for r in orphans:
            print(f"   kill {r['pid']}  ({r['age_min']:.0f}분 · {r['args'][:70]})")
            try:
                os.kill(r["pid"], 15)
            except Exception as e:                              # noqa: BLE001
                print(f"     실패: {e}")
        time.sleep(3)
        left = [r for r in scan()["procs"] if r["orphan"] and not r["managed"]]
        print(f"  남은 고아 {len(left)} 개")
    elif orphans:
        print("  (정리하려면 --kill-orphans — ⛔계산 중인 것을 죽일 수 있으니 확인 후)")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=1)
        print(f"  saved {a.json}")


if __name__ == "__main__":
    main()
