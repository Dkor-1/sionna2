# -*- coding: utf-8 -*-
"""
adv_mesh_dimref_faults.py — **치수·외부 대조 검사기를 검사한다**
==============================================================================
왜 필요한가 (2026-08-16 인증 라운드)
  범주 지도(`outputs/mesh_cert_map_0816.json`)가 M6·M8·M14·M15 칸에 대해 이렇게 적었다:
    «부품 하나만 봉투 안에서 커지면 걸리는 검사가 없다 · 카메라를 30 mm 옮겨도 통과 ·
      로터 둘을 +20/−20 mm 어긋내도 평균이 같아 통과 · 실물 대조는 게이트 밖 일회성»
  `src/mesh_dimref.py` 가 그 칸들을 채운다. 그런데 **검사가 있다는 말은 «잡는다»가 증명돼야
  성립한다.** 그래서 이 파일이 결함을 **실제로 심어** 먹인다.

규약 — 검사마다 두 번 묻는다 (기존 `adv_mesh_check_faults.py` 와 같은 형식)
  · **음성 대조**: 손대지 않은 메쉬에서 그 행의 판정이 **기준선 그대로**인가 (거짓경보 없음)
  · **양성 대조**: 그 결함을 심으면 **바로 그 행이** 어긋나는가 (다른 행이 우연히 잡는 것은 인정 안 함)

⚠ 심는 결함은 **메모리 안의 메쉬 사본**에만 적용한다. 형상 상수(_SHELL_SHAPE·INTERNALS·
  GEAR_*·CHORD_*·envelope_mm …)는 한 글자도 안 건드린다. 파일도 안 쓴다.

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/adv_mesh_dimref_faults.py
      ⛔ GPU 안 쓴다. 나가는 값: 전부 잡으면 0, 하나라도 놓치면 1.
"""
from __future__ import annotations

import copy
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

import mesh_dimref as MD                                  # noqa: E402
from drones import DRONES, build_drone, rotor_layout      # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
_MESH: dict[str, object] = {}


def _say(tag: str, passed: bool, detail: str):
    RESULTS.append((tag, passed, detail))
    print(f"  {'✅' if passed else '❌'} {tag:44s} {detail}")


def mesh(key: str):
    """기준 메쉬(한 번만 짓는다)."""
    if key not in _MESH:
        _MESH[key] = build_drone(DRONES[key])
    return _MESH[key]


def verdicts(key: str, m=None) -> dict:
    r = MD.check_key(key, mesh=m if m is not None else mesh(key))
    return {row["rid"]: row for row in r["rows"]}


# --------------------------------------------------------------------------- #
#  결함 심는 도구 — 전부 메쉬 사본 위에서만 논다
# --------------------------------------------------------------------------- #
def _V(m):
    return np.asarray(m.v, float)


def _put(m, V):
    m.v = [tuple(map(float, p)) for p in V]
    return m


def scale_all(m, f: float):
    """전역 배율(단위 오류의 작은 판)."""
    out = copy.deepcopy(m)
    return _put(out, _V(out) * f)


def _group_vertex_ids(m, group: str) -> np.ndarray:
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    return np.unique(F[G == group])


def scale_group(m, group: str, f: float):
    """한 부품군만 **자기 무게중심 기준**으로 키운다(봉투 안에서 커지는 결함)."""
    out = copy.deepcopy(m)
    V = _V(out)
    ids = _group_vertex_ids(out, group)
    c = 0.5 * (V[ids].max(0) + V[ids].min(0))
    V[ids] = c + (V[ids] - c) * f
    return _put(out, V)


def move_group(m, group: str, d_mm):
    """한 부품군을 통째로 옮긴다(위치 결함)."""
    out = copy.deepcopy(m)
    V = _V(out)
    ids = _group_vertex_ids(out, group)
    V[ids] += np.asarray(d_mm, float) / 1000.0
    return _put(out, V)


def scale_group_z_from_top(m, group: str, f: float):
    """부품군을 **윗면 고정**으로 z 방향만 줄인다(다리 짧아짐)."""
    out = copy.deepcopy(m)
    V = _V(out)
    ids = _group_vertex_ids(out, group)
    ztop = V[ids][:, 2].max()
    V[ids, 2] = ztop + (V[ids, 2] - ztop) * f
    return _put(out, V)


def _rotor_parts(m, spec, groups=("prop", "motor", "gear")):
    """부품(연결요소)마다 «어느 로터 것인가» 를 붙여 준다."""
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    V = _V(m) * 1000.0
    ctr = np.asarray([r["center"] for r in rotor_layout(spec)], float) * 1000.0
    out = []
    for g in groups:
        if not (G == g).any():
            continue
        for c in MD._components(F[G == g]):
            ids = np.unique(c)
            P = V[ids]
            xy = np.array([P[:, 0].mean(), P[:, 1].mean()])
            i = int(np.linalg.norm(ctr[:, :2] - xy, axis=1).argmin())
            out.append((i, g, ids))
    return out


def move_rotor_radial(m, spec, rotor: int, dr_mm: float):
    """로터 하나의 부품 전체를 **반경 방향으로** 민다."""
    out = copy.deepcopy(m)
    V = _V(out)
    ctr = np.asarray([r["center"] for r in rotor_layout(spec)], float)
    for i, _g, ids in _rotor_parts(out, spec):
        if i != rotor:
            continue
        u = ctr[i, :2] / max(np.linalg.norm(ctr[i, :2]), 1e-12)
        V[ids, 0] += u[0] * dr_mm / 1000.0
        V[ids, 1] += u[1] * dr_mm / 1000.0
    return _put(out, V)


def flip_rotor_z(m, spec):
    """앞·뒤 로터의 높이차 부호를 뒤집는다(rotor_z_mm 부호 결함)."""
    out = copy.deepcopy(m)
    V = _V(out)
    ctr = np.asarray([r["center"] for r in rotor_layout(spec)], float)
    zs = {}
    for i, _g, ids in _rotor_parts(out, spec, groups=("prop",)):
        zs[i] = V[ids][:, 2].mean()
    if not zs:
        return out
    zmid = float(np.mean(list(zs.values())))
    for i, _g, ids in _rotor_parts(out, spec):
        dz = 2.0 * (zmid - zs.get(i, zmid))
        V[ids, 2] += dz
    return _put(out, V)


def scale_rotor_prop(m, spec, rotor: int, f: float):
    """로터 하나의 프로펠러만 키운다."""
    out = copy.deepcopy(m)
    V = _V(out)
    ctr = np.asarray([r["center"] for r in rotor_layout(spec)], float)
    for i, g, ids in _rotor_parts(out, spec, groups=("prop",)):
        if i != rotor:
            continue
        c = np.array([ctr[i, 0], ctr[i, 1]])
        V[ids, :2] = c + (V[ids, :2] - c) * f
    return _put(out, V)


def split_plates(m, dz_mm: float):
    """열린 프레임의 위판을 들어올린다(판 간격 결함)."""
    out = copy.deepcopy(m)
    V = _V(out)
    F = np.asarray(out.f, np.int64)
    G = np.asarray(out.g)
    for c in MD._components(F[G == "deck"]):
        ids = np.unique(c)
        P = V[ids] * 1000.0
        sz = P.max(0) - P.min(0)
        a, b = min(sz[0], sz[1]), max(sz[0], sz[1])
        if b > 0 and a / b >= 0.8 and sz[2] <= 0.1 * a and P[:, 2].mean() > 0:
            V[ids, 2] += dz_mm / 1000.0
    return _put(out, V)


# --------------------------------------------------------------------------- #
#  ① 전역 배율 — 단위/축척 축 (범주 M1)
# --------------------------------------------------------------------------- #
def test_global_scale(key="mini2"):
    base = verdicts(key)
    ok0 = [r for r in base.values() if r["verdict"] == "일치"]
    _say(f"①음성 {key} 원본", len(ok0) >= 8,
         f"일치 {len(ok0)}행 / 어긋남 {sum(1 for r in base.values() if r['verdict']=='어긋남')}행")

    bad = verdicts(key, scale_all(mesh(key), 1.01))
    flipped = [k for k, v in bad.items()
               if v["verdict"] == "어긋남" and base[k]["verdict"] == "일치"]
    _say("①양성 전역 ×1.01 (1 % 크게)", len(flipped) >= 3,
         f"일치→어긋남 {len(flipped)}행: {flipped}")

    #  ⭐ **탐지 하한을 잰다** — «잡는다» 만 말하고 «얼마나 작은 것까지» 를 안 적으면
    #     장담이 반쪽이다. 배율을 키워 가며 처음 걸리는 지점과 전부 걸리는 지점을 찾는다.
    ladder, first, allrow = [], None, None
    for f in (1.001, 1.002, 1.005, 1.01, 1.02, 1.05):
        v = verdicts(key, scale_all(mesh(key), f))
        n = sum(1 for k, x in v.items()
                if x["verdict"] == "어긋남" and base[k]["verdict"] == "일치")
        ladder.append((f, n))
        n_could = sum(1 for x in base.values() if x["verdict"] == "일치")
        if first is None and n >= 1:
            first = f
        if allrow is None and n == n_could:
            allrow = f
    _say("①양성 탐지 하한 사다리", first is not None and first <= 1.005,
         "배율→적발행 " + " ".join(f"{f:.3f}:{n}" for f, n in ladder)
         + f" ⇒ 처음 걸리는 배율 {first}, 전부 걸리는 배율 {allrow}"
         + "  (작은 부품 행은 U 가 그 부품 크기의 1 % 보다 커서 늦게 걸린다 — 선언된 한계)")


# --------------------------------------------------------------------------- #
#  ② 부품 하나만 커짐 — 지도가 «검사 없음» 이라 적은 바로 그 구멍 (M6)
# --------------------------------------------------------------------------- #
def test_part_only_scale(key="mini2"):
    base = verdicts(key)
    bad = verdicts(key, scale_group(mesh(key), "camera", 1.15))
    tgt = ["MI2-08", "MI2-09", "MI2-10"]
    caught = [t for t in tgt if bad[t]["verdict"] == "어긋남" and base[t]["verdict"] == "일치"]
    others = [k for k, v in bad.items()
              if k not in tgt and v["verdict"] == "어긋남" and base[k]["verdict"] == "일치"]
    _say("②양성 짐벌만 ×1.15 (봉투 안에서 커짐)", len(caught) == 3,
         f"짐벌 3행 중 {len(caught)}행 적발 · 잔차 "
         + ", ".join(f"{bad[t]['residual']:+.2f}" for t in tgt))
    _say("②음성 다른 행은 안 흔들림", not others,
         f"엉뚱하게 뒤집힌 행 {len(others)}개 {others}")


# --------------------------------------------------------------------------- #
#  ③ 부품 이동 — «카메라 30 mm 이동은 통과» 를 깬다 (M8)
# --------------------------------------------------------------------------- #
def test_part_translate(key="matrice4e"):
    base = verdicts(key)
    bad = verdicts(key, move_group(mesh(key), "camera", (30.0, 0.0, 0.0)))
    hit = bad["M4E-18"]["verdict"] == "어긋남" and base["M4E-18"]["verdict"] == "일치"
    _say("③양성 짐벌 +30 mm 앞으로", hit,
         f"짐벌 위치 x {base['M4E-18']['measured']:.2f} → {bad['M4E-18']['measured']:.2f} "
         f"(참값 {bad['M4E-18']['reference']}, 허용 ±{bad['M4E-18']['tolerance']['U']:.2f})")
    #  치수 행은 그대로여야 한다 — «이동» 과 «크기» 를 구별한다는 증거
    _say("③음성 이동은 치수 행을 안 건드린다",
         bad["M4E-14"]["verdict"] == base["M4E-14"]["verdict"],
         f"모터 벨 높이 판정 {base['M4E-14']['verdict']} → {bad['M4E-14']['verdict']}")


# --------------------------------------------------------------------------- #
#  ④ 로터 상쇄 이동 — 평균은 그대로, 로터별로는 틀림 (M8 의 대표 사례)
# --------------------------------------------------------------------------- #
def test_rotor_offset(key="matrice4e"):
    base = verdicts(key)
    m = move_rotor_radial(mesh(key), DRONES[key], 0, +20.0)
    m = move_rotor_radial(m, DRONES[key], 2, -20.0)
    bad = verdicts(key, m)
    hit = bad["M4E-10"]["verdict"] == "어긋남"
    _say("④양성 로터0 +20 / 로터2 −20 mm (평균 불변)", hit,
         f"앞 로터 반경 {base['M4E-10']['measured']:.2f} → {bad['M4E-10']['measured']:.2f} "
         f"(참값 227.16, 허용 ±{bad['M4E-10']['tolerance']['U']:.2f})")
    #  ⭐ 옛 검사(mesh_check.check_dimensions)는 이걸 왜 놓쳤나 — 평균 대각이 안 변해서다
    from mesh_check import check_dimensions
    d0 = check_dimensions(DRONES[key], mesh=mesh(key))
    d1 = check_dimensions(DRONES[key], mesh=m)
    _say("④참고 옛 치수검사는 대각 평균만 본다",
         abs(d1["diagonal_err_pct"] - d0["diagonal_err_pct"]) < 0.05,
         f"대각 오차 {d0['diagonal_err_pct']:+.3f} % → {d1['diagonal_err_pct']:+.3f} % (거의 그대로)")


# --------------------------------------------------------------------------- #
#  ⑤ 로터 높이차 부호 뒤집기 (M8 의 z 축)
# --------------------------------------------------------------------------- #
def test_rotor_z(key="mini2"):
    base = verdicts(key)
    bad = verdicts(key, flip_rotor_z(mesh(key), DRONES[key]))
    hit = bad["MI2-07"]["verdict"] == "어긋남" and base["MI2-07"]["verdict"] == "일치"
    _say("⑤양성 앞뒤 로터 높이차 부호 뒤집기", hit,
         f"앞뒤 벨 밑동 차 {base['MI2-07']['measured']:+.2f} → {bad['MI2-07']['measured']:+.2f} mm "
         f"(참값 +21.80)")


# --------------------------------------------------------------------------- #
#  ⑥ 다리 짧아짐 (M6 · gear)
# --------------------------------------------------------------------------- #
def test_gear(key="matrice4e"):
    base = verdicts(key)
    bad = verdicts(key, scale_group_z_from_top(mesh(key), "gear", 0.8))
    hit = bad["M4E-08"]["verdict"] == "어긋남" and base["M4E-08"]["verdict"] == "일치"
    _say("⑥양성 다리 20 % 짧게", hit,
         f"접지점 z {base['M4E-08']['measured']:.2f} → {bad['M4E-08']['measured']:.2f} "
         f"(참값 −59.82, 허용 ±{bad['M4E-08']['tolerance']['U']:.2f})")


# --------------------------------------------------------------------------- #
#  ⑦ 모터 벨 지름 (M6 · motor) — 공식 모터 단품 CAD 가 참값
# --------------------------------------------------------------------------- #
def test_motor_bell(key="x500v2"):
    base = verdicts(key)
    bad = verdicts(key, scale_group(mesh(key), "motor", 1.10))
    hit = bad["X50-06"]["verdict"] == "어긋남" and base["X50-06"]["verdict"] == "일치"
    _say("⑦양성 모터 벨 ×1.10", hit,
         f"벨 지름 {base['X50-06']['measured']:.2f} → {bad['X50-06']['measured']:.2f} mm "
         f"(AIR2216II CAD 28.0, 허용 ±{bad['X50-06']['tolerance']['U']:.2f})")


# --------------------------------------------------------------------------- #
#  ⑧ 판 간격 (M6 · deck) — 열린 프레임의 고유 치수
# --------------------------------------------------------------------------- #
def test_plate_gap(key="x500v2"):
    base = verdicts(key)
    bad = verdicts(key, split_plates(mesh(key), +5.0))
    hit = [t for t in ("X50-03", "X50-04")
           if bad[t]["verdict"] == "어긋남" and base[t]["verdict"] == "일치"]
    _say("⑧양성 위판 +5 mm 들어올리기", len(hit) == 2,
         f"간격 {base['X50-03']['measured']:.2f} → {bad['X50-03']['measured']:.2f} mm "
         f"(CAD 28.0) · 스택 {bad['X50-04']['measured']:.2f} (CAD 32.0)")
    _say("⑧음성 판 한 변·두께는 그대로",
         bad["X50-01"]["verdict"] == "일치" and bad["X50-02"]["verdict"] == "일치",
         f"한 변 {bad['X50-01']['measured']:.2f} · 두께 {bad['X50-02']['measured']:.2f}")


# --------------------------------------------------------------------------- #
#  ⑨ 프롭 하나만 커짐 (M6 · prop)
# --------------------------------------------------------------------------- #
def test_prop_one(key="mini2"):
    base = verdicts(key)
    bad = verdicts(key, scale_rotor_prop(mesh(key), DRONES[key], 0, 1.10))
    hit = bad["MI2-11"]["verdict"] == "어긋남" and base["MI2-11"]["verdict"] == "일치"
    _say("⑨양성 로터0 프롭만 ×1.10", hit,
         f"스윕 지름 평균 {base['MI2-11']['measured']:.2f} → {bad['MI2-11']['measured']:.2f} mm "
         f"(참값 119.23, 허용 ±{bad['MI2-11']['tolerance']['U']:.2f})")


# --------------------------------------------------------------------------- #
#  ⑩ 셸 위치 (M6 · body) — 공식 CAD 랜드마크
# --------------------------------------------------------------------------- #
def test_shell(key="matrice4e"):
    base = verdicts(key)
    bad = verdicts(key, move_group(mesh(key), "body", (5.0, 0.0, 0.0)))
    tgt = ["M4E-04", "M4E-05"]
    hit = [t for t in tgt if bad[t]["verdict"] == "어긋남" and base[t]["verdict"] == "일치"]
    _say("⑩양성 셸 +5 mm 앞으로", len(hit) == 2,
         f"앞끝 {base['M4E-04']['measured']:.2f}→{bad['M4E-04']['measured']:.2f} · "
         f"뒤끝 {base['M4E-05']['measured']:.2f}→{bad['M4E-05']['measured']:.2f} (CAD 159.01 / −75.59)")


# --------------------------------------------------------------------------- #
#  ⑪ 규칙 가드 — M4T/M4E 짐벌 (참값 표 자체를 공격한다)
# --------------------------------------------------------------------------- #
def test_guard_m4t():
    g = MD.guard_m4t_gimbal()
    _say("⑪음성 현재 표는 규칙을 지킨다", g["ok"], f"위반 {g['violations']}")

    bad_row = MD.DimRef(
        rid="XX-01", key="matrice4e", part="camera", quantity="짐벌 폭",
        measure="gimbal_W", ref_mm=59.0, ref_class="cad_m4t", grade="A",
        source="(시험용) M4T CAD 에서 짐벌 치수를 읽었다 — 규칙 위반",
        source_file="outputs/meshfix_matrice4e.json",
        definition="시험용", circularity="independent", u_def_mm=0.0, u_def_why="시험용")
    g2 = MD.guard_m4t_gimbal(MD.REFS + [bad_row])
    _say("⑪양성 짐벌 치수를 M4T CAD 에서 읽으면 걸린다",
         (not g2["ok"]) and g2["violations"] == ["XX-01"],
         f"위반 {g2['violations']}")

    #  ⭐ 위치 행은 계속 허용돼야 한다 — 규칙이 과잉금지가 아님을 보인다
    pos_row = MD.DimRef(
        rid="XX-02", key="matrice4e", part="camera", quantity="짐벌 위치",
        measure="gimbal_cx", ref_mm=148.3, ref_class="cad_m4t", grade="A",
        source="(시험용) 부착 위치", source_file="outputs/meshfix_matrice4e.json",
        definition="시험용", circularity="independent", u_def_mm=0.0, u_def_why="시험용")
    g3 = MD.guard_m4t_gimbal(MD.REFS + [pos_row])
    _say("⑪음성 짐벌 «위치» 는 CAD 를 써도 된다", g3["ok"], f"위반 {g3['violations']}")


# --------------------------------------------------------------------------- #
#  ⑫ 규칙 가드 — 허용오차 유도 강제 (임의 숫자 금지)
# --------------------------------------------------------------------------- #
def test_guard_tolerance():
    g = MD.guard_tolerance_provenance()
    _say("⑫음성 현재 표는 전부 유도 문장을 갖는다", g["ok"], f"위반 {g['violations']}")

    naked = MD.DimRef(
        rid="XX-03", key="mini2", part="body", quantity="아무거나", measure="frame_L",
        ref_mm=100.0, ref_class="pub_1mm", grade="A", source="(시험용)",
        source_file="docs/drone_specs_2026.json", definition="시험용",
        circularity="independent", u_def_mm=3.0, u_def_why="")     # ← 유도 문장이 비었다
    g2 = MD.guard_tolerance_provenance(MD.REFS + [naked])
    _say("⑫양성 근거 없는 허용오차는 표에 못 들어온다",
         (not g2["ok"]) and any(v[0] == "XX-03" for v in g2["violations"]),
         f"위반 {g2['violations']}")

    photo_naked = MD.DimRef(
        rid="XX-04", key="mini2", part="body", quantity="아무거나", measure="frame_L",
        ref_mm=100.0, ref_class="photo", grade="B", source="(시험용)",
        source_file="docs/drone_specs_2026.json", definition="시험용",
        circularity="independent", u_def_mm=0.0, u_def_why="시험용", ref_band_pct=None)
    g3 = MD.guard_tolerance_provenance(MD.REFS + [photo_naked])
    _say("⑫양성 밴드 없는 사진 값도 막힌다",
         (not g3["ok"]) and any(v[0] == "XX-04" for v in g3["violations"]),
         f"위반 {[v for v in g3['violations'] if v[0]=='XX-04']}")


# --------------------------------------------------------------------------- #
#  ⑬ 근거 파일 대조 — «[A] 라고 적었는데 파일이 없다» 를 잡는다 (M15)
# --------------------------------------------------------------------------- #
def test_guard_provenance():
    a = MD.audit_reference_provenance()
    _say("⑬음성 모든 행의 근거 파일이 실재한다", a["ok"],
         f"확인 {a['n_confirmed']}/{a['n_rows']} · 파일없음 {a['n_missing_file']} · "
         f"값미발견 {a['n_value_not_found']}")

    ghost = MD.DimRef(
        rid="XX-05", key="mini2", part="body", quantity="유령", measure="frame_L",
        ref_mm=159.113, ref_class="glb_mini2", grade="A", source="(시험용)",
        source_file="outputs/this_file_does_not_exist_0816.json",
        definition="시험용", circularity="independent", u_def_mm=0.0, u_def_why="시험용")
    a2 = MD.audit_reference_provenance(rows=[ghost])
    _say("⑬양성 없는 파일을 근거로 대면 걸린다",
         (not a2["ok"]) and a2["rows"][0]["status"] == "파일 없음",
         f"판정 «{a2['rows'][0]['status']}»")

    liar = MD.DimRef(
        rid="XX-06", key="mini2", part="body", quantity="거짓값", measure="frame_L",
        ref_mm=1234.567, ref_class="glb_mini2", grade="A", source="(시험용)",
        source_file="outputs/meshdef_mini2_glb.json",
        definition="시험용", circularity="independent", u_def_mm=0.0, u_def_why="시험용")
    a3 = MD.audit_reference_provenance(rows=[liar])
    _say("⑬양성 파일에 없는 수를 «그 파일에서 왔다» 고 하면 걸린다",
         a3["rows"][0]["status"] == "파일은 있으나 값 미발견",
         f"판정 «{a3['rows'][0]['status']}»")


# --------------------------------------------------------------------------- #
#  ⑭ 참값 자체를 흔들어 본다 — 검사가 «참값에 반응하는가»
# --------------------------------------------------------------------------- #
def test_reference_sensitivity(key="mini2"):
    base = verdicts(key)["MI2-04"]
    row = [r for r in MD.REFS if r.rid == "MI2-04"][0]
    shifted = copy.deepcopy(row)
    shifted.ref_mm = row.ref_mm + 3.0
    saved = MD.REFS[MD.REFS.index(row)]
    MD.REFS[MD.REFS.index(row)] = shifted
    try:
        v = verdicts(key)["MI2-04"]
    finally:
        MD.REFS[MD.REFS.index(shifted)] = saved
    _say("⑭양성 참값을 3 mm 흔들면 판정이 뒤집힌다",
         base["verdict"] == "일치" and v["verdict"] == "어긋남",
         f"참값 213.05→216.05 에서 잔차 {base['residual']:+.3f}→{v['residual']:+.3f} mm")
    _say("⑭음성 되돌리면 판정도 되돌아온다",
         verdicts(key)["MI2-04"]["verdict"] == base["verdict"],
         "표를 원상복구했다(다른 시험에 오염 없음)")


# --------------------------------------------------------------------------- #
#  ⑮ 재현성 — 같은 메쉬면 잔차가 **비트 동일**해야 한다 (봉인의 전제)
# --------------------------------------------------------------------------- #
def test_repeatability(key="matrice4e"):
    a = verdicts(key)
    b = MD.check_key(key, mesh=build_drone(DRONES[key]))
    same = all(abs((a[r["rid"]]["measured"] or 0) - (r["measured"] or 0)) < 1e-9
               for r in b["rows"])
    _say("⑮음성 다시 지어도 잔차가 같다", same,
         f"{len(b['rows'])}행 전부 1e-9 mm 안에서 동일")


# --------------------------------------------------------------------------- #
#  ⑯ 봉인 — 「선언된 잔차」가 회귀를 실제로 잡는가
# --------------------------------------------------------------------------- #
def test_seal(key="matrice4e"):
    """인증서가 못박은 «지금 잔차» 를 잣대로 삼아, 형상이 흔들리면 회귀로 걸리는지 본다."""
    base = MD.check_key(key, mesh=mesh(key))
    declared = {r["rid"]: r["residual"] for r in base["rows"] if r["residual"] is not None}

    same = MD.check_key(key, mesh=mesh(key), declared=declared)
    _say("⑯음성 손대지 않으면 회귀 아님", same["regression_ok"],
         f"선언 {len(declared)}행 전부 회귀 없음")

    moved = MD.check_key(key, mesh=move_group(mesh(key), "gear", (0.0, 0.0, -3.0)),
                         declared=declared)
    bad = [r["rid"] for r in moved["rows"] if r.get("regression_ok") is False]
    _say("⑯양성 다리를 3 mm 내리면 회귀로 걸린다",
         (not moved["regression_ok"]) and "M4E-08" in bad,
         f"회귀 적발 {bad}")

    #  지문 — 형상이 바뀌면 지문도 바뀌어야 한다(«낡은 인증서» 를 알아채는 장치)
    fp0 = MD.mesh_fingerprint(mesh(key))
    fp1 = MD.mesh_fingerprint(move_group(mesh(key), "gear", (0.0, 0.0, -3.0)))
    _say("⑯양성 형상이 바뀌면 메쉬 지문도 바뀐다", fp0 != fp1, f"{fp0} → {fp1}")


def main() -> int:
    print("=" * 104)
    print("치수·외부 대조 적대 시험 — 결함을 심어 mesh_dimref 가 «그 행에서» 잡는지 본다")
    print("=" * 104)
    print("\n[① 전역 배율]");           test_global_scale()
    print("\n[② 부품만 커짐]");         test_part_only_scale()
    print("\n[③ 부품 이동]");           test_part_translate()
    print("\n[④ 로터 상쇄 이동]");      test_rotor_offset()
    print("\n[⑤ 로터 높이차 부호]");    test_rotor_z()
    print("\n[⑥ 다리 길이]");           test_gear()
    print("\n[⑦ 모터 벨 지름]");        test_motor_bell()
    print("\n[⑧ 판 간격]");             test_plate_gap()
    print("\n[⑨ 프롭 하나만]");         test_prop_one()
    print("\n[⑩ 셸 위치]");             test_shell()
    print("\n[⑪ 규칙: M4T/M4E 짐벌]");  test_guard_m4t()
    print("\n[⑫ 규칙: 허용오차 유도]"); test_guard_tolerance()
    print("\n[⑬ 규칙: 근거 파일]");     test_guard_provenance()
    print("\n[⑭ 참값 민감도]");         test_reference_sensitivity()
    print("\n[⑮ 재현성]");              test_repeatability()
    print("\n[⑯ 봉인·회귀]");           test_seal()

    n_ok = sum(1 for _, p, _ in RESULTS if p)
    print("\n" + "=" * 104)
    print(f"결과: {n_ok}/{len(RESULTS)} 통과")
    if n_ok < len(RESULTS):
        print("놓친 항목:")
        for tag, p, d in RESULTS:
            if not p:
                print(f"  ❌ {tag} — {d}")
        return 1
    print("⇒ 범주 지도가 «양성 대조 없음» 이라 적은 M6·M8·M14·M15 축에 이제 양성 대조가 있다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
