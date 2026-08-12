# -*- coding: utf-8 -*-
"""
verify_raybudget_meaning.py — **광선을 더 쏘면 PathSolver 에서 «정확히 무엇이» 좋아지나.**

사용자(2026-08-11)
> "PathSolver를 뭘 고쳤다는거야? 그럼 40억발을 쏘면 더 괜찮아지는거 아니니?"

⛔ **엔진은 안 고쳤다.** 광선을 22 배 더 쐈을 뿐이다. 이 스크립트는 «더 쏘면 무엇이
   달라지나» 를 예산의 함수로 재고, 수렴 여부·비용·시드와의 관계를 판정한다.

■ 무엇을 읽나 (⛔ 다 읽기만 한다 · GPU 안 쓴다 · 원장 안 덮는다)
  · outputs/raybudget_ladder/spp*_s*_*.npz     40 m 8 계단 × 시드 (E · npaths · seconds)
  · outputs/elev_sweep_shards/*_el*_*.npz      10 m 앙각 7 점 × 3 팔
  · outputs/elevation_sweep_md.json            앙각 원장(교차 확인용)
  · outputs/report07_range40_raybudget.json    40 m 2 예산 원장
  · outputs/raybudget_seed_ladder.json         시드 8 판 원장
  · outputs/deck_ours_by_range.json            우리 커널 비용
  · outputs/rt_no_rcs_verify.json              PathSolver 가 σ 를 안 잰다는 증거

■ 재는 것 (전부 예산의 함수)
  npaths_median · npaths_cv · npaths_zero_frac  경로 수와 그 흔들림
  beat_hz → beat_rel_err_pct · n_beat_ok        박자 추정 오차
  h1_over_h2_db                                 1× − 2× 조화 여유
  peaks_per_rev                                 회전당 첨두 개수 (예측 2)
  oob_frac_pct                                  대역밖(|f| > f_tip) 에너지 비율
  level_db                                      레벨
  sec_per_pose                                  비용

새 산출물만: outputs/verify_raybudget_meaning.json · .png
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                       # noqa: E402
from scipy.signal import spectrogram as _spec                            # noqa: E402
from scipy.signal import find_peaks                                      # noqa: E402

LAD = f"{ROOT}/outputs/raybudget_ladder"
ELS_DIR = f"{ROOT}/outputs/elev_sweep_shards"
OUT_JSON = f"{ROOT}/outputs/verify_raybudget_meaning.json"
OUT_PNG = f"{ROOT}/outputs/verify_raybudget_meaning.png"

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"])
FFL = float(TJ["f_flash_hz"])            # 126.667 Hz — 예측 박자
FTIP40 = float(TJ["f_tip_hz"])           # 1228.72 Hz — 40 m · el −15° 의 날개끝
FC = 3.5e9

# md_mapstyle 규약을 **그대로** 재현한다(우회하지 않는다).
from md_mapstyle import auto_periods, flash_spec, FLASH_HOP, FLASH_PAD   # noqa: E402


# ════════════════════════════════════════════════════════════════════════════
#  지표
# ════════════════════════════════════════════════════════════════════════════
def band_series(E, f_tip, prf=PRF):
    """flash_spec 규약으로 스펙트로그램 → (f, t, S, 날개끝 대역 에너지 g(t))."""
    f, t, S, nper = flash_spec(np.asarray(E, complex), prf, FFL, auto_periods(prf, FFL))
    b = (np.abs(f) >= 0.35 * f_tip) & (np.abs(f) <= 1.00 * f_tip)
    g = (S[b, :] ** 2).sum(axis=0) if b.sum() >= 2 else np.zeros(S.shape[1])
    return f, t, S, g, int(b.sum()), nper


def beat_and_h(g, t):
    """대역 에너지 시계열의 변조 스펙트럼 → (박자, 1×−2× dB). 원장 규약과 동일."""
    if g.size < 8 or not np.isfinite(g).all() or g.max() <= 0:
        return None, None
    y = g - g.mean()
    dt = float(t[1] - t[0]); m = len(y)
    A = np.abs(np.fft.rfft(y * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)
    if A.max() <= 0:
        return None, None
    A = A / A.max()
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])

    def pkv(f0, half=18.0):
        w = (fr >= f0 - half) & (fr <= f0 + half)
        return float(A[w].max()) if w.any() else np.nan
    p1, p2 = pkv(FFL), pkv(2 * FFL)
    h = 20 * np.log10(p1 / p2) if (p1 > 0 and p2 > 0) else np.nan
    return float(pk), float(h)


def peaks_per_rev(g, t):
    """회전당 첨두 개수. 예측 = 2 (2 날개 · 회전 1 번에 플래시 2 회).

    ⭐정의를 한 곳에 못 박는다 — g 를 0..1 로 정규화하고 **prominence 0.15** 이상의
      국소 최대만 센다. 그 다음 «기록 길이 ÷ 회전 주기» 로 나눈다.
      (f_rev = f_flash / 2 = 63.33 Hz. 날개 2 장이므로.)
    ⚠ prominence 문턱은 임의값이다. 문턱을 바꾸면 절대값이 바뀌므로 **예산 사이의
      비교**로만 읽어라(같은 문턱을 모든 팔에 쓴다)."""
    if g.size < 8 or g.max() <= g.min():
        return None
    y = (g - g.min()) / (g.max() - g.min())
    pk, _ = find_peaks(y, prominence=0.15)
    dur = float(t[-1] - t[0])
    n_rev = dur * (FFL / 2.0)
    return float(len(pk) / n_rev) if n_rev > 0 else None


def oob_frac(E, f_tip, prf=PRF):
    """⭐**대역밖 에너지 비율** — 물리가 금지하는 자리에 앉은 에너지의 몫.

    표적 위 어떤 점도 날개끝보다 빠르지 않으므로 |f_D| > f_tip 은 **물리가 없다.**
    거기 있는 에너지는 전부 수치 산물(자세마다 경로 집합이 홱 바뀌는 계단)이다.

    정의: 슬로타임 열 E 의 주기도(periodogram, Hann 창) 전력 중
          |f| > f_tip 의 몫 [%]. DC(동체선) 포함 전체 전력으로 나눈다."""
    E = np.asarray(E, complex)
    if E.size < 16 or not np.any(np.abs(E) > 0):
        return None
    w = np.hanning(E.size)
    P = np.abs(np.fft.fft(E * w)) ** 2
    f = np.fft.fftfreq(E.size, 1.0 / prf)
    tot = P.sum()
    if tot <= 0:
        return None
    return float(100.0 * P[np.abs(f) > f_tip].sum() / tot)


def band_frac(E, f_tip, prf=PRF):
    """날개끝 대역(0.35~1.0·f_tip) 전력의 몫 [%] — «신호가 있기는 한가».

    ⭐대역밖 비율과 **짝**으로 읽어야 한다. 대역밖이 0 이어도 대역안도 0 이면
      그건 «깨끗한» 것이 아니라 **아무것도 없는** 것이다."""
    E = np.asarray(E, complex)
    if E.size < 16 or not np.any(np.abs(E) > 0):
        return None
    P = np.abs(np.fft.fft(E * np.hanning(E.size))) ** 2
    f = np.fft.fftfreq(E.size, 1.0 / prf)
    tot = P.sum()
    if tot <= 0:
        return None
    b = (np.abs(f) >= 0.35 * f_tip) & (np.abs(f) <= 1.00 * f_tip)
    return float(100.0 * P[b].sum() / tot)


def npaths_spectrum(npaths, prf=PRF):
    """⭐**기전 검사** — 경로 «개수» 자체가 몇 Hz 로 흔들리나.

    가설: 경로가 몇 개뿐이면 자세마다 «어느 면이 잡히나» 가 홱 바뀌어 가짜 첨두가 생기고
    그게 주기를 반으로 쪼갠다. 그렇다면 **개수 시계열**이 2·f_flash 에 선을 가져야 한다
    (날개가 들어올 때 한 번, 나갈 때 한 번). 반대로 개수가 조용한데 박자만 2 배면
    가설은 틀린 것이다."""
    if npaths is None:
        return dict(peak_hz=None, r_2x_over_1x_db=None, ac_frac=None)
    x = np.asarray(npaths, float)
    if x.size < 64 or np.std(x) <= 0:
        return dict(peak_hz=None, r_2x_over_1x_db=None,
                    ac_frac=(0.0 if x.size else None))
    y = (x - x.mean()) * np.hanning(x.size)
    A = np.abs(np.fft.rfft(y, n=8 * x.size))
    fr = np.fft.rfftfreq(8 * x.size, 1.0 / prf)
    sel = (fr >= 40) & (fr <= 400)
    if not sel.any() or A[sel].max() <= 0:
        return dict(peak_hz=None, r_2x_over_1x_db=None,
                    ac_frac=float(np.std(x) / (x.mean() + 1e-300)))
    pk = float(fr[sel][int(np.argmax(A[sel]))])

    def v(f0, half=15.0):
        w = (fr >= f0 - half) & (fr <= f0 + half)
        return float(A[w].max()) if w.any() else np.nan
    a1, a2 = v(FFL), v(2 * FFL)
    r = 20 * np.log10(a2 / a1) if (a1 > 0 and a2 > 0) else np.nan
    return dict(peak_hz=round(pk, 2),
                r_2x_over_1x_db=(None if not np.isfinite(r) else round(float(r), 2)),
                ac_frac=round(float(np.std(x) / (x.mean() + 1e-300)), 4))


def dc_stats(E):
    """DC(정지 성분) 지배도. |mean(E)| / rms(E) 와 변조 깊이."""
    E = np.asarray(E, complex)
    r = float(np.sqrt(np.mean(np.abs(E) ** 2)))
    if r <= 0:
        return None, None
    return (float(np.abs(np.mean(E)) / r),
            float(np.std(np.abs(E)) / (np.mean(np.abs(E)) + 1e-300)))


# ════════════════════════════════════════════════════════════════════════════
#  40 m 사다리 적재
# ════════════════════════════════════════════════════════════════════════════
def load_ladder():
    cens = {}
    for f in glob.glob(f"{LAD}/spp*_s*_*.npz"):
        b = os.path.basename(f)
        spp = int(b.split("_")[0][3:]); seed = int(b.split("_")[1][1:])
        cens.setdefault(spp, {}).setdefault(seed, []).append(f)
    out = {}
    for spp in sorted(cens):
        arms = []
        for seed in sorted(cens[spp]):
            fs = sorted(cens[spp][seed])
            E, idx, npa, secs, nfull = [], [], [], 0.0, None
            nsh = None
            for f in fs:
                z = np.load(f, allow_pickle=True)
                m = np.asarray(z["meta"], float)
                E.append(z["E"]); idx.append(z["idx"]); npa.append(z["npaths"])
                secs += float(m[5]); nfull = int(m[4]); nsh = int(m[2])
            idx = np.concatenate(idx); o = np.argsort(idx)
            complete = (len(fs) == nsh) and (len(idx) == nfull)
            arms.append(dict(seed=seed, n=len(idx), complete=bool(complete),
                             n_shards=len(fs), n_shards_expected=int(nsh),
                             E=np.concatenate(E)[o],
                             npaths=np.concatenate(npa)[o].astype(float),
                             seconds=secs))
        out[spp] = arms
    return out


def arm_metrics(E, npaths, f_tip):
    f, t, S, g, nb, nper = band_series(E, f_tip)
    pk, h = beat_and_h(g, t)
    dcd, mod = dc_stats(E)
    d = dict(
        n=int(E.size),
        npaths_median=float(np.median(npaths)) if npaths is not None else None,
        npaths_mean=float(np.mean(npaths)) if npaths is not None else None,
        npaths_cv=(float(np.std(npaths) / np.mean(npaths))
                   if npaths is not None and np.mean(npaths) > 0 else None),
        npaths_zero_frac=(float(np.mean(npaths == 0)) if npaths is not None else None),
        npaths_step_rel=(float(np.mean(np.abs(np.diff(npaths))) / np.mean(npaths))
                         if npaths is not None and np.mean(npaths) > 0 else None),
        level_db=(float(20 * np.log10(np.mean(np.abs(E)) + 1e-300))),
        beat_hz=pk, h1_over_h2_db=h,
        beat_rel_err_pct=(None if pk is None else float(100.0 * (pk - FFL) / FFL)),
        peaks_per_rev=peaks_per_rev(g, t),
        oob_frac_pct=oob_frac(E, f_tip),
        dc_dominance=dcd, mod_depth=mod,
        band_frac_pct=band_frac(E, f_tip),
        e_step_rel=float(np.mean(np.abs(np.diff(E))) / (np.mean(np.abs(E)) + 1e-300)),
        n_band_bins=nb, nperseg=int(nper))
    ns = npaths_spectrum(npaths)
    d["npaths_beat_hz"] = ns["peak_hz"]
    d["npaths_2x_over_1x_db"] = ns["r_2x_over_1x_db"]
    d["npaths_ac_frac"] = ns["ac_frac"]
    if npaths is not None and np.std(npaths) > 0:
        d["corr_absE_npaths"] = float(np.corrcoef(np.abs(E), npaths)[0, 1])
    else:
        d["corr_absE_npaths"] = None
    return d


def _f(x, nd=3):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def agg(vals, nd=3):
    v = [x for x in vals if x is not None and np.isfinite(x)]
    if not v:
        return dict(median=None, mean=None, sd=None, n=0)
    return dict(median=_f(np.median(v), nd), mean=_f(np.mean(v), nd),
                sd=_f(np.std(v, ddof=1), nd) if len(v) > 1 else None, n=len(v))


# ════════════════════════════════════════════════════════════════════════════
#  그림 — ⭐집 규약: 그림 안 글자는 전부 영어
# ════════════════════════════════════════════════════════════════════════════
#  dataviz 규약: 형태 먼저(순서 있는 수치축 위의 크기 변화 → 선+점 소다중),
#  축은 패널마다 하나, 범주색은 고정 순서(참조 팔레트 슬롯 1·2·7),
#  물리 진리선은 계열색이 아니라 중성 회색 파선.
#  ⚠ scripts/validate_palette.js 는 이 기계의 node(12) 가 ESM 을 못 읽어 **못 돌렸다**.
#    그래서 참조 팔레트의 **검증된 슬롯 값을 그대로** 쓰고 새 색을 만들지 않았다.
C_PS = "#2a78d6"      # slot 1 blue  — Sionna PathSolver
C_OURS = "#eb6834"    # slot 2 orange — Ours (SBR+PO)
C_ALT = "#4a3aa7"     # slot 7 violet — second measure inside a panel
C_TRUTH = "#8a8a84"   # neutral — physics / prediction
C_TXT = "#0b0b0b"
C_TXT2 = "#52514e"
C_GRID = "#dedddb"


def figure(res) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rungs = res["ladder_40m"]["rungs"]
    ou = res["ours_40m_reference"]
    x = np.array([r["spp_m"] for r in rungs], float)
    STARVED = 40.0            # 이 아래 계단은 자세당 경로가 0~2 개다

    def med(key, sub="median"):
        return np.array([np.nan if r[key][sub] is None else r[key][sub]
                         for r in rungs], float)

    def seedvals(r, key):
        return [q[key] for q in r["arms"]
                if q.get(key) is not None and np.isfinite(q[key])]

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": C_TXT2,
                         "axes.labelcolor": C_TXT, "text.color": C_TXT,
                         "xtick.color": C_TXT2, "ytick.color": C_TXT2,
                         "axes.grid": True, "grid.color": C_GRID,
                         "grid.linewidth": 0.6, "axes.axisbelow": True})
    fig, ax = plt.subplots(2, 3, figsize=(15.0, 8.4), facecolor="white")
    fig.suptitle("What more rays actually buy in Sionna PathSolver   ·   "
                 "40 m · DJI Matrice 4E · el −15° · PRF 19.7 kHz · 1,024 poses per seed",
                 fontsize=13.5, fontweight="bold", y=0.985)

    def deco(a, t, yl, note=None):
        a.set_title(t, fontsize=10.5, fontweight="bold", loc="left", pad=6)
        a.set_xlabel("rays per source", fontsize=8.5, color=C_TXT2)
        a.set_ylabel(yl, fontsize=8.5, color=C_TXT2)
        a.set_xscale("log")
        a.set_xlim(0.7, 6500)
        a.set_xticks([1, 10, 100, 1000, 4000])
        a.set_xticklabels(["1 M", "10 M", "100 M", "1,000 M", "4,000 M"], fontsize=8)
        a.axvspan(0.7, STARVED, color="#f0efec", zorder=0)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        if note:
            a.text(0.985, 0.03, note, transform=a.transAxes, ha="right", va="bottom",
                   fontsize=8, color=C_TXT2)

    # ── (1) 경로 수 ─────────────────────────────────────────────────────────
    a = ax[0, 0]
    y = med("npaths_median", "mean")
    good = x >= STARVED
    a.plot(x[good], y[good], "-o", color=C_PS, lw=2.2, ms=8,
           label="paths per pose (mean over seeds)")
    bad = (~good) & (y > 0)
    a.plot(x[bad], y[bad], "o", mfc="white", mec=C_PS, mew=1.6, ms=8,
           label="starved rungs (0–2 paths)")
    xr = np.array([64.0, 4000.0])
    a.plot(xr, y[x == 64][0] * xr / 64.0, "--", color=C_TRUTH, lw=1.8,
           label="slope 1 — one ray buys one path")
    a.set_yscale("log"); a.set_ylim(0.1, 600)
    a.text(0.05, 0.93, "paths still grow ∝ rays at 4 billion\n"
                       "→ collection has NOT saturated",
           transform=a.transAxes, fontsize=8.8, color=C_TXT, va="top")
    deco(a, "1 · Paths per pose — no saturation in sight", "paths per pose")
    a.legend(fontsize=7.8, frameon=False, loc="lower right")

    # ── (2) 대역밖 ──────────────────────────────────────────────────────────
    a = ax[0, 1]
    yo = med("oob_frac_pct", "mean"); yb = med("band_frac_pct", "mean")
    a.plot(x, yo, "-o", color=C_PS, lw=2.2, ms=8, label="out-of-band  |f| > f_tip")
    a.plot(x, yb, "-s", color=C_ALT, lw=1.6, ms=6, alpha=0.85,
           label="in-band  0.35–1.0 f_tip")
    a.axhline(ou["oob_frac_pct"], color=C_OURS, lw=2.0,
              label=f"ours out-of-band  {ou['oob_frac_pct']:.2f} %")
    a.axhline(ou["band_frac_pct"], color=C_OURS, lw=1.4, ls=":",
              label=f"ours in-band  {ou['band_frac_pct']:.2f} %")
    a.set_yscale("log"); a.set_ylim(0.02, 60)
    a.annotate("16 M: 90 % of poses\nreturn nothing at all",
               xy=(16, 7.5), xytext=(1.05, 1.6), fontsize=8, color=C_TXT2,
               arrowprops=dict(arrowstyle="-", color=C_TXT2, lw=0.8))
    a.text(0.985, 0.055, "low at both ends for opposite reasons:\n"
                         "left = no signal · right = smooth signal",
           transform=a.transAxes, ha="right", va="bottom", fontsize=8, color=C_TXT2)
    deco(a, "2 · Out-of-band energy is NOT monotone", "share of Doppler power [%]")
    a.legend(fontsize=7.6, frameon=False, loc="upper right")

    # ── (3) 레벨 ────────────────────────────────────────────────────────────
    a = ax[0, 2]
    lab = True
    for r in rungs:
        vs = [v for v in seedvals(r, "level_db") if v > -1000]
        if vs:
            a.plot([r["spp_m"]] * len(vs), vs, "o", color=C_PS, ms=5, alpha=0.35,
                   label="one seed" if lab else None); lab = False
    yl = med("level_db", "mean"); g = yl > -1000
    a.plot(x[g], yl[g], "-o", color=C_PS, lw=2.2, ms=8, label="mean over seeds")
    a.set_ylim(-190, -132)
    a.annotate("", xy=(4000, -144.6), xytext=(178, -157.6),
               arrowprops=dict(arrowstyle="->", color=C_TXT2, lw=1.2, ls="--"))
    a.text(0.05, 0.93, "+13.0 dB from 178 M to 4,000 M,\n"
                       "and the last step (×1.4 rays) is still +3.6 dB\n"
                       "→ the estimate is still climbing",
           transform=a.transAxes, fontsize=8.6, color=C_TXT, va="top")
    deco(a, "3 · Level — missing energy keeps coming back",
         "level  20·log₁₀ mean|E|  [dB]")
    a.legend(fontsize=7.8, frameon=False, loc="lower right")

    # ── (4) 박자 ────────────────────────────────────────────────────────────
    a = ax[1, 0]
    lab = True
    for r in rungs:
        vs = seedvals(r, "beat_hz")
        if vs:
            a.plot([r["spp_m"]] * len(vs), vs, "o", color=C_PS, ms=8, alpha=0.6,
                   label="one seed" if lab else None); lab = False
    a.axhline(FFL, color=C_TRUTH, ls="--", lw=1.8, label=f"truth {FFL:.1f} Hz  (1×)")
    a.axhline(2 * FFL, color=C_TRUTH, ls=":", lw=1.6, label=f"{2*FFL:.1f} Hz  (2×)")
    a.axhline(ou["beat_hz"], color=C_OURS, lw=2.0, label=f"ours {ou['beat_hz']:.1f} Hz")
    a.set_ylim(90, 540)
    for r, txt in ((178.0, "2 of 7\nright"), (4000.0, "5 of 8\nright")):
        a.text(r, 200, txt, ha="center", va="center", fontsize=8, color=C_TXT2)
    deco(a, "4 · Blade-flash rate — the seed decides, not the budget",
         "estimated beat [Hz]")
    a.set_yticks([100, 150, 200, 250, 300, 350, 400])
    a.legend(fontsize=7.6, frameon=False, loc="upper left", ncol=2,
             bbox_to_anchor=(0.0, 1.02))

    # ── (5) 여유폭 ──────────────────────────────────────────────────────────
    a = ax[1, 1]
    lab = True
    for r in rungs:
        vs = seedvals(r, "h1_over_h2_db")
        if vs:
            a.plot([r["spp_m"]] * len(vs), vs, "o", color=C_PS, ms=6, alpha=0.35,
                   label="one seed" if lab else None); lab = False
    ym = med("h1_over_h2_db", "mean")
    a.plot(x, ym, "-o", color=C_PS, lw=2.2, ms=8, label="mean over seeds")
    a.axhline(0, color=C_TRUTH, ls="--", lw=1.8, label="0 dB — coin flip")
    a.axhline(ou["h1_over_h2_db"], color=C_OURS, lw=2.0,
              label=f"ours {ou['h1_over_h2_db']:+.1f} dB")
    a.set_ylim(-12, 30)
    a.text(0.985, 0.055, "seed scatter is ±5 dB, so a +2 dB mean margin\n"
                         "still flips the answer about a third of the time",
           transform=a.transAxes, ha="right", va="bottom", fontsize=8, color=C_TXT2)
    deco(a, "5 · 1× minus 2× margin — never clears the noise",
         "1× peak − 2× peak  [dB]")
    a.legend(fontsize=7.6, frameon=False, loc="upper left", ncol=2)

    # ── (6) 회전당 첨두 ─────────────────────────────────────────────────────
    a = ax[1, 2]
    lab = True
    for r in rungs:
        vs = seedvals(r, "peaks_per_rev")
        if vs:
            a.plot([r["spp_m"]] * len(vs), vs, "o", color=C_PS, ms=6, alpha=0.35,
                   label="one seed" if lab else None); lab = False
    yp = med("peaks_per_rev", "mean")
    a.plot(x, yp, "-o", color=C_PS, lw=2.2, ms=8, label="mean over seeds")
    a.axhline(2.0, color=C_TRUTH, ls="--", lw=1.8, label="physics: 2 blades → 2 / rev")
    a.axhline(ou["peaks_per_rev"], color=C_OURS, lw=2.0,
              label=f"ours {ou['peaks_per_rev']:.2f} / rev")
    a.set_ylim(0, 8.5)
    a.text(0.985, 0.055, "flat from 178 M to 4,000 M — the extra peaks\n"
                         "are not bought away",
           transform=a.transAxes, ha="right", va="bottom", fontsize=8, color=C_TXT2)
    deco(a, "6 · Peaks per revolution — rays do not fix it",
         "peaks per rotor revolution")
    a.legend(fontsize=7.6, frameon=False, loc="upper left")

    fig.text(0.010, 0.011,
             "Shaded band = starved rungs (≤ 16 M rays: 0–2 paths per pose, nothing to "
             "measure).   Rungs 1 M–64 M and 712 M–2,848 M carry only 3 seeds; "
             "178 M carries 7 and 4,000 M carries 8.\n"
             "Ledger outputs/verify_raybudget_meaning.json  ·  shards "
             "outputs/raybudget_ladder/  ·  ours reference outputs/deck_ours_by_range.npz "
             "key R40/E (4,096 poses, same site and same STFT convention).",
             fontsize=7.3, color=C_TXT2, linespacing=1.5)
    fig.tight_layout(rect=[0, 0.042, 1, 0.962])
    fig.savefig(OUT_PNG, dpi=170, facecolor="white")
    plt.close(fig)
    print(f"✅ {OUT_PNG}")


def main() -> None:
    res = {"_meta": {
        "generator": "benchmark/verify_raybudget_meaning.py",
        "question_ko": ("광선을 더 쏘면 PathSolver 에서 정확히 무엇이 좋아지나. "
                        "40 억 발이면 수렴인가."),
        "no_gpu_ko": "⛔ GPU 를 쓰지 않는다. 기존 npz·json 을 읽어 CPU 로만 다시 잰다.",
        "prf_hz": PRF, "f_flash_hz": FFL, "f_tip_40m_hz": FTIP40, "fc_hz": FC,
        "stft_ko": "md_mapstyle.flash_spec + auto_periods — 덱·기존 원장과 같은 규약",
        "oob_def_ko": ("대역밖 = |f_D| > f_tip. 표적 위 어떤 점도 날개끝보다 빠를 수 없으므로 "
                       "거기 있는 전력은 전부 수치 산물이다. Hann 창 주기도 전력의 몫[%]."),
        "peaks_def_ko": "정규화 g(t) 의 prominence ≥ 0.15 국소최대 수 ÷ 회전 수(f_rev=63.33 Hz)",
    }}

    # ── 1. 40 m 사다리 8 계단 ────────────────────────────────────────────────
    lad = load_ladder()
    rungs = []
    for spp in sorted(lad):
        arms_m, arms_raw = [], []
        for a in lad[spp]:
            if not a["complete"]:
                arms_raw.append(dict(seed=a["seed"], skipped_ko=(
                    f"샤드 {a['n_shards']}/{a['n_shards_expected']} 뿐 — 자세가 "
                    f"등간격이 아니라 STFT 가 성립하지 않는다. 제외."), n=a["n"]))
                continue
            m = arm_metrics(a["E"], a["npaths"], FTIP40)
            m.update(seed=a["seed"], seconds=round(a["seconds"], 1),
                     sec_per_pose=round(a["seconds"] / max(1, a["n"]), 4))
            arms_m.append(m)
            arms_raw.append({k: (_f(v, 4) if isinstance(v, float) else v)
                             for k, v in m.items()})
        if not arms_m:
            continue
        beats = [a["beat_hz"] for a in arms_m]
        ok = [b for b in beats if b is not None and abs(b - FFL) / FFL < 0.05]
        two = [b for b in beats if b is not None and abs(b - 2 * FFL) / (2 * FFL) < 0.05]
        rungs.append(dict(
            spp=spp, spp_m=spp / 1e6, n_seeds=len(arms_m),
            n_poses=int(np.median([a["n"] for a in arms_m])),
            npaths_median=agg([a["npaths_median"] for a in arms_m], 1),
            npaths_cv=agg([a["npaths_cv"] for a in arms_m], 4),
            npaths_zero_frac=agg([a["npaths_zero_frac"] for a in arms_m], 4),
            npaths_step_rel=agg([a["npaths_step_rel"] for a in arms_m], 4),
            level_db=agg([a["level_db"] for a in arms_m], 3),
            beat_hz=[_f(b, 2) for b in beats],
            n_beat_1x=len(ok), n_beat_2x=len(two), n_beat_other=len(beats) - len(ok) - len(two),
            beat_abs_rel_err_pct=agg([abs(a["beat_rel_err_pct"]) for a in arms_m
                                      if a["beat_rel_err_pct"] is not None], 2),
            h1_over_h2_db=agg([a["h1_over_h2_db"] for a in arms_m], 2),
            peaks_per_rev=agg([a["peaks_per_rev"] for a in arms_m], 3),
            oob_frac_pct=agg([a["oob_frac_pct"] for a in arms_m], 4),
            band_frac_pct=agg([a["band_frac_pct"] for a in arms_m], 4),
            e_step_rel=agg([a["e_step_rel"] for a in arms_m], 4),
            mod_depth=agg([a["mod_depth"] for a in arms_m], 4),
            npaths_ac_frac=agg([a["npaths_ac_frac"] for a in arms_m], 4),
            npaths_beat_hz=[a["npaths_beat_hz"] for a in arms_m],
            npaths_2x_over_1x_db=agg([a["npaths_2x_over_1x_db"] for a in arms_m], 2),
            corr_absE_npaths=agg([a["corr_absE_npaths"] for a in arms_m], 3),
            sec_per_pose=agg([a["sec_per_pose"] for a in arms_m], 4),
            arms=arms_raw))
    res["ladder_40m"] = dict(
        range_m=40.0, el_deg=-15.0, drone="matrice4e", f_tip_hz=FTIP40,
        shard_dir=LAD, rungs=rungs)

    # ── 2. 수렴 판정 — 이웃 계단 차이가 줄고 있나 ────────────────────────────
    def series(key, sub="median"):
        return [(r["spp_m"], (r[key][sub] if isinstance(r[key], dict) else r[key]))
                for r in rungs]

    conv = {}
    for key in ("level_db", "oob_frac_pct", "npaths_cv", "e_step_rel",
                "peaks_per_rev", "beat_abs_rel_err_pct"):
        s = [(x, y) for x, y in series(key) if y is not None]
        steps = []
        for (x0, y0), (x1, y1) in zip(s[:-1], s[1:]):
            steps.append(dict(from_m=x0, to_m=x1, d=_f(y1 - y0, 4),
                              ray_ratio=_f(x1 / x0, 2)))
        conv[key] = dict(values=[(x, _f(y, 4)) for x, y in s], steps=steps,
                         monotonic=bool(all(st["d"] is not None for st in steps) and (
                             all(st["d"] >= 0 for st in steps) or
                             all(st["d"] <= 0 for st in steps))))
    res["convergence_40m"] = conv

    # ── 2b. ⭐경로 수가 광선에 비례하나 (포화했나) ───────────────────────────
    good = [r for r in rungs if (r["npaths_median"]["mean"] or 0) >= 1.0]
    xs = np.log(np.array([r["spp_m"] for r in good]))
    ys = np.log(np.array([r["npaths_median"]["mean"] for r in good]))
    slope = float(np.polyfit(xs, ys, 1)[0]) if len(good) >= 3 else None
    top = [r for r in rungs if r["spp_m"] >= 64]
    xt = np.log(np.array([r["spp_m"] for r in top]))
    slope_top = float(np.polyfit(xt, np.log(np.array(
        [r["npaths_median"]["mean"] for r in top])), 1)[0])
    slope_top_med = float(np.polyfit(xt, np.log(np.array(
        [r["npaths_median"]["median"] for r in top])), 1)[0])
    res["path_yield"] = dict(
        loglog_slope_paths_vs_rays=_f(slope, 3),
        loglog_slope_collection_regime_64M_to_4000M=dict(
            from_mean=_f(slope_top, 3), from_median=_f(slope_top_med, 3),
            note_ko="⭐굶은 계단(1~16 M)을 뺀 «수집 구간» 만. 1.00 이면 순수 선형이다."),
        slope_meaning_ko=("1.0 이면 광선 하나가 경로 하나를 **선형으로** 더 준다 = "
                          "아직 수집 단계이고 포화가 안 왔다는 뜻. 0 에 가까우면 포화."),
        rows=[dict(spp_m=r["spp_m"], npaths_mean=r["npaths_median"]["mean"],
                   paths_per_million_rays=_f((r["npaths_median"]["mean"] or 0) / r["spp_m"], 5))
              for r in rungs],
        step_ratios=[dict(from_m=a["spp_m"], to_m=b["spp_m"],
                          ray_ratio=_f(b["spp_m"] / a["spp_m"], 2),
                          path_ratio=_f((b["npaths_median"]["mean"] or 0) /
                                        max(a["npaths_median"]["mean"] or 1e-9, 1e-9), 2))
                     for a, b in zip(top[:-1], top[1:])])

    # ── 2c. ⭐시드 산포가 1/√경로 로 주나 (몬테카를로 한계) ──────────────────
    sq = []
    for r in rungs:
        npm = r["npaths_median"]["mean"]
        sd = r["level_db"]["sd"]
        if not npm or npm < 1 or sd is None or not np.isfinite(sd) or sd > 100:
            continue
        pred = 8.686 / np.sqrt(npm)          # 20log10(1+1/√N) 의 소신호 근사
        sq.append(dict(spp_m=r["spp_m"], n_seeds=r["n_seeds"],
                       npaths_mean=npm, sd_level_db=sd,
                       sqrtN_prediction_db=_f(pred, 3),
                       observed_over_sqrtN=_f(sd / pred, 2)))
    res["mc_scaling"] = dict(
        rows=sq,
        def_ko=("시드 간 레벨 표준편차를 «경로가 독립 표본이면 이래야 한다» 는 값 "
                "8.686/√경로수 와 견준다. 1 이면 순수 몬테카를로, 1 보다 크면 "
                "√N 으로 안 지워지는 몫이 남아 있다는 뜻."))

    # ── 2d. 우리 커널 40 m 기준선 (같은 자리·같은 규약) ──────────────────────
    zo = np.load(f"{ROOT}/outputs/deck_ours_by_range.npz", allow_pickle=True)
    Eo = zo["R40/E"]
    om = arm_metrics(Eo, None, FTIP40)
    res["ours_40m_reference"] = dict(
        source="outputs/deck_ours_by_range.npz key 'R40/E' (4096 자세, el −15°, 40 m)",
        level_db=_f(om["level_db"], 2), beat_hz=_f(om["beat_hz"], 2),
        h1_over_h2_db=_f(om["h1_over_h2_db"], 2),
        peaks_per_rev=_f(om["peaks_per_rev"], 3),
        oob_frac_pct=_f(om["oob_frac_pct"], 4),
        band_frac_pct=_f(om["band_frac_pct"], 4),
        mod_depth=_f(om["mod_depth"], 4),
        e_step_rel=_f(om["e_step_rel"], 4),
        caveat_ko=("⚠ 자세 수가 4,096 이라 사다리(1,024)보다 기록이 4 배 길다. "
                   "박자·대역밖은 길이에 크게 안 걸리지만 «첨두/회전» 은 표본이 "
                   "많을수록 안정하다 — 절대 비교는 조심."))

    # ── 3. 10 m 앙각 (2 예산) ────────────────────────────────────────────────
    from drones import DRONES                                            # noqa: E402
    spec = DRONES[TJ.get("drone", "matrice4e")]
    lam = 2.998e8 / FC
    Rp = spec.prop_dia_mm / 2000.0
    f_rev = float(getattr(spec, "hover_rpm", 6000.0)) / 60.0

    def ftip_el(el):
        return 2.0 * (2 * np.pi * f_rev * Rp) / lam * np.cos(np.radians(el))

    engines = sorted({os.path.basename(f).rsplit("_el", 1)[0]
                      for f in glob.glob(f"{ELS_DIR}/*_el*.npz")})
    elev = []
    for eng in engines:
        for el in (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0):
            fs = sorted(glob.glob(f"{ELS_DIR}/{eng}_el{el:+.0f}_*.npz"))
            if not fs:
                continue
            E = None; npa = None; secs = 0.0
            for f in fs:
                z = np.load(f)
                m = np.asarray(z["meta"], float)
                ii = z["idx"].astype(int)
                if E is None:
                    E = np.zeros(int(m[3]), complex)
                    npa = np.full(int(m[3]), np.nan)
                E[ii] = z["E"]; secs += float(m[5])
                if "npaths" in z:
                    npa[ii] = z["npaths"]
            if not np.isfinite(E).all() or (E == 0).mean() > 0.01:
                # ⭐미완 실행(샤드가 다 안 찼다) — 제외한다. 0 자세가 섞이면
                #   모든 지표가 «계단» 쪽으로 거짓 이동한다.
                continue
            ft = max(ftip_el(el), 1e-6)
            npv = None if (npa is None or not np.isfinite(npa).all()) else npa
            mm = arm_metrics(E, npv, ft)
            mm.update(engine=eng, el_deg=el, f_tip_hz=round(float(ft), 1),
                      seconds=round(secs, 1), sec_per_pose=round(secs / E.size, 4))
            elev.append({k: (_f(v, 4) if isinstance(v, float) else v)
                         for k, v in mm.items()})
    res["elevation_10m"] = dict(range_m=10.0, shard_dir=ELS_DIR, rows=elev)

    # ── 4. el 0 만 왜 다른가 — 예산 불변성 검사 ──────────────────────────────
    def get(eng, el, k):
        for r in elev:
            if r["engine"] == eng and abs(r["el_deg"] - el) < 1e-9:
                return r.get(k)
        return None

    el0 = []
    for el in (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0):
        a = get("sionna", el, "level_db"); b = get("sionna_p250000000", el, "level_db")
        el0.append(dict(
            el_deg=el,
            level_db_11M=a, level_db_250M=b,
            level_delta_db=_f(None if (a is None or b is None) else b - a, 3),
            npaths_11M=get("sionna", el, "npaths_median"),
            npaths_250M=get("sionna_p250000000", el, "npaths_median"),
            dc_dominance_11M=get("sionna", el, "dc_dominance"),
            dc_dominance_250M=get("sionna_p250000000", el, "dc_dominance"),
            mod_depth_11M=get("sionna", el, "mod_depth"),
            mod_depth_250M=get("sionna_p250000000", el, "mod_depth"),
            mod_depth_ours=get("ours", el, "mod_depth"),
            level_db_ours=get("ours", el, "level_db"),
            oob_11M=get("sionna", el, "oob_frac_pct"),
            oob_250M=get("sionna_p250000000", el, "oob_frac_pct"),
            oob_ours=get("ours", el, "oob_frac_pct"),
            band_frac_11M=get("sionna", el, "band_frac_pct"),
            band_frac_250M=get("sionna_p250000000", el, "band_frac_pct"),
            band_frac_ours=get("ours", el, "band_frac_pct")))

    # ⭐el 0 을 자세 열 수준에서 더 판다 — «상수 하나» 인가
    deep = []
    for eng in ("sionna", "sionna_p250000000", "ours"):
        for el in (0.0, -15.0):
            fs = sorted(glob.glob(f"{ELS_DIR}/{eng}_el{el:+.0f}_*.npz"))
            if not fs:
                continue
            E = None; npa = None
            for f in fs:
                z = np.load(f); m = np.asarray(z["meta"], float); ii = z["idx"].astype(int)
                if E is None:
                    E = np.zeros(int(m[3]), complex); npa = np.full(int(m[3]), np.nan)
                E[ii] = z["E"]
                if "npaths" in z:
                    npa[ii] = z["npaths"]
            a = np.abs(E)
            deep.append(dict(
                engine=eng, el_deg=el,
                absE_ptp_db=_f(20 * np.log10(a.max() / max(a.min(), 1e-300)), 2),
                absE_rel_sd=_f(float(np.std(a) / np.mean(a)), 5),
                n_unique_absE=int(np.unique(np.round(a / max(a.mean(), 1e-300), 6)).size),
                npaths_unique=(None if not np.isfinite(npa).all()
                               else sorted(set(int(v) for v in npa))[:12]),
                npaths_sd=(None if not np.isfinite(npa).all() else _f(float(np.std(npa)), 3)),
                phase_ptp_deg=_f(float(np.ptp(np.unwrap(np.angle(E)))) * 180 / np.pi, 2)))
    res["el0_probe"] = dict(rows=el0, deep=deep,
                            live_job_note_ko=(
                                "⚠ outputs/elev_sweep_shards/ 에 sionna_p1000000000_el+0_* 가 "
                                "**진행 중**이다(08:53·08:55 두 샤드뿐). 미완이라 이 원장에서 "
                                "제외했다 — 다 차면 다시 재야 한다."))

    # ── 5. 비용 ──────────────────────────────────────────────────────────────
    ours = json.load(open(f"{ROOT}/outputs/deck_ours_by_range.json"))
    n_ours = int(ours["_meta"]["n"])
    res["cost"] = dict(
        ours_kernel=dict(
            source="outputs/deck_ours_by_range.json ranges.{R}.cpu_seconds ÷ _meta.n",
            n=n_ours,
            sec_per_pose={k: round(v["cpu_seconds"] / n_ours, 4)
                          for k, v in ours["ranges"].items()}),
        pathsolver_40m_by_budget=[
            dict(spp_m=r["spp_m"], sec_per_pose=r["sec_per_pose"]["median"],
                 n_seeds=r["n_seeds"]) for r in rungs],
        caveat_ko=("⚠ 벽시계다. 이 실행들은 GPU 를 다른 작업과 나눠 썼으므로 같은 예산 "
                   "안에서도 시드마다 최대 2.5 배 차이가 난다(sd 를 함께 싣는다). "
                   "예산 사이의 배수는 그 잡음보다 훨씬 커서 방향은 읽을 수 있다."))

    # ── 6. 시드 vs 예산 — 같은 비용이면 어느 쪽이 이득인가 ────────────────────
    sl = json.load(open(f"{ROOT}/outputs/raybudget_seed_ladder.json"))
    cells = {c["spp"]: c for c in sl["cells"]}
    res["seed_vs_budget"] = dict(
        source="outputs/raybudget_seed_ladder.json cells[*].structure",
        rows=[dict(spp_m=c["spp_m"], n_seeds=c["n_seeds"],
                   sd_level_db=c["sd_level_db"],
                   ratio_observed_over_iid=c["structure"]["ratio_observed_over_iid"],
                   predicted_if_iid_db=c["structure"]["predicted_if_iid_db"],
                   sd_within_pose_db=c["structure"]["sd_within_pose_db"])
              for c in sl["cells"]])
    if 178_000_000 in cells and 4_000_000_000 in cells:
        c1, c2 = cells[178_000_000], cells[4_000_000_000]
        # 같은 비용 = 광선 총량. 178M×K 시드 vs 4000M×1 시드.
        k_equal = 4_000_000_000 / 178_000_000
        res["seed_vs_budget"]["equal_cost"] = dict(
            k_seeds_of_178M_for_one_4000M=round(k_equal, 1),
            sd_level_178M=c1["sd_level_db"], sd_level_4000M=c2["sd_level_db"],
            sd_of_mean_of_k_seeds_178M_db=round(c1["sd_level_db"] / np.sqrt(k_equal), 3),
            note_ko=("⭐시드 평균은 **판별 평균 레벨**에만 유효하다. 시드 K 판을 평균하면 "
                     "레벨 산포는 sd/√K 로 준다(시드끼리는 독립 추첨이므로). "
                     "그러나 박자·조화 여유는 판마다 다른 답을 주므로 «평균» 이 정의되지 "
                     "않는다 — 투표해야 하고, 투표는 다수가 틀리면 같이 틀린다."))

    # ── 7. 기전 — 가설 검사 ─────────────────────────────────────────────────
    mech = {}
    # (a) 같은 계단 안에서 경로가 적은 시드가 2× 를 읽나?
    within = []
    for r in rungs:
        arms = [a for a in r["arms"] if a.get("beat_hz") is not None]
        if len(arms) < 3:
            continue
        one = [a["npaths_median"] for a in arms
               if abs(a["beat_hz"] - FFL) / FFL < 0.05]
        twx = [a["npaths_median"] for a in arms
               if abs(a["beat_hz"] - 2 * FFL) / (2 * FFL) < 0.05]
        within.append(dict(spp_m=r["spp_m"],
                           npaths_of_1x_seeds=one, npaths_of_2x_seeds=twx,
                           mean_1x=_f(np.mean(one) if one else None, 1),
                           mean_2x=_f(np.mean(twx) if twx else None, 1)))
    mech["within_rung_paths_vs_beat"] = within
    # (b) 계단 사이 — 경로 수와 «1× 를 맞춘 시드 비율»
    mech["across_rung"] = [dict(spp_m=r["spp_m"], npaths=r["npaths_median"]["median"],
                                frac_beat_1x=round(r["n_beat_1x"] / r["n_seeds"], 3),
                                n_seeds=r["n_seeds"],
                                oob_pct=r["oob_frac_pct"]["median"],
                                peaks_per_rev=r["peaks_per_rev"]["median"])
                           for r in rungs]
    res["mechanism"] = mech

    # ── 6b. 같은 벽시계면 어느 쪽이 이득인가 ─────────────────────────────────
    r178 = next(r for r in rungs if r["spp_m"] == 178.0)
    r4000 = next(r for r in rungs if r["spp_m"] == 4000.0)
    wall = (r4000["sec_per_pose"]["median"] / r178["sec_per_pose"]["median"])
    res["seed_vs_budget"]["equal_wallclock"] = dict(
        sec_per_pose_178M=r178["sec_per_pose"]["median"],
        sec_per_pose_4000M=r4000["sec_per_pose"]["median"],
        k_seeds_of_178M_per_one_4000M=round(float(wall), 2),
        why_not_22p5_ko=("광선을 22.5 배 늘렸는데 벽시계는 7.8 배만 늘었다 — 낮은 예산에는 "
                         "광선과 무관한 고정비(메쉬 쓰기·씬 조립·커널 기동)가 크다."),
        ledger_sd_178M_db=cells[178_000_000]["sd_level_db"],
        ledger_sd_4000M_db=cells[4_000_000_000]["sd_level_db"],
        sd_of_mean_of_k_seeds_178M_db=round(
            float(cells[178_000_000]["sd_level_db"] / np.sqrt(wall)), 3),
        verdict_ko=("⭐**레벨**만 보면 같은 벽시계에서 시드 여러 판이 이긴다. "
                    "그러나 **박자**는 평균이 안 되고 투표해야 하는데, 178 M 의 다수는 "
                    "2 배(오답)이고 4,000 M 의 다수는 1 배(정답)다 — 그래서 축에 따라 "
                    "답이 갈린다. 무조건문 금지."),
        beat_majority=dict(
            m178=dict(n_1x=r178["n_beat_1x"], n_2x=r178["n_beat_2x"],
                      n_seeds=r178["n_seeds"], majority="2x_WRONG"),
            m4000=dict(n_1x=r4000["n_beat_1x"], n_2x=r4000["n_beat_2x"],
                       n_seeds=r4000["n_seeds"], majority="1x_RIGHT")))

    # ── 7b. ⭐«동전 던지기» 예측 — 여유폭이 잡음보다 작으면 답이 뒤집힌다 ────
    from math import erf, sqrt as _sq
    coin = []
    for r in rungs:
        mu, sd = r["h1_over_h2_db"]["mean"], r["h1_over_h2_db"]["sd"]
        if mu is None or sd is None or sd <= 0:
            continue
        p = 0.5 * (1.0 + erf((0.0 - mu) / (sd * _sq(2.0))))
        coin.append(dict(spp_m=r["spp_m"], margin_mean_db=mu, margin_sd_db=sd,
                         predicted_frac_wrong=round(float(p), 3),
                         observed_frac_wrong=round(
                             (r["n_beat_2x"] + r["n_beat_other"]) / r["n_seeds"], 3),
                         n_seeds=r["n_seeds"]))
    res["mechanism"]["coin_flip_model"] = dict(
        rows=coin,
        ours_margin_db=res["ours_40m_reference"]["h1_over_h2_db"],
        model_ko=("박자를 정하는 것은 «1× 봉우리가 2× 봉우리보다 큰가» 하나뿐이다. "
                  "여유폭(1×−2×)이 정규분포라 보고 P(여유<0) 을 예측해 실측 오답률과 "
                  "견준다. 맞으면 «시드마다 답이 다른» 것이 잡음 위 동전던지기라는 뜻이다."),
        caveat_ko="⚠ 시드가 3~8 판뿐이라 관측 오답률의 표준오차가 0.17~0.29 다.")

    # ── 8. el 0 — 이미 답이 나와 있는 원장을 가리킨다 ────────────────────────
    lb = json.load(open(f"{ROOT}/outputs/verify_elevation_lensB_el0.json"))
    res["el0_probe"]["already_solved_in_ledger"] = dict(
        ledger="outputs/verify_elevation_lensB_el0.json",
        mechanism_ko=("⭐el 0 의 거대한 상수는 **카메라 렌즈판 정반사 3 벌**이다. "
                      "4,096 자세 복소평균이 3·λ/(4πL)(L = 2·(10 − 0.17430) m)와 "
                      "진폭 상대오차 3.4e-5 · 위상오차 0.00048 rad 로 맞는다."),
        keys=dict(
            observed_mean_abs=lb["A_mechanism_CONFIRMED_harder"]["observed_mean_E"]["abs"],
            predicted_abs=lb["A_mechanism_CONFIRMED_harder"]["predicted_three_copies"]["abs"],
            abs_rel_err=lb["A_mechanism_CONFIRMED_harder"]["match"]["abs_rel_err"],
            phase_err_rad=lb["A_mechanism_CONFIRMED_harder"]["match"]["phase_err_rad"],
            sigma_eff_three_copies_m2=lb["D_headline_magnitude_is_soft"]["sionna_sigma_eff_m2"]["three_copies"],
            overestimate_db_range=[
                lb["D_headline_magnitude_is_soft"]["overestimate_db"]["vs_all_camera_planes"]["three"],
                lb["D_headline_magnitude_is_soft"]["overestimate_db"]["vs_single_plate"]["three"]],
            facets_normal_to_los=lb["C_four_side_claims_that_are_WRONG"]["C3_other_elevations_do_have_normal_facets"]["measured_facets_normal_to_los_within_0p05deg"],
            flip_threshold_dc_over_residual_db=[60, 65],
            el0_dc_over_residual_db=lb["B_pedestal_is_necessary_and_sufficient"]["dose_response"]["1.0"]["dc_over_residual_db"]),
        why_budget_cannot_fix_it_ko=(
            "⭐⭐면적이 Sionna 정반사 진폭식에 **안 들어간다**(outputs/rt_no_rcs_verify.json "
            "A_plate: 판 한 변 0.2 → 4 m 로 20 배 키워도 ratio_db 가 −7.9134 로 소수 4 자리까지 "
            "같다). 즉 이 오차는 **표본 부족이 아니라 식의 성질**이다. 그래서 광선을 "
            "11.1 M → 250 M 로 22.5 배 늘려도 el 0 레벨이 0.003 dB 밖에 안 움직인다 — "
            "이 원장이 직접 재서 확인했다."))

    # ── 9. ⭐판정 ────────────────────────────────────────────────────────────
    res["verdicts"] = {
        "headline_ko": (
            "⭐**엔진을 고친 게 아니다. 자세마다 표적을 맞히는 광선을 «0~8 개» 에서 "
            "«168 개» 로 산 것이다** — 표본을 샀지 물리를 산 게 아니다."),
        "q_40억발이_더_나은가": {
            "answer": "조건부 예 — 축에 따라 갈린다",
            "improves_ko": [
                "경로 수 0 → 168 개/자세 (1 M 은 자세 전부 0 경로)",
                "레벨 +13.0 dB (178 M −157.62 → 4,000 M −144.61, 평균)",
                "대역밖 비율 2.52 % → 0.13 % (약 20 배). ⭐우리 커널 0.18 % 보다도 낮다 (⚠ 우리 커널 열은 4,096 자세라 주기도 칸이 4 배 촘촘하다 — 같은 정의지만 같은 분해능은 아니다)",
                "시드 간 레벨 표준편차 4.156 → 1.833 dB (원장 raybudget_seed_ladder)",
                "박자 다수결: 178 M 은 다수가 2 배(오답) · 4,000 M 은 다수가 1 배(정답)"],
            "does_not_improve_ko": [
                "⭐회전당 첨두 3.91 개로 178 M 부터 4,000 M 까지 **평평**하다(물리는 2, 우리 커널 1.93)",
                "⭐1×−2× 여유폭 평균 −1.88 → +2.14 dB 인데 시드 산포가 4.6~5.3 dB 라 "
                "차이가 잡음 안이다(t ≈ 1.6). 우리 커널은 +7.36 dB",
                "판마다의 박자는 여전히 8 판 중 3 판이 2 배로 읽힌다",
                "⭐경로 수가 광선에 **선형**으로 계속 는다(마지막 계단 광선 ×1.40 → 경로 ×1.45). "
                "포화가 안 왔다 = 더 부어도 끝이 안 보인다",
                "el 0 의 27~58 dB σ 과대는 광선 22.5 배에 **0.003 dB** 만 움직인다"],
            "in_band_caveat_ko": (
                "⚠ 4,000 M 의 대역밖이 낮은 것을 «깨끗해졌다» 로만 읽으면 안 된다. "
                "같은 판의 **대역안** 몫도 0.19 % 로 우리 커널 0.66 % 의 3.5 분의 1 이다 — "
                "잡음이 줄면서 신호도 같이 얇아졌다.")},
        "q_수렴하는가": {
            "answer": "아니다 — 4,000 M 은 수렴점이 아니다",
            "criterion_ko": ("«이웃 계단의 차이가 그 계단의 시드 간 산포보다 작은가» 로 판정한다. "
                             "작으면 남은 편향이 어차피 못 지우는 잡음 아래라 «충분» 이다."),
            "evidence_ko": [
                "레벨: 2,848 → 4,000 M (광선 ×1.40) 에서 +3.63 dB 인데 4,000 M 의 시드 sd 는 "
                "1.83 dB 다. 차이가 산포의 2 배 → 아직 오르는 중. "
                "(⚠ 차이의 표준오차 1.52 dB, t = 2.38, 2,848 M 은 시드 3 판뿐이라 **단정 못 한다**)",
                "⭐⭐경로 수 log-log 기울기가 64 M~4,000 M 구간에서 **0.998**(시드 평균) · "
                "1.034(중앙값)다 — 정확히 1 이다. 광선 하나가 경로 하나를 그대로 더 준다 "
                "(×2.78→×2.63 · ×4.0→×3.48 · ×4.0→×4.68 · ×1.40→×1.45). "
                "포화의 조짐이 **하나도** 없다",
                "회전당 첨두는 178 M 부터 3.91 로 굳어 물리값 2 로 안 간다 — "
                "이건 예산으로 안 줄어드는 **바닥**이다"],
            "what_would_convergence_look_like_ko": (
                "광선을 배로 늘렸을 때 (a) 경로 수 증가율이 1 보다 확실히 작아지고 "
                "(b) 레벨 변화가 시드 sd 아래로 내려가고 (c) 회전당 첨두가 2 로 내려와야 한다. "
                "지금은 셋 다 아니다.")},
        "q_비단조_이유": {
            "answer_ko": (
                "⭐대역밖 비율은 «품질» 이 아니라 «계단짐 ÷ 총전력» 이다. 양 끝이 낮은 이유가 "
                "서로 다르다 — 왼쪽은 **신호가 아예 없어서**(경로 0~1 개면 열이 상수라 "
                "부술 게 없다), 오른쪽은 **합이 매끄러워져서**다. 그 사이에 경로가 "
                "몇 개씩 켜졌다 꺼졌다 하는 구간이 있고 거기서 최대가 된다."),
            "numbers_ko": [
                "1 M: 자세 100 % 가 0 경로 → 정의 불가",
                "4 M: 경로 수가 **고정**(cv = 0)이라 열이 거의 상수 → 대역밖 0.33 %, "
                "그런데 대역안도 0.48 % 로 신호가 없다",
                "16 M: 자세 90.5 % 가 0 경로 → 열에 0 이 박혀 계단이 최대 → 7.97 %",
                "64~712 M: 경로 2~26 개, 자세 간 상대 걸음 e_step_rel 0.051→0.133 으로 최대 → "
                "대역밖 1.56~2.80 %",
                "2,848~4,000 M: 경로 116~168 개, e_step_rel 0.044→0.030 → 0.25 → 0.13 %  (전부 시드 평균)"],
            "reproduces_main_session_ko": (
                "⭐이 원장이 메인 세션 수치를 **재현했다**. 시드 평균으로 4 M 0.333 / "
                "64 M 1.557 / 178 M 2.518 / 712 M 2.798 / 2,848 M 0.255 / 4,000 M 0.128 % — "
                "메인 세션이 말한 0.32 / 1.53 / 2.57 / 2.74 / 0.25 / 0.10 과 0.03 pp 안에서 맞는다. "
                "⇒ «비단조» 는 사실이다.")},
        "q_기전_가설검사": {
            "hypothesis_ko": ("경로가 몇 개뿐이면 자세마다 «어느 면이 잡히나» 가 홱 바뀌어 "
                              "가짜 첨두가 생기고 그게 주기를 반으로 쪼갠다"),
            "verdict": "REFUTED at ≥178 M rays, partially supported below",
            "why_ko": [
                "⭐**경로 개수 시계열이 2 배로 안 흔들린다.** 178 M·712 M·2,848 M·4,000 M 의 "
                "**모든 시드**에서 npaths(t) 의 최강선이 127.45 Hz(= 우리 격자에서 126.67 Hz "
                "의 가장 가까운 칸)이고, 2× 성분은 1× 보다 7~17 dB 작다. 개수는 조용하다",
                "그런데 **장(場)** 의 대역 에너지는 같은 판에서 253 Hz 로 읽힌다 ⇒ "
                "2 배 읽기는 «개수의 깜빡임» 이 아니라 **복소 합** 안에서 생긴다",
                "64 M 이하에서는 반대다 — npaths(t) 최강선이 252.5 / 379.96 Hz 로 2×·3× 다. "
                "즉 **가설은 굶은 구간에서만 맞는다**",
                "|E| 와 경로 수의 상관도 0.30(64 M) → 0.09(178 M) → −0.03(4,000 M) 로 사라진다"],
            "replacement_ko": (
                "⭐대신 맞는 설명: **1× 봉우리와 2× 봉우리의 키가 거의 같아서 어느 쪽이 이기나가 "
                "동전던지기다.** 여유폭 평균/표준편차로 P(여유<0) 을 계산하면 178 M 0.66 · "
                "4,000 M 0.344 인데 실측 오답률은 0.714 · 0.375 다(시드 7·8 판). "
                "⚠ 시드 3 판짜리 계단(64 M·712 M·2,848 M)에서는 이 예측이 안 맞는다 — "
                "표본이 모자란다."),
            "not_tested_ko": (
                "⚠ «왜 2× 가 그렇게 큰가» 는 **안 풀었다**. 로터 4 개가 rpm 이 조금씩 달라 "
                "플래시 열이 4 개 섞이는데, 광선 집합이 그중 일부만 잡으면 회전당 4 번으로 "
                "읽힐 수 있다 — 그럴듯하지만 **검증 안 했다**. 1,024 자세(52 ms)로는 "
                "로터 간 0.56 Hz 차이를 분해 못 한다(분해능 ≈ 20 Hz).")},
        "q_비용": {
            "retraction_ref": "docs/RETRACTION_LOG.md §R26 — «PathSolver 가 더 싸다» 는 철회됐다",
            "table_ko": [
                "우리 커널 (거리 무관): 3 m 0.601 · 15 m 0.512 · 40 m 0.635 s/자세",
                "PathSolver 40 m: 1 M 0.383 · 4 M 0.347 · 16 M 0.470 · 64 M 0.597 · "
                "178 M 0.419 · 712 M 1.031 · 2,848 M 1.480 · 4,000 M 3.260 s/자세 (시드 중앙값)"],
            "crossover_ko": ("⭐교차점은 **64~712 M 사이**다. 그 아래면 PathSolver 가 싸고 "
                             "그 위면 우리 커널이 싸다. 4,000 M 에서는 PathSolver 가 "
                             "우리 커널의 **5.1 배** 비싸다(3.260 ÷ 0.635)."),
            "caveat_ko": ("⚠⚠ 이 초 수는 전부 **벽시계**이고 GPU 를 남과 나눠 썼다. "
                          "같은 예산 안에서도 시드마다 sd 가 0.007~1.42 s 다. "
                          "⚠ 우리 커널 값은 4,096 자세 CPU 초이고 PathSolver 는 GPU 다 — "
                          "«같은 하드웨어 비교» 가 아니다. 이 표는 **우리 워크플로에서 "
                          "실제로 기다린 시간**이지 알고리즘 복잡도 비교가 아니다.")},
        "q_시드_대_예산": {
            "answer_ko": "⭐축에 따라 다르다. 무조건문 금지.",
            "level_ko": ("**레벨은 시드가 이긴다.** 같은 벽시계(4,000 M 한 판 = 178 M 7.79 판)면 "
                         "178 M 7.79 판의 평균은 sd 4.156/√7.79 = **1.489 dB** 이고 "
                         "4,000 M 한 판은 **1.833 dB** 다. 광선 총량으로 맞추면(22.5 판) "
                         "0.877 dB 로 더 벌어진다."),
            "beat_ko": ("**박자는 예산이 이긴다.** 박자는 평균이 안 되고 투표해야 하는데, "
                        "178 M 은 7 판 중 5 판이 2 배(다수가 **오답**)이고 4,000 M 은 "
                        "8 판 중 5 판이 1 배(다수가 **정답**)다. 판을 아무리 늘려도 "
                        "다수가 틀리면 같이 틀린다."),
            "r23_link_ko": ("R23 의 «관측/i.i.d. = 23.4~31.2 배» 는 **한 판 안에서 자세를 "
                            "평균해도 시드 편향이 안 지워진다** 는 뜻이지, 시드를 여러 판 "
                            "도는 것이 무의미하다는 뜻이 아니다. 시드끼리는 독립 추첨이므로 "
                            "판을 평균하면 레벨은 √K 로 준다 — 위 숫자가 그것이다.")},
        "q_el0": {
            "answer": "이미 풀려 있다 — 카메라 렌즈판 정반사 3 벌(원장 verify_elevation_lensB_el0.json)",
            "my_independent_checks_ko": [
                "⭐11.1 M 과 250 M 의 레벨이 **0.003 dB** 차이다(−59.6543 vs −59.6570). "
                "다른 6 앙각은 1.48~12.55 dB 움직인다 ⇒ el 0 은 표본 문제가 아니다",
                "⭐4,096 자세 내내 |E| 의 최대/최소 비가 **0.00 dB**, 상대 표준편차 4e-5, "
                "위상 폭 **0.02°** — 로터가 안 보인다(우리 커널은 같은 자리에서 "
                "5.44 dB · 10.7 % · 40.6°)",
                "날개끝 대역 몫이 0.0000 %(11.1 M) · 0.0003 %(250 M) 다. 우리 커널은 2.76 % ⇒ "
                "376.73 Hz · 50.27 Hz 라는 «박자» 는 상대 1e-5 짜리 먼지에 맞춘 값이고 "
                "**아무것도 안 재고 있다**"],
            "root_cause_ko": ("⭐⭐**면적이 Sionna 정반사 진폭식에 안 들어간다.** "
                              "outputs/rt_no_rcs_verify.json 의 A_plate 는 판 한 변을 "
                              "0.2 → 4 m 로 20 배 키워도 ratio_db 가 −7.913447 ~ −7.913449 로 "
                              "**소수 다섯 자리까지 같다**. 그래서 1.56e-3 m² 렌즈판이 "
                              "무한 거울처럼 되돌아오고 σ_eff 가 2,927 m² 가 된다"),
            "why_rays_cannot_fix_ko": ("표본 부족이 아니라 **식의 성질**이므로 광선으로는 "
                                       "절대 안 고쳐진다. 이것이 이 라운드 전체의 요약이다 — "
                                       "광선은 **표본**을 사지 **물리**를 못 산다."),
            "not_measure_zero_ko": ("⚠ «각도 하나의 우연» 이 아니다. 원장 C3 이 잰 «시선에 "
                                    "0.05° 안으로 수직인 면 수» 는 el 0 에서 106 개, "
                                    "el −90 에서 688 개다(−90 은 셸 가림이 막았을 뿐이다). "
                                    "정렬이 걸리는 각도가 곧 표적의 대칭축 = 정면·직하방 = "
                                    "**누구나 고르는 각도**다.")}}

    # ── 저장 ─────────────────────────────────────────────────────────────────
    json.dump(res, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    figure(res)
    print(f"✅ {OUT_JSON}")

    # 화면 표
    print("\n═══ 40 m 사다리 ═══")
    print(f"{'광선[M]':>9} {'시드':>4} {'경로':>6} {'경로CV':>7} {'0경로%':>7} "
          f"{'레벨dB':>9} {'1x/총':>7} {'|박자오차|%':>10} {'1x−2x dB':>9} "
          f"{'첨두/회전':>9} {'대역밖%':>8} {'s/자세':>8}")
    for r in rungs:
        print(f"{r['spp_m']:>9.0f} {r['n_seeds']:>4d} "
              f"{r['npaths_median']['median']:>6.1f} "
              f"{(r['npaths_cv']['median'] or 0):>7.3f} "
              f"{100*(r['npaths_zero_frac']['median'] or 0):>7.1f} "
              f"{r['level_db']['median']:>9.2f} "
              f"{r['n_beat_1x']}/{r['n_seeds']:<5} "
              f"{(r['beat_abs_rel_err_pct']['median'] or 0):>10.2f} "
              f"{(r['h1_over_h2_db']['median'] if r['h1_over_h2_db']['median'] is not None else float('nan')):>9.2f} "
              f"{(r['peaks_per_rev']['median'] or 0):>9.2f} "
              f"{(r['oob_frac_pct']['median'] or 0):>8.3f} "
              f"{(r['sec_per_pose']['median'] or 0):>8.3f}")

    print("\n═══ 10 m 앙각 ═══")
    print(f"{'엔진':>18} {'el':>5} {'경로':>6} {'레벨dB':>9} {'박자':>8} "
          f"{'첨두/회전':>9} {'대역밖%':>8} {'DC지배':>7} {'변조깊이':>8}")
    for r in elev:
        print(f"{r['engine']:>18} {r['el_deg']:>5.0f} "
              f"{(r['npaths_median'] if r['npaths_median'] is not None else float('nan')):>6.1f} "
              f"{r['level_db']:>9.2f} "
              f"{(r['beat_hz'] if r['beat_hz'] is not None else float('nan')):>8.2f} "
              f"{(r['peaks_per_rev'] if r['peaks_per_rev'] is not None else float('nan')):>9.2f} "
              f"{(r['oob_frac_pct'] if r['oob_frac_pct'] is not None else float('nan')):>8.3f} "
              f"{(r['dc_dominance'] if r['dc_dominance'] is not None else float('nan')):>7.3f} "
              f"{(r['mod_depth'] if r['mod_depth'] is not None else float('nan')):>8.3f}")


if __name__ == "__main__":
    main()
