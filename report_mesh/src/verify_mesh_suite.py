# -*- coding: utf-8 -*-
"""
verify_mesh_suite.py — 드론 메쉬 신뢰성 **종합 검증 스위트** (report_mesh 시리즈의 증거 JSON)
================================================================================================
목적: "이 메쉬를 레이더 시뮬레이션에 믿고 써도 되는가?" 를 **9개 독립 검사**로 정량화한다.
      결과는 report_mesh/outputs/mesh_verify.json 에 저장 — 리포트 본문의 모든 숫자는 여기서 읽는다
      (손으로 적은 숫자 금지, 하우스 규약).

9개 섹션(각각 한 질문):
  A geometry     — 삼각형이 기하학적으로 건강한가? (watertight·법선방향·winding·퇴화면·중복점·엣지길이)
  B symmetry     — 좌우대칭 기체가 정말 대칭인가? (미러 chamfer 거리)
  C dims         — 공식 제원(외형·대각·프롭지름)과 몇 % 안에서 맞는가?
  D volume       — 닫힌 부피 → 암시 밀도가 물리적으로 말이 되는가? (솔리드 근사의 정직한 한계 포함)
  E materials    — 모든 부위(그룹)에 전파 재질이 배정돼 있는가?
  F overlap      — 부위끼리 얼마나 겹치는가? (조립식 의도 겹침의 정량 공개)
  G scan         — 실기체 3D 스캔(Phantom 4, CC-BY)과 표면이 몇 mm 안에서 일치하는가?
  H po_conv      — PO 적분이 점 간격을 절반으로 줄여도 RCS 가 흔들리지 않는가? (수치 수렴)
  I sbr_subdiv   — SBR(GPU)이 메쉬를 세분화해도 RCS 가 흔들리지 않는가? (표현 충실도)

실행:  ~/.venvs/py312/bin/python report_mesh/src/verify_mesh_suite.py            # 전체 (I 는 GPU)
       ~/.venvs/py312/bin/python report_mesh/src/verify_mesh_suite.py --skip-sbr # GPU 없이 A~H
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))       # sionna2/
SRC = os.path.join(ROOT, "src")
OUT = os.path.abspath(os.path.join(HERE, "..", "outputs"))
os.makedirs(OUT, exist_ok=True)
for p in (SRC, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

C0 = 299_792_458.0
FC = 3.5e9                      # 검증 기준 주파수(5G NR) — 파장 85.7 mm
LAM_HI = C0 / 5.21e9            # 최고 대역(WiFi 5.21 GHz) 파장 57.5 mm — 엣지 길이 기준


# --------------------------------------------------------------------------- #
#  공용: geom.Mesh → trimesh (그룹 단위)
# --------------------------------------------------------------------------- #
def _group_trimeshes(mesh):
    """geom.Mesh 를 그룹(부위)별 trimesh 로 쪼갠다. {group: trimesh.Trimesh}"""
    import trimesh
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g)
    out = {}
    for grp in sorted(set(G.tolist())):
        f = F[G == grp]
        used = np.unique(f)
        remap = np.full(int(used.max()) + 1, -1, int)
        remap[used] = np.arange(len(used))
        tm = trimesh.Trimesh(vertices=V[used], faces=remap[f], process=False)
        out[grp] = tm
    return out


def _sample_points(mesh, spacing, exclude_groups=()):
    """검사용 표면 점 샘플 (그룹 제외 지원)."""
    from rcs_po import mesh_to_points
    if exclude_groups:
        from geom import Mesh
        m2 = Mesh()
        keep = [i for i, g in enumerate(mesh.g)
                if not any(g.startswith(e) for e in exclude_groups)]
        V = np.asarray(mesh.v, float)
        idx = {}
        for i in keep:
            tri = mesh.f[i]
            ids = []
            for vi in tri:
                if vi not in idx:
                    idx[vi] = m2.add_vertex(*V[vi])
                ids.append(idx[vi])
            m2.add_tri(*ids, group=mesh.g[i])
        mesh = m2
    P, N, dA = mesh_to_points(mesh, spacing)
    return P, N, dA


# --------------------------------------------------------------------------- #
#  A. 기하 품질 — mesh_check 확장판
# --------------------------------------------------------------------------- #
def sec_A_geometry(drones):
    from mesh_check import check_mesh
    res = {}
    for key, mesh in drones.items():
        base = check_mesh(mesh, key)                    # watertight/법선/winding/퇴화면
        tms = _group_trimeshes(mesh)
        V = np.asarray(mesh.v, float)
        F = np.asarray(mesh.f, int)
        # 중복 꼭짓점(1e-9 m 격자)·미사용 꼭짓점
        n_dup = len(V) - len(np.unique(np.round(V / 1e-9).astype(np.int64), axis=0))
        n_unused = len(V) - len(np.unique(F))
        # 엣지 길이 분포(전체) — 최고대역 파장 대비
        E = np.concatenate([V[F[:, 1]] - V[F[:, 0]],
                            V[F[:, 2]] - V[F[:, 1]],
                            V[F[:, 0]] - V[F[:, 2]]])
        el = np.linalg.norm(E, axis=1) * 1000.0                        # mm
        # 삼각형 최소각 분포 — 퇴화 위험 정량화
        def _angles(a, b, c):
            def ang(u, v):
                cu = np.einsum("ij,ij->i", u, v) / (
                    np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1) + 1e-30)
                return np.degrees(np.arccos(np.clip(cu, -1, 1)))
            return np.minimum.reduce([ang(b - a, c - a), ang(a - b, c - b), ang(a - c, b - c)])
        min_ang = _angles(V[F[:, 0]], V[F[:, 1]], V[F[:, 2]])
        res[key] = dict(
            n_verts=int(len(V)), n_faces=int(len(F)), n_groups=len(tms),
            groups=base["groups"], ok=bool(base["ok"]),
            dup_vertices=int(n_dup), unused_vertices=int(n_unused),
            edge_mm=dict(p50=float(np.percentile(el, 50)), p95=float(np.percentile(el, 95)),
                         max=float(el.max())),
            edge_vs_lam52=dict(lam_mm=LAM_HI * 1e3,
                               p95_over_lam=float(np.percentile(el, 95) / (LAM_HI * 1e3)),
                               max_over_lam=float(el.max() / (LAM_HI * 1e3))),
            tri_min_angle_deg=dict(p1=float(np.percentile(min_ang, 1)),
                                   p10=float(np.percentile(min_ang, 10)),
                                   median=float(np.percentile(min_ang, 50))),
        )
    return res


# --------------------------------------------------------------------------- #
#  B. 좌우대칭 — y→−y 미러와의 chamfer 거리 (비행안정 좌우대칭이 기하로도 성립하나)
# --------------------------------------------------------------------------- #
def sec_B_symmetry(drones):
    """전체(full)와 프레임만(frame_only) 두 겹으로 잰다.
    ⚠ 프로펠러는 **카이럴**(CW/CCW 쌍 + 스큐 날) — y 미러가 날개 위상·회전방향을 뒤집으므로
    full 의 큰 p95 는 결함이 아니라 프로펠러 물리다. 기체 대칭성은 frame_only 로 판정한다."""
    from scipy.spatial import cKDTree
    res = {}
    for key, mesh in drones.items():
        row = {}
        for tag, excl in [("full", ()), ("frame_only", ("prop",))]:
            P, _, _ = _sample_points(mesh, spacing=4e-3, exclude_groups=excl)
            Q = P * np.array([1.0, -1.0, 1.0])          # y 미러
            d = cKDTree(P).query(Q, k=1)[0] * 1000.0    # mm
            row[tag] = dict(n_points=int(len(P)),
                            chamfer_mm=dict(p50=float(np.percentile(d, 50)),
                                            p95=float(np.percentile(d, 95)),
                                            max=float(d.max())))
        res[key] = row
    return res


# --------------------------------------------------------------------------- #
#  C. 치수 대조 — 공식 제원 vs 우리가 만든 메쉬 실측
# --------------------------------------------------------------------------- #
def sec_C_dims(specs):
    from drones import frame_envelope_mm, build_propeller
    res = {}
    for key, spec in specs.items():
        env = frame_envelope_mm(spec)
        # 프로펠러 지름: 메쉬 xy 반경 최대 ×2
        pv = np.asarray(build_propeller(spec).v, float)
        dia_meas = 2.0 * float(np.hypot(pv[:, 0], pv[:, 1]).max()) * 1000.0
        errs = {}
        if spec.envelope_mm:
            # ⚠ 공식 외형이 **프롭 포함**인 기체(Mini 5 Pro: 304×380×91)는 프레임이 아니라
            #   **완성된 드론 전체**를 공식값과 견뎌야 한다. 프레임만 91 mm 에 맞추면 프롭이
            #   그 위로 더 얹혀 실제 총높이가 106 mm 가 된다. frame_envelope_mm 이 축별로
            #   올바른 비교대상(lwh_compare_mm)을 이미 골라 준다.
            for ax, off, meas in zip("LWH", spec.envelope_mm, env["lwh_compare_mm"]):
                if off is not None:
                    errs[ax] = dict(official=float(off), measured=float(meas),
                                    err_pct=float((meas - off) / off * 100.0),
                                    basis=("full drone (official envelope includes propellers)"
                                           if env["official_includes_props"] else "airframe"))
        # 프롭 포함 공식 L/W 와 견줄 값은 **회전 디스크 외곽**이다 — 정적 메쉬 bbox 는
        # 블레이드가 멈춘 방위에 따라 달라진다(2날 프롭은 원반이 아니라 선이다).
        if env["official_includes_props"]:
            errs["prop_disc_L"] = dict(measured=float(env["prop_disc_lw_mm"][0]))
            errs["prop_disc_W"] = dict(measured=float(env["prop_disc_lw_mm"][1]))
        errs["diagonal"] = dict(official=float(spec.diagonal_mm),
                                measured=float(env["diagonal_effective_mm"]),
                                err_pct=float((env["diagonal_effective_mm"] - spec.diagonal_mm)
                                              / spec.diagonal_mm * 100.0))
        errs["prop_dia"] = dict(official=float(spec.prop_dia_mm), measured=dia_meas,
                                err_pct=float((dia_meas - spec.prop_dia_mm)
                                              / spec.prop_dia_mm * 100.0))
        worst = max(abs(v["err_pct"]) for v in errs.values() if "err_pct" in v)
        res[key] = dict(checks=errs, worst_err_pct=float(worst),
                        fit_scale=[float(x) for x in env["fit_scale"]])
    return res


# --------------------------------------------------------------------------- #
#  D. 부피 → 암시 밀도 타당성 (솔리드 근사의 정직한 공개)
# --------------------------------------------------------------------------- #
def sec_D_volume(drones, specs):
    res = {}
    for key, mesh in drones.items():
        tms = _group_trimeshes(mesh)
        vols = {}
        for grp, tm in tms.items():
            comps = tm.split(only_watertight=False)
            v = sum(abs(c.volume) for c in comps if c.is_watertight)
            vols[grp] = float(v * 1e6)                  # cm³
        total_cm3 = float(sum(vols.values()))
        w_g = specs[key].weight_g
        row = dict(volume_cm3=vols, total_cm3=total_cm3, weight_g=float(w_g),
                   implied_density_g_cm3=float(w_g / total_cm3) if total_cm3 else None)
        if key == "s1000plus":                          # weight_g=9500 은 대표 TOW(페이로드 포함)
            row["airframe_g"] = 4400.0                  # 기체 자중(SPECS.md) — 밀도는 이걸로도 병기
            row["implied_density_airframe_g_cm3"] = float(4400.0 / total_cm3)
        res[key] = row
    return res


# --------------------------------------------------------------------------- #
#  E. 재질 커버리지 — 그룹마다 |Γ| 가 배정돼 있나 (빠지면 PEC=1.0 으로 과대반사)
# --------------------------------------------------------------------------- #
def sec_E_materials(drones, specs):
    from drones import drone_gamma_map
    res = {}
    for key, mesh in drones.items():
        gm = drone_gamma_map(specs[key], FC)
        groups = sorted(set(mesh.g))
        # 그룹명이 gamma 키로 시작-매칭되는지(관용: prop_1 → prop)
        cover = {}
        for g in groups:
            hit = g in gm or any(g.startswith(k) for k in gm)
            cover[g] = bool(hit)
        res[key] = dict(gamma_map={k: float(v) for k, v in gm.items()},
                        groups=groups,
                        uncovered=[g for g, ok in cover.items() if not ok],
                        all_covered=all(cover.values()))
    return res


# --------------------------------------------------------------------------- #
#  F. 부위 겹침 — 조립식 의도 겹침을 불리언 교차부피로 정량 공개
# --------------------------------------------------------------------------- #
def sec_F_overlap(drones):
    import trimesh
    res = {}
    for key, mesh in drones.items():
        tms = {g: t for g, t in _group_trimeshes(mesh).items()}
        # watertight 단일컴포넌트만 불리언 대상(견고성)
        solid = {}
        for g, t in tms.items():
            comps = [c for c in t.split(only_watertight=False) if c.is_watertight]
            if comps:
                solid[g] = comps
        pairs = []
        keys = sorted(solid)
        total_overlap = 0.0
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a_list, b_list = solid[keys[i]], solid[keys[j]]
                ov = 0.0
                for a in a_list:
                    for b in b_list:
                        # bbox 겹칠 때만 불리언 시도
                        if (a.bounds[0] > b.bounds[1]).any() or (b.bounds[0] > a.bounds[1]).any():
                            continue
                        try:
                            inter = trimesh.boolean.intersection([a, b], engine="manifold")
                            if inter is not None and inter.volume:
                                ov += abs(inter.volume)
                        except BaseException:
                            pass
                if ov > 1e-12:
                    pairs.append(dict(a=keys[i], b=keys[j], overlap_cm3=float(ov * 1e6)))
                    total_overlap += ov
        tot_vol = sum(abs(c.volume) for cl in solid.values() for c in cl)
        res[key] = dict(pairs=sorted(pairs, key=lambda p: -p["overlap_cm3"]),
                        total_overlap_cm3=float(total_overlap * 1e6),
                        overlap_pct_of_volume=float(total_overlap / tot_vol * 100.0)
                        if tot_vol else 0.0)
    return res


# --------------------------------------------------------------------------- #
#  G. 실기체 스캔 대조 — Phantom 4 CC-BY 스캔과의 표면 chamfer 거리 [mm]
#     (스캔에는 프로펠러·짐벌카메라가 없다 → CAD 쪽도 해당 그룹 제외; z 오프셋만 탐색 정렬)
# --------------------------------------------------------------------------- #
def sec_G_scan(drones):
    from scipy.spatial import cKDTree
    npz = os.path.join(ROOT, "assets", "meshes", "cad", "phantom4_scan_points.npz")
    if not os.path.exists(npz):
        return dict(error="scan npz not found", path=npz)
    S = np.load(npz)
    Ps = np.asarray(S["P"], float)                       # 스캔 점(m, z-up, 스케일 보정됨)
    mesh = drones["phantom4"]
    Pc, _, _ = _sample_points(mesh, spacing=3e-3,
                              exclude_groups=("prop", "camera", "gimbal"))
    # 수평 중심 정렬 + z 오프셋 그리드 탐색(±30 mm)
    Ps = Ps - Ps.mean(0) * np.array([1, 1, 0])
    Pc = Pc - Pc.mean(0) * np.array([1, 1, 0])
    tree_c = cKDTree(Pc)
    best = None
    for dz in np.arange(-0.03, 0.0301, 0.002):
        d = tree_c.query(Ps + np.array([0, 0, dz]), k=1)[0]
        med = float(np.median(d))
        if best is None or med < best[1]:
            best = (float(dz), med)
    dz = best[0]
    Ps2 = Ps + np.array([0, 0, dz])
    d_s2c = tree_c.query(Ps2, k=1)[0] * 1000.0           # 스캔→CAD [mm]
    d_c2s = cKDTree(Ps2).query(Pc, k=1)[0] * 1000.0      # CAD→스캔 [mm]
    def _st(d):
        return dict(p50=float(np.percentile(d, 50)), p90=float(np.percentile(d, 90)),
                    p99=float(np.percentile(d, 99)), max=float(d.max()))
    return dict(n_scan=int(len(Ps)), n_cad=int(len(Pc)), z_shift_mm=dz * 1000.0,
                scan_to_cad_mm=_st(d_s2c), cad_to_scan_mm=_st(d_c2s),
                source=dict(thing="Thingiverse thing:1456295", license="CC-BY",
                            author="NeverDun/Eamon McQuaide",
                            note="스캔에 프로펠러·짐벌 없음 → CAD 도 해당 그룹 제외 비교"))


# --------------------------------------------------------------------------- #
#  H. PO 수렴 — 점 간격 s → s/2 로 줄여도 RCS 패턴이 흔들리지 않는가
# --------------------------------------------------------------------------- #
def sec_H_po_convergence(keys=("mavic4pro", "phantom4")):
    from rcs_po import drone_rcs_pattern, dbsm
    az = np.arange(0.0, 360.0, 5.0)
    lam = C0 / FC
    res = {}
    for key in keys:
        rows = {}
        for s, tag in [(lam / 10, "lam/10"), (lam / 20, "lam/20")]:
            sig, _ = drone_rcs_pattern(key, FC, az, el_deg=15.0, spacing=s)
            rows[tag] = np.asarray(sig, float)
        d = np.abs(10 * np.log10(np.maximum(rows["lam/20"], 1e-12))
                   - 10 * np.log10(np.maximum(rows["lam/10"], 1e-12)))
        # 방위평균(전력평균) 차이 — 헤드라인용
        m10 = 10 * np.log10(np.mean(rows["lam/10"]))
        m20 = 10 * np.log10(np.mean(rows["lam/20"]))
        res[key] = dict(n_az=len(az), el_deg=15.0, fc_ghz=FC / 1e9,
                        per_angle_absdiff_db=dict(mean=float(d.mean()),
                                                  p95=float(np.percentile(d, 95)),
                                                  max=float(d.max())),
                        azavg_dbsm=dict(lam10=float(m10), lam20=float(m20),
                                        diff=float(m20 - m10)))
    return res


# --------------------------------------------------------------------------- #
#  I. SBR 세분화 불변 (GPU) — 메쉬를 4배(1회 subdivide) 잘게 해도 SBR RCS 가 같은가
# --------------------------------------------------------------------------- #
def _subdivide_mesh(mesh):
    """그룹 보존 1회 subdivide (삼각형 4분할). geom.Mesh → geom.Mesh"""
    import trimesh
    from geom import Mesh
    out = Mesh()
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g)
    for grp in sorted(set(G.tolist())):
        f = F[G == grp]
        used = np.unique(f)
        remap = np.full(int(used.max()) + 1, -1, int)
        remap[used] = np.arange(len(used))
        tm = trimesh.Trimesh(vertices=V[used], faces=remap[f], process=False).subdivide()
        base = len(out.v)
        for p in tm.vertices:
            out.add_vertex(*p)
        for a, b, c in tm.faces:
            out.add_tri(base + int(a), base + int(b), base + int(c), group=grp)
    return out


def sec_I_sbr_subdiv(key="mavic4pro"):
    """두 겹 검사:
    ① subdivision 불변 — 삼각형을 4배 잘게 해도 σ 동일해야(표면이 같으니 자명하지만,
       파이프라인이 테셀레이션 밀도에 **의존하지 않음**을 실측으로 못박는다).
    ② 광선 간격 수렴 — SBR 의 **진짜 수치 놉**인 광선 격자 λ/12 → λ/24 로 반절해도
       σ 가 흔들리지 않아야 진짜 수렴이다."""
    from gpu import pick
    pick(verbose=True)
    from drones import DRONES, build_drone, drone_gamma_map
    from rcs_sbr import rcs_sbr_batch
    spec = DRONES[key]
    mesh = build_drone(spec)
    gm = drone_gamma_map(spec, FC)
    az = np.arange(0.0, 360.0, 15.0)
    lam = C0 / FC
    t0 = time.time()

    def _stats(sa, sb):
        d = np.abs(10 * np.log10(np.maximum(sb, 1e-12))
                   - 10 * np.log10(np.maximum(sa, 1e-12)))
        return dict(per_angle_absdiff_db=dict(mean=float(d.mean()),
                                              p95=float(np.percentile(d, 95)),
                                              max=float(d.max())),
                    azavg_dbsm=dict(a=float(10 * np.log10(np.mean(sa))),
                                    b=float(10 * np.log10(np.mean(sb))),
                                    diff=float(10 * np.log10(np.mean(sb))
                                               - 10 * np.log10(np.mean(sa)))))

    # ① subdivision 불변 (광선 간격 기본 λ/12 고정)
    s_base = np.asarray(rcs_sbr_batch(mesh, gm, FC, az, el_deg=15.0), float)
    mesh2 = _subdivide_mesh(mesh)
    s_fine = np.asarray(rcs_sbr_batch(mesh2, gm, FC, az, el_deg=15.0), float)
    sub = _stats(s_base, s_fine)
    sub.update(faces_base=len(mesh.f), faces_fine=len(mesh2.f))

    # ② 광선 간격 수렴 λ/12 → λ/24 (기본 메쉬)
    s_r24 = np.asarray(rcs_sbr_batch(mesh, gm, FC, az, el_deg=15.0,
                                     spacing=lam / 24.0), float)
    ray = _stats(s_base, s_r24)
    ray.update(spacing_a="lam/12", spacing_b="lam/24")

    return dict(drone=key, n_az=len(az), el_deg=15.0, fc_ghz=FC / 1e9,
                subdivision_invariance=sub, ray_spacing_convergence=ray,
                runtime_s=float(time.time() - t0))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-sbr", action="store_true")
    a = ap.parse_args()

    from drones import DRONES, build_drone
    specs = dict(DRONES)
    drones = {k: build_drone(s) for k, s in specs.items()}
    print(f"드론 {len(drones)}종 빌드 완료")

    out = dict(meta=dict(fc_ghz=FC / 1e9, lam_hi_mm=LAM_HI * 1e3,
                         mesh_engine="cad(trimesh+manifold3d)",
                         drones=list(drones)))
    for name, fn, args in [
        ("A_geometry", sec_A_geometry, (drones,)),
        ("B_symmetry", sec_B_symmetry, (drones,)),
        ("C_dims", sec_C_dims, (specs,)),
        ("D_volume", sec_D_volume, (drones, specs)),
        ("E_materials", sec_E_materials, (drones, specs)),
        ("F_overlap", sec_F_overlap, (drones,)),
        ("G_scan", sec_G_scan, (drones,)),
        ("H_po_convergence", sec_H_po_convergence, ()),
    ]:
        t0 = time.time()
        try:
            out[name] = fn(*args)
            print(f"  [{name}] OK ({time.time()-t0:.1f}s)")
        except BaseException as e:
            out[name] = dict(error=repr(e))
            print(f"  [{name}] ERROR: {e!r}")
    if not a.skip_sbr:
        t0 = time.time()
        try:
            out["I_sbr_subdiv"] = sec_I_sbr_subdiv()
            print(f"  [I_sbr_subdiv] OK ({time.time()-t0:.1f}s)")
        except BaseException as e:
            out["I_sbr_subdiv"] = dict(error=repr(e))
            print(f"  [I_sbr_subdiv] ERROR: {e!r}")

    path = os.path.join(OUT, "mesh_verify.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✅ 저장: {path}")


if __name__ == "__main__":
    main()
