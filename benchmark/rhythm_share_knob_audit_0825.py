# -*- coding: utf-8 -*-
"""리듬 몫이 «손잡이»에 얼마나 흔들리는가 — 덱에 올릴 물건인지 판정.
⛔GPU 안 씀. 있는 샤드만 읽는다."""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, "/workspace/sionna/benchmark")
sys.path.insert(0, "/workspace/sionna/src")
from clutter_parts_ladder_0824 import load, f_tip, cs_eca, PRF, FFL

EL = 0.0
def share(E, hw, fa):
    x = np.asarray(E, complex); x = x - x.mean(); n = x.size
    P = np.abs(np.fft.fft(x * np.hanning(n)))**2
    fr = np.fft.fftfreq(n, 1.0/PRF)
    above = np.abs(fr) >= fa
    if not above.any() or P[above].sum() <= 0: return float("nan")
    kk = np.round(np.abs(fr)/FFL)
    on = above & (np.abs(np.abs(fr) - kk*FFL) <= hw)
    return 100.0*P[on].sum()/P[above].sum()

P_,_ = load("sionna_p4000000000_partsprop_r15_n8192_d1", EL)   # 프로펠러 단독
W_,_ = load("sionna_p4000000000_phys_r15_n8192_d1",      EL)   # 통짜 stock
O_,_ = load("ours_r15_n8192",                            EL)   # 통짜 our kernel
FT = f_tip(EL)
print(f"el {EL:+.0f}  f_flash={FFL:.2f} Hz  f_tip={FT:.1f} Hz  PRF={PRF:.0f} Hz")
print(f"길이: prop={P_.size} whole={W_.size} ours={O_.size}\n")

# 백색잡음 대조군 — 같은 길이, 같은 손잡이
rng = np.random.default_rng(0)
N_ = rng.normal(size=W_.size) + 1j*rng.normal(size=W_.size)

rows = [("propellers only", P_), ("whole drone stock", W_), ("whole drone ours", O_),
        ("WHITE NOISE", N_)]
print("=== ① hw 손잡이만 흔들었을 때 (f_above = f_tip 고정) ===")
hws = [2.0, 4.0, 8.0, 16.0, 32.0, 63.3]
print(f"{'':22}" + "".join(f"{h:>9.1f}" for h in hws) + "   ← hw [Hz]")
print(f"{'기하학적 바닥 2hw/ffl':22}" + "".join(f"{200*h/FFL:>8.1f}%" for h in hws))
print("-"*22 + "-"*9*len(hws))
for name, E in rows:
    print(f"{name:22}" + "".join(f"{share(E,h,FT):>8.1f}%" for h in hws))

print("\n=== ② f_above 손잡이만 흔들었을 때 (hw = 8 Hz 고정) ===")
fas = [("1.5·f_flash (함수 기본값)", 1.5*FFL), ("f_tip el0 (덱이 쓴 값)", FT),
       ("f_tip el-30 (다른 파일이 쓴 값)", 1101.6), ("2·f_tip", 2*FT)]
for label, fa in fas:
    vals = "".join(f"{share(E,8.0,fa):>8.1f}%" for _, E in rows)
    print(f"{label:32}{fa:>8.1f} Hz  {vals}")
print(f"{'':32}{'':>8}     " + "".join(f"{n.split()[0][:7]:>8}" for n,_ in rows))
