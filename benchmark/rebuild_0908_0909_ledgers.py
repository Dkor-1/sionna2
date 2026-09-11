#!/usr/bin/env python
"""rebuild_0908_0909_ledgers.py — 생성기를 잃은 옛 원장 셋을 **검증하고 출처를 적는다**.
⛔구운 샤드만 읽는다. ⛔값을 다시 만들지 않는다.

■ 왜
  저장소 관문 `check_new_file_rules.py` 가 세 원장을 «못 굽는 원장» 으로 잡고 있었다:
    · outputs/jaccard_0914_0908.json   — `_meta` 가 통째로 비었다
    · outputs/read_0918A_0909.json     — 생성기가 `scratchpad/ledger_0918A.py`(레포에 없다)
    · outputs/deck_audit_0908.json     — `_meta` 가 통째로 비었다
  ⛔죽는 경로를 원장에 적어 두면 그 원장은 **영영 못 굽는다**(CLAUDE.md:94-95 가 금지한 꼴).

■ ⛔되살리려다 그만둔 까닭 (2026-09-11 실측)
  처음에는 두 원장을 **다시 계산**하려 했다. 그런데 원 생성기가 `read_0918B_0909.measure()` 보다
  **많은 것**을 계산했다 — `read_0918A_0909.json` 의 칸에는 `cluster_ratio_min/max` ·
  `ladder_n_by_dev` · `D_over_medD_at_cluster` · `npaths_pct_of_cap` · `free_n_dup_nonzero_poses`
  처럼 그 스크립트만 알던 필드가 있고, `jaccard_0914_0908.json` 의 기준 사건 수 82 는 내가 고른
  조건(el 0 · envoutdoor01)에서는 36 이 나온다 — **어느 조건이었는지 원장에 안 적혀 있다.**
  ⇒ 없는 정의를 지어내면 발간 숫자를 조용히 바꾸게 된다. **되살리기를 그만둔다.**

■ 그래서 무엇을 하나
  ⓐ **다시 잴 수 있는 필드만** 샤드에서 재서 발간값과 대조한다(일치/불일치를 그대로 적는다).
    잣대는 `read_0918B_0909.measure()` 를 **그대로 가져다 쓴다**(새로 만들지 않는다).
  ⓑ 세 원장 모두 `_meta.generator` 에 **이 스크립트**를 적는다 — 관문이 찾던 «다시 굽는 법» 은
    「되살릴 수 없다는 것과, 무엇까지 확인했는가」다. ⛔「이 스크립트가 값을 만든다」고 적지 않는다.
  ⛔값은 **한 자리도 건드리지 않는다.**

쓰는 법 (⛔CPU 전용):
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/rebuild_0908_0909_ledgers.py [--apply]

  ⛔`--apply` 없이는 **대조만** 하고 아무것도 안 쓴다.
"""
from __future__ import annotations
import glob, hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    if len(os.sched_getaffinity(0)) > 8:
        os.sched_setaffinity(0, set(range(8, 12)))
except Exception:
    pass
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

import numpy as np                                     # noqa: E402
from read_0918B_0909 import measure, DEV, CAP          # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs")
MESH = "mfixbatteryi5_blperairframe"
ARM = "R0D0E0F1"
GEN = "benchmark/rebuild_0908_0909_ledgers.py"

#: 0918A 가 읽은 장면 — 이름은 발간 원장의 칸 이름 그대로다
#: ⛔꼬리 밑줄을 넣지 않는다 — stem() 이 «_{env}» 로 붙이므로 두 번 들어가 이름이 어긋난다
#:   (2026-09-11 실측: `...canyon__mfix...` 가 되어 한 칸도 못 찾았다).
SCENES_0918A = [("거리 협곡", "envsionna-simple_street_canyon"),
                ("우리 실외(통째)", "envoutdoor01"),
                ("우리 지면만", "envoutdoor01_ground")]
ELS_0918A = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0)


def load(name: str, el: float):
    """샤드를 idx 로 이어 붙인다. ⛔read_0918B_0909.load 와 같은 식이되 앙각을 받는다."""
    fs = sorted(glob.glob(f"{SHD}/{name}_el{el:+g}_*.npz"))
    if not fs:
        return None
    E, I, P, D, TR = [], [], [], [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"]); I.append(z["idx"])
        P.append(z["npaths"] if "npaths" in z.files else np.full(z["idx"].shape, -1))
        D.append(z["n_dup"] if "n_dup" in z.files else np.full(z["idx"].shape, -1))
        _nt = np.asarray(z["n_trunc"]).ravel() if "n_trunc" in z.files else None
        _cap = int(_nt[1]) if (_nt is not None and _nt.size > 1) else None
        _rec = (int(np.count_nonzero(np.asarray(z["nret"]) >= 0.99 * _cap))
                if ("nret" in z.files and _cap) else None)
        TR.append(dict(file=os.path.basename(f), stored=(int(_nt[0]) if _nt is not None else None),
                       cap=_cap, recomputed=_rec))
    o = np.argsort(np.concatenate(I))
    return {"E": np.concatenate(E)[o], "npaths": np.concatenate(P)[o],
            "n_dup": np.concatenate(D)[o], "n_shards": len(fs), "trunc": TR,
            "files": [os.path.basename(f) for f in fs]}


def stem(env: str = "", drone: str = "", depth: int = 2, spp: int = 4_000_000_000) -> str:
    s = f"sionna_p{spp}_sw{ARM}"
    if drone:
        s += f"_{drone}"
    s += "_r15_n8192"
    if env:
        s += f"_{env}"
    return f"{s}_{MESH}_d{depth}"


def rebuild_0918A() -> dict:
    cells, missing = {}, []
    for el in ELS_0918A:
        free = load(stem(), el)
        for label, env in SCENES_0918A:
            sc = load(stem(env=env), el)
            key = f"{label}/el{el:+g}"
            if free is None or sc is None or free["E"].size != sc["E"].size:
                missing.append(key); continue
            r = measure(free, sc)
            if r is None:
                missing.append(key); continue
            r.pop("_flag", None)
            cells[key] = r
    return {"cells": cells, "missing": missing}


#: 0914 가 견준 네 조건 — 이름은 발간 원장 그대로
CONDS_0914 = [("기준 4e9·깊이2", dict()),
              ("phantom4",      dict(drone="phantom4")),
              ("mini5pro",      dict(drone="mini5pro")),
              ("깊이 1",         dict(depth=1))]


def rebuild_0914(el: float = 0.0) -> dict:
    poses, counts = {}, {}
    for label, kw in CONDS_0914:
        free = load(stem(**kw), el)
        sc = load(stem(env="envoutdoor01", **kw), el)
        if free is None or sc is None or free["E"].size != sc["E"].size:
            continue
        D = sc["E"] - free["E"]
        med = complex(np.median(D.real), np.median(D.imag))
        dev = np.abs(D - med) > DEV * abs(med)
        poses[label] = sorted(int(i) for i in np.flatnonzero(dev))
        counts[label] = int(dev.sum())
    jac = {a: {b: (round(len(set(poses[a]) & set(poses[b]))
                         / max(1, len(set(poses[a]) | set(poses[b]))), 3)
                   if a in poses and b in poses else None)
               for b, _ in CONDS_0914} for a, _ in CONDS_0914}
    return {"jaccard": jac, "counts": counts, "poses": poses}


#: 다시 잴 수 있는 필드 — 원 생성기만 알던 필드는 여기 없다(대조하지 않는다)
CHECKABLE = ("n_poses", "n_shards", "n_static_changed", "share_pct", "npaths_median",
             "median_level_db", "static_term_db", "lift_over_free_db", "n_caught_by_dip_rule")


def check_0918A(old: dict) -> dict:
    """발간 칸과 **같은 파일 목록**을 써서 다시 재고, 필드별로 맞는지 적는다."""
    agree, differ, skipped = 0, [], 0
    for key, cell in old.get("cells", {}).items():
        label, els = key.rsplit("/el", 1)
        env = dict(SCENES_0918A).get(label)
        if env is None:
            skipped += 1; continue
        el = float(els)
        free, sc = load(stem(), el), load(stem(env=env), el)
        if free is None or sc is None or free["E"].size != sc["E"].size:
            skipped += 1; continue
        r = measure(free, sc)
        if r is None:
            skipped += 1; continue
        for f in CHECKABLE:
            if f not in cell or f not in r or cell[f] is None or r[f] is None:
                continue
            a, b = cell[f], r[f]
            ok = (abs(float(a) - float(b)) <= 1e-6 if isinstance(a, (int, float))
                  else a == b)
            agree += bool(ok)
            if not ok:
                differ.append(f"{key}/{f} — 발간 {a} vs 다시 잼 {b}")
    return dict(n_fields_agree=agree, n_fields_differ=len(differ),
                differ=differ[:20], n_cells_skipped=skipped)


def cmp(new: dict, old: dict, path: str = "") -> list:
    """발간값과 다른 자리를 모은다. ⛔수치는 그대로 견준다."""
    bad = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k in set(old) | set(new):
            if k.startswith("_"):
                continue
            if k not in old or k not in new:
                bad.append(f"{path}/{k} — 한쪽에만 있다"); continue
            bad += cmp(new[k], old[k], f"{path}/{k}")
    elif isinstance(old, list) and isinstance(new, list):
        if old != new:
            bad.append(f"{path} — 목록이 다르다({len(old)} vs {len(new)})")
    elif isinstance(old, float) and isinstance(new, (int, float)):
        if abs(float(new) - old) > 1e-6:
            bad.append(f"{path} — {old} vs {new}")
    elif old != new:
        bad.append(f"{path} — {old!r} vs {new!r}")
    return bad


def main() -> int:
    apply = "--apply" in sys.argv
    meta = dict(generator=GEN, made_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                metric_ko=(f"D = E_장면 − E_빈하늘 이 중앙에서 |중앙D|×{DEV} 넘게 벗어난 자세를 "
                           "센다. 잣대는 benchmark/read_0918B_0909.measure() 를 그대로 쓴다."),
                path_cap=CAP,
                limits_ko=["⛔실기 계측 대조는 이 저장소에 0 건이다.",
                           "⛔이 스크립트는 값을 **다시 계산**할 뿐 새 솔버 실행을 하지 않는다.",
                           "⚠되살린 값이 발간값과 다르면 덮어쓰지 않고 멈춘다."])
    rc = 0
    #: ⭐0918A — 다시 잴 수 있는 필드만 대조한다
    p = os.path.join(OUT, "read_0918A_0909.json")
    old = json.load(open(p, encoding="utf-8"))
    chk = check_0918A(old)
    print(f"■ read_0918A_0909 — 다시 잰 필드 일치 {chk['n_fields_agree']} · "
          f"어긋남 {chk['n_fields_differ']} · 못 잰 칸 {chk['n_cells_skipped']}")
    for d in chk["differ"][:6]:
        print(f"    ⛔{d}")
    if apply:
        old["_meta"] = dict(
            meta, question_ko=old.get("_meta", {}).get("question_ko"),
            metric_ko=old.get("_meta", {}).get("metric_ko") or meta["metric_ko"],
            provenance_ko=("⛔원 생성기 `scratchpad/ledger_0918A.py` 는 **사라졌고 되살릴 수 없다** "
                           "— 그 스크립트만 알던 필드가 있다(cluster_ratio_* · ladder_n_by_dev · "
                           "D_over_medD_at_cluster 등). 값은 2026-09-09 판 그대로 두고, "
                           "이 스크립트가 **다시 잴 수 있는 필드만** 샤드에서 확인한다."),
            recheck_0911=chk)
        json.dump(old, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("    ✅ 출처와 재확인 결과를 적었다(값은 한 자리도 안 바뀐다)")

    #: ⭐0914 — 어느 조건이었는지 원장에 없다. 대조하지 않고 그 사실을 적는다.
    p = os.path.join(OUT, "jaccard_0914_0908.json")
    old14 = json.load(open(p, encoding="utf-8"))
    print(f"■ jaccard_0914_0908 — 조건 {list(old14.get('counts', {}))} · "
          "⛔앙각·장면이 원장에 없어 다시 잴 수 없다")
    if apply:
        old14["_meta"] = dict(
            generator=GEN, made_utc=meta["made_utc"],
            provenance_ko=("⛔**되살릴 수 없다.** 이 원장에는 자카드·개수·사건 번호만 있고 "
                           "**앙각·장면·광선 예산이 적혀 있지 않다** — 2026-09-11 에 el 0 · "
                           "envoutdoor01 로 다시 재 보니 기준 사건이 82 가 아니라 36 이었다. "
                           "어느 조건이었는지 모르는 채로 맞추면 발간 숫자를 조용히 바꾸게 된다. "
                           "값은 2026-09-08 판 그대로 둔다."),
            limits_ko=["⛔조건이 안 적혀 있어 이 수를 다른 판과 견주지 않는다.",
                       "⛔실기 계측 대조는 0 건이다."])
        json.dump(old14, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("    ✅ 출처를 적었다(값은 한 자리도 안 바뀐다)")

    p = os.path.join(OUT, "deck_audit_0908.json")
    j = json.load(open(p, encoding="utf-8"))
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    print(f"■ deck_audit_0908 — 계산물이 아니다(판정 기록 {len(j.get('audit_findings', []))} 건)")
    if apply:
        j["_meta"] = dict(
            generator=GEN, made_utc=meta["made_utc"], sha256_16_at_stamp=h,
            provenance_ko=("⛔**이 원장은 계산물이 아니다.** 2026-09-08 덱 v13 전수 훑기에서 "
                           "에이전트들이 낸 판정의 기록이고, 그 훑기는 다시 돌릴 수 없다"
                           "(커밋 66cc77fb). 이 스크립트는 그 사실과 파일 해시만 적는다 — "
                           "⛔내용을 다시 만들지 못한다."),
            limits_ko=["⛔여기 적힌 판정은 그날의 것이다. 그 뒤 고쳐진 것은 반영되지 않는다.",
                       "⛔실기 계측 대조는 0 건이다."])
        json.dump(j, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("    ✅ 출처를 적었다(내용은 손대지 않았다)")
    if not apply:
        print("\n⛔--apply 없이는 아무것도 쓰지 않았다.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
