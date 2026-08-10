# -*- coding: utf-8 -*-
"""
build_deck0811_result_figs.py — 0811 팀미팅 덱의 **결과 그림 둘**.

이 판의 축은 하나다 — **Sionna PathSolver ↔ 우리 SBR+PO**. 그래서 그림도 둘뿐이다.

  r1  «둘이 같은 박자를 낸다»   60 ms 확대 맵 두 장 + 박자 일치를 재는 작은 패널
  r2  «거리에 대한 성질이 반대다»  거리판(3/8/15 m) + 40 m 광선 사다리

⭐ 왜 이렇게 좁혔나 (사용자 지시 2026-08-10)
  · 두 열만 — 대조군(가림 끈 PO)은 **뺐다**. "둘 중 하나만 넣으면 안 되니, 뭔 차이인지도
    잘 모르겠고." 대조군은 세 번째 축이라 이 판의 이야기가 아니다.
  · 208 ms 전체판은 **뺐다** — 플래시가 눌려 붙어 안 읽힌다. 확대판만 남긴다.
  · 비용 곡선(R²)은 **뺐다** — 한 장에 패널 셋은 안 읽힌다(v5 10장의 실패). 노트로 간다.

⚠⚠ **기하 주의 — 이 그림의 가장 중요한 선택**
  report07_three_engines.npz 의 `sionna` 열은 **기선 0.20 m 준-모노(3.8°)** 로 돈 낡은 판이다
  (스크립트 수정 07:08 > 원장 생성 06:23). 기하가 맞는 판은
  report07_three_engine_ranges.npz(기선 0, 진짜 모노스태틱)다. **후자를 쓴다.**
  ⭐ 이 선택이 결과를 바꾼다 — 낡은 판으로 박자를 재면 최대선이 **2·f_flash 로 넘어가**
    예측치 대비 +99.6 % 가 나온다. 기하가 맞는 판은 −0.32 % 다. 이 그림은 그 차이 위에 서 있다.
  두 우리 팔(sbr·po)은 표적 앵커 평면파라 거리·기선과 무관하므로 원장 그대로 재사용한다
  (report07_three_engine_ranges.py 자신이 같은 이유로 그렇게 했다).

⛔ 감사(outputs/deck0811_number_audit.json)가 «버린다» 로 판정한 것은 한 자리도 안 쓴다.
   특히 이 그림들에서 뺀 것 — 엔진 간 레벨 비교(−60 dB), Sionna 변조 깊이 p-p,
   f_tip 안 스펙트럼 코사인, 40 m 의 −504.9/443.7 dB, 8·15 m 의 개별 경로 수·레벨.
   맵은 **전부 자기 최대값으로 정규화**해 레벨 비교가 애초에 일어나지 않게 한다.

읽는 것: outputs/report07_three_engine_ranges.{npz,json}   (Sionna, 거리별, 기선 0)
         outputs/report07_three_engines.{npz,json}         (우리 SBR 팔 · 슬로타임 격자)
         outputs/report07_ray_budget_test.json             (40 m 광선 사다리)
         outputs/report07_sionna_ranges.json               (40 m 빈 자세 교차확인)
쓰는 것: outputs/figures/deck0811_r1.{png,pdf}
         outputs/figures/deck0811_r2.{png,pdf}
         outputs/deck0811_beat_check.json                  (박자 지표 원장 — 아래 참조)

⭐ 왜 원장 JSON 을 새로 쓰나 — 감사가 «지표를 코드로 못 박고 원장 JSON 으로 내는 것이
   먼저다» 라고 했다. 박자 일치 수치는 여기서 정의를 고정해 재계산하고, 그 값과 **강건성
   포락(96개 분석 변형)** 을 같이 남긴다. 덱 빌더는 하드코딩 대신 이 파일을 읽으면 된다.

    python benchmark/build_deck0811_result_figs.py
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
BJ = json.load(open(f"{ROOT}/outputs/report07_ray_budget_test.json"))
SJ = json.load(open(f"{ROOT}/outputs/report07_sionna_ranges.json"))

M = RJ["_meta"]
PRF, FFL, FTIP = float(M["prf_hz"]), float(M["f_flash_hz"]), float(M["f_tip_hz"])
NAME, FC = M["name"], float(M["fc_hz"])
AZ, EL = float(M["az_deg"]), float(M["el_deg"])
N = int(M["n"])
PERIODS = auto_periods(PRF, FFL)

# 운동학 예측치의 재료 — 원장에서 읽는다(하드코딩 금지).
#   f_flash = 날개 수 x 회전수/60. 로터별 회전수의 평균이 공칭값이고, 날개 수는
#   그 둘에서 되짚어 나온다(원장이 f_flash 와 rpm 을 둘 다 적어 두었다).
RPM0 = float(np.mean(OJ["_meta"]["rpm_per_rotor"]))
BLADES = round(FFL * 60.0 / RPM0)
assert abs(BLADES * RPM0 / 60.0 - FFL) < 1e-6, "f_flash 가 날개수 x rpm/60 과 안 맞는다"

# 60 ms 확대 창 — build_flash_zoom 과 같은 자리(시작 과도를 20 ms 피한다)
ZOOM_MS = 60.0
N0 = int(round(0.020 * PRF))
NZ = int(round(ZOOM_MS / 1000.0 * PRF))

E_SIONNA = np.asarray(RZ["R3/E"], complex)      # ⭐기선 0 — 기하가 맞는 판
E_OURS = np.asarray(OZ["sbr"], complex)         # 표적 앵커 평면파 — 거리·기선 무관

C_SIONNA, C_OURS, C_PRED = "#c2570a", "#1f5fa8", "#222222"

FS = 13.0
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1.5, "ytick.labelsize": FS - 1.5,
    "axes.linewidth": 1.1, "lines.linewidth": 2.0,
    "figure.dpi": 200, "savefig.dpi": 200, "font.family": "DejaVu Sans",
})


# ── 박자 지표 — ⭐정의를 코드로 못 박는다 ───────────────────────────────────
BAND_LO, BAND_HI = 0.35, 1.00      # 날개끝 대역 (f_tip 배수)
PAD = 64                           # 선 스펙트럼 제로패딩
SEARCH = (40.0, 400.0)             # 최대선을 찾는 구간 [Hz]


def tip_band_line(E):
    """날개끝 대역 에너지의 **선 스펙트럼**과 그 최대선.

    ① 규약 스펙트로그램(flash_spec)으로 도플러-시간 맵을 만든다.
    ② |f| 가 0.35~1.00·f_tip 인 날개끝 대역의 **전력을 시간 슬롯마다 합한다** → g(t).
    ③ g 의 평균을 빼고 Hann 을 씌워 64배 제로패딩 rFFT → 선 스펙트럼.
    ④ 40~400 Hz 의 최대선을 찾고 이웃 세 점 포물선으로 위치를 다듬는다.

    ⚠ 관측 창이 208 ms 라 레일리 분해능은 4.8 Hz 다. ④의 포물선 보간은 **강한 선 하나의
      위치 추정**이지 분해능 주장이 아니다 — 캡션에 그렇게 적는다."""
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
    """⭐지표가 분석 선택에 얼마나 딸려 있나 — 96개 변형으로 포락을 잰다.

    감사가 코사인·p-p 를 버린 이유가 «격자를 바꾸면 값이 변한다» 였다. 같은 잣대를
    내 지표에도 먼저 들이댄다. 대역·패딩·전력/진폭·조각 길이·창 유무를 전부 흔든다."""
    out = {"ours": [], "sionna": [], "sionna_off_fundamental": 0, "n_variants": 0}
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
                            if key == "sionna" and abs(d) > 5.0:
                                out["sionna_off_fundamental"] += 1
                                continue
                            out[key].append(d)
    return out


# ═══ r1 — 둘이 같은 박자를 낸다 ═════════════════════════════════════════════
def build_r1(beat):
    fig = plt.figure(figsize=(12.2, 7.1))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.32, 1.0], width_ratios=[1, 1, 0.035],
                          wspace=0.10, hspace=0.46,
                          left=0.070, right=0.928, top=0.888, bottom=0.152)

    cap0, m = "", None
    for c, (E, title) in enumerate((
            (E_SIONNA, "Sionna PathSolver"),
            (E_OURS, "Ours, SBR + PO"))):
        seg = E[N0:N0 + NZ]
        ax = fig.add_subplot(gs[0, c])
        f, t, S, nper = flash_spec(seg, PRF, FFL, PERIODS)
        m = draw(ax, t + N0 / PRF, f, S, FTIP)
        if c == 0:
            cap0 = caption(PRF, FFL, nper, len(t))
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
    # ⭐수치는 **범례 이름 안에** 넣는다. 첫 판에서 따로 만든 글상자가 3배 조화선을 덮었다 —
    #   데이터를 가리는 글상자는 안 된다. 위쪽에 여백(headroom)을 만들어 거기에만 글을 둔다.
    # ⚠ 두 최대선이 0.47 Hz 차이라 표식이 서로를 덮는다. 높이를 엇갈리게 둔다 —
    #   «둘이 같은 자리에 꽂힌다» 가 보이려면 둘 다 보여야 한다.
    for key, col, base, ymk in (("sionna", C_SIONNA, "Sionna PathSolver", 9.5),
                                ("ours", C_OURS, "Ours, SBR + PO", 2.0)):
        fr, X, fpk = beat[key]["fr"], beat[key]["X"], beat[key]["peak_hz"]
        s = fr <= 420
        lab = f"{base}    {fpk:.2f} Hz    off by {dev_pct(fpk):+.2f} %"
        ax.plot(fr[s], 20 * np.log10(X[s] + 1e-6), color=col, lw=2.2, label=lab)
        ax.plot([fpk], [ymk], marker="v", ms=10, color=col, clip_on=False, zorder=5)
    ax.plot([], [], color=C_PRED, ls="--", lw=1.5,
            label=f"Kinematic prediction    {FFL:.2f} Hz    "
                  f"{BLADES:.0f} blades at {RPM0:.0f} rpm")

    # ⚠ 조화 눈금 이름은 축 **위**(축좌표 y)에 둔다 — 데이터 좌표에 두면 ylim 을 바꿀 때마다
    #   글자가 그림 안으로 굴러 들어온다(첫 판에서 그랬다).
    for h, nm in ((1, "flash rate"), (2, "2x"), (3, "3x")):
        ax.axvline(h * FFL, color=C_PRED, ls="--", lw=1.5 if h == 1 else 1.0,
                   alpha=0.85 if h == 1 else 0.42, zorder=0)
        ax.annotate(nm, xy=(h * FFL, 1.0), xycoords=("data", "axes fraction"),
                    ha="center", va="bottom", fontsize=FS - 3, color=C_PRED,
                    alpha=0.9, annotation_clip=False)

    ax.set_xlim(0, 420)
    ax.set_ylim(-44, 34)                       # 위쪽 34 dB 는 **글 자리**다(데이터는 0 dB 이하)
    ax.set_yticks([-40, -30, -20, -10, 0])
    ax.set_xlabel("Modulation rate of the blade tip band energy [Hz]")
    ax.set_ylabel("Line level [dB]")
    ax.legend(loc="upper right", fontsize=FS - 3.5, framealpha=0.94,
              title="Strongest line in the blade tip band", title_fontsize=FS - 3.5,
              borderpad=0.55, labelspacing=0.42)
    ax.grid(alpha=0.22)

    fig.suptitle(f"{NAME} hovering at {FC/1e9:.1f} GHz, belly view "
                 f"(az {AZ:.0f} deg, el {EL:.0f} deg), R = 3 m. "
                 f"The same {ZOOM_MS:.0f} ms window through two engines.",
                 fontsize=FS + 1.5, y=0.972)

    cap = (cap0 + "\n"
           "Same slow time grid, same rotor speeds, same display convention, so only the "
           "scattering engine differs. Sionna is the true monostatic run at baseline 0. "
           "Maps are normalized to their own peak, so this compares structure and timing, "
           f"never level. The beat is measured on the full {N/PRF*1e3:.0f} ms record, not "
           f"on the {ZOOM_MS:.0f} ms zoom. Rayleigh bin {PRF/N:.1f} Hz, so the quoted peak "
           "is an interpolated line position and not a resolution claim. Ledger "
           "outputs/deck0811_beat_check.json.")
    cap = "\n".join(textwrap.fill(p, 150) for p in cap.split("\n"))
    fig.text(0.070, 0.086, cap, fontsize=FS - 3.5, color="0.32", va="top")

    for ext in ("png", "pdf"):
        fig.savefig(f"{FIG}/deck0811_r1.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ═══ r2 — 거리에 대한 성질이 반대다 ═════════════════════════════════════════
def build_r2():
    rows = [("R3", 3.0), ("R8", 8.0), ("R15", 15.0)]
    fig = plt.figure(figsize=(14.0, 7.4))
    gs = fig.add_gridspec(3, 5, width_ratios=[1, 1, 0.032, 0.20, 1.30],
                          wspace=0.12, hspace=0.30,
                          left=0.052, right=0.975, top=0.862, bottom=0.225)

    m = None
    for r, (key, rng) in enumerate(rows):
        for c, (E, base, col) in enumerate((
                (np.asarray(RZ[f"{key}/E"], complex), "Sionna PathSolver", C_SIONNA),
                (E_OURS, "Ours, SBR + PO", C_OURS))):
            seg = E[N0:N0 + NZ]
            ax = fig.add_subplot(gs[r, c])
            f, t, S, _ = flash_spec(seg, PRF, FFL, PERIODS)
            m = draw(ax, t + N0 / PRF, f, S, FTIP)
            if c == 1:                       # 우리 열을 띠로 감싼다
                for sp in ax.spines.values():
                    sp.set_color(C_OURS)
                    sp.set_linewidth(2.2)
            # ⭐뱃지를 **줄마다** 붙인다 — 제목 한 줄에만 적으면 «광선이 거리 따라 오른다»
            #   와 «우리 열은 한 번만 계산했다» 가 첫 줄에서만 읽히고 아래 두 줄은 그냥
            #   반복처럼 보인다(첫 판이 그랬다).
            badge = (f"{RJ['ranges'][key]['spp']/1e6:g}M rays" if c == 0
                     else ("computed once" if r == 0 else "same array"))
            ax.text(0.014, 0.94, badge, transform=ax.transAxes, ha="left", va="top",
                    fontsize=FS - 4, color=col, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.24", fc="white", ec=col,
                              lw=1.0, alpha=0.90))
            if r == 0:
                sub = ("solved again at every range" if c == 0
                       else "range never enters the kernel")
                ax.set_title(f"{base}\n{sub}", fontsize=FS - 1.5, color=col,
                             fontweight="bold", pad=6)
            if c == 0:
                ax.set_ylabel(f"R = {rng:.0f} m\nDoppler [Hz]", fontsize=FS - 1.5)
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
    bars = ax.bar(x, zero, width=0.56, color="#b03030", alpha=0.85, zorder=2,
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
    # ⚠ 눈금표에 «(rule value)» 두 줄을 넣었더니 아래 캡션과 겹쳤다. 규칙은 축 이름 한 줄로.
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

    ax.set_title("40 m was a budget, not a wall\n"
                 "Only the ray count changes across this ladder",
                 fontsize=FS, fontweight="bold", pad=8)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", fontsize=FS - 3, framealpha=0.93,
              bbox_to_anchor=(0.5, 0.90))

    fig.suptitle(f"{NAME}, belly view, {FC/1e9:.1f} GHz. Left, one row per range, the "
                 "same 60 ms window. Right, what it costs Sionna to reach 40 m.",
                 fontsize=FS + 1.5, y=0.965)

    cap = ("Left. Only the Sionna column is solved again at each range, with the ray budget "
           "raised as the target shrinks in solid angle. Our column is computed once on a "
           "target anchored plane wave grid, so the same array is drawn in all three rows. "
           "That repetition is the claim, not an accident of plotting. Far field boundary "
           f"2D squared over lambda is about {SJ['_meta']['farfield_boundary_m']:.1f} m, so "
           "the 3 m row is near field for Sionna while 8 and 15 m are far field. No pose is "
           "ray starved at 3, 8 or 15 m. Maps are normalized to their own peak, so this "
           "compares structure only, never level.\n"
           "Right. At 40 m a starved budget leaves most poses with no path at all, which "
           "looks like a collapse. Raising the ray count alone removes it, and at the rule "
           "value the path count matches the 3 m case. A separate run at the same 32M "
           f"budget gave {SJ['ranges']['R40']['paths_zero_frac']*100:.0f} % empty poses, "
           "close to the 32M bar here. Ledger outputs/report07_ray_budget_test.json, "
           f"{BJ['_meta']['n_poses']} poses per rung, {BJ['_meta']['prf_hz']/1000:g} kHz.")
    cap = "\n".join(textwrap.fill(p, 132) for p in cap.split("\n"))
    fig.text(0.052, 0.155, cap, fontsize=FS - 3.5, color="0.32", va="top")

    for ext in ("png", "pdf"):
        fig.savefig(f"{FIG}/deck0811_r2.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    beat = {}
    for key, E in (("sionna", E_SIONNA), ("ours", E_OURS)):
        fr, X, fpk, nper, nslot, ray = tip_band_line(E)
        beat[key] = {"fr": fr, "X": X, "peak_hz": fpk, "nper": nper,
                     "slots": nslot, "rayleigh_hz": ray}

    rob = robustness()
    print(f"\n═══ 박자 지표 (f_flash 예측 {FFL:.3f} Hz) ═══")
    for k in ("sionna", "ours"):
        print(f"  {k:7s} 최대선 {beat[k]['peak_hz']:8.3f} Hz  "
              f"({dev_pct(beat[k]['peak_hz']):+.3f} %)")
    print(f"  강건성 {rob['n_variants']} 변형 — ours |dev| ≤ "
          f"{max(abs(v) for v in rob['ours']):.3f} % · sionna |dev| ≤ "
          f"{max(abs(v) for v in rob['sionna']):.3f} % "
          f"(기본파를 벗어난 변형 {rob['sionna_off_fundamental']}개)")

    json.dump({
        "_meta": {
            "owner": "build_deck0811_result_figs.py — 0811 덱 결과 그림 둘의 박자 지표",
            "why_ko": "감사가 «지표를 코드로 못 박고 원장 JSON 으로 내라» 고 했다. "
                      "덱 빌더는 이 파일을 읽어 주입한다(하드코딩 금지).",
            "source_npz": {
                "sionna": "report07_three_engine_ranges.npz : R3/E  (기선 0, 진짜 모노스태틱)",
                "ours": "report07_three_engines.npz : sbr  (표적 앵커 평면파, 거리·기선 무관)"},
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
            "caveat_ko": "포물선 보간은 강한 선 하나의 위치 추정이지 분해능 주장이 아니다 "
                         "(레일리 빈 4.8 Hz)."},
        "prediction_hz": FFL,
        "engines": {k: {"peak_hz": round(beat[k]["peak_hz"], 3),
                        "dev_pct": round(dev_pct(beat[k]["peak_hz"]), 3),
                        "is_band_max": True} for k in ("sionna", "ours")},
        "robustness": {
            "n_variants": rob["n_variants"],
            "swept_ko": "대역 6종 · 패딩 2종 · 전력/진폭 · 조각 0.45|0.60 주기 · 창 유무",
            "ours_abs_dev_max_pct": round(max(abs(v) for v in rob["ours"]), 3),
            "sionna_abs_dev_max_pct": round(max(abs(v) for v in rob["sionna"]), 3),
            "sionna_off_fundamental_variants": rob["sionna_off_fundamental"],
            "note_ko": "⚠ Sionna 팔은 좁은 대역(0.5~1.0 f_tip)을 고르면 2/96 변형에서 "
                       "최대선이 2·f_flash 로 넘어간다. 우리 팔은 96/96 이 기본파다."},
        "figures": ["outputs/figures/deck0811_r1.png", "outputs/figures/deck0811_r2.png"],
    }, open(f"{ROOT}/outputs/deck0811_beat_check.json", "w"), ensure_ascii=False, indent=1)

    build_r1(beat)
    build_r2()
    print("\n  ✅ outputs/figures/deck0811_r1.png / .pdf")
    print("  ✅ outputs/figures/deck0811_r2.png / .pdf")
    print("  ✅ outputs/deck0811_beat_check.json")


if __name__ == "__main__":
    main()
