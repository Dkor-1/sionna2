# -*- coding: utf-8 -*-
"""
run_min_cell.py — (benchmark) '제대로 된' 최소 셀 1개 (무반사 챔버 내부)
========================================================================
최소 시작: 1 config × 1 드론 × radial × N trial.

**핵심 차이(공정성 수정)**: 표적 SNR 을 손잡이로 주지 않는다. 고정 EIRP·잡음예산 +
RCS·기하·대역폭에서 **물리로 유도**(link_budget)하고, SCR 은 RD맵에서 **측정**한다.
  이전 report4 : x축 = '표적 에코 진폭[dB]'(주입) → 처리이득만 비교(공정성 위배)
  지금 최소셀 : 에코 SNR = P_echo/P_n (유도) → SCR·Pd 가 물리에서 '나온다'

**고속 Monte-Carlo**: 표적·직접파·클러터(결정론적 부분)는 모든 trial에서 동일하고 잡음만
다르다. 그래서 결정론적 surv 를 **1회** 합성하고, ECA 참조 자기상관도 **1회** 프리컴퓨트한
뒤(ECACanceller), trial 마다 잡음만 더해 돌린다 → make_cpi 반복 FFT·ECA 재계산 제거.

기하: report1~4 와 같은 30×20×11 m 무반사 챔버(geometry.py). numpy 전용(GPU 불필요).
RT 교차검증은 channel 만 SionnaRTChannel 로 스왑(기하 동일 — run_matrix.py D 섹션).
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

from waveforms import lte_downlink, nr_downlink, wifi_80211ac, PILOT_RATE_HZ  # noqa: E402
from passive_process import make_cpi, ECACanceller, range_doppler, ca_cfar_2d, peak_detection  # noqa: E402
from bistatic_scene import C0                                   # noqa: E402
from link_budget import LinkBudget, link_terms                  # noqa: E402
from channel import AnalyticChannel                             # noqa: E402
from scenarios import radial                                    # noqa: E402
from geometry import TX, RX, CENTER, CH_CLUTTER_RATIO, chamber_window, SPEED, SPAN  # noqa: E402

# 챔버 EIRP(통제 변수): 챔버 조명원은 저출력 안테나(12 dBm ≈ 16 mW, WiFi AP 급).
# R~20 m 근거리라 이 값에서 G3 광대역 조합은 전부 여유 있게 탐지된다(측정 결과) —
# Pd 전이(어느 예산부터 잡히나)는 run_matrix.py A 섹션의 EIRP 스윕이 측정한다.
EIRP_DBM = 12.0


def measure_scr(Rb, f_d, rd, true_Rb, true_fd):
    """SCR = 표적셀(±1) 최대전력 / 기준영역(0-도플러 능선·표적근방 제외) 평균전력 [dB].
    ※ 분자가 3×3 창의 max 라 잡음 한계(무표적)에서 ~+3 dB 상향 바이어스가 있다 —
      전 셀에 동일하게 적용되므로 셀 간 '비교'의 공정성은 유지된다."""
    from link_budget import lin2db
    ri = int(np.argmin(np.abs(Rb - true_Rb)))
    di = int(np.argmin(np.abs(f_d - true_fd)))
    cell = rd[max(0, di - 1):di + 2, max(0, ri - 1):ri + 2].max() ** 2
    mask = np.ones_like(rd, bool)
    zd = int(np.argmin(np.abs(f_d)))
    mask[max(0, zd - 1):zd + 2, :] = False               # 0-도플러 클러터/직접파 능선 제외
    mask[max(0, di - 3):di + 4, max(0, ri - 3):ri + 4] = False   # 표적 근방 제외
    ref = float(np.mean(rd[mask] ** 2)) + 1e-30
    return float(lin2db(cell / ref)), (ri, di)


def wilson_ci(hits, n, z=1.96):
    """이항비율 Wilson 95% 신뢰구간 (Pd 오차막대용). 반환 (lo, hi)."""
    if n == 0:
        return 0.0, 1.0
    p = hits / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float((c - h) / d), float((c + h) / d)


def frame_len(wf):
    """CPI 프레임 길이[샘플]. LTE/5G 는 연속 송신이라 프레임=tx 길이 그대로 타일링이 타당.
    **WiFi 는 CSMA/CA 패킷 신호** — 패킷을 백투백으로 타일링하면 유효 PRF ~18 kHz 가 되어
    자체 가정(waveforms.PILOT_RATE_HZ: 혼잡 AP ~1 kHz)보다 ~12 dB 의 비물리적 코히어런트
    이득을 얻는다. 그래서 패킷률에 맞춰 패킷 뒤를 무음으로 채운 슬롯 길이(fs/패킷률)를 쓴다."""
    L = len(wf.tx)
    if wf.std == "wifi":
        L = max(L, int(round(wf.fs_hz / PILOT_RATE_HZ["wifi"]["LLTF"])))
    return L


def run_cell(wf, drone, pos, vel, lb, channel=None, target_amp="po",
             M=48, N=200, pfa=1e-4, seed0=0, noise_var=1.0, power_ref_tx=None):
    """(신호 wf) × (드론) × (궤적) 셀 1개 → 유도 링크텀 + 측정 SCR/Pd(+CI)/거리오차.
      channel     : 채널 백엔드(None=AnalyticChannel). RT 교차검증 시 SionnaRTChannel 주입.
      target_amp  : 'po'(기본) | 'rt'(RT 표적산란비 — RT 백엔드에서만 유효).
      power_ref_tx: 전력 정규화 기준 파형(기본 wf.tx). **점유모드 간 비교**(G1/G2/G3) 시
                    G3 의 tx 를 넘기면 'per-RE 송신전력 동일' 가정이 되어, 시간희소한
                    G1(SSB 버스트만)의 낮은 평균 방사전력이 물리대로 반영된다."""
    ch = channel or AnalyticChannel()
    fs = wf.fs_hz

    # 기준(정합필터) 파형 = wf.ref (**아는 파일럿/기준신호만** = 진짜 패시브 레이더 모델).
    #   파일럿 기준은 autocorrelation 이 깨끗 + **점유 G1/G2/G3 가 여기서 공정성으로 작동**:
    #   G1(SSB만)→협대역·저에너지 기준, G3(+PRS 등)→전대역 기준.
    # 정규화는 **전체 송신파형(tx) 전력 기준**: a_tgt/dpi_amp(링크버짓)는 '풀신호 per-sample
    #   진폭'이므로 tx 의 rms 로 나누면 파일럿 성분이 실제 상대 진폭을 유지한다. (ref 자체
    #   전력=1 정규화는 G1 희소 파일럿의 저에너지 핸디캡을 지워 불공정.)
    pref = wf.tx if power_ref_tx is None else power_ref_tx
    txp = np.sqrt(np.mean(np.abs(pref) ** 2) + 1e-30)
    ref_frame = wf.ref.astype(complex) / txp             # 파일럿만(수신기가 아는 부분)
    tx_frame = wf.tx.astype(complex) / txp               # 전체 송신(파일럿+데이터)
    # G1/G2 를 pref(G3) 기준으로 주입할 때의 실효 전력차(≤0 dB) — 보고/CSV 용
    occ_db = float(20 * np.log10(np.sqrt(np.mean(np.abs(wf.tx) ** 2)) / txp + 1e-30))
    # WiFi 듀티: 패킷 사이를 무음으로(에코·DPI·기준 모두 동일하게) → PRF 가 패킷률로 떨어짐
    Lf = frame_len(wf)
    if Lf > len(tx_frame):
        pad = np.zeros(Lf - len(tx_frame), complex)
        ref_frame = np.concatenate([ref_frame, pad])
        tx_frame = np.concatenate([tx_frame, pad])
    n_range, n_taps = chamber_window(wf)                 # 챔버 Rb 창 → 거리빈·ECA 탭

    # 대표 스냅샷(궤적 중앙)에서 링크텀 유도 (최소셀 = 1 스냅샷)
    mid = len(pos) // 2
    st = ch.state(TX, RX, pos[mid], vel[mid], wf.carrier_hz, drone)
    lt = link_terms(lb, st.lam, st.sigma_m2, st.R1, st.R2, st.L, wf.bw_hz)
    # 잡음대역 보정: link_terms 의 P_n 은 점유대역 B 기준인데 시뮬 잡음은 fs 레이트 백색(var=1).
    #   매치드필터 출력 SNR 은 잡음 PSD 가 결정하므로 주입 진폭을 √(B/fs) 로 낮춰
    #   'per-sample 잡음전력 = kT₀F·fs' 와 등가로 만든다 — 이걸 빼먹으면 fs/B 가 큰
    #   협대역(LTE)이 광대역 대비 최대 ~2 dB 유리해지는 계통 편향이 생긴다.
    bw_corr = float(np.sqrt(wf.bw_hz / fs))
    dpi = lt["dpi_amp"] * bw_corr
    if target_amp == "rt" and st.rt_echo_ratio is not None:
        a_tgt = dpi * st.rt_echo_ratio               # RT 표적산란비(PO 대신, RT 백엔드)
    else:
        a_tgt = lt["a_tgt"] * bw_corr                 # PO 기반(권장)
    clutter_abs = tuple((dt, dpi * r) for (dt, r) in st.clutter)   # 비율→절대(직접파 스케일)
    true_Rb = st.tau * C0
    # 실효 per-sample 에코 SNR (주입 기준: 점유차 + 잡음대역 보정 반영) — CSV/노트북 인용용
    snr_echo_eff_db = float(lt["snr_echo_db"] + occ_db + 10 * np.log10(wf.bw_hz / fs))

    # --- 결정론적 surv(표적+DPI+클러터) 1회 + ECA 참조 프리컴퓨트 1회 ---
    # 표적 에코 = 기준성분만 코히어런트 기여(데이터 성분은 미지→상관에서 잡음화, 에코는 미약해 무시).
    tgt_det, ref_cpi = make_cpi(ref_frame, M, fs, st.tau, st.fd, a_tgt=a_tgt,
                                dpi_amp=0.0, clutter=(), abs_noise=True, noise_var=0.0)
    # DPI·클러터 = **전체 송신신호**(파일럿+데이터). ECA(파일럿 지연복제 부분공간)는 파일럿
    #   성분만 지울 수 있고 **데이터-DPI 잔류**가 남는다. (DPI 를 파일럿만으로 합성하면
    #   ECA 가 직접파를 '이상적으로 완전 제거'해 협대역이 비현실적으로 유리해지는 왜곡 방지.)
    #   ※ 현 챔버 동작점(DNR~60 dB)에선 이 잔류가 OFDM RE 직교성 덕에 잡음 플로어 아래로
    #     측정됨 — 강한 클러터/고 DNR 설정에서 유효해지는 안전장치다.
    dpi_det, _ = make_cpi(tx_frame, M, fs, 0.0, 0.0, a_tgt=0.0,
                          dpi_amp=dpi, clutter=clutter_abs, abs_noise=True, noise_var=0.0)
    surv_det = tgt_det + dpi_det
    canceller = ECACanceller(ref_cpi, n_taps)
    Ncpi = len(surv_det)
    nstd = np.sqrt(noise_var / 2.0)

    hits = 0
    scrs = []
    rb_errs = []
    example = None
    for k in range(N):
        rng = np.random.default_rng(seed0 + k)
        noise = nstd * (rng.standard_normal(Ncpi) + 1j * rng.standard_normal(Ncpi))
        res = canceller.cancel(surv_det + noise)
        Rb, f_d, rd = range_doppler(res, ref_cpi, fs, M, n_range=n_range)
        scr, (ri, di) = measure_scr(Rb, f_d, rd, true_Rb, st.fd)
        det, _, _ = ca_cfar_2d(rd, pfa=pfa)
        zd = int(np.argmin(np.abs(f_d)))
        det[zd, :] = False       # 0-도플러 능선 행 자체는 히트로 안 침(DPI/클러터 잔류 보호)
        hit = det[max(0, di - 1):di + 2, max(0, ri - 1):ri + 2].any()   # 참셀 ±1 에 CFAR 히트
        hits += int(hit)
        scrs.append(scr)
        # 위치정보 유용성 측정: 0-도플러 능선 제외 후 최강 피크의 Rb 오차 —
        #   '탐지되지만(도플러축) 위치는 못 준다(거친 ΔRb)' 를 수치로 드러낸다.
        rd2 = rd.copy(); rd2[max(0, zd - 1):zd + 2, :] = 0
        pk = peak_detection(Rb, f_d, rd2, det)
        if pk and pk["val"] > 0:
            rb_errs.append(abs(pk["Rb"] - true_Rb))
        if k == 0:
            example = (Rb, f_d, rd, st, lt, (ri, di), true_Rb)
    lo, hi = wilson_ci(hits, N)
    return dict(pd=hits / N, pd_lo=lo, pd_hi=hi,
                scr_mean=float(np.mean(scrs)), scr_std=float(np.std(scrs)),
                rb_err_m=(float(np.mean(rb_errs)) if rb_errs else None),
                snr_echo_eff_db=snr_echo_eff_db,
                link=lt, state=st, example=example, wf=wf, drone=drone, M=M, N=N,
                n_range=n_range, n_taps=n_taps)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import vizstyle
    vizstyle.use_korean()
    import matplotlib.pyplot as plt

    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    drone = "mavic4pro"
    pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)
    # 기본 채널 = Analytic + 무반사 약한 잔향 클러터(직접파 대비 비율).
    #   ※ ch = SionnaRTChannel(with_chamber=True) 로 바꾸면 클러터가 RT 실측 멀티패스로(GPU).
    ch = AnalyticChannel(clutter=CH_CLUTTER_RATIO)

    # ---------- 최소 셀: 5G NR 100 MHz @ 3.5 GHz (챔버서 표적 분리 잘 되는 광대역) ----------
    wf = nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")
    res = run_cell(wf, drone, pos, vel, lb, channel=ch, M=48, N=200)
    lt, st = res["link"], res["state"]

    print("=" * 72)
    print(f"최소 셀 — {wf.name} {wf.bw_hz/1e6:.0f}MHz@{wf.carrier_hz/1e9:.2f}GHz  /  {drone}  /  radial  (무반사 챔버)")
    print("-" * 72)
    print(f"  기하   R1={st.R1:.1f}m  R2={st.R2:.1f}m  L={st.L:.1f}m  "
          f"Rb={st.tau*C0:.1f}m  fd={st.fd:+.0f}Hz  β={st.beta:.0f}°  (n_range={res['n_range']}, n_taps={res['n_taps']})")
    print(f"  RCS    σ={10*np.log10(st.sigma_m2):.1f} dBsm  (반송파·자세평균, PO)")
    print(f"  [물리 유도]  에코SNR={lt['snr_echo_db']:+.1f} dB   "
          f"직접파SNR={lt['snr_direct_db']:+.1f} dB   DNR(직접-에코)={lt['dnr_db']:.1f} dB")
    print(f"  [측정 결과]  SCR={res['scr_mean']:.1f} ± {res['scr_std']:.1f} dB   "
          f"Pd={res['pd']*100:.0f}% [{res['pd_lo']*100:.0f},{res['pd_hi']*100:.0f}]   "
          f"(M={res['M']}, N={res['N']}, CFAR Pfa=1e-4)")

    # ---------- 3-신호 공정 비교 (같은 기하·예산 → SNR 이 신호마다 '나온다') ----------
    print("\n3-신호 SNR_in 비교  (같은 EIRP·기하·드론; B·λ·σ 만 신호 물리로 다름):")
    print(f"  {'신호':<15}{'fc[GHz]':>8}{'B[MHz]':>8}{'σ[dBsm]':>9}"
          f"{'ΔRb[m]':>8}{'잡음[dBm]':>11}{'에코SNR[dB]':>12}")
    sigs = [
        ("WiFi 80MHz",  wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G3")),
        ("LTE 10MHz",   lte_downlink(bw_hz=10e6, carrier_hz=1.843e9, occupancy="G3")),
        ("LTE 20MHz",   lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy="G3")),
        ("5G 100MHz",   wf),
    ]
    for nm, w in sigs:
        s = ch.state(TX, RX, pos[len(pos) // 2], vel[len(vel) // 2], w.carrier_hz, drone)
        L = link_terms(lb, s.lam, s.sigma_m2, s.R1, s.R2, s.L, w.bw_hz)
        pn_dbm = 10 * np.log10(L["P_noise_w"]) + 30
        print(f"  {nm:<15}{w.carrier_hz/1e9:>8.2f}{w.bw_hz/1e6:>8.0f}"
              f"{10*np.log10(s.sigma_m2):>9.1f}{C0/w.bw_hz:>8.1f}{pn_dbm:>11.1f}{L['snr_echo_db']:>12.1f}")
    print("  → 협대역(LTE)은 잡음(kTB)이 작아 per-sample SNR↑, 광대역(5G/WiFi)은 거리분해능↑.")
    print("    챔버서 실제 Pd 는 둘의 절충 + 시나리오(도플러)로 갈린다 → run_matrix.py 참조.")

    # ---------- RD 맵 그림 ----------
    Rb, f_d, rd, st, lt, (ri, di), true_Rb = res["example"]
    rdb = 20 * np.log10(rd / rd.max() + 1e-9)
    fig, ax = plt.subplots(figsize=(8.2, 5.4), constrained_layout=True)
    im = ax.pcolormesh(Rb, f_d, rdb, cmap="turbo", vmin=-50, vmax=0, shading="auto")
    ax.plot(true_Rb, st.fd, "o", mfc="none", mec="w", ms=15, mew=1.6, label="True target")
    det, _, _ = ca_cfar_2d(rd, pfa=1e-4)
    dd, dr = np.where(det)
    ax.plot(Rb[dr], f_d[dd], "x", color="w", ms=6, mew=1.2, alpha=0.7, label="CFAR detections")
    ax.set_xlabel("Bistatic range Rb [m]")
    ax.set_ylabel("Doppler f_d [Hz]")
    ax.set_title(
        f"Minimal cell RD map · {wf.name} {wf.bw_hz/1e6:.0f}MHz / {drone} / radial (anechoic chamber)\n"
        f"echo SNR={lt['snr_echo_db']:+.1f}dB (physics-derived) · "
        f"SCR={res['scr_mean']:.1f}dB (measured) · Pd={res['pd']*100:.0f}%",
        fontsize=10.5)
    fig.colorbar(im, ax=ax, label="Normalized [dB]")
    ax.legend(loc="upper right", fontsize=9)
    out = os.path.abspath(os.path.join(_HERE, "..", "outputs", "figures", "report5_min_cell.png"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"\nRD맵 저장 → {os.path.relpath(out, os.path.join(_HERE, '..'))}")


if __name__ == "__main__":
    main()
