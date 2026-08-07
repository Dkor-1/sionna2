#!/usr/bin/env python
"""다섯 갈래(floating·gimbal·ground·mini2·prop_gap)를 하나의 패치 명세로 합친다.

이 스크립트는 **소스를 한 줄도 고치지 않는다**. 측정이 필요한 곳은 엔진을 메모리 안에서만
임시로 갈아끼워(monkeypatch) 재고, 원상복구한다. GPU 는 쓰지 않는다.

내는 것: outputs/meshdef_spec.json
"""
from __future__ import annotations
import hashlib, json, os, sys, time, subprocess

ROOT = "/home/yunjung/workspace/sionna2"
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
sys.path.insert(0, ROOT)
os.environ.setdefault("SIONNA2_NO_GPU", "1")

import numpy as np                      # noqa: E402
import drone_cad as dc                  # noqa: E402
import drones as dr                     # noqa: E402

T0 = time.time()
R = lambda x, n=4: round(float(x), n)    # noqa: E731


# ────────────────────────────────────────────────────────────────────────────
# 0) 손대지 않았음을 스스로 증명한다 — 소스 파일 해시
# ────────────────────────────────────────────────────────────────────────────
def _fhash(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


SOURCE_GUARD = {
    p: dict(sha256_16=_fhash(os.path.join(ROOT, p)),
            mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                time.localtime(os.path.getmtime(os.path.join(ROOT, p)))))
    for p in ("src/drones.py", "src/drone_cad.py", "src/geom.py")
}


# ────────────────────────────────────────────────────────────────────────────
# 1) 기준선 — 열 기체의 메쉬 지문. 「손대지 않을 기체는 비트동일」 검사의 진리원
# ────────────────────────────────────────────────────────────────────────────
def mesh_sha(m):
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, np.int64)
    h = hashlib.sha256(np.ascontiguousarray(np.round(V, 9)).tobytes())
    h.update(np.ascontiguousarray(F).tobytes())
    return h.hexdigest()[:16]


def baseline():
    import channel as ch                                     # σ 캐시 지문과 같은 함수
    out = {}
    for k, s in dr.DRONES.items():
        d, f, p = dr.build_drone(s), dr.build_frame(s), dr.build_propeller(s)
        V = np.asarray(d.v, float) * 1000.0
        G = np.asarray(d.g)
        Fi = np.asarray(d.f, np.int64)
        pv = V[np.unique(Fi[G == "prop"])]
        out[k] = dict(
            drone_sha16=mesh_sha(d), frame_sha16=mesh_sha(f), prop_sha16=mesh_sha(p),
            sigma_cache_fp=ch._mesh_fp(k),           # benchmark/channel.py::_mesh_fp
            n_v=int(len(d.v)), n_f=int(len(d.f)),
            fit_scale=[round(float(x), 9) for x in dr.frame_fit_scale(s)],
            bbox_mm=[R(x, 4) for x in (V.max(0) - V.min(0))],
            prop_group_z_mm=[R(pv[:, 2].min()), R(pv[:, 2].max())],
            prop_group_centroid_z_mm=R(pv[:, 2].mean()),
            env_props_included=bool(getattr(s, "env_props_included", False)),
            envelope_mm=list(s.envelope_mm) if s.envelope_mm else None)
    return out


# ────────────────────────────────────────────────────────────────────────────
# 2) 얽힘 측정 — 접지(다리) ↔ 프롭 간격이 서로를 얼마나 끌고 가는가
#    두 방향 다 잰다. 방향이 기체마다 반대라는 것이 이 라운드의 핵심 발견이다.
# ────────────────────────────────────────────────────────────────────────────
def _drone_probe(key):
    s = dr.DRONES[key]
    m = dr.build_drone(s)
    V = np.asarray(m.v, float) * 1000.0
    G = np.asarray(m.g); F = np.asarray(m.f, np.int64)
    gz = lambda g: V[np.unique(F[G == g])]                    # noqa: E731
    mot, pro = gz("motor"), gz("prop")
    r = dict(sz=round(float(dr.frame_fit_scale(s)[2]), 9),
             frame_zmin_mm=R(V[:, 2].min()), frame_zmax_mm=R(V[:, 2].max()),
             bell_top_mm=R(mot[:, 2].max()), prop_lowest_mm=R(pro[:, 2].min()),
             gap_propmesh_minus_belltop_mm=R(pro[:, 2].min() - mot[:, 2].max()))
    if (G == "gear").any():
        r["gear_zmin_mm"] = R(gz("gear")[:, 2].min())
    return r


def interlocks():
    out = {}

    # (A) matrice4e : 다리 길이 → sz → 벨·프롭 절대 z
    old = dc.GEAR_SPIKE_H["matrice4e"]
    rows = {}
    for lbl, h in (("base", old), ("minus_1mm", old - 0.001), ("plus_1mm", old + 0.001),
                   ("plus_0p214mm", old + 0.000214)):
        dc.GEAR_SPIKE_H["matrice4e"] = h; dr._FIT_CACHE.clear()
        rows[lbl] = dict(spike_h_m=h, **_drone_probe("matrice4e"))
    dc.GEAR_SPIKE_H["matrice4e"] = old; dr._FIT_CACHE.clear()
    d = lambda a, b, k: round((rows["plus_1mm"][k] - rows["minus_1mm"][k]) / 2.0, 9)  # noqa: E731
    out["A_matrice4e_gear_drives_prop"] = dict(
        rows=rows,
        d_sz_per_mm_leg=d(0, 0, "sz"),
        d_belltop_mm_per_mm_leg=d(0, 0, "bell_top_mm"),
        d_gap_mm_per_mm_leg=d(0, 0, "gap_propmesh_minus_belltop_mm"),
        ko="다리를 1 mm 늘리면 sz 가 이만큼 줄고, 그 배율이 벨·프롭 절대 z 를 통째로 끌어내린다. "
           "ground 라운드가 GEAR_SPIKE_H 를 '안 고친다' 로 판정했으므로 이 통로는 지금 잠겨 있다. "
           "다만 ground C3(앞뒤 다리 분리)이 들어오면 프레임 최저점이 최대 앞뒤 발바닥 차만큼 움직인다.")

    # (B) mini5pro : prop_z → sz → 다리 접지  (matrice4e 와 화살표가 **반대**다)
    _am = dr._arm_motor_dims
    rows = {}
    for lbl, dz in (("base", 0.0), ("minus_1mm", -0.001), ("plus_1mm", +0.001)):
        def patched(spec, diag, _dz=dz):
            a, mh, pz = _am(spec, diag)
            return (a, mh, pz + _dz) if spec.key == "mini5pro" else (a, mh, pz)
        dr._arm_motor_dims = patched; dr._FIT_CACHE.clear()
        rows[lbl] = dict(d_prop_z_mm=dz * 1000, **_drone_probe("mini5pro"))
    dr._arm_motor_dims = _am; dr._FIT_CACHE.clear()
    out["B_mini5pro_prop_drives_gear"] = dict(
        rows=rows,
        d_sz_per_mm_prop=round((rows["plus_1mm"]["sz"] - rows["minus_1mm"]["sz"]) / 2.0, 9),
        d_gearzmin_mm_per_mm_prop=round(
            (rows["plus_1mm"]["gear_zmin_mm"] - rows["minus_1mm"]["gear_zmin_mm"]) / 2.0, 6),
        ko="mini5pro 는 env_props_included=True 라 sz 를 프롭 장착높이로 푼다. 그래서 프롭을 "
           "옮기면 프레임 전체 배율이 바뀌고 **다리 접지점이 따라 움직인다** — matrice4e 와 정반대 방향이다.")

    # (C) matrice4e 에는 되먹임이 없다는 것을 반증 시도로 확인
    rows = {}
    for lbl, dz in (("base", 0.0), ("plus_5mm", 0.005), ("minus_5mm", -0.005)):
        def patched(spec, diag, _dz=dz):
            a, mh, pz = _am(spec, diag)
            return (a, mh, pz + _dz) if spec.key == "matrice4e" else (a, mh, pz)
        dr._arm_motor_dims = patched; dr._FIT_CACHE.clear()
        rows[lbl] = dict(d_prop_z_mm=dz * 1000, **_drone_probe("matrice4e"))
    dr._arm_motor_dims = _am; dr._FIT_CACHE.clear()
    out["C_matrice4e_prop_has_no_feedback"] = dict(
        rows=rows,
        sz_all_equal=len({r["sz"] for r in rows.values()}) == 1,
        ko="프롭을 ±5 mm 옮겨도 sz 가 소수 9자리까지 같다 — matrice4e 는 프레임 bbox 만 보고 "
           "배율을 푼다. 즉 화살표는 다리→프롭 한 방향뿐이고, 고리(cycle)는 없다.")
    return out


# ────────────────────────────────────────────────────────────────────────────
# 3) matrice4e 기수 — F22/F23/F24 와 짐벌 정정이 같은 자리를 두고 다툰다
# ────────────────────────────────────────────────────────────────────────────
CRADLE_BOX = dict(x=(71.59, 146.34), y=(-31.55, 31.55), z=(-17.19, 0.93))   # F23 제안 신설파트


def nose_conflict():
    from scipy.spatial import cKDTree
    _gs, _fe = dc._gimbal_sensor_v2, dc._fisheye

    def build(gpatch=None, fz=None, fr=None):
        dc._gimbal_sensor_v2 = (lambda w, h, d, cx, cz: _gs(*gpatch)) if gpatch else _gs

        def fe(cx, cy, cz, r, axis="x"):
            if abs(cz - (-0.0191)) < 1e-9:                    # 하방 어안쌍만
                if fz is not None: cz = fz
                if fr is not None: r = fr
            return _fe(cx, cy, cz, r, axis)
        dc._fisheye = fe if (fz is not None or fr is not None) else _fe
        dr._FIT_CACHE.clear()
        m = dr.build_frame(dr.DRONES["matrice4e"])
        dc._gimbal_sensor_v2, dc._fisheye = _gs, _fe
        dr._FIT_CACHE.clear()
        return m

    def probe(m, tag):
        V = np.asarray(m.v, float) * 1000.0
        F = np.asarray(m.f, np.int64); G = np.asarray(m.g); C = V[F].mean(1)
        down = (G == "camera") & (C[:, 0] > 70) & (C[:, 0] < 100) & (C[:, 2] < 0)
        gim = (G == "camera") & (C[:, 0] > 110) & (C[:, 2] < 30)
        Fo = F[~down]; P = V[Fo]
        S = np.concatenate([P.reshape(-1, 3), P.mean(1),
                            (P[:, 0] + P[:, 1]) / 2, (P[:, 1] + P[:, 2]) / 2, (P[:, 0] + P[:, 2]) / 2])
        d, _ = cKDTree(S).query(V[np.unique(F[down])])
        box = ((C[:, 0] >= CRADLE_BOX["x"][0]) & (C[:, 0] <= CRADLE_BOX["x"][1])
               & (C[:, 1] >= CRADLE_BOX["y"][0]) & (C[:, 1] <= CRADLE_BOX["y"][1])
               & (C[:, 2] >= CRADLE_BOX["z"][0]) & (C[:, 2] <= CRADLE_BOX["z"][1]))
        gv = V[np.unique(F[gim])]
        return dict(tag=tag,
                    down_pair_min_dist_to_rest_mm=R(d.min()),
                    down_pair_bbox_mm=[R(x, 2) for x in V[np.unique(F[down])].min(0)]
                                      + [R(x, 2) for x in V[np.unique(F[down])].max(0)],
                    tris_already_inside_F23_box=dict(
                        body=int(((G == "body") & box).sum()),
                        camera=int(((G == "camera") & box).sum()),
                        total=int(box.sum()), of_total_tris=int(len(F))),
                    gimbal_assembly_bbox_mm=[R(x, 2) for x in gv.min(0)] + [R(x, 2) for x in gv.max(0)])

    rows = [probe(build(), "baseline"),
            probe(build(fz=-0.01364), "F22 only  (down-pair z −19.1 → −13.64)"),
            probe(build(fr=0.0043), "F24 only  (down-pair r 9.0 → 4.3)"),
            probe(build(fz=-0.01364, fr=0.0043), "F22 + F24"),
            probe(build(gpatch=(0.059, 0.0612, 0.052, 0.1483, -0.01036)), "gimbal G1+G2 (h,cz)"),
            probe(build(gpatch=(0.0629, 0.0612, 0.0364, 0.1561, -0.01036)), "gimbal G1..G4 (all four)")]

    # 짐벌 helper 자체를 직접 재서 요·댐핑판이 어디로 가는지 본다
    def helper(args):
        A = dc._gimbal_sensor_v2(*args)
        V = [np.asarray(m.vertices, float) * 1000.0 for _g, m in A]
        allv = np.concatenate(V)
        nm = ["yoke_cyl", "damper_plate", "block_upper", "block_lower"]
        return dict(assembly_bbox_mm=[R(x, 2) for x in allv.min(0)] + [R(x, 2) for x in allv.max(0)],
                    **{nm[i]: [R(x, 2) for x in V[i].min(0)] + [R(x, 2) for x in V[i].max(0)]
                       for i in range(4)})

    # 셸 배(belly) 프로파일 — F23 이 말하는 「빈 자리」가 실제로 어디까지인가
    m = dr.build_frame(dr.DRONES["matrice4e"])
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64); G = np.asarray(m.g); C = V[F].mean(1)
    belly = []
    for x0 in range(60, 170, 10):
        sel = (G == "body") & (C[:, 0] >= x0) & (C[:, 0] < x0 + 10) & (abs(C[:, 1]) <= 26.0)
        if sel.sum():
            belly.append(dict(x_mm=[x0, x0 + 10], shell_min_z_mm=R(C[sel, 2].min(), 2),
                              shell_max_z_mm=R(C[sel, 2].max(), 2), n_tris=int(sel.sum()),
                              below_cradle_roof=bool(C[sel, 2].min() < CRADLE_BOX["z"][0])))
    return dict(variants=rows,
                gimbal_helper=dict(
                    current=helper((0.059, 0.047, 0.052, 0.1483, -0.01716)),
                    G1_G2=helper((0.059, 0.0612, 0.052, 0.1483, -0.01036)),
                    G1_to_G4=helper((0.0629, 0.0612, 0.0364, 0.1561, -0.01036))),
                shell_belly_profile=belly,
                cradle_box_mm=CRADLE_BOX)


# ────────────────────────────────────────────────────────────────────────────
# 4) mini2 C1 을 독립으로 확인 — 렌즈가 실제로 어디에 놓이는가
# ────────────────────────────────────────────────────────────────────────────
def mini2_check():
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
    return dict(engine_bw_mm=R(bw, 5),
                engine_bw_formula="drone_cad.py:2020,2028  W = spec.body_w_mm/1000 ; bw = W * _SHELL_SHAPE['mini2']['fw']",
                unrelated_body_w_from_drone_dims_mm=R(dr._drone_dims(s)[5] * 1000, 4),
                lens_center_y_measured_mm=R((pos[:, 1].min() + pos[:, 1].max()) / 2, 4),
                lens_center_y_predicted_old_mm=R(0.1077 * bw, 4),
                lens_center_y_predicted_new_mm=R(0.102796 * bw, 4),
                cad_target_y_mm=7.1999,
                n_tris=int(sel.sum()),
                ko="렌즈가 놓이는 자리를 엔진에서 직접 재니 7.5434 mm 로, mini2 라운드가 계산한 값과 "
                   "소수 넷째 자리까지 같다. 66.85 mm 는 drones._drone_dims 가 내는 **다른** 양이고 "
                   "이 코드경로와 무관하다 — F7 기록이 그 둘을 섞었다는 진단이 맞다.")


# ────────────────────────────────────────────────────────────────────────────
# 5) σ 디스크캐시가 정말 형상 지문을 갖는가 (floating F22 의 경고를 반증 시도)
# ────────────────────────────────────────────────────────────────────────────
def sigma_cache_check():
    import collections, channel as ch
    cur = {k: ch._mesh_fp(k) for k in dr.DRONES}
    raw = json.load(open(os.path.join(ROOT, "outputs/sigma_sbr_cache.json")))
    cnt = collections.Counter(k.split("|", 1)[0] for k in raw)
    rows = []
    for head, n in sorted(cnt.items()):
        d, _, fp = head.partition("@")
        rows.append(dict(key_head=head, n_entries=n, drone=d,
                         matches_current_mesh=bool(cur.get(d) == fp)))
    return dict(key_builder="benchmark/channel.py::_sig_key → f'{drone}@{_mesh_fp(drone)}|{fc}|{az}|{el}'",
                current_fingerprints=cur, cache_entries_total=len(raw), by_key_head=rows,
                verdict_ko="σ 디스크캐시는 키에 메쉬 지문을 넣는다 — 메쉬를 고치면 저절로 미스가 난다. "
                           "matrice4e 항목은 이미 옛 지문이라 지금도 미스다. 손으로 지울 필요 없다. "
                           "⚠ 그러나 이 보호는 50개짜리 σ 조회표에만 걸린다. **저장된** 격자"
                           "(report13_sigma_grid*.json · das_fleet_* · report15_* · report16_*)에는 "
                           "지문이 없어 조용히 낡는다 — 진짜 위험은 이쪽이다.")


# ────────────────────────────────────────────────────────────────────────────
# 6) 무효화 대상 — 메쉬를 읽는 스크립트를 기계적으로 센다(손으로 안 적는다)
# ────────────────────────────────────────────────────────────────────────────
def mesh_readers():
    cmd = ("grep -ln 'build_drone\\|build_frame\\|DRONES\\[' "
           "benchmark/*.py src/*.py 2>/dev/null")
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    files = sorted(x for x in r.stdout.split() if x)
    return dict(n_files=len(files), how=cmd, files=files)


def output_index():
    """outputs/*.json 중 기체 이름이 든 것 + 크기 + 마지막 수정시각."""
    import glob
    keys = list(dr.DRONES)
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "outputs", "*.json"))):
        b = os.path.basename(f)
        if b.startswith("meshdef_"):
            continue
        try:
            t = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        hit = [k for k in keys if k in t]
        if hit:
            rows.append(dict(file="outputs/" + b, kb=os.path.getsize(f) // 1024,
                             mtime=time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(f))),
                             drones=hit))
    return rows


# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    doc = dict(
        _meta=dict(
            title="다섯 갈래 메쉬 결함 라운드 → 하나의 패치 명세",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            generator="scratchpad/build_meshdef_spec.py (이 파일)",
            merges=["outputs/meshdef_floating.json", "outputs/meshdef_gimbal.json",
                    "outputs/meshdef_ground.json", "outputs/meshdef_mini2_glb.json",
                    "outputs/meshdef_prop_gap.json"],
            discipline=dict(
                no_source_edit="src/drones.py · src/drone_cad.py 를 열지도 고치지도 않았다. "
                               "측정은 메모리 안 monkeypatch 로만 하고 즉시 원복한다.",
                gpu="GPU 미사용(전부 CPU). GPU3 은 근처에도 가지 않았다.",
                writes="outputs/meshdef_spec.json · docs/MESH_DEFECTS.md 만 새로 쓴다. "
                       "report00_* · report15_* · report16_* 는 읽기만 했다.",
                stage="증거 확보와 명세까지. **적용은 다음 라운드다.**"),
            source_guard=SOURCE_GUARD),
        baseline_fingerprints=baseline(),
        interlocks=interlocks(),
        nose_conflict=nose_conflict(),
        mini2_check=mini2_check(),
        sigma_cache_check=sigma_cache_check(),
        mesh_readers=mesh_readers(),
        output_index=output_index(),
    )
    doc["_meta"]["elapsed_s"] = R(time.time() - T0, 1)
    out = os.path.join(ROOT, "outputs", "meshdef_spec.json")
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", out, os.path.getsize(out) // 1024, "KB in", doc["_meta"]["elapsed_s"], "s")
