#!/usr/bin/env python
"""적대검증 2부 — 1부에서 드러난 의심을 끝까지 판다.

  (a) 크래들 상자를 x=118 로 잘라도 셸 삼각형이 남는가
  (b) mini5pro 프롭이 «벨 솔리드 안» 에 있다는 526/313 을 반경까지 넣어 다시 센다
  (c) 엔진의 다리 기하 — GEAR_SPIKE_H 의 기준면과 발끝 구 반지름을 직접 잰다
      (ground 의 항등식 «h = L_cad + 뿌리오프셋 − 4.7» 이 동어반복인지 판정하려면 필요하다)
  (d) mini2 GLB 를 내가 직접 열어 벨리 렌즈 y 를 잰다 — 새 상수 0.102796 의 근거 7.1999 검증

⛔ 소스 무편집 · GPU 무사용.
"""
from __future__ import annotations
import hashlib, json, os, sys, time

ROOT = "/home/yunjung/workspace/sionna2"
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "benchmark"))
sys.path.insert(0, ROOT)
os.environ.setdefault("SIONNA2_NO_GPU", "1"); os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np                      # noqa: E402
import drone_cad as dc                  # noqa: E402
import drones as dr                     # noqa: E402

R = lambda x, n=4: round(float(x), n)    # noqa: E731
T0 = time.time()
GUARD = lambda: {p: hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()[:16]
                 for p in ("src/drones.py", "src/drone_cad.py")}          # noqa: E731
G_IN = GUARD()
OUT = {}

CRADLE = dict(x=(71.59, 146.34), y=(-31.55, 31.55), z=(-17.19, 0.93))


# (a) 잘린 상자에도 셸이 남는가 ────────────────────────────────────────────────
def a_cut_box():
    m = dr.build_frame(dr.DRONES["matrice4e"])
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64); G = np.asarray(m.g); C = V[F].mean(1)
    res = {}
    for tag, xmax in (("as_proposed_146.34", 146.34), ("doc_ruling_118", 118.0),
                      ("real_gimbal_edge_122.3", 122.3), ("shell_vertex_edge_128", 128.0)):
        box = ((C[:, 0] >= CRADLE["x"][0]) & (C[:, 0] <= xmax)
               & (C[:, 1] >= CRADLE["y"][0]) & (C[:, 1] <= CRADLE["y"][1])
               & (C[:, 2] >= CRADLE["z"][0]) & (C[:, 2] <= CRADLE["z"][1]))
        res[tag] = dict(body=int(((G == "body") & box).sum()),
                        camera=int(((G == "camera") & box).sum()),
                        total=int(box.sum()))
    # 셸 배가 상자 지붕(0.93) 아래로 처음 내려가는 x
    xs = []
    for x0 in range(60, 170, 2):
        sel = (G == "body") & (C[:, 0] >= x0) & (C[:, 0] < x0 + 2) & (abs(C[:, 1]) <= 26.0)
        if sel.sum():
            vz = V[np.unique(F[sel])][:, 2]
            xs.append(dict(x=x0, vmin=R(vz.min(), 2), below_roof=bool(vz.min() < CRADLE["z"][0]),
                           below_boxtop=bool(vz.min() < CRADLE["z"][1])))
    first_below_roof = next((r["x"] for r in xs if r["below_roof"]), None)
    return dict(counts=res, first_x_shell_vertex_below_cradle_roof_mm=first_below_roof,
                fine_profile=xs)


# (b) mini5pro 프롭 ↔ 벨 솔리드 겹침 ───────────────────────────────────────────
def b_prop_in_bell():
    out = {}
    for key in ("mini5pro", "matrice4e"):
        s = dr.DRONES[key]
        m = dr.build_drone(s)
        V = np.asarray(m.v, float) * 1000.0
        G = np.asarray(m.g); F = np.asarray(m.f, np.int64)
        mot = V[np.unique(F[G == "motor"])]
        lay = dr.rotor_layout(s)
        rows = []
        tot_v = tot_t = 0
        for k, r in enumerate(lay):
            cx, cy = r["center"][0] * 1000.0, r["center"][1] * 1000.0
            near = (np.hypot(mot[:, 0] - cx, mot[:, 1] - cy) < 40.0)
            if not near.any():
                continue
            bm = mot[near]
            rad = float(np.hypot(bm[:, 0] - cx, bm[:, 1] - cy).max())
            zlo, zhi = float(bm[:, 2].min()), float(bm[:, 2].max())
            pv_idx = np.unique(F[G == "prop"])
            PV = V[pv_idx]
            inv = ((np.hypot(PV[:, 0] - cx, PV[:, 1] - cy) <= rad)
                   & (PV[:, 2] >= zlo) & (PV[:, 2] <= zhi))
            Fp = F[G == "prop"]
            Cp = V[Fp].mean(1)
            int_ = ((np.hypot(Cp[:, 0] - cx, Cp[:, 1] - cy) <= rad)
                    & (Cp[:, 2] >= zlo) & (Cp[:, 2] <= zhi))
            rows.append(dict(rotor=k, center_xy_mm=[R(cx, 2), R(cy, 2)], bell_r_mm=R(rad, 3),
                             bell_z_mm=[R(zlo, 3), R(zhi, 3)],
                             prop_verts_in_bell=int(inv.sum()), prop_tris_in_bell=int(int_.sum())))
            tot_v += int(inv.sum()); tot_t += int(int_.sum())
        out[key] = dict(per_rotor=rows, total_verts_in_bell=tot_v, total_tris_in_bell=tot_t)
    return out


# (c) 엔진 다리 기하 — GEAR_SPIKE_H 의 기준면과 발끝 구 ────────────────────────
def c_gear_geometry():
    s = dr.DRONES["matrice4e"]
    old = dc.GEAR_SPIKE_H["matrice4e"]
    rows = {}
    for h_mm in (52.9, 50.05, 45.0, 60.0):
        dc.GEAR_SPIKE_H["matrice4e"] = h_mm / 1000.0; dr._FIT_CACHE.clear()
        m = dr._build_frame_raw(s)
        V = np.asarray(m.v, float) * 1000.0
        G = np.asarray(m.g); F = np.asarray(m.f, np.int64)
        gv = V[np.unique(F[G == "gear"])]
        rows[f"h={h_mm}"] = dict(frame_zmin_mm=R(V[:, 2].min(), 4), gear_zmin_mm=R(gv[:, 2].min(), 4),
                                 gear_zmax_mm=R(gv[:, 2].max(), 4))
    dc.GEAR_SPIKE_H["matrice4e"] = old; dr._FIT_CACHE.clear()
    hs = [52.9, 50.05, 45.0, 60.0]
    zs = [rows[f"h={h}"]["frame_zmin_mm"] for h in hs]
    slope = (zs[3] - zs[2]) / (hs[3] - hs[2])
    const = zs[0] - slope * hs[0]
    return dict(rows=rows, d_framezmin_per_mm_h=R(slope, 6), intercept_mm=R(const, 4),
                ko="frame 바닥 = slope·h + intercept. intercept 는 «암 평면 → 스파이크 부착점 "
                   "− 발끝 구 반지름» 의 합이다. ground 의 '뿌리 오프셋 7.4175' 가 독립 측정인지 "
                   "잔차인지 이 값으로 가른다.")


# (d) mini2 GLB 를 내가 직접 열어 벨리 렌즈를 잰다 ─────────────────────────────
def d_mini2_glb():
    import trimesh
    p = os.path.join(ROOT, "assets/meshes/reference/WM161_zhankai_1k.glb")
    md5 = hashlib.md5(open(p, "rb").read()).hexdigest()
    sc = trimesh.load(p, force="scene")
    # 씬 전체를 월드로 굽고 mini2 라운드가 선언한 축 사상으로 옮긴다: X=z, Y=x, Z=y (×1000)
    parts = {}
    for name, geom in sc.geometry.items():
        parts[name] = geom
    tf = {}
    for node in sc.graph.nodes_geometry:
        T, gname = sc.graph[node]
        Vv = np.asarray(parts[gname].vertices, float)
        Vw = (T[:3, :3] @ Vv.T).T + T[:3, 3]
        P = np.stack([Vw[:, 2], Vw[:, 0], Vw[:, 1]], 1) * 1000.0     # X=z, Y=x, Z=y
        tf[node] = P
    allv = np.concatenate(list(tf.values()))
    # 프롭 제외 bbox (mini2 라운드 선언 파트명)
    prop_names = {"polySurface58", "polySurface61", "polySurface80", "polySurface81",
                  "polySurface84", "polySurface89", "polySurface95", "polySurface102"}
    nonprop = np.concatenate([v for k, v in tf.items()
                              if not any(pn in k for pn in prop_names)])
    ext = nonprop.max(0) - nonprop.min(0)
    # 벨리(아래쪽) 파트 중 좌우로 갈라진 작은 렌즈 후보를 찾는다
    zlo = nonprop[:, 2].min()
    cands = []
    for k, v in tf.items():
        if any(pn in k for pn in prop_names):
            continue
        lo, hi = v.min(0), v.max(0)
        span = hi - lo
        cy = (lo[1] + hi[1]) / 2.0
        if hi[2] < zlo + 25.0 and max(span) < 30.0 and abs(cy) > 2.0:
            cands.append(dict(node=k, n_v=int(len(v)), bbox_lo=[R(x, 3) for x in lo],
                              bbox_hi=[R(x, 3) for x in hi], centre=[R(x, 4) for x in (lo + hi) / 2]))
    cands = sorted(cands, key=lambda c: (c["centre"][2], -abs(c["centre"][1])))
    return dict(md5=md5, n_nodes=len(tf), nonprop_bbox_mm=[R(x, 5) for x in ext],
                nonprop_z_min_mm=R(zlo, 4), belly_lens_candidates=cands[:24])


for nm, fn in (("a_cut_box", a_cut_box), ("b_prop_in_bell", b_prop_in_bell),
               ("c_gear_geometry", c_gear_geometry), ("d_mini2_glb", d_mini2_glb)):
    t = time.time(); OUT[nm] = fn(); print(f"[{nm}] {time.time()-t:.1f}s", flush=True)

G_OUT = GUARD()
OUT["_meta"] = dict(generator="benchmark/meshdef_attack_verify2.py",
                    generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    source_guard_in=G_IN, source_guard_out=G_OUT,
                    sources_unchanged=(G_IN == G_OUT), gpu="사용 안 함",
                    elapsed_s=round(time.time() - T0, 1))
p = os.path.join(ROOT, "outputs/meshdef_attack_raw2.json")
json.dump(OUT, open(p, "w"), ensure_ascii=False, indent=1)
print("wrote", p, "unchanged=", OUT["_meta"]["sources_unchanged"])
