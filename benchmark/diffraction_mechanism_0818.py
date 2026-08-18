# -*- coding: utf-8 -*-
"""
diffraction_mechanism_0818.py — 회절을 켜면 왜 리듬이 사라지나, 물리와 수식으로
================================================================================

물음
----
스위치 격자에서 **회절 하나만 켜면** 무늬가 무너진다(리듬 몫 80.5 → 11.7 %). 사용자 물음:
«예상과 다른 이 결과가 왜 나오나 — 물리적으로, 수식적으로».

무엇을 재나 (전부 저장된 원장에서, GPU 없음)
--------------------------------------------
  ① **얹는가 바꾸는가** — 회절 켠 시계열을 끈 시계열에 투영해 담김계수 a 를 낸다.
     ⭐정지 성분(DC)을 먼저 빼고 해야 뜻이 있다. DC 를 남기면 a 가 50 배로 나온다(허수).
  ② **얹힌 항의 성질** — 잔차 r = x_D − a·x_S 의 이웃 자세 상관(lag-1)과 도플러 분포.
  ③ **백색 예측과 대조** — r 이 완전 백색이라면 두 수가 **닫힌 식**으로 정해진다:
        f_tip 위 몫 = (PRF/2 − f_tip)/(PRF/2)
        리듬 몫     = 2·hw / f_flash
     이 둘을 실측과 나란히 놓는다. 백색잡음 20 회 대조군도 같이 돌린다.
  ④ **광선 예산 사다리** — 광선을 늘리면 이 항이 줄어드는가(수렴) 늘어나는가(발산).
     ⛔이것이 «표본 잡음» 가설을 가르는 자리다.

산출: outputs/diffraction_mechanism_0818.json · outputs/figures/diffraction_mechanism.png

실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/diffraction_mechanism_0818.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
FIG = os.path.join(ROOT, "outputs", "figures")
OUT = os.path.join(ROOT, "outputs", "diffraction_mechanism_0818.json")

EL = -30.0
PRF = 19700.0
FFL = 126.66666666666667          # 날개 플래시 박자 [Hz]
FTIP = 1101.6                     # el −30° 날개끝 도플러 상한 [Hz]
HW = 8.0                          # 빗살 반폭 [Hz]

SPEC = "sionna_p4000000000_r15_n8192_d1"                # 정반사만 (회절 끔)
DIFF = "sionna_p4000000000_onlydiffr_r15_n8192"         # 정반사 + 회절

#: 광선 예산 사다리 — (팔 이름, 광선 수, 깊이)
LADDER = [
    ("sionna_p1000000000_swR1D1E1F1_r15_n8192_d1", 1.0e9, 1),
    ("sionna_p4000000000_phys_r15_n8192_d1", 4.0e9, 1),
    ("sionna_phys", 1.1111111e7, 3),
    ("sionna_p250000000_phys", 2.5e8, 3),
    ("sionna_p4000000000_swR1D1E1F1_r15_n8192_d3", 4.0e9, 3),
]


def load(arm: str):
    """샤드 → 자세 시계열. 결측이 있으면 (시계열, 결측수)."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{EL:+.0f}_*.npz"))
    if not fs:
        return None, None
    E = seen = None
    for f in fs:
        d = np.load(f)
        n = int(np.asarray(d["meta"], float)[3])
        if E is None:
            E = np.zeros(n, complex)
            seen = np.zeros(n, bool)
        ii = d["idx"].astype(int)
        E[ii] = d["E"]
        seen[ii] = True
    return E, int((~seen).sum())


def lag1(x: np.ndarray) -> float:
    """이웃 자세 사이 상관 — 1 이면 매끄럽고 0 이면 백색."""
    x = x - x.mean()
    return float(abs(np.vdot(x[:-1], x[1:])) / np.vdot(x, x).real)


def shares(x: np.ndarray):
    """(f_tip 위 에너지 몫 [%], 그중 빗살에 붙은 몫 [%])."""
    ac = x - x.mean()
    P = np.abs(np.fft.fft(ac * np.hanning(ac.size))) ** 2
    fr = np.fft.fftfreq(ac.size, 1.0 / PRF)
    ab = np.abs(fr) >= FTIP
    k = np.round(np.abs(fr) / FFL)
    on = np.abs(np.abs(fr) - k * FFL) <= HW
    return (100.0 * P[ab].sum() / P.sum(), 100.0 * P[ab & on].sum() / P[ab].sum())


def acdb(x: np.ndarray) -> float:
    ac = x - x.mean()
    return float(10 * np.log10((np.abs(ac) ** 2).mean()))


def main() -> None:
    t0 = time.time()

    # ── ① 얹는가 바꾸는가 ────────────────────────────────────────────────
    xs, ms = load(SPEC)
    xd, md = load(DIFF)
    if xs is None or xd is None:
        raise SystemExit("⛔ 샤드가 없다")
    if ms or md:
        raise SystemExit(f"⛔ 결측 자세가 있다 (정반사 {ms} · 회절 {md}) — 채우고 다시")

    s = xs - xs.mean()                      # ⭐DC 를 먼저 뺀다
    d = xd - xd.mean()
    a = complex(np.vdot(s, d) / np.vdot(s, s))
    r = d - a * s                           # 회절이 **얹은** 항
    pw = lambda v: float((np.abs(v) ** 2).mean())                       # noqa: E731

    contain = dict(
        a_abs=round(abs(a), 4), a_phase_deg=round(float(np.degrees(np.angle(a))), 2),
        kept_power_frac=round(pw(a * s) / pw(d), 4),
        added_power_frac=round(pw(r) / pw(d), 4),
        added_over_specular_db=round(10 * np.log10(pw(r) / pw(s)), 2),
        dc_rise_db=round(20 * np.log10(abs(xd.mean()) / abs(xs.mean())), 2),
        ac_rise_db=round(acdb(xd) - acdb(xs), 2),
        reading_ko=("담김계수가 1 근처면 회절은 **얹는 축**이다 — 원래 시계열을 그대로 "
                    "두고 위에 새 항을 더한다. 바꾸는 축이면 a 가 1 에서 크게 벗어난다."),
    )

    # ── ②③ 얹힌 항이 백색인가 — 닫힌 식과 대조 ─────────────────────────
    white_above = 100.0 * (PRF / 2 - FTIP) / (PRF / 2)
    white_comb = 100.0 * 2 * HW / FFL
    rng = np.random.default_rng(7)
    ctl = np.array([[*shares(rng.normal(size=xs.size) + 1j * rng.normal(size=xs.size)),
                     lag1(rng.normal(size=xs.size) + 1j * rng.normal(size=xs.size))]
                    for _ in range(20)])

    rows = {}
    for tag, v in (("specular_only", s), ("diffraction_on", d), ("added_term", r)):
        ab, cb = shares(v)
        rows[tag] = dict(above_tip_pct=round(ab, 2), rhythm_pct=round(cb, 2),
                         lag1=round(lag1(v), 4), ac_db=round(acdb(v), 2))

    whiteness = dict(
        closed_form=dict(
            above_tip_pct=round(white_above, 2),
            above_tip_formula="(PRF/2 − f_tip)/(PRF/2)",
            rhythm_pct=round(white_comb, 2),
            rhythm_formula="2·hw/f_flash",
        ),
        white_control_20runs=dict(
            above_tip_pct=[round(ctl[:, 0].mean(), 2), round(ctl[:, 0].std(), 2)],
            rhythm_pct=[round(ctl[:, 1].mean(), 2), round(ctl[:, 1].std(), 2)],
            lag1=round(ctl[:, 2].mean(), 4)),
        measured_added_term=rows["added_term"],
        verdict_ko=("얹힌 항의 두 수가 **닫힌 식과 백색 대조군에 같이 앉으면** "
                    "그 항은 슬로우타임에서 백색이다 — 즉 도플러 정보가 없다."),
    )

    # ── ④ 광선 예산 사다리 ──────────────────────────────────────────────
    ladder = []
    for arm, rays, depth in LADDER:
        x, miss = load(arm)
        if x is None:
            continue
        ab, cb = shares(x)
        ladder.append(dict(arm=arm, rays=rays, max_depth=depth, n_missing=miss,
                           ac_db=round(acdb(x), 2), above_tip_pct=round(ab, 2),
                           lag1=round(lag1(x), 4)))
    for d_ in (1, 3):
        g = sorted([l for l in ladder if l["max_depth"] == d_], key=lambda z: z["rays"])
        for i in range(1, len(g)):
            g[i]["vs_prev"] = dict(
                ray_ratio=round(g[i]["rays"] / g[i - 1]["rays"], 2),
                d_ac_db=round(g[i]["ac_db"] - g[i - 1]["ac_db"], 2),
                expected_if_sampling_noise_db=round(
                    -10 * np.log10(g[i]["rays"] / g[i - 1]["rays"]), 2),
                expected_if_incoherent_sum_db=round(
                    10 * np.log10(g[i]["rays"] / g[i - 1]["rays"]), 2))

    # ── 그림 ────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(1, 3, figsize=(19.5, 5.4))

    lags = np.arange(0, 41)
    for v, nm, c in ((s, "specular only", "#1565c0"), (r, "term diffraction adds", "#c62828")):
        vv = v - v.mean()
        ac = np.array([abs(np.vdot(vv[:vv.size - k], vv[k:])) / np.vdot(vv, vv).real
                       for k in lags])
        ax[0].plot(lags, ac, lw=2.0, color=c, label=nm)
    ax[0].axhline(0, color="0.6", lw=0.8)
    ax[0].set_xlabel("lag [poses]")
    ax[0].set_ylabel("normalised correlation")
    ax[0].set_title("how fast it forgets between poses", pad=7)
    ax[0].legend(fontsize=11)
    ax[0].grid(alpha=0.3)

    for v, nm, c in ((s, "specular only", "#1565c0"), (r, "term diffraction adds", "#c62828")):
        vv = v - v.mean()
        P = np.abs(np.fft.fftshift(np.fft.fft(vv * np.hanning(vv.size)))) ** 2
        fr = np.fft.fftshift(np.fft.fftfreq(vv.size, 1.0 / PRF))
        ax[1].plot(fr, 10 * np.log10(P / P.max()), lw=0.7, color=c, alpha=0.85, label=nm)
    for sgn in (-1, 1):
        ax[1].axvline(sgn * FTIP, color="k", ls="--", lw=1.2)
    ax[1].text(FTIP, 3, " blade tip ceiling", fontsize=11, va="bottom")
    ax[1].set_xlim(-PRF / 2, PRF / 2)
    ax[1].set_ylim(-70, 8)
    ax[1].set_xlabel("Doppler [Hz]")
    ax[1].set_ylabel("dB below own peak")
    ax[1].set_title("where the energy sits in Doppler", pad=7)
    ax[1].legend(fontsize=11, loc="lower right")
    ax[1].grid(alpha=0.3)

    for d_, mk, c in ((1, "o", "#1565c0"), (3, "s", "#c62828")):
        g = sorted([l for l in ladder if l["max_depth"] == d_], key=lambda z: z["rays"])
        if len(g) < 2:
            continue
        ax[2].plot([l["rays"] for l in g], [l["ac_db"] for l in g], mk + "-", lw=2.0,
                   color=c, label=f"depth {d_}")
    ax[2].set_xscale("log")
    ax[2].set_xlabel("rays cast")
    ax[2].set_ylabel("moving-part power [dB]")
    ax[2].set_title("more rays makes it stronger, not weaker", pad=7)
    ax[2].legend(fontsize=11)
    ax[2].grid(alpha=0.3, which="both")

    fig.suptitle("turning diffraction on adds a term that is white in slow time "
                 "and has not converged", fontsize=15, color="0.3")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    p = f"{FIG}/diffraction_mechanism.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)

    doc = {
        "_meta": {
            "generator": "benchmark/diffraction_mechanism_0818.py",
            "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                           time.gmtime(time.time() + 9 * 3600)),
            "question_ko": "회절을 켜면 왜 리듬이 사라지나 — 물리·수식",
            "gpu_used": False,
            "inputs": ["outputs/elev_sweep_shards/*.npz"],
            "setup_ko": f"matrice4e · 3.5 GHz · 15 m · 자세 8192 · 앙각 {EL}° · "
                        f"PRF {PRF:.0f} Hz · f_tip {FTIP} Hz · f_flash {FFL:.2f} Hz",
            "elapsed_s": round(time.time() - t0, 2),
        },
        "q1_additive_or_transforming": contain,
        "q2_is_the_added_term_white": whiteness,
        "q3_ray_budget_ladder": ladder,
        "arms": rows,
        "figure": "outputs/figures/diffraction_mechanism.png",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print("═══ ① 얹는가 바꾸는가 ═══")
    print(f"  담김계수 a = {abs(a):.3f} ∠{np.degrees(np.angle(a)):+.1f}°  "
          f"→ 남은 몫 {contain['kept_power_frac']*100:.1f} % · 얹힌 몫 "
          f"{contain['added_power_frac']*100:.1f} %")
    print(f"  DC {contain['dc_rise_db']:+.1f} dB · AC {contain['ac_rise_db']:+.1f} dB")
    print("\n═══ ②③ 얹힌 항이 백색인가 ═══")
    print(f"  {'':22s} {'f_tip 위':>10s} {'리듬':>9s} {'lag-1':>8s}")
    print(f"  {'닫힌 식(완전 백색)':22s} {white_above:9.2f} % {white_comb:8.2f} %        —")
    print(f"  {'백색잡음 20 회':22s} {ctl[:,0].mean():9.2f} % {ctl[:,1].mean():8.2f} % "
          f"{ctl[:,2].mean():8.4f}")
    for tag, ko in (("specular_only", "정반사만"), ("diffraction_on", "회절 켠 판"),
                    ("added_term", "⭐회절이 얹은 항")):
        v = rows[tag]
        print(f"  {ko:22s} {v['above_tip_pct']:9.2f} % {v['rhythm_pct']:8.2f} % "
              f"{v['lag1']:8.4f}")
    print("\n═══ ④ 광선 예산 사다리 ═══")
    for l in ladder:
        vs = l.get("vs_prev")
        tail = (f"  광선 ×{vs['ray_ratio']:.1f} → {vs['d_ac_db']:+.2f} dB "
                f"(표본잡음이면 {vs['expected_if_sampling_noise_db']:+.1f} · "
                f"비간섭 합이면 {vs['expected_if_incoherent_sum_db']:+.1f})" if vs else "")
        print(f"  깊이 {l['max_depth']} · 광선 {l['rays']:.2e} · AC {l['ac_db']:8.2f} dB · "
              f"f_tip 위 {l['above_tip_pct']:5.1f} % · lag-1 {l['lag1']:.3f}{tail}")
    print(f"\nsaved {OUT}\nsaved {p}")


if __name__ == "__main__":
    main()
