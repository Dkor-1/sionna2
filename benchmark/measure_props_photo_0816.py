#!/usr/bin/env python
"""⭐ 프로펠러 평면형 정밀 계측 — DJI Mavic 4 Pro(1158F) · DJI Mini 5 Pro(6028F)  (2026-08-16)

왜 재는가
---------
`src/drone_cad.py` 는 날 폭 최대값을 `CHORD_MAX_OVER_R = 0.25` **단일 상수**로 10기종
전부에 걸고, 시위 분포 `CHORD_FRAC` 은 3DR Solo 하나에서 베낀 것이다. 실측 c_max/R 은
기종마다 1.5 배 벌어진다(docs/MESH_AUDIT_0816.md I2). 표적 신호의 움직이는 성분은 사실상
전부 프로펠러이므로(outputs/material_verdict_0816.json), 기종 비교(=분류)가 이 상수 하나
위에 서 있다. 그래서 «그 기체의 진짜 프롭» 을 각각 잰다.

이 파일이 재는 것 (계측만 — ⛔코드 무변경 · ⛔GPU 미사용 · ⛔git 미접촉)
-----------------------------------------------------------------------
  주력   : mavic4pro = DJI **1158F** (267 mm) · mini5pro = DJI **6028F** (152.4 mm)
  검증용 : DJI Mini 2 = **4726F** — 저장소에 유일한 DJI 공식 3D(GLB)와 그 **정투영 상면
           렌더**(mini2_d24)가 둘 다 있다. 같은 물건을 «3D 로 직접» 과 «사진 코드로» 재서
           자를 먼저 검증한다.
  참고   : Matrice 4E 1157F/1154F 제품컷 — 함대 전체를 **같은 자**로 놓기 위한 곁수치.

⭐ 규약 — 이게 다르면 비교가 무의미하다
--------------------------------------
R 의 정의   : **스윕 디스크 반경**. 회전중심 C 에서 날 끝까지의 거리.
              C = 2날 프롭의 두 날끝 **중점**. `outputs/reference_props.json` 의 R_disc/2
              와 같은 뜻이라 사과-대-사과다.
날 뿌리     : r_root = 각폭 곡선이 허브 덩어리를 벗어나 날 폭으로 **떨어지는** 반경(안쪽
              국소 최소). 요약 통계는 **max(0.25R, r_root+0.03R) ~ 0.96R** 만 쓴다.
              ⚠ 이 하한을 안 두면 허브가 «가장 넓은 시위» 로 잡혀 c_max/R 이 2 배로 뜬다.
시위 c(r)   : **두 정의를 구분한다.**
   (1) c_arc = r·Δθ  — 회전면에 **투영된** 폭. 사진(2D)이 줄 수 있는 것은 이것뿐이다.
   (2) c_cal = 반경 r 원통 단면의 최대 캘리퍼 — `measure_reference_props.py` 와
       `drone_cad` 의 시위. 날이 비틀려 있으므로 항상 c_cal ≥ c_arc.
   ⭐ 두 정의의 다리(c_cal/c_arc)를 Mini 2 공식 CAD 에서 실측해 환산계수로 남긴다.
   ⚠ 감사 문서가 사진값 0.181(투영)과 메쉬값 0.273(캘리퍼)을 같은 표에 나란히 적은 것은
      이 다리를 안 건넌 것이다.

⭐ 같은 양을 두 방법으로 (규약 요구사항)
---------------------------------------
  방법 A(극좌표) : 반경 밴드의 각폭 → c = r·Δθ
  방법 B(직교)   : 날을 스팬축으로 회전시켜 **열마다 수직 폭**
  두 방법의 0.3~0.9R 불일치를 날마다 보고한다. 문턱값도 ±15 흔들어 감도를 낸다.

⭐ 2날 평균이 필수인 이유 (이 라운드에서 새로 실측한 것)
------------------------------------------------------
날은 **비틀려** 있다. 시선이 회전축에서 벗어나면 한 날은 시위가 넓게, 반대 날은 좁게
찍힌다(1차항이 부호만 반대). 그래서 **한 프롭의 두 날 평균**이 1차 오차를 지운다.
남는 날간 비대칭 asym_pct = |w1-w2|/(w1+w2) 은 그 사진이 얼마나 비스듬한지의 계기판이다.

산출: outputs/prop_measure_mavic4pro_mini5pro_0816.json
실행: PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/measure_props_photo_0816.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path("/workspace/sionna")
PHOTO = ROOT / "assets/photos"
REF = ROOT / "assets/meshes/reference"
OUT = ROOT / "outputs/prop_measure_mavic4pro_mini5pro_0816.json"

GRID = np.round(np.arange(0.25, 0.9601, 0.05), 3)   # 비교 격자 r/R
RSTEP = 0.005
R_LO, R_HI = 0.12, 0.99
SUM_LO_FLOOR, SUM_HI = 0.25, 0.96                    # 요약 통계 구간


# ===================================================================== #
#  0. 실루엣
# ===================================================================== #
def _otsu(v):
    h, _ = np.histogram(v, bins=256, range=(0, 255))
    p = h / h.sum()
    w = np.cumsum(p)
    mu = np.cumsum(p * np.arange(256))
    sb = (mu[-1] * w - mu) ** 2 / np.maximum(w * (1 - w), 1e-12)
    return float(np.argmax(sb))


def silhouette(path, mode, thr=None):
    if mode == "alpha":                 # 투명 배경 렌더 — 알파가 곧 실루엣
        rgba = np.asarray(Image.open(path).convert("RGBA"))
        return rgba[..., 3] > 128, -1.0, rgba[..., :3].astype(float)
    a = np.asarray(Image.open(path).convert("RGB"), float)
    if mode == "dark_on_light":
        v = a.mean(axis=2)
        thr = _otsu(v) if thr is None else thr
        return v < thr, float(thr), a
    if mode == "not_blue":
        v = a[..., 2] - np.maximum(a[..., 0], a[..., 1])
        thr = 40.0 if thr is None else thr
        return v < thr, float(thr), a
    raise ValueError(mode)


def orange_tips(rgb, min_px=40):
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    m = (R > 120) & (R - B > 60) & (R - G > 25)
    lab, n = ndimage.label(m)
    if n == 0:
        return np.zeros((0, 2))
    sz = ndimage.sum(m, lab, range(1, n + 1))
    out = []
    for i in np.argsort(sz)[::-1]:
        if sz[i] < min_px:
            break
        ys, xs = np.where(lab == i + 1)
        out.append([xs.mean(), ys.mean()])
    return np.array(out, float)


def envelope_tips(mask, n_tips, sep_frac=0.22):
    """조립 상태 상면도 — 실루엣 중심에서 «가장 먼 점» 을 최소간격을 두고 차례로 고른다.
    날끝은 기체에서 가장 튀어나온 점들이라 이 탐욕법으로 안정적으로 잡힌다."""
    ys, xs = np.where(mask)
    P = np.c_[xs.astype(float), ys.astype(float)]
    c0 = P.mean(0)
    r = np.linalg.norm(P - c0, axis=1)
    order = np.argsort(r)[::-1]
    sep = sep_frac * float(r.max())
    picked = []
    for k in order:
        p = P[k]
        if all(np.linalg.norm(p - q) > sep for q in picked):
            picked.append(p)
        if len(picked) == n_tips:
            break
    return np.array(picked, float)


def isolated_tips(mask, n_props, min_frac=0.004):
    """따로 놓인 프롭 제품컷 — 성분마다 «가장 먼 두 점» 이 두 날끝."""
    lab, n = ndimage.label(mask)
    sz = ndimage.sum(mask, lab, range(1, n + 1))
    order = [i for i in np.argsort(sz)[::-1] if sz[i] > min_frac * mask.size][:n_props]
    tips = []
    for i in order:
        ys, xs = np.where(lab == i + 1)
        P = np.c_[xs.astype(float), ys.astype(float)]
        c = P.mean(0)
        p1 = P[int(np.argmax(np.linalg.norm(P - c, axis=1)))]
        p2 = P[int(np.argmax(np.linalg.norm(P - p1, axis=1)))]
        tips += [p1, p2]
    return np.array(tips, float)


# ===================================================================== #
#  1. 날끝 짝짓기
# ===================================================================== #
def _seg_coverage(mask, p, q, n=200):
    t = np.linspace(0.03, 0.97, n)[:, None]
    pts = p[None, :] * (1 - t) + q[None, :] * t
    xi = np.clip(np.round(pts[:, 0]).astype(int), 0, mask.shape[1] - 1)
    yi = np.clip(np.round(pts[:, 1]).astype(int), 0, mask.shape[0] - 1)
    return float(mask[yi, xi].mean())


def pair_tips(tips, mask):
    n = len(tips)
    best = [None, -1.0]

    def rec(rem, pairs, worst):
        if worst <= best[1]:
            return
        if not rem:
            best[0], best[1] = list(pairs), worst
            return
        i = rem[0]
        for j in rem[1:]:
            cov = _seg_coverage(mask, tips[i], tips[j])
            rec([k for k in rem[1:] if k != j], pairs + [(i, j, cov)], min(worst, cov))

    rec(list(range(n)), [], 1.0)
    return best[0], best[1]


# ===================================================================== #
#  2. 평면형
# ===================================================================== #
def _arcs(th, gap):
    s = np.sort(th)
    if len(s) < 2:
        return []
    d = np.diff(np.r_[s, s[0] + 2 * np.pi])
    g = np.where(d > gap)[0]
    if len(g) == 0:
        return [(float(s[0]), float(s[-1]))]
    out = []
    for k in range(len(g)):
        i0 = (g[k] + 1) % len(s)
        i1 = g[(k + 1) % len(g)]
        seg = s[i0:i1 + 1] if i0 <= i1 else np.r_[s[i0:], s[:i1 + 1] + 2 * np.pi]
        if len(seg) >= 2:
            out.append((float(seg[0]), float(seg[-1])))
    return out


def blade_polar(P, C, R, th_tip, band_px=2.5, gap_deg=14.0, min_pts=5,
                grow_limit=None):
    """방법 A — 날끝에서 안쪽으로 «각도 추적».

    허브 오염은 추적을 끊는 대신 **요약 구간의 하한**(r_root+0.03, 최소 0.25R)으로 막는다.
    끊는 방식은 팁 근처의 1 px 요동에도 걸려 곡선을 잘라먹었다(이 라운드에서 실측).
    """
    d = P - C
    r = np.hypot(d[:, 0], d[:, 1])
    th = np.arctan2(d[:, 1], d[:, 0])
    rr = np.round(np.arange(R_HI, R_LO - 1e-9, -RSTEP), 4)
    band = band_px
    c = np.full(len(rr), np.nan)
    prev_th = th_tip
    prev_c = None
    sel_mask = np.zeros(len(P), bool)
    for i, x in enumerate(rr):
        m = np.abs(r - x * R) < band
        if m.sum() < min_pts:
            continue
        tt = th[m]
        aa = _arcs(tt, np.radians(gap_deg))
        if not aa:
            continue

        def gap_to_prev(a):
            e = abs(np.angle(np.exp(1j * (0.5 * (a[0] + a[1]) - prev_th))))
            return max(0.0, e - 0.5 * (a[1] - a[0]))

        k = int(np.argmin([gap_to_prev(a) for a in aa]))
        if gap_to_prev(aa[k]) > np.radians(25.0):
            continue
        lo, hi = aa[k]
        cw = x * R * (hi - lo)
        if grow_limit and prev_c is not None and cw > grow_limit * prev_c:
            break                                   # 허브에 먹혔다 — 여기서 끊는다
        c[i] = cw
        prev_c = cw
        prev_th = float(np.angle(np.exp(1j * 0.5 * (lo + hi))))
        sel = np.zeros(int(m.sum()), bool)
        for sh in (0.0, 2 * np.pi, -2 * np.pi):
            sel |= (tt + sh >= lo - 1e-12) & (tt + sh <= hi + 1e-12)
        sel_mask[np.where(m)[0][sel]] = True
    return rr[::-1], c[::-1], sel_mask


def blade_cartesian(P, C, R, tip, bin_px=2.0):
    """방법 B — 스팬축(C→tip)으로 회전시켜 열마다 수직 폭. 표본 방식이 A 와 다르다."""
    e = (tip - C) / np.linalg.norm(tip - C)
    n = np.array([-e[1], e[0]])
    d = P - C
    s, t = d @ e, d @ n
    rr = np.round(np.arange(R_LO, R_HI + 1e-9, RSTEP), 4)
    c = np.full(len(rr), np.nan)
    for i, x in enumerate(rr):
        m = np.abs(s - x * R) < bin_px
        if m.sum() < 4:
            continue
        c[i] = float(t[m].max() - t[m].min())
    return rr, c


def root_radius(rr, c):
    """허브를 벗어나는 반경 = 안쪽(<0.45R) 각폭 곡선의 국소 최소."""
    ok = np.isfinite(c) & (rr < 0.45)
    if ok.sum() < 4:
        return None
    x, y = rr[ok], c[ok]
    return float(x[int(np.argmin(y))])


def summarize(rr, c, R, lo=None, label=""):
    """⭐ 품질 문턱: 0.35~0.90R 을 **끊김 없이** 덮지 못하면 None (가림·잘림 표본을 버린다)."""
    lo = SUM_LO_FLOOR if lo is None else max(SUM_LO_FLOOR, lo)
    ok = np.isfinite(c) & (rr >= lo) & (rr <= SUM_HI)
    if ok.sum() < 8:
        return None
    core = np.isfinite(c) & (rr >= 0.35) & (rr <= 0.90)
    n_core = int(((rr >= 0.35) & (rr <= 0.90)).sum())
    if core.sum() < 0.92 * n_core:
        return None
    x, y = rr[ok], c[ok]
    cmax = float(y.max())
    return dict(
        label=label,
        c_max_over_R=cmax / R,
        peak_r_over_R=float(x[int(np.argmax(y))]),
        c_over_cmax={f"{g:.2f}": (float(np.interp(g, x, y)) / cmax
                                  if x[0] <= g <= x[-1] else None) for g in GRID},
        c_over_R={f"{g:.2f}": (float(np.interp(g, x, y)) / R
                               if x[0] <= g <= x[-1] else None) for g in GRID},
        area_over_R2=float(np.trapezoid(y / R, x)),
        area_centroid_r_over_R=float(np.trapezoid(y * x, x) / np.trapezoid(y, x)),
        outboard_share_0p6=float(np.trapezoid(y[x >= 0.6], x[x >= 0.6])
                                 / np.trapezoid(y, x)),
        r_range=[float(x[0]), float(x[-1])],
    )


# ===================================================================== #
#  3. 어파인 정류
# ===================================================================== #
def fit_rectify(vecs):
    V = np.asarray(vecs, float)
    if len(V) < 3:
        return np.eye(2), dict(applied=False, n_props=int(len(V)),
                               reason_ko="프롭 3개 미만 — 정류 지렛대가 없다")

    def S_of(p):
        phi, lk = p
        k = np.exp(lk)
        Rm = np.array([[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]])
        return Rm @ np.diag([k, 1.0 / k]) @ Rm.T

    def cost(p):
        q = np.einsum("ij,jk,ik->i", V, S_of(p), V)
        return float(np.std(q) / np.mean(q))

    best, bp = 1e9, (0.0, 0.0)
    for phi in np.linspace(0, np.pi, 91):
        for lk in np.linspace(-0.6, 0.6, 121):
            cc = cost((phi, lk))
            if cc < best:
                best, bp = cc, (phi, lk)
    p = np.array(bp, float)
    step = np.array([np.pi / 90, 0.01])
    for _ in range(500):
        moved = False
        for j in (0, 1):
            for sg in (+1, -1):
                q = p.copy()
                q[j] += sg * step[j]
                cq = cost(q)
                if cq < best:
                    best, p, moved = cq, q, True
        if not moved:
            step *= 0.5
            if step.max() < 1e-7:
                break
    S = S_of(p)
    w, U = np.linalg.eigh(S)
    W = U @ np.diag(np.sqrt(w)) @ U.T
    W = W / np.sqrt(np.linalg.det(W))
    raw = np.linalg.norm(V, axis=1)
    rec = np.linalg.norm(V @ W.T, axis=1)
    return W, dict(
        applied=True, n_props=int(len(V)),
        stretch_ratio=float(np.exp(abs(p[1]))),
        stretch_axis_deg=float(np.degrees(p[0]) % 180.0),
        tip2tip_px_raw=[float(v) for v in raw],
        tip2tip_spread_raw_pct=float(100 * raw.std() / raw.mean()),
        tip2tip_spread_rectified_pct=float(100 * rec.std() / rec.mean()),
        meaning_ko=("끝점-끝점 길이는 참평면에서 전부 D 로 같아야 한다. 그 조건으로 찌그러짐을 "
                    "푼다. stretch_ratio 1.00 = 완전한 평면도."),
    )


# ===================================================================== #
#  4. 사진 한 장
# ===================================================================== #
def measure_photo(path, mode, n_props, thr=None, tips="orange", rectify=True,
                  label="", grade=""):
    mask, thr_used, rgb = silhouette(path, mode, thr)
    T, tips_used = None, tips
    if tips == "orange":
        o = orange_tips(rgb)
        if len(o) >= 2 * n_props:
            T, tips_used = o[: 2 * n_props], "orange"
    if T is None:
        if tips == "isolated":
            T, tips_used = isolated_tips(mask, n_props), "isolated"
        else:
            T, tips_used = envelope_tips(mask, 2 * n_props), "envelope"
    if len(T) != 2 * n_props:
        return dict(file=Path(path).name, error=f"날끝 {len(T)}개 (필요 {2*n_props})")

    pairs, worst = pair_tips(T, mask)
    ys, xs = np.where(mask)
    P = np.c_[xs.astype(float), ys.astype(float)]
    props0 = [dict(t1=T[i], t2=T[j], cov=float(c)) for (i, j, c) in pairs]
    W, rect = (fit_rectify([p["t2"] - p["t1"] for p in props0]) if rectify
               else (np.eye(2), dict(applied=False, reason_ko="요청 안 함")))

    frames = {}
    for fname, M in (("raw", np.eye(2)), ("rectified", W)):
        if fname == "rectified" and not rect.get("applied"):
            continue
        Pm = P @ M.T
        out = []
        for pi, p0 in enumerate(props0):
            t1, t2 = p0["t1"] @ M.T, p0["t2"] @ M.T
            C = 0.5 * (t1 + t2)
            Rpx = float(0.5 * (np.linalg.norm(t1 - C) + np.linalg.norm(t2 - C)))
            bl, prof = [], []
            for bi, tp in enumerate((t1, t2)):
                th = float(np.arctan2(*(tp - C)[::-1]))
                rrA, cA, sel = blade_polar(Pm, C, Rpx, th)
                rrB, cB = blade_cartesian(Pm[sel] if sel.sum() > 40 else Pm, C, Rpx, tp)
                rroot = root_radius(rrA, cA)
                sA = summarize(rrA, cA, Rpx, (rroot + 0.03) if rroot else None,
                               "A_polar")
                sB = summarize(rrB, cB, Rpx, (rroot + 0.03) if rroot else None,
                               "B_cartesian")
                if sA is None:
                    continue
                g = np.arange(0.35, 0.9001, 0.02)
                oa, ob = np.isfinite(cA), np.isfinite(cB)
                if oa.sum() > 8 and ob.sum() > 8:
                    aa = np.interp(g, rrA[oa], cA[oa])
                    bb = np.interp(g, rrB[ob], cB[ob])
                    dmax = float(np.max(np.abs(aa - bb) / aa) * 100)
                    dmean = float(np.mean(np.abs(aa - bb) / aa) * 100)
                else:
                    dmax = dmean = None
                bl.append(dict(blade=bi, r_root_over_R=rroot,
                               A_polar=sA, B_cartesian=sB,
                               AB_diff_pct_mean=dmean, AB_diff_pct_max=dmax))
                prof.append((rrA, cA, rroot))
            if len(prof) != 2:
                out.append(dict(prop=pi, error="날 2장을 못 잼", blades=bl))
                continue
            rr = prof[0][0]
            cavg = np.nanmean(np.vstack([prof[0][1], prof[1][1]]), axis=0)
            lo = max([q[2] for q in prof if q[2] is not None] or [None])
            savg = summarize(rr, cavg, Rpx, (lo + 0.03) if lo else None, "two_blade_mean")
            w1 = bl[0]["A_polar"]["c_max_over_R"]
            w2 = bl[1]["A_polar"]["c_max_over_R"]
            out.append(dict(
                prop=pi, R_px=Rpx, tip_pair_coverage=p0["cov"],
                blades=bl, two_blade_mean=savg,
                blade_asym_pct=float(100 * abs(w1 - w2) / (w1 + w2)),
                faceon_proxy=float(savg["c_max_over_R"] * Rpx * Rpx) if savg else None,
            ))
        frames[fname] = out

    res = dict(file=Path(path).name, label=label, grade=grade, mode=mode,
               threshold=thr_used, tips_from=tips_used,
               tip_pairing_worst_coverage=float(worst),
               rectify=rect, frames=frames)
    for fname, out in frames.items():
        v = np.array([o["two_blade_mean"]["c_max_over_R"] for o in out
                      if o.get("two_blade_mean")])
        if len(v):
            res.setdefault("summary", {})[fname] = dict(
                c_max_over_R_mean=float(v.mean()),
                c_max_over_R_sd=float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                c_max_over_R_min=float(v.min()), c_max_over_R_max=float(v.max()),
                spread_pct=float(100 * (v.max() - v.min()) / v.mean()),
                n_props=int(len(v)),
                best_prop_faceon=int(np.argmax([o.get("faceon_proxy") or -1
                                                for o in out])),
                c_max_over_R_best_faceon=float(
                    out[int(np.argmax([o.get("faceon_proxy") or -1 for o in out]))]
                    ["two_blade_mean"]["c_max_over_R"]),
                blade_asym_pct=[round(o["blade_asym_pct"], 2) for o in out
                                if "blade_asym_pct" in o],
            )
    return res


# ===================================================================== #
#  5. Mini 2 공식 CAD (3D)
# ===================================================================== #
def _sample_surface(v, f, n=240_000, seed=0):
    rng = np.random.default_rng(seed)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    tot = area.sum()
    cnt = rng.multinomial(n, area / tot)
    idx = np.repeat(np.arange(len(f)), cnt)
    u1, u2 = rng.random(len(idx)), rng.random(len(idx))
    su = np.sqrt(u1)
    p = ((1 - su)[:, None] * a[idx] + (su * (1 - u2))[:, None] * b[idx]
         + (su * u2)[:, None] * c[idx])
    return np.vstack([v[np.unique(f)], p])


def _mini2_blades():
    import trimesh
    s = trimesh.load(str(REF / "WM161_zhankai_1k.glb"), process=False, force="scene")
    bl = []
    for node in s.graph.nodes_geometry:
        T, gn = s.graph[node]
        g = s.geometry[gn]
        if not hasattr(g, "faces") or len(g.faces) not in (1635, 1691):
            continue
        v = trimesh.transform_points(np.asarray(g.vertices, float), T)
        bl.append((node, v, np.asarray(g.faces, int)))
    return bl


def mini2_cad():
    """회전축 = 월드 +y(감사 실측). 평면 = (x, z). 두 정의(arc·caliper)를 같이 낸다."""
    bl = _mini2_blades()
    if len(bl) != 8:
        return dict(error=f"날 {len(bl)}장 (8 예상)")
    S = [_sample_surface(v, f) for _, v, f in bl]
    ctr = np.array([p[:, [0, 2]].mean(0) for p in S])
    used, rotors = set(), []
    for i in range(8):
        if i in used:
            continue
        d = [np.linalg.norm(ctr[i] - ctr[j]) if (j not in used and j != i) else 1e9
             for j in range(8)]
        j = int(np.argmin(d))
        used |= {i, j}
        rotors.append((i, j))
    res = []
    for (i, j) in rotors:
        # 회전중심: 두 날끝의 중점으로 수렴
        C = 0.5 * (ctr[i] + ctr[j])
        for _ in range(6):
            Pi, Pj = S[i][:, [0, 2]], S[j][:, [0, 2]]
            ti = Pi[int(np.argmax(np.linalg.norm(Pi - C, axis=1)))]
            tj = Pj[int(np.argmax(np.linalg.norm(Pj - C, axis=1)))]
            C = 0.5 * (ti + tj)
        R = float(0.5 * (np.linalg.norm(ti - C) + np.linalg.norm(tj - C)))
        for k in (i, j):
            p2 = S[k][:, [0, 2]] - C
            y = S[k][:, 1]
            r = np.hypot(p2[:, 0], p2[:, 1])
            th = np.arctan2(p2[:, 1], p2[:, 0])
            rr = np.round(np.arange(R_LO, R_HI + 1e-9, RSTEP), 4)
            ca = np.full(len(rr), np.nan)
            cc = np.full(len(rr), np.nan)
            for a, x in enumerate(rr):
                m = np.abs(r - x * R) < 0.005 * R
                if m.sum() < 30:
                    continue
                aa = _arcs(th[m], np.radians(14.0))
                if not aa:
                    continue
                lo, hi = max(aa, key=lambda t: t[1] - t[0])
                ca[a] = x * R * (hi - lo)
                ref = 0.5 * (lo + hi)
                tl = ref + np.angle(np.exp(1j * (th[m] - ref)))
                Q = np.c_[x * R * tl, y[m]]
                if len(Q) > 700:
                    Q = Q[np.random.default_rng(0).choice(len(Q), 700, replace=False)]
                cc[a] = float(np.linalg.norm(Q[:, None] - Q[None], axis=2).max())
            rroot = root_radius(rr, ca)
            lo0 = (rroot + 0.03) if rroot else None
            sa = summarize(rr, ca, R, lo0, "plan_projected_arc")
            sc = summarize(rr, cc, R, lo0, "cylindrical_caliper")
            if not (sa and sc):
                continue
            g = np.arange(0.35, 0.9001, 0.02)
            oa, oc = np.isfinite(ca), np.isfinite(cc)
            ratio = np.interp(g, rr[oc], cc[oc]) / np.interp(g, rr[oa], ca[oa])
            res.append(dict(blade=bl[k][0], R_m=R, disc_dia_mm=2000.0 * R,
                            r_root_over_R=rroot, arc=sa, caliper=sc,
                            cal_over_arc_mean=float(ratio.mean()),
                            cal_over_arc_at={f"{x:.2f}": float(np.interp(x, g, ratio))
                                             for x in (0.4, 0.5, 0.7, 0.9)}))
    if not res:
        return dict(error="측정 실패")
    arc = np.array([b["arc"]["c_max_over_R"] for b in res])
    cal = np.array([b["caliper"]["c_max_over_R"] for b in res])
    bridge = np.array([b["cal_over_arc_mean"] for b in res])
    return dict(n_blades=len(res), blades=res, summary=dict(
        disc_dia_mm=float(np.mean([b["disc_dia_mm"] for b in res])),
        arc_c_max_over_R=dict(mean=float(arc.mean()), sd=float(arc.std(ddof=1))),
        caliper_c_max_over_R=dict(mean=float(cal.mean()), sd=float(cal.std(ddof=1))),
        cal_over_arc=dict(mean=float(bridge.mean()), sd=float(bridge.std(ddof=1))),
        meaning_ko=("cal_over_arc = «원통 캘리퍼 시위 ÷ 회전면 투영 폭». 사진으로 잰 값에 "
                    "이 계수를 곱해야 drone_cad·reference_props 의 시위와 같은 축이 된다."),
    ))


# ===================================================================== #
#  5b. FCC 실기체 톱 평면 (프롭 접힘) — 척도 없는 형상비
# ===================================================================== #
def fcc_folded_blades(level=52.0, min_px=1200, min_elong=2.5):
    """mavic4pro p01 (FCC 시험소 톱 평면, 프롭 접힘, 자 포함).

    ⭐ 왜 이 사진이 특별한가: **실기체를 위에서 곧게 내려다본 시험소 컷**이라 렌더보다
    기울기가 작다. 접힘은 날을 힌지 둘레로 **회전면 안에서** 돌린 것이라 날 자체의
    평면형은 그대로다.

    ⛔ 어려운 점: 두 날이 겹쳐 쌓인다. 그래서 여기서 내는 것은 **척도 없는 형상비**
        aspect = w_max / s_peak
      w_max  = 날 축에 수직인 최대 폭
      s_peak = **날끝에서** 그 최대 폭이 나오는 지점까지의 거리
    접힘과 무관한 날 고유의 수다. 펼친 상태에서 r = R - s 이므로
        c_max/R = aspect × (1 - r_peak/R)
    로 환산된다(r_peak/R 은 렌더 계측에서 가져온다).
    겹친 성분은 **상한**, 잘 갈라진 성분은 **점추정**으로 표시한다.
    """
    p = PHOTO / "mavic4pro/mavic4pro_p01_fcc_top_plan_ruler.jpg"
    a = np.asarray(Image.open(p).convert("RGB"), float)
    lum = a.mean(axis=2)
    blue = a[..., 2] - np.maximum(a[..., 0], a[..., 1])
    obj = blue < 40
    lab, n = ndimage.label(obj)
    sz = ndimage.sum(obj, lab, range(1, n + 1))
    # 기체 = 화면 안쪽에 갇힌 가장 큰 성분(바깥 성분은 자·테두리)
    drone = None
    for i in np.argsort(sz)[::-1][:5]:
        ys, xs = np.where(lab == i + 1)
        if xs.min() > 20 and ys.min() > 20 and xs.max() < obj.shape[1] - 20 \
                and ys.max() < obj.shape[0] - 20:
            drone = (lab == i + 1)
            break
    if drone is None:
        return dict(error="기체 성분을 못 찾음")
    bl = drone & (lum < level)
    lb, nn = ndimage.label(bl)
    s = ndimage.sum(bl, lb, range(1, nn + 1))
    out = []
    for i in np.argsort(s)[::-1]:
        if s[i] < min_px:
            break
        ys, xs = np.where(lb == i + 1)
        P = np.c_[xs, ys].astype(float)
        c = P.mean(0)
        X = P - c
        w, V = np.linalg.eigh(X.T @ X / len(X))
        elong = float(np.sqrt(w[1] / max(w[0], 1e-12)))
        if elong < min_elong:
            continue
        e = V[:, 1]
        nvec = np.array([-e[1], e[0]])
        sv = X @ e
        tv = X @ nvec
        if abs(sv.max()) < abs(sv.min()):     # 뾰족한 끝(팁)을 +s 로
            sv, tv = -sv, -tv
        # 팁 = 폭이 가장 좁아지는 끝. 두 끝의 국소 폭으로 판정
        def width_at(x, hw=3.0):
            m = np.abs(sv - x) < hw
            return float(tv[m].max() - tv[m].min()) if m.sum() > 3 else np.nan
        if width_at(sv.max() - 6) > width_at(sv.min() + 6):
            sv, tv = -sv, -tv
        s0 = sv.max()                          # 팁
        grid = np.arange(2.0, s0 - sv.min() - 2.0, 1.0)
        wid = np.array([width_at(s0 - g) for g in grid])
        ok = np.isfinite(wid)
        if ok.sum() < 20:
            continue
        g, wq = grid[ok], wid[ok]
        k = int(np.argmax(wq))
        out.append(dict(
            n_px=int(s[i]), centroid=[float(c[0]), float(c[1])],
            elongation=elong, span_px=float(s0 - sv.min()),
            w_max_px=float(wq[k]), s_peak_px=float(g[k]),
            aspect_w_over_speak=float(wq[k] / g[k]),
        ))
    return dict(level=level, n_components=len(out), components=out,
                caveat_ko=("두 날이 겹치면 폭이 부풀어 **상한**이 된다. 아래 표에서 "
                           "aspect 가 작은 성분이 잘 갈라진 단일 날에 가깝다."))


# ===================================================================== #
#  6. main
# ===================================================================== #
def main():
    t0 = time.time()
    doc = {"_meta": {
        "title": "프로펠러 평면형 정밀 계측 — Mavic 4 Pro 1158F · Mini 5 Pro 6028F",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M",
                                       time.localtime(time.time() + 9 * 3600)),
        "script": "benchmark/measure_props_photo_0816.py",
        "python": "/workspace/.venvs/py312/bin/python",
        "policy": "⛔코드 무변경 · ⛔GPU 미사용 · ⛔git 미접촉",
        "R_definition_ko": ("R = 스윕 디스크 반경 = 회전중심 C 에서 날 끝까지. "
                            "C = 2날 프롭의 두 날끝 중점. reference_props.json 의 "
                            "R_disc/2 와 같은 뜻."),
        "root_definition_ko": ("r_root = 각폭 곡선이 허브를 벗어나는 반경(안쪽 국소 최소). "
                               "요약은 max(0.25R, r_root+0.03R)~0.96R 만 쓴다."),
        "chord_definitions_ko": {
            "c_arc": "r·Δθ — 회전면 투영 폭. 사진이 줄 수 있는 유일한 값.",
            "c_caliper": "반경 r 원통 단면의 최대 캘리퍼 — drone_cad/reference_props 의 시위.",
            "bridge": "A 절의 cal_over_arc 가 두 축을 잇는 계수(Mini 2 공식 CAD 실측).",
        },
        "two_methods_ko": "A=극좌표 각폭, B=직교 스팬축 열폭. 날마다 AB_diff_pct 를 적는다.",
    }}

    # --- A. 자 검증 ---------------------------------------------------- #
    A = {"why_ko": ("새 대상에 대기 전에 답을 아는 물건으로 자를 검증한다. Mini 2 는 "
                    "저장소에 공식 3D(GLB)와 그 **정투영 상면 렌더**가 둘 다 있다.")}
    # 3D 캘리퍼는 느리다(원통단면×쌍거리). 이미 성공한 결과가 있으면 재사용한다.
    cached = None
    if OUT.exists() and "--fresh" not in __import__("sys").argv:
        try:
            old = json.loads(OUT.read_text())
            c = old["A_ruler_validation"]["cad_direct_3d"]
            if "error" not in c:
                cached = c
        except Exception:
            cached = None
    A["cad_direct_3d"] = cached if cached else mini2_cad()
    A["cad_direct_3d_from_cache"] = bool(cached)
    A["cad_top_render_through_photo_pipeline"] = measure_photo(
        PHOTO / "mini2/mini2_d24_officialcad_unfolded_top.png", "alpha", 4,
        thr=None, tips="envelope", label="Mini 2 공식 CAD 정투영 상면 렌더", grade="검증")
    try:
        a3 = A["cad_direct_3d"]["summary"]["arc_c_max_over_R"]["mean"]
        ph = A["cad_top_render_through_photo_pipeline"]["summary"]["raw"]["c_max_over_R_mean"]
        A["verdict"] = dict(
            cad_direct_arc=a3, photo_pipeline_on_same_object=ph,
            error_pct=float(100 * (ph - a3) / a3),
            note_ko=("같은 물건(4726F)을 «3D 직접» 과 «사진 코드» 로 잰 차이 = 이 자의 정확도. "
                     "두 값 모두 투영(arc) 정의라 사과-대-사과다."))
    except Exception as e:                                    # pragma: no cover
        A["verdict"] = {"error": repr(e)}
    doc["A_ruler_validation"] = A

    # --- B. mini5pro 6028F ---------------------------------------------- #
    B = {"identity": dict(
        prop="6028F", dia_mm=152.4, pitch_mm=71.12, pitch_in=2.8, blades=2,
        folding=True, mass_g_each=2.8, material="Nylon + Rubber",
        source_ko="DJI 공식 프롭 표 + DJI 스토어 제품 페이지 (outputs/prop_identity_0816.json)")}
    B["primary"] = measure_photo(
        PHOTO / "mini5pro/mini 5 pro_3.png", "dark_on_light", 4, thr=110.0,
        label="[B] DJI 공식 렌더 상면 — 프롭 4개 전개", grade="B")
    for th in (95.0, 125.0):
        B[f"threshold_{int(th)}"] = measure_photo(
            PHOTO / "mini5pro/mini 5 pro_3.png", "dark_on_light", 4, thr=th,
            label=f"문턱값 감도 {th:.0f}", grade="B")
    doc["B_mini5pro_6028F"] = B

    # --- C. mavic4pro 1158F --------------------------------------------- #
    C = {"identity": dict(
        prop="1158F", dia_mm=267.0, pitch_mm=147.0, pitch_in=5.8, blades=2,
        folding=True, mass_g_each=11.8, material="Enhanced Nylon Composite",
        source_ko="DJI 공식 프롭 표 (26.7×14.7 cm) (outputs/prop_identity_0816.json)")}
    C["primary"] = measure_photo(
        PHOTO / "mavic4pro/mavic 4 pro_3.png", "dark_on_light", 4, thr=110.0,
        label="[B] DJI 공식 렌더 상면(기울어짐) — 프롭 4개", grade="B")
    for th in (95.0, 125.0):
        C[f"threshold_{int(th)}"] = measure_photo(
            PHOTO / "mavic4pro/mavic 4 pro_3.png", "dark_on_light", 4, thr=th,
            label=f"문턱값 감도 {th:.0f}", grade="B")
    C["render34"] = measure_photo(
        PHOTO / "mavic4pro/mavic 4 pro_4.png", "dark_on_light", 4, thr=110.0,
        label="[B-] DJI 공식 렌더 3/4 — 더 비스듬함", grade="B-")
    C["product_pair_c10"] = measure_photo(
        PHOTO / "mavic4pro/mavic4pro_c10_propeller_pair_1158F.jpg", "dark_on_light", 2,
        thr=None, tips="isolated",
        label="[B-] 제품컷 1158F 1쌍 — 사선, 프롭 2개라 정류 불가", grade="B-")
    C["fcc_top_plan_folded"] = fcc_folded_blades()
    doc["C_mavic4pro_1158F"] = C

    # --- D. 함대 곁수치 (같은 자) ---------------------------------------- #
    D = {"why_ko": "주력 두 기종의 수를 «같은 자로 잰 다른 DJI 프롭» 옆에 놓아야 뜻이 생긴다."}
    D["m4e_1157F_product"] = measure_photo(
        PHOTO / "matrice4e/matrice4e_c02_prop_standard_1157F_pair.jpg",
        "dark_on_light", 2, thr=None, tips="isolated",
        label="Matrice 4E 표준 1157F 제품컷", grade="B")
    D["m4e_1154F_product"] = measure_photo(
        PHOTO / "matrice4e/matrice4e_c01_prop_low_noise_1154F_pair.jpg",
        "dark_on_light", 2, thr=None, tips="isolated",
        label="Matrice 4E 저소음 1154F 제품컷", grade="B")
    doc["D_fleet_same_ruler"] = D

    doc["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    print("wrote", OUT, f"({OUT.stat().st_size/1024:.0f} KB, {doc['_meta']['runtime_s']} s)")
    return doc


if __name__ == "__main__":
    main()
