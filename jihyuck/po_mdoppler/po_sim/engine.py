"""
Simulation engine — ties mesh + kinematics + physics + occlusion together.

Per pulse it produces a *decomposed* set of complex contributions (body and each
blade material, with and without occlusion) rather than a single signal. From
those, every occlusion × blade-material ablation combination is reconstructable
post-hoc by addition (body is metal, fixed):

    occ=none, mat=X :  body_none + blade_none_X
    occ=body, mat=X :  body_occ  + blade_none_X
    occ=full, mat=X :  body_occ  + blade_occ_X          X ∈ {nylon, cf, metal}

Occlusion (ray-casting) is the expensive axis, so it runs once per pulse and the
resulting visible/keep facet sets are reused across all blade materials (each
material is just a different Fresnel Γ reweighting — nearly free).

`po_sim` is a pure library: all parameters arrive via `SimConfig` (the "how")
and `SceneSpec` (the "what" — materials + airframe geometry). Nothing here reads
`configs/`; the CLI wires defaults in.
"""
import os
import time
from dataclasses import dataclass, field
from multiprocessing import Pool

import numpy as np

from . import physics
from .mesh import DroneMesh
from .occlusion import build_body_bvh, self_occlusion_mask, body_block_mask
from .kinematics import load_flight, radar_position, window_starts, window_poses


@dataclass
class SceneSpec:
    """What is being simulated: materials + rotor layout."""
    body_mat: tuple                       # (er, sigma), fixed metal
    blade_mats: dict                      # {name: (er, sigma)}
    blade_mat_keys: list                  # ordered material names
    blade_offsets: np.ndarray             # (n_blades, 3) rotor hub positions
    blade_dirs: np.ndarray                # (n_blades,) spin signs
    per_rotor: bool = False               # also store per-rotor cf signals

    @property
    def n_blades(self):
        return len(self.blade_dirs)


def signal_keys(blade_mat_keys, per_rotor=False):
    """Ordered list of npz keys written per window."""
    keys = (["body_none", "body_occ"]
            + [f"blade_none_{m}" for m in blade_mat_keys]
            + [f"blade_occ_{m}" for m in blade_mat_keys])
    if per_rotor:
        keys += ([f"blade_occ_cf_r{i}" for i in range(4)]
                 + [f"blade_none_cf_r{i}" for i in range(4)])
    return keys


# ==============================================================================
# ONE PULSE -> decomposed complex contributions
# ==============================================================================
def compute_pulse_decomposed(mesh, cfg, spec, rot_mat, pos_body,
                             blade_angles_4, radar_pos, body_bvh):
    """Simulate one pulse -> dict of complex scalars keyed by `signal_keys`."""
    out = {k: 0.0 + 0j for k in signal_keys(spec.blade_mat_keys, spec.per_rotor)}
    kw = cfg.k

    # ---------------- BODY (material = metal, fixed) ----------------
    centers, normals, areas = mesh.body_facets(rot_mat, pos_body)
    visible, dist, cos_theta = physics.visible_facets(centers, normals, radar_pos)
    if visible.any():
        vis_idx = np.where(visible)[0]
        cv, dv = cos_theta[vis_idx], dist[vis_idx]
        gamma = physics.fresnel_te_vec(cv, spec.body_mat[0], spec.body_mat[1], cfg.f_c)
        term = gamma * physics.geometry_term(areas[vis_idx], cv, dv, kw)
        out["body_none"] = np.sum(term)
        not_occ = self_occlusion_mask(body_bvh, centers, vis_idx, radar_pos)
        out["body_occ"] = np.sum(term[not_occ])

    # ---------------- BLADES (reuse geometry across materials) ----------------
    for b_idx in range(spec.n_blades):
        angle = blade_angles_4[b_idx] * spec.blade_dirs[b_idx]
        centers_b, normals_b, areas_b = mesh.blade_facets(
            b_idx, angle, rot_mat, pos_body, spec.blade_offsets[b_idx])
        vis_b, dist_b, cos_b = physics.visible_facets(centers_b, normals_b, radar_pos)
        if not vis_b.any():
            continue
        vb_idx = np.where(vis_b)[0]
        cvb, dvb = cos_b[vb_idx], dist_b[vb_idx]
        geom = physics.geometry_term(areas_b[vb_idx], cvb, dvb, kw)   # material-free
        keep = body_block_mask(body_bvh, centers_b, vb_idx, radar_pos)

        for m in spec.blade_mat_keys:
            er, sg = spec.blade_mats[m]
            contrib = physics.fresnel_te_vec(cvb, er, sg, cfg.f_c) * geom
            out[f"blade_none_{m}"] += np.sum(contrib)
            out[f"blade_occ_{m}"] += np.sum(contrib[keep])
            if spec.per_rotor and m == "cf":
                out[f"blade_none_cf_r{b_idx}"] = np.sum(contrib)
                out[f"blade_occ_cf_r{b_idx}"] = np.sum(contrib[keep])
    return out


# ==============================================================================
# WORKER: one window -> window_XXXXX.npz  (multiprocessing)
# ==============================================================================
# Populated once per worker process by the Pool initializer so the mesh is loaded
# a single time per worker (never pickled per task).
_CTX = {}


def _init_worker(mesh_dir, cfg, spec):
    _CTX["mesh"] = DroneMesh.load(mesh_dir)
    _CTX["cfg"] = cfg
    _CTX["spec"] = spec
    _CTX["keys"] = signal_keys(spec.blade_mat_keys, spec.per_rotor)


def _worker_simulate_window(task):
    w_idx, t_start, out_dir, positions, rot_matrices, blade_angles_all, radar_pos = task
    mesh, cfg, spec, keys = _CTX["mesh"], _CTX["cfg"], _CTX["spec"], _CTX["keys"]

    sigs = {k: np.zeros(cfg.n_pulses, dtype=np.complex128) for k in keys}
    body_bvh = None
    for i in range(cfg.n_pulses):
        if i % cfg.bvh_rebuild_every == 0:        # drone drifts ~cm -> reuse BVH
            body_bvh = build_body_bvh(mesh, rot_matrices[i], positions[i])
        d = compute_pulse_decomposed(
            mesh, cfg, spec, rot_matrices[i], positions[i],
            blade_angles_all[i], radar_pos, body_bvh)
        for k in keys:
            sigs[k][i] = d[k]

    np.savez(os.path.join(out_dir, f"window_{w_idx:05d}.npz"), **sigs)
    # cheap progress scalar: mean |occ=full, mat=cf| (falls back to first material)
    prog_mat = "cf" if "blade_occ_cf" in sigs else spec.blade_mat_keys[0]
    full = sigs["body_occ"] + sigs[f"blade_occ_{prog_mat}"]
    return w_idx, t_start, float(np.mean(np.abs(full)))


# ==============================================================================
# DRIVER: whole flight -> many windows
# ==============================================================================
def run_generation(cfg, spec, *, grade, data_dir, out_dir, mesh_dir, workers,
                   max_windows=0, rpm_sweep=None, progress_every=5):
    """Generate all windows for one flight (grade) into *out_dir*.

    Returns (n_windows, out_dir). Writes window_XXXXX.npz + metadata.npz + MANIFEST.txt.
    """
    os.makedirs(out_dir, exist_ok=True)
    keys = signal_keys(spec.blade_mat_keys, spec.per_rotor)

    mesh = DroneMesh.load(mesh_dir)           # for banner / metadata only
    flight = load_flight(data_dir, cfg)
    radar_pos = radar_position(flight.flight_center, cfg)
    slant_range = float(np.linalg.norm(flight.flight_center - radar_pos))
    starts = window_starts(flight, cfg, max_windows)
    n_windows = len(starts)

    print("=" * 70)
    print(f"  PO ablation generator | grade {grade} | workers {workers}")
    print(f"  per-pulse tris: {mesh.total_tris} | keys/window: {len(keys)}")
    print(f"  blade materials: {spec.blade_mat_keys} | body: metal(fixed)")
    print(f"  RPM_SCALE={cfg.rpm_scale} | blade cf(er,σ)={spec.blade_mats.get('cf')}")
    print(f"  windows: {n_windows} | slant range: {slant_range:.1f} m -> {out_dir}")
    print("=" * 70)

    # per-window RPM sweep (battery-state coverage): scale blade angle per window
    sw = None
    if rpm_sweep is not None:
        lo, hi = rpm_sweep
        sw = np.linspace(lo, hi, n_windows)
        np.random.default_rng(42).shuffle(sw)     # decorrelate from the timeline
        print(f"  per-window RPM sweep [{lo:g},{hi:g}] over {n_windows} windows")

    print("  precomputing kinematics...")
    all_args = []
    for w_idx, t_start in enumerate(starts):
        positions, rot_matrices, blade_angles = window_poses(flight, t_start, cfg)
        if sw is not None:
            blade_angles = blade_angles * (sw[w_idx] / cfg.rpm_scale)
        all_args.append((w_idx, t_start, out_dir, positions, rot_matrices,
                         blade_angles, radar_pos))

    print("  running...")
    t0 = time.time()
    done = 0
    with Pool(processes=workers, initializer=_init_worker,
              initargs=(mesh_dir, cfg, spec)) as pool:
        for w_idx, t_start, sigmean in pool.imap_unordered(
                _worker_simulate_window, all_args, chunksize=1):
            done += 1
            if done % progress_every == 0 or done == n_windows:
                el = time.time() - t0
                rate = done / el if el > 0 else 0
                eta = (n_windows - done) / rate if rate > 0 else 0
                print(f"  [{done:4d}/{n_windows}] {el:.0f}s | {rate:.3f} win/s | "
                      f"ETA {eta/60:.1f} min")

    _write_metadata(out_dir, cfg, spec, grade, radar_pos, flight.flight_center,
                    slant_range, starts, keys)
    _write_manifest(out_dir, grade, n_windows, cfg, keys, spec.blade_mat_keys)
    print(f"\n  DONE grade {grade}: {n_windows} windows in {(time.time()-t0)/60:.1f} min")
    print(f"  out: {out_dir}")
    return n_windows, out_dir


def _write_metadata(out_dir, cfg, spec, grade, radar_pos, flight_center,
                    slant_range, starts, keys):
    np.savez(
        os.path.join(out_dir, "metadata.npz"),
        grade=grade, radar_pos=radar_pos, flight_center=flight_center,
        slant_range=slant_range, window_starts=starts,
        n_pulses=cfg.n_pulses, prf=cfg.prf, fc=cfg.f_c, wavelength=cfg.wavelength,
        rpm_scale=cfg.rpm_scale, signal_keys=np.array(keys),
        body_mat=np.array(spec.body_mat), blade_mat_keys=np.array(spec.blade_mat_keys),
        blade_mats=np.array([spec.blade_mats[m] for m in spec.blade_mat_keys]),
        clean=True,
    )


def _write_manifest(out_dir, grade, n_windows, cfg, keys, blade_mat_keys):
    with open(os.path.join(out_dir, "MANIFEST.txt"), "w") as f:
        f.write("PO ablation — decomposed clean signals (per window_XXXXX.npz)\n")
        f.write(f"grade={grade}  windows={n_windows}  "
                f"N_PULSES={cfg.n_pulses}  PRF={cfg.prf}\n\n")
        f.write("keys per npz (each complex128 (n_pulses,)):\n")
        for k in keys:
            f.write(f"  {k}\n")
        f.write("\nreconstruct (occlusion x blade-material), body=metal fixed:\n")
        f.write("  occ=none, mat=X :  body_none + blade_none_X\n")
        f.write("  occ=body, mat=X :  body_occ  + blade_none_X\n")
        f.write("  occ=full, mat=X :  body_occ  + blade_occ_X\n")
        f.write(f"  X in {{{', '.join(blade_mat_keys)}}}\n\n")
        f.write("post-hoc (NOT baked in): noise, global scale, body-blade ratio,\n")
        f.write("  bulk-Doppler, jitter, PRF/time-scale, DC removal, spectrogram params.\n")
