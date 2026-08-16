# -*- coding: utf-8 -*-
"""
adv_mesh_topo_faults.py — **위상·이산화 검사기를 검사한다**(양성 대조 + 음성 대조)
==============================================================================
왜 이 파일이 있나
  이 저장소의 규약은 하나다 — «검사가 있다» 고 말하려면 **결함을 일부러 심어서 걸리는 것**을
  보여야 한다(양성 대조). 그리고 멀쩡한 것이 통과하는 것도 보여야 한다(음성 대조).
  둘 중 하나만 있으면 «0 이 나오는 검사기» 와 «0 이 맞는 대상» 을 구별할 수 없다.
  형식은 기존 `benchmark/adv_mesh_check_faults.py` 를 그대로 따른다.

무엇을 시험하나 — `src/mesh_topo_check.py` 의 검사 8종 전부.
  T1 닫힘        · T2 법선 일관성 · T3 다양체(⭐나비넥타이) · T4 ⭐자기교차 · T5 퇴화 삼각형
  D1 파장 대비 크기(⭐눈금검증 포함) · D2 로프트 스플라인 오버슛 · D3 ⭐끝단 캡 손실

⭐ 특별히 두 가지를 더 한다(단순 «걸린다» 보다 강한 주장):
  ① **공백 증명** — 나비넥타이·자기교차는 기존 `mesh_check` 가 **통과시킨다**는 것을 같은
     메쉬로 보인다. 즉 «새 검사가 진짜 새 자리를 본다» 를 증거로 남긴다.
  ② **눈금 검증** — D1 의 사지타 추정기가 해석적 참값(원통·구의 r(1−cos))과 몇 % 안에서
     맞는지 잰다. 잣대 자체가 틀리면 양성/음성 대조는 의미가 없다.

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/adv_mesh_topo_faults.py
      ⛔ GPU 안 쓴다. 파일도 안 쓴다(읽기 + 화면 출력). 나가는 값: 전부 통과 0, 하나라도 실패 1.
"""
from __future__ import annotations

import copy
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import mesh_check                                          # noqa: E402
import mesh_topo_check as mt                               # noqa: E402
import cadkit                                              # noqa: E402
import drone_cad                                           # noqa: E402
from geom import Mesh, cylinder, uv_sphere                  # noqa: E402
from drones import DRONES, build_drone                      # noqa: E402
#  상자 만드는 헬퍼는 기존 적대 시험 파일 것을 **그대로 쓴다**(같은 규약·중복 금지)
from adv_mesh_check_faults import _box, _clean_box_mesh     # noqa: E402

RESULTS: list[dict] = []
LAM = mt.C0 / mt.FC_DEFAULT_HZ            # 85.65 mm @ 3.5 GHz


def _say(tag: str, passed: bool, detail: str, kind: str = "positive"):
    RESULTS.append(dict(tag=tag, passed=bool(passed), detail=detail, kind=kind))
    print(f"  {'✅' if passed else '❌'} {tag:44s} {detail}")


def _topo(mesh, name="_synthetic", self_int=True):
    return mt.check_topology(mesh, name=name, self_int=self_int)


def _g(res, grp="body"):
    return res["groups"][grp]


# --------------------------------------------------------------------------- #
#  T1 — 닫힘: 경계 «모서리» 가 아니라 경계 «곡선»(구멍) 을 센다
# --------------------------------------------------------------------------- #
def test_closure():
    ok = _topo(_clean_box_mesh())
    _say("T1 음성대조: 멀쩡한 상자",
         ok["ok"] and _g(ok)["boundary_curves"] == 0 and _g(ok)["boundary_edges"] == 0,
         f"경계곡선 {_g(ok)['boundary_curves']} · 경계모서리 {_g(ok)['boundary_edges']} · "
         f"판정 {ok['ok']}", kind="negative")

    m = _clean_box_mesh(); m.f = m.f[:-1]; m.g = m.g[:-1]      # 삼각형 1장 제거
    r1 = _topo(m)
    _say("T1 양성대조: 구멍 1개", (not r1["ok"]) and _g(r1)["boundary_curves"] == 1
         and _g(r1)["boundary_edges"] == 3,
         f"경계곡선 {_g(r1)['boundary_curves']} · 경계모서리 {_g(r1)['boundary_edges']}")

    #  ⭐ 곡선을 세는 것의 값어치 — 「모서리 6개」는 «구멍 1개(육각)» 일 수도 «구멍 2개» 일
    #    수도 있다. **마주보는** 두 면(x− 와 x+)에서 한 장씩 지워 정점이 안 겹치는 구멍 2개를
    #    만든다(옆면에서 지우면 두 구멍이 꼭짓점을 공유해 테두리가 한 덩이로 이어진다).
    m2 = _clean_box_mesh()
    keep = [i for i in range(len(m2.f)) if i not in (0, 2)]     # x− 1장 + x+ 1장
    m2.f = [m2.f[i] for i in keep]; m2.g = [m2.g[i] for i in keep]
    r2 = _topo(m2)
    _say("T1 양성대조: 구멍 2개(모서리 수로는 구별 불가)",
         (not r2["ok"]) and _g(r2)["boundary_curves"] == 2 and _g(r2)["boundary_edges"] == 6,
         f"경계곡선 {_g(r2)['boundary_curves']} · 경계모서리 {_g(r2)['boundary_edges']} "
         f"— 모서리만 세면 «6» 하나로 뭉개진다")


# --------------------------------------------------------------------------- #
#  T2 — 법선 일관성: 감김 뒤집힘 ↔ 부호부피, **서로 다른 두 결함**
# --------------------------------------------------------------------------- #
def test_normals():
    ok = _topo(_clean_box_mesh())
    _say("T2 음성대조: 멀쩡한 상자",
         _g(ok)["flipped_edges"] == 0 and _g(ok)["negative_volume_parts"] == 0,
         f"감김뒤집힘 {_g(ok)['flipped_edges']} · 부호부피<0 부품 "
         f"{_g(ok)['negative_volume_parts']}", kind="negative")

    m = _clean_box_mesh(); m.f = [(a, c, b) for (a, b, c) in m.f]     # 전면 반전
    r = _topo(m)
    _say("T2 양성대조: 법선 전체 안쪽",
         (not r["ok"]) and _g(r)["negative_volume_parts"] == 1 and _g(r)["flipped_edges"] == 0,
         f"부호부피<0 부품 {_g(r)['negative_volume_parts']} · 감김뒤집힘 "
         f"{_g(r)['flipped_edges']} (전면 반전은 감김이 여전히 일관적 — 두 축이 다르다)")

    m = _clean_box_mesh()
    m.f[3] = (m.f[3][0], m.f[3][2], m.f[3][1])                        # 한 장만 반전
    r = _topo(m)
    _say("T2 양성대조: 한 장만 감김 반전",
         (not r["ok"]) and _g(r)["flipped_edges"] == 3,
         f"감김뒤집힘 모서리 {_g(r)['flipped_edges']}개 (그 삼각형의 세 변)")


# --------------------------------------------------------------------------- #
#  T3 — 다양체: 모서리(기존 축) + ⭐나비넥타이 정점(새 축) + 중복 삼각형
# --------------------------------------------------------------------------- #
def _bowtie_mesh():
    """상자 2개가 **정점 하나만** 공유한다. 모서리는 하나도 공유하지 않는다."""
    m = Mesh("body")
    _box(m, (0.0, 0.0, 0.0), (0.1, 0.1, 0.1), "body")
    _box(m, (0.1, 0.1, 0.1), (0.2, 0.2, 0.2), "body")
    return m


def test_manifold():
    ok = _topo(_clean_box_mesh())
    _say("T3 음성대조: 멀쩡한 상자",
         _g(ok)["nonmanifold_edges"] == 0 and _g(ok)["bowtie_vertices"] == 0
         and _g(ok)["duplicate_faces"] == 0,
         f"비다양체 {_g(ok)['nonmanifold_edges']} · 나비넥타이 {_g(ok)['bowtie_vertices']} · "
         f"중복면 {_g(ok)['duplicate_faces']}", kind="negative")

    #  ⑴ 비다양체 모서리 — 기존 상자 모서리에 «지느러미» 삼각형 한 장을 더 붙인다
    m = _clean_box_mesh()
    a, b, _c = m.f[0]
    d = m.add_vertex(-0.05, -0.05, 0.05)
    m.add_tri(a, b, d, group="body")
    r = _topo(m)
    _say("T3 양성대조: 비다양체 모서리(지느러미)",
         (not r["ok"]) and _g(r)["nonmanifold_edges"] >= 1 and _g(r)["max_edge_multiplicity"] >= 3,
         f"비다양체 모서리 {_g(r)['nonmanifold_edges']} · 최대 다중도 "
         f"{_g(r)['max_edge_multiplicity']}")

    #  ⑵ ⭐나비넥타이 — 이 라운드의 핵심. 지도 M3 «없음» 칸이다.
    bt = _bowtie_mesh()
    r = _topo(bt)
    _say("T3 양성대조: ⭐나비넥타이 정점",
         (not r["ok"]) and _g(r)["bowtie_vertices"] == 1
         and _g(r)["nonmanifold_edges"] == 0 and _g(r)["boundary_edges"] == 0,
         f"나비넥타이 {_g(r)['bowtie_vertices']}개 · 비다양체 모서리 "
         f"{_g(r)['nonmanifold_edges']} · 경계모서리 {_g(r)['boundary_edges']} "
         f"(모서리 세기로는 **완전히 정상**으로 보인다)")

    #  ⭐ 공백 증명 — 같은 메쉬를 기존 검사기에 먹인다
    old = mesh_check.check_mesh(bt, name="_synthetic")
    _say("T3 공백증명: 기존 mesh_check 는 나비넥타이를 통과시킨다", old["ok"],
         f"mesh_check 판정 {old['ok']} · watertight "
         f"{old['groups']['body']['watertight']} · 경계모서리 "
         f"{old['groups']['body']['boundary_edges']} — 새 검사가 없으면 놓친다",
         kind="gap")

    #  ⑶ 중복 삼각형
    m = _clean_box_mesh()
    m.add_tri(*m.f[0], group="body")
    r = _topo(m)
    _say("T3 양성대조: 중복 삼각형",
         (not r["ok"]) and _g(r)["duplicate_faces"] == 1,
         f"중복면 {_g(r)['duplicate_faces']}장 (PO 는 이 면적을 두 번 더한다)")


# --------------------------------------------------------------------------- #
#  T4 — ⭐자기교차: 껍질 하나가 스스로를 뚫는다
# --------------------------------------------------------------------------- #
def _self_pierce_mesh():
    """원통 껍질의 한 정점을 **축 건너편으로** 밀어 껍질이 스스로를 관통하게 만든다.

    ⚠ 상자 꼭짓점을 반대면 너머로 미는 판은 **안 걸린다** — 그 꼭짓점의 면들은 반대면 면들과
      정점을 공유해서 «이웃» 으로 걸러지기 때문이다(정직하게 적어 둔다: 첫 시도가 그랬다).
      원통은 반대쪽 벽과 정점을 공유하지 않아 진짜 자기교차가 된다."""
    m = cylinder(0.05, 0.10, seg=16, caps=True, group="body")
    v = list(m.v)
    #  옆면 링의 한 정점(윗링 0번)을 원통 반대쪽 벽 **너머**로 민다
    v[1] = (-0.12, v[1][1], v[1][2])
    m.v = v
    return m


def test_self_intersection():
    clean = _topo(_clean_box_mesh())
    _say("T4 음성대조: 멀쩡한 상자", clean["ok"] and _g(clean)["self_int_hits"] == 0
         and _g(clean)["self_int_unchecked_parts"] == 0,
         f"자기교차 {_g(clean)['self_int_hits']} · 미검사 부품 "
         f"{_g(clean)['self_int_unchecked_parts']}", kind="negative")

    m = _self_pierce_mesh()
    r = _topo(m)
    _say("T4 양성대조: ⭐자기교차(꼭짓점이 반대면 관통)",
         (not r["ok"]) and _g(r)["self_int_hits"] > 0,
         f"교차 삼각형쌍 {_g(r)['self_int_hits']} · 경계모서리 {_g(r)['boundary_edges']} · "
         f"비다양체 {_g(r)['nonmanifold_edges']}")

    old = mesh_check.check_mesh(m, name="_synthetic")
    _say("T4 공백증명: 기존 mesh_check 는 자기교차를 통과시킨다", old["ok"],
         f"mesh_check 판정 {old['ok']} · watertight {old['groups']['body']['watertight']} "
         f"— 수밀·감김·법선·구멍이 전부 정상이라 안 걸린다", kind="gap")

    #  ⚠ 거짓경보 시험 — **맞닿기만** 하는 두 상자(면을 공유)는 교차가 아니다.
    m2 = Mesh("body")
    _box(m2, (0.0, 0.0, 0.0), (0.1, 0.1, 0.1), "body")
    _box(m2, (0.1, 0.0, 0.0), (0.2, 0.1, 0.1), "body")
    r2 = _topo(m2)
    _say("T4 음성대조: 면이 맞닿은 상자 2개(설계)", _g(r2)["self_int_hits"] == 0,
         f"교차 {_g(r2)['self_int_hits']} — 맞닿음을 결함으로 부르지 않는다", kind="negative")

    #  실기체 음성 대조
    real = _topo(build_drone(DRONES["mavic4pro"]), name="mavic4pro")
    n_si = sum(v["self_int_hits"] for v in real["groups"].values())
    n_un = sum(v["self_int_unchecked_parts"] for v in real["groups"].values())
    _say("T4 음성대조: 실기체 mavic4pro", n_si == 0 and n_un == 0,
         f"자기교차 {n_si} · 미검사 부품 {n_un} (부품 "
         f"{sum(v['n_parts'] for v in real['groups'].values())}개 전수)", kind="negative")


# --------------------------------------------------------------------------- #
#  T5 — 퇴화 삼각형: 인덱스 중복 · 면적 0 · 슬리버
# --------------------------------------------------------------------------- #
def test_degenerate():
    ok = _topo(_clean_box_mesh())
    _say("T5 음성대조: 멀쩡한 상자",
         _g(ok)["repeat_index_faces"] == 0 and _g(ok)["zero_area_faces"] == 0
         and _g(ok)["zero_len_edges"] == 0,
         f"인덱스중복 {_g(ok)['repeat_index_faces']} · 면적0 {_g(ok)['zero_area_faces']} · "
         f"길이0모서리 {_g(ok)['zero_len_edges']} · 최소내각 {_g(ok)['min_angle_deg']}°",
         kind="negative")

    m = _clean_box_mesh()
    a, b, _ = m.f[0]
    m.add_tri(a, a, b, group="body")                 # (a,a,b)
    r = _topo(m)
    _say("T5 양성대조: 인덱스 중복 (a,a,b)",
         (not r["ok"]) and _g(r)["repeat_index_faces"] == 1,
         f"인덱스중복 {_g(r)['repeat_index_faces']}장 — PO 는 이 면을 조용히 버린다"
         f"(rcs_po.mesh_to_points 의 area<1e-12 continue)")

    m = _clean_box_mesh()
    p = m.add_vertex(0.0, 0.0, 0.2); q = m.add_vertex(0.05, 0.0, 0.2)
    s = m.add_vertex(0.1, 0.0, 0.2)                  # 일직선 3점 → 면적 0
    m.add_tri(p, q, s, group="body")
    r = _topo(m)
    _say("T5 양성대조: 면적 0(일직선 3점)",
         (not r["ok"]) and _g(r)["zero_area_faces"] == 1,
         f"면적0 {_g(r)['zero_area_faces']}장 · 최소내각 {_g(r)['min_angle_deg']}°")

    m = _clean_box_mesh()
    for i in range(100):
        p = m.add_vertex(0.0, 0.0, 0.2 + 1e-3 * i)
        q = m.add_vertex(0.1, 0.0, 0.2 + 1e-3 * i)
        s = m.add_vertex(0.1, 1e-7, 0.2 + 1e-3 * i)
        m.add_tri(p, q, s, group="body")
    r = _topo(m)
    _say("T5 양성대조: 슬리버 100장",
         _g(r)["slivers"] >= 100 and _g(r)["min_angle_deg"] < mt.SLIVER_MIN_ANGLE_DEG,
         f"슬리버 {_g(r)['slivers']}장 · 최소내각 {_g(r)['min_angle_deg']}° · "
         f"p99 종횡비 {_g(r)['p99_aspect']}")


# --------------------------------------------------------------------------- #
#  D1 — 파장 대비 삼각형 크기.  ⭐먼저 **잣대의 눈금**을 해석해와 맞춰 본다
# --------------------------------------------------------------------------- #
def _facet(mesh, lam=LAM):
    V = np.asarray(mesh.v, float); F = np.asarray(mesh.f, np.int64)
    Vw, Fw, _ = mt.weld(V, F)
    return mt.facet_wavelength(Vw, Fw, lam)


def test_wavelength():
    #  ⭐ 눈금 검증 — 원통·구의 **해석적** 사지타 r(1−cos(π/seg)) 와 견준다.
    rows = []
    for r_m, seg in ((0.012, 20), (0.05, 32), (0.20, 12), (0.50, 24)):
        f = _facet(cylinder(r_m, 0.30, seg=seg, caps=False, group="body"))
        want = 1000.0 * r_m * (1 - math.cos(math.pi / seg))
        got = f["max_sagitta_mm"]
        rows.append((f"원통 r={1000*r_m:.0f}mm seg={seg}", want, got,
                     abs(got - want) / max(want, 1e-12)))
    for r_m, seg, rings in ((0.05, 24, 12), (0.30, 32, 16)):
        f = _facet(uv_sphere(r_m, seg=seg, rings=rings, group="body"))
        want = 1000.0 * r_m * (1 - math.cos(math.pi / seg))
        got = f["max_sagitta_mm"]
        rows.append((f"구 r={1000*r_m:.0f}mm seg={seg}", want, got,
                     abs(got - want) / max(want, 1e-12)))
    worst = max(x[3] for x in rows)
    _say("D1 눈금검증: 사지타 추정 ↔ 해석값", worst < 0.15,
         "  ".join(f"{n}: {w:.3f}→{g:.3f} mm({100*e:+.1f}%)" for n, w, g, e in rows[:3])
         + f"  … 최악 오차 {100*worst:.1f} %", kind="calibration")

    #  음성 대조 — 촘촘한 원통(드론 부품 크기)
    fine = _facet(cylinder(0.012, 0.30, seg=20, caps=True, group="body"))
    _say("D1 음성대조: 촘촘한 원통(스키드 튜브 크기)",
         fine["sagitta_over_lam16_area_pct"] == 0.0,
         f"사지타 {fine['max_sagitta_mm']} mm = λ/{LAM*1000/max(fine['max_sagitta_mm'],1e-9):.0f} "
         f"(허용 λ/16 = {1000*LAM/16:.2f} mm) · 위반면적 "
         f"{fine['sagitta_over_lam16_area_pct']} %", kind="negative")

    #  ⭐양성 대조 — 성긴 곡면(반지름 0.5 m · 분할 14. 이면각 25.7° 로 «매끈» 구간 안이다)
    coarse = _facet(cylinder(0.5, 0.6, seg=14, caps=False, group="body"))
    _say("D1 양성대조: 성긴 곡면(r=500mm·seg=14)",
         coarse["sagitta_over_lam16_area_pct"] > mt.SAGITTA_AREA_PCT_BUDGET["_default"],
         f"사지타 {coarse['max_sagitta_mm']} mm > λ/16 = {1000*LAM/16:.2f} mm · "
         f"위반면적 {coarse['sagitta_over_lam16_area_pct']} %")

    #  ⭐음성 대조(판별력) — **큰 평면**은 삼각형이 아무리 커도 이산화 오차가 없다
    plate = Mesh("body")
    i0 = plate.add_vertex(-0.5, -0.5, 0.0); i1 = plate.add_vertex(0.5, -0.5, 0.0)
    i2 = plate.add_vertex(0.5, 0.5, 0.0); i3 = plate.add_vertex(-0.5, 0.5, 0.0)
    plate.add_quad(i0, i1, i2, i3, group="body")
    fp = _facet(plate)
    _say("D1 음성대조(판별력): 1 m 평판(변 = 16.5 λ)",
         fp["sagitta_over_lam16_area_pct"] == 0.0 and fp["max_edge_over_lam"] > 10,
         f"최대변 {fp['max_edge_mm']} mm = {fp['max_edge_over_lam']}λ 인데 사지타 "
         f"{fp['max_sagitta_mm']} mm — 평면은 크기가 커도 오차가 아니다"
         f"(PO 는 λ/7 로 다시 쪼갠다)", kind="negative")

    #  실기체 음성 대조 + 여유 보고
    real = _topo(build_drone(DRONES["s1000plus"]), name="s1000plus", self_int=False)
    d = real["discretization"]
    _say("D1 음성대조: 실기체 s1000plus(가장 빠듯한 기체)",
         d["ok"], f"사지타 위반면적 {d['sagitta_over_lam16_area_pct']} % · 최대 사지타 "
         f"{d['max_sagitta_mm']} mm = λ/16 의 "
         f"{d['max_sagitta_mm']/(1000*LAM/16):.2f} 배", kind="negative")


# --------------------------------------------------------------------------- #
#  D2 — 로프트 스플라인 오버슛
# --------------------------------------------------------------------------- #
def test_loft_overshoot():
    xs = np.array([-0.10, -0.06, -0.01, 0.036, 0.076, 0.10])
    flat = np.linspace(0.02, 0.05, 6)                       # 일직선 → 3차 보간도 직선
    a, pct, _ = mt._spline_overshoot(xs, flat)
    _say("D2 음성대조: 단조(일직선) 제어점", pct < 0.01,
         f"오버슛 {1000*a:.5f} mm = {pct:.4f} % — 3차 보간이 직선을 그대로 통과한다",
         kind="negative")

    #  ⭐ 가운데가 잘록한 표 — 3차 보간이 양옆에서 **표 위로** 부푼다
    valley = np.array([0.050, 0.050, 0.010, 0.050, 0.050, 0.050])
    a2, pct2, ymin = mt._spline_overshoot(xs, valley)
    _say("D2 양성대조: 잘록한 제어점(스플라인이 부푼다)",
         pct2 > mt.LOFT_OVERSHOOT_PCT_BUDGET["_default"],
         f"오버슛 {1000*a2:.3f} mm = {pct2:.1f} % (예산 "
         f"{mt.LOFT_OVERSHOOT_PCT_BUDGET['_default']} %) · 스플라인 최소 {1000*ymin:.3f} mm")

    #  ⭐ 메쉬로도 확인 — 계산이 아니라 **실제로 그렇게 지어지는가**
    secs = cadkit.spline_sections(xs, valley, valley * 0.8, n_pow=2.9, n_sec=30, n_pts=48)
    m = cadkit.loft(secs, n_pts=48)
    got_hw = 0.5 * float(np.ptp(np.asarray(m.vertices)[:, 1]))
    _say("D2 양성대조(메쉬): 부푼 만큼 실제로 지어진다",
         got_hw > float(valley.max()) * 1.05,
         f"메쉬 최대 반폭 {1000*got_hw:.2f} mm > 설계표 최대 {1000*valley.max():.2f} mm "
         f"({100*(got_hw/valley.max()-1):+.1f} %) — 계산과 메쉬가 같은 말을 한다")

    #  ⭐ 하한 클램프 — 스플라인이 0 밑으로 내려가면 superellipse 가 조용히 0.1 mm 로 바꾼다
    dip = np.array([0.010, 0.010, 0.050, 0.010, 0.010, 0.010])
    _a3, _p3, ymin3 = mt._spline_overshoot(xs, dip)
    secs2 = cadkit.spline_sections(xs, dip, dip, n_pow=2.9, n_sec=30, n_pts=48)
    n_clamp = sum(1 for (_x, p) in secs2 if (p.bounds[2] - p.bounds[0]) <= 2e-4)
    _say("D2 양성대조: 하한 클램프 탐지", n_clamp > 0,
         f"스플라인 최소 {1000*ymin3:+.3f} mm (음수!) → 클램프에 닿은 단면 {n_clamp}개 — "
         f"반폭이 음수로 내려가면 «조용히» 0.1 mm 가 된다")

    #  실기체 음성 대조
    for key in ("matrice4e", "mini5pro"):
        _mesh, rec = mt.instrumented_build(DRONES[key])
        lc = mt.check_loft_caps(DRONES[key], rec=rec)
        _say(f"D2 음성대조: 실기체 {key}", lc["ok"],
             f"오버슛 {lc['max_overshoot_pct']} % (예산 {lc['overshoot_budget_pct']}) · "
             f"클램프 {lc['clamped_sections']}", kind="negative")


# --------------------------------------------------------------------------- #
#  D3 — ⭐끝단 캡: 캡이 있는가 · 끝단 단면을 얼마나 잃었나
# --------------------------------------------------------------------------- #
def test_end_caps():
    #  ⑴ 캡 부재 — loft(cap=False) 는 양 끝이 열린 관이다
    xs = np.linspace(-0.1, 0.1, 6)
    hw = np.array([0.02, 0.03, 0.035, 0.033, 0.025, 0.015])
    secs = cadkit.spline_sections(xs, hw, hw * 0.7, n_pow=2.9, n_sec=20, n_pts=48)
    m_cap = cadkit.loft(secs, n_pts=48, cap=True)
    m_open = cadkit.loft(secs, n_pts=48, cap=False)
    ec_cap = mt.edge_census(np.asarray(m_cap.faces, np.int64))
    ec_open = mt.edge_census(np.asarray(m_open.faces, np.int64))
    _say("D3 음성대조: 캡 있는 로프트", ec_cap["n_boundary"] == 0,
         f"경계모서리 {ec_cap['n_boundary']}", kind="negative")

    Vo = np.asarray(m_open.vertices, float)
    cur = mt.boundary_curves(Vo, np.asarray(m_open.faces, np.int64))
    rings = [c for c in cur if c["is_planar_ring"]]
    _say("D3 양성대조: ⭐끝단 캡 손실(cap=False)",
         ec_open["n_boundary"] == 96 and len(cur) == 2 and len(rings) == 2,
         f"경계모서리 {ec_open['n_boundary']} · 경계곡선 {len(cur)}개 · 그중 «평면 링» "
         f"{len(rings)}개 (지름 {rings[0]['diameter_mm'] if rings else 0:.1f} mm) "
         f"— 캡이 빠진 자리의 지문")

    #  ⑵ ⭐캡 형상 손실 — 스무딩이 끝단 단면을 깎는다.
    #     음성 대조 = 출하 상태(smooth_iters=0) · 양성 대조 = 옛 값(4)
    for key in ("matrice4e", "mavic4pro", "phantom4"):
        sh = drone_cad._SHELL_SHAPE.get(key, drone_cad._SHELL_DEFAULT)
        spec = DRONES[key]
        bl = spec.body_l_mm / 1000.0 * sh["fl"]
        bw = spec.body_w_mm / 1000.0 * sh["fw"]
        bh = spec.body_h_mm / 1000.0 * sh["fh"]

        def _deficit(iters):
            mm = drone_cad._body_folding(bl, bw, bh, nose_drop=sh["ndrop"], n_pow=sh["npow"],
                                         hw_f=sh["hw"], hh_f=sh["hh"], zo_f=sh["zo"],
                                         smooth_iters=iters)
            got = mt._end_station(np.asarray(mm.vertices, float),
                                  np.asarray(mm.faces, np.int64), bl)
            hwf = np.asarray(sh["hw"], float); hhf = np.asarray(sh["hh"], float)
            want = [(hwf[0] * bw * 0.95, hhf[0] * bh), (hwf[-1] * bw * 0.95, hhf[-1] * bh)]
            return max(100.0 if got[i] is None else abs(100.0 * (got[i][j] / want[i][j] - 1.0))
                       for i in (0, 1) for j in (0, 1))

        d0, d4 = _deficit(0), _deficit(4)
        _say(f"D3 음성대조: {key} 출하판(smooth_iters=0)",
             d0 <= mt.CAP_DEFICIT_PCT_BUDGET["_default"],
             f"끝단 단면 오차 {d0:.3f} % (예산 {mt.CAP_DEFICIT_PCT_BUDGET['_default']} %)",
             kind="negative")
        _say(f"D3 양성대조: {key} 옛 판(smooth_iters=4)",
             d4 > mt.CAP_DEFICIT_PCT_BUDGET["_default"],
             f"끝단 단면 손실 {d4:.1f} % — 2026-08-16 이전 상태가 이랬다"
             f"(«−38~−44 %» 선언과 같은 자리)")


# --------------------------------------------------------------------------- #
#  ⭐ 교차 검증 — 두 검사기(trimesh 경로 ↔ numpy 자체 위상)가 같은 답을 내는가
# --------------------------------------------------------------------------- #
def test_cross_check(keys=("mini2", "matrice4e")):
    for key in keys:
        m = build_drone(DRONES[key])
        new = _topo(m, name=key, self_int=False)
        old = mesh_check.check_mesh(m, name=key)
        rows, agree = [], True
        for grp, ov in old["groups"].items():
            nv = new["groups"][grp]
            same = (ov["boundary_edges"] == nv["boundary_edges"]
                    and ov["nonmanifold_edges"] == nv["nonmanifold_edges"]
                    and ov["slivers"] == nv["slivers"]
                    and ov["degenerate"] == nv["zero_area_faces"]
                    and ov["n_parts"] == nv["n_parts"])
            agree &= same
            if not same:
                rows.append(f"{grp}(구 {ov['boundary_edges']}/{ov['nonmanifold_edges']}/"
                            f"{ov['slivers']}/{ov['degenerate']}/{ov['n_parts']} ↔ 신 "
                            f"{nv['boundary_edges']}/{nv['nonmanifold_edges']}/"
                            f"{nv['slivers']}/{nv['zero_area_faces']}/{nv['n_parts']})")
        _say(f"교차검증: {key} — trimesh 경로 ↔ 자체 위상", agree,
             "경계모서리·비다양체·슬리버·퇴화·부품수 전 그룹 일치"
             if agree else " ".join(rows), kind="crosscheck")


def run_all():
    print("=" * 112)
    print("위상·이산화 검사기 적대 시험 — 결함을 심어 걸리는지(양성) · 멀쩡하면 통과하는지(음성)")
    print("=" * 112)
    print("\n[T1 닫힘 — 경계 곡선]")
    test_closure()
    print("\n[T2 법선 일관성 — 감김 ↔ 부호부피]")
    test_normals()
    print("\n[T3 다양체 — 모서리 · ⭐나비넥타이 정점 · 중복면]")
    test_manifold()
    print("\n[T4 ⭐자기교차]")
    test_self_intersection()
    print("\n[T5 퇴화 삼각형]")
    test_degenerate()
    print("\n[D1 파장 대비 삼각형 크기 — ⭐눈금검증 포함]")
    test_wavelength()
    print("\n[D2 로프트 스플라인 오버슛]")
    test_loft_overshoot()
    print("\n[D3 ⭐끝단 캡 손실]")
    test_end_caps()
    print("\n[교차 검증 — 두 검사기가 같은 답을 내는가]")
    test_cross_check()
    return RESULTS


def main():
    res = run_all()
    n_ok = sum(1 for r in res if r["passed"])
    kinds = {}
    for r in res:
        kinds.setdefault(r["kind"], [0, 0])
        kinds[r["kind"]][0] += int(r["passed"]); kinds[r["kind"]][1] += 1
    print("\n" + "=" * 112)
    print(f"결과: {n_ok}/{len(res)} 통과   "
          + " · ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(kinds.items())))
    if n_ok < len(res):
        print("실패 항목:")
        for r in res:
            if not r["passed"]:
                print(f"  ❌ {r['tag']} — {r['detail']}")
        return 1
    print("⇒ 위상·이산화 8축 전부 «양성 대조 + 음성 대조» 를 통과했다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
