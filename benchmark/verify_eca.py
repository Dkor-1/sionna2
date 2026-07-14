# -*- coding: utf-8 -*-
"""
verify_eca.py — [E2] ECA(직접파 제거) 교정 검증
================================================================================
질문: **"ECA 가 직접파를 얼마나 지우는가, 그리고 이론과 맞는가?"**

벤치마크(Pd/추적)를 믿으려면 먼저 검출기 앞단이 교정돼 있어야 한다. ECA 는 그 앞단의
전부다 — DPI 를 못 지우면 아무것도 안 보이고, **너무 잘 지우면 표적까지 지운다.**

핵심 사실 하나만 알면 전부 따라온다:
    ECACanceller.cancel(s) = s − X(XᴴX)⁻¹Xᴴ s = (I − P) s
    X = [ref, ref(-1), …, ref(-(n_taps-1))]  ← **기준신호의 정수지연 복제** n_taps 개
  즉 ECA 는 **s 에 대해 선형인 사영 연산자**다(가중치는 ref 에만 의존). 그러면:
    · 기준신호의 지연복제의 선형결합(= 정적 클러터)은 span(X) 안 → **진폭 무관 정확히 0**
    · span(X) 밖의 것(도플러 有, 데이터 성분, 양자화잡음)은 **못 지운다**
    · 표적도 도플러가 작으면 span(X) 에 가까워진다 → **지워진다** ← [4] 가 이 실험의 핵심

섹션:
  [1] 상쇄 깊이 vs 탭 수      — DPI(+RT 실측 잔향) 만, 표적·잡음 없이. n_taps 1→96 스윕.
  [2] DNR 30~90 dB 스윕       — float64 ECA 는 완벽하다. **얼마나 비현실적인가**를 ADC 양자화로 정량화.
  [3] 파일럿 기준 vs 전체송신 — ECA 기저=wf.ref(파일럿), DPI=wf.tx(파일럿+데이터) → 데이터 잔류.
  [4] ★ 표적 손실 vs 도플러  — 최소 검출가능 도플러 = **저속 드론 탐지의 근본 한계**.
  [5] 정적 클러터 = 죽은 파라미터 — 부분공간 사영으로 '왜' 그런지.

실행:  ~/.venvs/py312/bin/python benchmark/verify_eca.py     (numpy 전용, GPU 불필요)
출력:  outputs/verify_eca.json  +  outputs/figures/verify_eca.png
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from waveforms import nr_downlink, lte_downlink, wifi_80211ac              # noqa: E402
from passive_process import make_cpi, ECACanceller, range_doppler, ca_cfar_2d  # noqa: E402
from bistatic_scene import bistatic_params, C0                             # noqa: E402
from link_budget import LinkBudget, link_terms                             # noqa: E402
from channel import AnalyticChannel, rt_chamber_clutter                    # noqa: E402
from scenarios import radial                                               # noqa: E402
from geometry import (TX, RX, CENTER, CH_CLUTTER_RATIO, SPEED, SPAN,       # noqa: E402
                      chamber_window)
from run_min_cell import run_cell, EIRP_DBM, frame_len                     # noqa: E402

OUT_JSON = os.path.join(_ROOT, "outputs", "verify_eca.json")
OUT_FIG = os.path.join(_ROOT, "outputs", "figures", "verify_eca.png")
DRONE = "mavic4pro"
M_DEF = 48                       # run_min_cell 과 동일한 CPI 프레임 수


# --------------------------------------------------------------------------- #
#  공통 준비 — run_min_cell.run_cell 과 **완전히 같은** 정규화/창 설정을 재현한다.
#  (여기서 잰 숫자가 벤치마크에 그대로 적용되려면 동작점이 같아야 한다.)
# --------------------------------------------------------------------------- #
def waveforms(occ="G3"):
    return [("5G NR 100MHz", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy=occ)),
            ("WiFi 80MHz",   wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy=occ)),
            ("LTE 20MHz",    lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy=occ))]


class Setup:
    """한 파형의 동작점: 프레임(파일럿/전체), 링크텀, 기하, RD 창."""

    def __init__(self, wf, M=M_DEF, use_rt_clutter=True):
        self.wf = wf
        self.M = M
        self.fs = wf.fs_hz
        pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)
        mid = len(pos) // 2
        self.pos, self.vel = pos[mid], vel[mid]
        cl = rt_chamber_clutter(wf.carrier_hz) if use_rt_clutter else ()
        self.clutter_ratio = cl or CH_CLUTTER_RATIO
        self.clutter_is_rt = bool(cl)
        ch = AnalyticChannel(clutter=self.clutter_ratio)
        self.st = ch.state(TX, RX, self.pos, self.vel, wf.carrier_hz, DRONE)
        lb = LinkBudget(eirp_dbm=EIRP_DBM)
        self.lt = link_terms(lb, self.st.lam, self.st.sigma_m2,
                             self.st.R1, self.st.R2, self.st.L, wf.bw_hz)

        # run_cell 과 동일: tx 의 rms 로 정규화, 잡음대역 보정 √(B/fs)
        txp = np.sqrt(np.mean(np.abs(wf.tx) ** 2) + 1e-30)
        ref_f = wf.ref.astype(complex) / txp
        tx_f = wf.tx.astype(complex) / txp
        Lf = frame_len(wf)
        if Lf > len(tx_f):                        # WiFi 듀티: 패킷 뒤 무음
            pad = np.zeros(Lf - len(tx_f), complex)
            ref_f = np.concatenate([ref_f, pad])
            tx_f = np.concatenate([tx_f, pad])
        self.ref_frame, self.tx_frame, self.Lf = ref_f, tx_f, Lf
        self.bw_corr = float(np.sqrt(wf.bw_hz / self.fs))
        self.dpi = self.lt["dpi_amp"] * self.bw_corr
        self.a_tgt = self.lt["a_tgt"] * self.bw_corr
        self.clutter_abs = tuple((dt, self.dpi * r) for dt, r in self.clutter_ratio)
        self.n_range, self.n_taps = chamber_window(wf)
        self.ref_cpi = np.tile(ref_f, M)
        self.N = len(self.ref_cpi)
        self.true_Rb = self.st.tau * C0
        self.true_fd = self.st.fd
        self.prf = self.fs / self.Lf
        self.T_cpi = M * self.Lf / self.fs        # 코히어런트 적분시간
        self.dfd = 1.0 / self.T_cpi               # 도플러 분해능 = PRF/M
        # 파일럿 에너지 비율(=ECA 가 원리적으로 지울 수 있는 DPI 의 몫)
        self.ref_frac_db = float(10 * np.log10(
            (np.mean(np.abs(ref_f) ** 2) + 1e-30) / (np.mean(np.abs(tx_f) ** 2) + 1e-30)))
        # 도플러 ↔ 속도 환산(현 기하의 radial 시나리오): fd = k · v
        p = bistatic_params(TX, RX, self.pos, self.vel, wf.carrier_hz)
        self.hz_per_ms = abs(p["fd"]) / SPEED     # [Hz / (m/s)]

    def cpi(self, frame, tau=0.0, fd=0.0, a=0.0, dpi=0.0, clutter=()):
        s, _ = make_cpi(frame, self.M, self.fs, tau, fd, a_tgt=a, dpi_amp=dpi,
                        clutter=clutter, abs_noise=True, noise_var=0.0)
        return s


def pw(x):
    return float(np.mean(np.abs(x) ** 2))


def db(x):
    return float(10 * np.log10(max(x, 1e-300)))


# --------------------------------------------------------------------------- #
#  [1] 상쇄 깊이 vs 탭 수 — 표적·잡음 없이 DPI(+정적 잔향)만
# --------------------------------------------------------------------------- #
TAPS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96)


def sec1_depth_vs_taps(setups):
    """이론: ECA 기저는 **정수지연** 복제 n_taps 개. 잔향의 지연확산을 덮으면 상쇄가 완성된다.
    두 구성으로 나눠 원인을 분리한다:
      (a) DPI 만(0 지연) — 기저에 정확히 들어있다 → 탭 1개로도 float64 한계까지.
      (b) DPI + RT 실측 잔향(분수지연 탭들) — 탭이 지연확산을 덮어야 한다."""
    out = []
    for name, S in setups:
        dmax = max(dt for dt, _ in S.clutter_abs)
        spread_smp = dmax * S.fs
        dpi_only = S.cpi(S.ref_frame, dpi=S.dpi)
        dpi_cl = S.cpi(S.ref_frame, dpi=S.dpi, clutter=S.clutter_abs)
        rows = []
        for nt in TAPS:
            c = ECACanceller(S.ref_cpi, nt)
            r_a, r_b = c.cancel(dpi_only), c.cancel(dpi_cl)
            # 시작 과도(CPI 첫 nt+지연확산 샘플)는 인과 FIR 이 원리적으로 못 맞춘다
            #   (make_cpi 의 분수지연은 주파수영역 = **순환** 지연이라 CPI 머리에 wrap 성분이 있다).
            #   그 구간을 뺀 '정상상태' 깊이도 같이 잰다 — 어느 쪽이 한계인지 정직하게 가른다.
            g = int(nt + np.ceil(spread_smp) + 2)
            rows.append(dict(
                n_taps=nt,
                depth_dpi_db=db(pw(dpi_only) / max(pw(r_a), 1e-300)),
                depth_full_db=db(pw(dpi_cl) / max(pw(r_b), 1e-300)),
                depth_full_steady_db=db(pw(dpi_cl[g:]) / max(pw(r_b[g:]), 1e-300)),
            ))
        out.append(dict(name=name, fs_mhz=S.fs / 1e6,
                        smp_ns=1e9 / S.fs,
                        clutter_src=("RT" if S.clutter_is_rt else "assumed"),
                        n_clutter=len(S.clutter_abs),
                        max_delay_ns=dmax * 1e9,
                        spread_samples=spread_smp,
                        taps_used_in_bench=S.n_taps,
                        dnr_db=S.lt["dnr_db"],
                        rows=rows))
    return out


# --------------------------------------------------------------------------- #
#  [2] DNR 스윕 — float64 ECA 의 '완벽함'과, ADC 유한 동적범위가 만드는 진짜 바닥
# --------------------------------------------------------------------------- #
DNRS = (30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0)
ADC_BITS = (12, 14, 16)


def _quantize(x, bits, headroom_sigma=3.0):
    """복소 ADC(I/Q 각각 bits 비트, 중간범위 반올림). 풀스케일 = max|x| + 여유."""
    fs_ = float(max(np.abs(x.real).max(), np.abs(x.imag).max())) * 1.02 + 1e-30
    step = 2.0 * fs_ / (2 ** bits)
    q = lambda v: np.clip(np.round(v / step), -2 ** (bits - 1), 2 ** (bits - 1) - 1) * step
    return q(x.real) + 1j * q(x.imag), step, fs_


def sec2_dnr(setups):
    """cancel() 은 **선형** 사영이므로 잡음이 있든 없든 DPI 잔류는 cancel(dpi_det) 그대로다.
    → float64 에서는 '잔류/잡음' 이 DNR 에 대해 정확히 1:1 로 따라간다(깊이가 상수).
      즉 **DNR 을 아무리 올려도 잔류는 항상 잡음보다 수백 dB 아래** = 비현실적.
    현실의 바닥은 ADC 양자화잡음이다(span(X) 밖의 백색잡음 → ECA 가 못 지운다):
      양자화잡음/열잡음 = DNR − (6.02·b + 1.76) + 상수  → **DNR 이 커지면 반드시 열잡음을 넘는다.**"""
    out = []
    for name, S in setups:
        nt = S.n_taps
        c = ECACanceller(S.ref_cpi, nt)
        # 정규화된 '단위 DPI' 결정론 성분(파일럿 기준 + RT 잔향)
        unit = S.cpi(S.ref_frame, dpi=1.0,
                     clutter=tuple((dt, r) for dt, r in S.clutter_ratio))
        p_unit = pw(unit)
        resid_unit = c.cancel(unit)
        p_resid_unit = pw(resid_unit)
        rng = np.random.default_rng(7)
        noise = (rng.standard_normal(S.N) + 1j * rng.standard_normal(S.N)) / np.sqrt(2)  # var=1
        rows = []
        for dnr in DNRS:
            amp = 10 ** (dnr / 20.0) / np.sqrt(p_unit)       # DPI 전력 = 10^(DNR/10) × 잡음전력(=1)
            det = amp * unit
            surv = det + noise
            r_float = amp * resid_unit                        # 선형성 → 재계산 불필요
            row = dict(dnr_db=float(dnr),
                       resid_float_db=db(pw(r_float)),        # 열잡음(=0 dB) 대비
                       depth_float_db=db(pw(det) / max(pw(r_float), 1e-300)))
            for b in ADC_BITS:
                sq, step, fsc = _quantize(surv, b)
                qerr = sq - surv                              # 양자화 오차(백색, span(X) 밖)
                r_q = r_float + c.cancel(qerr)
                row[f"resid_adc{b}_db"] = db(pw(r_q))
                row[f"depth_adc{b}_db"] = db(pw(det) / max(pw(r_q), 1e-300))
            rows.append(row)
        out.append(dict(name=name, n_taps=nt, rows=rows,
                        bench_dnr_db=S.lt["dnr_db"]))
    return out


# --------------------------------------------------------------------------- #
#  [3] 파일럿 기준 vs 전체송신 — ECA 가 원리적으로 못 지우는 데이터 성분
# --------------------------------------------------------------------------- #
def sec3_pilot_vs_tx(occs=("G1", "G2", "G3")):
    """벤치마크는 ECA 기저를 wf.ref(파일럿)로 만들고 DPI 는 wf.tx(파일럿+데이터)로 합성한다.
    데이터 RE 는 기준의 지연복제 부분공간 밖 → **원리적으로 못 지운다.**
    잔류의 크기는 (거의) 파형의 '비-기준 에너지 비율'이 정한다.
    다만 RD 맵에서는 그 잔류가 **0-도플러 행**에 통째로 앉는다(DPI 는 정지) → 0-도플러 마스킹이
    그것을 다시 막는다. 두 숫자를 모두 보고한다: (시간영역 깊이) 와 (RD 맵 비-0도플러 잔류)."""
    out = []
    for occ in occs:
        for name, wf in waveforms(occ):
            S = Setup(wf, M=M_DEF)
            c = ECACanceller(S.ref_cpi, S.n_taps)
            # (a) DPI 를 파일럿으로 합성(이상적 = 기저 안) / (b) 전체송신으로 합성(현실 = 데이터 포함)
            d_ref = S.cpi(S.ref_frame, dpi=S.dpi, clutter=S.clutter_abs)
            d_tx = S.cpi(S.tx_frame, dpi=S.dpi, clutter=S.clutter_abs)
            r_ref, r_tx = c.cancel(d_ref), c.cancel(d_tx)
            # RD 맵에서 데이터-DPI 잔류가 어디에 앉는가 (잡음 없이 잔류만)
            Rb, f_d, rd = range_doppler(r_tx, S.ref_cpi, S.fs, S.M, n_range=S.n_range)
            zd = int(np.argmin(np.abs(f_d)))
            rd_off = rd.copy(); rd_off[max(0, zd - 1):zd + 2, :] = 0.0
            # 열잡음(var=1)만 통과시켰을 때 RD 맵 평균전력 = 비교 기준(잡음 플로어)
            rng = np.random.default_rng(11)
            nz = (rng.standard_normal(S.N) + 1j * rng.standard_normal(S.N)) / np.sqrt(2)
            _, _, rdn = range_doppler(c.cancel(nz), S.ref_cpi, S.fs, S.M, n_range=S.n_range)
            nfloor = float(np.mean(rdn ** 2))
            out.append(dict(
                occ=occ, name=name, ref_name=wf.ref_name,
                ref_bw_mhz=wf.ref_bw_hz / 1e6,
                ref_energy_frac_db=S.ref_frac_db,           # 파일럿/전체 평균전력 [dB]
                depth_pilot_dpi_db=db(pw(d_ref) / max(pw(r_ref), 1e-300)),   # 이상(기저 안)
                depth_tx_dpi_db=db(pw(d_tx) / max(pw(r_tx), 1e-300)),        # 현실(데이터 포함)
                resid_over_noise_db=db(pw(r_tx) / 1.0),     # 시간영역 잔류 vs 열잡음(var=1)
                rd_zerodop_peak_over_nfloor_db=db(rd[zd].max() ** 2 / nfloor),
                rd_offzero_peak_over_nfloor_db=db(rd_off.max() ** 2 / nfloor),
                dnr_db=S.lt["dnr_db"], n_taps=S.n_taps))
    return out


# --------------------------------------------------------------------------- #
#  [4] ★ 표적 손실 vs 도플러 — 최소 검출가능 도플러(= 저속 드론의 근본 한계)
# --------------------------------------------------------------------------- #
def _fd_grid(dfd):
    """0 ~ 200 Hz. 노치는 도플러 분해능 Δf_d 규모라 0 근처를 촘촘히."""
    g = np.concatenate([np.linspace(0, 2.5 * dfd, 26), np.linspace(2.6 * dfd, 200.0, 40)])
    return np.unique(np.clip(g, 0, 200.0))


def sec4_target_loss(setups, Ms=(16, 48, 96)):
    """표적만(잡음·DPI·클러터 없이) 넣고 도플러를 0→200 Hz 스윕, ECA 전/후 RD 피크 손실[dB].

    이론: ECA 는 '기준의 정수지연 복제(=0-도플러)' 부분공간을 지운다. 표적 지연이 탭 창 안이면
      (챔버는 Rb≈22 m 로 항상 안이다), 표적의 slow-time 톤 exp(j2πf_d t) 가 CPI 평균과
      겹치는 만큼 함께 지워진다:
          유지율 ≈ 1 − |D(f_d·T_CPI)|²,   D = 정규화 디리클레 커널(≈sinc)
      → 노치 폭은 **1/T_CPI = 도플러 분해능 Δf_d = PRF/M** 한 빈 규모. 파형·M 이 달라도
        f_d/Δf_d 로 정규화하면 **하나의 곡선으로 붕괴**한다 — 그게 이 실험의 증명이다."""
    out = []
    for name, S0 in setups:
        for M in Ms:
            S = Setup(S0.wf, M=M)
            c = ECACanceller(S.ref_cpi, S.n_taps)
            grid = _fd_grid(S.dfd)
            rows = []
            for fd in grid:
                tgt = S.cpi(S.ref_frame, tau=S.st.tau, fd=float(fd), a=1.0)
                Rb, f_ax, rd0 = range_doppler(tgt, S.ref_cpi, S.fs, S.M, n_range=S.n_range)
                _, _, rd1 = range_doppler(c.cancel(tgt), S.ref_cpi, S.fs, S.M, n_range=S.n_range)
                ri = int(np.argmin(np.abs(Rb - S.true_Rb)))
                di = int(np.argmin(np.abs(f_ax - fd)))
                sl = (slice(max(0, di - 1), di + 2), slice(max(0, ri - 1), ri + 2))
                p0 = rd0[sl].max(); p1 = rd1[sl].max()
                rows.append(dict(fd_hz=float(fd), fd_over_dfd=float(fd / S.dfd),
                                 loss_db=float(20 * np.log10((p1 + 1e-30) / (p0 + 1e-30))),
                                 energy_loss_db=db(pw(c.cancel(tgt)) / max(pw(tgt), 1e-300)),
                                 theory_loss_db=_theory_loss_db(fd, S.T_cpi)))
            loss = np.array([r["loss_db"] for r in rows])
            fds = np.array([r["fd_hz"] for r in rows])

            def cross(th):                       # 손실이 th dB 보다 얕아지는 최초 도플러(선형보간)
                ok = np.where(loss > -th)[0]
                if not len(ok) or ok[0] == 0:
                    return None
                i = ok[0]
                x0, x1, y0, y1 = fds[i - 1], fds[i], loss[i - 1], loss[i]
                return float(x0 + ((-th) - y0) * (x1 - x0) / (y1 - y0 + 1e-30))

            fd3, fd1 = cross(3.0), cross(1.0)
            out.append(dict(
                name=name, M=M, n_taps=S.n_taps,
                prf_hz=S.prf, T_cpi_ms=S.T_cpi * 1e3, dfd_hz=S.dfd,
                lam_m=S.st.lam, hz_per_ms=S.hz_per_ms,
                fd_3db_hz=fd3, fd_1db_hz=fd1,
                fd_3db_over_dfd=(fd3 / S.dfd if fd3 else None),
                v_3db_ms=(fd3 / S.hz_per_ms if fd3 else None),   # 최소 검출가능 속도(3 dB 손실)
                v_1db_ms=(fd1 / S.hz_per_ms if fd1 else None),
                loss_at_0_db=float(loss[0]),
                bench_fd_hz=S.true_fd, bench_loss_db=float(
                    np.interp(abs(S.true_fd), fds, loss)),
                rows=rows))
    return out


def _theory_loss_db(fd, T):
    """1-D 사영 근사: 유지율 = 1 − |(1/T)∫exp(j2πf_d t)dt|² = 1 − sinc²(f_d·T)."""
    x = fd * T
    s = 1.0 if abs(x) < 1e-12 else np.sin(np.pi * x) / (np.pi * x)
    return float(10 * np.log10(max(1.0 - s ** 2, 1e-300)))


def sec4b_range_gate(setups):
    """보조: 탭 창(n_taps) 밖의 표적은 도플러 0 이어도 ECA 가 못 지운다.
    → 표적 손실은 '도플러' 뿐 아니라 '표적이 탭 창 안인가'의 함수다. 챔버는 항상 안이다."""
    out = []
    for name, S in setups:
        c = ECACanceller(S.ref_cpi, S.n_taps)
        dr = C0 / S.fs
        gate_m = S.n_taps * dr
        rows = []
        for rb in (S.true_Rb, gate_m * 0.5, gate_m * 1.5, gate_m * 3.0):
            if rb >= S.n_range * dr:             # RD 창 밖이면 측정 불가
                continue
            tgt = S.cpi(S.ref_frame, tau=rb / C0, fd=0.0, a=1.0)
            rows.append(dict(rb_m=float(rb), inside_gate=bool(rb < gate_m),
                             loss_db=db(pw(c.cancel(tgt)) / max(pw(tgt), 1e-300))))
        out.append(dict(name=name, n_taps=S.n_taps, gate_m=float(gate_m),
                        sample_m=float(dr), true_Rb=float(S.true_Rb), rows=rows))
    return out


# --------------------------------------------------------------------------- #
#  [5] 정적 클러터 = 죽은 파라미터 — 부분공간 사영으로 설명
# --------------------------------------------------------------------------- #
def sec5_clutter_dead(setups):
    """정적 클러터 c = Σ aᵢ·ref(t−τᵢ) 는 '지연된 기준신호의 선형결합'이다 → **span(X) 안**.
    ⇒ (I−P)c ≈ 0 (진폭 무관, 정확히 소거). 잔류의 유일한 원인은
      (a) τᵢ 가 정수샘플이 아니라 정수지연 기저로 완벽히 못 만드는 **분수지연 보간 오차**,
      (b) XᴴX 의 대각로딩(1e-6) 과 float64.
    이걸 3중으로 확인한다: ①사영 잔류비 ②진폭 스윕(0 → 직접파보다 강함) ③ SCR/Pd 불변."""
    proj = []
    for name, S in setups:
        c = ECACanceller(S.ref_cpi, S.n_taps)
        # ① 클러터만(진폭 1 기준) 사영 잔류
        cl = S.cpi(S.ref_frame, clutter=tuple((dt, r) for dt, r in S.clutter_ratio))
        res = c.cancel(cl)
        # 정수지연 클러터(대조군) — 분수지연 보간오차가 원인임을 분리
        dr_s = 1.0 / S.fs
        cl_int = S.cpi(S.ref_frame,
                       clutter=tuple((round(dt * S.fs) * dr_s, r) for dt, r in S.clutter_ratio))
        res_int = c.cancel(cl_int)
        # XᴴX 조건수(대각로딩 전) — '완벽함'의 수치적 한계
        n = S.n_taps
        R = np.array([np.vdot(S.ref_cpi[:S.N - d], S.ref_cpi[d:]) for d in range(n)])
        idx = np.arange(n); D = idx[None, :] - idx[:, None]
        XhX = np.where(D <= 0, R[np.abs(D)], np.conj(R[np.abs(D)]))
        cond = float(np.linalg.cond(XhX))
        proj.append(dict(name=name, n_taps=n,
                         resid_frac_db=db(pw(res) / max(pw(cl), 1e-300)),
                         resid_frac_int_delay_db=db(pw(res_int) / max(pw(cl_int), 1e-300)),
                         cond_XhX=cond, load_rel=float(1e-6 / abs(R[0])),
                         clutter_src=("RT" if S.clutter_is_rt else "assumed")))

    # ② 진폭 스윕 → SCR/Pd (run_cell = 벤치마크와 같은 경로)
    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)
    wf = nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")
    base = rt_chamber_clutter(3.5e9) or CH_CLUTTER_RATIO
    sweep = []
    for scale in (0.0, 1.0, 10.0, 100.0):
        cl = tuple((dt, r * scale) for dt, r in base) if scale else ()
        r = run_cell(wf, DRONE, pos, vel, lb, channel=AnalyticChannel(clutter=cl), M=32, N=60)
        sweep.append(dict(scale=float(scale),
                          strongest_db=(float(20 * np.log10(max(a for _, a in cl))) if cl else None),
                          scr=r["scr_mean"], pd=r["pd"]))
    scrs = [x["scr"] for x in sweep]
    return dict(projection=proj, sweep=sweep,
                scr_span_db=float(max(scrs) - min(scrs)),
                clutter_src=("RT" if base is not rt_chamber_clutter and base else "RT"))


# --------------------------------------------------------------------------- #
#  그림
# --------------------------------------------------------------------------- #
def figure(res, setups):
    import matplotlib
    matplotlib.use("Agg")
    import vizstyle
    vizstyle.use_korean()
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(2, 2, figsize=(13.6, 9.6), constrained_layout=True)
    COL = {"5G NR 100MHz": "#1565c0", "WiFi 80MHz": "#c62828", "LTE 20MHz": "#2e7d32"}

    # (a) 깊이 vs 탭
    ax = axs[0, 0]
    for e in res["S1_depth_vs_taps"]:
        t = [r["n_taps"] for r in e["rows"]]
        ax.plot(t, [r["depth_full_db"] for r in e["rows"]], "-o", ms=4,
                color=COL[e["name"]], label=f"{e['name']} (DPI+clutter)")
        ax.plot(t, [r["depth_dpi_db"] for r in e["rows"]], "--", lw=1.2,
                color=COL[e["name"]], alpha=0.55, label=f"{e['name']} (DPI only)")
        ax.axvline(e["taps_used_in_bench"], color=COL[e["name"]], ls=":", lw=1, alpha=0.5)
    ax.set_xscale("log", base=2); ax.set_xticks(TAPS); ax.set_xticklabels(TAPS, fontsize=7)
    ax.set_xlabel("ECA taps  n_taps"); ax.set_ylabel("Cancellation depth [dB]")
    ax.set_title("(a) Cancellation depth vs taps (no target, no noise)\n"
                 "dotted vline = taps used by the benchmark", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=6.5, ncol=2, loc="lower right")

    # (b) DNR 스윕 + ADC
    ax = axs[0, 1]
    e = [x for x in res["S2_dnr"] if x["name"] == "5G NR 100MHz"][0]
    d = [r["dnr_db"] for r in e["rows"]]
    ax.axhline(0, color="k", lw=1.4, label="thermal noise floor (0 dB)")
    ax.plot(d, [r["resid_float_db"] for r in e["rows"]], "-o", ms=4, color="#1565c0",
            label="our ECA (float64) residual")
    for b, c_ in zip(ADC_BITS, ("#ef6c00", "#c62828", "#6a1b9a")):
        ax.plot(d, [r[f"resid_adc{b}_db"] for r in e["rows"]], "-s", ms=4, color=c_,
                label=f"ECA after {b}-bit ADC")
    ax.axvline(e["bench_dnr_db"], color="grey", ls=":", lw=1.2)
    ax.annotate("benchmark\noperating point", (e["bench_dnr_db"], -60),
                fontsize=7.5, color="grey", ha="center")
    ax.set_xlabel("DNR = direct path / noise [dB]")
    ax.set_ylabel("ECA residual re. thermal noise [dB]")
    ax.set_title("(b) Our ECA has no dynamic-range limit -- it is unphysically perfect\n"
                 "(5G NR 100MHz; ADC curves added here for the first time)", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=7.5, loc="upper left")

    # (c) ★ 표적 손실 vs 도플러 (정규화 붕괴)
    ax = axs[1, 0]
    for e in res["S4_target_loss"]:
        ls = {16: ":", 48: "-", 96: "--"}[e["M"]]
        x = [r["fd_over_dfd"] for r in e["rows"]]
        ax.plot(x, [r["loss_db"] for r in e["rows"]], ls, lw=1.5, color=COL[e["name"]],
                alpha=0.9, label=f"{e['name']}  M={e['M']}")
    e0 = res["S4_target_loss"][0]
    xt = np.linspace(0.001, 4.5, 400)
    ax.plot(xt, [10 * np.log10(max(1 - (np.sin(np.pi * u) / (np.pi * u)) ** 2, 1e-12)) for u in xt],
            "k-", lw=2.4, alpha=0.35, label="theory  1 - sinc$^2$(f$_d$T)")
    ax.axhline(-3, color="k", ls="--", lw=0.8)
    ax.set_xlim(0, 4.5); ax.set_ylim(-45, 3)
    ax.set_xlabel("target Doppler / Doppler resolution   f$_d$ / $\\Delta$f$_d$   ($\\Delta$f$_d$=1/T$_{CPI}$)")
    ax.set_ylabel("target amplitude loss after ECA [dB]")
    ax.set_title("(c) ECA also cancels the TARGET -- notch width = one Doppler bin\n"
                 "all waveforms and CPI lengths collapse onto one curve", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=7, ncol=2, loc="lower right")

    # (d) 최소 검출가능 속도
    ax = axs[1, 1]
    e48 = [x for x in res["S4_target_loss"] if x["M"] == 48]
    names = [x["name"] for x in e48]
    v3 = [x["v_3db_ms"] for x in e48]
    v1 = [x["v_1db_ms"] for x in e48]
    xp = np.arange(len(names))
    ax.bar(xp - 0.19, v3, 0.36, color=[COL[n] for n in names], label="v at -3 dB loss")
    ax.bar(xp + 0.19, v1, 0.36, color=[COL[n] for n in names], alpha=0.45,
           label="v at -1 dB loss")
    for i, (a, b) in enumerate(zip(v3, v1)):
        ax.text(i - 0.19, a, f"{a:.2f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + 0.19, b, f"{b:.2f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(SPEED, color="k", ls="--", lw=1.2)
    ax.annotate(f"benchmark target speed {SPEED:.0f} m/s", (len(names) - 0.5, SPEED),
                fontsize=8, ha="right", va="bottom")
    ax.set_xticks(xp); ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("minimum detectable radial speed [m/s]")
    ax.set_title("(d) Slow-drone blind zone (M=48, radial geometry)\n"
                 "below these speeds the ECA eats the target", fontsize=10)
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=8)

    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    setups = [(n, Setup(wf)) for n, wf in waveforms("G3")]

    print("=" * 84)
    print("[E2] ECA 검증 — 동작점 (run_min_cell 과 동일: EIRP=12dBm, semi-anechoic 챔버, mavic4pro)")
    for n, S in setups:
        print(f"  {n:14s} fs={S.fs/1e6:7.2f}MHz  샘플={1e9/S.fs:5.2f}ns({C0/S.fs:5.2f}m)  "
              f"Lf={S.Lf}  PRF={S.prf:7.1f}Hz  T_CPI={S.T_cpi*1e3:5.1f}ms  Δf_d={S.dfd:5.2f}Hz  "
              f"n_taps={S.n_taps}  DNR={S.lt['dnr_db']:.1f}dB  잔향={'RT' if S.clutter_is_rt else '가정'}")

    print("\n" + "=" * 84)
    print("[1] 상쇄 깊이 vs 탭 수 (표적·잡음 없음)")
    S1 = sec1_depth_vs_taps(setups)
    for e in S1:
        print(f"  {e['name']}  잔향 {e['n_clutter']}탭, 최대지연 {e['max_delay_ns']:.1f}ns "
              f"= {e['spread_samples']:.2f} 샘플  (벤치마크 사용 탭={e['taps_used_in_bench']})")
        print(f"      {'n_taps':>7} {'DPI만[dB]':>11} {'DPI+잔향[dB]':>13} {'정상상태[dB]':>13}")
        for r in e["rows"]:
            print(f"      {r['n_taps']:>7} {r['depth_dpi_db']:>11.1f} "
                  f"{r['depth_full_db']:>13.1f} {r['depth_full_steady_db']:>13.1f}")

    print("\n" + "=" * 84)
    print("[2] DNR 스윕 — float64 ECA 는 동적범위 한계가 없다 (+ ADC 를 넣으면?)")
    S2 = sec2_dnr(setups)
    for e in S2:
        print(f"  {e['name']}  (벤치마크 동작점 DNR={e['bench_dnr_db']:.1f}dB)   "
              f"[값 = 잔류 / 열잡음, dB.  0 dB = 잡음과 같음]")
        print(f"      {'DNR':>5} {'float64':>10} {'16bit':>9} {'14bit':>9} {'12bit':>9}")
        for r in e["rows"]:
            print(f"      {r['dnr_db']:>5.0f} {r['resid_float_db']:>10.1f} "
                  f"{r['resid_adc16_db']:>9.1f} {r['resid_adc14_db']:>9.1f} {r['resid_adc12_db']:>9.1f}")

    print("\n" + "=" * 84)
    print("[3] 파일럿 기준 vs 전체송신 — ECA 가 못 지우는 데이터 성분")
    S3 = sec3_pilot_vs_tx()
    print(f"  {'점유':>4} {'파형':14s} {'기준':>8} {'파일럿E[dB]':>11} {'깊이(파일럿DPI)':>15} "
          f"{'깊이(실제tx DPI)':>16} {'잔류/잡음':>10} {'RD 비0도플러':>12}")
    for r in S3:
        print(f"  {r['occ']:>4} {r['name']:14s} {r['ref_name']:>8} {r['ref_energy_frac_db']:>11.1f} "
              f"{r['depth_pilot_dpi_db']:>15.1f} {r['depth_tx_dpi_db']:>16.1f} "
              f"{r['resid_over_noise_db']:>10.1f} {r['rd_offzero_peak_over_nfloor_db']:>12.1f}")

    print("\n" + "=" * 84)
    print("[4] ★ 표적 손실 vs 도플러 — ECA 는 저속 표적을 함께 지운다")
    S4 = sec4_target_loss(setups)
    S4b = sec4b_range_gate(setups)
    print(f"  {'파형':14s} {'M':>3} {'T_CPI':>8} {'Δf_d':>7} {'fd(-3dB)':>9} {'fd/Δf_d':>8} "
          f"{'v(-3dB)':>8} {'v(-1dB)':>8} {'fd=0 손실':>9}")
    for e in S4:
        print(f"  {e['name']:14s} {e['M']:>3} {e['T_cpi_ms']:>7.1f}ms {e['dfd_hz']:>6.2f}Hz "
              f"{e['fd_3db_hz']:>8.2f}Hz {e['fd_3db_over_dfd']:>8.3f} "
              f"{e['v_3db_ms']:>7.2f}m/s {e['v_1db_ms']:>7.2f}m/s {e['loss_at_0_db']:>8.1f}dB")
    print("  → 노치 폭이 f_d/Δf_d 로 보면 파형·M 에 무관하게 같다 = 노치는 **도플러 빈 1개** 규모.")
    print("  → 벤치마크 표적(3 m/s radial)의 ECA 손실:")
    for e in S4:
        if e["M"] == 48:
            print(f"      {e['name']:14s} f_d={e['bench_fd_hz']:+7.1f}Hz → 손실 {e['bench_loss_db']:+.2f} dB")
    print("  [4b] 탭 창 밖의 표적은 도플러 0 이어도 안 지워진다(=손실은 '도플러 × 창' 함수):")
    for e in S4b:
        inn = ", ".join(f"Rb={r['rb_m']:.1f}m{'(안)' if r['inside_gate'] else '(밖)'}→{r['loss_db']:+.1f}dB"
                        for r in e["rows"])
        print(f"      {e['name']:14s} 탭창={e['gate_m']:.1f}m  {inn}")

    print("\n" + "=" * 84)
    print("[5] 정적 클러터는 죽은 파라미터 — 왜? 부분공간 사영")
    S5 = sec5_clutter_dead(setups)
    print("  ① 클러터-only 사영 잔류 (클러터 = 지연된 기준의 선형결합 = span(X) 안):")
    for p in S5["projection"]:
        print(f"      {p['name']:14s} 잔류/입력 = {p['resid_frac_db']:8.1f} dB "
              f"(정수지연이면 {p['resid_frac_int_delay_db']:8.1f} dB)  cond(XᴴX)={p['cond_XhX']:.1e}")
    print("  ② 진폭 스윕 (run_cell = 벤치마크와 같은 경로):")
    for r in S5["sweep"]:
        s = "없음" if r["strongest_db"] is None else f"{r['strongest_db']:+6.1f} dB"
        print(f"      클러터 {s:>10} → SCR {r['scr']:.12f} dB   Pd {r['pd']:.2f}")
    print(f"  → SCR 전 변동폭 {S5['scr_span_db']:.2e} dB. 확인: **죽은 파라미터**.")

    res = dict(
        meta=dict(drone=DRONE, eirp_dbm=EIRP_DBM, M_default=M_DEF,
                  taps_swept=list(TAPS), dnrs=list(DNRS), adc_bits=list(ADC_BITS),
                  setups=[dict(name=n, fs_hz=S.fs, Lf=S.Lf, prf_hz=S.prf,
                               T_cpi_s=S.T_cpi, dfd_hz=S.dfd, n_taps=S.n_taps,
                               n_range=S.n_range, dnr_db=S.lt["dnr_db"],
                               true_Rb_m=S.true_Rb, true_fd_hz=S.true_fd,
                               hz_per_ms=S.hz_per_ms, lam_m=S.st.lam,
                               clutter_src=("RT" if S.clutter_is_rt else "assumed"),
                               ref_energy_frac_db=S.ref_frac_db)
                          for n, S in setups]),
        S1_depth_vs_taps=S1, S2_dnr=S2, S3_pilot_vs_tx=S3,
        S4_target_loss=S4, S4b_range_gate=S4b, S5_clutter_dead=S5)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    figure(res, setups)
    print(f"\n→ {OUT_JSON}\n→ {OUT_FIG}   ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
