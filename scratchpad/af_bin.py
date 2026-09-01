import sys, json, numpy as np
sys.path.insert(0,"/workspace/sionna/src")
from numpy.lib.stride_tricks import sliding_window_view
from drones import DRONES
L=json.load(open("/workspace/sionna/outputs/elevation_sweep_md.json",encoding="utf-8"))
Z=np.load("/workspace/sionna/outputs/elevation_sweep_md.npz"); PRF=float(L["_meta"]["prf_hz"]); LAM=3e8/3.5e9
MESH="mfixbatteryi5_blperairframe"
DR=[("matrice4e",""),("s1000plus","s1000plus_"),("mavic4pro","mavic4pro_"),("mini5pro","mini5pro_")]
def spec(k):
    s_=DRONES[k]; b=getattr(s_,"prop_blades",2); r=float(s_.hover_rpm); d=float(getattr(s_,"prop_dia_mm",274))/1000.
    return b*r/60., 2*(np.pi*d*r/60.)/LAM
rng=np.random.default_rng(11)
for dk,pre in DR:
    ffl,ft0=spec(dk)
    E2=np.asarray(Z[f"sionna_p4000000000_swR0D0E0F1_{pre}r15_n8192_{MESH}_d2/el+0"]); ft2=ft0
    nper=max(8,int(round(0.45*PRF/ffl))); nfft=8*nper; w=np.hanning(nper+1)[:-1]
    SS=np.abs(np.fft.fft(sliding_window_view(E2,nper)[::2]*w,n=nfft,axis=1)).T/w.sum()
    fq=np.fft.fftshift(np.fft.fftfreq(nfft,1./PRF)); SS=np.fft.fftshift(SS,axes=0)
    g=(SS**2)[(np.abs(fq)>=.35*ft2)&(np.abs(fq)<=ft2),:].sum(axis=0)
    Y=np.abs(np.fft.rfft((g-g.mean())*np.hanning(g.size)))**2
    fr=np.fft.rfftfreq(g.size,1./(PRF/2.)); df=fr[1]-fr[0]
    fl=float(np.median(Y[(fr>20)&(fr<500)])); b_=int(round(ffl/df))
    win=Y[b_-3:b_+4]; j=int(np.argmax(win))-3
    # surrogate percentile of the +-3 reading
    v3=10*np.log10(win.max()/fl)
    s=[]
    for _ in range(2000):
        gp=rng.permutation(g); Yp=np.abs(np.fft.rfft((gp-gp.mean())*np.hanning(gp.size)))**2
        flp=float(np.median(Yp[(fr>20)&(fr<500)])); s.append(10*np.log10(Yp[b_-3:b_+4].max()/flp))
    s=np.array(s); p=(s>=v3).mean()
    print(f"{dk:>10}  f_flash={ffl:6.1f}  peak at bin offset {j:+d} "
          f"({fr[b_+j]:6.1f} Hz vs {ffl:6.1f} Hz, {fr[b_+j]-ffl:+5.1f} Hz)  "
          f"+-3={v3:6.2f} dB  surrogate p-value={p:.4f}")
