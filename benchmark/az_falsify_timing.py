# -*- coding: utf-8 -*-
"""az_falsify_timing.py — «az45 팔의 계산 시간이 다르다» 를 기계 부하로 설명할 수 있나.

방법: 샤드 파일마다 [끝 = mtime, 시작 = mtime − meta[5](경과초)] 구간을 만든다.
      그 구간이 **샤드 폴더 전체**의 다른 구간과 얼마나 겹치는지(동시 실행 개수)를
      시간가중 평균으로 낸다 = 그 샤드가 겪은 기계 부하.
      그 다음 자세당 초 ↔ 부하 의 관계를 본다.
⛔GPU 안 쓴다. ⛔기존 파일 안 고친다.
"""
from __future__ import annotations
import glob, json, os
import numpy as np

ROOT = "/workspace/sionna"
SHD = f"{ROOT}/outputs/elev_sweep_shards"
OUT = f"{ROOT}/outputs/az_falsify_timing.json"

ARMS = {
    "ours_az0": "ours_r15_n8192",
    "ours_az45": "ours_r15_n8192_az45",
    "ps_az0": "sionna_p4000000000_r15_n8192_d1",
    "ps_az45": "sionna_p4000000000_r15_n8192_az45_d1",
    "psphys_az0": "sionna_p4000000000_phys_r15_n8192_d1",
    "psphys_az45": "sionna_p4000000000_phys_r15_n8192_az45_d1",
}
ELS = (0.0, -30.0, -60.0, -90.0)


def load_all():
    """샤드 폴더 전체의 (파일, 시작, 끝, 자세수) — 기계 부하 배경."""
    recs = []
    for f in glob.glob(f"{SHD}/*_el*.npz"):
        try:
            z = np.load(f)
            m = np.asarray(z["meta"], float)
            dur = float(m[5]); npose = int(z["idx"].size)
        except Exception:
            continue
        end = os.path.getmtime(f)
        recs.append((os.path.basename(f), end - dur, end, npose))
    return recs


def overlap_load(t0, t1, others):
    """[t0,t1) 동안 동시에 돌던 **다른** 샤드 프로세스 수의 시간가중 평균."""
    if t1 <= t0:
        return float("nan")
    edges = {t0, t1}
    for _, s, e, _ in others:
        if e > t0 and s < t1:
            edges.add(max(s, t0)); edges.add(min(e, t1))
    xs = sorted(edges)
    tot = 0.0
    for a, b in zip(xs[:-1], xs[1:]):
        mid = 0.5 * (a + b)
        cnt = sum(1 for _, s, e, _ in others if s <= mid < e)
        tot += cnt * (b - a)
    return tot / (t1 - t0)


def main():
    allrec = load_all()
    print(f"샤드 총 {len(allrec)} 개에서 시간 구간 복원")
    out = {"_meta": {"n_shards_scanned": len(allrec), "gpu_used": False,
                     "method_ko": "샤드 [mtime−경과, mtime] 구간의 시간가중 동시실행 수"},
           "arms": {}}
    for nm, eng in ARMS.items():
        rec = {}
        for el in ELS:
            fs = sorted(glob.glob(f"{SHD}/{eng}_el{el:+.0f}_*.npz"))
            if not fs:
                continue
            per, loads, starts, ends = [], [], [], []
            for f in fs:
                z = np.load(f); m = np.asarray(z["meta"], float)
                dur = float(m[5]); npose = int(z["idx"].size)
                end = os.path.getmtime(f); start = end - dur
                base = os.path.basename(f)
                others = [r for r in allrec if r[0] != base]
                per.append(dur / npose)
                loads.append(overlap_load(start, end, others))
                starts.append(start); ends.append(end)
            rec[f"{el:+.0f}"] = dict(
                n_shards=len(fs),
                sec_per_pose_med=round(float(np.median(per)), 4),
                sec_per_pose_min=round(float(np.min(per)), 4),
                sec_per_pose_max=round(float(np.max(per)), 4),
                machine_load_med=round(float(np.median(loads)), 2),
                machine_load_min=round(float(np.min(loads)), 2),
                machine_load_max=round(float(np.max(loads)), 2),
                t_start_utc=float(np.min(starts)), t_end_utc=float(np.max(ends)),
            )
        out["arms"][nm] = rec

    # ── 부하 ↔ 자세당 시간 상관 (엔진별로, az0·az45 를 한 표본집합에 넣는다) ──
    corr = {}
    for eng_tag, (a0, a45) in {"ours": ("ours_az0", "ours_az45"),
                               "ps": ("ps_az0", "ps_az45"),
                               "psphys": ("psphys_az0", "psphys_az45")}.items():
        X, Y, W = [], [], []
        for nm in (a0, a45):
            for el, d in out["arms"][nm].items():
                X.append(d["machine_load_med"]); Y.append(d["sec_per_pose_med"])
                W.append(nm.endswith("az45"))
        X, Y = np.array(X), np.array(Y)
        r = float(np.corrcoef(X, Y)[0, 1]) if X.size > 2 else float("nan")
        corr[eng_tag] = dict(load=[float(x) for x in X], sec_per_pose=[float(y) for y in Y],
                             is_az45=[bool(w) for w in W], pearson_r=round(r, 3))
    out["load_vs_time"] = corr

    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1, default=float)
    print("wrote", OUT)
    import datetime as dt
    for nm, rec in out["arms"].items():
        print(f"\n{nm}")
        for el, d in rec.items():
            t0 = dt.datetime.utcfromtimestamp(d["t_start_utc"]) + dt.timedelta(hours=9)
            t1 = dt.datetime.utcfromtimestamp(d["t_end_utc"]) + dt.timedelta(hours=9)
            print(f"  el{el}: s/pose {d['sec_per_pose_med']:.4f} "
                  f"({d['sec_per_pose_min']:.4f}~{d['sec_per_pose_max']:.4f}) "
                  f"| 동시실행 {d['machine_load_med']:.1f} "
                  f"({d['machine_load_min']:.1f}~{d['machine_load_max']:.1f}) "
                  f"| KST {t0:%m-%d %H:%M}→{t1:%m-%d %H:%M}")
    print("\n── 부하 ↔ 자세당 시간 ──")
    for k, v in out["load_vs_time"].items():
        print(f"  {k}: r = {v['pearson_r']}  load {['%.1f'%x for x in v['load']]}  "
              f"s/pose {['%.3f'%y for y in v['sec_per_pose']]}  az45 {v['is_az45']}")


if __name__ == "__main__":
    main()
