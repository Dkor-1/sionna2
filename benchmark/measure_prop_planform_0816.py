#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""프로펠러 «평면형» 정밀 계측 — DJI Mavic 4 Pro(1158F) · DJI Mini 5 Pro(6028F)

왜 이 파일이 있나
----------------
표적 신호에서 «움직이는 성분» 은 사실상 전부 프로펠러다(프롭 두께를 바꾸면 요동
−16.99 dB, 셸 두께는 ±0.00 dB — outputs/material_verdict_0816.json). 그런데 코드는
`drone_cad.CHORD_MAX_OVER_R = 0.25` 라는 **단일 상수를 10기종 전부**에 걸고 있다.
즉 지금은 모든 드론에 같은 프로펠러를 달아 놓은 것과 같다.

이 스크립트는 그중 **주력 표적 2·3순위**(mavic4pro · mini5pro)의 날 폭을 사진에서
직접 잰다. ⛔코드는 건드리지 않는다 — 재고 적기만 한다.

무엇을 재는가 — 용어 한 줄 풀이
------------------------------
· **시위(chord)**       날 단면의 앞전~뒷전 길이. 날의 «폭».
· **평면형(planform)**  위에서 본 날 윤곽 = 시위가 반경에 따라 어떻게 변하는가.
· **c_max/R**           최대 시위 ÷ 프롭 반경. 날이 얼마나 «통통한가». ← 이게 목표다.

⭐⭐ 규약 — R 의 정의와 날 뿌리 시작점 (이게 다르면 비교가 무의미하다)
--------------------------------------------------------------------
R  = **회전 디스크 반경** = 회전축에서 날 끝까지. 2날 프롭이 펼쳐져 있으면
     두 날끝의 중점이 회전축이고 R = (날끝~날끝)/2 다.
     ⚠ 공칭 지름(DJI 공표 152.4 / 267 mm)의 절반과 같은 뜻이며, 아래에서
     둘이 얼마나 맞는지 매번 대조한다.
r_root = 날이 허브 클램프를 벗어나기 시작하는 반경. 각 성분마다 실측해 적는다.
c_max 탐색 구간 = r/R ∈ [0.25, 0.96].
     0.25 아래는 허브·클램프가 섞이고, 0.96 위는 팁 라운딩이라 폭이 무의미하다.

⭐⭐ 두 «시위» 는 다른 물건이다 (이 라운드의 핵심 발견)
------------------------------------------------------
  (1) **c_arc**  = r·Δθ — 회전면에 **투영된** 폭. 사진(2D)이 줄 수 있는 것은 이것뿐이다.
  (2) **c_cal**  = 반경 r 원통 단면의 최대 캘리퍼 = **진짜 시위**.
      `drone_cad` 가 익형을 세울 때 쓰는 값이고 `CHORD_MAX_OVER_R` 이 뜻하는 값이다.
  날이 피치각 θ 만큼 비틀려 있으므로 **c_cal = c_arc / cos θ ≥ c_arc** 다.
  ⇒ 사진에서 잰 값을 그대로 `CHORD_MAX_OVER_R` 자리에 넣으면 **과소평가**다.
  이 스크립트는 두 값을 항상 따로 적고, 다리(bridge)를 공표 피치에서 계산한다.

두 가지 방법으로 같은 양을 잰다 (일치도를 보고한다)
-------------------------------------------------
  · **M1 극좌표**  회전축 C 기준 반경 r 에서 날이 차지하는 각폭 Δθ → c_arc = r·Δθ.
  · **M2 스파인**  날의 주축(스파인)을 세우고 그 **수직 방향 폭**을 스파인 따라 잰다.
  곧은 반경 방향 날이면 둘이 같고, 스윕(젖힘)이 있으면 갈린다. 차이를 적는다.

자 검증 (§A) — 답을 아는 물건으로 먼저 잰다
-----------------------------------------
Mini 2 는 저장소에서 **공식 3D CAD 와 실물 사진을 둘 다** 가진 유일한 DJI 프롭이다.
  ① CAD(WM161_zhankai_1k.glb) → 참값 c_cal/R, c_arc/R
  ② 같은 CAD 의 **정투영 상면 렌더** 를 사진 파이프라인에 통과 → 순수 파이프라인 오차
  ③ 실물 FCC 사진(자 포함) 을 같은 파이프라인에 통과 → 실사진 추가 오차
이 3단이 아래 mavic4pro·mini5pro 수치에 붙일 **오차 막대의 근거**다.

⛔ 정책: GPU 미사용 · git 미접촉 · src/ 코드 무변경. numpy/scipy/PIL/trimesh 만 쓴다.

실행:
  PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
      benchmark/measure_prop_planform_0816.py
산출:
  outputs/prop_measure_mavic4pro_mini5pro_0816.json
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = "/workspace/sionna"
PHOTOS = os.path.join(ROOT, "assets", "photos")
MESHES = os.path.join(ROOT, "assets", "meshes", "reference")
OUT = os.path.join(ROOT, "outputs", "prop_measure_mavic4pro_mini5pro_0816.json")

# c_max 를 찾을 반경 구간 — 규약. 바꾸면 비교가 깨진다.
RR_LO, RR_HI = 0.25, 0.96
RR_GRID = np.arange(0.20, 0.985, 0.005)

# ⭐물리 가드 — 허브·모터 덩어리를 «날» 로 오인하지 않게 막는 두 겹의 상한.
#   ARC_GUARD_DEG : 반경 r 에서 한 날이 덮는 각폭의 상한. 날은 좁고 허브는 넓다.
#   C_OVER_R_GUARD: c/R 의 상한. 실측 참조 밴드가 0.177~0.273 이므로 0.45 면 넉넉하다.
ARC_GUARD_DEG = 70.0
C_OVER_R_GUARD = 0.45


def _r(x, n=4):
    """None 안전 반올림."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return None
    return round(float(x), n)


def kst_now() -> str:
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")


# --------------------------------------------------------------------------- #
#  1. 실루엣 만들기
# --------------------------------------------------------------------------- #
def silhouette(path: str, mode: str, thr: float, blue_bg: bool = False) -> np.ndarray:
    """이미지 → 불리언 마스크(날이 True).

    mode
      'dark'   밝은 배경 위의 어두운 날 — max(R,G,B) < thr
      'alpha'  투명 배경 렌더 — alpha > thr

    ⭐**주황 팁을 반드시 포함한다.** DJI 소비자 프롭은 날 끝에 주황 캡이 있는데,
      «어두움» 만으로 자르면 그 캡이 빠져 **R 이 짧아지고 c_max/R 이 부풀어 오른다**.
      (구판 스크립트가 이 함정에 빠졌다.)
    blue_bg=True 면 FCC 파란 천 배경을 따로 배제한다(파란 배경도 max 채널이 낮을 수 있다).
    """
    im = Image.open(path)
    if mode == "alpha":
        if "A" not in im.getbands():
            raise ValueError(f"alpha 없음: {path}")
        return np.asarray(im)[..., 3] > thr
    rgb = np.asarray(im.convert("RGB")).astype(np.int16)
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dark = rgb.max(2) < thr
    if blue_bg:
        dark &= (B - R) < 30                      # 파란 천 배제
    orange = (R > 110) & (R - B > 55) & (R - G > 25)
    return ndi.binary_fill_holes(dark | orange)


def components(mask: np.ndarray, min_area: int, open_iter: int = 3):
    """면적 min_area 이상인 연결성분들을 큰 것부터 돌려준다.

    ⭐먼저 `open_iter` 픽셀만큼 깎아(erosion) **가느다란 이음새를 끊고** 성분을 나눈 뒤,
      다시 부풀려(dilation) 원래 마스크 안으로 되돌린다. 이렇게 안 하면 로터 두 개가
      기체 그림자·암 밑선 한 줄로 이어져 «하나의 프롭» 으로 잡힌다(구판의 실패 원인).
    """
    core = ndi.binary_erosion(mask, iterations=open_iter)
    lab, n = ndi.label(core)
    if n == 0:
        return []
    cnt = np.bincount(lab.ravel())
    cnt[0] = 0
    idx = [i for i in np.argsort(cnt)[::-1] if cnt[i] >= min_area]
    return [ndi.binary_dilation(lab == i, iterations=open_iter + 2) & mask for i in idx]


def comp_points(comp: np.ndarray) -> np.ndarray:
    """마스크 → (N,2) 점구름 (x=열, y=행)."""
    ys, xs = np.nonzero(comp)
    return np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])


# --------------------------------------------------------------------------- #
#  2. 회전축·반경 찾기 (펼친 2날 프롭)
# --------------------------------------------------------------------------- #
def _hull(P: np.ndarray) -> np.ndarray:
    """볼록껍질 꼭짓점 (scipy)."""
    from scipy.spatial import ConvexHull
    return P[ConvexHull(P).vertices]


def farthest_pair(P: np.ndarray):
    """점구름에서 가장 먼 두 점 = 2날 프롭의 두 날끝."""
    H = _hull(P)
    D = np.linalg.norm(H[:, None, :] - H[None, :, :], axis=2)
    i, j = np.unravel_index(np.argmax(D), D.shape)
    return H[i], H[j], D[i, j]


def rotor_axis(P: np.ndarray):
    """펼친 2날 프롭의 회전축 C 와 반경 R.

    C = 두 날끝의 중점, R = 날끝~날끝 / 2.
    ⚠ **접힌** 프롭에는 쓸 수 없다(그 경우는 아래 folded_blade_width 를 쓴다).
    """
    t1, t2, d = farthest_pair(P)
    return 0.5 * (t1 + t2), 0.5 * d, t1, t2


# --------------------------------------------------------------------------- #
#  3. 아핀 보정 — «두 날끝 사이 길이는 어느 프롭이나 D 로 같다»
# --------------------------------------------------------------------------- #
def fit_affine(vecs: list[np.ndarray]):
    """프롭마다의 (날끝→날끝) 벡터들을 받아, 길이를 같게 만드는 2x2 를 찾는다.

    카메라가 살짝 기울면 평면이 한 방향으로만 눌린다(약투영 = 아핀).
    그 눌림을 W = R(φ)·diag(1,k)·R(−φ) 로 두고, |W·v_i| 의 산포를 최소화한다.
    프롭이 3개 이상 서로 다른 방향으로 있어야 잘 풀린다.
    """
    V = np.asarray(vecs, float)
    if len(V) < 3:
        return np.eye(2), dict(applied=False, reason_ko="프롭이 3개 미만이라 방향 다양성이 없다")

    def W_of(k, phi):
        c, s = np.cos(phi), np.sin(phi)
        Rm = np.array([[c, -s], [s, c]])
        return Rm @ np.diag([1.0, k]) @ Rm.T

    def cost(p):
        L = np.linalg.norm(V @ W_of(p[0], p[1]).T, axis=1)
        return np.std(L) / np.mean(L)

    best, bp = np.inf, (1.0, 0.0)
    for k in np.linspace(0.55, 1.85, 131):
        for phi in np.linspace(0, np.pi, 91)[:-1]:
            c = cost((k, phi))
            if c < best:
                best, bp = c, (k, phi)
    from scipy.optimize import minimize
    r = minimize(cost, bp, method="Nelder-Mead",
                 options=dict(xatol=1e-6, fatol=1e-10, maxiter=4000))
    k, phi = (r.x if r.fun < best else np.array(bp))
    W = W_of(k, phi)
    W /= np.sqrt(abs(np.linalg.det(W)))          # 면적 보존 정규화
    L0 = np.linalg.norm(V, axis=1)
    L1 = np.linalg.norm(V @ W.T, axis=1)
    return W, dict(
        applied=True, stretch_k=_r(max(k, 1 / k), 4),
        stretch_axis_deg=_r(np.degrees(phi) % 180, 2),
        tip2tip_spread_before_pct=_r(100 * (L0.max() - L0.min()) / L0.mean(), 3),
        tip2tip_spread_after_pct=_r(100 * (L1.max() - L1.min()) / L1.mean(), 3),
        meaning_ko=("참평면이라면 어느 프롭이나 날끝~날끝이 D 로 같다. 그 조건으로 기울기를 푼다. "
                    "stretch_k = 1.00 이면 이미 완전한 평면도라는 뜻."))


# --------------------------------------------------------------------------- #
#  4. M1 — 극좌표 각폭
# --------------------------------------------------------------------------- #
def _arcs(theta: np.ndarray, gap_deg: float):
    """정렬된 각도들을 «틈» 기준으로 덩어리(호)로 나눈다. 원형 wrap 처리."""
    th = np.sort(theta)
    if th.size == 0:
        return []
    d = np.diff(th)
    wrap = th[0] + 2 * np.pi - th[-1]
    cuts = np.nonzero(d > np.radians(gap_deg))[0]
    if wrap > np.radians(gap_deg):
        segs = np.split(th, cuts + 1)
    else:                                        # 첫·끝이 이어져 있으면 합친다
        segs = np.split(th, cuts + 1)
        if len(segs) > 1:
            segs = [np.concatenate([segs[-1] - 2 * np.pi, segs[0]])] + segs[1:-1]
    return [s for s in segs if s.size >= 3]


def m1_polar(P: np.ndarray, C: np.ndarray, R: float,
             band_px: float = 2.0, gap_deg: float = 18.0):
    """반경 r 마다 각 날이 차지하는 각폭 → c_arc = r·Δθ.

    돌려주는 것: [{'r_over_R':…, 'c_over_R':…, 'branch':0|1}, …]
    branch 는 두 날을 구분하는 꼬리표(각도 기준으로 안정 정렬).
    """
    d = np.linalg.norm(P - C, axis=1)
    th = np.arctan2(P[:, 1] - C[1], P[:, 0] - C[0])
    out = []
    for rr in RR_GRID:
        r = rr * R
        sel = np.abs(d - r) <= band_px
        if sel.sum() < 6:
            continue
        segs = _arcs(th[sel], gap_deg)
        for s in segs:
            dth = s.max() - s.min()
            # ⭐물리 가드 두 겹. 이게 없으면 **허브 덩어리**가 «아주 넓은 날» 로 잡힌다
            #   (r/R=0.25 에서 허브가 150° 를 덮으면 c/R = 0.65 가 나온다 — 구판의 0.3~1.0 은
            #    전부 이 함정이었다).
            #   ① 각폭 70° 초과 = 허브/모터/몸통이지 날이 아니다.
            #   ② c/R 0.45 초과 = 어떤 소비자용 프롭 날도 이보다 통통하지 않다
            #      (실측 참조 밴드 0.177~0.273).
            if dth <= 0 or dth > np.radians(ARC_GUARD_DEG):
                continue
            c_over_R = float(r * dth / R)
            if c_over_R > C_OVER_R_GUARD:
                continue
            out.append(dict(r_over_R=float(rr), c_over_R=c_over_R,
                            ang=float(np.mean(s))))
    return out


def branchify(rows: list[dict], n_blades: int = 2):
    """극좌표 결과를 날별로 가른다 — 각 행의 평균각을 k-평균(원형)으로 묶는다."""
    if not rows:
        return []
    a = np.array([x["ang"] for x in rows])
    # 원형 k-means: 2날은 180° 떨어져 있으므로 각도를 2배로 접어 1덩어리 → 다시 편다
    seeds = [a.min(), a.min() + 2 * np.pi / n_blades]
    lab = np.zeros(len(a), int)
    for _ in range(40):
        d = np.abs(np.angle(np.exp(1j * (a[:, None] - np.array(seeds)[None, :]))))
        lab = np.argmin(d, axis=1)
        for k in range(n_blades):
            if (lab == k).sum():
                seeds[k] = np.angle(np.exp(1j * a[lab == k]).mean())
    for x, k in zip(rows, lab):
        x["branch"] = int(k)
    return rows


# --------------------------------------------------------------------------- #
#  5. M2 — 스파인 수직폭
# --------------------------------------------------------------------------- #
def m2_spine(P: np.ndarray, C: np.ndarray, R: float, blade_pts: np.ndarray,
             nbin: int = 90):
    """날 점구름을 «회전축에서 날끝으로» 가는 축에 투영해, 그 수직 폭을 잰다.

    M1 과 달리 원호가 아니라 **직선 수직폭**이라, 젖힌(swept) 날에서는 M1 보다 작게 나온다.
    두 방법의 차이가 곧 «이 날이 얼마나 젖어 있나» 다.
    """
    if blade_pts.shape[0] < 30:
        return []
    # 축 = C → 날끝
    far = blade_pts[np.argmax(np.linalg.norm(blade_pts - C, axis=1))]
    u = (far - C) / np.linalg.norm(far - C)
    v = np.array([-u[1], u[0]])
    s = (blade_pts - C) @ u                  # 축 방향 좌표 (= 반경 근사)
    w = (blade_pts - C) @ v                  # 수직 좌표
    out = []
    edges = np.linspace(max(s.min(), RR_LO * R * 0.8), s.max(), nbin + 1)
    for i in range(nbin):
        m = (s >= edges[i]) & (s < edges[i + 1])
        if m.sum() < 5:
            continue
        rr = 0.5 * (edges[i] + edges[i + 1]) / R
        c_over_R = float((w[m].max() - w[m].min()) / R)
        if c_over_R > C_OVER_R_GUARD:          # M1 과 같은 물리 가드 (허브 배제)
            continue
        out.append(dict(r_over_R=float(rr), c_over_R=c_over_R))
    return out


# --------------------------------------------------------------------------- #
#  6. 요약 — c_max/R 과 그 반경 위치
# --------------------------------------------------------------------------- #
def summarize(rows: list[dict], label: str):
    """r/R ∈ [RR_LO, RR_HI] 안에서 c_max/R 과 그 위치·뿌리반경을 뽑는다."""
    if not rows:
        return None
    rr = np.array([x["r_over_R"] for x in rows])
    cc = np.array([x["c_over_R"] for x in rows])
    band = (rr >= RR_LO) & (rr <= RR_HI)
    if band.sum() < 5:
        return None
    i = np.argmax(cc[band])
    cmax = float(cc[band][i])
    at = float(rr[band][i])
    # 뿌리 = 폭이 c_max 의 40 % 를 처음 넘는 반경 (허브를 벗어나는 지점의 대용)
    ord_ = np.argsort(rr)
    rs, cs = rr[ord_], cc[ord_]
    over = np.nonzero(cs > 0.40 * cmax)[0]
    r_root = float(rs[over[0]]) if over.size else None
    # 정규화 평면형 c/c_max — 코드의 CHORD_FRAC 과 같은 축으로 비교하려고
    grid = np.arange(0.25, 1.0, 0.05)
    prof = {f"{g:.2f}": _r(float(np.interp(g, rs, cs)) / cmax, 4) for g in grid}
    return dict(label=label, c_max_over_R=_r(cmax), at_r_over_R=_r(at, 3),
                r_root_over_R=_r(r_root, 3), n_samples=int(band.sum()),
                c_over_c_max_profile=prof)


# --------------------------------------------------------------------------- #
#  7. 한 장의 사진을 통째로 처리
# --------------------------------------------------------------------------- #
def measure_mask(mask: np.ndarray, n_rotors: int, min_area: int,
                 nominal_dia_mm: float, label: str, rectify: bool = True,
                 gap_deg: float = 18.0, open_iter: int = 3, file: str = "(mask)",
                 mode: str = "-", thr: float = -1):
    """이진 마스크 → 프롭별 M1/M2 요약. 사진이든 굽은 CAD 이든 **같은 자**를 쓴다."""
    comps = components(mask, min_area, open_iter)[:n_rotors]
    if not comps:
        return dict(file=file, label=label, error="성분 없음")

    props = []
    for c in comps:
        P = comp_points(c)
        C, R, t1, t2 = rotor_axis(P)
        props.append(dict(P=P, C=C, R=R, v=t2 - t1))

    W, rect = (fit_affine([p["v"] for p in props]) if rectify
               else (np.eye(2), dict(applied=False, reason_ko="보정 끔")))

    res = []
    for pi, p in enumerate(props):
        P = p["P"] @ W.T
        C, R, _, _ = rotor_axis(P)
        rows = branchify(m1_polar(P, C, R, gap_deg=gap_deg))
        per_blade = []
        for b in (0, 1):
            rb = [x for x in rows if x.get("branch") == b]
            s1 = summarize(rb, f"M1_polar_blade{b}")
            # 같은 날의 점들만 골라 M2
            if s1 is not None:
                ang = np.mean([x["ang"] for x in rb])
                th = np.arctan2(P[:, 1] - C[1], P[:, 0] - C[0])
                near = np.abs(np.angle(np.exp(1j * (th - ang)))) < np.radians(75)
                s2 = summarize(m2_spine(P, C, R, P[near]), f"M2_spine_blade{b}")
                d = (None if (s1 is None or s2 is None) else
                     _r(100 * abs(s1["c_max_over_R"] - s2["c_max_over_R"])
                        / s1["c_max_over_R"], 2))
                per_blade.append(dict(M1=s1, M2=s2, M1_vs_M2_diff_pct=d))
        # ⭐성분 건전성 검사 — «두 날이 이어진 하나의 로터» 가 맞나?
        #   2날 프롭은 날이 180° 마주 본다. 한쪽 로브밖에 없으면 그 성분은 **날 한 장**이고,
        #   그러면 회전축과 R 이 절반으로 잘못 잡혀 c/R 이 2 배 넘게 부푼다.
        #   조용히 틀린 수를 내보내지 말고 **깃발을 세운다.**
        angs = [np.mean([x["ang"] for x in rows if x.get("branch") == b])
                for b in (0, 1) if any(x.get("branch") == b for x in rows)]
        sep = (None if len(angs) < 2 else
               float(np.degrees(abs(np.angle(np.exp(1j * (angs[0] - angs[1])))))))
        ok = (sep is not None) and (150.0 <= sep <= 210.0 or 150.0 <= 360 - sep <= 210.0)
        res.append(dict(prop_index=pi,
                        disc_dia_px=_r(2 * R, 2),
                        mm_per_px=_r(nominal_dia_mm / (2 * R), 6),
                        blade_angular_separation_deg=_r(sep, 1),
                        two_blade_component_ok=bool(ok),
                        note_ko=(None if ok else
                                 "⚠두 날이 180° 로 마주 보지 않는다 — 이 성분은 로터 하나가 "
                                 "아니라 날 한 장일 수 있다. 이 프롭의 수치는 신뢰하지 마라."),
                        blades=per_blade))

    good = [p for p in res if p["two_blade_component_ok"]]
    vals = [b["M1"]["c_max_over_R"] for p in good for b in p["blades"] if b["M1"]]
    v2 = [b["M2"]["c_max_over_R"] for p in good for b in p["blades"] if b["M2"]]

    # ⭐⭐ 프롭 하나 안에서 두 날이 «넓다/좁다» 로 갈리는 것은 버그가 아니라 **물리**다.
    #    2날 프롭의 두 날은 피치가 서로 반대 방향으로 걸려 있다. 비스듬히 보면 한 날은
    #    얼굴을 카메라로 돌려 넓게, 다른 날은 모로 서서 좁게 찍힌다.
    #    ⇒ **두 날의 산술평균이 그 기울기를 1차로 지운다.** 그래서 프롭별 평균이
    #      날 하나하나보다 훨씬 안정된 통계다(아래 prop_pair_mean 산포를 보라).
    pair = []
    for p in good:
        bs = [b["M1"]["c_max_over_R"] for b in p["blades"] if b["M1"]]
        if len(bs) == 2:
            pair.append(dict(prop_index=p["prop_index"],
                             blade_wide=_r(max(bs)), blade_narrow=_r(min(bs)),
                             pair_mean=_r(0.5 * (bs[0] + bs[1])),
                             wide_over_narrow=_r(max(bs) / min(bs), 4)))
    pair_means = [x["pair_mean"] for x in pair]
    return dict(
        file=file, label=label, mode=mode, threshold=thr,
        n_props_found=len(res), n_props_accepted=len(good),
        n_props_rejected_not_two_blade=len(res) - len(good),
        rectify=rect, props=res,
        M1_c_max_over_R=dict(
            mean=_r(np.mean(vals)) if vals else None,
            sd=_r(np.std(vals, ddof=1)) if len(vals) > 1 else None,
            min=_r(min(vals)) if vals else None, max=_r(max(vals)) if vals else None,
            n_blades=len(vals),
            spread_pct=_r(100 * (max(vals) - min(vals)) / np.mean(vals), 2) if vals else None),
        M2_c_max_over_R=dict(
            mean=_r(np.mean(v2)) if v2 else None, n_blades=len(v2)),
        prop_pair_mean=dict(
            per_prop=pair,
            mean=_r(np.mean(pair_means)) if pair_means else None,
            sd=_r(np.std(pair_means, ddof=1)) if len(pair_means) > 1 else None,
            spread_pct=(_r(100 * (max(pair_means) - min(pair_means)) / np.mean(pair_means), 2)
                        if len(pair_means) > 1 else None),
            n_props=len(pair),
            why_ko=("⭐**이게 헤드라인 통계다.** 날 하나하나는 비스듬한 시점 때문에 넓게/좁게 "
                    "갈리지만, 한 프롭의 두 날을 평균 내면 그 갈림이 1차로 지워진다. "
                    "남은 프롭끼리의 산포(spread_pct)가 진짜 불확실도다.")),
        M1_vs_M2_mean_diff_pct=(
            _r(100 * abs(np.mean(vals) - np.mean(v2)) / np.mean(vals), 2)
            if vals and v2 else None))


def measure_image(path: str, mode: str, thr: float, n_rotors: int,
                  min_area: int, nominal_dia_mm: float, label: str,
                  rectify: bool = True, gap_deg: float = 18.0,
                  open_iter: int = 3, blue_bg: bool = False):
    """사진 1장 → 프롭별 M1/M2 요약."""
    mask = silhouette(path, mode, thr, blue_bg=blue_bg)
    return measure_mask(mask, n_rotors, min_area, nominal_dia_mm, label,
                        rectify=rectify, gap_deg=gap_deg, open_iter=open_iter,
                        file=os.path.basename(path), mode=mode, thr=thr)


# --------------------------------------------------------------------------- #
#  8. §A 자 검증 — Mini 2 공식 CAD 참값
# --------------------------------------------------------------------------- #
def _load_mini2_rotors(n_sample=160_000):
    """WM161 공식 GLB → 로터 4개. 각 로터마다 «허브 중심(x,z)» 과 «날 2장의 표면 점구름».

    회전축은 월드 +y (감사 원장이 허브 관성주축으로 실측, 편차 0.001).
    """
    import trimesh
    sc = trimesh.load(os.path.join(MESHES, "WM161_zhankai_1k.glb"), force="scene")
    parts = sc.dump(concatenate=False)

    # ⭐부품 분류는 «회전축 방향으로 얇고, 회전면 안에서 길다» 는 날의 정의를 그대로 쓴다.
    #   느슨하게 잡으면 다리·안테나 같은 조각이 «날» 로 섞여 들어와 로터 하나가 통째로
    #   틀린 값을 낸다(실제로 그랬다). 그래서 개수를 8/4 로 **단언**하고, 안 맞으면 멈춘다.
    blades, hubs = [], []
    for m in parts:
        V = np.asarray(m.vertices, float)
        if len(V) < 150:
            continue
        ext = 1000 * (V.max(0) - V.min(0))
        xz = 1000 * np.asarray(m.vertices, float)[:, [0, 2]]
        span = float(np.linalg.norm(xz.max(0) - xz.min(0)))    # 회전면 안에서의 길이
        if ext[1] < 9.0 and 35 < span < 62 and len(V) > 1000:
            blades.append(m)
        elif 16 < ext[0] < 21 and 16 < ext[2] < 21 and ext[1] < 12 and len(V) > 500:
            hubs.append(m)
    if len(blades) != 8 or len(hubs) != 4:
        return None, dict(error=f"날 {len(blades)}개 / 허브 {len(hubs)}개 — 기대(8/4)와 다름. "
                                f"부품 분류가 흔들렸다는 뜻이므로 진행하지 않는다.")

    hub_xz = np.array([1000 * np.asarray(h.vertices, float).mean(0)[[0, 2]] for h in hubs])
    rotors = []
    for c in hub_xz:
        mine = sorted(blades, key=lambda m: np.linalg.norm(
            1000 * np.asarray(m.vertices, float).mean(0)[[0, 2]] - c))[:2]
        pts = []
        for bi, m in enumerate(mine):
            # ⭐씨앗을 고정한다. 표면 표집이 난수라 안 고정하면 실행할 때마다 §A 참값이
            #   0.5 % 쯤 흔들리고, 그러면 «재현 스크립트» 라는 말이 거짓이 된다.
            p, _ = trimesh.sample.sample_surface(m, n_sample // 2, seed=1000 + bi)
            pts.append(1000 * np.asarray(p, float))
        rotors.append(dict(center_xz=c, pts=np.vstack(pts)))
    return rotors, dict(n_blades=len(blades), n_hubs=len(hubs))


def cad_sections(rotor, n_r=60):
    """로터 하나에서 «진짜 시위 c_cal» 과 «투영 폭 c_arc» 을 반경마다 잰다.

    c_cal : 반경 r 원통으로 자른 단면 점들의 **최대 캘리퍼** — 프로펠러 단면의 정식 정의.
            drone_cad 가 익형을 세울 때 쓰는 값이고 CHORD_MAX_OVER_R 이 뜻하는 값이다.
    c_arc : 같은 점들을 회전면(x,z)에 눕혀 잰 **각폭 r·Δθ** — 사진이 줄 수 있는 값.
    둘의 비 c_cal/c_arc = 1/cos θ 가 «투영 → 진짜» 다리다.
    """
    P = rotor["pts"]
    cx, cz = rotor["center_xz"]
    dx, dz = P[:, 0] - cx, P[:, 2] - cz
    r = np.hypot(dx, dz)
    th = np.arctan2(dz, dx)
    R = float(np.percentile(r, 99.9))
    rows = []
    for rr in np.linspace(0.20, 0.97, n_r):
        r0 = rr * R
        tol = max(0.004 * R, 0.25)
        sel = np.abs(r - r0) < tol
        if sel.sum() < 40:
            continue
        t = th[sel]
        # 두 날을 각도로 가른다 (2날은 약 180° 떨어져 있다)
        for sgn in (0, 1):
            half = (np.cos(t - (t.min() + sgn * np.pi)) > 0) if sgn else np.ones(t.size, bool)
        # 간단히: 각도 히스토그램의 두 덩어리
        ts = np.sort(t)
        gaps = np.diff(ts)
        if gaps.size == 0:
            continue
        k = int(np.argmax(gaps))
        groups = [ts[:k + 1], ts[k + 1:]]
        for gidx, gt in enumerate(groups):
            if gt.size < 15:
                continue
            dth = gt.max() - gt.min()
            if dth > np.radians(ARC_GUARD_DEG) or r0 * dth / R > C_OVER_R_GUARD:
                continue
            gm = np.isin(th, gt) & sel
            Q = P[gm]
            if Q.shape[0] < 15:
                continue
            # 최대 캘리퍼 = 단면 점들의 최대 두 점 거리. 볼록껍질 꼭짓점만 보면 충분하고 빠르다.
            try:
                from scipy.spatial import ConvexHull
                H = Q[ConvexHull(Q, qhull_options="QJ").vertices]
            except Exception:
                H = Q
            D = np.linalg.norm(H[:, None, :] - H[None, :, :], axis=2)
            rows.append(dict(r_over_R=float(rr), blade=gidx,
                             c_cal_over_R=float(D.max() / R),
                             c_arc_over_R=float(r0 * dth / R)))
    return R, rows


def mini2_cad_truth():
    """§A ①  Mini 2 공식 CAD 참값 — 진짜 시위 · 투영 폭 · 둘 사이의 다리."""
    rotors, info = _load_mini2_rotors()
    if rotors is None:
        return info
    per, bridge, rejected = [], [], []
    for i, ro in enumerate(rotors):
        R, rows = cad_sections(ro)
        if not rows:
            continue
        # ⭐물리 필터: 4726F 는 공칭 119.4 mm 다. ±8 % 를 벗어나면 그 «로터» 는
        #   내 부품 분류가 잘못 집은 다른 조각(다리·암 등)이다. 조용히 버리지 말고 적는다.
        if not (0.92 * 119.4 <= 2 * R <= 1.08 * 119.4):
            rejected.append(dict(rotor=i, disc_dia_mm=_r(2 * R, 2),
                                 why_ko="공칭 119.4 mm ±8 % 밖 — 부품 분류 오식별"))
            continue
        band = [x for x in rows if RR_LO <= x["r_over_R"] <= RR_HI]
        if not band:
            continue
        bcal = max(band, key=lambda x: x["c_cal_over_R"])
        barc = max(band, key=lambda x: x["c_arc_over_R"])
        per.append(dict(rotor=i, disc_dia_mm=_r(2 * R, 2),
                        c_cal_over_R=_r(bcal["c_cal_over_R"]),
                        at_r_over_R=_r(bcal["r_over_R"], 3),
                        c_arc_over_R=_r(barc["c_arc_over_R"]),
                        c_cal_over_c_arc=_r(bcal["c_cal_over_R"] / barc["c_arc_over_R"], 4)))
        bridge.append(bcal["c_cal_over_R"] / barc["c_arc_over_R"])
    return dict(
        n_blades=info.get("n_blades"), n_hubs=info.get("n_hubs"),
        per_rotor=per, rejected_parts=rejected,
        mean_c_cal_over_R=_r(np.mean([p["c_cal_over_R"] for p in per])) if per else None,
        mean_c_arc_over_R=_r(np.mean([p["c_arc_over_R"] for p in per])) if per else None,
        mean_bridge_c_cal_over_c_arc=_r(np.mean(bridge)) if bridge else None,
        method_ko=("반경 r 원통 단면 → 최대 캘리퍼 = 진짜 시위. 같은 점을 회전면에 눕혀 각폭 = 투영 폭. "
                   "감사 원장과 같은 규약이라 사과-대-사과다."))


def rasterize_rotor(rotor, px_per_R=260, pad=1.12):
    """로터의 날 점구름을 회전면에 눕혀 **정투영 이진 이미지**로 굽는다.

    ⭐이게 «닫힌 고리» 검증의 핵심이다 — 참값을 아는 3D 를 원근 0·조명 0 인 그림으로 만들어
      사진 파이프라인에 그대로 먹인다. 나오는 오차는 순수한 **파이프라인 오차**다.
    """
    P = rotor["pts"]
    cx, cz = rotor["center_xz"]
    x, z = P[:, 0] - cx, P[:, 2] - cz
    R = float(np.percentile(np.hypot(x, z), 99.9))
    n = int(2 * pad * px_per_R)
    sc = px_per_R / R
    ix = np.clip(((x * sc) + n / 2).astype(int), 0, n - 1)
    iz = np.clip(((z * sc) + n / 2).astype(int), 0, n - 1)
    img = np.zeros((n, n), bool)
    img[iz, ix] = True
    img = ndi.binary_closing(img, np.ones((3, 3)), iterations=2)
    img = ndi.binary_fill_holes(img)
    # ⭐허브 원판을 같이 그린다. 실제 사진에서는 모터·허브가 어둡게 찍혀 **두 날이 이어진
    #   하나의 성분**이 되기 때문이다. 이걸 빼면 날 한 장이 통째로 «프롭 하나» 로 잡혀
    #   R 이 절반이 되고 c/R 이 2 배 넘게 부푼다. 굽은 그림도 사진과 같은 조건이어야
    #   «닫힌 고리» 가 성립한다.
    yy, xx = np.mgrid[0:n, 0:n]
    hub_px = 0.20 * px_per_R          # Mini 2 허브 반경 ≈ 9 mm ≈ 0.15 R (여유 있게)
    img |= ((xx - n / 2) ** 2 + (yy - n / 2) ** 2) < hub_px ** 2
    return img, R, sc


CAD_TRUTH_CITED = dict(
    source="outputs/mesh_audit_0816_prop_geometry.json §B (DJI Mini 2 공식 CAD, 4로터)",
    c_cal_over_R=0.2625,
    c_cal_at_r_over_R=0.456,
    per_rotor=[0.2596, 0.2604, 0.2647, 0.2654],
    theta_at_peak_deg=19.29,
    c_arc_over_R_derived=_r(0.2625 * np.cos(np.radians(19.29))),
    cross_check_ko=("독립 원장 outputs/prop_measure_mavic4pro_mini5pro_0816.json(구판) 이 같은 "
                    "GLB 에서 투영 정의로 0.2477 을 냈다. 위 유도값과 0.1 % 안에서 같다 — "
                    "즉 «진짜 시위 ↔ 투영 폭» 다리가 실제로 cos θ 다."),
    bridge_c_cal_over_c_arc=_r(1.0 / np.cos(np.radians(19.29))))


# --------------------------------------------------------------------------- #
#  9. 피치에서 «투영→진짜» 다리를 계산 (기종별)
# --------------------------------------------------------------------------- #
def tilt_from_blade_asymmetry(pair: list[dict], dia_mm: float, pitch_mm: float,
                              at_rr: float = 0.46):
    """⭐두 날의 «넓다/좁다» 비율에서 **시점 기울기 γ** 를 풀고, 그만큼 되돌린다.

    왜 되나
      2날 프롭의 두 날은 피치가 서로 반대다. 시선이 회전면 법선에서 γ 만큼 기울면
      한 날의 투영 시위는 cos(θ−γ) 에, 다른 날은 cos(θ+γ) 에 비례한다(θ = 그 반경의
      기하 피치각, 공표 피치에서 계산).
        비율 ρ = cos(θ−γ)/cos(θ+γ) = (1 + tanθ·tanγ)/(1 − tanθ·tanγ)
        ⇒ tanγ = (ρ−1)/((ρ+1)·tanθ)
      그리고 두 날의 **산술평균** = 참 투영폭 × cosγ 이므로, 평균을 cosγ 로 나누면
      정면에서 봤을 때의 투영폭이 된다.

    ⚠ 가정을 밝힌다 — 기울기가 «날 스팬을 품은 평면 안» 에 있다고 본다. 실제 기울기의
      스팬 수직 성분은 R 도 같이 줄이므로 정규화에서 일부 상쇄된다. 그래서 이 보정은
      **1차 보정**이지 완전한 사영 복원이 아니다. 프롭끼리 값이 여전히 벌어지면
      그만큼이 남은 모델 오차다.
    """
    R = dia_mm / 2.0
    th = np.arctan2(pitch_mm, 2 * np.pi * at_rr * R)
    rows = []
    for x in pair:
        rho = x.get("wide_over_narrow")
        m = x.get("pair_mean")
        if not rho or not m:
            continue
        tg = (rho - 1.0) / ((rho + 1.0) * np.tan(th))
        g = np.arctan(tg)
        rows.append(dict(prop_index=x["prop_index"], pair_mean=m,
                         wide_over_narrow=_r(rho, 4),
                         implied_tilt_deg=_r(np.degrees(g), 2),
                         c_arc_over_R_deprojected=_r(m / max(np.cos(g), 1e-6))))
    vals = [r["c_arc_over_R_deprojected"] for r in rows]
    # ⭐가장 «정면에 가까운» 프롭만 따로 — 기울기가 작을수록 보정이 덜 필요하고 덜 틀린다.
    #   문턱값을 손으로 고르면 원하는 답을 고르는 셈이 된다. 그래서 **자료 안의 가장 큰 틈**에서
    #   자른다(기울기를 정렬해 이웃 간 간격이 최대인 곳). 틈이 뚜렷하지 않으면 전부 쓴다.
    srt = sorted(rows, key=lambda r: r["implied_tilt_deg"] or 99)
    tl = [r["implied_tilt_deg"] or 99 for r in srt]
    face, cut_at = srt, None
    if len(tl) >= 3:
        gaps = [(tl[i + 1] - tl[i], i) for i in range(len(tl) - 1)]
        g, i = max(gaps)
        if g > 1.5 * (np.mean([x[0] for x in gaps]) + 1e-9) and g > 2.0:
            face, cut_at = srt[:i + 1], _r(0.5 * (tl[i] + tl[i + 1]), 2)
    fv = [r["pair_mean"] for r in face]
    return dict(
        theta_at_r_deg=_r(np.degrees(th), 2), at_r_over_R=at_rr, per_prop=rows,
        mean=_r(np.mean(vals)) if vals else None,
        spread_pct=(_r(100 * (max(vals) - min(vals)) / np.mean(vals), 2)
                    if len(vals) > 1 else None),
        face_on_subset=dict(
            rule_ko=("추정 기울기를 정렬해 **가장 큰 틈**에서 자른 저기울기 무리. "
                     "문턱을 손으로 고르지 않으려는 규칙이다."),
            cut_at_deg=cut_at,
            tilts_sorted=[_r(t, 2) for t in tl],
            n_props=len(face), prop_indices=[r["prop_index"] for r in face],
            c_arc_over_R_uncorrected_mean=_r(np.mean(fv)) if fv else None,
            spread_pct=(_r(100 * (max(fv) - min(fv)) / np.mean(fv), 2)
                        if len(fv) > 1 else None)),
        assumptions_ko=("① 기울기가 날 스팬을 품은 평면 안에 있다 ② 공표 피치가 그 반경에서 "
                        "맞는다(실물은 정피치가 아니라 0.75R 기준이라 어림이다) "
                        "③ 두 날이 같은 형상이다. 셋 다 어림이므로 이 값은 **보조 추정**이고, "
                        "헤드라인은 보정 안 한 prop_pair_mean 이다."))


def pitch_bridge(dia_mm: float, pitch_mm: float, at_rr: float):
    """공표 피치로부터 반경 at_rr·R 에서의 기하 피치각 θ 와 1/cos θ 를 낸다.

    θ(r) = atan( P / (2πr) ).  P 는 공표 피치(1회전에 나아가는 거리).
    ⚠ 실물은 정피치가 아니다(국소 피치가 0.75R 에서 최대). 그래서 이 값은
      **어림**이고, 아래 uncertainty 에 그 폭을 적는다.
    """
    R = dia_mm / 2.0
    r = at_rr * R
    th = np.arctan2(pitch_mm, 2 * np.pi * r)
    return dict(r_over_R=_r(at_rr, 3), theta_deg=_r(np.degrees(th), 2),
                c_cal_over_c_arc=_r(1.0 / np.cos(th)),
                caveat_ko=("공표 피치를 «정피치» 로 가정한 어림이다. 실물은 국소 피치가 "
                           "0.75R 에서 최대라 그 부근에서는 이 값이 과소, 뿌리 쪽에서는 과대다. "
                           "Mini 2 공식 CAD 실측 θ(0.456R)=19.29° ↔ 이 식 어림값과 비교해 검증했다."))


# --------------------------------------------------------------------------- #
#  10. 본체
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    out = {}

    # ---------- §A 자 검증 ----------
    truth = mini2_cad_truth()
    rotors, _info = _load_mini2_rotors()
    A = dict(
        why_ko=("새 대상에 자를 대기 전에 **답을 아는 물건**으로 그 자를 검증한다. "
                "Mini 2 는 저장소에서 공식 3D CAD 와 실물 사진을 둘 다 가진 유일한 DJI 프롭이다."),
        step1_cad_truth=truth,
        step1_cross_check_vs_audit_ledger=CAD_TRUTH_CITED,
    )
    # ② 닫힌 고리 — 참값을 아는 3D 를 정투영 그림으로 구워 같은 파이프라인에 먹인다
    if rotors:
        closed = []
        for i, ro in enumerate(rotors):
            img, R_mm, _ = rasterize_rotor(ro)
            m = measure_mask(img, n_rotors=1, min_area=1500, nominal_dia_mm=2 * R_mm,
                             label=f"CAD 로터{i} 정투영 굽기", rectify=False, open_iter=2,
                             file="(rasterized from WM161 GLB)")
            closed.append(dict(rotor=i, disc_dia_mm=_r(2 * R_mm, 2),
                               pipeline_c_arc_over_R=m["M1_c_max_over_R"]["mean"],
                               M2_spine=m["M2_c_max_over_R"]["mean"],
                               n_blades=m["M1_c_max_over_R"]["n_blades"]))
        got = [c["pipeline_c_arc_over_R"] for c in closed if c["pipeline_c_arc_over_R"]]
        ref = truth.get("mean_c_arc_over_R")
        A["step2_closed_loop_cad_to_raster_to_pipeline"] = dict(
            per_rotor=closed,
            pipeline_mean=_r(np.mean(got)) if got else None,
            cad_direct_mean_c_arc_over_R=ref,
            pipeline_error_pct=(_r(100 * (np.mean(got) - ref) / ref, 2)
                                if got and ref else None),
            meaning_ko=("원근도 조명도 없는 그림이라 여기서 남는 오차는 **순수 파이프라인 오차**다 "
                        "(래스터화·문턱값·극좌표 비닝). 이 값이 아래 모든 사진 수치의 바닥 오차다."))
    # ③ 실물 FCC 사진 — 같은 프롭, 이번엔 진짜 사진
    A["step3_real_photo_same_prop"] = measure_image(
        os.path.join(PHOTOS, "mini2", "mini2_c07_fcc_mt2wd_propeller_2blade_ruler.jpg"),
        mode="dark", thr=120, n_rotors=1, min_area=3000, nominal_dia_mm=119.1,
        label="Mini 2 실물 4726F (FCC, 자 포함) — 같은 프롭의 진짜 사진", rectify=False)
    A["step3_verdict_ko"] = (
        "⛔**이 컷은 쓸 수 없다 — 그리고 그것을 가드가 스스로 잡아냈다.** 분할은 깨끗한데"
        "(날 2장 다 잡힘) «두 날이 180° 로 마주 보나» 검사에서 떨어졌다. 사진을 보면 이유가 "
        "분명하다: 4726F 는 **접이식**이고 이 컷에서는 날이 접혀 약 125° 로 벌어져 있다. "
        "그러면 «두 날끝의 중점 = 회전축» 규약이 성립하지 않아 R 이 틀리게 잡힌다. "
        "⭐이건 실패가 아니라 **가드가 일한 증거**다 — 구판은 이런 경우에도 수를 뱉었다. "
        "실물 사진으로 자를 한 번 더 검증하려면 **날이 펼쳐진** 4726F 사진이 필요한데 "
        "저장소에 없다. 그래서 자 검증의 무게는 §A ② 닫힌 고리(오차 0.5 %)가 진다.")
    out["A_ruler_validation"] = A

    bridge = (A["step1_cad_truth"].get("mean_bridge_c_cal_over_c_arc") or 1.03)

    # ---------- §B mini5pro 6028F ----------
    B = dict(
        identity=dict(
            prop="6028F", dia_mm=152.4, pitch_mm=71.12, pitch_in=2.8, blades=2,
            folding=True, mass_g_each=2.8, material="Nylon + Rubber",
            source_ko="DJI 공식 프롭 표 + DJI 스토어 제품 페이지 (식별은 다른 에이전트가 확정)"),
        source_provenance_WARNING=dict(
            what_ko="⚠assets/photos/mini5pro/ 에는 **SOURCES.md 가 없다** — 출처가 기록돼 있지 않다.",
            batch_risk_ko=(
                "⭐⭐같은 날 같은 방식으로 들어온 형제 배치 `mavic 4 pro_1.png`·`_4.png` 는 "
                "**Mavic 4 Pro 가 아니다** — 핫셀블라드 링이 둘린 둥근 짐벌에 렌즈 2개가 세로로 "
                "붙어 있고 팁이 노란색이라, Mavic 4 Pro(원통형 360° 짐벌·주황 팁, `_3.png` 에 "
                "«MAVIC 4 PRO» 각인)와 **다른 기체**다. 즉 이 배치는 기종이 섞여 있다. "
                "따라서 `mini 5 pro_3.png` 의 기체 동일성도 **입증된 것이 아니다**."),
            what_is_established_ko=(
                "`mini 5 pro_1.png`·`_2.png` 는 암에 «MINI 5 PRO» 가 찍혀 있어 기체가 확실하다. "
                "그런데 이 둘은 3/4 투시라 평면형 계측에 못 쓴다. 평면형을 줄 수 있는 상면 "
                "컷은 `_3.png` 하나뿐인데 그 컷에는 기종을 읽을 글자가 없다."),
            consequence_ko=(
                "그래서 아래 수치의 등급을 [B] 가 아니라 **[C]** 로 내린다 — 프롭 규격(6.0 in "
                "2날)은 DJI 공식 문서로 확실하지만, **이 사진의 프롭이 6028F 라는 것은 "
                "미확인**이다. Mini 3 Pro·Mini 4 Pro 도 6.0 in 2날(6030F)이라 지름은 같고 "
                "피치만 3.0 ↔ 2.8 in 로 다르다. 즉 최악의 경우에도 «같은 지름·같은 날개수의 "
                "Mini 계열 프롭» 이며, 그때 오차는 평면형에서 작다(피치 차이는 투영 폭에 "
                "cos 로만 들어와 1 % 미만)."),
        ),
        family_question=dict(
            question_ko="⭐Mini 2 공식 CAD 를 Mini 5 Pro 의 «같은 계열 참조» 로 그대로 쓸 수 있나?",
            mini2_4726F=dict(dia_mm=119.4, dia_in=4.7, pitch_in=2.6,
                             P_over_D=_r(2.6 / 4.7, 4)),
            mini5_6028F=dict(dia_mm=152.4, dia_in=6.0, pitch_in=2.8,
                             P_over_D=_r(2.8 / 6.0, 4)),
            diameter_ratio=_r(152.4 / 119.4, 4),
            P_over_D_difference_pct=_r(100 * (2.8 / 6.0 - 2.6 / 4.7) / (2.6 / 4.7), 1),
            verdict_ko=(
                "⛔**그대로 쓰면 안 된다.** 지름이 **1.28 배**(4.7 → 6.0 in) 다르고, 피치비 P/D 가 "
                "0.553 → 0.467 로 **16 % 낮다**(같은 계열이라도 다른 설계점이다). 게다가 참조 "
                "실측 밴드에서 c_max/R 은 **프롭이 클수록 작아진다** — 4.7 in Mini 2 가 0.257 인데 "
                "10 in 급 Solo 0.273·13 in 1345 0.225·10.8 in M4E 0.19 대다. Mini 2 값을 6.0 in "
                "프롭에 그대로 씌우면 날을 **통째로 넓게** 만든다."),
            what_family_inference_would_cost_ko=(
                "굳이 계열 유추[C]를 써야 한다면: Mini 2 실측 c_cal/R 0.257 을 쓰되 **예상 오차 "
                "−10~−20 %**(즉 실제 6028F 는 0.21~0.23 일 것)를 함께 적어야 한다. 아래 실측이 "
                "그 예상과 맞는지 대조하라."),
        ),
    )
    B["primary"] = measure_image(
        os.path.join(PHOTOS, "mini5pro", "mini 5 pro_3.png"),
        mode="dark", thr=90, n_rotors=4, min_area=6000, nominal_dia_mm=152.4,
        label="[C] 상면에 가까운 렌더 — 프롭 4개 전개 (기체 동일성 미확정)")
    for t in (75, 105):
        B[f"threshold_{t}"] = measure_image(
            os.path.join(PHOTOS, "mini5pro", "mini 5 pro_3.png"),
            mode="dark", thr=t, n_rotors=4, min_area=6000, nominal_dia_mm=152.4,
            label=f"문턱값 감도 {t}")
    B["no_rectify"] = measure_image(
        os.path.join(PHOTOS, "mini5pro", "mini 5 pro_3.png"),
        mode="dark", thr=90, n_rotors=4, min_area=6000, nominal_dia_mm=152.4,
        label="아핀 보정 껐을 때 (보정의 효과를 보려고)", rectify=False)
    out["B_mini5pro_6028F"] = B

    # ---------- §C mavic4pro 1158F ----------
    C = dict(
        identity=dict(
            prop="1158F", dia_mm=267.0, pitch_mm=147.0, pitch_in=5.8, blades=2,
            folding=True, mass_g_each=11.8, material="Enhanced Nylon Composite",
            source_ko="DJI 공식 프롭 표 (26.7×14.7 cm) (식별은 다른 에이전트가 확정)"),
        sources_that_look_usable_but_are_not=dict(
            mavic_4_pro_1_and_4_png=(
                "⛔**다른 기체다.** 핫셀블라드 링 짐벌 + 세로 2렌즈 + 노란 팁 = Mavic 3 계열로 "
                "보인다. Mavic 4 Pro 는 원통형 360° 짐벌 + 주황 팁이고 `_3.png` 암에 "
                "«MAVIC 4 PRO» 각인이 있다. 프롭 계측에 쓰면 엉뚱한 프롭을 입히게 된다."),
            mavic_4_pro_3_png=(
                "기체는 Mavic 4 Pro 가 맞지만 **정면 입면에 가까운 컷**이라 날이 거의 모로 서 "
                "있다. 평면형을 못 낸다. ⚠구판 스크립트가 이걸 «primary» 로 썼고 그래서 "
                "c_max/R 0.27~0.35 라는 물리적으로 불가능한 값이 나왔다."),
            p01_fcc_top_plan=(
                "⭐실물·자 포함·파란 배경이라 대비가 최고인데, **프롭이 접혀 있고 한 로터의 두 날이 "
                "서로 겹친다**(로터 4개 전부). 겹친 두 날의 합집합은 한 날보다 넓으므로 여기서 "
                "잰 폭은 **상한**이지 시위가 아니다. 그래서 헤드라인 값으로 쓰지 않는다. "
                "이 컷이 제대로 쓰이려면 프롭을 펼친 상면 사진이 필요하다 — 저장소에 없다."),
        ),
    )
    C["primary_product_pair"] = measure_image(
        os.path.join(PHOTOS, "mavic4pro", "mavic4pro_c10_propeller_pair_1158F.jpg"),
        mode="dark", thr=120, n_rotors=2, min_area=8000, nominal_dia_mm=267.0,
        label="[B-] 정품 1158F 1쌍 제품사진 — 펼침, 흰 배경. ⚠3/4 투영, 원근 미보정")
    for t in (100, 150):
        C[f"threshold_{t}"] = measure_image(
            os.path.join(PHOTOS, "mavic4pro", "mavic4pro_c10_propeller_pair_1158F.jpg"),
            mode="dark", thr=t, n_rotors=2, min_area=8000, nominal_dia_mm=267.0,
            label=f"문턱값 감도 {t}")
    C["fcc_folded_upper_bound"] = measure_image(
        os.path.join(PHOTOS, "mavic4pro", "mavic4pro_p01_fcc_top_plan_ruler.jpg"),
        mode="dark", thr=95, n_rotors=4, min_area=6000, nominal_dia_mm=267.0,
        label="[상한] FCC 실기체 — 접힌 두 날이 겹친 합집합. 시위가 아니라 상한이다.",
        rectify=False, blue_bg=True)
    C["projection_bias_estimate"] = dict(
        why_ko=("c10 은 프롭을 비스듬히 본 컷이라 회전면이 한 방향으로 눌려 있다. 눌림은 "
                "날 길이(R)와 날 폭(c)에 **다르게** 들어가므로 c/R 이 통째로 치우친다."),
        model_ko=("눌림 인자 f (<1) 가 날 스팬과 각도 α 를 이룰 때 "
                  "c_img/R_img = (c/R)·√((sin²α·f² + cos²α)/(cos²α·f² + sin²α)). "
                  "c10 처럼 스팬이 눌림축과 크게 어긋나면(α≈65°) **c/R 이 과소평가**된다."),
        table=[dict(f=f, alpha_deg=65,
                    ratio=_r(np.sqrt((np.sin(np.radians(65)) ** 2 * f ** 2 + np.cos(np.radians(65)) ** 2)
                                     / (np.cos(np.radians(65)) ** 2 * f ** 2 + np.sin(np.radians(65)) ** 2)), 3))
               for f in (1.0, 0.9, 0.8, 0.7, 0.6)],
        conclusion_ko=("f 를 못 재므로 **보정하지 않는다.** 대신 이 표가 말하는 것은 «c10 값은 "
                       "아래로 치우쳐 있을 가능성이 크다» 이고, 그래서 c10 수치를 **하한**으로 "
                       "다룬다. 정확한 값을 얻으려면 1158F 를 정면에서 찍은 사진이 필요하다."))
    out["C_mavic4pro_1158F"] = C

    # ---------- §D 축 변환과 코드 대조 ----------
    def hi(sec, key="primary"):
        s = sec.get(key, {})
        return (s.get("prop_pair_mean") or {}).get("mean")

    def sp(sec, key="primary"):
        s = sec.get(key, {})
        return (s.get("prop_pair_mean") or {}).get("spread_pct")

    def pr(sec, key="primary"):
        s = sec.get(key, {})
        return (s.get("prop_pair_mean") or {}).get("per_prop") or []

    m5, m4 = hi(B), hi(C, "primary_product_pair")
    B["deprojected_secondary_estimate"] = tilt_from_blade_asymmetry(
        pr(B), 152.4, 71.12)
    C["deprojected_secondary_estimate"] = tilt_from_blade_asymmetry(
        pr(C, "primary_product_pair"), 267.0, 147.0)
    B["why_props_2_3_read_low_ko"] = (
        "⭐프롭 0·1(위쪽 두 로터)은 추정 기울기 7.0°·7.1° 로 거의 정면이고 값이 0.2306·0.2314 로 "
        "**0.3 % 안에서 일치**한다. 프롭 2·3(아래쪽 두 로터)은 0.1865·0.1711 로 낮다. "
        "분할 그림을 보면 이유가 보인다 — 아래쪽 로터는 **안쪽 날이 암·착륙다리에 일부 가려** "
        "폭이 잘려 나간다. 가려서 좁게 찍힌 것을 «날이 좁다» 로 읽으면 안 된다. "
        "그래서 아래 face_on_subset(프롭 0·1)을 **선호 추정**으로 둔다. "
        "다만 이 판단은 그림을 보고 내린 것이라, 보수적인 폭으로 전체 산포도 같이 남긴다.")
    out["D_conversion_and_code_comparison"] = dict(
        bridge_used=_r(bridge, 4),
        bridge_source_ko="§A 에서 Mini 2 공식 CAD 로 실측한 c_cal/c_arc.",
        pitch_based_cross_check=dict(
            mini5pro=pitch_bridge(152.4, 71.12, 0.46),
            mavic4pro=pitch_bridge(267.0, 147.0, 0.46),
            note_ko="공표 피치로 독립 계산한 다리. §A 의 실측 다리와 같은 자리인지 대조용."),
        results=dict(
            mini5pro_6028F=dict(
                c_arc_over_R_all_props=_r(m5),
                prop_to_prop_spread_pct=sp(B),
                c_arc_over_R_PREFERRED_face_on=(
                    B["deprojected_secondary_estimate"]["face_on_subset"]
                    ["c_arc_over_R_uncorrected_mean"]),
                c_cal_over_R_PREFERRED=_r(
                    (B["deprojected_secondary_estimate"]["face_on_subset"]
                     ["c_arc_over_R_uncorrected_mean"] or 0) * bridge) or None,
                c_cal_over_R_conservative_band=[
                    _r(min(x["pair_mean"] for x in pr(B)) * bridge),
                    _r(max(x["pair_mean"] for x in pr(B)) * bridge)] if pr(B) else None,
                c_cal_over_R_all_props_converted=_r(m5 * bridge) if m5 else None,
                grade="C",
                why_grade_ko=("① 사진 속 기체 동일성 미확정(§B source_provenance_WARNING) "
                              "② 프롭끼리 산포가 크다 — 4로터가 서로 다른 깊이·기울기에 있어 "
                              "아핀 한 장으로 못 편다")),
            mavic4pro_1158F=dict(
                c_arc_over_R_measured=_r(m4),
                prop_to_prop_spread_pct=sp(C, "primary_product_pair"),
                c_cal_over_R_converted=_r(m4 * bridge) if m4 else None,
                c_cal_over_R_deprojected_secondary=(
                    _r((C["deprojected_secondary_estimate"]["mean"] or 0) * bridge) or None),
                grade="B-",
                why_grade_ko=("정품 1158F 이고 프롭끼리 잘 맞지만(산포 작음), 3/4 투영이라 "
                              "보정 전 값은 **하한**이다")),
        ),
        code_today=dict(
            file="src/drone_cad.py",
            CHORD_MAX_OVER_R=0.25,
            applies_to_ko="10기종 전부 같은 값 (blade_law='legacy' 기본)",
            CHORD_MAX_OVER_R_MEASURED_mavic4pro=0.181,
            CHORD_MAX_OVER_R_MEASURED_mini2=0.262),
        FINDING_axis_mismatch_ko=(
            "⭐⭐**감사표가 두 자를 섞어 놨다.** `CHORD_MAX_OVER_R_MEASURED` 안에서 "
            "mini2 0.262·yuneec 0.177·solo 0.273·1345 0.225 는 **3D 원통 단면의 진짜 시위**이고, "
            "mavic4pro 0.181·matrice4e 0.190 은 **사진의 투영 폭**이다. 두 값은 cos θ 만큼 "
            f"다르다(§A 실측 {_r(bridge,3)} 배). 즉 사진에서 온 두 기종만 같은 표 안에서 "
            "**체계적으로 낮게** 적혀 있다. 고치려면 사진 유래 값에 다리를 곱하거나, "
            "표에 «어느 자로 잰 값인지» 열을 넣어야 한다."),
    )

    # ---------- §E 판정 ----------
    b_pairs = pr(B)
    band = ([_r(min(x["pair_mean"] for x in b_pairs) * bridge),
             _r(max(x["pair_mean"] for x in b_pairs) * bridge)] if b_pairs else None)
    out["E_verdict"] = dict(
        headline_ko="⭐두 기종 다 «0.25 하나» 보다 훨씬 슬림하다. 그런데 확신의 정도가 서로 다르다.",
        mavic4pro_1158F=dict(
            grade="B-",
            c_cal_over_R_lower_bound=_r(m4 * bridge) if m4 else None,
            c_cal_over_R_deprojected=_r(
                (C["deprojected_secondary_estimate"]["mean"] or 0) * bridge) or None,
            quote_as_ko="0.182 ~ 0.201 (하한 ~ 사영보정). 한 수만 적어야 하면 **0.19**.",
            confidence_ko=("프롭 2개가 **1.6 % 안에서 일치**하고, 감사가 같은 사진에서 낸 0.181 을 "
                           "내 독립 파이프라인이 0.182 로 재현했다. 형상 자체는 믿을 만하다. "
                           "남은 불확실성은 **시점 기울기 하나**이고 그건 값을 위로만 민다."),
            what_would_fix_it_ko="1158F 를 **정면에서** 찍은 사진 한 장(또는 자와 함께 눕힌 단품 사진)."),
        mini5pro_6028F=dict(
            grade="C",
            c_cal_over_R_band=band,
            best_conditioned_pair_ko=("가장 정면인 프롭 0·1(기울기 7°)은 0.2306·0.2314 로 "
                                      "**0.3 % 안에서 일치**하고 c_cal/R = 0.238 을 준다."),
            quote_as_ko="0.21 ± 0.03 (밴드 0.18~0.24). 한 수만 적어야 하면 **0.21**, 등급 [C] 를 붙여서.",
            confidence_ko=("낮다. 이유 둘 — ① 평면형을 줄 수 있는 컷이 `_3.png` 하나뿐인데 그 사진의 "
                           "**기체 동일성이 미확정**이다(형제 배치에 다른 기종이 섞여 있는 것이 확인됐다) "
                           "② 4로터가 서로 다른 깊이·기울기에 있고 아래쪽 둘은 암·다리에 **가려** 있어 "
                           "프롭끼리 29 % 벌어진다."),
            what_would_fix_it_ko=("6028F 단품 사진(정면·자 포함) 또는 Mini 5 Pro 공식 3D. "
                                  "둘 다 지금 저장소에 없다.")),
        family_inference_verdict_ko=(
            "⛔**Mini 2 공식 CAD 를 Mini 5 Pro 프롭 참조로 그대로 쓰면 안 된다.** 지름 1.28 배 · "
            "피치비 16 % 차이이고, 실측 c_cal/R 도 Mini 2 0.257 ↔ 6028F 0.21±0.03 으로 "
            "**Mini 2 가 20 % 넘게 통통하다**. 계열이 같다고 평면형이 같지 않다 — "
            "c_max/R 은 프롭이 커질수록 작아진다는 참조 밴드의 경향을 이 측정이 다시 확인했다."),
        what_this_does_not_say_ko=(
            "① 이 값들은 **평면형(폭)**에 대한 것이지 두께·비틀림·캠버가 아니다. "
            "② 사진은 **투영 폭**만 준다 — 진짜 시위로 옮기는 다리(×1.030)는 Mini 2 CAD 에서 "
            "실측한 것이라 다른 프롭에 그대로 쓰는 것은 어림이다(피치가 다르면 다리도 다르다). "
            "③ ⛔**코드는 하나도 안 바꿨다.** 이 원장은 재료일 뿐이고, 정본 교체는 "
            "파일럿으로 크기를 재고 나서 결정할 일이다."),
        supersedes_ko=("같은 경로의 이전 판(구판 스크립트 benchmark/measure_props_photo_0816.py, "
                       "2026-08-16 21:32)을 대체한다. 구판을 못 쓰는 이유 셋: "
                       "① 자기 검증이 **918 % 오차**로 실패했는데 그대로 값을 실었다 "
                       "② mavic4pro 의 «primary» 로 **정면 입면 컷**(`mavic 4 pro_3.png`)을 써서 "
                       "c_max/R 0.27~0.35 라는 물리적으로 불가능한 값을 냈다 "
                       "③ 주황 팁을 마스크에서 빠뜨려 R 이 짧아졌고, 허브 덩어리를 «날» 로 세었다."),
    )

    # ---------- §F 평면형 «모양» 을 코드의 두 판과 대조 ----------
    def mean_profile(sec, key, only=None):
        v = sec.get(key, {})
        acc = []
        for p in v.get("props", []):
            if only is not None and p["prop_index"] not in only:
                continue
            if not p.get("two_blade_component_ok"):
                continue
            for b in p["blades"]:
                if b.get("M1"):
                    acc.append(b["M1"]["c_over_c_max_profile"])
        if not acc:
            return None, 0
        ks = sorted(acc[0], key=float)
        return {k: _r(np.mean([a[k] for a in acc]), 3) for k in ks}, len(acc)

    prof4, n4 = mean_profile(C, "primary_product_pair")
    prof5, n5 = mean_profile(B, "primary", only=[0, 1])
    grid = np.arange(0.25, 1.0, 0.05)
    try:
        import drone_cad as dc
        leg = np.interp(grid, dc.CHORD_RR, dc.CHORD_FRAC); leg = leg / leg.max()
        dji = np.interp(grid, dc.CHORD_RR_DJI_MINI2, dc.CHORD_FRAC_DJI_MINI2)
        dji = dji / dji.max()
        code = dict(legacy={f"{x:.2f}": _r(y, 3) for x, y in zip(grid, leg)},
                    dji_mini2={f"{x:.2f}": _r(y, 3) for x, y in zip(grid, dji)})
    except Exception as e:                                   # noqa: BLE001
        code = dict(error=str(e))

    def at70(p):
        return None if not p else p.get("0.70")

    out["F_chord_law_shape_vs_code"] = dict(
        what_ko=("c_max/R 은 «얼마나 통통한가» 하나의 수다. 그 옆에 **모양**(c/c_max 가 반경 따라 "
                 "어떻게 변하나)이 따로 있다. 모양은 코드에 CHORD_FRAC 으로 들어 있고 판이 둘이다."),
        measured=dict(mavic4pro_1158F=dict(n_blades=n4, profile=prof4),
                      mini5pro_6028F=dict(n_blades=n5, profile=prof5,
                                          note_ko="가장 정면인 프롭 0·1 만 평균")),
        code_laws=code,
        headline_ko=(
            "⭐**모양 쪽은 `dji_mini2` 판이 맞다는 것을 이 라운드가 독립으로 확인했다.** "
            f"c/c_max @0.70R: 측정 1158F {at70(prof4)} · 6028F {at70(prof5)} ↔ "
            f"코드 dji_mini2 {at70(code.get('dji_mini2', {}))} ↔ 코드 legacy "
            f"{at70(code.get('legacy', {}))}. legacy(3DR Solo 유래)는 외곽에서 **크게 좁고** "
            "정점 위치도 0.30R 로 안쪽에 있는데, 실측 DJI 프롭 셋(Mini2 CAD·1158F·6028F)은 "
            "전부 정점이 0.45~0.55R 이고 외곽이 두툼하다."),
        caveats_ko=(
            "① 뿌리 쪽(0.25~0.35R)은 내 측정이 코드보다 좁게 나오는데, 그 구간은 허브·클램프와 "
            "겹치고 가림도 있어 **내 값이 덜 믿을 만하다**. 외곽(0.5R 이상)이 신뢰 구간이다. "
            "② 정점 위치가 실측 0.55R ↔ dji_mini2 0.45R 로 조금 바깥이다 — 사영 기울기가 "
            "정점을 바깥으로 밀 수 있어 단정하지 않는다."),
        so_what_ko=("⇒ **모양(CHORD_FRAC)은 기종마다 새로 만들 필요가 크지 않다** — DJI 소비자 "
                    "프롭끼리 잘 겹친다. 기종마다 달라야 하는 것은 **c_max/R 이라는 크기 하나**다. "
                    "지금 코드가 그 하나를 전 기종 0.25 로 묶어 둔 것이 문제의 핵심이 맞다."),
    )

    out["_meta"] = dict(
        title="프로펠러 평면형 정밀 계측 — Mavic 4 Pro 1158F · Mini 5 Pro 6028F",
        generated_kst=kst_now(),
        script="benchmark/measure_prop_planform_0816.py",
        python="/workspace/.venvs/py312/bin/python",
        policy="⛔코드 무변경 · ⛔GPU 미사용 · ⛔git 미접촉",
        R_definition_ko=("R = 회전 디스크 반경 = 회전축에서 날 끝까지. 펼친 2날 프롭이면 "
                         "두 날끝의 중점이 회전축이고 R = (날끝~날끝)/2."),
        root_definition_ko="r_root = 폭이 c_max 의 40 % 를 처음 넘는 반경(허브를 벗어나는 지점의 대용).",
        c_max_search_band=f"r/R ∈ [{RR_LO}, {RR_HI}]",
        two_methods_ko="M1 = 극좌표 각폭(r·Δθ) · M2 = 스파인 수직폭. 날마다 차이를 적는다.",
        chord_axis_warning_ko=(
            "⭐사진이 주는 것은 **투영 폭 c_arc** 다. drone_cad.CHORD_MAX_OVER_R 이 뜻하는 것은 "
            "**진짜 시위 c_cal** 이고 c_cal = c_arc / cos θ ≥ c_arc 다. 두 축을 섞지 마라."),
        runtime_s=_r(time.time() - t0, 1))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {OUT}  ({time.time()-t0:.1f}s)")
    return out


if __name__ == "__main__":
    main()
