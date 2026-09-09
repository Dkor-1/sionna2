#!/usr/bin/env python
"""jobs_0918 **B 묶음** 을 읽는다 — 걸리는 자세를 정하는 것이 프롭인가 프레임인가.

⭐잣대는 benchmark/read_0914_0908.py 의 measure() 와 ⑬ 견주기를 **그대로** 쓴다.
  (문턱 없는 셈: D = E_실외 − E_빈하늘 이 중앙에서 |중앙D|×0.5 넘게 벗어난 자세)
⭐0919 의 «널»(광선 재표본 3.8e9·4.2e9 · 되풀이 rep1·rep2)도 같은 잣대로 함께 읽는다.
"""
from __future__ import annotations
import glob, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "read_0918B_0909.json")
MESH = "mfixbatteryi5_blperairframe"
ARM, EL, CAP, DEV = "R0D0E0F1", -60.0, 2_000_000, 0.5


def load(name):
    fs = sorted(glob.glob(f"{SHD}/{name}_el{EL:+g}_*.npz"))
    if not fs:
        return None
    E, I, P, DUP, TR = [], [], [], [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"]); I.append(z["idx"])
        P.append(z["npaths"] if "npaths" in z.files else np.full(z["idx"].shape, -1))
        DUP.append(z["n_dup"] if "n_dup" in z.files else np.full(z["idx"].shape, -1))
        if "n_trunc" in z.files:
            TR.append(np.asarray(z["n_trunc"]).ravel())
    o = np.argsort(np.concatenate(I))
    return {"E": np.concatenate(E)[o], "npaths": np.concatenate(P)[o],
            "n_dup": np.concatenate(DUP)[o], "n_shards": len(fs),
            "trunc": [t.tolist() for t in TR], "files": [os.path.basename(f) for f in fs]}


def stem(spp=4_000_000_000, env="", rep=0, tail=""):
    """elevation_sweep_md 의 이름 규칙 그대로 — 순서가 중요하다(:449-471)."""
    s = f"sionna_p{spp}_sw{ARM}_r15_n8192"
    if rep:
        s += f"_rep{rep}"
    if env:
        s += f"_env{env}"
    return s + (tail or "") + f"_{MESH}_d2"


def db(x):
    return float(20.0 * np.log10(max(float(x), 1e-300)))


def measure(free, out):                       # ⭐read_0914_0908.py:96-125 와 같은 코드
    F, O = free["E"], out["E"]
    if F.size != O.size:
        return None
    D = O - F
    med = complex(np.median(D.real), np.median(D.imag))
    dev = np.abs(D - med) > DEV * abs(med)
    amp = np.abs(O)
    m = float(np.median(amp))
    r = {"n_poses": int(O.size), "n_shards": out["n_shards"],
         "n_static_changed": int(dev.sum()),
         "share_pct": round(100.0 * float(dev.mean()), 2),
         "level_at_events_db": (None if not dev.any()
                                else round(db(np.median(amp[dev])) - db(m), 2)),
         "median_level_db": round(db(m), 2),
         "static_term_db": round(db(abs(med)), 2),
         "lift_over_free_db": round(db(m) - db(np.median(np.abs(F))), 2),
         "n_caught_by_dip_rule": int((amp / m < 0.1).sum()),
         "_flag": dev}
    npa = out["npaths"]
    if (npa >= 0).any():
        r["npaths_median"] = int(np.median(npa[npa >= 0]))
        r["at_path_cap"] = bool(np.median(npa[npa >= 0]) >= 0.99 * CAP)
    dup = out["n_dup"]
    if (dup >= 0).any():
        r["n_poses_with_dup"] = int((dup > 0).sum())
    r["trunc_outdoor"] = out["trunc"]
    return r


CELLS = [
    ("기준선", "배율 없음 (matrice4e · el −60)", stem(env="outdoor01_ground"), stem()),
    ("B 프롭", "프롭 ×0.6 (프레임 고정)",
     stem(env="outdoor01_ground", tail="_ps0.6"), stem(tail="_ps0.6")),
    ("B 프레임", "프레임 ×1.5 (프롭 고정)",
     stem(env="outdoor01_ground", tail="_fs1.5"), stem(tail="_fs1.5")),
    ("B 통째", "기체 통째 ×1.5 (프롭+프레임)",
     stem(env="outdoor01_ground", tail="_ps1.5_fs1.5"), stem(tail="_ps1.5_fs1.5")),
    ("널 광선", "광선 3.8e9 (표본 통째 재추출)",
     stem(spp=3_800_000_000, env="outdoor01_ground"), stem(spp=3_800_000_000)),
    ("널 광선", "광선 4.2e9 (표본 통째 재추출)",
     stem(spp=4_200_000_000, env="outdoor01_ground"), stem(spp=4_200_000_000)),
    ("널 되풀이", "되풀이 1 (같은 설정 재실행)",
     stem(env="outdoor01_ground", rep=1), stem(rep=1)),
    ("널 되풀이", "되풀이 2 (같은 설정 재실행)",
     stem(env="outdoor01_ground", rep=2), stem(rep=2)),
]


def main() -> int:
    t0 = time.time()
    cells, flags, missing = {}, {}, []
    for grp, lbl, so, sf in CELLS:
        O, F = load(so), load(sf)
        if O is None or F is None:
            missing.append({"group": grp, "cell": lbl, "stem_outdoor": so,
                            "stem_free": sf, "have_outdoor": O is not None,
                            "have_free": F is not None})
            print(f"  ⏳{grp:<8}{lbl:<30} 아직 없다 "
                  f"(실외 {O is not None} · 빈 하늘 {F is not None})", flush=True)
            continue
        r = measure(F, O)
        if r is None:
            missing.append({"group": grp, "cell": lbl, "why": "자세 수가 안 맞는다"})
            continue
        flags[lbl] = r.pop("_flag")
        r.update(group=grp, cell=lbl, stem_outdoor=so, stem_free=sf,
                 files_outdoor=O["files"], files_free=F["files"])
        cells[lbl] = r
        print(f"  {grp:<8}{lbl:<30} 사건 {r['n_static_changed']:>4}"
              f" ({r['share_pct']:>5.2f} %) · 그때 {str(r['level_at_events_db']):>7} dB"
              f" · 지면이 올린 몫 {r['lift_over_free_db']:>6.1f} dB"
              f" · 옛 규칙 {r['n_caught_by_dip_rule']:>4}"
              f" · 경로중앙 {r.get('npaths_median')}"
              f"{'  ⛔상한' if r.get('at_path_cap') else ''}", flush=True)

    base = "배율 없음 (matrice4e · el −60)"
    pairs = {}
    ks = list(cells)
    for i, ka in enumerate(ks):
        for kb in ks[i + 1:]:
            fa, fb = flags[ka], flags[kb]
            if fa.size != fb.size:
                continue
            na, nb, N = int(fa.sum()), int(fb.sum()), int(fa.size)
            inter, uni = int((fa & fb).sum()), int((fa | fb).sum())
            pairs[f"{ka} ∩ {kb}"] = {
                "n_a": na, "n_b": nb, "n_intersect": inter,
                "jaccard": round(inter / max(uni, 1), 4),
                "expected_if_unrelated": round(na * nb / N, 2),
                "share_of_smaller": round(inter / max(min(na, nb), 1), 4),
                "vs_baseline": (ka == base or kb == base),
                #: ⭐기준선과의 비대칭 — 「몇 개가 살아남고 몇 개가 새로 생겼나」
                **({"baseline_kept": int((fa & fb).sum()),
                    "baseline_lost": int((flags[base] & ~(fb if ka == base else fa)).sum()),
                    "brand_new": int(((~flags[base]) & (fb if ka == base else fa)).sum())}
                   if (ka == base or kb == base) else {}),
                #: ⭐호버 회전수는 모두 matrice4e 3800 rpm — 배율은 rpm 을 안 건드린다
                #:   (elevation_sweep_md.py:359 FastPoser 는 크기만 받고 rpm 은 :372 원장값).
                "comparable": True}
    print("\n  ⑬ 기준선과 견준다 (우연 기댓값 · 자카드)")
    for k, v in pairs.items():
        if not v["vs_baseline"]:
            continue
        print(f"    ⭐{k:<70} 교집합 {v['n_intersect']:>3} / 작은쪽 "
              f"{min(v['n_a'], v['n_b']):>3} · 우연이면 "
              f"{v['expected_if_unrelated']:>6.2f} · 자카드 {v['jaccard']:.3f}", flush=True)
    print("\n  나머지 짝")
    for k, v in pairs.items():
        if v["vs_baseline"]:
            continue
        print(f"      {k:<70} 교집합 {v['n_intersect']:>3} · 자카드 {v['jaccard']:.3f}",
              flush=True)

    #: ④ comb_snr 의 대역이 _ps 를 따라가나 — 실측한다
    band = {}
    try:
        import comb_snr as CS
        import importlib
        ESM = importlib.import_module("elevation_sweep_md")
        for tag in ("", "_ps0.6", "_ps1.5_fs1.5", "_fs1.5"):
            arm = stem(env="outdoor01_ground", tail=tag)
            band[tag or "(배율 없음)"] = {
                "comb_snr.f_tip_hz": round(float(CS.f_tip(EL, arm)), 3),
                "elevation_sweep_md.f_tip_at_hz": round(float(ESM.f_tip_at(EL, arm)), 3)}
    except Exception as e:                                            # noqa: BLE001
        band["_error"] = repr(e)

    doc = {"_meta": {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "generator": "benchmark/read_0918B_0909.py",
                     "question_ko": "0918 B — 걸리는 자세를 정하는 것이 프롭인가 프레임인가",
                     "metric_ko": f"read_0914_0908.py 와 같은 잣대 — D = E_실외 − E_빈하늘 이 "
                                  f"중앙에서 |중앙D|×{DEV} 넘게 벗어난 자세를 센다(문턱 없음)",
                     "el_deg": EL, "arm": ARM, "path_cap": CAP,
                     "elapsed_s": round(time.time() - t0, 1),
                     "null_caveat_ko": "⚠«되풀이»(--rep) 널은 표본을 다시 뽑지 않는다 — "
                                       "rep1·rep2 의 E 가 기준선과 |Δ|max 8.4e-10 (중앙 |E| "
                                       "1.9e-4 의 4e-6 배) 로 사실상 같다. 되풀이 자카드 1.000 은 "
                                       "«수치 재현성» 이지 «표본 흔들기» 가 아니다. "
                                       "표본을 통째로 다시 뽑는 널은 ±5 % 예산(3.8e9·4.2e9) 뿐이다.",
                     "limits_ko": [
                         "⛔자카드 하나로 「프롭이 정한다」를 결론짓지 않는다.",
                         "⛔손잡이와 원인은 일대일이 아니다.",
                         "⛔이 저장소에 실기 계측 대조는 0 건이다."]},
           "band_check_f_tip": band,
           "pairs": pairs, "cells": cells, "missing": missing}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\n⭐{OUT}  읽은 칸 {len(cells)} · 없는 칸 {len(missing)}")
    print("\n  ④ 대역이 _ps 를 따라가나")
    for k, v in band.items():
        print(f"    {k:<16} {v}", flush=True)
    return 0


if __name__ == "__main__":
    os.sched_setaffinity(0, {0, 1})                   # 규약 17 — 코어를 묶는다
    raise SystemExit(main())
