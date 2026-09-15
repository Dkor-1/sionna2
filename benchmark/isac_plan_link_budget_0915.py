"""isac_plan_link_budget_0915.py - X410 hardware facts and first-order link budget ledger.

Purpose
    Build the ledger outputs/isac_plan_link_budget_0915.json for the ISAC detection+tracking plan
    notebook. It collects the USRP X410 / USRP-2921 specification facts, the AMD DS926 RF-ADC noise
    figures and published drone RCS values (other groups' measurements) in ONE SOURCES table, and
    computes from them a first-order link budget for a quasi-monostatic drone detector:
    detection thresholds, a worked radar-equation example, maximum-range and SNR-vs-range grids,
    range factors, Doppler walk, TX-to-RX isolation needs (ADC linearity and TX broadband noise),
    phase-noise spreading of the leakage, blade-tip Doppler sampling needs, and intra-symbol Doppler.
    Repo facts (propeller geometry, rpm, tip-Doppler code, report07 meta) are read from the repo and
    every quoted line is checked at run time.

Run
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/isac_plan_link_budget_0915.py
    Optional: --root <repo root> (default: parent of this script's directory)
              --out <ledger path> (default: <root>/outputs/isac_plan_link_budget_0915.json)
              --core <cpu index> (default: lowest core in the current affinity)

Runtime
    About 0.06 s for main() (_meta.wall_time_s) and about 0.7 s for the whole process including imports,
    on one CPU core (closed-form arithmetic, no simulation, no GPU).

Scope
    These are simulation / code / bookkeeping checks: closed-form link-budget arithmetic on
    published specification values and literature constants. There is no comparison against RF
    measurements; no radio was operated. Published RCS values are other groups' measurements and
    are used only as a bracket for the sigma grid. Every assumption is listed in _meta.assumptions.
"""
from __future__ import annotations

import argparse
import math
import os
import sys


def _early_args():
    ap = argparse.ArgumentParser(description="X410 facts and first-order link budget ledger")
    ap.add_argument("--root", default=None, help="repo root (default: parent of the script dir)")
    ap.add_argument("--out", default=None, help="ledger path (default: ROOT/outputs/<name>.json)")
    ap.add_argument("--core", type=int, default=None, help="single CPU core to pin to")
    return ap.parse_args()


ARGS = _early_args()
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["SIONNA2_ALLOW_CPU"] = "1"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"
_CORE = ARGS.core if ARGS.core is not None else min(os.sched_getaffinity(0))
os.sched_setaffinity(0, {_CORE})

import ast  # noqa: E402
import datetime as _dt  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import scipy  # noqa: E402
from scipy import constants as sc  # noqa: E402
from scipy.optimize import brentq  # noqa: E402
from scipy.stats import chi2, ncx2  # noqa: E402

NAME = "isac_plan_link_budget_0915"
SCRIPT = Path(__file__).resolve()
ROOT = Path(ARGS.root).resolve() if ARGS.root else SCRIPT.parents[1]
OUT = Path(ARGS.out).resolve() if ARGS.out else ROOT / "outputs" / f"{NAME}.json"
RUN_COMMAND = f'CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/{NAME}.py'

# ---------------------------------------------------------------------------------------------
# Configuration inputs (grids, sizes). No random numbers are drawn anywhere in this script.
# ---------------------------------------------------------------------------------------------
SEEDS: dict = {}
FC_GHZ = (2.45, 3.5, 5.8)
G_DBI = (6, 12, 18)
T_MS = (10, 100)
SIGMA_DBSM = (-25, -20, -15)
BANDWIDTH_HZ = 20e6
PFA = 1e-6
PD = 0.9
SNR_RANGE_FC_GHZ = 3.5
SNR_RANGE_G_DBI = (12, 18)
SNR_RANGE_T_MS = 100
SNR_RANGE_SIGMA = -20
SNR_RANGE_LOG_POINTS = 31               # log grid 10..1000 m
SNR_RANGE_ANCHORS_M = (15, 25, 50, 200, 300, 500)
WORKED = dict(fc_ghz=3.5, g_dbi=12, sigma_dbsm=-20, t_ms=100, r_m=100.0)
ACCEL_MPS2 = (1, 2, 5)
PN_ISOLATION_DB = (30, 40, 50, 60)
TIP_EL_DEG = (0.0, -15.0)
LEAK_ECHO_R_M = (15, 50, 100, 200, 500)
LEAK_ECHO_ISOLATION_DB = 50
NOISE_SCOPE_RANGE_M = 500.0
EXTRA_LOSS_DB = (0, 3, 6)
STREAM_RATES_HZ = (30.72e6, 25e6)
STREAM_CHANNELS = 4
STREAM_BYTES_PER_SAMPLE = 4             # sc16 complex: 2 x 16 bit
DRONE_KEY = "matrice4e"

# ---------------------------------------------------------------------------------------------
# ASSUMPTIONS - every assumed constant; 'flag' says whether any document supports it.
# ---------------------------------------------------------------------------------------------
ASSUMPTIONS = [
    dict(id="loss_db", value=3.0, unit="dB", flag="assumed",
         note="Total system loss L in the radar equation. Does not include the RF cable run that an "
              "outdoor setup needs (both radios are rated indoor use only); that cable loss is unknown."),
    dict(id="bandwidth_hz", value=BANDWIDTH_HZ, unit="Hz", flag="configuration",
         note="Receiver noise bandwidth and range-bin size basis."),
    dict(id="nonfluctuating_threshold_db", value=13.0, unit="dB", flag="configuration",
         note=f"Planning threshold, the rounded Albersheim value for Pd {PD:g} / Pfa {PFA:g} / one look "
              "(the exact computed values are in constants.thresholds; the rounding is checked in "
              "constants.thresholds.albersheim_rounds_to_planning_threshold)."),
    dict(id="ofdm_papr_db", value=11.0, unit="dB", flag="assumed_unverified",
         note="OFDM peak-to-average power ratio used only for OFDM cases. Subtracted from the ADC "
              "full scale as in the earlier calculation; the {crest:.2f} dB crest factor (10*log10(2)) of the "
              "full-scale sine that defines dBFS is ignored, so this is conservative by up to {crest:.2f} dB."
              .format(crest=10.0 * math.log10(2.0))),
    dict(id="adc_noise_margin_db", value=6.0, unit="dB", flag="assumed",
         note="RX gain set so thermal noise sits this far above the ADC noise in band; the resulting "
              "noise-figure degradation is computed (constants.nf_degradation_db_at_margin)."),
    dict(id="tx_noise_margin_db", value=6.0, unit="dB", flag="assumed",
         note="Leaked TX broadband noise kept this far below the RX thermal density."),
    dict(id="tx_noise_gain_scaling", value="dB-for-dB with TX gain", unit="rule", flag="assumed_unverified",
         note="X410 Table 8 gives -146 dBm/Hz at the TX gain that yields 0 dBm for a 0 dBFS baseband "
              "signal. The density is assumed to rise dB-for-dB with gain. For a 0 dBFS CW tone at "
              "maximum output the offset is the CW output power; for an OFDM average of +5 dBm the "
              "gain must yield (5 + PAPR) dBm for a 0 dBFS tone, so the offset is 5 + PAPR. No NI "
              "document states this scaling."),
    dict(id="phase_noise_fc_scaling", value="20*log10(fc / 1 GHz)", unit="rule", flag="assumed_unverified",
         note="X410 Table 7 phase noise is given at a 1 GHz carrier only; the ZBX uses 1-2 GHz IFs, "
              "so the true scaling is not documented."),
    dict(id="rx_lo_independent_db", value=3.0, unit="dB", flag="assumed_unverified",
         note="RX LO phase noise assumed independent of and equal to TX phase noise (+3 dB). Whether "
              "TX and RX of one ZBX channel share a synthesizer could not be confirmed."),
    dict(id="leakage_delay", value="near-zero delay (range bin 0)", unit="rule", flag="assumed",
         note="Quasi-monostatic antennas a short distance apart put the direct leakage at near-zero "
              "delay; the phase-noise rows apply to that bin only."),
    dict(id="ds926_applicability", value="ZU2xDR Table 1 applies to the X410 XCZU28DR", unit="rule",
         flag="assumed_unverified",
         note="DS926 Table 1 test conditions (2 GS/s external clock, -1 dBFS input, Tj 40 C) differ from "
              "the X410 (ZBX manual: ADC runs at approx. 3 GHz, IF 1-2 GHz; clocking inside the X410 "
              "not documented)."),
    dict(id="ds926_nsd_main_point", value="FIN = 1.9 GHz typical", unit="rule", flag="assumed",
         note="Main NSD for the ds926_nsd rows is the typical value at FIN 1.9 GHz (inside the 1-2 GHz "
              "ZBX IF); rows also carry the bracket from that value to the -35 dBFS noise-floor value."),
    dict(id="full_duty_coherent_integration", value="SNR gain = B*T", unit="rule", flag="assumed",
         note="Full-duty waveform, matched filtering and coherent integration over T with no Doppler "
              "walk, range migration or straddle loss (doppler_walk_rows shows when this breaks)."),
    dict(id="monostatic_equal_gains", value="Gt = Gr = G", unit="rule", flag="configuration",
         note="Quasi-monostatic geometry, same antenna gain on TX and RX."),
    dict(id="body_speed_fully_radial", value="f_body = 2 v / lambda", unit="rule", flag="assumed",
         note="Worst case: the whole body speed is radial."),
    dict(id="sigma_bracket", value=list(SIGMA_DBSM), unit="dBsm", flag="configuration",
         note="Bracket chosen to span the published other-group measurements listed in sources; no "
              "in-band (2.45 / 3.5 GHz) aspect-averaged total RCS of a quadcopter was found. This repo's "
              "simulated levels are not used as RCS."),
    dict(id="reference_channel_equal_lo_noise", value="sigma_TX = sigma_RXA = sigma_RXB", unit="rule",
         flag="assumed_unverified",
         note="Used only for the coupled-reference-channel residual; independent LOs of equal noise."),
]

# ---------------------------------------------------------------------------------------------
# SOURCES - external specification / literature values. Every literal external number lives here.
# ---------------------------------------------------------------------------------------------
X410_URL = "https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8895/Ettus-USRPX410-Datasheet.pdf"
X410_DOC = "NI Ettus USRP X410 Specifications 378493G-01 (PDF dated 2026-03-11)"
UHD_URL = "https://files.ettus.com/manual/page_usrp_x4xx.html"
UHD_DOC = "UHD manual, USRP X4x0 series page"
ZBX_URL = "https://files.ettus.com/manual/page_zbx.html"
ZBX_DOC = "UHD manual, ZBX daughterboard page"
PROD_URL = "https://www.ettus.com/all-products/usrp-x410/"
PROD_DOC = "Ettus Research USRP X410 product page"
U2921_URL = "https://download.ni.com/support/manuals/375867d.pdf"
U2921_DOC = "NI USRP-2921 Specifications 375867D"
DS926_URL = "https://docs.amd.com/r/en-US/ds926-zynq-ultrascale-plus-rfsoc/RF-ADC-Performance-Characteristics"
DS926_DOC = "AMD DS926 Zynq UltraScale+ RFSoC data sheet, RF-ADC Performance Characteristics"
PATEL_URL = "http://eprints.gla.ac.uk/164563/7/164563.pdf"
PATEL_DOC = ("Patel, Fioranelli, Anderson (2018) Review of radar classification and RCS characterisation "
             "techniques for small UAVs or drones, IET Radar Sonar Navig. 12(9) 911-919, author accepted version")
RAHMAN_URL = ("https://research-repository.st-andrews.ac.uk/bitstream/handle/10023/16589/"
              "IET_RSN_RCS_author_accepted_version.pdf")
RAHMAN_DOC = "Rahman & Robertson (2019) In-flight RCS measurements of drones and birds at K-band and W-band, author accepted version"
LILING_URL = "https://users.ece.utexas.edu/~ling/SmallDroneISAR_Li_Ling.pdf"
LILING_DOC = "C. J. Li and H. Ling, Radar Signatures of Small Consumer Drones (slides, UT Austin)"
MERAKI_URL = "https://documentation.meraki.com/MR/Wi-Fi_Basics_and_Best_Practices/Wi-Fi_6_(802.11ax)_Technical_Guide"
MERAKI_DOC = "Cisco Meraki Documentation, Wi-Fi 6 (802.11ax) Technical Guide"
KEYSIGHT_GI_URL = "https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/wlan-mimo/content/mimo_fmt_grdintparams.htm"
KEYSIGHT_GI_DOC = "Keysight 89600 VSA help, Guard Interval (802.11n/ac/ax/be/bn)"

SOURCES = [
    # ---- USRP X410 --------------------------------------------------------------------------
    dict(id="x410_frequency_range", value={"min_hz": 1e6, "max_hz": 7.2e9, "tunable_max_hz": 8e9}, unit="Hz",
         url=X410_URL, doc=X410_DOC, locator="Table 2 Key Specifications (p.5); Table 6 and Table 9",
         note="'1 MHz to 7.2 GHz, tunable up to 8 GHz'; above 7.2 GHz power, EVM, noise density and NF may degrade (footnote 7)."),
    dict(id="x410_channels", value={"tx": 4, "rx": 4}, unit="count", url=X410_URL, doc=X410_DOC,
         locator="Table 2 (p.5): '4 TX, 4 RX, independently tunable'; 'Superheterodyne architecture'; Table 6 (p.8) and "
                 "Table 9 (p.10) 'Number of channels 4'",
         note="The front panel artwork (Figure 1, p.4) labels each of DB 0 and DB 1 '2-Channel RF Transceiver'. Channel "
              "count only; channel-to-channel isolation is not specified (see not_computed)."),
    dict(id="x410_max_bandwidth", value=400e6, unit="Hz", url=X410_URL, doc=X410_DOC,
         locator="Table 2 (p.5) 'Up to 400 MHz bandwidth per channel'; Table 8 (p.9, TX) and Table 16 (p.12, RX) "
                 "'Maximum instantaneous real-time bandwidth 400 MHz'",
         note="Per channel. Whether the full 400 MHz can be streamed to a host depends on the FPGA image and "
              "interface (uhd_x410_master_clock_rates, x410_qsfp28)."),
    dict(id="x410_converter_bits", value={"adc_bits": 12, "dac_bits": 14}, unit="bit", url=X410_URL, doc=X410_DOC,
         locator="Table 5 Baseband (p.8)", note="Converter sample rate is not stated in the NI spec."),
    dict(id="x410_max_iq_rate", value=[491.52e6, 500e6], unit="S/s", url=X410_URL, doc=X410_DOC,
         locator="Table 5 (p.8), footnote 6", note="Applicable maximum depends on the sample rate selected in software."),
    dict(id="x410_fpga", value="Xilinx RFSoC XCZU28DR Speed Grade -1", unit="text", url=X410_URL, doc=X410_DOC,
         locator="Table 4 Programmable Logic (p.7)", note="Basis for using the DS926 ZU2xDR RF-ADC table."),
    dict(id="x410_tx_max_output_power_table", value=23.0, unit="dBm (upper bound, '<23 dBm')", url=X410_URL,
         doc=X410_DOC, locator="Table 6 Transmitter (p.9), footnote 8",
         note="Stated as '<23 dBm'; 'Maximum output power varies by frequency'."),
    dict(id="x410_fig3_cw_max_output", value=[{"fc_ghz": 2.45, "dbm": 22.4}, {"fc_ghz": 3.5, "dbm": 22.4},
                                              {"fc_ghz": 5.8, "dbm": 19.1}],
         unit="dBm", reading_uncertainty_db=0.5, url=X410_URL, doc=X410_DOC,
         locator="Figure 3 'TX Maximum Output Power: 0 dBFS CW, Maximum Gain Setting' (p.10), digitised from a rendered page",
         note="Mean of 16 channels on 4 units. Reading uncertainty about +/-0.5 dB at 2.45 and 3.5 GHz. 5.8 GHz sits "
              "just above a curve discontinuity, so its reading uncertainty is larger and not quantified."),
    dict(id="x410_fig3_level_at_5p7ghz", value=16.7, unit="dBm", url=X410_URL, doc=X410_DOC,
         locator="Figure 3 (p.10), level just below the discontinuity near 5.7 GHz, read by eye",
         note="Used only as a knob-shake for the 5.8 GHz CW power (range_factors.pt_reading_rows)."),
    dict(id="x410_fig2_evm_floor_channel_power", value=5.0, unit="dBm", url=X410_URL, doc=X410_DOC,
         locator="Figure 2 'TX EVM Bathtub Curves: 5GNR, UL, FDD, SISO, 100 MHz BW, 30 kHz SCS, 256 QAM' (p.9-10), read by eye",
         note="EVM stays at its floor up to about +5 dBm channel power and degrades above about +7 dBm; used as the "
              "linear OFDM average power case 'ofdm_plus5dbm'."),
    dict(id="x410_tx_phase_noise_1ghz", value=[{"offset_hz": 1e3, "dbc_per_hz": -91.0},
                                               {"offset_hz": 1e4, "dbc_per_hz": -101.0},
                                               {"offset_hz": 1e5, "dbc_per_hz": -103.0}],
         unit="dBc/Hz", url=X410_URL, doc=X410_DOC, locator="Table 7 TX Phase Noise, 1 GHz Carrier Frequency (p.9)",
         note="Nominal, 23 C. Nothing is specified beyond 100 kHz offset or at other carriers."),
    dict(id="x410_tx_noise_density", value=-146.0, unit="dBm/Hz", url=X410_URL, doc=X410_DOC,
         locator="Table 8 Bandwidth and Noise Density (p.9), footnote 11",
         note="'Measured at the TX gain setting required to reach 0 dBm output power with 0 dBFS baseband signal.'"),
    dict(id="x410_rx_noise_figure", value=[{"band_lo_ghz": 0.5, "band_hi_ghz": 3.1, "nf_db": 8.0},
                                           {"band_lo_ghz": 3.1, "band_hi_ghz": 6.0, "nf_db": 6.5},
                                           {"band_lo_ghz": 6.0, "band_hi_ghz": 8.0, "nf_db": 9.0}],
         unit="dB", url=X410_URL, doc=X410_DOC, locator="Table 15 Noise Figure (p.11); Definitions and Conditions (p.4)",
         note="Table 15 lists '500 MHz to 3.1 GHz 8 dB', '3.1 GHz to 6 GHz 6.5 dB', '6 GHz to 8 GHz 9 dB' with no "
              "typical/nominal qualifier, so by the document's Definitions ('Specifications are Characteristics unless "
              "otherwise noted') it is a characteristic not covered by the warranty, valid at '23 °C ± 5 °C'. The band "
              "edges 3.1 and 6 GHz appear in two rows; nf_db() assigns an edge frequency to the upper band."),
    dict(id="x410_rx_max_operating_input", value=0.0, unit="dBm", url=X410_URL, doc=X410_DOC,
         locator="Table 13 Maximum Operating Power (p.11), footnote 12",
         note="Maximum input at the RF port that does not saturate the ADC (with suitable gain)."),
    dict(id="x410_rx_damage_level", value=[{"band": "<=3 GHz", "dbm": 14.0}, {"band": ">3 GHz", "dbm": 17.0}],
         unit="dBm continuous", url=X410_URL, doc=X410_DOC, locator="Table 12 Maximum Input Power, Damage Level (p.11)",
         note=">3 GHz also '+20 dBm for up to 5 minutes'."),
    dict(id="x410_rx_iip3", value=12.0, unit="dBm", url=X410_URL, doc=X410_DOC, locator="Table 16 (p.12)",
         note="Specified at the '0 dBm input, full scale' (low gain) setting; lower at higher gain."),
    dict(id="x410_rx_gain_range", value=60.0, unit="dB", url=X410_URL, doc=X410_DOC, locator="Table 10 (p.10-11), >500 MHz",
         note="'>500 MHz 60 dB, nominal' ('<=500 MHz 38 dB, nominal'). Table note as printed: 'The gain range is the "
              "received signal amplitude resulting from the gain setting varies over the frequency band and among "
              "devices.' Listed for context; not used in the arithmetic."),
    dict(id="x410_fig5_fs_input_30db_gain", value=[{"fc_ghz": 2.45, "dbm": -18.5}, {"fc_ghz": 3.5, "dbm": -15.0},
                                                   {"fc_ghz": 5.8, "dbm": -13.5}],
         unit="dBm", url=X410_URL, doc=X410_DOC,
         locator="Figure 5 'RX Input Power to Reach 0 dBFS: CW Input, 30 dB Gain Setting' (p.12), read by eye",
         note="Used only for the input-referred ADC-noise cross-check."),
    dict(id="x410_front_panel_label", value="TX OUTPUT MAX +15 dBm, RX INPUT MAX +20 dBm", unit="text",
         url=X410_URL, doc=X410_DOC, locator="Figure 1 Front Panel artwork (p.4)",
         note="Conflicts on its face with Table 6 ('<23 dBm'), Figure 3 and Table 12/13; the meaning of the label "
              "could not be resolved."),
    dict(id="x410_synchronization", value=["REF IN", "PPS IN", "TRIG IN/OUT", "GPSDO", "OCXO"], unit="text",
         url=X410_URL, doc=X410_DOC, locator="Table 2 Synchronization (p.5-6); Table 17 (p.13)",
         note="OCXO 2.5 ppm unlocked, 5 ppb GPS-locked. No reference output is listed."),
    dict(id="x410_environment", value={"operating_temp_c": [0, 55], "indoor_use_only": True}, unit="C",
         url=X410_URL, doc=X410_DOC, locator="Table 22 Environmental Characteristics (p.15): 'Indoor use only.'",
         note="Outdoor use needs a sheltered radio cabled to the antennas; the cable loss is not in loss_db."),
    dict(id="x410_qsfp28", value="2 QSFP28 (10/100 GbE, Aurora)", unit="text", url=X410_URL, doc=X410_DOC,
         locator="Table 2 Digital interfaces (p.6); Table 4 (p.7)",
         note="UHD manual: X4_200 image uses '4x 10 GbE (All Lanes)' on QSFP28 port 0 (port 1 unused); "
              "CG_400 uses 100 GbE on both ports (" + UHD_URL + ")."),
    dict(id="uhd_x410_master_clock_rates",
         value=[{"image": "200 MHz", "mcr_hz": 245.76e6}, {"image": "200 MHz", "mcr_hz": 250e6},
                {"image": "400 MHz", "mcr_hz": 491.52e6}, {"image": "400 MHz", "mcr_hz": 500e6}],
         unit="Hz", url=UHD_URL, doc=UHD_DOC, locator="Section on master clock rates",
         note="'The 200 MHz images allow master clock rates of 245.76 MHz or 250 MHz. The 400 MHz images allow master "
              "clock rates of 491.52 MHz or 500 MHz.' Also: 'Timed tuning is not supported on X410/X440'."),
    dict(id="uhd_x410_loopback_attenuation", value=30.0, unit="dB (minimum)", url=UHD_URL, doc=UHD_DOC,
         locator="Caution box", note="'X410: Always use at least 30dB attenuation if operating in loopback configuration.'"),
    dict(id="uhd_x410_trig_in_out", value="not supported in default FPGA images", unit="text", url=UHD_URL, doc=UHD_DOC,
         locator="Front/rear panel description", note="'The TRIG IN/OUT port is not supported in default FPGA images.'"),
    dict(id="uhd_x410_rj45_streaming", value=10e6, unit="S/s (approx.)", url=UHD_URL, doc=UHD_DOC,
         locator="Rear panel description",
         note="'It is also possible to stream data over this interface, albeit at a slow rate (approx. 10 Msps).' "
              "CONFLICTS with x410_product_page_rj45."),
    dict(id="x410_product_page_rj45", value="does not support IQ streaming", unit="text", url=PROD_URL, doc=PROD_DOC,
         locator="Specifications / interfaces text",
         note="'The RJ45 port is used for remote management of the device and does not support IQ streaming.' "
              "CONFLICTS with uhd_x410_rj45_streaming."),
    dict(id="x410_product_page_phase_coherence", value="multi-radio phase-aligned operation not supported", unit="text",
         url=PROD_URL, doc=PROD_DOC, locator="Specifications text",
         note="'Multi-Radio phase-aligned and phase-coherent operations are not supported, as RF chain LO import and "
              "export functionality is not supported on the USRP X410.'"),
    dict(id="zbx_lo_per_channel", value="LMX2572 per synthesizer; LOs intentionally at different frequencies", unit="text",
         url=ZBX_URL, doc=ZBX_DOC, locator="LO section",
         note="'All LO synthesizers are identical (LMX2572).' 'When programming the two channels to the same frequency, "
              "the LOs will thus intentionally run at different frequencies.'"),
    dict(id="zbx_if_and_adc_rate", value={"if_lo_hz": 1e9, "if_hi_hz": 2e9, "adc_rate_approx_hz": 3e9}, unit="Hz",
         url=ZBX_URL, doc=ZBX_DOC, locator="Signal path description",
         note="Second LO 'moves the IF to a value between 1 and 2 GHz. The USRP ADC/DAC (running at a sampling rate of "
              "approx. 3 GHz) will sample the IF directly.'"),
    dict(id="zbx_cal_loopback", value="CAL_LOOPBACK and TERMINATION antenna settings", unit="text", url=ZBX_URL,
         doc=ZBX_DOC, locator="Antenna settings",
         note="CAL_LOOPBACK: 'loop back the Tx path into the Rx path (this is sometimes required for calibration "
              "purposes)'; TERMINATION (Rx only): 'terminate the Rx path'."),
    dict(id="ni_channel_phase_not_fixed", value="channel-to-channel phase not guaranteed per initialization", unit="text",
         url="https://www.mail-archive.com/usrp-users@lists.ettus.com/msg14585.html",
         doc="usrp-users mailing list, Haydn Nelson (NI), 2022-05-16, 'Re: Does X410 support phase-aligned and phase-corent?'",
         locator="message body",
         note="'The USRP X410 doesn't have that LO sharing capability built in'; a shared 10 MHz reference "
              "'doesn't guarantee a fixed phase difference channel to channel on each initialization'."),
    # ---- USRP-2921 ---------------------------------------------------------------------------
    dict(id="u2921_bands", value=[{"lo_ghz": 2.4, "hi_ghz": 2.5}, {"lo_ghz": 4.9, "hi_ghz": 5.9}], unit="GHz",
         url=U2921_URL, doc=U2921_DOC, locator="Transmitter and Receiver 'Frequency range' (p.1-2)",
         note="Does not cover 3.5 GHz."),
    dict(id="u2921_half_duplex", value="half-duplex", unit="text", url=U2921_URL, doc=U2921_DOC,
         locator="'Half-Duplex Device' section (p.3)",
         note="'The USRP-2921 is a half-duplex device. The USRP-2921 cannot transmit and receive signals at the same time.'"),
    dict(id="u2921_tx_power", value={"min_dbm": 17.0, "max_dbm": 20.0}, unit="dBm", url=U2921_URL, doc=U2921_DOC,
         locator="Transmitter 'Maximum output power (Pout)' (p.2)", note="50 mW to 100 mW in both bands."),
    dict(id="u2921_noise_figure", value={"min_db": 5.0, "max_db": 7.0}, unit="dB", url=U2921_URL, doc=U2921_DOC,
         locator="Receiver 'Noise figure' (p.3); Definitions and Conditions (p.1)",
         note="'Noise figure 5 dB to 7 dB', no frequency breakdown across the two bands. Definitions: 'Specifications "
              "are Characteristics unless otherwise noted' (not covered by the warranty); Conditions: 'Specifications "
              "are valid at 25 °C unless otherwise noted'."),
    dict(id="u2921_max_iq_rate", value=[{"sample_width_bit": 16, "rate_sps": 25e6, "rx_rt_bandwidth_hz": 19e6},
                                        {"sample_width_bit": 8, "rate_sps": 50e6, "rx_rt_bandwidth_hz": 36e6}],
         unit="S/s", url=U2921_URL, doc=U2921_DOC, locator="Receiver 'Maximum I/Q sample rate' and 'Maximum instantaneous real-time bandwidth' (p.3)",
         note="ADC 2 channels, 100 MS/s, 14 bit; RX maximum input -15 dBm."),
    dict(id="u2921_environment", value={"operating_temp_c": "23 +/- 5", "indoor_use_only": True}, unit="C",
         url=U2921_URL, doc=U2921_DOC, locator="Environment / Operating Environment (p.4)",
         note="'Indoor use only.'; 'Operating temperature 23 °C ± 5 °C'; 'Relative humidity range 10% to 90%, "
              "noncondensing'; 'Maximum altitude 2,000 m'. As for the X410, outdoor use needs a sheltered radio "
              "cabled to the antennas."),
    # ---- AMD DS926 RF-ADC --------------------------------------------------------------------
    dict(id="ds926_zu2xdr_rfadc_nsd",
         value=[{"condition": "noise_floor_input_minus35dbfs", "typ_dbfs_per_hz": -151.5},
                {"condition": "fin_240mhz", "typ_dbfs_per_hz": -150.0, "max_dbfs_per_hz": -147.0},
                {"condition": "fin_1p9ghz", "typ_dbfs_per_hz": -148.0},
                {"condition": "fin_2p4ghz", "typ_dbfs_per_hz": -146.0, "max_dbfs_per_hz": -144.0},
                {"condition": "fin_3p5ghz", "temperature_grade": "E and I", "typ_dbfs_per_hz": -144.0,
                 "max_dbfs_per_hz": -142.0},
                {"condition": "fin_3p5ghz_m_temperature_grade", "temperature_grade": "M", "typ_dbfs_per_hz": -144.0,
                 "max_dbfs_per_hz": -141.0}],
         unit="dBFS/Hz", url=DS926_URL, doc=DS926_DOC,
         locator="Table 1 'RF-ADC Quad ADC Tile Performance Characteristics for ZU2xDR Devices', NSD rows "
                 "'Noise spectral density averaged across the first Nyquist zone'; the 'F IN = 3.5 GHz (by temperature "
                 "range)' row is split into 'E and I' (max -142) and 'M' (max -141) (document edition 2024-12-23)",
         note="Averaged across the first Nyquist zone; test conditions: sampling rate 2 GS/s (external clock), ADC "
              "inputs -1 dBFS, nominal voltage, Tj = 40 C. The X410 spec names the device 'Xilinx RFSoC XCZU28DR Speed "
              "Grade -1' without a temperature grade, so which 3.5 GHz maximum applies is not stated; only the typical "
              "values enter the arithmetic."),
    # ---- Published drone RCS (other groups' measurements) ------------------------------------
    dict(id="rcs_phantom2_10ghz_other_group", value=-20.0, unit="dBsm (other group's measurement, aspect-averaged)",
         url=RAHMAN_URL, doc=RAHMAN_DOC, locator="Section 1 Introduction, citing Schroder et al. [6]",
         note="DJI Phantom 2 at 10 GHz: 'on average -20 dBsm, after accounting for the fluctuations at different aspect "
              "angles'. Patel 2018 Table 1 lists Schroder 10 GHz as '-20 to -30' dBsm."),
    dict(id="rcs_f450_5p8_8p2ghz_other_group", value=-17.0, unit="dBsm (other group's measurement)", url=PATEL_URL,
         doc=PATEL_DOC, locator="Table 1 (Herschfelt et al. [22], 5.8 to 8.2 GHz) and Section 2 text on [22] (p.3)",
         note="HH polarisation per Patel's text: 'Both measurements exhibit a distinct relative amplitude of "
              "approximately -20 dB, with a HH RCS of -17 dBsm for the quadcopter and VV RCS of -8 dBsm for the "
              "octocopter, these findings correspond well to the physical reflectors of the target.' The quadcopter "
              "in [22] is the DJI 'F450 Flame Wheel (4 rotors)'. Table 1 itself does not state polarisation."),
    dict(id="rcs_parrot_ar_8p5ghz_other_group", value=-20.9, unit="dBsm (other group's measurement)", url=PATEL_URL,
         doc=PATEL_DOC, locator="Table 1 (Guay et al. [28], 8.5 GHz)", note="Parrot AR."),
    dict(id="rcs_cx20_9ghz_other_group", value={"rotors_off_dbsm": -21.0, "rotors_on_dbsm": -16.0},
         unit="dBsm (other group's measurement)", url=PATEL_URL, doc=PATEL_DOC,
         locator="Section 2 text (Khristenko et al. [23]) and Table 1",
         note="Cheerson CX-20, 9 GHz H-pol. Relative amplitude -25 dB rotors stopped, -22 dB rotating."),
    dict(id="li_ling_isar_single_image_max_other_group",
         value=[{"drone": "DJI Phantom 2", "band_ghz": "3-6", "el_deg": 0, "az_deg": 194, "max_dbsm": -27.5, "slide": 9},
                {"drone": "3DR Solo", "band_ghz": "3-6", "el_deg": 0, "az_deg": 90, "max_dbsm": -24.2, "slide": 12},
                {"drone": "DJI Inspire 1", "band_ghz": "3-6", "el_deg": 0, "az_deg": 270, "max_dbsm": -13.7, "slide": 13}],
         unit="dBsm (maximum pixel of one ISAR image; NOT a total RCS)", url=LILING_URL, doc=LILING_DOC,
         locator="slides 9, 12, 13 ('Max = ... dBsm'); slide 9 'On average, RCS at 3-6 GHz about ~12 dB lower than "
                 "12-15 GHz'; slide 14 'Drone propellers did not contribute a significant return relative to the drone body'",
         note="Patel 2018 Table 1 lists 'C. Li et al., 3 to 6 GHz, -24.2 dBsm' as an RCS; the slides show it is a "
              "single-image maximum, so it must not be used as a total RCS."),
    dict(id="blade_to_body_relative_level_other_groups",
         value=[{"authors": "Ritchie et al. [24]", "fc_ghz": "2.4", "relative_db": -17.0},
                {"authors": "Schroder et al. [20]", "fc_ghz": "10.0", "relative_db": -20.0},
                {"authors": "Herschfelt et al. [22]", "fc_ghz": "5.8-8.2", "relative_db": -20.0},
                {"authors": "Kim et al. [25]", "fc_ghz": "14.0", "relative_db": -20.0},
                {"authors": "Khristenko et al. [23]", "fc_ghz": "9.0", "relative_db": -22.0}],
         unit="dB relative to body", url=PATEL_URL, doc=PATEL_DOC, locator="Table 1 'Relative Amplitude / dB' column",
         note="Khristenko's -22 dB is with rotors rotating (-25 dB stopped), so it is not a clean blade-to-body ratio."),
    dict(id="blade_20_25db_statement_other_group", value={"lo_db": -25.0, "hi_db": -20.0}, unit="dB relative to body",
         url=PATEL_URL, doc=PATEL_DOC, locator="Section 2 text on Khristenko et al. [23]",
         note="'rotating elements are at least 20 to 25 dB weaker than the main body'."),
    # ---- Detection theory, noise reference -------------------------------------------------
    dict(id="albersheim_equation",
         value={"a_num": 0.62, "b_coef": 0.12, "c_coef": 1.7, "d0": 6.2, "d1": 4.54, "d2": 0.44, "n_coef": -5.0},
         unit="coefficients",
         url="https://doi.org/10.1109/PROC.1981.12082",
         doc="W. J. Albersheim (1981) A closed-form approximation to Robertson's detection characteristics, Proc. IEEE 69(7) 839",
         locator="closed-form equation",
         note="SNR_dB = n_coef*log10(N) + (d0 + d1/sqrt(N + d2)) * log10(A + b*A*B + c*B), A = ln(a_num/Pfa), "
              "B = ln(Pd/(1-Pd)); nonfluctuating target, noncoherent integration of N looks."),
    dict(id="swerling1_single_look", value="Pd = Pfa ** (1 / (1 + SNR))", unit="formula",
         url="https://doi.org/10.1109/TIT.1960.1057561",
         doc="P. Swerling (1960) Probability of detection for fluctuating targets, IRE Trans. Inf. Theory IT-6, 269-308",
         locator="Case 1, single pulse (also M. A. Richards, Fundamentals of Radar Signal Processing, ch. 6)",
         note="Square-law detection of a Rayleigh-fluctuating target in Gaussian noise."),
    dict(id="standard_noise_temperature", value=290.0, unit="K", url="https://www.itu.int/rec/R-REC-P.372",
         doc="ITU-R Recommendation P.372 (Radio noise)", locator="noise-figure / reference temperature definition (T0 = 290 K)",
         note="Reference temperature for noise figure; k and c come from scipy.constants (SI exact)."),
    # ---- Waveform numerologies ---------------------------------------------------------------
    dict(id="nr_numerology", value=[{"mu": 0, "scs_hz": 15e3}, {"mu": 1, "scs_hz": 30e3}, {"mu": 2, "scs_hz": 60e3}],
         symbols_per_slot=14, subframe_s=1e-3, unit="Hz",
         url="https://www.3gpp.org/dynareport/38211.htm", doc="3GPP TS 38.211 NR Physical channels and modulation",
         locator="Table 4.2-1 (Delta f = 2^mu * 15 kHz); Table 4.3.2-1 (14 symbols per slot, 2^mu slots per subframe, normal CP)",
         note="Earlier summary also via https://www.sharetechnote.com/html/5G/5G_FrameStructure.html."),
    dict(id="lte_numerology", value={"scs_hz": 15e3, "symbols_per_slot": 7, "slot_s": 0.5e-3}, unit="Hz",
         url="https://www.3gpp.org/dynareport/36211.htm", doc="3GPP TS 36.211 E-UTRA Physical channels and modulation",
         locator="clause 6.2.3, Table 6.2.3-1 (normal cyclic prefix)", note="14 symbols per 1 ms."),
    dict(id="wifi_legacy_ofdm", value={"scs_hz": 312.5e3, "t_fft_s": 3.2e-6, "t_gi_s": 0.8e-6, "t_gi_short_s": 0.4e-6},
         unit="Hz / s", url="https://standards.ieee.org/ieee/802.11/7028/",
         doc="IEEE Std 802.11-2020 (Clause 17 OFDM PHY timing-related parameters; short GI in HT/VHT clauses)",
         locator="Clause 17 timing-related parameters table (table number could not be verified: the standard text "
                 "was not accessible to this review)",
         primary_locator_status="could_not_verify",
         checkable_locators=[
             dict(url=MERAKI_URL, doc=MERAKI_DOC,
                  locator="section 'Orthogonal frequency division multiple access (OFDMA)', subsections 'Subcarriers' "
                          "and 'Symbol Time'",
                  quote="OFDM uses 64 subcarriers spaced 312.5 KHz apart. ... OFDM symbols take 3.2 µs."),
             dict(url=KEYSIGHT_GI_URL, doc=KEYSIGHT_GI_DOC,
                  locator="section 'Guard Interval (TGI) Time Calculation', table for 802.11n/ac",
                  quote="Guard Interval | T(FFT) | T(GI): 1/4 | 3.2 µs | 0.8 µs; 1/8 | 3.2 µs | 0.4 µs (table cells)"),
         ],
         note="The checkable locators are vendor documents, not the standard. The Keysight table is labelled "
              "802.11n/ac; its T_FFT and long/short GI equal the values used here. An earlier summary via "
              "https://www.litepoint.com/blog/wi-fi-6-vs-wi-fi-5-key-changes-to-the-rf-physical-layer/ could not be "
              "retrieved as raw text for a verbatim check."),
    dict(id="wifi_he_ofdm", value={"scs_hz": 78.125e3, "t_fft_s": 12.8e-6, "t_gi_s": [0.8e-6, 1.6e-6, 3.2e-6]},
         unit="Hz / s", url="https://standards.ieee.org/ieee/802.11ax/7180/",
         doc="IEEE Std 802.11ax-2021 (Clause 27 HE PHY timing-related constants)",
         locator="Clause 27 timing-related constants table (table number could not be verified: the standard text "
                 "was not accessible to this review)",
         primary_locator_status="could_not_verify",
         checkable_locators=[
             dict(url=MERAKI_URL, doc=MERAKI_DOC,
                  locator="section 'Orthogonal frequency division multiple access (OFDMA)', subsections 'Subcarriers' "
                          "and 'Symbol Time'",
                  quote="OFDMA uses 256 subcarriers spaced 78.125 KHz apart. ... OFDMA symbols take four times longer, "
                        "12.8 µs."),
             dict(url=KEYSIGHT_GI_URL, doc=KEYSIGHT_GI_DOC,
                  locator="section 'Guard Interval (TGI) Time Calculation', table for 802.11ax",
                  quote="Guard Interval | T(FFT) | T(GI): 1/4 | 12.8 µs | 3.2 µs; 1/8 | 12.8 µs | 1.6 µs; "
                        "1/16 | 12.8 µs | 0.8 µs (table cells)"),
         ],
         note="The checkable locators are vendor documents, not the standard. An earlier summary via "
              "https://www.litepoint.com/blog/wi-fi-6-vs-wi-fi-5-key-changes-to-the-rf-physical-layer/ could not be "
              "retrieved as raw text for a verbatim check."),
]
SRC = {s["id"]: s for s in SOURCES}
ASM = {a["id"]: a["value"] for a in ASSUMPTIONS}

# ---------------------------------------------------------------------------------------------
# Repo quotes checked at run time: (path, expected line, exact substring).
# ---------------------------------------------------------------------------------------------
REPO_QUOTES = [
    ("src/drones.py", 60, "물리적 최대치가 아니라 인증 등급(C0/C1/C2)·펌웨어 상한이다."),
    ("src/drones.py", 63, "matrice4e 는 코드 7500 vs docs/drone_specs_2026.json 6130 으로 충돌 상태 — 미해결."),
    ("src/drones.py", 339, '"matrice4e": DroneSpec('),
    ("src/drones.py", 343, "prop_dia_mm=274, prop_blades=2, num_rotors=4,"),
    ("src/drones.py", 344, "max_speed_ms=21, hover_rpm=3800, max_rpm=7500"),
    ("src/drones.py", 355, "MAX RPM IS AMBIGUOUS AND IS NOT A PHYSICAL LIMIT"),
    ("src/drones.py", 357, "'official C2 certification'. Unresolved. More importantly the declared maximum is a CLASS/FIRMWARE"),
    ("benchmark/elevation_sweep_md.py", 1821, "lam = 2.998e8 / carrier_of(arm)"),
    ("benchmark/elevation_sweep_md.py", 1822, "R = spec.prop_dia_mm / 2000.0"),
    ("benchmark/elevation_sweep_md.py", 1834, 'f_rev = float(getattr(spec, "hover_rpm", 6000.0)) / 60.0'),
    ("benchmark/elevation_sweep_md.py", 1835, "return 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(el_deg))"),
    ("benchmark/report07_three_engine_maps.py", 61, 'OUTJ = os.path.join(ROOT, "outputs", "report07_three_engines.json")'),
    ("benchmark/report07_three_engine_maps.py", 89, 'rpm0 = float(getattr(spec, "hover_rpm", 6000.0))'),
    ("benchmark/report07_three_engine_maps.py", 90, "lam = 3e8 / FC"),
    ("benchmark/report07_three_engine_maps.py", 91, "R = spec.prop_dia_mm / 1000.0 / 2.0"),
    ("benchmark/report07_three_engine_maps.py", 92, "f_rev = rpm0 / 60.0"),
    ("benchmark/report07_three_engine_maps.py", 94, "f_tip = 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(a.el))"),
]
REPO_LEDGER_REPORT07 = "outputs/report07_three_engines.json"


# ---------------------------------------------------------------------------------------------
def db10(x):
    return 10.0 * math.log10(x)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rnd(x, nd=6):
    return float(round(float(x), nd))


def check_quote(rel: str, line: int, quote: str) -> dict:
    p = ROOT / rel
    lines = p.read_text(encoding="utf-8").splitlines()
    status = "missing"
    found = None
    if 1 <= line <= len(lines) and quote in lines[line - 1]:
        status, found = "ok", line
    else:
        hits = [i + 1 for i, s in enumerate(lines) if quote in s]
        if len(hits) == 1:
            status, found = "moved", hits[0]
        elif len(hits) > 1:
            status = "ambiguous"
    if found is None:
        raise RuntimeError(f"repo quote check failed ({status}): {rel}:{line}: {quote!r}")
    return dict(path=rel, line_expected=line, line=found, quote=quote, status=status, sha256=sha256_file(p))


def drone_spec_from_ast(key: str) -> dict:
    """Read literal DroneSpec(...) keywords for DRONES[key] from src/drones.py without importing it."""
    tree = ast.parse((ROOT / "src/drones.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == key and isinstance(v, ast.Call):
                    out = {}
                    for kw in v.keywords:
                        try:
                            out[kw.arg] = ast.literal_eval(kw.value)
                        except ValueError:
                            continue
                    return out
    raise RuntimeError(f"DroneSpec for {key!r} not found in src/drones.py")


def nf_db(fc_ghz: float) -> float:
    for band in SRC["x410_rx_noise_figure"]["value"]:
        if band["band_lo_ghz"] <= fc_ghz < band["band_hi_ghz"]:
            return band["nf_db"]
    raise ValueError(fc_ghz)


def pt_cw_dbm(fc_ghz: float) -> float:
    for r in SRC["x410_fig3_cw_max_output"]["value"]:
        if r["fc_ghz"] == fc_ghz:
            return r["dbm"]
    raise ValueError(fc_ghz)


def pt_case_dbm(fc_ghz: float, case: str) -> float:
    if case in ("cw_max", "cw_tone_max"):
        return pt_cw_dbm(fc_ghz)
    if case == "ofdm_plus5dbm":
        return SRC["x410_fig2_evm_floor_channel_power"]["value"]
    raise ValueError(case)


def nsd(condition: str) -> float:
    for r in SRC["ds926_zu2xdr_rfadc_nsd"]["value"]:
        if r["condition"] == condition:
            return r["typ_dbfs_per_hz"]
    raise ValueError(condition)


C_MPS = sc.c
K_B = sc.k
T0_K = SRC["standard_noise_temperature"]["value"]
KT0_DBW_HZ = db10(K_B * T0_K)
KT0_DBM_HZ = KT0_DBW_HZ + 30.0


def lam_m(fc_ghz: float) -> float:
    return C_MPS / (fc_ghz * 1e9)


def snr_terms(fc_ghz, pt_dbm, g_dbi, sigma_dbsm, t_s, r_m, nf, loss):
    lam = lam_m(fc_ghz)
    return [
        dict(term="pt_dbw", db=pt_dbm - 30.0),
        dict(term="gt_plus_gr", db=2.0 * g_dbi),
        dict(term="lambda_squared", db=db10(lam ** 2)),
        dict(term="sigma", db=float(sigma_dbsm)),
        dict(term="dwell_time_T", db=db10(t_s)),
        dict(term="minus_four_pi_cubed", db=-db10((4 * math.pi) ** 3)),
        dict(term="minus_range_to_fourth", db=-40.0 * math.log10(r_m)),
        dict(term="minus_kT0_dbw_per_hz", db=-KT0_DBW_HZ),
        dict(term="minus_noise_figure", db=-nf),
        dict(term="minus_loss", db=-loss),
    ]


def snr_db(fc_ghz, pt_dbm, g_dbi, sigma_dbsm, t_s, r_m, nf, loss):
    return sum(t["db"] for t in snr_terms(fc_ghz, pt_dbm, g_dbi, sigma_dbsm, t_s, r_m, nf, loss))


def snr_linear_db(fc_ghz, pt_dbm, g_dbi, sigma_dbsm, t_s, r_m, nf, loss):
    """Independent linear-domain evaluation, used as a closure check of the dB sum."""
    pt_w = 10 ** ((pt_dbm - 30) / 10)
    g = 10 ** (g_dbi / 10)
    sig = 10 ** (sigma_dbsm / 10)
    f = 10 ** (nf / 10)
    lo = 10 ** (loss / 10)
    lam = lam_m(fc_ghz)
    num = pt_w * g * g * lam ** 2 * sig * t_s
    den = (4 * math.pi) ** 3 * r_m ** 4 * K_B * T0_K * f * lo
    return db10(num / den)


def rmax_m(fc_ghz, pt_dbm, g_dbi, sigma_dbsm, t_s, nf, loss, thr_db):
    s1 = snr_db(fc_ghz, pt_dbm, g_dbi, sigma_dbsm, t_s, 1.0, nf, loss)
    return 10 ** ((s1 - thr_db) / 40.0)


def albersheim_db(pd, pfa, n=1):
    co = SRC["albersheim_equation"]["value"]
    a = math.log(co["a_num"] / pfa)
    b = math.log(pd / (1 - pd))
    return co["n_coef"] * math.log10(n) + (co["d0"] + co["d1"] / math.sqrt(n + co["d2"])) * math.log10(
        a + co["b_coef"] * a * b + co["c_coef"] * b)


def swerling1_db(pd, pfa):
    return db10(math.log(pfa) / math.log(pd) - 1.0)


def pd_nonfluct_exact(snr_db_val, pfa):
    """Square-law detector, one look, nonfluctuating target: Pd = Q_chi2'(2 dof, noncentrality 2 SNR)."""
    thr = chi2.isf(pfa, 2)
    return float(ncx2.sf(thr, 2, 2 * 10 ** (snr_db_val / 10)))


# ---------------------------------------------------------------------------------------------
def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def out_label() -> str:
    try:
        return OUT.relative_to(ROOT).as_posix()
    except ValueError:
        return f"(outside root) {OUT.name}"


DEFINITIONS = {
    "kT0_dbm_per_hz": f"10*log10(k*T0) + 30 with k from scipy.constants and T0 = {T0_K:g} K.",
    "snr_db": "Radar equation, full-duty coherent integration over T: SNR = Pt Gt Gr lambda^2 sigma T / "
              "((4 pi)^3 R^4 k T0 F L), evaluated as the dB sum of worked_example.terms; lambda = c/fc with c "
              "from scipy.constants.",
    "snr_per_sample_db": "snr_db - 10*log10(B*T): the SNR of one sample in bandwidth B.",
    "integration_gain_db": "10*log10(B*T).",
    "closure_db": "snr_db (dB sum) minus the same quantity evaluated in the linear domain.",
    "rmax_m": "Range where snr_db equals the threshold: 10**((SNR at 1 m - threshold)/40).",
    "threshold_nonfluctuating_13db": f"{ASM['nonfluctuating_threshold_db']:.1f} dB planning threshold (configuration, "
                                     "see assumptions).",
    "threshold_swerling1": f"Swerling-1 single look, Pd {PD:g}, Pfa {PFA:g}: 10*log10(ln(Pfa)/ln(Pd) - 1).",
    "albersheim": "Albersheim closed form with N = 1 (sources.albersheim_equation).",
    "pd_exact_nonfluctuating": "Square-law detection of a nonfluctuating target, one look: threshold = chi2.isf(Pfa, 2); "
                               "Pd = ncx2.sf(threshold, 2, 2*SNR).",
    "range_factor": "Maximum-range ratio for an SNR change of dS dB: 10**(dS/40).",
    "walk_hz": "Doppler change over the dwell from constant radial acceleration a: 2*a*T/lambda.",
    "bin_hz": "Doppler bin width 1/T.",
    "thermal_floor_dbm_in_band": "kT0 + NF + 10*log10(B).",
    "fs_to_adc_noise_db_in_band_ideal_12bit_mcr": (
        f"20*log10(2)*{SRC['x410_converter_bits']['value']['adc_bits']} + 10*log10(1.5) + 10*log10(MCR/B) with MCR = "
        f"{SRC['uhd_x410_master_clock_rates']['value'][0]['mcr_hz'] / 1e6:g} MS/s (the earlier, superseded model: master "
        "clock rate is not the converter rate and converter noise is ignored)."),
    "fs_to_adc_noise_db_in_band_ds926_nsd": "-NSD[dBFS/Hz] - 10*log10(B).",
    "leakage_ceiling_dbm": "thermal_floor_dbm_in_band + fs_to_adc_noise_db_in_band - adc_noise_margin_db - PAPR, PAPR = "
                           "ofdm_papr_db for OFDM cases and 0 for a constant-envelope CW tone. It follows from setting "
                           "the RX gain so thermal noise sits margin dB above the input-referred ADC noise and keeping "
                           "the leakage peak at or below full scale.",
    "required_isolation_db (isolation_rows)": "average TX power - leakage_ceiling_dbm.",
    "tx_noise_dbm_per_hz": (f"{SRC['x410_tx_noise_density']['value']:g} dBm/Hz + TX gain offset; offset = CW output "
                            f"power for cw_tone_max and ({SRC['x410_fig2_evm_floor_channel_power']['value']:g} + PAPR) for "
                            "ofdm_plus5dbm (assumptions.tx_noise_gain_scaling)."),
    "required_isolation_db (tx_noise_isolation_rows)": "tx_noise_dbm_per_hz - (kT0 + NF) + tx_noise_margin_db.",
    "nf_degradation_db_at_margin": "10*log10(1 + 10**(-margin/10)).",
    "excess_over_thermal_db_at_1khz": (
        "(Pt - I) + L_pn(1 kHz) + rx_lo_independent_db - (kT0 + NF), with L_pn(1 kHz) = "
        f"{next(r['dbc_per_hz'] for r in SRC['x410_tx_phase_noise_1ghz']['value'] if r['offset_hz'] == 1e3):g} dBc/Hz "
        "+ 20*log10(fc/1 GHz). The Doppler bin width cancels, so it does not depend on T. Applies to the leakage's own "
        "range bin near zero delay."),
    "reference_channel_residual_change_db": "10*log10(var_RXA + var_RXB) - 10*log10(var_TX + var_RXB): change of the "
                                            "phase-noise skirt on signal channel B after subtracting the phase measured "
                                            "on a coupled reference channel A with an independent LO.",
    "v_tip_mps": "2*pi*(rpm/60)*(prop_dia_mm/2000).",
    "f_tip_hz": "2*v_tip*cos(el)/lambda (monostatic, blade-tip Doppler magnitude).",
    "f_body_hz": "2*body_speed/lambda (fully radial).",
    "required_complex_rate_hz": "2*(f_tip + f_body): complex slow-time sampling rate that keeps +/- the maximum Doppler "
                                "inside one unaliased span.",
    "f_flash_hz": "prop_blades * rpm / 60.",
    "fraction (intra_symbol_doppler_rows)": "f_hz / scs_hz.",
    "slow_time_rate_hz": "every_symbol: symbols per second of the numerology; one_symbol_per_slot: slots per second "
                         "(NR, LTE); Wi-Fi rates hold only inside a packet.",
    "leakage_to_echo_ratio_db": "(Pt - I) - echo power, echo = Pt + 2G + 10log10(lambda^2) + sigma - 10log10((4pi)^3) - 40log10(R).",
    "adc_noise_input_referred_dbm_per_hz": "Fig.5 0 dBFS input at 30 dB gain + NSD (dBFS/Hz).",
    "combined_required_isolation_db": "max(adc_ds926_isolation_db, tx_noise_isolation_db) for one fc/case: the larger of "
                                      "the ADC-linearity requirement (DS926 main NSD) and the TX broadband-noise "
                                      "requirement. Phase noise, maximum operating input and loopback attenuation are "
                                      "not folded in.",
    "binding": "'adc' when adc_ds926_isolation_db >= tx_noise_isolation_db, else 'tx_noise': which term sets "
               "combined_required_isolation_db.",
    "max_operating_input_isolation_db": "pt_avg_dbm + papr_db - x410_rx_max_operating_input (dBm): isolation that keeps "
                                        "the leakage peak at or below the X410 Table 13 maximum operating power.",
    "required_isolation_db_if_ofdm_papr_applied_to_cw": "cw_tone_max rows only: pt_avg_dbm - (leakage_ceiling_dbm - "
                                                        "ofdm_papr_db), i.e. the earlier calculation that also subtracted "
                                                        "the OFDM PAPR for a CW tone. Kept for traceability; not the "
                                                        "current model.",
    "leakage_ceiling_dbm_at_best_nsd": "leakage_ceiling_dbm evaluated with the DS926 noise-floor NSD "
                                       "(noise_floor_input_minus35dbfs, typical) instead of the main FIN 1.9 GHz value.",
    "required_isolation_db_at_best_nsd": "pt_avg_dbm - leakage_ceiling_dbm_at_best_nsd.",
    "walk_over_bin": "walk_hz / bin_hz = 2*a*T^2/lambda: Doppler walk over the dwell in units of one Doppler bin.",
    "both_gains_reach_scope_range": "min(rmax_m_g12, rmax_m_g18) >= scope_range_m.",
    "any_gain_reaches_scope_range": "max(rmax_m_g12, rmax_m_g18) >= scope_range_m.",
    "relative_difference_meta_vs_formula": "(f_tip_hz_meta - f_tip_hz_formula_at_el_minus15) / "
                                           "f_tip_hz_formula_at_el_minus15, formula with c_used_for_formula_mps.",
    "f_tip_hz_with_si_c": "Same f_tip formula with c = scipy.constants.c (exact SI value).",
    "payload_gbps": "channels * rate_hz * bytes_per_sample * 8 / 1e9: IQ sample payload only, without packet or "
                    "protocol overhead.",
    "decimation": "mcr_hz / rate_hz (integer_decimation is true when it is an integer to 1e-9).",
    "albersheim_rounds_to_planning_threshold": "round(albersheim_pd0p9_pfa1e-6_db) == "
                                               "planning_threshold_nonfluctuating_db.",
    "is_consequence_of_assumption": "true when the entry follows directly from the named assumption (assumption_id) "
                                    "by arithmetic, so it restates that assumption rather than adding a finding.",
    "assumption_id": "id of the entry in _meta.assumptions that the value follows from.",
    "max_rpm_note_quotes": "repo_quotes records (path, line, quote, sha256) that support tip_doppler_inputs.max_rpm_note.",
    "max_rpm_docs_json_value_from_quote": "rpm value attributed to docs/drone_specs_2026.json, parsed at run time from "
                                          "the quoted src/drones.py comment line.",
    "relative_difference_from_quoted_c_ratio": "c_used_for_formula_mps / report07_generator_c_mps - 1, with both "
                                               "constants parsed from the quoted lines; f_tip scales as fc/c, so this "
                                               "is the gap a c difference alone produces.",
    "residual_after_quoted_c_ratio": "relative_difference_meta_vs_formula (unrounded) minus "
                                     "relative_difference_from_quoted_c_ratio.",
    "explanation_quotes": "repo_quotes records for the report07 generator lines (rpm0, lam, R, f_rev, f_tip) and the "
                          "elevation_sweep_md.py lines (lam, R, f_rev, f_tip) that repo_rotor_reference.note relies on.",
    "complex_rate_exceeds_rj45_uhd_rate": "bandwidth_hz (complex sample rate needed) > uhd_x410_rj45_streaming value.",
    "temperature_grade (sources.ds926_zu2xdr_rfadc_nsd)": "DS926 Table 1 temperature-range column label for the "
                                                          "FIN 3.5 GHz NSD row ('E and I' or 'M').",
    "primary_locator_status (sources)": "'could_not_verify' when the table number in locator could not be checked "
                                        "against the primary document.",
    "checkable_locators (sources)": "openly accessible documents whose text was read verbatim for the same values: "
                                    "url, doc, locator and the quoted text.",
}

NOT_COMPUTED = [
    dict(item=f"phase-noise excess over thermal in range bin 2 ({2 * C_MPS / (2 * BANDWIDTH_HZ):.0f} m at "
              f"{BANDWIDTH_HZ / 1e6:g} MHz)",
         why="It depends on the waveform's range sidelobes and inter-carrier spreading (waveform and window); only "
             "the leakage's own near-zero range bin is computed here."),
    dict(item="actual TX-to-RX isolation of the antenna pair and X410 channel-to-channel isolation",
         why="Not in any X410 document; it has to be measured."),
    dict(item="RF-ADC NSD at the X410's own converter rate and clocking",
         why="Neither the NI spec nor the UHD manual states it; DS926 values are at 2 GS/s with an external clock."),
    dict(item="whether TX and RX of one ZBX channel share an LO synthesizer",
         why=f"No verbatim document statement found; the phase-noise rows assume independent LOs "
             f"({ASM['rx_lo_independent_db']:+g} dB)."),
    dict(item="in-band (2.45 / 3.5 GHz) aspect-averaged total RCS of a quadcopter, and of the matrice4e",
         why="No such published measurement was found; the sigma grid is a bracket."),
    dict(item="cable loss for a sheltered (indoor-rated) radio feeding outdoor antennas",
         why="Unknown; range_factors.loss_rows shows the sensitivity to extra loss."),
]


def main() -> None:
    t_start = time.time()
    started = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.parent.mkdir(parents=True, exist_ok=True)

    quotes = [check_quote(*q) for q in REPO_QUOTES]
    report07 = json.loads((ROOT / REPO_LEDGER_REPORT07).read_text(encoding="utf-8"))["_meta"]
    spec = drone_spec_from_ast(DRONE_KEY)

    source_hashes = {rel: sha256_file(ROOT / rel) for rel in sorted({q[0] for q in REPO_QUOTES} | {REPO_LEDGER_REPORT07})}

    meta = {
        "generator": f"benchmark/{NAME}.py",
        "command": RUN_COMMAND,
        "invocation": {"root": ".", "out": out_label(), "core": _CORE},
        "started_utc": started,
        "finished_utc": None,
        "status": "partial",
        "git_head": git_head(),
        "packages": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "script_sha256": sha256_file(SCRIPT),
        "seeds": SEEDS,
        "seeds_note": "No random numbers are drawn; all values are closed-form.",
        "scope": ("Simulation / code / bookkeeping checks: closed-form link-budget arithmetic on published specification "
                  "values and literature constants, plus run-time checks of quoted repo lines. No comparison against "
                  "RF measurements; no radio was operated. Published RCS values are other groups' measurements, used "
                  "only to bracket sigma."),
        "definitions": DEFINITIONS,
        "assumptions": ASSUMPTIONS,
        "source_hashes": source_hashes,
        "sections_done": [],
    }
    doc: dict = {"_meta": meta, "sources": SOURCES, "repo_quotes": quotes, "not_computed": NOT_COMPUTED}

    def checkpoint(section: str) -> None:
        meta["sections_done"].append(section)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    checkpoint("sources_and_quotes")

    loss = ASM["loss_db"]
    papr = ASM["ofdm_papr_db"]
    thr13 = ASM["nonfluctuating_threshold_db"]

    # ---- constants ---------------------------------------------------------------------------
    alb = albersheim_db(PD, PFA)
    sw1 = swerling1_db(PD, PFA)
    snr_exact = brentq(lambda s: pd_nonfluct_exact(s, PFA) - PD, 0.0, 30.0, xtol=1e-9)
    thresholds = {"threshold_values_db": {"nonfluctuating_13db": thr13, "swerling1": sw1}}
    doc["constants"] = {
        "kT0_dbm_per_hz": rnd(KT0_DBM_HZ),
        "kT0_dbw_per_hz": rnd(KT0_DBW_HZ),
        "c_mps": C_MPS,
        "k_j_per_k": K_B,
        "t0_k": T0_K,
        "loss_db": loss,
        "loss_db_flag": "assumed",
        "bandwidth_hz": BANDWIDTH_HZ,
        "range_resolution_m": rnd(C_MPS / (2 * BANDWIDTH_HZ)),
        "pd": PD,
        "pfa": PFA,
        "thresholds": {
            "albersheim_pd0p9_pfa1e-6_db": rnd(alb),
            "swerling1_pd0p9_pfa1e-6_db": rnd(sw1),
            "nonfluctuating_exact_pd0p9_pfa1e-6_db": rnd(snr_exact),
            "pd_exact_nonfluctuating_at_13db": rnd(pd_nonfluct_exact(thr13, PFA)),
            "pd_exact_nonfluctuating_at_albersheim": rnd(pd_nonfluct_exact(alb, PFA)),
            "planning_threshold_nonfluctuating_db": thr13,
            "albersheim_rounds_to_planning_threshold": bool(round(alb) == thr13),
            "formulas": {
                "albersheim": "SNR_dB = -5 log10(N) + (6.2 + 4.54/sqrt(N+0.44)) log10(A + 0.12 A B + 1.7 B), "
                              "A = ln(0.62/Pfa), B = ln(Pd/(1-Pd)), N = 1",
                "swerling1": "SNR = ln(Pfa)/ln(Pd) - 1 (from Pd = Pfa^(1/(1+SNR)))",
                "nonfluctuating_exact": "solve ncx2.sf(chi2.isf(Pfa,2), 2, 2 SNR) = Pd",
            },
        },
        "nf_by_fc": [{"fc_ghz": f, "nf_db": nf_db(f)} for f in FC_GHZ],
        "pt_by_case": [{"fc_ghz": f, "pt_case": c, "pt_dbm": pt_case_dbm(f, c)}
                       for f in FC_GHZ for c in ("cw_max", "ofdm_plus5dbm")],
        "nf_degradation_db_at_margin": rnd(db10(1 + 10 ** (-ASM["adc_noise_margin_db"] / 10))),
    }
    checkpoint("constants")

    # ---- worked example ----------------------------------------------------------------------
    w = WORKED
    w_pt = pt_cw_dbm(w["fc_ghz"])
    w_t = w["t_ms"] / 1000.0
    w_nf = nf_db(w["fc_ghz"])
    terms = snr_terms(w["fc_ghz"], w_pt, w["g_dbi"], w["sigma_dbsm"], w_t, w["r_m"], w_nf, loss)
    s = sum(t["db"] for t in terms)
    ig = db10(BANDWIDTH_HZ * w_t)
    doc["worked_example"] = {
        "fc_hz": w["fc_ghz"] * 1e9, "pt_dbm": w_pt, "pt_case": "cw_max", "g_dbi": w["g_dbi"],
        "sigma_dbsm": w["sigma_dbsm"], "t_s": w_t, "r_m": w["r_m"], "nf_db": w_nf, "loss_db": loss,
        "terms": [dict(term=t["term"], db=rnd(t["db"], 4)) for t in terms],
        "snr_db": rnd(s, 4),
        "snr_per_sample_db": rnd(s - ig, 4),
        "integration_gain_db": rnd(ig, 4),
        "closure_db": s - snr_linear_db(w["fc_ghz"], w_pt, w["g_dbi"], w["sigma_dbsm"], w_t, w["r_m"], w_nf, loss),
    }
    checkpoint("worked_example")

    # ---- rmax rows -----------------------------------------------------------------------------
    rows = []
    for f in FC_GHZ:
        for case in ("cw_max", "ofdm_plus5dbm"):
            for g in G_DBI:
                for tm in T_MS:
                    for sg in SIGMA_DBSM:
                        for thn, thv in thresholds["threshold_values_db"].items():
                            rows.append(dict(fc_ghz=f, pt_case=case, g_dbi=g, t_ms=tm, sigma_dbsm=sg, threshold=thn,
                                             pt_dbm=pt_case_dbm(f, case), nf_db=nf_db(f), threshold_db=rnd(thv, 4),
                                             rmax_m=rnd(rmax_m(f, pt_case_dbm(f, case), g, sg, tm / 1000, nf_db(f),
                                                               loss, thv), 3)))
    doc["rmax_rows"] = rows

    def rmax_lookup(**kw):
        hit = [r for r in rows if all(r[k] == v for k, v in kw.items())]
        assert len(hit) == 1, kw
        return hit[0]["rmax_m"]

    checkpoint("rmax_rows")

    # ---- SNR vs range --------------------------------------------------------------------------
    grid = sorted({rnd(r, 3) for r in np.logspace(1, 3, SNR_RANGE_LOG_POINTS)} | {float(a) for a in SNR_RANGE_ANCHORS_M})
    log_set = {rnd(r, 3) for r in np.logspace(1, 3, SNR_RANGE_LOG_POINTS)}
    srows = []
    f = SNR_RANGE_FC_GHZ
    for case in ("cw_max", "ofdm_plus5dbm"):
        for g in SNR_RANGE_G_DBI:
            for i, r in enumerate(grid):
                srows.append(dict(fc_ghz=f, pt_case=case, g_dbi=g, t_ms=SNR_RANGE_T_MS, sigma_dbsm=SNR_RANGE_SIGMA,
                                  r_m=r, r_index=i, on_log_grid=r in log_set,
                                  snr_db=rnd(snr_db(f, pt_case_dbm(f, case), g, SNR_RANGE_SIGMA, SNR_RANGE_T_MS / 1000,
                                                    r, nf_db(f), loss), 4)))
    doc["snr_vs_range_rows"] = srows
    checkpoint("snr_vs_range_rows")

    # ---- range factors -------------------------------------------------------------------------
    blade_vals = sorted({b["relative_db"] for b in SRC["blade_to_body_relative_level_other_groups"]["value"]}
                        | {SRC["blade_20_25db_statement_other_group"]["value"]["lo_db"],
                           SRC["blade_20_25db_statement_other_group"]["value"]["hi_db"]}, reverse=True)
    ref_sigma = SNR_RANGE_SIGMA
    pt_reading = []
    for fc in FC_GHZ:
        for dp in (-SRC["x410_fig3_cw_max_output"]["reading_uncertainty_db"], SRC["x410_fig3_cw_max_output"]["reading_uncertainty_db"]):
            pt_reading.append(dict(fc_ghz=fc, knob="fig3_reading_uncertainty", delta_pt_db=dp, factor=rnd(10 ** (dp / 40))))
    d57 = SRC["x410_fig3_level_at_5p7ghz"]["value"] - pt_cw_dbm(5.8)
    pt_reading.append(dict(fc_ghz=5.8, knob="fig3_level_below_discontinuity_5p7ghz", delta_pt_db=rnd(d57, 4),
                           factor=rnd(10 ** (d57 / 40))))
    doc["range_factors"] = {
        "swerling1_vs_13db": rnd(10 ** (-(sw1 - thr13) / 40)),
        "swerling1_vs_albersheim": rnd(10 ** (-(sw1 - alb) / 40)),
        "blade_rows": [dict(blade_minus_body_db=b, factor=rnd(10 ** (b / 40))) for b in blade_vals],
        "sigma_rows": [dict(sigma_dbsm=sg, factor_vs_minus20=rnd(10 ** ((sg - ref_sigma) / 40))) for sg in SIGMA_DBSM],
        "pt_case_rows": [dict(fc_ghz=fc, ofdm_plus5dbm_vs_cw_max=rnd(10 ** ((pt_case_dbm(fc, "ofdm_plus5dbm")
                                                                          - pt_cw_dbm(fc)) / 40))) for fc in FC_GHZ],
        "loss_rows": [dict(extra_loss_db=e, factor=rnd(10 ** (-e / 40))) for e in EXTRA_LOSS_DB],
        "pt_reading_rows": pt_reading,
    }
    # scope of the "noise is not binding" statement
    scope = []
    for case in ("cw_max", "ofdm_plus5dbm"):
        for thn in ("nonfluctuating_13db", "swerling1"):
            for sg in SIGMA_DBSM:
                for tm in T_MS:
                    r12 = rmax_lookup(fc_ghz=SNR_RANGE_FC_GHZ, pt_case=case, g_dbi=SNR_RANGE_G_DBI[0], t_ms=tm, sigma_dbsm=sg, threshold=thn)
                    r18 = rmax_lookup(fc_ghz=SNR_RANGE_FC_GHZ, pt_case=case, g_dbi=SNR_RANGE_G_DBI[1], t_ms=tm, sigma_dbsm=sg, threshold=thn)
                    scope.append(dict(fc_ghz=SNR_RANGE_FC_GHZ, pt_case=case, threshold=thn, sigma_dbsm=sg, t_ms=tm,
                                      rmax_m_g12=r12, rmax_m_g18=r18, scope_range_m=NOISE_SCOPE_RANGE_M,
                                      both_gains_reach_scope_range=bool(min(r12, r18) >= NOISE_SCOPE_RANGE_M),
                                      any_gain_reaches_scope_range=bool(max(r12, r18) >= NOISE_SCOPE_RANGE_M)))
    doc["noise_binding_scope_rows"] = scope
    checkpoint("range_factors")

    # ---- Doppler walk --------------------------------------------------------------------------
    doc["doppler_walk_rows"] = [
        dict(accel_mps2=a, fc_ghz=fc, t_ms=tm, walk_hz=rnd(2 * a * (tm / 1000) / lam_m(fc), 4), bin_hz=rnd(1000 / tm, 4),
             walk_over_bin=rnd((2 * a * (tm / 1000) / lam_m(fc)) / (1000 / tm), 5))
        for a in ACCEL_MPS2 for fc in FC_GHZ for tm in T_MS]
    checkpoint("doppler_walk_rows")

    # ---- Isolation: ADC linearity and TX noise --------------------------------------------------
    mcr = SRC["uhd_x410_master_clock_rates"]["value"][0]["mcr_hz"]
    bits = SRC["x410_converter_bits"]["value"]["adc_bits"]
    ideal_dr = 20 * math.log10(2) * bits + db10(3 / 2) + db10(mcr / BANDWIDTH_HZ)   # ideal full-scale sine SQNR
    nsd_main = nsd("fin_1p9ghz")
    nsd_best = nsd("noise_floor_input_minus35dbfs")
    margin = ASM["adc_noise_margin_db"]
    irows = []
    for fc in FC_GHZ:
        nth = KT0_DBM_HZ + nf_db(fc) + db10(BANDWIDTH_HZ)
        for case in ("ofdm_plus5dbm", "cw_tone_max"):
            p = pt_case_dbm(fc, case)
            pk = papr if case == "ofdm_plus5dbm" else 0.0
            for model in ("ideal_12bit_mcr", "ds926_nsd"):
                row = dict(fc_ghz=fc, case=case, adc_model=model, pt_avg_dbm=p, papr_db=pk,
                           thermal_floor_dbm_in_band=rnd(nth, 4))
                if model == "ideal_12bit_mcr":
                    dr = ideal_dr
                    ceil = nth + dr - margin - pk
                    row.update(fs_to_adc_noise_db_in_band=rnd(dr, 4), leakage_ceiling_dbm=rnd(ceil, 4),
                               required_isolation_db=rnd(p - ceil, 4), status="superseded_model_kept_for_traceability")
                else:
                    dr = -nsd_main - db10(BANDWIDTH_HZ)
                    dr_best = -nsd_best - db10(BANDWIDTH_HZ)
                    ceil = nth + dr - margin - pk
                    ceil_best = nth + dr_best - margin - pk
                    row.update(nsd_dbfs_per_hz=nsd_main, nsd_best_dbfs_per_hz=nsd_best,
                               fs_to_adc_noise_db_in_band=rnd(dr, 4), leakage_ceiling_dbm=rnd(ceil, 4),
                               required_isolation_db=rnd(p - ceil, 4),
                               leakage_ceiling_dbm_at_best_nsd=rnd(ceil_best, 4),
                               required_isolation_db_at_best_nsd=rnd(p - ceil_best, 4), status="current_model")
                if case == "cw_tone_max":
                    # The earlier calculation also subtracted the OFDM PAPR for the CW-maximum case; kept only so
                    # that its numbers can be traced. A constant-envelope tone has no such term.
                    row["required_isolation_db_if_ofdm_papr_applied_to_cw"] = rnd(p - (ceil - papr), 4)
                irows.append(row)
    doc["isolation_rows"] = irows
    trows = []
    for fc in FC_GHZ:
        rxd = KT0_DBM_HZ + nf_db(fc)
        for case in ("ofdm_plus5dbm", "cw_tone_max"):
            p = pt_case_dbm(fc, case)
            offset = p + papr if case == "ofdm_plus5dbm" else p
            txn = SRC["x410_tx_noise_density"]["value"] + offset
            trows.append(dict(fc_ghz=fc, case=case, pt_avg_dbm=p, tx_gain_offset_db=rnd(offset, 4),
                              tx_noise_dbm_per_hz=rnd(txn, 4), rx_thermal_dbm_per_hz=rnd(rxd, 4),
                              required_isolation_db=rnd(txn - rxd + ASM["tx_noise_margin_db"], 4),
                              flag="gain_scaling_rule_unverified"))
    doc["tx_noise_isolation_rows"] = trows
    # combined requirement (max of ADC ds926 and TX noise) per fc/case
    comb = []
    for fc in FC_GHZ:
        for case in ("ofdm_plus5dbm", "cw_tone_max"):
            a = next(r for r in irows if r["fc_ghz"] == fc and r["case"] == case and r["adc_model"] == "ds926_nsd")
            t = next(r for r in trows if r["fc_ghz"] == fc and r["case"] == case)
            comb.append(dict(fc_ghz=fc, case=case, adc_ds926_isolation_db=a["required_isolation_db"],
                             adc_ds926_isolation_db_at_best_nsd=a["required_isolation_db_at_best_nsd"],
                             tx_noise_isolation_db=t["required_isolation_db"],
                             combined_required_isolation_db=max(a["required_isolation_db"], t["required_isolation_db"]),
                             binding=("adc" if a["required_isolation_db"] >= t["required_isolation_db"] else "tx_noise"),
                             max_operating_input_isolation_db=rnd(a["pt_avg_dbm"] + a["papr_db"]
                                                                  - SRC["x410_rx_max_operating_input"]["value"], 4),
                             loopback_minimum_attenuation_db=SRC["uhd_x410_loopback_attenuation"]["value"]))
    doc["isolation_summary_rows"] = comb
    # Fig.5 cross-check of input-referred ADC noise
    doc["adc_fig5_crosscheck_rows"] = [
        dict(fc_ghz=r["fc_ghz"], fs_input_dbm_at_30db_gain=r["dbm"], nsd_condition=cond, nsd_dbfs_per_hz=nsd(cond),
             adc_noise_input_referred_dbm_per_hz=rnd(r["dbm"] + nsd(cond), 4),
             rx_thermal_dbm_per_hz=rnd(KT0_DBM_HZ + nf_db(r["fc_ghz"]), 4),
             adc_minus_thermal_db=rnd(r["dbm"] + nsd(cond) - (KT0_DBM_HZ + nf_db(r["fc_ghz"])), 4))
        for r in SRC["x410_fig5_fs_input_30db_gain"]["value"]
        for cond in ("noise_floor_input_minus35dbfs", "fin_1p9ghz")]
    # leakage to echo
    le = []
    fc = SNR_RANGE_FC_GHZ
    for r in LEAK_ECHO_R_M:
        p = pt_cw_dbm(fc)
        echo = p + 2 * SNR_RANGE_G_DBI[0] + db10(lam_m(fc) ** 2) + SNR_RANGE_SIGMA - db10((4 * math.pi) ** 3) - 40 * math.log10(r)
        leak = p - LEAK_ECHO_ISOLATION_DB
        le.append(dict(fc_ghz=fc, pt_case="cw_max", g_dbi=SNR_RANGE_G_DBI[0], sigma_dbsm=SNR_RANGE_SIGMA,
                       isolation_db=LEAK_ECHO_ISOLATION_DB, r_m=float(r), echo_dbm=rnd(echo, 4), leakage_dbm=rnd(leak, 4),
                       leakage_to_echo_ratio_db=rnd(leak - echo, 4)))
    doc["leakage_to_echo_rows"] = le
    checkpoint("isolation_rows")

    # ---- Phase noise ----------------------------------------------------------------------------
    pn1k = next(r["dbc_per_hz"] for r in SRC["x410_tx_phase_noise_1ghz"]["value"] if r["offset_hz"] == 1e3)
    prow = []
    for fc in FC_GHZ:
        lpn = pn1k + 20 * math.log10(fc)
        for case in ("ofdm_plus5dbm", "cw_tone_max"):
            p = pt_case_dbm(fc, case)
            for iso in PN_ISOLATION_DB:
                exc = (p - iso) + lpn + ASM["rx_lo_independent_db"] - (KT0_DBM_HZ + nf_db(fc))
                prow.append(dict(fc_ghz=fc, case=case, isolation_db=iso, pt_avg_dbm=p,
                                 phase_noise_dbc_per_hz_at_1khz_scaled=rnd(lpn, 4),
                                 excess_over_thermal_db_at_1khz=rnd(exc, 4),
                                 applies_to="leakage range bin near zero delay",
                                 flag="fc_scaling_and_independent_rx_lo_unverified"))
    doc["phase_noise_rows"] = prow
    # coupled reference channel: residual with independent equal LO noise
    var_tx = var_a = var_b = 1.0
    ref_change = db10(var_a + var_b) - db10(var_tx + var_b)
    doc["phase_noise_reference_channel"] = {
        "skirt_without_reference_rel_db": rnd(db10(var_tx + var_b), 6),
        "skirt_after_subtracting_reference_rel_db": rnd(db10(var_a + var_b), 6),
        "reference_channel_residual_change_db": rnd(ref_change, 6),
        "is_consequence_of_assumption": True,
        "assumption_id": "reference_channel_equal_lo_noise",
        "note": ("This is not a finding: it restates assumption reference_channel_equal_lo_noise by arithmetic. With "
                 "equal, independent LO noise a coupled TX sample on channel A removes the TX term but adds channel "
                 f"A's RX LO noise, so the phase-noise skirt on channel B changes by {ref_change:+.1f} dB. With other "
                 "LO noise ratios or a shared LO the result differs. A coupled reference is still useful against "
                 "additive broadband TX noise and TX distortion. It captures only channel A's phase; array "
                 "calibration needs a known signal into every RX channel per session (e.g. splitter or the ZBX "
                 "CAL_LOOPBACK setting)."),
    }
    checkpoint("phase_noise_rows")

    # ---- Tip Doppler ----------------------------------------------------------------------------
    blades = int(spec["prop_blades"])
    dia_mm = float(spec["prop_dia_mm"])
    radius = dia_mm / 2000.0
    rpms = [(float(spec["hover_rpm"]), "hover", False), (float(spec["max_rpm"]), "coded_max_disputed_upper_bracket", True)]
    speeds = (0.0, float(spec["max_speed_ms"]))
    tip = []
    for fc in FC_GHZ:
        for rpm, label, disputed in rpms:
            vt = 2 * math.pi * (rpm / 60) * radius
            for el in TIP_EL_DEG:
                ft = 2 * vt * math.cos(math.radians(el)) / lam_m(fc)
                for vb in speeds:
                    fb = 2 * vb / lam_m(fc)
                    tip.append(dict(fc_ghz=fc, rpm=rpm, rpm_label=label, rpm_disputed=disputed, v_tip_mps=rnd(vt, 5),
                                    el_deg=el, body_speed_mps=vb, f_tip_hz=rnd(ft, 4), f_body_hz=rnd(fb, 4),
                                    required_complex_rate_hz=rnd(2 * (ft + fb), 4), f_flash_hz=rnd(blades * rpm / 60, 5)))
    doc["tip_doppler_rows"] = tip
    q_disp = next(q for q in quotes if "NOT A PHYSICAL LIMIT" in q["quote"])
    q_conf = next(q for q in quotes if q["path"] == "src/drones.py" and "drone_specs_2026.json" in q["quote"])
    q_class_ko = next(q for q in quotes if q["path"] == "src/drones.py" and "인증 등급" in q["quote"])
    q_class_en = next(q for q in quotes if q["path"] == "src/drones.py" and "CLASS/FIRMWARE" in q["quote"])
    m_docs = re.search(r"drone_specs_2026\.json\s+(\d+)", q_conf["quote"])
    m_code = re.search(r"(\d+)\s+vs", q_conf["quote"])
    if m_docs is None or m_code is None:
        raise RuntimeError("could not parse the rpm values from the quoted src/drones.py conflict line")
    docs_max_rpm = float(m_docs.group(1))
    if float(m_code.group(1)) != float(spec["max_rpm"]):
        raise RuntimeError("quoted coded max rpm does not match the DroneSpec literal")
    doc["tip_doppler_inputs"] = {
        "drone": DRONE_KEY, "prop_dia_mm": dia_mm, "prop_blades": blades, "hover_rpm": float(spec["hover_rpm"]),
        "max_rpm": float(spec["max_rpm"]), "max_speed_ms": float(spec["max_speed_ms"]),
        "read_from": "src/drones.py (AST literal read of the DRONES entry; lines checked in repo_quotes)",
        "max_rpm_dispute_quotes": [q_disp, q_conf],
        "max_rpm_note": (f"{float(spec['max_rpm']):.0f} rpm is the coded maximum. The code flags declared maxima as a "
                         f"class/firmware ceiling rather than a physical limit (src/drones.py lines {q_class_ko['line']}, "
                         f"{q_disp['line']} and {q_class_en['line']}) and records a conflict with {docs_max_rpm:.0f} rpm "
                         f"in docs/drone_specs_2026.json (line {q_conf['line']}); rows at "
                         f"{float(spec['max_rpm']):.0f} rpm are an upper bracket."),
        "max_rpm_note_quotes": [q_class_ko, q_conf, q_disp, q_class_en],
        "max_rpm_docs_json_value_from_quote": docs_max_rpm,
    }
    # slow-time rates of common numerologies and aliasing check at el 0
    nr = SRC["nr_numerology"]
    lte = SRC["lte_numerology"]["value"]
    wl = SRC["wifi_legacy_ofdm"]["value"]
    he = SRC["wifi_he_ofdm"]["value"]
    rates = []
    for m in nr["value"]:
        slot_s = nr["subframe_s"] / (2 ** m["mu"])
        rates.append(dict(waveform=f"nr_scs{int(m['scs_hz'] / 1e3)}khz", reference_use="every_symbol",
                          rate_hz=rnd(nr["symbols_per_slot"] / slot_s, 3)))
        rates.append(dict(waveform=f"nr_scs{int(m['scs_hz'] / 1e3)}khz", reference_use="one_symbol_per_slot",
                          rate_hz=rnd(1 / slot_s, 3)))
    rates.append(dict(waveform="lte_scs15khz", reference_use="every_symbol",
                      rate_hz=rnd(lte["symbols_per_slot"] / lte["slot_s"], 3)))
    rates.append(dict(waveform="lte_scs15khz", reference_use="one_symbol_per_slot", rate_hz=rnd(1 / lte["slot_s"], 3),
                      note="bookkeeping bracket only; LTE reference signals occupy more than one symbol per slot"))
    rates.append(dict(waveform="wifi_legacy_gi0p8us", reference_use="every_symbol_within_packet",
                      rate_hz=rnd(1 / (wl["t_fft_s"] + wl["t_gi_s"]), 3)))
    for gi in he["t_gi_s"]:
        rates.append(dict(waveform=f"wifi_he_gi{str(round(gi * 1e6, 1)).replace('.', 'p')}us",
                          reference_use="every_symbol_within_packet", rate_hz=rnd(1 / (he["t_fft_s"] + gi), 3)))
    alias = []
    for rr in rates:
        for t in tip:
            if t["el_deg"] != 0.0:
                continue
            alias.append(dict(waveform=rr["waveform"], reference_use=rr["reference_use"], fc_ghz=t["fc_ghz"], rpm=t["rpm"],
                              body_speed_mps=t["body_speed_mps"], el_deg=t["el_deg"], rate_hz=rr["rate_hz"],
                              required_complex_rate_hz=t["required_complex_rate_hz"],
                              aliases=bool(rr["rate_hz"] < t["required_complex_rate_hz"])))
    doc["slow_time_rate_rows"] = rates
    doc["slow_time_alias_rows"] = alias
    checkpoint("tip_doppler_rows")

    # ---- Repo rotor reference -------------------------------------------------------------------
    el_ref = float(report07["el_deg"])
    fc_ref = float(report07["fc_hz"])
    f_rev = float(spec["hover_rpm"]) / 60.0
    vt = 2 * math.pi * f_rev * radius
    q_sweep = next(q for q in quotes if q["path"].endswith("elevation_sweep_md.py") and q["quote"].startswith("lam ="))
    q_rep07 = next(q for q in quotes if q["path"].endswith("report07_three_engine_maps.py") and q["quote"].startswith("lam ="))
    c_sweep_text = q_sweep["quote"].split("=")[1].split("/")[0].strip()   # constant quoted from elevation_sweep_md.py
    c_rep07_text = q_rep07["quote"].split("=")[1].split("/")[0].strip()   # constant quoted from report07_three_engine_maps.py
    c_sweep = float(c_sweep_text)
    c_rep07 = float(c_rep07_text)
    rep07_quotes = [q for q in quotes if q["path"] == "benchmark/report07_three_engine_maps.py"
                    and not q["quote"].startswith("OUTJ")]
    sweep_quotes = [q for q in quotes if q["path"] == "benchmark/elevation_sweep_md.py"]
    q_rpm0 = next(q for q in rep07_quotes if q["quote"].startswith("rpm0 ="))
    q_frev07 = next(q for q in rep07_quotes if q["quote"].startswith("f_rev ="))
    q_frev_sw = next(q for q in sweep_quotes if q["quote"].startswith("f_rev ="))
    if "hover_rpm" not in q_rpm0["quote"] or "hover_rpm" not in q_frev_sw["quote"]:
        raise RuntimeError("quoted rotation-rate lines no longer read hover_rpm")
    div07 = float(q_frev07["quote"].split("/")[1])                        # divisor quoted from the report07 f_rev line
    if abs(float(spec["hover_rpm"]) / div07 - f_rev) > 1e-12:
        raise RuntimeError("report07 f_rev divisor differs from the formula divisor")

    def ftip_c(cval):
        return 2.0 * vt / (cval / fc_ref) * math.cos(math.radians(el_ref))

    meta_ft = float(report07["f_tip_hz"])
    formula_sweep = ftip_c(c_sweep)
    rel_meta = (meta_ft - formula_sweep) / formula_sweep
    rel_c_ratio = c_sweep / c_rep07 - 1.0
    residual_c = rel_meta - rel_c_ratio
    doc["repo_rotor_reference"] = {
        "drone": report07.get("drone"),
        "el_deg": el_ref,
        "fc_hz": fc_ref,
        "f_flash_hz": rnd(blades * f_rev, 9),
        "f_flash_hz_meta": float(report07["f_flash_hz"]),
        "f_tip_hz_meta": meta_ft,
        "f_tip_hz_formula_at_el_minus15": rnd(formula_sweep, 6),
        "c_used_for_formula_mps": c_sweep,
        "formula_source": "benchmark/elevation_sweep_md.py f_tip_at (quoted in repo_quotes)",
        "relative_difference_meta_vs_formula": rnd(rel_meta, 8),
        "relative_difference_from_quoted_c_ratio": rnd(rel_c_ratio, 8),
        "residual_after_quoted_c_ratio": residual_c,
        "f_tip_hz_with_si_c": rnd(ftip_c(C_MPS), 6),
        "f_tip_hz_with_report07_generator_c": rnd(ftip_c(c_rep07), 9),
        "report07_generator_c_mps": c_rep07,
        "relative_difference_meta_vs_report07_generator_c": ftip_c(c_rep07) / meta_ft - 1.0,
        "rpm_per_rotor_mean_meta": rnd(float(np.mean(report07["rpm_per_rotor"])), 6),
        "prf_hz_meta": float(report07["prf_hz"]),
        "explanation_quotes": rep07_quotes + sweep_quotes,
        "note": (f"The meta f_tip_hz ({meta_ft:.3f} Hz) differs from the elevation_sweep_md.py formula value "
                 f"({formula_sweep:.3f} Hz) by {rel_meta * 100:+.4f}%. Explanation: the script that writes "
                 f"{REPO_LEDGER_REPORT07} (benchmark/report07_three_engine_maps.py) computes the wavelength with "
                 f"c = {c_rep07_text} (line {q_rep07['line']}), while benchmark/elevation_sweep_md.py uses "
                 f"c = {c_sweep_text} (line {q_sweep['line']}). f_tip scales as fc/c, so the quoted constants alone give "
                 f"{rel_c_ratio * 100:+.4f}% ({c_sweep_text}/{c_rep07_text} - 1); the residual after removing it is "
                 f"{abs(residual_c):.1e}. Both scripts take the rotation rate from hover_rpm (report07 lines "
                 f"{q_rpm0['line']} and {q_frev07['line']}, elevation_sweep_md.py line {q_frev_sw['line']}), so the "
                 f"meta rpm_per_rotor spread (mean {float(np.mean(report07['rpm_per_rotor'])):.3f} rpm) does not enter "
                 "f_tip_hz. This is a difference in a bookkeeping constant, not in the physics."),
    }
    checkpoint("repo_rotor_reference")

    # ---- Intra-symbol Doppler ------------------------------------------------------------------
    scs_list = [("nr", m["scs_hz"]) for m in nr["value"]] + [("wifi_he", he["scs_hz"]), ("wifi_legacy", wl["scs_hz"])]
    isd = []
    for t in tip:
        if t["el_deg"] != 0.0 or t["body_speed_mps"] != 0.0:
            continue
        for fam, scs in scs_list:
            isd.append(dict(fc_ghz=t["fc_ghz"], rpm=t["rpm"], component="blade_tip_el0", family=fam, f_hz=t["f_tip_hz"],
                            scs_hz=scs, fraction=rnd(t["f_tip_hz"] / scs, 6)))
    doc["intra_symbol_doppler_rows"] = isd
    checkpoint("intra_symbol_doppler_rows")

    # ---- Streaming / clock-rate bookkeeping ----------------------------------------------------
    srt = []
    for rate in STREAM_RATES_HZ:
        for m in SRC["uhd_x410_master_clock_rates"]["value"]:
            d = m["mcr_hz"] / rate
            srt.append(dict(rate_hz=rate, mcr_hz=m["mcr_hz"], image=m["image"], decimation=rnd(d, 6),
                            integer_decimation=bool(abs(d - round(d)) < 1e-9)))
    stream = []
    for rate in STREAM_RATES_HZ:
        bps = STREAM_CHANNELS * rate * STREAM_BYTES_PER_SAMPLE * 8
        stream.append(dict(rate_hz=rate, channels=STREAM_CHANNELS, bytes_per_sample=STREAM_BYTES_PER_SAMPLE,
                           payload_mb_per_s=rnd(bps / 8 / 1e6, 4), payload_gbps=rnd(bps / 1e9, 4),
                           exceeds_rj45_uhd_rate_per_channel=bool(rate > SRC["uhd_x410_rj45_streaming"]["value"])))
    doc["clock_rate_rows"] = srt
    doc["streaming_rows"] = stream
    rj45_short = bool(BANDWIDTH_HZ > SRC["uhd_x410_rj45_streaming"]["value"])
    doc["rj45_conflict"] = {
        "uhd_manual": SRC["uhd_x410_rj45_streaming"]["note"],
        "product_page": SRC["x410_product_page_rj45"]["note"],
        "status": (f"conflicting NI sources; either way below a {BANDWIDTH_HZ / 1e6:g} MHz complex rate" if rj45_short
                   else f"conflicting NI sources; the UHD manual rate reaches a {BANDWIDTH_HZ / 1e6:g} MHz complex rate"),
        "complex_rate_exceeds_rj45_uhd_rate": rj45_short,
        "complex_rate_needed_for_bandwidth_sps": BANDWIDTH_HZ,
        "rj45_uhd_rate_sps": SRC["uhd_x410_rj45_streaming"]["value"],
    }

    # every row list must be addressable by its identifying fields (one row per selector)
    identity = {
        "rmax_rows": ("fc_ghz", "pt_case", "g_dbi", "t_ms", "sigma_dbsm", "threshold"),
        "snr_vs_range_rows": ("fc_ghz", "pt_case", "g_dbi", "t_ms", "sigma_dbsm", "r_m"),
        "noise_binding_scope_rows": ("fc_ghz", "pt_case", "threshold", "sigma_dbsm", "t_ms"),
        "doppler_walk_rows": ("accel_mps2", "fc_ghz", "t_ms"),
        "isolation_rows": ("fc_ghz", "case", "adc_model"),
        "tx_noise_isolation_rows": ("fc_ghz", "case"),
        "isolation_summary_rows": ("fc_ghz", "case"),
        "adc_fig5_crosscheck_rows": ("fc_ghz", "nsd_condition"),
        "leakage_to_echo_rows": ("r_m",),
        "phase_noise_rows": ("fc_ghz", "case", "isolation_db"),
        "tip_doppler_rows": ("fc_ghz", "rpm", "el_deg", "body_speed_mps"),
        "slow_time_rate_rows": ("waveform", "reference_use"),
        "slow_time_alias_rows": ("waveform", "reference_use", "fc_ghz", "rpm", "body_speed_mps"),
        "intra_symbol_doppler_rows": ("fc_ghz", "rpm", "scs_hz"),
        "clock_rate_rows": ("rate_hz", "mcr_hz"),
        "streaming_rows": ("rate_hz",),
    }
    for key, fields in identity.items():
        tuples = [tuple(r[f] for f in fields) for r in doc[key]]
        if len(set(tuples)) != len(tuples):
            raise RuntimeError(f"{key}: identifying fields {fields} do not select unique rows")
    for key, fields in (("blade_rows", ("blade_minus_body_db",)), ("sigma_rows", ("sigma_dbsm",)),
                        ("pt_case_rows", ("fc_ghz",)), ("loss_rows", ("extra_loss_db",)),
                        ("pt_reading_rows", ("fc_ghz", "knob", "delta_pt_db"))):
        tuples = [tuple(r[f] for f in fields) for r in doc["range_factors"][key]]
        if len(set(tuples)) != len(tuples):
            raise RuntimeError(f"range_factors.{key}: identifying fields {fields} do not select unique rows")
        identity[f"range_factors.{key}"] = fields
    meta["row_identity_fields"] = {k: list(v) for k, v in identity.items()}
    meta["status"] = "complete"
    meta["finished_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta["wall_time_s"] = round(time.time() - t_start, 3)
    checkpoint("streaming_rows")
    print(f"wrote {OUT} ({len(rows)} rmax rows, {len(srows)} snr rows) in {meta['wall_time_s']} s")


if __name__ == "__main__":
    main()
