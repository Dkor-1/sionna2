import numpy as np, json, sys
sys.path.insert(0,'/workspace/sionna/src')
import drones as DR
GRID=np.round(np.arange(0.10,0.995,0.01),3)
def cal(V,F,X):
    tri=V[F]; d=tri[:,:,0]-X
    hit=~(np.all(d>0,axis=1)|np.all(d<0,axis=1)); tri,d=tri[hit],d[hit]
    if len(tri)==0: return 0.0
    pts=[]
    for k in range(3):
        a,b=k,(k+1)%3; da,db=d[:,a],d[:,b]; cr=(da*db)<0
        if np.any(cr):
            t=(da[cr]/(da[cr]-db[cr]))[:,None]
            pts.append(tri[cr,a,1:]+t*(tri[cr,b,1:]-tri[cr,a,1:]))
        on=np.abs(da)<1e-15
        if np.any(on): pts.append(tri[on,a,1:])
    if not pts: return 0.0
    P=np.vstack(pts)
    from scipy.spatial import ConvexHull
    if len(P)>3:
        try: P=P[ConvexHull(P).vertices]
        except Exception: pass
    D=np.linalg.norm(P[:,None,:]-P[None,:,:],axis=-1)
    return float(D.max())*1000.
LAW=json.load(open('/workspace/sionna/outputs/prop_law_by_airframe_0816.json'))['C_law_by_airframe']
for key in ['mini2','phantom3','matrice4e']:
    spec=DR.DRONES[key]; R=spec.prop_dia_mm/2000.
    m=DR.build_propeller(spec, blade_law='per_airframe')
    V=np.asarray(m.v,float); F=np.asarray(m.f,np.int64)
    xspan=V[:,0].max()
    print(key,'R_nom mm',round(R*1000,2),'x_span mm',round(xspan*1000,2),'ratio',round(xspan/R,5))
    want=np.interp(GRID,LAW[key]['chord_rr'],LAW[key]['chord_frac']); want/=want.max()
    band=GRID<=0.96
    for base,lab in ((R,'R_nom'),(xspan,'x_span')):
        c=np.array([cal(V,F,rr*base) for rr in GRID]); n=c/c.max()
        dev=np.abs(n[band]/want[band]-1)*100; i=int(np.argmax(dev))
        g=GRID[band]
        print(f'   {lab}: max {dev.max():.2f}% @r/R={g[i]}   0.15:{dev[g==0.15][0]:.1f} 0.2:{dev[g==0.2][0]:.1f} 0.3:{dev[g==0.3][0]:.1f} 0.5:{dev[g==0.5][0]:.1f} 0.7:{dev[g==0.7][0]:.1f} 0.9:{dev[g==0.9][0]:.1f} 0.96:{dev[g==0.96][0]:.1f}')
