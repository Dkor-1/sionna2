# -*- coding: utf-8 -*-
"""교차항의 «뾰족함»이 물리인가 솔버 이산화 흔적인가.
   같은 장면·같은 자세를 두 엔진으로 쏜 뒤 요동의 «모양»을 비교한다."""
import sys, numpy as np
sys.path.insert(0,"/workspace/sionna/benchmark"); sys.path.insert(0,"/workspace/sionna/src")
from clutter_parts_ladder_0824 import load, PRF, FFL
ac=lambda x: np.asarray(x)-np.asarray(x).mean()
def shape(x):
    a=np.abs(ac(x)); e=a**2; e=e/e.sum(); top=np.sort(e)[::-1]
    kurt=float((a**4).mean()/(a**2).mean()**2)
    p1=100*top[:max(1,len(top)//100)].sum()
    # 이웃 표본 사이 상대 도약 — 경로가 톡 튀면 커진다
    d=np.abs(np.diff(np.asarray(x)))
    jump=float(np.percentile(d,99.9)/ (np.abs(np.asarray(x)).mean()+1e-300))
    return kurt,p1,jump

ARMS=[("PathSolver phy off","sionna_p4000000000_r15_n8192_d1"),
      ("PathSolver phy on ","sionna_p4000000000_phys_r15_n8192_d1"),
      ("SBR + PO (ours)   ","ours_r15_n8192")]
print("=== 통짜 기체 요동의 «모양» — el +0, 자세 8192 ===")
print(f"{'엔진':20}{'첨도':>9}{'상위1% 몫':>12}{'99.9%ile 도약/평균':>22}")
print("-"*63)
for nm,arm in ARMS:
    E,_=load(arm,0.0)
    if E is None: print(f"{nm:20}  (샤드 없음)"); continue
    k,p1,j=shape(E)
    print(f"{nm:20}{k:9.1f}{p1:11.1f}%{j:22.3e}")
print("\n  참고 · 매끄러운 연속 신호는 첨도 ≈2, 상위 1 % 몫 ≈6 %")
E,_=load("sionna_p4000000000_partsprop_r15_n8192_d1",0.0); k,p1,j=shape(E)
print(f"  {'프로펠러 단독(PS)':18}{k:9.1f}{p1:11.1f}%{j:22.3e}")
E,_=load("ours_free_r15_n8192",0.0); k,p1,j=shape(E)
print(f"  {'프로펠러 단독(ours)':18}{k:9.1f}{p1:11.1f}%{j:22.3e}")

print("\n=== 자세를 촘촘히 하면 뾰족함이 «수렴»하나(물리) 안 하나(이산화) ===")
E,_=load("sionna_p4000000000_r15_n8192_d1",0.0)
for step in (1,2,4,8):
    k,p1,j=shape(E[::step])
    print(f"  자세 간격 x{step}  (표본 {E[::step].size:5d})  첨도 {k:7.1f} · 상위1% {p1:5.1f}%")

# ── 섬광 폭 — 이 파일의 핵심 판정 ──────────────────────────────────────
print("\n=== 섬광 하나가 몇 «자세» 에 걸쳐 있나 ===")
print(f"   블레이드 통과 1 회당 자세 수 {PRF/FFL:.1f}  ← 물리적 스윕이면 이 폭이어야 한다\n")
for nm,arm in [("PathSolver phy off","sionna_p4000000000_r15_n8192_d1"),
               ("PathSolver phy on ","sionna_p4000000000_phys_r15_n8192_d1"),
               ("SBR + PO (ours)   ","ours_r15_n8192")]:
    E,_=load(arm,0.0); a=np.abs(ac(E)); m=a>(a.mean()+3*a.std())
    runs=[]; c=0
    for v in m:
        if v: c+=1
        elif c: runs.append(c); c=0
    if c: runs.append(c)
    runs=np.array(runs) if runs else np.array([0])
    print(f"  {nm}  사건 {len(runs):4d} · 폭 중앙값 {np.median(runs):5.1f} 자세 · "
          f"1 자세짜리 {100*np.mean(runs==1):5.1f} %")
