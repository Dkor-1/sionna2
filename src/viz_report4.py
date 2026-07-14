# -*- coding: utf-8 -*-
"""
viz_report4.py — (report4) **Sionna 로 만든** 바이스태틱 패시브 레이더 탐지 체인
================================================================================
report4 의 모든 그림을 여기서 만든다. 이전 viz_bistatic.py 는 감시신호를 **손으로**
합성했고(a_tgt=1.0, dpi_amp=55, snr_db=14 — 물리 근거가 없는 손잡이), 챔버 서사도
"무반사라 클러터가 약하다"로 틀려 있었다. 둘 다 여기서 바로잡는다.

■ 신호 체인 — 전부 Sionna
    환경 경로(직접파·바닥·벽)  = **Sionna RT** (benchmark/channel.SionnaRTChannel, with_chamber=True)
                                 → RT 가 실제로 찾은 (상대지연, 직접파대비 진폭비)
    표적 RCS σ                 = **SBR** (rcs_sbr: Mitsuba 광선 + PO 적분, 가림 포함)
    절대전력(직접파·에코·잡음) = **link_budget** (EIRP·kTB — 손잡이 아님, 물리로 유도)
    감시신호 합성              = **Sionna PHY** (cir_to_time_channel + ApplyTimeChannel)
    ECA / CAF / CFAR           = passive_process  (레이더 고유 — Sionna 에 없다)
    장면 렌더                  = **Sionna RT 렌더러** (render_rt)

■ 헤드라인 — **바닥 유령(floor ghost)은 살아남지만, 가짜 표적이 되지는 않는다**
  챔버는 **semi-anechoic**: 벽4면+천장만 흡수체, **바닥은 반사성 콘크리트**다.
  · 정적 클러터는 **죽은 파라미터**다 — ECA 의 기저가 '지연된 기준신호'라 사영이 진폭과
    무관하게 정확히 0 으로 지운다(직접파보다 센 클러터를 넣어도 SCR 이 1e-9 dB 움직임).
  · **표적 경유 바닥 유령**(TX→표적→바닥→RX)은 표적과 함께 **도플러가 실려** ECA 를 통과한다.
    Rb +3.51 m, 에코 대비 −18.2 dB. **여기까지는 사실이다.**
  · ⚠ **그러나 '5G 는 이걸 분해해 100% 가짜 표적을 만든다'는 주장은 측정으로 반증됐다.**
    - 🔑 **대조군이 결정타**: 바닥을 **끄고** 같은 셀의 CFAR 히트율을 재면 5G 에서 **똑같이 100%** 다.
      즉 그 히트는 유령이 아니라 **표적 자신의 거리부엽**이다. 옛 수치는 **대조군 없는 테스트의
      아티팩트**였다. 유령 창을 표적 창과 서로소로 만들고 대조군을 빼면 **P_false = 0%** — 세 신호 모두.
    - 왜 그런가: sep/ΔRb = 1.15 는 **레일리 기준**(같은 세기 두 표적)이다. 유령은 **18 dB 약하고**,
      표적에서 겨우 **1.4 거리샘플**(c/fs=2.44 m) 떨어져 있다 → 표적 자신의 응답 안에 파묻힌다.
      유령을 켜도 그 셀은 **+1.5 dB** 밖에 안 오른다.
      (유령 위치의 정확한 스커트 값은 널 근처에서 심하게 출렁이므로 숫자 하나로 말하지 않는다 —
       robust 한 증거는 위의 대조군이다.)
    - 393 MHz(ΔRb=0.76 m)로 4배 넓히면 유령이 셀에서 **+5.5 dB** 올라오지만, 이번엔
      **CA-CFAR 가 가린다**(강한 표적이 훈련창 안에 있음 = target masking) → 그래도 P_false = 0.
  · ⇒ **유령의 실제 효과는 '가짜 표적'이 아니라 '편향'이다** — 거리 추정 +0.1~0.3 m, 세기 <1 dB.
    유령을 진짜 분해하려면 B ≳ 220 MHz(무마진) / 440 MHz(6 dB 마진) **그리고** CFAR 훈련창 재설계가 필요하다.

실행:  python src/viz_report4.py            (그림 4장)
       python src/viz_report4.py --gif      (+ 추적 GIF)
       python src/viz_report4.py --rt       (+ RT 환경경로 재측정)
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

from gpu import pick as _pick_gpu          # noqa: E402  (mitsuba/torch import 전에!)
_pick_gpu(verbose=False)

import numpy as np                          # noqa: E402
import torch                                # noqa: E402
from sionna.phy.channel import (cir_to_time_channel, ApplyTimeChannel,   # noqa: E402
                                time_lag_discrete_time_channel)

import vizstyle                             # noqa: E402
vizstyle.use_korean()
import matplotlib.pyplot as plt             # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter   # noqa: E402
import matplotlib.image as mpimg            # noqa: E402

from bistatic_scene import bistatic_params, CHAMBER, TX, RX, TGT, VEL, C0   # noqa: E402
from waveforms import wifi_80211ac, lte_downlink, nr_downlink               # noqa: E402
from passive_process import (ECACanceller, range_doppler, ca_cfar_2d,       # noqa: E402
                             peak_detection)
from sionna_chain import target_paths                                       # noqa: E402
from link_budget import LinkBudget, link_terms                              # noqa: E402
from geometry import chamber_window, floor_ghost                            # noqa: E402
from run_min_cell import frame_len, measure_scr, wilson_ci                  # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")
REND = os.path.join(ROOT, "outputs", "renders")
RT_ENV = os.path.join(ROOT, "outputs", "rt_chamber_env.json")

DRONE = "mavic4pro"
EIRP_DBM = 12.0            # 챔버 조명원(저출력 AP 급) — run_min_cell 과 동일한 통제 변수
MDS = 300e-9               # Sionna 채널 최대 지연확산 — 챔버 최대 Rb(≈40 m=133 ns) 를 덮는다
COL = {"wifi": "#1565c0", "lte": "#ef6c00", "nr": "#2e7d32"}
STD = {"wifi": "WiFi", "lte": "LTE", "nr": "5G"}


def waveforms(occ="G3"):
    return {"wifi": wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy=occ),
            "lte": lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy=occ),
            "nr": nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy=occ)}


def nr_fr2(occ="G3"):
    """**초광대역 대조 파형** — NR FR2 수비학(μ=3, SCS 120 kHz) → 점유 393 MHz, ΔRb = 0.76 m.
    실재하는 신호가 아니라 **'대역폭을 4배 주면 유령이 분해되는가'를 시험하는 대조군**이다.
    (waveforms.nr_downlink 의 CP 표는 μ=1 기준이라 FR2 심볼 타이밍과 정확히 같지는 않다 —
     여기서 쓰는 것은 오직 **점유 대역폭**뿐이므로 결론에 영향이 없다.)"""
    return nr_downlink(bw_hz=100e6, scs_hz=120e3, carrier_hz=3.5e9, occupancy=occ)


def range_ambiguity(wf, rb_m):
    """기준신호(정합필터 템플릿)의 **거리 모호함수** |χ(Rb)| (0 dB 정규화).

        χ(τ) = Σ_k |R[k]|² e^{j2π f_k τ}  /  Σ_k |R[k]|²

    이게 report4 의 핵심 도구다: 표적보다 18 dB 약한 유령이 **별개 표적으로 보이려면**
    표적 자신의 이 곡선이 유령 위치에서 −18 dB **아래**로 내려가 있어야 한다.
    'sep/ΔRb > 1'(레일리)만으로는 부족하다 — 그건 **같은 세기** 두 표적의 기준이다."""
    R = np.fft.fft(np.asarray(wf.ref))
    P = np.abs(R) ** 2
    f = np.fft.fftfreq(len(R), d=1.0 / wf.fs_hz)
    tau = np.atleast_1d(np.asarray(rb_m, float)) / C0
    chi = (P[None, :] * np.exp(2j * np.pi * f[None, :] * tau[:, None])).sum(1) / P.sum()
    return 20 * np.log10(np.abs(chi) + 1e-12)


# =========================================================================== #
#  ① 환경 경로 — Sionna RT 가 실측한 챔버 멀티패스
# =========================================================================== #
def measure_rt_env(fcs=(1.843e9, 3.5e9, 5.21e9), spp=4_000_000):
    """SionnaRTChannel(with_chamber=True) 로 챔버 환경 경로를 실측 → JSON 캐시.
    반환/저장: fc → [(상대지연[s], 직접파대비 진폭비), …]  (직접파 자신은 (0, 1))."""
    from channel import SionnaRTChannel
    ch = SionnaRTChannel(with_chamber=True, spp=spp, max_depth=3,
                         min_clutter_ratio=3e-4, max_clutter=12)
    out = {}
    for fc in fcs:
        t0 = time.time()
        st = ch.state(TX, RX, TGT, VEL, fc, DRONE)
        out[f"{fc:.0f}"] = dict(fc=float(fc),
                                clutter=[[float(d), float(r)] for d, r in st.clutter])
        print(f"  [RT] fc={fc/1e9:.3f} GHz → 환경경로 {len(st.clutter)}개 "
              f"(최강 {20*np.log10(max(r for _, r in st.clutter)):+.1f} dB)  ({time.time()-t0:.0f}s)")
    os.makedirs(os.path.dirname(RT_ENV), exist_ok=True)
    json.dump(out, open(RT_ENV, "w"), indent=1)
    return out


_ENV_CACHE = None


def rt_env(fc):
    """캐시된 RT 환경 경로 → (tau[P], amp_rel[P]).  P[0] = 직접파 (0 s, 비 1.0)."""
    global _ENV_CACHE
    if _ENV_CACHE is None:
        if not os.path.exists(RT_ENV):
            print("  RT 환경경로 캐시가 없습니다 → 지금 측정합니다(Sionna RT).")
            _ENV_CACHE = measure_rt_env()
        else:
            _ENV_CACHE = json.load(open(RT_ENV))
    key = min(_ENV_CACHE, key=lambda k: abs(float(k) - fc))
    cl = _ENV_CACHE[key]["clutter"]
    tau = np.array([0.0] + [c[0] for c in cl])
    amp = np.array([1.0] + [c[1] for c in cl])
    return tau, amp


# =========================================================================== #
#  ② 표적 RCS — SBR (Mitsuba 광선 + PO 적분, 가림 포함)
# =========================================================================== #
_SIG_CACHE: dict = {}


def sbr_sigma(fc, u1, u2, drone=DRONE, az_span_deg=8.0, n_az=5):
    """바이스태틱 σ ≈ 이등분선 방향 모노스태틱 σ (등가정리) — **SBR**.
    channel.bistatic_rcs_m2 와 같은 규약이지만 엔진이 순수 PO(가림 X) 대신 SBR(가림 O)."""
    from rcs_po import drone_rcs_pattern
    b = np.asarray(u1) + np.asarray(u2)
    n = np.linalg.norm(b)
    look = (b / n) if n > 1e-9 else np.asarray(u1)
    az = float(np.degrees(np.arctan2(look[1], look[0])))
    el = float(np.degrees(np.arcsin(np.clip(look[2], -1.0, 1.0))))
    key = (drone, round(fc / 1e6), round(az, 2), round(el, 2))
    if key not in _SIG_CACHE:
        azs = az + np.linspace(-az_span_deg / 2, az_span_deg / 2, int(n_az))
        sig, _ = drone_rcs_pattern(drone, fc, az_deg=azs, el_deg=el, engine="sbr")
        _SIG_CACHE[key] = float(np.mean(np.atleast_1d(sig)))    # 선형 평균 = 기대 RCS
    return _SIG_CACHE[key]


# =========================================================================== #
#  ③ 감시신호 합성 — Sionna PHY (cir_to_time_channel + ApplyTimeChannel)
# =========================================================================== #
DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_H_ELEMS = 1.5e8          # h 텐서 한 배치의 최대 원소 수 (complex64 → ≈1.2 GB)


def apply_cpi(frame, a, tau, M, fs, mds=MDS, batch=None):
    """CPI(기준프레임 M회 반복)에 경로 (a, τ) 를 **Sionna PHY 로** 먹인다.

      frame : (Lf,) 한 프레임        a : (P, M·Lf) 절대 샘플시각의 복소이득(도플러 포함)
      tau   : (P,) 직접파 기준 상대지연 [s]
    반환    : (M·Lf,) 감시신호.

    구현 노트 — 두 가지가 중요하다:
      · **프레임 단위 배치**: 전체 CPI(5G 는 2.95 M 샘플)를 한 번에 넣으면 h 텐서가 수 GB 다.
        CPI 는 같은 프레임의 주기적 타일링이므로 프레임마다 **순환 프리픽스**(직전 프레임의
        꼬리 = 자기 자신의 꼬리)를 붙여 자르면 전체를 한 번에 넣은 것과 **정확히 같다**.
      · **l_min 보정**: ApplyTimeChannel 의 출력 t 번째 샘플은 참 시각 t+l_min 에 해당한다
        (Sionna sinc 필터의 군지연). 앞에서 −l_min 개를 버리지 않으면 **모든 경로가 −l_min
        샘플만큼 더 지연**된다(5G 에선 6 샘플 = Rb +14.6 m 편향). ⚠ src/sionna_chain.py 의
        apply() 는 y[:N] 로 잘라 이 보정이 빠져 있다 — 아래 crosscheck() 참조.
      · **GPU + 적응 배치**: h 텐서는 B·P·T·l_tot 로 커진다(RT 경로 13개 × WiFi 프레임이면
        한 프레임만도 400 MB). CPU 에 두면 기어간다 → GPU 로 올리고 배치를 예산에 맞춘다."""
    frame = np.asarray(frame, np.complex64)
    Lf = len(frame)
    lmin, lmax = time_lag_discrete_time_channel(fs, mds)
    l_tot = lmax - lmin + 1
    pre = l_tot - 1
    xe = np.concatenate([frame[-pre:], frame])            # 순환 프리픽스
    Ne = len(xe)
    Tn = Ne + l_tot - 1                                   # 채널 시점 수
    t0 = pre - lmin                                       # 출력에서 프레임이 시작하는 위치
    Ntot = M * Lf
    tau = np.asarray(tau, np.float32)
    a = np.asarray(a, np.complex64)
    P = len(tau)
    if batch is None:                                     # h 가 예산을 넘지 않게
        batch = int(max(1, min(M, _H_ELEMS // max(1, P * Tn * l_tot))))
    out = np.zeros(Ntot, np.complex64)
    Tt = torch.from_numpy(tau)[None, None, None].to(DEV)
    tt = np.arange(Tn)
    Xe = torch.from_numpy(xe).to(DEV)
    app = ApplyTimeChannel(num_time_samples=Ne, l_tot=l_tot)
    for m0 in range(0, M, batch):
        ms = range(m0, min(m0 + batch, M))
        B = len(ms)
        A = np.empty((B, P, Tn), np.complex64)
        for bi, m in enumerate(ms):
            idx = np.clip(m * Lf - pre + lmin + tt, 0, Ntot - 1)
            A[bi] = a[:, idx]
        At = torch.from_numpy(A).to(DEV)[:, None, None, None, None]
        h = cir_to_time_channel(fs, At, Tt.expand(B, -1, -1, -1), lmin, lmax, normalize=False)
        y = app(Xe.expand(B, Ne)[:, None, None, :], h).detach().cpu().numpy().reshape(B, -1)
        del At, h
        for bi, m in enumerate(ms):
            out[m * Lf:(m + 1) * Lf] = y[bi, t0:t0 + Lf]
    return out


def build_cpi(wf, tgt=TGT, vel=VEL, M=48, ghost_on=True, drone=DRONE, lb=None):
    """한 셀의 **결정론적** 감시신호를 Sionna 로 합성한다 (잡음은 trial 마다 따로 더한다).

      환경(직접파+바닥+벽) = RT 경로 × 전체 송신파형(tx: 파일럿+데이터)
      표적 에코 + 바닥유령 = SBR σ × 거울상 기하 × 기준파형(ref: 수신기가 아는 파일럿)
      절대 스케일          = link_budget (잡음전력 1 정규화)

    ※ 진폭이 전부 EIRP 에 √로 비례하므로, 반환된 surv 는 **EIRP 스윕 시 스칼라 배**만 하면
      된다(Sionna 를 다시 안 돌려도 된다) — scale_for_eirp() 참조."""
    lb = lb or LinkBudget(eirp_dbm=EIRP_DBM)
    fs, fc = wf.fs_hz, wf.carrier_hz
    p = bistatic_params(TX, RX, tgt, vel, fc)
    sigma = sbr_sigma(fc, p["u1"], p["u2"], drone=drone)
    lt = link_terms(lb, p["lam"], sigma, p["R1"], p["R2"], p["L"], wf.bw_hz)

    # 잡음대역 보정(run_min_cell 과 동일 규약): 시뮬 잡음은 fs 레이트 백색(var=1)인데
    # link_terms 의 P_n 은 점유대역 B 기준 → 주입 진폭을 √(B/fs) 로 낮춰 등가로 만든다.
    bw_corr = float(np.sqrt(wf.bw_hz / fs))
    dpi = lt["dpi_amp"] * bw_corr

    txp = float(np.sqrt(np.mean(np.abs(wf.tx) ** 2) + 1e-30))
    ref_frame = wf.ref.astype(np.complex64) / txp
    tx_frame = wf.tx.astype(np.complex64) / txp
    Lf = frame_len(wf)                       # WiFi 는 패킷률에 맞춰 무음 패딩(듀티)
    if Lf > len(tx_frame):
        pad = np.zeros(Lf - len(tx_frame), np.complex64)
        ref_frame = np.concatenate([ref_frame, pad])
        tx_frame = np.concatenate([tx_frame, pad])
    Ntot = M * Lf
    n_range, n_taps = chamber_window(wf)

    # --- 환경 경로 (RT 실측, 0-도플러) ---
    tau_e, amp_e = rt_env(fc)
    a_env = (dpi * amp_e)[:, None] * np.ones((1, Ntot), np.complex64)
    surv = apply_cpi(tx_frame, a_env, tau_e, M, fs)

    # --- 표적 에코 (+ 바닥 유령) : SBR σ + 거울상 기하, 도플러는 시간축 a 에 실린다 ---
    a_t, tau_t = target_paths(TX, RX, tgt, vel, fc, sigma_m2=sigma, fs=fs, n_time=Ntot,
                              floor_ghost=ghost_on)
    surv = surv + apply_cpi(ref_frame, dpi * a_t, tau_t, M, fs)

    g = floor_ghost(TX, RX, tgt, vel, fc, pol="V")
    ghost = dict(g, rb_m=float(g["rb_m"]), sep_m=float(g["rb_m"] - p["Rb"]),
                 d_rb_m=float(C0 / wf.bw_hz),
                 amp_db=float(20 * np.log10(g["amp_ratio"] + 1e-30)))
    ghost["ratio"] = abs(ghost["sep_m"]) / ghost["d_rb_m"]
    ghost["resolved"] = bool(ghost["ratio"] > 1.0)

    return dict(surv=surv, ref_cpi=np.tile(ref_frame, M), fs=fs, M=M, Lf=Lf,
                n_range=n_range, n_taps=n_taps, sigma=sigma, link=lt, p=p, wf=wf,
                ghost=ghost, ghost_on=ghost_on, dpi=dpi, bw_corr=bw_corr,
                true_Rb=p["Rb"], true_fd=p["fd"], eirp_dbm=lb.eirp_dbm,
                n_env=len(tau_e))


def scale_for_eirp(cell, eirp_dbm):
    """EIRP 를 바꾼 결정론적 감시신호 — 전 경로 진폭이 √EIRP 에 비례하므로 스칼라 배.
    (Sionna 채널을 다시 돌리지 않는다. 잡음은 절대 고정 var=1.)"""
    return cell["surv"] * float(10 ** ((eirp_dbm - cell["eirp_dbm"]) / 20.0))


def detect(cell, surv, pfa=1e-4):
    """ECA → CAF 거리-도플러 → CA-CFAR.  (셋 다 레이더 고유 — Sionna 에 없다.)"""
    can = cell.get("_can")
    if can is None:
        can = cell["_can"] = ECACanceller(cell["ref_cpi"], cell["n_taps"])
    res = can.cancel(surv)
    Rb, f_d, rd = range_doppler(res, cell["ref_cpi"], cell["fs"], cell["M"],
                                n_range=cell["n_range"])
    det, _, _ = ca_cfar_2d(rd, pfa=pfa)
    zd = int(np.argmin(np.abs(f_d)))
    det[zd, :] = False                    # 0-도플러 능선(직접파·정적 클러터 잔류)은 히트 아님
    return Rb, f_d, rd, det


def _cell_idx(Rb, f_d, rb, fd):
    return (int(np.argmin(np.abs(Rb - rb))), int(np.argmin(np.abs(f_d - fd))))


def _ghost_window(Rb, f_d, cell):
    """유령 셀(±1) 중 **참표적 셀(±1) 과 겹치지 않는** 부분만 돌려준다.

    왜 이렇게까지 하나: 유령은 표적에서 고작 1~2 거리빈 떨어져 있다. ±1 창을 그대로 쓰면
    표적 자신의 피크·거리부엽이 유령 창에 새어 들어와 P_false 가 **가짜로 부풀려진다**.
    두 창을 서로소로 만들어야 '별개의 표적으로 찍혔다'가 참이 된다.
    창이 통째로 표적 창에 먹히면(=병합, LTE/WiFi) 유령은 정의상 검출 불가 → 빈 창."""
    ri, di = _cell_idx(Rb, f_d, cell["true_Rb"], cell["true_fd"])
    gi, gd = _cell_idx(Rb, f_d, cell["ghost"]["rb_m"], cell["ghost"]["fd"])
    cells = [(d, r)
             for d in range(max(0, gd - 1), min(len(f_d), gd + 2))
             for r in range(max(0, gi - 1), min(len(Rb), gi + 2))
             if abs(d - di) > 1 or abs(r - ri) > 1]          # 표적 창과 서로소
    return cells, (ri, di)


def montecarlo(cell, eirp_dbm=None, N=40, pfa=1e-4, seed0=0):
    """잡음만 바꿔가며 N-trial → Pd(참표적) · P_false(유령셀에 별개 검출) · SCR.

    ※ ghost_on=False 인 셀에도 **같은 유령 셀 위치**에서 P_false 를 잰다 — 그게 **대조군**이다
      (표적 거리부엽이 그 셀을 때리는 확률). ON 과 OFF 의 차이만이 '유령이 만든 가짜 표적'이다."""
    surv0 = cell["surv"] if eirp_dbm is None else scale_for_eirp(cell, eirp_dbm)
    Ncpi = len(surv0)
    hits = ghosts = 0
    scrs = []
    for k in range(N):
        rng = np.random.default_rng(seed0 + k)
        noise = np.sqrt(0.5) * (rng.standard_normal(Ncpi) + 1j * rng.standard_normal(Ncpi))
        Rb, f_d, rd, det = detect(cell, surv0 + noise, pfa)
        gcells, (ri, di) = _ghost_window(Rb, f_d, cell)
        hits += int(det[max(0, di - 1):di + 2, max(0, ri - 1):ri + 2].any())
        scr, _ = measure_scr(Rb, f_d, rd, cell["true_Rb"], cell["true_fd"])
        scrs.append(scr)
        ghosts += int(any(det[d, r] for d, r in gcells))
    lo, hi = wilson_ci(hits, N)
    return dict(pd=hits / N, pd_lo=lo, pd_hi=hi, p_false=ghosts / N,
                scr=float(np.mean(scrs)), N=N, n_gcells=len(gcells))


# =========================================================================== #
#  검증 — Sionna PHY 체인이 손합성(make_cpi) 과 같은가
# =========================================================================== #
def crosscheck(verbose=True):
    """Sionna PHY 체인 ↔ passive_process.make_cpi (손합성) 상관 검증.
    같은 (a, τ) 를 주면 상관 1.0000 이어야 한다 — 그래야 '엔진만 바꿨다'가 참이다."""
    from passive_process import make_cpi
    out = []
    for key, wf in waveforms().items():
        fs, Lf, M = wf.fs_hz, len(wf.tx), 8
        tau_s, fd = 22.0 / C0, 65.0
        n = np.arange(M * Lf)
        a = (1e-3 * np.exp(1j * 2 * np.pi * fd * n / fs))[None, :]
        y = apply_cpi(wf.tx, a, np.array([tau_s]), M, fs)
        s, _ = make_cpi(wf.tx, M, fs, tau_s, fd, a_tgt=1e-3, dpi_amp=0.0, clutter=(),
                        abs_noise=True, noise_var=0.0)
        c = abs(np.vdot(s, y) / (np.linalg.norm(s) * np.linalg.norm(y) + 1e-30))
        out.append((key, float(c)))
        if verbose:
            print(f"  {STD[key]:5s} Sionna PHY ↔ make_cpi 상관 = {c:.6f}")
    return out


# =========================================================================== #
#  ④ Sionna RT 렌더 — 챔버 안 TX/RX/드론 + 추적된 경로 (바닥 반사가 보인다)
# =========================================================================== #
def render_scene(tag="r4", tgt=TGT, spp=512, force=False):
    """Sionna RT 렌더러로 챔버 장면 + **RT 가 실제로 추적한 1-bounce 경로**를 그린다.
    바닥 반사가 그림에 그대로 보인다 — 유령 서사와 직결된다."""
    outs = {k: os.path.join(REND, f"{tag}_{k}.png") for k in ("wide", "side", "top")}
    if not force and all(os.path.exists(v) for v in outs.values()):
        return outs
    os.makedirs(REND, exist_ok=True)
    import render_rt as R
    import sionna.rt as rt
    sc = R.make_scene(drone=DRONE, tgt=tuple(map(float, tgt)), cutaway=True, vel=VEL)
    solver = rt.PathSolver()
    paths = solver(sc, max_depth=1, los=True, specular_reflection=True,
                   diffuse_reflection=False, refraction=False,
                   samples_per_src=4_000_000, seed=1)
    print(f"  [RT] 1-bounce 경로 {int(np.asarray(paths.tau).size)}개 (직접파 + 바닥/벽 반사)")
    R.shot(sc, f"{tag}_wide", R.cam(*R.CAMS["wide"]), paths=paths, spp=spp, res=(1180, 860))
    R.shot(sc, f"{tag}_side", R.cam(*R.CAMS["side"]), paths=paths, spp=spp, res=(1180, 860),
           clip=R.CLIP_CEIL)
    R.shot(sc, f"{tag}_top", R.cam(*R.CAMS["top"]), paths=paths, spp=spp, res=(1180, 860),
           clip=R.CLIP_CEIL)
    return outs


# =========================================================================== #
#  그림 1 — 기하: Sionna RT 렌더 + 바닥 유령 단면
# =========================================================================== #
def fig_geometry(outdir=FIG):
    R = render_scene()
    fc = 3.5e9
    p = bistatic_params(TX, RX, TGT, VEL, fc)
    g = floor_ghost(TX, RX, TGT, VEL, fc, pol="V")
    tau_e, amp_e = rt_env(fc)

    fig = plt.figure(figsize=(16.2, 5.9), constrained_layout=True)
    fig.suptitle("The chamber has a floor - and the floor is the whole story",
                 fontsize=15.5, fontweight="bold")
    fig.supxlabel(
        "(a) is rendered by Sionna RT itself: those rays ARE the paths the solver found. Walls and ceiling are absorber,\n"
        "the FLOOR is bare concrete. (c) is what RT measured - every one of those paths is static, so ECA erases them all.\n"
        "The one path ECA cannot erase is the ghost in (b), because it goes through the moving target.",
        fontsize=8.5, color="0.45")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.18, 1.05, 1.0])

    # (a) Sionna RT 렌더
    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(mpimg.imread(R["wide"])); ax.axis("off")
    ax.set_title("(a) Sionna RT - the paths it actually traced", fontsize=10.5)
    ax.text(0.5, -0.06, "TX (red) and RX (green) on the same wall; rays bounce off floor and ceiling.\n"
                        "Note: NO ray reaches the drone - a 0.35 m target at 18 m is invisible to RT.",
            transform=ax.transAxes, ha="center", va="top", fontsize=8, color="0.4")

    # (b) 펼친 경로 단면 — TX→표적→RX (직접) vs TX→표적→바닥→RX (유령)
    axg = fig.add_subplot(gs[0, 1])
    tx, rx, tg = (np.asarray(v, float) for v in (TX, RX, TGT))
    s1 = float(np.linalg.norm(tg[:2] - tx[:2]))            # TX→표적 지상거리
    s2 = float(np.linalg.norm(rx[:2] - tg[:2]))            # 표적→RX 지상거리
    sB = s1 + s2 * tg[2] / (tg[2] + rx[2])                 # 바닥 반사점(거울상 직선 ∩ z=0)
    axg.axhspan(-0.5, 0, color="#b0a99f", zorder=0)
    axg.axhline(0, color="#5d534a", lw=2.2)
    axg.text((s1 + s2) * 0.5, -0.3, "reflective concrete floor", color="0.2", fontsize=8.5,
             ha="center", va="center")
    axg.plot([0, s1], [tx[2], tg[2]], "--", color="#ef6c00", lw=1.8, label="R1  TX $\\to$ target")
    axg.plot([s1, s1 + s2], [tg[2], rx[2]], "-", color="#2e7d32", lw=2.4,
             label="R2  target $\\to$ RX  (echo)")
    axg.plot([s1, sB], [tg[2], 0], "-", color="#ff1744", lw=2.2)
    axg.plot([sB, s1 + s2], [0, rx[2]], "-", color="#ff1744", lw=2.2,
             label="R2'  target $\\to$ floor $\\to$ RX  (GHOST)")
    axg.plot([s1, s1 + s2], [tg[2], -rx[2]], ":", color="#ff1744", lw=1.1, alpha=0.75)
    axg.plot(0, tx[2], "^", ms=14, color="#ef6c00")
    axg.text(0, tx[2] + 0.6, "TX", color="#ef6c00", ha="center", fontsize=9.5)
    axg.plot(s1 + s2, rx[2], "v", ms=14, color="#1565c0")
    axg.text(s1 + s2, rx[2] + 0.6, "RX", color="#1565c0", ha="center", fontsize=9.5)
    axg.plot(s1 + s2, -rx[2], "v", ms=11, mfc="none", mec="#ff1744", mew=1.5)
    axg.text(s1 + s2, -rx[2] - 1.3, "RX image", color="#ff1744", ha="center", fontsize=8.5)
    axg.plot(s1, tg[2], "o", ms=12, color="k")
    axg.text(s1, tg[2] + 0.7, "target", ha="center", fontsize=9.5)
    axg.plot(sB, 0, "o", ms=8, mfc="#ff1744", mec="w", mew=1.2)
    axg.annotate(f"$\\theta_i$ = {g['theta_i_deg']:.0f}$\\degree$,  $|\\Gamma|$ = {g['gamma']:.2f}",
                 xy=(sB, 0), xytext=(sB - 8.5, 3.2), fontsize=9, color="#ff1744",
                 arrowprops=dict(arrowstyle="->", color="#ff1744", lw=1.1))
    axg.text(0.015, 0.975,
             f"echo   Rb = {p['Rb']:.1f} m   $f_d$ = {p['fd']:+.0f} Hz\n"
             f"GHOST  Rb = {g['rb_m']:.1f} m   $f_d$ = {g['fd']:+.0f} Hz\n"
             f"          {g['rb_m']-p['Rb']:+.2f} m,  {20*np.log10(g['amp_ratio']):.1f} dB re echo\n"
             f"it carries the target's Doppler\n$\\Rightarrow$ ECA cannot remove it",
             transform=axg.transAxes, va="top", fontsize=8.8,
             bbox=dict(fc="#ffebee", ec="#ff1744", alpha=0.93, boxstyle="round,pad=0.42"))
    axg.set_xlim(-2, s1 + s2 + 2); axg.set_ylim(-8.2, 12.5)
    axg.set_xlabel("distance along the unfolded path [m]"); axg.set_ylabel("height z [m]")
    axg.set_title("(b) The target-borne floor ghost", fontsize=10.5)
    axg.legend(fontsize=8, loc="lower left", framealpha=0.9)
    axg.grid(alpha=0.22)

    # (c) RT 가 실측한 챔버 CIR — 전부 0-도플러 → ECA 가 죽인다.  유령만 도플러 有.
    axc = fig.add_subplot(gs[0, 2])
    db = 20 * np.log10(amp_e[1:] + 1e-12)
    axc.stem(tau_e[1:] * 1e9, db, linefmt="0.55", markerfmt="o", basefmt=" ")
    axc.plot(0, 0, "*", ms=18, color="#c62828", zorder=5)
    axc.text(1.5, 0.4, "direct path (DPI)", color="#c62828", fontsize=9, va="bottom")
    i0 = int(np.argmin(np.abs(tau_e[1:] - 19.3e-9)))
    axc.annotate(f"floor bounce\n{tau_e[1:][i0]*1e9:.1f} ns, {db[i0]:.1f} dB\n"
                 f"(Fresnel predicts -14.7 dB)",
                 xy=(tau_e[1:][i0] * 1e9, db[i0]), xytext=(46, -7.5), fontsize=8.5,
                 color="#5d534a",
                 arrowprops=dict(arrowstyle="->", color="#5d534a", lw=1.0))
    axc.axvspan(-3, 145, color="#eceff1", zorder=0)
    axc.text(0.5, 0.055, "ALL of these are static (0 Doppler)\n$\\Rightarrow$ ECA projects them exactly to zero\n"
                         "(a dead parameter: even +14 dB moves SCR by 1e-9 dB)",
             transform=axc.transAxes, ha="center", fontsize=8.6, color="0.25",
             bbox=dict(fc="w", ec="0.6", alpha=0.9, boxstyle="round,pad=0.35"))
    axc.set_xlim(-4, 145); axc.set_ylim(-26, 4)
    axc.set_xlabel("delay relative to direct path [ns]")
    axc.set_ylabel("amplitude re direct [dB]")
    axc.set_title(f"(c) Chamber CIR measured by Sionna RT\n({len(tau_e)-1} paths, "
                  f"strongest {db.max():+.1f} dB)", fontsize=10.5)
    axc.grid(alpha=0.25)

    fn = os.path.join(outdir, "report4_geometry.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[r4]", os.path.relpath(fn, ROOT)); return fn


# =========================================================================== #
#  그림 2 — 거리-도플러: 유령 OFF vs ON  (Sionna PHY 로 합성)
# =========================================================================== #
def fig_rangedoppler(outdir=FIG, M=48):
    wf = waveforms()["nr"]
    cells = {}
    for on in (False, True):
        t0 = time.time()
        cells[on] = build_cpi(wf, M=M, ghost_on=on)
        print(f"  [Sionna PHY] 5G CPI ghost={'ON ' if on else 'OFF'} 합성 ({time.time()-t0:.1f}s)")
    c1 = cells[True]
    g = c1["ghost"]; lt = c1["link"]

    fig, axes = plt.subplots(1, 2, figsize=(14.4, 5.8), constrained_layout=True)
    fig.suptitle("The floor ghost survives ECA - and yet almost nothing changes",
                 fontsize=15, fontweight="bold")
    prf = c1["fs"] / c1["Lf"]
    fig.supxlabel(
        f"5G NR 100 MHz - signal synthesised by Sionna PHY (ApplyTimeChannel) on Sionna-RT chamber paths "
        f"({c1['n_env']} paths) + SBR target $\\sigma$ = {10*np.log10(c1['sigma']):.1f} dBsm.\n"
        f"EIRP {EIRP_DBM:.0f} dBm -> echo SNR {lt['snr_echo_db']:+.1f} dB, direct-to-echo "
        f"{lt['dnr_db']:.0f} dB (all physics-derived, no hand-set knobs) - "
        f"PRF {prf:.0f} Hz - $\\Delta$Rb = {C0/wf.bw_hz:.1f} m - CFAR Pfa = 1e-4",
        fontsize=8.5, color="0.45")

    for ax, on in zip(axes, (False, True)):
        c = cells[on]
        rng = np.random.default_rng(3)
        Ncpi = len(c["surv"])
        noise = np.sqrt(0.5) * (rng.standard_normal(Ncpi) + 1j * rng.standard_normal(Ncpi))
        Rb, f_d, rd, det = detect(c, c["surv"] + noise)
        rdb = 20 * np.log10(rd / rd.max() + 1e-9)
        im = ax.pcolormesh(Rb, f_d, rdb, cmap="turbo", vmin=-45, vmax=0, shading="auto")
        ax.plot(c["true_Rb"], c["true_fd"], "o", mfc="none", mec="w", ms=16, mew=1.8,
                label="True target")
        dd, dr = np.where(det)
        if len(dd):
            ax.plot(Rb[dr], f_d[dd], "x", color="w", ms=7, mew=1.4, alpha=0.85,
                    label="CFAR detections")
        if on:
            ax.plot(g["rb_m"], g["fd"], "s", mfc="none", mec="#ff1744", ms=16, mew=2.0,
                    label="Floor ghost (predicted position)")
        ax.set_xlim(c["true_Rb"] - 13, g["rb_m"] + 13)
        ax.set_ylim(-330, 330)
        ax.set_xlabel("Bistatic range Rb [m]"); ax.set_ylabel("Doppler $f_d$ [Hz]")
        ax.set_title(("(b) Floor reflection ON (the real semi-anechoic chamber)"
                      if on else "(a) Floor reflection OFF (the idealised anechoic one)"),
                     fontsize=11)
        ax.legend(fontsize=8.5, loc="upper right", framealpha=0.85)
        fig.colorbar(im, ax=ax, fraction=0.046, label="Normalized [dB]")

    axes[1].annotate(f"+{g['sep_m']:.2f} m,  {g['amp_db']:.1f} dB   (sep / $\\Delta$Rb = {g['ratio']:.2f})\n"
                     f"but it lands INSIDE the target's own ridge",
                     xy=(g["rb_m"] + 1.2, g["fd"]),
                     xytext=(c1["true_Rb"] - 12.2, -250), ha="left",
                     fontsize=9, color="w",
                     arrowprops=dict(arrowstyle="->", color="w", lw=1.2))
    axes[0].text(0.03, 0.05, "The horizontal streak is the target's OWN range sidelobe ridge -\n"
                             "present in both panels. It is 18 dB stronger than the ghost,\n"
                             "and the ghost sits on top of it. See report4_ghost.png.",
                 transform=axes[0].transAxes, fontsize=8, color="w", va="bottom")
    fn = os.path.join(outdir, "report4_rangedoppler.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[r4]", os.path.relpath(fn, ROOT))
    return fn, cells

# =========================================================================== #
#  그림 3 — 바닥 유령: 살아남지만 **가짜 표적이 되지는 않는다** (헤드라인)
# =========================================================================== #
def ghost_cell_levels(wf, M=32):
    """유령 셀의 세기를 **잡음 없이** ON/OFF 로 잰다 (표적 피크 대비 dB).

    OFF 값 = 표적 자신의 정합필터 스커트가 그 셀에 흘린 양(= **대조군**).
    ON−OFF = 유령이 실제로 보탠 양. 이게 작으면 '유령이 만든 가짜 표적'은 존재하지 않는다."""
    out = {}
    for nm, on in (("off", False), ("on", True)):
        c = build_cpi(wf, M=M, ghost_on=on)
        Rb, f_d, rd, _ = detect(c, c["surv"])                 # 잡음 0
        di = int(np.argmin(np.abs(f_d - c["true_fd"])))
        ri = int(np.argmin(np.abs(Rb - c["true_Rb"])))
        gi = int(np.argmin(np.abs(Rb - c["ghost"]["rb_m"])))
        pk = rd[max(0, di - 1):di + 2, max(0, ri - 1):ri + 2].max()
        out[nm] = float(20 * np.log10(rd[max(0, di - 1):di + 2,
                                         max(0, gi - 1):gi + 2].max() / pk))
        out[nm + "_cell"] = c
    out["excess"] = out["on"] - out["off"]
    return out


def fig_ghost(outdir=FIG, M=32, N=40):
    """**교정된 헤드라인**: 유령은 ECA 를 통과해 살아남지만, 이 대역폭들에선 **가짜 표적이 되지 않는다.**
    표적 자신의 정합필터 주엽 스커트(−7.7 dB)가 유령(−18.2 dB)보다 10 dB 세기 때문이다."""
    keys = ["lte", "wifi", "nr"]
    wfs = waveforms()
    wfs["fr2"] = nr_fr2()                       # 대조군: 393 MHz (ΔRb=0.76 m)
    allk = keys + ["fr2"]
    LBL = dict(STD, fr2="393 MHz\n(control)")

    lv, mc_on, mc_off = {}, {}, {}
    for k in allk:
        t0 = time.time()
        lv[k] = ghost_cell_levels(wfs[k], M=M)
        mc_on[k] = montecarlo(lv[k]["on_cell"], N=N)
        mc_off[k] = montecarlo(lv[k]["off_cell"], N=N)
        g = lv[k]["on_cell"]["ghost"]
        print(f"  [{k:4s}] B={wfs[k].bw_hz/1e6:6.1f}MHz dRb={g['d_rb_m']:5.2f}m ratio={g['ratio']:.2f} | "
              f"ghost cell OFF={lv[k]['off']:+6.1f}dB ON={lv[k]['on']:+6.1f}dB "
              f"excess={lv[k]['excess']:+5.1f}dB | Pd={mc_on[k]['pd']*100:3.0f}% "
              f"P_false ON={mc_on[k]['p_false']*100:3.0f}% ctrl={mc_off[k]['p_false']*100:3.0f}% "
              f"({time.time()-t0:.0f}s)")

    fig, axes = plt.subplots(1, 3, figsize=(16.4, 5.4), constrained_layout=True)
    fig.suptitle("The floor ghost survives ECA - but it never becomes a false target",
                 fontsize=15.5, fontweight="bold")
    fig.supxlabel(
        "The ghost is 18 dB below the echo and only 3.5 m behind it. To be seen as a SEPARATE target it must rise above the\n"
        "target's own matched-filter skirt at that offset - and it does not. 'separation / $\\Delta$Rb > 1' is the Rayleigh criterion for\n"
        "two EQUAL scatterers; a 18 dB weaker one needs far more. Even the 393 MHz control, where the ghost does clear the\n"
        "skirt, is masked by CA-CFAR: the strong target sits inside the CFAR training window.",
        fontsize=8.5, color="0.45")

    g0 = lv["nr"]["on_cell"]["ghost"]
    sep, gdb = g0["sep_m"], g0["amp_db"]

    # (a) 정합필터 거리 모호함수 + 유령 위치/세기
    ax = axes[0]
    rb = np.linspace(-1.0, 12.0, 3000)
    for k in allk:
        c = "#7b1fa2" if k == "fr2" else COL[k]
        ls = "--" if k == "fr2" else "-"
        ax.plot(rb, range_ambiguity(wfs[k], rb), color=c, lw=1.8, ls=ls,
                label=f"{'393 MHz (control)' if k=='fr2' else STD[k]} "
                      f"({wfs[k].bw_hz/1e6:.0f} MHz)")
    ax.axvline(sep, color="k", ls=":", lw=1.2)
    ax.axhline(gdb, color="#ff1744", lw=1.6)
    ax.plot(sep, gdb, "*", ms=20, color="#ff1744", zorder=6)
    ax.annotate("the GHOST lives here\n(+3.51 m, -18.2 dB)", xy=(sep, gdb),
                xytext=(5.0, -11.5), fontsize=9, color="#ff1744",
                arrowprops=dict(arrowstyle="->", color="#ff1744", lw=1.2))
    ax.text(sep + 0.15, -3.0, "ghost offset", rotation=90, fontsize=8.5, color="0.3")
    ax.text(0.30, 0.055,
            "For LTE / WiFi / 5G the ghost falls inside the target's own\n"
            "main-lobe skirt / first sidelobes - the target's response there is\n"
            "comparable to the ghost. Only 393 MHz puts several clean\n"
            "resolution cells between them.",
            transform=ax.transAxes, fontsize=8.2, color="0.25",
            bbox=dict(fc="w", ec="0.6", alpha=0.92, boxstyle="round,pad=0.35"))
    ax.set_xlim(-1, 12); ax.set_ylim(-34, 3)
    ax.set_xlabel("range offset from the target [m]")
    ax.set_ylabel("matched-filter response [dB re peak]")
    ax.set_title("(a) Why the ghost hides: the target's own ambiguity", fontsize=11)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.25)

    # (b) 유령 셀 실측 — OFF(대조군) vs ON
    ax = axes[1]
    x = np.arange(len(allk))
    off = [lv[k]["off"] for k in allk]
    on = [lv[k]["on"] for k in allk]
    ax.bar(x - 0.2, off, 0.4, color="0.75", hatch="//", edgecolor="0.45",
           label="floor OFF (control) = target's own skirt")
    ax.bar(x + 0.2, on, 0.4, color="#ff1744", label="floor ON = skirt + ghost")
    for i, k in enumerate(allk):
        ax.text(i + 0.2, max(on[i], off[i]) + 0.5, f"+{lv[k]['excess']:.1f} dB",
                ha="center", fontsize=9, fontweight="bold",
                color="#c62828" if lv[k]["excess"] > 3 else "0.35")
    ax.axhline(gdb, color="#ff1744", ls=":", lw=1.4)
    ax.text(len(allk) - 0.5, gdb + 0.4, "ghost's own level (-18.2 dB)", ha="right",
            fontsize=8.5, color="#ff1744")
    ax.set_xticks(x); ax.set_xticklabels([LBL[k] for k in allk], fontsize=9)
    ax.set_ylabel("level in the ghost cell ($\\pm$1 bin) [dB re target peak]")
    ax.set_ylim(-21, 3)
    ax.set_title("(b) What is actually in the ghost cell (measured, noise-free)", fontsize=11)
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.25, axis="y")
    ax.text(0.5, 0.30, "Turning the floor ON raises the cell by only\n"
                       "+1.5 dB at 5G. The cell is filled by the TARGET,\nnot by the ghost.",
            transform=ax.transAxes, ha="center", fontsize=8.3, color="0.25",
            bbox=dict(fc="w", ec="0.6", alpha=0.92, boxstyle="round,pad=0.35"))

    # (c) 결과 — 가짜 표적은 나오지 않는다
    ax = axes[2]
    pd = [mc_on[k]["pd"] * 100 for k in allk]
    pf = [mc_on[k]["p_false"] * 100 for k in allk]
    pf0 = [mc_off[k]["p_false"] * 100 for k in allk]
    ax.bar(x - 0.26, pd, 0.26, color="#2e7d32", label="Pd (true target)")
    ax.bar(x, pf, 0.26, color="#ff1744", label="P(false target), floor ON")
    ax.bar(x + 0.26, pf0, 0.26, color="0.75", hatch="//", edgecolor="0.45",
           label="same cell, floor OFF (control)")
    for i in range(len(allk)):
        ax.text(i - 0.26, pd[i] + 2, f"{pd[i]:.0f}%", ha="center", fontsize=8.5)
        ax.text(i, pf[i] + 2, f"{pf[i]:.0f}%", ha="center", fontsize=8.5, color="#c62828")
    ax.set_xticks(x); ax.set_xticklabels([LBL[k] for k in allk], fontsize=9)
    ax.set_ylabel("probability [%]"); ax.set_ylim(0, 132)
    ax.set_title(f"(c) The control kills the claim (N = {N})", fontsize=11)
    ax.legend(fontsize=7.6, loc="upper left"); ax.grid(alpha=0.25, axis="y")
    ax.annotate("", xy=(2.30, 108), xytext=(1.98, 108),
                arrowprops=dict(arrowstyle="<->", color="#c62828", lw=1.3))
    ax.text(2.14, 111, "IDENTICAL", ha="center", fontsize=8.4, fontweight="bold",
            color="#c62828")
    ax.text(0.5, 0.42,
            "At 5G the ghost cell fires 100% of the time -\nbut it fires 100% with the floor OFF too.\n"
            "Those hits are the TARGET's own sidelobes.\n"
            "The old \"100% false target\" was this artifact.\n\n"
            "The ghost's real effect is a BIAS: it shifts the\n"
            "range estimate by 0.1 - 0.3 m, level by < 1 dB.",
            transform=ax.transAxes, ha="center", fontsize=8.1, color="0.25",
            bbox=dict(fc="#fff8e1", ec="#c62828", alpha=0.95, boxstyle="round,pad=0.4"))

    fn = os.path.join(outdir, "report4_ghost.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[r4]", os.path.relpath(fn, ROOT))
    return fn, (lv, mc_on, mc_off)


# =========================================================================== #
#  그림 4 — 검출 성능: Pd·P_false vs EIRP (물리 유도, 손잡이 없음)
# =========================================================================== #
def fig_detection(outdir=FIG, M=24, N=24, eirps=(-18, -12, -6, 0, 6, 12)):
    """(a) Pd vs EIRP — 물리 예산에서 유도. (b) 유령이 왜 끝내 선언되지 않나 — **CFAR 마스킹**."""
    # 스윕은 비싸다(수 분) → JSON 캐시. 그림 문구만 고칠 땐 재계산하지 않는다.
    cache = os.path.join(ROOT, "outputs", "report4_detection.json")
    sig = dict(M=M, N=N, eirps=list(eirps))
    curves = None
    if os.path.exists(cache):
        d = json.load(open(cache))
        if d.get("sig") == sig:
            curves = {k: tuple(v) for k, v in d["curves"].items()}
            print("  (캐시된 EIRP 스윕 재사용 —", os.path.relpath(cache, ROOT), ")")
    if curves is None:
        curves = {}
        for k, wf in waveforms().items():
            cON = build_cpi(wf, M=M, ghost_on=True)
            cOFF = build_cpi(wf, M=M, ghost_on=False)          # **대조군**
            pd, pf, pf0 = [], [], []
            for e in eirps:
                pd.append(montecarlo(cON, eirp_dbm=e, N=N)["pd"])
                pf.append(montecarlo(cON, eirp_dbm=e, N=N)["p_false"])
                pf0.append(montecarlo(cOFF, eirp_dbm=e, N=N)["p_false"])
            curves[k] = (pd, pf, pf0)
            print(f"  [{STD[k]:4s}] Pd {['%.2f' % v for v in pd]}\n"
                  f"         P_false ON   {['%.2f' % v for v in pf]}\n"
                  f"         P_false ctrl {['%.2f' % v for v in pf0]}")
        json.dump(dict(sig=sig, curves=curves), open(cache, "w"), indent=1)
    wfs = waveforms()

    fig, axes = plt.subplots(1, 3, figsize=(16.6, 5.3), constrained_layout=True)
    fig.suptitle("Detection is physics-derived - and the ghost still never fires",
                 fontsize=15, fontweight="bold")
    fig.supxlabel(
        "x-axis is the illuminator EIRP, a physical budget - NOT an injected echo SNR. Echo power follows from the bistatic radar equation with the\n"
        f"SBR RCS and the RT geometry; noise is kT0FB. Reference = known pilots only. M = {M}, Pfa = 1e-4, N = {N} trials per point.",
        fontsize=8.5, color="0.45")

    # (a) Pd vs EIRP
    ax = axes[0]
    for k in ("lte", "wifi", "nr"):
        ax.plot(eirps, curves[k][0], "o-", color=COL[k], lw=2.0,
                label=f"{STD[k]} {wfs[k].bw_hz/1e6:.0f} MHz")
    ax.axhline(0.9, color="0.6", ls=":", lw=0.9)
    ax.set_xlabel("Illuminator EIRP [dBm]"); ax.set_ylabel("Pd")
    ax.set_ylim(-0.05, 1.08); ax.grid(alpha=0.3); ax.legend(fontsize=8.5, loc="lower right")
    ax.set_title("(a) Pd of the true target", fontsize=11.5)

    # (b) P_false: 유령 ON vs 대조군 — 겹치면 '유령 때문이 아니다'
    ax = axes[1]
    for k in ("lte", "wifi", "nr"):
        ax.plot(eirps, curves[k][1], "o-", color=COL[k], lw=2.2,
                label=f"{STD[k]} - floor ON")
        ax.plot(eirps, curves[k][2], "x--", color=COL[k], lw=1.4, ms=9, mew=2,
                alpha=0.85, label=f"{STD[k]} - floor OFF (control)")
    ax.set_xlabel("Illuminator EIRP [dBm]"); ax.set_ylabel("P(hit in the ghost cell)")
    ax.set_ylim(-0.05, 1.16); ax.grid(alpha=0.3); ax.legend(fontsize=7.4, loc="upper left", ncol=1)
    ax.set_title("(b) The ghost cell fires - MORE with the floor OFF", fontsize=11.5)
    ax.text(0.97, 0.34,
            "5G: the CONTROL (floor OFF, dashed)\nfires at even LOWER EIRP than\n"
            "floor ON. Adding the ghost does not\ncreate those hits - it partially\n"
            "CANCELS them (coherent sum).\n\n$\\Rightarrow$ the hits are the TARGET's own\n"
            "sidelobes. There is no phantom.",
            transform=ax.transAxes, ha="right", fontsize=8.2, color="#c62828",
            bbox=dict(fc="#fff8e1", ec="#c62828", alpha=0.95, boxstyle="round,pad=0.4"))

    # (c) 왜 안 찍히나 — 393 MHz(유령이 분해된 경우)에서도 CA-CFAR 가 가린다
    ax = axes[2]
    wf2 = nr_fr2()
    c2 = build_cpi(wf2, M=M, ghost_on=True)
    rng = np.random.default_rng(7)
    noise = np.sqrt(0.5) * (rng.standard_normal(len(c2["surv"])) +
                            1j * rng.standard_normal(len(c2["surv"])))
    can = ECACanceller(c2["ref_cpi"], c2["n_taps"])
    Rb, f_d, rd = range_doppler(can.cancel(c2["surv"] + noise), c2["ref_cpi"], c2["fs"],
                                c2["M"], n_range=c2["n_range"])
    _, thr, _ = ca_cfar_2d(rd, pfa=1e-4)
    di = int(np.argmin(np.abs(f_d - c2["true_fd"])))
    pk = rd[di].max()
    ax.plot(Rb, 20 * np.log10(rd[di] / pk + 1e-12), color="#7b1fa2", lw=1.9,
            label="range cut at the target Doppler")
    ax.plot(Rb, 20 * np.log10(thr[di] / pk + 1e-12), color="#c62828", lw=1.6, ls="--",
            label="CA-CFAR threshold")
    ax.axvline(c2["true_Rb"], color="k", ls=":", lw=1.1)
    ax.axvline(c2["ghost"]["rb_m"], color="#ff1744", ls=":", lw=1.4)
    ax.text(c2["true_Rb"], 3, " target", rotation=90, fontsize=8.5, va="bottom")
    ax.text(c2["ghost"]["rb_m"], 3, " ghost", rotation=90, fontsize=8.5, va="bottom",
            color="#ff1744")
    gi = int(np.argmin(np.abs(Rb - c2["ghost"]["rb_m"])))
    ax.annotate("the ghost peak is REAL here\nbut sits UNDER the CFAR threshold:\n"
                "the strong target is inside the\nCFAR training window (masking)",
                xy=(Rb[gi], 20 * np.log10(rd[di, gi] / pk)),
                xytext=(c2["true_Rb"] + 7.5, -26), fontsize=8.6, color="#c62828",
                arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.1))
    ax.set_xlim(c2["true_Rb"] - 9, c2["true_Rb"] + 19); ax.set_ylim(-42, 10)
    ax.set_xlabel("Bistatic range Rb [m]"); ax.set_ylabel("level [dB re peak]")
    ax.set_title(f"(c) Even at {wf2.bw_hz/1e6:.0f} MHz: CFAR masks the ghost", fontsize=11.5)
    ax.legend(fontsize=8.5, loc="upper right"); ax.grid(alpha=0.28)

    fn = os.path.join(outdir, "report4_detection.png")
    fig.savefig(fn, dpi=130); plt.close(fig)
    print("[r4]", os.path.relpath(fn, ROOT))
    return fn, curves


# =========================================================================== #
#  ⑤ 추적 GIF — 좌: Sionna RT 렌더 / 우: Sionna PHY 거리-도플러
# =========================================================================== #
def _trajectory(n, speed=4.0):
    P0 = np.array([16.0, 5.0, 6.0]); C = np.array([25.0, 10.0, 5.0]); P1 = np.array([18.0, 15.0, 6.5])
    t = np.linspace(0, 1, n)[:, None]
    pos = (1 - t) ** 2 * P0 + 2 * (1 - t) * t * C + t ** 2 * P1
    d = 2 * (1 - t) * (C - P0) + 2 * t * (P1 - C)
    vel = d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-9) * speed
    return pos, vel


def gif_tracking(outdir=FIG, n_frames=20, M=24, fps=6, spp=192):
    """드론이 챔버를 날며: (좌) Sionna RT 가 매 프레임 경로를 다시 추적해 렌더,
    (우) Sionna PHY 가 합성한 감시신호의 거리-도플러 + CFAR + 유령."""
    import render_rt as R
    import sionna.rt as rt
    wf = waveforms()["nr"]
    pos, vel = _trajectory(n_frames)
    fdir = os.path.join(REND, "r4_flight")
    os.makedirs(fdir, exist_ok=True)
    solver = rt.PathSolver()
    frames = []
    print(f"[r4-gif] {n_frames} 프레임 (Sionna RT 렌더 + Sionna PHY 신호)…")
    for i in range(n_frames):
        sc = R.make_scene(drone=DRONE, tgt=tuple(map(float, pos[i])), cutaway=True,
                          vel=tuple(map(float, vel[i])))
        paths = solver(sc, max_depth=1, los=True, specular_reflection=True,
                       diffuse_reflection=False, refraction=False,
                       samples_per_src=800_000, seed=1)
        png = os.path.join(fdir, f"f{i:03d}.png")
        sc.render_to_file(camera=R.cam(*R.CAMS["wide"]), filename=png, num_samples=spp,
                          resolution=(900, 680), paths=paths, fov=70.0)
        c = build_cpi(wf, tgt=pos[i], vel=vel[i], M=M, ghost_on=True)
        rng = np.random.default_rng(100 + i)
        noise = np.sqrt(0.5) * (rng.standard_normal(len(c["surv"])) +
                                1j * rng.standard_normal(len(c["surv"])))
        Rb, f_d, rd, det = detect(c, c["surv"] + noise)
        frames.append((png, Rb, f_d, 20 * np.log10(rd / rd.max() + 1e-9), det,
                       c["true_Rb"], c["true_fd"], c["ghost"]["rb_m"], c["ghost"]["fd"]))
        if i % 5 == 0:
            print(f"  frame {i:2d}/{n_frames}")

    fig = plt.figure(figsize=(13.6, 5.6))
    axl = fig.add_subplot(1, 2, 1); axr = fig.add_subplot(1, 2, 2)
    hist = []

    def upd(i):
        png, Rb, f_d, rdb, det, tRb, tfd, gRb, gfd = frames[i]
        axl.clear(); axl.imshow(mpimg.imread(png)); axl.axis("off")
        axl.set_title(f"Sionna RT - frame {i+1}/{n_frames} (paths re-traced)", fontsize=10.5)
        axr.clear()
        axr.pcolormesh(Rb, f_d, rdb, cmap="turbo", vmin=-42, vmax=0, shading="auto")
        axr.plot(tRb, tfd, "o", mfc="none", mec="w", ms=14, mew=1.5)
        axr.plot(gRb, gfd, "s", mfc="none", mec="#ff1744", ms=14, mew=1.8)
        dd, dr = np.where(det)
        if len(dd):
            axr.plot(Rb[dr], f_d[dd], "x", color="w", ms=6, mew=1.2, alpha=0.8)
            hist.append((Rb[dr], f_d[dd]))
        axr.set_xlim(Rb[0], Rb[-1]); axr.set_ylim(f_d[0], f_d[-1])
        axr.set_xlabel("Bistatic range Rb [m]"); axr.set_ylabel("Doppler $f_d$ [Hz]")
        axr.set_title("Sionna PHY signal -> ECA / CAF / CFAR\n"
                      "circle = target   square = floor ghost   x = CFAR hit", fontsize=10)
        fig.suptitle("Tracking a drone in the chamber - the ghost tracks it too",
                     fontsize=13.5, fontweight="bold")
        return ()

    anim = FuncAnimation(fig, upd, frames=n_frames, blit=False)
    fn = os.path.join(outdir, "report4_tracking.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=88)
    plt.close(fig)
    print("[r4-gif]", os.path.relpath(fn, ROOT))
    return fn


# =========================================================================== #
def build_all(gif=True, rt_refresh=False):
    os.makedirs(FIG, exist_ok=True)
    if rt_refresh or not os.path.exists(RT_ENV):
        print("① Sionna RT — 챔버 환경 경로 실측")
        measure_rt_env()
    print("\n② Sionna PHY 체인 검증 (↔ 손합성 make_cpi)")
    crosscheck()
    print("\n③ 그림")
    fig_geometry()
    fig_rangedoppler()
    fig_ghost()
    fig_detection()
    if gif:
        gif_tracking()
    print("\nreport4 (Sionna) 그림 완료 →", os.path.relpath(FIG, ROOT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--rt", action="store_true", help="RT 환경경로 재측정")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    if a.only:
        globals()[a.only]()
    else:
        build_all(gif=a.gif, rt_refresh=a.rt)
