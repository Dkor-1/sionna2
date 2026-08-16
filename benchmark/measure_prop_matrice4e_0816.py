#!/usr/bin/env python
"""⭐ DJI Matrice 4E 프로펠러 정밀 계측 — 사진 계측 (2026-08-16)

왜 하는가
  같은 날 재질 판정이 «표적 신호의 움직이는 성분은 사실상 전부 프로펠러» 라고 실측했다
  (프롭 두께 0.9 mm 에서 요동 −16.99 dB, 셸 두께는 ±0.00 dB). 그런데 코드는 10기종
  전부에 `CHORD_MAX_OVER_R = 0.25` 라는 **단일 상수**를 걸고, 평면형(시위 분포)도
  3DR Solo 하나에서 베껴 쓴다. matrice4e 는 주력 표적 1순위인데 공식 CAD
  (`assets/meshes/reference/matrice4-M4T_v2.step`)에 **프로펠러가 아예 없다**
  (`outputs/meshfix_matrice4e.json`) → 사진 계측이 최선이다.

⭐ 정의를 먼저 못 박는다 — 이게 다르면 비교가 무의미하다
  · **회전축 O**   프롭 허브의 «모터 축 구멍» 중심.
                   접이식 프롭은 날마다 **경첩 핀**이 따로 있고 두 핀은 축에 대해
                   대칭이다(안 그러면 불균형) → **두 핀 구멍의 중점 = O**. 제품 렌더에서
                   두 핀 구멍은 배경색 구멍으로 보이므로 부분픽셀로 잡힌다.
                   교차검사: 실루엣의 **2회 회전대칭(C2) 중심**을 따로 구해 비교한다.
  · **R (반경)**   O 에서 그 날의 끝까지의 최대 거리 = 스윕 디스크 반경. **날마다 따로**.
  · **날 뿌리**    두 날의 실루엣이 각도로 분리되기 시작하는 반경 `r_split/R` 과
                   경첩 반경 `e/R` 을 둘 다 적는다. 시위 표는 분리된 구간에서만 유효하다.
  · **시위(chord)** 세 가지를 **동시에** 낸다. 서로 다른 양이고 서로 다른 답을 준다:
      c_arc(r) = r·Δθ(r)     반경 r 에서 날 실루엣의 각폭 × r.
                 ⭐이것이 **회전면에 투영된 날 폭**이고 c_arc = c_true·cos β 가
                 **정확히** 성립한다(β = 국소 피치각). 스윕(날의 휘어짐)은 이 관계를
                 바꾸지 않는다 — 단면은 어차피 반경 r 원통 위에서 잘리기 때문이다.
      c_str(r) = 2r·sin(Δθ/2)  같은 두 점의 **직선** 거리(투영).
      c_cal(r) = 국소 스팬축에 **수직**한 캘리퍼 폭. 감사(docs/MESH_AUDIT_0816.md)가
                 쓴 정의라 연속성을 위해 같이 낸다. 스윕이 있으면 c_arc 보다 작다.
  · **c_true(r) = c_arc(r)/cos β(r)**  익형 시위의 복원. β 는 공표 피치에서 오는
                 **가정**이라 세 가지 k(r) 법으로 밴드를 낸다(DERIVED).
  · **면적**      투영 평면형 면적 = ∫ c_arc dr (극좌표 적분이라 **정확**하다).

축척(자)
  사진 안에 물리 자가 없다. 공칭 지름 **274 mm**(레지스트리 `prop_dia_mm`;
  DJI 공표 «10.8 inch» = 274.32 mm → 쓰면 전 결과 +0.12 %)를 자로 쓴다.
  ⇒ **비율(c/R)은 자와 무관하고, mm 값만 자에 걸린다.**

원근·기울기 보정
  제품 렌더는 «거의» 정투영이지만 확인해야 한다. 이 스크립트는 두 축으로 잡는다:
   (1) **날 짝 비대칭** — 프롭이 τ 만큼 기울면 두 날의 투영 시위가
       c·cos(β−τ⊥) 와 c·cos(β+τ⊥) 로 **갈라진다**(1차 유도는 아래 `tilt_model` 참고).
       ⇒ 갈라짐의 크기가 곧 기울기이고, **두 날의 평균은 τ 의 2차까지 무편향**이다.
   (2) **기체 상면 렌더** — 프롭 4개가 **서로 다른 방위각**에 있으므로 공통 기울기가
       있으면 방위각에 따라 체계적으로 변한다. 4프롭 × 2날 = 8날로 교차검사한다.

⛔ GPU 미사용 · ⛔ git 무접촉 · ⛔ 저장소 코드 무변경(이 파일은 **추가**다).
   numpy / scipy / PIL 만 쓴다.

재현
  PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
      benchmark/measure_prop_matrice4e_0816.py
산출: outputs/prop_measure_matrice4e_0816.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage, optimize

ROOT = Path("/workspace/sionna")
PHOTO = ROOT / "assets/photos/matrice4e"
OUT = ROOT / "outputs/prop_measure_matrice4e_0816.json"

NOMINAL_DIA_MM = 274.0          # 레지스트리 prop_dia_mm (DJI «10.8 in» = 274.32)
NOMINAL_PITCH_IN = 5.7          # ⚠ DJI 미공표. 부품번호 1157F 뒷자리 해석(DERIVED)
MM_PER_IN = 25.4

RGRID = np.round(np.arange(0.10, 0.9951, 0.005), 4)      # r/R 격자
REPORT_RR = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60,
             0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.98]
BANDS = ((0.15, 0.96), (0.20, 0.96), (0.25, 0.95), (0.30, 0.96),
         (0.50, 0.96), (0.60, 0.96), (0.70, 0.96), (0.80, 0.96))


# ===================================================================== #
#  0. 기본 도구
# ===================================================================== #
def bilinear(A: np.ndarray, x, y):
    H, W = A.shape
    x = np.clip(np.asarray(x, float), 0, W - 1.001)
    y = np.clip(np.asarray(y, float), 0, H - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x0 + 1] * fx * (1 - fy)
            + A[y0 + 1, x0] * (1 - fx) * fy + A[y0 + 1, x0 + 1] * fx * fy)


def _run_bounds(inside: np.ndarray, i_ref: int, wrap: bool):
    n = len(inside)
    if not inside[i_ref % n]:
        return None
    i0 = i_ref
    while (inside[(i0 - 1) % n] if wrap else (i0 > 0 and inside[i0 - 1])):
        i0 -= 1
        if i_ref - i0 >= n:
            return None
    i1 = i_ref
    while (inside[(i1 + 1) % n] if wrap else (i1 < n - 1 and inside[i1 + 1])):
        i1 += 1
        if i1 - i_ref >= n:
            return None
    return i0, i1


def measure_run(L, xs, ys, inside, i_ref, wrap, ds, edge_frac=0.5, pad_px=3.0):
    """스캔 경로 위의 «물체 구간» 폭을 **두 가지 독립한 방법**으로 잰다.

    ⭐왜 이렇게까지 하나 — 시위는 45 px 인데 반경은 228 px 다. 가장자리를 한 화소
      안쪽/바깥쪽으로 잘못 잡으면 c/R 이 **4 % 움직인다.** 단순 이진화(문턱값)는
      «반투명 가장자리 화소» 를 통째로 넣거나 통째로 버리므로 그만큼 틀린다.

    ① `w_cov` — **피복률 적분**.  가장자리 화소의 밝기는 그 화소가 물체에 덮인
       비율 α 에 (거의) 비례한다. α = (b − L)/(b − m) 를 구간 양옆 3 px 까지 포함해
       적분하면 «흐릿한 가장자리» 가 저절로 상쇄된다. 문턱값에 거의 안 걸린다.
       b = 국소 배경(양쪽을 선형 혼합 — 한쪽이 흰 종이, 다른 쪽이 회색 암이어도 된다),
       m = 구간 안쪽의 가장 짙은 부분.
    ② `w_lev` — **50 % 밝기 교차점**.  같은 b, m 으로 lev = b + (m−b)·edge_frac 를
       만들고 그 높이를 지나는 지점을 선형보간으로 찾는다. ①의 교차검사.

    반환: dict(w_cov, w_lev, t_lo, t_hi, m, b_lo, b_hi)   (폭은 **px 단위**)
    """
    n = len(inside)
    rb = _run_bounds(inside, i_ref, wrap)
    if rb is None:
        return None
    i0, i1 = rb
    if i1 - i0 < 1:
        return None
    npad = max(2, int(np.ceil(pad_px / ds)))
    half = max(1, (i1 - i0) // 2)

    def val(j):
        return float(bilinear(L, xs[j % n], ys[j % n]))

    def med(js):
        return float(np.median(bilinear(L, xs[np.array(js) % n],
                                        ys[np.array(js) % n])))

    if not wrap and (i0 - 2 * npad < 0 or i1 + 2 * npad > n - 1):
        return None
    b_lo = med([i0 - k for k in range(npad, 2 * npad + 1)])
    b_hi = med([i1 + k for k in range(npad, 2 * npad + 1)])
    kin = min(npad, half)
    # ⚠ 안쪽 밝기는 **양쪽 가장자리마다 따로** 잡는다. 렌더된 날 표면에는 하이라이트가
    #   있어서 «구간 전체의 한 값» 으로 피복률을 계산하면 안쪽을 덜 세어 시위가 줄어든다.
    m_lo = med([i0 + k for k in range(kin, 2 * kin + 1)])
    m_hi = med([i1 - k for k in range(kin, 2 * kin + 1)])
    if b_lo - m_lo < 8.0 or b_hi - m_hi < 8.0:      # 대비가 없으면 못 잰다
        return None

    def edge_cov(i_edge, sgn, b_side, m_side):
        """가장자리 창(바깥 npad ~ 안쪽 kin)에서 피복률을 적분해 «덮인 길이» 를 낸다."""
        js = np.arange(i_edge - sgn * npad, i_edge + sgn * kin + sgn, sgn)
        v = bilinear(L, xs[js % n], ys[js % n])
        a = np.clip((b_side - v) / max(b_side - m_side, 1e-6), 0.0, 1.0)
        return float(a.sum() * ds)

    core = float((i1 - kin) - (i0 + kin)) * ds
    w_cov = core + edge_cov(i0, +1, b_lo, m_lo) + edge_cov(i1, -1, b_hi, m_hi)

    def cross(i_out, i_in, b_side, m_side):
        lev = b_side + (m_side - b_side) * edge_frac
        step = int(np.sign(i_in - i_out))
        prev_j, prev_v = i_out, val(i_out)
        for k in range(1, 2 * npad + 1):
            jj = i_out + step * k
            vv = val(jj)
            if (prev_v - lev) * (vv - lev) <= 0 and prev_v != vv:
                t = (lev - prev_v) / (vv - prev_v)
                return prev_j + t * (jj - prev_j)
            prev_j, prev_v = jj, vv
        return float(i_out)

    t_lo = cross(i0 - npad, i0 + kin, b_lo, m_lo)
    t_hi = cross(i1 + npad, i1 - kin, b_hi, m_hi)
    return dict(w_cov=w_cov, w_lev=float((t_hi - t_lo) * ds),
                t_lo=float(t_lo), t_hi=float(t_hi),
                m_lo=m_lo, m_hi=m_hi, b_lo=b_lo, b_hi=b_hi,
                i0=i0, i1=i1, n=n)


def find_holes(mask_obj, L, min_px=4):
    """실루엣 안의 «구멍»(배경색인데 바깥 배경과 안 이어짐) 중심 — 부분픽셀."""
    lab, nb = ndimage.label(~mask_obj)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    out = []
    for c in range(1, nb + 1):
        if c in border:
            continue
        m = lab == c
        if m.sum() < min_px:
            continue
        md = ndimage.binary_dilation(m, iterations=2)
        ys, xs = np.where(md)
        w = np.clip(L[ys, xs] - 60.0, 0, None) ** 2
        if w.sum() <= 0:
            continue
        out.append((float((xs * w).sum() / w.sum()),
                    float((ys * w).sum() / w.sum()), int(m.sum())))
    return out


def c2_center(cov, pts_xy, c0):
    """2회 회전대칭 중심 — 180° 회전 후 겹침 최대화(부분픽셀, 다중 출발)."""
    xs, ys = pts_xy[:, 0], pts_xy[:, 1]

    def cost(c):
        return -float(bilinear(cov, 2 * c[0] - xs, 2 * c[1] - ys).sum())

    best, bc = None, None
    for dx in (-1.5, 0.0, 1.5):
        for dy in (-1.5, 0.0, 1.5):
            s0 = np.array([c0 + [dx, dy], c0 + [dx + 0.7, dy],
                           c0 + [dx, dy + 0.7]], float)
            r = optimize.minimize(cost, c0 + np.array([dx, dy]),
                                  method="Nelder-Mead",
                                  options=dict(xatol=1e-3, fatol=1e-2,
                                               maxiter=2000, initial_simplex=s0))
            if best is None or r.fun < best:
                best, bc = float(r.fun), r.x
    return np.asarray(bc, float), -best / max(len(xs), 1)


# ===================================================================== #
#  1. 한 날의 평면형
# ===================================================================== #
def refine_tip(L, mask, O, tip_xy, edge_frac=0.5):
    """팁 반경을 부분픽셀로 — 팁 방위각을 따라 바깥으로 **피복률 적분**.

    R = r_in + ∫ α dr  (r_in 은 확실히 날 안쪽). 직선 가장자리라면 이 적분이 곧
    피복률 50 % 지점이고, 흐릿함(안티에일리어싱·JPEG)에 거의 안 걸린다.
    """
    v = np.asarray(tip_xy, float) - O
    r0 = float(np.hypot(*v))
    d = v / r0
    ds = 0.02
    t = np.arange(r0 - 4.0, r0 + 6.0 + ds, ds)
    px, py = O[0] + t * d[0], O[1] + t * d[1]
    L_ray = bilinear(L, px, py)
    m = float(np.median(L_ray[(t >= r0 - 3.0) & (t <= r0 - 1.5)]))   # 날 안쪽(국소)
    b = float(np.median(L_ray[t >= r0 + 3.0]))                       # 바깥 배경
    if b - m < 8.0:
        return r0
    sel = t >= r0 - 1.5
    alpha = np.clip((b - L_ray[sel]) / (b - m), 0.0, 1.0)
    return float((r0 - 1.5) + alpha.sum() * ds)


def blade_planform(L, mask, O, tip_xy, R_px, name="", edge_frac=0.5,
                   want_cal=True):
    """팁에서 안쪽으로 «행진»하며 시위 분포를 r/R 격자에서 잰다.

    이전 반경의 중시위 각도를 다음 반경의 기준점으로 쓴다 → 날이 휘어도(스윕) 추적이
    끊기지 않는다. 두 날이 붙는 반경(허브)에서 자동으로 멈춘다.
    """
    th_ref = float(np.arctan2(tip_xy[1] - O[1], tip_xy[0] - O[0]))
    rr = RGRID[::-1]
    res = {k: np.full(len(rr), np.nan) for k in
           ("c_arc", "c_arc_lev", "c_str", "th_mid", "dtheta")}
    r_merge = None
    for i, x in enumerate(rr):
        if r_merge is not None:            # 허브에서 두 날이 붙은 아래쪽은 안 잰다
            continue
        r = x * R_px
        n = max(1440, int(np.ceil(2 * np.pi * r / 0.10)))
        ds = 2 * np.pi * r / n                     # 호 방향 표본 간격 [px]
        th = np.linspace(-np.pi, np.pi, n, endpoint=False)
        xs = O[0] + r * np.cos(th)
        ys = O[1] + r * np.sin(th)
        ins = bilinear(mask.astype(float), xs, ys) > 0.5
        i_ref = int(round((th_ref + np.pi) / (2 * np.pi) * n)) % n
        if not ins[i_ref]:
            for d in range(1, max(2, int(n * 0.08))):
                if ins[(i_ref + d) % n]:
                    i_ref = (i_ref + d) % n
                    break
                if ins[(i_ref - d) % n]:
                    i_ref = (i_ref - d) % n
                    break
            else:
                continue
        mr = measure_run(L, xs, ys, ins, i_ref, True, ds, edge_frac)
        if mr is None:
            r_merge = x
            continue
        # ⭐두 날이 붙었는가: 이 구간이 **반대편**(θ+π)까지 삼켰으면 허브다
        i0, i1 = mr["i0"], mr["i1"]
        i_anti = (i_ref + n // 2) % n
        span_ok = ((i_anti - i0) % n) > ((i1 - i0) % n)
        dth = mr["w_cov"] / r
        if (not span_ok) or dth <= 0 or dth > np.radians(140):
            r_merge = x
            continue
        res["dtheta"][i] = dth
        res["c_arc"][i] = mr["w_cov"]
        res["c_arc_lev"][i] = mr["w_lev"]
        res["c_str"][i] = 2 * r * np.sin(dth / 2)
        th_lo = -np.pi + mr["t_lo"] * (2 * np.pi / n)
        th_hi = -np.pi + mr["t_hi"] * (2 * np.pi / n)
        res["th_mid"][i] = th_ref = 0.5 * (th_lo + th_hi)
    for k in list(res):
        res[k] = res[k][::-1]
    res["rr"] = RGRID.copy()
    res["r_merge_over_R"] = r_merge

    c_cal = np.full(len(RGRID), np.nan)
    if want_cal:
        good = np.isfinite(res["th_mid"])
        mx = O[0] + RGRID * R_px * np.cos(res["th_mid"])
        my = O[1] + RGRID * R_px * np.sin(res["th_mid"])
        if good.sum() > 8:
            k = 5
            w = good.astype(float)
            sx = np.convolve(np.nan_to_num(mx) * w, np.ones(k), "same")
            sy = np.convolve(np.nan_to_num(my) * w, np.ones(k), "same")
            cnt = np.convolve(w, np.ones(k), "same")
            sx = np.where(cnt > 0, sx / np.maximum(cnt, 1e-9), np.nan)
            sy = np.where(cnt > 0, sy / np.maximum(cnt, 1e-9), np.nan)
            for i in range(len(RGRID)):
                if not good[i]:
                    continue
                j0, j1 = max(0, i - 3), min(len(RGRID) - 1, i + 3)
                dx, dy = sx[j1] - sx[j0], sy[j1] - sy[j0]
                nn = np.hypot(dx, dy)
                if not np.isfinite(nn) or nn < 1e-6:
                    continue
                nx, ny = -dy / nn, dx / nn
                span = 1.4 * res["c_arc"][i] + 10.0
                npts = max(400, int(np.ceil(2 * span / 0.10)))
                t = np.linspace(-span, span, npts)
                dsl = float(t[1] - t[0])
                px, py = mx[i] + t * nx, my[i] + t * ny
                ins = bilinear(mask.astype(float), px, py) > 0.5
                if not ins[npts // 2]:
                    continue
                mrq = measure_run(L, px, py, ins, npts // 2, False, dsl,
                                  edge_frac)
                if mrq is None:
                    continue
                c_cal[i] = mrq["w_cov"]
    res["c_cal"] = c_cal
    res["name"] = name
    res["R_px"] = R_px
    res["tip_az_deg"] = float(np.degrees(np.arctan2(tip_xy[1] - O[1],
                                                    tip_xy[0] - O[0])))
    return res


# ===================================================================== #
#  2. 소스 A/B — 흰 배경 위 제품 렌더 (프롭 2개 = 날 4장)
# ===================================================================== #
def run_product_render(path, label, part, edge_frac=0.5, T_seg=235.0,
                       want_cal=True):
    rgb = np.asarray(Image.open(path).convert("RGB"), float)
    L = rgb.mean(axis=2)
    obj = L < T_seg
    lab, n = ndimage.label(obj)
    sz = ndimage.sum(obj, lab, range(1, n + 1))
    comps = [int(i) + 1 for i in np.argsort(sz)[::-1][:2]
             if sz[i] > 0.005 * obj.size]
    holes = find_holes(obj, L)
    props, blades = [], []
    for pi, ci in enumerate(comps):
        cm = lab == ci
        ys, xs = np.where(cm)
        hs = [h for h in holes if xs.min() - 3 <= h[0] <= xs.max() + 3
              and ys.min() - 3 <= h[1] <= ys.max() + 3]
        hs = sorted(hs, key=lambda h: h[1])
        rec = {"label": f"{label}-p{pi+1}", "n_hinge_holes": len(hs),
               "hinge_holes_px": [[round(h[0], 3), round(h[1], 3), h[2]]
                                  for h in hs]}
        if len(hs) == 2:
            O = np.array([(hs[0][0] + hs[1][0]) / 2, (hs[0][1] + hs[1][1]) / 2])
            rec["axis_method"] = "hinge_midpoint"
            rec["hinge_half_sep_px"] = round(float(np.hypot(
                hs[0][0] - hs[1][0], hs[0][1] - hs[1][1]) / 2), 4)
            hv = np.array([hs[1][0] - hs[0][0], hs[1][1] - hs[0][1]], float)
        else:
            O = np.array([xs.mean(), ys.mean()])
            rec["axis_method"] = "centroid(FALLBACK — 경첩 구멍 못 찾음)"
            hv = np.array([0.0, 1.0])
        cov = np.where(cm, np.clip((255.0 - L) / 20.0, 0, 1), 0.0)
        Oc, ov = c2_center(cov, np.c_[xs, ys].astype(float), O)
        rec["c2_center_px"] = [round(float(Oc[0]), 4), round(float(Oc[1]), 4)]
        rec["c2_overlap_frac"] = round(float(ov), 5)
        rec["axis_hinge_vs_c2_px"] = round(float(np.hypot(*(O - Oc))), 4)
        rec["axis_px"] = [round(float(O[0]), 4), round(float(O[1]), 4)]

        hv = hv / np.linalg.norm(hv)
        d = np.hypot(xs - O[0], ys - O[1])
        side = ((xs - O[0]) * hv[0] + (ys - O[1]) * hv[1]) > 0
        bl = []
        for s, nm in ((side, "1"), (~side, "2")):
            i = int(np.argmax(np.where(s, d, -1)))
            tip0 = np.array([xs[i], ys[i]], float)
            R = refine_tip(L, cm, O, tip0, edge_frac)
            pf = blade_planform(L, cm, O, tip0, R, f"{label}-p{pi+1}b{nm}",
                                edge_frac, want_cal)
            pf["prop"] = f"{label}-p{pi+1}"
            bl.append(pf)
            blades.append(pf)
        rec["blades"] = [{"name": b["name"], "R_px": round(b["R_px"], 4),
                          "tip_az_deg": round(b["tip_az_deg"], 3),
                          "r_merge_over_R": b["r_merge_over_R"]} for b in bl]
        rec["R_asym_pct"] = round(float(200 * (bl[0]["R_px"] - bl[1]["R_px"])
                                        / (bl[0]["R_px"] + bl[1]["R_px"])), 4)
        props.append(rec)
    return dict(path=path, label=label, part=part, props=props, blades=blades,
                L=L, ok=True)


# ===================================================================== #
#  3. 소스 C — 기체 상면 렌더 (프롭 4개 = 날 8장)
# ===================================================================== #
def run_aircraft_top(path, label, edge_frac=0.5, want_cal=True):
    rgb = np.asarray(Image.open(path).convert("RGB"), float)
    L = rgb.mean(axis=2)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    orange = (r > 185) & (b < 145) & ((r - b) > 65)
    blade_mask = ndimage.binary_closing(( L < 110) | orange, np.ones((3, 3)))
    lab, n = ndimage.label(blade_mask)
    sz = ndimage.sum(blade_mask, lab, range(1, n + 1))
    comps = [int(i) + 1 for i in np.argsort(sz)[::-1][:4]]
    labo, no = ndimage.label(orange)
    szo = ndimage.sum(orange, labo, range(1, no + 1))

    props, blades = [], []
    for pi, ci in enumerate(comps):
        cm = lab == ci
        ys, xs = np.where(cm)
        # 이 성분 안의 주황 팁 2개
        tips = []
        for i in np.argsort(szo)[::-1]:
            if szo[i] < 80:
                break
            mo = labo == (i + 1)
            if (mo & cm).sum() < 0.5 * mo.sum():
                continue
            yo, xo = np.where(mo)
            tips.append((float(xo.mean()), float(yo.mean())))
        if len(tips) != 2:
            continue
        O0 = np.array([(tips[0][0] + tips[1][0]) / 2,
                       (tips[0][1] + tips[1][1]) / 2])
        Oc, ov = c2_center(cm.astype(float), np.c_[xs, ys].astype(float), O0)
        rec = {"label": f"{label}-p{pi+1}",
               "axis_method": "C2_symmetry(성분 전체) — 경첩 구멍은 이 렌더에서 안 보인다",
               "axis_px": [round(float(Oc[0]), 4), round(float(Oc[1]), 4)],
               "axis_tipcentroid_mid_vs_c2_px": round(float(np.hypot(*(O0 - Oc))), 4),
               "c2_overlap_frac": round(float(ov), 5)}
        hv = np.array([tips[0][0] - Oc[0], tips[0][1] - Oc[1]], float)
        hv /= np.linalg.norm(hv)
        d = np.hypot(xs - Oc[0], ys - Oc[1])
        side = ((xs - Oc[0]) * hv[0] + (ys - Oc[1]) * hv[1]) > 0
        bl = []
        for s, nm in ((side, "1"), (~side, "2")):
            q = int(np.argmax(np.where(s, d, -1)))
            tip0 = np.array([xs[q], ys[q]], float)
            R = refine_tip(L, cm, Oc, tip0, edge_frac)
            pf = blade_planform(L, cm, Oc, tip0, R, f"{label}-p{pi+1}b{nm}",
                                edge_frac, want_cal)
            pf["prop"] = f"{label}-p{pi+1}"
            bl.append(pf)
            blades.append(pf)
        rec["blades"] = [{"name": b["name"], "R_px": round(b["R_px"], 4),
                          "tip_az_deg": round(b["tip_az_deg"], 3),
                          "r_merge_over_R": b["r_merge_over_R"]} for b in bl]
        rec["R_asym_pct"] = round(float(200 * (bl[0]["R_px"] - bl[1]["R_px"])
                                        / (bl[0]["R_px"] + bl[1]["R_px"])), 4)
        props.append(rec)
    return dict(path=path, label=label, part="on-aircraft (기종 미상 → 아래 판정)",
                props=props, blades=blades, L=L, ok=True)


# ===================================================================== #
#  4. 요약 통계
# ===================================================================== #
def at(rr, y, x):
    m = np.isfinite(y)
    if m.sum() < 3 or x < rr[m].min() or x > rr[m].max():
        return float("nan")
    return float(np.interp(x, rr[m], y[m]))


PEAK_WIN = (0.18, 0.98)          # 정점은 이 구간에서만 찾는다(허브 잔여물 배제)


def peak(rr, y):
    y = np.where((rr >= PEAK_WIN[0]) & (rr <= PEAK_WIN[1]), y, np.nan)
    m = np.isfinite(y)
    if m.sum() < 5:
        return float("nan"), float("nan")
    r, v = rr[m], y[m]
    i = int(np.argmax(v))
    if 0 < i < len(v) - 1:
        y0, y1, y2 = v[i - 1], v[i], v[i + 1]
        den = y0 - 2 * y1 + y2
        dd = float(np.clip(0.5 * (y0 - y2) / den, -1, 1)) if abs(den) > 1e-12 else 0.0
        return float(y1 - 0.25 * (y0 - y2) * dd), float(r[i] + dd * (r[1] - r[0]))
    return float(v[i]), float(r[i])


def band_int(rr, c, lo, hi):
    m = np.isfinite(c) & (rr >= lo) & (rr <= hi)
    if m.sum() < 3 or rr[m].min() > lo + 0.02 or rr[m].max() < hi - 0.02:
        return float("nan")
    return float(np.trapezoid(c[m], rr[m]))


def _r(x, k=5):
    return None if (x is None or not np.isfinite(x)) else round(float(x), k)


def summarize(src):
    bl = src["blades"]
    R = np.array([b["R_px"] for b in bl])
    mm_px = (NOMINAL_DIA_MM / 2.0) / R.mean()
    out = {
        "file": src["path"].name,
        "part": src["part"],
        "n_blades": len(bl),
        "R_px_per_blade": {b["name"]: round(b["R_px"], 3) for b in bl},
        "R_px_mean": round(float(R.mean()), 3),
        "R_px_spread_pct": round(float(100 * (R.max() - R.min()) / R.mean()), 3),
        "scale_mm_per_px": round(float(mm_px), 6),
        "scale_ruler": f"공칭 지름 {NOMINAL_DIA_MM} mm (=2R). 사진 안에 물리 자 없음.",
        "props": src["props"],
    }
    rr = bl[0]["rr"]
    R_mm = NOMINAL_DIA_MM / 2
    chord = {}
    for key in ("c_arc", "c_arc_lev", "c_str", "c_cal"):
        M = np.vstack([b[key] / b["R_px"] for b in bl])
        if not np.isfinite(M).any():
            continue                      # 이 잣대는 이번 실행에서 안 쟀다
        with np.errstate(all="ignore"):
            mu = np.nanmean(M, axis=0)
            sd = np.nanstd(M, axis=0)
        cmax, rpk = peak(rr, mu)
        per = {b["name"]: _r(peak(rr, M[i])[0]) for i, b in enumerate(bl)}
        vals = [v for v in per.values() if v]
        if not vals or not np.isfinite(cmax):
            continue
        chord[key] = {
            "c_max_over_R": _r(cmax),
            "c_max_mm": _r(cmax * R_mm, 3),
            "peak_r_over_R": _r(rpk, 4),
            "per_blade_c_max_over_R": per,
            "blade_spread_of_c_max_pct": _r(100 * (max(vals) - min(vals)) / cmax, 3),
            "table_c_over_R": {f"{x:.2f}": _r(at(rr, mu, x)) for x in REPORT_RR},
            "table_c_mm": {f"{x:.2f}": _r(at(rr, mu, x) * R_mm, 3) for x in REPORT_RR},
            "table_blade_sd_pct": {
                f"{x:.2f}": _r(100 * at(rr, sd, x) / at(rr, mu, x), 2)
                for x in REPORT_RR},
            "table_c_over_cmax": {f"{x:.2f}": _r(at(rr, mu, x) / cmax, 4)
                                  for x in REPORT_RR},
            "band_int_c_dr_over_R2": {f"{lo:.2f}-{hi:.2f}": _r(band_int(rr, mu, lo, hi), 6)
                                      for lo, hi in BANDS},
            "band_area_mm2_per_blade": {
                f"{lo:.2f}-{hi:.2f}": _r(band_int(rr, mu, lo, hi) * R_mm * R_mm, 2)
                for lo, hi in BANDS},
        }
        chord[key]["_mu"] = mu
    out["chord"] = chord
    out["_rr"] = rr
    out["_M"] = {k: np.vstack([b[k] / b["R_px"] for b in bl])
                 for k in ("c_arc", "c_arc_lev", "c_str", "c_cal")}
    out["_blades"] = bl
    return out


# ===================================================================== #
#  5. 기울기 모델 — 날 짝 비대칭에서 τ 를 읽는다
# ===================================================================== #
TILT_DERIVATION = (
    "정투영으로 프롭이 τ 만큼 기울면, 회전면에 투영된 시위는 두 날에서 "
    "c·cos(β−τ⊥) 와 c·cos(β+τ⊥) 로 갈라진다(τ⊥ = 날 스팬에 수직한 기울기 성분, "
    "β = 국소 피치각). 1차 유도: 이미지 좌표 (X,Y)=(x−z·tanτ, y) 로 두고 "
    "단면의 앞전·뒷전을 ±(c/2)(cosβ·t̂ + sinβ·ẑ) 로 놓으면 각폭이 그대로 나온다. "
    "따라서 (c₂−c₁)/(c₂+c₁) = tanβ · tanτ⊥ 이고, ⭐**두 날의 평균은 τ 의 2차까지 "
    "무편향**이다. 반경 R 은 반대다 — 스팬과 **나란한** 기울기 성분이 팁 레이크(z_t) "
    "와 곱해져 ΔR = 2·τ∥·z_t 를 만든다."
)


def tilt_from_pairs(summ, beta_law_rr, beta_law_deg):
    """프롭마다 두 날의 c_arc 비대칭 → tanβ·tanτ⊥, 그리고 τ⊥ 추정."""
    rr = summ["_rr"]
    M = summ["_M"]["c_arc"]
    bl = summ["_blades"]
    byprop = {}
    for i, b in enumerate(bl):
        byprop.setdefault(b["prop"], []).append((i, b))
    rows = []
    for p, lst in byprop.items():
        if len(lst) != 2:
            continue
        (i1, b1), (i2, b2) = lst
        c1, c2 = M[i1], M[i2]
        asym = (c2 - c1) / (c2 + c1)
        tanb = np.tan(np.radians(np.interp(rr, beta_law_rr, beta_law_deg)))
        with np.errstate(all="ignore"):
            tt = asym / tanb
        m = np.isfinite(tt) & (rr >= 0.25) & (rr <= 0.90)
        rows.append({
            "prop": p,
            "blade_span_az_deg": round(float(b1["tip_az_deg"]), 2),
            "R_asym_pct": round(float(200 * (b1["R_px"] - b2["R_px"])
                                      / (b1["R_px"] + b2["R_px"])), 3),
            "chord_asym_pct_0.25_0.90": _r(100 * float(np.nanmean(asym[m])), 3),
            "tan_tau_perp_est": _r(float(np.nanmean(tt[m])), 4),
            "tau_perp_deg_est": _r(float(np.degrees(np.arctan(np.nanmean(tt[m])))), 3),
            "tau_perp_scatter_deg": _r(float(np.degrees(np.arctan(
                np.nanstd(tt[m])))), 3),
        })
    return rows


# ===================================================================== #
#  6. 코드 법칙과의 대조 + 권고 상수
# ===================================================================== #
def beta_deg(rr, R_mm, pitch_mm, k_rr=None, k_v=None):
    r = np.maximum(rr * R_mm, 1e-6)
    k = np.ones_like(rr) if k_rr is None else np.interp(rr, k_rr, k_v)
    return np.degrees(np.arctan(k * pitch_mm / (2 * np.pi * r)))


def compare_to_code(summ):
    sys.path.insert(0, str(ROOT / "src"))
    import drone_cad as dc
    rr = summ["_rr"]
    R_mm = NOMINAL_DIA_MM / 2
    P_mm = NOMINAL_PITCH_IN * MM_PER_IN
    photo = summ["chord"]["c_arc"]["_mu"]                    # 투영 c/R (사진)

    laws = {"k_const_1": (None, None),
            "k_legacy_solo": (np.array(dc.PITCH_RR), np.array(dc.PITCH_K))}
    if hasattr(dc, "PITCH_K_DJI_MINI2"):
        laws["k_dji_mini2"] = (np.array(dc.PITCH_RR_DJI_MINI2),
                               np.array(dc.PITCH_K_DJI_MINI2))
    betas = {k: beta_deg(rr, R_mm, P_mm, *v) for k, v in laws.items()}

    # 우리 legacy 법칙의 **투영** 평면형
    ours_c = np.interp(rr, dc.CHORD_RR, dc.CHORD_FRAC) * dc.CHORD_MAX_OVER_R
    ours_proj = ours_c * np.cos(np.radians(betas["k_legacy_solo"]))
    ours_cmax, ours_rpk = peak(rr, ours_c)
    op_max, op_rpk = peak(rr, ours_proj)
    ph_max, ph_rpk = peak(rr, photo)

    out = {
        "how_compared": (
            "⭐사진은 **투영 폭**만 준다. 코드의 시위 c(r) 은 익형 시위라 투영하면 "
            "c(r)·cos β(r) 다. 그래서 (1) 코드를 **투영해서** 사진과 맞대고, "
            "(2) 사진을 코드 자신의 β 법으로 **역투영해서** 코드가 쓸 상수를 낸다. "
            "⚠ 역투영은 β 가정에 걸린다 — 세 k 법의 밴드를 함께 적는다."),
        "pitch_used_mm": round(P_mm, 3),
        "pitch_provenance": "1157F 뒷자리 해석 5.7 in (DJI 미공표) — DERIVED",
        "ours_legacy_true_c_max_over_R": _r(ours_cmax),
        "ours_legacy_projected_c_max_over_R": _r(op_max),
        "ours_legacy_projected_peak_r": _r(op_rpk, 3),
        "photo_projected_c_max_over_R": _r(ph_max),
        "photo_projected_peak_r": _r(ph_rpk, 3),
        "projected_ratio_ours_over_photo": _r(op_max / ph_max, 4),
        "projected_band_ratio_ours_over_photo": {
            f"{lo:.2f}-{hi:.2f}": _r(band_int(rr, ours_proj, lo, hi)
                                     / band_int(rr, photo, lo, hi), 4)
            for lo, hi in BANDS},
        "projected_band_dB_A2": {
            f"{lo:.2f}-{hi:.2f}": _r(20 * np.log10(band_int(rr, ours_proj, lo, hi)
                                                   / band_int(rr, photo, lo, hi)), 3)
            for lo, hi in BANDS},
    }

    rec = {}
    for name, bd in betas.items():
        c_true = photo / np.cos(np.radians(bd))
        cm, rp = peak(rr, c_true)
        grid = [0.00, 0.07, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
                0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
        frac = {f"{x:.2f}": _r(at(rr, c_true, x) / cm, 4) for x in grid}
        rec[name] = {
            "beta_deg_at": {f"{x:.2f}": _r(float(np.interp(x, rr, bd)), 3)
                            for x in (0.20, 0.30, 0.50, 0.75, 0.90)},
            "c_max_over_R_TRUE": _r(cm),
            "peak_r_over_R": _r(rp, 3),
            "CHORD_FRAC_like": frac,
        }
    out["unprojected_true_chord_by_k_law"] = rec
    out["headline"] = (
        "⭐사진이 직접 주는 것은 **투영 c_max/R** 이다. 익형 시위(코드가 쓰는 양)는 "
        "cos β 만큼 더 크고, β 가정에 따라 그 보정이 크게 갈린다 — 위 세 줄을 보라.")
    return out


# ===================================================================== #
#  7. main
# ===================================================================== #
def main():
    t0 = time.time()
    doc = {"_meta": {
        "title": "DJI Matrice 4E 프로펠러 사진 정밀 계측 (1157F 표준 / 1154F 저소음)",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M",
                                       time.localtime(time.time() + 9 * 3600)),
        "script": "benchmark/measure_prop_matrice4e_0816.py",
        "python": "/workspace/.venvs/py312/bin/python",
        "policy": "⛔GPU 미사용 · ⛔git 무접촉 · ⛔저장소 코드 무변경(이 파일은 추가)",
        "nominal_dia_mm": NOMINAL_DIA_MM,
        "nominal_pitch_in_DERIVED": NOMINAL_PITCH_IN,
    }}

    A = run_product_render(PHOTO / "matrice4e_c02_prop_standard_1157F_pair.jpg",
                           "A", "1157F 표준 (제품 렌더, 프롭 2개)")
    B = run_product_render(PHOTO / "matrice4e_c01_prop_low_noise_1154F_pair.jpg",
                           "B", "1154F 저소음 (제품 렌더, 프롭 2개)")
    C = run_aircraft_top(PHOTO / "matrice 4E_5.png", "C")

    sA, sB, sC = summarize(A), summarize(B), summarize(C)
    doc["A_1157F_product_render"] = sA
    doc["B_1154F_product_render"] = sB
    doc["C_aircraft_top_view"] = sC

    # --- 기울기 --------------------------------------------------------- #
    rrg = sA["_rr"]
    bd = beta_deg(rrg, NOMINAL_DIA_MM / 2, NOMINAL_PITCH_IN * MM_PER_IN)
    doc["tilt_and_perspective"] = {
        "derivation": TILT_DERIVATION,
        "beta_law_used_for_tau": "k≡1 (정피치 가정) — τ 는 β 가정에 반비례하므로 상한이다",
        "A_1157F": tilt_from_pairs(sA, rrg, bd),
        "B_1154F": tilt_from_pairs(sB, rrg, bd),
        "C_aircraft": tilt_from_pairs(sC, rrg, bd),
    }

    doc["code_comparison_1157F"] = compare_to_code(sA)

    # --- 민감도(가장자리 판정 · 이진화 문턱) ------------------------------ #
    sens = []
    for ef, T in ((0.35, 235.0), (0.65, 235.0), (0.5, 215.0), (0.5, 248.0)):
        s = summarize(run_product_render(
            PHOTO / "matrice4e_c02_prop_standard_1157F_pair.jpg", "S",
            "sens", edge_frac=ef, T_seg=T, want_cal=False))
        sens.append({"edge_frac": ef, "T_seg": T,
                     "R_px_mean": s["R_px_mean"],
                     "c_arc_c_max_over_R": s["chord"]["c_arc"]["c_max_over_R"],
                     "area_0.20_0.96_mm2": s["chord"]["c_arc"]
                     ["band_area_mm2_per_blade"]["0.20-0.96"]})
    base = sA["chord"]["c_arc"]["c_max_over_R"]
    doc["sensitivity_1157F"] = {
        "baseline_edge_frac_0.5_T_235": {
            "c_max_over_R": base, "R_px_mean": sA["R_px_mean"],
            "area_0.20_0.96_mm2": sA["chord"]["c_arc"]
            ["band_area_mm2_per_blade"]["0.20-0.96"]},
        "variants": sens,
        "c_max_over_R_full_spread_pct": _r(
            100 * (max([v["c_arc_c_max_over_R"] for v in sens] + [base])
                   - min([v["c_arc_c_max_over_R"] for v in sens] + [base])) / base, 2),
    }

    for k in ("A_1157F_product_render", "B_1154F_product_render",
              "C_aircraft_top_view"):
        doc[k].pop("_rr", None)
        doc[k].pop("_M", None)
        doc[k].pop("_blades", None)
        for kk in doc[k]["chord"]:
            doc[k]["chord"][kk].pop("_mu", None)

    doc["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str),
                   encoding="utf-8")
    print("wrote", OUT, doc["_meta"]["elapsed_s"], "s")
    return doc


if __name__ == "__main__":
    main()
