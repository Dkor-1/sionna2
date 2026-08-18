"""Step 7 - close the remaining holes: (e) done on the hub-free radius range, per-blade sweep,
axis sensitivity, watertightness, and the final apples-to-apples table."""
import json
import sys

import numpy as np
import trimesh
from scipy.optimize import minimize
from scipy.spatial import cKDTree

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad")

import drone_cad as dc
import propmeas as pm
from drones import DRONES
from s1_glb import world_meshes, sample_surface, tri_areas_centroids, area_inertia, sym_err

SP = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad"
ROT = json.load(open(f"{SP}/glb_rotors.json"))
GLB = "/workspace/sionna/assets/meshes/reference/WM161_zhankai_1k.glb"
rr = np.round(np.arange(0.02, 1.0001, 0.005), 5)
grid = np.array([0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80,
                 0.85, 0.90, 0.95])
OUT = {}

spec = DRONES["mini2"]
R_ours = spec.prop_dia_mm / 1000.0 / 2.0
P = float(spec.prop_pitch_in) * 0.0254
cmax_law, _ = dc.resolve_chord_max_over_r(spec, "legacy")
probe = dc._blade(R_ours, root_frac=0.070, chord_max=cmax_law, pitch_m=P, n_sec=22, law="legacy")
V = np.asarray(probe.vertices)
scale = R_ours / float(np.hypot(V[:, 0], V[:, 1]).max())
ours = dc._blade(R_ours * scale, root_frac=0.070, chord_max=cmax_law, pitch_m=P,
                 n_sec=22, law="legacy")
oc, od = np.zeros(3), np.array([0.0, 0.0, 1.0])
R_o, _ = pm.tip_radius(ours, oc, od)
c_o = np.array([pm.chord_at(ours, oc, od, x * R_o)["chord"] for x in rr])

sc, W = world_meshes(GLB)
blades = {k: m for k, m in W.items() if len(m.faces) in (1635, 1691)}


def sect_int(cv, R, lo, hi):
    m = (rr >= lo) & (rr <= hi)
    return float(np.trapezoid(np.nan_to_num(cv[m]), rr[m] * R))


# ---------------------------------------------------- axis sensitivity + per-blade sweep
sens = {}
for tag, use_fit in (("fitted_axis", True), ("world_y_axis", False)):
    ratios, sweeps, wt = [], [], []
    for hub, info in ROT.items():
        c = np.array(info["centre_m"])
        d = np.array(info["axis"]) if use_fit else np.array([0.0, 1.0, 0.0])
        for b in info["blades"]:
            m = blades[b]
            R, r0 = pm.tip_radius(m, c, d)
            prof = [pm.chord_at(m, c, d, x * R) for x in rr]
            cc = np.array([p["chord"] for p in prof])
            ph = np.array([p["phi_mid"] for p in prof])
            ok = np.isfinite(ph)
            Lam = np.degrees(np.arctan(rr[ok] * R * np.gradient(np.unwrap(ph[ok]), rr[ok] * R)))
            ratios.append(dict(R_mm=R * 1000, root_over_R=r0 / R,
                               c_max_over_R=float(np.nanmax(cc) / R),
                               peak=float(rr[int(np.nanargmax(cc))]),
                               sect_175_975=sect_int(cc, R, 0.175, 0.975) * 1e6,
                               sect_60_96=sect_int(cc, R, 0.60, 0.96) * 1e6,
                               norm=(np.interp(grid, rr, cc) / np.nanmax(cc)).tolist(),
                               sweep_abs=np.abs(np.interp(grid, rr[ok], Lam)).tolist()))
            wt.append(bool(m.is_watertight))
    o175 = sect_int(c_o, R_o, 0.175, 0.975) * 1e6
    o60 = sect_int(c_o, R_o, 0.60, 0.96) * 1e6
    d175 = float(np.mean([x["sect_175_975"] for x in ratios]))
    d60 = float(np.mean([x["sect_60_96"] for x in ratios]))
    sens[tag] = dict(
        dji_R_mm=float(np.mean([x["R_mm"] for x in ratios])),
        dji_c_max_over_R=float(np.mean([x["c_max_over_R"] for x in ratios])),
        dji_peak=float(np.mean([x["peak"] for x in ratios])),
        ratio_175_975=o175 / d175, ratio_60_96=o60 / d60,
        dji_norm=np.round(np.mean([x["norm"] for x in ratios], axis=0), 4).tolist(),
        dji_sweep_abs_deg=np.round(np.mean([x["sweep_abs"] for x in ratios], axis=0), 2).tolist(),
        dji_watertight=wt)
    print(f"[{tag}] dji R {sens[tag]['dji_R_mm']:.3f} c_max/R {sens[tag]['dji_c_max_over_R']:.4f} "
          f"peak {sens[tag]['dji_peak']:.3f}  ratio(0.175-0.975) {sens[tag]['ratio_175_975']:.4f} "
          f"ratio(0.60-0.96) {sens[tag]['ratio_60_96']:.4f}")
print("[sweep |L| deg] dji", sens["fitted_axis"]["dji_sweep_abs_deg"])
ok = np.isfinite(np.array([pm.chord_at(ours, oc, od, x * R_o)["phi_mid"] for x in rr]))
pho = np.array([pm.chord_at(ours, oc, od, x * R_o)["phi_mid"] for x in rr])
Lo = np.degrees(np.arctan(rr[ok] * R_o * np.gradient(np.unwrap(pho[ok]), rr[ok] * R_o)))
print("[sweep |L| deg] ours", np.round(np.abs(np.interp(grid, rr[ok], Lo)), 2).tolist())
OUT["axis_sensitivity_and_sweep"] = sens
OUT["axis_sensitivity_and_sweep"]["ours_sweep_abs_deg"] = np.round(
    np.abs(np.interp(grid, rr[ok], Lo)), 2).tolist()
OUT["axis_sensitivity_and_sweep"]["ours_watertight"] = bool(ours.is_watertight)

# ---------------------------------------------------- (e) reference props, hub-free range
def fit_axis(mesh, n=30000):
    A, C = tri_areas_centroids(mesh)
    c0, I = area_inertia(C, A)
    ev, evec = np.linalg.eigh(I)
    surf = sample_surface([mesh], n)
    tree = cKDTree(surf)
    cands = sorted((sym_err(surf, tree, c0, evec[:, i]), i) for i in range(3))
    d0 = evec[:, cands[0][1]]
    d0 = d0 / np.linalg.norm(d0)
    t1 = np.cross(d0, [1, 0, 0])
    t1 = t1 / np.linalg.norm(t1) if np.linalg.norm(t1) > 1e-6 else np.cross(d0, [0, 1, 0])
    t2 = np.cross(d0, t1)

    def obj(x):
        d = d0 + x[0] * t1 + x[1] * t2
        return sym_err(surf, tree, c0 + x[2] * t1 + x[3] * t2, d / np.linalg.norm(d))

    r = minimize(obj, np.zeros(4), method="Nelder-Mead",
                 options=dict(xatol=1e-7, fatol=1e-10, maxiter=4000, maxfev=4000))
    d = d0 + r.x[0] * t1 + r.x[1] * t2
    return c0 + r.x[2] * t1 + r.x[3] * t2, d / np.linalg.norm(d), float(r.fun)


refs = {}
for name, fn in (("3dr_solo", "solo_prop_cw.stl"), ("holybro_1345", "1345_prop_cw.stl"),
                 ("yuneec_typhoon", "prop_cw_assembly_remeshed_v3.stl")):
    m = trimesh.load(f"/workspace/sionna/assets/meshes/reference/{fn}", process=True)
    if not isinstance(m, trimesh.Trimesh):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    c, d, err = fit_axis(m)
    R, _ = pm.tip_radius(m, c, d)
    cs = np.array([pm.chord_at(m, c, d, x * R, True)["chord"] for x in rr])
    hubfree = rr >= 0.20                                   # below this the hub owns the section
    cm = np.nanmax(cs[hubfree])
    i = int(np.nanargmax(np.where(hubfree, cs, -1)))
    unit = 1000.0 if R < 1.0 else 1.0
    refs[name] = dict(R_mm=R * unit, c_max_over_R=float(cm / R), peak_r_over_R=float(rr[i]),
                      norm=np.round(np.interp(grid, rr, cs) / cm, 4).tolist(),
                      sym_rms_mm=err * unit)
    print(f"(e) {name:15s} R={R*unit:7.2f} c_max/R={cm/R:.4f} peak={rr[i]:.3f} "
          f"norm@0.70R={np.interp(0.70, rr, cs)/cm:.4f}")

led = json.load(open("/workspace/sionna/outputs/reference_props.json"))["props"]
for k, v in led.items():
    st = v["stations"]
    r_l = np.array([s["r_over_R"] for s in st])
    c_l = np.array([s["chord_mm"] for s in st])
    keep = np.array(["rejected" not in s for s in st])
    cm = c_l[keep].max()
    refs.setdefault(k, {})["ledger_norm"] = np.round(np.interp(grid, r_l, c_l) / cm, 4).tolist()
    refs[k]["ledger_c_max_over_R"] = float(v["chord_max_over_R"])
    refs[k]["ledger_peak"] = float(v["chord_peak_r_over_R"])
    refs[k]["ledger_R_mm"] = float(v["R_disc_mm"])
refs["ours_law_norm"] = np.round(np.interp(grid, dc.CHORD_RR, dc.CHORD_FRAC), 4).tolist()
refs["ours_mesh_norm"] = np.round(np.interp(grid, rr, c_o) / np.nanmax(c_o), 4).tolist()
refs["dji_mesh_norm"] = sens["fitted_axis"]["dji_norm"]
refs["grid"] = grid.tolist()
OUT["e_reference_props"] = refs
print("(e) ledger vs mine, normalised chord at 0.70R:")
for k in ("3dr_solo", "holybro_1345", "yuneec_typhoon"):
    print(f"    {k:15s} ledger {refs[k]['ledger_norm'][9]:.3f}   mine {refs[k]['norm'][9]:.3f}")
print("    ours law       ", refs["ours_law_norm"][9], " ours mesh", refs["ours_mesh_norm"][9],
      " dji", refs["dji_mesh_norm"][9])

json.dump(OUT, open(f"{SP}/final.json", "w"), indent=1, default=float)
print("saved")
