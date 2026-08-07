# -*- coding: utf-8 -*-
"""
report15_null_control.py — ⭐⭐ **대조군 B: 널(null) 대조** — 판정의 안전장치
================================================================================

report15_probe.py 는 "로터 위상을 스텝하고 매번 재추적하면 h(φ) 가 흔들린다" 를 재고
그 흔들림이 **재추적 잡음바닥보다 유의하게 크다**고 판정했다. 그 판정은 한 가지를
가정한다 — **흔들리면 안 되는 물체는 흔들리지 않는다**. 이 파일이 그것을 검사한다.

    변조가 나오면 안 되는 물체에서도 변조가 나오면, 그것은 물리가 아니라 **산물**이다.

같은 격자·같은 위상 스텝·같은 관측량(h = Σ a_p·exp(−j2πf_c·τ_p))·같은 판정함수를 쓴다.
측정·통계·판정 코드는 **report15_probe 에서 그대로 import** 한다 — 두 실험이 다른 코드로
재면 비교가 성립하지 않기 때문이다.

팔(arm) 구성 — 지시받은 4 종 + 해석에 필요한 보강
--------------------------------------------------------------------------------
 ①  sphere_*          등가부피 구를 z 축으로 회전 → ⭐ 물리적 변조 **0** 이어야 한다.
                      (플라스틱 / 금속 두 재질, mini2 · matrice4e 두 부피)
 ①' sphere_static     같은 구를 **회전시키지 않고** 매 스텝 OBJ 재작성·씬 재조립·재추적
                      → 파이프라인 자체가 만드는 바닥(기하 변화 0).
 ①" disc_mini2        ⭐⭐ **가장 강한 널**: 프로펠러를 같은 반경·같은 두께의 **회전대칭
                      원판**으로 바꿔 같은 위상으로 돌린다. 물리적 변조는 정확히 0 인데
                      **메쉬 꼭짓점은 블레이드와 똑같은 크기로 움직인다**(rim 변위 = tip 변위).
                      구(球) 널의 약점 — "구는 사실 거의 안 움직인다" — 을 정면으로 막는다.
 ②  yaw_*             드론을 **통째로** 회전(로터가 아니라 기체 전체) → 양성대조.
                      · yaw       : 위상 격자를 그대로 기체 요(yaw) 에 먹인다(0…180°).
                      · yawmatch  : **표면 최대변위를 로터 팁 변위와 같게** 맞춘 작은 요각.
                        (각도는 기하에서 계산한다 — 손으로 고르지 않는다.)
 ③  norotor_mini2     프로펠러 그룹 제거 + 같은 로터 위상 스텝 → 메쉬가 **완전히 동결**된다
                      (위상이 움직일 것이 없다). 블레이드 기여 분리 + 두 번째 완전 널.
 ④  half_mini2        같은 드론을 **삼각형 절반**으로 줄여 같은 로터 스텝
                      → 변조가 메쉬 해상도에 얼마나 의존하나.
                      ⚠ 정지자세에서 삼각형 2→1 개가 −6.05 dB, 1→0 개가 −42.97 dB 였다.
 ⓪  full_mini2        기준 신호. probe 와 같은 조건을 **이 스크립트 안에서 다시** 재서
                      모든 비교가 같은 세션·같은 코드경로 위에 놓이게 한다.

⭐ 팔마다 "얼마나 세게 흔들었나"를 같이 잰다 (drive)
   · vertex_shift  : 같은 인덱스 꼭짓점의 최대 이동거리 — **메쉬가** 얼마나 움직였나
   · surface_shift : φ=0 점군과 φ 점군의 양방향 최근접거리(하우스도르프 근사)
                     — **표면(형상)이** 얼마나 움직였나
   회전대칭체는 vertex_shift 는 크지만 surface_shift 는 ~0 이다. 이 두 숫자를 같이 보지 않으면
   "널이 널인 이유"가 '진짜 대칭' 인지 '아무것도 안 움직여서' 인지 구별되지 않는다.

⛔ src/drones.py · src/drone_cad.py 는 **읽기만** 한다. 분절(articulation)은 그 파일의 공개
   함수(build_frame / build_propeller / rotor_layout)만 조합해 재현하고, 재현이 맞는지
   `pose_articulated` 출력과 **꼭짓점 해시로 대조**해 JSON 에 남긴다(self_check).
⛔ 기존 산출물 덮어쓰기 금지 — 출력은 outputs/report15_null_control.json 하나뿐이다.
⛔ 숫자 손입력 금지 — 구 반경·요각·원판 두께·삼각형 목표 전부 계산해서 JSON 에 담는다.
그림 없음(순수 측정). 본문·주석·print 한국어.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#  ⭐ 측정·통계·판정은 probe 에서 그대로 가져온다 (import 시점에 gpu.pick 이 돌아
#     여유 메모리가 가장 많은 카드를 잡고, 그 다음에 mitsuba/sionna 가 올라온다).
import report15_probe as P                                             # noqa: E402
from report15_probe import (AZ_DEG, BASELINE_M, EL_DEG, FC, LAM,       # noqa: E402
                            MAX_PATHS, RANGE_M, _thin, drop_scratch,
                            id_to_group, judge, place, rt_echo, spread)

from geom import Mesh, cylinder, rotate, translate, uv_sphere          # noqa: E402
from drones import (DRONES, DRONE_GROUP_MAT, build_frame,              # noqa: E402
                    build_propeller, drone_colors, pose_articulated,
                    rotor_layout)
from scene_build import Part, build_scene                              # noqa: E402

import fast_simplification as fsimp                                    # noqa: E402
from scipy.spatial import cKDTree                                      # noqa: E402

SCRATCH = os.path.join(ROOT, "outputs", "meshes", "report15_null")
OUT_JSON = os.path.join(ROOT, "outputs", "report15_null_control.json")
PROBE_JSON = os.path.join(ROOT, "outputs", "report15_probe.json")


# --------------------------------------------------------------------------- #
#  메쉬 계량 (⛔ 손입력 금지 — 전부 여기서 계산)
# --------------------------------------------------------------------------- #
def _VF(m: Mesh):
    return np.asarray(m.v, float), np.asarray(m.f, int)


def mesh_metrics(m: Mesh) -> dict:
    """삼각형 수·꼭짓점 수·부피(발산정리)·표면적·바운딩박스·그룹별 삼각형 수.

    ⚠ 이 메쉬는 '닫힌 프리미티브의 합집합' 이 아니라 **삼각형 수프**다(부품끼리 겹친다).
      따라서 부피는 '겹침을 중복해서 세는 부품별 부피의 합' 이다. 등가부피 구를 정할 때
      그 정의를 쓴다는 사실을 여기 남긴다(다른 정의를 쓰면 반경이 달라진다)."""
    V, F = _VF(m)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    vol = float(np.sum(np.einsum("ij,ij->i", p0, cr)) / 6.0)
    area = float(np.sum(np.linalg.norm(cr, axis=1)) / 2.0)
    b0, b1 = V.min(axis=0), V.max(axis=0)
    gs = {}
    for g in m.groups():
        gs[g] = int(sum(1 for x in m.g if x == g))
    return dict(n_tris=int(F.shape[0]), n_verts=int(V.shape[0]),
                volume_m3=vol, area_m2=area,
                r_equal_volume_m=float((3.0 * abs(vol) / (4.0 * math.pi)) ** (1.0 / 3.0)),
                r_equal_area_m=float(math.sqrt(abs(area) / (4.0 * math.pi))),
                bbox_min=[float(x) for x in b0], bbox_max=[float(x) for x in b1],
                span_m=[float(x) for x in (b1 - b0)],
                tris_by_group=gs,
                note_ko=("부피는 삼각형 수프의 발산정리 합 — 겹치는 부품은 중복 계산된다. "
                         "등가부피 구의 반경은 이 정의를 따른다."))


def drive_metrics(V0: np.ndarray, V1: np.ndarray) -> dict:
    """φ=0 대비 φ 의 **두 가지** 변위.

    · vertex : 같은 인덱스 꼭짓점의 이동거리 — '메쉬 데이터가 얼마나 바뀌었나'
    · surface: 두 점군의 양방향 최근접거리(하우스도르프 근사) — '형상이 얼마나 바뀌었나'
    회전대칭체는 vertex 는 크고 surface 는 ~0 이다. 이 차이가 널 대조의 핵심이다."""
    out = {}
    if V0.shape == V1.shape:
        d = np.linalg.norm(V1 - V0, axis=1)
        out.update(vertex_max_m=float(d.max()), vertex_mean_m=float(d.mean()))
    else:
        out.update(vertex_max_m=None, vertex_mean_m=None)
    t0, t1 = cKDTree(V0), cKDTree(V1)
    d10, _ = t0.query(V1)
    d01, _ = t1.query(V0)
    out.update(surface_max_m=float(max(d10.max(), d01.max())),
               surface_mean_m=float(0.5 * (d10.mean() + d01.mean())))
    return out


# --------------------------------------------------------------------------- #
#  분절 재현 (⛔ drones.py 편집 금지 → 공개 함수 조합으로 pose_articulated 를 재현)
# --------------------------------------------------------------------------- #
def articulate(frame: Mesh, prop_ccw: Mesh, prop_cw: Mesh, spec,
               rotor_phase_deg, body_yaw_deg: float = 0.0) -> Mesh:
    """pose_articulated 와 **같은 식**. 다만 프레임/프로펠러 템플릿을 밖에서 받는다
    (그래야 '프롭 제거' · '삼각형 절반' · '프롭→원판' 을 원본 편집 없이 만들 수 있다).
    self_check 에서 원본 pose_articulated 와 꼭짓점 해시로 대조한다."""
    B = rotate("z", float(body_yaw_deg))
    out = frame.transformed(B)
    rl = rotor_layout(spec)
    if rotor_phase_deg is None:
        rotor_phase_deg = [0.0] * len(rl)
    for rot, ph in zip(rl, rotor_phase_deg):
        cx, cy, cz = rot["center"]
        M = B @ translate(cx, cy, cz) @ rotate("z", rot["base_ang"] + float(ph))
        src = prop_ccw if rot["dir"] > 0 else prop_cw
        if src is not None and src.n_tris():
            out.merge(src.transformed(M), group="prop")
    return out


def rotor_phase_vector(spec, phi_deg: float) -> list:
    """로터별 스핀 = dir_k · φ — probe.posed_mesh 와 **같은 규약**."""
    return [r["dir"] * float(phi_deg) for r in rotor_layout(spec)]


# --------------------------------------------------------------------------- #
#  메쉬 변형기
# --------------------------------------------------------------------------- #
def subset_groups(m: Mesh, drop=(), keep=None) -> Mesh:
    """그룹 단위로 면을 골라낸 새 메쉬 (꼭짓점 배열은 그대로 둔다 — write_obj 가 추린다)."""
    out = Mesh()
    out.v = list(m.v)
    for (f, g) in zip(m.f, m.g):
        if g in drop:
            continue
        if keep is not None and g not in keep:
            continue
        out.f.append(f); out.g.append(g)
    return out


def decimate_by_group(m: Mesh, reduction: float) -> tuple[Mesh, dict]:
    """⭐ **그룹마다 따로** 사분면오차(quadric) 데시메이션 → 그룹(=재질)이 보존된다.
    그룹별 삼각형 수·부피·표면적 변화를 전부 기록한다(작은 그룹은 절반이 안 될 수 있다)."""
    V, F = _VF(m)
    G = np.asarray(m.g, object)
    out = Mesh()
    rep = {}
    for g in m.groups():
        sel = (G == g)
        Fg = F[sel]
        used = np.unique(Fg)
        remap = np.full(V.shape[0], -1, int); remap[used] = np.arange(used.size)
        Vg = V[used].astype(np.float64)
        Fg2 = remap[Fg].astype(np.int32)
        try:
            p2, f2 = fsimp.simplify(Vg, Fg2, target_reduction=float(reduction))
            p2 = np.asarray(p2, float); f2 = np.asarray(f2, int)
        except Exception as e:                                   # 너무 작은 그룹은 그대로 둔다
            p2, f2 = Vg, Fg2.astype(int)
            rep[g] = dict(error=str(e))
        base = len(out.v)
        out.v.extend([tuple(map(float, p)) for p in p2])
        for tri in f2:
            out.f.append((int(tri[0]) + base, int(tri[1]) + base, int(tri[2]) + base))
            out.g.append(g)

        def _va(Vx, Fx):
            if len(Fx) == 0:
                return 0.0, 0.0
            a0, a1, a2 = Vx[Fx[:, 0]], Vx[Fx[:, 1]], Vx[Fx[:, 2]]
            c = np.cross(a1 - a0, a2 - a0)
            return (float(np.sum(np.einsum("ij,ij->i", a0, c)) / 6.0),
                    float(np.sum(np.linalg.norm(c, axis=1)) / 2.0))
        v0, ar0 = _va(Vg, Fg2.astype(int)); v1, ar1 = _va(p2, f2)
        rep.setdefault(g, {}).update(
            tris_before=int(Fg2.shape[0]), tris_after=int(f2.shape[0]),
            kept_frac=float(f2.shape[0] / max(1, Fg2.shape[0])),
            volume_before_m3=v0, volume_after_m3=v1,
            area_before_m2=ar0, area_after_m2=ar1,
            area_change_db=float(20.0 * math.log10(max(ar1, 1e-30) / max(ar0, 1e-30))))
    return out, rep


def _odd(n: int) -> int:
    """⚠⚠ **위상 격자와 테셀레이션의 공약수 함정** — 여기서 한 번 걸렸다(기록).
    z 축 회전체의 메쉬는 φ ≡ 0 (mod 360/seg) 에서 **자기 자신과 정확히 같아진다**.
    위상 격자가 φ_k = k·(180/n_steps) 이므로 조건은 k·seg/(2·n_steps) ∈ ℤ 이고,
    n_steps=32 이면 k·seg/64 ∈ ℤ 다. seg 가 짝수면 k<32 에서도 걸린다
    (실측: matrice4e 구가 seg=200 으로 나와 φ=45·90·135° 에서 메쉬가 **완전히 동일**했다
     → 널이 조용한 것이 '대칭' 때문이 아니라 '아무것도 안 바뀌어서' 였다).
    seg 를 **홀수**로 두면 64 | k·seg 는 64 | k 를 요구하고 k<32 이므로 절대 걸리지 않는다."""
    return int(n) if int(n) % 2 == 1 else int(n) + 1


def sphere_matched(radius: float, target_tris: int) -> tuple[Mesh, dict]:
    """⭐ **삼각형 예산을 드론과 맞춘** 등가부피 구.
    uv_sphere(seg, rings) 의 삼각형 수 = 2·seg·(rings−1). 면이 정사각에 가깝도록 seg≈2·rings
    로 두고 target_tris 에 가장 가까운 (seg, rings) 를 찾는다 — 손으로 고르지 않는다.
    ⚠ 구를 드론보다 성기게 깎으면 '널이 조용한 이유' 가 '대칭' 인지 '면이 커서' 인지 갈리지 않는다.
    ⚠ seg 는 _odd() 로 홀수화한다 — 위상 스텝이 메쉬를 그대로 재현하지 못하게."""
    best = None
    for seg in range(9, 601, 2):
        rings = max(2, int(round(seg / 2)))
        t = 2 * seg * (rings - 1)
        d = abs(t - int(target_tris))
        if best is None or d < best[0]:
            best = (d, seg, rings, t)
    _, seg, rings, t = best
    seg = _odd(seg)
    m = uv_sphere(radius, seg=seg, rings=rings, group="sph")
    facet_eq = 2.0 * math.pi * radius / seg              # 적도 방위 간격
    return m, dict(radius_m=float(radius), seg=int(seg), rings=int(rings), seg_is_odd=True,
                   n_tris=int(m.n_tris()), target_tris=int(target_tris),
                   facet_equator_m=float(facet_eq),
                   facet_equator_lambda=float(facet_eq / LAM),
                   null_mechanism="facet re-orientation (every normal's azimuth rotates)",
                   note_ko=("삼각형 수를 드론과 맞춰 널이 조용한 이유가 '면이 성겨서' 가 아니게 하고, "
                            "seg 를 홀수로 두어 위상 스텝이 메쉬를 재현하지 못하게 했다. "
                            "⭐ 구를 돌리면 **모든 면의 법선 방위가 실제로 회전한다** — 형상은 같지만 "
                            "면의 집합은 다르다. 원판 널(면은 같은 평면·삼각형만 재분할)과 서로 다른 "
                            "고장모드를 검사하므로 둘 다 필요하다."))


def disc_like_prop(prop: Mesh, prop_radius_m: float) -> tuple[Mesh, dict]:
    """⭐⭐ 프로펠러를 **회전대칭 원판**으로 교체 — 물리적 변조는 정확히 0 인데
    메쉬 꼭짓점은 블레이드와 **같은 크기로** 움직인다(rim 변위 = tip 변위).
    반경 = 프롭 반경, 두께 = 프롭 템플릿의 z 두께, 삼각형 수 ≈ 프롭 템플릿과 동일
    (원기둥 삼각형 수 = 4·seg → seg = round(n_tris_prop/4)). seg 는 _odd() 로 홀수화한다."""
    V = np.asarray(prop.v, float)
    thick = float(V[:, 2].max() - V[:, 2].min())
    zc = float(0.5 * (V[:, 2].max() + V[:, 2].min()))
    seg = _odd(max(9, int(round(prop.n_tris() / 4.0))))
    m = cylinder(prop_radius_m, thick, axis="z", center=(0.0, 0.0, zc), seg=seg,
                 caps=True, group="prop")
    rim = 2.0 * math.pi * prop_radius_m / seg
    return m, dict(radius_m=float(prop_radius_m), thickness_m=thick, z_center_m=zc,
                   seg=int(seg), n_tris=int(m.n_tris()),
                   n_tris_prop_template=int(prop.n_tris()),
                   rim_facet_m=float(rim), rim_facet_lambda=float(rim / LAM),
                   null_mechanism="re-triangulation (facet planes invariant)",
                   note_ko=("회전대칭이라 물리적 변조 0. 그러나 rim 꼭짓점은 블레이드 팁과 "
                            "같은 거리를 움직인다 → '구는 안 움직여서 조용했다' 는 반론을 막는다. "
                            "⚠ 다만 원판의 위·아래 면은 회전해도 **같은 평면**에 남고 삼각형만 "
                            "다시 잘린다 — 즉 이 널이 검사하는 것은 '꼭짓점/OBJ 장부가 바뀌는 것만으로 "
                            "변조가 생기나' 다. 면의 **방향**이 바뀌는 경우는 구(球) 널이 맡는다."))


# --------------------------------------------------------------------------- #
#  씬 조립 (probe.build_posed_scene 과 같은 규약, 메쉬만 밖에서 받는다)
# --------------------------------------------------------------------------- #
def scene_from_mesh(m: Mesh, key: str, tag: str, matmap: dict, colmap: dict):
    d = os.path.join(SCRATCH, f"{key}_{tag}")
    paths = m.write_obj_per_group(d, key)
    parts = [Part(name=f"{key}_{g}_{tag}", obj=p, mat_key=matmap[g],
                  color=colmap.get(g, (0.7, 0.7, 0.7))) for g, p in paths.items()]
    return build_scene(parts, fc=FC), d


# --------------------------------------------------------------------------- #
#  팔(arm) 정의
# --------------------------------------------------------------------------- #
class Arm:
    """한 대조군. mesh_at(φ) 만 다르고 나머지(격자·관측량·통계·판정)는 전부 같다."""

    def __init__(self, key, label_ko, role, expect, mesh_at, matmap, colmap, extra=None):
        self.key = key
        self.label_ko = label_ko
        self.role = role                 # 'signal' | 'null' | 'positive' | 'resolution'
        self.expect = expect             # True = 변조가 나와야 정상, False = 나오면 산물
        self.mesh_at = mesh_at
        self.matmap = matmap
        self.colmap = colmap
        self.extra = extra or {}


def build_arms(keys, reduction=0.5) -> tuple[list, dict]:
    """모든 팔과, 팔을 만들며 계산한 기하 사실들을 함께 돌려준다."""
    geo = {}
    arms = []
    cols_all = None

    #  --- mini2 계열 --------------------------------------------------------- #
    spec = DRONES["mini2"]
    cols = drone_colors(spec)
    cols_all = cols
    frame = build_frame(spec)
    prop_ccw = build_propeller(spec)
    prop_cw = build_propeller(spec, mirror=True)
    full0 = articulate(frame, prop_ccw, prop_cw, spec, rotor_phase_vector(spec, 0.0))
    geo["mini2"] = dict(mesh=mesh_metrics(full0),
                        frame=mesh_metrics(frame), prop_template=mesh_metrics(prop_ccw))
    matmap_drone = {g: DRONE_GROUP_MAT[g][0] for g in full0.groups()}

    prop_R = float(spec.prop_dia_mm) / 2000.0
    #  ⭐ 요(yaw) 정합각: 기체 전체를 돌렸을 때 **최대 표면 변위**가 로터 팁의 최대 변위와
    #     같아지는 각도. 손으로 고르지 않는다.
    Vf = np.asarray(full0.v, float)
    R_max = float(np.linalg.norm(Vf[:, :2], axis=1).max())          # 회전축(z)에서 가장 먼 점
    period = 360.0 / int(spec.prop_blades)                          # 2날 → 180°
    tip_chord = 2.0 * prop_R * math.sin(math.radians(period) / 2.0)  # 팁이 φ범위에서 그리는 최대 현
    yaw_span = 2.0 * math.degrees(math.asin(min(1.0, tip_chord / (2.0 * R_max))))
    geo["mini2"]["yaw_match"] = dict(
        prop_radius_m=prop_R, r_max_from_axis_m=R_max, phase_period_deg=period,
        tip_max_chord_m=tip_chord, tip_max_chord_lambda=float(tip_chord / LAM),
        yaw_span_deg=float(yaw_span),
        note_ko=("기체 요각 Δ 를 2·R_max·sin(Δ/2) = 2·r_prop·sin(period/2) 로 풀었다 — "
                 "즉 '표면 최대변위' 를 로터 팁과 같게 맞춘 양성대조."))

    if "full" in keys:
        arms.append(Arm("full_mini2", "mini2 · 로터 위상 스텝(기준 신호)", "signal", True,
                        lambda phi, s=spec, a=frame, b=prop_ccw, c=prop_cw:
                            articulate(a, b, c, s, rotor_phase_vector(s, phi)),
                        matmap_drone, cols))

    if "norotor" in keys:
        arms.append(Arm("norotor_mini2", "mini2 · 프로펠러 제거 + 같은 로터 위상 스텝",
                        "null", False,
                        lambda phi, s=spec, a=frame:
                            articulate(a, None, None, s, rotor_phase_vector(s, phi)),
                        {g: DRONE_GROUP_MAT[g][0] for g in frame.groups()}, cols,
                        extra=dict(note_ko=("프롭이 없으니 위상이 움직일 것이 없다 → 메쉬가 "
                                            "완전히 동결된다. 완전 널이자 블레이드 기여 분리축."))))

    if "disc" in keys:
        disc, disc_info = disc_like_prop(prop_ccw, prop_R)
        geo["mini2"]["disc"] = disc_info
        arms.append(Arm("disc_mini2", "mini2 · 프로펠러→회전대칭 원판, 같은 위상 스텝",
                        "null", False,
                        lambda phi, s=spec, a=frame, d=disc:
                            articulate(a, d, d, s, rotor_phase_vector(s, phi)),
                        matmap_drone, cols, extra=disc_info))

    if "half" in keys:
        frame_h, rep_f = decimate_by_group(frame, reduction)
        prop_ccw_h, rep_p = decimate_by_group(prop_ccw, reduction)
        prop_cw_h, _ = decimate_by_group(prop_cw, reduction)
        half0 = articulate(frame_h, prop_ccw_h, prop_cw_h, spec, rotor_phase_vector(spec, 0.0))
        info = dict(target_reduction=float(reduction),
                    tris_full=int(full0.n_tris()), tris_half=int(half0.n_tris()),
                    kept_frac=float(half0.n_tris() / max(1, full0.n_tris())),
                    frame_by_group=rep_f, prop_template=rep_p,
                    mesh=mesh_metrics(half0))
        geo["mini2"]["half"] = info
        arms.append(Arm("half_mini2", "mini2 · 삼각형 절반 + 같은 로터 위상 스텝",
                        "resolution", True,
                        lambda phi, s=spec, a=frame_h, b=prop_ccw_h, c=prop_cw_h:
                            articulate(a, b, c, s, rotor_phase_vector(s, phi)),
                        matmap_drone, cols, extra=info))

    if "yaw" in keys:
        arms.append(Arm("yaw_mini2", "mini2 · **기체 전체** 회전(위상 격자를 요각에 그대로)",
                        "positive", True,
                        lambda phi, s=spec, a=frame, b=prop_ccw, c=prop_cw:
                            articulate(a, b, c, s, rotor_phase_vector(s, 0.0), body_yaw_deg=phi),
                        matmap_drone, cols))
        arms.append(Arm("yawmatch_mini2",
                        "mini2 · 기체 전체 회전(표면변위를 로터 팁과 정합)", "positive", True,
                        lambda phi, s=spec, a=frame, b=prop_ccw, c=prop_cw, k=yaw_span / period:
                            articulate(a, b, c, s, rotor_phase_vector(s, 0.0),
                                       body_yaw_deg=phi * k),
                        matmap_drone, cols, extra=geo["mini2"]["yaw_match"]))

    #  --- 구(球) 널 --------------------------------------------------------- #
    if "sphere" in keys:
        r1 = geo["mini2"]["mesh"]["r_equal_volume_m"]
        sph1, si1 = sphere_matched(r1, geo["mini2"]["mesh"]["n_tris"])
        geo["mini2"]["sphere"] = si1
        #  ⚠ 재질 선택 이유(실측, §specular_probe 참조): ITU `metal` 은 S=0(순수 정반사)이고
        #    Sionna PathSolver 는 **구에서 정반사 경로를 하나도 못 찾는다** → 금속 구는
        #    256M spp 에서도 경로 0 개라 널로 쓸 수가 없다. 강산란 널은 |Γ|=0.99 이면서
        #    S=0.30 인 `carbon` 으로 세운다(확산 채널이 살아 있어야 잴 것이 있다).
        for mat in ("plastic", "carbon"):
            arms.append(Arm(f"sphere_mini2_{mat}",
                            f"mini2 등가부피 구({mat}) · z 회전", "null", False,
                            lambda phi, m=sph1: m.rotated("z", float(phi)),
                            {"sph": mat}, {"sph": (0.7, 0.7, 0.7)},
                            extra=dict(si1, material=mat)))
        arms.append(Arm("sphere_mini2_static",
                        "mini2 등가부피 구(plastic) · **회전 없음**(파이프라인 바닥)",
                        "null", False,
                        lambda phi, m=sph1: m.rotated("z", 0.0),
                        {"sph": "plastic"}, {"sph": (0.7, 0.7, 0.7)},
                        extra=dict(si1, material="plastic",
                                   note_ko=("기하 변화 0. 매 스텝 OBJ 재작성 + 씬 재조립 + 재추적만 "
                                            "한다 → 파이프라인이 스스로 만드는 변조의 바닥."))))

        spec2 = DRONES["matrice4e"]
        full2 = pose_articulated(spec2, rotor_phase_deg=rotor_phase_vector(spec2, 0.0))
        geo["matrice4e"] = dict(mesh=mesh_metrics(full2))
        r2 = geo["matrice4e"]["mesh"]["r_equal_volume_m"]
        sph2, si2 = sphere_matched(r2, geo["matrice4e"]["mesh"]["n_tris"])
        geo["matrice4e"]["sphere"] = si2
        arms.append(Arm("sphere_matrice4e_plastic",
                        "matrice4e 등가부피 구(plastic) · z 회전", "null", False,
                        lambda phi, m=sph2: m.rotated("z", float(phi)),
                        {"sph": "plastic"}, {"sph": (0.7, 0.7, 0.7)},
                        extra=dict(si2, material="plastic")))
    return arms, geo


# --------------------------------------------------------------------------- #
#  ⭐ 정반사 탐침 — "왜 금속 구를 널로 쓰지 않았나" 를 주장이 아니라 관측으로 남긴다
# --------------------------------------------------------------------------- #
def specular_probe(radius: float, target_tris: int, spp: int, az=AZ_DEG, el=EL_DEG) -> dict:
    """구(3 재질) vs **이등분선에 법선을 맞춘 평판**(3 재질) 의 정반사/확산 경로수.

    probe 의 양성대조(0.3 m 금속평판 → 경로 1개)를 이 스크립트의 씬 조립기로 재현해
    (a) 정반사 탐색기가 살아 있음을 보이고, (b) 그럼에도 **구에서는 정반사가 0** 이며
    (c) ITU metal(S=0) 구는 확산도 없어 경로가 통째로 0 임을 기록한다.
    이 세 사실이 '강산란 널을 carbon 으로 세운' 이유다."""
    from geom import quad
    sph, si = sphere_matched(radius, target_tris)
    u = P.look_dir(az, el)
    e1, e2 = P.basis_perp(u)
    h = 0.15                                   # 0.3 m 정사각 평판 (probe 와 같은 크기)
    pts = [(-h * e1 - h * e2), (h * e1 - h * e2), (h * e1 + h * e2), (-h * e1 + h * e2)]
    plate = quad(*[tuple(map(float, p)) for p in pts], group="plate")
    rows = []
    for shape, m in (("sphere", sph), ("plate", plate)):
        for mat in ("plastic", "carbon", "metal"):
            key = f"probe_{shape}_{mat}"
            scene, d = scene_from_mesh(m, key, "P", {m.groups()[0]: mat},
                                       {m.groups()[0]: (0.7, 0.7, 0.7)})
            g2 = id_to_group(scene, key)
            place(scene, az=az, el=el)
            a = rt_echo(scene, spp, 1, diffuse=False, id2grp=g2)
            b = rt_echo(scene, spp, 1, diffuse=True, id2grp=g2)
            drop_scratch(d)
            rows.append(dict(shape=shape, material=mat, n_tris=int(m.n_tris()),
                             spec_n=int(a["n_paths"]), spec_amp_db=a["amp_db"],
                             prod_n=int(b["n_paths"]), prod_amp_db=b["amp_db"]))
    plate_ok = any(r["shape"] == "plate" and r["spec_n"] > 0 for r in rows)
    sph_spec = sum(r["spec_n"] for r in rows if r["shape"] == "sphere")
    return dict(spp=int(spp), az_deg=float(az), el_deg=float(el), sphere=si,
                plate_half_m=float(h), rows=rows,
                specular_solver_alive=bool(plate_ok),
                sphere_specular_paths_total=int(sph_spec),
                metal_sphere_empty=bool(all(r["prod_n"] == 0 for r in rows
                                            if r["shape"] == "sphere" and r["material"] == "metal")),
                note_ko=("평판에서는 정반사 경로가 나오는데 구에서는 0 이다 — 정반사 탐색기가 "
                         "죽은 것이 아니라 곡면에서 못 찾는다. ITU metal 은 S=0 이라 확산도 "
                         "없어 금속 구는 경로가 통째로 0 → 널 대조로 쓸 수 없다."))


def expected_null_range(k: int, n_mc: int = 200_000, seed: int = 12345) -> dict:
    """⭐ 판정함수 검토용 기준선 — **순수 잡음일 때** k 개 위상평균의 ptp 기대값.

    judge() 의 검정 ① 은 `ptp(위상평균) > 3·SE` 다. 그런데 독립 정규 k 개의 **범위(range)**
    기대값은 k=32 에서 이미 4 SE 를 넘는다. 즉 검정 ① 은 단독으로는 **관대**하고, 실제
    변별력은 검정 ②(ANOVA)에서 나온다. 이 숫자를 손으로 적지 않고 몬테카를로로 낸다."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((int(n_mc), int(k)))
    r = x.max(axis=1) - x.min(axis=1)
    return dict(k=int(k), n_mc=int(n_mc),
                expected_range_over_se=float(r.mean()),
                p95_range_over_se=float(np.quantile(r, 0.95)),
                judge_test1_threshold_over_se=3.0,
                test1_is_liberal=bool(r.mean() > 3.0),
                note_ko=("독립 정규 k 개의 범위 기대값 / SE. judge 의 검정① 문턱 3 보다 크면 "
                         "검정①은 순수 잡음도 통과시킨다 → 판정은 ANOVA(검정②)가 지탱한다."))


# --------------------------------------------------------------------------- #
#  self-check — 분절 재현이 원본과 같은가 (⛔ drones.py 를 못 고치니 대신 증명한다)
# --------------------------------------------------------------------------- #
def self_check(phis) -> dict:
    out = {}
    for key in ("mini2", "matrice4e"):
        spec = DRONES[key]
        fr, pc, pw = build_frame(spec), build_propeller(spec), build_propeller(spec, mirror=True)
        rows = []
        for phi in (phis[0], phis[len(phis) // 3], phis[-1]):
            ph = rotor_phase_vector(spec, phi)
            a = pose_articulated(spec, rotor_phase_deg=ph)
            b = articulate(fr, pc, pw, spec, ph)
            sa, sb = P.mesh_signature(a), P.mesh_signature(b)
            rows.append(dict(phase_deg=float(phi), sha1_reference=sa["sha1"],
                             sha1_reproduced=sb["sha1"], match=bool(sa["sha1"] == sb["sha1"]),
                             n_tris=int(sa["n_tris"])))
        out[key] = dict(rows=rows, all_match=bool(all(r["match"] for r in rows)))
    out["note_ko"] = ("articulate() 가 drones.pose_articulated 와 **꼭짓점 해시까지 동일**한지 "
                      "확인한다. 같아야 '프롭 제거·원판 교체·삼각형 절반' 이 원본과 같은 "
                      "분절 규약 위에 있다고 말할 수 있다.")
    return out


# --------------------------------------------------------------------------- #
#  한 팔 실행 — probe 와 **같은** 절차: 잡음바닥 → 위상 스텝 → 판정
# --------------------------------------------------------------------------- #
MODES = (("spec", False), ("prod", True))


def run_arm(arm: Arm, phis, seeds, spp, n_repeat, az, el, max_depth=1, verbose=True) -> dict:
    t_arm = time.time()
    R = dict(key=arm.key, label_ko=arm.label_ko, role=arm.role,
             expect_modulation=bool(arm.expect), extra=arm.extra,
             materials={k: v for k, v in arm.matmap.items()})

    #  φ=0 기준 메쉬 — 계량 + 변위 기준점
    m0 = arm.mesh_at(float(phis[0]))
    V0 = np.asarray(m0.v, float)
    R["mesh"] = mesh_metrics(m0)

    #  ── 잡음바닥: 아무것도 움직이지 않고 같은 씬을 n_repeat 번 재추적 ────────────
    scene, d0 = scene_from_mesh(m0, arm.key, "N", arm.matmap, arm.colmap)
    g2 = id_to_group(scene, arm.key)
    geo = place(scene, az=az, el=el)
    noise = {}
    for mname, diff in MODES:
        runs = [rt_echo(scene, spp, seed=s, max_depth=max_depth, diffuse=diff, id2grp=g2)
                for s in range(1, n_repeat + 1)]
        noise[mname] = dict(diffuse=bool(diff), spread=spread(runs), runs=[_thin(r) for r in runs])
    drop_scratch(d0)
    R["noise"] = dict(geometry=geo, n_repeat=int(n_repeat), spp=int(spp), by_mode=noise)
    if verbose:
        sp = noise["prod"]["spread"]
        print(f"    [{arm.key}] 잡음바닥(prod): |h|={_f(sp,'amp_db_mean','%.2f')} dB  "
              f"σ={_f(sp,'amp_db_std')} dB  ptp={_f(sp,'amp_db_ptp')} dB  "
              f"n̄={sp['n_paths_mean']:.1f}", flush=True)

    #  ── 위상 스텝: 매 스텝 메쉬 재생성 → OBJ 재작성 → 씬 재조립 → 재추적 ────────
    res = {m: [] for m, _ in MODES}
    sigs, drives = [], []
    for i, phi in enumerate(phis):
        m = arm.mesh_at(float(phi))
        sg = P.mesh_signature(m)
        sg["phase_deg"] = float(phi)
        sigs.append(sg)
        drives.append(dict(phase_deg=float(phi), **drive_metrics(V0, np.asarray(m.v, float))))
        scene, d = scene_from_mesh(m, arm.key, f"D{i:03d}", arm.matmap, arm.colmap)
        g2 = id_to_group(scene, arm.key)
        geo = place(scene, az=az, el=el)
        for mname, diff in MODES:
            runs = [rt_echo(scene, spp, seed=s, max_depth=max_depth, diffuse=diff, id2grp=g2)
                    for s in seeds]
            res[mname].append(dict(step=i, phase_deg=float(phi), spread=spread(runs),
                                   runs=[_thin(r) for r in runs]))
        drop_scratch(d)
        if verbose and (i % 8 == 0 or i == len(phis) - 1):
            s_ = res["prod"][-1]["spread"]
            print(f"      φ={phi:7.3f}°  prod n={s_['n_paths_mean']:7.1f} "
                  f"|h|={_f(s_,'amp_db_mean','%.2f')} dB   "
                  f"surf_shift={drives[-1]['surface_max_m']*1e3:7.3f} mm", flush=True)

    n_uniq = len({s["sha1"] for s in sigs})
    dv_v = [d["vertex_max_m"] for d in drives if d["vertex_max_m"] is not None]
    dv_s = [d["surface_max_m"] for d in drives]
    step_v = []
    for i in range(1, len(phis)):
        a = arm.mesh_at(float(phis[i - 1])); b = arm.mesh_at(float(phis[i]))
        Va, Vb = np.asarray(a.v, float), np.asarray(b.v, float)
        if Va.shape == Vb.shape:
            step_v.append(float(np.linalg.norm(Vb - Va, axis=1).max()))
    R["geometry_drive"] = dict(
        n_distinct_mesh_sha1=int(n_uniq), mesh_frozen=bool(n_uniq == 1),
        vertex_shift_max_m=(float(max(dv_v)) if dv_v else None),
        vertex_shift_max_lambda=(float(max(dv_v) / LAM) if dv_v else None),
        surface_shift_max_m=float(max(dv_s)),
        surface_shift_max_lambda=float(max(dv_s) / LAM),
        vertex_shift_per_step_max_m=(float(max(step_v)) if step_v else None),
        per_phase=drives, signatures=sigs,
        note_ko=("vertex = 메쉬 데이터가 움직인 거리, surface = 형상이 움직인 거리. "
                 "회전대칭체는 vertex 는 크고 surface 는 ~0 이다."))
    R["sweep"] = dict(phases_deg=[float(x) for x in phis], seeds=[int(s) for s in seeds],
                      spp=int(spp), max_depth=int(max_depth), geometry=geo,
                      by_mode={m: res[m] for m, _ in MODES})

    #  ── 판정 (probe 의 judge 를 그대로) ────────────────────────────────────── #
    V = {}
    for mname, _ in MODES:
        nf = noise[mname]["spread"]
        for ch in ("all", "prop"):
            v = judge(res[mname], nf, channel=ch)
            n = len(phis)
            if n >= 32 and n % 16 == 0:
                v16 = judge(res[mname][:: n // 16], nf, channel=ch)
                v["subsample_16step"] = {k: v16[k] for k in
                                         ("modulation_ptp_db", "modulation_above_noise",
                                          "verdict", "n_paths_behaviour") if k in v16}
            V[f"{mname}/{ch}"] = v
            if verbose:
                print(f"      [{arm.key}/{mname}/{ch}] n̄={v.get('n_paths_mean',0):.1f}  "
                      f"ptp={_f(v,'modulation_ptp_db','%.3f')} dB  σ_noise="
                      f"{_f(v,'noise_floor_std_db','%.3f')} dB  "
                      f"ptp/SE={_f(v,'ptp_over_noise_se','%.2f')}  → {v.get('verdict')}",
                      flush=True)
    R["verdict"] = V
    sig_ch = sorted([k for k, v in V.items() if v.get("modulation_above_noise")])
    pa = V.get("prod/all") or {}
    pp = V.get("prod/prop") or {}
    #  ⭐ 두 검정을 **따로** 남긴다 — 판정이 어느 검정에 실려 있는지 보이게.
    _p = (pa.get("anova") or {}).get("p_value")
    _r = pa.get("ptp_over_noise_se")
    R["headline"] = dict(
        test1_ptp_over_3se=bool(_r is not None and _r > 3.0),
        test2_anova_p_lt_1e3=bool(_p is not None and _p < 1e-3
                                  and (pa.get("modulation_ptp_db") or 0.0) > 0.0),
        key=arm.key, role=arm.role, expect_modulation=bool(arm.expect),
        mesh_frozen=R["geometry_drive"]["mesh_frozen"],
        vertex_shift_max_lambda=R["geometry_drive"]["vertex_shift_max_lambda"],
        surface_shift_max_lambda=R["geometry_drive"]["surface_shift_max_lambda"],
        n_tris=R["mesh"]["n_tris"],
        level_db=(noise["prod"]["spread"] or {}).get("amp_db_mean"),
        noise_floor_db=(noise["prod"]["spread"] or {}).get("amp_db_std"),
        noise_floor_ptp_db=(noise["prod"]["spread"] or {}).get("amp_db_ptp"),
        modulation_ptp_db=pa.get("modulation_ptp_db"),
        modulation_ptp_db_prop=pp.get("modulation_ptp_db"),
        ptp_over_noise_se=pa.get("ptp_over_noise_se"),
        anova_p=(pa.get("anova") or {}).get("p_value"),
        n_paths_behaviour=pa.get("n_paths_behaviour"),
        modulation_above_noise=bool(sig_ch),
        channels_significant=sig_ch,
        specular_channel_empty=bool(noise["spec"]["spread"]["n_paths_mean"] == 0),
        seconds=float(time.time() - t_arm))
    R["seconds"] = float(time.time() - t_arm)
    if verbose:
        h = R["headline"]
        flag = ("정상" if bool(h["modulation_above_noise"]) == bool(arm.expect) else "⚠ 불일치")
        print(f"    ⇒ [{arm.key}] 기대={'변조' if arm.expect else '무변조'} / "
              f"관측={'변조' if h['modulation_above_noise'] else '무변조'}  → {flag}  "
              f"({R['seconds']:.0f}s)", flush=True)
    return R


def _f(d, k, fmt="%.3f"):
    v = d.get(k)
    return (fmt % v) if v is not None else "n/a"


# --------------------------------------------------------------------------- #
#  교차 비교 — ⭐ 산물 바닥 vs 신호
# --------------------------------------------------------------------------- #
def compare(arms_out: dict) -> dict:
    def hl(k):
        return (arms_out.get(k) or {}).get("headline") or {}

    nulls = {k: v["headline"] for k, v in arms_out.items()
             if v["headline"]["role"] == "null"}
    sig = hl("full_mini2")
    #  ⭐ 산물 바닥 = 널 팔들의 위상변동 ptp 중 **최댓값** (all·prop 두 채널 중 큰 쪽)
    floor_rows = []
    for k, h in nulls.items():
        cand = [x for x in (h.get("modulation_ptp_db"), h.get("modulation_ptp_db_prop"))
                if x is not None]
        if cand:
            floor_rows.append(dict(arm=k, ptp_db=float(max(cand)),
                                   ptp_db_all=h.get("modulation_ptp_db"),
                                   noise_floor_db=h.get("noise_floor_db"),
                                   ptp_over_noise_se=h.get("ptp_over_noise_se"),
                                   anova_p=h.get("anova_p"),
                                   test1_ptp_over_3se=h.get("test1_ptp_over_3se"),
                                   test2_anova_p_lt_1e3=h.get("test2_anova_p_lt_1e3"),
                                   significant=bool(h["modulation_above_noise"]),
                                   mesh_frozen=bool(h["mesh_frozen"]),
                                   vertex_shift_max_lambda=h.get("vertex_shift_max_lambda"),
                                   surface_shift_max_lambda=h.get("surface_shift_max_lambda")))
    floor_rows.sort(key=lambda r: -r["ptp_db"])
    floor = floor_rows[0] if floor_rows else None

    out = dict(
        artifact_floor=floor, null_arms=floor_rows,
        nulls_that_signalled=[r["arm"] for r in floor_rows if r["significant"]],
        #  ⭐ 검정별 분해 — '널이 검정①만 통과' 라면 그건 널의 실패가 아니라 **검정①의 실패**다
        nulls_passing_test1_only=[r["arm"] for r in floor_rows
                                  if r.get("test1_ptp_over_3se")
                                  and not r.get("test2_anova_p_lt_1e3")],
        nulls_passing_test2=[r["arm"] for r in floor_rows if r.get("test2_anova_p_lt_1e3")],
        signal=dict(arm="full_mini2", ptp_db=sig.get("modulation_ptp_db"),
                    ptp_db_prop=sig.get("modulation_ptp_db_prop"),
                    noise_floor_db=sig.get("noise_floor_db"),
                    significant=sig.get("modulation_above_noise")))
    if floor and sig.get("modulation_ptp_db") is not None:
        out["signal_over_artifact_floor_db"] = float(sig["modulation_ptp_db"] - floor["ptp_db"])
        out["signal_over_artifact_floor_ratio"] = float(
            sig["modulation_ptp_db"] / max(floor["ptp_db"], 1e-12))

    #  ③ 블레이드 기여 분리 — 프롭 있는 드론 vs 프롭 없는 드론
    a, b = hl("full_mini2"), hl("norotor_mini2")
    if a and b:
        out["blade_isolation"] = dict(
            full_level_db=a.get("level_db"), norotor_level_db=b.get("level_db"),
            level_delta_db=(None if (a.get("level_db") is None or b.get("level_db") is None)
                            else float(a["level_db"] - b["level_db"])),
            full_modulation_ptp_db=a.get("modulation_ptp_db"),
            norotor_modulation_ptp_db=b.get("modulation_ptp_db"),
            norotor_mesh_frozen=b.get("mesh_frozen"),
            norotor_significant=b.get("modulation_above_noise"),
            note_ko=("프롭을 빼면 위상이 움직일 것이 없다 → 프롭 없는 팔의 변조는 정의상 "
                     "파이프라인 산물이다. 두 팔의 |h| 차이가 블레이드가 채널에 더한 양이다."))

    #  ④ 메쉬 해상도 의존
    a, b = hl("full_mini2"), hl("half_mini2")
    if a and b:
        out["mesh_resolution"] = dict(
            tris_full=a.get("n_tris"), tris_half=b.get("n_tris"),
            level_full_db=a.get("level_db"), level_half_db=b.get("level_db"),
            level_delta_db=(None if (a.get("level_db") is None or b.get("level_db") is None)
                            else float(b["level_db"] - a["level_db"])),
            modulation_full_db=a.get("modulation_ptp_db"),
            modulation_half_db=b.get("modulation_ptp_db"),
            modulation_delta_db=(None if (a.get("modulation_ptp_db") is None
                                          or b.get("modulation_ptp_db") is None)
                                 else float(b["modulation_ptp_db"] - a["modulation_ptp_db"])),
            noise_full_db=a.get("noise_floor_db"), noise_half_db=b.get("noise_floor_db"),
            both_significant=bool(a.get("modulation_above_noise")
                                  and b.get("modulation_above_noise")))

    #  ② 양성대조가 실제로 켜졌나
    out["positive_controls"] = {k: dict(ptp_db=hl(k).get("modulation_ptp_db"),
                                        significant=hl(k).get("modulation_above_noise"),
                                        surface_shift_max_lambda=hl(k).get(
                                            "surface_shift_max_lambda"))
                                for k in ("yaw_mini2", "yawmatch_mini2") if hl(k)}
    return out


def reproducibility(J: dict, prev_path: str) -> dict:
    """⭐ **프로세스를 새로 띄워도 같은 숫자가 나오나** — 이전 실행본과 팔별 headline 을 대조한다.

    시드는 고정이지만 GPU 는 다른 작업과 공유되고 커널 스케줄도 매번 다르다. 재현되지 않으면
    '널이 조용했다' 는 관측 자체가 우연일 수 있다. 손으로 옮겨 적지 않고 여기서 계산한다."""
    if not os.path.exists(prev_path):
        return dict(available=False, path=prev_path)
    with open(prev_path) as f:
        prev = json.load(f)
    keys = ("level_db", "noise_floor_db", "modulation_ptp_db", "modulation_ptp_db_prop",
            "ptp_over_noise_se", "surface_shift_max_lambda", "vertex_shift_max_lambda")
    rows, worst = {}, dict(delta=0.0, arm=None, field=None)
    for grp in ("arms", "arms_hot"):
        for k, v in (J.get(grp) or {}).items():
            p = ((prev.get(grp) or {}).get(k) or {}).get("headline")
            if not p:
                continue
            h = v["headline"]
            d = {}
            for kk in keys:
                a, b = h.get(kk), p.get(kk)
                if a is None or b is None:
                    continue
                d[kk] = float(abs(a - b))
                if d[kk] > worst["delta"]:
                    worst = dict(delta=d[kk], arm=f"{grp}/{k}", field=kk)
            same_v = (h.get("modulation_above_noise") == p.get("modulation_above_noise"))
            rows[f"{grp}/{k}"] = dict(max_abs_delta=(max(d.values()) if d else None),
                                      verdict_identical=bool(same_v))
    return dict(available=True, path=prev_path, n_arms_compared=len(rows),
                max_abs_delta_any=float(worst["delta"]), worst=worst,
                all_verdicts_identical=bool(all(r["verdict_identical"] for r in rows.values())),
                bitwise_identical=bool(worst["delta"] == 0.0), by_arm=rows,
                note_ko=("새 프로세스·다른 GPU 점유 상황에서 다시 돌린 결과와의 차이. "
                         "0 이면 이 실험의 모든 숫자가 프로세스 간 결정적이다."))


def overall_verdict(cmp_: dict, arms_out: dict) -> dict:
    """⭐ 이 실험이 판정을 통과시키는가 — 조건을 코드에 박아 둔다(사후 해석 금지)."""
    floor = cmp_.get("artifact_floor") or {}
    sig = cmp_.get("signal") or {}
    nulls_bad = cmp_.get("nulls_that_signalled") or []
    pos = cmp_.get("positive_controls") or {}
    pos_ok = bool(pos) and all(v.get("significant") for v in pos.values())
    sig_ok = bool(sig.get("significant"))
    margin = cmp_.get("signal_over_artifact_floor_db")
    return dict(
        positive_controls_fired=pos_ok,
        signal_significant=sig_ok,
        nulls_clean=bool(not nulls_bad),
        nulls_that_signalled=nulls_bad,
        artifact_floor_db=floor.get("ptp_db"), artifact_floor_arm=floor.get("arm"),
        signal_ptp_db=sig.get("ptp_db"), margin_db=margin,
        gate_pass=bool(pos_ok and sig_ok and not nulls_bad),
        note_ko=("gate_pass = (양성대조 전부 켜짐) ∧ (기준 신호 유의) ∧ (널 전부 조용함). "
                 "하나라도 어긋나면 probe 의 §D 판정을 그대로 인용하면 안 된다."))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=32)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--repeat", type=int, default=32)
    ap.add_argument("--spp", type=int, default=256_000_000)
    ap.add_argument("--reduction", type=float, default=0.5)
    ap.add_argument("--arms", default="full,norotor,disc,half,yaw,sphere")
    ap.add_argument("--hot", default="full_mini2,norotor_mini2,disc_mini2,sphere_mini2_carbon",
                    help="정반사가 살아 있는 자세에서 다시 돌릴 팔 (빈 문자열이면 생략)")
    ap.add_argument("--compare-to", default="",
                    help="이전 실행본 JSON 경로 — 프로세스 간 재현성을 계산해 담는다")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()

    if a.quick:
        a.steps, a.seeds, a.repeat, a.spp = 4, 2, 4, 4_000_000
        a.hot = ""

    os.makedirs(SCRATCH, exist_ok=True)
    period = 360.0 / int(DRONES["mini2"].prop_blades)          # 2날 → 180°
    phis = list(np.linspace(0.0, period, int(a.steps), endpoint=False))
    seeds = tuple(range(1, a.seeds + 1))

    #  probe 에서 hot 자세(정반사가 존재하는 유일한 자세)를 읽어 온다 — 손입력 금지
    probe = {}
    hot_aspect = None
    if os.path.exists(PROBE_JSON):
        with open(PROBE_JSON) as f:
            probe = json.load(f)
        hot_aspect = ((probe.get("airframes", {}).get("mini2", {})
                       .get("S_aspect") or {}).get("hot_aspect"))

    t0 = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_null_control.py",
        question=("변조가 나오면 안 되는 물체에서도 변조가 나오는가 — "
                  "① 등가부피 구 회전 ② 기체 전체 회전(양성) ③ 로터 제거 ④ 삼각형 절반"),
        observable=("h = Σ_p a_p·exp(−j2πf_c·τ_p)  (report15_probe.rt_echo 를 그대로 import)"),
        measurement_code="report15_probe.{rt_echo, spread, judge, place, id_to_group}",
        fc_hz=FC, lambda_m=LAM, az_deg=AZ_DEG, el_deg=EL_DEG, range_m=RANGE_M,
        baseline_m=BASELINE_M, max_paths=MAX_PATHS, max_depth=1,
        n_phase_steps=int(a.steps), phase_period_deg=float(period),
        phases_deg=[float(x) for x in phis],
        sweep_seeds=int(a.seeds), n_repeat_noise=int(a.repeat), spp=int(a.spp),
        decimation_target_reduction=float(a.reduction),
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        materials="production per-group (DRONE_GROUP_MAT); 구는 단일재질",
        related=dict(probe="outputs/report15_probe.json",
                     facet="outputs/facet_count.json"),
        #  ⭐ 널이 하나로는 부족한 이유 — 세 널이 **서로 다른 고장모드**를 막는다.
        null_design=dict(
            norotor_mini2=("메쉬가 문자 그대로 동결된다(프롭이 없어 위상이 움직일 것이 없다). "
                           "재실행 결정성만 잰다 — 0 이 아니면 그 뒤 모든 숫자가 무의미하다."),
            disc_mini2=("꼭짓점은 블레이드 팁과 같은 크기로 움직이는데 면은 같은 평면에 남는다 "
                        "(삼각형만 재분할). '메쉬 장부가 바뀌는 것만으로 변조가 생기나' 를 막는다."),
            sphere_mini2=("형상은 불변인데 **모든 면의 법선 방위가 회전한다**. "
                          "'대칭체라도 면 방향이 바뀌면 변조가 생기나' 를 막는다."),
            why_all_three=("원판은 면 방향이 안 바뀌고, 구는 표면 변위가 작다. "
                           "각각 반론이 하나씩 있어 셋을 겹쳐야 빈틈이 없다.")),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), arms={})

    def _save():
        with open(OUT_JSON, "w") as f:
            json.dump(J, f, ensure_ascii=False, indent=1)

    print(f"\n══ 널 대조 — 위상 {a.steps} 스텝 × 시드 {a.seeds} × spp {a.spp:,} "
          f"@ az={AZ_DEG}° el={EL_DEG}° R={RANGE_M} m ══", flush=True)

    print("  self-check: 분절 재현 == drones.pose_articulated ?", flush=True)
    J["self_check"] = self_check(phis)
    for k, v in J["self_check"].items():
        if isinstance(v, dict):
            print(f"    {k}: all_match={v['all_match']}", flush=True)

    arm_keys = {x.strip() for x in a.arms.split(",") if x.strip()}
    arms, geo = build_arms(arm_keys, reduction=a.reduction)
    J["geometry"] = geo
    J["judge_null_reference"] = expected_null_range(int(a.steps))
    r_ = J["judge_null_reference"]
    print(f"  판정함수 기준선: 순수잡음 {a.steps} 위상의 ptp 기대값 = "
          f"{r_['expected_range_over_se']:.2f}·SE  (검정① 문턱 3·SE "
          f"→ {'관대' if r_['test1_is_liberal'] else '보수적'})", flush=True)
    if "sphere" in arm_keys:
        print("  정반사 탐침 (구 vs 평판, 3 재질) …", flush=True)
        J["specular_probe"] = specular_probe(geo["mini2"]["mesh"]["r_equal_volume_m"],
                                             geo["mini2"]["mesh"]["n_tris"], a.spp)
        sp_ = J["specular_probe"]
        for r in sp_["rows"]:
            print(f"    {r['shape']:7s}/{r['material']:8s}  spec n={r['spec_n']:5d}  "
                  f"prod n={r['prod_n']:6d}  |h|_prod="
                  f"{('%.2f' % r['prod_amp_db']) if r['prod_amp_db'] is not None else 'n/a':>9} dB",
                  flush=True)
        print(f"    → 정반사 탐색기 살아있음={sp_['specular_solver_alive']}  "
              f"구의 정반사 경로 총합={sp_['sphere_specular_paths_total']}  "
              f"금속 구 경로 0={sp_['metal_sphere_empty']}", flush=True)
    _save()
    print(f"  팔 {len(arms)}개: " + ", ".join(x.key for x in arms), flush=True)

    for arm in arms:
        print(f"\n── {arm.key} — {arm.label_ko} "
              f"[{'변조 나와야 정상' if arm.expect else '변조 나오면 산물'}]", flush=True)
        J["arms"][arm.key] = run_arm(arm, phis, seeds, a.spp, a.repeat, AZ_DEG, EL_DEG)
        _save()

    #  ⭐ 정반사가 살아 있는 자세에서 한 번 더 — 그 자세에서만 spec 채널이 비어 있지 않다
    hot_keys = [x.strip() for x in a.hot.split(",") if x.strip()]
    if hot_keys and hot_aspect:
        az_h, el_h = float(hot_aspect["az_deg"]), float(hot_aspect["el_deg"])
        J["meta"]["hot_aspect"] = dict(az_deg=az_h, el_deg=el_h,
                                       source="report15_probe.mini2.S_aspect.hot_aspect")
        J["arms_hot"] = {}
        by_key = {x.key: x for x in arms}
        for k in hot_keys:
            if k not in by_key:
                continue
            print(f"\n── [hot az={az_h}° el={el_h}°] {k}", flush=True)
            J["arms_hot"][k] = run_arm(by_key[k], phis, seeds, a.spp, a.repeat, az_h, el_h)
            _save()

    J["comparison"] = compare(J["arms"])
    J["verdict"] = overall_verdict(J["comparison"], J["arms"])
    if J.get("arms_hot"):
        J["comparison_hot"] = compare(J["arms_hot"])
    #  probe 의 해당 숫자를 **읽어서** 나란히 둔다 (손입력 금지)
    if probe:
        J["probe_reference"] = {k: v.get("headline")
                                for k, v in probe.get("airframes", {}).items()}
        J["probe_reference"]["blockers_source"] = "outputs/report15_probe.json"
    if a.compare_to:
        J["reproducibility"] = reproducibility(J, a.compare_to)
        r = J["reproducibility"]
        if r.get("available"):
            print(f"  재현성: 팔 {r['n_arms_compared']}개 대조, 최대 |Δ| = "
                  f"{r['max_abs_delta_any']:.3e}  판정 전부 동일 = "
                  f"{r['all_verdicts_identical']}", flush=True)
    J["meta"]["seconds_total"] = float(time.time() - t0)
    _save()

    v = J["verdict"]
    print("\n" + "═" * 78)
    print(f"  양성대조 켜짐 = {v['positive_controls_fired']}   기준신호 유의 = "
          f"{v['signal_significant']}   널 전부 조용 = {v['nulls_clean']}")
    print(f"  산물 바닥 = {_f(v,'artifact_floor_db','%.3f')} dB ({v.get('artifact_floor_arm')})"
          f"   기준신호 = {_f(v,'signal_ptp_db','%.3f')} dB"
          f"   여유 = {_f(v,'margin_db','%.3f')} dB")
    print(f"  ⇒ gate_pass = {v['gate_pass']}")
    if v.get("nulls_that_signalled"):
        print(f"  ⚠ 변조를 낸 널: {v['nulls_that_signalled']}")
    print(f"\n✅ 저장 → {OUT_JSON}   ({J['meta']['seconds_total']:.0f}s)")
    return J


if __name__ == "__main__":
    main()
