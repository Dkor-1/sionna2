# -*- coding: utf-8 -*-
"""
compare_kernels_0820.py — 옛 커널(`ours`) ↔ 새 GPU 커널(`ours_gpu`) 전면 대조
================================================================================

⛔**팀미팅 덱에는 안 싣는다.** 이건 «두 커널이 같은 결론을 내는가» 를 원장에 남기는 것이다.

왜 필요한가
-----------
`ours_gpu` 는 물리를 그대로 두고 계산 장소만 GPU 로 옮긴 판이다(3.66 배). 그런데 GPU 가
float32 라 **비트 동일이 아니다** — σ 최대차 0.0009 dB 수준이다. 자세 몇 개로는 «작다» 를
확인했지만, **생산 길이(4,096 자세) × 조합 24 종**에서도 그러한지는 안 봤다.

⭐오늘 여러 번 겪었다 — 「자세 32 개로 재서 0.1 % 꼬리를 놓친」 사례가 실제로 있었다
  (개선 커널 K 묶기: 32 자세에서 0.0007 dB → 512 자세에서 0.328 dB, **500 배**).
  그래서 이 대조는 **전 자세**를 본다.

무엇을 보나 — σ 가 아니라 **우리가 실제로 쓰는 숫자**
-----------------------------------------------------
  · 하류 잣대: 빗살 대비 · 리듬 몫 · AC 세기 (`build_md_atlas` 정본 함수 그대로)
  · 자세별 σ 차이의 **분포**(중앙값·p99·최대) — 꼬리를 봐야 한다
  · ⭐**상대 패턴** 차 — 평균을 뺀 뒤의 차이. 마이크로도플러가 쓰는 것이 이것이다.

판정선
------
  · 하류 잣대 : 판정 막대 **2.68 dB** 의 1/100 = 0.0268
  · 상대 패턴 : 그 앙각의 **격자 산포 밴드**(−30° 1.161 dB 등)의 1/10
    ⛔절대 σ 는 판정에 안 쓴다 — 애초에 격자에 1.4 dB 흔들리는 양이다.

실행: python benchmark/compare_kernels_0820.py
산출: outputs/compare_kernels_0820.json
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_md_atlas as A                                      # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "compare_kernels_0820.json")
TAG = "mfixbatteryi5_blperairframe"
FFL = 126.66666666666667
TOL_METRIC = 0.0268          # 판정 막대 2.68 dB 의 1/100
#: 정본 메쉬의 격자 산포 밴드 [dB] — 상대 패턴 판정선은 이것의 1/10
GRID_BAND = {0: 3.86, -15: 1.31, -30: 1.161, -45: 0.09, -52: 0.018,
             -60: 0.02, -68: 0.091, -75: 0.10, -82: 0.120, -90: 5.62}

PAT = re.compile(r"^(?P<eng>ours_gpu|ours)(?P<dr>_(?:mavic4pro|mini5pro|s1000plus|matrice4e))?"
                 r"_r(?P<r>[\d.]+)_n(?P<n>\d+)(?P<rot>_rot[a-z_0-9]+?)?"
                 rf"_{TAG}(?P<div>_div\d+)?_el(?P<el>[+-]\d+)_(?P<sh>\d+)\.npz$")


def f_tip_at(el: float) -> float:
    return 1101.6 / np.cos(np.radians(-30.0)) * np.cos(np.radians(el))


def _f(v):
    if v is None:
        return None
    return float(v[0]) if isinstance(v, (tuple, list)) else float(v)


def load_cell(eng, dr, rot, div, el):
    """한 칸의 모든 샤드를 이어 붙인다. ⭐결측이 있으면 **안 쓴다**(0 이 섞이면 잣대가 거짓)."""
    pat = f"{SHD}/{eng}{dr}_r15_n8192{rot}_{TAG}{div}_el{el:+d}_*.npz"
    fs = sorted(glob.glob(pat))
    if not fs:
        return None
    E = seen = None
    for f in fs:
        d = np.load(f)
        n = int(np.asarray(d["meta"], float)[3])
        if E is None:
            E = np.zeros(n, complex); seen = np.zeros(n, bool)
        ii = d["idx"].astype(int)
        E[ii] = d["E"]; seen[ii] = True
    if not seen.all():
        return None                       # ⛔덜 찬 칸은 비교 안 한다
    return E


def metrics(E, el):
    ft = f_tip_at(el)
    return dict(ac_db=float(10 * np.log10((np.abs(E - E.mean()) ** 2).mean())),
                rhythm_pct=_f(A.rhythm_share(E, FFL, ft)),
                comb_db=_f(A.comb_contrast_db(E, FFL, ft)))


def main():
    # 옛 판이 있는 칸을 모으고, 같은 설정의 새 판을 찾는다
    keys = collections.defaultdict(set)
    for f in glob.glob(f"{SHD}/ours*_el*.npz"):
        m = PAT.match(os.path.basename(f))
        if not m or m.group("r") != "15" or m.group("n") != "8192":
            continue
        keys[(m.group("dr") or "", m.group("rot") or "", m.group("div") or "")]\
            .add(int(m.group("el")))

    rows, miss = [], []
    for (dr, rot, div), els in sorted(keys.items()):
        for el in sorted(els, reverse=True):
            Eo = load_cell("ours", dr, rot, div, el)
            En = load_cell("ours_gpu", dr, rot, div, el)
            if Eo is None or En is None or Eo.shape != En.shape:
                miss.append(dict(drone=(dr[1:] or "matrice4e"), rot=(rot[4:] or "none"),
                                 div=(div[1:] or ""), el=el,
                                 why=("옛 판 없음/덜참" if Eo is None else
                                      ("새 판 없음/덜참" if En is None else "길이 불일치"))))
                continue
            so = 20 * np.log10(np.abs(Eo) + 1e-300)
            sn = 20 * np.log10(np.abs(En) + 1e-300)
            dsig = np.abs(sn - so)
            drel = np.abs((sn - sn.mean()) - (so - so.mean()))     # ⭐상대 패턴
            mo, mn = metrics(Eo, el), metrics(En, el)
            dm = {k: (None if (mo[k] is None or mn[k] is None) else abs(mn[k] - mo[k]))
                  for k in mo}
            band = GRID_BAND.get(el)
            lim = None if band is None else band / 10.0
            ok = all((dm[k] is None) or (dm[k] <= TOL_METRIC) for k in dm) \
                and (lim is None or float(drel.max()) <= lim)
            rows.append(dict(
                drone=(dr[1:] or "matrice4e"), rot=(rot[4:] or "none"),
                div=(div[1:] or ""), el=el, n_poses=int(Eo.size),
                sigma_med_db=round(float(np.median(dsig)), 6),
                sigma_p99_db=round(float(np.percentile(dsig, 99)), 6),
                sigma_max_db=round(float(dsig.max()), 6),
                rel_max_db=round(float(drel.max()), 6),
                grid_band_db=band, rel_limit_db=lim,
                metric_delta={k: (None if v is None else round(v, 6)) for k, v in dm.items()},
                metrics_old=mo, metrics_new=mn, ok=bool(ok)))

    bad = [r for r in rows if not r["ok"]]
    doc = {"_meta": {
        "generator": "benchmark/compare_kernels_0820.py",
        "role_ko": "옛 ours ↔ 새 ours_gpu 전면 대조 — ⛔팀미팅 덱에는 안 싣는다",
        "judge_ko": (f"하류 잣대 {TOL_METRIC} dB(판정 막대 2.68 의 1/100) · "
                     f"상대 패턴은 그 앙각 격자 밴드의 1/10"),
        "why_not_absolute_ko": "절대 σ 는 애초에 격자에 최대 1.4 dB 흔들려 판정에 못 쓴다",
        "n_cells": len(rows), "n_fail": len(bad), "n_missing": len(miss)},
        "cells": rows, "missing": miss[:40]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"═══ 옛 ours ↔ 새 ours_gpu · 짝지어진 칸 {len(rows)} ═══")
    if rows:
        print(f"  {'기체':10s}{'로터':14s}{'앙각':>5s}{'σ중앙':>9s}{'σp99':>9s}"
              f"{'⭐상대차':>9s}{'한계':>8s}{'빗살차':>9s}  판정")
        for r in rows:
            lim = "—" if r["rel_limit_db"] is None else f"{r['rel_limit_db']:.4f}"
            cb = "—" if r["metric_delta"]["comb_db"] is None else f"{r['metric_delta']['comb_db']:.5f}"
            print(f"  {r['drone']:10s}{(r['rot']+('/'+r['div'] if r['div'] else '')):14s}"
                  f"{r['el']:5d}{r['sigma_med_db']:9.5f}{r['sigma_p99_db']:9.5f}"
                  f"{r['rel_max_db']:9.5f}{lim:>8s}{cb:>9s}  {'✅' if r['ok'] else '⛔'}")
    print(f"\n  칸 {len(rows)} · 실패 {len(bad)} · 아직 짝 없음 {len(miss)}")
    print(f"  ⭐{'✅ 두 커널이 같은 결론을 낸다' if rows and not bad else ('⛔ 갈리는 칸이 있다' if bad else '⚠비교할 칸이 없다')}")
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
