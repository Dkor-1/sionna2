# -*- coding: utf-8 -*-
"""
test_ofdm_receiver_pilot_0917.py - checks for benchmark/ofdm_receiver_pilot_0917.py on a small system
=====================================================================================================

What is checked
    - the active-subcarrier mask follows sionna.phy.ofdm.ResourceGrid.effective_subcarrier_ind (cross-checked
      against the installed class when it imports; the explicit guard/DC rule is checked either way);
    - the time-domain fractional delay + Doppler equals src/radar_process.py _delay_doppler;
    - noise-free on-grid recovery (QPSK and 16-QAM, grid-level and time-domain channels);
    - null-mask handling: no division at nulls, finite estimate, recovery with random nulls, and a stale
      (tiled) reference loses the target;
    - the receiver takes no truth and its output does not change when truth metadata is edited;
    - static clutter is cancelled by slow-time mean removal, and a Doppler above half the reference rate lands on
      the predicted alias when only every k-th symbol is used;
    - CFAR false-alarm calibration: a frame threshold set on calibration H0 seeds gives a false-alarm rate
      near the target on disjoint evaluation H0 seeds.

Run (pytest is not installed in this venv; the __main__ block runs every test_ function)
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 \
        /workspace/.venvs/py312/bin/python benchmark/test_ofdm_receiver_pilot_0917.py
    or, where pytest exists: python -m pytest benchmark/test_ofdm_receiver_pilot_0917.py -q
"""
from __future__ import annotations

import copy
import dataclasses
import importlib.util
import inspect
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ofdm_receiver_pilot_0917",
                                               os.path.join(HERE, "ofdm_receiver_pilot_0917.py"))
P = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = P
_spec.loader.exec_module(P)

SMALL = P.System(fc_hz=3.5e9, scs_hz=30e3, fft=128, cp=16, n_sym=64, guard=(20, 19), dc_null=True)
RX = P.RxCfg()


def _single(S, q, kbin, modulation="qpsk", model="grid", null_frac=0.0, seed=0, snr_db=None):
    rng = np.random.default_rng(seed)
    mask = P.make_mask(S, null_frac, rng)
    X = P.payload(rng, S, mask, modulation, S.n_sym)
    tau, f = q / S.fs, kbin / (S.n_sym * S.t_sym)
    paths = [{"tau_s": tau, "f_hz": f, "amp": np.exp(1j * rng.uniform(0, 2 * np.pi))}]
    nv = 0.0 if snr_db is None else 10 ** (-snr_db / 10)
    if model == "time":
        Y = P.demod(P.channel_time(P.tx_time(X, S), S, paths, nv, rng), S, S.n_sym)
    else:
        Y = P.channel_grid(X, S, paths, nv, rng)
    truth = {"target": {"range_m": P.C0 * tau / 2, "f_hz": f}, "ghost": None}
    return X, Y, mask, truth


def test_mask_convention():
    m = P.base_mask(SMALL)
    assert m.sum() == SMALL.fft - sum(SMALL.guard) - 1
    assert not m[SMALL.fft // 2]
    assert np.flatnonzero(m)[0] == SMALL.guard[0]
    assert np.flatnonzero(m)[-1] == SMALL.fft - SMALL.guard[1] - 1
    try:
        from sionna.phy.ofdm import ResourceGrid
    except Exception as exc:                       # optional cross-check only
        print(f"   (sionna ResourceGrid cross-check skipped: {type(exc).__name__})")
        return
    rg = ResourceGrid(num_ofdm_symbols=1, fft_size=SMALL.fft, subcarrier_spacing=SMALL.scs_hz,
                      num_guard_carriers=SMALL.guard, dc_null=True)
    assert np.array_equal(np.asarray(rg.effective_subcarrier_ind), np.flatnonzero(m))


def test_fractional_delay_matches_radar_process():
    sys.path.insert(0, os.path.join(P.ROOT, "src"))
    from radar_process import _delay_doppler
    rng = np.random.default_rng(3)
    x = rng.standard_normal(4096) + 1j * rng.standard_normal(4096)
    R, v = 37.3, 6.2
    ref = _delay_doppler(x, SMALL.fs, R, SMALL.fc_hz, v)
    f = 2 * v * SMALL.fc_hz / P.C0
    ours = P.channel_time(x, SMALL, [{"tau_s": 2 * R / P.C0, "f_hz": f, "amp": 1.0}], 0.0, rng)
    assert np.max(np.abs(ours - ref)) < 1e-9 * np.max(np.abs(ref))


def test_on_grid_recovery():
    res = P.resolution(SMALL)
    for modulation in ("qpsk", "16qam"):
        for model, tol_bins in (("grid", 1e-9), ("time", 0.02)):
            X, Y, mask, truth = _single(SMALL, 5, 3, modulation, model)
            out = P.receiver_grid(Y, X, mask, SMALL, RX)
            sc = P.score(out, truth, SMALL, RX)["strongest"]
            assert abs(sc["range_err_m"]) <= tol_bins * res["range_bin_m"], (modulation, model, sc)
            assert abs(sc["doppler_err_hz"]) <= tol_bins * res["doppler_bin_hz"], (modulation, model, sc)


def test_off_grid_interpolation():
    res = P.resolution(SMALL)
    for dq, dk in ((0.3, 0.0), (0.0, 0.3), (0.5, 0.5), (0.1, 0.4)):
        X, Y, mask, truth = _single(SMALL, 5 + dq, 3 + dk, "qpsk", "grid")
        sc = P.score(P.receiver_grid(Y, X, mask, SMALL, RX), truth, SMALL, RX)["strongest"]
        assert abs(sc["range_err_m"]) <= 0.05 * res["range_bin_m"], (dq, dk, sc)
        assert abs(sc["doppler_err_hz"]) <= 0.05 * res["doppler_bin_hz"], (dq, dk, sc)


def test_null_mask_handling():
    res = P.resolution(SMALL)
    X, Y, mask, truth = _single(SMALL, 6.4, 2.7, "16qam", "time", null_frac=0.1, seed=5)
    assert (~mask).sum() > (~P.base_mask(SMALL)).sum()            # random nulls were added
    assert np.all(X[:, ~mask] == 0)                                # nothing transmitted on nulls
    with np.errstate(divide="raise", invalid="raise"):          # a division by a null would raise here
        out = P.receiver_grid(Y, X, mask, SMALL, RX)
    assert np.isfinite(out["strongest"]["tau_s"]) and np.isfinite(out["strongest"]["f_hz"])
    sc = P.score(out, truth, SMALL, RX)["strongest"]
    assert abs(sc["range_err_m"]) <= 0.1 * res["range_bin_m"], sc
    assert abs(sc["doppler_err_hz"]) <= 0.1 * res["doppler_bin_hz"], sc
    stale = np.tile(X[:1], (SMALL.n_sym, 1))
    st = P.score(P.receiver_grid(Y, stale, mask, SMALL, RX), truth, SMALL, RX)
    assert not st["strongest"]["within_tol"]
    assert 10 * np.log10(st["strongest"]["P"] / out["strongest"]["P"]) < -10


def test_receiver_takes_no_truth_and_ignores_truth_edits():
    params = set(inspect.signature(P.receiver_grid).parameters)
    assert not {"truth", "target", "geometry"} & params
    X, Y, mask, truth = _single(SMALL, 7.2, 4.4, "qpsk", "time", seed=9, snr_db=-20)
    out1 = P.receiver_grid(Y, X, mask, SMALL, RX)
    edited = copy.deepcopy(truth)
    edited["target"]["range_m"] += 100.0
    edited["target"]["f_hz"] *= -1
    out2 = P.receiver_grid(Y, X, mask, SMALL, RX)
    assert out1["strongest"] == out2["strongest"] and out1["frame_stat"] == out2["frame_stat"]
    s1, s2 = P.score(out1, truth, SMALL, RX), P.score(out2, edited, SMALL, RX)
    assert s1["frame_stat"] == s2["frame_stat"]                    # only the scoring sees the edit


def test_static_clutter_cancelled_and_stride_alias():
    rng = np.random.default_rng(11)
    mask = P.base_mask(SMALL)
    X = P.payload(rng, SMALL, mask, "qpsk", SMALL.n_sym)
    clutter = [{"tau_s": 3 / SMALL.fs, "f_hz": 0.0, "amp": 30.0}, {"tau_s": 7.4 / SMALL.fs, "f_hz": 0.0, "amp": 10.0}]
    Y = P.demod(P.channel_time(P.tx_time(X, SMALL), SMALL, clutter, 0.0, rng), SMALL, SMALL.n_sym)
    on = P.receiver_grid(Y, X, mask, SMALL, RX)
    off = P.receiver_grid(Y, X, mask, SMALL, dataclasses.replace(RX, static_removal=False))
    # not exactly zero in the time-domain channel: fractional-delay tails cross symbol boundaries
    assert on["max_P"] < 1e-6 * off["max_P"], (on["max_P"], off["max_P"])
    k = 4
    F = 1.0 / (k * SMALL.t_sym)
    f_true = 0.8 * F                                              # outside +-F/2: must fold to -0.2 F
    tau = 5 / SMALL.fs
    Y = P.channel_grid(X, SMALL, [{"tau_s": tau, "f_hz": f_true, "amp": 1.0}], 0.0, rng)
    cfg = dataclasses.replace(RX, stride=k)
    sc = P.score(P.receiver_grid(Y, X, mask, SMALL, cfg), {"target": {"range_m": P.C0 * tau / 2, "f_hz": f_true},
                                                            "ghost": None}, SMALL, cfg)
    assert abs(sc["f_alias_pred_hz"] - (f_true - F)) < 1e-9
    assert abs(sc["strongest_f_hz"] - sc["f_alias_pred_hz"]) <= 0.05 * P.resolution(SMALL)["doppler_hz"], sc
    assert sc["strongest"]["within_tol"]


def test_cfar_calibration_on_separate_h0_seeds():
    pfa, n = 0.1, 300
    S = dataclasses.replace(SMALL, n_sym=32)

    def frame_stats(stream):
        stats = []
        for i in range(n):
            ss = np.random.SeedSequence(P.CFG["seed_root"], spawn_key=(stream, i))
            r_pay, r_noise = (np.random.default_rng(c) for c in ss.spawn(2))
            mask = P.base_mask(S)
            X = P.payload(r_pay, S, mask, "qpsk", S.n_sym)
            Y = P.channel_grid(X, S, [], 1.0, r_noise)
            stats.append(P.receiver_grid(Y, X, mask, S, RX)["frame_stat"])
        return np.array(stats)

    cal, ev = frame_stats(900), frame_stats(901)
    assert not np.array_equal(cal, ev)
    alpha = float(np.quantile(cal, 1 - pfa, method="higher"))
    assert (cal > alpha).mean() <= pfa
    rate = float((ev > alpha).mean())
    lo, hi = P.wilson(int((ev > alpha).sum()), n)
    assert 0.04 <= rate <= 0.18, (rate, lo, hi)


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as exc:
                failed += 1
                print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    sys.exit(1 if failed else 0)
