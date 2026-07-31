# -*- coding: utf-8 -*-
"""
make_report02_target.py — 리포트 02 「표적 모델」 빌더  →  report02_target.ipynb
============================================================================================
계약서: `docs/REBUILD_2026-07-30.md` (골격 §2, 서술규약 §5). 규약 강제는 `src/report_style.py`.

이 파일이 하는 일 (한 번 실행하면 셋 다 나온다)
  ① **파생 JSON** `outputs/report02_derived.json` — 리포트가 인용하는데 원본 JSON 에 *값으로*
     들어있지 않은 양들을 여기서 계산해 **디스크에 남긴다**. 손으로 친 숫자를 0개로 만들기 위한
     장치다. 계산하는 것은 넷뿐이고, 입력·정의·공식을 JSON 안 `_meta` 에 함께 적는다:
       · 기체별 **외접구 반경 r** 과 밴드별 전기적 크기 kr   (메쉬에서 직접)
       · **해석 PO ↔ 정확 Mie** 간극이 1.0 / 0.5 / 0.2 dB 아래로 내려가는 kr (기준해 두 개로)
       · 기체별 **밴드 기울기** dB/GHz (rcs_anchor.json 의 3밴드 방위평균 σ 를 1차 적합)
       · **앵커 원장 요약** — 재보정이 옮긴 양의 범위·패턴 불변량·비교가능성 판정 집계
         (`outputs/sigma_anchor.json` 을 읽어 집계만 한다. 앵커 자체는 `src/sigma_anchor.py`)
  ② **그림 3장** — kr 스윕 · 전기적 크기 · 밴드 기울기(앵커 전후). 나머지 5장은 이미 있는 PNG.
  ③ **노트북** `report02_target.ipynb`.

실행
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report02_target.py

읽는 것 (전부 저장소에 이미 있는 실험 산출물)
  outputs/report1.json · report2_waveform_rcs.json · report3_rt.json · report6_sbr.json
  outputs/rcs_anchor.json · sigma_anchor.json · sbr_kr_sweep.json
  outputs/real_cad_compare.json · community_compare.json · phantom4_scan_compare.json

무결성 장치
  · `derive()` 는 밴드 정의를 `rcs_anchor.json:meta.bands` 와 대조하고, 자체 적합한 밴드 기울기를
    `sigma_anchor.json` 이 독립으로 적합한 값과 대조한다. 어긋나면 **거기서 멈춘다**.
  · 리포트 숫자는 전부 `report_style.num()`/`table_from()` 을 통과한다 — JSON 을 열어 대조한다.

⚠ GPU 도 Sionna 도 필요 없다. 메쉬 빌드(`drones.build_drone`)와 numpy/scipy 만 쓴다(약 20 초).
"""
from __future__ import annotations

import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                    # noqa: E402
import matplotlib                                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                       # noqa: E402

from report_style import (assert_fig_text, build_notebook, caption,    # noqa: E402
                          code, from_json, header, limits, md, table, table_from)

C0 = 299792458.0
FIGDIR = os.path.join(_ROOT, "outputs", "figures")
DERIVED = os.path.join(_ROOT, "outputs", "report02_derived.json")
NB_OUT = os.path.join(_ROOT, "report02_target.ipynb")

#: 리포트 전체가 쓰는 세 밴드. 값은 rcs_anchor.json:meta.bands 와 같아야 하며 아래서 검사한다.
BANDS = {"LTE": 1.843e9, "5G": 3.500e9, "WiFi": 5.210e9}

#: §1 표에 올리는 기체 순서 — 전기적으로 작은 것부터. mini5pro·matrice4e 가 실측 대상.
DRONE_ORDER = ["mini5pro", "phantom4", "mavic4pro", "matrice4e",
               "typhoonh480", "x500v2", "s1000plus"]

#: 앵커 재보정 모드. 크기법칙(L²/L⁴)을 **쓰지 않는** 모드를 생산 기준으로 삼는다 —
#: 크기전이가 앵커의 가장 약한 고리이기 때문이다(sigma_anchor.json:uncontrolled 참조).
ANCHOR_MODE = "slope_only"


# =========================================================================== #
#  ①  파생값 — 리포트가 인용할 수 있도록 디스크에 남긴다
# =========================================================================== #
def _enclosing_radius(mesh) -> float:
    """**외접구 반경**: bbox 중심에서 가장 먼 정점까지의 거리 [m].

    정의를 하나로 고정하는 것이 목적이다. bbox 대각선의 절반은 빈 모서리까지 세어 과대평가하고,
    최대 치수의 절반은 과소평가한다. 이 정의는 메쉬 정점만으로 결정되어 재현이 쉽다.
    """
    V = np.asarray(mesh.v, float)
    c = 0.5 * (V.min(0) + V.max(0))
    return float(np.linalg.norm(V - c, axis=1).max())


def _po_mie_floor(kr_max=60.0, step=0.01):
    """**해석 PO 기준해**와 **정확 Mie 기준해**의 간극이 임계값 아래로 내려가는 kr.

    둘 다 우리 결과가 아니라 **기준해**다(`benchmark/mie_pec_sphere.py` 파일 머리말).
    반환하는 kr 은 "그 위로는 다시 임계를 넘지 않는" 마지막 교차점 바로 다음 격자점이다.
    """
    from mie_pec_sphere import mie_pec_backscatter_norm, po_sphere_norm
    kr = np.arange(1.0, kr_max + 1e-9, step)
    mie = np.array([mie_pec_backscatter_norm(float(x)) for x in kr])
    po = np.asarray(po_sphere_norm(kr), float)
    d_db = 10.0 * np.log10(po / mie)
    out = {}
    for thr, name in ((1.0, "kr_below_1p0_db"), (0.5, "kr_below_0p5_db"),
                      (0.2, "kr_below_0p2_db")):
        idx = np.where(np.abs(d_db) > thr)[0]
        out[name] = float(kr[idx[-1] + 1])
    lo = (kr >= 1.0) & (kr <= 3.0)
    out["max_abs_db_kr1_to_3"] = float(np.abs(d_db[lo]).max())
    out["grid_step"] = step
    out["kr_scan_max"] = kr_max
    return out, kr, d_db


def _band_slope(anchor):
    """기체별 **밴드 기울기** dB/GHz — 세 밴드의 방위평균 σ(el=0°)를 주파수에 1차 적합."""
    fb = np.array([anchor["meta"]["bands"][k] / 1e9
                   for k in anchor["meta"]["bands"]], float)
    out = {}
    for key, rec in anchor["drones"].items():
        mu = np.array([rec["bands"][b]["el0"]["mean_dbsm"]
                       for b in anchor["meta"]["bands"]], float)
        out[key] = float(np.polyfit(fb, mu, 1)[0])
    return out, [float(x) for x in fb]


def _anchor_ledger(sa, slope_ours):
    """`outputs/sigma_anchor.json` 을 **집계만** 한다 — 앵커 계산 자체는 src/sigma_anchor.py.

    담는 것: 재보정이 옮긴 양의 범위(어느 기체·어느 밴드가 최대/최소인가), 각도패턴이
    정말 안 움직였는지(불변량), 비교가능성 판정 집계, 최대 미통제항.
    """
    D = sa["drones"]

    # ── 자체 적합 기울기 ↔ 앵커 모듈의 독립 적합 대조 (어긋나면 멈춘다) ────────────
    worst = 0.0
    for k, rec in D.items():
        worst = max(worst, abs(rec["slope_ours_3band_db_per_ghz"] - slope_ours[k]))
    assert worst < 1e-6, f"밴드 기울기 불일치: 최대 {worst:.3e} dB/GHz"

    # ── 재보정이 옮긴 양 (밴드별 Δ) ─────────────────────────────────────────────
    cells = [(rec["modes"][ANCHOR_MODE]["delta_db"][b], k, b)
             for k, rec in D.items() for b in rec["modes"][ANCHOR_MODE]["delta_db"]]
    lo, hi = min(cells), max(cells)

    verdicts = {k: rec["comparability"]["verdict"] for k, rec in D.items()}
    n_v = {v: sum(1 for x in verdicts.values() if x == v)
           for v in ("direct", "scaled", "not_comparable")}

    unc = [u for u in sa["uncontrolled"] if u.get("size_db")]
    big = max(unc, key=lambda u: abs(u["size_db"]))

    slope_after = {k: rec["modes"][ANCHOR_MODE]["slope_after_db_per_ghz"]
                   for k, rec in D.items()}
    shape = max(rec["shape_invariance_max_abs_db"] for rec in D.values())

    return {
        "mode": ANCHOR_MODE,
        "mode_note": D[DRONE_ORDER[0]]["modes"][ANCHOR_MODE]["pivot_note"],
        "anchor_id": sa["sources"]["default_anchor"],
        "anchor_platform": sa["sources"]["anchors"][sa["sources"]["default_anchor"]]["platform"],
        "correction_max_db": hi[0], "correction_max_drone": hi[1], "correction_max_band": hi[2],
        "correction_min_db": lo[0], "correction_min_drone": lo[1], "correction_min_band": lo[2],
        "correction_abs_max_db": max(abs(lo[0]), abs(hi[0])),
        "slope_after_db_per_ghz": float(np.mean(list(slope_after.values()))),
        "slope_after_spread_db_per_ghz": float(np.ptp(list(slope_after.values()))),
        "shape_invariance_max_abs_db": shape,
        "verdicts": verdicts,
        "n_direct": n_v["direct"], "n_scaled": n_v["scaled"],
        "n_not_comparable": n_v["not_comparable"],
        "largest_uncontrolled_term": big["term"],
        "largest_uncontrolled_db": abs(float(big["size_db"])),
        "applied_to_kernel": False,
        "applied_note": ("커널(`src/rcs_sbr.py`)은 그대로다. 재보정은 σ 원장(ledger)이고, "
                         "밴드 간 비교는 이 원장 위에서 읽는다(05편)."),
    }


def derive(verbose=True) -> dict:
    """파생 JSON 을 계산해 `outputs/report02_derived.json` 에 쓴다."""
    t0 = time.time()
    import drones                                     # GPU·Sionna 불필요

    anchor = json.load(open(os.path.join(_ROOT, "outputs", "rcs_anchor.json")))
    sa = json.load(open(os.path.join(_ROOT, "outputs", "sigma_anchor.json")))
    # 밴드 정의가 앵커와 어긋나면 여기서 멈춘다 — 조용히 다른 주파수를 쓰는 일이 없도록.
    for short, f in BANDS.items():
        hit = [v for k, v in anchor["meta"]["bands"].items() if k.startswith(short)]
        assert hit and abs(hit[0] - f) < 1e3, f"밴드 불일치: {short} {f} vs {hit}"

    air = {}
    for key in DRONE_ORDER:
        spec = drones.DRONES[key]
        mesh = drones.build_drone(spec)
        r = _enclosing_radius(mesh)
        rec = dict(name=spec.name, n_rotors=int(spec.num_rotors),
                   diagonal_mm=float(spec.diagonal_mm), weight_g=float(spec.weight_g),
                   prop_dia_mm=float(spec.prop_dia_mm), n_tris=int(mesh.n_tris()),
                   n_groups=len(mesh.groups()), r_encl_m=r, release=spec.release)
        for b, f in BANDS.items():
            rec[f"kr_{b}"] = float(2.0 * np.pi * r / (C0 / f))
        air[key] = rec
        if verbose:
            print(f"  {key:12s} r={r:.4f} m  kr(LTE)={rec['kr_LTE']:.2f}")

    krs = [(air[k][f"kr_{b}"], k, b) for k in air for b in BANDS]
    kmin, kmax = min(krs), max(krs)

    floor, kr_grid, d_db = _po_mie_floor()
    # PO 모델 간극이 1 dB 를 넘는(= 기준해 구에서조차 편치 않은) 기체·밴드 조합
    below = [(k, b) for (v, k, b) in krs if v < floor["kr_below_1p0_db"]]

    slope, fb = _band_slope(anchor)
    das = float(anchor["literature"]["mu_eps"]["multiband_phantom3"]["mu_a"])
    m3d = float(anchor["literature"]["mu_eps"]["mono3d_theta90"]["mu_a"])
    ratio = {k: v / das for k, v in slope.items()}

    rt = json.load(open(os.path.join(_ROOT, "outputs", "report3_rt.json")))
    A = rt["A_rays"]["rows"]

    J = {
        "_meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "src/make_report02_target.py :: derive()",
            "purpose": "리포트 02 가 인용하는 파생값. 원본 JSON 에 값으로 없는 것만 담는다.",
            "inputs": ["outputs/rcs_anchor.json", "outputs/sigma_anchor.json",
                       "outputs/report3_rt.json", "src/drones.py (메쉬 정의)",
                       "benchmark/mie_pec_sphere.py (기준해 두 개)"],
            "definitions": {
                "r_encl_m": "외접구 반경 = bbox 중심에서 가장 먼 메쉬 정점까지의 거리 [m]",
                "kr_*": "2*pi*r_encl/lambda — 밴드 중심주파수 기준 전기적 크기",
                "po_floor": "해석 PO 기준해 / 정확 Mie 기준해 의 dB 차가 임계 아래로 "
                            "내려가는 kr. 둘 다 우리 결과가 아니라 기준해다.",
                "band_slope": "세 밴드(1.843/3.5/5.21 GHz)의 방위평균 sigma(el=0deg)를 "
                              "주파수[GHz]에 1차 적합한 기울기 [dB/GHz]",
                "anchor": "outputs/sigma_anchor.json 의 재보정 원장 집계. 앵커 계산 자체는 "
                          "src/sigma_anchor.py 가 한다.",
            },
            "runtime_s": None,
        },
        "airframes": air,
        "bands_ghz": {k: v / 1e9 for k, v in BANDS.items()},
        "electrical": {
            "n_airframe_band": len(krs),
            "kr_min": kmin[0], "kr_min_drone": kmin[1], "kr_min_band": kmin[2],
            "kr_min_name": air[kmin[1]]["name"],
            "kr_max": kmax[0], "kr_max_drone": kmax[1], "kr_max_band": kmax[2],
            "kr_max_name": air[kmax[1]]["name"],
            "n_below_po_1db": len(below),
            "below_po_1db": [f"{k} @ {b}" for k, b in below],
        },
        "po_floor": floor,
        "band_slope": {
            "fit_bands_ghz": fb, "n_fit": len(fb), "el_deg": 0.0,
            "ours_db_per_ghz": slope,
            "ours_min": min(slope.values()), "ours_min_drone": min(slope, key=slope.get),
            "ours_max": max(slope.values()), "ours_max_drone": max(slope, key=slope.get),
            "lit_das_db_per_ghz": das,
            "lit_mono3d_db_per_ghz": m3d,
            "ratio_vs_das": ratio,
            "ratio_min": min(ratio.values()), "ratio_max": max(ratio.values()),
        },
        "anchor": _anchor_ledger(sa, slope),
        "stock_rt": {
            "coh_climb_db": float(A[-1]["coh_db"] - A[0]["coh_db"]),
            "spp_lo": int(A[0]["spp"]), "spp_hi": int(A[-1]["spp"]),
            "note": "광선을 16배 쏘면 코히런트 합이 이만큼 더 커진다 = 수렴하지 않는다",
        },
    }
    J["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    with open(DERIVED, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    if verbose:
        print(f"✅ 파생값 저장 → outputs/report02_derived.json ({J['_meta']['runtime_s']} s)")
    return J, kr_grid, d_db


# =========================================================================== #
#  ②  그림 3장 — 글자는 전부 영어(하우스 규약), assert_fig_text 로 검사
# =========================================================================== #
def _save(fig, name):
    os.makedirs(FIGDIR, exist_ok=True)
    p = os.path.join(FIGDIR, name)
    fig.savefig(p, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  🖼  outputs/figures/{name}")


def fig_electrical_size(J):
    """기체 7 × 밴드 3 = 21 조합의 kr 을, PO 근사가 얼마나 편안한 영역인지와 겹쳐 보여준다."""
    T = ["Electrical size of every airframe, against where PO is comfortable",
         "kr = 2*pi*r/lambda   (r = enclosing-sphere radius of the mesh)",
         "PO vs exact Mie gap > 1 dB", "0.5 - 1 dB", "0.2 - 0.5 dB", "< 0.2 dB",
         "LTE 1.843 GHz", "5G 3.5 GHz", "WiFi 5.21 GHz", "smallest of all 21",
         "measured in campaign 06"]
    assert_fig_text(*T)
    A, F = J["airframes"], J["po_floor"]
    keys = DRONE_ORDER
    meas = {"matrice4e", "mini5pro"}
    fig, ax = plt.subplots(figsize=(11.0, 4.4))
    edges = [1.0, F["kr_below_1p0_db"], F["kr_below_0p5_db"], F["kr_below_0p2_db"], 200.0]
    cols = ["#ffcdd2", "#ffe0b2", "#fff9c4", "#e8f5e9"]
    ax.set_ylim(-0.75, len(keys) + 0.05)
    for (a, b), c, lab in zip(zip(edges[:-1], edges[1:]), cols, T[2:6]):
        ax.axvspan(a, b, color=c, zorder=0)
        ax.text(np.sqrt(a * b), len(keys) - 0.05, lab, ha="center", va="top",
                fontsize=8, color="#555")
    mk = dict(zip(BANDS, ["o", "s", "^"]))
    cl = dict(zip(BANDS, ["#00695c", "#1565c0", "#e65100"]))
    for i, k in enumerate(keys):
        y = len(keys) - 1 - i
        v = [A[k][f"kr_{b}"] for b in BANDS]
        ax.plot([min(v), max(v)], [y, y], color="#9e9e9e", lw=1.0, zorder=2)
        for b, lab in zip(BANDS, T[6:9]):
            ax.plot(A[k][f"kr_{b}"], y, mk[b], color=cl[b], ms=7, zorder=3,
                    label=lab if i == 0 else None)
    kmin = J["electrical"]["kr_min"]
    ax.annotate(f"{T[9]}: kr = {kmin:.2f}", xy=(kmin, len(keys) - 1),
                xytext=(kmin * 0.62, len(keys) - 1.75), fontsize=9, color="#b71c1c",
                arrowprops=dict(arrowstyle="->", color="#b71c1c"))
    ax.set_yticks(range(len(keys)))
    labs = [(A[k]["name"] + (f"  [{T[10]}]" if k in meas else ""))
            for k in reversed(keys)]
    ax.set_yticklabels(labs, fontsize=9)
    for t, k in zip(ax.get_yticklabels(), reversed(keys)):
        if k in meas:
            t.set_color("#b71c1c")
            t.set_fontweight("bold")
    ax.set_xscale("log")
    ax.set_xlim(4, 150)
    ax.set_xticks([5, 10, 20, 30, 50, 100])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlabel(T[1])
    ax.set_title(T[0], fontsize=12, weight="bold")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.95)
    ax.grid(axis="x", ls=":", alpha=0.5, zorder=1)
    _save(fig, "report02_electrical_size.png")


def fig_kr_sweep(J, kr_grid, d_db):
    """(a) 두 기준해와 우리 커널  (b) 두 개의 서로 다른 오차."""
    T = ["Two reference solutions, and the two errors they measure",
         "(a) PEC sphere backscatter, normalised", "(b) the two gaps, separated",
         "kr = 2*pi*r/lambda", "sigma / (pi r^2)", "gap [dB]",
         "exact Mie  [REFERENCE SOLUTION]", "analytic PO  [REFERENCE SOLUTION]",
         "our SBR+PO kernel  (lambda/16 ray grid)",
         "ours - analytic PO   = OUR numerical error",
         "analytic PO - exact Mie   = the PO MODEL's own gap (a floor, not a bound)",
         "max |ours - PO|", "1 dB", "0.5 dB", "0.2 dB"]
    assert_fig_text(*T)
    S = json.load(open(os.path.join(_ROOT, "outputs", "sbr_kr_sweep.json")))
    rows = sorted([r for r in S["rows"] if r["div"] == 16], key=lambda r: r["kr"])
    kr = np.array([r["kr"] for r in rows])
    sb = np.array([r["sigma_sbr_m2"] / (np.pi * r["r_m"] ** 2) for r in rows])
    e_po = np.array([r["db_sbr_over_po"] for r in rows])

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.0, 4.6))
    kk = np.linspace(1, 100, 4000)
    from mie_pec_sphere import mie_pec_backscatter_norm, po_sphere_norm
    a1.plot(kk, [mie_pec_backscatter_norm(float(x)) for x in kk], color="#9e9e9e",
            lw=2.4, label=T[6], zorder=1)
    a1.plot(kk, po_sphere_norm(kk), color="#212121", lw=1.1, ls="--", label=T[7], zorder=2)
    a1.plot(kr, sb, "o", color="#1565c0", ms=6, label=T[8], zorder=3)
    a1.set_xscale("log")
    a1.set_yscale("log")
    a1.set_xlabel(T[3])
    a1.set_ylabel(T[4])
    a1.set_title(T[1], fontsize=11)
    a1.legend(fontsize=8.5, loc="lower right")
    a1.grid(ls=":", alpha=0.5)

    a2.axhline(0, color="#bdbdbd", lw=0.8)
    a2.plot(kr_grid, d_db, color="#c62828", lw=1.4, label=T[10], zorder=2)
    a2.plot(kr, e_po, "o-", color="#1565c0", ms=5, lw=1.0, label=T[9], zorder=3)
    F = J["po_floor"]
    for thr in (1.0, 0.5, 0.2):
        a2.axhline(thr, color="#e0e0e0", lw=0.8, zorder=0)
        a2.axhline(-thr, color="#e0e0e0", lw=0.8, zorder=0)
    for key, lab in (("kr_below_1p0_db", T[12]), ("kr_below_0p5_db", T[13]),
                     ("kr_below_0p2_db", T[14])):
        a2.axvline(F[key], color="#c62828", ls=":", lw=1.0, zorder=1)
        a2.text(F[key], -3.85, f"{lab} @ kr={F[key]:.2f}", rotation=90, fontsize=7.5,
                color="#c62828", ha="right", va="bottom")
    i = int(np.argmax(np.abs(e_po)))
    a2.annotate(f"{T[11]} = {abs(e_po[i]):.3f} dB", xy=(kr[i], e_po[i]),
                xytext=(1.15, -2.9), fontsize=9, color="#1565c0",
                arrowprops=dict(arrowstyle="->", color="#1565c0"))
    a2.set_xscale("log")
    a2.set_xlim(1, 100)
    a2.set_ylim(-4, 4)
    a2.set_xlabel(T[3])
    a2.set_ylabel(T[5])
    a2.set_title(T[2], fontsize=11)
    a2.legend(fontsize=8.5, loc="upper right")
    a2.grid(ls=":", alpha=0.5)
    fig.suptitle(T[0], fontsize=13, weight="bold", y=1.03)
    _save(fig, "report02_kr_sweep.png")


def fig_band_slope(J):
    """우리 밴드 기울기가 어디에 있고, 측정 앵커가 그것을 어디로 옮기는가."""
    T = ["Where the measurement anchor moves each airframe's band slope",
         "band slope  [dB / GHz]   (fit of azimuth-mean sigma at 1.843 / 3.5 / 5.21 GHz)",
         "measured: Das, IEEE WCL 2026 (anchor)", "measured: Yuan, EuCAP 2025 azimuth plane",
         "ours, raw SBR + PO (bar colour = comparability)", "x steeper than the anchor",
         "after re-levelling", "direct", "scaled", "not comparable"]
    assert_fig_text(*T)
    B, A, K = J["band_slope"], J["airframes"], J["anchor"]
    keys = sorted(B["ours_db_per_ghz"], key=lambda k: B["ours_db_per_ghz"][k])
    face = {"direct": "#1565c0", "scaled": "#78909c", "not_comparable": "#8d6e63"}
    fig, ax = plt.subplots(figsize=(11.4, 4.4))
    y = np.arange(len(keys))
    ax.barh(y, [B["ours_db_per_ghz"][k] for k in keys], height=0.62,
            color=[face[K["verdicts"][k]] for k in keys], label=T[4])
    for i, k in enumerate(keys):
        v = B["ours_db_per_ghz"][k]
        ax.annotate("", xy=(K["slope_after_db_per_ghz"], i), xytext=(v, i),
                    arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.2))
        ax.text(v + 0.04, i, f"{v:.2f}   ({B['ratio_vs_das'][k]:.1f}{T[5]})",
                va="center", fontsize=8.5, color="#0d47a1")
    ax.axvline(B["lit_das_db_per_ghz"], color="#c62828", lw=2.0, label=T[2])
    ax.axvline(B["lit_mono3d_db_per_ghz"], color="#ef6c00", lw=2.0, ls="--", label=T[3])
    ax.plot([K["slope_after_db_per_ghz"]] * len(keys), y, "o", color="#c62828",
            ms=6, label=T[6], zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels([A[k]["name"] if k in A else k for k in keys], fontsize=9)
    ax.set_xlabel(T[1])
    ax.set_xlim(0, max(B["ours_db_per_ghz"].values()) * 2.35)
    ax.set_title(T[0], fontsize=12, weight="bold")
    h = [plt.Rectangle((0, 0), 1, 1, color=face[v]) for v in
         ("direct", "scaled", "not_comparable")]
    lg = ax.legend(fontsize=8.5, loc="lower right", framealpha=0.97)
    ax.add_artist(lg)
    ax.legend(h, [T[7], T[8], T[9]], fontsize=8, loc="upper right", framealpha=0.97,
              title="comparability to the anchor platform", title_fontsize=8)
    ax.grid(axis="x", ls=":", alpha=0.5)
    _save(fig, "report02_band_slope.png")


# =========================================================================== #
#  ③  노트북 본문
# =========================================================================== #
def blocks(J):
    D = from_json("outputs/report02_derived.json")
    A = from_json("outputs/rcs_anchor.json")
    S = from_json("outputs/sbr_kr_sweep.json")
    R1 = from_json("outputs/report1.json")
    R2 = from_json("outputs/report2_waveform_rcs.json")
    R3 = from_json("outputs/report3_rt.json")
    R6 = from_json("outputs/report6_sbr.json")
    CAD = from_json("outputs/real_cad_compare.json")
    COM = from_json("outputs/community_compare.json")
    PH4 = from_json("outputs/phantom4_scan_compare.json")
    SA = from_json("outputs/sigma_anchor.json")

    B = []

    # ── 서두 6블록 ──────────────────────────────────────────────────────────
    B.append(header(
        num=2,
        title="표적 모델: 자세 구조는 기하에서, 레벨은 측정에서",
        question="드론 메쉬에서 계산한 RCS 중 무엇을 믿어도 되는가?",
        conclusion_lines=[
            f"엔진 수치는 건강하다 — 해석 PO 기준해 대비 최대 편차 "
            f"{S.num('summary_div16.max_abs_db_vs_po', 0.201, '{:.3f}', 'dB')}"
            f"(kr {S.num('summary_div16.n_points', 21, '{:.0f}')}점 × 입사 "
            f"{S.num('meta.n_incidence', 48, '{:.0f}')}방향, kr=1 까지 전부).",
            f"그래서 **자세 구조**(각도에 따른 σ 의 모양)는 기하에서 나온 것으로 방어된다 — "
            f"부품별 재질 + 광선추적 가림(가림만으로 "
            f"{R2.num('occlusion.occlusion_db', -4.2356, '{:+.2f}', 'dB')}).",
            f"**레벨과 주파수 의존성은 방어되지 않는다** — 우리 밴드 기울기는 "
            f"{D.num('band_slope.ours_min', fmt='{:.3f}')}~"
            f"{D.num('band_slope.ours_max', fmt='{:.3f}', unit='dB/GHz')} 로 측정 문헌의 "
            f"{D.num('band_slope.ratio_min', fmt='{:.1f}')}~"
            f"{D.num('band_slope.ratio_max', fmt='{:.1f}')}배 가파르다. "
            f"PO 가 f² 정반사항만 남기고 모서리 회절항(PTD)을 버리기 때문이다.",
            f"그래서 레벨·주파수는 **측정 앵커**에서 받는다(§4) — 밴드별 보정 "
            f"{D.num('anchor.correction_min_db', fmt='{:+.2f}')}~"
            f"{D.num('anchor.correction_max_db', fmt='{:+.2f}', unit='dB')}, "
            f"각도패턴 변화 "
            f"{D.num('anchor.shape_invariance_max_abs_db', fmt='{:.1e}', unit='dB')}.",
            f"⚠ 앵커는 실험실 한 곳·기체 한 대이고 최대 미통제항이 "
            f"{D.num('anchor.largest_uncontrolled_db', fmt='{:.2f}', unit='dB')} 로 "
            f"보정량보다 크다. **재보정은 검증이 아니다.**",
        ],
        claims=[
            "자세에 따른 σ 의 **구조** — 부품별 재질 + 광선추적 가림에서 나온다",
            f"커널이 해석 PO 기준해를 재현한다 — kr=1..100 전 구간 편차 ≤"
            f"{S.num('summary_div16.max_abs_db_vs_po', fmt='{:.3f}', unit='dB')}",
            "가림·재질·부품이 σ 를 얼마나 움직이는지 — 같은 메쉬에서 켜고 끈 차이",
            "**모노스태틱** 자세 패턴(방위 로브 · 방위평균)",
            f"재보정이 각도패턴을 건드리지 않는다 — 정규화 패턴 변화 "
            f"{D.num('anchor.shape_invariance_max_abs_db', fmt='{:.1e}', unit='dB')}",
        ],
        non_claims=[
            "**절대 σ 레벨** — 측정 앵커(Das, IEEE WCL 2026)에서 온다",
            "**주파수 기울기** — PTD 회절항이 없어 계통적으로 가파르다(§4)",
            "널(널 깊이·자세별 최소값) — 격자·평활에 10 dB 넘게 흔들린다",
            "β>45° 바이스태틱 · 마이크로도플러 — 이 편의 근거로 지지되지 않는다",
            "앵커 σ 가 참값에 가깝다는 것 — 재보정은 검증이 아니다(§4.3)",
        ],
        prereq=[("01 §3", "선행연구가 표적 산란 계산을 어떻게 회피했는지 — 측정 · 피팅 · "
                          "stock 방치 · 해석 블레이드")],
        repro=dict(
            cmd=["# ① 근거 실험 (완료 — 산출 JSON 이 저장소에 있다)",
                 "SIONNA2_GPU=2 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/verify_sbr_kr_sweep.py",
                 "SIONNA2_GPU=2 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/rcs_anchor.py",
                 "# ② 측정 앵커 원장 (GPU 불필요 — 위 JSON 만 읽는다)",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/sigma_anchor.py",
                 "# ③ 이 리포트 재생성 (파생 JSON + 그림 3장 + 노트북) — GPU 불필요",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "src/make_report02_target.py"],
            out=["outputs/sbr_kr_sweep.json", "outputs/rcs_anchor.json",
                 "outputs/sigma_anchor.json", "outputs/report02_derived.json"],
            runtime=f"kr 스윕 {S.num('meta.runtime_s', fmt='{:.0f}', unit='s')} · "
                    f"앵커 {A.num('meta.runtime_s', fmt='{:.0f}', unit='s')} (GPU 1장) · "
                    f"리포트 빌드 {D.num('_meta.runtime_s', fmt='{:.0f}', unit='s')}",
            note="rcs_anchor 는 기체별로 쪼개 병렬 실행 후 benchmark/merge_anchor_parts.py 로 병합한다",
        ),
    ))

    # ── §1 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §1. 일곱 대의 기체", "",
        "메쉬는 사진이 아니라 **제원**에서 세운다 — 공식 외형(L×W×H)·모터 대각·프롭 지름에 맞춘 뒤 "
        "부품을 **재질 그룹**으로 나눠 유지한다(`src/drones.py:43` DroneSpec, "
        "`src/drones.py:822` build_drone).",
        "⭐ **matrice4e · mini5pro 가 실측 대상**(06편)이므로 이 둘의 충실도가 가장 중요하다.", "",
        table(["기체", "대각 [mm]", "로터", "프롭 [mm]", "무게 [g]", "삼각형", "외접반경 r [m]"],
              [[D.num(f"airframes.{k}.name"),
                D.num(f"airframes.{k}.diagonal_mm", fmt="{:.0f}"),
                D.num(f"airframes.{k}.n_rotors", fmt="{:.0f}"),
                D.num(f"airframes.{k}.prop_dia_mm", fmt="{:.1f}"),
                D.num(f"airframes.{k}.weight_g", fmt="{:.0f}"),
                D.num(f"airframes.{k}.n_tris", fmt="{:.0f}"),
                D.num(f"airframes.{k}.r_encl_m", fmt="{:.3f}")] for k in DRONE_ORDER])))

    B.append(md(
        "![airframes](outputs/figures/report2_gallery.png)", "",
        caption(1, "SBR 이 실제로 적분하는 메쉬는 어떻게 생겼나?"), "",
        "*(Sionna 자체 렌더러가 같은 메쉬를 그린 것이다 — 삽화가 아니다. 색 = 재질 그룹. "
        "렌더는 5종만 있다.)*"))

    B.append(md(
        "### §1.1 전기적 크기 — 실측 대상이 가장 불리한 자리에 있다", "",
        f"PO 근사는 표적이 파장보다 충분히 커야 한다. 기체 7 × 밴드 3 = "
        f"{D.num('electrical.n_airframe_band', 21, '{:.0f}')}개 조합 중 전기적으로 가장 작은 것은 "
        f"**{D.num('electrical.kr_min_name')} @ {D.num('electrical.kr_min_band')}** 로 "
        f"kr = {D.num('electrical.kr_min', fmt='{:.2f}')}, 가장 큰 것은 "
        f"{D.num('electrical.kr_max_name')} @ {D.num('electrical.kr_max_band')} 의 "
        f"kr = {D.num('electrical.kr_max', fmt='{:.1f}')} 다.", "",
        f"PO 모델 간극이 1 dB 아래로 내려가는 지점은 kr = "
        f"{D.num('po_floor.kr_below_1p0_db', fmt='{:.2f}')}(§3) 이고, 그보다 작은 조합이 "
        f"{D.num('electrical.n_below_po_1db', fmt='{:.0f}')}개 있다.",
        "**실측 대상 하나가 PO 가 가장 불편한 구석에 앉아 있다.** 그 대가의 크기는 §3 이 잰다.", "",
        "![electrical size](outputs/figures/report02_electrical_size.png)", "",
        caption(2, "각 기체·밴드는 PO 근사가 얼마나 편안한 영역에 놓이는가?")))

    B.append(md(
        "### §1.2 부품별 재질 — 두 엔진이 같은 표를 읽는다", "",
        "Sionna RT 와 우리 SBR 적분기는 **같은 재질 표**를 읽는다"
        "(`src/materials.py:53` MATERIALS, `src/drones.py:562` DRONE_GROUP_MAT). "
        "ITU-R P.2040 이 정의하는 것은 그대로 쓰고, 없는 것(플라스틱·카본)만 문헌값으로 채운다.", "",
        table(["재질", "출처", "쓰이는 부품", r"\|Γ\| 벌크", r"\|Γ\| PO 실효"],
              [["metal", "ITU", "모터 · 배터리팩",
                R1.num("chamber.materials.metal.gamma_bulk", fmt="{:.3f}"),
                R1.num("chamber.materials.metal.gamma_po", fmt="{:.2f}")],
               ["camera_assembly", "ITU", "짐벌 카메라(금속 하우징 + 렌즈)",
                R1.num("chamber.materials.camera_assembly.gamma_bulk", fmt="{:.3f}"),
                R1.num("chamber.materials.camera_assembly.gamma_po", fmt="{:.2f}")],
               ["pcb", "ITU", "ESC · 메인보드(FR-4 + 구리면)",
                R1.num("chamber.materials.pcb.gamma_bulk", fmt="{:.3f}"),
                R1.num("chamber.materials.pcb.gamma_po", fmt="{:.2f}")],
               ["carbon", "문헌", "암 · 데크 · 카본 착륙장치",
                R1.num("chamber.materials.carbon.gamma_bulk", fmt="{:.3f}"),
                R1.num("chamber.materials.carbon.gamma_po", fmt="{:.2f}")],
               ["plastic", "문헌", "동체 셸 · 캐노피 · 착륙장치",
                R1.num("chamber.materials.plastic.gamma_bulk", fmt="{:.3f}"),
                R1.num("chamber.materials.plastic.gamma_po", fmt="{:.2f}")],
               ["prop_plastic", "문헌", "프로펠러(셸보다 얇음)",
                R1.num("chamber.materials.prop_plastic.gamma_bulk", fmt="{:.3f}"),
                R1.num("chamber.materials.prop_plastic.gamma_po", fmt="{:.2f}")]])))

    B.append(md(
        "### §1.3 이 메쉬가 실물과 얼마나 다른가", "",
        "제원에서 세운 우리 메쉬를 **실물 유래 메쉬** 넷과 같은 커널·같은 자세로 맞댄다"
        "(`benchmark/compare_community.py`, `src/compare_phantom_scan.py`).", "",
        table(["대조 원본", "Δ 투영면적 [dB]", "Δ 방위평균 σ [dB]", "자세별 RMS [dB]"],
              [[PH4.num("name_real"),
                PH4.num("d_area_db", fmt="{:+.2f}"), PH4.num("d_sigma_db", fmt="{:+.2f}"),
                PH4.num("d_sigma_rms_db", fmt="{:.1f}")],
               [CAD.num("typhoon.name_real"),
                CAD.num("typhoon.d_area_db", fmt="{:+.2f}"),
                CAD.num("typhoon.d_sigma_db", fmt="{:+.2f}"),
                CAD.num("typhoon.d_sigma_rms_db", fmt="{:.1f}")],
               [COM.num("m100.name_real"),
                COM.num("m100.d_area_db", fmt="{:+.2f}"), COM.num("m100.d_sigma_db", fmt="{:+.2f}"),
                COM.num("m100.d_sigma_rms_db", fmt="{:.1f}")],
               [COM.num("m600.name_real"),
                COM.num("m600.d_area_db", fmt="{:+.2f}"), COM.num("m600.d_sigma_db", fmt="{:+.2f}"),
                COM.num("m600.d_sigma_rms_db", fmt="{:.1f}")]]), "",
        "**읽는 법**: 방위평균은 ~1 dB 안에서 맞고 **자세별 RMS 는 맞지 않는다** — "
        "널 위치가 메쉬 세부에 민감해서다.",
        "그래서 이 편은 로브와 방위평균만 인용한다(§5)."))

    # ── §2 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §2. 스톡 Sionna 로는 안 되는 이유, 그리고 우리 엔진", "",
        "Sionna 의 `PathSolver` 는 **전파(propagation)** 도구다. 표면을 국소 무한 거울로 보고"
        "(기하광학) 경로별 지연·도플러·복소이득을 준다.", "",
        "**표면적분 단계가 없다** — 그래서 표적의 σ 가 창발하지 않는다. "
        "광선을 더 쏘아도 해결되지 않는다.", "",
        table(["실험", "결과", "출처"],
              [[f"금속 평판 변 {R3.num('D_plate.rows[0].side_m', fmt='{:.1f}')}→"
                f"{R3.num('D_plate.rows[-1].side_m', fmt='{:.1f}', unit='m')} (σ 가 "
                f"{R3.num('D_plate.sigma_span_db', fmt='{:.1f}', unit='dB')} 변함)",
                f"RT 진폭 {R3.num('D_plate.rt_span_db', fmt='{:.2e}', unit='dB')} 변함 (= 불변)",
                "`benchmark/rt_experiments.py` D"],
               ["PEC 구에 광선 1M~400M 발",
                f"표적 경로 {R3.num('E_sphere.rows[0].n_paths', fmt='{:.0f}')}개 "
                f"(곡면 정반사점을 거울상법이 못 찾는다)", "동 E"],
               ["드론 확산 에코, 광선 25M→400M",
                f"코히런트 합이 {D.num('stock_rt.coh_climb_db', fmt='{:+.1f}', unit='dB')} "
                f"더 커진다 (수렴하지 않는다)", "동 A"],
               ["ITU `metal` 의 산란계수 S",
                f"{R3.num('C_metal.itu_metal_S', fmt='{:.1f}')} → 모터·배터리·PCB 는 확산 기여 0",
                "동 C"]]), "",
        f"σ 의 {R3.num('C_metal.metal_share_pct', fmt='{:.0f}', unit='%')} 가 바로 그 금속 부품에 "
        f"얹혀 있다. **σ 는 적분에서 나온다.**"))

    B.append(md(
        "![stock RT](outputs/figures/report3_f6_no_sigma.png)", "",
        caption(3, "광선을 더 쏘면 스톡 Sionna RT 가 드론의 σ 를 내놓는가?")))

    B.append(md(
        "### §2.1 우리가 하는 것 — SBR (광선 + PO 면적분)", "",
        "상용 솔버(FEKO/CST SBR+)가 고주파 RCS 를 내는 표준 방법 그대로다: "
        "**① 광선으로 실제 조명면을 찾고 ② 그 위에서 PO 표면적분**(`src/rcs_sbr.py:184`).", "",
        table(["단계", "무엇을", "누가"],
              [["첫 충돌 탐색 · 가림", "어느 면이 실제로 보이는가",
                "🟢 Sionna 의 Mitsuba/OptiX 광선엔진"],
               ["재질 |Γ|", "부품별 반사계수", "🟢 Sionna 재질표 (`src/materials.py:53`)"],
               ["PO 면적분 → σ", "E = Σ |Γᵢ| e^{j2k pᵢ·û} d², σ = 4π|E|²/λ²",
                "🔵 우리 (`src/rcs_sbr.py:184`)"],
               ["셸 투과", "얇은 유전체 셸 뒤 금속(배터리·PCB) 코히런트 합",
                "🔵 우리 (동 `penetrate=True`)"]]), "",
        "게재된 선행 중 이 단계를 갖춘 것은 없다 — Proc. IEEE 2026 의 Clutter-Aware ISAC 조차 "
        "메쉬를 Sionna 에 넣고 **stock Fresnel 로 둔다**(01편 §3)."))

    B.append(md(
        "![occlusion](outputs/figures/report2_occlusion.png)", "",
        caption(4, "광선을 PO 앞에 두면 σ 가 얼마나 달라지는가?"), "",
        f"한 방위에서 순수 PO 가 '조명됐다'고 센 면의 "
        f"{R2.num('occlusion.hidden_frac', fmt='{:.0%}')} 는 실제로 다른 것 뒤에 있다. 방위 "
        f"{R2.num('occlusion.n_az', fmt='{:.0f}')}점 평균으로 "
        f"{R2.num('occlusion.occlusion_db', fmt='{:+.2f}', unit='dB')}, 오목부 다중반사는 "
        f"{R2.num('occlusion.multibounce_db', fmt='{:+.2f}', unit='dB')} 뿐이다.", "",
        f"가림의 크기는 기체 형상이 정한다 — 방위 {R6.num('n_az', fmt='{:.0f}')}점 격자에서 "
        f"{R6.num('compare.mavic4pro.occl_el15', fmt='{:+.2f}')}(Mavic 4 Pro) ~ "
        f"{R6.num('compare.s1000plus.occl_el15', fmt='{:+.2f}', unit='dB')}"
        f"(S1000+, 열린 프레임이라 가릴 것이 없다) 다. "
        f"⚠ 두 줄은 **자세격자가 다르므로** Mavic 값도 서로 다르다 — 같은 격자 안에서만 비교할 것."))

    # ── §3 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §3. 이 엔진이 무엇만큼 값어치가 있나 — 절대 섞지 않는 두 가지", "",
        "```", "(커널 − Mie)  =  (커널 − 해석 PO)   +   (해석 PO − Mie)",
        "                  ↑ (a) 우리 수치오차       ↑ (b) PO 근사를 쓴 대가", "```",
        "**(a) 는 우리 것**이고 격자를 조이면 줄어든다. **(b) 는 물리모델 고유**라 못 줄인다. "
        "기준을 하나로 두면 (b) 가 통째로 우리 오차로 잘못 기입된다.", "",
        "⭐ **Mie 와 해석 PO 는 둘 다 기준해(reference solution)이지 우리 출력이 아니다** — "
        "닫힌형 해다(`benchmark/mie_pec_sphere.py:98` Mie, `:127` 해석 PO). "
        "저장소 방침상 **순수 PO 를 엔진으로 쓴 결과는 리포트에 없다.**"))

    B.append(md(
        "![kr sweep](outputs/figures/report02_kr_sweep.png)", "",
        caption(5, "우리 수치오차와 PO 근사 자체의 간극은 각각 kr 에 따라 얼마인가?")))

    B.append(md(
        "### §3.1 두 눈금, 따로 읽는 법", "",
        table(["", "(a) 우리 수치오차 · 과녁 = 해석 PO", "(b) PO 모델의 간극 · 과녁 = 정확 Mie"],
              [["최대 편차 (kr=1..100)",
                S.num("summary_div16.max_abs_db_vs_po", 0.201, "{:.3f}", "dB"),
                S.num("summary_div16.max_abs_db_vs_mie", fmt="{:.2f}", unit="dB") + " (kr=1)"],
               ["kr≥30 산포",
                S.num("summary_div16.std_sbr_over_po_pct_kr_ge30", 0.885, "{:.3f}", "%"),
                S.num("summary_div16.std_sbr_over_mie_pct_kr_ge30", fmt="{:.3f}", unit="%")],
               ["1 dB 아래로 내려가는 kr",
                "해당 없음 (전 구간 "
                + S.num("summary_div16.max_abs_db_vs_po", fmt="{:.3f}", unit="dB") + " 이내)",
                D.num("po_floor.kr_below_1p0_db", fmt="{:.2f}")],
               ["0.5 / 0.2 dB 아래로", "해당 없음",
                D.num("po_floor.kr_below_0p5_db", fmt="{:.2f}") + " / "
                + D.num("po_floor.kr_below_0p2_db", fmt="{:.2f}")]]), "",
        f"**Sagitta(preprint)가 말하는 kr≥30 은 우리 바닥이 아니라 그들 커널이 Mie 로 수렴하는 "
        f"지점**이다. 우리 커널은 kr="
        f"{S.num('summary_div16.kr_min', fmt='{:.0f}')} 에서도 (a) 열의 편차 안에 있다."))

    B.append(md(
        "### §3.2 ⚠ (b)는 **하한이지 상한이 아니다**", "",
        "위 kr 문턱은 **매끄럽고 볼록한 구**에서 잰 값이다. 우리 표적은 그렇지 않다 — "
        "프롭 날개·암 모서리·착륙장치처럼 **얇고 모서리가 많다**.", "",
        "PO 는 모서리 회절을 담지 못하므로 실제 드론에서의 모델 간극은 이 구 값보다 **크다**. "
        "그 크기는 우리가 모른다.", "",
        f"여기에 격자 불확실성이 더 붙는다 — λ/16 격자에서 서브셀 위상 산포가 "
        f"{R2.num('sbr_validation.dither[2].spread', fmt='{:.2f}', unit='dB')}"
        f"(λ/24 에서 {R2.num('sbr_validation.dither[3].spread', fmt='{:.2f}', unit='dB')}). "
        f"**절대 레벨에 붙는 값이고 자세 간 상대 패턴에는 훨씬 덜 붙는다.**"))

    # ── §4 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §4. ⭐ 앵커 — 왜 레벨과 주파수는 측정에서 받는가", "",
        f"밴드 3점으로 잰 우리 σ(f) 기울기는 "
        f"{D.num('band_slope.ours_min', fmt='{:.3f}')}"
        f"({D.num('band_slope.ours_min_drone')}) ~ "
        f"{D.num('band_slope.ours_max', fmt='{:.3f}', unit='dB/GHz')}"
        f"({D.num('band_slope.ours_max_drone')}) 인데, 측정 문헌은 "
        f"{A.num('literature.mu_eps.multiband_phantom3.mu_a', 0.21, '{:.3f}')}(Das, IEEE WCL 2026) "
        f"와 {A.num('literature.mu_eps.mono3d_theta90.mu_a', 0.315, '{:.3f}', 'dB/GHz')}"
        f"(Yuan, EuCAP 2025) 다 — 우리가 {D.num('band_slope.ratio_min', fmt='{:.1f}')}~"
        f"{D.num('band_slope.ratio_max', fmt='{:.1f}')}배 가파르다.", "",
        "**원인**: PO 는 f² 로 커지는 정반사항만 남긴다. 실제 표적에는 **주파수에 거의 무관한 "
        "모서리 회절항**이 함께 있고 우리는 그 항(PTD)을 구현하지 않았다. "
        "부호가 정해진 계통오차이므로 **측정으로 교정할 수 있다** — 그것이 앵커다.", "",
        f"재보정은 `src/sigma_anchor.py` 가 하고 원장은 `outputs/sigma_anchor.json` 이다. "
        f"모드는 `{D.num('anchor.mode')}` — 크기법칙(L²/L⁴)을 쓰지 않는 쪽을 택했다(§4.3)."))

    B.append(md(
        "![band slope](outputs/figures/report02_band_slope.png)", "",
        caption(6, "측정 앵커는 각 기체의 밴드 기울기를 어디로 옮기는가?")))

    B.append(md(
        "### §4.1 분해 — 어느 축이 어디서 오나", "",
        "게재된 표준트랙 논문이 쓰는 분해를 그대로 따른다 — σ = **A(f)·B₁(φ,θ)·B₂** "
        "(Zhang, IEEE JSAC 44:702, 2026: 측정 적합 모델).", "",
        table(["인자", "무엇", "어디서 오나", "이 편의 근거"],
              [["A(f)", "레벨 + 주파수 의존성", "**측정 앵커**(외부)",
                f"Das μ = {A.num('literature.mu_eps.multiband_phantom3.mu_a', fmt='{:.2f}')}·f "
                f"{A.num('literature.mu_eps.multiband_phantom3.mu_b', fmt='{:+.2f}', unit='dBsm')}"],
               ["B₁(φ,θ)", "자세에 따른 모양", "**기하**(SBR+PO)",
                f"재보정이 바꾼 정규화 패턴 "
                f"{D.num('anchor.shape_invariance_max_abs_db', fmt='{:.1e}', unit='dB')}"],
               ["B₂", "산포(자세 요동의 분포)", "기하 — 단 분포족만",
                f"적합 RMSE {A.num('literature.fit_rmse_db.AAV', fmt='{:.2f}', unit='dB')} 가 "
                f"문헌 기준선"]]), "",
        f"밴드별 보정량은 {D.num('anchor.correction_min_db', fmt='{:+.2f}')} ~ "
        f"{D.num('anchor.correction_max_db', fmt='{:+.2f}', unit='dB')} 이고, 그동안 **모양은 "
        f"소수점 15자리까지 그대로**다. 눈금만 측정에서 온다."))

    B.append(md(
        "### §4.2 비교가능성 원장 — 보정된 숫자가 기체마다 같은 뜻이 아니다", "",
        f"앵커 기체는 {D.num('anchor.anchor_platform')} 한 대다. 같은 급이면 'direct', "
        f"크기법칙으로 옮겼으면 'scaled', 위상 자체가 다르면 'not_comparable' 이다 — "
        f"{D.num('anchor.n_direct', fmt='{:.0f}')} / "
        f"{D.num('anchor.n_scaled', fmt='{:.0f}')} / "
        f"{D.num('anchor.n_not_comparable', fmt='{:.0f}')} 대씩이다.", "",
        table_from("outputs/sigma_anchor.json:drones",
                   [("기체", "name"), ("대각 D [m]", "comparability.D_m"),
                    ("D/D_ref", "comparability.size_ratio"),
                    ("로터", "comparability.num_rotors"),
                    ("판정", "comparability.verdict"),
                    ("L²↔L⁴ 산포 [dB]", "comparability.size_law_spread_db")],
                   fmt={"comparability.D_m": "{:.3f}",
                        "comparability.size_ratio": "{:.2f}",
                        "comparability.num_rotors": "{:.0f}",
                        "comparability.size_law_spread_db": "{:.2f}"},
                   order=DRONE_ORDER)))

    B.append(md(
        "### §4.3 ⚠ 앵커가 통제하지 못한 것 — 반드시 함께 읽을 것", "",
        table_from("outputs/sigma_anchor.json:uncontrolled",
                   [("미통제 항목", "term"), ("상태", "status"), ("크기 [dB]", "size_db")],
                   fmt={"size_db": "{:+.2f}"}, null="미상"), "",
        f"가장 큰 미통제항 **{D.num('anchor.largest_uncontrolled_term')}** 이 "
        f"{D.num('anchor.largest_uncontrolled_db', fmt='{:.2f}', unit='dB')} 로, 실제 적용한 "
        f"보정 최대치 {D.num('anchor.correction_abs_max_db', fmt='{:.2f}', unit='dB')} 보다 크다. "
        "밴드 간 격차를 **빡빡한 숫자로 읽으면 안 된다**(05편).", "",
        "⭐ **측정에 맞춰 재척도하는 것은 그 측정으로 검증한 것이 아니다.** 자유도를 소모했을 뿐이고, "
        "검증은 06편의 독립 측정이 한다. 커널 자체는 그대로다 — 원장만 있다."))

    # ── §5 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §5. 살아남는 결과 — 자세 · 부품 · 재질", "",
        "위 경계를 지키면 세 가지가 남는다. 전부 **같은 메쉬 위에서 무엇을 켜고 끈 차이**라 "
        "절대 레벨의 불확실성이 상당 부분 상쇄된다.", "",
        table(["살아남는 것", "왜", "인용해도 되는 형태"],
              [["방위 로브 위치·상대 높이", "기하가 결정한다", "로브 · 방위평균"],
               ["부품별 기여", "같은 메쉬에서 그룹만 뺀 차이", "Δ dB"],
               ["재질 가중의 대가", "|Γ| 만 바꾼 차이", "Δ dB"],
               ["**널 깊이**", "격자·평활·밴드평균에 10 dB 넘게 흔들린다", "❌ 인용 금지"]])))

    B.append(md(
        "![aspect](outputs/figures/report2_rcs_polar.png)", "",
        caption(7, "기체와 밴드에 따라 자세 패턴의 모양이 어떻게 달라지는가?"), "",
        "*(로브는 안정적이고 로브 사이 널은 그렇지 않다 — 그림 안 캡션이 그 경계를 적고 있다.)*"))

    B.append(md(
        "### §5.1 부품을 하나씩 빼면", "",
        f"{R2.num('materials.name')} · {D.num('bands_ghz.5G', fmt='{:.1f}', unit='GHz')} · "
        f"el={R2.num('materials.el', fmt='{:.0f}', unit='°')}, 같은 커널·같은 자세격자에서 "
        f"그룹만 지운다(`src/viz_report2.py:1075`). **드론은 금속 덩어리가 아니다.**", "",
        table_from("outputs/report2_waveform_rcs.json:materials.rows",
                   [("무엇을 남겼나", "label"), ("면", "n_faces"),
                    ("방위평균 σ [dBsm]", "mean_dbsm"), ("Δ [dB]", "delta_db")],
                   fmt={"n_faces": "{:.0f}", "mean_dbsm": "{:.2f}", "delta_db": "{:+.2f}"}), "",
        "![strip](outputs/figures/report2_materials.png)", "",
        caption(8, "드론에서 실제로 반사하는 것은 어느 부품인가?")))

    # ── 재현용 코드 셀 ─────────────────────────────────────────────────────
    B.append(code(
        "# 이 편의 숫자를 직접 열어보기 — 그림·표의 모든 값은 아래 JSON 에서 나온다.",
        "import json",
        "D = json.load(open('outputs/report02_derived.json'))",
        "print(json.dumps(D['_meta']['definitions'], ensure_ascii=False, indent=1))",
        "print('kr 최소 조합 :', D['electrical']['kr_min_drone'],",
        "      D['electrical']['kr_min_band'], round(D['electrical']['kr_min'], 2))",
        "print('밴드 기울기  :', {k: round(v, 3) for k, v in",
        "      D['band_slope']['ours_db_per_ghz'].items()})",
        "print('앵커 원장    :', {k: D['anchor'][k] for k in",
        "      ('mode', 'correction_min_db', 'correction_max_db', 'largest_uncontrolled_db')})"))

    # ── 이 편의 한계 ───────────────────────────────────────────────────────
    B.append(limits([
        ("PTD 모서리 회절항이 없다 — 밴드 기울기가 계통적으로 가파르다",
         "`src/rcs_sbr.py:184` 의 면적분에 등가 모서리 전류를 더한 뒤 §4 기울기를 다시 잰다"),
        (f"앵커의 크기전이 법칙(L² vs L⁴)이 미해소 — 최대 "
         f"{D.num('anchor.largest_uncontrolled_db', fmt='{:.2f}', unit='dB')} 갈린다",
         "06편 측정으로 두 기체(Matrice 4E · Mini 5 Pro)의 상대 레벨을 재 크기지수를 직접 고정한다"),
        ("편파가 통제되지 않는다 — 커널은 재질당 스칼라 |Γ| 하나이고 앵커는 VV 측정이다",
         "06편 측정 설계에서 편파 축을 확정한 뒤 `src/materials.py:171` 에 편파 분해를 넣을지 결정"),
        ("앵커가 코드가 아니라 원장이다 — 생산 σ 는 여전히 SBR+PO 원값이다",
         "05편 밴드 비교에서 `outputs/sigma_anchor.json` 의 `modes.slope_only.delta_db` 를 적용해 읽는다"),
        ("PO 모델 간극의 kr 문턱은 **구**에서만 잰 값이다(얇은 표적의 하한)",
         "평판·이면반사체 표준체로 같은 kr 스윕을 돌려 문턱을 다시 세운다 "
         "(`benchmark/verify_sbr_defect_fixes.py` 에 두 닫힌형이 이미 있다)"),
        ("메쉬 자세별 RMS 가 실물 대조와 5~10 dB 어긋난다",
         "널을 인용하지 않는 현 규약을 유지하되 06편 측정으로 로브 위치부터 대조한다"),
        ("모노스태틱만 방어된다 — 바이스태틱은 β≤45° 로 제한한다",
         "`src/rcs_sbr.py:330` `rcs_sbr_multistatic` 의 상반성 검사를 β 별로 다시 돌린다"),
    ], sec="§6."))

    return B


# =========================================================================== #
def main():
    print("── 리포트 02 빌드 ──")
    J, kr_grid, d_db = derive()
    fig_electrical_size(J)
    fig_kr_sweep(J, kr_grid, d_db)
    fig_band_slope(J)
    rep = build_notebook(NB_OUT, blocks(J), strict=True)
    print(f"✅ {os.path.relpath(NB_OUT, _ROOT)}")
    return rep


if __name__ == "__main__":
    main()
