#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""freeze_0912.py — 2026-09-12 의 **기준선**을 뜬다. 나중에 흔들렸는지 이것으로 안다.

■ 왜 만들었나
  사용자 지시(2026-09-12): 「가·나·다 모두 시행해 볼 수 없을까? **현재까지의 결과들도 잘 보존하고**」
  세 갈래(물리 경로 · 파형 생존 · 대역폭)는 전부 원장·샤드·보고서를 흔든다. 흔들고 나서
  「무엇이 달라졌나」를 말하려면 **흔들기 전의 수**가 한자리에 있어야 한다.

  ⛔태그만으로는 약하다. 태그는 파일을 되돌릴 뿐, **수가 움직였다는 것을 알려 주지 않는다.**
    이 빌더는 수를 다시 계산해 기준선과 대조하고, 어긋나면 그 자리를 짚어 준다.

■ 무엇을 뜨나 — 발간·인용되는 수만
  · 원장·아틀라스의 규모와 자격(완결 칸·미완·영 전계·잘림·세대 선택)
  · 실외 사건 수(협곡 갈아낀 자세) · 낙차 사다리
  · 지면이 있을 때 기체 사이 레벨이 모이는 정도
  · 각주 포인터 검사 · 철회 검사의 통과 여부
  ⛔값을 하드코딩하지 않는다 — 매번 상류에서 다시 계산한다. 기준선은 JSON 에만 있다.

■ 쓰는 법
    PYTHONPATH=src:benchmark $PY benchmark/freeze_0912.py            # 기준선을 뜬다(없을 때만)
    PYTHONPATH=src:benchmark $PY benchmark/freeze_0912.py --check    # 지금과 기준선을 대조
    PYTHONPATH=src:benchmark $PY benchmark/freeze_0912.py --update   # 기준선을 지금으로 갱신
  ⛔--update 는 «움직인 것을 확인하고 받아들일 때» 만 쓴다. 그때 왜 움직였는지 커밋에 적는다.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs/freeze_0912.json")
MD = os.path.join(ROOT, "docs/FREEZE_0912.md")


def js(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def measure() -> dict:
    """지금의 수를 **상류에서 다시 계산**한다."""
    m: dict = {}
    L = js("outputs/elevation_sweep_md.json")
    R = L["rows"]
    m["ledger"] = dict(
        n_rows=len(R),
        n_complete=sum(1 for r in R if r.get("n_missing") == 0 and r.get("n_poses") == 8192),
        n_incomplete=sum(1 for r in R if r.get("n_missing", 0) > 0),
        n_zero_field=sum(1 for r in R if r.get("n_zero_field", 0) > 0),
        n_truncated=sum(1 for r in R if r.get("truncated")),
        n_mixed_generations=sum(1 for r in R if r.get("mixed_generations")),
        engines=len({r["engine"] for r in R}),
        elevations=len({r["el_deg"] for r in R}),
    )
    #: 세대를 고른 칸이 무엇으로 갈렸는지 — 흔들리면 안 되는 자리다
    _mg = [dict(engine=r["engine"], el_deg=r["el_deg"],
                selected_by=r["mixed_generations"]["selected_by"],
                tie_unresolved=r["mixed_generations"]["tie_unresolved"],
                kept_duplicate_poses=r["mixed_generations"]["kept_duplicate_poses"],
                kept_conflicting_poses=r["mixed_generations"]["kept_conflicting_poses"])
           for r in R if r.get("mixed_generations")]
    m["mixed_generations"] = sorted(_mg, key=lambda d: (d["engine"], d["el_deg"]))

    try:
        A = js("outputs/md_atlas_index.json")
        cells = sum(len(i["cells"]) for t in A["topics"].values() for i in t["arms"].values())
        m["atlas"] = dict(topics=len(A["topics"]), cells=cells,
                          arms=sum(len(t["arms"]) for t in A["topics"].values()))
    except Exception as e:                                          # noqa: BLE001
        m["atlas"] = dict(error=f"{type(e).__name__}")

    #: 실외 사건 수 — 덱 9 쪽이 인용하는 수
    try:
        C = js("outputs/read_canyonnull_0910.json")
        m["canyon_events"] = {k: v for k, v in C.items() if isinstance(v, (int, float))} \
            or dict(note="스칼라 없음")
        txt = json.dumps(C, ensure_ascii=False)
        m["canyon_events"]["has_96"] = ": 96" in txt or " 96," in txt or "96]" in txt
        m["canyon_events"]["has_339"] = "339" in txt
    except Exception as e:                                          # noqa: BLE001
        m["canyon_events"] = dict(error=f"{type(e).__name__}")

    #: ⭐지면이 있으면 기체 사이 레벨이 모인다 — 2026-09-12 에 확인한 가장 센 대조
    m["ground_collapse"] = ground_collapse(R)

    #: 검사기들
    m["checks"] = {}
    for name, cmd in (("row_pointers", ["benchmark/check_row_pointers.py", "--quiet"]),
                      ("retracted", ["benchmark/check_retracted.py"]),
                      ("report_links", ["benchmark/check_report_links.py"])):
        env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONPATH="src:benchmark")
        try:
            p = subprocess.run([sys.executable] + cmd, cwd=ROOT, env=env,
                               capture_output=True, text=True, timeout=900)
            m["checks"][name] = dict(exit=p.returncode,
                                     head=(p.stdout or p.stderr).strip().splitlines()[:1])
        except Exception as e:                                      # noqa: BLE001
            m["checks"][name] = dict(error=f"{type(e).__name__}")

    m["warehouse"] = dict(
        shards=len([x for x in os.listdir(os.path.join(ROOT, "outputs/elev_sweep_shards"))
                    if x.endswith(".npz")]))
    return m


def ground_collapse(R) -> dict:
    """지면이 있을 때 기체 사이 레벨 퍼짐이 줄어드는가 — 같은 팔·거리·예산·앙각에서만."""
    DR = ("phantom4", "mavic4pro", "mini5pro", "s1000plus")

    def drone(e):
        return next((d for d in DR if d in e), "matrice4e")

    def ok(r):
        return (r.get("n_missing") == 0 and r.get("n_zero_field", 0) == 0
                and not r.get("truncated") and r.get("n_poses") == 8192)

    def plain(e):
        return not re.search(r"_(ps|fs|bs|az|rot|shell|S0|rep|div|onlyrefr|phys|alt)[\d._]", e)

    out = {}
    for el in (-30.0, -60.0):
        F, G = {}, {}
        for r in R:
            e = r["engine"]
            if not (e.startswith("sionna") and "_swR0D0E0F1_" in e and e.endswith("_d2")
                    and "_r15_" in e and r["el_deg"] == el and r.get("spp") == 4e9
                    and ok(r) and plain(e)):
                continue
            d = drone(e)
            if "envoutdoor01_ground" in e:
                G[d] = r["level_db"]
            elif "env" not in e:
                F[d] = r["level_db"]
        both = sorted(set(F) & set(G))
        if len(both) < 2:
            out[f"el{el:+g}"] = dict(n_airframes=len(both), note="기체가 둘 미만 — 못 잰다")
            continue
        fv = [F[d] for d in both]
        gv = [G[d] for d in both]
        out[f"el{el:+g}"] = dict(
            n_airframes=len(both), airframes=both,
            free_spread_db=round(max(fv) - min(fv), 2),
            ground_spread_db=round(max(gv) - min(gv), 2),
            free_levels={d: F[d] for d in both}, ground_levels={d: G[d] for d in both})
    return out


def flatten(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flatten(v, f"{p}.{k}" if p else str(k))
    elif isinstance(o, list):
        yield p, json.dumps(o, ensure_ascii=False, sort_keys=True)
    else:
        yield p, o


def render(base: dict) -> None:
    m = base["baseline"]
    L, A = m["ledger"], m.get("atlas", {})
    lines = [
        "# 2026-09-12 기준선 — 세 갈래를 시작하기 전의 수",
        "",
        f"> ⛔이 문서는 손으로 쓰지 않는다. `benchmark/freeze_0912.py` 가 굽는다.",
        f"> 지금과 대조하려면 `--check`. 받아들이려면 `--update`(왜 움직였는지 커밋에 적는다).",
        "",
        f"- 뜬 때 `{base['frozen_utc']}` · 커밋 `{base['head']}`",
        f"- 사용자 지시: 「가·나·다 모두 시행해 볼 수 없을까? 현재까지의 결과들도 잘 보존하고」",
        "",
        "## 원장",
        "",
        "| | |", "|---|---:|",
        f"| 칸 | {L['n_rows']} |",
        f"| 그중 완결(자세 8,192 · 결측 0) | {L['n_complete']} |",
        f"| 미완 | {L['n_incomplete']} |",
        f"| 영 전계가 있는 칸 | {L['n_zero_field']} |",
        f"| 잘린 칸 | {L['n_truncated']} |",
        f"| 세대를 고른 칸 | {L['n_mixed_generations']} |",
        f"| 팔 | {L['engines']} |",
        f"| 앙각 | {L['elevations']} |",
        f"| 창고 샤드 | {m['warehouse']['shards']} |",
        "",
    ]
    if "cells" in A:
        lines += [f"아틀라스 — 주제 {A['topics']} · 팔 {A['arms']} · 칸 {A['cells']}", ""]
    lines += ["## 지면이 있으면 기체 사이 레벨이 모인다", "",
              "⛔같은 팔·거리·예산·앙각에서만 견준다. 기체가 둘 미만이면 안 잰다.", "",
              "| 앙각 | 기체 | 빈 하늘 퍼짐 | 지면 있음 퍼짐 |", "|---|---:|---:|---:|"]
    for k, v in m["ground_collapse"].items():
        if "free_spread_db" not in v:
            lines.append(f"| {k} | {v['n_airframes']} | — | {v.get('note','')} |")
            continue
        lines.append(f"| {k} | {v['n_airframes']} | {v['free_spread_db']} dB | "
                     f"{v['ground_spread_db']} dB |")
    lines += ["", "## 검사기", "", "| 검사 | 종료코드 |", "|---|---:|"]
    for k, v in m["checks"].items():
        lines.append(f"| {k} | {v.get('exit', v.get('error'))} |")
    lines += ["", "## 세대를 고른 칸", "",
              "| 팔 | 앙각 | 무엇으로 갈랐나 | 동점 미해결 | 중복 | 갈린 자세 |",
              "|---|---:|---|---|---:|---:|"]
    for d in m["mixed_generations"]:
        lines.append(f"| `{d['engine'][-40:]}` | {d['el_deg']:+g} | {d['selected_by']} | "
                     f"{d['tie_unresolved']} | {d['kept_duplicate_poses']} | "
                     f"{d['kept_conflicting_poses']} |")
    lines.append("")
    with open(MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    now = measure()
    if "--check" in sys.argv:
        if not os.path.exists(OUT):
            print("⛔기준선이 없다 — 먼저 인자 없이 한 번 돌린다"); return 2
        base = js("outputs/freeze_0912.json")["baseline"]
        a, b = dict(flatten(base)), dict(flatten(now))
        moved = [(k, a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
        #: 검사기 출력 첫 줄은 수가 들어 있어 흔들린다 — 종료코드만 본다
        moved = [x for x in moved if not x[0].endswith(".head")]
        print(f"═══ 기준선 대조 — 움직인 자리 {len(moved)} ═══")
        for k, x, y in moved[:40]:
            print(f"  {k}\n     기준 {x}\n     지금 {y}")
        if len(moved) > 40:
            print(f"  … 외 {len(moved)-40}")
        if moved:
            print("\n  ⭐움직인 것이 **받아들일 변화**라면 --update 로 갱신하고 커밋에 왜인지 적는다.")
        return 1 if moved else 0
    if os.path.exists(OUT) and "--update" not in sys.argv:
        print("⛔기준선이 이미 있다 — 대조는 --check, 갱신은 --update"); return 2
    base = dict(frozen_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                head=head, generator="benchmark/freeze_0912.py",
                why_ko=("2026-09-12 세 갈래(물리 경로·파형 생존·대역폭)를 시작하기 전의 수. "
                        "흔들고 나서 무엇이 달라졌는지 말하려면 흔들기 전의 수가 있어야 한다."),
                baseline=now)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=1)
    render(base)
    print(f"✅ {os.path.relpath(OUT, ROOT)} · {os.path.relpath(MD, ROOT)}")
    print(f"   원장 {now['ledger']['n_rows']} 칸 · 완결 {now['ledger']['n_complete']} · "
          f"창고 {now['warehouse']['shards']} 장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
