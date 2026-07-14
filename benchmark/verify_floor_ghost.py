# -*- coding: utf-8 -*-
"""
verify_floor_ghost.py — 챔버 바닥 검증: "정적 클러터는 죽은 파라미터, 진짜 위협은 유령"
==========================================================================================
report4/report5 는 챔버를 **anechoic**(무반사)이라 부르고 "흡수체 덕에 클러터가 약하다" 를
전제로 삼았다. 이 스크립트는 그 전제를 네 개의 실험으로 해체한다.

  [A] 챔버는 anechoic 이 아니라 **semi-anechoic** 이다 — 바닥이 반사성이다.
      TX→바닥→RX 정적 반사를 기하 + 프레넬(ITU 콘크리트, V편파=TM)로 닫힌형 유도하고,
      report5 §D 가 **이미 Sionna RT 로 실측해 둔** 챔버 클러터 탭과 대조한다.
      → 지연·진폭이 일치하면, RT 는 처음부터 바닥을 보고 있었고 우리 가정만 틀렸던 것이다.

  [B] 그런데 **왜 아무 수치도 안 틀렸나** — 정적 클러터 진폭을 스윕한다(없음 → 직접파보다 강함).
      ECA 가 진폭과 무관하게 정확히 소거하므로 SCR/Pd 가 꿈쩍도 안 하는 것을 보인다.
      → CH_CLUTTER_RATIO 는 **죽은 파라미터**. 고쳐도 결과가 안 바뀐다.
      → 따라서 report5 §D 의 "RT 와 Analytic 이 일치하니 Analytic 으로 스윕해도 된다" 는
        **클러터에 관한 한 공허하다**(어떤 클러터 모델이든 일치할 수밖에 없었다).

  [C] **진짜 위협 = 표적 경유 바닥 유령**(TX→표적→바닥→RX). 표적과 함께 도플러가 실려
      ECA 의 영공간 밖 → 안 지워진다. 기하·프레넬로 (지연, 도플러, 진폭)을 유도한다.

  [D] 유령을 실제로 주입하고 CFAR 를 돌린다. **거리분해능 ΔRb=c/B 가 운명을 가른다**:
      광대역일수록 유령이 진짜와 잘 **분리되어** 별개 표적으로 찍힌다.
      → 5G 를 최고의 조명원으로 만든 바로 그 분해능이 유령을 만든다.

실행:  cd benchmark && python verify_floor_ghost.py      (GPU 불필요 — [A] 는 캐시된 RT 결과 사용)
출력:  outputs/floor_ghost_verify.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", "src"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from geometry import (TX, RX, CENTER, CH_CLUTTER_RATIO, SPEED, SPAN,   # noqa: E402
                      floor_ghost, _fresnel_floor)
from scenarios import radial                                            # noqa: E402
from channel import AnalyticChannel                                     # noqa: E402
from link_budget import LinkBudget                                      # noqa: E402
from run_min_cell import run_cell, EIRP_DBM                             # noqa: E402
from waveforms import nr_downlink, lte_downlink, wifi_80211ac           # noqa: E402
from bistatic_scene import bistatic_params, C0                          # noqa: E402

OUT = os.path.abspath(os.path.join(_HERE, "..", "outputs", "floor_ghost_verify.json"))
RT_CACHE = os.path.abspath(os.path.join(_HERE, "..", "outputs", "report5_results.json"))
DRONE = "mavic4pro"


def waveforms():
    """report4/5 와 같은 3종. (표시명, wf) — 대역폭 오름차순이 아니라 서사 순서."""
    return [("5G NR 100MHz", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")),
            ("WiFi 80MHz", wifi_80211ac(bw_hz=80e6, carrier_hz=5.2e9)),
            ("LTE 20MHz", lte_downlink(bw_hz=20e6, carrier_hz=1.8e9, occupancy="G3"))]


# --------------------------------------------------------------------------- #
#  [A] 정적 바닥 반사 — 닫힌형 유도 vs Sionna RT 실측(report5 §D 캐시)
# --------------------------------------------------------------------------- #
def a_static_floor(fc=3.5e9):
    """TX→바닥→RX 를 거울상 + 프레넬로 유도하고, RT 가 실측한 클러터 탭과 대조."""
    tx, rx = np.asarray(TX, float), np.asarray(RX, float)
    rx_img = rx.copy(); rx_img[2] = -rx_img[2]

    L = float(np.linalg.norm(rx - tx))                 # 직접파
    Lf = float(np.linalg.norm(rx_img - tx))            # 바닥 경유(펴진 직선)
    d = rx_img - tx
    theta = float(np.arctan2(np.linalg.norm(d[:2]), abs(d[2])))
    gamma_tm = _fresnel_floor(theta, fc, pol="V")      # V편파 → 입사면 평행(TM)
    gamma_te = _fresnel_floor(theta, fc, pol="H")

    pred = dict(delay_ns=(Lf - L) / C0 * 1e9,
                theta_i_deg=np.degrees(theta),
                gamma_tm=gamma_tm, gamma_te=gamma_te,
                spread_db=20 * np.log10(L / Lf),
                rel_db_tm=20 * np.log10(gamma_tm * L / Lf),
                rel_db_te=20 * np.log10(gamma_te * L / Lf),
                L_direct_m=L, L_floor_m=Lf)

    rt_taps, assumed = [], [(dt * 1e9, 20 * np.log10(r)) for dt, r in CH_CLUTTER_RATIO]
    if os.path.exists(RT_CACHE):
        try:
            with open(RT_CACHE) as f:
                rt_taps = [tuple(t) for t in json.load(f)["D_rt"]["chamber_clutter"]]
        except Exception:
            rt_taps = []

    # 예측 지연(±1 ns) 안에 있는 RT 탭을 **전부** 보고한다. (정직하게: RT 는 19.3 ns 에 탭이
    #   두 개다 — −11.6 dB 와 −14.7 dB. 우리 닫힌형 예측과 0.0 dB 로 맞는 건 그중 하나뿐이고,
    #   다른 하나가 무엇인지는 **아직 모른다**. 바닥 타일이 밝은/어두운 두 SceneObject 로 쪼개져
    #   있어(chamber.floor_light/floor_dark) 반사점 근처에서 경로가 둘로 잡혔을 가능성이 있으나
    #   확인하지 않았다. 결론(= 바닥이 실재하고 우리가 과소가정했다)에는 영향이 없다.)
    near = [dict(delay_ns=t[0], rel_db=t[1], d_amp_db=t[1] - pred["rel_db_tm"])
            for t in rt_taps if abs(t[0] - pred["delay_ns"]) <= 1.0]
    best = min(near, key=lambda m: abs(m["d_amp_db"])) if near else None

    return dict(pred=pred, rt_taps=rt_taps, assumed=assumed,
                near_taps=near, match=best, n_near=len(near),
                rt_strongest_db=(max(db for _, db in rt_taps) if rt_taps else None),
                assumed_strongest_db=max(db for _, db in assumed))


# --------------------------------------------------------------------------- #
#  [B] 정적 클러터 진폭 스윕 — ECA 가 진폭을 보는가?
# --------------------------------------------------------------------------- #
def b_clutter_is_dead(lb, pos, vel, N=60, M=32):
    """클러터를 0 → 기본 → +20 dB → +40 dB(직접파보다 강함)로 키워도 SCR/Pd 가 안 바뀜을 보인다."""
    wf = nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")
    rows = []
    for scale in (0.0, 1.0, 10.0, 100.0):
        cl = tuple((dt, r * scale) for dt, r in CH_CLUTTER_RATIO) if scale else ()
        r = run_cell(wf, DRONE, pos, vel, lb, channel=AnalyticChannel(clutter=cl), M=M, N=N)
        rows.append(dict(scale=scale,
                         strongest_db=(20 * np.log10(max(a for _, a in cl)) if cl else None),
                         scr=r["scr_mean"], pd=r["pd"]))
    scrs = [x["scr"] for x in rows]
    return dict(rows=rows, scr_span_db=float(max(scrs) - min(scrs)))


# --------------------------------------------------------------------------- #
#  [C]+[D] 표적 경유 바닥 유령 — 유도 + 실제 CFAR 검출
# --------------------------------------------------------------------------- #
def cd_ghost(lb, pos, vel, N=60, M=32):
    mid = len(pos) // 2
    out = []
    for name, wf in waveforms():
        p = bistatic_params(TX, RX, pos[mid], vel[mid], wf.carrier_hz)
        r = run_cell(wf, DRONE, pos, vel, lb, M=M, N=N, floor_ghost_on=True)
        g = r["ghost"]
        out.append(dict(
            name=name, bw_hz=float(wf.bw_hz), fc=float(wf.carrier_hz),
            d_rb_m=g["d_rb_m"],                       # ΔRb = c/B
            rb_true=float(p["Rb"]), rb_ghost=g["rb_m"], sep_m=g["sep_m"],
            sep_over_drb=g["sep_m"] / g["d_rb_m"],
            fd_true=float(p["fd"]), fd_ghost=g["fd"],
            ghost_db=g["amp_db"], theta_i_deg=g["theta_i_deg"], gamma=g["gamma"],
            resolved=g["resolved"], pd=r["pd"], p_false=g["p_false"],
            scr=r["scr_mean"]))
    return out


def main():
    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)

    print("=" * 78)
    print("[A] 정적 바닥 반사 — 닫힌형 유도 vs Sionna RT 실측")
    A = a_static_floor()
    p = A["pred"]
    print(f"  기하: 직접파 {p['L_direct_m']:.2f} m, 바닥경유 {p['L_floor_m']:.2f} m "
          f"→ 여분지연 {p['delay_ns']:.1f} ns, 입사각 {p['theta_i_deg']:.1f}°")
    print(f"  프레넬(ITU 콘크리트): |Γ|_TM(V편파)={p['gamma_tm']:.3f}  확산 {p['spread_db']:+.1f} dB"
          f"  → 직접파 대비 **{p['rel_db_tm']:+.1f} dB**")
    if A["near_taps"]:
        print(f"  RT 가 그 지연(±1 ns)에서 찾은 경로 {A['n_near']}개:")
        for m in A["near_taps"]:
            tag = "  ← 닫힌형 예측과 일치" if abs(m["d_amp_db"]) < 0.15 else "  (미규명)"
            print(f"      {m['delay_ns']:.1f} ns / {m['rel_db']:+.1f} dB "
                  f"(Δ {m['d_amp_db']:+.2f} dB){tag}")
    print(f"  → RT 실측 최강 {A['rt_strongest_db']:+.1f} dB  vs  우리 가정 최강 "
          f"{A['assumed_strongest_db']:+.1f} dB  = **{A['rt_strongest_db']-A['assumed_strongest_db']:+.1f} dB 과소가정**")

    print("\n" + "=" * 78)
    print("[B] 그런데 그게 어떤 수치도 안 바꾼다 — ECA 는 정적 클러터 진폭을 안 본다")
    B = b_clutter_is_dead(lb, pos, vel)
    for r in B["rows"]:
        s = "없음" if r["strongest_db"] is None else f"{r['strongest_db']:+6.1f} dB"
        print(f"  클러터 {s:>10}  → SCR {r['scr']:.12f} dB   Pd {r['pd']:.2f}")
    print(f"  → SCR 전체 변동폭 = {B['scr_span_db']:.2e} dB  (직접파보다 14 dB 센 클러터까지 포함해서)")
    print("  → CH_CLUTTER_RATIO 는 **죽은 파라미터**. report5 §D 의 'RT≈Analytic' 일치는 클러터에 관한 한 공허.")

    print("\n" + "=" * 78)
    print("[C][D] 진짜 위협 — 표적 경유 바닥 유령(도플러 有 → ECA 통과)")
    D = cd_ghost(lb, pos, vel)
    print(f"  {'파형':14s} {'ΔRb=c/B':>8} {'유령분리':>9} {'분리/ΔRb':>9} {'유령진폭':>9} "
          f"{'Pd(참)':>7} {'P(가짜)':>8}")
    for d in D:
        v = "★ 별개 표적으로 검출" if d["p_false"] > 0.5 else "묻힘"
        print(f"  {d['name']:14s} {d['d_rb_m']:7.1f}m {d['sep_m']:8.2f}m {d['sep_over_drb']:8.2f}× "
              f"{d['ghost_db']:+8.1f}dB {d['pd']:7.2f} {d['p_false']:8.2f}  {v}")
    print("  → 대역폭이 넓을수록 유령이 진짜와 **잘 분리되어** 가짜 표적이 된다.")
    print("    5G 를 최고의 조명원으로 만든 바로 그 거리분해능이 유령을 만든다.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(dict(A_static_floor=A, B_clutter_dead=B, CD_ghost=D), f,
                  ensure_ascii=False, indent=1, default=float)
    print(f"\n→ {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
