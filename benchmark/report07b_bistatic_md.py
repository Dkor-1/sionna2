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
from rcs_sbr import (grid_ref_for_slowtime, sbr_field,                  # noqa: E402
                     sbr_field_bistatic)
from articulated_fast import FastPoser, rotor_phases                    # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                              # noqa: E402
from md_mapstyle import auto_periods, flash_spec, ridge_spec             # noqa: E402
from microdoppler import microdoppler_series                            # noqa: E402

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


def envelope(f, S, smooth_hz):
    """빗살을 지우고 **포락**만 남긴다 — 이동평균(폭 smooth_hz).

    ⚠ 왜 필요한가: 스펙트럼의 **선 위치**(f_flash 배수)는 β 에 안 변하고 **포락의 폭**만
      변한다. 그래서 선 구조를 그대로 두고 축척을 재려 하면 추정기가 «안 변한다» 는 쪽으로
      끌려간다(실제로 그랬다 — 초판 모양정합이 전부 s≈1 로 붙었다)."""
    P = np.asarray(S, float) ** 2
    df = float(f[1] - f[0])
    n = max(3, int(round(smooth_hz / df)) | 1)
    return np.convolve(P, np.ones(n) / n, mode="same")


def inst_max_doppler(E, prf, f_flash, f_body, drop_db=20.0, pct=99.0):
    """⭐**시간분해 최대 도플러** — 이 편의 주 추정기.

    왜 스펙트럼 «가장자리» 가 아니라 이것인가 (2026-08-10 실측으로 갈아탄 이유):
      전 구간 스펙트럼은 f_flash 간격의 **빗살**이다. 빗살 **선 위치는 β 에 안 변하고**
      포락만 줄어든다. 그래서 가장자리를 임계값으로 재면 눈금이 126.7 Hz 로 양자화되어
      ±10~25 % 가 튄다(실측). 반면 날개끝 도플러는 **한 회전 안에서 잠깐만** 도달하는
      시간 사건이라, 시간-주파수 평면에서 슬롯마다 재면 훨씬 날카롭다.

    재는 법: `md_mapstyle.ridge_spec` (능선 규약 — 주파수 분해능을 사는 판) 로 STFT 를 만들고,
      슬롯마다 그 슬롯 최대값 대비 drop_db 위에 남는 **최고 |f|** 를 취한 뒤, 그 시계열의
      pct 분위수를 쓴다(단발 이상치를 안 물게).
    ⚠ 절대값에는 −5 % 쯤의 계통 편향이 있다(모노에서 1159 Hz vs 공식 1229 Hz — 창·임계값 탓).
      우리가 쓰는 것은 **β=0 대비 비율**이라 그 편향은 상쇄된다."""
    f, t, S, _ = ridge_spec(np.asarray(E, complex), prf, f_flash)
    P = S ** 2
    ok = np.abs(f) > f_body
    fa, Pp = np.abs(f)[ok], P[ok]
    thr = Pp.max(axis=0) * 10 ** (-drop_db / 10.0)
    v = np.array([fa[Pp[:, j] > thr[j]].max() if (Pp[:, j] > thr[j]).any() else np.nan
                  for j in range(P.shape[1])])
    return float(np.nanpercentile(v, pct))


def edge_of(P_env, f, f_body, drop_db=25.0):
    """띠 바깥 **가장자리** — 동체선 밖 최대값 대비 drop_db 아래로 내려가는 마지막 |f|.
    ⭐순수 PO 처럼 잘린 스펙트럼에서는 임계값에 거의 안 민감하다(절벽이 80 dB 라서).
    ⚠ SBR 처럼 바닥이 넓은 스펙트럼에서는 **나이퀴스트까지 밀린다** — 그 사실 자체가 결과다."""
    m = np.abs(f) > f_body
    ref = P_env[m].max()
    thr = ref * 10 ** (-drop_db / 10.0)
    a = np.abs(f)[m]; p = P_env[m]
    o = np.argsort(a); a, p = a[o], p[o]
    above = np.where(p > thr)[0]
    return float(a[above[-1]]) if above.size else float("nan")


def floor_rel_db(P_env, f, f_lo):
    """|f| > f_lo 의 **바닥**이 봉우리보다 몇 dB 아래인가 — 스펙트럼 오염의 척도."""
    m = np.abs(f) > f_lo
    return float(10 * np.log10(np.median(P_env[m]) / P_env.max()))


def scale_fit(f, P0, P, f_max, scales):
    """P(f) ≈ a·P0(f/s) + c 를 (a,c) 최소제곱 · s 격자탐색으로 푼다.
    ⭐바닥 c 를 **가정하지 않고 자유 파라미터로 잰다**. 반환 (s, a, c, R²)."""
    m = np.abs(f) <= f_max
    y = P[m]
    best = (np.inf, np.nan, np.nan, np.nan)
    for s in scales:
        x = np.interp(f[m] / s, f, P0)
        A = np.stack([x, np.ones_like(x)], 1)
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        if coef[0] <= 0:
            continue
        r = float(np.sum((A @ coef - y) ** 2))
        if r < best[0]:
            best = (r, float(s), float(coef[0]), float(coef[1]))
    tot = float(np.sum((y - y.mean()) ** 2))
    return best[1], best[2], best[3], float(1 - best[0] / tot) if tot > 0 else np.nan


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

    # ⭐ 얼린 광선 격자 — 모노 팔(리포트 7)과 **같은 규약**이다. 격자는 자세의 bbox 에서
    #   나오는데 프로펠러가 돌면 bbox 가 숨을 쉬어 위상 원점(ctr)과 표본 집합(Rout·n)이
    #   프레임마다 바뀐다. 바이스태틱도 격자를 û_i 에서 같은 함수로 만들므로 병이 같다.
    #   ⚠ 한 판을 모든 수신방향(U_s)이 공유한다 — β 사이 비교가 격자 차이에 오염되면 안 된다.
    #   SIONNA2_FREEZE_GRID=0 이면 None → 옛 동작(전후 비교 스위치).
    gref = grid_ref_for_slowtime(fp.pose, fp.dirs, FC)
    print("  격자(얼림) " + (f"n={gref.n} ({gref.n**2}발) · Rout={gref.Rout:.4f} m"
                            if gref is not None else "OFF — SIONNA2_FREEZE_GRID=0"), flush=True)

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
            E[i] = sbr_field_bistatic(fp.pose(ph[i]), GM, FC, u_i, U_s, grid_ref=gref)
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
            # 생산 경로와 같은 판을 넘긴다 — 안 그러면 항등 검사가 생산과 다른 격자를 검사한다
            Em = sbr_field(mv, GM, FC, u_i, cache_key=ck, grid_ref=gref)
            Eb = sbr_field_bistatic(mv, GM, FC, u_i, u_i, cache_key=ck, grid_ref=gref)
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
                          this_run_grid_frozen=bool(gref is not None),
                          note=("리포트 7 의 모노 SBR 팔과 이 스윕의 β=0 열. "
                                "⚠ 두 열이 **같은 격자 규약**일 때만 0 이 나온다 — 이 스윕이 "
                                "얼린 판을 쓰는데 원장이 옛(안 얼린) 판이면 커진다. 그때는 "
                                "report07_three_engines.npz 를 먼저 다시 내라."))
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

    # ── ⭐순수-PO 대조팔 (바이스태틱) — 「왜 이게 필요한가」는 파일 상단 주석 참조 ────
    #   위상 항등식:  e^{jk(û_i+û_s)·p} = e^{j2k' û_b·p},  k' = k·cos(β/2)
    #   → **바이스태틱 PO 위상 = 이등분선 시선의 모노 PO 위상 @ 반송파 fc·cos(β/2)**.
    #   그래서 `microdoppler_series` 를 **고치지 않고** 그대로 불러 대조팔을 만든다.
    #   ⚠ 근사 하나: 진폭 게이트·obliquity 는 (n̂·û_b) 하나를 쓴다(두 게이트 n̂·û_i, n̂·û_s
    #     각각이 아니라). 도플러축은 위상이 정하므로 **이 팔이 재는 축척에는 영향이 없고**,
    #     레벨은 SBR 팔이 맡는다. 이 팔은 «가장자리가 잘려 보이는» 스펙트럼을 얻기 위한 것이다.
    SPACING_PO = rsb.C0 / FC / 11.0             # β 마다 점구름이 안 변하게 **고정**
    _have_po = a.analyze_only and "E_po" in np.load(OUTZ).files
    if _have_po:
        Epo = np.load(OUTZ)["E_po"]
        print("  ↻ PO 대조팔도 npz 에서 읽었다")
    else:
        t0 = time.time()
        Epo = np.zeros((NT, len(dirs)), complex)
        for j, (lab, pl, beta, us, phi) in enumerate(dirs):
            if beta == 0.0:                     # 원장과 비트동일하게 특수화
                azb, elb, fcb = AZ, EL, FC
            else:
                ub = bisector(u_i, us)
                azb = float(np.degrees(np.arctan2(ub[1], ub[0])))
                elb = float(np.degrees(np.arcsin(np.clip(ub[2], -1, 1))))
                fcb = FC * float(np.cos(np.radians(beta) / 2.0))
            _, Epo[:, j], _ = microdoppler_series(spec, fc=fcb, az=azb, el=elb, prf=PRF,
                                                  n_t=NT, rpm_per_rotor=rpms,
                                                  spacing=SPACING_PO)
        print(f"  ✅ PO 대조팔 {time.time()-t0:.0f}s")

    # 회귀 ③ — PO β=0 이 리포트 7 의 po 팔과 같은가
    po_ledger = None
    if os.path.exists(SRCZ):
        Z = np.load(SRCZ)
        if "po" in Z and len(Z["po"]) >= NT:
            p0 = np.asarray(Z["po"])[:NT]
            r = np.abs(Epo[:, 0] - p0) / (np.abs(p0) + 1e-300)
            po_ledger = dict(n=int(NT), max_rel_err=float(r.max()),
                             n_bit_identical=int(np.sum(Epo[:, 0] == p0)),
                             source="outputs/report07_three_engines.npz['po']",
                             note="리포트 7 의 순수 PO 팔과 이 대조팔의 β=0 열")
            print(f"  회귀 ③ PO 원장 대조 max rel {po_ledger['max_rel_err']:.3e} "
                  f"(비트동일 {po_ledger['n_bit_identical']}/{po_ledger['n']})")

    # ── 측정 ────────────────────────────────────────────────────────────────
    F_BODY = 0.15 * FTIP0                       # 동체선·1차 플래시 측대역 제외
    SMOOTH = 4.0 * FFL                          # 빗살(간격 f_flash)을 지우는 포락 폭
    f, S0 = spectrum(E[:, 0], PRF)
    P0 = envelope(f, S0, SMOOTH)
    _, S0p = spectrum(Epo[:, 0], PRF)
    P0p = envelope(f, S0p, SMOOTH)
    e0_sbr, e0_po = edge_of(P0, f, F_BODY), edge_of(P0p, f, F_BODY)
    v0_po = inst_max_doppler(Epo[:, 0], PRF, FFL, F_BODY)      # ⭐주 추정기의 기준(β=0)
    v0_sbr = inst_max_doppler(E[:, 0], PRF, FFL, F_BODY)
    scales = np.arange(0.25, 1.301, 0.002)
    rows = []
    t_env0 = b_env0 = None
    for j, (lab, pl, beta, us, phi) in enumerate(dirs):
        pred_A = float(np.cos(np.radians(beta) / 2.0))
        pred_B = horiz_ratio(u_i, us, EL)
        fj, Sj = spectrum(E[:, j], PRF)
        Pj = envelope(fj, Sj, SMOOTH)
        _, Sjp = spectrum(Epo[:, j], PRF)
        Pjp = envelope(fj, Sjp, SMOOTH)
        e_sbr, e_po = edge_of(Pj, fj, F_BODY), edge_of(Pjp, fj, F_BODY)
        # ⭐주 추정기 — 시간분해 최대 도플러(두 팔에 같은 잣대를 댄다)
        v_po = inst_max_doppler(Epo[:, j], PRF, FFL, F_BODY)
        v_sbr = inst_max_doppler(E[:, j], PRF, FFL, F_BODY)
        v_po_lo = inst_max_doppler(Epo[:, j], PRF, FFL, F_BODY, drop_db=25.0)
        v_po_hi = inst_max_doppler(Epo[:, j], PRF, FFL, F_BODY, drop_db=15.0)
        s_fit, a_fit, c_fit, r2 = scale_fit(f, P0, Pj, 2.4 * FTIP0, scales)
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
            # ⭐도플러 축척 — 순수 PO 대조팔에 시간분해 최대 도플러
            po_fmax_hz=v_po, po_ratio=float(v_po / v0_po),
            po_ratio_lo=float(v_po_lo / inst_max_doppler(Epo[:, 0], PRF, FFL, F_BODY,
                                                         drop_db=25.0)),
            po_ratio_hi=float(v_po_hi / inst_max_doppler(Epo[:, 0], PRF, FFL, F_BODY,
                                                         drop_db=15.0)),
            po_over_predA=float(v_po / v0_po / pred_A), po_over_predB=float(v_po / v0_po / pred_B),
            po_edge_hz=e_po, po_edge_ratio=float(e_po / e0_po),
            # SBR 팔 — **같은 잣대**를 대보면 «못 잰다» 는 것이 그대로 보인다
            sbr_fmax_hz=v_sbr, sbr_ratio=float(v_sbr / v0_sbr),
            sbr_edge_hz=e_sbr, sbr_edge_ratio=float(e_sbr / e0_sbr),
            sbr_floor_rel_db=floor_rel_db(Pj, fj, 1.5 * FTIP0),
            sbr_scale_fit=s_fit, sbr_scale_fit_r2=r2,
            sbr_scale_fit_floor_rel_db=float(10 * np.log10(max(c_fit, 1e-300) / Pj.max())),
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
    az_rows = [r for r in rows if r["plane"] == "azimuth" and r["beta_deg"] > 0]
    el_rows = [r for r in rows if r["plane"] == "elevation"]
    rest = rows[1:]

    def _mx(rr, key, pred):
        return float(max(abs(r[key] - r[pred]) for r in rr))

    # 모노 원장 세 엔진의 바닥 — «SBR 가장자리는 못 쓴다» 의 근거를 원장에서 만든다
    engines_floor = None
    if os.path.exists(SRCZ):
        Zm = np.load(SRCZ)
        engines_floor = {}
        for kk in ("sbr", "po", "sionna"):
            if kk in Zm and len(Zm[kk]) >= NT:
                fk, Sk = spectrum(np.asarray(Zm[kk])[:NT], PRF)
                Pk = envelope(fk, Sk, SMOOTH)
                _blade = np.abs(fk) > F_BODY               # 동체선 밖 = 블레이드가 만든 것
                _out = _blade & (np.abs(fk) > FTIP0)       # 그 중 공칭 날개끝 **밖**
                engines_floor[kk] = dict(
                    floor_rel_db=floor_rel_db(Pk, fk, 1.5 * FTIP0),
                    edge_hz=edge_of(Pk, fk, F_BODY),
                    # ⭐읽기 쉬운 잣대 — 블레이드 대역 전력 중 공칭 f_tip **밖**에 있는 비율
                    frac_power_beyond_ftip=float(Pk[_out].sum() / Pk[_blade].sum()))
    verdict = dict(
        doppler_scaling=dict(
            primary_estimator=("순수 PO 대조팔에 **시간분해 최대 도플러**"
                               "(ridge_spec STFT · 슬롯당 −20 dB · 99 분위)"),
            po_max_err_vs_pred_A=_mx(rest, "po_ratio", "pred_cos_half_beta"),
            po_max_err_vs_pred_B=_mx(rest, "po_ratio", "pred_bisector_horiz"),
            po_rms_rel_err_vs_pred_A=float(np.sqrt(np.mean([(r["po_over_predA"] - 1) ** 2
                                                            for r in rows]))),
            po_rms_rel_err_vs_pred_B=float(np.sqrt(np.mean([(r["po_over_predB"] - 1) ** 2
                                                            for r in rows]))),
            po_max_err_vs_pred_A_azimuth=_mx(az_rows, "po_ratio", "pred_cos_half_beta"),
            po_max_err_vs_pred_B_azimuth=_mx(az_rows, "po_ratio", "pred_bisector_horiz"),
            po_max_err_vs_pred_A_elevation=_mx(el_rows, "po_ratio", "pred_cos_half_beta"),
            po_max_err_vs_pred_B_elevation=_mx(el_rows, "po_ratio", "pred_bisector_horiz"),
            po_threshold_spread=float(max(abs(r["po_ratio_hi"] - r["po_ratio_lo"])
                                          for r in rows)),
            sharpest_case=("el120 — 두 예측이 가장 멀다(A 0.500 ↔ B 0.366): "
                           + f"실측 {next(r['po_ratio'] for r in rows if r['label'] == 'el120'):.3f}"),
            winner=("B (이등분선의 수평투영)"
                    if np.sqrt(np.mean([(r["po_over_predB"] - 1) ** 2 for r in rows]))
                    < np.sqrt(np.mean([(r["po_over_predA"] - 1) ** 2 for r in rows]))
                    else "A (cos(β/2))"),
        ),
        sbr_edge_unusable=dict(
            why=("SBR 슬로타임 스펙트럼에는 f_tip 밖까지 이어지는 **광대역 바닥**이 있다 — "
                 "표적이 도는 동안 광선 격자에서 히트 집합이 켜졌다 꺼지는 데서 온다. "
                 "그래서 «가장자리» 로는 f_tip 을 못 잰다(어떤 β 에서도 나이퀴스트까지 밀린다). "
                 "포락을 P(f)=a·P₀(f/s)+c 로 맞춰도 s 가 1 근처에 붙는다 — 축척이 없다는 뜻이 "
                 "아니라 **이 관측량으로는 축척이 안 보인다**는 뜻이다."),
            sbr_ratio_range=[float(min(r["sbr_ratio"] for r in rows)),
                             float(max(r["sbr_ratio"] for r in rows))],
            sbr_edge_ratio_range=[float(min(r["sbr_edge_ratio"] for r in rows)),
                                  float(max(r["sbr_edge_ratio"] for r in rows))],
            sbr_scale_fit_range=[float(min(r["sbr_scale_fit"] for r in rows)),
                                 float(max(r["sbr_scale_fit"] for r in rows))],
            mono_ledger_engine_floors_db=engines_floor,
            note=("모노 원장(report07_three_engines.npz)의 세 팔을 같은 추정기로 잰 것이다 — "
                  "순수 PO 는 바닥이 −100 dB 대이고 SBR·Sionna 는 −30~−40 dB 대다. "
                  "즉 이것은 바이스태틱의 성질이 아니라 **광선 엔진 공통의 성질**이고, "
                  "리포트 7 이 남긴 «SBR 의 날개끝 밖 능선» 미제와 같은 것이다."),
        ),
        flash_rate=dict(
            f_flash_nominal_hz=FFL,
            # ⚠ 포락 스펙트럼의 최대선이 **2차 고조파**로 넘어가는 칸이 있다(플래시가 반주기마다
            #   두 번 보이면 2f 선이 더 세진다). 그래서 «공칭의 정수배인가» 로 판정한다 —
            #   축척이 아니라 **격자**가 유지되는지가 이 절의 주장이다.
            harmonic_index=[int(round(r["f_flash_meas_hz"] / FFL)) for r in rows],
            max_abs_dev_from_harmonic_hz=float(max(
                abs(r["f_flash_meas_hz"] - round(r["f_flash_meas_hz"] / FFL) * FFL)
                for r in rows)),
            n_at_fundamental=int(sum(abs(r["f_flash_meas_hz"] - FFL) < 2.0 for r in rows)),
            n_total=len(rows),
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
        grid_frozen=bool(gref is not None),
        grid_ref=(gref.asjson() if gref is not None else None),
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

    np.savez_compressed(OUTZ, E=E, E_po=Epo, labels=np.array(labels), U_s=U_s, u_i=u_i,
                        census_A=Ac, census_idx=cen_idx, census_U=Uc,
                        census_beta=np.array([c[1] for c in cen_meta]),
                        census_plane=np.array([c[0] for c in cen_meta]))
    json.dump(dict(_meta=meta, geometry=[dict(label=r["label"], plane=r["plane"],
                                              beta_deg=r["beta_deg"], phi_deg=r["phi_deg"],
                                              u_s=r["u_s"],
                                              bisector_az_deg=r["bisector_az_deg"],
                                              bisector_el_deg=r["bisector_el_deg"])
                                         for r in rows],
                   rows=rows, census=census,
                   regression=dict(kernel_identity=ident, mono_ledger=ledger,
                                   po_control_ledger=po_ledger),
                   verdict=verdict),
              open(OUTJ, "w"), ensure_ascii=False, indent=1)

    # ── 콘솔 요약 ───────────────────────────────────────────────────────────
    print("\n═══ 도플러 축척: 예측 A cos(β/2) · 예측 B 이등분선-수평투영 · 실측 ═══")
    print(f"{'label':>7} {'plane':>9} {'beta':>5} {'predA':>7} {'predB':>7} "
          f"{'PO meas':>8} {'/predA':>7} {'/predB':>7} {'SBRmeas':>8} {'floor':>7} {'level':>8}")
    for r in rows:
        print(f"{r['label']:>7} {r['plane']:>9} {r['beta_deg']:5.0f} "
              f"{r['pred_cos_half_beta']:7.4f} {r['pred_bisector_horiz']:7.4f} "
              f"{r['po_ratio']:8.4f} {r['po_over_predA']:7.3f} {r['po_over_predB']:7.3f} "
              f"{r['sbr_ratio']:8.3f} {r['sbr_floor_rel_db']:7.1f} "
              f"{r['level_db_rel_mono']:+8.2f}")
    _V = verdict["doppler_scaling"]
    print("  ⭐판정:", _V["winner"],
          f"— 상대 rms 오차 A {_V['po_rms_rel_err_vs_pred_A']:.3f} vs B "
          f"{_V['po_rms_rel_err_vs_pred_B']:.3f}")
    print("  모노 원장 세 엔진 바닥:", {k: round(v["floor_rel_db"], 1)
                                for k, v in (engines_floor or {}).items()})
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
