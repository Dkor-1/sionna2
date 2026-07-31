# -*- coding: utf-8 -*-
"""
merge_anchor_parts.py — 기종별로 쪼개 돌린 `rcs_anchor` 조각들을 하나로 합친다
================================================================================
왜 쪼개 돌리나 (2026-07-29):
  `rcs_anchor.py` 는 전 기종을 **직렬로** 돌고 **끝에 한 번만** 저장한다. 공용 GPU 에서 이건
  치명적이었다 — 타 사용자와 경합하며 5시간 반을 계산하고도 `timeout` 에 걸려 **전손**할
  참이었다(4번째 기종에서 3시간째, 5번째는 시작도 못 함). 게다가 중간 결과가 없으니
  얼마나 남았는지도 알 수 없었다.
  → `--drones <한종>` 으로 쪼개 **카드마다 병렬**로 돌리면 (a) 한 종이 실패해도 나머지가 살고
    (b) 실시간 진행이 보이고 (c) 5시간 반이 실측 13분/종 × 병렬로 줄었다.

⚠ **병합은 반드시 재귀(deep merge)여야 한다.**
  같은 날 σ 격자 병합에서 최상위 `dict.update()` 를 써서 **5종 중 4종을 통째로 날렸다**
  (파일 0.97 MB → 0.25 MB). 기종 키가 `drones.<기종>` 안쪽에 있는데 최상위만 덮었기 때문이다.
  여기서는 그 실수를 구조적으로 막는다 — `drones` 만 합치고 나머지는 **일치 검사**를 한다.

공짜로 얻는 교차검증:
  `sphere_calibration` 은 조각마다 **독립적으로 재계산**된다(다른 GPU, 다른 프로세스).
  즉 5개 조각이 서로를 검증한다. 어긋나면 그것 자체가 발견이므로 **경고하고 산포를 기록**한다.

실행:
  ~/.venvs/py312/bin/python benchmark/merge_anchor_parts.py <조각디렉터리> [--out outputs/rcs_anchor.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)

# 조각마다 독립 재계산되는 블록 — 합치지 않고 **서로 대조**한다
CROSSCHECK = ("sphere_calibration",)
# 조각마다 같아야 하는 블록 — 어긋나면 조각들이 다른 코드/설정으로 돌았다는 뜻
IDENTICAL = ("literature",)
# 메타 중 조각마다 다른 게 정상인 키
META_PER_PART = ("generated", "gpu", "runtime_s")


def _flat(o, p=""):
    """중첩 dict 를 {경로: 값} 으로 편다 (숫자 대조용)."""
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(_flat(v, f"{p}.{k}" if p else str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(_flat(v, f"{p}[{i}]"))
    else:
        out[p] = o
    return out


def merge(part_paths, out_path, tol_db=0.05):
    parts = []
    for p in sorted(part_paths):
        with open(p, encoding="utf-8") as f:
            parts.append((os.path.basename(p), json.load(f)))
    if not parts:
        print("❌ 조각이 하나도 없다.")
        return 1

    print(f"=== 조각 {len(parts)}개 ===")
    for name, d in parts:
        dk = list(d.get("drones", {}))
        print(f"  {name:22s} 기종={dk}  gpu={d.get('meta', {}).get('gpu')}  "
              f"{d.get('meta', {}).get('runtime_s', 0):.0f}s")

    base_name, base = parts[0]
    merged = json.loads(json.dumps(base))          # 깊은 복사

    # ── 1. drones 를 합친다 (유일하게 **합치는** 블록) ────────────────────────────
    all_drones = {}
    dup = []
    for name, d in parts:
        for k, v in d.get("drones", {}).items():
            if k in all_drones:
                dup.append(k)
            all_drones[k] = v
    merged["drones"] = all_drones
    if dup:
        print(f"⚠ 중복 기종 {dup} — 나중 조각으로 덮었다.")

    # ── 2. IDENTICAL 블록은 같아야 한다 ──────────────────────────────────────────
    problems = []
    for blk in IDENTICAL:
        ref = _flat(base.get(blk, {}))
        for name, d in parts[1:]:
            cur = _flat(d.get(blk, {}))
            diff = [k for k in set(ref) | set(cur) if ref.get(k) != cur.get(k)]
            if diff:
                problems.append(f"{blk}: {name} 이 {base_name} 과 {len(diff)}곳 다르다 "
                                f"(예: {diff[:3]}) — 조각들이 다른 코드로 돌았을 수 있다")

    # ── 3. CROSSCHECK 블록은 독립 재계산 → 서로 검증 ─────────────────────────────
    spread = {}
    for blk in CROSSCHECK:
        ref = _flat(base.get(blk, {}))
        for k, v in ref.items():
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            vals = []
            for name, d in parts:
                cv = _flat(d.get(blk, {})).get(k)
                if isinstance(cv, (int, float)) and not isinstance(cv, bool):
                    vals.append(float(cv))
            if len(vals) > 1:
                rng = max(vals) - min(vals)
                spread[f"{blk}.{k}"] = dict(n=len(vals), min=min(vals), max=max(vals), range=rng)
                if abs(rng) > tol_db:
                    problems.append(f"{blk}.{k}: 조각 간 편차 {rng:.4f} > {tol_db} "
                                    f"(값 {[round(x,4) for x in vals]})")

    # ── 4. meta 정리 ────────────────────────────────────────────────────────────
    m = merged.setdefault("meta", {})
    m["n_drones"] = len(all_drones)
    m["merged_from"] = [n for n, _ in parts]
    m["runtime_s_per_part"] = {n: round(d.get("meta", {}).get("runtime_s", 0.0), 1)
                               for n, d in parts}
    m["runtime_s"] = round(sum(m["runtime_s_per_part"].values()), 1)
    m["gpus_used"] = sorted({str(d.get("meta", {}).get("gpu")) for _, d in parts})
    m["merge_note"] = (
        "기종별로 병렬 실행한 조각을 재귀 병합했다. `drones` 만 합치고 `literature` 는 일치를, "
        "`sphere_calibration` 은 조각 간 산포를 검사했다 — 후자는 조각마다 독립 재계산되므로 "
        "서로에 대한 교차검증이 된다. ⚠ 최상위 dict.update() 로 합치면 기종이 유실된다"
        "(2026-07-29 σ 격자에서 실제로 4종을 날린 적 있다).")
    m["crosscheck_spread"] = spread

    # ── 5. 판정 ────────────────────────────────────────────────────────────────
    print(f"\n=== 교차검증 (조각마다 독립 재계산되는 값) ===")
    worst = sorted(spread.items(), key=lambda kv: -abs(kv[1]["range"]))[:5]
    for k, v in worst:
        print(f"  {k:52s} 편차 {v['range']:+.5f}  (n={v['n']})")
    if problems:
        print(f"\n❌ 문제 {len(problems)}건")
        for p in problems:
            print(f"  · {p}")
    else:
        print(f"\n✅ 조각 간 불일치 없음 (허용 {tol_db})")

    print(f"\n=== 병합 결과 ===")
    print(f"  기종 {len(all_drones)}종: {sorted(all_drones)}")
    for dk, dv in sorted(all_drones.items()):
        nb = len(dv.get("bands", {}))
        print(f"    {dk:12s} 밴드 {nb}개, 키 {list(dv)}")

    if len(all_drones) < 2:
        print("⚠ 기종이 2종 미만이다 — 병합할 게 없다. 저장하지 않는다.")
        return 1

    # 덮어쓰기 전에 원본을 백업한다 (오늘 정본을 날릴 뻔한 적이 있다)
    if os.path.exists(out_path):
        bak = out_path + ".pre_merge.bak"
        if not os.path.exists(bak):
            with open(out_path, encoding="utf-8") as f, open(bak, "w", encoding="utf-8") as g:
                g.write(f.read())
            print(f"  기존 파일 백업 → {os.path.basename(bak)}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"✅ 저장: {out_path}  ({os.path.getsize(out_path)/1024:.0f} KB)")
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts_dir", help="기종별 조각 json 이 있는 디렉터리")
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "rcs_anchor.json"))
    ap.add_argument("--tol-db", type=float, default=0.05, help="조각 간 허용 편차")
    a = ap.parse_args()
    paths = glob.glob(os.path.join(a.parts_dir, "*.json"))
    return merge(paths, a.out, a.tol_db)


if __name__ == "__main__":
    sys.exit(main())
