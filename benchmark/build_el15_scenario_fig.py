# -*- coding: utf-8 -*-
"""
build_el15_scenario_fig.py — ⭐리포트 16 재설계판의 «실험 시나리오» 그림을 조립한다.

왜
--
사용자 지시: *"16번 레포트에 실험 시나리오도 시오나 렌더링을 토대로 그려줘."*

`render_el15_scene.py` 가 낸 **Sionna 렌더**를 재료로, 기하 도식과 앙각별 시선을
한 장에 세운다. 렌더만으로는 «어느 자리에서 보는가» 가 안 읽히고(15 m 씬에서
드론은 점이다), 도식만으로는 «무엇이 보이는가» 가 안 읽힌다 — 둘을 붙인다.

무엇이 보이나
    위  15 m 구면 위 앙각 7 점의 기하 (도식) — 거리·경계·방위가 숫자로
    아래 그 7 자리에서 **레이더가 실제로 보는 드론** (Sionna 렌더)
         · el 0°  로터를 옆에서 봐 블레이드가 선으로 보인다
         · el −90° 로터 원반이 열리고 **동체가 가운데를 덮는다**
           → 조각 78 «메쉬를 통째로 넣은 대가» 의 두 몫이 그림으로 갈린다

⭐집 규약 — 그림 안 글자는 **전부 영어**다(기억 `sionna2-viz-english`).

    PYTHONPATH=src:benchmark python benchmark/build_el15_scenario_fig.py
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                     # noqa: E402
from matplotlib.patches import Arc, FancyArrowPatch                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIGDIR = os.path.join(ROOT, "outputs", "figures")

ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
RNG = 15.0
#: ⭐집 규약 — 숫자는 원장에서 주입한다. 새 15 m 원장이 아직 없으면(스윕 진행 중)
#:   아래 대체값을 쓰고, 그 사실을 그림 우상단에 «ledger pending» 으로 밝힌다.
FF_BOUND_FB = 14.076       # 2D²/λ · D = 메쉬 3D 대각 0.7764 m · λ = 85.65 mm
FTIP0_FB = 1272.9          # el 0° 의 날개끝 주파수 [Hz]
LEDGER = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")


def from_ledger():
    """새 원장이 있으면 경계·f_tip 을 거기서 읽는다 → (ff, ftip0, 출처문구)."""
    import json
    try:
        d = json.load(open(LEDGER, encoding="utf-8"))
    except Exception:
        return FF_BOUND_FB, FTIP0_FB, "ledger pending — values from part 78"
    m = d.get("_meta", {})
    if abs(float(m.get("range_m", 0)) - RNG) > 1e-6:
        return FF_BOUND_FB, FTIP0_FB, "ledger pending — values from part 78"
    ff = float(m.get("farfield_boundary_m", FF_BOUND_FB))
    ft = FTIP0_FB
    for r in (d.get("rows") or []):
        if abs(float(r.get("el_deg", 9))) < 1e-6 and r.get("f_tip_hz"):
            ft = float(r["f_tip_hz"]); break
    return ff, ft, "elevation_sweep_md.json"
C_ARC, C_PT, C_TGT = "#7f8c9a", "#5b8def", "#e8913a"


def crop_white(a, pad=6):
    """렌더의 흰 여백을 잘라낸다 — 타일에 붙일 때 드론이 커 보이게."""
    g = a[..., :3].mean(axis=2) if a.ndim == 3 else a
    m = g < 0.985
    if not m.any():
        return a
    ys, xs = np.where(m)
    y0, y1 = max(0, ys.min() - pad), min(a.shape[0], ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(a.shape[1], xs.max() + pad + 1)
    return a[y0:y1, x0:x1]


def main():
    FF_BOUND, FTIP0, SRC = from_ledger()
    print(f"  · 원장 출처: {SRC}  (경계 {FF_BOUND:.3f} m · f_tip@0° {FTIP0:.1f} Hz)")
    fig = plt.figure(figsize=(15.0, 7.4), dpi=170)
    gs = fig.add_gridspec(2, 7, height_ratios=[1.02, 1.0],
                          hspace=0.13, wspace=0.030,
                          left=0.030, right=0.988, top=0.905, bottom=0.055)

    # ── 위: 기하 도식 ──────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, :])
    ax.set_aspect("equal")
    th = np.radians(np.linspace(-90, 0, 200))
    ax.plot(RNG * np.cos(th), RNG * np.sin(th), color=C_ARC, lw=1.3, zorder=1)
    th2 = np.radians(np.linspace(-90, 0, 200))
    ax.plot(FF_BOUND * np.cos(th2), FF_BOUND * np.sin(th2), color="#c0392b",
            lw=1.0, ls=(0, (5, 4)), zorder=1)
    # ⚠라벨을 호 위에 얹으면 앙각 라벨과 겹친다(−30° 자리) — 범례로 뺀다.

    for el in ELS:
        a = np.radians(el)
        x, y = RNG * np.cos(a), RNG * np.sin(a)
        ax.plot([0, x], [0, y], color=C_ARC, lw=0.7, alpha=0.55, zorder=1)
        ax.plot([x], [y], "o", ms=8.5, color=C_PT, zorder=3)
        lx, ly = 1.115 * x, 1.115 * y
        lab = "0°" if el == 0 else f"−{abs(el):.0f}°"   # 제목과 같은 유니코드 −
        ax.text(lx, ly, lab, fontsize=9.6, color=C_PT,
                ha="left" if el > -70 else "center",
                va="center" if el > -70 else "top", zorder=3)

    ax.plot([0], [0], "*", ms=19, color=C_TGT, zorder=4)
    ax.annotate("", xy=(RNG * np.cos(np.radians(-52)), RNG * np.sin(np.radians(-52))),
                xytext=(0, 0),
                arrowprops=dict(arrowstyle="<->", color="#444", lw=1.0))
    ax.text(0.52 * RNG * np.cos(np.radians(-52)) - 1.5,
            0.52 * RNG * np.sin(np.radians(-52)) + 0.35,
            f"R = {RNG:.0f} m", fontsize=10.2, color="#222",
            ha="center", va="bottom", rotation=-52)

    # 범례 — 호 라벨과 겹치지 않는 좌측 여백에 세운다
    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], marker="*", ls="none", ms=13, color=C_TGT,
               label="target — DJI Matrice 4E (hover)"),
        Line2D([], [], marker="o", ls="none", ms=7.5, color=C_PT,
               label="TX = RX (monostatic, baseline 0)"),
        Line2D([], [], color=C_ARC, lw=1.4,
               label=f"measurement sphere, R = {RNG:.0f} m"),
        Line2D([], [], color="#c0392b", lw=1.2, ls=(0, (5, 4)),
               label=f"far-field boundary  2D²/λ = {FF_BOUND:.2f} m"),
    ]
    # ⚠aspect="equal" 이라 축 상자와 실제 데이터 영역이 어긋난다 —
    #   축 좌표로 두면 호 위에 얹힌다. **그림 좌표**로 왼쪽 여백에 박는다.
    fig.legend(handles=handles, loc="upper left", fontsize=9.2,
               frameon=False, bbox_to_anchor=(0.035, 0.845),
               bbox_transform=fig.transFigure)

    ax.set_xlim(-6.0, RNG * 1.19)
    ax.set_ylim(-RNG * 1.14, 2.6)
    ax.axis("off")
    ax.set_title("Monostatic TX = RX on a 15 m sphere, azimuth 0°, "
                 "elevation swept 0° → −90°",
                 fontsize=11.6, pad=6)

    # ── 아래: 앙각별 Sionna 렌더 ───────────────────────────────────────────
    for k, el in enumerate(ELS):
        axi = fig.add_subplot(gs[1, k])
        p = os.path.join(FIGDIR, f"el15_view_el{el:+03.0f}.png")
        if os.path.exists(p):
            axi.imshow(crop_white(plt.imread(p)))
        else:
            axi.text(0.5, 0.5, "missing", ha="center", va="center",
                     transform=axi.transAxes, fontsize=9)
        axi.set_xticks([]); axi.set_yticks([])
        for s in axi.spines.values():
            s.set_edgecolor("#d7dde3")
        ft = FTIP0 * np.cos(np.radians(el))
        lab = "0°" if el == 0 else f"−{abs(el):.0f}°"
        axi.set_title(f"el {lab}", fontsize=10.4, color=C_PT, pad=3)
        axi.set_xlabel(f"$f_{{tip}}$ = {ft:.0f} Hz", fontsize=8.8, labelpad=2)

    fig.text(0.035, 0.955,
             "Experiment scenario — what the radar sees at each elevation",
             fontsize=13.4, fontweight="bold", va="bottom")
    fig.text(0.985, 0.955,
             "Sionna RT render · 8,192 poses · 4,000M rays · all physics on · "
             f"max_depth 1 & 2   |   source: {SRC}",
             fontsize=8.8, color="#5a6570", ha="right", va="bottom")

    out = os.path.join(FIGDIR, "el15_scenario.png")
    fig.savefig(out, dpi=170, facecolor="white")
    print(f"  ✅ {os.path.relpath(out, ROOT)}")
    print(f"     아래 줄 좌→우: el {ELS[0]:+.0f}° (rotors edge-on) → "
          f"el {ELS[-1]:+.0f}° (rotor disks open, body covers centre)")


if __name__ == "__main__":
    main()
