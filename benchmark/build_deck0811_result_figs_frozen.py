# -*- coding: utf-8 -*-
"""build_deck0811_result_figs_frozen.py — 0811 덱 결과 그림 둘의 **얼린 격자 판**.

원본 build_deck0811_result_figs.py 와 이야기·배치·지표 정의가 **같다**. 딱 하나만 다르다 —
우리 팔의 슬로타임 시계열을 «생산» 대신 **«격자를 얼린»** 것으로 바꾼다.

⭐왜 (2026-08-10, 커밋 5f088fa 뒤)
  SBR 슬로타임 스펙트럼의 날개끝 밖 광대역 바닥은 이산화 잡음이 아니었다. 원인은
  **자세마다 광선 격자를 다시 정의하는 것**이다(격자 중심 5.85 rad p-p 흔들림 ·
  격자 수 40 % 정수 튐 · 히트집합 17 % 흔들림). 가산성 정리 검사가 결정적이었다 —
  격자를 얼리면 잔차가 1e-15(기계정밀도)이고, 움직이는 격자는 O(1) 이다.
  sbr_grid_convergence.json 의 판정: λ/12 에서 얼리면 대역밖 비율이 9.3 dB 내려가고,
  얼린 팔만 예측대로 d² 로 수렴한다(기울기 -2.09, R²=0.987).

⛔계산을 새로 하지 않는다. 얼린 시계열은 이미 디스크에 있다 —
   outputs/sbr_grid_convergence.npz : E_froz_div12
   같은 원장의 E_prod_div12 는 report07_three_engines.npz['sbr'] 와 **4096/4096 비트동일**이고
   (regression_div12_vs_ledger), 아래에서 그 사실을 빌드마다 다시 확인한다.
   즉 이 그림이 그리는 것은 원본 그림이 그리던 그 시계열의 **얼린 쌍둥이**다.

⛔원본 산출물(deck0811_r1.png · deck0811_r2.png · deck0811_beat_check.json)은 안 건드린다.
   여기서 내는 것은 전부 `_frozen` 접미사다.

⚠지표 정의는 원본과 **한 글자도 안 바꿨다** — 바꾸면 두 판의 숫자를 비교할 수 없다.
  (원본의 frac_power_beyond_ftip 과는 다른 지표다. 그쪽은 포락 평활 커널이 동체 DC 를
   분모로 새게 해서 «동체 DC 대비» 가 되어 버렸고, 이 그림은 그 지표를 안 쓴다.)

읽는 것: outputs/report07_three_engine_ranges.{npz,json}   (Sionna, 거리별, 기선 0)
         outputs/report07_three_engines.{npz,json}         (메타 · 생산 팔 대조용)
         outputs/sbr_grid_convergence.{npz,json}           (⭐얼린 우리 팔)
         outputs/report07_ray_budget_test.json             (40 m 광선 사다리)
         outputs/report07_sionna_ranges.json               (40 m 빈 자세 교차확인)
쓰는 것: outputs/figures/deck0811_r1_frozen.{png,pdf}
         outputs/figures/deck0811_r2_frozen.{png,pdf}
         outputs/deck0811_beat_check_frozen.json

    python benchmark/build_deck0811_result_figs_frozen.py
"""
from __future__ import annotations

import json
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import flash_spec, auto_periods, draw, caption          # noqa: E402

FIG = os.path.join(ROOT, "outputs", "figures")

# ── 원장 ────────────────────────────────────────────────────────────────────
RJ = json.load(open(f"{ROOT}/outputs/report07_three_engine_ranges.json"))
RZ = np.load(f"{ROOT}/outputs/report07_three_engine_ranges.npz")
OJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))
OZ = np.load(f"{ROOT}/outputs/report07_three_engines.npz")
GJ = json.load(open(f"{ROOT}/outputs/sbr_grid_convergence.json"))
GZ = np.load(f"{ROOT}/outputs/sbr_grid_convergence.npz")
BJ = json.load(open(f"{ROOT}/outputs/report07_ray_budget_test.json"))
SJ = json.load(open(f"{ROOT}/outputs/report07_sionna_ranges.json"))

M = RJ["_meta"]
PRF, FFL, FTIP = float(M["prf_hz"]), float(M["f_flash_hz"]), float(M["f_tip_hz"])
NAME, FC = M["name"], float(M["fc_hz"])
AZ, EL = float(M["az_deg"]), float(M["el_deg"])
N = int(M["n"])
PERIODS = auto_periods(PRF, FFL)

RPM0 = float(np.mean(OJ["_meta"]["rpm_per_rotor"]))
BLADES = round(FFL * 60.0 / RPM0)
assert abs(BLADES * RPM0 / 60.0 - FFL) < 1e-6, "f_flash 가 날개수 x rpm/60 과 안 맞는다"

# 60 ms 확대 창 — 원본과 같은 자리(시작 과도를 20 ms 피한다)
ZOOM_MS = 60.0
N0 = int(round(0.020 * PRF))
NZ = int(round(ZOOM_MS / 1000.0 * PRF))

E_SIONNA = np.asarray(RZ["R3/E"], complex)          # ⭐기선 0 — 기하가 맞는 판
E_PROD = np.asarray(GZ["E_prod_div12"], complex)    # 생산 팔(대조용, 그리지 않는다)
E_OURS = np.asarray(GZ["E_froz_div12"], complex)    # ⭐얼린 격자 — 이 판의 우리 팔

# ── ⭐혈통 검사 — 얼린 쌍둥이가 정말 그 시계열의 쌍둥이인가 ────────────────
_LEDGER_SBR = np.asarray(OZ["sbr"], complex)
_N_SAME = int((E_PROD == _LEDGER_SBR).sum())
if E_PROD.shape != _LEDGER_SBR.shape or _N_SAME != E_PROD.size:
    raise SystemExit(f"❌ 생산 div12 가 report07 원장 sbr 열과 다르다 "
                     f"({_N_SAME}/{E_PROD.size} 일치). 얼린 팔을 그 쌍둥이라 부를 수 없다")
if E_OURS.shape != _LEDGER_SBR.shape:
    raise SystemExit("❌ 얼린 시계열 길이가 원장과 다르다")
# ⭐2026-08-10 사용자 지시 — «frozen ray grid 가 뭐야? 제목에 꼭 써놔야 하니?»
#   맞는 지적이다. 이것은 우리가 만든 전문용어이고 청중은 모른다. **그림 제목에서 뺀다.**
#   대신 사실 자체는 캡션 한 줄과 발표 노트가 진다(어디에도 안 적으면 그건 숨기는 것이다).
FROZ_LABEL = ""

# ⭐40 m 판 — 사용자: «더 먼 거리 40 m 이런 거에 대한 그림 비교는 왜 없앤 거야?»
#   없앤 게 아니라 계산한 적이 없었다. benchmark/report07_range40.py 가 규칙값 178M 광선으로
#   자세 4,096 개를 **시드 두 개**로 냈다. 시드를 둘 돌린 이유는 8 m 에서 데였기 때문이다.
#   ⭐그리고 실제로 갈렸다 — 레벨은 2.6 dB 안이지만 **박자 최강선이 시드마다 다르다**.
R40J = (json.load(open(f"{ROOT}/outputs/report07_range40.json"))
        if os.path.exists(f"{ROOT}/outputs/report07_range40.json") else None)
R40Z = (np.load(f"{ROOT}/outputs/report07_range40.npz")
        if os.path.exists(f"{ROOT}/outputs/report07_range40.npz") else None)

C_SIONNA, C_OURS, C_PRED = "#c2570a", "#1f5fa8", "#222222"
NAME_SIONNA = "Sionna PathSolver"
NAME_OURS = "Ours (SBR + PO)"

FS = 13.0
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1.5, "ytick.labelsize": FS - 1.5,
    "axes.linewidth": 1.1, "lines.linewidth": 2.0,
    "figure.dpi": 200, "savefig.dpi": 200, "font.family": "DejaVu Sans",
})


# ── 박자 지표 — ⭐정의는 원본과 한 글자도 다르지 않다 ───────────────────────
BAND_LO, BAND_HI = 0.35, 1.00      # 날개끝 대역 (f_tip 배수)
PAD = 64                           # 선 스펙트럼 제로패딩
SEARCH = (40.0, 400.0)             # 최대선을 찾는 구간 [Hz]


def tip_band_line(E):
    """날개끝 대역 에너지의 **선 스펙트럼**과 그 최대선(원본과 동일한 정의)."""
    f, t, S, nper = flash_spec(E, PRF, FFL, PERIODS)
    band = (np.abs(f) >= BAND_LO * FTIP) & (np.abs(f) <= BAND_HI * FTIP)
    g = (S[band] ** 2).sum(axis=0)
    n, dt = len(g), float(t[1] - t[0])
    x = (g - g.mean()) * np.hanning(n)
    X = np.abs(np.fft.rfft(x, int(PAD * n)))
    fr = np.fft.rfftfreq(int(PAD * n), dt)
    sel = (fr >= SEARCH[0]) & (fr <= SEARCH[1])
    i = np.where(sel)[0][np.argmax(X[sel])]
    a, b, c = X[i - 1], X[i], X[i + 1]
    den = a - 2 * b + c
    fpk = fr[i] + (0.5 * (a - c) / den if den else 0.0) * (fr[1] - fr[0])
    return fr, X / X[sel].max(), float(fpk), nper, n, float(1.0 / (n * dt))


def dev_pct(fpk):
    return (fpk - FFL) / FFL * 100.0


def robustness():
    """⭐96개 분석 변형 포락 — 원본과 같은 스윕, 우리 팔만 얼린 것으로 바뀐다."""
    out = {"ours": [], "sionna": [], "sionna_off_fundamental": 0,
           "ours_off_fundamental": 0, "n_variants": 0}
    for lo, hi in [(0.30, 1.00), (0.35, 1.00), (0.40, 1.00),
                   (0.35, 1.10), (0.50, 1.00), (0.35, 0.90)]:
        for pad in (16, 64):
            for power in (True, False):
                for per in (None, PERIODS):
                    for win in (True, False):
                        out["n_variants"] += 1
                        for key, E in (("sionna", E_SIONNA), ("ours", E_OURS)):
                            f, t, S, _ = flash_spec(E, PRF, FFL, per)
                            b = (np.abs(f) >= lo * FTIP) & (np.abs(f) <= hi * FTIP)
                            g = (S[b] ** (2 if power else 1)).sum(axis=0)
                            n, dt = len(g), float(t[1] - t[0])
                            x = g - g.mean()
                            if win:
                                x = x * np.hanning(n)
                            X = np.abs(np.fft.rfft(x, int(pad * n)))
                            fr = np.fft.rfftfreq(int(pad * n), dt)
                            s = (fr >= SEARCH[0]) & (fr <= SEARCH[1])
                            i = np.where(s)[0][np.argmax(X[s])]
                            a, bb, c = X[i - 1], X[i], X[i + 1]
                            den = a - 2 * bb + c
                            fp = fr[i] + (0.5 * (a - c) / den if den else 0.0) * (fr[1] - fr[0])
                            d = dev_pct(fp)
                            if abs(d) > 5.0:
                                out[f"{key}_off_fundamental"] += 1
                                continue
                            out[key].append(d)
    return out


# ═══ r1 — 둘이 같은 박자를 낸다 ═════════════════════════════════════════════
def build_r1(beat):
    fig = plt.figure(figsize=(12.2, 7.1))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.32, 1.0], width_ratios=[1, 1, 0.035],
                          wspace=0.10, hspace=0.46,
                          left=0.070, right=0.928, top=0.900, bottom=0.200)

    cap0, m = "", None
    for c, (E, title) in enumerate((
            (E_SIONNA, NAME_SIONNA),
            (E_OURS, NAME_OURS))):
        seg = E[N0:N0 + NZ]
        ax = fig.add_subplot(gs[0, c])
        f, t, S, nper = flash_spec(seg, PRF, FFL, PERIODS)
        m = draw(ax, t + N0 / PRF, f, S, FTIP)
        if c == 0:
            cap0 = caption(PRF, FFL, nper, len(t))
        else:
            # ⭐두 판을 한눈에 구별할 표시. 짧게, 맵 안쪽 왼쪽 위에.
            ax.text(0.014, 0.955, "", transform=ax.transAxes,
                    ha="left", va="top", fontsize=FS - 4, color=C_OURS,
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.24", fc="white", ec=C_OURS,
                              lw=1.0, alpha=0.90))
        ax.set_title(title, fontsize=FS + 1, fontweight="bold",
                     color=(C_SIONNA if c == 0 else C_OURS), pad=7)
        ax.set_xlabel("Time [ms]")
        if c == 0:
            ax.set_ylabel("Doppler [Hz]")
        else:
            plt.setp(ax.get_yticklabels(), visible=False)

    cax = fig.add_subplot(gs[0, 2])
    cb = fig.colorbar(m, cax=cax)
    cb.set_label("Each map to its own peak [dB]", fontsize=FS - 2.5)
    cb.ax.tick_params(labelsize=FS - 3)

    # ── 박자 패널 ───────────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 0:2])
    for key, col, base in ((("sionna"), C_SIONNA, NAME_SIONNA),
                           (("ours"), C_OURS, NAME_OURS)):
        fr, X, fpk = beat[key]["fr"], beat[key]["X"], beat[key]["peak_hz"]
        s = fr <= 420
        # ⭐«어느 조화가 최강인가» 는 1x 와 2x 의 **여유**가 정한다. 그 여유가 작으면
        #   답이 잡음으로 뒤집힌다 — Sionna 팔은 여유가 1 dB 대라 시드만 바꿔도 뒤집히고,
        #   우리 팔은 7 dB 대라 안 뒤집힌다. 그래서 여유를 범례에 함께 적는다.
        def _line_db(f0):
            w = (fr > f0 - 6) & (fr < f0 + 6)
            return 20 * np.log10(X[w].max() / X.max() + 1e-30) if w.any() else -99.0
        margin = _line_db(FFL) - _line_db(2 * FFL)
        lab = (f"{base}    {fpk:.2f} Hz    off by {dev_pct(fpk):+.2f} %"
               f"    first line clears the second by {margin:+.1f} dB")
        ax.plot(fr[s], 20 * np.log10(X[s] + 1e-6), color=col, lw=2.2, label=lab)
    ax.plot([], [], color=C_PRED, ls="--", lw=1.5,
            label=f"Kinematic prediction    {FFL:.2f} Hz    "
                  f"{BLADES:.0f} blades at {RPM0:.0f} rpm")

    for h, nm in ((1, "flash rate"), (2, "2x"), (3, "3x")):
        ax.axvline(h * FFL, color=C_PRED, ls="--", lw=1.5 if h == 1 else 1.0,
                   alpha=0.85 if h == 1 else 0.42, zorder=0)
        # ⭐축 밖(위)에 두면 패널 제목과 겹친다 — 안쪽 위에 붙인다.
        ax.annotate(nm, xy=(h * FFL, 0.965), xycoords=("data", "axes fraction"),
                    ha="center", va="top", fontsize=FS - 3.5, color=C_PRED,
                    alpha=0.85)

    ax.set_xlim(0, 420)
    ax.set_ylim(-46, 6)
    ax.set_yticks([-40, -30, -20, -10, 0])
    ax.set_title(f"Blade tip band energy, {BAND_LO*FTIP:.0f} to {BAND_HI*FTIP:.0f} Hz, "
                 "how fast it rises and falls", fontsize=FS - 0.5, pad=10)
    ax.set_xlabel("Modulation rate [Hz]")
    ax.set_ylabel("Line level [dB]")
    # ⭐사용자 지적 — 범례가 2x·3x 고조파 봉우리를 가리고 있었다(upper right 가 정확히
    #   그 자리다). 축 **바깥 아래**로 빼서 곡선을 하나도 안 가리게 한다.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=1,
              fontsize=FS - 3.5, framealpha=0.0,
              title="Strongest line in the blade tip band", title_fontsize=FS - 3.5,
              borderpad=0.4, labelspacing=0.34, handlelength=2.4)
    ax.grid(alpha=0.22)

    fig.suptitle(f"{NAME} hovering at {FC/1e9:.1f} GHz, belly view "
                 f"(az {AZ:.0f} deg, el {EL:.0f} deg), R = 3 m. "
                 f"The same {ZOOM_MS:.0f} ms window through two engines.",
                 fontsize=FS + 1.5, y=0.972)

    # ⭐사용자 지시 — 그림 하단의 긴 캡션을 삭제했다. 설명은 발표 노트가 진다.
    #   캡션 자리가 비면서 아래 여백이 생기므로 축 밖 범례가 겹치지 않는다.

    for ext in ("png", "pdf"):
        fig.savefig(f"{FIG}/deck0811_r1_frozen.{ext}", bbox_inches="tight",
                    facecolor="white")
    plt.close(fig)


# ═══ r2 — 거리에 대한 성질이 반대다 ═════════════════════════════════════════
def build_r2():
    # ⭐8 m 칸을 뺐다 (2026-08-10). 원인이 확정됐기 때문이다 — 그 칸의 «3 배 조화» 와
    #   «레벨이 안 떨어짐» 은 거리의 성질이 아니라 **seed=1 몬테카를로 추첨 한 장**의 성질이다.
    #   드론에서 움직이는 것은 로터뿐이라 동체 경로 집합이 4,096 자세 내내 비트 동일해서,
    #   기록 전체가 추첨 한 번을 받침대로 깔고 있었다. 시드만 바꾸면 레벨이 18 dB 흔들리고
    #   기본파가 돌아온다(원장 outputs/probe_8m_anomaly.json).
    #   ⇒ 물리가 아니라 난수 한 장을 스크린에 띄우는 것이므로 뺀다. 3 m·15 m 만으로
    #     «거리는 한 엔진에만 비용으로 들어온다» 는 메시지가 그대로 선다.
    # 3 m 한 줄 + 40 m 두 시드. 15 m 는 뺐다 — 40 m 가 «먼 거리» 를 더 잘 말하고,
    # 두 시드가 나란히 있어야 «같은 계산인데 난수만 달라도 답이 갈린다» 가 보인다.
    rows = [("R3", 3.0, None)]
    if R40Z is not None:
        rows += [("R40", 40.0, 1), ("R40", 40.0, 2)]
    else:
        rows += [("R15", 15.0, None)]
    fig = plt.figure(figsize=(14.0, 7.4))
    gs = fig.add_gridspec(3, 5, width_ratios=[1, 1, 0.032, 0.20, 1.30],
                          wspace=0.12, hspace=0.30,
                          left=0.052, right=0.975, top=0.862, bottom=0.225)

    m = None
    for r, (key, rng, seed) in enumerate(rows):
        E_sio = (np.asarray(R40Z[f"S{seed}/E"], complex) if seed
                 else np.asarray(RZ[f"{key}/E"], complex))
        for c, (E, base, col) in enumerate((
                (E_sio, NAME_SIONNA, C_SIONNA),
                (E_OURS, NAME_OURS, C_OURS))):
            seg = E[N0:N0 + NZ]
            ax = fig.add_subplot(gs[r, c])
            f, t, S, _ = flash_spec(seg, PRF, FFL, PERIODS)
            m = draw(ax, t + N0 / PRF, f, S, FTIP)
            if c == 1:                       # 우리 열을 띠로 감싼다
                for sp in ax.spines.values():
                    sp.set_color(C_OURS)
                    sp.set_linewidth(2.2)
            # ⭐뱃지는 «몇 발 쐈나 ↔ 한 번만 계산했다» 대비만 진다. 용어를 안 쓴다.
            spp_m = (R40J["seeds"][str(seed)]["spp"] if seed
                     else RJ["ranges"][key]["spp"]) / 1e6
            # ⭐⭐사용자 지시(두 번째) — «computed once, same array 이런 거 안 넣었으면
            #   좋겠다니까? 좀 그림만 넣어줘». 우리 열에는 **아무 글자도 안 넣는다.**
            #   «한 번만 계산했다» 는 두 줄이 똑같이 생긴 것으로 이미 보이고,
            #   세 줄 다 파란 테두리로 묶여 있다.
            #   Sionna 열은 광선 수만 남긴다 — 그게 이 그림의 «비용» 축이다.
            #   측정된 최강선은 왼쪽 행 이름표로 내렸다(맵 위에 글을 얹지 않는다).
            badge = f"{spp_m:g}M rays" if c == 0 else ""
            if badge:
                ax.text(0.014, 0.94, badge, transform=ax.transAxes,
                        ha="left", va="top", fontsize=FS - 4, color=col,
                        fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.24", fc="white",
                                  ec=col, lw=1.0, alpha=0.90))
            # ⭐부제를 뺐다(사용자: «무슨 never enters kernel 이런 식으로 주저리주저리»).
            #   «다시 푼다 ↔ 한 번만 계산한다» 는 뱃지가 이미 말하고, 그림 자체가 보여준다.
            if r == 0:
                ax.set_title(base, fontsize=FS - 1.5, color=col,
                             fontweight="bold", pad=6)
            if c == 0:
                if seed:
                    bh = R40J["seeds"][str(seed)]["beat_hz"] if R40J else 0.0
                    lab = f"R = {rng:.0f} m\nrun {seed}\n{bh:.0f} Hz"
                else:
                    lab = f"R = {rng:.0f} m"
                ax.set_ylabel(f"{lab}\nDoppler [Hz]", fontsize=FS - 1.5)
            else:
                plt.setp(ax.get_yticklabels(), visible=False)
            if r == 2:
                ax.set_xlabel("Time [ms]", fontsize=FS - 1.5)
            else:
                plt.setp(ax.get_xticklabels(), visible=False)
            ax.tick_params(labelsize=FS - 4)

    cax = fig.add_subplot(gs[:, 2])
    cb = fig.colorbar(m, cax=cax)
    cb.set_label("Each map to its own peak [dB]", fontsize=FS - 3.5)
    cb.ax.tick_params(labelsize=FS - 4)

    # ── 광선 사다리 ─────────────────────────────────────────────────────────
    lad = BJ["ladder"]
    keys = sorted(lad, key=lambda k: lad[k]["spp"])
    spp = [lad[k]["spp"] / 1e6 for k in keys]
    zero = [lad[k]["zero_frac"] * 100.0 for k in keys]
    med = [lad[k]["paths_median"] for k in keys]
    x = np.arange(len(keys))

    ax = fig.add_subplot(gs[:, 4])
    ax.bar(x, zero, width=0.56, color="#b03030", alpha=0.85, zorder=2,
           label="Poses with zero paths [%]")
    for xi, v in zip(x, zero):
        ax.text(xi, v + 2.5, (f"{v:.0f} %" if v > 0 else "0 %"), ha="center",
                va="bottom", fontsize=FS - 1.5, color="#b03030", fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Poses with zero paths [%]", color="#b03030", fontsize=FS - 1)
    ax.tick_params(axis="y", colors="#b03030", labelsize=FS - 2.5)
    rule = BJ["_meta"]["rule_value_spp"] / 1e6
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s:.0f}M" for s in spp], fontsize=FS - 1.5)
    ax.set_xlabel(f"Rays per source at R = 40 m.  "
                  f"Rule value (R / 3)$^2$ x 1M = {rule:.0f}M.", fontsize=FS - 2)
    ax.grid(axis="y", alpha=0.2, zorder=0)

    ax2 = ax.twinx()
    ax2.plot(x, med, marker="o", ms=9, color=C_SIONNA, lw=2.4, zorder=3,
             label="Median paths per pose")
    r3med = RJ["ranges"]["R3"]["paths_median"]
    ax2.axhline(r3med, color=C_PRED, ls="--", lw=1.4, alpha=0.75, zorder=1)
    ax2.text(len(x) - 1, r3med + 0.22, f"same as R = 3 m, {r3med:.0f} paths",
             ha="right", va="bottom", fontsize=FS - 3, color=C_PRED)
    ax2.set_ylim(0, max(med) * 1.55 + 0.5)
    ax2.set_ylabel("Median paths per pose", color=C_SIONNA, fontsize=FS - 1)
    ax2.tick_params(axis="y", colors=C_SIONNA, labelsize=FS - 2.5)

    # ⭐⭐제목을 아예 뺐다 (사용자: «무슨 40m was a budget, not a wall 뭐 어쩌란거야»).
    #   맞는 지적이다 — 그건 제목이 아니라 슬로건이었다. 축 라벨이
    #   «빈 자세 [%]» · «자세당 경로 중앙값» · «R = 40 m 에서 소스당 광선 수» 로
    #   이미 다 말하고 있으므로 제목이 필요 없다.
    ax.set_title("",
                 fontsize=FS, fontweight="bold", pad=8)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", fontsize=FS - 3, framealpha=0.93,
              bbox_to_anchor=(0.5, 0.90))

    fig.suptitle(f"{NAME}, belly view, {FC/1e9:.1f} GHz. Left, one row per range, the "
                 "same 60 ms window. Right, what it costs Sionna to reach 40 m.",
                 fontsize=FS + 1.5, y=0.965)

    seed_note = ""
    if R40J:
        s1, s2 = R40J["seeds"]["1"], R40J["seeds"]["2"]
        seed_note = ("The two 40 m rows are the same computation with a different random "
                     f"seed. The level agrees within "
                     f"{abs(s1['level_db'] - s2['level_db']):.1f} dB and the strongest "
                     f"modulation line does not, at {s1['beat_hz']:.0f} Hz and "
                     f"{s2['beat_hz']:.0f} Hz against a prediction of {FFL:.0f} Hz. "
                     "Our column has no seed in it at all.\n")
    cap = ("Left. Only the Sionna column is solved again at each range, with the ray budget "
           "raised as the target shrinks in solid angle. Our column is computed once and "
           "reused, because a plane wave anchored on the target carries no range at all. "
           "That repetition is the claim, not an accident of plotting. No pose is ray "
           "starved at any range. Maps are normalized to their own peak, so this "
           "compares structure only, never level.\n" + seed_note +
           "Right. At 40 m a starved budget leaves most poses with no path at all, which "
           "looks like a collapse. Raising the ray count alone removes it, and at the rule "
           "value the path count matches the 3 m case. A separate run at the same 32M "
           f"budget gave {SJ['ranges']['R40']['paths_zero_frac']*100:.0f} % empty poses, "
           "close to the 32M bar here. Ledger outputs/report07_ray_budget_test.json, "
           f"{BJ['_meta']['n_poses']} poses per rung, {BJ['_meta']['prf_hz']/1000:g} kHz.")
    cap = "\n".join(textwrap.fill(p, 132) for p in cap.split("\n"))
    fig.text(0.052, 0.155, cap, fontsize=FS - 3.5, color="0.32", va="top")

    for ext in ("png", "pdf"):
        fig.savefig(f"{FIG}/deck0811_r2_frozen.{ext}", bbox_inches="tight",
                    facecolor="white")
    plt.close(fig)


def main():
    beat = {}
    for key, E in (("sionna", E_SIONNA), ("ours", E_OURS)):
        fr, X, fpk, nper, nslot, ray = tip_band_line(E)
        beat[key] = {"fr": fr, "X": X, "peak_hz": fpk, "nper": nper,
                     "slots": nslot, "rayleigh_hz": ray}

    # 참고용 — 생산 팔을 같은 지표로 재서 «판이 바뀌며 숫자가 얼마나 움직였나» 를 남긴다.
    _, _, fpk_prod, _, _, _ = tip_band_line(E_PROD)

    rob = robustness()
    print(f"\n═══ 박자 지표 · 얼린 격자 판 (f_flash 예측 {FFL:.3f} Hz) ═══")
    print(f"  production(ours) 최대선 {fpk_prod:8.3f} Hz  ({dev_pct(fpk_prod):+.3f} %)  ← 옛 판")
    for k in ("sionna", "ours"):
        print(f"  {k:16s} 최대선 {beat[k]['peak_hz']:8.3f} Hz  "
              f"({dev_pct(beat[k]['peak_hz']):+.3f} %)")
    print(f"  강건성 {rob['n_variants']} 변형 — ours |dev| ≤ "
          f"{max(abs(v) for v in rob['ours']):.3f} % · sionna |dev| ≤ "
          f"{max(abs(v) for v in rob['sionna']):.3f} % "
          f"(기본파를 벗어난 변형 ours {rob['ours_off_fundamental']}개 · "
          f"sionna {rob['sionna_off_fundamental']}개)")

    json.dump({
        "_meta": {
            "owner": "build_deck0811_result_figs_frozen.py — 0811 덱 결과 그림의 "
                     "**얼린 격자 판** 박자 지표",
            "why_ko": "우리 팔의 광선 격자를 자세마다 다시 정의하던 것이 대역밖 바닥의 "
                      "지배 원인이었다(sbr_grid_convergence.json). 격자를 얼린 시계열로 "
                      "같은 그림·같은 지표를 다시 낸다. 덱 빌더는 이 파일을 읽는다.",
            "source_npz": {
                "sionna": "report07_three_engine_ranges.npz : R3/E  (기선 0, 진짜 모노스태틱)",
                "ours": "⭐sbr_grid_convergence.npz : E_froz_div12  "
                        "(모든 자세에 같은 ctr0·Rout0·n0 — 얼린 격자)"},
            "provenance_ko": "같은 원장의 E_prod_div12 는 report07_three_engines.npz['sbr'] "
                             f"와 {_N_SAME}/{E_PROD.size} 비트동일임을 이 빌드에서 확인했다. "
                             "즉 얼린 팔은 옛 그림이 그리던 그 시계열의 쌍둥이다.",
            "geometry_note_ko": "⭐report07_three_engines.npz 의 sionna 열(기선 0.20 m)은 "
                                "쓰지 않았다. 그 판으로 재면 최대선이 2·f_flash 로 넘어가 "
                                "예측 대비 +99.6 % 가 나온다.",
            "prf_hz": PRF, "n": N, "record_ms": N / PRF * 1e3,
            "f_flash_hz": FFL, "f_tip_hz": FTIP,
            "rayleigh_hz": beat["ours"]["rayleigh_hz"],
            "metric_ko": f"flash_spec(0.45 주기·{beat['ours']['nper']} 표본) → "
                         f"|f|/f_tip {BAND_LO}~{BAND_HI} 대역 전력 합 g(t) → "
                         f"평균제거·Hann·{PAD}배 제로패딩 rFFT → {SEARCH[0]:.0f}~"
                         f"{SEARCH[1]:.0f} Hz 최대선 · 포물선 보간",
            "metric_unchanged_ko": "⭐지표 정의는 생산 판(deck0811_beat_check.json)과 "
                                   "한 글자도 다르지 않다. 바뀐 것은 입력 시계열뿐이다.",
            "caveat_ko": "포물선 보간은 강한 선 하나의 위치 추정이지 분해능 주장이 아니다 "
                         "(레일리 빈 4.8 Hz)."},
        "prediction_hz": FFL,
        "engines": {k: {"peak_hz": round(beat[k]["peak_hz"], 3),
                        "dev_pct": round(dev_pct(beat[k]["peak_hz"]), 3),
                        "is_band_max": True} for k in ("sionna", "ours")},
        "ours_production_reference": {
            "peak_hz": round(fpk_prod, 3),
            "dev_pct": round(dev_pct(fpk_prod), 3),
            "note_ko": "옛 판(격자를 자세마다 다시 정의)의 같은 지표. 두 판의 차이가 "
                       "«지난주와 숫자가 다른 이유» 다.",
            "shift_hz": round(beat["ours"]["peak_hz"] - fpk_prod, 3)},
        "robustness": {
            "n_variants": rob["n_variants"],
            "swept_ko": "대역 6종 · 패딩 2종 · 전력/진폭 · 조각 0.45|0.60 주기 · 창 유무",
            "ours_abs_dev_max_pct": round(max(abs(v) for v in rob["ours"]), 3),
            "sionna_abs_dev_max_pct": round(max(abs(v) for v in rob["sionna"]), 3),
            "ours_off_fundamental_variants": rob["ours_off_fundamental"],
            "sionna_off_fundamental_variants": rob["sionna_off_fundamental"],
            "note_ko": "생산 판과 같은 스윕이다. 두 팔 모두 기본파를 벗어난 변형 수를 "
                       "따로 센다."},
        "figures": ["outputs/figures/deck0811_r1_frozen.png",
                    "outputs/figures/deck0811_r2_frozen.png"],
    }, open(f"{ROOT}/outputs/deck0811_beat_check_frozen.json", "w"),
        ensure_ascii=False, indent=1)

    build_r1(beat)
    build_r2()
    print("\n  ✅ outputs/figures/deck0811_r1_frozen.png / .pdf")
    print("  ✅ outputs/figures/deck0811_r2_frozen.png / .pdf")
    print("  ✅ outputs/deck0811_beat_check_frozen.json")


if __name__ == "__main__":
    main()
