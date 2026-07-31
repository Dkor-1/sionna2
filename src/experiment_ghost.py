# -*- coding: utf-8 -*-
"""
experiment_ghost.py — [탐색용·미결론] RT 유령을 검출 채널에 주입해 보는 몬테카를로

⚠ 2026-07-20 상태: **탐색 실험, 결론 미확정.** 운용 SNR 35 dB 에서 −18 dB 유령은 밝은 표적
   ±1~2 빈에 앉아 지배도 +0.1 dB 뿐 — 별도 검출피크를 못 만든다. 이는 report09 의 '기하적
   분해가능성(sep/ΔRb>1)'과 결이 다른 '실제 검출가능성' 질문인데, 본 스크립트의 지표(차분지도
   피크 셀에서의 파워비)가 표적 사이드로브와 겹쳐 **깔끔히 분리 측정하지 못한다**. 따라서 이 결과로
   report09 헤드라인을 수정하지 않는다. 제대로 닫으려면: 표적 부재 채널에서 유령 단독 피크를
   SNR 스윕하며 CFAR 대비 측정(향후 과제). detection_ghost.json 은 이 미결론 상태의 기록물.

원래 목적: report09 는 유령 기하·세기를 RT 로 정량화했지만 검출 MC(report12)엔 안 넣었다
==========================================================================================
왜: report09 는 표적경유 바닥 유령의 기하·세기를 RT 로 정량화했지만(τ+Δτ, −18 dB,
    별개 도플러), 검출 몬테카를로(report12)의 채널에는 넣지 않았다 — "남은 정직한 갭".
    이 실험이 그 갭을 닫는다: **Sionna RT 가 찾은 물리(유령 탭)가 CFAR 검출 숫자
    (유령 셀 오검출률)로 직접 흘러 들어간다.**

무엇을 재나(모드별, N=1, 운용 σ 레벨):
  · P_ghost  : CFAR 가 유령 셀(±1빈)에서 발화할 확률 — 전대역이면 '가짜 표적'
  · Pd_true  : 진짜 표적 셀 검출확률(유령이 있어도 유지되는지)
  · baseline : 유령 없는 채널에서 같은 셀의 발화율(= 그 셀의 순수 오경보 기준선)

유령 파라미터 출처: outputs/floor_ghost_verify.json (report09 의 RT 결과)
  Rb_ghost = Rb_true + sep_m(3.531 m) → τ_ghost = τ + sep/c
  진폭     = 표적 에코 × 10^(ghost_db/20) (≈ −18 dB)
  도플러   = fd_true × (fd_ghost/fd_true)  (JSON 비율 — 표적경유라 ECA 를 통과한다)

실행:  SIONNA2_DET_K=4000 ~/.venvs/py312/bin/python src/experiment_ghost.py
출력:  outputs/detection_ghost.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from gpu import pick                                              # noqa: E402
pick(verbose=True)

from experiment_detection import (FC, MODES, CPI_CFG, N_TAPS, N_RANGE, DPI_AMP,  # noqa: E402
                                  X410Scenario, build_echo_sionna, target_aspect,
                                  pfa_nominal_for, Precomputed, measure_single_snr)
from passive_process import ECACanceller, range_doppler             # noqa: E402
from rcs_po import drone_rcs_pattern                              # noqa: E402

C0 = 299_792_458.0
K = int(os.environ.get("SIONNA2_DET_K", "4000"))
# ⭐ K(시행수=통계)와 배치(=순간 메모리)를 **분리**한다. 예전에는 배치가 하드코딩 64 라
#   메모리가 모자라면 K 를 줄이는 수밖에 없었는데, 그건 결과의 통계를 훼손하는 짓이다.
GHOST_BATCH = int(os.environ.get("SIONNA2_GHOST_BATCH", "64"))
SNR_OP = 35.0   # 운용 SNR[dB] — 링크버짓 실측 SCR 14.8~55.3 dB(verify_linkbudget D_sigma_table)의
                # 대표값. 유령(에코−18 dB)이 ~17 dB 로 보이는 현실적 지점.
# 유령 파라미터 (RT, report09) — 파형 표준별
GJ = {r["name"]: r for r in json.load(open(os.path.join(ROOT, "outputs",
                                                        "floor_ghost_verify.json")))["CD_ghost"]}
STD2GHOST = {"nr": "5G NR 100MHz", "wifi": "WiFi 80MHz", "lte": "LTE 20MHz"}
# 검사 모드: 협대역 상시(G1·L1 — 병합 예측) vs 광대역(G3 — 분리 예측) vs 경계(W3, 0.89×)
CODES = ("G1", "L1", "W3", "G3")


def make_ghost(ref_cpi, meta, wf, ghost):
    """표적 에코와 같은 방식(Sionna 지연 커널 + 위상램프)으로 유령 탭을 만든다."""
    import sionna_chain as sc
    from scipy.signal import fftconvolve
    tau_g = meta["tau"] + ghost["sep_m"] / C0
    amp_g = meta["amp"] * 10 ** (ghost["ghost_db"] / 20.0)
    fd_g = meta["fd"] * (ghost["fd_ghost"] / ghost["fd_true"])
    h, _, _ = sc.channel_taps([1.0], [tau_g], bandwidth=wf.fs_hz, n_time=1)
    kern = np.asarray(h.detach().cpu().numpy()).reshape(-1).astype(np.complex64)
    y = fftconvolve(ref_cpi, kern)[:len(ref_cpi)].astype(np.complex64)
    n = np.arange(len(ref_cpi))
    return (amp_g * y * np.exp(1j * 2 * np.pi * fd_g * n / wf.fs_hz)).astype(np.complex64), \
        dict(tau_g=tau_g, amp_g=float(amp_g), fd_g=float(fd_g))


def locate_cell(resid, ref, fs, M, exclude=None):
    """RD 지도에서 (0-도플러 능선·제외영역 밖) 최대 셀을 찾는다."""
    _, _, rd = range_doppler(resid, ref, fs, M, n_range=N_RANGE)
    zd = M // 2
    rd = rd.copy(); rd[max(0, zd - 2):zd + 3, :] = 0.0
    if exclude is not None:
        di, ri = exclude
        rd[max(0, di - 2):di + 3, max(0, ri - 2):ri + 3] = 0.0
    d, r = np.unravel_index(int(np.argmax(rd)), rd.shape)
    return int(d), int(r)


def fire_rate(pre, extra, cell, K, pfa_nom, seed, nscale=1.0):
    """몬테카를로: (에코[+extra]+DPI+잡음) → CFAR → cell ±1빈 발화율과 truth 발화율."""
    import torch
    from detection_gpu import rd_batch, cfar_batch
    from gpu import oom_backoff
    t = pre._t; dev = t["dev"]
    echo = t["echo"] + (torch.tensor(extra, device=dev) if extra is not None else 0)
    hits_c = 0; hits_t = 0; done = 0; pow_c = 0.0
    dg, rg = cell

    def _chunk(batch, n0):
        """시행 [n0, n0+batch) 를 계산한다. 난수 씨앗을 **청크 시작번호 n0 로** 잡는다.

        재현성 (정확히):
          · `GHOST_BATCH` 를 고정하면 결과는 **완전히 재현된다**.
          · 배치를 바꾸면 청크 경계가 바뀌므로 **비트단위로는 달라진다** — 다만 청크마다
            독립적으로 씨를 뿌리므로 각 추출은 여전히 정당한 독립표본이고, 차이는 MC 오차 안이다.
          · 옛 판(생성기 하나를 순차 소비)도 배치에 의존하기는 마찬가지였다. 바뀐 점은
            **OOM 백오프로 배치가 중간에 줄어도** 이어지는 청크가 오염되지 않는다는 것이다."""
        g = torch.Generator(device=dev).manual_seed(seed * 1000003 + n0)
        nz = ((torch.randn(batch, pre.Ns, generator=g, device=dev)
               + 1j * torch.randn(batch, pre.Ns, generator=g, device=dev)) / np.sqrt(2)) * nscale
        surv = echo[None, :] + t["dpi"][None, :] + nz
        rd = rd_batch(surv, t["ref"], pre.M, pre.n_range)
        det, _ = cfar_batch(rd, pfa=pfa_nom)
        hc = int(det[:, max(0, dg - 1):dg + 2, max(0, rg - 1):rg + 2]
                 .any(dim=(1, 2)).sum().item())
        ht = int(det[:, max(0, pre.di_true - 1):pre.di_true + 2,
                     max(0, pre.ri_true - 1):pre.ri_true + 2]
                 .any(dim=(1, 2)).sum().item())
        pc = float((rd[:, max(0, dg - 1):dg + 2, max(0, rg - 1):rg + 2] ** 2)
                   .amax(dim=(1, 2)).sum().item())
        return hc, ht, pc

    while done < K:
        b = min(GHOST_BATCH, K - done)
        # ⭐ 공용 GPU 에서 타 사용자가 갑자기 메모리를 잡아도 **죽지 말고 줄여서 계속** (gpu.oom_backoff).
        #   2026-07-29: 이 고리가 실제로 OOM 으로 죽어(3.28 GiB) stage4 가 통째로 멎었다.
        hc, ht, pc = oom_backoff(lambda batch: _chunk(batch, done), batch=b, min_batch=1)
        hits_c += hc; hits_t += ht; pow_c += pc
        done += b
    return hits_c / K, hits_t / K, pow_c / K


def main():
    from waveforms import wifi_80211ac, lte_downlink, nr_downlink
    FAC = {"nr": nr_downlink, "wifi": wifi_80211ac, "lte": lte_downlink}
    scn = X410Scenario(carrier_hz=FC)
    az, el = target_aspect(scn)
    sigma_dbsm, _ = drone_rcs_pattern("mavic4pro", FC, np.array([abs(az)]))
    sigma_m2 = float(sigma_dbsm[0])
    out = dict(meta=dict(K=K, drone="mavic4pro", sigma_dbsm=float(10 * np.log10(sigma_m2)),
                         source="outputs/floor_ghost_verify.json (RT, report09)"),
               modes={})
    modes = {c: m for m in MODES for c in [m[2]] if c in CODES}
    for code in CODES:
        std, occ, _, always_on = modes[code]
        wf = FAC[std](occupancy=occ)
        cfg = CPI_CFG[std]
        gh = GJ[STD2GHOST[std]]
        pfa_nom = pfa_nominal_for(std, 1e-4)
        y_echo, ref_cpi, meta = build_echo_sionna(wf, cfg["M"], cfg["b"], scn, sigma_m2,
                                                  (-3.0, 0.0, 0.0), verbose=False)
        y_ghost, gmeta = make_ghost(ref_cpi, meta, wf, gh)
        pre = Precomputed(y_echo, ref_cpi, wf, cfg["M"], meta).to_gpu()
        can = ECACanceller(ref_cpi, n_taps=N_TAPS, ridge_rel=1e-4)
        resid_g = can.cancel(y_ghost).astype(np.complex64)
        # 유령 셀 = 무잡음 차분 지도의 피크: |RD(에코+유령)| − |RD(에코)| 가 가장 커지는 셀
        #   (도플러 빈 부호·창 누설에 무관한 결정론적 위치)
        _, _, rd_e = range_doppler(pre.resid_echo, can.ref, wf.fs_hz, cfg["M"], n_range=N_RANGE)
        _, _, rd_eg = range_doppler(pre.resid_echo + resid_g, can.ref, wf.fs_hz, cfg["M"],
                                    n_range=N_RANGE)
        diff = rd_eg - rd_e
        zd = cfg["M"] // 2
        diff[max(0, zd - 2):zd + 3, :] = 0.0
        cell_g = tuple(int(v) for v in np.unravel_index(int(np.argmax(diff)), diff.shape))
        sep_bins = abs(cell_g[1] - pre.ri_true)
        # '별도 표적'이 성립하려면 유령 셀이 표적 주엽(±ΔRb) 밖이어야 한다
        rbin = C0 / wf.fs_hz
        merged = (sep_bins * rbin) < wf.range_resolution_m
        t0 = time.time()
        snr_ref = measure_single_snr(pre, 1.0)          # 잡음 σ=1 일 때의 SNR
        nscale = 10 ** ((snr_ref - SNR_OP) / 20.0)      # SNR_OP 운용점이 되도록 잡음 스케일
        p_base, pd_base, pw_base = fire_rate(pre, None, cell_g, K, pfa_nom, seed=7, nscale=nscale)
        p_ghost, pd_ghost, pw_ghost = fire_rate(pre, resid_g, cell_g, K, pfa_nom, seed=7, nscale=nscale)
        dom_db = 10 * np.log10(max(pw_ghost, 1e-30) / max(pw_base, 1e-30))
        drb = wf.range_resolution_m
        out["modes"][code] = dict(
            snr_op_db=SNR_OP, snr_ref_db=float(snr_ref),
            std=std, ref_bw_mhz=wf.ref_bw_hz / 1e6, range_res_m=drb,
            sep_m=gh["sep_m"], sep_over_drb=gh["sep_m"] / drb,
            ghost_db=gh["ghost_db"], fd_ratio=gh["fd_ghost"] / gh["fd_true"],
            ghost_cell=list(cell_g), true_cell=[pre.di_true, pre.ri_true],
            sep_bins=int(sep_bins), merged=bool(merged),
            p_fire_ghost_cell=dict(baseline=p_base, with_ghost=p_ghost),
            ghost_cell_dominance_db=float(dom_db),
            pd_true=dict(baseline=pd_base, with_ghost=pd_ghost),
            resolved_pred=bool(gh["sep_m"] / drb >= 1.0),
            note="merged=True 면 유령은 표적과 같은 분해능 셀 안(별도 표적 없음); "
                 "dominance=유령 주입 전후 그 셀 파워비(사이드로브 대비 유령의 지배도)")
        print(f"  ▶ {code} ({std} {wf.ref_bw_hz/1e6:.0f}MHz, ΔRb={drb:.1f}m, "
              f"sep/ΔRb={gh['sep_m']/drb:.2f}, sep={sep_bins:.0f}빈{' 병합' if merged else ''}): "
              f"유령셀 지배도 {dom_db:+.1f} dB · 발화 {p_base:.3f}→{p_ghost:.3f} · "
              f"Pd_true {pd_ghost:.3f} ({time.time()-t0:.0f}s)")
    path = os.path.join(ROOT, "outputs", "detection_ghost.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("✅ 저장:", path)


if __name__ == "__main__":
    main()
