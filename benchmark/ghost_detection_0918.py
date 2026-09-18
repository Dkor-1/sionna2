# -*- coding: utf-8 -*-
"""
ghost_detection_0918.py - what the 0962 drone-ground path lists do to OFDM detection (Q3)
=================================================================================================

Question
    runners/jobs_0962 measured the drone-ground ghost as a level and a delay per path class.  This
    script carries the same stored path lists into the CPU OFDM receiver of
    benchmark/ofdm_receiver_pilot_0917.py, through the conventions fixed by the Q0 adapter
    (benchmark/rt_channel_adapter_0918.py), and asks what the ghost and the environment-only path do
    to detection: gated power-delay and range-Doppler maps, probability of detection at a matched
    false-alarm condition, detections at the wrong range, and runs of consecutive frames with no
    detection.

    There is no tracker in this repository (no association or filter over frames exists in src/ or
    benchmark/ as of 2026-09-18), so no reacquisition number is written.  The frame-level surrogate
    that is written instead is `miss_run` - runs of consecutive frames of one trajectory run with no
    gated detection - and it is named a detection-level quantity, never a track.

Scope of every number this file writes
    numpy simulation on CPU.  The ray tracer is not run here: the path lists are read from the
    runners/jobs_0962 shards and their --dump-paths sidecars, which sionna-rt 2.1.0 produced earlier
    (benchmark/elevation_sweep_md.py).  No hardware, no RF measurement, no antenna calibration.
    3.5 GHz is the working carrier assumption of the stored cells, not a decided band.  Drone
    matrice4e, mesh revision 0, canonical thin slab (shell 0.75 mm, propeller 1.43 mm), tr38901
    stand-in aimed at the drone, flat ITU-concrete ground with scattering coefficient 0 (a mirror),
    4e9 rays, path cap 2,000,000, 4,096-position hover records at PRF 19,700 Hz, max_depth 2 (and 3
    where the row says so).  Bandwidths 20 and 100 MHz.  Every level is a PathSolver level, not a
    radar cross section.

Conventions carried over from Q0 (benchmark/rt_channel_adapter_0918.py; each was a real trap)
    * `paths.a` in the sidecar is the PASSBAND coefficient.  The baseband gain is
      `a * exp(-2j*pi*fc*tau)`.  The carrier phase is applied exactly once, here, at the delay the
      path has after the trajectory update - never twice.
    * `tau` stays ABSOLUTE (round trip from the radar).  Range evaluation reads that absolute value.
    * Poses are never blended and no path is matched or interpolated across poses.  A symbol's
      channel is the stored path list of one stored pose.
    * The receiver is given the channel only.  Truth (the drone's range and Doppler, the path class
      labels) is used after the receiver returns, in the scoring step.

What the synthetic trajectory does, and what it does not do
    The 0962 records are hovers: the drone's centre does not move, and the sidecar stores no Doppler
    (`want_doppler=False`), so every stored path is static.  To ask a detection question a body
    motion has to be added.  It is added as GEOMETRY, not as one phase:

        the drone is translated rigidly by u(t) = (v_h, v_z) t, the radar and the ground stay put.

    By Fermat's principle the first-order change of a listed path's length under that translation is
    u . (e_in - e_out) summed over the path's drone vertices, where e_in and e_out are the unit
    vectors into and out of that vertex.  For a flat mirror ground every leg that leaves or reaches
    the drone through the ground unfolds to the image radar, so the change depends only on how many
    of the path's two end legs are ground legs:

        0 ground legs  ([d], [d,d], [d,d,d])        dL/dt = 2 u.r        (r   = radar -> drone)
        1 ground leg   ([g,d], [d,g], [g,d,d], ...) dL/dt = u.r + u.r'   (r'  = image radar -> drone)
        2 ground legs  ([g,d,g])                    dL/dt = 2 u.r'
        no drone vertex ([g])                       dL/dt = 0

    The script asserts that no listed path has a ground interaction strictly between its first and
    last interaction (none exists in these five cells), which is what makes the end-leg rule exact
    for every listed class.  The direct and the ghost classes therefore get DIFFERENT delay rates
    and different Doppler, and their relative phase turns with the geometry.  No body-Doppler phase
    is applied to every path, and no phase is drawn at random in any frame.

    Not modelled: rotation of the drone about its own axes, the ground specular point's motion beyond
    the image construction, range migration inside one frame (reported as a fraction of a range
    cell), TX-RX leakage, CFO, phase noise, clock drift, ADC effects, antenna pattern changes with
    the changing look direction, and any real flight profile.

Adversarial review, 2026-09-18 (changelog; the detection frames were NOT re-run, only the blocks a
fix touches, through --figs-only)
    1. The delay model is a CONSTANT rate, the first-order change of each path's length at t = 0.
       The document called the trajectory a rigid translation and then printed the constant-rate
       phase turn as if it were the geometry's.  `exact_legs` / `linearisation_drift` added,
       `verify` check (10) added, section 1 now prints both turns and names the model, section 6
       carries both.  Measured: over the 200.9 ms used, the exact turn is 278 / 317 / 202 deg where
       the constant rate gives 298 / 339 / 217 deg (A / B / C).
    2. The environment-only path is static, so the slow-time mean removal subtracts it out: on its
       own it falls below -300 dB wherever the frame lists it at every pose.  The `env cell rel.
       drone cell` column of section 3 is therefore the drone paths' leakage, not a ground-return
       level - except at B (and B_d3), where the solver did not list the path at pose 151 (and 42),
       inside the map frame, and the removal turns that one missing pose into an impulse.  That, not
       the ground, is the -12 dB the column showed at B.  `verify` check (11) added, section 3 now
       prints the four levels per cell and band, section 4 and section 6 corrected.
    3. Section 5's second column was a difference of two per-class medians, taken on every 16th
       pose, and was labelled "new depth-3 classes".  It is now a count of the depth-3 paths whose
       (tau, a) row is not in the same pose's depth-2 list, by class; `class_counts_median` is
       counted at every pose.  The A direct figure moves from +4 to +5 as a median difference and is
       +4 as a count of new paths.
    4. "matched false-alarm condition" now says what is matched (the target) and what is not (the
       realised rate, 0.067 to 0.137 at target 0.1), and which pairs share one threshold exactly.
    5. Section 1's line on the unread E cell said E moves range and grazing angle together; against
       C it is close to a second range at the same grazing angle.  Corrected.
    6. --figs-only now rebuilds `cells`, `trajectory`, `depth_match` and `verify` as well, so a
       correction to anything derived from the stored path lists alone no longer needs the 41,968
       receiver frames run again.

Run (CPU only)
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 \
        /workspace/.venvs/py312/bin/python benchmark/ghost_detection_0918.py --workers 6
    --quick            fewer frames / seeds / SNR points, for a smoke test
    --doc-from-json    only rewrite the document from the stored ledger
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import os
import subprocess
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "benchmark")
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


PILOT = _load_module("ofdm_receiver_pilot_0917", "benchmark/ofdm_receiver_pilot_0917.py")

C0 = 299792458.0
GENERATOR = "benchmark/ghost_detection_0918.py"
OUT_JSON = "outputs/ghost_detection_0918.json"
DOC = "docs/GHOST_DETECTION_0918.md"
FIG_PREFIX = "outputs/figures/ghost_detection_0918_"
SHARD_DIR = "outputs/elev_sweep_shards"
PROV_DIR = "outputs/path_provenance"
ADAPTER_LEDGER = "outputs/rt_channel_adapter_0918.json"
READOUT_LEDGER = "outputs/readout_0918.json"

#: The five runners/jobs_0962 cells this script reads.  `geo` names the geometry the queue header
#  calls A / B / C; `R`, `el_deg` and `alt_m` are the job line's --range-m, --els and --env-alt, and
#  the header's derived quantities (radar height h, grazing angle psi, the two-ray excess R'-R) are
#  recomputed here from those three numbers and checked against the header values in `verify`.
CELLS = {
    "A_d2": {"geo": "A", "depth": 2, "R": 30.0, "el_deg": -5.0, "alt_m": 4.11,
             "stem": "sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt4.11_shell0.75mm"
                     "_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5",
             "header_psi_deg": 10.62, "header_excess_cm": 40.7, "job_lines": "3-4"},
    "B_d2": {"geo": "B", "depth": 2, "R": 30.0, "el_deg": -2.5, "alt_m": 2.81,
             "stem": "sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt2.81_shell0.75mm"
                     "_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-2.5",
             "header_psi_deg": 8.19, "header_excess_cm": 28.0, "job_lines": "7-8"},
    "C_d2": {"geo": "C", "depth": 2, "R": 30.0, "el_deg": -10.0, "alt_m": 6.71,
             "stem": "sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt6.71_shell0.75mm"
                     "_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-10",
             "header_psi_deg": 15.53, "header_excess_cm": 66.4, "job_lines": "15-16"},
    "A_d3": {"geo": "A", "depth": 3, "R": 30.0, "el_deg": -5.0, "alt_m": 4.11,
             "stem": "sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt4.11_shell0.75mm"
                     "_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d3_el-5",
             "header_psi_deg": 10.62, "header_excess_cm": 40.7, "job_lines": "9-10"},
    "B_d3": {"geo": "B", "depth": 3, "R": 30.0, "el_deg": -2.5, "alt_m": 2.81,
             "stem": "sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt2.81_shell0.75mm"
                     "_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d3_el-2.5",
             "header_psi_deg": 8.19, "header_excess_cm": 28.0, "job_lines": "11-12"},
}
#: The three geometries the detection question is read on: the three completed low-grazing cells of
#  runners/jobs_0962 at one range (30 m), so the grazing angle is the only geometry axis that moves.
#  The queue's other two completed ground geometries are E (15 m, psi 16.1 deg) - a second range, so
#  it would mix range with grazing angle - and F (60 m), which the 0962 header does not read until
#  runners/jobs_0961 R1 lands.  A_d3 and B_d3 are the depth arms of A and B.
PRIMARY = ("A_d2", "B_d2", "C_d2")
DEPTH_PAIRS = (("A_d2", "A_d3"), ("B_d2", "B_d3"))
#: The environment-only ablation depends on the geometry only (the nadir return does not touch the
#  drone and does not change with max_depth), so it is keyed by the geometry label and computed on
#  that geometry's depth-2 cell.  `verify` checks that the depth-3 cell lists the same key.
GEO_REF = {"A": "A_d2", "B": "B_d2", "C": "C_d2"}

#: Two CP-OFDM configurations, identical to the Q0 adapter's.  `bw20` is the 0917 pilot's own system;
#  `bw100` keeps the subcarrier spacing and the CP fraction and grows the FFT to the NR 100 MHz shape.
#  Both have the same symbol duration, so both use the same frame clock and the same pose sequence.
BANDS = {
    "bw20": {"label_mhz": 20.0,
             "system": {"fc_hz": 3.5e9, "scs_hz": 30e3, "fft": 1024, "cp": 72, "n_sym": 256,
                        "guard": [206, 205], "dc_null": True}},
    "bw100": {"label_mhz": 100.0,
              "system": {"fc_hz": 3.5e9, "scs_hz": 30e3, "fft": 4096, "cp": 288, "n_sym": 256,
                         "guard": [410, 409], "dc_null": True}},
}

#: Path composition = which listed paths the channel keeps.  Nested: c1 subset c2 subset c3.
COMPOSITIONS = {
    "direct":            ("direct",),
    "direct_ghost":      ("direct", "ghost1", "ghost2"),
    "direct_ghost_env":  ("direct", "ghost1", "ghost2", "env"),
}
COMPOSITION_TEXT = {
    "direct": "direct drone paths only (no ground interaction)",
    "direct_ghost": "direct drone paths plus the drone-ground mixed paths",
    "direct_ghost_env": "direct plus mixed plus the environment-only path",
}
LEGS = ("direct", "ghost1", "ghost2", "env")

CFG = {
    "seed_root": 20260918,
    "modulation": "qpsk",
    "window": "hann",
    "prf_hz": 19700.0,                       # meta[4] of every 0962 shard; asserted in load_cell
    #: Synthetic trajectory added to the stored hover: horizontal recession and climb, in m/s.
    #  Chosen so the body Doppler sits about 2.2 Doppler bins away from zero (clear of the CFAR
    #  guard and of the slow-time mean removal) while the direct-to-ghost path difference turns by
    #  about 0.6 to 0.9 wavelength over the stored record.  Both numbers are reported, not assumed.
    "traj": {"v_h_mps": 10.0, "v_z_mps": 5.0, "name": "recede10_climb5"},
    "n_frames": 22,                          # 22 x 9.1333 ms = 200.9 ms of the 207.9 ms record
    #: SNR per resource element, per band.  The two grids are offset because the 100 MHz band
    #  integrates 3,277 subcarriers against 613, i.e. 7.28 dB more energy at the same per-resource-
    #  element SNR; each grid is placed on its own band's transition so neither curve is read off a
    #  saturated end.  The bands are never read against each other on Pd (section 6).
    "snr_re_db": {"bw20": [-44.0, -41.0, -38.0, -35.0, -32.0],
                  "bw100": [-51.0, -48.0, -45.0, -42.0, -39.0]},
    "n_runs": 4,                             # independent noise streams, each spanning all frames
    "n_h0_noise": {"cal": 1000, "eval": 1000},   # noise-only ablation; T is scale free, so one set
    "n_h0_env": {"cal": 300, "eval": 300},       # environment-only ablation, per SNR point
    "pfa_frame": [0.1, 0.02],
    #: the one SNR point per band the static-removal knob is run at (the middle of that band's grid)
    "removal_off_snr_db": {"bw20": -38.0, "bw100": -45.0},
    "map_frame": 0,                          # the frame the noise-free observation figures show
    "map_snr_re_db": -42.0,
}
QUICK = {"n_frames": 6, "snr_re_db": {"bw20": [-38.0, -32.0], "bw100": [-45.0, -39.0]}, "n_runs": 2,
         "n_h0_noise": {"cal": 120, "eval": 120}, "n_h0_env": {"cal": 80, "eval": 80}}

#: Experiment codes keep every random stream disjoint (numpy SeedSequence spawn keys).
EXP = {"h0_noise_cal": 1, "h0_noise_eval": 2, "h0_env_cal": 3, "h0_env_eval": 4,
       "h1": 5, "h1_fixed_body": 6, "h1_removal_off": 7, "h0_env_removal_off_cal": 8,
       "h0_env_removal_off_eval": 9}
BAND_CODE = {"bw20": 0, "bw100": 1}
CELL_CODE = {k: i for i, k in enumerate(CELLS)}
COMP_CODE = {k: i for i, k in enumerate(COMPOSITIONS)}


# ----------------------------------------------------------------------------------------------------
#  Reading the stored cells
# ----------------------------------------------------------------------------------------------------
def _shard(stem: str, sh: str) -> str:
    return os.path.join(ROOT, SHARD_DIR, f"{stem}_{sh}.npz")


def _sidecar(stem: str, sh: str) -> str:
    return os.path.join(ROOT, PROV_DIR, f"{stem}_{sh}_prov.npz")


def carrier_from_arm(arm: str) -> float:
    """The carrier the cell was baked at, read from the arm name's `_fc<MHz>` tag; without that tag
    the sweep's convention carrier applies (benchmark/elevation_sweep_md.py sets FC = 3.5e9).  Same
    rule as benchmark/rt_channel_adapter_0918.py:carrier_from_arm."""
    import re
    m = re.search(r"_fc(\d+(?:\.\d+)?)", arm)
    return 3.5e9 if not m else float(m.group(1)) * 1e6


def leg_counts(part: np.ndarray, part_names: list) -> dict:
    """Per path: how many drone vertices it has and how many of its two END legs are ground legs.

    `part` is the sidecar's [depth, path] matrix of part indices; -1 means no interaction at that
    depth.  A name that starts with `env_` is the environment, every other name is a drone part.
    The end-leg count is (first interaction is environment) + (last interaction is environment).
    `interior_env` counts paths with an environment interaction that is neither first nor last; the
    end-leg rule of the module docstring is exact only while that count is zero, so the caller stops
    when it is not.
    """
    is_env = np.array([str(n).startswith("env_") for n in part_names], bool)
    hit = part >= 0
    idx = np.where(hit, part, 0)
    kind = np.where(hit, np.where(is_env[idx], 2, 1), 0)          # 0 none, 1 drone, 2 environment
    n_int = hit.sum(axis=0)
    n_drone = (kind == 1).sum(axis=0)
    n_env = (kind == 2).sum(axis=0)
    D, P = part.shape
    order = np.arange(D)[:, None]
    first_row = np.where(hit, order, D).min(axis=0)
    last_row = np.where(hit, order, -1).max(axis=0)
    cols = np.arange(P)
    first_kind = np.where(n_int > 0, kind[np.clip(first_row, 0, D - 1), cols], 0)
    last_kind = np.where(n_int > 0, kind[np.clip(last_row, 0, D - 1), cols], 0)
    end_ground = (first_kind == 2).astype(np.int8) + (last_kind == 2).astype(np.int8)
    interior_env = n_env - end_ground
    leg = np.full(P, -1, np.int8)                                  # -1 = no interaction listed
    leg[(n_drone > 0) & (end_ground == 0)] = 0                     # direct
    leg[(n_drone > 0) & (end_ground == 1)] = 1                     # ghost1
    leg[(n_drone > 0) & (end_ground == 2)] = 2                     # ghost2
    leg[(n_drone == 0) & (n_env > 0)] = 3                          # env
    return {"leg": leg, "n_drone": n_drone, "n_env": n_env, "n_int": n_int,
            "interior_env_paths": int((interior_env > 0).sum())}


def load_cell(key: str) -> dict:
    """Both shards of one 0962 cell, merged by global pose index and sorted, with the end-leg class
    of every listed path already computed.  The two shards split the record into even and odd global
    indices, so merging by `idx` and sorting restores the 4,096-position record."""
    c = dict(CELLS[key])
    stem = c["stem"]
    poses, a, tau, leg, npaths, off_len = [], [], [], [], [], []
    stamps, names_all, interior = [], [], 0
    E_all, idx_all = [], []
    for sh in ("00", "01"):
        z = np.load(_shard(stem, sh), allow_pickle=True)
        p = np.load(_sidecar(stem, sh), allow_pickle=True)
        names = [str(x) for x in p["part_names"]]
        names_all.append(names)
        # every array is decompressed once here: an NpzFile re-reads on every __getitem__
        p_a = np.asarray(p["a"]).astype(np.complex128)
        p_tau = np.asarray(p["tau"], np.float64)
        lc = leg_counts(np.asarray(p["part"], np.int16), names)
        interior += lc["interior_env_paths"]
        n_paths = np.asarray(p["n_paths"], np.int64)
        off = np.concatenate([[0], np.cumsum(n_paths)])
        slot = np.asarray(p["slot"], np.int64)
        idx = np.asarray(z["idx"], np.int64)
        meta = np.asarray(z["meta"], float)
        assert np.array_equal(idx[slot], np.asarray(p["pose"], np.int64)), f"{stem}_{sh}: pose != idx[slot]"
        assert abs(meta[4] - CFG["prf_hz"]) < 1e-9, f"{stem}_{sh}: PRF {meta[4]}"
        for t in range(slot.size):
            s, e = int(off[t]), int(off[t + 1])
            poses.append(int(idx[slot[t]]))
            a.append(p_a[s:e])
            tau.append(p_tau[s:e])
            leg.append(lc["leg"][s:e])
            npaths.append(e - s)
        E_all.append(np.asarray(z["E"], complex)[slot])
        idx_all.append(idx[slot])
        stamps.append({"shard": sh, "run_id": str(z["run_id"]), "solver_build": str(z["solver_build"]),
                       "cfg": [float(x) for x in np.asarray(z["cfg"], float)],
                       "el_deg": float(meta[0]), "n_poses": int(meta[3]), "prf_hz": float(meta[4]),
                       "spp": float(meta[6]), "seconds": float(meta[5]),
                       "n_trunc": int(np.asarray(z["n_trunc"])[0]),
                       "max_paths_cap": int(np.asarray(z["n_trunc"])[1]),
                       "n_unknown_id": int(np.asarray(p["n_unknown_id"])[0]),
                       "prim_ok_all": bool(np.asarray(p["prim_ok"], bool).all()),
                       "ant_pattern": str(z["ant_pattern"]) if "ant_pattern" in z else "iso"})
    order = np.argsort(np.asarray(poses, np.int64), kind="stable")
    pose = np.asarray(poses, np.int64)[order]
    assert np.array_equal(pose, np.arange(pose.size)), f"{stem}: merged poses are not 0..{pose.size - 1}"
    a = [a[i] for i in order]
    tau = [tau[i] for i in order]
    leg = [leg[i] for i in order]
    flat_a = np.concatenate(a).astype(np.complex128)
    flat_tau = np.concatenate(tau)
    flat_leg = np.concatenate(leg)
    n_paths = np.asarray([x.size for x in a], np.int64)
    off = np.concatenate([[0], np.cumsum(n_paths)])
    E = np.concatenate(E_all)[np.argsort(np.concatenate(idx_all), kind="stable")]
    c.update({"key": key, "pose": pose, "a": flat_a, "tau": flat_tau, "leg": flat_leg,
              "off": off, "n_paths": n_paths, "E": E, "stamps": stamps,
              "part_names": names_all, "interior_env_paths": interior,
              "fc_hz": carrier_from_arm(stem)})
    return c


_CELL_CACHE: dict = {}


def cell(key: str) -> dict:
    if key not in _CELL_CACHE:
        if len(_CELL_CACHE) >= 2:
            _CELL_CACHE.pop(next(iter(_CELL_CACHE)))
        _CELL_CACHE[key] = load_cell(key)
    return _CELL_CACHE[key]


# ----------------------------------------------------------------------------------------------------
#  Geometry and the synthetic trajectory
# ----------------------------------------------------------------------------------------------------
def geometry(c: dict) -> dict:
    """The queue header's own geometry, recomputed from the job line's R, el and --env-alt.

    Drone height H = --env-alt, radar height h = H + R sin(el), horizontal separation D = R cos(el),
    grazing angle psi = atan((H + h)/D), one ground leg R' = sqrt(D^2 + (H + h)^2).  `r_hat` is the
    unit vector radar -> drone and `r_img` the unit vector image-radar -> drone, both in the vertical
    plane as (horizontal, vertical) - a flat ground fixes that plane.
    """
    R, el, H = c["R"], math.radians(c["el_deg"]), c["alt_m"]
    h = H + R * math.sin(el)
    D = R * math.cos(el)
    Rp = math.hypot(D, H + h)
    return {"R_m": R, "el_deg": c["el_deg"], "drone_height_m": H, "radar_height_m": h,
            "horizontal_m": D, "psi_deg": math.degrees(math.atan2(H + h, D)),
            "leg_image_m": Rp, "excess_cm": 100.0 * (Rp - R),
            "r_hat": np.array([math.cos(el), -math.sin(el)]),
            "r_img": np.array([D, H + h]) / Rp,
            "nadir_round_trip_m": 2.0 * h}


def leg_rates(c: dict) -> dict:
    """Round-trip path-length rate dL/dt in m/s of each end-leg class under the synthetic trajectory,
    and the Doppler each one carries, f = -fc (dL/dt)/c0 (a receding path lengthens, so f < 0).

    The rate is CONSTANT: it is the first-order (t = 0) change of the path length under the
    translation, and the delay every frame of this file uses is tau + (dL/dt) t / c0.  It is not the
    exact length of the translated geometry, which curves; `exact_legs` gives that, and `verify`
    reports the difference the two accumulate over the record."""
    g = geometry(c)
    v = np.array([CFG["traj"]["v_h_mps"], CFG["traj"]["v_z_mps"]])
    ur, ui = float(v @ g["r_hat"]), float(v @ g["r_img"])
    rate = np.array([2.0 * ur, ur + ui, 2.0 * ui, 0.0])
    fc = c["fc_hz"]
    return {"rate_mps": rate, "doppler_hz": -fc * rate / C0,
            "u_dot_r": ur, "u_dot_r_img": ui,
            "excess_rate_mps": ui - ur, "geometry": g}


def exact_legs(c: dict, t: float) -> tuple:
    """The EXACT direct and one-ground leg lengths of the translated geometry at time t: the radar at
    (0, h), the drone centre at (D, H) + (v_h, v_z) t, the image radar at (0, -h).  Used only to say
    how far the constant-rate model of `leg_rates` has drifted by the end of the record; no channel in
    this file is built from it."""
    g = geometry(c)
    x = g["horizontal_m"] + CFG["traj"]["v_h_mps"] * t
    z = g["drone_height_m"] + CFG["traj"]["v_z_mps"] * t
    return math.hypot(x, z - g["radar_height_m"]), math.hypot(x, z + g["radar_height_m"])


def linearisation_drift(c: dict, seconds: float) -> dict:
    """Constant-rate model against the exact translated geometry over `seconds` of the record.

    `direct_phase_deg` is the extra phase the direct class would have turned had the exact lengths
    been used; `excess_turn_*_deg` is the direct-to-ghost relative turn, which is what the fade of
    section 3 is made of, under the two models."""
    lr = leg_rates(c)
    R0, Rp0 = exact_legs(c, 0.0)
    RT, RpT = exact_legs(c, seconds)
    lam = C0 / c["fc_hz"]
    lin_direct = lr["rate_mps"][0] * seconds
    ex_direct = 2.0 * (RT - R0)
    lin_exc = lr["excess_rate_mps"] * seconds
    ex_exc = (RpT - Rp0) - (RT - R0)
    return {"seconds": seconds,
            "direct_change_linear_m": lin_direct, "direct_change_exact_m": ex_direct,
            "direct_phase_deg": 360.0 * (ex_direct - lin_direct) / lam,
            "excess_turn_linear_deg": 360.0 * lin_exc / lam,
            "excess_turn_exact_deg": 360.0 * ex_exc / lam,
            "excess_start_cm": 100.0 * (Rp0 - R0), "excess_end_cm": 100.0 * (RpT - RT)}


# ----------------------------------------------------------------------------------------------------
#  Channel: one stored pose per OFDM symbol, the delay of every path updated from the geometry
# ----------------------------------------------------------------------------------------------------
def _block_q(fft: int) -> int:
    q = int(round(math.sqrt(fft)))
    while fft % q:
        q -= 1
    return q


def cfr_groups(fft: int, scs: float, amp: np.ndarray, tau: np.ndarray,
               groups: dict, q: int) -> dict:
    """H[k] = sum_p amp_p exp(-2j pi (k - fft//2) scs tau_p) on the centred subcarrier grid, for each
    group of path indices, as one set of exponentials shared by all groups.

    Writing k - fft//2 = b q + r splits the exponential into exp(.. b q) exp(.. r), which replaces
    fft x P exponentials by (fft/q + q) x P of them and one small matrix product per group.  The
    plain form is kept in `cfr_direct` and the two are compared in `verify`.
    """
    b = fft // q
    z = (-2j * math.pi * scs) * tau
    A = np.exp(np.outer(np.arange(b) * q - (fft // 2), z))
    A *= amp[None, :]
    Zr = np.exp(np.outer(z, np.arange(q)))
    return {name: (A[:, ix] @ Zr[ix]).ravel() if ix.size else np.zeros(fft, complex)
            for name, ix in groups.items()}


def cfr_direct(fft: int, scs: float, amp: np.ndarray, tau: np.ndarray) -> np.ndarray:
    nc = np.arange(fft) - fft // 2
    return np.exp(-2j * math.pi * np.outer(nc * scs, tau)) @ amp


def symbol_times(S, n_frame: int) -> np.ndarray:
    """Centre time of every FFT window of frame `n_frame`, measured from the start of the record, on
    a uniform symbol stride - the same time reference benchmark/ofdm_receiver_pilot_0917.py
    channel_grid uses inside a frame, continued across frames."""
    m = np.arange(S.n_sym)
    return ((n_frame * S.n_sym + m) * (S.fft + S.cp) + S.cp + (S.fft - 1) / 2) / S.fs


def frame_channel(c: dict, S, n_frame: int, mode: str = "rt_variation",
                  fixed_pose: int | None = None, fixed_scale: float = 1.0) -> dict:
    """Per-leg-class channel matrices H[symbol, subcarrier] of one frame.

    `rt_variation` gives every symbol the stored path list of the pose nearest that symbol's centre
    time (nearest stored pose, no interpolation and no matching).  `fixed_body` gives every symbol
    the same stored pose scaled by `fixed_scale`, so the mean level is kept and the pose-to-pose
    variation is removed.  In both modes each path's delay is tau + (dL/dt) t / c0 with the rate of
    its own end-leg class, and its baseband gain is a exp(-2j pi fc tau'), the carrier phase applied
    once at the updated delay.
    """
    lr = leg_rates(c)
    rate = lr["rate_mps"]
    t = symbol_times(S, n_frame)
    pose = (np.rint(CFG["prf_hz"] * t).astype(np.int64) if mode == "rt_variation"
            else np.full(S.n_sym, int(fixed_pose)))
    np.clip(pose, 0, c["pose"].size - 1, out=pose)
    q = _block_q(S.fft)
    H = {k: np.zeros((S.n_sym, S.fft), complex) for k in LEGS}
    scale = 1.0 if mode == "rt_variation" else float(fixed_scale)
    cache: dict = {}
    for m in range(S.n_sym):
        s, e = int(c["off"][pose[m]]), int(c["off"][pose[m] + 1])
        leg = c["leg"][s:e]
        key = int(pose[m])
        if key not in cache:
            cache[key] = {k: np.flatnonzero(leg == i) for i, k in enumerate(LEGS)}
        tau = c["tau"][s:e] + rate[np.clip(leg, 0, 3)] * t[m] / C0
        amp = (scale * c["a"][s:e]) * np.exp(-2j * math.pi * c["fc_hz"] * tau)
        out = cfr_groups(S.fft, S.scs_hz, amp, tau, cache[key], q)
        for k in LEGS:
            H[k][m] = out[k]
    return {"H": H, "pose_first": int(pose[0]), "pose_last": int(pose[-1]),
            "t_first": float(t[0]), "t_last": float(t[-1])}


def truth_of(c: dict, S, n_frame: int) -> dict:
    """The drone's range and Doppler in the frame, read from the stored direct paths and the
    trajectory - used only after the receiver returns.  `range_m` is c0/2 times the median absolute
    delay of the direct-class paths of the frame's first pose, advanced to the frame's centre time."""
    lr = leg_rates(c)
    t = symbol_times(S, n_frame)
    tc = float(t.mean())
    pose = int(np.rint(CFG["prf_hz"] * t[0]))
    pose = min(max(pose, 0), c["pose"].size - 1)
    s, e = int(c["off"][pose]), int(c["off"][pose + 1])
    d = c["leg"][s:e] == 0
    tau0 = float(np.median(c["tau"][s:e][d]))
    tau = tau0 + lr["rate_mps"][0] * tc / C0
    g1 = c["leg"][s:e] == 1
    tau_g = (float(np.median(c["tau"][s:e][g1])) + lr["rate_mps"][1] * tc / C0) if g1.any() else None
    return {"range_m": tau * C0 / 2, "tau_s": tau, "f_hz": float(lr["doppler_hz"][0]),
            "ghost_range_m": (tau_g * C0 / 2) if tau_g else None,
            "ghost_f_hz": float(lr["doppler_hz"][1]),
            "env_range_m": lr["geometry"]["nadir_round_trip_m"] / 2}


# ----------------------------------------------------------------------------------------------------
#  Receiver and scoring
# ----------------------------------------------------------------------------------------------------
def compose(Hc: dict, comp: str) -> np.ndarray:
    parts = COMPOSITIONS[comp]
    out = Hc[parts[0]].copy()
    for p in parts[1:]:
        out += Hc[p]
    return out


def run_receiver(H: np.ndarray, S, mask, rng, noise_var: float, static_removal: bool,
                 return_map: bool = False) -> dict:
    """One receiver frame on a channel matrix.  Y = H X + N with QPSK X, then the 0917 pilot's
    receiver.  QPSK is constant modulus, so Y/X = H + N/X keeps the noise white: the payload draw
    does not change the map statistics, and only the noise stream is redrawn between frames."""
    X = PILOT.payload(rng, S, mask, CFG["modulation"], S.n_sym)
    Y = H * X
    if noise_var > 0:
        Y = Y + np.sqrt(noise_var / 2) * (rng.standard_normal(Y.shape) + 1j * rng.standard_normal(Y.shape))
    cfg = PILOT.RxCfg(window=CFG["window"], static_removal=static_removal)
    return PILOT.receiver_grid(Y, X, mask, S, cfg, return_map=return_map)


def score_frame(out: dict, truth: dict, S) -> dict:
    """Detection-level score of one frame.  A candidate is `gated` when its range is within one range
    resolution cell and its Doppler within one Doppler resolution cell of the truth."""
    res = PILOT.resolution(S)
    F = 1.0 / S.t_sym

    def dr(e):
        return C0 * e["tau_s"] / 2 - truth["range_m"]

    def df(e):
        return ((e["f_hz"] - truth["f_hz"] + F / 2) % F) - F / 2

    gated = [e for e in out["top"] if abs(dr(e)) <= res["range_m"] and abs(df(e)) <= res["doppler_hz"]]
    best = max(gated, key=lambda e: e["T"]) if gated else None
    st = out["strongest"]
    return {"frame_stat": float(out["frame_stat"]),
            "gated_T": float(best["T"]) if best else 0.0,
            "gated_range_err_m": float(dr(best)) if best else None,
            "gated_doppler_err_hz": float(df(best)) if best else None,
            "strongest_T": float(st["T"]) if st else 0.0,
            "strongest_range_m": float(C0 * st["tau_s"] / 2) if st else None,
            "strongest_range_err_m": float(dr(st)) if st else None,
            "strongest_is_gated": bool(st is not None and abs(dr(st)) <= res["range_m"]
                                       and abs(df(st)) <= res["doppler_hz"]),
            "psl_db": out["psl_db"]}


def gate_power_db(out: dict, S, range_m: float) -> float:
    """Map power in the delay cells within half a range resolution cell of `range_m`, maximised over
    Doppler rows, in dB.  Read after the receiver returns; never given to the receiver."""
    P, tau_axis = out["map"]["P"], out["map"]["tau_axis"]
    res = PILOT.resolution(S)["range_m"]
    rng_axis = tau_axis * C0 / 2
    sel = np.abs(rng_axis - range_m) <= res / 2
    if not sel.any():
        sel = np.abs(rng_axis - range_m) == np.abs(rng_axis - range_m).min()
    return float(10 * np.log10(max(P[:, sel].max(), 1e-300)))


def _rng(*key) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(CFG["seed_root"], spawn_key=tuple(int(k) for k in key)))


# ----------------------------------------------------------------------------------------------------
#  Reference level and the noise scale
# ----------------------------------------------------------------------------------------------------
def reference_power(c: dict, S, n_frames: int) -> dict:
    """`p_ref` - the mean over the frames' symbols and active subcarriers of |H_direct|^2, the mean
    power per resource element that the direct drone paths alone put on the grid.  The noise variance
    of every arm of that cell and band is p_ref 10^(-snr_re_db/10), so the three compositions of one
    cell see the same noise and their differences are the added paths only."""
    mask = PILOT.base_mask(S)
    acc, n = 0.0, 0
    for k in range(n_frames):
        Hc = frame_channel(c, S, k)["H"]
        Hd = Hc["direct"][:, mask]
        acc += float((Hd.real ** 2 + Hd.imag ** 2).sum())
        n += Hd.size
    return {"p_ref": acc / n, "n_re": n}


# ----------------------------------------------------------------------------------------------------
#  Workers
# ----------------------------------------------------------------------------------------------------
def task_h1(spec: dict) -> list:
    """All H1 receiver frames of one (cell, band, frame): every composition, SNR point and run."""
    c = cell(spec["cell"])
    S = PILOT.build_system(BANDS[spec["band"]]["system"])
    mask = PILOT.base_mask(S)
    fc = frame_channel(c, S, spec["frame"], spec["mode"],
                       spec.get("fixed_pose"), spec.get("fixed_scale", 1.0))
    truth = truth_of(c, S, spec["frame"])
    rows = []
    for comp in spec["compositions"]:
        H = compose(fc["H"], comp)
        for snr in spec["snr_re_db"]:
            nv = spec["p_ref"] * 10 ** (-snr / 10)
            for run in range(spec["n_runs"]):
                rng = _rng(spec["exp"], CELL_CODE[spec["cell"]], BAND_CODE[spec["band"]],
                           COMP_CODE[comp], int(round(-snr)), run, spec["frame"])
                out = run_receiver(H, S, mask, rng, nv, spec["static_removal"])
                r = score_frame(out, truth, S)
                r.update({"cell": spec["cell"], "band": spec["band"], "comp": comp, "snr_re_db": snr,
                          "run": run, "frame": spec["frame"], "mode": spec["mode"],
                          "static_removal": spec["static_removal"]})
                rows.append(r)
    return rows


#: The environment-only ablation channel of one cell and band: built once per worker, because the
#  environment paths do not move and every ablation frame of that cell and band reuses them.
_ENV_CACHE: dict = {}


def task_h0(spec: dict) -> list:
    """Ablation frames: the same channel with every drone-touching path deleted.  For the two
    drone-only compositions that leaves nothing but noise; for `direct_ghost_env` it leaves the
    environment-only path.  This is a counterfactual, not a measurement of a target-absent scene."""
    S = PILOT.build_system(BANDS[spec["band"]]["system"])
    mask = PILOT.base_mask(S)
    if spec["kind"] == "noise":
        H = np.zeros((S.n_sym, S.fft), complex)
        nv = 1.0
    else:
        ck = (spec["cell"], spec["band"])
        if ck not in _ENV_CACHE:
            _ENV_CACHE.clear()
            _ENV_CACHE[ck] = frame_channel(cell(spec["cell"]), S, 0)["H"]["env"]
        H = _ENV_CACHE[ck]
        nv = spec["p_ref"] * 10 ** (-spec["snr_re_db"] / 10)
    rows = []
    for i in range(spec["i0"], spec["i1"]):
        rng = _rng(spec["exp"], BAND_CODE[spec["band"]], CELL_CODE.get(spec.get("cell"), 0),
                   int(round(-spec.get("snr_re_db", 0.0))), i)
        out = run_receiver(H, S, mask, rng, nv, spec["static_removal"])
        rows.append({"frame_stat": float(out["frame_stat"]),
                     "strongest_range_m": (float(C0 * out["strongest"]["tau_s"] / 2)
                                           if out["strongest"] else None)})
    return rows


def _dispatch(spec: dict) -> dict:
    t0 = time.time()
    rows = task_h1(spec) if spec["task"] == "h1" else task_h0(spec)
    return {"spec": {k: v for k, v in spec.items() if k != "p_ref"}, "rows": rows,
            "seconds": time.time() - t0}


# ----------------------------------------------------------------------------------------------------
#  Noise-free observation: maps, power-delay profiles, the drone cell over the trajectory
# ----------------------------------------------------------------------------------------------------
def observe(cells: dict, p_ref: dict, n_frames: int) -> dict:
    """Noise-free maps and the gated drone-cell level over the whole trajectory.  Nothing here is a
    detection: these are the channel and the map as the receiver sees them, with no threshold."""
    maps, traj, pdp = {}, {}, {}
    for ck in PRIMARY + tuple(k for _, k in DEPTH_PAIRS):
        c = cells[ck]
        for band, bd in BANDS.items():
            S = PILOT.build_system(bd["system"])
            mask = PILOT.base_mask(S)
            res = PILOT.resolution(S)
            lr = leg_rates(c)
            # level over the trajectory, every frame, both modes
            for mode in ("rt_variation", "fixed_body"):
                if mode == "fixed_body" and ck not in PRIMARY:
                    continue
                fp, fs_ = (None, 1.0)
                if mode == "fixed_body":
                    fp, fs_ = p_ref[(ck, band)]["fixed_pose"], p_ref[(ck, band)]["fixed_scale"]
                lev = {comp: [] for comp in list(COMPOSITIONS) + ["ghost_only", "env_only"]}
                rngs, conc = [], []
                wt = np.hanning(S.n_sym + 2)[1:-1]
                for n in range(n_frames):
                    Hc = frame_channel(c, S, n, mode, fp, fs_)["H"]
                    tr = truth_of(c, S, n)
                    rngs.append(tr["range_m"])
                    #: doppler_line_share - the share of the direct drone paths' slow-time energy that
                    #  stays in the single strongest Doppler row of the frame, averaged over active
                    #  subcarriers, with the receiver's slow-time window.  1 means the whole return sits
                    #  on one line; less means the pose-to-pose variation has spread it.
                    Xs = np.fft.fft(Hc["direct"][:, mask] * wt[:, None], axis=0)
                    ps = (Xs.real ** 2 + Xs.imag ** 2).mean(axis=1)
                    conc.append(float(ps.max() / max(ps.sum(), 1e-300)))
                    for comp in list(COMPOSITIONS) + ["ghost_only", "env_only"]:
                        H = (compose(Hc, comp) if comp in COMPOSITIONS else
                             (Hc["ghost1"] + Hc["ghost2"] if comp == "ghost_only" else Hc["env"]))
                        out = run_receiver(H, S, mask, _rng(99, 0), 0.0, True, return_map=True)
                        lev[comp].append(gate_power_db(out, S, tr["range_m"]))
                        if (mode == "rt_variation" and n == CFG["map_frame"] and comp in COMPOSITIONS
                                and comp not in maps.get((ck, band), {})):
                            m = maps.setdefault((ck, band), {})
                            P = out["map"]["P"]
                            m[comp] = {"P_db": (10 * np.log10(np.maximum(P, 1e-300))).astype(np.float32),
                                       "range_axis_m": (out["map"]["tau_axis"] * C0 / 2).astype(np.float32),
                                       "f_axis_hz": out["map"]["f_axis"].astype(np.float32)}
                            out2 = run_receiver(H, S, mask, _rng(99, 1), 0.0, False, return_map=True)
                            P2 = out2["map"]["P"]
                            m[comp + "_noremoval"] = {
                                "P_db": (10 * np.log10(np.maximum(P2, 1e-300))).astype(np.float32),
                                "range_axis_m": (out2["map"]["tau_axis"] * C0 / 2).astype(np.float32),
                                "f_axis_hz": out2["map"]["f_axis"].astype(np.float32)}
                traj[(ck, band, mode)] = {
                    "gate_db": {k: [float(x) for x in v] for k, v in lev.items()},
                    "range_m": [float(x) for x in rngs],
                    "doppler_line_share": [float(x) for x in conc],
                    "t_s": [float(symbol_times(S, n).mean()) for n in range(n_frames)]}
            pdp[(ck, band)] = {
                "range_resolution_m": res["range_m"], "range_sample_m": res["range_bin_m"],
                "doppler_resolution_hz": res["doppler_hz"],
                "occupied_mhz": PILOT.cfar_cells(S, PILOT.RxCfg())["occupied_span"] * S.scs_hz / 1e6,
                "truth": truth_of(c, S, 0), "doppler_hz": [float(x) for x in lr["doppler_hz"]]}
    return {"maps": maps, "traj": traj, "pdp": pdp}


# ----------------------------------------------------------------------------------------------------
#  Aggregation
# ----------------------------------------------------------------------------------------------------
def not_decidable_list(bands: dict, cellinfo: dict, traj: dict, n_frames: int) -> list:
    """Section 6, built from the ledger blocks alone so it can be rebuilt without re-running frames."""
    S_of = {b: PILOT.build_system(BANDS[b]["system"]) for b in BANDS}
    return [
    "Whether the ghost changes detection at a real site. Everything here is one simulated flat mirror "
    "ground with scattering coefficient 0, one airframe, one antenna stand-in and one carrier "
    "assumption; the `runners/jobs_0962` header's own P2 reading already says the listed ghost level "
    "leaves the computed two-ray level at A and B.",
    "Rotor micro-Doppler as a detection feature. A symbol's channel is the nearest stored pose, so the "
    f"frame carries the stored pose sequence at {CFG['prf_hz']:.0f} Hz; the frame's Doppler axis spans "
    f"+/-{1e-3 / (2 * S_of['bw20'].t_sym):.2f} kHz while the stored record carries only "
    f"+/-{CFG['prf_hz'] / 2e3:.2f} kHz, and the nearest-pose resampling puts replicas of that band at "
    f"+/-{CFG['prf_hz'] / 1e3:.1f} kHz offsets. Doppler beyond the stored band is a resampling "
    "artefact and no rotor-line claim is made from it.",
    "Any absolute sensitivity, range or link budget. The SNR axis is per resource element relative to "
    "the cell's own direct-path level; no transmit power, noise figure, antenna gain or integration "
    "budget enters, and a PathSolver level is not a radar cross section.",
    "Whether 100 MHz detects better than 20 MHz. The two bands are compared at the same SNR per "
    "resource element, and the 100 MHz band has "
    f"{bands['bw100']['occupied_mhz'] / bands['bw20']['occupied_mhz']:.2f} times the occupied "
    f"subcarriers, i.e. "
    f"{10 * math.log10(bands['bw100']['occupied_mhz'] / bands['bw20']['occupied_mhz']):.2f} dB more "
    "integrated energy at the same per-resource-element SNR. The band rows are read against each "
    "other only on range resolution and on where a peak lands, never as a detection gain.",
    f"Whether any of this carries to another grazing angle or range. The three geometries read here "
    f"span psi {min(d_['psi_deg'] for d_ in (cellinfo[k]['geometry'] for k in PRIMARY)):.2f} to "
    f"{max(d_['psi_deg'] for d_ in (cellinfo[k]['geometry'] for k in PRIMARY)):.2f} deg at one "
    f"range; the queue's E (15 m) and F (60 m) cells were not read, and nothing outside that span is "
    f"modelled from these cells.",
    f"A Pd difference smaller than the counting resolution. Each Pd is "
    f"{n_frames * CFG['n_runs']} frames ({n_frames} frames x {CFG['n_runs']} noise runs), so a "
    f"measured 0.5 carries a Wilson 95 % interval of "
    f"[{PILOT.wilson(n_frames * CFG['n_runs'] // 2, n_frames * CFG['n_runs'])[0]:.3f}, "
    f"{PILOT.wilson(n_frames * CFG['n_runs'] // 2, n_frames * CFG['n_runs'])[1]:.3f}]. The "
    f"frames of one run are consecutive poses of one record, so they are not independent draws of the "
    f"airframe state either.",
    f"The depth of the deepest ghost fade. The stored record bounds the trajectory to "
    f"{n_frames * S_of['bw20'].n_sym * S_of['bw20'].t_sym * 1e3:.1f} ms, over which the "
    f"direct-to-ghost path difference turns "
    f"{min(traj[k]['phase_turn_deg'] for k in PRIMARY):.0f} to "
    f"{max(traj[k]['phase_turn_deg'] for k in PRIMARY):.0f} deg at the constant rate the channel uses "
    f"({min(traj[k].get('phase_turn_exact_deg', float('nan')) for k in PRIMARY):.0f} to "
    f"{max(traj[k].get('phase_turn_exact_deg', float('nan')) for k in PRIMARY):.0f} deg for the exact "
    f"translated geometry). The peak-to-peak figures of section 3 are what that turn reached, not a "
    f"full fade cycle at every cell.",
    "What the ground return does to detection while the slow-time mean removal is on. That path is "
    "static, so the removal takes it out (section 3) and the `+ env` rows of section 4 are then "
    "carrying the drone paths and, in the cells whose map frame has a dropout, that dropout. Section "
    "4.3, with the removal off, is the only place the ground return itself is in the statistic, and "
    "that is one SNR point per band.",
    "Tracking. No tracker exists in this repository, so nothing here says whether a track would be "
    "held, lost or reacquired; `miss_run` counts frames, not track states.",
    f"Whether the trajectory is realistic. The {CFG['traj']['v_h_mps']:g} m/s recession and "
    f"{CFG['traj']['v_z_mps']:g} m/s climb were chosen so the body Doppler clears the slow-time mean "
    f"removal and the direct-to-ghost phase turns within the stored record; no flight profile was "
    f"measured, the drone's attitude does not change with the motion, and the delay is carried at a "
    f"constant rate rather than at the exact translated length (section 1).",
    "Anything at the rectangular range-bin window. Every number here uses the Hann window of the "
    "0917 pilot's receiver; `runners/jobs_0962` reads its own quantities at Hann with the "
    "rectangular window as the knob, and that knob was not turned here.",
    "What a real target-absent frame looks like. H0 here deletes the drone paths from the stored list; "
    "the ray tracer was not re-run on a drone-free scene, so scene returns that only exist because the "
    "drone is there (shadowing of the ground, for one) are deleted with it.",
    ]


def class_counts(c: dict) -> dict:
    """Listed paths of each end-leg class at every pose of the record (not a subsample)."""
    out = {}
    for i, name in enumerate(LEGS):
        out[name] = np.array([int((c["leg"][c["off"][t]:c["off"][t + 1]] == i).sum())
                              for t in range(c["pose"].size)], np.int64)
    return out


def cell_table(cells: dict) -> dict:
    """The per-cell block of the ledger: geometry, shard stamps and the class counts."""
    info = {}
    for k, c in cells.items():
        cc = class_counts(c)
        info[k] = {"stem": c["stem"], "geometry": geometry(c), "stamps": c["stamps"],
                   "median_paths_per_pose": float(np.median(c["n_paths"])),
                   "class_counts_median": {n: float(np.median(v)) for n, v in cc.items()},
                   "fc_hz": c["fc_hz"], "carrier_source": ("`_fc` tag" if "_fc" in c["stem"]
                                                           else "sweep convention 3.5 GHz")}
    return info


def trajectory_table(cells: dict, n_frames: int) -> dict:
    """The synthetic trajectory per cell: the constant rates the channel uses, and how far that
    constant-rate model has drifted from the exact translated geometry by the end of the record."""
    S20 = PILOT.build_system(BANDS["bw20"]["system"])
    T = n_frames * S20.n_sym * S20.t_sym
    traj = {}
    for k, c in cells.items():
        lr = leg_rates(c)
        lam = C0 / c["fc_hz"]
        dr = linearisation_drift(c, T)
        traj[k] = {"doppler_hz": [float(x) for x in lr["doppler_hz"]],
                   "doppler_bins": [float(x) * S20.n_sym * S20.t_sym for x in lr["doppler_hz"]],
                   "rate_mps": [float(x) for x in lr["rate_mps"]],
                   "excess_rate_mps": lr["excess_rate_mps"],
                   "record_seconds": T,
                   "phase_turn_deg": 360.0 * lr["excess_rate_mps"] * T / lam,
                   "phase_turn_exact_deg": dr["excess_turn_exact_deg"],
                   "linearisation": dr,
                   "travel_m": math.hypot(CFG["traj"]["v_h_mps"], CFG["traj"]["v_z_mps"]) * T}
    return traj


def depth_table(cells: dict, cellinfo: dict, obs: dict) -> dict:
    """max_depth 2 against max_depth 3, read only where the depth-2 path list is found unchanged
    inside the depth-3 list of the same pose.

    `subset_fraction` is over every 128th pose (an exact (tau, Re a, Im a) match).  `new_paths` is
    the other direction and the one the document quotes: per pose, the depth-3 paths that are NOT in
    the depth-2 list, counted by end-leg class - a count of what depth 3 added, not a difference of
    two medians."""
    pairs = []
    for d2, d3 in DEPTH_PAIRS:
        c2, c3 = cells[d2], cells[d3]
        hit, tot = 0, 0
        new = {n: [] for n in LEGS}
        for t in range(0, c2["pose"].size, 128):
            s2, e2 = int(c2["off"][t]), int(c2["off"][t + 1])
            s3, e3 = int(c3["off"][t]), int(c3["off"][t + 1])
            key3 = set(zip(c3["tau"][s3:e3].tolist(), c3["a"][s3:e3].real.tolist(),
                           c3["a"][s3:e3].imag.tolist()))
            key2 = set(zip(c2["tau"][s2:e2].tolist(), c2["a"][s2:e2].real.tolist(),
                           c2["a"][s2:e2].imag.tolist()))
            hit += sum(1 for x in zip(c2["tau"][s2:e2].tolist(), c2["a"][s2:e2].real.tolist(),
                                      c2["a"][s2:e2].imag.tolist()) if x in key3)
            tot += e2 - s2
            leg3 = c3["leg"][s3:e3]
            fresh = np.array([x not in key2 for x in zip(c3["tau"][s3:e3].tolist(),
                                                         c3["a"][s3:e3].real.tolist(),
                                                         c3["a"][s3:e3].imag.tolist())], bool)
            for i, n in enumerate(LEGS):
                new[n].append(int(((leg3 == i) & fresh).sum()))
        med2 = cellinfo[d2]["class_counts_median"]
        med3 = cellinfo[d3]["class_counts_median"]
        shift = {}
        for band in BANDS:
            a = np.array(obs["traj"][(d2, band, "rt_variation")]["gate_db"]["direct_ghost"])
            b = np.array(obs["traj"][(d3, band, "rt_variation")]["gate_db"]["direct_ghost"])
            shift[band] = float(b.mean() - a.mean())
        pairs.append({"d2": d2, "d3": d3, "subset_fraction": hit / tot,
                      "new_paths_median": {n: float(np.median(v)) for n, v in new.items()},
                      "class_counts_median_d2": med2, "class_counts_median_d3": med3,
                      "new_classes": ", ".join(f"{n} {float(np.median(new[n])):+.0f}" for n in LEGS),
                      "level_shift_db": shift, "read": hit / tot > 0.999})
    return {"pairs": pairs}


def derive_levels(obs: dict, n_frames: int) -> dict:
    """The noise-free level tables of section 3, built from the observation pass alone."""
    levels = {"frame0": [], "trajectory": []}
    for ck in PRIMARY + tuple(x for _, x in DEPTH_PAIRS):
        for band in BANDS:
            m = obs["maps"][(ck, band)]
            tr = obs["pdp"][(ck, band)]["truth"]
            res = obs["pdp"][(ck, band)]["range_resolution_m"]

            def cellmax(entry, rng_m):
                ax = entry["range_axis_m"]
                sel = np.abs(ax - rng_m) <= res / 2
                if not sel.any():
                    sel = np.abs(ax - rng_m) == np.abs(ax - rng_m).min()
                return float(entry["P_db"][:, sel].max())
            d0 = cellmax(m["direct"], tr["range_m"])
            levels["frame0"].append({
                "cell": ck, "band": band,
                "direct_ghost_rel_db": cellmax(m["direct_ghost"], tr["range_m"]) - d0,
                "direct_ghost_env_rel_db": cellmax(m["direct_ghost_env"], tr["range_m"]) - d0,
                "env_cell_rel_drone_db": cellmax(m["direct_ghost_env"], tr["env_range_m"])
                - cellmax(m["direct_ghost_env"], tr["range_m"]),
                "env_cell_rel_drone_noremoval_db": cellmax(m["direct_ghost_env_noremoval"], tr["env_range_m"])
                - cellmax(m["direct_ghost_env_noremoval"], tr["range_m"]),
                "drone_cell_abs_db": d0})
    levels["coherent_vs_class_sum"] = []
    for (ck, band, mode), t in obs["traj"].items():
        if mode != "rt_variation":
            continue
        dd = np.array(t["gate_db"]["direct"])
        gg = np.array(t["gate_db"]["ghost_only"])
        co = np.array(t["gate_db"]["direct_ghost"])
        inc = 10 * np.log10(10 ** (dd / 10) + 10 ** (gg / 10))
        levels["coherent_vs_class_sum"].append({
            "cell": ck, "band": band,
            "ghost_only_rel_direct_db": float((gg - dd).mean()),
            "coherent_rel_direct_mean_db": float((co - dd).mean()),
            "coherent_rel_direct_min_db": float((co - dd).min()),
            "coherent_rel_direct_max_db": float((co - dd).max()),
            "class_power_sum_rel_direct_db": float((inc - dd).mean()),
            "coherent_minus_class_sum_max_db": float(np.abs(co - inc).max())})
    levels["coherent_vs_class_sum"].sort(key=lambda r: (r["cell"], r["band"]))
    for (ck, band, mode), t in obs["traj"].items():
        if band != "bw100":
            continue
        a = np.array(t["gate_db"]["direct"])
        b = np.array(t["gate_db"]["direct_ghost"])
        levels["trajectory"].append({"cell": ck, "band": band, "mode": mode,
                                     "ptp_direct_db": float(np.ptp(a)), "ptp_ghost_db": float(np.ptp(b)),
                                     "mean_shift_db": float(b.mean() - a.mean()),
                                     "max_step_db": float(np.abs(np.diff(b)).max()),
                                     "doppler_line_share_median": float(np.median(t["doppler_line_share"]))})
    levels["trajectory"].sort(key=lambda r: (r["cell"], r["mode"]))
    return levels


def threshold_from(stats: np.ndarray, pfa: float) -> float:
    """Frame threshold at a false-alarm target: the (1 - pfa) quantile of the calibration ablation's
    frame statistics, by linear interpolation of the order statistics."""
    return float(np.quantile(np.asarray(stats, float), 1.0 - pfa, method="linear"))


def miss_runs(detected: np.ndarray) -> dict:
    """Runs of consecutive frames with no gated detection inside one trajectory run."""
    runs, cur = [], 0
    for d in detected:
        if d:
            if cur:
                runs.append(cur)
            cur = 0
        else:
            cur += 1
    if cur:
        runs.append(cur)
    return {"n_runs": len(runs), "max": int(max(runs)) if runs else 0,
            "mean": float(np.mean(runs)) if runs else 0.0, "total_missed": int(sum(runs))}


def aggregate(h1_rows: list, h0: dict, S_of: dict, n_frames: int, env_range_of: dict) -> dict:
    """Pd, false-alarm rate, wrong-range rate and missed-detection runs per arm and SNR point."""
    arms = {}
    for r in h1_rows:
        key = (r["cell"], r["band"], r["comp"], r["mode"], bool(r["static_removal"]), r["snr_re_db"])
        arms.setdefault(key, []).append(r)
    out = []
    for key, rows in sorted(arms.items(), key=lambda kv: str(kv[0])):
        ck, band, comp, mode, removal, snr = key
        S = S_of[band]
        res = PILOT.resolution(S)
        h0key = (("env", CELLS[ck]["geo"], band, removal, snr) if comp == "direct_ghost_env"
                 else ("noise", band, removal))
        cal, ev = h0[h0key]["cal"], h0[h0key]["eval"]
        entry = {"cell": ck, "band": band, "comp": comp, "mode": mode, "static_removal": removal,
                 "snr_re_db": snr, "n_frames": len(rows),
                 "h0_kind": h0key[0], "n_h0_cal": len(cal), "n_h0_eval": len(ev), "pfa": {}}
        for pfa in CFG["pfa_frame"]:
            T = threshold_from(cal, pfa)
            k = int((np.asarray(ev) >= T).sum())
            det = np.array([r["gated_T"] >= T for r in rows], bool)
            frame_det = np.array([r["frame_stat"] >= T for r in rows], bool)
            wrong = np.array([frame_det[i] and not rows[i]["strongest_is_gated"]
                              for i in range(len(rows))], bool)
            by_run = {}
            for i, r in enumerate(rows):
                by_run.setdefault(r["run"], {})[r["frame"]] = det[i]
            mr = [miss_runs(np.array([v[f] for f in sorted(v)], bool)) for v in by_run.values()]
            errs = [r["gated_range_err_m"] for i, r in enumerate(rows) if det[i]]
            sr = np.array([r["strongest_range_m"] for i, r in enumerate(rows)
                           if frame_det[i] and r["strongest_range_m"] is not None])
            env_r = env_range_of[ck]
            entry["pfa"][f"{pfa:g}"] = {
                "threshold_T": T,
                "pfa_measured_eval": k / len(ev), "pfa_wilson95": PILOT.wilson(k, len(ev)),
                "pd_gated": float(det.mean()), "pd_gated_wilson95": PILOT.wilson(int(det.sum()), det.size),
                "pd_frame": float(frame_det.mean()),
                "wrong_range_rate": float(wrong.mean()),
                "wrong_range_of_detected": float(wrong.sum() / max(frame_det.sum(), 1)),
                "miss_run_max": int(max(m["max"] for m in mr)) if mr else 0,
                "miss_run_mean": float(np.mean([m["mean"] for m in mr])) if mr else 0.0,
                "miss_runs_total": int(sum(m["n_runs"] for m in mr)),
                "gated_range_err_median_m": float(np.median(errs)) if errs else None,
                "gated_range_err_p95_m": float(np.percentile(np.abs(errs), 95)) if errs else None,
                "strongest_range_median_m": float(np.median(sr)) if sr.size else None,
                "strongest_in_env_cell_share": (float((np.abs(sr - env_r) <= res["range_m"] / 2).mean())
                                                if sr.size else None),
                "env_range_m": env_r,
            }
        entry["range_resolution_m"] = res["range_m"]
        out.append(entry)
    return {"arms": out}


# ----------------------------------------------------------------------------------------------------
#  Independent verification
# ----------------------------------------------------------------------------------------------------
def verify(cells: dict, n_frames: int) -> dict:
    """Recompute the load-bearing steps by a second route.  Failures are reported, never smoothed."""
    v = {}
    # (1) blocked CFR against the plain exponential form
    c = cells["A_d2"]
    s, e = int(c["off"][0]), int(c["off"][1])
    worst = 0.0
    for fft, scs in ((1024, 30e3), (4096, 30e3)):
        amp = c["a"][s:e] * np.exp(-2j * math.pi * c["fc_hz"] * c["tau"][s:e])
        g = cfr_groups(fft, scs, amp, c["tau"][s:e],
                       {"all": np.arange(e - s)}, _block_q(fft))["all"]
        d = cfr_direct(fft, scs, amp, c["tau"][s:e])
        worst = max(worst, float(np.abs(g - d).max() / np.abs(d).max()))
    v["cfr_block_vs_direct_max_rel"] = worst
    # (2) the stored field E against the path sum, the Q0 check repeated on the merged record
    rel = []
    for t in (0, 1, 1000, 4095):
        s, e = int(c["off"][t]), int(c["off"][t + 1])
        hit = c["leg"][s:e] >= 0
        amp = c["a"][s:e][hit] * np.exp(-2j * math.pi * c["fc_hz"] * c["tau"][s:e][hit])
        rel.append(abs(amp.sum() - c["E"][t]) / max(abs(c["E"][t]), 1e-300))
    v["path_sum_rel_err_max"] = float(max(rel))
    # (3) the grid channel against the pilot's time-domain channel for one frame of one pose
    S = PILOT.build_system(BANDS["bw20"]["system"])
    mask = PILOT.base_mask(S)
    s, e = int(c["off"][0]), int(c["off"][1])
    hit = c["leg"][s:e] >= 0
    tau = c["tau"][s:e][hit]
    amp = c["a"][s:e][hit] * np.exp(-2j * math.pi * c["fc_hz"] * tau)
    paths = [{"tau_s": float(tau[i]), "f_hz": 0.0, "amp": complex(amp[i])} for i in range(tau.size)]
    rng = np.random.default_rng(7)
    X = PILOT.payload(rng, S, mask, CFG["modulation"], S.n_sym)
    Yt = PILOT.demod(PILOT.channel_time(PILOT.tx_time(X, S), S, paths, 0.0, rng), S, S.n_sym)
    Yg = PILOT.channel_grid(X, S, paths, 0.0, rng)
    v["grid_vs_time_active_rel_l2"] = float(np.linalg.norm(Yt[:, mask] - Yg[:, mask])
                                            / np.linalg.norm(Yg[:, mask]))
    v["grid_vs_time_null_leak_rel"] = float(np.abs(Yt[:, ~mask]).max() / np.abs(Yg[:, mask]).max())
    #: control - the same comparison with every delay rounded to a whole sample.  The grid channel
    #  applies a per-symbol phase ramp; the pilot's time-domain channel applies one circular ramp over
    #  the whole frame, whose fractional-delay kernel reaches across symbol boundaries.  With integer
    #  delays that kernel is exact, so the residual left at integer delays is the numerical floor and
    #  the residual above it is the fractional-delay model difference, not a defect of either channel.
    tau_int = np.round(tau * S.fs) / S.fs
    amp_int = c["a"][s:e][hit] * np.exp(-2j * math.pi * c["fc_hz"] * tau_int)
    pi_ = [{"tau_s": float(tau_int[i]), "f_hz": 0.0, "amp": complex(amp_int[i])} for i in range(tau.size)]
    rng = np.random.default_rng(7)
    Xi = PILOT.payload(rng, S, mask, CFG["modulation"], S.n_sym)
    Yti = PILOT.demod(PILOT.channel_time(PILOT.tx_time(Xi, S), S, pi_, 0.0, rng), S, S.n_sym)
    Ygi = PILOT.channel_grid(Xi, S, pi_, 0.0, rng)
    v["grid_vs_time_integer_delay_rel_l2"] = float(np.linalg.norm(Yti[:, mask] - Ygi[:, mask])
                                                   / np.linalg.norm(Ygi[:, mask]))
    # (4) the end-leg rule: no listed path has an environment interaction strictly inside
    v["interior_env_paths"] = {k: int(cells[k]["interior_env_paths"]) for k in cells}
    v["end_leg_rule_exact"] = all(x == 0 for x in v["interior_env_paths"].values())
    # (5) geometry against the runners/jobs_0962 header's own computed columns
    geo = {}
    for k, cc in cells.items():
        g = geometry(cc)
        geo[k] = {"psi_deg": g["psi_deg"], "header_psi_deg": cc["header_psi_deg"],
                  "psi_diff_deg": g["psi_deg"] - cc["header_psi_deg"],
                  "excess_cm": g["excess_cm"], "header_excess_cm": cc["header_excess_cm"],
                  "excess_diff_cm": g["excess_cm"] - cc["header_excess_cm"],
                  "radar_height_m": g["radar_height_m"]}
    v["geometry_vs_header"] = geo
    v["geometry_within_header_rounding"] = all(abs(x["psi_diff_deg"]) < 0.02
                                               and abs(x["excess_diff_cm"]) < 0.05 for x in geo.values())
    # (6) the measured delay excess of the ghost class against the computed two-ray excess
    exc = {}
    for k, cc in cells.items():
        s, e = int(cc["off"][0]), int(cc["off"][1])
        leg = cc["leg"][s:e]
        tau = cc["tau"][s:e]
        if (leg == 1).any():
            exc[k] = {"measured_cm": float(100 * (np.median(tau[leg == 1]) - np.median(tau[leg == 0])) * C0),
                      "computed_cm": geometry(cc)["excess_cm"]}
    v["ghost_excess_first_pose"] = exc
    # (7) the environment-only path is the nadir return: one key, constant over the record
    envc = {}
    for k, cc in cells.items():
        m = cc["leg"] == 3
        r = cc["tau"][m] * C0 / 2
        per_pose = np.array([int((cc["leg"][cc["off"][t]:cc["off"][t + 1]] == 3).sum())
                             for t in range(cc["pose"].size)])
        envc[k] = {"n_paths": int(m.sum()), "distinct_round_trip_ps": int(np.unique(np.round(r * 2 / C0 * 1e12)).size),
                   "range_m": float(np.median(r)),
                   "nadir_half_round_trip_m": geometry(cc)["nadir_round_trip_m"] / 2,
                   "poses_without_env_path": int((per_pose == 0).sum()),
                   "poses": int(cc["pose"].size)}
    v["env_only_path"] = envc
    twin = {}
    for d2, d3 in DEPTH_PAIRS:
        c2, c3 = cells[d2], cells[d3]
        m2, m3 = c2["leg"] == 3, c3["leg"] == 3
        twin[f"{d2}|{d3}"] = {
            "same_round_trip": bool(abs(float(np.median(c2["tau"][m2])) - float(np.median(c3["tau"][m3])))
                                    * C0 < 1e-6),
            "amplitude_rel_diff": float(abs(np.median(np.abs(c2["a"][m2])) - np.median(np.abs(c3["a"][m3])))
                                        / max(np.median(np.abs(c2["a"][m2])), 1e-300))}
    v["env_only_path_depth_twin"] = twin
    v["env_ablation_shared_across_depth"] = all(x["same_round_trip"] and x["amplitude_rel_diff"] < 1e-6
                                                for x in twin.values())
    # (8) the gated class power of docs/READOUT_0918.md reproduced here, and the gate factor that
    #     separates it from the ungated per-resource-element level this file works with
    def h_window(x: np.ndarray) -> np.ndarray:
        """The range-bin window of benchmark/readout_0918.py:170 (Hann), repeated here."""
        return np.sinc(x) + 0.5 * (np.sinc(x - 1.0) + np.sinc(x + 1.0))

    stored = {}
    try:
        led = json.load(open(os.path.join(ROOT, READOUT_LEDGER)))
        for row in led["gates"]["0962"]["per_cell"]:
            stored[row["cell"]] = row["20 MHz"]["class_power_db"]
    except Exception as exc:                                       # noqa: BLE001
        stored = {"_error": str(exc)}
    cross = {}
    B = 20e6
    for k in ("A_d2", "B_d2", "C_d2"):
        cc = cells[k]
        tau0 = 2.0 * cc["R"] / C0
        amp = cc["a"] * np.exp(-2j * math.pi * cc["fc_hz"] * cc["tau"])
        w = h_window(B * (cc["tau"] - tau0))
        g = amp * w
        pid = np.repeat(np.arange(cc["n_paths"].size), cc["n_paths"])
        out = {}
        for name, sel in (("g", cc["leg"] == 3), ("direct_leg", cc["leg"] == 0),
                          ("ghost1_leg", cc["leg"] == 1)):
            if not sel.any():
                continue
            E_B = (np.bincount(pid[sel], weights=g[sel].real, minlength=cc["n_paths"].size)
                   + 1j * np.bincount(pid[sel], weights=g[sel].imag, minlength=cc["n_paths"].size))
            out[name] = float(10 * np.log10(max(float(np.mean(np.abs(E_B) ** 2)), 1e-300)))
        env = cc["leg"] == 3
        out["env_ungated_db"] = float(10 * np.log10(float(np.mean(np.abs(cc["a"][env]) ** 2))))
        out["env_gate_offset_cells"] = float(np.median(B * (cc["tau"][env] - tau0)))
        out["env_gate_weight_db"] = float(20 * np.log10(abs(float(h_window(
            np.array([out["env_gate_offset_cells"]]))[0]))))
        out["readout_class_power_db"] = stored.get(cc["stem"], {})
        cross[k] = out
    v["readout_cross_check_20MHz"] = cross
    v["env_gated_matches_readout"] = all(
        ("g" in x and isinstance(x["readout_class_power_db"], dict)
         and x["readout_class_power_db"].get("[g]") is not None
         and abs(x["g"] - x["readout_class_power_db"]["[g]"]) < 0.05) for x in cross.values())

    # (9) isolated_20xmedian of the merged record against the poses with no environment-only path
    iso = {}
    for k, cc in cells.items():
        E = cc["E"]
        m = complex(float(np.median(E.real)), float(np.median(E.imag)))
        dd = np.abs(E - m)
        sel = dd > 20.0 * np.median(dd)
        miss = np.array([int((cc["leg"][cc["off"][t]:cc["off"][t + 1]] == 3).sum()) == 0
                         for t in range(cc["pose"].size)], bool)
        nb = np.zeros_like(miss)
        nb[1:-1] = miss[1:-1] & ~miss[:-2] & ~miss[2:]
        iso[k] = {"isolated_20xmedian": int(sel.sum()), "normaliser": float(np.median(dd)),
                  "abs_m": float(abs(m)), "poses_missing_env_path": int(miss.sum()),
                  "env_path_missing": int(nb.sum()),
                  "missing_env_that_are_isolated": int((miss & sel).sum())}
    v["isolated_and_env_path_missing"] = iso

    # (10) the constant-rate delay model against the exact translated geometry over the record
    S20 = PILOT.build_system(BANDS["bw20"]["system"])
    rec_s = n_frames * S20.n_sym * S20.t_sym
    v["linearisation_drift"] = {k: linearisation_drift(cc, rec_s) for k, cc in cells.items()}

    # (11) what the slow-time mean removal leaves of the environment-only path, and where the
    #      environment cell's level comes from once it has run.  The environment-only path is one
    #      constant delay and one constant gain over the record (check 7), so the removal takes it out
    #      exactly - except at a pose where the solver did not list it, where the removal leaves the
    #      difference as an impulse.  Frame 0 is the frame the section-3 map table and the
    #      environment-only ablation channel (`task_h0`) are both built from, so the dropout poses
    #      inside frame 0 are the ones that matter for both.
    envrem = {}
    for k, cc in cells.items():
        miss = np.array([int((cc["leg"][cc["off"][t]:cc["off"][t + 1]] == 3).sum()) == 0
                         for t in range(cc["pose"].size)], bool)
        miss_idx = np.flatnonzero(miss)
        for band, bd in BANDS.items():
            S2 = PILOT.build_system(bd["system"])
            mask2 = PILOT.base_mask(S2)
            t0_ = symbol_times(S2, CFG["map_frame"])
            pose0 = np.clip(np.rint(CFG["prf_hz"] * t0_).astype(np.int64), 0, cc["pose"].size - 1)
            in_frame = [int(x) for x in miss_idx if pose0.min() <= x <= pose0.max()]
            Hc = frame_channel(cc, S2, CFG["map_frame"])["H"]
            env_r = geometry(cc)["nadir_round_trip_m"] / 2
            row = {"env_dropout_poses_in_map_frame": in_frame,
                   "map_frame_pose_span": [int(pose0.min()), int(pose0.max())]}
            for name, H_ in (("env_only", Hc["env"]), ("direct_only", Hc["direct"])):
                for rem in (True, False):
                    out = run_receiver(H_, S2, mask2, _rng(98, 0), 0.0, rem, return_map=True)
                    row[f"{name}_removal_{'on' if rem else 'off'}_env_cell_db"] = gate_power_db(
                        out, S2, env_r)
            envrem[f"{k}|{band}"] = row
    v["env_path_under_static_removal"] = envrem
    v["env_path_removed_where_no_dropout_in_map_frame"] = all(
        (r["env_only_removal_on_env_cell_db"] < r["direct_only_removal_on_env_cell_db"] - 100.0)
        for r in envrem.values() if not r["env_dropout_poses_in_map_frame"])

    # (12) range migration inside one frame, as a fraction of a range cell
    mig = {}
    for band, bd in BANDS.items():
        S2 = PILOT.build_system(bd["system"])
        res = PILOT.resolution(S2)
        for k, cc in cells.items():
            rate = leg_rates(cc)["rate_mps"][0]
            dl = rate * S2.n_sym * S2.t_sym / 2
            mig[f"{k}_{band}"] = {"range_change_in_frame_m": dl,
                                  "fraction_of_range_resolution": dl / res["range_m"]}
    v["range_migration_in_frame"] = mig
    return v


# ----------------------------------------------------------------------------------------------------
#  Figures
# ----------------------------------------------------------------------------------------------------
def figures(d: dict, obs: dict, prefix: str) -> dict:
    plt = PILOT._style()
    from paper_kit import series_style
    figs = {}
    comps = list(COMPOSITIONS)
    labels = {"direct": "direct only", "direct_ghost": "direct + mixed",
              "direct_ghost_env": "direct + mixed + env"}

    # F1 - gated power-delay profile, three compositions x two bands, cell A, frame 0, noise free
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.3))
    for ax, band in zip(axs, BANDS):
        m = obs["maps"][("A_d2", band)]
        tr = obs["pdp"][("A_d2", band)]["truth"]
        res = obs["pdp"][("A_d2", band)]["range_resolution_m"]
        for i, comp in enumerate(comps):
            P = m[comp]["P_db"]
            ax.plot(m[comp]["range_axis_m"], P.max(axis=0) - P.max(),
                    label=labels[comp], **series_style(i, marker=False))
        ax.axvspan(tr["range_m"] - res / 2, tr["range_m"] + res / 2, color="#cccccc", alpha=0.55, lw=0)
        ax.axvline(tr["env_range_m"], color="#888888", ls=":", lw=1.0)
        ax.set_xlim(0, 45)
        ax.set_ylim(-70, 3)
        ax.set_xlabel("round-trip range [m]")
        ax.set_title(f"{BANDS[band]['label_mhz']:.0f} MHz")
    axs[0].set_ylabel("map power [dB rel. max]")
    axs[1].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.suptitle(f"A (psi {CELLS['A_d2']['header_psi_deg']:.1f} deg), frame {CFG['map_frame']}, "
                 f"noise free, slow-time mean removed", y=1.03)
    figs["pdp"] = PILOT._save(fig, prefix + "pdp.png")
    plt.close(fig)

    # F2 - range-Doppler maps, three compositions, cell A, bw100, with and without mean removal
    fig, axs = plt.subplots(2, 3, figsize=(9.4, 5.0), sharex=True, sharey=True)
    m = obs["maps"][("A_d2", "bw100")]
    for j, comp in enumerate(comps):
        for i, suff in enumerate(("", "_noremoval")):
            P = m[comp + suff]["P_db"]
            ax = axs[i, j]
            im = ax.pcolormesh(m[comp + suff]["range_axis_m"], m[comp + suff]["f_axis_hz"] / 1e3,
                               P - P.max(), vmin=-60, vmax=0, shading="auto", cmap="magma", rasterized=True)
            ax.set_xlim(0, 45)
            ax.set_ylim(-3, 3)
            if i == 0:
                ax.set_title(labels[comp])
            if j == 0:
                ax.set_ylabel(("mean removed\n" if i == 0 else "no mean removal\n") + "Doppler [kHz]")
            if i == 1:
                ax.set_xlabel("round-trip range [m]")
    cb = fig.colorbar(im, ax=axs, fraction=0.025, pad=0.02)
    cb.set_label("map power [dB rel. panel max]")
    figs["rangedoppler"] = PILOT._save(fig, prefix + "rangedoppler.png")
    plt.close(fig)

    # F3 - Pd against per-resource-element SNR, per composition, three geometries x two bands
    #: the two rows carry different SNR grids (section 1), so the x axis is not shared between them
    fig, axs = plt.subplots(2, 3, figsize=(9.6, 5.8), sharey=True)
    pfa_key = f"{CFG['pfa_frame'][0]:g}"
    for i, band in enumerate(BANDS):
        for j, ck in enumerate(PRIMARY):
            ax = axs[i, j]
            for n, comp in enumerate(comps):
                rows = sorted([a for a in d["detection"]["arms"]
                               if a["cell"] == ck and a["band"] == band and a["comp"] == comp
                               and a["mode"] == "rt_variation" and a["static_removal"]],
                              key=lambda a: a["snr_re_db"])
                if not rows:
                    continue
                ax.plot([r["snr_re_db"] for r in rows], [r["pfa"][pfa_key]["pd_gated"] for r in rows],
                        label=labels[comp], **series_style(n))
            ax.set_ylim(-0.03, 1.03)
            if i == 0:
                ax.set_title(f"{ck.split('_')[0]} (psi {CELLS[ck]['header_psi_deg']:.1f} deg)")
            if j == 0:
                ax.set_ylabel(f"{BANDS[band]['label_mhz']:.0f} MHz\nPd gated")
            ax.set_xlabel("SNR per resource element [dB]")
    axs[0, 2].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.subplots_adjust(hspace=0.45)
    fig.suptitle(f"frame false-alarm target {pfa_key} on the drone-deleted ablation", y=1.0)
    figs["pd"] = PILOT._save(fig, prefix + "pd.png")
    plt.close(fig)

    # F4 - the gated drone cell over the trajectory: ray-traced variation against a fixed body
    fig, axs = plt.subplots(1, 3, figsize=(9.6, 3.2), sharey=True)
    for j, ck in enumerate(PRIMARY):
        ax = axs[j]
        base = float(np.mean(obs["traj"][(ck, "bw100", "rt_variation")]["gate_db"]["direct"]))
        for n, (mode, comp) in enumerate((("rt_variation", "direct"), ("rt_variation", "direct_ghost"),
                                          ("fixed_body", "direct"), ("fixed_body", "direct_ghost"))):
            t = obs["traj"][(ck, "bw100", mode)]
            y = np.array(t["gate_db"][comp])
            ax.plot(np.array(t["t_s"]) * 1e3, y - base,
                    label=f"{'RT' if mode == 'rt_variation' else 'fixed body'}, "
                          f"{'direct' if comp == 'direct' else 'direct + mixed'}",
                    **series_style(n, marker=False))
        ax.set_xlabel("time in the record [ms]")
        ax.set_title(f"{ck.split('_')[0]} (psi {CELLS[ck]['header_psi_deg']:.1f} deg)")
    axs[0].set_ylabel("gated drone cell [dB rel. mean]")
    axs[2].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.suptitle(f"{BANDS['bw100']['label_mhz']:.0f} MHz, noise free; the trajectory turns the "
                 f"direct-to-ghost phase", y=1.03)
    figs["trajectory"] = PILOT._save(fig, prefix + "trajectory.png")
    plt.close(fig)

    # F5 - depth 2 against depth 3, gated drone cell over the trajectory and Pd
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.4))
    for n, (d2, d3) in enumerate(DEPTH_PAIRS):
        for k, ls in ((d2, "-"), (d3, "--")):
            t = obs["traj"][(k, "bw100", "rt_variation")]
            y = np.array(t["gate_db"]["direct_ghost"])
            ref = np.array(obs["traj"][(d2, "bw100", "rt_variation")]["gate_db"]["direct_ghost"]).mean()
            #: colour and marker carry the geometry, the line style carries max_depth, so no series
            #  is told apart by colour alone (paper_kit audit)
            st = series_style(n)
            st["linestyle"] = ls
            st["markevery"] = 4
            st["markerfacecolor"] = "none" if ls == "--" else st["color"]
            axs[0].plot(np.array(t["t_s"]) * 1e3, y - ref, label=f"{k}", **st)
    axs[0].set_xlabel("time in the record [ms]")
    axs[0].set_ylabel("gated drone cell\n[dB rel. depth-2 mean]")
    for n, (d2, d3) in enumerate(DEPTH_PAIRS):
        for k, ls in ((d2, "-"), (d3, "--")):
            rows = sorted([a for a in d["detection"]["arms"]
                           if a["cell"] == k and a["band"] == "bw100" and a["comp"] == "direct_ghost"
                           and a["mode"] == "rt_variation" and a["static_removal"]],
                          key=lambda a: a["snr_re_db"])
            st = series_style(n)
            st["linestyle"] = ls
            st["markerfacecolor"] = "none" if ls == "--" else st["color"]
            axs[1].plot([r["snr_re_db"] for r in rows],
                        [r["pfa"][pfa_key]["pd_gated"] for r in rows], label=k, **st)
    axs[1].set_xlabel("SNR per resource element [dB]")
    axs[1].set_ylabel("Pd gated")
    axs[1].set_ylim(-0.03, 1.03)
    h, la = axs[0].get_legend_handles_labels()
    fig.legend(h, la, loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=4, frameon=False)
    fig.suptitle(f"{BANDS['bw100']['label_mhz']:.0f} MHz, direct + mixed; "
                 f"solid max_depth 2, dashed max_depth 3", y=1.04)
    figs["depth"] = PILOT._save(fig, prefix + "depth.png")
    plt.close(fig)
    return figs


# ----------------------------------------------------------------------------------------------------
#  Ledger and document
# ----------------------------------------------------------------------------------------------------
def _sha(path: str) -> str:
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else "missing"


def _git_head() -> str:
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=20).stdout.strip() or "unknown"
    except Exception:                                              # noqa: BLE001
        return "unknown"


def _json_default(o):
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def _g(x, nd=3):
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "yes" if x else "**no**"
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    return str(x)


def _arm(d: dict, **kw):
    for a in d["detection"]["arms"]:
        if all(a[k] == v for k, v in kw.items()):
            return a
    return None


def write_doc(d: dict, path: str) -> None:
    m, v, o = d["_meta"], d["verify"], d["observation"]
    pfa0 = f"{CFG['pfa_frame'][0]:g}"
    pfa1 = f"{CFG['pfa_frame'][1]:g}"
    L = []
    L.append("# The 0962 ground-ghost path lists at the OFDM receiver: detection (Q3) - 2026-09-18\n")
    L.append(f"> Generated by `{GENERATOR}` from `{OUT_JSON}` (git HEAD at run `{m['git_head'][:12]}`); "
             f"do not edit by hand. Command: `{m['command']}`. Runtime {m['seconds']:.1f} s.")
    if m.get("figs_only_rebuild"):
        fr = m["figs_only_rebuild"]
        L.append(f"> The receiver frames are that run's. Everything derived from the stored path lists "
                 f"alone ({', '.join(fr['rebuilt'])}) was rebuilt afterwards by `{fr['command']}` at git "
                 f"HEAD `{fr['git_head'][:12]}` in {fr['seconds']:.1f} s; "
                 f"{', '.join(fr['carried_over'])} were carried over unchanged.")
    L.append("> Scope: a numpy simulation of a monostatic OFDM radar receiver on the stored path lists of "
             "`runners/jobs_0962`. The ray tracer is not run here. No hardware, no RF measurement, no "
             "antenna calibration. Drone `matrice4e` mesh revision 0, canonical thin slab "
             "(shell 0.75 mm, propeller 1.43 mm), tr38901 stand-in aimed at the drone (not the six real "
             "antennas), flat ITU-concrete ground with scattering coefficient 0 (a mirror), 4e9 rays, path "
             f"cap {m['max_paths_cap']:,}, {m['record_poses']:,}-position hover records at PRF "
             f"{m['prf_hz']:,.0f} Hz, {m['carrier_ghz']:g} GHz working assumption, "
             "sionna-rt 2.1.0, no receiver noise except where an SNR is named. Every level is a PathSolver "
             "level, not a radar cross section.\n")
    L.append("> **There is no tracker in this repository.** No association or filter over frames exists in "
             "`src/` or `benchmark/`, so no reacquisition number is written. What is written instead is "
             "`miss_run`, runs of consecutive frames of one trajectory run with no gated detection: a "
             "detection-level quantity, not a track.\n")

    L.append("## 1. What was run\n")
    L.append("Three completed low-grazing geometries of `runners/jobs_0962`, all at 30 m so that the "
             "grazing angle is the only geometry axis that moves, each crossed with two bandwidths and "
             "three nested path compositions.\n")
    L.append("| cell | job lines | R | elevation | ground alt | radar height | psi | R'-R computed | "
             "listed paths / pose (median) |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for k in PRIMARY + tuple(x for _, x in DEPTH_PAIRS):
        c = CELLS[k]
        g = d["cells"][k]["geometry"]
        L.append(f"| `{k}` ({c['geo']}, max_depth {c['depth']}) | {c['job_lines']} | {c['R']:.0f} m | "
                 f"{c['el_deg']:g} deg | {c['alt_m']:g} m | {g['radar_height_m']:.3f} m | "
                 f"{g['psi_deg']:.2f} deg | {g['excess_cm']:.1f} cm | "
                 f"{d['cells'][k]['median_paths_per_pose']:.0f} |")
    L.append("")
    L.append("The two geometries this file does **not** read, both complete on disk: E, at 15 m, sits at "
             "psi 16.10 deg by the `runners/jobs_0962` header, so against A and B it moves range and "
             "grazing angle together while against C (psi 15.53 deg) it is close to a second range at "
             "the same grazing angle - a range axis this file does not open; and F, at 60 m, is not read "
             "by that header until `runners/jobs_0961` R1 lands.\n")
    L.append("| axis | levels |")
    L.append("|---|---|")
    band_txt = "; ".join(
        "{:.0f} MHz (occupied {:.2f} MHz, range resolution {:.2f} m, range sample {:.2f} m)".format(
            b["label_mhz"], d["bands"][k]["occupied_mhz"], d["bands"][k]["range_resolution_m"],
            d["bands"][k]["range_sample_m"])
        for k, b in BANDS.items())
    L.append(f"| bandwidth | {band_txt} |")
    L.append(f"| path composition | {'; '.join(f'`{k}` = {t}' for k, t in COMPOSITION_TEXT.items())} |")
    snr_txt = "; ".join("{:.0f} MHz: {} dB".format(BANDS[b]["label_mhz"],
                                            ", ".join(f"{x:g}" for x in d["_cfg"]["snr_re_db"][b]))
                        for b in BANDS)
    L.append(f"| SNR per resource element | {snr_txt} |")
    L.append(f"| frames per trajectory run | {d['_cfg']['n_frames']} "
             f"({d['_cfg']['n_frames'] * d['bands']['bw20']['frame_ms']:.1f} ms of the "
             f"{m['record_ms']:.1f} ms record) |")
    L.append(f"| independent noise runs | {d['_cfg']['n_runs']} |")
    L.append(f"| body-amplitude arm | `rt_variation` (the stored pose sequence) and `fixed_body` "
             f"(one stored pose held for the whole record, rescaled to the same mean level) |")
    L.append("")
    tj = d["trajectory"]
    dbin = d["bands"]["bw20"]["doppler_resolution_hz"]
    L.append(f"**The synthetic trajectory.** The stored records are hovers and carry no Doppler, so a body "
             f"motion is added as geometry: the drone is translated rigidly at "
             f"{CFG['traj']['v_h_mps']:g} m/s horizontally away from the radar and "
             f"{CFG['traj']['v_z_mps']:g} m/s upward, the radar and the ground staying put. Each listed "
             f"path's length changes with the number of its end legs that reach the drone through the "
             f"ground (module docstring), so the direct and the ghost classes get different delays and "
             f"different Doppler. No single body-Doppler phase is applied to every path and no phase is "
             f"drawn at random in any frame.\n")
    L.append("**The delay every frame uses is a constant rate**, `tau + (dL/dt) t / c0`: the rate is the "
             "first-order change of that path's length at the start of the record, held for the whole "
             "record. The exact lengths of the translated geometry curve away from it, so the two "
             "columns below are given side by side and the exact one is the one to read as geometry. "
             "The channel, the maps and every detection number of this file are built from the "
             "constant-rate delay.\n")
    L.append("| cell | direct Doppler | one-ground Doppler | two-ground Doppler | direct - ghost | "
             "d(R'-R)/dt | phase turn, constant rate | phase turn, exact translation |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for k in PRIMARY + tuple(x for _, x in DEPTH_PAIRS):
        t = tj[k]
        L.append(f"| `{k}` | {t['doppler_hz'][0]:.1f} Hz ({t['doppler_bins'][0]:.2f} bins) | "
                 f"{t['doppler_hz'][1]:.1f} Hz | {t['doppler_hz'][2]:.1f} Hz | "
                 f"{t['doppler_hz'][0] - t['doppler_hz'][1]:.2f} Hz "
                 f"({abs(t['doppler_hz'][0] - t['doppler_hz'][1]) / dbin:.3f} bins) | "
                 f"{t['excess_rate_mps']:.4f} m/s | {t['phase_turn_deg']:.0f} deg | "
                 f"{t.get('phase_turn_exact_deg', float('nan')):.0f} deg |")
    L.append("")
    lz = [tj[k].get("linearisation") for k in PRIMARY if tj[k].get("linearisation")]
    if lz:
        L.append(f"Over the {tj[PRIMARY[0]]['record_seconds'] * 1e3:.1f} ms used, the constant rate leaves "
                 f"the direct class's own round-trip path short of the exact translation by "
                 f"{min(abs(x['direct_phase_deg']) for x in lz):.0f} to "
                 f"{max(abs(x['direct_phase_deg']) for x in lz):.0f} deg of carrier phase - a common "
                 f"phase on every drone path, which the Doppler processing absorbs - and turns the "
                 f"direct-to-ghost difference "
                 f"{min(x['excess_turn_linear_deg'] - x['excess_turn_exact_deg'] for x in lz):.0f} to "
                 f"{max(x['excess_turn_linear_deg'] - x['excess_turn_exact_deg'] for x in lz):.0f} deg "
                 f"further than the exact geometry would. The fade of section 3 is made of that "
                 f"relative turn, so it is read as a fade over the turn the table gives, not as a fade "
                 f"at a measured flight profile (section 6).\n")
    L.append(f"The direct and the ghost classes are **not** separable in Doppler here (they differ by at "
             f"most {max(abs(tj[k]['doppler_hz'][0] - tj[k]['doppler_hz'][1]) for k in tj) / dbin:.3f} "
             f"Doppler bins) nor in range (the two-ray excess is at most "
             f"{max(d['cells'][k]['geometry']['excess_cm'] for k in d['cells']):.1f} cm of round-trip path "
             f"against a {d['bands']['bw100']['range_resolution_m']:.2f} m range resolution at 100 MHz). "
             f"They add coherently inside one cell, and the trajectory turns their relative phase.\n")

    L.append("## 2. Checks before any detection number\n")
    L.append("| check | result |")
    L.append("|---|---|")
    L.append(f"| the end-leg rule is exact: no listed path has an environment interaction strictly between "
             f"its first and last | {_g(v['end_leg_rule_exact'])} "
             f"(interior-environment paths {sum(v['interior_env_paths'].values())} of "
             f"{d['_meta']['total_listed_paths']:,}) |")
    L.append(f"| blocked channel-frequency-response form against the plain exponential form | max relative "
             f"difference {v['cfr_block_vs_direct_max_rel']:.3g} |")
    L.append(f"| stored `E` against the sum over listed paths of `a exp(-2j pi fc tau)` (Q0's check, "
             f"repeated on the merged record) | max {v['path_sum_rel_err_max']:.3g} |")
    L.append(f"| the grid channel against the pilot's time-domain channel, one frame of one pose, on "
             f"active subcarriers | relative L2 {v['grid_vs_time_active_rel_l2']:.3g}; with every delay "
             f"rounded to a whole sample {v['grid_vs_time_integer_delay_rel_l2']:.3g} |")
    L.append(f"| geometry against the `runners/jobs_0962` header's own computed columns | "
             f"{_g(v['geometry_within_header_rounding'])} (worst psi "
             f"{max(abs(x['psi_diff_deg']) for x in v['geometry_vs_header'].values()):.3g} deg, worst "
             f"R'-R {max(abs(x['excess_diff_cm']) for x in v['geometry_vs_header'].values()):.3g} cm) |")
    mig = max(x["fraction_of_range_resolution"] for x in v["range_migration_in_frame"].values())
    L.append(f"| range migration inside one frame, as a fraction of a range resolution cell | "
             f"at most {mig:.4f} (not modelled: the delay is fixed inside a symbol) |")
    if v.get("linearisation_drift"):
        lz = list(v["linearisation_drift"].values())
        L.append(f"| the constant-rate delay against the exact translated geometry, over the record | "
                 f"direct class {min(abs(x['direct_phase_deg']) for x in lz):.0f} to "
                 f"{max(abs(x['direct_phase_deg']) for x in lz):.0f} deg of carrier phase; "
                 f"direct-to-ghost turn {min(x['excess_turn_exact_deg'] for x in lz):.0f} to "
                 f"{max(x['excess_turn_exact_deg'] for x in lz):.0f} deg exact against "
                 f"{min(x['excess_turn_linear_deg'] for x in lz):.0f} to "
                 f"{max(x['excess_turn_linear_deg'] for x in lz):.0f} deg at the constant rate |")
    if v.get("env_path_under_static_removal"):
        er = v["env_path_under_static_removal"]
        clean = [r for r in er.values() if not r["env_dropout_poses_in_map_frame"]]
        L.append(f"| the slow-time mean removal against the environment-only path, frame "
                 f"{CFG['map_frame']} | "
                 f"{_g(v.get('env_path_removed_where_no_dropout_in_map_frame'))}: where the frame lists "
                 f"the path at every pose it falls to the numerical floor of the computation (at most "
                 f"{max(r['env_only_removal_on_env_cell_db'] for r in clean):.0f} dB), against "
                 f"{max(r['env_only_removal_off_env_cell_db'] for r in clean):.1f} dB with the removal "
                 f"off |")
    L.append("")
    L.append(f"The residual left by the two channel models at fractional delays "
             f"({v['grid_vs_time_active_rel_l2']:.3g}) is the fractional-delay kernel, not a defect: the "
             f"pilot's time-domain channel applies one circular phase ramp over the whole frame, whose "
             f"interpolation kernel reaches across symbol boundaries, while the grid channel applies a "
             f"per-symbol ramp. With every delay rounded to a whole sample the same comparison falls to "
             f"{v['grid_vs_time_integer_delay_rel_l2']:.3g}. The production channel of this file is the "
             f"grid form; Q0 (`docs/RT_CHANNEL_ADAPTER_0918.md` section 3) checked the same pair at these "
             f"delays and both stay inside the cyclic prefix here "
             f"({d['bands']['bw20']['cp']} samples at "
             f"{d['bands']['bw20']['label_mhz']:.0f} MHz).\n")
    L.append("**The environment-only path is the nadir ground return and it does not move.** Its round-trip "
             "delay is a single value over the whole record in every cell:\n")
    L.append("| cell | env-only paths listed | distinct round-trip delays | range | 2 x radar height / 2 | "
             "poses with no env-only path |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for k, e in v["env_only_path"].items():
        L.append(f"| `{k}` | {e['n_paths']:,} | {e['distinct_round_trip_ps']} | {e['range_m']:.4f} m | "
                 f"{e['nadir_half_round_trip_m']:.4f} m | {e['poses_without_env_path']} of {e['poses']:,} |")
    L.append("")
    L.append("`env_path_missing` of `docs/READOUT_0917.md` section 1 - an environment-only path key present "
             "at a non-isolated neighbour position and absent at the position - applied to the single "
             "environment key of these cells, beside `isolated_20xmedian` of the merged record. In these "
             "five cells no two positions without the key are neighbours, so the count is also the plain "
             "count of positions without it:\n")
    L.append("| cell | `isolated_20xmedian` | normaliser | \\|m\\| | poses missing the env path | "
             "`env_path_missing` | missing poses that are also isolated |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for k, e in v["isolated_and_env_path_missing"].items():
        L.append(f"| `{k}` | {e['isolated_20xmedian']} | {e['normaliser']:.4g} | {e['abs_m']:.4g} | "
                 f"{e['poses_missing_env_path']} | {e['env_path_missing']} | "
                 f"{e['missing_env_that_are_isolated']} |")
    L.append("")
    L.append("Nothing here says why a solver candidate was lost.\n")
    L.append("**The level in this file and `class_power_db` in `docs/READOUT_0918.md` are the same path read "
             "at two places.** That readout's `E_B` weights every path by the range-bin window centred on "
             "the drone's nominal range (`benchmark/readout_0918.py:222`), so its `[g]` is the environment "
             "path already pushed into the drone's range bin; the map here puts the same path at its own "
             "range cell. Recomputed with the readout's own window here:\n")
    L.append("| cell | `class_power_db([g])` recomputed | the same number in `outputs/readout_0918.json` | "
             "env path ungated | gate offset | gate weight |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for k, x in v["readout_cross_check_20MHz"].items():
        st = x["readout_class_power_db"].get("[g]") if isinstance(x["readout_class_power_db"], dict) else None
        L.append(f"| `{k}` | {x['g']:.2f} dB | {('%.2f dB' % st) if st is not None else '-'} | "
                 f"{x['env_ungated_db']:.2f} dB | {x['env_gate_offset_cells']:.2f} range cells | "
                 f"{x['env_gate_weight_db']:.2f} dB |")
    L.append("")

    L.append("## 3. What the maps show, before any threshold\n")
    L.append(f"Figure, gated power-delay profile: `{d['figures']['pdp']['path']}`.\n")
    L.append(f"Figure, range-Doppler maps: `{d['figures']['rangedoppler']['path']}`.\n")
    lv = d["levels"]
    L.append("Gated drone cell and the environment cell, noise free, slow-time mean removed, frame "
             f"{CFG['map_frame']} (dB relative to the `direct` composition of the same cell and band):\n")
    L.append("| cell | band | direct | direct + mixed | + env | env cell rel. drone cell | "
             "env cell, no mean removal |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    for row in lv["frame0"]:
        L.append(f"| `{row['cell']}` | {BANDS[row['band']]['label_mhz']:.0f} MHz | 0.00 | "
                 f"{row['direct_ghost_rel_db']:+.2f} | {row['direct_ghost_env_rel_db']:+.2f} | "
                 f"{row['env_cell_rel_drone_db']:+.2f} | {row['env_cell_rel_drone_noremoval_db']:+.2f} |")
    L.append("")
    er = v.get("env_path_under_static_removal") or {}
    if er:
        clean = {k: r for k, r in er.items() if not r["env_dropout_poses_in_map_frame"]}
        dirty = {k: r for k, r in er.items() if r["env_dropout_poses_in_map_frame"]}
        L.append("**Read the two environment columns as two different things.** The environment-only path "
                 "is one constant delay and one constant gain over the record (section 2), so with the "
                 "slow-time mean removal on it is subtracted out: on its own it falls to the numerical "
                 "floor of the computation (at most "
                 f"{max(r['env_only_removal_on_env_cell_db'] for r in clean.values()):.0f} dB) in every "
                 "cell whose frame lists it at every pose. The `+ env` column therefore differs from "
                 f"`direct + mixed` by at most "
                 f"{max(abs(r['direct_ghost_env_rel_db'] - r['direct_ghost_rel_db']) for r in lv['frame0']):.2f}"
                 " dB, and the `env cell rel. drone cell` column is not a level of the ground return:")
        L.append("")
        L.append("| cell | band | env dropout poses inside the map frame | env path alone, removal on | "
                 "env path alone, removal off | drone paths alone at the env cell, removal on |")
        L.append("|---|---|---|---:|---:|---:|")
        for key in sorted(er):
            ck, band = key.split("|")
            if ck not in PRIMARY + tuple(x for _, x in DEPTH_PAIRS):
                continue
            r = er[key]
            drop = (", ".join(str(x) for x in r["env_dropout_poses_in_map_frame"])
                    if r["env_dropout_poses_in_map_frame"] else "none")
            L.append(f"| `{ck}` | {BANDS[band]['label_mhz']:.0f} MHz | {drop} "
                     f"(poses {r['map_frame_pose_span'][0]}-{r['map_frame_pose_span'][1]}) | "
                     f"{r['env_only_removal_on_env_cell_db']:.1f} dB | "
                     f"{r['env_only_removal_off_env_cell_db']:.1f} dB | "
                     f"{r['direct_only_removal_on_env_cell_db']:.1f} dB |")
        L.append("")
        L.append("So with the removal on, what sits in the environment cell is the drone paths' own "
                 "delay-domain leakage - at A and C the `env cell rel. drone cell` column and the "
                 "drone-paths-alone column agree to 0.1 dB - except where the solver did not list the "
                 "environment path at a pose inside the frame. At "
                 + ", ".join(sorted({k.split('|')[0] for k in dirty})) +
                 " the poses named in the third column fall inside the map frame (section 2's "
                 "`env_path_missing` table counts them over the whole record), and the mean removal "
                 "turns each missing pose into an impulse at the environment delay; that impulse, not "
                 "the ground return, is what the column reports there - it stands "
                 f"{min(r['env_only_removal_on_env_cell_db'] - r['direct_only_removal_on_env_cell_db'] for r in dirty.values()):.0f}"
                 " to "
                 f"{max(r['env_only_removal_on_env_cell_db'] - r['direct_only_removal_on_env_cell_db'] for r in dirty.values()):.0f}"
                 " dB above the drone paths' leakage into the same cell. Nothing here says why the "
                 "solver lost the candidate. The `no mean removal` "
                 "column is the one that carries the ground return itself, and section 4.3 is where it "
                 "acts.\n")
    L.append("**A sum of class powers is not the coherent total.** The drone gate of `direct + mixed` "
             "against the drone gate of `direct` alone and against the power sum of the two classes, "
             "averaged over the trajectory (noise free):\n")
    L.append("| cell | band | mixed alone rel. direct | coherent total rel. direct (mean / min / max) | "
             "class power sum rel. direct | largest coherent - class-sum gap |")
    L.append("|---|---|---:|---:|---:|---:|")
    for row in lv["coherent_vs_class_sum"]:
        L.append(f"| `{row['cell']}` | {BANDS[row['band']]['label_mhz']:.0f} MHz | "
                 f"{row['ghost_only_rel_direct_db']:+.2f} dB | "
                 f"{row['coherent_rel_direct_mean_db']:+.2f} / {row['coherent_rel_direct_min_db']:+.2f} / "
                 f"{row['coherent_rel_direct_max_db']:+.2f} dB | "
                 f"{row['class_power_sum_rel_direct_db']:+.2f} dB | "
                 f"{row['coherent_minus_class_sum_max_db']:.2f} dB |")
    L.append("")
    L.append(f"Figure, the gated drone cell over the trajectory: "
             f"`{d['figures']['trajectory']['path']}`.\n")
    L.append("Over the whole trajectory (noise free, 100 MHz), the gated drone cell of `direct + mixed` "
             "against `direct`:\n")
    L.append("| cell | mode | peak-to-peak of `direct` | peak-to-peak of `direct + mixed` | "
             "mean level change | largest single-frame change | `doppler_line_share` |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    for row in lv["trajectory"]:
        L.append(f"| `{row['cell']}` | {row['mode']} | {row['ptp_direct_db']:.2f} dB | "
                 f"{row['ptp_ghost_db']:.2f} dB | {row['mean_shift_db']:+.2f} dB | "
                 f"{row['max_step_db']:.2f} dB | {row['doppler_line_share_median']:.3f} |")
    L.append("")
    L.append("`doppler_line_share` is the share of the direct drone paths' slow-time energy that stays in "
             "the single strongest Doppler row of the frame, averaged over the active subcarriers with the "
             "receiver's slow-time window, median over the frames. Under `fixed_body` the drone is one "
             "constant gain moving on the trajectory, so the share is what the window alone leaves; under "
             "`rt_variation` the pose-to-pose change of the stored path lists spreads the rest. That spread "
             "is the vertical band at the drone's range in the range-Doppler figure. How much of it is the "
             "airframe's own motion and how much is the nearest-pose resampling of the stored record is not "
             "separated here (section 6).\n")

    L.append("## 4. Detection\n")
    L.append("**The H0 set is an ablation, not a target-absent measurement.** It is the same channel with "
             "every drone-touching path deleted. For `direct` and `direct + mixed` that leaves nothing but "
             "noise; for `direct + mixed + env` it leaves the environment-only path. Nothing was measured "
             "with the drone absent from the scene; the ray tracer was not re-run without the drone.\n")
    L.append("The CFAR statistic is a ratio of map power to its own training average, so the noise-only "
             "ablation's frame statistic does not depend on the noise variance: one calibration set per "
             "band and removal setting serves every SNR point. The environment-only ablation is built "
             f"from frame {CFG['map_frame']}'s environment channel and is calibrated separately at every "
             "SNR point, because its path is fixed while the noise level moves. With the mean removal on "
             "that path is subtracted out (section 3), so in the `direct + mixed + env` rows below the "
             "environment-only ablation is a noise-only ablation in every cell whose map frame lists the "
             "path at every pose; where the frame has a dropout it carries that impulse instead.\n")
    pf = [a["pfa"][pfa0]["pfa_measured_eval"] for a in d["detection"]["arms"]
          if a["mode"] == "rt_variation" and a["static_removal"] and a["cell"] in PRIMARY]
    ncal_noise = max((a["n_h0_cal"] for a in d["detection"]["arms"] if a["h0_kind"] == "noise"),
                     default=0)
    ncal_env = max((a["n_h0_cal"] for a in d["detection"]["arms"] if a["h0_kind"] == "env"), default=0)
    L.append(f"Each arm's threshold comes from its own calibration frames and the rate below is measured "
             f"on disjoint evaluation frames, so the target false-alarm rate is the same for the three "
             f"compositions rather than the threshold. **The realised rate is not the same**: the "
             f"calibration sets are finite ({ncal_noise:,} frames for the noise-only ablation, "
             f"{ncal_env:,} per SNR point for the environment-only one), so at target {pfa0} the measured "
             f"rate runs {min(pf):.3f} to {max(pf):.3f} across the arms of this table. `direct` and "
             f"`direct + mixed` of one cell, band and removal setting share one calibration set and "
             f"therefore one threshold exactly, so their Pd difference is free of that spread; the "
             f"`+ env` arm has its own, and its Pd difference carries it.\n")
    L.append(f"Figure, Pd against SNR per resource element: `{d['figures']['pd']['path']}`.\n")
    L.append(f"Frame false-alarm target {pfa0}; `pd_gated` needs a candidate above threshold within one "
             f"range resolution cell and one Doppler resolution cell of the drone. `wrong_range` is the "
             f"share of all frames in which the frame statistic crossed the threshold and the map's "
             f"largest peak - the strongest local maximum by power, which is not itself required to be "
             f"above the threshold - lies outside that gate. "
             f"`miss_run_max` is the longest run of consecutive frames of one trajectory run with no gated "
             f"detection (out of {d['_cfg']['n_frames']}).\n")
    L.append("| cell | band | composition | SNR/RE | Pd gated | Pfa measured (95 %) | wrong range | "
             "miss_run max | Pd at target " + pfa1 + " |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for a in d["detection"]["arms"]:
        if a["mode"] != "rt_variation" or not a["static_removal"] or a["cell"] not in PRIMARY:
            continue
        p0, p1 = a["pfa"][pfa0], a["pfa"][pfa1]
        L.append(f"| `{a['cell']}` | {BANDS[a['band']]['label_mhz']:.0f} MHz | `{a['comp']}` | "
                 f"{a['snr_re_db']:g} dB | {p0['pd_gated']:.3f} | {p0['pfa_measured_eval']:.4f} "
                 f"[{p0['pfa_wilson95'][0]:.4f}, {p0['pfa_wilson95'][1]:.4f}] | "
                 f"{p0['wrong_range_rate']:.3f} | {p0['miss_run_max']} | {p1['pd_gated']:.3f} |")
    L.append("")

    L.append("### 4.1 What the ghost paths did to Pd\n")
    L.append("| cell | band | SNR/RE | Pd direct | Pd direct + mixed | difference | Pd + env | "
             "difference vs direct + mixed |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for ck in PRIMARY:
        for band in BANDS:
            for snr in d["_cfg"]["snr_re_db"][band]:
                a1 = _arm(d, cell=ck, band=band, comp="direct", snr_re_db=snr, mode="rt_variation",
                          static_removal=True)
                a2 = _arm(d, cell=ck, band=band, comp="direct_ghost", snr_re_db=snr, mode="rt_variation",
                          static_removal=True)
                a3 = _arm(d, cell=ck, band=band, comp="direct_ghost_env", snr_re_db=snr,
                          mode="rt_variation", static_removal=True)
                if not (a1 and a2 and a3):
                    continue
                p1_, p2_, p3_ = (x["pfa"][pfa0]["pd_gated"] for x in (a1, a2, a3))
                L.append(f"| `{ck}` | {BANDS[band]['label_mhz']:.0f} MHz | {snr:g} dB | {p1_:.3f} | "
                         f"{p2_:.3f} | {p2_ - p1_:+.3f} | {p3_:.3f} | {p3_ - p2_:+.3f} |")
    L.append("")
    L.append("### 4.2 A fixed body amplitude against the ray-traced variation\n")
    L.append("`fixed_body` holds one stored pose for the whole record and rescales it so the mean level per "
             "resource element matches `rt_variation`; the trajectory geometry is unchanged. The "
             "difference is therefore the pose-to-pose variation of the ray-traced path lists, not a "
             "level difference.\n")
    L.append("| cell | band | SNR/RE | Pd `rt_variation` | Pd `fixed_body` | difference | "
             "miss_run max RT / fixed |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    for ck in PRIMARY:
        for band in BANDS:
            for snr in d["_cfg"]["snr_re_db"][band]:
                a1 = _arm(d, cell=ck, band=band, comp="direct_ghost", snr_re_db=snr,
                          mode="rt_variation", static_removal=True)
                a2 = _arm(d, cell=ck, band=band, comp="direct_ghost", snr_re_db=snr,
                          mode="fixed_body", static_removal=True)
                if not (a1 and a2):
                    continue
                q1, q2 = a1["pfa"][pfa0], a2["pfa"][pfa0]
                L.append(f"| `{ck}` | {BANDS[band]['label_mhz']:.0f} MHz | {snr:g} dB | "
                         f"{q1['pd_gated']:.3f} | {q2['pd_gated']:.3f} | "
                         f"{q2['pd_gated'] - q1['pd_gated']:+.3f} | "
                         f"{q1['miss_run_max']} / {q2['miss_run_max']} |")
    L.append("")
    L.append("### 4.3 Slow-time mean removal off\n")
    ro = ", ".join(f"{BANDS[b]['label_mhz']:.0f} MHz at {CFG['removal_off_snr_db'][b]:g} dB"
                   for b in BANDS)
    L.append(f"At {ro} per resource element, `direct + mixed + env` with the "
             f"slow-time mean removal of the 0917 pilot's step 3 switched off, against the same arm with it "
             f"on. The environment-only path is at zero Doppler and at the radar's own height, so this is "
             f"where a detection lands at the wrong range.\n")
    #: how far the drone cell sits below the environment cell when the slow-time mean is kept
    nr = {(r["cell"], r["band"]): -r["env_cell_rel_drone_noremoval_db"] for r in lv["frame0"]}
    L.append(f"With the removal off the ablation still carries the environment path, and that path is in "
             f"every H1 frame as well, so the threshold calibrated on the ablation sits at the level of the "
             f"ground return itself. In the same frames the drone cell is "
             f"{abs(max(nr[(c, b)] for c in PRIMARY for b in BANDS)):.1f} to "
             f"{abs(min(nr[(c, b)] for c in PRIMARY for b in BANDS)):.1f} dB below that ground cell "
             f"(section 3), and the rows below say how often anything crossed and where the strongest "
             f"candidate of a crossing frame sat. The threshold column is on the arm's own statistic, so "
             f"the two rows of a cell are not read against each other as levels.\n")
    L.append("| cell | band | removal | threshold T | Pd gated | wrong range | "
             "strongest candidate outside the gate | median range of the strongest candidate | "
             "strongest in the environment cell |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for ck in PRIMARY:
        for band in BANDS:
            for rem in (True, False):
                a = _arm(d, cell=ck, band=band, comp="direct_ghost_env",
                         snr_re_db=CFG["removal_off_snr_db"][band], mode="rt_variation",
                         static_removal=rem)
                if not a:
                    continue
                p = a["pfa"][pfa0]
                L.append(f"| `{ck}` | {BANDS[band]['label_mhz']:.0f} MHz | "
                         f"{'on' if rem else 'off'} | {p['threshold_T']:.4g} | {p['pd_gated']:.3f} | "
                         f"{p['wrong_range_rate']:.3f} | {p['wrong_range_of_detected']:.3f} | "
                         f"{_g(p['strongest_range_median_m'], 4)} m | "
                         f"{_g(p['strongest_in_env_cell_share'])} |")
    L.append("")
    L.append(f"«strongest in the environment cell» counts the strongest candidate of a crossing frame "
             f"within half a range resolution cell of that cell's own environment path range "
             f"({min(x['range_m'] for x in v['env_only_path'].values()):.4f} to "
             f"{max(x['range_m'] for x in v['env_only_path'].values()):.4f} m). "
             f"At {BANDS['bw20']['label_mhz']:.0f} MHz that half-cell is "
             f"{d['bands']['bw20']['range_resolution_m'] / 2:.2f} m wide and the delay search starts at "
             f"zero range, so a noise peak in the first few delay cells is counted in that column as "
             f"well; the `removal on` rows at that band are read with that in mind.\n")

    L.append("## 5. max_depth 2 against max_depth 3\n")
    dm = d["depth_match"]
    L.append("The comparison is read only where the listed path classes really match. Per pose, with the "
             "end-leg classes of this file:\n")
    L.append("| pair | depth-2 paths found unchanged in depth 3 | depth-3 paths not in the depth-2 list, "
             "by end-leg class (median per pose) | read? |")
    L.append("|---|---:|---|---|")
    for r in dm["pairs"]:
        L.append(f"| `{r['d2']}` vs `{r['d3']}` | {r['subset_fraction']:.4f} | {r['new_classes']} | "
                 f"{'yes' if r['read'] else 'written, not read'} |")
    L.append("")
    L.append("The second column counts, at each pose, the depth-3 paths whose `(tau, a)` row is not in "
             "that pose's depth-2 list, and takes the median over the sampled poses. It is a count of "
             "what depth 3 added, not a difference of two per-class medians; the per-class medians "
             "themselves are in `outputs/ghost_detection_0918.json` under `cells.*.class_counts_median`, "
             "counted at every pose of the record.\n")
    L.append("The pair is read where the depth-2 path list is found unchanged inside the depth-3 list, so "
             "the depth-3 arm differs only by the classes depth 2 cannot list. The classes "
             "`runners/jobs_0962` P3 reports as moving between the depths (listed below from that "
             "readout's own ledger) are its first/last labelling absorbing the new `[g,d,d]` and `[d,d,g]` "
             "paths into the one-bounce classes; here those paths are one-ground-leg paths by the same "
             "end-leg rule and are counted as such.\n")
    try:
        led = json.load(open(os.path.join(ROOT, READOUT_LEDGER)))
        for r3 in led["gates"]["0962"]["P3"]:
            dd3 = r3.get("depth3_minus_depth2_db", {})
            L.append(f"- geometry {r3['key']}, the same pair in `outputs/readout_0918.json` "
                     f"(`gates.0962.P3`): depth 3 - depth 2 of "
                     + ", ".join(f"{k} {_g(v, 3)} dB" for k, v in dd3.items()) + ".")
        L.append("")
    except Exception as exc:                                       # noqa: BLE001
        L.append(f"- the readout ledger could not be read for the depth deltas: {exc}\n")
    L.append(f"Figure, max_depth 2 against max_depth 3: `{d['figures']['depth']['path']}`.\n")
    L.append("| pair | band | SNR/RE | Pd depth 2 | Pd depth 3 | difference | mean gated level change |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    for r in dm["pairs"]:
        for band in BANDS:
            for snr in d["_cfg"]["snr_re_db"][band]:
                a2 = _arm(d, cell=r["d2"], band=band, comp="direct_ghost", snr_re_db=snr,
                          mode="rt_variation", static_removal=True)
                a3 = _arm(d, cell=r["d3"], band=band, comp="direct_ghost", snr_re_db=snr,
                          mode="rt_variation", static_removal=True)
                if not (a2 and a3):
                    continue
                L.append(f"| `{r['d2']}` vs `{r['d3']}` | {BANDS[band]['label_mhz']:.0f} MHz | {snr:g} dB | "
                         f"{a2['pfa'][pfa0]['pd_gated']:.3f} | {a3['pfa'][pfa0]['pd_gated']:.3f} | "
                         f"{a3['pfa'][pfa0]['pd_gated'] - a2['pfa'][pfa0]['pd_gated']:+.3f} | "
                         f"{r['level_shift_db'].get(band, float('nan')):+.2f} dB |")
    L.append("")

    L.append("## 6. What this does not decide\n")
    for s in d["not_decidable"]:
        L.append(f"- {s}")
    L.append("")
    L.append("## 7. Figures and inputs\n")
    for k, f_ in d["figures"].items():
        L.append(f"- `{f_['path']}` (min font {_g(f_['min_font_pt'])} pt, overlap warnings "
                 f"{f_['overlap_warnings']}, colour-only series {f_['colour_only_series']})")
    L.append("")
    L.append("| file | sha256 (first 12) |")
    L.append("|---|---|")
    for k, s in sorted(d["_meta"]["inputs"].items()):
        L.append(f"| `{k}` | `{s[:12]}` |")
    L.append("")
    with open(os.path.join(ROOT, path), "w") as f:
        f.write("\n".join(L))


# ----------------------------------------------------------------------------------------------------
#  main
# ----------------------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--doc-from-json", action="store_true")
    ap.add_argument("--figs-only", action="store_true",
                    help="redraw the figures and the document from the stored ledger "
                         "(the noise-free observation is recomputed; no detection frame is re-run)")
    ap.add_argument("--out-json", default=OUT_JSON)
    ap.add_argument("--doc", default=DOC)
    ap.add_argument("--fig-prefix", default=FIG_PREFIX)
    args = ap.parse_args()
    if args.doc_from_json:
        d = json.load(open(os.path.join(ROOT, args.out_json)))
        write_doc(d, args.doc)
        print(f"wrote {args.doc}")
        return
    if args.quick:
        CFG.update(QUICK)
    t_start = time.time()
    if args.figs_only:
        d = json.load(open(os.path.join(ROOT, args.out_json)))
        CFG.update(d["_cfg"])
        cells = {k: load_cell(k) for k in CELLS}
        for k, c in cells.items():
            _CELL_CACHE[k] = c
        p_ref = {}
        for key, v_ in d["p_ref"].items():
            ck, band = key.split("|")
            p_ref[(ck, band)] = v_
        #: ledgers written before these fields existed are backfilled from the cells themselves, so
        #  the document never falls back to a typed constant.
        d["_meta"].update({
            "record_poses": int(cells["A_d2"]["pose"].size),
            "prf_hz": float(CFG["prf_hz"]),
            "record_ms": 1e3 * cells["A_d2"]["pose"].size / CFG["prf_hz"],
            "max_paths_cap": int(cells["A_d2"]["stamps"][0]["max_paths_cap"]),
            "carrier_ghz": float(cells["A_d2"]["fc_hz"]) / 1e9})
        obs = observe(cells, p_ref, CFG["n_frames"])
        d["levels"] = derive_levels(obs, CFG["n_frames"])
        d["observation"] = {"pdp": {f"{k[0]}|{k[1]}": v for k, v in obs["pdp"].items()},
                            "traj": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in obs["traj"].items()}}
        #: everything that is derived from the stored cells alone is rebuilt here, so a correction to
        #  a derived quantity does not need the 41,968 receiver frames run again.  Only
        #  d["detection"] is carried over from the stored ledger.
        d["cells"] = cell_table(cells)
        d["trajectory"] = trajectory_table(cells, CFG["n_frames"])
        d["depth_match"] = depth_table(cells, d["cells"], obs)
        d["verify"] = verify(cells, CFG["n_frames"])
        d["not_decidable"] = not_decidable_list(d["bands"], d["cells"], d["trajectory"], CFG["n_frames"])
        d["figures"] = figures(d, obs, args.fig_prefix)
        #: provenance of the rebuild, so the document's header does not claim the whole ledger came
        #  out of the run that produced the detection frames.
        d["_meta"]["figs_only_rebuild"] = {
            "git_head": _git_head(), "python": sys.version.split()[0], "numpy": np.__version__,
            "command": ('CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 12 '
                        f'/workspace/.venvs/py312/bin/python {GENERATOR} --figs-only'),
            "rebuilt": ["cells", "trajectory", "levels", "observation", "depth_match", "verify",
                        "not_decidable", "figures"],
            "carried_over": ["detection", "p_ref", "bands", "_cfg"],
            "seconds": time.time() - t_start}
        with open(os.path.join(ROOT, args.out_json), "w") as f:
            json.dump(d, f, indent=1, default=_json_default)
        write_doc(d, args.doc)
        print(f"[{time.time() - t_start:6.1f}s] redrew figures and {args.doc}")
        return

    cells = {k: load_cell(k) for k in CELLS}
    for k, c in cells.items():
        _CELL_CACHE[k] = c
    n_frames = CFG["n_frames"]
    S_of = {b: PILOT.build_system(BANDS[b]["system"]) for b in BANDS}

    # reference level per (cell, band) and the fixed-body reference pose
    p_ref = {}
    for ck, c in cells.items():
        for band, S in S_of.items():
            r = reference_power(c, S, n_frames)
            t = symbol_times(S, 0)
            poses = np.unique(np.rint(CFG["prf_hz"] * np.concatenate(
                [symbol_times(S, n) for n in range(n_frames)])).astype(np.int64))
            poses = poses[poses < c["pose"].size]
            pw = np.array([float(np.abs(c["a"][c["off"][p]:c["off"][p + 1]]
                                        [c["leg"][c["off"][p]:c["off"][p + 1]] == 0]).sum()) for p in poses])
            ref_pose = int(poses[int(np.argmin(np.abs(pw - pw.mean())))])
            r["fixed_pose"] = ref_pose
            r["fixed_scale"] = 1.0
            p_ref[(ck, band)] = r
    # rescale the fixed-body arm so its mean power per resource element matches rt_variation
    for (ck, band), r in p_ref.items():
        if ck not in PRIMARY:
            continue
        S = S_of[band]
        acc, n = 0.0, 0
        for k in range(n_frames):
            Hd = frame_channel(cells[ck], S, k, "fixed_body", r["fixed_pose"], 1.0)["H"]["direct"]
            mask = PILOT.base_mask(S)
            acc += float((np.abs(Hd[:, mask]) ** 2).sum())
            n += Hd[:, mask].size
        r["fixed_scale"] = math.sqrt(r["p_ref"] / (acc / n))
        r["fixed_body_p_ref_before_scale"] = acc / n
    print(f"[{time.time() - t_start:6.1f}s] reference levels done", flush=True)

    # ---------------- task list ----------------
    tasks = []
    for band in BANDS:
        for kind, exp, n in (("cal", EXP["h0_noise_cal"], CFG["n_h0_noise"]["cal"]),
                             ("eval", EXP["h0_noise_eval"], CFG["n_h0_noise"]["eval"])):
            step = max(50, n // 8)
            for i0 in range(0, n, step):
                tasks.append({"task": "h0", "kind": "noise", "band": band, "exp": exp,
                              "i0": i0, "i1": min(i0 + step, n), "static_removal": True,
                              "which": ("noise", band, True, kind)})
    for geo, ck in GEO_REF.items():
        for band in BANDS:
            for snr in CFG["snr_re_db"][band]:
                for kind, exp, n in (("cal", EXP["h0_env_cal"], CFG["n_h0_env"]["cal"]),
                                     ("eval", EXP["h0_env_eval"], CFG["n_h0_env"]["eval"])):
                    step = max(50, n // 4)
                    for i0 in range(0, n, step):
                        tasks.append({"task": "h0", "kind": "env", "cell": ck, "band": band, "exp": exp,
                                      "snr_re_db": snr, "p_ref": p_ref[(ck, band)]["p_ref"],
                                      "i0": i0, "i1": min(i0 + step, n), "static_removal": True,
                                      "which": ("env", geo, band, True, snr, kind)})
            for kind, exp, n in (("cal", EXP["h0_env_removal_off_cal"], CFG["n_h0_env"]["cal"]),
                                 ("eval", EXP["h0_env_removal_off_eval"], CFG["n_h0_env"]["eval"])):
                step = max(50, n // 4)
                for i0 in range(0, n, step):
                    tasks.append({"task": "h0", "kind": "env", "cell": ck, "band": band, "exp": exp,
                                  "snr_re_db": CFG["removal_off_snr_db"][band],
                                  "p_ref": p_ref[(ck, band)]["p_ref"],
                                  "i0": i0, "i1": min(i0 + step, n), "static_removal": False,
                                  "which": ("env", geo, band, False,
                                            CFG["removal_off_snr_db"][band], kind)})
    for ck in CELLS:
        for band in BANDS:
            for n in range(n_frames):
                tasks.append({"task": "h1", "cell": ck, "band": band, "frame": n,
                              "compositions": list(COMPOSITIONS), "snr_re_db": CFG["snr_re_db"][band],
                              "n_runs": CFG["n_runs"], "mode": "rt_variation",
                              "static_removal": True, "exp": EXP["h1"],
                              "p_ref": p_ref[(ck, band)]["p_ref"]})
    for ck in PRIMARY:
        for band in BANDS:
            for n in range(n_frames):
                tasks.append({"task": "h1", "cell": ck, "band": band, "frame": n,
                              "compositions": ["direct_ghost"], "snr_re_db": CFG["snr_re_db"][band],
                              "n_runs": CFG["n_runs"], "mode": "fixed_body",
                              "fixed_pose": p_ref[(ck, band)]["fixed_pose"],
                              "fixed_scale": p_ref[(ck, band)]["fixed_scale"],
                              "static_removal": True, "exp": EXP["h1_fixed_body"],
                              "p_ref": p_ref[(ck, band)]["p_ref"]})
                tasks.append({"task": "h1", "cell": ck, "band": band, "frame": n,
                              "compositions": ["direct_ghost_env"],
                              "snr_re_db": [CFG["removal_off_snr_db"][band]],
                              "n_runs": CFG["n_runs"], "mode": "rt_variation",
                              "static_removal": False, "exp": EXP["h1_removal_off"],
                              "p_ref": p_ref[(ck, band)]["p_ref"]})
    tasks.sort(key=lambda s: (s["task"], s.get("cell", ""), s.get("band", "")))
    print(f"[{time.time() - t_start:6.1f}s] {len(tasks)} tasks", flush=True)

    h0_raw, h1_rows = {}, []
    with mp.get_context("fork").Pool(args.workers, maxtasksperchild=40) as pool:
        for i, res in enumerate(pool.imap_unordered(_dispatch, tasks, chunksize=1)):
            sp = res["spec"]
            if sp["task"] == "h0":
                h0_raw.setdefault(tuple(sp["which"]), []).extend(r["frame_stat"] for r in res["rows"])
            else:
                h1_rows.extend(res["rows"])
            if (i + 1) % 50 == 0:
                print(f"[{time.time() - t_start:6.1f}s] {i + 1}/{len(tasks)}", flush=True)
    print(f"[{time.time() - t_start:6.1f}s] receiver frames done", flush=True)

    h0 = {}
    for key, vals in h0_raw.items():
        base, kind = key[:-1], key[-1]
        h0.setdefault(base, {})[kind] = vals
    print(f"[{time.time() - t_start:6.1f}s] h0 sets: {len(h0)}", flush=True)

    env_range_of = {k: geometry(c)["nadir_round_trip_m"] / 2 for k, c in cells.items()}
    det = aggregate(h1_rows, h0, S_of, n_frames, env_range_of)
    obs = observe(cells, p_ref, n_frames)
    print(f"[{time.time() - t_start:6.1f}s] observation done", flush=True)
    ver = verify(cells, n_frames)

    # ---------------- derived tables ----------------
    bands = {}
    for band, S in S_of.items():
        res = PILOT.resolution(S)
        bands[band] = {"label_mhz": BANDS[band]["label_mhz"],
                       "occupied_mhz": PILOT.cfar_cells(S, PILOT.RxCfg())["occupied_span"] * S.scs_hz / 1e6,
                       "range_resolution_m": res["range_m"], "range_sample_m": res["range_bin_m"],
                       "doppler_resolution_hz": res["doppler_hz"], "frame_ms": S.n_sym * S.t_sym * 1e3,
                       "symbol_us": S.t_sym * 1e6, "fft": S.fft, "cp": S.cp, "n_sym": S.n_sym}
    cellinfo = cell_table(cells)
    traj = trajectory_table(cells, n_frames)
    levels = derive_levels(obs, n_frames)
    print(f"[{time.time() - t_start:6.1f}s] levels done", flush=True)

    #: data only - the prose that reads this table lives in write_doc, and the whole block is rebuilt
    #  by --figs-only, so a correction to either does not have to wait for the frames to be run again.
    depth_match = depth_table(cells, cellinfo, obs)

    not_dec = not_decidable_list(bands, cellinfo, traj, n_frames)

    meta = {"generator": GENERATOR, "git_head": _git_head(), "seconds": time.time() - t_start,
            "command": ('CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 '
                        f'/workspace/.venvs/py312/bin/python {GENERATOR} --workers {args.workers}'),
            "workers": args.workers, "quick": bool(args.quick),
            "python": sys.version.split()[0], "numpy": np.__version__,
            "total_listed_paths": int(sum(c["a"].size for c in cells.values())),
            "record_poses": int(cells["A_d2"]["pose"].size),
            "prf_hz": float(CFG["prf_hz"]),
            "record_ms": 1e3 * cells["A_d2"]["pose"].size / CFG["prf_hz"],
            "max_paths_cap": int(cells["A_d2"]["stamps"][0]["max_paths_cap"]),
            "carrier_ghz": float(cells["A_d2"]["fc_hz"]) / 1e9,
            "n_receiver_frames": len(h1_rows) + sum(len(v) for s in h0.values() for v in s.values()),
            "inputs": {}}
    for k, c in cells.items():
        for sh in ("00", "01"):
            meta["inputs"][f"outputs/elev_sweep_shards/{c['stem']}_{sh}.npz"] = _sha(
                f"outputs/elev_sweep_shards/{c['stem']}_{sh}.npz")
            meta["inputs"][f"outputs/path_provenance/{c['stem']}_{sh}_prov.npz"] = _sha(
                f"outputs/path_provenance/{c['stem']}_{sh}_prov.npz")
    for k in ("benchmark/ofdm_receiver_pilot_0917.py", "benchmark/rt_channel_adapter_0918.py",
              "benchmark/elevation_sweep_md.py", ADAPTER_LEDGER, READOUT_LEDGER,
              "runners/jobs_0962_drone_ground_ghost_low_grazing_tripod.txt"):
        meta["inputs"][k] = _sha(k)

    d = {"_meta": meta, "_cfg": {k: v for k, v in CFG.items()}, "bands": bands, "cells": cellinfo,
         "trajectory": traj, "levels": levels, "detection": det, "depth_match": depth_match,
         "verify": ver, "p_ref": {f"{k[0]}|{k[1]}": v for k, v in p_ref.items()},
         "not_decidable": not_dec,
         "observation": {"pdp": {f"{k[0]}|{k[1]}": v for k, v in obs["pdp"].items()},
                         "traj": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in obs["traj"].items()}}}
    d["figures"] = figures(d, obs, args.fig_prefix)
    d["_meta"]["seconds"] = time.time() - t_start
    with open(os.path.join(ROOT, args.out_json), "w") as f:
        json.dump(d, f, indent=1, default=_json_default)
    write_doc(d, args.doc)
    print(f"[{time.time() - t_start:6.1f}s] wrote {args.out_json} and {args.doc}")


if __name__ == "__main__":
    main()
