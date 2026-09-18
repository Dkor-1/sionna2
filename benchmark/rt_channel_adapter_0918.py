# -*- coding: utf-8 -*-
"""
rt_channel_adapter_0918.py - stored ray-traced path lists -> the CPU OFDM receiver's channel (Q0)
=================================================================================================

Q0-a. Read an elevation-sweep shard and its --dump-paths sidecar, turn every listed path into the
    (delay, complex baseband gain) pair that benchmark/ofdm_receiver_pilot_0917.py already accepts, and
    check the conversion: idx/pose alignment, path counts, build-material-geometry match, the stored
    complex field, a CFR channel against the time-domain channel, and what the drone's range bin does
    when every path keeps its own delay instead of being collapsed into the single stored field E.
Q0-b. Compare the pilot's circular-delay channel with a linear-stream channel over six transmission
    conditions (continuous / two bursts x delay inside the cyclic prefix / near its edge / beyond it),
    each repeated with the Doppler set to zero so the intra-symbol-Doppler floor is separated from the
    delay behaviour, and with a fractional-delay pair on top of the six.

Scope of every number this file writes
    numpy simulation on CPU. The ray tracer is not run here: the path lists are read from shards that
    sionna-rt 2.1.0 produced earlier (benchmark/elevation_sweep_md.py). No hardware, no RF measurement.
    3.5 GHz is the working carrier assumption of the stored cells, not a decided band.

Conventions that must not be broken (each was a real trap)
    * `paths.a` in the sidecar is the PASSBAND coefficient (benchmark/report15_probe.py:324). The
      baseband gain the receiver wants is `a * exp(-2j*pi*fc*tau)`, i.e. Sionna's `cir()` value. The
      carrier phase is applied exactly once, here, and nowhere else downstream.
    * `tau` stays ABSOLUTE (round trip from the radar). Nothing in this file subtracts a reference
      delay or re-centres the delay axis: range evaluation reads that absolute value.
    * Poses are never blended. A receiver frame sees one stored pose. No path is matched or
      interpolated across poses anywhere in this file.
    * The receiver is given the channel only. Target bins and path-class labels never cross into it;
      they are used after the receiver returns, in the scoring step, exactly as the pilot does.

Run (CPU only)
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 \
        /workspace/.venvs/py312/bin/python benchmark/rt_channel_adapter_0918.py
    --quick            fewer poses / symbols, for a smoke test
    --doc-from-json    only rewrite the document from the stored ledger
Tests: benchmark/test_rt_channel_adapter_0918.py

Changelog
    2026-09-18, adversarial review of Q0.  Every number of the first run reproduced bit for bit; the
    changes below are guards, scope and naming, not new results.
      1. The carrier read from the arm name is now cross-checked against `src/arm_grammar.py`'s parsed
         `fc` field, so the regex (which mirrors `elevation_sweep_md.carrier_of`) cannot disagree with
         the grammar unnoticed.
      2. The run stops if a cell carries object ids that were missing from that pose's map
         (`n_unknown_id > 0`).  `path_class` files such a path under `no_interaction`, so it would be
         dropped from both the sum and the channel while the sweep's `E` still holds it.
      3. Q0-b rows now carry `delay_search_max_range_m` and `target_in_delay_search_span`.  The
         receiver searches delays 0 .. CP only, so the `beyond_cp` target lies outside the grid and its
         `delay_bias_m` is not a measured bias.  The document says so where the number appears.
      4. `{model}_{tag}_ghost_peak_db` renamed `{model}_{tag}_highest_other_peak_db`: it is
         `receiver_grid`'s `psl_db`, and no ghost path exists in the Q0-b scene.
      5. New `draw_spread` block: the integer-delay rows repeated over several payload/phase draws,
         because the edge waveform residual and the beyond-CP delay estimate move with the draw while
         the field residual does not.  The single-draw rows are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "benchmark")
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))
from arm_grammar import parse as arm_parse, unparse as arm_unparse  # noqa: E402

_spec = importlib.util.spec_from_file_location("ofdm_receiver_pilot_0917",
                                               os.path.join(HERE, "ofdm_receiver_pilot_0917.py"))
PILOT = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = PILOT
_spec.loader.exec_module(PILOT)

C0 = 299792458.0
GENERATOR = "benchmark/rt_channel_adapter_0918.py"
TEST_MODULE = "benchmark/test_rt_channel_adapter_0918.py"
OUT_JSON = "outputs/rt_channel_adapter_0918.json"
DOC = "docs/RT_CHANNEL_ADAPTER_0918.md"
SHARD_DIR = "outputs/elev_sweep_shards"
PROV_DIR = "outputs/path_provenance"

#: The 0960 15 m matched pair the brief starts from: one axis differs (the ground plane), everything
#  else is byte-identical in the arm name.  Both shards of each stem are read.
PAIR = {
    "open_sky": "sionna_p4000000000_swR0D0E0F1_r15_n4096_shell0.75mm_prop1.43mm"
                "_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15",
    "ground":   "sionna_p4000000000_swR0D0E0F1_r15_n4096_envoutdoor01_ground_alt5.4_shell0.75mm"
                "_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15",
}
SHARDS = ("00", "01")

#: Two CP-OFDM configurations.  `bw20` is the pilot's own system (docs/OFDM_PILOT_0917.md section 1).
#  `bw100` keeps the subcarrier spacing and the CP fraction and grows the FFT to the NR 100 MHz shape.
#  `label_mhz` is the nominal channel bandwidth; `occupied_mhz` in the ledger is what is really used.
BANDS = {
    "bw20":  {"label_mhz": 20.0,
              "system": {"fc_hz": 3.5e9, "scs_hz": 30e3, "fft": 1024, "cp": 72, "n_sym": 256,
                         "guard": [206, 205], "dc_null": True}},
    "bw100": {"label_mhz": 100.0,
              "system": {"fc_hz": 3.5e9, "scs_hz": 30e3, "fft": 4096, "cp": 288, "n_sym": 256,
                         "guard": [410, 409], "dc_null": True}},
}
WINDOWS = ("hann", "rect")

#: Pass thresholds, fixed here so section 3 has a stated tolerance rather than a read-off number.
#  `grid_vs_time_peak_range_frac_of_resolution` is a fraction of that band's range resolution.
TOL = {"path_sum_rel_err": 1e-4,
       "grid_vs_time_map_rel": 1e-3,
       "grid_vs_time_peak_range_frac_of_resolution": 0.01,
       "grid_vs_time_peak_power_db": 0.05}

CFG = {
    "seed_root": 20260918,
    "modulation": "qpsk",
    #: Slots of shard 00 whose path list feeds a receiver frame.  Two poses, far apart in the record.
    "rx_slots": [0, 1024],
    "rx_shard": "00",
    #: Q0-a runs noise free: every residual below is a model difference, not a noise draw.
    "q0a_noise_var": 0.0,
    #: Q0-b schedule, in OFDM symbol slots of the bw20 system.
    "q0b": {
        "band": "bw20",
        "n_slots": 512,
        "n_active": 256,
        "clutter_delay_samples": 8,
        "clutter_power_db": 20.0,
        "target_power_db": 0.0,
        "target_doppler_bins": 1.4,
        "delay_cases": {"inside_cp": 24, "near_cp_edge": 70, "beyond_cp": 115},
        "frac_delay_case": {"name": "inside_cp_fractional", "delay_samples": 24.4},
        "snr_db": -30.0,
    },
}
QUICK = {"rx_slots": [0], "q0b": {**CFG["q0b"], "n_slots": 128, "n_active": 64}}


# ----------------------------------------------------------------------------------------------------
#  Reading the stored cells
# ----------------------------------------------------------------------------------------------------
def shard_path(stem: str, shard: str) -> str:
    return os.path.join(ROOT, SHARD_DIR, f"{stem}_{shard}.npz")


def sidecar_path(stem: str, shard: str) -> str:
    return os.path.join(ROOT, PROV_DIR, f"{stem}_{shard}_prov.npz")


def carrier_from_arm(arm: str) -> float:
    """The carrier the cell was baked at, read from the arm name's `_fc<MHz>` tag.  Without that tag the
    sweep's convention carrier applies: benchmark/elevation_sweep_md.py sets `FC = 3.5e9` and its
    `carrier()` writes no tag when the carrier is that value (same rule as its `carrier_of`)."""
    m = re.search(r"_fc(\d+(?:\.\d+)?)", arm)
    return 3.5e9 if not m else float(m.group(1)) * 1e6


def load_cell(stem: str, shard: str) -> dict:
    """Shard + sidecar of one shard, with the per-pose slice boundaries already built."""
    z = np.load(shard_path(stem, shard), allow_pickle=True)
    p = np.load(sidecar_path(stem, shard), allow_pickle=True)
    n_paths = np.asarray(p["n_paths"], np.int64)
    off = np.concatenate([[0], np.cumsum(n_paths)])
    part_names = [str(x) for x in p["part_names"]]
    meta = np.asarray(z["meta"], float)
    return {
        "stem": stem, "shard": shard,
        "idx": np.asarray(z["idx"], np.int64), "E": np.asarray(z["E"], complex),
        "E_dedup": np.asarray(z["E_dedup"], complex), "n_dup": np.asarray(z["n_dup"], np.int64),
        "npaths": np.asarray(z["npaths"], np.int64), "nret": np.asarray(z["nret"], np.int64),
        "n_trunc": [int(x) for x in np.asarray(z["n_trunc"])],
        "solver_build": str(z["solver_build"]), "run_id": str(z["run_id"]),
        "cfg": [float(x) for x in np.asarray(z["cfg"], float)],
        "meta": {"el_deg": meta[0], "shard": meta[1], "nshards": meta[2], "n_poses": meta[3],
                 "prf_hz": meta[4], "seconds": meta[5], "spp": meta[6]},
        "ant": {"pattern": str(z["ant_pattern"]) if "ant_pattern" in z else "iso",
                "cap_db": float(z["ant_cap_db"][0]) if "ant_cap_db" in z else None,
                "aim_offset_deg": float(z["aim_offset_deg"][0]) if "aim_offset_deg" in z else None},
        "pose": np.asarray(p["pose"], np.int64), "slot": np.asarray(p["slot"], np.int64),
        "n_paths": n_paths, "off": off,
        "a": np.asarray(p["a"]), "tau": np.asarray(p["tau"], np.float64),
        "part": np.asarray(p["part"], np.int16), "obj_raw": np.asarray(p["obj_raw"], np.int64),
        "prim_ok": np.asarray(p["prim_ok"], bool), "part_names": part_names,
        "n_unknown_id": int(np.asarray(p["n_unknown_id"])[0]),
        "prov_arm": str(p["arm"]), "prov_el_deg": float(np.asarray(p["el_deg"])[0]),
        "prov_run_id": str(p["run_id"]), "prov_solver_build": str(p["solver_build"]),
    }


#: path_class - what a listed path touched, read from the sidecar `part` matrix and `part_names`
#  (names that start with `env_` are the environment; every other name is a drone part).
#  -1 in `part` is "no interaction at that depth", -2 is "object id missing from that pose's map".
CLASSES = ("drone_only", "env_only", "mixed", "no_interaction")


def path_class(part_slice: np.ndarray, part_names: list) -> np.ndarray:
    """Per-path class index into CLASSES for one pose's [depth, path] slice of `part`."""
    is_env_name = np.array([n.startswith("env_") for n in part_names], bool)
    hit = part_slice >= 0
    idx = np.where(hit, part_slice, 0)
    env = hit & is_env_name[idx]
    drone = hit & ~is_env_name[idx]
    any_env, any_drone = env.any(axis=0), drone.any(axis=0)
    out = np.full(part_slice.shape[1], CLASSES.index("no_interaction"), np.int8)
    out[any_drone & ~any_env] = CLASSES.index("drone_only")
    out[any_env & ~any_drone] = CLASSES.index("env_only")
    out[any_drone & any_env] = CLASSES.index("mixed")
    return out


def pose_paths(cell: dict, slot: int) -> dict:
    """One pose's path list, with the carrier phase applied exactly once.

    `amp` is the baseband gain a*exp(-2j*pi*fc*tau) (Sionna `cir()`); `tau_s` is the absolute round-trip
    delay, untouched.  `unknown_part` counts paths whose object id was missing from that pose's map.
    """
    t = int(np.flatnonzero(cell["slot"] == slot)[0])
    s, e = int(cell["off"][t]), int(cell["off"][t + 1])
    a = cell["a"][s:e].astype(np.complex128)
    tau = cell["tau"][s:e]
    part = cell["part"][:, s:e]
    cls = path_class(part, cell["part_names"])
    fc = cell["fc_hz"] if "fc_hz" in cell else 3.5e9
    return {"slot": slot, "pose": int(cell["pose"][t]), "a": a, "tau_s": tau,
            "amp": a * np.exp(-2j * np.pi * fc * tau), "cls": cls,
            "hit": cls != CLASSES.index("no_interaction"),
            "unknown_part": int((part == -2).any(axis=0).sum())}


def class_mask(pp: dict, name: str) -> np.ndarray:
    """Which listed paths a named channel configuration keeps.  `all` = every path with an interaction."""
    c = pp["cls"]
    if name == "all":
        return pp["hit"]
    if name == "drone":
        return c == CLASSES.index("drone_only")
    if name == "drone_mixed":
        return (c == CLASSES.index("drone_only")) | (c == CLASSES.index("mixed"))
    if name == "env":
        return c == CLASSES.index("env_only")
    raise ValueError(name)


# ----------------------------------------------------------------------------------------------------
#  Channels built from a path list (every path static: the sidecar stores no Doppler)
# ----------------------------------------------------------------------------------------------------
def cfr(S, amp: np.ndarray, tau: np.ndarray) -> np.ndarray:
    """Channel frequency response on the centred subcarrier grid, the convention channel_grid uses:
    H[k] = sum_p amp_p exp(-2j*pi*(k - N//2)*scs*tau_p).  The carrier phase is already inside amp."""
    nc = np.arange(S.fft) - S.fft // 2
    return np.exp(-2j * np.pi * np.outer(nc * S.scs_hz, tau)) @ amp


def channel_grid_static(X: np.ndarray, S, amp: np.ndarray, tau: np.ndarray,
                        noise_var: float = 0.0, rng=None) -> np.ndarray:
    """Y = H X for a static path list; identical to PILOT.channel_grid with every f_hz = 0."""
    Y = X * cfr(S, amp, tau)[None, :]
    if noise_var > 0:
        Y = Y + np.sqrt(noise_var / 2) * (rng.standard_normal(Y.shape) + 1j * rng.standard_normal(Y.shape))
    return Y


def static_frame_ramp(L: int, fs: float, amp: np.ndarray, tau: np.ndarray, block: int = 512) -> np.ndarray:
    """sum_p amp_p exp(-2j*pi*f*tau_p) on the numpy fftfreq(L, 1/fs) grid, as one blocked matrix product.

    The fftfreq grid is k = 0..L/2-1 then -L/2..-1, so inside a block of `block` consecutive entries the
    integer k rises by one whenever `block` divides L/2.  That makes the exponential separable,
    exp(-2j*pi*k*n_p/L) = exp(-2j*pi*k0*n_p/L) * exp(-2j*pi*r*n_p/L), and the sum over paths becomes a
    single zgemm.  Falls back to a chunked exponential when the block does not divide L/2.
    """
    n = tau * fs
    if L % (2 * block) == 0:
        k = np.fft.fftfreq(L) * L
        k0 = k[::block]
        A = np.exp(-2j * np.pi * np.outer(k0, n / L)) * amp[None, :]
        Cm = np.exp(-2j * np.pi * np.outer(n / L, np.arange(block)))
        return (A @ Cm).ravel()
    f = np.fft.fftfreq(L, d=1.0 / fs)
    out = np.empty(L, complex)
    for s in range(0, L, 16384):
        out[s:s + 16384] = np.exp(-2j * np.pi * np.outer(f[s:s + 16384], tau)) @ amp
    return out


def channel_time_static(tx: np.ndarray, S, amp: np.ndarray, tau: np.ndarray,
                        noise_var: float = 0.0, rng=None) -> np.ndarray:
    """PILOT.channel_time for a path list whose every f_hz is 0, computed without a python path loop.
    benchmark/test_rt_channel_adapter_0918.py checks it against PILOT.channel_time directly."""
    L = len(tx)
    rx = np.fft.ifft(np.fft.fft(tx) * static_frame_ramp(L, S.fs, amp, tau))
    if noise_var > 0:
        rx = rx + np.sqrt(noise_var / 2) * (rng.standard_normal(L) + 1j * rng.standard_normal(L))
    return rx


# ----------------------------------------------------------------------------------------------------
#  Q0-a: the checks
# ----------------------------------------------------------------------------------------------------
def check_alignment(cell: dict) -> dict:
    """idx <-> sidecar pose, the interleave rule, path counts, and the sidecar's own labels."""
    slot, pose, idx = cell["slot"], cell["pose"], cell["idx"]
    sh, nsh = int(cell["meta"]["shard"]), int(cell["meta"]["nshards"])
    interleave_ok = bool(np.array_equal(idx, sh + nsh * np.arange(idx.size)))
    return {
        "n_poses_shard": int(idx.size), "n_poses_dumped": int(slot.size),
        "slot_strictly_increasing": bool(np.all(np.diff(slot) > 0)),
        "slot_in_range": bool(slot.min() >= 0 and slot.max() < idx.size),
        "pose_equals_idx_at_slot": bool(np.array_equal(idx[slot], pose)),
        "idx_follows_interleave_rule": interleave_ok,
        "nret_equals_sidecar_n_paths": bool(np.array_equal(cell["nret"][slot], cell["n_paths"])),
        "npaths_equals_paths_with_interaction": None,   # filled by check_field_sum (same pass)
        "prov_arm_matches_stem": bool(cell["prov_arm"] == cell["stem"].rsplit("_el", 1)[0]),
        "prov_el_matches_meta": bool(abs(cell["prov_el_deg"] - cell["meta"]["el_deg"]) < 1e-9),
        "prov_run_id_matches_shard": bool(cell["prov_run_id"] == cell["run_id"]),
        "prov_solver_build_matches_shard": bool(cell["prov_solver_build"] == cell["solver_build"]),
        "n_unknown_id": cell["n_unknown_id"],
        "prim_ok_all": bool(cell["prim_ok"].all()),
        "n_trunc": cell["n_trunc"][0], "max_paths_cap": cell["n_trunc"][1],
    }


def check_field_sum(cell: dict, fc: float) -> dict:
    """path_sum_rel_err - |sum over listed paths with any interaction of a*exp(-2j*pi*fc*tau) - E| / |E|,
    per dumped pose.  Also the same sum against the stored E_dedup, and the per-class path counts.

    The adapter repeats the arithmetic the sweep used (same stored numbers, same order), so this number
    can be exactly zero.  `path_sum_rel_err_fsum` therefore adds an order-independent reference,
    `math.fsum` over the real and imaginary parts, and `cancellation_sum_abs_over_abs_E` reports
    sum |a| / |E| so the reader can see how much cancellation the sum carries."""
    rel = np.empty(cell["slot"].size)
    rel_fs = np.empty(cell["slot"].size)
    canc = np.empty(cell["slot"].size)
    rel_dd = np.empty(cell["slot"].size)
    n_hit = np.empty(cell["slot"].size, np.int64)
    cls_count = np.zeros((cell["slot"].size, len(CLASSES)), np.int64)
    cls_incoh = np.zeros((cell["slot"].size, len(CLASSES)))
    tau_min = np.empty(cell["slot"].size)
    tau_max = np.empty(cell["slot"].size)
    for t in range(cell["slot"].size):
        s, e = int(cell["off"][t]), int(cell["off"][t + 1])
        cls = path_class(cell["part"][:, s:e], cell["part_names"])
        hit = cls != CLASSES.index("no_interaction")
        amp = cell["a"][s:e][hit].astype(np.complex128) * np.exp(-2j * np.pi * fc * cell["tau"][s:e][hit])
        Es, Et = amp.sum(), cell["E"][cell["slot"][t]]
        rel[t] = abs(Es - Et) / max(abs(Et), 1e-300)
        rel_fs[t] = abs(complex(math.fsum(amp.real), math.fsum(amp.imag)) - Et) / max(abs(Et), 1e-300)
        canc[t] = float(np.abs(amp).sum() / max(abs(Et), 1e-300))
        rel_dd[t] = abs(Es - cell["E_dedup"][cell["slot"][t]]) / max(abs(cell["E_dedup"][cell["slot"][t]]), 1e-300)
        n_hit[t] = int(hit.sum())
        for c in range(len(CLASSES)):
            m = cls == c
            cls_count[t, c] = int(m.sum())
            if m.any():
                a_c = cell["a"][s:e][m].astype(np.complex128)
                cls_incoh[t, c] = float((a_c.real ** 2 + a_c.imag ** 2).sum())
        tau_min[t], tau_max[t] = cell["tau"][s:e][hit].min(), cell["tau"][s:e][hit].max()
    tot = cls_incoh.sum(axis=1)
    share = np.where(tot[:, None] > 0, cls_incoh / np.maximum(tot[:, None], 1e-300), 0.0)
    return {
        "n_poses": int(cell["slot"].size),
        "path_sum_rel_err_max": float(rel.max()), "path_sum_rel_err_median": float(np.median(rel)),
        "path_sum_rel_err_fsum_max": float(rel_fs.max()),
        "path_sum_rel_err_fsum_median": float(np.median(rel_fs)),
        "path_sum_bit_identical_fraction": float((rel == 0.0).mean()),
        "cancellation_sum_abs_over_abs_E_max": float(canc.max()),
        "path_sum_rel_err_vs_E_dedup_max": float(rel_dd.max()),
        "n_dup_total": int(cell["n_dup"][cell["slot"]].sum()),
        "npaths_equals_paths_with_interaction": bool(np.array_equal(cell["npaths"][cell["slot"]], n_hit)),
        "class_count_median": {CLASSES[c]: float(np.median(cls_count[:, c])) for c in range(len(CLASSES))},
        "class_share_incoh_db": {CLASSES[c]: (float(10 * np.log10(max(np.median(share[:, c]), 1e-300)))
                                              if cls_count[:, c].any() else None)
                                 for c in range(len(CLASSES))},
        "range_m_min": float(tau_min.min() * C0 / 2), "range_m_max": float(tau_max.max() * C0 / 2),
        "delay_spread_ns_median": float(np.median((tau_max - tau_min)) * 1e9),
    }


def check_pair_geometry(cells: dict) -> dict:
    """build / material / geometry match: the arm names are re-read with src/arm_grammar.py and the two
    scenes must differ in the environment fields only; the stored stamps must agree everywhere."""
    fields, warn = {}, []
    for scene, stem in PAIR.items():
        arm = stem.rsplit("_el", 1)[0]
        f = arm_parse(arm)
        assert arm_unparse(f) == arm, f"arm grammar round trip failed for {arm}"
        fields[scene] = {k: v for k, v in f.items() if v not in (None, "", False)}
    a, b = fields["open_sky"], fields["ground"]
    diff = sorted(set(a) ^ set(b)) + sorted(k for k in set(a) & set(b) if a[k] != b[k])
    stamps = {}
    for scene in PAIR:
        for sh in SHARDS:
            c = cells[(scene, sh)]
            stamps[f"{scene}_{sh}"] = {
                "solver_build": c["solver_build"], "run_id": c["run_id"], "cfg": c["cfg"],
                "el_deg": c["meta"]["el_deg"], "n_poses": c["meta"]["n_poses"],
                "prf_hz": c["meta"]["prf_hz"], "spp": c["meta"]["spp"], "ant": c["ant"],
            }
    base = stamps[f"open_sky_{SHARDS[0]}"]
    for k, v in stamps.items():
        for key in ("solver_build", "cfg", "el_deg", "n_poses", "prf_hz", "spp", "ant"):
            if v[key] != base[key]:
                warn.append(f"{k}.{key} differs from open_sky_{SHARDS[0]}")
    return {"arm_fields": fields, "fields_that_differ": diff,
            "fields_that_differ_are_environment_only": diff == ["env", "env_alt"],
            "stamps": stamps, "stamp_mismatches": warn}


def receiver_on_paths(S, amp: np.ndarray, tau: np.ndarray, window: str,
                      model: str, seed: int, noise_var: float = 0.0) -> dict:
    """One receiver frame on a static path list.  static_removal is OFF: the sidecar carries no Doppler,
    so every RT path here is at zero Doppler and slow-time mean removal would delete the whole channel."""
    rng = np.random.default_rng(seed)
    mask = PILOT.base_mask(S)
    X = PILOT.payload(rng, S, mask, CFG["modulation"], S.n_sym)
    if model == "grid":
        Y = channel_grid_static(X, S, amp, tau, noise_var, rng)
    elif model == "time":
        rx = channel_time_static(PILOT.tx_time(X, S), S, amp, tau, noise_var, rng)
        Y = PILOT.demod(rx, S, S.n_sym)
    else:
        raise ValueError(model)
    cfgrx = PILOT.RxCfg(window=window, static_removal=False)
    out = PILOT.receiver_grid(Y, X, mask, S, cfgrx, return_map=True)
    return out


def _bin_power(out: dict, S, tau_s: float) -> dict:
    """Map power, in dB relative to the map maximum, in the delay cell nearest an absolute delay, taken
    over every Doppler row.  Read after the receiver returns; it is never given to the receiver."""
    P, tau_axis = out["map"]["P"], out["map"]["tau_axis"]
    j = int(np.argmin(np.abs(tau_axis - tau_s)))
    col = P[:, j]
    return {"cell_index": j, "cell_tau_ns": float(tau_axis[j] * 1e9),
            "cell_range_m": float(tau_axis[j] * C0 / 2),
            "cell_max_db": float(10 * np.log10(max(col.max(), 1e-300))),
            "map_max_db": float(10 * np.log10(max(P.max(), 1e-300)))}


def q0a(cells: dict, quick: bool) -> dict:
    fc = float(BANDS["bw20"]["system"]["fc_hz"])
    assert all(float(b["system"]["fc_hz"]) == fc for b in BANDS.values()), "the bands must share a carrier"
    #: The carrier that turns the sidecar's passband `a` into a baseband gain has to be the carrier the
    #  cell was baked at.  Pointing PAIR at an `_fc3450` cell without this guard would silently put the
    #  wrong phase on every path, so the run stops instead.
    carrier = {}
    per_cell, align, geom = {}, {}, check_pair_geometry(cells)
    for scene, stem in PAIR.items():
        f_arm = carrier_from_arm(stem)
        #: The tag rule above mirrors `elevation_sweep_md.carrier_of`, which is what the sweep itself
        #  reads.  Cross-check it against the grammar so the two readings cannot part company: the
        #  grammar owns the arm name (src/arm_grammar.py), the regex owns the merge-side convention.
        f_gram = geom["arm_fields"][scene].get("fc")
        f_gram = fc if f_gram is None else float(f_gram) * 1e6
        if abs(f_gram - f_arm) > 1.0:
            raise SystemExit(f"carrier read disagrees for {stem}: the `_fc` tag says {f_arm / 1e9:g} GHz "
                             f"while src/arm_grammar.py parses {f_gram / 1e9:g} GHz")
        if abs(f_arm - fc) > 1.0:
            raise SystemExit(f"carrier mismatch: {stem} was baked at {f_arm / 1e9:g} GHz while the "
                             f"receiver bands use {fc / 1e9:g} GHz")
        carrier[scene] = {"fc_hz": f_arm, "fc_hz_from_arm_grammar": f_gram,
                          "source": ("the `_fc<MHz>` tag of the arm name" if "_fc" in stem else
                                     "no `_fc` tag in the arm name, so the sweep's convention carrier "
                                     "applies (benchmark/elevation_sweep_md.py, FC = 3.5e9)")}
    #: ⛔A path whose object id was missing from that pose's map is stored as `part = -2`, and
    #  `path_class` files it under `no_interaction` - so it would be dropped from the sum and from the
    #  channel while the sweep's `E` (whose mask is `O != NO_OBJ`) still holds it.  Refuse such a cell
    #  rather than report a quiet difference.
    for key, c in cells.items():
        if c["n_unknown_id"]:
            raise SystemExit(f"{key}: {c['n_unknown_id']} path interactions carry an object id that was "
                             "missing from that pose's map (`part == -2`). This adapter's path classes "
                             "cannot place them, so it would drop them from the channel while the "
                             "sweep's stored E keeps them. Fix the sidecar before reading this cell.")
    for (scene, sh), c in cells.items():
        c["fc_hz"] = fc
        al = check_alignment(c)
        fs = check_field_sum(c, fc)
        al["npaths_equals_paths_with_interaction"] = fs.pop("npaths_equals_paths_with_interaction")
        align[f"{scene}_{sh}"] = al
        per_cell[f"{scene}_{sh}"] = fs

    rows, bins = [], []
    slots = CFG["rx_slots"] if not quick else QUICK["rx_slots"]
    for band, bd in BANDS.items():
        S = PILOT.build_system(bd["system"])
        res = PILOT.resolution(S)
        for scene in PAIR:
            c = cells[(scene, CFG["rx_shard"])]
            for slot in slots:
                pp = pose_paths(c, slot)
                sets = ["all"] if scene == "open_sky" else ["all", "drone", "drone_mixed", "env"]
                for cset in sets:
                    m = class_mask(pp, cset)
                    if not m.any():
                        continue
                    amp, tau = pp["amp"][m], pp["tau_s"][m]
                    for window in WINDOWS:
                        outs = {}
                        for model in ("grid", "time"):
                            outs[model] = receiver_on_paths(S, amp, tau, window, model,
                                                            seed=CFG["seed_root"] + slot)
                        Pg, Pt = outs["grid"]["map"]["P"], outs["time"]["map"]["P"]
                        num = float(np.sqrt(((Pg - Pt) ** 2).sum()))
                        den = float(np.sqrt((Pg ** 2).sum()))
                        sg, st = outs["grid"]["strongest"], outs["time"]["strongest"]
                        rows.append({
                            "band": band, "occupied_mhz": res_span_mhz(S), "scene": scene,
                            "pose": pp["pose"], "slot": slot, "class_set": cset, "window": window,
                            "n_paths": int(m.sum()),
                            "grid_vs_time_map_rel": num / max(den, 1e-300),
                            "grid_vs_time_peak_range_m": abs(C0 * (sg["tau_s"] - st["tau_s"]) / 2),
                            "grid_vs_time_peak_doppler_hz": abs(sg["f_hz"] - st["f_hz"]),
                            "grid_vs_time_peak_power_db": abs(10 * np.log10(sg["P"] / st["P"])),
                            "grid_peak_range_m": C0 * sg["tau_s"] / 2,
                            "grid_peak_doppler_hz": sg["f_hz"],
                            "grid_psl_db": outs["grid"]["psl_db"],
                            "range_resolution_m": res["range_m"], "range_sample_m": res["range_bin_m"],
                        })
                # per-path delays kept vs collapsed into the stored field E
                if "hann" in WINDOWS:
                    m = class_mask(pp, "all")
                    amp, tau = pp["amp"][m], pp["tau_s"][m]
                    E = complex(amp.sum())
                    tau_nom = 2.0 * float(cells[(scene, CFG["rx_shard"])]["cfg"][0]) / C0
                    kept = receiver_on_paths(S, amp, tau, "hann", "grid",
                                             seed=CFG["seed_root"] + slot)
                    coll = receiver_on_paths(S, np.array([E]), np.array([tau_nom]), "hann", "grid",
                                             seed=CFG["seed_root"] + slot)
                    bk, bc = _bin_power(kept, S, tau_nom), _bin_power(coll, S, tau_nom)
                    env_tau = None
                    me = class_mask(pp, "env")
                    if me.any():
                        env_tau = float(np.median(pp["tau_s"][me]))
                    bins.append({
                        "band": band, "occupied_mhz": res_span_mhz(S), "scene": scene,
                        "pose": pp["pose"], "n_paths": int(m.sum()),
                        "nominal_range_m": tau_nom * C0 / 2,
                        "drone_bin_kept_db": bk["cell_max_db"] - bk["map_max_db"],
                        "drone_bin_collapsed_db": bc["cell_max_db"] - bc["map_max_db"],
                        "drone_bin_power_delta_db": (bc["cell_max_db"] - bc["map_max_db"])
                                                    - (bk["cell_max_db"] - bk["map_max_db"]),
                        "kept_peak_range_m": C0 * kept["strongest"]["tau_s"] / 2,
                        "collapsed_peak_range_m": C0 * coll["strongest"]["tau_s"] / 2,
                        "kept_psl_db": kept["psl_db"], "collapsed_psl_db": coll["psl_db"],
                        "env_only_range_m": (env_tau * C0 / 2) if env_tau else None,
                        "env_bin_kept_db": ((_bin_power(kept, S, env_tau)["cell_max_db"]
                                             - bk["map_max_db"]) if env_tau else None),
                        "env_bin_collapsed_db": ((_bin_power(coll, S, env_tau)["cell_max_db"]
                                                  - bc["map_max_db"]) if env_tau else None),
                    })
    for r in rows:
        r["within_tolerance"] = bool(
            r["grid_vs_time_map_rel"] < TOL["grid_vs_time_map_rel"]
            and r["grid_vs_time_peak_range_m"]
            < TOL["grid_vs_time_peak_range_frac_of_resolution"] * r["range_resolution_m"]
            and r["grid_vs_time_peak_power_db"] < TOL["grid_vs_time_peak_power_db"])
    worst = {k: float(max(r[k] for r in rows)) for k in
             ("grid_vs_time_map_rel", "grid_vs_time_peak_range_m", "grid_vs_time_peak_doppler_hz",
              "grid_vs_time_peak_power_db")}
    return {"alignment": align, "field_sum": per_cell, "pair_geometry": geom, "carrier": carrier,
            "tolerance": TOL, "grid_vs_time_worst": worst,
            "grid_vs_time_all_within_tolerance": bool(all(r["within_tolerance"] for r in rows)),
            "path_sum_all_within_tolerance": bool(all(v["path_sum_rel_err_max"] < TOL["path_sum_rel_err"]
                                                      for v in per_cell.values())),
            "receiver_rows": rows, "range_bin_rows": bins,
            "static_removal": False, "noise_var": CFG["q0a_noise_var"],
            "rx_slots": slots, "rx_shard": CFG["rx_shard"]}


def res_span_mhz(S) -> float:
    return PILOT.cfar_cells(S, PILOT.RxCfg())["occupied_span"] * S.scs_hz / 1e6


# ----------------------------------------------------------------------------------------------------
#  Q0-b: finite bursts, circular-delay channel against a linear stream
# ----------------------------------------------------------------------------------------------------
def schedule(kind: str, n_slots: int, n_active: int) -> np.ndarray:
    """Transmitted slot indices.  `continuous` puts every active symbol at the front of the span;
    `two_bursts` splits them into two equal blocks at the two ends of the same span."""
    if kind == "continuous":
        return np.arange(n_active)
    if kind == "two_bursts":
        h = n_active // 2
        return np.concatenate([np.arange(h), np.arange(n_slots - h, n_slots)])
    raise ValueError(kind)


def build_stream(X: np.ndarray, S, slots: np.ndarray, n_slots: int) -> np.ndarray:
    """Zero everywhere except the transmitted slots; symbol m of X goes into the m-th transmitted slot."""
    Lb = S.fft + S.cp
    x = np.zeros(n_slots * Lb, complex)
    blocks = PILOT.tx_time(X, S).reshape(X.shape[0], Lb)
    for m, s in enumerate(slots):
        x[s * Lb:(s + 1) * Lb] = blocks[m]
    return x


def linear_stream_rx(x: np.ndarray, S, paths: list, tail: int) -> np.ndarray:
    """Linear (non-circular) channel on the whole stream: every path is an integer sample shift with a
    zero fill, then a Doppler phase on the ABSOLUTE sample index.  Nothing wraps."""
    L = len(x) + tail
    xp = np.concatenate([x, np.zeros(tail, complex)])
    n = np.arange(L)
    y = np.zeros(L, complex)
    for p in paths:
        d = int(round(p["tau_s"] * S.fs))
        assert abs(p["tau_s"] * S.fs - d) < 1e-9, "linear_stream_rx takes integer sample delays"
        sh = np.zeros(L, complex)
        sh[d:] = xp[:L - d]
        y += p["amp"] * sh * (np.exp(2j * np.pi * p["f_hz"] * n / S.fs) if p["f_hz"] else 1.0)
    return y


def circular_block_rx(x: np.ndarray, S, paths: list, slots: np.ndarray, n_slots: int,
                      tail: int) -> np.ndarray:
    """The present model: PILOT.channel_time applied to each transmitted block, with the Doppler phase
    continued from the block's absolute start sample.  Delays wrap inside the block."""
    Lb = S.fft + S.cp
    L = n_slots * Lb + tail
    y = np.zeros(L, complex)
    runs, start = [], 0
    for i in range(1, len(slots) + 1):
        if i == len(slots) or slots[i] != slots[i - 1] + 1:
            runs.append((int(slots[start]), int(slots[i - 1]) + 1))
            start = i
    for s0, s1 in runs:
        n0, n1 = s0 * Lb, s1 * Lb
        blk = x[n0:n1]
        n = np.arange(n0, n1)
        for p in paths:
            d = int(round(p["tau_s"] * S.fs))
            rolled = np.roll(blk, d)
            y[n0:n1] += p["amp"] * rolled * (np.exp(2j * np.pi * p["f_hz"] * n / S.fs) if p["f_hz"] else 1.0)
    return y


def collect_windows(y: np.ndarray, S, slots: np.ndarray) -> np.ndarray:
    """Demodulate the transmitted slots in schedule order (the receiver's uniform-stride assumption)."""
    Lb = S.fft + S.cp
    blk = np.stack([y[s * Lb + S.cp:(s + 1) * Lb] for s in slots])
    return np.fft.fftshift(np.fft.fft(blk, axis=1), axes=1) / np.sqrt(S.fft)


def delay_search_max_range_m(S, cfg=None) -> float:
    """delay_search_max_range_m - the largest round-trip range the receiver's delay grid can hold.
    `receiver_grid` searches `pad_delay * S.cp + 1` padded cells of width 1/(pad_delay*fft*scs), so the
    last cell sits at exactly the CP duration: a path later than that has no cell of its own."""
    cfg = cfg or PILOT.RxCfg()
    D = cfg.pad_delay * S.fft
    return float((cfg.pad_delay * S.cp) / (D * S.scs_hz) * C0 / 2)


def usable_fft_fraction(S, paths: list, slots: np.ndarray) -> float:
    """usable_fft_fraction - over the transmitted FFT windows, the mean fraction of window samples that
    the largest-delay path still draws from that symbol's own cyclic extension: 1 while that delay is
    inside the CP, (N - (d - CP))/N once it is past it."""
    d = max(int(round(p["tau_s"] * S.fs)) for p in paths)
    return float(max(0.0, min(1.0, (S.fft - max(0, d - S.cp)) / S.fft)))


def q0b(quick: bool) -> dict:
    cfg = QUICK["q0b"] if quick else CFG["q0b"]
    bd = BANDS[cfg["band"]]
    S = PILOT.build_system({**bd["system"], "n_sym": cfg["n_active"]})
    Lb = S.fft + S.cp
    tail = 4 * Lb
    n_slots, n_active = cfg["n_slots"], cfg["n_active"]
    f_bin = 1.0 / (n_active * S.t_sym)
    f_d = cfg["target_doppler_bins"] * f_bin
    rng0 = np.random.default_rng(CFG["seed_root"])
    mask = PILOT.base_mask(S)
    X = PILOT.payload(rng0, S, mask, CFG["modulation"], n_active)
    phase_c, phase_t = rng0.uniform(0, 2 * np.pi), rng0.uniform(0, 2 * np.pi)
    noise = (np.random.default_rng(CFG["seed_root"] + 77)
             .standard_normal(n_slots * Lb + tail)
             + 1j * np.random.default_rng(CFG["seed_root"] + 78).standard_normal(n_slots * Lb + tail))

    cases = dict(cfg["delay_cases"])
    frac = cfg["frac_delay_case"]
    rows = []
    for kind in ("continuous", "two_bursts"):
        slots = schedule(kind, n_slots, n_active)
        x = build_stream(X, S, slots, n_slots)
        for cname, dsmp in list(cases.items()) + [(frac["name"], frac["delay_samples"])]:
            paths = [
                {"tau_s": cfg["clutter_delay_samples"] / S.fs, "f_hz": 0.0,
                 "amp": 10 ** (cfg["clutter_power_db"] / 20) * np.exp(1j * phase_c)},
                {"tau_s": dsmp / S.fs, "f_hz": f_d,
                 "amp": 10 ** (cfg["target_power_db"] / 20) * np.exp(1j * phase_t)},
            ]
            integer = abs(dsmp - round(dsmp)) < 1e-9
            if integer:
                y_lin = linear_stream_rx(x, S, paths, tail)
                y_cir = circular_block_rx(x, S, paths, slots, n_slots, tail)
                pad_floor = None
            else:
                y_lin, pad_floor = _linear_fractional(x, S, paths, tail)
                y_cir = _circular_fractional(x, S, paths, slots, n_slots, tail)
            # waveform residual, split at the block edges
            edge = np.zeros(len(y_lin), bool)
            w = S.cp + int(np.ceil(dsmp))
            runs, start = [], 0
            for i in range(1, len(slots) + 1):
                if i == len(slots) or slots[i] != slots[i - 1] + 1:
                    runs.append((int(slots[start]), int(slots[i - 1]) + 1))
                    start = i
            for s0, s1 in runs:
                edge[s0 * Lb:s0 * Lb + w] = True
                edge[s1 * Lb - w:s1 * Lb + w] = True
            inside = np.zeros(len(y_lin), bool)
            for s0, s1 in runs:
                inside[s0 * Lb:s1 * Lb] = True
            inside &= ~edge

            def _res_db(m):
                num = float((np.abs(y_cir[m] - y_lin[m]) ** 2).sum())
                den = float((np.abs(y_lin[m]) ** 2).sum())
                return float(10 * np.log10(max(num, 1e-300) / max(den, 1e-300)))

            row = {"schedule": kind, "delay_case": cname, "delay_samples": float(dsmp),
                   "delay_vs_cp": float(dsmp / S.cp), "target_range_m": float(dsmp / S.fs * C0 / 2),
                   "target_doppler_hz": float(f_d), "doppler_bin_hz": float(f_bin),
                   "n_active_symbols": int(n_active), "slot_grid": int(n_slots),
                   "transmit_span_slots": int(slots[-1] - slots[0] + 1),
                   "transmit_span_s": float((slots[-1] - slots[0] + 1) * Lb / S.fs),
                   "usable_fft_fraction": usable_fft_fraction(S, paths, slots),
                   #: The receiver's delay grid stops at the CP. Outside it the strongest-peak delay
                   #  cannot land on the target at all, so `*_delay_bias_m` of such a row is where a
                   #  spurious peak fell, not a measured bias.
                   "delay_search_max_range_m": delay_search_max_range_m(S),
                   "target_in_delay_search_span": bool(dsmp / S.fs * C0 / 2
                                                       <= delay_search_max_range_m(S)),
                   "waveform_residual_edge_db": _res_db(edge),
                   "waveform_residual_inside_db": _res_db(inside),
                   "linear_pad_floor_db": pad_floor}
            #: The noise level is measured, not asserted: `snr_waveform_db` is the mean received sample
            #  power over the transmitted slots divided by the noise variance that `snr_db` sets.
            txm = np.zeros(len(y_lin), bool)
            for s0, s1 in runs:
                txm[s0 * Lb:s1 * Lb] = True
            row["noise_var"] = float(10 ** (-cfg["snr_db"] / 10))
            row["snr_waveform_db"] = float(10 * np.log10(float((np.abs(y_lin[txm]) ** 2).mean())
                                                         / row["noise_var"]))
            act = np.flatnonzero(mask)
            nc = (np.arange(S.fft) - S.fft // 2)[act]
            #: analytic reference for field_residual_db: the response of the same paths at each
            #  transmitted window, with the Doppler phase at that window's centre in ABSOLUTE time.
            tm = (slots * Lb + S.cp + (S.fft - 1) / 2) / S.fs
            ref = np.zeros((len(slots), act.size), complex)
            for p in paths:
                ref += p["amp"] * np.exp(2j * np.pi * p["f_hz"] * tm)[:, None] \
                    * np.exp(-2j * np.pi * nc * S.scs_hz * p["tau_s"])[None, :]
            def _fres(y, ref_):
                """field_residual_db for one waveform against one analytic per-symbol response."""
                Yw = collect_windows(y, S, slots)
                num = float((np.abs(Yw[:, act] / X[:, act] - ref_) ** 2).sum())
                return float(10 * np.log10(max(num, 1e-300) / float((np.abs(ref_) ** 2).sum())))

            #: Doppler-zero control - the same delays, the same payload, f_hz = 0.  `ref` holds one
            #  Doppler phase per symbol (the window centre) while both channels move that phase inside
            #  the symbol; that intra-symbol term is common to the two models and sets the residual
            #  floor.  With the Doppler taken out, what is left is the delay and CP behaviour alone.
            paths0 = [{**p, "f_hz": 0.0} for p in paths]
            if integer:
                y_lin0 = linear_stream_rx(x, S, paths0, tail)
                y_cir0 = circular_block_rx(x, S, paths0, slots, n_slots, tail)
            else:
                y_lin0, _ = _linear_fractional(x, S, paths0, tail)
                y_cir0 = _circular_fractional(x, S, paths0, slots, n_slots, tail)
            ref0 = np.zeros((len(slots), act.size), complex)
            for p in paths0:
                ref0 += p["amp"] * np.exp(-2j * np.pi * nc * S.scs_hz * p["tau_s"])[None, :]
            row["linear_field_residual_doppler_zero_db"] = _fres(y_lin0, ref0)
            row["circular_field_residual_doppler_zero_db"] = _fres(y_cir0, ref0)

            for model, y in (("linear", y_lin), ("circular", y_cir)):
                Y = collect_windows(y, S, slots)
                row[f"{model}_field_residual_db"] = _fres(y, ref)
                for tag, nv in (("nf", 0.0), ("snr", 10 ** (-cfg["snr_db"] / 10))):
                    Yn = Y if nv == 0 else collect_windows(y + np.sqrt(nv / 2) * noise, S, slots)
                    out = PILOT.receiver_grid(Yn, X, mask, S, PILOT.RxCfg(), return_map=True)
                    s = out["strongest"]
                    F = 1.0 / S.t_sym
                    row[f"{model}_{tag}_peak_range_m"] = float(C0 * s["tau_s"] / 2)
                    row[f"{model}_{tag}_delay_bias_m"] = float(C0 * s["tau_s"] / 2 - dsmp / S.fs * C0 / 2)
                    row[f"{model}_{tag}_doppler_bias_hz"] = float(((s["f_hz"] - f_d + F / 2) % F) - F / 2)
                    #: highest_other_peak_db - `receiver_grid`'s `psl_db`: the largest map power
                    #  outside the guard box around the strongest peak, in dB relative to that peak.
                    row[f"{model}_{tag}_highest_other_peak_db"] = float(out["psl_db"])
            rows.append(row)
    return {"band": cfg["band"], "occupied_mhz": res_span_mhz(S), "config": cfg,
            "symbol_slots": int(n_slots), "active_symbols": int(n_active),
            "cp_samples": int(S.cp), "fft": int(S.fft), "fs_hz": float(S.fs),
            "cp_range_limit_m": float(S.cp / S.fs * C0 / 2),
            "delay_search_max_range_m": delay_search_max_range_m(S),
            "rows": rows, "draw_spread": q0b_draw_spread(S, cfg, 2 if quick else 8)}


def q0b_draw_spread(S, cfg: dict, n_draws: int) -> dict:
    """Repeat the integer-delay rows over `n_draws` payload-and-phase draws and keep the min and max.

    The rows above are one draw.  Some of their numbers are a property of the configuration and some
    are a property of that draw, and the reader cannot tell which from a single row: the waveform
    residual at the block edges is set by whatever payload happened to wrap, and beyond the CP the
    strongest peak is not the target at all, so where it lands is a draw.  This block measures that.
    """
    Lb = S.fft + S.cp
    tail = 4 * Lb
    n_slots, n_active = cfg["n_slots"], cfg["n_active"]
    mask = PILOT.base_mask(S)
    act = np.flatnonzero(mask)
    nc = (np.arange(S.fft) - S.fft // 2)[act]
    f_bin = 1.0 / (n_active * S.t_sym)
    f_d = cfg["target_doppler_bins"] * f_bin
    F = 1.0 / S.t_sym
    keys = ("waveform_residual_edge_db", "waveform_residual_inside_db", "linear_field_residual_db",
            "linear_nf_delay_bias_m", "linear_nf_doppler_bias_hz")
    acc = {}
    for k in range(n_draws):
        rng = np.random.default_rng(CFG["seed_root"] + 1000 + k)
        X = PILOT.payload(rng, S, mask, CFG["modulation"], n_active)
        pc, pt = rng.uniform(0, 2 * np.pi), rng.uniform(0, 2 * np.pi)
        for kind in ("continuous", "two_bursts"):
            slots = schedule(kind, n_slots, n_active)
            x = build_stream(X, S, slots, n_slots)
            runs, start = [], 0
            for i in range(1, len(slots) + 1):
                if i == len(slots) or slots[i] != slots[i - 1] + 1:
                    runs.append((int(slots[start]), int(slots[i - 1]) + 1))
                    start = i
            tm = (slots * Lb + S.cp + (S.fft - 1) / 2) / S.fs
            for cname, dsmp in cfg["delay_cases"].items():
                paths = [{"tau_s": cfg["clutter_delay_samples"] / S.fs, "f_hz": 0.0,
                          "amp": 10 ** (cfg["clutter_power_db"] / 20) * np.exp(1j * pc)},
                         {"tau_s": dsmp / S.fs, "f_hz": f_d,
                          "amp": 10 ** (cfg["target_power_db"] / 20) * np.exp(1j * pt)}]
                y_lin = linear_stream_rx(x, S, paths, tail)
                y_cir = circular_block_rx(x, S, paths, slots, n_slots, tail)
                w = S.cp + int(np.ceil(dsmp))
                edge = np.zeros(len(y_lin), bool)
                inside = np.zeros(len(y_lin), bool)
                for s0, s1 in runs:
                    edge[s0 * Lb:s0 * Lb + w] = True
                    edge[s1 * Lb - w:s1 * Lb + w] = True
                    inside[s0 * Lb:s1 * Lb] = True
                inside &= ~edge
                ref = np.zeros((len(slots), act.size), complex)
                for pp in paths:
                    ref += pp["amp"] * np.exp(2j * np.pi * pp["f_hz"] * tm)[:, None] \
                        * np.exp(-2j * np.pi * nc * S.scs_hz * pp["tau_s"])[None, :]
                Yw = collect_windows(y_lin, S, slots)
                out = PILOT.receiver_grid(Yw, X, mask, S, PILOT.RxCfg(), return_map=True)
                st = out["strongest"]

                def _r(m):
                    return float(10 * np.log10(
                        max(float((np.abs(y_cir[m] - y_lin[m]) ** 2).sum()), 1e-300)
                        / max(float((np.abs(y_lin[m]) ** 2).sum()), 1e-300)))

                vals = {"waveform_residual_edge_db": _r(edge),
                        "waveform_residual_inside_db": _r(inside),
                        "linear_field_residual_db": float(10 * np.log10(
                            max(float((np.abs(Yw[:, act] / X[:, act] - ref) ** 2).sum()), 1e-300)
                            / float((np.abs(ref) ** 2).sum()))),
                        "linear_nf_delay_bias_m": float(C0 * st["tau_s"] / 2 - dsmp / S.fs * C0 / 2),
                        "linear_nf_doppler_bias_hz": float(((st["f_hz"] - f_d + F / 2) % F) - F / 2)}
                d = acc.setdefault(f"{kind}|{cname}", {k2: [] for k2 in keys})
                for k2 in keys:
                    d[k2].append(vals[k2])
    return {"n_draws": int(n_draws), "delay_cases": sorted(cfg["delay_cases"]),
            "spread": {row: {k2: {"min": float(min(v)), "max": float(max(v)),
                                  "spread": float(max(v) - min(v))}
                             for k2, v in cols.items()} for row, cols in acc.items()}}


def _linear_fractional(x: np.ndarray, S, paths: list, tail: int):
    """Fractional-delay linear stream: an ideal delay on a zero-padded stream.  The pad makes the wrap
    land in zeros; linear_pad_floor_db is the difference between two pad lengths, i.e. this model's own
    numerical floor rather than a property of the channel."""
    def _run(pad):
        L = len(x) + pad
        xp = np.concatenate([x, np.zeros(pad, complex)])
        f = np.fft.fftfreq(L, d=1.0 / S.fs)
        sp = np.fft.fft(xp)
        n = np.arange(L)
        y = np.zeros(L, complex)
        for p in paths:
            d = np.fft.ifft(sp * np.exp(-2j * np.pi * f * p["tau_s"]))
            y += p["amp"] * d * (np.exp(2j * np.pi * p["f_hz"] * n / S.fs) if p["f_hz"] else 1.0)
        return y[:len(x) + tail]
    y1, y2 = _run(tail), _run(4 * tail)
    num = float((np.abs(y1 - y2) ** 2).sum())
    den = float((np.abs(y2) ** 2).sum())
    return y2, float(10 * np.log10(max(num, 1e-300) / den))


def _circular_fractional(x: np.ndarray, S, paths: list, slots: np.ndarray, n_slots: int, tail: int):
    """PILOT.channel_time per transmitted block, Doppler continued from the block's absolute start."""
    Lb = S.fft + S.cp
    y = np.zeros(n_slots * Lb + tail, complex)
    runs, start = [], 0
    for i in range(1, len(slots) + 1):
        if i == len(slots) or slots[i] != slots[i - 1] + 1:
            runs.append((int(slots[start]), int(slots[i - 1]) + 1))
            start = i
    for s0, s1 in runs:
        n0, n1 = s0 * Lb, s1 * Lb
        blk = x[n0:n1]
        L = n1 - n0
        f = np.fft.fftfreq(L, d=1.0 / S.fs)
        sp = np.fft.fft(blk)
        n = np.arange(n0, n1)
        for p in paths:
            d = np.fft.ifft(sp * np.exp(-2j * np.pi * f * p["tau_s"]))
            y[n0:n1] += p["amp"] * d * (np.exp(2j * np.pi * p["f_hz"] * n / S.fs) if p["f_hz"] else 1.0)
    return y


# ----------------------------------------------------------------------------------------------------
#  Ledger and document
# ----------------------------------------------------------------------------------------------------
def _sha(path: str) -> str:
    return hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest()


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


def write_doc(d: dict, path: str) -> None:
    m, a, b = d["_meta"], d["q0a"], d["q0b"]
    L = []
    L.append("# RT path lists -> the CPU OFDM receiver: adapter and finite-burst check (Q0) - 2026-09-18\n")
    L.append(f"> Generated by `{GENERATOR}` from `{OUT_JSON}` (git HEAD at run `{m['git_head'][:12]}`); "
             f"do not edit by hand. Command: `{m['command']}`. Tests: `{TEST_MODULE}`.\n")
    L.append("> Scope: a numpy simulation on CPU. The ray tracer is not run here; path lists are read from "
             "shards that sionna-rt 2.1.0 wrote earlier. No hardware, no RF measurement. Every number is a "
             "property of this setup at the stated drone, build, range, elevation, ray budget, depth, path "
             "cap, record length and bandwidth.\n")

    L.append("## 1. What the adapter does\n")
    L.append("| Step | Rule |\n|---|---|")
    L.append("| baseband gain | `amp = a * exp(-2j*pi*fc*tau)` from the sidecar's passband `a`; applied once, here |")
    L.append("| delay | `tau_s = tau`, the absolute round-trip delay; never re-centred or normalised |")
    L.append("| Doppler | `f_hz = 0` for every RT path: the sweep stores none (`unpack(want_doppler=False)`) |")
    L.append("| pose | one stored pose per receiver frame; no path is matched or interpolated across poses |")
    L.append("| classes | `drone_only` / `env_only` / `mixed` from the sidecar `part` names; used only after the receiver returns |\n")
    car = a["carrier"]["open_sky"]
    L.append(f"Carrier for the baseband conversion: {car['fc_hz'] / 1e9:g} GHz, taken from the stored cell "
             f"({car['source']}). The receiver bands below use the same value and the run stops if they "
             "differ. 3.5 GHz is the working assumption of these cells, not a decided band.\n")
    L.append("Because every RT path here is at zero Doppler, slow-time mean removal would delete the whole "
             f"channel; section 3 therefore runs the receiver with `static_removal = {a['static_removal']}` "
             f"and noise variance {a['noise_var']}. Intra-frame motion, the pose-rate/symbol-rate mismatch "
             "and any time interpolation are out of this file's scope.\n")

    L.append("## 2. The stored cells, and what matched\n")
    g = a["pair_geometry"]
    L.append("Arm names re-read with `src/arm_grammar.py` (round trip checked). Fields that differ between "
             f"the two scenes: `{', '.join(g['fields_that_differ'])}` - environment only: "
             f"{_g(g['fields_that_differ_are_environment_only'])}. Stamp mismatches "
             f"(solver build, cfg, elevation, positions, PRF, rays, antenna): "
             f"{len(g['stamp_mismatches']) or 'none'}.\n")
    L.append("| Cell | positions | dumped | pose = idx[slot] | interleave | nret = sidecar | npaths = paths with interaction | truncated | unknown ids |\n"
             "|---|---|---|---|---|---|---|---|---|")
    for k, v in a["alignment"].items():
        L.append(f"| `{k}` | {v['n_poses_shard']} | {v['n_poses_dumped']} | {_g(v['pose_equals_idx_at_slot'])} | "
                 f"{_g(v['idx_follows_interleave_rule'])} | {_g(v['nret_equals_sidecar_n_paths'])} | "
                 f"{_g(v['npaths_equals_paths_with_interaction'])} | {v['n_trunc']} / {v['max_paths_cap']:,} | "
                 f"{v['n_unknown_id']} |")
    L.append("")
    L.append("`path_sum_rel_err` = |sum over listed paths with any interaction of `a*exp(-2j*pi*fc*tau)` - stored `E`| / |`E`|, "
             f"per dumped position; the threshold is this file's own, `TOL['path_sum_rel_err']` = "
             f"{_g(a['tolerance']['path_sum_rel_err'])}, not a figure from any other document. "
             "`path_sum_rel_err_fsum` is the same difference with an order-independent sum (`math.fsum` on "
             "the real and imaginary parts) and `bit-identical` is the fraction of positions where the "
             "adapter's own sum reproduces the stored `E` to the last bit - it does, because the adapter "
             "repeats the sweep's arithmetic on the sweep's stored numbers. `sum|a| / |E|` shows how much "
             "cancellation that sum carries.\n")
    L.append("| Cell | positions | path_sum_rel_err max | median | fsum max | bit-identical | sum\\|a\\| / \\|E\\| max | vs stored E_dedup (max) | duplicate rows | range min..max (m) | delay spread (ns, median) |\n"
             "|---|---|---|---|---|---|---|---|---|---|---|")
    for k, v in a["field_sum"].items():
        L.append(f"| `{k}` | {v['n_poses']} | {_g(v['path_sum_rel_err_max'])} | {_g(v['path_sum_rel_err_median'])} | "
                 f"{_g(v['path_sum_rel_err_fsum_max'])} | {_g(100 * v['path_sum_bit_identical_fraction'], 4)} % | "
                 f"{_g(v['cancellation_sum_abs_over_abs_E_max'], 3)} | "
                 f"{_g(v['path_sum_rel_err_vs_E_dedup_max'])} | {v['n_dup_total']} | "
                 f"{_g(v['range_m_min'])}..{_g(v['range_m_max'])} | {_g(v['delay_spread_ns_median'])} |")
    L.append("")
    L.append("Path classes, median over the dumped positions. `class_share_incoh_db` = "
             "10 log10 of that class's share of `sum |a|^2` over all listed paths of the position.\n")
    L.append("| Cell | drone_only | env_only | mixed | no_interaction | share drone_only (dB) | env_only (dB) | mixed (dB) |\n"
             "|---|---|---|---|---|---|---|---|")
    for k, v in a["field_sum"].items():
        c, s = v["class_count_median"], v["class_share_incoh_db"]
        L.append(f"| `{k}` | {_g(c['drone_only'])} | {_g(c['env_only'])} | {_g(c['mixed'])} | "
                 f"{_g(c['no_interaction'])} | {_g(s['drone_only'])} | {_g(s['env_only'])} | {_g(s['mixed'])} |")
    L.append("")

    L.append("## 3. CFR channel against the time-domain channel\n")
    tol = a["tolerance"]
    w = a["grid_vs_time_worst"]
    L.append("`grid_vs_time_map_rel` = L2 difference of the two delay-Doppler power maps divided by the L2 "
             "norm of the CFR map. Both channels carry the same path list; the CFR channel is exact for a "
             "static path list, the time-domain channel adds the frame-level fractional-delay tails.\n")
    npos_cell = next(iter(a["field_sum"].values()))["n_poses"]
    L.append(f"Scope of this section: {len(a['rx_slots'])} of the {npos_cell} dumped positions of shard "
             f"`{a['rx_shard']}` (slots {', '.join(str(x) for x in a['rx_slots'])}), one payload draw per "
             "row, no noise. It compares two ways of applying the same stored path list; it says nothing "
             "about the other positions of the record.\n")
    L.append(f"Tolerance declared in the source as `TOL`, not read off the table below: "
             f"map difference < {_g(tol['grid_vs_time_map_rel'])}, "
             f"peak range difference < {_g(tol['grid_vs_time_peak_range_frac_of_resolution'])} of that "
             f"band's range resolution, peak power difference < {_g(tol['grid_vs_time_peak_power_db'])} dB. "
             f"Every row within tolerance: {_g(a['grid_vs_time_all_within_tolerance'])}. Worst over all "
             f"rows: map {_g(w['grid_vs_time_map_rel'])}, peak range {_g(w['grid_vs_time_peak_range_m'])} m, "
             f"peak Doppler {_g(w['grid_vs_time_peak_doppler_hz'])} Hz, peak power "
             f"{_g(w['grid_vs_time_peak_power_db'])} dB.\n")
    L.append("| band | occupied (MHz) | scene | pose | class set | window | paths | map rel | peak range diff (m) | peak Doppler diff (Hz) | peak power diff (dB) | within tolerance | CFR peak range (m) | CFR highest other peak (dB) |\n"
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in a["receiver_rows"]:
        L.append(f"| {r['band']} | {_g(r['occupied_mhz'], 4)} | {r['scene']} | {r['pose']} | {r['class_set']} | "
                 f"{r['window']} | {r['n_paths']} | {_g(r['grid_vs_time_map_rel'])} | "
                 f"{_g(r['grid_vs_time_peak_range_m'])} | {_g(r['grid_vs_time_peak_doppler_hz'])} | "
                 f"{_g(r['grid_vs_time_peak_power_db'])} | {_g(r['within_tolerance'])} | "
                 f"{_g(r['grid_peak_range_m'], 5)} | {_g(r['grid_psl_db'])} |")
    L.append("")

    L.append("## 4. Every path keeps its delay, against one collapsed field E\n")
    L.append("`drone_bin_power_delta_db` = (map power in the delay cell nearest the nominal drone delay, "
             "relative to that map's maximum) with all paths collapsed into the single stored field `E` at "
             "the nominal delay, minus the same quantity with every path at its own delay. Read after the "
             "receiver returns; the receiver is never told where the drone is.\n")
    L.append(f"Scope of this section: the Hann window and the CFR channel only, noise free, the same "
             f"{len(a['rx_slots'])} positions of shard `{a['rx_shard']}` as section 3. The nominal delay is "
             "the sweep's own `cfg[0]` range, not a fitted value.\n")
    L.append("| band | occupied (MHz) | scene | pose | paths | nominal range (m) | kept: bin (dB re map max) | collapsed: bin (dB) | delta (dB) | kept peak (m) | collapsed peak (m) | env-only path (m) | env cell kept (dB) | env cell collapsed (dB) |\n"
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in a["range_bin_rows"]:
        L.append(f"| {r['band']} | {_g(r['occupied_mhz'], 4)} | {r['scene']} | {r['pose']} | {r['n_paths']} | "
                 f"{_g(r['nominal_range_m'], 4)} | {_g(r['drone_bin_kept_db'])} | {_g(r['drone_bin_collapsed_db'])} | "
                 f"{_g(r['drone_bin_power_delta_db'])} | {_g(r['kept_peak_range_m'], 5)} | "
                 f"{_g(r['collapsed_peak_range_m'], 5)} | {_g(r['env_only_range_m'], 4)} | "
                 f"{_g(r['env_bin_kept_db'])} | {_g(r['env_bin_collapsed_db'])} |")
    L.append("")

    L.append("## 5. Finite bursts: the circular-delay channel against a linear stream\n")
    r_c = next(r for r in b["rows"] if r["schedule"] == "continuous")
    r_b = next(r for r in b["rows"] if r["schedule"] == "two_bursts")
    L.append(f"Band `{b['band']}` (occupied {_g(b['occupied_mhz'], 4)} MHz), FFT {b['fft']}, CP "
             f"{b['cp_samples']} samples = {_g(b['cp_range_limit_m'], 4)} m of round-trip range, "
             f"{b['active_symbols']} transmitted symbols on a {b['symbol_slots']}-slot grid in both "
             "schedules. Paired across the schedules and across the two channel models: the payload, the "
             "two path phases, the Doppler, the number of transmitted symbols and the noise draw. Not "
             "paired, by construction: the elapsed span. The continuous schedule sends its "
             f"{b['active_symbols']} symbols in {r_c['transmit_span_slots']} consecutive slots "
             f"({_g(1e3 * r_c['transmit_span_s'], 4)} ms) and the two-burst schedule splits them into two "
             f"blocks at the two ends of the grid, spanning {r_b['transmit_span_slots']} slots "
             f"({_g(1e3 * r_b['transmit_span_s'], 4)} ms). That difference is the burst condition being "
             "tested, and the Doppler bin below is read against the transmitted symbol count, not against "
             "that span.\n")
    L.append("The Doppler-zero columns repeat each row with `f_hz = 0` on both paths and nothing else "
             "changed. `field_residual_db` compares a per-symbol channel estimate with an analytic "
             "response that holds one Doppler phase per symbol, so a moving target leaves an "
             "intra-symbol-Doppler floor in both models; the Doppler-zero column removes that floor and "
             "leaves the delay and CP behaviour alone.\n")
    L.append("`usable_fft_fraction`: over the transmitted FFT windows, the mean fraction of window samples "
             "the largest-delay path still draws from that symbol's own cyclic extension. "
             "`waveform_residual_*_db` = 10 log10 of the circular-minus-linear sample energy over the linear "
             "energy, taken over the block edges (CP + delay at each block end) and over the interior. "
             "`field_residual_db` = the same ratio for the per-symbol channel estimate against the analytic "
             "response of the same paths.\n")
    L.append("| schedule | delay case | delay (samples) | delay / CP | target range (m) | usable FFT fraction | waveform residual edge (dB) | inside (dB) | linear field residual (dB) | circular field residual (dB) | linear, Doppler zero (dB) | circular, Doppler zero (dB) |\n"
             "|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in b["rows"]:
        L.append(f"| {r['schedule']} | {r['delay_case']} | {_g(r['delay_samples'], 4)} | {_g(r['delay_vs_cp'])} | "
                 f"{_g(r['target_range_m'], 4)} | {_g(r['usable_fft_fraction'])} | "
                 f"{_g(r['waveform_residual_edge_db'])} | {_g(r['waveform_residual_inside_db'])} | "
                 f"{_g(r['linear_field_residual_db'])} | {_g(r['circular_field_residual_db'])} | "
                 f"{_g(r['linear_field_residual_doppler_zero_db'])} | "
                 f"{_g(r['circular_field_residual_doppler_zero_db'])} |")
    L.append("")
    L.append("Estimates of the strongest peak, noise free (`nf`) and with noise added to the waveform "
             f"(`snr`, noise variance {_g(b['rows'][0]['noise_var'], 4)} per time sample). "
             "`snr_waveform_db` in the ledger is the measured ratio of the mean received sample power over "
             f"the transmitted slots to that variance: {_g(min(r['snr_waveform_db'] for r in b['rows']))} "
             f"to {_g(max(r['snr_waveform_db'] for r in b['rows']))} dB over the rows, dominated by the "
             f"clutter path, which is {_g(b['config']['clutter_power_db'])} dB above the target, so the "
             "target path alone sits that much lower. (`config.snr_db` in the ledger is the pilot's own "
             "convention - the noise variance per sample is 10^(-snr_db/10), i.e. the per-sample SNR a "
             "unit-amplitude path would have - so it is not the SNR of this scene; `snr_waveform_db` is.) "
             "The truth enters only here, for scoring.\n")
    L.append("| schedule | delay case | model | nf delay bias (m) | nf Doppler bias (Hz) | nf highest other peak (dB) | snr delay bias (m) | snr Doppler bias (Hz) | snr highest other peak (dB) |\n"
             "|---|---|---|---|---|---|---|---|---|")
    for r in b["rows"]:
        for model in ("linear", "circular"):
            L.append(f"| {r['schedule']} | {r['delay_case']} | {model} | "
                     f"{_g(r[f'{model}_nf_delay_bias_m'], 4)} | {_g(r[f'{model}_nf_doppler_bias_hz'], 4)} | "
                     f"{_g(r[f'{model}_nf_highest_other_peak_db'])} | {_g(r[f'{model}_snr_delay_bias_m'], 4)} | "
                     f"{_g(r[f'{model}_snr_doppler_bias_hz'], 4)} | {_g(r[f'{model}_snr_highest_other_peak_db'])} |")
    L.append("")
    ds_ = b["draw_spread"]
    outside = sorted({r["delay_case"] for r in b["rows"] if not r["target_in_delay_search_span"]})
    L.append(f"The receiver's delay grid holds round-trip ranges 0 .. "
             f"{_g(b['delay_search_max_range_m'], 4)} m, i.e. the CP and no further "
             "(`delay_search_max_range_m`). `target_in_delay_search_span` says whether that row's target "
             "has a cell of its own. "
             + (f"It is no for: {', '.join('`' + c + '`' for c in outside)}. In those rows the delay bias "
                "in the table above is where a spurious peak fell, not a measurement of a bias, and the "
                "next table shows how far it moves when only the payload draw changes.\n"
                if outside else "It is yes for every row here.\n"))
    L.append(f"The rows above are one payload-and-phase draw. Repeating the integer-delay rows over "
             f"{ds_['n_draws']} draws (seed root {CFG['seed_root']} + 1000 + k, nothing else changed) "
             "separates what the configuration fixes from what the draw fixes.\n")
    L.append("| schedule | delay case | edge residual (dB) min..max | inside residual (dB) min..max | "
             "linear field residual (dB) min..max | linear nf delay bias (m) min..max |\n"
             "|---|---|---|---|---|---|")
    for key in sorted(ds_["spread"]):
        kind, cname = key.split("|")
        v = ds_["spread"][key]
        def _mm(name, nd=3):
            return f"{_g(v[name]['min'], nd)} .. {_g(v[name]['max'], nd)}"
        L.append(f"| {kind} | {cname} | {_mm('waveform_residual_edge_db')} | "
                 f"{_mm('waveform_residual_inside_db')} | {_mm('linear_field_residual_db', 4)} | "
                 f"{_mm('linear_nf_delay_bias_m', 4)} |")
    L.append("")
    L.append(f"The Doppler bin of a {b['active_symbols']}-symbol frame is "
             f"{_g(b['rows'][0]['doppler_bin_hz'], 4)} Hz and the target sits at "
             f"{_g(b['rows'][0]['target_doppler_hz'], 4)} Hz. A two-burst schedule is read by a "
             "uniform-stride receiver here: its Doppler axis is that of the transmitted symbol index, not of "
             "wall-clock time. That is a property of this receiver, not of either channel model, and it is "
             "the same in both model columns.\n")

    L.append("## 6. What is explained, and what failed\n")
    fs_max = max(v["path_sum_rel_err_max"] for v in a["field_sum"].values())
    fsum_max = max(v["path_sum_rel_err_fsum_max"] for v in a["field_sum"].values())
    bit_min = min(v["path_sum_bit_identical_fraction"] for v in a["field_sum"].values())
    canc_max = max(v["cancellation_sum_abs_over_abs_E_max"] for v in a["field_sum"].values())
    npos = sum(v["n_poses"] for v in a["field_sum"].values())
    L.append(f"- **Complex phase and amplitude - measured, passed.** Over {npos} dumped positions in the "
             f"four cells the largest `path_sum_rel_err` is {_g(fs_max)}, against this file's threshold "
             f"{_g(a['tolerance']['path_sum_rel_err'])}; in the weakest cell {_g(100 * bit_min, 4)} % of the "
             "positions reproduce the stored `E` bit for bit, because the adapter repeats the sweep's "
             "own arithmetic on the sweep's own stored numbers. An order-independent sum leaves "
             f"{_g(fsum_max)}, and `sum |a| / |E|` reaches {_g(canc_max, 3)}, so summation order is not "
             "carrying the result. What this establishes: the carrier convention (one "
             "`exp(-2j*pi*fc*tau)`, not two), the path selection, and that the sidecar list is complete "
             "for these cells. What it does not establish: that the traced field is right - that is a "
             "measurement question.")
    n_out = sum(1 for r in a["receiver_rows"] if not r["within_tolerance"])
    L.append(f"- **Time axis - measured, {'passed' if not n_out else 'FAILED'}.** CFR channel against "
             f"time-domain channel: {len(a['receiver_rows']) - n_out} of {len(a['receiver_rows'])} rows are "
             "within the stated tolerance; the worst row differs by "
             f"{_g(a['grid_vs_time_worst']['grid_vs_time_map_rel'])} in the map, "
             f"{_g(a['grid_vs_time_worst']['grid_vs_time_peak_range_m'])} m in peak range and "
             f"{_g(a['grid_vs_time_worst']['grid_vs_time_peak_power_db'])} dB in peak power.")
    dg = [r for r in a["range_bin_rows"] if r["scene"] == "ground"]
    ds = [r for r in a["range_bin_rows"] if r["scene"] == "open_sky"]
    L.append(f"- **Delay axis - measured.** Collapsing the list into the single stored `E` at the nominal "
             f"delay, instead of keeping each path at its own delay, raises the drone-range cell (relative "
             f"to that map's own maximum) by "
             f"{_g(min(r['drone_bin_power_delta_db'] for r in dg))} to "
             f"{_g(max(r['drone_bin_power_delta_db'] for r in dg))} dB over the {len(dg)} ground rows and "
             f"{_g(min(r['drone_bin_power_delta_db'] for r in ds))} to "
             f"{_g(max(r['drone_bin_power_delta_db'] for r in ds))} dB over the {len(ds)} open-sky rows "
             "(band and position as tabulated in section 4). Collapsing puts every path at the nominal "
             "drone delay, so the cell holds the whole field by construction; that is a property of the "
             "collapsed model, not a gain.")
    rows = b["rows"]
    icp = [r for r in rows if r["delay_case"] == "inside_cp"]
    bcp = [r for r in rows if r["delay_case"] == "beyond_cp"]
    icp0 = max(max(r["linear_field_residual_doppler_zero_db"], r["circular_field_residual_doppler_zero_db"])
               for r in icp)
    bcp0 = max(max(r["linear_field_residual_doppler_zero_db"], r["circular_field_residual_doppler_zero_db"])
               for r in bcp)
    gap = max(abs(r["linear_field_residual_db"] - r["circular_field_residual_db"]) for r in rows)
    dspread = max(v["linear_nf_delay_bias_m"]["spread"]
                  for k, v in b["draw_spread"]["spread"].items() if k.endswith("|beyond_cp"))
    L.append(f"- **Residual floor - explained.** With the target moving, both models sit at "
             f"{_g(max(r['linear_field_residual_db'] for r in icp))} dB for delays inside the CP. The "
             f"Doppler-zero control drops the same rows to {_g(icp0)} dB, so that floor is the "
             "intra-symbol Doppler of a per-symbol channel estimate, not a difference between the two "
             "channel models.")
    L.append(f"- **Beyond the cyclic prefix - a stress result, not a code defect.** At "
             f"{_g(bcp[0]['delay_samples'], 4)} samples ({_g(bcp[0]['delay_vs_cp'])} of the CP, "
             f"{_g(bcp[0]['target_range_m'], 4)} m) the field residual rises to "
             f"{_g(max(r['linear_field_residual_db'] for r in bcp))} dB. That target also sits past the "
             f"receiver's delay grid, which stops at {_g(bcp[0]['delay_search_max_range_m'], 4)} m (the CP), "
             "so no cell of the map belongs to it: the `delay_bias_m` of those rows is where a spurious "
             f"peak fell ({_g(max(abs(r['linear_nf_delay_bias_m']) for r in bcp), 4)} m here, moving by "
             f"{_g(dspread, 3)} m across {_g(b['draw_spread']['n_draws'])} payload draws), not a measured "
             "bias, and it is not evidence of how far off a detection would be. Three things say "
             "stress rather than bug: the two models, which differ only in whether the stream wraps, break "
             f"together (the largest linear-circular gap in `field_residual_db` over all rows is "
             f"{_g(gap)} dB); the Doppler-zero "
             f"control stays at {_g(bcp0)} dB where the inside-CP rows fall to {_g(icp0)} dB, so the "
             "residual follows the delay, not the Doppler; and `usable_fft_fraction` is "
             f"{_g(bcp[0]['usable_fft_fraction'])}, i.e. part of every FFT window is no longer that "
             "symbol's own cyclic extension. A delay past the CP is outside what CP-OFDM demodulation "
             "covers, so the threshold for a usable estimate is crossed by the configuration, not by the "
             "adapter.")
    tb = [r for r in rows if r["schedule"] == "two_bursts" and r["delay_case"] != "beyond_cp"]
    L.append(f"- **Two bursts - the receiver's time axis, not the channel.** Across the burst rows inside "
             f"the CP the delay bias stays within {_g(max(abs(r['linear_nf_delay_bias_m']) for r in tb), 3)} m "
             f"while the Doppler bias reaches {_g(max(abs(r['linear_nf_doppler_bias_hz']) for r in tb), 4)} Hz "
             f"in a {_g(rows[0]['doppler_bin_hz'], 4)} Hz bin, identically in both channel models. The "
             "receiver reads the transmitted symbol index as if the stride were uniform; the idle gap "
             "between the bursts is not in that axis. Q0 does not fix this - a burst-aware Doppler axis is "
             "a receiver change, and it is named here so it is not read later as a channel effect.")
    L.append("- **Not covered here.** The sidecar stores no Doppler, so every RT path in sections 2-4 is "
             "static and the receiver runs without slow-time mean removal; rotor motion inside a frame, "
             "the pose-rate against symbol-rate mismatch, path matching across poses, association and "
             "tracking are all outside this file. No path was interpolated between poses anywhere.\n")

    L.append("## 7. Inputs\n")
    L.append("| File | sha256 (first 16) |\n|---|---|")
    for k, v in sorted(m["inputs"].items()):
        L.append(f"| `{k}` | `{v[:16]}` |")
    L.append("")
    with open(os.path.join(ROOT, path), "w") as f:
        f.write("\n".join(L) + "\n")


# ----------------------------------------------------------------------------------------------------
#  Main
# ----------------------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out-json", default=OUT_JSON)
    ap.add_argument("--doc", default=DOC)
    ap.add_argument("--doc-from-json", action="store_true")
    args = ap.parse_args()
    if args.doc_from_json:
        raw = open(os.path.join(ROOT, args.out_json), "rb").read()
        led = json.loads(raw)
        led["_meta"]["json_sha256"] = hashlib.sha256(raw).hexdigest()
        write_doc(led, args.doc)
        print(f"  rewrote {args.doc} from {args.out_json}", flush=True)
        return

    t0 = time.time()
    cells = {}
    for scene, stem in PAIR.items():
        for sh in SHARDS:
            cells[(scene, sh)] = load_cell(stem, sh)
            print(f"  loaded {scene} {sh}: {cells[(scene, sh)]['slot'].size} dumped positions", flush=True)
    A = q0a(cells, args.quick)
    print(f"  Q0-a done, {time.time() - t0:.1f} s", flush=True)
    B = q0b(args.quick)
    print(f"  Q0-b done, {time.time() - t0:.1f} s", flush=True)

    inputs = {}
    for scene, stem in PAIR.items():
        for sh in SHARDS:
            inputs[f"{SHARD_DIR}/{stem}_{sh}.npz"] = _sha(f"{SHARD_DIR}/{stem}_{sh}.npz")
            inputs[f"{PROV_DIR}/{stem}_{sh}_prov.npz"] = _sha(f"{PROV_DIR}/{stem}_{sh}_prov.npz")
    led = {"_meta": {"generator": GENERATOR, "test_module": TEST_MODULE, "doc": args.doc,
                     "git_head": _git_head(), "quick": bool(args.quick),
                     "command": ('CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 '
                                 f'/workspace/.venvs/py312/bin/python {GENERATOR}'
                                 + (" --quick" if args.quick else "")),
                     "wall_s": time.time() - t0, "inputs": inputs,
                     "pilot_module": "benchmark/ofdm_receiver_pilot_0917.py",
                     "pilot_sha256": _sha("benchmark/ofdm_receiver_pilot_0917.py"),
                     "bands": BANDS, "pair": PAIR, "cfg": CFG},
           "q0a": A, "q0b": B}
    out = os.path.join(ROOT, args.out_json)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(led, f, indent=1, default=_json_default, sort_keys=False)
    raw = open(out, "rb").read()
    led["_meta"]["json_sha256"] = hashlib.sha256(raw).hexdigest()
    write_doc(led, args.doc)
    print(f"  wrote {args.out_json} and {args.doc} in {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
