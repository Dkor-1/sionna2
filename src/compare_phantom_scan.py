# -*- coding: utf-8 -*-
"""compare_phantom_scan.py — report03: DJI Phantom 4 실물 0.4mm 스캔 vs 우리 파라메트릭 메쉬.

다운로드 원본(스캔) → 스캔에 대응하는 파트만(프롭·짐벌 제외) 우리 방식으로 제작 → 둘 다 PEC 로
형상만 비교(SBR σ + 투영면적). 결과 → outputs/phantom4_scan_compare.json.
스캔 STL(154MB)은 저장소에 없다 — prep_cad_scan.py docstring 의 archive.org 미러에서 내려받는다
(Thingiverse thing:1456295, CC-BY NeverDun). 그림은 viz_report3_phantom_scan.py.
"""

import os, sys, numpy as np
sys.path.insert(0, "src")
os.environ.setdefault("SIONNA2_GPU", "0")
import trimesh
from mesh_compare import compare
from drones import DRONES, build_drone
from geom import Mesh as GMesh

STL = ("/tmp/claude-1015/-workspace/b16ec570-b204-4255-9c8a-da23fd2adf6d/"
       "scratchpad/cad/phantom4_scan/files/DJIPHANTOM4_.3MM.stl")
SCALE = 1.0125/1000.0   # mm→m + 휠베이스 보정(345.7→350mm)

print("스캔 로드…(154MB)")
scan = trimesh.load(STL, force="mesh")
print(f"  원본 {len(scan.faces):,} tris")
scan.apply_scale(SCALE)
# PCA z-up 정렬(최소분산축=z, 다리 아래로)
V = np.asarray(scan.vertices); c = V.mean(0)
cov = np.cov((V-c).T); w,Q = np.linalg.eigh(cov)
zax = Q[:, np.argmin(w)]                      # 최소분산=납작한 축=z
R = np.eye(4); R[:3,:3] = Q[:, np.argsort(-w)].T  # 큰축→x,y; 작은축→z
scan.apply_transform(R)
scan.apply_translation(-scan.bounds.mean(0))
# 다리가 아래(-z)로 가도록 부호: z-분포 하단이 더 넓으면(다리) OK, 아니면 뒤집기
Vz = np.asarray(scan.vertices)
if np.median(Vz[Vz[:,2]<0][:,0].std()) < Vz[Vz[:,2]>0][:,0].std():
    pass
# 표시·계산용 축소(quadric)
if len(scan.faces) > 120000:
    try: scan = scan.simplify_quadric_decimation(120000); print(f"  축소 {len(scan.faces):,} tris")
    except Exception as e: print("  decimate 실패:", e)
scan.merge_vertices(); scan.update_faces(scan.nondegenerate_faces())

# 우리 Phantom mesh — 스캔에 맞춰 프롭·짐벌 제외(스캔엔 없음)
m = build_drone(DRONES["phantom4"])
keep = [i for i,g in enumerate(m.g) if g not in ("prop","camera")]
V = np.asarray(m.v, float); F = np.asarray(m.f)
fk = F[keep]
used = np.unique(fk); remap = {o:n for n,o in enumerate(used)}
ours = trimesh.Trimesh(vertices=V[used], faces=np.vectorize(remap.get)(fk), process=False)
ours.apply_translation(-ours.bounds.mean(0))
print(f"우리 Phantom(프롭·짐벌 제외) {len(ours.faces):,} tris")
print(f"스캔 bbox(mm): {np.round((scan.bounds[1]-scan.bounds[0])*1000,1)}  ours: {np.round((ours.bounds[1]-ours.bounds[0])*1000,1)}")

# 비교(둘 다 PEC, 형상만) — n_az 48
print("σ 비교(SBR, both PEC)…")
res = compare(scan, ours, fc=3.5e9, el=15.0, n_az=48,
              name_real="Phantom 4 real scan (0.4mm)", name_ours="ours (from spec)")
import json
json.dump(res, open("outputs/phantom4_scan_compare.json","w"), ensure_ascii=False, indent=1)
print(f"\n결과: Δσ={res['d_sigma_db']:+.2f} dB · ΔArea={res['d_area_db']:+.2f} dB · "
      f"per-az RMS={res['d_sigma_rms_db']:.1f} dB")
print(f"  scan σ={res['sigma_mean_real_dbsm']:.1f} dBsm · ours σ={res['sigma_mean_ours_dbsm']:.1f} dBsm")
# 오버레이용 메쉬 저장(축소본)
scan.export("outputs/phantom4_scan_decim.ply")
ours.export("outputs/phantom4_ours_noprops.ply")
print("✅ JSON + 오버레이 메쉬 저장")
