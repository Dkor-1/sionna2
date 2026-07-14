# -*- coding: utf-8 -*-
"""
viz_bistatic.py — (report4) **챔버 드로잉 헬퍼 + 옛 손합성 기준선**
====================================================================
⚠ **이 모듈은 더 이상 report4 의 그림을 만들지 않는다.** report4 의 모든 그림은
`src/viz_report4.py` 가 만든다 (Sionna RT 환경경로 + SBR σ + Sionna PHY 신호합성 + Sionna 렌더).

여기 남은 것은 두 가지뿐이다:
  1. **챔버 드로잉 헬퍼** — `benchmark/run_matrix.py`(report5) 가 import 한다. 건드리지 말 것.
  2. **옛 손합성 CPI** (`legacy_cpi`) — Sionna PHY 체인의 **대조군**. `viz_report4.crosscheck()` 가
     이걸로 상관 1.0000 을 확인한다.

■ 왜 갈아엎었나 — 옛 report4 는 두 군데가 틀렸다
  ① **물리 근거가 없었다**: 감시신호를 `make_cpi(a_tgt=1.0, dpi_amp=55.0, snr_db=14.0)` 로 합성했다.
     이 셋은 **손으로 박은 값**이다 — 표적 RCS 도, 링크버짓도, 실제 챔버 경로도 들어가 있지 않다.
     지금은 σ=SBR(가림 포함), 절대전력=link_budget(EIRP·kTB), 환경경로=Sionna RT 실측이다.
  ② **서사가 거짓이었다**: "무반사 챔버라 클러터가 약하다 → 주된 방해는 직접파뿐".
     · 챔버는 **semi-anechoic** 이다 — 벽4면+천장만 흡수체, **바닥은 반사성 콘크리트**(chamber.py).
     · 클러터는 약하지도 않다 — **Sionna RT 실측 최강 −9.8 dB**, 바닥 반사 19.3 ns / −14.7 dB
       (프레넬 예측과 0.1 dB 내 일치). 아래 CH_CLUTTER 가정(−25~−30 dB)보다 11~16 dB 세다.
     · 그런데도 **어떤 수치도 안 틀렸다** — 정적 클러터가 이 하네스에서 **죽은 파라미터**이기
       때문이다. ECA 의 기저가 정확히 '지연된 기준신호'라 사영이 **진폭과 무관하게 0 으로** 지운다
       (직접파보다 14 dB 센 클러터를 넣어도 SCR 이 1.5e-9 dB 움직인다).
     · **진짜 위협은 표적을 경유한 바닥 유령**(TX→표적→바닥→RX)이다. 표적과 함께 **도플러가 실려**
       ECA 의 영공간 밖 → 지워지지 않고 **가짜 표적**으로 남는다. 옛 모델엔 이게 **아예 없었다**.
       → report4 의 새 헤드라인. `viz_report4.fig_ghost()` 참조.
"""
from __future__ import annotations
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

# 챔버 배치 상수(TX/RX/TGT/VEL)의 단일 출처는 bistatic_scene.py
from bistatic_scene import bistatic_params, C0, CHAMBER, TX, RX, TGT, VEL  # noqa: F401


def _scaled_mesh(mesh, target_extent, center):
    """메쉬를 target_extent 크기로 스케일해 center 에 놓는다 (3D 도식용 확대)."""
    V = np.array(mesh.v); b0, b1 = V.min(0), V.max(0); c = (b0 + b1) / 2
    s = target_extent / max((b1 - b0).max(), 1e-9)
    return (V - c) * s + np.asarray(center)


def _draw_chamber(ax, W, D, H):
    """3D 축에 챔버(상자)를 그린다 — 바닥 격자 + 12모서리 + 반투명 벽 + 흡수체 힌트.
    ※ 바닥은 **반사성 콘크리트**다(흡수체가 아니다) — semi-anechoic."""
    ax.plot_surface(np.array([[0, W], [0, W]]), np.array([[0, 0], [D, D]]),
                    np.zeros((2, 2)), color="0.80", alpha=0.6, zorder=0, shade=False)
    for gx in range(0, int(W) + 1, 5):
        ax.plot([gx, gx], [0, D], [0, 0], color="0.65", lw=0.4)
    for gy in range(0, int(D) + 1, 5):
        ax.plot([0, W], [gy, gy], [0, 0], color="0.65", lw=0.4)
    c = np.array([[x, y, z] for x in (0, W) for y in (0, D) for z in (0, H)])
    E = [(0,1),(2,3),(4,5),(6,7),(0,2),(1,3),(4,6),(5,7),(0,4),(1,5),(2,6),(3,7)]
    ax.add_collection3d(Line3DCollection([[c[a], c[b]] for a, b in E],
                                         colors="0.6", linewidths=0.8))
    walls = [
        [[W,0,0],[W,D,0],[W,D,H],[W,0,H]],
        [[0,0,0],[W,0,0],[W,0,H],[0,0,H]],
        [[0,D,0],[W,D,0],[W,D,H],[0,D,H]],
    ]
    ax.add_collection3d(Poly3DCollection(walls, facecolors="#e8eef5", edgecolors="none", alpha=0.10))
    for yy in np.linspace(2, D - 2, 6):
        for zz in np.linspace(1.5, H - 1.5, 4):
            ax.plot([W, W - 0.7], [yy, yy], [zz, zz], color="#b7c4d6", lw=0.6)
    ax.text(W * 0.5, D * 0.5, H + 0.6, "Semi-anechoic chamber 30x20x11 m\n(walls+ceiling absorber, FLOOR reflective)",
            color="0.4", fontsize=8, ha="center")


def _draw_chamber_plan(ax, W, D):
    """평면도에 챔버 바닥 사각형 + 4면 흡수체 라이닝 힌트."""
    ax.add_patch(plt.Rectangle((0, 0), W, D, facecolor="#e4e0da", edgecolor="none", zorder=0))
    ax.add_patch(plt.Rectangle((0, 0), W, D, fill=False, edgecolor="0.5", lw=1.4))
    for yy in np.linspace(1, D - 1, 12):
        ax.plot([0, 0.5], [yy, yy], color="#c2ccdb", lw=0.6)
        ax.plot([W, W - 0.5], [yy, yy], color="#c2ccdb", lw=0.6)
    for xx in np.linspace(1, W - 1, 16):
        ax.plot([xx, xx], [0, 0.5], color="#c2ccdb", lw=0.6)
        ax.plot([xx, xx], [D, D - 0.5], color="#c2ccdb", lw=0.6)


def _trajectory(n_frames, speed=4.0):
    """챔버 quiet zone 을 가로지르는 2차 베지어 비행경로 → (pos[n,3], vel[n,3])."""
    P0 = np.array([16.0, 5.0, 6.0]); C = np.array([25.0, 10.0, 5.0]); P1 = np.array([18.0, 15.0, 6.5])
    t = np.linspace(0, 1, n_frames)[:, None]
    pos = (1 - t)**2 * P0 + 2 * (1 - t) * t * C + t**2 * P1
    dpos = 2 * (1 - t) * (C - P0) + 2 * t * (P1 - C)
    vel = dpos / (np.linalg.norm(dpos, axis=1, keepdims=True) + 1e-9) * speed
    return pos, vel


def legacy_cpi(ref_frame, M, fs, tau_s, fd_hz, a_tgt, **kw):
    """**옛 손합성 CPI** (passive_process.make_cpi) — Sionna PHY 체인의 대조군.
    `viz_report4.apply_cpi()` 가 같은 (a, τ) 에서 이것과 상관 1.0000 을 내야 한다."""
    from passive_process import make_cpi
    return make_cpi(ref_frame, M, fs, tau_s, fd_hz, a_tgt=a_tgt, **kw)


if __name__ == "__main__":
    p = bistatic_params(TX, RX, TGT, VEL, 3.5e9)
    print("viz_bistatic 는 이제 헬퍼 모듈입니다. report4 그림은 src/viz_report4.py 가 만듭니다.")
    print(f"  챔버 배치: L={p['L']:.1f}m  Rb={p['Rb']:.2f}m  f_d={p['fd']:+.0f}Hz  beta={p['beta']:.0f}deg")
