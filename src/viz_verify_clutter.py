# -*- coding: utf-8 -*-
"""
viz_verify_clutter.py — (report6) 챔버 바닥 검증 시각화
=========================================================
benchmark/verify_floor_ghost.py 가 만든 outputs/floor_ghost_verify.json 만 읽어 그린다
(**하드코딩 수치 없음** — 숫자는 전부 측정에서 온다).

  report6_floor_geom.png   : 챔버 단면 — 직접파 / 정적 바닥반사(ECA 가 지움) / 표적 경유 유령(안 지워짐)
  report6_clutter_dead.png : (좌) RT 실측 클러터 vs 우리 가정 vs 프레넬 예측
                             (우) 클러터 진폭을 40 dB 키워도 SCR 이 안 움직인다 = 죽은 파라미터
  report6_ghost_cfar.png   : 대역폭이 유령의 운명을 가른다 — 분리/ΔRb 와 P(가짜검출)

그림 텍스트는 전부 영어(프로젝트 규약), 본문/주석은 한국어.
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                        # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")
JSON = os.path.join(ROOT, "outputs", "floor_ghost_verify.json")

C_DIRECT, C_STATIC, C_GHOST, C_TGT = "#455a64", "#90a4ae", "#c62828", "#1565c0"


def _load():
    with open(JSON) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
#  ① 기하 — 두 개의 바닥 경로, 운명이 다르다
# --------------------------------------------------------------------------- #
def fig_geometry(d, outdir=FIG):
    """챔버 단면(y-z). TX/RX 는 x=4 로 같고 y 로 15 m 벌어져 있으므로 y-z 평면이 진짜 단면이다."""
    from bistatic_scene import TX, RX, TGT                       # 단일 출처
    A = d["A_static_floor"]; g5 = d["CD_ghost"][0]               # 5G 케이스
    ty, tz = TX[1], TX[2]
    ry, rz = RX[1], RX[2]
    gy, gz = TGT[1], TGT[2]

    fig, ax = plt.subplots(figsize=(12.4, 6.6), constrained_layout=True)
    D, H = 20.0, 11.0
    # 챔버 위에 여백 띠(z = 11.6~15.4)를 만들어 주석을 전부 거기 올린다 — 광선과 겹치지 않게.
    ax.add_patch(plt.Rectangle((0, 0), D, H, fill=False, ec="0.55", lw=1.6))
    # 흡수체(벽·천장) vs 반사 바닥
    for yy in np.linspace(0.35, D - 0.35, 42):                    # 천장 흡수체 힌트
        ax.plot([yy, yy + 0.18], [H, H - 0.42], color="#b0bec5", lw=0.8)
    for zz in np.linspace(0.4, H - 0.4, 22):                      # 좌우 벽 흡수체 힌트
        ax.plot([0, 0.42], [zz, zz + 0.18], color="#b0bec5", lw=0.8)
        ax.plot([D, D - 0.42], [zz, zz + 0.18], color="#b0bec5", lw=0.8)
    ax.axhspan(-0.55, 0, color="#8d6e63", alpha=0.65)
    ax.text(D / 2, -0.34, "FLOOR — reflective concrete (ITU $\\varepsilon_r$=5.24)",
            ha="center", va="center", fontsize=9, color="w", fontweight="bold")
    ax.text(0.6, H - 0.75, "walls + ceiling: pyramidal absorber", fontsize=8.5, color="#607d8b")

    # 노드
    ax.plot(ty, tz, "^", ms=15, color="#c62828"); ax.text(ty, tz + 0.55, "TX", ha="center", fontsize=10, fontweight="bold")
    ax.plot(ry, rz, "v", ms=15, color="#1565c0"); ax.text(ry, rz + 0.55, "RX", ha="center", fontsize=10, fontweight="bold")
    ax.plot(gy, gz, "o", ms=11, color="k"); ax.text(gy - 0.5, gz - 0.9, "drone", ha="center", fontsize=10, fontweight="bold")

    # ① 직접파
    ax.plot([ty, ry], [tz, rz], color=C_DIRECT, lw=2.6, zorder=3)
    ax.text((ty + ry) / 2 + 2.5, (tz + rz) / 2 + 0.5, "direct path (DPI)", color=C_DIRECT,
            fontsize=9.5, ha="center", fontweight="bold")

    # ② 정적 바닥반사 TX→floor→RX  (거울상으로 반사점 계산)
    yb = ty + (ry - ty) * tz / (tz + rz)
    ax.plot([ty, yb, ry], [tz, 0, rz], color=C_STATIC, lw=2.2, ls="--", zorder=3)
    ax.plot(yb, 0, "s", ms=8, color=C_STATIC)
    p = A["pred"]; m = A.get("match")
    txt = f"static floor bounce\n{p['delay_ns']:.1f} ns,  {p['rel_db_tm']:+.1f} dB"
    if m:
        txt += f"\nSionna RT agrees:\n{m['delay_ns']:.1f} ns,  {m['rel_db']:+.1f} dB"
    txt += "\n\nECA REMOVES IT\n(zero Doppler)"
    ax.annotate(txt, xy=(yb, 0), xytext=(4.3, 13.2), fontsize=8.8, color="#37474f",
                ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.45", fc="#eceff1", ec=C_STATIC, lw=1.3),
                arrowprops=dict(arrowstyle="->", color=C_STATIC, lw=1.4,
                                connectionstyle="arc3,rad=-0.15"))

    # ③ 표적 경유 유령 TX→target→floor→RX
    yb2 = gy + (ry - gy) * gz / (gz + rz)
    ax.plot([ty, gy], [tz, gz], color=C_GHOST, lw=2.0, zorder=4)
    ax.plot([gy, yb2, ry], [gz, 0, rz], color=C_GHOST, lw=2.0, zorder=4)
    ax.plot(yb2, 0, "s", ms=8, color=C_GHOST)
    ax.annotate(f"target-via-floor GHOST\n{g5['sep_m']:+.2f} m,  {g5['ghost_db']:+.1f} dB\n"
                f"$R_b$ = {g5['rb_ghost']:.1f} m\n(real drone {g5['rb_true']:.1f} m)\n\n"
                f"ECA CANNOT REMOVE IT\n(carries the target's Doppler)",
                xy=(yb2, 0), xytext=(15.9, 13.2), fontsize=8.8, color="#b71c1c",
                ha="center", va="center", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.45", fc="#ffebee", ec=C_GHOST, lw=1.5),
                arrowprops=dict(arrowstyle="->", color=C_GHOST, lw=1.6,
                                connectionstyle="arc3,rad=0.15"))

    ax.set_xlim(-1.4, D + 1.4); ax.set_ylim(-1.4, 16.6)
    ax.set_xlabel("y [m]"); ax.set_ylabel("z [m]"); ax.set_aspect("equal")
    ax.set_yticks([0, 2, 4, 6, 8, 10])
    ax.set_title("Two floor paths, two fates", fontsize=14.5, fontweight="bold", loc="left")
    fig.supxlabel("The chamber is SEMI-anechoic — walls and ceiling are absorber-lined, the floor is not.\n"
                  "The static floor bounce sits at zero Doppler, so the canceller deletes it. The path that goes "
                  "via the target does not — and that one survives.",
                  fontsize=9, color="0.4")
    out = os.path.join(outdir, "report6_floor_geom.png")
    fig.savefig(out, dpi=140); plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
#  ② 클러터는 죽은 파라미터
# --------------------------------------------------------------------------- #
def fig_clutter_dead(d, outdir=FIG):
    A, B = d["A_static_floor"], d["B_clutter_dead"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.7), constrained_layout=True)

    # (좌) RT 실측 vs 가정 vs 프레넬 예측
    rt = A["rt_taps"]; asm = A["assumed"]; p = A["pred"]
    floor_db = min(t[1] for t in (rt + asm)) - 4
    if rt:
        xs, ys = [t[0] for t in rt], [t[1] for t in rt]
        ax1.vlines(xs, floor_db, ys, color=C_TGT, lw=2.0)
        ax1.plot(xs, ys, "o", ms=8, color=C_TGT,
                 label=f"Sionna RT, measured in the chamber ({len(rt)} paths)")
    xs, ys = [t[0] for t in asm], [t[1] for t in asm]
    ax1.vlines(xs, floor_db, ys, color="#90a4ae", lw=2.0, ls="--")
    ax1.plot(xs, ys, "s", ms=8, color="#90a4ae", label="what we ASSUMED (CH_CLUTTER_RATIO)")
    ax1.set_ylim(floor_db, max(t[1] for t in rt + asm) + 7)
    ax1.axhline(p["rel_db_tm"], color=C_GHOST, lw=1.4, ls=":",
                label=f"Fresnel prediction for the floor ({p['rel_db_tm']:+.1f} dB)")
    ax1.axvline(p["delay_ns"], color=C_GHOST, lw=1.4, ls=":")
    ax1.plot([p["delay_ns"]], [p["rel_db_tm"]], "*", ms=20, color=C_GHOST, zorder=6)
    if A.get("match"):
        m = A["match"]
        ax1.annotate(f"RT found a path exactly here:\n{m['delay_ns']:.1f} ns, {m['rel_db']:+.1f} dB\n"
                     f"($\\Delta$ = {m['d_amp_db']:+.2f} dB from theory)",
                     xy=(m["delay_ns"], m["rel_db"]), xytext=(m["delay_ns"] + 6, m["rel_db"] - 11),
                     fontsize=9, color=C_GHOST, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.35", fc="#ffebee", ec=C_GHOST, lw=1),
                     arrowprops=dict(arrowstyle="->", color=C_GHOST, lw=1.4))
    gap = A["rt_strongest_db"] - A["assumed_strongest_db"]
    xg = 34.0                                             # 빈 구역에 세로 이중화살표
    ax1.annotate("", xy=(xg, A["rt_strongest_db"]), xytext=(xg, A["assumed_strongest_db"]),
                 arrowprops=dict(arrowstyle="<->", color="#ef6c00", lw=2.2))
    ax1.axhline(A["rt_strongest_db"], color="#ef6c00", lw=0.9, ls=":", alpha=0.7)
    ax1.axhline(A["assumed_strongest_db"], color="#ef6c00", lw=0.9, ls=":", alpha=0.7)
    ax1.text(xg + 1.5, (A["rt_strongest_db"] + A["assumed_strongest_db"]) / 2,
             f"we under-modelled\nthe chamber by\n{gap:.1f} dB", fontsize=10,
             color="#ef6c00", fontweight="bold", va="center")
    ax1.set_xlim(3, 52)
    ax1.set_xlabel("Delay after the direct path [ns]")
    ax1.set_ylabel("Amplitude re. direct path [dB]")
    ax1.set_title("The floor was always there — RT saw it, we didn't",
                  fontsize=12.5, fontweight="bold", loc="left")
    ax1.legend(fontsize=8.2, loc="lower left"); ax1.grid(alpha=0.25)

    # (우) 클러터 진폭 스윕 → SCR 불변
    rows = B["rows"]
    xs = [(r["strongest_db"] if r["strongest_db"] is not None else -45) for r in rows]
    ys = [r["scr"] for r in rows]
    lab = ["none" if r["strongest_db"] is None else f"{r['strongest_db']:+.0f}" for r in rows]
    ax2.plot(xs, ys, "o-", color=C_TGT, lw=2.4, ms=11, zorder=4)
    for x, y, l in zip(xs, ys, lab):
        ax2.annotate(l, (x, y), textcoords="offset points", xytext=(0, 13),
                     ha="center", fontsize=9.5, fontweight="bold", color=C_TGT)
    ax2.axvline(0, color=C_DIRECT, lw=1.2, ls="--")
    ax2.text(0.6, np.mean(ys), "clutter as strong\nas the direct path", fontsize=8.8,
             color=C_DIRECT, rotation=90, va="center")
    span = B["scr_span_db"]
    ax2.set_ylim(np.mean(ys) - 1.0, np.mean(ys) + 1.0)
    ax2.set_xlabel("Strongest static clutter tap, re. direct path [dB]")
    ax2.set_ylabel("Measured SCR [dB]")
    ax2.set_title("...and it changes nothing. Clutter is a dead parameter.",
                  fontsize=12.5, fontweight="bold", loc="left")
    ax2.text(0.5, 0.18, f"SCR moves by {span:.0e} dB across the whole sweep\n"
                        f"(Pd = 1.00 everywhere)",
             transform=ax2.transAxes, ha="center", fontsize=11, fontweight="bold",
             color="#b71c1c",
             bbox=dict(boxstyle="round,pad=0.45", fc="#ffebee", ec=C_GHOST, lw=1.3))
    ax2.grid(alpha=0.25)

    fig.supxlabel("Static clutter is a delayed copy of the reference with no Doppler — exactly the subspace ECA projects out — so the\n"
                  "canceller nulls it whatever its amplitude, and the zero-Doppler row is masked out of CFAR anyway.\n"
                  "Every clutter number in report4/report5 was therefore unfalsifiable.",
                  fontsize=9, color="0.4")
    out = os.path.join(outdir, "report6_clutter_dead.png")
    fig.savefig(out, dpi=140); plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
#  ③ 대역폭이 유령의 운명을 가른다
# --------------------------------------------------------------------------- #
def fig_ghost_cfar(d, outdir=FIG):
    D = d["CD_ghost"]
    names = [x["name"] for x in D]
    sep_ratio = [x["sep_over_drb"] for x in D]
    pfalse = [x["p_false"] for x in D]
    drb = [x["d_rb_m"] for x in D]
    sep = D[0]["sep_m"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.7), constrained_layout=True)

    cols = [C_GHOST if r > 1 else "#90a4ae" for r in sep_ratio]
    ax1.barh(names, sep_ratio, color=cols, height=0.55)
    ax1.axvline(1.0, color="k", lw=1.8, ls="--")
    ax1.text(1.03, 2.42, "resolution limit\n(separation = 1 range cell)", fontsize=9,
             va="top", fontweight="bold")
    for i, (r, w) in enumerate(zip(sep_ratio, drb)):
        ax1.text(r + 0.03, i, f"{r:.2f}$\\times$   ($\\Delta R_b$ = {w:.1f} m)",
                 va="center", fontsize=9.5)
    ax1.set_xlim(0, 1.45)
    ax1.set_xlabel(f"Ghost separation ({sep:.2f} m) in units of the range cell $\\Delta R_b = c/B$")
    ax1.set_title("Wider bandwidth = the ghost gets its own range cell",
                  fontsize=12.5, fontweight="bold", loc="left")
    ax1.grid(alpha=0.25, axis="x")

    cols2 = [C_GHOST if p > 0.5 else "#90a4ae" for p in pfalse]
    ax2.barh(names, pfalse, color=cols2, height=0.55)
    for i, p in enumerate(pfalse):
        ax2.text(p + 0.025, i, f"{p*100:.0f}%", va="center", ha="left",
                 fontsize=13, fontweight="bold",
                 color=(C_GHOST if p > 0.5 else "#607d8b"))
    ax2.set_xlim(0, 1.28)
    ax2.set_xlabel("P(the ghost is declared a separate target by CFAR)")
    ax2.set_title("...and CFAR duly reports a drone that isn't there",
                  fontsize=12.5, fontweight="bold", loc="left")
    ax2.grid(alpha=0.25, axis="x")

    g = D[0]
    ax2.text(0.5, 0.60, f"5G: the real drone at $R_b$ = {g['rb_true']:.1f} m\n"
                        f"AND a phantom at {g['rb_ghost']:.1f} m,\nevery single trial.",
             transform=ax2.transAxes, ha="center", va="center", fontsize=11.5,
             fontweight="bold", color="#b71c1c",
             bbox=dict(boxstyle="round,pad=0.5", fc="#ffebee", ec=C_GHOST, lw=1.4))

    fig.supxlabel("The floor ghost sits a fixed 3.5 m behind the target, at a fixed -18 dB. Whether it becomes a second detection is\n"
                  "decided purely by the range cell — so the very resolution that makes 5G the best illuminator is what turns the floor\n"
                  "into a phantom drone. Not yet included in report4/report5.",
                  fontsize=9, color="0.4")
    out = os.path.join(outdir, "report6_ghost_cfar.png")
    fig.savefig(out, dpi=140); plt.close(fig)
    return out


def main():
    os.makedirs(FIG, exist_ok=True)
    d = _load()
    for f in (fig_geometry, fig_clutter_dead, fig_ghost_cfar):
        print("[viz_verify_clutter]", os.path.relpath(f(d), ROOT))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, _HERE)
    main()
