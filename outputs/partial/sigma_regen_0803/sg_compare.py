# -*- coding: utf-8 -*-
"""구(2026-07-29) ↔ 신(2026-08-03) σ 격자 대조표 + 그림.

무엇을 재는가
  · 셀단위 Δ = 신 − 구 [dB] : max|Δ| · rms · 평균
  · 레벨이동  : 10log10⟨σ⟩ 차이 (m² 선형평균 = 인용규약)
  · 패턴상관  : 같은 셀끼리 dB 값 상관 ρ — 각도구조가 남았는지
  · 백분위·CDF: p10/p50/p90 이동, KS 통계
  · ⭐순위     : 기체간 σ 순위가 바뀌었는가 (밴드별 · 전체)
산출: outputs/sigma_grid_regen.json · outputs/figs/sigma_grid_old_vs_new.png
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = "/workspace/sionna"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

NEW = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")
OLD = os.path.join(ROOT, "outputs", "archive", "report13_sigma_grid_pre0803.json")
OUT_JSON = os.path.join(ROOT, "outputs", "sigma_grid_regen.json")
OUT_FIG = os.path.join(ROOT, "outputs", "figs", "sigma_grid_old_vs_new.png")
BANDS = ["LTE 1.8 GHz", "5G NR 3.5 GHz", "WiFi 5.2 GHz"]
BAND_SHORT = {"LTE 1.8 GHz": "LTE 1.8", "5G NR 3.5 GHz": "5G NR 3.5", "WiFi 5.2 GHz": "WiFi 5.2"}

# 데이터viz 기준 팔레트 (light) — 계열은 2~3개만 쓴다
C_OLD, C_NEW, C_3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, INK3 = "#0b0b0b", "#52514e", "#8a8983"


def lin_mean_db(a_db):
    return float(10.0 * np.log10(np.mean(10.0 ** (np.asarray(a_db, float) / 10.0))))


def ks(a, b):
    a, b = np.sort(np.ravel(a)), np.sort(np.ravel(b))
    g = np.concatenate([a, b])
    return float(np.max(np.abs(np.searchsorted(a, g, "right") / a.size
                               - np.searchsorted(b, g, "right") / b.size)))


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


def kendall(x, y):
    n, c, d = len(x), 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(x[i] - x[j]) * np.sign(y[i] - y[j])
            c += s > 0
            d += s < 0
    return float((c - d) / (0.5 * n * (n - 1)))


def main():
    new, old = json.load(open(NEW)), json.load(open(OLD))
    gn, go = new["sigma"]["grid"], old["sigma"]["grid"]
    shared = [d for d in gn if d in go]
    only_new = [d for d in gn if d not in go]
    print("공통 기체:", shared, "| 신규:", only_new)

    per, dstat = {}, {}
    for d in shared:
        rows = {}
        for b in BANDS:
            no, oo = gn[d][b], go[d][b]
            assert no["az_deg"] == oo["az_deg"] and no["el_deg"] == oo["el_deg"], f"{d}/{b} 축 불일치"
            for key, tag in (("sigma_smooth_dbsm", "smooth"), ("sigma_dbsm", "raw")):
                N = np.asarray(no[key], float)
                O = np.asarray(oo[key], float)
                dl = (N - O).ravel()
                r = dict(
                    n_cells=int(dl.size),
                    max_abs_delta_db=float(np.max(np.abs(dl))),
                    rms_delta_db=float(np.sqrt(np.mean(dl ** 2))),
                    mean_cell_delta_db=float(np.mean(dl)),
                    level_shift_db=lin_mean_db(N) - lin_mean_db(O),
                    old_level_dbsm=lin_mean_db(O), new_level_dbsm=lin_mean_db(N),
                    pattern_corr=float(np.corrcoef(O.ravel(), N.ravel())[0, 1]),
                    n_within_0p01db=int(np.sum(np.abs(dl) < 0.01)),
                    n_within_1db=int(np.sum(np.abs(dl) < 1.0)),
                    ks_stat=ks(O, N),
                    pct_old_dbsm={p: float(np.percentile(O, q)) for p, q in
                                  (("p10", 10), ("p50", 50), ("p90", 90))},
                    pct_new_dbsm={p: float(np.percentile(N, q)) for p, q in
                                  (("p10", 10), ("p50", 50), ("p90", 90))})
                r["pct_delta_db"] = {k: r["pct_new_dbsm"][k] - r["pct_old_dbsm"][k]
                                     for k in r["pct_old_dbsm"]}
                rows.setdefault(tag, {})[b] = r
        # 기체 전체(3밴드 풀링, smooth 기준)
        No = np.concatenate([np.asarray(gn[d][b]["sigma_smooth_dbsm"], float).ravel() for b in BANDS])
        Oo = np.concatenate([np.asarray(go[d][b]["sigma_smooth_dbsm"], float).ravel() for b in BANDS])
        dl = No - Oo
        rows["pooled"] = dict(
            n_cells=int(dl.size), max_abs_delta_db=float(np.max(np.abs(dl))),
            rms_delta_db=float(np.sqrt(np.mean(dl ** 2))),
            mean_cell_delta_db=float(np.mean(dl)),
            level_shift_db=lin_mean_db(No) - lin_mean_db(Oo),
            old_level_dbsm=lin_mean_db(Oo), new_level_dbsm=lin_mean_db(No),
            pattern_corr=float(np.corrcoef(Oo, No)[0, 1]),
            n_within_0p01db=int(np.sum(np.abs(dl) < 0.01)),
            ks_stat=ks(Oo, No),
            pct_old_dbsm={"p10": float(np.percentile(Oo, 10)), "p50": float(np.percentile(Oo, 50)),
                          "p90": float(np.percentile(Oo, 90))},
            pct_new_dbsm={"p10": float(np.percentile(No, 10)), "p50": float(np.percentile(No, 50)),
                          "p90": float(np.percentile(No, 90))})
        rows["pooled"]["pct_delta_db"] = {k: rows["pooled"]["pct_new_dbsm"][k]
                                          - rows["pooled"]["pct_old_dbsm"][k]
                                          for k in rows["pooled"]["pct_old_dbsm"]}
        per[d] = rows
        dstat[d] = rows["pooled"]

    # ── 순위 ──
    def level(g, d, b):
        return lin_mean_db(np.asarray(g[d][b]["sigma_smooth_dbsm"], float))

    def level_all(g, d):
        return lin_mean_db(np.concatenate(
            [np.asarray(g[d][b]["sigma_smooth_dbsm"], float).ravel() for b in BANDS]))

    ranking = {}
    changed = False
    for b in BANDS + ["ALL BANDS"]:
        f = (lambda g, d: level_all(g, d)) if b == "ALL BANDS" else (lambda g, d, b=b: level(g, d, b))
        lo = {d: f(go, d) for d in shared}
        ln = {d: f(gn, d) for d in shared}
        ro = sorted(shared, key=lambda d: -lo[d])
        rn = sorted(shared, key=lambda d: -ln[d])
        x = np.array([lo[d] for d in shared])
        y = np.array([ln[d] for d in shared])
        n_move = sum(1 for i, d in enumerate(ro) if rn.index(d) != i)
        ranking[b] = dict(
            old_order_desc=ro, new_order_desc=rn, changed=bool(ro != rn),
            n_drones_moved=int(n_move),
            old_level_dbsm={d: lo[d] for d in ro}, new_level_dbsm={d: ln[d] for d in rn},
            spearman=spearman(x, y), kendall_tau=kendall(list(x), list(y)),
            max_rank_shift=int(max(abs(rn.index(d) - ro.index(d)) for d in shared)))
        changed = changed or (ro != rn)
    # 신규 기체까지 넣은 오늘의 순위(대조 불가, 참고용)
    all_new = sorted(gn, key=lambda d: -level_all(gn, d))
    ranking["ALL BANDS (7 drones, new only)"] = dict(
        new_order_desc=all_new,
        new_level_dbsm={d: level_all(gn, d) for d in all_new},
        note="typhoonh480·x500v2 는 옛 격자에 없어 대조 불가 — 오늘 판의 순위만")

    summary = {d: dict(max_abs_delta_db=round(dstat[d]["max_abs_delta_db"], 2),
                       rms_delta_db=round(dstat[d]["rms_delta_db"], 2),
                       mean_cell_delta_db=round(dstat[d]["mean_cell_delta_db"], 2),
                       level_shift_db=round(dstat[d]["level_shift_db"], 2),
                       pattern_corr=round(dstat[d]["pattern_corr"], 3),
                       n_identical_cells=dstat[d]["n_within_0p01db"],
                       n_cells=dstat[d]["n_cells"]) for d in shared}

    obj = dict(
        meta=dict(
            title="sigma grid regeneration on today's mesh — old vs new",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            new=os.path.relpath(NEW, ROOT), old=os.path.relpath(OLD, ROOT),
            new_meta={k: new["meta"].get(k) for k in
                      ("generated", "git_rev", "div", "jitter", "n_f", "frac_bw", "smooth_deg",
                       "backend", "runtime_s", "mesh_fp", "worker_cpu_hours", "drones")},
            old_meta={k: old["meta"].get(k) for k in
                      ("generated", "git_rev", "div", "jitter", "n_f", "frac_bw", "smooth_deg",
                       "backend", "runtime_s", "mesh_generation", "drone_order")},
            axes_identical=True,
            statistic=("headline = sigma_smooth_dbsm (the consumed/quoted array); "
                       "level = 10log10 linear mean in m^2 (quote_policy)"),
            shared_drones=shared, new_only_drones=only_new),
        summary_by_drone=summary,
        by_drone_band=per,
        ranking=ranking,
        cache_prune=json.load(open(os.path.join(SCRATCH, "cache_prune.json"))))
    json.dump(obj, open(OUT_JSON, "w"), indent=1, ensure_ascii=False)
    print("→", OUT_JSON)
    figure(obj, gn, go, shared)
    return obj


# --------------------------------------------------------------------------- #
def figure(obj, gn, go, shared):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK3, "axes.labelcolor": INK2,
                         "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 10,
                         "figure.facecolor": "white", "axes.facecolor": "white"})
    order = sorted(shared, key=lambda d: -obj["summary_by_drone"][d]["max_abs_delta_db"])
    fig = plt.figure(figsize=(13.5, 12.2))
    gs = GridSpec(3, 6, figure=fig, hspace=0.52, wspace=0.75,
                  left=0.075, right=0.985, top=0.915, bottom=0.055)

    # (a) 기체별 Δ 막대 — 3계열(슬롯 1·2·3)
    ax = fig.add_subplot(gs[0, 0:3])
    y = np.arange(len(order))[::-1]
    h = 0.26
    v1 = [obj["summary_by_drone"][d]["max_abs_delta_db"] for d in order]
    v2 = [obj["summary_by_drone"][d]["rms_delta_db"] for d in order]
    v3 = [abs(obj["summary_by_drone"][d]["level_shift_db"]) for d in order]
    for k, (v, c, lab) in enumerate([(v1, C_OLD, "max |Δ|"), (v2, C_NEW, "rms Δ"),
                                     (v3, C_3, "|level shift|")]):
        ax.barh(y + (1 - k) * h, v, height=h * 0.9, color=c, label=lab, zorder=3)
        for yy, vv in zip(y + (1 - k) * h, v):
            ax.text(vv + 0.35, yy, f"{vv:.1f}", va="center", ha="left", fontsize=7.5, color=INK2)
    ax.set_yticks(y, order)
    ax.set_xlabel("cell-wise change, new − old  [dB]")
    ax.set_title("(a)  How far the grid moved  (3 bands pooled, 3240 cells / drone)", loc="left")
    ax.set_xlim(0, max(v1) * 1.22)
    ax.grid(axis="x", color="#e6e5e0", zorder=0)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # (b) 순위 slope chart
    ax = fig.add_subplot(gs[0, 3:6])
    rk = obj["ranking"]["ALL BANDS"]
    ro, rn = rk["old_order_desc"], rk["new_order_desc"]
    for d in shared:
        i, j = ro.index(d), rn.index(d)
        moved = i != j
        ax.plot([0, 1], [-i, -j], color=(C_NEW if moved else INK3), lw=2 if moved else 1.2,
                zorder=3 if moved else 2)
        ax.scatter([0, 1], [-i, -j], s=34, color=(C_NEW if moved else INK3), zorder=4)
        ax.text(-0.045, -i, f"{d}  {rk['old_level_dbsm'][d]:+.1f}", ha="right", va="center",
                fontsize=8.5, color=INK)
        ax.text(1.045, -j, f"{rk['new_level_dbsm'][d]:+.1f}  {d}", ha="left", va="center",
                fontsize=8.5, color=INK)
    ax.set_xlim(-0.62, 1.62)
    ax.set_ylim(-len(shared) + 0.4, 0.6)
    ax.set_xticks([0, 1], ["OLD (2026-07-29)", "NEW (2026-08-03)"])
    ax.set_yticks([])
    ax.set_title(f"(b)  Cross-drone sigma ranking, all bands  "
                 f"[{'CHANGED' if rk['changed'] else 'unchanged'}, "
                 f"Spearman {rk['spearman']:.2f}]", loc="left")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

    # (c) 백분위 덤벨
    ax = fig.add_subplot(gs[1, 0:3])
    labs, yy = [], []
    k = 0
    for d in order:
        p = obj["by_drone_band"][d]["pooled"]
        for q in ("p90", "p50", "p10"):
            o, n = p["pct_old_dbsm"][q], p["pct_new_dbsm"][q]
            ax.plot([o, n], [k, k], color=INK3, lw=1.1, zorder=2)
            ax.scatter([o], [k], s=30, color=C_OLD, zorder=3)
            ax.scatter([n], [k], s=30, color=C_NEW, zorder=4)
            labs.append(f"{d} {q}")
            yy.append(k)
            k -= 1
        k -= 0.7
    ax.set_yticks(yy, labs, fontsize=7.5)
    ax.set_xlabel("sigma  [dBsm]")
    ax.set_title("(c)  Percentiles move too — old ● → new ●  (percentile quoting is not a shelter)",
                 loc="left")
    ax.grid(axis="x", color="#e6e5e0", zorder=0)
    ax.set_axisbelow(True)
    ax.scatter([], [], s=30, color=C_OLD, label="old")
    ax.scatter([], [], s=30, color=C_NEW, label="new")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # (d) 방위 컷 — 각도구조가 남았는지
    d0, b0 = "mavic4pro", "5G NR 3.5 GHz"
    ax = fig.add_subplot(gs[1, 3:6])
    el = np.asarray(gn[d0][b0]["el_deg"], float)
    i = int(np.argmin(np.abs(el + 3.5)))
    az = np.asarray(gn[d0][b0]["az_deg"], float)
    O = np.asarray(go[d0][b0]["sigma_smooth_dbsm"], float)[i]
    N = np.asarray(gn[d0][b0]["sigma_smooth_dbsm"], float)[i]
    ax.plot(az, O, color=C_OLD, lw=1.6, label="old")
    ax.plot(az, N, color=C_NEW, lw=1.6, label="new")
    rho = float(np.corrcoef(O, N)[0, 1])
    ax.set_xlabel("azimuth  [deg]")
    ax.set_ylabel("sigma  [dBsm]")
    ax.set_xlim(0, 357)
    ax.set_title(f"(d)  {d0}, {BAND_SHORT[b0]} GHz, el = {el[i]:+.1f}°  —  "
                 f"pattern corr rho = {rho:.2f}", loc="left")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower right")
    ax.grid(color="#e6e5e0")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # (e..) CDF 소형다중 — 기체마다 한 칸
    for j, d in enumerate(order):
        ax = fig.add_subplot(gs[2, j])
        for g, c, lab in ((go, C_OLD, "old"), (gn, C_NEW, "new")):
            v = np.sort(np.concatenate(
                [np.asarray(g[d][b]["sigma_smooth_dbsm"], float).ravel() for b in BANDS]))
            ax.plot(v, np.linspace(0, 1, v.size), color=c, lw=1.6, label=lab)
        p = obj["by_drone_band"][d]["pooled"]
        ax.set_title(f"({chr(101+j)})  {d}\nKS = {p['ks_stat']:.2f}", loc="left", fontsize=9)
        ax.set_xlabel("sigma  [dBsm]")
        if j == 0:
            ax.set_ylabel("CDF")
            ax.legend(frameon=False, fontsize=8, loc="upper left")
        ax.grid(color="#e6e5e0")
        ax.set_axisbelow(True)
        ax.set_xlim(-55, 5)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    fig.suptitle("Free-space sigma grid regenerated on today's mesh — every cell moved\n"
                 "same settings (div=16, jitter=2, penetrate, n_f=3, 3° smoothing, "
                 "az 0…357°/3°, el 0…−20°, 3 bands)",
                 fontsize=12.5, color=INK, x=0.075, ha="left", y=0.985)
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=170)
    print("→", OUT_FIG)


if __name__ == "__main__":
    main()
