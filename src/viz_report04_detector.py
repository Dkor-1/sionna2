# -*- coding: utf-8 -*-
"""viz_report04_detector.py — 리포트 04(검출기) 의 **게재 품질** 그림을 만든다

재현:
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py

입력(전부 이미 측정된 JSON — 무거운 계산 없음, 수 초):
    outputs/verify_eca.json           §1 사슬 · §2 ECA
    outputs/verify_cfar.json          §1 사슬 · §3 CFAR 교정
    outputs/verify_observability.json §4 분해능 · 관측가능성

출력: outputs/figures/report04_f{1..7}_*.{pdf,png}  — 벡터 PDF + 400 dpi PNG 를 함께 낸다.

규격(PAPER_SPEC §4.3, 구현은 `src/paper_kit.py`)
------------------------------------------------------------------------------
· 폭은 IEEE 2단 조판 기준 — `single` 3.5 in · `double` 7.16 in. 놓일 폭을
  `placed_width_in` 으로 함께 넘겨 **축소 후** 글자 크기로 판정한다.
· 글자 하한 8 pt. 본문 9~10 pt, 눈금·범례는 그보다 1 pt 작게 잡되 하한을 지킨다.
· 계열은 **색 + 마커 + 선종**(막대는 **색 + 해치**) 이중부호화 — 흑백 인쇄에서 살아남는다.
· 수식 조판(`$…$`)을 쓰지 않는다 — mathtext 아래첨자는 본문의 0.7배로 찍혀 8 pt 하한을
  깨뜨린다. 유니코드 기호(Δ · σ · λ)와 영어 낱말로 적는다.
· 그림 제목은 짧은 판 이름((a)/(b))만 둔다. 문장은 캡션이 진다 — `PAPER_CAPTIONS` 가
  그 완결 문장이고, `save_figure(caption=…)` 이 PDF 메타데이터에 심는다.

⚠ 하우스 규약: **그림 안의 글자는 전부 영어**(제목·축·범례·주석). 본문·주석은 한국어.
⚠ 그림 1개 = 질문 1개. 노트북용 **질문 캡션**은 빌더(`src/make_report04_detector.py`)가 붙인다.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import matplotlib                                                   # noqa: E402
matplotlib.use("Agg")
import numpy as np                                                  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch      # noqa: E402

from paper_kit import paper_style, save_figure                      # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")

# 파형 3종 — 이름·계열 색인을 전 그림에서 통일한다(0=WiFi, 1=LTE, 2=5G).
WFS = ("WiFi80", "LTE20", "NR100")
ECA_NAME = {"WiFi80": "WiFi 80MHz", "LTE20": "LTE 20MHz", "NR100": "5G NR 100MHz"}
LABEL = {"WiFi80": "WiFi 80 MHz", "LTE20": "LTE 20 MHz", "NR100": "5G NR 100 MHz"}
SHORT = {"WiFi80": "WiFi", "LTE20": "LTE", "NR100": "5G NR"}
IDX = {b: i for i, b in enumerate(WFS)}
HATCH = {"WiFi80": "", "LTE20": "//", "NR100": "xx"}

#: ⭐ 논문에 그대로 붙일 **완결 문장** 캡션(PAPER_SPEC §4.3).
#  빌더가 같은 문자열을 `figure_md(paper_caption=…)` 로 실어 `outputs/paper_kit.json` 에 모은다.
PAPER_CAPTIONS: dict[str, str] = {
    "f1_chain":
        "Passive bistatic detection chain applied identically to all three illuminators: "
        "a least-squares ECA projection removes the direct path from the surveillance "
        "channel, a cross-ambiguity function maps delay against Doppler, and a 2D CA-CFAR "
        "declares detections at a threshold calibrated against the measured empirical "
        "false-alarm rate.",
    "f2_eca_depth":
        "ECA cancellation depth saturates at a floor set by the measured multipath "
        "environment rather than by the number of taps, and that floor differs by more "
        "than twenty decibels across the three waveforms.",
    "f3_eca_notch":
        "The ECA zero-Doppler notch removes target energy inside one Doppler bin for all "
        "three waveforms, and the resulting minimum detectable radial speed is set by the "
        "wavelength and by the coherent processing interval.",
    "f4_pfa":
        "The empirical false-alarm rate measured over 10,000 range-Doppler maps per "
        "waveform exceeds the nominal rate by a waveform-dependent factor, so the CFAR "
        "threshold is calibrated before the three illuminators are compared at one "
        "false-alarm rate.",
    "f5_cause":
        "Removing the slow-time Hann window and whitening the matched filter returns the "
        "empirical false-alarm rate to its nominal value, which identifies training-cell "
        "correlation as the origin of the offset.",
    "f6_resolution":
        "Reference bandwidth sets the bistatic range resolution while signal-to-noise "
        "ratio sets the single-target range accuracy, and the two quantities are "
        "separated by more than an order of magnitude for every illuminator considered.",
    "f7_observability":
        "One transmitter-receiver pair leaves rotation about the baseline unobservable, "
        "and a second receiver raises the Fisher information rank to six while reducing "
        "the position RMS error to 0.19 m.",
}


def _j(name):
    with open(os.path.join(ROOT, "outputs", name), encoding="utf-8") as f:
        return json.load(f)


E = _j("verify_eca.json")
C = _j("verify_cfar.json")
O = _j("verify_observability.json")

GT = C["meta"]["gt_default"]
ZD = C["meta"]["zd_mask_operational"]
SETUP = {s["name"]: s for s in E["meta"]["setups"]}          # ECA 쪽 이름 키
S1 = {s["name"]: s for s in E["S1_depth_vs_taps"]}


def crow(band, mode, win, pfa, mask=ZD):
    """verify_cfar.json 의 (guard/train, 0-도플러 마스크, 명목 Pfa) 한 줄."""
    for r in C["chain"][band][mode][win]["rows"]:
        if r["gt"] == GT and r["zd_mask_width"] == mask and abs(r["pfa_nom"] - pfa) < 1e-15:
            return r
    raise KeyError(f"{band}/{mode}/{win} pfa={pfa}")


def wrows(band, mode="dpi_eca", win="op", mask=ZD):
    return sorted((r for r in C["chain"][band][mode][win]["rows"]
                   if r["gt"] == GT and r["zd_mask_width"] == mask),
                  key=lambda r: r["pfa_nom"])


def white_rows(mask=ZD):
    return sorted((r for r in C["white"]["48x24"]["rows"]
                   if r["gt"] == GT and r["zd_mask_width"] == mask),
                  key=lambda r: r["pfa_nom"])


def ctrl_ratio(key, pfa=1e-4):
    for r in C[key]["op"]["rows"]:
        if r["gt"] == GT and r["zd_mask_width"] == ZD and abs(r["pfa_nom"] - pfa) < 1e-15:
            return r["ratio"]
    raise KeyError(key)


def sat_depth(band):
    """탭을 아무리 늘려도 더 안 깊어지는 상한 = 측정된 소거 바닥."""
    return max(r["depth_full_db"] for r in S1[ECA_NAME[band]]["rows"])


def _emit(fig, name, width_in):
    """벡터 PDF + 400 dpi PNG 를 함께 저장하고 게재 규격 검사를 통과시킨다."""
    os.makedirs(FIG, exist_ok=True)
    stem = os.path.join("outputs", "figures", f"report04_{name}")
    out = save_figure(fig, stem, dpi=400, caption=PAPER_CAPTIONS[name],
                      title=f"report04 {name}", placed_width_in=width_in,
                      strict=True, close=True)
    chk = out["check"]
    mark = "✅" if chk["ok"] else "⚠"
    print(f"  {mark} {out['pdf']}  +  {out['png']}   "
          f"(min {chk['min_font_pt']} pt · 색전용계열 {len(chk['colour_only_series'])})")
    if not chk["ok"]:
        print("     " + " / ".join(chk["violations"]))
    return out


def _src(fig, text):
    """출처 한 줄 — 그림만 떼어 가도 어느 JSON 에서 나왔는지 남는다."""
    fig.text(0.0, -0.012, text, ha="left", va="top", fontsize=8.2, color="#666666")


def _plain_log(axis, mode: str = "dec") -> None:
    """로그축 눈금 글자에서 **수식 조판을 걷어낸다**.

    matplotlib 기본 로그 포매터는 `10^{-4}` 를 mathtext 로 찍고, 그 위첨자는 본문의 0.7배가
    되어 8 pt 하한을 깬다. 십진("0.01")이나 지수 문자열("1e-4")로 바꿔 하한을 지킨다.
    """
    from matplotlib.ticker import FuncFormatter, NullFormatter

    def fmt(v, _pos):
        if v <= 0:
            return ""
        e = int(round(float(np.log10(v))))
        if abs(v - 10.0 ** e) > 1e-6 * v:
            return ""
        return f"1e{e}" if mode == "sci" else f"{10.0 ** e:g}"

    axis.set_major_formatter(FuncFormatter(fmt))
    axis.set_minor_formatter(NullFormatter())


# --------------------------------------------------------------------------- #
#  그림 1 — 검출 사슬 (수신 신호가 판정이 되기까지)
# --------------------------------------------------------------------------- #
def f1_chain():
    W = 7.16
    with paper_style(width="double", base_pt=9.0, aspect=0.50,
                     **{"axes.grid": False}) as st:
        fig, ax = st.figure()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")

        def tri(vals, f="{:.0f}", sep=" / "):
            return sep.join(f.format(v) for v in vals)

        dnr = [SETUP[ECA_NAME[b]]["dnr_db"] for b in WFS]
        taps = [SETUP[ECA_NAME[b]]["n_taps"] for b in WFS]
        floor = [sat_depth(b) for b in WFS]
        nrng = [C["chain"][b]["n_range_op"] for b in WFS]
        ratio = [crow(b, "dpi_eca", "op", 1e-4)["ratio"] for b in WFS]
        M = C["meta"]["M_cpi"]
        g, t = GT.replace("g", "").split("_t")

        # (제목, 하는 일 2줄, 측정된 사실 — 등폭 글자 23칸 안)
        stages = [
            ("1  RX", ["surveillance and", "reference channels"],
             [f"DNR {tri(dnr)} dB"]),
            ("2  ECA", ["least-squares", "projection"],
             [f"taps {tri(taps)}", f"floor {tri(floor)} dB"]),
            ("3  CAF", ["correlate over", "delay and Doppler"],
             [f"{tri(nrng, sep='/')} range bins", f"x {M:.0f} Doppler bins",
              "slow-time Hann"]),
            ("4  CA-CFAR", ["threshold from the", "local neighbourhood"],
             [f"guard {g} train {t}", "nominal 1e-4 gives",
              f"{tri(ratio, '{:.2f}', sep='/')} x"]),
        ]

        x0, w, gap = 0.8, 23.7, 1.3
        for i, (title, what, facts) in enumerate(stages):
            x = x0 + i * (w + gap)
            lead = i == len(stages) - 1                 # 마지막 칸이 이 논문의 중심이다
            ax.add_patch(FancyBboxPatch(
                (x, 22.0), w, 58.0, boxstyle="round,pad=0.4,rounding_size=1.0",
                linewidth=1.9 if lead else 0.9,
                edgecolor="#000000", facecolor="#E6E6E6" if lead else "#F7F7F7"))
            ax.text(x + w / 2, 73.0, title, ha="center", va="center",
                    fontsize=9.5, fontweight="bold")
            ax.text(x + w / 2, 63.0, "\n".join(what), ha="center", va="top",
                    fontsize=8.4, linespacing=1.35)
            ax.text(x + w / 2, 44.0, "\n".join(facts), ha="center", va="top",
                    fontsize=8.4, family="monospace", linespacing=1.35)
            if i < len(stages) - 1:
                ax.add_patch(FancyArrowPatch(
                    (x + w + 0.1, 51.0), (x + w + gap - 0.1, 51.0),
                    arrowstyle="-|>", mutation_scale=10, linewidth=1.1, color="#000000"))

        ax.text(0.0, 96.0, "triples read as  WiFi / LTE / 5G NR",
                ha="left", va="top", fontsize=8.4, style="italic")
        ax.text(0.0, 14.0,
                f"calibration loop: {C['meta']['n_maps_chain']:,} maps per waveform over "
                f"{C['meta']['runtime_s']:.0f} s of GPU Monte Carlo,\n"
                "then the nominal threshold is rescaled onto the target empirical rate",
                ha="left", va="top", fontsize=8.4, linespacing=1.35)
        _src(fig, "verify_eca.json : meta.setups   verify_cfar.json : chain, meta")
        return _emit(fig, "f1_chain", W)


# --------------------------------------------------------------------------- #
#  그림 2 — ECA 소거 깊이: 탭을 늘리면 어디서 멈추나
# --------------------------------------------------------------------------- #
def f2_eca_depth():
    W = 3.5
    with paper_style(width="single", base_pt=9.0, aspect=0.78,
                     **{"xtick.labelsize": 8.2, "ytick.labelsize": 8.2,
                        "legend.fontsize": 8.2}) as st:
        fig, ax = st.figure()
        for b in WFS:
            s = S1[ECA_NAME[b]]
            t = [r["n_taps"] for r in s["rows"]]
            ax.plot(t, [r["depth_full_db"] for r in s["rows"]],
                    label=LABEL[b], **st.series(IDX[b]))
            ax.annotate(f"{sat_depth(b):.0f} dB", xy=(96, sat_depth(b)),
                        xytext=(-2, 4), textcoords="offset points", ha="right",
                        fontsize=8.2, fontweight="bold", color=st.color(IDX[b]))
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 4, 16, 64])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_xlabel("ECA taps")
        ax.set_ylabel("cancellation depth [dB]")
        ax.set_ylim(0, 72)
        ax.legend(loc="upper left")
        ax.text(0.97, 0.04,
                "direct path alone:\nfloat64 limit, off scale",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=8.2)
        _src(fig, "verify_eca.json : S1_depth_vs_taps")
        return _emit(fig, "f2_eca_depth", W)


# --------------------------------------------------------------------------- #
#  그림 3 — ECA 의 대가: 0-도플러 노치가 먹는 느린 표적
# --------------------------------------------------------------------------- #
def f3_eca_notch():
    W = 7.16
    with paper_style(width="double", base_pt=9.5, aspect=0.40,
                     **{"xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                        "legend.fontsize": 8.5}) as st:
        fig, axes = st.figure(1, 2)

        ax = axes[0]
        for b in WFS:
            s = next(x for x in E["S4_target_loss"]
                     if x["name"] == ECA_NAME[b] and x["M"] == 48)
            rr = [r for r in s["rows"] if 0.0 < r["fd_over_dfd"] <= 2.0]
            ax.plot([r["fd_over_dfd"] for r in rr], [r["energy_loss_db"] for r in rr],
                    label=LABEL[b], markevery=3, **st.series(IDX[b]))
        th = [r for r in s["rows"] if 0.0 < r["fd_over_dfd"] <= 2.0]
        ax.plot([r["fd_over_dfd"] for r in th], [r["theory_loss_db"] for r in th],
                color="#000000", linestyle=(0, (6, 2)), marker="none",
                linewidth=1.1, label="theory  1 - sinc squared")
        ax.axhline(-3, color="#000000", linestyle=":", linewidth=0.9)
        ax.text(1.97, -2.4, "-3 dB", ha="right", fontsize=8.5, fontweight="bold")
        ax.set_xlabel("Doppler offset / Doppler bin width")
        ax.set_ylabel("target energy removed [dB]")
        ax.set_ylim(-26, 3)
        ax.set_title("(a) notch width, 48 frames")
        ax.legend(loc="lower right")

        ax = axes[1]
        Ms = sorted({x["M"] for x in E["S4_target_loss"]})
        width = 0.26
        xs = np.arange(len(Ms))
        for b in WFS:
            v = [next(x for x in E["S4_target_loss"]
                      if x["name"] == ECA_NAME[b] and x["M"] == m)["v_3db_ms"] for m in Ms]
            ax.bar(xs + (IDX[b] - 1) * width, v, width, label=LABEL[b],
                   color=st.color(IDX[b]), hatch=HATCH[b],
                   edgecolor="#000000", linewidth=0.6)
        tcpi = {m: next(x["T_cpi_ms"] for x in E["S4_target_loss"] if x["M"] == m)
                for m in Ms}
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{m}\n{tcpi[m]:.0f} ms" for m in Ms])
        ax.set_xlabel("frames per CPI  (shortest CPI of the three)")
        ax.set_ylabel("min detectable radial speed [m/s]")
        ax.set_ylim(0, 4.6)
        ax.set_title("(b) longer CPI narrows the notch")
        ax.legend(loc="upper right", ncol=1)
        _src(fig, "verify_eca.json : S4_target_loss")
        return _emit(fig, "f3_eca_notch", W)


# --------------------------------------------------------------------------- #
#  그림 4 — ⭐ 명목 Pfa vs 경험 Pfa (이 편의 중심)
# --------------------------------------------------------------------------- #
def f4_pfa():
    W = 7.16
    with paper_style(width="double", base_pt=9.5, aspect=0.42,
                     **{"xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                        "legend.fontsize": 8.2}) as st:
        fig, axes = st.figure(1, 2)

        ax = axes[0]
        nom = np.array(sorted(C["meta"]["pfa_nominal"]))
        ax.plot(nom, nom, color="#000000", linestyle=":", marker="none",
                linewidth=1.0, label="empirical = nominal")
        Wr = white_rows()
        ax.plot([r["pfa_nom"] for r in Wr], [r["pfa_emp"] for r in Wr],
                label=f"ideal white map ({C['meta']['n_maps_white']:,})",
                **st.series(6))
        for b in WFS:
            rr = wrows(b)
            ax.plot([r["pfa_nom"] for r in rr], [r["pfa_emp"] for r in rr],
                    label=f"{SHORT[b]} chain", **st.series(IDX[b]))
        ax.set_xscale("log")
        ax.set_yscale("log")
        _plain_log(ax.xaxis, "sci")
        _plain_log(ax.yaxis, "sci")
        ax.set_xlabel("nominal false-alarm rate (asked for)")
        ax.set_ylabel("empirical false-alarm rate (measured)")
        ax.set_title("(a) the detector fires more often than asked")
        ax.legend(loc="upper left")

        ax = axes[1]
        for b in WFS:
            r = crow(b, "dpi_eca", "op", 1e-4)
            lo, hi = r["pfa_lo"] / 1e-4, r["pfa_hi"] / 1e-4
            ax.bar(IDX[b], r["ratio"], 0.55, color=st.color(IDX[b]), hatch=HATCH[b],
                   edgecolor="#000000", linewidth=0.6, label=LABEL[b])
            ax.errorbar(IDX[b], r["ratio"], yerr=[[r["ratio"] - lo], [hi - r["ratio"]]],
                        fmt="none", ecolor="#000000", capsize=4, linewidth=1.1)
            ax.text(IDX[b], hi + 0.10, f"{r['ratio']:.2f}", ha="center",
                    fontsize=9.5, fontweight="bold")
        hline = ax.axhline(1.0, color="#000000", linestyle="--", linewidth=1.0,
                           label="calibrated target")
        ax.legend(handles=[hline], loc="upper right")   # 막대는 x 눈금이 이미 이름 짓는다
        ax.set_xticks(range(3))
        ax.set_xticklabels([SHORT[b] for b in WFS])
        ax.set_ylabel("empirical / nominal false-alarm rate")
        ax.set_ylim(0, 3.2)
        ax.set_title("(b) by a different factor per waveform")
        ax.text(0.03, 0.95,
                f"nominal 1e-4\n{C['meta']['n_maps_chain']:,} maps per waveform\n"
                "whiskers: 95 % CI",
                transform=ax.transAxes, va="top", fontsize=8.2)
        _src(fig, "verify_cfar.json : white.48x24, chain.*.dpi_eca.op")
        return _emit(fig, "f4_pfa", W)


# --------------------------------------------------------------------------- #
#  그림 5 — 원인: 이웃 칸 상관. 끄면 눈금이 돌아온다
# --------------------------------------------------------------------------- #
def f5_cause():
    W = 7.16
    with paper_style(width="double", base_pt=9.5, aspect=0.42,
                     **{"xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                        "legend.fontsize": 8.5}) as st:
        fig, axes = st.figure(1, 2)

        ax = axes[0]
        vals = [crow("NR100", "noise", "op", 1e-4)["ratio"],
                ctrl_ratio("control_rect_window_NR100"),
                ctrl_ratio("control_whitened_mf_NR100"),
                ctrl_ratio("control_whitened_mf_rect_NR100")]
        names = ["Hann +\nmatched", "rect\nwindow", "whitened\nMF", "both\nremoved"]
        hat = ["", "//", "\\\\", "xx"]
        greys = ["#4D4D4D", "#8C8C8C", "#8C8C8C", "#D9D9D9"]
        for i, (v, h, g) in enumerate(zip(vals, hat, greys)):
            ax.bar(i, v, 0.58, color=g, hatch=h, edgecolor="#000000", linewidth=0.6)
            ax.text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=9.0,
                    fontweight="bold")
        ax.axhline(1.0, color="#000000", linestyle="--", linewidth=1.0)
        ax.set_xticks(range(4))
        ax.set_xticklabels(names)
        ax.set_ylabel("empirical / nominal false-alarm rate")
        ax.set_ylim(0, max(vals) * 1.30)
        ax.set_title("(a) 5G NR, noise-only maps")

        ax = axes[1]
        xs = np.arange(3)
        rho_d = [C["chain"][b]["noise"]["whiteness"]["rho_doppler"][0] for b in WFS]
        rho_r = [C["chain"][b]["noise"]["whiteness"]["rho_range"][0] for b in WFS]
        ax.bar(xs - 0.19, rho_d, 0.36, color=st.color(3), hatch="",
               edgecolor="#000000", linewidth=0.6, label="Doppler axis")
        ax.bar(xs + 0.19, rho_r, 0.36, color=st.color(4), hatch="///",
               edgecolor="#000000", linewidth=0.6, label="range axis")
        for x, v in zip(xs - 0.19, rho_d):
            ax.text(x, v + 0.014, f"{v:.2f}", ha="center", fontsize=8.5)
        for x, v in zip(xs + 0.19, rho_r):
            ax.text(x, v + 0.014, f"{v:.2f}", ha="center", fontsize=8.5)
        ax.axhline(0, color="#000000", linewidth=0.8)
        ax.set_xticks(xs)
        ax.set_xticklabels([SHORT[b] for b in WFS])
        ax.set_ylabel("lag-1 correlation of adjacent cells")
        ax.set_ylim(-0.02, 0.60)
        ax.legend(loc="upper center", ncol=2)
        ax.set_title("(b) CA-CFAR assumes independent training cells")
        _src(fig, "verify_cfar.json : chain.*.noise, control_*_NR100")
        return _emit(fig, "f5_cause", W)


# --------------------------------------------------------------------------- #
#  그림 6 — 분해능(두 표적을 가르나) vs 정확도(한 표적을 얼마나 정밀히 찍나)
# --------------------------------------------------------------------------- #
def f6_resolution():
    W = 7.16
    cells = O["cells"]
    with paper_style(width="double", base_pt=9.5, aspect=0.40,
                     **{"xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                        "legend.fontsize": 8.5}) as st:
        fig, ax = st.figure()
        xs = np.arange(len(cells))
        #  ⚠ 분해능 막대는 **선언 규약** c/B_ref (drb_bw_m) 다 — 리포트 03 §1·§2 와 같은 수.
        #    JSON 의 drb_m 은 max(자기상관 -3 dB, 거리 빈) 이라 규약과 다른 양이므로 쓰지 않는다.
        drb = [c["drb_bw_m"] for c in cells]
        bins = [c["bin_m"] for c in cells]
        sig = [c["sigma_rb_m"] for c in cells]
        ax.bar(xs - 0.19, drb, 0.36, color=st.color(0), hatch="",
               edgecolor="#000000", linewidth=0.6,
               label="resolution  c / B_ref  (declared convention)")
        ax.bar(xs + 0.19, sig, 0.36, color=st.color(2), hatch="xx",
               edgecolor="#000000", linewidth=0.6,
               label="accuracy  CRLB on a single target")
        ax.scatter(xs - 0.19, bins, marker="_", s=260, linewidths=1.8,
                   color="#000000", zorder=4, label="range bin  c / fs")
        for x, v in zip(xs - 0.19, drb):
            ax.text(x, v * 1.35, f"{v:.1f} m", ha="center", fontsize=8.5,
                    fontweight="bold")
        for x, v in zip(xs + 0.19, sig):
            ax.text(x, v * 1.35, f"{v * 100:.1f} cm", ha="center", fontsize=8.5,
                    fontweight="bold")
        ax.set_yscale("log")
        _plain_log(ax.yaxis, "dec")
        ax.set_ylim(3e-3, 6e2)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{c['label']}\n{c['ref_bw_mhz']:.1f} MHz reference"
                            for c in cells])
        ax.set_ylabel("bistatic range [m, log scale]")
        ax.legend(loc="upper left", ncol=1)
        _src(fig, "verify_observability.json : cells")
        return _emit(fig, "f6_resolution", W)


# --------------------------------------------------------------------------- #
#  그림 7 — 관측가능성: 송수신 한 쌍으로는 위치가 안 풀린다
# --------------------------------------------------------------------------- #
def f7_observability():
    W = 3.5
    F = O["fixes"]
    keys = ["1RX (baseline)", "2RX", "1RX + AoA(1deg)", "1RX + AoA(5deg)"]
    names = ["1 RX", "2 RX", "1 RX\n+AoA 1°", "1 RX\n+AoA 5°"]
    vals = [F[k]["pos_rms_m"] for k in keys]
    rank = [F[k]["rank_practical"] for k in keys]
    hat = ["", "xx", "//", "//"]
    greys = ["#D9D9D9", "#4D4D4D", "#A6A6A6", "#A6A6A6"]
    with paper_style(width="single", base_pt=9.0, aspect=0.86,
                     **{"xtick.labelsize": 8.2, "ytick.labelsize": 8.2}) as st:
        fig, ax = st.figure()
        for i, (v, h, g) in enumerate(zip(vals, hat, greys)):
            ax.bar(i, v, 0.6, color=g, hatch=h, edgecolor="#000000", linewidth=0.6)
            txt = f"{v:.0f} m" if v >= 1 else f"{v * 100:.0f} cm"
            ax.text(i, v * 1.6, txt, ha="center", fontsize=8.6, fontweight="bold")
        ax.set_yscale("log")
        _plain_log(ax.yaxis, "dec")
        ax.set_ylim(5e-3, 5e2)
        ax.set_xticks(range(4))
        ax.set_xticklabels([f"{n}\nrank {r}/6" for n, r in zip(names, rank)])
        ax.set_ylabel("position RMS error [m, log scale]")
        _src(fig, "verify_observability.json : fixes")
        return _emit(fig, "f7_observability", W)


def build_all():
    print("리포트 04 그림 생성 (게재 규격: 벡터 PDF + 400 dpi PNG):")
    for fn in (f1_chain, f2_eca_depth, f3_eca_notch, f4_pfa,
               f5_cause, f6_resolution, f7_observability):
        fn()


if __name__ == "__main__":
    build_all()
