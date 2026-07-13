# -*- coding: utf-8 -*-
"""
scenarios.py — (benchmark) 드론 모션 시나리오 (통제 축 C)
========================================================
**한 번 정의해 모든 신호·드론에 동일하게 재사용** → 공정한 통제 축(EXPERIMENT_SPEC §6).
각 함수: 고정 기하(tx, rx)와 중심 center 기준으로 positions[n,3], velocities[n,3] 반환.

난이도(도플러 관점 — 0-도플러 클러터 능선과의 거리):
  radial     : 바이스태틱 이등분선 따라 접근/후퇴 → 최대 radial 도플러 → **가장 쉬움**
  tangential : 시선(이등분선)에 수직 횡단 → 저 radial 도플러 → 능선 근처 → **어려움**
  hover      : 정지 → 도플러≈0 → 능선 위 → bulk-only 로 사실상 blind(**예상된 난제**;
               여기가 훗날 프로펠러 마이크로도플러 레이어가 필요한 지점 = report3)
  waypoint   : 프로그램된 꺾임 경로 → 도플러 부호·크기 변동(검출 연속성 시험)
"""
from __future__ import annotations

import numpy as np


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def hover(tx, rx, center, n=32, **_):
    pos = np.tile(np.asarray(center, float), (n, 1))
    vel = np.zeros((n, 3))
    return pos, vel


def radial(tx, rx, center, speed=12.0, span=60.0, n=32, approach=True, **_):
    """바이스태틱 이등분선 방향으로 접근/후퇴. center 중심 ±span/2 구간."""
    c = np.asarray(center, float)
    u1 = _unit(np.asarray(tx, float) - c)                # 표적→TX
    u2 = _unit(np.asarray(rx, float) - c)                # 표적→RX
    d = _unit(u1 + u2)                                   # 이등분선(표적→'레이더쪽')
    if not approach:
        d = -d
    t = np.linspace(-0.5, 0.5, n)[:, None]
    pos = c + (-d) * t * span                            # 시작 멀리 → 가까이(접근)
    vel = np.tile(d * speed, (n, 1))
    return pos, vel


def tangential(tx, rx, center, speed=12.0, span=60.0, n=32, **_):
    """시선(이등분선)에 수직으로 횡단 → radial 도플러 작음(능선 근처)."""
    c = np.asarray(center, float)
    u1 = _unit(np.asarray(tx, float) - c)
    u2 = _unit(np.asarray(rx, float) - c)
    look = _unit(u1 + u2)
    horiz = _unit(np.cross(look, [0, 0, 1.0]))           # 수평면 내, 시선에 수직
    t = np.linspace(-0.5, 0.5, n)[:, None]
    pos = c + horiz * t * span
    vel = np.tile(horiz * speed, (n, 1))
    return pos, vel


def waypoint(tx, rx, center, speed=12.0, n=48, **_):
    """감시영역을 가로지르는 'ㄴ'자 베지어 경로 → 도플러 부호가 변함."""
    c = np.asarray(center, float)
    P0 = c + np.array([-30, 30, 0.0])
    C = c + np.array([-6, -6, 3.0])
    P1 = c + np.array([35, -18, -4.0])
    t = np.linspace(0, 1, n)[:, None]
    pos = (1 - t) ** 2 * P0 + 2 * (1 - t) * t * C + t ** 2 * P1
    d = 2 * (1 - t) * (C - P0) + 2 * t * (P1 - C)
    vel = d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-9) * speed
    return pos, vel


SCENARIOS = {"hover": hover, "radial": radial,
             "tangential": tangential, "waypoint": waypoint}


if __name__ == "__main__":
    TX = (0.0, 250.0, 35.0); RX = (0.0, 0.0, 6.0); C = (180.0, 220.0, 60.0)
    for name, fn in SCENARIOS.items():
        pos, vel = fn(TX, RX, C)
        sp = np.linalg.norm(vel, axis=1)
        print(f"{name:11s} n={len(pos):2d}  속도 {sp.min():.1f}~{sp.max():.1f} m/s  "
              f"위치범위 x[{pos[:,0].min():.0f},{pos[:,0].max():.0f}] "
              f"y[{pos[:,1].min():.0f},{pos[:,1].max():.0f}]")
