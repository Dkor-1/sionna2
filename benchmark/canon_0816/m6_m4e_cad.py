# -*- coding: utf-8 -*-
"""6단계 — matrice4e: 공식 CAD 랜드마크(meshfix_matrice4e.json) ↔ **지금 지어지는 메쉬**."""
import json, sys
import numpy as np
import trimesh
sys.path.insert(0, "/workspace/sionna/src")
import drones as D
import drone_cad as DC

SCR = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad"
spec = D.DRONES["matrice4e"]
raw = D._build_frame_raw(spec)
V = np.asarray(raw.v, float) * 1000
F = np.asarray(raw.f, int)
G = np.asarray(raw.g, object)


def gsel(*groups):
    return F[np.isin(G, list(groups))]


def parts(faces):
    tm = trimesh.Trimesh(vertices=V / 1000.0, faces=faces, process=True, validate=False)
    return list(tm.split(only_watertight=False, repair=False))


out = {}
# ── 셸(body 그룹은 셸+암 합집합) — 중심선 근처만 보면 셸이다
body = trimesh.Trimesh(vertices=V / 1000.0, faces=gsel("body"), process=True, validate=False)
BV = np.asarray(body.vertices) * 1000
mid = np.abs(BV[:, 1]) < 20.0            # |y| < 20 mm — 암은 이 띠에 없다
out["shell_centreband"] = dict(
    x_min=round(float(BV[mid, 0].min()), 2), x_max=round(float(BV[mid, 0].max()), 2),
    z_min=round(float(BV[mid, 2].min()), 2), z_max=round(float(BV[mid, 2].max()), 2))
out["shell_centre_x"] = round((float(BV[mid, 0].min()) + float(BV[mid, 0].max())) / 2, 2)

# ── 다리(gear) — 최저점(발) 과 그 반경
gp = parts(gsel("gear"))
feet = []
for c in gp:
    P = np.asarray(c.vertices) * 1000
    zt = P[:, 2].min()
    tip = P[P[:, 2] < zt + 1.0]
    cx, cy = float(tip[:, 0].mean()), float(tip[:, 1].mean())
    root = P[P[:, 2] > P[:, 2].max() - 1.0]
    feet.append(dict(z_foot=round(float(zt), 2),
                     r_foot=round(float(np.hypot(cx, cy)), 2),
                     d_tip=round(float(max(tip[:, 0].max() - tip[:, 0].min(),
                                           tip[:, 1].max() - tip[:, 1].min())), 2),
                     r_root=round(float(np.hypot(root[:, 0].mean(), root[:, 1].mean())), 2),
                     d_root=round(float(max(root[:, 0].max() - root[:, 0].min(),
                                            root[:, 1].max() - root[:, 1].min())), 2),
                     z_root=round(float(P[:, 2].max()), 2)))
out["gear"] = feet

# ── 모터 벨
mp = parts(gsel("motor"))
bells = []
for c in mp:
    P = np.asarray(c.vertices) * 1000
    cx, cy = P[:, 0].mean(), P[:, 1].mean()
    bells.append(dict(r=round(float(np.hypot(cx, cy)), 2), x=round(float(cx), 2), y=round(float(cy), 2),
                      z=[round(float(P[:, 2].min()), 2), round(float(P[:, 2].max()), 2)],
                      d=round(float(P[:, 0].max() - P[:, 0].min()), 2)))
out["motor_bells"] = sorted(bells, key=lambda b: -b["x"])

# ── RTK / 캐노피
cp = parts(gsel("canopy"))
out["canopy_parts"] = [dict(z=[round(float(np.asarray(c.vertices)[:, 2].min() * 1000), 2),
                              round(float(np.asarray(c.vertices)[:, 2].max() * 1000), 2)],
                            x=[round(float(np.asarray(c.vertices)[:, 0].min() * 1000), 2),
                               round(float(np.asarray(c.vertices)[:, 0].max() * 1000), 2)],
                            d=round(float((np.asarray(c.vertices)[:, 1].max()
                                           - np.asarray(c.vertices)[:, 1].min()) * 1000), 2))
                       for c in cp]

# ── 프롭 장착 z (rotor_layout, raw = fit 전으로 환산)
sz = D.frame_fit_scale(spec)[2]
rl = D.rotor_layout(spec)
out["prop_mount_z_mm_raw"] = [round(float(r["center"][2]) * 1000 / sz, 3) for r in rl]
out["fit_sz"] = round(float(sz), 6)

# ── CAD 랜드마크
cad = json.load(open("/workspace/sionna/outputs/meshfix_matrice4e.json"))["datum"]["cad_landmarks_in_our_frame_mm"]
out["cad_landmarks"] = cad
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open(f"{SCR}/m6_m4e.json", "w"), ensure_ascii=False, indent=1)
