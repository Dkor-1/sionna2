# -*- coding: utf-8 -*-
"""
scenarios.py — (benchmark) 드론 모션 시나리오 (통제 축 C)
========================================================
**한 번 정의해 모든 신호·드론에 동일하게 재사용** → 공정한 통제 축.
각 함수: 고정 기하(tx, rx)와 중심 center 기준으로 positions[n,3], velocities[n,3] 반환.
스케일은 speed·span 파라미터로 준다(기본값 = geometry.SPEED/SPAN, 챔버 실내 스케일).

난이도(도플러 관점 — 0-도플러 클러터/직접파 능선과의 거리):
  radial     : 바이스태틱 이등분선 따라 접근/후퇴 → 최대 radial 도플러 → **가장 쉬움**
  tangential : 시선(이등분선)에 수직 횡단 → 저 radial 도플러 → 능선 근처 → **어려움**
  hover      : 정지 → 도플러≈0 → 능선 위 → bulk-only 로 사실상 blind(**예상된 난제**;
               여기가 훗날 프로펠러 마이크로도플러 레이어가 필요한 지점 = report3)
  waypoint   : 프로그램된 꺾임 경로 → 도플러 부호·크기 변동(검출 연속성 시험)
"""
from __future__ import annotations

import numpy as np

# 챔버 실내 스케일 기본값 — geometry.py 가 단일 출처(여기서 재export해 기존 사용처 유지).
# (geometry 는 scenarios 를 import 하지 않으므로 순환 없음.)
from geometry import SPEED, SPAN


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def hover(tx, rx, center, n=32, **_):
    pos = np.tile(np.asarray(center, float), (n, 1))
    vel = np.zeros((n, 3))
    return pos, vel


def radial(tx, rx, center, speed=SPEED, span=SPAN, n=32, approach=True, **_):
    """바이스태틱 이등분선 방향으로 접근/후퇴. center 중심 ±span/2 구간."""
    c = np.asarray(center, float)
    u1 = _unit(np.asarray(tx, float) - c)                # 표적→TX
    u2 = _unit(np.asarray(rx, float) - c)                # 표적→RX
    d = _unit(u1 + u2)                                   # 이등분선(표적→'레이더쪽')
    if not approach:
        d = -d
    t = np.linspace(-0.5, 0.5, n)[:, None]
    pos = c + d * t * span                               # t=-0.5 레이더 반대쪽 멀리 → t=+0.5 가까이(접근; vel=+d 와 일치)
    vel = np.tile(d * speed, (n, 1))
    return pos, vel


def tangential(tx, rx, center, speed=SPEED, span=SPAN, n=32, **_):
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


def waypoint(tx, rx, center, speed=SPEED, span=SPAN, n=48, **_):
    """quiet zone 을 가로지르는 'ㄴ'자 베지어 경로 → 도플러 부호가 변함.
    꺾임점 오프셋을 span 에 비례시켜 챔버 안에 들어오게 한다(실외 하드코딩 제거).
    스냅샷을 **호길이 균등**으로 재샘플링해 |Δpos|/Δt 가 speed 와 일치(등속 비행)하게 한다
    — 균등 t 샘플이면 베지어 곡률 때문에 위치 간격과 속도 크기가 어긋난다."""
    c = np.asarray(center, float)
    P0 = c + span * np.array([-0.5, 0.5, 0.0])
    ctrl = c + span * np.array([-0.1, -0.1, 0.05])
    P1 = c + span * np.array([0.55, -0.3, -0.07])
    tf = np.linspace(0, 1, 20 * n)[:, None]                  # 촘촘한 t → 호길이 표
    pf = (1 - tf) ** 2 * P0 + 2 * (1 - tf) * tf * ctrl + tf ** 2 * P1
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pf, axis=0), axis=1))])
    t = np.interp(np.linspace(0, s[-1], n), s, tf[:, 0])[:, None]   # 호길이 균등 t
    pos = (1 - t) ** 2 * P0 + 2 * (1 - t) * t * ctrl + t ** 2 * P1
    d = 2 * (1 - t) * (ctrl - P0) + 2 * t * (P1 - ctrl)
    vel = d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-9) * speed
    return pos, vel


SCENARIOS = {"hover": hover, "radial": radial,
             "tangential": tangential, "waypoint": waypoint}


if __name__ == "__main__":
    from geometry import TX, RX, CENTER, CHAMBER
    W, D, H = CHAMBER
    print(f"챔버 {CHAMBER}  TX={TX} RX={RX}  center={CENTER}")
    for name, fn in SCENARIOS.items():
        pos, vel = fn(TX, RX, CENTER)
        sp = np.linalg.norm(vel, axis=1)
        inside = (pos[:, 0].min() >= 0 and pos[:, 0].max() <= W and
                  pos[:, 1].min() >= 0 and pos[:, 1].max() <= D and
                  pos[:, 2].min() >= 0 and pos[:, 2].max() <= H)
        print(f"  {name:11s} n={len(pos):2d}  속도 {sp.min():.1f}~{sp.max():.1f} m/s  "
              f"x[{pos[:,0].min():.1f},{pos[:,0].max():.1f}] "
              f"y[{pos[:,1].min():.1f},{pos[:,1].max():.1f}] "
              f"z[{pos[:,2].min():.1f},{pos[:,2].max():.1f}]  챔버안={inside}")
