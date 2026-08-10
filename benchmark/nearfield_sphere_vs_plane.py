# -*- coding: utf-8 -*-
"""
nearfield_sphere_vs_plane.py — **평면파 근사가 3 m 에서 얼마나 틀리나**를 잰다.

왜 (사용자, 2026-08-10)
> "3 m 거리에서는 다른 방식으로 계산해서 STFT 그려내는 것이 원래 맞다는 거지?"

맞다. 우리 커널은 조명을 **평면파**로 넣는다 — 파면이 평평하다는 가정이고, 그것이
**원거리장 근사**다. 이 기체의 경계는 2D²/λ ≈ 8 m 인데 **주력 거리 3 m 는 그 안쪽**이다.
가까우면 파면이 휘어 기체 앞뒤가 다른 위상을 받으므로 간섭 무늬가 실제로 달라진다.

2차 위상 오차의 크기: k·D²/(4R). D=0.6 m · R=3 m · 3.5 GHz 에서 **약 2.2 rad** —
무시할 수 없다. 그래서 **재본다.**

무엇을 하나
  같은 자세 열(로터 한 바퀴)을 두 번 계산한다.
    ① 평면파 (지금 생산 경로)          sbr_field(..., range_m=None)
    ② 구면파 (거리를 실제로 넣는다)     sbr_field(..., range_m=R)
  거리 R 을 3 · 8 · 15 · 40 m 로 훑어, **멀어질수록 둘이 수렴하는지** 본다.
  ⭐수렴하면 그 자체가 «평면파 근사가 원거리장에서 정당하다» 는 증거이고,
    3 m 에서 얼마나 갈라지는지가 **우리가 지금 감수하고 있는 오차**다.

⚠ 이 배선은 **위상만** 구면파로 바꾼다. 광선은 여전히 평행 격자이고 1/r 확산도 안 넣는다.
  근거리장의 지배적 효과가 위상 곡률이라 그것부터 잰다. 광선 발산·확산은 다음 단계다.
⛔ 기존 원장을 안 건드린다. 자기 파일(outputs/nearfield_sphere_vs_plane.json)에만 쓴다.

    SIONNA2_GPU=2 PYTHONPATH=src python benchmark/nearfield_sphere_vs_plane.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick                                                  # noqa: E402
pick(verbose=True)

import numpy as np                                                    # noqa: E402
from articulated_fast import FastPoser, rotor_phases                  # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                            # noqa: E402
from md_mapstyle import auto_periods, flash_spec                      # noqa: E402
from rcs_sbr import C0, DEFAULT_DIV, grid_ref_from, sbr_field         # noqa: E402

OUT = f"{ROOT}/outputs/nearfield_sphere_vs_plane.json"
OUTN = f"{ROOT}/outputs/nearfield_sphere_vs_plane.npz"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]


def _look(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def band_spectrum(E, prf, fflash, ftip):
    """맵의 날개끝 대역 에너지를 시간축으로 본 뒤 다시 푸리에 — 덱과 같은 자."""
    per = auto_periods(prf, fflash)
    f, t, S, _ = flash_spec(np.asarray(E, complex), prf, fflash, per)
    b = (np.abs(f) >= 0.35 * ftip) & (np.abs(f) <= 1.0 * ftip)
    g = (S[b, :] ** 2).sum(axis=0)
    g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    peak = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])
    return float(peak), S / S.max()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranges", default="3,8,15,40")
    ap.add_argument("--n", type=int, default=512, help="자세 수(한 바퀴를 고르게)")
    a = ap.parse_args()

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    fc = float(TJ["fc_hz"]); prf = float(TJ["prf_hz"])
    fflash, ftip = float(TJ["f_flash_hz"]), float(TJ["f_tip_hz"])
    u = _look(float(TJ.get("az_deg", 0.0)), float(TJ.get("el_deg", -15.0)))
    gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    rpms = np.asarray(TJ["rpm_per_rotor"], float)

    n = int(a.n)
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    meshes = [fp.pose(ph[i]) for i in range(n)]
    lam = C0 / fc
    d = lam / DEFAULT_DIV
    gref = grid_ref_from(meshes[::max(1, n // 64)], fc, spacing=d)   # 얼린 격자(오늘 규약)

    V = np.asarray(meshes[0].v, float)
    D = float(np.linalg.norm(V.max(0) - V.min(0)))
    ff = 2.0 * D * D / lam

    ranges = [float(x) for x in a.ranges.split(",")]
    out, series = {}, {}
    print(f"\n═══ {spec.name} · 평면파 ↔ 구면파 · 자세 {n} · "
          f"표적 크기 {D*1000:.0f} mm · 원거리장 경계 2D²/λ = {ff:.2f} m ═══", flush=True)

    t0 = time.time()
    Ep = np.array([sbr_field(m, gm, fc, u, spacing=d, grid_ref=gref) for m in meshes])
    print(f"  평면파 {time.time()-t0:.0f} s", flush=True)
    pk_p, S_p = band_spectrum(Ep, prf, fflash, ftip)
    series["plane/E"] = Ep

    for R in ranges:
        t1 = time.time()
        Es = np.array([sbr_field(m, gm, fc, u, spacing=d, grid_ref=gref, range_m=R)
                       for m in meshes])
        pk_s, S_s = band_spectrum(Es, prf, fflash, ftip)
        series[f"sphere{R:.0f}/E"] = Es
        # 위상 곡률의 이론 크기 — 2차 위상 오차 k D²/(4R)
        quad = 2 * np.pi / lam * D * D / (4 * R)
        out[f"{R:.0f}"] = dict(
            range_m=R, seconds=round(time.time() - t1, 1),
            quadratic_phase_rad=float(quad),
            inside_farfield=bool(R < ff),
            map_cosine=float((S_p.ravel() @ S_s.ravel())
                             / np.linalg.norm(S_p) / np.linalg.norm(S_s)),
            amp_corr=float(np.corrcoef(np.abs(Ep), np.abs(Es))[0, 1]),
            level_diff_db=float(20 * np.log10(np.abs(Es).mean() / np.abs(Ep).mean())),
            beat_plane_hz=pk_p, beat_sphere_hz=pk_s,
            beat_diff_pct=float(100 * (pk_s - pk_p) / fflash))
        r = out[f"{R:.0f}"]
        print(f"  R={R:5.0f} m  {'근거리장' if r['inside_farfield'] else '원거리장'}"
              f"  2차위상 {quad:5.2f} rad  맵코사인 {r['map_cosine']:.4f}"
              f"  진폭상관 {r['amp_corr']:.4f}  레벨 {r['level_diff_db']:+.2f} dB"
              f"  박자 {pk_s:.2f} Hz ({r['beat_diff_pct']:+.3f} %)", flush=True)

    json.dump({"_meta": {
        "generator": "benchmark/nearfield_sphere_vs_plane.py",
        "question_ko": "평면파(원거리장) 근사가 3 m 에서 얼마나 틀리나",
        "what_changes_ko": "조명 위상만 구면파로. 광선은 평행 격자 그대로이고 1/r 확산 없음.",
        "drone": spec.key, "fc_hz": fc, "prf_hz": prf, "n": n,
        "target_size_m": D, "farfield_boundary_m": ff,
        "f_flash_hz": fflash, "f_tip_hz": ftip,
        "beat_plane_hz": pk_p,
        "grid": "얼린 격자(오늘 규약)", "spacing_m": d},
        "ranges": out}, open(OUT, "w"), ensure_ascii=False, indent=1)
    np.savez_compressed(OUTN, **series)
    print(f"\n✅ {OUT}\n✅ {OUTN}")

    c = [out[k]["map_cosine"] for k in out]
    print(f"\n⭐가장 가까운 거리에서 코사인 {min(c):.4f} · 가장 먼 거리에서 {max(c):.4f}")
    print("   → 멀어질수록 1 에 붙으면 평면파 근사가 원거리장에서 정당하다는 증거다.")


if __name__ == "__main__":
    main()
