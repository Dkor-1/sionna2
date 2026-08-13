# -*- coding: utf-8 -*-
"""shard 21개 → 정본 `outputs/report13_sigma_grid.json` 재조립 + 앵커·신뢰도·파생 재계산.

생산자(`experiment_freespace_sigma`)의 함수를 그대로 불러 meta 를 만들고, 옛 파일의 축 설정
(div·jitter·penetrate·n_f·el/az 격자·통계규약)이 그대로인지 **대조해서 다르면 멈춘다**.
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = "/workspace/sionna"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")
OLD = os.path.join(ROOT, "outputs", "archive", "report13_sigma_grid_pre0803.json")
DRONES = ["mini5pro", "phantom4", "mavic4pro", "matrice4e", "s1000plus", "typhoonh480", "x500v2"]
BANDS = ["lte", "nr", "wifi"]


def main():
    import experiment_freespace_sigma as X
    from channel import _mesh_fp

    old = json.load(open(OLD))
    om = old["meta"]
    # ── 설정 일치 검사(비교가 성립하려면 축·엔진이 같아야 한다) ──
    assert int(om["div"]) == X.DIV, f"div {om['div']} vs {X.DIV}"
    assert int(om["jitter"]) == X.JITTER, "jitter 불일치"
    assert int(om["n_f"]) == X.N_F and abs(om["frac_bw"] - X.FRAC_BW) < 1e-12, "밴드평균 불일치"
    assert abs(om["smooth_deg"] - X.SMOOTH_DEG) < 1e-12, "평활 불일치"
    assert np.allclose(om["az_deg"], X.AZ_GRID) and np.allclose(om["el_deg"], X.EL_GRID), "격자 불일치"
    assert [b[0] for b in om["bands"]] == [b[0] for b in X.BANDS], "밴드 불일치"

    grid, rt, fps = {}, 0.0, {}
    for d in DRONES:
        grid[d] = {}
        for b in BANDS:
            p = os.path.join(SCRATCH, f"sigma_{d}_{b}.json")
            if not os.path.exists(p):
                print(f"  ✗ 없음: {d}/{b}")
                continue
            sh = json.load(open(p))
            assert sh["done"], f"{d}/{b} 미완"
            grid[d][sh["band"]] = sh["node"]
            rt += sh["runtime_s"]
            fps[d] = sh["mesh_fp"]
        if not grid[d]:
            del grid[d]
    print(f"  샤드 {sum(len(v) for v in grid.values())}칸 · 워커 CPU시간 합 {rt/3600:.2f} h")

    # 지문이 계산 도중에 바뀌지 않았는지(다른 워크플로가 메쉬를 고쳤는지) 확인
    now = {d: _mesh_fp(d) for d in grid}
    drift = {d: (fps[d], now[d]) for d in grid if fps[d] != now[d]}

    bands = list(X.BANDS)
    meta = X._meta(X.AZ_GRID, X.EL_GRID, X.N_F, X.DIV, X.SMOOTH_DEG, bands, "direct",
                   extra=dict(smoke=False))
    meta["engine"] = om["engine"]
    meta["mesh_fp"] = now
    meta["mesh_generation"] = "2026-08-03 (drone_cad/drones working tree, uncommitted)"
    meta["regenerated_from"] = "shards: (drone x band), src/experiment_freespace_sigma._sigma_grid_one"
    meta["regen_note"] = ("el 을 한 줄씩 잘라 부른 것 외에는 생산자 경로와 동일 — 3° 평활이 az 행 "
                          "단위로 독립이라 9줄 일괄호출과 비트 동일하다.")
    meta["predecessor"] = "outputs/archive/report13_sigma_grid_pre0803.json (2026-07-29 판)"
    meta["worker_cpu_hours"] = round(rt / 3600.0, 3)
    meta["drones"] = list(grid)

    out = {"meta": meta, "sigma": {"grid": grid}}
    out["sigma_confidence"] = X.sigma_confidence(list(grid), bands)
    try:
        dl = X.anchor_deltas(grid, drones=list(grid))
        out["sigma"]["anchor"] = dl
        out["sigma"]["anchor"]["applied_default"] = dict(
            mode=X.ANCHOR_MODE_DEFAULT, branch=X.ANCHOR_BRANCH_DEFAULT,
            consumer=("experiment_freespace_range._sigma_at 가 조회 σ 에 apply_anchor 를 곱한다"),
            switch="anchor_on (기본 켬); 끄면 delta=0 = 수리 전 거동")
        print(f"  [anchor] relevel 대조 max|Δ| = {dl['relevel_crosscheck_max_abs_db']:.2e} dB")
    except Exception as e:
        print(f"  [anchor] skip: {type(e).__name__}: {e}")
    X._derive_aggregates(out)

    ms = os.path.join(SCRATCH, "multistatic.json")
    if os.path.exists(ms):
        out["multistatic"] = json.load(open(ms))
        X._derive_aggregates(out)
        meta["multistatic_regenerated"] = True
    else:
        meta["multistatic_regenerated"] = False
        meta["multistatic_note"] = ("옛 판의 multistatic 블록은 같은 메쉬 낡음을 그대로 안고 있어 "
                                    "옮겨 싣지 않았다 — 필요하면 multistatic_check 로 재생성할 것.")
    if drift:
        meta["mesh_fp_drift_during_run"] = drift

    tmp = OUT + ".tmp"
    json.dump(out, open(tmp, "w"))
    os.replace(tmp, OUT)
    print(f"  → {OUT}  ({os.path.getsize(OUT)/1e6:.2f} MB)  drift={drift}")
    return out


if __name__ == "__main__":
    main()
