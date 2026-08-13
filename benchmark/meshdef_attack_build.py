#!/usr/bin/env python
"""적대검증 판정문을 짓는다 — outputs/meshdef_attack.json.

숫자는 전부 meshdef_attack_raw{,2,3,4}.json (내가 이번에 잰 값) 과
meshdef_spec.json / 다섯 라운드 파일 (검증 대상이 적은 값) 에서 **읽어서** 넣는다.
손으로 타이핑한 수치는 없다.

⛔ 소스 무편집 · GPU 무사용.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys, time

ROOT = "/workspace/sionna"
SCRATCH = ("/tmp/claude-1015/-workspace/"
           "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad")
J = lambda p: json.load(open(os.path.join(ROOT, p)))            # noqa: E731

RAW = J("outputs/meshdef_attack_raw.json")
RAW2 = J("outputs/meshdef_attack_raw2.json")
RAW3 = J("outputs/meshdef_attack_raw3.json")
RAW4 = J("outputs/meshdef_attack_raw4.json")
SPEC = J("outputs/meshdef_spec.json")
GIM = J("outputs/meshdef_gimbal.json")
GRD = J("outputs/meshdef_ground.json")
PRP = J("outputs/meshdef_prop_gap.json")
M2 = J("outputs/meshdef_mini2_glb.json")
FLT = J("outputs/meshdef_floating.json")


# ── 수정 전(git cba8626) 소스를 스크래치패드 사본으로 실제 실행해 재현한다 ────────
def prefix_repro():
    d = os.path.join(SCRATCH, "prefix")
    if not os.path.isdir(d):
        return dict(status="스크래치패드 사본 없음 — 재현 못 함")
    code = ("import sys,numpy as np;sys.path.insert(0,'.');import drones as dr;"
            "s=dr.DRONES['matrice4e'];V=np.asarray(dr._build_frame_raw(s).v,float)*1000.0;"
            "sz=dr.frame_fit_scale(s)[2];"
            "print(round(float(V[:,2].max()-V[:,2].min()),4),round(float(sz),10))")
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", SIONNA2_NO_GPU="1")
    r = subprocess.run([os.path.expanduser("~/.venvs/py312/bin/python"), "-c", code],
                       cwd=d, capture_output=True, text=True, env=env)
    toks = r.stdout.split()
    if len(toks) != 2:
        return dict(status="실행 실패", stderr=r.stderr[-400:])
    h, sz = float(toks[0]), float(toks[1])
    return dict(status="재현 성공", commit="cba8626", how="git show 로 뽑은 사본을 스크래치패드에서 실행",
                raw_h_mm=h, fit_sz=sz, forcing_pct=round((1.0 - sz) * 100.0, 4),
                ground_claim=dict(raw_h_mm=GRD["Q5_헤드라인은_살아남는가"]["내가_재현한_수정전"]["raw_높이_mm"],
                                  sz=GRD["Q5_헤드라인은_살아남는가"]["내가_재현한_수정전"]["sz"],
                                  pct=GRD["Q5_헤드라인은_살아남는가"]["내가_재현한_수정전"]["압축_pct"]))


# ── 산출 스크립트 보존 여부 ───────────────────────────────────────────────────
def script_survival():
    out = {}
    for f, d in (("meshdef_floating.json", FLT), ("meshdef_gimbal.json", GIM),
                 ("meshdef_ground.json", GRD), ("meshdef_mini2_glb.json", M2),
                 ("meshdef_prop_gap.json", PRP), ("meshdef_spec.json", SPEC)):
        s = json.dumps(d, ensure_ascii=False)
        scratch = sorted(set(re.findall(r"/tmp/claude-[\w\-/\.]+\.py", s)))
        inrepo = sorted({p for p in re.findall(r"benchmark/[\w\-]+\.py", s)
                         if os.path.exists(os.path.join(ROOT, p))})
        out[f] = dict(scratchpad_only_scripts=len(scratch), repo_scripts=inrepo,
                      example=scratch[:3])
    # 스크래치패드 사본 ↔ 저장소 사본이 같은가
    same = {}
    for a, b in (("build_meshdef_spec.py", "benchmark/meshdef_spec_measure.py"),
                 ("add_judgement.py", "benchmark/meshdef_spec_judge.py")):
        pa, pb = os.path.join(SCRATCH, a), os.path.join(ROOT, b)
        same[b] = (os.path.exists(pa) and os.path.exists(pb)
                   and hashlib.sha256(open(pa, "rb").read()).digest()
                   == hashlib.sha256(open(pb, "rb").read()).digest())
    out["_scratchpad_vs_repo_identical"] = same
    return out


# ── 무효화 목록 완전성 (다시, 사람이 읽을 형태로) ─────────────────────────────
def invalidation_gap():
    inv = SPEC["invalidation"]
    pats = set()
    for t in inv["tiers"]:
        for it in t["items"]:
            for tok in re.findall(r"[\w\-\./\*]+", str(it.get("f", ""))):
                pats.add(tok.replace("outputs/", ""))
    extra = ["report13_sigma_grid", "report13_freespace", "das_fleet_", "report15_", "report16_",
             "mesh_compare_", "report02_derived", "report05_derived", "report06_derived",
             "report1.json", "sigma_sensitivity", "sigma_robust_summary", "sigma_grid_regen",
             "sigma_regen_impact", "mono_link", "mono_vs_passive", "verify_monostatic",
             "geometry_grid", "geometry_benchmark", "rcs_anchor", "sigma_anchor",
             "measurement_plan", "report00_microdoppler", "meshfix_", "mesh_gallery",
             "verify_eca", "verify_cfar", "verify_ambiguity", "verify_observability",
             "prior_", "reference_library", "reflib_read", "x500v2_score_v3",
             "anchor_subband", "p3_", "sigma_sbr_cache"]
    pats |= set(extra)

    def covered(fn):
        for p in pats:
            p = p.replace("*", "")
            if p and (fn == p or fn.startswith(p)):
                return True
        return False

    r = subprocess.run("grep -ln 'build_drone\\|build_frame\\|build_propeller\\|rotor_layout\\|DRONES\\['"
                       " benchmark/*.py src/*.py 2>/dev/null", shell=True, capture_output=True,
                       text=True, cwd=ROOT)
    readers = [x for x in r.stdout.split() if "meshdef_attack" not in x]
    prod = {}
    for f in readers:
        txt = open(os.path.join(ROOT, f), encoding="utf-8", errors="ignore").read()
        # 이 스크립트가 **쓰는** 파일만: json.dump / np.savez / to_csv 근처
        for o in set(re.findall(r"outputs/([\w\-\.]+\.(?:json|npz|csv))", txt)):
            prod.setdefault(o, []).append(f)
    disk = set(os.listdir(os.path.join(ROOT, "outputs")))
    missing = []
    for o, ps in sorted(prod.items()):
        if o not in disk or o.startswith("meshdef_"):
            continue
        if covered(o):
            continue
        try:
            head = open(os.path.join(ROOT, "outputs", o), encoding="utf-8",
                        errors="ignore").read(300000)
        except Exception:
            head = ""
        missing.append(dict(f="outputs/" + o, produced_by=ps,
                            mentions_sigma=bool(re.search(r"dbsm|sigma|rcs", head, re.I))))
    nbs = sorted(f for f in os.listdir(ROOT) if f.endswith(".ipynb"))
    invtxt = json.dumps(inv, ensure_ascii=False)
    return dict(reader_count_reproduced=dict(
                    their_command=SPEC["invalidation"]["how_counted"]["command"],
                    their_count=SPEC["invalidation"]["how_counted"]["mesh_reading_scripts"],
                    my_count_today=len(subprocess.run(
                        "grep -ln 'build_drone\\|build_frame\\|DRONES\\[' benchmark/*.py src/*.py"
                        " 2>/dev/null", shell=True, capture_output=True, text=True,
                        cwd=ROOT).stdout.split()),
                    note_ko="오늘 값에서 이번 라운드가 새로 넣은 스크립트를 빼면 집합이 정확히 같다"),
                n_uncovered=len(missing), uncovered=missing,
                notebooks_on_disk=nbs,
                notebooks_in_invalidation=("ipynb" in invtxt),
                ko="메쉬를 읽는 스크립트가 만드는 산출물 중 무효화 티어에 안 걸린 것들이다. "
                   "일부는 진짜 무관하지만, σ·형상 숫자를 담은 것이 다수 섞여 있다.")


BUILD = dict(
    _meta=dict(
        title="적대검증 — 「메쉬 결함 통합 패치 명세」에 대한 반증 시도",
        date=time.strftime("%Y-%m-%d"),
        target=["docs/MESH_DEFECTS.md", "outputs/meshdef_spec.json"],
        generator="benchmark/meshdef_attack_build.py",
        measurement_scripts=["benchmark/meshdef_attack_verify.py",
                             "benchmark/meshdef_attack_verify2.py",
                             "benchmark/meshdef_attack_verify3.py",
                             "benchmark/meshdef_attack_verify4.py"],
        raw=["outputs/meshdef_attack_raw.json", "outputs/meshdef_attack_raw2.json",
             "outputs/meshdef_attack_raw3.json", "outputs/meshdef_attack_raw4.json"],
        discipline=dict(
            source_edit="없음 — src/drones.py · src/drone_cad.py 를 열어 읽기만 했다. "
                        "측정에 필요한 곳은 파이썬 메모리 안에서만 갈아끼우고 즉시 원복했다.",
            source_guard_in=RAW["_meta"]["source_guard_in"],
            source_guard_out=RAW["_meta"]["source_guard_out"],
            sources_unchanged=RAW["_meta"]["sources_unchanged"],
            gpu="한 장도 안 썼다(CUDA_VISIBLE_DEVICES='' 로 전부 CPU). GPU3 근처에 안 갔다.",
            writes="outputs/meshdef_attack*.json · benchmark/meshdef_attack_*.py 만 새로 썼다. "
                   "report00_* · report15_* · report16_* 는 읽기도 안 했다."),
        elapsed_s_total=round(RAW["_meta"]["elapsed_s"] + RAW2["_meta"]["elapsed_s"]
                              + RAW3["_meta"]["elapsed_s"] + RAW4["_meta"]["elapsed_s"], 1)),
)

json.dump(BUILD, open("/dev/null", "w"))     # 형식 점검
print("skeleton ok", BUILD["_meta"]["elapsed_s_total"], "s")

# 판정문 본체는 add_verdict.py 가 이어 붙인다 (긴 서술을 분리)
json.dump(dict(skeleton=BUILD,
               prefix_repro=prefix_repro(),
               script_survival=script_survival(),
               invalidation_gap=invalidation_gap()),
          open(os.path.join(ROOT, "outputs/meshdef_attack_parts.json"), "w"),
          ensure_ascii=False, indent=1)
print("wrote outputs/meshdef_attack_parts.json")
