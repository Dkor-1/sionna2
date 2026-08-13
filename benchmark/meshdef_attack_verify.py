#!/usr/bin/env python
"""적대검증 — 「메쉬 결함 통합 패치 명세」(docs/MESH_DEFECTS.md · outputs/meshdef_spec.json)를
   내 손으로 다시 재서 반증을 시도한다.

⛔ 규율
  - src/drones.py · src/drone_cad.py 를 **편집하지 않는다**. 필요한 경우 파이썬 메모리 안에서만
    잠깐 갈아끼우고(monkeypatch) 즉시 원복한다. 시작·종료 해시를 둘 다 찍는다.
  - GPU 를 쓰지 않는다(전부 CPU).
  - outputs/report00_* · report15_* · report16_* 를 건드리지 않는다. 새로 쓰는 것은 meshdef_* 뿐이다.

내는 것: outputs/meshdef_attack_raw.json  (판정은 별도 스크립트가 붙인다)
"""
from __future__ import annotations
import hashlib, json, os, sys, time

ROOT = "/workspace/sionna"
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
sys.path.insert(0, ROOT)
os.environ.setdefault("SIONNA2_NO_GPU", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")     # ⛔ GPU3 근처에도 안 간다

import numpy as np                       # noqa: E402
import drone_cad as dc                   # noqa: E402
import drones as dr                      # noqa: E402

T0 = time.time()
R = lambda x, n=4: round(float(x), n)     # noqa: E731
SPEC = json.load(open(os.path.join(ROOT, "outputs/meshdef_spec.json")))


def fhash(p):
    return hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()[:16]


GUARD_FILES = ("src/drones.py", "src/drone_cad.py", "src/geom.py")
GUARD_IN = {p: fhash(p) for p in GUARD_FILES}


def mesh_sha(m):
    V = np.asarray(m.v, float); F = np.asarray(m.f, np.int64)
    h = hashlib.sha256(np.ascontiguousarray(np.round(V, 9)).tobytes())
    h.update(np.ascontiguousarray(F).tobytes())
    return h.hexdigest()[:16]


OUT: dict = {}

# ══════════════════════════════════════════════════════════════════════════════
# Q2-a  기준선 지문을 내가 다시 만든다 — 명세의 baseline_fingerprints 가 진짜인가
# ══════════════════════════════════════════════════════════════════════════════
def q2_baseline():
    rows = {}
    for k, s in dr.DRONES.items():
        d, f, p = dr.build_drone(s), dr.build_frame(s), dr.build_propeller(s)
        V = np.asarray(d.v, float) * 1000.0
        G = np.asarray(d.g); Fi = np.asarray(d.f, np.int64)
        pv = V[np.unique(Fi[G == "prop"])]
        mine = dict(drone_sha16=mesh_sha(d), frame_sha16=mesh_sha(f), prop_sha16=mesh_sha(p),
                    n_v=int(len(d.v)), n_f=int(len(d.f)),
                    fit_scale=[round(float(x), 9) for x in dr.frame_fit_scale(s)],
                    prop_group_centroid_z_mm=R(pv[:, 2].mean()))
        theirs = SPEC["baseline_fingerprints"][k]
        diff = {a: [mine[a], theirs.get(a)] for a in mine if mine[a] != theirs.get(a)}
        rows[k] = dict(mine=mine, matches=(not diff), diff=diff)
    return dict(n_drones=len(rows), all_match=all(v["matches"] for v in rows.values()), rows=rows)


# ══════════════════════════════════════════════════════════════════════════════
# Q3  접지 기준 — 「직접측정을 쓰면 sz = 1.019 로 돌아간다」가 정말인가.
#     GEAR_SPIKE_H 를 가설별로 메모리에서만 갈아끼워 frame_fit_scale 을 직접 푼다.
# ══════════════════════════════════════════════════════════════════════════════
def q3_fit_scale():
    s = dr.DRONES["matrice4e"]
    old = dc.GEAR_SPIKE_H["matrice4e"]
    hyp = {
        "A_현채택_역산_52.9":          0.0529,
        "B_직접측정_평균_50.05":       0.050050,      # ground 표의 h_mm 그대로
        "B2_직접측정_평균_50.0796":    0.0500796,     # ground 가 실제로 잰 평균
        "C_직접측정_앞다리_54.753":    0.054753,
        "D_직접측정_뒷다리_45.407":    0.045407,
        "F_뿌리오프셋포함_앞발_52.904": 0.0529042,
        "F_뿌리오프셋포함_평균_52.797": 0.0527972,
        "E_수정전옛값_79.0":           0.079,
    }
    rows = {}
    for lbl, h in hyp.items():
        dc.GEAR_SPIKE_H["matrice4e"] = h; dr._FIT_CACHE.clear()
        Vr = np.asarray(dr._build_frame_raw(s).v, float) * 1000.0
        sz = float(dr.frame_fit_scale(s)[2])
        rows[lbl] = dict(spike_h_mm=R(h * 1000, 4), raw_zmin_mm=R(Vr[:, 2].min(), 4),
                         raw_zmax_mm=R(Vr[:, 2].max(), 4),
                         raw_h_mm=R(Vr[:, 2].max() - Vr[:, 2].min(), 4),
                         env_h_mm=float(s.envelope_mm[2]), fit_sz=round(sz, 6),
                         forcing_pct=R((1.0 / sz - 1.0) * 100.0, 4))
    dc.GEAR_SPIKE_H["matrice4e"] = old; dr._FIT_CACHE.clear()
    # 되돌아왔는지 확인
    rows["_restored_sz"] = round(float(dr.frame_fit_scale(s)[2]), 9)
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# Q2-b / X1  크래들 상자 다툼 — 「짐벌이 x=117.62 에서 시작한다」가 상자와 진짜 겹치는가.
#            bbox 최소 x 가 아니라 **상자와 실제로 교차하는 파트**를 따로 센다.
# ══════════════════════════════════════════════════════════════════════════════
CRADLE = dict(x=(71.59, 146.34), y=(-31.55, 31.55), z=(-17.19, 0.93))


def q2_cradle():
    m = dr.build_frame(dr.DRONES["matrice4e"])
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64); G = np.asarray(m.g); C = V[F].mean(1)
    inbox = ((C[:, 0] >= CRADLE["x"][0]) & (C[:, 0] <= CRADLE["x"][1])
             & (C[:, 1] >= CRADLE["y"][0]) & (C[:, 1] <= CRADLE["y"][1])
             & (C[:, 2] >= CRADLE["z"][0]) & (C[:, 2] <= CRADLE["z"][1]))
    gim = (G == "camera") & (C[:, 0] > 110) & (C[:, 2] < 30)          # 명세의 짐벌 선택자
    down = (G == "camera") & (C[:, 0] > 70) & (C[:, 0] < 100) & (C[:, 2] < 0)
    gv = V[np.unique(F[gim])]

    # 짐벌 helper 의 네 파트를 개별로 재서, 어느 파트가 상자와 **정말** 겹치는지 본다
    A = dc._gimbal_sensor_v2(0.059, 0.047, 0.052, 0.1483, -0.01716)   # 현행 인자
    names = ["yoke_cyl", "damper_plate", "block_upper", "block_lower"]
    parts = {}
    for nm, (_g, tm) in zip(names, A):
        P = np.asarray(tm.vertices, float) * 1000.0
        lo, hi = P.min(0), P.max(0)
        ov = all(hi[i] >= CRADLE["xyz"[i]][0] and lo[i] <= CRADLE["xyz"[i]][1] for i in range(3))
        parts[nm] = dict(bbox_mm=[R(x, 2) for x in lo] + [R(x, 2) for x in hi],
                         overlaps_cradle_box=bool(ov))
    first_overlapping_x = min((p["bbox_mm"][0] for p in parts.values()
                               if p["overlaps_cradle_box"]), default=None)
    return dict(
        gimbal_selector_bbox_min_x_mm=R(gv[:, 0].min(), 2),
        gimbal_parts=parts,
        first_overlapping_part_min_x_mm=first_overlapping_x,
        tris_inbox_body=int(((G == "body") & inbox).sum()),
        tris_inbox_camera_total=int(((G == "camera") & inbox).sum()),
        tris_inbox_camera_gimbal_only=int((gim & inbox).sum()),
        tris_inbox_camera_downpair=int((down & inbox).sum()),
        tris_inbox_all=int(inbox.sum()),
        ko="짐벌 조립체 bbox 최소 x 는 117.62 지만, 크래들 상자와 z 로 정말 겹치는 파트는 "
           "block_upper 하나뿐이다. 그 파트의 최소 x 가 진짜 경계다.")


# ══════════════════════════════════════════════════════════════════════════════
# Q3-b / X2  「반지름만 줄이면 8.77 → 13.37 로 나빠진다」를 다시 재고,
#            그 지표가 결함을 재는 지표로 타당한지 반증한다(반지름 스윕).
# ══════════════════════════════════════════════════════════════════════════════
def q3_fisheye():
    from scipy.spatial import cKDTree
    _fe = dc._fisheye

    def build(fz=None, fr=None):
        def fe(cx, cy, cz, r, axis="x"):
            if abs(cz - (-0.0191)) < 1e-9:
                if fz is not None: cz = fz
                if fr is not None: r = fr
            return _fe(cx, cy, cz, r, axis)
        dc._fisheye = fe if (fz is not None or fr is not None) else _fe
        dr._FIT_CACHE.clear()
        m = dr.build_frame(dr.DRONES["matrice4e"])
        dc._fisheye = _fe; dr._FIT_CACHE.clear()
        return m

    def metric(m):
        V = np.asarray(m.v, float) * 1000.0
        F = np.asarray(m.f, np.int64); G = np.asarray(m.g); C = V[F].mean(1)
        down = (G == "camera") & (C[:, 0] > 70) & (C[:, 0] < 100) & (C[:, 2] < 0)
        P = V[F[~down]]
        S = np.concatenate([P.reshape(-1, 3), P.mean(1),
                            (P[:, 0] + P[:, 1]) / 2, (P[:, 1] + P[:, 2]) / 2, (P[:, 0] + P[:, 2]) / 2])
        dv = V[np.unique(F[down])]
        d, _ = cKDTree(S).query(dv)
        ctr = dv.mean(0)
        dc_, _ = cKDTree(S).query(ctr[None, :])
        return R(d.min()), R(float(dc_[0])), [R(x, 2) for x in dv.min(0)] + [R(x, 2) for x in dv.max(0)]

    rows = {}
    base_r, base_z = 0.009, -0.0191
    rows["baseline r9.0 z-19.1"] = metric(build())
    for r_mm in (8.0, 7.0, 6.0, 5.6, 4.3, 3.0, 2.0, 1.0):
        rows[f"r{r_mm} only"] = metric(build(fr=r_mm / 1000.0))
    rows["z-13.64 only"] = metric(build(fz=-0.01364))
    rows["z-13.64 + r4.3"] = metric(build(fz=-0.01364, fr=0.0043))
    return dict(columns=["min_dist_vertex_to_rest_mm", "dist_center_to_rest_mm", "downpair_bbox_mm"],
                rows=rows,
                ko="반지름을 줄일수록 «정점→나머지» 최단거리가 단조 증가한다. 즉 이 지표는 "
                   "«렌즈가 얼마나 떠 있나» 가 아니라 «렌즈 표면이 껍질에서 얼마나 물러났나» 를 잰다. "
                   "중심→나머지 거리는 반지름과 무관해야 정상이다 — 그것도 같이 잰다.")


# ══════════════════════════════════════════════════════════════════════════════
# Q2-c / A5 함정  프롭 자리를 바꿔도 prop_sha16 이 안 변한다는 주장
# ══════════════════════════════════════════════════════════════════════════════
def q2_prop_trap():
    _am = dr._arm_motor_dims
    out = {}
    for key in ("matrice4e", "mini5pro"):
        s = dr.DRONES[key]
        rows = {}
        for lbl, dz in (("base", 0.0), ("prop_z_plus_5mm", 0.005)):
            def patched(spec, diag, _dz=dz, _k=key):
                a, mh, pz = _am(spec, diag)
                return (a, mh, pz + _dz) if spec.key == _k else (a, mh, pz)
            dr._arm_motor_dims = patched; dr._FIT_CACHE.clear()
            d, p, f = dr.build_drone(s), dr.build_propeller(s), dr.build_frame(s)
            V = np.asarray(d.v, float) * 1000.0
            G = np.asarray(d.g); Fi = np.asarray(d.f, np.int64)
            pv = V[np.unique(Fi[G == "prop"])]
            rows[lbl] = dict(prop_sha16=mesh_sha(p), frame_sha16=mesh_sha(f), drone_sha16=mesh_sha(d),
                             prop_group_z_min_mm=R(pv[:, 2].min()), prop_group_z_max_mm=R(pv[:, 2].max()),
                             sz=round(float(dr.frame_fit_scale(s)[2]), 9))
        dr._arm_motor_dims = _am; dr._FIT_CACHE.clear()
        out[key] = dict(rows=rows,
                        prop_sha_unchanged=rows["base"]["prop_sha16"] == rows["prop_z_plus_5mm"]["prop_sha16"],
                        frame_sha_unchanged=rows["base"]["frame_sha16"] == rows["prop_z_plus_5mm"]["frame_sha16"],
                        drone_sha_unchanged=rows["base"]["drone_sha16"] == rows["prop_z_plus_5mm"]["drone_sha16"],
                        prop_group_z_moved_mm=R(rows["prop_z_plus_5mm"]["prop_group_z_min_mm"]
                                                - rows["base"]["prop_group_z_min_mm"]))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Q2-d  프롭 간격·겹침 — mini5pro 프롭 삼각형이 벨 안에 있다(526개)는 주장
# ══════════════════════════════════════════════════════════════════════════════
def q2_prop_gap():
    out = {}
    for key in ("matrice4e", "mini5pro", "mavic4pro"):
        s = dr.DRONES[key]
        m = dr.build_drone(s)
        V = np.asarray(m.v, float) * 1000.0
        G = np.asarray(m.g); F = np.asarray(m.f, np.int64); C = V[F].mean(1)
        mot = V[np.unique(F[G == "motor"])]
        pro_f = F[G == "prop"]
        pro = V[np.unique(pro_f)]
        # 벨 원기둥 근사: 모터 그룹의 (x,y) 중심들 주변 반경·z 범위
        bell_top = float(mot[:, 2].max()); bell_bot = float(mot[:, 2].min())
        # 프롭 정점 중 벨 z 범위 안에 있는 것
        pv = pro
        inside_z = (pv[:, 2] < bell_top) & (pv[:, 2] > bell_bot)
        # 삼각형 기준(무게중심)
        pc = C[G == "prop"]
        tri_inside = int(((pc[:, 2] < bell_top) & (pc[:, 2] > bell_bot)).sum())
        out[key] = dict(bell_top_mm=R(bell_top), bell_bottom_mm=R(bell_bot),
                        prop_lowest_mm=R(pro[:, 2].min()), prop_highest_mm=R(pro[:, 2].max()),
                        gap_propmesh_minus_belltop_mm=R(pro[:, 2].min() - bell_top),
                        prop_vertices_below_bell_top=int(inside_z.sum()),
                        prop_tris_centroid_below_bell_top=tri_inside,
                        n_prop_tris=int((G == "prop").sum()))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Q2-e  mini2 렌즈 y = 7.5434 · bw = 70.04109
# ══════════════════════════════════════════════════════════════════════════════
def q2_mini2():
    s = dr.DRONES["mini2"]
    sh = dc._SHELL_SHAPE["mini2"]
    bw = s.body_w_mm * sh["fw"]
    m = dr.build_frame(s)
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64); G = np.asarray(m.g); C = V[F].mean(1)
    sel = ((G == "camera") & (abs(C[:, 1]) > 3.0) & (abs(C[:, 1]) < 12.0)
           & (C[:, 2] > -18) & (C[:, 2] < -11))
    P = V[np.unique(F[sel])]
    pos = P[P[:, 1] > 0]
    return dict(body_w_mm=R(s.body_w_mm, 6), shell_fw=R(sh["fw"], 6), engine_bw_mm=R(bw, 6),
                drone_dims_body_w_mm=R(dr._drone_dims(s)[5] * 1000, 4),
                lens_center_y_measured_mm=R((pos[:, 1].min() + pos[:, 1].max()) / 2, 4),
                pred_old_0p1077=R(0.1077 * bw, 4), pred_new_0p102796=R(0.102796 * bw, 4),
                n_tris=int(sel.sum()))


# ══════════════════════════════════════════════════════════════════════════════
# Q2-f  matrice4e 셸 배 프로파일 (X1 의 산수 근거)
# ══════════════════════════════════════════════════════════════════════════════
def q2_belly():
    m = dr.build_frame(dr.DRONES["matrice4e"])
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64); G = np.asarray(m.g); C = V[F].mean(1)
    rows = []
    for x0 in range(60, 170, 10):
        sel = (G == "body") & (C[:, 0] >= x0) & (C[:, 0] < x0 + 10) & (abs(C[:, 1]) <= 26.0)
        if sel.sum():
            # 삼각형 무게중심이 아니라 **정점** 최저도 같이 낸다 — 무게중심은 실제 표면보다 높다
            vmin = V[np.unique(F[sel])][:, 2].min()
            rows.append(dict(x_mm=[x0, x0 + 10], centroid_min_z_mm=R(C[sel, 2].min(), 2),
                             vertex_min_z_mm=R(vmin, 2), n_tris=int(sel.sum()),
                             centroid_below_roof=bool(C[sel, 2].min() < CRADLE["z"][0]),
                             vertex_below_roof=bool(vmin < CRADLE["z"][0])))
    return rows


for name, fn in (("q2_baseline", q2_baseline), ("q3_fit_scale", q3_fit_scale),
                 ("q2_cradle", q2_cradle), ("q3_fisheye", q3_fisheye),
                 ("q2_prop_trap", q2_prop_trap), ("q2_prop_gap", q2_prop_gap),
                 ("q2_mini2", q2_mini2), ("q2_belly", q2_belly)):
    t = time.time()
    OUT[name] = fn()
    print(f"[{name}] {time.time()-t:.1f}s", flush=True)

GUARD_OUT = {p: fhash(p) for p in GUARD_FILES}
OUT["_meta"] = dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    generator="benchmark/meshdef_attack_verify.py",
                    source_guard_in=GUARD_IN, source_guard_out=GUARD_OUT,
                    sources_unchanged=(GUARD_IN == GUARD_OUT),
                    gpu="사용 안 함(CUDA_VISIBLE_DEVICES='')",
                    elapsed_s=round(time.time() - T0, 1))
p = os.path.join(ROOT, "outputs/meshdef_attack_raw.json")
json.dump(OUT, open(p, "w"), ensure_ascii=False, indent=1)
print("wrote", p, OUT["_meta"]["elapsed_s"], "s  sources_unchanged=",
      OUT["_meta"]["sources_unchanged"])
