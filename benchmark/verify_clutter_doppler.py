# -*- coding: utf-8 -*-
"""
verify_clutter_doppler.py — [E3] cold clutter 도플러퍼짐 + hot clutter + 진폭 스윕
================================================================================
질문(정독노트 §6-2): **"클러터에 도플러퍼짐을 주면 '죽은 파라미터' 결론이 살아남는가?"**
답(측정): **아니다 — SCR 항등식은 도플러 즉시 죽고, 잔류가 진폭에 amp² 로 복귀한다.**
나아가(C4) **움직이는 클러터는 표적셀에 가짜 검출을 만든다** — 표적을 −80 dB 로 지워도 표적셀 CFAR 가
울리고(클러터 링이 표적 거리빈을 bracket), 클러터를 빼면 0 이 된다. 특히 저속 드론(fd < 클러터밴드)은
움직이는 클러터와 분간되지 않는다(서베이 §V-A4 경고 재현).

Clutter-Aware ISAC 서베이(§V-A4, Proc. IEEE 114:52-91, 2026)는 정적-클러터 전제를 부정한다:
  "the cold clutter is modeled as a collection of C = 100 scatterers uniformly distributed
   over four iso-range rings ... their radial velocities are uniformly distributed over
   [-1, 1] m/s to represent slow-moving environmental clutter."

■ '죽은 파라미터'의 진짜 메커니즘 — 두 개의 서로 다른 항등식을 구분한다 (측정으로 확정)
  verify_eca.json S5 의 `scr_span=3.4e-9` 과 이 파일의 zero-dop 대조군은 **같은 숫자가 나오지만
  메커니즘이 다르다.** 반드시 구분해 서술할 것:
    · verify_eca S5 : 클러터를 **ref_frame(파일럿)** 으로 반사 → 지연복제가 정확히 ECA 기저
      span(X) 안 → (I−P)c ≈ 0, ECA 가 진폭 무관하게 −300 dB 로 소거. **진짜 ECA span(X) 항등식.**
    · 이 파일 : 설계근거(d)대로 클러터를 **tx_frame(파일럿+데이터)** 로 반사(환경은 방사 전체를
      되쏜다). ECA 기저는 파일럿뿐이라 데이터 성분이 span(X) 밖 → ECA 는 **~1.4 dB 만** 지운다
      (도플러 유무와 거의 무관, 측정 확인). 그런데도 zero-dop 이 '죽는' 이유는 ECA 가 아니라
      **0-도플러 노치**다: 정적 잔류가 RD 맵 0-도플러 능선(zd±1)에 99.99% 앉고, det[zd,:]=False
      마스크 + measure_scr(표적셀 fd≠0 에서 측정)가 그걸 배제한다.
  도플러가 실리면 잔류가 노치 밖으로 새어(off-notch ~8%) 표적 도플러대에 침입 → SCR·ref-region 이
  **진폭 의존으로 복귀**(amp² 정확). ⚠ 그러니 "cold 이 span(X) 안이라 ECA 가 진폭 무관 소거"는
  이 파일에 틀렸다 — 참인 문장은 "0-도플러 노치가 정적 잔류를 배제, 도플러가 잔류를 노치 밖으로
  이동"이다. (mechanism_probe: eca_resid_db·notch_frac 로 JSON 에 영속화.)

■ 설계 결정 — **make_cpi 를 한 줄도 고치지 않는다**
  cold clutter 산란체 n 은 물리적으로  β_n·δ(τ−τ_n)·exp(j2πf_{d,n}·t)  이고, 이는
  make_cpi 의 기존 `ghosts=((τ,f_d,amp),…)` 루프(passive_process.py:68-69)와 **문자
  그대로 같다**. 그래서 새 인자 없이, 이 신규 파일이 자기 CPI 를 선형 합성하되
  cold clutter 성분을 기존 ghosts 인자로 주입한다(옵션②). 커널(make_cpi·ECACanceller·
  range_doppler·ca_cfar_2d·measure_scr)은 전부 import 재사용.
    surv_det = tgt_det + dpi_det + clut_cpi(tx_frame, ghosts=cold)   ← 선형 중첩
  → report01~12 는 이 파일을 부르지 않고 ghosts 기본값 () 그대로라 산출 비트 불변.

■ 정직성 두 축(서베이 규약)
  · scnr_in [dB]  = 억제 前  10log10(P_echo/(P_clutter+P_hot+P_noise))  ← DPI 는 제외(별도 축)
                    ⚠ "SCNR" 이지만 DPI(패시브 지배간섭, ~50 dB)는 분모에 없다 = pre-ECA, DPI-제외.
  · scr_out [dB]  = 억제 後  measure_scr(...)                          ← 우리 기존 헤드라인
  cold(도플러퍼짐) vs zero-dop(fd 전부 0, 옛 결과 재현) 대조군을 **동일 산란체·동일 시드**로
  나란히 돌려, SCR 이 도플러 하에서만 진폭 의존으로 복귀하는지를 격리한다.
  CNR 앵커는 기대공식이 아니라 **실현전력을 측정해 재스케일**(라벨=실현, anchor_cold_clutter_empirical).

실행:
  전체 (5G/WiFi/LTE → outputs):   ~/.venvs/py312/bin/python benchmark/verify_clutter_doppler.py
  스모크 (5G only → /tmp):        ... benchmark/verify_clutter_doppler.py --smoke
GPU: σ 는 mavic4pro SBR 캐시 조회라 GPU-free. (캐시 미스만 SIONNA2_GPU=3 필요.)
출력: outputs/verify_clutter_doppler.json + outputs/figures/verify_clutter_doppler.png
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from passive_process import (make_cpi, ECACanceller, range_doppler,        # noqa: E402
                             ca_cfar_2d)
from bistatic_scene import bistatic_params, C0                             # noqa: E402
from geometry import TX, RX, SPEED                                         # noqa: E402
from verify_eca import Setup, waveforms, M_DEF, DRONE                      # noqa: E402
from run_min_cell import measure_scr                                       # noqa: E402

OUT_JSON = os.path.join(_ROOT, "outputs", "verify_clutter_doppler.json")
OUT_FIG = os.path.join(_ROOT, "outputs", "figures", "verify_clutter_doppler.png")

# RT 실측 챔버 최강 바닥탭(직접파 대비) — cold clutter 총전력 앵커(정독노트 §6-2, geometry.py)
RT_FLOOR_TOP_DB = -9.8            # 19.3 ns 개별탭은 −14.7 dB; 최강 탭 −9.8 dB


def _lin(db):
    return 10.0 ** (db / 10.0)


def pw(x):
    return float(np.mean(np.abs(x) ** 2))


def db10(x):
    return float(10.0 * np.log10(max(float(x), 1e-300)))


# =========================================================================== #
#  항목 1 — cold clutter 도플러퍼짐 모델 (서베이 §V-A4)
# =========================================================================== #
def _floor_ray_root(tx, rx, g0, d, s, rmax=48.0, ngrid=480):
    """바닥(z=0) 위 반직선 p(r)=g0+r·d 에서 R1(p)+R2(p)=s 인 최초 교점 p 를 찾는다.
    (등-Rb 타원체 ∩ 바닥평면 = 등-Rb 곡선. 그 위에 방위 d 로 산란체를 놓는다.)
    교점이 없으면 None."""
    r = np.linspace(0.05, rmax, ngrid)
    pts = g0[None, :] + r[:, None] * d[None, :]                 # z=0 유지(g0,d 모두 z=0)
    f = np.linalg.norm(pts - tx, axis=1) + np.linalg.norm(pts - rx, axis=1) - s
    sgn = np.sign(f)
    idx = np.where(sgn[:-1] * sgn[1:] < 0)[0]
    if not len(idx):
        return None
    i = idx[0]
    r0 = r[i] - f[i] * (r[i + 1] - r[i]) / (f[i + 1] - f[i] + 1e-30)  # 선형보간
    return g0 + r0 * d


def cold_clutter_scatterers(tx, rx, tgt, fc, *, C=100,
                            ring_offsets_m=(-1.5, -0.6, +0.6, +1.5),
                            v_max=1.0, az_range_deg=(-90.0, 90.0),
                            floor_z=0.0, chamber=(30.0, 20.0, 11.0),
                            max_tries=40, rng=None):
    """서베이 §V-A4 정확 처방. 반환 (scat, diag).
      scat : list[(tau_s, fd_hz, beta_complex)]  — make_cpi 의 ghosts 형식 그대로
      · C 개 산란체를 표적 바이스태틱거리 Rb0 을 **bracket 하는 4개 iso-Rb 링**
        (가까운 쪽 2·먼 쪽 2 = ring_offsets_m)에 균등 배분.
      · 각 산란체: 방위 φ~U[az_range]를 **바이스태틱 이등분선 기준**으로 챔버 바닥(z=floor_z)
        위 iso-Rb 곡선에 배치(챔버 벽 밖이면 방위 리샘플). semi-anechoic → 바닥이 유일 강반사면.
      · 반경속도 v~U[-v_max,+v_max] m/s(이등분선 성분) → fd = v·|û1+û2|/λ (bistatic_params 규약,
        산란체 자신의 국소 기하 |û1+û2| 사용).
      · β_c~CN(0,1)(여기선 단위분산; 스케일은 anchor 단계에서 RT 실측으로 고정)."""
    rng = rng or np.random.default_rng(0)
    tx = np.asarray(tx, float); rx = np.asarray(rx, float); tgt = np.asarray(tgt, float)
    lam = C0 / fc
    L = float(np.linalg.norm(tx - rx))
    p = bistatic_params(tx, rx, tgt, (0.0, 0.0, 0.0), fc)
    Rb0 = float(p["Rb"])
    # 바이스태틱 이등분선을 바닥평면에 사영 → 방위 0 방향
    b = p["u1"] + p["u2"]
    b_xy = np.array([b[0], b[1], 0.0])
    nb = np.linalg.norm(b_xy)
    b_xy = b_xy / nb if nb > 1e-9 else np.array([1.0, 0.0, 0.0])
    g0 = np.array([tgt[0], tgt[1], floor_z])                    # 표적 지상투영(링 중심 기준점)
    W, D = chamber[0], chamber[1]

    # 링별 개수(균등 배분, 나머지는 앞 링부터)
    nring = len(ring_offsets_m)
    per = [C // nring + (1 if k < C % nring else 0) for k in range(nring)]

    scat = []
    positions = []
    ring_of = []
    placed_per_ring = [0] * nring
    az_placed = []
    fd_list = []
    a_lo, a_hi = math.radians(az_range_deg[0]), math.radians(az_range_deg[1])
    for ir, off in enumerate(ring_offsets_m):
        s = L + Rb0 + off                                      # R1+R2 목표(=베이스라인+Rb)
        tau = (Rb0 + off) / C0                                 # 링이 지연을 결정(방위 무관)
        for _ in range(per[ir]):
            pos = None
            for _t in range(max_tries):
                phi = rng.uniform(a_lo, a_hi)
                cphi, sphi = math.cos(phi), math.sin(phi)
                d = np.array([cphi * b_xy[0] - sphi * b_xy[1],
                              sphi * b_xy[0] + cphi * b_xy[1], 0.0])
                cand = _floor_ray_root(tx, rx, g0, d, s)
                if cand is None:
                    continue
                if 0.0 <= cand[0] <= W and 0.0 <= cand[1] <= D:  # 챔버 벽 안
                    pos = cand
                    az_placed.append(math.degrees(phi))
                    break
            if pos is None:
                continue                                       # 이 링·방위엔 산란체 없음
            u1n = (tx - pos); u1n /= max(np.linalg.norm(u1n), 1e-9)
            u2n = (rx - pos); u2n /= max(np.linalg.norm(u2n), 1e-9)
            kn = float(np.linalg.norm(u1n + u2n)) / lam        # [Hz per (m/s)] 국소
            v = rng.uniform(-v_max, v_max)
            fd = v * kn
            beta = (rng.standard_normal() + 1j * rng.standard_normal()) / math.sqrt(2.0)
            scat.append((float(tau), float(fd), complex(beta)))
            positions.append(pos.tolist()); ring_of.append(ir)
            placed_per_ring[ir] += 1; fd_list.append(fd)

    fd_arr = np.array(fd_list) if fd_list else np.array([0.0])
    diag = dict(
        C_requested=int(C), C_placed=len(scat), Rb0_m=Rb0, L_m=L, lam_m=lam,
        ring_offsets_m=list(ring_offsets_m), placed_per_ring=placed_per_ring,
        v_max_ms=v_max, fd_band_hz=float(np.max(np.abs(fd_arr))),
        fd_std_hz=float(np.std(fd_arr)),
        ring_tau_ns=[float((Rb0 + o) / C0 * 1e9) for o in ring_offsets_m],
        positions=positions, ring_of=ring_of)
    return scat, diag


def anchor_cold_clutter(scat, dpi_amp, *, cnr_db=RT_FLOOR_TOP_DB):
    """CNR 을 자유 손잡이가 아니라 RT 실측값으로 고정한다.
    앙상블 총 전력비(clutter/direct)를 RT 최강 바닥탭 cnr_db 에 맞춰 β 전체를 스칼라 스케일.
      make_cpi(tx_frame, ghosts=cold) 에서 ghost n 의 전력 ≈ |amp_n|²·pw(tx_frame),
      DPI 전력 = dpi²·pw(tx_frame) → 비 = Σ|amp_n|²/dpi² = 10^(cnr_db/10).
      amp_n = s·β_n,  s = dpi·10^(cnr_db/20)/sqrt(Σ|β_n|²).
    반환 (cold_amped[(tau,fd,amp_complex)], scale_s).
    ⚠ 규약: cnr_db 는 총 클러터/직접파 **전력비**(dB). RT 최강탭(−9.8 dB, 진폭 20log10)의
      전력을 100개 이동 산란체에 분산시킨 앵커 — 40 dB 스윕이 이 기준선 주위를 훑는다."""
    if not scat:
        return [], 0.0
    beta = np.array([b for _, _, b in scat])
    s = dpi_amp * (10.0 ** (cnr_db / 20.0)) / math.sqrt(float(np.sum(np.abs(beta) ** 2)) + 1e-30)
    cold = [(t, f, complex(s * b)) for (t, f, b) in scat]
    return cold, float(s)


def build_clut_cpi(S, cold):
    """cold clutter 산란체 → 결정론 감시신호 성분(길이 M·Lf). tx_frame(파일럿+데이터) 반사.
    ⚠ make_cpi 의 delayed() 는 ghost 마다 전체 CPI FFT 를 한다(100 ghost = 200 FFT). 비싸므로
    **한 번만** 만들고 선형성(clut(scale)=scale·clut)으로 스윕 전체가 재사용한다."""
    clut, _ = make_cpi(S.tx_frame, S.M, S.fs, 0.0, 0.0, a_tgt=0.0, dpi_amp=0.0,
                       clutter=(), ghosts=tuple(cold), abs_noise=True, noise_var=0.0)
    return clut


def _dpi_power(S):
    dpi, _ = make_cpi(S.tx_frame, S.M, S.fs, 0.0, 0.0, a_tgt=0.0, dpi_amp=S.dpi,
                      clutter=(), abs_noise=True, noise_var=0.0)
    return pw(dpi)


def anchor_cold_clutter_empirical(S, scat, *, cnr_db=RT_FLOOR_TOP_DB):
    """**경험적 앵커** — 실현전력을 측정해 재스케일 → 실현 CNR == cnr_db (라벨=실현, 시드 무관).
    같은 지연을 공유하는 링내 산란체의 코히어런트 합 때문에 실현 전력은 기대공식(Σ|β|²) 주위로
    ±2~3 dB 요동한다(감사 물리 결함2) → 실측 후 보정해 라벨=실현을 보장한다.
    반환 (cold[(tau,fd,amp)], scale, realized_cnr_db, clut_dop[precomputed]).
    ⚠ 100-ghost make_cpi 는 **딱 한 번**만 만들고(비쌈) 선형성으로 재스케일한다."""
    cold0, s0 = anchor_cold_clutter(scat, S.dpi, cnr_db=cnr_db)
    if not cold0:
        return [], 0.0, None, None
    clut0 = build_clut_cpi(S, cold0)
    p_dpi = _dpi_power(S)
    r0 = db10(pw(clut0) / (p_dpi + 1e-300))
    corr = 10.0 ** ((cnr_db - r0) / 20.0)
    cold = [(t, f, complex(corr * a)) for (t, f, a) in cold0]
    clut_dop = corr * clut0                                       # 선형 → 재빌드 불필요
    r1 = db10(pw(clut_dop) / (p_dpi + 1e-300))                    # 실현 CNR(측정, ≈cnr_db)
    return cold, float(s0 * corr), float(r1), clut_dop


def eca_mechanism_probe(S, clut_dop, clut_zero):
    """'죽은 파라미터'의 메커니즘을 영속화한다(감사 물리 결함1 정정 근거).
    **미리 만든** clut(도플러/제로도플러)을 ECA(파일럿 기저)에 통과시켜 잔류비를 재고, 잔류가
    RD 맵 0-도플러 노치(zd±1)에 얼마나 앉는지 잰다.
      · eca_resid_db ≈ −1.4 dB (도플러 무관) → ECA 는 tx-클러터를 거의 못 지운다.
      · zero-dop notch_frac ≈ 1.0 (전부 노치 안, 배제됨) / doppler 는 노치 밖으로 샌다.
    ⇒ 죽음/부활을 가르는 건 ECA 사영이 아니라 0-도플러 노치다."""
    ref_cpi = np.tile(S.ref_frame, S.M)
    canc = ECACanceller(ref_cpi, S.n_taps)
    out = {}
    for tag, clut in (("zero_dop", clut_zero), ("doppler", clut_dop)):
        res = canc.cancel(clut)
        Rb, f_d, rd = range_doppler(res, ref_cpi, S.fs, S.M, n_range=S.n_range)
        zd = int(np.argmin(np.abs(f_d)))
        P = rd ** 2
        notch = float(P[max(0, zd - 1):zd + 2, :].sum() / (P.sum() + 1e-300))
        out[tag] = dict(eca_resid_db=db10(pw(res) / (pw(clut) + 1e-300)),
                        notch_frac=notch, off_notch_frac=float(1.0 - notch))
    return out


def estimate_coherence_bandwidth(cold_amped, bw_hz, n_f=513):
    """평균 채널전달함수 H(f)=Σ amp_n·exp(−j2πf·τ_n) 에서 주파수 상관 ρ_f(Δf) 를 재고,
    |ρ_f|=1/e 지점을 B_c 로 본다. 1/(2π·τ_rms) 와 대조(진단). B_c 는 4링 지연폭에서 창발."""
    if not cold_amped:
        return dict(Bc_hz=None, one_over_2pi_tau_rms_hz=None,
                    delay_spread_ns=None)
    taus = np.array([t for t, _, _ in cold_amped])
    amps = np.array([a for _, _, a in cold_amped])
    f = np.linspace(-bw_hz / 2.0, bw_hz / 2.0, n_f)
    H = (amps[None, :] * np.exp(-2j * np.pi * np.outer(f, taus))).sum(1)
    df = float(f[1] - f[0])
    rho = np.empty(n_f)
    for k in range(n_f):
        a = H[:n_f - k]; b = H[k:]
        num = np.vdot(a, b)
        den = math.sqrt(abs(np.vdot(a, a) * np.vdot(b, b))) + 1e-30
        rho[k] = abs(num) / den
    below = np.where(rho < math.exp(-1.0))[0]
    Bc = float(below[0] * df) if len(below) else float(f[-1] - f[0])
    w = np.abs(amps) ** 2; w = w / (w.sum() + 1e-30)
    tau_bar = float(np.sum(w * taus))
    tau_rms = math.sqrt(max(float(np.sum(w * (taus - tau_bar) ** 2)), 0.0))
    return dict(Bc_hz=Bc, one_over_2pi_tau_rms_hz=(1.0 / (2 * math.pi * tau_rms) if tau_rms > 0 else None),
                delay_spread_ns=tau_rms * 1e9)


# =========================================================================== #
#  항목 3 — hot clutter (외부 비협조 이미터, 독립 파형)
# =========================================================================== #
def _ofdm_indep(fs, bw_hz, N, rng, nfft=1024, cp_frac=0.07):
    """독립 OFDM 파형(단위 전력, 길이 N). 우리 ref 와 **무상관** — QPSK 심볼이 매번 랜덤."""
    n_used = int(nfft * bw_hz / fs)
    ncp = int(nfft * cp_frac)
    half = n_used // 2
    idx = np.r_[np.arange(1, half + 1), np.arange(nfft - half, nfft)]   # DC·엣지 제외
    nsym = int(np.ceil(N / (nfft + ncp))) + 1
    out = []
    for _ in range(nsym):
        X = np.zeros(nfft, complex)
        q = rng.integers(0, 4, size=len(idx))
        X[idx] = np.exp(1j * (np.pi / 4 + np.pi / 2 * q))
        x = np.fft.ifft(X) * math.sqrt(nfft)
        out.append(np.concatenate([x[-ncp:], x]))
    sig = np.concatenate(out)[:N]
    return sig / (math.sqrt(pw(sig)) + 1e-30)


def hot_clutter_signal(fs, bw_hz, N, *, inr_db=20.0, noise_var=1.0,
                       kind="ofdm_indep", rng=None):
    """외부 비협조 이미터 1기 → RX 시간영역 간섭 벡터(길이 N).
    inr_db : 간섭/열잡음 전력비[dB] → 진폭 = sqrt(10^(inr/10)·noise_var).
    ⚠ 우리 ref 의 지연복제가 **아니다** → make_cpi ghosts/clutter 로 넣지 않고 surv 에 직접 가산.
      독립 파형이라 (a) ECA span(X) 밖, (b) 정합필터 코히어런트 이득 없음, (c) 0-도플러에
      갇히지 않음 → 서베이: 'not confined to fD=0, cannot be removed by slow-time
      subtraction alone.'"""
    rng = rng or np.random.default_rng(0)
    amp = math.sqrt(_lin(inr_db) * noise_var)
    if kind == "ofdm_indep":
        base = _ofdm_indep(fs, bw_hz, N, rng)
    else:                                                     # 대역제한 백색(대체)
        w = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / math.sqrt(2)
        Wf = np.fft.fft(w); fr = np.fft.fftfreq(N, d=1 / fs)
        Wf[np.abs(fr) > bw_hz / 2] = 0.0
        base = np.fft.ifft(Wf); base = base / (math.sqrt(pw(base)) + 1e-30)
    return amp * base


# =========================================================================== #
#  CPI 자기조립 (make_cpi 무수정) + Monte-Carlo 검출/측정
# =========================================================================== #
def assemble_surv_det(S, cold=(), tgt_fd=None, clut_cpi=None, echo_scale=1.0):
    """결정론 감시신호 = 표적에코 + DPI(+정적 RT클러터) + cold(도플러퍼짐, ghosts 주입).
    run_min_cell.run_cell 과 **동일 규약**: 표적·에코는 ref_frame(파일럿 코히어런트),
    DPI·클러터는 tx_frame(파일럿+데이터). cold=()·tgt_fd=None·clut_cpi=None·echo_scale=1 이면
    run_cell 과 비트일치.
    tgt_fd     : 표적 도플러 override(C4 속도 스윕용). None 이면 S.st.fd(벤치마크 동작점).
    echo_scale : 표적 에코 진폭 배율(C4 near-threshold 스윕용). 1.0=벤치 동작점.
    clut_cpi   : **미리 만든** cold-clutter CPI(길이 M·Lf). 주면 make_cpi ghost 빌드를 건너뛴다
                 (100-ghost FFT 비용 회피 — 선형성으로 스윕이 재사용). 주면 cold 는 무시."""
    fs, M = S.fs, S.M
    fd = S.st.fd if tgt_fd is None else float(tgt_fd)
    tgt_det, ref_cpi = make_cpi(S.ref_frame, M, fs, S.st.tau, fd, a_tgt=S.a_tgt * float(echo_scale),
                                dpi_amp=0.0, clutter=(), abs_noise=True, noise_var=0.0)
    dpi_det, _ = make_cpi(S.tx_frame, M, fs, 0.0, 0.0, a_tgt=0.0, dpi_amp=S.dpi,
                          clutter=S.clutter_abs, abs_noise=True, noise_var=0.0)
    surv_det = tgt_det + dpi_det
    p_clut = 0.0
    if clut_cpi is not None:
        surv_det = surv_det + clut_cpi
        p_clut = pw(clut_cpi)
    elif cold:
        clut_cpi, _ = make_cpi(S.tx_frame, M, fs, 0.0, 0.0, a_tgt=0.0, dpi_amp=0.0,
                               clutter=(), ghosts=tuple(cold),
                               abs_noise=True, noise_var=0.0)
        surv_det = surv_det + clut_cpi
        p_clut = pw(clut_cpi)
    return dict(surv_det=surv_det, ref_cpi=ref_cpi, tgt_fd=fd,
                p_echo=pw(tgt_det), p_dpi=pw(dpi_det), p_clut=p_clut)


def run_clutter_cell(S, cold=(), hot_inr_db=None, doppler_notch=True,
                     N=60, pfa=1e-4, noise_var=1.0, seed0=0, tgt_fd=None, clut_cpi=None,
                     echo_scale=1.0):
    """자기조립 CPI → N-trial Monte-Carlo. 커널은 전부 import(ECACanceller·range_doppler·
    ca_cfar_2d·measure_scr). 반환: Pd·SCR(억제 후)·scnr_in(억제 전)·ref-region 전력 등.
    doppler_notch : run_min_cell 의 det[zd,:]=False 를 'MTI prenull' 로 재명명(동일 동작).
      ⚠ det[zd,:]=False 는 **0-도플러 한 빈만** null 한다 → 노치 반폭은 dfd/2(±1빈이 아님).
    scnr_in : 억제 前 10log10(P_echo/(P_clut+P_hot+P_noise)). **DPI 는 분모에서 제외**(별도 축).
      hot 이 있으면 P_hot=10^(inr/10)·noise_var 를 분모에 포함(감사 결함1 정정 — 없으면
      cold_only 와 cold+hot 의 scnr_in 이 항등적으로 같아진다)."""
    fd_meas = S.st.fd if tgt_fd is None else float(tgt_fd)
    comp = assemble_surv_det(S, cold, tgt_fd=tgt_fd, clut_cpi=clut_cpi, echo_scale=echo_scale)
    surv_det, ref_cpi = comp["surv_det"], comp["ref_cpi"]
    fs, M = S.fs, S.M
    canceller = ECACanceller(ref_cpi, S.n_taps)
    Ncpi = len(surv_det)
    nstd = math.sqrt(noise_var / 2.0)
    p_hot = (_lin(hot_inr_db) * noise_var) if hot_inr_db is not None else 0.0
    scnr_in = db10(comp["p_echo"] / (comp["p_clut"] + p_hot + noise_var))

    hits = 0
    scrs = []
    ref_pows = []                 # measure_scr 기준영역 전력(진폭의존 진단, 노치 무관)
    cfar_extra = 0                # 표적셀 밖 CFAR 히트 수(오검출 대리지표)
    example = None
    for k in range(N):
        rng = np.random.default_rng(seed0 + k)
        surv = surv_det + nstd * (rng.standard_normal(Ncpi) + 1j * rng.standard_normal(Ncpi))
        if hot_inr_db is not None:
            surv = surv + hot_clutter_signal(fs, S.wf.bw_hz, Ncpi,
                                              inr_db=hot_inr_db, noise_var=noise_var,
                                              rng=np.random.default_rng(10_000 + seed0 + k))
        res = canceller.cancel(surv)
        Rb, f_d, rd = range_doppler(res, ref_cpi, fs, M, n_range=S.n_range)
        scr, (ri, di) = measure_scr(Rb, f_d, rd, S.true_Rb, fd_meas)
        det, thr, _ = ca_cfar_2d(rd, pfa=pfa)
        zd = int(np.argmin(np.abs(f_d)))
        if doppler_notch:
            det[zd, :] = False                                 # MTI prenull (0-도플러 1빈만)
        hit = det[max(0, di - 1):di + 2, max(0, ri - 1):ri + 2].any()
        hits += int(hit)
        # 표적셀 ±1 밖 CFAR 히트(오검출 대리) — 노치·표적셀 제외
        det2 = det.copy(); det2[max(0, di - 1):di + 2, max(0, ri - 1):ri + 2] = False
        cfar_extra += int(det2.sum())
        # 기준영역 전력(0-도플러 능선·표적근방 제외) — 진폭의존을 노치와 독립으로 노출
        mask = np.ones_like(rd, bool)
        mask[max(0, zd - 1):zd + 2, :] = False
        mask[max(0, di - 3):di + 4, max(0, ri - 3):ri + 4] = False
        ref_pows.append(float(np.mean(rd[mask] ** 2)))
        scrs.append(scr)
        if k == 0:
            example = (Rb, f_d, rd, (ri, di))
    return dict(pd=hits / N, scr_mean=float(np.mean(scrs)), scr_std=float(np.std(scrs)),
                scnr_in_db=scnr_in, ref_region_pow=float(np.mean(ref_pows)),
                ref_region_db=db10(np.mean(ref_pows)),
                cfar_extra_per_trial=cfar_extra / N, p_hot=p_hot, tgt_fd_hz=fd_meas,
                p_echo=comp["p_echo"], p_clut=comp["p_clut"], p_dpi=comp["p_dpi"],
                N=N, M=M, example=example)


# =========================================================================== #
#  항목 2 — 40 dB 진폭 스윕 (핵심 시험) : cold(도플러) vs zero-dop 대조군
# =========================================================================== #
def sweep_clutter_amplitude(S, cold_anchor, clut_base, *, scales_db=(-np.inf, 0.0, 40.0),
                            doppler=True, N=60, pfa=1e-4, seed0=0):
    """RT 앵커 baseline × 10^(scale_db/20). scale_db=-inf → cold 없음(=옛 죽은파라미터 재현).
    doppler=True: cold 의 fd 유지(퍼짐) / False: fd 전부 0(대조군 — 정적 잔류가 0-도플러
    노치에 앉아 배제됨, ECA 가 아니라 노치가 죽인다).
    clut_base : **미리 만든** 앵커스케일 clut CPI(도플러 arm 이면 clut_dop, zero-dop arm 이면
      clut_zero). 스케일은 선형(clut_cpi=sc·clut_base)이라 100-ghost FFT 재빌드가 없다.
    **동일 산란체·동일 β·동일 시드**로 두 arm 을 비교해 '도플러가 유일 원인'임을 격리한다."""
    rows = []
    for sdb in scales_db:
        if not np.isfinite(sdb):
            clut_cpi = None
        else:
            clut_cpi = (10.0 ** (sdb / 20.0)) * clut_base
        r = run_clutter_cell(S, doppler_notch=True, N=N, pfa=pfa, seed0=seed0, clut_cpi=clut_cpi)
        rows.append(dict(scale_db=(None if not np.isfinite(sdb) else float(sdb)),
                         doppler=bool(doppler and np.isfinite(sdb)),
                         scr_out_db=r["scr_mean"], scr_std_db=r["scr_std"],
                         scnr_in_db=r["scnr_in_db"], pd=r["pd"],
                         ref_region_db=r["ref_region_db"],
                         cfar_extra=r["cfar_extra_per_trial"]))
    scrs = [x["scr_out_db"] for x in rows]
    return dict(rows=rows, doppler=doppler,
                scr_span_db=float(max(scrs) - min(scrs)),
                ref_span_db=float(max(x["ref_region_db"] for x in rows)
                                  - min(x["ref_region_db"] for x in rows)))


# =========================================================================== #
#  섹션 러너 (전체 실행용)
# =========================================================================== #
def prep_setup(S, rng_seed=1):
    """한 파형의 cold clutter 산란체 생성 + **경험적 앵커**(라벨=실현 CNR) + 결정론 clut CPI
    **미리 계산**(도플러/제로도플러). C1~C4 가 이 배열을 재사용해 100-ghost FFT 를 1회로 줄인다."""
    rng = np.random.default_rng(rng_seed)
    scat, diag = cold_clutter_scatterers(TX, RX, S.pos, S.wf.carrier_hz, rng=rng)
    cold, scale, cnr_real, clut_dop = anchor_cold_clutter_empirical(S, scat, cnr_db=RT_FLOOR_TOP_DB)
    clut_zero = build_clut_cpi(S, [(t, 0.0, a) for (t, f, a) in cold]) if cold else None
    return dict(S=S, scat=scat, diag=diag, cold=cold, scale=scale, cnr_real_db=cnr_real,
                clut_dop=clut_dop, clut_zero=clut_zero)


def sec_C1_cold_model(preps):
    out = []
    for p in preps:
        S, diag, cold = p["S"], p["diag"], p["cold"]
        bc = estimate_coherence_bandwidth(cold, S.wf.bw_hz)
        mech = eca_mechanism_probe(S, p["clut_dop"], p["clut_zero"])   # 메커니즘 영속화
        out.append(dict(
            name=S.wf.name, dfd_hz=S.dfd,
            notch_halfwidth_hz=S.dfd / 2.0,                 # 단일 0-도플러 빈 → 반폭 dfd/2 (감사 F3)
            notch_def="single zero-Doppler bin det[zd,:]=False (half-width dfd/2, not +/-1 bin)",
            fd_band_hz=diag["fd_band_hz"], fd_std_hz=diag["fd_std_hz"],
            fd_band_over_dfd=diag["fd_band_hz"] / S.dfd,
            C_placed=diag["C_placed"], placed_per_ring=diag["placed_per_ring"],
            ring_tau_ns=diag["ring_tau_ns"], Rb0_m=diag["Rb0_m"],
            anchor_scale=p["scale"], cnr_nominal_db=RT_FLOOR_TOP_DB,
            cnr_realized_db=p["cnr_real_db"], eca_mechanism=mech, **bc))
    return out


def sec_C2_amplitude_sweep(p, *, N=100, seed0=0):
    S, cold = p["S"], p["cold"]
    dop = sweep_clutter_amplitude(S, cold, p["clut_dop"], doppler=True, N=N, seed0=seed0)
    zero = sweep_clutter_amplitude(S, cold, p["clut_zero"], doppler=False, N=N, seed0=seed0)
    return dict(name=S.wf.name, diag=p["diag"], doppler=dop, zero_dop=zero)


def sec_C2b_M96(wf, *, N=60, seed0=0, rng_seed=1, M=96):
    """M=96 교차시험 — dfd 축소로 클러터밴드가 0-도플러 노치보다 넓어지면 SCR 이 더 무너지는지."""
    S = Setup(wf, M=M)
    rng = np.random.default_rng(rng_seed)
    scat, diag = cold_clutter_scatterers(TX, RX, S.pos, wf.carrier_hz, rng=rng)
    cold, _, cnr_real, clut_dop = anchor_cold_clutter_empirical(S, scat, cnr_db=RT_FLOOR_TOP_DB)
    dop = sweep_clutter_amplitude(S, cold, clut_dop, doppler=True, N=N, seed0=seed0)
    return dict(name=S.wf.name, M=M, dfd_hz=S.dfd, notch_halfwidth_hz=S.dfd / 2.0,
                fd_band_hz=diag["fd_band_hz"], fd_band_over_dfd=diag["fd_band_hz"] / S.dfd,
                cnr_realized_db=cnr_real, doppler=dop)


def sec_C3_hot_clutter(p, *, N=60, seed0=0):
    """hot clutter(독립 이미터). ⚠ 서베이 헤드라인은 **입력SCNR 의 cold→cold+hot 열화**지만,
    우리 scnr_in 은 pre-ECA·DPI제외 축이라 정확한 apples-to-apples 가 아니다(감사 F1). 그래서:
      · scnr_in 분모에 hot 전력을 포함(없으면 cold_only==cold+hot 로 무반응).
      · hot 을 두 레벨로: INR=20 dB(서베이류 약한 hot)와 **CNR-matched**(clutter/noise 와 동급)."""
    S, clut = p["S"], p["clut_dop"]
    cold_only = run_clutter_cell(S, hot_inr_db=None, N=N, seed0=seed0, clut_cpi=clut)
    cnr_to_noise_db = db10(cold_only["p_clut"])             # noise_var=1 → clutter/noise [dB]
    inr20 = run_clutter_cell(S, hot_inr_db=20.0, N=N, seed0=seed0, clut_cpi=clut)
    inrm = run_clutter_cell(S, hot_inr_db=cnr_to_noise_db, N=N, seed0=seed0, clut_cpi=clut)

    def row(r):
        return dict(scnr_in_db=r["scnr_in_db"], scr_out_db=r["scr_mean"], pd=r["pd"],
                    cfar_extra=r["cfar_extra_per_trial"], p_hot=r["p_hot"], p_clut=r["p_clut"])
    return dict(name=S.wf.name, clutter_to_noise_db=cnr_to_noise_db,
                hot_inr_matched_db=cnr_to_noise_db,
                cold_only=row(cold_only), cold_hot_inr20=row(inr20),
                cold_hot_cnrmatched=row(inrm),
                survey_ref=dict(cold_only=-45.9, cold_hot=-47.4, sionna_rt_sitespec=-63.5),
                scnr_in_def="echo/(clutter+hot+noise), pre-ECA, DPI-excluded",
                caveat="서베이(-45.9->-47.4)는 입력SCNR 축이라 우리 pre-ECA·DPI제외 값과 "
                       "정확한 apples-to-apples 아님 — hot 기여의 부호/방향만 대조.")


def sec_C4_target_speed(p, *, speeds_ms=(0.2, 0.6, 1.2, 2.0, 3.0), N=60, seed0=0,
                        notarget_db=-80.0):
    """★ H2 시험 — 표적 속도(호버~빠름) 스윕 하에서 '표적 검출'이 실제로 표적을 보는가, 아니면
    **움직이는 cold 클러터에 오염**되는가를 격리한다. 각 속도에서 3조건(전부 MTI 노치 on):
      (bench)         echo=1 + cold 클러터 — 정상 동작점.
      (notarget)      echo≈0(−80 dB) + cold 클러터 — 표적을 지워도 표적셀이 CFAR 를 울리면
                      그 검출은 **클러터가 만든 것**(표적 무관).
      (notgt_noclut)  echo≈0 + 클러터 없음 — 깨끗한 기준(잡음만 → Pd≈Pfa≈0).
    저속(fd < 클러터밴드 ±21 Hz)에서 pd_notarget ≈ pd_bench 면, 그 속도의 '검출'은 표적이 아니라
    클러터다 → **저속/호버 드론은 움직이는 클러터와 분간되지 않는다**(서베이 §V-A4 경고와 일치).
    ⚠ Pd '블라인드 존'을 노치 손실로 보이려던 앞선 설계는 실패했다 — 에코를 −86 dB 까지 낮춰도
    표적셀 CFAR 가 계속 울렸는데, 그건 노치가 아니라 **클러터가 표적셀을 울린 것**이었다(이 절이 그걸 증명)."""
    S, cold, clut = p["S"], p["cold"], p["clut_dop"]
    es0 = 10.0 ** (notarget_db / 20.0)
    rows = []
    for v in speeds_ms:
        fd = v * S.hz_per_ms
        bench = run_clutter_cell(S, doppler_notch=True, N=N, seed0=seed0, tgt_fd=fd,
                                 clut_cpi=clut, echo_scale=1.0)
        notgt = run_clutter_cell(S, doppler_notch=True, N=N, seed0=seed0, tgt_fd=fd,
                                 clut_cpi=clut, echo_scale=es0)
        clean = run_clutter_cell(S, doppler_notch=True, N=N, seed0=seed0, tgt_fd=fd,
                                 clut_cpi=None, echo_scale=es0)
        rows.append(dict(v_ms=float(v), fd_hz=float(fd), fd_over_dfd=float(fd / S.dfd),
                         in_clutter_band=bool(abs(fd) <= p["diag"]["fd_band_hz"]),
                         pd_bench=bench["pd"], pd_notarget=notgt["pd"], pd_notgt_noclut=clean["pd"],
                         scr_bench=bench["scr_mean"],
                         cfar_extra_bench=bench["cfar_extra_per_trial"],
                         cfar_extra_notarget=notgt["cfar_extra_per_trial"]))
    return dict(name=S.wf.name, dfd_hz=S.dfd, hz_per_ms=S.hz_per_ms,
                fd_band_hz=p["diag"]["fd_band_hz"], notarget_db=notarget_db,
                bench_speed_ms=SPEED, rows=rows)


# =========================================================================== #
#  make_cpi 불변 증명 — 3파형 (감사 지적3: 5G 단일 → 전 파형)
# =========================================================================== #
def prove_make_cpi_unchanged(setups, verbose=True, N=40):
    """① ghosts=() 가 no-op(비트일치)  ② none-point(cold=()) 가 run_cell 과 비트일치.
    setups = [(name, Setup), ...]. 파형마다 검증(WiFi 패딩·LTE 저대역 경로 포함)."""
    from run_min_cell import run_cell, EIRP_DBM
    from link_budget import LinkBudget
    from channel import AnalyticChannel, rt_chamber_clutter
    from scenarios import radial
    from geometry import CENTER, SPAN, CH_CLUTTER_RATIO
    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)
    per = []
    allmatch = True
    for name, S in setups:
        fs, M = S.fs, S.M
        s1, _ = make_cpi(S.ref_frame, M, fs, S.st.tau, S.st.fd, a_tgt=1.0, dpi_amp=30.0,
                         clutter=S.clutter_abs, abs_noise=True, noise_var=0.0)
        s2, _ = make_cpi(S.ref_frame, M, fs, S.st.tau, S.st.fd, a_tgt=1.0, dpi_amp=30.0,
                         clutter=S.clutter_abs, abs_noise=True, noise_var=0.0, ghosts=())
        ghosts_noop = bool(np.array_equal(s1, s2))
        ch = AnalyticChannel(clutter=rt_chamber_clutter(S.wf.carrier_hz) or CH_CLUTTER_RATIO)
        rc = run_cell(S.wf, DRONE, pos, vel, lb, channel=ch, M=M, N=N, pfa=1e-4)
        ours = run_clutter_cell(S, cold=(), doppler_notch=True, N=N, seed0=0, pfa=1e-4)
        d_scr = abs(rc["scr_mean"] - ours["scr_mean"])
        d_pd = abs(rc["pd"] - ours["pd"])
        m = ghosts_noop and (d_scr < 1e-9) and (d_pd < 1e-12)
        allmatch = allmatch and m
        per.append(dict(name=name, ghosts_noop=ghosts_noop, none_scr=ours["scr_mean"],
                        run_cell_scr=rc["scr_mean"], d_scr=d_scr, d_pd=d_pd, match=bool(m)))
        if verbose:
            print(f"  [{name:14s}] ghosts=() no-op {'PASS' if ghosts_noop else 'FAIL'} | "
                  f"none==run_cell Δ={d_scr:.2e}dB Pd {rc['pd']:.3f}/{ours['pd']:.3f} "
                  f"→ {'PASS' if m else 'FAIL'}", flush=True)
    return dict(per_waveform=per, all_match=bool(allmatch))


# =========================================================================== #
#  그림 (영어 텍스트)
# =========================================================================== #
def figure(C2_list, C4, path):
    import matplotlib
    matplotlib.use("Agg")
    try:
        import vizstyle
        vizstyle.use_korean()
    except Exception:
        pass
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 3, figsize=(18.6, 5.2), constrained_layout=True)
    ax = axs[0]
    for C2 in C2_list:
        dop = C2["doppler"]["rows"]; zero = C2["zero_dop"]["rows"]
        xd = [r["scale_db"] for r in dop if r["scale_db"] is not None]
        yd = [r["scr_out_db"] for r in dop if r["scale_db"] is not None]
        yz = [r["scr_out_db"] for r in zero if r["scale_db"] is not None]
        ax.plot(xd, yd, "-o", label=f"{C2['name']} Doppler-spread")
        ax.plot(xd, yz, "--s", alpha=0.55, label=f"{C2['name']} zero-Doppler (control)")
    ax.set_xlabel("cold-clutter amplitude re. RT anchor [dB]")
    ax.set_ylabel("SCR after ECA (measured) [dB]")
    ax.set_title("(a) Does SCR stay amplitude-independent?\n"
                 "zero-Doppler flat (notch-killed) vs Doppler degrades", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=6.5)

    ax = axs[1]
    for C2 in C2_list:
        dop = C2["doppler"]["rows"]; zero = C2["zero_dop"]["rows"]
        xd = [r["scale_db"] for r in dop if r["scale_db"] is not None]
        yr = [r["ref_region_db"] for r in dop if r["scale_db"] is not None]
        yz = [r["ref_region_db"] for r in zero if r["scale_db"] is not None]
        ax.plot(xd, yr, "-o", label=f"{C2['name']} Doppler")
        ax.plot(xd, yz, "--s", alpha=0.55, label=f"{C2['name']} zero-Doppler")
    ax.set_xlabel("cold-clutter amplitude re. RT anchor [dB]")
    ax.set_ylabel("ref-region mean power [dB]")
    ax.set_title("(b) Notch-independent residual probe\n"
                 "Doppler slope>0 (amp^2) => dead-param identity broken", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=6.5)

    ax = axs[2]
    if C4:
        x = [r["v_ms"] for r in C4["rows"]]
        ax.plot(x, [r["pd_bench"] for r in C4["rows"]], "-o", color="#2e7d32",
                label="Pd, real target (echo=1)")
        ax.plot(x, [r["pd_notarget"] for r in C4["rows"]], "-s", color="#c62828",
                label=f"Pd, NO target ({C4['notarget_db']:.0f}dB) + clutter")
        ax.plot(x, [r["pd_notgt_noclut"] for r in C4["rows"]], "--^", color="#1565c0",
                alpha=0.7, label="Pd, no target, no clutter (baseline)")
        fb = C4["fd_band_hz"] / C4["hz_per_ms"]
        ax.axvspan(0, fb, color="orange", alpha=0.12)
        ax.annotate("clutter Doppler band", (fb * 0.5, 0.5), fontsize=7,
                    color="#b26a00", ha="center", rotation=90)
        ax.set_ylim(-0.03, 1.08)
        ax.set_xlabel("target radial speed [m/s]")
        ax.set_ylabel("Pd at target cell (notch ON)")
        ax.set_title("(c) H2: is the low-speed detection the target or the clutter?\n"
                     "no-target Pd~1 ⇒ slow drone indistinguishable from moving clutter", fontsize=10)
        ax.grid(alpha=0.3); ax.legend(fontsize=6.6)
    else:
        ax.axis("off")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


# =========================================================================== #
def _print_sweep(tag, sw):
    print(f"    {tag}: scr_span={sw['scr_span_db']:.3e} dB  ref_span={sw['ref_span_db']:.2f} dB")
    for r in sw["rows"]:
        lbl = "none " if r["scale_db"] is None else f"{r['scale_db']:+5.0f}dB"
        print(f"      [{lbl}] scr_out={r['scr_out_db']:8.4f}dB  scnr_in="
              f"{r['scnr_in_db']:8.2f}dB  Pd={r['pd']:.3f}  ref={r['ref_region_db']:7.2f}dB  "
              f"cfar_extra={r['cfar_extra']:.2f}")


def _dump(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1,
                  default=lambda o: float(o) if isinstance(o, np.floating) else o)


def smoke():
    """1파형(5G)·작은 N·스윕 3점(없음/기본/+40dB). /tmp 산출. GPU3.
    N 은 SMOKE_N(기본 15), 무거운 M=96/hot/C4 는 SMOKE_HEAVY=1 로 켠다(ECA≈1.2s/trial)."""
    t0 = time.time()
    N = int(os.environ.get("SMOKE_N", "15"))
    heavy = bool(os.environ.get("SMOKE_HEAVY"))
    print("=" * 84, flush=True)
    print(f"[E3 SMOKE] cold clutter 도플러퍼짐 — 5G NR 100MHz, mavic4pro, 챔버 (N={N}, heavy={heavy})",
          flush=True)
    name, wf = waveforms("G3")[0]                          # 5G
    S = Setup(wf, M=M_DEF)
    print(f"  {name}: M={S.M} dfd={S.dfd:.2f}Hz(노치 반폭 dfd/2={S.dfd/2:.2f}Hz) prf={S.prf:.0f}Hz "
          f"true_fd={S.true_fd:+.1f}Hz true_Rb={S.true_Rb:.1f}m n_taps={S.n_taps} n_range={S.n_range}",
          flush=True)

    print("\n[불변 증명] make_cpi 파괴적 수정 없음:", flush=True)
    inv = prove_make_cpi_unchanged([(name, S)], N=max(12, N))

    print("\n[C1] cold clutter 모델 (서베이 §V-A4 처방) + 경험적 앵커 + 메커니즘 프로브:", flush=True)
    p = prep_setup(S)
    c1 = sec_C1_cold_model([p])[0]
    print(f"  C_placed={c1['C_placed']}/100  링별={c1['placed_per_ring']}  "
          f"링 지연={[round(x,1) for x in c1['ring_tau_ns']]} ns")
    print(f"  도플러밴드=±{c1['fd_band_hz']:.1f}Hz  (dfd={c1['dfd_hz']:.1f}Hz → "
          f"{c1['fd_band_over_dfd']:.2f}×빈)  CNR nominal={c1['cnr_nominal_db']:.1f} "
          f"realized={c1['cnr_realized_db']:.2f}dB (라벨=실현)")
    mz = c1["eca_mechanism"]["zero_dop"]; mdp = c1["eca_mechanism"]["doppler"]
    print(f"  [메커니즘] ECA resid/in: zero-dop {mz['eca_resid_db']:+.2f}dB "
          f"doppler {mdp['eca_resid_db']:+.2f}dB (거의 동일=ECA 무관) | "
          f"notch_frac zero {mz['notch_frac']*100:.2f}% doppler {mdp['notch_frac']*100:.2f}% "
          f"→ 죽음은 노치, 부활은 노치탈출", flush=True)

    print(f"\n[C2] ★ 진폭 스윕 3점 (없음 / 기본=RT앵커 / +40dB), N={N}:", flush=True)
    C2 = sec_C2_amplitude_sweep(p, N=N, seed0=0)
    _print_sweep("Doppler-spread cold ", C2["doppler"])
    _print_sweep("zero-Dop control    ", C2["zero_dop"])

    C2b = None; C3 = None; C4 = None
    if heavy:
        print("\n[C2b] M=96 교차시험:", flush=True)
        C2b = sec_C2b_M96(wf, N=N)
        print(f"  M=96 dfd={C2b['dfd_hz']:.2f}Hz  클러터밴드=±{C2b['fd_band_hz']:.1f}Hz → "
              f"{C2b['fd_band_over_dfd']:.2f}×빈")
        _print_sweep("Doppler-spread cold ", C2b["doppler"])

        print("\n[C3] hot clutter (INR=20dB + CNR-matched, scnr_in 은 hot 포함):", flush=True)
        C3 = sec_C3_hot_clutter(p, N=max(20, N))
        for k in ("cold_only", "cold_hot_inr20", "cold_hot_cnrmatched"):
            r = C3[k]
            print(f"  {k:20s}: scnr_in={r['scnr_in_db']:7.2f}dB scr_out={r['scr_out_db']:6.2f}dB "
                  f"Pd={r['pd']:.3f} cfar_extra={r['cfar_extra']:.2f}")
        print(f"  clutter/noise={C3['clutter_to_noise_db']:.1f}dB (=CNR-matched hot INR)")

        print("\n[C4] ★ 표적속도 스윕 — 저속 검출은 표적인가 클러터인가 (notch on):", flush=True)
        C4 = sec_C4_target_speed(p, N=max(20, N))
        print(f"  클러터밴드 ±{C4['fd_band_hz']:.1f}Hz  notarget echo={C4['notarget_db']:.0f}dB")
        for r in C4["rows"]:
            tag = "IN-band" if r["in_clutter_band"] else "out"
            print(f"    v={r['v_ms']:.1f}m/s fd={r['fd_hz']:+6.1f}Hz({r['fd_over_dfd']:+.2f}빈,{tag}) "
                  f"Pd: target={r['pd_bench']:.2f} notarget={r['pd_notarget']:.2f} "
                  f"clean={r['pd_notgt_noclut']:.2f} | scr={r['scr_bench']:.1f} "
                  f"cfar_extra={r['cfar_extra_bench']:.1f}")

    fig_path = "/tmp/verify_clutter_doppler_smoke.png"
    figure([C2], C4, fig_path)
    js = dict(meta=dict(waveform=name, drone=DRONE, M=S.M, dfd_hz=S.dfd,
                        notch_halfwidth_hz=S.dfd / 2.0, N=N, true_fd_hz=S.true_fd,
                        cnr_anchor_db=RT_FLOOR_TOP_DB),
              invariance=inv, C1=c1, C2=C2, C2b_M96=C2b, C3=C3, C4=C4)
    _dump("/tmp/verify_clutter_doppler_smoke.json", js)
    print(f"\n→ /tmp/verify_clutter_doppler_smoke.json · {fig_path}   ({time.time()-t0:.0f}s)", flush=True)
    return js


def main():
    t0 = time.time()
    N2 = int(os.environ.get("E3_N_C2", "60"))
    N3 = int(os.environ.get("E3_N_C3", "60"))
    N4 = int(os.environ.get("E3_N_C4", "60"))
    Ninv = int(os.environ.get("E3_N_INV", "40"))
    setups = [(n, Setup(wf)) for n, wf in waveforms("G3")]
    print(f"[E3] cold(도플러퍼짐)+hot+표적속도 — 3파형  (N_C2={N2} N_C3={N3} N_C4={N4} N_inv={Ninv})",
          flush=True)

    print("[불변 증명] make_cpi 파괴적 수정 없음 (3파형):", flush=True)
    inv = prove_make_cpi_unchanged(setups, N=Ninv)

    print("[prep] cold clutter 산란체 + 경험적 앵커...", flush=True)
    preps = [prep_setup(S) for _, S in setups]
    C1 = sec_C1_cold_model(preps)

    C2_list = []
    for p in preps:
        print(f"[C2] {p['S'].wf.name} 진폭 스윕(도플러 vs zero-dop)...", flush=True)
        C2_list.append(sec_C2_amplitude_sweep(p, N=N2, seed0=0))

    p5 = preps[0]                                          # 5G = 헤드라인 파형
    print("[C2b] M=96 교차시험 (5G)...", flush=True)
    C2b = sec_C2b_M96(setups[0][1].wf, N=N2)
    print("[C3] hot clutter (5G)...", flush=True)
    C3 = sec_C3_hot_clutter(p5, N=N3)
    print("[C4] 표적속도 스윕 (5G)...", flush=True)
    C4 = sec_C4_target_speed(p5, N=N4)

    figure(C2_list, C4, OUT_FIG)
    res = dict(
        meta=dict(drone=DRONE, M_default=M_DEF, cnr_anchor_db=RT_FLOOR_TOP_DB,
                  scnr_in_def="echo/(clutter+hot+noise), pre-ECA, DPI-excluded",
                  notch_def="single zero-Doppler bin det[zd,:]=False, half-width dfd/2",
                  anchor="empirical (realized clutter/DPI power measured & rescaled)",
                  headline_waveform="5G NR 100MHz (C2b/C3/C4 are 5G-only; C2 is 3-waveform)",
                  N_C2=N2, N_C3=N3, N_C4=N4),
        invariance=inv, C1_cold_model=C1, C2_amplitude_sweep=C2_list,
        C2b_M96=C2b, C3_hot_clutter=C3, C4_target_speed=C4)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    _dump(OUT_JSON, res)
    print(f"→ {OUT_JSON}\n→ {OUT_FIG}   ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        smoke()
    else:
        main()
