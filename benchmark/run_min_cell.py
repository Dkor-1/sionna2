# -*- coding: utf-8 -*-
"""
run_min_cell.py — (benchmark) '제대로 된' 최소 셀 1개
=====================================================
EXPERIMENT_SPEC 최소 시작: 1 config × 1 드론 × radial × N trial.

**핵심 차이(공정성 수정)**: 표적 SNR 을 손잡이로 주지 않는다. 고정 EIRP·잡음예산 +
RCS·기하·대역폭에서 **물리로 유도**(link_budget)하고, SCR 은 RD맵에서 **측정**한다.
  이전 report4 : x축 = '표적 에코 진폭[dB]'(주입) → 처리이득만 비교(공정성 위배)
  지금 최소셀 : 에코 SNR = P_echo/P_n (유도) → SCR·Pd 가 물리에서 '나온다'

산출:
  · 콘솔: 최소셀의 유도 SNR / 측정 SCR / Pd
  · 콘솔: 3-신호(WiFi/LTE/5G) SNR_in 비교표 — 같은 EIRP·기하·드론에서 B·λ·σ 만
          신호 물리로 다르므로 SNR 이 신호마다 '다르게 나온다'(= 공정 비교의 핵심)
  · 그림: outputs/figures/bench_min_cell.png (RD맵 + 검출)

로컬 실행: AnalyticChannel(닫힌형). 서버에선 SionnaRTChannel 로 스왑(기하만 교체).
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "src"))
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from waveforms import lte_downlink, nr_downlink, wifi_80211ac   # noqa: E402
from passive_process import make_cpi, eca, range_doppler, ca_cfar_2d  # noqa: E402
from bistatic_scene import C0                                   # noqa: E402
from link_budget import LinkBudget, link_terms, lin2db          # noqa: E402
from channel import AnalyticChannel                             # noqa: E402
from scenarios import radial                                    # noqa: E402

# --- 고정 기하(통제 변수) : 기지국(조명) · 지상 감시수신 · 감시영역 중심 --------------
TX = (0.0, 250.0, 35.0)        # 조명원(illuminator, 기지국 옥상)
RX = (0.0, 0.0, 6.0)           # 패시브 감시 수신기
TGT0 = (180.0, 220.0, 60.0)    # 감시영역 중심(라디얼 궤적의 중앙)


def measure_scr(Rb, f_d, rd, true_Rb, true_fd):
    """SCR = 표적셀(±1) 최대전력 / 기준영역(0-도플러 능선·표적근방 제외) 평균전력 [dB].
    (EXPERIMENT_SPEC §8 정의)"""
    ri = int(np.argmin(np.abs(Rb - true_Rb)))
    di = int(np.argmin(np.abs(f_d - true_fd)))
    cell = rd[max(0, di - 1):di + 2, max(0, ri - 1):ri + 2].max() ** 2
    mask = np.ones_like(rd, bool)
    zd = int(np.argmin(np.abs(f_d)))
    mask[max(0, zd - 1):zd + 2, :] = False               # 0-도플러 클러터 능선 제외
    mask[max(0, di - 3):di + 4, max(0, ri - 3):ri + 4] = False   # 표적 근방 제외
    ref = float(np.mean(rd[mask] ** 2)) + 1e-30
    return float(lin2db(cell / ref)), (ri, di)


def run_cell(wf, drone, pos, vel, lb, channel=None, target_amp="po",
             M=48, N=200, pfa=1e-4, seed0=0):
    """(신호 wf) × (드론) × (궤적) 셀 1개 → 유도 링크텀 + 측정 SCR/Pd.
      channel     : 채널 백엔드(None=AnalyticChannel). **서버에선 SionnaRTChannel 주입**.
      target_amp  : 'po'(기본) | 'rt'(RT 표적산란비 사용 — RT 백엔드에서만 유효)."""
    ch = channel or AnalyticChannel()
    fs = wf.fs_hz

    # 기준(정합필터)·에코 파형 = wf.ref (**아는 파일럿/기준신호만** = 진짜 패시브 레이더 모델).
    #   · data 섞인 full 신호(wf.tx)를 기준으로 쓰면 거리 사이드로브가 큼(비-thumbtack).
    #   · 파일럿 기준은 autocorrelation 이 깨끗 + **점유 G1/G2/G3 가 여기서 공정성으로 작동**:
    #     G1(SSB만)→협대역·저에너지 기준 → 분해능·처리이득↓, G3(+PRS 등)→전대역 기준.
    ref_frame = wf.ref.astype(complex).copy()
    ref_frame /= np.sqrt(np.mean(np.abs(ref_frame) ** 2) + 1e-30)   # 표본전력 1 정규화
    Lf = len(ref_frame)
    n_range = int(min(Lf, 1200 / (C0 / fs)))             # ~1.2 km 까지 거리축
    # ECA 제거 탭은 거리창 전체를 덮어야 0-도플러 클러터/직접파가 창 내내 지워진다.
    # (표적은 fd≠0 이라 ECA 가 보존 — 넓혀도 안전. 좁으면 창 끝에 직접파 잔차 줄무늬가 남음)
    n_taps = int(min(n_range + 8, 96))

    # 대표 스냅샷(궤적 중앙)에서 링크텀 유도 (최소셀 = 1 스냅샷)
    mid = len(pos) // 2
    st = ch.state(TX, RX, pos[mid], vel[mid], wf.carrier_hz, drone)
    lt = link_terms(lb, st.lam, st.sigma_m2, st.R1, st.R2, st.L, wf.bw_hz)
    dpi = lt["dpi_amp"]
    if target_amp == "rt" and st.rt_echo_ratio is not None:
        a_tgt = dpi * st.rt_echo_ratio               # RT 표적산란비(PO 대신, RT 백엔드)
    else:
        a_tgt = lt["a_tgt"]                           # PO 기반(권장)
    clutter_abs = tuple((dt, dpi * r) for (dt, r) in st.clutter)   # 비율→절대(직접파 스케일)
    true_Rb = st.tau * C0

    hits = 0
    scrs = []
    example = None
    for k in range(N):
        surv, ref = make_cpi(
            ref_frame, M, fs, st.tau, st.fd, a_tgt=a_tgt, dpi_amp=dpi,
            clutter=clutter_abs,                                # 채널이 준 정적 클러터(ECA 제거)
            abs_noise=True, noise_var=1.0,                      # 잡음전력=1(a_tgt·dpi 가 물리비)
            rng=np.random.default_rng(seed0 + k))
        Rb, f_d, rd = range_doppler(eca(surv, ref, n_taps), ref, fs, M, n_range=n_range)
        scr, (ri, di) = measure_scr(Rb, f_d, rd, true_Rb, st.fd)
        det, _, _ = ca_cfar_2d(rd, pfa=pfa)
        hit = det[max(0, di - 1):di + 2, max(0, ri - 1):ri + 2].any()   # 참셀 ±1 에 CFAR 히트
        hits += int(hit)
        scrs.append(scr)
        if k == 0:
            example = (Rb, f_d, rd, st, lt, (ri, di), true_Rb)
    return dict(pd=hits / N, scr_mean=float(np.mean(scrs)), scr_std=float(np.std(scrs)),
                link=lt, state=st, example=example, wf=wf, drone=drone, M=M, N=N)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import vizstyle
    vizstyle.use_korean()
    import matplotlib.pyplot as plt

    # EIRP 43 dBm ≈ 20 W: 소형셀/Wi-Fi AP 급 조명원(의미있는 구간).
    #   ※ 매크로 기지국(63 dBm)이면 근거리 드론은 SCR 40dB+ 로 '너무 쉽게' 잡힘 —
    #     그 자체가 정직한 결과(벤치마크 변별 구간은 소형조명·원거리·어려운 모션).
    lb = LinkBudget(eirp_dbm=43.0)
    drone = "mavic4pro"
    pos, vel = radial(TX, RX, TGT0, speed=12.0, span=60.0, n=48)
    # 로컬 데모 채널 = Analytic + 작은 정적 클러터(직접파 대비 비율).
    #   ※ 서버: ch = SionnaRTChannel() 로 바꾸면 클러터가 RT 실측 멀티패스로 대체(자유공간이면 ≈0).
    ch = AnalyticChannel(clutter=((0.0, 0.15), (40e-9, 0.08)))

    # ---------- 최소 셀: LTE 10 MHz @ 1.8 GHz ----------
    wf = lte_downlink(bw_hz=10e6, carrier_hz=1.843e9, occupancy="G3")
    res = run_cell(wf, drone, pos, vel, lb, channel=ch, M=48, N=200)
    lt, st = res["link"], res["state"]

    print("=" * 68)
    print(f"최소 셀 — {wf.name} {wf.bw_hz/1e6:.0f}MHz@{wf.carrier_hz/1e9:.2f}GHz  /  {drone}  /  radial")
    print("-" * 68)
    print(f"  기하   R1={st.R1:.0f}m  R2={st.R2:.0f}m  L={st.L:.0f}m  "
          f"Rb={st.tau*C0:.0f}m  fd={st.fd:+.0f}Hz  β={st.beta:.0f}°")
    print(f"  RCS    σ={10*np.log10(st.sigma_m2):.1f} dBsm  (반송파·자세 반영, PO)")
    print(f"  [물리 유도]  에코SNR={lt['snr_echo_db']:+.1f} dB   "
          f"직접파SNR={lt['snr_direct_db']:+.1f} dB   DNR(직접-에코)={lt['dnr_db']:.1f} dB")
    print(f"  [측정 결과]  SCR={res['scr_mean']:.1f} ± {res['scr_std']:.1f} dB   "
          f"Pd={res['pd']*100:.0f}%   (M={res['M']}, N={res['N']}, CFAR Pfa=1e-4)")

    # ---------- 3-신호 공정 비교 (같은 기하·예산 → SNR 이 신호마다 '나온다') ----------
    print("\n3-신호 SNR_in 비교  (같은 EIRP·기하·드론; B·λ·σ 만 신호 물리로 다름):")
    print(f"  {'신호':<15}{'fc[GHz]':>8}{'B[MHz]':>8}{'σ[dBsm]':>9}"
          f"{'잡음[dBm]':>11}{'에코SNR[dB]':>12}")
    sigs = [
        ("WiFi 80MHz",  wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G3")),
        ("LTE 10MHz",   wf),
        ("LTE 20MHz",   lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy="G3")),
        ("5G 100MHz",   nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")),
    ]
    for nm, w in sigs:
        s = ch.state(TX, RX, pos[len(pos) // 2], vel[len(vel) // 2], w.carrier_hz, drone)
        L = link_terms(lb, s.lam, s.sigma_m2, s.R1, s.R2, s.L, w.bw_hz)
        pn_dbm = 10 * np.log10(L["P_noise_w"]) + 30
        print(f"  {nm:<15}{w.carrier_hz/1e9:>8.2f}{w.bw_hz/1e6:>8.0f}"
              f"{10*np.log10(s.sigma_m2):>9.1f}{pn_dbm:>11.1f}{L['snr_echo_db']:>12.1f}")
    print("  → 5G 는 σ↑·λ↑ 로 에코전력엔 유리하나 B(=잡음)가 5~10× → 순효과는 '나오는 대로'.")
    print("    (다음 단계: 여기에 점유 G1/G2/G3 파일럿-기준 처리이득까지 얹으면 완전한 공정 비교)")

    # ---------- RD 맵 그림 ----------
    Rb, f_d, rd, st, lt, (ri, di), true_Rb = res["example"]
    rdb = 20 * np.log10(rd / rd.max() + 1e-9)
    fig, ax = plt.subplots(figsize=(8.2, 5.4), constrained_layout=True)
    im = ax.pcolormesh(Rb, f_d, rdb, cmap="turbo", vmin=-50, vmax=0, shading="auto")
    ax.plot(true_Rb, st.fd, "o", mfc="none", mec="w", ms=15, mew=1.6, label="참 표적")
    det, _, _ = ca_cfar_2d(rd, pfa=1e-4)
    dd, dr = np.where(det)
    ax.plot(Rb[dr], f_d[dd], "x", color="w", ms=6, mew=1.2, alpha=0.7, label="CFAR 검출")
    ax.set_xlabel("바이스태틱 거리 Rb [m]")
    ax.set_ylabel("도플러 f_d [Hz]")
    ax.set_title(
        f"최소 셀 RD맵 · {wf.name} {wf.bw_hz/1e6:.0f}MHz / {drone} / radial\n"
        f"에코SNR={lt['snr_echo_db']:+.1f}dB (물리 유도) · "
        f"SCR={res['scr_mean']:.1f}dB (측정) · Pd={res['pd']*100:.0f}%",
        fontsize=10.5)
    fig.colorbar(im, ax=ax, label="정규화 [dB]")
    ax.legend(loc="upper right", fontsize=9)
    out = os.path.abspath(os.path.join(_HERE, "..", "outputs", "figures", "bench_min_cell.png"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"\nRD맵 저장 → {os.path.relpath(out, os.path.join(_HERE, '..'))}")


if __name__ == "__main__":
    main()
