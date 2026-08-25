# -*- coding: utf-8 -*-
"""교차항이 «무엇처럼» 생겼나 — 날개 반향인가, 동체가 깜빡이는 것인가."""
import sys, numpy as np
sys.path.insert(0,"/workspace/sionna/benchmark"); sys.path.insert(0,"/workspace/sionna/src")
from clutter_parts_ladder_0824 import load, f_tip, cs_eca, PRF, FFL
EL=0.0; FT=f_tip(EL)
P_,_=load("sionna_p4000000000_partsprop_r15_n8192_d1",EL)
W_,_=load("sionna_p4000000000_phys_r15_n8192_d1",EL)
B_,_=load("sionna_p4000000000_partsnoprop_r15_n8192_d1",EL)
ac=lambda x: np.asarray(x)-np.asarray(x).mean()
X = ac(W_)-ac(B_)-ac(P_)                       # 교차항
R = cs_eca(W_)

print("=== ① 합이 맞나 (선형 중첩이 성립하나) ===")
lin = ac(B_)+ac(P_)
print(f"  |동체+프로펠러| 요동 : {np.abs(lin).std():.3e}")
print(f"  |통짜|         요동 : {np.abs(ac(W_)).std():.3e}")
print(f"  ⇒ 통짜 / (동체+프로펠러) = {np.abs(ac(W_)).std()/np.abs(lin).std():.1f} 배")
print(f"  ⇒ 교차항이 통짜 요동에서 차지하는 몫 : "
      f"{100*np.linalg.norm(X)/np.linalg.norm(ac(W_)):.2f} %")

print("\n=== ② «깜빡임» 인가 — 시간에 몰려 있나 ===")
def peaky(x, name):
    a=np.abs(ac(x)); e=a**2; e=e/e.sum()
    top=np.sort(e)[::-1]
    k=float((a**4).mean()/(a**2).mean()**2)          # 첨도(2 = 가우시안)
    print(f"  {name:16} 첨도 {k:7.2f} · 에너지 상위 1 % 표본이 차지 {100*top[:max(1,len(top)//100)].sum():5.1f} %")
peaky(P_,"프로펠러 단독"); peaky(X,"교차항"); peaky(R,"ECA 잔차"); peaky(B_,"동체 단독")

print("\n=== ③ 교차항이 동체 세기에 매여 있나 ===")
print(f"  동체 평균 |E|      : {np.abs(B_).mean():.3e}")
print(f"  프로펠러 평균 |E|  : {np.abs(P_).mean():.3e}")
print(f"  ⇒ 동체 / 프로펠러  : {np.abs(B_).mean()/np.abs(P_).mean():.3e} 배 "
      f"({20*np.log10(np.abs(B_).mean()/np.abs(P_).mean()):.1f} dB)")
print(f"  교차항 크기 / (동체평균 × 프로펠러요동상대) 예측 검산:")
pred = np.abs(B_).mean()*(np.abs(ac(P_)).std()/np.abs(P_).mean())
print(f"    예측 {pred:.3e}  vs  실제 교차항 {np.abs(X).std():.3e}")
