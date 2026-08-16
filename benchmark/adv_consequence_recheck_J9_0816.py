# -*- coding: utf-8 -*-
"""
adv_consequence_recheck_J9_0816.py — 분류 축을 **발표된 6 클래스**로 다시 (2026-08-16)
=======================================================================================

왜 필요한가
-----------
저장소가 발표한 마이크로도플러 분류(`outputs/md_classify.json`)는 **6 기체**를 가른다:
mini2 · mini5pro · phantom4 · matrice4e · typhoonh480 · s1000plus.
그리고 그 판정의 핵심 문장은 «플래시(로터 회전수)가 전부가 아니다» 다 — f_flash 를 뺀
`geometry_only` 팔이 23 개 **형상 유래 특징**만으로 79.5 % 를 낸다(우연 16.7 %).
바로 그 팔이 날 형상 법칙 교체에 노출된 팔이다. 앞 라운드는 3 기체만 봤다.

여기서 재는 것
--------------
  ① 판마다 6 기체를 **다시 지어** 클래스 간 거리를 잰다 — 간격이 좁아지나(=분류가 죽나)
  ② 전체 27 특징 / geometry_only 23 특징 두 벌로 각각
  ③ «판이 섞이면 위험하다» 를 직접 시험 — legacy 로 학습한 것(발표된 클래스 평균)에
     새 판으로 지은 벡터를 넣으면 자기 클래스로 돌아오나(최근접 클래스평균)

규약: CPU 전용 · 소스 무변경 · 순수 PO(가림 없음) · 단일 방위(az 0)·단일 창.
    ⚠ 절대 정확도를 발표값과 비교하면 안 된다(팔이 다르다). 비교는 **판 사이**만.
조각 산출: outputs/_J9_sixclass_0816.json
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adv_consequence_recheck_0816 as R                                   # noqa: E402
from drones import DRONES                                                   # noqa: E402

SIX = ["mini2", "mini5pro", "phantom4", "matrice4e", "typhoonh480", "s1000plus"]
GEOM_ONLY = ["m_cent", "m_rms", "dc_over_ac_db", "env_kurtosis", "asym",
             "h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8", "h9", "h10", "h11", "h12",
             "fold_h1", "fold_h2", "fold_h3", "fold_h4", "fold_h5", "fold_h6"]
ELS = [-30.0, 0.0]
WIN = 4925


def main():
    t0 = time.time()
    from md_classify_dataset import features, FEATURE_NAMES as FEATS
    stats = json.load(open(os.path.join(ROOT, "outputs", "md_classify.json")))["feature_stats"]
    names = list(FEATS)

    vec = {}
    for key in SIX:
        spec = DRONES[key]
        for law in R.LAWS:
            res, _ = R.slowtime(spec, law, ELS, n_poses=R.N_POSES)
            for el in ELS:
                v, _ = features(res[el]["E"][:WIN], R.PRF)
                vec[(key, law, el)] = np.asarray(v, float)
            print(f"  J9 {key}/{law} {time.time()-t0:.1f}s", flush=True)

    def zdist(a, b, el, law, feat_names):
        """클래스 간 거리 — 발표된 클래스내 표준편차를 자로."""
        sq, used = 0.0, 0
        for nm in feat_names:
            st = stats.get(nm)
            if not st or a not in st or b not in st:
                continue
            sd = math.sqrt(0.5 * (st[a]["std"] ** 2 + st[b]["std"] ** 2))
            if sd <= 0:
                continue
            i = names.index(nm)
            sq += ((vec[(a, law, el)][i] - vec[(b, law, el)][i]) / sd) ** 2
            used += 1
        return math.sqrt(sq), used

    out = {}
    for el in ELS:
        per_set = {}
        for setname, fset in (("all27", names), ("geometry_only23", GEOM_ONLY)):
            per_law = {}
            for law in R.LAWS:
                pairs = {}
                for i in range(len(SIX)):
                    for j in range(i + 1, len(SIX)):
                        d, n = zdist(SIX[i], SIX[j], el, law, fset)
                        pairs[f"{SIX[i]}|{SIX[j]}"] = round(d, 3)
                vals = np.array(list(pairs.values()))
                per_law[law] = dict(pairs=pairs, min_pair_z=round(float(vals.min()), 3),
                                    median_pair_z=round(float(np.median(vals)), 3),
                                    n_features_used=n)
            per_set[setname] = dict(
                per_law=per_law,
                change_vs_legacy={
                    law: dict(
                        d_min_pair_z=round(per_law[law]["min_pair_z"]
                                           - per_law["legacy"]["min_pair_z"], 3),
                        ratio_min_pair=round(per_law[law]["min_pair_z"]
                                             / max(per_law["legacy"]["min_pair_z"], 1e-9), 4),
                        ratio_median_pair=round(per_law[law]["median_pair_z"]
                                                / max(per_law["legacy"]["median_pair_z"],
                                                      1e-9), 4),
                        n_pairs_that_shrank=int(sum(
                            1 for k in per_law[law]["pairs"]
                            if per_law[law]["pairs"][k] < per_law["legacy"]["pairs"][k])),
                        n_pairs=len(per_law[law]["pairs"]))
                    for law in R.LAWS[1:]})
        out[f"{el:+.0f}"] = per_set

    #: ③ 판이 섞이면 — 발표된 클래스 평균(=legacy 세대 학습)에 새 판 벡터를 넣는다
    mixed = {}
    for el in ELS:
        per_law = {}
        for law in R.LAWS:
            for setname, fset in (("all27", names), ("geometry_only23", GEOM_ONLY)):
                hit = 0
                assign = {}
                for key in SIX:
                    best, bestd = None, 1e300
                    for cand in SIX:
                        sq, used = 0.0, 0
                        for nm in fset:
                            st = stats.get(nm)
                            if not st or cand not in st or not st[cand].get("std"):
                                continue
                            i = names.index(nm)
                            sq += ((vec[(key, law, el)][i] - st[cand]["mean"])
                                   / st[cand]["std"]) ** 2
                            used += 1
                        d = math.sqrt(sq / max(used, 1))
                        if d < bestd:
                            best, bestd = cand, d
                    assign[key] = best
                    hit += int(best == key)
                per_law[f"{law}/{setname}"] = dict(
                    assign=assign, n_correct=hit, n=len(SIX),
                    accuracy=round(hit / len(SIX), 4))
        mixed[f"{el:+.0f}"] = per_law

    res = dict(
        between_class=out, nearest_class_mean=mixed,
        classes=SIX, window_samples=WIN, els=ELS, laws=R.LAWS,
        caveat_ko="이 팔은 순수 PO·단일 방위·단일 창이라 **절대 정확도**를 발표값과 비교하면 "
                  "안 된다. 여기서 읽을 것은 오직 «판을 갈면 클래스 간 거리가 좁아지는가» 다.",
        elapsed_s=round(time.time() - t0, 1))
    json.dump(res, open(os.path.join(ROOT, "outputs", "_J9_sixclass_0816.json"),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "between_class"},
                     ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    main()
