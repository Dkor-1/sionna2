# -*- coding: utf-8 -*-
"""
deck_ours_by_range.py — 덱용: **우리 커널을 거리별로 진짜 계산한다**.

왜 (사용자, 2026-08-10)
> "거리별로 STFT 실제로 뽑아낸 결과 (직접 거리별로 뽑아내도록)"

그전까지 우리 열은 **한 번 계산한 배열을 모든 거리에 그대로** 썼다. 평면파(원거리장)
조명에는 거리라는 입력이 없기 때문이다. 그것이 틀린 것은 아니지만 «거리별 결과» 라고
부를 수는 없다.

이제 `sbr_field(..., range_m=R)` 로 **구면파 조명**을 넣을 수 있으므로, 거리마다 실제로
다시 계산한다. 그러면 우리 열도 거리의 함수가 된다.
⭐ 근거리장 실험(outputs/nearfield_sphere_vs_plane.json)이 이미 확인해 둔 것:
   진폭 상관이 3 → 40 m 에서 0.854 → 0.997 로 **평면파 답으로 수렴**한다.
   즉 멀리서는 둘이 같아지고, 가까이서만 갈린다.

⚠ 이 배선은 위상만 구면파다 — 광선은 평행 격자이고 1/r 확산은 없다.
⛔ 기존 원장을 안 건드린다. 자기 파일에만 쓴다.

    SIONNA2_GPU=2 PYTHONPATH=src python benchmark/deck_ours_by_range.py --shard i --nshards N
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
from rcs_sbr import C0, DEFAULT_DIV, grid_ref_from, sbr_field         # noqa: E402

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
OUT = f"{ROOT}/outputs/deck_ours_by_range.json"
OUTN = f"{ROOT}/outputs/deck_ours_by_range.npz"
SHD = f"{ROOT}/outputs/ours_range_shards"


def _look(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranges", default="3,15,40")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fc, prf, n = float(TJ["fc_hz"]), float(TJ["prf_hz"]), int(TJ["n"])
    u = _look(float(TJ.get("az_deg", 0.0)), float(TJ.get("el_deg", -15.0)))
    ranges = [float(x) for x in a.ranges.split(",")]

    if a.merge:
        series, meta = {}, {}
        for R in ranges:
            E = np.zeros(n, complex); tot = 0.0
            for f in sorted(os.listdir(SHD)):
                if not f.startswith(f"R{R:.0f}_"):
                    continue
                z = np.load(f"{SHD}/{f}")
                E[z["idx"]] = z["E"]; tot += float(z["secs"])
            series[f"R{R:.0f}/E"] = E
            meta[f"{R:.0f}"] = dict(range_m=R, cpu_seconds=round(tot, 1),
                                    level_db=float(20 * np.log10(np.abs(E).mean() + 1e-30)))
            print(f"  R={R:5.0f} m  레벨 {meta[f'{R:.0f}']['level_db']:.2f} dB")
        np.savez_compressed(OUTN, **series)
        json.dump({"_meta": {
            "generator": "benchmark/deck_ours_by_range.py",
            "what_ko": "우리 커널을 **구면파 조명**으로 거리마다 다시 계산한 슬로타임 열",
            "illumination": "spherical wave, phase exp(j2k(|p-p_tx|-R))",
            "caveat_ko": "위상만 구면파. 광선은 평행 격자이고 1/r 확산은 없다.",
            "grid_ko": "얼린 격자(자세 전 구간 합집합 bbox)",
            "drone": spec.key, "fc_hz": fc, "prf_hz": prf, "n": n,
            "az_deg": TJ.get("az_deg", 0.0), "el_deg": TJ.get("el_deg", -15.0),
            "rpm_per_rotor": TJ["rpm_per_rotor"]},
            "ranges": meta}, open(OUT, "w"), ensure_ascii=False, indent=1)
        print(f"\n✅ {OUT}\n✅ {OUTN}")
        return

    fp = FastPoser(spec)
    rpms = np.asarray(TJ["rpm_per_rotor"], float)
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    d = (C0 / fc) / DEFAULT_DIV
    # 판은 전 자세 합집합으로 한 번 (얼린 격자 — 오늘 규약)
    gref = grid_ref_from([fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))], fc, spacing=d)

    idx = np.arange(a.shard, n, a.nshards)
    os.makedirs(SHD, exist_ok=True)
    for R in ranges:
        E = np.zeros(idx.size, complex)
        t0 = time.time()
        for j, i in enumerate(idx):
            E[j] = sbr_field(fp.pose(ph[int(i)]), gm, fc, u,
                             spacing=d, grid_ref=gref, range_m=R)
            if j and j % 128 == 0:
                el = time.time() - t0
                print(f"    R={R:.0f} shard {a.shard}: {j}/{idx.size} "
                      f"{el/60:.1f}분 ETA {(idx.size-j)/j*el/60:.1f}분", flush=True)
        np.savez_compressed(f"{SHD}/R{R:.0f}_{a.shard:02d}.npz",
                            idx=idx, E=E, secs=time.time() - t0)
        print(f"  ✅ R={R:.0f} m shard {a.shard} · {idx.size} 자세 · "
              f"{(time.time()-t0)/60:.1f}분", flush=True)


if __name__ == "__main__":
    main()
