# -*- coding: utf-8 -*-
"""
build_engine_concept_v3.py — **글자 없는 개념도**. PathSolver ↔ SBR+PO 를 그림만으로 보인다.

왜 v3 인가 (사용자 지적, 2026-08-11)
------------------------------------
    "4페이지 이미지가 너무 주저리주저리가 심하다. path solver 랑 SBR+PO 가 이해되게끔만
     하면 좋겠는데 텍스트가 너무 많다. 직관적인 사진만 넣어줄 수 없나."

그래서 v2 에서 숫자·표·사슬 띠·각주를 **전부 뺐다**. 남은 글자는 열 제목 두 개와
아주 짧은 라벨 다섯 개뿐이다(총 60여 자, v2 는 1281 자).
v2 빌더·그림은 그대로 둔다. 이 파일은 새 파일이고 새 출력물만 쓴다.

그림 하나로 읽혀야 하는 것 (글자 없이)
  ① 왼쪽 — 광선이 레이더에서 **사방으로** 나가고 표적에 닿는 것은 아주 좁은 부채꼴뿐이다.
     나머지는 표적 옆을 스쳐 허공으로 나간다. 표적 위에 찍힌 점도 몇 개 안 된다.
  ② 오른쪽 — 격자가 표적 경계상자에 **딱 붙어** 있고 평행 광선이 거기서 출발한다.
     첫 히트마다 점이 찍혀 앞면 윤곽이 점선처럼 이어지고, 그 뒤는 회색(그림자)이라
     점이 하나도 없다. 가림이 공짜라는 말의 그림이다.
  ③ 두 칸의 표적은 **같은 렌더를 같은 크기·같은 자리**에 놓았다. 다른 것은 조명 방식뿐이다.

⭐ 점은 손으로 찍지 않는다. 렌더 실루엣 마스크에 대고 광선을 실제로 행진시켜 처음 만나는
   화소를 찾는다(2차원 유사체). 그림자도 같은 마스크에서 «행에서 처음 만난 덩어리 뒤» 로
   계산한다. 그래서 왼쪽 프로펠러는 밝고 그 뒤 동체·오른쪽 프로펠러는 그늘이다.

새 GPU 계산은 하지 않는다. 이미 있는 렌더 PNG 한 장만 읽어 CPU 로 그린다.

    python benchmark/build_engine_concept_v3.py
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402
import numpy as np                                               # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle  # noqa: E402
from PIL import Image                                            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGD = os.path.join(ROOT, "outputs", "figures")
STEM = os.path.join(FIGD, "deck0811_concept_v3")

#  바탕이 되는 실제 Sionna 렌더 (새로 렌더하지 않는다)
SRC = os.path.join(FIGD, "report07_anim_poster.png")

INK = "#1b1f24"
GRAY = "#6b7480"
FAINT = "#98a1ab"
HAIR = "#dfe3e8"
ACC = "#cc3311"            # 강조 1색 — «실제로 계산에 쓰이는 광선»
SHADE = (0.36, 0.40, 0.45)  # 그림자 회색

#  ── 판 크기 ──────────────────────────────────────────────────────────────── #
FIGW, FIGH = 16.40, 7.30           # 2.25 : 1
MARG, GUT = 0.30, 0.44
COLW = (FIGW - 2 * MARG - GUT) / 2.0
PAN_T = 0.82                       # 칸 위끝(인치, 위에서)
PAN_B = 0.20                       # 칸 아래 여백
PAN_H = FIGH - PAN_T - PAN_B

#  ── 칸 안 좌표계(화소) ───────────────────────────────────────────────────── #
WP = 1560
HP = int(round(WP * PAN_H / COLW))

#  표적을 놓는 자리 — **두 칸에서 완전히 같다**
DW_FRAC = 0.44                     # 표적 폭 / 칸 폭
CX_FRAC, CY_FRAC = 0.615, 0.520    # 표적 중심

RADAR = (0.052, 0.520)             # 왼쪽 칸 레이더 자리(칸 폭·높이 비율)
N_FAN = 288                        # 왼쪽 칸에 그리는 광선 수(사방)
GRID_PAD = 0.055                   # 오른쪽 칸 격자 상자가 표적에서 띄우는 여백(표적 폭 대비)
RAY_DY = 8.0                       # 오른쪽 칸 광선 간격(화소)


# ─────────────────────────────────────────────────────────────────────────── #
#  1. 표적 자산 — 렌더 한 장에서 실루엣을 오려 칸 좌표계에 붙인다
# ─────────────────────────────────────────────────────────────────────────── #
def target_asset():
    """렌더에서 기체만 오려 (칸 크기 RGBA 캔버스, 불투명 마스크, 상자) 를 돌려준다."""
    if not os.path.exists(SRC):
        raise RuntimeError(f"바탕 렌더가 없다: {SRC}. 렌더를 새로 뽑지 말고 경로를 확인해라.")
    a = np.asarray(Image.open(SRC).convert("RGB"), dtype=float) / 255.0

    #  포스터 아래쪽에는 크기비교용 작은 기체와 붉은 표식이 같이 있다. 위 덩어리만 쓴다.
    top = a[: int(0.55 * a.shape[0])]
    lum = top.mean(2)
    m = lum < 0.999                                     # 배경은 순백(1.0)이라 이걸로 갈린다
    ys, xs = np.nonzero(m)
    if ys.size == 0:
        raise RuntimeError("렌더에서 기체를 못 찾았다. 배경이 순백이 아닐 수 있다.")
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    rgb = top[y0:y1, x0:x1]
    alpha = np.clip((1.0 - rgb.mean(2)) * 300.0, 0.0, 1.0)   # 배경만 투명, 가장자리는 부드럽게

    #  칸 좌표계에 놓을 크기로 줄인다
    dw = DW_FRAC * WP
    dh = dw * (y1 - y0) / (x1 - x0)
    tw, th = int(round(dw)), int(round(dh))
    rgba = np.dstack([rgb, alpha])
    im = Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").resize((tw, th), Image.LANCZOS)
    small = np.asarray(im, dtype=float) / 255.0

    px = int(round(CX_FRAC * WP - tw / 2))
    py = int(round(CY_FRAC * HP - th / 2))

    canvas = np.zeros((HP, WP, 4), dtype=float)
    canvas[py:py + th, px:px + tw] = small
    mask = canvas[..., 3] > 0.30

    #  흰 바탕 위 흰 기체라 프로펠러가 사라진다. 실루엣 테두리를 얇게 둘러 살린다.
    #  (두 칸에 같은 캔버스를 쓰므로 테두리도 두 칸에서 똑같다.)
    edge = np.zeros_like(mask)
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            edge |= np.roll(np.roll(mask, dy, 0), dx, 1)
    edge &= ~mask
    canvas[edge, 0], canvas[edge, 1], canvas[edge, 2] = 0.52, 0.56, 0.61
    canvas[edge, 3] = 0.80
    return canvas, mask, (px, py, px + tw, py + th)


# ─────────────────────────────────────────────────────────────────────────── #
#  2. 광선 행진 — 손으로 찍지 않고 마스크에 대고 실제로 찾는다
# ─────────────────────────────────────────────────────────────────────────── #
def march(mask, p0, ang_deg, t_max, step=2.0):
    """점 p0 에서 각 ang_deg 로 나아가며 첫 히트까지의 거리를 돌려준다(없으면 None)."""
    d = np.array([np.cos(np.radians(ang_deg)), np.sin(np.radians(ang_deg))])
    t = np.arange(8.0, t_max, step)
    x = np.round(p0[0] + t * d[0]).astype(int)
    y = np.round(p0[1] + t * d[1]).astype(int)
    ok = (x >= 0) & (x < WP) & (y >= 0) & (y < HP)
    if not ok.any():
        return d, None
    hit = np.zeros_like(t, dtype=bool)
    hit[ok] = mask[y[ok], x[ok]]
    if not hit.any():
        return d, None
    return d, float(t[hit.argmax()])


def exit_t(p0, d):
    """칸 경계까지의 거리."""
    ts = []
    for lo, hi, o, v in ((0.0, WP, p0[0], d[0]), (0.0, HP, p0[1], d[1])):
        if abs(v) < 1e-9:
            continue
        ts += [(lo - o) / v, (hi - o) / v]
    return min(t for t in ts if t > 0)


def first_blob_end(mask):
    """행마다 «처음 만난 덩어리» 의 시작과 끝 열을 준다. 그 뒤가 곧 그림자다."""
    H, W = mask.shape
    start = np.full(H, -1)
    end = np.full(H, -1)
    any_hit = mask.any(1)
    idx = np.nonzero(any_hit)[0]
    s = mask[idx].argmax(1)
    for r, si in zip(idx, s):
        row = mask[r]
        nxt = np.nonzero(~row[si:])[0]
        start[r] = si
        end[r] = si + (int(nxt[0]) if nxt.size else W - si)
    return start, end


# ─────────────────────────────────────────────────────────────────────────── #
#  3. 왼쪽 칸 — 레이더에서 사방으로, 돌아오는 것은 극히 일부
# ─────────────────────────────────────────────────────────────────────────── #
def panel_left(ax, canvas, mask, box):
    rc = np.array([RADAR[0] * WP, RADAR[1] * HP])
    hits = []

    for a_deg in np.linspace(0.0, 360.0, N_FAN, endpoint=False) + 0.6:
        d = np.array([np.cos(np.radians(a_deg)), np.sin(np.radians(a_deg))])
        te = exit_t(rc, d)
        _, th = march(mask, rc, a_deg, te)
        if th is None:
            p = rc + te * d
            ax.plot([rc[0], p[0]], [rc[1], p[1]], color=FAINT, lw=0.55, alpha=0.30, zorder=2)
        else:
            p = rc + th * d
            hits.append(p)
            ax.plot([rc[0], p[0]], [rc[1], p[1]], color=ACC, lw=1.5, alpha=0.95, zorder=5)

    ax.imshow(canvas, extent=(0, WP, HP, 0), zorder=4, interpolation="antialiased")

    if hits:
        h = np.array(hits)
        ax.plot(h[:, 0], h[:, 1], "o", ms=5.4, mfc=ACC, mec="white", mew=0.8,
                ls="none", zorder=7)

    #  되돌아오는 화살 — 표적에서 레이더로 활처럼. 다발과 겹치지 않게 아래로 크게 휜다.
    apex = None
    if hits:
        h = np.array(hits)
        src = h[np.argmax(h[:, 1])]
        dst = np.array([rc[0] + 30.0, rc[1] + 16.0])
        rad = 0.34
        ax.add_patch(FancyArrowPatch(tuple(src), tuple(dst),
                                     arrowstyle="-|>", mutation_scale=22, lw=2.4,
                                     color=ACC, alpha=0.95, zorder=8,
                                     connectionstyle=f"arc3,rad={rad}",
                                     shrinkA=10, shrinkB=6))
        dv = dst - src
        apex = 0.5 * (src + dst) + 0.5 * rad * np.array([dv[1], -dv[0]])

    #  레이더 표식
    ax.add_patch(Circle(tuple(rc), 13, facecolor=INK, edgecolor="none", zorder=9))
    for r in (28, 44):
        ax.add_patch(Circle(tuple(rc), r, facecolor="none", edgecolor=INK,
                            lw=1.3, alpha=0.45, zorder=9))

    #  글자 — 셋뿐
    halo = dict(facecolor="white", edgecolor="none", alpha=0.88, pad=2.0)
    ax.text(rc[0], rc[1] + 78, "Tx and Rx", color=INK, fontsize=15, fontweight="bold",
            ha="center", va="top", zorder=10, bbox=halo)
    ax.text(0.545 * WP, 0.215 * HP, "miss", color=GRAY, fontsize=15, ha="center", va="center",
            zorder=10, bbox=halo)
    if apex is not None:
        ax.text(apex[0], apex[1] + 6, "return", color=ACC, fontsize=15, fontweight="bold",
                ha="center", va="center", zorder=10, bbox=halo)

    ax.set_xlim(0, WP)
    ax.set_ylim(HP, 0)
    return len(hits)


# ─────────────────────────────────────────────────────────────────────────── #
#  4. 오른쪽 칸 — 표적에 붙은 격자, 첫 히트만, 뒤는 그림자
# ─────────────────────────────────────────────────────────────────────────── #
def panel_right(ax, canvas, mask, box):
    """조명은 왼쪽에서 오는 평면파다(왼쪽 칸 레이더와 같은 방향).

    그늘은 **기체 위에만** 칠한다. 빈 공간까지 칠하면 상자가 통째로 회색 판이 되어
    기체가 묻힌다(첫 판의 흠). 기체 위에만 칠하면 «앞면은 컬러, 뒷면은 납작한 회색» 이
    되어 대비가 산다. 이 방향에서 가려지는 기체 화소는 78%다(측정값)."""
    x0, y0, x1, y1 = box
    pad = GRID_PAD * (x1 - x0)
    bx0, bx1 = x0 - pad, x1 + pad
    by0, by1 = y0 - pad, y1 + pad

    start, end = first_blob_end(mask)                    # 행마다 처음 만난 덩어리

    #  ① 가림 — 행에서 첫 덩어리 뒤는 전부 그늘이다
    sh = np.zeros((HP, WP), dtype=bool)
    cols = np.arange(WP)[None, :]
    rows = np.nonzero(end >= 0)[0]
    sh[rows] = cols >= end[rows][:, None]
    keep = np.zeros((HP, WP), dtype=bool)
    keep[int(by0):int(by1), int(bx0):int(bx1)] = True
    sh &= keep
    #  테두리 화소도 같이 칠해야 그늘 경계가 두 겹으로 남지 않는다
    shx = sh.copy()
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            shx |= np.roll(np.roll(sh, dy, 0), dx, 1)
    body = canvas[..., 3] > 0.05
    ov = np.zeros((HP, WP, 4))
    ov[..., 0], ov[..., 1], ov[..., 2] = SHADE
    ov[..., 3] = np.where(shx & body, 0.42, 0.0)         # 가려진 면만 납작한 회색으로

    #  ② 들어오는 평면파 — 상자 왼쪽에서만, 아주 옅게
    #  줄이 너무 촘촘하면 «줄공책» 처럼 보인다. 성기게, 대신 조금 진하게.
    for y in np.arange(0.035 * HP, HP, 0.060 * HP):
        ax.plot([0.0, bx0], [y, y], color=ACC, lw=0.9, alpha=0.22, zorder=2)
    for fy in (0.14, 0.50, 0.86):
        y = fy * HP
        ax.add_patch(FancyArrowPatch((0.045 * WP, y), (0.045 * WP + 0.085 * WP, y),
                                     arrowstyle="-|>", mutation_scale=17, lw=2.2,
                                     color=ACC, alpha=0.80, zorder=3))

    #  ③ 격자 상자 — 표적에 딱 붙어 있다
    ax.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, facecolor="none",
                           edgecolor=GRAY, lw=1.1, ls=(0, (5, 4)), alpha=0.85, zorder=6))

    #  ④ 촘촘한 광선 — 상자 왼쪽 모서리 빗살에서 출발해 첫 히트에서 멈춘다
    ys = np.arange(by0 + RAY_DY * 0.5, by1, RAY_DY)
    hx, hy = [], []
    for y in ys:
        r = int(round(y))
        s = start[r] if 0 <= r < HP else -1
        if s >= 0 and bx0 <= s <= bx1:
            ax.plot([bx0, s], [y, y], color=ACC, lw=1.1, alpha=0.70, zorder=4)
            hx.append(s)
            hy.append(y)
        else:
            ax.plot([bx0, bx1], [y, y], color=ACC, lw=0.8, alpha=0.12, zorder=4)
        ax.plot([bx0 - 13, bx0], [y, y], color=ACC, lw=1.2, alpha=0.80, zorder=5)   # 빗살
    ax.plot([bx0, bx0], [by0, by1], color=ACC, lw=1.5, alpha=0.80, zorder=5)

    ax.imshow(canvas, extent=(0, WP, HP, 0), zorder=7, interpolation="antialiased")
    ax.imshow(ov, extent=(0, WP, HP, 0), zorder=8, interpolation="antialiased")

    ax.plot(hx, hy, "o", ms=4.2, mfc=ACC, mec="white", mew=0.5, ls="none", zorder=10)

    #  ⑤ 글자 — 둘뿐
    halo = dict(facecolor="white", edgecolor="none", alpha=0.90, pad=2.0)
    k = int(0.24 * len(hx))
    ax.annotate("first hit", xy=(hx[k], hy[k]), xytext=(bx0 - 0.155 * WP, by0 - 0.135 * HP),
                color=ACC, fontsize=15, fontweight="bold", ha="center", va="center", zorder=12,
                bbox=halo,
                arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.6, shrinkA=5, shrinkB=3,
                                connectionstyle="arc3,rad=0.20"))
    #  «shadow» 는 그늘진 **기체 뒷면** 을 가리켜야 한다. 빈 곳을 가리키면 뭘 보라는 건지 모른다.
    ax.annotate("shadow", xy=(x0 + 0.64 * (x1 - x0), y0 + 0.66 * (y1 - y0)),
                xytext=(bx1 - 0.075 * WP, by1 + 0.155 * HP),
                color=GRAY, fontsize=15, ha="center", va="center", zorder=12, bbox=halo,
                arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.6, shrinkA=5, shrinkB=3,
                                connectionstyle="arc3,rad=-0.20"))

    ax.set_xlim(0, WP)
    ax.set_ylim(HP, 0)
    return len(hx)


# ─────────────────────────────────────────────────────────────────────────── #
#  5. 판 짜기
# ─────────────────────────────────────────────────────────────────────────── #
def build():
    canvas, mask, box = target_asset()

    fig = plt.figure(figsize=(FIGW, FIGH), dpi=220)
    fig.patch.set_facecolor("white")

    def X(i):
        return i / FIGW

    def Y(i):
        return 1.0 - i / FIGH

    heads = [(MARG, "Sionna PathSolver"), (MARG + COLW + GUT, "Ours (SBR+PO)")]
    for x0, s in heads:
        fig.text(X(x0), Y(0.46), s, fontsize=21, fontweight="bold", color=INK,
                 ha="left", va="center")

    axes = []
    for x0, _ in heads:
        ax = fig.add_axes([X(x0), Y(PAN_T + PAN_H), COLW / FIGW, PAN_H / FIGH])
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_facecolor("white")
        axes.append(ax)

    n_left = panel_left(axes[0], canvas, mask, box)
    n_right = panel_right(axes[1], canvas, mask, box)

    #  두 칸 사이 실낱 구분선
    xd = X(MARG + COLW + GUT / 2.0)
    fig.add_artist(plt.Line2D([xd, xd], [Y(FIGH - 0.24), Y(0.24)], color=HAIR, lw=1.2))

    #  ⛔ 하우스 규약 자기검사 — 세미콜론·대시 금지, 글자량 보고
    txts = [t.get_text() for t in fig.texts] + \
           [c.get_text() for a in fig.axes for c in a.texts]
    txts = [t for t in txts if t.strip()]
    bad = [t for t in txts if any(ch in t for ch in ";—–")]
    if bad:
        raise RuntimeError(f"금지 문자가 그림 글자에 있다: {bad}")

    for ext in ("png", "pdf"):
        fig.savefig(f"{STEM}.{ext}", facecolor="white")
    plt.close(fig)

    w, h = Image.open(f"{STEM}.png").size
    n_chars = sum(len(t) for t in txts)
    print(f"\n✅ {STEM}.png   {w}×{h} px   aspect {w / h:.2f}")
    print(f"   바탕 렌더 {os.path.basename(SRC)} (새 렌더 없음, CPU 그리기만)")
    print(f"   글자 {len(txts)} 조각 · {n_chars} 자   (v2 는 34 조각 1281 자)")
    print(f"   왼쪽 광선 {N_FAN} 발 중 표적에 닿은 것 {n_left} 발 "
          f"({100 * n_left / N_FAN:.1f}%)")
    print(f"   오른쪽 첫 히트 점 {n_right} 개")
    for t in txts:
        print(f"     · {t!r}")


if __name__ == "__main__":
    build()
