# -*- coding: utf-8 -*-
"""p3_ours_v2.py — ⭐ Phantom 3 σ **재계산 (사진 실측 메쉬 v2)**, el=0 하나만.

구판 outputs/p3_ours.json 은 고도 10개를 돌아 14,542 s 를 썼다. 대조에 실제로 쓰이는 컷은
el=0(=Yuan θ90 방위면) 하나뿐이므로 여기서는 그것만 돌린다. 대신 주파수를 **61점**으로
조밀하게 깐다 — 구판 21점은 SE 0.066 dB/GHz 에 끝점이 기울기를 끌었다.

⚠ 격자 설계: 61점 균등(Δ=0.27333 GHz)은 구판 21점 격자(Δ=0.82)를 **매 3번째 점으로 정확히
  포함**한다. 그래서 v1↔v2 를 같은 21주파수에서 **짝지어** 비교할 수 있다.

⚠ 나머지 규약은 구판과 완전히 동일(p3_ours.json meta 대조):
    div=16 · n_az=360 · jitter=2 · penetrate=True · max_bounce=1 · ptd=False · 선형평균
  달라진 것은 **메쉬(사진 실측 재구축)** 와 주파수 밀도뿐이다.

실행:
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/p3_ours_v2.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))

OUT = os.path.join(ROOT, "outputs", "p3_ours_v2.json")
PARTS = os.path.join(ROOT, "outputs", "partial", "p3_v2")
PY = os.path.expanduser("~/.venvs/py312/bin/python")

N_FREQ = 61
FREQS = np.linspace(1.8, 18.2, N_FREQ)
V1_FREQS = np.linspace(1.8, 18.2, 21)
GPUS = [2, 3]
PROCS_PER_GPU = 6
MEM_MB = 2800

COMM = {"1.800": 1.8, "1.843": 1.843, "3.500": 3.5, "5.210": 5.21, "10.000": 10.0, "18.200": 18.2}
SUBBANDS = [(1.8, 6.0), (1.8, 10.0), (6.0, 18.2), (10.0, 18.2)]


def _fit(f, y):
    f, y = np.asarray(f, float), np.asarray(y, float)
    a, b = np.polyfit(f, y, 1)
    r = y - (a * f + b)
    ss = float(np.sum((y - y.mean()) ** 2))
    return dict(a=float(a), b=float(b),
                R2=float(1.0 - np.sum(r ** 2) / ss) if ss > 0 else float("nan"),
                rmse_db=float(np.sqrt(np.mean(r ** 2))),
                se_a=float(np.sqrt(np.sum(r ** 2) / (len(f) - 2) / np.sum((f - f.mean()) ** 2))),
                n=int(len(f)))


def mesh_fingerprint():
    from drones import DRONES, build_drone
    m = build_drone(DRONES["phantom3"])
    h = hashlib.sha256()
    h.update(np.asarray(m.v, dtype=np.float32).tobytes())
    h.update(np.asarray(m.f, dtype=np.int32).tobytes())
    V = np.asarray(m.v, float)
    return dict(sha256_16=h.hexdigest()[:16], n_vert=len(m.v), n_tri=len(m.f),
                bbox_m=[float(x) for x in (V.max(0) - V.min(0))])


def launch():
    os.makedirs(PARTS, exist_ok=True)
    n_w = len(GPUS) * PROCS_PER_GPU
    # 비용 ∝ f² (광선격자 λ/16) → 비싼 것부터 가장 한가한 워커에 얹는 그리디 균형
    order = sorted(range(N_FREQ), key=lambda i: -FREQS[i] ** 2)
    load = [0.0] * n_w
    bins: list[list[float]] = [[] for _ in range(n_w)]
    for i in order:
        w = int(np.argmin(load))
        bins[w].append(float(FREQS[i]))
        load[w] += FREQS[i] ** 2

    procs, parts = [], []
    for w in range(n_w):
        if not bins[w]:
            continue
        gpu = GPUS[w % len(GPUS)]
        part = os.path.join(PARTS, f"w{w:02d}.json")
        parts.append(part)
        env = dict(os.environ, SIONNA2_GPU=str(gpu), SIONNA2_GPU_MEM=str(MEM_MB),
                   PYTHONPATH=f"{ROOT}/src:{ROOT}/benchmark")
        log = open(os.path.join(PARTS, f"w{w:02d}.log"), "w")
        procs.append(subprocess.Popen(
            [PY, os.path.join(ROOT, "benchmark", "p3_v2_worker.py"), part,
             ",".join(f"{x:.6f}" for x in sorted(bins[w]))],
            env=env, stdout=log, stderr=subprocess.STDOUT))
        print(f"[drv] worker {w:02d} → GPU {gpu}  {len(bins[w])}개  예상비용 {load[w]:.0f}", flush=True)
    return procs, parts


def main():
    t0 = time.time()
    fp = mesh_fingerprint()
    print("[drv] mesh", fp, flush=True)
    procs, parts = launch()
    rc = [p.wait() for p in procs]
    print(f"[drv] 워커 종료 rc={rc}  경과 {time.time()-t0:.0f}s", flush=True)

    freq = {}
    for p in parts:
        if os.path.exists(p):
            freq.update(json.load(open(p)))
    f = np.array(sorted(float(k) for k in freq))
    key = {float(k): k for k in freq}
    mu = np.array([freq[key[x]]["mu_dbsm"] for x in f])
    eps = np.array([freq[key[x]]["eps_db"] for x in f])
    print(f"[drv] 회수 {f.size}/{N_FREQ} 주파수", flush=True)

    fit_mu = _fit(f, mu)
    fit_eps = _fit(f, eps)
    sub = {}
    for lo, hi in SUBBANDS:
        m = (f >= lo) & (f <= hi)
        if m.sum() >= 3:
            sub[f"{lo}-{hi} GHz"] = _fit(f[m], mu[m])

    # 구판 21점 격자와 **정확히 겹치는** 부분표본 (v1↔v2 짝비교용)
    idx = [int(np.argmin(np.abs(f - x))) for x in V1_FREQS]
    ok = all(abs(f[i] - x) < 1e-6 for i, x in zip(idx, V1_FREQS))
    fit_on_v1grid = _fit(f[idx], mu[idx]) if ok else None

    lin_minus = np.array([freq[key[x]]["lin_minus_db_mean_db"] for x in f])
    p10 = np.array([freq[key[x]]["percentiles_norm"]["P10_db"] for x in f])
    p1 = np.array([freq[key[x]]["percentiles_norm"]["P1_db"] for x in f])
    tally = {}
    for x in f:
        for dom in ("power", "amplitude"):
            b = freq[key[x]]["distributions"][dom]["best_by_CvM"]
            tally.setdefault(dom, {})
            tally[dom][b] = tally[dom].get(b, 0) + 1

    v1 = json.load(open(os.path.join(ROOT, "outputs", "p3_ours.json")))
    out = dict(
        meta=dict(
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            drone="phantom3", drone_name="DJI Phantom 3 Professional",
            what=("⭐ **v2 — 사진 실측으로 재구축한 메쉬**로 다시 낸 el=0 σ. 구판 "
                  "outputs/p3_ours.json 을 덮지 않는다. 바뀐 것은 메쉬와 주파수 밀도뿐이고 "
                  "커널·규약은 구판과 같다."),
            engine=v1["meta"]["engine"], caller=v1["meta"]["caller"],
            n_az=360, az_grid_deg=v1["meta"]["az_grid_deg"], div=16,
            ray_spacing="λ/div", jitter=v1["meta"]["jitter"], penetrate=v1["meta"]["penetrate"],
            max_bounce=1, ptd=False, band="1.8–18.2 GHz (Das 측정대역)",
            stat_convention=v1["meta"]["stat_convention"],
            els_deg=[0.0], n_freq=int(f.size),
            freq_sampling=(f"1.8–18.2 GHz **균등 {N_FREQ}점, Δ={16.4/(N_FREQ-1):.5f} GHz**. "
                           "구판 21점(Δ=0.82)을 **매 3번째 점으로 정확히 포함**한다 → 같은 "
                           "주파수에서 v1↔v2 짝비교가 된다."),
            settings_identical_to_v1=dict(
                div=True, n_az=True, jitter=True, penetrate=True, max_bounce=True,
                ptd=True, statistic=True, band=True,
                differences=["메쉬(사진 실측 재구축)", f"주파수 21점 → {int(f.size)}점", "el=0 만 계산"]),
            mesh=fp, mesh_v1_note="구판 메쉬는 phantom4 형상표 상속본(28,160 삼각형)",
            gpus=GPUS, procs_per_gpu=PROCS_PER_GPU, gpu_mem_budget_mb=MEM_MB,
            wall_clock_s=round(time.time() - t0, 1),
            runtime_s_total_process=round(sum(freq[key[x]]["runtime_s"] for x in f), 1),
        ),
        elevation_convention=v1.get("elevation_convention"),
        aspects=dict(el0=dict(el_deg=0.0, freq=freq, n_freq=int(f.size))),
        headline=dict(
            quantity="mu(f) = 10*log10(mean_az sigma_lin)   [dBsm],  f in GHz  (**선형평균**)",
            reference_aspect="el0  (theta=90 수평면, 방위 전주기)",
            a_ours_db_per_ghz=fit_mu["a"], b_ours_dbsm=fit_mu["b"], R2=fit_mu["R2"],
            rmse_db=fit_mu["rmse_db"], se_a=fit_mu["se_a"], n_freq=int(f.size),
            eps_fit=dict(c_db_per_ghz=fit_eps["a"], d_db=fit_eps["b"], R2=fit_eps["R2"]),
            mu_hat_at={k: float(fit_mu["a"] * v + fit_mu["b"]) for k, v in COMM.items()},
            fit_on_v1_21pt_subgrid=fit_on_v1grid,
        ),
        fit=dict(el0=dict(el_deg=0.0, n_points=int(f.size),
                          freqs_ghz=[float(x) for x in f],
                          mu_dbsm=[float(x) for x in mu], eps_db=[float(x) for x in eps],
                          a_mu_db_per_ghz=fit_mu["a"], b_mu_dbsm=fit_mu["b"],
                          R2_mu=fit_mu["R2"], rmse_mu_db=fit_mu["rmse_db"], se_a=fit_mu["se_a"],
                          c_eps_db_per_ghz=fit_eps["a"], d_eps_db=fit_eps["b"],
                          R2_eps=fit_eps["R2"], rmse_eps_db=fit_eps["rmse_db"])),
        subband_fits=dict(note=v1["subband_fits"]["note"], by_aspect=dict(el0=sub)),
        distribution_summary=dict(
            n_cases=int(f.size), best_by_CvM_tally=tally,
            percentiles_norm_db=dict(
                P10_mean=round(float(p10.mean()), 3), P10_min=round(float(p10.min()), 3),
                P10_max=round(float(p10.max()), 3), P1_mean=round(float(p1.mean()), 3),
                P1_min=round(float(p1.min()), 3), P1_max=round(float(p1.max()), 3),
                swerling_exponential_theory=dict(P10=-9.77, P1=-19.98),
                meaning="평균전력으로 정규화한 σ 의 하위 10%/1% 분위점."),
            eps_db_stats=dict(mean=round(float(eps.mean()), 3), min=round(float(eps.min()), 3),
                              max=round(float(eps.max()), 3)),
            linear_minus_dB_domain_mean_db=dict(
                mean=round(float(lin_minus.mean()), 3), min=round(float(lin_minus.min()), 3),
                max=round(float(lin_minus.max()), 3),
                note="μ(선형평균) − mean(dB영역). 지수분포 이론 오프셋 2.507 dB."),
        ),
        elevation_lobe=dict(
            note=("⚠ v2 는 el=0 만 돌렸다 — 고도 로브 절은 구판 outputs/p3_ours.json 을 볼 것. "
                  "대조(Yuan θ90)에 쓰이는 컷은 el=0 하나이므로 이 판의 결론에는 안 닿는다."),
            a_mu_by_elevation_db_per_ghz=v1["elevation_lobe"]["a_mu_by_elevation_db_per_ghz"],
            from_v1=True),
        caveats=v1.get("caveats"),
    )
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT, flush=True)
    print(f"a={fit_mu['a']:+.4f} ± {fit_mu['se_a']:.4f}  b={fit_mu['b']:.3f}  "
          f"R2={fit_mu['R2']:.3f}  rmse={fit_mu['rmse_db']:.3f}  n={f.size}", flush=True)
    if fit_on_v1grid:
        print(f"v1격자 21점 재적합: a={fit_on_v1grid['a']:+.4f} ± {fit_on_v1grid['se_a']:.4f}", flush=True)


if __name__ == "__main__":
    main()
