# -*- coding: utf-8 -*-
"""
verify_po_elev_metric.py — 「도플러 폭」을 재는 잣대를 다시 세우고 앙각 7 점을 다시 잰다
================================================================================

■ 왜 만드나 (2026-08-11, 사용자 지적)
앙각 스윕에서 「위상 변동폭」과 「−20 dB 폭」이 단조가 아니었다(−30·−60 도에서 튄다).
사용자: "직관적으로 이해가 안 간다. 우리 PO 를 제대로 검증해봐라."
⇒ 먼저 잣대를 의심한다. 잣대가 부실하면 커널 판정은 시작조차 못 한다.

■ 옛 잣대 두 개가 왜 부실한가 (이 스크립트가 수로 보인다)
  1) np.ptp(np.unwrap(np.angle(E))) — 권선수(winding number)이지 대역폭이 아니다.
     합신호가 복소평면 원점 근처를 지나면 위상은 임의로 빨리 돈다. 그때의 위상 회전율은
     어떤 산란점의 속도도 아니다. 느린 항들의 「합」이 0 에 가까워지며 생기는 위상일 뿐이다.
     누적 언랩은 원점을 한 바퀴 돌 때마다 360 도를 없던 대역폭으로 적는다.
  2) 전 구간 단일 Hann FFT 의 「−20 dB 폭」 — 문턱이 전역 최대(= 동체 DC 선)를 기준으로 잡힌다.
     그래서 이 잣대가 재는 것은 도플러 폭이 아니라 "동체 선 대비 로터 아치가 몇 dB 아래인가"
     라는 세기비다. 앙각이 바뀌면 동체 투영면적이 바뀌어 세기비가 바뀌고, −20 dB 등고선이
     도플러와 무관한 이유로 튄다.

■ 새 잣대 — 정의를 여기 못 박는다 (인용은 이 파일과 원장 JSON 만)
  헤드라인 W_q : AC 스펙트럼 분위 폭 [Hz]. 문턱 없음, 전 구간이라 통계적으로 안정.
     1. x_ac = x − mean(x)          정지 성분(동체 DC 선) 제거. 2) 의 오염원을 없앤다.
     2. P(f) = |FFT(x_ac * Hann, 4배 패딩)|^2
     3. P 를 40 Hz 로 평활한 뒤 P_n = mean(P over |f| >= 2*f_tip(0deg) = 2546 Hz)
        여기는 물리적으로 금지된 대역이다. 드론 위 어떤 점도 블레이드 팁보다 빠르지 않으므로
        거기 있는 것은 전부 잡음(SBR 격자 이산화, Sionna 광선 표본잡음)이다.
        실측: 2.5~9.85 kHz 에서 평평하다(최대/최소 1.4~2.0) → 백색 가정 타당.
        ⭐평균이지 중앙값이 아니다. 주기도표 빈은 지수분포라 중앙값 = 0.693*평균이고,
          중앙값을 빼면 잡음이 통째로 양의 잔차로 남아 폭이 잡음쪽으로 끌려간다.
          (이 스크립트 첫 판이 실제로 그 함정에 빠졌다 — el −90 에서 W90 이 6325 Hz 로 나왔다.)
     4. P' = P − P_n  (클리핑하지 않는다 — 잡음 빈 기여가 평균 0 으로 상쇄되도록)
     5. W_q = 누적 sum_{|f|<=W} P' 가 q 에 닿는 최소 W.   q = 0.75 / 0.90(본) / 0.95
     · 문턱(−20 dB)이 아니라 분위라서 "어디를 기준으로 몇 dB" 라는 자의성이 없다.
     · 전역 최대를 안 쓴다 → 동체/로터 세기비에 흔들리지 않는다.
     · 잡음을 빼므로 금지 대역의 splatter 가 폭으로 새지 않는다.
  W_q_fm : 진폭 정규화 후 같은 추정기. z = E/|E| 로 AM 을 완전히 없애고 FM 만 남긴다.
     AM 이 폭을 만든 것인지 FM 이 만든 것인지 가르는 가장 곧은 대조군.
  edge_comb : 아치의 실제 가장자리. 로터 신호는 f_flash 주기라 에너지가 n*f_flash 빗에 앉는다.
     각 조화를 국소 배경(+-50 Hz 중앙값)과 견주어 10 dB 를 넘는 마지막 조화 → f_edge.
     ⚠ 우리 커널에서는 고차 조화가 깨끗이 안 죽는다(격자 이산화 잔차도 주기적이라 빗에 앉는다).
       그래서 진단으로만 쓰고 헤드라인으로 안 쓴다.

■ ⭐측정의 원리적 바닥 — f_flash = 126.67 Hz
  로터가 주기적이면 스펙트럼은 n*f_flash 빗 위에만 산다. 따라서 이 관측으로 표현할 수 있는
  0 아닌 최소 폭은 f_flash 다. 예측이 그보다 작으면(−75: 206 Hz, −90: 17 Hz) 측정이
  «너무 넓게» 나오는 것이 정상이고 커널의 잘못이 아니다. 판정에서 반드시 표시한다.
  W95_stft : 조각별(블레이드 2주기) 95 % 분위 폭의 중앙값. 조각이 짧아 잡음에 약하다. 보조.
  B_fm : AM/FM 대역폭 분해(진단용). |xdot|^2 = Adot^2 + A^2 phidot^2 항등식 + Parseval 로
     B_tot^2 = B_am^2 + B_fm^2. 널에서 발산 안 하고 unwrap 을 안 쓴다.
     주의: 에너지 가중이라 정지 동체가 크면 통째로 눌린다 → 헤드라인으로 쓰면 안 된다.
     여기서는 AM 이 실제로 얼마나 큰가(B_am)를 보이는 데만 쓴다.

■ 예측도 같은 추정기로 만든다 (사과 대 사과)
  f_tip 은 가장자리(최대)이고 W_q 는 분위라 둘을 바로 비교하면 모양 상수가 낀다.
  그래서 예측을 기하에서 직접 만든다 —
      프롭 꼭짓점 v 의 왕복거리 d_v(t) 를 미분 → f_dop[t,v] = (2/lam) * ddot_v
      W_q_pred = 꼭짓점 면적 가중 |f_dop| 의 q 분위수
  즉 "모든 프롭 표면이 똑같이 비간섭적으로 산란한다면 도플러 전력분포는 이 히스토그램" 이다.
  가정이 없고(평면파도 안 쓴다), 측정과 같은 q 를 쓴다.

■ 여기가 이번 라운드의 물리 정정
  · pred_ff = f_tip*cos(el)  원거리장(평면파) 예측. 사용자가 "다툴 여지 없다" 한 그것.
  · 이 판의 R = 10 m 는 프롭 전체폭 D = 0.72 m 의 원거리장 경계 2D^2/lam = 12.0 m 안쪽이다.
    근거리장에서는 로터 허브가 중심에서 0.25 m 어긋나 있어 직하방(−90 도)에서도 시선이
    2 도 기울고 도플러가 정확히 0 이 아니다. 평면파 cos(el) 은 −90 도 근처에서 틀린 예측이다.

■ 기준(reference) — 산란 물리를 다 뺀 기하만의 신호
  report15_verdict_geomref.py 와 같은 모형: h(t) = sum_v exp(−j*2k*|tx − p_v(t)|), 균일 가중.
  geom_prop(프롭 꼭짓점만)의 도플러 진실값은 위 히스토그램(균일 가중)이므로,
  W_q(geom_prop) 이 W_q_pred 와 맞으면 추정기 자체가 검증된다.

⛔ GPU 를 쓰지 않는다(순수 numpy). 기존 원장을 덮어쓰지 않는다.
   산출물은 outputs/verify_po_elev_metric.json 하나뿐이다.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
PRF = 19700.0
RANGE_M = 10.0
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
F_FLASH = 126.66666666666667
F_TIP0 = 1272.91                    # el = 0 의 f_tip [Hz] = 2*(2 pi f_rev R)/lam
F_FORBID = 2.0 * F_TIP0             # 이 위는 물리적으로 불가능 → 잡음 바닥 추정 구간
QS = (0.75, 0.90, 0.95)
Q_MAIN = 0.90
PAD = 4
SEG_PERIODS = 2.0
SEG_HOP = 16
NPZ = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
OUT = os.path.join(ROOT, "outputs", "verify_po_elev_metric.json")


# ════════════════════════════════════════════════════════════════════════════
#  옛 잣대 (재현용)
# ════════════════════════════════════════════════════════════════════════════
def old_phase_ptp_deg(E):
    """1) np.unwrap 누적 위상의 변동폭 [deg] — 실은 권선수."""
    return float(np.ptp(np.unwrap(np.angle(np.asarray(E, complex)))) * 180.0 / np.pi)


def old_fft_width(E, thr_db=20.0, prf=PRF, pad=8):
    """2) 전 구간 단일 Hann FFT 에서 전역 최대 대비 −thr dB 인 최대 |f| [Hz]."""
    E = np.asarray(E, complex)
    n = len(E)
    Z = np.fft.fftshift(np.fft.fft(E * np.hanning(n), n=pad * n))
    f = np.fft.fftshift(np.fft.fftfreq(pad * n, 1.0 / prf))
    S = np.abs(Z)
    if S.max() <= 0:
        return 0.0
    return float(np.abs(f[S > S.max() * 10 ** (-thr_db / 20.0)]).max())


# ════════════════════════════════════════════════════════════════════════════
#  헤드라인 추정기
# ════════════════════════════════════════════════════════════════════════════
def ac_spectrum(x, prf=PRF, pad=PAD):
    """정지 성분 제거 + Hann + 제로패딩 → (f, P)."""
    x = np.asarray(x, complex)
    x = x - x.mean()
    n = len(x)
    Z = np.fft.fftshift(np.fft.fft(x * np.hanning(n), n=pad * n))
    f = np.fft.fftshift(np.fft.fftfreq(pad * n, 1.0 / prf))
    return f, np.abs(Z) ** 2


def w_quantile_spec(f, P, qs=QS, f_forbid=F_FORBID, smooth_hz=40.0, f_kin=None):
    """잡음 뺀 AC 스펙트럼의 분위 폭 [Hz] + 신뢰도.

    ⭐잡음 바닥은 금지대역의 **평균**이다(중앙값이 아니다). 주기도표 빈은 지수분포라
      중앙값은 평균의 0.693 배이고, 중앙값을 빼면 잡음이 통째로 양의 잔차로 남아
      폭이 잡음쪽으로 끌려간다(첫 판에서 실제로 그랬다).
    ⭐누적은 클리핑하지 않는다. 잡음 빈의 기여가 평균 0 이 되어 상쇄되도록.
    ⭐평활(≈40 Hz)로 주기도표 분산을 줄인다 — 우리 폭은 100 Hz 이상이라 손해가 없다."""
    df = float(f[1] - f[0])
    m = max(1, int(round(smooth_hz / df)) | 1)
    Ps = np.convolve(P, np.ones(m) / m, mode="same")
    nb = np.abs(f) >= f_forbid
    Pn = float(Ps[nb].mean()) if nb.sum() > 8 else 0.0
    Pc = Ps - Pn
    inb = ~nb
    sig = float(Pc[inb].clip(0).sum())
    noi = float(Pn * inb.sum())
    out = {"noise_floor": Pn,
           "snr_db": float(10 * np.log10(max(sig, 1e-300) / max(noi, 1e-300)))}
    o = np.argsort(np.abs(f))
    c = np.cumsum(Pc[o])
    tot = float(c[inb[o]].max()) if inb[o].any() else 0.0
    if tot <= 0:
        for q in qs:
            out[f"W{int(q*100)}"] = 0.0
        out["over_kinematic_frac"] = None
        return out
    c = c / tot
    for q in qs:
        i = int(np.argmax(c >= q)) if (c >= q).any() else len(c) - 1
        out[f"W{int(q*100)}"] = float(abs(f[o[i]]))
    if f_kin is not None and f_kin > 0:
        ov = Pc[inb & (np.abs(f) > f_kin)].clip(0).sum()
        out["over_kinematic_frac"] = float(ov / max(Pc[inb].clip(0).sum(), 1e-300))
    else:
        out["over_kinematic_frac"] = None
    return out


def edge_comb(f, P, f_flash=F_FLASH, snr_db=10.0, nmax=24, run=2):
    """조화 빗 위에서만 표본한 아치 가장자리.

    각 조화의 봉우리(+-12 Hz 최대)를 **국소 배경**(+-50 Hz 중앙값, 봉우리 제외)과 견준다.
    문턱 아래가 `run` 개 연달아 나오기 직전까지를 가장자리로 본다(지속 가장자리)."""
    df = float(f[1] - f[0])
    hw = max(1, int(round(12.0 / df)))
    bg = max(1, int(round(50.0 / df)))
    snr = []
    for k in range(1, nmax + 1):
        fh = k * f_flash
        if fh > 0.95 * PRF / 2:
            break
        pk, bk = [], []
        for sgn in (+1, -1):
            i = int(np.argmin(np.abs(f - sgn * fh)))
            pk.append(P[max(0, i - hw):i + hw + 1].max())
            lo, hi = P[max(0, i - bg):max(0, i - hw)], P[i + hw + 1:i + bg + 1]
            if lo.size + hi.size > 4:
                bk.append(np.median(np.concatenate([lo, hi])))
        if not bk:
            break
        snr.append(float(10 * np.log10(max(np.mean(pk), 1e-300)
                                       / max(np.mean(bk), 1e-300))))
    k_edge, miss = 0, 0
    for k, v in enumerate(snr, 1):
        if v > snr_db:
            if miss < run:
                k_edge = k
        else:
            miss += 1
            if miss >= run:
                break
    return dict(k_edge=int(k_edge), f_edge_hz=float(k_edge * f_flash),
                comb_snr_db=snr)


def _stft(x, prf=PRF, hop=SEG_HOP, pad=8):
    x = np.asarray(x, complex)
    nper = int(round(SEG_PERIODS * prf / F_FLASH))
    w = np.hanning(nper + 2)[1:-1]
    st = np.arange(0, len(x) - nper + 1, hop)
    nfft = pad * nper
    f = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / prf))
    S = np.empty((st.size, nfft))
    for i, s in enumerate(st):
        S[i] = np.abs(np.fft.fftshift(np.fft.fft(x[s:s + nper] * w, n=nfft)))
    return f, S, nper


def w95_stft(x, prf=PRF, q=0.95):
    """조각별 95 % 분위 폭의 중앙값 [Hz] (보조 잣대)."""
    f, S, _ = _stft(np.asarray(x, complex) - np.mean(x), prf)
    out = []
    for row in S:
        P = row ** 2
        t = P.sum()
        if t <= 0:
            continue
        c = float((f * P).sum() / t)
        o = np.argsort(np.abs(f - c))
        cum = np.cumsum(P[o]) / t
        k = min(int(np.searchsorted(cum, q)), len(o) - 1)
        out.append(float(abs(f[o[k]] - c)))
    return float(np.median(out)) if out else 0.0


def _deriv4(x, dt):
    return (-x[4:] + 8.0 * x[3:-1] - 8.0 * x[1:-3] + x[:-4]) / (12.0 * dt), x[2:-2]


def am_fm_bandwidth(E, prf=PRF):
    """B_tot^2 = B_am^2 + B_fm^2 분해 [Hz]. unwrap 을 안 쓴다."""
    x = np.asarray(E, complex)
    xd, xc = _deriv4(x, 1.0 / prf)
    A2 = (xc.conj() * xc).real
    te = A2.sum()
    if te <= 0:
        return dict(B_tot=0.0, B_am=0.0, B_fm=0.0, f_bar=0.0, identity_rel=0.0)
    ip = xd * xc.conj()
    A = np.sqrt(np.maximum(A2, 1e-300))
    f_bar = float(ip.imag.sum() / (2 * np.pi * te))
    m2t = float((np.abs(xd) ** 2).sum() / (4 * np.pi ** 2 * te))
    m2a = float(((ip.real / A) ** 2).sum() / (4 * np.pi ** 2 * te))
    m2f = float(((ip.imag / A) ** 2).sum() / (4 * np.pi ** 2 * te))
    return dict(B_tot=float(np.sqrt(max(m2t - f_bar ** 2, 0.0))),
                B_am=float(np.sqrt(max(m2a, 0.0))),
                B_fm=float(np.sqrt(max(m2f - f_bar ** 2, 0.0))),
                f_bar=f_bar,
                identity_rel=float(abs(m2t - (m2a + m2f)) / max(m2t, 1e-30)))


def measure(x, f_kin=None):
    """한 시계열에 새 잣대를 전부 적용. f_kin = 기하가 허용하는 최대 도플러 [Hz]."""
    x = np.asarray(x, complex)
    f, P = ac_spectrum(x)
    r = w_quantile_spec(f, P, f_kin=f_kin)
    r["edge_comb"] = edge_comb(f, P)
    a = np.abs(x)
    z = np.where(a > 0, x / np.maximum(a, 1e-300), 1.0 + 0j)     # AM 제거
    fz, Pz = ac_spectrum(z)
    rz = w_quantile_spec(fz, Pz, f_kin=f_kin)
    r["fm"] = {k: rz[k] for k in ("W75", "W90", "W95", "snr_db",
                                  "over_kinematic_frac")}
    r["W95_stft"] = w95_stft(x)
    r["am_fm"] = am_fm_bandwidth(x)
    r["am_fm_ac"] = am_fm_bandwidth(x - x.mean())
    r["old_phase_ptp_deg"] = old_phase_ptp_deg(x)
    r["old_w20_hz"] = old_fft_width(x, 20.0)
    return r


# ════════════════════════════════════════════════════════════════════════════
#  기하 기준 + 예측 히스토그램
# ════════════════════════════════════════════════════════════════════════════
def los(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def geom_reference(n=4096, prf=PRF, chunk=256):
    """기하만의 신호 + 꼭짓점 도플러 히스토그램에서 만든 예측."""
    import articulated_fast as AF
    from drones import DRONES
    spec = DRONES["matrice4e"]
    fp = AF.FastPoser(spec)
    rpms = np.array([3808.36, 3791.64, 3795.402, 3804.598])
    ph = AF.rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    F = np.asarray(fp.f, int)
    g = np.asarray(fp.g, dtype=object)
    Fp = F[g == "prop"]
    sel = np.unique(Fp.ravel())
    remap = {v: i for i, v in enumerate(sel)}
    k = 2.0 * np.pi / LAM

    V0 = np.asarray(fp.pose(ph[0]).v, float)
    cen = 0.5 * (V0.min(axis=0) + V0.max(axis=0))
    tx = {el: cen + RANGE_M * los(0.0, el) for el in ELS}

    # 꼭짓점 면적 가중 (메쉬 밀도 편향 제거) — 강체회전이라 자세와 무관
    ar = 0.5 * np.linalg.norm(np.cross(V0[Fp[:, 1]] - V0[Fp[:, 0]],
                                       V0[Fp[:, 2]] - V0[Fp[:, 0]]), axis=1)
    wv = np.zeros(sel.size)
    for c in range(3):
        np.add.at(wv, [remap[v] for v in Fp[:, c]], ar / 3.0)
    wv /= wv.sum()

    hp = {el: np.zeros(n, complex) for el in ELS}
    ha = {el: np.zeros(n, complex) for el in ELS}
    D = {el: np.zeros((n, sel.size), np.float32) for el in ELS}
    for s in range(0, n, chunk):
        e = min(n, s + chunk)
        Vs = np.stack([np.asarray(fp.pose(ph[i]).v, float) for i in range(s, e)])
        Vp = Vs[:, sel, :]
        for el in ELS:
            d = np.linalg.norm(Vp - tx[el], axis=2)
            D[el][s:e] = d.astype(np.float32)
            hp[el][s:e] = np.exp(-2j * k * d).sum(axis=1)
            ha[el][s:e] = np.exp(-2j * k * np.linalg.norm(Vs - tx[el], axis=2)).sum(axis=1)

    pred = {}
    for el in ELS:
        fd = 2.0 * np.gradient(D[el].astype(np.float64), 1.0 / prf, axis=0) / LAM
        af = np.abs(fd).ravel()
        w = np.tile(wv, fd.shape[0])
        o = np.argsort(af)
        cw = np.cumsum(w[o]) / w.sum()
        p = dict(f_max=float(af.max()),
                 f_rms=float(np.sqrt((w * af[np.arange(af.size)] ** 2).sum() / w.sum())))
        for q in QS:
            p[f"W{int(q*100)}"] = float(af[o[min(int(np.searchsorted(cw, q)),
                                                 len(o) - 1)]])
        pred[el] = p
    return dict(prop=hp, all=ha), pred, int(sel.size)


# ════════════════════════════════════════════════════════════════════════════
#  합성 대조군 — 잣대 자체에 눈금을 매긴다
# ════════════════════════════════════════════════════════════════════════════
def synth(beta, b_over_a, n=4096, prf=PRF, f_rev=63.333333, nblade=2):
    """x = b + (1/K) sum_k exp(j beta sin(2 pi f_rev t + k pi/K)) — FM 폭을 우리가 안다."""
    t = np.arange(n) / prf
    x = np.zeros(n, complex)
    for kk in range(nblade):
        x += np.exp(1j * beta * np.sin(2 * np.pi * f_rev * t + kk * np.pi / nblade))
    return x / nblade + b_over_a


def pearson(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m] - a[m].mean(), b[m] - b[m].mean()
    d = np.sqrt((a ** 2).sum() * (b ** 2).sum())
    return float((a * b).sum() / d) if d > 0 else float("nan")


def spearman(a, b):
    from scipy.stats import rankdata
    return pearson(rankdata(a), rankdata(b))


# ════════════════════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    d = np.load(NPZ)
    cos_el = {el: float(np.cos(np.radians(el))) for el in ELS}
    ekeys = [f"{el:+.0f}" for el in ELS]

    # ── 1. 옛 잣대 부검 ────────────────────────────────────────────────────
    autopsy = {}
    for el in ELS:
        E = d[f"ours/el{el:+.0f}"]
        a = np.abs(E)
        dph = np.diff(np.angle(E))
        dph = (dph + np.pi) % (2 * np.pi) - np.pi
        n = len(E)
        Z = np.fft.fftshift(np.fft.fft(E * np.hanning(n), n=8 * n))
        f = np.fft.fftshift(np.fft.fftfreq(8 * n, 1.0 / PRF))
        S = np.abs(Z) / np.abs(Z).max()
        db = 20 * np.log10(S + 1e-30)
        ft = max(F_TIP0 * cos_el[el], 1.0)
        widths = {f"w{T}": old_fft_width(E, T) for T in (10, 15, 20, 25, 30, 40)}
        dc = float(db[np.abs(f) < 40].max())
        arch = float(db[(np.abs(f) > 0.35 * ft) & (np.abs(f) < ft)].max())
        autopsy[f"{el:+.0f}"] = dict(
            phase_ptp_deg=old_phase_ptp_deg(E),
            winding_turns=old_phase_ptp_deg(E) / 360.0,
            amp_min_over_median=float(a.min() / np.median(a)),
            amp_min_db=float(20 * np.log10(a.min() / np.median(a))),
            n_null_events_25pct=int(((a[1:-1] < a[:-2]) & (a[1:-1] < a[2:])
                                     & (a[1:-1] < 0.25 * np.median(a))).sum()),
            max_dphi_deg=float(np.degrees(np.abs(dph).max())),
            max_dphi_as_hz=float(np.abs(dph).max() / (2 * np.pi) * PRF),
            max_dphi_as_mps=float(np.abs(dph).max() / (2 * np.pi) * PRF * LAM / 2),
            v_tip_mps=float(F_TIP0 * cos_el[el] * LAM / 2),
            n_jumps_over_90deg=int((np.abs(dph) > np.pi / 2).sum()),
            widths_hz=widths,
            width_threshold_spread=float(max(widths.values())
                                         / max(min(widths.values()), 1e-9)),
            dc_line_db=dc, arch_peak_db=arch, dc_minus_arch_db=dc - arch)

    # ── 2. 기하 기준 + 예측 ────────────────────────────────────────────────
    print("기하 기준 계산 중 (4096 자세 x 7 앙각, 순수 numpy)...", flush=True)
    gser, pred, nvp = geom_reference()
    print(f"  프롭 꼭짓점 {nvp} 개 · {time.time()-t0:.0f}s", flush=True)

    # ── 3. 새 잣대로 다시 재기 ─────────────────────────────────────────────
    arms = {"ours": {el: d[f"ours/el{el:+.0f}"] for el in ELS},
            "sionna": {el: d[f"sionna/el{el:+.0f}"] for el in ELS},
            "geom_prop": gser["prop"], "geom_all": gser["all"]}
    rows = {}
    for arm, ser in arms.items():
        rows[arm] = {}
        for el in ELS:
            m = measure(ser[el], f_kin=pred[el]["f_max"])
            m["cos_el"] = cos_el[el]
            m["pred_ff_hz"] = F_TIP0 * cos_el[el]
            m["pred_geom"] = pred[el]
            rows[arm][f"{el:+.0f}"] = m

    # ── 4. 합성 대조군 ─────────────────────────────────────────────────────
    beta0 = F_TIP0 / 63.333333
    syn_am = {}
    for r in (0.0, 0.5, 0.9, 0.99, 1.0, 1.05, 2.0):
        x = synth(beta0, r)
        mm = measure(x, f_kin=F_TIP0)
        syn_am[f"{r:g}"] = dict(
            b_over_a=r,
            amp_min_over_median=float(np.abs(x).min() / np.median(np.abs(x))),
            old_phase_ptp_deg=mm["old_phase_ptp_deg"], old_w20_hz=mm["old_w20_hz"],
            W90=mm["W90"], W90_fm=mm["fm"]["W90"],
            edge_comb_hz=mm["edge_comb"]["f_edge_hz"],
            B_fm=mm["am_fm"]["B_fm"], B_am=mm["am_fm"]["B_am"])
    syn_cos = {}
    for el in ELS:
        x = synth(beta0 * cos_el[el], 0.9)
        mm = measure(x, f_kin=F_TIP0*cos_el[el])
        syn_cos[f"{el:+.0f}"] = dict(
            cos_el=cos_el[el], truth_edge_hz=F_TIP0 * cos_el[el],
            old_phase_ptp_deg=mm["old_phase_ptp_deg"], old_w20_hz=mm["old_w20_hz"],
            W90=mm["W90"], W90_fm=mm["fm"]["W90"],
            edge_comb_hz=mm["edge_comb"]["f_edge_hz"], B_fm=mm["am_fm"]["B_fm"])

    # ── 5. 판정 ────────────────────────────────────────────────────────────
    def verdict(vals, pr, absolute):
        v = np.array([vals[k] for k in ekeys], float)
        p = np.array([pr[k] for k in ekeys], float)
        s = 1.0 if absolute else (v[0] / p[0] if p[0] > 0 else np.nan)
        ratio = v / (s * np.where(p > 0, p, np.nan))
        fin = ratio[:-1][np.isfinite(ratio[:-1])]
        return dict(r_pearson=pearson(v, p), r_spearman=spearman(v, p),
                    scale_at_0=float(s),
                    ratio_by_el={k: (float(x) if np.isfinite(x) else None)
                                 for k, x in zip(ekeys, ratio)},
                    ratio_spread=float(fin.max() / fin.min()) if fin.size else None,
                    values_hz={k: float(x) for k, x in zip(ekeys, v)})

    pred_cos = {k: F_TIP0 * cos_el[el] for k, el in zip(ekeys, ELS)}
    pred_geo = {k: pred[el][f"W{int(Q_MAIN*100)}"] for k, el in zip(ekeys, ELS)}
    getters = (("W90", lambda m: m["W90"]),
               ("W90_fm", lambda m: m["fm"]["W90"]),
               ("W75", lambda m: m["W75"]),
               ("edge_comb", lambda m: m["edge_comb"]["f_edge_hz"]),
               ("W95_stft", lambda m: m["W95_stft"]),
               ("B_fm", lambda m: m["am_fm"]["B_fm"]),
               ("OLD_phase_ptp", lambda m: m["old_phase_ptp_deg"]),
               ("OLD_w20", lambda m: m["old_w20_hz"]))
    verd = {}
    for arm in arms:
        verd[arm] = {}
        for name, get in getters:
            vals = {k: get(rows[arm][k]) for k in ekeys}
            verd[arm][name] = dict(
                vs_cos_shape=verdict(vals, pred_cos, absolute=False),
                vs_geom_absolute=verdict(vals, pred_geo, absolute=True))

    J = dict(
        _meta=dict(
            generator="benchmark/verify_po_elev_metric.py",
            date=time.strftime("%Y-%m-%d %H:%M:%S"),
            question_ko="도플러 폭을 재는 옳은 잣대를 정하고 앙각 7 점을 다시 잰다",
            source_npz=NPZ, fc_hz=FC, prf_hz=PRF, range_m=RANGE_M,
            f_flash_hz=F_FLASH, f_tip0_hz=F_TIP0, f_forbid_hz=F_FORBID,
            elevations_deg=list(ELS), q_main=Q_MAIN, gpu="사용 안 함 (순수 numpy)",
            n_prop_vertices=nvp,
            unit_warning_ko=("ours 는 산란 면적분 E [m^2], sionna 는 채널 h [무차원], "
                             "geom_* 는 무가중 위상합 [무차원] — 팔 사이 절대 레벨 비교 금지. "
                             "폭 [Hz] 은 단위와 무관하므로 팔 사이 비교가 유효하다."),
            nearfield_ko=("R = 10 m 는 프롭 전체폭 D = 0.72 m 의 원거리장 경계 "
                          "2D^2/lam = 12.0 m 안쪽이다. 그래서 −90 도에서도 도플러가 0 이 아니다."),
        ),
        metric_definitions=dict(
            W_q=("헤드라인. x−mean(x) 의 Hann FFT 전력을 40 Hz 로 평활하고, "
                 "|f|>=2*f_tip(0)=2546 Hz(물리적 금지대역)의 **평균**을 잡음으로 뺀 뒤 "
                 "누적 전력이 q 에 닿는 |f|. 문턱 없음, 전역 최대 안 씀. "
                 "중앙값을 빼면 잡음 잔차가 남아 폭이 부풀므로 반드시 평균."),
            floor_ko=("측정의 원리적 바닥 = f_flash = 126.67 Hz. 주기 로터의 스펙트럼은 "
                      "n*f_flash 빗 위에만 살아서 그보다 좁은 폭은 표현이 안 된다."),
            over_kinematic_frac=("기하가 허용하는 최대 도플러(pred f_max) 를 넘는 곳에 "
                                 "남아 있는 AC 에너지 몫. 0 이어야 정상."),
            W_q_fm=("z = E/|E| (AM 완전 제거) 에 같은 추정기. AM 이 폭을 만든 것인지 "
                    "FM 이 만든 것인지 가른다."),
            edge_comb=("AC 스펙트럼을 n*f_flash 빗 위에서만 표본해 잡음 대비 10 dB 를 "
                       "넘는 최고 조화 → f_edge = n*f_flash. 광대역 잡음을 배제한 가장자리."),
            W95_stft="조각별(블레이드 2주기) 95 % 분위 폭의 중앙값. 보조.",
            B_fm=("AM/FM 분해 B_tot^2 = B_am^2 + B_fm^2 의 FM 몫. 진단용. "
                  "에너지 가중이라 정지 동체가 크면 눌린다 → 헤드라인 금지."),
            pred_geom=("꼭짓점 왕복거리를 직접 미분한 |f_dop| 의 면적가중 q 분위수. "
                       "측정과 같은 q 라 절대비교가 가능하다. 평면파 가정 없음."),
            pred_ff="f_tip*cos(el) — 원거리장(평면파) 예측. 가장자리 양이라 분위 폭과 모양 상수가 다르다.",
            OLD_phase_ptp=("np.ptp(np.unwrap(np.angle(E))). 대역폭이 아니라 권선수다. "
                           "합신호가 원점 근처를 지나면 한 바퀴마다 360 도가 없던 대역폭으로 적힌다."),
            OLD_w20=("전 구간 단일 Hann FFT 에서 전역 최대(= 동체 DC 선) 대비 −20 dB 인 최대 |f|. "
                     "재는 것이 도플러 폭이 아니라 동체/로터 세기비다."),
        ),
        old_metric_autopsy=autopsy,
        prediction_geometric={f"{el:+.0f}": pred[el] for el in ELS},
        rows=rows,
        synthetic_am_sweep=syn_am,
        synthetic_cos_sweep=syn_cos,
        verdict=verd,
    )
    J["_meta"]["seconds"] = float(time.time() - t0)
    with open(OUT, "w") as fh:
        json.dump(J, fh, ensure_ascii=False, indent=1)

    # ── 화면 요약 ─────────────────────────────────────────────────────────
    print("\n=== 예측: 같은 분위(q=0.90)로 만든 기하 예측 vs 평면파 f_tip*cos ===")
    print(f"{'el':>5} {'cos':>6} {'f_tip*cos':>10} {'pred W90':>9} {'pred max':>9}")
    for el in ELS:
        print(f"{el:>5.0f} {cos_el[el]:>6.3f} {F_TIP0*cos_el[el]:>10.1f} "
              f"{pred[el]['W90']:>9.1f} {pred[el]['f_max']:>9.1f}")
    for arm in ("geom_prop", "ours", "sionna"):
        print(f"\n=== {arm} ===")
        print(f"{'el':>5} {'W90':>8} {'W90_fm':>8} {'edge_comb':>10} {'W75':>8} "
              f"{'S/N':>7} {'초과%':>6} {'옛 ptp':>9} {'옛 w20':>8}")
        for el in ELS:
            m = rows[arm][f"{el:+.0f}"]
            print(f"{el:>5.0f} {m['W90']:>8.1f} {m['fm']['W90']:>8.1f} "
                  f"{m['edge_comb']['f_edge_hz']:>10.1f} {m['W75']:>8.1f} "
                  f"{m['snr_db']:>7.1f} {100*(m['over_kinematic_frac'] or 0):>6.1f} {m['old_phase_ptp_deg']:>9.1f} "
                  f"{m['old_w20_hz']:>8.1f}")
    print("\n=== 판정: cos(el) 모양을 따르나 (0 도로 눈금 맞춘 뒤 비의 산포, −90 제외) ===")
    print(f"{'팔':>10} {'잣대':>14} {'r(cos)':>8} {'rho':>7} {'비산포':>8} | "
          f"{'기하예측 대비 r':>10} {'비산포':>8}")
    for arm in ("geom_prop", "ours", "sionna"):
        for nm, _ in getters:
            a = verd[arm][nm]["vs_cos_shape"]
            b = verd[arm][nm]["vs_geom_absolute"]
            sp = a["ratio_spread"]
            sb = b["ratio_spread"]
            print(f"{arm:>10} {nm:>14} {a['r_pearson']:>8.3f} {a['r_spearman']:>7.3f} "
                  f"{(f'{sp:.2f}' if sp else '  -'):>8} | {b['r_pearson']:>10.3f} "
                  f"{(f'{sb:.2f}' if sb else '  -'):>8}")
    print(f"\nOK {OUT}  ({J['_meta']['seconds']:.0f}s)")


if __name__ == "__main__":
    main()
