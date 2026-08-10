# -*- coding: utf-8 -*-
"""
report07_ray_budget_test.py — ⭐40 m 붕괴가 **구조적인가 예산 부족인가**를 결판낸다.

왜 이 시험이 필요한가 (2026-08-10, 적대적 검증이 잡은 내 오류)
--------------------------------------------------------------
그림 9 의 본문이 «광선 수를 (R/3)² 로 보상했다» 고 적었는데, 실제 예산은
    R= 3 m   1.0M   (규칙대로)
    R=10 m   8.0M   ← 규칙대로면 11.1M  (0.72배)
    R=20 m  16.0M   ← 규칙대로면 44.4M  (0.36배)
    R=40 m  32.0M   ← 규칙대로면 177.8M (0.18배)
로 **보상이 안 됐다**. 그래서 «40 m 에서 자세의 78 %가 경로 0» 이라는 관측이
«PathSolver 의 구조적 한계» 인지 «내가 광선을 덜 쏜 탓» 인지 분리되지 않는다.
말로 얼버무리지 말고 **규칙대로 쏴 보고** 결판낸다.

시험 설계 — 한 축만 움직인다
  40 m 고정 · 같은 자세열 · 같은 기하(진짜 모노스태틱) · 광선 수만 사다리로 올린다.
  32M(원판) → 64M → 128M → 178M(규칙값). 자세 수는 비용 때문에 128 로 줄이되
  네 팔이 **같은 자세**를 보므로 비교는 공정하다.

무엇이 어떤 답인가
  · 178M 에서도 빈 자세 비율이 높게 남는다  → 구조적이다(내 원래 주장이 살아난다)
  · 빈 자세가 광선 수에 따라 계속 내려간다  → 예산 부족이었다(주장을 접어야 한다)

    python benchmark/report07_ray_budget_test.py
"""
from __future__ import annotations

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
import report15_probe as RP                                            # noqa: E402
from articulated_fast import FastPoser, rotor_phases                   # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, drone_colors               # noqa: E402

FC = 3.5e9
AZ, EL, RNG = 0.0, -15.0, 40.0
N_T = 128                                   # 자세 수(네 팔 공통)
LADDER = [32_000_000, 64_000_000, 128_000_000, 178_000_000]
STATIC_SPREAD = 0.0022
PATTERN = np.array([+1.0, -1.0, -0.55, +0.55])


def main():
    spec = DRONES["matrice4e"]
    fp = FastPoser(spec)
    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    f_rev = rpm0 / 60.0
    lam = 3e8 / FC
    R_ = spec.prop_dia_mm / 1000.0 / 2.0
    f_tip = 2.0 * (2 * np.pi * f_rev * R_) / lam * np.cos(np.radians(EL))
    prf = float(np.ceil(4.0 * f_tip / 100.0) * 100.0)
    t = np.arange(N_T) / prf
    rpms = rpm0 * (1.0 + STATIC_SPREAD * np.resize(PATTERN, len(fp.dirs)))
    ph = rotor_phases(t, rpms, fp.dirs)
    cols = drone_colors(spec)

    print(f"\n═══ 광선 예산 사다리 · R={RNG:.0f} m · 자세 {N_T} 고정 · 기선 0 ═══")
    print(f"  규칙값 (R/3)²×1M = {1e6*(RNG/3)**2/1e6:.0f}M · 사다리 "
          f"{[f'{s/1e6:.0f}M' for s in LADDER]}", flush=True)

    out = {}
    for spp in LADDER:
        npaths = np.zeros(N_T, int)
        E = np.zeros(N_T, complex)
        t0 = time.time()
        for i in range(N_T):
            mv = fp.pose(ph[i])
            m = mv.to_mesh()
            d = os.path.join(RP.SCRATCH, f"{spec.key}_RB{i % 2}")
            paths_obj = m.write_obj_per_group(d, spec.key)
            parts = [RP.Part(name=f"{spec.key}_{g}_{i%2}", obj=p,
                             mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                     for g, p in paths_obj.items()]
            sc = RP.build_scene(parts, fc=FC)
            RP.place(sc, az=AZ, el=EL, rng=RNG, baseline=0.0)
            p = RP.rt.PathSolver()(sc, max_depth=1, los=True, specular_reflection=True,
                                   diffuse_reflection=True, refraction=False,
                                   samples_per_src=int(spp),
                                   max_num_paths_per_src=RP.MAX_PATHS, seed=1)
            try:
                aa, tau, _, O = RP.unpack(p)
            except ValueError:
                aa = np.zeros(0)
            if aa.size:
                hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
                E[i] = complex(np.sum(aa[hit] * np.exp(-1j * 2 * np.pi * FC * tau[hit])))
                npaths[i] = int(hit.sum())
            RP.drop_scratch(d)
        secs = time.time() - t0
        zero = float((npaths == 0).mean())
        db = 20 * np.log10(np.abs(E) + 1e-30)
        good = db[npaths > 0]
        out[f"{spp/1e6:.0f}M"] = {
            "spp": int(spp), "seconds": round(secs, 1),
            "paths_median": float(np.median(npaths)),
            "paths_mean": float(npaths.mean()),
            "zero_frac": zero,
            "level_db_nonzero": float(good.mean()) if good.size else None,
        }
        print(f"  {spp/1e6:6.0f}M  {secs/60:5.1f}분 · 경로 중앙 {np.median(npaths):4.0f} · "
              f"평균 {npaths.mean():6.2f} · **빈 자세 {zero:6.1%}** · "
              f"레벨(경로있는자세) {good.mean() if good.size else float('nan'):.1f} dB", flush=True)

    zf = [out[k]["zero_frac"] for k in out]
    verdict = ("예산 부족이었다 — 광선을 규칙대로 쏘니 빈 자세가 사라진다"
               if zf[-1] < 0.05 else
               "구조적이다 — 규칙값까지 쏴도 빈 자세가 남는다"
               if zf[-1] > 0.5 * zf[0] else
               "섞여 있다 — 광선을 늘리면 줄지만 규칙값에서도 남는다")
    print(f"\n⭐ 판정: {verdict}  (빈 자세 {zf[0]:.1%} → {zf[-1]:.1%})", flush=True)

    json.dump({"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "why_ko": "그림 9 의 «(R/3)² 보상» 서술이 실제 예산과 어긋나(0.18배) "
                                   "40 m 붕괴가 구조인지 예산인지 분리되지 않았다. 규칙값까지 "
                                   "쏴 보고 결판낸다.",
                         "range_m": RNG, "n_poses": N_T, "prf_hz": prf,
                         "baseline_m": 0.0, "rule_value_spp": 1e6 * (RNG / 3) ** 2,
                         "verdict_ko": verdict},
               "ladder": out},
              open(f"{ROOT}/outputs/report07_ray_budget_test.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"✅ outputs/report07_ray_budget_test.json")


if __name__ == "__main__":
    main()
