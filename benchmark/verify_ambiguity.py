# -*- coding: utf-8 -*-
"""
verify_ambiguity.py — [E3] **모호함수(Ambiguity Function)**: 검출기 성능의 상한
==============================================================================
탐지·추적 벤치마크를 **하기 전에** 알아야 할 것: 각 조명원 파형의 기준신호가 만드는
|chi(tau, f_d)| 이 실제로 어떤 모양인가. 이것이 거리·도플러 분해능, 부엽(강한 표적이
약한 표적을 가리는 정도), 그리고 **가짜 표적(모호 봉우리)** 의 상한을 정한다.

■ 무엇을 계산하는가 — "검출기의 모호함수"(파형의 교과서 AF 가 아니라)
  passive_process.range_doppler 는 CPI 를 **프레임(=기준신호 1주기)** 으로 쪼개서
  프레임마다 순환상관(fast-time) → 프레임축 Hann + FFT(slow-time) 한다. 그러니 우리가
  재야 할 것은 **그 처리가 점표적에 주는 응답**이다:

      chi(tau, fd) = SUM_n  x_tau[n] * conj(x[n]) * w[n] * exp(+j 2pi fd n / fs)
      x        = run_min_cell 과 **동일하게** 만든 기준 CPI = tile(wf.ref / rms(wf.tx), M)
                 (WiFi 는 frame_len() 규약대로 패킷률 1 kHz 슬롯으로 zero-pad)
      x_tau    = 주파수영역 위상램프로 만든 **분수지연** 사본(make_cpi 와 같은 방식)
      w[p]     = np.hanning(M)  (range_doppler 의 slow-time 창과 동일)

  기준 CPI 는 프레임 주기 Lf 로 **정확히 주기적**이므로 AF 가 **엄밀히 분리**된다:

      chi(tau, fd) = A(tau, fd) * D(fd)
      A(tau,fd) = SUM_{n<Lf} x_tau[n] conj(x[n]) exp(+j2pi fd n/fs)   (프레임 내부)
      D(fd)     = SUM_{p<M}  w[p] exp(+j2pi fd p Lf/fs)               (slow-time 배열인자)

  → 근사가 아니라 **항등식**이다(주기성 때문). 덕분에 GPU 로 정확히·싸게 계산한다.
  → D(fd) 는 fd = k*PRF (PRF=fs/Lf) 에서 **0 dB 로 되살아난다** = 도플러 모호(replica).

■ 재는 것
  1. 거리 분해능  : |chi(tau,0)| 의 -3 dB 폭 [m].  ※ **바이스태틱**이라 Rb = c*tau (왕복 아님)
                    → 이론치는 c/B_ref (모노스태틱 c/2B 가 아니다; geometry.py 규약과 일치)
  2. 도플러 분해능: |chi(0,fd)| 의 -3 dB 폭 [Hz]. 이론 1/T_CPI (Hann 이 약 1.44배 넓힘)
  3. PSL / ISL    : 주엽(첫 널) 바깥 최대/적분 부엽
  4. 모호 봉우리  : 전 지연축(프레임 전체) x 도플러축에서 찾은 국소 최대 — OFDM 심볼 반복,
                    CP, comb(빗살) 격자가 만드는 **가짜 표적**의 위치
  5. 바닥 유령 겹침: 유령 셀(진짜 표적 대비 +3.53 m)에 표적 자신의 부엽/모호봉우리가
                    얼마나 새는가 — 유령(-18.1 dB)보다 크면 유령 검출은 해석 불가가 된다.
  6. 5G SSB 이중고: 좁은 대역(거리) + **20 ms 버스트 주기**(도플러 모호)를 AF 로 보인다.

실행:  ~/.venvs/py312/bin/python benchmark/verify_ambiguity.py
출력:  outputs/verify_ambiguity.json, outputs/figures/verify_ambiguity_{af,range,doppler}.png
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", "src"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick          # noqa: E402  — torch import 전에!
pick()

import numpy as np            # noqa: E402
import torch                  # noqa: E402

from waveforms import wifi_80211ac, lte_downlink, nr_downlink, PILOT_RATE_HZ  # noqa: E402
from run_min_cell import frame_len                                            # noqa: E402
from geometry import TX, RX, CENTER, SPEED, SPAN, floor_ghost                 # noqa: E402
from scenarios import radial                                                  # noqa: E402
from bistatic_scene import bistatic_params, C0                                # noqa: E402

# GPU 선택·강제 (2026-07-28): 이 하네스는 (Lf x F) 지수행렬을 만들기 때문에 순간 메모리가 크다.
#   공용 GPU 에서 **타 사용자와 경합**하면 단일 할당이 실패한다(실측: 7.63 GiB 요구 vs 여유 5.54 GiB).
#   · SIONNA2_GPU=N   → 그 카드로 고정 (gpu.pick 규약과 동일)
#   · SIONNA2_CPU=1   → CPU 폴백(느리지만 251 GB RAM 이라 확실히 끝난다)
#   그리고 아래 frame_af 는 도플러축을 청크로 잘라 complex128 중간값이 통째로 뜨지 않게 한다.
if os.environ.get("SIONNA2_CPU") == "1":
    DEV = torch.device("cpu")
else:
    _g = os.environ.get("SIONNA2_GPU")
    if _g:
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", _g)
    DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
FD_CHUNK = int(os.environ.get("SIONNA2_FD_CHUNK", "512"))   # 도플러축 청크(메모리 레버)
OUT = os.path.abspath(os.path.join(_HERE, "..", "outputs", "verify_ambiguity.json"))
FIGDIR = os.path.abspath(os.path.join(_HERE, "..", "outputs", "figures"))

M_CPI = 48                     # run_min_cell/report4·5 기본 CPI 프레임 수
RB_LO, RB_HI = -30.0, 80.0     # 미세 지연격자 범위 [m] (챔버 창 60 m 를 포함)
RB_STEP = 0.05                 # 미세 지연격자 간격 [m]  → LTE(ΔRb 16.7m)~5G(3.1m) 모두 충분
FD_MAP = 260.0                 # 2D 지도 도플러 반폭 [Hz] (드론 도플러 대역)
NFD_MAP = 521


def waveform_set():
    """벤치마크 3종 x 점유모드 G1/G3. (키, 표시명, wf)"""
    out = []
    for occ in ("G1", "G3"):
        out.append((f"wifi_{occ}", f"WiFi 80MHz {occ}",
                    wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy=occ)))
        out.append((f"lte_{occ}", f"LTE 20MHz {occ}",
                    lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy=occ)))
        out.append((f"nr_{occ}", f"5G NR 100MHz {occ}",
                    nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy=occ)))
    return out


# --------------------------------------------------------------------------- #
#  기준 CPI 프레임 — run_min_cell.run_cell 과 **똑같이** 만든다
# --------------------------------------------------------------------------- #
def ref_frame_of(wf):
    txp = np.sqrt(np.mean(np.abs(wf.tx) ** 2) + 1e-30)
    rf = wf.ref.astype(complex) / txp
    Lf = frame_len(wf)                       # WiFi 는 패킷률(1 kHz) 슬롯으로 pad
    if Lf > len(rf):
        rf = np.concatenate([rf, np.zeros(Lf - len(rf), complex)])
    return rf[:Lf], Lf


def slow_time_af(M, Lf, fs, fd_hz):
    """D(fd) = SUM_p w[p] exp(+j2pi fd p Lf/fs) — range_doppler 의 Hann slow-time."""
    w = np.hanning(M)
    p = np.arange(M)
    return (w[None, :] * np.exp(2j * np.pi * np.asarray(fd_hz)[:, None] * p[None, :] * Lf / fs)).sum(1)


# --------------------------------------------------------------------------- #
#  A(tau, fd) — 프레임 내부 항 (GPU)
# --------------------------------------------------------------------------- #
def frame_af(rf, fs, tau_s, fd_hz, chunk=64):
    """A(tau,fd) = SUM_{n<Lf} x_tau[n] conj(x[n]) exp(+j2pi fd n/fs).
    x_tau 는 주파수영역 위상램프(분수지연) — make_cpi 의 delayed() 와 동일한 연산."""
    Lf = len(rf)
    x = torch.as_tensor(rf, dtype=torch.complex64, device=DEV)
    X = torch.fft.fft(x)
    f = torch.fft.fftfreq(Lf, d=1.0 / fs).to(DEV)
    n = torch.arange(Lf, device=DEV, dtype=torch.float64)
    fdt = torch.as_tensor(fd_hz, device=DEV, dtype=torch.float64)
    # ⚠ 메모리: 예전에는 E(Lf x F) 를 float64 지수로 **한 번에** 만들어 complex128 중간값이
    #   그대로 떴다(실측 7.63 GiB). 결과는 어차피 complex64 로 캐스팅되므로,
    #   도플러축을 FD_CHUNK 로 잘라 만들면 **수치는 비트단위 동일**하고 순간 메모리만 1/(F/청크) 이 된다.
    E = torch.empty((Lf, len(fd_hz)), dtype=torch.complex64, device=DEV)
    for j0 in range(0, len(fd_hz), FD_CHUNK):
        j1 = min(j0 + FD_CHUNK, len(fd_hz))
        E[:, j0:j1] = torch.exp(2j * np.pi * fdt[None, j0:j1] * n[:, None] / fs).to(torch.complex64)
    xc = torch.conj(x)
    out = torch.empty((len(tau_s), len(fd_hz)), dtype=torch.complex64, device=DEV)
    for i0 in range(0, len(tau_s), chunk):
        t = torch.as_tensor(tau_s[i0:i0 + chunk], device=DEV, dtype=torch.float64)
        ramp = torch.exp(-2j * np.pi * f[None, :].to(torch.float64) * t[:, None]).to(torch.complex64)
        xt = torch.fft.ifft(X[None, :] * ramp, dim=1)             # (k, Lf) 분수지연
        out[i0:i0 + chunk] = (xt * xc[None, :]) @ E               # (k, F)
    return out.cpu().numpy()


def full_plane_af(rf, fs, fd_hz):
    """전 지연축(정수 lag, 프레임 전체 = 순환) x 도플러 → 모호 봉우리 사냥용.
    A(l,fd) = SUM_n x[n-l] conj(x[n]) e^{+j2pi fd n/fs}  (l = 0..Lf-1, 순환)."""
    Lf = len(rf)
    x = torch.as_tensor(rf, dtype=torch.complex64, device=DEV)
    X = torch.fft.fft(x)
    n = torch.arange(Lf, device=DEV, dtype=torch.float64)
    res = np.empty((len(fd_hz), Lf), dtype=np.float32)
    for i, fd in enumerate(fd_hz):
        u = torch.conj(x) * torch.exp(2j * np.pi * fd * n / fs).to(torch.complex64)
        # SUM_n x[n-l] u[n] = IFFT( FFT(x) * conj(FFT(conj(u))) )  (순환 상관)
        A = torch.fft.ifft(X * torch.conj(torch.fft.fft(torch.conj(u))))
        res[i] = torch.abs(A).cpu().numpy()
    return res                                    # (F, Lf)


# --------------------------------------------------------------------------- #
#  측정 유틸
# --------------------------------------------------------------------------- #
def _half_width(ax, mag):
    """피크(중앙) 기준 -3 dB 전폭. 선형보간. ax 는 단조증가, 피크는 argmax."""
    i = int(np.argmax(mag))
    h = mag[i] / np.sqrt(2.0)
    def cross(rng):
        prev = i
        for j in rng:
            if mag[j] < h:
                x0, x1 = ax[prev], ax[j]
                y0, y1 = mag[prev], mag[j]
                return x0 + (h - y0) * (x1 - x0) / (y1 - y0 + 1e-30)
            prev = j
        return None
    lo = cross(range(i - 1, -1, -1))
    hi = cross(range(i + 1, len(ax)))
    if lo is None or hi is None:
        return None
    return float(hi - lo)


def _first_null(ax, mag, fallback):
    """피크에서 바깥으로 가며 만나는 첫 국소최소(널)의 |축 좌표|.
    ⚠ 격자 끝까지 국소최소가 없으면(=주엽에 뚜렷한 널이 없음 — 스펙트럼이 테이퍼된 경우)
      **격자 끝값을 돌려주지 않고** fallback(이론 널)을 쓰고 found=False 를 알린다.
      (그러지 않으면 5G SSB 처럼 널이 없는 파형에서 '주엽 폭 = 격자 끝'이 되어
       부엽 영역이 사라지고 PSL 이 비현실적으로 좋아 보인다.)"""
    i = int(np.argmax(mag))
    best = None
    for rng in (range(i + 1, len(mag) - 1), range(i - 1, 0, -1)):
        for j in rng:
            if mag[j] <= mag[j - 1] and mag[j] <= mag[j + 1]:
                d = abs(ax[j] - ax[i])
                best = d if best is None else max(best, d)
                break
    if best is None:
        return float(fallback), False
    return float(best), True


def db(v, ref):
    return float(20 * np.log10(np.maximum(v, 1e-12) / ref))


# --------------------------------------------------------------------------- #
#  파형 1개 측정
# --------------------------------------------------------------------------- #
def analyze(key, name, wf, ghost_ctx):
    rf, Lf = ref_frame_of(wf)
    fs = wf.fs_hz
    prf = fs / Lf                                     # 프레임률 = 시뮬 PRF
    T_cpi = M_CPI * Lf / fs
    tau_grid = np.arange(RB_LO, RB_HI + 1e-9, RB_STEP) / C0        # 미세 지연[s]
    rb_grid = tau_grid * C0
    fd_grid = np.linspace(-FD_MAP, FD_MAP, NFD_MAP)

    A = frame_af(rf, fs, tau_grid, fd_grid)                        # (K, F)
    D = slow_time_af(M_CPI, Lf, fs, fd_grid)                       # (F,)
    chi = np.abs(A * D[None, :])
    peak = float(chi.max())
    chi_db = 20 * np.log10(chi / peak + 1e-12)

    # --- 거리 컷 (fd=0) — 미세격자
    i0 = int(np.argmin(np.abs(fd_grid)))
    rcut = chi[:, i0]
    dR3 = _half_width(rb_grid, rcut)                               # -3 dB 폭 [m]
    dR_theory = C0 / wf.ref_bw_hz                                  # 바이스태틱 c/B_ref
    Rnull, rnull_found = _first_null(rb_grid, rcut, dR_theory)

    # --- 도플러 컷 (tau=0) — 미세격자(모호 replica 까지)
    fd_fine = np.linspace(-1.6 * prf, 1.6 * prf, 6401)
    A0 = frame_af(rf, fs, np.array([0.0]), fd_fine)[0]
    D0 = slow_time_af(M_CPI, Lf, fs, fd_fine)
    dcut = np.abs(A0 * D0)
    dcut_db = 20 * np.log10(dcut / dcut.max() + 1e-12)
    dF3 = _half_width(fd_fine, dcut)
    dF_theory = 1.0 / T_cpi
    Fnull, _ = _first_null(fd_fine, dcut, 2.0 / T_cpi)             # Hann 첫 널 = 2/T_CPI
    # 도플러 모호 replica 높이 = |chi(0, PRF)| — slow-time D(fd) 만 보면 fd=PRF 에서 0 dB 지만,
    #   **프레임 내부 항 A(0,PRF)** 가 이를 눌러줄 수 있다: 기준신호가 프레임 전체에 고르게
    #   퍼져 있으면(LTE CRS) 프레임 안에서 위상이 한 바퀴 돌아 상쇄되고, 버스트형(WiFi LTF,
    #   5G SSB)이면 상쇄가 없어 replica 가 **0 dB 그대로** 살아난다.
    rep = float(np.abs(frame_af(rf, fs, np.array([0.0]), np.array([prf]))[0, 0]
                       * slow_time_af(M_CPI, Lf, fs, np.array([prf]))[0]))
    replica_db = db(rep, dcut.max())
    # replica 를 정하는 것은 '점유율'이 아니라 **프레임 안에서 에너지가 얼마나 퍼져 있는가**이다:
    #   A(0,PRF) = SUM_n |x[n]|^2 exp(+j2pi n/Lf)  = 에너지분포의 특성함수(주파수 1/Lf).
    #   에너지가 프레임 전체에 고르게 퍼지면(LTE CRS: l=0,4,7,11) 위상이 한 바퀴 돌아 상쇄되고,
    #   앞쪽에 뭉쳐 있으면(5G SSB: l=0..3, WiFi LTF: 1심볼) 상쇄가 없어 replica 가 0 dB 로 산다.
    e = np.abs(rf) ** 2
    e = e / (e.sum() + 1e-30)
    n_idx = np.arange(Lf)
    ref_duty = float(np.mean(np.abs(rf) ** 2 > 1e-6 * np.mean(np.abs(rf) ** 2)))   # 시간점유율
    mu = float((e * n_idx).sum())
    ref_spread = float(np.sqrt((e * (n_idx - mu) ** 2).sum()) / Lf)                # rms 확산/프레임
    #   균등분포면 1/sqrt(12)=0.289 (최대), 한 점에 뭉치면 0

    # --- 전 평면(정수 lag x 무모호 도플러 M빈) → 전역 PSL/ISL/모호봉우리
    fd_bins = (np.arange(M_CPI) - M_CPI // 2) * prf / M_CPI        # ±PRF/2 무모호 구간
    P = full_plane_af(rf, fs, fd_bins)                             # (M, Lf)
    Dl = np.abs(slow_time_af(M_CPI, Lf, fs, fd_bins))
    P = P * Dl[:, None]
    gpeak = float(P.max())
    lag = np.arange(Lf)
    lag_m = np.where(lag <= Lf // 2, lag, lag - Lf) * C0 / fs      # 순환 → ±
    main = (np.abs(lag_m)[None, :] <= Rnull) & (np.abs(fd_bins)[:, None] <= Fnull)
    psl_2d = db(P[~main].max(), gpeak)
    isl_2d = float(10 * np.log10((P[~main] ** 2).sum() / (P[main] ** 2).sum()))

    # 거리축(fd=0) 전역 부엽 — OFDM 반복구조가 만드는 봉우리
    zrow = int(np.argmin(np.abs(fd_bins)))
    rline = P[zrow]
    rline_db = 20 * np.log10(rline / rline.max() + 1e-12)
    off = np.abs(lag_m) > Rnull
    psl_range = float(rline_db[off].max())
    isl_range = float(10 * np.log10((rline[off] ** 2).sum() / (rline[~off] ** 2).sum()))

    # **챔버 창 안**의 PSL/ISL — 검출기가 실제로 계산하는 RD 맵(|Rb|<=60 m, 전 도플러빈)
    #   전역 PSL/ISL 은 km 단위 지연축까지 적분하므로 '검출기가 보는 값'이 아니다.
    win = np.abs(lag_m) <= 60.0
    Pw = P[:, win]; mw = main[:, win]
    psl_ch = db(Pw[~mw].max(), gpeak)
    isl_ch = float(10 * np.log10((Pw[~mw] ** 2).sum() / (Pw[mw] ** 2).sum()))

    # --- 모호 봉우리(전 평면 국소 최대, 주엽 밖)
    Pdb = 20 * np.log10(P / gpeak + 1e-12)

    def find_peaks(thr_db, sel):
        got = []
        for (d_i, l_i) in np.argwhere((Pdb > thr_db) & (~main) & sel):
            v = Pdb[d_i, l_i]
            nb = Pdb[max(0, d_i - 1):d_i + 2, max(0, l_i - 2):l_i + 3]
            if v >= nb.max() - 1e-9:
                got.append(dict(rb_m=float(lag_m[l_i]), fd_hz=float(fd_bins[d_i]),
                                db=float(v), tau_us=float(lag_m[l_i] / C0 * 1e6)))
        got.sort(key=lambda p: -p["db"])
        return got

    allsel = np.ones_like(main, bool)
    peaks = find_peaks(-25.0, allsel)[:12]
    # 챔버 RD 창(±60 m) 안 = 검출기 맵에 **실제로 나타나는** 봉우리 (창 안에서 따로 탐색)
    chsel = np.broadcast_to(np.abs(lag_m)[None, :] <= 60.0, main.shape)
    in_ch = find_peaks(-45.0, chsel)[:8]

    # --- 바닥 유령 셀에 새는 표적 부엽 (2D 미세격자에서 읽음)
    g = ghost_ctx[key]
    gi = int(np.argmin(np.abs(rb_grid - g["sep_m"])))
    gj = int(np.argmin(np.abs(fd_grid - g["dfd_hz"])))
    af_at_ghost = float(chi_db[gi, gj])

    # --- 물리 파일럿 반복률(PILOT_RATE_HZ) 기준 slow-time — 5G SSB 20 ms 이중고
    prf_phys = wf.pilot_rate_hz
    lam = C0 / wf.carrier_hz
    phys = dict(
        prf_model_hz=float(prf),                       # 현 벤치마크가 실제로 쓰는 프레임률
        prf_physical_hz=float(prf_phys),               # waveforms.PILOT_RATE_HZ (SSB 50 Hz 등)
        ratio=float(prf / max(prf_phys, 1e-9)),
        fd_unamb_model_hz=float(prf / 2),
        fd_unamb_phys_hz=float(prf_phys / 2),
        v_unamb_model_ms=float(prf / 2 * lam / 2),     # |fd|max = 2v/λ (바이스태틱 상한)
        v_unamb_phys_ms=float(wf.v_unambiguous_ms),    # = PRF*λ/4
        fd_res_phys_hz=float(1.0 / (M_CPI / max(prf_phys, 1e-9))),
        cpi_model_ms=float(T_cpi * 1e3),
        cpi_phys_ms=float(M_CPI / max(prf_phys, 1e-9) * 1e3),
    )
    # 표적 도플러가 물리 PRF 로 접힐 때 보이는 겉보기 도플러
    fd_t = g["fd_true"]
    if prf_phys > 0:
        ap = (fd_t + prf_phys / 2) % prf_phys - prf_phys / 2
    else:
        ap = fd_t
    phys["fd_true_hz"] = float(fd_t)
    phys["fd_aliased_phys_hz"] = float(ap)
    phys["aliased"] = bool(abs(fd_t) > prf_phys / 2)

    res = dict(
        key=key, name=name, std=wf.std, mode=wf.mode,
        carrier_hz=float(wf.carrier_hz), bw_hz=float(wf.bw_hz),
        ref_name=wf.ref_name, ref_bw_hz=float(wf.ref_bw_hz),
        Lf=int(Lf), fs_hz=float(fs), M=M_CPI, prf_hz=float(prf), T_cpi_ms=float(T_cpi * 1e3),
        # 거리
        dR_meas_m=dR3, dR_theory_m=float(dR_theory), dR_ratio=(dR3 / dR_theory if dR3 else None),
        dR_mono_theory_m=float(C0 / (2 * wf.ref_bw_hz)),
        range_null_m=float(Rnull), range_null_found=bool(rnull_found),
        range_bin_m=float(C0 / fs),
        # 도플러
        dF_meas_hz=dF3, dF_theory_hz=float(dF_theory),
        dF_ratio=(dF3 / dF_theory if dF3 else None), doppler_null_hz=float(Fnull),
        doppler_replica_db=replica_db, ref_time_duty=ref_duty,
        ref_time_spread=ref_spread,
        # 부엽
        psl_2d_db=psl_2d, isl_2d_db=isl_2d,
        psl_range_db=psl_range, isl_range_db=isl_range,
        psl_chamber_db=psl_ch, isl_chamber_db=isl_ch,
        amb_peaks=peaks, peaks_in_chamber=in_ch,
        n_peaks_in_chamber=len(in_ch),
        # 유령
        ghost=dict(g, af_db_at_ghost_cell=af_at_ghost,
                   sidelobe_over_ghost_db=float(af_at_ghost - g["amp_db"])),
        physical=phys,
    )
    figdata = dict(rb=rb_grid, fd=fd_grid, chi_db=chi_db, rcut_db=20 * np.log10(rcut / peak + 1e-12),
                   fd_fine=fd_fine, dcut_db=dcut_db, lag_m=lag_m, rline_db=rline_db, prf=prf)
    return res, figdata


# --------------------------------------------------------------------------- #
#  기하 컨텍스트 — 진짜 표적 / 바닥 유령 (파형별 반송파에 의존)
# --------------------------------------------------------------------------- #
def ghost_context(wfs):
    pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)
    mid = len(pos) // 2
    ctx = {}
    for key, _, wf in wfs:
        p = bistatic_params(TX, RX, pos[mid], vel[mid], wf.carrier_hz)
        g = floor_ghost(TX, RX, pos[mid], vel[mid], wf.carrier_hz, pol="V")
        ctx[key] = dict(rb_true_m=float(p["Rb"]), fd_true=float(p["fd"]),
                        rb_ghost_m=float(g["rb_m"]), fd_ghost=float(g["fd"]),
                        sep_m=float(g["rb_m"] - p["Rb"]),
                        dfd_hz=float(g["fd"] - p["fd"]),
                        amp_db=float(20 * np.log10(g["amp_ratio"] + 1e-30)))
    return ctx


# --------------------------------------------------------------------------- #
#  그림
# --------------------------------------------------------------------------- #
def figures(results, figs):
    import vizstyle
    vizstyle.use_korean()
    import matplotlib.pyplot as plt

    os.makedirs(FIGDIR, exist_ok=True)
    order = ["wifi", "lte", "nr"]
    modes = ["G1", "G3"]
    col = {"wifi": "#1565c0", "lte": "#00897b", "nr": "#c62828"}

    # --- Fig 1: 2D AF 지도 (3 x 2)
    fig, axes = plt.subplots(2, 3, figsize=(15.0, 7.8), constrained_layout=True)
    for r, mo in enumerate(modes):
        for c, st in enumerate(order):
            k = f"{st}_{mo}"
            R, F = results[k], figs[k]
            ax = axes[r][c]
            im = ax.pcolormesh(F["rb"], F["fd"], F["chi_db"].T, cmap="turbo",
                               vmin=-45, vmax=0, shading="auto")
            g = R["ghost"]
            ax.plot(0, 0, "o", mfc="none", mec="w", ms=11, mew=1.5)
            ax.plot(g["sep_m"], g["dfd_hz"], "x", color="w", ms=9, mew=2.0)
            ax.annotate("floor ghost cell", (g["sep_m"], g["dfd_hz"]), color="w",
                        fontsize=7.5, xytext=(6, 8), textcoords="offset points")
            ax.set_xlim(-15, 60)
            ax.set_ylim(-160, 160)
            ax.set_title(f"{R['name']} · ref={R['ref_name']} ({R['ref_bw_hz']/1e6:.1f} MHz)\n"
                         f"range -3dB = {R['dR_meas_m']:.2f} m (theory c/B = {R['dR_theory_m']:.2f} m) · "
                         f"PSL(chamber) = {R['psl_chamber_db']:.1f} dB", fontsize=8.6)
            if r == 1:
                ax.set_xlabel("Bistatic range offset  c*tau [m]")
            if c == 0:
                ax.set_ylabel("Doppler offset  f_d [Hz]")
    fig.colorbar(im, ax=axes, label="|chi| normalized [dB]", shrink=0.85)
    fig.suptitle("Detector ambiguity function |chi(tau, f_d)| of the passive reference signal\n"
                 "(CPI = 48 frames, Hann slow-time — identical to passive_process.range_doppler)",
                 fontsize=11)
    p1 = os.path.join(FIGDIR, "verify_ambiguity_af.png")
    fig.savefig(p1, dpi=130); plt.close(fig)

    # --- Fig 2: 거리 컷 (챔버 창 + 전 지연축)
    fig, axs = plt.subplots(1, 2, figsize=(14.2, 5.2), constrained_layout=True)
    for st in order:
        for mo, ls in zip(modes, ["--", "-"]):
            k = f"{st}_{mo}"
            R, F = results[k], figs[k]
            axs[0].plot(F["rb"], F["rcut_db"], ls, color=col[st], lw=1.5,
                        label=f"{R['name'].split(' ')[0]} {mo} ({R['ref_bw_hz']/1e6:.0f} MHz)")
    g = results["nr_G3"]["ghost"]
    axs[0].axvline(g["sep_m"], color="k", ls=":", lw=1.6)
    axs[0].annotate(f"floor ghost cell  +{g['sep_m']:.2f} m\nghost level {g['amp_db']:.1f} dB",
                    (g["sep_m"], g["amp_db"]), fontsize=8, va="center", ha="left",
                    xytext=(20.0, -41.0), textcoords="data",
                    bbox=dict(fc="white", ec="0.6", alpha=0.9, pad=2),
                    arrowprops=dict(arrowstyle="->", lw=1.0, color="k"))
    axs[0].axhline(g["amp_db"], color="gray", ls="-.", lw=1.0)
    axs[0].set_xlim(-20, 50); axs[0].set_ylim(-45, 2)
    axs[0].set_xlabel("Bistatic range offset  c*tau [m]")
    axs[0].set_ylabel("|chi(tau, 0)| [dB]")
    axs[0].set_title("Zero-Doppler cut — chamber window\n"
                     "(dashed = G1 idle cell, solid = G3 full load; WiFi G1 and G3 coincide exactly)",
                     fontsize=9.5)
    axs[0].legend(fontsize=7.6, ncol=2); axs[0].grid(alpha=0.3)

    # 오른쪽: 전 지연축을 |Rb| 로그축 + 좌우 포락선(max) 으로 — km 단위 모호 봉우리를 한 눈에
    for st in order:
        for mo, ls in zip(modes, ["--", "-"]):
            k = f"{st}_{mo}"
            R, F = results[k], figs[k]
            a = np.abs(F["lag_m"]); v = F["rline_db"]
            o = np.argsort(a)
            axs[1].plot(np.maximum(a[o], 1.0), v[o], ls, color=col[st], lw=0.9, alpha=0.8,
                        label=f"{R['name'].split(' ')[0]} {mo}")
    axs[1].axvspan(1.0, 60.0, color="k", alpha=0.18)
    axs[1].annotate("chamber RD window\n(|Rb| <= 60 m)", (7.0, -55), fontsize=8, ha="center")
    for k, txt in (("lte_G1", "LTE CRS comb-6\n6.66 km, -5.3 dB"),
                   ("wifi_G1", "WiFi CP\n0.96 km, -14.3 dB")):
        p = results[k]["amb_peaks"][0]
        axs[1].plot(abs(p["rb_m"]), p["db"], "v", color=col[k.split("_")[0]], ms=7)
        axs[1].annotate(txt, (abs(p["rb_m"]), p["db"]), fontsize=7.6, ha="center",
                        xytext=(0, 8), textcoords="offset points", color=col[k.split("_")[0]])
    axs[1].set_xscale("log")
    axs[1].set_xlabel("|Bistatic range offset|  |c*tau| [m]   (log; full frame, cyclic)")
    axs[1].set_ylabel("|chi(tau, 0)| [dB]")
    axs[1].set_ylim(-60, 4)
    axs[1].set_title("Full delay axis — OFDM ambiguity peaks (CP, symbol, comb)\n"
                     "every one of them sits at km scale, far outside the chamber window",
                     fontsize=9.5)
    axs[1].legend(fontsize=7.6, ncol=3, loc="lower right"); axs[1].grid(alpha=0.3, which="both")
    p2 = os.path.join(FIGDIR, "verify_ambiguity_range.png")
    fig.savefig(p2, dpi=130); plt.close(fig)

    # --- Fig 3: 도플러 컷 + 5G SSB 이중고
    fig, axs = plt.subplots(1, 2, figsize=(14.2, 5.2), constrained_layout=True)
    for st in order:
        k = f"{st}_G1"
        R, F = results[k], figs[k]
        axs[0].plot(F["fd_fine"] / R["prf_hz"], F["dcut_db"], color=col[st], lw=1.3,
                    label=f"{R['name'].split(' ')[0]} G1  PRF={R['prf_hz']:.0f} Hz  "
                          f"spread={R['ref_time_spread']:.3f}  replica={R['doppler_replica_db']:.1f} dB")
    axs[0].axvspan(-0.5, 0.5, color="k", alpha=0.10)
    axs[0].annotate("unambiguous zone\n|f_d| < PRF/2", (0.30, -8), fontsize=8, ha="left")
    axs[0].set_xlabel("Doppler  f_d / PRF   (PRF = frame rate of the tiled reference)")
    axs[0].set_ylabel("|chi(0, f_d)| [dB]")
    axs[0].set_ylim(-60, 4)
    axs[0].set_title("Zero-delay Doppler cut — replicas at f_d = k*PRF\n"
                     "pilot packed at frame start (WiFi LTF, 5G SSB) -> full 0 dB replica;\n"
                     "pilot spread over the frame (LTE CRS, l=0/4/7/11) -> replica suppressed",
                     fontsize=9.5)
    axs[0].legend(fontsize=7.4, loc="lower left"); axs[0].grid(alpha=0.3)

    # 물리 파일럿 반복률 기준 slow-time AF (SSB 20 ms 대 CRS 1 ms)
    for st in order:
        R = results[f"{st}_G1"]
        prf_p = R["physical"]["prf_physical_hz"]
        fdg = np.linspace(-160, 160, 4001)
        w = np.hanning(M_CPI); p = np.arange(M_CPI)
        Dp = np.abs((w[None, :] * np.exp(2j * np.pi * fdg[:, None] * p[None, :] / prf_p)).sum(1))
        axs[1].plot(fdg, 20 * np.log10(Dp / Dp.max() + 1e-12), color=col[st], lw=1.3,
                    label=f"{R['name'].split(' ')[0]} G1  ref={R['ref_name']}  PRF = {prf_p:.0f} Hz")
    ft = results["nr_G1"]["physical"]["fd_true_hz"]
    fa = results["nr_G1"]["physical"]["fd_aliased_phys_hz"]
    axs[1].axvline(ft, color="k", ls=":", lw=1.6)
    axs[1].annotate(f"true target f_d = {ft:+.0f} Hz  (5G @3.5 GHz, 3 m/s)\n"
                    f"-->  folds to {fa:+.0f} Hz inside |f_d| < 25 Hz",
                    (ft + 6, -12), fontsize=8, ha="left", va="center")
    axs[1].annotate("(WiFi G1 hidden under LTE G1 - both PRF = 1000 Hz)", (-170, -38.5),
                    fontsize=7.5, ha="left", color="#555555")
    axs[1].set_xlim(-175, 205)
    axs[1].set_xlabel("Doppler  f_d [Hz]")
    axs[1].set_ylabel("slow-time |D(f_d)| [dB]")
    axs[1].set_ylim(-40, 2)
    axs[1].set_title("Slow-time ambiguity at the PHYSICAL pilot rate (waveforms.PILOT_RATE_HZ)\n"
                     "5G SSB repeats every 20 ms -> replicas every 50 Hz -> the target folds",
                     fontsize=9.5)
    axs[1].legend(fontsize=8); axs[1].grid(alpha=0.3)
    p3 = os.path.join(FIGDIR, "verify_ambiguity_doppler.png")
    fig.savefig(p3, dpi=130); plt.close(fig)
    return [p1, p2, p3]


# --------------------------------------------------------------------------- #
#  자기검증 — 해석적 AF 가 **정말로** 검출기의 응답인가?
# --------------------------------------------------------------------------- #
def validate_against_detector(wfs, n_range=40):
    """잡음·DPI 없는 단위 점표적(지연 0, 도플러 0)을 make_cpi 로 만들어
    passive_process.range_doppler 에 넣고, 그 RD 맵을 해석적 chi(tau,fd) 와 대조한다.
    둘이 같아야 이 리포트의 모든 숫자가 '검출기의' 숫자다."""
    from passive_process import make_cpi, range_doppler
    rows = []
    for key, name, wf in wfs:
        rf, Lf = ref_frame_of(wf); fs = wf.fs_hz
        surv, ref_cpi = make_cpi(rf, M_CPI, fs, 0.0, 0.0, a_tgt=1.0, dpi_amp=0.0,
                                 clutter=(), abs_noise=True, noise_var=0.0)
        Rb, f_d, rd = range_doppler(surv, ref_cpi, fs, M_CPI, n_range=n_range)
        chi = np.abs(frame_af(rf, fs, np.arange(n_range) / fs, f_d)
                     * slow_time_af(M_CPI, Lf, fs, f_d)[None, :]).T
        a = 20 * np.log10(rd / rd.max() + 1e-12)
        b = 20 * np.log10(chi / chi.max() + 1e-12)
        e = np.abs(a - b)
        rows.append(dict(key=key, max_err_db_above_m45=float(e[a > -45].max()),
                         med_err_db=float(np.median(e[a > -45])), n_cells=int((a > -45).sum())))
    return rows


def main():
    wfs = waveform_set()
    ctx = ghost_context(wfs)
    val = validate_against_detector(wfs)
    print("=== [검증] 해석적 chi(tau,fd) vs 실제 검출기 range_doppler() 응답 ===")
    for v in val:
        print(f"  {v['key']:8s} -45 dB 위 {v['n_cells']:3d}셀: 최대오차 {v['max_err_db_above_m45']:.3f} dB "
              f"(중앙값 {v['med_err_db']:.4f} dB)")
    print("  → 해석적 AF = 검출기의 응답. 아래 숫자는 전부 '이 검출기의' 숫자다.\n")
    results, figdata = {}, {}
    for key, name, wf in wfs:
        r, f = analyze(key, name, wf, ctx)
        results[key] = r; figdata[key] = f
        print(f"[{name:18s}] ref={r['ref_name']:7s} {r['ref_bw_hz']/1e6:5.1f}MHz  "
              f"ΔRb: 측정 {r['dR_meas_m']:6.2f} m / 이론 {r['dR_theory_m']:6.2f} m "
              f"(x{r['dR_ratio']:.2f})   Δfd: 측정 {r['dF_meas_hz']:5.1f} Hz / 이론 "
              f"{r['dF_theory_hz']:5.1f} Hz (x{r['dF_ratio']:.2f})  "
              f"PSL {r['psl_2d_db']:6.1f} dB  ISL {r['isl_2d_db']:6.1f} dB")

    print("\n=== 도플러 모호 replica 높이 |chi(0, PRF)| — 기준신호의 '프레임 내 시간확산'이 정한다 ===")
    print("     (확산 = 에너지 rms 확산/프레임길이. 균등=0.289 가 최대, 한 점에 뭉치면 0)")
    for k, r in results.items():
        print(f"  {r['name']:18s} 시간점유 {r['ref_time_duty']*100:5.1f}%  시간확산 {r['ref_time_spread']:.3f}  →  "
              f"replica {r['doppler_replica_db']:+6.1f} dB "
              f"({'0 dB 로 살아남음(버스트형)' if r['doppler_replica_db'] > -6 else '프레임 내 위상상쇄로 억제'})")

    print("\n=== 모호 봉우리(주엽 밖 국소최대 > -25 dB) — 전 지연축 ===")
    for k, r in results.items():
        top = r["amb_peaks"][:3]
        s = ", ".join(f"{p['rb_m']/1e3:+.2f} km @ {p['fd_hz']:+.0f} Hz : {p['db']:.1f} dB" for p in top)
        print(f"  {r['name']:18s} 최강: {s or '없음'}")
    print("\n=== 그중 챔버 RD 창(±60 m) 안에 실제로 나타나는 것 ===")
    for k, r in results.items():
        ic = r["peaks_in_chamber"]
        s = ", ".join(f"{p['rb_m']:+.1f} m @ {p['fd_hz']:+.0f} Hz : {p['db']:.1f} dB" for p in ic[:4])
        print(f"  {r['name']:18s} PSL(챔버창) {r['psl_chamber_db']:6.1f} dB  ISL(챔버창) "
              f"{r['isl_chamber_db']:6.1f} dB | {s or '봉우리 없음'}")

    print("\n=== 바닥 유령 셀에 새는 표적 부엽 ===")
    for k, r in results.items():
        g = r["ghost"]
        v = "유령이 부엽에 **파묻힘**" if g["sidelobe_over_ghost_db"] > 0 else "유령이 부엽 위로 보임"
        print(f"  {r['name']:18s} 유령 +{g['sep_m']:.2f} m / {g['dfd_hz']:+.1f} Hz  "
              f"유령진폭 {g['amp_db']:+.1f} dB  vs  그 셀의 AF {g['af_db_at_ghost_cell']:+.1f} dB "
              f"→ {g['sidelobe_over_ghost_db']:+.1f} dB  {v}")

    print("\n=== 5G 이중고: 모델 PRF vs 물리 PRF ===")
    for k, r in results.items():
        p = r["physical"]
        print(f"  {r['name']:18s} 모델 PRF {p['prf_model_hz']:7.0f} Hz (v_max {p['v_unamb_model_ms']:6.1f} m/s) | "
              f"물리 PRF {p['prf_physical_hz']:6.0f} Hz (v_max {p['v_unamb_phys_ms']:5.2f} m/s) "
              f"→ x{p['ratio']:.0f} 낙관   표적 fd {p['fd_true_hz']:+.0f} Hz → "
              f"{'접힘 ' + format(p['fd_aliased_phys_hz'], '+.0f') + ' Hz' if p['aliased'] else '접힘 없음'}")

    figs = figures(results, figdata)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = dict(M_cpi=M_CPI, rb_grid_m=[RB_LO, RB_HI, RB_STEP], fd_map_hz=FD_MAP,
                detector_validation=val,
                device=str(DEV), figures=[os.path.relpath(p, os.path.join(_HERE, "..")) for p in figs],
                note="chi(tau,fd) = A(tau,fd)*D(fd) — exact (reference CPI is periodic with Lf). "
                     "Bistatic convention: Rb = c*tau, theory dRb = c/B_ref (not c/2B).")
    with open(OUT, "w") as f:
        json.dump(dict(meta=meta, waveforms=results, geometry=ctx), f,
                  ensure_ascii=False, indent=1, default=float)
    print(f"\n→ {OUT}")
    for p in figs:
        print(f"→ {p}")


if __name__ == "__main__":
    main()
