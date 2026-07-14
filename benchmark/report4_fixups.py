# -*- coding: utf-8 -*-
"""
report4_fixups.py — **적대적 검증에서 드러난 오류의 정정값을 *측정*한다**
================================================================================
report4 는 6개 검증실험(E1..E6)의 JSON 을 읽어 조립된다. 그런데 적대적 재검증에서
그 JSON 의 일부 수치·귀속이 틀렸음이 드러났다. 규약상 **정정값도 손으로 적을 수 없다.**
→ 이 스크립트가 정정값을 **다시 측정하거나 원본 JSON 에서 재유도**해 하나의 JSON 에 남긴다.

각 항목은 셋 중 하나다:
  MEASURED  — GPU/CPU 로 새로 측정(대조군 포함)
  DERIVED   — 원본 JSON 의 원자료(rows/sample)에서 정확히 재계산 (손계산 아님)
  RETRACTED — 측정으로 뒷받침되지 않아 **철회**. 대체값 없음(모르는 건 모른다고 쓴다)

실행:  ~/.venvs/py312/bin/python benchmark/report4_fixups.py
출력:  outputs/report4_fixups.json
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

OUT = os.path.join(_ROOT, "outputs", "report4_fixups.json")


def J(name):
    with open(os.path.join(_ROOT, "outputs", name), encoding="utf-8") as f:
        return json.load(f)


# =========================================================================== #
#  F1 — [E1] CFAR: 원인 귀속 정정 + 손계산 제거 + CI 정정
# =========================================================================== #
def f1_cfar():
    """적대적 검증이 반증한 것:
      (a) 'LTE 2.45x = 거리축 과표본 상관' → **거짓**. 거리상관 0 인 WiFi 도 거리창을 좁히면
          부푼다 → 진짜 주범 중 하나는 **거리창(n_range)이 CFAR 훈련창보다 좁은 것**.
          → n_range 스윕 대조군을 **측정**한다.
      (b) '클러터를 넣어도 안 움직였다' → 이 실험엔 클러터 on/off 대조가 **없었다**.
          → 대조군을 **측정**한다.
      (c) 'Hann ±1 빈 -5.75 dB' → JSON 에 없는 손계산. → **계산해서 JSON 에 남긴다.**
      (d) Wilson CI 는 셀 독립을 가정 → 이 실험이 재고 있는 상관 때문에 **낙관적**.
          → 유효 독립셀(eff_indep_2d)로 CI 를 다시 낸다.
    """
    import verify_cfar as V           # gpu.pick() → torch import 순서를 이 모듈이 지킨다
    import torch
    from geometry import CH_CLUTTER_RATIO, chamber_window
    from channel import rt_chamber_clutter

    out = {}
    cf = J("verify_cfar.json")

    # ---- (c) Hann slow-time 창의 DFT 사이드로브 (M=48) --------------------- #
    M = cf["meta"]["M_cpi"]
    w = np.hanning(M)
    W = np.abs(np.fft.fft(w * np.exp(0j), 4096))
    # ±k 빈에서의 응답: 주파수 k/M → FFT 격자 index k*4096/M
    peak = W[0]
    side = {}
    for k in (1, 2, 3):
        idx = int(round(k * 4096 / M))
        side[f"bin_{k}"] = float(20 * np.log10(W[idx] / peak))
    out["hann_sidelobe_db"] = dict(M=M, **side, kind="MEASURED(계산)",
                                   note="slow-time Hann 의 DFT 응답. ±1 빈이 -6 dB 밖에 안 떨어져 "
                                        "0-도플러 DPI 잔류가 zd±1 행에도 실린다.")

    # ---- (a)(b) 대조군 측정 ------------------------------------------------ #
    from waveforms import nr_downlink, lte_downlink, wifi_80211ac
    WF = dict(
        WiFi80=wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G3"),
        LTE20=lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy="G3"),
        NR100=nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3"),
    )
    PFA = 1e-4
    GT = V.GT[V.GT_DEFAULT]                  # ((2,2),(6,6))
    GTK = V.gt_key(*GT)                      # 'g2x2_t6x6'  — rows 의 gt 는 문자열 키
    N_MAPS = 4000

    def ratio_at(chain, mode, n_range, dpi_amp=0.0, clutter=(), seed=101):
        op, _wd, diag = V.exp_chain(chain, N_MAPS, V.batch_for(chain), mode,
                                    dpi_amp=dpi_amp, clutter=clutter,
                                    n_range_op=n_range, seed=seed)
        row = [r for r in op["rows"] if r["gt"] == GTK
               and r["zd_mask_width"] == 1 and abs(r["pfa_nom"] - PFA) < 1e-12][0]
        return row, diag

    # (a) 거리창 스윕 — 파형 고유 성질(거리상관)인가, 하네스 설정(n_range)인가?
    nr_sweep = []
    for wname, ranges in (("LTE20", (6, 16, 24, 48)), ("WiFi80", (6, 16)), ("NR100", (6, 24))):
        wf = WF[wname]
        _nr_bench, ntaps = chamber_window(wf)
        ch = V.Chain(wf, ntaps)
        for nR in ranges:
            row, diag = ratio_at(ch, "noise", nR)
            nr_sweep.append(dict(
                wf=wname, n_range=nR, n_range_bench=int(_nr_bench),
                pfa_nom=PFA, pfa_emp=row["pfa_emp"], ratio=row["pfa_emp"] / PFA,
                hits=row["hits"], cells=row["cells"],
                rho_range_lag1=float(diag["rho_range"][0]),
                rho_doppler_lag1=float(diag["rho_doppler"][0]),
                cfar_train_radius_range=GT[0][1] + GT[1][1],
                all_cells_are_range_edge=bool(nR < 2 * (GT[0][1] + GT[1][1]) + 1),
            ))
            print(f"  [F1a] {wname} nR={nR:3d} → ratio {row['pfa_emp']/PFA:.2f} "
                  f"(rho_range {diag['rho_range'][0]:+.3f})", flush=True)
    out["range_window_sweep"] = dict(
        kind="MEASURED", n_maps=N_MAPS, mode="noise", gt=V.GT_DEFAULT, zd_mask_width=1,
        rows=nr_sweep,
        note="CFAR 거리축 훈련창 반경 = guard+train = %d 빈. n_range 가 그 2배+1 보다 좁으면 "
             "**모든 셀이 가장자리 셀**이 되어 훈련셀이 잘리고 서로 중첩된다."
             % (GT[0][1] + GT[1][1]))

    # (b) 정적 클러터 on/off 대조 (NR100, 운용형상)
    ch = V.Chain(WF["NR100"], chamber_window(WF["NR100"])[1])
    nR = chamber_window(WF["NR100"])[0]
    lt_dpi = cf["chain"]["NR100"]["dpi_amp"]
    cl_ratio = rt_chamber_clutter(WF["NR100"].carrier_hz) or CH_CLUTTER_RATIO
    cl_abs = tuple((dt, lt_dpi * r) for dt, r in cl_ratio)
    r_on, d_on = ratio_at(ch, "dpi_eca", nR, dpi_amp=lt_dpi, clutter=cl_abs, seed=77)
    r_off, d_off = ratio_at(ch, "dpi_eca", nR, dpi_amp=lt_dpi, clutter=(), seed=77)
    out["clutter_control"] = dict(
        kind="MEASURED", wf="NR100", n_maps=N_MAPS, n_range=int(nR), pfa_nom=PFA,
        clutter_on=dict(hits=r_on["hits"], pfa_emp=r_on["pfa_emp"],
                        ratio=r_on["pfa_emp"] / PFA, rho_range=float(d_on["rho_range"][0])),
        clutter_off=dict(hits=r_off["hits"], pfa_emp=r_off["pfa_emp"],
                         ratio=r_off["pfa_emp"] / PFA, rho_range=float(d_off["rho_range"][0])),
        clutter_below_dpi_db=float(20 * np.log10(max(r for _, r in cl_ratio))),
        note="Pfa 는 안 움직인다(결론 참). 그러나 RD 맵 자체는 미세하게 바뀐다 → "
             "'ECA 사영으로 정확히 0' 이라는 기전 설명은 틀렸다. 클러터는 지연된 tx(데이터 포함)라 "
             "ECA 부분공간 밖이다. 안 움직이는 진짜 이유는 클러터가 DPI 보다 훨씬 아래라 "
             "이미 소거불가인 DPI 데이터잔류에 묻히기 때문.")
    print(f"  [F1b] clutter on {r_on['hits']} hits / off {r_off['hits']} hits", flush=True)

    # ---- (d) 상관 보정 CI ------------------------------------------------- #
    def wilson(k, n):
        if n <= 0:
            return (0.0, 0.0)
        z = 1.959963985
        p = k / n
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
        return (max(0.0, c - h), c + h)

    ci_rows = []
    for wname in ("WiFi80", "LTE20", "NR100"):
        ch_j = cf["chain"][wname]["dpi_eca"]
        eff = ch_j["whiteness"]["eff_indep_frac_2d"]
        for r in ch_j["op"]["rows"]:
            if r["gt"] != GTK or r["zd_mask_width"] != 1:
                continue
            if r["pfa_nom"] not in (1e-3, 1e-4, 1e-5):
                continue
            n_eff = r["cells"] * eff
            lo_n, hi_n = wilson(r["hits"], r["cells"])           # 순진한 CI (JSON 이 쓴 것)
            k_eff = r["hits"] * eff
            lo_e, hi_e = wilson(k_eff, n_eff)                    # 상관 보정 CI
            ci_rows.append(dict(wf=wname, pfa_nom=r["pfa_nom"], pfa_emp=r["pfa_emp"],
                                ratio=r["pfa_emp"] / r["pfa_nom"],
                                eff_indep_2d=eff,
                                ci_naive=[lo_n, hi_n], ci_corrected=[lo_e, hi_e],
                                ratio_ci_corrected=[lo_e / r["pfa_nom"], hi_e / r["pfa_nom"]]))
    out["corrected_ci"] = dict(
        kind="DERIVED", rows=ci_rows,
        note="wilson_ci 는 셀 iid 를 가정하나 이 실험이 재는 대상이 바로 셀 상관이다. "
             "유효 독립셀 수 n_eff = cells × eff_indep_2d 로 다시 낸 CI. "
             "점추정(배율)은 불편이지만 원 CI 는 낙관적 → 소수 둘째 자리는 무의미.")
    return out


# =========================================================================== #
#  F2 — [E2] ECA: 동작점 dB 단위 오류 + 진폭/전력 혼동 → 최소검출속도 정정
# =========================================================================== #
def f2_eca():
    eca = J("verify_eca.json")
    out = {}

    # (a) §2 의 동작점: 코드는 lt["dnr_db"](=직접파/에코) 를 'DNR=직접파/잡음' 축에 찍었다.
    #     올바른 값은 lt["snr_direct_db"]. → link_budget 으로 다시 계산(MEASURED).
    from waveforms import nr_downlink, lte_downlink, wifi_80211ac
    from channel import AnalyticChannel, rt_chamber_clutter
    from scenarios import radial
    from geometry import TX, RX, CENTER, CH_CLUTTER_RATIO, SPEED, SPAN
    from link_budget import LinkBudget, link_terms
    from run_min_cell import EIRP_DBM

    pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)
    mid = len(pos) // 2
    rows = []
    for name, wf in (("5G NR 100MHz", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")),
                     ("WiFi 80MHz", wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G3")),
                     ("LTE 20MHz", lte_downlink(bw_hz=20e6, carrier_hz=1.843e9, occupancy="G3"))):
        cl = rt_chamber_clutter(wf.carrier_hz) or CH_CLUTTER_RATIO
        st = AnalyticChannel(clutter=cl).state(TX, RX, pos[mid], vel[mid],
                                               wf.carrier_hz, "mavic4pro")
        lt = link_terms(LinkBudget(eirp_dbm=EIRP_DBM), st.lam, st.sigma_m2,
                        st.R1, st.R2, st.L, wf.bw_hz)
        rows.append(dict(name=name,
                         plotted_as_dnr_db=lt["dnr_db"],           # 코드가 찍은 값 (직접파/에코)
                         correct_direct_over_noise_db=lt["snr_direct_db"],
                         err_db=lt["dnr_db"] - lt["snr_direct_db"],
                         snr_echo_per_sample_db=lt["snr_echo_db"]))
    out["dnr_operating_point"] = dict(
        kind="MEASURED", rows=rows,
        note="verify_eca.py 의 §2 그림 x축은 '직접파/잡음'인데 동작점 마커는 '직접파/에코'로 찍혔다. "
             "두 값의 차이가 곧 per-sample 에코 SNR(음수)이다.")

    # (b) 표적 손실 vs 도플러 — 플롯된 loss_db 는 20log(진폭), 이론(1-sinc²)은 에너지.
    #     JSON rows 에 energy_loss_db 가 있으므로 **전력 -3 dB** 교차점을 재유도한다(DERIVED).
    def cross(fds, loss, th):
        ok = np.where(loss > -th)[0]
        if not len(ok) or ok[0] == 0:
            return None
        i = ok[0]
        x0, x1, y0, y1 = fds[i - 1], fds[i], loss[i - 1], loss[i]
        return float(x0 + ((-th) - y0) * (x1 - x0) / (y1 - y0 + 1e-30))

    notch = []
    for s in eca["S4_target_loss"]:
        fds = np.array([r["fd_hz"] for r in s["rows"]])
        amp = np.array([r["loss_db"] for r in s["rows"]])          # 20log|RD| (코드가 쓴 것)
        eng = np.array([r["energy_loss_db"] for r in s["rows"]])   # 10log(에너지) — 이론과 맞는 것
        thy = np.array([r["theory_loss_db"] for r in s["rows"]])
        m = (eng > -60) & (thy > -60)          # fd=0 의 이론 센티널(-3000) 제외
        fd3_e, fd1_e = cross(fds, eng, 3.0), cross(fds, eng, 1.0)
        fd3_t = cross(fds, thy, 3.0)
        notch.append(dict(
            name=s["name"], M=s["M"], T_cpi_ms=s["T_cpi_ms"], dfd_hz=s["dfd_hz"],
            hz_per_ms=s["hz_per_ms"],
            fd_3db_reported_hz=s["fd_3db_hz"], v_3db_reported_ms=s["v_3db_ms"],
            fd_3db_energy_hz=fd3_e, fd_1db_energy_hz=fd1_e,
            v_3db_energy_ms=(fd3_e / s["hz_per_ms"]) if fd3_e else None,
            v_1db_energy_ms=(fd1_e / s["hz_per_ms"]) if fd1_e else None,
            fd_3db_theory_hz=fd3_t,
            fd_3db_over_dfd_energy=(fd3_e / s["dfd_hz"]) if fd3_e else None,
            v_overstated_factor=(s["v_3db_ms"] / (fd3_e / s["hz_per_ms"])) if fd3_e else None,
            max_dev_energy_vs_theory_db=float(np.max(np.abs(eng[m] - thy[m]))) if m.any() else None,
            bench_fd_hz=s["bench_fd_hz"], bench_loss_db=s["bench_loss_db"],
        ))
    out["eca_notch"] = dict(
        kind="DERIVED", rows=notch,
        note="플롯·헤드라인이 쓴 loss_db 는 20log10(RD 진폭비)인데 이론곡선 1-sinc²(f_d·T_cpi) 는 "
             "에너지다. JSON 의 energy_loss_db 는 이론과 일치한다 → 레이더 관례(전력 -3 dB)로 "
             "노치폭·최소검출속도를 다시 낸다.")

    # (c) ECA 상쇄깊이 바닥 (S1) — 'float64 ECA 는 무한히 완벽' 이라는 §2 전제는 거짓
    depth = []
    for s in eca["S1_depth_vs_taps"]:
        rr = {r["n_taps"]: r for r in s["rows"]}
        nb = s["taps_used_in_bench"]
        tp = np.array(sorted(rr))
        dp = np.array([rr[t]["depth_full_db"] for t in tp])
        d_bench = float(np.interp(nb, tp, dp))          # 벤치 탭수가 스윕 격자에 없으면 보간
        depth.append(dict(name=s["name"], n_taps_bench=nb,
                          depth_at_bench_taps_db=d_bench,
                          depth_at_bench_taps_is_interpolated=bool(nb not in rr),
                          depth_saturated_db=s["rows"][-1]["depth_full_db"],
                          depth_dpi_only_db=s["rows"][-1]["depth_dpi_db"],
                          n_clutter=s["n_clutter"], clutter_src=s["clutter_src"],
                          spread_samples=s["spread_samples"],
                          steady_vs_circular_db=abs(s["rows"][-1]["depth_full_db"]
                                                    - s["rows"][-1]["depth_full_steady_db"])))
    out["eca_depth"] = dict(kind="DERIVED", rows=depth,
                            note="DPI 만이면 float64 한계(200 dB+)까지 지운다. RT 실측 잔향이 들어오면 "
                                 "30~56 dB 에서 **포화**한다 → ECA 에는 단단한 바닥이 있다.")

    # (d) ADC 는 병목이 아니다 (S2)
    adc = []
    for s in eca["S2_dnr"]:
        r0 = s["rows"][0]
        rl = s["rows"][-1]
        gaps = [abs(r[f"depth_adc{b}_db"] - r["depth_float_db"]) for r in s["rows"] for b in (12, 14, 16)]
        adc.append(dict(name=s["name"],
                        dnr_lo=r0["dnr_db"], dnr_hi=rl["dnr_db"],
                        resid_float_lo_db=r0["resid_float_db"], resid_float_hi_db=rl["resid_float_db"],
                        resid_rises_db=rl["resid_float_db"] - r0["resid_float_db"],
                        dnr_rises_db=rl["dnr_db"] - r0["dnr_db"],
                        max_adc_vs_float_gap_db=float(max(gaps))))
    out["eca_adc"] = dict(kind="DERIVED", rows=adc,
                          note="잔류가 DNR 과 1:1 로 상승 = 깊이 일정(=바닥). ADC 12/14/16-bit 는 "
                               "float64 와 1 dB 안쪽 → **양자화는 병목이 아니다**.")

    # (e) §4b 는 구조적으로 공허 — gate 가 항상 RD 창보다 넓다
    gate = []
    for s in eca["S4b_range_gate"]:
        rd_window_m = s["sample_m"] * (s["n_taps"] - 8)     # chamber_window: n_taps = n_range+8
        gate.append(dict(name=s["name"], gate_m=s["gate_m"], rd_window_m=rd_window_m,
                         all_inside_gate=all(r["inside_gate"] for r in s["rows"]),
                         n_rows=len(s["rows"])))
    out["eca_gate_vacuous"] = dict(
        kind="DERIVED", rows=gate,
        note="ECA 탭 창(n_taps·dr)이 RD 거리창(n_range·dr)보다 항상 넓다(n_taps = n_range+8). "
             "따라서 '탭 창 밖 표적' 은 RD 맵에 애초에 나타날 수 없다 → §4b 는 시연 불가.")

    out["eca_precursor_hypothesis"] = dict(
        kind="RETRACTED",
        note="ECA 바닥의 원인으로 '인과 FIR 이 서브샘플 지연의 보간커널 왼쪽 지지를 못 가진다'는 "
             "가설이 제기됐으나 **우리 JSON 에 대조군이 없다** → 이 리포트는 원인을 단정하지 않는다.")
    return out


# =========================================================================== #
#  F3 — [E3] 모호함수: 바닥 유령 마진을 **검출기 격자**에서 다시 잰다
# =========================================================================== #
def f3_ambiguity():
    """원 스크립트는 chi 를 0.05 m 미세격자의 **상대 오프셋**(+3.53 m)에서 읽었다.
    그러나 range_doppler 의 거리축은 Rb = k·c/fs 의 **절대 격자**(빈 2.4~9.8 m)다.
    표적도 유령도 빈 중심에 없다 → 검출기가 실제로 보는 셀에서 다시 계산한다(MEASURED).
    덧붙여 표적의 서브빈 위치를 한 빈에 걸쳐 훑어 마진의 **변동폭**을 낸다."""
    import verify_ambiguity as A
    import torch
    from bistatic_scene import C0

    amb = J("verify_ambiguity.json")
    wfs = A.waveform_set()
    rows = []
    for key, name, wf in wfs:
        w = amb["waveforms"][key]
        g = w["ghost"]
        fs, Lf = w["fs_hz"], w["Lf"]
        bin_m = C0 / fs
        rb_t, rb_g = g["rb_true_m"], g["rb_ghost_m"]
        fd_t, fd_g = g["fd_true"], g["fd_ghost"]
        a_g = 10 ** (g["amp_db"] / 20.0)                     # 유령/표적 전압비
        rf, _Lf = A.ref_frame_of(wf)

        # 검출기 거리빈 중심 (k·c/fs). 유령에 가장 가까운 빈 = 유령이 앉는 셀.
        kg = int(round(rb_g / bin_m))
        rb_cell = kg * bin_m

        def chi_db(d_rb, d_fd):
            """|chi| [dB re 피크] — 검출기와 동일한 처리(프레임 AF × Hann slow-time AF)."""
            tau = np.array([d_rb / C0, 0.0])
            fdv = np.array([d_fd, 0.0])
            Afr = A.frame_af(rf, fs, tau, fdv)               # (2,2)
            D = A.slow_time_af(w["M"], Lf, fs, fdv)          # (2,)
            v = abs(complex(Afr[0, 0]) * complex(D[0]))
            v0 = abs(complex(Afr[1, 1]) * complex(D[1]))     # 피크 (0,0)
            return float(20 * np.log10(max(v, 1e-30) / max(v0, 1e-30)))

        # 유령셀에서: (i) 표적 자신의 응답 누설, (ii) 유령 자신의 응답
        tgt_leak = chi_db(rb_cell - rb_t, fd_g - fd_t)       # 표적 피크는 (rb_t, fd_t)
        ghost_resp = 20 * np.log10(a_g) + chi_db(rb_cell - rb_g, 0.0)
        margin = ghost_resp - tgt_leak

        # 표적의 서브빈 위치를 한 빈에 걸쳐 훑는다(궤적을 따라 실제로 변한다)
        sweep = []
        for frac in np.linspace(-0.5, 0.5, 21):
            off = frac * bin_m
            kg2 = int(round((rb_g + off) / bin_m))
            rc = kg2 * bin_m
            tl = chi_db(rc - (rb_t + off), fd_g - fd_t)
            gr = 20 * np.log10(a_g) + chi_db(rc - (rb_g + off), 0.0)
            sweep.append(gr - tl)
        rows.append(dict(
            key=key, name=name, bin_m=bin_m, ghost_bin_index=kg,
            rb_true_m=rb_t, rb_ghost_m=rb_g, rb_ghost_cell_m=rb_cell,
            cell_minus_true_m=rb_cell - rb_t,
            ghost_amp_db=g["amp_db"],
            target_leak_into_ghost_cell_db=tgt_leak,
            ghost_response_in_cell_db=ghost_resp,
            margin_db=margin,
            margin_reported_finegrid_db=-g["sidelobe_over_ghost_db"],
            margin_subbin_min_db=float(np.min(sweep)),
            margin_subbin_max_db=float(np.max(sweep)),
            margin_subbin_span_db=float(np.max(sweep) - np.min(sweep)),
        ))
        print(f"  [F3] {name:16s} bin {bin_m:5.2f} m  margin {margin:+6.1f} dB "
              f"(fine-grid said {-g['sidelobe_over_ghost_db']:+.1f}) "
              f"subbin [{min(sweep):+.1f},{max(sweep):+.1f}]", flush=True)

    out = {"ghost_margin_on_detector_grid": dict(
        kind="MEASURED", rows=rows,
        note="유령이 앉는 **검출기 셀**에는 표적 자신의 응답도 들어온다. 미세격자에서 읽은 마진은 "
             "검출기가 계산할 수 없는 값이다. 표적의 서브빈 위치에 따라 마진이 크게 흔들리므로 "
             "**단일 값 인용 불가**.")}

    # 챔버 창 안의 모호 봉우리 — 원 JSON 이 이미 세고 있었다(요약이 틀렸다)
    pk = []
    for key, w in amb["waveforms"].items():
        inch = w["peaks_in_chamber"]
        strongest = max(inch, key=lambda p: p["db"]) if inch else None
        pk.append(dict(key=key, name=w["name"], n_peaks_in_chamber=w["n_peaks_in_chamber"],
                       strongest_in_chamber=strongest,
                       psl_chamber_db=w["psl_chamber_db"],
                       strongest_global=w["amb_peaks"][0] if w["amb_peaks"] else None))
    out["peaks_in_chamber"] = dict(
        kind="DERIVED", rows=pk,
        note="'모호 봉우리는 전부 km 스케일, 챔버 창 안엔 하나도 없다' 는 자기 JSON 이 반박한다.")

    # 코드베이스 규약 충돌: c/B (바이스태틱 Rb 축) vs c/2B (waveforms.range_resolution_m)
    conv = []
    for key, w in amb["waveforms"].items():
        conv.append(dict(key=key, ref_bw_hz=w["ref_bw_hz"],
                         drb_bistatic_c_over_B_m=w["dR_theory_m"],
                         range_res_property_c_over_2B_m=w["dR_mono_theory_m"],
                         factor=w["dR_theory_m"] / w["dR_mono_theory_m"]))
    out["resolution_convention_conflict"] = dict(
        kind="DERIVED", rows=conv,
        note="waveforms.Waveform.range_resolution_m 은 c/(2B) 를 돌려주고 그 값이 report2/문서의 "
             "공표수치(WiFi 2.0 / LTE 8.3 / SSB 20.8 m)를 만든다. 그러나 RD 맵의 Rb 축은 "
             "Rb = c·tau 라 분해능이 c/B 다 → 코드베이스가 **두 규약을 동시에** 쓰고 있다. "
             "RD 맵·유령 분리 논의에 c/2B 를 쓰면 2배 낙관.")
    return out


# =========================================================================== #
#  F4 — [E4] 링크버짓: 손실분해의 잡음바닥 아티팩트 제거
# =========================================================================== #
def f4_linkbudget():
    lb = J("verify_linkbudget.json")
    out = {}
    M = lb["BE_processing_gain"]["M"]

    # (a) Hann 코히어런트 창손실의 **정확값** — 인용된 10log(2/3) 는 점근값
    w = np.hanning(M)
    exact = float(10 * np.log10((w.sum() ** 2) / (M * (w ** 2).sum())))
    asym = float(10 * np.log10(2 / 3))
    rows = []
    for r in lb["BE_processing_gain"]["waveforms"]:
        rows.append(dict(name=r["name"], reported_db=r["loss_hann_window_db"],
                         exact_db=exact, asymptotic_quoted_db=asym))
    out["hann_window_loss"] = dict(
        kind="DERIVED", M=M, exact_db=exact, asymptotic_quoted_db=asym, rows=rows,
        note="창손실은 파형 무관 상수인데 파형별로 다르게 보고됐다 — 그 산포는 몬테카를로 "
             "잡음바닥 추정오차다. np.hanning(48) 의 정확한 코히어런트 손실 = (Σw)²/(M·Σw²).")

    # (b) straddle: *_worst 키는 잡음바닥이 다른 두 추정의 뺄셈 → *_half 키를 쓴다
    st = []
    for r in lb["BE_processing_gain"]["waveforms"]:
        st.append(dict(name=r["name"],
                       range_worst_reported_db=-r["loss_straddle_rng_worst_db"],
                       range_half_db=r["loss_straddle_rng_half_db"],
                       dopp_worst_reported_db=-r["loss_straddle_dopp_worst_db"],
                       dopp_half_db=r["loss_straddle_dopp_half_db"],
                       b_over_fs=r["bw_hz"] / r["fs_hz"]))
    out["straddle"] = dict(
        kind="DERIVED", rows=st, hann_scallop_max_db=-1.3640,
        note="*_worst 는 잡음바닥 추정이 서로 다른 두 실행의 뺄셈이라 편향됐다 — 보고된 LTE 도플러 "
             "straddle 은 Hann 반빈 scallop 의 이론 최대치조차 넘는다(물리적으로 불가능). "
             "같은 시드에서 분모가 상쇄되는 *_half 키가 자기일관 값이다.")

    # (c) CFAR 손실은 파형 의존 — 실제 맵 크기에서 훈련셀 수를 센다
    g, t = tuple(lb["BE_processing_gain"]["cfar"]["guard"]), tuple(lb["BE_processing_gain"]["cfar"]["train"])
    pfa = lb["BE_processing_gain"]["cfar"]["pfa"]

    def ntrain_range(M, nR):
        gd, gr = g
        td, tr = t
        lo, hi = 10 ** 9, 0
        for d in range(M):
            for rr in range(nR):
                d0, d1 = max(0, d - gd - td), min(M, d + gd + td + 1)
                r0, r1 = max(0, rr - gr - tr), min(nR, rr + gr + tr + 1)
                e0, e1 = max(0, d - gd), min(M, d + gd + 1)
                f0, f1 = max(0, rr - gr), min(nR, rr + gr + 1)
                n = (d1 - d0) * (r1 - r0) - (e1 - e0) * (f1 - f0)
                lo, hi = min(lo, n), max(hi, n)
        return lo, hi

    cf = []
    for r in lb["BE_processing_gain"]["waveforms"]:
        nR = r["n_range"]
        lo, hi = ntrain_range(M, nR)
        def loss(n):
            a = n * (pfa ** (-1.0 / n) - 1.0)
            return float(10 * np.log10(a / (-math.log(pfa))))
        cf.append(dict(name=r["name"], n_range=nR, M=M,
                       n_train_min=lo, n_train_max=hi,
                       cfar_loss_min_db=loss(hi), cfar_loss_max_db=loss(lo),
                       degenerate=bool(nR <= g[1] + t[1]),
                       reported_n_train=lb["BE_processing_gain"]["cfar"]["n_train_full"]))
    out["cfar_loss"] = dict(
        kind="DERIVED", pfa=pfa, guard=list(g), train=list(t), rows=cf,
        note="보고서는 Ntrain=264 하나로 CFAR 손실을 냈지만 264 는 5G(n_range=24)에만 도달한다. "
             "LTE(n_range=6)는 CFAR 거리축 훈련반경(guard+train=%d)보다 좁아 **모든 셀이 "
             "가장자리** → 훈련셀이 39~87 개로 줄고 손실이 커진다. 사실상 1D 도플러 CFAR 로 퇴화."
             % (g[1] + t[1]))

    # (d) 관측시간 비대칭 — 물리가 아니라 규약
    out["cpi_asymmetry"] = dict(
        kind="DERIVED", cpi_ms=lb["C_noise_floor"]["cpi_ms"],
        span_db=lb["C_noise_floor"]["cpi_span_db"],
        note="frame_len() 이 파형마다 프레임을 다르게 정의해(WiFi 1 ms 패킷슬롯, LTE 1 ms, 5G 0.5 ms) "
             "같은 M=48 이 5G 에는 절반의 CPI 시간을 준다 → 3.01 dB. 통제변수여야 할 관측시간이 "
             "통제되지 않았다.")

    # (e) '파일럿이 송신에너지의 0.4%' 는 두 물리량의 혼동 → 정확히 분해
    from waveforms import wifi_80211ac
    from run_min_cell import frame_len
    wf = wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9, occupancy="G3")
    E_ref = float(np.sum(np.abs(wf.ref) ** 2))
    E_tx = float(np.sum(np.abs(wf.tx) ** 2))
    Lf = frame_len(wf)
    out["wifi_pilot_fraction"] = dict(
        kind="MEASURED",
        pilot_over_tx_energy=E_ref / E_tx,
        pilot_over_tx_energy_db=float(10 * np.log10(E_ref / E_tx)),
        packet_duty=len(wf.tx) / Lf,
        packet_duty_db=float(10 * np.log10(len(wf.tx) / Lf)),
        pilot_power_frac_db_json=[r for r in lb["BE_processing_gain"]["waveforms"]
                                  if r["name"].startswith("WiFi")][0]["pilot_power_frac_db"],
        note="JSON 의 pilot_power_frac_db 는 E_ref/L_frame 이고 그 프레임의 대부분은 무음 패딩이다. "
             "'파일럿이 송신에너지의 0.4%' 는 서로 다른 두 양(파일럿 비율 × 패킷 듀티)을 합쳐 "
             "잘못 라벨한 것.")

    # (f) D2: 부엽 융단이 CFAR 문턱을 올린다 (자기가림) — 원 JSON 의 pedestal 을 그대로 인용하되
    #     'CFAR 는 융단을 못 본다' 는 인과 주장은 철회
    out["pedestal_causality"] = dict(
        kind="RETRACTED",
        pedestal_rows=lb["D2_pedestal"],
        note="'CFAR 는 국소 잡음을 보므로 부엽 융단이 Pd 에 영향 없다' 는 인과 주장은 틀렸다 — "
             "CFAR 훈련창은 표적의 부엽 위에 놓인다(고전적 표적 자기가림). 이 동작점에서 Pd 가 "
             "안 깨지는 것은 피크가 잡음보다 압도적으로 높기 때문이지 CFAR 가 융단을 못 보기 "
             "때문이 아니다. 자기가림의 크기는 **우리 JSON 에 측정돼 있지 않다** → 단정하지 않는다.")
    return out


# =========================================================================== #
#  F5 — [E5] 관측가능성: ΔRb 재측정 → 껍질부피 재계산, 속도 CRLB 스케일 정정
# =========================================================================== #
def f5_observability():
    import torch
    obs = J("verify_observability.json")
    amb = J("verify_ambiguity.json")
    out = {}

    # (a) 속도 CRLB: 스케일 좌표 u_v = δv/t_obs 인데 코드가 sp/t_obs 로 나눴다 → ×t_obs²
    t_obs = obs["gramian"]["t_obs_s"]
    fx = []
    for k, v in obs["fixes"].items():
        if k.startswith("_"):
            continue
        fx.append(dict(config=k, rank=v["rank"],
                       sigma_pos_m=v["sigma_pos_m"], pos_rms_m=v["pos_rms_m"],
                       sigma_vel_reported_ms=v["sigma_vel_ms"],
                       sigma_vel_corrected_ms=[x * t_obs ** 2 for x in v["sigma_vel_ms"]]))
    out["crlb"] = dict(
        kind="DERIVED", t_obs_s=t_obs, factor=t_obs ** 2, rows=fx,
        note="위치 CRLB 는 속도좌표 재스케일에 불변 → **2RX 위치 0.22 m 는 그대로 유효**. "
             "속도 CRLB 만 t_obs² = %g 배 낙관적으로 찍혔다." % (t_obs ** 2))

    # (b) ΔRb: 관측가능성 스크립트는 자기상관을 1샘플 선형보간으로 재 계통 과소.
    #     모호함수 스크립트는 0.05 m 미세격자로 같은 양을 정확히 쟀다 → 그 값을 쓴다.
    KMAP = {"wifi80_G1": "wifi_G1", "lte20_G1": "lte_G1",
            "nr100_G1": "nr_G1", "nr100_G3": "nr_G3"}
    cells = {c["key"]: c for c in obs["cells"]}
    drb = []
    for k, c in cells.items():
        a = amb["waveforms"][KMAP[k]]
        d_old = c["drb_m"]
        d_ac = a["dR_meas_m"]                       # 미세격자 -3dB 전폭 (바이스태틱 Rb 축)
        d_new = max(d_ac, c["bin_m"])               # 샘플빈 한계
        drb.append(dict(key=k, label=c["label"],
                        drb_ac_reported_m=c["drb_ac_m"], drb_ac_finegrid_m=d_ac,
                        bin_m=c["bin_m"], drb_used_reported_m=d_old, drb_used_corrected_m=d_new,
                        changed=abs(d_new - d_old) > 1e-6))
    out["drb"] = dict(kind="DERIVED", rows=drb,
                      note="verify_observability 의 자기상관 -3dB 반폭은 4개 중 3개에서 1샘플 미만이라 "
                           "사실상 선형보간 외삽이었다. verify_ambiguity 가 같은 양을 0.05 m 격자에서 "
                           "정확히 쟀으므로 그 값으로 교체한다.")

    # (c) 껍질 부피 재계산 — GPU 복셀 적분 (원 스크립트와 동일 격자)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ch = obs["meta"]["chamber"]
    dx = obs["meta"]["grid"]["dx"]
    tx = torch.tensor(obs["meta"]["tx"], dtype=torch.float32, device=dev)
    rx = torch.tensor(obs["meta"]["rx"], dtype=torch.float32, device=dev)
    xs = torch.arange(dx / 2, ch[0], dx, dtype=torch.float32, device=dev)
    ys = torch.arange(dx / 2, ch[1], dx, dtype=torch.float32, device=dev)
    zs = torch.arange(dx / 2, ch[2], dx, dtype=torch.float32, device=dev)
    vox = dx ** 3

    def shell_volume(rb_true, width):
        tot = 0.0
        for z0 in range(0, len(zs), 32):
            Z = zs[z0:z0 + 32]
            X, Y, ZZ = torch.meshgrid(xs, ys, Z, indexing="ij")
            R1 = torch.sqrt((X - tx[0]) ** 2 + (Y - tx[1]) ** 2 + (ZZ - tx[2]) ** 2)
            R2 = torch.sqrt((X - rx[0]) ** 2 + (Y - rx[1]) ** 2 + (ZZ - rx[2]) ** 2)
            L = float(torch.linalg.norm(tx - rx))
            Rb = R1 + R2 - L
            tot += float((torch.abs(Rb - rb_true) <= width / 2).sum()) * vox
        return tot

    sh = []
    for r in drb:
        c = cells[r["key"]]
        v_old_check = shell_volume(c["Rb_true"], r["drb_used_reported_m"])
        v_new = shell_volume(c["Rb_true"], r["drb_used_corrected_m"])
        sh.append(dict(key=r["key"], label=c["label"],
                       drb_reported_m=r["drb_used_reported_m"],
                       drb_corrected_m=r["drb_used_corrected_m"],
                       v_shell_json_m3=c["v_shell_m3"],
                       v_shell_recomputed_m3=v_old_check,
                       v_shell_corrected_m3=v_new,
                       frac_corrected=v_new / obs["meta"]["grid"]["chamber_m3"],
                       reproduces_json=abs(v_old_check - c["v_shell_m3"]) / max(c["v_shell_m3"], 1e-9) < 0.02))
        print(f"  [F5] {c['label']:22s} dRb {r['drb_used_reported_m']:5.2f}->{r['drb_used_corrected_m']:5.2f} m  "
              f"V {c['v_shell_m3']:7.1f}->{v_new:7.1f} m3", flush=True)
    out["shell_volume"] = dict(
        kind="MEASURED", chamber_m3=obs["meta"]["grid"]["chamber_m3"], dx=dx, rows=sh,
        note="정정된 ΔRb 로 등-Rb 껍질 부피를 다시 적분했다. reproduces_json=True 는 같은 격자로 "
             "원 값을 재현했다는 뜻(방법 검증).")

    out["rayleigh_quotient"] = dict(
        kind="RETRACTED",
        json_value_tangential=obs["gramian"]["tangential"]["rayleigh_generator"],
        note="요약문이 인용한 '레일리 몫 ~1e-19' 는 JSON 어디에도 없다. JSON 의 유일한 값은 "
             "tangential 의 2.14e-3 이고, 그 값은 회전 생성자의 속도블록 스케일 버그로 오염돼 있다. "
             "→ 이 리포트는 레일리 몫을 인용하지 않는다. 회전 대칭의 증거는 **비선형 원본**에서 "
             "직접 잰 max|dRb|=%.1e m / max|dfd|=%.1e Hz 다(이건 스케일과 무관하다)."
             % (obs["gramian"]["exact_rotation"]["max_dRb_m"],
                obs["gramian"]["exact_rotation"]["max_dfd_hz"]))
    return out


# =========================================================================== #
#  F6 — [E6] 바닥 유령: 표적 누설을 유령으로 센 인덱싱 결함 정정
# =========================================================================== #
def f6_ghost():
    from scipy.stats import chi2
    gh = J("verify_ghost_impact.json")
    out = {}

    # (a) p_false 정정 — 격자무관 지표(margin>0 AND bins_apart>=2)로 재계산
    C = gh["C_cfar"]
    per = {}
    for r in C:
        key = (r["wf"], r["scen"])
        ba = r["bins_apart"]
        ba0 = ba[0] if isinstance(ba, (list, tuple)) else ba
        m = r["ghost_margin_db"]
        sep_ok = (ba0 is not None and ba0 >= 2)
        above = (m is not None and m > 0)
        per.setdefault(key, []).append(dict(i=r["i"], p_false_reported=r["ghost_p_false"],
                                            bins_apart=ba0, margin_db=m,
                                            counts_corrected=bool(sep_ok and above)))
    rows = []
    for (wfn, scen), v in sorted(per.items()):
        pf_rep = float(np.mean([x["p_false_reported"] for x in v]))
        pf_cor = float(np.mean([1.0 if x["counts_corrected"] else 0.0 for x in v]))
        rows.append(dict(wf=wfn, scen=scen, n_snapshots=len(v),
                         p_false_reported=pf_rep, p_false_corrected=pf_cor, cells=v))
    # 파형별 평균 + 3-of-5 트랙개시
    def track35(p):
        return float(sum(math.comb(5, k) * p ** k * (1 - p) ** (5 - k) for k in (3, 4, 5)))

    wf_sum = []
    for wfn in sorted({r["wf"] for r in rows}):
        rr = [r for r in rows if r["wf"] == wfn]
        p_rep = float(np.mean([r["p_false_reported"] for r in rr]))
        p_cor = float(np.mean([r["p_false_corrected"] for r in rr]))
        pw = gh["D_tracker"]["per_wf"][wfn]
        wf_sum.append(dict(
            wf=wfn,
            p_false_reported=p_rep, p_false_corrected=p_cor,
            track35_reported=pw["p_track_ghost_separate"], track35_corrected=track35(p_cor),
            random_tracks_per_window=pw["n_random_tracks_per_window"],
            ratio_reported=(pw["p_track_ghost_separate"] / pw["n_random_tracks_per_window"]
                            if pw["n_random_tracks_per_window"] > 0 else None),
            ratio_corrected=(track35(p_cor) / pw["n_random_tracks_per_window"]
                             if pw["n_random_tracks_per_window"] > 0 else None),
            per_scen={r["scen"]: dict(rep=r["p_false_reported"], cor=r["p_false_corrected"])
                      for r in rr}))
    out["p_false"] = dict(
        kind="DERIVED", by_cell=rows, by_waveform=wf_sum,
        note="run_min_cell 의 유령 3x3 박스 [gi-1,gi+1] 은 bins_apart==2 일 때 표적 검출박스 "
             "[ri-1,ri+1] 과 열 ri+1 을 **공유**한다 → 표적 주엽 스커트의 CFAR 히트가 '유령이 별개 "
             "표적으로 찍혔다'로 계수됐다. 격자무관 지표(유령이 CFAR 문턱 위 AND 2빈 이상 떨어짐)로 "
             "다시 세면 크게 줄고, 'tangential 이 최악' 은 정반대가 된다.")

    # (b) 랜덤 FA 측정의 검정력 — Poisson CI
    fa = []
    for r in gh["fa_rows"]:
        k, n = r["fa"], r["cells"]
        lo = chi2.ppf(0.025, 2 * k) / 2 / n if k > 0 else 0.0
        hi = chi2.ppf(0.975, 2 * (k + 1)) / 2 / n
        fa.append(dict(wf=r["wf"], fa_count=k, cells=n, pfa_emp=r["pfa_emp"],
                       pfa_ci95=[float(lo), float(hi)],
                       nominal=gh["config"]["pfa"],
                       distinguishable_from_nominal=bool(lo > gh["config"]["pfa"]
                                                         or hi < gh["config"]["pfa"])))
    out["fa_power"] = dict(
        kind="DERIVED", rows=fa,
        note="FA 개수가 1~5 개뿐이다 → Poisson 95%% CI 가 자릿수 폭이다. 5G·WiFi 의 경험 Pfa 는 "
             "명목 1e-4 와 **통계적으로 구별 불가**. 이 하네스로는 Pfa 를 잴 수 없다(그건 E1 의 일).")

    # (c) 게이트의 실제 결합 포함률 — 저장된 샘플에서 직접 센다
    s = gh["E_mitigation"]["sample"]
    g = gh["E_mitigation"]["gate"]
    sep = np.array(s["ghost_sep"], float)
    amp = np.array(s["ghost_amp"], float)
    inside = (sep >= g["sep_lo"]) & (sep <= g["sep_hi"]) & \
             (amp >= g["amp_lo"]) & (amp <= g["amp_hi"])
    drb = gh["E_mitigation"]["cost"]["d_rb_m"]
    res = sep > drb
    # 저장된 샘플은 800점뿐 → 챔버 전역에서 새로 몬테카를로 (MEASURED)
    from geometry import TX as _TX, RX as _RX, floor_ghost as _fg
    rng = np.random.default_rng(20260714)
    NMC = 20000
    P = np.column_stack([rng.uniform(1, 29, NMC), rng.uniform(1, 19, NMC),
                         rng.uniform(0.5, 9, NMC)])
    Vv = rng.normal(0, 2, (NMC, 3))
    smc, amc, dmc = [], [], []
    for i in range(NMC):
        gg = _fg(_TX, _RX, P[i], Vv[i], 3.5e9, pol="V")
        from bistatic_scene import bistatic_params as _bp
        bp = _bp(_TX, _RX, P[i], Vv[i], 3.5e9)
        smc.append(gg["rb_m"] - bp["Rb"])
        amc.append(20 * np.log10(max(gg["amp_ratio"], 1e-12)))
        dmc.append(gg["fd"] - bp["fd"])
    smc, amc, dmc = np.array(smc), np.array(amc), np.array(dmc)
    in_mc = (smc >= g["sep_lo"]) & (smc <= g["sep_hi"]) & \
            (amc >= g["amp_lo"]) & (amc <= g["amp_hi"]) & \
            (dmc >= g["dfd_lo"]) & (dmc <= g["dfd_hi"])
    res_mc = smc > drb
    print(f"  [F6] gate joint coverage (MC n={NMC}) = {in_mc.mean():.3f} "
          f"(resolved only {in_mc[res_mc].mean():.3f})", flush=True)

    in_geo = (smc >= g["sep_lo"]) & (smc <= g["sep_hi"]) & \
             (amc >= g["amp_lo"]) & (amc <= g["amp_hi"])     # 속도가정 없는 기하 부분만
    out["gate_coverage"] = dict(
        kind="MEASURED", n_mc=NMC,
        coverage_sep_amp_mc=float(in_geo.mean()),
        coverage_sep_amp_among_resolved_mc=float(in_geo[res_mc].mean()) if res_mc.any() else None,
        coverage_sep_amp_dfd_mc=float(in_mc.mean()),
        coverage_among_resolved_mc=float(in_mc[res_mc].mean()) if res_mc.any() else None,
        n_sample=int(len(sep)),
        coverage_sep_and_amp=float(inside.mean()),
        coverage_among_resolved=float(inside[res].mean()) if res.any() else None,
        cost_false_reject=gh["E_mitigation"]["cost"]["p_gate_sep_dfd_amp"],
        cost_false_reject_given_resolvable=gh["E_mitigation"]["cost"]["p_gate_sep_dfd_amp_given_resolvable"],
        note="'유령의 99%%를 덮는다' 는 각 축의 주변부 분위수(0.5~99.5%%)를 **결합** 커버리지로 잘못 "
             "옮긴 값이다. 실제 결합 포함률은 그보다 낮다. sep&amp 는 속도가정이 없는 기하량이고, "
             "dfd 축까지 더한 값은 표적 속도분포 가정(여기선 등방 N(0,2) m/s)에 의존한다.")

    # (d) 유령 진폭의 편파 의존 — 미공개 단일점 가정이었다 (MEASURED)
    from geometry import TX, RX, floor_ghost
    from scenarios import radial
    from geometry import CENTER, SPEED, SPAN
    pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)
    mid = len(pos) // 2
    pol = []
    for p in ("V", "H"):
        gg = floor_ghost(TX, RX, pos[mid], vel[mid], 3.5e9, pol=p)
        pol.append(dict(pol=p, gamma=gg["gamma"], theta_i_deg=gg["theta_i_deg"],
                        amp_db=float(20 * np.log10(gg["amp_ratio"]))))
    out["polarization"] = dict(
        kind="MEASURED", rows=pol,
        delta_db=pol[1]["amp_db"] - pol[0]["amp_db"],
        note="입사각이 콘크리트 브루스터각 바로 아래라 V(TM) 편파에서 바닥반사가 이례적으로 약하다. "
             "H(TE) 이면 유령이 훨씬 세진다 → 모든 유령 결론은 **편파 V 가정에 걸려 있다**.")

    # (e) dfd 는 평균이 아니라 최대를 봐야 한다
    dd = []
    for scen, v in gh["A_B_tracks"].items():
        for wfn, w in v.items():
            if not isinstance(w, dict) or "dfd_mean" not in w:
                continue
            dd.append(dict(scen=scen, wf=wfn, dfd_mean_hz=w.get("dfd_mean"),
                           dfd_absmax_hz=w.get("dfd_absmax"),
                           dfd_res_hz=w.get("d_fd_hz"),
                           frac_doppler_resolved=w.get("frac_doppler_resolved"),
                           frac_range_resolved=w.get("frac_range_resolved"),
                           d_rb_m=w.get("d_rb_m")))
    out["dfd"] = dict(kind="DERIVED", rows=dd,
                      note="'df_d 차 <= 7 Hz' 는 평균이다. 절대 최대는 그보다 크다(결론은 유지).")
    return out


# =========================================================================== #
def main():
    t0 = time.time()
    res = {"_meta": dict(
        purpose="적대적 검증에서 드러난 오류의 정정값 — 측정 또는 원자료 재유도. 손으로 적은 값 없음.",
        kinds=dict(MEASURED="새로 측정(대조군 포함)",
                   DERIVED="원본 JSON 의 원자료에서 정확히 재계산",
                   RETRACTED="측정으로 뒷받침되지 않아 철회 — 대체값 없음"))}
    for name, fn in (("F2_eca", f2_eca), ("F4_linkbudget", f4_linkbudget),
                     ("F6_ghost", f6_ghost), ("F1_cfar", f1_cfar),
                     ("F3_ambiguity", f3_ambiguity), ("F5_observability", f5_observability)):
        print(f"\n{'='*70}\n▶ {name}\n{'='*70}", flush=True)
        res[name] = fn()
    res["_meta"]["runtime_s"] = time.time() - t0
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
