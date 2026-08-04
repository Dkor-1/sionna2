# -*- coding: utf-8 -*-
"""ptd_drone_effect_headline.py — ptd_drone_effect.json 에 판정 블록을 덧붙인다(재계산 없음)."""
from __future__ import annotations

import json
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DST = os.path.join(ROOT, "outputs", "ptd_drone_effect.json")
DAS = 0.210

with open(DST, encoding="utf-8") as fh:
    D = json.load(fh)

MANY, FEW = "s1000plus", "mini5pro"
#  헤드라인은 **적합이 믿을 만하고 레벨도 물리적인** 조합에서만 뽑는다:
#  mini5pro(모서리 적음) · 조밀격자 1.8~5.8 GHz · 고도 3컷 풀링 · V(=VV, Das 규약과 동일 편파)
H = D["slopes"][FEW]["dense"]["el_pooled"]["V"]
Hm = D["slopes"][MANY]["dense"]["el_pooled"]["V"]
Hc = D["slopes"][FEW]["dense"]["el-2.0"]["V"]
Hh = D["slopes"][FEW]["dense"]["el_pooled"]["H"]

cost = D["cost"]["summary_pct"]
pp = D["per_pose_runtime_ms"]
fix = D["addendum"]["extraction_amortisation_correction"]
ctrl = D["production_sbr_control"]["summary"]

hl = {
    "question_1_effect": {
        "many_edges": dict(
            drone=MANY, L_metal_m=D["drones"][MANY]["edge_stats"]["length_metal_m"],
            L_metal_lambda=D["drones"][MANY]["L_metal_lambda_at_3p5GHz"],
            delta_sigma_mean_db_range=[
                min(D["drones"][MANY]["configs"][c]["V"]["delta_mean_db"]
                    for c in D["drones"][MANY]["configs"]),
                max(D["drones"][MANY]["configs"][c]["V"]["delta_mean_db"]
                    for c in D["drones"][MANY]["configs"])],
            verdict="PTD raises the azimuth-mean sigma by 8-24 dB - physically impossible"),
        "few_edges": dict(
            drone=FEW, L_metal_m=D["drones"][FEW]["edge_stats"]["length_metal_m"],
            L_metal_lambda=D["drones"][FEW]["L_metal_lambda_at_3p5GHz"],
            delta_sigma_mean_db_range=[
                min(D["drones"][FEW]["configs"][c]["V"]["delta_mean_db"]
                    for c in D["drones"][FEW]["configs"]),
                max(D["drones"][FEW]["configs"][c]["V"]["delta_mean_db"]
                    for c in D["drones"][FEW]["configs"])],
            verdict="PTD is a small, plausible correction (<= ~1.5 dB on the azimuth mean)"),
        "level_sanity_vs_production_sbr_db": ctrl,
        "reading": ("the effect scales with metal edge length exactly as PTD predicts, but on the "
                    "edge-rich airframe it overshoots into the physically impossible. Only the "
                    "edge-poor airframe gives numbers we can stand behind."),
    },
    "question_2_band_slope": {
        "headline_configuration": (f"{FEW} (few edges), dense grid 1.8-5.8 GHz (21 points), "
                                   f"3 elevation cuts pooled, V-pol (= Das VV convention)"),
        "slope_before_db_per_ghz": H["slope_po_db_per_ghz"],
        "se_before": H["se_po"], "r2_before": H["r2_po"],
        "slope_after_db_per_ghz": H["slope_ptd_db_per_ghz"],
        "se_after": H["se_ptd"], "r2_after": H["r2_ptd"],
        "delta_slope_db_per_ghz": H["delta_slope_db_per_ghz"],
        "das_slope_db_per_ghz": DAS,
        "gap_before_x": H["gap_po_x"], "gap_after_x": H["gap_ptd_x"],
        "significant": bool(abs(H["delta_slope_db_per_ghz"]) > 2 * max(H["se_po"], H["se_ptd"])),
        "answer": ("NO for the polarization that matters. On V-pol - the polarization Das "
                   "measured - the slope moves 0.954 -> 0.857 dB/GHz, a 0.097 dB/GHz change "
                   "against a fit standard error of ~0.10 dB/GHz. The gap to the measured slope "
                   "goes 4.54x -> 4.08x, a 10 % reduction that is not statistically separable "
                   "from zero. PTD does NOT explain the slope gap."),
        "cross_checks": {
            "few_edges_H_pol": dict(before=Hh["slope_po_db_per_ghz"],
                                    after=Hh["slope_ptd_db_per_ghz"],
                                    gap_before_x=Hh["gap_po_x"], gap_after_x=Hh["gap_ptd_x"],
                                    note=("H-pol DOES halve the gap (4.54x -> 1.91x) and the "
                                          "change is ~5 standard errors. But Das measured VV, so "
                                          "this is not the apples-to-apples number. It does say "
                                          "the fringe term carries real frequency-flat content.")),
            "few_edges_el_minus_2_V": dict(before=Hc["slope_po_db_per_ghz"],
                                           after=Hc["slope_ptd_db_per_ghz"],
                                           gap_before_x=Hc["gap_po_x"], gap_after_x=Hc["gap_ptd_x"]),
            "many_edges_V": dict(before=Hm["slope_po_db_per_ghz"], after=Hm["slope_ptd_db_per_ghz"],
                                 r2_before=Hm["r2_po"], r2_after=Hm["r2_ptd"],
                                 note=("REJECTED as a headline: the PO fit itself is meaningless "
                                       "(R2 0.05) because the 1.9 m frame's azimuth mean speckles "
                                       "at this lambda/7 point density, and the PTD level is "
                                       "16 dB above the production SBR value.")),
            "mechanism": ("the edge term's own slope is near zero (edge-only fits: "
                          f"{H['slope_edge_only_db_per_ghz']:+.2f} dB/GHz V-pooled, "
                          f"{Hh['slope_edge_only_db_per_ghz']:+.2f} dB/GHz H-pooled) - as expected, "
                          "since sigma_edge ~ (4pi/lambda^2)|L*lambda*f1|^2 is frequency-flat while "
                          "sigma_PO ~ A^2/lambda^2 rises. So a frequency-flat term added to a "
                          "rising one MUST flatten the total - but only in proportion to its "
                          "weight, and on V-pol its weight is 12-18 dB below the PO term."),
        },
        "published_reference_slopes": {
            "our_three_band_headline_db_per_ghz": 1.891,
            "our_three_band_headline_source": ("outputs/validate_measured_airframe.json "
                                               "8_comparison._headline.slope_ours_three_band_only "
                                               "(phantom4, production SBR)"),
            "our_per_airframe_three_band_db_per_ghz": {"min": 0.959, "max": 1.542,
                                                       "source": "outputs/report06_measurement.json"},
            "our_full_band_1p8_18p2_db_per_ghz": 0.435,
            "our_sub_band_1p8_5p21_db_per_ghz": 1.657,
            "note": ("the '~2.0 dB/GHz, 6.4-9.5x gap' framing refers to the published SBR "
                     "three-band headline, NOT to the PO-engine slopes measured here. The PO "
                     "engine used for this PTD experiment gives a lower before-slope to begin "
                     "with, so the before/after pair above must be read as a matched pair, not "
                     "spliced onto the published 1.891."),
        },
        "band_span_caveat": D["meta"]["band_span_warning"],
    },
    "question_3_cost": {
        "edge_vs_area_integral_pct": cost["vs_surface_integral"],
        "edge_vs_full_po_solve_pct": cost["vs_surface_plus_pointcloud"],
        "by_drone_edge_vs_area_integral_pct": {
            k: cost["by_drone"][k]["vs_surface_integral"] for k in cost["by_drone"]},
        "one_off_edge_extraction": {k: v for k, v in fix.items() if k != "note"},
        "extraction_note": fix["note"],
        "gao_2012_printed_pct": [4.6, 17.2],
        "comparison": ("Gao printed 4.6-17.2 %. Against the PO area integral alone we measure "
                       "11-260 % (median 78 %): on the small airframe at low frequency the edge "
                       "line integral costs about TWICE the surface integral. Against the whole "
                       "PO solve (point cloud + integral) we measure 7-34 % (median 20 %), which "
                       "brackets Gao's number. The two framings differ by what sits in the "
                       "denominator, so the framing must be stated with the number."),
        "why_the_difference": ("edge cost is frequency-INDEPENDENT here (the segment count is set "
                              "by the CAD tessellation, not by lambda) while the PO surface cost "
                              "grows as f^2. So the percentage falls monotonically with frequency "
                              "and with target size, and Gao's ~3920 lambda aircraft sits at the "
                              "far end of that trend where the surface integral dominates. NOT a "
                              "like-for-like comparison."),
    },
    "question_4_per_pose_runtime": {
        "edge_term_only_ms": pp["edge_term_only"],
        "po_only_ms_cpu_this_run": pp["po_only"],
        "po_plus_ptd_ms_realistic": {k: fix[k]["po_plus_ptd_median_ms_realistic"]
                                     for k in (MANY, FEW)},
        "baselines_ms": {"stock_sionna_published": [59.2, 286.0],
                         "stock_sionna_same_rtx4090": [72.8, 128.0],
                         "our_production_sbr_gpu_median": 38.1,
                         "ziganshin_per_angular_point": [1.94, 52.8]},
        "answer": ("the edge line integral adds 1.5-5.3 ms per pose (median 2.7 ms) on the host "
                   "CPU. A complete CPU PO+PTD pose is 12-28 ms (median ~15 ms on the small "
                   "airframe, ~28 ms on the large one, with edge extraction amortized over the "
                   "production grid). That is BELOW stock Sionna's own published per-pose cost "
                   "(59-286 ms) and below stock Sionna measured on our own RTX 4090 (73-128 ms), "
                   "and it sits beside our production GPU SBR pose of 38 ms. Cascading the "
                   "diffraction term does not negate the ray-tracing advantage at our target "
                   "size."),
    },
    "falsification_attempts": [
        {"hypothesis": ("the drone-level PTD effect is a mesh artifact: ~40-55 % of the kept metal "
                        "edge length has |alpha-180| of only 5-10 deg, i.e. tessellation seams on "
                        "the motor cylinders, and doc 3.7 warns those can stack coherently"),
         "test": "re-extract edges with sharp_deg = 5, 8, 10, 15, 20, 30 deg and recompute sigma",
         "result": (f"REFUTED. Raising the gate 5 -> 30 deg discards 53 % of the metal edge length "
                    f"on {MANY} (18.2 -> 8.5 m) and 61 % on {FEW} (5.9 -> 2.3 m), yet the mean "
                    f"delta moves by only "
                    f"{D['addendum'][MANY]['sharp_deg_verdict']['collapse_db']:+.2f} dB and "
                    f"{D['addendum'][FEW]['sharp_deg_verdict']['collapse_db']:+.2f} dB. The effect "
                    f"comes from the genuinely sharp motor rims, not from the seams."),
         "status": "our hypothesis was wrong; recorded as such"},
        {"hypothesis": "PTD flattens the frequency slope and closes the gap to the measured 0.21",
         "test": "dense 21-point regression 1.8-5.8 GHz, both polarizations, 3 elevation cuts",
         "result": ("PARTLY REFUTED. On V-pol (Das's polarization) the gap moves 4.54x -> 4.08x, "
                    "inside the fit error. Only H-pol halves it. The direction of the effect is "
                    "right; the magnitude is nowhere near enough to explain a 4-9x gap."),
         "status": "reported as a null result"},
    ],
    "blockers_before_this_can_be_used": [
        "reentrant edges (N < 1) are now excluded by default (defect D-3): before that guard, "
        "6.5 % of the s1000plus metal edge length sitting next to the exact pole N = 1/6 produced "
        "99.99 % of its edge field. Any drone number predating the guard is a numerical "
        "divergence, not physics, and the sentence 'the effect scales with metal edge length "
        "exactly as PTD predicts' is WITHDRAWN.",
        "the near-flat tessellation-seam threshold sharp_deg is not a pure speed knob (defect "
        "D-5): quote every drone number as a band over sharp_deg 5..30 deg, never a single value.",
        "no occlusion: this PO/PTD path lets every metal edge on the airframe radiate, including "
        "the far-side motors. The production engine is SBR with occlusion. The edge term must be "
        "attached to the SBR field (attach_to_sbr_field) and that path has never been executed.",
        "the truncated-wedge (TW) correction is absent, and the motor rims are exactly the "
        "few-lambda features where the infinite-wedge EEC is known to be worst.",
        "PTD attaches only where |Gamma| >= 0.999, which on our CAD means the motors and the "
        "battery box and nothing else - the carbon truss of s1000plus (|Gamma| = 0.90) "
        "contributes zero. Whether that is right is a modelling decision, not a measurement.",
    ],
    "one_line": ("PTD is cheap (+2.7 ms/pose, +7-34 % of a PO solve) and it does bend the slope "
                 "the right way, but on the polarization Das measured it closes only 10 % of the "
                 "gap - and on the edge-rich airframe it produces a sigma 16 dB above our own "
                 "production value, so the level cannot be used until the flat-plate calibration "
                 "and the SBR attachment are done."),
}
D["headline"] = hl
with open(DST, "w") as fh:
    json.dump(D, fh, indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in hl.items() if k in
                  ("question_2_band_slope", "one_line")}, indent=1, ensure_ascii=False)[:3000])
print("\n갱신:", DST)
