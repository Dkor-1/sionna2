#!/usr/bin/env python
"""적대검증 3부 — mini2 GLB 랜드마크 직접 재측정 + 짐벌 h=61.2 유도 검산 + 무효화 목록 완전성.

⛔ 소스 무편집 · GPU 무사용.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys, time

ROOT = "/workspace/sionna"
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "benchmark"))
sys.path.insert(0, ROOT)
os.environ.setdefault("SIONNA2_NO_GPU", "1"); os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np                      # noqa: E402

R = lambda x, n=4: round(float(x), n)    # noqa: E731
OUT = {}
T0 = time.time()


# ── (a) mini2 GLB — pSphere3(벨리 하방비전 렌즈)의 좌우 오프셋을 직접 잰다 ──────
def a_mini2_lens():
    import trimesh
    p = os.path.join(ROOT, "assets/meshes/reference/WM161_zhankai_1k.glb")
    sc = trimesh.load(p, force="scene")
    geo = dict(sc.geometry)
    world = {}
    for node in sc.graph.nodes_geometry:
        T, g = sc.graph[node]
        V = np.asarray(geo[g].vertices, float)
        Vw = (T[:3, :3] @ V.T).T + T[:3, 3]
        world[node] = np.stack([Vw[:, 2], Vw[:, 0], Vw[:, 1]], 1) * 1000.0   # X=z,Y=x,Z=y

    prop = {"polySurface58", "polySurface61", "polySurface80", "polySurface81",
            "polySurface84", "polySurface89", "polySurface95", "polySurface102"}
    nonprop = np.concatenate([v for k, v in world.items() if k not in prop])
    origin_z = float(nonprop[:, 2].min()) + 24.52          # mini2 라운드 step3 선언
    # 원점 X: Default_4 의 앞뒤 중앙
    d4 = [k for k in world if k.startswith("Default_4")]
    origin_x = float((world[d4[0]][:, 0].min() + world[d4[0]][:, 0].max()) / 2) if d4 else None

    res = dict(origin_x_declared=20.2177, origin_x_measured=R(origin_x, 5) if origin_x else None,
               origin_z_declared=1844.35829, origin_z_measured=R(origin_z, 5),
               nodes=len(world))
    # pSphere3 을 찾는다
    hit = [k for k in world if "pSphere3" in k]
    res["pSphere3_nodes"] = hit
    for k in hit:
        V = world[k]
        neg, pos = V[V[:, 1] < 0], V[V[:, 1] > 0]
        res[f"{k}_bbox_mm"] = [R(x, 4) for x in V.min(0)] + [R(x, 4) for x in V.max(0)]
        res[f"{k}_n_v"] = int(len(V))
        if len(neg) and len(pos):
            cpos = (pos[:, 1].min() + pos[:, 1].max()) / 2.0
            cneg = (neg[:, 1].min() + neg[:, 1].max()) / 2.0
            res[f"{k}_y_centres_mm"] = [R(cneg, 4), R(cpos, 4)]
            res[f"{k}_y_halfsep_mm"] = R((cpos - cneg) / 2.0, 4)
            res[f"{k}_y_gap_mm"] = [R(neg[:, 1].max(), 4), R(pos[:, 1].min(), 4)]
            res[f"{k}_z_rel_origin_mm"] = [R(V[:, 2].min() - origin_z, 3), R(V[:, 2].max() - origin_z, 3)]
            res[f"{k}_x_rel_origin_mm"] = [R(V[:, 0].min() - (origin_x or 0), 3),
                                           R(V[:, 0].max() - (origin_x or 0), 3)]
    # 모터 벨 대각(213.051) 재검
    bell = ["polySurface76", "polySurface96", "polySurface90", "polySurface53"]
    cen = {}
    for b in bell:
        ks = [k for k in world if k == b or k.startswith(b + "_")]
        if ks:
            V = np.concatenate([world[k] for k in ks])
            cen[b] = [(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2]
    if len(cen) == 4:
        c = list(cen.values())
        import itertools
        ds = sorted(float(np.hypot(a[0] - b[0], a[1] - b[1])) for a, b in itertools.combinations(c, 2))
        res["motor_bell_centres"] = {k: [R(v[0], 4), R(v[1], 4)] for k, v in cen.items()}
        res["motor_pair_distances_mm"] = [R(x, 4) for x in ds]
        res["motor_diagonal_mm"] = [R(ds[-1], 4), R(ds[-2], 4)]
    res["published_diagonal_mm"] = 213.0
    res["published_quantum_mm"] = 1.0
    return res


# ── (b) 짐벌 h=61.2 가 사진 58.1 을 재현하는가 ────────────────────────────────
def b_gimbal_h():
    import drone_cad as dc
    rows = {}
    for tag, args in (("current h=47.0", (0.059, 0.047, 0.052, 0.1483, -0.01716)),
                      ("proposed h=61.2", (0.059, 0.0612, 0.052, 0.1483, -0.01036)),
                      ("h=58.1 (photo raw)", (0.059, 0.0581, 0.052, 0.1483, -0.01036))):
        A = dc._gimbal_sensor_v2(*args)
        Vs = [np.asarray(m.vertices, float) * 1000.0 for _g, m in A]
        blk = np.concatenate([Vs[2], Vs[3]])          # block_upper + block_lower
        allv = np.concatenate(Vs)
        rows[tag] = dict(block_h_mm=R(blk[:, 2].max() - blk[:, 2].min(), 3),
                         block_w_mm=R(blk[:, 1].max() - blk[:, 1].min(), 3),
                         block_bottom_z_mm=R(blk[:, 2].min(), 3),
                         assembly_top_z_mm=R(allv[:, 2].max(), 3))
    rows["ratio_block_h_over_h_param"] = R(rows["current h=47.0"]["block_h_mm"] / 47.0, 6)
    rows["implied_h_for_photo_58.1"] = R(58.1 / rows["ratio_block_h_over_h_param"], 3)
    return rows


# ── (c) 무효화 목록 완전성 ───────────────────────────────────────────────────
def c_invalidation():
    spec = json.load(open(os.path.join(ROOT, "outputs/meshdef_spec.json")))
    listed = set()
    for tier in spec["invalidation"]["tiers"]:
        for it in tier["items"]:
            for tok in re.split(r"[·\s]+", str(it.get("f", ""))):
                tok = tok.strip().strip("`")
                if tok:
                    listed.add(tok)
    # B급 문자열도 긁는다
    btxt = json.dumps(spec["invalidation"], ensure_ascii=False)
    listed |= set(re.findall(r"outputs/[\w\*\./]+", btxt))

    # 저장소에서 «메쉬를 읽는» 스크립트를 다시 센다
    def grep_files(pat, globs):
        cmd = f"cd {ROOT} && grep -ln '{pat}' {globs} 2>/dev/null | sort"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return [x for x in r.stdout.split() if x]

    readers = grep_files(r"build_drone\|build_frame\|DRONES\[", "benchmark/*.py src/*.py")
    readers_wide = grep_files(r"build_drone\|build_frame\|build_propeller\|rotor_layout\|DRONES\[\|frame_fit_scale",
                              "benchmark/*.py src/*.py *.py")

    # 스크립트 → 스크립트가 쓰는 outputs 파일 이름 추출
    prod = {}
    for f in readers_wide:
        try:
            txt = open(os.path.join(ROOT, f), encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        outs = set(re.findall(r"outputs/([\w\-\.]+\.(?:json|csv|npz))", txt))
        if outs:
            prod[f] = sorted(outs)

    produced = sorted({o for v in prod.values() for o in v})
    on_disk = {f for f in os.listdir(os.path.join(ROOT, "outputs")) if f.endswith((".json", ".csv", ".npz"))}

    def is_listed(fn):
        if f"outputs/{fn}" in listed or fn in listed:
            return True
        for L in listed:
            L2 = L.replace("outputs/", "")
            if L2.endswith("*") and fn.startswith(L2[:-1]):
                return True
            if "*" in L2:
                pre = L2.split("*")[0]
                if pre and fn.startswith(pre):
                    return True
        return False

    missing = sorted(f for f in produced if f in on_disk and not is_listed(f))
    return dict(n_listed_tokens=len(listed),
                n_mesh_readers_spec_recipe=len(readers),
                n_mesh_readers_wider=len(readers_wide),
                n_products_of_mesh_readers=len(produced),
                missing_from_invalidation=missing,
                n_missing=len(missing),
                producers_of_missing={m: [k for k, v in prod.items() if m in v] for m in missing})


for nm, fn in (("a_mini2_lens", a_mini2_lens), ("b_gimbal_h", b_gimbal_h),
               ("c_invalidation", c_invalidation)):
    t = time.time(); OUT[nm] = fn(); print(f"[{nm}] {time.time()-t:.1f}s", flush=True)

OUT["_meta"] = dict(generator="benchmark/meshdef_attack_verify3.py",
                    generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    src_guard={p: hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()[:16]
                               for p in ("src/drones.py", "src/drone_cad.py")},
                    elapsed_s=round(time.time() - T0, 1))
p = os.path.join(ROOT, "outputs/meshdef_attack_raw3.json")
json.dump(OUT, open(p, "w"), ensure_ascii=False, indent=1)
print("wrote", p)
