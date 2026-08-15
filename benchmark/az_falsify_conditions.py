# -*- coding: utf-8 -*-
"""az_falsify_conditions.py — «방위 45° 팔이 정말 같은 조건인가» 를 원장·샤드에서 직접 잰다.

⛔GPU 안 쓴다(sionna.rt·mitsuba import 없음). 저장된 npz·json 만 읽는다.
⛔기존 파일 안 고친다. 결과는 outputs/az_falsify_conditions.json 새로 쓴다.
"""
from __future__ import annotations
import glob, json, os, re
import numpy as np

ROOT = "/workspace/sionna"
SHD = f"{ROOT}/outputs/elev_sweep_shards"
LEDGER = f"{ROOT}/outputs/elevation_sweep_md.json"
NPZ = f"{ROOT}/outputs/elevation_sweep_md.npz"
OUT = f"{ROOT}/outputs/az_falsify_conditions.json"

PAIRS = [
    ("ours",      "ours_r15_n8192",                        "ours_r15_n8192_az45"),
    ("ps_nophys", "sionna_p4000000000_r15_n8192_d1",       "sionna_p4000000000_r15_n8192_az45_d1"),
    ("ps_phys",   "sionna_p4000000000_phys_r15_n8192_d1",  "sionna_p4000000000_phys_r15_n8192_az45_d1"),
]
ELS_CMP = (0.0, -30.0, -60.0, -90.0)


def shard_facts(eng: str, el: float) -> dict:
    fs = sorted(glob.glob(f"{SHD}/{eng}_el{el:+.0f}_*.npz"))
    if not fs:
        return dict(present=False)
    idx_all, secs, cfgs, metas, mtimes, npaths = [], [], [], [], [], []
    n_decl = set(); nsh_decl = set(); prf = set()
    for f in fs:
        z = np.load(f)
        m = np.asarray(z["meta"], float)
        metas.append([float(x) for x in m])
        n_decl.add(int(m[3])); nsh_decl.add(int(m[2])); prf.add(float(m[4]))
        secs.append(float(m[5]))
        idx_all.append(z["idx"].astype(int))
        mtimes.append(os.path.getmtime(f))
        if "cfg" in z:
            cfgs.append([None if np.isnan(v) else float(v) for v in np.asarray(z["cfg"], float)])
        else:
            cfgs.append(None)
        if "npaths" in z:
            npaths.append(np.asarray(z["npaths"]))
    I = np.concatenate(idx_all)
    n = max(n_decl)
    return dict(
        present=True, n_shards_files=len(fs), nshards_declared=sorted(nsh_decl),
        n_poses_declared=sorted(n_decl), prf_hz=sorted(prf),
        idx_count=int(I.size), idx_unique=int(np.unique(I).size),
        idx_min=int(I.min()), idx_max=int(I.max()),
        idx_covers_all=bool(np.array_equal(np.sort(np.unique(I)), np.arange(n))),
        idx_has_dupes=bool(np.unique(I).size != I.size),
        seconds_sum=round(float(np.sum(secs)), 1),
        seconds_per_shard_med=round(float(np.median(secs)), 1),
        seconds_per_shard_min=round(float(np.min(secs)), 1),
        seconds_per_shard_max=round(float(np.max(secs)), 1),
        sec_per_pose_med=round(float(np.sum(secs) / n), 4),
        cfg_unique=[list(c) if c else None for c in {tuple(c) if c else None for c in cfgs}],
        mtime_first=min(mtimes), mtime_last=max(mtimes),
        wall_span_h=round((max(mtimes) - min(mtimes)) / 3600.0, 3),
        # ⭐동시성 지표: 샤드들이 겹쳐 돌았는가 = (일 합계) / (달력 시간 폭)
        concurrency_est=round(float(np.sum(secs)) / max(1.0, (max(mtimes) - min(mtimes))), 2),
        npaths_med=(int(np.median(np.concatenate(npaths))) if npaths else None),
    )


def series(z, eng, el):
    k = f"{eng}/el{el:+.0f}"
    return np.asarray(z[k], complex) if k in z else None


def ac_dc(E):
    """움직이는 부분(시계열 평균 제거 후 전력) · 가만히 있는 부분(평균의 크기)."""
    mu = complex(np.mean(E))
    ac = float(np.mean(np.abs(E - mu) ** 2))
    return dict(dc_abs=abs(mu), ac_pow=ac,
                ac_db=float(10 * np.log10(ac + 1e-300)),
                dc_db=float(20 * np.log10(abs(mu) + 1e-300)))


def main():
    led = json.load(open(LEDGER))
    rows = {(r["engine"], r["el_deg"]): r for r in led["rows"]}
    z = np.load(NPZ, allow_pickle=True)
    out = {"_meta": {
        "purpose_ko": "az45 팔이 az0 팔과 같은 조건으로 계산됐는지 — 광선예산·깊이·자세수·"
                      "거리·격자·시드·계산시간·결측을 샤드 단위로 대조",
        "gpu_used": False, "source": [LEDGER, NPZ, SHD]},
        "pairs": {}}

    for tag, a0, a45 in PAIRS:
        rec = {"arm_az0": a0, "arm_az45": a45, "els": {}}
        for el in ELS_CMP:
            f0, f45 = shard_facts(a0, el), shard_facts(a45, el)
            r0, r45 = rows.get((a0, el)), rows.get((a45, el))
            E0, E45 = series(z, a0, el), series(z, a45, el)
            e = dict(shards_az0=f0, shards_az45=f45)
            if r0 and r45:
                e["ledger"] = {k: [r0.get(k), r45.get(k)] for k in
                               ("n_poses", "n_missing", "seconds", "range_m", "max_depth",
                                "spp", "physics", "grid_div", "npaths_median", "level_db")}
            if E0 is not None and E45 is not None:
                m0, m45 = ac_dc(E0), ac_dc(E45)
                e["metric"] = dict(
                    ac_db_az0=round(m0["ac_db"], 2), ac_db_az45=round(m45["ac_db"], 2),
                    d_ac_db=round(m45["ac_db"] - m0["ac_db"], 2),
                    dc_abs_az0=m0["dc_abs"], dc_abs_az45=m45["dc_abs"],
                    d_dc_db=round(m45["dc_db"] - m0["dc_db"], 2),
                    n_zero_az0=int((E0 == 0).sum()), n_zero_az45=int((E45 == 0).sum()),
                    identical=bool(np.array_equal(E0, E45)),
                    max_abs_diff=float(np.max(np.abs(E0 - E45))),
                    rel_diff=float(np.max(np.abs(E0 - E45)) / (np.max(np.abs(E0)) + 1e-300)),
                )
            rec["els"][f"{el:+.0f}"] = e
        out["pairs"][tag] = rec

    # ── 시간 산포: 같은 팔 안에서도 벽시계가 얼마나 흔들리나 ──────────────────
    spread = {}
    for tag, a0, a45 in PAIRS:
        for nm, arm in (("az0", a0), ("az45", a45)):
            s = []
            for r in led["rows"]:
                if r["engine"] == arm:
                    s.append(r["seconds"])
            if s:
                spread[f"{tag}/{nm}"] = dict(
                    n_el=len(s), sec_min=min(s), sec_max=max(s),
                    sec_med=float(np.median(s)),
                    within_arm_ratio=round(max(s) / min(s), 2))
    out["wallclock_spread_within_arm"] = spread
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1, default=float)
    print("wrote", OUT)

    # 요약 출력
    for tag, rec in out["pairs"].items():
        print(f"\n═══ {tag}: {rec['arm_az0']}  ↔  {rec['arm_az45']}")
        for el, e in rec["els"].items():
            s0, s45 = e["shards_az0"], e["shards_az45"]
            print(f"  el{el}: shards {s0.get('n_shards_files')}↔{s45.get('n_shards_files')} "
                  f"| nsh_decl {s0.get('nshards_declared')}↔{s45.get('nshards_declared')} "
                  f"| poses {s0.get('n_poses_declared')}↔{s45.get('n_poses_declared')} "
                  f"| cover {s0.get('idx_covers_all')}↔{s45.get('idx_covers_all')} "
                  f"| dup {s0.get('idx_has_dupes')}↔{s45.get('idx_has_dupes')}")
            print(f"        sec/pose {s0.get('sec_per_pose_med')}↔{s45.get('sec_per_pose_med')} "
                  f"| conc {s0.get('concurrency_est')}↔{s45.get('concurrency_est')} "
                  f"| span_h {s0.get('wall_span_h')}↔{s45.get('wall_span_h')}")
            print(f"        cfg az0 {s0.get('cfg_unique')} | cfg az45 {s45.get('cfg_unique')}")
            m = e.get("metric")
            if m:
                print(f"        AC {m['ac_db_az0']:+.2f}→{m['ac_db_az45']:+.2f} "
                      f"(Δ{m['d_ac_db']:+.2f}) · DC Δ{m['d_dc_db']:+.2f} dB "
                      f"· identical={m['identical']} rel={m['rel_diff']:.3e}")
    print("\n── 같은 팔 안 벽시계 산포 ──")
    for k, v in out["wallclock_spread_within_arm"].items():
        print(f"  {k}: {v['sec_min']:.0f}~{v['sec_max']:.0f} s "
              f"(x{v['within_arm_ratio']}) med {v['sec_med']:.0f}")


if __name__ == "__main__":
    main()
