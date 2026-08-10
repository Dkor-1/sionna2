# -*- coding: utf-8 -*-
"""
passive_two_channel_md.py — **패시브 2채널 승격**: 기준채널이 현실적이면 얼마를 잃는가
=========================================================================================

무엇이 문제였나
---------------
`src/passive_process.py` 에는 정석 사슬(ECA → CAF 거리-도플러 → CA-CFAR)이 **이미 있다.**
그런데 우리 헤드라인 검출 수치(report12 / outputs/detection_rx_sweep.json)는 그 사슬을 쓰되
**기준신호를 송신 파형 그 자체(잡음 0 · 다중경로 0)** 로 준다. 즉 «기준 안테나가 완벽하다» 는
**상한**이다. 패시브 레이더에서 기준채널은 실제로 받아서 재는 신호이고, 거기에는 잡음도
다중경로도 섞인다. 이 스크립트는 그 대가를 **잰다.**

물음: **기준채널이 현실적이면 얼마나 손해 보나?**

무엇을 재나 (세 갈래)
---------------------
E1  기준채널 팔별 출력 SINR 손실 · 검출률 · 경험적 Pfa · DPI 소거깊이
      팔 A  이상적    : 기준 = 송신 파형 그대로 (지금의 헤드라인 가정)
      팔 B  잡음 기준 : 기준 SNR ρ ∈ {40,30,20,10,0} dB      ← 단일축
      팔 C  다중경로  : 다중경로/직접파 전력비 MDR ∈ {-30..-10} dB ← 단일축
    표적은 헤드라인과 같은 **단일 도플러 점표적**(비교 가능성 유지).
E1b 같은 팔을, 표적을 **우리 마이크로도플러 원장**(hover_long, matrice4e)으로 바꿔 다시.
      → 도플러 확산·에일리어싱이 검출에 얹는 추가 손실.
E2  **마이크로도플러가 살아남는가** — RD 맵의 표적 거리빈에서 슬로타임 도플러를 꺼내
      시간-도플러 맵을 만든다(sliding sub-CPI = STFT). 플래시가 보이나?
      + ECA 0-도플러 노치의 대가(동체선이 얼마나 지워지나).

⚠ 이 스크립트는 `src/passive_process.py` 를 **읽기만** 한다 — 사슬은 그 파일 것을 그대로 쓴다.

실행:
    python benchmark/passive_two_channel_md.py --stage all
    python benchmark/passive_two_channel_md.py --stage e1 --k 48
출력:
    outputs/passive_two_channel.json  (원장 — 모든 수치)
    outputs/passive_two_channel.npz   (맵·곡선 배열)
    outputs/figures/passive_2ch_f1.{png,pdf}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from passive_process import (make_cpi, ECACanceller, range_doppler,      # noqa: E402
                             ca_cfar_2d, doppler_guard_mask,
                             pfa_nominal_for, PFA_CALIBRATION)
from waveforms import wifi_80211ac, lte_downlink, nr_downlink            # noqa: E402
from geometry import TX, RX, CENTER, SPEED, CH_CLUTTER_RATIO             # noqa: E402
from bistatic_scene import bistatic_params, CHAMBER                      # noqa: E402
import md_mapstyle as MS                                                 # noqa: E402

C0 = 299792458.0
FC = 3.5e9
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")

# --------------------------------------------------------------------------- #
#  하우스 규약을 그대로 물려받는다 (src/experiment_detection.py = report12 헤드라인)
# --------------------------------------------------------------------------- #
CPI_CFG = {                       # (프레임수 M, 프레임당 파형블록 b) — T_CPI 를 맞춘다
    "nr":   dict(M=112, b=1),     # 블록 61440(0.5ms) → PRF 2000 Hz,   T_CPI 56 ms
    "wifi": dict(M=112, b=9),     # 블록 4160(52µs)×9 → PRF 2136 Hz,   T_CPI 52 ms
    "lte":  dict(M=56,  b=1),     # 블록 30720(1ms)   → PRF 1000 Hz,   T_CPI 56 ms
}
N_RANGE = 32                      # RD 거리빈 (report12 와 동일)
N_TAPS = 40                       # ECA 탭  (n_range 를 덮어 [R3] 을 막는다)
RIDGE_REL = 1e-4                  # 대역제한 기준신호(NR G1=SSB 7.2MHz) 안정화
PFA_TARGET = 1e-4                 # **경험적** 목표 — 명목값은 pfa_nominal_for 가 준다
GUARD_WIDTH = 3                   # 0-도플러 능선 가드(Hann ±1빈 누설까지)

# 상시 기준신호 3인방 — 협조 없이 패시브가 실제로 얻는 것 (report12 헤드라인)
WAVEFORMS = [
    ("W1", "wifi", lambda: wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G1")),
    ("L1", "lte",  lambda: lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy="G1")),
    ("G1", "nr",   lambda: nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G1")),
]

# 기준채널 다중경로 — 챔버에서 실제로 잰 것에 앵커한다.
#   19.3 ns : TX→바닥→RX 여분지연 (benchmark/geometry.py, RT 실측과 0.1 dB 내 일치)
#   40/75 ns: 그보다 먼 벽·천장 왕복 (선언된 가정 — 실측 아님)
MP_DELAYS_S = (19.3e-9, 40.0e-9, 75.0e-9)

REF_SNR_DB = (40.0, 30.0, 20.0, 10.0, 0.0)      # 팔 B 단일축
MP_RATIO_DB = (-30.0, -25.0, -20.0, -15.0, -10.0)  # 팔 C 단일축
DTR_SENS_DB = (40.0, 50.0, 60.0)                # DPI/표적비 민감도(팔 B ρ=20dB 에서만)

TARGET_SINR_A_DB = 20.0          # 팔 A 출력 SINR 을 이 값으로 맞춰 σ 를 교정(파형 간 공정)

MD_LEDGER = os.path.join(OUT, "report07_hover_long.npz")
MD_META = os.path.join(OUT, "report07_hover_long.json")


# --------------------------------------------------------------------------- #
#  기하 · 링크버짓
# --------------------------------------------------------------------------- #
def scene_numbers(sigma_dbsm):
    """챔버 바이스태틱 기하 + 직접파/표적 전력비(DTR)."""
    vel = (-SPEED, 0.0, 0.0)                       # report12 헤드라인과 같은 등속 직진
    p = bistatic_params(TX, RX, CENTER, vel, FC)
    R1, R2, L = p["R1"], p["R2"], p["L"]
    sigma = 10 ** (sigma_dbsm / 10.0)
    # 직접파 P_d = PtGtGr λ²/(4πL)²   /   표적 P_t = PtGtGr λ²σ/((4π)³R1²R2²)
    dtr = 4 * np.pi * (R1 ** 2) * (R2 ** 2) / ((L ** 2) * sigma)
    return dict(vel=list(vel), R1=float(R1), R2=float(R2), L=float(L),
                Rb_m=float(p["Rb"]), tau_s=float(p["tau"]), fd_hz=float(p["fd"]),
                beta_deg=float(p["beta"]), sigma_dbsm=float(sigma_dbsm),
                dtr_db=float(10 * np.log10(dtr)),
                note=("DTR = 4π R1²R2²/(L²σ) — 감시안테나가 등방(직접파 억제 0 dB)이라 가정한 "
                      "최악값. 실제 패시브는 안테나 패턴·차폐로 수십 dB 를 깎는다."))


# --------------------------------------------------------------------------- #
#  CPI 재료 — make_cpi 를 그대로 쓰되 표적 변조만 갈아끼운다
# --------------------------------------------------------------------------- #
def build_pieces(wf, M, b, tau, dpi_amp, clutter, verbose=False):
    """make_cpi 를 **두 번** 불러 (a) 깨끗한 표적 지연복제 g, (b) 배경(DPI+클러터) 을 얻는다.

    ⭐ 왜 두 번인가 — make_cpi 의 표적항은 `a_tgt·delayed(1,τ)·exp(j2πf_d n/fs)` 로 **단일
      도플러 톤**이다. 마이크로도플러는 톤이 아니라 시간가변 복소변조 m(t) 다. 그래서
      make_cpi 를 고치지 않고(그 파일은 읽기전용), make_cpi 가 만들어 준 **자기 자신의
      지연복제 g** 에 m(t) 를 곱한다. m(t)=exp(j2πf_d t) 를 넣으면 make_cpi 원래 동작과
      **수치적으로 동일**하다(아래 verify_identity 가 실측으로 확인한다).
    """
    ref_frame = np.tile(wf.tx, b)
    ref_frame = ref_frame / np.sqrt(np.mean(np.abs(ref_frame) ** 2))     # 전력 정규화
    # (a) 깨끗한 지연복제 — 잡음·DPI·클러터 전부 끈다
    g, ref_cpi = make_cpi(ref_frame, M, wf.fs_hz, tau, 0.0, a_tgt=1.0,
                          dpi_amp=0.0, clutter=(), abs_noise=True, noise_var=0.0)
    # (b) 배경 = DPI + 정적 클러터 (잡음 0 — 잡음은 트라이얼마다 따로 뽑는다)
    bg, _ = make_cpi(ref_frame, M, wf.fs_hz, tau, 0.0, a_tgt=0.0,
                     dpi_amp=dpi_amp, clutter=clutter, abs_noise=True, noise_var=0.0)
    if verbose:
        print(f"    pieces: Ns={len(g):,}  |g|²={np.mean(np.abs(g)**2):.4f}  "
              f"|bg|²={np.mean(np.abs(bg)**2):.4e}")
    return g.astype(np.complex128), bg.astype(np.complex128), ref_cpi.astype(np.complex128)


def verify_identity(wf, M, b, tau, fd):
    """g·exp(j2πf_d t) + 배경 == make_cpi 원본 (같은 rng) 인지 실측한다."""
    ref_frame = np.tile(wf.tx, b)
    ref_frame = ref_frame / np.sqrt(np.mean(np.abs(ref_frame) ** 2))
    Ns = M * len(ref_frame)
    a, dpi = 1.0, 30.0
    ref_ok, _ = make_cpi(ref_frame, M, wf.fs_hz, tau, fd, a_tgt=a, dpi_amp=dpi,
                         clutter=CH_CLUTTER_RATIO, abs_noise=True, noise_var=0.0)
    g, bg, _ = build_pieces(wf, M, b, tau, dpi, CH_CLUTTER_RATIO)
    n = np.arange(Ns)
    mine = a * g * np.exp(2j * np.pi * fd * n / wf.fs_hz) + bg
    err = np.linalg.norm(mine - ref_ok) / (np.linalg.norm(ref_ok) + 1e-30)
    return float(err)


def md_modulation(fs, Ns, prf_led, E, fd_bulk=0.0, margin=0.25):
    """마이크로도플러 원장 E(슬로타임, prf_led) → **fast-time 복소변조 m(t)**, 평균전력 1.

    대역제한 보간(FFT zero-stuff)을 쓴다 — 선형보간은 kernel 응답이 ±5 kHz 대에서
    이미지(19.7 kHz 접힘)를 만들어 프레임 표본화에서 되접힌다.
    가장자리 순환 불연속을 피하려고 **여유(margin)를 두고 보간한 뒤 가운데를 잘라** 쓴다."""
    T = Ns / fs
    L_need = int(np.ceil(T * prf_led))
    L_ext = int(np.ceil(L_need * (1 + 2 * margin)))
    if L_ext > len(E):
        L_ext = len(E)
    i0 = (len(E) - L_ext) // 2
    seg = np.asarray(E[i0:i0 + L_ext], complex)
    seg = seg - 0.0                                     # DC(동체선) 유지 — 지우지 않는다
    Ns_ext = int(round(L_ext * fs / prf_led))
    Sp = np.fft.fft(seg)
    Z = np.zeros(Ns_ext, complex)
    h = L_ext // 2
    Z[:h + 1] = Sp[:h + 1]
    Z[Ns_ext - (L_ext - h - 1):] = Sp[h + 1:]
    m_ext = np.fft.ifft(Z) * (Ns_ext / L_ext)
    j0 = (Ns_ext - Ns) // 2
    m = m_ext[j0:j0 + Ns]
    if len(m) < Ns:                                     # 안전
        m = np.pad(m, (0, Ns - len(m)), mode="wrap")
    m = m / np.sqrt(np.mean(np.abs(m) ** 2))            # 평균전력 1 — 톤 표적과 공정 비교
    if fd_bulk:
        m = m * np.exp(2j * np.pi * fd_bulk * np.arange(Ns) / fs)
    return m.astype(np.complex128)


def delayed_copy(x, fs, tau):
    """분수지연 (make_cpi 내부 `delayed` 와 같은 주파수영역 방식)."""
    N = len(x)
    f = np.fft.fftfreq(N, d=1 / fs)
    return np.fft.ifft(np.fft.fft(x) * np.exp(-1j * 2 * np.pi * f * tau))


# --------------------------------------------------------------------------- #
#  기준채널 팔 — 여기가 이 실험의 전부다
# --------------------------------------------------------------------------- #
def make_ref_meas(ref_cpi, arm, rng, mp_copies=None):
    """송신 파형 ref_cpi 로부터 **수신된(=측정된) 기준채널** 을 만든다.

      arm = ('ideal',)                  → 지금의 헤드라인 가정
      arm = ('refsnr', rho_db)          → + 백색잡음, 기준채널 SNR = rho_db
      arm = ('mp', mdr_db)              → + 지연·감쇠 복사본 (다중경로/직접파 = mdr_db)
      arm = ('both', rho_db, mdr_db)    → 둘 다 (단일축 아님 — 참고점)
    ⚠ **감시채널의 직접파는 깨끗한 송신 파형이다** — 물리적으로 옳다. 오염되는 것은
      우리가 *재는* 기준신호이지 송신기가 보내는 신호가 아니다."""
    kind = arm[0]
    ref = ref_cpi.copy()
    p_ref = float(np.mean(np.abs(ref_cpi) ** 2))
    if kind in ("mp", "both"):
        mdr = arm[-1]
        tot = p_ref * 10 ** (mdr / 10.0)
        per = tot / len(mp_copies)
        for c in mp_copies:
            ph = np.exp(2j * np.pi * rng.random())
            ref = ref + ph * np.sqrt(per / max(float(np.mean(np.abs(c) ** 2)), 1e-30)) * c
    if kind in ("refsnr", "both"):
        rho = arm[1]
        nv = p_ref * 10 ** (-rho / 10.0)
        ref = ref + np.sqrt(nv / 2) * (rng.standard_normal(len(ref))
                                       + 1j * rng.standard_normal(len(ref)))
    return ref


def ref_conditioning(ref_cpi, n_taps=N_TAPS, ridge_rel=RIDGE_REL):
    """ECA 가 푸는 XᴴX 의 **조건수** — 기준신호 잡음이 가중치로 얼마나 증폭되는지의 척도.
    (ECACanceller 안의 행렬을 같은 식으로 다시 만들어 보기만 한다 — 사슬은 안 건드린다.)"""
    N = len(ref_cpi); n = int(n_taps)
    R = np.array([np.vdot(ref_cpi[:N - d], ref_cpi[d:]) for d in range(n)])
    idx = np.arange(n); D = idx[None, :] - idx[:, None]
    load = 1e-6 + float(ridge_rel) * abs(R[0])
    XhX = np.where(D <= 0, R[np.abs(D)], np.conj(R[np.abs(D)])) + load * np.eye(n)
    ev = np.linalg.eigvalsh(XhX)
    return dict(cond=float(ev.max() / max(ev.min(), 1e-300)),
                cond_db=float(10 * np.log10(ev.max() / max(ev.min(), 1e-300))),
                ridge_rel=float(ridge_rel), n_taps=int(n))


def arm_label(arm):
    k = arm[0]
    if k == "ideal":
        return "ideal"
    if k == "refsnr":
        return f"refSNR{arm[1]:+.0f}dB"
    if k == "mp":
        return f"MDR{arm[1]:+.0f}dB"
    if k == "eca_only":
        return f"ECAonly-noisy{arm[1]:+.0f}dB"
    if k == "caf_only":
        return f"CAFonly-noisy{arm[1]:+.0f}dB"
    return f"refSNR{arm[1]:+.0f}dB+MDR{arm[2]:+.0f}dB"


# --------------------------------------------------------------------------- #
#  한 트라이얼 — 사슬은 passive_process 것 그대로
# --------------------------------------------------------------------------- #
_W = {}          # 워커 전역 (fork 로 물려받는다)


def _chain(surv, ref_meas, wf, M, n_range, pfa_nom, ref_caf=None):
    """사슬 = passive_process 것 그대로. ref_caf 를 따로 주면 **ECA 와 정합필터가 서로 다른
    기준신호**를 쓴다 — 손실이 어느 단에서 나오는지 가르는 대조군(E1c)."""
    can = ECACanceller(ref_meas, n_taps=N_TAPS, ridge_rel=RIDGE_REL)
    resid = can.cancel(surv)
    Rb, f_d, rd = range_doppler(resid, can.ref if ref_caf is None else ref_caf,
                                wf.fs_hz, M, n_range=n_range)
    det, thr, noise = ca_cfar_2d(rd, pfa=pfa_nom)
    det = doppler_guard_mask(det, f_d, width=GUARD_WIDTH)
    return Rb, f_d, rd, det, noise


def _trial(task):
    arm, tri, target_on = task
    S = _W
    import zlib                                     # 결정적 시드 (파이썬 hash() 는 프로세스마다 다르다)
    seed = zlib.crc32(f"{arm_label(arm)}|{tri}|{int(target_on)}".encode()) ^ S.get("seed0", 0)
    rng = np.random.default_rng(seed & 0xFFFFFFFF)
    Ns = S["Ns"]
    noise = (rng.standard_normal(Ns) + 1j * rng.standard_normal(Ns)) * np.sqrt(S["nv"] / 2)
    surv = S["bg"] + noise
    if target_on:
        surv = surv + S["a_tgt"] * S["g"] * S["mod"]
    kind = arm[0]
    if kind in ("eca_only", "caf_only"):               # E1c — 손실이 어느 단에서 나오나
        dirty = make_ref_meas(S["ref_cpi"], ("refsnr", arm[1]), rng, S["mp_copies"])
        clean = S["ref_cpi"]
        ref_meas = dirty if kind == "eca_only" else clean
        ref_caf = clean if kind == "eca_only" else dirty      # ⚠ range_doppler 는 **CPI 전체**를 받는다
    else:
        ref_meas = make_ref_meas(S["ref_cpi"], arm, rng, S["mp_copies"])
        ref_caf = None
    Rb, f_d, rd, det, nz = _chain(surv, ref_meas, S["wf"], S["M"], S["n_range"],
                                  S["pfa_nom"], ref_caf=ref_caf)
    di, ri = S["di_true"], S["ri_true"]
    zd = int(np.argmin(np.abs(f_d)))
    h = GUARD_WIDTH // 2
    out = dict(arm=arm_label(arm), trial=tri, target=bool(target_on))
    if target_on:
        pk = float(rd[di, ri]) ** 2
        nzc = float(nz[di, ri]) + 1e-300
        out["sinr_db"] = 10 * np.log10(pk / nzc)
        out["peak_db"] = 10 * np.log10(pk + 1e-300)
        out["floor_db"] = 10 * np.log10(nzc)
        sub = det[max(0, di - 2):di + 3, max(0, ri - 2):ri + 3]
        out["hit"] = bool(sub.any())
        # 검출 마스크 전체에서 가장 센 셀이 표적 근처인가 (헤드라인 규약)
        masked = np.where(det, rd, 0.0)
        if masked.max() > 0:
            a, bq = np.unravel_index(int(np.argmax(masked)), masked.shape)
            out["hit_peak"] = bool(abs(a - di) <= 2 and abs(bq - ri) <= 2)
        else:
            out["hit_peak"] = False
        out["zd_ridge_db"] = 10 * np.log10(float(np.max(rd[max(0, zd - h):zd + h + 1, :]) ** 2) + 1e-300)
    else:
        lo, hi = max(0, zd - h), min(det.shape[0], zd + h + 1)
        valid = det.shape[0] - (hi - lo)
        out["n_fa"] = int(det.sum())
        out["n_cell"] = int(valid * det.shape[1])
        out["floor_db"] = 10 * np.log10(float(np.median(nz)) + 1e-300)
    return out


# --------------------------------------------------------------------------- #
#  σ 교정 — 팔 A 의 출력 SINR 을 TARGET_SINR_A_DB 로 맞춘다 (파형 간 공정 비교)
# --------------------------------------------------------------------------- #
def calibrate_sigma(S, target_db, n=2, iters=14, headroom_db=3.0):
    """잡음전력 nv 를 찾는다 — 열잡음이 바닥이면 SINR = −10log10(nv)+const 라 **한 번 재고
    바로 푼다**. DPI 잔류가 바닥을 지배하면 그 관계가 깨지므로 몇 번 더 조인다.

    ⭐⭐ **천장이 있다.** 잡음을 0 으로 줄여도 출력 SINR 은 무한히 안 올라간다 — ECA 가 못
      지운 직접파 잔류와 표적 자신의 부엽이 바닥을 만들기 때문이다. 5G 상시 기준신호(SSB,
      7.2 MHz 를 122.88 MHz 로 표본화)처럼 **기준신호가 좁으면** XᴴX 가 준특이라 ECA 가
      직접파를 못 지우고 그 천장이 낮게 내려앉는다. 그래서 먼저 천장을 재고, 목표가 천장에
      너무 가까우면 (천장 − headroom) 으로 낮춘다. 안 그러면 σ² 가 0 으로 발산한다."""
    def meas(nv):
        S["nv"] = float(nv)
        return float(np.mean([_trial((("ideal",), 900 + t, True))["sinr_db"] for t in range(n)]))

    ceiling = meas(1e-24)                                  # 잡음 없이 = 천장
    tgt = float(target_db)
    if ceiling < target_db + headroom_db:
        tgt = ceiling - headroom_db
    nv = 1e-6
    v = meas(nv)
    for _ in range(iters):
        if abs(v - tgt) < 0.2:
            break
        nv = nv * 10 ** ((v - tgt) / 10.0)
        v = meas(nv)
    S["nv"] = float(nv)
    return float(nv), float(v), float(ceiling), float(tgt)


# --------------------------------------------------------------------------- #
#  E1 / E1b — 팔별 스윕
# --------------------------------------------------------------------------- #
def run_sweep(tag, wf_key, std, wf, target_mode, arms, K, Kpfa, nproc, geom, E_led,
              prf_led, dtr_db=None, verbose=True):
    cfg = CPI_CFG[std]
    M, b = cfg["M"], cfg["b"]
    tau, fd = geom["tau_s"], geom["fd_hz"]
    dtr_db = geom["dtr_db"] if dtr_db is None else dtr_db
    a_tgt = 1.0
    dpi_amp = a_tgt * 10 ** (dtr_db / 20.0)
    t0 = time.time()
    g, bg, ref_cpi = build_pieces(wf, M, b, tau, dpi_amp, CH_CLUTTER_RATIO, verbose=verbose)
    Ns = len(g)
    n = np.arange(Ns)
    if target_mode == "tone":
        mod = np.exp(2j * np.pi * fd * n / wf.fs_hz)
    else:
        mod = md_modulation(wf.fs_hz, Ns, prf_led, E_led, fd_bulk=fd)
    mp_copies = [delayed_copy(ref_cpi, wf.fs_hz, d) for d in MP_DELAYS_S]

    _W.clear()
    _W.update(dict(wf=wf, M=M, Ns=Ns, n_range=N_RANGE, g=g, bg=bg, ref_cpi=ref_cpi,
                   mod=mod, a_tgt=a_tgt, mp_copies=mp_copies, nv=1e-6, seed0=0,
                   pfa_nom=pfa_nominal_for(std, PFA_TARGET), di_true=0, ri_true=0))

    # 진짜 표적셀 — 잡음·DPI 없는 표적만의 RD 피크에서 실측 (라벨이 아니라 실측으로)
    Rb0, f_d0, rd0 = range_doppler(a_tgt * g * mod, ref_cpi, wf.fs_hz, M, n_range=N_RANGE)
    zd0 = int(np.argmin(np.abs(f_d0)))
    di, ri = np.unravel_index(int(np.argmax(rd0)), rd0.shape)
    _W["di_true"], _W["ri_true"] = int(di), int(ri)

    # ECA 전 0-도플러 능선(무잡음) — 소거깊이의 기준
    _, f_dp, rd_pre = range_doppler(bg + a_tgt * g * mod, ref_cpi, wf.fs_hz, M, n_range=N_RANGE)
    zdp = int(np.argmin(np.abs(f_dp)))
    h = GUARD_WIDTH // 2
    ridge_pre_db = 10 * np.log10(float(np.max(rd_pre[max(0, zdp - h):zdp + h + 1, :]) ** 2) + 1e-300)

    nv, sinr_a, ceil_db, tgt_db = calibrate_sigma(_W, TARGET_SINR_A_DB)
    if verbose:
        print(f"  [{tag}/{wf_key}] Ns={Ns:,} M={M} b={b} PRF={wf.fs_hz/(len(wf.tx)*b):.1f}Hz "
              f"DTR={dtr_db:.1f}dB  천장={ceil_db:.2f}dB 목표={tgt_db:.1f}dB "
              f"σ²={nv:.3e} → 팔A SINR={sinr_a:.2f}dB  "
              f"truth=({di},{ri})  ({time.time()-t0:.1f}s 준비)", flush=True)

    tasks = [(a, t, True) for a in arms for t in range(K)]
    tasks += [(a, t, False) for a in arms for t in range(Kpfa)]
    if nproc > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(nproc) as pool:
            res = pool.map(_trial, tasks, chunksize=2)
    else:
        res = [_trial(t) for t in tasks]

    rows = []
    for a in arms:
        lab = arm_label(a)
        tgt = [r for r in res if r["arm"] == lab and r["target"]]
        fre = [r for r in res if r["arm"] == lab and not r["target"]]
        sinr = np.array([r["sinr_db"] for r in tgt])
        nfa = sum(r["n_fa"] for r in fre); ncell = sum(r["n_cell"] for r in fre)
        rows.append(dict(
            arm=lab, kind=a[0],
            axis_value=(None if a[0] == "ideal" else float(a[1])),
            sinr_db_mean=float(sinr.mean()), sinr_db_std=float(sinr.std()),
            sinr_db_p10=float(np.percentile(sinr, 10)),
            # 손실이 «표적 피크가 내려간 것» 인지 «바닥이 올라온 것» 인지 가른다
            peak_db_mean=float(np.mean([r["peak_db"] for r in tgt])),
            floor_db_mean=float(np.mean([r["floor_db"] for r in tgt])),
            pd=float(np.mean([r["hit"] for r in tgt])),
            pd_peak=float(np.mean([r["hit_peak"] for r in tgt])),
            zd_ridge_db_mean=float(np.mean([r["zd_ridge_db"] for r in tgt])),
            eca_depth_db=float(ridge_pre_db - np.mean([r["zd_ridge_db"] for r in tgt])),
            pfa_emp=(nfa / ncell if ncell else None), n_fa=int(nfa), n_cell=int(ncell),
            K=len(tgt), Kpfa=len(fre)))
    base = next(r for r in rows if r["kind"] == "ideal")["sinr_db_mean"]
    for r in rows:
        r["loss_db"] = float(base - r["sinr_db_mean"])
    return dict(tag=tag, mode=wf_key, std=std, target_model=target_mode,
                M=M, b=b, Ns=int(Ns), prf_hz=float(wf.fs_hz / (len(wf.tx) * b)),
                T_cpi_ms=float(Ns / wf.fs_hz * 1e3), fs_hz=float(wf.fs_hz),
                ref_name=wf.ref_name, ref_bw_mhz=float(wf.ref_bw_hz / 1e6),
                dRb_m=float(C0 / wf.ref_bw_hz), n_range=N_RANGE, n_taps=N_TAPS,
                dtr_db=float(dtr_db), noise_var=float(nv), sinr_ideal_db=float(sinr_a),
                sinr_ceiling_db=float(ceil_db), sinr_target_db=float(tgt_db),
                ceiling_note=("잡음 0 에서의 출력 SINR — ECA 가 못 지운 직접파 잔류와 표적 부엽이 "
                              "만드는 한계. 기준신호가 좁으면(5G SSB) 이 천장이 낮다."),
                pfa_nominal=float(_W["pfa_nom"]), pfa_target_emp=PFA_TARGET,
                truth_cell=[int(di), int(ri)], ridge_pre_db=float(ridge_pre_db),
                seconds=float(time.time() - t0), rows=rows)


# --------------------------------------------------------------------------- #
#  E2 — 마이크로도플러 생존 (sliding sub-CPI = STFT)
# --------------------------------------------------------------------------- #
def run_md_survival(std, wf, b, seconds, arms, E_led, prf_led, geom, f_flash, f_tip,
                    nper=None, sinr_target=None, nproc=1, verbose=True):
    """RD 맵의 **표적 거리빈**에서 도플러 슬라이스를 꺼내 시간축으로 쌓는다 = 시간-도플러 맵.

    조각 길이·hop 은 md_mapstyle 규약(auto_periods → 0.45 또는 0.6 블레이드 주기, hop 2)
    을 **프레임 단위로** 옮긴 것이다. ⚠ range_doppler 는 제로패딩을 하지 않으므로
    md_mapstyle 의 8배 패딩만 빠진다(주파수축 보간 — 정보량 불변)."""
    ref_frame = np.tile(wf.tx, b)
    ref_frame = ref_frame / np.sqrt(np.mean(np.abs(ref_frame) ** 2))
    Lf = len(ref_frame)
    prf = wf.fs_hz / Lf
    M_tot = int(seconds * prf)
    per = prf / f_flash
    if nper is None:
        nper = int(round(MS.auto_periods(prf, f_flash) * per))
        forced = False
    else:
        forced = True
    nper = max(4, int(nper))
    hop = MS.FLASH_HOP
    tau = geom["tau_s"]
    dpi_amp = 10 ** (geom["dtr_db"] / 20.0)

    t0 = time.time()
    g, bg, ref_cpi = build_pieces(wf, M_tot, b, tau, dpi_amp, CH_CLUTTER_RATIO)
    Ns = len(g)
    mod = md_modulation(wf.fs_hz, Ns, prf_led, E_led, fd_bulk=0.0)     # 호버 = 병진 도플러 0
    mp_copies = [delayed_copy(ref_cpi, wf.fs_hz, d) for d in MP_DELAYS_S]

    # 표적 거리빈 — 표적만의 짧은 CPI 로 실측
    seg0 = slice(0, nper * Lf)
    _, _, rd_t = range_doppler(g[seg0] * mod[seg0], ref_cpi[seg0], wf.fs_hz, nper, n_range=N_RANGE)
    ri = int(np.unravel_index(int(np.argmax(rd_t)), rd_t.shape)[1])

    # 잡음 — E1 과 같은 규약(팔 A 의 출력 SINR 을 맞춘다)
    if sinr_target is None:
        sinr_target = TARGET_SINR_A_DB
    _W.clear()
    _W.update(dict(wf=wf, M=nper, Ns=nper * Lf, n_range=N_RANGE,
                   g=g[seg0].copy(), bg=bg[seg0].copy(), ref_cpi=ref_cpi[seg0].copy(),
                   mod=mod[seg0].copy(), a_tgt=1.0,
                   mp_copies=[c[seg0].copy() for c in mp_copies], nv=1e-6,
                   pfa_nom=pfa_nominal_for(std, PFA_TARGET),
                   di_true=int(np.unravel_index(int(np.argmax(rd_t)), rd_t.shape)[0]), ri_true=ri))
    nv, sinr_a, ceil_db, tgt_db = calibrate_sigma(_W, sinr_target)

    rng = np.random.default_rng(20260810)
    noise = (rng.standard_normal(Ns) + 1j * rng.standard_normal(Ns)) * np.sqrt(nv / 2)
    surv_full = bg + g * mod + noise
    n_slot = max(1, (M_tot - nper) // hop + 1)
    if verbose:
        print(f"  [E2/{std}] PRF={prf:.1f}Hz M_tot={M_tot} nper={nper} "
              f"({nper/per:.2f} blade periods, Δf={prf/nper:.0f}Hz, Δt={nper/prf*1e3:.2f}ms) "
              f"hop={hop} slots={n_slot} Ns={Ns:,} σ²={nv:.3e} SINR_A={sinr_a:.2f}dB "
              f"({time.time()-t0:.1f}s 준비)", flush=True)

    surv_nodpi = g * mod + noise          # DPI·클러터 없는 대조군 — ECA 노치만 분리해 잰다
    maps = {}
    diag = {}
    for spec in arms:
        lab = spec["label"]
        real_arm = spec.get("ref", ("ideal",))
        use_eca = spec.get("eca", True)
        src = surv_full if spec.get("dpi", True) else surv_nodpi
        rng2 = np.random.default_rng(777)
        ref_meas = make_ref_meas(ref_cpi, real_arm, rng2, mp_copies)
        S = np.zeros((nper, n_slot))
        f_d = None
        for j in range(n_slot):
            s0 = j * hop * Lf
            s1 = s0 + nper * Lf
            sv = src[s0:s1]
            rm = ref_meas[s0:s1]
            if use_eca:
                can = ECACanceller(rm, n_taps=N_TAPS, ridge_rel=RIDGE_REL)
                sv = can.cancel(sv)
                rr = can.ref
            else:
                rr = rm
            Rb, f_d, rd = range_doppler(sv, rr, wf.fs_hz, nper, n_range=N_RANGE)
            S[:, j] = rd[:, ri]
        t_ax = (np.arange(n_slot) * hop + nper / 2) / prf
        maps[lab] = dict(S=S, f_d=f_d, t=t_ax)
        diag[lab] = md_metrics(S, f_d, t_ax, f_flash, f_tip, prf)
        diag[lab].update(ref_arm=arm_label(real_arm), eca=bool(use_eca),
                         dpi=bool(spec.get("dpi", True)))
        if verbose:
            d = diag[lab]
            print(f"      {lab:24s} flash_contrast={d['flash_contrast_db']:6.2f}dB "
                  f"flash_line={d['flash_line_db']:6.2f}dB "
                  f"body/tip={d['zero_bin_rel_tip_db']:7.2f}dB "
                  f"tipband={d['tip_band_db']:7.2f}dB", flush=True)
    meta = dict(std=std, mode=wf.mode, b=int(b), prf_hz=float(prf), M_tot=int(M_tot),
                nper=int(nper), nper_periods=float(nper / per), forced_nper=bool(forced),
                hop=int(hop), n_slot=int(n_slot), df_hz=float(prf / nper),
                dt_ms=float(nper / prf * 1e3), seconds=float(seconds),
                f_unamb_hz=float(prf / 2), f_tip_hz=float(f_tip), f_flash_hz=float(f_flash),
                range_bin=int(ri), noise_var=float(nv), sinr_ideal_db=float(sinr_a),
                sinr_ceiling_db=float(ceil_db), sinr_target_db=float(tgt_db),
                Ns=int(Ns), dtr_db=float(geom["dtr_db"]),
                pad_note="range_doppler 는 제로패딩이 없다 — md_mapstyle 의 8배 패딩만 빠진다.",
                seconds_run=float(time.time() - t0))
    return maps, diag, meta


def md_metrics(S, f_d, t, f_flash, f_tip, prf):
    """플래시가 보이나 — 정의를 코드로 못 박는다(산문 아님).

      tip_band       : 0.35·f_tip ≤ |f_d| ≤ 1.00·f_tip 대의 전력 (문헌 날개끝 띠)
      flash_contrast : 그 띠 전력(dB)의 시간축 **p95−p5** — 플래시가 또렷할수록 크다
      flash_line     : 그 띠 전력 시계열의 스펙트럼에서 **f_flash 선**이 배경 중앙값보다
                       몇 dB 솟았나 — 「빗살이 주기적인가」의 직접 측정
      body_frac      : |f_d| ≤ 1.5·Δf 대(=동체선) 전력 / 전체 전력
    ⚠ 에일리어싱이면 tip 대가 접혀 들어와 지표가 «좋아 보일» 수 있다 — 맵을 같이 봐야 한다."""
    P = S ** 2
    fa = np.abs(f_d)
    band = (fa >= 0.35 * f_tip) & (fa <= 1.00 * f_tip)
    if not band.any():
        band = fa >= 0.35 * f_tip
    tb = P[band, :].sum(axis=0) + 1e-300
    tb_db = 10 * np.log10(tb)
    contrast = float(np.percentile(tb_db, 95) - np.percentile(tb_db, 5))
    # 플래시 선: 띠 전력 시계열의 스펙트럼
    x = tb - tb.mean()
    if len(x) > 16:
        w = np.hanning(len(x))
        Sx = np.abs(np.fft.rfft(x * w)) ** 2
        fx = np.fft.rfftfreq(len(x), d=(t[1] - t[0]) if len(t) > 1 else 1.0)
        if fx[-1] >= f_flash:
            k = int(np.argmin(np.abs(fx - f_flash)))
            k = max(1, k)
            lo, hi = max(1, k - 2), min(len(Sx), k + 3)
            peak = float(Sx[lo:hi].max())
            bgm = float(np.median(Sx[1:]))
            line = 10 * np.log10(peak / (bgm + 1e-300))
        else:
            line = float("nan")
    else:
        line = float("nan")
    df = abs(f_d[1] - f_d[0]) if len(f_d) > 1 else 1.0
    body = fa <= 1.5 * df
    body_frac = float(P[body, :].sum() / (P.sum() + 1e-300))
    zbin = fa <= 0.5 * df                            # 0-도플러 **한 빈** = 동체선
    zero_rel = float(10 * np.log10((P[zbin, :].mean() + 1e-300) / (P[band, :].mean() + 1e-300)))
    return dict(flash_contrast_db=contrast, flash_line_db=float(line),
                tip_band_db=float(10 * np.log10(tb.mean() / (P.sum(axis=0).mean() + 1e-300))),
                body_frac_db=float(10 * np.log10(body_frac + 1e-300)),
                zero_bin_rel_tip_db=zero_rel, df_hz=float(df),
                total_db=float(10 * np.log10(P.sum() + 1e-300)))


# --------------------------------------------------------------------------- #
#  요약 — 「그래서 우리 기준채널은 실제로 어느 팔인가」
# --------------------------------------------------------------------------- #
def summarize(led):
    """⭐ 스윕은 ρ 를 **가정**해 훑는다. 그런데 ρ 는 자유 파라미터가 아니다 —
    같은 링크버짓 안에서 기준안테나가 받는 직접파의 SNR 은 **감시채널의 잡음으로부터 계산된다**:

        ρ_ref = (직접파 전력) / (수신기 잡음전력) = dpi_amp² / σ²     (안테나 이득 동일 가정)

    감시안테나가 조명원 쪽으로 향한 기준안테나보다 이득이 낮으면 ρ_ref 는 더 커진다
    (G_extra). 그래서 스윕 위에 **우리 형상이 실제로 앉는 자리**를 찍는다."""
    out = {}
    for blk in led.get("E1", []):
        dtr = blk["dtr_db"]; nv = blk["noise_var"]
        rho0 = dtr - 10 * np.log10(nv)                    # a_tgt=1 → dpi_amp²=10^(dtr/10)
        xs = sorted([r["axis_value"] for r in blk["rows"] if r["kind"] == "refsnr"])
        ys = [next(r["loss_db"] for r in blk["rows"]
                   if r["kind"] == "refsnr" and r["axis_value"] == x) for x in xs]
        pds = [next(r["pd"] for r in blk["rows"]
                    if r["kind"] == "refsnr" and r["axis_value"] == x) for x in xs]
        loss_at = float(np.interp(rho0, xs, ys))
        pd_at = float(np.interp(rho0, xs, pds))
        extrap = bool(rho0 > max(xs) or rho0 < min(xs))
        # ⭐ 닫힌 꼴: ρ_ref = DTR − G_proc + SINR_target  (G_proc = 사슬의 처리이득)
        g_proc = 10 * np.log10(nv) + blk["sinr_ideal_db"]
        # 손실 ≤ 3 dB 를 지키려면 기준채널 SNR 이 얼마여야 하나 (곡선을 뒤집어 읽는다)
        o = np.argsort(ys)[::-1]                       # 손실 내림차순 = ρ 오름차순
        req = float(np.interp(3.0, np.array(ys)[o], np.array(xs)[o]))
        req_clip = bool(3.0 < min(ys) or 3.0 > max(ys))
        mp = sorted([r["axis_value"] for r in blk["rows"] if r["kind"] == "mp"])
        mp_loss = [next(r["loss_db"] for r in blk["rows"]
                        if r["kind"] == "mp" and r["axis_value"] == x) for x in mp]
        out[blk["mode"]] = dict(
            rho_ref_selfconsistent_db=float(rho0),
            loss_at_selfconsistent_db=loss_at, pd_at_selfconsistent=pd_at,
            extrapolated=extrap,
            note=("ρ_ref = DTR − 10log10(σ²) — **기준안테나와 감시안테나가 똑같다**는 퇴화된 "
                  "경우의 값이다. 실제 패시브는 안테나가 둘이고 손잡이도 둘이다: "
                  "DTR 은 **감시안테나가 조명원을 얼마나 죽이나**, ρ_ref 는 **기준안테나가 "
                  "조명원을 얼마나 잘 받나**. 둘은 독립이다. 이 값은 «안테나로 아무것도 "
                  "안 했을 때» 우리가 어디에 서 있는지를 표시하는 점이지 예측이 아니다."),
            proc_gain_db=float(g_proc),
            closed_form="ρ_ref[dB] = DTR − G_proc + SINR_target — ρ 는 자유 파라미터가 아니다",
            ref_snr_needed_for_3db_loss=req, ref_snr_needed_clipped=req_clip,
            ref_antenna_gain_needed_db=float(req - rho0),
            loss_db_by_refsnr={f"{x:+.0f}": y for x, y in zip(xs, ys)},
            pd_by_refsnr={f"{x:+.0f}": y for x, y in zip(xs, pds)},
            loss_db_by_mdr={f"{x:+.0f}": y for x, y in zip(mp, mp_loss)},
            pfa_emp_by_arm={r["arm"]: r["pfa_emp"] for r in blk["rows"]},
            eca_depth_db_by_arm={r["arm"]: r["eca_depth_db"] for r in blk["rows"]},
            sinr_ideal_db=blk["sinr_ideal_db"], dtr_db=dtr, noise_var=nv)
    led["summary"] = out

    # E2 — 마이크로도플러 생존 판정
    e2 = led.get("E2", {})
    surv = {}
    if "wifi_b1" in e2:
        m = e2["wifi_b1"]["metrics"]
        base = e2.get("ledger_direct", {}).get("metrics", {})
        for lab, d in m.items():
            surv[lab] = dict(flash_contrast_db=d["flash_contrast_db"],
                             flash_line_db=d["flash_line_db"],
                             zero_bin_rel_tip_db=d["zero_bin_rel_tip_db"])
        if "noDPI_ECA" in m and "noDPI_noECA" in m:
            surv["eca_notch_cost_db"] = dict(
                value=float(m["noDPI_noECA"]["zero_bin_rel_tip_db"]
                            - m["noDPI_ECA"]["zero_bin_rel_tip_db"]),
                what=("표적만 있는 대조군에서 ECA 를 켜고 끈 차이 — 0-도플러 한 빈(동체선)이 "
                      "날개끝 띠 대비 몇 dB 내려가나. 이것이 ECA 노치의 순수한 대가다."))
        surv["ledger_direct"] = dict(flash_contrast_db=base.get("flash_contrast_db"),
                                     flash_line_db=base.get("flash_line_db"))
    if "nr_b1" in e2:
        mm = e2["nr_b1"]["meta"]
        surv["nr_alias"] = dict(
            prf_hz=mm["prf_hz"], f_unamb_hz=mm["f_unamb_hz"], f_tip_hz=mm["f_tip_hz"],
            aliased=bool(mm["f_tip_hz"] > mm["f_unamb_hz"]),
            what=("5G 상시 기준신호(SSB)의 프레임률 2 kHz 는 무모호 도플러 ±1 kHz 밖에 못 준다. "
                  "로터 끝 도플러가 그보다 크면 마이크로도플러가 접힌다."))
    led["md_survival"] = surv

    led["assumptions"] = [
        "조명원 = 상시 기준신호 3인방(WiFi 80MHz VHT-LTF · LTE 20MHz CRS · 5G 100MHz SSB). "
        "기준채널은 **full-waveform capture** 를 가정한다(수신한 송신 파형 전체).",
        "기하 = 30×20×11 m semi-anechoic 챔버, TX(4,2.5,8) RX(4,17.5,6.5) 표적(21,10,5.5), "
        "β=47.6°, R_b=22.28 m, τ=74.3 ns. 표적 속도 3 m/s → f_d=63.8 Hz (E1) / 호버 0 Hz (E2).",
        "DTR(직접파/표적 전력비) = 4π R1²R2²/(L²σ), σ=−27.58 dBsm(mavic4pro @3.5GHz, "
        "outputs/detection_rx_sweep.json). **감시안테나 지향성 0 dB** 가정이라 최악값이다.",
        "CPI 는 report12 헤드라인 규약 그대로(T_CPI≈52~56 ms, n_range=32, n_taps=40, "
        "ridge_rel=1e-4). σ² 는 팔 A 의 출력 SINR 이 목표값이 되도록 파형마다 교정한다.",
        "CFAR 명목 Pfa 는 passive_process.pfa_nominal_for(경험 1e-4 교정표) 를 쓰고, "
        "0-도플러 가드는 doppler_guard_mask(width=3).",
        "기준채널 다중경로 지연 19.3 ns 는 챔버 바닥반사 실측(geometry.py), 40·75 ns 는 "
        "**선언된 가정**이다. 위상은 트라이얼마다 무작위.",
        "마이크로도플러 원장 = outputs/report07_hover_long.npz (matrice4e, **모노스태틱** "
        "az0/el−15, fc 3.5 GHz, PRF 19.7 kHz, SITL rpm 프리셋). 이걸 바이스태틱 사슬의 표적 "
        "복소변조로 재사용한다 — 기하 근사이고, WiFi 팔에서는 반송파도 5.21 GHz 로 다르다"
        "(도플러축은 3.5 GHz 조명 기준으로 읽어야 한다; 5.21 GHz 면 1.49배 넓어진다).",
        "정적 클러터는 이 하네스에서 죽은 파라미터다(ECA 가 진폭과 무관하게 정확히 소거) — "
        "geometry.py 가 실측으로 확정한 사실이고 여기서도 그대로다.",
    ]
    led["open_problems"] = [
        "⚠ **정합필터 템플릿이 프레임 0 에 얼어 있다.** passive_process.range_doppler 는 "
        "`ref[:Lf]` 한 프레임을 M 프레임 전부에 쓴다(파형이 정확히 타일링된다는 전제). 실제 "
        "기준채널 잡음은 프레임마다 독립인데 이 모델은 한 실현을 M 번 재사용한다 — 즉 CAF 쪽 "
        "대가는 «상관된 잡음» 으로 모델된 것이다. ECA 쪽은 CPI 전체(프레임마다 독립 잡음)를 "
        "쓰므로 정확하다. 고치려면 range_doppler 를 손대야 하는데 그 파일은 읽기전용이라 "
        "이번에 안 했다. **부호도 크기도 아직 모른다.**",
        "⚠ CFAR 명목 Pfa 교정표(pfa_nominal_for)는 **이상적 기준신호** 형상에서 측정된 것이다. "
        "기준채널이 오염되면 RD 맵의 통계가 달라져 교정이 더는 성립하지 않는다 — 그래서 팔마다 "
        "경험적 Pfa 를 같이 쟀다. 팔 간 Pd 비교는 **같은 경험적 Pfa 가 아니다**(원장의 "
        "pfa_emp_by_arm 을 보고 읽어야 한다).",
        "⚠ 마이크로도플러 원장이 모노스태틱(β=0)이다. 바이스태틱 원장(report07b, β=30~120°)이 "
        "있으나 az30~az120 은 SBR 스펙트럼 바닥이 나이퀴스트까지 차 있어(±9.8 kHz @ −30 dB) "
        "생존 판정을 오염시킨다 — 그래서 쓰지 않았다. 바이스태틱 마이크로도플러의 깨끗한 원장은 "
        "**아직 없다**.",
        "⚠ ECA 는 standard(1회 최소제곱 사영)다. 문헌 표준인 sliding ECA-S 가 아니다 — "
        "저도플러 표적 보존은 ECA-S 의 장점이지 여기 것이 아니다(passive_process 스스로 밝힌 한계).",
        "⚠ 기준채널 다중경로를 **감시채널에는 넣지 않았다**. 같은 방이면 감시채널에도 다중경로가 "
        "있어야 물리적으로 일관되지만, 그러면 축이 둘이 된다(단일축 규칙). 감시채널 다중경로 = "
        "표적경유 유령은 geometry.floor_ghost 로 이미 따로 다뤄져 있다.",
        "⚠ 손실 수치는 DTR 에 강하게 의존한다. 여기 헤드라인 DTR=65.9 dB 는 **감시안테나가 "
        "등방**이라는 최악 가정이다. 실제 패시브는 안테나·차폐로 DTR 을 깎는다 — "
        "E1_dtr_sensitivity 가 그 기울기를 잰다.",
        "⚠ **5G G1(SSB) 의 SINR 천장은 부분적으로 처리 규약의 산물이다.** 7.2 MHz 기준신호를 "
        "122.88 MHz 로 표본화한 채 ECA 를 돌리면 XᴴX 가 준특이라 직접파가 안 지워진다. 실제 "
        "수신기라면 기준신호 대역으로 **여파·데시메이션** 하고 처리한다 — 그러면 천장이 "
        "올라간다. 우리 하우스 형상(report12 G1)이 그걸 안 한다는 것이 여기서 드러난 것이고, "
        "얼마나 올라가는지는 **아직 안 쟀다**.",
    ]
    return led


# --------------------------------------------------------------------------- #
#  그림 — 그림 안 글자는 전부 영어(하우스 규약), 하이퍼파라미터 주석 없음
# --------------------------------------------------------------------------- #
def build_figure(led, arr, figdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    COL = {"W1": "#1f77b4", "L1": "#d62728", "G1": "#2ca02c"}
    NAME = {"W1": "WiFi 80 MHz (VHT-LTF)", "L1": "LTE 20 MHz (CRS)", "G1": "5G 100 MHz (SSB)"}

    fig = plt.figure(figsize=(15.5, 12.6))
    gs = GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.26,
                  left=0.065, right=0.965, top=0.945, bottom=0.055)

    # --- (a) 기준채널 잡음 → 손실 --------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    for blk in led.get("E1", []):
        xs, ys, es = [], [], []
        for r in blk["rows"]:
            if r["kind"] == "refsnr":
                xs.append(r["axis_value"]); ys.append(r["loss_db"]); es.append(r["sinr_db_std"])
        o = np.argsort(xs)
        ax.errorbar(np.array(xs)[o], np.array(ys)[o], yerr=np.array(es)[o], marker="o",
                    color=COL[blk["mode"]], label=NAME[blk["mode"]], lw=1.8, ms=5, capsize=3)
    ax.set_xlabel("Reference-channel SNR  [dB]")
    ax.set_ylabel("Output SINR loss vs ideal reference  [dB]")
    ax.set_title("(a)  Noisy reference channel", loc="left", fontsize=11, fontweight="bold")
    ax.invert_xaxis(); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper left")

    # --- (b) 기준채널 다중경로 → 손실 ----------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    for blk in led.get("E1", []):
        xs, ys, es = [], [], []
        for r in blk["rows"]:
            if r["kind"] == "mp":
                xs.append(r["axis_value"]); ys.append(r["loss_db"]); es.append(r["sinr_db_std"])
        o = np.argsort(xs)
        ax.errorbar(np.array(xs)[o], np.array(ys)[o], yerr=np.array(es)[o], marker="s",
                    color=COL[blk["mode"]], label=NAME[blk["mode"]], lw=1.8, ms=5, capsize=3)
    ax.set_xlabel("Multipath-to-direct power ratio in reference  [dB]")
    ax.set_ylabel("Output SINR loss vs ideal reference  [dB]")
    ax.set_title("(b)  Multipath-contaminated reference", loc="left", fontsize=11,
                 fontweight="bold")
    ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper left")

    # --- (c) 기전: ECA 소거깊이 ----------------------------------------------
    ax = fig.add_subplot(gs[0, 2])
    for blk in led.get("E1", []):
        xs, ys = [], []
        for r in blk["rows"]:
            if r["kind"] == "refsnr":
                xs.append(r["axis_value"]); ys.append(r["eca_depth_db"])
        o = np.argsort(xs)
        ax.plot(np.array(xs)[o], np.array(ys)[o], marker="o", color=COL[blk["mode"]],
                label=NAME[blk["mode"]], lw=1.8, ms=5)
        ideal = next(r for r in blk["rows"] if r["kind"] == "ideal")["eca_depth_db"]
        ax.axhline(ideal, color=COL[blk["mode"]], ls=":", lw=1.2, alpha=0.7)
    ax.set_xlabel("Reference-channel SNR  [dB]")
    ax.set_ylabel("Direct-path cancellation depth  [dB]")
    ax.set_title("(c)  Why it costs: ECA cannot cancel what it mismeasures",
                 loc="left", fontsize=11, fontweight="bold")
    ax.invert_xaxis(); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower left")

    # --- (d)~(i) 마이크로도플러 맵 -------------------------------------------
    e2 = led.get("E2", {})
    f_tip = float(led["md_ledger"]["f_tip_hz"])
    panels = []
    if "e2_ledger__S" in arr:
        panels.append(("e2_ledger", "(d)  Ledger STFT (no passive chain) — upper bound",
                       float(led["md_ledger"]["prf_hz"])))
    wmeta = e2.get("wifi_b1", {}).get("meta", {})
    order = [("ideal", "(e)  Passive chain, ideal reference"),
             ("refSNR+10dB", "(f)  Passive chain, reference SNR 10 dB"),
             ("MDR-20dB", "(g)  Passive chain, multipath reference -20 dB"),
             ("noDPI_noECA", "(h)  Target only, ECA off — the body line ECA removes")]
    for key, ttl in order:
        if f"e2_wifi__{key}__S" in arr:
            panels.append((f"e2_wifi__{key}", ttl, wmeta.get("prf_hz", 1.0)))
    nmeta = e2.get("nr_b1", {}).get("meta", {})
    if "e2_nr__ideal__S" in arr:
        panels.append(("e2_nr__ideal",
                       "(i)  5G frame rate 2 kHz — micro-Doppler aliases",
                       nmeta.get("prf_hz", 1.0)))

    slots = [gs[1, 0], gs[1, 1], gs[1, 2], gs[2, 0], gs[2, 1], gs[2, 2]]
    # ⭐ WiFi 사슬 패널들은 **공통 기준**으로 정규화한다 — 패널마다 자기 최댓값으로 맞추면
    #    ECA 노치가 그림에서 사라진다(각 패널이 스스로를 0 dB 로 끌어올리므로).
    wref = max([float(arr[f"{k}__S"].max()) for k, _, _ in panels if k.startswith("e2_wifi")]
               or [1.0])
    mesh = None
    for k, (key, ttl, prf) in enumerate(panels[:6]):
        ax = fig.add_subplot(slots[k])
        S = arr[f"{key}__S"]; f = arr[f"{key}__f"]; t = arr[f"{key}__t"]
        mesh = MS.draw(ax, t, f, S, f_tip, ref=(wref if key.startswith("e2_wifi") else None))
        if key.startswith("e2_nr"):
            ax.set_ylim(-prf / 2, prf / 2)
        ax.set_title(ttl, loc="left", fontsize=10, fontweight="bold")
        ax.set_xlabel("Time  [ms]")
        ax.set_ylabel("Doppler  [Hz]")
    if mesh is not None:
        cb = fig.colorbar(mesh, ax=fig.axes[3:], fraction=0.014, pad=0.012)
        cb.set_label("Relative power  [dB]")

    fig.suptitle("Passive radar with a real reference channel — what the two-channel "
                 "promotion costs", fontsize=13.5, fontweight="bold")
    for ext in ("png", "pdf"):
        p = os.path.join(figdir, f"passive_2ch_f1.{ext}")
        fig.savefig(p, dpi=170 if ext == "png" else None, bbox_inches="tight")
        print("  그림:", p, f"{os.path.getsize(p)/1e6:.2f} MB", flush=True)
    plt.close(fig)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["all", "e1", "e1b", "e1c", "e2", "fig", "summary"])
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--kpfa", type=int, default=128)
    ap.add_argument("--kmd", type=int, default=16)
    ap.add_argument("--nproc", type=int, default=24)
    ap.add_argument("--seconds", type=float, default=0.20)
    ap.add_argument("--sigma-dbsm", type=float, default=-27.5779568443798)
    ap.add_argument("--only", default="", help="W1|L1|G1 — 한 파형만 다시 돌려 원장에 덮어쓴다")
    args = ap.parse_args()
    wf_list = [w for w in WAVEFORMS if (not args.only or w[0] == args.only)]

    def _merge(key, rows):
        """--only 로 한 파형만 다시 돌렸을 때 원장의 그 항목만 갈아끼운다."""
        old = {r["mode"]: r for r in led.get(key, [])}
        for r in rows:
            old[r["mode"]] = r
        led[key] = [old[k] for k in ("W1", "L1", "G1") if k in old]

    os.makedirs(FIG, exist_ok=True)
    jpath = os.path.join(OUT, "passive_two_channel.json")
    npath = os.path.join(OUT, "passive_two_channel.npz")
    led = json.load(open(jpath, encoding="utf-8")) if os.path.exists(jpath) else {}
    arr = dict(np.load(npath, allow_pickle=True)) if os.path.exists(npath) else {}

    geom = scene_numbers(args.sigma_dbsm)
    d = np.load(MD_LEDGER)
    E_led = d["E"]
    mmeta = json.load(open(MD_META, encoding="utf-8"))["_meta"]
    prf_led = float(mmeta["prf_hz"])
    f_flash = float(mmeta["f_flash_hz"])
    f_tip = float(mmeta["f_tip_hz"])

    led.setdefault("_meta", {}).update(dict(
        generated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        script="benchmark/passive_two_channel_md.py",
        question="기준채널이 현실적이면(잡음·다중경로) 패시브 검출은 얼마를 잃는가",
        chain="src/passive_process.py — make_cpi · ECACanceller · range_doppler · ca_cfar_2d "
              "(읽기전용, 재구현 없음)",
        host=os.uname().nodename))
    led["geometry"] = geom
    led["md_ledger"] = dict(path="outputs/report07_hover_long.npz", **mmeta)
    led["config"] = dict(
        cpi_cfg={k: dict(v) for k, v in CPI_CFG.items()}, n_range=N_RANGE, n_taps=N_TAPS,
        ridge_rel=RIDGE_REL, pfa_target_emp=PFA_TARGET, guard_width=GUARD_WIDTH,
        mp_delays_ns=[x * 1e9 for x in MP_DELAYS_S],
        ref_snr_db=list(REF_SNR_DB), mp_ratio_db=list(MP_RATIO_DB),
        target_sinr_ideal_db=TARGET_SINR_A_DB,
        clutter_ratio=[[float(a), float(b)] for a, b in CH_CLUTTER_RATIO],
        pfa_calibration_source=PFA_CALIBRATION.get("_source"))

    arms_full = ([("ideal",)] + [("refsnr", r) for r in REF_SNR_DB]
                 + [("mp", m) for m in MP_RATIO_DB] + [("both", 20.0, -20.0)])
    arms_md = [("ideal",), ("refsnr", 20.0), ("refsnr", 10.0), ("mp", -20.0)]

    if args.stage in ("all", "e1"):
        print("== E1 — 단일 도플러 점표적 (헤드라인과 같은 표적모델) ==", flush=True)
        led["identity_check"] = {}
        out = []
        for key, std, mk in wf_list:
            wf = mk()
            cfg = CPI_CFG[std]
            err = verify_identity(wf, 4, cfg["b"], geom["tau_s"], geom["fd_hz"])
            led["identity_check"][key] = dict(rel_err=err, note=(
                "make_cpi 원본 == (make_cpi 지연복제)×exp(j2πf_d t) + (make_cpi 배경). "
                "상대오차가 0 이면 표적변조 갈아끼우기가 make_cpi 를 안 바꾼 것이다."))
            print(f"  identity {key}: rel_err={err:.3e}", flush=True)
            out.append(run_sweep("E1", key, std, wf, "tone", arms_full,
                                 args.k, args.kpfa, args.nproc, geom, E_led, prf_led))
        _merge("E1", out)
        # DTR 민감도 (팔 B ρ=20 dB) — 단일축
        sens = []
        for key, std, mk in wf_list:
            wf = mk()
            for dtr in DTR_SENS_DB:
                r = run_sweep(f"E1-DTR{dtr:.0f}", key, std, wf, "tone",
                              [("ideal",), ("refsnr", 20.0)], max(12, args.k // 3),
                              max(24, args.kpfa // 4), args.nproc, geom, E_led, prf_led,
                              dtr_db=dtr, verbose=False)
                sens.append(r)
                print(f"  DTR sens {key} {dtr:.0f}dB: loss(ρ=20dB)="
                      f"{r['rows'][1]['loss_db']:.2f}dB", flush=True)
        led.setdefault("E1_dtr_sensitivity", [])
        keep = [x for x in led["E1_dtr_sensitivity"]
                if x["mode"] not in {r["mode"] for r in sens}]
        led["E1_dtr_sensitivity"] = keep + sens
        json.dump(led, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if args.stage in ("all", "e1c"):
        print("== E1c — 손실이 어느 단에서 나오나 (ECA 만 오염 vs 정합필터만 오염) ==", flush=True)
        out = []
        for key, std, mk in wf_list:
            wf = mk()
            arms = [("ideal",)]
            for rho in (20.0, 10.0):
                arms += [("refsnr", rho), ("eca_only", rho), ("caf_only", rho)]
            r = run_sweep("E1c", key, std, wf, "tone", arms, 16, 32,
                          args.nproc, geom, E_led, prf_led)
            r["ref_conditioning"] = ref_conditioning(_W["ref_cpi"])
            print(f"    {key} ref XᴴX cond = {r['ref_conditioning']['cond_db']:.1f} dB "
                  f"(ref_bw {wf.ref_bw_hz/1e6:.1f} MHz / fs {wf.fs_hz/1e6:.1f} MHz)", flush=True)
            out.append(r)
            for row in r["rows"]:
                print(f"    {key} {row['arm']:20s} loss={row['loss_db']:7.2f}dB "
                      f"Pd={row['pd']:.2f}", flush=True)
        _merge("E1c", out)
        json.dump(led, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if args.stage in ("all", "e1b"):
        print("== E1b — 표적을 마이크로도플러 원장으로 교체 ==", flush=True)
        out = []
        for key, std, mk in wf_list:
            wf = mk()
            out.append(run_sweep("E1b", key, std, wf, "md", arms_md,
                                 args.kmd, args.kmd * 2, args.nproc, geom, E_led, prf_led))
        _merge("E1b", out)
        json.dump(led, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if args.stage in ("all", "e2"):
        print("== E2 — 마이크로도플러 생존 ==", flush=True)
        e2 = {}
        # (1) WiFi b=1 — 슬로타임 PRF 가 유일하게 로터 도플러를 담는다
        wf = wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G1")
        arms = [dict(label="ideal", ref=("ideal",)),
                dict(label="refSNR+20dB", ref=("refsnr", 20.0)),
                dict(label="refSNR+10dB", ref=("refsnr", 10.0)),
                dict(label="MDR-20dB", ref=("mp", -20.0)),
                dict(label="noECA", ref=("ideal",), eca=False),
                # ECA 0-도플러 노치만 분리하는 대조군 — DPI·클러터를 끄고 ECA 만 켠다/끈다
                dict(label="noDPI_ECA", ref=("ideal",), dpi=False, eca=True),
                dict(label="noDPI_noECA", ref=("ideal",), dpi=False, eca=False)]
        maps, diag, meta = run_md_survival("wifi", wf, 1, args.seconds, arms, E_led,
                                           prf_led, geom, f_flash, f_tip, nproc=args.nproc)
        e2["wifi_b1"] = dict(meta=meta, metrics=diag)
        for k, v in maps.items():
            arr[f"e2_wifi__{k}__S"] = v["S"]
            arr[f"e2_wifi__{k}__f"] = v["f_d"]
            arr[f"e2_wifi__{k}__t"] = v["t"]
        # (2) NR b=1 — 상시 5G 기준신호의 프레임률로는 무엇이 되나
        wfn = nr_downlink(bw_hz=100e6, scs_hz=30e3, carrier_hz=3.5e9, occupancy="G1")
        mapsn, diagn, metan = run_md_survival("nr", wfn, 1, args.seconds,
                                              [dict(label="ideal", ref=("ideal",))],
                                              E_led, prf_led, geom, f_flash, f_tip,
                                              nper=32, nproc=args.nproc)
        e2["nr_b1"] = dict(meta=metan, metrics=diagn)
        for k, v in mapsn.items():
            arr[f"e2_nr__{k}__S"] = v["S"]
            arr[f"e2_nr__{k}__f"] = v["f_d"]
            arr[f"e2_nr__{k}__t"] = v["t"]
        # (3) 원장 직접 STFT — 사슬을 안 탄 상한
        f0, t0_, S0, nper0 = MS.flash_spec(E_led[:int(args.seconds * prf_led)], prf_led,
                                           f_flash, periods=MS.auto_periods(prf_led, f_flash))
        arr["e2_ledger__S"] = S0
        arr["e2_ledger__f"] = f0
        arr["e2_ledger__t"] = t0_
        e2["ledger_direct"] = dict(nper=int(nper0), prf_hz=prf_led,
                                   metrics=md_metrics(S0, f0, t0_, f_flash, f_tip, prf_led),
                                   note="사슬을 안 탄 원장 자체의 STFT — 생존 판정의 상한")
        led["E2"] = e2
        json.dump(led, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        np.savez_compressed(npath, **arr)

    if args.stage in ("all", "summary", "fig"):
        led = summarize(led)
        for k, v in led.get("summary", {}).items():
            print(f"  [{k}] ρ_ref(자기일관)={v['rho_ref_selfconsistent_db']:.1f}dB → "
                  f"손실 {v['loss_at_selfconsistent_db']:.2f}dB  Pd {v['pd_at_selfconsistent']:.2f}"
                  f"{'  (외삽)' if v['extrapolated'] else ''}", flush=True)

    if args.stage in ("all", "fig"):
        build_figure(led, arr, FIG)

    json.dump(led, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("저장:", jpath, flush=True)


if __name__ == "__main__":
    main()
