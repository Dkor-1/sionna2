# -*- coding: utf-8 -*-
"""
mesh_compare.py — **우리 파라메트릭 메쉬 vs 실물 CAD**: 근사가 σ 에 몇 dB 오차를 만드는가
=============================================================================================
질문: *"스펙시트 숫자로 코드가 만든 메쉬가, 실물 3D 모델과 얼마나 다른가?"*
      *"그 차이가 RCS 에 몇 dB 로 나타나는가?"*

왜 이 실험이 필요한가
  우리 드론 메쉬는 **다운로드한 게 아니라 코드가 스펙에서 생성**한 것이다.
  실루엣은 **사진을 보고 한 우리의 해석**이지 3D 스캔이 아니다. 그 근사가 얼마나 손해인지
  숫자로 말할 수 있어야 한다.

왜 DJI 로 못 하나 (정직하게)
  **DJI 는 공식 CAD 를 공개하지 않는다.** 인터넷의 DJI 3D 모델은 시각용(껍데기만, 내부 금속
  산란체 없음)이고 치수 검증도 안 되고 라이선스도 제약이 있다 → RCS 에 쓸 수 없다.
  → 대신 **CAD 가 공개된 실물 드론**(Yuneec Typhoon H480, 3DR Solo, Holybro 1345 프롭)으로
    **우리 방법 자체**를 검증한다. assets/meshes/reference/SOURCES.md 참조.

공정한 비교를 위한 규칙 (중요)
  실물 CAD 는 **껍데기뿐**이다 — 배터리·PCB·모터 같은 **내부 금속이 없다**.
  그래서 σ 를 그냥 비교하면 사과-오렌지다.
  → **양쪽을 동일 재질(전부 PEC)로 두고** 껍데기 형상만 비교한다.
    그러면 남는 차이는 **순수하게 기하(실루엣) 차이**다. 그게 우리가 알고 싶은 것이다.

무엇을 재나
  1. 외형(바운딩박스) 차이
  2. **투영면적 vs 방위각** — RCS 는 투영면적이 지배한다(평판극한 σ ∝ A²)
  3. **SBR σ vs 방위각** — 같은 PEC, 같은 격자, 같은 엔진(Mitsuba 광선 + PO 적분)
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from gpu import pick as _pick_gpu     # noqa: E402  (mitsuba import 전에)
_pick_gpu(verbose=False)

import numpy as np                    # noqa: E402
import trimesh                        # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
REF = os.path.join(ROOT, "assets", "meshes", "reference")
C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  실물 CAD 로더 — 단위·정렬을 맞춘다
# --------------------------------------------------------------------------- #
#  ⚠ **파일마다 단위가 다르다.** 이걸 틀리면 프롭이 0.3 mm 가 된다(실제로 그랬다).
#     · rotors_simulator 의 Typhoon STL : **mm** 단위 (SDF 가 <scale>0.001</scale> 로 m 변환)
#     · rotors_simulator 의 3DR Solo STL : **m** 단위 (SDF scale 1)
#     · PX4-gazebo-models 의 x500 메쉬   : **m** 단위
UNIT_SCALE = {
    "main_body_remeshed_v3.stl": 1e-3,
    "leg1_remeshed_v3.stl": 1e-3,
    "leg2_remeshed_v3.stl": 1e-3,
    "prop_cw_assembly_remeshed_v3.stl": 1e-3,
    "prop_ccw_assembly_remeshed_v3.stl": 1e-3,
    "prop_guard_jybhz.stl": 1e-3,
    "cgo3_camera_remeshed_v1.stl": 1e-3,
    "cgo3_mount_remeshed_v1.stl": 1e-3,
    "cgo3_vertical_arm_remeshed_v1.stl": 1e-3,
    "cgo3_horizontal_arm_remeshed_v1.stl": 1e-3,
    "solo.stl": 1.0,
    "solo_prop_cw.stl": 1.0,
    "solo_prop_ccw.stl": 1.0,
    "1345_prop_cw.stl": 1.0,
    "5010Bell.dae": 1.0,
    "NXP-HGD-CF.dae": 1.0,
}


def load_reference(name: str, unit_scale: float | None = None) -> trimesh.Trimesh:
    """참조 CAD 를 읽어 **미터 단위 · 원점 중심**으로 맞춘다.
    unit_scale=None 이면 UNIT_SCALE 표를 쓴다 (파일마다 다르다 — 위 주석 참조)."""
    p = os.path.join(REF, name)
    s = UNIT_SCALE.get(name, 1.0) if unit_scale is None else float(unit_scale)
    m = trimesh.load(p, force="mesh")
    m.apply_scale(s)
    m.apply_translation(-m.bounds.mean(axis=0))          # 원점 중심
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    trimesh.repair.fix_normals(m)
    return m


def typhoon_h480_real() -> trimesh.Trimesh:
    """**Yuneec Typhoon H480 실물 CAD** 조립 — 동체 + 다리 2 + 프롭 6 (Apache-2.0).
    Gazebo SDF 의 배치를 따른다(로터 6개, 반경 ~0.26 m)."""
    body = load_reference("main_body_remeshed_v3.stl")
    parts = [body]
    # 다리 2개 (SDF 배치 근사 — 동체 아래 좌우)
    for nm, sy in (("leg1_remeshed_v3.stl", +1), ("leg2_remeshed_v3.stl", -1)):
        L = load_reference(nm)
        L.apply_translation([0.0, sy * 0.10, -0.10])
        parts.append(L)
    # 프롭 6개 — 헥사 배치(60° 간격), 로터 반경은 동체 크기에서 유도
    R = 0.26
    prop = load_reference("prop_cw_assembly_remeshed_v3.stl")
    for k in range(6):
        a = np.radians(30 + 60 * k)
        P = prop.copy()
        P.apply_transform(trimesh.transformations.rotation_matrix(a, [0, 0, 1]))
        P.apply_translation([R * np.cos(a), R * np.sin(a), 0.045])
        parts.append(P)
    m = trimesh.util.concatenate(parts)
    m.apply_translation(-m.bounds.mean(axis=0))
    return m


# --------------------------------------------------------------------------- #
#  1. 투영면적 vs 방위각 — RCS 의 1차 결정요인
# --------------------------------------------------------------------------- #
def projected_area(m: trimesh.Trimesh, az_deg, el_deg=15.0, grid=1.5e-3):
    """시선 방향에서 본 **투영면적** [m²]. 광선 격자로 실루엣을 래스터화해 센다
    (볼록/오목·가림 무관하게 정확하다)."""
    from rcs_sbr import _look
    import mitsuba as mi
    V = np.asarray(m.vertices, np.float32)
    F = np.asarray(m.faces, np.uint32)
    mm = mi.Mesh("ref", vertex_count=len(V), face_count=len(F),
                 has_vertex_normals=False, has_vertex_texcoords=False)
    p = mi.traverse(mm)
    p["vertex_positions"] = mi.Float(V.ravel())
    p["faces"] = mi.UInt32(F.ravel())
    p.update()
    scene = mi.load_dict({"type": "scene", "s": mm})

    ctr = 0.5 * (V.max(0) + V.min(0))
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * 1.2 + 5 * grid
    n = int(np.ceil(2 * Rout / grid))
    t = (np.arange(n) - (n - 1) / 2.0) * grid
    A, B = np.meshgrid(t, t, indexing="ij")

    out = []
    for az in np.atleast_1d(np.asarray(az_deg, float)):
        u = _look(az, el_deg)
        tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
        e2 = np.cross(u, e1)
        O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
        D = np.tile(-u, (O.shape[0], 1))
        ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                       d=mi.Vector3f(*D.T.astype(np.float32)))
        si = scene.ray_intersect(ray)
        hit = int(np.asarray(si.is_valid()).astype(bool).sum())
        out.append(hit * grid * grid)
    return np.array(out) if np.ndim(az_deg) else float(out[0])


# --------------------------------------------------------------------------- #
#  2. SBR σ — 동일 PEC, 동일 격자
# --------------------------------------------------------------------------- #
def sigma_pec(m: trimesh.Trimesh, fc, az_deg, el_deg=15.0, div=12, key=None):
    """**전부 PEC** 로 두고 SBR σ [m²]. 형상만 비교하기 위한 규약."""
    from rcs_sbr import rcs_sbr_batch, DEFAULT_DIV
    from geom import Mesh
    g = Mesh()
    V = np.asarray(m.vertices, float); F = np.asarray(m.faces, int)
    g.v = [tuple(map(float, p)) for p in V]
    g.f = [tuple(map(int, f)) for f in F]
    g.g = ["metal"] * len(F)
    lam = C0 / fc
    return rcs_sbr_batch(g, {"metal": "metal"}, fc, az_deg=az_deg, el_deg=el_deg,
                         spacing=lam / div, cache_key=key)


def compare(real: trimesh.Trimesh, ours: trimesh.Trimesh, fc=3.5e9, el=15.0,
            n_az=72, name_real="real CAD", name_ours="ours (parametric)"):
    """실물 CAD vs 우리 메쉬 — 외형·투영면적·σ 를 **같은 조건**으로 비교."""
    az = np.linspace(0, 360, n_az, endpoint=False)

    def bb(x):
        return (x.bounds[1] - x.bounds[0]) * 1000

    Ar = projected_area(real, az, el)
    Ao = projected_area(ours, az, el)
    Sr = np.atleast_1d(sigma_pec(real, fc, az, el, key=("real", name_real)))
    So = np.atleast_1d(sigma_pec(ours, fc, az, el, key=("ours", name_ours)))

    d_area = 10 * np.log10(np.mean(Ao) / np.mean(Ar))
    d_sig = 10 * np.log10(np.mean(So) / np.mean(Sr))
    return dict(
        az=az.tolist(), el=el, fc=fc,
        name_real=name_real, name_ours=name_ours,
        bbox_real_mm=bb(real).tolist(), bbox_ours_mm=bb(ours).tolist(),
        n_faces_real=int(len(real.faces)), n_faces_ours=int(len(ours.faces)),
        area_real=Ar.tolist(), area_ours=Ao.tolist(),
        sigma_real=Sr.tolist(), sigma_ours=So.tolist(),
        area_mean_real=float(np.mean(Ar)), area_mean_ours=float(np.mean(Ao)),
        sigma_mean_real_dbsm=float(10 * np.log10(np.mean(Sr))),
        sigma_mean_ours_dbsm=float(10 * np.log10(np.mean(So))),
        d_area_db=float(d_area),                    # 투영면적 차이 [dB]
        d_sigma_db=float(d_sig),                    # **σ 차이 [dB]** ← 핵심 수치
        # 방위각별 σ 차이의 산포 (평균만 맞고 패턴이 다를 수도 있다)
        d_sigma_rms_db=float(np.sqrt(np.mean((10 * np.log10(So / Sr)) ** 2))),
    )
