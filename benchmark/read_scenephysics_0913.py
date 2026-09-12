#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""read_scenephysics_0913.py — **장면 축 × 물리 축**을 교차시켜 읽는다. (세 갈래 중 (가))

■ 왜 만들었나
  0910 덱 9 쪽이 스스로 열어 둔 ⚠ 가 있다:
    「회절을 켠 두 팔은 다섯 칸에서 필터 뒤 값이 빈 하늘보다 **높다** — 필터가 없던
      구조를 만들었는지 **안 갈랐다**. 그 팔에는 아직 안 쓴다.」
  그 판정을 하려면 켠 팔이 **여러 장면·여러 앙각에** 서야 하는데, 2026-09-12 재고로는
  장면을 조각낸 판(지면만·건물만)에 켠 팔이 **한 칸도 없었다**. 0928 큐가 그것을 산다.
  이 판독기는 **지금 있는 칸으로 먼저 돌고**, 0928 이 들어오면 그대로 다시 돌면 된다.

■ 무엇을 재나 — 칸마다 (장면, 팔, 앙각), 빈 하늘 짝이 있을 때만
  ① 장면이 얹은 몫  lift = 레벨(장면) − 레벨(빈 하늘)
  ② 갈아낀 자세 수  덱의 잣대 그대로(hampel_mask win=51 · k=5.0) — 96·339 를 만든 그 잣대
  ③ ⭐**필터 뒤 값이 빈 하늘보다 높은가** — 덱이 열어 둔 ⚠ 그 자체
     순서는 덱과 같다(bake_outdoor.py:465): **갈아끼우고 나서** 정지 성분을 뺀다.

■ ⛔이 판독기가 답하지 않는 것
  · ⛔「어느 팔이 맞는가」를 답하지 않는다. 다섯 팔은 전부 근사이고 현실은 실기 계측이
    정한다 — **실기 계측 대조는 0 건**이다.
  · ⛔팔 사이의 **절대 레벨을 견주지 않는다**(집 규약). 견주는 것은 각 팔이 **자기 빈 하늘
    짝과** 얼마나 떨어지는가다.
  · ⛔D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·후보 탐색
    차이가 함께 들어간다. 「장면이 얹은 몫」으로만 부른다(read_canyonnull_0910 과 같은 한정).
  · ⛔지면만·건물만은 **우리 장면을 조각낸 것**이라 솔버가 주는 협곡과 같지 않다.
    드론 고도도 다르다(우리 20 m · 솔버 25 m). 장면을 가로질러 더하지 않는다.
  · ⛔갈아낀 자세 수를 «사건» 으로 부르되 그것이 무엇인지는 이 판이 말하지 않는다.

쓰는 법 (⛔CPU 전용):
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/read_scenephysics_0913.py
"""
from __future__ import annotations

import contextlib
import glob
import importlib.util
import io
import json
import os
import re
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = "/workspace/team_meeting/teammeeting_0910"
OUT = os.path.join(ROOT, "outputs/read_scenephysics_0913.json")
MD = os.path.join(ROOT, "docs/SCENEPHYSICS_0913.md")
ARMS = {"R0D0E0F1": "확산만", "R0D1E0F1": "+굴절", "R0D1E1F1": "+굴절+모서리",
        "R1D0E0F1": "+반사", "R1D1E1F1": "전부"}


def prod():
    """⛔병합을 다시 구현하지 않는다 — 생산 코드를 그대로 부른다."""
    spec = importlib.util.spec_from_file_location(
        "esm", os.path.join(ROOT, "benchmark/elevation_sweep_md.py"))
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass
    return m


def deck_filters():
    """⛔필터를 다시 구현하지 않는다 — 덱이 쓰는 그 함수를 부른다."""
    if DECK not in sys.path:
        sys.path.insert(0, DECK)
    from bake_outdoor import drop_outliers, hampel_mask       # noqa: PLC0415
    return hampel_mask, drop_outliers


def series(esm, arm, el):
    fs = sorted(glob.glob(f"{esm.SHD}/{arm}_el{el:+g}_*.npz"))
    if not fs:
        return None
    with contextlib.redirect_stdout(io.StringIO()):
        fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")
    E = seen = None
    for f in fs:
        z = np.load(f)
        ii = z["idx"].astype(int)
        if E is None:
            n0 = int(np.asarray(z["meta"], float)[3])
            E = np.zeros(n0, complex)
            seen = np.zeros(n0, bool)
        E[ii] = z["E"]
        seen[ii] = True
    return E if seen.all() else None


def db(x):
    return round(float(20 * np.log10(float(x) + 1e-300)), 2)


def main() -> int:
    esm = prod()
    hampel_mask, drop_outliers = deck_filters()
    L = json.load(open(os.path.join(ROOT, "outputs/elevation_sweep_md.json"), encoding="utf-8"))

    def sc(e):
        return ("canyon" if "envsionna-simple_street_canyon" in e else
                "gnd" if "envoutdoor01_ground" in e else
                "bldg" if "envoutdoor01_bldg" in e else
                "outdoor" if "envoutdoor01" in e else "free")

    def usable(r):
        e = r["engine"]
        return (e.startswith("sionna") and r.get("n_missing") == 0
                and r.get("n_poses") == 8192 and r.get("spp") == 4e9
                and e.endswith("_d2") and "_r15_" in e
                and not re.search(r"_(ps|fs|bs|az|rot|shell|S0|rep|div|onlyrefr|phys|alt|fc)[\d._]", e)
                and not any(d in e for d in ("mini5pro", "mavic4pro", "phantom4", "s1000plus")))

    #: 빈 하늘 짝을 (팔, 앙각) 으로 찾는다
    free = {}
    for r in L["rows"]:
        if usable(r) and sc(r["engine"]) == "free":
            a = re.search(r"_sw(R\dD\dE\dF\d)", r["engine"])
            if a:
                free[(a.group(1), r["el_deg"])] = r["engine"]

    rows = []
    for r in sorted(L["rows"], key=lambda r: (sc(r["engine"]), r["engine"], r["el_deg"])):
        if not usable(r) or sc(r["engine"]) == "free":
            continue
        a = re.search(r"_sw(R\dD\dE\dF\d)", r["engine"])
        if not a:
            continue
        arm, el = a.group(1), r["el_deg"]
        fengine = free.get((arm, el))
        if not fengine:
            continue
        Es, Ef = series(esm, r["engine"], el), series(esm, fengine, el)
        if Es is None or Ef is None:
            continue
        #: ② 덱의 잣대 그대로 — 갈아낀 자세 수
        mask = hampel_mask(np.abs(Es), 51, 5.0)
        #: ③ ⭐순서가 중요하다 — **갈아끼우고 나서** 정지 성분을 뺀다(덱 bake_outdoor.py:465)
        Er, n_rep = drop_outliers(Es, 51, 5.0)
        rows.append(dict(
            scene=sc(r["engine"]), arm=arm, arm_ko=ARMS.get(arm, arm), el_deg=el,
            engine=r["engine"], free_engine=fengine,
            level_scene_db=db(np.abs(Es).mean()), level_free_db=db(np.abs(Ef).mean()),
            lift_db=round(db(np.abs(Es).mean()) - db(np.abs(Ef).mean()), 2),
            n_replaced=int(mask.sum()), n_replaced_dropfn=int(n_rep),
            #: 정지 성분을 뺀 뒤의 변동 크기 — 이것을 빈 하늘과 견준다
            ac_after_db=db(np.std(Er - Er.mean())),
            ac_free_db=db(np.std(Ef - Ef.mean())),
            above_free_db=round(db(np.std(Er - Er.mean())) - db(np.std(Ef - Ef.mean())), 2),
        ))
        x = rows[-1]
        print(f"  {x['scene']:8s} {x['arm_ko']:10s} el{el:+4g} · 얹은 몫 {x['lift_db']:+7.2f} dB"
              f" · 갈아낀 {x['n_replaced']:4d} · 필터 뒤−빈하늘 {x['above_free_db']:+7.2f} dB"
              f" {'⛔위' if x['above_free_db'] > 0 else ''}", flush=True)

    out = dict(_meta=dict(
        generator="benchmark/read_scenephysics_0913.py",
        made_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        question_ko=("장면 축 × 물리 축 — 물리 스위치를 켜면 장면이 얹은 몫과 «필터 뒤가 "
                     "빈 하늘보다 높은가» 가 달라지나"),
        deck_open_warning_ko=("0910 덱 9 쪽: 「회절을 켠 두 팔은 다섯 칸에서 필터 뒤 값이 "
                              "빈 하늘보다 높다 — 필터가 없던 구조를 만들었는지 안 갈랐다」"),
        filter_ko="덱의 hampel_mask(win=51, k=5.0)·drop_outliers 를 그대로 부른다(재구현 없음)",
        order_ko="⭐갈아끼우고 나서 정지 성분을 뺀다 — 거꾸로 하면 4 칸 그림이 8~10 dB 달라진다",
        limits_ko=[
            "⛔「어느 팔이 맞는가」를 답하지 않는다 — 다섯 팔은 전부 근사다. 실기 계측 0 건.",
            "⛔팔 사이 절대 레벨을 견주지 않는다. 각 팔이 **자기 빈 하늘 짝과** 얼마나 떨어지는가만 본다.",
            "⛔D = 장면 − 빈 하늘 은 «환경 산란» 이 아니다 — 차폐·경로 변화·후보 탐색 차이가 함께 든다.",
            "⛔지면만·건물만은 우리 장면을 조각낸 것이라 솔버가 주는 협곡과 같지 않다(고도도 20 vs 25 m).",
            "⛔갈아낀 자세를 «사건» 으로 부르되 그것이 무엇인지는 이 판이 말하지 않는다.",
        ]), rows=rows)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    render(out)
    n_above = sum(1 for x in rows if x["above_free_db"] > 0)
    print(f"\n✅ {os.path.relpath(OUT, ROOT)} · {os.path.relpath(MD, ROOT)}  ({len(rows)} 칸)")
    print(f"   ⭐필터 뒤가 빈 하늘보다 **높은** 칸 {n_above}/{len(rows)}")
    return 0


def render(o) -> None:
    rows, m = o["rows"], o["_meta"]
    lines = ["# 장면 축 × 물리 축 — 필터 뒤가 빈 하늘보다 높은가", "",
             f"> ⛔손으로 쓰지 않는다. `{m['generator']}` 가 굽는다. `{m['made_utc']}`", "",
             "덱이 열어 둔 ⚠ — " + m["deck_open_warning_ko"], "",
             m["filter_ko"] + " · " + m["order_ko"], "",
             "| 장면 | 팔 | 앙각 | 얹은 몫 | 갈아낀 자세 | 필터 뒤 − 빈 하늘 |",
             "|---|---|---:|---:|---:|---:|"]
    for r in rows:
        flag = " ⛔" if r["above_free_db"] > 0 else ""
        lines.append(f"| {r['scene']} | {r['arm_ko']} | {r['el_deg']:+g} | "
                     f"{r['lift_db']:+.2f} dB | {r['n_replaced']} | "
                     f"{r['above_free_db']:+.2f} dB{flag} |")
    n_above = sum(1 for x in rows if x["above_free_db"] > 0)
    lines += ["", f"⛔표시는 필터 뒤가 빈 하늘보다 **높은** 칸 — {n_above}/{len(rows)}.", "",
              "## ⛔이 판독이 말하지 않는 것", ""]
    lines += [f"- {x}" for x in m["limits_ko"]]
    lines.append("")
    with open(MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
