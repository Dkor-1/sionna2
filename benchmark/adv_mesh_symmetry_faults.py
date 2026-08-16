# -*- coding: utf-8 -*-
"""
adv_mesh_symmetry_faults.py — **대칭·손잡이·파생량 검사기를 검사한다**
==============================================================================
왜 이 파일이 있나
  감사(`docs/MESH_AUDIT_0816.md` I6)의 교훈 그대로다:

    «검사기를 만들면 **양성 대조**부터 통과시켜야 한다. 음성 대조만으로는
      «0 이 나오는 검사기» 와 «0 이 맞는 대상» 을 구별할 수 없다.»

  그래서 `src/mesh_symmetry.py` 의 검사 다섯 축마다 **둘 다** 건다.
    · **음성 대조** — 손대지 않은 메쉬는 **통과해야** 한다 (거짓경보가 아님을 보인다)
    · **양성 대조** — 그 축의 결함을 **실제로 지어 넣으면 걸려야** 한다 (본다는 것을 보인다)

  형식은 기존 `benchmark/adv_mesh_check_faults.py` 를 그대로 따른다.

⛔ 저장소의 형상 상수는 **하나도 안 건드린다.** 결함은 전부 메쉬 **사본**(deepcopy) 이나
   스펙 **사본**(dataclasses.replace) 위에서 짓는다. 원본은 읽기만 한다.

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/adv_mesh_symmetry_faults.py
      ⛔ GPU 안 쓴다. 파일도 안 쓴다(읽기 + 화면 출력).
      나가는 값: 전부 잡으면 0, 하나라도 놓치면 1.
"""
from __future__ import annotations

import copy
import dataclasses
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

import mesh_check                                       # noqa: E402
import mesh_symmetry as msym                            # noqa: E402
from drones import DRONES, build_drone, rotor_layout    # noqa: E402

KEY = "mavic4pro"          # 주력 표적 하나로 대조를 돈다(⭐실측 표적은 mini5pro·matrice4e)
RESULTS: list[dict] = []


def _say(axis: str, kind: str, tag: str, passed: bool, detail: str):
    """kind: '음성'(멀쩡한 것은 통과해야) / '양성'(결함은 걸려야) / '한계'(못 잡는다고 선언) /
             '검정'(자 자체를 닫힌 해에 대 본다)"""
    RESULTS.append(dict(axis=axis, kind=kind, tag=tag, passed=bool(passed), detail=detail))
    print(f"  {'✅' if passed else '❌'} [{kind}] {tag:42s} {detail}")


# --------------------------------------------------------------------------- #
#  결함을 심는 도구 — 전부 **사본** 위에서만 움직인다
# --------------------------------------------------------------------------- #
def _arrays(mesh):
    return (np.asarray(mesh.v, float), np.asarray(mesh.f, np.int64), np.asarray(mesh.g))


def _put(mesh, V, F=None):
    out = copy.deepcopy(mesh)
    out.v = [tuple(map(float, p)) for p in V]
    if F is not None:
        out.f = [tuple(map(int, t)) for t in F]
    return out


def _shift_group(mesh, group, dxyz):
    """그룹 하나를 통째로 평행이동한다(단위 m)."""
    V, F, G = _arrays(mesh)
    used = np.unique(F[G == group])
    V[used] += np.asarray(dxyz, float)
    return _put(mesh, V)


def _scale_group_halfside(mesh, group, factor, side=+1):
    """그룹 중 y 부호가 `side` 인 정점만 그 부품 중심 기준으로 키운다 — **좌우 한쪽만** 커진다."""
    V, F, G = _arrays(mesh)
    used = np.unique(F[G == group])
    sel = used[np.sign(V[used, 1]) == side]
    if not len(sel):
        return copy.deepcopy(mesh)
    c = V[sel].mean(0)
    V[sel] = c + (V[sel] - c) * float(factor)
    return _put(mesh, V)


def _rotate_all(mesh, axis, deg):
    """기체 전체를 축(x/y/z) 둘레로 돌린다."""
    V, F, G = _arrays(mesh)
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    R = {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
         "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
         "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]
    return _put(mesh, V @ R.T)


def _prop_face_labels(mesh, spec):
    V, F, G = _arrays(mesh)
    C = np.asarray([r["center"] for r in rotor_layout(spec)], float)
    pidx = np.where(G == "prop")[0]
    Cp = V[F[pidx]].mean(1)
    lab = np.linalg.norm(Cp[:, None, :2] - C[None, :, :2], axis=2).argmin(1)
    return V, F, G, C, pidx, lab


def _flip_rotor_handedness(mesh, spec, rotors):
    """로터 `rotors` 의 프롭만 **제자리에서** 거울상으로 바꾼다(그 로터 축을 지나는 y 평면 기준)."""
    V, F, G, C, pidx, lab = _prop_face_labels(mesh, spec)
    for k in rotors:
        fsel = pidx[lab == k]
        used = np.unique(F[fsel])
        V[used, 1] = 2.0 * C[k, 1] - V[used, 1]
        F[fsel] = F[fsel][:, [0, 2, 1]]        # 반사는 det=−1 → 감김 반전
    return _put(mesh, V, F)


def _flip_prop_winding(mesh, spec, rotors):
    """**정점은 그대로 두고 감김만** 뒤집는다(법선이 안쪽을 본다)."""
    V, F, G, C, pidx, lab = _prop_face_labels(mesh, spec)
    for k in rotors:
        fsel = pidx[lab == k]
        F[fsel] = F[fsel][:, [0, 2, 1]]
    return _put(mesh, V, F)


def _mirror_prop_forgot_rewind(mesh, spec, rotors):
    """⭐ **거울만 뜨고 감김 반전을 빠뜨린다** — 실제로 나기 쉬운 실수다.
    (반사는 행렬식이 −1 이라 정점을 거울 뜨면 감김도 같이 뒤집어야 법선이 바깥을 본다.
     이 저장소의 `_flip_rotor_handedness` 는 그 줄을 갖고 있고, 그 줄을 빼먹은 판이 이것이다.)"""
    V, F, G, C, pidx, lab = _prop_face_labels(mesh, spec)
    for k in rotors:
        used = np.unique(F[pidx[lab == k]])
        V[used, 1] = 2.0 * C[k, 1] - V[used, 1]
    return _put(mesh, V, F)


def _spin_one_prop(mesh, spec, rotor, deg):
    """로터 하나의 프롭만 제 축 둘레로 `deg` 만큼 돌린다(다른 부품은 그대로)."""
    V, F, G, C, pidx, lab = _prop_face_labels(mesh, spec)
    used = np.unique(F[pidx[lab == rotor]])
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    x, y = V[used, 0] - C[rotor, 0], V[used, 1] - C[rotor, 1]
    V[used, 0] = C[rotor, 0] + ca * x - sa * y
    V[used, 1] = C[rotor, 1] + sa * x + ca * y
    return _put(mesh, V)


def _flip_group_winding(mesh, group):
    V, F, G = _arrays(mesh)
    sel = G == group
    F[sel] = F[sel][:, [0, 2, 1]]
    return _put(mesh, V, F)


def _rename_group(mesh, old, new):
    out = copy.deepcopy(mesh)
    out.g = [new if g == old else g for g in mesh.g]
    return out


def _duplicate_group(mesh, group):
    """그룹의 삼각형을 **한 벌 더** 얹는다(정점도 새로 쌓는다) — 면적 이중계상 결함."""
    V, F, G = _arrays(mesh)
    sel = np.where(G == group)[0]
    used = np.unique(F[sel])
    remap = np.zeros(int(used.max()) + 1, np.int64)
    remap[used] = np.arange(len(used)) + len(V)
    V2 = np.vstack([V, V[used]])
    F2 = np.vstack([F, remap[F[sel]]])
    G2 = np.concatenate([G, np.full(len(sel), group)])
    out = copy.deepcopy(mesh)
    out.v = [tuple(map(float, p)) for p in V2]
    out.f = [tuple(map(int, t)) for t in F2]
    out.g = list(G2)
    return out


def _drop_one_triangle(mesh, group):
    """그룹의 삼각형 1장을 뺀다 — 껍질이 열린다."""
    V, F, G = _arrays(mesh)
    i = int(np.where(G == group)[0][0])
    keep = np.ones(len(F), bool)
    keep[i] = False
    out = copy.deepcopy(mesh)
    out.f = [tuple(map(int, t)) for t in F[keep]]
    out.g = list(G[keep])
    return out


def _drop_half_group(mesh, group, side=+1):
    """그룹 중 y 부호가 `side` 인 삼각형을 통째로 지운다 — 좌우 한쪽만 없어진다."""
    V, F, G = _arrays(mesh)
    cy = V[F].mean(1)[:, 1]
    kill = (G == group) & (np.sign(cy) == side)
    keep = ~kill
    out = copy.deepcopy(mesh)
    out.f = [tuple(map(int, t)) for t in F[keep]]
    out.g = list(G[keep])
    return out


# --------------------------------------------------------------------------- #
#  0.  자 검정 — 닫힌 해가 있는 도형
# --------------------------------------------------------------------------- #
def test_rulers():
    st = msym.selftest_rulers()
    _say("자검정", "검정", "정육면체 투영면적 ↔ 닫힌 해",
         abs(st["cube_axis_err_rel"]) < 1e-3 and abs(st["cube_diag_err_rel"]) < 3e-3,
         f"축 {st['cube_axis_m2']:.6f}(오차 {st['cube_axis_err_rel']:+.1e}) · "
         f"대각 {st['cube_diag_m2']:.6f} ↔ √3={st['cube_diag_closed_form_m2']:.6f} "
         f"(오차 {st['cube_diag_err_rel']:+.1e})")
    _say("자검정", "검정", "직육면체 질량·CoM·관성 ↔ 닫힌 해",
         st["mass_ruler_max_err_rel"] <= 1e-12,
         f"두 자(trimesh · 손계산) 모두 최대 상대오차 {st['mass_ruler_max_err_rel']:.1e} "
         f"— 질량 {st['box_mass_rawruler_kg']} kg = ρabc, I = m(b²+c²)/12 …")

    #  ⭐ 자를 일부러 망가뜨리면 잡히는가 — 껍질을 열어 «한쪽면 합 = 양면합/2» 항등식을 깬다
    V, F = msym._unit_box()
    u = (0.3, 0.5, 0.81)
    ok_closed = abs(msym.onesided_area(V, F, u) - msym.twosided_area(V, F, u)) < 1e-15
    a1 = msym.onesided_area(V, F[:-1], u)
    a2 = msym.twosided_area(V, F[:-1], u)
    _say("자검정", "양성", "삼각형 1장 뺀 상자 → 항등식 깨짐",
         ok_closed and abs(a1 - a2) > 1e-4,
         f"닫힌 상자 |한쪽면−양면/2| < 1e-15 · 연 상자 {abs(a1 - a2):.5f} m² 차이 "
         f"— check_projected_area 의 ⑶번 판정이 이걸 본다")


# --------------------------------------------------------------------------- #
#  1.  손잡이 — 자 둘
# --------------------------------------------------------------------------- #
def test_handedness():
    spec = DRONES[KEY]
    m = build_drone(spec)
    good = msym.check_rotor_handedness(spec, mesh=m)
    _say("손잡이", "음성", f"{KEY} 원본", good["ok"],
         f"기준 자A {good['h_ref_normals']:+.4f} / 자B {good['h_ref_positions']:+.4f} · "
         + " ".join(f"{r['h_normals']:+.3f}/{r['h_positions']:+.3f}" for r in good["per_rotor"]))

    n_rot = len(good["per_rotor"])
    same = _flip_rotor_handedness(m, spec, [k for k in range(n_rot) if k % 2 == 1])
    r = msym.check_rotor_handedness(spec, mesh=same)
    n_a = sum(1 for x in r["per_rotor"] if not x["ok_normals"])
    n_b = sum(1 for x in r["per_rotor"] if not x["ok_positions"])
    _say("손잡이", "양성", "전 로터 같은 손잡이 (2026-07-28 실제 버그)",
         (not r["ok"]) and n_a == n_rot // 2 and n_b == n_rot // 2,
         f"자A 불일치 {n_a}/{n_rot} · 자B 불일치 {n_b}/{n_rot} — 두 자가 **같은 로터**를 짚는다")

    one = _flip_rotor_handedness(m, spec, [0])
    r1 = msym.check_rotor_handedness(spec, mesh=one)
    n_a1 = sum(1 for x in r1["per_rotor"] if not x["ok_normals"])
    n_b1 = sum(1 for x in r1["per_rotor"] if not x["ok_positions"])
    _say("손잡이", "양성", "한 로터만 뒤집기",
         (not r1["ok"]) and n_a1 == 1 and n_b1 == 1,
         f"자A {n_a1}개 · 자B {n_b1}개 — rotor0 하나만 짚었다")

    #  ⭐ 실제로 나기 쉬운 실수 — 거울만 뜨고 감김 반전을 빼먹기
    fr = _mirror_prop_forgot_rewind(m, spec, [0])
    rf = msym.check_rotor_handedness(spec, mesh=fr)
    na = [x["rotor"] for x in rf["per_rotor"] if not x["ok_normals"]]
    nb = [x["rotor"] for x in rf["per_rotor"] if not x["ok_positions"]]
    _say("손잡이", "양성", "⭐거울 변환에서 감김 반전을 빼먹기",
         (not rf["ok"]) and na == [0] and nb == [0],
         f"자A {na} · 자B {nb} — 두 자가 **독립적으로** 같은 로터를 짚는다 "
         f"(자A 는 법선을, 자B 는 정점만 본다)")

    #  ⭐⭐ 정직하게 적을 것 — «두 자가 갈리는 결함» 은 **만들지 못했다**
    wf = _flip_prop_winding(m, spec, [0])
    rw = msym.check_rotor_handedness(spec, mesh=wf)
    dis = [x["rotor"] for x in rw["per_rotor"] if not x["rulers_agree"]]
    cm = mesh_check.check_mesh(wf, KEY)["groups"]["prop"]
    _say("손잡이", "한계", "감김만 뒤집기는 이 축이 못 잡는다(다른 파일이 잡는다)",
         rw["ok"] and dis == [] and (not cm["ok"]) and cm["raw_negative_parts"] >= 1,
         f"자A {rw['per_rotor'][0]['h_normals']:+.4f}(원본 "
         f"{good['per_rotor'][0]['h_normals']:+.4f}) — 크기만 변하고 **부호는 안 뒤집힌다**"
         f"(윗면 선택 n_z>0 이 뒤집힌 아랫면을 대신 고르기 때문). "
         f"⇒ mesh_check 가 잡는다: 안쪽법선 {cm['inward_normals']} · "
         f"손계산 음수부품 {cm['raw_negative_parts']} · 판정 {cm['ok']}. "
         f"⚠ 따라서 `rulers_agree` 필드는 **양성 대조가 없다** — 내가 지은 결함 전부에서 "
         f"두 자가 일치했다. 이 필드는 «있다»고 치지 않고 감시값으로만 남긴다")

    #  한계 선언 — 전체 거울상은 결함이 아니다
    V, F, G = _arrays(m)
    V[:, 1] = -V[:, 1]
    mir = _put(m, V, F[:, [0, 2, 1]])
    rm = msym.check_rotor_handedness(spec, mesh=mir)
    _say("손잡이", "한계", "기체 전체 거울상은 안 걸린다(맞다)", rm["ok"],
         "이웃 로터가 반대로 도는 배치라 통째로 뒤집으면 프롭이 «반대 방향 로터 자리»로 "
         "옮겨가며 손잡이도 같이 뒤집힌다 — 로터 번호만 바뀐 같은 기체다")


# --------------------------------------------------------------------------- #
#  2.  로터 회전방향 배치 규약
# --------------------------------------------------------------------------- #
def _spec_with(spec, **kw):
    return dataclasses.replace(spec, **kw)


def test_dir_convention():
    ok_all, bad_keys = True, []
    for k, s in DRONES.items():
        try:
            r = msym.check_rotor_dir_convention(s)
        except Exception as e:
            ok_all = False
            bad_keys.append(f"{k}({type(e).__name__})")
            continue
        if not r["ok"]:
            ok_all = False
            bad_keys.append(k)
    _say("배치규약", "음성", f"레지스트리 {len(DRONES)}기종 전부", ok_all,
         "이웃반대 · 마주보는쌍(부호는 n 에서 유도) · Σdir=0 · 거울짝(반경·높이 같고 방향 반대)"
         + (f" ⛔실패 {bad_keys}" if bad_keys else ""))

    base = DRONES[KEY]
    ang = list(msym._rotor_frame(base)[3])

    #  ⑴ 목록 순서를 방위 순서가 아니게 섞는다 → dir 이 k%2 로 정해지므로 이웃규약이 깨진다
    bad = _spec_with(base, rotor_deg=(ang[0], ang[2], ang[1], ang[3]))
    r = msym.check_rotor_dir_convention(bad)
    _say("배치규약", "양성", "rotor_deg 를 방위 순서가 아니게 섞기",
         (not r["ok"]) and (not r["neighbors_alternate"]),
         f"방위순 dir {r['azimuth_sorted_dir']} — 이웃이 같은 방향으로 돈다. "
         f"각도·반경은 전부 스펙 그대로라 치수·위상 검사는 **하나도** 안 걸린다")

    #  ⑵ 거울 짝을 깬다 — 한 로터의 각도만 옮긴다
    bad2 = _spec_with(base, rotor_deg=(ang[0] + 8.0, ang[1], ang[2], ang[3]))
    r2 = msym.check_rotor_dir_convention(bad2)
    _say("배치규약", "양성", "로터 하나만 방위 +8° (좌우 배치 깨짐)", not r2["ok"],
         f"실패 {len(r2['failures'])}건 — {r2['failures'][0] if r2['failures'] else ''}")

    #  ⑶ 거울 짝의 반경을 깬다
    rad = [abs(v) for v in np.hypot(*msym._rotor_frame(base)[0][:, :2].T)]
    bad3 = _spec_with(base, rotor_deg=tuple(ang),
                      rotor_r_mm=(rad[0] + 20.0, rad[1], rad[2], rad[3]))
    r3 = msym.check_rotor_dir_convention(bad3)
    _say("배치규약", "양성", "거울 짝의 반경만 +20 mm", not r3["ok"],
         f"실패 {len(r3['failures'])}건 — 거울짝 반경차가 잡힌다")

    #  ⑷ 거울 짝의 높이를 깬다
    bad4 = _spec_with(base, rotor_z_mm=(10.0, 0.0, 0.0, 0.0))
    r4 = msym.check_rotor_dir_convention(bad4)
    _say("배치규약", "양성", "거울 짝의 높이만 +10 mm", not r4["ok"],
         f"실패 {len(r4['failures'])}건 — 거울짝 높이차가 잡힌다")


# --------------------------------------------------------------------------- #
#  3.  좌우 거울 대칭
# --------------------------------------------------------------------------- #
def _prism(n_seg, phase_deg, R=0.010, H=0.20):
    """정 n 각기둥 — **위상(phase)** 을 줄 수 있다. 근사하는 «원기둥» 솔리드는 좌우대칭인데
    n 각형 다면체 자체는 위상이 (180/n)° 의 배수가 아니면 좌우대칭이 **아니다**.
    이걸로 «분할이 달라서 생기는 잔차»의 크기를 **해석값과 대 본다**.
    ⚠ 위상을 (180/n)° 로 주면 거울상이 자기 자신과 겹쳐 잔차가 0 이 된다 — 최대 어긋남은
      그 절반인 (90/n)° 다(처음에 이걸 틀려서 대조가 0 을 냈다)."""
    a = np.radians(phase_deg) + np.arange(n_seg) * 2 * np.pi / n_seg
    ring = np.c_[R * np.cos(a), R * np.sin(a)]
    V = np.vstack([np.c_[ring, np.zeros(n_seg)], np.c_[ring, np.full(n_seg, H)],
                   [[0, 0, 0]], [[0, 0, H]]])
    cb, ct = 2 * n_seg, 2 * n_seg + 1
    F = []
    for i in range(n_seg):
        j = (i + 1) % n_seg
        F += [[i, j, n_seg + j], [i, n_seg + j, n_seg + i]]     # 옆면(바깥 법선)
        F += [[cb, j, i]]                                        # 바닥
        F += [[ct, n_seg + i, n_seg + j]]                        # 윗면
    return V, np.asarray(F, np.int64)


def test_lateral():
    spec = DRONES[KEY]
    m = build_drone(spec)
    good = msym.check_lateral_symmetry(spec, mesh=m)
    worst = max(g["surf_rms_mm"] for g in good["groups"].values())
    pm = max((r["max_mm"] for r in good["prop_mirror"]), default=0.0)
    _say("좌우대칭", "음성", f"{KEY} 원본", good["ok"],
         f"프레임 표면잔차 최대 {worst:.4f} mm · 면적 y-모멘트 "
         f"{good['frame_area_y_moment_rel']:+.1e} · 프롭 짝맞춤 최대 {pm:.1e} mm")

    for grp, dy in (("camera", 0.020), ("battery", 0.015)):
        r = msym.check_lateral_symmetry(spec, mesh=_shift_group(m, grp, (0, dy, 0)))
        got = r["groups"].get(grp, {})
        _say("좌우대칭", "양성", f"{grp} 그룹을 y 로 {dy*1000:.0f} mm 이동",
             (not r["ok"]) and not got.get("ok", True),
             f"{grp} 표면잔차 {got.get('surf_rms_mm')} mm > 예산 {got.get('budget_mm')} mm")

    r = msym.check_lateral_symmetry(spec, mesh=_scale_group_halfside(m, "gear", 1.05, +1))
    _say("좌우대칭", "양성", "다리 **한쪽만** 5 % 확대", not r["ok"],
         f"실패 {len(r['failures'])}건 — {r['failures'][0][:70] if r['failures'] else ''}")

    r = msym.check_lateral_symmetry(spec, mesh=_rotate_all(m, "z", 5.0))
    _say("좌우대칭", "양성", "기체 전체를 요(z) 5° 회전", not r["ok"],
         f"실패 {len(r['failures'])}건 — 기수 방향이 어긋나면 좌우 대칭이 먼저 깨진다")

    r = msym.check_lateral_symmetry(spec, mesh=_spin_one_prop(m, spec, 0, 5.0))
    npf = sum(1 for x in r["prop_mirror"] if not x["ok"])
    _say("좌우대칭", "양성", "프롭 하나만 제 축으로 5° 회전",
         (not r["ok"]) and npf > 0,
         f"프롭 짝맞춤 실패 {npf}쌍 — 예산이 {msym.PROP_MIRROR_MAX_MM:g} mm(µm)라 "
         f"정지위상 어긋남이 바로 걸린다")

    #  ⭐ **분할 대조** — 완벽히 대칭인 솔리드를 «좌우로 다르게 분할» 해서 지으면 잔차가
    #     얼마나 나오는가. 실기체에서 본 0.10~0.41 mm 잔차와 gear 의 1e-2 급 좌우차가
    #     «형상 비대칭»인지 «분할 차이»인지 가르는 대조다. 다리 굵기(반경 10 mm)로 맞춘다.
    rows = []
    for n_seg in (12, 16):
        R = 0.010
        V, F = _prism(n_seg, phase_deg=90.0 / n_seg, R=R)    # 최대 어긋남 위상
        rms, mx = msym._surface_mirror_residual(V * 1000.0, F)
        sag = R * (1.0 - math.cos(math.pi / n_seg)) * 1000.0  # 해석 sagitta [mm]
        a_p = msym.onesided_area(V, F, msym.view_dir(37.0, 0.0))
        a_m = msym.onesided_area(V, F, msym.view_dir(-37.0, 0.0))
        rows.append((n_seg, mx, sag, abs(a_p - a_m) / a_m))
    ok = all(abs(mx - sag) <= 1e-4 * max(sag, 1e-9) for _, mx, sag, _ in rows)
    _say("좌우대칭", "검정", "⭐분할 대조: 대칭 솔리드 + 비대칭 분할", ok,
         " · ".join(f"{n}각기둥 R=10mm: 표면잔차 최대 {mx:.4f} mm = 해석 sagitta "
                    f"R(1−cos π/n) {sag:.4f} mm, 한쪽면합 좌우차 {rel:.2e}"
                    for n, mx, sag, rel in rows)
         + "  ⇒ 실기체 gear 의 잔차(0.10~0.41 mm)와 좌우차(7e-3~2.5e-2)는 **이 범위 안**이다 "
           "— 분할 차이로 **설명 가능한 크기**다(설명 가능하다 ≠ 증명했다)")


# --------------------------------------------------------------------------- #
#  4.  질량중심 · 관성
# --------------------------------------------------------------------------- #
def test_mass_inertia():
    spec = DRONES[KEY]
    m = build_drone(spec)
    good = msym.check_mass_inertia(spec, mesh=m)
    _say("질량·관성", "음성", f"{KEY} 원본", good["ok"],
         f"CoM {good['com_mm']} mm · I_xy {good['product_inertia_rel']['Ixy']:.1e} · "
         f"주축기울기 {good['principal_axis_tilt_deg']}° · 두 자 일치 "
         f"{good['ruler_agreement']['mass_rel']:.1e}")

    r = msym.check_mass_inertia(spec, mesh=_shift_group(m, "battery", (0, 0.015, 0)))
    _say("질량·관성", "양성", "배터리를 y 로 15 mm 이동",
         (not r["ok"]) and abs(r["com_mm"][1]) > 0.05,
         f"CoM_y {r['com_mm'][1]:+.4f} mm (상대 {r['com_y_rel']:.1e}) · "
         f"I_xy {r['product_inertia_rel']['Ixy']:.1e} · 실패 {len(r['failures'])}건")

    r = msym.check_mass_inertia(spec, mesh=_rotate_all(m, "x", 5.0))
    _say("질량·관성", "양성", "기체를 롤(x) 5° 회전",
         (not r["ok"]) and r["principal_axis_tilt_deg"] > msym.PRINCIPAL_TILT_BUDGET_DEG,
         f"주축이 y 에서 {r['principal_axis_tilt_deg']}° 벗어남 · "
         f"I_yz {r['product_inertia_rel']['Iyz']:.1e} · CoM_y {r['com_mm'][1]:+.3f} mm")

    r = msym.check_mass_inertia(spec, mesh=_flip_group_winding(m, "battery"))
    neg = any("질량이 0 이하" in f or "총질량" in f for f in r["failures"])
    _say("질량·관성", "양성", "배터리 감김 뒤집기 → 질량 음수", (not r["ok"]) and neg,
         f"battery 질량 {r['per_group'].get('battery', {}).get('mass_kg')} kg · "
         f"실패 {len(r['failures'])}건 — 부피가 음수면 관성도 물리적으로 무의미하다")

    r = msym.check_mass_inertia(spec, mesh=_rename_group(m, "gear", "landing_skid"))
    _say("질량·관성", "양성", "밀도표에 없는 그룹 이름(gear→landing_skid)",
         (not r["ok"]) and any("DENSITY" in f for f in r["failures"]),
         f"실패 {len(r['failures'])}건 — 조용한 폴백 대신 그 자리에서 멈춘다")

    #  두 자의 비교기 자체 시험 — 한쪽 자의 입력만 1.000001 배 키우면 어긋남이 잡혀야 한다
    V, F = msym._unit_box((0, 0, 0), (0.3, 0.5, 0.7))
    rho = np.full(len(F), 1234.0)
    a = msym.mass_properties_raw(V, F, rho)["mass"]
    b = msym.mass_properties_raw(V * 1.000001, F, rho)["mass"]
    rel = abs(a - b) / b
    _say("질량·관성", "양성", "비교기 시험: 한 자의 입력만 1.000001 배",
         rel > msym.MASS_RULER_AGREE_REL,
         f"두 자의 질량 상대차 {rel:.2e} > 허용 {msym.MASS_RULER_AGREE_REL:.0e} "
         f"— 1 ppm 크기 차이도 비교기가 본다")


# --------------------------------------------------------------------------- #
#  5.  투영면적
# --------------------------------------------------------------------------- #
def _area_kw():
    """대조는 빠르게 — 앙각 1개 · 픽셀 512. 수치의 정본은 인증서 쪽(앙각 2개 · 1024)이다.

    ⛔ **방위 간격을 90° 로 잡으면 안 된다.** el=0 에서 방위 90°↔270° 는 보는 방향이 정확히
       û ↔ −û 라, 닫힌 껍질에서는 Σmax(n̂·û,0)A 가 **항등적으로 같다**. 즉 그 쌍으로 거울
       대칭을 재면 어떤 결함을 넣어도 0 이 나온다(처음에 이걸로 대조 두 개를 놓쳤다).
       30° 간격이면 30↔330 · 60↔300 … 처럼 축퇴하지 않는 짝이 생긴다."""
    return dict(az_step=30.0, elevations=(0.0,), npx=512)


def test_projected_area():
    spec = DRONES[KEY]
    m = build_drone(spec)
    good = msym.check_projected_area(spec, mesh=m, **_area_kw())
    _say("투영면적", "음성", f"{KEY} 원본", good["ok"],
         f"실루엣 평균 {good['sil_mean_m2']:.5f} m² · PO/실루엣 {good['onesided_over_sil_mean']} "
         f"· 좌우차 실루엣 {good['mirror_max_rel']:.1e} / 한쪽면합 "
         f"{good['mirror_onesided_max_rel']:.1e}")

    r = msym.check_projected_area(spec, mesh=_rotate_all(m, "z", 5.0), **_area_kw())
    _say("투영면적", "양성", "기체 요(z) 5° 회전 → 좌우 투영면적이 갈린다", not r["ok"],
         f"좌우차 실루엣 {r['mirror_max_rel']:.1e} / 한쪽면합 "
         f"{r['mirror_onesided_max_rel']:.1e} (예산 {msym.PROJ_MIRROR_TOL_REL:.0e} / "
         f"{msym.PROJ_MIRROR_ONESIDED_TOL_REL:.0e})")

    r = msym.check_projected_area(spec, mesh=_drop_half_group(m, "gear", +1), **_area_kw())
    gm = r["group_mirror"].get("gear", {})
    _say("투영면적", "양성", "다리를 좌우 **한쪽만** 삭제", not r["ok"],
         f"gear 그룹 좌우차 {gm.get('onesided_mirror_max_rel'):.2e} > 예산 "
         f"{gm.get('budget'):.1e} — 그룹별 자가 **어느 부품인지 집어낸다**")

    r = msym.check_projected_area(spec, mesh=_drop_one_triangle(m, "body"), **_area_kw())
    ident = any("양면합" in f for f in r["failures"])
    _say("투영면적", "양성", "body 삼각형 1장 제거 → 껍질이 열린다",
         (not r["ok"]) and ident,
         f"«한쪽면 합 = 양면합/2» 항등식이 깨진다 — 실패 {len(r['failures'])}건")

    dup = _duplicate_group(m, "body")
    r = msym.check_projected_area(spec, mesh=dup, **_area_kw())
    _say("투영면적", "양성", "body 그룹을 **한 벌 더** 얹기(면적 이중계상)",
         (not r["ok"]) and r["onesided_over_sil_max"] > good["onesided_over_sil_max"],
         f"PO/실루엣 배수 {good['onesided_over_sil_max']} → {r['onesided_over_sil_max']} "
         f"(예산 {msym.PROJ_DOUBLE_COUNT_BUDGET.get(spec.key, msym.PROJ_DOUBLE_COUNT_BUDGET['_default'])}) "
         f"— 실루엣은 그대로인데 PO 가 더하는 양만 늘었다")


def run_all() -> list[dict]:
    print("=" * 104)
    print("대칭·손잡이·파생량 검사기 적대 시험 — 일부러 나쁜 메쉬를 지어 mesh_symmetry 가 잡는지 본다")
    print("=" * 104)
    print("\n[0. 자 검정 — 답을 아는 도형]")
    test_rulers()
    print("\n[1. 로터 손잡이 — 자 둘(법선 · 위치)]")
    test_handedness()
    print("\n[2. 로터 회전방향 배치 규약]")
    test_dir_convention()
    print("\n[3. 좌우 거울 대칭]")
    test_lateral()
    print("\n[4. 질량중심 · 관성]")
    test_mass_inertia()
    print("\n[5. 투영면적 — 자 둘(실루엣 · 한쪽면 합)]")
    test_projected_area()
    return RESULTS


def main():
    rows = run_all()
    n_ok = sum(1 for r in rows if r["passed"])
    print("\n" + "=" * 104)
    print(f"결과: {n_ok}/{len(rows)} 통과")
    kinds = {}
    for r in rows:
        kinds.setdefault(r["kind"], [0, 0])
        kinds[r["kind"]][1] += 1
        kinds[r["kind"]][0] += int(r["passed"])
    print("  종류별: " + " · ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(kinds.items())))
    if n_ok < len(rows):
        print("놓친 항목:")
        for r in rows:
            if not r["passed"]:
                print(f"  ❌ [{r['kind']}] {r['tag']} — {r['detail']}")
        return 1
    print("⇒ 다섯 축 전부에서 «멀쩡한 것은 통과, 결함은 걸린다» 가 코드로 증명됐다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
