# -*- coding: utf-8 -*-
"""
md_snr_vs_range.py — ⭐**거리와 SNR 을 잇는 길** 하나 (원장: outputs/md_snr_vs_range.json)

무엇을 하나
------------
σ · 거리 · EIRP · 안테나이득에서 SNR(R) 을 세우고, 그 역(«이 SNR 은 몇 m 인가»)도 낸다.
**세 층위를 항상 함께** 낸다 — 표본당 SNR(정합필터 전) · 정합필터 이득 · STFT 조각 이득.

⭐ 재구현 금지 규약을 지킨다 — 새로 지어낸 수가 **하나도 없다**:
  σ (방위평균)      ← outputs/md_range_sweep*.json  `rows[].sigma_eq_aspect_mean_plane_dbsm`
  dc_ac (기체별)    ← 같은 파일        `rows[].arms.A0_reference.dc_ac_db`
  링크버짓 상수     ← src/microdoppler_nearfield.py  DECLARED_*  (챔버 12 dBm)
  매크로 EIRP       ← benchmark/link_budget.py       (63 dBm)
  사다리·역함수     ← src/microdoppler_nearfield.py  snr_ladder() · range_for_snr_db()
  분류 정확도       ← outputs/md_classify.json       `noise[<AC SNR dB>][arm][clf]`  (거리만 붙인다)
  관측성 R90        ← outputs/md_range_sweep_mf.json (실측 — 잡음 실현에서 센다)

⚠ 전제 배지(원장 meta 에 그대로 박는다)
  capture  = full_waveform  (정합필터 이득 10log10(B/PRF) 이 붙는 조건)
  noise    = thermal_only   (클러터·직접파 잔류·ECA 노치·위상잡음 없음)
  geometry = monostatic_equivalent (R_t = R_r = R → −40 dB/decade)
             ⚠ 바이스태틱으로 한 다리만 움직이면 −20 dB/decade 다. 원장에 둘 다 적는다.

실행:
    cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/md_snr_vs_range.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import microdoppler_nearfield as nf                     # noqa: E402

OUT = os.path.join(ROOT, "outputs", "md_snr_vs_range.json")
SWEEP_NEW = os.path.join(ROOT, "outputs", "md_range_sweep_mf.json")
SWEEP_OLD = os.path.join(ROOT, "outputs", "md_range_sweep.json")
CLASSIFY = os.path.join(ROOT, "outputs", "md_classify.json")

PRF = 20000.0
N_T = 6144                     # md_metrics 의 전창 FFT 길이 (한 조각 = CPI 전체)
MAP_NPERSEG = 70               # flash_spec 맵 한 조각(19.7 kHz·126.7 Hz 플래시 규약)
EIRP_ARMS = {"chamber_12dBm": 12.0, "macro_gnb_63dBm": 63.0}
#: 사다리를 그릴 거리 격자 [m] — 산술이라 촘촘해도 공짜다
R_GRID = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 27.3, 30.0, 40.0, 50.0,
          70.0, 100.0, 150.0, 200.0, 300.0, 500.0, 1000.0]
#: 「이 SNR 은 몇 m 인가」를 낼 문턱 [dB]
THRESH_DB = [20.0, 13.0, 10.0, 6.0, 3.0, 0.0, -3.0, -6.0, -10.0, -15.0, -20.0]


def _load(path):
    with open(path) as f:
        return json.load(f)


def _sweep_source(prefer_new=True):
    """σ·dc_ac 를 읽을 원장. 새 원장이 있으면 그쪽(같은 σ 계산이지만 최신)."""
    if prefer_new and os.path.exists(SWEEP_NEW):
        return SWEEP_NEW
    return SWEEP_OLD


def cell_inputs(doc, path):
    """원장에서 (drone, band) 마다 σ·dc_ac 를 뽑는다. **여기서 계산하는 것은 없다.**"""
    out = []
    for c in doc["cells"]:
        r0 = c["rows"][0]
        sig_db = float(r0["sigma_eq_aspect_mean_plane_dbsm"])
        # 평면파 방위평균 σ 는 거리에 무관해야 한다 — 원장 안에서 그것을 확인한다(정직성).
        spread = max(abs(float(r["sigma_eq_aspect_mean_plane_dbsm"]) - sig_db)
                     for r in c["rows"])
        out.append(dict(
            drone=c["drone"], band=c["band"], fc_hz=float(c["fc_hz"]),
            sigma_dbsm=sig_db, sigma_m2=10.0 ** (sig_db / 10.0),
            sigma_source=f"{os.path.relpath(path, ROOT)}::cells[].rows[0]."
                         "sigma_eq_aspect_mean_plane_dbsm (azimuth mean over 36 aspects)",
            sigma_range_spread_db=float(spread),
            dc_ac_db=float(r0["arms"]["A0_reference"]["dc_ac_db"]),
            dc_ac_source=f"{os.path.relpath(path, ROOT)}::cells[].rows[0].arms."
                         "A0_reference.dc_ac_db (plane-wave noiseless reference)",
            f_tip_hz=float(c["f_tip_hz"]), flash_hz=float(c["flash_hz"]),
            r_ff_m=float(c["r_ff_m"])))
    return out


def ladder_rows(ci, eirp_dbm, capture="full_waveform", nperseg=N_T):
    rows = []
    for R in R_GRID:
        lad = nf.snr_ladder(ci["sigma_m2"], R, ci["fc_hz"], prf=PRF, capture=capture,
                            dc_ac_db=ci["dc_ac_db"], nperseg=nperseg, window="hann",
                            eirp_dbm=eirp_dbm)
        rows.append(dict(
            R_m=float(R),
            # ⭐ 세 층위 — 키 이름에 층위가 박혀 있다
            snr_sample_db=round(float(lad["snr_sample_db"]), 4),     # ① 정합필터 **전**
            gain_mf_db=round(float(lad["gain_mf_db"]), 4),           # ②
            snr_slow_db=round(float(lad["snr_slow_db"]), 4),         # ③ 슬로타임 총전력
            dc_ac_off_db=round(float(lad["dc_ac_off_db"]), 4),
            snr_slow_ac_db=round(float(lad["snr_slow_ac_db"]), 4),   # ③′ ⭐정본
            gain_stft_db=round(float(lad["gain_stft_db"]), 4),       # ④
            snr_map_ac_db=round(float(lad["snr_map_ac_db"]), 4),     # ⑤
        ))
    return rows


def crossings(ci, eirp_dbm, capture="full_waveform", nperseg=N_T):
    """문턱마다 «몇 m 인가» — 사다리의 닫힌형 역함수(range_for_snr_db)."""
    kw = dict(prf=PRF, capture=capture, dc_ac_db=ci["dc_ac_db"],
              nperseg=nperseg, window="hann", eirp_dbm=eirp_dbm)
    out = {}
    for rung in ("snr_slow_db", "snr_slow_ac_db", "snr_map_ac_db"):
        out[rung] = {f"{t:g}": round(nf.range_for_snr_db(t, ci["sigma_m2"], ci["fc_hz"],
                                                         rung=rung, legs="both", **kw), 3)
                     for t in THRESH_DB}
    return out


def region_two(ci, eirp_dbm, capture="full_waveform"):
    """⭐«검출은 되는데 마이크로도플러는 안 보이는» 구간 — ③ > 0 dB 이면서 ③′ < 0 dB.

    선행연구 대응물: arXiv:2402.04368 Fig. 4(b) 가 같은 구간을 그림 하나에 라벨로 표시한다.
    우리는 그 경계를 **계산**한다 — 폭이 정확히 dc_ac_off_db 의 1/4 decade 다."""
    kw = dict(prf=PRF, capture=capture, dc_ac_db=ci["dc_ac_db"], eirp_dbm=eirp_dbm)
    r_ac0 = nf.range_for_snr_db(0.0, ci["sigma_m2"], ci["fc_hz"], rung="snr_slow_ac_db", **kw)
    r_tot0 = nf.range_for_snr_db(0.0, ci["sigma_m2"], ci["fc_hz"], rung="snr_slow_db", **kw)
    off = nf.dc_ac_offset_db(ci["dc_ac_db"], exact=True)
    return dict(inner_m=round(r_ac0, 3), outer_m=round(r_tot0, 3),
                width_db=round(float(off), 4), width_ratio=round(r_tot0 / r_ac0, 4),
                meaning="between these two ranges the echo is above the noise (a detector sees "
                        "the target) but the blade line is not (no micro-Doppler)")


# --------------------------------------------------------------------------- #
#  분류 정확도 → 거리 (⭐정확도를 **다시 계산하지 않는다**. 거리만 붙인다)
# --------------------------------------------------------------------------- #
def classify_vs_range(cells_by_drone, capture="full_waveform"):
    if not os.path.exists(CLASSIFY):
        return dict(available=False, why=f"{os.path.relpath(CLASSIFY, ROOT)} 이 없다")
    doc = _load(CLASSIFY)
    noise = doc.get("noise", {})
    if not noise:
        return dict(available=False, why="md_classify.json 에 noise 팔이 없다")
    meta = doc.get("_meta", {})
    rows = []
    for snr_key in sorted(noise, key=lambda s: -float(s)):
        s_ac = float(snr_key)
        rec = dict(snr_slow_ac_db=s_ac,
                   accuracy=noise[snr_key].get("all", {}),
                   range_m={})
        for drone, ci in cells_by_drone.items():
            arm = {}
            for name, eirp in EIRP_ARMS.items():
                arm[name] = round(nf.range_for_snr_db(
                    s_ac, ci["sigma_m2"], ci["fc_hz"], rung="snr_slow_ac_db",
                    prf=PRF, capture=capture, dc_ac_db=ci["dc_ac_db"], eirp_dbm=eirp), 2)
            rec["range_m"][drone] = arm
        rows.append(rec)
    return dict(
        available=True,
        source=os.path.relpath(CLASSIFY, ROOT),
        accuracy_is_reused="accuracy numbers are copied from md_classify.json; only the range "
                           "column is computed here",
        snr_axis_is="snr_slow_ac_db (AC / blade line) - the classifier injects noise with "
                    "reference='ac', which is exactly rung 3'",
        chance=meta.get("chance_accuracy"),
        window_s=meta.get("window_s"), prf_hz=meta.get("prf_main_hz"),
        airframes=meta.get("airframes"),
        caveat="the per-airframe dc_ac_db differs by up to 20 dB, so the SNR->range map is "
               "per airframe; the accuracy column is the 6-class pooled accuracy",
        rows=rows)


# --------------------------------------------------------------------------- #
#  실측 관측성 (새 스윕 원장에서) — R90
# --------------------------------------------------------------------------- #
def observability(path):
    """⭐**R90** — 잡음 실현의 90 % 에서 블레이드선이 아직 보이는 최대 거리.

    «보인다» 의 정의는 `md_metrics` 가 이미 갖고 있다: 평활 주기도의 첨두가 잡음바닥 대비
    10 dB 미만이면 `fd_edge_hz = NaN`(= 묻혔다). 원장은 유효 실현 수를 함께 적으므로
    유효 몫을 거리에 대해 보고 0.9 를 지나는 자리를 로그거리로 선형보간한다."""
    if not os.path.exists(path):
        return dict(available=False, why=f"{os.path.relpath(path, ROOT)} 이 아직 없다")
    doc = _load(path)
    cap = doc["meta"].get("slow_time", {}).get("capture", "?")
    out = []
    for c in doc["cells"]:
        n_noise = int(doc["meta"].get("n_noise", 8))
        for arm in ("A1_snr_only", "A3_both"):
            R, frac, peak = [], [], []
            for r in c["rows"]:
                a = r["arms"][arm]
                nv = a.get("fd_edge_hz_n_valid", None)
                f = (float(nv) / n_noise) if nv is not None else (
                    1.0 if a.get("fd_edge_hz") is not None else 0.0)
                R.append(float(r["R_m"])); frac.append(f)
                peak.append(a.get("spec_peak_over_floor_db"))
            # 1000 m 앵커는 «원거리장 수렴» 용이라 관측성 곡선에서 뺀다(단조성 판단만 방해)
            keep = [i for i, x in enumerate(R) if x <= 500.0]
            R = [R[i] for i in keep]; frac = [frac[i] for i in keep]
            peak = [peak[i] for i in keep]
            out.append(dict(drone=c["drone"], band=c["band"], arm=arm,
                            capture=cap, n_noise=n_noise,
                            R_m=R, valid_fraction=frac,
                            spec_peak_over_floor_db=peak,
                            R90_m=_cross_down(R, frac, 0.9),
                            R50_m=_cross_down(R, frac, 0.5),
                            R_peak10dB_m=_cross_down(R, [p if p is not None else float("nan")
                                                         for p in peak], 10.0)))
    return dict(available=True, source=os.path.relpath(path, ROOT), capture=cap,
                definition="R90 = largest range where >=90% of the noise realisations still "
                           "yield a finite fd_edge_hz (md_metrics declares NaN when the smoothed "
                           "periodogram peak is <10 dB over its own median floor)",
                cells=out)


def _cross_down(x, y, level):
    """단조 감소하는 y(x) 가 level 을 지나는 x — 로그거리 선형보간. 못 지나면 None."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 2 or y[0] < level:
        return None
    for i in range(1, len(x)):
        if y[i] < level <= y[i - 1]:
            lx0, lx1 = np.log10(x[i - 1]), np.log10(x[i])
            t = (y[i - 1] - level) / max(y[i - 1] - y[i], 1e-12)
            return round(float(10.0 ** (lx0 + t * (lx1 - lx0))), 3)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--capture", default="full_waveform",
                    choices=["full_waveform", "pre_mf", "always_on_pilot"])
    ap.add_argument("--sweep", default="", help="σ·dc_ac 를 읽을 원장(기본: 새 것 → 옛 것)")
    a = ap.parse_args()

    t0 = time.time()
    src = a.sweep or _sweep_source()
    doc = _load(src)
    cis = cell_inputs(doc, src)
    head = {ci["drone"]: ci for ci in cis if ci["band"] == "5G NR 3.5 GHz"}

    cells = []
    for ci in cis:
        arms = {}
        for name, eirp in EIRP_ARMS.items():
            arms[name] = dict(
                eirp_dbm=eirp,
                rows=ladder_rows(ci, eirp, a.capture),
                range_at_threshold_m=crossings(ci, eirp, a.capture),
                region_ii_detected_but_no_microdoppler=region_two(ci, eirp, a.capture))
        cells.append(dict(**ci, capture=a.capture, prf_hz=PRF,
                          geometry="monostatic_equivalent",
                          slope_db_per_decade=dict(monostatic_both_legs=-40.0,
                                                   bistatic_one_leg=-20.0),
                          eirp_arms=arms))

    g_mf = float(nf.matched_filter_gain_db(nf.DECLARED_B_HZ, PRF, capture=a.capture))
    doc_out = dict(
        _meta=dict(
            title="micro-Doppler SNR ladder vs range (the bridge between sigma and metres)",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            generator="benchmark/md_snr_vs_range.py",
            convention=nf.SNR_CONVENTION, canonical_rung=nf.CANONICAL_SNR_KEY,
            capture=a.capture, noise="thermal_only", geometry="monostatic_equivalent",
            three_layers=dict(
                snr_sample_db="rung 1 - per Rx sample, BEFORE the matched filter, over B=100 MHz",
                gain_mf_db=f"rung 2 - 10log10(B/PRF) = {g_mf:.2f} dB, ONE PRI correlated, "
                           "full-waveform capture only",
                gain_stft_db=f"rung 4 - 10log10(nperseg)+window loss; here nperseg = {N_T} "
                             "(md_metrics takes one full-record Hann FFT)",
                do_not_confuse=dict(
                    gain_mf_db=round(g_mf, 4),
                    cpi_coherent_gain_db=round(float(10 * np.log10(N_T)) - 1.76, 4),
                    map_frame_gain_db=round(float(10 * np.log10(MAP_NPERSEG)) - 1.76, 4),
                    note="three separate ~37/37/17 dB quantities; the map only ever shows the "
                         "third one")),
            link_budget=dict(eirp_dbm=EIRP_ARMS, rx_gain_dbi=nf.DECLARED_RX_GAIN_DBI,
                             noise_figure_db=nf.DECLARED_NF_DB, b_hz=nf.DECLARED_B_HZ,
                             noise_bw_effective_hz=(PRF if a.capture == "full_waveform"
                                                   else nf.DECLARED_B_HZ),
                             provenance="EIRP 12 dBm DECLARED (chamber class, no source doc); "
                                        "63 dBm is the macro-gNB value used in "
                                        "benchmark/link_budget.py"),
            reuse=dict(sigma=os.path.relpath(src, ROOT),
                       ladder="src/microdoppler_nearfield.py::snr_ladder",
                       inverse="src/microdoppler_nearfield.py::range_for_snr_db",
                       accuracy="outputs/md_classify.json (copied, not recomputed)"),
            caveats=[
                "sigma is our SBR/PO far-field-equivalent value and is 3.78 dB (2.39x) above the "
                "Das bistatic measurement anchor; in range that is a factor 0.79 - the range "
                "columns carry that unresolved uncertainty",
                "gain_mf_db assumes an ideal matched filter and a clean reference channel; the "
                "real two-channel passive chain loses part of it (benchmark/passive_two_channel_md.py)",
                "gain_stft_db for a single STFT frame is our extrapolation of Braun eq (3.37), "
                "which is stated for a 2-D periodogram - no primary source for one STFT frame",
                "an ECA zero-Doppler notch would remove the body DC and drive dc_ac_off_db to 0, "
                "which would move every AC row up by up to 37 dB - unmeasured",
                "always-on pilots (LTE CRS 1 kHz, 5G SSB 50 Hz) cannot produce a 20 kHz slow time; "
                "for those arms capture='always_on_pilot' and gain_mf_db = 0"],
            runtime_s=round(time.time() - t0, 2)),
        cells=cells,
        classification_vs_range=classify_vs_range(head, a.capture),
        observability_measured=observability(SWEEP_NEW),
    )
    tmp = a.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc_out, f, indent=1, ensure_ascii=False, default=float)
    os.replace(tmp, a.out)

    print(f"σ·dc_ac source: {os.path.relpath(src, ROOT)}   capture={a.capture}   "
          f"gain_mf={g_mf:.2f} dB")
    for c in cells:
        if c["band"] != "5G NR 3.5 GHz":
            continue
        ch = c["eirp_arms"]["chamber_12dBm"]
        mo = c["eirp_arms"]["macro_gnb_63dBm"]
        print(f"  {c['drone']:11s} σ={c['sigma_dbsm']:7.2f} dBsm  dc_ac={c['dc_ac_db']:5.1f} dB | "
              f"R(AC 0 dB) 12 dBm {ch['range_at_threshold_m']['snr_slow_ac_db']['0']:8.2f} m   "
              f"63 dBm {mo['range_at_threshold_m']['snr_slow_ac_db']['0']:9.2f} m | "
              f"region II {ch['region_ii_detected_but_no_microdoppler']['inner_m']:.1f}"
              f"–{ch['region_ii_detected_but_no_microdoppler']['outer_m']:.1f} m")
    print(f"\n→ {os.path.relpath(a.out, ROOT)}  ({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main()
