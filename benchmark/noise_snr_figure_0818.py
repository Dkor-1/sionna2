# -*- coding: utf-8 -*-
"""
noise_snr_figure_0818.py — 3 장(잡음)용 «SNR 이 드러나는» 그림
================================================================================

사용자 지시: «잡음 모델링하고 나면 SNR 도 드러나게끔 그림 그려줘».

세 칸으로 답한다
----------------
  ⓐ **무늬가 녹는 과정** — 같은 STFT 를 SNR 을 낮춰 가며 나란히. 정성.
  ⓑ **잣대 vs SNR** — 빗살 대비 곡선에 **귀무분포 p99.9 판정 막대**를 겹친다.
     곡선이 막대를 뚫고 내려오는 자리가 «읽기 한계 SNR». 판정.
  ⓒ **SNR vs 거리** — 원장의 거리 칸에서 잰 AC SNR. ⓑ 의 한계 SNR 을 여기 얹으면
     «몇 미터» 가 나온다. 분모.

⭐잣대·귀무·SNR 곡선은 **다시 구현하지 않는다** — `outputs/noise_distance_frame.json`
  (귀무 4,000 시행 · 팔마다 96 점 SNR 곡선 · 거리 칸)을 그대로 읽는다. 정본은 구현이 하나다.

⭐**두 층 표기 규약**(docs/LINK_BUDGET §10): 그림에 시나리오 이름과 EIRP 를 박고,
  «검증된 것(팔 사이 상대 비교)» 과 «검증 안 된 것(절대 미터)» 을 함께 적는다.

⛔GPU 없음. 산출: outputs/noise_snr_figure_0818.json ·
   outputs/figures/noise_snr_panels.png (+ --with-maps 면 noise_snr_maps.png)

실행:  PYTHONPATH=src:benchmark python benchmark/noise_snr_figure_0818.py [--with-maps]
       (⚠--with-maps 는 STFT 를 다섯 장 그려 CPU 를 크게 쓴다 — GPU 큐가 도는 동안은 뺀다)
"""
from __future__ import annotations

import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIG = os.path.join(ROOT, "outputs", "figures")
OUT = os.path.join(ROOT, "outputs", "noise_snr_figure_0818.json")
FRAME = json.load(open(os.path.join(ROOT, "outputs", "noise_distance_frame.json"),
                       encoding="utf-8"))
CANON = json.load(open(os.path.join(ROOT, "outputs", "link_budget_canon_0816.json"),
                       encoding="utf-8"))

EL = -30.0                       # 헤드라인 앙각
SCN = CANON["_meta"]["headline_scenario"]
SC = CANON["scenarios"][SCN]

ARMS = [("ours", "Our kernel (SBR+PO)", "#c62828"),
        ("ps_off", "PathSolver, all off", "#1565c0"),
        ("ps_refr", "PathSolver, refraction only", "#2e7d32"),
        ("ps_phys", "PathSolver, all on", "#6a1b9a")]


def cells_for(arm, el=EL):
    return sorted([c for c in FRAME["cells"] if c["arm"] == arm and c["el_deg"] == el],
                  key=lambda c: c["range_m"])


def null_bar_db(el=EL):
    """⭐판정 막대 — 빗살 대비의 **귀무분포**(잡음만) p99.9.

    사용자 규칙: «막대는 판정하는 그 양의 귀무분포에서 세운다»(docs/MAP_SCALING §2-b).
    원장은 평균·표준편차·p05·p95 를 4,000 시행으로 준다. p99.9 는 정규 근사
    (mean + 3.090·std) 로 세우고, 원장의 p95 로 근사가 맞는지 검산한다.
    """
    n = FRAME["null_control"][f"{el:+.0f}".replace("+0", "+0")] \
        if f"{el:+.0f}" in FRAME["null_control"] else FRAME["null_control"][str(int(el))]
    cc = n["comb_contrast_db"]
    bar = cc["mean"] + 3.090 * cc["std"]
    n_trial = n["n_trial"]
    # ⭐정본은 게이트가 20,000 시행으로 **경험적** p99.9 를 낸 값이다(2026-08-18).
    #   있으면 그것을 쓰고, 위 정규 근사는 검산용으로만 남긴다.
    try:
        G = json.load(open(os.path.join(ROOT, "outputs",
                                        "noise_main_gates_n20000_0818.json"), encoding="utf-8"))
        b = G["G3_bars"][f"el_minus{abs(int(el))}"]
        bar_canon, n_trial = float(b["bar_noise_db"]), int(b["n_null"])
        approx_err = round(abs(bar - bar_canon), 3)
        bar = bar_canon
    except Exception:
        bar_canon, approx_err = None, None
    # 검산 — 정규 근사가 p95 를 얼마나 맞히나
    p95_pred = cc["mean"] + 1.645 * cc["std"]
    # ⚠원장에는 **선이 둘** 있다. 사전등록이 정한 막대는 p99.9 이고,
    #   noise_distance_frame.read_lines 의 readable_db 는 그보다 **더 엄한** 별개 선이다.
    #   어느 쪽인지 안 밝히고 «막대» 라고 쓰면 판정이 갈린다 — 둘 다 싣는다.
    rl = FRAME.get("read_lines", {}).get(str(int(el)), {})
    return dict(bar_db=round(bar, 3), mean=cc["mean"], std=cc["std"],
                p95_ledger=cc["p95"], p95_normal_approx=round(p95_pred, 3),
                p95_err_db=round(abs(p95_pred - cc["p95"]), 3), n_trial=n_trial,
                canon_source=("게이트 20,000 시행 경험적 p99.9" if bar_canon is not None
                              else "정규 근사(20,000 판 없음)"),
                normal_approx_minus_canon_db=approx_err,
                rule_ko="⭐정본 막대 = 빗살 대비 귀무분포 p99.9 (사전등록 규칙, 정규 근사 mean+3.090σ)",
                frame_readable_db=rl.get("readable_db"),
                frame_undecidable_db=rl.get("undecidable_db"),
                two_lines_note_ko=("원장의 readable_db 는 평균+4.46σ 로 p99.9(3.09σ)보다 엄하다. "
                                   "판정은 사전등록 막대(p99.9)로 하고, 더 엄한 선은 참고로 겹쳐 둔다"))


def crossing(curve, bar):
    """빗살 대비 곡선이 막대를 **아래에서 위로** 뚫는 SNR [dB] — 선형 보간."""
    xs = [p["snr_ac_db"] for p in curve]
    ys = [p["comb_db_mean"] for p in curve]
    for i in range(1, len(xs)):
        if ys[i - 1] < bar <= ys[i]:
            t = (bar - ys[i - 1]) / (ys[i] - ys[i - 1])
            return round(xs[i - 1] + t * (xs[i] - xs[i - 1]), 3)
    return None


def range_at_snr(cells, snr_db):
    """거리 칸의 (log10 R, SNR) 직선을 맞춰 그 SNR 이 되는 거리 [m]."""
    pts = [(np.log10(c["range_m"]), c["by_convention"]["S1"]["snr_ac_db"])
           for c in cells if c.get("by_convention", {}).get("S1")]
    if len(pts) < 2:
        return None, None
    x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
    a, b = np.polyfit(x, y, 1)                       # SNR = a·log10R + b
    if a == 0:
        return None, (a, b)
    return round(float(10 ** ((snr_db - b) / a)), 1), (round(float(a), 2), round(float(b), 2))


def main():
    t0 = time.time()
    with_maps = "--with-maps" in sys.argv
    nb = null_bar_db()
    bar = nb["bar_db"]

    rows = {}
    for key, label, _c in ARMS:
        cs = cells_for(key)
        if not cs:
            continue
        c15 = cs[0]
        cur = c15.get("snr_curve") or []
        xs = crossing(cur, bar)
        rng, law = range_at_snr(cs, xs) if xs is not None else (None, None)
        law_key = f"{key}_el{EL:+.0f}".replace("+0", "+0")
        erl = FRAME.get("engine_range_law", {}).get(law_key, {})
        dp = (abs(erl.get("measured_p", 0) - erl.get("assumed_p", 0))
              if erl else None)
        rows[key] = dict(
            label=label, clean_comb_db=c15["clean"]["comb_contrast_db"],
            range_law_measured_p=erl.get("measured_p"),
            range_law_assumed_p=erl.get("assumed_p"),
            range_extrapolation_trustworthy=(None if dp is None else bool(dp <= 0.5)),
            range_caveat_ko=(None if dp is None or dp <= 0.5 else
                             f"⛔거리 외삽 신뢰 불가 — 이 팔의 측정 거리지수 p="
                             f"{erl.get('measured_p')} 가 규약값 {erl.get('assumed_p')} 와 "
                             f"{dp:.2f} 벌어진다. 엔진 자체가 거리에 따라 레벨을 나르고 있어 "
                             f"레이다식을 한 번 더 얹으면 이중 계상이다"),
            snr_at_bar_db=xs, snr_law_db_per_decade=(law[0] if law else None),
            snr_at_15m_db=c15["by_convention"]["S1"]["snr_ac_db"],
            readable_range_m=rng,
            ranges_in_ledger=[c["range_m"] for c in cs],
            note_ko=("빗살 대비가 귀무 막대를 뚫는 SNR 과, 그 SNR 이 되는 거리. "
                     "⚠거리는 이 팔의 거리 칸으로 맞춘 직선의 **연장**이다"))

    # ── 그림 ⓑⓒ (선 그림 — 싸다) ────────────────────────────────────────
    fig, ax = plt.subplots(1, 2, figsize=(15.5, 5.6))

    for key, label, col in ARMS:
        cs = cells_for(key)
        if not cs:
            continue
        cur = cs[0].get("snr_curve") or []
        if not cur:
            continue
        x = [p["snr_ac_db"] for p in cur]
        y = [p["comb_db_mean"] for p in cur]
        s = [p["comb_db_std"] for p in cur]
        ax[0].plot(x, y, lw=2.0, color=col, label=label)
        ax[0].fill_between(x, np.array(y) - np.array(s), np.array(y) + np.array(s),
                           color=col, alpha=0.12, lw=0)
        xs = rows[key]["snr_at_bar_db"]
        if xs is not None:
            ax[0].plot([xs], [bar], "o", ms=7, color=col, zorder=5)
    ax[0].axhline(bar, color="k", ls="--", lw=1.6)
    x1 = ax[0].get_xlim()[1]
    ax[0].annotate(f"decision bar {bar:.2f} dB\n(noise only, p99.9, "
                   f"{nb['n_trial']:,} trials)", xy=(x1, bar), xytext=(-8, 8),
                   textcoords="offset points", ha="right", va="bottom", fontsize=9.5,
                   bbox=dict(fc="white", ec="0.7", alpha=0.9, pad=2.5))
    if nb.get("frame_readable_db") is not None:
        ax[0].axhline(nb["frame_readable_db"], color="0.45", ls=":", lw=1.4)
        ax[0].annotate(f"stricter line {nb['frame_readable_db']:.2f} dB",
                       xy=(x1, nb["frame_readable_db"]), xytext=(-8, -14),
                       textcoords="offset points", ha="right", va="top",
                       fontsize=9, color="0.45",
                       bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))
    ax[0].set_xlabel("per-sample SNR of the moving part [dB]")
    ax[0].set_ylabel("comb contrast [dB]")
    ax[0].set_title("how much SNR the pattern needs", pad=7)
    ax[0].grid(alpha=0.3)
    ax[0].legend(fontsize=9.5, loc="upper left")

    for key, label, col in ARMS:
        cs = cells_for(key)
        pts = [(c["range_m"], c["by_convention"]["S1"]["snr_ac_db"]) for c in cs
               if c.get("by_convention", {}).get("S1")]
        if len(pts) < 2:
            continue
        ax[1].plot([p[0] for p in pts], [p[1] for p in pts], "o-", lw=2.0, color=col,
                   label=label)
        xs, rng = rows[key]["snr_at_bar_db"], rows[key]["readable_range_m"]
        if xs is not None and rng:
            ok = rows[key].get("range_extrapolation_trustworthy")
            # ⛔거리 외삽을 못 믿는 팔은 별을 비워 그린다(엔진이 이미 거리로 레벨을 나른다)
            ax[1].plot([rng], [xs], "*", ms=16, color=col, zorder=5,
                       mfc=(col if ok else "none"), mew=1.8)
    ax[1].set_xscale("log")
    from matplotlib.ticker import FixedLocator, NullLocator, FixedFormatter
    tk = [15, 30, 60, 120, 250, 500, 1000]
    ax[1].xaxis.set_major_locator(FixedLocator(tk))
    ax[1].xaxis.set_major_formatter(FixedFormatter([str(t) for t in tk]))
    ax[1].xaxis.set_minor_locator(NullLocator())      # 로그 보조 눈금이 겹쳐 읽힌다
    ax[1].set_xlabel("range [m]")
    ax[1].set_ylabel("per-sample SNR of the moving part [dB]")
    ax[1].set_title("and how far that SNR reaches", pad=7)
    ax[1].grid(alpha=0.3, which="both")
    ax[1].legend(fontsize=9.5, loc="lower left")

    fig.suptitle(f"{SC['label_en']}  ·  EIRP {SC['eirp_dbm']:.0f} dBm  ·  "
                 f"CPI {SC['cpi_s']*1e3:.0f} ms  ·  looking up from "
                 f"{abs(EL):.0f}{chr(176)} below the drone",
                 fontsize=13.5, color="0.3")
    fig.text(0.5, 0.905, "stars mark where the pattern stops being readable   "
                         "(hollow = the range extrapolation is not trustworthy "
                         "for that arm)", ha="center", fontsize=10.5, color="0.45")
    fig.text(0.5, 0.015,
             "verified: the ordering between arms and the SNR a pattern needs.   "
             "not verified: the absolute metres — no field comparison yet, "
             "and transmit-to-receive isolation is unmeasured.",
             ha="center", fontsize=10.5, color="0.45")
    fig.tight_layout(rect=(0, 0.045, 1, 0.895))
    p = f"{FIG}/noise_snr_panels.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)

    figs = [p]
    if with_maps:
        figs.append(_maps())

    doc = {"_meta": {
        "generator": "benchmark/noise_snr_figure_0818.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "3 장(잡음)의 «SNR 이 드러나는» 그림 — 잣대 vs SNR, SNR vs 거리",
        "gpu_used": False,
        "inputs": ["outputs/noise_distance_frame.json", "outputs/link_budget_canon_0816.json"],
        "scenario": SCN, "eirp_dbm": SC["eirp_dbm"], "cpi_s": SC["cpi_s"], "el_deg": EL,
        "elapsed_s": round(time.time() - t0, 2)},
        "null_bar": nb, "arms": rows, "figures": figs,
        "quoting_rule_ko": ("⛔시나리오 이름 없이 미터만 말하지 않는다 — 저장소에 EIRP "
                            "12·23·27·32·47·63 dBm 이 같이 산다. 그림에 이름과 EIRP 를 박았다.")}
    json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"═══ 판정 막대 ═══\n  {bar:.2f} dB  (귀무 {nb['n_trial']} 시행 · "
          f"평균 {nb['mean']:+.3f} · σ {nb['std']:.3f})")
    print(f"  검산: 정규 근사 p95 {nb['p95_normal_approx']:+.3f} vs 원장 p95 "
          f"{nb['p95_ledger']:+.3f}  → 차 {nb['p95_err_db']:.3f} dB")
    print(f"\n═══ 팔마다 — 막대를 뚫는 SNR 과 그 거리 (앙각 {EL:.0f}°) ═══")
    print(f"  {'팔':30s} {'깨끗한 빗살':>10s} {'막대통과 SNR':>12s} {'15 m SNR':>9s} {'읽기 한계':>10s}")
    for k, r in rows.items():
        flag = "" if r.get("range_extrapolation_trustworthy") in (True, None) else "  ⛔거리 외삽 불가"
        print(f"  {r['label']:30s} {r['clean_comb_db']:9.1f} dB "
              f"{r['snr_at_bar_db']!s:>11} dB {r['snr_at_15m_db']:8.1f} dB "
              f"{(str(r['readable_range_m'])+' m') if r['readable_range_m'] else '—':>10}{flag}")
    print(f"\nsaved {OUT}")
    for f in figs:
        print(f"saved {f}")


def _maps():
    """ⓐ 무늬가 녹는 과정 — 같은 STFT 를 SNR 을 낮춰 가며. ⚠CPU 를 크게 쓴다."""
    import glob
    from md_mapstyle import auto_periods, flash_spec, draw
    TJ = json.load(open(os.path.join(ROOT, "outputs", "switch_grid.json")))["_meta"]
    PRF, FFL, FTIP = 19700.0, float(TJ["f_flash_hz"]), float(TJ["f_tip_hz"])
    per = auto_periods(PRF, FFL)
    E = None
    for f in sorted(glob.glob(os.path.join(ROOT, "outputs", "elev_sweep_shards",
                                           "ours_r15_n8192_el-30_*.npz"))):
        d = np.load(f)
        n = int(np.asarray(d["meta"], float)[3])
        if E is None:
            E = np.zeros(n, complex)
        E[d["idx"].astype(int)] = d["E"]
    w = E[:int(round(0.058 * PRF))]
    w = w - w.mean()
    pac = float((np.abs(w) ** 2).mean())
    rng = np.random.default_rng(5)
    lv = [None, 20.0, 10.0, 3.0, 0.0]
    fig, ax = plt.subplots(1, len(lv), figsize=(4.6 * len(lv), 4.6),
                           sharex=True, sharey=True)
    for a, s in zip(ax, lv):
        x = w if s is None else w + np.sqrt(pac / 10 ** (s / 10) / 2) * (
            rng.normal(size=w.size) + 1j * rng.normal(size=w.size))
        f_, t_, S, _ = flash_spec(x, PRF, FFL, per)
        draw(a, t_, f_, S, FTIP)
        a.set_ylim(-2000, 2000)
        a.set_title("no noise" if s is None else f"SNR {s:.0f} dB", pad=7)
        a.set_xlabel("time [ms]")
    ax[0].set_ylabel("Doppler [Hz]")
    fig.suptitle("the same run as noise is added, looking up from 30" + chr(176) +
                 " below the drone — each panel scaled to its own peak",
                 fontsize=14, color="0.35")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    p = f"{FIG}/noise_snr_maps.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


if __name__ == "__main__":
    main()
