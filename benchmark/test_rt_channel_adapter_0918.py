# -*- coding: utf-8 -*-
"""
test_rt_channel_adapter_0918.py - checks for benchmark/rt_channel_adapter_0918.py
=================================================================================

What is checked
    - the carrier phase is applied exactly once: `amp = a * exp(-2j*pi*fc*tau)`, and the sum over the
      listed paths with any interaction reproduces the stored complex field E;
    - the absolute delay survives the adapter (nothing re-centres or normalises it);
    - the fast static channels equal the pilot's own channels: `static_frame_ramp` against a direct
      exponential sum, `channel_time_static` against `PILOT.channel_time`, `channel_grid_static`
      against `PILOT.channel_grid`;
    - `circular_block_rx` on one continuous block equals `PILOT.channel_time`, and the linear stream
      does not wrap (the samples before a burst stay zero while the circular model fills them);
    - path classes follow the sidecar `part` names, and no truth reaches the receiver;
    - the alignment checks fail when the pose mapping is broken on purpose;
    - the carrier is read from the arm name (`_fc<MHz>`, else the sweep's convention 3.5 GHz);
    - the field sum also carries an order-independent reference and the cancellation it runs into;
    - the Q0-b Doppler-zero control separates the intra-symbol-Doppler floor from the delay behaviour;
    - `usable_fft_fraction` follows its stated definition;
    - (2026-09-18 review) the delay-search span matches `receiver_grid`'s own delay grid, a cell whose
      object ids are unknown is refused rather than silently dropped, and the arm-name carrier read
      agrees with `src/arm_grammar.py`.

Run (pytest is not installed in this venv; the __main__ block runs every test_ function)
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" MPLBACKEND=Agg nice -n 19 taskset -c 8-15 \
        /workspace/.venvs/py312/bin/python benchmark/test_rt_channel_adapter_0918.py
"""
from __future__ import annotations

import importlib.util
import inspect
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("rt_channel_adapter_0918",
                                               os.path.join(HERE, "rt_channel_adapter_0918.py"))
A = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = A
_spec.loader.exec_module(A)
P = A.PILOT

SMALL = P.System(fc_hz=3.5e9, scs_hz=30e3, fft=128, cp=16, n_sym=32, guard=(20, 19), dc_null=True)
FC = 3.5e9


def _have_data() -> bool:
    return all(os.path.exists(A.shard_path(s, sh)) and os.path.exists(A.sidecar_path(s, sh))
               for s in A.PAIR.values() for sh in A.SHARDS)


def _rand_paths(rng, n, tau_lo, tau_hi, f_hz=0.0):
    tau = rng.uniform(tau_lo, tau_hi, n)
    amp = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    return [{"tau_s": float(t), "f_hz": f_hz, "amp": complex(c)} for t, c in zip(tau, amp)]


# ---------------------------------------------------------------------------------------------------
def test_carrier_phase_applied_once_and_field_matches():
    if not _have_data():
        print("   (skipped: stored shards or sidecars are not present)")
        return
    cell = A.load_cell(A.PAIR["ground"], "00")
    cell["fc_hz"] = FC
    pp = A.pose_paths(cell, 0)
    expect = pp["a"] * np.exp(-2j * np.pi * FC * pp["tau_s"])
    assert np.allclose(pp["amp"], expect, rtol=0, atol=0)
    # applying it a second time must be a different channel - this is the trap the brief names
    twice = pp["amp"] * np.exp(-2j * np.pi * FC * pp["tau_s"])
    assert not np.allclose(pp["amp"], twice)
    E = complex(pp["amp"][pp["hit"]].sum())
    t = int(np.flatnonzero(cell["slot"] == 0)[0])
    stored = cell["E"][cell["slot"][t]]
    assert abs(E - stored) / abs(stored) < 1e-4, abs(E - stored) / abs(stored)


def test_absolute_delay_preserved():
    if not _have_data():
        print("   (skipped: stored shards or sidecars are not present)")
        return
    cell = A.load_cell(A.PAIR["ground"], "00")
    cell["fc_hz"] = FC
    pp = A.pose_paths(cell, 0)
    s = int(cell["off"][0])
    assert np.array_equal(pp["tau_s"], cell["tau"][s:s + pp["tau_s"].size])
    assert pp["tau_s"].min() > 0.0
    # the shortest path of the ground cell is the radar's own nadir reflection, 2h/c
    assert 1.0 < pp["tau_s"].min() * A.C0 / 2 < 2.0, pp["tau_s"].min() * A.C0 / 2


def test_static_frame_ramp_matches_direct_sum():
    rng = np.random.default_rng(3)
    L = 2 * (SMALL.fft + SMALL.cp) * 8
    tau = rng.uniform(0, 8 / SMALL.fs, 17)
    amp = rng.standard_normal(17) + 1j * rng.standard_normal(17)
    f = np.fft.fftfreq(L, d=1.0 / SMALL.fs)
    direct = np.exp(-2j * np.pi * np.outer(f, tau)) @ amp
    for block in (8, 16, 15):                       # 15 does not divide L/2 -> fallback branch
        got = A.static_frame_ramp(L, SMALL.fs, amp, tau, block=block)
        assert np.abs(got - direct).max() / np.abs(direct).max() < 1e-12, block


def test_channel_time_static_matches_pilot():
    rng = np.random.default_rng(4)
    mask = P.base_mask(SMALL)
    X = P.payload(rng, SMALL, mask, "qpsk", SMALL.n_sym)
    tx = P.tx_time(X, SMALL)
    paths = _rand_paths(rng, 11, 0.0, 10 / SMALL.fs)
    ref = P.channel_time(tx, SMALL, paths, 0.0, rng)
    got = A.channel_time_static(tx, SMALL, np.array([p["amp"] for p in paths]),
                                np.array([p["tau_s"] for p in paths]))
    assert np.abs(got - ref).max() / np.abs(ref).max() < 1e-12


def test_channel_grid_static_matches_pilot():
    rng = np.random.default_rng(5)
    mask = P.base_mask(SMALL)
    X = P.payload(rng, SMALL, mask, "qpsk", SMALL.n_sym)
    paths = _rand_paths(rng, 7, 0.0, 10 / SMALL.fs)
    ref = P.channel_grid(X, SMALL, paths, 0.0, rng)
    got = A.channel_grid_static(X, SMALL, np.array([p["amp"] for p in paths]),
                                np.array([p["tau_s"] for p in paths]))
    assert np.abs(got - ref).max() / np.abs(ref).max() < 1e-12


def test_circular_block_matches_pilot_channel_time():
    rng = np.random.default_rng(6)
    mask = P.base_mask(SMALL)
    X = P.payload(rng, SMALL, mask, "qpsk", SMALL.n_sym)
    slots = np.arange(SMALL.n_sym)
    x = A.build_stream(X, SMALL, slots, SMALL.n_sym)
    paths = [{"tau_s": 5 / SMALL.fs, "f_hz": 0.0, "amp": 1 + 0.3j},
             {"tau_s": 9 / SMALL.fs, "f_hz": 137.0, "amp": -0.4 + 0.2j}]
    ref = P.channel_time(P.tx_time(X, SMALL), SMALL, paths, 0.0, rng)
    got = A.circular_block_rx(x, SMALL, paths, slots, SMALL.n_sym, tail=0)
    assert np.abs(got - ref).max() / np.abs(ref).max() < 1e-12


def test_linear_stream_does_not_wrap_but_circular_does():
    rng = np.random.default_rng(7)
    mask = P.base_mask(SMALL)
    n_act = 8
    X = P.payload(rng, SMALL, mask, "qpsk", n_act)
    S = P.System(SMALL.fc_hz, SMALL.scs_hz, SMALL.fft, SMALL.cp, n_act, SMALL.guard, SMALL.dc_null)
    slots = A.schedule("two_bursts", 32, n_act)
    x = A.build_stream(X, S, slots, 32)
    d = 9
    paths = [{"tau_s": d / S.fs, "f_hz": 0.0, "amp": 1.0 + 0j}]
    tail = 4 * (S.fft + S.cp)
    y_lin = A.linear_stream_rx(x, S, paths, tail)
    y_cir = A.circular_block_rx(x, S, paths, slots, 32, tail)
    Lb = S.fft + S.cp
    assert np.abs(y_lin[:d]).max() == 0.0                       # nothing precedes the first burst
    assert np.abs(y_cir[:d]).max() > 0.0                        # the block's own tail wound around
    s2 = int(slots[n_act // 2]) * Lb                            # first sample of the second burst
    assert np.abs(y_lin[s2:s2 + d]).max() == 0.0                # the idle gap really is idle
    assert np.abs(y_cir[s2:s2 + d]).max() > 0.0
    # the tail after the last burst carries the delayed copy in the linear model only
    end = (int(slots[-1]) + 1) * Lb
    assert np.abs(y_lin[end:end + d]).max() > 0.0
    assert np.abs(y_cir[end:end + d]).max() == 0.0


def test_path_class_from_part_names():
    names = ["matrice4e_body", "matrice4e_prop", "env_ground"]
    part = np.array([[0, 2, 0, -1],
                     [-1, -1, 2, -1]], np.int16)
    got = A.path_class(part, names)
    assert list(got) == [A.CLASSES.index("drone_only"), A.CLASSES.index("env_only"),
                         A.CLASSES.index("mixed"), A.CLASSES.index("no_interaction")]


def test_class_masks_partition_the_listed_paths():
    if not _have_data():
        print("   (skipped: stored shards or sidecars are not present)")
        return
    cell = A.load_cell(A.PAIR["ground"], "00")
    cell["fc_hz"] = FC
    pp = A.pose_paths(cell, 0)
    drone = A.class_mask(pp, "drone")
    env = A.class_mask(pp, "env")
    mixed = A.class_mask(pp, "drone_mixed") & ~drone
    assert int(drone.sum() + env.sum() + mixed.sum()) == int(A.class_mask(pp, "all").sum())
    assert env.sum() >= 1 and mixed.sum() >= 1


def test_receiver_gets_no_truth_and_ignores_path_order():
    rng = np.random.default_rng(8)
    amp = rng.standard_normal(20) + 1j * rng.standard_normal(20)
    tau = rng.uniform(0, 10 / SMALL.fs, 20)
    src = inspect.getsource(A.receiver_on_paths)
    assert "truth" not in src and "PILOT.receiver_grid(Y, X, mask, S, cfgrx" in src
    o1 = A.receiver_on_paths(SMALL, amp, tau, "hann", "grid", seed=1)
    perm = rng.permutation(20)
    o2 = A.receiver_on_paths(SMALL, amp[perm], tau[perm], "hann", "grid", seed=1)
    assert np.abs(o1["map"]["P"] - o2["map"]["P"]).max() / o1["map"]["P"].max() < 1e-10


def test_alignment_checks_fail_on_a_broken_mapping():
    if not _have_data():
        print("   (skipped: stored shards or sidecars are not present)")
        return
    cell = A.load_cell(A.PAIR["open_sky"], "00")
    assert A.check_alignment(cell)["pose_equals_idx_at_slot"] is True
    bad = dict(cell)
    bad["pose"] = cell["pose"] + 2                              # one interleave step off
    assert A.check_alignment(bad)["pose_equals_idx_at_slot"] is False
    bad2 = dict(cell)
    bad2["n_paths"] = cell["n_paths"].copy()
    bad2["n_paths"][3] += 1
    assert A.check_alignment(bad2)["nret_equals_sidecar_n_paths"] is False


def test_pair_differs_in_environment_fields_only():
    fields = {}
    for scene, stem in A.PAIR.items():
        arm = stem.rsplit("_el", 1)[0]
        f = A.arm_parse(arm)
        assert A.arm_unparse(f) == arm
        fields[scene] = {k: v for k, v in f.items() if v not in (None, "", False)}
    a, b = fields["open_sky"], fields["ground"]
    diff = sorted(set(a) ^ set(b)) + sorted(k for k in set(a) & set(b) if a[k] != b[k])
    assert diff == ["env", "env_alt"], diff


def test_usable_fft_fraction_definition():
    inside = [{"tau_s": 10 / SMALL.fs, "f_hz": 0.0, "amp": 1.0}]
    beyond = [{"tau_s": (SMALL.cp + 20) / SMALL.fs, "f_hz": 0.0, "amp": 1.0}]
    slots = np.arange(4)
    assert A.usable_fft_fraction(SMALL, inside, slots) == 1.0
    assert abs(A.usable_fft_fraction(SMALL, beyond, slots) - (SMALL.fft - 20) / SMALL.fft) < 1e-12


def test_carrier_from_arm():
    assert A.carrier_from_arm(A.PAIR["open_sky"]) == 3.5e9
    assert A.carrier_from_arm(A.PAIR["ground"]) == 3.5e9
    assert A.carrier_from_arm("sionna_p4000000000_swR0D0E0F1_r15_n1024_envoutdoor01_fc3450_rt210") == 3.45e9
    assert A.carrier_from_arm("sionna_p4e9_partsfc_r15_rt210") == 3.5e9        # the `fc` part group


def test_field_sum_reference_sum_and_cancellation():
    if not _have_data():
        print("   (skipped: stored shards or sidecars are not present)")
        return
    cell = A.load_cell(A.PAIR["open_sky"], "00")
    t = 8                                                     # a short slice keeps the test quick
    e = int(cell["off"][t])
    small = dict(cell, slot=cell["slot"][:t], off=cell["off"][:t + 1], a=cell["a"][:e],
                 tau=cell["tau"][:e], part=cell["part"][:, :e])
    r = A.check_field_sum(small, FC)
    assert r["path_sum_rel_err_max"] < A.TOL["path_sum_rel_err"]
    assert r["path_sum_rel_err_fsum_max"] < 1e-12             # order-independent reference
    assert 1.0 <= r["cancellation_sum_abs_over_abs_E_max"] < 1e3
    assert 0.0 <= r["path_sum_bit_identical_fraction"] <= 1.0


def test_q0b_doppler_zero_control_separates_the_floor_from_the_delay():
    r = A.q0b(quick=True)
    rows = {(x["schedule"], x["delay_case"]): x for x in r["rows"]}
    ic, bc = rows[("continuous", "inside_cp")], rows[("continuous", "beyond_cp")]
    # inside the CP with the Doppler removed, both models reproduce the analytic response exactly
    assert ic["linear_field_residual_doppler_zero_db"] < -200
    assert ic["circular_field_residual_doppler_zero_db"] < -200
    # with the target moving, the floor is the same for the two models: it is not a model difference
    assert abs(ic["linear_field_residual_db"] - ic["circular_field_residual_db"]) < 1.0
    assert -100 < ic["linear_field_residual_db"] < -20
    # beyond the CP the residual survives the Doppler-zero control - it follows the delay
    assert bc["linear_field_residual_doppler_zero_db"] > -60
    assert bc["circular_field_residual_doppler_zero_db"] > -60


def test_schedules_are_paired():
    a = A.schedule("continuous", 512, 256)
    b = A.schedule("two_bursts", 512, 256)
    assert a.size == b.size == 256
    assert a.max() < 512 and b.max() == 511 and b.min() == 0


def test_delay_search_span_matches_the_receiver_grid():
    """The stated span must be the receiver's own last delay cell, not a number written beside it."""
    for S in (SMALL, P.build_system(A.BANDS["bw20"]["system"])):
        cfg = P.RxCfg()
        out = P.receiver_grid(np.zeros((S.n_sym, S.fft), complex), np.ones((S.n_sym, S.fft), complex),
                              P.base_mask(S), S, cfg, return_map=True)
        last = float(out["map"]["tau_axis"][-1]) * A.C0 / 2
        assert abs(A.delay_search_max_range_m(S, cfg) - last) < 1e-9
        assert abs(last - S.cp / S.fs * A.C0 / 2) < 1e-9        # it is exactly the CP


def test_q0b_rows_flag_targets_outside_the_delay_grid():
    r = A.q0b(quick=True)
    for row in r["rows"]:
        inside = row["target_range_m"] <= row["delay_search_max_range_m"]
        assert row["target_in_delay_search_span"] == inside
        assert ("ghost" not in k for k in row)
    cases = {x["delay_case"]: x for x in r["rows"] if x["schedule"] == "continuous"}
    assert cases["inside_cp"]["target_in_delay_search_span"] is True
    assert cases["near_cp_edge"]["target_in_delay_search_span"] is True
    assert cases["beyond_cp"]["target_in_delay_search_span"] is False
    assert not any(k.endswith("ghost_peak_db") for k in cases["inside_cp"])
    assert "linear_nf_highest_other_peak_db" in cases["inside_cp"]


def test_draw_spread_separates_draw_from_configuration():
    """The block must actually vary the draw, and must show what the single row cannot."""
    r = A.q0b(quick=True)["draw_spread"]
    assert r["n_draws"] >= 2
    for key, v in r["spread"].items():
        # the field residual is a property of the configuration
        assert v["linear_field_residual_db"]["spread"] < 1.0
        # the edge residual is not: different payloads wrap different symbols
        assert v["waveform_residual_edge_db"]["spread"] > 0.0
        if key.endswith("|beyond_cp"):
            assert v["linear_nf_delay_bias_m"]["spread"] > 1.0
        else:
            assert v["linear_nf_delay_bias_m"]["spread"] < 1.0


def test_a_cell_with_unknown_object_ids_is_refused():
    """`path_class` files a `part == -2` path under `no_interaction`; the sweep's E keeps it. Refuse."""
    if not _have_data():
        return
    cells = {}
    for scene, stem in A.PAIR.items():
        for sh in A.SHARDS:
            cells[(scene, sh)] = A.load_cell(stem, sh)
    cells[("ground", "00")]["n_unknown_id"] = 3
    try:
        A.q0a(cells, quick=True)
    except SystemExit as e:
        assert "missing from that pose's map" in str(e)
        return
    raise AssertionError("q0a accepted a cell with unknown object ids")


def test_carrier_read_agrees_with_the_arm_grammar():
    if not _have_data():
        return
    for scene, stem in A.PAIR.items():
        arm = stem.rsplit("_el", 1)[0]
        f = A.arm_parse(arm)
        assert A.arm_unparse(f) == arm
        tag = f.get("fc")
        expect = 3.5e9 if tag is None else float(tag) * 1e6
        assert A.carrier_from_arm(stem) == expect


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    bad = 0
    for n, f in fns:
        try:
            f()
            print(f"  ok   {n}")
        except AssertionError as e:                             # noqa: PERF203
            bad += 1
            print(f"  FAIL {n}: {e}")
        except Exception as e:                                  # noqa: BLE001
            bad += 1
            print(f"  ERR  {n}: {type(e).__name__}: {e}")
    print(f"\n  {len(fns) - bad}/{len(fns)} passed")
    sys.exit(1 if bad else 0)
