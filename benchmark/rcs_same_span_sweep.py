# -*- coding: utf-8 -*-
"""
rcs_same_span_sweep.py — ⭐«같은 구간을 적합하라» 를 닫는다: 2~18 GHz 스윕.

왜
--
Das (IEEE WCL 2026) 의 Phantom 3 기울기 0.21 dB/GHz 는 **2~18 GHz** 적합이고,
우리 것(0.17~1.57)은 **1.8~6.0 GHz** 적합이었다 — 구간이 4배 달라 비교를 못 닫았다
(덱 v1 1부가 그렇게 정직하게 적었다). 이 스윕이 우리 μ(f)를 **그들 구간 전체**에서 내
같은 구간·같은 통계(선형 방위평균)로 기울기를 다시 적합한다.

설계
----
  주파수   2.0 ~ 18.0 GHz, 0.5 GHz 간격(33점)
  기체     matrice4e(1차 실측 표적) · mini5pro(2차) · phantom4(⭐Das 표적 Phantom 3 의 최근접)
  통계     el=0 방위면 360점, 선형평균 → μ = 10log10(mean σ) — Das §III-1 규약
  엔진     rcs_sbr_batch (가림 + 각도의존 Γ(θ) 켬, jitter=2, penetrate=True)
  ⚠ PO 유효성: 하한(특징폭 ≥0.729λ)은 고주파로 갈수록 오히려 여유가 커진다.
    대신 메쉬 이산화가 조여진다 — 18 GHz 에서 λ=16.7 mm, 우리 변 중앙 ~3 mm = 0.18λ (허용).
  ⚠ Γ(θ) 는 방위평균을 +0.1~0.33 dB 만 움직인다(실측) — 기울기 비교에는 중립적.

    python benchmark/rcs_same_span_sweep.py
"""
from __future__ import annotations
import json, os, sys, time
os.environ.setdefault("SIONNA2_GPU", "2")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from gpu import pick                                                   # noqa: E402
pick(verbose=True)
import numpy as np                                                     # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, build_drone                # noqa: E402
import rcs_sbr as RS                                                   # noqa: E402

GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
FREQS = np.arange(2.0, 18.01, 0.5) * 1e9
AZ = np.linspace(0, 360, 360, endpoint=False)
KEYS = ["matrice4e", "mini5pro", "phantom4"]
DAS = {"slope": 0.21, "band": [1.8, 18.2], "cite": "Das IEEE WCL 2026, Phantom 3, dB az-mean"}

out = {"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "freqs_ghz": (FREQS / 1e9).tolist(), "n_az": len(AZ), "el_deg": 0.0,
                 "engine": "rcs_sbr_batch · penetrate=True · jitter=2 · ANGLE_GAMMA=on",
                 "statistic": "10log10(mean_az sigma_lin) — Das §III-1 규약",
                 "why_ko": "Das 와 같은 2~18 GHz 구간에서 기울기를 적합해 «구간이 다르다» 비교 불능을 닫는다",
                 "das_anchor": DAS}, "drones": {}}
for key in KEYS:
    spec = DRONES[key]; mesh = build_drone(spec)
    mu = []
    t0 = time.time()
    for fc in FREQS:
        s = np.asarray(RS.rcs_sbr_batch(mesh, GM, float(fc), AZ, el_deg=0.0), float)
        mu.append(10 * np.log10(max(s.mean(), 1e-30)))
        print(f"  {spec.name:16s} {fc/1e9:5.1f} GHz  mu {mu[-1]:7.2f} dBsm  "
              f"({time.time()-t0:.0f}s)", flush=True)
    mu = np.array(mu); f_ghz = FREQS / 1e9
    def fit(lo, hi):
        m = (f_ghz >= lo) & (f_ghz <= hi)
        a, b = np.polyfit(f_ghz[m], mu[m], 1)
        r = np.corrcoef(f_ghz[m], mu[m])[0, 1] ** 2
        return {"a_db_per_ghz": float(a), "b_dbsm": float(b), "r2": float(r),
                "span_ghz": [lo, hi], "n": int(m.sum())}
    out["drones"][key] = {"name": spec.name, "mu_dbsm": mu.tolist(),
                          "fit_full_2_18": fit(2.0, 18.0),
                          "fit_low_2_6": fit(2.0, 6.0),
                          "seconds": round(time.time() - t0, 1)}
    ff, fl = out["drones"][key]["fit_full_2_18"], out["drones"][key]["fit_low_2_6"]
    print(f"  ⭐{spec.name}: 전구간(2~18) a={ff['a_db_per_ghz']:+.3f} dB/GHz (R²{ff['r2']:.2f}) · "
          f"저구간(2~6) a={fl['a_db_per_ghz']:+.3f} · Das {DAS['slope']}", flush=True)
json.dump(out, open(f"{ROOT}/outputs/rcs_same_span.json", "w"), ensure_ascii=False, indent=1)
print("\n✅ outputs/rcs_same_span.json")
