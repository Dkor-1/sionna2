# -*- coding: utf-8 -*-
"""치수 앵커 감사 6단계 — 블레이드 **면적**(플랜폼) 결손을 정량화한다."""
import json, sys
import numpy as np
import trimesh
sys.path.insert(0, "/workspace/sionna/src")
import drone_cad as dc
from drones import DRONES, build_propeller

GLB = "/workspace/sionna/assets/meshes/reference/WM161_zhankai_1k.glb"
B = ["polySurface58", "polySurface61", "polySurface80", "polySurface81",
     "polySurface84", "polySurface89", "polySurface95", "polySurface102"]


def planform_outside(V, F, axis, cen, rmin):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    c = V[F].mean(1)
    ax = [i for i in range(3) if i != axis]
    r = np.hypot(c[:, ax[0]] - cen[0], c[:, ax[1]] - cen[1])
    m = r >= rmin
    return float(0.5 * np.abs(n[m, axis]).sum()), float(0.5 * np.linalg.norm(n[m], axis=1).sum())


def main(out):
    res = {}
    # ── DJI 실물 CAD ────────────────────────────────────────────────────────
    s = trimesh.load(GLB)
    dji = []
    hubs = {}
    parts = {}
    for name in s.graph.nodes_geometry:
        T, g = s.graph[name]
        if g in B:
            m = s.geometry[g].copy(); m.apply_transform(T)
            parts[g] = m
    # 로터별 짝 → 팁투팁 중점 = 허브
    cen2 = {k: np.asarray(v.vertices)[:, [0, 2]].mean(0) for k, v in parts.items()}
    keys = list(parts); used = set(); pairs = []
    for k in keys:
        if k in used:
            continue
        d = sorted(((np.linalg.norm(cen2[k] - cen2[j]), j) for j in keys if j != k and j not in used))
        pairs.append((k, d[0][1])); used |= {k, d[0][1]}
    for ka, kb in pairs:
        A = np.asarray(parts[ka].vertices)[:, [0, 2]]
        Bv = np.asarray(parts[kb].vertices)[:, [0, 2]]
        d2 = ((A[:, None] - Bv[None]) ** 2).sum(-1)
        i, j = np.unravel_index(np.argmax(d2), d2.shape)
        cen = 0.5 * (A[i] + Bv[j]); R = 0.5 * float(np.sqrt(d2[i, j]))
        for kk in (ka, kb):
            V = np.asarray(parts[kk].vertices); F = np.asarray(parts[kk].faces)
            pf, sf = planform_outside(V, F, 1, cen, 0.10 * R)
            dji.append(dict(part=kk, R_mm=R * 1000, planform_cm2=pf * 1e4, surf_cm2=sf * 1e4))
    res["dji_mini2_cad_blades"] = dji
    dji_pf = float(np.mean([d["planform_cm2"] for d in dji]))
    dji_sf = float(np.mean([d["surf_cm2"] for d in dji]))
    dji_R = float(np.mean([d["R_mm"] for d in dji]))

    # ── 우리 프롭 (mini2) — 같은 자, 같은 r>=0.10R 컷 ────────────────────────
    spec = DRONES["mini2"]
    m = build_propeller(spec, n=24)
    V = np.asarray(m.v, float); F = np.asarray(m.f, int)
    R_ours = spec.prop_dia_mm / 2000.0
    pf, sf = planform_outside(V, F, 2, (0.0, 0.0), 0.10 * R_ours)
    ours_pf_blade = pf * 1e4 / 2.0                    # 2날 → 1장당
    ours_sf_blade = sf * 1e4 / 2.0
    res["ours_mini2_prop"] = dict(R_mm=R_ours * 1000, planform_cm2_per_blade=ours_pf_blade,
                                  surf_cm2_per_blade=ours_sf_blade)
    res["mini2_blade_area_compare"] = dict(
        dji_planform_cm2=round(dji_pf, 3), ours_planform_cm2=round(ours_pf_blade, 3),
        planform_err_pct=round(100 * (ours_pf_blade - dji_pf) / dji_pf, 2),
        dji_surface_cm2=round(dji_sf, 3), ours_surface_cm2=round(ours_sf_blade, 3),
        surface_err_pct=round(100 * (ours_sf_blade - dji_sf) / dji_sf, 2),
        dji_R_mm=round(dji_R, 2), ours_R_mm=round(R_ours * 1000, 2))

    # ── 시위분포만으로 본 면적 (스팬 적분), 안/밖 나눠서 ─────────────────────
    d = json.load(open("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/dji_prop.json"))
    st = {}
    for k in [k for k in d if not k.startswith("_")]:
        for row in d[k]["stations"]:
            st.setdefault(round(row["r_over_R"], 4), []).append(row["chord_over_R"])
    rr = np.array(sorted(st))
    cd = np.array([np.median(st[k]) for k in rr])
    co = np.interp(rr, dc.CHORD_RR, dc.CHORD_FRAC) * dc.CHORD_MAX_OVER_R
    sel_in = (rr >= 0.175) & (rr < 0.5)
    sel_out = rr >= 0.5
    sel_all = rr >= 0.175
    def integ(y, m):
        return float(np.trapezoid(y[m], rr[m]))
    res["chord_integral"] = dict(
        note="c/R 를 r/R 로 적분 = 블레이드 면적/R^2. r/R>=0.175 (허브 제외)",
        dji_all=round(integ(cd, sel_all), 5), ours_all=round(integ(co, sel_all), 5),
        err_all_pct=round(100 * (integ(co, sel_all) / integ(cd, sel_all) - 1), 2),
        dji_inboard=round(integ(cd, sel_in), 5), ours_inboard=round(integ(co, sel_in), 5),
        err_inboard_pct=round(100 * (integ(co, sel_in) / integ(cd, sel_in) - 1), 2),
        dji_outboard=round(integ(cd, sel_out), 5), ours_outboard=round(integ(co, sel_out), 5),
        err_outboard_pct=round(100 * (integ(co, sel_out) / integ(cd, sel_out) - 1), 2),
        dji_chord_peak_rr=float(rr[int(np.argmax(cd))]), ours_chord_peak_rr=0.30,
        dji_chord_max_over_R=round(float(cd.max()), 4), ours_chord_max_over_R=dc.CHORD_MAX_OVER_R)

    # ── 참조 3종(현행 법칙의 근거)의 시위 피크 — 대조군 ────────────────────
    rp = json.load(open("/workspace/sionna/outputs/reference_props.json"))["props"]
    res["reference_props_peak"] = {k: dict(chord_max_over_R=v["chord_max_over_R"],
                                           chord_peak_r_over_R=v["chord_peak_r_over_R"])
                                   for k, v in rp.items()}
    # 참조 Solo 의 c/cmax 곡선을 우리 법칙과 비교(법칙이 자기 근거를 재현하는가)
    for k, v in rp.items():
        stt = [s for s in v["stations"] if "rejected" not in s]
        r2 = np.array([s["r_over_R"] for s in stt]); c2 = np.array([s["chord_over_R"] for s in stt])
        cmx = c2.max()
        ours = np.interp(r2, dc.CHORD_RR, dc.CHORD_FRAC)
        res.setdefault("law_vs_reference", {})[k] = dict(
            rms_frac_err=round(float(np.sqrt(np.mean((ours - c2 / cmx) ** 2))), 4),
            area_err_pct=round(100 * (float(np.trapezoid(ours * dc.CHORD_MAX_OVER_R, r2))
                                      / float(np.trapezoid(c2, r2)) - 1), 2))
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "dji_mini2_cad_blades"},
                     ensure_ascii=False, indent=1))
    print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1])
