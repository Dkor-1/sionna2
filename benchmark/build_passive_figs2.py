# -*- coding: utf-8 -*-
"""
build_passive_figs2.py — 그림 2 「처리 사슬의 어느 단이 대가를 무나」

원장(outputs/passive_two_channel.json + .npz)만 읽어서 그린다. 계산은 없다 —
숫자는 전부 원장에서 꺼내 주입하고, 곡선은 원장 .npz 의 맵을 시간평균한 것이다.
(맵에서 다시 잰 0-도플러 대비값이 원장의 zero_bin_rel_tip_db 와 같은지 스스로 검산한다.)

무엇을 보이나
--------------
(a)(b)  **단 분해** — 기준채널 오염을 ①정합필터에만 ②ECA 에만 ③둘 다 넣었을 때의 손실.
        원장 E1c 의 caf_only / eca_only / refsnr 팔이다. 두 오염 수준(+20, +10 dB)에서
        같은 그림이 나온다: 정합필터 단은 사실상 공짜이고 ECA 단이 전부를 문다.
(c)     **ECA 가 무엇을 걷어내나** — 직접파가 있는 상태에서 ECA on/off 의 도플러 프로파일.
        끄면 0-도플러가 날개끝 띠보다 45 dB 위로 솟아 마이크로도플러를 덮는다.
(d)     **노치의 값** — 그 이득과, 표적만 있는 대조군에서 잰 순수 대가(0.6 dB).

⭐ 그림 안 글자는 전부 영어(하우스 규약). 하이퍼파라미터 주석은 그림에 안 박는다.
⭐ 색은 dataviz 규약 팔레트의 슬롯 1·2·3(범주형)과 진단 대비쌍(파랑↔빨강)을 쓴다.

실행:
    PYTHONPATH=src python benchmark/build_passive_figs2.py
출력:
    outputs/figures/passive_f2.{png,pdf}
"""
from __future__ import annotations

import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "outputs", "passive_two_channel.json")
ARRAYS = os.path.join(ROOT, "outputs", "passive_two_channel.npz")
FIGDIR = os.path.join(ROOT, "outputs", "figures")
STEM = "passive_f2"

# ── 색 — dataviz 팔레트(검증 통과: 전체쌍 CVD ΔE 9.2, 정상시야 ΔE 24.0) ──────────
C_MF = "#2a78d6"     # 슬롯 1 파랑 — 정합필터 단만 오염
C_ECA = "#eb6834"    # 슬롯 2 주황 — ECA 단만 오염
C_BOTH = "#1baf7a"   # 슬롯 3 청록 — 두 단 다 오염(측정된 전체)
C_ON = "#2a78d6"     # ECA on
C_OFF = "#e34948"    # ECA off (슬롯 8 빨강)
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"

MODES = ["W1", "L1", "G1"]
NAME = {"W1": "WiFi 80 MHz\n(VHT-LTF)", "L1": "LTE 20 MHz\n(CRS)", "G1": "5G 100 MHz\n(SSB)"}


def _load():
    with open(LEDGER, encoding="utf-8") as fh:
        led = json.load(fh)
    arr = np.load(ARRAYS)
    return led, arr


def _stage_losses(led, level):
    """E1c 에서 (정합필터만, ECA만, 둘다) 손실[dB] 를 파형별로 꺼낸다."""
    out = {}
    for blk in led["E1c"]:
        rows = blk["rows"]

        def pick(kind):
            for r in rows:
                if r["kind"] == kind and r.get("axis_value") == level:
                    return float(r["loss_db"])
            raise KeyError(f"{blk['mode']} {kind} @ {level}")

        out[blk["mode"]] = dict(mf=pick("caf_only"), eca=pick("eca_only"),
                                both=pick("refsnr"))
    return out


def _doppler_profile(arr, key, f_tip):
    """맵을 시간평균해 도플러 프로파일[dB] 을 만든다 — 기준은 날개끝 띠 평균(0 dB).

    ⭐ 원장의 zero_bin_rel_tip_db 와 **정의가 같다**(md_metrics): 0-도플러 한 빈 대
      0.35~1.00·f_tip 띠. 그래서 이 곡선의 0 Hz 값이 원장 숫자와 일치해야 한다."""
    S = arr[f"e2_wifi__{key}__S"]
    f = arr[f"e2_wifi__{key}__f"]
    P = (S ** 2).mean(axis=1)
    fa = np.abs(f)
    band = (fa >= 0.35 * f_tip) & (fa <= 1.00 * f_tip)
    prof = 10 * np.log10(P / P[band].mean())
    o = np.argsort(f)
    return f[o], prof[o]


def _bar_panel(ax, losses, level, tag, title, ymax):
    xs = np.arange(len(MODES))
    w = 0.26
    series = [("mf", C_MF, "Matched filter only"),
              ("eca", C_ECA, "ECA only"),
              ("both", C_BOTH, "Both stages")]
    for k, (key, col, lab) in enumerate(series):
        vals = [losses[m][key] for m in MODES]
        ax.bar(xs + (k - 1) * w, vals, w * 0.88, color=col, label=lab,
               edgecolor="white", linewidth=0.8, zorder=3)
        for x, v in zip(xs + (k - 1) * w, vals):
            ax.text(x, v + (0.9 if v >= 0 else -0.7), f"{v:.1f}",
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=8.2, color=INK, zorder=4)
    ax.axhline(0, color=INK2, lw=0.8, zorder=2)
    ax.set_xticks(xs)
    ax.set_xticklabels([NAME[m] for m in MODES], fontsize=9)
    ax.set_ylim(-3.2, ymax)
    ax.set_ylabel("Output SINR loss vs ideal reference  [dB]", fontsize=9.5)
    ax.set_title(f"{tag}  {title}", loc="left", fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.22, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=INK2, labelsize=9)


def build(led, arr):
    f_tip = float(led["md_ledger"]["f_tip_hz"])
    surv = led["md_survival"]
    z_off = float(surv["noECA"]["zero_bin_rel_tip_db"])
    z_on = float(surv["ideal"]["zero_bin_rel_tip_db"])
    z_ctrl_off = float(surv["noDPI_noECA"]["zero_bin_rel_tip_db"])
    z_ctrl_on = float(surv["noDPI_ECA"]["zero_bin_rel_tip_db"])
    cost = float(surv["eca_notch_cost_db"]["value"])
    benefit = z_off - z_on

    l20 = _stage_losses(led, 20.0)
    l10 = _stage_losses(led, 10.0)

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "axes.labelsize": 9.5,
                         "axes.edgecolor": MUTED, "text.color": INK,
                         "axes.labelcolor": INK2, "legend.frameon": False})

    fig = plt.figure(figsize=(15.0, 8.8))
    gs = GridSpec(2, 2, figure=fig, width_ratios=[1.12, 1.0], hspace=0.40, wspace=0.20,
                  left=0.055, right=0.975, top=0.895, bottom=0.085)

    # --- (a)(b) 단 분해 ------------------------------------------------------
    ymax = max(v for d in (l20, l10) for r in d.values() for v in r.values()) * 1.14
    ax_a = fig.add_subplot(gs[0, 0])
    _bar_panel(ax_a, l20, 20.0, "(a)",
               "Contaminating one stage at a time — reference SNR 20 dB", ymax)
    ax_a.legend(fontsize=8.8, ncol=3, loc="upper left",
                title="Where the reference-channel noise enters",
                title_fontsize=8.8, handlelength=1.3, columnspacing=1.2,
                borderaxespad=0.2)
    ax_b = fig.add_subplot(gs[1, 0])
    _bar_panel(ax_b, l10, 10.0, "(b)",
               "The same decomposition at reference SNR 10 dB", ymax)

    # --- (c) ECA on/off 도플러 프로파일 --------------------------------------
    ax_c = fig.add_subplot(gs[0, 1])
    f_off, p_off = _doppler_profile(arr, "noECA", f_tip)
    f_on, p_on = _doppler_profile(arr, "ideal", f_tip)
    xlim = 1.9 * f_tip
    for s in (+1, -1):
        ax_c.axvspan(s * 0.35 * f_tip, s * 1.00 * f_tip, color=MUTED, alpha=0.13,
                     lw=0, zorder=0)
        ax_c.axvline(s * f_tip, color=MUTED, ls="--", lw=0.9, zorder=1)
    ax_c.axhline(0, color=INK2, lw=0.9, ls=":", zorder=1)
    ax_c.plot(f_off, p_off, color=C_OFF, lw=2.0, marker="o", ms=4.5,
              label="ECA off", zorder=4)
    ax_c.plot(f_on, p_on, color=C_ON, lw=2.0, marker="o", ms=4.5,
              label="ECA on", zorder=5)
    ax_c.text(0.10 * xlim, z_off + 2.0, f"{z_off:+.1f} dB", color=C_OFF,
              fontsize=10, fontweight="bold", va="bottom", ha="left")
    ax_c.text(-0.06 * xlim, z_on - 2.2, f"{z_on:+.1f} dB", color=C_ON,
              fontsize=10, fontweight="bold", va="top", ha="right")
    ax_c.text(-0.98 * xlim, 1.4, "blade-tip band = 0 dB reference",
              fontsize=8.4, color=INK2, va="bottom")
    ax_c.set_xlim(-xlim, xlim)
    ax_c.set_ylim(min(p_on.min(), p_off.min()) - 4, z_off + 11)
    ax_c.set_xlabel("Doppler  [Hz]")
    ax_c.set_ylabel("Time-averaged power vs blade-tip band  [dB]", fontsize=9.5)
    ax_c.set_title("(c)  What ECA removes — direct path present, WiFi chain",
                   loc="left", fontsize=11, fontweight="bold")
    ax_c.legend(fontsize=9, loc="upper right", handlelength=1.6)
    ax_c.grid(alpha=0.22)
    ax_c.set_axisbelow(True)
    for s in ("top", "right"):
        ax_c.spines[s].set_visible(False)
    ax_c.tick_params(colors=INK2, labelsize=9)

    # --- (d) 노치가 사는 것 vs 무는 값 ---------------------------------------
    #     같은 연산(ECA on)이 두 경우에 0-도플러에서 걷어가는 양을 나란히 놓는다:
    #     직접파가 있으면 걷어가는 것이 간섭이고(이득), 표적만 있으면 표적이다(대가).
    ax_d = fig.add_subplot(gs[1, 1])
    rows = [(1.0, "Direct path present\n(interference taken out)", benefit, z_off, z_on),
            (0.0, "Target only, control\n(target body line taken out)",
             cost, z_ctrl_off, z_ctrl_on)]
    ax_d.barh([r[0] for r in rows], [r[2] for r in rows], height=0.34, color=C_ON,
              edgecolor="white", linewidth=0.8, zorder=3)
    for y, lab, delta, off, on in rows:
        ax_d.text(delta + 0.9, y + 0.10, f"{delta:.2f} dB", va="bottom", ha="left",
                  fontsize=12, fontweight="bold", color=INK, zorder=4)
        ax_d.text(delta + 0.9, y - 0.10, f"ECA off {off:.2f}  →  on {on:.2f} dB",
                  va="top", ha="left", fontsize=9, color=INK2, zorder=4)
    ax_d.set_yticks([r[0] for r in rows])
    ax_d.set_yticklabels([r[1] for r in rows], fontsize=9.5)
    ax_d.set_ylim(-0.55, 1.55)
    ax_d.set_xlim(0, benefit * 1.46)
    ax_d.set_xlabel("Zero-Doppler bin lowered by switching ECA on  [dB]")
    ax_d.set_title(f"(d)  The notch buys {benefit:.0f} dB and costs {cost:.1f} dB",
                   loc="left", fontsize=11, fontweight="bold")
    ax_d.grid(axis="x", alpha=0.22)
    ax_d.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax_d.spines[s].set_visible(False)
    ax_d.tick_params(colors=INK2, labelsize=9, length=0)
    ax_d.text(0.0, -0.26, "Control is a rotor-dominated hover — little body energy "
                          "at zero Doppler for the notch to take.",
              transform=ax_d.transAxes, fontsize=8.4, color=MUTED, style="italic")

    fig.suptitle("Which stage of the passive chain pays for a degraded reference "
                 "channel?", fontsize=13.5, fontweight="bold")

    os.makedirs(FIGDIR, exist_ok=True)
    for ext in ("png", "pdf"):
        p = os.path.join(FIGDIR, f"{STEM}.{ext}")
        fig.savefig(p, dpi=170 if ext == "png" else None, bbox_inches="tight")
        print("  그림:", p, f"{os.path.getsize(p)/1e6:.2f} MB", flush=True)
    plt.close(fig)
    return dict(l20=l20, l10=l10, z_off=z_off, z_on=z_on, z_ctrl_off=z_ctrl_off,
                z_ctrl_on=z_ctrl_on, cost=cost, benefit=benefit, f_tip=f_tip)


def selfcheck(led, arr, f_tip):
    """맵에서 다시 잰 0-도플러 대비값이 원장 숫자와 같은지 — 곡선과 주석이 어긋나면 안 된다."""
    ok = True
    for key in ("ideal", "noECA", "noDPI_ECA", "noDPI_noECA"):
        f, prof = _doppler_profile(arr, key, f_tip)
        df = abs(f[1] - f[0])
        z = float(prof[np.abs(f) <= 0.5 * df].mean())
        ref = float(led["E2"]["wifi_b1"]["metrics"][key]["zero_bin_rel_tip_db"])
        good = abs(z - ref) < 0.01
        ok &= good
        print(f"  검산 {key:12s} 곡선 0 Hz {z:8.3f} dB · 원장 {ref:8.3f} dB "
              f"{'일치' if good else '⚠불일치'}")
    return ok


def main():
    led, arr = _load()
    print("원장:", LEDGER)
    print("  생성", led["_meta"]["generated"], "·", led["_meta"]["script"])
    d = build(led, arr)
    ok = selfcheck(led, arr, d["f_tip"])
    print("\n주입한 수치 — 전부 원장에서 읽었다")
    for lvl, tab in (("+20 dB", d["l20"]), ("+10 dB", d["l10"])):
        for m in MODES:
            r = tab[m]
            print(f"  ref SNR {lvl}  {m}: 정합필터만 {r['mf']:+7.2f} · "
                  f"ECA만 {r['eca']:+7.2f} · 둘다 {r['both']:+7.2f} dB")
    print(f"  0-도플러 대 날개끝 띠: ECA off {d['z_off']:.2f} → on {d['z_on']:.2f} dB "
          f"(이득 {d['benefit']:.2f} dB)")
    print(f"  대조군(표적만): off {d['z_ctrl_off']:.2f} → on {d['z_ctrl_on']:.2f} dB "
          f"(순수 대가 {d['cost']:.2f} dB)")
    print("검산", "통과" if ok else "⚠실패")


if __name__ == "__main__":
    main()
