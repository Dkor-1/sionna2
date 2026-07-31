# -*- coding: utf-8 -*-
"""make_report03_illuminators.py — `report03_illuminators.ipynb` 생성기

리포트 03 **조명원 — 세 파형과 그 대가**
질문: *패시브 레이더가 빌려 쓸 수 있는 상시 신호는 무엇이고, 그 선택은 몇 dB 의 대가를 치르는가?*

이 파일이 하는 일 (순서대로)
---------------------------------------------------------------------------
1. `outputs/report03_illuminators.json` 을 **계산해서 쓴다** — 상위 JSON 에 스칼라로
   존재하지 않는 파생량(기준신호 에너지, λ² 격차, 점유 대가)만. 항목마다 `from` 에
   어느 상위 JSON/코드에서 왔는지 박는다.
2. 그림 3장을 그린다 — `outputs/figures/report03_{cost_ledger,af_mainlobe,af_sidelobe}.png`.
   나머지 4장은 `src/viz_report2.py` 가 이미 만든 것을 재사용한다.
3. `src/report_style.py` 의 규약(docs/REBUILD_2026-07-30.md §5)으로 노트북을 조립한다.

⚠ 노트북은 **생성물**이다. `report03_illuminators.ipynb` 를 직접 고치지 말고 이 파일을 고쳐라.
⚠ 본문 숫자는 **전부** `num()` 을 통과한다 — JSON 과 어긋나면 빌드가 멈춘다. 손으로 친 숫자 0개.
⚠ 이 파일은 다른 편의 빌더·`report_style.py`·`rcs_sbr.py` 를 건드리지 않는다.

실행:  cd /home/yunjung/workspace/sionna2 && \
       PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report03_illuminators.py
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#  BLAS 스레드 상한 — numpy import 전에 잡아야 먹는다(같은 박스에서 다른 작업이 동시에 돈다).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np                                                    # noqa: E402

from report_style import (assert_fig_text, build_notebook, caption,    # noqa: E402
                          code, fetch, header, limits, md, num, table)

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")
NB = os.path.join(ROOT, "report03_illuminators.ipynb")

#: 이 편이 인용하는 상위 JSON — 전부 다른 실험이 남긴 것이다.
J_WAVE = "outputs/report2_waveform_rcs.json"     # 파형 제원 + Sionna 교차대조
J_AMB = "outputs/verify_ambiguity.json"          # 모호함수(검출기와 동일 커널)
J_FIX = "outputs/report4_fixups.json"            # 링크버짓 규약 상수(듀티·√(B/fs)·CPI)
J_MTX = "outputs/report5_results.json"           # 점유×EIRP 검출 몬테카를로
J_LED = "outputs/report03_illuminators.json"     # ← 이 파일이 만든다

C0 = 299_792_458.0
STDS = ("wifi", "lte", "nr")
COL = {"wifi": "#ef6c00", "lte": "#00897b", "nr": "#c62828"}
SHORT = {"wifi": "WiFi", "lte": "LTE", "nr": "5G NR"}


# =========================================================================== #
#  1) 파생 원장 — outputs/report03_illuminators.json
# =========================================================================== #
def _pd50_eirp(rows, occ, thr=0.5):
    """`occ` 격자가 Pd ≥ thr 를 처음 넘는 EIRP[dBm]. 격자 안에서 못 넘으면 예외."""
    rr = sorted((r for r in rows if r["occ"] == occ), key=lambda r: r["eirp_dbm"])
    hit = next((r["eirp_dbm"] for r in rr if r["pd"] >= thr), None)
    if hit is None:
        raise RuntimeError(
            f"점유 {occ} 가 EIRP 격자 안에서 Pd≥{thr} 를 못 넘는다 — "
            f"{J_MTX}:A_occupancy 를 더 넓은 EIRP 로 다시 돌려야 원장을 쓸 수 있다.")
    return hit


def build_ledger(path: str = J_LED) -> dict:
    """상위 JSON 에 **스칼라로 없는** 파생량만 계산해 기록한다.

    원칙: 상위 JSON 에 그대로 있는 값은 여기 복사하지 않는다(리포트가 원본을 직접 인용한다).
          여기 들어오는 것은 ① 격자를 다시 만들어야 나오는 에너지, ② 두 값의 비, ③ 표 스캔뿐.
    """
    from waveforms import all_waveforms                 # CPU 수 초 — 격자를 다시 세운다

    grids: dict[str, dict] = {}
    for occ in ("G1", "G3"):
        wfs = all_waveforms(occ)
        g = {}
        for k in STDS:
            wf = wfs[k]
            e_ref = float(np.sum(np.abs(wf.ref) ** 2))
            e_tx = float(np.sum(np.abs(wf.tx) ** 2))
            g[k] = dict(
                name=wf.name, ref_name=wf.ref_name,
                carrier_hz=float(wf.carrier_hz), bw_hz=float(wf.bw_hz),
                ref_bw_hz=float(wf.ref_bw_hz),
                drb_m=float(wf.range_resolution_m),
                prf_hz=float(wf.pilot_rate_hz),
                occupancy_frac=float(wf.occupancy_frac),
                e_ref_db=float(10 * np.log10(e_ref + 1e-30)),
                e_tx_db=float(10 * np.log10(e_tx + 1e-30)),
                e_ref_over_tx_db=float(10 * np.log10(e_ref / e_tx)))
        grids[occ] = g

    # ── λ² — EIRP 와 수신 이득이 고정일 때 반송파가 무는 대가 -------------------
    car = {k: grids["G1"][k]["carrier_hz"] for k in STDS}
    lam2 = {f"lte_to_{k}_db": float(20 * np.log10(car["lte"] / car[k]))
            for k in ("nr", "wifi")}

    # ── 기준신호 에너지 격차(상시 G1 → 풀로드 G3) ------------------------------
    e_gap = {k: float(grids["G3"][k]["e_ref_db"] - grids["G1"][k]["e_ref_db"]) for k in STDS}

    # ── 점유 대가 — 같은 표적·같은 기하에서 Pd 0.5 를 넘기는 EIRP 격차 ---------
    rows = fetch((J_MTX, "A_occupancy.rows"))
    eirps = fetch((J_MTX, "A_occupancy.eirps"))
    t1, t3 = _pd50_eirp(rows, "G1"), _pd50_eirp(rows, "G3")
    step = float(min(np.diff(sorted(set(float(e) for e in eirps)))))
    #  이 격차 안에 무엇이 섞여 있나 — 리포트가 "18 dB 는 순수 점유가 아니다"를 말할 수 있게.
    r1 = next(r for r in rows if r["occ"] == "G1")
    r3 = next(r for r in rows if r["occ"] == "G3")

    # ── 모호함수가 검출기 출력과 얼마나 같은가 (6개 중 최악) --------------------
    dv = fetch((J_AMB, "meta.detector_validation"))
    af_err = max(float(r["max_err_db_above_m45"]) for r in dv)

    led = dict(
        _meta=dict(
            purpose="리포트 03 의 파생 원장 — 상위 JSON 에 스칼라로 없는 값만. 손으로 적은 값 0개.",
            made_by="src/make_report03_illuminators.py:build_ledger",
            upstream=[J_WAVE, J_AMB, J_FIX, J_MTX],
            note="모든 항목은 두 양의 비이거나 격자에서 잰 에너지다 — 표적 σ 가 상쇄된다."),
        grids=grids,
        lambda2=dict(
            **lam2,
            defn="20log10(lam/lam_ref) — EIRP 고정 · 수신 안테나 이득 고정 전제. "
                 "코드: src/freespace_link.py:371 (snr_rd_terms_db 의 lambda2 항)",
            span_db=float(min(lam2.values()))),
        ref_energy_gap_G1_to_G3_db=dict(
            **e_gap, defn="10log10(E_ref(G3)/E_ref(G1)) — 상관에 쓸 수 있는 기준신호 에너지만",
            from_="src/waveforms.py 격자 재생성 (all_waveforms)"),
        occupancy_cost=dict(
            value_db=float(t1 - t3), pd_threshold=0.5,
            eirp_G1_dbm=float(t1), eirp_G3_dbm=float(t3), eirp_grid_step_db=step,
            ref_bw_G1_mhz=float(r1["ref_bw_mhz"]), ref_bw_G3_mhz=float(r3["ref_bw_mhz"]),
            occ_frac_G1=float(r1["occupancy_frac"]), occ_frac_G3=float(r3["occupancy_frac"]),
            n_trials=int(r1["N"]), drone=str(r1["drone"]), scen=str(r1["scen"]),
            defn="5G 100 MHz, 상시(G1=SSB) 가 풀로드(G3=NR-PRS) 와 같은 Pd 를 내려면 "
                 "EIRP 를 얼마나 더 써야 하나. 같은 표적·같은 기하의 차라서 σ 가 상쇄된다. "
                 "⚠ 이 격차에는 기준신호 대역(7.2→98.28 MHz)과 점유율이 함께 들어 있다 — "
                 "'점유만'의 값이 아니다.",
            from_=f"{J_MTX}:A_occupancy.rows"),
        detector_af_max_err_db=dict(
            value=af_err, n_cases=len(dv),
            defn="해석 모호함수 |chi| 와 검출기 거리도플러 출력의 최대 편차(−45 dB 이상 셀)",
            from_=f"{J_AMB}:meta.detector_validation"),
    )
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
    print(f"[ledger] {path}")
    return led


# =========================================================================== #
#  2) 그림 — 전부 영어 텍스트(하우스 규약). 캡션은 노트북 쪽에 한 줄.
# =========================================================================== #
def _save(fig, name, sub):
    """그림 저장 + 그림 밑 설명 한 덩어리.

    ⚠ 설명은 **캔버스 바깥(y<0)** 에 둔다. 축 라벨·눈금글자와 겹치지 않게 하는 유일하게
      안전한 방법이다(`bbox_inches="tight"` 가 캔버스 밖 텍스트까지 포함해 잘라 준다).
    """
    import matplotlib.pyplot as plt
    assert_fig_text(sub)
    fig.text(0.0, -0.015, sub, ha="left", va="top",
             fontsize=8.5, color="#555555", linespacing=1.6)
    p = os.path.join(FIG, name)
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(p, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[fig] outputs/figures/{name}")
    return p


def fig_cost_ledger(led):
    """조명원 쪽 dB 원장 — 항목마다 값과 출처 키를 함께 찍는다."""
    import matplotlib.pyplot as plt

    #  ⚠ 라벨 안의 숫자도 손으로 치지 않는다 — 전부 원장/JSON 에서 꺼낸다.
    ghz = {k: led["grids"]["G1"][k]["carrier_hz"] / 1e9 for k in STDS}
    cpi = fetch((J_FIX, "F4_linkbudget.cpi_asymmetry.cpi_ms"))
    cpi_hi, cpi_lo = max(cpi.values()), min(cpi.values())

    items = [
        ("Occupancy: 5G always-on (SSB) vs full load (NR-PRS)",
         -led["occupancy_cost"]["value_db"], "report5_results : A_occupancy", "#6a1b9a"),
        ("Reference energy, same pair (exact grid ledger)",
         -led["ref_energy_gap_G1_to_G3_db"]["nr"], "report03_illuminators : ref_energy_gap", "#c62828"),
        ("WiFi packet duty (fraction of time on air)",
         fetch((J_FIX, "F4_linkbudget.wifi_pilot_fraction.packet_duty_db")),
         "report4_fixups : wifi_pilot_fraction", "#ef6c00"),
        ("WiFi pilot energy / total transmit energy (G3)",
         fetch((J_FIX, "F4_linkbudget.wifi_pilot_fraction.pilot_over_tx_energy_db")),
         "report4_fixups : wifi_pilot_fraction", "#ef6c00"),
        (f"Carrier lambda^2: LTE {ghz['lte']:.2f} -> WiFi {ghz['wifi']:.2f} GHz",
         led["lambda2"]["lte_to_wifi_db"], "report03_illuminators : lambda2", "#1565c0"),
        (f"Carrier lambda^2: LTE {ghz['lte']:.2f} -> 5G {ghz['nr']:.2f} GHz",
         led["lambda2"]["lte_to_nr_db"], "report03_illuminators : lambda2", "#1565c0"),
        (f"CPI convention span (same M frames -> {cpi_lo:.0f} vs {cpi_hi:.0f} ms)",
         -fetch((J_FIX, "F4_linkbudget.cpi_asymmetry.span_db")),
         "report4_fixups : cpi_asymmetry", "#455a64"),
    ]
    assert_fig_text(*[i[0] for i in items], *[i[2] for i in items])

    fig, ax = plt.subplots(figsize=(11.4, 4.6), constrained_layout=True)
    y = np.arange(len(items))[::-1]
    vals = [i[1] for i in items]
    ax.barh(y, vals, height=0.62, color=[i[3] for i in items], alpha=0.9)
    for yy, (lab, v, src, _c) in zip(y, items):
        ax.text(v - 0.5, yy, f"{v:+.2f} dB", va="center", ha="right",
                fontsize=10, fontweight="bold", color="#222")
        ax.text(0.4, yy + 0.16, lab, va="center", ha="left", fontsize=9.5, color="#111")
        ax.text(0.4, yy - 0.22, src, va="center", ha="left", fontsize=7.6, color="#777")
    ax.set_yticks([])
    ax.set_xlim(min(vals) * 1.28, 14.0)
    ax.axvline(0, color="#333", lw=1.0)
    ax.set_xlabel("Penalty [dB]   (more negative = the illuminator choice costs more)")
    ax.set_title("Illuminator cost ledger — every entry is a ratio of two waveform quantities, "
                 "so target RCS cancels", fontsize=12)
    ax.grid(axis="x", alpha=0.3)
    return _save(fig, "report03_cost_ledger.png",
                 "Each bar is exact: it comes from the resource grid, the carrier, or a "
                 "same-target EIRP difference. None of them contains the target RCS.\n"
                 "Occupancy is read off a detection Monte-Carlo (EIRP grid step "
                 f"{led['occupancy_cost']['eirp_grid_step_db']:.0f} dB); every other bar is closed form.")


def _amb_rows():
    """verify_ambiguity.json 의 6개 (표준 x 점유) 항목을 표시 순서대로."""
    W = fetch((J_AMB, "waveforms"))
    keys = ["wifi_G1", "lte_G1", "nr_G1", "wifi_G3", "lte_G3", "nr_G3"]
    return [(k, W[k]) for k in keys]


def fig_af_mainlobe():
    """모호함수 주엽 — 측정 −3 dB 폭 vs 닫힌형(c/B_ref, 1/T_CPI)."""
    import matplotlib.pyplot as plt

    rows = _amb_rows()
    labs = [f"{SHORT[k.split('_')[0]]}\n{r['ref_name']} {k.split('_')[1]}" for k, r in rows]
    cols = [COL[k.split("_")[0]] for k, _ in rows]
    assert_fig_text(*labs)

    fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.3), constrained_layout=True)
    x = np.arange(len(rows))

    meas = [r["dR_meas_m"] for _, r in rows]
    theo = [r["dR_theory_m"] for _, r in rows]
    ax[0].bar(x - 0.2, theo, 0.4, color="#cfd8dc", edgecolor="#90a4ae",
              label=r"closed form  $\Delta R_b = c/B_{ref}$")
    ax[0].bar(x + 0.2, meas, 0.4, color=cols, label="measured  -3 dB width")
    for xi, (m, t) in enumerate(zip(meas, theo)):
        ax[0].text(xi, max(m, t) * 1.03, f"{m / t * 100:.0f}%", ha="center",
                   fontsize=9, color="#333")
    ax[0].set_ylabel(r"Bistatic range mainlobe [m]")
    ax[0].set_title("(a) Range: measured mainlobe vs $c/B_{ref}$", fontsize=11)

    mf = [r["dF_meas_hz"] for _, r in rows]
    tf = [r["dF_theory_hz"] for _, r in rows]
    ax[1].bar(x - 0.2, tf, 0.4, color="#cfd8dc", edgecolor="#90a4ae",
              label=r"closed form  $1/T_{CPI}$")
    ax[1].bar(x + 0.2, mf, 0.4, color=cols, label="measured  -3 dB width")
    for xi, (m, t) in enumerate(zip(mf, tf)):
        ax[1].text(xi, max(m, t) * 1.03, f"{m / t:.2f}x", ha="center", fontsize=9, color="#333")
    ax[1].set_ylabel("Doppler mainlobe [Hz]")
    ax[1].set_title("(b) Doppler: measured mainlobe vs $1/T_{CPI}$", fontsize=11)

    for a in ax:
        a.set_xticks(x)
        a.set_xticklabels(labs, fontsize=8.5)
        a.grid(axis="y", alpha=0.3)
        a.legend(fontsize=8.5)
    return _save(fig, "report03_af_mainlobe.png",
                 "Range: the measured -3 dB mainlobe tracks c/B_ref, which is the bistatic "
                 "convention used everywhere in this project (the monostatic c/2B is half of it).\n"
                 "Doppler: every waveform sits at the same multiple of 1/T_CPI because the "
                 "broadening is set by the slow-time Hann window, not by the waveform.")


def fig_af_sidelobe():
    """부엽·도플러 레플리카 — 기준신호가 표적 에너지를 어디에 남기는가."""
    import matplotlib.pyplot as plt

    rows = _amb_rows()
    labs = [f"{SHORT[k.split('_')[0]]}\n{r['ref_name']} {k.split('_')[1]}" for k, r in rows]
    cols = [COL[k.split("_")[0]] for k, _ in rows]
    assert_fig_text(*labs)

    fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.3), constrained_layout=True)
    x = np.arange(len(rows))

    psl = [r["psl_2d_db"] for _, r in rows]
    isl = [r["isl_2d_db"] for _, r in rows]
    ax[0].bar(x - 0.2, psl, 0.4, color=cols)
    ax[0].bar(x + 0.2, isl, 0.4, color=cols, alpha=0.42)
    ax[0].axhline(0, color="#333", lw=1.0)
    ax[0].set_ylabel("Level relative to mainlobe [dB]")
    ax[0].set_title("(a) How much energy leaves the mainlobe", fontsize=11)
    #  범례는 **밝기**로만 구분한다 — 색은 표준을 뜻하므로 색 견본을 쓰면 오독된다.
    from matplotlib.patches import Patch
    ax[0].legend(handles=[Patch(facecolor="#607d8b", label="peak sidelobe (2D)"),
                          Patch(facecolor="#607d8b", alpha=0.42,
                                label="integrated sidelobe (2D)")],
                 fontsize=8.5, title="bar shade (colour = standard)", title_fontsize=8)

    #  ⚠ WiFi 는 G1 과 G3 의 기준신호가 같은 VHT-LTF 라 점이 정확히 겹친다.
    #     겹친 점을 두 번 찍고 라벨을 포개면 그림이 거짓말을 한다 — 합쳐서 하나로 찍는다.
    pts: dict[tuple, list] = {}
    for (k, r), c_ in zip(rows, cols):
        key = (round(r["ref_time_spread"], 6), round(r["doppler_replica_db"], 4))
        #  색이 표준을 말하므로 라벨은 기준신호 이름 + 점유모드만 — 짧아야 겹치지 않는다.
        pts.setdefault(key, [c_, []])[1].append(f"{r['ref_name']} {k.split('_')[1]}")
    for i, ((s_, r_), (c_, names)) in enumerate(sorted(pts.items())):
        merged = names[0] if len(names) == 1 else \
            names[0].rsplit(" ", 1)[0] + " (" + "=".join(n.rsplit(" ", 1)[1] for n in names) + ")"
        #  점이 x 축에 몰려 있어 라벨을 한 방향으로만 빼면 옆 점 위에 얹힌다 — 사분면을 번갈아 쓴다.
        left = bool(i % 2)
        ax[1].scatter(s_, r_, s=150, color=c_, edgecolor="#333", zorder=3)
        ax[1].annotate(merged, (s_, r_), textcoords="offset points",
                       xytext=(-12 if left else 12, -15 if left else 8),
                       ha="right" if left else "left", fontsize=9, color="#333")
    ax[1].axvline(1 / np.sqrt(12), color="#455a64", ls="--", lw=1.2)
    ax[1].text(0.985, 0.97, "dashed: uniform spread over the frame (max possible)",
               transform=ax[1].transAxes, ha="right", va="top",
               fontsize=8.5, color="#455a64")
    ax[1].set_xscale("log")
    ax[1].set_xlim(6e-4, 0.75)
    ax[1].set_ylim(-27, 7)
    ax[1].set_xlabel("RMS spread of the reference energy over the frame  "
                     "[fraction of frame, log]")
    ax[1].set_ylabel(r"Doppler replica at $\pm$PRF [dB]")
    ax[1].set_title("(b) Why some references alias at full strength", fontsize=11)
    ax[1].grid(alpha=0.3, which="both")

    ax[0].set_xticks(x)
    ax[0].set_xticklabels(labs, fontsize=8.5)
    ax[0].grid(axis="y", alpha=0.3)
    return _save(fig, "report03_af_sidelobe.png",
                 "(a) A high sidelobe means a strong target masks a weak one elsewhere in the map.\n"
                 "(b) A reference whose energy is bunched at the front of the frame (WiFi LTF, 5G SSB) "
                 "keeps a full-strength replica at +-PRF, so anything past the unambiguous velocity "
                 "folds back in at almost no loss. LTE CRS is spread over the frame, so its replica "
                 "cancels.")


# =========================================================================== #
#  3) 노트북 조립
# =========================================================================== #
def build_blocks(led):
    W1 = lambda k, f=None, u="": num(None, (J_WAVE, f"reference.G1.{k}"), f, u)   # noqa: E731
    A = lambda k, f=None, u="": num(None, (J_AMB, f"waveforms.{k}"), f, u)        # noqa: E731
    L = lambda k, f=None, u="": num(None, (J_LED, k), f, u)                       # noqa: E731
    X = lambda k, f=None, u="": num(None, (J_WAVE, f"crosscheck.{k}"), f, u)      # noqa: E731

    #  §2.1 표는 straddle 행 순서가 (wifi, lte, nr) 라고 가정한다 — 그 가정을 여기서 깬다.
    #  B/f_s 는 격자에서 다시 계산할 수 있으므로, 행이 뒤섞이면 여기서 빌드가 멈춘다.
    for i, k in enumerate(STDS):
        got = fetch((J_FIX, f"F4_linkbudget.straddle.rows[{i}].b_over_fs"))
        want = led["grids"]["G1"][k]["bw_hz"] / (fetch((J_WAVE, f"crosscheck.{k}.fs_mhz")) * 1e6)
        if abs(got - want) > 1e-6 * max(1.0, abs(want)):            # pragma: no cover
            raise RuntimeError(
                f"straddle 행 {i} 가 {k} 가 아니다 — B/fs {got:.6f} vs 격자 {want:.6f}. "
                f"{J_FIX} 의 행 순서를 확인하라.")

    blocks = []

    # ── 6블록 서두 ────────────────────────────────────────────────────────── #
    blocks.append(header(
        num=3,
        title="조명원 — 세 파형과 그 대가",
        question="패시브 레이더가 빌려 쓸 수 있는 상시 신호는 무엇이고, "
                 "그 선택은 몇 dB 의 대가를 치르는가?",
        conclusion_lines=[
            f"패시브가 상관에 쓸 수 있는 것은 셀이 **늘 켜 두는 기준신호**뿐이다 — "
            f"LTE=CRS({W1('lte.ref_bw_mhz', '{:.1f}', 'MHz')}), "
            f"5G=SSB({W1('nr.ref_bw_mhz', '{:.1f}', 'MHz')}), "
            f"WiFi=VHT-LTF({W1('wifi.ref_bw_mhz', '{:.1f}', 'MHz')}).",
            f"**5G 는 이중고**다 — 기준신호가 좁아 ΔR_b = {W1('nr.dR_m', '{:.1f}', 'm')} "
            f"(LTE {W1('lte.dR_m', '{:.1f}', 'm')}), 드물어서 PRF "
            f"{W1('nr.prf_hz', '{:.0f}', 'Hz')} → 무모호 속도 "
            f"{W1('nr.vmax_ms', '{:.2f}', 'm/s')} (LTE {W1('lte.vmax_ms', '{:.1f}', 'm/s')}).",
            "⭐ 이 편의 수치는 **표적 σ 와 무관**하다 — 파형·반송파·기하만으로 정해지므로 "
            "02편의 RCS 감사가 무엇을 바꾸든 움직이지 않는다(§0).",
            f"조명원 선택의 대가는 dB 로 닫힌다 — 점유 "
            f"{L('occupancy_cost.value_db', '{:.1f}', 'dB')}, "
            f"반송파 λ² {L('lambda2.span_db', '{:.2f}', 'dB')}(밴드 양끝), "
            f"WiFi 패킷 듀티 "
            f"{num(None, (J_FIX, 'F4_linkbudget.wifi_pilot_fraction.packet_duty_db'), '{:.2f}', 'dB')}.",
            f"파형은 Sionna PHY 독립 변조기와 상관 {X('nr.corr', '{:.4f}')} 로 일치하고, "
            f"우리가 그리는 모호함수는 검출기 출력과 최대 "
            f"{L('detector_af_max_err_db.value', '{:.3f}', 'dB')} 안에서 같다.",
        ],
        claims=[
            "세 조명원의 **B_ref · ΔR_b · PRF · 듀티 · 모호함수** — 자원격자에서 잰 정확한 양",
            "**상시 신호만 쓰는 체제에서 LTE CRS > 5G SSB** — 거리·속도 두 축 모두",
            "OFDM **변조 단계**가 Sionna PHY 와 일치한다 — 상관·NMSE 로 정량화(§3)",
            "§4 의 모호함수는 **검출기가 실제로 내는 응답**이다 — 편차 상한을 명시(§4)",
        ],
        non_claims=[
            "기준신호 **배치 좌표**(CRS·SSB·VHT-LTF)의 독립 검증 — Sionna 에 생성기가 없다(§3)",
            "**full-waveform capture** 체제 — 이 편은 상시 신호만 쓰는 기본선이다(§1)",
            "검출확률·CFAR·Pfa — 04편 소관. 이 편은 σ 를 곱하기 **전** 단계다",
            "표적 밝기 σ 와 그 밴드 의존성 — 02편 소관",
            "WiFi 의 상시성 — PRF 는 혼잡 AP 대표값이지 보장된 값이 아니다(마지막 절)",
        ],
        prereq=None,
        repro=dict(
            cmd=["cd /home/yunjung/workspace/sionna2",
                 "# ① 파형 제원 · 자원격자 · Sionna 교차대조 (그림 4장 포함)",
                 "~/.venvs/py312/bin/python src/viz_report2.py",
                 "# ② 모호함수 — 검출기와 같은 커널",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ambiguity.py",
                 "# ③ 링크버짓 규약 상수(듀티 · CPI · CFAR)",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/report4_fixups.py",
                 "# ④ 이 편의 파생 원장 + 그림 3장 + 노트북",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report03_illuminators.py"],
            out=[J_WAVE, J_AMB, J_FIX, J_MTX, J_LED],
            runtime=f"① {num(None, (J_WAVE, 'meta.runtime_s'), '{:.0f}', 's')} "
                    f"(대부분은 같은 스크립트의 RCS 스윕이고 파형 부분은 초 단위) · "
                    f"③ {num(None, (J_FIX, '_meta.runtime_s'), '{:.0f}', 's')} · "
                    f"② GPU 1장 수 분 · ④ 초 단위",
            note=f"{J_MTX} 는 검출 몬테카를로가 이미 남긴 것이다 — 이 편은 그중 "
                 f"`A_occupancy` 만 인용한다(재실행 불필요).",
        ),
    ))

    # ── §0 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §0. 이 편의 수치는 무엇에 의존하는가",
        "",
        "조명원 쪽 양들은 **파형·반송파·관측시간**만으로 정해진다. 표적의 σ 를 곱하기 **전** 단계라서, "
        "σ 를 둘러싼 논쟁이 어떻게 끝나든 아래 값은 바뀌지 않는다. 인수인계 시 **가장 먼저 믿어도 되는 층**이다.",
        "",
        table(["양", "무엇이 정하나", "σ 에 의존?", "이 편의 절"],
              [["기준신호 대역 $B_{ref}$ → $\\Delta R_b$", "자원격자", "없음", "§1"],
               ["PRF → 무모호 속도", "기준신호 반복주기", "없음", "§1"],
               ["점유 · 듀티 · λ² · √(B/f_s)", "파형 · 반송파 · 표본율", "없음", "§2"],
               ["모호함수(주엽·부엽·레플리카)", "기준신호 파형 + 창", "없음", "§4"],
               ["검출확률 $P_d$ · CFAR 문턱", "위 전부 **× σ × 기하**", "**있음**", "04 · 05편"]]),
    ))

    # ── §1 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §1. 세 조명원 — 무엇이 늘 켜져 있는가",
        "",
        "패시브 수신기는 두 조건을 **동시에** 만족하는 신호에만 상관을 걸 수 있다. "
        "**① 내용을 미리 안다** — 데이터는 매 순간 바뀌므로 못 쓴다. "
        "**② 아무 셀이나 늘 켠다** — 조건부로 켜지는 신호는 하필 그때 없으면 표적을 놓친다.",
        "",
        "두 조건을 다 만족하는 신호는 표준마다 **하나씩**이다. 격자에서 잰 제원은 다음과 같다.",
        "",
        table(["표준", "상시 기준신호", "반송파", "채널 점유대역", "$B_{ref}$", "$\\Delta R_b=c/B_{ref}$"],
              [["WiFi 802.11ac", "VHT-LTF", W1("wifi.carrier_ghz", "{:.2f}", "GHz"),
                W1("wifi.chan_bw_mhz", "{:.1f}", "MHz"), W1("wifi.ref_bw_mhz", "{:.1f}", "MHz"),
                W1("wifi.dR_m", "{:.1f}", "m")],
               ["LTE Rel-9", "CRS", W1("lte.carrier_ghz", "{:.3f}", "GHz"),
                W1("lte.chan_bw_mhz", "{:.1f}", "MHz"), W1("lte.ref_bw_mhz", "{:.1f}", "MHz"),
                W1("lte.dR_m", "{:.1f}", "m")],
               ["5G NR Rel-16", "SSB", W1("nr.carrier_ghz", "{:.2f}", "GHz"),
                W1("nr.chan_bw_mhz", "{:.1f}", "MHz"), W1("nr.ref_bw_mhz", "{:.1f}", "MHz"),
                W1("nr.dR_m", "{:.1f}", "m")]]),
        "",
        "$B_{ref}$ 는 기준신호가 차지한 부반송파의 **양끝 span** 이다(`src/waveforms.py:237`) — "
        "안쪽 널 톤을 포함하므로 WiFi 처럼 span 이 점유대역보다 넓을 수 있다. "
        "격자는 `src/waveforms.py:258`(WiFi) · `:313`(LTE) · `:370`(5G), "
        "$\\Delta R_b$ 는 `src/waveforms.py:144`.",
    ))

    blocks.append(md(
        "![resource grid](outputs/figures/report2_resource_grid.png)", "",
        caption(1, "유휴 셀이 실제로 켜는 칸은 어디이고, 그중 패시브가 상관에 쓸 수 있는 것은 무엇인가?"),
    ))

    blocks.append(md(
        "### §1.1 5G 의 이중고 — 좁고, 드물다",
        "",
        "**PRS 는 상시 신호가 아니다.** 넓은 대역을 켜지만 **측위 세션이 설정돼야** 켜지는 옵션이고, "
        "남의 셀을 빌리는 패시브 수신기는 그것이 켜져 있다고 가정할 수 없다. "
        "따라서 5G 의 기본선은 SSB 이고, PRS 를 켠 수치는 **낙관적 상한**으로만 읽는다.",
        "",
        table(["축", "정하는 것", "LTE CRS", "5G SSB", "격차"],
              [["거리 $\\Delta R_b$", "$B_{ref}$", W1("lte.dR_m", "{:.1f}", "m"),
                W1("nr.dR_m", "{:.1f}", "m"),
                f"{fetch((J_WAVE, 'reference.G1.nr.dR_m')) / fetch((J_WAVE, 'reference.G1.lte.dR_m')):.1f}배 거칢"],
               ["속도 $v_{max}$ (모노 등가)", "PRF", W1("lte.vmax_ms", "{:.1f}", "m/s"),
                W1("nr.vmax_ms", "{:.2f}", "m/s"),
                f"{fetch((J_WAVE, 'reference.G1.lte.vmax_ms')) / fetch((J_WAVE, 'reference.G1.nr.vmax_ms')):.0f}배 빠름"]]),
        "",
        f"SSB 는 PRF {W1('nr.prf_hz', '{:.0f}', 'Hz')} — **걷는 속도의 드론도 도플러가 접힌다**(§4.3). "
        "통신 세대가 최신이라고 조명원으로 좋은 것은 아니다.",
        "",
        "> ⚠ 반대로 **WiFi 가 이기는 것도 조건부**다. 위 PRF 는 혼잡 AP 값이고, 비콘만 내보내는 "
        "유휴 AP 면 속도축에서 5G 보다 나쁘다(그림 2 의 Caveat 2, §5).",
    ))

    blocks.append(md(
        "![reference signal budget](outputs/figures/report2_ref_signal.png)", "",
        caption(2, "기준신호의 넓이와 반복이 거리·속도 눈금을 각각 얼마로 정하는가?"),
    ))

    # ── §2 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §2. 대가 원장 — 전부 정확한 양",
        "",
        "조명원 선택이 만드는 dB 격차를 한 표에 모은다. 모든 항목이 **두 양의 비**라서 표적 σ 가 상쇄된다.",
        "",
        table(["항목", "값", "무엇의 비인가"],
              [["점유 대가 (5G · 상시 vs 풀로드)", L("occupancy_cost.value_db", "{:.1f}", "dB"),
                f"같은 표적·같은 기하에서 $P_d$ "
                f"{L('occupancy_cost.pd_threshold', '{:.1f}')} 를 넘기는 EIRP 차"],
               ["기준신호 에너지 격차 (같은 쌍)", L("ref_energy_gap_G1_to_G3_db.nr", "{:.2f}", "dB"),
                "$E_{ref}$(G3) / $E_{ref}$(G1) — 상관에 쓸 수 있는 에너지만"],
               ["반송파 λ² (LTE→WiFi)", L("lambda2.lte_to_wifi_db", "{:.2f}", "dB"),
                "$20\\log_{10}(\\lambda/\\lambda_{ref})$ — EIRP·수신이득 고정"],
               ["반송파 λ² (LTE→5G)", L("lambda2.lte_to_nr_db", "{:.2f}", "dB"), "위와 같음"],
               ["WiFi 파일럿 / 총 송신 에너지",
                num(None, (J_FIX, "F4_linkbudget.wifi_pilot_fraction.pilot_over_tx_energy_db"),
                    "{:.2f}", "dB"), "G3 격자에서 상관에 쓸 수 있는 몫"],
               ["WiFi 패킷 듀티",
                num(None, (J_FIX, "F4_linkbudget.wifi_pilot_fraction.packet_duty_db"),
                    "{:.2f}", "dB"), "패킷이 공중에 있는 시간 비율"],
               ["CPI 규약 격차",
                num(None, (J_FIX, "F4_linkbudget.cpi_asymmetry.span_db"), "{:.2f}", "dB"),
                "같은 프레임 수 M 이 5G 에 주는 관측시간이 절반"]]),
    ))

    blocks.append(md(
        "> ⚠ **부호는 원본 JSON 그대로다.** 손해가 양수로 적히는 항목(점유·기준신호 에너지·CPI)과 "
        "음수로 적히는 항목(λ²·WiFi 두 항목)이 섞여 있다 — 그림 4 는 전부 "
        "'음수 = 손해'로 부호를 맞춰 다시 그린 것이다.",
        "",
        f"> ⚠ **점유 대가는 '점유만'의 값이 아니다.** G1→G3 은 기준신호 대역도 "
        f"{L('occupancy_cost.ref_bw_G1_mhz', '{:.1f}', 'MHz')} → "
        f"{L('occupancy_cost.ref_bw_G3_mhz', '{:.1f}', 'MHz')} 로 함께 넓어진다. "
        f"두 효과를 분리하려면 대역을 고정한 채 점유만 바꾼 스윕이 따로 필요하다.",
        "",
        "> ⚠ 앞의 두 WiFi 항목은 **서로 다른 양**이다. 하나는 에너지 비, 하나는 시간 비다 — "
        "곱해서 한 숫자로 만들면 안 된다.",
        "",
        "> ⚠ **λ² 는 전제가 붙는다.** EIRP 가 고정이고 수신 안테나 **이득**이 고정일 때만 성립한다"
        "(`src/freespace_link.py:371`). 수신 **개구면적**을 고정하면 부호가 뒤집힌다.",
        "",
        "> ⚠ **CPI 규약 격차는 통제해야 할 변수다.** 파형 비교에서 관측시간이 다르면 그 차이가 "
        "파형의 우열로 오독된다 — 04·05편은 관측시간을 맞춘 뒤에 비교한다.",
    ))

    blocks.append(md(
        "![occupancy](outputs/figures/report2_occupancy.png)", "",
        caption(3, "셀이 데이터로 바빠지면 패시브의 거리분해능도 같이 좋아지는가?"),
    ))

    blocks.append(md(
        "![cost ledger](outputs/figures/report03_cost_ledger.png)", "",
        caption(4, "조명원 선택이 무는 대가는 항목별로 몇 dB 인가?"),
    ))

    blocks.append(md(
        "### §2.1 규약 — 여기서 틀리면 2배가 틀린다",
        "",
        f"이 프로젝트의 거리축은 **바이스태틱 거리합** $R_b=R_1+R_2-L$ 이므로 분해능은 "
        f"$\\Delta R_b=c/B_{{ref}}$ 다. 모노스태틱 교과서 값 $c/2B$ 는 그 절반이다 — 비 "
        f"{num(None, (J_FIX, 'F3_ambiguity.resolution_convention_conflict.rows[0].factor'), '{:.0f}')}"
        f"배. 섞어 쓰면 분해능을 그만큼 낙관하게 된다.",
        "",
        "잡음대역 정규화 √(B/f_s) 도 같은 성격의 규약이다 — 선언한 대역 B 와 표본율 f_s 가 다르면 "
        "주입 진폭을 그만큼 낮춰야 매치드필터 출력 SNR 이 파형 간 공정해진다"
        "(`benchmark/run_min_cell.py:131`).",
        "",
        table(["파형", "$B/f_s$", "$\\Delta R_b=c/B_{ref}$", "모노 등가 $c/2B$"],
              [[fetch((J_FIX, f"F4_linkbudget.straddle.rows[{i}].name")),
                num(None, (J_FIX, f"F4_linkbudget.straddle.rows[{i}].b_over_fs"), "{:.4f}"),
                num(None, (J_AMB, f"waveforms.{k}_G1.dR_theory_m"), "{:.2f}", "m"),
                num(None, (J_AMB, f"waveforms.{k}_G1.dR_mono_theory_m"), "{:.2f}", "m")]
               for i, k in enumerate(STDS)]),
    ))

    blocks.append(code(
        "# §2 원장을 JSON 에서 그대로 읽어 찍는다 — 본문 숫자에 하드코딩이 없음을 확인하는 셀.",
        "import json",
        "L = json.load(open('outputs/report03_illuminators.json'))",
        "print('점유 대가      ', f\"{L['occupancy_cost']['value_db']:+.1f} dB\",",
        "      f\"(G1 {L['occupancy_cost']['eirp_G1_dbm']:+.0f} dBm vs \"",
        "      f\"G3 {L['occupancy_cost']['eirp_G3_dbm']:+.0f} dBm, \"",
        "      f\"격자 {L['occupancy_cost']['eirp_grid_step_db']:.0f} dB)\")",
        "for k in ('wifi', 'lte', 'nr'):",
        "    g1, g3 = L['grids']['G1'][k], L['grids']['G3'][k]",
        "    print(f\"{k:5s} G1 ref={g1['ref_name']:8s} B_ref={g1['ref_bw_hz']/1e6:6.2f} MHz \"",
        "          f\"dRb={g1['drb_m']:6.2f} m  E_ref/E_tx={g1['e_ref_over_tx_db']:+6.2f} dB\"",
        "          f\"   | G1->G3 기준신호 에너지 \"",
        "          f\"{L['ref_energy_gap_G1_to_G3_db'][k]:+5.2f} dB\")",
    ))

    # ── §3 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §3. 파형이 규격대로인가 — Sionna PHY 로 채점",
        "",
        "Sionna PHY 는 5G NR 뉴머롤로지(`nr.CarrierConfig`, `TS 38.211` 구현)와 OFDM 변조기는 주지만, "
        "**WiFi·LTE 파형도 상시 기준신호(CRS·SSB·VHT-LTF)의 격자 배치도 주지 않는다.** "
        "그래서 격자는 규격서를 읽어 `src/waveforms.py` 의 표준별 생성기(§1 의 줄번호)에 세우고, "
        "**격자를 신호로 바꾸는 단계**만 "
        "독립 변조기 `sionna.phy.ofdm.OFDMModulator` 로 채점한다(`src/viz_report2.py:387`).",
        "",
        table(["이 대조가 **확인해 주는 것**", "이 대조가 **못 하는 것**"],
              [["IFFT 규약 — fftshift 방향·정규화", "가드밴드·DC 널 배치 (격자는 우리가 건넨 입력)"],
               ["CP 복사와 심볼별 이어붙이기 순서", "CP 길이 **값**이 3GPP 표와 맞는가"],
               ["두 독립 구현이 같은 시간파형을 내는가", "파일럿 **좌표** (Sionna 에 생성기가 없다)"]]),
    ))

    blocks.append(md(
        "![crosscheck](outputs/figures/report2_crosscheck.png)", "",
        caption(5, "같은 자원격자를 두 변조기에 넣으면 같은 시간파형이 나오는가?"),
    ))

    blocks.append(md(
        f"세 파형 모두 상관이 소수 넷째 자리까지 1 이고, 남은 차이는 float32 반올림 바닥이다. "
        f"오른쪽 열은 **대조의 분해력 시험**이다 — 재변조 쪽에 심볼별 CP 배열 대신 첫 CP 스칼라만 "
        f"넘기면 두 번째 심볼부터 시간축이 어긋나 상관이 무너진다. CP 가 심볼마다 같은 WiFi 는 그대로다.",
        "",
        table(["표준", "표본 수", "$f_s$", "상관", "NMSE", "CP 앞머리", "CP 배열을 안 넘기면"],
              [["WiFi 802.11ac", X("wifi.n", "{:.0f}"), X("wifi.fs_mhz", "{:.2f}", "MHz"),
                X("wifi.corr", "{:.4f}"), X("wifi.nmse_db", "{:.1f}", "dB"),
                f"`{fetch((J_WAVE, 'crosscheck.wifi.cp_head'))}`", X("wifi.corr_bug", "{:.4f}")],
               ["LTE Rel-9", X("lte.n", "{:.0f}"), X("lte.fs_mhz", "{:.2f}", "MHz"),
                X("lte.corr", "{:.4f}"), X("lte.nmse_db", "{:.1f}", "dB"),
                f"`{fetch((J_WAVE, 'crosscheck.lte.cp_head'))}`", X("lte.corr_bug", "{:.4f}")],
               ["5G NR Rel-16", X("nr.n", "{:.0f}"), X("nr.fs_mhz", "{:.2f}", "MHz"),
                X("nr.corr", "{:.4f}"), X("nr.nmse_db", "{:.1f}", "dB"),
                f"`{fetch((J_WAVE, 'crosscheck.nr.cp_head'))}`", X("nr.corr_bug", "{:.4f}")]]),
        "",
        "대조는 **G3(풀로드) 격자 하나**에서 돈다 — '세 파형 모두'는 그 조건 아래의 진술이다.",
    ))

    # ── §4 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §4. 모호함수 — 검출기가 실제로 보는 눈",
        "",
        f"모호함수 $\\chi(\\tau,f_d)$ 는 기준신호 하나가 거리-도플러 평면에 만드는 응답이다. "
        f"우리가 그리는 것은 별도 계산이 아니라 **검출기가 쓰는 것과 같은 커널**이고, "
        f"검출기의 거리도플러 출력과 최대 {L('detector_af_max_err_db.value', '{:.3f}', 'dB')} "
        f"({L('detector_af_max_err_db.n_cases', '{:.0f}')}개 경우, −45 dB 이상 셀) 안에서 같다. "
        f"코드: `benchmark/verify_ambiguity.py:150`, 검출기는 `src/passive_process.py:133`.",
        "",
        "### §4.1 주엽 — 닫힌형이 맞는가",
        "",
        f"거리 주엽은 $c/B_{{ref}}$ 예측의 "
        f"{A('wifi_G1.dR_ratio', '{:.0%}')} ~ {A('nr_G1.dR_ratio', '{:.0%}')} 이고, "
        f"도플러 주엽은 여섯 경우 모두 $1/T_{{CPI}}$ 의 "
        f"{A('wifi_G1.dF_ratio', '{:.2f}')}배 근처다 — 이 배수는 파형이 아니라 "
        f"**slow-time Hann 창**이 정한다(`src/passive_process.py:142`).",
    ))

    blocks.append(md(
        "![ambiguity mainlobe](outputs/figures/report03_af_mainlobe.png)", "",
        caption(6, "측정한 모호함수 주엽이 닫힌형 예측과 몇 % 안에서 맞는가?"),
    ))

    blocks.append(md(
        "### §4.2 부엽과 도플러 레플리카 — 검출에 무엇을 뜻하나",
        "",
        "주엽 밖으로 새는 에너지는 두 가지로 나타난다. **부엽**은 강한 표적이 평면 다른 곳의 약한 "
        "표적을 덮는 정도이고, **±PRF 의 레플리카**는 무모호 속도를 넘은 표적이 되접혀 들어오는 세기다.",
        "",
        "⚠ 이 표의 PRF 는 **검출기 프레임률**이다. 물리 SSB 주기 기준의 접힘은 §4.3 이 따로 다룬다(§5).",
        "",
        table(["기준신호", "2D 부엽 최대", "±PRF 레플리카", "프레임 내 시간점유", "함의"],
              [["WiFi VHT-LTF", A("wifi_G1.psl_2d_db", "{:.1f}", "dB"),
                A("wifi_G1.doppler_replica_db", "{:.2f}", "dB"),
                A("wifi_G1.ref_time_duty", "{:.1%}"), "레플리카가 **무손실** — 접힘이 그대로 산다"],
               ["LTE CRS", A("lte_G1.psl_2d_db", "{:.1f}", "dB"),
                A("lte_G1.doppler_replica_db", "{:.2f}", "dB"),
                A("lte_G1.ref_time_duty", "{:.1%}"), "레플리카는 죽지만 부엽이 가장 높다"],
               ["5G SSB", A("nr_G1.psl_2d_db", "{:.1f}", "dB"),
                A("nr_G1.doppler_replica_db", "{:.2f}", "dB"),
                A("nr_G1.ref_time_duty", "{:.1%}"), "부엽은 낮으나 레플리카가 거의 무손실"]]),
        "",
        "레플리카를 정하는 것은 점유율이 아니라 **에너지가 프레임 안에 얼마나 퍼져 있는가**다 — "
        "CRS 처럼 프레임 전체에 흩어지면 위상이 상쇄되고, LTF·SSB 처럼 앞쪽에 뭉치면 상쇄가 없다.",
    ))

    blocks.append(md(
        "![ambiguity sidelobe](outputs/figures/report03_af_sidelobe.png)", "",
        caption(7, "각 기준신호는 표적 에너지를 부엽과 도플러 레플리카에 얼마나 남기는가?"),
    ))

    blocks.append(md(
        "### §4.3 접힘 — 5G SSB 는 걷는 드론도 놓친다",
        "",
        f"SSB 의 물리 반복률은 {A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')} 다. "
        f"무모호 도플러가 ±{A('nr_G1.physical.fd_unamb_phys_hz', '{:.0f}', 'Hz')} 뿐이라, 이 프로젝트의 "
        f"기준 표적 속도에서 참 도플러 {A('nr_G1.physical.fd_true_hz', '{:.1f}', 'Hz')} 가 "
        f"{A('nr_G1.physical.fd_aliased_phys_hz', '{:.1f}', 'Hz')} 로 접힌다"
        f"(`aliased` = {A('nr_G1.physical.aliased')}). 같은 조건에서 WiFi·LTE 는 접히지 않는다.",
        "",
        table(["기준신호", "물리 PRF", "무모호 속도", "접히는가"],
              [["WiFi VHT-LTF", A("wifi_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                A("wifi_G1.physical.v_unamb_phys_ms", "{:.1f}", "m/s"),
                A("wifi_G1.physical.aliased")],
               ["LTE CRS", A("lte_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                A("lte_G1.physical.v_unamb_phys_ms", "{:.1f}", "m/s"),
                A("lte_G1.physical.aliased")],
               ["5G SSB", A("nr_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                A("nr_G1.physical.v_unamb_phys_ms", "{:.2f}", "m/s"),
                A("nr_G1.physical.aliased")]]),
        "",
        "이것이 §1 이 말한 이중고의 두 번째 절반이다 — 5G 는 **좁아서** 거리를 못 가르고, "
        "**드물어서** 속도를 못 가른다.",
    ))

    # ── 마지막 절 ─────────────────────────────────────────────────────────── #
    blocks.append(limits([
        ("기준신호 **격자 좌표**(CRS·SSB·VHT-LTF)의 독립 검증이 없다 — Sionna 에 생성기가 없어 "
         "§3 대조는 변조 단계까지만 닿는다",
         "X410 으로 실제 셀을 캡처해 `src/waveforms.py` 의 격자와 대조 → 06편 측정 설계에 항목 추가"),
        ("**§4 의 모호함수는 검출기 프레임률로 계산된다** — 5G 는 프레임률 "
         f"{A('nr_G1.physical.prf_model_hz', '{:.0f}', 'Hz')}, 물리 SSB 반복은 "
         f"{A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')} 로 "
         f"{A('nr_G1.physical.ratio', '{:.0f}')}배 차이다. §4.3 의 접힘 표만 물리 PRF 로 따로 냈다",
         "`benchmark/run_min_cell.py:74` 의 `frame_len()` 을 물리 SSB 주기로 확장해 "
         "`benchmark/verify_ambiguity.py:108` 이 같은 프레임을 쓰게 하고 §4 표 전체를 재계산"),
        (f"점유 대가는 EIRP 격자 {L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')} 간격에서 "
         f"읽은 값이고, 표적 {L('occupancy_cost.drone')} · 시나리오 "
         f"{L('occupancy_cost.scen')} · 시행 {L('occupancy_cost.n_trials', '{:.0f}')}회 "
         f"한 점에서만 쟀다",
         "`benchmark/run_matrix.py:300` 의 `eirps` 를 2 dB 간격으로 좁히고 §2 의 대역 고정 스윕을 "
         "추가해 '점유만'의 값을 분리"),
        ("**WiFi 의 상시성이 가장 약하다** — PRF 는 혼잡 AP 대표값이고, 비콘만 나오는 유휴 AP 는 "
         "훨씬 드물다. 문헌이 트래픽을 일부러 유발하는 이유다",
         "`src/waveforms.py:112` 의 `PILOT_RATE_HZ` 를 트래픽 시나리오 파라미터로 올리고 "
         "§1 표를 시나리오별로"),
        ("이 편은 **상시 신호만** 쓰는 체제의 기본선이다 — 부하가 걸린 셀에서 파형 전체를 캡처하는 "
         "체제는 재지 않았다",
         "05편 검출 비교에 'full-waveform capture' 축을 하나 더 세우고 두 체제를 섞어 인용하지 않기"),
        ("**λ² 항은 수신 안테나 이득 고정 전제**에 묶여 있다 — 개구면적 고정이면 부호가 뒤집힌다",
         "06편 측정 설계에서 실제 수신 안테나를 확정한 뒤 `src/freespace_link.py:371` 전제를 재확인"),
    ], sec="§5."))

    return blocks


# =========================================================================== #
def main():
    led = build_ledger()
    fig_cost_ledger(led)
    fig_af_mainlobe()
    fig_af_sidelobe()
    rep = build_notebook(NB, build_blocks(led), strict=True)
    print(f"wrote {os.path.relpath(NB, ROOT)}  "
          f"(md {rep['md_cells']} · code {rep['code_cells']} · fig {rep['figures']})")
    return rep


if __name__ == "__main__":
    main()
