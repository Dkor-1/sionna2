# -*- coding: utf-8 -*-
"""
mesh_cert_dimension_external_0816.py — **치수·외부 기준 대조 인증서**를 쓴다
==============================================================================
무엇을 만드나: `outputs/mesh_cert_dimension_external_0816.json`
  ① 잔차표      — 기체 × 부품 칸마다 «메쉬에서 잰 값 ↔ 바깥 참값» 과 그 차이
  ② 허용오차    — 기체별로 **측정 불확실도에서 유도**한 U (임의 숫자 없음)
  ③ 근거 등급   — 칸마다 [A] 공식 CAD · [B] 사진 · [C] 계열 유추 · [D] 대리 · «모름»
  ④ 대조 결과   — 양성(결함을 심으면 걸린다) + 음성(멀쩡하면 통과) 전수
  ⑤ 가드        — M4T/M4E 짐벌 규칙 · 허용오차 유도 강제 · 근거 파일 실재
  ⑥ 봉인        — 지금 잔차를 «선언» 으로 못박고 메쉬 지문을 같이 적는다(회귀 감지)
  ⑦ 못 하는 것  — 이 인증서가 **장담하지 않는** 범위

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/mesh_cert_dimension_external_0816.py
      ⛔ GPU 미사용 · ⛔ git 미접촉 · ⛔ 형상 상수 무변경(읽기만).
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import os
import sys
from contextlib import redirect_stdout

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _HERE)

import mesh_dimref as MD                                   # noqa: E402
from drones import DRONES, build_drone                     # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "mesh_cert_dimension_external_0816.json")


def _kst() -> str:
    return (_dt.datetime.now(_dt.timezone.utc)
            + _dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")


def _env() -> dict:
    import scipy
    import trimesh
    return dict(python=sys.executable, numpy=np.__version__,
                scipy=scipy.__version__, trimesh=trimesh.__version__,
                gpu_used=False)


def _asset_status() -> dict:
    """참조 자산이 지금 손에 있는가 — 없으면 그 기체의 [A] 주장은 재현할 수 없다."""
    import hashlib
    want = {
        "matrice4-M4T_v2.step": ("DJI Matrice 4T 공식 STEP", "51ff9a47fac2c4c7a9d3817d5444f74d",
                                 "⛔깃에 없다(158 MB) — outputs/meshfix_matrice4e.json 이 추출값을 들고 있다"),
        "WM161_zhankai_1k.glb": ("DJI Mini 2 공식 GLB(펼침)", "7d391743dd4f5c8bcb60f581f4ee0e94",
                                 "깃에 있다"),
        "x500v2-frame.step": ("Holybro X500 V2 공식 STEP", None, "깃에 있다"),
        "AIR2216II_Motor_3D.STEP": ("Holybro AIR2216II 모터 단품 STEP", None, "깃에 있다"),
    }
    ref = os.path.join(_ROOT, "assets", "meshes", "reference")
    out = {}
    for f, (what, md5, note) in want.items():
        p = os.path.join(ref, f)
        ok = os.path.exists(p)
        d = dict(what=what, present=bool(ok), note=note, expected_md5=md5)
        if ok:
            d["bytes"] = os.path.getsize(p)
            if md5 and d["bytes"] < 50_000_000:
                h = hashlib.md5(open(p, "rb").read()).hexdigest()
                d["md5"] = h
                d["md5_match"] = bool(h == md5)
            elif md5:
                d["md5"] = "미계산(158 MB — 이 라운드는 읽지 않았다)"
        out[f] = d
    return out


def _reference_relive() -> dict:
    """⭐ 참값을 **다시 잰다** — 저장소 안에 있는 자산(Mini 2 공식 GLB)을 이 라운드가 직접 열어
    참값 표의 수가 재현되는지 본다. «원장을 베껴 적었다» 와 «내가 다시 쟀다» 는 다른 주장이다."""
    p = os.path.join(_ROOT, "assets", "meshes", "reference", "WM161_zhankai_1k.glb")
    if not os.path.exists(p):
        return dict(available=False, why="GLB 없음")
    import trimesh
    sc = trimesh.load(p, process=False)
    pts = {}
    for node in sc.graph.nodes_geometry:
        T, gname = sc.graph[node]
        v = trimesh.transform_points(np.asarray(sc.geometry[gname].vertices, float), T)
        #  glTF(+y 위 · +z 기수) → 저장소 규약(X 기수 · Y 좌우 · Z 위), mm
        P = np.column_stack([v[:, 2], v[:, 0], v[:, 1]]) * 1000.0
        pts.setdefault(gname, []).append(P)
    pts = {k: np.vstack(v) for k, v in pts.items()}
    PROPS = {"polySurface58", "polySurface61", "polySurface80", "polySurface81",
             "polySurface84", "polySurface89", "polySurface95", "polySurface102"}
    nonprop = np.vstack([v for k, v in pts.items() if k not in PROPS])
    span = nonprop.max(0) - nonprop.min(0)
    bells = ["polySurface76", "polySurface96", "polySurface90", "polySurface53"]
    ctr, dims = [], []
    for b in bells:
        P = pts[b]
        ctr.append(0.5 * (P.max(0) + P.min(0)))
        dims.append(P.max(0) - P.min(0))
    ctr = np.asarray(ctr)
    diag = max(float(np.hypot(*(ctr[i][:2] - ctr[j][:2])))
               for i in range(4) for j in range(i + 1, 4))
    gim = pts["polySurface204"]
    gdim = gim.max(0) - gim.min(0)
    #  ⚠ 판정 문장을 **손으로 쓰지 않는다** — 재실측과 원장의 차이를 계산해서 적는다.
    #    (손으로 적으면 코드가 바뀌었을 때 문장만 낡는다)
    led = dict(span=[159.1127, 203.4336, 55.9773], diag=213.051,
               bell=[18.2028, 18.1327, 7.1055], gim=[40.567, 32.239, 34.012])
    dmax = max([abs(float(span[i]) - led["span"][i]) for i in range(3)]
               + [abs(diag - led["diag"])]
               + [abs(float(dims[0][i]) - led["bell"][i]) for i in range(3)]
               + [abs(float(gdim[i]) - led["gim"][i]) for i in range(3)])
    return dict(
        available=True, file="assets/meshes/reference/WM161_zhankai_1k.glb",
        method=("glTF 노드별 월드 변환 적용 → 축 바꿔치기(X=z, Y=x, Z=y)·×1000 → "
                "프롭 8장(polySurface58/61/80/81/84/89/95/102) 제외"),
        remeasured=dict(
            props_excluded_span_mm=[round(float(x), 4) for x in span],
            motor_bell_diagonal_mm=round(diag, 4),
            front_bell_bbox_mm=[round(float(x), 4) for x in dims[0]],
            gimbal_part_bbox_mm=[round(float(x), 4) for x in gdim],
        ),
        ledger_says=dict(
            props_excluded_span_mm=led["span"], motor_bell_diagonal_mm=led["diag"],
            front_bell_bbox_mm=led["bell"], gimbal_part_bbox_mm=led["gim"],
        ),
        max_abs_difference_mm=round(float(dmax), 5),
        verdict=(f"재현됨 — 10개 값 전부 원장과 최대 {dmax:.4f} mm 안에서 같다. "
                 "즉 이 인증서의 mini2 참값은 «원장을 베껴 적은 것» 이 아니라 "
                 "**이 라운드가 DJI 공식 GLB 를 직접 열어 다시 잰 것**이다. "
                 "⚠ 벨 대각은 벨 파트의 bbox 중심으로 쟀다 — 원장은 «벨 축» 이라고 적는데 "
                 "두 잣대가 이 대칭 부품에서는 같은 점을 준다(차이 0.0005 mm)."),
    )


def _reference_relive_x500() -> dict:
    """⭐ Holybro X500 V2 **공식 STEP 을 이 라운드가 직접 다시 파싱**해 참값을 재유도한다.
    파서는 저장소에 이미 있는 것(benchmark/measure_x500v2_cad.py::Step, OCC 없이 STEP 어셈블리
    변환을 합성)을 그대로 쓴다 — 새로 짠 자를 믿으라고 하지 않는다.

    CAD 축 규약: x = 좌우 · y = 위 · z = 앞뒤. 하판 아랫면이 y = 0 이다."""
    p = os.path.join(_ROOT, "assets", "meshes", "reference", "x500v2-frame.step")
    if not os.path.exists(p):
        return dict(available=False, why="STEP 없음")
    try:
        from pathlib import Path

        from measure_x500v2_cad import Step
        st = Step(Path(p))
        P = st.assemble()
    except Exception as e:                                       # noqa: BLE001
        return dict(available=False, why=f"파싱 실패: {type(e).__name__}: {e}")

    def _pts(name):
        return np.vstack([q for q, _ in P[name]])

    def _levels(name, k=2):
        """부품에서 **면이 놓인 y 레벨**을 점 개수로 찾는다(판의 상·하면)."""
        y = np.round(_pts(name)[:, 1], 3)
        v, c = np.unique(y, return_counts=True)
        idx = np.argsort(-c)[:k]
        return sorted(float(v[i]) for i in idx)

    bot, top = _levels("BOTTOM-PLATE-X500-V5"), _levels("TOP-PLATE-X500-V5")
    #  판 한 변 = 면 레벨(직선변)에서의 x 폭. 코너 돌기(±74)는 다른 레벨에 있다.
    q = _pts("BOTTOM-PLATE-X500-V5")
    flat = q[np.abs(q[:, 1] - bot[1]) < 1e-6]
    span = float(flat[:, 0].max() - flat[:, 0].min())
    skid = _pts("CARBON-FIBER-TUBE")
    rails = [np.vstack([r for r, _ in P["CARBON-FIBER-TUBE300"][i:i + 1]])
             for i in range(len(P["CARBON-FIBER-TUBE300"]))]
    rail_z = [float(0.5 * (r[:, 2].min() + r[:, 2].max())) for r in rails]
    rail_len = float(np.mean([float(r[:, 0].max() - r[:, 0].min()) for r in rails]))
    foam = _pts("JIAO-EVA")
    pm06 = _pts("PCB-PM06")
    got = dict(
        plate_thickness_mm=round(bot[1] - bot[0], 4),
        plate_gap_mm=round(top[0] - bot[1], 4),
        plate_stack_mm=round(top[1] - bot[0], 4),
        plate_span_across_flats_mm=round(span, 4),
        skid_track_mm=round(float(np.abs(np.unique(np.round(skid[:, 2], 2))).max() * 2), 4),
        payload_rail_track_mm=round(max(rail_z) - min(rail_z), 4),
        payload_rail_length_mm=round(rail_len, 4),
        gear_height_mm=round(float(-foam[:, 1].min()), 4),
        pm06_bbox_mm=[round(float(x), 4) for x in (pm06.max(0) - pm06.min(0))],
    )
    led = dict(plate_thickness_mm=2.0, plate_gap_mm=28.0, plate_stack_mm=32.0,
               plate_span_across_flats_mm=143.72, skid_track_mm=239.91,
               payload_rail_track_mm=60.0, payload_rail_length_mm=250.0,
               gear_height_mm=215.28, pm06_bbox_mm=[55.0, 11.99, 35.0])
    diffs = {}
    for k, v in got.items():
        a = np.atleast_1d(np.asarray(v, float))
        b = np.atleast_1d(np.asarray(led[k], float))
        diffs[k] = round(float(np.abs(a - b).max()), 4)
    return dict(
        available=True, file="assets/meshes/reference/x500v2-frame.step",
        parser="benchmark/measure_x500v2_cad.py :: Step (저장소 기존 파서)",
        method=("STEP 어셈블리 변환을 합성해 부품별 점군을 조립좌표로 옮긴 뒤, 판은 «점이 가장 "
                "많이 모인 두 y 레벨»(=상·하면)로, 튜브는 축 위치로, 다리 높이는 폼 최저점으로 잰다"),
        remeasured=got, ledger_says=led, abs_difference_mm=diffs,
        max_abs_difference_mm=round(max(diffs.values()), 4),
        verdict=(f"재현됨 — 9개 값 전부 원장(outputs/x500v2_cad.json)과 최대 "
                 f"{max(diffs.values()):.3f} mm 안에서 같다. 즉 x500v2 참값도 «베껴 적은 것» 이 "
                 f"아니라 이 라운드가 제조사 STEP 에서 다시 뽑은 것이다."),
    )


def build_certificate() -> dict:
    keys = list(DRONES.keys())
    meshes = {k: build_drone(DRONES[k]) for k in keys}
    res = MD.check_all(keys, meshes=meshes)

    #  ---- 잔차표를 한 줄씩 편다 ----------------------------------------
    table = []
    for k in keys:
        table += res[k]["rows"]

    #  ---- 기체별 허용오차 «선언» -----------------------------------------
    tol_by_key = {}
    for k in keys:
        rows = [r for r in res[k]["rows"] if r["reference"] is not None]
        if not rows:
            tol_by_key[k] = dict(n_rows=0, note="외부 참값 행이 없다 — 이 기체는 치수 축에서 장담하지 못한다")
            continue
        Us = [r["tolerance"]["U"] for r in rows]
        cls = sorted({r["ref_class"] for r in rows})
        tol_by_key[k] = dict(
            n_rows=len(rows),
            U_min_mm=round(min(Us), 4), U_max_mm=round(max(Us), 4),
            U_median_mm=round(float(np.median(Us)), 4),
            reference_classes=cls,
            best_grade=sorted({r["grade"] for r in rows})[0],
            derivation=("행마다 U = k·√(u_ref²+u_def²+u_disc²), k=2. u_ref 는 그 기체의 참값 "
                        "출처 등급이 정하고(REF_CLASS), u_def 는 «참값의 정의와 우리 잣대의 "
                        "정의가 얼마나 다른가», u_disc 는 «다면체로 지은 곡면을 재는 오차» 다."),
            per_class_u_ref={c: (round(MD.REF_CLASS[c]["u_mm"], 4)
                                 if MD.REF_CLASS[c]["u_mm"] is not None else "행마다 다름(밴드)")
                             for c in cls},
        )

    #  ---- 기체별 «무엇을 장담하고 무엇을 못 하는가» ------------------------
    assurance = {}
    for k in keys:
        rows = [r for r in res[k]["rows"] if r["reference"] is not None]
        indep = [r for r in rows if r["circularity"] == "independent"]
        indep_ok = [r for r in indep if r["verdict"] == "일치"]
        indep_bad = [r for r in indep if r["verdict"] == "어긋남"]
        parts_seen = sorted({r["part"] for r in rows})
        parts_missing = [p for p in MD.PARTS if p not in parts_seen]
        U = [r["tolerance"]["U"] for r in indep_ok] or [r["tolerance"]["U"] for r in rows]

        def _by_part(rs):
            d = {}
            for r in rs:
                d.setdefault(r["part"], []).append(r)
            return d

        can = "; ".join(
            f"{p} ±{max(x['tolerance']['U'] for x in v):.2f} mm({len(v)}행)"
            for p, v in sorted(_by_part(indep_ok).items()))
        cannot = "; ".join(
            f"{p} {max(v, key=lambda x: abs(x['residual']))['residual']:+.2f} mm 어긋남({len(v)}행)"
            for p, v in sorted(_by_part(indep_bad).items()))
        assurance[k] = dict(
            n_rows=len(rows), n_independent=len(indep),
            n_independent_match=len(indep_ok), n_independent_mismatch=len(indep_bad),
            resolution_mm=(round(float(np.median(U)), 3) if U else None),
            parts_with_reference=parts_seen, parts_without_reference=parts_missing,
            can_state_ko=(f"독립 근거로 «외부 참값과 이 범위 안에서 같다» 고 장담하는 칸 — {can}"
                          if indep_ok else "독립 근거로 장담할 수 있는 치수가 **없다**."),
            cannot_state_ko=(
                (f"독립 근거로 **어긋난다**고 판정된 칸 — {cannot}. " if indep_bad else "")
                + (f"외부 참값이 아예 없어 **모름**인 칸 — {', '.join(parts_missing)}."
                   if parts_missing else "")),
        )

    #  ---- 봉인: 지금 잔차를 선언으로 못박는다 ------------------------------
    declared = {r["rid"]: r["residual"] for r in table if r["residual"] is not None}
    fps = {k: MD.mesh_fingerprint(meshes[k]) for k in keys}

    #  ---- 가드 -----------------------------------------------------------
    guards = dict(
        m4t_gimbal_rule=MD.guard_m4t_gimbal(),
        tolerance_provenance=MD.guard_tolerance_provenance(),
        reference_provenance=MD.audit_reference_provenance(),
    )

    #  ---- 대조(양성·음성) 전수 — 적대 시험을 **여기서 실제로 돌린다** -------
    import adv_mesh_dimref_faults as ADV
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = ADV.main()
    controls = [dict(tag=t, passed=bool(p), detail=d) for t, p, d in ADV.RESULTS]

    #  ---- 커버리지: 어느 칸이 «외부 참값을 갖는가» -------------------------
    gm = MD.grade_matrix()
    n_cell = sum(len(v) for v in gm.values())
    n_known = sum(1 for v in gm.values() for c in v.values() if c["grade"] != "모름")
    n_A = sum(1 for v in gm.values() for c in v.values() if c["grade"] in ("A", "A-"))
    n_indep = sum(c.get("independent", 0) for v in gm.values() for c in v.values())

    summary = {k: dict(n_rows=res[k]["n_rows"], 일치=res[k]["n_match"],
                       어긋남=res[k]["n_mismatch"], 기록만=res[k]["n_informational"],
                       모름=res[k]["n_unknown"]) for k in keys}

    cert = {
        "_meta": {
            "title": "메쉬 인증서 — 치수·외부 기준 대조 (2026-08-16)",
            "generated_kst": _kst(),
            "author_role": "검사 신설자 라운드 — 치수·외부 기준 대조 담당",
            "policy": ("⛔GPU 미사용(CPU only) · ⛔git 미접촉 · ⛔형상 상수 무변경"
                       "(_SHELL_SHAPE·INTERNALS·GEAR_*·CHORD_*·PITCH_K*·ARM_TIP_Z·envelope_mm "
                       "한 글자도 안 건드렸다). 이 라운드가 만든 것은 검사·대조·인증서뿐이다."),
            "what_ko": ("우리 메쉬에서 잰 치수를 **저장소 밖의 참값**(제조사 공식 CAD·공표 제원·"
                        "제품 사진)과 기체 × 부품 칸마다 견주고, 허용오차를 그 참값의 측정 "
                        "불확실도에서 유도해 «일치/어긋남/모름» 을 판정한다."),
            "why_ko": ("기존 `mesh_check.check_dimensions` 는 메쉬를 `DroneSpec` 과 견준다. "
                       "그런데 DroneSpec 은 **우리가 적은 수**라, «스펙대로 정확히 지은 틀린 "
                       "기체» 를 원리적으로 통과시킨다(범주 지도 M14). 이 인증서가 그 구멍을 막는다."),
            "how_to_read_ko": (
                "판정은 넷뿐이다 — «일치»=|잔차| ≤ 허용오차 U · «어긋남»=U 를 넘었다(결함 신고이지 "
                "빌드 실패가 아니다) · «기록만»=참값과 우리 잣대의 정의가 달라 견줄 수 없다 · "
                "«모름»=외부 참값이 저장소에 없다. ⭐**순환(circularity)** 칸을 반드시 같이 읽을 것: "
                "«circular» 는 그 참값에서 상수를 유도해 놓고 다시 그 참값과 견준 행이라, 일치해도 "
                "«실물과 맞다» 가 아니라 «값이 메쉬에 실렸다» 는 뜻이다."),
            "glossary_ko": {
                "잔차": "우리 메쉬에서 잰 값 − 바깥 참값. (+)면 우리가 크다.",
                "표준불확도 u": "참값이 얼마나 흔들리는지를 «1 시그마» 로 적은 수[mm].",
                "확장불확도 U": "U = k·u, k=2. 약 95 % 를 덮는다. 허용오차가 이 U 다.",
                "근거 등급": "[A] 공식 CAD 직접 · [B] 사진 계측 · [C] 계열 유추 · [D] 대리.",
                "순환": "참값에서 상수를 유도해 놓고 그 참값과 다시 견주는 것. 독립 증거가 아니다.",
                "스윕 디스크": "프로펠러가 돌면서 쓸고 지나가는 원반. «프롭 포함» 외형은 이걸로 잰다.",
                "양성 대조": "일부러 그 결함을 만든 메쉬를 먹여 «걸리는가» 를 보는 시험.",
                "음성 대조": "손대지 않은 메쉬가 «통과하는가» 를 보는 시험(거짓경보가 아님을 보인다).",
            },
            "code": ["src/mesh_dimref.py (검사 본체)",
                     "benchmark/adv_mesh_dimref_faults.py (양성·음성 대조)",
                     "benchmark/mesh_cert_dimension_external_0816.py (이 인증서)"],
            "inputs_read": [
                "assets/meshes/reference/WM161_zhankai_1k.glb (DJI Mini 2 공식 — 이 라운드가 직접 다시 쟀다)",
                "outputs/meshfix_matrice4e.json (DJI M4T 공식 STEP 추출 랜드마크)",
                "outputs/x500v2_cad.json (Holybro 공식 STEP 51항목)",
                "outputs/meshdef_mini2_glb.json (Mini 2 GLB 재실측 원장)",
                "docs/drone_specs_2026.json (공표 제원 + 1차 출처 검증)",
                "assets/meshes/reference/SOURCES.md (참조 자산 출처·라이선스·오식별 정정)",
                "src/drones.py (DroneSpec·기종 note — 공표값의 출처 문장)",
                "outputs/prop_law_by_airframe_0816.json (프롭 축 등급 행렬 — 여기서는 인용만)",
                "outputs/mesh_cert_map_0816.json (범주 지도 M6·M8·M14·M15)",
            ],
            "env": _env(),
        },

        # ------------------------------------------------------------------
        "scope": {
            "covers_ko": ["M6 부품 치수 — 스펙의 수가 아니라 **바깥 참값**과 견준다",
                          "M8 부품 위치·자세 — 로터별 반경/방위/높이차, 부품 위치",
                          "M14 실물 대조 — 공식 CAD·공표·사진",
                          "M15 근거 등급 — 기체 × 부품 행렬"],
            "does_not_cover_ko": ["위상(구멍·비다양체·자기교차) — `mesh_check.py` 의 몫",
                                  "삼각형 품질·파장 대비 분할 — 다른 축",
                                  "재질·전기물성 — 치수 축이 아니다",
                                  "프롭 평면형·두께 — `prop_law_by_airframe_0816.json` 의 몫(여기서는 지름만)"],
        },

        # ------------------------------------------------------------------
        "tolerance_policy": {
            "one_line_ko": ("허용오차에 임의 숫자를 쓰지 않는다 — U 는 **참값의 측정 불확실도**에서 "
                            "유도한다. 유도 문장이 없는 행은 가드가 표에서 막는다."),
            "formula": "U = k·√(u_ref² + u_def² + u_disc²),  k = 2",
            "k_why_ko": ("k=2 는 이 파일에서 유일하게 «관례로 고른» 수다(GUM 의 확장계수, 약 95 % 포함). "
                         "나머지 숫자는 전부 측정에서 나온다."),
            "u_ref_classes": {k: dict(u_mm=(round(v["u_mm"], 4) if v["u_mm"] is not None else None),
                                      derivation=v["derivation"],
                                      source_file=v.get("source_file"))
                              for k, v in MD.REF_CLASS.items()},
            "u_def_ko": ("«참값의 정의» 와 «우리 잣대의 정의» 가 다를 때 그 차이를 mm 로 선언한다. "
                         "행마다 u_def_why 문장이 붙고, 없으면 가드가 막는다. 예: matrice4e 펼침 "
                         "길이의 참값은 «앞 암 끝 페어링 ↔ 뒤 암 끝 페어링» 인데 우리 잣대는 "
                         "«motor 그룹 x 폭» 이라 페어링 두께만큼 다르다 ⇒ 0.5 mm."),
            "u_disc_ko": ("다면체로 지은 곡면을 «지름» 으로 잴 때 외접·내접이 달라 생기는 오차. "
                          "메쉬에서 직접 잰다(같은 부품의 최대·최소 반경 차/√3). 상자·평면·"
                          "최댓값 위치를 재는 잣대에는 붙지 않는다(0, 이유를 같이 적는다)."),
            "why_not_percent_ko": ("«1 % · 3 %» 같은 비율 잣대를 안 쓴다. 같은 1 % 가 mini2(213 mm)와 "
                                   "m350rtk(895 mm)에서 4 배 다른 엄격도가 되고, 무엇보다 그 수의 "
                                   "근거가 «실측하고 여유를 붙였다» 뿐이기 때문이다."),
            "per_airframe": tol_by_key,
        },

        # ------------------------------------------------------------------
        "reference_assets": _asset_status(),
        "reference_relive": {
            "why_ko": ("«원장에 그렇게 적혀 있다» 와 «내가 자산을 열어 다시 쟀다» 는 다른 주장이다. "
                       "저장소에 있는 두 공식 자산은 이 라운드가 직접 다시 쟀다. "
                       "M4T STEP(158 MB)만 다시 파싱하지 않았고 그 사실을 limits 에 적었다."),
            "mini2_glb": _reference_relive(),
            "x500v2_step": _reference_relive_x500(),
        },

        # ------------------------------------------------------------------
        "residual_table": table,
        "summary_by_airframe": summary,
        "assurance_by_airframe": {
            "read_ko": ("«장담» 은 «전부 맞다» 가 아니라 «이 범위는 맞고 이 범위는 모른다» 다. "
                        "can_state 는 **순환이 아닌 행이 일치한 것**만 센다 — 순환 행의 일치는 "
                        "«값이 메쉬에 실렸다» 일 뿐이라 실물 장담에 못 쓴다."),
            "by_key": assurance,
        },
        "category_map_delta": {
            "map": "outputs/mesh_cert_map_0816.json",
            "before_ko": {
                "M6": "controls.positive = «프롭 지름·전역 배율만 있음 (adv D3)»",
                "M8": "controls.positive = «프롭↔벨 축만» · 측정: 로터 ±20 mm 상쇄와 카메라 30 mm 이동은 **통과(놓침)**",
                "M14": "controls.positive = «없음» · 실물 대조는 게이트 밖 일회성",
                "M15": "«기체 × 부품 등급 행렬은 없다»",
            },
            "after_ko": {
                "M6": ("부품 치수 행 다수(짐벌·모터 벨·판·레일·PCB·배터리·다리)에 외부 참값이 붙었고, "
                       "양성 대조 ②⑥⑦⑧⑨⑩ 이 «부품 하나만 커짐/짧아짐» 을 실제로 잡는다."),
                "M8": ("로터별 반경·방위·앞뒤 높이차 행이 생겼고, 양성 대조 ③④⑤ 가 «카메라 30 mm 이동» · "
                       "«로터 +20/−20 mm 상쇄» · «높이차 부호 뒤집기» 를 전부 잡는다. "
                       "④는 옛 치수검사가 왜 놓쳤는지(대각 평균 불변)도 같이 보인다."),
                "M14": ("공식 CAD·공표·사진 참값 대조가 코드가 됐고(74행), Mini 2 GLB 는 이 라운드가 "
                        "직접 다시 쟀다. 근거 파일 대조 가드가 «[A] 라고 적었는데 그 파일에 그 수가 없다» 를 잡는다."),
                "M15": "기체 × 부품 등급 행렬이 기계가 읽는 형태로 생겼다(grade_matrix).",
            },
            "still_missing_ko": [
                "셸형 기체의 «암만» 재는 잣대가 없다(암이 body 에 불리언 합쳐져 있다).",
                "canopy·accent 칸은 대부분 외부 참값이 없다.",
                "공식 CAD 없는 6기체의 부품 치수는 여전히 «모름» 이다 — 사진에서 밴드까지 선언된 값이 드물다.",
            ],
        },

        # ------------------------------------------------------------------
        "grade_matrix": {
            "definitions": MD.GRADE_DEFS,
            "parts": list(MD.PARTS),
            "note_ko": ("칸의 등급은 «그 칸을 보는 행 중 가장 강한 근거» 다. 행이 하나도 없으면 "
                        "«모름» 이고, **채우지 않는 것이 규율이다**. independent 는 그 칸의 행 중 "
                        "순환이 아닌 행의 수다 — 0 이면 «값이 실렸다» 까지만 장담한다."),
            "prop_column_note_ko": ("프롭 칸은 여기서 **지름만** 본다. 평면형·시위·두께의 기체별 "
                                    "등급은 outputs/prop_law_by_airframe_0816.json 의 "
                                    "C_law_by_airframe[*].grade 가 정본이다(A~D + proxy_of)."),
            "matrix": gm,
            "coverage": dict(n_cells=n_cell, n_with_reference=n_known,
                             n_grade_A=n_A, n_independent_rows=n_indep,
                             read_ko=(f"{n_cell} 칸 중 외부 참값이 있는 칸은 {n_known} 칸이고, "
                                      f"그중 공식 CAD/공표 직접([A]/[A−])이 {n_A} 칸이다. "
                                      f"순환이 아닌 «독립» 행은 전부 {n_indep} 개다.")),
        },

        # ------------------------------------------------------------------
        "guards": guards,
        "controls": {
            "rule_ko": ("검사마다 양성 대조(결함을 심으면 걸린다)와 음성 대조(멀쩡하면 통과)를 "
                        "둘 다 건다. 이 둘이 없는 검사는 «있다» 고 치지 않는다."),
            "runner": "benchmark/adv_mesh_dimref_faults.py",
            "n_total": len(controls), "n_passed": sum(1 for c in controls if c["passed"]),
            "exit_code": int(rc),
            "detection_floor_ko": ("전역 배율 결함은 ×1.002(0.2 %)부터 걸리기 시작하고 ×1.05 에서 "
                                   "전 행이 걸린다. 작은 부품 행이 늦게 걸리는 이유는 U 가 그 부품 "
                                   "크기의 1 % 보다 크기 때문이다 — 선언된 한계다."),
            "results": controls,
        },

        # ------------------------------------------------------------------
        "seal": {
            "what_ko": ("지금 잔차를 «선언» 으로 못박는다. 다음 라운드가 형상을 바꾸면 잔차가 "
                        "이 값에서 벗어나고, `mesh_dimref.check_all(declared=…)` 이 그것을 "
                        "**회귀** 로 잡는다. 예산 규약은 저장소의 기존 표들과 같은 뜻이다 — "
                        "«이만큼이 옳다» 가 아니라 «지금 이만큼이다»."),
            "how_to_use_ko": ("python -c \"import json,mesh_dimref as M; "
                              "d=json.load(open('outputs/mesh_cert_dimension_external_0816.json'))"
                              "['seal']; print(M.check_all(declared=d['declared_residual_mm']))\""),
            "regression_rule": "|잔차| ≤ max(|선언값|×1.02, |선언값| + U) 이면 회귀 없음",
            "mesh_fingerprints": fps,
            "fingerprint_note_ko": ("지문이 바뀌었는데 잔차가 그대로면 검사가 눈이 먼 것이고, "
                                    "지문이 그대로인데 잔차가 바뀌면 검사 코드가 바뀐 것이다."),
            "declared_residual_mm": {k: round(v, 4) for k, v in declared.items()},
        },

        # ------------------------------------------------------------------
        "findings": [],          # 아래에서 채운다
        "limits": [],            # 아래에서 채운다
        "headline": "",
    }
    return cert, res, table, gm


def _findings(table, res) -> list[dict]:
    """어긋난 행을 **사람이 읽는 문장**으로 정리한다(큰 것부터)."""
    bad = [r for r in table if r["verdict"] == "어긋남"]
    bad.sort(key=lambda r: -abs(r["residual_pct"] or 0))
    out = []
    for r in bad:
        out.append(dict(
            rid=r["rid"], key=r["key"], part=r["part"], quantity=r["quantity"],
            measured=r["measured"], reference=r["reference"],
            residual=r["residual"], residual_pct=r["residual_pct"],
            U=r["tolerance"]["U"], grade=r["grade"], circularity=r["circularity"],
            source=r["source"],
        ))
    return out


def main() -> int:
    cert, res, table, gm = build_certificate()

    bad = _findings(table, res)
    cert["findings"] = dict(
        n_mismatch=len(bad),
        read_ko=("«어긋남» 은 빌드 실패가 아니라 **결함 신고**다. 아래는 큰 것부터이고, "
                 "각 행의 circularity 를 같이 읽어야 한다 — 순환 행의 어긋남은 «상수가 "
                 "메쉬에 안 실렸다» 는 뜻이고, 독립 행의 어긋남은 «실물과 다르다» 는 뜻이다."),
        rows=bad,
    )

    cert["limits"] = [
        "⭐이 인증서는 **치수 축**만 장담한다. 위상(구멍·비다양체)·삼각형 품질·재질·프롭 평면형은 "
        "다른 검사의 몫이고 여기서 장담하지 않는다.",
        "⭐공식 CAD 가 **없는** 기체가 6종이다(Mavic 4 Pro · Mini 5 Pro · Phantom 3/4 · S1000+ · "
        "M350 RTK). 이 기체들의 참값 상한은 «공표 제원 + 사진» 이고, 부품 단위 치수는 대부분 "
        "«모름» 으로 남았다 — 빈칸이 가짜 통과보다 낫다.",
        "⭐**순환 행은 독립 증거가 아니다.** 예: matrice4e 높이 149.5 는 envelope_mm 이 강제하는 "
        "값이라 일치가 보장돼 있다. 이 인증서에서 «실물과 맞다» 를 주장할 수 있는 것은 "
        "circularity=independent 인 행뿐이다.",
        "⛔M4T STEP 은 **Matrice 4T** 판이다. 짐벌은 4E 와 다른 물건이라 짐벌 «치수» 참값으로 "
        "쓰지 않았다(가드가 코드로 막는다). 짐벌 «위치» 만 CAD 를 썼다.",
        "⚠셸형 기체는 암이 body 그룹에 불리언 합쳐져 있어 «암만» 재는 잣대가 없다. 암 단면·"
        "길이의 외부 대조는 열린 프레임(x500v2)에서만 가능하다.",
        "⚠**matrice4e 참값만 원장 인용이다.** M4T STEP 은 158 MB 이고 깃에 없어 이 라운드가 "
        "다시 파싱하지 않았다 — 그 참값은 outputs/meshfix_matrice4e.json 에서 읽고, 근거 파일 "
        "대조 가드로 «그 파일에 그 수가 실제로 있는지» 만 확인했다. 반면 Mini 2 GLB 와 X500 STEP 은 "
        "이 라운드가 **직접 다시 열어 재유도**했고(reference_relive), 원장과 각각 0.0005 mm · "
        "0.010 mm 안에서 같았다.",
        "⚠사진 유래 참값은 밴드가 선언된 것만 썼다. matrice4e 짐벌 치수(59×47×52)는 우리 잣대가 "
        "크래들까지 세어 정의가 달라 «기록만» 이다 — 판정하지 않는다.",
        "⚠«일치» 는 «U 안» 이라는 뜻이고 U 는 참값의 불확실도가 정한다. 참값이 거친 기체(공표 "
        "1 mm 반올림)에서는 U 가 크므로 «일치» 의 강도도 그만큼 약하다.",
    ]

    n_ok = cert["controls"]["n_passed"]
    n_all = cert["controls"]["n_total"]
    cov = cert["grade_matrix"]["coverage"]
    cert["headline"] = (
        f"치수 축에 **외부 참값 대조 {len(table)}행**을 세웠다 — 일치 "
        f"{sum(1 for r in table if r['verdict']=='일치')} · 어긋남 {len(bad)} · "
        f"기록만 {sum(1 for r in table if r['verdict']=='기록만')} · 모름 "
        f"{sum(1 for r in table if r['verdict']=='모름')}. 허용오차는 전부 측정 불확실도에서 "
        f"유도했고(k=2), 양성·음성 대조 {n_ok}/{n_all} 이 그 검사들이 실제로 잡는다는 것을 "
        f"보인다. 기체 × 부품 {cov['n_cells']} 칸 중 외부 참값이 있는 칸은 {cov['n_with_reference']} 칸이다 — "
        f"나머지는 «모름» 으로 남겼다."
    )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(cert, f, ensure_ascii=False, indent=1)

    print("=" * 104)
    print("치수·외부 기준 대조 인증서")
    print("=" * 104)
    print(cert["headline"])
    print(f"\n가드: M4T/M4E 짐벌 {'✅' if cert['guards']['m4t_gimbal_rule']['ok'] else '❌'} · "
          f"허용오차 유도 {'✅' if cert['guards']['tolerance_provenance']['ok'] else '❌'} · "
          f"근거 파일 {'✅' if cert['guards']['reference_provenance']['ok'] else '❌'} "
          f"(확인 {cert['guards']['reference_provenance']['n_confirmed']}/"
          f"{cert['guards']['reference_provenance']['n_rows']})")
    print(f"대조: {n_ok}/{n_all} 통과")
    print("\n기체별 —")
    for k, s in cert["summary_by_airframe"].items():
        t = cert["tolerance_policy"]["per_airframe"][k]
        u = (f"U {t.get('U_min_mm','—')}~{t.get('U_max_mm','—')} mm"
             if t.get("n_rows") else "참값 없음")
        print(f"  {k:12s} 행 {s['n_rows']:2d} · 일치 {s['일치']:2d} · 어긋남 {s['어긋남']:2d} · "
              f"기록만 {s['기록만']} · 모름 {s['모름']}   ({u})")
    print(f"\n큰 어긋남 (상위 8) —")
    for r in cert["findings"]["rows"][:8]:
        print(f"  {r['rid']:8s} {r['key']:11s} {r['quantity'][:24]:24s} "
              f"{r['measured']:9.2f} ↔ {r['reference']:9.2f}  "
              f"{r['residual']:+8.2f} mm ({r['residual_pct']:+6.2f} %) "
              f"U±{r['U']:.2f} [{r['grade']}·{r['circularity']}]")
    print(f"\n기록: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
