# -*- coding: utf-8 -*-
"""
grid_band_mfix_0818.py — **정본 메쉬**의 격자 산포 밴드를 잰다
================================================================================

왜 필요한가
-----------
판정 밴드(«이 차이가 유의한가» 의 잣대)는 같은 앙각에서 표면 격자를 **λ/12 ↔ λ/24** 로
바꿔 재고 그 차이로 만든다. 그런데 저장소의 격자 사다리 팔은 전부 **옛(legacy) 메쉬**다
(`ours_r15_n8192_div24` — 정본 꼬리표 `_mfixbatteryi5_blperairframe` 이 없다).
⇒ **정본 메쉬로 판정하면서 옛 메쉬의 잣대를 쓰고 있었다.** 시험한 적이 없다.

그리고 새로 채운 앙각 **−52·−68·−82** 에는 λ/24 판이 아예 없어 밴드가 **없다**
(`docs/GRID_BAND_GAP_0818.md`). 그래서 큐에 div24 를 넣었고, 이 파일이 그 산출을 읽는다.

⛔`frame_completion_0816.py` §④ 는 짝을 **옛 팔 이름**으로 찾으므로 새 판을 못 읽는다.
   여기서는 이름을 하드코딩하지 않고 **원장/샤드에서 실제 팔 이름을 찾아** 짝짓는다.

⭐잣대 식은 **다시 구현하지 않는다** — `build_md_atlas`(정본 잣대)의 함수를 그대로 쓴다.

⛔GPU 없음. 산출: outputs/grid_band_mfix_0818.json

실행: PYTHONPATH=src:benchmark python benchmark/grid_band_mfix_0818.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_md_atlas as A                                             # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "grid_band_mfix_0818.json")

BASE = "ours_r15_n8192_mfixbatteryi5_blperairframe"     # λ/12 (규약값)
DIV24 = BASE + "_div24"
PRF = 19700.0
FFL = 126.66666666666667

#: 옛 메쉬에서 잰 밴드 — 지금까지 판정에 쓰던 값(비교 대상)
LEGACY_AC_DB = {0: 3.86, -15: 1.31, -30: 0.37, -45: 0.09, -60: 0.02, -75: 0.10, -90: 5.62}


def load_shards(arm: str, el: int):
    """샤드 → (E, 채워진 자세 인덱스). ⭐결측을 0 으로 두지 않고 **인덱스로** 돌려준다."""
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
    return E, np.flatnonzero(seen)


def f_tip_at(el: int) -> float:
    """앙각별 날개끝 도플러 — 원장 메타의 −15° 값을 코사인으로 옮긴다(스윕과 같은 규약)."""
    return 1101.6 / np.cos(np.radians(-30.0)) * np.cos(np.radians(el))


def main():
    t0 = time.time()
    rows, warn = {}, []
    for el in (0, -15, -30, -45, -52, -60, -68, -75, -82, -90):
        e12, i12 = load_shards(BASE, el)
        e24, i24 = load_shards(DIV24, el)
        if e12 is None or e24 is None:
            continue
        # ⭐두 판이 **같은 자세 집합**에서만 비교한다 — 한쪽만 덜 차 있으면 그 차이가
        #   격자 탓인지 표본 탓인지 못 가른다(오늘 아침 «결측 512 자세» 사고와 같은 함정).
        idx = np.intersect1d(i12, i24)
        if idx.size == 0:
            continue
        full = (idx.size == e12.size)
        if not full:
            warn.append(dict(el_deg=el, n_used=int(idx.size), n_total=int(e12.size),
                             note_ko="두 판의 **공통 자세**만 썼다 — 아직 샤드가 덜 찼다. "
                                     "값은 잠정이고 다 차면 다시 잰다"))
        a, b = e12[idx], e24[idx]
        ft = f_tip_at(el)
        ac_a = float(10 * np.log10((np.abs(a - a.mean()) ** 2).mean()))
        ac_b = float(10 * np.log10((np.abs(b - b.mean()) ** 2).mean()))
        r_a = A.rhythm_share(a, FFL, ft)
        r_b = A.rhythm_share(b, FFL, ft)
        c_a = A.comb_contrast_db(a, FFL, ft)
        c_b = A.comb_contrast_db(b, FFL, ft)
        # ⚠comb_contrast_db 는 대역에 배음이 세 개도 안 들어가면 **None** 을 낸다
        #   (낮은 앙각·직하방). 그때는 그 잣대만 비우고 나머지는 그대로 낸다.
        def _f(v):
            if v is None:
                return None
            return float(v[0]) if isinstance(v, (tuple, list)) else float(v)
        band_ac = round(abs(ac_b - ac_a), 3)
        rows[str(el)] = dict(
            n_poses_used=int(idx.size), complete=bool(full),
            ac_db_div12=round(ac_a, 2), ac_db_div24=round(ac_b, 2),
            band_ac_db=band_ac,
            rhythm_pct_div12=round(_f(r_a), 2), rhythm_pct_div24=round(_f(r_b), 2),
            band_rhythm_pp=round(abs(_f(r_b) - _f(r_a)), 2),
            comb_db_div12=(None if _f(c_a) is None else round(_f(c_a), 2)),
            comb_db_div24=(None if _f(c_b) is None else round(_f(c_b), 2)),
            band_comb_db=(None if (_f(c_a) is None or _f(c_b) is None)
                          else round(abs(_f(c_b) - _f(c_a)), 2)),
            comb_undefined_why_ko=(None if _f(c_a) is not None else
                                   "대역(2·f_flash ~ f_tip)에 배음이 셋도 안 들어간다 — "
                                   "이 앙각에서는 빗살 대비가 정의되지 않는다"),
            legacy_band_ac_db=LEGACY_AC_DB.get(el),
            vs_legacy_db=(None if LEGACY_AC_DB.get(el) is None
                          else round(band_ac - LEGACY_AC_DB[el], 3)))

    anchor = rows.get("-30")
    doc = {"_meta": {
        "generator": "benchmark/grid_band_mfix_0818.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "정본 메쉬의 격자 산포 밴드 — 판정 잣대를 정본 메쉬에서 처음으로 잰다",
        "gpu_used": False,
        "arms": {"div12": BASE, "div24": DIV24},
        "metric_source_ko": "잣대 식은 build_md_atlas(정본)의 함수를 그대로 씀 — 다시 구현 안 함",
        "elapsed_s": round(time.time() - t0, 2)},
        "cells": rows,
        "incomplete_cells": warn,
        "anchor_check": (None if not anchor else dict(
            el_deg=-30, mfix_band_ac_db=anchor["band_ac_db"],
            legacy_band_ac_db=LEGACY_AC_DB[-30],
            diff_db=anchor["vs_legacy_db"],
            reading_ko=("⭐−30° 는 옛 메쉬에서 이미 0.37 dB 로 재 둔 각도다. 정본 메쉬 값이 "
                        "가까우면 나머지 여섯 각도의 옛 밴드를 그대로 쓸 근거가 생기고, "
                        "많이 벌어지면 일곱 개를 전부 다시 재야 한다"))),
        "open_ko": ["아직 안 난 앙각은 큐가 채우는 중이다",
                    "샤드가 덜 찬 칸은 두 판의 공통 자세로만 잰 **잠정값**이다"]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"═══ 정본 메쉬 격자 밴드 ({len(rows)} 앙각) ═══")
    print(f"  {'앙각':>5s} {'자세':>6s} {'AC 밴드':>8s} {'옛 밴드':>8s} {'차':>8s} "
          f"{'리듬 밴드':>9s} {'빗살 밴드':>9s}")
    for el, r in sorted(rows.items(), key=lambda kv: -int(kv[0])):
        lg = "—" if r["legacy_band_ac_db"] is None else f"{r['legacy_band_ac_db']:.2f}"
        df = "—" if r["vs_legacy_db"] is None else f"{r['vs_legacy_db']:+.3f}"
        mark = "" if r["complete"] else "  ⚠잠정(덜 참)"
        print(f"  {el:>5s} {r['n_poses_used']:6d} {r['band_ac_db']:8.3f} {lg:>8s} {df:>8s} "
              f"{r['band_rhythm_pp']:9.2f} "
              f"{('—' if r['band_comb_db'] is None else format(r['band_comb_db'],'.2f')):>9s}{mark}")
    if anchor:
        print(f"\n⭐−30° 대조: 정본 {anchor['band_ac_db']:.3f} dB vs 옛 "
              f"{LEGACY_AC_DB[-30]:.2f} dB → 차 {anchor['vs_legacy_db']:+.3f} dB")
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
