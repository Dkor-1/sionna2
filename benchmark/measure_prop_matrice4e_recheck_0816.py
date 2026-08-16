#!/usr/bin/env python
"""⭐ DJI Matrice 4E 프로펠러 — 사진 계측 **독립 재검증** (2026-08-16, 2차 패스)

무엇이 다른가 (1차 패스 `benchmark/measure_prop_matrice4e_0816.py` 대비)
  1차 패스는 «고정 밝기 임계값 + 부분픽셀 보간» 으로 실루엣을 잡았다. 이 파일은
  **완전히 다른 잣대**로 같은 대상을 다시 잰다. 두 잣대가 만나야 값을 믿는다.
    · 임계값이 **아예 없는** 시위 정의 — 덮개율(α) 각적분.  c_cov(r) = r·∫α(θ)dθ
      안티에일리어싱된 실루엣에서 이 적분은 임계값을 안 고르고도 폭의 불편추정이다.
    · α 자체를 **국소 물체색으로 정규화**해 복원한다(검은 날 ~50 · 주황 팁 ~165 처럼
      물체색이 다르면 고정 임계값은 팁을 깎는다).
    · 회전축을 **C2(180° 회전) 대칭 최적화**로 잡고, 힌지 구멍 중점과 대조한다.
    · ⭐**잣대 자체를 참값 아는 대상에 대 본다** — 우리 프롭 메쉬를 회전축 방향으로
      정투영해 사진과 같은 R=228 px 로 래스터한 뒤, 같은 파이프라인으로 재고
      «촘촘한 래스터(참값)» 와 비교한다. 해상도·감마·JPEG·기울기 편향을 **수치로** 낸다.

⭐ 정의 (이게 다르면 비교가 무의미하다)
  · 회전축 O   : α 영상의 C2 대칭 중심. 2날 프롭은 축 둘레 180° 대칭이다.
                 교차검사 = 힌지 관통구멍 2개의 중점.
  · R (반경)   : O 에서 그 날의 α=0.5 실루엣 끝까지의 최대 거리. **날마다 따로** 낸다.
                 정규화(r/R)에는 한 프롭의 두 날 평균 R_prop 을 쓴다(두 날이 같은 자를 쓰도록).
  · 날 뿌리    : 사진에서 «회색 허브/힌지 하드웨어» → «검은 복합재 날» 로 넘어가는 반경
                 r_black 을 밝기로 찾아 적는다. 그 안쪽 표의 값은 **날이 아니라 허브**다.
  · 시위       : ⚠ 아래 셋은 전부 **투영 시위**다. 회전축 방향에서 본 날 폭이라
                 c_proj(r) = c_true(r)·cos β(r) 이고 β 는 국소 피치각이다.
      c_cov (기본) r·∫α dθ            — 임계값 없음
      c_half       r·Δθ (α=0.5 교차)  — 1차 패스와 같은 계열
      c_str        2r·sin(Δθ/2)       — 두 교차점의 직선거리
  · 면적       : A(r1,r2) = ∫ c dr (극좌표에서 정확). 화소 α 직접합과 교차검증한다.

⛔ GPU 미사용 · ⛔ git 무접촉 · ⛔ 저장소 코드 무변경(이 파일과 산출 JSON 은 **추가**).
   numpy · scipy · PIL · trimesh 만 쓴다.

재현
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
      /workspace/.venvs/py312/bin/python benchmark/measure_prop_matrice4e_recheck_0816.py
산출
  outputs/prop_measure_matrice4e_0816.json          (이 파일이 쓴다)
  outputs/prop_measure_matrice4e_0816_pass1.json    (1차 패스 원본 보존 복사)
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage, optimize

ROOT = Path("/workspace/sionna")
PHOTO = ROOT / "assets/photos/matrice4e"
OUT = ROOT / "outputs/prop_measure_matrice4e_0816.json"
PASS1 = ROOT / "outputs/prop_measure_matrice4e_0816_pass1.json"

WHITE = 255.0
NOMINAL_DIA_MM = 274.0          # DJI 공표 10.8 inch = 274.32 → 레지스트리는 274.0
MM_PER_IN = 25.4

RGRID = np.round(np.arange(0.100, 0.9976, 0.0025), 5)
REPORT_RR = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55,
             0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.98]
BANDS = [(0.20, 0.96), (0.15, 0.96), (0.25, 0.95), (0.30, 0.96),
         (0.50, 0.96), (0.70, 0.96), (0.80, 0.96), (0.90, 0.96)]


# ===================================================================== #
#  1. 영상 → 덮개율 α                                                    #
# ===================================================================== #
def srgb_to_linear(u):
    u = u / 255.0
    out = np.where(u <= 0.04045, u / 12.92, ((u + 0.055) / 1.055) ** 2.4)
    return out * 255.0


def coverage(arr_rgb, core_T=205.0, ramp_T=253.5, linearise=False):
    """흰 배경 위 안티에일리어싱 실루엣에서 부분픽셀 덮개율 α 를 복원.

      L = α·C_obj + (1−α)·255      (합성은 선형 공간에서 일어난다)
    C_obj 는 화소마다 다르다 ⇒ **가장 가까운 확실한 내부 화소**의 밝기를 C_obj 로 쓴다.
    linearise=True 면 sRGB → 선형으로 되돌린 뒤 푼다(감마 편향 시험용).
    """
    L8 = arr_rgb.mean(2)
    L = srgb_to_linear(L8) if linearise else L8
    white = srgb_to_linear(np.array([WHITE]))[0] if linearise else WHITE
    core = ndimage.binary_erosion(L8 < core_T, np.ones((3, 3)))
    if not core.any():
        core = L8 < core_T
    idx = ndimage.distance_transform_edt(~core, return_distances=False, return_indices=True)
    Cobj = L[tuple(idx)]
    a = np.clip((white - L) / np.maximum(white - Cobj, 1.0), 0.0, 1.0)
    a[L8 >= ramp_T] = 0.0
    return a


def components(a, min_px=1000):
    lab, n = ndimage.label(a > 0.5)
    sizes = ndimage.sum(a > 0.5, lab, range(1, n + 1))
    keep = sorted([i + 1 for i in range(n) if sizes[i] >= min_px], key=lambda k: -sizes[k - 1])
    return [(lab == k) for k in keep]


# ===================================================================== #
#  2. 회전축                                                             #
# ===================================================================== #
def axis_by_c2(a, mask, half=None):
    """C2 대칭 중심 = 회전축. 잔차와 함께 돌려준다."""
    A = a * mask
    c0 = np.array(ndimage.center_of_mass(mask))
    if half is None:                      # 대상 크기에 맞춰 창을 잡는다(작은 그림에서 느려지지 않게)
        ys, xs = np.nonzero(mask)
        half = int(np.hypot(ys - c0[0], xs - c0[1]).max()) + 6
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1].astype(float)

    def cost(c):
        p = ndimage.map_coordinates(A, [c[0] + yy, c[1] + xx], order=1, mode="constant", cval=0.0)
        q = ndimage.map_coordinates(A, [c[0] - yy, c[1] - xx], order=1, mode="constant", cval=0.0)
        return float(np.abs(p - q).sum() / (p.sum() + q.sum() + 1e-9))

    r = optimize.minimize(cost, c0, method="Nelder-Mead",
                          options=dict(xatol=1e-4, fatol=1e-9, maxiter=4000))
    # 위치 불확실도: 비용의 2차 곡률에서
    h = 0.5
    d2 = [(cost(r.x + h * e) + cost(r.x - h * e) - 2 * r.fun) / h ** 2
          for e in (np.array([1.0, 0.0]), np.array([0.0, 1.0]))]
    return r.x, float(r.fun), [float(v) for v in d2]


def hinge_holes(L8, axis, box=32, T=248.0):
    """허브 안의 **관통 구멍**(배경이 비쳐 흰색) 2개를 찾아 중점을 낸다."""
    cy, cx = axis
    y0, x0 = int(cy) - box, int(cx) - box
    sub = L8[y0:y0 + 2 * box + 1, x0:x0 + 2 * box + 1]
    lab, n = ndimage.label(sub > T)
    out = []
    for k in range(1, n + 1):
        m = lab == k
        if m.sum() < 4 or m.sum() > 200:
            continue
        ys, xs = np.nonzero(m)
        if ys.min() == 0 or xs.min() == 0 or ys.max() == m.shape[0] - 1 or xs.max() == m.shape[1] - 1:
            continue                              # 테두리에 닿으면 배경이다
        w = (sub[m] - T)
        out.append((float((ys * w).sum() / w.sum() + y0),
                    float((xs * w).sum() / w.sum() + x0), int(m.sum())))
    out.sort(key=lambda h: -h[2])
    return out[:2]


# ===================================================================== #
#  3. 극좌표 시위 — 세 정의를 한 번에                                      #
# ===================================================================== #
def ring(a, axis, r_px, n_over=12.0):
    n = max(int(2 * np.pi * r_px * n_over), 1440)
    th = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    v = ndimage.map_coordinates(a, [axis[0] + r_px * np.sin(th), axis[1] + r_px * np.cos(th)],
                                order=1, mode="constant", cval=0.0)
    return th, v


def blade_segments(th, v, level=0.5):
    """α=level 을 지나는 각 구간들을 부분픽셀로."""
    s = v - level
    n = len(s)
    dth = th[1] - th[0]
    up = np.where((s <= 0) & (np.roll(s, -1) > 0))[0]
    dn = np.where((s > 0) & (np.roll(s, -1) <= 0))[0]
    if len(up) == 0 or len(dn) == 0:
        return []

    def cross(i):
        s0, s1 = s[i], s[(i + 1) % n]
        return th[i] + dth * (-s0) / (s1 - s0)

    ups = np.sort(np.array([cross(i) for i in up]))
    dns = np.sort(np.array([cross(i) for i in dn]))
    segs = []
    for u in ups:
        d = dns[dns > u]
        d = d[0] if len(d) else dns[0] + 2 * np.pi
        segs.append((float(u), float(d)))
    return segs


def chord_at(a, axis, r_px, level=0.5, expect=2):
    """반경 r 에서 날 하나하나의 (c_cov, c_half, c_str, 중심각) 을 낸다."""
    th, v = ring(a, axis, r_px)
    segs = blade_segments(th, v, level)
    if len(segs) != expect:
        return None
    dth = th[1] - th[0]
    res = []
    for (u, d) in segs:
        half = d - u
        # 덮개율 각적분 — 구간 양쪽으로 넉넉히 넓혀 α 꼬리까지 담는다
        pad = 0.35 * half + 6 * dth
        lo, hi = u - pad, d + pad
        k = int(np.ceil((hi - lo) / dth)) + 1
        tt = np.linspace(lo, hi, k)
        vv = ndimage.map_coordinates(a, [axis[0] + r_px * np.sin(tt), axis[1] + r_px * np.cos(tt)],
                                     order=1, mode="constant", cval=0.0)
        cov = float(np.trapezoid(vv, tt))
        res.append(dict(c_cov=cov * r_px, c_half=half * r_px,
                        c_str=2 * r_px * np.sin(half / 2), th_mid=float((u + d) / 2 % (2 * np.pi))))
    return res


def blade_radius(a, axis, th_mid, r_lo, r_hi, level=0.5):
    """그 날의 방향으로 α=level 이 사라지는 반경 = R (이분법)."""
    def has(r):
        th, v = ring(a, axis, r)
        segs = blade_segments(th, v, level)
        for (u, d) in segs:
            m = (u + d) / 2 % (2 * np.pi)
            dd = abs((m - th_mid + np.pi) % (2 * np.pi) - np.pi)
            if dd < np.radians(35):
                return True
        return False
    lo, hi = r_lo, r_hi
    if not has(lo):
        return float("nan")
    while hi - lo > 1e-3:
        mid = 0.5 * (lo + hi)
        if has(mid):
            lo = mid
        else:
            hi = mid
    return lo


def measure_prop(a, mask, level=0.5, rgrid=RGRID):
    """한 프롭(2날)을 통째로 잰다."""
    A = a * mask
    axis, resid, curv = axis_by_c2(a, mask)
    ys, xs = np.nonzero(mask)
    rmax = float(np.hypot(ys - axis[0], xs - axis[1]).max())
    # 두 날의 방향
    probe = chord_at(A, axis, 0.6 * rmax, level)
    if probe is None:
        raise RuntimeError("0.6R 에서 날 2장이 안 잡힌다")
    th_mids = [p["th_mid"] for p in probe]
    Rs = [blade_radius(A, axis, t, 0.5 * rmax, rmax + 3.0, level) for t in th_mids]
    R_prop = float(np.mean(Rs))
    tab = {}
    for u in rgrid:
        res = chord_at(A, axis, u * R_prop, level)
        if res is None:
            continue
        res.sort(key=lambda p: min(abs((p["th_mid"] - t + np.pi) % (2 * np.pi) - np.pi) for t in th_mids))
        # 각 날에 배정
        assign = []
        for t in th_mids:
            best = min(res, key=lambda p: abs((p["th_mid"] - t + np.pi) % (2 * np.pi) - np.pi))
            assign.append(best)
        if assign[0] is assign[1]:
            continue
        tab[float(u)] = assign
    return dict(axis=[float(axis[0]), float(axis[1])], c2_resid=resid, c2_curv=curv,
                R_px_per_blade=[float(x) for x in Rs], R_prop_px=R_prop,
                th_mid_deg=[float(np.degrees(t) % 360) for t in th_mids], table=tab)


def curves(meas, key="c_cov"):
    rr = np.array(sorted(meas["table"]))
    vals = np.array([[b[key] for b in meas["table"][u]] for u in rr]) / meas["R_prop_px"]
    return rr, vals


def summarise(meas, key="c_cov"):
    rr, vals = curves(meas, key)
    mean = vals.mean(1)
    i = int(mean.argmax())
    out = dict(c_max_over_R=float(mean[i]), peak_r_over_R=float(rr[i]),
               per_blade_c_max_over_R=[float(vals[:, j].max()) for j in range(vals.shape[1])])
    out["blade_spread_of_c_max_pct"] = float(
        100 * (max(out["per_blade_c_max_over_R"]) - min(out["per_blade_c_max_over_R"]))
        / np.mean(out["per_blade_c_max_over_R"]))
    out["table_c_over_R"] = {f"{u:.2f}": float(np.interp(u, rr, mean)) for u in REPORT_RR}
    out["table_c_over_cmax"] = {k: round(v / out["c_max_over_R"], 4)
                                for k, v in out["table_c_over_R"].items()}
    out["table_blade_diff_pct"] = {
        f"{u:.2f}": float(100 * abs(np.interp(u, rr, vals[:, 0]) - np.interp(u, rr, vals[:, 1]))
                          / np.interp(u, rr, mean)) for u in REPORT_RR}
    bands = {}
    for (r1, r2) in BANDS:
        m = (rr >= r1) & (rr <= r2)
        bands[f"{r1}-{r2}"] = float(np.trapezoid(mean[m], rr[m]))
    out["band_int_c_dr_over_R2"] = bands
    return out


# ===================================================================== #
#  4. 참값 아는 대상으로 잣대 검정                                          #
# ===================================================================== #
def rasterize(tri2d, R_px, margin=1.15, ss=4):
    half = R_px * margin
    n = int(2 * half) + 2
    N = n * ss
    acc = np.zeros((N, N), dtype=bool)
    for t in tri2d:
        xs = (t[:, 0] * R_px + half) * ss
        ys = (t[:, 1] * R_px + half) * ss
        x0, x1 = max(int(np.floor(xs.min())), 0), min(int(np.ceil(xs.max())) + 1, N)
        y0, y1 = max(int(np.floor(ys.min())), 0), min(int(np.ceil(ys.max())) + 1, N)
        if x1 <= x0 or y1 <= y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12:
            continue
        l0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
        l1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
        acc[y0:y1, x0:x1] |= (l0 >= 0) & (l1 >= 0) & (l0 + l1 <= 1)
    a = acc.reshape(n, ss, n, ss).mean(axis=(1, 3))
    return a, (half, half)


def our_prop_fresh():
    """⭐**지금 코드가 만드는** matrice4e 프롭 (build_propeller_cad, n_sec=20).

    아래 `our_prop_on_disk` 와 **다르다** — 디스크 자산이 낡았다(E 절 참조).
    """
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from drones import DRONES
    from drone_cad import build_propeller_cad
    A = build_propeller_cad(DRONES["matrice4e"], n_sec=20)
    m = A.parts["prop"][0]
    V = np.asarray(m.vertices)
    R_mesh = float(np.hypot(V[:, 0], V[:, 1]).max())
    return V, np.asarray(m.faces), R_mesh, int(len(m.faces))


def our_prop_on_disk():
    """저장소 디스크에 놓인 정본 자산에서 로터 1개(2날)를 뽑는다."""
    m = trimesh.load(ROOT / "assets/meshes/drones/matrice4e/matrice4e__prop.obj", process=False)
    if isinstance(m, trimesh.Scene):
        m = m.dump(concatenate=True)
    cc = m.split(only_watertight=False)
    hubs = [c for c in cc if len(c.faces) < 400]
    blades = [c for c in cc if len(c.faces) >= 400]
    ctr = hubs[0].bounds.mean(0)
    near = sorted(blades, key=lambda b: np.linalg.norm(b.bounds.mean(0)[:2] - ctr[:2]))[:2]
    V, F, off = [], [], 0
    for b in near:
        V.append(np.asarray(b.vertices))
        F.append(np.asarray(b.faces) + off)
        off += len(b.vertices)
    V = np.vstack(V) - ctr
    rr = np.hypot(V[:, 0], V[:, 1])
    return V, np.vstack(F), float(rr.max()), float(rr.min()), len(cc)


def measure_raster(a, axis, level=0.5, key="c_cov"):
    """래스터 실루엣에 사진과 **같은** 잣대를 댄다."""
    lo, hi = 0.4 * axis[0], 1.15 * axis[0]

    def has(r):
        th, v = ring(a, axis, r)
        return len(blade_segments(th, v, level)) > 0
    while hi - lo > 1e-3:
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if has(mid) else (lo, mid)
    R = lo
    rr, cm = [], []
    for u in RGRID:
        res = chord_at(a, axis, u * R, level)
        if res is None:
            continue
        rr.append(u)
        cm.append(np.mean([p[key] for p in res]) / R)
    rr, cm = np.array(rr), np.array(cm)
    i = int(cm.argmax())
    band = (rr >= 0.20) & (rr <= 0.96)
    return dict(R_px=float(R), c_max_over_R=float(cm[i]), peak_r_over_R=float(rr[i]),
                band_020_096=float(np.trapezoid(cm[band], rr[band])),
                table={f"{u:.2f}": float(np.interp(u, rr, cm)) for u in REPORT_RR})


# ===================================================================== #
#  5. 투영 → 참시위 되돌리기                                               #
# ===================================================================== #
def beta_deg(rr, R_mm, pitch_mm, law):
    """국소 피치각 β(r). 세 법으로 밴드를 낸다 (⚠ 전부 DERIVED)."""
    r = np.maximum(rr * R_mm, 1e-6)
    if law == "constant_pitch":                 # 정피치 나선
        P = np.full_like(r, pitch_mm)
    elif law == "dji_mini2_k":                  # DJI Mini 2 공식 CAD 에서 잰 국소피치 분포
        from drone_cad import PITCH_RR_DJI_MINI2, PITCH_K_DJI_MINI2
        P = pitch_mm * np.interp(rr, PITCH_RR_DJI_MINI2, PITCH_K_DJI_MINI2)
    elif law == "flat_beta_at_075R":            # 비틀림 없음(β 를 0.75R 값으로 고정)
        r75 = 0.75 * R_mm
        b = np.arctan2(pitch_mm, 2 * np.pi * r75)
        return np.full_like(rr, np.degrees(b))
    else:
        raise ValueError(law)
    return np.degrees(np.arctan2(P, 2 * np.pi * r))


# ===================================================================== #
#  main                                                                  #
# ===================================================================== #
def main():
    t0 = time.time()
    doc = {}

    doc["_meta"] = dict(
        title="DJI Matrice 4E 프로펠러 사진 계측 — 독립 재검증 2차 패스 (1157F 표준 / 1154F 저소음)",
        generated_kst=time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 9 * 3600)),
        script="benchmark/measure_prop_matrice4e_recheck_0816.py",
        python="/workspace/.venvs/py312/bin/python",
        policy="⛔GPU 미사용 · ⛔git 무접촉 · ⛔저장소 코드 무변경(이 파일·JSON 은 추가)",
        supersedes="benchmark/measure_prop_matrice4e_0816.py (1차 패스) — 원본은 "
                   "outputs/prop_measure_matrice4e_0816_pass1.json 로 보존",
        what_is_new="임계값 없는 시위 정의(덮개율 각적분) + 국소 물체색 정규화 α + "
                    "C2 대칭 회전축 + ⭐참값 아는 대상(우리 메쉬 정투영 래스터)으로 잣대 검정",
        nominal_dia_mm=NOMINAL_DIA_MM,
        prop_identity="matrice4e 순정 = 1157F(표준). 1154F 는 별매 저소음. 근거는 "
                      "레지스트리 weight_g=1219(=DJI 표준프롭 이륙중량) · 저소음은 액세서리 별매.",
    )

    doc["conventions"] = dict(
        rotor_axis="α 영상의 C2(180° 회전) 대칭 중심. 교차검사 = 힌지 관통구멍 2개의 중점",
        R="O 에서 그 날의 α=0.5 실루엣 끝까지 최대 거리 — 날마다 따로. 정규화에는 두 날의 평균 R_prop",
        root="회색 허브/힌지 → 검은 복합재 날 전이 반경 r_black 을 밝기로 찾아 적는다. 그 안쪽은 날이 아니다",
        chord_c_cov="r·∫α(θ)dθ — **임계값 없음**. 기본 정의",
        chord_c_half="r·Δθ, α=0.5 교차 (1차 패스 계열)",
        chord_c_str="2r·sin(Δθ/2) — 두 교차점의 직선거리",
        projection="⚠ 셋 다 **투영 시위**다. c_proj = c_true·cos β. 참시위는 아래 F 절에서 밴드로만 준다",
        area="A(r1,r2) = ∫c dr (극좌표에서 정확). 화소 α 직접합과 교차검증",
        scale="사진 안에 물리 자가 없다. 공칭 지름 274.0 mm 를 자로 쓴다 ⇒ **비율은 자와 무관**, mm 만 자에 걸린다",
    )

    # ---------- A. 잣대 검정 (참값 아는 대상) ---------------------------- #
    V, F, R_mesh, n_faces_fresh = our_prop_fresh()
    Vn = V / R_mesh

    def raster_measure(Vv, Rpx, ss=4, key="c_cov"):
        a, ax = rasterize(Vv[F][:, :, :2], Rpx, ss=ss)
        return measure_raster(a, ax, key=key), a, ax

    ref, _, _ = raster_measure(Vn, 1200.0)          # 촘촘한 래스터 = 참값
    lowres, a_lr, ax_lr = raster_measure(Vn, 228.3)  # 사진과 같은 해상도
    calib = dict(
        what="우리 matrice4e 프롭 메쉬를 회전축 방향으로 정투영해 래스터하고, **사진과 똑같은 잣대**를 댄다",
        why="잣대가 얼마나 정확한지는 참값 아는 대상에 대 봐야 안다",
        truth_R1200px=ref, photo_res_R228px=lowres,
        resolution_bias_pct=dict(
            c_max_over_R=float(100 * (lowres["c_max_over_R"] / ref["c_max_over_R"] - 1)),
            band_020_096=float(100 * (lowres["band_020_096"] / ref["band_020_096"] - 1))),
    )

    # 시위 정의 3종이 서로 얼마나 다른가 (같은 래스터)
    defs = {}
    for key in ("c_cov", "c_half", "c_str"):
        defs[key] = raster_measure(Vn, 228.3, key=key)[0]["c_max_over_R"]
    calib["chord_definition_spread_on_truth"] = dict(
        values=defs,
        c_cov_vs_c_half_pct=float(100 * (defs["c_cov"] / defs["c_half"] - 1)),
        c_cov_vs_c_str_pct=float(100 * (defs["c_cov"] / defs["c_str"] - 1)),
        note="참값 대상에서 이미 갈리는 폭 = 정의가 만드는 하한 오차")

    # 감마(sRGB) 편향 — 렌더는 선형에서 합성하고 sRGB 로 내보낸다
    Cobj_lin = 45.0
    L_lin = WHITE * (1 - a_lr) + Cobj_lin * a_lr
    u = L_lin / WHITE
    L_srgb = WHITE * np.where(u <= 0.0031308, 12.92 * u, 1.055 * u ** (1 / 2.4) - 0.055)
    img_srgb = np.repeat(L_srgb[:, :, None], 3, axis=2)
    g_naive = measure_raster(coverage(img_srgb), ax_lr)
    g_lin = measure_raster(coverage(img_srgb, linearise=True), ax_lr)
    calib["gamma_bias"] = dict(
        setup="참 α 로 선형합성 → sRGB 인코딩 → 되읽기",
        as_measured_srgb=g_naive["c_max_over_R"], linearised=g_lin["c_max_over_R"],
        truth=lowres["c_max_over_R"],
        bias_srgb_pct=float(100 * (g_naive["c_max_over_R"] / lowres["c_max_over_R"] - 1)),
        bias_linear_pct=float(100 * (g_lin["c_max_over_R"] / lowres["c_max_over_R"] - 1)),
        verdict="둘 중 나쁜 쪽을 체계오차로 싣는다 — 실제 JPEG 이 어느 공간에서 합성됐는지는 모른다")

    # JPEG 압축 편향
    tmp = ROOT / "outputs/_tmp_prop_calib.jpg"
    Image.fromarray(np.repeat((WHITE * (1 - a_lr) + Cobj_lin * a_lr)[:, :, None], 3, 2)
                    .astype(np.uint8)).save(tmp, quality=88)
    a_jpg = coverage(np.asarray(Image.open(tmp).convert("RGB")).astype(float))
    j = measure_raster(a_jpg, ax_lr)
    tmp.unlink(missing_ok=True)
    calib["jpeg_bias"] = dict(quality=88, measured=j["c_max_over_R"], truth=lowres["c_max_over_R"],
                              bias_pct=float(100 * (j["c_max_over_R"] / lowres["c_max_over_R"] - 1)))

    # ⭐ 기울기(원근) 민감도 — 사진만 보고는 못 알아내는 계통오차
    tilt = []
    for name, ax_i in (("span", 0), ("perp", 1)):
        for tau in (-30, -20, -10, -5, 5, 10, 20, 30):
            t = np.radians(tau)
            ca, sa = np.cos(t), np.sin(t)
            Vr = Vn.copy()
            if ax_i == 0:
                y = Vr[:, 1] * ca - Vr[:, 2] * sa
                z = Vr[:, 1] * sa + Vr[:, 2] * ca
                Vr[:, 1], Vr[:, 2] = y, z
            else:
                x = Vr[:, 0] * ca + Vr[:, 2] * sa
                z = -Vr[:, 0] * sa + Vr[:, 2] * ca
                Vr[:, 0], Vr[:, 2] = x, z
            m, _, _ = raster_measure(Vr, 228.3)
            tilt.append(dict(tilt_axis=name, tau_deg=tau, c_max_over_R=m["c_max_over_R"],
                             d_c_max_pct=float(100 * (m["c_max_over_R"] / lowres["c_max_over_R"] - 1)),
                             R_px=m["R_px"],
                             d_R_pct=float(100 * (m["R_px"] / lowres["R_px"] - 1))))
    calib["tilt_sensitivity"] = dict(
        setup="같은 메쉬를 원반면 밖으로 τ 만큼 기울여 정투영 — R 도 실루엣에서 다시 잰다(사진과 같은 절차)",
        rows=tilt,
        worst_within_10deg_pct=float(max(abs(r["d_c_max_pct"]) for r in tilt if abs(r["tau_deg"]) <= 10)),
        worst_within_20deg_pct=float(max(abs(r["d_c_max_pct"]) for r in tilt if abs(r["tau_deg"]) <= 20)),
        verdict_ko="⭐사진 한 장에서 공통 기울기 τ 는 **원리적으로 못 잡는다**(정투영이면 아핀변환이라 "
                  "C2 대칭도 보존된다). 대신 그 대가를 여기서 수치로 못 박는다.")
    calib["why_no_homography"] = dict(
        asked="«평면 호모그래피 또는 알려진 치수 기준자로 원근·기울기 보정»",
        done="기준자는 썼다 — 공칭 지름 274 mm. 그래서 **비율(c/R)은 자와 무관**하다",
        not_done="호모그래피는 **못 놓는다**. 평면 호모그래피를 풀려면 같은 평면 위에 치수를 아는 "
                 "기준점 4개가 필요한데 제품 렌더에는 없다. 원형 특징(원→타원)으로 대신하려 해도 "
                 "1157F 허브의 관통구멍은 **지름 3.4 px**(면적 9~10 px)라 타원 축비를 못 뽑는다",
        instead="그래서 «못 잡는 기울기» 를 없는 셈 치지 않고 **대가를 표로 못 박았다**(tilt_sensitivity). "
                "±10° → ≤%.1f %% · ±20° → ≤%.1f %%"
                % (calib["tilt_sensitivity"]["worst_within_10deg_pct"],
                   calib["tilt_sensitivity"]["worst_within_20deg_pct"]),
        evidence_view_is_near_face_on=[
            "한 프롭의 두 날 반경이 0.4~0.6 % 안에서 같다 — 큰 기울기면 갈라진다",
            "이미지 안 다른 위치에 놓인 프롭 2개의 실루엣 면적이 0.4 % 안에서 같다 — "
            "원근(짧은 렌즈)이면 위치에 따라 달라진다",
            "⚠둘 다 **공통** 기울기는 못 배제한다(정투영에서 기울기는 아핀변환이고 C2 대칭을 보존한다)",
        ])
    doc["A_ruler_calibration"] = calib

    # ---------- B·C. 실물 프롭 두 종 ------------------------------------- #
    parts = {
        "B_1157F_standard": dict(
            file="matrice4e_c02_prop_standard_1157F_pair.jpg",
            part="1157F 표준 (⭐matrice4e 순정)",
            source="DJI 스토어 제품 렌더 (SOURCES.md: cdn.shopify.com .../standard_propellers_matrice_4_...png)"),
        "C_1154F_low_noise": dict(
            file="matrice4e_c01_prop_low_noise_1154F_pair.jpg",
            part="1154F 저소음 (별매 액세서리 — 대조군)",
            source="DJI 스토어 제품 렌더 (SOURCES.md: .../low-noise_props_matrice_4_...png)"),
    }
    for k, info in parts.items():
        rgb = np.asarray(Image.open(PHOTO / info["file"]).convert("RGB")).astype(float)
        L8 = rgb.mean(2)
        a = coverage(rgb)
        comps = components(a)
        info["n_props_in_image"] = len(comps)
        props = []
        for j, cmask in enumerate(comps):
            m = measure_prop(a, cmask)
            hh = hinge_holes(L8, m["axis"])
            if len(hh) == 2:
                mid = [(hh[0][0] + hh[1][0]) / 2, (hh[0][1] + hh[1][1]) / 2]
                m["hinge_holes_px"] = [[round(h[0], 3), round(h[1], 3), h[2]] for h in hh]
                m["axis_hinge_midpoint"] = [round(v, 3) for v in mid]
                m["axis_c2_vs_hinge_px"] = round(float(np.hypot(mid[0] - m["axis"][0],
                                                                mid[1] - m["axis"][1])), 3)
                m["hinge_half_sep_px"] = round(float(np.hypot(hh[0][0] - hh[1][0],
                                                              hh[0][1] - hh[1][1]) / 2), 3)
            else:
                m["hinge_holes_px"] = None
                m["axis_c2_vs_hinge_px"] = None
            # 회색 허브 → 검은 날 전이 반경
            rblk = None
            prev = None
            for u in np.arange(0.05, 0.60, 0.005):
                res = chord_at(a * cmask, m["axis"], u * m["R_prop_px"])
                if res is None:
                    continue
                vals = []
                for p in res:
                    tt = np.linspace(p["th_mid"] - 0.3 * p["c_half"] / (u * m["R_prop_px"]),
                                     p["th_mid"] + 0.3 * p["c_half"] / (u * m["R_prop_px"]), 21)
                    yy = m["axis"][0] + u * m["R_prop_px"] * np.sin(tt)
                    xx = m["axis"][1] + u * m["R_prop_px"] * np.cos(tt)
                    vals.append(np.median(ndimage.map_coordinates(L8, [yy, xx], order=1)))
                cur = float(np.mean(vals))
                if prev is not None and prev[1] > 100 >= cur:
                    rblk = float(np.interp(100.0, [cur, prev[1]], [u, prev[0]]))
                    break
                prev = (u, cur)
            m["r_black_over_R"] = rblk
            m["r_black_note"] = "회색 하드웨어(L≈130~145) → 검은 복합재(L≈60~80) 전이(L=100 교차). 안쪽은 날이 아니다"
            for key in ("c_cov", "c_half", "c_str"):
                m[key] = summarise(m, key)
            # 화소 α 직접합 ↔ ∫c dr 교차검증
            rr, vals = curves(m, "c_cov")
            band = (rr >= 0.20) & (rr <= 0.96)
            int_c = float(np.trapezoid(vals.sum(1)[band], rr[band])) * m["R_prop_px"] ** 2
            ys, xs = np.mgrid[0:a.shape[0], 0:a.shape[1]]
            rad = np.hypot(ys - m["axis"][0], xs - m["axis"][1]) / m["R_prop_px"]
            pix = float((a * cmask * ((rad >= 0.20) & (rad <= 0.96))).sum())
            m["area_crosscheck_px2"] = dict(int_c_dr=round(int_c, 2), pixel_alpha_sum=round(pix, 2),
                                            diff_pct=round(100 * (int_c / pix - 1), 3))
            m.pop("table")
            props.append(m)
        info["props"] = props
        # 프롭끼리·날끼리 일치도
        cm = [p["c_cov"]["c_max_over_R"] for p in props]
        info["prop_to_prop"] = dict(
            c_max_over_R=cm,
            spread_pct=float(100 * (max(cm) - min(cm)) / np.mean(cm)),
            note="⭐이 이미지의 프롭 2개는 **같은 부품의 서로 다른 배치**다 — 완전 독립 표본은 아니지만 "
                 "같은 렌더의 복붙도 아니다(실루엣 면적은 0.4 % 안에서 같고 주축은 1.4° 다르다)")
        allb = [v for p in props for v in p["c_cov"]["per_blade_c_max_over_R"]]
        info["n_blades_measured"] = len(allb)
        info["blade_c_max_over_R_all"] = allb
        info["blade_spread_pct"] = float(100 * (max(allb) - min(allb)) / np.mean(allb))
        info["headline"] = dict(
            c_max_over_R_projected=float(np.mean(cm)),
            peak_r_over_R=float(np.mean([p["c_cov"]["peak_r_over_R"] for p in props])),
            R_px=float(np.mean([p["R_prop_px"] for p in props])),
            mm_per_px=float(NOMINAL_DIA_MM / 2 / np.mean([p["R_prop_px"] for p in props])),
            c_max_mm=float(np.mean(cm) * NOMINAL_DIA_MM / 2),
            table_c_mm={k: round(float(v * NOMINAL_DIA_MM / 2), 3)
                        for k, v in props[0]["c_cov"]["table_c_over_R"].items()},
            blade_area_020_096_mm2=float(np.mean(
                [p["c_cov"]["band_int_c_dr_over_R2"]["0.2-0.96"] for p in props])
                * (NOMINAL_DIA_MM / 2) ** 2),
        )
        doc[k] = info

    b, c = doc["B_1157F_standard"], doc["C_1154F_low_noise"]
    doc["D_variant_contrast"] = dict(
        question="⭐어느 프롭인지 안 적으면 σ·마이크로도플러가 갈린다 (감사 ?3)",
        c_max_over_R=dict(std_1157F=b["headline"]["c_max_over_R_projected"],
                          low_noise_1154F=c["headline"]["c_max_over_R_projected"]),
        low_noise_over_standard=dict(
            c_max=float(c["headline"]["c_max_over_R_projected"] / b["headline"]["c_max_over_R_projected"]),
            blade_area_020_096=float(c["headline"]["blade_area_020_096_mm2"]
                                     / b["headline"]["blade_area_020_096_mm2"])),
        robustness="공통 기울기·감마·JPEG 는 두 렌더에 **같이** 걸리므로 이 **비율**은 절대값보다 훨씬 튼튼하다",
        which_one_ships="1157F 표준. 레지스트리 weight_g=1219 가 DJI 의 표준프롭 이륙중량이고 "
                        "(저소음은 1229), 저소음은 «for C2» 별매 액세서리다",
    )

    # ---------- E. 우리 코드와 사과-대-사과 -------------------------------- #
    #   ⭐사진도 우리 메쉬도 **같은 양**(회전축 방향 투영 실루엣의 호폭)을 **같은 잣대**로 잰다.
    #     피치·스윕 가정이 하나도 안 들어간다 — 이것이 유일하게 깨끗한 비교다.
    ours = lowres                       # 지금 코드가 만드는 프롭
    Vd, Fd, rmax_d, rmin_d, ncomp_d = our_prop_on_disk()
    a_d, ax_d = rasterize((Vd / rmax_d)[Fd][:, :, :2], 228.3)
    disk = measure_raster(a_d, ax_d)
    photo_tab = b["props"][0]["c_cov"]["table_c_over_R"]
    photo_band = float(np.mean([p["c_cov"]["band_int_c_dr_over_R2"]["0.2-0.96"] for p in b["props"]]))
    doc["E_vs_our_code"] = dict(
        how="회전축 방향 정투영 실루엣의 **호폭**을 사진과 같은 해상도(R=228 px)·같은 잣대로 쟀다. "
            "피치·스윕 가정이 안 들어간다",
        ours_fresh_build=dict(
            what="⭐지금 코드가 만드는 프롭 — src/drone_cad.build_propeller_cad(matrice4e, n_sec=20)",
            n_faces=n_faces_fresh, c_max_over_R=ours["c_max_over_R"],
            peak_r_over_R=ours["peak_r_over_R"], band_020_096=ours["band_020_096"],
            table=ours["table"]),
        ours_on_disk_asset=dict(
            what="⚠저장소 디스크 자산 assets/meshes/drones/matrice4e/matrice4e__prop.obj",
            c_max_over_R=disk["c_max_over_R"], peak_r_over_R=disk["peak_r_over_R"],
            band_020_096=disk["band_020_096"], table=disk["table"]),
        asset_is_stale=dict(
            verdict="⭐**디스크 자산은 낡았다 — 지금 코드가 만드는 것과 다른 물건이다.**",
            evidence=[
                "스윕디스크 반경 %.5f m ↔ 공칭 0.137 m = **+%.2f %%**. 이 +0.84 %% 초과는 "
                "drone_cad 주석이 «2026-07-28 에 고쳤다» 고 적은 바로 그 버그다. 새로 빌드하면 0.137000 이다"
                % (rmax_d, 100 * (rmax_d / 0.137 - 1)),
                "날 뿌리 반경 %.5f m = **0.140 R** ↔ 지금 코드의 root_frac=0.070 이면 0.00959 m 여야 한다 "
                "(=옛 기본값 0.14 로 구워진 메쉬)" % rmin_d,
                "연결요소 %d 개(허브·날이 안 붙었다) ↔ 새 빌드는 union 이 먹어 1 개" % ncomp_d,
                "결과: 투영 호폭 봉우리가 **0.50R**(디스크) ↔ **0.32R**(새 빌드). 형상이 다르다",
            ],
            consequence="⛔이 자산으로 «우리 프롭» 을 판정한 결론은 다시 봐야 한다. 아래 비교의 정본은 "
                        "**새 빌드**다. (같은 낌새를 benchmark/adv_multiref_planform_0816.py 도 "
                        "지름 축에서 적어 뒀다 — 독립 확인)"),
        photo_1157F=dict(c_max_over_R=b["headline"]["c_max_over_R_projected"],
                         peak_r_over_R=b["headline"]["peak_r_over_R"],
                         band_020_096=photo_band, table=photo_tab),
        ratio_fresh_over_photo=dict(
            c_max=round(float(ours["c_max_over_R"] / b["headline"]["c_max_over_R_projected"]), 4),
            band_020_096=round(float(ours["band_020_096"] / photo_band), 4),
            per_radius={k: round(float(ours["table"][k] / photo_tab[k]), 3) for k in photo_tab}),
        ratio_disk_over_photo=dict(
            c_max=round(float(disk["c_max_over_R"] / b["headline"]["c_max_over_R_projected"]), 4),
            band_020_096=round(float(disk["band_020_096"] / photo_band), 4)),
        finding_ko="⭐**총면적은 거의 맞는데 반경 분포가 틀렸다.** 새 빌드 대 사진: 총 날면적 "
                   "(0.20~0.96R) %+.1f %% 인데, 안쪽 0.20~0.40R 은 **+11~+22 %% 넓고** "
                   "바깥 0.65~0.85R 은 **−6~−10 %% 좁다**. 팁(0.98R)은 −32 %% 다(감사 I8 «뾰족한 팁»). "
                   "면적 오차가 서로 상쇄돼 «크기는 맞다» 로 보일 뿐이다"
                   % (100 * (ours["band_020_096"] / photo_band - 1)),
        why_it_matters="σ(면적 적분)에는 상쇄돼 잘 안 보이지만, **마이크로도플러는 f ∝ r 이라 "
                       "반경 분포가 곧 스펙트럼 포락선**이다. 안쪽이 넓고 바깥이 좁으면 "
                       "낮은 도플러가 과대·f_tip 밴드가 과소로 나온다",
        audit_I2_correction="⚠감사 I2 의 «matrice4e +31 %%» 는 **참(설계) 시위 상수 0.25** 를 "
                            "**투영 호폭 사진값 0.190** 과 견준 수다 — 서로 다른 양이다. "
                            "같은 양끼리 재면 c_max %+.1f %% · 면적 %+.1f %% 다"
                            % (100 * (ours["c_max_over_R"] / b["headline"]["c_max_over_R_projected"] - 1),
                               100 * (ours["band_020_096"] / photo_band - 1)),
    )

    # ---------- F. 투영 → 참시위 (⭐코드 상수에 넣을 값) -------------------- #
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    rrq = np.array(REPORT_RR)
    R_mm = NOMINAL_DIA_MM / 2
    dep = {}
    for law in ("constant_pitch", "dji_mini2_k", "flat_beta_at_075R"):
        for name, pitch_in in (("1157F", 5.7), ("1154F", 5.4)):
            src = b if name == "1157F" else c
            tab = src["props"][0]["c_cov"]["table_c_over_R"]
            cp = np.array([tab[f"{u:.2f}"] for u in rrq])
            bt = beta_deg(rrq, R_mm, pitch_in * MM_PER_IN, law)
            ct = cp / np.cos(np.radians(bt))
            i = int(ct.argmax())
            dep[f"{name}_{law}"] = dict(
                pitch_in=pitch_in, beta_deg={f"{u:.2f}": round(float(v), 2) for u, v in zip(rrq, bt)},
                c_true_over_R={f"{u:.2f}": round(float(v), 5) for u, v in zip(rrq, ct)},
                c_true_max_over_R=round(float(ct[i]), 5), peak_r_over_R=float(rrq[i]))
    doc["F_deprojection_to_true_chord"] = dict(
        why_ko="⭐`CHORD_MAX_OVER_R` 는 로프트가 익형 단면에 쓰는 **참시위**다. 사진은 **투영시위**를 준다. "
              "그대로 상수에 넣으면 만들어진 날이 실물보다 좁아진다",
        pitch_provenance=dict(
            p1154F="[A-] DJI M4 시리즈 매뉴얼 p.101 «1154F = 27.4 × 13.7 cm». 13.7 cm = 5.394 in ⇒ **피치 5.4 in**",
            p1157F="[B] DJI 는 1157F 피치를 공표 안 한다. 부품번호 뒷 두 자리 = 피치(0.1 in) 규약을 "
                   "DJI 자신의 표가 3줄에서 확증한다 — 1158F 26.7×14.7 cm(14.7 cm = 5.79 in), "
                   "6028F 15.2×7.1 cm(7.1 cm = 2.80 in), 1154F 위. ⇒ 1157F = **5.7 in**",
            caveat="⚠ 그래도 1157F 피치는 **유도값**이다. 아래 세 법의 폭이 그 대가다"),
        laws=dep,
        pitch_law_centre_and_band_1157F=dict(
            note="⚠이 값은 **피치법만** 되돌린 것이다. 코드 상수 권고는 I 절을 볼 것(스윕까지 본다)",
            c_true_max_over_R=round(float(np.mean([dep["1157F_constant_pitch"]["c_true_max_over_R"],
                                                   dep["1157F_dji_mini2_k"]["c_true_max_over_R"]])), 4),
            band=[round(min(dep[f"1157F_{l}"]["c_true_max_over_R"] for l in
                            ("constant_pitch", "dji_mini2_k", "flat_beta_at_075R")), 4),
                  round(max(dep[f"1157F_{l}"]["c_true_max_over_R"] for l in
                            ("constant_pitch", "dji_mini2_k", "flat_beta_at_075R")), 4)],
            grade="[B] 사진 계측(투영) × [DERIVED] 피치 되돌리기"),
        warning_ko="⭐`CHORD_MAX_OVER_R_MEASURED['matrice4e'] = 0.190` 은 **투영값**이다. 참시위 상수 "
                  "자리에 그대로 넣으면 날이 약 7~10 % 좁아진다. 위 recommended 를 쓸 것",
    )

    # ---------- G. 두께 — 못 잰다 ------------------------------------------ #
    r_ex = 0.70
    P = 5.7 * MM_PER_IN
    bta = np.radians(float(beta_deg(np.array([r_ex]), R_mm, P, "dji_mini2_k")[0]))
    c70 = b["props"][0]["c_cov"]["table_c_over_R"]["0.70"] * R_mm
    doc["G_thickness"] = dict(
        answer="⛔ **사진으로 못 잰다.** 값을 만들지 않는다",
        why="옆모습에서 날의 겉보기 높이는 H(r) = c(r)·sin β(r) + t(r)·cos β(r) 다. "
            "0.70R 에서 c = %.1f mm, β ≈ %.1f° 이므로 첫 항이 %.2f mm — 두께 t(≈1 mm)보다 "
            "몇 배 크다. β 를 1° 잘못 알면 겉보기 높이가 %.2f mm 움직인다(두께의 절반)."
            % (c70, np.degrees(bta), c70 * np.sin(bta), c70 * np.cos(bta) * np.radians(1.0)),
        conclusion="즉 옆모습에서 t 를 되풀어내는 것은 **조건수가 나쁜 역문제**다. "
                   "상한(t ≤ H/cos β)밖에 못 준다",
        repo_state="감사 ?2 그대로 미해결 — 두 추정 0.99 mm(1157F 시위 × Mini2 t/c) vs 1.40 mm"
                   "(Mini2 반경 환산)가 1.41 배 벌어져 있다. 이 파일은 그 간극을 **안 좁혔다**",
        only_way_out="① 1157F 실물 확보 후 캘리퍼/마이크로미터 ② DJI 공식 프롭 CAD(현재 없음) "
                     "③ 옆모습 고해상 사진 + 피치 독립 측정",
        side_view_attempt=dict(
            file="matrice4e_p01_side_profile_left.jpg (2667×2667 — 폴더에서 가장 큰 옆모습)",
            what_we_see="⭐확대해 보면 옆모습에 보이는 것은 날의 **윗면**이지 단면이 아니다. "
                        "날이 비틀려 있어 옆에서 봐도 앞전~뒷전이 위아래로 펼쳐져 보인다. "
                        "«두께로 보이는 것» 은 사실상 전부 시위의 투영이다",
            geometric_bound="볼록 단면의 어느 방향 투영폭이든 그 단면의 최소폭(=두께) 이상이다 ⇒ "
                            "겉보기 폭 W 는 **t 의 상한**밖에 못 준다. 여기서 W ≈ 5~7 mm 급이라 "
                            "t(≈1 mm)에 대해 쓸모없는 상한이다",
            other_views="p02·p05 정면/후면도 같은 이유로 안 된다. 날 단면이 정면으로 보이는 사진은 "
                        "폴더에 **없다**"),
        p09_underside_note="p09/p10(하면도)은 모터 벨의 원형 링이 뚜렷한 타원으로 찍힐 만큼 "
                           "원반면이 크게 기울어 있어 시위 계측에 못 쓴다. ⚠축비를 수치로는 "
                           "**못 쟀다** — 날·암이 벨과 같은 검은색이라 링만 자동 분리가 안 된다",
    )

    # ---------- H. 비틀림·스윕이 «투영 호폭» 을 얼마나 옮기는가 ------------- #
    #   ⭐사진이 재는 것은 «반경 r 원호를 따라 잰 날 폭»(호폭)이다. 코드의 CHORD_MAX_OVER_R 은
    #   «스팬 정거장에서의 설계 시위» 다. 날이 **스윕**(시미터, sweep_frac=0.10R)돼 있으면
    #   둘은 같은 양이 아니다. 여기서 우리 코드 자신의 로프트로 그 차이를 분해한다.
    #   ⛔ 코드는 안 건드린다 — `drone_cad._blade` 를 **인자만 바꿔 호출**할 뿐이다.
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "src"))
    from drone_cad import _blade as _dc_blade
    import trimesh.transformations as tf

    def two_blade_proj(pitch_m, sweep_frac):
        b1 = _dc_blade(0.137, root_frac=0.070, chord_max=0.25, pitch_m=pitch_m,
                       n_sec=22, sweep_frac=sweep_frac)
        b2 = b1.copy()
        b2.apply_transform(tf.rotation_matrix(np.pi, [0, 0, 1]))
        Vv = np.vstack([np.asarray(b1.vertices), np.asarray(b2.vertices)])
        Ff = np.vstack([np.asarray(b1.faces), np.asarray(b2.faces) + len(b1.vertices)])
        Vv = Vv / float(np.hypot(Vv[:, 0], Vv[:, 1]).max())
        aa, axx = rasterize(Vv[Ff][:, :, :2], 228.3)
        return measure_raster(aa, axx)

    P_m = 5.7 * MM_PER_IN / 1000.0
    dec = {
        "1_design_law_only": dict(desc="피치≈0 · 스윕 0 — 호폭 = 설계 시위 그대로",
                                  **two_blade_proj(1e-6, 0.0)),
        "2_plus_twist": dict(desc="+ 피치 5.7 in 비틀림 (스윕 0)", **two_blade_proj(P_m, 0.0)),
        "3_plus_sweep_shipped": dict(desc="+ 시미터 스윕 0.10R = **실제 출하 형상**",
                                     **two_blade_proj(P_m, 0.10)),
    }
    for v in dec.values():
        v.pop("table", None)
    doc["H_twist_sweep_decomposition"] = dict(
        why="사진(호폭) ↔ 코드 상수(설계 시위) 를 잇는 다리. 스윕이 있으면 둘은 다른 양이다",
        design_constant_CHORD_MAX_OVER_R=0.25,
        steps=dec,
        arc_over_design=dict(
            twist_only=float(dec["2_plus_twist"]["c_max_over_R"] / 0.25),
            twist_and_sweep=float(dec["3_plus_sweep_shipped"]["c_max_over_R"] / 0.25)),
        peak_shift="설계 시위 봉우리 0.30R → 비틀림·스윕을 거친 투영 호폭 봉우리 %.2fR. "
                   "실물 1157F 의 호폭 봉우리는 0.29R 이라 **봉우리 위치는 사실상 맞다** — "
                   "틀린 것은 봉우리의 «높이» 와 바깥쪽 꼬리의 «두께» 다(E 절)"
                   % dec["3_plus_sweep_shipped"]["peak_r_over_R"],
        cost_of_each=dict(
            twist_pct=round(float(100 * (dec["2_plus_twist"]["c_max_over_R"]
                                         / dec["1_design_law_only"]["c_max_over_R"] - 1)), 2),
            sweep_pct=round(float(100 * (dec["3_plus_sweep_shipped"]["c_max_over_R"]
                                         / dec["2_plus_twist"]["c_max_over_R"] - 1)), 2)),
        caveat="⚠실물 1157F 의 스윕량은 **모른다**. 이 다리는 우리 로프트의 스윕을 가정한다",
    )

    # ---------- I. 코드 상수 권고 (두 경로) -------------------------------- #
    photo_arc = b["headline"]["c_max_over_R_projected"]
    route_scalar = 0.25 * photo_arc / ours["c_max_over_R"]
    route_deproj = doc["F_deprojection_to_true_chord"]["laws"]["1157F_dji_mini2_k"]["c_true_max_over_R"]
    doc["I_recommended_constant"] = dict(
        target="src/drone_cad.py 의 `CHORD_MAX_OVER_R_MEASURED['matrice4e']` (지금 0.190)",
        route_A_scale_our_loft=dict(
            value=round(float(route_scalar), 4),
            how="우리 로프트의 투영 호폭이 사진과 같아지도록 상수만 비례로 줄인다 "
                "(0.25 × 사진호폭 %.5f / 우리호폭 %.5f)" % (photo_arc, ours["c_max_over_R"]),
            pro="우리 코드의 비틀림·스윕을 **그대로 통과**시키므로 가정이 적다",
            con="형상(봉우리 위치)은 여전히 틀린다 — 크기만 맞춘다"),
        route_B_deproject_photo=dict(
            value=round(float(route_deproj), 4),
            how="사진 호폭을 국소 피치각으로 나눠 참시위로 되돌린다(DJI Mini 2 공식 CAD 의 k(r) 법)",
            band=doc["F_deprojection_to_true_chord"]["pitch_law_centre_and_band_1157F"]["band"],
            con="스윕은 안 되돌린다 — 실물 스윕량을 모른다"),
        agreement_pct=round(float(100 * (route_scalar / route_deproj - 1)), 2),
        recommended=round(float(0.5 * (route_scalar + route_deproj)), 3),
        warning_ko="⭐현행 권고값 **0.190 은 투영 호폭**이다(사진이 주는 값). `CHORD_MAX_OVER_R` 는 "
                   "로프트가 익형에 쓰는 **설계 시위** 자리라 그대로 넣으면 날이 약 %.0f %% 좁아진다. "
                   "두 경로가 %.1f %% 안에서 만나는 **%.3f** 을 권한다"
                   % (100 * (1 - 0.190 / (0.5 * (route_scalar + route_deproj))),
                      abs(100 * (route_scalar / route_deproj - 1)),
                      0.5 * (route_scalar + route_deproj)),
        grade="[B] 사진 계측 + [DERIVED] 되돌리기. 실물 CAD 가 생기면 [A] 로 승격 가능",
    )

    # ---------- J. 다른 잣대·다른 출처와 대조 ------------------------------ #
    prior = None
    if PASS1.exists():
        try:
            prior = json.loads(PASS1.read_text())
        except Exception:
            prior = None
    cross = dict(
        quantity="1157F 투영 c_max/R (같은 양, 다른 방법·다른 사람)",
        this_pass_c_cov=round(float(photo_arc), 5),
        this_pass_c_half=round(float(np.mean([p["c_half"]["c_max_over_R"] for p in b["props"]])), 5),
        this_pass_c_str=round(float(np.mean([p["c_str"]["c_max_over_R"] for p in b["props"]])), 5),
        audit_MESH_AUDIT_0816=0.190,
    )
    if prior:
        try:
            cross["pass1_c_arc"] = prior["A_1157F_product_render"]["chord"]["c_arc"]["c_max_over_R"]
            cross["pass1_R_px_per_blade"] = prior["A_1157F_product_render"]["R_px_per_blade"]
            cross["pass1_R_spread_pct"] = prior["A_1157F_product_render"]["R_px_spread_pct"]
        except Exception:
            pass
    vals = [cross[k] for k in ("this_pass_c_cov", "this_pass_c_half", "this_pass_c_str",
                               "audit_MESH_AUDIT_0816", "pass1_c_arc") if k in cross]
    cross["all_estimates"] = vals
    cross["mean"] = round(float(np.mean(vals)), 5)
    cross["full_spread_pct"] = round(float(100 * (max(vals) - min(vals)) / np.mean(vals)), 2)
    cross["blade_radius_asymmetry"] = dict(
        this_pass_pct=round(float(100 * abs(b["props"][0]["R_px_per_blade"][0]
                                            - b["props"][0]["R_px_per_blade"][1])
                                  / np.mean(b["props"][0]["R_px_per_blade"])), 2),
        pass1_pct=1.61,
        why="⭐1 차 패스의 «두 날 반경이 1.6 % 다르다» 는 **실물 특성이 아니라 임계값 아티팩트**로 "
            "보인다. 팁은 주황 데칼이라 밝고(L≈165) 두 날의 음영도 다르다 — 고정 밝기 임계값은 "
            "그 차이를 길이 차이로 바꿔 읽는다. 물체색으로 정규화한 α 로 재면 0.4 % 로 줄어든다")
    doc["J_cross_source"] = cross

    # ---------- K. 매뉴얼 선화 (스타일화 — 낮은 등급) ---------------------- #
    try:
        rgbm = np.asarray(Image.open(PHOTO / "matrice4e_m07_top_plan_prop_rotation_AB.png")
                          .convert("RGB")).astype(float)
        Lm = rgbm.mean(2)
        chroma = rgbm.max(2) - rgbm.min(2)
        L2 = np.where(chroma < 25, Lm, 255.0)          # 주황 화살표·파랑 글자 지우기
        am = np.clip((255.0 - L2) / (255.0 - 215.0), 0, 1)
        lab, n = ndimage.label(am > 0.5)
        sizes = ndimage.sum(am > 0.5, lab, range(1, n + 1))
        rows = []
        for k in np.argsort(sizes)[::-1]:
            if not (2000 <= sizes[k] <= 4000):
                continue
            mm_ = ndimage.binary_fill_holes(lab == k + 1)
            try:
                r = measure_prop(am * mm_, mm_)
            except Exception:
                continue
            s = summarise(r, "c_cov")
            rows.append(dict(R_px=round(r["R_prop_px"], 2), c_max_over_R=round(s["c_max_over_R"], 4),
                             peak_r_over_R=s["peak_r_over_R"],
                             blade_spread_pct=round(s["blade_spread_of_c_max_pct"], 2)))
        doc["K_manual_line_art"] = dict(
            file="matrice4e_m07_top_plan_prop_rotation_AB.png (User Manual p.20)",
            grade="[D] **스타일화된 선화** — 계측 자료가 아니다. 실물 1157F 의 팁은 뭉툭한데 "
                  "선화는 뾰족하게 그린다. 검은 외곽선(폭 ~1.5 px)이 호폭을 위로 밀기도 한다",
            props=rows,
            mean_c_max_over_R=round(float(np.mean([r["c_max_over_R"] for r in rows])), 4) if rows else None,
            vs_product_render_pct=round(float(100 * (np.mean([r["c_max_over_R"] for r in rows])
                                                     / photo_arc - 1)), 1) if rows else None,
            use="정투영이라 «기울기» 걱정이 없는 유일한 다른 출처다. 다만 등급이 낮아 "
                "**숫자를 대체하지 않고 부호만** 본다")
    except Exception as e:                                    # noqa: BLE001
        doc["K_manual_line_art"] = dict(error=str(e), note="못 쟀다 — 없다고 적는다")

    # ---------- L. 불확실도 예산 ------------------------------------------- #
    A = doc["A_ruler_calibration"]
    budget = [
        dict(source="날 4장 사이 산포 (통계)", pct=round(b["blade_spread_pct"] / 2, 2), kind="random"),
        dict(source="프롭 2개 사이", pct=round(b["prop_to_prop"]["spread_pct"], 3), kind="random"),
        dict(source="해상도(228 px)", pct=round(abs(A["resolution_bias_pct"]["c_max_over_R"]), 2), kind="systematic"),
        dict(source="시위 정의(호폭↔직선현)", pct=round(abs(A["chord_definition_spread_on_truth"]["c_cov_vs_c_str_pct"]), 2), kind="systematic"),
        dict(source="감마(sRGB 합성 가정)", pct=round(abs(A["gamma_bias"]["bias_srgb_pct"]), 2), kind="systematic"),
        dict(source="JPEG 압축", pct=round(abs(A["jpeg_bias"]["bias_pct"]), 2), kind="systematic"),
        dict(source="⭐미지의 공통 기울기 ±10°", pct=round(A["tilt_sensitivity"]["worst_within_10deg_pct"], 2), kind="systematic-unknown"),
        dict(source="자(공칭 지름 274 mm) — 비율에는 안 걸림", pct=0.0, kind="scale-only"),
    ]
    rss = float(np.sqrt(sum(r["pct"] ** 2 for r in budget)))
    doc["L_uncertainty_budget"] = dict(
        rows=budget, rss_pct=round(rss, 2),
        projected_c_max_over_R=round(float(photo_arc), 5),
        projected_pm=round(float(photo_arc * rss / 100), 5),
        note="투영 호폭의 불확실도다. **참시위로 되돌리는 단계의 불확실도가 이보다 훨씬 크다** "
             "(피치법 밴드 %s) — 그쪽이 지배한다"
             % (doc["F_deprojection_to_true_chord"]["pitch_law_centre_and_band_1157F"]["band"],),
    )

    # ---------- M. 머리기사 ------------------------------------------------ #
    doc["M_headline"] = dict(
        aircraft="matrice4e / DJI Matrice 4E (⭐주력 표적 1순위)",
        prop_model="1157F 표준 (순정). 1154F 저소음은 별매 — 이 파일에서 대조군으로 같이 쟀다",
        best_source="[B] assets/photos/matrice4e/matrice4e_c02_prop_standard_1157F_pair.jpg "
                    "(DJI 스토어 제품 렌더, 720×720, 프롭 2개 = 날 4장)",
        why_not_A="⛔공식 CAD `assets/meshes/reference/matrice4-M4T_v2.step` 에 **프로펠러가 없다** "
                  "(outputs/meshfix_matrice4e.json). 1157F 3D 기하는 저장소에 없다",
        projected_arc_chord=dict(
            c_max_over_R=round(float(photo_arc), 4),
            pm_pct=round(rss, 1),
            peak_r_over_R=round(float(b["headline"]["peak_r_over_R"]), 3),
            c_max_mm=round(float(b["headline"]["c_max_mm"]), 2),
            blade_area_0p20_0p96R_mm2=round(float(b["headline"]["blade_area_020_096_mm2"]), 1),
            grade="[B] 사진 계측"),
        true_design_chord=dict(
            c_max_over_R=round(float(0.5 * (route_scalar + route_deproj)), 3),
            band=doc["F_deprojection_to_true_chord"]["pitch_law_centre_and_band_1157F"]["band"],
            grade="[B]×[DERIVED] — 피치·스윕 되돌리기가 지배하는 불확실도"),
        thickness="⛔ 못 쟀다 (G 절). 값을 만들지 않는다",
        valid_radius_range="0.20R ~ 0.97R. 그 안쪽은 회색 힌지 하드웨어이고(전이 r≈0.18~0.19R) "
                           "0.97R 밖은 날마다 반경이 달라 정규화 잡음이 지배한다",
        four_blade_agreement="c_max/R 산포 %.2f %% (4장) · 프롭 2개 사이 %.2f %% · "
                             "면적 교차검증(∫c dr ↔ 화소 α 합) %.2f %% 이내"
                             % (b["blade_spread_pct"], b["prop_to_prop"]["spread_pct"],
                                max(abs(p["area_crosscheck_px2"]["diff_pct"]) for p in b["props"])),
        open_questions=[
            "①실물 1157F 두께 — 미해결(감사 ?2). 사진으로는 원리적으로 못 잰다",
            "②실물 1157F 스윕량 — 미상. 호폭↔설계시위 다리를 우리 로프트 가정으로 놨다",
            "③사진의 공통 기울기 τ — 사진 한 장으로는 원리적으로 못 잡는다. 대가는 "
            "±10° 에서 %.1f %% · ±20° 에서 %.1f %%"
            % (A["tilt_sensitivity"]["worst_within_10deg_pct"],
               A["tilt_sensitivity"]["worst_within_20deg_pct"]),
            "④1157F 피치 5.7 in 은 부품번호 규약에서 온 **유도값**이다(1154F 는 매뉴얼에 13.7 cm 로 나온다)",
        ],
    )

    # ---------- N. 폴더 전수 선별 기록 ------------------------------------- #
    verdicts = {
        "matrice4e_c02_prop_standard_1157F_pair.jpg":
            ("USED ⭐1순위", "1157F 부품 단독 렌더. 흰 배경·날 4장·거의 정면. 이 파일의 정본"),
        "matrice4e_c01_prop_low_noise_1154F_pair.jpg":
            ("USED (대조군)", "1154F 부품 단독 렌더. 같은 조건이라 **비율 비교**가 튼튼하다"),
        "matrice4e_m07_top_plan_prop_rotation_AB.png":
            ("USED [D]", "매뉴얼 p.20 상면 선화. 정투영이라 기울기 걱정은 없지만 **스타일화**됐다"),
        "matrice4e_p01_side_profile_left.jpg":
            ("REJECT(시위) / 두께 시도", "옆모습. 날 윗면만 보여 두께를 못 준다(G 절)"),
        "matrice4e_p09_underside_plan.jpg":
            ("REJECT", "하면도지만 원반면이 크게 기울었다(모터 벨 링이 뚜렷한 타원)"),
        "matrice4e_p10_underside_plan_alt.jpg": ("REJECT", "p09 와 같은 이유 + 해상도 절반"),
        "matrice4e_p02_front_elevation.jpg": ("REJECT", "정면 — 원반면이 시선과 거의 나란"),
        "matrice4e_p05_rear_elevation.jpg": ("REJECT", "후면 — 상동"),
        "matrice4e_p03_front_elevation_gimbal.jpg": ("REJECT", "짐벌 중심 크롭 — 프롭 잘림"),
        "matrice4e_p04_front_low_angle.jpg": ("REJECT", "로우앵글 — 강한 원근"),
        "matrice4e_p06_rear_low_angle.jpg": ("REJECT", "로우앵글 — 강한 원근"),
        "matrice4e_p07_iso_front_left.jpg": ("REJECT", "아이소 — 원반면 기울기 큼"),
        "matrice4e_p08_iso_rear_left_low.jpg": ("REJECT", "아이소 — 상동"),
        "matrice4e_p11_front_top_iso.jpg": ("REJECT", "아이소 720 px — 작고 기울었다"),
        "matrice4e_p12_top_front_iso.jpg": ("REJECT", "위-앞 아이소 — 기울기 미상, 보정 기준점 없음"),
        "matrice4e_c03_intelligent_flight_battery.jpg": ("N/A", "배터리"),
        "matrice4e_c04_xray_internal_layout_render.jpg": ("N/A", "내부 X-ray 렌더"),
    }
    files = sorted(p.name for p in PHOTO.glob("*") if p.suffix.lower() in (".jpg", ".png"))
    rows = []
    for f in files:
        if f in verdicts:
            v, why = verdicts[f]
        elif f.startswith("matrice4e_t"):
            v, why = "N/A", "분해(teardown) 사진 — 프롭 없음"
        elif f.startswith("matrice4e_m"):
            v, why = "N/A", "매뉴얼 선화 세부(짐벌·배터리·포트 등) — 프롭 평면형 없음"
        elif f.startswith("matrice 4E_"):
            v, why = "REJECT", "제품 아이소 렌더 — 원반면이 기울어 투영 호폭이 압축된다"
        else:
            v, why = "N/A", "분류 안 됨"
        rows.append(dict(file=f, verdict=v, why=why))
    doc["N_photo_screening"] = dict(
        folder="assets/photos/matrice4e/", n_files=len(files),
        n_used=sum(1 for r in rows if r["verdict"].startswith("USED")),
        provenance="c01·c02 의 출처 URL 은 폴더 SOURCES.md 173~174 행에 있다 "
                   "(DJI 스토어 CDN, standard/low-noise propellers)",
        rows=rows,
        note="⭐프롭 «평면형» 을 잴 수 있는 사진은 폴더 %d 장 중 **3 장**뿐이고, 그중 계측 등급은 "
             "부품 렌더 2 장이다" % len(files),
    )

    doc["_elapsed_s"] = round(time.time() - t0, 1)
    return doc


if __name__ == "__main__":
    if OUT.exists() and not PASS1.exists():
        shutil.copy2(OUT, PASS1)
    d = main()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    hb = d["B_1157F_standard"]["headline"]
    print("1157F  c_max/R(투영) = %.5f  peak %.3fR  c_max %.2f mm  날면적(0.20-0.96R) %.1f mm²"
          % (hb["c_max_over_R_projected"], hb["peak_r_over_R"], hb["c_max_mm"],
             hb["blade_area_020_096_mm2"]))
    hc = d["C_1154F_low_noise"]["headline"]
    print("1154F  c_max/R(투영) = %.5f  peak %.3fR  c_max %.2f mm  날면적 %.1f mm²"
          % (hc["c_max_over_R_projected"], hc["peak_r_over_R"], hc["c_max_mm"],
             hc["blade_area_020_096_mm2"]))
    print("참(설계)시위 권고 1157F c_max/R =", d["I_recommended_constant"]["recommended"],
          d["F_deprojection_to_true_chord"]["pitch_law_centre_and_band_1157F"]["band"])
    print("잣대 검정 해상도편향 %.3f %%  기울기 ±10° 최악 %.2f %%"
          % (d["A_ruler_calibration"]["resolution_bias_pct"]["c_max_over_R"],
             d["A_ruler_calibration"]["tilt_sensitivity"]["worst_within_10deg_pct"]))
    print("→", OUT)
