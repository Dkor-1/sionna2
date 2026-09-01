import sys, json, numpy as np
sys.path.insert(0,"/workspace/sionna/src")
from numpy.lib.stride_tricks import sliding_window_view
from drones import DRONES
L=json.load(open("/workspace/sionna/outputs/elevation_sweep_md.json",encoding="utf-8"))
Z=np.load("/workspace/sionna/outputs/elevation_sweep_md.npz")
PRF=float(L["_meta"]["prf_hz"]); LAM=3e8/3.5e9
MESH="mfixbatteryi5_blperairframe"
DR=[("matrice4e",""),("s1000plus","s1000plus_"),("mavic4pro","mavic4pro_"),("mini5pro","mini5pro_")]
def spec(k):
    s_=DRONES[k]; b=getattr(s_,"prop_blades",2); r=float(s_.hover_rpm)
    d=float(getattr(s_,"prop_dia_mm",274))/1000.0
    return b*r/60.0, 2*(np.pi*d*r/60.0)/LAM, d*1000.0
def gseq(E2,ffl,ft2):
    nper=max(8,int(round(0.45*PRF/ffl))); nfft=8*nper
    w=np.hanning(nper+1)[:-1]
    SS=np.abs(np.fft.fft(sliding_window_view(E2,nper)[::2]*w,n=nfft,axis=1)).T/w.sum()
    fq=np.fft.fftshift(np.fft.fftfreq(nfft,1.0/PRF)); SS=np.fft.fftshift(SS,axes=0)
    msk=(np.abs(fq)>=0.35*ft2)&(np.abs(fq)<=ft2)
    return (SS**2)[msk,:].sum(axis=0)
def readout(g,ffl,k=3):
    Y=np.abs(np.fft.rfft((g-g.mean())*np.hanning(g.size)))**2
    fr=np.fft.rfftfreq(g.size,1.0/(PRF/2.0)); df=fr[1]-fr[0]
    fl=float(np.median(Y[(fr>20)&(fr<500)])); b_=int(round(ffl/df))
    return (10*np.log10(Y[max(0,b_-k):b_+k+1].max()/fl),
            10*np.log10(Y[b_]/fl), df, b_, ffl/df, Y.size)
rng=np.random.default_rng(7)
print(f"{'case':>14} {'ffl/df':>8} {'frac':>6} {'exact':>7} {'+-1':>7} {'+-3':>7} | "
      f"SURROGATE(perm g) med+-3 p99+-3 med_ex p99_ex | scaleinv")
for dk,pre in DR:
    ffl,ft0,dia=spec(dk)
    for el2 in (0.0,):
        k2=f"sionna_p4000000000_swR0D0E0F1_{pre}r15_n8192_{MESH}_d2/el{el2:+.0f}"
        E2=np.asarray(Z[k2]); ft2=ft0*np.cos(np.radians(el2))
        g=gseq(E2,ffl,ft2)
        v3,vex,df,b_,rat,ny=readout(g,ffl,3)
        v1,_,_,_,_,_=readout(g,ffl,1)
        # scale invariance check
        v3s,_,_,_,_,_=readout(gseq(E2*1e7,ffl,ft2),ffl,3)
        # surrogate null: random permutation of the SAME g (identical amplitude
        # distribution, periodicity destroyed) -- matched to the data, unlike white E
        s3=[];sex=[]
        for _ in range(200):
            gp=rng.permutation(g); a,b2,*_=readout(gp,ffl,3); s3.append(a); sex.append(b2)
        s3=np.array(s3); sex=np.array(sex)
        print(f"{dk+'@0':>14} {rat:8.2f} {rat-round(rat):6.2f} {vex:7.2f} {v1:7.2f} {v3:7.2f} | "
              f"{np.median(s3):7.2f} {np.percentile(s3,99):6.2f} {np.median(sex):6.2f} "
              f"{np.percentile(sex,99):6.2f} | {v3s-v3:+.2e}")
# order-statistic prediction for exponential bins
x=rng.standard_exponential((200000,7))
print("\nexpected pure-chance ratios for exponential periodogram bins:")
print(f"  10log10(max7/median-of-many) = {10*np.log10(np.median(x.max(1))/np.log(2)):.2f} dB")
print(f"  10log10(one bin /median-of-many) = {10*np.log10(np.median(x[:,0])/np.log(2)):.2f} dB")
print(f"  -> intrinsic search gain of a +-3-bin max = "
      f"{10*np.log10(np.median(x.max(1))/np.median(x[:,0])):.2f} dB")
