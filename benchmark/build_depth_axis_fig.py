# -*- coding: utf-8 -*-
"""
build_depth_axis_fig.py — ⭐**반사 깊이 축**(덱 30 장 Future work 1 번)의 판정 그림.

왜
--
08-16 병합으로 깊이 3 칸 12 개가 다 찼고 판정 원장
`outputs/depth_axis_verdict_0816.json` 이 그것을 읽었다. 그런데 **원장을 눈으로 보는
그림이 없었다** — 아틀라스 색인 `atlas/00_since_deck.html` 의 «아직 그림이 없는 것» 1 번이
바로 이 자리다. 이 스크립트가 그 자리를 메운다.

무엇을 그리나
------------
① `depth_axis_0816.png` — 원장의 **깊이 짝 22 개 전부**를 한 판에.
   ⭐핵심 장치는 «격자 산포 밴드를 띠로 겹치는 것»이다. 회색 띠 안이면 **판정 불가**이고,
   그 띠의 폭은 **앙각마다 다르다**(0° 3.86 · −30° 0.37 · −45° 0.09 · −60° 0.02 ·
   −75° 0.10 · −90° 5.62 dB). 옛 «전 앙각 3.86» 을 쓰면 빗각 판정을 놓친다.

⭐집 규약
   · 그림 안 글자는 **전부 영어** · 겹침 금지 · 범례는 그린 것과 1:1
   · 레벨(dB)은 전부 **정지 성분(DC) 제거 후** — moving power 열만 쓴다
   · 막대는 원장 헤드라인인 **가장 튄 자세 1 개를 솎은 값**(trim k=1). 생값이 크게
     다른 자리는 −60° 한 곳뿐이라 그 자리만 직접 주석을 단다.
   · 밴드는 **우리 커널(SBR+PO)에서 잰 것을 PathSolver 팔에 빌려 쓴 것**이다 — 캡션에 명시.

색
--
색맹 안전 검사(OKLab ΔE · protan/deutan/tritan 모사)를 통과한 세 색만 쓴다.
   slate #5B6570 · vermillion #D55E00 · band grey #C6CCD4
   (모든 짝 normal ΔE ≥ 24 · CVD 최소 ΔE ≥ 21)

사용법
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_depth_axis_fig.py

⛔GPU 안 쓴다 — 저장된 원장 JSON 만 읽는다.
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
from matplotlib.lines import Line2D                                      # noqa: E402
from matplotlib.patches import Patch                                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(ROOT, "outputs", "depth_axis_verdict_0816.json")
FIGDIR = os.path.join(ROOT, "outputs", "figures")
OUT = os.path.join(FIGDIR, "depth_axis_0816.png")

# ── 색 (색맹 안전 검사 통과) ────────────────────────────────────────────────
SLATE = "#5B6570"      # 밴드 안 — 판정 불가
VERM = "#D55E00"       # 밴드 밖 — 레벨이 움직였다
BAND = "#C6CCD4"       # 격자 산포 밴드
BLUE = "#0072B2"       # 회절 끔 / 단일 계열
INK = "#22282E"
MUTED = "#6E7780"
FAINT = "#C9CED4"

matplotlib.rcParams.update({
    "font.size": 10,
    "axes.edgecolor": "#B9BFC6",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.linewidth": 0.8,
})


def deg(el: float) -> str:
    """0 은 «0°», 음수는 유니코드 마이너스."""
    return "0°" if el == 0 else f"−{abs(el):.0f}°"


def rng(r: float) -> str:
    return f"{r:.0f} m"


# ═══════════════════════════════════════════════════════════════════════════ #
#  1. 원장 읽기 · 줄 배치
# ═══════════════════════════════════════════════════════════════════════════ #
def load():
    d = json.load(open(LEDGER, encoding="utf-8"))
    pairs = d["pairs"]
    nb = d["null_bands"]

    # ⭐줄 묶음 셋 — 원장의 in_standard_frame 깃발과 스위치 D 로만 가른다(손으로 안 고른다).
    grp_a = [p for p in pairs if p["in_standard_frame"]]
    grp_b = [p for p in pairs if not p["in_standard_frame"] and p["depths"] == [1, 3]]
    grp_c = [p for p in pairs if not p["in_standard_frame"] and p["depths"] == [1, 2]]
    assert len(grp_a) + len(grp_b) + len(grp_c) == len(pairs), "짝 분류가 안 맞는다"
    assert all(p["switches"]["D"] for p in grp_b), "B 묶음은 전부 회절 켠 조합이어야 한다"

    grp_a.sort(key=lambda p: (p["range_m"], -p["el_deg"], p["combo"]))
    grp_b.sort(key=lambda p: p["combo"])
    grp_c.sort(key=lambda p: -p["el_deg"])

    groups = [
        ("A", "Standard frame — the two arms our convention actually ships", grp_a),
        ("B", "Diffraction switched on — where depth still moves the level", grp_b),
        ("C", "All four switches on — depth 1 → 2, the elevation sweep", grp_c),
    ]
    return d, nb, groups


def place(groups, gap=1.90):
    """줄마다 y 좌표를 준다. 묶음 사이에 빈 칸을 둔다."""
    rows, y = [], 0.0
    heads = []
    for tag, title, ps in groups:
        heads.append((tag, title, y))
        for p in ps:
            rows.append((y, p))
            y += 1.0
        y += gap
    return rows, heads, y - gap


def row_label(p) -> str:
    """줄 이름 — 스위치 태그 · 앙각 · 거리. 깃발이 있으면 † 를 단다."""
    flagged = ("tip_ceiling_degenerate" in p["flags_d1"] + p["flags_dN"]
               or p["el_deg"] == 0.0)
    dagger = " †" if flagged else ""
    return f"{p['combo']} · {deg(p['el_deg'])} · {rng(p['range_m'])}{dagger}"


def headline(p, key):
    """원장 헤드라인 값 — 가장 튄 자세 k 개를 솎은 판."""
    return p["trim"][f"k{p['trim_headline_k']}"][key]


# ═══════════════════════════════════════════════════════════════════════════ #
#  2. 줄 판 셋 — 레벨 · 리듬 · 빗살  (+ 경로 수)
# ═══════════════════════════════════════════════════════════════════════════ #
def bar_panel(ax, rows, *, value_of, band_of, outside_of, xlim, title, sub,
              xlabel, na_of=None):
    """
    한 열 = 잣대 하나. 회색 띠 = 그 줄의 격자 산포 밴드.
    ⭐띠가 판보다 넓으면 그 줄은 판 전체가 회색이 된다 — «전부 밴드 안» 이라는 뜻 그대로다.
    """
    lo, hi = xlim
    for y, p in rows:
        b = band_of(p)
        if b is not None and b > 0:
            ax.barh(y, 2 * b, left=-b, height=0.9, color=BAND, lw=0, zorder=1)
    ax.axvline(0, color="#9AA2AA", lw=0.9, zorder=2)

    for y, p in rows:
        if na_of is not None and na_of(p):
            ax.text(0, y, "  n/a", ha="left", va="center", fontsize=8.0,
                    color=MUTED, style="italic", zorder=5)
            continue
        v = value_of(p)
        if v is None:
            continue
        ax.barh(y, v, height=0.56, color=VERM if outside_of(p) else SLATE,
                lw=0, zorder=4)

    ax.set_xlim(lo, hi)
    ax.set_title(title, fontsize=11.6, pad=21, color=INK)
    ax.text(0.5, 1.010, sub, transform=ax.transAxes, ha="center", va="bottom",
            fontsize=8.6, color=MUTED)
    ax.set_xlabel(xlabel, fontsize=9.6, labelpad=6)
    ax.tick_params(labelsize=8.8)
    ax.grid(axis="x", color="#EDEFF2", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)


def main():
    d, nb, groups = load()
    rows, heads, span = place(groups)
    band_by_el = {float(k): v for k, v in nb["grid_dispersion_ac_db_by_el"].items()}
    rhy_band = d["pairs"][0]["grid_band_rhythm_pp"]
    comb_band = d["pairs"][0]["grid_band_comb_db"]
    #: ⭐빗살 대비 밴드도 **앙각마다 다르다**(2026-08-16 적대검산). 전에는 전역 하한 4.04 dB
    #   하나로 그렸는데, 그 값은 정면(0°)을 뺀 빗각의 계단이라 정면 줄이 실제보다 안전해 보였다.
    #   정면의 밴드는 0.1 dB 다 — 그 줄의 +2.27 dB 는 밴드 **밖**이고, 그런데도 읽기가 안 바뀌는
    #   이유는 «양쪽 다 백색 널 자리» 라는 별개의 사실이다. 그 사실을 직접 적는다.
    comb_band_by_el = {float(k): v for k, v in nb["grid_dispersion_comb_db_by_el"].items()}
    null_pct = sum(p["rhythm_null_pct"] for p in d["pairs"]) / len(d["pairs"])

    fig = plt.figure(figsize=(19.6, 13.6), dpi=150)
    fig.patch.set_facecolor("white")

    gs_top = fig.add_gridspec(1, 4, left=0.205, right=0.988, top=0.876, bottom=0.352,
                              width_ratios=[1.62, 1.00, 1.00, 0.70], wspace=0.085)
    ax_lvl, ax_rhy, ax_comb, ax_np = [fig.add_subplot(gs_top[0, i]) for i in range(4)]

    # ── ① 레벨 — 밴드가 줄마다 다른 유일한 판 ─────────────────────────────
    LVL_LIM = 2.95
    bar_panel(
        ax_lvl, rows,
        value_of=lambda p: headline(p, "d_moving_power_db"),
        band_of=lambda p: band_by_el[p["el_deg"]],
        outside_of=lambda p: p["level_outside_band"],
        xlim=(-LVL_LIM, LVL_LIM),
        title="Moving power  ·  depth 3 minus depth 1",
        sub="the only column whose band is measured per elevation",
        xlabel="difference in moving power (stationary part removed)   [dB]")
    # 밴드가 판보다 넓은 줄만 골라 값을 적는다(선택적 직접 라벨)
    for y, p in rows:
        b = band_by_el[p["el_deg"]]
        if b > LVL_LIM:
            ax_lvl.text(LVL_LIM - 0.09, y, f"band ±{b:.2f} dB", ha="right",
                        va="center", fontsize=7.6, color="#7C858E", zorder=6)

    # ── ② 리듬 몫 ─────────────────────────────────────────────────────────
    bar_panel(
        ax_rhy, rows,
        value_of=lambda p: headline(p, "d_rhythm_pp"),
        band_of=lambda p: rhy_band,
        outside_of=lambda p: p["rhythm_outside_band"],
        xlim=(-1.05, 1.05),
        title="Rhythm share  ·  the reading itself",
        sub=f"band ±{rhy_band:.1f} %p — wider than this whole panel",
        xlabel="difference in rhythm share   [%p]")
    ax_rhy.set_xticks([-1.0, -0.5, 0.0, 0.5, 1.0])

    # ⭐−60° 는 생값이 −54.25 %p 였다 — 판 밖이라 묶음 사이 빈 자리에 직접 적는다.
    #   R13(08-15)이 «깊이 축 종결 불가» 의 근거로 쓴 바로 그 수이고, 08-16 에 철회됐다.
    gap_y = heads[1][2] - 1.00                      # B 묶음 머리 바로 위 빈 줄
    for y, p in rows:
        if p["outlier_driven"]:
            ax_rhy.annotate(
                "raw was −54.3 %p here\none pose out of 8,192",
                xy=(-0.36, y), xytext=(-0.52, gap_y),
                fontsize=8.4, color=VERM, ha="center", va="center", zorder=7,
                linespacing=1.45,
                arrowprops=dict(arrowstyle="-|>", color=VERM, lw=1.1,
                                shrinkA=4, shrinkB=3,
                                connectionstyle="arc3,rad=0.20"))

    # ── ③ 빗살 대비 ───────────────────────────────────────────────────────
    bar_panel(
        ax_comb, rows,
        value_of=lambda p: headline(p, "d_comb_contrast_db"),
        band_of=lambda p: comb_band_by_el.get(p["el_deg"]) or 0.0,
        outside_of=lambda p: p["comb_outside_band_by_el"],
        xlim=(-2.6, 2.6),
        title="Comb contrast  ·  the blade lines",
        sub="band per elevation too — 0.1 dB head-on, 4.0–4.6 oblique",
        xlabel="difference in comb contrast   [dB]",
        na_of=lambda p: headline(p, "d_comb_contrast_db") is None)
    # ⭐밴드 밖인데도 읽기가 안 바뀌는 줄 — 그 이유를 그림 안에 직접 적는다
    for y, p in rows:
        if p.get("comb_outside_band_by_el") and p.get("both_sides_at_comb_null"):
            ax_comb.annotate(
                "outside the band, yet both\nsides sit at the white null —\n"
                "no comb either way",
                xy=(headline(p, "d_comb_contrast_db"), y), xytext=(-1.45, y + 3.30),
                fontsize=8.2, color=VERM, ha="center", va="center", zorder=7,
                linespacing=1.45,
                arrowprops=dict(arrowstyle="-|>", color=VERM, lw=1.0,
                                shrinkA=4, shrinkB=4,
                                connectionstyle="arc3,rad=0.24"))
            break

    # ── ④ 경로 수 — 깊이 3 이 실제로 더 찾나 ──────────────────────────────
    for y, p in rows:
        r = p["npaths_ratio"]
        ax_np.barh(y, r - 1.0, left=1.0, height=0.56, color=SLATE, lw=0, zorder=4)
        if r == 1.0:
            ax_np.text(1.004, y, f"{p['npaths_d1']}→{p['npaths_dN']}", ha="left",
                       va="center", fontsize=7.6, color=MUTED, zorder=5)
    ax_np.axvline(1.0, color="#9AA2AA", lw=0.9, zorder=2)
    ax_np.set_xlim(0.994, 1.168)
    ax_np.set_xticks([1.00, 1.05, 1.10, 1.15])
    ax_np.set_xticklabels(["1.00", "1.05", "1.10", "1.15"])
    ax_np.set_title("Paths found", fontsize=11.6, pad=21, color=INK)
    ax_np.text(0.5, 1.008, "depth 3 ÷ depth 1", transform=ax_np.transAxes,
               ha="center", va="bottom", fontsize=8.6, color=MUTED)
    ax_np.set_xlabel("ratio   [×]", fontsize=9.6, labelpad=6)
    ax_np.tick_params(labelsize=8.8)
    ax_np.grid(axis="x", color="#EDEFF2", lw=0.7, zorder=0)
    ax_np.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax_np.spines[s].set_visible(False)

    # ── 줄 이름 · 묶음 머리 ───────────────────────────────────────────────
    for ax in (ax_lvl, ax_rhy, ax_comb, ax_np):
        ax.set_ylim(span + 0.35, -1.75)
        ax.set_yticks([y for y, _ in rows])
        ax.set_yticklabels([])
        ax.tick_params(axis="y", length=0, pad=6)
    ax_lvl.set_yticklabels([row_label(p) for _, p in rows], fontsize=8.7, color=INK)

    tr = ax_lvl.get_yaxis_transform()
    for tag, title, y0 in heads:
        ax_lvl.text(-0.328, y0 - 0.92, f"{tag} · {title}", transform=tr,
                    ha="left", va="center", fontsize=10.4, color=INK,
                    fontweight="bold", clip_on=False)
        ax_lvl.plot([-0.330, 1.0], [y0 - 0.55, y0 - 0.55], transform=tr,
                    color="#DCE0E5", lw=0.9, clip_on=False, zorder=0)

    # ── 범례 (그린 것과 1:1) ──────────────────────────────────────────────
    fig.legend(
        handles=[
            Patch(fc=BAND, ec="none",
                  label="grid dispersion band — a difference inside it is NOT a verdict"),
            Patch(fc=SLATE, ec="none", label="difference inside the band"),
            Patch(fc=VERM, ec="none", label="difference outside the band"),
        ],
        loc="upper center", bbox_to_anchor=(0.596, 0.312), ncol=3,
        frameon=False, fontsize=10.2, handlelength=1.5, columnspacing=2.6,
        handleheight=0.95)

    # ═══════════════════════════════════════════════════════════════════ #
    #  아랫줄 — 밴드 자체 · 얹힌 항 · 튕김 사다리
    # ═══════════════════════════════════════════════════════════════════ #
    gs_bot = fig.add_gridspec(1, 3, left=0.058, right=0.988, top=0.243, bottom=0.098,
                              width_ratios=[1.00, 1.30, 0.82], wspace=0.235)
    ax_band, ax_add, ax_lad = [fig.add_subplot(gs_bot[0, i]) for i in range(3)]

    # ── Q1 · 밴드는 하나의 수가 아니다 ────────────────────────────────────
    els = sorted(band_by_el, reverse=True)
    vals = [band_by_el[e] for e in els]
    ax_band.bar(range(len(els)), vals, color=BAND, edgecolor="#9AA2AA", lw=0.8,
                width=0.66, zorder=3)
    ax_band.set_yscale("log")
    ax_band.set_ylim(0.012, 11)
    ax_band.set_xticks(range(len(els)))
    ax_band.set_xticklabels([deg(e) for e in els], fontsize=9.2)
    for i, v in enumerate(vals):
        ax_band.text(i, v * 1.22, f"{v:.2f}", ha="center", va="bottom",
                     fontsize=8.6, color=INK, zorder=4)
    ax_band.set_title("The band is not one number", fontsize=11.6, pad=19, color=INK)
    ax_band.text(0.5, 1.010,
                 "wide head-on and straight below · far tighter at oblique angles",
                 transform=ax_band.transAxes, ha="center", va="bottom",
                 fontsize=8.6, color=MUTED)
    ax_band.set_ylabel("band half-width   [dB]", fontsize=9.4)
    ax_band.set_xlabel("elevation", fontsize=9.4, labelpad=4)
    ax_band.tick_params(labelsize=8.6)
    ax_band.grid(axis="y", color="#EDEFF2", lw=0.7, zorder=0)
    ax_band.set_axisbelow(True)
    for s in ("top", "right"):
        ax_band.spines[s].set_visible(False)

    # ── Q2 · 깊이가 얹는 항의 성격 ────────────────────────────────────────
    #   ⭐깃발 달린 칸(정면 0° 익사 · 직하방 −90° 상한 퇴화)은 속 빈 표식으로 갈라 그린다.
    p13 = [p for p in d["pairs"] if p["depths"] == [1, 3]]

    def flagged(p):
        return ("tip_ceiling_degenerate" in p["flags_d1"] + p["flags_dN"]
                or p["el_deg"] == 0.0)

    for on in (False, True):
        col = VERM if on else BLUE
        sel = [p for p in p13 if p["switches"]["D"] is on]
        solid = [p for p in sel if not flagged(p)]
        hollow = [p for p in sel if flagged(p)]
        ax_add.scatter([headline(p, "residual_over_d1_db") for p in solid],
                       [headline(p, "residual_rhythm_pct") for p in solid],
                       s=80, c=col, edgecolors="white", linewidths=1.4, zorder=4,
                       label="diffraction off" if not on else "diffraction on")
        if hollow:
            ax_add.scatter([headline(p, "residual_over_d1_db") for p in hollow],
                           [headline(p, "residual_rhythm_pct") for p in hollow],
                           s=80, facecolors="white", edgecolors=col, linewidths=1.8,
                           zorder=5,
                           label="† cell carries a ledger flag" if not on else None)
    ax_add.axhline(null_pct, color=MUTED, lw=1.0, ls=(0, (5, 3)), zorder=2)
    ax_add.text(-30.0, null_pct - 3.2,
                f"white null {null_pct:.1f} %  —  no blade beat at all",
                fontsize=8.8, color=MUTED, ha="left", va="top")
    ax_add.set_xlim(-30.8, 0.6)
    ax_add.set_ylim(0, 100)
    ax_add.set_title("What the extra bounces actually add", fontsize=11.6, pad=19,
                     color=INK)
    ax_add.text(0.5, 1.010, "the 15 depth 1 → 3 pairs",
                transform=ax_add.transAxes, ha="center", va="bottom",
                fontsize=8.6, color=MUTED)
    ax_add.set_xlabel("size of the added term   [dB relative to depth 1]",
                      fontsize=9.4, labelpad=4)
    ax_add.set_ylabel("rhythm share of the added term   [%]", fontsize=9.4)
    ax_add.tick_params(labelsize=8.6)
    ax_add.grid(color="#EDEFF2", lw=0.7, zorder=0)
    ax_add.set_axisbelow(True)
    for s in ("top", "right"):
        ax_add.spines[s].set_visible(False)
    ax_add.legend(
        handles=[
            Line2D([], [], ls="none", marker="o", ms=8.6, mfc=BLUE, mec="white",
                   mew=1.4, label="diffraction off"),
            Line2D([], [], ls="none", marker="o", ms=8.6, mfc=VERM, mec="white",
                   mew=1.4, label="diffraction on"),
            Line2D([], [], ls="none", marker="o", ms=8.6, mfc="white", mec=BLUE,
                   mew=1.8, label="† cell carries a ledger flag"),
        ],
        loc="upper right", frameon=False, fontsize=9.2,
        handletextpad=0.5, borderpad=0.2, labelspacing=0.55)
    ax_add.text(-24.6, 42.0,
                "small and beating —\na real second-bounce target echo",
                fontsize=8.8, color=BLUE, ha="center", va="center", linespacing=1.5)
    # ⚠«회절 항이 한 번 더 실렸다» 는 이 그림이 못 세우는 주장이다(2026-08-16 적대검산):
    #   그 팔은 깊이 1 판부터 이미 백색이라 얹힌 항이 백색인 것이 새 정보가 아니다.
    ax_add.text(-11.0, 26.0,
                "big but structureless — though this arm\nis already white at depth 1, "
                "so this says little",
                fontsize=8.8, color=VERM, ha="center", va="center", linespacing=1.5)

    # ── Q3 · 튕김 사다리 ──────────────────────────────────────────────────
    lad = d["bounce_ladder"]
    r = lad["power_ratio_to_d1"]
    ceil2 = r[1] + (r[1] - r[0])          # 줄어드는 급수라면 여기서 멈춘다
    ax_lad.bar([0, 1, 2], r, width=0.54, color=BLUE, lw=0, zorder=4)
    ax_lad.plot([1.58, 2.42], [ceil2, ceil2], color=MUTED, lw=1.5,
                ls=(0, (5, 3)), zorder=6)
    ax_lad.text(2.52, ceil2, "ceiling if the\nseries were decaying", ha="left",
                va="center", fontsize=8.5, color=MUTED, linespacing=1.5, zorder=6)
    for i, v in enumerate(r):
        ax_lad.text(i, v + 0.04, f"{v:.3f}", ha="center", va="bottom",
                    fontsize=8.8, color=INK, zorder=5)
    ax_lad.set_xticks([0, 1, 2])
    ax_lad.set_xticklabels(["depth 1", "depth 2", "depth 3"], fontsize=9.2)
    ax_lad.set_xlim(-0.62, 3.55)
    ax_lad.set_ylim(0, 1.95)
    ax_lad.set_title("Bounce ladder — one cell", fontsize=11.6, pad=19, color=INK)
    ax_lad.text(0.5, 1.010,
                f"the 3rd bounce adds {lad['third_over_second']:.1f}× "
                f"what the 2nd added",
                transform=ax_lad.transAxes, ha="center", va="bottom",
                fontsize=8.6, color=MUTED)
    ax_lad.set_ylabel("moving power relative to depth 1   [×]", fontsize=9.4)
    ax_lad.tick_params(labelsize=8.6)
    ax_lad.grid(axis="y", color="#EDEFF2", lw=0.7, zorder=0)
    ax_lad.set_axisbelow(True)
    for s in ("top", "right"):
        ax_lad.spines[s].set_visible(False)
    ax_lad.text(0.5, -0.185, f"all four switches on · {deg(lad['el_deg'])} · "
                             f"{rng(lad['range_m'])}\n"
                             "depth 3 is a separately named run\n"
                             "(two names differ by 0.07 dB, not 2.2)",
                transform=ax_lad.transAxes, ha="center", va="top",
                fontsize=8.2, color=MUTED, linespacing=1.5)

    # ═══════════════════════════════════════════════════════════════════ #
    #  제목 · 캡션
    # ═══════════════════════════════════════════════════════════════════ #
    fig.text(0.5, 0.972,
             "Does letting rays bounce three times change what we read?",
             ha="center", va="top", fontsize=19, color=INK, fontweight="bold")
    fig.text(0.5, 0.938,
             "every depth pair in the ledger — 22 pairs — each against the band "
             "that decides whether its difference means anything",
             ha="center", va="top", fontsize=11.6, color=MUTED)

    fig.text(0.5, 0.0345,
             "All levels measured after the stationary part is removed.   "
             "Bars are the ledger headline — the single most extreme pose trimmed; "
             "the one place the raw value differs is called out.\n"
             "R = specular refraction · D = diffraction · E = edge diffraction · "
             "F = diffuse reflection;   1 = on, 0 = off.   "
             "† the cell carries a ledger flag — head-on already sits at the null and "
             "straight-below has no blade-tip ceiling, so those rows are evidence "
             "for neither side.",
             ha="center", va="center", fontsize=8.9, color=MUTED, linespacing=1.7)
    fig.text(0.5, 0.0075,
             "⚠ The band was measured on OUR kernel's grid axis (SBR+PO) and is "
             "borrowed here — these are all PathSolver arms, and PathSolver's own "
             "depth-3 spread has never been measured.      "
             "Source: outputs/depth_axis_verdict_0816.json",
             ha="center", va="center", fontsize=8.4, color="#8A9198")

    fig.savefig(OUT, facecolor="white")
    print(f"  ✅ {os.path.relpath(OUT, ROOT)}")
    print(f"     짝 {len(rows)} 개 · 묶음 {len(heads)} 개")
    n_out = sum(1 for _, p in rows if p["level_outside_band"])
    print(f"     레벨 밴드 밖 {n_out} 줄 · 리듬/빗살 밴드 밖(전역) "
          f"{sum(1 for _, p in rows if p['rhythm_outside_band'] or p['comb_outside_band'])} 줄"
          f" · 빗살 밴드 밖(앙각별) "
          f"{sum(1 for _, p in rows if p['comb_outside_band_by_el'])} 줄")
    print(f"     판독을 바꾼 줄 — 전역 밴드 "
          f"{sum(1 for _, p in rows if p['moves_the_reading'])} 개 · 앙각별 밴드 "
          f"{sum(1 for _, p in rows if p['moves_the_reading_by_el_band'])} 개"
          f"(둘 다 백색 널 자리라 읽기는 불변)")


if __name__ == "__main__":
    main()
