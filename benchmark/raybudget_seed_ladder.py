# -*- coding: utf-8 -*-
"""
raybudget_seed_ladder.py — **«레벨 산포가 광선으로 줄어든다» 를 제대로 재본다.**

사용자(2026-08-11)
> "레벨 산포가 무너졌니 어쩌고 하는 거 검증해보기 위해서 작업을 더 해볼래?"

■ 왜 다시 재나
지금까지 «1.78 억 발 2.61 dB → 40 억 발 1.22 dB» 라고 말해 왔는데, **시드가 판마다 두 개뿐**이다.
두 값의 차이(max−min)는 표본 2 개의 극단폭이고 **통계가 아니다**. 시드를 늘려 **표준편차**로
재고, 두 판의 차이가 우연으로 설명되는지 본다.

■ ⭐먼저 못 박아야 할 구조 — 시드는 «자세마다 뿌리는 잡음» 이 아니다
`report07_range40.py:115` 가 `PathSolver()(..., seed=a.seed)` 를 **모든 자세에 같은 값**으로
넘긴다. Fibonacci lattice 는 결정론적이므로 **한 시드 = 한 광선 방향 집합**이고, 그 집합을
4,096 자세 내내 그대로 쓴다. 즉 시드 효과는 자세에 걸쳐 **평균으로 지워지는 잡음이 아니라
방향 집합 하나의 계통 편향**일 수 있다.

이 스크립트가 그것을 가른다. K 시드 × N 자세의 |E| 행렬에서

    (a) 판별 평균 레벨의 시드 간 표준편차          ← «계통 편향» 이면 N 을 늘려도 안 준다
    (b) 자세 하나에서의 시드 간 표준편차의 평균     ← 두 값의 비가 구조를 말한다

i.i.d. 잡음이면 (a) ≈ (b)/√N 이어야 한다. 계통 편향이면 (a) ≈ (b) 에 가깝게 남는다.
**어느 쪽이든 그대로 적는다.**

■ 재는 것 셋 (전부 시드에 대한 표준편차)
  1. `level_db`      = 20·log10(mean|E|)      — «레벨 산포» 의 정본 정의
  2. `h1_over_h2_db` = 1× 봉우리 ÷ 2× 봉우리   — 어느 조화가 이기나
  3. `beat_hz`       = 대역 에너지 최강선       — 박자

■ ⛔ 자료를 안 덮는다
샤드는 `outputs/raybudget_ladder/spp{spp}_s{seed}_{shard}.npz` 로 나간다.
`outputs/range40_shards/` · `outputs/report07_range40.json` 은 **건드리지 않는다**.

    # 한 조각
    SIONNA2_GPU=2 PYTHONPATH=src:benchmark python benchmark/raybudget_seed_ladder.py \
        --spp 178000000 --seed 3 --n 1024 --shard 0 --nshards 4
    # 분석
    PYTHONPATH=src:benchmark python benchmark/raybudget_seed_ladder.py --analyse
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, f"{ROOT}/benchmark")

import numpy as np                                                       # noqa: E402

SHARD_DIR = f"{ROOT}/outputs/raybudget_ladder"
OUT_JSON = f"{ROOT}/outputs/raybudget_seed_ladder.json"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF, FFL, FTIP = TJ["prf_hz"], TJ["f_flash_hz"], TJ["f_tip_hz"]
FC, RANGE_M = 3.5e9, 40.0


# ═══ 계산 ═══════════════════════════════════════════════════════════════════
def run(a) -> None:
    from gpu import pick
    pick(verbose=False)
    import report15_probe as RP
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT, drone_colors

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    n = int(a.n)
    az, el = float(TJ.get("az_deg", 0.0)), float(TJ.get("el_deg", -15.0))
    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    spread = float(TJ["rpm_spread_frac"])
    # ⭐자세·회전수는 원장 그대로 — 그래야 기존 판과 사과-대-사과다
    pattern = np.array([+1.0, -1.0, -0.55, +0.55])
    rpms = rpm0 * (1.0 + spread * np.resize(pattern, len(fp.dirs)))
    ph = rotor_phases(np.arange(n) / PRF, rpms, fp.dirs)
    cols = drone_colors(spec)

    idx = np.arange(a.shard, n, a.nshards)
    E = np.zeros(idx.size, complex)
    npaths = np.zeros(idx.size, int)
    t0 = time.time()
    for j, i in enumerate(idx):
        i = int(i)
        m = fp.pose(ph[i]).to_mesh()
        d = os.path.join(RP.SCRATCH, f"lad_{spec.key}_p{a.spp}s{a.seed}sh{a.shard}_{i % 2}")
        paths_obj = m.write_obj_per_group(d, spec.key)
        parts = [RP.Part(name=f"{spec.key}_{g}_{i%2}", obj=p,
                         mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                 for g, p in paths_obj.items()]
        sc = RP.build_scene(parts, fc=FC)
        RP.place(sc, az=az, el=el, rng=RANGE_M, baseline=0.0)
        p = RP.rt.PathSolver()(sc, max_depth=1, los=True, specular_reflection=True,
                               diffuse_reflection=True, refraction=False,
                               samples_per_src=int(a.spp),
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
            e = time.time() - t0
            print(f"    spp{a.spp/1e6:.0f}M s{a.seed} sh{a.shard}: {j}/{idx.size} "
                  f"{e/60:.1f}분 ETA {(idx.size-j)/j*e/60:.1f}분", flush=True)

    os.makedirs(SHARD_DIR, exist_ok=True)
    np.savez_compressed(
        f"{SHARD_DIR}/spp{a.spp}_s{a.seed}_{a.shard:02d}.npz",
        idx=idx, E=E, npaths=npaths,
        meta=np.array([a.seed, a.shard, a.nshards, a.spp, n, time.time() - t0]))
    print(f"✅ spp {a.spp/1e6:.0f}M · seed {a.seed} · shard {a.shard}/{a.nshards} "
          f"· {idx.size} 자세 · {(time.time()-t0)/60:.1f}분", flush=True)


# ═══ 분석 ═══════════════════════════════════════════════════════════════════
def band_energy(E, prf=None):
    """덱과 **같은** 규약. md_mapstyle.flash_spec 을 그대로 쓴다."""
    from md_mapstyle import auto_periods, flash_spec
    prf = prf or PRF
    f, t, S, _ = flash_spec(np.asarray(E, complex), prf, FFL, auto_periods(prf, FFL))
    b = (np.abs(f) >= 0.35 * FTIP) & (np.abs(f) <= 1.00 * FTIP)
    g = (S[b, :] ** 2).sum(axis=0)
    g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)
    A = A / A.max()
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])

    def peak(f0, half=18.0):
        w = (fr >= f0 - half) & (fr <= f0 + half)
        return float(A[w].max()) if w.any() else np.nan
    p1, p2 = peak(FFL), peak(2 * FFL)
    h = 20 * np.log10(p1 / p2) if (p1 > 0 and p2 > 0) else np.nan
    return float(pk), float(h)


def load(spp: int, seed: int):
    fs = sorted(glob.glob(f"{SHARD_DIR}/spp{spp}_s{seed}_*.npz"))
    if not fs:
        return None
    E, idx, npz, secs = [], [], [], 0.0
    for f in fs:
        z = np.load(f, allow_pickle=True)
        E.append(z["E"]); idx.append(z["idx"]); npz.append(z["npaths"])
        secs += float(np.asarray(z["meta"], float)[5])
    idx = np.concatenate(idx); o = np.argsort(idx)
    return dict(E=np.concatenate(E)[o], idx=idx[o],
                npaths=np.concatenate(npz)[o], seconds=secs, n=len(idx))


def analyse() -> None:
    seen = {}
    for f in glob.glob(f"{SHARD_DIR}/spp*_s*_*.npz"):
        b = os.path.basename(f)
        spp = int(b.split("_")[0][3:]); seed = int(b.split("_")[1][1:])
        seen.setdefault(spp, set()).add(seed)
    if not seen:
        raise SystemExit(f"❌ {SHARD_DIR} 에 샤드가 없다")

    cells, rows = [], []
    for spp in sorted(seen):
        arms = []
        for seed in sorted(seen[spp]):
            d = load(spp, seed)
            if d is None or d["n"] == 0:
                continue
            pk, h = band_energy(d["E"])
            lvl = 20 * np.log10(np.mean(np.abs(d["E"])))
            arms.append(dict(seed=seed, n=d["n"], seconds=round(d["seconds"], 1),
                             npaths_median=int(np.median(d["npaths"])),
                             level_db=round(float(lvl), 3),
                             beat_hz=round(pk, 2), h1_over_h2_db=round(h, 2),
                             E=d["E"]))
        if len(arms) < 2:
            continue
        n_pose = min(a["n"] for a in arms)
        M = np.stack([np.abs(a["E"][:n_pose]) for a in arms])       # (K, N)

        # ⭐구조 판정 — 시드는 자세마다의 잡음인가, 방향 집합 하나의 계통 편향인가
        row_mean_db = 20 * np.log10(M.mean(axis=1))                 # 판별 평균 레벨
        sd_between = float(np.std(row_mean_db, ddof=1))             # (a)
        per_pose_db = 20 * np.log10(np.maximum(M, 1e-300))
        sd_within = float(np.mean(np.std(per_pose_db, axis=0, ddof=1)))  # (b)
        pred_iid = sd_within / np.sqrt(n_pose)                      # i.i.d. 이면 (a) ≈ 이 값

        def sd(k):
            v = [a[k] for a in arms if np.isfinite(a[k])]
            return round(float(np.std(v, ddof=1)), 3) if len(v) > 1 else None

        cells.append(dict(
            spp=spp, spp_m=spp / 1e6, n_seeds=len(arms), n_poses=n_pose,
            npaths_median=int(np.median([a["npaths_median"] for a in arms])),
            level_db_mean=round(float(np.mean([a["level_db"] for a in arms])), 3),
            sd_level_db=sd("level_db"),
            ptp_level_db=round(float(np.ptp([a["level_db"] for a in arms])), 3),
            sd_h1_over_h2_db=sd("h1_over_h2_db"),
            sd_beat_hz=sd("beat_hz"),
            beats_hz=[a["beat_hz"] for a in arms],
            h1_over_h2_db=[a["h1_over_h2_db"] for a in arms],
            structure=dict(
                sd_between_seeds_db=round(sd_between, 4),
                sd_within_pose_db=round(sd_within, 4),
                predicted_if_iid_db=round(float(pred_iid), 4),
                ratio_observed_over_iid=round(float(sd_between / pred_iid), 2)
                if pred_iid > 0 else None),
            arms=[{k: v for k, v in a.items() if k != "E"} for a in arms]))

    for c in cells:
        s = c["structure"]
        rows.append(f"  {c['spp_m']:>7.0f} M · 시드 {c['n_seeds']} · 자세 {c['n_poses']} · "
                    f"경로 {c['npaths_median']:>4d} | sd(level) {c['sd_level_db']:.3f} dB "
                    f"(p-p {c['ptp_level_db']:.2f}) | sd(1x/2x) "
                    f"{c['sd_h1_over_h2_db'] if c['sd_h1_over_h2_db'] is not None else float('nan'):.2f} dB"
                    f" | 관측/i.i.d. 예측 = {s['ratio_observed_over_iid']}x")

    verdict = dict(
        question_ko="광선을 늘리면 시드 간 레벨 산포가 정말 줄어드나",
        method_ko="시드마다 판을 따로 내고 판별 평균 레벨의 **표준편차**를 잰다. "
                  "p-p(최대−최소)는 표본 수에 따라 커지므로 판정에 쓰지 않는다.",
        structure_ko="⭐시드는 자세마다 다시 뽑는 잡음이 아니라 **광선 방향 집합 하나**를 고르는 "
                     "것이다(모든 자세에 같은 seed 를 넘긴다). 그래서 관측된 시드 간 표준편차가 "
                     "i.i.d. 예측(자세 안 산포 ÷ √N)보다 훨씬 크면, 그것은 평균으로 안 지워지는 "
                     "**계통 편향**이라는 뜻이다. ratio_observed_over_iid 가 그 배수다.",
        caveat_ko="⚠ 이 판정은 40 m·matrice4e·el −15°·기선 0 한 자리에서만 잰 것이다. "
                  "다른 거리·기체·앙각에서 같은지는 안 재봤다.")

    json.dump({"_meta": {
        "generator": "benchmark/raybudget_seed_ladder.py",
        "range_m": RANGE_M, "drone": TJ.get("drone"), "fc_hz": FC,
        "prf_hz": PRF, "f_flash_hz": FFL, "f_tip_hz": FTIP,
        "band_hz": [0.35 * FTIP, 1.00 * FTIP],
        "stft_ko": "md_mapstyle.flash_spec 규약 그대로(덱과 동일)",
        "shard_dir": SHARD_DIR,
        "not_touched_ko": "outputs/range40_shards/ 와 report07_range40.* 는 안 건드린다"},
        "cells": cells, "verdict": verdict},
        open(OUT_JSON, "w"), ensure_ascii=False, indent=1)

    print("\n═══ 시드 사다리 — 광선 예산별 ═══")
    print("\n".join(rows))
    print(f"\n✅ {OUT_JSON}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spp", type=int, default=178_000_000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--analyse", action="store_true")
    a = ap.parse_args()
    analyse() if a.analyse else run(a)


if __name__ == "__main__":
    main()
