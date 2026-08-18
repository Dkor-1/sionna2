# -*- coding: utf-8 -*-
"""
rotor_ladder_measured_0818.py — 로터 요동을 실제만큼 넣으면 잣대가 어떻게 되나 (**실측**)
================================================================================

2 장(로터)의 헤드라인은 지금까지 **계산식**뿐이었다 — 운동학 게이트가
«산포 σ_s 면 배음 k 에서 k·σ_s·f_flash 만큼 어긋나므로 고정 격자에 k_max 까지만 들어간다»
를 종이로 푼 것이다(`noise_main_gates.kinematics_gate`).

이 파일은 그것을 **실제로 돌린 시계열**로 다시 잰다. 큐가 프리셋마다 판을 냈다:

  요동 없음(현행 원장) · legacy(σ_s 0.22 %) · outdoor(2.35 %) · outdoor_v2(5.3 %)
  그리고 outdoor_v2 는 **씨앗 두 개** — «프리셋이 바꾼 것» 과 «이번 추첨이 그런 것» 을 가른다.

⭐잣대 식은 다시 구현하지 않는다 — `build_md_atlas`(정본) 함수를 그대로 쓴다.
⭐예측(계산식)과 실측을 **나란히** 낸다. 어긋나면 그것이 발견이다.

⛔GPU 없음. 산출: outputs/rotor_ladder_measured_0818.json

실행: PYTHONPATH=src:benchmark python benchmark/rotor_ladder_measured_0818.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_md_atlas as A                                             # noqa: E402
import noise_main_gates as G                                           # noqa: E402
import rotor_dynamics as R                                             # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "rotor_ladder_measured_0818.json")

TAG = "mfixbatteryi5_blperairframe"
BASE = f"ours_r15_n8192_{TAG}"                    # 요동 없음(현행 원장)
FFL = 126.66666666666667
ELS = (0, -30, -60)

#: (표시 이름, 팔 접미사, 프리셋 이름) — 프리셋 이름이 None 이면 요동 없음
LADDER = [
    ("요동 없음 (현행 원장)", "", None),
    ("legacy",       "_rotlegacy",       "legacy"),
    ("outdoor",      "_rotoutdoor",      "outdoor"),
    ("outdoor_v2",   "_rotoutdoor_v2",   "outdoor_v2"),
    ("outdoor_v2 (씨앗 1)", "_rotoutdoor_v2s1", "outdoor_v2"),
]


def load(arm: str, el: int):
    """샤드 → (시계열, 결측 수). ⭐결측이 있으면 세어서 함께 돌려준다."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+d}_*.npz"))
    if not fs:
        return None, None
    E = seen = None
    for f in fs:
        d = np.load(f)
        n = int(np.asarray(d["meta"], float)[3])
        if E is None:
            E = np.zeros(n, complex)
            seen = np.zeros(n, bool)
        ii = d["idx"].astype(int)
        E[ii] = d["E"]
        seen[ii] = True
    return E, int((~seen).sum())


def f_tip_at(el: int) -> float:
    return 1101.6 / np.cos(np.radians(-30.0)) * np.cos(np.radians(el))


def scalar(v):
    if v is None:
        return None
    return float(v[0]) if isinstance(v, (tuple, list)) else float(v)


def main():
    t0 = time.time()
    cells, missing = {}, []
    for el in ELS:
        ft = f_tip_at(el)
        row = {}
        for label, suf, pre in LADDER:
            arm = BASE if not suf else f"ours_r15_n8192{suf}_{TAG}"
            E, miss = load(arm, el)
            if E is None:
                missing.append(dict(el_deg=el, arm=arm, why="샤드 없음"))
                continue
            if miss:
                # ⛔결측을 0 으로 두고 재면 주기 무늬가 생긴다(0818 사고) — 아예 안 잰다
                missing.append(dict(el_deg=el, arm=arm, n_missing=miss,
                                    why="결측 자세 — 채워질 때까지 재지 않는다"))
                continue
            comb = scalar(A.comb_contrast_db(E, FFL, ft))
            rhy = scalar(A.rhythm_share(E, FFL, ft))
            ac = float(10 * np.log10((np.abs(E - E.mean()) ** 2).mean()))
            row[label] = dict(arm=arm, comb_contrast_db=(None if comb is None else round(comb, 2)),
                              rhythm_share_pct=(None if rhy is None else round(rhy, 2)),
                              ac_db=round(ac, 2),
                              sigma_s=(None if pre is None else round(R.get(pre).static_sigma, 5)),
                              sigma_w=(None if pre is None else round(R.get(pre).wobble_sigma, 5)))
        if row:
            cells[str(el)] = row

    # ── 계산식(운동학 게이트)의 예측을 나란히 ────────────────────────────
    pred = {}
    for label, suf, pre in LADDER:
        ss = (G.sigma_s_from_ledger()["sigma_s"] if pre is None else R.get(pre).static_sigma)
        g = G.kinematics_gate(FFL, f_tip_at(-30), ss)
        pred[label] = dict(sigma_s=round(ss, 5), k_max_fixed_grid=g["k_max_fixed_grid"],
                           k_top=g["k_top"], spread_at_k_top_hz=g["spread_at_k_top_hz"],
                           verdict_ko=g["verdict_ko"])

    # ── 씨앗 대조 — «프리셋» 인가 «이번 추첨» 인가 ────────────────────────
    seed_check = {}
    for el, row in cells.items():
        a = row.get("outdoor_v2"); b = row.get("outdoor_v2 (씨앗 1)")
        if a and b and a["comb_contrast_db"] is not None and b["comb_contrast_db"] is not None:
            seed_check[el] = dict(
                comb_seed0=a["comb_contrast_db"], comb_seed1=b["comb_contrast_db"],
                d_comb_db=round(abs(b["comb_contrast_db"] - a["comb_contrast_db"]), 2),
                rhythm_seed0=a["rhythm_share_pct"], rhythm_seed1=b["rhythm_share_pct"],
                d_rhythm_pp=round(abs(b["rhythm_share_pct"] - a["rhythm_share_pct"]), 2))

    doc = {"_meta": {
        "generator": "benchmark/rotor_ladder_measured_0818.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "로터 요동 프리셋 사다리 — 계산식이 아니라 **실제로 돌린 시계열**로 잰다",
        "gpu_used": False,
        "metric_source_ko": "잣대 식은 build_md_atlas(정본) 함수를 그대로 씀",
        "elapsed_s": round(time.time() - t0, 2)},
        "measured": cells,
        "predicted_by_kinematics_gate": pred,
        "seed_control": seed_check,
        "seed_rule_ko": ("⭐씨앗만 바꾼 두 판의 차이가 프리셋 사이 차이보다 작아야 "
                         "«프리셋이 바꾼 것» 이라 말할 수 있다"),
        "not_measured": missing}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print("═══ 실측 — 로터 요동을 키우면 잣대가 어떻게 되나 ═══")
    for el, row in cells.items():
        print(f"\n  ── 앙각 {el}° (f_tip {f_tip_at(int(el)):.0f} Hz)")
        print(f"     {'프리셋':22s} {'σ_s':>7s} {'빗살 대비':>10s} {'리듬 몫':>9s} {'움직임 dB':>10s}")
        for label, _s, _p in LADDER:
            v = row.get(label)
            if not v:
                continue
            ss = "—" if v["sigma_s"] is None else f"{v['sigma_s']*100:.2f}%"
            cb = "—" if v["comb_contrast_db"] is None else f"{v['comb_contrast_db']:.2f}"
            print(f"     {label:22s} {ss:>7s} {cb:>10s} {v['rhythm_share_pct']:8.2f}% "
                  f"{v['ac_db']:10.2f}")
    print("\n═══ 계산식(운동학 게이트)의 예측 — 고정 격자에 들어가는 배음 ═══")
    for label, v in pred.items():
        print(f"  {label:22s} σ_s {v['sigma_s']*100:5.2f}% → k_max {v['k_max_fixed_grid']:6.2f} "
              f"(쓸 배음 k_top {v['k_top']})")
    if seed_check:
        print("\n═══ 씨앗 대조 — 프리셋이 바꾼 것인가 이번 추첨인가 ═══")
        for el, v in seed_check.items():
            print(f"  앙각 {el}° : 빗살 {v['comb_seed0']} ↔ {v['comb_seed1']} "
                  f"(차 {v['d_comb_db']} dB) · 리듬 차 {v['d_rhythm_pp']} %p")
    if missing:
        print(f"\n⚠안 잰 칸 {len(missing)} 개 (결측·샤드 없음)")
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
