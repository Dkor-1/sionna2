# -*- coding: utf-8 -*-
"""
build_ch1_elevation_figs.py — 8/18 팀미팅 **Chapter 1 «앙각»** 그림 다섯 장.

계획서는 `docs/PLAN_0818_CH1_ELEVATION.md`, 판정은 `docs/CH1_ELEVATION_FINDINGS.md` 다.

읽는 것 (계산 없음 — 원장만 읽는다, GPU 안 씀)
    outputs/elevation_sweep_md.json   팔 3 × 앙각 7 의 박자·대역·경로수
    outputs/elevation_sweep_md.npz    시계열 (부호 정정본, 표식 phase_sign_v2 = 1)
    outputs/verify_nadir_flash.json   앙각별 분해(누설 감사 포함)
쓰는 것
    outputs/ch1_elevation_figdata.json   ⭐이 그림들이 쓰는 파생량의 **정의와 값**
    outputs/figures/ch1_f1_maps.png      맵 격자 (엔진 3 × 앙각 4)
    outputs/figures/ch1_f2_spectra.png   앙각별 도플러 스펙트럼
    outputs/figures/ch1_f3_prediction.png  예측 대 실측
    outputs/figures/ch1_f4_bandenergy.png  ⭐프로펠러 대역 에너지 대 앙각 (헤드라인)
    outputs/figures/ch1_f5_raybudget.png   광선 예산 대 박자

⭐ 잣대를 왜 이렇게 골랐나
  · **대역 에너지는 «전체 전력 중 몫»(dB)** 으로 낸다. 우리 팔과 PathSolver 팔은 정규화가
    달라 절대 레벨이 70 dB 벌어져 있어 나란히 못 놓는다. 몫은 눈금에 무관해서 놓을 수 있다.
    정의는 `verify_nadir_flash.py::decompose` 의 `share_of_total_power_db` 와 **같다**
    (9 칸에서 소수 둘째 자리까지 일치하는 것을 확인했다).
  · **얼린 격자 팔의 절대 레벨은 안 쓴다**(상설 규칙 I1, 판 흩어짐 3.45 dB).
  · **맵은 패널마다 자기 최대값으로 정규화**한다 — 레벨 비교가 애초에 일어나지 않게.
  · 대역이 비었는지 아닌지는 **같은 폭의 대역외 기준띠(2.6~3.4 kHz)** 와 견줘 판정한다.
    블레이드가 있을 수 없는 자리라, 그 값과 같으면 «신호» 가 아니라 **바닥**이다.

    PYTHONPATH=src:benchmark python benchmark/build_ch1_elevation_figs.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import auto_periods, flash_spec, draw                   # noqa: E402

FIG = os.path.join(ROOT, "outputs", "figures")
os.makedirs(FIG, exist_ok=True)

J = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
V = json.load(open(f"{ROOT}/outputs/verify_nadir_flash.json"))
M = J["_meta"]

assert int(np.asarray(Z["phase_sign_v2"]).ravel()[0]) == 1, "⛔ 부호 정정본이 아니다"

PRF = float(M["prf_hz"])
FFL = float(M["f_flash_hz"])
ELS = [float(x) for x in M["elevations_deg"]]
#: ⭐2026-08-14 — 같은 코드로 **여러 거리 판**을 굽는다. 10 m 옛 판은 기본값 그대로 나오고,
#  15 m 재설계판은 아래 세 환경변수로 팔·자세수·출력이름만 갈아끼워 굽는다.
#      CH1_ARMS = "키|표시이름|색 ; 키|표시이름|색 ; ..."  (없으면 옛 10 m 세 팔)
#                 ⚠구분자는 **세미콜론**이다 — 표시이름에 쉼표가 들어간다.
#      CH1_TAG  = "_r15"                                   출력 파일 뒤에 붙는 꼬리
#      CH1_N    = 8192                                     한 앙각의 자세 수
#  ⚠원장·npz 는 하나를 공유한다 — 팔 이름만으로 판이 갈린다.
TAG = os.environ.get("CH1_TAG", "")
N = int(os.environ.get("CH1_N", "4096"))
ROW = {(r["engine"], r["el_deg"]): r for r in J["rows"]}
FTIP0 = float(ROW[(os.environ.get("CH1_ARMS", "ours|x|x").split(";")[0]
                   .split("|")[0].strip(), 0.0)]["f_tip_hz"])            # el 0 의 f_tip = 1272.9 Hz
FIX_HI = float(json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))
               ["_meta"]["f_tip_hz"])                    # 덱 대역 상단 = −15° 의 f_tip
FIX_LO = 0.35 * FIX_HI
PERIODS = auto_periods(PRF, FFL)

# ── 팔 이름 (그림 글자는 영어 — 하우스 규약) ───────────────────────────────
_DEFAULT_ARMS = [
    ("ours",              "Ours (SBR + PO)",              "#c62828", "-",  2.2),
    ("sionna",            "PathSolver, 11.1 M rays",      "#8e9aab", "-",  1.3),
    ("sionna_p250000000", "PathSolver, 250 M rays",       "#1565c0", "-",  1.7),
]
if os.environ.get("CH1_ARMS"):
    _w = [1.3, 1.7, 2.2]
    ARMS = []
    for i, spec in enumerate(os.environ["CH1_ARMS"].split(";")):
        k, lab, col = [x.strip() for x in spec.split("|")]
        ARMS.append((k, lab, col, "-", _w[i % 3]))
else:
    ARMS = _DEFAULT_ARMS
ARM_KEYS = [a[0] for a in ARMS]
ARM_NAME = {a[0]: a[1] for a in ARMS}
ARM_COL = {a[0]: a[2] for a in ARMS}
A0, A1, A2 = ARM_KEYS[0], ARM_KEYS[1], ARM_KEYS[2]   # 0=우리 커널, 1·2=PathSolver 두 판

# 대역외 기준띠 — 블레이드가 원리적으로 못 오는 자리(같은 폭으로 옮겨 놓는다)
OOB_LO = 2600.0

FR = np.fft.fftshift(np.fft.fftfreq(N, 1.0 / PRF))
WIN = np.hanning(N)


# ══ 파생량 ══════════════════════════════════════════════════════════════════
def spectrum(key):
    """전 구간 한나 창 FFT 전력 — verify_nadir_flash.decompose 와 같은 규약."""
    E = np.asarray(Z[key], complex)
    return E, np.abs(np.fft.fftshift(np.fft.fft(E * WIN))) ** 2


def share_db(P, lo, hi):
    """대역 전력이 **전체 전력에서 차지하는 몫** [dB] — 눈금에 무관하다."""
    b = (np.abs(FR) >= lo) & (np.abs(FR) <= hi)
    if b.sum() < 2:
        return None
    return float(10 * np.log10(P[b].sum() / P.sum()))


def comb_lines(P, kmax=30, hw=12.0, gap=(30.0, 70.0)):
    """빗살 차수마다 «바닥 위 몇 dB» 인가. 바닥은 그 선 양옆의 중앙값이다."""
    af = np.abs(FR)
    snr = np.full(kmax + 1, np.nan)
    for k in range(1, kmax + 1):
        f0 = k * FFL
        m = np.abs(af - f0) <= hw
        s = (np.abs(af - f0) > gap[0]) & (np.abs(af - f0) <= gap[1])
        if m.sum() < 1 or s.sum() < 8:
            continue
        snr[k] = 10 * np.log10(P[m].sum() / (float(np.median(P[s])) * int(m.sum())))
    return snr


def ac_over_dc_db(E):
    """⚠**엔진 사이 비교에 쓰지 마라.** 2026-08-14 적대 검증이 무너뜨린 잣대다.

    분자가 «정지 성분 × 변조 성분» 의 교차항이라 정지 성분이 크면 같이 부푼다.
    남겨 두는 이유는 옛 판(10 m)의 값을 재현할 수 있게 하기 위해서일 뿐이다.
    판정에는 아래 `verified_visibility` 의 두 잣대를 쓴다.
    """
    d = E / E.mean() - 1.0
    return float(10 * np.log10(np.mean(np.abs(d) ** 2)))


# ⭐살아남은 잣대 — 정의는 benchmark/comb_snr.py 하나뿐이다(그대로 가져다 쓴다).
from comb_snr import comb_snr as _comb, band_g as _bandg, mod_snr as _mod   # noqa: E402


def verified_visibility(E, el, n_null=60, seed=20260814):
    """«날개 줄무늬가 실제로 보이는가» — 치환 널 위면 보인다.

    ① comb  느린시간 FFT 에서 블레이드 대역 안 f_flash 조화선 대 바닥 [dB]
    ② mod   블레이드 대역 전력이 f_flash 로 뛰는가 [dB]
    두 잣대 다 «시간축을 뒤섞어 주기성을 없앤 판» 을 같은 관을 통과시킨 값의
    **최댓값**을 문턱으로 쓴다. 눈금·정규화에 무관해 엔진 사이에서도 성립한다.
    """
    rng = np.random.default_rng(seed)
    out = {}
    c = _comb(E, PRF, el)
    g, fsg = _bandg(E, PRF, el)
    m = _mod(g, fsg) if g is not None else None
    cn, mn = [], []
    for _ in range(n_null):
        pm = rng.permutation(E.size)
        v = _comb(E[pm], PRF, el)
        if v is not None:
            cn.append(v)
        if g is not None:
            v2 = _mod(rng.permutation(g), fsg)
            if v2 is not None:
                mn.append(v2)
    if c is not None and cn:
        out.update(comb_snr_v2_db=round(c, 2), comb_null_max_db=round(max(cn), 2),
                   comb_visible=bool(c > max(cn)))
    if m is not None and mn:
        out.update(mod_snr_db=round(m, 2), mod_null_max_db=round(max(mn), 2),
                   mod_visible=bool(m > max(mn)))
    return out


DER = {"_meta": {
    "generator": "benchmark/build_ch1_elevation_figs.py",
    "purpose_ko": "8/18 Chapter 1 그림이 쓰는 파생량 — 정의를 코드로 못 박고 값을 남긴다",
    "inputs": ["outputs/elevation_sweep_md.json", "outputs/elevation_sweep_md.npz",
               "outputs/verify_nadir_flash.json"],
    "gpu_ko": "GPU 를 쓰지 않았다. 원장만 읽고 CPU 로 FFT 했다.",
    "spectrum_ko": f"{N} 점 한나 창 FFT, Δf = {PRF/N:.2f} Hz "
                   "(verify_nadir_flash.decompose 와 같은 규약)",
    "share_ko": "대역 전력 / 전체 전력 [dB] — 눈금 무관. verify 의 "
                "share_of_total_power_db 와 같은 정의",
    "band_track_ko": "0.35~1.0 × f_tip(el) — 앙각마다 다시 잡는다",
    "band_fixed_ko": f"{FIX_LO:.1f}~{FIX_HI:.1f} Hz 고정 (덱의 −15° 대역)",
    "oob_ko": f"대역외 기준띠 — 같은 폭을 {OOB_LO:.0f} Hz 위로 옮긴 것. "
              "블레이드가 원리적으로 못 오는 자리라 «바닥» 을 읽는다",
    "comb_ko": "빗살 선 SNR = k·f_flash ±12 Hz 전력 / 그 옆 30~70 Hz 중앙값",
    "verified_ko": "⭐판정용 잣대 둘 — comb_snr_v2_db(느린시간 FFT 조화선 대 바닥) 과 "
                   "mod_snr_db(대역 전력이 f_flash 로 뛰는 깊이). 문턱은 시간축을 "
                   "뒤섞은 치환 널 60 회의 최댓값이고, 그 위면 *_visible = true. "
                   "정의는 benchmark/comb_snr.py 하나뿐이다",
    "acdc_warning_ko": "⛔ac_over_dc_db 는 엔진 사이 비교에 쓰지 않는다 — 분자가 "
                       "정지 성분과의 교차항이라 2026-08-14 검증에서 무너졌다",
    "leakage_note_ko": "⚠ verify_nadir_flash 가 잡은 누설은 70 표본 STFT 대역전력의 "
                       "이야기다. 여기 share 는 4096 점 전 구간 FFT 라 DC 누설이 "
                       "−100 dB 아래다. 대신 **광대역 바닥**이 한계이고 그것을 "
                       "대역외 기준띠로 드러낸다",
}, "cells": {}}

for eng in ARM_KEYS:
    for el in ELS:
        key = f"{eng}/el{el:+.0f}"
        E, P = spectrum(key)
        r = ROW[(eng, el)]
        ft = float(r["f_tip_hz"])
        wt = 0.65 * ft                              # 추적대역 폭
        wf = FIX_HI - FIX_LO
        dc = float(10 * np.log10(P[np.argmin(np.abs(FR))] / P.sum()))
        st = share_db(P, 0.35 * ft, max(ft, 1e-6))
        sf = share_db(P, FIX_LO, FIX_HI)
        DER["cells"][key] = dict(
            engine=eng, el_deg=el, f_tip_hz=ft,
            share_track_db=st,
            share_track_oob_db=share_db(P, OOB_LO, OOB_LO + max(wt, 1e-6)),
            share_fixed_db=sf,
            share_fixed_oob_db=share_db(P, OOB_LO, OOB_LO + wf),
            # ⚠ 같은 양을 **동체선(반송파) 기준**으로도 낸다. el−60 에서 동체선이
            #   거의 널이라 «전체 대비» 몫이 혼자 뛰기 때문이다.
            carrier_share_db=round(dc, 2),
            share_track_rel_carrier_db=None if st is None else round(st - dc, 2),
            share_fixed_rel_carrier_db=round(sf - dc, 2),
            ac_over_dc_db=round(ac_over_dc_db(E), 2),
            comb_snr_db=[None if not np.isfinite(x) else round(float(x), 1)
                         for x in comb_lines(P)[1:]],
            beat_track_hz=r["track"]["beat_hz"], beat_fixed_hz=r["fixed"]["beat_hz"],
            npaths_median=r["npaths_median"],
            ledger_level_db=r["level_db"],
        )
        DER["cells"][key].update(verified_visibility(E, el))

# 기하 예측 — 고정대역 중 «그 앙각의 블레이드 대역» 이 덮는 몫
DER["prediction"] = {"fixed_band_overlap_frac": {}, "f_tip_hz": {}}
for el in ELS:
    ft = FTIP0 * np.cos(np.radians(el))
    lo, hi = max(FIX_LO, 0.35 * ft), min(FIX_HI, ft)
    DER["prediction"]["f_tip_hz"][f"{el:+.0f}"] = round(float(ft), 1)
    DER["prediction"]["fixed_band_overlap_frac"][f"{el:+.0f}"] = \
        round(float(max(0.0, hi - lo) / (FIX_HI - FIX_LO)), 4)


# ══ 그림 공통 ═══════════════════════════════════════════════════════════════
plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
    "legend.fontsize": 10, "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "axes.axisbelow": True,
})


def save(fig, name):
    name = name.replace(".png", f"{TAG}.png")
    p = os.path.join(FIG, name)
    fig.savefig(p, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {p}")
    return p


# ══ F1 — 맵 격자 ════════════════════════════════════════════════════════════
def fig1():
    els = [0.0, -30.0, -60.0, -90.0]
    n0 = int(round(0.020 * PRF))
    nz = int(round(0.060 * PRF))                      # 60 ms 확대 — 플래시가 보이게
    fig, ax = plt.subplots(3, 4, figsize=(15.0, 9.2), sharex=True, sharey=True)
    for i, (eng, nm, *_rest) in enumerate(ARMS):
        for j, el in enumerate(els):
            a = ax[i, j]
            E = np.asarray(Z[f"{eng}/el{el:+.0f}"], complex)[n0:n0 + nz]
            f, t, S, _ = flash_spec(E, PRF, FFL, PERIODS)
            ft = float(ROW[(eng, el)]["f_tip_hz"])
            m = draw(a, t, f, S, ft)                  # 패널마다 자기 최대값 기준
            a.set_ylim(-2000, 2000)
            if i == 0:
                a.set_title(f"elevation {el:+.0f}°"
                            + ("   (nadir)" if el == -90 else ""), pad=6)
            if j == 0:
                a.set_ylabel(f"{nm}\nDoppler [Hz]")
            if i == 2:
                a.set_xlabel("time [ms]")
            a.text(0.03, 0.94, r"$f_{\rm tip}$ = " + f"{ft:.0f} Hz", transform=a.transAxes,
                   color="w", fontsize=9.5, va="top",
                   bbox=dict(fc="k", alpha=0.45, ec="none", pad=1.8))
    fig.suptitle("CH1-F1   Micro-Doppler maps versus elevation "
                 "(each panel normalised to its own maximum)", y=0.985, fontsize=14)
    cb = fig.colorbar(ax[0, 0].collections[0], ax=ax, fraction=0.018, pad=0.012)
    cb.set_label("power below panel maximum [dB]")
    return save(fig, "ch1_f1_maps.png")


# ══ F2 — 앙각별 도플러 스펙트럼 ═════════════════════════════════════════════
def fig2():
    fig, axs = plt.subplots(2, 4, figsize=(16.0, 7.4), sharex=True, sharey=True)
    show = [A0, A2]
    for k, el in enumerate(ELS):
        a = axs.ravel()[k]
        for eng in show:
            E, P = spectrum(f"{eng}/el{el:+.0f}")
            dc = P[np.argmin(np.abs(FR))]
            a.plot(FR, 10 * np.log10(P / dc), lw=0.7, color=ARM_COL[eng],
                   alpha=0.9 if eng == A0 else 0.75)
        ft = float(ROW[(A0, el)]["f_tip_hz"])
        for s in (+1, -1):
            a.axvline(s * ft, color="k", ls="--", lw=1.1)
        a.set_title(f"elevation {el:+.0f}°" + ("   (nadir)" if el == -90 else ""), pad=5)
        a.text(0.5, 0.03, r"$f_{\rm tip}$ = " + f"{ft:.0f} Hz", transform=a.transAxes,
               ha="center", fontsize=9.5,
               bbox=dict(fc="w", alpha=0.75, ec="0.7", pad=1.6))
    axs.ravel()[-1].axis("off")
    axs.ravel()[-1].legend(handles=[
        Line2D([], [], color=ARM_COL[e], lw=2, label=ARM_NAME[e]) for e in show
    ] + [Line2D([], [], color="k", ls="--", lw=1.2,
                label=r"predicted $\pm f_{\rm tip}=f_{\rm tip,0}\cos(\rm el)$")],
        loc="center", frameon=False, fontsize=11)
    for a in axs[1, :]:
        a.set_xlabel("Doppler [Hz]")
    for a in axs[:, 0]:
        a.set_ylabel("power relative to body line [dB]")
    axs[0, 0].set_xlim(-2200, 2200)
    axs[0, 0].set_ylim(-95, 8)
    fig.suptitle("CH1-F2   Slow-time Doppler spectrum at each elevation", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    return save(fig, "ch1_f2_spectra.png")


# ══ F3 — 예측 대 실측 ═══════════════════════════════════════════════════════
def _elmap(a, eng, smooth=9):
    """앙각 × 도플러 지도 — 색은 동체선 대비 dB."""
    rows = []
    for el in ELS:
        _E, P = spectrum(f"{eng}/el{el:+.0f}")
        dc = P[np.argmin(np.abs(FR))]
        z = 10 * np.log10(np.convolve(P, np.ones(smooth) / smooth, mode="same") / dc)
        rows.append(z)
    Zm = np.array(rows)
    yy = np.array(ELS)
    ye = np.concatenate([[yy[0] + 7.5], (yy[:-1] + yy[1:]) / 2, [yy[-1] - 7.5]])
    df = float(FR[1] - FR[0])
    fe = np.concatenate([FR - df / 2, [FR[-1] + df / 2]])
    m = a.pcolormesh(fe, ye, Zm, cmap="magma", vmin=-70, vmax=-5,
                     shading="flat", rasterized=True)
    e = np.linspace(0, -90, 400)
    for s in (+1, -1):
        a.plot(s * FTIP0 * np.cos(np.radians(e)), e, color="#39ff14", lw=2.0)
    a.set_xlim(-2000, 2000)
    a.set_ylim(-97.5, 7.5)
    a.set_yticks(ELS)
    a.set_xlabel("Doppler [Hz]")
    return m


def fig3():
    fig, ax = plt.subplots(2, 2, figsize=(14.6, 9.8))
    fig.subplots_adjust(left=0.065, right=0.90, top=0.905, bottom=0.075,
                        hspace=0.42, wspace=0.22)
    m = _elmap(ax[0, 0], A0)
    ax[0, 0].set_title("(a)  Ours (SBR + PO):  the bright blade band narrows with "
                       r"$\cos(\rm el)$ and is gone at nadir", pad=6, fontsize=11.5)
    ax[0, 0].set_ylabel("elevation [deg]")
    _elmap(ax[0, 1], A2)
    ax[0, 1].set_title("(b)  PathSolver, 250 M rays:  the comb keeps its full width, "
                       "nadir included", pad=6, fontsize=11.5)
    b0 = ax[0, 1].get_position()
    cax = fig.add_axes((b0.x1 + 0.014, b0.y0, 0.014, b0.height))
    cb = fig.colorbar(m, cax=cax)
    cb.set_label("power relative to body line [dB]")

    # (c) 빗살 굴러떨어짐 — x 를 f_tip 으로 나눈다
    a = ax[1, 0]
    cmap = plt.get_cmap("viridis")
    for i, el in enumerate(ELS[:-1]):                 # −90 은 f_tip = 0 이라 못 나눈다
        ft = float(ROW[(A0, el)]["f_tip_hz"])
        c = cmap(i / 5.0)
        for eng, ls, lw, al in ((A0, "-", 2.0, 0.95),
                                (A2, ":", 1.4, 0.75)):
            s = np.array(DER["cells"][f"{eng}/el{el:+.0f}"]["comb_snr_db"], float)
            k = np.arange(1, s.size + 1) * FFL / ft
            g = k <= 3.0
            a.plot(k[g], s[g], ls, color=c, lw=lw, alpha=al)
    a.axvline(1.0, color="k", lw=1.4)
    a.set_xlabel(r"harmonic frequency  /  $f_{\rm tip}(\rm el)$")
    a.set_ylabel("blade comb line, above local floor [dB]")
    a.set_title("(c)  Beyond the kinematic limit ours drops away, "
                "PathSolver holds its comb", pad=6, fontsize=11.5)
    a.set_xlim(0, 3)
    a.set_ylim(-4, 70)
    a.legend(handles=[Line2D([], [], color="k", lw=2.0, label="Ours (SBR + PO)"),
                      Line2D([], [], color="k", ls=":", lw=1.6,
                             label="PathSolver, 250 M rays"),
                      Line2D([], [], color="k", lw=1.4,
                             label=r"kinematic limit $f=f_{\rm tip}$")]
             + [Line2D([], [], color=cmap(i / 5.0), lw=6,
                       label=f"{ELS[i]:+.0f}°") for i in range(6)],
             ncol=2, fontsize=9, frameon=True, loc="upper right")

    # (d) f_flash 는 앙각과 무관한가
    a = ax[1, 1]
    a.axhspan(FFL - 2, FFL + 2, color="#2e7d32", alpha=0.16)
    a.axhline(FFL, color="#2e7d32", lw=1.6)
    # ⭐세 팔의 값이 겹치므로 표식을 달리해 뒤에 것이 가려지지 않게 한다
    style = {A0: dict(marker="o", ms=11, mfc="#c62828", lw=2.4, zorder=5),
             A1: dict(marker="^", ms=11, mfc="none", mew=1.8, lw=1.4, zorder=3),
             A2: dict(marker="s", ms=8, mfc="none", mew=1.8,
                                       lw=1.4, zorder=4)}
    for eng, nm, col, _ls, _lw in ARMS:
        x, y = [], []
        for el in ELS:
            b = DER["cells"][f"{eng}/el{el:+.0f}"]["beat_track_hz"]
            if b is not None:
                x.append(el); y.append(b)
        a.plot(x, y, color=col, mec=col, label=nm, **style[eng])
    a.axvspan(-97.5, -82.5, color="0.85", alpha=0.8)
    a.text(-90, 300, "not measurable\n" + r"($f_{\rm tip}=0$)", ha="center",
           fontsize=9.5, color="0.25")
    a.text(-16, FFL + 14, r"predicted $f_{\rm flash}$ = "
           + f"{FFL:.2f} Hz  " + r"$\pm$2 Hz", color="#1b5e20", fontsize=10)
    a.set_xlim(7.5, -97.5)
    a.set_ylim(0, 420)
    a.set_xticks(ELS)
    a.set_xlabel("elevation [deg]")
    a.set_ylabel("measured blade beat, tracking band [Hz]")
    a.set_title("(d)  Flash rate does not move with elevation", pad=6, fontsize=11.5)
    a.legend(loc="center left", fontsize=9.5)
    fig.suptitle("CH1-F3   Prediction versus measurement", fontsize=14, y=0.975)
    return save(fig, "ch1_f3_prediction.png")


# ══ F4 — ⭐프로펠러 대역 에너지 대 앙각 (헤드라인) ══════════════════════════
def _sub4(band):
    """부제는 **원장에서 세어** 만든다 — 팔이 바뀌면 문장도 같이 바뀐다.

    «바닥에 붙었다» = 대역 몫이 같은 폭의 대역외 기준띠보다 3 dB 안으로 들어왔다.
    ⚠부제는 **한 줄로 짧게** 둔다(하우스 규약: 겹침 금지). 자세한 것은 본문이 적는다.
    """
    short = {ARM_KEYS[0]: "ours", ARM_KEYS[1]: "physics off", ARM_KEYS[2]: "physics on"}
    said = []
    for eng in ARM_KEYS:
        floored = []
        tot = 0
        for el in ELS:
            c = DER["cells"][f"{eng}/el{el:+.0f}"]
            v, o = c[f"share_{band}_db"], c[f"share_{band}_oob_db"]
            if v is None or o is None:
                continue
            tot += 1
            if v - o < 3.0:
                floored.append(el)
        if tot and len(floored) == tot:
            said.append(f"{short[eng]} at the floor everywhere")
        elif len(floored) >= 2:
            # 낮은 쪽 꼬리로 **붙어 있으면** «−60° 아래», 흩어져 있으면 «6 중 5» 로 적는다
            usable = [e for e in ELS
                      if DER["cells"][f"{eng}/el{e:+.0f}"][f"share_{band}_db"] is not None]
            tail = usable[-len(floored):]
            if sorted(tail) == sorted(floored):
                said.append(f"{short[eng]} at the floor below {max(floored) + 15:+.0f}"
                            + chr(176))
            else:
                said.append(f"{short[eng]} at the floor at {len(floored)} of {tot}")
    return ("\n" + ", ".join(said)) if said else ""


def fig4():
    fig, ax = plt.subplots(1, 2, figsize=(15.4, 6.4), sharey=True)
    for a, band, ttl, fs in (
            (ax[0], "track", "(a)  Tracking band  "
                             r"$0.35\,f_{\rm tip}(\rm el)\ldots f_{\rm tip}(\rm el)$"
                             + (_sub4("track") if TAG else
                                "\nno elevation trend down to " + r"$-75\degree$"),
             11.0),
            (ax[1], "fixed", "(b)  Fixed deck band  "
                             f"{FIX_LO:.0f}–{FIX_HI:.0f} Hz"
                             + (_sub4("fixed") if TAG else
                                "\nempties below " + r"$-60\degree$ for ours only"),
             11.0)):
        for eng, nm, col, ls, lw in ARMS:
            x, y, xo, yo = [], [], [], []
            for el in ELS:
                c = DER["cells"][f"{eng}/el{el:+.0f}"]
                v = c[f"share_{band}_db"]
                o = c[f"share_{band}_oob_db"]
                if v is None:
                    continue
                x.append(el); y.append(v); xo.append(el); yo.append(o)
            a.plot(x, y, "o-", color=col, lw=lw + 0.4, ms=7, label=nm, zorder=3)
            a.plot(xo, yo, ls=(0, (1, 2)), color=col, lw=1.2, alpha=0.75, zorder=2)
        if band == "fixed":
            # 기하 예측 — 겹침 몫만큼 준다(에너지가 대역 안에서 고르다는 가정)
            base = DER["cells"][f"{A0}/el-15"]["share_fixed_db"]
            xs, ys = [], []
            for el in ELS:
                fr_ = DER["prediction"]["fixed_band_overlap_frac"][f"{el:+.0f}"]
                if fr_ > 0:
                    xs.append(el); ys.append(base + 10 * np.log10(fr_))
            a.plot(xs, ys, "k--", lw=1.8, zorder=4,
                   label="geometric overlap prediction")
            a.axvspan(-97.5, -67.5, color="0.85", alpha=0.7, zorder=0)
            a.text(-82, -6, "band lies entirely\n"
                   r"above $f_{\rm tip}$", ha="center", fontsize=10, color="0.25")
        else:
            a.axvspan(-97.5, -82.5, color="0.85", alpha=0.8, zorder=0)
            a.text(-90, -30, "not measurable\n" + r"($f_{\rm tip}=0$,"
                   "\nzero-width band)", ha="center", fontsize=9.5, color="0.25")
        a.set_xlim(7.5, -97.5)
        a.set_xticks(ELS)
        a.set_xlabel("elevation [deg]")
        a.set_title(ttl, pad=8, fontsize=fs)
    ax[0].set_ylabel("propeller-band energy, share of total power [dB]")
    ax[0].set_ylim(-60, 3)
    ax[1].legend(loc="lower left", fontsize=9.5)
    ax[0].legend(handles=[Line2D([], [], color="0.35", ls=(0, (1, 2)), lw=1.4,
                                 label="same-width out-of-band reference "
                                       "(2.6–3.4 kHz):\na marker sitting on its own "
                                       "dotted line is at the floor")],
                 loc="lower center", fontsize=9.5)
    fig.suptitle("CH1-F4   Propeller-band energy versus elevation",
                 fontsize=14, y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    return save(fig, "ch1_f4_bandenergy.png")


# ══ F5 — 광선 예산 대 박자 ══════════════════════════════════════════════════
def fig5():
    fig, ax = plt.subplots(1, 3, figsize=(16.2, 5.4))
    # (a) 박자 오차
    a = ax[0]
    for eng, nm, col, _ls, _lw in ARMS:
        x, y = [], []
        for el in ELS:
            b = DER["cells"][f"{eng}/el{el:+.0f}"]["beat_track_hz"]
            if b is not None:
                x.append(el); y.append(max(abs(b - FFL), 0.02))
        a.semilogy(x, y, "o-", color=col, lw=1.8, ms=7, label=nm)
    a.axhline(2.0, color="#2e7d32", lw=1.5)
    a.text(-2, 2.6, "pass: within 2 Hz", color="#1b5e20", fontsize=10)
    a.set_xlim(7.5, -82.5)
    a.set_xticks(ELS[:-1])
    a.set_ylim(0.015, 3000)
    a.set_xlabel("elevation [deg]")
    a.set_ylabel(r"$|$beat $-\ f_{\rm flash}|$ [Hz]")
    a.set_title("(a)  Beat error, tracking band", pad=6)
    a.legend(fontsize=9, loc="upper right")

    # (b) 경로 수 — 예산이 앙각을 안 본다는 교란
    a = ax[1]
    for eng in ARM_KEYS[1:]:
        x = [el for el in ELS if DER["cells"][f"{eng}/el{el:+.0f}"]["npaths_median"]]
        y = [DER["cells"][f"{eng}/el{el:+.0f}"]["npaths_median"] for el in x]
        a.semilogy(x, y, "s-", color=ARM_COL[eng], lw=1.8, ms=7, label=ARM_NAME[eng])
    a.set_xlim(7.5, -97.5)
    a.set_xticks(ELS)
    a.set_xlabel("elevation [deg]")
    a.set_ylabel("median paths per pose")
    a.set_title("(b)  Paths found per pose" if TAG else
                "(b)  The budget rule looks at range only, so the path count "
                "drifts with elevation", pad=6, fontsize=11.5)
    a.legend(fontsize=9.5, loc="center left")

    # (c) 날개 줄무늬가 실제로 보이는가
    a = ax[2]
    if TAG:
        #: ⭐새 판은 **검증을 통과한 잣대**를 쓴다. AC/DC 는 엔진 사이에서 못 쓴다.
        for eng, nm, col, _ls, _lw in ARMS:
            xs, ys, vis = [], [], []
            for el in ELS:
                c = DER["cells"][f"{eng}/el{el:+.0f}"]
                if c.get("comb_snr_v2_db") is None:
                    continue
                xs.append(el); ys.append(c["comb_snr_v2_db"])
                vis.append(bool(c.get("comb_visible")))
            if not xs:
                continue
            a.plot(xs, ys, "-", color=col, lw=1.8, label=nm, zorder=3)
            xs = np.asarray(xs, float); ys = np.asarray(ys, float)
            vis = np.asarray(vis, bool)
            a.plot(xs[vis], ys[vis], "o", color=col, ms=8, zorder=4)
            a.plot(xs[~vis], ys[~vis], "o", mfc="white", mec=col, mew=1.8, ms=8, zorder=4)
        nulls = [DER["cells"][f"{e}/el{el:+.0f}"].get("comb_null_max_db")
                 for e in ARM_KEYS for el in ELS]
        nulls = [v for v in nulls if v is not None]
        if nulls:
            a.axhline(max(nulls), color="#2e7d32", lw=1.4, ls="--", zorder=2,
                      label="chance level (shuffled time)")
        a.set_xlim(7.5, -97.5)
        a.set_xticks(ELS)
        a.set_xlabel("elevation [deg]")
        a.set_ylabel("blade-line strength above noise [dB]")
        a.set_title("(c)  Blade lines versus chance", pad=6, fontsize=11.5)
        a.text(0.97, 0.03, "filled = above chance\nhollow = at chance",
               transform=a.transAxes, ha="right", va="bottom", fontsize=9, color="0.25",
               bbox=dict(fc="white", ec="0.8", alpha=0.9, pad=2.5))
        a.legend(fontsize=9, loc="upper left")
    else:
        for eng, nm, col, _ls, _lw in ARMS:
            y = [DER["cells"][f"{eng}/el{el:+.0f}"]["ac_over_dc_db"] for el in ELS]
            a.plot(ELS, y, "o-", color=col, lw=1.8, ms=7, label=nm)
        y0 = DER["cells"][f"{A1}/el+0"]["ac_over_dc_db"]
        a.annotate("the body specular dominates\nand almost nothing moves",
                   xy=(0.4, y0), xytext=(-24, -72), fontsize=9.5, color="0.2",
                   arrowprops=dict(arrowstyle="->", color="0.35", lw=1.2))
        a.set_xlim(7.5, -97.5)
        a.set_ylim(-95, 22)
        a.set_xticks(ELS)
        a.set_xlabel("elevation [deg]")
        a.set_ylabel("modulated power / carrier power [dB]")
        a.set_title("(c)  How much of the return actually moves", pad=6)
        a.legend(fontsize=9, loc="lower right")
    fig.suptitle("CH1-F5   Flash rate, path count, and blade-line visibility"
                 if TAG else "CH1-F5   Ray budget versus flash-rate accuracy",
                 fontsize=14, y=1.005)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save(fig, "ch1_f5_raybudget.png")


# ══ 판정 ════════════════════════════════════════════════════════════════════
def judge():
    g = {}
    # G1 — f_flash 가 앙각에 안 변한다 (추적대역, f_tip > 0 인 6 점)
    for eng in ARM_KEYS:
        b = [DER["cells"][f"{eng}/el{el:+.0f}"]["beat_track_hz"] for el in ELS[:-1]]
        g[f"G1_{eng}_worst_dev_hz"] = round(max(abs(x - FFL) for x in b), 2)
        g[f"G1_{eng}_n_within_2hz"] = int(sum(abs(x - FFL) <= 2 for x in b))
    # G2 — 빗살이 f_tip 에서 굴러떨어지나 (f_tip 아래 평균 − 1.3 f_tip 위 평균)
    for eng in ARM_KEYS:
        d = []
        for el in ELS[:-1]:
            ft = float(ROW[(eng, el)]["f_tip_hz"])
            s = np.array(DER["cells"][f"{eng}/el{el:+.0f}"]["comb_snr_db"], float)
            k = np.arange(1, s.size + 1) * FFL / ft
            lo, hi = s[(k <= 1.0)], s[(k >= 1.3) & (k <= 3.0)]
            if lo.size and hi.size:
                d.append(float(np.nanmean(lo) - np.nanmean(hi)))
        g[f"G2_{eng}_rolloff_db_mean"] = round(float(np.mean(d)), 1)
        g[f"G2_{eng}_rolloff_db_min"] = round(float(np.min(d)), 1)
    # G3 — 고정대역이 기하 예측대로 주나
    base = DER["cells"][f"{A0}/el-15"]["share_fixed_db"]
    err = {}
    for el in ELS:
        fr_ = DER["prediction"]["fixed_band_overlap_frac"][f"{el:+.0f}"]
        if fr_ <= 0:
            continue
        err[f"{el:+.0f}"] = round(DER["cells"][f"{A0}/el{el:+.0f}"]["share_fixed_db"]
                                  - (base + 10 * np.log10(fr_)), 1)
    g[f"G3_{A0}_fixed_minus_prediction_db"] = err
    g["G3_worst_db"] = max(abs(v) for v in err.values())
    # G4 — −63.8° 아래에서 박자가 무너지나
    g[f"G4_{A0}_beat_track_at_-75"] = DER["cells"][f"{A0}/el-75"]["beat_track_hz"]
    g[f"G4_{A0}_beat_fixed_at_-90"] = DER["cells"][f"{A0}/el-90"]["beat_fixed_hz"]
    #: 나딧 누설 감사는 옛 10 m 판에만 있다(verify_nadir_flash 는 그 판의 산물).
    _lk = V.get("B_decomposition", {}).get(f"{A0}/el-90")
    if _lk:
        g["G4_leak_ratio_at_-90_db"] = _lk["fixed_band_true_over_leakage_db"]
    # G5 — 경로 수가 앙각에 어떻게 걸리나
    for eng in ARM_KEYS[1:]:
        v = [DER["cells"][f"{eng}/el{el:+.0f}"]["npaths_median"] for el in ELS]
        g[f"G5_{eng}_npaths_min_max"] = [min(v), max(v)]
    # G6 — 두 엔진이 같은 방향으로 무너지나
    g[f"G6_{A0}_track_share_span_db"] = round(
        max(DER["cells"][f"{A0}/el{el:+.0f}"]["share_track_db"] for el in ELS[:-1])
        - min(DER["cells"][f"{A0}/el{el:+.0f}"]["share_track_db"] for el in ELS[:-1]), 1)
    # G7 — ⭐«날개 줄무늬가 보이는 앙각이 몇 점인가» (치환 널 위인 칸을 센다)
    for eng in ARM_KEYS:
        for key in ("comb", "mod"):
            cs = [DER["cells"][f"{eng}/el{el:+.0f}"] for el in ELS]
            has = [c for c in cs if c.get(f"{key}_visible") is not None]
            g[f"G7_{eng}_{key}_visible_n"] = [sum(bool(c[f"{key}_visible"]) for c in has),
                                              len(has)]
    DER["gates"] = g
    return g


def add_role_aliases():
    """⭐셀 키에 **역할 이름** 별칭을 얹는다 — 리포트가 팔의 긴 이름을 안 외우게.

    별칭은 같은 dict 를 가리키는 **또 하나의 키**일 뿐이고 값은 하나다. 어느 팔이 어느
    역할인지는 `_meta.alias_ko` 가 파일 안에 적어 둔다(파일명에 판이 들어 있다).
        ours        자리 0 — 우리 커널
        sionna_off  자리 1 — PathSolver, 물리 스위치 끔
        sionna_on   자리 2 — PathSolver, 물리 스위치 켬
    """
    role = {A0: "ours", A1: "sionna_off", A2: "sionna_on"}
    for key in list(DER["cells"]):
        eng, _, tail = key.partition("/")
        if eng in role:
            DER["cells"][f"{role[eng]}/{tail}"] = DER["cells"][key]
    # 게이트 이름에도 같은 별칭을 얹는다 — `G6_<팔>_...` → `G6_<역할>_...`
    for key in list(DER.get("gates", {})):
        for eng, nm in role.items():
            if eng in key:
                DER["gates"][key.replace(eng, nm)] = DER["gates"][key]
                break
    DER["_meta"]["alias_ko"] = (
        "셀 키에 역할 별칭을 함께 실었다 — " +
        " · ".join(f"{v} = {k}" for k, v in role.items()) +
        ". 별칭과 본이름은 **같은 값**을 가리킨다")


if __name__ == "__main__":
    print("═══ CH1 앙각 그림 ═══")
    gs = judge()
    add_role_aliases()
    outs = [fig1(), fig2(), fig3(), fig4(), fig5()]
    DER["_meta"]["figures"] = [os.path.relpath(p, ROOT) for p in outs]
    p = f"{ROOT}/outputs/ch1_elevation_figdata{TAG}.json"
    json.dump(DER, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {p}")
    print("\n── 게이트 ──")
    for k, v in gs.items():
        print(f"  {k:>42} : {v}")
