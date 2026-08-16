# -*- coding: utf-8 -*-
"""정적 산포가 «독립 가우시안 추첨» 인가, 아니면 **요 트림(yaw trim) 구조**인가.

우리 모델은 s_k ~ N(0,σ_s) 를 독립으로 뽑는다. 하지만 쿼드의 물리는 그렇지 않다:
요를 잡으려면 **같은 방향으로 도는 두 로터**가 반대 두 로터보다 빨라야 한다.
PX4 quad_x 모터 순서는 1=우전(CCW) 2=좌후(CCW) 3=좌전(CW) 4=우후(CW) 이므로
회전방향 분할은 esc[0,1] vs esc[2,3] = «01_vs_23» 이다.

시험 셋
  (T1) 세 가지 «둘 vs 둘» 분할 중 01_vs_23 이 실측에서 유독 큰가?
  (T2) 그 몫이 독립 가우시안 귀무분포(모델이 실제로 만드는 것)보다 큰가?
  (T3) 로터별 편차 패턴이 같은 비행 안에서 **일정한가**(= 진짜 트림)인가
       아니면 타일마다 흔들리나(= 계측/우연)?
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
SPLITS = {"01_vs_23": [1, 1, -1, -1], "02_vs_13": [1, -1, 1, -1],
          "03_vs_12": [1, -1, -1, 1]}


def shares(v):
    v = np.asarray(v, float)
    v = v - v.mean()
    tot = float((v ** 2).sum()) + 1e-30
    return {k: float((v @ (np.asarray(p, float) / 2.0)) ** 2 / tot) for k, p in SPLITS.items()}


def load(npz, tagger):
    z = np.load(npz)
    out = {}
    for k in sorted({x.split("__")[0] for x in z.files}):
        rpm = z[f"{k}__rpm"]
        mu = rpm.mean(axis=1)
        out.setdefault(tagger(k), []).append(mu / mu.mean() - 1.0)
    return out


veh = load(f"{HERE}/px4_fleet_corpus.npz", lambda k: k.split("_r")[0])
veh.update(load(f"{HERE}/rotor_corpus.npz",
                lambda k: ("px4_s500" if k.startswith("px4_s500") else
                           "px4_race" if "race" in k else
                           "dregon_meas" if "_meas_" in k else "dregon_cmd")))
hw = {d["log_id"][:8]: (d.get("sys_hw") or "") for d in json.load(open(f"{HERE}/esc_pick.json"))}
hw.update({"px4_s500": "PIXHAWK6C", "px4_race": "KAKUTEH7",
           "dregon_cmd": "MIKROKOPTER", "dregon_meas": "MIKROKOPTER"})

# 귀무분포: 독립 가우시안 s_k (우리 모델이 실제로 뽑는 것)
rng = np.random.default_rng(0)
null = np.array([[shares(rng.normal(0, 1, 4))[k] for k in SPLITS] for _ in range(200000)])
null_max = null.max(axis=1)
print("귀무(독립 가우시안 4개) 분할몫 분포: 각 분할 중앙 %.3f · 최대분할 중앙 %.3f · p95 %.3f"
      % (np.median(null[:, 0]), np.median(null_max), np.percentile(null_max, 95)))
print(f"  01_vs_23 몫이 0.8 을 넘을 확률 = {float((null[:,0]>0.8).mean()):.3f}")
print()
print(f"{'기체':11s}{'hw':17s}{'n':>3s}  {'01v23':>7s}{'02v13':>7s}{'03v12':>7s}"
      f"  {'패턴안정':>8s}  {'범위%':>7s}  판정")
rows = []
n_yaw = 0
real = []
for v, lst in sorted(veh.items()):
    if "SITL" in hw.get(v, "").upper():
        continue
    A = np.array(lst)
    if len(A) < 1:
        continue
    sh = shares(A.mean(axis=0))
    # 패턴 안정성: 타일별 편차벡터끼리의 평균 코사인 유사도
    B = A - A.mean(axis=1, keepdims=True)
    nb = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-30)
    C = nb @ nb.T
    iu = np.triu_indices(len(A), 1)
    stab = float(np.mean(C[iu])) if len(A) > 1 else float("nan")
    rng_pct = float((A.mean(axis=0).max() - A.mean(axis=0).min()) * 100)
    top = max(sh, key=sh.get)
    verdict = ("요트림(01v23) 지배" if top == "01_vs_23" and sh[top] > 0.6 else
               "다른 분할 지배" if sh[top] > 0.6 else "분할 구조 약함")
    n_yaw += int(top == "01_vs_23" and sh[top] > 0.6)
    print(f"{v[:10]:11s}{hw.get(v,'?')[:16]:17s}{len(A):3d}  {sh['01_vs_23']:7.3f}"
          f"{sh['02_vs_13']:7.3f}{sh['03_vs_12']:7.3f}  {stab:8.2f}  {rng_pct:7.2f}  {verdict}")
    rows.append(dict(vehicle=v, hw=hw.get(v, "?"), n=len(A), **sh, stability=stab,
                     range_pct=rng_pct, verdict=verdict))
    real.append(sh["01_vs_23"])

print()
print(f"실기체 {len(rows)}대 중 «01_vs_23(회전방향 쌍) 지배» {n_yaw}대")
print(f"01_vs_23 몫 중앙 {np.median(real):.3f} vs 독립가우시안 귀무 중앙 {np.median(null[:,0]):.3f}")
from scipy import stats                     # noqa: E402
u = stats.mannwhitneyu(real, null[:20000, 0], alternative="greater")
print(f"Mann–Whitney U (실측 > 귀무): p = {u.pvalue:.2e}")
json.dump(rows, open(f"{HERE}/static_structure.json", "w"), indent=1)
