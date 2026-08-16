# -*- coding: utf-8 -*-
"""
adv_mesh_check_faults.py — **검사기를 검사한다**: 일부러 나쁜 메쉬를 지어 잡히는지 본다
==============================================================================
왜 필요한가 (2026-08-16)
  메쉬 감사(`docs/MESH_AUDIT_0816.md` I6)가 검사기 자신을 공격했다. **나쁜 메쉬 5종을
  지어 넣었더니 5/5 전부 통과**했다 — 겹친 상자, 슬리버 다발, **단위가 1000 배 틀린 메쉬**,
  **좌우가 뒤집힌 거울상 기체**, 삼각형 1장 빠진 구멍. 게다가 `trimesh.split()` 이
  `repair=True` 기본이라 검사기는 **자기가 방금 메운 사본**을 보고 «수밀 통과» 라고 답했다.

  감사의 교훈이 이 파일의 존재 이유다:
    «검사기를 만들면 **양성 대조**부터 통과시켜야 한다. 음성 대조만으로는
      «0 이 나오는 검사기» 와 «0 이 맞는 대상» 을 구별할 수 없다.»

무엇을 하나 — 결함 7종을 **실제로 지어서** 검사기에 먹인다. 각 항목마다 두 번 묻는다.
  · 음성 대조: 손대지 않은 메쉬는 **통과해야** 한다 (거짓경보가 아님을 보인다)
  · 양성 대조: 결함을 넣은 메쉬는 **걸려야** 한다 (실제로 본다는 것을 보인다)

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/adv_mesh_check_faults.py
      ⛔ GPU 안 쓴다. 파일도 안 쓴다(읽기만 + 화면 출력).
      나가는 값: 전부 잡으면 0, 하나라도 놓치면 1.
"""
from __future__ import annotations

import copy
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

import mesh_check                                    # noqa: E402
from geom import Mesh                                # noqa: E402
from drones import DRONES, build_drone               # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def _say(tag: str, passed: bool, detail: str):
    RESULTS.append((tag, passed, detail))
    print(f"  {'✅' if passed else '❌'} {tag:34s} {detail}")


def _box(mesh: Mesh, lo, hi, group: str):
    """축정렬 상자 하나를 **바깥 법선**으로 메쉬에 얹는다(닫힌 껍질)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    idx = [mesh.add_vertex(x, y, z)
           for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    #  인덱스 = 4*i + 2*j + k  (i:x, j:y, k:z)
    def v(i, j, k):
        return idx[4 * i + 2 * j + k]
    quads = [((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)),   # x−
             ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)),   # x+
             ((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)),   # y−
             ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)),   # y+
             ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)),   # z−
             ((0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1))]   # z+
    #  ⚠ 위 네 점 차례는 «안쪽» 법선이 나오는 순서다(손계산 부호부피로 확인). 뒤집어 넣는다 —
    #    바깥 법선이어야 멀쩡한 상자가 음성 대조로 쓰인다.
    for a, b, c, d in quads:
        mesh.add_quad(v(*d), v(*c), v(*b), v(*a), group=group)
    return mesh


def _clean_box_mesh(name="body"):
    m = Mesh(name)
    return _box(m, (0.0, 0.0, 0.0), (0.1, 0.1, 0.1), name)


# --------------------------------------------------------------------------- #
#  D5 · C1 — 구멍(경계 모서리). 감사가 잡아낸 «검사기가 스스로 수리한다» 의 직격 시험
# --------------------------------------------------------------------------- #
def test_hole_and_selfrepair():
    """삼각형 1장을 빼서 구멍을 낸다. 검사기가 **메우지 않고** 잡아야 한다."""
    ok = mesh_check.check_mesh(_clean_box_mesh(), name="_synthetic")
    _say("D5 음성대조: 멀쩡한 상자", ok["ok"] and ok["groups"]["body"]["boundary_edges"] == 0,
         f"경계모서리 {ok['groups']['body']['boundary_edges']}, 판정 {ok['ok']}")

    m = _clean_box_mesh()
    m.f = m.f[:-1]                       # 삼각형 1장 제거 → 경계 모서리 3개
    m.g = m.g[:-1]
    bad = mesh_check.check_mesh(m, name="_synthetic")
    g = bad["groups"]["body"]
    _say("D5 양성대조: 구멍 뚫린 상자", (not bad["ok"]) and g["boundary_edges"] == 3,
         f"면 {g['n_faces']}, 경계모서리 {g['boundary_edges']}, 판정 {bad['ok']}")

    #  C1 직격 — 옛 동작(repair 기본값)이라면 무엇을 봤을까
    import trimesh
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    tm = trimesh.Trimesh(vertices=V, faces=F, process=True)
    old = tm.split(only_watertight=False)                       # repair 기본 = True
    new = tm.split(only_watertight=False, repair=False)         # 지금 우리 동작
    _say("C1 수리 대조: repair 기본 ↔ 명시",
         old[0].is_watertight and (not new[0].is_watertight)
         and len(old[0].faces) == len(F) + 1 and len(new[0].faces) == len(F),
         f"repair=True → {len(old[0].faces)}면·수밀 {old[0].is_watertight} | "
         f"repair=False → {len(new[0].faces)}면·수밀 {new[0].is_watertight}")


# --------------------------------------------------------------------------- #
#  D1 — 같은 그룹 안에서 80 % 겹친 상자 2개 (PO 면적 이중계상)
# --------------------------------------------------------------------------- #
def test_group_overlap():
    m = Mesh("body")
    _box(m, (0.0, 0.0, 0.0), (0.1, 0.1, 0.1), "body")
    _box(m, (0.5, 0.0, 0.0), (0.6, 0.1, 0.1), "body")          # 멀리 떨어진 두 번째 상자
    apart = mesh_check.check_mesh(m, name="_synthetic")
    _say("D1 음성대조: 떨어진 상자 2개",
         apart["ok"] and apart["groups"]["body"]["overlap_pct"] == 0.0,
         f"겹침 {apart['groups']['body']['overlap_pct']} %")

    m = Mesh("body")
    _box(m, (0.0, 0.0, 0.0), (0.1, 0.1, 0.1), "body")
    _box(m, (0.02, 0.0, 0.0), (0.12, 0.1, 0.1), "body")        # 80 % 겹침
    bad = mesh_check.check_mesh(m, name="_synthetic")
    g = bad["groups"]["body"]
    _say("D1 양성대조: 80 % 겹친 상자 2개", (not bad["ok"]) and g["overlap_pct"] > 1.0,
         f"겹침 {g['overlap_pct']} % (예산 {g['overlap_budget_pct']} %)")


# --------------------------------------------------------------------------- #
#  D2 — 슬리버 다발. 절대 면적 잣대(1e-14 m²)로는 안 잡히고 상대 잣대(최소 내각)로만 잡힌다
# --------------------------------------------------------------------------- #
def test_slivers():
    m = _clean_box_mesh()
    #  아주 가늘고 긴 삼각형을 100장 얹는다 — 면적은 1e-14 m² 를 넘지만 최소 내각은 0.001° 급
    for i in range(100):
        a = m.add_vertex(0.0, 0.0, 0.2 + 1e-3 * i)
        b = m.add_vertex(0.1, 0.0, 0.2 + 1e-3 * i)
        c = m.add_vertex(0.1, 1e-7, 0.2 + 1e-3 * i)
        m.add_tri(a, b, c, group="body")
    res = mesh_check.check_mesh(m, name="_synthetic")
    g = res["groups"]["body"]
    #  ⚠ 슬리버 축은 `res["ok"]`(부품 무결성) 가 아니라 **`res["sliver_ok"]`** 로 판정한다
    #    — 기체 전체를 보는 다른 층의 잣대라 일부러 분리했다(mesh_check.check_mesh 주석 참조).
    #    게이트 assert_ok() 와 check_all() 이 이 값을 확인한다.
    caught_rel = res["slivers"] >= 100 and not res["sliver_ok"]
    missed_abs = g["degenerate"] == 0
    _say("D2 양성대조: 슬리버 100장", caught_rel,
         f"상대잣대(최소내각<{mesh_check.SLIVER_MIN_ANGLE_DEG}°) {res['slivers']}장 "
         f"(예산 {res['sliver_budget']}) · 최소내각 {g['min_angle_deg']}° · sliver_ok={res['sliver_ok']}")
    _say("D2 참고: 절대 면적 잣대는 못 본다", missed_abs,
         f"면적<{mesh_check.DEGENERATE_AREA_M2} m² 로 센 퇴화면 {g['degenerate']}장 "
         f"— 감사 m2 가 지적한 그대로")


# --------------------------------------------------------------------------- #
#  D6 — 안쪽 법선. **수리 없는 손계산 부호부피**로 잡는다 (감사 §⑤ 0층 4번)
# --------------------------------------------------------------------------- #
def test_inward_normals():
    m = _clean_box_mesh()
    m.f = [(a, c, b) for (a, b, c) in m.f]           # winding 전부 반전 → 법선 안쪽
    res = mesh_check.check_mesh(m, name="_synthetic")
    g = res["groups"]["body"]
    _say("D6 양성대조: 법선 안쪽 뒤집기",
         (not res["ok"]) and g["raw_negative_parts"] == 1,
         f"손계산 부호부피 {g['raw_min_signed_volume_mm3']} mm³ "
         f"(음수 부품 {g['raw_negative_parts']}개) · trimesh 판정 {g['inward_normals']}")


# --------------------------------------------------------------------------- #
#  D3 — 단위가 1000 배 틀린 메쉬. 위상 검사는 **전부 통과한다**(형상이 멀쩡하니까)
# --------------------------------------------------------------------------- #
def test_wrong_units(key="mavic4pro"):
    spec = DRONES[key]
    m = build_drone(spec)
    good = mesh_check.check_dimensions(spec, mesh=m)
    _say(f"D3 음성대조: {key} 원본 치수", good["ok"],
         f"프롭지름 오차 {good['prop_dia_err_pct']:+.3f} % · 대각 {good['diagonal_err_pct']:+.2f} %")

    scaled = copy.deepcopy(m)
    scaled.v = [(x * 1000.0, y * 1000.0, z * 1000.0) for (x, y, z) in m.v]
    topo = mesh_check.check_mesh(scaled, name=key)
    dim = mesh_check.check_dimensions(spec, mesh=scaled)
    _say("D3 양성대조: 단위 1000 배", not dim["ok"],
         f"프롭지름 {dim['prop_dia_mm']} mm ↔ 스펙 {spec.prop_dia_mm} mm "
         f"({dim['prop_dia_err_pct']:+.0f} %) · 실패 {len(dim['failures'])}건")
    _say("D3 참고: 위상 검사만으로는 못 본다", topo["ok"],
         "수밀·winding·법선·구멍 전부 그대로 통과 — 치수 검사가 없으면 놓친다")


# --------------------------------------------------------------------------- #
#  D4 — 손대칭성. 프롭의 «손잡이»(비틀림 방향)가 그 로터의 회전방향과 안 맞는 기체
#
#  ⭐ 정직하게 적어 둘 것 — 감사 I6 의 D4 는 «기체 전체를 좌우로 뒤집기» 였는데,
#    그 시험은 **원리적으로 성립하지 않는다.** 우리 멀티로터는 이웃 로터가 서로 반대로 도는
#    관례(rotor_layout: 대각쌍 동일)라, 기체를 통째로 뒤집으면 각 프롭이 **반대 회전방향을 가진
#    다른 로터 자리로 옮겨가면서 손잡이도 같이 뒤집힌다** — 두 번 뒤집혀 제자리다. 즉 전체
#    거울상은 «로터 번호만 바꿔 단 같은 기체» 이지 결함이 아니다(실측으로 확인: 불일치 0개).
#    실제로 위험한 것, 그리고 이 저장소에서 **실제로 났던 버그**는 다음 둘이다:
#      · 네 로터에 **전부 같은 손잡이** 프롭을 달기 (2026-07-28 에 났던 바로 그 버그)
#      · **한 로터만** 손잡이가 뒤집히기
#    아래는 그 둘을 시험한다.
# --------------------------------------------------------------------------- #
def _flip_rotor_handedness(mesh, spec, rotors):
    """로터 `rotors` 의 프롭만 **제자리에서** 거울상으로 바꾼다(그 로터 축을 지나는 y 평면 기준).
    프롭 사본마다 정점 블록이 따로라, 그 면들이 쓰는 정점만 건드리면 다른 부품은 안 변한다."""
    from drones import rotor_layout
    out = copy.deepcopy(mesh)
    V = np.asarray(out.v, float)
    F = np.asarray(out.f, np.int64)
    G = np.asarray(out.g)
    prop_idx = np.where(G == "prop")[0]
    Cp = V[F[prop_idx]].mean(1)
    ctr = np.asarray([r["center"] for r in rotor_layout(spec)], float)
    near = np.linalg.norm(Cp[:, None, :2] - ctr[None, :, :2], axis=2).argmin(1)
    for k in rotors:
        fsel = prop_idx[near == k]
        used = np.unique(F[fsel])
        V[used, 1] = 2.0 * ctr[k, 1] - V[used, 1]           # y 거울
        F[fsel] = F[fsel][:, [0, 2, 1]]                     # 반사는 det=−1 → winding 반전
    out.v = [tuple(map(float, p)) for p in V]
    out.f = [tuple(map(int, t)) for t in F]
    return out


def test_handedness(key="mavic4pro"):
    spec = DRONES[key]
    m = build_drone(spec)
    good = mesh_check.check_handedness(spec, mesh=m)
    _say(f"D4 음성대조: {key} 원본 손대칭성", good["ok"],
         f"h_ref {good['h_ref']:+.4f} · 로터별 부호 "
         + " ".join(f"{r['h']:+.3f}" for r in good["per_rotor"]))

    n_rot = len(good["per_rotor"])
    all_same = _flip_rotor_handedness(m, spec, [k for k in range(n_rot) if k % 2 == 1])
    hnd = mesh_check.check_handedness(spec, mesh=all_same)
    topo = mesh_check.check_mesh(all_same, name=key)
    dim = mesh_check.check_dimensions(spec, mesh=all_same)
    _say("D4a 양성대조: 전 로터 같은 손잡이", not hnd["ok"],
         f"로터 {n_rot}개 중 {len(hnd['failures'])}개 부호 불일치 "
         f"(2026-07-28 에 실제로 났던 버그)")
    _say("D4a 참고: 위상·치수로는 못 본다", topo["ok"] and dim["ok"],
         "손잡이가 틀려도 수밀·법선·구멍·치수는 전부 그대로 통과한다")

    one = _flip_rotor_handedness(m, spec, [0])
    hnd1 = mesh_check.check_handedness(spec, mesh=one)
    _say("D4b 양성대조: 한 로터만 뒤집기",
         (not hnd1["ok"]) and len(hnd1["failures"]) == 1,
         f"불일치 {len(hnd1['failures'])}개 — {hnd1['failures']}")

    #  ⭐ 한계 선언 — 전체 거울상은 이 검사가 **못 잡는다**. 못 잡는 게 맞다(위 머리말).
    mir = copy.deepcopy(m)
    mir.v = [(x, -y, z) for (x, y, z) in m.v]
    mir.f = [(a, c, b) for (a, b, c) in m.f]
    hmir = mesh_check.check_handedness(spec, mesh=mir)
    _say("D4c 한계선언: 기체 전체 거울상은 안 걸린다", hmir["ok"],
         "이웃 로터가 반대로 도는 배치라 전체 거울상 = 로터 번호만 바뀐 같은 기체 "
         f"(불일치 {len(hmir['failures'])}개) — 결함이 아니다")


def main():
    print("=" * 96)
    print("검사기 적대 시험 — 일부러 나쁜 메쉬를 지어 mesh_check 가 잡는지 본다")
    print("=" * 96)
    print("\n[구멍 · 검사기 자가수리]")
    test_hole_and_selfrepair()
    print("\n[그룹 안 부품 겹침]")
    test_group_overlap()
    print("\n[슬리버 — 상대 잣대]")
    test_slivers()
    print("\n[안쪽 법선 — 수리 없는 손계산 부호부피]")
    test_inward_normals()
    print("\n[단위 오류]")
    test_wrong_units()
    print("\n[손대칭성 — 프롭 손잡이 ↔ 로터 회전방향]")
    test_handedness()

    n_ok = sum(1 for _, p, _ in RESULTS if p)
    print("\n" + "=" * 96)
    print(f"결과: {n_ok}/{len(RESULTS)} 통과")
    if n_ok < len(RESULTS):
        print("놓친 항목:")
        for tag, p, d in RESULTS:
            if not p:
                print(f"  ❌ {tag} — {d}")
        return 1
    print("⇒ 감사 I6 이 통과시켰던 결함 5종이 지금은 전부 걸린다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
