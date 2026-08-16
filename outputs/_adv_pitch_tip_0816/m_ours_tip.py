# -*- coding: utf-8 -*-
"""우리 날의 팁을 **DJI 를 잰 것과 같은 자**로 잰다(원통 단면, 같은 밴드 폭)."""
import sys, json, numpy as np, trimesh, dataclasses
from scipy.spatial import ConvexHull
sys.path[:0]=["/workspace/sionna/src","/workspace/sionna/benchmark"]
import drones, drone_cad
def cal(P):
    Q=P[ConvexHull(P).vertices]; D=Q[:,None,:]-Q[None,:,:]
    return float(np.linalg.norm(D,axis=-1).max())
def prof(V, rr, band):
    r=np.hypot(V[:,0],V[:,1]); R=r.max(); phi=np.arctan2(V[:,1],V[:,0]); z=V[:,2]
    out=[]
    for x in rr:
        r0=x*R; m=(np.abs(r-r0)<=band)&(np.abs(phi)<np.pi/2)
        if m.sum()<4: out.append(np.nan); continue
        pp=np.angle(np.exp(1j*(phi[m]-np.median(phi[m]))))
        out.append(cal(np.c_[r0*pp,z[m]-np.median(z[m])])/R)
    return np.array(out),R
rr=np.array([0.30,0.40,0.45,0.50,0.60,0.70,0.80,0.90,0.95,0.96,0.97,0.98,0.99,1.00])
res={}
for law,cmax in (("legacy",0.25),("dji_mini2",0.190),("dji_mini2",0.25)):
    sp=dataclasses.replace(drones.DRONES["mini2"],prop_chord_max_over_r=cmax)
    m=drones.build_propeller(sp,n=26,blade_law=law)
    V=np.array(m.v); F=np.array(m.f)
    v,_=trimesh.remesh.subdivide_to_size(V,F,max_edge=2.5e-4)
    for band_mm in (0.25,):
        p,R=prof(v,rr,band_mm*1e-3)
        cmx=np.nanmax(p)
        res[f"{law}@{cmax}"]=dict(R_mm=R*1000,c_max_over_R=float(cmx),
            c_over_R={f"{x:.2f}":round(float(q),4) for x,q in zip(rr,p)},
            c_norm={f"{x:.2f}":round(float(q/cmx),4) for x,q in zip(rr,p)})
        print(f"{law}@{cmax} R {R*1000:.2f} c_max/R {cmx:.4f}")
        print("  c/R  : "+" ".join(f"{q:.4f}" for q in p))
        print("  c/cmx: "+" ".join(f"{q/cmx:.3f}" for q in p))
print("  r/R  : "+" ".join(f"{x:5.2f} " for x in rr))
json.dump(res,open("ours_tip.json","w"),indent=1)
