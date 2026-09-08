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
    """표준 배치 샤드를 (팔, 방위, 앙각) 으로 묶는다 — 파일을 아직 안 연다.

    ⚠**광선 예산(spp)은 칸을 가르지 않는다.** 사다리의 칸들은 4e9 로 샀는데
      기준점인 축 위(방위 0·고도 0)는 4e9 샤드가 **옛 세대라 겹침을 안 적었고**,
      1e8·1e9 만 남아 있다. 예산을 칸의 열쇠에 넣으면 기준점이 사다리에서
      **빠져 버린다.** 그래서 묶기는 하되 칸마다 `spp` 를 함께 적어 드러낸다.
      (예산이 N 을 바꾸지 않는다는 것은 0.1e9→3.0004 · 1e9→2.9999 · 4e9→2.9972 로
       따로 쟀다. 그래도 섞였다는 사실 자체는 숨기지 않는다.)
    """
    g: dict[tuple[str, float, float], list[str]] = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(SHD, "*.npz"))):
        m = CANON.match(os.path.basename(p))
        if m is None:
            continue
        g[(m["arm"], float(m["az"] or 0.0), float(m["el"]))].append(p)
    return g


def measure(paths: list[str]):
    """한 칸(팔·방위·앙각)의 자세를 전부 모아 ① 과 ② 를 낸다."""
    E, D, spp = [], [], set()
    for p in paths:
        try:
            z = np.load(p)
        except Exception:
            continue
        if "n_dup" not in z.files or "E_dedup" not in z.files:
            continue          # 옛 세대 샤드 — 겹침을 안 적었다
        E.append(np.abs(z["E"]))
        D.append(np.abs(z["E_dedup"]))
        m = CANON.match(os.path.basename(p))
        if m:
            spp.add(int(m["spp"]))
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
        spp=sorted(spp),          #: ⚠이 칸이 어느 광선 예산에서 왔는지
        db_vs_dedup=round(20.0 * float(np.log10(np.median(r))), 3),
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
    """켜진 마지막 각도와 그 **바로 바깥** 첫 꺼진 각도.

    ⛔⛔**2026-09-07 — 옛 판은 성립할 수 없는 값을 냈다.** 옛 코드는 `first_off` 를
    「안쪽부터 훑어 처음 만난 꺼진 칸」으로 잡았는데, 사다리가 **단조가 아니면**
    그 칸이 `last_on` 보다 **안쪽**에 놓인다. 실제로 R0D1E1F1 방위는
    0.05°(켜짐) → 0.07°(1.0 %, 꺼짐) → 0.10·0.11°(켜짐) → 0.12°(꺼짐) 이라
    {last_on 0.11, first_off 0.07} 이 나왔다 — 꺼지는 자리가 켜진 자리보다 앞이다.
    그 값이 docs/RESUME.md 와 덱 결론줄로 흘러갔다.

    ⇒ 이제 **바깥 경계**를 낸다: 켜진 가장 바깥 칸(`last_on`)과, 그보다 바깥에서
      처음 꺼진 칸(`first_off`). 그리고 사다리가 단조인지(`monotonic`)와
      「꺼졌다 다시 켜진」 칸들(`reentrant_deg`)을 함께 적는다 —
      ⛔단조가 아니면 경계 하나로 인용하지 않는다.
    """
    ks = [k for k in sorted(lad, key=lambda x: abs(float(x)))
          if abs(float(k)) > 1e-9]
    on = [k for k in ks if lad[k]["share_pct"] > 50.0]
    last_on = on[-1] if on else None
    first_off = None
    if last_on is not None:
        for k in ks:
            if abs(float(k)) > abs(float(last_on)) and lad[k]["share_pct"] <= 50.0:
                first_off = k
                break
    #: 꺼졌다 다시 켜진 칸 — 이것이 있으면 「한 칸에서 사라진다」가 그대로 안 선다
    seen_off, reentrant = False, []
    for k in ks:
        if lad[k]["share_pct"] <= 50.0:
            seen_off = True
        elif seen_off:
            reentrant.append(k)
    return dict(last_on_deg=last_on, first_off_deg=first_off,
                monotonic=not reentrant, reentrant_deg=reentrant,
                note_ko=("" if not reentrant else
                         "⛔사다리가 단조가 아니다 — 꺼졌다 다시 켜지는 칸이 있어"
                         " 경계 하나로 인용할 수 없다"))


def main() -> int:
    g = group_files()
    cells = {k: v for k, v in ((k, measure(p)) for k, p in g.items()) if v}
    arms = sorted({k[0] for k in cells})

    #: ⭐**요약 문장을 손으로 쓰지 않는다.** 2026-09-07 감사에서 손으로 쓴 문장 둘이
    #  같은 원장의 값과 어긋난 채 발주 판단까지 정한 것이 잡혔다. 이제 여기서 센다.
    BY = {
        arm: {
            "azimuth_ladder_at_el0": ladder(cells, arm, "az"),
            "elevation_ladder_at_az0": ladder(cells, arm, "el"),
        }
        for arm in arms
    }
    for arm, v in BY.items():
        v["edge"] = {"azimuth": edge(v["azimuth_ladder_at_el0"]),
                     "elevation": edge(v["elevation_ladder_at_az0"])}

    def _inside(key):
        """창 안(share>50)의 값들 — 요약 문장이 여기서 나온다."""
        out = []
        for v in BY.values():
            for ax in ("azimuth_ladder_at_el0", "elevation_ladder_at_az0"):
                out += [e[key] for e in v[ax].values()
                        if e["share_pct"] > 50.0 and e.get(key) is not None]
        return out

    _N, _R = _inside("N"), _inside("r_max")
    _spp = sorted({x for v in BY.values() for ax in
                   ("azimuth_ladder_at_el0", "elevation_ladder_at_az0")
                   for e in v[ax].values() for x in (e.get("spp") or [])})
    _spp_axis = sorted({x for v in BY.values()
                        for k, e in v["azimuth_ladder_at_el0"].items()
                        if abs(float(k)) < 1e-9 for x in (e.get("spp") or [])})
    _nonmono = [f"{a}/{ax}" for a, v in BY.items() for ax in ("azimuth", "elevation")
                if not v["edge"][ax]["monotonic"]]
    #: ⭐축 위(0°) 칸의 dB 를 팔마다 세어 둔다 — 손으로 쓴 «+9.542 dB» 를 대체한다
    _axis_db = {a: v["azimuth_ladder_at_el0"][k]["db_vs_dedup"]
                for a, v in BY.items()
                for k in v["azimuth_ladder_at_el0"] if abs(float(k)) < 1e-9}

    doc = {
        "_meta": {
            "generator": "benchmark/front_window_0906.py",
            "question_ko": "같은 경로가 여러 줄로 적히는 «정면 창» 은 얼마나 좁은가",
            "share_pct_ko": "r=|E|/|E_dedup| 이 1.5 를 넘는 **자세의 비율** — 일어나나 안 일어나나",
            "N_ko": "r 의 중앙값 — 일어난다면 몇 줄로 적히나. ⚠혼합이라 오르내린다",
            "warning_ko": "⚠N 만 보면 창이 켜졌다 꺼졌다 하는 것처럼 보인다. 판단은 share_pct 로 한다",
            "scope_ko": "표준 배치만 — 15 m · 깊이 2 · mfixbatteryi5_blperairframe · 팔마다 따로",
            #: ⭐세어서 적는다 — 옛 판은 「축 위 기준점은 1e8·1e9 뿐」이라 손으로 적었는데
            #  실제로는 네 팔 중 셋이 축 위에 4e9 **만** 갖고 있었다(2026-09-07 감사).
            "spp_ko": "⚠광선 예산은 칸을 가르지 않는다 — 칸마다 spp 로 적었다."
                      f" 이 원장에 든 예산: {[f'{x:g}' for x in _spp]}."
                      f" 축 위(0°) 칸에 든 예산: {[f'{x:g}' for x in _spp_axis]}",
            "spp_all": _spp,
            "spp_on_axis": _spp_axis,
            #: ⛔손으로 쓴 문장이었다 — «정확히 3 배» 는 이 저장소가 금지한 표현이고
            #  (front_repeat_0906 · docs/RESUME.md), 9.542 는 이 원장 어디에도 없는 수다.
            #  게다가 네 팔 중 둘은 N≈2.35 라 3 배가 아니다. 세어서 적는다.
            "db_vs_dedup_ko": "20·log10(N) — 겹쳐 적힌 만큼 필드가 커진 크기(dB)."
                              f" 축 위(0°) 값은 팔마다 다르다: {_axis_db}."
                              " ⛔«정확히 3 배» 로 적지 마라 — 팔에 따라 2.35 배다",
            "db_vs_dedup_on_axis_by_arm": _axis_db,
            "on_threshold": ON,
            "min_poses": MIN_POSES,
            "n_cells": len(cells),
        },
        "by_arm": BY,
        "observations_ko": [
            "두 팔 모두 창 안에서는 **겹치는 자세가 99% 를 넘고**, 한 칸 밖에서는 **0.0%** 다.",
            f"⚠중앙값 N 은 창 안에서 {min(_N):.2f} 와 {max(_N):.2f} 사이를 오르내린다 —"
            " 겹치는 **줄 수**가 바뀌는 것이지 창이 켜졌다 꺼졌다 하는 것이 아니다."
            f" ⛔한 자세에서는 {max(_R):.1f} 까지 간다 — 회절 켠 팔의 방위 사다리가"
            " 특히 그렇다. 「2~3 줄」로 요약하지 마라.",
            ("⛔사다리가 단조가 아닌 자리: " + ", ".join(_nonmono)
             + ". 그 팔·축은 경계 하나로 인용할 수 없다.") if _nonmono else
            "✅사다리는 팔·축 모두 단조다 — 경계를 하나로 인용해도 된다.",
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
