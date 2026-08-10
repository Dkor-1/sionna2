# -*- coding: utf-8 -*-
"""
report07_hover_long.py — 문헌 형태의 **호버링 마이크로도플러 맵** (긴 창 + 흔들리는 rpm)

왜 다시 만드나
--------------
사용자가 문헌 그림(호버링 드론 마이크로도플러, Doppler ±2 kHz · Time 0~2 s · −40 dB)을
보여주며 «저런 형태로» 라고 했다. 우리 그림과 셋이 달랐다.

  ① **창이 짧았다** — 205 ms. 문헌은 2 s 다. 능선이 시간에 따라 어떻게 변하는지 보려면 길어야 한다.
  ② ⭐⭐ **rpm 을 고정값으로 뒀다** — 그래서 능선이 자로 그은 듯 곧다.
     ⚠ 실제 호버링은 비행제어기가 자세를 잡느라 **rpm 이 끊임없이 미세하게 흔들린다.**
       문헌 그림의 능선이 물결치는 것이 바로 그것이다. 우리는 그 물리를 아예 안 넣고 있었다.
  ③ 색·축 규약이 달랐다 — jet · −40 dB · ±2 kHz.

무엇을 넣나 — 호버 rpm 의 시간 변동
-----------------------------------
    rpm_k(t) = rpm0 · (1 + s_k + a·sin(2π f_ctl t + φ_k))

  s_k    로터별 정적 치우침 (무게중심·요 토크 균형) — 기존 ±2 %
  a      제어루프가 만드는 흔들림 진폭
  f_ctl  그 흔들림의 주파수. 멀티로터 자세루프는 대개 수 Hz 대다.
  φ_k    로터마다 다른 위상 — 네 모터가 같이 움직이지 않는다

⚠ a 와 f_ctl 은 **선언된 가정**이다. 우리에게 아직 실측 비행 로그가 없다.
  ⭐ 로그를 받으면 이 두 값이 **측정값으로 바뀐다** — 그것이 로그를 받아야 하는 이유 중 하나다.

    python benchmark/report07_hover_long.py [--sec 2.0]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick                                                   # noqa: E402
pick(verbose=True)

import numpy as np                                                     # noqa: E402
from articulated_fast import FastPoser                                 # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                             # noqa: E402
from rcs_sbr import sbr_field                                          # noqa: E402

FC = 3.5e9
GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}

# ⭐ 2026-08-07 정정 — 흩어짐을 ±2 % 로 뒀던 것은 **내 추측**이었고 틀렸다.
#   선배(홍지혁)의 PX4 텔레메트리를 내가 직접 재니 모터 간 산포가 **0.07~0.29 %** 였다.
#   그때 나는 그것을 «너무 작아 비현실적» 이라고 치부했는데, 그것이 실측이다.
#   ⚠ ±2 % 를 쓰면 네 로터의 빗살이 고조파마다 어긋나 맵이 뭉개진다 —
#     문헌 그림의 능선이 가늘고 선명한 이유가 여기 있다.
#
# ⭐ 2026-08-10 프리셋 이원화 — 웹 실측 앵커(outputs/rotor_rpm_web_anchor.json)가
#   그림을 완성했다: SITL 값은 **실내·이상 조건의 하한**이고, 실기체 야외는 더 벌어진다.
#     실내  NeuroBEM  정지비행  산포 ~0.54 % · 흔들림 0.74 % @ 0.7~2.2 Hz
#     야외  CODEV     정지비행  산포 ~2.4 %  · 흔들림 2.5 %  @ ~0.74 Hz
#     실기체 DJI P3 DAT(PWM 환산)  ~2~6 %
#   실증이 야외이므로([[실측=외부]]) 야외 프리셋이 헤드라인 후보다. SITL 프리셋은
#   대칭-이상 통제군으로 유지한다. 실측 로그가 오면 그 값이 프리셋을 대체한다.
PRESETS = {
    # (static_spread, wobble_amp, wobble_hz, 근거)
    "sitl":    (0.0022, 0.0015, 2.7, "선배 PX4 SITL 실측(0.07~0.29%) 중간값 — 대칭-이상 하한"),
    "outdoor": (0.02,   0.025,  1.0, "웹 실측 앵커 CODEV 야외(2.4%/2.5%@0.74Hz)·P3 DAT(2~6%) 반올림"),
}
STATIC_SPREAD, WOBBLE_AMP, WOBBLE_HZ = PRESETS["sitl"][:3]     # 기본은 기존과 동일(재현성)
PATTERN = np.array([+1.0, -1.0, -0.55, +0.55])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", default="matrice4e")
    ap.add_argument("--sec", type=float, default=2.0)
    ap.add_argument("--az", type=float, default=0.0)
    ap.add_argument("--el", type=float, default=-15.0)
    ap.add_argument("--preset", default="sitl", choices=list(PRESETS),
                    help="산포 프리셋 — sitl(실내·이상 하한, 기본) / outdoor(웹 실측 앵커)")
    ap.add_argument("--tag", default=None,
                    help="출력 접미사(기본: sitl 은 없음=기존 경로, 그 외 프리셋명)")
    a = ap.parse_args()

    global STATIC_SPREAD, WOBBLE_AMP, WOBBLE_HZ
    STATIC_SPREAD, WOBBLE_AMP, WOBBLE_HZ, preset_why = PRESETS[a.preset]
    tag = a.tag if a.tag is not None else ("" if a.preset == "sitl" else f"_{a.preset}")

    spec = DRONES[a.drone]
    fp = FastPoser(spec)
    n_rot = len(fp.dirs)
    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    lam = 3e8 / FC
    R = spec.prop_dia_mm / 1000.0 / 2.0
    f_rev = rpm0 / 60.0
    f_flash = spec.prop_blades * f_rev
    f_tip = 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(a.el))
    prf = float(np.ceil(4.0 * f_tip / 100.0) * 100.0)
    n = int(round(a.sec * prf))
    t = np.arange(n) / prf

    # ⭐ 흔들리는 rpm → 위상은 그 적분이다. 로터마다 다른 위상으로 흔든다.
    stat = STATIC_SPREAD * np.resize(PATTERN, n_rot)
    phi0 = 2 * np.pi * np.arange(n_rot) / n_rot
    rpm_t = rpm0 * (1.0 + stat[None, :]
                    + WOBBLE_AMP * np.sin(2 * np.pi * WOBBLE_HZ * t[:, None] + phi0[None, :]))
    # θ(t) = ∫ ω dt  — 흔들리므로 곱셈이 아니라 누적이다
    omega_deg = 360.0 * rpm_t / 60.0
    dt = 1.0 / prf
    ang = np.cumsum(omega_deg * dt, axis=0)
    ph = np.asarray(fp.dirs, float)[None, :] * ang

    print(f"\n═══ {spec.name} 호버링 · az {a.az:.0f} el {a.el:.0f} · {FC/1e9:.2f} GHz ═══")
    print(f"  f_flash {f_flash:.1f} Hz · f_tip {f_tip:.0f} Hz · PRF {prf:.0f} Hz")
    print(f"  {a.sec:.1f} s = {n} 표본 = {a.sec*f_flash:.0f} 블레이드 주기")
    print(f"  rpm 정적 치우침 ±{STATIC_SPREAD:.0%} · ⭐제어루프 흔들림 "
          f"±{WOBBLE_AMP:.1%} @ {WOBBLE_HZ:.1f} Hz", flush=True)

    u = np.array([np.cos(np.radians(a.el)) * np.cos(np.radians(a.az)),
                  np.cos(np.radians(a.el)) * np.sin(np.radians(a.az)),
                  np.sin(np.radians(a.el))])

    E = np.zeros(n, complex)
    t0 = time.time()
    for i in range(n):
        E[i] = sbr_field(fp.pose(ph[i]), GM, FC, u)
        if i and i % 1000 == 0:
            el = time.time() - t0
            print(f"    {i}/{n}  {el:.0f}s  ETA {(n-i)/i*el/60:.1f}분", flush=True)
    secs = time.time() - t0

    np.savez_compressed(f"{ROOT}/outputs/report07_hover_long{tag}.npz", E=E, t=t, rpm_t=rpm_t)
    json.dump({"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "drone": a.drone, "name": spec.name, "fc_hz": FC,
                         "az_deg": a.az, "el_deg": a.el,
                         "seconds": a.sec, "n": n, "prf_hz": prf,
                         "f_flash_hz": f_flash, "f_tip_hz": f_tip,
                         "blade_periods": a.sec * f_flash,
                         "rpm0": rpm0, "static_spread": STATIC_SPREAD,
                         "wobble_amp": WOBBLE_AMP, "wobble_hz": WOBBLE_HZ,
                         "preset": a.preset, "preset_why_ko": preset_why,
                         "compute_seconds": secs,
                         "declared_ko": ("⚠ 흔들림 진폭·주파수는 프리셋(문헌 앵커) 값이다. "
                                         "우리 표적의 실측 비행 로그가 이 둘을 측정값으로 바꾼다.")}},
              open(f"{ROOT}/outputs/report07_hover_long{tag}.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"\n  ✅ {secs/60:.1f}분 · outputs/report07_hover_long{tag}.npz")


if __name__ == "__main__":
    main()
