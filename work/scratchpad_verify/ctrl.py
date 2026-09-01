import os, sys, json, math, time
import numpy as np
import experiment_detection as ED
from waveforms import wifi_80211ac, lte_downlink, nr_downlink
from experiment_x410 import X410Scenario

FAC={"nr":nr_downlink,"wifi":wifi_80211ac,"lte":lte_downlink}
code=sys.argv[1]; std=sys.argv[2]; occ=sys.argv[3]
K=int(os.environ.get("CTRL_K","6000"))
from gpu import pick; pick(verbose=False)
scn=X410Scenario(carrier_hz=ED.FC)
az,el=ED.target_aspect(scn)
sigma_m2=10**(-27.5779568443798/10.0)   # ledger meta.sigma_dbsm
wf=FAC[std](occupancy=occ); cfg=ED.CPI_CFG[std]
pfa_nom=ED.pfa_nominal_for(std,1e-4)
y,ref,meta=ED.build_echo_sionna(wf,cfg["M"],cfg["b"],scn,sigma_m2,(-3.,0.,0.),verbose=False)
pre=ED.Precomputed(y,ref,wf,cfg["M"],meta).to_gpu()
snr_ref=ED.measure_single_snr(pre,1.0)
grid=np.linspace(-6,20,15); sig=10**((snr_ref-grid)/20.)
out={"DPI_AMP":ED.DPI_AMP,"snr_ref":snr_ref,"code":code,"K":K,"resid_dpi_pow":float(np.mean(np.abs(pre.resid_dpi)**2))}
for N in (1,4):
    sv,_=ED.steering_for_N(N,az,el)
    pds=[]
    t0=time.time()
    for sg in sig:
        pds.append(ED.gpu_montecarlo(pre,sv,sg,K,seed=1000+N,pfa=pfa_nom)["Pd"])
    p=np.array(pds)
    s50=float(np.interp(0.5,p,grid))
    out[str(N)]={"Pd":pds,"snr50":s50}
    print(f"  DPI={ED.DPI_AMP} {code} N={N} snr50={s50:.4f} ({time.time()-t0:.0f}s)",flush=True)
g=out["1"]["snr50"]-out["4"]["snr50"]
out["gain_N4"]=g; out["excess_N4"]=g-10*math.log10(4)
print(f"==> DPI={ED.DPI_AMP} {code}: gain(N=4)={g:.4f} dB, excess={g-10*math.log10(4):+.4f} dB",flush=True)
json.dump(out,open(f"/workspace/sionna/scratchpad_verify/ctrl_{code}_dpi{int(ED.DPI_AMP)}.json","w"))
