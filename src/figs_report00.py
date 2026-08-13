# -*- coding: utf-8 -*-
"""
figs_report00.py — 리포트 00(가르치는 편)의 그림 4장을 **게재 품질로** 그린다
============================================================================================
계약: `docs/PAPER_SPEC.md` §4.3 — 벡터(PDF) + 400 dpi PNG 동시 저장 · 글자 9 pt · 2단(7.16 in)
배치 뒤에도 8 pt 이상 · **색 + 해치/마커 이중부호화**. 강제는 `src/paper_kit.py` 의 `save_figure()`
가 한다 — 규격을 어기면 저장 전에 예외가 나고, 통과한 감사 결과는 PDF 메타데이터에 심겨
`check_figure()` 로 다시 확인된다.

⚠ 이 파일의 모든 글자는 **9 pt 한 종류**다. 조판 축소(tight bbox 가 7.16 in 을 넘으면 축소된다)를
   견디려면 여백이 필요해서다. 그래서 각 줄은 짧게 끊는다 — 반쪽 패널에서 한 줄 약 45자가 상한이다.

그리는 것 (수치는 전부 JSON 에서 읽는다. 이 파일에서 새로 계산하는 물리량은 없다)
    F1 두 계산의 갈림   ⟨report00_sionna_anatomy: item1·item2·item6⟩
                        + ⟨report00_sionna_probe: exp_a_ray_count_sweep·summary⟩
                        + ⟨report00_po_case: s2_our_kernel.production_settings.div⟩
    F2 크기가 안 들어간다 ⭐헤드라인
                        ⟨report00_evidence: A_plate_size_sweep.numbers⟩
    F3 같은 재질, 다른 모양
                        ⟨report00_evidence: C_same_material_different_shape.numbers⟩
    F4 할 수 있는 것 / 없는 것
                        ⟨report00_decision_map: axes·zones·items⟩

⭐ 공정성 — 이 4장은 Sionna 를 깎지 않는다
    F1 왼쪽의 중복 제거는 버그가 아니라 설계다 — 광선을 400배 늘려도 답이 0.0 dB 안 움직인다.
    F2 오른쪽은 RT 진폭이 이미지-소스 해석해와 0.0017 dB 안에서 맞는다는 것을 같이 그린다.
       엔진은 자기가 푸는 문제를 정확히 푼다. 다만 그 값은 표적의 되쏨이 아니다.
    F4 오른쪽 두 칸에서 Sionna 는 맞는 도구이고, 그 칸에 정확도 숫자를 적는다.
    틀린 것은 '도구가 부실하다' 가 아니라 '전파용 도구에 표적 산란을 시켰다' 이다.

그림 안의 글자는 전부 영어다(하우스 규약). 본문·주석·print 는 한국어다.

실행
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/figs_report00.py
"""
from __future__ import annotations

import json
import os
import sys
import textwrap

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np                                                      # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle                # noqa: E402

from paper_kit import PALETTE, check_figure, paper_style, save_figure   # noqa: E402

FIGDIR = "outputs/figures"
PLACED_IN = 7.16                       # IEEE 2단 폭. 저장본은 이 폭에 놓인다고 보고 검사한다.
PT = 9.0                               # ⭐ 그림 안 글자는 전부 이 크기다.
#: 눈금·범례 기본값은 본문보다 1 pt 작다(paper_rc). 이 편은 **전부 9 pt** 로 맞춘다 —
#  tight bbox 가 7.16 in 을 살짝 넘어 축소가 걸려도 8 pt 하한 위에 남게 하려는 것이다.
TICKS_9PT = {"xtick.labelsize": PT, "ytick.labelsize": PT, "legend.fontsize": PT}

SRC = {
    "evidence": "outputs/report00_evidence.json",
    "anatomy": "outputs/report00_sionna_anatomy.json",
    "probe": "outputs/report00_sionna_probe.json",
    "po_case": "outputs/report00_po_case.json",
    "decision": "outputs/report00_decision_map.json",
}

#: 계열 색 — 색 + 해치/마커/선종으로 항상 이중부호화한다.
C_PO, C_RT, C_REF, C_GREY = PALETTE[0], PALETTE[1], PALETTE[6], "#8A8A8A"

#: 논문에 그대로 붙일 캡션(완결 문장). 노트북 캡션(질문)은 빌더가 따로 단다.
CAPTIONS = {
    "f1": ("The two computations share one ray engine and part company at the surface: the path "
           "solver keeps a single representative of each specular chain and updates the field with "
           "a local plane-boundary matrix, while the physical-optics integral keeps every lit hit "
           "and sums its phase over the illuminated area."),
    # ⭐ 캡션의 숫자도 손으로 치지 않는다 — {} 자리에 JSON 값이 들어간다(아래 fig 함수가 채운다).
    "f2": ("Growing a metal plate from {side_lo:g} m to {side_hi:g} m raises the physical-optics "
           "radar cross section by {span_po:.1f} dB while the ray-traced target path stays at one "
           "path and one amplitude; that amplitude tracks the image-source mirror field to "
           "{dev_img:.4f} dB, so the solver is exact at what it solves and simply carries no "
           "target size."),
    "f3": ("A PEC sphere and a PEC flat plate of the same frontal area at the same frequency "
           "differ by {gap:.1f} dB in radar cross section, and only the plate grows with "
           "frequency, because the reflection coefficient is shared while the phase summation "
           "over the lit surface is not."),
    "f4": ("Where each experiment falls once the two questions are asked: when the target term "
           "cancels the ray engine is the whole answer and is exact in absolute terms, and only "
           "the left half needs a scattering integral, with the upper-left cell additionally "
           "needing a measurement anchor."),
}


def _load() -> dict:
    bag = {}
    for k, rel in SRC.items():
        p = os.path.join(_ROOT, rel)
        if not os.path.exists(p):
            raise SystemExit(
                f"근거 JSON 이 없다: {rel}\n  → F4 근거는 "
                "`PYTHONPATH=src python benchmark/build_report00_decision_map.py` 로 만든다.")
        with open(p, encoding="utf-8") as f:
            bag[k] = json.load(f)
    return bag


def _short(loc: str) -> str:
    """'path_solvers/sb_candidate_generator.py:484-498' → 'sb_candidate_generator.py:484-498'."""
    return loc.split("/")[-1]


def _pick(locs, needle: str) -> str:
    for s in locs:
        if needle in s:
            return _short(s)
    return _short(locs[0])


def _box(ax, x, y, lines, *, fc="#F4F4F4", ec="#BBBBBB", ha="left", va="center"):
    """주석 상자 하나. 상자는 patch 라 감사 대상이 아니고, 글자만 감사된다(9 pt 고정)."""
    ax.text(x, y, "\n".join(lines), fontsize=PT, ha=ha, va=va, linespacing=1.32,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=fc, edgecolor=ec, linewidth=0.6),
            zorder=6)


def _report(out: dict) -> None:
    c = out["check"]
    print(f"  {out['pdf']} · page {c['page_size_in'][0]:.2f} in · 최소 글자 {c['min_font_pt']} pt "
          f"→ 배치 {PLACED_IN} in 에서 {c['effective_min_font_pt']} pt · PNG {c['png_dpi']} dpi · "
          f"색만 구분 {len(c['colour_only_series'])}건 · "
          f"{'통과' if c['ok'] else '위반 ' + str(c['violations'])}")


# =========================================================================== #
# F1 — 두 계산이 갈리는 지점
# =========================================================================== #
def fig1_divergence(B):
    A = B["anatomy"]
    P = B["probe"]
    dedup_loc = _pick(A["item1_ray_shooting_and_dedup"]["b_dedup_point"]["where"], "484-498")
    field_loc = _pick(A["item2_field_calculation_arguments"]["where"], "853-863")
    args = list(A["item2_field_calculation_arguments"]["argument_inventory"].keys())
    spp = [r["samples_per_src"] for r in P["exp_a_ray_count_sweep"]]
    span_rays = P["summary"]["ray_count_span"]
    spread_rays_db = P["summary"]["abs_a_spread_over_ray_count_db"]
    n_paths = int(P["exp_a_ray_count_sweep"][0]["num_paths"])
    div = B["po_case"]["s2_our_kernel"]["production_settings"]["div"]
    eng = A["item6_versions"]["values"]

    # 세로 배치는 두 패널이 **똑같다** — 기하 / 한 줄 판정 / 설명상자 / 수식상자.
    Y_TX, Y_PLATE, Y_STATUS, Y_NOTE, Y_MATH = 9.3, 5.30, 4.72, 3.65, -1.75

    with paper_style(width="double", base_pt=PT) as st:
        fig, (axL, axR) = st.figure(1, 2, height=5.0)
        fig.suptitle(f"One ray engine (Mitsuba {eng['mitsuba']}, Dr.Jit {eng['drjit']}) "
                     "shoots rays and finds triangle hits", fontsize=PT)

        for ax in (axL, axR):
            ax.set_xlim(0, 10)
            ax.set_ylim(-8.1, 10.3)
            ax.axis("off")
            ax.add_patch(Rectangle((2.0, Y_PLATE - 0.30), 6.0, 0.30, facecolor="#DDDDDD",
                                   edgecolor="#555555", hatch="///", linewidth=0.8, zorder=3))

        # ── (a) Sionna path solver — 여러 광선이 경로 하나로 합쳐진다 ──────────
        axL.set_title("(a)  Path solver: rays are scouts", fontsize=PT, pad=5)
        tx, rx = (1.0, Y_TX), (9.0, Y_TX)
        hits = np.array([3.0, 4.0, 5.0, 6.0, 7.0])
        for h in hits:
            axL.plot([tx[0], h], [tx[1], Y_PLATE], color=C_GREY, lw=0.7, ls=(0, (2, 1.6)),
                     marker="", alpha=0.9, zorder=2)
        axL.plot(hits[hits != 5.0], [Y_PLATE] * 4, color=C_GREY, lw=0, marker="x",
                 markersize=5.5, markeredgewidth=1.1, zorder=4)
        axL.plot([tx[0], 5.0, rx[0]], [tx[1], Y_PLATE, rx[1]], color=C_PO, lw=2.0, ls="-",
                 marker="", zorder=5)
        axL.plot([5.0], [Y_PLATE], color=C_PO, lw=0, marker="o", markersize=6.5, zorder=6)
        axL.plot([tx[0]], [tx[1]], color="#222222", lw=0, marker="^", markersize=6.5, zorder=6)
        axL.plot([rx[0]], [rx[1]], color="#222222", lw=0, marker="v", markersize=6.5, zorder=6)
        axL.text(tx[0], tx[1] + 0.55, "TX", fontsize=PT, ha="center", va="bottom")
        axL.text(rx[0], rx[1] + 0.55, "RX", fontsize=PT, ha="center", va="bottom")
        axL.text(5.0, Y_STATUS, f"paths to the target: {n_paths}", fontsize=PT, ha="center",
                 va="top", color="#333333")
        _box(axL, 5.0, Y_NOTE, [f"N probe rays on a quasi-uniform lattice",
                                f"N: {spp[0]:.0e} to {spp[-1]:.0e} ({span_rays:.0f}x),"
                                f" amplitude spread {spread_rays_db:.1f} dB",
                                "all of them report one surface sequence,",
                                "so the first is kept and the rest discarded",
                                "the image method then places the exact point",
                                dedup_loc],
             ha="center", va="top", fc="#FBF3E7", ec="#D9BE95")
        _box(axL, 5.0, Y_MATH, ["field update at that one point",
                                "a = pattern x Fresnel Jones",
                                "        x 1/(s' + s) x lambda/4pi",
                                f"args: {', '.join(args[:3])},",
                                f"    {', '.join(args[3:])}",
                                "no area, no curvature, no triangle size",
                                field_loc],
             ha="center", va="top", fc="#EAF2F8", ec="#9CBBD3")

        # ── (b) 우리 PO 면적분 — 맞은 점을 전부 더한다 ─────────────────────────
        axR.set_title("(b)  PO integral: hits are the answer", fontsize=PT, pad=5)
        grid = np.linspace(2.45, 7.55, 11)
        for g in grid:
            axR.annotate("", xy=(g, Y_PLATE + 0.06), xytext=(g, Y_TX - 0.7),
                         arrowprops=dict(arrowstyle="-|>", color=C_RT, lw=1.0, mutation_scale=7))
        axR.plot(grid, [Y_PLATE] * len(grid), color=C_RT, lw=0, marker="o", markersize=3.6,
                 zorder=5)
        axR.annotate("", xy=(grid[0], Y_TX - 0.55), xytext=(grid[1], Y_TX - 0.55),
                     arrowprops=dict(arrowstyle="<->", color="#333333", lw=0.8, mutation_scale=7))
        axR.text(0.5 * (grid[0] + grid[1]), Y_TX - 0.45, "d", fontsize=PT, ha="center",
                 va="bottom")
        axR.text(5.0, Y_STATUS, "contributions: one per lit hit", fontsize=PT, ha="center",
                 va="top", color="#333333")
        _box(axR, 5.0, Y_NOTE, ["parallel rays on a uniform grid",
                                "over the aperture seen by the radar",
                                f"grid spacing d = lambda / {div} in production,",
                                "so one ray stands for the area d^2",
                                "the hit point and its phase are both kept",
                                "src/rcs_sbr.py"],
             ha="center", va="top", fc="#FBF3E7", ec="#D9BE95")
        _box(axR, 5.0, Y_MATH, ["coherent sum over every lit point",
                                "E = SUM |Gamma_i|",
                                "        x exp(j 2k p_i . u) x d^2",
                                "sigma = (4 pi / lambda^2) |E|^2",
                                "more lit area means more terms",
                                "self-shadowing is free: first hits only",
                                "size enters here, and only here"],
             ha="center", va="top", fc="#EAF6F0", ec="#93C6B2")

    out = save_figure(fig, f"{FIGDIR}/report00_f1", caption=CAPTIONS["f1"],
                      title="Where the two computations diverge",
                      placed_width_in=PLACED_IN, close=True)
    return out


# =========================================================================== #
# F2 — 크기가 안 들어간다 (헤드라인)
# =========================================================================== #
def fig2_size_does_not_enter(B):
    N = B["evidence"]["A_plate_size_sweep"]["numbers"]
    side = np.array(N["side_m"], float)
    sig = np.array(N["sigma_po_dbsm"], float)
    amp_po = np.array(N["amp_po_db"], float)
    rt = float(N["rt_coh_db_value"])
    img = float(N["image_source_theory_db"])
    npaths = float(N["n_paths_target_set_union"][0])
    slope = float(N["slope_sigma_db_per_area_db"])
    span_po = float(N["po_theory_span_db"])
    span_rt = float(N["rt_span_db"])
    ratio = float(N["size_ratio_max"])
    aratio = float(N["area_ratio_max"])
    cross = float(N["side_m_where_rt_equals_po"])
    dev_img = float(N["rt_minus_image_source_max_abs_db"])
    ncells = int(N["n_cells"])
    nseeds = int(N["n_seeds"])
    spp = N["spp_list"]
    dep = N["max_depth_tested"]

    with paper_style(width="double", base_pt=PT, **TICKS_9PT) as st:
        fig, (ax1, ax2) = st.figure(1, 2, height=3.5)

        # ── (a) 크기가 커지면 sigma 는 오르고 경로 수는 그대로다 ────────────────
        ax1.plot(side, sig, label="PO cross section", **st.series(0))
        ax1.set_xscale("log")
        ax1.set_xlabel("Metal plate side [m]")
        ax1.set_ylabel("PO radar cross section [dBsm]")
        ax1.set_xticks(side)
        ax1.set_xticklabels([f"{s:g}" for s in side])
        ax1.set_ylim(sig.min() - 14, sig.max() + 22)
        ax1.annotate("", xy=(side[-1], sig[-1]), xytext=(side[-1], sig[0]),
                     arrowprops=dict(arrowstyle="<->", color=C_PO, lw=0.9, mutation_scale=8))
        # 대각선 곡선이 패널을 가로지르므로, 화살표 옆에 **세로로** 세운다.
        ax1.text(side[-1] * 0.86, 20.0,
                 f"{span_po:.1f} dB over {ratio:.0f}x size\n({aratio:.0f}x area)",
                 fontsize=PT, rotation=90, ha="center", va="center", color=C_PO)
        ax1.text(side[0], sig.max() + 20,
                 f"slope {slope:.2f} dB per dB of area:\nthe cross section follows area squared",
                 fontsize=PT, ha="left", va="top")
        ax1.set_title("(a)  Size moves sigma, not the paths", fontsize=PT)

        axb = ax1.twinx()
        axb.plot(side, np.full_like(side, npaths), label="Ray-traced paths", **st.series(1))
        axb.set_ylabel("Paths to the target")
        axb.set_ylim(0, 2.6)
        axb.set_yticks([0, 1, 2])
        axb.grid(False)
        # 오른쪽 축 좌표로 **빈 곳(오른쪽 아래)** 에 놓는다 — 대각선 sigma 곡선을 피한다.
        axb.text(side[-1] * 0.93, 0.06,
                 f"flat at {npaths:.1f} in all {ncells} cells\n"
                 f"spp {spp[0]:.0e} to {spp[-1]:.0e}, {nseeds} seeds,\ndepth {dep[0]} to {dep[-1]}",
                 fontsize=PT, ha="right", va="bottom", color=C_RT)
        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = axb.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, loc="upper left", bbox_to_anchor=(0.02, 0.84),
                   fontsize=PT)

        # ── (b) 같은 단위로 겹쳐 본다 — 진폭 ────────────────────────────────
        ax2.plot(side, amp_po, label="PO, target this size", **st.series(0))
        ax2.plot(side, np.full_like(side, rt), label="Sionna RT path", **st.series(1))
        ax2.plot(side, np.full_like(side, img), color=C_REF, ls=(0, (5, 2)), marker="", lw=1.1,
                 label="Image source (analytic)")
        ax2.set_xscale("log")
        ax2.set_xlabel("Metal plate side [m]")
        ax2.set_ylabel("Received echo amplitude [dB]")
        ax2.set_xticks(side)
        ax2.set_xticklabels([f"{s:g}" for s in side])
        ax2.set_ylim(amp_po.min() - 12, amp_po.max() + 34)
        ax2.axvline(cross, color="#777777", lw=0.7, ls=":")
        ax2.text(cross * 0.90, rt + 5.0, f"equal only at\nside {cross:.2f} m",
                 fontsize=PT, ha="right", va="bottom", color="#444444")
        ax2.text(side[0], amp_po.max() + 31,
                 f"RT spread over {ratio:.0f}x size: {span_rt:.1e} dB\n"
                 f"RT minus image source: {dev_img:.4f} dB\n"
                 "exact at what it solves, which\nis propagation, not the target",
                 fontsize=PT, ha="left", va="top")
        ax2.legend(loc="lower right", fontsize=PT)
        ax2.set_title("(b)  A mirror field, not a target echo", fontsize=PT)

    out = save_figure(fig, f"{FIGDIR}/report00_f2",
                      caption=CAPTIONS["f2"].format(side_lo=side[0], side_hi=side[-1],
                                                    span_po=span_po, dev_img=dev_img),
                      title="Target size does not enter the path solver",
                      placed_width_in=PLACED_IN, close=True)
    return out


# =========================================================================== #
# F3 — 같은 재질, 다른 모양
# =========================================================================== #
def fig3_shape(B):
    C = B["evidence"]["C_same_material_different_shape"]["numbers"]
    sph = float(C["sphere_sigma_dbsm"])
    pla = float(C["plate_same_area_sigma_dbsm"])
    gap = float(C["shape_gap_db"])
    area = float(C["frontal_area_m2"])
    r = float(C["sphere_r_m"])
    fc = float(C["fc_hz"]) / 1e9
    lam = float(C["lambda_m"])
    kr = float(C["sphere_kr"])
    d_pla = float(C["plate_sigma_df_db_per_octave"])
    d_sph = float(C["sphere_sigma_df_db_per_octave"])

    with paper_style(width="double", base_pt=PT, **TICKS_9PT) as st:
        fig, (ax1, ax2) = st.figure(1, 2, height=3.5)

        # ── (a) 막대 — 같은 재질·같은 정면면적, 31 dB 차이 ─────────────────────
        ax1.bar([0], [sph], width=0.5, color=PALETTE[2], hatch="", edgecolor="white",
                label=f"PEC sphere, r = {r:.3f} m")
        ax1.bar([1], [pla], width=0.5, color=PALETTE[3], hatch="///", edgecolor="white",
                label="PEC plate, same area")
        ax1.axhline(0.0, color="#666666", lw=0.7)
        ax1.set_xticks([0, 1], ["Sphere", "Flat plate"], fontsize=PT)
        ax1.set_ylabel("Radar cross section [dBsm]")
        ax1.set_ylim(min(sph, 0.0) - 14, pla + 28)
        ax1.set_xlim(-0.62, 1.62)
        ax1.text(0, sph - 1.8, f"{sph:+.2f} dBsm", fontsize=PT, ha="center", va="top")
        ax1.text(1, pla + 1.8, f"{pla:+.2f} dBsm", fontsize=PT, ha="center", va="bottom")
        ax1.annotate("", xy=(0.5, sph), xytext=(0.5, pla),
                     arrowprops=dict(arrowstyle="<->", color="#333333", lw=1.0, mutation_scale=8))
        ax1.text(0.43, 0.5 * (sph + pla), f"{gap:.2f} dB\nfrom shape", fontsize=PT,
                 ha="right", va="center")
        ax1.text(-0.58, pla + 26,
                 f"both PEC, both {area:.4f} m^2 frontal area,\n"
                 f"both at {fc:.1f} GHz (lambda {lam * 100:.2f} cm, kr {kr:.1f})\n"
                 f"double the frequency: plate {d_pla:+.2f} dB per\noctave, "
                 f"sphere {d_sph:+.2f} dB per octave",
                 fontsize=PT, ha="left", va="top")
        ax1.legend(loc="lower right", fontsize=PT)
        ax1.set_title("(a)  Same coefficient, different answer", fontsize=PT)

        # ── (b) 위상 합산 모식도 ────────────────────────────────────────────
        ax2.set_xlim(0, 10)
        ax2.set_ylim(0, 9.6)
        ax2.axis("off")
        ax2.set_title("(b)  Why: how the contributions add", fontsize=PT)

        def chain(x0, y0, phases, color, step):
            """단위 위상자를 꼬리-머리로 이어 붙인다. 사슬의 시작점과 끝점을 돌려준다."""
            x, y = [x0], [y0]
            for ph in phases:
                x.append(x[-1] + step * np.cos(ph))
                y.append(y[-1] + step * np.sin(ph))
            for i in range(len(phases)):
                ax2.annotate("", xy=(x[i + 1], y[i + 1]), xytext=(x[i], y[i]),
                             arrowprops=dict(arrowstyle="-|>", color=color, lw=1.1,
                                             mutation_scale=7, shrinkA=0, shrinkB=0))
            return (x[0], y[0]), (x[-1], y[-1])

        n = 14
        # 평판: 위상이 맞는다 — 사슬이 일직선, 합이 길다
        s0, s1 = chain(1.5, 8.05, np.zeros(n), PALETTE[3], 0.42)
        ax2.annotate("", xy=(s1[0], s1[1] - 0.85), xytext=(s0[0], s0[1] - 0.85),
                     arrowprops=dict(arrowstyle="-|>", color=PALETTE[3], lw=2.2, mutation_scale=9,
                                     shrinkA=0, shrinkB=0))
        ax2.text(0.1, 9.15, "Flat plate: the lit face is co-phased", fontsize=PT, ha="left",
                 va="center")
        ax2.text(s1[0] + 0.25, s1[1] - 0.85, "sum: long", fontsize=PT, ha="left", va="center",
                 color=PALETTE[3])

        # 구: 표면이 휘어 위상이 흩어진다 — 사슬이 말려 합이 짧다
        c0, c1 = chain(2.55, 2.35, np.arange(n) * np.deg2rad(23.0), PALETTE[2], 0.55)
        ax2.annotate("", xy=(c1[0], c1[1]), xytext=(c0[0], c0[1]),
                     arrowprops=dict(arrowstyle="-|>", color=PALETTE[2], lw=2.4, mutation_scale=10,
                                     shrinkA=0, shrinkB=0))
        ax2.annotate("", xy=(0.5 * (c0[0] + c1[0]), 0.5 * (c0[1] + c1[1])), xytext=(5.55, 2.45),
                     arrowprops=dict(arrowstyle="-", color=PALETTE[2], lw=0.7,
                                     shrinkA=2, shrinkB=2))
        ax2.text(0.1, 6.35, "Sphere: the lit cap curves away,", fontsize=PT, ha="left",
                 va="center")
        ax2.text(0.1, 5.85, "so the phase spreads", fontsize=PT, ha="left", va="center")
        ax2.text(5.65, 2.45, "sum: short", fontsize=PT, ha="left", va="center",
                 color=PALETTE[2])
        ax2.add_patch(FancyBboxPatch((0.1, 0.1), 9.7, 1.75, boxstyle="round,pad=0.02",
                                     facecolor="#F4F4F4", edgecolor="#BBBBBB", linewidth=0.6))
        ax2.text(4.95, 0.97,
                 "Schematic: one arrow is one lit patch, its direction\n"
                 "is that patch's phase. Panel (a) is the measurement;\n"
                 "on the sphere only the specular point survives.",
                 fontsize=PT, ha="center", va="center")

    out = save_figure(fig, f"{FIGDIR}/report00_f3", caption=CAPTIONS["f3"].format(gap=gap),
                      title="Same material, different shape",
                      placed_width_in=PLACED_IN, close=True)
    return out


# =========================================================================== #
# F4 — 결정표
# =========================================================================== #
def fig4_decision(B):
    D = B["decision"]
    ax_x, ax_y = D["axes"]["x"], D["axes"]["y"]
    zones = {z["id"]: z for z in D["zones"]}
    by_zone = {zid: [i for i in D["items"] if i["zone"] == zid] for zid in zones}

    #: 칸의 좌하단 좌표는 (x_cancels, y_absolute) 가 정한다. 배치는 판단, 숫자는 JSON.
    corner = {(False, True): (0.0, 0.5), (True, True): (0.5, 0.5),
              (False, False): (0.0, 0.0), (True, False): (0.5, 0.0)}
    face = {"Z1": "#EAF2F8", "Z2": "#EAF2F8", "Z3": "#EAF6F0", "Z4": "#FBF3E7"}
    #: 한 칸의 글상자는 축 폭의 0.46 이다. 9 pt 에서 그 폭에 들어가는 글자 수 — 넘으면 옆 칸을 침범한다.
    WRAP_HEAD, WRAP_SUB, LINE_H = 40, 44, 0.0312
    edge = {"Z1": "#9CBBD3", "Z2": "#9CBBD3", "Z3": "#93C6B2", "Z4": "#D9BE95"}

    with paper_style(width="double", base_pt=PT, **TICKS_9PT) as st:
        fig, ax = st.figure(height=5.9)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_linewidth(0.8)

        for zid, z in zones.items():
            x0, y0 = corner[(z["x_cancels"], z["y_absolute"])]
            ax.add_patch(Rectangle((x0, y0), 0.5, 0.5, facecolor=face[zid], edgecolor="none",
                                   zorder=0))
            ax.text(x0 + 0.25, y0 + 0.462, z["tool_en"], fontsize=PT, ha="center", va="center",
                    fontweight="bold", zorder=3)
            ax.text(x0 + 0.25, y0 + 0.418, z["verdict_en"], fontsize=PT, ha="center", va="center",
                    style="italic", color="#444444", zorder=3)
            top = y0 + 0.386
            for it in by_zone[zid]:
                # 칸 폭에 맞춰 **줄바꿈**한다 — 상자 밖으로 삐져나가면 옆 칸을 침범한다.
                head = textwrap.wrap(it["label_en"], WRAP_HEAD)
                sub = []
                for t in [it["note_en"]] + [b["text_en"] for b in it["badges"]]:
                    sub += textwrap.wrap(t, WRAP_SUB)
                nline = len(head) + len(sub)
                h = 0.016 + LINE_H * nline
                ax.add_patch(FancyBboxPatch((x0 + 0.02, top - h), 0.46, h - 0.008,
                                            boxstyle="round,pad=0.004", facecolor="white",
                                            edgecolor=edge[zid], linewidth=0.7, zorder=1))
                yy = top - 0.011 - LINE_H / 2
                for k, t in enumerate(head + sub):
                    ax.text(x0 + 0.033, yy - LINE_H * k, t, fontsize=PT, ha="left", va="center",
                            color="#111111" if k < len(head) else "#555555", zorder=3)
                top -= h + 0.005

        ax.axvline(0.5, color="#333333", lw=1.0, zorder=2)
        ax.axhline(0.5, color="#333333", lw=1.0, zorder=2)

        ax.set_xticks([0.25, 0.75], [ax_x["false_en"], ax_x["true_en"]], fontsize=PT)
        ax.set_yticks([0.25, 0.75], [ax_y["false_en"], ax_y["true_en"]], fontsize=PT)
        ax.set_xlabel(ax_x["question_en"], fontsize=PT)
        ax.set_ylabel(ax_y["question_en"], fontsize=PT)
        ax.tick_params(length=0)
        for lbl in ax.get_yticklabels():
            lbl.set_rotation(90)
            lbl.set_va("center")
        ax.text(0.5, -0.105, D["footer_en"], fontsize=PT, ha="center", va="center",
                color="#444444", transform=ax.transAxes)

    out = save_figure(fig, f"{FIGDIR}/report00_f4", caption=CAPTIONS["f4"],
                      title="What the engine settles and what it does not",
                      placed_width_in=PLACED_IN, close=True)
    return out


# --------------------------------------------------------------------------- #
def main() -> int:
    B = _load()
    print("── 리포트 00 그림 (벡터 PDF + 400 dpi PNG · 9 pt · 색+해치) ──")
    made = []
    for fn in (fig1_divergence, fig2_size_does_not_enter, fig3_shape, fig4_decision):
        out = fn(B)
        _report(out)
        made.append(out)
    for m in made:
        rep = check_figure(m["pdf"], placed_width_in=PLACED_IN)
        if not rep["ok"]:
            raise SystemExit(f"저장본 재검사 실패: {rep}")
    print(f"✅ 그림 {len(made)}장 — 저장본 재검사 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
