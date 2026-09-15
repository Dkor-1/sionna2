"""What exists today for a Wi-Fi / LTE / 5G NR waveform benchmark (ISAC plan, 2026-09-15).

Purpose
    Build the ledger outputs/isac_plan_waveforms_0915.json that the ISAC detection+tracking plan
    report cites. It answers, with numbers computed in this run:
      1. sionna_phy_inventory  - what the installed Sionna PHY package offers (modules, NR exports,
                                 transform precoding, sync/CFO grep hits classified, FEC module
                                 files, per-symbol cyclic prefix).
      2. nr_pusch              - Sionna NR PUSCH bit chain: noise-free, negative control, 3-path LS,
                                 and the time-domain slot length for slot_number 0 and 1.
      3. native_bridge         - the same PUSCH grid put on the native 30.72 Msps / FFT-2048 raster
                                 with the per-symbol cyclic prefix (repo src/waveforms.ofdm_modulate),
                                 decoded under timing, CFO and AWGN impairments without any sync.
      4. wifi_shaped_grid      - a Wi-Fi-shaped 64-FFT tone map on Sionna's generic OFDM grid
                                 (a tone map only, NOT an 802.11 PPDU).
      5. legacy_generator      - src/waveforms.py stand-in generator: coding terms, PSS correlation
                                 against spec sequences, the 32 bandwidth calls, power bookkeeping.
      6. installed_elsewhere   - whether any 802.11 / LTE implementation, UHD, GNU Radio, MATLAB or
                                 Octave is installed on this host.
      7. x410_rates            - which candidate sample rates are integer divisors of the X410
                                 master clock rates.
      8. slow_time_rates       - symbol rate and one-reference-per-slot rate from numerology.

Run (from the repository root)
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/isac_plan_waveforms_0915.py
    Optional: --root <repo root> (default: parent of this file's directory)
              --out <ledger path> (default: <root>/outputs/isac_plan_waveforms_0915.json)
              --core <cpu index> (default: lowest core in the current affinity)
    The script pins itself to ONE CPU core and hides GPUs before importing numpy/torch.

Runtime
    About 3-4 minutes on one CPU core (Sionna 2.1.0 on PyTorch, CPU); the native bridge takes most of it.

Scope
    These are simulation / code / bookkeeping checks on installed software and repository code.
    There is no comparison against RF measurements; nothing here is a measured result. A profile that
    decodes here is only self-consistent inside this simulation.
"""
from __future__ import annotations

import argparse
import os
import sys


def _early_args():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="repository root (default: parent of the script directory)")
    ap.add_argument("--out", default=None, help="ledger path (default: <root>/outputs/isac_plan_waveforms_0915.json)")
    ap.add_argument("--core", type=int, default=None, help="single CPU core to pin to (default: lowest allowed)")
    return ap.parse_args()


ARGS = _early_args()
# Hide GPUs and bound threads BEFORE importing numpy / torch / sionna.
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["SIONNA2_ALLOW_CPU"] = "1"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"
_CORE = ARGS.core if ARGS.core is not None else min(os.sched_getaffinity(0))
os.sched_setaffinity(0, {_CORE})
sys.dont_write_bytecode = True  # read-only use of the repository: no __pycache__ writes from src imports

import ast  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import importlib.metadata as _md  # noqa: E402
import importlib.util  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
import tokenize  # noqa: E402
from fractions import Fraction  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

NAME = "isac_plan_waveforms_0915"
ROOT = Path(ARGS.root).resolve() if ARGS.root else Path(__file__).resolve().parents[1]
OUT = Path(ARGS.out).resolve() if ARGS.out else ROOT / "outputs" / f"{NAME}.json"

# --------------------------------------------------------------------------------------------------
# Configuration inputs (seeds, grids, sizes). Not results.
# --------------------------------------------------------------------------------------------------
CFG = {
    "torch_seed": 20260915,
    "numpy_seed": 915,
    "noise_free_receiver_no": 1e-6,          # receiver noise-variance argument for "noise-free" runs
    "pusch_default_n_blocks": 64,
    "pusch_20mhz": {"scs_khz": 30, "n_prb": 51, "mcs_index": 16, "mcs_table": 1},
    "pusch_20mhz_n_blocks": 16,
    "time_domain_slots": [0, 1],
    "time_domain_n_blocks": 4,
    "three_path": {"gains_abs": [1.0, 0.5, 0.2], "gains_phase_rad": [0.0, 1.0, -2.0],
                   "delays_ns": [0.0, 100.0, 400.0]},
    "three_path_noise_vars": [1e-6, 0.1],
    "bridge": {"scs_khz": 15, "n_prb": 106, "mcs_index": 10, "dmrs_additional_position": 1, "fft": 2048,
               "n_blocks": 16, "fft_window_early_samples": 8, "delay_samples": 300,
               "cfo_fraction_of_scs": [0.01, 0.05, 0.2], "awgn_snr_db_per_sample": 10.0},
    "wifi_grid": {"n_ofdm_symbols": 12, "fft": 64, "scs_hz": 312.5e3, "cp_samples": 16, "guard": [6, 5],
                  "pilot_tone_indices": [-21, -7, 7, 21], "pilot_values": [1, 1, 1, -1],
                  "n_blocks": 8, "noise_vars": [1e-6, 0.05],
                  "channel_gains": [[1.0, 0.0], [0.4, 1.0], [0.2, 1.5707963267948966]],  # [abs, phase rad]
                  "channel_delays_ns": [0.0, 50.0, 150.0]},
    "legacy_f15_calls": {"wifi": [20, 40, 80, 160], "lte": [1.4, 3, 5, 10, 15, 20],
                         "nr": [5, 10, 20, 40, 50, 100], "profiles": ["G1", "G3"]},
    "fec_terms": ["crc", "ldpc", "turbo", "convol", "viterbi", "scrambl", "interleav", "polar",
                  "encode", "decode", "mcs"],
    # Candidate sample rates in Msps (strings so the divisibility test is exact).
    "x410_candidate_rates_msps": ["20", "25", "30.72", "40", "61.44", "80", "122.88"],
    "sync_cfo_grep_regex": r"carrier frequency offset|\bcfo\b|timing offset|preamble|synchroniz",
    # Rules that classify each grep hit as synchronisation / timing / CFO estimation code or not.
    "sync_cfo_classification": {
        "compute_context_regex": r"(?i)cuda|device|accelerator|\brng\b|random|graph capture|cholesky",
        "estimation_def_name_regex": r"(?i)sync|cfo|timing|preamble|freq\w*_?offset|time_?offset",
    },
    # FFT size of the Sionna OFDMModulator/Demodulator per-symbol CP round trip; the CP pattern itself is
    # the LTE/NR 15 kHz subframe pattern from sources lte_numerology, scaled from FFT 2048 to this FFT.
    "cp_vector_test_fft": 64,
    # NR numerologies evaluated (subcarrier spacings in kHz).
    "legacy_nr_scs_khz": [15, 30, 60],
    "slow_time_nr_scs_khz": [15, 30, 60],
    "installed_search": {
        "dist_name_regex": r"(?i)80211|wlan|wifi|\blte\b|3gpp|srsran|commpy|py3gpp|pyphy|uhd|gnuradio|"
                           r"sdr|nr5g|matlab|octave|oai|openairinterface",
        "module_names": ["uhd", "gnuradio", "commpy", "py3gpp", "wifi80211", "ieee80211", "pyltesim",
                         "srsran", "matlab", "matlab.engine", "oct2py"],
        "executables": ["matlab", "octave", "octave-cli", "uhd_find_devices", "uhd_usrp_probe",
                        "gnuradio-config-info", "gnuradio-companion", "srsenb", "srsue", "gnb"],
        "library_regex": r"libuhd|libgnuradio|libsrsran",
        "system_site_dirs": ["/usr/local/lib/python3.12/dist-packages", "/usr/lib/python3/dist-packages"],
        "install_dirs": ["/usr/local/MATLAB", "/opt/matlab", "/opt/MATLAB", "/usr/share/octave",
                         "/usr/local/share/uhd", "/usr/share/uhd", "/usr/local/share/gnuradio"],
    },
}

# --------------------------------------------------------------------------------------------------
# External specification / literature values. Every non-configuration literal lives here.
# --------------------------------------------------------------------------------------------------
SOURCES = [
    {"id": "uhd_x410_mcr", "values": {"master_clock_rates_mhz_200mhz_image": ["245.76", "250"]},
     "url": "https://uhd.readthedocs.io/en/latest/page_usrp_x4xx.html",
     "document": "UHD manual, USRP X4x0 Series page",
     "locator": "section 'Master Clock Rates', subsection 'USRP X410'",
     "note": "Quoted there: 'The 200 MHz images allow master clock rates of 245.76 MHz or 250 MHz.' and "
             "'Applications that require 200 MHz bandwidth or less, should use the 200 MHz images and make use "
             "of the DDC/DUC for lower rates.' Page fetched 2026-09-15. The maximum DDC decimation of the "
             "installed FPGA image was not checked."},
    {"id": "nr_pss_mseq", "values": {"length": 127, "shift_per_n_id2": 43, "init_x6_to_x0": [1, 1, 1, 0, 1, 1, 0],
                                     "recursion_taps": [4, 0]},
     "url": "https://raw.githubusercontent.com/srsran/srsRAN_4G/master/lib/src/phy/sync/pss_nr.c",
     "document": "3GPP TS 38.211 section 7.4.2.2.1 (NR PSS); cross-read in srsRAN_4G pss_nr.c",
     "locator": "srsRAN_4G lib/src/phy/sync/pss_nr.c: macro PSS_NR_SEQUENCE_M(N_id_2) "
                "((43U * (N_id_2)) % SRSRAN_PSS_NR_LEN); function pss_nr_pregen(): initial state "
                "x[6..0] = 1,1,1,0,1,1,0, recursion x[i + 7] = (x[i + 4] + x[i]) % 2, mapping "
                "pss_nr_d[i] = 1.0f - 2.0f * x[i]. lib/include/srsran/phy/sync/pss_nr.h: macro SRSRAN_PSS_NR_LEN 127",
     "note": "d(n)=1-2x(m), m=(n+43*N_ID2) mod 127. The TS 38.211 text itself was not opened in this run "
             "(ETSI download returned 403 earlier); the constants were read in the srsRAN source "
             "(pss_nr.c and pss_nr.h fetched 2026-09-15 with a web fetch tool; located by macro/function name)."},
    {"id": "lte_pss_zc", "values": {"roots_for_n_id2_0_1_2": [25, 29, 34], "zc_length": 63, "n_tones": 62},
     "url": "https://raw.githubusercontent.com/srsran/srsRAN_4G/master/lib/src/phy/sync/pss.c",
     "document": "3GPP TS 36.211 section 6.11.1.1 (LTE PSS); cross-read in srsRAN_4G pss.c srsran_pss_generate",
     "locator": "root_value[] = {25.0, 29.0, 34.0} (about line 241); sign=-1 (about line 247); phase formulas "
                "for n<31 and n>=31 divided by 63.0 (about lines 255 and 260)",
     "note": "d_u(n)=exp(-j*pi*u*n(n+1)/63) for n=0..30 and exp(-j*pi*u*(n+1)(n+2)/63) for n=31..61. "
             "TS 36.211 text not opened in this run; constants read in srsRAN source."},
    {"id": "lte_numerology", "values": {"scs_hz": 15000, "symbols_per_slot_normal_cp": 7, "slots_per_subframe": 2,
                                        "cp_first_samples_at_30p72": 160, "cp_other_samples_at_30p72": 144,
                                        "fft_at_30p72": 2048, "subframe_s": "0.001"},
     "url": "https://raw.githubusercontent.com/srsran/srsRAN_4G/master/lib/include/srsran/phy/common/phy_common.h",
     "document": "3GPP TS 36.211 section 4.1 and Table 6.12-1; cross-read in srsRAN_4G phy_common.h",
     "locator": "SRSRAN_NOF_SLOTS_PER_SF 2 (about line 50), SRSRAN_CP_NORM_NSYMB 7 (about line 64), "
                "SRSRAN_CP_NORM_0_LEN 160 / SRSRAN_CP_NORM_LEN 144 (about lines 67-68), "
                "SRSRAN_LTE_TS 1/(15000*2048) (about line 95)",
     "note": "TS 36.211 text not opened in this run. The repo generator's LTE subframe length is recomputed "
             "at run time as a cross-check."},
    {"id": "wifi_legacy_numerology", "values": {"t_fft_us": "3.2", "gi_us": "0.8", "fft_20mhz": 64},
     "url": "https://www.litepoint.com/blog/wi-fi-6-vs-wi-fi-5-key-changes-to-the-rf-physical-layer/",
     "document": "IEEE Std 802.11-2020 Table 17-5 (timing-related parameters, not opened: paywalled); "
                 "secondary pages LitePoint blog and Keysight 89600 WLAN help 'Guard Interval'",
     "locator": "LitePoint: 'from 3.2 us in 802.11ac to 12.8 us in 802.11ax'; '802.11ac had two Guard Interval "
                "(GI) options - long GI (0.8us) and short GI (0.4us)'. Keysight: "
                "https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/wlan-mimo/content/mimo_fmt_grdintparams.htm",
     "note": "The secondary pages state the 802.11n/ac values; the non-HT 20 MHz OFDM PHY uses the same 3.2 us FFT "
             "period and 0.8 us GI (IEEE table not opened). FFT 64 at 20 Msps is the usual implementation raster."},
    {"id": "wifi_he_numerology", "values": {"t_fft_us": "12.8", "gi_us": ["0.8", "1.6", "3.2"]},
     "url": "https://www.litepoint.com/blog/wi-fi-6-vs-wi-fi-5-key-changes-to-the-rf-physical-layer/",
     "document": "IEEE Std 802.11ax-2021 Table 27-12 (timing-related constants, not opened: paywalled); "
                 "secondary page LitePoint blog",
     "locator": "'For 802.11ax, there is now a spectral spacing of 78.125 kHz between subcarriers'; "
                "'802.11ax has three types of GI - the normal GI (0.8 us), double (1.6 us) GI and quadruple (3.2 us) GI'",
     "note": "Values from secondary pages fetched 2026-09-15."},
]
SRC = {s["id"]: s["values"] for s in SOURCES}

HASHED: dict[str, str] = {}
QUOTES: list[dict] = []


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def relname(p: Path) -> str:
    p = Path(p).resolve()
    try:
        return "repo:" + p.relative_to(ROOT).as_posix()
    except ValueError:
        pass
    sp = Path(importlib.util.find_spec("sionna").origin).resolve().parents[1]
    try:
        return "site-packages:" + p.relative_to(sp).as_posix()
    except ValueError:
        return "external:" + p.name


def track(p: Path) -> str:
    key = relname(p)
    HASHED[key] = sha256_file(Path(p))
    return key


def quote(qid: str, p: Path, line: int, text: str) -> bool:
    """Open a text file, check that the stated 1-indexed line contains the quoted text."""
    lines = Path(p).read_text(encoding="utf-8").splitlines()
    ok = 1 <= line <= len(lines) and text in lines[line - 1]
    found = [i + 1 for i, s in enumerate(lines) if text in s]
    QUOTES.append({"id": qid, "path": track(p), "line": line, "quote": text, "found_at_line": ok,
                   "lines_containing_quote": found, "sha256": HASHED[relname(p)]})
    return ok


def utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def db(x: float) -> float:
    return float(10.0 * np.log10(x))


LEDGER: dict = {}
UNIQUE_CHECKS: list[dict] = []


def check_unique(where: str, rows: list, keys: list[str]) -> bool:
    """Every row must carry the identifying keys, the key combination must be unique, and string
    values must not contain ',' or ']' (they would break the report's condition selector)."""
    combos = [tuple(str(r.get(k)) for k in keys) for r in rows]
    ok_keys = all(all(k in r for k in keys) for r in rows)
    ok_unique = len(set(combos)) == len(combos)
    ok_chars = all(not any(c in v for c in ",]") for combo in combos for v in combo)
    UNIQUE_CHECKS.append({"list": where, "keys": keys, "n_rows": len(rows), "all_rows_have_keys": ok_keys,
                          "unique": ok_unique, "selector_safe_values": ok_chars})
    return ok_keys and ok_unique and ok_chars


def checkpoint(section: str | None, meta: dict, final: bool = False) -> None:
    if section:
        meta["sections_done"].append(section)
    meta["source_hashes"] = [{"path": k, "sha256": v} for k, v in sorted(HASHED.items())]
    meta["quotes_verified"] = QUOTES
    meta["selector_uniqueness_checks"] = UNIQUE_CHECKS
    if final:
        meta["finished_utc"] = utc()
        meta["wall_time_s"] = round(time.time() - T0, 1)
        meta["status"] = "complete"
    doc = {"_meta": meta, "sources": SOURCES, **LEDGER}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(f"[{utc()}] checkpoint {section or 'final'} -> {OUT}", flush=True)


T0 = time.time()

# ==================================================================================================
import torch  # noqa: E402
import sionna  # noqa: E402
from sionna.phy import config as sn_config  # noqa: E402

torch.manual_seed(CFG["torch_seed"])
sn_config.seed = CFG["torch_seed"]
SIONNA_DIR = Path(importlib.util.find_spec("sionna").origin).resolve().parent
PHY = SIONNA_DIR / "phy"

sys.path.insert(0, str(ROOT / "src"))
import waveforms as W  # noqa: E402  (repo legacy generator; numpy only)


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def versions() -> dict:
    out = {"python": platform.python_version()}
    for d in ("sionna", "sionna-rt", "torch", "numpy", "mitsuba", "drjit"):
        try:
            out[d] = _md.version(d)
        except _md.PackageNotFoundError:
            out[d] = "not installed"
    out["torch_cuda_available"] = bool(torch.cuda.is_available())
    out["sionna_device"] = str(sn_config.device)
    return out


META = {
    "generator": f"benchmark/{NAME}.py",
    "command": f'CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/{NAME}.py',
    "argv": [a if not a.startswith("/") else (relname(Path(a)) if relname(Path(a)).startswith("repo:")
                                              or Path(a).resolve() == ROOT else "<path outside root>")
             for a in sys.argv[1:]],
    "started_utc": utc(),
    "finished_utc": None,
    "status": "partial",
    "git_head": git_head(),
    "cpu_core": _CORE,
    "versions": versions(),
    "scope": "Simulation / code / bookkeeping checks on installed Sionna 2.1.0 (CPU) and repository code. "
             "No comparison against RF measurements. Decoding success here means self-consistent in "
             "simulation only.",
    "config": CFG,
    "definitions": {
        "ber": "fraction of transport-block (or information) bits where the decoded bit differs from the "
               "transmitted bit, over all blocks of the row",
        "crc_pass / crc_total": "number of transport blocks whose Sionna TB CRC status is True / number of blocks",
        "noise_free": "no noise added to the signal; the receiver is given noise variance "
                      "config.noise_free_receiver_no",
        "negative_control_random_phase": "each received resource element multiplied by exp(j*pi*U), U~Uniform[0,1) "
                                         "independently; a working CRC must fail",
        "three_path_ls": "frequency-domain 3-path channel (config.three_path) applied with ApplyOFDMChannel, "
                         "PUSCH LS channel estimation (receiver default) and LMMSE detection",
        "time_domain duration_us": "n_samples / (fft_size * subcarrier_spacing) * 1e6, with n_samples the "
                                   "length of PUSCHTransmitter(output_domain='time') output",
        "native_bridge": "PUSCH frequency grid (DC-centred) placed on an FFT-2048 raster, per-symbol CP from the "
                         "LTE/NR 15 kHz numerology, modulated with repo src/waveforms.ofdm_modulate, demodulated "
                         "with a numpy FFT window at the nominal CP boundary (no timing or CFO estimation), "
                         "decoded with Sionna PUSCHReceiver in the frequency domain",
        "fft_window_8_early": "demodulation FFT window starts 8 samples earlier than nominal (inside the CP)",
        "delay_300_samples": "300 zero samples prepended, tail truncated to keep the slot length; no timing sync",
        "cfo_<x>_scs": "signal multiplied by exp(j*2*pi*x*scs*n/fs), n the sample index; no CFO correction",
        "awgn_10db_per_sample": "SNR per time sample = mean |x[n]|^2 over all slot samples and blocks (CP and "
                                "unused FFT bins included) divided by the complex noise variance per sample; "
                                "see per_re_snr_db for the frequency-grid view. Not an Es/N0 of the coded bits.",
        "computed_signal_power_per_sample": "mean |x[n]|^2 of the noise-free bridge signal over all slot samples "
                                            "and blocks (CP and unused FFT bins included), computed in this run",
        "computed_noise_snr_db_per_sample": "10log10(computed_signal_power_per_sample / mean |w[n]|^2), w the "
                                            "noise realisation drawn in this run (differs from "
                                            "snr_db_per_sample_target by the finite-sample spread)",
        "per_re_snr_db": "10log10(P_grid / noise_var_per_sample), P_grid = mean |x|^2 over every resource element "
                         "of the whole PUSCH frequency grid (all OFDM symbols x all subcarriers x all blocks), "
                         "including the resource elements left empty on DMRS symbols (counted in "
                         "per_re_grid_n_zero_re); it is therefore not the energy per occupied resource element. "
                         "noise_var_per_sample equals the per-bin noise variance after the unitary FFT (assumption a3)",
        "per_re_grid_n_re": "number of resource elements in the PUSCH frequency grid over all blocks "
                            "(blocks x OFDM symbols x subcarriers)",
        "per_re_grid_n_zero_re": "number of those resource elements with x == 0 exactly",
        "per_re_grid_zero_re_only_on_dmrs_symbols": "True when every zero resource element lies on an OFDM symbol "
                                                    "listed in native_bridge.dmrs_symbol_indices",
        "wifi_shaped_grid ber": "information-bit error rate of LDPC5G-coded QPSK on the tone map after a "
                                "frequency-domain 3-path channel, LS estimation (nearest-neighbour "
                                "interpolation) and LMMSE equalisation",
        "nr_pss_corr / lte_pss_corr": "|<d_spec, g>| / (||d_spec|| ||g||), g the generator's PSS resource "
                                      "elements, d_spec the spec sequence from sources",
        "fec_term_hits": "number of case-insensitive substring occurrences of each term in src/waveforms.py",
        "f15 returned_occupied_mhz": "Waveform.bw_hz / 1e6 returned by the generator (its 'channel occupied "
                                     "band' metadata); null when the call raised",
        "f16 iq_minus_occupancy_db": "10log10(mean|tx|^2 profile / mean|tx|^2 G3) - "
                                     "10log10(occupancy_frac profile / occupancy_frac G3)",
        "f16 grid_energy_minus_iq_db": "10log10(sum|grid|^2 profile / sum|grid|^2 G3) - "
                                       "10log10(mean|tx|^2 profile / mean|tx|^2 G3)",
        "x410 divides": "Fraction(MCR)/Fraction(rate) is an integer (exact decimal arithmetic)",
        "symbol_rate_hz": "OFDM symbols per second averaged over a slot/subframe (CP included)",
        "one_rs_per_slot_rate_hz": "1 / slot duration: the slow-time sampling rate if one reference-signal "
                                   "occasion per slot is used; null where the standard has no slot structure",
        "sync_cfo_grep_hits": "number of source lines in sionna/phy/**/*.py matching config.sync_cfo_grep_regex "
                              "(case-insensitive); each hit is listed",
        "sync_cfo_hit_classification": "one row per grep hit: file_line (path:line), text (stripped line, first "
                                       "160 characters), match_in ('code' when any matched character lies outside "
                                       "comment and string tokens of Python tokenize, else 'comment' or "
                                       "'string_or_docstring'), enclosing_defs (names of the class/function "
                                       "definitions containing the line, outermost first), compute_context "
                                       "(line matches config.sync_cfo_classification.compute_context_regex: "
                                       "CUDA/device/RNG synchronisation wording), is_signal_processing",
        "is_signal_processing": "(match_in == 'code' OR any enclosing_defs name matches "
                                "config.sync_cfo_classification.estimation_def_name_regex) AND NOT compute_context. "
                                "True means the hit is part of synchronisation / timing / CFO estimation code; "
                                "comments and docstrings outside such definitions (e.g. the OFDMDemodulator l_min "
                                "docstring, a fixed configured FFT-window offset) are False",
        "sync_cfo_signal_processing_hits": "number of sync_cfo_hit_classification rows with is_signal_processing True",
        "fec_submodules": "relative paths of every .py file under the installed sionna/phy/fec directory "
                          "(recursive, sorted; __pycache__ excluded, package __init__.py files included)",
    },
    "assumptions": [
        {"id": "a1", "flag": "ASSUMED", "text": "The 3-path channel gains/delays and all noise variances are "
                                               "arbitrary configuration choices, not a measured channel."},
        {"id": "a2", "flag": "ASSUMED", "text": "The native bridge uses a hand-written numpy FFT demodulator "
                                               "matching repo ofdm_modulate scaling (ifft*sqrt(N) / fft/sqrt(N))."},
        {"id": "a3", "flag": "ASSUMED", "text": "For the AWGN row the receiver is told the per-sample noise "
                                               "variance, which equals the per-bin variance after a unitary FFT."},
        {"id": "a4", "flag": "ASSUMED", "text": "installed_elsewhere is a name-based search (distribution names, "
                                               "importable module names, executables on PATH, shared libraries, "
                                               "fixed install directories). A renamed or hand-copied "
                                               "implementation would be missed."},
        {"id": "a5", "flag": "ASSUMED", "text": "x410_rates only tests integer divisibility of the master clock "
                                               "rate; the DDC/DUC decimation range of the FPGA image was not checked."},
        {"id": "a6", "flag": "ASSUMED", "text": "Wi-Fi slow-time rates assume every OFDM symbol carries pilots; "
                                               "PPDU repetition is traffic dependent and not computed."},
        {"id": "a7", "flag": "EXTERNAL", "text": "Spec constants come from the sources table; several were read in "
                                                "srsRAN source or secondary pages instead of the 3GPP/IEEE text."},
    ],
    "sections_done": [],
}
HASHED[f"repo:benchmark/{NAME}.py"] = sha256_file(Path(__file__))

# ==================================================================================================
# 1. sionna_phy_inventory
# ==================================================================================================
print("section 1: sionna_phy_inventory", flush=True)
from sionna.phy import nr as sn_nr  # noqa: E402
from sionna.phy.nr import PUSCHConfig, PUSCHTransmitter, PUSCHReceiver  # noqa: E402
from sionna.phy.ofdm import OFDMModulator, OFDMDemodulator  # noqa: E402


def list_modules() -> list[str]:
    mods = []
    for child in sorted(PHY.iterdir()):
        if child.name.startswith("_"):
            continue
        if child.is_dir() and (child / "__init__.py").exists():
            mods.append("sionna.phy." + child.name)
            for g in sorted(child.iterdir()):
                if g.is_dir() and (g / "__init__.py").exists() and not g.name.startswith("_"):
                    mods.append(f"sionna.phy.{child.name}.{g.name}")
        elif child.suffix == ".py":
            mods.append("sionna.phy." + child.stem)
    return mods


nr_exports = list(getattr(sn_nr, "__all__", []))
track(PHY / "nr" / "__init__.py")
downlink_like = [e for e in nr_exports if re.search(r"PDSCH|PDCCH|SSB|PBCH|CSI|PRS|PSS|SSS", e)]

# transform precoding: runtime + quote
tp_runtime = False
tp_msg = ""
try:
    _pc = PUSCHConfig()
    _pc.transform_precoding = True
except NotImplementedError as e:
    tp_runtime = True
    tp_msg = str(e)
tp_q1 = quote("sionna_transform_precoding_raise", PHY / "nr" / "pusch_config.py", 258,
              "raise NotImplementedError(_TRANSFORM_PRECODING_ERROR)")
tp_q2 = quote("sionna_transform_precoding_msg", PHY / "nr" / "pusch_config.py", 19,
              "PUSCH transform precoding is not implemented")

# per-symbol CP vector: runtime + quotes
LTE_NUM = SRC["lte_numerology"]
cp_vec = np.array(([LTE_NUM["cp_first_samples_at_30p72"]]
                   + [LTE_NUM["cp_other_samples_at_30p72"]] * (LTE_NUM["symbols_per_slot_normal_cp"] - 1))
                  * LTE_NUM["slots_per_subframe"], dtype=np.int64)
_fft = CFG["cp_vector_test_fft"]
_cp_div = LTE_NUM["fft_at_30p72"] // _fft
_cpv = np.minimum(cp_vec // _cp_div, _fft)
_mod = OFDMModulator(cyclic_prefix_length=_cpv)
_xg = torch.zeros(1, len(cp_vec), _fft, dtype=torch.complex64)
_xg[..., 5] = 1.0
_xt = _mod(_xg)
_demod = OFDMDemodulator(_fft, 0, _cpv)
_back = _demod(_xt)
cp_vec_len_ok = int(_xt.shape[-1]) == len(_cpv) * _fft + int(_cpv.sum())
cp_vec_roundtrip_err = float((_back - _xg).abs().max())
cp_q1 = quote("sionna_modulator_cp_vector_param", PHY / "ofdm" / "modulator.py", 23,
              "Integer or vector of integers indicating the")
cp_q2 = quote("sionna_modulator_cp_vector_output", PHY / "ofdm" / "modulator.py", 34,
              "num_ofdm_symbols*fft_size+sum(cyclic_prefix_length)")
cp_q3 = quote("sionna_demodulator_cp_vector_param", PHY / "ofdm" / "demodulator.py", 62,
              "Integer or vector of integers indicating the")
q_carrier_cp = quote("sionna_carrier_single_cp_slot_rule", PHY / "nr" / "carrier_config.py", 257,
                     "if self.slot_number in [0, 7 * 2**self.mu]:")
q_pdsch = quote("sionna_tbencoder_pdsch_channel_type", PHY / "nr" / "tb_encoder.py", 140,
                "if channel_type not in (\"PDSCH\", \"PUSCH\"):")

# sync / CFO grep
rx_sync = re.compile(CFG["sync_cfo_grep_regex"], re.I)
SCL = CFG["sync_cfo_classification"]
rx_compute = re.compile(SCL["compute_context_regex"])
rx_est_name = re.compile(SCL["estimation_def_name_regex"])


def non_code_spans(txt: str) -> dict[int, list[tuple[int, int, str]]]:
    """Per 1-indexed line, character ranges covered by COMMENT or STRING tokens (Python tokenize)."""
    spans: dict[int, list[tuple[int, int, str]]] = {}
    kinds = {tokenize.COMMENT: "comment", tokenize.STRING: "string_or_docstring"}
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        if hasattr(tokenize, name):
            kinds[getattr(tokenize, name)] = "string_or_docstring"
    lines = txt.splitlines()
    for tok in tokenize.generate_tokens(io.StringIO(txt).readline):
        if tok.type not in kinds:
            continue
        (sr, sc), (er, ec) = tok.start, tok.end
        for ln in range(sr, er + 1):
            a = sc if ln == sr else 0
            b = ec if ln == er else len(lines[ln - 1]) if ln - 1 < len(lines) else 0
            spans.setdefault(ln, []).append((a, b, kinds[tok.type]))
    return spans


def enclosing_defs(tree: ast.AST, line: int) -> list[str]:
    found = [n for n in ast.walk(tree)
             if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
             and n.lineno <= line <= (n.end_lineno or n.lineno)]
    return [n.name for n in sorted(found, key=lambda n: (n.lineno, -(n.end_lineno or n.lineno)))]


sync_hits = []
sync_class_rows = []
sync_named_defs = []
for py in sorted(PHY.rglob("*.py")):
    if "__pycache__" in py.parts:
        continue
    txt = py.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(txt)
    except SyntaxError:
        tree = None
    spans = None
    for i, s in enumerate(txt.splitlines(), 1):
        if rx_sync.search(s):
            sync_hits.append({"path": relname(py), "line": i, "text": s.strip()[:160]})
            track(py)
            if spans is None:
                spans = non_code_spans(txt)
            where = set()
            for mt in rx_sync.finditer(s):
                for c in range(mt.start(), mt.end()):
                    k = next((kind for a, b, kind in spans.get(i, []) if a <= c < b), "code")
                    where.add(k)
            match_in = "code" if "code" in where else ("comment" if where == {"comment"} else "string_or_docstring")
            defs = enclosing_defs(tree, i) if tree is not None else []
            compute_ctx = bool(rx_compute.search(s))
            is_sp = bool((match_in == "code" or any(rx_est_name.search(nm) for nm in defs)) and not compute_ctx)
            sync_class_rows.append({"file_line": f"{relname(py)}:{i}", "text": s.strip()[:160],
                                    "match_in": match_in, "enclosing_defs": defs,
                                    "compute_context": compute_ctx, "is_signal_processing": is_sp})
    if tree is None:
        continue
    for n in ast.walk(tree):
        if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and re.search(r"(?i)sync|cfo|timing|preamble", n.name):
            sync_named_defs.append({"path": relname(py), "line": n.lineno, "name": n.name})

LEDGER["sionna_phy_inventory"] = {
    "modules": list_modules(),
    "fec_submodules": sorted(p.relative_to(PHY / "fec").as_posix() for p in (PHY / "fec").rglob("*.py")
                             if "__pycache__" not in p.parts),
    "nr_exports": nr_exports,
    "nr_exports_matching_downlink_signal_names": downlink_like,
    "transform_precoding_not_implemented": bool(tp_runtime and tp_q1 and tp_q2),
    "transform_precoding_runtime_raised": tp_runtime,
    "transform_precoding_runtime_message": tp_msg,
    "sync_cfo_grep_hits": len(sync_hits),
    "sync_cfo_grep_hit_lines": sync_hits,
    "sync_cfo_signal_processing_hits": int(sum(r["is_signal_processing"] for r in sync_class_rows)),
    "sync_cfo_hit_classification": sync_class_rows,
    "sync_cfo_named_class_or_function_defs": len(sync_named_defs),
    "sync_cfo_named_defs_list": sync_named_defs,
    "ofdm_modulator_accepts_cp_vector": bool(cp_vec_len_ok and cp_q1 and cp_q2),
    "ofdm_cp_vector_runtime": {"n_symbols": len(_cpv), "fft": _fft, "cp_samples": _cpv.tolist(),
                               "output_length": int(_xt.shape[-1]), "length_matches_sum_rule": cp_vec_len_ok,
                               "demodulator_roundtrip_max_abs_error": cp_vec_roundtrip_err,
                               "demodulator_quote_ok": cp_q3},
    "carrier_config_single_cp_quote_ok": q_carrier_cp,
    "tb_encoder_accepts_pdsch_quote_ok": q_pdsch,
    "versions": META["versions"],
}
checkpoint("sionna_phy_inventory", META)

# ==================================================================================================
# 2. nr_pusch
# ==================================================================================================
print("section 2: nr_pusch", flush=True)
from sionna.phy.channel import cir_to_ofdm_channel, subcarrier_frequencies, ApplyOFDMChannel  # noqa: E402

NO0 = CFG["noise_free_receiver_no"]


def ber_of(b, bh) -> float:
    return float((b != bh).float().mean())


rows = []
pc = PUSCHConfig()
tx = PUSCHTransmitter(pc)
rx = PUSCHReceiver(tx, return_tb_crc_status=True)
x, b = tx(CFG["pusch_default_n_blocks"])
bh, crc = rx(x, NO0)
rows.append({"test": "freq_domain_noise_free", "config": "PUSCHConfig() defaults",
             "subcarrier_spacing_khz": float(pc.carrier.subcarrier_spacing), "n_prb": int(pc.carrier.n_size_grid),
             "tb_bits": int(b.shape[-1]), "noise_var": NO0, "n_blocks": int(crc.numel()), "ber": ber_of(b, bh),
             "crc_pass": int(crc.sum()), "crc_total": int(crc.numel())})
g = torch.Generator().manual_seed(CFG["torch_seed"] + 1)
phase = torch.rand(x.shape, generator=g, dtype=torch.float32)
y = x * torch.exp(1j * torch.pi * phase).to(x.dtype)
bh, crc = rx(y, NO0)
rows.append({"test": "negative_control_random_phase", "config": "PUSCHConfig() defaults",
             "subcarrier_spacing_khz": float(pc.carrier.subcarrier_spacing), "n_prb": int(pc.carrier.n_size_grid),
             "tb_bits": int(b.shape[-1]), "noise_var": NO0, "n_blocks": int(crc.numel()), "ber": ber_of(b, bh),
             "crc_pass": int(crc.sum()), "crc_total": int(crc.numel())})


def pusch20(slot_number: int = 0) -> PUSCHConfig:
    c = PUSCHConfig()
    c.carrier.subcarrier_spacing = CFG["pusch_20mhz"]["scs_khz"]
    c.carrier.n_size_grid = CFG["pusch_20mhz"]["n_prb"]
    c.carrier.slot_number = slot_number
    c.n_size_bwp = CFG["pusch_20mhz"]["n_prb"]
    c.tb.mcs_index = CFG["pusch_20mhz"]["mcs_index"]
    c.tb.mcs_table = CFG["pusch_20mhz"]["mcs_table"]
    return c


pc2 = pusch20(0)
tx3 = PUSCHTransmitter(pc2, output_domain="freq")
rx3 = PUSCHReceiver(tx3, return_tb_crc_status=True)
nb3 = CFG["pusch_20mhz_n_blocks"]
x3, b3 = tx3(nb3)
rg3 = tx3.resource_grid
f3 = subcarrier_frequencies(rg3.fft_size, rg3.subcarrier_spacing)
tp = CFG["three_path"]
gains = torch.tensor([a * np.exp(1j * p) for a, p in zip(tp["gains_abs"], tp["gains_phase_rad"])],
                     dtype=torch.complex64)
npth = len(gains)
a_cir = gains.view(1, 1, 1, 1, 1, npth, 1).expand(nb3, 1, 1, 1, 1, npth, rg3.num_ofdm_symbols).clone()
tau = (torch.tensor(tp["delays_ns"], dtype=torch.float64) * 1e-9).to(torch.float32).view(1, 1, 1, npth).expand(nb3, 1, 1, npth)
h3 = cir_to_ofdm_channel(f3, a_cir, tau, normalize=False).to(x3.dtype)
cp3_s = float(rg3.cyclic_prefix_length) / (rg3.fft_size * rg3.subcarrier_spacing)
for i, no in enumerate(CFG["three_path_noise_vars"]):
    y3 = ApplyOFDMChannel()(x3, h3, no)
    bh3, crc3 = rx3(y3, no)
    name = "three_path_ls" if i == 0 else f"three_path_ls_noise_var_{str(no).replace('.', 'p')}"
    rows.append({"test": name, "config": "30 kHz, 51 PRB, MCS 16 table 1, slot 0, freq domain",
                 "subcarrier_spacing_khz": float(rg3.subcarrier_spacing) / 1e3, "n_prb": CFG["pusch_20mhz"]["n_prb"],
                 "tb_bits": int(b3.shape[-1]), "noise_var": no, "max_path_delay_ns": max(tp["delays_ns"]),
                 "cp_duration_ns": cp3_s * 1e9, "n_blocks": int(crc3.numel()), "ber": ber_of(b3, bh3),
                 "crc_pass": int(crc3.sum()), "crc_total": int(crc3.numel())})

td_rows = []
for sn in CFG["time_domain_slots"]:
    c = pusch20(sn)
    txt_ = PUSCHTransmitter(c, output_domain="time")
    rxt_ = PUSCHReceiver(txt_, input_domain="time", l_min=0, return_tb_crc_status=True)
    xt, bt = txt_(CFG["time_domain_n_blocks"])
    bht, crct = rxt_(xt, NO0)
    rg = txt_.resource_grid
    fs = float(rg.fft_size) * float(rg.subcarrier_spacing)
    ns = int(xt.shape[-1])
    td_rows.append({"slot_number": sn, "subcarrier_spacing_khz": float(rg.subcarrier_spacing) / 1e3,
                    "n_prb": CFG["pusch_20mhz"]["n_prb"], "fft_size": int(rg.fft_size),
                    "sample_rate_msps": fs / 1e6, "cp_len": int(rg.cyclic_prefix_length), "n_samples": ns,
                    "duration_us": ns / fs * 1e6, "n_blocks": int(crct.numel()), "ber": ber_of(bt, bht),
                    "crc_pass": int(crct.sum()), "crc_total": int(crct.numel())})
LEDGER["nr_pusch"] = {"rows": rows, "time_domain": td_rows,
                      "note": "Sionna PUSCH wrappers use one cyclic-prefix length for all 14 symbols of a slot "
                              "(see quotes_verified sionna_carrier_single_cp_slot_rule)."}
checkpoint("nr_pusch", META)

# ==================================================================================================
# 3. native_bridge
# ==================================================================================================
print("section 3: native_bridge", flush=True)
BR = CFG["bridge"]
track(ROOT / "src" / "waveforms.py")
pcb = PUSCHConfig()
pcb.carrier.subcarrier_spacing = BR["scs_khz"]
pcb.carrier.n_size_grid = BR["n_prb"]
pcb.n_size_bwp = BR["n_prb"]
pcb.tb.mcs_index = BR["mcs_index"]
pcb.dmrs.additional_position = BR["dmrs_additional_position"]
txb = PUSCHTransmitter(pcb, output_domain="freq")
rxb = PUSCHReceiver(txb, return_tb_crc_status=True)
NB = BR["n_blocks"]
xb, bb = txb(NB)
nsc = int(xb.shape[-1])
FFT = BR["fft"]
scs_hz = BR["scs_khz"] * 1e3
fs_b = FFT * scs_hz
lte = SRC["lte_numerology"]
scale = FFT // lte["fft_at_30p72"]
cp_slot = [lte["cp_first_samples_at_30p72"] * scale] + [lte["cp_other_samples_at_30p72"] * scale] * (
    lte["symbols_per_slot_normal_cp"] - 1)
cp_pat = cp_slot * lte["slots_per_subframe"]
nsym = len(cp_pat)
lo = FFT // 2 - nsc // 2


def to_time(grid_row):
    gfull = np.zeros((nsym, FFT), complex)
    gfull[:, lo:lo + nsc] = grid_row
    return W.ofdm_modulate(gfull, FFT, cp_pat)


def from_time(sig, offset=0):
    out, p = [], offset
    for li in range(nsym):
        p += cp_pat[li]
        out.append(np.fft.fftshift(np.fft.fft(sig[p:p + FFT])) / np.sqrt(FFT))
        p += FFT
    return np.array(out)[:, lo:lo + nsc]


xbn = xb.numpy()
txs = np.stack([to_time(xbn[i, 0, 0]) for i in range(NB)])
rng = np.random.default_rng(CFG["numpy_seed"])
br_rows = []


def run_bridge(condition, sig, offset=0, no=NO0, extra=None):
    yg = np.stack([from_time(sig[i], offset) for i in range(NB)])[:, None, None]
    bh_, crc_ = rxb(torch.from_numpy(yg.astype(np.complex64)), float(no))
    r = {"condition": condition, "n_blocks": int(crc_.numel()), "ber": ber_of(bb, bh_),
         "crc_pass": int(crc_.sum()), "crc_total": int(crc_.numel())}
    if extra:
        r.update(extra)
    br_rows.append(r)


run_bridge("noise_free", txs)
run_bridge("fft_window_8_early", txs, offset=-BR["fft_window_early_samples"],
           extra={"window_offset_samples": -BR["fft_window_early_samples"], "shortest_cp_samples": min(cp_pat)})
d = BR["delay_samples"]
run_bridge("delay_300_samples", np.concatenate([np.zeros((NB, d)), txs[:, :-d]], axis=1),
           extra={"delay_samples": d, "longest_cp_samples": max(cp_pat)})
nidx = np.arange(txs.shape[1])
for eps in BR["cfo_fraction_of_scs"]:
    run_bridge("cfo_" + f"{eps:g}".replace(".", "p") + "_scs", txs * np.exp(2j * np.pi * eps * scs_hz * nidx / fs_b),
               extra={"cfo_fraction_of_scs": eps, "cfo_hz": eps * scs_hz})
ps = float(np.mean(np.abs(txs) ** 2))
snr_lin = 10 ** (BR["awgn_snr_db_per_sample"] / 10)
no_t = ps / snr_lin
noise = np.sqrt(no_t / 2) * (rng.standard_normal(txs.shape) + 1j * rng.standard_normal(txs.shape))
p_re = float(np.mean(np.abs(xbn) ** 2))
zero_re = xbn[:, 0, 0] == 0
zero_sym = np.nonzero(zero_re.any(axis=(0, 2)))[0]
run_bridge("awgn_10db_per_sample", txs + noise, no=no_t,
           extra={"snr_db_per_sample_target": BR["awgn_snr_db_per_sample"],
                  "computed_signal_power_per_sample": ps, "noise_var_per_sample": no_t,
                  "computed_noise_snr_db_per_sample": db(ps / float(np.mean(np.abs(noise) ** 2))),
                  "per_re_snr_db": db(p_re / no_t),
                  "per_re_grid_n_re": int(zero_re.size), "per_re_grid_n_zero_re": int(zero_re.sum()),
                  "per_re_grid_zero_re_only_on_dmrs_symbols": bool(
                      set(zero_sym.tolist()) <= {int(v) for v in pcb.dmrs_symbol_indices})})
LEDGER["native_bridge"] = {
    "n_prb": BR["n_prb"], "scs_khz": BR["scs_khz"], "n_subcarriers": nsc, "fft": FFT, "fs_msps": fs_b / 1e6,
    "cp_pattern": cp_pat, "n_samples": int(txs.shape[1]), "duration_ms": txs.shape[1] / fs_b * 1e3,
    "mcs_index": BR["mcs_index"], "dmrs_symbol_indices": [int(v) for v in pcb.dmrs_symbol_indices],
    "tb_bits": int(bb.shape[-1]),
    "occupied_fraction_of_fft_bins": nsc / FFT,
    "sync": "none (no timing or CFO estimation anywhere in this chain)",
    "rows": br_rows,
}
checkpoint("native_bridge", META)

# ==================================================================================================
# 4. wifi_shaped_grid
# ==================================================================================================
print("section 4: wifi_shaped_grid", flush=True)
from sionna.phy.ofdm import ResourceGrid, ResourceGridMapper, PilotPattern, LSChannelEstimator, LMMSEEqualizer  # noqa: E402,E501
from sionna.phy.mapping import Mapper, Demapper, BinarySource  # noqa: E402
from sionna.phy.mimo import StreamManagement  # noqa: E402
from sionna.phy.fec.ldpc import LDPC5GEncoder, LDPC5GDecoder  # noqa: E402

WG = CFG["wifi_grid"]
nsw, fftw = WG["n_ofdm_symbols"], WG["fft"]
g_l, g_r = WG["guard"]
half = (fftw - g_l - g_r - 1) // 2
eff = np.r_[np.arange(-half, 0), np.arange(1, half + 1)]
mask = np.zeros((1, 1, nsw, len(eff)), bool)
pil_cols = [int(np.where(eff == k)[0][0]) for k in WG["pilot_tone_indices"]]
mask[..., pil_cols] = True
pil_vals = np.tile(np.array(WG["pilot_values"], np.complex64), nsw)[None, None, :]
pp = PilotPattern(torch.from_numpy(mask), torch.from_numpy(pil_vals))
rgw = ResourceGrid(num_ofdm_symbols=nsw, fft_size=fftw, subcarrier_spacing=WG["scs_hz"],
                   cyclic_prefix_length=WG["cp_samples"], num_guard_carriers=tuple(WG["guard"]), dc_null=True,
                   pilot_pattern=pp)
smw = StreamManagement(np.ones([1, 1]), 1)
nd = int(rgw.num_data_symbols)
nbits = nd * 2
kinfo = nbits // 2
encw = LDPC5GEncoder(kinfo, nbits)
decw = LDPC5GDecoder(encw, hard_out=True)
NBW = WG["n_blocks"]
uw = BinarySource()([NBW, 1, 1, kinfo])  # draws from sionna config RNG seeded with config.torch_seed
xgw = ResourceGridMapper(rgw)(Mapper("qam", 2)(encw(uw)))
fw = subcarrier_frequencies(fftw, WG["scs_hz"])
cg = torch.tensor([a * np.exp(1j * p) for a, p in WG["channel_gains"]], dtype=torch.complex64)
npw = len(cg)
aw = cg.view(1, 1, 1, 1, 1, npw, 1).expand(NBW, 1, 1, 1, 1, npw, nsw).clone()
tauw = (torch.tensor(WG["channel_delays_ns"], dtype=torch.float64) * 1e-9).to(torch.float32).view(1, 1, 1, npw).expand(NBW, 1, 1, npw)
hw = cir_to_ofdm_channel(fw, aw, tauw).to(xgw.dtype)
w_rows = []
for no in WG["noise_vars"]:
    yw = ApplyOFDMChannel()(xgw, hw, no)
    hh, err = LSChannelEstimator(rgw, interpolation_type="nn")(yw, no)
    xh, ne = LMMSEEqualizer(rgw, smw)(yw, hh, err, no)
    uhw = decw(Demapper("app", "qam", 2)(xh, ne).reshape(NBW, 1, 1, nbits))
    w_rows.append({"noise_var": no, "n_blocks": NBW, "info_bits_per_block": kinfo,
                   "ber": float((uhw != uw).float().mean()),
                   "block_errors": int(((uhw != uw).any(dim=-1)).sum())})
LEDGER["wifi_shaped_grid"] = {
    "note": "Tone map only (64 FFT, guard 6/5, DC null, 4 pilot tones per symbol) on Sionna's generic ResourceGrid "
            "with LDPC5G coding. It is NOT an 802.11 PPDU: no L-STF/L-LTF/L-SIG, no 802.11 scrambler, BCC, "
            "interleaver, pilot polarity sequence or FCS.",
    "fft": fftw, "subcarrier_spacing_hz": WG["scs_hz"], "bandwidth_hz": float(rgw.bandwidth),
    "n_ofdm_symbols": nsw, "cp_samples": WG["cp_samples"], "cp_duration_ns": WG["cp_samples"] / (fftw * WG["scs_hz"]) * 1e9,
    "n_effective_subcarriers": int(rgw.num_effective_subcarriers),
    "n_data_tones_per_symbol": nd // nsw, "n_pilot_tones_per_symbol": int(rgw.num_pilot_symbols) // nsw,
    "num_data_re": nd, "num_pilot_re": int(rgw.num_pilot_symbols),
    "channel_max_delay_ns": max(WG["channel_delays_ns"]),
    "rows": w_rows,
}
checkpoint("wifi_shaped_grid", META)

# ==================================================================================================
# 5. legacy_generator (src/waveforms.py)
# ==================================================================================================
print("section 5: legacy_generator", flush=True)
wf_path = ROOT / "src" / "waveforms.py"
wtxt = wf_path.read_text(encoding="utf-8").lower()
fec_hits = [{"term": t, "hits": wtxt.count(t)} for t in CFG["fec_terms"]]

np_ = SRC["nr_pss_mseq"]
L127 = np_["length"]


def nr_pss_spec(n_id2: int) -> np.ndarray:
    init = np_["init_x6_to_x0"][::-1]           # x(0)..x(6)
    t1, t0 = np_["recursion_taps"]
    x = list(init)
    for i in range(L127 - len(init)):
        x.append((x[i + t1] + x[i + t0]) % 2)
    x = np.array(x)
    m = (np.arange(L127) + np_["shift_per_n_id2"] * n_id2) % L127
    return (1 - 2 * x[m]).astype(complex)


zc = SRC["lte_pss_zc"]


def lte_pss_spec(u: int) -> np.ndarray:
    nzc = zc["zc_length"]
    h1 = zc["n_tones"] // 2
    n1 = np.arange(h1)
    n2 = np.arange(h1, zc["n_tones"])
    return np.r_[np.exp(-1j * np.pi * u * n1 * (n1 + 1) / nzc), np.exp(-1j * np.pi * u * (n2 + 1) * (n2 + 2) / nzc)]


def ncorr(a, b) -> float:
    return float(abs(np.vdot(a, b)) / (np.linalg.norm(a) * np.linalg.norm(b)))


wn = W.nr_downlink(occupancy="G1")
cN = wn.fft // 2
pss_nr_gen = wn.grid[0, cN - L127 // 2:cN + L127 // 2 + 1]
nr_rows = [{"n_id2": k, "corr": ncorr(nr_pss_spec(k), pss_nr_gen)} for k in range(3)]
nr_spec_cross = max(ncorr(nr_pss_spec(i), nr_pss_spec(j)) for i in range(3) for j in range(3) if i != j)
wl = W.lte_downlink(occupancy="G1")
cL = wl.fft // 2
h62 = zc["n_tones"] // 2
pss_lte_gen = wl.grid[6, np.r_[np.arange(-h62, 0), np.arange(1, h62 + 1)] + cL]
roots = zc["roots_for_n_id2_0_1_2"]
lte_rows = [{"root": u, "n_id2": i, "corr": ncorr(lte_pss_spec(u), pss_lte_gen)} for i, u in enumerate(roots)]
lte_conj_check = ncorr(lte_pss_spec(roots[1]), np.conj(lte_pss_spec(roots[2])))
ww = W.wifi_80211ac(occupancy="G1")
stf_nz = np.nonzero(ww.grid[0])[0] - ww.fft // 2
q_stf = quote("waveforms_lstf_comment_multiples_of_four", wf_path, 274, "L-STF: 4의 배수 톤만")
q_pss_nr = quote("waveforms_nr_pss_gold_qpsk", wf_path, 428, "if \"PSS\" in on: put(0, ssb_sync, qpsk_from_gold(11 + n_id")
q_pss_note = quote("waveforms_nr_pss_approximation_note", wf_path, 416, "Gold-QPSK 로 근사한다")
q_pss_lte = quote("waveforms_lte_pss_gold_qpsk", wf_path, 361, "if \"PSS\" in on: put(6, cen, qpsk_from_gold(101")

f13 = {"fec_term_hits": fec_hits, "fec_term_hits_total": int(sum(r["hits"] for r in fec_hits)),
       "nr_pss_corr": nr_rows, "nr_pss_generator_call": "nr_downlink(occupancy='G1'), grid row 0, centre 127 tones",
       "nr_pss_spec_self_corr": ncorr(nr_pss_spec(0), nr_pss_spec(0)),
       "nr_pss_spec_max_cross_corr_between_n_id2": nr_spec_cross,
       "lte_pss_corr": lte_rows, "lte_pss_generator_call": "lte_downlink(occupancy='G1'), grid row 6, centre 62 tones without DC",
       "lte_pss_spec_check_root29_vs_conj_root34": lte_conj_check,
       "wifi_lstf_nonzero_tones": int(len(stf_nz)),
       "wifi_lstf_tone_index_residues_mod4": sorted(set((stf_nz % 4).tolist())),
       "wifi_lstf_comment_quote_ok": q_stf,
       "pss_source_quotes_ok": bool(q_pss_nr and q_pss_note and q_pss_lte)}

q373 = quote("waveforms_nr_prb_rule", wf_path, 373, "n_rb = 273 if bw_hz >= 100e6 else 51")
q316 = quote("waveforms_lte_rb_lookup", wf_path, 316, "n_rb = {20e6: 100, 10e6: 50, 5e6: 25}.get(bw_hz, 100)")
q267 = quote("waveforms_wifi_vht80_pilots", wf_path, 267, "PILOT_SC = np.array([-103, -75, -39, -11, 11, 39, 75, 103])")
fn = {"wifi": W.wifi_80211ac, "lte": W.lte_downlink, "nr": W.nr_downlink}
f15 = []
calls = CFG["legacy_f15_calls"]
for std in ("wifi", "lte", "nr"):
    for req in calls[std]:
        for prof in calls["profiles"]:
            row = {"standard": std, "profile": prof, "requested_mhz": req}
            try:
                w = fn[std](bw_hz=req * 1e6, occupancy=prof)
                cols = np.where(np.any(w.grid != 0, axis=0))[0]
                row.update({"outcome": "ok", "returned_occupied_mhz": w.bw_hz / 1e6,
                            "returned_tx_grid_span_mhz": float((cols.max() - cols.min() + 1) * w.scs_hz / 1e6),
                            "fs_msps": w.fs_hz / 1e6, "fft": int(w.fft), "duration_us": float(w.duration_us),
                            "error_message": None})
                row["returned_minus_requested_mhz"] = row["returned_occupied_mhz"] - req
            except Exception as e:  # noqa: BLE001 - recording the failure is the point
                row.update({"outcome": type(e).__name__, "returned_occupied_mhz": None,
                            "returned_tx_grid_span_mhz": None, "fs_msps": None, "fft": None, "duration_us": None,
                            "error_message": str(e)[:200], "returned_minus_requested_mhz": None})
            f15.append(row)
f15_nr_scs = []
for scs in (k * 1e3 for k in CFG["legacy_nr_scs_khz"]):
    w = W.nr_downlink(scs_hz=scs, occupancy="G3")
    f15_nr_scs.append({"scs_khz": scs / 1e3, "fs_msps": w.fs_hz / 1e6, "cp_first_two": [int(v) for v in w.cp_lens[:2]],
                       "duration_us": float(w.duration_us), "returned_occupied_mhz": w.bw_hz / 1e6})

f16 = []
wfs = {o: W.all_waveforms(o) for o in ("G1", "G2", "G3")}
for std in ("wifi", "lte", "nr"):
    g3 = wfs["G3"][std]
    for prof in ("G1", "G2"):
        w = wfs[prof][std]
        occ_db = db(w.occupancy_frac / g3.occupancy_frac)
        iq_db = db(np.mean(np.abs(w.tx) ** 2) / np.mean(np.abs(g3.tx) ** 2))
        re_db = db(np.sum(np.abs(w.grid) ** 2) / np.sum(np.abs(g3.grid) ** 2))
        f16.append({"standard": std, "profile": prof, "reference_profile": "G3",
                    "occupancy_ratio_db": occ_db, "iq_power_ratio_db": iq_db, "grid_energy_ratio_db": re_db,
                    "iq_minus_occupancy_db": iq_db - occ_db, "grid_energy_minus_iq_db": re_db - iq_db,
                    "same_tx_length_as_reference": bool(len(w.tx) == len(g3.tx))})

LEDGER["legacy_generator"] = {
    "file": "src/waveforms.py", "sha256": HASHED["repo:src/waveforms.py"],
    "f13": f13,
    "f15": {"rows": f15, "n_calls": len(f15), "n_raised": sum(r["outcome"] != "ok" for r in f15),
            "nr_prb_rule_quote_ok": q373, "lte_rb_lookup_quote_ok": q316, "wifi_pilot_positions_quote_ok": q267,
            "nr_scs_rows": f15_nr_scs},
    "f16": {"rows": f16, "max_abs_grid_energy_minus_iq_db": max(abs(r["grid_energy_minus_iq_db"]) for r in f16),
            "min_iq_minus_occupancy_db": min(r["iq_minus_occupancy_db"] for r in f16),
            "max_iq_minus_occupancy_db": max(r["iq_minus_occupancy_db"] for r in f16)},
}
checkpoint("legacy_generator", META)

# ==================================================================================================
# 6. installed_elsewhere
# ==================================================================================================
print("section 6: installed_elsewhere", flush=True)
IS = CFG["installed_search"]
dists = sorted({(d.metadata["Name"] or "") for d in _md.distributions()})
rx_d = re.compile(IS["dist_name_regex"])
dist_hits = [d for d in dists if rx_d.search(d)]
mod_hits = []
for m in IS["module_names"]:
    try:
        if importlib.util.find_spec(m) is not None:
            mod_hits.append(m)
    except (ImportError, ValueError):
        pass
exe_hits = {e: shutil.which(e) for e in IS["executables"] if shutil.which(e)}
try:
    ldc = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True, timeout=30).stdout
    lib_hits = sorted({ln.strip().split(" ")[0] for ln in ldc.splitlines() if re.search(IS["library_regex"], ln)})
    ldconfig_ok = True
except (OSError, subprocess.SubprocessError):
    lib_hits, ldconfig_ok = [], False
sys_site_hits = []
for sd in IS["system_site_dirs"]:
    p = Path(sd)
    if p.is_dir():
        sys_site_hits += [f"{sd}/{c.name}" for c in p.iterdir() if rx_d.search(c.name)]
dir_hits = [d for d in IS["install_dirs"] if Path(d).exists()]


def any_match(rx: str) -> bool:
    r = re.compile(rx)
    return any(r.search(s) for s in dist_hits + mod_hits + list(exe_hits) + lib_hits + sys_site_hits + dir_hits)


LEDGER["installed_elsewhere"] = {
    "ieee80211_impl": any_match(r"(?i)80211|wlan|wifi|commpy"),
    "lte_impl": any_match(r"(?i)\blte\b|srsran|srsenb|srsue|py3gpp|oai|openairinterface|pyltesim"),
    "uhd_python": ("uhd" in mod_hits) or any("uhd" in s.lower() for s in dist_hits + sys_site_hits),
    "gnuradio": any_match(r"(?i)gnuradio"),
    "matlab": any_match(r"(?i)matlab"),
    "octave": any_match(r"(?i)octave|oct2py"),
    "how_checked": "importlib.metadata distribution names matched against config.installed_search.dist_name_regex; "
                   "importlib.util.find_spec for config module_names; shutil.which for config executables; "
                   "'ldconfig -p' lines matched against library_regex; names in system dist-packages dirs; "
                   "existence of fixed install directories. Name based only (assumption a4).",
    "n_distributions_in_this_python": len(dists),
    "python_executable": sys.executable,
    "distribution_name_hits": dist_hits, "module_hits": mod_hits, "executable_hits": exe_hits,
    "shared_library_hits": lib_hits, "ldconfig_ran": ldconfig_ok, "system_site_hits": sys_site_hits,
    "install_dir_hits": dir_hits,
    "note": "Only generic building blocks are installed (Sionna PHY FEC/OFDM/NR PUSCH); the repo holds the "
            "stand-in generator src/waveforms.py described under legacy_generator.",
}
checkpoint("installed_elsewhere", META)

# ==================================================================================================
# 7. x410_rates
# ==================================================================================================
print("section 7: x410_rates", flush=True)
mcr = SRC["uhd_x410_mcr"]["master_clock_rates_mhz_200mhz_image"]
m245, m250 = Fraction(mcr[0]), Fraction(mcr[1])
x_rows = []
for r in CFG["x410_candidate_rates_msps"]:
    fr = Fraction(r)
    q245, q250 = m245 / fr, m250 / fr
    d245, d250 = q245.denominator == 1, q250.denominator == 1
    divisor = int(q245) if d245 else (int(q250) if d250 else None)
    x_rows.append({"rate_msps": float(fr), "divides_245p76": d245, "divides_250": d250, "divisor": divisor,
                   "divisor_master_clock_mhz": float(m245) if d245 else (float(m250) if d250 else None),
                   "ratio_245p76_over_rate": float(q245), "ratio_250_over_rate": float(q250)})
# Where the candidate rates come from (computed, for the reader).
origins = [
    {"rate_msps": 20.0, "origin": "802.11 20 MHz: FFT 64 x 312.5 kHz",
     "computed_msps": float(SRC["wifi_legacy_numerology"]["fft_20mhz"] / (Fraction(SRC["wifi_legacy_numerology"]["t_fft_us"]) * Fraction(1, 10**6)) / 10**6)},
    {"rate_msps": 40.0, "origin": "802.11 40 MHz: FFT 128 x 312.5 kHz",
     "computed_msps": float(2 * SRC["wifi_legacy_numerology"]["fft_20mhz"] / (Fraction(SRC["wifi_legacy_numerology"]["t_fft_us"]) * Fraction(1, 10**6)) / 10**6)},
    {"rate_msps": 25.0, "origin": "candidate Wi-Fi resampling target: 250 MHz master clock / 10",
     "computed_msps": float(m250 / 10)},
    {"rate_msps": 30.72, "origin": "LTE/NR 15 kHz, FFT 2048", "computed_msps": lte["fft_at_30p72"] * lte["scs_hz"] / 1e6},
    {"rate_msps": 61.44, "origin": "NR 30 kHz FFT 2048 or 15 kHz FFT 4096", "computed_msps": 2 * lte["fft_at_30p72"] * lte["scs_hz"] / 1e6},
    {"rate_msps": 122.88, "origin": "NR 30 kHz, FFT 4096 (repo legacy NR)", "computed_msps": float(wfs["G3"]["nr"].fs_hz) / 1e6},
    {"rate_msps": 80.0, "origin": "802.11 80 MHz (repo legacy Wi-Fi)", "computed_msps": float(wfs["G3"]["wifi"].fs_hz) / 1e6},
]
LEDGER["x410_rates"] = {"master_clock_source_id": "uhd_x410_mcr", "rows": x_rows, "rate_origins": origins,
                        "note": "Divisibility only; DDC/DUC decimation limits of the FPGA image were not checked "
                                "(assumption a5)."}
checkpoint("x410_rates", META)

# ==================================================================================================
# 8. slow_time_rates
# ==================================================================================================
print("section 8: slow_time_rates", flush=True)
from sionna.phy.nr import CarrierConfig  # noqa: E402

q_nsym = quote("sionna_carrier_symbols_per_slot", PHY / "nr" / "carrier_config.py", 179, "return 14")
q_spf = quote("sionna_carrier_slots_per_subframe", PHY / "nr" / "carrier_config.py", 190,
              "spacing_map = {15: 1, 30: 2, 60: 4, 120: 8, 240: 16, 480: 32, 960: 64}")
st_rows = []
wl_ = SRC["wifi_legacy_numerology"]
t_sym = (Fraction(wl_["t_fft_us"]) + Fraction(wl_["gi_us"])) * Fraction(1, 10**6)
st_rows.append({"standard": "wifi_legacy", "profile": "nonht_20mhz_gi_0p8us",
                "label": "802.11 legacy non-HT 20 MHz, GI 0.8 us",
                "subcarrier_spacing_hz": float(1 / (Fraction(wl_["t_fft_us"]) * Fraction(1, 10**6))),
                "symbol_duration_us": float(t_sym * 10**6), "symbol_rate_hz": float(1 / t_sym),
                "slot_duration_us": None, "one_rs_per_slot_rate_hz": None,
                "note": "no slot structure; pilots in every OFDM symbol; L-LTF once per PPDU (traffic dependent)"})
he = SRC["wifi_he_numerology"]
for gi in he["gi_us"]:
    t_sym = (Fraction(he["t_fft_us"]) + Fraction(gi)) * Fraction(1, 10**6)
    st_rows.append({"standard": "wifi_ax", "profile": "he_gi_" + gi.replace(".", "p") + "us",
                    "label": f"802.11ax HE, GI {gi} us",
                    "subcarrier_spacing_hz": float(1 / (Fraction(he["t_fft_us"]) * Fraction(1, 10**6))),
                    "symbol_duration_us": float(t_sym * 10**6), "symbol_rate_hz": float(1 / t_sym),
                    "slot_duration_us": None, "one_rs_per_slot_rate_hz": None,
                    "note": "no slot structure; pilots in every data symbol; HE-LTF once per PPDU (traffic dependent)"})
# LTE 15 kHz: slot length from spec constants, cross-checked against the repo generator subframe length.
fs30 = lte["fft_at_30p72"] * lte["scs_hz"]
slot_samples = sum(cp_slot) // scale + lte["symbols_per_slot_normal_cp"] * lte["fft_at_30p72"]
t_slot = Fraction(slot_samples, int(fs30))
lte_gen = wfs["G3"]["lte"]
st_rows.append({"standard": "lte", "profile": "15khz_normal_cp", "label": "LTE 15 kHz normal CP",
                "subcarrier_spacing_hz": float(lte["scs_hz"]),
                "symbol_duration_us": float(t_slot / lte["symbols_per_slot_normal_cp"] * 10**6),
                "symbol_rate_hz": float(lte["symbols_per_slot_normal_cp"] / t_slot),
                "slot_duration_us": float(t_slot * 10**6), "one_rs_per_slot_rate_hz": float(1 / t_slot),
                "repo_generator_subframe_us": float(lte_gen.duration_us),
                "repo_generator_symbols_per_subframe": int(lte_gen.grid.shape[0]),
                "note": "CRS port 0 actually occupies 2 symbols per slot; 'one per slot' is the uniform-sampling view"})
for scs_k in CFG["slow_time_nr_scs_khz"]:
    cc = CarrierConfig(subcarrier_spacing=scs_k)
    n_sym = int(cc.num_symbols_per_slot)
    n_slot_sf = int(cc.num_slots_per_subframe)
    t_sf = Fraction(str(cc.sub_frame_duration))
    t_sl = t_sf / n_slot_sf
    st_rows.append({"standard": "nr", "profile": f"{scs_k}khz_normal_cp", "mu": int(cc.mu),
                    "label": f"NR {scs_k} kHz normal CP (mu={int(cc.mu)})",
                    "subcarrier_spacing_hz": scs_k * 1e3, "symbols_per_slot": n_sym, "slots_per_subframe": n_slot_sf,
                    "symbol_duration_us": float(t_sl / n_sym * 10**6), "symbol_rate_hz": float(n_sym / t_sl),
                    "slot_duration_us": float(t_sl * 10**6), "one_rs_per_slot_rate_hz": float(1 / t_sl),
                    "note": "numerology read from sionna.phy.nr.CarrierConfig"})
LEDGER["slow_time_rates"] = {"rows": st_rows, "sionna_numerology_quotes_ok": bool(q_nsym and q_spf),
                             "note": "Numerology-limited upper rates; the reference signal actually used for sensing "
                                     "(SSB, CRS, PRS, DMRS, LTF) repeats at its own configured period, which may be "
                                     "much lower."}
checkpoint("slow_time_rates", META)

check_unique("sionna_phy_inventory.sync_cfo_grep_hit_lines", LEDGER["sionna_phy_inventory"]["sync_cfo_grep_hit_lines"], ["path", "line"])
check_unique("sionna_phy_inventory.sync_cfo_hit_classification",
             LEDGER["sionna_phy_inventory"]["sync_cfo_hit_classification"], ["file_line"])
check_unique("nr_pusch.rows", LEDGER["nr_pusch"]["rows"], ["test"])
check_unique("nr_pusch.time_domain", LEDGER["nr_pusch"]["time_domain"], ["slot_number"])
check_unique("native_bridge.rows", LEDGER["native_bridge"]["rows"], ["condition"])
check_unique("wifi_shaped_grid.rows", LEDGER["wifi_shaped_grid"]["rows"], ["noise_var"])
check_unique("legacy_generator.f13.fec_term_hits", f13["fec_term_hits"], ["term"])
check_unique("legacy_generator.f13.nr_pss_corr", f13["nr_pss_corr"], ["n_id2"])
check_unique("legacy_generator.f13.lte_pss_corr", f13["lte_pss_corr"], ["root"])
check_unique("legacy_generator.f15.rows", f15, ["standard", "profile", "requested_mhz"])
check_unique("legacy_generator.f15.nr_scs_rows", f15_nr_scs, ["scs_khz"])
check_unique("legacy_generator.f16.rows", f16, ["standard", "profile"])
check_unique("x410_rates.rows", x_rows, ["rate_msps"])
check_unique("x410_rates.rate_origins", origins, ["rate_msps"])
check_unique("slow_time_rates.rows", st_rows, ["standard", "profile"])
check_unique("sources", SOURCES, ["id"])
check_unique("_meta.quotes_verified", QUOTES, ["id"])
META["all_selector_checks_pass"] = all(c["all_rows_have_keys"] and c["unique"] and c["selector_safe_values"]
                                       for c in UNIQUE_CHECKS)
checkpoint(None, META, final=True)
print(f"done in {time.time() - T0:.1f} s", flush=True)
