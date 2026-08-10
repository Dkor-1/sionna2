# -*- coding: utf-8 -*-
"""
report07b_bistatic_md.py — ⭐**바이스태틱각 β 만 열고** 마이크로도플러를 다시 잰다.

왜
--
리포트 7 의 맵은 전부 **모노스태틱**(송신국=수신국)이다. 그런데 우리 실증은 **패시브
바이스태틱**이다 — 조명은 남의 기지국이 하고 우리는 떨어진 곳에서 받는다. 그래서
«모노에서 본 무늬가 바이스태틱에서 그대로인가» 는 리포트 7 이 답하지 않은 질문이다.

이 스크립트는 **리포트 7 의 세팅을 한 글자도 안 바꾸고**(기체·자세·주파수·로터 회전수·
PRF·표본 수를 `outputs/report07_three_engines.json` 의 `_meta` 에서 **읽어서** 쓴다)
수신 방향 û_s 하나만 연다.

⭐ 답해야 하는 물리 넷
  ① **도플러 축척** — 바이스태틱 도플러는 이등분선 투영이다.
        f_d = (1/λ) v·(û_i + û_s) = (2/λ)·cos(β/2)·(v·û_b)      (û_b = 이등분선)
     교과서(Willis)가 «×cos(β/2)» 로 줄여 쓰는 것은 **v·û_b 가 v·û_i 와 같을 때만** 맞다.
     로터 날개끝 속도는 **수평**이므로 우리가 실제로 재는 것은
        f_tip(β) / f_tip(0) = |horiz(û_i + û_s)| / (2 cos el)                      … (예측 B)
     이고, 순진한 «cos(β/2)» 는 … (예측 A) 다. 둘이 갈리는 자리를 계산이 고른다.
  ② **f_tip 과 f_flash 는 서로 다른 것에서 온다** — 도플러는 **운동**, 플래시는 **기하**
     (정렬·가림)에서 온다. 그래서 두 평면을 나란히 돌린다:
        · 방위면(둘 다 같은 부각 −15°, 방위만 벌림) → 이등분선의 **방위**가 돈다
        · 앙각면(수직면 안에서 수신기가 올라감)     → 이등분선의 방위는 **그대로**
     ⭐예측: 플래시 시각은 방위면에서만 밀리고, 앙각면에서는 안 밀린다. 플래시 **주기**는
       둘 다 안 변한다(로터 회전이 정하는 것이지 시선이 정하는 것이 아니다).
  ③ **레벨** — β 가 커지면 조명게이트(n̂·û_i>0) ∩ 수신게이트(n̂·û_s>0) 가 좁아진다.
     `gate_census` 가 커널의 **바로 그 광선 격자**를 다시 쏴서 남는 유효면적 A_eff [m²] 를 센다.
  ④ **전방산란 무효가 얼마나 다가오나** — lit-PO 는 β→180° 에서 σ≡0 이다(그림자복사를 못 낸다).
     A_eff(β) 를 β=180° 까지 재서 β=120° 가 그 벼랑에서 얼마나 떨어져 있는지 숫자로 남긴다.

⚠ 이 편은 **기하만** 본다. 기준채널/감시채널 2채널 처리(ECA·CAF)는 `src/passive_process.py`
  에 있지만 여기서 **안 쓴다**. 여기서 얻는 것은 «표적이 그 기하에서 무엇을 되돌려주는가» 다.

원장
  outputs/report07b_bistatic_md.npz   E (n_t × n_dir) 복소 슬로타임 + 게이트 센서스
  outputs/report07b_bistatic_md.json  기하·예측·실측·회귀 전부

    cd sionna2 && SIONNA2_GPU=2 PYTHONPATH=src:benchmark \
        ~/.venvs/py312/bin/python benchmark/report07b_bistatic_md.py
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import socket
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")        # ⭐사용자 지시: 오늘은 GPU 2 만.

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick                                                    # noqa: E402
pick(verbose=True)

import numpy as np                                                      # noqa: E402
import mitsuba as mi                                                    # noqa: E402

import rcs_sbr as rsb                                                   # noqa: E402
from rcs_sbr import sbr_field, sbr_field_bistatic                       # noqa: E402
from articulated_fast import FastPoser, rotor_phases                    # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                              # noqa: E402
from md_mapstyle import auto_periods, flash_spec                        # noqa: E402

GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
SRC = os.path.join(_ROOT, "outputs", "report07_three_engines.json")
SRCZ = os.path.join(_ROOT, "outputs", "report07_three_engines.npz")
OUTZ = os.path.join(_ROOT, "outputs", "report07b_bistatic_md.npz")
OUTJ = os.path.join(_ROOT, "outputs", "report07b_bistatic_md.json")

BETAS = [0.0, 30.0, 60.0, 90.0, 120.0]        # 본 스윕(β=0 은 모노 회귀 대조)
BETAS_CENSUS = list(np.arange(0.0, 180.0 + 1e-9, 15.0))   # 게이트 센서스는 180° 까지


# ─────────────────────────────────────────────────────────────────────────── #
#  기하 — û_i 고정, û_s 를 **정해진 평면**에서 β 만큼 연다
# ─────────────────────────────────────────────────────────────────────────── #
def look(az_deg, el_deg):
    """표적 → 지상국 단위벡터 (리포트 7 과 **같은 식**)."""
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def us_azimuth(az, el, beta):
    """⭐**방위면(등부각 원뿔)** — 두 지상국이 **같은 부각 el** 에 있고 방위만 벌어진다.

    이것이 패시브 바이스태틱의 실제 기하다: 조명 기지국과 우리 수신기는 둘 다 지상에,
    표적은 그 위에 떠 있다. 그러면 둘의 부각은 같고 갈리는 것은 방위뿐이다.
    ⚠ 방위차 φ 는 β 와 **같지 않다** — 원뿔 위의 두 점이라 φ ≥ β 다. β 가 정확히 나오도록
      cos β = cos²el·cos φ + sin²el 을 φ 에 대해 푼다. β=0 은 부동소수 잔차 없이
      **û_s ≡ û_i** 로 특수화한다(모노 회귀 게이트가 비트 단위로 서게).
    ⚠ 도달 한계: 이 원뿔에서 낼 수 있는 최대 β 는 arccos(2sin²el − 1) = 150° (el=−15°) 다."""
    if beta == 0.0:
        return look(az, el), 0.0
    ce, se = np.cos(np.radians(el)), np.sin(np.radians(el))
    c = (np.cos(np.radians(beta)) - se * se) / (ce * ce)
    if not (-1.0 <= c <= 1.0):
        raise ValueError(f"β={beta}° 는 부각 {el}° 등부각 원뿔에서 도달 불가")
    phi = float(np.degrees(np.arccos(c)))
    return look(az + phi, el), phi


def us_elevation(az, el, beta):
    """**앙각면(대조군)** — 같은 수직면 안에서 수신기가 β 만큼 올라간다.

    물리적으로는 «공중 수신기» 지만, 여기서 이걸 도는 이유는 물리적 현실성이 아니라
    **분리**다: 이등분선의 **방위가 안 변하고 부각만 변한다**. 그래서 방위면과 나란히 두면
    «플래시는 기하(방위 정렬), 도플러는 운동(이등분선 투영)» 이 각각 따로 움직이는지 갈린다."""
    if beta == 0.0:
        return look(az, el), 0.0
    return look(az, el + beta), float(beta)


def horiz_ratio(u_i, u_s, el):
    """⭐예측 B — 날개끝 도플러의 축척 = |horiz(û_i+û_s)| / (2 cos el).

    날개끝 속도는 **수평**이고 한 회전에 모든 방위를 훑으므로, 한 회전 안의 최대 도플러는
        f_tip = (v_tip/λ)·|horiz(û_i+û_s)|
    다. 모노(û_s=û_i)에서 (2 v_tip/λ)·cos el 로 줄어 리포트 7 의 식과 정확히 겹친다."""
    q = np.asarray(u_i) + np.asarray(u_s)
    return float(np.hypot(q[0], q[1]) / (2.0 * np.cos(np.radians(el))))


def bisector(u_i, u_s):
    q = np.asarray(u_i) + np.asarray(u_s)
    n = np.linalg.norm(q)
    return q / n if n > 1e-12 else np.zeros(3)


# ─────────────────────────────────────────────────────────────────────────── #
#  게이트 센서스 — 커널의 **바로 그 광선 격자**를 다시 쏴서 유효면적을 센다
# ─────────────────────────────────────────────────────────────────────────── #
def gate_census(mesh, fc, u_i, U_s, spacing=None, pad=1.15, cache_key=None):
    """조명게이트 ∩ 수신게이트에 남는 **투영 유효면적** A_eff [m²] 를 센다 (장 계산 없음).

    ⚠ 이것은 물리의 재구현이 아니다 — `rcs_sbr` 자신의 씬 빌더(`_scene_for`)와 출사
      가시성(`_exit_visible`)을 그대로 불러 쓰고, 재질 Γ·위상은 **건드리지 않는다**.
      `sbr_field_bistatic` 이 합산하는 히트 집합의 **넓이만** 세는 진단이다.
        A_eff = Σ_{lit_i ∧ (n̂·û_s>0) ∧ exit_vis} d²
      모노(û_s=û_i)에서 A_eff 는 표적의 **투영 실루엣 면적**이 된다."""
    lam = rsb.C0 / float(fc)
    d = float(spacing) if spacing else lam / rsb.DEFAULT_DIV
    u_i = np.asarray(u_i, float); u_i = u_i / np.linalg.norm(u_i)
    U_s = np.stack([v / np.linalg.norm(v) for v in np.atleast_2d(np.asarray(U_s, float))])

    scene, shapes, gammas, matk = rsb._scene_for(mesh, GM, cache_key, fc)
    V = np.asarray(mesh.v, float)
    ctr = 0.5 * (V.max(0) + V.min(0))
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d
    n = int(np.ceil(2 * Rout / d))
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u_i[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u_i, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u_i, e1)
    O = (ctr + Rout * u_i)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
    D = np.tile(-u_i, (O.shape[0], 1))
    ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                   d=mi.Vector3f(*D.T.astype(np.float32)))
    si = scene.ray_intersect(ray)
    valid = np.asarray(si.is_valid()).astype(bool)
    P = np.asarray(mi.Point3f(si.p)).T
    Nn = np.asarray(mi.Vector3f(si.n)).T
    sgn = np.sign(Nn @ u_i); sgn[sgn == 0] = 1.0
    Nn = Nn * sgn[:, None]
    lit_i = valid & ((Nn @ u_i) > 1e-6)

    out = np.zeros(len(U_s))
    for j, us in enumerate(U_s):
        lit = lit_i & ((Nn @ us) > 1e-6)
        sel = np.where(lit)[0]
        if sel.size:
            lit = lit.copy()
            lit[sel] = rsb._exit_visible(scene, P[sel], Nn[sel], us)
        out[j] = float(lit.sum()) * d * d
    return out


# ─────────────────────────────────────────────────────────────────────────── #
#  측정기 — 도플러 축척 · 플래시
# ─────────────────────────────────────────────────────────────────────────── #
def spectrum(E, prf, pad=4):
    """전 구간 주기도(Hann·제로패딩). ⭐**축척을 재는 것은 스펙트로그램이 아니라 이것**이다 —
    맵은 시간분해능을 사느라 주파수를 팔았고(Δf≈280 Hz), 축척 차이는 최대 11 % (≈140 Hz)라
    맵에서는 원리적으로 안 보인다. 전 구간 FFT 는 Δf = PRF/N ≈ 4.8 Hz 다."""
    E = np.asarray(E, complex)
    w = np.hanning(len(E))
    nf = int(pad * len(E))
    S = np.fft.fftshift(np.abs(np.fft.fft(E * w, nf)))
    f = np.fft.fftshift(np.fft.fftfreq(nf, 1.0 / prf))
    return f, S


def tip_quantile(f, S, f_body, q=0.98):
    """⭐추정기 1 — 동체선을 뺀 뒤 **전력가중 |f| 분위수**. 축척에 등변(scale-equivariant)이라
    같은 추정기를 β 마다 쓰면 편향이 비율에서 상쇄된다."""
    m = np.abs(f) > f_body
    w = S[m] ** 2
    a = np.abs(f[m])
    o = np.argsort(a)
    a, w = a[o], w[o]
    c = np.cumsum(w) / w.sum()
    return float(np.interp(q, c, a))


def tip_knee(f, S, f_body, f_hi, drop_db=20.0):
    """추정기 2 — 날개끝 띠 위쪽 **무릎**: 띠 안 중앙값 대비 drop_db 아래로 내려간 마지막 |f|."""
    m = (np.abs(f) > f_body) & (np.abs(f) < f_hi)
    ref = np.median(S[m] ** 2)
    thr = ref * 10 ** (-drop_db / 10.0)
    a = np.abs(f); p = S ** 2
    o = np.argsort(a); a, p = a[o], p[o]
    k = np.where(a > f_body)[0]
    a, p = a[k], p[k]
    # 위에서 내려오며 임계 위로 올라오는 첫 자리
    above = np.where(p > thr)[0]
    return float(a[above[-1]]) if above.size else float("nan")


def tip_shape_scale(f, S0, S, f_body, f_max, scales):
    """⭐추정기 3 — **모양 정합**. S(f) 와 S0(f/s) 의 상관을 최대로 하는 s.
    임계값이 필요없고, 스펙트럼 전체(빗살 구조 포함)를 쓴다."""
    m = (np.abs(f) > f_body) & (np.abs(f) < f_max)
    fa, y = f[m], np.log10(S[m] ** 2 + 1e-30)
    y = y - y.mean()
    best, bs = -2.0, np.nan
    for s in scales:
        ref = np.interp(fa / s, f, np.log10(S0 ** 2 + 1e-30))
        ref = ref - ref.mean()
        c = float(np.dot(y, ref) / (np.linalg.norm(y) * np.linalg.norm(ref) + 1e-30))
        if c > best:
            best, bs = c, float(s)
    return bs, best


def flash_envelope(E, prf, f_flash, f_lo, f_hi):
    """날개끝 띠의 **시간축 에너지** b(t) — 이것이 «플래시» 의 관측량이다."""
    f, t, S, nper = flash_spec(E, prf, f_flash, auto_periods(prf, f_flash))
    m = (np.abs(f) > f_lo) & (np.abs(f) < f_hi)
    b = (S[m] ** 2).sum(axis=0)
    return t, b, nper


def line_freq(t, b, f_lo, f_hi):
    """b(t) 의 지배 선주파수 (플래시율)."""
    b = np.asarray(b, float) - np.mean(b)
    fs = 1.0 / np.mean(np.diff(t))
    nf = 1 << int(np.ceil(np.log2(len(b) * 8)))
    P = np.abs(np.fft.rfft(b * np.hanning(len(b)), nf))
    fr = np.fft.rfftfreq(nf, 1.0 / fs)
    m = (fr > f_lo) & (fr < f_hi)
    return float(fr[m][np.argmax(P[m])]), float(P[m].max() / (np.median(P[m]) + 1e-30))


def best_lag(t, b0, b, max_lag_s):
    """b 가 b0 대비 얼마나 밀렸나 [s] — 정규화 상호상관의 최대 자리(±max_lag_s 안)."""
    x = np.asarray(b0, float) - np.mean(b0)
    y = np.asarray(b, float) - np.mean(b)
    x /= (np.linalg.norm(x) + 1e-30); y /= (np.linalg.norm(y) + 1e-30)
    c = np.correlate(y, x, mode="full")
    lags = (np.arange(len(c)) - (len(x) - 1)) * float(np.mean(np.diff(t)))
    m = np.abs(lags) <= max_lag_s
    i = np.argmax(c[m])
    return float(lags[m][i]), float(c[m][i])


# ─────────────────────────────────────────────────────────────────────────── #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="0 = 리포트 7 원장의 표본 수 그대로")
    ap.add_argument("--census-poses", type=int, default=24)
    ap.add_argument("--analyze-only", action="store_true",
                    help="장(npz)은 그대로 두고 측정·판정만 다시 한다 — 추정기를 손볼 때 쓴다")
    a = ap.parse_args()

    M = json.load(open(SRC))["_meta"]
    spec = DRONES[M["drone"]]
    fp = FastPoser(spec)
    FC, AZ, EL = float(M["fc_hz"]), float(M["az_deg"]), float(M["el_deg"])
    PRF, FFL, FTIP0 = float(M["prf_hz"]), float(M["f_flash_hz"]), float(M["f_tip_hz"])
    NT = int(M["n"]) if a.n <= 0 else int(a.n)
    rpms = np.asarray(M["rpm_per_rotor"], float)

    t = np.arange(NT) / PRF
    ph = rotor_phases(t, rpms, fp.dirs)
    u_i = look(AZ, EL)

    # ── 방향 목록 ────────────────────────────────────────────────────────────
    dirs = []                                   # (label, plane, beta, u_s, phi)
    for b in BETAS:
        us, phi = us_azimuth(AZ, EL, b)
        dirs.append((f"az{b:.0f}", "azimuth", b, us, phi))
    for b in BETAS[1:]:
        us, phi = us_elevation(AZ, EL, b)
        dirs.append((f"el{b:.0f}", "elevation", b, us, phi))
    U_s = np.array([d[3] for d in dirs])
    labels = [d[0] for d in dirs]

    print(f"\n═══ {spec.name} · 바이스태틱 β 스윕 ═══")
    print(f"  리포트 7 원장에서 읽음: {FC/1e9:.2f} GHz · az {AZ:.0f} el {EL:.0f} · "
          f"PRF {PRF:.0f} Hz · N {NT} · f_tip {FTIP0:.0f} · f_flash {FFL:.1f}")
    for lab, pl, b, us, phi in dirs:
        chk = np.degrees(np.arccos(np.clip(float(u_i @ us), -1, 1)))
        print(f"   {lab:6s} {pl:9s} β={b:5.1f}° (검산 {chk:6.2f}°) φ={phi:7.3f}° "
              f"û_s=({us[0]:+.4f},{us[1]:+.4f},{us[2]:+.4f})  "
              f"예측A cos(β/2)={np.cos(np.radians(b)/2):.4f}  "
              f"예측B={horiz_ratio(u_i, us, EL):.4f}")

    # ── 슬로타임 복소열 ──────────────────────────────────────────────────────
    if a.analyze_only:
        Zp = np.load(OUTZ)
        E, secs = Zp["E"], float(json.load(open(OUTJ))["_meta"]["seconds_field"])
        assert list(Zp["labels"]) == labels and E.shape[0] == NT, "npz 가 이 설정과 안 맞는다"
        print(f"  ↻ --analyze-only: 기존 장 {E.shape} 를 그대로 쓴다")
    else:
        t0 = time.time()
        E = np.zeros((NT, len(dirs)), complex)
        for i in range(NT):
            E[i] = sbr_field_bistatic(fp.pose(ph[i]), GM, FC, u_i, U_s)
            if i and i % 512 == 0:
                el_ = time.time() - t0
                print(f"      {i}/{NT}  {el_:.0f}s  ETA {(NT-i)/i*el_/60:.1f}분", flush=True)
        secs = time.time() - t0
        print(f"  ✅ 장 계산 {secs:.0f}s ({secs/NT*1e3:.1f} ms/자세, 수신방향 {len(dirs)}개)")

    # ── 회귀 ① 커널 항등 (같은 cache_key 로 sbr_field 와 나란히) ─────────────
    if a.analyze_only:
        ident = json.load(open(OUTJ))["regression"]["kernel_identity"]
    else:
        idx = np.unique(np.linspace(0, NT - 1, 64).astype(int))
        rel = []
        for i in idx:
            mv = fp.pose(ph[i]); ck = ("r07b", int(i))
            Em = sbr_field(mv, GM, FC, u_i, cache_key=ck)
            Eb = sbr_field_bistatic(mv, GM, FC, u_i, u_i, cache_key=ck)
            rel.append(abs(complex(Eb) - Em) / abs(Em))
            rsb._SCENE_CACHE.clear()
        ident = dict(n=int(len(idx)), max_rel_err=float(max(rel)),
                     n_bit_identical=int(sum(r == 0.0 for r in rel)),
                     note="같은 cache_key(같은 Mitsuba 씬 객체)로 sbr_field 와 "
                          "sbr_field_bistatic(û_s=û_i)")

    # ── 회귀 ② 리포트 7 원장(npz['sbr']) 대조 ────────────────────────────────
    ledger = None
    if os.path.exists(SRCZ):
        Z = np.load(SRCZ)
        if "sbr" in Z and len(Z["sbr"]) >= NT:
            s0 = np.asarray(Z["sbr"])[:NT]
            r = np.abs(E[:, 0] - s0) / (np.abs(s0) + 1e-300)
            ledger = dict(n=int(NT), max_rel_err=float(r.max()), mean_rel_err=float(r.mean()),
                          n_bit_identical=int(np.sum(E[:, 0] == s0)),
                          max_phase_err_deg=float(np.abs(np.degrees(
                              np.angle(E[:, 0] / s0))).max()),
                          source="outputs/report07_three_engines.npz['sbr']",
                          note="리포트 7 의 모노 SBR 팔과 이 스윕의 β=0 열")
    print(f"  회귀 ① 커널 항등 max rel {ident['max_rel_err']:.3e} "
          f"(비트동일 {ident['n_bit_identical']}/{ident['n']})")
    if ledger:
        print(f"  회귀 ② 원장 대조   max rel {ledger['max_rel_err']:.3e} "
              f"(비트동일 {ledger['n_bit_identical']}/{ledger['n']})")

    # ── 게이트 센서스 (β=0…180°, 두 평면) ────────────────────────────────────
    Uc, cen_meta = [], []
    for pl, fn in (("azimuth", us_azimuth), ("elevation", us_elevation)):
        for b in BETAS_CENSUS:
            try:
                us, phi = fn(AZ, EL, b)
            except ValueError:
                continue                       # 등부각 원뿔이 못 닿는 β
            Uc.append(us); cen_meta.append((pl, b, phi))
    Uc = np.array(Uc)
    if a.analyze_only:
        Zp = np.load(OUTZ)
        Ac, cen_idx = Zp["census_A"], Zp["census_idx"]
    else:
        cen_idx = np.unique(np.linspace(0, NT - 1, a.census_poses).astype(int))
        Ac = np.zeros((len(cen_idx), len(Uc)))
        t0 = time.time()
        for r, i in enumerate(cen_idx):
            mv = fp.pose(ph[i]); ck = ("cen", int(i))
            Ac[r] = gate_census(mv, FC, u_i, Uc, cache_key=ck)
            rsb._SCENE_CACHE.clear()
        print(f"  ✅ 게이트 센서스 {time.time()-t0:.0f}s ({len(cen_idx)} 자세 × {len(Uc)} 방향)")
    Aeff = Ac.mean(axis=0)

    # ── 측정 ────────────────────────────────────────────────────────────────
    F_BODY = 0.15 * FTIP0                       # 동체선·1차 플래시 측대역 제외
    f, S0 = spectrum(E[:, 0], PRF)
    scales = np.arange(0.20, 1.201, 0.002)
    rows = []
    t_env0 = b_env0 = None
    for j, (lab, pl, beta, us, phi) in enumerate(dirs):
        pred_A = float(np.cos(np.radians(beta) / 2.0))
        pred_B = horiz_ratio(u_i, us, EL)
        fj, Sj = spectrum(E[:, j], PRF)
        q0 = tip_quantile(f, S0, F_BODY)
        qj = tip_quantile(fj, Sj, F_BODY)
        k0 = tip_knee(f, S0, F_BODY, 1.05 * FTIP0)
        kj = tip_knee(fj, Sj, F_BODY, 1.05 * FTIP0)
        sc, cc = tip_shape_scale(f, S0, Sj, F_BODY, 1.9 * FTIP0, scales)
        # 플래시 — 띠는 각 β 의 예측 축척으로 따라간다
        lo, hi = 0.35 * FTIP0 * pred_B, 1.05 * FTIP0 * pred_B
        tj, bj, nper = flash_envelope(E[:, j], PRF, FFL, lo, hi)
        ff, prom = line_freq(tj, bj, 0.4 * FFL, 3.0 * FFL)
        if j == 0:
            t_env0, b_env0 = tj, bj
        lag, cmax = best_lag(tj, b_env0, bj, 0.5 / FFL)
        lvl = float(10 * np.log10(np.mean(np.abs(E[:, j]) ** 2) + 1e-300))
        # 예측 플래시 밀림 — 이등분선 **방위** 회전 / (블레이드당 회전각)
        b_az = float(np.degrees(np.arctan2(bisector(u_i, us)[1], bisector(u_i, us)[0])))
        blade_deg = 360.0 / spec.prop_blades
        # ⚠ 로터는 짝을 지어 **반대로** 돈다(요 토크 상쇄). 그래서 이등분선 방위가 Δ 만큼
        #   돌면 CCW 로터의 플래시는 +Δ/(360·f_rev) 만큼 밀리고 CW 로터는 그만큼 당겨진다 —
        #   예측은 하나가 아니라 **±둘**이고, 넷을 합친 포락은 둘 사이 어딘가에 놓인다.
        _T = 1.0 / FFL
        pred_lag = (b_az / (360.0 * (rpms.mean() / 60.0))) % _T
        pred_lag_cw = (-b_az / (360.0 * (rpms.mean() / 60.0))) % _T
        rows.append(dict(
            label=lab, plane=pl, beta_deg=beta, phi_deg=phi,
            u_s=[float(x) for x in us],
            bisector_az_deg=b_az,
            bisector_el_deg=float(np.degrees(np.arcsin(np.clip(bisector(u_i, us)[2], -1, 1)))),
            pred_cos_half_beta=pred_A, pred_bisector_horiz=pred_B,
            f_tip_pred_A_hz=pred_A * FTIP0, f_tip_pred_B_hz=pred_B * FTIP0,
            meas_ratio_quantile=float(qj / q0), meas_ratio_knee=float(kj / k0),
            meas_ratio_shape=sc, shape_corr=cc,
            f_tip_meas_quantile_hz=float(qj), f_tip_meas_knee_hz=float(kj),
            level_dbsm_rel=lvl, level_db_rel_mono=None,   # 아래에서 채운다
            ptp_db=float((20 * np.log10(np.abs(E[:, j]) + 1e-30)).max()
                         - (20 * np.log10(np.abs(E[:, j]) + 1e-30)).min()),
            f_flash_meas_hz=ff, flash_prominence=prom,
            flash_lag_s=lag, flash_lag_corr=cmax,
            flash_lag_frac_period=float(lag * FFL),
            flash_lag_pred_s=pred_lag, flash_lag_pred_frac=float(pred_lag * FFL),
            flash_lag_pred_cw_s=pred_lag_cw, flash_lag_pred_cw_frac=float(pred_lag_cw * FFL),
            blade_deg=blade_deg,
        ))
    lvl0 = rows[0]["level_dbsm_rel"]
    for r in rows:
        r["level_db_rel_mono"] = float(r["level_dbsm_rel"] - lvl0)

    # 센서스 표
    a0 = float(Aeff[0])
    census = [dict(plane=pl, beta_deg=b, phi_deg=phi, A_eff_m2=float(A),
                   A_eff_rel_mono=float(A / a0), A_eff_db_rel_mono=float(20 * np.log10(A / a0))
                   if A > 0 else None)
              for (pl, b, phi), A in zip(cen_meta, Aeff)]

    # ── 판정 ────────────────────────────────────────────────────────────────
    def _err(r, key):
        return abs(r["meas_ratio_shape"] - r[key])

    az_rows = [r for r in rows if r["plane"] == "azimuth" and r["beta_deg"] > 0]
    el_rows = [r for r in rows if r["plane"] == "elevation"]
    verdict = dict(
        doppler_scaling=dict(
            estimator="meas_ratio_shape (모양 정합) — 분위수·무릎은 교차검증",
            max_err_vs_pred_A=float(max(_err(r, "pred_cos_half_beta") for r in rows[1:])),
            max_err_vs_pred_B=float(max(_err(r, "pred_bisector_horiz") for r in rows[1:])),
            max_err_vs_pred_A_azimuth_only=float(max(_err(r, "pred_cos_half_beta")
                                                     for r in az_rows)),
            max_err_vs_pred_B_azimuth_only=float(max(_err(r, "pred_bisector_horiz")
                                                     for r in az_rows)),
            max_err_vs_pred_A_elevation=float(max(_err(r, "pred_cos_half_beta")
                                                  for r in el_rows)),
            max_err_vs_pred_B_elevation=float(max(_err(r, "pred_bisector_horiz")
                                                  for r in el_rows)),
        ),
        flash_rate=dict(
            f_flash_nominal_hz=FFL,
            max_abs_dev_hz=float(max(abs(r["f_flash_meas_hz"] - FFL) for r in rows)),
            values_hz=[r["f_flash_meas_hz"] for r in rows],
        ),
        forward_scatter=dict(
            A_eff_rel_at_beta120_azimuth=float(
                next(c["A_eff_rel_mono"] for c in census
                     if c["plane"] == "azimuth" and abs(c["beta_deg"] - 120) < 1e-6)),
            A_eff_rel_at_beta150_azimuth=float(
                next(c["A_eff_rel_mono"] for c in census
                     if c["plane"] == "azimuth" and abs(c["beta_deg"] - 150) < 1e-6)),
            A_eff_at_beta180_elevation=float(
                next(c["A_eff_m2"] for c in census
                     if c["plane"] == "elevation" and abs(c["beta_deg"] - 180) < 1e-6)),
        ),
    )

    meta = dict(
        generated=_dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        host=socket.gethostname(), gpu=os.environ.get("SIONNA2_GPU"),
        script="benchmark/report07b_bistatic_md.py",
        kernel="rcs_sbr.sbr_field_bistatic (단일 격자 λ/12 · 각도의존 Γ(θ) · 투과 · 출사가시성)",
        inherited_from="outputs/report07_three_engines.json['_meta'] — 하드코딩 없음",
        drone=M["drone"], name=M["name"], fc_hz=FC, az_deg=AZ, el_deg=EL,
        n=NT, prf_hz=PRF, f_flash_hz=FFL, f_tip_mono_hz=FTIP0,
        blade_periods=NT / PRF * FFL, rpm_per_rotor=rpms.tolist(),
        rpm_spread_frac=M.get("rpm_spread_frac"), prop_blades=int(spec.prop_blades),
        rotor_dirs=[int(x) for x in np.sign(np.asarray(fp.dirs)).astype(int)]
        if np.ndim(fp.dirs) == 1 else None,
        betas_deg=BETAS, betas_census_deg=BETAS_CENSUS,
        seconds_field=secs, seconds_per_pose=secs / NT, n_rx_dirs=len(dirs),
        plane_azimuth=("⭐본 스윕. 두 지상국이 **같은 부각 el 원뿔** 위에 있고 방위만 φ 벌어진다"
                       " — 조명 기지국도 우리 수신기도 지상에 있고 표적이 그 위에 뜬 패시브"
                       " 바이스태틱의 실제 기하다. φ 는 β 와 다르고(φ≥β) cos β ="
                       " cos²el·cos φ + sin²el 로 푼다. 이 원뿔의 도달 한계는 β ≤ 150°."),
        plane_elevation=("대조군. 같은 수직면에서 수신기가 β 만큼 올라간다 — 이등분선의"
                         " **방위가 안 변한다**. 플래시(기하)와 도플러(운동)를 분리하려고 둔다."),
        f_body_cut_hz=F_BODY,
        display="맵은 src/md_mapstyle.flash_spec(auto_periods) — 리포트 7 과 같은 규약",
        scope_limits=[
            "lit-PO 전방산란 무효: β→180° 에서 조명·수신 게이트가 상호배타 → E≡0. 그림자복사"
            "(Babinet 전방로브 4πA²/λ²)를 못 낸다. β=120° 가 그 벼랑에서 얼마나 떨어졌는지는"
            " census 표가 잰다.",
            "상반성 부분성립: û_i 단일 조명격자를 재사용하므로 E(û_i,û_s) ↔ E(û_s,û_i) 가"
            " 비볼록 표적에서 어긋난다(격자세분으로 안 줄어듦).",
            "투과 출사경로는 입사 τ=1−|Γ|² 로 근사한 1차 투과 — 바이스태틱 비대칭을 더 키운다.",
            "obliquity 는 표준 PO 의 (n̂·û_i) 그대로 — 대칭 √((n̂·û_i)(n̂·û_s)) 는 폐기된 시도다.",
            "⚠ 기하만 본다. 기준채널/감시채널 2채널 처리(ECA·CAF, src/passive_process.py)는"
            " 이 편에서 쓰지 않는다 — 다음 단계다.",
            "도플러 **부호**는 검증하지 않았다 — 로터 스펙트럼이 거의 대칭이라 이 원장으로는"
            " 부호 규약을 가를 수 없다.",
        ],
    )

    np.savez_compressed(OUTZ, E=E, labels=np.array(labels), U_s=U_s, u_i=u_i,
                        census_A=Ac, census_idx=cen_idx, census_U=Uc,
                        census_beta=np.array([c[1] for c in cen_meta]),
                        census_plane=np.array([c[0] for c in cen_meta]))
    json.dump(dict(_meta=meta, geometry=[dict(label=r["label"], plane=r["plane"],
                                              beta_deg=r["beta_deg"], phi_deg=r["phi_deg"],
                                              u_s=r["u_s"],
                                              bisector_az_deg=r["bisector_az_deg"],
                                              bisector_el_deg=r["bisector_el_deg"])
                                         for r in rows],
                   rows=rows, census=census, regression=dict(kernel_identity=ident,
                                                            mono_ledger=ledger),
                   verdict=verdict),
              open(OUTJ, "w"), ensure_ascii=False, indent=1)

    # ── 콘솔 요약 ───────────────────────────────────────────────────────────
    print("\n═══ 도플러 축척: 예측 A cos(β/2) vs 예측 B 이등분선-수평투영 vs 실측 ═══")
    print(f"{'라벨':>7} {'평면':>9} {'β':>5} {'예A':>7} {'예B':>7} {'모양':>7} "
          f"{'분위':>7} {'무릎':>7} {'r':>6} {'레벨dB':>8}")
    for r in rows:
        print(f"{r['label']:>7} {r['plane']:>9} {r['beta_deg']:5.0f} "
              f"{r['pred_cos_half_beta']:7.4f} {r['pred_bisector_horiz']:7.4f} "
              f"{r['meas_ratio_shape']:7.4f} {r['meas_ratio_quantile']:7.4f} "
              f"{r['meas_ratio_knee']:7.4f} {r['shape_corr']:6.3f} "
              f"{r['level_db_rel_mono']:+8.2f}")
    print("\n═══ 플래시 ═══")
    for r in rows:
        print(f"{r['label']:>7} f_flash {r['f_flash_meas_hz']:7.2f} Hz "
              f"(공칭 {FFL:.2f}) · 밀림 {r['flash_lag_s']*1e3:+6.2f} ms "
              f"= {r['flash_lag_frac_period']:+.3f} 주기 (상관 {r['flash_lag_corr']:.3f}) "
              f"· 예측 {r['flash_lag_pred_frac']:+.3f}")
    print("\n═══ 게이트 센서스 A_eff (자세 평균) ═══")
    for c in census:
        print(f"  {c['plane']:>9} β {c['beta_deg']:5.0f}°  A_eff {c['A_eff_m2']*1e4:8.2f} cm² "
              f"= {c['A_eff_rel_mono']*100:6.2f} % of mono")
    print(f"\n✅ {OUTZ}\n✅ {OUTJ}")


if __name__ == "__main__":
    main()
