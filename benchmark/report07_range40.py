# -*- coding: utf-8 -*-
"""
report07_range40.py — 거리판에 **40 m 를 더한다**. 그리고 이번엔 시드를 두 개 돌린다.

왜 40 m 인가 (사용자)
> "더 먼 거리 예를 들어 40 m 이런 거에 대한 그림 비교는 왜 없앤 거야?"

없앤 게 아니라 **애초에 계산한 적이 없다.** 지금 덱 오른쪽의 40 m 사다리는
자세 128 개를 고정해 놓고 광선 수만 바꾼 **예산 시험**이고, 맵을 그릴 슬로타임
시계열이 아니다. 그래서 여기서 만든다.

⭐왜 시드를 둘 돌리나 — 오늘 8 m 에서 데인 것이 정확히 이것이다
`outputs/probe_8m_anomaly.json` 이 확정한 사실: Sionna PathSolver 는 확산 경로를
몬테카를로로 **발견**하고, 드론에서 움직이는 것은 로터뿐이라 동체 경로 집합이
전 자세에서 **비트 단위로 동일**해진다. 즉 시드를 하나만 쓰면 기록 전체가
**추첨 한 번**을 받침대로 깔고, 자세를 4,096 개 평균해도 그 추첨은 안 평균된다.
8 m 에서 시드만 바꾸니 레벨이 18 dB 흔들리고 최강선이 3 배 조화에서 기본파로 돌아왔다.
⇒ 40 m 를 시드 하나로 내고 그림에 올리면 **같은 함정을 두 번 밟는다.**
   그래서 두 시드를 나란히 내고, 둘이 다르면 **다르다고 그림에 적는다.**

⛔ 기존 원장(outputs/report07_three_engine_ranges.*)을 건드리지 않는다. 자기 파일에만 쓴다.

읽는 것: outputs/report07_three_engines.json(_meta — 자세 격자·회전수를 그대로 물려받는다)
쓰는 것: outputs/report07_range40.json · outputs/report07_range40.npz

    SIONNA2_GPU=2 PYTHONPATH=src python benchmark/report07_range40.py --seed 1
    SIONNA2_GPU=1 PYTHONPATH=src python benchmark/report07_range40.py --seed 2
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

from gpu import pick                                                 # noqa: E402
pick(verbose=True)

import numpy as np                                                   # noqa: E402
import report15_probe as RP                                          # noqa: E402
from articulated_fast import FastPoser, rotor_phases                 # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, drone_colors             # noqa: E402

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
FC = float(TJ["fc_hz"])
REF_RANGE_M = 3.0                    # 광선 예산 규칙의 기준 거리
REF_SPP = 1_000_000                  # 그 거리의 광선 수


def rule_spp(rng: float) -> int:
    """표적 입체각 (D/R)² 에서 나오는 규칙 — 광선 수는 거리 제곱으로 는다."""
    return int(round(REF_SPP * (rng / REF_RANGE_M) ** 2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", type=float, default=40.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--n", type=int, default=0, help="0 이면 원장의 자세 수를 그대로")
    ap.add_argument("--spp", type=int, default=0, help="0 이면 규칙값")
    # ⭐샤딩 — 한 프로세스가 자세를 다 도는 대신 여러 프로세스가 나눠 돈다.
    #   자세당 GPU 메모리가 900 MB 뿐이라 카드 하나에 여러 개가 들어간다(사용자: «화끈하게»).
    #   자세 i 는 rotor_phases 로 독립 결정되므로 순서에 의존하지 않는다 — 나눠도 결과가 같다.
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()

    rng_m = float(a.range)
    spp = int(a.spp) if a.spp else rule_spp(rng_m)
    OUT = f"{ROOT}/outputs/report07_range{rng_m:.0f}.json"
    OUTN = f"{ROOT}/outputs/report07_range{rng_m:.0f}.npz"

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    prf, n = float(TJ["prf_hz"]), int(a.n or TJ["n"])
    az, el = float(TJ.get("az_deg", 0.0)), float(TJ.get("el_deg", -15.0))
    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    spread = float(TJ["rpm_spread_frac"])
    # ⭐자세 격자·회전수는 원장 그대로 — 그래야 3 m·15 m 판과 사과-대-사과가 된다
    pattern = np.array([+1.0, -1.0, -0.55, +0.55])
    rpms = rpm0 * (1.0 + spread * np.resize(pattern, len(fp.dirs)))
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    cols = drone_colors(spec)

    print(f"\n═══ {spec.name} · R = {rng_m:.0f} m · spp {spp/1e6:.0f}M "
          f"(규칙 (R/{REF_RANGE_M:.0f})² × {REF_SPP/1e6:.0f}M) · seed {a.seed} · "
          f"자세 {n} · PRF {prf:.0f} Hz · 기선 0 ═══", flush=True)

    idx = np.arange(a.shard, n, a.nshards)      # 이 프로세스가 맡은 자세
    E = np.zeros(idx.size, complex)
    npaths = np.zeros(idx.size, int)
    t0 = time.time()
    for j, i in enumerate(idx):
        i = int(i)
        m = fp.pose(ph[i]).to_mesh()
        d = os.path.join(RP.SCRATCH, f"{spec.key}_R40S{a.seed}sh{a.shard}_{i % 2}")
        paths_obj = m.write_obj_per_group(d, spec.key)
        parts = [RP.Part(name=f"{spec.key}_{g}_{i%2}", obj=p,
                         mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                 for g, p in paths_obj.items()]
        sc = RP.build_scene(parts, fc=FC)
        RP.place(sc, az=az, el=el, rng=rng_m, baseline=0.0)      # 기선 0 진짜 모노스태틱
        p = RP.rt.PathSolver()(sc, max_depth=1, los=True, specular_reflection=True,
                               diffuse_reflection=True, refraction=False,
                               samples_per_src=int(spp),
                               max_num_paths_per_src=RP.MAX_PATHS, seed=int(a.seed))
        try:
            aa, tau, _, O = RP.unpack(p)
        except ValueError:
            aa = np.zeros(0)
        if aa.size:
            hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
            E[j] = complex(np.sum(aa[hit] * np.exp(-1j * 2 * np.pi * FC * tau[hit])))
            npaths[j] = int(hit.sum())
        RP.drop_scratch(d)
        if j and j % 128 == 0:
            elp = time.time() - t0
            print(f"    shard {a.shard}: {j}/{idx.size}  {elp/60:.1f}분  "
                  f"ETA {(idx.size-j)/j*elp/60:.1f}분", flush=True)

    secs = time.time() - t0
    if a.nshards > 1:
        sd = f"{ROOT}/outputs/range{rng_m:.0f}_shards"
        os.makedirs(sd, exist_ok=True)
        np.savez_compressed(f"{sd}/s{a.seed}_{a.shard:02d}.npz",
                            idx=idx, E=E, npaths=npaths,
                            meta=np.array([a.seed, a.shard, a.nshards, spp, n, secs]))
        print(f"\n✅ shard {a.shard}/{a.nshards} · {idx.size} 자세 · {secs/60:.1f}분", flush=True)
        return
    db = 20 * np.log10(np.abs(E) + 1e-30)

    # 기존 파일이 있으면 시드를 덧붙인다(다른 시드 실행을 지우지 않는다)
    old = json.load(open(OUT)) if os.path.exists(OUT) else {"seeds": {}}
    oldn = dict(np.load(OUTN)) if os.path.exists(OUTN) else {}
    old["_meta"] = {
        "generator": "benchmark/report07_range40.py",
        "inherited_from": "outputs/report07_three_engines.json['_meta'] — 하드코딩 없음",
        "why_ko": "거리판에 40 m 를 더한다. 자세 격자·회전수·PRF·기하는 3 m·15 m 판과 동일.",
        "why_two_seeds_ko": "Sionna 는 확산 경로를 몬테카를로로 발견하고, 로터만 움직이므로 "
                            "동체 경로 집합이 전 자세에서 동일해진다 — 시드 하나면 기록 전체가 "
                            "추첨 한 번 위에 선다(8 m 에서 18 dB 흔들림을 실측했다). "
                            "그래서 두 시드를 나란히 낸다.",
        "drone": spec.key, "name": spec.name, "fc_hz": FC,
        "az_deg": az, "el_deg": el, "range_m": rng_m, "baseline_m": 0.0,
        "n": n, "prf_hz": prf, "rpm_per_rotor": rpms.tolist(),
        "rpm_spread_frac": spread,
        "spp_rule_ko": f"(R/{REF_RANGE_M:.0f})² × {REF_SPP/1e6:.0f}M = {spp/1e6:.0f}M",
    }
    old["seeds"][str(a.seed)] = {
        "seed": int(a.seed), "spp": spp, "seconds": round(secs, 1),
        "paths_median": float(np.median(npaths)),
        "paths_mean": float(npaths.mean()),
        "paths_zero_frac": float((npaths == 0).mean()),
        "level_db": float(20 * np.log10(np.abs(E).mean() + 1e-30)),
        "ptp_db": float(db.max() - db.min()),
        "p5p95_db": float(np.percentile(db, 95) - np.percentile(db, 5)),
        # ⭐정적 성분이 얼어붙었는지 — 유일값이 1 이면 추첨 한 장이라는 직접 증거
        "n_unique_abs": int(np.unique(np.round(np.abs(E), 18)).size),
    }
    oldn[f"S{a.seed}/E"] = E
    oldn[f"S{a.seed}/npaths"] = npaths
    json.dump(old, open(OUT, "w"), ensure_ascii=False, indent=1)
    np.savez_compressed(OUTN, **oldn)

    r = old["seeds"][str(a.seed)]
    print(f"\n✅ {OUT}\n✅ {OUTN}")
    print(f"   seed {a.seed}: {secs/60:.1f}분 · 경로중앙 {r['paths_median']:.0f} · "
          f"빈자세 {r['paths_zero_frac']:.1%} · 레벨 {r['level_db']:.1f} dB · "
          f"p-p {r['ptp_db']:.1f} dB · |E| 유일값 {r['n_unique_abs']}")
    if len(old["seeds"]) > 1:
        ls = {k: v["level_db"] for k, v in old["seeds"].items()}
        print(f"   ⭐시드별 레벨: {ls}  → 폭 {max(ls.values())-min(ls.values()):.1f} dB")


if __name__ == "__main__":
    main()
