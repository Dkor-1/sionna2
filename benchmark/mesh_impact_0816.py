# -*- coding: utf-8 -*-
"""
mesh_impact_0816.py — **영향 측정 드라이버**: 수리 하나하나가 무엇을 얼마나 바꿨나
================================================================================

이 라운드는 값을 넣지 않는다. 앞선 세 라운드가 넣은 값의 **영향을 잰다.**

무엇을 하나
  1. 저장소 `src/` 를 얼린 스냅샷에서 **수리를 하나씩 되돌린 소스 트리 6벌**을 만든다.
       T0  아무 수리도 없음(기준선)
       T1  + ③ 끝단 캡(smooth_iters 0)                    [셸형 6종]
       T2  + ⑥ phantom4 외형 강제 해제(envelope_mm)        [phantom4]
       T3  + ① mavic4pro 짐벌 축소(0.050 → 0.0316)         [mavic4pro]
       T4  + ④ matrice4e 뒷다리 inboard 로터별              [matrice4e]
       T5  + ⑦ matrice4e 모터 벨 z 사슬(= 현재 저장소)      [matrice4e]
     ⭐ 순서는 앞 라운드들이 실제로 넣은 순서와 같다(상류부터). T5 의 소스는 스냅샷과
       **바이트 단위로 같아야 한다** — 그것으로 «되돌리기 규칙이 옳다» 를 증명한다.
  2. 트리마다 `mesh_impact_probe_0816.py` 를 **별도 프로세스**로 돌린다.
     (다른 라운드가 저장소 소스를 동시에 고치고 있어서, 저장소를 직접 재면 귀속이 깨진다.)
  3. 단계 간 차이를 표로 만든다 — 기체 × 수리 × (형상 Δmm · σ Δdb 방위평균 ·
     σ Δdb 최악방위 · 검사기) + **누적**(T5 − T0) + **마이크로도플러 축** + **비트동일**.

⛔ GPU 금지 · git 금지 · CPU 전용. σ 는 우리 커널 PO(가림 없음 · 재질 가중).

실행:
  cd /workspace/sionna && CUDA_VISIBLE_DEVICES="" \
    /workspace/.venvs/py312/bin/python benchmark/mesh_impact_0816.py --stage all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = "/workspace/sionna"
SNAP = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/snap/src"
WORK = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/trees"
PY = "/workspace/.venvs/py312/bin/python"
PROBE = os.path.join(ROOT, "benchmark", "mesh_impact_probe_0816.py")
OUT = os.path.join(ROOT, "outputs", "mesh_impact_0816.json")

AFFECTED = ["mini5pro", "mavic4pro", "matrice4e", "mini2", "phantom3", "phantom4"]
UNTOUCHED = ["m350rtk", "x500v2", "s1000plus", "typhoonh480"]
MD_KEYS = ["matrice4e", "mavic4pro", "phantom4", "mini5pro", "m350rtk"]

#  «되돌리기» 규칙 — (파일, 찾을 문자열, 바꿀 문자열, 기대 개수)
#  찾을 문자열 = **지금 저장소에 들어 있는(수리 후) 값**, 바꿀 문자열 = **수리 전 값**.
REVERT = {
    "caps": [("drone_cad.py", r"(?m)^(\s*)smooth_iters=0([,)])", r"\1smooth_iters=4\2", 6)],
    "env": [("drones.py",
             "envelope_mm=(None, None, 196.0)),",
             "envelope_mm=(289.5, 289.5, 196.0)),", 1)],
    "gimbal": [("drone_cad.py",
                "_gimbal_hasselblad(0.0316, gx, -0.30 * bh)",
                "_gimbal_hasselblad(0.050, gx, -0.30 * bh)", 1)],
    "b4": [("drone_cad.py",
            'GEAR_SPIKE_INBOARD = {"matrice4e": (1.011, 1.034, 1.034, 1.011)}',
            'GEAR_SPIKE_INBOARD = {}', 1)],
    "b7": [("drone_cad.py",
            'GEAR_SPIKE_H = {"matrice4e": (0.04661, 0.03879, 0.03879, 0.04661)}',
            'GEAR_SPIKE_H = {"matrice4e": 0.0529}', 1),
           ("drone_cad.py",
            'GEAR_TOP_Z = {"matrice4e": (-0.00851, -0.01633, -0.01633, -0.00851)}',
            'GEAR_TOP_Z = {}', 1),
           ("drone_cad.py",
            'MOTOR_BASE_Z = {"phantom3": 0.0110, "mini2": 0.007985, "matrice4e": -0.01242}',
            'MOTOR_BASE_Z = {"phantom3": 0.0110, "mini2": 0.007985}', 1),
           ("drone_cad.py",
            'ARM_Z_FOLLOWS_ROTOR = {"mini2": True, "mini5pro": True, "matrice4e": True}',
            'ARM_Z_FOLLOWS_ROTOR = {"mini2": True, "mini5pro": True}', 1),
           ("drone_cad.py",
            'ARM_TIP_Z = {"matrice4e": (-0.01635, -0.02228, -0.02228, -0.01635)}',
            'ARM_TIP_Z = {}', 1),
           ("drones.py",
            "        rotor_z_mm=(3.91, -3.91, -3.91, 3.91),\n", "", 1)],
}
#  단계 = «이 트리에서 아직 안 들어간 수리» 목록
STAGES = [
    ("T0", "기준선(수리 0건)", ["caps", "env", "gimbal", "b4", "b7"]),
    ("T1", "+③ 끝단 캡", ["env", "gimbal", "b4", "b7"]),
    ("T2", "+⑥ phantom4 외형 해제", ["gimbal", "b4", "b7"]),
    ("T3", "+① mavic4pro 짐벌", ["b4", "b7"]),
    ("T4", "+④ matrice4e 뒷다리", ["b7"]),
    ("T5", "+⑦ matrice4e 벨 z (= 현재 저장소)", []),
]
REPAIR_OF = {"T1": "caps", "T2": "env", "T3": "gimbal", "T4": "b4", "T5": "b7"}
REPAIR_KEYS = {"caps": AFFECTED, "env": ["phantom4"], "gimbal": ["mavic4pro"],
               "b4": ["matrice4e"], "b7": ["matrice4e"]}
#  ⭐ «상쇄하나 더하나» 를 **진짜로** 재려면 수리 하나만 든 세계가 필요하다.
#     사슬(T0→T1→…→T5)의 단계별 Δ 를 더하면 누적 Δ 가 되는 것은 **망원경 항등식**이라
#     상호작용의 증거가 아니다. 그래서 «그 수리 하나만 넣은» 트리를 따로 짓는다.
ISO = [("I_caps", ["env", "gimbal", "b4", "b7"], "caps"),
       ("I_env", ["caps", "gimbal", "b4", "b7"], "env"),
       ("I_gimbal", ["caps", "env", "b4", "b7"], "gimbal"),
       ("I_b4", ["caps", "env", "gimbal", "b7"], "b4"),
       ("I_b7", ["caps", "env", "gimbal", "b4"], "b7")]


def md5f(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def build_trees():
    os.makedirs(WORK, exist_ok=True)
    log = {}
    for tag, desc, undo in (STAGES + [(t, f"«{r}» 하나만", u) for t, u, r in ISO]):
        d = os.path.join(WORK, tag)
        if os.path.isdir(d):
            shutil.rmtree(d)
        shutil.copytree(SNAP, d)
        shutil.rmtree(os.path.join(d, "__pycache__"), ignore_errors=True)
        applied = []
        for rep in undo:
            for fn, old, new, n_exp in REVERT[rep]:
                p = os.path.join(d, fn)
                s = open(p).read()
                if old.startswith("(?m)"):
                    s2, n = re.subn(old, new, s)
                else:
                    n = s.count(old)
                    s2 = s.replace(old, new)
                if n != n_exp:
                    raise SystemExit(f"[되돌리기 실패] {tag}/{rep}/{fn}: {n}건 (기대 {n_exp})")
                open(p, "w").write(s2)
                applied.append(f"{rep}:{fn}:{n}")
        log[tag] = dict(desc=desc, undone=undo, edits=applied,
                        md5={f: md5f(os.path.join(d, f)) for f in ("drone_cad.py", "drones.py")})
    #  T5 는 스냅샷과 바이트 단위로 같아야 한다
    for f in ("drone_cad.py", "drones.py"):
        assert log["T5"]["md5"][f] == md5f(os.path.join(SNAP, f)), f"T5 ≠ 스냅샷 ({f})"
    log["_snapshot_md5"] = {f: md5f(os.path.join(SNAP, f)) for f in ("drone_cad.py", "drones.py")}
    log["_repo_md5_now"] = {f: md5f(os.path.join(ROOT, "src", f))
                            for f in ("drone_cad.py", "drones.py")}
    return log


def run_probes(par=6):
    procs, outs = [], {}
    jobs = [(t, AFFECTED, MD_KEYS) for t, _d, _u in STAGES]
    jobs += [(t, REPAIR_KEYS[r], [k for k in MD_KEYS if k in REPAIR_KEYS[r]])
             for t, _u, r in ISO if t != "I_caps"]     # I_caps == T1 이라 다시 안 잰다
    for tag, sig_keys, md_keys in jobs:
        o = os.path.join(WORK, f"probe_{tag}.json")
        outs[tag] = o
        cmd = [PY, PROBE, "--src", os.path.join(WORK, tag), "--out", o,
               "--sigma", ",".join(sig_keys), "--md", ",".join(md_keys), "--az-step", "1.0"]
        env = dict(os.environ, CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="4",
                   OPENBLAS_NUM_THREADS="4", MKL_NUM_THREADS="4")
        procs.append((tag, subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.PIPE)))
    for tag, p in procs:
        rc = p.wait()
        err = p.stderr.read().decode()[-2000:]
        print(f"[probe {tag}] rc={rc} {err[-300:] if rc else ''}", flush=True)
        if rc:
            raise SystemExit(f"probe {tag} 실패:\n{err}")
    return {t: json.load(open(o)) for t, o in outs.items()}


# --------------------------------------------------------------------------- #
#  σ 통계
# --------------------------------------------------------------------------- #
def ang_smooth(s, win_deg, step):
    n = max(1, int(round(win_deg / step)))
    k = np.ones(n) / n
    return np.convolve(np.concatenate([s[-n:], s, s[:n]]), k, "same")[n:-n]


def sig_stats(sig, step=1.0):
    s = np.asarray(sig, float)
    sm = ang_smooth(s, 3.0, step)
    az = np.arange(0, 360, step)
    return dict(az_mean_dbsm=round(float(10 * np.log10(s.mean())), 3),
                med_dbsm=round(float(10 * np.log10(np.median(s))), 3),
                worst_dbsm=round(float(10 * np.log10(sm.min())), 3),
                worst_az=float(az[int(np.argmin(sm))]),
                best_dbsm=round(float(10 * np.log10(sm.max())), 3),
                best_az=float(az[int(np.argmax(sm))]),
                cuts={f"az{int(a)}": round(float(10 * np.log10(sm[int(a / step)])), 3)
                      for a in (0, 90, 180, 270)})


def pattern_delta(a, b, step=1.0):
    """전후 방위패턴의 «같은 실현인가» 잣대 — dB 차의 RMS·상관."""
    A, B = 10 * np.log10(np.asarray(a, float)), 10 * np.log10(np.asarray(b, float))
    d = A - B
    return dict(rms_db=round(float(np.sqrt((d ** 2).mean())), 3),
                p95_abs_db=round(float(np.percentile(np.abs(d), 95)), 3),
                max_abs_db=round(float(np.abs(d).max()), 3),
                max_abs_az=float(np.arange(0, 360, step)[int(np.argmax(np.abs(d)))]),
                corr=round(float(np.corrcoef(A, B)[0, 1]), 4))


def sigma_block(after, before):
    """after/before = probe 의 sigma[key] dict."""
    out = {}
    for el in ("el0", "el15"):
        sa, sb = sig_stats(after[el]), sig_stats(before[el])
        out[el] = dict(
            before=sb, after=sa,
            d_az_mean_db=round(sa["az_mean_dbsm"] - sb["az_mean_dbsm"], 3),
            d_worst_db=round(sa["worst_dbsm"] - sb["worst_dbsm"], 3),
            d_med_db=round(sa["med_dbsm"] - sb["med_dbsm"], 3),
            d_cuts_db={c: round(sa["cuts"][c] - sb["cuts"][c], 3) for c in sa["cuts"]},
            pattern=pattern_delta(after[el], before[el]))
    return out


# --------------------------------------------------------------------------- #
#  형상 Δ
# --------------------------------------------------------------------------- #
def geom_delta(ga, gb):
    if "build_error" in ga or "build_error" in gb:
        return dict(error=[ga.get("build_error"), gb.get("build_error")])
    d = {}
    for f in ("drone_bbox_mm", "frame_raw_bbox_mm", "lwh_mm", "drone_z_mm"):
        d["d_" + f] = [round(x - y, 4) for x, y in zip(ga[f], gb[f])]
    d["d_wheelbase_mm"] = round(ga["wheelbase_mm"] - gb["wheelbase_mm"], 4)
    d["d_diag_eff_mm"] = round(ga["diag_eff_mm"] - gb["diag_eff_mm"], 4)
    d["fit_scale_before"] = gb["fit_scale"]
    d["fit_scale_after"] = ga["fit_scale"]
    d["d_n_tri"] = ga["n_tri"] - gb["n_tri"]
    d["d_rotor_centers_mm"] = [[round(x - y, 4) for x, y in zip(A, B)]
                               for A, B in zip(ga["rotor_centers_mm"], gb["rotor_centers_mm"])]
    gz = {}
    for g in sorted(set(ga["group_z"]) | set(gb["group_z"])):
        A, B = ga["group_z"].get(g), gb["group_z"].get(g)
        if A is None or B is None:
            gz[g] = "그룹 유무가 바뀜"
            continue
        dz = [round(A["z_mm"][0] - B["z_mm"][0], 4), round(A["z_mm"][1] - B["z_mm"][1], 4)]
        gz[g] = dict(d_z_mm=dz, sha_same=(ga["group_sha"][g] == gb["group_sha"][g]),
                     z_before=B["z_mm"], z_after=A["z_mm"])
    d["groups"] = gz
    d["changed_groups"] = sorted(g for g in gz if isinstance(gz[g], dict) and not gz[g]["sha_same"])
    d["sha_drone_same"] = ga["sha_drone"] == gb["sha_drone"]
    return d


# --------------------------------------------------------------------------- #
#  마이크로도플러 축
# --------------------------------------------------------------------------- #
def md_delta(ma, mb):
    """σ(로터 위상) 3차원 배열 (위상, el, az) 의 전후 차이.
    ⭐ «움직이는 성분» = 위상축을 따라 변하는 부분(평균 뺀 나머지). 그것이 마이크로도플러다."""
    lab = [f"el{int(e)}az{int(a)}" for e in ma["els"] for a in ma["az_deg"]]
    out = dict(n_rotor=ma["n_rotor"], labels=lab)
    for name in ("md_full", "md_prop_only", "md_single_rotor"):
        RA, RB = np.asarray(ma[name], float), np.asarray(mb[name], float)
        A = (10 * np.log10(RA + 1e-300)).reshape(RA.shape[0], -1)
        B = (10 * np.log10(RB + 1e-300)).reshape(RB.shape[0], -1)
        acA, acB = A - A.mean(0, keepdims=True), B - B.mean(0, keepdims=True)
        out[name] = dict(
            bit_identical=bool(np.array_equal(RA, RB)),
            d_mean_db=dict(zip(lab, [round(float(x), 4) for x in (A.mean(0) - B.mean(0))])),
            mod_ptp_db_before=dict(zip(lab, [round(float(x), 3) for x in (B.max(0) - B.min(0))])),
            mod_ptp_db_after=dict(zip(lab, [round(float(x), 3) for x in (A.max(0) - A.min(0))])),
            d_mod_ptp_db=dict(zip(lab, [round(float(x), 4) for x in
                                        ((A.max(0) - A.min(0)) - (B.max(0) - B.min(0)))])),
            #  ⭐ 이 한 줄이 «움직이는 성분이 0 인가» 의 답이다 — 위상 변동분의 RMS 차이
            d_ac_rms_db=dict(zip(lab, [round(float(x), 4) for x in
                                       np.sqrt(((acA - acB) ** 2).mean(0))])),
            max_abs_d_ac_db=round(float(np.abs(acA - acB).max()), 4),
            max_abs_d_db=round(float(np.abs(A - B).max()), 4))
    return out


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    a = ap.parse_args()
    t0 = time.time()
    print("[1] 되돌린 소스 트리 6벌 제작", flush=True)
    trees = build_trees()
    print("[2] 트리별 측정(병렬)", flush=True)
    pr = run_probes()
    print(f"[3] 표 조립 ({time.time()-t0:.0f}s)", flush=True)

    res = dict(_meta=dict(
        title="메쉬 값 적용 라운드 — 영향 측정(수리별·누적·마이크로도플러·비트동일)",
        ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        sigma_convention=("우리 커널 PO(src/rcs_po.py) · CPU · 가림 없음 · 재질 가중 |Γ| · "
                          "fc 3.5 GHz · 대역 100 MHz 5주파 비코히런트 평균 · 점간격 λ/7(중심) · "
                          "방위 1° 360점 · el 0°/15° · 최악방위는 3° 각도평활 뒤 최저"),
        method=("저장소 src/ 를 얼린 스냅샷에서 수리를 하나씩 되돌린 트리 6벌을 만들고 "
                "트리마다 별도 프로세스로 쟀다(다른 라운드가 저장소를 동시 편집 중)."),
        trees=trees, stages=[[t, d, u] for t, d, u in STAGES],
                          isolated=[[t, u, r] for t, u, r in ISO]), per_repair={}, cumulative={},
        micro_doppler={}, bit_identity={}, gate={})

    #  ── 수리별 (단계 i-1 → i) ────────────────────────────────────────────
    order = [s[0] for s in STAGES]
    for i in range(1, len(order)):
        tb, ta = order[i - 1], order[i]
        rep = REPAIR_OF[ta]
        blk = dict(stage=f"{tb}→{ta}", repair=rep, desc=STAGES[i][1], keys={})
        for k in AFFECTED + UNTOUCHED:
            gd = geom_delta(pr[ta]["geom"][k], pr[tb]["geom"][k])
            e = dict(geom=gd, expected_to_change=(k in REPAIR_KEYS[rep]))
            if k in pr[ta]["sigma"] and k in pr[tb]["sigma"]:
                e["sigma"] = sigma_block(pr[ta]["sigma"][k], pr[tb]["sigma"][k])
            blk["keys"][k] = e
        res["per_repair"][rep] = blk

    #  ── 누적 (T0 → T5) ──────────────────────────────────────────────────
    for k in AFFECTED + UNTOUCHED:
        e = dict(geom=geom_delta(pr["T5"]["geom"][k], pr["T0"]["geom"][k]))
        if k in pr["T5"]["sigma"]:
            e["sigma"] = sigma_block(pr["T5"]["sigma"][k], pr["T0"]["sigma"][k])
            for el in ("el0", "el15"):
                #  ⚠ 사슬 단계 Δ 의 합 = 누적 Δ 는 **망원경 항등식**이라 검산일 뿐이다.
                chain = sum(res["per_repair"][r]["keys"][k]["sigma"][el]["d_az_mean_db"]
                            for r in res["per_repair"])
                #  ⭐ 진짜 «상쇄하나 더하나» — 수리 하나만 든 세계들의 Δ 를 더해 누적과 비교.
                iso, iso_terms = 0.0, {}
                for tag, _u, rep in ISO:
                    if k not in REPAIR_KEYS[rep]:
                        continue
                    src = pr["T1"] if tag == "I_caps" else pr[tag]
                    v = sigma_block(src["sigma"][k], pr["T0"]["sigma"][k])[el]["d_az_mean_db"]
                    iso_terms[rep] = v
                    iso += v
                e["sigma"][el]["chain_sum_db"] = round(chain, 3)
                e["sigma"][el]["chain_check_db"] = round(e["sigma"][el]["d_az_mean_db"] - chain, 4)
                e["sigma"][el]["isolated_terms_db"] = {r: round(v, 3) for r, v in iso_terms.items()}
                e["sigma"][el]["isolated_sum_db"] = round(iso, 3)
                e["sigma"][el]["interaction_db"] = round(e["sigma"][el]["d_az_mean_db"] - iso, 3)
        res["cumulative"][k] = e

    #  ── 마이크로도플러 축 ────────────────────────────────────────────────
    for k in MD_KEYS:
        res["micro_doppler"][k] = dict(
            cumulative=md_delta(pr["T5"]["md"][k], pr["T0"]["md"][k]),
            per_repair={REPAIR_OF[order[i]]: md_delta(pr[order[i]]["md"][k],
                                                      pr[order[i - 1]]["md"][k])
                        for i in range(1, len(order))},
            prop_sha={t: [pr[t]["geom"][k]["sha_prop_ccw"], pr[t]["geom"][k]["sha_prop_cw"]]
                      for t in order})

    #  ── 비트동일 ────────────────────────────────────────────────────────
    for k in AFFECTED + UNTOUCHED:
        shas = {t: pr[t]["geom"][k]["sha_drone"] for t in order}
        res["bit_identity"][k] = dict(
            sha_by_stage=shas,
            identical_T0_T5=(shas["T0"] == shas["T5"]),
            changed_at=[order[i] for i in range(1, len(order))
                        if shas[order[i]] != shas[order[i - 1]]],
            expected_untouched=(k in UNTOUCHED))
    res["bit_identity"]["_verdict"] = (
        "안 건드린 4종(m350rtk·x500v2·s1000plus·typhoonh480) 이 T0→T5 내내 지문 불변이면 통과"
        if all(res["bit_identity"][k]["identical_T0_T5"] for k in UNTOUCHED)
        else "⛔ 실패 — 안 건드려야 할 기체가 바뀌었다")

    with open(OUT, "w") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(f"[완료] {OUT} ({os.path.getsize(OUT)/1024:.0f} KB, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
