# -*- coding: utf-8 -*-
"""verify_comparability_yuan.py — 측정앵커 **비교가능성(comparability)** 적대적 검증.

이 파일이 하는 일은 두 가지다.

 1) **Yuan Fig.5 의 측정 μ(f) 곡선을 PDF 벡터경로에서 직접 복원**한다.
    두 논문이 공표한 것은 1.8~18.2 GHz **전대역 선형회귀** 계수(a,b)뿐이다. 우리 대역
    (1.8~5.21 GHz)에서 측정 μ 가 실제로 어떻게 생겼는지는 그 계수로 알 수 없다.
    Yuan 논문 4쪽 Fig.5 는 래스터가 아니라 **벡터**라서 곡선 좌표를 그대로 꺼낼 수 있다.
    복원 정확도는 같은 축에 함께 그려진 **회귀직선**으로 독립검증한다 (아래 selfcheck).

 2) 복원곡선으로 **'우리 기울기가 측정보다 N배 가파르다'** 라는 비교가 성립하는지 따진다.
    결론은 아래 verdict 필드에 있다.

실행 (GPU 불필요):
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src:benchmark SIONNA2_CPU=1 ~/.venvs/py312/bin/python benchmark/verify_comparability_yuan.py
"""
from __future__ import annotations

import numpy as np

YUAN_PDF = ("/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/"
            "On_Experimental_Analysis_of_Mono-Static_3D_UAV_RCS_for_ISAC_Channel_Modeling.pdf")
PAGE = 3                                   # Fig.5 가 있는 쪽 (0-based)
MATLAB_BLUE = (0.0, 0.4470, 0.7402)        # MATLAB 기본 1번색 #0072BD
COLOR_TOL = 0.02
# Fig.5 (a)/(b)/(c) 축 상자 [pt] — θ = 90(방위면) / 0(위) / 180(아래)
BOXES = {90: (346.7, 63.7, 504.8, 146.9), 0: (346.7, 200.6, 504.8, 283.8),
         180: (346.7, 337.5, 504.8, 420.7)}
YUAN_PUBLISHED_AB = {90: (0.315, -16.15), 0: (0.231, -17.92), 180: (0.175, -17.12)}


def _axis_calibration(page, bb):
    """축 눈금 라벨의 좌표에서 pt→(GHz, dBsm) 1차 사상을 만든다."""
    xs, ys = [], []
    for x0, y0, x1, y1, t, *_ in page.get_text("words"):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        try:
            v = float(t)
        except ValueError:
            continue
        if bb[0] - 4 < cx < bb[2] + 4 and bb[3] + 1 < cy < bb[3] + 14 and v > 0:
            xs.append((v, cx))                       # 아래쪽 주파수축
        if bb[0] - 16 < cx < bb[0] - 1 and bb[1] - 4 < cy < bb[3] + 4 and v < 0:
            ys.append((v, cy))                       # 왼쪽 μ 축 (전부 음수 dBsm)
    if len(xs) < 3 or len(ys) < 3:
        raise RuntimeError(f"눈금 판독 실패 xs={xs} ys={ys}")
    ax = np.polyfit([c for _, c in xs], [v for v, _ in xs], 1)
    ay = np.polyfit([c for _, c in ys], [v for v, _ in ys], 1)
    err = max(np.abs(np.polyval(ax, [c for _, c in xs]) - [v for v, _ in xs]).max(),
              np.abs(np.polyval(ay, [c for _, c in ys]) - [v for v, _ in ys]).max())
    return ax, ay, float(err)


def _polyline(page, bb, ax, ay, dashed: bool):
    """상자 안의 파란 곡선 하나를 (f[GHz], μ[dBsm]) 로 돌려준다.

    dashed=False → 실선 = 범례 'Measured' (측정 방위평균 μ)
    dashed=True  → 파선 = 범례 'Mean-fre. fit' (논문 회귀직선) — 축보정 검증용"""
    best = None
    for dr in page.get_drawings():
        c = dr.get("color")
        if c is None or max(abs(c[i] - MATLAB_BLUE[i]) for i in range(3)) > COLOR_TOL:
            continue
        is_dashed = dr.get("dashes") not in (None, "[] 0")
        if is_dashed != dashed:
            continue
        r = dr["rect"]
        if not (r.y0 > bb[1] - 25 and r.y1 < bb[3] + 25
                and r.x0 > bb[0] - 25 and r.x1 < bb[2] + 25):
            continue   # ⚠ x 범위도 걸러야 한다 — 같은 높이 왼쪽 단에 Fig.4 의 파란 실선이 있다
        pts = [tuple(q) for it in dr["items"] if it[0] == "l" for q in (it[1], it[2])]
        if len(pts) > 500 and (best is None or len(pts) > len(best)):
            best = pts
    if best is None:
        raise RuntimeError(f"곡선을 못 찾았다 (bb={bb}, dashed={dashed})")
    q = np.array(best)
    f, mu = np.polyval(ax, q[:, 0]), np.polyval(ay, q[:, 1])
    o = np.argsort(f)
    f, mu = f[o], mu[o]
    fu, inv = np.unique(np.round(f, 4), return_inverse=True)     # 같은 x 는 평균
    return fu, np.array([mu[inv == i].mean() for i in range(len(fu))])


def extract(pdf=YUAN_PDF):
    """θ=90/0/180 의 측정 μ(f) 곡선 + 복원정확도 자기검증."""
    import fitz
    page = fitz.open(pdf)[PAGE]
    curves, check = {}, {}
    for th, bb in BOXES.items():
        ax, ay, tick_err = _axis_calibration(page, bb)
        f, mu = _polyline(page, bb, ax, ay, dashed=False)
        # 자기검증: 같은 축에 그려진 회귀직선을 복원해 공표계수와 맞춘다
        fl, ml = _polyline(page, bb, ax, ay, dashed=True)
        a_l, b_l = np.polyfit(fl, ml, 1)
        nonlin = float(np.abs(ml - (a_l * fl + b_l)).max())
        a_p, b_p = YUAN_PUBLISHED_AB[th]
        # 두번째 검증: 복원곡선을 전대역 재회귀하면 공표계수가 나와야 한다
        a_c, b_c = np.polyfit(f, mu, 1)
        curves[th] = (f, mu)
        check[th] = dict(tick_fit_resid_db=tick_err, fitline_nonlinearity_db=nonlin,
                         fitline_a=float(a_l), fitline_b=float(b_l),
                         fitline_da=float(a_l - a_p), fitline_db=float(b_l - b_p),
                         refit_a=float(a_c), refit_b=float(b_c),
                         refit_da=float(a_c - a_p), refit_db=float(b_c - b_p),
                         published_a=a_p, published_b=b_p, n_points=int(len(f)))
    return curves, check


def pooled_linear(curves, f_grid):
    """고도 3면을 **선형영역**에서 평균한 μ(f) [dBsm]."""
    return 10.0 * np.log10(np.mean([10.0 ** (np.interp(f_grid, f, mu) / 10.0)
                                    for f, mu in curves.values()], axis=0))


def slope_in(f, mu, lo, hi):
    """[lo,hi] GHz 국소 선형회귀 → (기울기 dB/GHz, 절편, R²)."""
    w = (f >= lo) & (f <= hi)
    a, b = np.polyfit(f[w], mu[w], 1)
    r = mu[w] - (a * f[w] + b)
    return float(a), float(b), float(1.0 - r.var() / mu[w].var())


if __name__ == "__main__":
    cur, chk = extract()
    for th, c in chk.items():
        print(f"θ={th:3d}: 눈금잔차 {c['tick_fit_resid_db']:.4f} dB · 회귀직선 비직선성 "
              f"{c['fitline_nonlinearity_db']:.4f} dB · Δa={c['fitline_da']:+.4f} Δb={c['fitline_db']:+.3f} "
              f"| 곡선재회귀 Δa={c['refit_da']:+.4f} Δb={c['refit_db']:+.3f}")
    fg = np.linspace(1.89, 18.03, 1200)
    pool = pooled_linear(cur, fg)
    print("\n창(window) 별 측정 기울기 [dB/GHz] (R²):")
    for lo, hi in [(1.89, 5.21), (1.89, 6.0), (1.89, 18.03)]:
        row = []
        for th, (f, mu) in cur.items():
            a, _, r2 = slope_in(f, mu, lo, hi)
            row.append(f"θ{th}={a:+.3f}({r2:+.2f})")
        a, _, r2 = slope_in(fg, pool, lo, hi)
        print(f"  [{lo:5.2f},{hi:5.2f}]  " + "  ".join(row) + f"  pooled={a:+.3f}({r2:+.2f})")
