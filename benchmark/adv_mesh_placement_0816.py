# -*- coding: utf-8 -*-
"""
adv_mesh_placement_0816.py — **배치·겹침·묻힘 검사기를 검사한다**
==============================================================================
규약(기존 `adv_mesh_check_faults.py` 와 같다): 검사 하나마다 **두 대조를 다 건다.**
  · **음성 대조** — 멀쩡한 것은 **통과해야** 한다 (거짓경보가 아님을 보인다)
  · **양성 대조** — 결함을 심으면 **걸려야** 한다 (실제로 본다는 것을 보인다)
이 두 대조가 없는 검사는 «있다» 고 치지 않는다.

⭐ 이 파일이 특별히 힘주는 것 — **측정법 자체가 틀리지 않았음**을 보인다.
   간극을 한 방향으로만 재면 «큰 상자가 가는 봉을 감쌀 때» 거짓양성이 난다(실제 2건).
   그래서 아래 P2 는 그 상황을 **일부러 지어서**, 순진한 잣대가 어떻게 틀리고 우리 잣대가
   어떻게 맞히는지를 **같은 메쉬 위에서 나란히** 보여준다. 놀랍게도 «양방향 정점↔면» 만으로도
   **부족하다** — 그래서 우리 엔진은 삼각형 교차와 내부판정을 함께 쓴다. 그 사실을 여기서 증명한다.

층 구조
  A. 원시함수 대조   — 교차 판정·점↔면 거리를 **독립 구현/독립 라이브러리**와 맞춰 본다 (A0~A4)
  B. 결함 대조       — 뜬 부품·관통·완전매몰·자기교차·동일평면·구멍난 컨테이너를 지어서
                       걸리는지 본다. 항목마다 **음성/양성 쌍** (B1~B6)
  C. 사각지대        — 못 잡는 것을 **일부러 시험해서** 못 잡는다는 것을 기록으로 남긴다 (C1~C4)
  D. 봉인 · 함대     — 같은 형상이면 같은 답 · 1 nm 만 바꿔도 지문이 달라짐 ·
                       실제 기체는 예산 안 · 실제 메쉬에서 독립 구현과 대조 (D1~D4)

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/adv_mesh_placement_0816.py [--fleet]
      ⛔ GPU 안 쓴다. 파일도 안 쓴다(읽기 + 화면 출력).
      나가는 값: 전부 통과 0, 하나라도 어긋나면 1.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

import mesh_placement as mp                       # noqa: E402
from geom import Mesh                             # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def _say(tag: str, passed: bool, detail: str):
    RESULTS.append((tag, passed, detail))
    print(f"  {'✅' if passed else '❌'} {tag:38s} {detail}")


# --------------------------------------------------------------------------- #
#  합성 메쉬 도구 — 상자 하나(닫힌 껍질, **바깥 법선**)
# --------------------------------------------------------------------------- #
def _box(mesh: Mesh, lo, hi, group: str):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    idx = [mesh.add_vertex(x, y, z)
           for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]

    def v(i, j, k):
        return idx[4 * i + 2 * j + k]

    quads = [((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)),
             ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)),
             ((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)),
             ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)),
             ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)),
             ((0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1))]
    #  ⚠ 위 차례는 «안쪽» 법선이 나오는 순서다 — 뒤집어 넣어야 바깥 법선이 된다
    #    (adv_mesh_check_faults._box 와 같은 규약. 아래 A0 이 매번 확인한다.)
    for a, b, c, d in quads:
        mesh.add_quad(v(*d), v(*c), v(*b), v(*a), group=group)
    return mesh


def _mesh_of(*boxes) -> Mesh:
    """(lo, hi, group) 들로 메쉬 하나를 짓는다. 단위는 **미터**(우리 메쉬 규약)."""
    m = Mesh("synthetic")
    for lo, hi, g in boxes:
        _box(m, lo, hi, g)
    return m


def _rel(mesh, i=0, j=1):
    """부품 두 개짜리 합성 메쉬의 관계 한 줄."""
    parts = mp.split_parts(mesh)
    return parts, mp.pair_relation(parts[i], parts[j])


# --------------------------------------------------------------------------- #
#  A. 원시함수 대조 — 판정의 바닥이 되는 계산이 맞는가
# --------------------------------------------------------------------------- #
def _brute_cross(t1, t2) -> bool:
    """**독립 구현** — 변(선분) ↔ 삼각형 교차를 무게중심 좌표로. 허용오차 없음(엄격).
    우리 벡터화 구현(Möller 구간겹침)과 **완전히 다른 길**이라 교차검증이 된다."""
    def seg_tri(p, q, A, B, C):
        n = np.cross(B - A, C - A)
        d = float(np.dot(n, q - p))
        if abs(d) < 1e-18:
            return False
        t = float(np.dot(n, A - p)) / d
        if t < 0.0 or t > 1.0:
            return False
        X = p + t * (q - p)
        v0, v1, v2 = C - A, B - A, X - A
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-300:
            return False
        u = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        return bool(u >= 0.0 and w >= 0.0 and u + w <= 1.0)
    for (p, q) in ((t2[0], t2[1]), (t2[1], t2[2]), (t2[2], t2[0])):
        if seg_tri(p, q, *t1):
            return True
    for (p, q) in ((t1[0], t1[1]), (t1[1], t1[2]), (t1[2], t1[0])):
        if seg_tri(p, q, *t2):
            return True
    return False


def test_A0_box_normals():
    """도구 자체 점검 — 이 파일이 짓는 상자가 **바깥 법선**인가. (안쪽이면 내부판정이 뒤집혀
    아래 모든 대조가 조용히 뜻을 잃는다.)"""
    parts = mp.split_parts(_mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body")))
    p = parts[0]
    _say("A0 도구점검: 합성 상자 바깥법선", p.watertight and p.volume_mm3 > 0,
         f"수밀 {p.watertight} · 부호부피 {p.volume_mm3:.1f} mm³ (양수여야 한다)")


def test_A1_tri_tri_known():
    """손으로 아는 다섯 경우."""
    T = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0]])
    F = np.array([[0, 1, 2]])
    i0, j0 = np.array([0]), np.array([0])
    cases = [
        ("가로지름", np.array([[0.2, 0.2, -1.], [0.3, 0.2, 1.], [0.25, 0.4, 0.]]), True),
        ("떠 있음", np.array([[0.2, 0.2, 4.], [0.3, 0.2, 6.], [0.25, 0.4, 5.]]), False),
        ("같은 평면", np.array([[0.1, 0.1, 0.], [0.9, 0.1, 0.], [0.1, 0.9, 0.]]), False),
        ("빗나감", np.array([[5.2, 5.2, -1.], [5.3, 5.2, 1.], [5.25, 5.4, 0.]]), False),
        ("T 접촉", np.array([[0.2, 0.2, 0.], [0.3, 0.2, 1.], [0.25, 0.4, 1.]]), True),
    ]
    bad = [n for n, V, want in cases
           if bool(mp.tri_tri_cross_mask(T, F, V, F, i0, j0, min_pen=0.0)[0]) != want]
    _say("A1 원시함수: 손으로 아는 5경우", not bad,
         "가로지름·떠있음·같은평면·빗나감·T접촉 전부 기대대로" if not bad else f"어긋남 {bad}")


def test_A2_tri_tri_random(n=3000):
    """무작위 삼각형 쌍 — **독립 구현**과 답이 같아야 한다."""
    rng = np.random.default_rng(20260816)
    F = np.array([[0, 1, 2]])
    i0, j0 = np.array([0]), np.array([0])
    bad = 0
    for _ in range(n):
        t1 = rng.normal(size=(3, 3))
        t2 = rng.normal(size=(3, 3)) * 0.8
        got = bool(mp.tri_tri_cross_mask(t1, F, t2, F, i0, j0, min_pen=0.0)[0])
        if got != _brute_cross(t1, t2):
            bad += 1
    _say("A2 원시함수: 무작위 3000쌍 ↔ 독립구현", bad == 0, f"불일치 {bad} / {n}")


def test_A3_point_triangle(n=1500):
    """점↔삼각형 거리 — **표본 최소값을 절대 넘지 않아야** 한다(표본은 참값의 상한)."""
    rng = np.random.default_rng(7)
    worst = 0.0
    for _ in range(n):
        T = rng.normal(size=(3, 3))
        P = rng.normal(size=(1, 3)) * 1.5
        d = float(mp._pt_tri_dist(P, T[None, 0], T[None, 1], T[None, 2])[0])
        w = rng.random((4000, 3))
        w /= w.sum(1, keepdims=True)
        worst = max(worst, d - float(np.linalg.norm(w @ T - P, axis=1).min()))
    _say("A3 원시함수: 점↔삼각형 ≤ 표본최소", worst <= 1e-12,
         f"표본 대비 최대 초과 {worst:.3e} (0 이하여야 한다)")


def test_A4_points_to_surface():
    """점무리↔표면 — **독립 라이브러리**(trimesh.proximity)와 맞춰 본다."""
    import trimesh
    rng = np.random.default_rng(1)
    m = trimesh.creation.icosphere(subdivisions=3, radius=0.05)
    P = rng.normal(size=(400, 3)) * 0.08
    d1 = mp.points_to_surface(P, np.asarray(m.vertices), np.asarray(m.faces))
    d2 = trimesh.proximity.closest_point(m, P)[1]
    err = float(np.abs(d1 - d2).max())
    _say("A4 원시함수: 점↔표면 ↔ trimesh", err < 1e-12, f"최대차 {err:.3e} m")


# --------------------------------------------------------------------------- #
#  B. 결함 대조 — 결함을 심으면 걸리는가 · 멀쩡하면 통과하는가
# --------------------------------------------------------------------------- #
def test_B1_floating():
    """⑴ 뜬 부품 — 붙어 있어야 할 것이 떨어졌나."""
    touch = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                     ((0.1, 0.02, 0.02), (0.2, 0.04, 0.04), "arm"))     # 면끼리 딱 붙음
    c = mp.placement_census(touch, "_synthetic")
    _say("B1 음성대조: 붙어 있는 두 부품", len(c["floating"]) == 0,
         f"뜬 부품 {len(c['floating'])}개 · 관계 {c['relations']}")

    apart = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                     ((0.105, 0.02, 0.02), (0.2, 0.04, 0.04), "arm"))   # 5 mm 띄움
    c2 = mp.placement_census(apart, "_synthetic")
    gaps = [round(f["gap_mm"], 3) for f in c2["floating"]]
    _say("B1 양성대조: 5 mm 띄운 부품", len(c2["floating"]) == 2 and abs(gaps[0] - 5.0) < 1e-6,
         f"뜬 부품 {len(c2['floating'])}개 · 이격 {gaps} mm (5.0 이어야 한다)")


def test_B2_big_box_thin_rod():
    """⭐⭐ ⑵ **측정법 대조** — 큰 상자가 가는 봉을 감쌀 때.

    실제로 이 저장소에서 2건 났던 거짓양성이다. 같은 메쉬를 세 가지 잣대로 재서 나란히 본다:
      · 순진한 잣대(한 방향·정점↔정점)      → «멀다»
      · 양방향 정점↔면                       → **그래도 «멀다»**(모서리에도 봉 정점에도 안 걸린다)
      · 우리 엔진(+ 삼각형 교차 · 내부판정)  → «관통» / «완전매몰»
    ⇒ 이것이 «양방향 + 내부판정 + 교차» 를 **다 써야 하는 이유**의 증명이다."""
    #  (가) 봉이 상자를 꿰뚫는다 (상자 100 mm, 봉 2×2 mm 가 x 로 관통)
    thru = _mesh_of(((-0.05, -0.05, -0.05), (0.05, 0.05, 0.05), "body"),
                    ((-0.15, -0.001, -0.001), (0.15, 0.001, 0.001), "arm"))
    _, r = _rel(thru)
    naive_far = r["gap_vertex_only_mm"] > 1.0
    bidir_far = r["gap_bidir_mm"] > 1.0
    _say("B2a 양성대조: 봉이 상자를 관통", r["relation"] == "R2_관통" and naive_far and bidir_far,
         f"우리 판정 {r['relation']} · 순진한잣대 {r['gap_vertex_only_mm']:.1f} mm → "
         f"«{r['relation_if_one_way_ruler']}»(거짓) · 양방향 정점↔면도 "
         f"{r['gap_bidir_mm']:.1f} mm(부족) · 교차 삼각형쌍 {r['cross_pairs']}")

    #  (나) 봉이 상자 **안에 통째로** 들어 있다 (교차가 아예 없다 → 내부판정만이 본다)
    inside = _mesh_of(((-0.05, -0.05, -0.05), (0.05, 0.05, 0.05), "body"),
                      ((-0.04, -0.001, -0.001), (0.04, 0.001, 0.001), "arm"))
    _, r2 = _rel(inside)
    #  ⚠ a/b 차례는 그룹 이름 순이라(arm < body) «봉» 이 a 다 — 어느 쪽이든 100 % 면 된다.
    inside_pct = max(r2["a_in_b_pct"] or 0.0, r2["b_in_a_pct"] or 0.0)
    _say("B2b 양성대조: 봉이 상자 안에 통째로",
         r2["relation"] == "R3_완전매몰" and r2["cross_pairs"] == 0
         and inside_pct == 100.0 and r2["gap_vertex_only_mm"] > 1.0,
         f"우리 판정 {r2['relation']}(교차쌍 {r2['cross_pairs']} — 교차만 보는 검사는 못 본다) · "
         f"봉의 {inside_pct} % 가 상자 안 · 순진한잣대 {r2['gap_vertex_only_mm']:.1f} mm(거짓)")

    #  (다) 음성 대조 — 진짜로 떨어져 있으면 «떨어짐» 이어야 한다(거짓경보가 아님)
    far = _mesh_of(((-0.05, -0.05, -0.05), (0.05, 0.05, 0.05), "body"),
                   ((0.055, -0.001, -0.001), (0.15, 0.001, 0.001), "arm"))
    _, r3 = _rel(far)
    _say("B2c 음성대조: 진짜로 떨어진 봉",
         r3["relation"] == "R0_떨어짐" and abs(r3["gap_mm"] - 5.0) < 1e-6,
         f"판정 {r3['relation']} · 간극 {r3['gap_mm']} mm (5.0 이어야 한다)")


def test_B3_self_intersection():
    """⑶ 자기 겹침 — 한 부품이 **자기 자신을** 뚫는다."""
    ok = _mesh_of(((0., 0, 0), (0.01, 0.01, 0.01), "body"))
    c = mp.placement_census(ok, "_synthetic")
    _say("B3 음성대조: 멀쩡한 상자", c["self_intersection"]["n_pairs"] == 0,
         f"자기교차 {c['self_intersection']['n_pairs']}쌍")

    bad = _mesh_of(((0., 0, 0), (0.01, 0.01, 0.01), "body"))
    #  한 꼭짓점을 반대쪽 면 **너머로** 밀어 넣는다 → 그 꼭짓점을 쓰는 삼각형이 윗면을 뚫는다
    v = list(bad.v)
    v[0] = (0.0, 0.0, 0.015)
    bad.v = v
    c2 = mp.placement_census(bad, "_synthetic")
    si = c2["self_intersection"]
    _say("B3 양성대조: 꼭짓점을 반대면 너머로", si["n_pairs"] > 0,
         f"자기교차 {si['n_pairs']}쌍 · 걸린 부품 {[p['pid'] for p in si['parts']]}")


def test_B4_crossing_and_engulf():
    """⑷ 관통 / ⑸ 완전매몰 — 겹친 상자 · 안에 든 상자."""
    apart = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                     ((0.5, 0, 0), (0.6, 0.1, 0.1), "body"))
    c = mp.placement_census(apart, "_synthetic")
    _say("B4 음성대조: 멀리 떨어진 두 상자",
         c["crossing"]["n_pairs"] == 0 and c["coplanar"]["n_pairs"] == 0,
         f"관통 {c['crossing']['n_pairs']} · 동일평면 {c['coplanar']['n_pairs']} · "
         f"관계 {c['relations']}")

    ov = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                  ((0.02, 0.03, 0.04), (0.12, 0.13, 0.14), "body"))     # 세 축 다 어긋나게 겹침
    _, r = _rel(ov)
    _say("B4 양성대조: 모서리로 겹친 두 상자",
         r["relation"] == "R2_관통" and r["cross_pairs"] > 0,
         f"판정 {r['relation']} · 교차 삼각형쌍 {r['cross_pairs']} · "
         f"파고든 깊이 {r['penetration_depth_mm']} mm")

    #  ⭐ 까다로운 판 — 옆면이 **딱 맞물린** 두 상자. 표면이 «가로지르지» 않고 같은 평면에서
    #     만나므로 **교차 잣대에는 하나도 안 걸린다**. 내부판정이 없으면 통째로 놓치는 자리다.
    flush = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                     ((0.02, 0, 0), (0.12, 0.1, 0.1), "body"))
    _, rf = _rel(flush)
    _say("B4 양성대조: 옆면이 딱 맞물려 겹친 두 상자",
         rf["relation"] == "R2_관통" and rf["cross_pairs"] == 0,
         f"판정 {rf['relation']} · 교차쌍 {rf['cross_pairs']}(교차 잣대는 0 — 못 본다) · "
         f"안에 든 면적 {max(rf['a_in_b_pct'], rf['b_in_a_pct'])} % ⇒ 내부판정이 잡는다")

    eng = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                   ((0.02, 0.02, 0.02), (0.08, 0.08, 0.08), "battery"))
    _, r2 = _rel(eng)
    inside_pct = max(r2["a_in_b_pct"] or 0.0, r2["b_in_a_pct"] or 0.0)
    _say("B4 양성대조: 상자 안의 상자(완전매몰)",
         r2["relation"] == "R3_완전매몰" and inside_pct == 100.0,
         f"판정 {r2['relation']} · 안쪽 {inside_pct} % · 교차쌍 {r2['cross_pairs']} "
         f"(교차는 0 이 맞다 — 표면이 안 만난다)")


def test_B5_coplanar():
    """⑹ 동일평면 — 같은 자리에 두 껍질이 겹쳤나(PO 가 같은 면을 두 재질로 두 번 더한다)."""
    apart = _mesh_of(((0., 0, 0), (0.01, 0.01, 0.001), "body"),
                     ((0., 0, 0.002), (0.01, 0.01, 0.003), "canopy"))     # 1 mm 띄움
    c = mp.placement_census(apart, "_synthetic")
    _say("B5 음성대조: 1 mm 띄운 두 판", c["coplanar"]["n_pairs"] == 0,
         f"동일평면 쌍 {c['coplanar']['n_pairs']} · 면적 {c['coplanar']['area_mm2']} mm²")

    stack = _mesh_of(((0., 0, 0), (0.01, 0.01, 0.001), "body"),
                     ((0., 0, 0.001), (0.01, 0.01, 0.002), "canopy"))     # 면이 정확히 포개짐
    c2 = mp.placement_census(stack, "_synthetic")
    want = 100.0      # 10 mm × 10 mm 접합면이 **양쪽** 껍질에 하나씩
    got = c2["coplanar"]["area_mm2"]
    _say("B5 양성대조: 면이 포개진 두 판",
         c2["coplanar"]["n_pairs"] == 1 and abs(got - 2 * want) < 1e-3,
         f"동일평면 면적 {got} mm² (양쪽 합 {2*want} 이어야 한다) · "
         f"판정 {list(c2['relations'])}")


def test_B6_blind_container():
    """⑺ ⭐**«못 봄» 을 «없음» 으로 보고하지 않는다** — 구멍 난 상자는 내부판정이 성립 안 하는데,
    그 사실을 **드러내면서** 교차 검사로 관통을 여전히 잡는가."""
    m = _mesh_of(((-0.05, -0.05, -0.05), (0.05, 0.05, 0.05), "body"),
                 ((-0.15, -0.001, -0.001), (0.15, 0.001, 0.001), "arm"))
    #  ⚠ **상자**(body)에서 삼각형 1장을 뺀다 — 봉(arm)이 아니라. 뒤에 있는 면을 그냥 지우면
    #    엉뚱한 부품에 구멍이 뚫려 대조가 헛돈다(첫 판에서 실제로 그랬다).
    kill = [i for i, g in enumerate(m.g) if g == "body"][0]
    m.f = [f for i, f in enumerate(m.f) if i != kill]
    m.g = [g for i, g in enumerate(m.g) if i != kill]
    c = mp.placement_census(m, "_synthetic")
    parts = mp.split_parts(m)
    box = [p for p in parts if p.group == "body"][0]
    r = mp.pair_relation(box, [p for p in parts if p.group == "arm"][0])
    _say("B6 양성대조: 구멍 난 컨테이너 + 관통",
         (not box.watertight) and len(c["blind_parts"]) == 1
         and r["relation"] == "R2_관통" and r["containment_seen"] is False,
         f"컨테이너 수밀 {box.watertight} · 못본부품 {len(c['blind_parts'])}개(보고됨) · "
         f"내부판정 성립 {r['containment_seen']} · 그래도 판정 {r['relation']}"
         f"(교차쌍 {r['cross_pairs']})")


# --------------------------------------------------------------------------- #
#  C. 사각지대 선언 — 못 잡는 것을 **시험해서** 못 잡는다고 기록한다
# --------------------------------------------------------------------------- #
def test_C1_shallow_limit():
    """⭐한계선언 ①: **교차 잣대**는 1 µm 보다 얕은 파고듦을 안 센다.
    왜 그렇게 정했는지는 mesh_placement.CROSS_PEN_MIN_M 주석에 있다 — 그 척도에서는 독립
    구현끼리도 답이 갈린다(실제 메쉬에서 32 % 불일치).
    ⚠ 이것은 **교차 잣대의 한계**다. 내부판정은 더 얕은 것도 볼 수 있다(면 하나가 통째로 들면).
      그래서 여기서는 판정 전체가 아니라 **교차 잣대 자체**를 시험한다 — 한계는 정확히
      그 자리에 있고, 그 자리에만 있다."""
    T = np.array([[0., 0, 0], [0.01, 0, 0], [0, 0.01, 0]])      # xy 평면 위 삼각형
    F = np.array([[0, 1, 2]])
    i0, j0 = np.array([0]), np.array([0])
    out = []
    for depth in (1e-7, 1e-5):                                   # 0.1 µm · 10 µm 파고듦
        S = np.array([[0.002, 0.002, -depth], [0.004, 0.002, 0.005], [0.003, 0.004, 0.005]])
        out.append(bool(mp.tri_tri_cross_mask(T, F, S, F, i0, j0)[0]))
    _say("C1 한계선언: 교차 잣대는 0.1 µm 를 안 센다",
         out == [False, True],
         f"0.1 µm 파고듦 → 교차 {out[0]} (못 잡는다고 선언한 자리) · "
         f"10 µm → 교차 {out[1]} (잡는다). ⚠내부판정은 이보다 얕은 겹침도 본다(B4 맞물린 상자)")


def test_C2_face_center_granularity():
    """⭐한계선언 ②: 내부판정의 알갱이는 **면 중심 한 점**이다(매몰면 검사와 같은 규약).
    면의 절반만 상대 솔리드 안에 있으면 그 면은 «전부 안» 또는 «전부 밖» 으로 세어진다."""
    m = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                 ((0.05, 0.02, 0.02), (0.15, 0.04, 0.04), "arm"))   # 절반만 들어간 봉
    parts = mp.split_parts(m)
    r = mp.pair_relation(parts[0], parts[1])
    _say("C2 한계선언: 알갱이는 면 중심 한 점",
         r["relation"] == "R2_관통",
         f"판정 {r['relation']} · 봉의 {r['b_in_a_pct']} % 가 상자 안으로 세어짐 "
         f"(면 단위 반올림 — 부분 매몰의 정확한 면적은 이 검사의 몫이 아니다)")


def test_C4_exact_duplicate():
    """⭐**완전히 같은 자리에 복제된 부품** — PO 가 같은 껍질을 두 번 더하는 최악의 자리.

    이 판이 까다로운 이유: 좌표가 같으면 웰딩이 두 껍질의 정점을 합쳐 버려서 «두 부품» 이라는
    구분 자체가 사라진다. 그러면 부품쌍 검사가 통째로 무력해질 것 같다 — **실제로는 아니다.**
    모서리를 네 삼각형이 쓰게 되어(비다양체) 부품 분해가 삼각형 단위로 잘게 쪼개지고,
    그 조각들이 서로 **동일평면**으로 잡힌다. 그 사실을 여기 기록으로 박아 둔다."""
    m = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                 ((0., 0, 0), (0.1, 0.1, 0.1), "body"))          # 완전 복제
    c = mp.placement_census(m, "_synthetic")
    pct = c["coplanar"]["area_pct"]
    _say("C4 양성대조: 완전히 겹친 복제 부품", pct > 99.0,
         f"동일평면 면적 {c['coplanar']['area_mm2']} mm² = 표면적의 {pct} % "
         f"(부품 분해는 삼각형 {c['n_parts']}개로 쪼개진다 — 비다양체 모서리 때문. "
         f"판정은 살아 있고 오히려 크게 보인다)")


def test_C3_absolute_placement():
    """⭐한계선언 ③: 이 파일은 **상대 관계**만 본다. «부품이 있어야 할 자리에 있는가»(절대 배치)는
    안 본다 — 두 부품을 통째로 100 mm 옮겨도 관계표는 **한 글자도 안 변한다.**"""
    d = np.array([0.1, 0.2, 0.3])                      # 두 부품을 **똑같이** 옮긴다
    a = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                 ((0.1, 0.02, 0.02), (0.2, 0.04, 0.04), "arm"))
    b = _mesh_of((tuple(d), tuple(d + 0.1), "body"),
                 (tuple(d + [0.1, 0.02, 0.02]), tuple(d + [0.2, 0.04, 0.04]), "arm"))
    ca = mp.placement_census(a, "_synthetic")
    cb = mp.placement_census(b, "_synthetic")
    _say("C3 한계선언: 절대 배치는 안 본다",
         ca["relation_sha1"] == cb["relation_sha1"],
         f"100 mm 옮겨도 관계지문 같음 {ca['relation_sha1'][:12]} — 절대 좌표는 다른 범주의 몫")


# --------------------------------------------------------------------------- #
#  D. 봉인 — 결정성 · 실제 함대
# --------------------------------------------------------------------------- #
def test_D1_determinism():
    """같은 형상이면 **같은 답**이어야 한다(관계지문 = 봉인의 열쇠)."""
    m = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                 ((0.02, 0, 0), (0.12, 0.1, 0.1), "body"),
                 ((0.5, 0, 0), (0.6, 0.1, 0.1), "arm"))
    h = [mp.placement_census(m, "_synthetic")["relation_sha1"] for _ in range(2)]
    _say("D1 봉인: 같은 형상 → 같은 관계지문", h[0] == h[1], f"{h[0][:16]} ↔ {h[1][:16]}")


def test_D2_seal_positive():
    """⭐봉인 **양성 대조** — 형상을 1 nm 만 건드려도 지문이 달라지는가.
    («같으면 같다» 만 보이면 봉인이 아니다. «다르면 다르다» 를 같이 보여야 봉인이다.)"""
    import copy
    m = _mesh_of(((0., 0, 0), (0.1, 0.1, 0.1), "body"),
                 ((0.02, 0.03, 0.04), (0.12, 0.13, 0.14), "body"))
    h0 = mp.fingerprint(m)
    m2 = copy.deepcopy(m)
    x, y, z = m2.v[0]
    m2.v[0] = (x + 1e-9, y, z)                       # 1 nm 이동
    m3 = copy.deepcopy(m)
    m3.g = ["canopy" if i == 0 else g for i, g in enumerate(m3.g)]   # 라벨 1장만 변경
    _say("D2 봉인 양성대조: 1 nm·라벨 1장",
         mp.fingerprint(m2) != h0 and mp.fingerprint(m3) != h0,
         f"원본 {h0[:10]} · 1 nm 옮김 {mp.fingerprint(m2)[:10]} · "
         f"라벨 1장 바꿈 {mp.fingerprint(m3)[:10]} — 셋이 다 달라야 한다")


def test_D3_fleet(keys=("mini5pro",)):
    """실제 기체 음성 대조 — 예산 안에 드는가. (전 기종은 인증서 스크립트가 돈다.)"""
    from drones import DRONES, build_drone
    for k in keys:
        try:
            m = build_drone(DRONES[k])
        except Exception as e:                                  # noqa: BLE001
            _say(f"D3 함대 음성대조: {k}", False, f"⛔ 빌드 실패 {type(e).__name__}: {e}")
            continue
        c = mp.placement_census(m, k)
        v = mp.check_placement(c)
        _say(f"D3 함대 음성대조: {k}", v["ok"],
             f"관계 {c['relations']} · 자기교차 {c['self_intersection']['n_pairs']} · "
             f"동일평면 {c['coplanar']['area_pct']} % · 판정 {v['failures'] or '통과'}")


def test_D4_fleet_vs_independent(key="mini5pro", max_parts=6):
    """⭐실제 기체 위에서 **독립 구현과 전수 대조** — 거짓양성이 0 인가.
    (합성 대조는 «내가 만든 상황» 이라 무르다. 진짜 메쉬의 슬리버·씨접합에서도 맞아야 한다.)"""
    from drones import DRONES, build_drone
    try:
        m = build_drone(DRONES[key])
    except Exception as e:                                      # noqa: BLE001
        _say(f"D4 실제메쉬 ↔ 독립구현({key})", False, f"⛔ 빌드 실패 {type(e).__name__}: {e}")
        return
    parts = sorted(mp.split_parts(m), key=lambda p: -len(p.F))[:max_parts]
    fp = fn = hit = tot = 0
    pen_fn = []
    for p in parts:
        i, j = mp._candidate_tri_pairs(p.C, p.R, p.C, p.R)
        s = i < j
        i, j = i[s], j[s]
        share = (p.F[i][:, :, None] == p.F[j][:, None, :]).any(axis=(1, 2))
        i, j = i[~share], j[~share]
        if not len(i):
            continue
        T = p.V[p.F]
        lo, hi = T.min(1), T.max(1)
        ov = np.all(lo[i] <= hi[j] + 1e-12, axis=1) & np.all(lo[j] <= hi[i] + 1e-12, axis=1)
        i, j = i[ov], j[ov]
        if not len(i):
            continue
        got = mp.tri_tri_cross_mask(p.V, p.F, p.V, p.F, i, j)
        bf = np.array([_brute_cross(p.V[p.F[a]], p.V[p.F[b]]) for a, b in zip(i, j)])
        fp += int((got & ~bf).sum())
        miss = ~got & bf
        fn += int(miss.sum())
        hit += int(got.sum())
        tot += len(i)
        if miss.any():
            _, _, pen = mp.tri_tri_cross_mask(p.V, p.F, p.V, p.F, i[miss], j[miss],
                                              min_pen=0.0, want_len=True)
            pen_fn.append(pen)
    pf = np.concatenate(pen_fn) if pen_fn else np.zeros(0)
    deep_miss = int((pf >= mp.CROSS_PEN_MIN_M).sum())
    _say(f"D4 실제메쉬 ↔ 독립구현({key})", fp == 0 and deep_miss == 0,
         f"후보 {tot} · 거짓양성 {fp} · 답 갈린 것 {fn}건인데 **전부 파고듦 < 1 µm** "
         f"(1 µm 넘는 놓침 {deep_miss}) — 선언한 사각지대 안")


def main():
    print("=" * 100)
    print("배치·겹침·묻힘 검사기 적대 시험 — 결함을 지어 넣고 잡는지 본다 (양성 + 음성 대조)")
    print("=" * 100)
    print("\n[A. 원시함수 — 판정의 바닥]")
    test_A0_box_normals()
    test_A1_tri_tri_known()
    test_A2_tri_tri_random()
    test_A3_point_triangle()
    test_A4_points_to_surface()
    print("\n[B. 결함 대조 — 심으면 걸리는가]")
    test_B1_floating()
    test_B2_big_box_thin_rod()
    test_B3_self_intersection()
    test_B4_crossing_and_engulf()
    test_B5_coplanar()
    test_B6_blind_container()
    print("\n[C. 사각지대 — 못 잡는 것을 시험해서 기록한다]")
    test_C1_shallow_limit()
    test_C2_face_center_granularity()
    test_C3_absolute_placement()
    test_C4_exact_duplicate()
    print("\n[D. 봉인 · 실제 함대]")
    test_D1_determinism()
    test_D2_seal_positive()
    if "--fleet" in sys.argv:
        test_D3_fleet()
        test_D4_fleet_vs_independent()
    else:
        print("  (함대 대조는 --fleet 로. 인증서 스크립트가 전 기종을 돈다.)")

    n_ok = sum(1 for _, p, _ in RESULTS if p)
    print("\n" + "=" * 100)
    print(f"결과: {n_ok}/{len(RESULTS)} 통과")
    if n_ok < len(RESULTS):
        print("놓친 항목:")
        for tag, p, d in RESULTS:
            if not p:
                print(f"  ❌ {tag} — {d}")
        return 1
    print("⇒ 배치·겹침·묻힘 5범주 전부 «양성 대조 + 음성 대조» 를 통과했고, 사각지대는 선언됐다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
