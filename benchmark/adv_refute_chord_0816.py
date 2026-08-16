# -*- coding: utf-8 -*-
"""adv_refute_chord_0816.py — 감사(docs/MESH_AUDIT_0816.md) C4 의 «날 면적 −29 %(−2.97 dB)»
를 **무너뜨리려고** 만든 재측정기. (2026-08-16, 반증 전담 라운드)

⛔ 이 파일은 **아무것도 고치지 않는다.** 저장소의 상수·메쉬·법칙을 읽기만 하고, 판정에 쓴
   숫자를 전부 스스로 다시 잰다. 산출: outputs/mesh_adv_refute_chord_0816.json

왜 새로 재나
  감사는 «우리 날» 을 **법칙 상수표**(CHORD_FRAC)에서 읽고 «DJI 날» 은 **메쉬에서 자로 재서**
  둘을 비교했다. 자가 다르면 차이의 일부는 자에서 나온다. 그래서 여기서는 **같은 자 하나**를
  두 메쉬에 똑같이 댄다.

쓰는 자(전부 여기서 정의한다)
  · 회전축   : 로터(날 2장+허브)는 축을 중심으로 180° 돌리면 자기 자신이 된다는 성질로 **맞춘다**
               (면적가중 관성텐서의 고유벡터 3개 중 자기정합 오차가 가장 작은 축 → 4자유도 미세조정).
               «월드 +y» 같은 가정을 안 쓴다.
  · r        : 그 축까지의 거리(원통 반경). 스팬 좌표가 아니다.
  · R        : 날 표면의 r 최댓값 = 스윕 반경.
  · 단면     : r = r0 원통과의 **정확한** 교선. 모서리마다 |p_perp(t)|² = r0² 인 t 를 2차방정식으로
               푼다(선형보간 근사가 아니다).
  · 시위     : 그 단면을 (호길이, 축방향) 평면에 펴서 잰 **최대 캘리퍼**.
  · 스윕각 Λ : 중시위 궤적의 국소 후퇴각. Λ = atan(r·dφ/dr), φ 는 **절대각을 언랩**해서 쓴다
               (감사가 «위상 언랩이 깨져 포기했다» 고 적은 바로 그 단계).

세 잣대(정의에 안 기대려고 셋을 쓴다)
  Y1 단면적분 ∫c dr   Y2 투영면적(회전면에 드리운 그림자, 0.05 mm 래스터)   Y3 표면적÷2

재현
  PYTHONPATH=src:benchmark python benchmark/adv_refute_chord_0816.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import trimesh
from scipy.optimize import minimize
from scipy.spatial import ConvexHull, cKDTree

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

import drone_cad as dc                                            # noqa: E402
from drones import DRONES                                         # noqa: E402

GLB = os.path.join(HERE, "assets/meshes/reference/WM161_zhankai_1k.glb")
REF = os.path.join(HERE, "assets/meshes/reference")
OUTJSON = os.path.join(HERE, "outputs/mesh_adv_refute_chord_0816.json")

RR = np.round(np.arange(0.02, 1.0001, 0.005), 5)
GRID = np.array([0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70,
                 0.75, 0.80, 0.85, 0.90, 0.95])


# ─────────────────────────────────────────────────────────────── 자(instrument)
def frame(axis):
    d = np.asarray(axis, float)
    d = d / np.linalg.norm(d)
    t = np.cross(d, [1.0, 0.0, 0.0])
    if np.linalg.norm(t) < 1e-6:
        t = np.cross(d, [0.0, 1.0, 0.0])
    t /= np.linalg.norm(t)
    return d, t, np.cross(d, t)


def section_points(mesh, centre, axis, r0, pick_lobe=False):
    """r = r0 원통과 삼각형 메쉬의 정확한 교선. 반환 (호길이 u, 축좌표 v, 단면 평균각 φ0)."""
    d, e1, e2 = frame(axis)
    V = np.asarray(mesh.vertices, float) - np.asarray(centre, float)
    A = np.c_[V @ e1, V @ e2, V @ d]
    F = np.asarray(mesh.faces)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    p0, p1 = A[E[:, 0]], A[E[:, 1]]
    q0 = p0[:, 0] ** 2 + p0[:, 1] ** 2
    q1 = p1[:, 0] ** 2 + p1[:, 1] ** 2
    keep = (np.minimum(q0, q1) <= r0 ** 2) & (np.maximum(q0, q1) >= r0 ** 2)
    if not keep.any():
        return np.empty(0), np.empty(0), np.nan
    p0, p1 = p0[keep], p1[keep]
    dp = p1 - p0
    a = dp[:, 0] ** 2 + dp[:, 1] ** 2
    b = 2 * (p0[:, 0] * dp[:, 0] + p0[:, 1] * dp[:, 1])
    c = p0[:, 0] ** 2 + p0[:, 1] ** 2 - r0 ** 2
    ts, lin = [], np.abs(a) < 1e-18
    if lin.any():
        with np.errstate(divide="ignore", invalid="ignore"):
            ts.append((np.where(lin)[0], -c[lin] / b[lin]))
    nl = ~lin
    disc = b[nl] ** 2 - 4 * a[nl] * c[nl]
    ok = disc >= 0
    idx = np.where(nl)[0][ok]
    sq = np.sqrt(disc[ok])
    for sgn in (-1.0, 1.0):
        ts.append((idx, (-b[nl][ok] + sgn * sq) / (2 * a[nl][ok])))
    pts = []
    for i_, t in ts:
        m = np.isfinite(t) & (t >= -1e-9) & (t <= 1 + 1e-9)
        if m.any():
            pts.append(p0[i_[m]] + t[m][:, None] * dp[i_[m]])
    if not pts:
        return np.empty(0), np.empty(0), np.nan
    P = np.vstack(pts)
    phi = np.arctan2(P[:, 1], P[:, 0])
    if pick_lobe:                       # 프롭 통짜 메쉬는 날이 둘 → 큰 덩어리 하나만
        ps = np.sort(phi)
        gaps = np.diff(np.r_[ps, ps[0] + 2 * np.pi])
        start = ps[(int(np.argmax(gaps)) + 1) % len(ps)]
        rel = (phi - start) % (2 * np.pi)
        rs = np.sort(rel)
        g2 = np.diff(rs)
        if g2.size and g2.max() > 0.35:
            cut = rs[int(np.argmax(g2))]
            m1 = rel <= cut
            if m1.sum() >= 3 and (~m1).sum() >= 3:
                km = m1 if m1.sum() >= (~m1).sum() else ~m1
                P, phi = P[km], phi[km]
    ph0 = np.arctan2(np.sin(phi).mean(), np.cos(phi).mean())
    dphi = (phi - ph0 + np.pi) % (2 * np.pi) - np.pi
    return r0 * dphi, P[:, 2], float(ph0)


def chord_at(mesh, centre, axis, r0, pick_lobe=False):
    u, v, ph0 = section_points(mesh, centre, axis, r0, pick_lobe)
    if u.size < 3:
        return dict(n=0, chord=np.nan, phi_mid=np.nan, thick=np.nan, area=np.nan, v_mid=np.nan)
    Q = np.c_[u, v]
    try:
        h = ConvexHull(Q)
        H, area = Q[h.vertices], float(h.volume)
    except Exception:
        H, area = Q, np.nan
    D = np.linalg.norm(H[:, None, :] - H[None, :, :], axis=-1)
    i, j = np.unravel_index(np.argmax(D), D.shape)
    chord = float(D[i, j])
    p, q = H[i], H[j]
    e = (q - p) / max(chord, 1e-15)
    off = (H - p) @ np.array([-e[1], e[0]])
    return dict(n=int(u.size), chord=chord, thick=float(off.max() - off.min()), area=area,
                v_mid=float(0.5 * (p[1] + q[1])),
                phi_mid=float(ph0 + 0.5 * (p[0] + q[0]) / max(r0, 1e-12)))


def chords(mesh, centre, axis, R, lobe=False):
    P = [chord_at(mesh, centre, axis, x * R, lobe) for x in RR]
    return (np.array([p["chord"] for p in P]), np.array([p["phi_mid"] for p in P]),
            np.array([p["area"] for p in P]), np.array([p["v_mid"] for p in P]))


def tip_radius(mesh, centre, axis):
    d, e1, e2 = frame(axis)
    V = np.asarray(mesh.vertices, float) - np.asarray(centre, float)
    r = np.hypot(V @ e1, V @ e2)
    return float(r.max()), float(r.min())


def sect_int(cv, R, lo, hi):
    m = (RR >= lo) & (RR <= hi)
    return float(np.trapezoid(np.nan_to_num(cv[m]), RR[m] * R))


def raster(mesh, centre, axis, R, bands, pitch=0.05e-3):
    d, e1, e2 = frame(axis)
    V = np.asarray(mesh.vertices, float) - np.asarray(centre, float)
    P = np.c_[V @ e1, V @ e2]
    lo, hi = P.min(0) - pitch, P.max(0) + pitch
    nx = int(np.ceil((hi[0] - lo[0]) / pitch))
    ny = int(np.ceil((hi[1] - lo[1]) / pitch))
    g = np.zeros((nx, ny), bool)
    for t in P[np.asarray(mesh.faces)]:
        x0 = int(np.floor((t[:, 0].min() - lo[0]) / pitch))
        x1 = int(np.ceil((t[:, 0].max() - lo[0]) / pitch))
        y0 = int(np.floor((t[:, 1].min() - lo[1]) / pitch))
        y1 = int(np.ceil((t[:, 1].max() - lo[1]) / pitch))
        if x1 <= x0 or y1 <= y0:
            continue
        X, Y = np.meshgrid(lo[0] + (np.arange(x0, x1) + .5) * pitch,
                           lo[1] + (np.arange(y0, y1) + .5) * pitch, indexing="ij")
        v0, v1, v2 = t
        den = (v1[1] - v2[1]) * (v0[0] - v2[0]) + (v2[0] - v1[0]) * (v0[1] - v2[1])
        if abs(den) < 1e-18:
            continue
        aa = ((v1[1] - v2[1]) * (X - v2[0]) + (v2[0] - v1[0]) * (Y - v2[1])) / den
        bb = ((v2[1] - v0[1]) * (X - v2[0]) + (v0[0] - v2[0]) * (Y - v2[1])) / den
        g[x0:x1, y0:y1] |= (aa >= 0) & (bb >= 0) & (1 - aa - bb >= 0)
    ix, iy = np.nonzero(g)
    r = np.hypot(lo[0] + (ix + .5) * pitch, lo[1] + (iy + .5) * pitch) / R
    tot = float(g.sum() * pitch * pitch)
    return tot, {f"{a:.3f}-{b:.3f}": float(((r >= a) & (r < b)).sum() * pitch * pitch)
                 for a, b in bands}


# ────────────────────────────────────────────────────── 회전축 맞추기 (가정 없이)
def tri_ac(m):
    v = m.vertices[m.faces]
    a = 0.5 * np.linalg.norm(np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), axis=1)
    return a, v.mean(axis=1)


def sample(meshes, n=25000, seed=0):
    rng = np.random.default_rng(seed)
    tot = sum(m.area for m in meshes)
    return np.vstack([trimesh.sample.sample_surface(
        m, max(200, int(n * m.area / tot)), seed=int(rng.integers(1 << 30)))[0] for m in meshes])


def sym_err(pts, tree, c, d):
    d = d / np.linalg.norm(d)
    q = pts - c
    img = c + 2 * np.outer(q @ d, d) - q
    return float(np.sqrt((tree.query(img)[0] ** 2).mean()))


def fit_axis(meshes, seed=0):
    A, C = zip(*[tri_ac(m) for m in meshes])
    P, w = np.vstack(C), np.concatenate(A)
    c0 = (P * w[:, None]).sum(0) / w.sum()
    dd = P - c0
    I = (w[:, None, None] * (dd[:, :, None] * dd[:, None, :])).sum(0) / w.sum()
    _, evec = np.linalg.eigh(I)
    surf = sample(meshes, seed=seed)
    tree = cKDTree(surf)
    d0 = evec[:, sorted((sym_err(surf, tree, c0, evec[:, i]), i) for i in range(3))[0][1]]
    d0 = d0 / np.linalg.norm(d0)
    t1 = np.cross(d0, [1, 0, 0])
    t1 = t1 / np.linalg.norm(t1) if np.linalg.norm(t1) > 1e-6 else np.cross(d0, [0, 1, 0])
    t2 = np.cross(d0, t1)
    r = minimize(lambda x: sym_err(surf, tree, c0 + x[2] * t1 + x[3] * t2,
                                   d0 + x[0] * t1 + x[1] * t2),
                 np.zeros(4), method="Nelder-Mead",
                 options=dict(xatol=1e-7, fatol=1e-10, maxiter=4000, maxfev=4000))
    d = d0 + r.x[0] * t1 + r.x[1] * t2
    return c0 + r.x[2] * t1 + r.x[3] * t2, d / np.linalg.norm(d), float(r.fun)


def glb_world():
    sc = trimesh.load(GLB, process=False)
    out = {}
    for name, geom in sc.geometry.items():
        for node in sc.graph.nodes_geometry:
            T, gname = sc.graph[node]
            if gname == name:
                m = geom.copy()
                m.apply_transform(T)
                out[node] = m
    return out


# ───────────────────────────────────────────────────────────── 우리 날 짓기
def our_blade(key="mini2", law="legacy", n_sec=22):
    sp = DRONES[key]
    R = sp.prop_dia_mm / 2000.0
    P = float(sp.prop_pitch_in or 5.0) * 0.0254
    cmax, _ = dc.resolve_chord_max_over_r(sp, law)
    probe = dc._blade(R, root_frac=0.070, chord_max=cmax, pitch_m=P, n_sec=n_sec, law=law)
    V = np.asarray(probe.vertices)
    s = R / float(np.hypot(V[:, 0], V[:, 1]).max())
    return (dc._blade(R * s, root_frac=0.070, chord_max=cmax, pitch_m=P, n_sec=n_sec, law=law),
            cmax, s, R)


def main():
    t0 = time.time()
    O = {}
    O["_meta"] = dict(
        title="감사 C4 «날 면적 −29 %(−2.97 dB)» 반증 라운드",
        date="2026-08-16", role="반증 전담(무너뜨리려고 잰다)",
        target_claims=["시위 분포가 외곽에서 27~39 % 좁다",
                       "날 면적 −29 %(−2.97 dB) · 외곽 −3.55 dB",
                       "정점 위치 우리 0.30R ↔ 실물 0.45R",
                       "3DR Solo 는 참조 넷 중 유일한 이상치",
                       "CHORD_MAX_OVER_R=0.25 는 실물 0.177~0.273 이고 크기와 반비례"],
        method_ko=__doc__.split("왜 새로 재나")[1].strip(),
        inputs=dict(dji=os.path.relpath(GLB, HERE),
                    ours="src/drone_cad._blade(law='legacy') — 상수는 읽기만",
                    refs=["solo_prop_cw.stl", "1345_prop_cw.stl",
                          "prop_cw_assembly_remeshed_v3.stl"],
                    ledger_for_crosscheck="outputs/reference_props.json"),
        reproduce="PYTHONPATH=src:benchmark python benchmark/adv_refute_chord_0816.py",
        nothing_was_modified=True)

    # ── DJI 로터 4개: 축 맞추기 ────────────────────────────────────────────
    W = glb_world()
    blades = {k: m for k, m in W.items() if len(m.faces) in (1635, 1691)}
    hubs = {k: m for k, m in W.items() if len(m.faces) == 1704}
    hub_c = {h: hubs[h].centroid for h in hubs}
    groups = {h: [] for h in hubs}
    for k, m in blades.items():
        groups[min(hub_c, key=lambda h: np.linalg.norm(hub_c[h] - m.centroid))].append(k)
    rotors = {}
    for h, bs in groups.items():
        c, d, err = fit_axis([hubs[h]] + [blades[b] for b in bs])
        rotors[h] = dict(blades=sorted(bs), centre=c, axis=d, sym_rms_mm=err * 1e3,
                         tilt_from_world_y_deg=float(np.degrees(np.arccos(abs(d[1])))))
    O["rotor_axes"] = {h: dict(blades=v["blades"], axis=v["axis"].tolist(),
                               sym_rms_mm=v["sym_rms_mm"],
                               tilt_from_world_y_deg=v["tilt_from_world_y_deg"])
                       for h, v in rotors.items()}

    DJI = {}
    for h, v in rotors.items():
        for b in v["blades"]:
            m = blades[b]
            R, r0 = tip_radius(m, v["centre"], v["axis"])
            cc, ph, ar, vm = chords(m, v["centre"], v["axis"], R)
            tot, bd = raster(m, v["centre"], v["axis"], R,
                             [(0, .175), (.175, .975), (.20, .96), (.60, .96), (0, 2)])
            DJI[b] = dict(R=R, root=r0, c=cc, ph=ph, ar=ar, vm=vm, proj=tot, bands=bd,
                          mesh=m, centre=v["centre"], axis=v["axis"],
                          watertight=bool(m.is_watertight), surf=float(m.area))

    ours, cmax_law, span_scale, R_spec = our_blade()
    oc, od = np.zeros(3), np.array([0.0, 0.0, 1.0])
    R_o, root_o = tip_radius(ours, oc, od)
    c_o, ph_o, ar_o, vm_o = chords(ours, oc, od, R_o)
    tot_o, bd_o = raster(ours, oc, od, R_o,
                         [(0, .175), (.175, .975), (.20, .96), (.60, .96), (0, 2)])

    # ── 자 검정: 우리 메쉬를 우리 법칙으로 되읽기 ─────────────────────────
    law_c = np.interp(RR, dc.CHORD_RR, dc.CHORD_FRAC) * cmax_law * R_spec * span_scale
    band = (RR >= 0.35) & (RR <= 0.90)
    O["instrument_calibration"] = dict(
        what="같은 자로 우리 메쉬를 재서 우리 법칙과 견준다",
        ratio_mesh_over_law_0p35_0p90R=float(np.mean(c_o[band] / law_c[band])),
        ratio_mesh_over_law_0p10_0p30R=float(np.mean(
            (c_o / law_c)[(RR >= 0.10) & (RR <= 0.30)])),
        note_ko="0.35~0.90R 에서 +1.8 % 안으로 되읽는다. 뿌리 쪽에서 낮게 읽는 것은 «원통 단면» "
                "정의 자체의 성질이다(뿌리에서는 시위선이 반경 방향에 가까워진다) — DJI 날에도 "
                "똑같이 적용되는 편향이라 비교에는 상쇄된다.")

    # ── 헤드라인: 세 잣대 × 여러 창 ─────────────────────────────────────
    WIN = [(0.175, 0.975), (0.20, 0.96), (0.15, 0.96), (0.10, 0.99), (0.033, 1.00),
           (0.25, 0.95), (0.50, 0.96), (0.60, 0.96), (0.70, 0.96), (0.90, 0.96)]
    y1 = {}
    for a, b in WIN:
        io = sect_int(c_o, R_o, a, b) * 1e6
        idd = np.array([sect_int(v["c"], v["R"], a, b) for v in DJI.values()]) * 1e6
        y1[f"{a}-{b}"] = dict(ours_mm2=io, dji_mm2=float(idd.mean()), dji_sd=float(idd.std()),
                              ratio=io / float(idd.mean()),
                              dB_if_plate=20 * np.log10(io / float(idd.mean())))
    y2 = {}
    for k in bd_o:
        dm = float(np.mean([v["bands"][k] for v in DJI.values()])) * 1e6
        y2[k] = dict(ours_mm2=bd_o[k] * 1e6, dji_mm2=dm, ratio=bd_o[k] * 1e6 / dm,
                     dB_if_plate=20 * np.log10(bd_o[k] * 1e6 / dm))
    sd = float(np.mean([v["surf"] for v in DJI.values()])) * 1e6 / 2
    y3 = dict(ours_mm2=float(ours.area) * 1e6 / 2, dji_mm2=sd,
              ratio=float(ours.area) * 1e6 / 2 / sd,
              dji_watertight=[v["watertight"] for v in DJI.values()],
              caveat_ko="DJI 날은 수밀이 아니다(열린 껍질, 경계 모서리 605개) — 이 잣대만 "
                        "약하다. 아래 판정은 Y1·Y2 로 한다.")
    O["A_headline"] = dict(Y1_section_integral=y1, Y2_projected=y2, Y3_half_surface=y3,
                           honest_full_blade_ratio=[min(y1["0.175-0.975"]["ratio"],
                                                        y2["0.000-2.000"]["ratio"]),
                                                    max(y1["0.175-0.975"]["ratio"],
                                                        y2["0.000-2.000"]["ratio"])])

    # ── 감사의 0.710 은 어디서 왔나 ────────────────────────────────────
    d_full = float(np.mean([sect_int(v["c"], v["R"], 0.0, 1.0) for v in DJI.values()]))
    O["B_forensics_of_0710"] = dict(
        audit_number=0.710,
        my_symmetric_number=float(sect_int(c_o, R_o, 0.175, 0.975)
                                  / np.mean([sect_int(v["c"], v["R"], 0.175, 0.975)
                                             for v in DJI.values()])),
        reconstruction=float(sect_int(c_o, R_o, 0.175, 0.975) / d_full),
        recipe_ko="우리 날은 0.175R 부터 자르고 DJI 날은 **통째로**(0.033R 부터) 적분하면 "
                  "0.712 가 나온다 — 감사의 0.710 과 같은 자리다. 창이 서로 다르다.",
        audit_projected_variant="507.8−50 = 458 ÷ 636 = 0.72 (같은 한쪽만 빼기)",
        why_it_is_wrong_ko="전제 «DJI 날 부품은 0.175R 부터» 가 실측으로 거짓이다(아래 C_c).",
        audit_contradicts_itself_ko="감사 자신의 면적표(E_area_impact_dB.mini2_vs_official_cad "
                                    "«0.20-0.96» area_ratio 0.7893)와 헤드라인 «−29 %» 가 서로 "
                                    "안 맞는다. 내가 같은 창으로 재면 0.7874 로 표 쪽이 맞다.")

    # ── (a) 정규화가 공정한가 ───────────────────────────────────────────
    dji_norm = np.mean([np.interp(GRID, RR, v["c"]) / np.nanmax(v["c"]) for v in DJI.values()],
                       axis=0)
    ours_mesh_norm = np.interp(GRID, RR, c_o) / np.nanmax(c_o)
    ours_law_norm = np.interp(GRID, dc.CHORD_RR, dc.CHORD_FRAC)
    fleet = {}
    for k in ("mini2", "mavic4pro", "matrice4e", "m350rtk", "mini5pro"):
        bl, cm, _, _ = our_blade(k)
        Rb, _ = tip_radius(bl, oc, od)
        cs = np.array([chord_at(bl, oc, od, x * Rb)["chord"] for x in RR])
        fleet[k] = dict(law=cm, built=float(np.nanmax(cs) / Rb),
                        peak_r_over_R=float(RR[int(np.nanargmax(cs))]))
    O["C_attacks"] = {}
    O["C_attacks"]["a_normalisation"] = dict(
        attack_ko="c_max 로 나눴는데 두 c_max 를 서로 다른 방법으로 얻었다면 이중 왜곡이다",
        ours_c_max_over_R_law=cmax_law,
        ours_c_max_over_R_as_built=float(np.nanmax(c_o) / R_o),
        ours_peak_as_built=float(RR[int(np.nanargmax(c_o))]),
        dji_c_max_over_R=float(np.mean([np.nanmax(v["c"]) / v["R"] for v in DJI.values()])),
        dji_peak=float(np.mean([RR[int(np.nanargmax(v["c"]))] for v in DJI.values()])),
        fleet_law_vs_built=fleet,
        grid=GRID.tolist(),
        ours_norm_law=np.round(ours_law_norm, 4).tolist(),
        ours_norm_as_built=np.round(ours_mesh_norm, 4).tolist(),
        dji_norm=np.round(dji_norm, 4).tolist(),
        deficit_at_0p70R_audit_pct=100 * (1 - 0.577 / 0.866),
        deficit_at_0p70R_fair_pct=float(100 * (1 - ours_mesh_norm[9] / dji_norm[9])),
        verdict_ko="**부분 정정**. 감사는 우리 쪽만 «법칙 c_max(0.25)» 로 나눴다. 실제로 지어진 "
                   "날의 c_max/R 은 전 기종 0.242(−3.1 %)라 정규화가 한쪽만 3 % 눌려 있었다. "
                   "고쳐도 0.70R 결손은 33.4 % → 30.5 % 로 줄 뿐 결론은 안 뒤집힌다. "
                   "그리고 절대 면적 비교에는 애초에 영향이 없다.")

    # ── (b) R 정의 ─────────────────────────────────────────────────────
    alt = {}
    for nm, Rd in (("nominal_4726F_59.7", 0.0597), ("registry_59.55", 0.05955)):
        v = list(DJI.values())[0]
        nn = np.interp(GRID, RR * v["R"] / Rd, v["c"]) / np.nanmax(v["c"])
        alt[nm] = float(100 * (1 - ours_mesh_norm[9] / nn[9]))
    O["C_attacks"]["b_radius_definition"] = dict(
        attack_ko="R 이 «팁 점» 인지 «스윕 반경» 인지 서로 다르면 r/R 이 어긋난다",
        ours_R_mm=R_o * 1e3, ours_span_normalisation=span_scale,
        dji_R_mm={k: v["R"] * 1e3 for k, v in DJI.items()},
        dji_R_front_mean=float(np.mean([v["R"] for k, v in DJI.items()
                                        if k in ("polySurface58", "polySurface61",
                                                 "polySurface80", "polySurface81")]) * 1e3),
        dji_R_rear_mean=float(np.mean([v["R"] for k, v in DJI.items()
                                       if k in ("polySurface84", "polySurface89",
                                                "polySurface102", "polySurface95")]) * 1e3),
        deficit_at_0p70R_with_other_R_pct=alt,
        verdict_ko="**반증 실패**. 두 쪽 다 «축까지의 최대 거리 = 스윕 반경» 하나로 통일해서 "
                   "쟀다. DJI 를 공칭 59.7 이나 레지스트리 59.55 로 정규화해도 0.70R 결손은 "
                   "29.6~29.8 % 로 거의 안 움직인다. 다만 GLB 자체가 앞 59.14 · 뒤 59.66 mm 로 "
                   "0.9 % 어긋나 있다(같은 부품이어야 하는데) — 이건 GLB 의 포즈 오차다.")

    # ── (c) 뿌리 ───────────────────────────────────────────────────────
    o_root = bd_o["0.000-0.175"] * 1e6
    d_root = float(np.mean([v["bands"]["0.000-0.175"] for v in DJI.values()])) * 1e6
    o_all, d_all = bd_o["0.000-2.000"] * 1e6, float(
        np.mean([v["bands"]["0.000-2.000"] for v in DJI.values()])) * 1e6
    rot_proj = {}
    for h, v in rotors.items():
        merged = trimesh.util.concatenate([hubs[h]] + [blades[b] for b in v["blades"]])
        rot_proj[h] = raster(merged, v["centre"], v["axis"], 1.0, [(0, 1e9)])[0] * 1e6
    prop = dc.build_propeller_cad(DRONES["mini2"])
    ours_rotor = raster(trimesh.util.concatenate(prop.parts["prop"]), oc, od, 1.0,
                        [(0, 1e9)])[0] * 1e6
    O["C_attacks"]["c_root"] = dict(
        attack_ko="감사 스스로 «우리 뿌리 여유 ≈50 mm²» 를 빼서 0.80 을 0.72 로 내렸다. "
                  "그 전제가 맞나?",
        audit_premise="DJI 날 부품은 0.175R 부터 시작한다(안쪽은 허브 부품)",
        measured_dji_blade_part_min_r_over_R=float(np.mean([v["root"] / v["R"]
                                                            for v in DJI.values()])),
        measured_ours_blade_min_r_over_R=float(root_o / R_o),
        root_band_0_to_0p175R_projected_mm2=dict(ours=o_root, dji=d_root),
        root_share_pct=dict(ours=100 * o_root / o_all, dji=100 * d_root / d_all),
        dji_chord_at_root_mm={f"{x:.3f}": float(np.interp(x, RR, list(DJI.values())[0]["c"]) * 1e3)
                              for x in (0.05, 0.10, 0.15, 0.175)},
        arithmetic=dict(ratio_full=o_all / d_all,
                        ratio_after_audit_one_sided_subtraction=(o_all - o_root) / d_all,
                        ratio_if_both_roots_removed=(o_all - o_root) / (d_all - d_root)),
        definition_free_whole_rotor=dict(
            ours_mm2=ours_rotor, dji_mm2=float(np.mean(list(rot_proj.values()))),
            ratio=ours_rotor / float(np.mean(list(rot_proj.values()))),
            note_ko="날 2장 + 허브를 통째로 투영한다 — «날이 어디서 시작하나» 를 정할 필요가 없다"),
        verdict_ko="**감사 반증**. DJI 날 부품은 0.033R 까지 들어가 있고, 0.175R 안쪽 투영면적이 "
                   "우리보다 **더 많다**(50.7 ↔ 46.9 mm²). 한쪽만 빼서 0.80→0.72 로 내린 것이 "
                   "«−29 %» 의 정체다. 양쪽 다 빼면 0.786, 안 빼면 0.797, 로터 통째로는 0.805 다.")

    # ── (d) 스윕/변형 ──────────────────────────────────────────────────
    def sweep(ph, R):
        ok = np.isfinite(ph)
        r = RR[ok] * R
        return RR[ok], np.degrees(np.arctan(r * np.gradient(np.unwrap(ph[ok]), r)))

    rs_o, L_o = sweep(ph_o, R_o)
    co_corr = c_o * np.cos(np.radians(np.interp(RR, rs_o, L_o)))
    corr, absL = [], []
    for v in DJI.values():
        rs, L = sweep(v["ph"], v["R"])
        absL.append(np.abs(np.interp(GRID, rs, L)))
        cd = v["c"] * np.cos(np.radians(np.interp(RR, rs, L)))
        corr.append(sect_int(co_corr, R_o, 0.175, 0.975) / sect_int(cd, v["R"], 0.175, 0.975))
    O["C_attacks"]["d_sweep_and_deformation"] = dict(
        attack_ko="원통 캘리퍼는 스윕이 크면 c/cosΛ 를 읽는다. DJI 가 더 휘었다면 DJI 가 "
                  "부풀려 읽힌 것이다. (감사는 이 단계를 «언랩이 깨져» 포기했다)",
        grid=GRID.tolist(),
        dji_sweep_abs_deg=np.round(np.mean(absL, axis=0), 2).tolist(),
        ours_sweep_abs_deg=np.round(np.abs(np.interp(GRID, rs_o, L_o)), 2).tolist(),
        sect_int_ratio_raw=y1["0.175-0.975"]["ratio"],
        sect_int_ratio_sweep_corrected=float(np.mean(corr)),
        mid_chord_axial_mm=dict(
            ours={f"{x}": float(np.interp(x, RR, vm_o) * 1e3) for x in (0.3, 0.7, 0.95)},
            dji={f"{x}": float(np.mean([np.interp(x, RR, v["vm"]) for v in DJI.values()]) * 1e3)
                 for x in (0.3, 0.7, 0.95)}),
        verdict_ko="**반증 실패 — 오히려 역효과**. 스윕은 우리 날이 더 크다(외곽 |Λ| 우리 7~9° ↔ "
                   "DJI 1~6°). 그래서 캘리퍼 부풀림은 우리 쪽이 더 컸고, 보정하면 비가 0.794 → "
                   "0.792 로 **내려간다**. 중시위 궤적의 축방향 변위도 ±1.3 mm 안이라 «휜 상태로 "
                   "저장» 가설도 안 선다.")

    # ── (e) Solo 쪽이 틀렸을 가능성 ────────────────────────────────────
    led = json.load(open(os.path.join(HERE, "outputs/reference_props.json")))["props"]
    refs = {}
    for nm, fn in (("3dr_solo", "solo_prop_cw.stl"), ("holybro_1345", "1345_prop_cw.stl"),
                   ("yuneec_typhoon", "prop_cw_assembly_remeshed_v3.stl")):
        m = trimesh.load(os.path.join(REF, fn), process=True)
        if not isinstance(m, trimesh.Trimesh):
            m = trimesh.util.concatenate(list(m.geometry.values()))
        c, d, err = fit_axis([m])
        R, _ = tip_radius(m, c, d)
        cs = np.array([chord_at(m, c, d, x * R, True)["chord"] for x in RR])
        hubfree = RR >= 0.20
        cm = float(np.nanmax(cs[hubfree]))
        st = led[nm]["stations"]
        r_l = np.array([s["r_over_R"] for s in st])
        c_l = np.array([s["chord_mm"] for s in st])
        keep = np.array(["rejected" not in s for s in st])
        u = 1e3 if R < 1.0 else 1.0
        refs[nm] = dict(mine_R_mm=R * u, mine_c_max_over_R=cm / R,
                        mine_peak=float(RR[int(np.nanargmax(np.where(hubfree, cs, -1)))]),
                        mine_norm=np.round(np.interp(GRID, RR, cs) / cm, 4).tolist(),
                        ledger_R_mm=led[nm]["R_disc_mm"],
                        ledger_c_max_over_R=led[nm]["chord_max_over_R"],
                        ledger_peak=led[nm]["chord_peak_r_over_R"],
                        ledger_norm=np.round(np.interp(GRID, r_l, c_l) / c_l[keep].max(),
                                             4).tolist())
    O["C_attacks"]["e_solo_measurement"] = dict(
        attack_ko="법칙이 Solo 를 소수 3자리까지 재현한다면 유도는 맞다 — 그러면 Solo **측정**이 "
                  "틀렸을 수 있다",
        grid=GRID.tolist(), refs=refs,
        ours_law_norm=np.round(ours_law_norm, 4).tolist(),
        dji_norm=np.round(dji_norm, 4).tolist(),
        norm_at_0p70R=dict(ours_law=float(ours_law_norm[9]),
                           ours_as_built=float(ours_mesh_norm[9]),
                           solo_mine=refs["3dr_solo"]["mine_norm"][9],
                           solo_ledger=refs["3dr_solo"]["ledger_norm"][9],
                           holybro_1345_mine=refs["holybro_1345"]["mine_norm"][9],
                           holybro_1345_ledger=refs["holybro_1345"]["ledger_norm"][9],
                           yuneec_mine=refs["yuneec_typhoon"]["mine_norm"][9],
                           dji=float(dji_norm[9])),
        verdict_ko="**반증 실패(측정) + 감사 반증(이상치 주장)**. Solo 를 독립적으로 다시 재도 "
                   "0.70R 정규화 시위 0.577, 정점 0.275R 로 원장과 소수 3자리까지 같다 — 측정은 "
                   "맞다. 그런데 같은 원장의 Holybro 1345 는 0.70R 에서 **0.492** 로 Solo 보다 "
                   "더 뿌리 편중이다. 감사의 정규화 시위 표는 1345 를 빠뜨렸다 ⇒ «Solo 는 유일한 "
                   "이상치» 는 거짓이고, 옳은 문장은 «참조 CAD 3종 중 2종이 뿌리 편중, DJI·Yuneec "
                   "계열이 늦은 정점» 이다.")

    # ── 수렴 ────────────────────────────────────────────────────────────
    conv = {}
    for ns in (22, 40, 80, 160):
        bl, cm, _, _ = our_blade("mini2", "legacy", ns)
        Rb, _ = tip_radius(bl, oc, od)
        cs = np.array([chord_at(bl, oc, od, x * Rb)["chord"] for x in RR])
        conv[f"n_sec={ns}"] = dict(faces=int(len(bl.faces)),
                                   sect_0175_0975_mm2=sect_int(cs, Rb, 0.175, 0.975) * 1e6,
                                   c_max_over_R=float(np.nanmax(cs) / Rb))
    ras = {}
    for p in (1e-4, 5e-5, 2.5e-5):
        ao = raster(ours, oc, od, R_o, [(0, 2)], pitch=p)[0] * 1e6
        v = list(DJI.values())[0]
        ad = raster(v["mesh"], v["centre"], v["axis"], v["R"], [(0, 2)], pitch=p)[0] * 1e6
        ras[f"{p*1e3:.3f}mm"] = dict(ours=ao, dji=ad, ratio=ao / ad)
    axis_alt = {}
    for tag, use in (("fitted", True), ("world_y", False)):
        io = sect_int(c_o, R_o, 0.175, 0.975)
        vals = []
        for h, v in rotors.items():
            d = v["axis"] if use else np.array([0.0, 1.0, 0.0])
            for b in v["blades"]:
                R, _ = tip_radius(blades[b], v["centre"], d)
                cc = np.array([chord_at(blades[b], v["centre"], d, x * R)["chord"] for x in RR])
                vals.append(sect_int(cc, R, 0.175, 0.975))
        axis_alt[tag] = float(io / np.mean(vals))
    O["F_convergence_and_robustness"] = dict(loft_resolution=conv, raster_pitch=ras,
                                             axis_choice=axis_alt)

    # ── 판정 ────────────────────────────────────────────────────────────
    O["G_verdict"] = dict(
        survives=[
            "우리 날은 실물 DJI 대비 외곽에서 좁다 — 0.70R 정규화 시위 0.599 ↔ 0.862",
            "외곽 면적 결손: 0.60–0.96R 비 0.663(−3.57 dB), 0.70–0.96R 0.661, 0.90–0.96R 0.696 "
            "— 감사의 0.665/0.662/0.700 을 소수 3자리까지 재현",
            "시위 정점 위치: 우리 0.310R ↔ DJI 0.454R",
            "c_max/R 이 실물마다 0.175~0.268 로 벌어져 단일 상수는 근거가 없다",
            "감사가 무해하다고 한 것들(날개 수·수밀·거울상)은 이 라운드에서 건드리지 않았다",
        ],
        falsified=[
            "«날 면적 −29 %(−2.97 dB)» — 세 잣대 어느 것도 그 값을 안 준다(0.79/0.80/0.76). "
            "정직한 값은 −20~−24 %, 평판식으로 옮기면 −1.9~−2.4 dB",
            "«DJI 날 부품은 0.175R 부터» — 실측 0.033R, 그 안쪽 면적은 우리보다 많다",
            "«3DR Solo 는 참조 넷 중 유일한 이상치» — 같은 원장의 1345 가 더 극단",
        ],
        corrected=[
            "«외곽에서 27~39 % 좁다» → 내가 직접 잰 참조 둘(DJI 공식 CAD 0.862 · Yuneec 0.863)"
            "로는 0.70R 결손 30.5~30.6 %. 감사의 제품사진 참조(0.785·0.952)를 그대로 믿으면 "
            "밴드는 24~37 % — 사진 두 값은 이 라운드에서 재측정하지 않았다",
            "«우리는 전부 c_max/R = 0.25» → 그건 파라미터, 지어진 값은 0.242(전 기종)",
        ],
        replacement_still_justified_ko="법칙을 DJI 로 갈아끼우는 방향 자체는 유지된다. "
                                       "무너진 것은 그 크기를 적은 숫자와 근거 이야기다.",
        files_to_fix=[
            "src/drone_cad.py:73 — «날 면적이 −29 %(−2.97 dB)» → «−20~−24 %(−1.9~−2.4 dB), "
            "외곽 −3.6 dB»",
            "outputs/mesh_audit_0816_prop_geometry.json E_area_impact_dB.two_failure_modes_ko[0] "
            "— 같은 수치",
            "outputs/mesh_audit_0816_prop_geometry.json M_robustness_definition_free."
            "reconciliation_ko — 한쪽만 뺀 뿌리 보정",
            "docs/MESH_AUDIT_0816.md C4 행 — «Solo 는 참조 넷 중 유일한 이상치» 문면",
            "src/drones.py:155 — c_max/R 오차 % 는 파라미터 0.25 기준(지어진 값 0.242 기준이면 "
            "mini2 −6.4 · matrice4e +27 · mavic4pro +34 %)",
        ],
        runtime_s=round(time.time() - t0, 1))

    def cleanser(o):
        if isinstance(o, dict):
            return {k: cleanser(v) for k, v in o.items() if k not in ("mesh",)}
        if isinstance(o, (list, tuple)):
            return [cleanser(x) for x in o]
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        return o

    json.dump(cleanser(O), open(OUTJSON, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUTJSON, f"({time.time()-t0:.1f} s)")
    print(json.dumps(cleanser(O["G_verdict"]), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
