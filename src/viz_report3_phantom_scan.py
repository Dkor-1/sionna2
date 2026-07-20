# -*- coding: utf-8 -*-
"""viz_report3_phantom_scan.py — report03: 실측 스캔 vs 우리 mesh 직접 비교(결과만).

가장 깨끗한 검증 — 우리 타깃 기체 **DJI Phantom 4** 를, 실물 0.4mm 3D 스캔
(Thingiverse thing:1456295, CC-BY NeverDun)과 **같은 조건(둘 다 PEC, 형상만)**으로
직접 비교한다. 다운로드 원본 → 스캔에 대응하는 파트만(프롭·짐벌 제외) 우리 mesh 제작 → 비교.
그림엔 과정이 아니라 **결과**만: 원본(점구름) vs 우리(mesh) + σ·투영면적 일치도.
출력: outputs/figures/report03_phantom_scan.png (그림 텍스트 영어 규약)
"""
from __future__ import annotations
import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from drones import DRONES, build_drone   # noqa: E402

OUT = os.path.join(ROOT, "outputs", "figures", "report03_phantom_scan.png")
R = json.load(open(os.path.join(ROOT, "outputs", "phantom4_scan_compare.json")))
SCAN = np.load(os.path.join(ROOT, "assets", "meshes", "cad", "phantom4_scan_points.npz"))

C_OURS = (0.30, 0.50, 0.85)

def _our_phantom():
    m = build_drone(DRONES["phantom4"])
    V = np.asarray(m.v, float); F = np.asarray(m.f)
    keep = np.array([g not in ("prop", "camera") for g in m.g])
    fk = F[keep]; used = np.unique(fk); remap = {o: n for n, o in enumerate(used)}
    Vk = V[used]; Fk = np.vectorize(remap.get)(fk)
    Vk = Vk - (Vk.max(0) + Vk.min(0)) / 2
    return Vk, Fk

fig = plt.figure(figsize=(13.5, 4.6), dpi=130)
# (1) 원본 스캔 — 점구름(높이색)
P = SCAN["P"].astype(float); P = P - (P.max(0) + P.min(0)) / 2
lim = float(np.abs(P).max()) * 1.02
a1 = fig.add_subplot(1, 3, 1, projection="3d")
a1.scatter(P[:, 0], P[:, 1], P[:, 2], c=P[:, 2], cmap="viridis", s=1.2, alpha=0.85, linewidths=0)
a1.set_xlim(-lim, lim); a1.set_ylim(-lim, lim); a1.set_zlim(-lim*0.6, lim*0.6)
a1.set_box_aspect((1, 1, 0.6)); a1.view_init(22, -58); a1.set_axis_off()
a1.set_title("Real 3D scan (downloaded)\nDJI Phantom 4 · 0.4 mm · CC-BY", fontsize=10.5, fontweight="bold")

# (2) 우리 mesh(대응 파트만: 프롭·짐벌 제외)
Vk, Fk = _our_phantom()
tris = Vk[Fk]
nrm = np.cross(tris[:, 1]-tris[:, 0], tris[:, 2]-tris[:, 0]); ln = np.linalg.norm(nrm, axis=1, keepdims=True); ln[ln < 1e-9] = 1
sh = 0.5 + 0.5*np.clip(nrm[:, 2:3]/ln*0.6+0.5, 0, 1); fc = np.clip(np.array(C_OURS)[None, :]*sh, 0, 1)
lim2 = float(np.abs(Vk).max())*1.02
a2 = fig.add_subplot(1, 3, 2, projection="3d")
a2.add_collection3d(Poly3DCollection(tris, facecolors=fc, edgecolors="none"))
a2.set_xlim(-lim2, lim2); a2.set_ylim(-lim2, lim2); a2.set_zlim(-lim2*0.6, lim2*0.6)
a2.set_box_aspect((1, 1, 0.6)); a2.view_init(22, -58); a2.set_axis_off()
a2.set_title("Our mesh (from spec sheet)\nmatched parts: no props / no gimbal", fontsize=10.5,
             fontweight="bold", color=(0.20, 0.34, 0.60))

# (3) 결과 — 일치도 막대
a3 = fig.add_subplot(1, 3, 3)
labels = ["Δ projected\narea", "Δ mean σ\n(PEC)"]
vals = [R["d_area_db"], R["d_sigma_db"]]
cols = ["#2e7d32" if abs(v) <= 1.0 else "#e08e0b" for v in vals]
a3.axhspan(-1, 1, color="#2e7d32", alpha=0.12, label="±1 dB")
a3.axhline(0, color="0.4", lw=0.8)
b = a3.bar(labels, vals, color=cols, edgecolor="0.3", width=0.55)
for bb, v in zip(b, vals):
    a3.text(bb.get_x()+bb.get_width()/2, v+(0.06 if v >= 0 else -0.10), f"{v:+.2f} dB",
            ha="center", va="bottom" if v >= 0 else "top", fontsize=11, fontweight="bold")
a3.set_ylim(-2.0, 2.0); a3.set_ylabel("ours − scan  [dB]", fontsize=9.5)
a3.set_title(f"Shape match to the real scan\nper-azimuth RMS = {R['d_sigma_rms_db']:.1f} dB (nulls, not citable)",
             fontsize=10.5, fontweight="bold")
a3.grid(axis="y", alpha=0.25); a3.legend(fontsize=8, loc="upper right")

fig.suptitle("Our Phantom 4 mesh vs a real 0.4 mm scan — same drone, both PEC, shape only",
             fontsize=13, fontweight="bold", y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUT, dpi=130, bbox_inches="tight", facecolor="white"); plt.close(fig)
print(f"✅ {os.path.relpath(OUT)}")
