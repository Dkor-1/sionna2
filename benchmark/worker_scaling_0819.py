# -*- coding: utf-8 -*-
"""
worker_scaling_0819.py — 카드 한 장에 워커를 몇 개 올려야 가장 빠른가 (**실측**)
================================================================================

물음
----
GPU 2 에 워커를 12 개 올렸다. 8 개로 줄이면 느려지나? 오히려 빨라지나?
광선추적은 카드를 시분할하므로 워커를 늘려도 **선형으로 안 빨라진다**. 어디서 꺾이는지 잰다.

규약
----
  · 같은 작업(같은 팔·같은 자세 수)을 **N 개 동시**에 돌리고 **전체 처리량**을 잰다.
    ⭐워커 하나의 속도가 아니라 **다 합쳐 초당 몇 자세**인지가 답이다.
  · 자세 수를 작게 잡아 빨리 끝낸다. 파일 이름에 `_n<자세수>` 가 들어가 **생산 샤드와 안 겹친다**.
  · ⭐생산 워커는 **죽이지 않고 SIGSTOP 으로 재운다** — 잰 뒤 SIGCONT 로 깨운다. 작업 손실 0.
  · 첫 판은 커널 컴파일이 섞이므로 자세 수에 여유를 둔다(예열분이 희석되게).

⛔GPU 2 만 쓴다. 산출: outputs/worker_scaling_0819.json
"""
from __future__ import annotations

import json, os, shutil, signal, subprocess, sys, time
import numpy as np

HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
OUT=os.path.join(ROOT,"outputs","worker_scaling_hi_0819.json")
SHD=os.path.join(ROOT,"outputs","elev_sweep_shards")
GPU="2"
NPOSE=64                      # 워커 하나가 도는 자세 수
LEVELS=(16,24,32,48)          # ⭐2 판 — 1 판이 16 까지 거의 선형이라 위를 본다
ARM=["--engine","sionna","--spp","4000000000","--sw","R1D0E0F1","--max-depth","2",
     "--range-m","15","--els=-30","--shard","0","--nshards","1"]

def gpu2_pids():
    """GPU 2 에서 도는 **생산** 워커 pid — 우리 벤치 프로세스는 아직 없다."""
    out=subprocess.run("ps -eo pid,args",shell=True,capture_output=True,text=True).stdout
    pids=[]
    for l in out.splitlines():
        if 'elevation_sweep_md.py' not in l or 'worker_scaling' in l: continue
        p=int(l.split()[0])
        try:
            env=open(f'/proc/{p}/environ').read().split('\0')
            cvd=[x.split('=',1)[1] for x in env if x.startswith('CUDA_VISIBLE_DEVICES=')]
            if cvd and cvd[0].strip()==GPU: pids.append(p)
        except Exception: pass
    return pids

def run_level(n):
    env=dict(os.environ, CUDA_VISIBLE_DEVICES=GPU, PYTHONPATH="src:benchmark",
             DRJIT_LIBOPTIX_PATH="/workspace/.venvs/optix/libnvoptix.so.1",
             LD_LIBRARY_PATH="/workspace/.venvs/optix:"+os.environ.get("LD_LIBRARY_PATH",""))
    # ⭐워커마다 자세 수를 조금씩 달리해 **파일 이름이 겹치지 않게** 한다(동시 쓰기 사고 방지)
    procs=[]; t0=time.time()
    for i in range(n):
        cmd=["/workspace/.venvs/py312/bin/python","benchmark/elevation_sweep_md.py",
             *ARM,"--n-poses",str(NPOSE+i)]
        procs.append(subprocess.Popen(cmd,env=env,cwd=ROOT,
                                      stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    rcs=[p.wait() for p in procs]
    dt=time.time()-t0
    poses=sum(NPOSE+i for i in range(n))
    return dict(n_workers=n, wall_s=round(dt,1), n_poses_total=poses,
                throughput_pose_per_s=round(poses/dt,3),
                per_worker_pose_per_s=round(poses/dt/n,4),
                all_ok=all(r==0 for r in rcs))

def main():
    stopped=gpu2_pids()
    print(f"  GPU {GPU} 생산 워커 {len(stopped)} 개 → 일시정지(SIGSTOP)")
    for p in stopped:
        try: os.kill(p, signal.SIGSTOP)
        except Exception: pass
    time.sleep(3)
    rows=[]
    try:
        for n in LEVELS:
            r=run_level(n); rows.append(r)
            print(f"   워커 {n:2d} → {r['wall_s']:6.1f} s · 전체 {r['throughput_pose_per_s']:6.3f} 자세/s"
                  f" · 워커당 {r['per_worker_pose_per_s']:.4f}")
    finally:
        for p in stopped:
            try: os.kill(p, signal.SIGCONT)
            except Exception: pass
        print(f"  생산 워커 {len(stopped)} 개 깨움(SIGCONT)")
        # 벤치가 만든 작은 샤드 지우기 (_n64.._n79)
        import glob
        for f in glob.glob(f"{SHD}/*_n{NPOSE}_*.npz")+[x for k in range(NPOSE,NPOSE+max(LEVELS))
                                                       for x in glob.glob(f"{SHD}/*_n{k}_*.npz")]:
            try: os.remove(f)
            except Exception: pass

    base=rows[0]["throughput_pose_per_s"] if rows else None
    for r in rows:
        r["vs_first_x"]=None if not base else round(r["throughput_pose_per_s"]/base,3)
        r["efficiency_pct"]=None if not base else round(
            100*r["per_worker_pose_per_s"]/rows[0]["per_worker_pose_per_s"],1)
    best=max(rows,key=lambda r:r["throughput_pose_per_s"]) if rows else None
    doc={"_meta":{"generator":"benchmark/worker_scaling_0819.py",
         "generated_kst":time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",time.gmtime(time.time()+9*3600)),
         "role_ko":"카드 한 장에 워커를 몇 개 올려야 전체 처리량이 가장 큰가 — 실측",
         "gpu":GPU,"n_poses_per_worker":NPOSE,"arm":" ".join(ARM),
         "method_ko":"생산 워커를 SIGSTOP 으로 재우고 잰 뒤 SIGCONT — 작업 손실 없음",
         "caveat_ko":"자세 수가 작아 커널 컴파일 비용이 상대적으로 크다. 절대 처리량보다 "
                     "**워커 수 사이의 비교**를 읽어야 한다"},
         "levels":rows,
         "best_n_workers":(None if not best else best["n_workers"]),
         "reading_ko":(None if not best else
           f"전체 처리량이 가장 큰 지점은 워커 {best['n_workers']} 개다")}
    with open(OUT,"w",encoding="utf-8") as f: json.dump(doc,f,ensure_ascii=False,indent=1)
    print(f"\n  saved {OUT}")

if __name__=="__main__": main()
