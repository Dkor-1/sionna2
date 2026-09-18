# -*- coding: utf-8 -*-
"""
drift_clutter_pilot_0918.py - drifting clutter against slow and hovering drones (CPU, extends the 0917 pilot)
=============================================================================================================

Why
    /workspace/sionna_queue_recommendations_2026-09-18.md section 4 Q1: the 0917 pilot already has a failure
    case. Thresholds set on static target-absent (H0) frames gave a frame false-alarm rate of 0.783 on H0
    frames whose clutter paths carried a Doppler up to +/-10 Hz, against a target of 0.01
    (outputs/ofdm_receiver_pilot_0917.json : h0.stress.h0_eval_drift10.frame["1e-02"]). The pilot's H1 target
    Doppler was 300..5000 Hz, so it never asked what a low-Doppler rejection costs a slow or hovering drone.
    This script asks both at once: on the same frames, what does each suppression method do to the false-alarm
    rate in drifting clutter, and what does it do to a target at 0, 0.1, 0.5 and 2 Doppler bins?

What is new here (the 0917 pilot is imported, not modified)
    - three clutter environments: every clutter path carries a Doppler drawn uniformly in +/-0, +/-2, +/-10 Hz;
    - four suppression methods: the pilot's slow-time mean removal, a fixed low-Doppler rejection baseline at
      two half-widths, and a suppression method trained on H0 frames (slow-time principal subspace projection);
    - two threshold arms: one keeps the threshold calibrated on the static H0 set, the other recalibrates on
      the H0 set of the matching environment. The trained method's training set follows its arm the same way;
    - development, calibration and evaluation are three disjoint H0 seed streams per environment: the trained
      method sees only the development stream, thresholds see only the calibration stream, and false-alarm
      rates are counted only on the evaluation stream. No threshold and no notch width is chosen on the
      evaluation data;
    - a hover H1 set whose target amplitude is the slow-time variation of a stored ray-traced cell instead of
      a constant, at the same mean target power as the constant-amplitude control.

Definitions used below (each also defined where it is first printed in the generated document)
    slow-target loss   Pd at body Doppler 2.0 bins minus Pd at the stated body Doppler, in probability points,
                       at the same environment, SNR, method, arm and frame false-alarm target.
    notch_1bin         mean removal followed by blanking, from the candidate search region, every map cell
                       whose Doppler grid row satisfies |Doppler| < 1 Doppler bin (= 1 / frame duration). The
                       half-width is a system quantity (the frame's Doppler resolution) fixed before any
                       evaluation frame was read. The blank acts on grid rows, not on interpolated Dopplers.
    notch_2bin         the same blank at 2 Doppler bins, the Hann main-lobe half-width the CFAR guard already
                       uses. Added after the first full run showed the 1-bin blank left the frame statistic
                       unchanged; still a system quantity, still never tuned on evaluation frames.
    h0_subspace        mean removal replaced by projecting the slow-time sequence of every active subcarrier
                       onto the orthogonal complement of the r leading eigenvectors of a slow-time covariance
                       accumulated over the H0 development frames; r = the number of eigenvalues above
                       10 x the median eigenvalue, clipped to [1, 8]. r is read from the development set only.

Run (CPU only; about 1.5 core-hours at the default counts)
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 \
        /workspace/.venvs/py312/bin/python benchmark/drift_clutter_pilot_0918.py --workers 4
    --quick runs reduced counts for a smoke test; --doc-from-json rewrites the document from the ledger.

Outputs
    outputs/drift_clutter_pilot_0918.json, outputs/figures/drift_clutter_0918_{pfa,pd,hover}.png,
    docs/DRIFT_CLUTTER_0918.md (generated from the JSON by this script; do not edit by hand).
Tests
    benchmark/test_drift_clutter_pilot_0918.py

Changelog
    2026-09-18, adversarial review of this deliverable. No trial, threshold, blank width or seed stream
    changed; every measured number of the first run is reproduced by the re-run. What changed:
      1. the blade-flash rate is read from `outputs/report07_three_engines.json : _meta` (the rotor ledger
         benchmark/elevation_sweep_md.py itself reads) and the blade count from src/drones.py, instead of the
         literals 126.6667 Hz and 3800 rpm. That record's four rotors are not at one rpm, so the per-rotor
         rates and their spread are carried with the mean;
      2. the stored record's own modulation spectrum is measured and recorded: peak level relative to the
         coherent part, the five strongest lines, and the share of modulation power inside each blank. The
         document's hover section printed a modelled flash rate and no measured line;
      3. document: "the six method-arm pairs", "the 108 H1 conditions" (twice) and "symbol period ... Hz"
         were stale or wrong after the fourth method was added - all three are now computed or corrected;
      4. document section 7 now states the detection consequence of the lowest-Pfa arm in the same sentence
         as its false-alarm rate, names the arm that keeps detection at a controlled rate, and names every
         row whose measured Pfa interval lies above its target;
      5. document sections 4.4 and 6: the hover Pd is scored only within one Doppler bin of 0 Hz, so a
         candidate raised by a rotor line is off-target and never Pd; three of the four body Doppler levels
         sit exactly on padded grid rows; the H1 range draw can put the target on a clutter path;
      6. figure `pd` prints the measured Pfa of each method in each panel (the curves share a target, not a
         measured rate); figure `hover` gains a third panel zoomed to the blank edges, because on the
         +/-14 kHz axis of the old panel (b) the two edges cannot be told apart, and the blade-flash
         harmonics are marked there;
      7. section 4.1 gains what the blank does to the frame statistic itself, before any threshold, on the
         evaluation stream - the mechanism behind the rates, which the rate table alone does not show.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import os
import resource
import subprocess
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

GENERATOR = "benchmark/drift_clutter_pilot_0918.py"
PILOT = "benchmark/ofdm_receiver_pilot_0917.py"
TEST_MODULE = "benchmark/test_drift_clutter_pilot_0918.py"
OUT_JSON = "outputs/drift_clutter_pilot_0918.json"
FIG_PREFIX = "outputs/figures/drift_clutter_0918_"
DOC = "docs/DRIFT_CLUTTER_0918.md"


def _load_pilot():
    spec = importlib.util.spec_from_file_location("ofdm_receiver_pilot_0917", os.path.join(ROOT, PILOT))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


P = _load_pilot()
C0 = P.C0
SYSTEM = P.SYSTEM

# ------------------------------------------------------------------------------------------------------
#  Stored ray-traced cell used for the hover H1 set (0961 job lines 15-16, the symbol-rate record).
#  Positions are 1/28,029 s apart, which is the pilot's symbol period to 7.0e-6 relative error, so one
#  position is taken per OFDM symbol with no resampling.
# ------------------------------------------------------------------------------------------------------
RT_STEM = ("sionna_p4000000000_swR0D0E0F1_r15_n4096_prf28029_shell0.75mm_prop1.43mm_"
           "mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15")
RT_SHARDS = [f"outputs/elev_sweep_shards/{RT_STEM}_{i:02d}.npz" for i in (0, 1)]
#  Rotor ledger the sweep itself reads (benchmark/elevation_sweep_md.py line 103): the per-rotor rpm of the
#  poses in that record and the blade-flash rate derived from them. Read, never typed in here.
ROTOR_LEDGER = "outputs/report07_three_engines.json"

CFG = {
    "seed_root": 20260918,
    "config": "qpsk_dcguard",
    "envs": {"static": 0.0, "drift2": 2.0, "drift10": 10.0},
    "body_doppler_bins": [0.0, 0.1, 0.5, 2.0],
    "snr_re_db": [-40.0, -36.0, -32.0],
    "methods": ["mean_removal", "notch_1bin", "notch_2bin", "h0_subspace"],
    "arms": ["static_cal", "matched_cal"],
    "notch_half_width_bins": 1.0,
    "notch_wide_half_width_bins": 2.0,
    "subspace": {"subcarrier_stride": 4, "eig_ratio_to_median": 10.0, "r_max": 8, "r_min": 1},
    "n_train": 200, "n_cal": 1000, "n_eval": 3000, "n_h1": 300,
    "pfa_frame": [0.1, 0.01],
    "n_top_candidates": 64,
    "h1_range_m": [40.0, 320.0],
    "train_chunk": 25,
}
QUICK = {"n_train": 12, "n_cal": 60, "n_eval": 80, "n_h1": 10,
         "body_doppler_bins": [0.0, 0.5], "snr_re_db": [-36.0], "train_chunk": 6}

EXP_CODES = {"h0_train": 1, "h0_cal": 2, "h0_eval": 3, "h1_body": 4, "h1_rt_hover": 5}
ENV_CODES = {"static": 0, "drift2": 1, "drift10": 2}

RX_MEAN = "mean_removal"
RX_NOTCH = "notch_1bin"
RX_NOTCH_WIDE = "notch_2bin"
RX_SUB_STATIC = "h0_subspace|static"
RX_SUB_MATCHED = "h0_subspace|matched"

CFG_RUN = dict(CFG)
BASES: dict = {}          # environment -> (M, r) orthonormal basis, set in the parent before the pool forks
RT_SERIES: np.ndarray | None = None


# ------------------------------------------------------------------------------------------------------
#  Receiver with a pluggable suppression stage and an optional fixed low-Doppler blank
# ------------------------------------------------------------------------------------------------------
def receiver_ext(Y: np.ndarray, X_ref: np.ndarray, mask: np.ndarray, S, cfg,
                 suppress: str = "mean", basis: np.ndarray | None = None, notch_bins: float = 0.0,
                 n_top: int = 64, return_map: bool = False) -> dict:
    """The 0917 receiver with the static-removal step replaced by `suppress` and a fixed low-Doppler blank.

    suppress: 'mean' (subtract the slow-time mean per subcarrier, the 0917 default), 'subspace' (subtract the
    projection of the slow-time sequence onto the columns of `basis`) or 'none'.
    notch_bins: candidates with |Doppler| below this many Doppler bins are dropped from the search region; the
    CFAR training average is unchanged. notch_bins = 0 reproduces benchmark/ofdm_receiver_pilot_0917.py
    receiver_grid exactly (pinned by test_matches_pilot_receiver in the test module).
    """
    k = int(cfg.stride)
    Yk, Xk = Y[::k], X_ref[::k]
    M, N = Yk.shape
    act = np.flatnonzero(mask)
    H = np.zeros((M, N), complex)
    H[:, act] = Yk[:, act] / Xk[:, act]                       # nulls and guards: masked, not divided
    if suppress == "mean":
        H[:, act] -= H[:, act].mean(axis=0, keepdims=True)
    elif suppress == "subspace":
        if basis is None:
            raise ValueError("suppress='subspace' needs a basis")
        H[:, act] -= basis @ (basis.conj().T @ H[:, act])
    elif suppress != "none":
        raise ValueError(suppress)
    occ = np.flatnonzero(P.base_mask(S))
    lo, hi = int(occ[0]), int(occ[-1])
    wf = np.zeros(N)
    if cfg.window == "hann":
        wf[lo:hi + 1] = np.hanning(hi - lo + 3)[1:-1]
        wt = np.hanning(M + 2)[1:-1]
    elif cfg.window == "rect":
        wf[lo:hi + 1] = 1.0
        wt = np.ones(M)
    else:
        raise ValueError(cfg.window)
    wf = wf * mask
    norm = float(wf.sum() * wt.sum())
    D = cfg.pad_delay * N
    G = np.zeros((M, D), complex)
    G[:, (np.arange(N) - N // 2) % D] = H * wt[:, None] * wf[None, :]
    cc = P.cfar_cells(S, cfg)
    gd, td, gt, tt = cc["guard_doppler"], cc["train_doppler"], cc["guard_delay"], cc["train_delay"]
    n_s = cfg.pad_delay * S.cp + 1                            # delay cells 0 .. CP duration
    marg = gt + tt + 1
    prof = (np.fft.ifft(G, axis=1) * D)[:, np.arange(-marg, n_s + marg) % D]
    Mp = cfg.pad_doppler * M
    Z = np.fft.fftshift(np.fft.fft(prof, n=Mp, axis=0), axes=0) / norm
    Pmap = Z.real ** 2 + Z.imag ** 2
    f_axis = np.fft.fftshift(np.fft.fftfreq(Mp, d=k * S.t_sym))
    tau_axis = np.arange(n_s) / (D * S.scs_hz)

    rd = gd + td
    Pw = np.concatenate([Pmap[-(rd + 1):], Pmap, Pmap[:rd + 1]], axis=0)     # Doppler axis is cyclic
    integ = np.zeros((Pw.shape[0] + 1, Pw.shape[1] + 1))
    integ[1:, 1:] = Pw.cumsum(axis=0).cumsum(axis=1)
    r = np.arange(Mp) + rd + 1
    c = np.arange(n_s) + marg

    def box(hr: int, hc: int) -> np.ndarray:
        r0, r1 = (r - hr)[:, None], (r + hr + 1)[:, None]
        c0, c1 = (c - hc)[None, :], (c + hc + 1)[None, :]
        return integ[r1, c1] - integ[r0, c1] - integ[r1, c0] + integ[r0, c0]

    noise = (box(rd, gt + tt) - box(gd, gt)) / cc["n_train"]
    Ps = Pmap[:, marg:marg + n_s]
    T = Ps / np.maximum(noise, 1e-300)

    bin_hz = 1.0 / (M * k * S.t_sym)
    keep = np.abs(f_axis) >= notch_bins * bin_hz              # notch_bins = 0 keeps every row
    Pn = Pw[rd:rd + Mp + 2, marg - 1:marg + n_s + 1]
    ismax = Ps > 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                ismax &= Ps >= Pn[1 + di:Pn.shape[0] - 1 + di, 1 + dj:Pn.shape[1] - 1 + dj]
    ismax &= keep[:, None]
    ci, cj = np.nonzero(ismax)

    def est(i: int, j: int) -> dict:
        jj = j + marg
        dm = P._offset(Pmap[(i - 1) % Mp, jj], Pmap[i, jj], Pmap[(i + 1) % Mp, jj], cfg.interp)
        dt = P._offset(Pmap[i, jj - 1], Pmap[i, jj], Pmap[i, jj + 1], cfg.interp)
        return {"tau_s": (j + dt) / (D * S.scs_hz), "f_hz": float(f_axis[i] + dm / (Mp * k * S.t_sym)),
                "P": float(Pmap[i, jj]), "T": float(T[i, j]), "i": int(i), "j": int(j)}

    Pk = Ps if notch_bins == 0.0 else Ps[keep]
    out = {"n_search": int(Pk.size), "mean_P": float(Pk.mean()), "frame_stat": 0.0, "strongest": None,
           "top": [], "psl_db": None, "top_T_cut": 0.0, "notch_bins": float(notch_bins),
           "n_search_full": int(Ps.size)}
    zero_rows = np.abs(f_axis) < 1.0 / (M * k * S.t_sym)
    out["zero_doppler_max_P"] = float(Ps[zero_rows].max())    # before the notch, for reference
    out["max_P"] = float(Pk.max())
    if len(ci):
        Tc = T[ci, cj]
        out["frame_stat"] = float(Tc.max())
        pick = list(np.argsort(-Tc)[:n_top])
        pick += [o for o in np.argsort(-Ps[ci, cj])[:n_top] if o not in set(pick)]
        out["top"] = [est(ci[o], cj[o]) for o in pick]
        out["top_T_cut"] = float(Tc[pick[n_top - 1]]) if len(Tc) > n_top else 0.0
        s = int(np.argmax(Ps[ci, cj]))
        i0, j0 = int(ci[s]), int(cj[s])
        out["strongest"] = est(i0, j0)
        ex = Ps.copy()
        ex[np.ix_((i0 + np.arange(-gd, gd + 1)) % Mp, np.arange(max(0, j0 - gt), min(n_s, j0 + gt + 1)))] = 0.0
        out["psl_db"] = float(10 * np.log10(max(ex.max(), 1e-300) / Ps[i0, j0]))
    if return_map:
        out["map"] = {"P": Ps, "f_axis": f_axis, "tau_axis": tau_axis}
    return out


# ------------------------------------------------------------------------------------------------------
#  Channel with an optional per-symbol complex gain on a path (the ray-traced hover input)
# ------------------------------------------------------------------------------------------------------
def channel_time_mod(tx: np.ndarray, S, paths: list, noise_var: float, rng) -> np.ndarray:
    """benchmark/ofdm_receiver_pilot_0917.py channel_time with one addition: a path may carry 'gain_t', a
    complex gain of one value per OFDM symbol (held over the symbol's CP and body). Without any 'gain_t' this
    reproduces channel_time exactly (pinned by test_matches_pilot_channel in the test module)."""
    L = len(tx)
    f = np.fft.fftfreq(L, d=1.0 / S.fs)
    spec = np.fft.fft(tx)
    n = np.arange(L)
    rx = np.zeros(L, complex)
    static = [p for p in paths if p["f_hz"] == 0.0 and p.get("gain_t") is None]
    if static:
        ramp = np.zeros(L, complex)
        for p in static:
            ramp += p["amp"] * np.exp(-2j * np.pi * f * p["tau_s"])
        rx += np.fft.ifft(spec * ramp)
    for p in paths:
        if p["f_hz"] == 0.0 and p.get("gain_t") is None:
            continue
        s = p["amp"] * np.fft.ifft(spec * np.exp(-2j * np.pi * f * p["tau_s"]))
        if p["f_hz"] != 0.0:
            s = s * np.exp(2j * np.pi * p["f_hz"] * n / S.fs)
        g = p.get("gain_t")
        if g is not None:
            s = s * np.repeat(np.asarray(g), S.fft + S.cp)[:L]
        rx += s
    if noise_var > 0:
        rx += np.sqrt(noise_var / 2) * (rng.standard_normal(L) + 1j * rng.standard_normal(L))
    return rx


# ------------------------------------------------------------------------------------------------------
#  Stored ray-traced cell
# ------------------------------------------------------------------------------------------------------
def load_rt_cell(shards: list) -> dict:
    """Read the stored open-sky cell, sort by pose index, and record what the reader checked."""
    idx, E, npaths, builds, metas, cfgs = [], [], [], [], [], []
    for rel in shards:
        d = np.load(os.path.join(ROOT, rel), allow_pickle=True)
        idx.append(d["idx"])
        E.append(d["E"])
        npaths.append(d["npaths"])
        builds.append(str(d["solver_build"]))
        metas.append(np.asarray(d["meta"], float))
        cfgs.append(np.asarray(d["cfg"], float))
        n_trunc = int(np.asarray(d["n_trunc"])[0])
        if n_trunc:
            raise RuntimeError(f"{rel}: {n_trunc} poses at the path cap; do not cite this cell")
    idx = np.concatenate(idx)
    E = np.concatenate(E)
    npaths = np.concatenate(npaths)
    o = np.argsort(idx)
    idx, E, npaths = idx[o], E[o], npaths[o]
    if not np.array_equal(idx, np.arange(idx.size)):
        raise RuntimeError("pose indices are not 0..n-1 exactly once")
    if not np.isfinite(E).all():
        raise RuntimeError("non-finite E")
    if len(set(builds)) != 1:
        raise RuntimeError(f"shards carry different solver builds: {builds}")
    m = np.median(E.real) + 1j * np.median(E.imag)
    dd = np.abs(E - m)
    iso = int((dd > 20 * np.median(dd)).sum())
    prf = float(metas[0][4])
    mean_E = E.mean()
    return {"stem": RT_STEM, "shards": shards, "solver_build": builds[0], "n_positions": int(idx.size),
            "prf_hz": prf, "record_s": idx.size / prf, "range_m": float(cfgs[0][0]),
            "elevation_deg": float(metas[0][0]), "max_depth": int(cfgs[0][1]), "rays": float(cfgs[0][2]),
            "isolated_20xmedian": iso, "npaths_median": float(np.median(npaths)),
            "npaths_min": int(npaths.min()), "npaths_max": int(npaths.max()),
            "static_level_db": float(20 * np.log10(abs(mean_E))),
            "ac_power_db": float(10 * np.log10(np.mean(np.abs(E - mean_E) ** 2))),
            "ac_to_static_db": float(10 * np.log10(np.mean(np.abs(E - mean_E) ** 2)) - 20 * np.log10(abs(mean_E))),
            "E": E}


def rt_window(E: np.ndarray, k0: int, n_sym: int) -> np.ndarray:
    """One frame of hover modulation: n_sym consecutive positions scaled to mean |g|^2 = 1, so the frame's
    mean target power equals that of the constant-amplitude control."""
    g = E[k0:k0 + n_sym]
    return g / math.sqrt(float(np.mean(np.abs(g) ** 2)))


# ------------------------------------------------------------------------------------------------------
#  Scenes
# ------------------------------------------------------------------------------------------------------
def doppler_bin_hz(S) -> float:
    return 1.0 / (S.n_sym * S.t_sym)


def build_scene_q1(spec: dict, S, rng, rt: np.ndarray | None = None) -> tuple[list, dict]:
    """Clutter + (for H1) one target path. Truth is returned, never given to the receiver."""
    paths, truth = [], {"target": None, "ghost": None}
    drift = float(spec["drift_hz"])
    for cl in P.CFG["scene"]["clutter"]:
        fd = rng.uniform(-drift, drift) if drift > 0 else 0.0
        paths.append(P._path(cl["range_m"], fd, cl["power_db"], rng.uniform(0, 2 * np.pi)))
    if spec["scene"] == "h0":
        return paths, truth
    rm = rng.uniform(*CFG["h1_range_m"])
    if spec["scene"] == "h1_body":
        f = spec["body_bins"] * doppler_bin_hz(S) * (1.0 if rng.random() < 0.5 else -1.0)
        p = P._path(rm, f, 0.0, rng.uniform(0, 2 * np.pi))
    elif spec["scene"] == "h1_rt_hover":
        if rt is None:
            raise RuntimeError("the hover set needs the stored cell")
        f = 0.0
        k0 = int(rng.integers(0, len(rt) - S.n_sym + 1))
        p = P._path(rm, 0.0, 0.0, rng.uniform(0, 2 * np.pi))
        p["gain_t"] = rt_window(rt, k0, S.n_sym)
        truth["rt_start_index"] = k0
    else:
        raise ValueError(spec["scene"])
    truth["target"] = {"range_m": rm, "f_hz": f}
    paths.append(p)
    return paths, truth


def frame_channel(spec: dict, S):
    """Payload, mask and received grid of one frame; returns (Y, X, mask, truth)."""
    ss = np.random.SeedSequence(CFG["seed_root"], spawn_key=tuple(int(v) for v in spec["key"]))
    r_pay, r_geo, r_noise, r_null = (np.random.default_rng(s) for s in ss.spawn(4))
    conf = P.CFG["configs"][CFG["config"]]
    mask = P.make_mask(S, conf["random_null_frac"], r_null)
    X = P.payload(r_pay, S, mask, conf["modulation"], S.n_sym)
    paths, truth = build_scene_q1(spec, S, r_geo, RT_SERIES)
    noise_var = 0.0 if spec["snr_db"] is None else 10 ** (-spec["snr_db"] / 10)
    Y = P.demod(channel_time_mod(P.tx_time(X, S), S, paths, noise_var, r_noise), S, S.n_sym)
    return Y, X, mask, truth


# ------------------------------------------------------------------------------------------------------
#  Workers
# ------------------------------------------------------------------------------------------------------
def receivers_for(env: str) -> list:
    """(label, suppression, basis environment, notch half-width in Doppler bins) of one frame."""
    rows = [(RX_MEAN, "mean", None, 0.0),
            (RX_NOTCH, "mean", None, float(CFG["notch_half_width_bins"])),
            (RX_NOTCH_WIDE, "mean", None, float(CFG["notch_wide_half_width_bins"])),
            (RX_SUB_STATIC, "subspace", "static", 0.0)]
    if env != "static":
        rows.append((RX_SUB_MATCHED, "subspace", env, 0.0))
    return rows


def run_frame(spec: dict) -> dict:
    S = SYSTEM
    cfg = P.RxCfg(**P.CFG["receiver_default"])
    Y, X, mask, truth = frame_channel(spec, S)
    rows = {}
    for label, sup, benv, notch in receivers_for(spec["env"]):
        out = receiver_ext(Y, X, mask, S, cfg, suppress=sup,
                           basis=None if benv is None else BASES[benv], notch_bins=notch,
                           n_top=CFG["n_top_candidates"])
        rec = P.score(out, truth, S, cfg)
        rows[label] = {"frame_stat": rec["frame_stat"], "off_T": rec["off_T"], "n_search": out["n_search"],
                       "mean_P": rec["mean_P"]}
        if truth["target"] is not None:
            rows[label].update({"target_T": rec["target_T"],
                                "strongest": rec.get("strongest", {"range_err_m": None, "doppler_err_hz": None,
                                                                   "within_tol": False, "P": 0.0})})
    return {"spec": spec, "rows": rows}


def train_chunk(spec: dict) -> np.ndarray:
    """Slow-time covariance of the divided channel estimate, summed over the frames of one chunk."""
    S = SYSTEM
    sub = int(CFG["subspace"]["subcarrier_stride"])
    R = np.zeros((S.n_sym, S.n_sym), complex)
    for i in spec["indices"]:
        sp = {**spec, "key": (EXP_CODES["h0_train"], ENV_CODES[spec["env"]], 0, 0, int(i))}
        Y, X, mask, _ = frame_channel(sp, S)
        act = np.flatnonzero(mask)[::sub]
        Hs = Y[:, act] / X[:, act]
        R += Hs @ Hs.conj().T
    return R


def basis_from_cov(R: np.ndarray, n_frames: int, n_sub: int) -> dict:
    lam, vec = np.linalg.eigh(R)
    order = np.argsort(lam)[::-1]
    lam, vec = lam[order].real, vec[:, order]
    med = float(np.median(lam))
    sub = CFG["subspace"]
    r = int((lam > sub["eig_ratio_to_median"] * med).sum())
    r = int(min(max(r, sub["r_min"]), sub["r_max"]))
    tot = float(lam.sum())
    return {"r": r, "basis": np.ascontiguousarray(vec[:, :r]),
            "eigenvalues_top8_db_re_median": [float(10 * np.log10(max(v, 1e-300) / med)) for v in lam[:8]],
            "median_eigenvalue": med, "leading_share": float(lam[0] / tot),
            "share_of_first_r": float(lam[:r].sum() / tot),
            "leading_vector_overlap_with_mean": float(abs(vec[:, 0].conj()
                                                          @ (np.ones(R.shape[0]) / math.sqrt(R.shape[0]))) ** 2),
            "n_train_frames": int(n_frames), "n_subcarriers_used": int(n_sub)}


# ------------------------------------------------------------------------------------------------------
#  Specs
# ------------------------------------------------------------------------------------------------------
def build_specs(cfg: dict) -> dict:
    g = {}
    for exp, n in (("h0_cal", cfg["n_cal"]), ("h0_eval", cfg["n_eval"])):
        g[exp] = [{"exp": exp, "env": e, "drift_hz": cfg["envs"][e], "scene": "h0",
                   "snr_db": P.CFG["snr_ref_db"], "key": (EXP_CODES[exp], ENV_CODES[e], 0, 0, i)}
                  for e in cfg["envs"] for i in range(n)]
    g["h1_body"] = [{"exp": "h1_body", "env": e, "drift_hz": cfg["envs"][e], "scene": "h1_body",
                     "body_bins": b, "snr_db": s,
                     "key": (EXP_CODES["h1_body"], ENV_CODES[e], int(round(b * 10)),
                             int(round((s + 100) * 10)), i)}
                    for e in cfg["envs"] for b in cfg["body_doppler_bins"] for s in cfg["snr_re_db"]
                    for i in range(cfg["n_h1"])]
    g["h1_rt_hover"] = [{"exp": "h1_rt_hover", "env": e, "drift_hz": cfg["envs"][e], "scene": "h1_rt_hover",
                         "body_bins": 0.0, "snr_db": s,
                         "key": (EXP_CODES["h1_rt_hover"], ENV_CODES[e], 0, int(round((s + 100) * 10)), i)}
                        for e in cfg["envs"] for s in cfg["snr_re_db"] for i in range(cfg["n_h1"])]
    return g


# ------------------------------------------------------------------------------------------------------
#  Aggregation
# ------------------------------------------------------------------------------------------------------
def rx_label(method: str, arm: str, env: str) -> str:
    if method != "h0_subspace":
        return method
    if arm == "static_cal" or env == "static":
        return RX_SUB_STATIC
    return RX_SUB_MATCHED


def cal_env(arm: str, env: str) -> str:
    return "static" if arm == "static_cal" else env


def _key(p: float) -> str:
    return f"{p:.0e}"


def agg_h0(res: dict) -> dict:
    """Thresholds from the calibration stream only; false alarms counted on the disjoint evaluation stream."""
    cal, ev = {}, {}
    for r in res["h0_cal"]:
        cal.setdefault(r["spec"]["env"], []).append(r["rows"])
    for r in res["h0_eval"]:
        ev.setdefault(r["spec"]["env"], []).append(r["rows"])
    alpha = {}                                 # receiver label -> env -> pfa key -> threshold
    for e, rows in cal.items():
        for label in rows[0]:
            fs = np.array([x[label]["frame_stat"] for x in rows])
            alpha.setdefault(label, {})[e] = {
                _key(p): float(np.quantile(fs, 1 - p, method="higher")) for p in CFG_RUN["pfa_frame"]}
    out = {"alpha": alpha, "rows": [], "search_cells": {}, "blank_effect": {}}
    for e, rows in cal.items():
        for label in rows[0]:
            out["search_cells"][f"{label}|{e}"] = int(rows[0][label]["n_search"])
    #  What the blank does to the frame statistic itself, before any threshold: on the evaluation stream,
    #  how often it changes the statistic at all and by how much, against mean removal on the same frames.
    for e, rows in ev.items():
        base = np.array([x[RX_MEAN]["frame_stat"] for x in rows])
        for label in (RX_NOTCH, RX_NOTCH_WIDE):
            if label not in rows[0]:
                continue
            got = np.array([x[label]["frame_stat"] for x in rows])
            drop = 10 * np.log10(np.maximum(base, 1e-300) / np.maximum(got, 1e-300))
            out["blank_effect"][f"{label}|{e}"] = {
                "n_eval": int(base.size), "frames_changed": int((base != got).sum()),
                "frac_changed": float((base != got).mean()),
                "median_drop_db": float(np.median(drop)), "max_drop_db": float(drop.max()),
                "median_drop_db_over_changed": (float(np.median(drop[base != got]))
                                                if (base != got).any() else None)}
    for method in CFG_RUN["methods"]:
        for arm in CFG_RUN["arms"]:
            for e in CFG_RUN["envs"]:
                lab = rx_label(method, arm, e)
                ce = cal_env(arm, e)
                a = alpha[lab][ce] if ce in alpha[lab] else alpha[RX_SUB_STATIC][ce]
                fs_cal = np.array([x[lab]["frame_stat"] for x in cal[e]]) if lab in cal[e][0] else None
                fs_ev = np.array([x[lab]["frame_stat"] for x in ev[e]])
                row = {"method": method, "arm": arm, "env": e, "receiver": lab, "calibrated_on": ce,
                       "n_eval": int(fs_ev.size), "n_cal": int(len(cal[ce])), "frame": {}}
                for kk, av in a.items():
                    n = int((fs_ev > av).sum())
                    row["frame"][kk] = {"alpha": av, "false_alarm_frames": n, "rate": n / fs_ev.size,
                                        "wilson95": P.wilson(n, int(fs_ev.size)),
                                        "cal_rate_same_env": (None if fs_cal is None
                                                              else float((fs_cal > av).mean()))}
                out["rows"].append(row)
    return out


def agg_h1(res: dict, h0: dict, exp: str) -> dict:
    groups = {}
    for r in res[exp]:
        sp = r["spec"]
        groups.setdefault((sp["env"], sp["body_bins"], sp["snr_db"]), []).append(r["rows"])
    rows = []
    res_cell = P.resolution(SYSTEM)
    for (e, b, snr), frames in sorted(groups.items()):
        for method in CFG_RUN["methods"]:
            for arm in CFG_RUN["arms"]:
                lab = rx_label(method, arm, e)
                ce = cal_env(arm, e)
                a = h0["alpha"][lab][ce]
                n = len(frames)
                row = {"env": e, "body_doppler_bins": b, "body_doppler_hz": b * doppler_bin_hz(SYSTEM),
                       "snr_re_db": snr, "method": method, "arm": arm, "receiver": lab, "calibrated_on": ce,
                       "n": n, "pd": {}, "off_target_frames": {}}
                for kk, av in a.items():
                    d = int(sum(x[lab]["target_T"] > av for x in frames))
                    off = int(sum(any(t > av for t, _ in x[lab]["off_T"]) for x in frames))
                    row["pd"][kk] = {"alpha": av, "detected": d, "pd": d / n, "wilson95": P.wilson(d, n)}
                    row["off_target_frames"][kk] = {"frames": off, "rate": off / n, "wilson95": P.wilson(off, n)}
                wt = [x[lab]["strongest"] for x in frames if x[lab]["strongest"]["within_tol"]]
                row["strongest_within_tol_frac"] = len(wt) / n
                if wt:
                    er = np.array([x["range_err_m"] for x in wt])
                    ef = np.array([x["doppler_err_hz"] for x in wt])
                    row.update({"bias_doppler_hz": float(ef.mean()), "rmse_doppler_hz": float(np.sqrt((ef ** 2).mean())),
                                "bias_range_m": float(er.mean()), "rmse_range_m": float(np.sqrt((er ** 2).mean()))})
                else:
                    row.update({"bias_doppler_hz": None, "rmse_doppler_hz": None,
                                "bias_range_m": None, "rmse_range_m": None})
                rows.append(row)
    fast = max(CFG_RUN["body_doppler_bins"])
    ref = {(x["env"], x["snr_re_db"], x["method"], x["arm"]): x for x in rows if x["body_doppler_bins"] == fast}
    for x in rows:
        r0 = ref.get((x["env"], x["snr_re_db"], x["method"], x["arm"]))
        x["slow_target_loss_points"] = {kk: (None if r0 is None else r0["pd"][kk]["pd"] - x["pd"][kk]["pd"])
                                        for kk in x["pd"]}
    pf = {}
    for r in h0["rows"]:
        pf[(r["method"], r["arm"], r["env"])] = {kk: v["rate"] for kk, v in r["frame"].items()}
    for x in rows:
        x["achieved_frame_pfa"] = pf[(x["method"], x["arm"], x["env"])]
    return {"rows": rows, "reference_body_doppler_bins": fast,
            "tolerance": {"range_m": res_cell["range_m"], "doppler_hz": res_cell["doppler_hz"]}}


# ------------------------------------------------------------------------------------------------------
#  Figures
# ------------------------------------------------------------------------------------------------------
def figures(d: dict, prefix: str) -> dict:
    plt = P._style()
    from paper_kit import series_style
    out = {}
    envs = list(CFG_RUN["envs"])
    kk = _key(min(CFG_RUN["pfa_frame"]))

    # 1. measured frame false-alarm rate per environment, method and arm
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.3), sharey=True)
    x = np.arange(len(envs))
    for ax, arm in zip(axs, CFG_RUN["arms"]):
        for i, method in enumerate(CFG_RUN["methods"]):
            sel = [next(r for r in d["h0"]["rows"] if r["method"] == method and r["arm"] == arm and r["env"] == e)
                   for e in envs]
            y = np.array([max(r["frame"][kk]["rate"], 1e-4) for r in sel])
            lo = np.array([max(r["frame"][kk]["wilson95"][0], 1e-4) for r in sel])
            hi = np.array([r["frame"][kk]["wilson95"][1] for r in sel])
            stl = series_style(i)
            ax.errorbar(x + (i - 1) * 0.12, y, yerr=[y - lo, hi - y], capsize=3, label=method, **stl)
        ax.axhline(min(CFG_RUN["pfa_frame"]), color="#333333", linestyle=(0, (2, 2)), linewidth=1.0)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{e}\n(+/-{CFG_RUN['envs'][e]:g} Hz)" for e in envs])
        ax.set_title(f"threshold arm: {arm}", fontsize=9)
        ax.set_xlabel("Clutter Doppler environment")
    axs[0].set_ylabel(f"Measured frame Pfa (target {kk})")
    axs[1].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.suptitle(f"Frame false-alarm rate on {d['config']['n_eval']} evaluation frames per environment "
                 "(Wilson 95 %; dashed line = target)", fontsize=9)
    fig.tight_layout()
    out["pfa"] = P._save(fig, prefix + "pfa.png")
    plt.close(fig)

    # 2. Pd against body Doppler, one panel per environment, matched-calibration arm
    snr_mid = CFG_RUN["snr_re_db"][len(CFG_RUN["snr_re_db"]) // 2]
    fig, axs = plt.subplots(1, len(envs), figsize=(3.5 * len(envs), 3.6), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, e in zip(axs, envs):
        ach = []
        for i, method in enumerate(CFG_RUN["methods"]):
            sel = sorted([r for r in d["h1"]["rows"] if r["env"] == e and r["method"] == method
                          and r["arm"] == "matched_cal" and r["snr_re_db"] == snr_mid],
                         key=lambda r: r["body_doppler_bins"])
            ax.plot([r["body_doppler_bins"] for r in sel], [r["pd"][kk]["pd"] for r in sel],
                    label=method, **series_style(i))
            ach.append(sel[0]["achieved_frame_pfa"][kk])
        for w in (CFG_RUN["notch_half_width_bins"], CFG_RUN["notch_wide_half_width_bins"]):
            ax.axvline(w, color="#333333", linestyle=(0, (1, 2)), linewidth=1.0)
        #  The curves in one panel are at a common Pfa *target*, not a common measured rate: print the
        #  measured rate of each method so the panel is not read as an equal-false-alarm comparison.
        ax.set_title(f"{e} (+/-{CFG_RUN['envs'][e]:g} Hz)\nmeasured Pfa "
                     + " / ".join(f"{v:.4f}" for v in ach), fontsize=8.5)
        ax.set_xlabel("Body Doppler (bins)")
        ax.set_ylim(-0.03, 1.03)
    axs[0].set_ylabel("Probability of detection")
    axs[-1].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.suptitle(f"Pd at frame Pfa target {kk}, SNR per RE {snr_mid:g} dB, matched-calibration arm "
                 "(dotted lines = the two blank edges; measured Pfa in method order)", fontsize=9)
    fig.tight_layout()
    out["pd"] = P._save(fig, prefix + "pd.png")
    plt.close(fig)

    # 3. the stored ray-traced hover input: one frame of slow-time modulation and its spectrum
    rt = d["rt_input"]
    g = np.asarray(rt["example_window_real"]) + 1j * np.asarray(rt["example_window_imag"])
    S = SYSTEM
    t_ms = np.arange(len(g)) * S.t_sym * 1e3
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.2))
    axs[0].plot(t_ms, np.abs(g), **series_style(0, marker=False))
    axs[0].axhline(abs(complex(rt["example_window_mean_real"], rt["example_window_mean_imag"])),
                   color="#333333", linestyle=(0, (2, 2)), linewidth=1.0)
    axs[0].set_xlabel("Time within the frame (ms)")
    axs[0].set_ylabel("|g| (mean |g|$^2$ = 1)")
    axs[0].set_title("(a) One frame of the stored cell (dashes: |mean g|)", fontsize=9)
    bin_hz = doppler_bin_hz(S)
    #  (b) the whole record, which resolves the blade-flash lines; (c) the same, zoomed to the blank edges,
    #  because on the full +/-14 kHz axis the two edges sit on top of each other and cannot be read.
    Pr = np.asarray(rt["mod_spectrum_db"], float)
    fr = np.fft.fftshift(np.fft.fftfreq(Pr.size, d=1.0 / rt["prf_hz"]))
    for ax, span, ttl in ((axs[1], None, f"(b) Modulation spectrum, all {rt['n_positions']} positions"),
                          (axs[2], 6.0 * bin_hz,
                           "(c) The same, at the blank edges\n(long dashes: blade-flash harmonics)")):
        sel = np.ones(fr.size, bool) if span is None else (np.abs(fr) <= span)
        ax.plot(fr[sel], Pr[sel], **series_style(1, marker=False))
        for w in (CFG_RUN["notch_half_width_bins"], CFG_RUN["notch_wide_half_width_bins"]):
            for sgn in (1.0, -1.0):
                ax.axvline(sgn * w * bin_hz, color="#333333", linestyle=(0, (1, 2)), linewidth=1.0)
        ax.set_xlabel("Doppler (Hz)")
        ax.set_title(ttl, fontsize=9)
        body = Pr[sel & (fr != 0.0)]                 # the mean was removed, so the 0 Hz bin is the floor
        ax.set_ylim(body.min() - 3.0, body.max() + 3.0)
    for k in range(1, 7):                       # blade-flash harmonics, marked where they are resolved
        if k * rt["f_flash_hz"] <= 6.0 * bin_hz:
            for sgn in (1.0, -1.0):
                axs[2].axvline(sgn * k * rt["f_flash_hz"], color="#b15928", linestyle=(0, (4, 3)),
                               linewidth=0.9)
    axs[1].set_ylabel("Power re |mean E|$^2$ (dB)")
    fig.suptitle(f"Hover input from {rt['stem'][:44]}... ({rt['n_positions']} positions at "
                 f"{rt['prf_hz']:.0f} Hz; dotted lines = the candidate-blank edges at "
                 f"{CFG_RUN['notch_half_width_bins']:g} and {CFG_RUN['notch_wide_half_width_bins']:g} "
                 "Doppler bins)", fontsize=8.5)
    fig.tight_layout()
    out["hover"] = P._save(fig, prefix + "hover.png")
    plt.close(fig)
    return out


# ------------------------------------------------------------------------------------------------------
#  Document (generated; every number printed from the result dict)
# ------------------------------------------------------------------------------------------------------
_g = P._g
_d = P._d


def write_doc(d: dict, path: str) -> None:
    m, cfg, sysd = d["_meta"], d["config"], d["system"]
    rt, sub, h0, h1, hv = d["rt_input"], d["subspace"], d["h0"], d["h1"], d["h1_rt_hover"]
    kk = _key(min(cfg["pfa_frame"]))
    L = []
    a = L.append
    a("# Drifting clutter against slow and hovering drones (CPU, extends the 0917 pilot) - 2026-09-18")
    a("")
    a(f"> Generated by `{m['generator']}` from `{m['out_json']}` (git HEAD at run `{m['git_head'][:12]}`); "
      f"do not edit by hand. Command: `{m['command']}`. Tests: `{m['test_module']}`.")
    a("> Scope: a numpy simulation of a monostatic OFDM radar receiver on synthetic point-path channels, with "
      "one slow-time modulation read from a stored PathSolver cell. No hardware, no RF measurement. Every "
      "number below is a property of this simulation setup at the stated parameters.")
    a("")
    a("## 1. Question and design")
    a("")
    a("The 0917 pilot set its thresholds on static target-absent frames and then met clutter that moved: at a "
      f"frame false-alarm target of {kk} the measured rate was "
      f"{_g(m['pilot_reference']['drift10_frame_pfa'])} with clutter Doppler up to "
      f"+/-{_g(m['pilot_reference']['drift10_hz'])} Hz "
      f"(`{m['pilot_reference']['ledger']}` : `{m['pilot_reference']['key']}`). Its H1 targets carried "
      f"|Doppler| {_g(m['pilot_reference']['h1_doppler_abs_hz'][0])}..{_g(m['pilot_reference']['h1_doppler_abs_hz'][1])} Hz, "
      "so it never asked what suppressing low Doppler costs a slow or hovering drone. This run asks both on "
      "the same frames.")
    a("")
    a("| Axis | Levels |")
    a("|---|---|")
    a("| clutter environment (Doppler of every clutter path, drawn uniformly per frame) | "
      + ", ".join(f"`{e}` +/-{_g(v)} Hz" for e, v in cfg["envs"].items()) + " |")
    a("| body Doppler (H1 target), in Doppler bins of this frame | "
      + ", ".join(_g(b) for b in cfg["body_doppler_bins"])
      + f" (1 bin = {_g(sysd['doppler_bin_hz'])} Hz) |")
    a("| SNR per resource element (dB) | " + ", ".join(_g(s) for s in cfg["snr_re_db"]) + " |")
    a("| suppression method | " + ", ".join(f"`{x}`" for x in cfg["methods"]) + " |")
    a("| threshold arm | " + ", ".join(f"`{x}`" for x in cfg["arms"]) + " |")
    a("| payload configuration | `" + cfg["config"] + "` (QPSK, DC + guard nulls) |")
    a("")
    a(f"Methods x environments x body Doppler x SNR = {len(cfg['methods'])} x {len(cfg['envs'])} x "
      f"{len(cfg['body_doppler_bins'])} x {len(cfg['snr_re_db'])} = {d['counts']['h1_conditions']} H1 "
      f"conditions per threshold arm, plus {d['counts']['h1_rt_conditions']} hover conditions with the stored "
      f"ray-traced modulation and {d['counts']['h0_conditions']} H0 conditions.")
    a("")
    a(f"The design asked for three methods - the present mean removal, one fixed low-Doppler rejection "
      f"baseline and one H0-trained suppression method - which is "
      f"{d['counts']['h1_conditions_three_method_core']} H1 conditions per arm. The second blank width "
      f"`notch_2bin` is a fourth method added after the first full run; it raises the count to "
      f"{d['counts']['h1_conditions']} and is reported alongside, never in place of, the three.")
    a("")
    a("Methods:")
    a("")
    a(f"- `mean_removal`: the 0917 pilot's step 3, subtract the slow-time mean of every active subcarrier.")
    a(f"- `notch_1bin`: mean removal, then drop every map cell whose Doppler grid row has |Doppler| below "
      f"{_g(cfg['notch_half_width_bins'])} Doppler bin ({_g(cfg['notch_half_width_bins'] * sysd['doppler_bin_hz'])} Hz) "
      "from the candidate search region. The half-width is the frame's Doppler resolution, a system quantity "
      "fixed before any evaluation frame was read; the CFAR training average is unchanged. The blank acts on "
      "the rows of the padded Doppler grid, so a candidate whose 3-point-interpolated Doppler falls inside the "
      "band is still kept when its grid row lies outside it.")
    a(f"- `notch_2bin`: the same candidate blank at a half-width of "
      f"{_g(cfg['notch_wide_half_width_bins'])} Doppler bins "
      f"({_g(cfg['notch_wide_half_width_bins'] * sysd['doppler_bin_hz'])} Hz), which is the Hann main-lobe "
      "half-width already used by the CFAR guard in section 2. It is also a system quantity and not a swept "
      "parameter, but it was added after the first run of this script showed that the "
      f"{_g(cfg['notch_half_width_bins'])}-bin width left the frame statistic unchanged, so it is not a blind "
      "choice made before any result was seen; both widths are reported side by side and neither was tuned on "
      "evaluation frames. Note the geometry this creates: the fastest body Doppler in this run is "
      f"{_g(h1['reference_body_doppler_bins'])} bins, which is exactly this half-width, so the reference "
      "target of sections 4.2 and 4.3 sits on the edge of this blank. Its Pd there is the best case for this "
      "width, and nothing in this run says what a blank one padded grid row wider would leave of it.")
    a(f"- `h0_subspace`: mean removal replaced by projecting every active subcarrier's slow-time sequence onto "
      f"the orthogonal complement of the r leading eigenvectors of a slow-time covariance accumulated over the "
      f"H0 development frames; r = the number of eigenvalues above {_g(cfg['subspace']['eig_ratio_to_median'])} x "
      f"the median eigenvalue, clipped to [{cfg['subspace']['r_min']}, {cfg['subspace']['r_max']}].")
    a("")
    a("Threshold arms: `static_cal` keeps the threshold (and, for `h0_subspace`, the trained subspace) of the "
      "static environment and carries it to the drifting ones; `matched_cal` recalibrates (and retrains) on "
      "the H0 sets of the matching environment. In the static environment the two arms are the same numbers "
      "by construction.")
    a("")
    a("### 1.1 Separation of development, calibration and evaluation")
    a("")
    a("| Stream | Frames per environment | Used for | Never used for |")
    a("|---|---|---|---|")
    a(f"| `h0_train` | {cfg['n_train']} | the `h0_subspace` covariance and r | thresholds, rates |")
    a(f"| `h0_cal` | {cfg['n_cal']} | the frame threshold at each false-alarm target | measured rates |")
    a(f"| `h0_eval` | {cfg['n_eval']} | the measured frame false-alarm rate | any threshold, any notch width |")
    a("")
    a(f"The three streams have disjoint seed keys (experiment codes "
      + ", ".join(f"{k}={v}" for k, v in m["seeds"]["experiment_codes"].items())
      + f"), so no frame appears twice. With {cfg['n_eval']} evaluation frames a measured rate of "
      f"{_g(d['interval_scale']['at_rate'])} has a Wilson 95 % interval of "
      f"[{_g(d['interval_scale']['wilson_at_rate'][0])}, {_g(d['interval_scale']['wilson_at_rate'][1])}] "
      f"and a measured {d['interval_scale']['zero_of_n']} of 0 gives "
      f"[{_g(d['interval_scale']['wilson_zero'][0])}, {_g(d['interval_scale']['wilson_zero'][1])}]; that is the "
      "resolution of every false-alarm number below.")
    a("")
    a("## 2. System, receiver and channel")
    a("")
    a("| Parameter | Value |")
    a("|---|---|")
    for k, v in (("carrier (Hz)", sysd["fc_hz"]), ("subcarrier spacing (Hz)", sysd["scs_hz"]),
                 ("FFT size", sysd["fft"]), ("CP (samples)", sysd["cp"]), ("symbols per frame", sysd["n_sym"]),
                 ("frame duration (s)", sysd["cpi_s"]), ("Doppler bin 1/frame (Hz)", sysd["doppler_bin_hz"]),
                 ("velocity per Doppler bin (m/s)", sysd["velocity_per_doppler_bin_mps"]),
                 ("range resolution (m)", sysd["range_resolution_m"]),
                 ("search range limit = CP (m)", sysd["max_range_cp_m"]),
                 ("Hann main-lobe half-width used by the CFAR guard (Doppler bins)", sysd["hann_lobe_bins"])):
        a(f"| {k} | {_g(v, 5)} |")
    a("")
    a("The system, payload, modulation, time-domain channel and receiver chain are those of "
      f"`{m['pilot']}` (division by the per-frame reference on active subcarriers, suppression, separable "
      "Hann window, inverse FFT over subcarriers, FFT over symbols, CA-CFAR, local maxima, 3-point peak "
      "interpolation). This script replaces only the suppression stage and adds the candidate blank of "
      "`notch_1bin` and `notch_2bin`; with no notch and mean removal it reproduces the pilot's receiver "
      "exactly (test "
      "`test_matches_pilot_receiver`). Clutter is the pilot's three zero-Doppler paths at "
      + ", ".join(f"{_g(x['range_m'])} m ({_g(x['power_db'])} dB)" for x in cfg["clutter"])
      + " relative to the target, each given a Doppler drawn uniformly in +/- the environment's value, held "
      "constant within a frame. H1 adds one target path at a range drawn uniformly in "
      f"{_g(cfg['h1_range_m'][0])}..{_g(cfg['h1_range_m'][1])} m; the pilot's target-borne second path is not "
      "used here, so every detection that is not within one resolution cell and one Doppler bin of the target "
      "counts as off-target. H0 frames use the noise level of SNR "
      f"{_g(cfg['snr_ref_db'])} dB for a unit target, as in the pilot.")
    a("")
    a("### 2.1 The hover input from a stored ray-traced cell")
    a("")
    a(f"Cell: `{rt['stem']}` (shards " + ", ".join(f"`{s}`" for s in rt["shards"]) + f"), "
      f"{rt['n_positions']} positions at {_g(rt['prf_hz'])} Hz = {_g(rt['record_s'])} s, open sky, "
      f"range {_g(rt['range_m'])} m, elevation {_g(rt['elevation_deg'])} deg, max_depth {rt['max_depth']}, "
      f"{_g(rt['rays'])} rays, canonical slab, tr38901 aimed, `{rt['solver_build']}`. Reader checks: pose "
      f"indices 0..n-1 exactly once, E finite, one solver build, no pose at the path cap; "
      f"`isolated_20xmedian` = {rt['isolated_20xmedian']} of {rt['n_positions']} positions; path count per "
      f"position {rt['npaths_min']}..{rt['npaths_max']} (median {_g(rt['npaths_median'])}).")
    a("")
    a(f"Over the whole record, static level 20log10|mean E| = {_g(rt['static_level_db'])} dB, "
      f"AC power 10log10 mean|E-mean E|^2 = {_g(rt['ac_power_db'])} dB, AC minus static = "
      f"{_g(rt['ac_to_static_db'])} dB. A hover frame takes {sysd['n_sym']} consecutive positions starting at "
      f"an index drawn uniformly in 0..{rt['n_start_positions'] - 1} and scales them to mean |g|^2 = 1, so the "
      "frame's mean target power equals that of the constant-amplitude control; window-to-window level "
      "variation of the record is removed by that scaling. Over the "
      f"{rt['n_start_positions']} windows the coherent share |mean g|^2 spans "
      f"{_g(rt['window_coherent_share_db_min'])}..{_g(rt['window_coherent_share_db_max'])} dB (median "
      f"{_g(rt['window_coherent_share_db_median'])} dB) and the window root-mean-square level spans "
      f"{_g(rt['window_rms_spread_db'])} dB.")
    a("")
    a(f"The stored positions are {_g(rt['prf_hz'])} Hz apart and the pilot's symbol rate is "
      f"{_g(sysd['symbol_rate_hz'])} Hz, a relative difference of {_g(rt['time_axis_rel_error'])}; one position "
      f"is used per symbol with no resampling, which over a {sysd['n_sym']}-symbol frame accumulates "
      f"{_g(rt['time_axis_frame_error_s'])} s ({_g(rt['time_axis_frame_error_frac_of_position'])} of one "
      "position spacing).")
    a("")
    a(f"The rotors turn throughout. The four rotors of this record are not at one rpm: "
      + ", ".join(_g(v, 6) for v in rt["rpm_per_rotor"]) + f" rpm (`{rt['flash_source']}`, airframe "
      f"`{rt['drone_key']}`, {rt['prop_blades']} blades per rotor), which is "
      + ", ".join(_g(v, 5) for v in rt["flash_per_rotor_hz"]) + f" Hz of blade flash, a spread of "
      f"{_g(rt['flash_spread_hz'])} Hz around a mean of {_g(rt['f_flash_hz'], 5)} Hz. The frame is "
      f"{_g(sysd['cpi_s'])} s, so it spans {_g(rt['flash_periods_per_frame'])} mean blade-flash periods and "
      f"the spread between rotors is far below the frame's Doppler bin of {_g(sysd['doppler_bin_hz'])} Hz; "
      "this run cannot separate the four.")
    a("")
    a("Measured on the stored record itself (not modelled): the spectrum of `E - mean E` over all "
      f"{rt['n_positions']} positions peaks {_g(rt['mod_peak_db_re_coherent'])} dB below the coherent part "
      f"|mean E|^2, at {_g(rt['mod_peak_hz'])} Hz = {_g(rt['mod_peak_over_flash'])} x the mean blade-flash "
      "rate. The five strongest lines are at "
      + ", ".join(f"{_g(f)} Hz ({_g(v)} dB)" for f, v in zip(rt["mod_top5_hz"], rt["mod_top5_db"]))
      + f". Of that modulation power, {_g(rt['mod_power_frac_within_1bin'])} lies inside the "
      f"{_g(cfg['notch_half_width_bins'])}-bin blank and {_g(rt['mod_power_frac_within_2bin'])} inside the "
      f"{_g(cfg['notch_wide_half_width_bins'])}-bin blank, so most of it is outside both; it is also "
      f"{_g(rt['mod_peak_db_re_coherent'])} dB below the coherent part, which is what `mean_removal` takes "
      "out. One frame of the record (the figure in section 5) peaks "
      f"{_g(rt['example_window_mod_peak_db'])} dB below |mean g|^2 at "
      f"{_g(rt['example_window_mod_peak_hz'])} Hz; at this frame length the lines above are not resolved.")
    a("")
    a("## 3. What the H0 development set gave the trained method")
    a("")
    a("| Environment | training frames | subcarriers used | r | leading eigenvalue (dB re median) | "
      "2nd | 3rd | share of the first r | overlap of the leading vector with the all-ones direction |")
    a("|---|---|---|---|---|---|---|---|---|")
    for e in cfg["envs"]:
        s = sub[e]
        ev = s["eigenvalues_top8_db_re_median"]
        a(f"| `{e}` | {s['n_train_frames']} | {s['n_subcarriers_used']} | {s['r']} | {_g(ev[0])} | {_g(ev[1])} | "
          f"{_g(ev[2])} | {_g(s['share_of_first_r'])} | {s['leading_vector_overlap_with_mean']:.6f} |")
    a("")
    a("The overlap column is |<u1, 1/sqrt(M)>|^2, printed to six decimals because it is the column that "
      "decides whether this method is new: at 1 the leading direction is exactly the constant slow-time "
      "sequence that `mean_removal` already removes, and the measured values here are "
      + ", ".join(f"{sub[e]['leading_vector_overlap_with_mean']:.6f}" for e in cfg["envs"])
      + " for " + ", ".join(f"`{e}`" for e in cfg["envs"])
      + ". r is read from the development frames only.")
    a("")
    a("## 4. Results (observations)")
    a("")
    a("### 4.1 Measured frame false-alarm rate")
    a("")
    a(f"Thresholds from {cfg['n_cal']} calibration frames, rates from {cfg['n_eval']} disjoint evaluation "
      "frames of the same environment. 'calibrated on' names the environment whose calibration frames set the "
      "threshold (and, for `h0_subspace`, trained the subspace).")
    a("")
    a("| Method | Arm | Environment | calibrated on | search cells | target | threshold | false frames / n | "
      "measured Pfa [Wilson 95 %] |")
    a("|---|---|---|---|---|---|---|---|---|")
    for r in h0["rows"]:
        cells = h0["search_cells"][f"{r['receiver']}|{r['env']}"]
        for pk, v in r["frame"].items():
            a(f"| `{r['method']}` | `{r['arm']}` | `{r['env']}` | `{r['calibrated_on']}` | {cells} | {pk} | "
              f"{_g(v['alpha'])} | {v['false_alarm_frames']}/{r['n_eval']} | {_g(v['rate'])} "
              f"[{_g(v['wilson95'][0])}, {_g(v['wilson95'][1])}] |")
    a("")
    a("")
    a("What the blank does to the frame statistic itself, before any threshold is applied, on the same "
      f"{cfg['n_eval']} evaluation frames: 'changed' is the share of frames whose frame statistic differs at "
      "all from `mean_removal` on that frame, and the drop is 10log10(statistic without blank / statistic "
      "with blank), so a positive drop means the blank lowered it.")
    a("")
    a("| Blank | Environment | frames changed | share changed | median drop (dB) | median drop over the "
      "changed frames (dB) | largest drop (dB) |")
    a("|---|---|---|---|---|---|---|")
    for key, v in h0.get("blank_effect", {}).items():
        lab, e = key.rsplit("|", 1)
        a(f"| `{lab}` | `{e}` | {v['frames_changed']}/{v['n_eval']} | {_g(v['frac_changed'])} | "
          f"{_g(v['median_drop_db'])} | {_d(v['median_drop_db_over_changed'])} | {_g(v['max_drop_db'])} |")
    a("")
    n_mc = len([r for r in h1["rows"] if r["arm"] == "matched_cal"])
    a(f"### 4.2 Detection, matched-calibration arm (the {n_mc} H1 conditions)")
    a("")
    a(f"Pd, off-target frames, Doppler bias and slow-target loss at frame false-alarm target {kk}. "
      "slow-target loss = Pd at body Doppler "
      f"{_g(h1['reference_body_doppler_bins'])} bins minus Pd here, in probability points, at the same "
      "environment, SNR, method and arm. 'achieved Pfa' repeats the measured rate of section 4.1 for this "
      "method, arm and environment, because the comparison is at a fixed false-alarm target and not at a "
      "fixed measured rate. Doppler bias and its RMSE are over the frames whose strongest peak lies within "
      "one resolution cell and one Doppler bin of the target (that fraction is the 'within cell' column), so "
      "they are conditional and optimistic where that fraction is low.")
    a("")
    _h1_table(a, [r for r in h1["rows"] if r["arm"] == "matched_cal"], kk)
    a("")
    a(f"### 4.3 Detection, static-calibration arm (the same {n_mc} conditions, threshold carried from "
      "static H0)")
    a("")
    _h1_table(a, [r for r in h1["rows"] if r["arm"] == "static_cal"], kk)
    a("")
    a("### 4.4 Hover with the stored ray-traced modulation")
    a("")
    a("Same H1 machinery, target Doppler exactly 0, target amplitude modulated by the stored cell instead of "
      "held constant. The constant-amplitude control is the body Doppler 0.0 row of sections 4.2 and 4.3 at "
      "the same environment, SNR, method and arm.")
    a("")
    a("⚠ Read Pd here with the scoring rule of section 2 in hand: a frame counts as a detection only when a "
      "candidate lands within one resolution cell and one Doppler bin of the target, and the target's "
      f"Doppler is 0, so the tolerance is |Doppler| <= {_g(sysd['doppler_bin_hz'])} Hz. The record's five "
      f"strongest modulation lines are at |Doppler| {_g(min(abs(v) for v in rt['mod_top5_hz']))} to "
      f"{_g(max(abs(v) for v in rt['mod_top5_hz']))} Hz (section 2.1), all outside that tolerance, so a "
      "candidate raised by a rotor line is counted in the off-target column and never in Pd. "
      f"For `notch_2bin` the tolerance band is inside the blank, so its Pd here is 0 by construction and only "
      "its off-target column carries information. What Pd in this section measures is whether the stored "
      "cell's time variation moves the detection of a target at the zero-Doppler cell, against a constant "
      "amplitude at the same mean power - not whether a hovering drone can be detected by its rotor lines, "
      "which this run does not ask.")
    a("")
    a("| Environment | SNR/RE (dB) | Method | Arm | Pd (RT hover) [95 %] | Pd (constant, 0.0 bins) [95 %] | "
      "RT minus constant | off-target frames (RT) | achieved Pfa | within cell (RT) |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    const = {(r["env"], r["snr_re_db"], r["method"], r["arm"]): r
             for r in h1["rows"] if r["body_doppler_bins"] == 0.0}
    for r in hv["rows"]:
        c = const[(r["env"], r["snr_re_db"], r["method"], r["arm"])]
        pr, pc = r["pd"][kk], c["pd"][kk]
        a(f"| `{r['env']}` | {_g(r['snr_re_db'])} | `{r['method']}` | `{r['arm']}` | "
          f"{_g(pr['pd'])} [{_g(pr['wilson95'][0])}, {_g(pr['wilson95'][1])}] | "
          f"{_g(pc['pd'])} [{_g(pc['wilson95'][0])}, {_g(pc['wilson95'][1])}] | "
          f"{_g(pr['pd'] - pc['pd'])} | {_g(r['off_target_frames'][kk]['rate'])} | "
          f"{_g(r['achieved_frame_pfa'][kk])} | {_g(r['strongest_within_tol_frac'])} |")
    a("")
    a("## 5. Figures")
    a("")
    for k in ("pfa", "pd", "hover"):
        f = d["figures"][k]
        a(f"- `{f['path']}` (min font {_g(f['min_font_pt'])} pt, overlap warnings {f['overlap_warnings']})")
    a("")
    a("## 6. What this does and does not show")
    a("")
    for s in d["not_shown"]:
        a(f"- {s}")
    a("")
    a("## 7. Reading (stated as reading, not as a result)")
    a("")
    for s in d["interpretation"]:
        a(f"- {s}")
    a("")
    a(f"Run cost: {_g(m['wall_s'])} s wall, {_g(m['cpu_s'])} CPU-seconds, {m['workers']} worker processes "
      f"(`taskset -c 8-15`). Frames run: {d['counts']['frames_total']}. sha256 of the ledger: "
      f"`{m.get('json_sha256', '')}`.")
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _h1_table(a, rows: list, kk: str) -> None:
    a("| Environment | body Doppler (bins) | SNR/RE (dB) | Method | Pd [Wilson 95 %] | slow-target loss "
      "(points) | off-target frames | achieved Pfa | Doppler bias (Hz) | Doppler RMSE (Hz) | within cell |")
    a("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: (x["env"], x["snr_re_db"], x["method"], x["body_doppler_bins"])):
        p = r["pd"][kk]
        a(f"| `{r['env']}` | {_g(r['body_doppler_bins'])} | {_g(r['snr_re_db'])} | `{r['method']}` | "
          f"{_g(p['pd'])} [{_g(p['wilson95'][0])}, {_g(p['wilson95'][1])}] | "
          f"{_d(r['slow_target_loss_points'][kk])} | {_g(r['off_target_frames'][kk]['rate'])} | "
          f"{_g(r['achieved_frame_pfa'][kk])} | {_d(r['bias_doppler_hz'])} | {_d(r['rmse_doppler_hz'])} | "
          f"{_g(r['strongest_within_tol_frac'])} |")


# ------------------------------------------------------------------------------------------------------
#  Main
# ------------------------------------------------------------------------------------------------------
def _sha(path: str) -> str:
    return hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest()


def main() -> None:
    global CFG_RUN, BASES, RT_SERIES
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--quick", action="store_true", help="reduced counts for a smoke test")
    ap.add_argument("--out-json", default=OUT_JSON)
    ap.add_argument("--fig-prefix", default=FIG_PREFIX)
    ap.add_argument("--doc", default=DOC)
    ap.add_argument("--doc-from-json", action="store_true",
                    help="only rewrite --doc from the existing --out-json ledger (no trials are run)")
    args = ap.parse_args()
    if args.doc_from_json:
        full = args.out_json if os.path.isabs(args.out_json) else os.path.join(ROOT, args.out_json)
        raw = open(full, "rb").read()
        led = json.loads(raw)
        led["_meta"]["json_sha256"] = hashlib.sha256(raw).hexdigest()
        CFG_RUN = {**CFG, **led["config"]}
        write_doc(led, args.doc)
        print(f"  rewrote {args.doc} from {args.out_json}", flush=True)
        return
    t0 = time.time()
    CFG_RUN = {**CFG, **(QUICK if args.quick else {})}
    for k in ("envs", "methods", "arms", "notch_half_width_bins", "notch_wide_half_width_bins",
              "subspace", "pfa_frame"):
        CFG_RUN[k] = CFG[k]
    CFG.update(CFG_RUN)                      # workers read CFG; keep the two in step before forking
    S = SYSTEM

    cell = load_rt_cell(RT_SHARDS)
    RT_SERIES = cell.pop("E")
    n_start = len(RT_SERIES) - S.n_sym + 1
    coh, rms = [], []
    for k0 in range(n_start):
        g = rt_window(RT_SERIES, k0, S.n_sym)
        coh.append(float(abs(g.mean()) ** 2))
        rms.append(float(np.sqrt(np.mean(np.abs(RT_SERIES[k0:k0 + S.n_sym]) ** 2))))
    coh_db = 10 * np.log10(np.array(coh))
    #  Blade-flash rate: read from the rotor ledger the sweep reads, and from the airframe spec, so it is a
    #  cited quantity and not a literal. The four rotors of this record do not share one rpm, so the flash
    #  rate is a mean over four values and the spread is carried with it.
    _tj = json.load(open(os.path.join(ROOT, ROTOR_LEDGER)))["_meta"]
    _rpm = [float(v) for v in _tj["rpm_per_rotor"]]
    from drones import DRONES                                  # noqa: E402  (airframe spec, read only)
    _spec = DRONES[str(_tj.get("drone", "matrice4e"))]
    _blades = int(_spec.prop_blades)
    _flash_per_rotor = [_blades * r / 60.0 for r in _rpm]
    f_flash = float(_tj["f_flash_hz"])
    if abs(f_flash - float(np.mean(_flash_per_rotor))) > 1e-6:  # the ledger's own two entries must agree
        raise RuntimeError(f"{ROTOR_LEDGER}: f_flash_hz {f_flash} != blades x mean rpm / 60 "
                           f"{np.mean(_flash_per_rotor)}")
    #  Measured slow-time modulation of the stored record itself (no model): the spectrum of E - mean E over
    #  all positions, in dB relative to the coherent part |mean E|^2, and the share of that modulation power
    #  that falls inside each candidate blank.
    _x = RT_SERIES - RT_SERIES.mean()
    _X = np.fft.fftshift(np.fft.fft(_x) / _x.size)
    _f = np.fft.fftshift(np.fft.fftfreq(_x.size, d=1.0 / cell["prf_hz"]))
    _pw = np.abs(_X) ** 2
    _pw_db = 10 * np.log10(np.maximum(_pw / abs(RT_SERIES.mean()) ** 2, 1e-12))   # floor -120 dB
    _ord = np.argsort(-_pw)[:5]
    bin_hz = doppler_bin_hz(S)
    cell.update({
        "n_start_positions": int(n_start),
        "window_coherent_share_db_min": float(coh_db.min()), "window_coherent_share_db_max": float(coh_db.max()),
        "window_coherent_share_db_median": float(np.median(coh_db)),
        "window_rms_spread_db": float(20 * np.log10(max(rms) / min(rms))),
        "time_axis_rel_error": abs(1.0 / S.t_sym - cell["prf_hz"]) / cell["prf_hz"],
        "time_axis_frame_error_s": abs(S.n_sym / cell["prf_hz"] - S.n_sym * S.t_sym),
        "time_axis_frame_error_frac_of_position": abs(S.n_sym / cell["prf_hz"] - S.n_sym * S.t_sym) * cell["prf_hz"],
        "f_flash_hz": f_flash, "rpm_per_rotor": _rpm, "prop_blades": _blades,
        "drone_key": str(_tj.get("drone", "matrice4e")),
        "flash_per_rotor_hz": _flash_per_rotor,
        "flash_spread_hz": float(max(_flash_per_rotor) - min(_flash_per_rotor)),
        "flash_source": f"{ROTOR_LEDGER} : _meta.f_flash_hz / _meta.rpm_per_rotor; blades from src/drones.py",
        "flash_periods_per_frame": S.n_sym * S.t_sym * f_flash,
        "mod_spectrum_db": [round(float(v), 4) for v in _pw_db],
        "mod_peak_db_re_coherent": float(_pw_db[_ord[0]]), "mod_peak_hz": float(_f[_ord[0]]),
        "mod_top5_hz": [float(_f[i]) for i in _ord], "mod_top5_db": [float(_pw_db[i]) for i in _ord],
        "mod_peak_over_flash": float(abs(_f[_ord[0]]) / f_flash),
        "mod_power_frac_within_1bin": float(_pw[np.abs(_f) < CFG["notch_half_width_bins"] * bin_hz].sum()
                                            / _pw.sum()),
        "mod_power_frac_within_2bin": float(_pw[np.abs(_f) < CFG["notch_wide_half_width_bins"] * bin_hz].sum()
                                            / _pw.sum()),
        "example_window_start_index": 0})
    gex = rt_window(RT_SERIES, 0, S.n_sym)
    _Gw = np.fft.fftshift(np.fft.fft(gex - gex.mean()) / gex.size)
    _fw = np.fft.fftshift(np.fft.fftfreq(gex.size, d=S.t_sym))
    _pwd = 10 * np.log10(np.maximum(np.abs(_Gw) ** 2 / abs(gex.mean()) ** 2, 1e-12))
    cell.update({"example_window_real": gex.real.tolist(), "example_window_imag": gex.imag.tolist(),
                 "example_window_mean_real": float(gex.mean().real),
                 "example_window_mean_imag": float(gex.mean().imag),
                 "example_window_mod_peak_db": float(_pwd.max()),
                 "example_window_mod_peak_hz": float(_fw[int(np.argmax(_pwd))])})

    ctx = mp.get_context("fork")
    timing = {}
    t1 = time.time()
    chunks = []
    for e in CFG_RUN["envs"]:
        idxs = list(range(CFG_RUN["n_train"]))
        step = int(CFG_RUN["train_chunk"])
        chunks += [{"env": e, "drift_hz": CFG_RUN["envs"][e], "scene": "h0", "snr_db": P.CFG["snr_ref_db"],
                    "indices": idxs[i:i + step]} for i in range(0, len(idxs), step)]
    with ctx.Pool(args.workers) as pool:
        covs = pool.map(train_chunk, chunks)
    acc = {}
    for spec, R in zip(chunks, covs):
        acc[spec["env"]] = acc.get(spec["env"], 0) + R
    n_sub = int(len(np.flatnonzero(P.base_mask(S))[::CFG_RUN["subspace"]["subcarrier_stride"]]))
    sub_info = {}
    for e, R in acc.items():
        info = basis_from_cov(R, CFG_RUN["n_train"], n_sub)
        BASES[e] = info.pop("basis")
        sub_info[e] = info
    timing["h0_train"] = {"n_frames": len(CFG_RUN["envs"]) * CFG_RUN["n_train"], "wall_s": time.time() - t1}
    print(f"  h0_train: {timing['h0_train']['n_frames']} frames, {timing['h0_train']['wall_s']:.1f} s; "
          + ", ".join(f"{e} r={sub_info[e]['r']}" for e in sub_info), flush=True)

    specs = build_specs(CFG_RUN)
    res = {}
    with ctx.Pool(args.workers) as pool:                 # forks after BASES and RT_SERIES are set
        for exp, sp in specs.items():
            t1 = time.time()
            res[exp] = pool.map(run_frame, sp, chunksize=max(1, len(sp) // (args.workers * 8)))
            timing[exp] = {"n_frames": len(sp), "wall_s": time.time() - t1}
            print(f"  {exp}: {len(sp)} frames, {timing[exp]['wall_s']:.1f} s", flush=True)

    resn = P.resolution(S)
    cc = P.cfar_cells(S, P.RxCfg())
    n_act = int(P.base_mask(S).sum())
    out = {
        "system": {**P.CFG["system"], "fs_hz": S.fs, "t_sym_s": S.t_sym, "symbol_rate_hz": 1 / S.t_sym,
                   "cpi_s": S.n_sym * S.t_sym, "n_active": n_act, "occupied_span": cc["occupied_span"],
                   "range_resolution_m": resn["range_m"], "doppler_bin_hz": resn["doppler_bin_hz"],
                   "velocity_per_doppler_bin_mps": resn["doppler_bin_hz"] * C0 / (2 * S.fc_hz),
                   "max_range_cp_m": C0 * S.cp / S.fs / 2, "hann_lobe_bins": 2.0,
                   "processing_gain_db": 10 * math.log10(n_act * S.n_sym)},
        "config": {**{k: CFG_RUN[k] for k in ("config", "envs", "body_doppler_bins", "snr_re_db", "methods",
                                              "arms", "notch_half_width_bins", "notch_wide_half_width_bins",
                                              "subspace", "n_train", "n_cal",
                                              "n_eval", "n_h1", "pfa_frame", "n_top_candidates", "h1_range_m",
                                              "train_chunk")},
                   "clutter": P.CFG["scene"]["clutter"], "snr_ref_db": P.CFG["snr_ref_db"],
                   "receiver_default": P.CFG["receiver_default"]},
        "rt_input": cell,
        "subspace": sub_info,
    }
    out["h0"] = agg_h0(res)
    out["h1"] = agg_h1(res, out["h0"], "h1_body")
    out["h1_rt_hover"] = agg_h1(res, out["h0"], "h1_rt_hover")
    n_cond_one_method = len(CFG_RUN["envs"]) * len(CFG_RUN["body_doppler_bins"]) * len(CFG_RUN["snr_re_db"])
    out["counts"] = {
        "h1_conditions": len(CFG_RUN["methods"]) * n_cond_one_method,
        "h1_conditions_three_method_core": 3 * n_cond_one_method,
        "h1_rt_conditions": len(CFG_RUN["methods"]) * len(CFG_RUN["envs"]) * len(CFG_RUN["snr_re_db"]),
        "h0_conditions": len(CFG_RUN["methods"]) * len(CFG_RUN["arms"]) * len(CFG_RUN["envs"]),
        "frames_total": int(sum(t["n_frames"] for t in timing.values())),
        "receiver_runs": int(sum(len(r["rows"]) for v in res.values() for r in v)),
    }
    p_at = min(CFG_RUN["pfa_frame"])
    out["interval_scale"] = {
        "n_eval": CFG_RUN["n_eval"], "at_rate": p_at,
        "wilson_at_rate": P.wilson(int(round(p_at * CFG_RUN["n_eval"])), CFG_RUN["n_eval"]),
        "zero_of_n": f"0/{CFG_RUN['n_eval']}", "wilson_zero": P.wilson(0, CFG_RUN["n_eval"])}
    out["figures"] = figures(out, args.fig_prefix)
    for k, f in out["figures"].items():
        full = f["path"] if os.path.isabs(f["path"]) else os.path.join(ROOT, f["path"])
        f["sha256"] = hashlib.sha256(open(full, "rb").read()).hexdigest()

    kk = _key(min(CFG_RUN["pfa_frame"]))
    d10 = [r for r in out["h0"]["rows"] if r["env"] == "drift10"]
    best = min(d10, key=lambda r: r["frame"][kk]["rate"])
    mean_d10 = next(r for r in out["h0"]["rows"] if r["env"] == "drift10" and r["method"] == "mean_removal"
                    and r["arm"] == "static_cal")
    _pad = int(P.CFG["receiver_default"]["pad_doppler"])
    _on_grid = sum(1 for b in CFG_RUN["body_doppler_bins"] if abs(b * _pad - round(b * _pad)) < 1e-9)
    #  Share of the H1 range draw that lands within one resolution cell of a clutter path, measured on the
    #  draw interval itself (union of the intervals, so overlapping clutter is not counted twice).
    _r0, _r1 = CFG_RUN["h1_range_m"]
    _cov = np.zeros(20001, bool)
    _grid = np.linspace(_r0, _r1, _cov.size)
    for _c in P.CFG["scene"]["clutter"]:
        _cov |= np.abs(_grid - _c["range_m"]) <= resn["range_m"]
    _clut_overlap = float(_cov.mean())
    _fast = out["h1"]["reference_body_doppler_bins"]
    _slow = max([b for b in CFG_RUN["body_doppler_bins"] if b < _fast] or [_fast])   # the next level down

    def _h1row(method, arm, env, b, snr):
        return next(r for r in out["h1"]["rows"] if r["method"] == method and r["arm"] == arm
                    and r["env"] == env and r["body_doppler_bins"] == b and r["snr_re_db"] == snr)

    _snr_hi = max(CFG_RUN["snr_re_db"])
    #  The two drift10 arms the reading below names: the one with the lowest measured Pfa, and the one that
    #  keeps the most detection among the arms whose measured Pfa is not above the target (Wilson interval
    #  reaching the target or lying below it). Both are picked on measured numbers, both are named with them.
    _keep = [r for r in d10 if r["frame"][kk]["wilson95"][0] <= min(CFG_RUN["pfa_frame"])]
    _usable = min(_keep, key=lambda r: -_h1row(r["method"], r["arm"], "drift10", _fast, _snr_hi)["pd"][kk]["pd"]) \
        if _keep else None
    _best_pd = _h1row(best["method"], best["arm"], "drift10", _fast, _snr_hi)["pd"][kk]
    _best_pd_slow = _h1row(best["method"], best["arm"], "drift10", _slow, _snr_hi)["pd"][kk]
    _over = [r for r in out["h0"]["rows"]
             if r["frame"][kk]["wilson95"][0] > min(CFG_RUN["pfa_frame"])]
    out["not_shown"] = [
        "Nothing about hardware: no X410, no RF capture, no measured isolation, CFO, phase noise or ADC "
        "behaviour; the transmit permit and the 3.5 GHz carrier are working assumptions, not settings that "
        "were measured.",
        "Clutter here is three point paths whose Doppler is constant within a frame and redrawn per frame. "
        "Real foliage and traffic are not that; how site clutter moves is not known from this simulation, so "
        "which of these three environments matches a capture is open.",
        "The target is one point path with a frequency-flat gain: no rotor micro-Doppler line structure in "
        "the constant-amplitude sets, no range migration, no extended target, no frequency-dependent "
        "scattering. The hover set adds a slow-time modulation read from one stored cell; that is a "
        "flat-fading time-modulation test, not a per-path ray-traced channel.",
        f"The hover modulation comes from one cell (`{cell['stem']}`): one airframe, one range "
        f"({_g(cell['range_m'])} m), one elevation ({_g(cell['elevation_deg'])} deg), one azimuth, open sky, "
        "max_depth 2, canonical slab. Nothing here says how it changes with aspect, range or environment.",
        "H0 is synthetic clutter plus white noise. It is not a target-absent capture, so none of these "
        "thresholds transfers to a measurement.",
        f"Frame false-alarm targets were calibrated at {', '.join(_key(p) for p in CFG_RUN['pfa_frame'])} only, "
        f"from {CFG_RUN['n_cal']} calibration frames; at the {kk} target that threshold is the "
        f"{int(round(min(CFG_RUN['pfa_frame']) * CFG_RUN['n_cal']))}-th largest calibration frame statistic, so "
        "the threshold itself is coarse at this calibration size.",
        f"Only one payload configuration (`{CFG_RUN['config']}`, QPSK) was run; 16-QAM and the random-null "
        "mask of the 0917 pilot are not in this set.",
        "Both candidate-blank half-widths and the eigenvalue rule are system quantities, not values tuned on "
        "evaluation frames, and were not swept; nothing here says they are the best choices. The 2-bin width "
        "was added after the 1-bin width was seen to leave the frame statistic unchanged, so the pair is a "
        "reported comparison, not a pre-registered one.",
        "Body Doppler mostly lands on the padded Doppler grid instead of between its rows. With "
        f"pad_doppler = {_pad}, a body Doppler of b bins sits at row b x {_pad} of that grid ("
        + ", ".join(f"{_g(b)} bins at row {_g(b * _pad)}" for b in CFG_RUN["body_doppler_bins"])
        + f"), so {_on_grid} of the {len(CFG_RUN['body_doppler_bins'])} levels are exactly on a row and "
        "carry no straddle loss, which is the best case for detection. Pd here is therefore not an average "
        "over the target's position within a Doppler cell.",
        "Every H1 target is one path drawn uniformly in range over "
        f"{_g(CFG_RUN['h1_range_m'][0])}..{_g(CFG_RUN['h1_range_m'][1])} m while the three clutter paths sit "
        f"at fixed ranges, so {_g(_clut_overlap)} of the H1 frames put the target within one resolution cell "
        f"({_g(resn['range_m'])} m) of a clutter path in delay, where it is on top of a path "
        + " or ".join(f"{_g(c['power_db'])} dB" for c in P.CFG["scene"]["clutter"][1:])
        + " above it. Those frames are not separated out in any row above.",
        "Detection is scored only within one resolution cell and one Doppler bin of the target. For the "
        "hover set the target Doppler is 0, so a candidate raised by a rotor line is counted as off-target "
        "and never as Pd (section 4.4).",
    ]
    out["interpretation"] = [
        f"In `drift10` at the {kk} target, the lowest measured frame false-alarm rate of the {len(d10)} "
        f"method-arm pairs is `{best['method']}`/`{best['arm']}` at {_g(best['frame'][kk]['rate'])} "
        f"[{_g(best['frame'][kk]['wilson95'][0])}, {_g(best['frame'][kk]['wilson95'][1])}], against "
        f"{_g(mean_d10['frame'][kk]['rate'])} for `mean_removal`/`static_cal`. That is not by itself an "
        f"improvement: in the same environment and arm its Pd at {_g(_fast)} bins and SNR/RE "
        f"{_g(_snr_hi)} dB is {_g(_best_pd['pd'])} "
        f"[{_g(_best_pd['wilson95'][0])}, {_g(_best_pd['wilson95'][1])}]"
        + (f" and at {_g(_slow)} bins {_g(_best_pd_slow['pd'])} "
           f"[{_g(_best_pd_slow['wilson95'][0])}, {_g(_best_pd_slow['wilson95'][1])}]"
           if _slow != _fast else "")
        + ", so the lowest false-alarm rate in this run is bought by lowering detection as well. Section 4.2 "
        "carries the Pd of every row and is where any such trade is read.",
    ] + ([
        f"Of the {len(d10)} `drift10` pairs, {len(_keep)} have a measured false-alarm rate that is not above "
        f"the {kk} target (Wilson interval reaching the target or below it). Of those, the one with the "
        f"highest Pd at {_g(_fast)} bins and SNR/RE {_g(_snr_hi)} dB is "
        f"`{_usable['method']}`/`{_usable['arm']}`: measured Pfa {_g(_usable['frame'][kk]['rate'])} "
        f"[{_g(_usable['frame'][kk]['wilson95'][0])}, {_g(_usable['frame'][kk]['wilson95'][1])}], Pd "
        f"{_g(_h1row(_usable['method'], _usable['arm'], 'drift10', _fast, _snr_hi)['pd'][kk]['pd'])} there"
        + (f" and {_g(_h1row(_usable['method'], _usable['arm'], 'drift10', _slow, _snr_hi)['pd'][kk]['pd'])} "
           f"at {_g(_slow)} bins" if _slow != _fast else "")
        + ". Every number in that sentence is measured in this run; which of them matters for a capture is "
        "not something this run answers."] if _usable is not None else []) + ([
        "Not every threshold held on its own evaluation stream: "
        + "; ".join(f"`{r['method']}`/`{r['arm']}` in `{r['env']}` measured "
                    f"{_g(r['frame'][kk]['rate'])} [{_g(r['frame'][kk]['wilson95'][0])}, "
                    f"{_g(r['frame'][kk]['wilson95'][1])}]" for r in _over)
        + f", whose Wilson interval lies above the {kk} target, so for those rows the target was not met and "
        "the Pd in section 4.2 is read at the measured rate, not at the target."] if _over else []) + [
        "A rate measured on this evaluation set cannot be read below the interval in section 1.1; two rows "
        "whose Wilson intervals overlap are not separated by this run.",
        "Section 4.4 compares one stored cell's time variation against a constant amplitude at the same mean "
        "target power. A difference there is a property of that cell's slow-time modulation within a "
        f"{_g(S.n_sym * S.t_sym)} s window, not of hovering drones in general.",
    ]
    ru_self = resource.getrusage(resource.RUSAGE_SELF)
    ru_ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", GENERATOR, TEST_MODULE],
                           capture_output=True, text=True).stdout.strip()
    pilot_led = json.load(open(os.path.join(ROOT, "outputs/ofdm_receiver_pilot_0917.json")))
    out["_meta"] = {
        "generator": GENERATOR, "pilot": PILOT, "test_module": TEST_MODULE, "out_json": args.out_json,
        "command": "CUDA_VISIBLE_DEVICES=\"\" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 "
                   + sys.executable + " " + " ".join([GENERATOR] + sys.argv[1:]),
        "git_head": head, "generator_git_status": dirty or "clean",
        "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "quick": bool(args.quick), "workers": args.workers, "wall_s": time.time() - t0,
        "cpu_s": ru_self.ru_utime + ru_self.ru_stime + ru_ch.ru_utime + ru_ch.ru_stime, "timing": timing,
        "numpy": np.__version__,
        "sha256": {p: _sha(p) for p in (GENERATOR, PILOT, TEST_MODULE, "src/waveforms.py") + tuple(RT_SHARDS)
                   if os.path.exists(os.path.join(ROOT, p))},
        "pilot_reference": {
            "ledger": "outputs/ofdm_receiver_pilot_0917.json",
            "key": "h0.stress.h0_eval_drift10.frame[\"1e-02\"]",
            "drift10_frame_pfa": pilot_led["h0"]["stress"]["h0_eval_drift10"]["frame"]["1e-02"]["rate"],
            "drift10_hz": pilot_led["h0"]["stress"]["h0_eval_drift10"]["drift_doppler_hz"],
            "drift2_frame_pfa": pilot_led["h0"]["stress"]["h0_eval_drift2"]["frame"]["1e-02"]["rate"],
            "h1_doppler_abs_hz": pilot_led["config"]["scene"]["h1_doppler_abs_hz"]},
        "seeds": {"seed_root": CFG["seed_root"], "experiment_codes": EXP_CODES, "env_codes": ENV_CODES,
                  "layout": "SeedSequence(seed_root, spawn_key=(experiment, environment, body-Doppler code, "
                            "SNR code, index)).spawn(4) -> payload, geometry+phases, noise, null mask"},
        "scope": "numpy simulation of a monostatic OFDM-radar receiver on synthetic point-path channels, with "
                 "one slow-time modulation read from a stored PathSolver cell; no hardware, no RF measurement",
    }
    full = args.out_json if os.path.isabs(args.out_json) else os.path.join(ROOT, args.out_json)
    txt = json.dumps(out, indent=1, default=P._json_default, allow_nan=False)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(txt)
    out["_meta"]["json_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    write_doc(out, args.doc)
    print(f"  wrote {args.out_json}, {args.doc}, figures {args.fig_prefix}*; wall {time.time() - t0:.1f} s",
          flush=True)


if __name__ == "__main__":
    main()
