# -*- coding: utf-8 -*-
"""피치 법칙이 저장소의 **실제 플래시 잣대**(md_metrics)를 얼마나 움직이나."""
import json, sys, numpy as np
sys.path[:0] = ["/workspace/sionna/src", "/workspace/sionna/benchmark"]
import drone_cad, drones
from rcs_po import mesh_to_points, C0
from microdoppler_nearfield import md_metrics
FC=3.5e9; LAM=C0/FC
def look(az,el):
    az,el=np.radians(az),np.radians(el)
    return np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
def theta_of(rr_,k_,rr,P,R): return np.arctan(np.interp(rr,rr_,k_)*P/(2*np.pi*rr*R))
def grad_law(name,g,spec):
    R=spec.prop_dia_mm/2000.; P=float(spec.prop_pitch_in)*0.0254
    rr=np.linspace(0.05,1.,96); th=theta_of(drone_cad.PITCH_RR,drone_cad.PITCH_K,rr,P,R)
    th75=np.interp(0.75,rr,th); thg=np.clip(th75+g*(th-th75),np.radians(.5),np.radians(80))
    drone_cad.PITCH_LAWS[name]=dict(rr=tuple(rr),k=tuple(2*np.pi*rr*R*np.tan(thg)/P),source="scratch")
    return name
def run(spec,pl,el,n_phi=2880):
    m=drones.build_propeller(spec,n=26,pitch_law=pl)
    P,N,dA=mesh_to_points(m,LAM/11.); k=2*np.pi/LAM; u=look(0,el)
    phis=np.linspace(0,360./spec.prop_blades,n_phi,endpoint=False); E=np.empty(n_phi,complex)
    for a in range(0,n_phi,150):
        b=min(a+150,n_phi); th=np.radians(phis[a:b]); c,s=np.cos(-th),np.sin(-th)
        U=np.stack([c*u[0]-s*u[1],s*u[0]+c*u[1],np.full(b-a,u[2])],1)
        NU=N@U.T; E[a:b]=(np.where(NU>0,NU,0.)*dA[:,None]*np.exp(2j*k*(P@U.T))).sum(0)
    rpm=float(spec.hover_rpm); prf=20000.; n_t=8192
    t=np.arange(n_t)/prf; idx=np.mod((360.*rpm/60.)*t/(360./spec.prop_blades)*n_phi,n_phi)
    i0=np.floor(idx).astype(int)%n_phi; i1=(i0+1)%n_phi; f=idx-np.floor(idx)
    Et=E[i0]*(1-f)+E[i1]*f
    R=spec.prop_dia_mm/2000.; v=2*np.pi*rpm/60.*R
    ft=2*v/LAM*np.cos(np.radians(el))
    md=md_metrics(Et,prf,flash_hz=spec.prop_blades*rpm/60.,f_tip=ft)
    sig=(4*np.pi/LAM**2)*np.abs(E)**2
    return dict(law=pl,peak_dbsm=float(10*np.log10(sig.max())),mean_dbsm=float(10*np.log10(sig.mean())),
                flash_contrast_db=md["flash_contrast_db"],harmonic_frac=md["harmonic_frac"],
                fd_edge_hz=md["fd_edge_hz"],dc_ac_db=md["dc_ac_db"],f_tip_hz=ft)
out=[]
for key in ("matrice4e","mini2"):
    spec=drones.DRONES[key]
    laws=["legacy","dji_mini2",grad_law("g0",0.,spec),grad_law("g2",2.,spec)]
    for el in (-30.,-60.):
        base=None
        for pl in laws:
            r=run(spec,pl,el); r.update(drone=key,el=el)
            if base is None: base=r
            r["d_contrast_db"]=r["flash_contrast_db"]-base["flash_contrast_db"]
            r["d_peak_db"]=r["peak_dbsm"]-base["peak_dbsm"]
            out.append(r)
            print(f"{key:10s} el{el:+5.0f} {pl:10s} peak {r['peak_dbsm']:7.2f} "
                  f"contrast {r['flash_contrast_db']:6.2f} (Δ{r['d_contrast_db']:+5.2f}) "
                  f"harm {r['harmonic_frac']:.4f} fd_edge {r['fd_edge_hz']:8.1f}/{r['f_tip_hz']:.0f}",flush=True)
json.dump(out,open("pitch_spec.json","w"),indent=1)
