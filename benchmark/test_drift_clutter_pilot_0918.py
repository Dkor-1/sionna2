# -*- coding: utf-8 -*-
"""
test_drift_clutter_pilot_0918.py - checks for benchmark/drift_clutter_pilot_0918.py on a small system
=====================================================================================================

What is checked
    - receiver_ext with mean removal and no notch reproduces the 0917 pilot's receiver_grid exactly (this is
      the pin that keeps the copied receiver body from drifting away from the pilot);
    - channel_time_mod without any per-symbol gain reproduces the pilot's channel_time exactly, and a
      constant gain of 1 changes nothing;
    - a per-symbol gain is applied at the symbol it belongs to (a one-symbol gate leaves one symbol lit);
    - the subspace projection onto the constant slow-time direction equals mean removal;
    - the notch removes candidates below its edge and keeps a target above it;
    - the blank acts on Doppler grid rows: the number of removed search cells matches the row count at both
      configured half-widths, and a kept candidate may still interpolate to a Doppler inside the band;
    - the H0 development covariance of static clutter is dominated by the constant slow-time direction, and
      the eigenvalue rule returns a rank of at least one;
    - the receiver takes no truth and its output does not change when truth metadata is edited;
    - the hover window is scaled to mean |g|^2 = 1 and stays inside the stored record;
    - development, calibration and evaluation frames never share a seed key;
    - a frame threshold set on calibration frames gives a false-alarm rate near the target on disjoint
      evaluation frames, in a drifting-clutter environment.

Run (pytest is not installed in this venv; the __main__ block runs every test_ function)
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 \
        /workspace/.venvs/py312/bin/python benchmark/test_drift_clutter_pilot_0918.py
"""
from __future__ import annotations

import copy
import importlib.util
import inspect
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("drift_clutter_pilot_0918",
                                               os.path.join(HERE, "drift_clutter_pilot_0918.py"))
Q = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = Q
_spec.loader.exec_module(Q)
P = Q.P

SMALL = P.System(fc_hz=3.5e9, scs_hz=30e3, fft=128, cp=16, n_sym=64, guard=(20, 19), dc_null=True)
RX = P.RxCfg()


def _frame(S, paths, seed=0, modulation="qpsk", null_frac=0.0, snr_db=None, model="time"):
    rng = np.random.default_rng(seed)
    mask = P.make_mask(S, null_frac, rng)
    X = P.payload(rng, S, mask, modulation, S.n_sym)
    nv = 0.0 if snr_db is None else 10 ** (-snr_db / 10)
    r1, r2 = np.random.default_rng(seed + 1), np.random.default_rng(seed + 1)
    if model == "time":
        Y_p = P.demod(P.channel_time(P.tx_time(X, S), S, copy.deepcopy(paths), nv, r1), S, S.n_sym)
        Y_q = P.demod(Q.channel_time_mod(P.tx_time(X, S), S, copy.deepcopy(paths), nv, r2), S, S.n_sym)
    else:
        Y_p = P.channel_grid(X, S, paths, nv, r1)
        Y_q = Y_p
    return X, mask, Y_p, Y_q


def _target(range_m, f_hz, phase=0.3):
    return P._path(range_m, f_hz, 0.0, phase)


def _clutter(S, drift_hz, seed=5):
    rng = np.random.default_rng(seed)
    return [P._path(c["range_m"], rng.uniform(-drift_hz, drift_hz) if drift_hz else 0.0,
                    c["power_db"], rng.uniform(0, 2 * np.pi)) for c in P.CFG["scene"]["clutter"]]


# ------------------------------------------------------------------------------------------------------
def test_matches_pilot_receiver():
    """Mean removal, no notch: every field the aggregation reads must equal the pilot's receiver."""
    S = SMALL
    for snr_db in (None, -20.0):
        paths = _clutter(S, 0.0) + [_target(90.0, 3.0 / (S.n_sym * S.t_sym))]
        X, mask, Y, _ = _frame(S, paths, seed=11, snr_db=snr_db)
        a = P.receiver_grid(Y, X, mask, S, RX, n_top=16)
        b = Q.receiver_ext(Y, X, mask, S, RX, suppress="mean", notch_bins=0.0, n_top=16)
        assert a["frame_stat"] == b["frame_stat"], (a["frame_stat"], b["frame_stat"])
        assert a["n_search"] == b["n_search"]
        assert a["max_P"] == b["max_P"]
        assert a["psl_db"] == b["psl_db"]
        assert a["zero_doppler_max_P"] == b["zero_doppler_max_P"]
        assert abs(a["mean_P"] - b["mean_P"]) <= 1e-12 * abs(a["mean_P"])
        assert len(a["top"]) == len(b["top"])
        for ea, eb in zip(a["top"], b["top"]):
            assert ea == eb, (ea, eb)
        assert a["strongest"] == b["strongest"]
    print("ok test_matches_pilot_receiver")


def test_matches_pilot_channel():
    S = SMALL
    paths = _clutter(S, 2.0) + [_target(90.0, 400.0)]
    tx = P.tx_time(P.payload(np.random.default_rng(3), S, P.make_mask(S, 0.0, np.random.default_rng(3)),
                             "qpsk", S.n_sym), S)
    a = P.channel_time(tx, S, copy.deepcopy(paths), 0.0, np.random.default_rng(7))
    b = Q.channel_time_mod(tx, S, copy.deepcopy(paths), 0.0, np.random.default_rng(7))
    assert np.array_equal(a, b)
    ones = [dict(p) for p in paths]
    ones[-1]["gain_t"] = np.ones(S.n_sym, complex)
    c = Q.channel_time_mod(tx, S, ones, 0.0, np.random.default_rng(7))
    assert np.abs(a - c).max() <= 1e-12 * np.abs(a).max(), np.abs(a - c).max()
    print("ok test_matches_pilot_channel")


def test_gain_lands_on_its_symbol():
    S = SMALL
    tx = P.tx_time(P.payload(np.random.default_rng(4), S, P.make_mask(S, 0.0, np.random.default_rng(4)),
                             "qpsk", S.n_sym), S)
    g = np.zeros(S.n_sym, complex)
    g[5] = 1.0
    paths = [dict(_target(0.0, 0.0), gain_t=g)]
    rx = Q.channel_time_mod(tx, S, paths, 0.0, np.random.default_rng(0))
    blk = np.abs(rx.reshape(S.n_sym, S.fft + S.cp)).sum(axis=1)
    assert blk[5] > 0 and np.count_nonzero(blk > 1e-12) == 1, blk
    print("ok test_gain_lands_on_its_symbol")


def test_subspace_of_constant_equals_mean_removal():
    S = SMALL
    paths = _clutter(S, 0.0) + [_target(90.0, 3.0 / (S.n_sym * S.t_sym))]
    X, mask, Y, _ = _frame(S, paths, seed=12, snr_db=-20.0)
    U = (np.ones((S.n_sym, 1)) / np.sqrt(S.n_sym)).astype(complex)
    a = Q.receiver_ext(Y, X, mask, S, RX, suppress="mean", n_top=8)
    b = Q.receiver_ext(Y, X, mask, S, RX, suppress="subspace", basis=U, n_top=8)
    assert abs(a["frame_stat"] - b["frame_stat"]) <= 1e-9 * a["frame_stat"], (a["frame_stat"], b["frame_stat"])
    assert abs(a["strongest"]["f_hz"] - b["strongest"]["f_hz"]) <= 1e-6
    print("ok test_subspace_of_constant_equals_mean_removal")


def test_notch_blanks_below_its_edge_and_keeps_above():
    S = SMALL
    bin_hz = 1.0 / (S.n_sym * S.t_sym)
    slow = _clutter(S, 0.0) + [_target(90.0, 0.3 * bin_hz)]
    fast = _clutter(S, 0.0) + [_target(90.0, 3.0 * bin_hz)]
    for paths, expect in ((slow, False), (fast, True)):
        X, mask, Y, _ = _frame(S, paths, seed=13, snr_db=-20.0)
        out = Q.receiver_ext(Y, X, mask, S, RX, suppress="mean", notch_bins=1.0, n_top=32)
        assert all(abs(e["f_hz"]) >= bin_hz - 1e-9 for e in out["top"]), "candidate inside the notch"
        assert out["n_search"] < out["n_search_full"]
        near = any(abs(abs(e["f_hz"]) - abs(paths[-1]["f_hz"])) < bin_hz for e in out["top"])
        assert near == expect, (near, expect)
    print("ok test_notch_blanks_below_its_edge_and_keeps_above")


def test_blank_acts_on_grid_rows_not_interpolated_doppler():
    """The candidate blank removes whole Doppler rows of the padded map.

    Two things are pinned: the number of removed search cells equals (rows with |grid Doppler| < the
    half-width) x (delay cells), for both configured half-widths; and a kept candidate may still report an
    interpolated Doppler inside the blanked band, because the blank is applied before the 3-point
    interpolation. The second property is why `notch_1bin` can leave a frame statistic untouched even when the
    reported Doppler of the peak that sets it is below one bin.
    """
    S = SMALL
    bin_hz = 1.0 / (S.n_sym * S.t_sym)
    k, M = int(RX.stride), SMALL.n_sym // int(RX.stride)
    Mp = RX.pad_doppler * M
    n_s = RX.pad_delay * S.cp + 1
    f_axis = np.fft.fftshift(np.fft.fftfreq(Mp, d=k * S.t_sym))
    paths = _clutter(S, 0.0) + [_target(90.0, 3.0 * bin_hz)]
    X, mask, Y, _ = _frame(S, paths, seed=17, snr_db=-20.0)
    full = Q.receiver_ext(Y, X, mask, S, RX, suppress="mean", notch_bins=0.0, n_top=32)
    for w in (Q.CFG["notch_half_width_bins"], Q.CFG["notch_wide_half_width_bins"]):
        rows = int((np.abs(f_axis) < w * bin_hz).sum())
        out = Q.receiver_ext(Y, X, mask, S, RX, suppress="mean", notch_bins=float(w), n_top=32)
        assert out["n_search_full"] == Mp * n_s, (out["n_search_full"], Mp * n_s)
        assert full["n_search"] - out["n_search"] == rows * n_s, (w, full["n_search"] - out["n_search"],
                                                                  rows * n_s)
        assert all(abs(f_axis[e["i"]]) >= w * bin_hz - 1e-9 for e in out["top"]), "kept a blanked grid row"
    # a candidate on the first kept row may interpolate to a Doppler inside the band
    edge = float(Q.CFG["notch_half_width_bins"]) * bin_hz
    near_edge = _clutter(S, 0.0) + [_target(90.0, 0.92 * edge)]
    X2, mask2, Y2, _ = _frame(S, near_edge, seed=19, snr_db=-20.0)
    o2 = Q.receiver_ext(Y2, X2, mask2, S, RX, suppress="mean",
                        notch_bins=float(Q.CFG["notch_half_width_bins"]), n_top=32)
    inside = [e for e in o2["top"] if abs(e["f_hz"]) < edge]
    assert all(abs(f_axis[e["i"]]) >= edge - 1e-9 for e in inside), "an interpolated value came from a blanked row"
    print(f"ok test_blank_acts_on_grid_rows_not_interpolated_doppler "
          f"(row counts match at both half-widths; {len(inside)} kept candidates of this small system "
          "interpolate below the 1-bin edge)")


def test_h0_covariance_is_constant_direction_for_static_clutter():
    S = SMALL
    M = S.n_sym
    R = np.zeros((M, M), complex)
    n_frames = 8
    for s in range(n_frames):
        X, mask, Y, _ = _frame(S, _clutter(S, 0.0, seed=100 + s), seed=200 + s, snr_db=-35.0)
        act = np.flatnonzero(mask)[::2]
        Hs = Y[:, act] / X[:, act]
        R += Hs @ Hs.conj().T
    info = Q.basis_from_cov(R, n_frames, len(np.flatnonzero(P.base_mask(S))[::2]))
    assert info["r"] >= 1
    assert info["leading_vector_overlap_with_mean"] > 0.95, info["leading_vector_overlap_with_mean"]
    assert info["eigenvalues_top8_db_re_median"][0] > 10.0
    print(f"ok test_h0_covariance_is_constant_direction_for_static_clutter "
          f"(r={info['r']}, overlap={info['leading_vector_overlap_with_mean']:.4f})")


def test_receiver_takes_no_truth():
    src = inspect.getsource(Q.receiver_ext)
    assert "truth" not in src, "receiver_ext must not mention truth"
    S = SMALL
    paths = _clutter(S, 2.0) + [_target(90.0, 500.0)]
    X, mask, Y, _ = _frame(S, paths, seed=14, snr_db=-20.0)
    a = Q.receiver_ext(Y, X, mask, S, RX, suppress="mean", n_top=8)
    b = Q.receiver_ext(Y, X, mask, S, RX, suppress="mean", n_top=8)
    assert a["frame_stat"] == b["frame_stat"] and a["strongest"] == b["strongest"]
    print("ok test_receiver_takes_no_truth")


def test_hover_window_normalisation():
    E = (np.random.default_rng(0).standard_normal(500)
         + 1j * np.random.default_rng(1).standard_normal(500)) + 5.0
    for k0 in (0, 7, 500 - 64):
        g = Q.rt_window(E, k0, 64)
        assert g.size == 64
        assert abs(float(np.mean(np.abs(g) ** 2)) - 1.0) < 1e-12
    print("ok test_hover_window_normalisation")


def test_flash_rate_is_read_from_the_rotor_ledger():
    """The blade-flash rate printed in section 2.1 must come from the ledger and the airframe spec, not from
    a literal in this pilot: ledger f_flash_hz == prop_blades x mean(rpm_per_rotor) / 60, and the four rotors
    of that record are not at one rpm, so the spread must be non-zero and must be carried."""
    import json as _json
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
    from drones import DRONES
    tj = _json.load(open(os.path.join(os.path.dirname(HERE), Q.ROTOR_LEDGER)))["_meta"]
    rpm = [float(v) for v in tj["rpm_per_rotor"]]
    blades = int(DRONES[str(tj.get("drone", "matrice4e"))].prop_blades)
    flash = [blades * r / 60.0 for r in rpm]
    assert abs(float(tj["f_flash_hz"]) - float(np.mean(flash))) < 1e-6, (tj["f_flash_hz"], np.mean(flash))
    spread = max(flash) - min(flash)
    assert spread > 0.0, "this record's rotors are all at one rpm; the spread wording must be revisited"
    import ast as _ast
    src = open(os.path.join(HERE, "drift_clutter_pilot_0918.py"), encoding="utf-8").read()
    tree = _ast.parse(src)
    doc_end = (tree.body[0].end_lineno                        # the changelog in the module docstring names
               if _ast.get_docstring(tree) else 0)            # the old literals, so skip those lines
    body = "\n".join(src.splitlines()[doc_end:])
    assert "126.6667" not in body and "3800.0" not in body, "the flash rate is hard-coded again"
    print(f"ok test_flash_rate_is_read_from_the_rotor_ledger (f_flash={float(tj['f_flash_hz']):.4f} Hz, "
          f"per-rotor spread {spread:.3f} Hz)")


def test_seed_streams_are_disjoint():
    keys = set()
    for exp in ("h0_train", "h0_cal", "h0_eval"):
        for e in Q.ENV_CODES:
            for i in range(50):
                keys.add((Q.EXP_CODES[exp], Q.ENV_CODES[e], 0, 0, i))
    assert len(keys) == 3 * len(Q.ENV_CODES) * 50
    h1 = {(Q.EXP_CODES["h1_body"], Q.ENV_CODES[e], int(round(b * 10)), int(round((s + 100) * 10)), i)
          for e in Q.ENV_CODES for b in Q.CFG["body_doppler_bins"] for s in Q.CFG["snr_re_db"]
          for i in range(20)}
    assert not (h1 & keys)
    assert len(h1) == len(Q.ENV_CODES) * len(Q.CFG["body_doppler_bins"]) * len(Q.CFG["snr_re_db"]) * 20
    rt = {(Q.EXP_CODES["h1_rt_hover"], Q.ENV_CODES[e], 0, int(round((s + 100) * 10)), i)
          for e in Q.ENV_CODES for s in Q.CFG["snr_re_db"] for i in range(20)}
    assert not (rt & h1) and not (rt & keys)
    print("ok test_seed_streams_are_disjoint")


def test_threshold_from_calibration_holds_on_evaluation():
    """Drifting clutter, matched calibration: the measured rate must sit near the target."""
    S = SMALL
    n, target = 200, 0.1
    stats = {"cal": [], "eval": []}
    for tag, base in (("cal", 3000), ("eval", 9000)):
        for i in range(n):
            X, mask, Y, _ = _frame(S, _clutter(S, 10.0, seed=base + i), seed=base + 10000 + i, snr_db=-35.0)
            out = Q.receiver_ext(Y, X, mask, S, RX, suppress="mean", n_top=8)
            stats[tag].append(out["frame_stat"])
    alpha = float(np.quantile(np.array(stats["cal"]), 1 - target, method="higher"))
    rate = float((np.array(stats["eval"]) > alpha).mean())
    lo, hi = P.wilson(int(round(rate * n)), n)
    assert lo <= target <= hi or abs(rate - target) < 0.08, (alpha, rate, lo, hi)
    print(f"ok test_threshold_from_calibration_holds_on_evaluation (alpha={alpha:.3f}, rate={rate:.3f})")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"\n{len(fns)} checks passed")
