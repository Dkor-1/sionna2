# -*- coding: utf-8 -*-
"""
make_report06_measurement.py — 리포트 06 「실측」 빌더  →  report06_measurement.ipynb
============================================================================================
계약서: `docs/REBUILD_2026-07-30.md` (골격 §2 의 06 편, 서술규약 §5). 규약 강제는 `src/report_style.py`.

이 편의 역할: **다음 라운드의 계약서**. 무엇을 재면 시뮬의 어느 주장이 결판나는가를 숫자로 적는다.

이 파일이 하는 일 (한 번 실행하면 셋 다 나온다)
  ① **파생 JSON** `outputs/report06_derived.json` — 두 원본 JSON 에 흩어져 있거나 아예 값으로
     없는 설계값을 여기서 계산해 디스크에 남긴다. 손으로 친 숫자를 0개로 만들기 위한 장치다.
       · 원거리장 2D²/λ — **D 정의 세 가지**를 한 표에 모은다(정의가 섞이면 거리가 2배 틀린다)
       · 교정구 여유 — 정확 Mie σ 와 기체 예상 σ 의 차 [dB]
       · 점표적 조건 — 서브밴드 거리분해능 vs 기체 최대치수
       · 자세 각도표본 — λ/4D 권장 간격과 한 바퀴 표본수
       · 크기법칙 L²/L⁴ **차등신호** — 두 기체를 함께 재면 얼마로 갈리는가
       · 기울기 판별폭 — 우리 3밴드 기울기와 앵커 기울기가 대역 끝에서 벌리는 간격
       · 지면반사 유령의 경로차 vs 거리분해능
  ② **그림 6장** — ADC 여유 · 원거리장 · 교정구 · 크기법칙 · 기울기 · 지면반사.
  ③ **노트북** `report06_measurement.ipynb`.

실행
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py

읽는 것 (전부 저장소에 이미 있는 산출물)
  outputs/report06_measurement.json  ← benchmark/plan_measurement.py
  outputs/measurement_plan.json      ← src/sigma_anchor.py :: write_measurement_plan()
  outputs/sigma_anchor.json          ← src/sigma_anchor.py

⚠ GPU 도 Sionna 도 필요 없다. numpy/scipy + Mie 기준해만 쓴다(약 10 초).
⚠ 이 편은 **설계값만** 담는다. 아무것도 측정하지 않았다.
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
                          code, fetch, from_json, header, limits, md,
                          num, table, table_from)

C0 = 299792458.0
FIGDIR = os.path.join(_ROOT, "outputs", "figures")
DERIVED = os.path.join(_ROOT, "outputs", "report06_derived.json")
NB_OUT = os.path.join(_ROOT, "report06_measurement.ipynb")

R6 = os.path.join(_ROOT, "outputs", "report06_measurement.json")
MP = os.path.join(_ROOT, "outputs", "measurement_plan.json")
SA = os.path.join(_ROOT, "outputs", "sigma_anchor.json")

#: 구매 확정 2종. 순서 = 큰 것 먼저.
AIR = ("matrice4e", "mini5pro")
#: 교정 기준체 — 문헌이 실제로 쓴 두 금속구.
SPHERES = ("0.178", "0.25")
#: 서브밴드 후보 [MHz] — X410 순시대역 400 을 쪼갠다.
BW_MHZ = (400, 200, 100, 50)
#: 밴드 표시 이름 → 짧은 이름
SHORT = {"LTE 1.843 GHz": "LTE", "5G 3.5 GHz": "5G", "WiFi 5.21 GHz": "WiFi"}


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# =========================================================================== #
#  ①  파생값 — 리포트가 인용할 수 있도록 디스크에 남긴다
# =========================================================================== #
def derive(verbose=True) -> dict:
    """설계값을 계산해 `outputs/report06_derived.json` 에 쓴다. 측정은 하지 않는다."""
    t0 = time.time()
    r6, mp, sa = _load(R6), _load(MP), _load(SA)
    bands = list(r6["bands"].keys())

    # ── 원거리장: D 정의 세 가지를 같은 표에 ──────────────────────────────────
    #   env  = 회전 로터 디스크까지 포함한 외접상자의 3D 대각 (가장 큼 → 채택)
    #   bbox = 프로펠러 포함 수평 최대치수 (radar_scene.target_extent)
    #   diag = 모터-모터 대각 (앵커 문헌 Das/Yuan 의 관례)
    ff_rows = []
    for dk in AIR:
        e, m = r6["farfield"][dk], mp["airframes"][dk]
        for b in bands:
            lam = r6["bands"][b]["lam_m"]
            ff_rows.append(dict(
                airframe=dk, band=SHORT[b], lam_mm=lam * 1e3,
                D_env_m=e["D_m"], R_ff_env_m=e["bands"][b]["R_ff_m"],
                D_bbox_m=m["D_bbox_m"], R_ff_bbox_m=m["by_band"][b]["farfield_m_bbox"],
                D_diag_m=m["D_diagonal_m"], R_ff_diag_m=m["by_band"][b]["farfield_m_diag"],
                spread_ratio=e["bands"][b]["R_ff_m"] / m["by_band"][b]["farfield_m_diag"]))
    worst = max(ff_rows, key=lambda r: r["R_ff_env_m"])

    # ── 교정 기준체: 정확 Mie σ 와 기체 예상 σ 의 여유 ────────────────────────
    exp = mp["expected_sigma_dbsm_from_anchor"]["by_drone"]
    cal_rows = []
    for rs in SPHERES:
        sk, mk = f"sphere_r{rs}", f"r={float(rs):.3f}m"
        for b in bands:
            mie = r6["farfield"][sk]["bands"][b]["mie_dbsm"]
            cal_rows.append(dict(
                sphere=f"r={float(rs)*100:.1f} cm", band=SHORT[b],
                ka=mp["calibration_spheres"][mk][b]["ka"], mie_dbsm=mie,
                mie_minus_go_db=mp["calibration_spheres"][mk][b]["mie_minus_go_db"],
                R_ff_m=r6["farfield"][sk]["bands"][b]["R_ff_m"],
                margin_matrice4e_db=mie - exp["matrice4e"]["L2"][b],
                margin_mini5pro_db=mie - exp["mini5pro"]["L2"][b]))
    cal_margin_min = min(min(r["margin_matrice4e_db"], r["margin_mini5pro_db"])
                         for r in cal_rows)

    # ── 점표적 조건: 서브밴드 거리분해능 c/2B 가 기체 최대치수보다 커야 한다 ──
    pt_rows = []
    for bw in BW_MHZ:
        dr = C0 / (2.0 * bw * 1e6)
        row = dict(B_MHz=bw, dR_m=dr)
        for dk in AIR:
            D = mp["airframes"][dk]["D_bbox_m"]
            row[f"{dk}_margin_m"] = dr - D
            row[f"{dk}_ok"] = "점표적" if dr > D else "⚠ 퍼짐"
        pt_rows.append(row)
    #  ⚠ 대역이 넓을수록 ΔR 이 작아 조건이 어려워진다 → 만족하는 것 중 **가장 넓은** 대역.
    bw_ok = max([r["B_MHz"] for r in pt_rows
                 if all(r[f"{d}_ok"] == "점표적" for d in AIR)], default=None)

    # ── 자세 각도표본: 권장 간격 λ/4D 와 한 바퀴 표본수 ───────────────────────
    asp_rows = []
    for dk in AIR:
        for b in bands:
            v = mp["airframes"][dk]["by_band"][b]
            step = v["az_step_recommended_deg"]
            asp_rows.append(dict(airframe=dk, band=SHORT[b],
                                 az_nyquist_deg=v["az_step_nyquist_deg"],
                                 az_recommended_deg=step,
                                 n_az_per_turn=360.0 / step,
                                 finer_than_anchor_2deg=bool(step < 2.0)))
    asp_min = min(asp_rows, key=lambda r: r["az_recommended_deg"])

    # ── 크기법칙 L²/L⁴ — 두 기체를 함께 재면 갈리는가 ─────────────────────────
    sl = {}
    for dk in AIR:
        c = sa["drones"][dk]["comparability"]
        sl[dk] = dict(size_ratio=c["size_ratio"],
                      corr_L2_db=c["size_corr_L2_db"], corr_L4_db=c["size_corr_L4_db"],
                      spread_db=c["size_corr_L4_db"] - c["size_corr_L2_db"],
                      verdict=c["verdict"],
                      mu_L2_dbsm={SHORT[b]: exp[dk]["L2"][b] for b in bands},
                      mu_L4_dbsm={SHORT[b]: exp[dk]["L4"][b] for b in bands})
    size_law = dict(
        by_airframe=sl,
        differential_db=abs(sl["matrice4e"]["spread_db"] - sl["mini5pro"]["spread_db"]),
        definition="(L4-L2)_matrice4e - (L4-L2)_mini5pro [dB]. 두 기체가 앵커보다 "
                   "각각 크고 작으므로 두 법칙의 예측이 **반대 방향**으로 갈린다.",
        uncontrolled_size_db=[u for u in sa["uncontrolled"]
                              if u["term"] == "size transfer law"][0]["size_db"])

    # ── 기울기 판별폭 — 세션 재현성 요구치 ───────────────────────────────────
    span = float(r6["slope_discrimination"]["band_span_ghz"])
    a_anchor = float(sa["drones"][AIR[0]]["modes"]["slope_only"]["slope_anchor_db_per_ghz"])
    slope_rows = []
    for dk in AIR:
        a = sa["drones"][dk]["slope_ours_3band_db_per_ghz"]
        slope_rows.append(dict(airframe=dk, ours_db_per_ghz=a, anchor_db_per_ghz=a_anchor,
                               ratio_over_anchor=a / a_anchor, gap_db=(a - a_anchor) * span))
    slope = dict(rows=slope_rows, span_ghz=span, anchor_db_per_ghz=a_anchor,
                 gap_db_min=min(r["gap_db"] for r in slope_rows),
                 fit_note_short="세 밴드 방위평균 μ 를 f[GHz] 에 1차 적합(el=0)",
                 definition="ours = sigma_anchor.json:drones.<k>.slope_ours_3band_db_per_ghz "
                            "(세 밴드 방위평균 mu 를 f[GHz] 에 1차 적합, el=0). "
                            "gap = (ours - anchor) * span — 대역 끝에서 두 가설이 벌리는 간격 [dB]. "
                            "세션간 진폭 재현성이 이보다 나빠야 기울기 판정이 성립한다.")

    # ── 지면반사 유령: 경로차 2hH/R 이 거리분해능보다 커야 게이팅으로 뗀다 ────
    gb_rows = []
    for k, v in mp["ground_bounce"].items():
        if k.startswith("_"):
            continue
        h, H, R = (float(s.split("=")[1].rstrip("m")) for s in k.split(","))
        gb_rows.append(dict(h_m=h, H_m=H, R_m=R, path_diff_m=v,
                            sep_at_200MHz=bool(v > C0 / (2 * 200e6)),
                            sep_at_100MHz=bool(v > C0 / (2 * 100e6))))
    gb_frac200 = sum(r["sep_at_200MHz"] for r in gb_rows) / len(gb_rows)
    gb_ref_bw = 200

    J = {
        "_meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "src/make_report06_measurement.py :: derive()",
            "purpose": "리포트 06 이 인용하는 **설계값**. 측정값은 하나도 없다.",
            "inputs": ["outputs/report06_measurement.json", "outputs/measurement_plan.json",
                       "outputs/sigma_anchor.json"],
            "definitions": {
                "R_ff": "2*D^2/lambda. D 정의 3종: env(로터 디스크 포함 외접상자 3D 대각) · "
                        "bbox(프로펠러 포함 수평 최대치수) · diag(모터-모터, 앵커 문헌 관례). "
                        "채택은 가장 보수적인 env.",
                "margin_*_db": "교정구 정확 Mie sigma - 기체 예상 sigma(L2 크기보정) [dB]. "
                               "양수면 교정구가 표적보다 밝다.",
                "dR_m": "c/(2B) — 모노스태틱 거리분해능. 점표적 조건은 dR > D_bbox.",
                "az_recommended_deg": "lambda/(4*D_bbox) [deg] — 방위 각도표본 권장 간격.",
                "gap_db": slope["definition"],
                "differential_db": size_law["definition"],
                "path_diff_m": "2hH/R — 표적경유 지면반사와 직접 표적경로의 경로차 [m].",
            },
            "runtime_s": None,
        },
        "farfield": ff_rows,
        "farfield_adopted": dict(
            D_def="env — 회전 로터 디스크를 포함한 외접상자의 3D 대각",
            R_ff_max_m=worst["R_ff_env_m"], airframe=worst["airframe"], band=worst["band"],
            spread_ratio_max=max(r["spread_ratio"] for r in ff_rows),
            why="D 정의를 모터대각으로 잡으면 요구거리가 절반 이하로 내려간다. "
                "로터는 전기적 산란체이므로 포함한다."),
        "calibration": cal_rows,
        "calibration_margin_min_db": cal_margin_min,
        "calibration_pick": dict(
            radius_m=float(SPHERES[0]), radius_cm=float(SPHERES[0]) * 100.0,
            why="세 밴드 모두 Mie−πr² 편차가 작고 앵커 문헌(Yuan)이 쓴 것과 같은 크기다."),
        "hw_span": dict(f_lo_mhz=r6["hw"]["f_lo_hz"] / 1e6,
                        f_hi_ghz=r6["hw"]["f_hi_hz"] / 1e9),
        "point_target": pt_rows,
        "point_target_max_bw_MHz": bw_ok,
        "aspect": asp_rows,
        "aspect_finest_deg": asp_min["az_recommended_deg"],
        "aspect_finest_airframe": asp_min["airframe"],
        "aspect_finest_band": asp_min["band"],
        "aspect_n_az_max": asp_min["n_az_per_turn"],
        "size_law": size_law,
        "slope": slope,
        "ground_bounce": gb_rows,
        "ground_bounce_ref_bw_MHz": gb_ref_bw,
        "ground_bounce_n_geom": len(gb_rows),
        "ground_bounce_sep_frac_200MHz": gb_frac200,
        "ground_bounce_min_m": min(r["path_diff_m"] for r in gb_rows),
        "ground_bounce_max_m": max(r["path_diff_m"] for r in gb_rows),
    }
    J["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    with open(DERIVED, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    if verbose:
        print(f"  원거리장 최대   : {worst['R_ff_env_m']:.2f} m "
              f"({worst['airframe']} · {worst['band']})")
        print(f"  교정구 최소여유 : {cal_margin_min:+.2f} dB")
        print(f"  점표적 최대대역 : {bw_ok} MHz")
        print(f"  각도표본 최소   : {asp_min['az_recommended_deg']:.2f}°")
        print(f"  크기법칙 차등   : {size_law['differential_db']:.2f} dB")
        print(f"  기울기 판별폭   : {slope['gap_db_min']:.2f} dB (최소)")
        print(f"✅ 파생값 저장 → outputs/report06_derived.json "
              f"({J['_meta']['runtime_s']} s)")
    return J


# =========================================================================== #
#  ②  그림 6장 — 글자는 전부 영어(하우스 규약), assert_fig_text 로 검사
# =========================================================================== #
def _save(fig, name):
    os.makedirs(FIGDIR, exist_ok=True)
    p = os.path.join(FIGDIR, name)
    fig.savefig(p, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  🖼  outputs/figures/{name}")


def fig_adc(J):
    """12-bit ADC 동적범위가 직접파 대 잡음비 위에 얼마나 남는가."""
    r6 = _load(R6)
    T = ["12-bit ADC headroom above the direct-path-to-noise ratio",
         "dB", "direct-path-to-noise ratio (DNR)", "headroom",
         "ADC dynamic range, 12-bit", "waveform"]
    assert_fig_text(*T)
    wfs = list(r6["adc"]["per_waveform"].keys())
    dnr = [r6["adc"]["per_waveform"][w]["dnr_db"] for w in wfs]
    dr = r6["adc"]["dynamic_range_db"]
    fig, ax = plt.subplots(figsize=(7.6, 3.1))
    y = np.arange(len(wfs))
    ax.barh(y, dnr, color="#3b6ea5", height=0.5, label=T[2])
    ax.barh(y, [dr - d for d in dnr], left=dnr, color="#c9d8e8", height=0.5, label=T[3])
    ax.axvline(dr, color="#b03030", lw=1.6)
    ax.text(dr + 1.2, 0.5 * (len(wfs) - 1), f"{T[4]} = {dr:.1f} dB",
            ha="center", va="center", fontsize=8.5, color="#b03030", rotation=90)
    for i, d in enumerate(dnr):
        ax.text(0.5 * (d + dr), i, f"+{dr - d:.1f} dB", ha="center", va="center",
                fontsize=9)
    ax.set_yticks(y, wfs)
    ax.set_xlabel(T[1])
    ax.set_ylabel(T[5])
    ax.set_xlim(0, dr * 1.10)
    ax.set_title(T[0], fontsize=11, pad=22)
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2,
              fontsize=8, framealpha=0.95)
    ax.grid(axis="x", alpha=0.3)
    _save(fig, "report06_adc_headroom.png")


def fig_farfield(J):
    """세 D 정의가 만드는 요구거리의 폭 — 정의를 섞으면 거리가 2배 틀린다."""
    T = ["Far-field distance 2D^2/lambda for the two purchased airframes",
         "Required range [m]", "Band",
         "D = envelope diagonal incl. rotor discs (adopted)",
         "D = bbox max horizontal extent", "D = motor-to-motor diagonal",
         "calibration sphere r = 17.8 cm", "DJI Matrice 4E", "DJI Mini 5 Pro"]
    assert_fig_text(*T)
    r6 = _load(R6)
    bands = list(r6["bands"].keys())
    xb = np.arange(len(bands))
    fig, ax = plt.subplots(figsize=(7.8, 3.6))
    for i, (dk, lbl, col) in enumerate(zip(AIR, (T[7], T[8]), ("#3b6ea5", "#5aa469"))):
        rows = [r for r in J["farfield"] if r["airframe"] == dk]
        env = [r["R_ff_env_m"] for r in rows]
        bb = [r["R_ff_bbox_m"] for r in rows]
        dg = [r["R_ff_diag_m"] for r in rows]
        off = (i - 0.5) * 0.34
        ax.bar(xb + off, env, width=0.3, color=col, alpha=0.85, label=lbl)
        ax.plot(xb + off, bb, "s", ms=5, color="#333333",
                label=T[4] if i == 0 else None)
        ax.plot(xb + off, dg, "v", ms=6, color="#b03030",
                label=T[5] if i == 0 else None)
    sph = [r6["farfield"]["sphere_r0.178"]["bands"][b]["R_ff_m"] for b in bands]
    ax.plot(xb, sph, "o--", color="#8a6bbf", ms=5, lw=1.2, label=T[6])
    top = max(r["R_ff_env_m"] for r in J["farfield"])
    ax.annotate(f"{top:.1f} m", xy=(xb[-1] - 0.17, top), xytext=(xb[-1] - 0.75, top * 0.92),
                fontsize=9, arrowprops=dict(arrowstyle="->", lw=0.9))
    ax.set_xticks(xb, [SHORT[b] + f"\n{r6['bands'][b]['fc_hz']/1e9:.3g} GHz" for b in bands])
    ax.set_xlabel(T[2])
    ax.set_ylabel(T[1])
    ax.set_title(T[0] + "\n" + T[3], fontsize=10)
    ax.legend(fontsize=8, ncol=2, framealpha=0.95)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "report06_farfield.png")


def fig_calibration(J):
    """교정구 반경을 어떻게 고르나 — 정확 Mie 가 기체 예상 σ 위에 있어야 한다."""
    from mie_pec_sphere import sphere_reference_set
    T = ["Calibration sphere: exact Mie sigma against the expected drone level",
         "Sphere radius [m]", "sigma [dBsm]", "optical limit pi*r^2",
         "DJI Matrice 4E, expected (anchor, L^2)", "DJI Mini 5 Pro, expected (anchor, L^2)",
         "r = 17.8 cm", "r = 25 cm"]
    assert_fig_text(*T)
    r6, mp = _load(R6), _load(MP)
    bands = list(r6["bands"].keys())
    rr = np.linspace(0.06, 0.32, 140)
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    cols = ("#3b6ea5", "#5aa469", "#c07830")
    for b, c in zip(bands, cols):
        f = r6["bands"][b]["fc_hz"]
        assert_fig_text(SHORT[b])
        ax.plot(rr, [sphere_reference_set(float(x), f)["mie_dbsm"] for x in rr],
                color=c, lw=1.5, label=f"Mie, {SHORT[b]}")
    ax.plot(rr, 10 * np.log10(np.pi * rr ** 2), "k--", lw=1.0, label=T[3])
    exp = mp["expected_sigma_dbsm_from_anchor"]["by_drone"]
    for dk, lbl, ls in zip(AIR, (T[4], T[5]), ("-.", ":")):
        lv = float(np.mean([exp[dk]["L2"][b] for b in bands]))
        ax.axhline(lv, color="#b03030", ls=ls, lw=1.2)
        ax.text(0.318, lv + 0.35, lbl, fontsize=8, color="#b03030", ha="right")
    for rs, lbl in zip(SPHERES, (T[6], T[7])):
        ax.axvline(float(rs), color="#777777", lw=0.9, alpha=0.7)
        ax.text(float(rs) - 0.004, -25.6, lbl, fontsize=8, rotation=90,
                color="#555555", va="bottom", ha="right")
    ax.set_xlabel(T[1])
    ax.set_ylabel(T[2])
    ax.set_ylim(-26, -3)
    ax.set_title(T[0], fontsize=11)
    ax.legend(fontsize=8, loc="upper left", ncol=2, framealpha=0.95)
    ax.grid(alpha=0.3)
    _save(fig, "report06_calibration.png")


def fig_size_law(J):
    """두 기체를 함께 재면 L² 와 L⁴ 가 반대 방향으로 갈린다."""
    T = ["L^2 versus L^4 size-transfer law, predicted from the anchor",
         "Frequency [GHz]", "mu [dBsm]", "L^2", "L^4",
         "Matrice 4E (larger than anchor)", "Mini 5 Pro (smaller than anchor)",
         "differential signature"]
    assert_fig_text(*T)
    r6 = _load(R6)
    bands = list(r6["bands"].keys())
    fg = [r6["bands"][b]["fc_hz"] / 1e9 for b in bands]
    fig, ax = plt.subplots(figsize=(7.4, 3.7))
    sl = J["size_law"]["by_airframe"]
    for dk, lbl, c in zip(AIR, (T[5], T[6]), ("#3b6ea5", "#5aa469")):
        ax.plot(fg, [sl[dk]["mu_L2_dbsm"][SHORT[b]] for b in bands], "o-",
                color=c, lw=1.8, ms=5, label=f"{lbl} · {T[3]}")
        ax.plot(fg, [sl[dk]["mu_L4_dbsm"][SHORT[b]] for b in bands], "s--",
                color=c, lw=1.6, ms=5, alpha=0.75, label=f"{lbl} · {T[4]}")
        y2 = sl[dk]["mu_L2_dbsm"][SHORT[bands[-1]]]
        y4 = sl[dk]["mu_L4_dbsm"][SHORT[bands[-1]]]
        ax.annotate("", xy=(fg[-1] + 0.18, y2), xytext=(fg[-1] + 0.18, y4),
                    arrowprops=dict(arrowstyle="<->", color=c, lw=1.2))
        ax.text(fg[-1] + 0.26, 0.5 * (y2 + y4), f"{abs(y4 - y2):.2f} dB",
                fontsize=8.5, color=c, va="center")
    ax.text(0.02, 0.05, f"{T[7]} = {J['size_law']['differential_db']:.2f} dB",
            transform=ax.transAxes, fontsize=9.5,
            bbox=dict(fc="#fff3cd", ec="#c0a030", lw=0.8))
    ax.set_xlim(fg[0] - 0.3, fg[-1] + 1.35)
    lo = min(sl[d][k][SHORT[b]] for d in AIR for k in ("mu_L2_dbsm", "mu_L4_dbsm")
             for b in bands)
    hi = max(sl[d][k][SHORT[b]] for d in AIR for k in ("mu_L2_dbsm", "mu_L4_dbsm")
             for b in bands)
    ax.set_ylim(lo - 2.2, hi + 1.2)
    ax.set_xlabel(T[1])
    ax.set_ylabel(T[2])
    ax.set_title(T[0], fontsize=11)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2,
              framealpha=0.95)
    ax.grid(alpha=0.3)
    _save(fig, "report06_size_law.png")


def fig_slope(J):
    """기울기 두 가설이 대역 끝에서 벌리는 간격 = 세션 재현성 요구치."""
    T = ["Frequency-slope hypotheses across the measured band span",
         "Frequency [GHz]", "mu, referenced to the low band [dB]",
         "our kernel (SBR+PO, no PTD)", "measurement anchor 0.21 dB/GHz",
         "gap at the top of the span", "DJI Matrice 4E", "DJI Mini 5 Pro"]
    assert_fig_text(*T)
    span = J["slope"]["span_ghz"]
    f0 = float(_load(R6)["slope_discrimination"]["f_lo_ghz"])
    fg = np.linspace(f0, f0 + span, 60)
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    a_anc = J["slope"]["anchor_db_per_ghz"]
    ax.plot(fg, a_anc * (fg - f0), "k-", lw=2.0, label=f"{T[4]}")
    for r, lbl, c, fr in zip(J["slope"]["rows"], (T[6], T[7]),
                             ("#3b6ea5", "#5aa469"), (0.28, 0.62)):
        ax.plot(fg, r["ours_db_per_ghz"] * (fg - f0), "--", color=c, lw=1.8,
                label=f"{T[3]} · {lbl} ({r['ours_db_per_ghz']:.2f} dB/GHz)")
        ax.annotate("", xy=(fg[-1], r["ours_db_per_ghz"] * span),
                    xytext=(fg[-1], a_anc * span),
                    arrowprops=dict(arrowstyle="<->", color=c, lw=1.3))
        ax.text(fg[-1] - 0.10, (fr * r["ours_db_per_ghz"] + (1 - fr) * a_anc) * span,
                f"{r['gap_db']:.2f} dB", fontsize=9, color=c, ha="right", va="center")
    ax.text(0.02, 0.92, T[5], transform=ax.transAxes, fontsize=9, color="#555555")
    ax.set_xlabel(T[1])
    ax.set_ylabel(T[2])
    ax.set_title(T[0], fontsize=11)
    ax.legend(fontsize=8, loc="upper left", framealpha=0.95)
    ax.grid(alpha=0.3)
    _save(fig, "report06_slope.png")


def fig_ground_bounce(J):
    """야외 지면반사 유령을 레인지게이팅으로 뗄 수 있는 기하는 어디까지인가."""
    T = ["Target-via-ground ghost: path difference against range resolution",
         "Ground range R [m]", "Path difference 2hH/R [m]",
         "antenna height h", "target height H", "range resolution c/2B"]
    assert_fig_text(*T)
    rows = J["ground_bounce"]
    hs = sorted({r["h_m"] for r in rows})
    Hs = sorted({r["H_m"] for r in rows})
    fig, ax = plt.subplots(figsize=(7.4, 3.7))
    cols = {h: c for h, c in zip(hs, ("#3b6ea5", "#5aa469", "#c07830"))}
    styles = {H: s for H, s in zip(Hs, (":", "--", "-"))}
    for h in hs:
        for H in Hs:
            sel = sorted([r for r in rows if r["h_m"] == h and r["H_m"] == H],
                         key=lambda r: r["R_m"])
            ax.plot([r["R_m"] for r in sel], [r["path_diff_m"] for r in sel],
                    styles[H], color=cols[h], lw=1.5, marker="o", ms=3.5,
                    label=f"h={h:.1f} m, H={H:.0f} m")
    for bw, c in zip((400, 200, 100), ("#999999", "#b03030", "#7a2020")):
        dr = C0 / (2 * bw * 1e6)
        ax.axhline(dr, color=c, lw=1.1, alpha=0.9)
        ax.text(51.5, dr + 0.06, f"B={bw} MHz  {T[5]} = {dr:.2f} m",
                fontsize=8, color=c, va="bottom")
    ax.set_xlabel(T[1])
    ax.set_ylabel(T[2])
    ax.set_xlim(18, 78)
    ax.set_title(T[0] + f"   ({T[3]}, {T[4]})", fontsize=10.5)
    ax.legend(fontsize=7.4, ncol=3, loc="upper right", framealpha=0.95)
    ax.grid(alpha=0.3)
    _save(fig, "report06_ground_bounce.png")


# =========================================================================== #
#  ③  노트북 블록
# =========================================================================== #
def blocks(J) -> list:
    D = from_json("outputs/report06_derived.json")
    M = from_json("outputs/report06_measurement.json")
    P = from_json("outputs/measurement_plan.json")
    A = from_json("outputs/sigma_anchor.json")
    B: list = []

    # ── 서두 6블록 ─────────────────────────────────────────────────────────
    B.append(header(
        num=6,
        title="실측 계획과 검증",
        question="무엇을 재면 시뮬레이션의 어느 주장이 결판나는가?",
        conclusion_lines=[
            "야외 비행시험은 **탐지통계**를 준다. **절대 σ 는 주지 않는다** — 같은 세션의 "
            "교정표적·배경차감·자세통제·원거리장이 추가로 있어야 나온다(§2).",
            f"원거리장 요구는 최대 "
            f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.1f}', unit='m')} "
            f"(Matrice 4E · WiFi, 로터 디스크 포함 외접 대각 기준).",
            f"주파수 기울기를 판정하려면 세션간 진폭 재현성이 "
            f"{D.num('slope.gap_db_min', fmt='{:.2f}', unit='dB')} 보다 좋아야 한다.",
            f"앵커의 최대 미해소 항인 크기법칙(L² vs L⁴, "
            f"{D.num('size_law.uncontrolled_size_db', fmt='{:.2f}', unit='dB')})은 "
            f"두 기체를 함께 재면 "
            f"{D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} 의 "
            f"차등신호로 갈린다(§4).",
            f"12-bit ADC 여유는 최소 "
            f"{M.num('adc.headroom_db_min', fmt='{:.1f}', unit='dB')} — "
            f"자유공간 기하 기준이고 야외 직접파에서는 줄어든다(§1).",
        ],
        claims=[
            "절대 σ 를 얻는 데 **무엇이 필요한가** — 6가지 요구조건과 각각의 수치 임계",
            "원거리장·각도표본·점표적·교정구·지면반사 분리의 **계산된 설계값**",
            "시뮬의 주장마다 **어느 측정이 결판내는가**(§4 결정표)",
            "장비 제약이 무엇을 막는가 — X410 12-bit ADC 여유",
        ],
        non_claims=[
            "**측정 결과** — 이 편에는 잰 값이 하나도 없다. 전부 설계값이다",
            "야외 비행시험만으로 절대 σ 가 나온다는 것 — 교정 없이는 상대값뿐이다",
            "시뮬 σ 의 정확도 — 이 편은 그것을 검증하지 않는다(02편이 경계를 긋는다)",
            "편파에 대한 예측 — 커널에 편파 자유도가 없어 예측 자체가 불가능하다",
            "야외 절대 탐지거리의 시뮬 대조 — 환경이 다르다(§3)",
        ],
        prereq=[("02 §4", "앵커가 무엇을 통제하고 무엇을 통제하지 못하는가"),
                ("03", "세 조명원(LTE·5G·WiFi)의 대역과 점유"),
                ("04", "명목 Pfa 와 경험 Pfa 를 왜 교정해야 하는가"),
                ("05", "자유공간에서 나온 탐지 결과가 무엇을 가정하는가")],
        repro=dict(
            cmd=["PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "
                 "\"import sigma_anchor as S; S.write_measurement_plan()\"",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "src/make_report06_measurement.py"],
            out=["outputs/report06_measurement.json", "outputs/measurement_plan.json",
                 "outputs/report06_derived.json"],
            runtime="약 10 초 (GPU 불필요)",
            note="긴 산문판 설계서는 `docs/MEASUREMENT_PLAN.md` 에 있고, 그 안의 수치표는 "
                 "`src/sigma_anchor.py:939` 가 자동 주입한다"),
    ))

    # ── §1 하드웨어 ────────────────────────────────────────────────────────
    B.append(md(
        "## §1. 하드웨어 — X410 한 대로 기준과 감시를 동시에",
        "",
        "TX 4채널 · RX 4채널이다. **RX0 = 기준 채널**(직접파), **RX1~3 = 감시 배열**로 쓴다.",
        "사양은 `src/experiment_x410.py:60`, 배치는 `src/experiment_x410.py:100` 한 곳에만 있다.",
        "",
        "⚠ **12-bit ADC 가 야외의 천장이다.** 직접파를 양자화하는 순간 그 아래는 못 지운다.",
        "그 한계 모형이 `src/experiment_x410.py:83` 의 `adc_quantize()` 다."))

    B.append(md(
        table(["항목", "값", "무엇을 제약하나"], [
            ["TX / RX 채널",
             M.num("hw.n_tx", fmt="{:.0f}") + " / " + M.num("hw.n_rx", fmt="{:.0f}"),
             "기준 1 + 감시 3 배분"],
            ["채널당 순시대역", M.num("hw.max_bw_mhz", fmt="{:.0f}", unit="MHz"),
             "거리분해능과 점표적 조건(§2-3)"],
            ["주파수 범위", D.num("hw_span.f_lo_mhz", fmt="{:.0f}", unit="MHz") + " ~ "
             + D.num("hw_span.f_hi_ghz", fmt="{:.1f}", unit="GHz"), "세 밴드 전부 커버"],
            ["ADC 동적범위", M.num("hw.dynamic_range_db", fmt="{:.2f}", unit="dB"),
             "직접파 제거의 천장"],
            ["감시배열 AoA 빔폭", M.num("hw.aoa_beamwidth_deg", fmt="{:.1f}", unit="°"),
             "각도 관측 — 디텍션에는 불필요"],
            ["최대대역 바이스태틱 ΔR",
             M.num("hw.range_res_bistatic_m_at_max_bw", fmt="{:.3f}", unit="m"),
             "표적이 여러 거리빈에 퍼진다(§2-3)"]]),
        "",
        f"원사양 출처는 `{M.get('hw.source')}` 한 곳이다."))

    B.append(md(
        "![adc headroom](outputs/figures/report06_adc_headroom.png)",
        "",
        caption(1, "12-bit ADC 는 직접파 대 잡음비 위에 얼마의 여유를 남기는가?"),
        "",
        f"가장 빡빡한 파형은 `{M.get('adc.worst_waveform')}` 이다 — 점유대역이 좁아 "
        f"기준채널 이득이 높다.",
        "",
        "⚠ 이 DNR 은 **자유공간 시뮬 기하**의 값이다⟨outputs/report06_measurement.json : "
        "adc.dnr_source⟩. 야외에서 송수신을 가깝게 놓으면 DNR 이 올라가 여유가 줄어든다."))

    # ── §2 탐지성능 vs 절대 σ ──────────────────────────────────────────────
    B.append(md(
        "## §2. ⭐ 탐지성능과 절대 σ 는 다른 실험이다",
        "",
        "야외 비행시험은 **탐지통계**(검출·오경보·최대거리)를 준다. σ 는 주지 않는다.",
        "σ 는 절대량이라 같은 세션 안에 기준이 있어야 하고, 자세와 환경이 통제되어야 한다.",
        "",
        table(["야외 비행시험이 이미 주는 것", "절대 σ 가 **추가로** 요구하는 것"], [
            ["표적 유/무의 검출·오경보 통계", "같은 세션·같은 지지대의 **알려진 σ 교정표적**"],
            ["같은 기하에서의 파형 간 상대 우열", "표적을 치운 **배경의 코히런트 차감**"],
            ["거리·도플러 응답의 존재", "엔코더 턴테이블로 **통제된 자세**"],
            ["링크가 닫히는지 여부", "**원거리장** 거리 또는 근접장 서브밴드 처리"],
            ["실제 클러터에서의 오경보율", "안테나 패턴·송수신 체인 이득 교정"]]),
        "",
        "다섯 줄 전부 조건까지 적힌 산문판이 `docs/MEASUREMENT_PLAN.md` §1-1~1-6 에 있다."))

    # ── §2-1 원거리장 ──────────────────────────────────────────────────────
    B.append(md(
        "### §2-1. 원거리장 — 얼마나 멀리 떨어져야 하나",
        "",
        f"`R_ff = 2D²/λ`. **D 정의를 섞으면 요구거리가 최대 "
        f"{D.num('farfield_adopted.spread_ratio_max', fmt='{:.2f}')}배 틀린다.**",
        "채택은 가장 보수적인 정의다 — 회전 로터 디스크까지 포함한 외접상자의 3D 대각.",
        "",
        D.table("farfield",
                [("기체", "airframe"), ("밴드", "band"), ("λ", "lam_mm"),
                 ("D_env", "D_env_m"), ("**R_ff(env)**", "R_ff_env_m"),
                 ("R_ff(bbox)", "R_ff_bbox_m"), ("R_ff(모터대각)", "R_ff_diag_m")],
                fmt={"lam_mm": "{:.0f} mm", "D_env_m": "{:.3f} m",
                     "R_ff_env_m": "{:.2f} m", "R_ff_bbox_m": "{:.2f} m",
                     "R_ff_diag_m": "{:.2f} m"})))

    B.append(md(
        "![farfield](outputs/figures/report06_farfield.png)",
        "",
        caption(2, "각 기체와 밴드에서 원거리장에 들어가려면 얼마나 멀어야 하는가?"),
        "",
        f"최대 요구는 {D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')} 다.",
        "교정구는 기체보다 요구거리가 낮으므로, 기체 기준 거리에 같은 자리로 놓으면 자동 만족이다."))

    # ── §2-2 교정 기준체 ───────────────────────────────────────────────────
    B.append(md(
        "### §2-2. 교정 기준체 — σ 를 절대량으로 만드는 유일한 장치",
        "",
        "**정밀 PEC 구**를 쓴다. 구는 방위무관이라 정렬 오차가 σ 에 안 들어간다.",
        "",
        "기준값은 πr²(광학 점근)이 아니라 **정확 Mie** 다.",
        "단일 출처는 `benchmark/mie_pec_sphere.py:207` 이고 자체검증 `selfcheck()` 을 갖고 있다.",
        "",
        "세션 **시작과 끝에 한 번씩** 잰다. 두 값의 차이가 그 세션의 드리프트 예산이다.",
        "그 차이가 목표 정확도보다 크면 그 세션 자료는 버린다."))

    B.append(md(
        D.table("calibration",
                [("구", "sphere"), ("밴드", "band"), ("ka", "ka"),
                 ("σ_Mie", "mie_dbsm"), ("Mie−πr²", "mie_minus_go_db"),
                 ("Matrice 4E 대비 여유", "margin_matrice4e_db"),
                 ("Mini 5 Pro 대비 여유", "margin_mini5pro_db")],
                fmt={"ka": "{:.1f}", "mie_dbsm": "{:+.2f} dBsm",
                     "mie_minus_go_db": "{:+.2f} dB",
                     "margin_matrice4e_db": "{:+.2f} dB",
                     "margin_mini5pro_db": "{:+.2f} dB"})))

    B.append(md(
        "![calibration](outputs/figures/report06_calibration.png)",
        "",
        caption(3, "어느 반경의 교정구가 세 밴드 모두에서 기체 예상 σ 위에 있는가?"),
        "",
        f"교정구는 기체보다 최소 "
        f"{D.num('calibration_margin_min_db', fmt='{:.2f}', unit='dB')} 밝다. "
        f"여유가 양수여야 같은 이득 설정으로 둘 다 잡히고, 그래야 비율이 σ 비율이 된다.",
        "",
        f"채택 반경은 {D.num('calibration_pick.radius_cm', fmt='{:.1f}', unit='cm')} 다 — "
        f"{D.get('calibration_pick.why')}"))

    # ── §2-3 점표적 조건 ───────────────────────────────────────────────────
    B.append(md(
        "### §2-3. 점표적 조건 — 순시대역을 통째로 쓰면 안 된다",
        "",
        "peak |s|² 를 σ 로 쓰려면 표적이 **한 거리빈 안**에 들어와야 한다.",
        f"두 기체를 함께 만족시키는 최대 서브밴드는 "
        f"{D.num('point_target_max_bw_MHz', fmt='{:.0f}', unit='MHz')} 다.",
        "서브밴드마다 σ 를 내면 그 다발이 곧 σ(f) 이고, 앵커 문헌의 절차와 같다.",
        "",
        D.table("point_target",
                [("대역 B", "B_MHz"), ("ΔR = c/2B", "dR_m"),
                 ("Matrice 4E", "matrice4e_ok"), ("여유", "matrice4e_margin_m"),
                 ("Mini 5 Pro", "mini5pro_ok"), ("여유", "mini5pro_margin_m")],
                fmt={"B_MHz": "{:.0f} MHz", "dR_m": "{:.3f} m",
                     "matrice4e_margin_m": "{:+.3f} m",
                     "mini5pro_margin_m": "{:+.3f} m"})))

    # ── §2-4 자세 통제 ─────────────────────────────────────────────────────
    B.append(md(
        "### §2-4. 자세 통제 — 각도표본이 성기면 로브를 놓친다",
        "",
        "방위는 엔코더 턴테이블로 돌리고, 표본 간격은 `λ/4D` 이하로 잡는다.",
        f"가장 촘촘한 요구는 {D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} "
        f"(`{D.get('aspect_finest_airframe')}` · `{D.get('aspect_finest_band')}`)이고, "
        f"한 바퀴에 {D.num('aspect_n_az_max', fmt='{:.0f}')} 표본이다.",
        "",
        "⚠ 앵커 문헌은 2° 를 썼고 본인들이 고주파에서 성길 수 있다고 적었다. 같은 선택을 하지 않는다.",
        "로터는 **정지**시키고 블레이드 방위를 기록한다 — 앵커가 회전 성분을 뺐으므로 맞춘다."))

    B.append(md(
        D.table("aspect",
                [("기체", "airframe"), ("밴드", "band"),
                 ("Δφ 나이퀴스트", "az_nyquist_deg"), ("Δφ 권장", "az_recommended_deg"),
                 ("한 바퀴 표본수", "n_az_per_turn"),
                 ("앵커 2° 보다 촘촘", "finer_than_anchor_2deg")],
                fmt={"az_nyquist_deg": "{:.2f}°", "az_recommended_deg": "{:.2f}°",
                     "n_az_per_turn": "{:.0f}"})))

    # ── §2-5 배경 차감과 지면반사 ──────────────────────────────────────────
    B.append(md(
        "### §2-5. 배경 차감과 지면반사 — 야외는 무향실이 아니다",
        "",
        "배경 S_BG 는 **지지대를 세운 채로** 재고 **복소수로** 뺀다.",
        "표적을 경유한 지면반사가 표적 리턴과 같은 거리빈에 들어오면 σ 가 오염된다.",
        "경로차 `2hH/R` 이 서브밴드 거리분해능보다 **커야** 레인지게이팅으로 뗀다.",
        "",
        "![ground bounce](outputs/figures/report06_ground_bounce.png)",
        "",
        caption(4, "어떤 야외 기하가 지면반사 유령을 표적 거리빈 밖으로 밀어내는가?"),
        "",
        f"{D.num('ground_bounce_n_geom', fmt='{:.0f}')}개 기하 중 "
        f"{D.num('ground_bounce_ref_bw_MHz', fmt='{:.0f}', unit='MHz')} 서브밴드에서 "
        f"분리되는 비율은 {D.num('ground_bounce_sep_frac_200MHz', fmt='{:.0%}')} 다. "
        f"안 되면 표적을 더 높이 띄우거나 안테나를 낮춘다."))

    # ── §3 시뮬 vs 실측 ────────────────────────────────────────────────────
    B.append(md(
        "## §3. 시뮬과 실측 — 무엇이 비교 가능하고 무엇이 아닌가",
        "",
        "**구조는 같고 환경은 다르다.** 이 한 줄이 §4 결정표의 마지막 열을 결정한다.",
        "",
        table(["같아서 비교 가능한 축", "달라서 비교 불가능한 축"], [
            ["바이스태틱 구조 — 기준 1 + 감시 3", "환경 — 시뮬은 자유공간, 실측은 지면반사·다중경로"],
            ["같은 기체 2종(Matrice 4E · Mini 5 Pro)", "클러터 — 시뮬에는 정적 산란체가 없다"],
            ["같은 세 파형(LTE · 5G · WiFi)", "동적범위 — 시뮬 ECA 는 무한, 실측은 12-bit"],
            ["같은 검출기 사슬(ECA → 거리도플러 → CA-CFAR)", "자세 — 시뮬은 각도격자, 비행 중에는 미통제"],
            ["σ 통계 규약(방위 선형평균)", "절대 탐지거리 — 링크예산의 전제가 다르다"]]),
        "",
        "실측이 결판낼 수 있는 것은 **σ 자체와 상대 순서**이고, 절대 탐지거리가 아니다."))

    B.append(md(
        "### §3-1. 앵커가 통제하지 못한 항 — 이 캠페인이 닫으러 가는 목록",
        "",
        A.table("uncontrolled",
                [("미통제 항목", "term"), ("상태", "status"), ("크기", "size_db")],
                fmt={"size_db": "{:+.2f} dB"}, null="미상")))

    B.append(md(
        "가장 큰 미해소 항(크기전이 법칙)이 실제로 적용된 보정 대부분보다 크다.",
        "그래서 이 캠페인의 첫 표적은 탐지성능이 아니라 **이 원장을 줄이는 것**이다.",
        "",
        table(["기체", "앵커 대비 등급", "크기비", "L² 보정", "L⁴ 보정"], [
            ["Matrice 4E", A.get("drones.matrice4e.comparability.verdict"),
             A.num("drones.matrice4e.comparability.size_ratio", fmt="{:.3f}"),
             A.num("drones.matrice4e.comparability.size_corr_L2_db", fmt="{:+.2f}", unit="dB"),
             A.num("drones.matrice4e.comparability.size_corr_L4_db", fmt="{:+.2f}", unit="dB")],
            ["Mini 5 Pro", A.get("drones.mini5pro.comparability.verdict"),
             A.num("drones.mini5pro.comparability.size_ratio", fmt="{:.3f}"),
             A.num("drones.mini5pro.comparability.size_corr_L2_db", fmt="{:+.2f}", unit="dB"),
             A.num("drones.mini5pro.comparability.size_corr_L4_db", fmt="{:+.2f}", unit="dB")]]),
        "",
        "등급이 다르면 같은 보정이라도 뜻이 다르다 — 두 기체 다 `scaled` 이지 `direct` 가 아니다."))

    # ── §4 결정표 ──────────────────────────────────────────────────────────
    B.append(md(
        "## §4. ⭐ 결정표 — 어느 측정이 어느 주장을 결판내는가",
        "",
        "왼쪽은 시뮬이 지금 하는 주장, 가운데는 그것을 건드리는 측정, 오른쪽은 **판정 임계**다.",
        "임계를 못 맞추면 그 행은 미결로 남는다.",
        "",
        table(["02편의 주장", "결판내는 측정", "판정 임계"], [
            ["자세에 따른 σ 의 **구조**(로브 위치)는 기하에서 나온다",
             "턴테이블 방위컷, 정지 로터",
             f"Δφ ≤ {D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} (§2-4)"],
            ["**절대 레벨은 우리 것이 아니다** — 앵커에서 받는다",
             "같은 세션 교정구 + 배경 코히런트 차감",
             f"교정구 여유 ≥ {D.num('calibration_margin_min_db', fmt='{:.2f}', unit='dB')} (§2-2)"],
            ["**주파수 기울기도 우리 것이 아니다** — PO 에 회절항이 없다",
             "세 밴드를 같은 세션에서 측정",
             f"세션 재현성 < {D.num('slope.gap_db_min', fmt='{:.2f}', unit='dB')} (§4-1)"],
            ["크기전이 법칙 L² / L⁴ 는 **미해소**다",
             "두 기체를 한 캠페인에서 측정",
             f"차등 {D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} (§4-2)"],
            ["편파는 **미해소**다 — 커널에 편파 자유도가 없다",
             "VV / VH / HV / HH 4조합",
             "무편파 스칼라 모형의 오차를 처음으로 숫자화"]])))

    B.append(md(
        table(["03~05편의 주장", "결판내는 측정", "판정 임계"], [
            ["파형별 점유·대역폭 대가는 σ 와 무관하게 정확하다(03)",
             "X410 이 같은 기하에서 세 파형을 송신",
             "σ 무관량이라 **반증 대상이 아니다** — 사슬 확인용"],
            ["명목 Pfa 를 교정해야 파형 비교가 성립한다(04)",
             "표적 없는 배경 CPI 를 길게 녹화해 CFAR 임계 넘김을 센다",
             "실제 클러터로 교정이 전이되는가 — 통제 Pfa 는 시뮬만 가능"],
            ["자유공간에서 어느 조명원이 어느 거리까지 보이나(05)",
             "야외 고정기하 탐지시험",
             "**절대 거리는 비교 불가**(§3). 파형 간 순서만 본다"],
            ["12-bit ADC 가 직접파 제거의 천장이다(§1)",
             "직접파를 실제로 받아 ECA 잔차를 잰다",
             f"여유 {M.num('adc.headroom_db_min', fmt='{:.1f}', unit='dB')} 가 "
             f"야외에서 얼마나 줄어드는가"]])))

    B.append(md(
        "### §4-1. 기울기 — 세션 재현성이 판정의 문턱이다",
        "",
        "![slope](outputs/figures/report06_slope.png)",
        "",
        caption(5, "우리 기울기와 앵커 기울기를 가르려면 세션 재현성이 얼마나 좋아야 하는가?"),
        "",
        f"우리 커널은 {D.num('slope.rows[0].ours_db_per_ghz', fmt='{:.3f}')} ~ "
        f"{D.num('slope.rows[1].ours_db_per_ghz', fmt='{:.3f}')} dB/GHz 이고 앵커는 "
        f"{D.num('slope.anchor_db_per_ghz', fmt='{:.2f}')} dB/GHz 다. "
        f"대역 {D.num('slope.span_ghz', fmt='{:.3f}', unit='GHz')} 를 지나며 두 가설이 "
        f"{D.num('slope.gap_db_min', fmt='{:.2f}')} ~ "
        f"{D.num('slope.rows[1].gap_db', fmt='{:.2f}')} dB 벌어진다.",
        "",
        f"기울기의 정의는 하나로 고정한다 — {D.num('slope.fit_note_short')}."))

    B.append(md(
        "### §4-2. 크기법칙 — 두 기체를 함께 사는 이유",
        "",
        "![size law](outputs/figures/report06_size_law.png)",
        "",
        caption(6, "두 기체를 함께 재면 L² 와 L⁴ 를 가를 수 있는가?"),
        "",
        f"Matrice 4E 는 앵커보다 크고(크기비 "
        f"{D.num('size_law.by_airframe.matrice4e.size_ratio', fmt='{:.3f}')}), Mini 5 Pro 는 "
        f"작다({D.num('size_law.by_airframe.mini5pro.size_ratio', fmt='{:.3f}')}). "
        f"두 법칙의 예측이 **반대 방향**으로 갈리므로 한 대만 재면 레벨 오차와 구별되지 않는다.",
        "",
        f"차등신호 {D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} 가 "
        f"두 기체를 함께 사는 이유다."))

    # ── 재현용 코드 셀 ─────────────────────────────────────────────────────
    B.append(code(
        "# 이 편의 숫자를 직접 열어보기 — 표·그림의 모든 값은 아래 JSON 에서 나온다.",
        "import json",
        "D = json.load(open('outputs/report06_derived.json'))",
        "print(json.dumps(D['_meta']['definitions'], ensure_ascii=False, indent=1))",
        "print('원거리장 채택 :', D['farfield_adopted'])",
        "print('기울기 판별폭 :', [(r['airframe'], round(r['gap_db'], 2))",
        "                          for r in D['slope']['rows']])",
        "print('크기법칙 차등 :', round(D['size_law']['differential_db'], 2), 'dB')"))

    # ── 이 편의 한계 ───────────────────────────────────────────────────────
    B.append(limits([
        ("아무것도 측정하지 않았다 — 이 편은 전부 설계값이다",
         "기체 2종 입고 후 §2 의 6조건대로 세션을 돌리고, 산출물을 "
         "`outputs/measured_sigma.json` 으로 굳혀 `src/sigma_anchor.py:788` 의 앵커를 교체한다"),
        ("장비 선택이 미결이다 — VNA 가 σ(f) 에는 정도이고 X410 은 보유 장비다",
         "`docs/MEASUREMENT_PLAN.md` §2 의 비교표에서 하나를 고르고, X410 이면 §1-1 "
         "교정 절차를 더 엄격히 적용한다"),
        ("편파 축이 커널에 없다 — VV 를 재도 붙일 곳이 없다",
         "`src/materials.py` 의 `gamma_po()` 를 편파 의존 프레넬로 바꿀지 먼저 결정한다"),
        ("바이스태틱 측정 설계가 없다 — 이 편의 수치는 전부 모노스태틱 기준이다",
         "β≤45° 제한 안에서 송수신 분리각별 기하를 §2-1·§2-5 와 같은 방식으로 계산한다"),
        ("마이크로도플러 세션이 설계에 없다",
         "정지 로터 세션과 **별도**로 회전 세션을 잡는다 — 앵커와의 사과-대-사과를 깨지 않기 위해서다"),
        ("지면반사 분리는 평탄지면 2hH/R 근사만 본다",
         "실제 부지의 지형·반사체를 넣은 기하로 §2-5 표를 다시 계산한다"),
    ], sec="§5."))

    return B


# =========================================================================== #
def main():
    print("── 리포트 06 빌드 ──")
    J = derive()
    fig_adc(J)
    fig_farfield(J)
    fig_calibration(J)
    fig_size_law(J)
    fig_slope(J)
    fig_ground_bounce(J)
    rep = build_notebook(NB_OUT, blocks(J), strict=True)
    print(f"✅ {os.path.relpath(NB_OUT, _ROOT)}")
    return rep


if __name__ == "__main__":
    main()
