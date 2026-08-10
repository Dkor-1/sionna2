# -*- coding: utf-8 -*-
"""
build_engine_concept_v2.py — **두 엔진 개념도**, 이번엔 도식이 아니라 **실제 렌더** 위에 그린다.

왜 v2 인가 (사용자 지적, 2026-08-11 팀미팅 준비)
--------------------------------------------------
① "시오나 렌더링이라던가 다른 방식으로 표현 불가능하니?"
   → 옛 판(build_engine_concept_fig.py)의 기체는 초타원으로 손그림한 **도식 실루엣**이었다.
     이 판은 이미 뽑아 둔 **Sionna HQ 렌더**를 바탕으로 깐다. 새로 렌더하지 않는다.
       · 왼쪽  outputs/figures/report07_f0c.png          (2304×1440, TX/RX 구 + 실제 경로선)
       · 오른쪽 outputs/figures/report07_anim_poster.png (2000×1494, 표적 근접 정지컷)
② "w/o occlusion 은 뭔지 모르겠어 좀 어렵네"
   → **세 번째 열을 뺐다.** 이번 팀미팅의 축은 «PathSolver ↔ 우리 SBR+PO» 하나뿐이라
     대조군은 그림에서 사라지고 발표 노트 한 줄로만 남는다.

그림에서 읽혀야 하는 것 (딱 세 가지)
  1. 왼쪽 — 광선은 **레이더에서** 나가고, 돌아온 소수만 «경로» 가 된다. 표적 위 면적분이 없다.
  2. 오른쪽 — 격자가 **표적에 앵커**되고 평면파로 조명한다. **첫 히트만** 더하므로 가림이 공짜다.
     거리는 변수로 들어오지 않는다.
  3. 아래 띠 — 두 열 모두 자세당 복소수 하나를 낼 뿐이고, 그 다음 슬로타임·STFT 는 **완전히 같다**.

⭐ 오른쪽 열의 «첫 히트» 점은 **손으로 찍지 않았다.** 렌더의 실루엣 마스크에 대고 광선을
   실제로 진행시켜 처음 만나는 화소를 찾는다(2차원 유사체). 그래서 왼쪽 로터에는 점이 찍히고
   그 뒤로 그림자가 생기며, 가려진 면에는 점이 없다. 이것이 «first hit only» 의 그림이다.
   ⚠ 3차원 첫 히트가 아니라 **렌더 실루엣에 대한 2차원 첫 히트**다. 캡션에 그렇게 적는다.

수치는 실행 시점에 원장에서 읽는다(하드코딩 금지, 하우스 규약).
그림 안 텍스트는 전부 **영어**이고 세미콜론·대시는 쓰지 않는다.

    python benchmark/build_engine_concept_v2.py
"""
from __future__ import annotations

import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
import numpy as np                                                       # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402
from PIL import Image                                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGD = os.path.join(ROOT, "outputs", "figures")
STEM = os.path.join(FIGD, "deck0811_concept_v2")

C0 = 299792458.0

SRC_LEFT = os.path.join(FIGD, "report07_f0c.png")            # 실제 경로 렌더
SRC_RIGHT = os.path.join(FIGD, "report07_anim_poster.png")   # 표적 근접 렌더

INK = "#1b1f24"
GRAY = "#6b7480"
FAINT = "#8d97a2"
BLUE = "#1f5fbf"
GREEN = "#127a4e"
RULE = "#c7ced5"
BAND = "#eef1f4"


# ─────────────────────────────────────────────────────────────────────────── #
#  1. 실행 시점 사실 수집 — JSON 원장 + 소스 상수
# ─────────────────────────────────────────────────────────────────────────── #
def _grab(path, pattern, what):
    """소스에서 상수 하나를 뽑는다. 못 찾으면 예외 — 조용히 거짓말하지 않는다."""
    m = re.search(pattern, open(path, encoding="utf-8").read(), re.M)
    if not m:
        raise RuntimeError(f"{os.path.relpath(path, ROOT)} 에서 {what} 를 못 찾았다. "
                           f"소스가 바뀌었으면 정규식을 고쳐라.")
    return m.group(1)


def facts() -> dict:
    J3 = json.load(open(f"{ROOT}/outputs/report07_three_engines.json", encoding="utf-8"))
    JR = json.load(open(f"{ROOT}/outputs/report07_three_engine_ranges.json", encoding="utf-8"))
    M, R3 = J3["_meta"], JR["ranges"]["R3"]

    div = int(_grab(f"{ROOT}/src/rcs_sbr.py", r"^DEFAULT_DIV\s*=\s*(\d+)", "DEFAULT_DIV"))

    #  열 제목은 결과 그림과 **글자까지 같아야** 청중이 두 그림을 잇는다. 실재를 검사한다.
    ref = open(f"{ROOT}/benchmark/build_three_engine_fig.py", encoding="utf-8").read()
    for t in ("Sionna PathSolver", "Ours (SBR+PO"):
        if t not in ref:
            raise RuntimeError(f"열 제목 {t!r} 이 결과 그림 빌더에 없다. 라벨이 바뀌었다.")

    #  슬로타임 → STFT 규약은 결과 그림이 쓰는 그 모듈에서 **계산해서** 가져온다.
    sys.path.insert(0, os.path.join(ROOT, "src"))
    import md_mapstyle as MS                                             # noqa: N806
    prf, ffl = float(M["prf_hz"]), float(M["f_flash_hz"])
    per = MS.auto_periods(prf, ffl)
    nper = int(round(per * prf / ffl))

    fc = float(M["fc_hz"])
    lam = C0 / fc
    return dict(name=M["name"], fc=fc, lam=lam, div=div, d_mm=1e3 * lam / div,
                spp=int(R3["spp"]), paths_med=float(R3["paths_median"]),
                rng=float(R3["range_m"]),
                n_pose=int(M["n"]), prf=prf, win_ms=1e3 * int(M["n"]) / prf,
                periods=per, nper=nper, hop=int(MS.FLASH_HOP))


def ray_count(lam: float, div: int):
    """SBR 광선 격자가 자세당 몇 발인가 — rcs_sbr.sbr_field 와 같은 식으로 **센다**.

    Rout = max|V-ctr|*1.15 + 3d,  n = ceil(2*Rout/d),  광선 n**2.
    로터 위상마다 경계구가 달라지므로 한 블레이드 주기를 훑어 (min, max) 를 준다.
    실패하면 None 을 돌려주고 그림에서 그 라벨을 뺀다 — 숫자를 지어내지 않는다."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "src"))
        from articulated_fast import FastPoser
        from drones import DRONES
        fp = FastPoser(DRONES["matrice4e"])
        d = lam / div
        ns = []
        for phi in np.linspace(0.0, 180.0, 7):
            V = np.asarray(fp.pose(np.full(len(fp.dirs), phi)).v, float)
            ctr = 0.5 * (V.max(0) + V.min(0))
            r = float(np.linalg.norm(V - ctr, axis=1).max())
            ns.append(int(np.ceil(2 * (r * 1.15 + 3 * d) / d)) ** 2)
        return min(ns), max(ns)
    except Exception as exc:                                             # noqa: BLE001
        print(f"  ⚠ 광선 수 계산 실패({exc}). 그 라벨을 뺀다.")
        return None


# ─────────────────────────────────────────────────────────────────────────── #
#  2. 렌더 읽기 — 새로 렌더하지 않는다. 이미 있는 PNG 를 자른다.
# ─────────────────────────────────────────────────────────────────────────── #
PANEL_AR = None            # 두 칸의 목표 가로세로비. build() 가 채운다.


def load_rgba(path: str) -> np.ndarray:
    if not os.path.exists(path):
        raise RuntimeError(f"바탕 렌더가 없다: {path}. 렌더를 새로 뽑지 말고 경로를 확인해라.")
    return np.asarray(Image.open(path).convert("RGBA"), dtype=float) / 255.0


def content_bbox(a: np.ndarray, alpha_bg: bool) -> tuple[int, int, int, int]:
    """내용이 실제로 있는 사각형. 투명 배경이면 알파로, 흰 배경이면 밝기로 잡는다."""
    m = (a[..., 3] > 0.04) if alpha_bg else (a[..., :3].sum(2) < 2.92)
    ys, xs = np.nonzero(m)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def crop_to_ar(a: np.ndarray, box, ar: float, pad_x: float = 0.03):
    """내용 사각형을 중심에 두고 목표 가로세로비로 잘라 낸다(모자라면 가장자리에 맞춘다)."""
    H, W = a.shape[:2]
    x0, y0, x1, y1 = box
    px = pad_x * (x1 - x0)
    x0, x1 = max(0, x0 - px), min(W, x1 + px)
    w = x1 - x0
    h = w / ar
    cy = 0.5 * (y0 + y1)
    ty0, ty1 = cy - 0.5 * h, cy + 0.5 * h
    if ty0 < 0:
        ty0, ty1 = 0.0, h
    if ty1 > H:
        ty0, ty1 = H - h, float(H)
    if ty0 < 0:                                   # 그래도 안 되면 세로를 다 쓰고 가로를 줄인다
        ty0, ty1 = 0.0, float(H)
        w = (ty1 - ty0) * ar
        cx = 0.5 * (x0 + x1)
        x0, x1 = cx - 0.5 * w, cx + 0.5 * w
    sl = (slice(int(round(ty0)), int(round(ty1))), slice(int(round(x0)), int(round(x1))))
    return a[sl], (int(round(x0)), int(round(ty0)))


def first_hits(mask: np.ndarray, ang_deg: float, n_rays: int, step: float = 1.2):
    """평면파 광선을 실루엣 마스크에 대고 진행시켜 **첫 히트**와 **마지막 히트**를 찾는다.

    반환: (y0, hit, k_in, k_out, dvec, L). 화소 좌표계(x 오른쪽, y 아래)."""
    H, W = mask.shape
    t = np.radians(ang_deg)
    dx, dy = float(np.cos(t)), float(np.sin(t))
    L = W / dx
    y0 = np.linspace(-W * np.tan(t) - 12.0, H + 12.0, n_rays)
    ks = np.arange(0.0, L, step)
    Y = y0[:, None] + ks[None, :] * dy
    xi = np.clip(np.round(ks * dx).astype(int), 0, W - 1)[None, :]
    yi = np.round(Y).astype(int)
    inside = (Y >= 0) & (Y < H)
    M = mask[np.clip(yi, 0, H - 1), np.broadcast_to(xi, Y.shape)] & inside
    hit = M.any(1)
    k_in = ks[M.argmax(1)]
    k_out = ks[M.shape[1] - 1 - M[:, ::-1].argmax(1)]
    return y0, hit, k_in, k_out, (dx, dy), L


# ─────────────────────────────────────────────────────────────────────────── #
#  3. 칸 그리기
# ─────────────────────────────────────────────────────────────────────────── #
def panel_pathsolver(ax, F):
    """왼쪽 — 실제 Sionna 경로 렌더 위에 «쏜 표본» 부채꼴을 얹는다."""
    a = load_rgba(SRC_LEFT)
    sub, off = crop_to_ar(a, content_bbox(a, alpha_bg=True), PANEL_AR, pad_x=0.02)
    H, W = sub.shape[:2]

    #  레이더 위치 = 렌더 안 초록 구의 무게중심(왼쪽 3분의 1 안에서만 찾는다).
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    sph = (al > 0.78) & (g > 0.78) & (r < 0.74) & (b < 0.74)
    sph[:, int(0.25 * a.shape[1]):] = False
    ys, xs = np.nonzero(sph)
    rc = np.array([xs.mean() - off[0], ys.mean() - off[1]])

    #  표적 위치·크기 = 렌더 안 불투명 화소 중 오른쪽 덩어리.
    dm = al > 0.04
    dm[:, :int(0.60 * a.shape[1])] = False
    ys2, xs2 = np.nonzero(dm)
    dc = np.array([xs2.mean() - off[0], ys2.mean() - off[1]])
    corners = np.array([[xs2.min() - off[0], ys2.min() - off[1]],
                        [xs2.max() - off[0], ys2.min() - off[1]],
                        [xs2.min() - off[0], ys2.max() - off[1]],
                        [xs2.max() - off[0], ys2.max() - off[1]]], float)

    reach = 2.6 * float(np.hypot(*(dc - rc)))

    #  ① 버려지는 표본 — 광선은 **온 구면으로** 나간다.
    #     (sionna/rt/utils/ray_tracing.py spawn_ray_from_sources 가 fibonacci_lattice 를
    #      square_to_uniform_sphere 로 감싼다. 실측 확인 2026-08-10.)
    #     그래서 부채꼴이 아니라 별처럼 사방으로 그린다. 대부분은 표적을 못 맞힌다.
    for adeg in np.linspace(0.0, 360.0, 161)[:-1] + 1.7:
        v = np.array([np.cos(np.radians(adeg)), np.sin(np.radians(adeg))])
        ax.plot(*np.array([rc, rc + reach * v]).T, color=BLUE, lw=0.9, alpha=0.20, zorder=1)

    ax.imshow(sub, zorder=3, interpolation="antialiased")

    #  ② 살아남은 경로 — 렌더가 실제로 그린 선이 너무 가늘어 프로젝터에서 사라진다.
    #     선을 **새로 그리지 않고** 렌더 안의 경로 화소만 골라 굵혀서 다시 얹는다.
    #     (구·기체 상자는 빼서 표적과 레이더를 덮지 않게 한다.)
    pm = sub[..., 3] > 0.15
    yy, xx = np.mgrid[0:H, 0:W]
    #  rs 는 물리량이 아니라 **그리기 상수**다. 레이더 표식 두 구를 덮을 만큼이면 된다.
    rs = 0.085 * W
    pm &= (xx - rc[0]) ** 2 + (yy - rc[1]) ** 2 > rs ** 2

    #  기체가 실제로 두꺼워지는 열(= 동체)부터를 «덮으면 안 되는 곳» 으로 본다.
    #  bbox 전체를 빼면 프로펠러 끝까지 잘려 다발이 허공에서 끊긴다(첫 판의 흠).
    bx0, bx1 = int(corners[:, 0].min()), int(corners[:, 0].max())
    by0, by1 = int(corners[:, 1].min()), int(corners[:, 1].max())
    colcnt = (sub[by0:by1 + 1, bx0:bx1 + 1, 3] > 0.15).sum(0)
    core = np.nonzero(colcnt > 0.30 * colcnt.max())[0]
    cx0 = bx0 + (int(core[0]) if core.size else 0)
    pm &= ~((xx > cx0 - 10) & (xx < bx1 + 10) & (yy > by0 - 10) & (yy < by1 + 10))

    thick = pm.copy()
    for ddy in (-1, 0, 1):
        for ddx in (-1, 0, 1):
            thick |= np.roll(np.roll(pm, ddy, 0), ddx, 1)
    #  기체에 다가갈수록 서서히 옅어지게 한다. 딱 끊기면 그림이 고장 난 것처럼 보인다.
    ramp = np.clip((cx0 - xx) / (0.09 * W), 0.0, 1.0)
    ov = np.zeros((H, W, 4))
    ov[..., 0], ov[..., 1], ov[..., 2] = 0.11, 0.12, 0.14
    ov[..., 3] = np.where(thick, 0.60 * ramp, 0.0)
    ax.imshow(ov, zorder=4, interpolation="antialiased")

    #  ③ 글자 — 최소한으로. 광선 위에 얹히므로 흰 판을 깐다.
    bbox = dict(facecolor="white", alpha=0.82, edgecolor="none", pad=2.0)
    ax.text(rc[0] + 0.022 * W, rc[1] + 0.090 * H, "Tx and Rx", color="#a41220",
            fontsize=13.5, fontweight="bold", ha="left", va="top", zorder=6, bbox=bbox)
    ax.annotate(f"median {F['paths_med']:.0f} paths return",
                xy=tuple(rc + 0.62 * (dc - rc)),
                xytext=(0.455 * W, 0.805 * H),
                color=BLUE, fontsize=13.5, fontweight="bold", ha="left", va="center",
                zorder=6, bbox=bbox,
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.8, shrinkA=6, shrinkB=4,
                                connectionstyle="arc3,rad=-0.20"))
    ax.text(0.030 * W, 0.055 * H, f"{F['spp']:,} ray samples per pose".replace(",", " "),
            color=BLUE, fontsize=13.5, fontweight="bold", ha="left", va="top", zorder=6,
            bbox=bbox)
    ax.text(0.030 * W, 0.150 * H, "fired over the whole sphere, almost all of them miss",
            color=GRAY, fontsize=12.5, ha="left", va="top", zorder=6, bbox=bbox)

    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)


def panel_sbrpo(ax, F, rays):
    """오른쪽 — 표적 근접 렌더 위에 평면파와 **계산된 첫 히트**를 얹는다."""
    a = load_rgba(SRC_RIGHT)
    #  포스터 아래쪽에는 크기비교용 작은 기체와 레이더 표식이 같이 들어 있다.
    #  이 칸은 **표적 하나만** 보여야 하므로 위쪽 덩어리로 잘라 낸다.
    top = a[:int(0.55 * a.shape[0])]
    sub, _ = crop_to_ar(top, content_bbox(top, alpha_bg=False), PANEL_AR, pad_x=0.03)
    H, W = sub.shape[:2]
    mask = sub[..., :3].sum(2) < 2.92

    y0, hit, k_in, k_out, (dx, dy), L = first_hits(mask, 7.0, 92)

    for i in range(len(y0)):
        if hit[i]:
            ki, ko = k_in[i], k_out[i]
            ax.plot([0, ki * dx], [y0[i], y0[i] + ki * dy],
                    color=GREEN, lw=1.05, alpha=0.55, zorder=4)
            ax.plot([ko * dx, L * dx], [y0[i] + ko * dy, y0[i] + L * dy],
                    color=FAINT, lw=1.05, alpha=0.26, zorder=4)
        else:
            ax.plot([0, L * dx], [y0[i], y0[i] + L * dy],
                    color=GREEN, lw=0.85, alpha=0.11, zorder=4)

    ax.imshow(sub, zorder=3, interpolation="antialiased")

    hx = k_in[hit] * dx
    hy = y0[hit] + k_in[hit] * dy
    ax.plot(hx, hy, "o", ms=4.4, mfc=GREEN, mec="white", mew=0.6, zorder=6, ls="none")

    #  진행 방향을 크게 한 번만 — 평면파라는 것이 읽히게 화살표 셋.
    for fy in (0.20, 0.50, 0.80):
        y = fy * H
        ax.add_patch(FancyArrowPatch((0.020 * W, y), (0.105 * W, y + 0.085 * W * dy / dx),
                                     arrowstyle="-|>", mutation_scale=16, lw=2.4,
                                     color=GREEN, alpha=0.85, zorder=7))

    lab = "incident plane wave"
    if rays:
        lab += f",  {rays[0] / 1000:.0f}k to {rays[1] / 1000:.0f}k rays per pose"
    ax.text(0.022 * W, 0.055 * H, lab, color=GREEN, fontsize=13.5, fontweight="bold",
            ha="left", va="top", zorder=8)
    ax.text(0.022 * W, 0.135 * H,
            f"ray grid at λ/{F['div']:.0f}, {F['d_mm']:.1f} mm at "
            f"{F['fc'] / 1e9:.1f} GHz", color=GRAY, fontsize=12.5,
            ha="left", va="top", zorder=8)
    ax.text(0.978 * W, 0.055 * H, "first hit only", color=GREEN, fontsize=13.5,
            fontweight="bold", ha="right", va="top", zorder=8)
    ax.text(0.978 * W, 0.135 * H, "so the far side is never summed", color=GRAY,
            fontsize=12.5, ha="right", va="top", zorder=8)

    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)


# ─────────────────────────────────────────────────────────────────────────── #
#  4. 판 짜기
# ─────────────────────────────────────────────────────────────────────────── #
FIGW, FIGH = 16.60, 8.30
MARG, GUT = 0.34, 0.34
COLW = (FIGW - 2 * MARG - GUT) / 2.0
PAN_T, PAN_H = 1.46, 3.50


def build():
    global PANEL_AR
    PANEL_AR = COLW / PAN_H

    F = facts()
    rays = ray_count(F["lam"], F["div"])

    fig = plt.figure(figsize=(FIGW, FIGH), dpi=200)
    fig.patch.set_facecolor("white")

    def X(inch):
        return inch / FIGW

    def Y(inch):
        return 1.0 - inch / FIGH

    warn = []

    def txt(x_in, y_in, s, **kw):
        return fig.text(X(x_in), Y(y_in), s, **kw)

    def check(t, x_in, limit_in, tag):
        """칸 밖으로 흘러나가는 글자를 잡는다(하우스 규약: 넘침 금지)."""
        bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
        w_in = bb.width / fig.dpi
        if x_in + w_in > limit_in + 1e-3:
            warn.append(f"{tag}: {x_in + w_in:.2f} in > {limit_in:.2f} in  |  {t.get_text()[:60]}")

    #  ── 표제 ────────────────────────────────────────────────────────────── #
    txt(MARG, 0.44, "What the two engines actually compute",
        fontsize=26, fontweight="bold", color=INK, ha="left", va="center")
    txt(MARG, 0.86,
        "Both give one complex number per rotor pose. The map is what the same STFT "
        "makes of those numbers.",
        fontsize=14.5, color=GRAY, ha="left", va="center")

    #  ── 열 제목 ─────────────────────────────────────────────────────────── #
    cols = [
        (MARG, BLUE, "Sionna PathSolver",
         "rays leave the radar and the few that come back are the paths"),
        (MARG + COLW + GUT, GREEN, "Ours (SBR+PO)",
         "a ray grid is anchored on the target and only the first hit is summed"),
    ]
    for x0, c, head, sub in cols:
        t = txt(x0, 1.13, head, fontsize=20, fontweight="bold", color=c, ha="left", va="center")
        check(t, x0, x0 + COLW, "head")
        t = txt(x0, 1.40, sub, fontsize=13.5, color=GRAY, ha="left", va="center")
        check(t, x0, x0 + COLW, "subhead")

    #  ── 두 칸 ───────────────────────────────────────────────────────────── #
    axes = []
    for x0, *_ in cols:
        ax = fig.add_axes([X(x0), Y(PAN_T + PAN_H), COLW / FIGW, PAN_H / FIGH])
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color(RULE)
            sp.set_linewidth(1.1)
        ax.set_facecolor("white")
        axes.append(ax)
    panel_pathsolver(axes[0], F)
    panel_sbrpo(axes[1], F, rays)

    #  ── 칸 아래 세 줄 + 핵심 한 줄 ──────────────────────────────────────── #
    rows = [
        [("FIRED", f"{F['spp']:,}".replace(",", " ") + " ray samples, uniform on the sphere"),
         ("KEPT", f"the paths that return, median {F['paths_med']:.0f} "
                  f"at {F['rng']:.0f} m"),
         ("LEFT OUT", "the surface integral over the target")],
        [("FIRED", f"a plane wave on a λ/{F['div']:.0f} ray grid"),
         ("KEPT", "the first hit of every ray"),
         ("LEFT OUT", "back facing and hidden facets")],
    ]
    keys = [("Solid angle falls as (D/R)², so the ray budget grows with range", BLUE),
            ("The grid rides on the target, so range is not a variable at all", GREEN)]
    y_rows = (5.34, 5.66, 5.98)
    for (x0, c, *_), rws, (kline, kc) in zip(cols, rows, keys):
        for y, (lab, s) in zip(y_rows, rws):
            txt(x0 + 0.04, y, lab, fontsize=12.0, fontweight="bold", color=FAINT,
                ha="left", va="center")
            t = txt(x0 + 1.28, y, s, fontsize=14.5, color=INK, ha="left", va="center")
            check(t, x0 + 1.28, x0 + COLW, "row")
        fig.add_artist(plt.Line2D([X(x0 + 0.04), X(x0 + COLW)], [Y(6.22), Y(6.22)],
                                  color=kc, lw=2.0, alpha=0.85))
        t = txt(x0 + 0.04, 6.48, kline, fontsize=14.5, fontweight="bold", color=kc,
                ha="left", va="center")
        check(t, x0 + 0.04, x0 + COLW, "key")

    #  ── 아래 띠 — 두 열 공통 사슬 ───────────────────────────────────────── #
    txt(MARG, 6.98, "BOTH COLUMNS THEN RUN THE SAME SLOW TIME CHAIN",
        fontsize=13.0, fontweight="bold", color=FAINT, ha="left", va="center")

    chain = [
        "one complex number\nper rotor pose",
        f"{F['n_pose']} poses on a slow time grid\n"
        f"PRF {F['prf'] / 1e3:.1f} kHz, {F['win_ms']:.0f} ms",
        f"STFT, {F['nper']} sample Hann\n"
        f"{F['periods']:.2f} blade periods, hop {F['hop']}",
        "the micro-Doppler map\ntime against Doppler",
    ]
    bx = fig.add_axes([X(MARG), Y(7.94), (FIGW - 2 * MARG) / FIGW, 0.72 / FIGH])
    bx.set_axis_off()
    bx.set_xlim(0, 1)
    bx.set_ylim(0, 1)
    n = len(chain)
    gap = 0.028
    bw = (1.0 - (n - 1) * gap) / n
    for i, s in enumerate(chain):
        x = i * (bw + gap)
        bx.add_patch(FancyBboxPatch((x, 0.06), bw, 0.88, boxstyle="round,pad=0,rounding_size=0.012",
                                    facecolor=BAND, edgecolor=RULE, lw=1.1,
                                    transform=bx.transAxes))
        bx.text(x + bw / 2, 0.50, s, ha="center", va="center", fontsize=13.5, color=INK,
                linespacing=1.45, transform=bx.transAxes)
        if i < n - 1:
            bx.add_patch(FancyArrowPatch((x + bw + 0.004, 0.50), (x + bw + gap - 0.004, 0.50),
                                         arrowstyle="-|>", mutation_scale=15, lw=1.6,
                                         color=FAINT, transform=bx.transAxes))

    #  ── 각주 한 줄 ──────────────────────────────────────────────────────── #
    txt(MARG, 8.14,
        "Real Sionna renders of the simulated " + F["name"] +
        ". Rays are drawn sparse for readability and the first hits on the right are "
        "traced against the rendered silhouette.",
        fontsize=11.5, color=FAINT, ha="left", va="center")

    #  ⛔ 하우스 규약 자기검사 — 세미콜론·대시는 그림 글자에 들어가면 안 된다.
    #     (저장 **전에** 본다. 닫은 뒤에는 fig.texts 를 못 읽는다.)
    bad = [t.get_text() for t in fig.texts + [c for a in fig.axes for c in a.texts]
           if any(ch in t.get_text() for ch in ";—–")]
    if bad:
        raise RuntimeError(f"금지 문자가 그림 글자에 있다: {bad}")

    for ext in ("png", "pdf"):
        fig.savefig(f"{STEM}.{ext}", facecolor="white")
    plt.close(fig)

    w, h = Image.open(f"{STEM}.png").size
    print(f"\n✅ {STEM}.png   {w}×{h} px   aspect {w / h:.2f}")
    print(f"   바탕 렌더  {os.path.basename(SRC_LEFT)} · {os.path.basename(SRC_RIGHT)}")
    print(f"   표적 {F['name']} · fc {F['fc'] / 1e9:.1f} GHz · λ/{F['div']} = {F['d_mm']:.2f} mm")
    print(f"   Sionna {F['spp']:,} spp → 경로 중앙 {F['paths_med']:.0f} @ {F['rng']:.0f} m")
    if rays:
        print(f"   SBR 광선/자세 {rays[0]:,} ~ {rays[1]:,}")
    print(f"   슬로타임 {F['n_pose']} 자세 · PRF {F['prf'] / 1e3:.1f} kHz · {F['win_ms']:.1f} ms "
          f"· STFT {F['nper']} 표본({F['periods']:.2f} 주기) · hop {F['hop']}")
    if warn:
        print("\n⚠ 칸 넘침 의심:")
        for w_ in warn:
            print("   " + w_)
    else:
        print("   넘침 검사 통과")


if __name__ == "__main__":
    build()
