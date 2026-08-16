# -*- coding: utf-8 -*-
"""팁 밴드 스펙트럼 — **바이스태틱**(β=81°, 헤드라인 팔) 확인. 감사 C5 가 «형상 민감도는
바이스태틱에서 커진다» 고 했으므로 모노 결과만으로 끝내지 않는다."""
import json, sys, dataclasses, numpy as np
sys.path[:0] = ["/workspace/sionna/src", "/workspace/sionna/benchmark"]
import drone_cad, drones
from rcs_po import mesh_to_points, C0
FC=3.5e9; LAM=C0/FC; K=2*np.pi/LAM
def look(az,el):
    az,el=np.radians(az),np.radians(el)
    return np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
L_rr,L_fr=list(drone_cad.CHORD_RR),list(drone_cad.CHORD_FRAC)
b=dict(drone_cad.BLADE_LAWS["legacy"]); f=list(L_fr); f[-1]=0.20
b.update(chord_rr=tuple(L_rr),chord_frac=tuple(f),source="scratch tip0.20")
drone_cad.BLADE_LAWS["legacy_tip0.20"]=b
def series(spec,law,el,beta,cmax,n_phi=2880):
    sp=dataclasses.replace(spec,prop_chord_max_over_r=cmax)
    m=drones.build_propeller(sp,n=26,blade_law=law)
    P,N,dA=mesh_to_points(m,LAM/11.)
    ut,us=look(0,el),look(beta,el)
    phis=np.linspace(0,360./spec.prop_blades,n_phi,endpoint=False); E=np.empty(n_phi,complex)
    for a in range(0,n_phi,120):
        q=min(a+120,n_phi); th=np.radians(phis[a:q]); c,s=np.cos(-th),np.sin(-th)
        Ut=np.stack([c*ut[0]-s*ut[1],s*ut[0]+c*ut[1],np.full(q-a,ut[2])],1)
        Us=np.stack([c*us[0]-s*us[1],s*us[0]+c*us[1],np.full(q-a,us[2])],1)
        NT=N@Ut.T; NS=N@Us.T
        E[a:q]=(np.where((NT>0)&(NS>0),NT,0.)*dA[:,None]*np.exp(1j*K*(P@(Ut+Us).T))).sum(0)
    return phis,E
spec=drones.DRONES["matrice4e"]; el=-30.; rpm=float(spec.hover_rpm); prf=20000.; n_t=8192
R=spec.prop_dia_mm/2000.; v=2*np.pi*rpm/60.*R
res=[]
for beta in (81.0,120.0):
    ft=2*v/LAM*np.cos(np.radians(el))*np.cos(np.radians(beta/2))
    base=None
    for law,cmax in (("legacy",0.25),("legacy_tip0.20",0.25),("dji_mini2",0.25),("dji_mini2",0.190)):
        phis,E=series(spec,law,el,beta,cmax)
        t=np.arange(n_t)/prf; idx=np.mod((360.*rpm/60.)*t/(360./spec.prop_blades)*len(E),len(E))
        i0=np.floor(idx).astype(int)%len(E); i1=(i0+1)%len(E); fr=idx-np.floor(idx)
        Et=E[i0]*(1-fr)+E[i1]*fr
        ac=Et-Et.mean(); S=np.abs(np.fft.fftshift(np.fft.fft(ac*np.hanning(len(ac)))))**2
        fq=np.fft.fftshift(np.fft.fftfreq(len(ac),1/prf))
        bp=lambda lo,hi: float(S[(np.abs(fq)>=lo)&(np.abs(fq)<hi)].sum())
        r=dict(beta=beta,law=f"{law}@{cmax}",f_tip=ft,P_tot=float(S.sum()),
               P_tip=bp(0.9*ft,ft),P_oob=bp(ft,prf/2),
               sig_mean_dbsm=float(10*np.log10((4*np.pi/LAM**2)*np.mean(np.abs(E)**2))),
               peak_dbsm=float(10*np.log10((4*np.pi/LAM**2)*np.max(np.abs(E)**2))))
        if base is None: base=r
        for q in ("P_tot","P_tip","P_oob"): r["d_"+q]=float(10*np.log10(r[q]/base[q]))
        res.append(r)
        print(f"β{beta:5.0f} {r['law']:22s} σmean {r['sig_mean_dbsm']:7.2f} peak {r['peak_dbsm']:7.2f} "
              f"ΔP_tot {r['d_P_tot']:+6.2f} ΔP_tip(0.9-1.0) {r['d_P_tip']:+6.2f} ΔP_oob {r['d_P_oob']:+6.2f}",flush=True)
json.dump(res,open("tip_bistatic.json","w"),indent=1)
