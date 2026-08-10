# -*- coding: utf-8 -*-
"""
build_three_engine_fig.py — 세 엔진의 마이크로도플러 맵을 나란히 놓는다.

⭐ 이 그림이 답하는 것: **우리 맵이 맞는가.**
   지금까지는 대조군이 없어 «근본적으로 잘못됐다» 는 의심을 확인할 방법이 없었다.
   세 엔진을 **같은 슬로타임 격자**(같은 기체·자세·주파수·PRF·로터별 rpm)에 태웠으므로,
   f_tip 아래에서 셋이 같은 능선을 내면 우리 맵이 맞고, 한쪽만 다르면 그쪽이 틀린 것이다.

   ① Sionna PathSolver — h = Σ a_p·exp(−j2πf_c·τ_p)   (WiFi-JEPA 가 쓰는 자리)
   ② 우리 SBR          — 광선 격자 + 가림 + 각도의존 Γ
   ③ 우리 순수 PO      — 가림 없음, 점구름 면적분

⚠ 레벨은 엔진마다 규약이 다르다(Sionna 는 우리보다 60 dB 낮다 — 경로 10~13개 대
  광선 격자 수만 개). 그래서 **각 패널을 자기 최대로 정규화**하고 레벨 차는 제목에 적는다.
  이 그림이 묻는 것은 레벨이 아니라 **무늬**다.

읽는 것: outputs/report07_three_engines.{npz,json}
쓰는 것: outputs/figures/report07_f5.{png,pdf}
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram as _spec

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

J = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))
Z = np.load(f"{ROOT}/outputs/report07_three_engines.npz")
FIGDIR = f"{ROOT}/outputs/figures"
M = J["_meta"]
PRF, FTIP, FFL = M["prf_hz"], M["f_tip_hz"], M["f_flash_hz"]

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})


from md_mapstyle import flash_spec, auto_periods, draw                       # noqa: E402


def spec_of(E):
    """⭐플래시 해상도 규약(md_mapstyle) — 모든 맵이 같은 설정을 쓴다."""
    return flash_spec(E, PRF, FFL, auto_periods(PRF, FFL))


# ⭐ 라벨 정정(2026-08-07) — «SBR 커널 / PO 커널» 이 별개 물리처럼 읽혔다.
#   산란식은 둘 다 PO 다. 차이는 **어느 면을 셈에 넣느냐** 뿐이다:
#     기본(SBR+PO)  광선이 보이는 면을 고르고 그 면에 PO      ← 가림 O
#     대조(w/o occ) 법선만 보고 모든 면에 PO                  ← 가림 X
ARMS = [("sionna", "Sionna PathSolver"),
        ("sbr", "Ours (SBR+PO, default)"),
        ("po", "Ours, nothing blocked (control)")]
got = [(k, ttl) + spec_of(Z[k]) for k, ttl in ARMS]
ref = max(J["levels_db"].values())

fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.9), sharey=True)
for ax, (k, ttl, f, t, S, nper) in zip(axes, got):
    m = draw(ax, t, f, S, FTIP)
    ax.set_title(f"{ttl}\n{J['ptp_db'][k]:.1f} dB p-p  ·  level "
                 f"{J['levels_db'][k] - ref:+.0f} dB vs strongest", fontsize=FS)
    ax.set_xlabel("Time [ms]")
axes[0].set_ylabel("Doppler [Hz]")
fig.colorbar(m, ax=axes, pad=0.012).set_label(
    "Magnitude, each panel to its own peak [dB]", fontsize=FS)
fig.suptitle(f"{M['name']} — hovering, belly view (az {M['az_deg']:.0f}, el {M['el_deg']:.0f}), "
             f"{M['fc_hz']/1e9:.1f} GHz.   Same slow-time grid for all three engines.",
             fontsize=FS + 0.5, y=1.10)
# 설정 수치는 그림에 안 적는다 — 리포트의 «표시 규약» 절이 담는다.
for ext in ("png", "pdf"):
    fig.savefig(f"{FIGDIR}/report07_f5.{ext}", bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"  ✅ outputs/figures/report07_f5.png")

# ── 판정 — 무늬가 같은가 (레벨을 빼고 스펙트럼 모양만) ───────────────────────
print("\n═══ ⭐판정: f_tip 안에서 세 엔진의 스펙트럼 모양이 같은가 ═══")
shapes = {}
for k, _ in ARMS:
    E = np.asarray(Z[k], complex)
    E = E - E.mean()
    S = np.abs(np.fft.fftshift(np.fft.fft(E * np.hanning(len(E)))))
    f = np.fft.fftshift(np.fft.fftfreq(len(E), 1 / PRF))
    inb = np.abs(f) <= FTIP
    shapes[k] = S[inb] / (np.linalg.norm(S[inb]) + 1e-30)
for i, (a, _) in enumerate(ARMS):
    for b, _ in ARMS[i + 1:]:
        print(f"  {a:7s} ↔ {b:7s}  스펙트럼 코사인 {float(shapes[a] @ shapes[b]):.4f}")
out = {"cosine_in_ftip": {f"{a}_vs_{b}": float(shapes[a] @ shapes[b])
                          for i, (a, _) in enumerate(ARMS) for b, _ in ARMS[i + 1:]},
       "note_ko": "1 에 가까우면 세 엔진이 같은 무늬를 낸다 = 우리 맵이 맞다"}
J["verdict"] = out
json.dump(J, open(f"{ROOT}/outputs/report07_three_engines.json", "w"),
          ensure_ascii=False, indent=1)
