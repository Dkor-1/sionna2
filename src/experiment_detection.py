# -*- coding: utf-8 -*-
"""
experiment_detection.py — **다중 수신기(Rx 1→4) 패시브 디텍션 실험** (report12)
==================================================================================
질문: "수신기를 1개에서 4개로 늘리면 드론 탐지가 얼마나 좋아지나?" 를 **몬테카를로로 측정**한다.

■ 이 실험이 '시오나 내부에서 도는' 부분 (ISAC = C + S)
  · **Sionna RT**  : 챔버 기하·직접파(TX→감시) 경로. (렌더는 render_detection.py)
  · **SBR/Mitsuba**: 표적 RCS σ(θ) — drone_rcs_pattern (Sionna 가 쓰는 Mitsuba 광선 + 우리 PO).
  · **Sionna PHY** : 표적 에코를 파형에 먹인다 — sionna_chain.apply = cir_to_time_channel +
                     ApplyTimeChannel. (make_cpi 의 손계산 지연·도플러를 Sionna 가 대신한다.)
  · **우리 레이더 체인**(Sionna 에 없음): ECA → 거리-도플러(CAF) → CA-CFAR → **빔포밍 결합**.

■ 왜 Rx 를 늘리면 좋아지나 (측정으로 확인한다, 가정하지 않는다)
  감시 배열 N 소자(λ/2 ULA)는 표적 에코를 **소자마다 다른 위상**(조향벡터)으로,
  **잡음은 서로 독립**으로 받는다. 표적 방향으로 **코히어런트 빔포밍**(위상 정합 후 합)하면
  표적 전압은 √N 배, 잡음 전력은 그대로 → **출력 SNR 이 N 배(= +10·log10 N dB)**.
  N=1→4 이면 이론상 **+6.02 dB**. 이 실험은 그 이득이 실제로 나오는지, 그래서 Pd 곡선이
  얼마나 왼쪽으로(=더 약한 표적도 탐지) 이동하는지 **직접 잰다**.

■ report4/report10 의 교정을 강제한다
  · CFAR 명목 Pfa 는 파형별로 교정(passive_process.pfa_nominal_for) — 공정 비교.
  · 표적 없는 트라이얼로 **경험적 Pfa** 를 같이 재서 교정이 실제로 맞는지 확인.

실행:  python src/experiment_detection.py            (전체 스윕 + 그림 + 애니 프레임)
       python src/experiment_detection.py --quick    (작은 K 로 빠르게)
출력:  outputs/detection_rx_sweep.json,  outputs/figures/report12_*.png,
       outputs/anim/<name>/frame_*.png  (render_detection.py 가 GIF 로 묶는다)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                    # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")
ANIM = os.path.join(OUT, "anim")
C0 = 299792458.0
FC = 3.5e9

from experiment_x410 import X410Scenario, steering_vector             # noqa: E402
from passive_process import (ECACanceller, range_doppler, ca_cfar_2d,  # noqa: E402
                             peak_detection, pfa_nominal_for)


# --------------------------------------------------------------------------- #
#  표적 기하 — 지연 τ, 도플러 f_d, 감시배열 소자별 조향위상
# --------------------------------------------------------------------------- #
def target_aspect(scn: X410Scenario):
    """표적을 감시배열 중심에서 본 방위/고각 [deg]."""
    u = np.asarray(scn.target, float) - np.asarray(scn.surv_center, float)
    u /= np.linalg.norm(u)
    az = float(np.degrees(np.arctan2(u[1], u[0])))
    el = float(np.degrees(np.arcsin(np.clip(u[2], -1, 1))))
    return az, el


def bistatic_tau_fd(scn: X410Scenario, vel, fc=FC):
    """표적 (지연 τ[s], 도플러 f_d[Hz]) — 감시배열 중심 기준 바이스태틱."""
    tx = np.asarray(scn.tx_pos, float)
    rx = np.asarray(scn.surv_center, float)
    tgt = np.asarray(scn.target, float)
    vel = np.asarray(vel, float)
    lam = C0 / fc
    R1 = np.linalg.norm(tgt - tx)
    R2 = np.linalg.norm(rx - tgt)
    L = np.linalg.norm(rx - tx)
    u1 = (tx - tgt) / R1
    u2 = (rx - tgt) / R2
    fd = float(vel @ (u1 + u2)) / lam
    tau = float((R1 + R2 - L) / C0)
    return tau, fd, dict(R1=float(R1), R2=float(R2), L=float(L), Rb=float(R1 + R2 - L))



# --------------------------------------------------------------------------- #
#  CPI 설계 — 드론(저속)의 도플러가 0-도플러 능선 밖으로 나오게 **긴 CPI**
# --------------------------------------------------------------------------- #
#  드론은 실내에서 느리다(≈3 m/s → f_d≈64 Hz). 도플러 분해능 Δf_d = 1/T_CPI 이므로
#  T_CPI 를 ~55 ms 로 잡아야 표적이 0-도플러 가드(±1 빈) 밖 3~4 빈에 앉는다.
#  파형별 (프레임수 M, 프레임당 블록수 b) — 블록=파형 1개(주기적 tile). PRF=fs/(b·블록길이).
CPI_CFG = {
    "nr":   dict(M=112, b=1),    # 블록 61440(0.5ms) → PRF 2000Hz, T_CPI 56ms, Ns 6.88M
    "wifi": dict(M=112, b=9),    # 블록 4160(52µs)×9 → PRF 2136Hz, T_CPI 52ms, Ns 4.19M
    "lte":  dict(M=56,  b=1),    # 블록 30720(1ms) → PRF 1000Hz, T_CPI 56ms, Ns 1.72M
}
N_RANGE = 32       # RD 거리빈 (CFAR 훈련창이 성립하도록 넉넉히; ECA 탭이 이 창을 덮는다)
N_TAPS = 40        # ECA 제거 탭 — n_range 를 덮어 DPI 누설이 거리창 밖으로 안 새게
DPI_AMP = 40.0     # 직접파 누설 진폭(표적보다 수십 dB 큼)

# --------------------------------------------------------------------------- #
#  9-모드 벤치마크 — 3표준 × 3점유레벨 (사용자 지시 2026-07-16)
#  ⚠ 정직: 실제로 바뀌는 것은 '점유율'이 아니라 **패시브가 잠글 수 있는 기준신호**다.
#     WiFi: W1~W3 모두 프리앰블(VHT-LTF)이 기준 → 데이터 점유만 다르고 분해능은 사실상 불변.
#     LTE : L1=CRS(상시) → L2·L3=PRS(측위세션 필요, 기준신호 교체).
#     5G  : G1=SSB(상시, 7.2MHz, 거침) → G2·G3=NR-PRS(98MHz, 정밀, 세션 필요).
#     **헤드라인은 상시 3인방 W1·L1·G1** — 협조 없이 패시브가 실제로 얻는 것. 나머지는 낙관적 상한.
#  가정: 각 모드는 그 모드의 **송신 파형(wf.tx)** 을 기준으로 상관한다(full-waveform capture 상한).
#        (시간가변 점유는 현실성 있게 모델 불가 → 고정 점유로 단순화, 사용자 승인.)
MODES = [
    ("wifi", "G1", "W1", True), ("wifi", "G2", "W2", False), ("wifi", "G3", "W3", False),
    ("lte",  "G1", "L1", True), ("lte",  "G2", "L2", False), ("lte",  "G3", "L3", False),
    ("nr",   "G1", "G1", True), ("nr",   "G2", "G2", False), ("nr",   "G3", "G3", False),
]


# --------------------------------------------------------------------------- #
#  ① Sionna PHY 로 표적 에코 생성 (한 파형당 1회)
# --------------------------------------------------------------------------- #
def build_echo_sionna(wf, M, b, scn, sigma_m2, vel, fc=FC, verbose=True):
    """**Sionna PHY** 의 `cir_to_time_channel` 로 **지연 sinc 커널**을 얻어 표적 에코 CPI 를 만든다.
    ⚠ 정직(적대적 검증 wxrrogxwb): ApplyTimeChannel 은 **쓰지 않는다**(6.9M CPI 서 OOM → 커널만 받아
    scipy fftconvolve 로 콘볼루션). 도플러·진폭은 **후처리 위상램프**로 건다 — 고정지연·협대역에서
    시변 ApplyTimeChannel 과 **정확히 동등**함을 확인(range walk≈0.17m ≪ ΔR). 즉 Sionna 는 '지연 펄스정형'을,
    도플러는 우리가 담당한다. 프레임 = b개 파형블록. CPI = M 프레임. 반환 (y_echo, ref_cpi, meta)."""
    import sionna_chain as sc                                       # GPU (torch/sionna)
    from scipy.signal import fftconvolve
    block = wf.tx.astype(np.complex64)
    ref_cpi = np.tile(block, b * M)                                 # 주기적 송신 스트림
    Ns = ref_cpi.size
    Lf = Ns // M                                                    # 프레임 길이 = b·블록
    fs = wf.fs_hz
    tau, fd, geo = bistatic_tau_fd(scn, vel, fc)
    amp = np.sqrt(sigma_m2) * geo["L"] / (np.sqrt(4 * np.pi) * geo["R1"] * geo["R2"])
    t0 = time.time()
    # Sionna PHY: 지연 τ 의 **sinc 보간 커널**을 cir_to_time_channel 로 받는다(수백 탭·메모리 가벼움).
    #   전체 6.9M CPI 를 ApplyTimeChannel 로 한 번에 먹이면 시변채널 텐서가 20 GB+ 라 OOM →
    #   대신 Sionna 가 계산한 펄스정형 커널로 우리가 콘볼루션(fftconvolve)하고, 도플러는 위상램프로.
    h, l_min, l_max = sc.channel_taps([1.0], [tau], bandwidth=fs, n_time=1)
    kernel = np.asarray(h.detach().cpu().numpy()).reshape(-1).astype(np.complex64)  # l_tot 탭
    y_del = fftconvolve(ref_cpi, kernel)[:Ns].astype(np.complex64)  # Sionna 커널로 분수지연
    n = np.arange(Ns)
    y_echo = (amp * y_del * np.exp(1j * 2 * np.pi * fd * n / fs)).astype(np.complex64)
    if verbose:
        print(f"    [Sionna PHY] {wf.std:4s} 에코  Ns={Ns:,} (M={M},Lf={Lf}) 커널 {kernel.size}탭  "
              f"τ={tau*1e9:.1f}ns Rb={geo['Rb']:.1f}m f_d={fd:+.1f}Hz  PRF={fs/Lf:.0f}Hz "
              f"Δf_d={fs/Lf/M:.1f}Hz  ({time.time()-t0:.1f}s)")
    meta = dict(tau=tau, fd=fd, amp=float(amp), M=int(M), b=int(b), Lf=int(Lf), Ns=int(Ns),
                fs=float(fs), prf=float(fs / Lf), dfd=float(fs / Lf / M),
                sigma_m2=float(sigma_m2), **geo)
    return y_echo, ref_cpi, meta


def analytic_echo(wf, meta):
    """해석적 지연+도플러 에코 (Sionna PHY 검증 대조군)."""
    block = wf.tx.astype(np.complex64)
    ref_cpi = np.tile(block, meta["b"] * meta["M"])
    Nn = ref_cpi.size; fs = meta["fs"]
    f = np.fft.fftfreq(Nn, d=1 / fs)
    delayed = np.fft.ifft(np.fft.fft(ref_cpi) * np.exp(-1j * 2 * np.pi * f * meta["tau"]))
    n = np.arange(Nn)
    return (meta["amp"] * delayed * np.exp(1j * 2 * np.pi * meta["fd"] * n / fs)).astype(np.complex64)


def steering_for_N(N, az, el, fc=FC):
    """감시 ULA N 소자의 표적방향 조향벡터 (원거리, λ/2 간격)."""
    scn_N = X410Scenario(n_surv=N, carrier_hz=fc)
    return steering_vector(scn_N, az, el), scn_N


# --------------------------------------------------------------------------- #
#  ② 사전계산 — ECA 는 선형이라 표적·직접파의 잔차를 1회만 구한다
# --------------------------------------------------------------------------- #
class Precomputed:
    """ECA(에코)·ECA(직접파) 를 한 번만 계산해 GPU 로 올린다. 몬테카를로는 여기에 잡음만 더한다.

    코히어런트 결합의 물리(측정으로 확인, verify_combine):
      N 소자가 표적을 조향위상으로, 잡음을 독립으로 받는다 → 표적방향 정합·합 → 표적전압 √N,
      잡음전력 그대로 → **출력 SNR = N 배 (= +10·log10 N dB)**. 이것이 Rx 를 늘리는 이유.
    루프 속도를 위해 잡음의 ECA(≈항등, n_taps/Ns≪1)는 생략하고, 결합잡음은 분산 σ² 로 직접 뽑는다
    (verify_combine 이 '독립 N개 결합 == 분산 σ²' 를 실측해 확인한다)."""

    def __init__(self, y_echo, ref_cpi, wf, M, vel_meta):
        self.wf = wf; self.M = int(M); self.n_range = N_RANGE
        self.meta = vel_meta
        self.Ns = len(ref_cpi)
        can = ECACanceller(ref_cpi, n_taps=N_TAPS, ridge_rel=1e-4)   # 대역제한 기준신호 안정화(cond~1e4)
        self.ref_frame = can.ref[:self.Ns // self.M].copy()         # 한 프레임 기준(정합필터용)
        self.resid_echo = can.cancel(y_echo).astype(np.complex64)   # ECA(에코) 1회
        self.resid_dpi = can.cancel(DPI_AMP * ref_cpi).astype(np.complex64)  # ECA(직접파) 1회
        # truth 셀 = **표적 에코**의 RD 피크. 0-도플러 능선(DPI 잔차)은 제외하고 찾는다
        # (Sionna 커널 지연규약 오프셋 때문에 거리빈이 해석값과 다르므로 반드시 실측으로 잡는다).
        Rb, f_d, rd_e = range_doppler(self.resid_echo, can.ref, wf.fs_hz, M, n_range=self.n_range)
        zd = M // 2
        rd_search = rd_e.copy(); rd_search[max(0, zd - 2):zd + 3, :] = 0.0
        self.di_true, self.ri_true = [int(v) for v in np.unravel_index(int(np.argmax(rd_search)), rd_e.shape)]
        self.peak0 = float(rd_e[self.di_true, self.ri_true])        # 표적 피크 진폭
        # 그림용 무잡음 RD (에코+DPI잔차 — 0-도플러 능선까지 보이게)
        self.Rb, self.f_d, self.rd0 = range_doppler(self.resid_echo + self.resid_dpi, can.ref,
                                                    wf.fs_hz, M, n_range=self.n_range)
        # ⚠ 거리축 앵커 보정(적대적 감사): range_doppler 는 거리축을 lag·c/fs(lag0 기준)로 라벨하는데,
        #   Sionna 커널의 l_min 오프셋 때문에 표적이 옛 lag 에 앉아 **축 숫자가 물리적으로 틀렸다**
        #   (챔버 22 m 인데 그림·GIF 가 36~78 m 표시). Pd/SNR50 은 truth 셀 실측이라 옳지만 라벨만 어긋난다.
        #   → 실측 표적빈 ri_true 를 참 R_b(meta['Rb'])에 앵커시켜 축 전체를 이동한다.
        _dr = C0 / wf.fs_hz
        self.Rb = (np.arange(self.n_range) - self.ri_true) * _dr + float(vel_meta["Rb"])

    def to_gpu(self):
        import torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        self._t = dict(
            echo=torch.tensor(self.resid_echo, device=dev),
            dpi=torch.tensor(self.resid_dpi, device=dev),
            ref=torch.tensor(self.ref_frame, device=dev),
            dev=dev)
        return self


# --------------------------------------------------------------------------- #
#  ③ 단일소자 출력 SNR (x 축 눈금) — numpy 로 한 번
# --------------------------------------------------------------------------- #
def measure_single_snr(pre: Precomputed, sigma):
    """N=1 출력 SNR[dB] = 무잡음 표적피크² / 잡음셀 전력. (σ 로 정확히 스케일되므로 1회 측정)."""
    from passive_process import range_doppler as _rd
    rng = np.random.default_rng(12345)
    noise = ((rng.standard_normal(pre.Ns) + 1j * rng.standard_normal(pre.Ns))
             * (sigma / np.sqrt(2))).astype(np.complex64)
    _, _, rd_n = _rd(pre.resid_dpi + noise, np.tile(pre.ref_frame, pre.M),
                     pre.wf.fs_hz, pre.M, n_range=pre.n_range)
    ncell = float(np.median(rd_n ** 2)) + 1e-30
    return 10 * np.log10(pre.peak0 ** 2 / ncell)


# --------------------------------------------------------------------------- #
#  ④ GPU 배치 몬테카를로 — 수천 트라이얼을 한꺼번에
# --------------------------------------------------------------------------- #
def _batch_size(Ns, budget_frac=0.6):
    """예산 메모리에 맞춰 배치 크기 — GPU 를 크게 쓴다(사용자 방침)."""
    try:
        from gpu import budget_mb
        bud = budget_mb() * 1e6 * budget_frac
    except Exception:
        bud = 6e9
    per = Ns * 8 * 10                                              # surv+FFT 중간버퍼 대략 10배
    return int(max(4, min(128, bud / per)))


def gpu_montecarlo(pre: Precomputed, sv, sigma, K, seed, pfa, batch=None):
    """Pd, 경험적 Pfa (표적 유/무). torch 배치로 GPU 에서."""
    import torch
    from detection_gpu import rd_batch, cfar_batch, peak_batch
    t = pre._t; dev = t["dev"]
    N = len(sv); sqrtN = float(np.sqrt(N))
    M, nr = pre.M, pre.n_range
    batch = batch or int(os.environ.get("SIONNA2_DET_BATCH", "0")) or _batch_size(pre.Ns)
    g = torch.Generator(device=dev).manual_seed(int(seed))
    echo = t["echo"]; dpi = t["dpi"]; ref = t["ref"]
    tol_d, tol_r = 2, 2

    def _noise(b):
        return ((torch.randn(b, pre.Ns, generator=g, device=dev)
                 + 1j * torch.randn(b, pre.Ns, generator=g, device=dev))
                * (sigma / np.sqrt(2))).to(torch.complex64)

    hits = 0; done = 0
    while done < K:
        b = min(batch, K - done)
        surv = sqrtN * echo[None, :] + dpi[None, :] + _noise(b)
        rd = rd_batch(surv, ref, M, nr)
        det, _ = cfar_batch(rd, pfa=pfa)
        di, ri, val, found = peak_batch(rd, det, guard_zd=2)         # DPI 능선 ±2 가드
        hit = found & (torch.abs(di - pre.di_true) <= tol_d) & (torch.abs(ri - pre.ri_true) <= tol_r)
        hits += int(hit.sum().item()); done += b
    Pd = hits / K

    # 경험적 Pfa — 표적 없이, **0-도플러 능선 ±2 만** 제외(verify_cfar 교정 규약과 동일: 표적
    # 거리열은 제외하지 않는다). 분모는 **제외한 셀을 뺀 유효 셀 수**로 나눈다(det.numel() 아님 —
    # 이전엔 제외셀까지 세어 Pfa 가 ~0.7배 저편향됐다; 적대적 검증 wxrrogxwb 가 발견).
    Kf = max(K // 2, 200); fa = 0; ncell = 0; done = 0
    zd = M // 2
    lo, hi = max(0, zd - 2), min(M, zd + 3)
    valid_rows = M - (hi - lo)                                       # 능선 제외 후 유효 도플러행 수
    while done < Kf:
        b = min(batch, Kf - done)
        surv = dpi[None, :] + _noise(b)
        rd = rd_batch(surv, ref, M, nr)
        det, _ = cfar_batch(rd, pfa=pfa)
        det[:, lo:hi, :] = False                                    # 0-도플러 능선 ±2 만 제외
        fa += int(det.sum().item()); ncell += b * valid_rows * nr   # 유효 셀만 분모에
        done += b
    Pfa_emp = fa / max(ncell, 1)
    return dict(Pd=Pd, Pfa_emp=Pfa_emp, K=int(K))


def verify_combine(pre: Precomputed, az, el, N=4, K=64):
    """**측정으로 확인**: N 소자 독립잡음을 표적방향 결합하면 잡음전력이 √N 안 커지고 σ² 로 보존되는가.
    반환: 측정 결합잡음전력/σ² (≈1.0 이어야 → 표적 √N·잡음 σ = 출력 SNR N배)."""
    import torch
    sv, _ = steering_for_N(N, az, el)
    dev = pre._t["dev"]
    L = min(pre.Ns, 262144)                                       # 슬라이스로 충분(메모리 절약)
    svt = torch.tensor(sv.astype(np.complex64), device=dev)
    g = torch.Generator(device=dev).manual_seed(0)
    # N개 독립잡음 → conj(sv)/√N 결합 → 전력이 σ²(=1) 로 보존되는지 실측
    nz = ((torch.randn(K, N, L, generator=g, device=dev)
           + 1j * torch.randn(K, N, L, generator=g, device=dev)) / np.sqrt(2)).to(torch.complex64)
    comb = (torch.conj(svt)[None, :, None] * nz).sum(dim=1) / np.sqrt(N)
    return float(comb.abs().pow(2).mean().item())                # ≈ 1.0


# --------------------------------------------------------------------------- #
#  ⑤ 전체 스윕 — 파형 × N=1..4 × sigma 그리드
# --------------------------------------------------------------------------- #
def run_sweep(quick=False, modes=None, n_list=(1, 2, 3, 4),
              vel=(-3.0, 0.0, 0.0), pfa_target=1e-4, drone="mavic4pro"):
    from gpu import pick
    pick(verbose=True)
    os.makedirs(FIG, exist_ok=True)
    K = 200 if quick else int(os.environ.get("SIONNA2_DET_K", "2000"))
    n_snr = 9 if quick else 15
    from waveforms import wifi_80211ac, lte_downlink, nr_downlink
    from rcs_po import drone_rcs_pattern
    FAC = {"nr": nr_downlink, "wifi": wifi_80211ac, "lte": lte_downlink}
    modes = modes if modes is not None else MODES
    rd_dump = os.environ.get("SIONNA2_DET_RDDUMP", "G1,L1,W1,G3,L3,W3").split(",")
    scn = X410Scenario(carrier_hz=FC)
    az, el = target_aspect(scn)
    sigma_dbsm, _ = drone_rcs_pattern(drone, FC, np.array([abs(az)]))
    sigma_m2 = float(sigma_dbsm[0])
    print(f"■ 표적 {drone}: 방위 az={az:.1f}° el={el:.1f}°  SBR σ={10*np.log10(sigma_m2):.1f} dBsm "
          f"(Mitsuba)  |  vel={vel} m/s  |  {len(modes)}모드")

    results = {"meta": dict(K=K, vel=list(vel), az=az, el=el, drone=drone,
                            sigma_dbsm=float(10 * np.log10(sigma_m2)),
                            pfa_target=pfa_target, fc=FC, n_list=list(n_list),
                            modes=[m[2] for m in modes]),
               "modes": {}}
    arrays = {}                                                    # GIF 용 원본
    for (std, occ, code, always_on) in modes:
        wf = FAC[std](occupancy=occ)
        cfg = CPI_CFG[std]
        pfa_nom = pfa_nominal_for(std, pfa_target)
        y_echo, ref_cpi, meta = build_echo_sionna(wf, cfg["M"], cfg["b"], scn, sigma_m2, vel,
                                                  verbose=False)
        ya = analytic_echo(wf, meta)
        xc = np.abs(np.correlate(y_echo[:30000], ya[:30000], mode="same"))
        corr = float(xc.max() / (np.linalg.norm(y_echo[:30000]) * np.linalg.norm(ya[:30000]) + 1e-30))
        pre = Precomputed(y_echo, ref_cpi, wf, cfg["M"], meta).to_gpu()
        cr = verify_combine(pre, az, el, N=4)
        snr_ref = measure_single_snr(pre, 1.0)
        snr_grid = np.linspace(-6, 20, n_snr)
        sig_grid = 10 ** ((snr_ref - snr_grid) / 20.0)
        print(f"  ▶ {code} ({std.upper()} {occ}, ref={wf.ref_name} {wf.ref_bw_hz/1e6:.0f}MHz, "
              f"occ={wf.occupancy_frac*100:.0f}%, {'상시' if always_on else '세션/제어'}): "
              f"corr={corr:.3f} 결합/σ²={cr:.3f} truth=({pre.di_true},{pre.ri_true})")
        wf_res = dict(std=std, occ=occ, code=code, always_on=bool(always_on),
                      ref_name=wf.ref_name, ref_bw_mhz=wf.ref_bw_hz / 1e6,
                      occupancy=wf.occupancy_frac,
                      M=meta["M"], b=meta["b"], Ns=meta["Ns"], prf=meta["prf"], dfd=meta["dfd"],
                      corr_sionna=corr, combine_ratio=cr, range_res_m=wf.range_resolution_m,
                      v_unamb_ms=wf.v_unambiguous_ms, snr_grid=snr_grid.tolist(),
                      Rb_true=meta["Rb"], fd_true=meta["fd"], di_true=pre.di_true, ri_true=pre.ri_true,
                      pfa_nominal=pfa_nom, curves={})
        for N in n_list:
            sv, _ = steering_for_N(N, az, el)
            pds, pfas = [], []
            t0 = time.time()
            for sg in sig_grid:
                r = gpu_montecarlo(pre, sv, sg, K, seed=1000 + N, pfa=pfa_nom)
                pds.append(r["Pd"]); pfas.append(r["Pfa_emp"])
            pda = np.array(pds)
            snr50 = float(np.interp(0.5, pda, snr_grid)) if pda.max() >= 0.5 >= pda.min() else None
            wf_res["curves"][str(N)] = dict(Pd=pds, Pfa_emp=pfas, snr50=snr50)
            print(f"      N={N}: SNR50={('%.1f'%snr50) if snr50 is not None else 'NA'}dB  "
                  f"({time.time()-t0:.1f}s)")
        results["modes"][code] = wf_res
        if code in rd_dump:
            arrays[f"{code}_rd0"] = pre.rd0
            arrays[f"{code}_Rb"] = pre.Rb
            arrays[f"{code}_fd"] = pre.f_d
            _dump_example_rd(pre, az, el, snr_ref, arrays, code)

    jpath = os.path.join(OUT, "detection_rx_sweep.json")
    with open(jpath, "w") as f:
        json.dump(results, f, indent=2)
    np.savez_compressed(os.path.join(OUT, "detection_arrays.npz"), **arrays)
    print(f"\n✅ 저장: {os.path.relpath(jpath, ROOT)}  +  detection_arrays.npz ({len(arrays)} arrays)")
    make_static_figures(results)
    return results


def _dump_example_rd(pre, az, el, snr_ref, arrays, std, target_snr=8.0):
    """단일소자 SNR≈target 에서 N=1..4 의 대표 RD 맵(1장씩) — GIF·그림용."""
    import torch
    from detection_gpu import rd_batch
    sg = 10 ** ((snr_ref - target_snr) / 20.0)
    dev = pre._t["dev"]; g = torch.Generator(device=dev).manual_seed(2024)
    for N in (1, 2, 3, 4):
        noise = ((torch.randn(1, pre.Ns, generator=g, device=dev)
                  + 1j * torch.randn(1, pre.Ns, generator=g, device=dev)) * (sg / np.sqrt(2))).to(torch.complex64)
        surv = np.sqrt(N) * pre._t["echo"][None] + pre._t["dpi"][None] + noise
        rd = rd_batch(surv, pre._t["ref"], pre.M, pre.n_range)[0].cpu().numpy()
        arrays[f"{std}_rdN{N}"] = rd


# --------------------------------------------------------------------------- #
#  ⑥ 정적 그림 (영어 텍스트) — GIF 는 render_detection.py 가 만든다
# --------------------------------------------------------------------------- #
def make_static_figures(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(FIG, exist_ok=True)
    MD = results["modes"]
    codes = list(MD.keys())
    n_list = results["meta"]["n_list"]
    ncol = {1: "#c0392b", 2: "#e67e22", 3: "#2980b9", 4: "#27ae60"}
    SCOL = {"wifi": "#2980b9", "lte": "#e67e22", "nr": "#c0392b"}
    SNAME = {"wifi": "WiFi", "lte": "LTE", "nr": "5G"}
    full = [c for c in ("W3", "L3", "G3") if c in MD]                # 제어/풀 (사용자 실험)
    on = [c for c in ("W1", "L1", "G1") if c in MD]                  # 상시(기회주의 하한)

    def s50(code, N=1):
        return MD[code]["curves"][str(N)]["snr50"]

    # (A) 헤드라인 — 9모드 SNR50(N=1) 막대, 표준별 묶음, 상시 빗금
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    xs = []; labels = []
    for i, code in enumerate(codes):
        w = MD[code]; v = s50(code)
        xs.append(i)
        hatch = "//" if w["always_on"] else None
        ax.bar(i, v if v is not None else 0, color=SCOL[w["std"]], hatch=hatch,
               edgecolor="k", alpha=0.85)
        ax.text(i, (v or 0) + 0.2, f"ΔRb{w['range_res_m']:.0f}", ha="center", fontsize=7)
        labels.append(f"{code}\n{w['ref_name']}")
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("SNR for $P_d=0.5$ (single Rx) [dB]  ↓ better")
    ax.set_title("9-mode passive-detection benchmark — SNR needed to detect the drone\n"
                 "(hatched = always-on reference; the opportunistic floor)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=SCOL[s], label=SNAME[s]) for s in ("wifi", "lte", "nr")]
              + [Patch(facecolor="gray", hatch="//", label="always-on (opportunistic)")],
              fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "report12_9mode.png"), dpi=140)
    plt.close(fig)

    # (B) Rx 스윕 — 제어/풀 모드 3종 패널, N=1..4
    panel = full if full else codes[:3]
    fig, axes = plt.subplots(1, len(panel), figsize=(5.0 * len(panel), 4.3), squeeze=False)
    for ax, code in zip(axes[0], panel):
        w = MD[code]; g = np.array(w["snr_grid"])
        for N in n_list:
            ax.plot(g, w["curves"][str(N)]["Pd"], "-o", ms=3, color=ncol[N], label=f"N={N} Rx")
        ax.set_title(f"{code}  ({SNAME[w['std']]} {w['ref_name']})\nΔRb={w['range_res_m']:.1f} m (bistatic)")
        ax.set_xlabel("single-Rx output SNR [dB]"); ax.set_ylabel("$P_d$")
        ax.set_ylim(-0.03, 1.03); ax.grid(alpha=0.3); ax.axhline(0.5, ls=":", c="gray")
        ax.legend(fontsize=8, loc="lower right")
    fig.suptitle("Controlled/full modes — adding receivers shifts $P_d$ left "
                 "($+10\\log_{10}N$ dB coherent gain)", fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "report12_pd_curves.png"), dpi=140)
    plt.close(fig)

    # (C) SNR50 vs N — 대표 모드들 + 이상적
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    s5ref = None
    for code in (full + on):
        w = MD[code]
        ns = [N for N in n_list if w["curves"][str(N)]["snr50"] is not None]
        s5 = [w["curves"][str(N)]["snr50"] for N in ns]
        if s5:
            s5ref = s5
            ls = "-" if not w["always_on"] else "--"
            ax.plot(ns, s5, ls + "o", color=SCOL[w["std"]], label=f"{code} ({w['ref_name']})")
    nn = np.array(n_list, float)
    if s5ref:
        ax.plot(nn, s5ref[0] - 10 * np.log10(nn / nn[0]), "k:", lw=1.5, label="ideal $-10\\log_{10}N$")
    ax.set_xlabel("number of surveillance receivers N"); ax.set_ylabel("SNR for $P_d=0.5$ [dB]")
    ax.set_xticks(n_list); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_title("Receiver-count gain (solid=controlled/full, dashed=always-on)")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "report12_snr50_vs_n.png"), dpi=140)
    plt.close(fig)

    # (D) 경험적 Pfa — 9모드
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    for i, code in enumerate(codes):
        w = MD[code]
        allp = np.array([w["curves"][str(N)]["Pfa_emp"] for N in n_list]).ravel()
        allp = allp[allp > 0]
        ax.scatter([i] * len(allp), allp, alpha=0.5, s=16, color=SCOL[w["std"]])
    ax.axhline(results["meta"]["pfa_target"], ls="--", c="k", label="target $10^{-4}$")
    ax.set_xticks(range(len(codes))); ax.set_xticklabels(codes)
    ax.set_yscale("log"); ax.set_ylabel("empirical $P_{fa}$"); ax.grid(alpha=0.3, which="both")
    ax.legend()
    ax.set_title("Empirical $P_{fa}$ per mode — per-std nominal calibration\n"
                 "(NOT fully equalized across modes; read cross-mode SNR50 with this caveat)")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "report12_pfa.png"), dpi=140)
    plt.close(fig)
    print("  [fig] report12_9mode / pd_curves / snr50_vs_n / pfa .png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    run_sweep(quick=a.quick)
