# -*- coding: utf-8 -*-
"""
front_window_0906.py — **정면 창은 얼마나 좁은가**
==========================================================================================
물음
    솔버가 **같은 경로를 여러 줄로 적는** 현상은 az 0°·el 0° 한 점에서만 난다는 것이
    2026-09-05 에 갈렸다. 그 점의 **폭**이 이 물음이다 —
      · 폭이 0.1° 보다 좁으면 축 위 특이점이고, 실제 비행 자세에서는 거의 안 만난다.
      · 0.5° 쯤 되면 호버링 자세 흔들림 안에 들어와 **실제로 만나는 자리**가 된다.

무엇을 재나 — ⭐**두 가지를 함께 적는다**
    자세마다  r = |E| / |E_dedup|  (E_dedup > 0 인 자세만) 을 구해
      ① `share_pct` … r > 1.5 인 **자세의 비율**. 「일어나나 안 일어나나」
      ② `N`         … r 의 중앙값.               「일어난다면 몇 줄로 적히나」
    ⚠**② 만 보면 안 된다.** r 은 작은 정수들의 **혼합**이라, 겹치는 자세가
      100% 여도 2 와 3 의 섞임에 따라 중앙값이 2.0 과 3.0 사이를 오르내린다.
      2026-09-06 에 그 오르내림을 「창이 켜졌다 꺼졌다 한다」로 잘못 읽었다.
      ①로 보면 오르내리지 않는다 — 거의 100% 에서 한 칸 만에 0.0% 로 간다.

⛔**팔을 섞지 않는다.** 팔마다 값이 다르다(방위 0.05° 에서 R0D0E0F1 은 2.00,
  R0D1E1F1 은 7.99). 섞으면 없는 봉우리가 생긴다 — 앞 판의 「0.05° 4.97」이 그것이다.
⛔**표준 배치만 읽는다** — 15 m · 깊이 2 · `mfixbatteryi5_blperairframe`.
  기체·크기·되풀이·씨앗·환경을 바꾼 샤드는 축이 다르므로 뺀다.
⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/front_window_0906.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "front_window_0906.json")
MIN_POSES = 50          # 이보다 적으면 중앙값이 안 선다
ON = 1.5                # r 이 이보다 크면 「겹쳐 적혔다」로 센다 (1 과 2 의 한가운데)

#: 표준 배치의 샤드 이름. 여기 안 맞는 것은 축이 다르므로 읽지 않는다.
CANON = re.compile(
    r"^sionna_p(?P<spp>\d+)_sw(?P<arm>R\dD\dE\dF\d)_r15_n8192_"
    r"(?:az(?P<az>[0-9.]+)_)?mfixbatteryi5_blperairframe_d2_"
    r"el(?P<el>[-+][0-9.]+)_\d+\.npz$"
)


def group_files() -> dict[tuple[str, float, float], list[str]]:
    """표준 배치 샤드를 (팔, 방위, 앙각) 으로 묶는다 — 파일을 아직 안 연다."""
    g: dict[tuple[str, float, float], list[str]] = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(SHD, "*.npz"))):
        m = CANON.match(os.path.basename(p))
        if m is None:
            continue
        g[(m["arm"], float(m["az"] or 0.0), float(m["el"]))].append(p)
    return g


def measure(paths: list[str]):
    """한 칸(팔·방위·앙각)의 자세를 전부 모아 ① 과 ② 를 낸다."""
    E, D = [], []
    for p in paths:
        try:
            z = np.load(p)
        except Exception:
            continue
        if "n_dup" not in z.files or "E_dedup" not in z.files:
            continue          # 옛 세대 샤드 — 겹침을 안 적었다
        E.append(np.abs(z["E"]))
        D.append(np.abs(z["E_dedup"]))
    if not E:
        return None
    e = np.concatenate(E)
    d = np.concatenate(D)
    ok = d > 0
    if int(ok.sum()) < MIN_POSES:
        return None
    r = e[ok] / d[ok]
    return dict(
        share_pct=round(100.0 * float((r > ON).mean()), 2),
        N=round(float(np.median(r)), 4),
        r_max=round(float(r.max()), 1),
        n_poses=int(ok.sum()),
        n_shards=len(paths),
    )


def ladder(cells, arm: str, key: str) -> dict:
    """한 팔의 사다리 — 다른 축은 0 으로 고정한다."""
    out = {}
    for (a, az, el), v in cells.items():
        if a != arm:
            continue
        other, this = (el, az) if key == "az" else (az, el)
        if abs(other) > 1e-9:
            continue
        out[f"{this:g}"] = v
    return {k: out[k] for k in sorted(out, key=lambda x: abs(float(x)))}


def edge(lad: dict) -> dict:
    """켜진 마지막 각도와 처음 꺼진 각도 — ①로 판단한다."""
    ks = sorted(lad, key=lambda x: abs(float(x)))
    last_on = first_off = None
    for k in ks:
        if abs(float(k)) < 1e-9:
            continue
        if lad[k]["share_pct"] > 50.0:
            last_on = k
        elif first_off is None:
            first_off = k
    return dict(last_on_deg=last_on, first_off_deg=first_off)


def main() -> int:
    g = group_files()
    cells = {k: v for k, v in ((k, measure(p)) for k, p in g.items()) if v}
    arms = sorted({k[0] for k in cells})

    doc = {
        "_meta": {
            "generator": "benchmark/front_window_0906.py",
            "question_ko": "같은 경로가 여러 줄로 적히는 «정면 창» 은 얼마나 좁은가",
            "share_pct_ko": "r=|E|/|E_dedup| 이 1.5 를 넘는 **자세의 비율** — 일어나나 안 일어나나",
            "N_ko": "r 의 중앙값 — 일어난다면 몇 줄로 적히나. ⚠혼합이라 오르내린다",
            "warning_ko": "⚠N 만 보면 창이 켜졌다 꺼졌다 하는 것처럼 보인다. 판단은 share_pct 로 한다",
            "scope_ko": "표준 배치만 — 15 m · 깊이 2 · mfixbatteryi5_blperairframe · 팔마다 따로",
            "on_threshold": ON,
            "min_poses": MIN_POSES,
            "n_cells": len(cells),
        },
        "by_arm": {
            arm: {
                "azimuth_ladder_at_el0": ladder(cells, arm, "az"),
                "elevation_ladder_at_az0": ladder(cells, arm, "el"),
                "edge": {
                    "azimuth": edge(ladder(cells, arm, "az")),
                    "elevation": edge(ladder(cells, arm, "el")),
                },
            }
            for arm in arms
        },
        "observations_ko": [
            "두 팔 모두 창 안에서는 **겹치는 자세가 99% 를 넘고**, 한 칸 밖에서는 **0.0%** 다.",
            "⚠중앙값 N 은 창 안에서 2.0 과 3.0 사이를 오르내린다 — 겹치는 **줄 수**가"
            " 바뀌는 것이지 창이 켜졌다 꺼졌다 하는 것이 아니다.",
            "⛔팔마다 값이 다르다 — 두 팔을 섞으면 없는 봉우리가 생긴다.",
            "⛔이 창을 «실제 비행에서 만나나» 로 옮기려면 호버링 자세 흔들림의 크기가"
            " 있어야 하는데, 이 저장소에는 그 실측이 없다.",
        ],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"칸 {len(cells)} 개 → {OUT}\n")
    for arm in arms:
        print(f"  ━━ {arm} ━━")
        for name, key in (("방위 (el 0°)", "az"), ("앙각 (az 0°)", "el")):
            lad = ladder(cells, arm, key)
            print(f"    {name}   경계 {edge(lad)}")
            for k, v in lad.items():
                if abs(float(k)) <= 6:
                    mark = "██" if v["share_pct"] > 50 else ("░ " if v["share_pct"] > 1 else "  ")
                    print(f"      {float(k):+7.3f}°  {mark} 겹치는 자세 {v['share_pct']:6.2f}%"
                          f" · N={v['N']:.3f} · 최대 {v['r_max']:.0f} · 샤드 {v['n_shards']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
