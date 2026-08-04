# -*- coding: utf-8 -*-
"""
phi_sweep_verdict.py — outputs/phi_sweep.json 을 읽어 **판정 블록**(verdict)을 붙인다.

질문: 우리가 발표해온 결론 중 **φ=90° 에서만 성립하는 것**이 있는가.
방법: 주장마다 (a) φ=90° 발표값, (b) φ 를 쓸었을 때의 값 범위, (c) 판정 을 적는다.
      판정은 **팔 B(σ 고정)** 와 **자세평균 팔** 을 통제군으로 삼는다 — 거기서 평평하면
      φ 의존은 기하가 아니라 σ 자세 몫이다.

실행: PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/phi_sweep_verdict.py
"""
from __future__ import annotations

import json
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
JSON_PATH = os.path.join(ROOT, "outputs", "phi_sweep.json")
MODES = ("W1", "L1", "G1")


def _arr(x):
    return np.array([np.nan if v is None else float(v) for v in x], float)


def build(D: dict) -> dict:
    phi = np.array(D["geometry"]["axis"]["phi_deg"], float)
    i90 = int(np.argmin(np.abs(phi - 90.0)))
    G = D["geometry"]
    ga, gs = G["axis"], G["summary"]

    # 1) 기하 확산항 — 여러 요약통계의 φ 범위
    un = np.abs(_arr(ga["n2_absmax_db"]))
    gt = np.abs(_arr(ga["n2_gated_absmax_db"]))
    md = np.abs(_arr(ga["n2_median_db"]))
    d1k = np.abs(np.array([r["n2_at_d1km_db"] for r in G["rows"]], float))
    spread_at_R = {m: np.abs(np.array([r["spread_db_at_R"]
                                       for r in D["sigma_fixed"]["by_mode"][m]["rows"]], float))
                   for m in MODES}

    # 2) R90 세 팔
    fixed = {m: _arr(D["sigma_fixed"]["by_mode"][m]["axis"]["R90_m"]) for m in MODES}
    asp = {m: _arr(D["aspect_averaged"]["by_mode"][m]["axis"]["R90_mean_over_psi_m"])
           for m in MODES}
    grid = {dr: {m: _arr(D["sigma_grid"][dr]["by_mode"][m]["axis"]["R90_m"]) for m in MODES}
            for dr in D["sigma_grid"]}

    def _span(a):
        return dict(at_phi90=float(a[i90]), min=float(np.nanmin(a)), max=float(np.nanmax(a)),
                    phi_at_min_deg=float(phi[int(np.nanargmin(a))]),
                    phi_at_max_deg=float(phi[int(np.nanargmax(a))]),
                    span_pct_of_phi90=float(100.0 * (np.nanmax(a) - np.nanmin(a)) / a[i90]),
                    span_db_equiv=float(40.0 * np.log10(np.nanmax(a) / np.nanmin(a))),
                    phi90_is=("minimum" if np.isclose(a[i90], np.nanmin(a)) else
                              "maximum" if np.isclose(a[i90], np.nanmax(a)) else "interior"))

    # 3) 블라인드·벽·수렴지수
    blind = {m: _arr(D["sigma_fixed"]["by_mode"][m]["axis"]["blind_frac"]) for m in MODES}
    nloc = {m: np.array([r["n_local_at_R"] for r in D["sigma_fixed"]["by_mode"][m]["rows"]],
                        float) for m in MODES}
    ceil = {m: np.array([r["snr_ceiling_db"] for r in D["sigma_fixed"]["by_mode"][m]["rows"]],
                        float) for m in MODES}
    limits = sorted({l for dr in D["sigma_grid"] for m in MODES
                     for l in D["sigma_grid"][dr]["by_mode"][m]["summary"]["limits_seen"]})
    cov = {m: _arr(D["sigma_grid"]["mini5pro"]["by_mode"][m]["axis"]["coverage_C"]) for m in MODES}
    cov_fix = {m: _arr(D["sigma_fixed"]["by_mode"][m]["axis"]["coverage_C"]) for m in MODES}

    # 4) 대칭성 자기검사 — φ 와 360−φ 는 기하가 같아야 한다
    def _mirror(a):
        idx = [int(np.argmin(np.abs(phi - ((360.0 - p) % 360.0)))) for p in phi]
        return float(np.nanmax(np.abs(a - a[idx])))
    sym = dict(
        constant_sigma_max_abs_diff_m={m: _mirror(fixed[m]) for m in MODES},
        sigma_grid_max_abs_diff_m={m: _mirror(grid["mini5pro"][m]) for m in MODES},
        meaning="phi and 360-phi are mirror images in y, so the GEOMETRY must be identical. The "
                "constant-sigma arm reproduces that to 0.0 m (self-check on the phi definition and "
                "the sweep code); the sigma-grid arm does not, and the residual is exactly the "
                "drone's azimuth RCS asymmetry - which is what makes the single-aspect R90 swing.")

    # 5) 자세평균 순위
    asp_orders = [tuple(sorted(MODES, key=lambda m: -asp[m][i])) for i in range(len(phi))]
    rank_aspect = dict(order_at_phi90=list(asp_orders[i90]),
                       n_distinct_orders=len(set(asp_orders)),
                       n_phi_with_different_order=int(sum(1 for o in asp_orders
                                                          if o != asp_orders[i90])),
                       flips=bool(len(set(asp_orders)) > 1))
    D.setdefault("rankings", {})["R90_aspect_averaged"] = dict(
        key="R90 averaged over 72 headings (mini5pro, sigma grid)", **rank_aspect)

    claims = [
        dict(id="C1",
             claim="Under the N1 normalisation (R_eq = sqrt(R1 R2) held equal) the geometry axis "
                   "contributes exactly zero to the link budget",
             published_at_phi90="max |spread difference| = 5.7e-14 dB (floating point)",
             range_over_phi="no phi axis exists - the identity is algebraic",
             verdict="SURVIVES", only_at_phi90=False,
             why="This is a CONVENTION, not a measurement: the bistatic radar equation folds into "
                 "R_eq^4 by construction. It cannot be a phi=90 artefact."),
        dict(id="C2",
             claim="The monostatic-vs-bistatic spread term differs by only 0.118 dB "
                   "(DECK_FACTS F27 / G5)",
             published_at_phi90=f"{un[i90]:.4f} dB (max |20log10(R2/R1)| over the 240-point d-grid)",
             range_over_phi=dict(
                 ungated_absmax_db=[float(np.nanmin(un)), float(np.nanmax(un))],
                 gated_absmax_db=[float(np.nanmin(gt)), float(np.nanmax(gt))],
                 median_over_d_db=[float(np.nanmin(md)), float(np.nanmax(md))],
                 at_fixed_d_1km_db=[float(np.nanmin(d1k)), float(np.nanmax(d1k))],
                 at_the_R90_operating_point_db=[
                     float(np.nanmin([spread_at_R[m].min() for m in MODES])),
                     float(np.nanmax([spread_at_R[m].max() for m in MODES]))],
                 phi_at_max_deg=float(phi[int(np.nanargmax(un))])),
             verdict="ONLY AT phi=90 (as a number) - but its operational reach is much smaller "
                     "than the 23.17 dB headline suggests",
             only_at_phi90=True,
             why="0.118 dB is genuinely specific to the perpendicular bisector, where R1=R2 holds "
                 "structurally. Sweeping phi takes it to 23.17 dB at phi=180. BUT that extremum is "
                 "an absolute max over the d-grid, reached at d~250 m where the target sits almost "
                 "on top of the illuminator; it survives the beta/far-field gate yet never reaches "
                 f"the R90 inversion, because R90 sits at 3.6-6.5 km where |delta| is at most "
                 f"{float(np.nanmax([spread_at_R[m].max() for m in MODES])):.2f} dB. The median over "
                 f"the d-grid tops out at {float(np.nanmax(md)):.2f} dB and the value at a fixed "
                 f"1 km at {float(np.nanmax(d1k)):.2f} dB."),
        dict(id="C3",
             claim="Geometry does not move the link budget / the detection result",
             published_at_phi90="R90 at phi=90 deg (see per-mode numbers)",
             range_over_phi=dict(
                 constant_sigma_control={m: _span(fixed[m]) for m in MODES},
                 aspect_averaged={m: _span(asp[m]) for m in MODES}),
             verdict="SURVIVES", only_at_phi90=False,
             why="With sigma held constant (pure geometry) R90 moves by at most "
                 f"{max(_span(fixed[m])['span_pct_of_phi90'] for m in MODES):.2f} % "
                 f"(<= {max(_span(fixed[m])['span_db_equiv'] for m in MODES):.3f} dB-equivalent) "
                 "over the FULL 360 deg circle, and with the drone aspect averaged out it moves by "
                 f"at most {max(_span(asp[m])['span_pct_of_phi90'] for m in MODES):.2f} %. "
                 "phi=90 deg is the MINIMUM in every arm, so the published range is the "
                 "conservative end of the phi axis, not a flattering one. The reason is that R90 is "
                 "set far out where kappa = R1 R2 -> d^2 regardless of phi; the phi dependence of "
                 "kappa lives at short range where SNR is already tens of dB above threshold."),
        dict(id="C4",
             claim="Doppler-blind heading fraction: WiFi 8.33 % / LTE 25 % / 5G 100 %",
             published_at_phi90={m: float(blind[m][i90]) for m in MODES},
             range_over_phi={m: [float(np.nanmin(blind[m])), float(np.nanmax(blind[m]))]
                             for m in MODES},
             verdict="SURVIVES", only_at_phi90=False,
             why="Constant to the resolution of the 72-heading grid at every phi. Structural: "
                 "rotating phi rotates the bisector u1+u2 in azimuth, and psi is swept over the "
                 "full circle, so the SET of folded Doppler values is only rotated - the fraction "
                 "below the guard is unchanged."),
        dict(id="C5",
             claim="Idle 5G (SSB, PRF 50 Hz) is Doppler-blind in 100 % of headings",
             published_at_phi90=float(blind["G1"][i90]),
             range_over_phi=[float(np.nanmin(blind["G1"])), float(np.nanmax(blind["G1"]))],
             verdict="SURVIVES", only_at_phi90=False,
             why="1.0 at all 72 phi. The guard half-width 2.5/T = 25 Hz equals PRF/2, so the whole "
                 "folded Doppler axis is guard - a time-axis fact with no geometry in it."),
        dict(id="C6",
             claim="The binding wall is the DPI residual (limit = dpi_residual)",
             published_at_phi90="dpi_residual",
             range_over_phi=limits,
             verdict="SURVIVES", only_at_phi90=False,
             why="Same label at all 72 phi for all 3 drones and all 3 modes."),
        dict(id="C7",
             claim="R scales as SNR^(1/4) at the operating point (local exponent n ~ 4)",
             published_at_phi90={m: float(nloc[m][i90]) for m in MODES},
             range_over_phi={m: [float(np.nanmin(nloc[m])), float(np.nanmax(nloc[m]))]
                             for m in MODES},
             verdict="SURVIVES", only_at_phi90=False,
             why="3.98-4.02 across the whole circle - the far-field regime where R90 lives is "
                 "monostatic-like for every phi."),
        dict(id="C8",
             claim="In-scene SNR ceiling (the best SNR anywhere on the valid d-grid)",
             published_at_phi90={m: float(ceil[m][i90]) for m in MODES},
             range_over_phi={m: [float(np.nanmin(ceil[m])), float(np.nanmax(ceil[m]))]
                             for m in MODES},
             verdict="ONLY AT phi=90", only_at_phi90=True,
             why=f"phi=90 deg gives the LOWEST ceiling of the whole circle; sweeping phi raises it "
                 f"by {float(np.nanmax(ceil['L1']) - ceil['L1'][i90]):.1f} dB (the target can pass "
                 "almost overhead the illuminator or the receiver, collapsing R1 or R2). Any "
                 "sentence quoting a ceiling must name the azimuth. It does NOT change R90, because "
                 "the extra SNR is at short range."),
        dict(id="C9",
             claim="Illuminator ranking by detection range (which of WiFi / LTE / 5G wins)",
             published_at_phi90=dict(
                 aspect_averaged=rank_aspect["order_at_phi90"],
                 single_aspect_by_drone={dr: D["rankings"][f"R90_{dr}"]["order_at_phi90"]
                                         for dr in D["sigma_grid"]}),
             range_over_phi=dict(
                 aspect_averaged_n_distinct_orders=rank_aspect["n_distinct_orders"],
                 aspect_averaged_n_phi_that_differ=rank_aspect["n_phi_with_different_order"],
                 single_aspect_n_distinct_orders={
                     dr: D["rankings"][f"R90_{dr}"]["n_distinct_orders"] for dr in D["sigma_grid"]},
                 single_aspect_n_phi_that_differ={
                     dr: D["rankings"][f"R90_{dr}"]["n_phi_with_different_order"]
                     for dr in D["sigma_grid"]},
                 constant_sigma_n_distinct_orders=D["rankings"]["R90_sigma_fixed"]
                 ["n_distinct_orders"]),
             verdict="SURVIVES as published (the published map is aspect-averaged); the "
                     "SINGLE-ASPECT ranking is cut-specific and must never be quoted",
             only_at_phi90=False,
             why="The headline map in docs/GEOMETRY_BENCHMARK.md comes from geometry_benchmark.py, "
                 "which uses the aspect_avg sigma configuration. Aspect-averaged, the order is "
                 f"{rank_aspect['order_at_phi90']} at ALL 72 phi (0 flips), and the constant-sigma "
                 "control likewise gives a single order. At a SINGLE aspect all six possible orders "
                 "appear and 43-68 of the 72 phi disagree with the phi=90 order - but that is an "
                 "ASPECT fragility, not a phi=90 artefact, and it is already visible as a "
                 "drone-to-drone disagreement at phi=90 itself."),
        dict(id="C10",
             claim="Coverage C (fraction of headings with Pd >= 0.9) at the detection range",
             published_at_phi90={m: float(cov[m][i90]) for m in MODES},
             range_over_phi={m: [float(np.nanmin(cov[m])), float(np.nanmax(cov[m]))]
                             for m in MODES},
             verdict="CUT-SPECIFIC, and the metric itself is fragile", only_at_phi90=True,
             why="C swings from 0.00 to 0.86 across phi in the sigma-grid arm, but the "
                 "constant-sigma control gives C identically "
                 f"{float(cov_fix['W1'][i90]):.3f} at every phi. C is evaluated AT d = R90, which "
                 "is by construction the range where Pd ~ 0.5, so C only becomes non-zero when "
                 "sigma varies strongly with heading. It therefore measures the sigma heading "
                 "spread, not coverage, and it should not be quoted as a single number at all."),
    ]

    only = [c["id"] + ": " + c["claim"] for c in claims if c.get("only_at_phi90")]
    return dict(
        question="Is 'geometry does not move the link budget' an artefact of phi=90 deg?",
        headline=(
            "NO for the operational claim, YES for the one number that was quoted. Holding sigma "
            "constant (pure geometry), R90 moves by at most "
            f"{max(_span(fixed[m])['span_pct_of_phi90'] for m in MODES):.2f} % over the full 360 deg "
            "of scene azimuth, and phi=90 deg is the MINIMUM - the published range is the "
            "conservative end. What IS specific to phi=90 deg is the 0.118 dB spread-term number "
            "itself (it reaches 23.17 dB at phi=180 deg) and the in-scene SNR ceiling (+17 dB), but "
            "both extrema live at short range where the link is already far above threshold, so "
            "neither reaches the detection-range answer. The large phi dependence one actually sees "
            "in a raw R90-vs-phi plot (up to 28 dB-equivalent) is the drone's RCS ASPECT pattern, "
            "not geometry: it vanishes in both the constant-sigma control and the "
            "heading-averaged arm."),
        claims=claims,
        claims_only_at_phi90=only,
        symmetry_selfcheck=sym,
        controls=dict(
            constant_sigma="sigma = 0.01 m^2 everywhere; any residual phi dependence is geometry",
            aspect_averaged="sigma from the grid but R90 averaged over 72 headings; removes the "
                            "drone azimuth pattern",
            reading="If a quantity is flat in BOTH controls but swings in the raw sigma-grid arm, "
                    "its phi dependence is aspect, not geometry."),
        caveats=[
            "The sigma grid (outputs/report13_sigma_grid.json, generated "
            f"{(D['meta'].get('sigma_file_generated'))}, git "
            f"{D['meta'].get('sigma_file_git_rev')}) PRE-DATES the 2026-07-31 mesh rebuild. Absolute "
            "RCS levels and therefore absolute R90 values are STALE - only the phi-relative reading "
            "is used here.",
            "The sigma grid stores elevations 0 to -20 deg only. "
            f"{100.0 * float(np.nanmax(np.array(ga['frac_el_outside_sigma_grid'], float))):.1f} % of "
            "d-cells fall outside it at the worst phi (4.6 % even at phi=90 deg) and are clamped to "
            "the -20 deg row; every one of the 72 phi has at least one clamped lookup. This affects "
            "the sigma-grid arm only - the constant-sigma control is immune.",
            "The Pd=0.9 threshold 11.861 dB is reused verbatim from the published run, which "
            "applied the W1 transfer curve to all three modes. 5G G1 has no measurable transfer "
            "curve at all (SSB M=5 makes the whole dopoff grid infeasible), so its detection "
            "numbers rest on a borrowed threshold.",
            "Coverage C is evaluated at d = R90, which makes it self-referential; see claim C10.",
            "Only phi was swept. L=500 m, altitude 60 m, speed 5 m/s, T_CPI=0.1 s, N=1 and the "
            "declared EIRP/NF budget are all held at their headline values, and the interaction of "
            "phi with those axes is not measured.",
            "The monostatic arm here is the geometry_grid.py convention (the monostatic node placed "
            "at the illuminator for N3, at the receiver for N2). It carries no DPI or "
            "self-interference ledger - it is a pure spread-term comparison.",
            "Three drones (mini5pro, mavic4pro, s1000plus) of the seven in the sigma grid.",
        ])


def main():
    with open(JSON_PATH) as f:
        D = json.load(f)
    D["verdict"] = build(D)
    tmp = JSON_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(D, f)
    os.replace(tmp, JSON_PATH)
    v = D["verdict"]
    print(v["headline"])
    print("\n[φ=90° 에서만 성립]")
    for c in v["claims_only_at_phi90"]:
        print("  ·", c)
    print("\n[전체 판정]")
    for c in v["claims"]:
        print(f"  {c['id']}: {c['verdict'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
