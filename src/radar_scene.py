# -*- coding: utf-8 -*-
"""
radar_scene.py — (report2) 모노스태틱 레이더 장면 + 채널 추출
=============================================================

report1 에서 만든 차폐시설 + 드론을 그대로 가져와, **모노스태틱 레이더**를 구성한다.

구성 개념
  * 안테나(송신 TX ≈ 수신 RX, 같은 쪽)를 챔버 한쪽 끝에 둔다.
  * 표적 드론을 반대쪽 '조용한 영역(quiet zone)' 중앙에 둔다 → 거리 R 최대 확보.
  * Sionna 광선추적으로 TX→표적→RX 경로(에코)를 얻는다.
  * 표적 있을 때 / 없을 때를 각각 풀어 **배경 차감**으로 순수 표적 산란만 남긴다.

원거리장(far-field) 점검
  RCS 는 R ≥ 2D²/λ 에서만 정의. farfield_distance() 로 (드론×주파수) 조합을 점검한다.
  (거대한 S1000+ 는 고주파에서 30 m 챔버 안 far-field 가 안 됨 → 명시)

이 파일은 '파형(WiFi/LTE/5G)'과 무관한 장면/채널 부분만 담당한다.
파형 합성·정합필터·RCS 비교는 별도 모듈(waveforms.py, radar_process.py)에서.
"""
from __future__ import annotations

import os
import math
import numpy as np

import mitsuba as mi
import sionna.rt as rt

from scene_build import build_scene, chamber_parts, drone_parts
from drones import DRONES

C0 = 299792458.0
_HERE = os.path.dirname(os.path.abspath(__file__))
CMESH = os.path.abspath(os.path.join(_HERE, "..", "assets", "meshes", "chamber"))
DMESH = os.path.abspath(os.path.join(_HERE, "..", "assets", "meshes", "drones"))

# 챔버 x∈[0,30]. 안테나는 한쪽 끝, 표적은 quiet zone.
# 거리 R=10 m: 작은 드론 4종은 far-field(2~7 m) 만족 + 광선이 표적을 충분히 맞힘.
# (22 m 처럼 너무 멀면 작은 표적에 광선이 거의 안 닿아 에코를 못 찾음)
ANT_POS = (2.0, 10.0, 5.5)
TGT_POS = (12.0, 10.0, 5.5)
RX_OFFSET = 0.3                         # 준-모노스태틱: 송수신 안테나 간격 [m]


def farfield_distance(D_m: float, fc: float) -> float:
    """원거리장 시작거리 2D²/λ [m]."""
    return 2.0 * D_m * D_m / (C0 / fc)


def target_extent(target_key: str) -> float:
    """표적의 최대 수평 크기 D [m] (프로펠러 포함 스팬)."""
    from drones import build_drone
    b0, b1 = build_drone(DRONES[target_key]).bounds()
    return float(max(b1[0] - b0[0], b1[1] - b0[1]))


def build_monostatic_scene(target_key: str | None, fc: float = 3.5e9,
                           yaw_deg: float = 0.0, tgt_pos=TGT_POS, ant_pos=ANT_POS,
                           directional=True, with_chamber=False):
    """모노스태틱 장면을 만든다.
    target_key=None  → 표적 없는 장면(배경 차감용).
    with_chamber=False → 자유공간(깨끗한 RCS 측정). True → 챔버 벽 포함(클러터 평가용).
    """
    parts = []
    if with_chamber:
        cparts, info = chamber_parts(CMESH, cutaway=False)
        parts += cparts
    else:
        info = dict(W=30.0, D=20.0, H=11.0)
    if target_key is not None:
        dp, _ = drone_parts(DRONES[target_key], position=tgt_pos, yaw_deg=yaw_deg,
                            mesh_dir=os.path.join(DMESH, target_key))
        parts += dp
    scene = build_scene(parts, fc=fc)

    # 지향성 안테나(tr38901, 3GPP 소자패턴) 1소자 — quiet zone 으로 조준.
    pat = "tr38901" if directional else "iso"
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern=pat, polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern=pat, polarization="V")
    tx = rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in ant_pos]))
    rx_pos = (ant_pos[0], ant_pos[1] + RX_OFFSET, ant_pos[2])
    rx = rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in rx_pos]))
    scene.add(tx); scene.add(rx)
    tx.look_at(mi.Point3f(*[float(v) for v in tgt_pos]))
    rx.look_at(mi.Point3f(*[float(v) for v in tgt_pos]))
    return scene, info


def solve_paths(scene, spp=2_000_000, max_depth=2):
    return rt.PathSolver()(scene, max_depth=max_depth, los=True,
                           specular_reflection=True, diffuse_reflection=True,
                           refraction=False, samples_per_src=spp, seed=1)


def paths_arrays(paths):
    """경로별 (복소이득 a[P], 지연 tau[P], 도플러 dop[P], 정점 V[depth,P,3],
    상호작용 inter[depth,P]). 단일 송수신 안테나(1×1) 가정."""
    ar = np.asarray(paths.a[0]); ai = np.asarray(paths.a[1])
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]          # (P,)
    P = a.shape[0]
    tau = np.asarray(paths.tau).reshape(-1, P)[0]            # (P,)
    dop = np.asarray(paths.doppler).reshape(-1)
    dop = dop[:P] if dop.shape[0] >= P else np.zeros(P)
    V = np.asarray(paths.vertices)[:, 0, 0, :, :]            # (depth,P,3)
    inter = np.asarray(paths.interactions)[:, 0, 0, :]       # (depth,P)
    return a, tau, dop, V, inter


def target_echo_paths(paths, tgt_pos=TGT_POS, radius=2.0):
    """표적 근처에서 실제로 상호작용한 경로만 골라 (a, tau, dop) 를 돌려준다 (= 에코).
    interactions != 0 인 정점만 '진짜 상호작용'으로 본다(LOS 빈 정점 제외)."""
    a, tau, dop, V, inter = paths_arrays(paths)
    tgt = np.array(tgt_pos, float)
    depth, P = inter.shape
    keep = np.zeros(P, bool)
    for d in range(depth):
        present = inter[d] != 0
        dist = np.linalg.norm(V[d] - tgt, axis=-1)
        keep |= present & (dist < radius)
    return a[keep], tau[keep], dop[keep]


def channel_freqresp(a, tau, freqs):
    """경로합으로 채널 주파수응답 H(f) = Σ aₚ·exp(-j2πf·τₚ)."""
    a = np.asarray(a).reshape(-1); tau = np.asarray(tau).reshape(-1)
    f = np.asarray(freqs).reshape(-1, 1)
    return (a.reshape(1, -1) * np.exp(-1j * 2 * np.pi * f * tau.reshape(1, -1))).sum(axis=1)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", default="phantom4")
    ap.add_argument("--fc", type=float, default=3.5e9)
    ap.add_argument("--spp", type=int, default=1_000_000)
    args = ap.parse_args()

    R = math.dist(ANT_POS, TGT_POS)
    print(f"안테나-표적 거리 R = {R:.1f} m,  왕복지연 ≈ {2*R/C0*1e9:.1f} ns")
    print("== 원거리장 점검 (2D²/λ) ==")
    for k in DRONES:
        D = target_extent(k); rff = farfield_distance(D, args.fc)
        ok = "OK" if rff <= R else "✗ (챔버 부족)"
        print(f"  {k:10s} D={D:.2f} m  R_ff={rff:5.1f} m  @ {args.fc/1e9:.1f}GHz  {ok}")

    scene, info = build_monostatic_scene(args.drone, fc=args.fc)
    paths = solve_paths(scene, spp=args.spp)
    a, tau, dop = target_echo_paths(paths)
    print(f"\n표적({args.drone}) 에코 경로 수: {len(tau)}")
    if len(tau):
        t0 = float(np.min(tau))
        print(f"  최단 에코 지연 = {t0*1e9:.1f} ns  (이론 왕복 {2*R/C0*1e9:.1f} ns)")
        print(f"  에코 합 전력(상대) = {10*np.log10(np.sum(np.abs(a)**2)+1e-30):.1f} dB")
