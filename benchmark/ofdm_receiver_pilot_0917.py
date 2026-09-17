# -*- coding: utf-8 -*-
"""
ofdm_receiver_pilot_0917.py - CPU OFDM-radar receiver pilot on synthetic delay/Doppler channels
=================================================================================================

Why
    The external review of 2026-09-17 (section 6 and section 7 item C) and docs/RESUME_0916.md section 4
    item 2 ask for a receiver check that does not depend on the ray tracer: does an OFDM-division
    receiver recover a known delay and Doppler on and off the FFT grid while payload and null
    subcarriers change, with static multipath plus a moving target, and does a CFAR threshold set on
    target-absent (H0) data hold on other H0 data? benchmark/report07_5g_waveform.py is a resource-grid
    identity test (Y = hX divided by X, no delay axis, no noise); this script adds a time-domain CP-OFDM
    channel, a delay axis, noise, clutter, H0/H1 sets and a detector.

System assumption (stated, not tested)
    Monostatic OFDM radar with its own transmitter. The receiver knows the transmitted resource grid of
    every OFDM symbol of the frame (a per-frame reference; the tiled first-frame reference failed in
    outputs/isac_plan_detection_0915.json : f14_reference). The receive FFT window is aligned to the
    transmitted symbol boundaries. Not modelled: TX-to-RX leakage, CFO, phase noise, clock drift, ADC
    quantisation or clipping, range migration inside a frame, antenna patterns and angles. Every path
    is a point with one delay, one constant Doppler and one frequency-flat complex gain.

Waveform (NR-structured, not standard compliant; values in CFG["system"])
    Subcarrier spacing, FFT size and sample rate follow the NR 30 kHz numerology at the native
    30.72 Msps raster. The resource-grid mask follows the sionna.phy.ofdm.ResourceGrid convention
    (guard carriers left/right, optional DC null at index fft/2; src/waveforms_sionna.py uses the same
    class). NR does not reserve the DC subcarrier; the DC null here is a mask choice. Every CP has the
    same length (the longer first-symbol CP of a slot is not modelled), so slow time is sampled
    uniformly. Payload: QPSK or 16-QAM from src/waveforms.py rand_qam (unit mean energy), a new draw for
    every resource element of every symbol; OFDM modulation with src/waveforms.py ofdm_modulate
    (unitary IFFT + CP).

Receiver (function receiver_grid; it has no truth argument)
    1. CP removal and unitary FFT per symbol, centred subcarrier order (demod).
    2. Division by the per-frame reference on active subcarriers only. Null and guard subcarriers are
       masked: they are never divided and their channel estimate is zero.
    3. Static removal: subtract the slow-time mean per subcarrier (MOBICOM plan section 4 step 3).
    4. Separable window (Hann by default) over the occupied subcarrier span and over slow time; null
       subcarriers keep weight zero. The map is normalised so that a unit on-grid path peaks at 1.
    5. Delay transform: inverse FFT over subcarriers, zero-padded by pad_delay. Search region set by the
       system, never by truth: delays from zero to the CP duration.
    6. Doppler transform: FFT over slow time (every stride-th symbol), zero-padded by pad_doppler.
    7. CA-CFAR on power with guard and training boxes (Doppler axis cyclic, delay axis with margin
       cells outside the search region); statistic T = P / mean(training P).
    8. Candidates are local maxima of P (8 neighbours) in the search region; a detection is a
       candidate with T above the threshold. Peak interpolation: 3-point parabola on log power per axis.

Channels
    channel_time: time-domain CP-OFDM stream; each path delayed by the frequency-domain phase ramp over
    the whole frame (the method of src/passive_process.py make_cpi and src/radar_process.py
    _delay_doppler) and multiplied by exp(j 2 pi f_D t); AWGN per sample. channel_grid: grid-level
    control Y = H X + N with the same delay/Doppler phases and no inter-carrier interference or
    fractional-delay tails. Scenes: one target (on or off grid); static clutter (three zero-Doppler
    paths stronger than the target) plus a moving target plus a target-borne second path with its own
    delay and Doppler ("ghost", Doppler-carrying multipath); H0 = the same static clutter without target
    or ghost; H0 stress sets with 20 dB less noise and with clutter carrying a small Doppler.

Evaluation
    Noise-free: estimation error of the strongest candidate against truth (on grid, delay-only,
    Doppler-only and joint off-grid offsets; several payload seeds, both null masks, both channel
    models; receiver knob variants). A stale-reference control divides by the first symbol tiled over
    the frame. Detection: thresholds (frame-level and cell-level) are set from calibration H0 seeds only
    and false-alarm rates are counted on disjoint evaluation H0 seeds (a bootstrap over the calibration frames
    shows how far the threshold moves with a calibration set of that size); Pd versus per-resource-element SNR
    on H1 seeds with random target delay and Doppler. A noise-free control repeats the fixed clutter scene
    without the second path, and noise-free clutter-only frames (static and drifting clutter, with and
    without static removal) record how much clutter reaches the map in H0. Truth is used only in score().
    Repetition rate:
    the receiver uses only every k-th symbol as reference and the Doppler estimate is compared with the
    alias predicted by the sampling theorem.

Run (about half a core-hour; 6 worker processes)
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 \
        /workspace/.venvs/py312/bin/python benchmark/ofdm_receiver_pilot_0917.py --workers 6
    --quick runs reduced counts; give --out-json/--fig-prefix/--doc elsewhere for a smoke test.
    --doc-from-json rewrites docs/OFDM_PILOT_0917.md from the existing ledger without running trials.

Outputs
    outputs/ofdm_receiver_pilot_0917.json, outputs/figures/ofdm_pilot_0917_{map,offgrid,rmse,pd}.png,
    docs/OFDM_PILOT_0917.md (generated from the JSON by this script; do not edit by hand).
Tests
    benchmark/test_ofdm_receiver_pilot_0917.py (python benchmark/test_ofdm_receiver_pilot_0917.py)
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import multiprocessing as mp
import os
import resource
import subprocess
import sys
import time
from dataclasses import dataclass

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
from waveforms import ofdm_modulate, rand_qam  # noqa: E402  (numpy-only module)

C0 = 299792458.0
GENERATOR = "benchmark/ofdm_receiver_pilot_0917.py"
TEST_MODULE = "benchmark/test_ofdm_receiver_pilot_0917.py"
OUT_JSON = "outputs/ofdm_receiver_pilot_0917.json"
FIG_PREFIX = "outputs/figures/ofdm_pilot_0917_"
DOC = "docs/OFDM_PILOT_0917.md"
LINK_BUDGET = "outputs/isac_plan_link_budget_0915.json"
LOGIC_REVIEW = "outputs/research_logic_review_0916.json"

CFG = {
    "seed_root": 20260917,
    "system": {"fc_hz": 3.5e9, "scs_hz": 30e3, "fft": 1024, "cp": 72, "n_sym": 256,
               "guard": [206, 205], "dc_null": True},
    "configs": {
        "qpsk_dcguard": {"modulation": "qpsk", "random_null_frac": 0.0},
        "16qam_dcguard": {"modulation": "16qam", "random_null_frac": 0.0},
        "qpsk_dcguard_rand10": {"modulation": "qpsk", "random_null_frac": 0.10},
    },
    "receiver_default": {"window": "hann", "interp": "logparabola", "pad_delay": 2, "pad_doppler": 2,
                         "static_removal": True, "stride": 1},
    "knobs": {
        "hann_logpar_pad2": {},
        "hann_par_pad2": {"interp": "parabola"},
        "hann_logpar_pad1": {"pad_delay": 1, "pad_doppler": 1},
        "rect_par_pad1": {"window": "rect", "interp": "parabola", "pad_delay": 1, "pad_doppler": 1},
        "hann_none_pad2": {"interp": "none"},
        "hann_logpar_pad2_noremoval": {"static_removal": False},
    },
    "scene": {
        "clutter": [{"range_m": 18.0, "power_db": 30.0}, {"range_m": 61.5, "power_db": 24.0},
                    {"range_m": 143.2, "power_db": 18.0}],
        "ghost": {"extra_range_m": 16.0, "doppler_factor": 0.93, "power_db": -6.0},
        "fixed_target": {"range_m": 99.0, "speed_mps": 9.1},
        "h1_range_m": [40.0, 320.0],
        "h1_doppler_abs_hz": [300.0, 5000.0],
        "drift_doppler_hz": [2.0, 10.0],
    },
    "offgrid": {"q0_samples": 20, "k0_bins": 2, "offsets": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
                "n_payload_seeds": 4},
    "clutter_noise_free_seeds": 4,
    "h0_clutter_noise_free_seeds": 2,
    "stale": {"q_samples": 20.3, "k_bins": 2.4, "n_seeds": 2},
    "stride": {"n_sym": 560, "strides": [1, 2, 4, 7, 14, 28, 56], "snr_db": -30.0,
               "n_clean": 2, "n_noisy": 8},
    "snr_ref_db": -35.0,
    "lownoise_snr_ref_db": -15.0,
    "snr_grid_db": [-46.0, -44.0, -42.0, -40.0, -38.0, -36.0, -34.0, -32.0, -30.0, -28.0, -26.0],
    "n_cal": 1000, "n_eval": 1000, "n_eval_stress": 300, "n_h1": 150,
    "pfa_frame": [0.1, 0.01], "pfa_cell": [1e-4, 1e-5], "t_floor": 6.0,
    "n_top_candidates": 64,
    "map_snr_db": -22.0,
    "rmse_min_within_tol_frac": 0.9,
    "n_bootstrap": 2000,
}
QUICK = {"n_cal": 60, "n_eval": 60, "n_eval_stress": 20, "n_h1": 12,
         "snr_grid_db": [-42.0, -36.0, -30.0], "clutter_noise_free_seeds": 1, "h0_clutter_noise_free_seeds": 1,
         "offgrid": {"q0_samples": 20, "k0_bins": 2, "offsets": [0.0, 0.3, 0.5], "n_payload_seeds": 1},
         "stride": {"n_sym": 560, "strides": [1, 14, 56], "snr_db": -30.0, "n_clean": 1, "n_noisy": 2}}

EXP_CODES = {"nf_offgrid": 1, "nf_clutter": 2, "nf_stale": 3, "stride": 4, "nf_h0_clutter": 5, "h0_cal": 10, "h0_eval": 11,
             "h0_eval_lownoise": 12, "h0_eval_drift2": 13, "h0_eval_drift10": 14, "h1": 20, "map": 30}
CONFIG_CODES = {"qpsk_dcguard": 0, "16qam_dcguard": 1, "qpsk_dcguard_rand10": 2}


# ----------------------------------------------------------------------------------------------------
#  System, masks, payload, modulation
# ----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class System:
    fc_hz: float
    scs_hz: float
    fft: int
    cp: int
    n_sym: int
    guard: tuple
    dc_null: bool

    @property
    def fs(self) -> float:
        return self.fft * self.scs_hz

    @property
    def t_sym(self) -> float:
        return (self.fft + self.cp) / self.fs


def build_system(d: dict) -> System:
    return System(float(d["fc_hz"]), float(d["scs_hz"]), int(d["fft"]), int(d["cp"]), int(d["n_sym"]),
                  tuple(int(x) for x in d["guard"]), bool(d["dc_null"]))


def base_mask(S: System) -> np.ndarray:
    """Active subcarriers in centred order, sionna ResourceGrid.effective_subcarrier_ind convention."""
    idx = np.arange(S.guard[0], S.fft - S.guard[1])
    if S.dc_null:
        idx = idx[idx != S.fft // 2]
    m = np.zeros(S.fft, bool)
    m[idx] = True
    return m


def make_mask(S: System, random_null_frac: float, rng) -> np.ndarray:
    """Base mask plus random in-band nulls; the first and last active subcarriers are never nulled so
    the occupied span (and with it the window and CFAR geometry) stays that of the base mask."""
    m = base_mask(S)
    if random_null_frac > 0:
        act = np.flatnonzero(m)[1:-1]
        k = int(math.floor(random_null_frac * (len(act) + 2)))
        m[rng.choice(act, k, replace=False)] = False
    return m


def payload(rng, S: System, mask: np.ndarray, modulation: str, n_sym: int) -> np.ndarray:
    order = {"qpsk": 4, "16qam": 16}[modulation]
    X = np.zeros((n_sym, S.fft), complex)
    X[:, mask] = rand_qam(rng, n_sym * int(mask.sum()), order=order).reshape(n_sym, -1)
    return X


def tx_time(X: np.ndarray, S: System) -> np.ndarray:
    return ofdm_modulate(X, S.fft, S.cp)


def demod(rx: np.ndarray, S: System, n_sym: int) -> np.ndarray:
    blk = rx[: n_sym * (S.fft + S.cp)].reshape(n_sym, S.fft + S.cp)[:, S.cp:]
    return np.fft.fftshift(np.fft.fft(blk, axis=1), axes=1) / np.sqrt(S.fft)


# ----------------------------------------------------------------------------------------------------
#  Channels
# ----------------------------------------------------------------------------------------------------
def channel_time(tx: np.ndarray, S: System, paths: list, noise_var: float, rng) -> np.ndarray:
    """Sum of delayed, Doppler-shifted copies of the TX stream plus AWGN (variance noise_var per sample).
    Fractional delay: phase ramp over the FFT of the whole frame, as in src/passive_process.py make_cpi."""
    L = len(tx)
    f = np.fft.fftfreq(L, d=1.0 / S.fs)
    spec = np.fft.fft(tx)
    n = np.arange(L)
    rx = np.zeros(L, complex)
    static = [p for p in paths if p["f_hz"] == 0.0]
    if static:
        ramp = np.zeros(L, complex)
        for p in static:
            ramp += p["amp"] * np.exp(-2j * np.pi * f * p["tau_s"])
        rx += np.fft.ifft(spec * ramp)
    for p in paths:
        if p["f_hz"] != 0.0:
            rx += (p["amp"] * np.fft.ifft(spec * np.exp(-2j * np.pi * f * p["tau_s"]))
                   * np.exp(2j * np.pi * p["f_hz"] * n / S.fs))
    if noise_var > 0:
        rx += np.sqrt(noise_var / 2) * (rng.standard_normal(L) + 1j * rng.standard_normal(L))
    return rx


def channel_grid(X: np.ndarray, S: System, paths: list, noise_var: float, rng) -> np.ndarray:
    """Grid-level control: Y = H X + N, Doppler phase taken at the centre of each FFT window."""
    M, N = X.shape
    nc = np.arange(N) - N // 2
    tm = (np.arange(M) * (N + S.cp) + S.cp + (N - 1) / 2) / S.fs
    H = np.zeros((M, N), complex)
    for p in paths:
        H += p["amp"] * np.exp(2j * np.pi * p["f_hz"] * tm)[:, None] \
            * np.exp(-2j * np.pi * nc * S.scs_hz * p["tau_s"])[None, :]
    Y = H * X
    if noise_var > 0:
        Y = Y + np.sqrt(noise_var / 2) * (rng.standard_normal(Y.shape) + 1j * rng.standard_normal(Y.shape))
    return Y


# ----------------------------------------------------------------------------------------------------
#  Receiver (no truth anywhere below until score())
# ----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class RxCfg:
    window: str = "hann"
    interp: str = "logparabola"
    pad_delay: int = 2
    pad_doppler: int = 2
    static_removal: bool = True
    stride: int = 1


def cfar_cells(S: System, cfg: RxCfg) -> dict:
    """Guard half-widths cover the window main lobe (2 resolution cells for Hann, 1 for rect) in padded
    cells; training half-widths add twice the guard."""
    act = np.flatnonzero(base_mask(S))
    span = int(act[-1] - act[0] + 1)
    lobe = 2.0 if cfg.window == "hann" else 1.0
    gd = int(math.ceil(lobe * cfg.pad_doppler))
    gt = int(math.ceil(lobe * S.fft / span * cfg.pad_delay))
    td, tt = 2 * gd, 2 * gt
    n_train = (2 * (gd + td) + 1) * (2 * (gt + tt) + 1) - (2 * gd + 1) * (2 * gt + 1)
    return {"guard_doppler": gd, "train_doppler": td, "guard_delay": gt, "train_delay": tt,
            "n_train": int(n_train), "occupied_span": span}


def _offset(ym: float, y0: float, yp: float, mode: str) -> float:
    if mode == "none":
        return 0.0
    if mode == "logparabola":
        ym, y0, yp = (math.log(max(v, 1e-300)) for v in (ym, y0, yp))
    elif mode == "parabola":
        ym, y0, yp = (math.sqrt(max(v, 0.0)) for v in (ym, y0, yp))
    else:
        raise ValueError(mode)
    den = ym - 2.0 * y0 + yp
    if not den < 0:
        return 0.0
    return float(min(0.5, max(-0.5, 0.5 * (ym - yp) / den)))


def receiver_grid(Y: np.ndarray, X_ref: np.ndarray, mask: np.ndarray, S: System, cfg: RxCfg,
                  keep_floor: float | None = None, n_top: int = 64, return_map: bool = False) -> dict:
    k = int(cfg.stride)
    Yk, Xk = Y[::k], X_ref[::k]
    M, N = Yk.shape
    act = np.flatnonzero(mask)
    H = np.zeros((M, N), complex)
    H[:, act] = Yk[:, act] / Xk[:, act]                       # nulls and guards: masked, not divided
    if cfg.static_removal:
        H[:, act] -= H[:, act].mean(axis=0, keepdims=True)
    occ = np.flatnonzero(base_mask(S))
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
    cc = cfar_cells(S, cfg)
    gd, td, gt, tt = cc["guard_doppler"], cc["train_doppler"], cc["guard_delay"], cc["train_delay"]
    n_s = cfg.pad_delay * S.cp + 1                            # delay cells 0 .. CP duration
    marg = gt + tt + 1
    prof = (np.fft.ifft(G, axis=1) * D)[:, np.arange(-marg, n_s + marg) % D]
    Mp = cfg.pad_doppler * M
    Z = np.fft.fftshift(np.fft.fft(prof, n=Mp, axis=0), axes=0) / norm
    P = Z.real ** 2 + Z.imag ** 2
    f_axis = np.fft.fftshift(np.fft.fftfreq(Mp, d=k * S.t_sym))
    tau_axis = np.arange(n_s) / (D * S.scs_hz)

    rd = gd + td
    Pw = np.concatenate([P[-(rd + 1):], P, P[:rd + 1]], axis=0)       # Doppler axis is cyclic
    integ = np.zeros((Pw.shape[0] + 1, Pw.shape[1] + 1))
    integ[1:, 1:] = Pw.cumsum(axis=0).cumsum(axis=1)
    r = np.arange(Mp) + rd + 1
    c = np.arange(n_s) + marg

    def box(hr: int, hc: int) -> np.ndarray:
        r0, r1 = (r - hr)[:, None], (r + hr + 1)[:, None]
        c0, c1 = (c - hc)[None, :], (c + hc + 1)[None, :]
        return integ[r1, c1] - integ[r0, c1] - integ[r1, c0] + integ[r0, c0]

    noise = (box(rd, gt + tt) - box(gd, gt)) / cc["n_train"]
    Ps = P[:, marg:marg + n_s]
    T = Ps / np.maximum(noise, 1e-300)

    Pn = Pw[rd:rd + Mp + 2, marg - 1:marg + n_s + 1]
    ismax = Ps > 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                ismax &= Ps >= Pn[1 + di:Pn.shape[0] - 1 + di, 1 + dj:Pn.shape[1] - 1 + dj]
    ci, cj = np.nonzero(ismax)

    def est(i: int, j: int) -> dict:
        jj = j + marg
        dm = _offset(P[(i - 1) % Mp, jj], P[i, jj], P[(i + 1) % Mp, jj], cfg.interp)
        dt = _offset(P[i, jj - 1], P[i, jj], P[i, jj + 1], cfg.interp)
        return {"tau_s": (j + dt) / (D * S.scs_hz), "f_hz": float(f_axis[i] + dm / (Mp * k * S.t_sym)),
                "P": float(P[i, jj]), "T": float(T[i, j]), "i": int(i), "j": int(j)}

    out = {"n_search": int(Ps.size), "mean_P": float(Ps.mean()), "frame_stat": 0.0, "strongest": None,
           "top": [], "psl_db": None, "top_T_cut": 0.0}
    zero_rows = np.abs(f_axis) < 1.0 / (M * k * S.t_sym)
    out["zero_doppler_max_P"] = float(Ps[zero_rows].max())
    out["max_P"] = float(Ps.max())
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
    if keep_floor is not None:
        out["t_floor"] = T[T > keep_floor].astype(np.float32)
    if return_map:
        out["map"] = {"P": Ps, "f_axis": f_axis, "tau_axis": tau_axis}
    return out


# ----------------------------------------------------------------------------------------------------
#  Scenes and scoring (truth lives only here)
# ----------------------------------------------------------------------------------------------------
def doppler_hz(speed_mps: float, fc_hz: float) -> float:
    return 2.0 * speed_mps * fc_hz / C0


def _path(range_m: float, f_hz: float, power_db: float, phase: float) -> dict:
    return {"tau_s": 2.0 * range_m / C0, "f_hz": float(f_hz),
            "amp": 10 ** (power_db / 20) * np.exp(1j * phase)}


def build_scene(spec: dict, S: System, rng) -> tuple[list, dict]:
    sc = CFG["scene"]
    scene = spec["scene"]
    paths, truth = [], {"target": None, "ghost": None}
    if scene.startswith("clutter"):
        for cl in sc["clutter"]:
            fd = rng.uniform(-spec["drift_hz"], spec["drift_hz"]) if scene == "clutter_h0_drift" else 0.0
            paths.append(_path(cl["range_m"], fd, cl["power_db"], rng.uniform(0, 2 * np.pi)))
    if scene == "single":
        g = spec["geometry"]
        tau = g["q"] / S.fs
        f = g["kbin"] / (S.n_sym * S.t_sym) if "kbin" in g else g["f_hz"]
        truth["target"] = {"range_m": C0 * tau / 2, "f_hz": f}
    elif scene == "clutter_h1_fixed":
        ft = sc["fixed_target"]
        truth["target"] = {"range_m": ft["range_m"], "f_hz": doppler_hz(ft["speed_mps"], S.fc_hz)}
    elif scene == "clutter_h1_random":
        f = rng.uniform(*sc["h1_doppler_abs_hz"]) * (1 if rng.random() < 0.5 else -1)
        truth["target"] = {"range_m": rng.uniform(*sc["h1_range_m"]), "f_hz": f}
    if truth["target"] is not None:
        t = truth["target"]
        paths.append(_path(t["range_m"], t["f_hz"], 0.0, rng.uniform(0, 2 * np.pi)))
        if scene.startswith("clutter_h1") and spec.get("ghost", True):
            gh = sc["ghost"]
            truth["ghost"] = {"range_m": t["range_m"] + gh["extra_range_m"], "f_hz": t["f_hz"] * gh["doppler_factor"]}
            paths.append(_path(truth["ghost"]["range_m"], truth["ghost"]["f_hz"], gh["power_db"],
                               rng.uniform(0, 2 * np.pi)))
    return paths, truth


def resolution(S: System) -> dict:
    span = cfar_cells(S, RxCfg())["occupied_span"]
    return {"range_m": C0 / (2 * span * S.scs_hz), "doppler_hz": 1.0 / (S.n_sym * S.t_sym),
            "range_bin_m": C0 / (2 * S.fs), "doppler_bin_hz": 1.0 / (S.n_sym * S.t_sym)}


def score(out: dict, truth: dict, S: System, cfg: RxCfg) -> dict:
    res = resolution(S)
    F = 1.0 / (cfg.stride * S.t_sym)

    def err(e: dict, tr: dict) -> tuple[float, float]:
        return C0 * e["tau_s"] / 2 - tr["range_m"], ((e["f_hz"] - tr["f_hz"] + F / 2) % F) - F / 2

    def near(e: dict, tr: dict | None) -> bool:
        if tr is None:
            return False
        dr, df = err(e, tr)
        return abs(dr) <= res["range_m"] and abs(df) <= res["doppler_hz"]

    rec = {k: out[k] for k in ("frame_stat", "mean_P", "max_P", "psl_db", "zero_doppler_max_P", "n_search")}
    rec["top_T_cut"] = out["top_T_cut"]
    if "t_floor" in out:
        rec["t_floor"] = out["t_floor"]
    st = out["strongest"]
    rec["strongest_f_hz"] = None if st is None else st["f_hz"]
    for name in ("target", "ghost"):
        tr = truth[name]
        if tr is None:
            continue
        cand = [e for e in out["top"] if near(e, tr)]
        best = max(cand, key=lambda e: e["P"]) if cand else None
        rec[f"{name}_T"] = best["T"] if best else 0.0
        rec[f"{name}_P"] = best["P"] if best else 0.0
        rec[f"{name}_err"] = list(err(best, tr)) if best else None
    tgt = truth["target"]
    if tgt is not None and st is not None:
        dr, df = err(st, tgt)
        rec["strongest"] = {"range_err_m": dr, "doppler_err_hz": df, "within_tol": near(st, tgt), "P": st["P"]}
        rec["f_true_hz"] = tgt["f_hz"]
        rec["f_alias_pred_hz"] = tgt["f_hz"] - F * round(tgt["f_hz"] / F)
    rec["off_T"] = [[e["T"], abs(e["f_hz"]) < res["doppler_hz"]] for e in out["top"]
                    if not near(e, truth["target"]) and not near(e, truth["ghost"])]
    return rec


# ----------------------------------------------------------------------------------------------------
#  Trials
# ----------------------------------------------------------------------------------------------------
SYSTEM = build_system(CFG["system"])


def run_trial(spec: dict) -> dict:
    S = dataclasses.replace(SYSTEM, n_sym=int(spec.get("n_sym") or SYSTEM.n_sym))
    ss = np.random.SeedSequence(CFG["seed_root"], spawn_key=tuple(int(v) for v in spec["key"]))
    r_pay, r_geo, r_noise, r_null = (np.random.default_rng(s) for s in ss.spawn(4))
    conf = CFG["configs"][spec["config"]]
    mask = make_mask(S, conf["random_null_frac"], r_null)
    X = payload(r_pay, S, mask, conf["modulation"], S.n_sym)
    paths, truth = build_scene(spec, S, r_geo)
    noise_var = 0.0 if spec["snr_db"] is None else 10 ** (-spec["snr_db"] / 10)
    if spec["model"] == "time":
        Y = demod(channel_time(tx_time(X, S), S, paths, noise_var, r_noise), S, S.n_sym)
    else:
        Y = channel_grid(X, S, paths, noise_var, r_noise)
    rows = {}
    for label, rxd, stale in spec["receivers"]:
        cfg = RxCfg(**{**CFG["receiver_default"], **rxd})
        Xref = np.tile(X[:1], (S.n_sym, 1)) if stale else X
        out = receiver_grid(Y, Xref, mask, S, cfg, keep_floor=spec.get("keep_floor"),
                            n_top=CFG["n_top_candidates"], return_map=spec.get("return_map", False))
        rows[label] = score(out, truth, S, cfg)
        if spec.get("return_map"):
            rows[label]["map"] = out["map"]
    return {"spec": {k: v for k, v in spec.items() if k != "receivers"}, "rows": rows}


def default_rx(label: str = "default") -> list:
    return [(label, {}, False)]


def build_specs(cfg: dict, strides_f: list) -> dict:
    g = {}
    og = cfg["offgrid"]
    knobs = [(k, v, False) for k, v in cfg["knobs"].items()]
    geoms = [("delay", o, 0.0) for o in og["offsets"]] + [("doppler", 0.0, o) for o in og["offsets"][1:]] \
        + [("both", o, o) for o in og["offsets"][1:]]
    g["nf_offgrid"] = [
        {"exp": "nf_offgrid", "config": c, "model": m, "key": (EXP_CODES["nf_offgrid"], CONFIG_CODES[c], s, 0),
         "snr_db": None, "scene": "single", "sweep": sw, "dq": dq, "dk": dk,
         "geometry": {"q": og["q0_samples"] + dq, "kbin": og["k0_bins"] + dk}, "receivers": knobs}
        for c in cfg["configs"] for m in ("grid", "time") for s in range(og["n_payload_seeds"]) for sw, dq, dk in geoms]
    g["nf_clutter"] = [
        {"exp": "nf_clutter", "config": c, "model": m, "key": (EXP_CODES["nf_clutter"], CONFIG_CODES[c], s, 0),
         "snr_db": None, "scene": "clutter_h1_fixed", "ghost": gh, "receivers": default_rx()}
        for c in cfg["configs"] for m in ("grid", "time") for s in range(cfg["clutter_noise_free_seeds"])
        for gh in (True, False)]
    nh = cfg["h0_clutter_noise_free_seeds"]
    g["nf_h0_clutter"] = [
        {"exp": "nf_h0_clutter", "config": c, "model": m, "key": (EXP_CODES["nf_h0_clutter"], CONFIG_CODES[c], s, 0),
         "snr_db": None, "scene": "clutter_h0", "drift_hz": 0.0,
         "receivers": [("default", {}, False), ("no_static_removal", {"static_removal": False}, False)]}
        for c in cfg["configs"] for m in ("grid", "time") for s in range(nh)] + [
        {"exp": "nf_h0_clutter", "config": "qpsk_dcguard", "model": "time",
         "key": (EXP_CODES["nf_h0_clutter"], CONFIG_CODES["qpsk_dcguard"], s, j + 1),
         "snr_db": None, "scene": "clutter_h0_drift", "drift_hz": dh, "receivers": default_rx()}
        for j, dh in enumerate(cfg["scene"]["drift_doppler_hz"]) for s in range(nh)]
    st = cfg["stale"]
    g["nf_stale"] = [
        {"exp": "nf_stale", "config": c, "model": "time", "key": (EXP_CODES["nf_stale"], CONFIG_CODES[c], s, 0),
         "snr_db": None, "scene": "single", "geometry": {"q": st["q_samples"], "kbin": st["k_bins"]},
         "receivers": [("per_frame_reference", {}, False), ("stale_first_symbol", {}, True)]}
        for c in ("qpsk_dcguard", "16qam_dcguard") for s in range(st["n_seeds"])]
    sd = cfg["stride"]
    base_st = {"exp": "stride", "config": "qpsk_dcguard", "model": "time", "n_sym": sd["n_sym"], "scene": "single"}
    g["stride"] = [
        {**base_st, "key": (EXP_CODES["stride"], fi, 0 if snr is None else 1, s), "snr_db": snr,
         "snr_mode": "noise-free" if snr is None else "same SNR per RE",
         "geometry": {"q": cfg["offgrid"]["q0_samples"], "f_hz": fv}, "f_label": fl,
         "receivers": [(f"k{k}", {"stride": k}, False) for k in sd["strides"]]}
        for fi, (fl, fv) in enumerate(strides_f)
        for snr, n in ((None, sd["n_clean"]), (sd["snr_db"], sd["n_noisy"])) for s in range(n)] + [
        {**base_st, "key": (EXP_CODES["stride"], fi, 2, s, k), "snr_db": sd["snr_db"] + 10 * math.log10(k),
         "snr_mode": "same integrated SNR", "geometry": {"q": cfg["offgrid"]["q0_samples"], "f_hz": fv},
         "f_label": fl, "receivers": [(f"k{k}", {"stride": k}, False)]}
        for fi, (fl, fv) in enumerate(strides_f) for k in sd["strides"] for s in range(sd["n_noisy"])]
    for exp, n, scene, snr, confs in (
            ("h0_cal", cfg["n_cal"], "clutter_h0", cfg["snr_ref_db"], list(cfg["configs"])),
            ("h0_eval", cfg["n_eval"], "clutter_h0", cfg["snr_ref_db"], list(cfg["configs"])),
            ("h0_eval_lownoise", cfg["n_eval_stress"], "clutter_h0", cfg["lownoise_snr_ref_db"], ["qpsk_dcguard"]),
            ("h0_eval_drift2", cfg["n_eval_stress"], "clutter_h0_drift", cfg["snr_ref_db"], ["qpsk_dcguard"]),
            ("h0_eval_drift10", cfg["n_eval_stress"], "clutter_h0_drift", cfg["snr_ref_db"], ["qpsk_dcguard"])):
        drift = {"h0_eval_drift2": cfg["scene"]["drift_doppler_hz"][0],
                 "h0_eval_drift10": cfg["scene"]["drift_doppler_hz"][1]}.get(exp, 0.0)
        g[exp] = [{"exp": exp, "config": c, "model": "time", "key": (EXP_CODES[exp], CONFIG_CODES[c], i, 0),
                   "snr_db": snr, "scene": scene, "drift_hz": drift, "keep_floor": cfg["t_floor"],
                   "receivers": default_rx()}
                  for c in confs for i in range(n)]
    g["h1"] = [{"exp": "h1", "config": c, "model": "time",
                "key": (EXP_CODES["h1"], CONFIG_CODES[c], int(round((snr + 100) * 10)), i),
                "snr_db": snr, "scene": "clutter_h1_random", "receivers": default_rx()}
               for c in cfg["configs"] for snr in cfg["snr_grid_db"] for i in range(cfg["n_h1"])]
    return g


# ----------------------------------------------------------------------------------------------------
#  Aggregation
# ----------------------------------------------------------------------------------------------------
ROUNDOFF_DB = -200.0                     # map values below this (re a unit target) are printed as round-off
WILSON_LEVEL_PCT = 95
WILSON_Z = 1.959963985


def wilson(k: int, n: int, z: float = WILSON_Z) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, centre - half), min(1.0, centre + half)]


def _key(p: float) -> str:
    return f"{p:.0e}"


def agg_offgrid(results: list, S: System) -> dict:
    res = resolution(S)
    groups = {}
    for r in results:
        sp = r["spec"]
        for label, row in r["rows"].items():
            k = (sp["config"], sp["model"], label, sp["sweep"], sp["dq"], sp["dk"])
            groups.setdefault(k, []).append(row)
    rows = []
    for (c, m, label, sw, dq, dk), rr in sorted(groups.items()):
        er = np.array([x["strongest"]["range_err_m"] for x in rr])
        ef = np.array([x["strongest"]["doppler_err_hz"] for x in rr])
        rows.append({"config": c, "model": m, "receiver": label, "sweep": sw, "delay_offset_bins": dq,
                     "doppler_offset_bins": dk, "n_payload_seeds": len(rr),
                     "range_err_mean_m": float(er.mean()), "range_err_maxabs_m": float(np.abs(er).max()),
                     "range_err_spread_m": float(er.max() - er.min()),
                     "doppler_err_mean_hz": float(ef.mean()), "doppler_err_maxabs_hz": float(np.abs(ef).max()),
                     "doppler_err_spread_hz": float(ef.max() - ef.min()),
                     "range_err_maxabs_bins": float(np.abs(er).max() / res["range_bin_m"]),
                     "doppler_err_maxabs_bins": float(np.abs(ef).max() / res["doppler_bin_hz"]),
                     "psl_db_max": float(max(x["psl_db"] for x in rr)),
                     "all_within_tol": bool(all(x["strongest"]["within_tol"] for x in rr))})
    summ = {}
    for label in CFG["knobs"]:
        for m in ("grid", "time"):
            sel = [x for x in rows if x["receiver"] == label and x["model"] == m]
            if not sel:
                continue
            on = [x for x in sel if x["delay_offset_bins"] == 0 and x["doppler_offset_bins"] == 0]
            summ[f"{label}|{m}"] = {
                "on_grid_range_err_maxabs_m": max(x["range_err_maxabs_m"] for x in on),
                "on_grid_doppler_err_maxabs_hz": max(x["doppler_err_maxabs_hz"] for x in on),
                "all_range_err_maxabs_m": max(x["range_err_maxabs_m"] for x in sel),
                "all_doppler_err_maxabs_hz": max(x["doppler_err_maxabs_hz"] for x in sel),
                "all_range_err_maxabs_bins": max(x["range_err_maxabs_bins"] for x in sel),
                "all_doppler_err_maxabs_bins": max(x["doppler_err_maxabs_bins"] for x in sel),
                "max_payload_spread_range_m": max(x["range_err_spread_m"] for x in sel),
                "max_payload_spread_doppler_hz": max(x["doppler_err_spread_hz"] for x in sel),
                "psl_db_max": max(x["psl_db_max"] for x in sel),
                "all_within_tol": all(x["all_within_tol"] for x in sel)}
    return {"rows": rows, "summary": summ}


def agg_clutter(results: list) -> dict:
    groups = {}
    for r in results:
        groups.setdefault((r["spec"]["config"], r["spec"]["model"], r["spec"]["ghost"]), []).append(r["rows"]["default"])
    rows = []
    for (c, m, gh), rr in sorted(groups.items()):
        found = [x for x in rr if x.get("ghost_err") is not None and x["target_P"] > 0]
        lev = [float(10 * np.log10(x["ghost_P"] / x["target_P"])) for x in found]
        rows.append({"config": c, "model": m, "second_path": gh, "n_seeds": len(rr),
                     "target_range_err_maxabs_m": float(max(abs(x["strongest"]["range_err_m"]) for x in rr)),
                     "target_doppler_err_maxabs_hz": float(max(abs(x["strongest"]["doppler_err_hz"]) for x in rr)),
                     "strongest_is_target_all": all(x["strongest"]["within_tol"] for x in rr),
                     "ghost_found": len(found),
                     "ghost_level_db_min": min(lev) if lev else None,
                     "ghost_level_db_max": max(lev) if lev else None,
                     "ghost_range_err_maxabs_m": float(max(abs(x["ghost_err"][0]) for x in found)) if found else None,
                     "ghost_doppler_err_maxabs_hz": float(max(abs(x["ghost_err"][1]) for x in found)) if found else None,
                     "zero_doppler_band_max_db_re_target": float(max(10 * np.log10(max(x["zero_doppler_max_P"], 1e-300)
                                                                                   / x["target_P"]) for x in rr)),
                     "psl_db_max": float(max(x["psl_db"] for x in rr))})
    res = resolution(SYSTEM)
    gh = CFG["scene"]["ghost"]
    return {"rows": rows, "ghost_power_db_truth": gh["power_db"],
            "ghost_separation_range_cells": gh["extra_range_m"] / res["range_m"],
            "ghost_separation_doppler_bins": abs(doppler_hz(CFG["scene"]["fixed_target"]["speed_mps"], SYSTEM.fc_hz)
                                                 * (1 - gh["doppler_factor"])) / res["doppler_hz"]}


def agg_stale(results: list) -> dict:
    rows = []
    for r in results:
        a, b = r["rows"]["per_frame_reference"], r["rows"]["stale_first_symbol"]
        rows.append({"config": r["spec"]["config"], "seed_index": r["spec"]["key"][2],
                     "per_frame_target_P": a["target_P"], "per_frame_within_tol": a["strongest"]["within_tol"],
                     "stale_target_P": b["target_P"], "stale_within_tol": b["strongest"]["within_tol"],
                     "stale_strongest_P": b["strongest"]["P"],
                     "stale_strongest_minus_per_frame_peak_db": float(10 * np.log10(b["strongest"]["P"] / a["target_P"]))})
    return {"rows": rows,
            "stale_loss_db_min": float(min(x["stale_strongest_minus_per_frame_peak_db"] for x in rows)),
            "stale_loss_db_max": float(max(x["stale_strongest_minus_per_frame_peak_db"] for x in rows)),
            "stale_within_tol_count": int(sum(x["stale_within_tol"] for x in rows)),
            "per_frame_within_tol_count": int(sum(x["per_frame_within_tol"] for x in rows)), "n": len(rows)}


def agg_stride(results: list, S: System) -> dict:
    groups = {}
    n_sym = CFG_RUN["stride"]["n_sym"]
    for r in results:
        sp = r["spec"]
        for label, row in r["rows"].items():
            groups.setdefault((sp["f_label"], sp["snr_mode"], label), []).append((row, sp["snr_db"]))
    rows = []
    for (fl, mode, label), pairs in groups.items():
        rr = [x for x, _ in pairs]
        snr = pairs[0][1]
        k = int(label[1:])
        F = 1.0 / (k * S.t_sym)
        ftrue = rr[0]["f_true_hz"]
        est = np.array([x["strongest_f_hz"] for x in rr])
        pred = rr[0]["f_alias_pred_hz"]
        werr = ((est - pred + F / 2) % F) - F / 2                   # wrapped error relative to the predicted alias
        rows.append({"doppler_label": fl, "snr_mode": mode, "snr_db": snr, "stride": k, "reference_rate_hz": F,
                     "n_reference_symbols": int(math.ceil(n_sym / k)), "f_true_hz": ftrue,
                     "aliased": bool(abs(ftrue) >= F / 2), "f_alias_predicted_hz": pred,
                     "alias_inside_zero_doppler_cell": bool(abs(pred) < 1.0 / (n_sym * S.t_sym)),
                     "integrated_snr_db": None if snr is None else
                     snr + 10 * math.log10(int(base_mask(S).sum()) * math.ceil(n_sym / k)),
                     "f_est_mean_wrapped_hz": float(pred + werr.mean()),
                     "err_vs_alias_maxabs_hz": float(np.abs(werr).max()),
                     "within_tol_of_alias_all": bool(all(x["strongest"]["within_tol"] for x in rr)),
                     "n_within_tol_of_alias": int(sum(bool(x["strongest"]["within_tol"]) for x in rr)),
                     "n_trials": len(rr)})
    order = {"noise-free": 0, "same SNR per RE": 1, "same integrated SNR": 2}
    rows.sort(key=lambda x: (x["doppler_label"], order[x["snr_mode"]], x["stride"]))
    return {"rows": rows, "n_sym": n_sym, "cpi_s": n_sym * S.t_sym,
            "doppler_resolution_hz": 1.0 / (n_sym * S.t_sym)}


def agg_h0(res_by_exp: dict) -> dict:
    cc = cfar_cells(SYSTEM, RxCfg())
    out = {"per_config": {}, "transfer_qpsk_thresholds": {}, "stress": {}}

    def rows_of(exp: str, c: str) -> list:
        return [r["rows"]["default"] for r in res_by_exp[exp] if r["spec"]["config"] == c]

    def evaluate(rows: list, alphas_frame: dict, alphas_cell: dict) -> dict:
        fs = np.array([x["frame_stat"] for x in rows])
        ncell = int(sum(x["n_search"] for x in rows))
        tv = np.concatenate([x["t_floor"] for x in rows]) if rows else np.zeros(0)
        e = {"n_frames": len(rows), "n_cells": ncell, "frame": {}, "cell": {},
             "mean_P": float(np.mean([x["mean_P"] for x in rows])),
             "top_T_cut_max": float(max(x["top_T_cut"] for x in rows)) if rows else 0.0}
        for kk, a in alphas_frame.items():
            n = int((fs > a).sum())
            e["frame"][kk] = {"alpha": a, "false_alarm_frames": n, "rate": n / len(rows), "wilson95": wilson(n, len(rows))}
        for kk, a in alphas_cell.items():
            if a <= CFG["t_floor"]:
                e["cell"][kk] = {"alpha": a, "rate": None, "note": "threshold below the stored floor"}
                continue
            n = int((tv > a).sum())
            e["cell"][kk] = {"alpha": a, "exceed_cells": n, "rate": n / ncell}
        return e

    for c in CFG_RUN["configs"]:
        cal = rows_of("h0_cal", c)
        fs = np.array([x["frame_stat"] for x in cal])
        a_frame = {_key(p): float(np.quantile(fs, 1 - p, method="higher")) for p in CFG_RUN["pfa_frame"]}
        tv = np.sort(np.concatenate([x["t_floor"] for x in cal]))[::-1]
        ncell = int(sum(x["n_search"] for x in cal))
        a_cell, a_nom = {}, {}
        for p in CFG_RUN["pfa_cell"]:
            kk = int(math.floor(p * ncell))
            if len(tv) <= kk:
                raise RuntimeError(f"stored cells {len(tv)} do not reach rank {kk}; lower t_floor")
            a_cell[_key(p)] = float(tv[kk])
            a_nom[_key(p)] = float(cc["n_train"] * (p ** (-1.0 / cc["n_train"]) - 1.0))
        ev = rows_of("h0_eval", c)
        evs = np.sort(np.array([x["frame_stat"] for x in ev]))
        brng = np.random.default_rng(np.random.SeedSequence(CFG["seed_root"], spawn_key=(EXP_CODES["h0_cal"], 99,
                                                                                         CONFIG_CODES[c])))
        boot = {}
        for p in CFG_RUN["pfa_frame"]:
            al = np.quantile(fs[brng.integers(0, len(fs), (CFG["n_bootstrap"], len(fs)))], 1 - p, axis=1,
                             method="higher")
            rates = (len(evs) - np.searchsorted(evs, al, side="right")) / len(evs)
            boot[_key(p)] = {"alpha_2p5_97p5": [float(v) for v in np.percentile(al, [2.5, 97.5])],
                             "eval_rate_2p5_97p5": [float(v) for v in np.percentile(rates, [2.5, 97.5])]}
        out["per_config"][c] = {
            "calibration_bootstrap": {"n_resamples": CFG["n_bootstrap"], "frame": boot},
            "alpha_frame": a_frame, "alpha_cell": a_cell, "alpha_cell_nominal_ca_cfar": a_nom,
            "calibration": evaluate(cal, a_frame, a_cell),
            "evaluation": evaluate(ev, a_frame, a_cell),
            "evaluation_at_nominal_alpha": evaluate(ev, {}, a_nom),
            "frame_stat_cal_quantiles": {str(q): float(np.quantile(fs, q)) for q in (0.5, 0.9, 0.99)}}
    q = out["per_config"]["qpsk_dcguard"]
    for c in CFG_RUN["configs"]:
        if c != "qpsk_dcguard":
            out["transfer_qpsk_thresholds"][c] = evaluate(rows_of("h0_eval", c), q["alpha_frame"], q["alpha_cell"])
    for exp in ("h0_eval_lownoise", "h0_eval_drift2", "h0_eval_drift10"):
        out["stress"][exp] = evaluate(rows_of(exp, "qpsk_dcguard"), q["alpha_frame"], q["alpha_cell"])
    out["stress"]["h0_eval_lownoise"]["snr_ref_db"] = CFG_RUN["lownoise_snr_ref_db"]
    out["stress"]["h0_eval_drift2"]["drift_doppler_hz"] = CFG["scene"]["drift_doppler_hz"][0]
    out["stress"]["h0_eval_drift10"]["drift_doppler_hz"] = CFG["scene"]["drift_doppler_hz"][1]
    mq = out["per_config"]["qpsk_dcguard"]["evaluation"]["mean_P"]
    m16 = out["per_config"]["16qam_dcguard"]["evaluation"]["mean_P"]
    out["floor_ratio_db_16qam_vs_qpsk"] = float(10 * np.log10(m16 / mq))
    out["cfar"] = cc
    return out


def agg_h0_clutter(results: list, h0: dict) -> dict:
    """Noise-free target-absent frames (clutter only): largest map value in the search region, relative to a unit
    on-grid target peak and to the mean map power of the evaluation H0 set of the same configuration."""
    groups = {}
    for r in results:
        sp = r["spec"]
        for label, row in r["rows"].items():
            groups.setdefault((sp["config"], sp["model"], float(sp["drift_hz"]), label), []).append(row)
    rows = []
    for (c, m, dh, label), rr in sorted(groups.items()):
        mx = max(x["max_P"] for x in rr)
        floor = h0["per_config"][c]["evaluation"]["mean_P"]
        rows.append({"config": c, "model": m, "clutter_drift_doppler_hz": dh, "receiver": label, "n_seeds": len(rr),
                     "max_P_db_re_unit_target": float(10 * np.log10(max(mx, 1e-300))),
                     "max_P_db_re_h0_eval_mean_P": float(10 * np.log10(max(mx, 1e-300) / floor))})
    return {"rows": rows, "h0_eval_snr_ref_db": CFG_RUN["snr_ref_db"]}


def crb(S: System, snr_db: float) -> dict:
    act = np.flatnonzero(base_mask(S)) - S.fft // 2
    snr = 10 ** (snr_db / 10)
    sn = float(((act - act.mean()) ** 2).sum())
    tm = np.arange(S.n_sym) * S.t_sym
    stt = float(((tm - tm.mean()) ** 2).sum())
    var_tau = 1.0 / (2 * snr * (2 * np.pi * S.scs_hz) ** 2 * S.n_sym * sn)
    var_f = 1.0 / (2 * snr * (2 * np.pi) ** 2 * len(act) * stt)
    return {"range_std_m": float(C0 / 2 * math.sqrt(var_tau)), "doppler_std_hz": float(math.sqrt(var_f))}


def agg_h1(results: list, h0: dict, S: System) -> dict:
    groups = {}
    for r in results:
        groups.setdefault((r["spec"]["config"], r["spec"]["snr_db"]), []).append(r["rows"]["default"])
    rows = []
    for (c, snr), rr in sorted(groups.items()):
        n = len(rr)
        row = {"config": c, "snr_re_db": snr, "n": n, "pd": {}, "off_target_frames": {},
               "integrated_snr_db": snr + 10 * np.log10(int(base_mask(S).sum()) * S.n_sym)}
        for kk, a in h0["per_config"][c]["alpha_frame"].items():
            d = int(sum(x["target_T"] > a for x in rr))
            off = int(sum(any(t > a for t, _ in x["off_T"]) for x in rr))
            off_nz = int(sum(any(t > a and not z for t, z in x["off_T"]) for x in rr))
            row["pd"][kk] = {"alpha": a, "detected": d, "pd": d / n, "wilson95": wilson(d, n)}
            row["off_target_frames"][kk] = {"frames": off, "rate": off / n, "wilson95": wilson(off, n),
                                            "frames_outside_zero_doppler_cell": off_nz,
                                            "rate_outside_zero_doppler_cell": off_nz / n}
        wt = [x for x in rr if x["strongest"]["within_tol"]]
        row["strongest_within_tol_frac"] = len(wt) / n
        if wt:
            er = np.array([x["strongest"]["range_err_m"] for x in wt])
            ef = np.array([x["strongest"]["doppler_err_hz"] for x in wt])
            row.update({"rmse_range_m": float(np.sqrt((er ** 2).mean())), "bias_range_m": float(er.mean()),
                        "rmse_doppler_hz": float(np.sqrt((ef ** 2).mean())), "bias_doppler_hz": float(ef.mean())})
        row["crb"] = crb(S, snr)
        row["frames_with_truncated_candidate_list_at_loosest_alpha"] = int(sum(
            x["top_T_cut"] > min(h0["per_config"][c]["alpha_frame"].values()) for x in rr))
        rows.append(row)
    snr50 = {}
    for c in CFG_RUN["configs"]:
        for kk in h0["per_config"][c]["alpha_frame"]:
            pts = [(x["snr_re_db"], x["pd"][kk]["pd"]) for x in rows if x["config"] == c]
            v = None
            for (s0, p0), (s1, p1) in zip(pts, pts[1:]):
                if p0 < 0.5 <= p1:
                    v = s0 + (0.5 - p0) * (s1 - s0) / (p1 - p0)
                    break
            snr50[f"{c}|{kk}"] = v
    return {"rows": rows, "snr_re_db_at_pd_half": snr50}


# ----------------------------------------------------------------------------------------------------
#  Figures
# ----------------------------------------------------------------------------------------------------
def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "xtick.labelsize": 8.5,
                         "ytick.labelsize": 8.5, "legend.fontsize": 8, "axes.grid": True, "grid.linewidth": 0.4,
                         "grid.color": "#dddddd", "axes.spines.top": False, "axes.spines.right": False,
                         "lines.linewidth": 1.4, "lines.markersize": 5})
    return plt


def _save(fig, path: str) -> dict:
    from paper_kit import audit_figure
    from figcheck import warn
    audit = audit_figure(fig)
    overlaps = warn(fig, os.path.basename(path))
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    fig.savefig(full, dpi=300, bbox_inches="tight")
    return {"path": path, "min_font_pt": audit["min_font_pt"], "colour_only_series": len(audit["colour_only_series"]),
            "overlap_warnings": len(overlaps)}


def figures(res: dict, maps: dict, prefix: str) -> dict:
    plt = _style()
    from matplotlib.colors import LinearSegmentedColormap
    from paper_kit import PALETTE, series_style
    out = {}
    S = SYSTEM
    cmap = LinearSegmentedColormap.from_list("blue_seq", ["#ffffff", "#9ec5f4", PALETTE[0], "#0d2a4a"])

    # 1. delay-Doppler maps
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6))
    snr_txt = f"{CFG['map_snr_db']:.0f}"
    for ax, (key, title, zoom) in zip(axs, (("on_grid", "(a) One target on grid\nnoise-free", True),
                                            ("off_grid", "(b) One target, +0.5 sample, +0.5 bin\nnoise-free", True),
                                            ("clutter", "(c) Clutter, target, second path\nSNR per RE " + snr_txt + " dB",
                                             False))):
        m = maps[key]
        R = C0 * m["tau_axis"] / 2
        P = m["P"] / m["peak_P"]
        db = 10 * np.log10(np.maximum(P, 1e-12))
        if zoom:
            rsel = np.abs(R - m["truth_range_m"]) <= 30
            fsel = np.abs(m["f_axis"] - m["truth_f_hz"]) <= 800
        else:
            rsel = np.ones(len(R), bool)
            fsel = np.abs(m["f_axis"]) <= 2500
        im = ax.pcolormesh(R[rsel], m["f_axis"][fsel], db[np.ix_(fsel, rsel)], vmin=-45, vmax=0, cmap=cmap,
                           shading="nearest", rasterized=True)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("Range (m)")
        ax.set_ylim(m["f_axis"][fsel][0], m["f_axis"][fsel][-1])
        ax.grid(False)
    axs[0].set_ylabel("Doppler (Hz)")
    cb = fig.colorbar(im, ax=axs, shrink=0.9, pad=0.02)
    cb.set_label("Power relative to target peak (dB)")
    out["map"] = _save(fig, prefix + "map.png")
    plt.close(fig)

    # 2. off-grid error (noise-free, time-domain channel, QPSK, DC + guard nulls)
    rows = [x for x in res["noise_free_offgrid"]["rows"] if x["config"] == "qpsk_dcguard" and x["model"] == "time"]
    labels = [k for k in CFG_RUN["knobs"] if k != "hann_logpar_pad2_noremoval"]
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.2))
    for i, lab in enumerate(labels):
        stl = series_style(i)
        for ax, sweep, off, key in ((axs[0], "delay", "delay_offset_bins", "range_err_maxabs_m"),
                                    (axs[1], "doppler", "doppler_offset_bins", "doppler_err_maxabs_hz")):
            sel = sorted([x for x in rows if x["receiver"] == lab and x["sweep"] == sweep and x[off] > 0],
                         key=lambda x: x[off])
            sel = [x for x in sel if x[key] > 0]                  # exact zeros cannot sit on a log axis
            ax.plot([x[off] for x in sel], [x[key] for x in sel], label=lab, **stl)
    axs[0].set_xlabel("Delay offset from grid (fraction of a sample)")
    axs[0].set_ylabel("Max |range error| (m)")
    axs[1].set_xlabel("Doppler offset from grid (fraction of a bin)")
    axs[1].set_ylabel("Max |Doppler error| (Hz)")
    for ax in axs:
        ax.set_yscale("log")
    axs[1].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.suptitle("Noise-free error off grid, max over payload seeds (QPSK, DC + guard nulls, time-domain channel)",
                 fontsize=9)
    fig.tight_layout()
    out["offgrid"] = _save(fig, prefix + "offgrid.png")
    plt.close(fig)

    # 3. RMSE vs SNR
    h1 = res["h1"]["rows"]
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.2))
    for i, c in enumerate(CFG_RUN["configs"]):
        sel = [x for x in h1 if x["config"] == c and "rmse_range_m" in x
               and x["strongest_within_tol_frac"] >= CFG["rmse_min_within_tol_frac"]]
        for ax, key in ((axs[0], "rmse_range_m"), (axs[1], "rmse_doppler_hz")):
            ax.plot([x["snr_re_db"] for x in sel], [x[key] for x in sel], label=c, **series_style(i))
    crb_rows = [x for x in h1 if x["config"] == "qpsk_dcguard"]
    for ax, key in ((axs[0], "range_std_m"), (axs[1], "doppler_std_hz")):
        ax.plot([x["snr_re_db"] for x in crb_rows], [x["crb"][key] for x in crb_rows], color="#333333",
                linestyle=(0, (2, 2)), marker="", label="CRB (QPSK, no window)")
        ax.set_yscale("log")
        ax.set_xlabel("SNR per resource element (dB)")
    axs[0].set_ylabel("Range RMSE (m)")
    axs[1].set_ylabel("Doppler RMSE (Hz)")
    axs[1].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.suptitle("Error of the strongest peak (SNR points where it lies within one cell of the target in "
                 f">= {CFG['rmse_min_within_tol_frac']:.0%} of frames)", fontsize=9)
    fig.tight_layout()
    out["rmse"] = _save(fig, prefix + "rmse.png")
    plt.close(fig)

    # 4. Pd vs SNR
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    strict = _key(min(CFG_RUN["pfa_frame"]))
    loose = _key(max(CFG_RUN["pfa_frame"]))
    for i, c in enumerate(CFG_RUN["configs"]):
        sel = [x for x in h1 if x["config"] == c]
        ax.plot([x["snr_re_db"] for x in sel], [x["pd"][strict]["pd"] for x in sel],
                label=f"{c}, frame Pfa target {strict}", **series_style(i))
    sel = [x for x in h1 if x["config"] == "qpsk_dcguard"]
    st3 = series_style(3)
    ax.plot([x["snr_re_db"] for x in sel], [x["pd"][loose]["pd"] for x in sel],
            label=f"qpsk_dcguard, frame Pfa target {loose}", **st3)
    ax.set_xlabel("SNR per resource element (dB)")
    ax.set_ylabel("Probability of detection")
    ax.set_ylim(-0.02, 1.02)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    ax.set_title("Detection within one resolution cell, thresholds set on calibration H0 seeds", fontsize=9)
    fig.tight_layout()
    out["pd"] = _save(fig, prefix + "pd.png")
    plt.close(fig)
    return out


def map_trials() -> dict:
    og = CFG["offgrid"]
    base = {"config": "qpsk_dcguard", "model": "time", "receivers": default_rx(), "return_map": True}
    specs = {
        "on_grid": {**base, "exp": "map", "key": (EXP_CODES["map"], 0, 0, 0), "snr_db": None, "scene": "single",
                    "geometry": {"q": og["q0_samples"], "kbin": og["k0_bins"]}},
        "off_grid": {**base, "exp": "map", "key": (EXP_CODES["map"], 0, 1, 0), "snr_db": None, "scene": "single",
                     "geometry": {"q": og["q0_samples"] + 0.5, "kbin": og["k0_bins"] + 0.5}},
        "clutter": {**base, "exp": "map", "key": (EXP_CODES["map"], 0, 2, 0), "snr_db": CFG["map_snr_db"],
                    "scene": "clutter_h1_fixed"},
    }
    maps = {}
    for k, sp in specs.items():
        r = run_trial(sp)["rows"]["default"]
        _, truth = build_scene(sp, SYSTEM, np.random.default_rng(0))
        m = r["map"]
        m["peak_P"] = r["target_P"]
        m["truth_range_m"] = truth["target"]["range_m"]
        m["truth_f_hz"] = truth["target"]["f_hz"]
        maps[k] = m
    return maps


# ----------------------------------------------------------------------------------------------------
#  Document (generated; every number printed from the result dict)
# ----------------------------------------------------------------------------------------------------
def _g(x, nd=3):
    if x is None:
        return "not reached"
    if isinstance(x, (bool, np.bool_)):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return f"{int(x)}"
    if abs(x) < 1e-12:                      # e.g. a Wilson lower bound of 0 events after rounding
        return "0"
    if abs(x) >= 1e4 and float(x).is_integer():
        return f"{x:.0f}"
    if abs(x) >= 1e4 or abs(x) < 1e-3:
        return f"{x:.{nd - 1}e}"
    return f"{x:.{nd}g}"


def _d(x, nd=3):
    return "-" if x is None else _g(x, nd)


def write_doc(d: dict, path: str) -> None:
    m, sysd, rx = d["_meta"], d["system"], d["receiver"]
    h0, h1, nf = d["h0"], d["h1"], d["noise_free_offgrid"]["summary"]
    cl, stl, sr = d["noise_free_clutter"], d["stale_reference"], d["stride"]
    cfgs = list(d["config"]["configs"])
    L = []
    a = L.append
    a("# OFDM receiver pilot (CPU, synthetic channels) - 2026-09-17")
    a("")
    a(f"> Generated by `{m['generator']}` from `{m['out_json']}` (git HEAD at run `{m['git_head'][:12]}`); "
      f"do not edit by hand. Command: `{m['command']}`. Tests: `{m['test_module']}`.")
    a("> Scope: a numpy simulation of a monostatic OFDM radar receiver on synthetic point-path channels. "
      "No ray tracer, no hardware, no RF measurement. Every number below is a property of this simulation "
      "setup at the stated parameters.")
    a("")
    a("## 1. System assumptions (stated, not tested)")
    a("")
    a("- Own transmitter; the receiver knows the transmitted resource grid of every OFDM symbol (per-frame reference) "
      "and its FFT window is aligned to the transmitted symbols.")
    a("- Not modelled: TX-RX leakage, CFO, phase noise, clock drift, ADC effects, range migration inside a frame, "
      "antennas and angles. Each path has one delay, one constant Doppler and one frequency-flat complex gain.")
    a("")
    a("| Parameter | Value |")
    a("|---|---|")
    for k, v in (("carrier (Hz)", sysd["fc_hz"]), ("subcarrier spacing (Hz)", sysd["scs_hz"]), ("FFT size", sysd["fft"]),
                 ("sample rate (Hz)", sysd["fs_hz"]), ("CP (samples, every symbol)", sysd["cp"]),
                 ("symbols per frame", sysd["n_sym"]), ("guard carriers (left, right)", str(tuple(sysd["guard"]))),
                 ("DC null", sysd["dc_null"]), ("active subcarriers (base mask)", sysd["n_active"]),
                 ("occupied span (subcarriers)", sysd["occupied_span"]), ("symbol rate (Hz)", sysd["symbol_rate_hz"]),
                 ("frame duration (s)", sysd["cpi_s"]), ("range resolution c/(2 span df) (m)", sysd["range_resolution_m"]),
                 ("range sample c/(2 fs) (m)", sysd["range_bin_m"]), ("Doppler bin 1/frame (Hz)", sysd["doppler_bin_hz"]),
                 ("velocity per Doppler bin (m/s)", sysd["velocity_per_doppler_bin_mps"]),
                 ("search range limit = CP (m)", sysd["max_range_cp_m"]),
                 ("unambiguous Doppler +/- (Hz)", sysd["unambiguous_doppler_hz"]),
                 ("coherent gain 10 log10(active x symbols) (dB)", sysd["processing_gain_db"])):
        a(f"| {k} | {_g(v, 5) if not isinstance(v, str) else v} |")
    a("")
    a("The mask follows the `sionna.phy.ofdm.ResourceGrid` guard/DC convention; NR does not reserve the DC "
      "subcarrier, so the DC null is a mask choice. Payload per resource element per symbol from "
      "`src/waveforms.py` `rand_qam`; modulation with `src/waveforms.py` `ofdm_modulate`.")
    a("")
    a("Configurations (payload and null mask):")
    a("")
    for c in cfgs:
        cc = d["config"]["configs"][c]
        a(f"- `{c}`: {cc['modulation']}, DC + guard nulls" + (
            f", plus a random {_g(cc['random_null_frac'])} fraction of in-band subcarriers nulled (a new pattern per "
            "trial, known to the receiver)" if cc["random_null_frac"] > 0 else ""))
    a("")
    a("## 2. Receiver")
    a("")
    a("Division by the per-frame reference on active subcarriers only (null and guard subcarriers are masked, "
      "never divided, estimate set to zero) -> slow-time mean removal -> separable window -> inverse FFT over "
      "subcarriers (delay) -> FFT over symbols (Doppler) -> CA-CFAR -> local maxima -> 3-point peak interpolation. "
      "The receiver function takes no truth; the search region is fixed by the system (delay from zero to the CP "
      "duration, all Doppler cells).")
    a("")
    a(f"Default: window `{rx['default']['window']}`, interpolation `{rx['default']['interp']}`, zero-padding "
      f"delay x{rx['default']['pad_delay']} and Doppler x{rx['default']['pad_doppler']}, static removal "
      f"{_g(rx['default']['static_removal'])}. CFAR (padded cells): guard Doppler {rx['cfar']['guard_doppler']}, "
      f"training Doppler {rx['cfar']['train_doppler']}, guard delay {rx['cfar']['guard_delay']}, training delay "
      f"{rx['cfar']['train_delay']}, {rx['cfar']['n_train']} training cells; {rx['search_cells']} search cells per frame.")
    a("")
    a("## 3. Channels and data sets")
    a("")
    sc = d["config"]["scene"]
    a(f"- Time-domain CP-OFDM channel (fractional delay by a phase ramp over the whole frame, as in "
      f"`src/passive_process.py` `make_cpi`) and a grid-level control `Y = H X + N` without inter-carrier "
      f"interference or fractional-delay tails.")
    a(f"- Static clutter: {len(sc['clutter'])} zero-Doppler paths at "
      + ", ".join(f"{_g(x['range_m'])} m ({_g(x['power_db'])} dB)" for x in sc["clutter"])
      + " relative to the target power.")
    a(f"- H1 target: range uniform in {_g(sc['h1_range_m'][0])}-{_g(sc['h1_range_m'][1])} m, |Doppler| uniform in "
      f"{_g(sc['h1_doppler_abs_hz'][0])}-{_g(sc['h1_doppler_abs_hz'][1])} Hz with random sign, plus a target-borne "
      f"second path at +{_g(sc['ghost']['extra_range_m'])} m, Doppler x{_g(sc['ghost']['doppler_factor'])}, "
      f"{_g(sc['ghost']['power_db'])} dB (Doppler-carrying multipath).")
    a(f"- SNR per resource element = target power / noise variance per sample (unit mean symbol energy). "
      f"H0 sets use the noise level of SNR {_g(d['config']['snr_ref_db'])} dB for a unit target.")
    a(f"- Seeds: `numpy.random.SeedSequence({m['seeds']['seed_root']}, spawn_key=(experiment, configuration, index, "
      f"sub-index))`, four child streams (payload, geometry and phases, noise, null mask). Experiment codes: "
      + ", ".join(f"{k}={v}" for k, v in m["seeds"]["experiment_codes"].items())
      + ". Calibration and evaluation H0 sets therefore never share a stream. The configuration code is part of the "
      "key, so different configurations draw different payloads, phases and noise; the grid/time pairs and the "
      "with/without second path pairs share their keys.")
    a(f"- Trial counts: calibration H0 {d['config']['n_cal']} and evaluation H0 {d['config']['n_eval']} per "
      f"configuration; stress H0 {d['config']['n_eval_stress']}; H1 {d['config']['n_h1']} per configuration per SNR.")
    a("")
    a("## 4. Results (observations)")
    a("")
    a("### 4.1 Noise-free estimation, single target")
    a("")
    a("Maximum |error| of the strongest candidate over all three configurations, the payload seeds and every "
      "offset (on grid, delay-only, Doppler-only, joint; offsets in fractions of a range sample and a Doppler bin).")
    a("")
    a("| Receiver | Channel | On-grid range (m) | On-grid Doppler (Hz) | All offsets range (m) | All offsets Doppler (Hz) | "
      "range (samples) | Doppler (bins) | payload spread range (m) | highest other peak (dB) | all within 1 cell |")
    a("|---|---|---|---|---|---|---|---|---|---|---|")
    for key, v in nf.items():
        lab, model = key.split("|")
        a(f"| `{lab}` | {model} | {_g(v['on_grid_range_err_maxabs_m'])} | {_g(v['on_grid_doppler_err_maxabs_hz'])} | "
          f"{_g(v['all_range_err_maxabs_m'])} | {_g(v['all_doppler_err_maxabs_hz'])} | {_g(v['all_range_err_maxabs_bins'])} | "
          f"{_g(v['all_doppler_err_maxabs_bins'])} | {_g(v['max_payload_spread_range_m'])} | {_g(v['psl_db_max'])} | "
          f"{_g(v['all_within_tol'])} |")
    a("")
    dflt, nrm = nf.get("hann_logpar_pad2|grid"), nf.get("hann_logpar_pad2_noremoval|grid")
    if dflt and nrm:
        a(f"Static removal on versus off (grid-level channel, default window and interpolation): largest Doppler error "
          f"{_g(dflt['all_doppler_err_maxabs_hz'])} versus {_g(nrm['all_doppler_err_maxabs_hz'])} Hz, highest other peak "
          f"{_g(dflt['psl_db_max'])} versus {_g(nrm['psl_db_max'])} dB (each the maximum over the three configurations). "
          "In map panel (b) the removal leaves a copy of the "
          "off-grid target at zero Doppler and the target delay.")
        a("")
    a("'highest other peak' = largest map value outside the guard box of the strongest peak, relative to that peak "
      "(window sidelobes, null-mask sidelobes and, in the time-domain channel, inter-carrier interference and "
      "fractional-delay tails). Figure: `" + d["figures"]["offgrid"]["path"] + "`.")
    a("")
    a("### 4.2 Noise-free clutter scene (fixed target, second path, static clutter)")
    a("")
    a(f"Target at {_g(sc['fixed_target']['range_m'])} m and {_g(sc['fixed_target']['speed_mps'])} m/s; second path "
      f"{_g(cl['ghost_power_db_truth'])} dB, {_g(cl['ghost_separation_range_cells'])} range resolution cells and "
      f"{_g(cl['ghost_separation_doppler_bins'])} Doppler bins from the target. Rows with second path 'no' are the "
      "control with only the second path removed (same seeds, same clutter).")
    a("")
    a("| Config | Channel | second path | seeds | strongest = target | target range err (m) | target Doppler err (Hz) | "
      "second path found | second path level (dB, min..max) | second path range err (m) | max within one Doppler bin of zero (dB re target) |")
    a("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in cl["rows"]:
        a(f"| `{r['config']}` | {r['model']} | {_g(r['second_path'])} | {r['n_seeds']} | {_g(r['strongest_is_target_all'])} | "
          f"{_g(r['target_range_err_maxabs_m'])} | {_g(r['target_doppler_err_maxabs_hz'])} | "
          f"{(str(r['ghost_found']) + '/' + str(r['n_seeds'])) if r['second_path'] else '-'} | "
          f"{_d(r['ghost_level_db_min'])}..{_d(r['ghost_level_db_max'])} | {_d(r['ghost_range_err_maxabs_m'])} | "
          f"{_g(r['zero_doppler_band_max_db_re_target'])} |")
    a("")
    ft_bins = doppler_hz(sc["fixed_target"]["speed_mps"], sysd["fc_hz"]) / sysd["doppler_bin_hz"]
    hann_half = rx["cfar"]["guard_doppler"] / rx["default"]["pad_doppler"]
    cr = h0["clutter_residual_noise_free"]["rows"]
    cr_static = [r for r in cr if r["clutter_drift_doppler_hz"] == 0 and r["receiver"] == "default"]
    zb = [r["zero_doppler_band_max_db_re_target"] for r in cl["rows"] if not r["second_path"]]
    a(f"Last column: largest map power within one Doppler bin of zero, relative to the target peak. In the rows without "
      f"the second path it spans {_g(min(zb))}..{_g(max(zb))} dB over both channel models and all configurations. The "
      f"noise-free clutter-only frames of section 4.4 give at most {_g(max(r['max_P_db_re_unit_target'] for r in cr_static))} dB "
      f"relative to a unit target peak, so this column is not a clutter residual; the target sits {_g(ft_bins)} Doppler "
      f"bins from zero, within the {_g(hann_half)}-bin half-width of the Hann main lobe used for the CFAR guard. "
      "Configurations use different seed streams (section 3), so differences between configuration rows (for example "
      "how often the second path is found) are not a controlled modulation or null-mask comparison.")
    a("")
    a("### 4.3 Payload change: per-frame reference versus a stale reference")
    a("")
    a(f"Same received frames, divided either by the true per-symbol grid or by the first symbol tiled over the frame "
      f"({stl['n']} frames, QPSK and 16-QAM, time-domain channel, noise-free). Strongest stale-reference peak relative "
      f"to the per-frame target peak: {_g(stl['stale_loss_db_min'])} to {_g(stl['stale_loss_db_max'])} dB; strongest "
      f"peak within one cell of the target: per-frame {stl['per_frame_within_tol_count']}/{stl['n']}, stale "
      f"{stl['stale_within_tol_count']}/{stl['n']}.")
    a("")
    a("### 4.4 H0: thresholds from calibration seeds, false alarms on evaluation seeds")
    a("")
    crd = h0["clutter_residual_noise_free"]
    a(f"Noise-free target-absent frames (clutter only): largest map value in the search region, relative to a unit "
      f"on-grid target peak and to the mean map power of the evaluation H0 set of the same configuration (noise level "
      f"of SNR {_g(crd['h0_eval_snr_ref_db'])} dB).")
    a("")
    a("| Config | Channel | clutter Doppler drift +/- (Hz) | receiver | seeds | max (dB re unit target) | max (dB re H0 eval. mean map power) |")
    a("|---|---|---|---|---|---|---|")
    for r in crd["rows"]:
        a(f"| `{r['config']}` | {r['model']} | {_g(r['clutter_drift_doppler_hz'])} | `{r['receiver']}` | {r['n_seeds']} | "
          f"{_g(r['max_P_db_re_unit_target'])} | {_g(r['max_P_db_re_h0_eval_mean_P'])} |")
    a("")
    st_def = [r["max_P_db_re_h0_eval_mean_P"] for r in crd["rows"] if r["clutter_drift_doppler_hz"] == 0 and r["receiver"] == "default"]
    st_off = [r["max_P_db_re_h0_eval_mean_P"] for r in crd["rows"] if r["receiver"] == "no_static_removal"]
    a(f"With static removal the static clutter leaves at most {_g(max(st_def))} dB relative to the evaluation-set mean "
      f"map power (without removal {_g(min(st_off))}..{_g(max(st_off))} dB). In this setup the clutter paths carry "
      "no Doppler and their delays are inside the CP (the time-domain channel adds only fractional-delay tails), so "
      "the static-clutter H0 sets below calibrate the detector against noise; clutter energy above the noise enters "
      "the map only in the drift rows.")
    grid_static = [r["max_P_db_re_unit_target"] for r in crd["rows"] if r["model"] == "grid"
                   and r["clutter_drift_doppler_hz"] == 0 and r["receiver"] == "default"]
    if grid_static and max(grid_static) < ROUNDOFF_DB:
        a(f"The grid-level rows with removal ({_g(min(grid_static))}..{_g(max(grid_static))} dB) are floating-point "
          "round-off.")
    a("")
    a("Frame statistic = largest CFAR ratio among local maxima in the search region; frame threshold = empirical "
      "quantile of calibration frames. Cell threshold = empirical rank over all calibration search cells. "
      f"Intervals are Wilson {WILSON_LEVEL_PCT} %.")
    a("")
    a(f"| Config | target | frame alpha | cal. rate | eval. false frames / n | eval. rate [Wilson {WILSON_LEVEL_PCT} %] | "
      "eval. rate over calibration resamples (2.5-97.5 %) |")
    a("|---|---|---|---|---|---|---|")
    for c in cfgs:
        pc = h0["per_config"][c]
        for kk, al in pc["alpha_frame"].items():
            ce, ee = pc["calibration"]["frame"][kk], pc["evaluation"]["frame"][kk]
            bt = pc["calibration_bootstrap"]["frame"][kk]["eval_rate_2p5_97p5"]
            a(f"| `{c}` | frame {kk} | {_g(al, 4)} | {_g(ce['rate'])} | {ee['false_alarm_frames']}/{pc['evaluation']['n_frames']} | "
              f"{_g(ee['rate'])} [{_g(ee['wilson95'][0])}, {_g(ee['wilson95'][1])}] | {_g(bt[0])}..{_g(bt[1])} |")
    a("")
    a("The Wilson interval covers only the finite evaluation set. The last column re-draws the calibration set with "
      f"replacement ({h0['per_config'][cfgs[0]]['calibration_bootstrap']['n_resamples']} resamples), recomputes the "
      "threshold and counts the same evaluation frames, so it shows how much the threshold itself moves with a "
      "calibration set of this size.")
    a("")
    a("| Config | cell target | calibrated alpha | eval. cell rate | nominal CA-CFAR alpha | eval. cell rate at nominal |")
    a("|---|---|---|---|---|---|")
    for c in cfgs:
        pc = h0["per_config"][c]
        for kk, al in pc["alpha_cell"].items():
            en = pc["evaluation_at_nominal_alpha"]["cell"][kk]
            a(f"| `{c}` | {kk} | {_g(al, 4)} | {_g(pc['evaluation']['cell'][kk]['rate'])} | "
              f"{_g(pc['alpha_cell_nominal_ca_cfar'][kk], 4)} | {_g(en['rate'])} |")
    a("")
    a("Thresholds of `qpsk_dcguard` applied to other evaluation sets (frame rate at each frame target):")
    a("")
    for name, ev in list(h0["transfer_qpsk_thresholds"].items()) + list(h0["stress"].items()):
        parts = [f"{kk}: {fr['false_alarm_frames']}/{ev['n_frames']} = {_g(fr['rate'])} "
                 f"[{_g(fr['wilson95'][0])}, {_g(fr['wilson95'][1])}]" for kk, fr in ev["frame"].items()]
        extra = ""
        if "snr_ref_db" in ev:
            extra = (f" (noise level of SNR {_g(ev['snr_ref_db'])} dB, i.e. clutter-to-noise "
                     f"{_g(ev['snr_ref_db'] - d['config']['snr_ref_db'])} dB higher than in calibration)")
        if "drift_doppler_hz" in ev:
            extra = (f" (each clutter path carries a Doppler uniform in +/-{_g(ev['drift_doppler_hz'])} Hz; Doppler bin "
                     f"{_g(sysd['doppler_bin_hz'])} Hz)")
        a(f"- `{name}`{extra}: " + "; ".join(parts))
    a("")
    a(f"H0 noise floor after division (mean map power, evaluation sets): 16-QAM minus QPSK = "
      f"{_g(h0['floor_ratio_db_16qam_vs_qpsk'])} dB. The analytic average of 1/|X|^2 in "
      f"`{m['inputs']['logic_review']}` : `ofdm.noise_ratio_db` is {_g(d['ledger_values']['noise_ratio_db'])} dB.")
    a("")
    a("### 4.5 H1: detection and estimation versus SNR")
    a("")
    a("A detection counts for the target when a detected local maximum lies within one range resolution cell and "
      "one Doppler bin of the target truth (truth used only for this scoring). 'off-target frames' = frames with at "
      "least one detection that is near neither the target nor the second path.")
    a("")
    kk0 = _key(min(d["config"]["pfa_frame"]))
    a(f"| Config | SNR/RE (dB) | integrated, base mask (dB) | Pd at frame {kk0} [{WILSON_LEVEL_PCT} %] | off-target frames | "
      "of which outside zero-Doppler cell | strongest within cell | range RMSE (m) | CRB (m) | Doppler RMSE (Hz) | CRB (Hz) |")
    a("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in h1["rows"]:
        p = r["pd"][kk0]
        ot = r["off_target_frames"][kk0]
        a(f"| `{r['config']}` | {_g(r['snr_re_db'])} | {_g(r['integrated_snr_db'])} | {_g(p['pd'])} "
          f"[{_g(p['wilson95'][0])}, {_g(p['wilson95'][1])}] | {_g(ot['rate'])} | {_g(ot['rate_outside_zero_doppler_cell'])} | "
          f"{_g(r['strongest_within_tol_frac'])} | {_d(r.get('rmse_range_m'))} | {_g(r['crb']['range_std_m'])} | "
          f"{_d(r.get('rmse_doppler_hz'))} | {_g(r['crb']['doppler_std_hz'])} |")
    a("")
    a("SNR per resource element where Pd crosses 0.5 (linear interpolation on the swept grid):")
    a("")
    for k, v in h1["snr_re_db_at_pd_half"].items():
        a(f"- `{k}`: {_g(v)} dB")
    q50 = h1["snr_re_db_at_pd_half"].get(f"16qam_dcguard|{kk0}")
    p50 = h1["snr_re_db_at_pd_half"].get(f"qpsk_dcguard|{kk0}")
    if q50 is not None and p50 is not None:
        a(f"- 16-QAM minus QPSK at frame {kk0}: {_g(q50 - p50)} dB")
    a("")
    a("The CRB line is for a single unwindowed complex exponential with known QPSK symbols; the receiver uses a Hann "
      "window and a random target position, so the RMSE is not expected to meet it. RMSE is computed only over "
      "trials whose strongest peak lies within one cell of the target (conditional, optimistic where that fraction is "
      f"low; the figure shows only SNR points where it is at least {_g(d['config']['rmse_min_within_tol_frac'])}). "
      f"Candidate lists were truncated above the loosest frame threshold in "
      f"{sum(r['frames_with_truncated_candidate_list_at_loosest_alpha'] for r in h1['rows'])} H1 frames. "
      f"For comparison with the high-SNR end of the table, section 4.2 (noise-free, fixed geometry, same second path) gives "
      f"a largest target range error of {_g(max(r['target_range_err_maxabs_m'] for r in cl['rows'] if r['second_path']))} m "
      f"with the second path and {_g(max(r['target_range_err_maxabs_m'] for r in cl['rows'] if not r['second_path']))} m "
      "without it. Figures: `"
      + d["figures"]["rmse"]["path"] + "`, `" + d["figures"]["pd"]["path"] + "`.")
    a("")
    a("### 4.6 Reference on every k-th symbol only (repetition rate)")
    a("")
    lv = d["ledger_values"]
    a(f"Frame of {sr['n_sym']} symbols ({_g(sr['cpi_s'])} s, Doppler bin {_g(sr['doppler_resolution_hz'])} Hz), "
      "QPSK, time-domain channel, one target; the receiver uses symbols 0, k, 2k, ... as reference. Doppler values "
      f"from `{m['inputs']['link_budget']}` : `tip_doppler_rows` ({_g(lv['fc_ghz'])} GHz, rpm label {lv['rpm_label']}, "
      f"el {_g(lv['el_deg'])} deg, body speed {_g(lv['body_speed_mps'])} m/s): body {_g(lv['f_body_hz'])} Hz and body + "
      f"blade tip {_g(lv['f_body_plus_tip_hz'])} Hz. `slow_time_rate_rows` of that ledger lists "
      f"{_g(lv['one_symbol_per_slot_rate_hz'])} Hz for `{lv['rate_waveform']}` with one reference symbol per slot; here "
      f"k = {lv['k_slot']} gives {_g(lv['k_slot_rate_hz'], 5)} Hz because every CP has the same length.")
    a("")
    a("Noise rows: 'same SNR per RE' keeps the noise per element, so fewer reference symbols means less integrated "
      "SNR; 'same integrated SNR' raises the SNR per RE by 10 log10 k so the integrated SNR stays that of k = 1. "
      "Estimates are averaged after wrapping onto the predicted alias.")
    a("")
    a("| Doppler | noise | SNR/RE (dB) | integrated (dB) | k | reference rate (Hz) | reference symbols | true (Hz) | aliased | "
      "predicted alias (Hz) | alias in zero-Doppler cell | estimate mean, wrapped (Hz) | max err vs alias (Hz) | "
      "strongest peak within one cell of alias / trials |")
    a("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sr["rows"]:
        a(f"| {r['doppler_label']} | {r['snr_mode']} | {'-' if r['snr_db'] is None else _g(r['snr_db'])} | "
          f"{'-' if r['integrated_snr_db'] is None else _g(r['integrated_snr_db'])} | {r['stride']} | "
          f"{_g(r['reference_rate_hz'], 5)} | {r['n_reference_symbols']} | {_g(r['f_true_hz'], 5)} | {_g(r['aliased'])} | "
          f"{_g(r['f_alias_predicted_hz'], 5)} | {_g(r['alias_inside_zero_doppler_cell'])} | {_g(r['f_est_mean_wrapped_hz'], 5)} | "
          f"{_g(r['err_vs_alias_maxabs_hz'])} | {r['n_within_tol_of_alias']}/{r['n_trials']} |")
    a("")
    a("One cell = one range resolution cell and one Doppler bin of this frame; the maximum error column is set by the "
      "worst single trial, so read it with the count. "
      "The folding itself is sampling-theorem arithmetic. The table records where this receiver's estimate lands "
      "relative to the predicted alias, including rows where the alias falls into the zero-Doppler cell that static "
      "removal suppresses. It does not say which rate a rotor measurement needs (constant-Doppler tones, not rotor "
      "returns).")
    a("")
    a("## 5. Figures")
    a("")
    for k, f in d["figures"].items():
        a(f"- `{f['path']}` (min font {_g(f['min_font_pt'])} pt, overlap warnings {f['overlap_warnings']})")
    a("")
    a("## 6. What this pilot does NOT show")
    a("")
    for s in d["not_shown"]:
        a(f"- {s}")
    a("")
    a("## 7. Interpretation (not tested here)")
    a("")
    for s in d["interpretation"]:
        a(f"- {s}")
    a("")
    a("## 8. Open")
    a("")
    for s in d["open"]:
        a(f"- {s}")
    a("")
    a(f"Run cost: {_g(m['wall_s'])} s wall, {_g(m['cpu_s'])} CPU-seconds, {m['workers']} worker processes "
      f"(`taskset -c 8-15`). sha256 of the ledger: `{m.get('json_sha256', '')}`.")
    txt = "\n".join(L) + "\n"
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(txt)


# ----------------------------------------------------------------------------------------------------
#  Main
# ----------------------------------------------------------------------------------------------------
CFG_RUN = dict(CFG)


def _sha(path: str) -> str:
    return hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest()


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def main() -> None:
    global CFG_RUN
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--workers", type=int, default=6)
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
        write_doc(led, args.doc)
        print(f"  rewrote {args.doc} from {args.out_json}", flush=True)
        return
    t0 = time.time()
    CFG_RUN = {**CFG, **(QUICK if args.quick else {})}

    lb = json.load(open(os.path.join(ROOT, LINK_BUDGET)))
    row = next(r for r in lb["tip_doppler_rows"] if abs(r["fc_ghz"] - SYSTEM.fc_hz / 1e9) < 1e-9
               and r["rpm_label"] == "hover" and r["el_deg"] == 0 and r["body_speed_mps"] > 0)
    rate_row = next(r for r in lb["slow_time_rate_rows"]
                    if r["waveform"] == "nr_scs30khz" and r["reference_use"] == "one_symbol_per_slot")
    lr = json.load(open(os.path.join(ROOT, LOGIC_REVIEW)))
    k_slot = int(round(1.0 / SYSTEM.t_sym / rate_row["rate_hz"]))
    ledger_values = {"f_body_hz": row["f_body_hz"], "f_tip_hz": row["f_tip_hz"],
                     "f_body_plus_tip_hz": row["f_body_hz"] + row["f_tip_hz"], "body_speed_mps": row["body_speed_mps"],
                     "fc_ghz": row["fc_ghz"], "el_deg": row["el_deg"], "rpm_label": row["rpm_label"], "rpm": row["rpm"],
                     "rate_waveform": rate_row["waveform"], "one_symbol_per_slot_rate_hz": rate_row["rate_hz"],
                     "k_slot": k_slot, "k_slot_rate_hz": 1.0 / (k_slot * SYSTEM.t_sym),
                     "noise_ratio_db": lr["ofdm"]["noise_ratio_db"]}
    strides_f = [("body", ledger_values["f_body_hz"]), ("body+tip", ledger_values["f_body_plus_tip_hz"])]

    specs = build_specs(CFG_RUN, strides_f)
    ctx = mp.get_context("fork")
    res_by_exp, timing = {}, {}
    with ctx.Pool(args.workers) as pool:
        for exp, sp in specs.items():
            t1 = time.time()
            res_by_exp[exp] = pool.map(run_trial, sp, chunksize=max(1, len(sp) // (args.workers * 8)))
            timing[exp] = {"n_trials": len(sp), "wall_s": time.time() - t1}
            print(f"  {exp}: {len(sp)} trials, {timing[exp]['wall_s']:.1f} s", flush=True)

    S = SYSTEM
    res = resolution(S)
    cc = cfar_cells(S, RxCfg())
    n_act = int(base_mask(S).sum())
    out = {
        "system": {**CFG["system"], "fs_hz": S.fs, "t_sym_s": S.t_sym, "symbol_rate_hz": 1 / S.t_sym,
                   "cpi_s": S.n_sym * S.t_sym, "n_active": n_act, "occupied_span": cc["occupied_span"],
                   "range_resolution_m": res["range_m"], "range_bin_m": res["range_bin_m"],
                   "doppler_bin_hz": res["doppler_bin_hz"],
                   "velocity_per_doppler_bin_mps": res["doppler_bin_hz"] * C0 / (2 * S.fc_hz),
                   "max_range_cp_m": C0 * S.cp / S.fs / 2, "unambiguous_doppler_hz": 0.5 / S.t_sym,
                   "processing_gain_db": 10 * math.log10(n_act * S.n_sym)},
        "receiver": {"default": CFG["receiver_default"], "cfar": cc,
                     "search_cells": (CFG["receiver_default"]["pad_delay"] * S.cp + 1)
                     * CFG["receiver_default"]["pad_doppler"] * S.n_sym,
                     "tolerance": {"range_m": res["range_m"], "doppler_hz": res["doppler_hz"]}},
        "config": {k: CFG_RUN[k] for k in ("configs", "knobs", "scene", "offgrid", "stale", "stride", "snr_ref_db",
                                            "lownoise_snr_ref_db", "snr_grid_db", "n_cal", "n_eval", "n_eval_stress",
                                            "n_h1", "pfa_frame", "pfa_cell", "t_floor", "n_top_candidates",
                                            "clutter_noise_free_seeds", "h0_clutter_noise_free_seeds", "map_snr_db",
                                            "rmse_min_within_tol_frac")},
        "ledger_values": ledger_values,
        "noise_free_offgrid": agg_offgrid(res_by_exp["nf_offgrid"], S),
        "noise_free_clutter": agg_clutter(res_by_exp["nf_clutter"]),
        "stale_reference": agg_stale(res_by_exp["nf_stale"]),
        "stride": agg_stride(res_by_exp["stride"], S),
    }
    out["h0"] = agg_h0(res_by_exp)
    out["h0"]["clutter_residual_noise_free"] = agg_h0_clutter(res_by_exp["nf_h0_clutter"], out["h0"])
    out["h0"]["frame_stats"] = {exp: {c: [round(r["rows"]["default"]["frame_stat"], 5) for r in res_by_exp[exp]
                                          if r["spec"]["config"] == c] for c in CFG_RUN["configs"]}
                                for exp in ("h0_cal", "h0_eval")}
    out["h1"] = agg_h1(res_by_exp["h1"], out["h0"], S)
    maps = map_trials()
    out["figures"] = figures(out, maps, args.fig_prefix)
    for k, f in out["figures"].items():
        full = f["path"] if os.path.isabs(f["path"]) else os.path.join(ROOT, f["path"])
        f["sha256"] = hashlib.sha256(open(full, "rb").read()).hexdigest()
    out["not_shown"] = [
        "Nothing about the ray tracer or its pose fields: no Sionna RT output enters this script.",
        "Nothing about hardware: no X410, no RF capture, no measured isolation, CFO, phase noise or ADC behaviour.",
        "Paths are points with frequency-flat gains and constant Doppler: no rotor micro-Doppler, no range migration, "
        "no extended target, no frequency-dependent scattering.",
        "Linking the ray tracer to range or frequency-selective tests needs per-path delays and complex gains; a single "
        "complex pose field E(t) supports only flat-fading or time-modulation tests.",
        "H0 contains only the static clutter set and white noise (plus the two stress sets); real target-absent "
        "captures have moving clutter, interference and leakage, so these thresholds do not transfer to captures.",
        "The static-clutter H0 sets do not test clutter suppression: the clutter paths carry no Doppler and have delays "
        "inside the CP, and after slow-time mean removal their largest map value is "
        f"{max(r['max_P_db_re_h0_eval_mean_P'] for r in out['h0']['clutter_residual_noise_free']['rows'] if r['clutter_drift_doppler_hz'] == 0 and r['receiver'] == 'default'):.3g} "
        "dB relative to the mean map power of the evaluation H0 set (section 4.4, noise-free clutter-only rows); only "
        "the drift sets put clutter energy into the map.",
        f"Frame false-alarm targets were calibrated at {', '.join(_key(p) for p in CFG_RUN['pfa_frame'])} only, with "
        f"{CFG_RUN['n_cal']} calibration and {CFG_RUN['n_eval']} evaluation frames per configuration; the frame target in "
        "docs/MOBICOM_PIPELINE_PLAN_0916.md section 5 is lower than the lowest of these and needs more independent H0 "
        "trials than this pilot ran (that section gives the count).",
        "Delays beyond the CP (inter-symbol interference) and targets inside the zero-Doppler notch of the static "
        "removal are outside the tested region.",
        "Timing and CFO synchronisation, the longer first-symbol CP and non-contiguous symbols (UL slots, SSB gaps) "
        "are not modelled.",
    ]
    out["interpretation"] = [
        "Section 4.3 is a control with one variable switched (same received frames, only the reference changes): in "
        "this simulation the target peak depends on dividing by the per-frame grid, so a receiver that tiles one "
        "reference symbol would not serve as the validation for a changing payload.",
        "The gap between the nominal CA-CFAR alpha and the calibrated one is attributed to correlated cells (window, "
        "zero-padding, guard bands) by analogy with the bistatic-chain result in src/passive_process.py (CFAR "
        "calibration note); this script did not switch the window or padding off to confirm it for H0.",
    ]
    cl = out["noise_free_clutter"]["rows"]
    with_gh = max(r["target_range_err_maxabs_m"] for r in cl if r["second_path"])
    no_gh = max(r["target_range_err_maxabs_m"] for r in cl if not r["second_path"])
    top = [r for r in out["h1"]["rows"] if r["config"] == "qpsk_dcguard"][-1]
    out["interpretation"].append(
        f"At the highest swept SNR ({top['snr_re_db']:g} dB per RE, qpsk_dcguard) the range RMSE is "
        f"{top['rmse_range_m'] / top['crb']['range_std_m']:.2g} times the CRB line. The noise-free control of section 4.2 "
        f"moves the largest target range error from {no_gh:.2g} m to {with_gh:.2g} m when only the second path is added, "
        "so a bias from the second path (inside the Hann main lobe of the target in delay) is a candidate contributor; "
        "the H1 sets themselves were not rerun without the second path, and the Hann window alone also keeps the RMSE "
        "above an unwindowed bound.")
    d10 = out["h0"]["stress"]["h0_eval_drift10"]["frame"]
    d2 = out["h0"]["stress"]["h0_eval_drift2"]["frame"]
    kk = _key(min(CFG_RUN["pfa_frame"]))
    out["interpretation"].append(
        f"With slow-time mean removal, thresholds set on static clutter gave a frame false-alarm rate of "
        f"{d2[kk]['rate']:.3g} when each clutter path carried up to +/-{CFG['scene']['drift_doppler_hz'][0]:g} Hz and "
        f"{d10[kk]['rate']:.3g} with up to +/-{CFG['scene']['drift_doppler_hz'][1]:g} Hz (target {kk}). How real site "
        "clutter moves is not known from this simulation, so which of these cases applies to captures is open.")
    out["open"] = [
        "Leakage/self-interference cancellation, CFO and timing estimation before division (MOBICOM plan section 6 "
        "layer 4).",
        "Moving clutter in H0 beyond the two drift sets, and a calibration set large enough for the plan's frame "
        "false-alarm target.",
        "An RT-linked version needs per-path delay and gain dumps under a new output name (review verdict for "
        "section 7 C); no production stem is to be rerun with --overwrite.",
    ]
    ru_self = resource.getrusage(resource.RUSAGE_SELF)
    ru_ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", GENERATOR, TEST_MODULE],
                           capture_output=True, text=True).stdout.strip()
    out["_meta"] = {
        "generator": GENERATOR, "test_module": TEST_MODULE, "out_json": args.out_json,
        "command": "CUDA_VISIBLE_DEVICES=\"\" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 "
                   + sys.executable + " " + " ".join([GENERATOR] + sys.argv[1:]),
        "git_head": head, "generator_git_status": dirty or "clean",
        "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "quick": bool(args.quick), "workers": args.workers, "wall_s": time.time() - t0,
        "cpu_s": ru_self.ru_utime + ru_self.ru_stime + ru_ch.ru_utime + ru_ch.ru_stime, "timing": timing,
        "numpy": np.__version__,
        "sha256": {p: _sha(p) for p in (GENERATOR, TEST_MODULE, "src/waveforms.py", LINK_BUDGET, LOGIC_REVIEW)
                   if os.path.exists(os.path.join(ROOT, p))},
        "inputs": {"link_budget": LINK_BUDGET, "logic_review": LOGIC_REVIEW, "waveform_helpers": "src/waveforms.py"},
        "seeds": {"seed_root": CFG["seed_root"], "experiment_codes": EXP_CODES, "config_codes": CONFIG_CODES,
                  "layout": "SeedSequence(seed_root, spawn_key=(experiment, configuration or Doppler index, index or "
                            "SNR code, index)).spawn(4) -> payload, geometry+phases, noise, null mask"},
        "scope": "numpy simulation of a monostatic OFDM-radar receiver on synthetic point-path channels; no ray tracer, "
                 "no hardware, no RF measurement",
        "prior_work": {"benchmark/report07_5g_waveform.py": "resource-grid identity test (Y = hX divided by X), no delay "
                       "axis, pre-freeze hover channel",
                       "outputs/isac_plan_detection_0915.json : f14_reference": "tiled first-frame reference fails with "
                       "independent payload per frame in the bistatic chain",
                       "outputs/verify_cfar.json": "nominal versus empirical CA-CFAR false-alarm rate in the bistatic chain"},
    }
    full = args.out_json if os.path.isabs(args.out_json) else os.path.join(ROOT, args.out_json)
    txt = json.dumps(out, indent=1, default=_json_default, allow_nan=False)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(txt)
    out["_meta"]["json_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    write_doc(out, args.doc)
    print(f"  wrote {args.out_json}, {args.doc}, figures {args.fig_prefix}*; wall {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
