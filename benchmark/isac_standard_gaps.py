#!/usr/bin/env python
"""ISAC 표준 결손 3건의 **수치 원장** — XPR · UMa-AV 기하 · TR 38.765 §9.

`prior_work/isac_standard_scenarios.md` §⑩⑪⑫ 가 인용하는 수를 전부 여기서 만든다.
서술은 그 문서에, 수는 여기에.

원문 근거 (전부 1차자료 축자 확인, 접근일 2026-08-11):
  · 3GPP TR 38.901 V19.4.0 §7.9.2.1 / §7.9.2.2 / §7.9.4.1  (38901-j40.zip)
  · 3GPP TR 38.765 V20.0.0 §4 / §5 / §6 / §9 / Annex A      (38765-k00.zip)
  · 3GPP TR 36.777 V15.0.0 Annex B / B.1.1 / B.1.3          (36777-f00.zip)

⛔ GPU 미사용. numpy 만 쓴다.
⛔ src/materials.py 는 모듈 최상단에서 `import sionna.rt` 를 하므로 임포트하지 않는다.
   프레넬 두 줄만 materials.py:259-279 에서 **값을 바꾸지 않고** 옮겼다.

실행:  PYTHONPATH=src:benchmark python benchmark/isac_standard_gaps.py
산출:  outputs/isac_standard_gaps.json
"""
from __future__ import annotations

import json
import os
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "isac_standard_gaps.json")

SEED = 20260811


# ─────────────────────────────────────────────────────────────────────────────
# ① XPR — TR 38.901 eq 7.9.2-5 / 7.9.4-4 의 CPM 대 우리 스칼라 커널
# ─────────────────────────────────────────────────────────────────────────────
MU_XPR, SD_XPR = 13.75, 7.07          # Table 7.9.2.2-1, UAV
D_LOS = np.diag([1.0, -1.0]).astype(complex)   # §7.9.4.1 Step 14, LOS 링크 CPM

V = np.array([1.0, 0.0])                       # θ (수직편파)
H = np.array([0.0, 1.0])                       # φ (수평편파)
P45 = np.array([1.0, 1.0]) / np.sqrt(2.0)      # +45° 슬랜트
M45 = np.array([1.0, -1.0]) / np.sqrt(2.0)     # −45° 슬랜트


def _cpm_target(rng, n, random_kappa=True):
    """eq 7.9.2-5: [[e^{jΦθθ}, √(κ⁻¹)e^{jΦθφ}], [√(κ⁻¹)e^{jΦφθ}, e^{jΦφφ}]].

    Φ 넷은 전부 독립 U(−π,π) (§7.9.4.1 Step 13 축자)."""
    kap = (10 ** (rng.normal(MU_XPR, SD_XPR, n) / 10) if random_kappa
           else np.full(n, 10 ** (MU_XPR / 10)))
    b = 1.0 / np.sqrt(kap)
    ph = rng.uniform(-np.pi, np.pi, (n, 4))
    C = np.empty((n, 2, 2), complex)
    C[:, 0, 0] = np.exp(1j * ph[:, 0])
    C[:, 0, 1] = b * np.exp(1j * ph[:, 1])
    C[:, 1, 0] = b * np.exp(1j * ph[:, 2])
    C[:, 1, 1] = np.exp(1j * ph[:, 3])
    return C


def _chain(C):
    """CPM_rx · CPM_tgt · CPM_tx (양쪽 LOS) 뒤 eq 7.9.4-4 의 정규화
    ÷ sqrt((|d^θθ|² + |d^φφ|²)/2)."""
    M = np.einsum("ij,njk,kl->nil", D_LOS, C, D_LOS)
    nrm = np.sqrt((np.abs(M[:, 0, 0]) ** 2 + np.abs(M[:, 1, 1]) ** 2) / 2.0)
    return M / nrm[:, None, None]


def _port(M, frx, ftx):
    return np.einsum("i,nij,j->n", frx.conj(), M, ftx)


def xpr_block(n=4_000_000):
    rng = np.random.default_rng(SEED)
    M_ln = _chain(_cpm_target(rng, n, True))
    M_fx = _chain(_cpm_target(rng, n, False))
    Ms = _chain(np.tile(np.eye(2, dtype=complex), (1, 1, 1)))   # 우리 커널: CPM = I

    def pw(M, fr, ft):
        return float(np.mean(np.abs(_port(M, fr, ft)) ** 2))

    ref = pw(Ms, V, V)
    # ⚠ ±inf 는 표준 JSON 이 아니다 — 문자열 표지로 낸다(다른 언어 파서가 죽지 않게).
    db = lambda x: (float(10 * np.log10(x / ref)) if x / ref > 1e-12 else "-inf")

    ports = {}
    for name, fr, ft in [("V_to_V", V, V), ("V_to_H", H, V),
                         ("p45_to_p45", P45, P45), ("p45_to_m45", M45, P45)]:
        ports[name] = {
            "3gpp_kappa_lognormal_db": db(pw(M_ln, fr, ft)),
            "3gpp_kappa_fixed_at_mu_db": db(pw(M_fx, fr, ft)),
            "our_scalar_kernel_db": db(pw(Ms, fr, ft)),
        }

    def eff_xpr(M, fco, fcr, ftx):
        pc, px = pw(M, fco, ftx), pw(M, fcr, ftx)
        return float(10 * np.log10(pc / px)) if px > 1e-12 else "+inf"

    X = rng.normal(MU_XPR, SD_XPR, n)
    inv = float(np.mean(10 ** (-X / 10)))

    return {
        "source": "TR 38.901 V19.4.0 Table 7.9.2.2-1 (UAV) + eq 7.9.2-5 + eq 7.9.4-4",
        "mu_xpr_db": MU_XPR, "sigma_xpr_db": SD_XPR,
        "n_monte_carlo": n,
        "port_power_db_ref_copol_scalar": ports,
        "effective_xpr_db": {
            "3gpp_kappa_lognormal": {
                "basis_V_H": eff_xpr(M_ln, V, H, V),
                "basis_slant45": eff_xpr(M_ln, P45, M45, P45)},
            "3gpp_kappa_fixed_at_mu": {
                "basis_V_H": eff_xpr(M_fx, V, H, V),
                "basis_slant45": eff_xpr(M_fx, P45, M45, P45)},
            "our_scalar_kernel": {"basis_V_H": "+inf", "basis_slant45": "+inf",
                                  "why_ko": "교차편파 항이 구조적으로 0 이다"},
        },
        "dual_pol_bs_single_port_loss_db": {
            "3gpp_kappa_lognormal": float(
                10 * np.log10(pw(M_ln, P45, P45)
                              / (pw(M_ln, P45, P45) + pw(M_ln, M45, P45)))),
            "our_scalar_kernel": float(
                10 * np.log10(pw(Ms, P45, P45)
                              / (pw(Ms, P45, P45) + pw(Ms, M45, P45)))),
        },
        "kappa_distribution": {
            "P_xpr_below_0dB": float(np.mean(X < 0)),
            "P_xpr_below_3dB": float(np.mean(X < 3)),
            "P_xpr_above_20dB": float(np.mean(X > 20)),
            "E_inv_kappa": inv,
            "power_domain_effective_xpr_db": float(-10 * np.log10(inv)),
            "note_ko": ("σ_XPR=7.07 dB 의 로그정규 꼬리 때문에 전력영역 유효 XPR 이 "
                        "μ 보다 낮다. μ 를 그대로 링크버짓에 쓰면 안 된다."),
        },
        "propagation_xpr_uma_db": {
            "source": "TR 38.901 Table 7.5-6 Part-1, UMa 열",
            "LOS": {"mu": 8.0, "sigma": 4.0},
            "NLOS": {"mu": 7.0, "sigma": 3.0},
            "note_ko": ("표적 XPR(13.75/7.07) 과 **다른 수**다. 전파 XPR 은 "
                        "CPM_tx·CPM_rx (eq 7.9.4-7/-8) 에 들어가고 표적 XPR 은 "
                        "CPM_target (eq 7.9.4-6) 에 들어간다. 셋이 곱해진다."),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# ② 우리 커널이 계산하고 버리는 편파 대비 (materials.py:259-279 식 그대로)
# ─────────────────────────────────────────────────────────────────────────────
EPS0 = 8.8541878128e-12
MATS = {                      # src/materials.py::MATERIALS 의 유전체 항목
    "plastic": dict(er=2.7, sg=0.02),
    "plastic_blue": dict(er=2.7, sg=0.02),
    "prop_plastic": dict(er=2.7, sg=0.02),
    "carbon": dict(er=5.0, sg=3.0e3),
    "absorber": dict(er=1.4, sg=1.2),
}


def _fresnel(cos_i, er, sigma, fc):
    w = 2 * np.pi * fc
    erc = er - 1j * sigma / (w * EPS0)
    ci = np.clip(np.asarray(cos_i, float), 0.0, 1.0)
    sq = np.sqrt(erc - (1.0 - ci ** 2))
    return (ci - sq) / (ci + sq), (erc * ci - sq) / (erc * ci + sq)


def te_tm_block(fc=3.5e9):
    th = np.arange(0.0, 90.0, 0.25)
    ci = np.cos(np.radians(th))
    out = {}
    for k, v in MATS.items():
        te, tm = _fresnel(ci, v["er"], v["sg"], fc)
        r = 20 * np.log10(np.abs(te) / np.maximum(np.abs(tm), 1e-18))
        g = np.sqrt((np.abs(te) ** 2 + np.abs(tm) ** 2) / 2.0)   # materials.py:276
        dte = 20 * np.log10(np.abs(te) / g)
        dtm = 20 * np.log10(np.abs(tm) / np.maximum(g, 1e-18))
        i = int(np.argmax(np.abs(r)))
        pick = lambda a: float(r[int(np.argmin(np.abs(th - a)))])
        out[k] = {
            "contrast_db_at_deg": {"0": pick(0), "30": pick(30), "60": pick(60),
                                   "75": pick(75), "85": pick(85)},
            "contrast_max_abs_db": float(r[i]), "contrast_max_at_deg": float(th[i]),
            "poweravg_vs_TE_worst_db": float(dte[int(np.argmax(np.abs(dte)))]),
            "poweravg_vs_TM_worst_db": float(dtm[int(np.argmax(np.abs(dtm)))]),
        }
    return {
        "definition": "20*log10(|Gamma_TE| / |Gamma_TM|) per facet, and the error the "
                      "power-average scalar makes against each polarisation",
        "fc_hz": fc,
        "code_ref": "src/materials.py:259-279 (_fresnel_te_tm, gamma_shape)",
        "metal_like_note_ko": ("metal·pcb·camera_assembly 는 itu='metal' PEC 근사라 "
                               "|Γ_TE|=|Γ_TM| 이고 대비가 0 dB 다."),
        "scope_ko": ("⚠ 이것은 **면 단위 상한**이다. 표적 전체 σ 에 얼마가 남는지는 "
                     "편파 커널이 없어서 **측정하지 못했다**. 브루스터 널은 각도폭이 좁고 "
                     "면들이 평균되므로 이 수를 표적 σ 오차로 읽으면 안 된다."),
        "not_comparable_to_xpr_ko": ("이 대비는 동일편파 두 성분의 비(S_θθ 대 S_φφ)이고 "
                                     "3GPP κ 는 교차편파 누설(|S_θφ|²/|S_θθ|²)이다. "
                                     "우리 커널에는 S_θφ 를 만드는 경로가 없다."),
        "by_material": out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ③ UMa-AV 표적 드롭 기하 (TR 38.765 Annex A Table A-1 baseline)
# ─────────────────────────────────────────────────────────────────────────────
ISD, H_BS, H_LO, H_HI, D3_MIN = 500.0, 25.0, 25.0, 300.0, 10.0

# 실측 R90 (3.5 GHz · EIRP 12 dBm, chamber class)
# ⟨outputs/md_snr_vs_range.json :: observability_measured⟩
R90_M = {"mavic4pro": 72.542, "s1000plus": 51.2, "matrice4e": 22.1,
         "mini5pro": 15.745, "phantom4": 15.4}


def _drop(rng, n):
    R = ISD / np.sqrt(3.0)
    acc, need = [], n
    while need > 0:
        x = rng.uniform(-R, R, need * 2)
        y = rng.uniform(-R, R, need * 2)
        ax, ay = np.abs(x), np.abs(y)
        ok = (ay <= np.sqrt(3) / 2 * R) & (np.sqrt(3) * ax + ay <= np.sqrt(3) * R)
        acc.append(np.stack([x[ok], y[ok]], 1))
        need -= int(ok.sum())
    P = np.concatenate(acc)[:n]
    d2 = np.hypot(P[:, 0], P[:, 1])
    ang = np.degrees(np.arctan2(P[:, 1], P[:, 0])) % 360
    sec = (ang >= 330) | (ang < 90)                     # 3섹터 중 하나 (120°)
    d2 = d2[sec]
    h = rng.uniform(H_LO, H_HI, d2.size)
    d3 = np.hypot(d2, h - H_BS)
    k = d3 >= D3_MIN
    return d2[k], h[k], d3[k]


def umaav_block(n=2_000_000):
    rng = np.random.default_rng(SEED)
    d2, h, d3 = _drop(rng, n)
    el = -np.degrees(np.arctan2(h - H_BS, d2))          # 우리 규약: belly = 음수
    q = lambda a, p: float(np.percentile(a, p))

    res = {
        "source": "TR 38.765 V20.0.0 Annex A Table A-1 (FR1 baseline)",
        "assumptions": {"isd_m": ISD, "bs_height_m": H_BS,
                        "target_height_m": [H_LO, H_HI],
                        "min_bs_target_3d_m": D3_MIN,
                        "layout": "hexagonal grid, 7 macro sites, 3 sectors per site",
                        "targets": "N=5 per sector, centre site only, uniform in sector"},
        "n_samples": int(d3.size),
        "d2d_m": {"p5": q(d2, 5), "median": q(d2, 50), "p95": q(d2, 95),
                  "max": float(d2.max())},
        "height_m": {"p5": q(h, 5), "median": q(h, 50), "p95": q(h, 95)},
        "d3d_m": {"p5": q(d3, 5), "median": q(d3, 50), "p95": q(d3, 95),
                  "max": float(d3.max())},
        "elevation_deg_our_convention": {
            "p5": q(el, 5), "median": q(el, 50), "p95": q(el, 95),
            "min": float(el.min()), "max": float(el.max()),
            "convention_ko": "belly view = 음수. gNB(25 m)가 표적(25~300 m)을 올려다본다."},
        "frac_el_within_0_to_minus20": float(np.mean(el > -20.0)),
        "frac_el_below_minus20": float(np.mean(el <= -20.0)),
        "frac_el_below_minus57": float(np.mean(el <= -57.0)),
    }

    scale = 10 ** ((63.0 - 12.0) / 40.0)     # R ∝ EIRP^(1/4), 단일정적 1/R⁴
    res["eirp_scale_63dBm_over_12dBm"] = float(scale)
    res["frac_targets_within_R90"] = {
        "eirp_12dBm_chamber": {k: float(np.mean(d3 <= v)) for k, v in R90_M.items()},
        "eirp_63dBm_macro": {k: float(np.mean(d3 <= v * scale))
                             for k, v in R90_M.items()},
        "R90_source": "outputs/md_snr_vs_range.json :: observability_measured",
        "caveat_ko": ("TR 38.765 의 52/37 dBm 은 **도통 전력**이고 배열 이득은 "
                      "ITU-R M.2412 Table 9 패턴에 맡긴다. 우리 63 dBm 은 EIRP "
                      "선언값이라 두 수를 직접 같다고 놓을 수 없다."),
    }

    # 우리 σ 격자 el 확장의 의미 — 옛 −20° 클램프 편향을 UMa-AV 분포로 가중
    try:
        v = json.load(open(os.path.join(ROOT, "outputs",
                                        "sigma_el_extend_verify.json")))
        by = v["clamp_direction"]["by_el"]
        er = np.array(sorted((float(k) for k in by), reverse=True))
        mb = np.array([by[f"{int(e)}"]["mean_db"] if f"{int(e)}" in by
                       else by[str(e)]["mean_db"] for e in er])
        idx = np.argmin(np.abs(el[:, None] - er[None, :]), axis=1)
        w = np.bincount(idx, minlength=er.size).astype(float)
        w /= w.sum()
        res["our_sigma_grid_el"] = {
            "grid_rows_deg": [float(x) for x in er],
            "umaav_weight_per_row": {str(int(e)): float(ww) for e, ww in zip(er, w)},
            "clamp_bias_weighted_by_umaav_db": float(np.sum(w * mb)),
            "clamp_rms_db": v["clamp_error"]["rms_db"],
            "clamp_level_only_rms_db": v["clamp_error"]["level_only"]["rms_db"],
            "clamp_max_abs_db": v["clamp_error"]["max_abs_db"],
            "reading_ko": ("가중 평균 편향은 −0.03 dB 로 거의 0 이다 — 옛 −20° 클램프는 "
                           "**레벨 편향이 아니라 산포**였다. 표적 하나하나로는 "
                           "rms 6.23 dB 틀렸다."),
            "source": "outputs/sigma_el_extend_verify.json",
        }
    except Exception as exc:                                   # pragma: no cover
        res["our_sigma_grid_el"] = {"unavailable": repr(exc)}

    for B, name in [(100e6, "5G NR 100 MHz"), (20e6, "LTE 20 MHz"),
                    (80e6, "WiFi 80 MHz")]:
        res.setdefault("range_resolution_m", {})[name] = float(3e8 / (2 * B))
    res["range_resolution_note_ko"] = ("TR 38.765 Table 4.2-1 의 수평/수직 정확도 목표는 "
                                       "10 m 다. FR1 대역폭 100 MHz 는 규격과 우리가 같다.")
    return res


def main():
    t0 = time.time()
    doc = {
        "_meta": {
            "title": "3GPP ISAC 표준 결손 3건의 수치 원장 (XPR · UMa-AV · TR 38.765 §9)",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "script": "benchmark/isac_standard_gaps.py",
            "prose": "prior_work/isac_standard_scenarios.md §⑩⑪⑫⑬",
            "gpu_used": False,
            "primary_sources": [
                "3GPP TR 38.901 V19.4.0 (2026-06) — 38901-j40.zip",
                "3GPP TR 38.765 V20.0.0 (2026-06) — 38765-k00.zip",
                "3GPP TR 36.777 V15.0.0 (2018-01) — 36777-f00.zip",
            ],
            "accessed": "2026-08-11",
        },
        "xpr": xpr_block(),
        "our_kernel_polarisation": te_tm_block(),
        "umaav_geometry": umaav_block(),
        "tr38765_clause9": {
            "source": "TR 38.765 V20.0.0 §9 (축자)",
            "baseline1": {"tx_power_dbm": 52, "antenna_isolation_db": 80,
                          "multi_or_all_trp": "9/10 sources",
                          "single_trp": "3/11 sources"},
            "baseline2": {"tx_power_dbm": 37, "antenna_isolation_db": 65,
                          "multi_or_all_trp": "7/9 sources",
                          "single_trp": "2/9 sources"},
            "measurement_levels": {
                "A": "not supported (transport capacity)",
                "C": "agreed for specification in a potential future normative phase",
                "D": "conditional on privacy/security resolution by appropriate WG(s)"},
            "protocol": {"sensing_data": "Option 1 (SCTP-based)",
                         "control_plane": "dedicated NsAP between gNB and SenF"},
            "results_pointers": {"results": "R1-2601668", "assumptions": "R1-2601669",
                                 "excel": "R1-2601610"},
            "n_results": {"baseline1": 46, "baseline2": 29, "other": 55,
                          "total": 130,
                          "bistatic": 0,
                          "note_ko": "130 건 전부 gNB 모노스태틱이다. 바이스태틱 평가는 0 건."},
            "performance_objectives": {
                "missed_detection": 0.05, "false_alarm_type1": 0.05,
                "false_alarm_type2": 0.05,
                "horizontal_accuracy_m_at_90pct": 10.0,
                "vertical_accuracy_m_at_90pct": 10.0,
                "velocity_accuracy_mps_at_90pct": 5.0},
            "not_metrics_ko": ("§4.1 축자: 'Sensing resolution, sensing service latency "
                               "and refreshing rate are not considered as performance "
                               "metrics for the evaluation of NR ISAC.'"),
        },
    }
    doc["_meta"]["runtime_s"] = round(time.time() - t0, 2)
    with open(OUT, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024:.1f} kB, "
          f"{doc['_meta']['runtime_s']} s)")


if __name__ == "__main__":
    main()
