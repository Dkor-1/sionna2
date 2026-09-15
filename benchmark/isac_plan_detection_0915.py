# -*- coding: utf-8 -*-
"""
isac_plan_detection_0915.py -- what the current detection code does, and what tracking still needs
=====================================================================================================
Purpose
    Ledger builder for the ISAC detection+tracking plan report. It recomputes, on one CPU core,
    the behaviour of the current single-CPI passive detection chain (ECA -> range-Doppler map ->
    CA-CFAR -> peak pick) for review findings 1-5 and 14, and it inventories which tracking
    components exist in src/ and benchmark/. Every number in the ledger is computed here from repo
    code, repo ledgers or fixed-seed synthetic signals. Repo text facts are re-read at run time: the
    script opens the file, checks that the stated line contains the quoted text, and stores the
    path, line, quote and sha256.

Run
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/isac_plan_detection_0915.py
    Optional arguments:
      --core N     pin the process to CPU core N (default: lowest core in the current affinity)
      --root PATH  repository root (default: parent of this script's directory)
      --out PATH   output ledger (default: ROOT/outputs/isac_plan_detection_0915.json)

Runtime
    About 45-90 seconds on one core (measured 48 s and 70 s). The report12 L1 map (f4) dominates.

Scope
    Simulation / code / bookkeeping checks only. No value here is compared against RF measurements.
    Detection maps are synthetic (analytic echoes, QPSK references, Gaussian noise).
"""
from __future__ import annotations

import argparse
import os
import sys

NAME = "isac_plan_detection_0915"


def _parse_args():
    ap = argparse.ArgumentParser(description="Detection facts and tracking gaps ledger (CPU only).")
    ap.add_argument("--core", type=int, default=None,
                    help="single CPU core to pin (default: lowest core in current affinity)")
    ap.add_argument("--root", default=None, help="repository root (default: parent of script dir)")
    ap.add_argument("--out", default=None, help="output JSON path (default: ROOT/outputs/<name>.json)")
    return ap.parse_args()


ARGS = _parse_args()
# CPU only, one core. Affinity must be set before numpy/torch/sionna are imported:
# thread-count variables alone do not bound every runtime.
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["SIONNA2_ALLOW_CPU"] = "1"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_k] = "1"
_AFFINITY_BEFORE = sorted(os.sched_getaffinity(0))
CORE = int(ARGS.core) if ARGS.core is not None else int(_AFFINITY_BEFORE[0])
os.sched_setaffinity(0, {CORE})

import ast                      # noqa: E402
import fnmatch                  # noqa: E402
import hashlib                  # noqa: E402
import importlib.metadata       # noqa: E402
import inspect                  # noqa: E402
import json                     # noqa: E402
import re                       # noqa: E402
import subprocess               # noqa: E402
import time                     # noqa: E402
import types                    # noqa: E402
import warnings                 # noqa: E402
from datetime import datetime, timezone   # noqa: E402
from pathlib import Path        # noqa: E402

import numpy as np              # noqa: E402
import torch                    # noqa: E402

torch.set_num_threads(1)
try:
    torch.set_num_interop_threads(1)
except RuntimeError:
    pass

ROOT = Path(ARGS.root).resolve() if ARGS.root else Path(__file__).resolve().parents[1]
OUT = Path(ARGS.out).resolve() if ARGS.out else ROOT / "outputs" / f"{NAME}.json"
for _p in (ROOT / "src",):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

T0 = time.time()
STARTED = datetime.now(timezone.utc).isoformat(timespec="seconds")

# --------------------------------------------------------------------------- #
#  Configuration inputs (seeds, grids, sizes). These are inputs, not results.
# --------------------------------------------------------------------------- #
SEEDS = {
    "f1f2_reference_qpsk": 20260915,
    "f1_montecarlo_torch": 7,
    "f3_reference_qpsk": 11,
    "f4_background_map": 11,
    "f4_l1_noise_torch": 1,
    "f5_signals": 12,
    "f14_probe_seeds": [915, 1, 2, 3],
}
CONFIG = {
    "f1f2": dict(Lf=256, M=32, fs_hz=256000.0, delay_samples=9, doppler_bin=6, echo_amplitude=0.02,
                 meta_rb_values_m=[200.0, 300.0]),
    "f1": dict(K=192, batch=16, noise_sigma=1.0, pfa=1e-3, n_elements=4,
               true_az_deg=30.0, wrong_az_deg=-40.0, el_deg=0.0),
    "f2": dict(fs_list_hz=[20e6, 30.72e6, 122.88e6], kernel_delays_samples=[5, 20],
               impulse_length=256, impulse_index=32),
    "f3": dict(Lf=256, M=56, delay_samples=9,
               doppler_bins=[0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0],
               sensitivity_configs=[dict(config_id="Lf128_M64_taps16_ridge0", Lf=128, M=64, n_taps=16,
                                         ridge_rel=0.0, delay_samples=7),
                                    dict(config_id="Lf256_M56_taps40_ridge0", Lf=256, M=56, n_taps=40,
                                         ridge_rel=0.0, delay_samples=9)],
               speed_bins=[0.1, 1.0]),
    "f4": dict(map_doppler_rows=64, map_range_bins=32, strong_cell_db=list(range(60, 111, 5)),
               strong_cell_zero_doppler=dict(row=32, col=2), strong_cell_off_ridge=dict(row=10, col=2),
               excluded_rows_half_width=2, pfa=1e-4, l1_mode="L1", l1_n_rx=[1, 4]),
    "f5": dict(Lf=256, M=32, fs_hz=256000.0, n_range=32, pfa=1e-4, noise_sigma=1.0,
               targets=[dict(amplitude=3.0, delay_samples=5, doppler_bin=6),
                        dict(amplitude=1.5, delay_samples=14, doppler_bin=-9)],
               peak_batch_guard_zd=2),
    "f14": dict(delay_samples=7, doppler_bin=5, n_range_max=32,
                configs=[(915, 32, 128), (1, 32, 128), (2, 32, 128), (3, 32, 128),
                         (915, 16, 128), (915, 64, 128), (915, 32, 512), (915, 128, 1024)],
                pyapril_scenario_std="nr", pyapril_r_max=64, pyapril_fd_max_hz=200.0),
    "inventory": dict(roots=["src", "benchmark"], file_glob="*.py", exclude_glob="*isac*0915*",
                      max_examples=3),
}

# External specification / literature values. Only one is used, as a cross-check of a repo constant.
SOURCES = [
    dict(id="si_speed_of_light", value=299792458.0, unit="m/s",
         url="https://www.bipm.org/en/publications/si-brochure",
         document="BIPM, The International System of Units (SI Brochure), 9th edition (2019)",
         locator="Section 2.2 'Definition of the SI', Table 1 (seven defining constants), speed of light in vacuum",
         note="Exact defining constant. Used only to check that the repo constant C0 used in all "
              "calculations equals it; no calculation takes the value from this table."),
]

# --------------------------------------------------------------------------- #
#  Bookkeeping helpers
# --------------------------------------------------------------------------- #
HASHES: dict = {}
_LINES: dict = {}
QUOTES: list = []


def _rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def lines_of(relpath: str) -> list:
    if relpath not in _LINES:
        b = (ROOT / relpath).read_bytes()
        HASHES[relpath] = hashlib.sha256(b).hexdigest()
        _LINES[relpath] = b.decode("utf-8").splitlines()
    return _LINES[relpath]


def quote(relpath: str, line: int, text: str) -> dict:
    """Check that `line` of `relpath` contains `text`; record the result either way."""
    ls = lines_of(relpath)
    ok = 1 <= line <= len(ls) and text in ls[line - 1]
    found = [i + 1 for i, s in enumerate(ls) if text in s]
    rec = dict(path=relpath, line=int(line), quote=text, verified=bool(ok),
               lines_containing_quote=found[:10], sha256=HASHES[relpath])
    QUOTES.append(rec)
    return rec


def int_in_quote(rec: dict, pattern: str) -> int | None:
    m = re.search(pattern, rec["quote"])
    return int(m.group(1)) if (m and rec["verified"]) else None


def float_in_quote(rec: dict, pattern: str) -> float | None:
    m = re.search(pattern, rec["quote"])
    return float(m.group(1)) if (m and rec["verified"]) else None


def parse_repo(relpath: str):
    """ast.parse a repo file without echoing its own SyntaxWarnings (invalid escapes in repo strings)."""
    lines_of(relpath)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse("\n".join(_LINES[relpath]))


def top_level_defs(relpath: str) -> dict:
    tree = parse_repo(relpath)
    return {n.name: n.lineno for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


def function_node(relpath: str, name: str):
    tree = parse_repo(relpath)
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name:
            return n
    return None


def hash_file(relpath: str) -> str:
    lines_of(relpath)
    return HASHES[relpath]


def r(x, nd=6):
    """Round a float for readability; keep None/bool/int untouched."""
    if x is None or isinstance(x, (bool, int)):
        return x
    return float(round(float(x), nd)) + 0.0


def git(*args) -> str:
    try:
        return subprocess.run(["git", "--no-optional-locks", "-C", str(ROOT), *args],
                              capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:                                          # noqa: BLE001
        return f"unavailable: {type(e).__name__}"


def pkg_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


LEDGER: dict = {}


def write_ledger(status: str) -> None:
    meta = LEDGER["_meta"]
    meta["status"] = status
    meta["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds") if status == "complete" else None
    meta["wall_time_s"] = r(time.time() - T0, 2)
    meta["source_hashes"] = [dict(path=k, sha256=v) for k, v in sorted(HASHES.items())]
    meta["quote_checks"] = dict(n_quotes=len(QUOTES), n_failed=sum(1 for q in QUOTES if not q["verified"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + ".partial")
    tmp.write_text(json.dumps(LEDGER, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(tmp, OUT)


def qpsk(rng, n):
    return (((rng.integers(0, 2, n) * 2 - 1) + 1j * (rng.integers(0, 2, n) * 2 - 1)) / np.sqrt(2))


def db10(x):
    return float(10.0 * np.log10(x))


# --------------------------------------------------------------------------- #
#  Shared synthetic CPI (findings 1 and 2)
# --------------------------------------------------------------------------- #
def synthetic_cpi():
    c = CONFIG["f1f2"]
    rng = np.random.default_rng(SEEDS["f1f2_reference_qpsk"])
    Lf, M, fs = c["Lf"], c["M"], c["fs_hz"]
    ref_frame = qpsk(rng, Lf).astype(np.complex64)
    ref_cpi = np.tile(ref_frame, M)
    Ns = ref_cpi.size
    fd = c["doppler_bin"] * fs / (Lf * M)
    n = np.arange(Ns)
    y_echo = (c["echo_amplitude"] * np.roll(ref_cpi, c["delay_samples"])
              * np.exp(2j * np.pi * fd * n / fs)).astype(np.complex64)
    wf = types.SimpleNamespace(fs_hz=fs, std="nr")
    return ref_cpi, y_echo, wf


# --------------------------------------------------------------------------- #
#  f1 -- steering vector content in gpu_montecarlo
# --------------------------------------------------------------------------- #
def section_f1(ed, pre):
    from experiment_x410 import X410Scenario, steering_vector
    c1 = CONFIG["f1"]
    scn = X410Scenario(n_surv=c1["n_elements"], carrier_hz=ed.FC)
    sv_true = steering_vector(scn, c1["true_az_deg"], c1["el_deg"])
    sv_wrong = steering_vector(scn, c1["wrong_az_deg"], c1["el_deg"])
    N = c1["n_elements"]
    alt = np.array([(-1.0) ** k for k in range(N)], complex)
    variants = [
        ("steer_true_az", f"ideal ULA steering at the true azimuth {c1['true_az_deg']} deg", sv_true),
        ("steer_wrong_az", f"ideal ULA steering at a wrong azimuth {c1['wrong_az_deg']} deg", sv_wrong),
        ("all_zeros", "all-zero vector of length 4", np.zeros(N, complex)),
        ("alternating_sign", "vector [+1,-1,+1,-1]", alt),
    ]
    rows = []
    for name, desc, sv in variants:
        res = ed.gpu_montecarlo(pre, sv, c1["noise_sigma"], K=c1["K"], seed=SEEDS["f1_montecarlo_torch"],
                                pfa=c1["pfa"], batch=c1["batch"])
        rows.append(dict(name=name, steering=desc, pd=r(res["Pd"], 8), pfa_emp=r(res["Pfa_emp"], 10),
                         n_trials=int(res["K"])))
    all_identical = len({(x["pd"], x["pfa_emp"]) for x in rows}) == 1

    # A physical 4-element coherent combiner steered at the wrong azimuth, relative to ideal steering:
    # |w^H a|^2 / (|w|^2 |a|^2) with w = wrong steering, a = true array response.
    g_rel = abs(np.vdot(sv_wrong, sv_true)) ** 2 / (np.vdot(sv_wrong, sv_wrong).real * np.vdot(sv_true, sv_true).real)
    combiner = dict(n_elements=N, element_spacing="lambda/2 ULA (experiment_x410.X410Scenario)",
                    true_az_deg=c1["true_az_deg"], steer_az_deg=c1["wrong_az_deg"], el_deg=c1["el_deg"],
                    carrier_hz=float(ed.FC), loss_db=r(db10(g_rel), 4))

    # AST: where is the name `sv` used inside gpu_montecarlo?
    node = function_node("src/experiment_detection.py", "gpu_montecarlo")
    parents = {}
    for p in ast.walk(node):
        for ch in ast.iter_child_nodes(p):
            parents[ch] = p
    sv_uses = []
    for m in ast.walk(node):
        if isinstance(m, ast.Name) and m.id == "sv":
            par = parents.get(m)
            in_len = isinstance(par, ast.Call) and isinstance(par.func, ast.Name) and par.func.id == "len"
            sv_uses.append(dict(line=m.lineno, inside_len_call=bool(in_len)))
    arg_names = [a.arg for a in node.args.args]
    sv_body_uses = sv_uses                     # the function argument itself is an ast.arg, not ast.Name

    # snr50 gains from the published report12 ledger
    led_rel = "outputs/detection_rx_sweep.json"
    led = json.loads((ROOT / led_rel).read_text(encoding="utf-8"))
    hash_file(led_rel)
    ideal = db10(4.0)
    snr_rows = []
    for mode in led["meta"]["modes"]:
        cur = led["modes"][mode]["curves"]
        g = float(cur["1"]["snr50"]) - float(cur["4"]["snr50"])
        snr_rows.append(dict(mode=mode, snr50_n1_minus_n4_db=r(g, 4), minus_ideal_gain_db=r(g - ideal, 4),
                             exceeds_ideal_gain=bool(g > ideal)))
    return dict(
        variants=rows, all_identical=bool(all_identical), n_trials=int(c1["K"]),
        noise_sigma=c1["noise_sigma"], pfa_nominal=c1["pfa"], monte_carlo_seed=SEEDS["f1_montecarlo_torch"],
        synthetic_cpi=dict(CONFIG["f1f2"], reference_seed=SEEDS["f1f2_reference_qpsk"]),
        physical_combiner_loss_db=combiner["loss_db"],
        physical_combiner_config=combiner,
        sv_name_uses_in_gpu_montecarlo=sv_body_uses,
        sv_used_only_via_len=bool(sv_body_uses) and all(u["inside_len_call"] for u in sv_body_uses),
        gpu_montecarlo_arguments=arg_names,
        code_quotes=dict(
            only_len_sv=quote("src/experiment_detection.py", 269, "N = len(sv); sqrtN = float(np.sqrt(N))"),
            sqrt_n_line=quote("src/experiment_detection.py", 284,
                              "surv = sqrtN * echo[None, :] + dpi[None, :] + _noise(b)"),
            hit_test_near_truth=quote("src/experiment_detection.py", 288,
                                      "hit = found & (torch.abs(di - pre.di_true) <= tol_d)"),
        ),
        snr50_ledger=led_rel,
        ideal_gain_db=r(ideal, 6),
        snr50_gain_rows=snr_rows,
        n_modes_exceeding_ideal_gain=int(sum(x["exceeds_ideal_gain"] for x in snr_rows)),
    )


# --------------------------------------------------------------------------- #
#  f2 -- range axis anchored to meta['Rb']; Sionna kernel l_min offset
# --------------------------------------------------------------------------- #
def section_f2(ed, ref_cpi, y_echo, wf):
    import sionna_chain as sc
    from sionna.phy.channel import time_lag_discrete_time_channel
    from scipy.signal import fftconvolve
    c = CONFIG["f1f2"]; c2 = CONFIG["f2"]
    mds = inspect.signature(sc.channel_taps).parameters["max_delay_spread"].default
    lmin_rows = []
    for fs in c2["fs_list_hz"]:
        lmin, lmax = time_lag_discrete_time_channel(fs, mds)
        lmin_rows.append(dict(fs_hz=float(fs), l_min=int(lmin), l_max=int(lmax), max_delay_spread_s=float(mds)))
    lag_rows = []
    L, i0 = c2["impulse_length"], c2["impulse_index"]
    for fs in c2["fs_list_hz"]:
        for d in c2["kernel_delays_samples"]:
            h, lmin, _lmax = sc.channel_taps([1.0], [d / fs], bandwidth=fs, n_time=1)
            kernel = np.asarray(h.detach().cpu().numpy()).reshape(-1).astype(np.complex64)
            x = np.zeros(L, np.complex64); x[i0] = 1.0
            y = fftconvolve(x, kernel)[:L]             # same truncation as build_echo_sionna
            peak = int(np.argmax(np.abs(y)))
            lag_rows.append(dict(fs_hz=float(fs), delay_samples=int(d), output_peak_index=peak,
                                 extra_lag_samples=int(peak - i0 - d), minus_l_min=int(-lmin)))
    extra = sorted({x["extra_lag_samples"] for x in lag_rows})

    preA = ed.Precomputed(y_echo, ref_cpi, wf, c["M"], {"Rb": c["meta_rb_values_m"][0]})
    preB = ed.Precomputed(y_echo, ref_cpi, wf, c["M"], {"Rb": c["meta_rb_values_m"][1]})
    native_Rb, _, _ = ed.range_doppler(preA.resid_echo, ref_cpi, c["fs_hz"], c["M"], n_range=ed.N_RANGE)
    C0 = float(ed.C0)

    node = function_node("src/experiment_detection.py", "build_echo_sionna")
    lmin_lines = sorted({m.lineno for m in ast.walk(node) if isinstance(m, ast.Name) and m.id == "l_min"})
    return dict(
        l_min_rows=lmin_rows,
        channel_taps_default_max_delay_spread_s=float(mds),
        kernel_lag_rows=lag_rows,
        measured_extra_lag_samples=(extra[0] if len(extra) == 1 else None),
        measured_extra_lag_all_rows_equal=bool(len(extra) == 1),
        meta_rb_values_m=c["meta_rb_values_m"],
        rd_identical=bool(np.array_equal(preA.rd0, preB.rd0)),
        truth_cell_A=[int(preA.di_true), int(preA.ri_true)],
        truth_cell_B=[int(preB.di_true), int(preB.ri_true)],
        axis_at_truth_cell_A_m=r(preA.Rb[preA.ri_true], 4),
        axis_at_truth_cell_B_m=r(preB.Rb[preB.ri_true], 4),
        axis_shift_m_when_meta_rb_changes=r(float(np.max(np.abs(preB.Rb - preA.Rb))), 6),
        native_axis_at_truth_cell_m=r(native_Rb[preA.ri_true], 4),
        true_excess_path_m=r(c["delay_samples"] * C0 / c["fs_hz"], 4),
        l_min_name_lines_in_build_echo_sionna=lmin_lines,
        l_min_used_after_assignment=bool(len(lmin_lines) > 1),
        code_quotes=dict(
            axis_anchor=quote("src/experiment_detection.py", 222,
                              'self.Rb = (np.arange(self.n_range) - self.ri_true) * _dr + float(vel_meta["Rb"])'),
            l_min_returned=quote("src/experiment_detection.py", 155,
                                 "h, l_min, l_max = sc.channel_taps([1.0], [tau], bandwidth=fs, n_time=1)"),
            convolution_truncation=quote("src/experiment_detection.py", 157,
                                         "y_del = fftconvolve(ref_cpi, kernel)[:Ns]"),
            native_axis=quote("src/passive_process.py", 146, "Rb = np.arange(n_range) * C0 / fs"),
        ),
    )


# --------------------------------------------------------------------------- #
#  f3 -- standard ECA and low Doppler
# --------------------------------------------------------------------------- #
def _eca_rows(pp, Lf, M, n_taps, ridge, delay, bins, rng):
    ref = np.tile(qpsk(rng, Lf), M); N = ref.size; n = np.arange(N)
    can = pp.ECACanceller(ref, n_taps=n_taps, ridge_rel=ridge)
    out = []
    for nu in bins:
        s = np.roll(ref, delay) * np.exp(2j * np.pi * nu * n / N)
        res = can.cancel(s)
        meas = db10(np.sum(np.abs(res) ** 2) / np.sum(np.abs(s) ** 2))
        g = abs(np.mean(np.exp(2j * np.pi * nu * n / N))) ** 2
        rem = 1.0 - g
        ana = db10(rem) if rem > 1e-12 else None
        out.append(dict(doppler_bin=float(nu), retained_db_measured=r(meas, 4), retained_db_analytic=r(ana, 4)))
    return out


def section_f3(ed, pp):
    import freespace_detect as fsd
    from detection_gpu import peak_batch
    c3 = CONFIG["f3"]
    q_taps = quote("src/experiment_detection.py", 104, "N_TAPS = 40")
    q_ridge = quote("src/experiment_detection.py", 203, "ECACanceller(ref_cpi, n_taps=N_TAPS, ridge_rel=1e-4)")
    n_taps = int(ed.N_TAPS)
    ridge = float_in_quote(q_ridge, r"ridge_rel=([0-9.eE+-]+)\)")
    rng = np.random.default_rng(SEEDS["f3_reference_qpsk"])
    rows = _eca_rows(pp, c3["Lf"], c3["M"], n_taps, ridge, c3["delay_samples"], c3["doppler_bins"], rng)
    sens = []
    for sc_ in c3["sensitivity_configs"]:
        for row in _eca_rows(pp, sc_["Lf"], sc_["M"], sc_["n_taps"], sc_["ridge_rel"], sc_["delay_samples"],
                             c3["doppler_bins"], rng):
            sens.append(dict(config_id=sc_["config_id"], Lf=sc_["Lf"], M=sc_["M"], n_taps=sc_["n_taps"],
                             ridge_rel=sc_["ridge_rel"], **row))
    n_main = c3["Lf"] * c3["M"]
    bin0_edge_floor_db = db10(c3["delay_samples"] / n_main)
    diffs = [abs(x["retained_db_measured"] - x["retained_db_analytic"])
             for x in rows + sens if x["retained_db_analytic"] is not None and x["doppler_bin"] >= 0.1]

    # guard rows, from verified code quotes
    q_pb = quote("src/experiment_detection.py", 287, "peak_batch(rd, det, guard_zd=2)")
    q_fw = quote("src/freespace_detect.py", 91, "DOPPLER_GUARD_WIDTH = 3")
    guard_zd = int_in_quote(q_pb, r"guard_zd=(\d+)")
    width = int_in_quote(q_fw, r"DOPPLER_GUARD_WIDTH = (\d+)")
    M = c3["M"]; zd = M // 2
    # empirical: which Doppler rows does peak_batch refuse? one candidate cell per row
    blocked = []
    for row in range(M):
        rd = torch.zeros((1, M, 4), dtype=torch.float64); rd[0, row, 1] = 1.0
        det = rd > 0
        _, _, _, found = peak_batch(rd, det, guard_zd=guard_zd)
        if not bool(found[0]):
            blocked.append(row - zd)
    lo, hi, zd2 = fsd._submap_rows(M, None, width)
    fs_blocked = [int(k - zd2) for k in range(lo, hi)]

    # bin width and speed at the report12 LTE CPI, read from the published ledger
    led_rel = "outputs/detection_rx_sweep.json"
    led = json.loads((ROOT / led_rel).read_text(encoding="utf-8"))
    L1 = led["modes"]["L1"]
    t_cpi = float(L1["M"]) / float(L1["prf"])
    bin_w = 1.0 / t_cpi
    fc = float(led["meta"]["fc"])
    lam = float(ed.C0) / fc
    speed_rows = [dict(doppler_bins=float(b), radial_speed_mps_monostatic_equivalent=r(b * bin_w * lam / 2.0, 6))
                  for b in c3["speed_bins"]]
    frame_rows = []
    for mode in led["meta"]["modes"]:
        md = led["modes"][mode]
        frame_rows.append(dict(mode=mode, std=md["std"], Ns=int(md["Ns"]), M=int(md["M"]), b=int(md["b"]),
                               frame_samples=int(md["Ns"]) // (int(md["M"]) * int(md["b"]))))
    return dict(
        rows=rows,
        sizes=dict(Lf=c3["Lf"], M=c3["M"], taps=n_taps, ridge_rel=ridge, delay_samples=c3["delay_samples"],
                   reference="QPSK frame tiled M times", seed=SEEDS["f3_reference_qpsk"],
                   taps_source=q_taps, ridge_source=q_ridge),
        sensitivity_rows=sens,
        production_frame_rows=frame_rows,
        production_frame_note="frame_samples = Ns / (M * b) per mode of outputs/detection_rx_sweep.json.",
        max_abs_measured_minus_analytic_db_for_bins_ge_0p1=r(max(diffs), 4),
        bin0_circular_shift_edge_floor_db=r(bin0_edge_floor_db, 4),
        bin0_note=("At 0 bins the projection removes the echo except the first delay_samples samples, which "
                   "np.roll wraps from the CPI end and a causal delayed copy does not model; "
                   "bin0_circular_shift_edge_floor_db = 10log10(delay_samples / (Lf*M))."),
        guard_rows=dict(
            peak_batch_guard_zd=guard_zd,
            peak_batch_blocked_doppler_bin_offsets=blocked,
            freespace_detect_guard_width=width,
            freespace_detect_removed_doppler_bin_offsets=fs_blocked,
            code_quotes=dict(peak_batch_call=q_pb, freespace_width=q_fw),
            probe_map_doppler_rows=M,
        ),
        l1_ledger=led_rel,
        t_cpi_s=r(t_cpi, 6),
        t_cpi_matches_ledger_dfd=bool(abs(bin_w - float(L1["dfd"])) < 1e-9 * bin_w),
        bin_width_hz=r(bin_w, 6),
        carrier_hz=fc,
        wavelength_m=r(lam, 6),
        radial_speed_per_0p1_bin_mps=speed_rows[0]["radial_speed_mps_monostatic_equivalent"],
        radial_speed_rows=speed_rows,
        speed_convention="monostatic-equivalent: v = bins * bin_width_hz * wavelength / 2",
    )


# --------------------------------------------------------------------------- #
#  f4 -- float32 running sums in cfar_batch
# --------------------------------------------------------------------------- #
def section_f4(ed, pp):
    from detection_gpu import cfar_batch, rd_batch
    c4 = CONFIG["f4"]
    nd, nr = c4["map_doppler_rows"], c4["map_range_bins"]
    rng = np.random.default_rng(SEEDS["f4_background_map"])
    base = np.abs(rng.standard_normal((nd, nr)) + 1j * rng.standard_normal((nd, nr))) / np.sqrt(2)

    def run(place):
        di, dj = place["row"], place["col"]
        hw = c4["excluded_rows_half_width"]
        keep = np.array([abs(i - di) > hw for i in range(nd)])
        out = []
        for pdb in c4["strong_cell_db"]:
            rd = base.copy(); rd[di, dj] = 10 ** (pdb / 20)
            d64, _ = cfar_batch(torch.tensor(rd, dtype=torch.float64)[None], pfa=c4["pfa"])
            d32, t32 = cfar_batch(torch.tensor(rd, dtype=torch.float32)[None], pfa=c4["pfa"])
            d32in64, _ = cfar_batch(torch.tensor(rd, dtype=torch.float32).double()[None], pfa=c4["pfa"])
            dnp, _, _ = pp.ca_cfar_2d(rd, pfa=c4["pfa"])
            cnt = lambda d: int((d[0].numpy() if hasattr(d, "numpy") else d)[keep, :].sum())   # noqa: E731
            out.append(dict(strong_cell_db=int(pdb), strong_cell_row=int(di), strong_cell_col=int(dj),
                            false_cells_float32=cnt(d32), false_cells_float64=cnt(d64),
                            false_cells_float32_input_float64_sum=cnt(d32in64),
                            false_cells_numpy_ca_cfar_2d=cnt(dnp),
                            float32_threshold_cells_le_zero=int((t32[0].numpy() <= 0)[keep, :].sum())))
        return out

    rows = run(c4["strong_cell_zero_doppler"])
    rows_off = run(c4["strong_cell_off_ridge"])
    first32 = next((x["strong_cell_db"] for x in rows if x["false_cells_float32"] > 0), None)
    last_zero32 = (max((x["strong_cell_db"] for x in rows
                        if x["false_cells_float32"] == 0 and x["strong_cell_db"] < first32), default=None)
                   if first32 is not None else None)

    # report12 L1 at production settings (analytic echo in place of the Sionna kernel echo)
    from waveforms import lte_downlink
    led_rel = "outputs/detection_rx_sweep.json"
    led = json.loads((ROOT / led_rel).read_text(encoding="utf-8"))
    L1 = led["modes"][c4["l1_mode"]]
    wf = lte_downlink(occupancy=L1["occ"])
    cfg = ed.CPI_CFG[wf.std]
    scn = ed.X410Scenario(carrier_hz=ed.FC)
    vel = tuple(float(v) for v in led["meta"]["vel"])
    scale_lin = 10 ** (float(led["meta"]["sigma_dbsm"]) / 10)
    tau, fd, geo = ed.bistatic_tau_fd(scn, vel)
    amp = np.sqrt(scale_lin) * geo["L"] / (np.sqrt(4 * np.pi) * geo["R1"] * geo["R2"])
    meta = dict(tau=tau, fd=fd, amp=float(amp), M=cfg["M"], b=cfg["b"], fs=wf.fs_hz, **geo)
    y = ed.analytic_echo(wf, meta)
    ref_cpi = np.tile(wf.tx.astype(np.complex64), cfg["b"] * cfg["M"])
    pre = ed.Precomputed(y, ref_cpi, wf, cfg["M"], meta)
    snr_ref = ed.measure_single_snr(pre, 1.0)
    snr_max = float(max(L1["snr_grid"]))
    sig_min = 10 ** ((snr_ref - snr_max) / 20.0)
    pre.to_gpu()
    t = pre._t
    g = torch.Generator().manual_seed(SEEDS["f4_l1_noise_torch"])
    Ns = pre.Ns
    nz = ((torch.randn(1, Ns, generator=g) + 1j * torch.randn(1, Ns, generator=g))
          * (sig_min / np.sqrt(2))).to(torch.complex64)
    l1_rows = []
    rd_dtype = None
    pfa_prod = float(L1["pfa_nominal"])
    for N in c4["l1_n_rx"]:
        surv = float(np.sqrt(N)) * t["echo"][None] + t["dpi"][None] + nz
        rd = rd_batch(surv, t["ref"], pre.M, pre.n_range)
        rd_dtype = str(rd.dtype)
        P = (rd[0].double() ** 2).numpy()
        med = float(np.median(P))
        d32, _ = cfar_batch(rd, pfa=c4["pfa"])
        d64, _ = cfar_batch(rd.double(), pfa=c4["pfa"])
        d32p, _ = cfar_batch(rd, pfa=pfa_prod)
        d64p, _ = cfar_batch(rd.double(), pfa=pfa_prod)
        l1_rows.append(dict(n_rx=int(N), rd_dtype=str(rd.dtype),
                            mask_mismatches_at_production_pfa=int((d32p != d64p).sum().item()),
                            float32_detections_at_production_pfa=int(d32p.sum().item()),
                            float64_detections_at_production_pfa=int(d64p.sum().item()),
                            max_cell_over_median_db=r(db10(P.max() / med), 3),
                            zero_doppler_row_max_over_median_db=r(db10(P[pre.M // 2].max() / med), 3),
                            mask_mismatches=int((d32 != d64).sum().item()),
                            float32_detections=int(d32.sum().item()), float64_detections=int(d64.sum().item())))
    del pre, t, nz
    return dict(
        rows=rows,
        rows_strong_cell_off_ridge=rows_off,
        map_size=dict(doppler_rows=nd, range_bins=nr, background="unit-mean-power Rayleigh magnitude",
                      seed=SEEDS["f4_background_map"], pfa=c4["pfa"],
                      excluded_rows_half_width_around_strong_cell=c4["excluded_rows_half_width"]),
        first_strong_cell_db_with_float32_false_cells=first32,
        float32_false_cell_onset_band_db=dict(last_strong_cell_db_without=last_zero32, first_strong_cell_db_with=first32),
        float64_false_cells_all_zero=bool(all(x["false_cells_float64"] == 0 for x in rows + rows_off)),
        float32_input_float64_sum_false_cells_all_zero=bool(
            all(x["false_cells_float32_input_float64_sum"] == 0 for x in rows + rows_off)),
        counts_note=("Exact float32 false-cell counts depend on the summation order and library of the running "
                     "sums; cite the onset band and the float64 = 0 result, not the counts as characteristic values."),
        report12_l1_check=dict(
            mode=c4["l1_mode"], echo="analytic_echo (not the Sionna kernel echo)", M=int(cfg["M"]),
            n_samples=int(Ns), snr_grid_max_db=snr_max, snr_ref_db_at_sigma1=r(snr_ref, 4),
            noise_sigma_at_grid_max=r(sig_min, 10), noise_seed=SEEDS["f4_l1_noise_torch"],
            dpi_amplitude=float(ed.DPI_AMP), rb_from_geometry_m=r(geo["Rb"], 6),
            rb_matches_ledger=bool(abs(geo["Rb"] - float(L1["Rb_true"])) < 1e-6),
            rows=l1_rows,
            pfa_used=c4["pfa"],
            production_pfa_nominal=pfa_prod,
            production_pfa_nominal_key=f"{led_rel}:modes.{c4['l1_mode']}.pfa_nominal",
            max_cell_over_median_db=max(x["max_cell_over_median_db"] for x in l1_rows),
            mask_mismatches=int(sum(x["mask_mismatches"] for x in l1_rows)),
            mask_mismatches_at_production_pfa=int(sum(x["mask_mismatches_at_production_pfa"] for x in l1_rows)),
        ),
        dtype_probe=dict(
            rd_dtype=rd_dtype,
            torch_complex64_real_dtype=str(torch.zeros(1, dtype=torch.complex64).real.dtype),
            numpy_complex64_to_torch_dtype=str(torch.tensor(np.zeros(2, np.complex64)).dtype),
        ),
        code_quotes=dict(
            power_in_input_dtype=quote("src/detection_gpu.py", 51, "P = rd ** 2"),
            running_sum_dtype=quote("src/detection_gpu.py", 57,
                                    "S = torch.zeros((B, nd + 1, nr + 1), dtype=P.dtype, device=dev)"),
            running_sum=quote("src/detection_gpu.py", 58,
                              "S[:, 1:, 1:] = torch.cumsum(torch.cumsum(P, dim=1), dim=2)"),
            self_check_float64_input=quote("src/detection_gpu.py", 116,
                                           "rd_t = torch.tensor(rd_np, dtype=torch.float64, device=dev)[None]"),
            noise_dtype_complex64=quote("src/experiment_detection.py", 279, "* (sigma / np.sqrt(2))).to(torch.complex64)"),
        ),
        l1_ledger=led_rel,
    )


# --------------------------------------------------------------------------- #
#  f5 -- magnitude-only maps and single global peak
# --------------------------------------------------------------------------- #
def section_f5(pp):
    from scipy import ndimage
    from detection_gpu import cfar_batch, peak_batch, rd_batch
    c5 = CONFIG["f5"]
    rng = np.random.default_rng(SEEDS["f5_signals"])
    Lf, M, fs, nrg = c5["Lf"], c5["M"], c5["fs_hz"], c5["n_range"]
    ref = np.tile(qpsk(rng, Lf), M); N = ref.size; n = np.arange(N)
    dfd = fs / Lf / M
    surv = sum(tg["amplitude"] * np.roll(ref, tg["delay_samples"]) * np.exp(2j * np.pi * tg["doppler_bin"] * dfd * n / fs)
               for tg in c5["targets"])
    surv = surv + (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * np.sqrt(0.5) * c5["noise_sigma"]
    Rb, f_d, rd = pp.range_doppler(surv, ref, fs, M, n_range=nrg)
    det, _thr, _ = pp.ca_cfar_2d(rd, pfa=c5["pfa"])
    pk = pp.peak_detection(Rb, f_d, rd, det)
    target_cells = [[M // 2 + tg["doppler_bin"], tg["delay_samples"]] for tg in c5["targets"]]
    rdt = rd_batch(torch.tensor(surv[None]), torch.tensor(ref[:Lf]), M, nrg)
    dett, _ = cfar_batch(rdt, pfa=c5["pfa"])
    di, ri, _val, found = peak_batch(rdt, dett, guard_zd=c5["peak_batch_guard_zd"])
    _lab, ncomp = ndimage.label(det, structure=np.ones((3, 3), int))
    return dict(
        cfar_mask_cells=int(det.sum()),
        cfar_mask_cells_torch=int(dett.sum().item()),
        cfar_connected_components_8conn=int(ncomp),
        n_targets=len(c5["targets"]),
        target_cells=target_cells,
        target_cells_in_cfar_mask=[bool(det[a, b]) for a, b in target_cells],
        peaks_returned_by_peak_detection=(1 if isinstance(pk, dict) else 0),
        peak_detection_cell=([int(pk["di"]), int(pk["ri"])] if isinstance(pk, dict) else None),
        peaks_returned_by_peak_batch=int(found.sum().item()),
        peaks_returned_by_peak_batch_note=("peak_batch returns one masked argmax per trial; with one trial (B=1) "
                                           "this count is at most 1 by construction and shows the interface limit."),
        peak_batch_cell=[int(di[0]), int(ri[0])],
        rd_is_complex=bool(np.iscomplexobj(rd) or torch.is_complex(rdt)),
        rd_is_complex_numpy=bool(np.iscomplexobj(rd)),
        rd_is_complex_torch=bool(torch.is_complex(rdt)),
        sizes=dict(Lf=Lf, M=M, fs_hz=fs, n_range=nrg, pfa=c5["pfa"], seed=SEEDS["f5_signals"],
                   noise_sigma=c5["noise_sigma"], targets=c5["targets"]),
        code_quotes=dict(
            numpy_magnitude=quote("src/passive_process.py", 147, "return Rb, f_d, np.abs(RD)"),
            numpy_single_argmax=quote("src/passive_process.py", 205,
                                      "di, ri = np.unravel_index(np.argmax(masked), masked.shape)"),
            torch_magnitude=quote("src/detection_gpu.py", 44, "return RD.abs()"),
            torch_single_max=quote("src/detection_gpu.py", 98, "val, idx = flat.max(dim=1)"),
        ),
    )


# --------------------------------------------------------------------------- #
#  f14 -- first-frame reference reuse
# --------------------------------------------------------------------------- #
def _f14_probe(pp, seed, M, L, delay, dbin, nmax):
    rng = np.random.default_rng(seed)
    fs = 1000.0 * L
    nrg = min(nmax, L)
    ref = np.exp(0.5j * np.pi * rng.integers(0, 4, (M, L)))
    surv = np.roll(ref, delay, axis=1) * np.exp(2j * np.pi * dbin * np.arange(M) / M)[:, None]
    _, _, observed = pp.range_doppler(surv.ravel(), ref.ravel(), fs, M, n_range=nrg)
    rp = np.fft.ifft(np.fft.fft(surv, axis=1) * np.conj(np.fft.fft(ref, axis=1)), axis=1)[:, :nrg]
    expected = np.abs(np.fft.fftshift(np.fft.fft(rp * np.hanning(M)[:, None], axis=0), axes=0))
    ref_rep = np.tile(ref[0], (M, 1))
    surv_rep = np.roll(ref_rep, delay, axis=1) * np.exp(2j * np.pi * dbin * np.arange(M) / M)[:, None]
    _, _, obs_rep = pp.range_doppler(surv_rep.ravel(), ref_rep.ravel(), fs, M, n_range=nrg)
    cell = (M // 2 + dbin, delay)
    prod_arg = [int(v) for v in np.unravel_index(observed.argmax(), observed.shape)]
    corr_arg = [int(v) for v in np.unravel_index(expected.argmax(), expected.shape)]
    loss = 20 * np.log10(observed[cell] / expected[cell])
    ml = db10(M * L)
    return dict(config_id=f"seed{seed}_M{M}_L{L}", seed=int(seed), M=int(M), L=int(L), loss_db=r(loss, 4),
                ten_log10_ML_db=r(ml, 4), loss_plus_ten_log10_ML_db=r(loss + ml, 4),
                argmax_correct=bool(prod_arg == list(cell)), production_argmax=prod_arg,
                per_frame_reference_argmax=corr_arg, truth_cell=[int(cell[0]), int(cell[1])],
                repeated_frame_control_db=r(20 * np.log10(obs_rep[cell] / expected[cell]), 9),
                production_peak_to_median_db=r(20 * np.log10(observed.max() / np.median(observed)), 3))


def _scan_kernel_callers():
    """Files whose code calls range_doppler / rd_batch / make_cpi (AST call nodes), with tile evidence per file."""
    names = {"range_doppler", "rd_batch", "make_cpi"}
    tile_re = re.compile(r"np\.tile\(")
    rows = []
    for rel in _py_files():
        ls = lines_of(rel)
        try:
            tree = parse_repo(rel)
        except SyntaxError:
            continue
        calls, called = [], set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                if nm in names:
                    calls.append(n.lineno); called.add(nm)
        if not calls:
            continue
        ev = []
        if any(tile_re.search(s) for s in ls):
            ev.append("np.tile in file")
        if "make_cpi" in called:
            ev.append("calls make_cpi (tiles at src/passive_process.py:68)")
        uses_ed = any(isinstance(n, ast.Call) and (
            (isinstance(n.func, ast.Name) and n.func.id in ("Precomputed", "build_echo_sionna"))
            or (isinstance(n.func, ast.Attribute) and n.func.attr in ("Precomputed", "build_echo_sionna")))
            for n in ast.walk(tree))
        if uses_ed:
            ev.append("calls experiment_detection Precomputed/build_echo_sionna (tiles at src/experiment_detection.py:145)")
        calls = sorted(set(calls))
        rows.append(dict(path=rel, kernels_called=sorted(called), call_lines=calls[:8], n_call_lines=len(calls),
                         tile_evidence=ev, classified_as_tiled_by_scan=bool(ev)))
    return rows


def _extract_functions(relpath, names, namespace):
    """Compile only the named top-level functions of a repo file (no module-level imports run)."""
    tree = parse_repo(relpath)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    mod = ast.Module(body=nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(mod), relpath, "exec"), namespace)   # noqa: S102
    return {n.name for n in nodes}


def section_f14(pp):
    c = CONFIG["f14"]
    rows = [_f14_probe(pp, s, M, L, c["delay_samples"], c["doppler_bin"], c["n_range_max"]) for (s, M, L) in c["configs"]]
    tile_quotes = [
        quote("src/passive_process.py", 68, "ref_cpi = np.tile(ref_frame, M)"),
        quote("src/experiment_detection.py", 145, "ref_cpi = np.tile(block, b * M)"),
        quote("src/experiment_detection.py", 173, 'ref_cpi = np.tile(block, meta["b"] * meta["M"])'),
        quote("src/freespace_detect.py", 474, "ref_cpi = np.tile(ref_frame, M)"),
        quote("src/freespace_detect.py", 1054, "ref_cpi = np.tile(np.asarray(pre.ref_frame), M)"),
        quote("src/experiment_freespace_range.py", 206, 'np.tile(np.asarray(pre.ref_frame), ref["M"])'),
        quote("src/experiment_freespace_range.py", 729, 'ref_cpi = np.tile(np.asarray(ref["wf"].tx, np.complex64), Mf)'),
        quote("src/make_r6_frames.py", 46, "ref_cpi = np.tile(ref_frame, M)"),
    ]
    first_frame_quotes = dict(
        numpy_first_frame=quote("src/passive_process.py", 139, "Rf = np.conj(np.fft.fft(ref[:Lf]))"),
        torch_single_frame=quote("src/detection_gpu.py", 39, "Rf = torch.conj(torch.fft.fft(ref_frame))"),
    )
    callers = _scan_kernel_callers()
    unclassified = [x["path"] for x in callers if not x["classified_as_tiled_by_scan"]]

    # The one non-tiled reference found: benchmark/verify_pyapril.py builds a non-repeating QPSK reference.
    pyap_rel = "benchmark/verify_pyapril.py"
    q_pyap = quote(pyap_rel, 52, "ref = np.exp(1j * rng.integers(0, 4, Ns) * (np.pi / 2)).astype(np.complex64)")
    q_pyap_rd = quote(pyap_rel, 71, 'Rb, fd, rd = range_doppler(resid, can.ref, sc["fs"], sc["M"], n_range=r_max)')
    main_node = function_node(pyap_rel, "main")
    ours_called_in_main = any(isinstance(m, ast.Call) and isinstance(m.func, ast.Name) and m.func.id == "ours"
                              for m in ast.walk(main_node)) if main_node is not None else None
    ns = {"np": np, "os": os}
    got = _extract_functions(pyap_rel, {"build_scenario", "ours"}, ns)
    sc_ = ns["build_scenario"](std=c["pyapril_scenario_std"])
    o = ns["ours"](sc_, c["pyapril_r_max"], c["pyapril_fd_max_hz"], None)
    # Control: the same scenario lines with the reference frame repeated M times (local copy of
    # build_scenario lines 49-60; the 'independent' copy must reproduce build_scenario exactly).
    q_bs = [quote(pyap_rel, 50, "Ns = n_blocks * Lf"),
            quote(pyap_rel, 51, 'rng = np.random.default_rng({"nr": 1, "wifi": 2, "lte": 3}.get(std, 0) + seed)'),
            quote(pyap_rel, 55, "dpi = 10 ** (dpi_db / 20.0) * ref"),
            quote(pyap_rel, 57, "echo = a * np.roll(ref, r_bin_true) * np.exp(1j * 2 * np.pi * fd_true_hz * n / fs)"),
            quote(pyap_rel, 58, "npow = (np.abs(echo) ** 2).mean() / (10 ** (snr_db / 10.0))"),
            quote(pyap_rel, 59, "noise = np.sqrt(npow / 2) * (rng.standard_normal(Ns) + 1j * rng.standard_normal(Ns))")]
    defaults = {k: v.default for k, v in inspect.signature(ns["build_scenario"]).parameters.items()}

    def _local_scenario(tiled: bool):
        fs = sc_["fs"]; Lf = defaults["Lf"]; M = defaults["n_blocks"]; Ns = M * Lf
        rng = np.random.default_rng({"nr": 1, "wifi": 2, "lte": 3}.get(c["pyapril_scenario_std"], 0) + defaults["seed"])
        ref = np.exp(1j * rng.integers(0, 4, Ns) * (np.pi / 2)).astype(np.complex64)
        if tiled:
            ref = np.tile(ref[:Lf], M)
        n = np.arange(Ns)
        fd_true_hz = defaults["dopp_bin_true"] * (fs / Lf / M)
        dpi = 10 ** (defaults["dpi_db"] / 20.0) * ref
        a = 10 ** (defaults["tgt_db"] / 20.0)
        echo = a * np.roll(ref, defaults["r_bin_true"]) * np.exp(1j * 2 * np.pi * fd_true_hz * n / fs)
        npow = (np.abs(echo) ** 2).mean() / (10 ** (defaults["snr_db"] / 10.0))
        noise = np.sqrt(npow / 2) * (rng.standard_normal(Ns) + 1j * rng.standard_normal(Ns))
        return dict(sc_, ref=ref, surv=(dpi + echo + noise).astype(np.complex64))

    loc_ind = _local_scenario(False)
    copy_matches = bool(np.array_equal(loc_ind["ref"], sc_["ref"]) and np.array_equal(loc_ind["surv"], sc_["surv"]))
    o_t = ns["ours"](_local_scenario(True), c["pyapril_r_max"], c["pyapril_fd_max_hz"], None)
    pyap_control = dict(local_copy_reproduces_build_scenario=copy_matches, source_quotes=q_bs,
                        peak_cell=[int(o_t["peak_di"]), int(o_t["peak_ri"])],
                        peak_at_truth=bool(o_t["peak_di"] == o_t["zd"] + sc_["dopp_bin_true"]
                                           and o_t["peak_ri"] == sc_["r_bin_true"]),
                        n_cfar_cells=int(o_t["n_fired"]))
    pyap = dict(path=pyap_rel, functions_extracted=sorted(got), repeated_frame_control=pyap_control, reference_quote=q_pyap, range_doppler_quote=q_pyap_rd,
                ours_called_by_main=ours_called_in_main,
                ours_rerun=dict(scenario_std_label=c["pyapril_scenario_std"], M=int(sc_["M"]), Lf=int(sc_["Lf"]),
                                truth_cell=[int(o["zd"] + sc_["dopp_bin_true"]), int(sc_["r_bin_true"])],
                                peak_cell=[int(o["peak_di"]), int(o["peak_ri"])],
                                peak_at_truth=bool(o["peak_di"] == o["zd"] + sc_["dopp_bin_true"]
                                                   and o["peak_ri"] == sc_["r_bin_true"]),
                                n_cfar_cells=int(o["n_fired"])),
                verify_pyapril_ledger_stores_ours=None)
    pj = ROOT / "outputs/verify_pyapril.json"
    if pj.exists():
        hash_file("outputs/verify_pyapril.json")
        d = json.loads(pj.read_text(encoding="utf-8"))
        pyap["verify_pyapril_ledger_stores_ours"] = any("ours" in m for m in d.get("modes", {}).values())
    return dict(
        rows=rows,
        probe=dict(delay_samples=c["delay_samples"], doppler_bin=c["doppler_bin"], n_range_max=c["n_range_max"],
                   fs_rule="fs = 1000 * L (only labels the axis)", reference="independent random QPSK per frame"),
        n_rows_argmax_correct=int(sum(x["argmax_correct"] for x in rows)),
        loss_db_min=min(x["loss_db"] for x in rows), loss_db_max=max(x["loss_db"] for x in rows),
        max_abs_repeated_frame_control_db=max(abs(x["repeated_frame_control_db"]) for x in rows),
        first_frame_quotes=first_frame_quotes,
        tile_quotes=tile_quotes,
        kernel_caller_scan=callers,
        kernel_callers_not_classified_as_tiled=unclassified,
        non_tiled_reference_case=pyap,
        note=("Every CPI builder quoted in tile_quotes repeats one reference frame M times, which is the "
              "repeated-frame control of the rows (0 dB). The AST scan of range_doppler/rd_batch/make_cpi callers "
              "finds tile evidence in every calling file except those listed in "
              "kernel_callers_not_classified_as_tiled. The exception, benchmark/verify_pyapril.py, builds a "
              "non-repeating QPSK reference; its ours() chain is not called by main() and its ledger does not "
              "store that chain's result, so no published output depends on it. Rerunning ours() on that "
              "scenario and on the same scenario with a repeated frame is in non_tiled_reference_case. "
              "The scan looks for tile evidence per file, not for data flow."),
    )


# --------------------------------------------------------------------------- #
#  tracking inventory
# --------------------------------------------------------------------------- #
_PY_CACHE: list = []


def _py_files() -> list:
    if not _PY_CACHE:
        ci = CONFIG["inventory"]
        for root in ci["roots"]:
            for p in sorted((ROOT / root).rglob(ci["file_glob"])):
                if "__pycache__" in p.parts or any(part.startswith(".") for part in p.relative_to(ROOT).parts):
                    continue
                if fnmatch.fnmatch(p.name, ci["exclude_glob"]):
                    continue
                _PY_CACHE.append(_rel(p))
    return _PY_CACHE


# Each row: comma-free component_id (selector key), label, a wide grep pattern (spec terms plus
# spelling variants and near terms), a spec-terms-only grep pattern, and the library call / import names
# whose presence in code would indicate an implementation rather than a mention.
TRACKING_PATTERNS = [
    dict(component_id="kalman_ekf_ukf", component="kalman / ekf / ukf",
         grep_pattern=r"kalman|(?<![a-z])(ekf|ukf)(?![a-z])",
         spec_grep_pattern=r"kalman|(?<![a-z])(ekf|ukf)(?![a-z])",
         library_call_names=["KalmanFilter", "ExtendedKalmanFilter", "UnscentedKalmanFilter"],
         library_modules=["filterpy", "pykalman", "stonesoup"]),
    dict(component_id="data_association",
         component="data association (linear_sum_assignment, hungarian, jpda, gnn)",
         grep_pattern=r"linear_sum_assignment|hungarian|(?<![a-z])(jpda|gnn)(?![a-z])",
         spec_grep_pattern=r"linear_sum_assignment|hungarian|(?<![a-z])(jpda|gnn)(?![a-z])",
         library_call_names=["linear_sum_assignment", "Munkres"],
         library_modules=["munkres", "lap", "stonesoup"]),
    dict(component_id="gating", component="gating (mahalanobis, chi2 gate)",
         grep_pattern=r"mahalanobis|chi2[ _-]?gat|chi-?square[ _-]?gat|(?<![a-z])gating(?![a-z])",
         spec_grep_pattern=r"mahalanobis|chi-?2[ _-]?gat",
         library_call_names=["mahalanobis"],
         library_modules=["stonesoup"]),
    dict(component_id="cfar_cell_clustering",
         component="clustering of CFAR cells (dbscan, connected components, nms)",
         grep_pattern=r"dbscan|connected[ _-]?components?|(?<![a-z])nms(?![a-z])"
                      r"|non[ _-]?max(imum)?[ _-]?suppression|ndimage\.label",
         spec_grep_pattern=r"dbscan|connected[ _-]?components?|(?<![a-z])nms(?![a-z])",
         library_call_names=["DBSCAN", "dbscan", "connected_components", "ndimage.label", "nms",
                             "non_max_suppression"],
         library_modules=[]),
    dict(component_id="track_management", component="track management (tentative/confirmed track, m-of-n)",
         grep_pattern=r"tentative|confirmed[ _-]?track|(?<![a-z0-9])m[ _-]of[ _-]n(?![a-z])"
                      r"|(?<![0-9])[0-9]+[ _-]of[ _-][0-9]+[ _-]track"
                      r"|track[ _-]?(management|initiation|confirmation|deletion)",
         spec_grep_pattern=r"tentative|confirmed[ _-]?track|(?<![a-z0-9])m[ _-]of[ _-]n(?![a-z])",
         library_call_names=[],
         library_modules=["stonesoup"]),
    dict(component_id="angle_estimation", component="angle estimation (music, bartlett, capon, esprit, doa)",
         grep_pattern=r"(?<![a-z])(music|bartlett|capon|esprit|doa|aoa)(?![a-z])",
         spec_grep_pattern=r"(?<![a-z])(music|bartlett|capon|esprit|doa)(?![a-z])",
         library_call_names=[],
         library_modules=["doatools", "spectrum"]),
    dict(component_id="tracking_metrics", component="tracking metrics (gospa, ospa, id switch)",
         grep_pattern=r"(?<![a-z])(gospa|ospa|mota|motp)(?![a-z])|id[ _-]?switch",
         spec_grep_pattern=r"(?<![a-z])(gospa|ospa)(?![a-z])|id[ _-]?switch",
         library_call_names=["gospa", "ospa", "GOSPA", "OSPA", "GOSPAMetric", "OSPAMetric"],
         library_modules=["motmetrics", "stonesoup"]),
]
_CFAR_CALL_RE = re.compile(r"cfar", re.I)


def _call_name(node):
    """(base, name) of a Call node's function: foo() -> (None, 'foo'), mod.foo() -> ('mod', 'foo')."""
    f = node.func
    if isinstance(f, ast.Name):
        return None, f.id
    if isinstance(f, ast.Attribute):
        return (f.value.id if isinstance(f.value, ast.Name) else None), f.attr
    return None, None


def _scopes(tree):
    """[(scope_name, first_line, nodes directly in that function scope)]; the module is one scope."""
    out = []

    def visit(node, acc):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inner = []
                out.append((ch.name, ch.lineno, inner))
                visit(ch, inner)
            else:
                acc.append(ch)
                visit(ch, acc)

    top = []
    out.append(("<module>", 1, top))
    visit(tree, top)
    return out


def _library_hit(node, spec):
    names = set(spec["library_call_names"])
    mods = {m.split(".")[0] for m in spec["library_modules"]}
    if isinstance(node, ast.Call):
        base, nm = _call_name(node)
        return bool(nm is not None and (nm in names or (base is not None and f"{base}.{nm}" in names)))
    if isinstance(node, ast.Import):
        return any(a.name.split(".")[0] in mods or a.name.split(".")[-1] in names for a in node.names)
    if isinstance(node, ast.ImportFrom):
        return bool((node.module or "").split(".")[0] in mods or any(a.name in names for a in node.names))
    return False


def section_inventory():
    files = _py_files()
    cfar_re = re.compile(r"cfar", re.I)
    mx = CONFIG["inventory"]["max_examples"]
    rows = []
    for spec in TRACKING_PATTERNS:
        rx = re.compile(spec["grep_pattern"], re.I)
        rx_spec = re.compile(spec["spec_grep_pattern"], re.I)
        hits, files_hit, cfar_hits, defs, spec_hits, spec_defs = [], set(), 0, [], [], []
        lib_hits, lib_in_cfar_scope, lib_in_cfar_file, spec_defs_in_cfar_file = [], [], [], []
        for rel in files:
            ls = lines_of(rel)
            file_mentions_cfar = any(cfar_re.search(x) for x in ls)
            for i, line in enumerate(ls):
                if rx.search(line):
                    hits.append(f"{rel}:{i + 1}")
                    files_hit.add(rel)
                    cfar_hits += int(file_mentions_cfar)
                if rx_spec.search(line):
                    spec_hits.append(f"{rel}:{i + 1}")
            try:
                tree = parse_repo(rel)
            except SyntaxError:
                continue
            scopes = _scopes(tree)
            file_calls_cfar = any(isinstance(n, ast.Call) and _CFAR_CALL_RE.search(_call_name(n)[1] or "")
                                  for _nm, _l, nodes in scopes for n in nodes)
            for nd_ in ast.walk(tree):
                if isinstance(nd_, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if rx.search(nd_.name):
                        defs.append(f"{rel}:{nd_.lineno}:{nd_.name}")
                    if rx_spec.search(nd_.name):
                        spec_defs.append(f"{rel}:{nd_.lineno}:{nd_.name}")
                        if file_calls_cfar:
                            spec_defs_in_cfar_file.append(f"{rel}:{nd_.lineno}:{nd_.name}")
            for sname, _sl, nodes in scopes:
                scope_calls_cfar = any(isinstance(n, ast.Call) and _CFAR_CALL_RE.search(_call_name(n)[1] or "")
                                       for n in nodes)
                for n in nodes:
                    if _library_hit(n, spec):
                        tag = f"{rel}:{n.lineno}:{sname}"
                        lib_hits.append(tag)
                        if scope_calls_cfar:
                            lib_in_cfar_scope.append(tag)
                        if file_calls_cfar:
                            lib_in_cfar_file.append(tag)
        lib_hits.sort(); lib_in_cfar_scope.sort(); lib_in_cfar_file.sort()
        rows.append(dict(
            component_id=spec["component_id"], component=spec["component"],
            grep_pattern=spec["grep_pattern"], pattern_flags="case-insensitive",
            hits_in_src_benchmark=len(hits), files_with_hits=len(files_hit),
            hits_in_files_mentioning_cfar=cfar_hits,
            example_hits=hits[:mx],
            named_definitions_matching=len(defs),
            example_named_definitions=defs[:mx],
            spec_grep_pattern=spec["spec_grep_pattern"],
            hits_spec_terms_only=len(spec_hits),
            example_hits_spec_terms_only=spec_hits[:mx],
            implementation_defs=len(spec_defs),
            example_implementation_defs=spec_defs[:mx],
            library_call_names=spec["library_call_names"], library_modules=spec["library_modules"],
            library_calls_or_imports=len(lib_hits),
            example_library_calls_or_imports=lib_hits[:mx],
            library_calls_or_imports_in_files_calling_cfar=len(lib_in_cfar_file),
            library_calls_or_imports_in_functions_calling_cfar=len(lib_in_cfar_scope),
            example_library_calls_or_imports_in_functions_calling_cfar=lib_in_cfar_scope[:mx],
            implementation_defs_in_files_calling_cfar=len(spec_defs_in_cfar_file),
            implementation_defs_or_library_calls_in_files_calling_cfar=len(spec_defs_in_cfar_file)
            + len(lib_in_cfar_file),
        ))
    return rows, len(files)


REUSABLE = [
    ("src/passive_process.py", "ECACanceller",
     "Standard whole-CPI ECA: least-squares removal of delayed zero-Doppler copies of the reference; "
     "reference autocorrelation factorised once.",
     "yes, per CPI; removes low-Doppler targets (f3_eca)"),
    ("src/passive_process.py", "range_doppler",
     "Frame matched filter plus slow-time Hann FFT; returns the magnitude map and uses only the first reference frame.",
     "needs changes: complex output (f5) and a per-frame reference (f14)"),
    ("src/passive_process.py", "ca_cfar_2d", "float64 2-D CA-CFAR with a summed-area table.", "yes"),
    ("src/passive_process.py", "_subbin", "Parabolic sub-bin offset from the peak cell and its two neighbours.",
     "yes, per detection cluster"),
    ("src/passive_process.py", "peak_detection", "One masked global argmax with sub-bin refinement.",
     "not as is: one peak per map (f5)"),
    ("src/passive_process.py", "doppler_guard_mask", "Zero-Doppler guard applied to a detection mask.", "yes"),
    ("src/passive_process.py", "make_cpi", "Synthetic CPI builder that tiles one reference frame M times.",
     "test signals only; no moving target across CPIs"),
    ("src/detection_gpu.py", "rd_batch", "Batched magnitude range-Doppler map from one reference frame.",
     "needs changes: complex output and a per-frame reference"),
    ("src/detection_gpu.py", "cfar_batch", "Batched CA-CFAR; running sums in the input dtype.",
     "after float64 running sums (f4_cfar)"),
    ("src/detection_gpu.py", "peak_batch", "One masked argmax per trial after a zero-Doppler guard.",
     "not as is: one peak per trial (f5)"),
    ("src/freespace_detect.py", "_cfar_excl_rows",
     "CA-CFAR on a sub-map with the zero-Doppler guard rows removed from detection and training.", "yes"),
    ("src/freespace_detect.py", "_cfar_excl_rows_batch", "Batched version of _cfar_excl_rows (uses cfar_batch).",
     "yes, after the cfar_batch dtype fix"),
    ("src/freespace_detect.py", "detect_target_neighborhood",
     "Threshold crossing within +-tol cells of a given truth cell.", "evaluation only (needs truth)"),
    ("src/freespace_detect.py", "calibrate_pfa",
     "Empirical false-alarm rate on target-free trials; iterates the nominal Pfa.", "yes, truth-free threshold calibration"),
    ("src/freespace_detect.py", "false_alarms_per_cpi", "Expected false alarms per CPI from map shape and Pfa.",
     "yes, for false-track budgeting"),
    ("src/experiment_x410.py", "adc_quantize", "Uniform I/Q ADC quantisation.", "yes, front-end model"),
    ("src/experiment_x410.py", "X410Scenario", "Legacy small bistatic layout with half-wavelength ULA element positions.",
     "geometry template only; not an outdoor layout"),
    ("src/experiment_x410.py", "steering_vector", "Ideal plane-wave ULA steering vector (no calibration or pattern).",
     "starting point for an angle scan"),
    ("src/sionna_chain.py", "channel_taps", "Sionna discrete-time sinc taps; also returns l_min.",
     "yes, if the -l_min offset is applied (f2_range_axis)"),
    ("src/experiment_detection.py", "bistatic_tau_fd", "Bistatic delay and Doppler of a point target.",
     "yes, measurement function for (Rb, fd)"),
    ("benchmark/verify_observability.py", "bistatic_Rb", "Analytic bistatic range.", "yes, measurement model"),
    ("benchmark/verify_observability.py", "bistatic_fd", "Analytic bistatic Doppler.", "yes, measurement model"),
    ("benchmark/verify_observability.py", "grad_Rb", "Gradient of bistatic range with respect to position.",
     "yes, EKF Jacobian"),
    ("benchmark/verify_observability.py", "grad_fd_p", "Gradient of bistatic Doppler with respect to position.",
     "yes, EKF Jacobian"),
    ("benchmark/verify_observability.py", "grad_fd_v", "Gradient of bistatic Doppler with respect to velocity.",
     "yes, EKF Jacobian"),
    ("benchmark/verify_observability.py", "_rows_pair", "Whitened Jacobian rows of (Rb, fd) for state [p0, v].",
     "yes, EKF Jacobian"),
    ("benchmark/verify_observability.py", "gramian",
     "Constant-velocity observability Gramian with optional azimuth/elevation rows (angle sigma is an input).",
     "yes, design-time observability check"),
    ("benchmark/scenarios.py", "hover", "Truth trajectory: fixed position, zero velocity.", "yes, as truth"),
    ("benchmark/scenarios.py", "radial", "Truth trajectory along the bistatic bisector.", "yes, as truth"),
    ("benchmark/scenarios.py", "tangential", "Truth trajectory across the bisector.", "yes, as truth"),
    ("benchmark/scenarios.py", "waypoint", "Truth trajectory on a bent Bezier path at constant speed.", "yes, as truth"),
    ("benchmark/verify_ghost_impact.py", "d_tracker", "Analytic binomial M-of-N track-start probabilities.",
     "reference formula only; no association"),
    ("src/report14_stap.py", "stap_weights", "MVDR space-time weights for a given covariance.",
     "adjacent asset, not a tracker"),
    ("src/report14_stap.py", "estimate_covariance", "Sample covariance with diagonal loading or rank truncation.",
     "adjacent asset, not a tracker"),
    ("src/microdoppler_proc.py", "clutter_suppress", "IIR MTI notch on an already-selected target signal.",
     "adjacent asset for slow-target studies; no range bin"),
]


#: Code quotes that back a detail of a REUSABLE description (line, text), checked at run time.
REUSABLE_QUOTES = {
    ("src/passive_process.py", "_subbin"): (192, "den = vm1 - 2.0 * v0 + vp1"),
    ("src/experiment_x410.py", "X410Scenario"): (127, "d = lam / 2.0"),
    ("benchmark/verify_ghost_impact.py", "d_tracker"): (227, 'out = {"init_logic": "3-of-5", "per_wf": {}}'),
}


def section_reusable():
    rows = []
    for path, fn, what, reuse in REUSABLE:
        defs = top_level_defs(path)
        ln = defs.get(fn)
        q = REUSABLE_QUOTES.get((path, fn))
        rows.append(dict(path=path, function=fn, def_line=ln,
                         def_line_verified=bool(ln is not None and re.match(rf"\s*(def|class) {re.escape(fn)}\b",
                                                                              lines_of(path)[ln - 1])),
                         what=what, reusable_for_tracking=reuse,
                         what_quote=(quote(path, q[0], q[1]) if q else None)))
    return rows


# --------------------------------------------------------------------------- #
def main() -> int:
    c0_ok = None
    LEDGER["_meta"] = dict(
        generator=f"benchmark/{NAME}.py",
        command=f'CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/{NAME}.py',
        argv=sys.argv[1:],
        started_utc=STARTED, finished_utc=None, status="started",
        git_head=git("rev-parse", "HEAD"),
        packages=dict(python=sys.version.split()[0], numpy=pkg_version("numpy"), scipy=pkg_version("scipy"),
                      torch=pkg_version("torch"), sionna=pkg_version("sionna")),
        cpu=dict(core=CORE, affinity_after=sorted(os.sched_getaffinity(0)), torch_threads=torch.get_num_threads(),
                 cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"), cuda_available=torch.cuda.is_available()),
        scope=("Simulation / code / bookkeeping checks of the current detection code and a text inventory of "
               "tracking components. Synthetic signals only; no comparison against RF measurements."),
        seeds=SEEDS, config=CONFIG,
        definitions=dict(
            pd="gpu_montecarlo hit rate: CFAR-masked global maximum within +-2 cells of the noiseless truth cell.",
            pfa_emp="gpu_montecarlo target-free false detections divided by cells outside the zero-Doppler +-2 rows.",
            physical_combiner_loss_db="10log10(|w^H a|^2/(|w|^2|a|^2)), w = ULA steering at the wrong azimuth, "
                                      "a = ULA response at the true azimuth; relative to ideal steering.",
            snr50_n1_minus_n4_db="curves['1'].snr50 - curves['4'].snr50 per mode in outputs/detection_rx_sweep.json.",
            ideal_gain_db="10log10(4), coherent gain of 4 elements with independent noise.",
            extra_lag_samples="argmax|fftconvolve(impulse, channel_taps kernel)[:L]| - impulse index - requested delay.",
            axis_shift_m_when_meta_rb_changes="max |Rb_axis(meta Rb B) - Rb_axis(meta Rb A)| for the same IQ.",
            retained_db_measured="10log10(sum|ECA(s)|^2 / sum|s|^2) for a noiseless delayed echo with nu Doppler bins.",
            retained_db_analytic="10log10(1 - |mean_n exp(j2pi nu n/N)|^2); null when the argument is 0 (nu = 0).",
            doppler_bin="cycles of Doppler phase over the whole CPI (= Doppler FFT bins).",
            false_cells="CFAR detections in rows farther than 2 rows from the strong cell's row.",
            float32_input_float64_sum="cfar_batch on the float32 map cast to float64 before squaring and summing.",
            max_cell_over_median_db="10log10(max cell power / median cell power) of the float32 L1 map.",
            mask_mismatches="number of cells where float32 and float64 cfar_batch masks differ (summed over n_rx rows).",
            f14_loss_db="20log10(|production map at truth cell| / |per-frame-reference map at truth cell|).",
            repeated_frame_control_db="Same ratio when all frames repeat frame 0 (the case every tiled builder is in).",
            hits_in_src_benchmark="number of matching lines in *.py under src/ and benchmark/ excluding *isac*0915*.",
            hits_in_files_mentioning_cfar="subset of those hits in files that contain 'cfar' anywhere.",
            cfar_connected_components_8conn="scipy.ndimage.label of the CFAR mask with a 3x3 structuring element.",
            loss_plus_ten_log10_ML_db="f14 loss_db + 10log10(M*L); near 0 when the loss equals the full coherent gain.",
            production_peak_to_median_db="20log10(max / median) of the production magnitude map in the f14 probe.",
            peak_at_truth="ours() Doppler-guarded argmax equals (zero-Doppler row + dopp_bin_true, r_bin_true).",
            named_definitions_matching="function/class names matching grep_pattern (AST).",
            component_id="comma-free row identifier for condition selectors.",
            hits_spec_terms_only="matching lines for spec_grep_pattern (spec terms only), same file set.",
            implementation_defs="function/class definitions (AST) whose name matches spec_grep_pattern.",
            library_calls_or_imports=("AST call nodes whose function name (or base.name) is in library_call_names, "
                                      "plus import statements of library_modules or of those names."),
            library_calls_or_imports_in_functions_calling_cfar=("subset whose innermost enclosing function (or the "
                                                                "module body) also calls a function whose name contains "
                                                                "'cfar'."),
            library_calls_or_imports_in_files_calling_cfar="subset in files with any call to a name containing 'cfar'.",
            implementation_defs_or_library_calls_in_files_calling_cfar=(
                "implementation_defs in files calling a cfar function plus library_calls_or_imports_in_files_calling_cfar; "
                "0 means no named definition or listed library call of that component sits in a file on the CFAR "
                "detection path."),
            dB_ratio_sign=("physical_combiner_loss_db and f14 loss_db are 10log10 / 20log10 ratios and are negative "
                           "when power is lost; do not add a second minus sign when writing 'loss'."),
            mask_mismatches_at_production_pfa="mask_mismatches with pfa = the L1 production pfa_nominal.",
        ),
        assumptions=[
            dict(id="synthetic_cpi_f1f2", flagged=True, text="Findings 1-2 use an analytic integer-delay echo on a "
                 "tiled QPSK frame, not a Sionna kernel echo or a report12 waveform."),
            dict(id="dpi_amplitude", flagged=True, text="Precomputed adds the module DPI_AMP direct-path term "
                 "(value recorded in f4_cfar.report12_l1_check.dpi_amplitude; env SIONNA2_DPI_AMP unset="
                 f"{'SIONNA2_DPI_AMP' not in os.environ})."),
            dict(id="l1_check_echo", flagged=True, text="report12 L1 check uses analytic_echo instead of the Sionna "
                 "kernel echo, geometry X410Scenario defaults, velocity and the echo amplitude scale read from "
                 "outputs/detection_rx_sweep.json meta (the velocity key and the analytic point-echo amplitude "
                 "scale key), one noise draw, n_rx 1 and 4, CFAR pfa from CONFIG f4 and, separately, the "
                 "production pfa_nominal of the L1 mode."),
            dict(id="speed_convention", flagged=True, text="Radial speed per Doppler bin uses the monostatic-equivalent "
                 "v = f_d * wavelength / 2; bistatic Doppler depends on geometry."),
            dict(id="f3_sizes", flagged=True, text="ECA low-Doppler rows use a short synthetic frame (Lf in "
                 "f3_eca.sizes) instead of the production frames (f3_eca.production_frame_rows, read from "
                 "outputs/detection_rx_sweep.json); taps and ridge are the production values (N_TAPS and ridge_rel "
                 "read from code)."),
            dict(id="f4_map", flagged=True, text="Float32 CFAR rows use a 64x32 unit-mean background with one strong cell; "
                 "real maps with extended ridges were not modelled."),
            dict(id="inventory_regex", flagged=True, text="Tracking inventory is a regex/AST text scan; a grep hit "
                 "is a mention, not an implementation, and a miss outside src/ and benchmark/ is not asserted. "
                 "grep_pattern is wider than the spec term list (spelling variants and near terms such as aoa, "
                 "bare gating, ndimage.label, track initiation, mota); spec_grep_pattern holds the spec terms only. "
                 "Library call names and modules per row are a chosen list, not an exhaustive one."),
        ],
    )
    LEDGER["sources"] = SOURCES
    write_ledger("started")

    import experiment_detection as ed
    import passive_process as pp
    hash_file("src/experiment_detection.py"); hash_file("src/passive_process.py"); hash_file("src/detection_gpu.py")
    hash_file("src/experiment_x410.py"); hash_file("src/sionna_chain.py"); hash_file("src/freespace_detect.py")
    hash_file("src/waveforms.py")
    c0_ok = bool(float(ed.C0) == SOURCES[0]["value"] and float(pp.C0) == SOURCES[0]["value"])
    LEDGER["_meta"]["repo_c0_equals_si_value"] = c0_ok

    ref_cpi, y_echo, wf = synthetic_cpi()
    pre = ed.Precomputed(y_echo, ref_cpi, wf, CONFIG["f1f2"]["M"], {"Rb": CONFIG["f1f2"]["meta_rb_values_m"][0]}).to_gpu()
    t = time.time(); LEDGER["f1_steering"] = section_f1(ed, pre); LEDGER["f1_steering"]["section_wall_s"] = r(time.time() - t, 2)
    write_ledger("partial:f1")
    t = time.time(); LEDGER["f2_range_axis"] = section_f2(ed, ref_cpi, y_echo, wf); LEDGER["f2_range_axis"]["section_wall_s"] = r(time.time() - t, 2)
    write_ledger("partial:f2")
    t = time.time(); LEDGER["f3_eca"] = section_f3(ed, pp); LEDGER["f3_eca"]["section_wall_s"] = r(time.time() - t, 2)
    write_ledger("partial:f3")
    t = time.time(); LEDGER["f4_cfar"] = section_f4(ed, pp); LEDGER["f4_cfar"]["section_wall_s"] = r(time.time() - t, 2)
    write_ledger("partial:f4")
    t = time.time(); LEDGER["f5_multi_target"] = section_f5(pp); LEDGER["f5_multi_target"]["section_wall_s"] = r(time.time() - t, 2)
    write_ledger("partial:f5")
    t = time.time(); LEDGER["f14_reference"] = section_f14(pp); LEDGER["f14_reference"]["section_wall_s"] = r(time.time() - t, 2)
    write_ledger("partial:f14")
    t = time.time()
    inv_rows, n_files = section_inventory()
    LEDGER["tracking_inventory"] = dict(rows=inv_rows, n_files_scanned=n_files, roots=CONFIG["inventory"]["roots"],
                                        exclude_glob=CONFIG["inventory"]["exclude_glob"],
                                        reusable_assets=section_reusable(),
                                        section_wall_s=None)
    LEDGER["tracking_inventory"]["section_wall_s"] = r(time.time() - t, 2)
    # hashes of every scanned file are too many to list individually; store one digest over (path, sha256)
    scan_digest = hashlib.sha256("\n".join(f"{p}\t{HASHES[p]}" for p in _py_files()).encode()).hexdigest()
    LEDGER["tracking_inventory"]["scanned_files_digest_sha256"] = scan_digest
    keep = {q["path"] for q in QUOTES} | {x[0] for x in REUSABLE} | {
        "src/experiment_detection.py", "src/passive_process.py", "src/detection_gpu.py", "src/experiment_x410.py",
        "src/sionna_chain.py", "src/freespace_detect.py", "src/waveforms.py",
        "outputs/detection_rx_sweep.json", "outputs/verify_pyapril.json"}
    for p in list(HASHES):
        if p not in keep:
            HASHES.pop(p, None)
    LEDGER["_meta"]["source_hashes_note"] = ("source_hashes lists files whose content a value depends on (quoted, "
                                             "executed or read ledgers); the full inventory scan is covered by "
                                             "tracking_inventory.scanned_files_digest_sha256.")
    LEDGER["_meta"]["quotes_failed"] = [q for q in QUOTES if not q["verified"]]
    write_ledger("complete")
    print(f"wrote {OUT}  ({time.time() - T0:.1f} s, quotes failed: {len(LEDGER['_meta']['quotes_failed'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
