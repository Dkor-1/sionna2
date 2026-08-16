#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mesh_certify.py — 메쉬 인증의 **한 줄 진입점** + ⭐골든 봉인(regression seal)
==============================================================================
이 파일이 하는 일은 하나다 — **앞으로 누가 무엇을 바꿔도 자동으로 걸리게** 만든다.

무엇을 봉인하나 (다섯 축)
  ① 형상        — 기체 10대의 메쉬 지문(정점·삼각형·그룹별 해시) + 부품 census
  ② 치수        — 기체마다 잣대 49종의 실측값(mm). 「무엇이 얼마나」 를 말할 수 있는 유일한 축
  ③ 잣대·예산   — 검사기 7모듈의 예산표. **예산을 몰래 늘리면 걸린다**(검사는 통과시키면서)
  ④ 바깥 참값   — mesh_dimref.REFS 77행. **참값을 우리 메쉬에 맞춰 고치면 걸린다**
  ⑤ 문(door)   — 메쉬가 밖으로 나가는 자리(파일 쓰기) 전수 + 인메모리 소비자 census.
                  **새 문이 생기면 걸린다**(게이트를 안 지나는 새 경로)
  ⑥ 인증서      — 다른 라운드가 만든 인증서 6종의 파일 해시·지문. 조용히 바뀌면 걸린다

⚠ 봉인은 «옳음» 의 증명이 아니다 — **«안 바뀜» 의 증명**이다. 옳음은 인증서 4종과
  적대 대조 6스위트가 맡는다. 이 파일은 그것들이 «아직 그 메쉬에 대한 것인가» 를 지킨다.

실행 (전부 CPU only · GPU 미사용 · git 미접촉)
  cd sionna && PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
      benchmark/mesh_certify.py                 # 봉인 대조(기본).  ~30 초
  ... benchmark/mesh_certify.py --full          # 지도·검사·대조·매트릭스·봉인 전부. ~4 분
  ... benchmark/mesh_certify.py --update --reason "짐벌 폭 공식 CAD 로 정정(2층 수리)"
  ... benchmark/mesh_certify.py --gates         # 문 배선 감사만
  ... benchmark/mesh_certify.py --how           # 골든 갱신 절차
  ... benchmark/mesh_certify.py --list          # 단계 목록 + 실측 소요시간

나가는 값(exit code)
  0 = 골든과 완전히 같다        1 = 노랑만(코드·인증서 파일이 바뀌었고 형상은 그대로)
  2 = 빨강/주황(형상·예산·참값·문이 바뀌었다 → 사람이 판단하고 재봉인해야 한다)
  3 = 골든 파일이 없다 / 내부 오류
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures as _fut
import datetime as _dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time

#  ⛔ 이 라운드 규약 — GPU 를 절대 안 쓴다. 스레드도 과하게 안 쓴다(공용 기계).
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

GOLDEN_PATH = os.path.join(ROOT, "outputs", "mesh_golden_0816.json")

#  ── 봉인 대상 ────────────────────────────────────────────────────────────── #
#  ⑶ 잣대·예산을 담고 있는 모듈. 이름이 예산꼴이면 **자동으로** 딸려 들어간다
#     (새 예산이 생겨도 사람이 목록을 고칠 필요가 없다 = 봉인이 스스로 넓어진다).
BUDGET_MODULES = ("mesh_check", "mesh_topo_check", "mesh_placement",
                  "mesh_symmetry", "mesh_dimref", "material_provenance", "mesh_buried")
_BUDGETISH = re.compile(r"(BUDGET|TOL|_PCT|MARGIN|_MIN_|_MAX_|MIN_|MAX_|_EPS|EPS_|SEED"
                        r"|_DIV|_MM$|_M$|_DEG|RANK|CAP|COVERAGE|NPX|SAMPLE|GROUPS|CASES)")
#  이름 규칙에 안 걸리지만 반드시 봉인해야 하는 잣대들(손으로 못박는다)
_BUDGET_EXTRA = {
    "mesh_topo_check": ("FC_DEFAULT_HZ", "FACET_EDGE_DIV", "SAGITTA_DIV", "WELD_TOL_M"),
    "mesh_dimref": ("K_COVERAGE", "REF_CLASS", "PARTS", "GRADE_DEFS"),
    "material_provenance": ("BANDS", "MODEL_KEY_CLASS", "SKIN_DEPTH_MARGIN"),
    "mesh_placement": ("DEPTH_SAMPLE_MAX",),
    "mesh_symmetry": ("PROJ_NPX",),
}

#  ⑴ 형상을 만드는 상수표. 여기 값이 바뀌면 형상 지문도 반드시 바뀌어야 한다
#    (안 바뀌면 그 상수는 죽은 상수라는 뜻 — 그것도 알아낼 값어치가 있다).
SHAPE_CONST_MODULES = {
    "drone_cad": None,      # None = 이름 규칙으로 전수(대문자 + 지정 밑줄표)
    "drones": ("DRONE_GROUP_MAT", "OPEN_MOTOR_BASE_M", "MATERIAL_COLOR"),
}
_SHAPE_UNDERSCORE_OK = ("_SHELL_SHAPE", "_SHELL_DEFAULT", "_ARM_SECTION", "_ARM_WIDTH")

#  ⑹ 다른 라운드가 만든 인증서 — 파일 해시 + 안에 박힌 지문을 같이 데려온다
CERTS = {
    "map":        ("outputs/mesh_cert_map_0816.json", None),
    "topology":   ("outputs/mesh_cert_topology_discretization_0816.json",
                   ("regression_seal", "per_airframe")),
    "dimension":  ("outputs/mesh_cert_dimension_external_0816.json",
                   ("seal", "mesh_fingerprints")),
    "placement":  ("outputs/mesh_cert_placement_overlap_0816.json", ("seal", "per_drone")),
    "symmetry":   ("outputs/mesh_cert_symmetry_derived_0816.json",
                   ("regression_seal", "mesh_fingerprints")),
    "material":   ("outputs/mesh_cert_material_provenance_0816.json",
                   ("seal", "fingerprints")),
    "matrix":     ("outputs/mesh_cert_matrix_0816.json", ("seal", "per_airframe")),
}

#  코드 지문 — 형상·검사를 만드는 파일들(내용이 바뀌면 값이 바뀐다)
CODE_FILES = ("src/drones.py", "src/drone_cad.py", "src/cadkit.py", "src/geom.py",
              "src/mesh_check.py", "src/mesh_topo_check.py", "src/mesh_dimref.py",
              "src/mesh_placement.py", "src/mesh_symmetry.py",
              "src/material_provenance.py", "src/mesh_buried.py",
              "src/articulated_fast.py", "benchmark/mesh_certify.py",
              #  ⭐적대 대조 스위트도 봉인한다 — «검사가 잡는다» 의 증명을 담은 코드라
              #    이것이 조용히 무뎌지면 인증서 전체가 헛것이 된다.
              "benchmark/adv_mesh_check_faults.py", "benchmark/adv_mesh_topo_faults.py",
              "benchmark/adv_mesh_dimref_faults.py", "benchmark/adv_mesh_symmetry_faults.py",
              "benchmark/adv_mesh_placement_0816.py",
              "benchmark/adv_material_provenance_faults.py",
              "benchmark/adv_mesh_certify_faults.py")

#  ⑸ 문 — 메쉬(또는 메쉬에서 나온 파일)가 프로세스 밖으로 나가는 호출.
WRITER_ATTRS = {"write_obj", "write_obj_per_group", "export", "export_stl",
                "write_ply", "write_stl", "save_mesh"}
#  인메모리로 형상을 만들어 쓰는 자리(문을 안 지나는 경로) — 세기만 한다
BUILDER_FUNCS = {"build_drone", "pose_articulated", "build_frame", "build_propeller",
                 "build_frame_cad", "build_propeller_cad"}


# =========================================================================== #
#  0. 잔손
# =========================================================================== #
def _kst() -> str:
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")


def _sha16(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def _sha_json(o) -> str:
    return _sha16(json.dumps(o, ensure_ascii=False, sort_keys=True, default=str).encode())


def _file_sha16(path: str) -> str | None:
    try:
        with open(path, "rb") as fh:
            return _sha16(fh.read())
    except OSError:
        return None


def _jsonify(o):
    """tuple 키·numpy 값을 JSON 이 삼킬 수 있게. tuple 키는 'a|b' 로 편다."""
    import numpy as np
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            kk = "|".join(map(str, k)) if isinstance(k, tuple) else str(k)
            out[kk] = _jsonify(v)
        return out
    if isinstance(o, (list, tuple)):
        return [_jsonify(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 12)
    if isinstance(o, (np.integer, int)) and not isinstance(o, bool):
        return int(o)
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _jsonify(o.tolist())
    if o is None or isinstance(o, str):
        return o
    return str(o)


def _is_jsonable(v) -> bool:
    try:
        json.dumps(_jsonify(v))
        return True
    except (TypeError, ValueError):
        return False


# =========================================================================== #
#  1. 기체 하나의 스냅샷 (형상 · 치수 · 디스크 자산)
# =========================================================================== #
def _obj_body_sha_expected(V, F, G, group: str) -> tuple[str, int, int]:
    """`geom.Mesh.write_obj` 가 **지금 메쉬로 쓴다면** 나올 본문의 지문.
    (주석줄은 뺀다 — 파일 머리말은 형상이 아니다.)"""
    sel = [i for i in range(len(F)) if G[i] == group]
    used, remap, lines = [], {}, []
    for fi in sel:
        for vi in F[fi]:
            vi = int(vi)
            if vi not in remap:
                remap[vi] = len(used)
                used.append(vi)
    for vi in used:
        x, y, z = V[vi]
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
    for fi in sel:
        a, b, c = (int(x) for x in F[fi])
        lines.append(f"f {remap[a]+1} {remap[b]+1} {remap[c]+1}")
    return _sha16("\n".join(lines).encode()), len(used), len(sel)


def _obj_body_sha_file(path: str) -> tuple[str, int, int] | None:
    """디스크의 OBJ 를 같은 규칙으로 지문화(주석·빈줄 제외)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = [ln.strip() for ln in fh
                     if ln.startswith("v ") or ln.startswith("f ")]
    except OSError:
        return None
    nv = sum(1 for ln in lines if ln[0] == "v")
    nf = sum(1 for ln in lines if ln[0] == "f")
    return _sha16("\n".join(lines).encode()), nv, nf


def snapshot_one(key: str) -> dict:
    """기체 하나 — 빌드 + 지문 + 그룹 census + 잣대 49종 + 디스크 자산 대조. ~3 초."""
    import numpy as np
    import drones
    import mesh_dimref as MD
    import mesh_placement as MP
    import mesh_topo_check as MT

    t0 = time.time()
    spec = drones.DRONES[key]
    mesh = drones.build_drone(spec)
    V = np.asarray(mesh.v, float)                       # [m]
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray([str(x) for x in mesh.g])
    Vmm = V * 1000.0
    t_build = time.time() - t0

    # ---- 전체 지문 -------------------------------------------------------- #
    #  sha.mesh 는 **치수·대칭 인증서와 같은 함수**(mesh_dimref.mesh_fingerprint)로 만든다.
    #  같은 수를 써야 인증서와 골든을 직접 견줄 수 있다.
    sha = dict(
        mesh=MD.mesh_fingerprint(mesh),
        verts=_sha16(V.round(9).tobytes()),
        faces=_sha16(F.tobytes()),
        labels=_sha16("|".join(G.tolist()).encode()),
        #  배치 인증서는 sha1 을 쓴다 — 같은 수를 들고 있어야 인증서와 **직접** 견줄 수 있다
        placement_sha1=MP.fingerprint(mesh),
    )

    def _tri_area_mm2(Vm, Ff):
        a, b, c = Vm[Ff[:, 0]], Vm[Ff[:, 1]], Vm[Ff[:, 2]]
        return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)

    A_all = _tri_area_mm2(Vmm, F)
    lo, hi = Vmm.min(0), Vmm.max(0)

    # ---- 그룹별 census ---------------------------------------------------- #
    groups = {}
    for g in sorted(set(G.tolist())):
        Fg = F[G == g]
        Vw, Fw, n_merged = MT.weld(V, Fg)
        n_parts, _lab = MT.face_components(Fw, len(Vw))
        ec = MT.edge_census(Fw, len(Vw))
        A = _tri_area_mm2(Vmm, Fg)
        P = Vmm[Fg].reshape(-1, 3)
        cen = (P.reshape(-1, 3, 3).mean(1) * A[:, None]).sum(0) / max(A.sum(), 1e-30)
        groups[g] = dict(
            n_faces=int(len(Fg)),
            n_verts_used=int(len(np.unique(Fg))),
            n_parts=int(n_parts),
            n_welded=int(n_merged),
            boundary_edges=int(ec["n_boundary"]),
            nonmanifold_edges=int(ec["n_nonmanifold"]),
            flipped_edges=int(ec["n_flipped"]),
            area_mm2=round(float(A.sum()), 6),
            volume_mm3=round(float(MT.signed_volume_mm3(Vw, Fw)), 6),
            bbox_mm=[round(float(x), 6) for x in
                     list(P.min(0)) + list(P.max(0))],
            centroid_mm=[round(float(x), 6) for x in cen],
            sha=_sha16(Vmm[Fg].round(6).tobytes()),
        )

    # ---- 치수 49종(mesh_dimref 의 자) ------------------------------------- #
    rl = MD.ruler(spec, mesh)
    dims, dim_err = {}, {}
    for name, fn in MD._MEASURE.items():
        try:
            v = float(fn(rl))
            dims[name] = None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
        except Exception as e:                                        # noqa: BLE001
            dims[name] = None
            dim_err[name] = f"{type(e).__name__}: {e}"[:120]

    # ---- 선언값(DroneSpec) ------------------------------------------------ #
    import dataclasses
    declared = {f.name: _jsonify(getattr(spec, f.name))
                for f in dataclasses.fields(spec)
                if _is_jsonable(getattr(spec, f.name))}

    # ---- ⭐디스크 자산(assets/meshes/drones/<key>) ↔ 지금 빌더 출력 -------- #
    adir = os.path.join(ROOT, "assets", "meshes", "drones", key)
    assets = dict(dir=os.path.relpath(adir, ROOT), exists=os.path.isdir(adir), files={},
                  n_match=0, n_stale=0, n_missing=0, n_orphan=0)
    if assets["exists"]:
        on_disk = {f for f in os.listdir(adir) if f.endswith(".obj")}
        for g in groups:
            fn = f"{key}__{g}.obj"
            p = os.path.join(adir, fn)
            want, wv, wf = _obj_body_sha_expected(V, F, G, g)
            got = _obj_body_sha_file(p)
            on_disk.discard(fn)
            if got is None:
                assets["files"][fn] = dict(state="없음", want_sha=want,
                                           want_v=wv, want_f=wf)
                assets["n_missing"] += 1
                continue
            same = got[0] == want
            assets["files"][fn] = dict(
                state="일치" if same else "낡음", want_sha=want, disk_sha=got[0],
                want_v=wv, disk_v=got[1], want_f=wf, disk_f=got[2],
                mtime=_dt.datetime.fromtimestamp(os.path.getmtime(p),
                                             _dt.timezone.utc).strftime("%Y-%m-%d"))
            assets["n_match" if same else "n_stale"] += 1
        for fn in sorted(on_disk):
            assets["files"][fn] = dict(state="빌더에 없는 파일")
            assets["n_orphan"] += 1

    return dict(
        key=key, n_verts=int(len(V)), n_faces=int(len(F)), n_groups=len(groups),
        sha=sha,
        bbox_mm=[round(float(x), 6) for x in list(lo) + list(hi)],
        span_mm=[round(float(hi[i] - lo[i]), 6) for i in range(3)],
        area_mm2=round(float(A_all.sum()), 6),
        volume_mm3=round(float(MT.signed_volume_mm3(V, F)), 6),
        groups=groups, dims_mm=dims, dim_errors=dim_err,
        declared=declared, disk_assets=assets,
        _sec=round(time.time() - t0, 2), _sec_build=round(t_build, 2),
    )


def _worker(key):                          # ProcessPoolExecutor 용(모듈 최상위여야 한다)
    try:
        return key, snapshot_one(key), None
    except Exception:                                                 # noqa: BLE001
        import traceback
        return key, None, traceback.format_exc()[-1500:]


def snapshot_fleet(keys, jobs: int = 5, verbose: bool = True) -> dict:
    out, t0 = {}, time.time()
    if jobs <= 1:
        for k in keys:
            k, snap, err = _worker(k)
            out[k] = snap if snap is not None else {"_error": err}
            if verbose:
                print(f"   {k:12s} {out[k].get('_sec', 0):5.1f} s  "
                      f"면 {out[k].get('n_faces', 0):6d}", flush=True)
    else:
        with _fut.ProcessPoolExecutor(max_workers=jobs) as ex:
            for k, snap, err in ex.map(_worker, list(keys)):
                out[k] = snap if snap is not None else {"_error": err}
                if verbose:
                    print(f"   {k:12s} {out[k].get('_sec', 0):5.1f} s  "
                          f"면 {out[k].get('n_faces', 0):6d}", flush=True)
    if verbose:
        print(f"   → 기체 {len(out)}대 {time.time()-t0:.1f} s (병렬 {jobs})", flush=True)
    return out


# =========================================================================== #
#  2. 잣대·예산 · 바깥 참값 · 형상 상수
# =========================================================================== #
def snapshot_budgets() -> dict:
    """검사기 모듈의 **예산·잣대**를 값째로 뜬다. 예산을 늘리면 여기서 걸린다."""
    import importlib
    out = {}
    for mod_name in BUDGET_MODULES:
        mod = importlib.import_module(mod_name)
        vals, extra = {}, _BUDGET_EXTRA.get(mod_name, ())
        for name, v in vars(mod).items():
            if name.startswith("_") or not name.isupper():
                continue
            if not (_BUDGETISH.search(name) or name in extra):
                continue
            if callable(v) or not _is_jsonable(v):
                continue
            vals[name] = _jsonify(v)
        out[mod_name] = dict(values=vals, n=len(vals), sha=_sha_json(vals))
    return out


def snapshot_refs() -> dict:
    """⭐바깥 참값 표(mesh_dimref.REFS) — 참값을 우리 메쉬에 맞춰 고치면 걸린다."""
    import mesh_dimref as MD
    rows = {}
    for r in MD.REFS:
        rows[r.rid] = dict(key=r.key, part=r.part, quantity=r.quantity, measure=r.measure,
                           ref_mm=r.ref_mm, ref_class=r.ref_class, grade=r.grade,
                           circularity=r.circularity, source_file=r.source_file,
                           u_def_mm=r.u_def_mm, ref_band_pct=r.ref_band_pct)
    return dict(n_rows=len(rows), rows=rows, sha=_sha_json(rows),
                measures=sorted(MD._MEASURE), n_measures=len(MD._MEASURE))


def snapshot_shape_consts() -> dict:
    """형상을 만드는 상수표(값째로). 이것이 바뀌면 형상 지문도 바뀌어야 한다."""
    import importlib
    out = {}
    for mod_name, only in SHAPE_CONST_MODULES.items():
        mod = importlib.import_module(mod_name)
        vals = {}
        for name, v in vars(mod).items():
            take = (name in only) if only else (
                (name.isupper() and not name.startswith("_")) or name in _SHAPE_UNDERSCORE_OK)
            if not take or callable(v) or not _is_jsonable(v):
                continue
            vals[name] = _jsonify(v)
        out[mod_name] = dict(values=vals, n=len(vals), sha=_sha_json(vals))
    return out


# =========================================================================== #
#  3. 문(door) 감사 — 메쉬가 밖으로 나가는 자리
# =========================================================================== #
#  ⭐ 문마다 «게이트가 걸려 있나» 를 손으로 판정해 여기 못박는다. 스캔이 이 원장에 없는
#    문을 새로 찾으면 **실패**한다(= 새 경로가 조용히 생기는 것을 막는다).
DOOR_VERDICT = {
    # (파일, 함수/속성, 코드줄 앞부분) → 판정
    "src/drones.py::write_obj_per_group": dict(
        cls="정본 자산", gated=True,
        why="`python src/drones.py` 의 __main__ 에 mesh_check.assert_ok() 가 걸려 있다 "
            "(MESH_GATE=off 로만 끌 수 있고, 끄면 경고를 찍는다)"),
    "src/scene_build.py::write_obj_per_group::_scene": dict(
        cls="장면 임시", gated=False,
        why="drone_parts() 가 렌더/RT 용 OBJ 를 mesh_dir/_scene 에 쓴다. 게이트 없음 — "
            "여기로 나가는 것은 **지금 빌더 출력**이라 형상이 나빠져도 그대로 나간다"),
    "src/scene_build.py::write_obj_per_group::chamber": dict(
        cls="드론 아님", gated=False, why="차폐시설 메쉬 — 드론 형상이 아니다"),
    "src/scene_build.py::write_obj": dict(
        cls="드론 아님", gated=False, why="스튜디오 바닥판 사각형 한 장 — 드론 형상이 아니다"),
    "src/gazebo_export.py::export": dict(
        cls="다른 빌더", gated=False,
        why="⭐Gazebo STL 은 build_frame_cad(drone_cad) 에서 나온다 — geom.Mesh 가 아니라서 "
            "저장소의 어떤 메쉬 검사도 이 산출물을 안 본다(선언된 사각지대)"),
    "src/viz_report1.py::write_obj_per_group": dict(
        cls="장면 임시", gated=False, why="리포트1 애니메이션용 임시 OBJ"),
    "src/chamber.py::write_obj_per_group": dict(
        cls="드론 아님", gated=False, why="차폐시설 메쉬 — 드론 형상이 아니다"),
    "src/geom.py::write_obj": dict(
        cls="문 자체", gated=False, why="write_obj_per_group 이 부르는 하부 구현(문의 몸통)"),
    "src/compare_phantom_scan.py::export": dict(
        cls="비교 산출", gated=False, why="실물 스캔 대조용 PLY — 시뮬에 안 들어간다"),
}
#  benchmark/ 쪽 문은 «실험마다 장면 OBJ 를 쓰는» 같은 종류라 파일별로 못박지 않고
#  한 부류로 묶는다. 새 파일이 생기면 «새 문» 으로 신고된다.
DOOR_BENCH_CLASS = dict(cls="실험 장면 임시", gated=False,
                        why="실험 스크립트가 Sionna/Mitsuba 에 먹일 장면 OBJ 를 그때그때 쓴다 "
                            "— 게이트 없음. 나가는 형상은 지금 빌더 출력과 같다")


_ASSET_LINE = re.compile(r"meshes[^\n]{0,24}drones")


def scan_asset_readers() -> dict:
    """**들어오는 쪽** — 디스크 정본 자산(assets/meshes/drones)을 참조하는 자리.
    나가는 문만 세면 반쪽이다. 낡은 OBJ 를 **읽어 쓰는** 자리도 같이 봉인한다."""
    rows = []
    for sub in ("src", "benchmark"):
        d = os.path.join(ROOT, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py") or fn == "mesh_certify.py":
                continue
            try:
                lines = open(os.path.join(d, fn), encoding="utf-8",
                             errors="replace").read().splitlines()
            except OSError:
                continue
            for i, ln in enumerate(lines, 1):
                if not _ASSET_LINE.search(ln):
                    continue
                code = ln.strip()[:120]
                #  «정본 파일 자체를 읽는가»(<key>__<group>.obj) ↔ «디렉터리 경로만 넘기는가»
                direct = bool(re.search(r"__[a-z_]*\.obj|\*__|__\{", code))
                rows.append(dict(file=f"{sub}/{fn}", line=i, code=code,
                                 kind="정본 OBJ 직접 읽기" if direct else "경로 전달·정의"))
    direct = [r for r in rows if r["kind"] == "정본 OBJ 직접 읽기"]
    return dict(
        n=len(rows), n_direct=len(direct), rows=rows,
        ids=sorted(f"{r['file']}::{r['code']}" for r in rows),
        note_ko=[
            "렌더·RT 경로(render_rt · radar_scene · benchmark/channel)는 자산 **디렉터리**만 "
            "넘기고 scene_build.drone_parts() 가 `<key>/_scene/` 에 **그때 새로 쓴다** — "
            "즉 그 경로가 쓰는 형상은 낡지 않는다.",
            "위험한 것은 `<key>__<group>.obj` 를 **직접 읽는** 자리다 — 그 파일은 "
            "`python src/drones.py` 를 다시 돌려야만 갱신된다.",
        ])


def scan_doors() -> dict:
    """src/ · benchmark/ 를 AST 로 훑어 **메쉬가 파일로 나가는 호출**을 전수로 찾는다."""
    doors, consumers = [], []
    for sub in ("src", "benchmark"):
        d = os.path.join(ROOT, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(d, fn)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
                tree = ast.parse(text)
            except (OSError, SyntaxError):
                continue
            lines = text.splitlines()
            n_build = 0
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                if isinstance(f, ast.Attribute) and f.attr in WRITER_ATTRS:
                    code = lines[node.lineno - 1].strip()[:120]
                    doors.append(dict(file=f"{sub}/{fn}", attr=f.attr, line=node.lineno,
                                      code=code))
                name = (f.attr if isinstance(f, ast.Attribute)
                        else (f.id if isinstance(f, ast.Name) else None))
                if name in BUILDER_FUNCS:
                    n_build += 1
            if n_build:
                consumers.append(dict(file=f"{sub}/{fn}", n_calls=n_build))
    for h in doors:
        k = f"{h['file']}::{h['attr']}"
        code = re.sub(r"\s+", " ", h["code"])
        #  같은 파일·같은 호출이라도 **줄마다 뜻이 다를 수 있다**(차폐시설 ↔ 드론).
        #  그래서 «file::attr::코드조각» 키를 먼저 보고, 없으면 «file::attr» 로 떨어진다.
        v = None
        for kk, vv in DOOR_VERDICT.items():
            if kk.startswith(k + "::") and kk.split("::", 2)[2] in code:
                v = vv
                break
        v = v or DOOR_VERDICT.get(k) or (DOOR_BENCH_CLASS
                                         if h["file"].startswith("benchmark/") else None)
        h["verdict"] = v or dict(cls="⚠판정 없음", gated=False,
                                 why="원장에 없는 문 — 사람이 판정하고 재봉인해야 한다")
        h["id"] = f"{k}::{code}"
    n_gate = sum(1 for h in doors if h["verdict"]["gated"])
    readers = scan_asset_readers()
    return dict(
        asset_readers=readers,
        n_doors=len(doors), n_gated=n_gate, n_ungated=len(doors) - n_gate,
        doors=sorted(doors, key=lambda h: h["id"]),
        door_ids=sorted(h["id"] for h in doors),
        consumers=sorted(consumers, key=lambda c: c["file"]),
        n_consumer_files=len(consumers),
        n_consumer_calls=sum(c["n_calls"] for c in consumers),
        gate_wiring_ko=[
            "⭐게이트가 실제로 걸린 문은 **하나**다 — `python src/drones.py`(정본 OBJ 내보내기)."
            " 거기서 mesh_check.assert_ok() 가 돌고, 실패하면 파일이 안 나간다.",
            "나머지 문(장면 임시·실험 장면·Gazebo)은 게이트를 안 지난다.",
            "⭐⭐인메모리 경로(build_drone 을 직접 부르는 RCS·SBR·마이크로도플러·렌더)는 "
            "애초에 **문이 아니다** — 파일을 안 쓰고 배열을 그대로 쓴다. 그래서 어떤 게이트도 "
            "그 경로를 못 막는다. 지금 저장소에서 그런 파일이 "
            "%d 개(호출 %d 곳)다." % (len(consumers), sum(c["n_calls"] for c in consumers)),
            "막으려면 import 시점 검사를 걸어야 하는데 전 기종 검사가 ~35 초라 안 건다 "
            "(src/drones.py 주석의 선언과 같은 이유). 대신 이 파일(mesh_certify)을 "
            "라운드 끝에 돌리는 것이 규율이다.",
        ],
    )


# =========================================================================== #
#  4. 인증서 · 코드 지문
# =========================================================================== #
#  판정이 «나쁜 쪽» 인가 — 매트릭스가 쓰는 낱말 그대로
_BAD_VERDICT = ("어긋남", "실패", "위반", "결함", "사각지대")


def snapshot_matrix_verdicts() -> dict:
    """⭐인증 매트릭스 450칸의 **판정과 값**. 검사기가 조용히 무뎌지면 여기서 걸린다
    (형상 지문은 그대로인데 판정만 뒤집히는 경우가 그렇다)."""
    p = os.path.join(ROOT, CERTS["matrix"][0])
    try:
        j = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return dict(missing=True, cells={}, n_checks=0)
    cells = {}
    for cid, row in (j.get("matrix") or {}).items():
        cell = {}
        for k, c in (row or {}).items():
            if not isinstance(c, dict):
                continue
            v = c.get("value")
            cell[k] = dict(v=c.get("verdict"),
                           x=round(v, 9) if isinstance(v, float) else _jsonify(v),
                           b=_jsonify(c.get("budget")))
        cells[cid] = cell
    n_cell = sum(len(v) for v in cells.values())
    return dict(n_checks=len(cells), n_cells=n_cell, cells=cells, sha=_sha_json(cells),
                source=CERTS["matrix"][0])


def snapshot_certs() -> dict:
    out = {}
    for name, (rel, path) in CERTS.items():
        p = os.path.join(ROOT, rel)
        rec = dict(path=rel, exists=os.path.exists(p), file_sha=_file_sha16(p))
        if rec["exists"]:
            try:
                j = json.load(open(p, encoding="utf-8"))
                rec["generated_kst"] = (j.get("_meta") or {}).get("generated_kst")
                if path:
                    node = j
                    for step in path:
                        node = (node or {}).get(step) if isinstance(node, dict) else None
                    rec["fingerprints"] = _jsonify(node) if node is not None else None
            except (OSError, ValueError) as e:
                rec["read_error"] = str(e)[:120]
        out[name] = rec
    return out


def snapshot_code() -> dict:
    return {f: _file_sha16(os.path.join(ROOT, f)) for f in CODE_FILES}


# =========================================================================== #
#  5. 골든 만들기 / 견주기
# =========================================================================== #
UPDATE_PROCEDURE_KO = [
    "① **왜 바뀌는지 한 줄로 적을 수 있어야 한다.** 못 적으면 그 변경은 사고다 — 먼저 원인을 찾는다.",
    "② 형상을 고친 라운드가 **인증서 4종을 재발급**한다: "
    "benchmark/make_mesh_cert_topology_0816.py · mesh_cert_dimension_external_0816.py · "
    "mesh_cert_placement_0816.py · mesh_cert_symmetry_derived_0816.py "
    "(재질을 건드렸으면 mesh_cert_material_provenance_0816.py 도).",
    "③ 적대 대조 6스위트를 다시 돌려 **여전히 잡히는지** 확인한다 "
    "(adv_mesh_check_faults · adv_mesh_topo_faults · adv_mesh_dimref_faults · "
    "adv_mesh_symmetry_faults · adv_mesh_placement_0816 · adv_material_provenance_faults).",
    "④ 매트릭스를 다시 찍는다: mesh_cert_matrix_run_one.py(기체별) → mesh_cert_matrix_fleet.py → "
    "make_mesh_cert_matrix_0816.py.  = `mesh_certify.py --full` 한 줄로 대신할 수 있다.",
    "⑤ 정본 OBJ 자산을 다시 내보낸다: `PYTHONPATH=src python src/drones.py` "
    "(게이트가 여기서 돈다. 이걸 빼먹으면 디스크 자산이 낡아 골든이 «낡음» 으로 신고한다).",
    "⑥ 마지막에 골든을 다시 봉인한다: "
    "`python benchmark/mesh_certify.py --update --reason \"<한 줄 이유>\"`. "
    "이유 없이는 갱신을 거부한다.",
    "⑦ 갱신본은 history 에 **이전 지문과 이유**를 남긴다 — 언제 무엇이 왜 바뀌었는지 "
    "골든 파일 하나만 열면 따라갈 수 있다.",
]

LIMITS_KO = [
    "봉인은 «옳음» 이 아니라 «안 바뀜» 을 증명한다. 처음부터 틀린 형상은 골든이 지켜 준다 — "
    "틀린 채로.",
    "게이트가 실제로 걸린 문은 `python src/drones.py` **하나**다. 장면 임시 OBJ·실험 장면·"
    "Gazebo STL 은 게이트를 안 지난다.",
    "⭐인메모리 경로(build_drone 직접 호출)는 문이 아니라 막을 수 없다. RCS·SBR·마이크로도플러·"
    "렌더는 전부 이 경로다. 이 파일을 라운드 끝에 돌리는 규율이 유일한 방벽이다.",
    "Gazebo STL 은 **다른 빌더**(drone_cad.build_frame_cad)에서 나와 저장소의 메쉬 검사가 "
    "한 번도 본 적 없다.",
    "치수 49종은 mesh_dimref 의 자다 — 그 자가 못 재는 부위(예: 내부 배선·안테나)는 골든에도 없다.",
    "형상 상수 봉인은 **표에 담긴 상수**만 본다. 함수 안에 숫자로 박힌 값(하드코딩)은 "
    "코드 지문(파일 sha)으로만 잡힌다 — «어디가» 바뀌었는지는 못 말한다.",
    "디스크 자산 대조는 assets/meshes/drones/<key>/ 만 본다. _scene/ 같은 파생물은 "
    "매번 새로 쓰이므로 대조 대상이 아니다.",
    "위상 인증서 지문(32자)은 봉인 대조에서 **다시 계산하지 않는다**(기체당 ~12초). "
    "그 축은 `--full` 의 fleet 단계(mesh_topo_check.check_seal)가 맡는다.",
    "매트릭스 판정 축은 **파일에 적힌 판정**을 굳힌 것이다 — 그 판정이 지금도 맞는지는 "
    "`--full` 로 다시 찍어야 안다.",
    "골든은 **한 기계·한 파이썬**에서 재현된다는 전제다. 부동소수 차이가 나는 환경에서는 "
    "지문이 달라질 수 있다(같은 컨테이너에서 독립 빌드 4회 재현 확인).",
]


def build_golden(keys=None, jobs=5, verbose=True) -> dict:
    import drones
    keys = list(keys or drones.DRONES)
    if verbose:
        print("① 형상·치수 스냅샷 …", flush=True)
    fleet = snapshot_fleet(keys, jobs=jobs, verbose=verbose)
    if verbose:
        print("② 예산·참값·형상상수·문·인증서 …", flush=True)
    g = dict(
        _meta=dict(
            title="메쉬 골든 봉인 — 기체 10 × (형상·치수·예산·참값·문·인증서)",
            generated_kst=_kst(),
            role_ko="⭐앞으로 누가 무엇을 바꿔도 자동으로 걸리게 하는 기준선. "
                    "«무엇이 얼마나» 를 사람이 읽는 형식으로 뱉는 것이 목적이다.",
            policy_ko="⛔GPU 미사용(CPU only) · ⛔git 미접촉 · ⛔형상 상수 무변경 — "
                      "이 라운드가 만든 것은 검사·대조·봉인·인증서뿐이다.",
            entry_point="PYTHONPATH=src:benchmark python benchmark/mesh_certify.py",
            python=sys.executable,
            n_airframes=len(keys),
        ),
        airframes=fleet,
        budgets=snapshot_budgets(),
        references=snapshot_refs(),
        shape_constants=snapshot_shape_consts(),
        doors=scan_doors(),
        matrix_verdicts=snapshot_matrix_verdicts(),
        certificates=snapshot_certs(),
        code_fingerprints=snapshot_code(),
        update_procedure_ko=UPDATE_PROCEDURE_KO,
        limits_ko=LIMITS_KO,
        history=[],
    )
    g["_meta"]["seal_all"] = _sha_json({k: v.get("sha") for k, v in fleet.items()})
    return g


#  ── 견주기 ──────────────────────────────────────────────────────────────── #
RED, ORANGE, YELLOW = "🔴", "🟠", "🟡"


def _deep_diff(a, b, path="", out=None, cap=400):
    """잎사귀 단위 차이 (경로, 옛값, 새값). dict/list 를 재귀로 판다."""
    out = [] if out is None else out
    if len(out) >= cap:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _deep_diff(a.get(k, "<없음>"), b.get(k, "<없음>"), f"{path}.{k}" if path else str(k), out, cap)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, f"길이 {len(a)}", f"길이 {len(b)}"))
        for i in range(min(len(a), len(b))):
            _deep_diff(a[i], b[i], f"{path}[{i}]", out, cap)
    elif a != b:
        out.append((path, a, b))
    return out


def _num_delta(o, n):
    if isinstance(o, (int, float)) and isinstance(n, (int, float)) and not isinstance(o, bool):
        d = n - o
        pct = (100.0 * d / abs(o)) if o else float("inf")
        return d, pct
    return None, None


def diff_golden(old: dict, new: dict) -> list[dict]:
    """골든 ↔ 지금. 사람이 읽는 findings 목록(심각도 · 무엇이 · 얼마나)."""
    F = []

    def add(sev, kind, what, lines=(), key=None):
        F.append(dict(sev=sev, kind=kind, what=what, key=key, lines=list(lines)))

    # ---------- ① 형상 ----------------------------------------------------- #
    ao, an = old.get("airframes", {}), new.get("airframes", {})
    for k in sorted(set(ao) | set(an)):
        o, n = ao.get(k), an.get(k)
        if o is None:
            add(RED, "형상", f"{k} — 골든에 없던 기체가 나타났다", key=k)
            continue
        if n is None:
            add(RED, "형상", f"{k} — 기체가 사라졌다(레지스트리에서 빠짐)", key=k)
            continue
        if n.get("_error"):
            add(RED, "형상", f"{k} — 스냅샷이 죽었다", [n["_error"][-300:]], key=k)
            continue
        if o["sha"]["mesh"] == n["sha"]["mesh"]:
            continue
        L = []
        same_topo = o["sha"]["faces"] == n["sha"]["faces"]
        L.append(f"지문 {o['sha']['mesh']} → {n['sha']['mesh']}"
                 + ("  (삼각형 연결은 그대로 · 정점 좌표만 움직였다)" if same_topo else ""))
        if o["n_faces"] != n["n_faces"] or o["n_verts"] != n["n_verts"]:
            L.append(f"삼각형 {o['n_faces']} → {n['n_faces']} ({n['n_faces']-o['n_faces']:+d}) · "
                     f"정점 {o['n_verts']} → {n['n_verts']} ({n['n_verts']-o['n_verts']:+d})")
        for i, ax in enumerate("xyz"):
            d0 = n["bbox_mm"][i] - o["bbox_mm"][i]
            d1 = n["bbox_mm"][i + 3] - o["bbox_mm"][i + 3]
            if abs(d0) > 1e-6 or abs(d1) > 1e-6:
                L.append(f"외형 {ax}: [{o['bbox_mm'][i]:.3f}, {o['bbox_mm'][i+3]:.3f}] → "
                         f"[{n['bbox_mm'][i]:.3f}, {n['bbox_mm'][i+3]:.3f}] mm "
                         f"(아래끝 {d0:+.3f} · 위끝 {d1:+.3f})")
        dv, pv = _num_delta(o["volume_mm3"], n["volume_mm3"])
        if dv and abs(dv) > 1e-6:
            L.append(f"부피 {o['volume_mm3']:.1f} → {n['volume_mm3']:.1f} mm³ ({pv:+.2f} %)")
        # 그룹별
        for g in sorted(set(o["groups"]) | set(n["groups"])):
            go, gn = o["groups"].get(g), n["groups"].get(g)
            if go is None:
                L.append(f"  그룹 {g}: **새 그룹**(면 {gn['n_faces']})")
                continue
            if gn is None:
                L.append(f"  그룹 {g}: **사라짐**(면 {go['n_faces']})")
                continue
            if go["sha"] == gn["sha"]:
                continue
            bits = [f"면 {go['n_faces']}→{gn['n_faces']} ({gn['n_faces']-go['n_faces']:+d})"]
            if go["n_parts"] != gn["n_parts"]:
                bits.append(f"부품 {go['n_parts']}→{gn['n_parts']}")
            if go["boundary_edges"] != gn["boundary_edges"]:
                bits.append(f"⚠경계모서리 {go['boundary_edges']}→{gn['boundary_edges']}")
            if go["nonmanifold_edges"] != gn["nonmanifold_edges"]:
                bits.append(f"⚠비다양체 {go['nonmanifold_edges']}→{gn['nonmanifold_edges']}")
            d, p = _num_delta(go["volume_mm3"], gn["volume_mm3"])
            if d is not None and abs(d) > 1e-6:
                bits.append(f"부피 {p:+.2f} %")
            d, p = _num_delta(go["area_mm2"], gn["area_mm2"])
            if d is not None and abs(d) > 1e-6:
                bits.append(f"면적 {p:+.2f} %")
            for i, ax in enumerate("xyz"):
                dd = [gn["bbox_mm"][i] - go["bbox_mm"][i], gn["bbox_mm"][i+3] - go["bbox_mm"][i+3]]
                if max(abs(x) for x in dd) > 1e-3:
                    bits.append(f"{ax}상자 {dd[0]:+.2f}/{dd[1]:+.2f} mm")
            L.append(f"  그룹 {g}: " + " · ".join(bits))
        # 치수
        rows = []
        for m in sorted(set(o["dims_mm"]) | set(n["dims_mm"])):
            vo, vn = o["dims_mm"].get(m), n["dims_mm"].get(m)
            if vo is None or vn is None:
                if vo != vn:
                    rows.append((float("inf"), f"  치수 {m}: {vo} → {vn}"))
                continue
            d = vn - vo
            if abs(d) > 1e-6:
                pct = 100.0 * d / abs(vo) if vo else float("nan")
                rows.append((abs(d), f"  치수 {m}: {vo:.3f} → {vn:.3f} mm "
                                     f"({d:+.3f} mm, {pct:+.2f} %)"))
        rows.sort(key=lambda r: -r[0])
        L += [r[1] for r in rows[:20]]
        if len(rows) > 20:
            L.append(f"  … 치수 {len(rows)-20}행 더 바뀜")
        add(RED, "형상", f"{k} — 형상이 바뀌었다", L, key=k)

    # ---------- ① -b 디스크 자산 ------------------------------------------- #
    for k in sorted(set(ao) & set(an)):
        o, n = ao[k], an[k]
        if n.get("_error"):
            continue
        so, sn = o.get("disk_assets", {}), n.get("disk_assets", {})
        if [so.get(x) for x in ("n_stale", "n_missing", "n_orphan")] != \
           [sn.get(x) for x in ("n_stale", "n_missing", "n_orphan")]:
            add(ORANGE, "자산", f"{k} — 디스크 OBJ 자산의 상태가 바뀌었다",
                [f"낡음 {so.get('n_stale')}→{sn.get('n_stale')} · "
                 f"없음 {so.get('n_missing')}→{sn.get('n_missing')} · "
                 f"고아 {so.get('n_orphan')}→{sn.get('n_orphan')} "
                 f"(일치 {so.get('n_match')}→{sn.get('n_match')})"], key=k)

    # ---------- ② 예산 ----------------------------------------------------- #
    for mod in sorted(set(old.get("budgets", {})) | set(new.get("budgets", {}))):
        bo = (old.get("budgets", {}).get(mod) or {}).get("values", {})
        bn = (new.get("budgets", {}).get(mod) or {}).get("values", {})
        d = _deep_diff(bo, bn)
        if not d:
            continue
        L = []
        loosened = False
        for path, a, b in d[:40]:
            dd, pct = _num_delta(a, b)
            if dd is not None:
                tag = "완화(느슨해짐)" if dd > 0 else "강화(조여짐)"
                loosened |= dd > 0
                L.append(f"  {path}: {a} → {b}  ({dd:+g}, {tag})")
            else:
                loosened = True
                L.append(f"  {path}: {a} → {b}")
        if len(d) > 40:
            L.append(f"  … {len(d)-40}건 더")
        add(ORANGE if loosened else YELLOW, "예산",
            f"{mod} — 검사 잣대·예산이 바뀌었다 ({len(d)}건)", L)

    # ---------- ③ 바깥 참값 ------------------------------------------------ #
    ro = (old.get("references") or {}).get("rows", {})
    rn = (new.get("references") or {}).get("rows", {})
    d = _deep_diff(ro, rn)
    if d:
        L = [f"  {p}: {a} → {b}" for p, a, b in d[:40]]
        if len(d) > 40:
            L.append(f"  … {len(d)-40}건 더")
        add(ORANGE, "참값", f"바깥 참값 표(REFS)가 바뀌었다 — 행 {len(ro)} → {len(rn)}, "
                            f"잎사귀 {len(d)}건", L)

    # ---------- ④ 형상 상수 ------------------------------------------------ #
    for mod in sorted(set(old.get("shape_constants", {})) | set(new.get("shape_constants", {}))):
        co = (old.get("shape_constants", {}).get(mod) or {}).get("values", {})
        cn = (new.get("shape_constants", {}).get(mod) or {}).get("values", {})
        d = _deep_diff(co, cn)
        if not d:
            continue
        L = [f"  {p}: {a} → {b}" for p, a, b in d[:40]]
        if len(d) > 40:
            L.append(f"  … {len(d)-40}건 더")
        add(ORANGE, "형상상수", f"{mod} — 형상 상수표가 바뀌었다 ({len(d)}건)", L)

    # ---------- ⑤ 문 ------------------------------------------------------- #
    do, dn = old.get("doors", {}), new.get("doors", {})
    so, sn = set(do.get("door_ids", [])), set(dn.get("door_ids", []))
    new_doors = sorted(sn - so)
    gone_doors = sorted(so - sn)
    if new_doors:
        add(RED, "문", f"⭐새 문이 {len(new_doors)}개 생겼다 — 게이트를 안 지나는 새 경로일 수 있다",
            [f"  + {x}" for x in new_doors[:20]])
    if gone_doors:
        add(YELLOW, "문", f"문이 {len(gone_doors)}개 사라졌다",
            [f"  − {x}" for x in gone_doors[:20]])
    unjudged = [h["id"] for h in dn.get("doors", []) if h["verdict"]["cls"] == "⚠판정 없음"]
    if unjudged:
        add(RED, "문", f"판정이 없는 문 {len(unjudged)}개 — 원장에 판정을 적고 재봉인해야 한다",
            [f"  ? {x}" for x in unjudged[:20]])
    ro_ids = set((do.get("asset_readers") or {}).get("ids", []))
    rn_ids = set((dn.get("asset_readers") or {}).get("ids", []))
    if rn_ids - ro_ids:
        add(ORANGE, "자산독자",
            f"디스크 자산을 참조하는 자리가 {len(rn_ids - ro_ids)}곳 늘었다 "
            f"— 낡은 OBJ 를 읽게 되는지 확인해야 한다",
            [f"  + {x}" for x in sorted(rn_ids - ro_ids)[:15]])
    if ro_ids - rn_ids:
        add(YELLOW, "자산독자", f"디스크 자산 참조가 {len(ro_ids - rn_ids)}곳 사라졌다",
            [f"  − {x}" for x in sorted(ro_ids - rn_ids)[:15]])
    if do.get("n_consumer_calls") != dn.get("n_consumer_calls"):
        add(YELLOW, "문",
            f"인메모리 소비자(문이 아닌 경로)가 {do.get('n_consumer_calls')} → "
            f"{dn.get('n_consumer_calls')} 곳으로 바뀌었다",
            ["  (막을 수 없는 경로다 — 늘어난 것 자체는 결함이 아니고, 규율의 대상이다)"])

    # ---------- ⑤-b 매트릭스 450칸의 판정 ---------------------------------- #
    mo = (old.get("matrix_verdicts") or {}).get("cells", {})
    mn = (new.get("matrix_verdicts") or {}).get("cells", {})
    flips, moves, worse = [], [], False
    for cid in sorted(set(mo) | set(mn)):
        ro, rn = mo.get(cid) or {}, mn.get(cid) or {}
        for k in sorted(set(ro) | set(rn)):
            a, b = ro.get(k) or {}, rn.get(k) or {}
            if a == b:
                continue
            if a.get("v") != b.get("v"):
                bad = any(w in str(b.get("v")) for w in _BAD_VERDICT)
                worse |= bad and not any(w in str(a.get("v")) for w in _BAD_VERDICT)
                flips.append(f"  {'⛔' if bad else '  '} {cid} {k}: "
                             f"{a.get('v')} → {b.get('v')}  (값 {a.get('x')} → {b.get('x')})")
            else:
                d, p = _num_delta(a.get("x"), b.get("x"))
                if d is None or abs(d) > 1e-9:
                    moves.append(f"  {cid} {k}: 값 {a.get('x')} → {b.get('x')}"
                                 + (f" ({p:+.2f} %)" if p is not None and abs(p) < 1e9 else ""))
    if flips:
        add(RED if worse else ORANGE, "매트릭스",
            f"인증 매트릭스의 판정이 {len(flips)}칸 뒤집혔다"
            + ("  ⛔통과 → 실패가 있다" if worse else ""), flips[:20])
    if moves:
        add(YELLOW, "매트릭스", f"판정은 같은데 잰 값이 {len(moves)}칸 달라졌다", moves[:15])

    # ---------- ⑥ 인증서 --------------------------------------------------- #
    for name in sorted(set(old.get("certificates", {})) | set(new.get("certificates", {}))):
        co = old.get("certificates", {}).get(name) or {}
        cn = new.get("certificates", {}).get(name) or {}
        if co.get("file_sha") == cn.get("file_sha"):
            continue
        L = [f"  파일 지문 {co.get('file_sha')} → {cn.get('file_sha')} "
             f"(발행 {co.get('generated_kst')} → {cn.get('generated_kst')})"]
        fd = _deep_diff(co.get("fingerprints") or {}, cn.get("fingerprints") or {})
        L += [f"  {p}: {a} → {b}" for p, a, b in fd[:12]]
        add(YELLOW, "인증서", f"인증서 {name} 가 바뀌었다", L)

    # ---------- ⑦ 코드 ----------------------------------------------------- #
    cod, cnd = old.get("code_fingerprints", {}), new.get("code_fingerprints", {})
    ch = [f for f in sorted(set(cod) | set(cnd)) if cod.get(f) != cnd.get(f)]
    if ch:
        shape_same = all(ao.get(k, {}).get("sha", {}).get("mesh")
                         == an.get(k, {}).get("sha", {}).get("mesh") for k in ao)
        add(YELLOW, "코드", f"코드 지문이 {len(ch)}개 파일에서 바뀌었다"
                            + ("  (형상은 그대로 — 주석·검사 쪽 변경으로 보인다)" if shape_same else ""),
            [f"  {f}: {cod.get(f)} → {cnd.get(f)}" for f in ch])

    return F


def check_certs_live(new: dict) -> list[dict]:
    """⭐인증서가 **아직 이 메쉬에 대한 것인가** — 지금 메쉬의 지문과 인증서 안 지문을 견준다.
    (골든과 무관한 검사다. 골든이 낡아도 이건 «지금» 을 본다.)
    ⚠ 위상 인증서 지문은 여기서 못 본다 — 다시 계산하는 데 기체당 ~12 초라 `--full` 의
      fleet 단계(mesh_topo_check.check_seal)가 맡는다."""
    F, certs, af = [], new.get("certificates", {}), new.get("airframes", {})
    live16 = {k: v.get("sha", {}).get("mesh") for k, v in af.items() if not v.get("_error")}
    live40 = {k: v.get("sha", {}).get("placement_sha1") for k, v in af.items()
              if not v.get("_error")}
    plans = [("dimension", "sha256_16", live16), ("symmetry", "sha256_16", live16),
             ("placement", "mesh_sha1", live40)]
    for cname, field, live in plans:
        fp = (certs.get(cname) or {}).get("fingerprints") or {}
        bad, miss = [], []
        for k, want in live.items():
            got = fp.get(k)
            got = got.get(field) if isinstance(got, dict) else got
            if got is None:
                miss.append(k)
            elif got != want:
                bad.append(f"  {k}: 인증서 {got} ↔ 지금 {want}")
        if bad:
            F.append(dict(sev=RED, kind="인증서유효",
                          what=f"인증서 {cname} 는 **다른 메쉬**에 대한 것이다 "
                               f"({len(bad)}/{len(live)} 기체 불일치 → 재발급 필요)",
                          key=None, lines=bad[:12]))
        if miss:
            F.append(dict(sev=YELLOW, kind="인증서유효",
                          what=f"인증서 {cname} 에 지문이 없는 기체 {len(miss)}대",
                          key=None, lines=["  " + ", ".join(miss)]))
    return F


def render_findings(findings, old, new) -> str:
    """사람이 읽는 대조 보고."""
    L = []
    ao, an = old.get("airframes", {}), new.get("airframes", {})
    same = sum(1 for k in an
               if ao.get(k, {}).get("sha", {}).get("mesh") == an[k].get("sha", {}).get("mesh"))
    L.append("=" * 100)
    L.append(f"골든 봉인 대조 — {os.path.relpath(GOLDEN_PATH, ROOT)}  "
             f"(봉인 {old.get('_meta', {}).get('generated_kst')})")
    L.append(f"  지금 {_kst()} · 기체 {len(an)}대 · 형상 동일 {same}/{len(an)}")
    L.append("=" * 100)
    if not findings:
        L.append("✅ 형상·치수·예산·참값·형상상수·문·인증서·코드 — **전부 골든과 같다.**")
    for f in findings:
        L.append(f"\n{f['sev']} [{f['kind']}] {f['what']}")
        for ln in f["lines"]:
            L.append(f"     {ln}")
    #  디스크 자산은 «바뀌지 않아도» 늘 알려 준다(낡은 채로 굳는 것을 막는다)
    stale = {k: v["disk_assets"] for k, v in an.items()
             if not v.get("_error") and v.get("disk_assets", {}).get("exists")
             and (v["disk_assets"]["n_stale"] or v["disk_assets"]["n_missing"])}
    nodir = [k for k, v in an.items()
             if not v.get("_error") and not v.get("disk_assets", {}).get("exists")]
    L.append("\n" + "-" * 100)
    L.append("디스크 정본 자산(assets/meshes/drones/<key>/*.obj) ↔ 지금 빌더 출력")
    if stale:
        for k, s in sorted(stale.items()):
            L.append(f"  ⚠ {k:12s} 일치 {s['n_match']} · 낡음 {s['n_stale']} · 없음 {s['n_missing']}"
                     f" · 고아 {s['n_orphan']}")
    if nodir:
        L.append(f"  ⚠ 내보낸 적 없는 기체: {', '.join(sorted(nodir))}")
    if not stale and not nodir:
        L.append("  ✅ 전 기체 일치")
    if stale or nodir:
        L.append("  → 고치는 법: PYTHONPATH=src python src/drones.py "
                 "(mesh_check.assert_ok 게이트가 여기서 돈다)")
    return "\n".join(L)


def render_gates(doors: dict) -> str:
    L = ["=" * 100, "문(door) 배선 감사 — 메쉬가 밖으로 나가는 자리", "=" * 100,
         f"  문 {doors['n_doors']}개 중 게이트가 걸린 문 {doors['n_gated']}개 · "
         f"안 걸린 문 {doors['n_ungated']}개"]
    by = {}
    for h in doors["doors"]:
        by.setdefault(h["verdict"]["cls"], []).append(h)
    for cls in sorted(by):
        hs = by[cls]
        L.append(f"\n[{cls}]  {len(hs)}곳   게이트 {'있음' if hs[0]['verdict']['gated'] else '없음'}")
        L.append(f"     {hs[0]['verdict']['why']}")
        for h in hs[:12]:
            L.append(f"       {h['file']}:{h['line']}  {h['code'][:80]}")
        if len(hs) > 12:
            L.append(f"       … {len(hs)-12}곳 더")
    L.append("\n" + "-" * 100)
    for s in doors["gate_wiring_ko"]:
        L.append("  · " + s)
    return "\n".join(L)


# =========================================================================== #
#  6. 단계 실행기 — 지도 · 검사 · 대조 · 매트릭스 · 봉인
# =========================================================================== #
#  (초) 는 2026-08-16 이 기계(192코어, 다른 작업과 공유)에서 잰 실측이다.
#  실측 = 2026-08-16 · 192코어 공용기(다른 작업과 공유) · `--jobs 6` 에서 잰 값이다.
STAGES = [
    ("map",      "범주 지도 ↔ 매트릭스 덮임 확인", 0.1),
    ("raw",      "기체별 전 검사 원자료 10개 (mesh_cert_matrix_run_one)", 126),
    ("fleet",    "함대 검사 + 위상·재질 봉인 대조 (mesh_cert_matrix_fleet)", 121),
    ("controls", "적대 대조 6스위트 (양성·음성 184건)", 34),
    ("matrix",   "매트릭스 표 생성 (make_mesh_cert_matrix + html)", 5),
    ("golden",   "골든 봉인 대조(이 파일)", 9),
    ("certs",    "⚠인증서 5종 재발급 — 형상이 바뀐 뒤에만 (기본 꺼짐 · 미측정)", None),
]
DEFAULT_FULL = ("map", "raw", "fleet", "controls", "matrix", "golden")

_PY = sys.executable
_ENV = dict(os.environ, PYTHONPATH=f"{os.path.join(ROOT,'src')}:{_HERE}",
            CUDA_VISIBLE_DEVICES="")


def _run(cmd, log=None, cwd=ROOT):
    t = time.time()
    if log:
        with open(log, "w", encoding="utf-8") as fh:
            r = subprocess.run(cmd, cwd=cwd, env=_ENV, stdout=fh, stderr=subprocess.STDOUT)
        #  ⭐ 나가는 값도 파일로 남긴다 — 매트릭스 생성기가 `<이름>.exit` 를 읽어
        #    «대조가 진짜 통과했나» 를 표에 싣는다(안 남기면 그 칸이 «모름» 이 된다).
        with open(os.path.splitext(log)[0] + ".exit", "w", encoding="utf-8") as fh:
            fh.write(f"{r.returncode}\n")
    else:
        r = subprocess.run(cmd, cwd=cwd, env=_ENV)
    return dict(cmd=" ".join(cmd[1:]), rc=r.returncode, sec=round(time.time() - t, 1),
                log=os.path.relpath(log, ROOT) if log else None)


def stage_map() -> dict:
    """범주 지도 20칸이 매트릭스 45행에 전부 덮였는가."""
    try:
        mp = json.load(open(os.path.join(ROOT, CERTS["map"][0]), encoding="utf-8"))
        mx = json.load(open(os.path.join(ROOT, CERTS["matrix"][0]), encoding="utf-8"))
    except (OSError, ValueError) as e:
        return dict(ok=False, why=f"지도/매트릭스를 못 읽었다: {e}")
    cats = [c["id"] for c in mp["categories"]]
    covered = set()
    for r in mx["checks"]:
        for c in str(r.get("category", "")).split("·"):
            covered.add(c.strip())
    miss = [c for c in cats if c not in covered]
    return dict(ok=not miss, n_categories=len(cats), n_checks=len(mx["checks"]),
                uncovered=miss)


def run_full(stages, jobs, raw_dir, keys, update_reason=None,
             matrix_out=None, matrix_md=None, skip_html=False) -> dict:
    res, t0 = {}, time.time()
    raw_dir = os.path.abspath(raw_dir)
    ctl_dir = os.path.join(raw_dir, "ctl")
    os.makedirs(ctl_dir, exist_ok=True)

    #  ⭐순서는 **부른 순서**를 따른다(기본값은 golden 이 맨 끝 — 다 돌리고 나서 봉인을 본다)
    _desc = {n: d for n, d, _ in STAGES}
    for name in stages:
        if name not in _desc:
            print(f"⚠ 모르는 단계 [{name}] — 건너뛴다")
            continue
        desc = _desc[name]
        print(f"\n{'='*100}\n▶ 단계 [{name}] {desc}\n{'='*100}", flush=True)
        t = time.time()
        if name == "map":
            res["map"] = stage_map()
            print(f"   지도 {res['map'].get('n_categories')}칸 · 매트릭스 "
                  f"{res['map'].get('n_checks')}행 · 안 덮인 칸 {res['map'].get('uncovered')}")
        elif name == "raw":
            runs = []
            with _fut.ThreadPoolExecutor(max_workers=jobs) as ex:
                futs = {ex.submit(
                    _run, [_PY, os.path.join(_HERE, "mesh_cert_matrix_run_one.py"),
                           "--key", k, "--out", os.path.join(raw_dir, f"{k}.json")],
                    os.path.join(ctl_dir, f"run_one_{k}.log")): k for k in keys}
                for f in _fut.as_completed(futs):
                    r = f.result(); r["key"] = futs[f]; runs.append(r)
                    print(f"   {r['key']:12s} rc={r['rc']} {r['sec']:6.1f} s", flush=True)
            res["raw"] = dict(runs=sorted(runs, key=lambda r: r["key"]),
                              ok=all(r["rc"] == 0 for r in runs))
        elif name == "fleet":
            r = _run([_PY, os.path.join(_HERE, "mesh_cert_matrix_fleet.py"),
                      os.path.join(raw_dir, "fleet.json")],
                     os.path.join(ctl_dir, "fleet.log"))
            res["fleet"] = dict(**r, ok=r["rc"] == 0)
            print(f"   rc={r['rc']} {r['sec']:.1f} s → {r['log']}")
        elif name == "controls":
            suites = ["adv_mesh_check_faults", "adv_mesh_topo_faults", "adv_mesh_dimref_faults",
                      "adv_mesh_symmetry_faults", "adv_mesh_placement_0816",
                      "adv_material_provenance_faults"]
            runs = []
            with _fut.ThreadPoolExecutor(max_workers=min(6, jobs)) as ex:
                futs = {ex.submit(_run, [_PY, os.path.join(_HERE, s + ".py")],
                                  os.path.join(ctl_dir, s + ".log")): s for s in suites}
                for f in _fut.as_completed(futs):
                    r = f.result(); r["suite"] = futs[f]
                    tail = ""
                    try:
                        for ln in open(os.path.join(ROOT, r["log"]), encoding="utf-8"):
                            if ln.startswith("결과:"):
                                tail = ln.strip()
                    except OSError:
                        pass
                    r["result"] = tail
                    runs.append(r)
                    print(f"   {r['suite']:32s} rc={r['rc']} {r['sec']:6.1f} s  {tail}",
                          flush=True)
            res["controls"] = dict(runs=sorted(runs, key=lambda r: r["suite"]),
                                   ok=all(r["rc"] == 0 for r in runs))
        elif name == "matrix":
            cmd = [_PY, os.path.join(_HERE, "make_mesh_cert_matrix_0816.py"),
                   "--raw-dir", raw_dir, "--fleet", os.path.join(raw_dir, "fleet.json"),
                   "--ctl-dir", ctl_dir]
            if matrix_out:
                cmd += ["--out", matrix_out]
            if matrix_md:
                cmd += ["--md", matrix_md]
            r1 = _run(cmd, os.path.join(ctl_dir, "matrix.log"))
            r2 = dict(rc=0, sec=0.0, cmd="(건너뜀)") if skip_html else _run(
                [_PY, os.path.join(_HERE, "make_mesh_cert_matrix_html_0816.py")],
                os.path.join(ctl_dir, "matrix_html.log"))
            res["matrix"] = dict(table=r1, html=r2, ok=(r1["rc"] == 0 and r2["rc"] == 0))
            print(f"   표 rc={r1['rc']} {r1['sec']:.1f} s · html rc={r2['rc']} {r2['sec']:.1f} s")
        elif name == "certs":
            gens = ["make_mesh_cert_topology_0816", "mesh_cert_dimension_external_0816",
                    "mesh_cert_placement_0816", "mesh_cert_symmetry_derived_0816",
                    "mesh_cert_material_provenance_0816"]
            runs = []
            for s in gens:
                r = _run([_PY, os.path.join(_HERE, s + ".py")],
                         os.path.join(ctl_dir, s + ".log"))
                r["gen"] = s
                runs.append(r)
                print(f"   {r['gen']:38s} rc={r['rc']} {r['sec']:7.1f} s", flush=True)
            res["certs"] = dict(runs=runs, ok=all(r["rc"] == 0 for r in runs))
        elif name == "golden":
            res["golden"] = cmd_verify(jobs=jobs, keys=keys, update_reason=update_reason,
                                       quiet=False)
        res.setdefault("_sec", {})[name] = round(time.time() - t, 1)
    res.setdefault("_sec", {})["total"] = round(time.time() - t0, 1)
    return res


# =========================================================================== #
#  7. CLI
# =========================================================================== #
def cmd_verify(jobs=5, keys=None, update_reason=None, quiet=False, out_json=None) -> dict:
    import drones
    keys = list(keys or drones.DRONES)
    partial = len(keys) < len(drones.DRONES)
    new = build_golden(keys=keys, jobs=jobs, verbose=not quiet)

    if not os.path.exists(GOLDEN_PATH):
        if update_reason is None:
            print(f"⛔ 골든이 없다: {GOLDEN_PATH}\n"
                  f"   처음 봉인하려면: --update --reason \"최초 봉인\"")
            return dict(ok=False, exit=3, reason="골든 없음")
        return _write_golden(new, update_reason, old=None)

    old = json.load(open(GOLDEN_PATH, encoding="utf-8"))
    findings = check_certs_live(new) + diff_golden(old, new)
    text = render_findings(findings, old, new)
    if not quiet:
        print("\n" + text)
    sev = {f["sev"] for f in findings}
    code = 2 if (RED in sev or ORANGE in sev) else (1 if YELLOW in sev else 0)

    if update_reason is not None:
        if partial:
            print("⛔ 일부 기체만 돌린 결과로는 갱신하지 않는다(--keys 를 빼고 다시).")
            return dict(ok=False, exit=3, reason="부분 실행")
        return _write_golden(new, update_reason, old=old, findings=findings, text=text)

    res = dict(ok=code == 0, exit=code, n_findings=len(findings), findings=findings,
               report_text=text.splitlines(), partial=partial)
    if out_json:
        json.dump(_jsonify(res), open(out_json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"\n→ {out_json}")
    return res


def _write_golden(new: dict, reason: str, old: dict | None,
                  findings=None, text: str = "") -> dict:
    hist = list((old or {}).get("history", []))
    if old is not None:
        hist.append(dict(
            sealed_kst=old.get("_meta", {}).get("generated_kst"),
            replaced_kst=_kst(), reason=reason,
            previous_seal_all=old.get("_meta", {}).get("seal_all"),
            previous_file_sha=_file_sha16(GOLDEN_PATH),
            previous_mesh_sha={k: v.get("sha", {}).get("mesh")
                               for k, v in old.get("airframes", {}).items()},
            n_findings=len(findings or []),
            what_changed_ko=[f"{f['sev']} [{f['kind']}] {f['what']}" for f in (findings or [])],
        ))
    new["history"] = hist[-20:]
    new["_meta"]["update_reason"] = reason
    if text:
        new["last_update_diff_ko"] = text.splitlines()
    os.makedirs(os.path.dirname(GOLDEN_PATH), exist_ok=True)
    json.dump(_jsonify(new), open(GOLDEN_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n✅ 골든 재봉인 — {GOLDEN_PATH}\n   이유: {reason}\n"
          f"   지문(seal_all) {new['_meta']['seal_all']} · "
          f"크기 {os.path.getsize(GOLDEN_PATH)/1024:.0f} KB")
    return dict(ok=True, exit=0, updated=True, reason=reason)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="메쉬 인증 한 줄 진입점 + 골든 봉인 (CPU only)")
    ap.add_argument("--full", action="store_true", help="지도·검사·대조·매트릭스·봉인 전부")
    ap.add_argument("--stage", default=None,
                    help="쉼표로 단계 고르기: " + ",".join(s[0] for s in STAGES))
    ap.add_argument("--update", action="store_true", help="골든 재봉인(--reason 필수)")
    ap.add_argument("--reason", default=None, help="재봉인 이유 한 줄")
    ap.add_argument("--jobs", type=int, default=5, help="병렬 작업 수(기본 5)")
    ap.add_argument("--keys", default=None, help="기체 일부만(쉼표)")
    ap.add_argument("--raw-dir", default=os.path.join(ROOT, "outputs",
                                                      "mesh_cert_matrix_raw_0816"))
    ap.add_argument("--matrix-out", default=None, help="매트릭스 json 을 다른 곳에(연습용)")
    ap.add_argument("--matrix-md", default=None, help="매트릭스 md 를 다른 곳에(연습용)")
    ap.add_argument("--skip-html", action="store_true", help="매트릭스 html 생성을 건너뛴다")
    ap.add_argument("--gates", action="store_true", help="문 배선 감사만 찍는다")
    ap.add_argument("--how", action="store_true", help="골든 갱신 절차를 찍는다")
    ap.add_argument("--list", action="store_true", help="단계 목록 + 실측 소요시간")
    ap.add_argument("--json", default=None, help="결과를 JSON 으로도 쓴다")
    a = ap.parse_args(argv)

    if a.list:
        print("단계         실측(초)  하는 일")
        for n, d, s in STAGES:
            print(f"  {n:10s} {('미측정' if s is None else f'{s:7.1f}'):>7s}  {d}")
        print(f"\n  기본(--full) = {', '.join(DEFAULT_FULL)}  ≈ "
              f"{sum(s for n, _, s in STAGES if n in DEFAULT_FULL and s):.0f} 초"
              f"  (봉인 대조만이면 {dict((n, s) for n, _, s in STAGES)['golden']:.0f} 초)")
        return 0
    if a.how:
        print("=" * 100)
        print("골든이 «바뀌어야 마땅한» 경우의 갱신 절차 (의도한 수리)")
        print("=" * 100)
        for s in UPDATE_PROCEDURE_KO:
            print("  " + s)
        print("\n못 하는 것:")
        for s in LIMITS_KO:
            print("  · " + s)
        return 0
    if a.gates:
        print(render_gates(scan_doors()))
        return 0

    keys = [k.strip() for k in a.keys.split(",")] if a.keys else None
    reason = a.reason if a.update else None
    if a.update and not a.reason:
        print("⛔ --update 에는 --reason \"한 줄 이유\" 가 필요하다. "
              "이유를 못 적으면 그 변경은 사고다.")
        return 3

    if a.full or a.stage:
        stages = ([s.strip() for s in a.stage.split(",")] if a.stage else list(DEFAULT_FULL))
        import drones
        res = run_full(stages, jobs=a.jobs, raw_dir=a.raw_dir,
                       keys=keys or list(drones.DRONES), update_reason=reason,
                       matrix_out=a.matrix_out, matrix_md=a.matrix_md,
                       skip_html=a.skip_html)
        print(f"\n{'='*100}\n단계별 소요(초): "
              + " · ".join(f"{k} {v}" for k, v in res["_sec"].items()))
        if a.json:
            json.dump(_jsonify(res), open(a.json, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"→ {a.json}")
        g = res.get("golden") or {}
        return int(g.get("exit", 0))

    res = cmd_verify(jobs=a.jobs, keys=keys, update_reason=reason, out_json=a.json)
    return int(res.get("exit", 0))


if __name__ == "__main__":
    sys.exit(main())
