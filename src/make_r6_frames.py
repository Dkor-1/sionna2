#!/usr/bin/env python
"""report13 R6 — 실 MC RD맵 프레임열 producer.

viz_report13 의 r6_rd_recede 는 `curves.rd_frames`(|RD| 2D 배열 리스트)를 애니로 돌려
**거리 증가에 따라 표적 CFAR 봉우리가 잡음에 묻혀 사라지는** 장면을 만든다. 그 프레임을
여기서 실제 RD 처리(`passive_process.range_doppler`)로 생성해 report13_freespace.json 에 주입한다.

물리: 거리 d 마다 (a) 조명파형을 M 프레임 타일한 기준 CPI, (b) 표적에코(지연 τ(d)·도플러 f_d·
진폭=닫힌형 snr_rd_db(d) 로 보정) + 열잡음 + 약한 0-도플러 클러터능선의 감시 CPI 를 만들고,
range_doppler 로 |RD| 를 낸다. 진폭은 **한 번 보정**(a=1 출력봉우리 측정)해 각 d 의 출력 SNR 이
snr_rd_db(d) 와 맞게 스케일한다 — GPU 0회.

실행: PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_r6_frames.py [--drone mavic4pro --mode L1]
"""
import os, sys, json, argparse
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))

import freespace_scene as fss                       # noqa: E402
import freespace_link as fsl                        # noqa: E402
import experiment_freespace_range as R              # noqa: E402
from passive_process import range_doppler           # noqa: E402
from waveforms import all_waveforms                 # noqa: E402

C0 = R.C0
FREESPACE = os.path.join(ROOT, "outputs", "report13_freespace.json")
SIGMA = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")


def _one_rd(ref_frame, M, tau_samples, fd_hz, fs, amp, sigma_n, clutter_amp, rng, n_range):
    """감시 CPI(에코+잡음+0-도플러 클러터) → |RD| 맵[도플러,거리]."""
    Lf = len(ref_frame)
    T_frame = Lf / fs
    frames = np.empty((M, Lf), complex)
    ref_delayed = np.roll(ref_frame, int(tau_samples))      # 표적지연(순환)
    for m in range(M):
        dopp = np.exp(2j * np.pi * fd_hz * m * T_frame)     # slow-time 도플러 위상
        echo = amp * dopp * ref_delayed
        clutter = clutter_amp * ref_frame                   # 0-도플러(정적) 클러터 능선
        noise = (rng.standard_normal(Lf) + 1j * rng.standard_normal(Lf)) * (sigma_n / np.sqrt(2))
        frames[m] = echo + clutter + noise
    surv = frames.reshape(-1)
    ref_cpi = np.tile(ref_frame, M)
    Rb, fd, rd = range_doppler(surv, ref_cpi, fs, M, n_range=n_range)
    return np.abs(rd)


def build_frames(drone="mavic4pro", mode="L1",
                 ds=(200., 400., 700., 1100., 1700., 2500., 3500., 5000.),
                 L=500., alt=60., phi=90., T_cpi=0.1, n_range=1024, dr_target_db=45.0, seed=0):
    std, occ = R.MODE_STD[mode]
    bname, fc, bw = R._BAND_BY_STD[std]
    lam = C0 / fc
    wf = all_waveforms(occ)[std]
    fs = float(wf.fs_hz)
    ref = np.asarray(wf.tx, complex)
    # 한 프레임 = 반복주기. 너무 길면 자르되 표적지연을 담을 만큼은 유지.
    Lf = min(len(ref), 4096)
    ref_frame = ref[:Lf].copy()
    if np.max(np.abs(ref_frame)) > 0:
        ref_frame /= np.sqrt(np.mean(np.abs(ref_frame) ** 2))   # 단위전력 정규화
    prf = float(fss.prf_hz(std, occ))
    M = int(fss.M_from_prf(T_cpi, prf))
    M = max(8, min(M, 64))
    lookup = R._sigma_lookup(json.load(open(SIGMA)), drone, bname)
    sigma_n = 1.0
    rng = np.random.default_rng(seed)

    # ── 진폭 보정: a=1·무잡음으로 출력봉우리 이득 G 를 한 번 측정 ──
    tau_ref = int(round((0.5) * (fs) * 1e-6))   # 임의 소지연(≈0.5µs)
    cal = _one_rd(ref_frame, M, tau_ref, 20.0, fs, amp=1.0, sigma_n=1e-9,
                  clutter_amp=0.0, rng=np.random.default_rng(1), n_range=n_range)
    G = float(np.max(cal) ** 2)                 # a=1 출력봉우리 전력
    # 잡음바닥(출력) 측정
    noise_only = _one_rd(ref_frame, M, tau_ref, 20.0, fs, amp=0.0, sigma_n=sigma_n,
                         clutter_amp=0.0, rng=np.random.default_rng(2), n_range=n_range)
    n_floor = float(np.median(noise_only) ** 2)

    frames = []
    meta = []
    for d in ds:
        tgt = fss.target_pos(d, phi, L, alt)
        p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt, (0., 0., 0.), fc)
        R1 = float(np.ravel(p["R1"])[0]); R2 = float(np.ravel(p["R2"])[0])
        Rb = R1 + R2 - L
        tau_s = Rb / C0
        tau_samples = int(round(tau_s * fs)) % Lf
        # 도플러: 표적이 speed=5 m/s 로 방사방향 성분 → 대표 f_d
        fd = 2.0 * 5.0 / lam * 0.3                       # 대표 바이스태틱 도플러(비영, 클러터와 분리)
        az, _ = R._look_az(p["u1"], p["u2"]); az = float(np.ravel(az)[0]); el = float(p["el_deg"])
        sigma = R._sigma_at(lookup, az, el)
        snr_db = fsl.snr_rd_db(R.EIRP_DBM, R.GRX_DBI, lam, sigma, R1, R2, nf=R.NF_DB, eta_ref=0., T=T_cpi)
        # 목표 출력 SNR(잡음바닥 대비) → 진폭. 출력봉우리전력 = amp²·G = snr_lin·n_floor.
        snr_lin = 10 ** (snr_db / 10.0)
        amp = np.sqrt(max(snr_lin, 1e-30) * n_floor / max(G, 1e-30))
        # 클러터 능선은 끈다 — 0-도플러 정적성분은 M프레임 코히런트합이라 별도 보정이 필요하고
        # R6 의 서사(표적 봉우리가 **잡음바닥**으로 소멸)에는 잡음만으로 충분하다.
        clutter_amp = 0.0
        rd = _one_rd(ref_frame, M, tau_samples, fd, fs, amp=amp, sigma_n=sigma_n,
                     clutter_amp=clutter_amp, rng=rng, n_range=n_range)
        frames.append(rd.astype(np.float32))
        meta.append(dict(d_m=float(d), Rb_m=float(Rb), snr_db=float(snr_db)))
    return frames, meta, dict(drone=drone, mode=mode, M=int(M), n_range=int(n_range))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", default="mavic4pro")
    ap.add_argument("--mode", default="L1")
    a = ap.parse_args(argv)
    frames, meta, cfg = build_frames(drone=a.drone, mode=a.mode)
    # dB 스케일 — **전역최대(최근접 봉우리) 기준**으로 정규화해야 원거리 봉우리가
    # 잡음바닥으로 가라앉는 '소멸'이 보인다(프레임별 자기최대 정규화는 금물).
    gmax = max(float(np.max(rd)) for rd in frames)
    out_frames = []
    for rd in frames:
        z = 20.0 * np.log10(np.maximum(rd, 1e-6) / gmax)   # 0 dB = 최근접 봉우리
        z = np.clip(z, -45.0, 0.0)
        out_frames.append(z.tolist())
    d = json.load(open(FREESPACE))
    d.setdefault("curves", {})["rd_frames"] = out_frames
    d["curves"]["rd_frames_meta"] = dict(frames=meta, **cfg,
                                         note="실 MC RD맵(passive_process.range_doppler); dB, 0=봉우리, DR45")
    tmp = FREESPACE + ".tmp"
    json.dump(d, open(tmp, "w"))
    os.replace(tmp, FREESPACE)
    print(f"[R6] rd_frames {len(out_frames)}프레임 주입 → {os.path.relpath(FREESPACE, ROOT)}")
    for m in meta:
        print(f"   d={m['d_m']:6.0f}m  Rb={m['Rb_m']:7.1f}m  snr={m['snr_db']:+6.1f}dB")


if __name__ == "__main__":
    main()
