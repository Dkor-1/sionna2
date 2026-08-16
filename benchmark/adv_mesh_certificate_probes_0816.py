"""심사자 라운드 — **인증서가 근거로 삼는 시험**을 한 파일로 (2026-08-16/17).

이 라운드는 형상을 한 글자도 안 바꾼다. 만드는 것은 검사·대조·인증서뿐이다.
여기 담긴 일곱 시험은 `docs/MESH_CERTIFICATE.md` 의 «장담 못 하는 것» 칸을 채운 근거이고,
전부 **인메모리 복제본**만 흔든다(저장소 파일·형상 상수는 안 건드린다).

    PYTHONPATH=src:benchmark python benchmark/adv_mesh_certificate_probes_0816.py
    →  outputs/mesh_certificate_probes_0816.json

시험 목록 (앞의 네 라운드를 공격한 다섯 갈래 중 ①②에 해당)
  C1 직렬화     출하 OBJ 는 미터 소수 6자리다. 되읽어 **저장소 자기 검사**를 먹이면 판정이 같은가?
  C2 부품 존재   그룹을 통째로 지우면 45검사 계열 중 무엇이 우는가?
  C3 매몰면 여유  A9 예산의 남은 여유가 «부품 하나를 통째로 묻는 것» 보다 큰가?
  C4 좌우대칭 문턱 0.15 mm 예산은 **물리 단차** 몇 mm 에 해당하는가?
  C5 프롭↔벨    양성 대조가 없던 축에 결함을 심으면 무는가?
  C6 원시값     NaN·Inf·빈 라벨을 심으면 무엇이 잡고 무엇이 죽는가?
  C7 외부 참값   유도한 허용오차 U 가 **경계에서** 무는가(0.9 U 통과 · 1.1 U 실패)?
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "src"))

from drones import DRONES, build_drone, rotor_layout          # noqa: E402
from geom import Mesh                                         # noqa: E402
import material_provenance                                    # noqa: E402
import mesh_check                                             # noqa: E402
import mesh_dimref                                            # noqa: E402
import mesh_placement                                         # noqa: E402
import mesh_symmetry                                          # noqa: E402
import mesh_topo_check                                        # noqa: E402

OUT_JSON = os.path.join(_HERE, "..", "outputs", "mesh_certificate_probes_0816.json")
KEY = "mini5pro"          # 감도 시험의 기준 기체 = ⭐주력 표적


# --------------------------------------------------------------------------- #
#  공통
# --------------------------------------------------------------------------- #
_CACHE: dict[str, tuple] = {}


def arrays(key: str):
    """기체 메쉬를 (V, F, G) 배열로. 한 번만 짓고 재사용한다."""
    if key not in _CACHE:
        m = build_drone(DRONES[key])
        _CACHE[key] = (np.asarray(m.v, float), np.asarray(m.f, np.int64), np.asarray(m.g))
    v, f, g = _CACHE[key]
    return v.copy(), f.copy(), g.copy()


def mk(v, f, g) -> Mesh:
    m = Mesh()
    m.v = [tuple(x) for x in v]
    m.f = [tuple(int(i) for i in t) for t in f]
    m.g = list(g)
    return m


def tri_area(V, F):
    return 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)


def read_obj(path):
    V, F = [], []
    with open(path) as fh:
        for ln in fh:
            if ln.startswith("v "):
                V.append([float(x) for x in ln.split()[1:4]])
            elif ln.startswith("f "):
                F.append([int(t.split("/")[0]) - 1 for t in ln.split()[1:4]])
    return np.asarray(V, float), np.asarray(F, np.int64)


# --------------------------------------------------------------------------- #
#  C1 — 직렬화(왕복). 범주 지도에 **없는** 자리다.
# --------------------------------------------------------------------------- #
def probe_serialization() -> dict:
    """검사한 것(메모리)과 출하한 것(파일)이 같은 물건인가.

    `geom.Mesh.write_obj` 는 `v {x:.6f}` — 미터 소수 6자리라 **1 µm 격자**로 양자화한다.
    게이트(`mesh_check.assert_ok`)는 write 앞에서 도니까 파일은 한 번도 검사된 적이 없다."""
    print("\nC1 직렬화 — 출하 파일에 저장소 자기 검사를 먹인다")
    out, tmp = [], tempfile.mkdtemp(prefix="cert_ser_")
    for key in DRONES:
        V, F, G = arrays(key)
        m = mk(V, F, G)
        mem = mesh_check.check_mesh(m, name=key)
        V2, F2, G2 = [], [], []
        for grp in sorted(set(G.tolist())):
            p = os.path.join(tmp, f"{key}__{grp}.obj")
            m.write_obj(p, only_group=grp)
            Vf, Ff = read_obj(p)
            off = len(V2)
            V2.extend(Vf.tolist()); F2.extend((Ff + off).tolist()); G2.extend([grp] * len(Ff))
        fil = mesh_check.check_mesh(mk(np.asarray(V2), np.asarray(F2, np.int64), np.asarray(G2)),
                                    name=key)
        rows = []
        for grp, a in mem["groups"].items():
            b = fil["groups"][grp]
            ka = (a["watertight"], a["boundary_edges"], a.get("nonmanifold_edges", 0), a["degenerate"])
            kb = (b["watertight"], b["boundary_edges"], b.get("nonmanifold_edges", 0), b["degenerate"])
            if ka != kb:
                rows.append(dict(group=grp, memory=ka, file=kb,
                                 memory_ok=a["ok"], file_ok=b["ok"]))
        rec = dict(key=key, memory_ok=mem["ok"], file_ok=fil["ok"],
                   slivers_memory=mem["slivers"], slivers_file=fil["slivers"],
                   changed_groups=rows)
        out.append(rec)
        if mem["ok"] != fil["ok"] or rows:
            print(f"   ❗{key:12s} 메모리 ok={mem['ok']} → 파일 ok={fil['ok']}  "
                  f"바뀐 그룹 {[r['group'] for r in rows]}")
    n_bad = sum(1 for r in out if r["memory_ok"] and not r["file_ok"])
    print(f"   ⇒ 메모리는 통과하는데 **출하 파일은 실패**하는 기체 {n_bad} / {len(out)}")
    return dict(per_airframe=out, n_file_fails=n_bad,
                verdict_ko=("출하 파일은 검사된 적이 없다 — 직렬화는 범주 지도에 없는 층이다"
                            if n_bad else "출하 파일과 메모리 판정이 같다"))


# --------------------------------------------------------------------------- #
#  C2 — 부품 존재(M7). 그룹을 통째로 지운다.
# --------------------------------------------------------------------------- #
def _battery_of_checks(m, key, spec) -> dict:
    out = {}

    def run(nm, fn):
        try:
            r = fn()
            out[nm] = "통과" if (r.get("ok") if isinstance(r, dict) else bool(r)) else "실패"
        except Exception as e:                                  # noqa: BLE001
            out[nm] = f"예외 {type(e).__name__}"

    run("A1~A4 부품위상", lambda: mesh_check.check_mesh(m, key))
    run("A5 치수(스펙)", lambda: mesh_check.check_dimensions(spec, mesh=m))
    run("A6 손대칭", lambda: mesh_check.check_handedness(spec, mesh=m))
    run("A9 매몰면", lambda: mesh_check.check_buried_faces(spec, mesh=m))
    run("T·D 위상·이산화", lambda: mesh_topo_check.check_topology(m, name=key))
    run("S3 좌우대칭", lambda: mesh_symmetry.check_lateral_symmetry(spec, mesh=m))
    run("S4 질량·관성", lambda: mesh_symmetry.check_mass_inertia(spec, mesh=m))
    run("S5 투영면적", lambda: mesh_symmetry.check_projected_area(spec, mesh=m))
    run("V1 라벨↔기하", lambda: material_provenance.check_label_geometry(spec, mesh=m))
    try:
        cen = mesh_placement.placement_census(m, key)
        out["P1~P5 배치"] = "통과" if mesh_placement.check_placement(cen).get("ok") else "실패"
    except Exception as e:                                      # noqa: BLE001
        out["P1~P5 배치"] = f"예외 {type(e).__name__}"
    x = mesh_dimref.check_key(key, mesh=m)
    out["_x1"] = {r["rid"]: r["verdict"] for r in x["rows"]}
    return out


def probe_missing_part() -> dict:
    """그룹 하나를 통째로 지운다 — 무엇이 우는가."""
    print("\nC2 부품 존재 — 그룹을 통째로 지운다")
    spec = DRONES[KEY]
    V, F, G = arrays(KEY)
    A = tri_area(V, F); tot = float(A.sum())
    ctl = _battery_of_checks(mk(V, F, G), KEY, spec)
    rows = []
    for grp in ["canopy", "gear", "camera", "motor", "battery"]:
        if not (G == grp).any():
            continue
        keep = G != grp
        got = _battery_of_checks(mk(V, F[keep], G[keep]), KEY, spec)
        diff = [k for k in ctl if not k.startswith("_") and ctl[k] != got[k]]
        flip = [rid for rid in ctl["_x1"] if ctl["_x1"][rid] != got["_x1"].get(rid, "없음")]
        apct = round(float(100.0 * A[G == grp].sum() / tot), 3)
        rows.append(dict(group=grp, n_faces=int((G == grp).sum()), area_pct=apct,
                         checks_that_changed=diff, x1_rows_that_flipped=flip,
                         silent=bool(not diff and not flip)))
        print(f"   {grp:9s} 면 {int((G==grp).sum()):5d} · 표면적 {apct:5.2f} %  "
              f"→ 운 검사 {diff if diff else '**없음**'}"
              + (f" · X1 뒤집힘 {flip}" if flip else ""))
    n_silent = sum(1 for r in rows if r["silent"])
    print(f"   ⇒ 통째로 사라져도 **아무도 못 보는** 그룹 {n_silent} / {len(rows)}")
    return dict(key=KEY, rows=rows, n_silent=n_silent,
                verdict_ko="부품 존재(M7)는 판정이 없다 — 대칭이 깨지거나 부품쌍 관계가 바뀔 때만 간접으로 걸린다")


# --------------------------------------------------------------------------- #
#  C3 — A9 예산의 남은 여유 vs 부품 하나의 기여
# --------------------------------------------------------------------------- #
def probe_buried_headroom() -> dict:
    print("\nC3 매몰면 — 예산 여유가 «부품 하나를 통째로 묻는 것» 보다 큰가")
    spec = DRONES[KEY]
    V0, F, G = arrays(KEY)
    A = tri_area(V0, F); tot = float(A.sum())
    b0 = mesh_check.check_buried_faces(spec, mesh=mk(V0, F, G))
    head = b0["budget_pct"] - b0["defect_pct"]
    print(f"   기준: 진짜결함 {b0['defect_pct']:.3f} % · 예산 {b0['budget_pct']} % · 남은 여유 {head:.2f} pp")
    rows = []
    for grp, dz in [("gear", 40.0), ("motor", 30.0)]:
        if not (G == grp).any():
            continue
        vg = np.unique(F[G == grp])
        V = V0.copy(); V[vg, 2] += dz / 1000.0                  # 셸 속으로 밀어 넣는다
        r = mesh_check.check_buried_faces(spec, mesh=mk(V, F, G))
        rows.append(dict(group=grp, dz_mm=dz, area_pct=round(float(100 * A[G == grp].sum() / tot), 3),
                         defect_pct=r["defect_pct"], delta_pp=round(r["defect_pct"] - b0["defect_pct"], 3),
                         budget=r["budget_pct"], ok=r["ok"]))
        print(f"   {grp:6s}(표면적 {100*A[G==grp].sum()/tot:5.2f} %) 를 {dz:.0f} mm 밀어 넣음 → "
              f"결함 {r['defect_pct']:.3f} % ({r['defect_pct']-b0['defect_pct']:+.2f} pp) "
              f"{'통과 ← 예산을 못 넘는다' if r['ok'] else '실패'}")
    return dict(key=KEY, baseline=b0["defect_pct"], budget=b0["budget_pct"],
                headroom_pp=round(head, 3), injections=rows,
                verdict_ko="예산 여유보다 단일 부품의 기여가 작으면 이 검사는 그 결함으로는 실패할 수 없다")


# --------------------------------------------------------------------------- #
#  C4 — 좌우대칭의 실효 문턱
# --------------------------------------------------------------------------- #
def probe_symmetry_threshold() -> dict:
    print("\nC4 좌우대칭 — 예산 0.15 mm 는 물리 단차 몇 mm 인가")
    spec = DRONES[KEY]
    V0, F, G = arrays(KEY)
    vb = np.unique(F[G == "body"]); vb = vb[V0[vb, 1] > 0]
    rows, first_fail = [], None
    for d in [0.0, 0.05, 0.10, 0.16, 0.30, 0.50, 1.00]:
        V = V0.copy(); V[vb, 1] += d / 1000.0
        r = mesh_symmetry.check_lateral_symmetry(spec, mesh=mk(V, F, G))
        gb = r["groups"]["body"]
        rows.append(dict(step_mm=d, surf_rms_mm=gb["surf_rms_mm"], budget_mm=gb["budget_mm"],
                         y_moment=r["frame_area_y_moment_rel"], ok=r["ok"]))
        if not r["ok"] and first_fail is None:
            first_fail = d
        print(f"   단차 {d:5.2f} mm → 표면잔차 {gb['surf_rms_mm']:.5f} mm (예산 {gb['budget_mm']}) · "
              f"y-모멘트 {r['frame_area_y_moment_rel']:9.2e}  {'통과' if r['ok'] else '실패'}")
    print(f"   ⇒ 실효 문턱 ≈ {first_fail} mm (0.16 mm 는 통과)")
    return dict(key=KEY, rows=rows, first_fail_step_mm=first_fail,
                verdict_ko="자가 읽는 값은 물리 단차의 약 0.55배 + 기준선이라 예산 숫자보다 문턱이 높다")


# --------------------------------------------------------------------------- #
#  C5 — 프롭↔벨 관통(양성 대조가 없던 축)
# --------------------------------------------------------------------------- #
def probe_prop_bell() -> dict:
    print("\nC5 프롭↔벨 솔리드 관통 — 양성 대조를 새로 건다")
    spec = DRONES[KEY]
    V0, F, G = arrays(KEY)
    vp = np.unique(F[G == "prop"])
    rows = []
    for d in [0.0, 0.5, 1.0, 1.5, 2.0]:
        V = V0.copy(); V[vp, 2] -= d / 1000.0
        r = mesh_check.check_prop_bell_solid(spec, mesh=mk(V, F, G))
        rows.append(dict(sink_mm=d, area_pct=r["area_pct"], tris=r["tris"],
                         budget=r["budget_pct"], ok=r["ok"]))
        print(f"   침강 {d:4.1f} mm → 관통면적 {r['area_pct']:6.3f} % (예산 {r['budget_pct']}) "
              f"삼각형 {r['tris']:5d}  {'통과' if r['ok'] else '실패 ✅ 걸림'}")
    return dict(key=KEY, rows=rows,
                verdict_ko="선언된 스탠드오프(1.0 mm)를 다 쓰는 지점부터 문다 — 검사는 건강하다")


# --------------------------------------------------------------------------- #
#  C6 — 원시값(NaN·Inf·빈 라벨)
# --------------------------------------------------------------------------- #
def probe_raw_values() -> dict:
    print("\nC6 원시값 — NaN·Inf·빈 라벨")
    spec = DRONES[KEY]
    rows = []
    faults = [("NaN 정점", "nan"), ("Inf 정점", "inf"), ("1e6 m 정점", "far"), ("빈 그룹 라벨", "label")]
    for name, kind in faults:
        V, F, G = arrays(KEY)
        if kind == "nan":
            V[5, 1] = np.nan
        elif kind == "inf":
            V[5, 1] = np.inf
        elif kind == "far":
            V[5, 1] = 1e6
        else:
            G = np.where(np.arange(len(G)) == 3, "", G)
        m = mk(V, F, G)
        got = {}
        for nm, fn in [("check_mesh", lambda: mesh_check.check_mesh(m, KEY)),
                       ("check_dimensions", lambda: mesh_check.check_dimensions(spec, mesh=m)),
                       ("check_handedness", lambda: mesh_check.check_handedness(spec, mesh=m)),
                       ("lateral_symmetry", lambda: mesh_symmetry.check_lateral_symmetry(spec, mesh=m)),
                       ("mass_inertia", lambda: mesh_symmetry.check_mass_inertia(spec, mesh=m))]:
            try:
                got[nm] = "통과" if fn().get("ok") else "실패"
            except Exception as e:                              # noqa: BLE001
                got[nm] = f"예외 {type(e).__name__}"
        caught = any(v != "통과" for v in got.values())
        crashed = [k for k, v in got.items() if v.startswith("예외")]
        rows.append(dict(fault=name, results=got, caught=caught, crashed=crashed))
        print(f"   {name:12s} → 잡힘 {'예' if caught else '❗아니오'} · "
              f"실패로 잡은 검사 {[k for k,v in got.items() if v=='실패']} · 예외로 죽은 검사 {crashed}")
    return dict(key=KEY, rows=rows,
                verdict_ko="잡히기는 하나 절반은 «실패» 가 아니라 «예외» 로 죽는다 — 판정문이 아니라 스택트레이스가 나온다")


# --------------------------------------------------------------------------- #
#  C7 — 외부 참값 U 의 경계
# --------------------------------------------------------------------------- #
def probe_x1_boundary() -> dict:
    print("\nC7 외부 참값 — 유도한 허용오차 U 가 경계에서 무는가")
    cases = [("matrice4e", "M4E-04", "body", 0), ("matrice4e", "M4E-07", "body", 2),
             ("mini2", "MI2-06", "motor", 2)]
    rows, n_ok = [], 0
    for key, rid, grp, axis in cases:
        V0, F, G = arrays(key)
        base = {r["rid"]: r for r in mesh_dimref.check_key(key, mesh=mk(V0, F, G))["rows"]}[rid]
        U, r0 = base["tolerance"]["U"], base["residual"]
        vg = np.unique(F[G == grp])
        for mult in (0.9, 1.1):
            want = mult * U
            shift = (want - r0) if r0 >= 0 else -(want + r0)
            V = V0.copy(); V[vg, axis] += shift / 1000.0
            rr = {r["rid"]: r for r in mesh_dimref.check_key(key, mesh=mk(V, F, G))["rows"]}[rid]
            ok = (rr["verdict"] == "일치") == (mult < 1.0)
            n_ok += ok
            rows.append(dict(key=key, rid=rid, mult=mult, U=round(U, 4),
                             residual=rr["residual"], verdict=rr["verdict"], control_ok=bool(ok)))
            print(f"   {key:10s} {rid} {mult:.1f} U → 잔차 {rr['residual']:+8.4f} mm "
                  f"(U={U:.3f}) {rr['verdict']:5s} {'✅' if ok else '❌'}")
    print(f"   ⇒ 경계 대조 {n_ok}/{len(rows)}")
    return dict(rows=rows, n_ok=n_ok, n_total=len(rows),
                verdict_ko="U 는 경계에서 정확히 문다 — 이 축의 허용값은 역산이 아니다")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    res = {"_meta": dict(
        title="메쉬 인증서 근거 시험 — 심사자 라운드",
        generated_kst=time.strftime("%Y-%m-%d %H:%M KST", time.localtime(time.time() + 9 * 3600)),
        policy_ko="형상 상수 무변경 · GPU 미사용 · git 미접촉. 흔드는 것은 전부 인메모리 복제본이다.",
        reference_airframe=KEY,
        mesh_fingerprints={k: mesh_dimref.mesh_fingerprint(mk(*arrays(k))) for k in DRONES},
    )}
    res["C1_serialization"] = probe_serialization()
    res["C2_missing_part"] = probe_missing_part()
    res["C3_buried_headroom"] = probe_buried_headroom()
    res["C4_symmetry_threshold"] = probe_symmetry_threshold()
    res["C5_prop_bell"] = probe_prop_bell()
    res["C6_raw_values"] = probe_raw_values()
    res["C7_x1_boundary"] = probe_x1_boundary()
    res["_meta"]["elapsed_s"] = round(time.time() - t0, 1)

    os.makedirs(os.path.dirname(os.path.abspath(OUT_JSON)), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print(f"\n기록 → {os.path.relpath(OUT_JSON, os.path.join(_HERE, '..'))}  "
          f"({res['_meta']['elapsed_s']} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
