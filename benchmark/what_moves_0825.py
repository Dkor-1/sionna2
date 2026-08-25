# -*- coding: utf-8 -*-
"""자세(pose)마다 «무엇이» 바뀌는가 — 동체는 정말 정지인가, 깜빡임의 박자는 무엇인가."""
import sys, numpy as np
sys.path.insert(0,"/workspace/sionna/benchmark"); sys.path.insert(0,"/workspace/sionna/src")
from clutter_parts_ladder_0824 import load, f_tip, PRF, FFL
EL=0.0
B,_=load("sionna_p4000000000_partsnoprop_r15_n8192_d1",EL)   # 동체만
P,_=load("sionna_p4000000000_partsprop_r15_n8192_d1", EL)    # 프로펠러만
W,_=load("sionna_p4000000000_r15_n8192_d1",           EL)    # 통짜
ac=lambda x: np.asarray(x)-np.asarray(x).mean()

print("=== ① 동체만 팔은 자세가 바뀌어도 정말 안 변하나 ===")
b=np.asarray(B)
print(f"  |E| 최소 {np.abs(b).min():.6e}  최대 {np.abs(b).max():.6e}")
print(f"  |E| 상대 변동폭 (max-min)/mean : {(np.abs(b).max()-np.abs(b).min())/np.abs(b).mean():.3e}")
print(f"  ⇒ 자세 8192 개 내내 사실상 «같은 값». 동체는 정지다.")

print("\n=== ② 통짜의 흔들림은 어떤 박자인가 ===")
X = ac(W)-ac(B)-ac(P)                       # 교차항
env = np.abs(X)                             # 깜빡임 포락선
e = env - env.mean()
Pw = np.abs(np.fft.rfft(e*np.hanning(e.size)))**2
fr = np.fft.rfftfreq(e.size, 1.0/PRF)
k = np.argsort(Pw)[::-1][:6]
print(f"  날개 박자 f_flash = {FFL:.2f} Hz  (블레이드가 시선을 지나가는 빈도)")
print(f"  교차항 포락선의 우세 주파수 [Hz] : {', '.join(f'{fr[i]:.1f}' for i in sorted(k))}")
top = fr[k[0]]
print(f"  최강 성분 {top:.1f} Hz  =  f_flash × {top/FFL:.3f}")

print("\n=== ③ 깜빡임 개수 세기 (58 ms 창) ===")
nz=int(round(0.058*PRF)); seg=env[:nz]
thr=seg.mean()+3*seg.std()
cross=np.sum((seg[1:]>thr)&(seg[:-1]<=thr))
print(f"  문턱(평균+3σ) 넘는 상승 사건 {cross} 회 / {nz/PRF*1000:.0f} ms")
print(f"  ⇒ {cross/(nz/PRF):.0f} Hz · 예상 날개 박자 {FFL:.0f} Hz")
