# -*- coding: utf-8 -*-
"""
report15_verdict_geomref.py — ⭐⭐ **기하 위상 기준(geometric phase reference)**
================================================================================

무엇을 가르려고 만드는가
  판정 (b) 는 "h(φ) 가 블레이드의 전기적 크기가 요구하는 만큼의 조화를 담는가" 를 묻는다.
  이상 점산란자(Jacobi–Anger)는 블레이드를 **팁의 점 하나**로 뭉갠 모형이라, 실제 메쉬가
  요구하는 조화 수와 정확히 같지 않다(코드·피치·허브 때문에 조금 넓거나 좁을 수 있다).

  그래서 **같은 메쉬**로 위상만 더한 기준을 만든다:

      h_geom(φ) = Σ_v exp(−j k (|tx − p_v(φ)| + |rx − p_v(φ)|))

  · 산란 물리 없음(진폭·재질·가림·법선 전부 무시, 가중치 균일)
  · 오직 **움직이는 기하가 만드는 왕복 위상**만 남는다
  · TX/RX 는 Sionna 격자와 같은 좌표(구면파, 준-모노스태틱 baseline 0.2 m)

  이 기준의 조화 빗은 "이 메쉬가 이 자세·거리에서 **원리적으로** 낼 수 있는 도플러 구조"다.
  Sionna 의 빗이 여기에 맞으면, Sionna 는 움직이는 기하의 위상을 제대로 따라가고 있는 것이다.
  어긋나면 Sionna 의 빗은 기하가 아니라 다른 무언가(표본 잡음 등)에서 온 것이다.

⛔ src/drones.py · src/drone_cad.py 는 읽기만. GPU 안 씀(순수 numpy). 신규 파일 하나만 쓴다.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from drones import DRONES, pose_articulated, rotor_layout                # noqa: E402

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
BASELINE_M = 0.20
RANGES = (1.0, 3.0, 10.0)
ASPECTS = (("nose", 0.0, 15.0), ("oblique", 45.0, 15.0), ("side", 90.0, 15.0),
           ("hot", 0.0, 0.0), ("disc", 0.0, 75.0))
N_PHASE = 64
KEYS = ("mini2", "matrice4e")
OUT_JSON = os.path.join(ROOT, "outputs", "report15_verdict_geomref.json")


def look_dir(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


def basis_perp(u):
    t = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, t); e1 /= np.linalg.norm(e1)
    return e1, np.cross(u, e1)


def antennas(az, el, rng, baseline=BASELINE_M):
    u = look_dir(az, el)
    e1, _ = basis_perp(u)
    return rng * u + 0.5 * baseline * e1, rng * u - 0.5 * baseline * e1


def prop_vertices(spec, phase_deg):
    """로터 위상 φ 의 **프로펠러 그룹 꼭짓점**만. Sionna 격자와 같은 규약
    (로터 k 의 스핀 = dir_k·φ, pose_articulated 그대로)."""
    dirs = [r["dir"] for r in rotor_layout(spec)]
    m = pose_articulated(spec, rotor_phase_deg=[d * float(phase_deg) for d in dirs])
    V = np.asarray(m.v, float)
    #  geom.Mesh 는 **면별 그룹 이름**을 m.g 에 담는다 → prop 면이 쓰는 꼭짓점만 모은다
    g = np.asarray(m.g, dtype=object)
    F = np.asarray(m.f, int)
    sel = np.unique(F[g == "prop"].ravel())
    if sel.size == 0:
        raise RuntimeError("prop 그룹 면을 찾지 못했다")
    return V[sel]


def geom_wave(P_by_phase, tx, rx):
    """h_geom(φ) = Σ_v exp(−j k (|tx−p| + |rx−p|)). 가중치 균일(위상만 본다)."""
    k = 2.0 * np.pi / LAM
    out = np.empty(len(P_by_phase), complex)
    for i, P in enumerate(P_by_phase):
        d = np.linalg.norm(P - tx, axis=1) + np.linalg.norm(P - rx, axis=1)
        out[i] = np.exp(-1j * k * d).sum()
    return out


def comb(z):
    """한 주기 복소 파형 → 조화 크기(k=1..N/2)와 −20 dB 가장자리 빈."""
    N = len(z)
    Z = np.fft.fft(z) / N
    ny = N // 2
    a = np.abs(Z[1:ny + 1])
    if a.max() <= 0:
        return a, None, None
    thr = a.max() * 10 ** (-20.0 / 20.0)
    idx = np.where(a >= thr)[0]
    return a, (int(idx.max()) + 1 if idx.size else None), int(np.argmax(a)) + 1


def main():
    t0 = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_verdict_geomref.py",
        role=("같은 메쉬로 **위상만** 더한 기준 — 움직이는 기하가 원리적으로 낼 수 있는 "
              "도플러 빗. Sionna 의 빗이 기하에서 오는지 가른다."),
        model="h_geom(φ) = Σ_v exp(−j k (|tx−p_v(φ)| + |rx−p_v(φ)|)), 가중치 균일",
        ignores=["산란 진폭", "재질", "법선", "가림", "면적 가중"],
        fc_hz=FC, lambda_m=LAM, baseline_m=BASELINE_M, n_phase=N_PHASE,
        ranges_m=list(RANGES),
        aspects=[dict(name=n, az_deg=a, el_deg=e) for n, a, e in ASPECTS],
        gpu="사용 안 함", stamp=time.strftime("%Y-%m-%d %H:%M:%S")), airframes={})

    for key in KEYS:
        spec = DRONES[key]
        period = 360.0 / int(spec.prop_blades)
        phis = np.arange(N_PHASE) * (period / N_PHASE)
        print(f"\n{key} — 프롭 꼭짓점 수집 ({N_PHASE} 위상)")
        P = [prop_vertices(spec, float(p)) for p in phis]
        nv = int(P[0].shape[0])
        f_rev = float(spec.hover_rpm) / 60.0
        f_flash = int(spec.prop_blades) * f_rev
        r_tip = float(spec.prop_dia_mm) / 2000.0
        f_tip = 2.0 * (2.0 * np.pi * f_rev * r_tip) / LAM
        cells = {}
        for R in RANGES:
            for ak, az, el in ASPECTS:
                tx, rx = antennas(az, el, R)
                z = geom_wave(P, tx, rx)
                a, edge, peak = comb(z)
                pred = f_tip * math.cos(math.radians(el))
                cells[f"{R:g}/{ak}"] = dict(
                    range_m=float(R), aspect=ak, el_deg=float(el),
                    n_prop_vertices=nv,
                    harm_abs=[float(x) for x in a],
                    harm_freq_hz=[float((i + 1) * f_flash) for i in range(len(a))],
                    edge_bin=edge, peak_bin=peak,
                    f_edge_hz=float(edge * f_flash) if edge else None,
                    f_tip_pred_hz=float(pred),
                    edge_over_pred=float(edge * f_flash / pred) if edge and pred else None,
                    modulation_ptp_db=float(np.ptp(20 * np.log10(np.abs(z) + 1e-300))))
                print(f"   R={R:>4g} {ak:8s} edge_bin={str(edge):>4s} "
                      f"f_edge={cells[f'{R:g}/{ak}']['f_edge_hz']}  "
                      f"pred={pred:8.1f} Hz  ratio={cells[f'{R:g}/{ak}']['edge_over_pred']}")
        J["airframes"][key] = dict(
            name=spec.name, n_prop_vertices=nv, f_rev_hz=f_rev, f_flash_hz=f_flash,
            f_tip_hz=f_tip, prop_radius_m=r_tip,
            phases_deg=[float(x) for x in phis], phase_period_deg=period, by_cell=cells)

    J["meta"]["seconds_total"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False)
    print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")


if __name__ == "__main__":
    main()
