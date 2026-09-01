import sys, json, numpy as np
sys.path.insert(0, "/workspace/sionna/src")
from numpy.lib.stride_tricks import sliding_window_view
from drones import DRONES

L = json.load(open("/workspace/sionna/outputs/elevation_sweep_md.json", encoding="utf-8"))
Z = np.load("/workspace/sionna/outputs/elevation_sweep_md.npz")
PRF = float(L["_meta"]["prf_hz"]); LAM = 3e8/3.5e9
MESH = "mfixbatteryi5_blperairframe"
DR = [("matrice4e",""),("s1000plus","s1000plus_"),("mavic4pro","mavic4pro_"),("mini5pro","mini5pro_")]

def spec(k):
    s_=DRONES[k]; b=getattr(s_,"prop_blades",2); r=float(s_.hover_rpm)
    d=float(getattr(s_,"prop_dia_mm",274))/1000.0
    return b*r/60.0, 2*(np.pi*d*r/60.0)/LAM, d*1000.0

def pipeline(E2, ffl, ft2):
    """exact bottom-row loop of bake_maps.fig_airframes"""
    nper = max(8,int(round(0.45*PRF/ffl))); nfft = 8*nper
    w = np.hanning(nper+1)[:-1]
    SS = np.abs(np.fft.fft(sliding_window_view(E2,nper)[::2]*w, n=nfft, axis=1)).T/w.sum()
    fq = np.fft.fftshift(np.fft.fftfreq(nfft,1.0/PRF)); SS = np.fft.fftshift(SS,axes=0)
    msk = (np.abs(fq)>=0.35*ft2)&(np.abs(fq)<=ft2)
    g = (SS**2)[msk,:].sum(axis=0)
    Y = np.abs(np.fft.rfft((g-g.mean())*np.hanning(g.size)))**2
    fr = np.fft.rfftfreq(g.size,1.0/(PRF/2.0)); df = fr[1]-fr[0]
    fl = float(np.median(Y[(fr>20)&(fr<500)]))
    b_ = int(round(ffl/df))
    v3  = 10*np.log10(Y[max(0,b_-3):b_+4].max()/fl)   # THE LINE (dead code)
    vex = 10*np.log10(Y[b_]/fl)                        # exact bin
    return v3, vex, fl, df, b_, fr, Y

rng = np.random.default_rng(20260901)
print(f"PRF={PRF}")
print(f"{'airframe':>11} {'f_flash':>8} {'df':>6} | {'exact':>7} {'+-3bin':>7} {'gain':>6} | "
      f"{'null_med3':>9} {'null_p99_3':>10} {'null_med_ex':>11} {'null_p99_ex':>11}")
for dk,pre in DR:
    ffl, ft0, dia = spec(dk)
    for el2 in (0.0,-30.0):
        k2=f"sionna_p4000000000_swR0D0E0F1_{pre}r15_n8192_{MESH}_d2/el{el2:+.0f}"
        if k2 not in Z.files: continue
        E2=np.asarray(Z[k2]); ft2=ft0*np.cos(np.radians(el2))
        v3,vex,fl,df,b_,fr,Y = pipeline(E2,ffl,ft2)
        # ---- white null: circular gaussian scaled to mean|E|
        n3=[];nex=[]
        s=float(np.mean(np.abs(E2)))
        for _ in range(60):
            En=s*(rng.standard_normal(E2.size)+1j*rng.standard_normal(E2.size))/np.sqrt(2)
            a,b2,*_=pipeline(En,ffl,ft2); n3.append(a); nex.append(b2)
        n3=np.array(n3); nex=np.array(nex)
        tag=f"{dk}@{el2:+.0f}"
        print(f"{tag:>11} {ffl:8.1f} {df:6.2f} | {vex:7.2f} {v3:7.2f} {v3-vex:6.2f} | "
              f"{np.median(n3):9.2f} {np.percentile(n3,99):10.2f} "
              f"{np.median(nex):11.2f} {np.percentile(nex,99):11.2f}")
        # harmonic contamination of the 20-500 median
        harm=[]
        for h in range(1,20):
            f=h*ffl
            if 20<f<500: harm.append(f)
        sel=(fr>20)&(fr<500)
        clean=sel.copy()
        for f in harm:
            clean &= ~(np.abs(fr-f)<=3*df)
        fl2=float(np.median(Y[clean]))
        if el2==0.0:
            print(f"{'':>11} harmonics in 20-500: {len(harm)}  floor {10*np.log10(fl):.3f} dB "
                  f"-> harm-excised {10*np.log10(fl2):.3f} dB  (delta {10*np.log10(fl/fl2):+.3f} dB)"
                  f"  n_bins={sel.sum()}")
