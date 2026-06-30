# -*- coding: utf-8 -*-
"""
rcs_po.py — (report2) 물리광학(Physical Optics)으로 드론 RCS 계산
==================================================================

왜 광선추적(Sionna RT) 대신 PO 인가?
  Sionna RT 의 확산반사로 '작은 드론'의 후방산란을 뽑으면 표본잡음이 크고
  글린트(번쩍임)에 좌우돼 **절대 RCS 가 불안정**합니다(예전 작업도 같은 이유로
  RT 의 RCS 를 신뢰하지 않았음). 그래서 CAD 표적 RCS 의 표준 기법인
  **물리광학(PO)** 으로, 우리가 report1 에서 만든 '정확한 메쉬'로부터 직접 계산합니다.

PO 핵심 (모노스태틱 후방산란)
  표적 표면을 점들로 잘게 나누고, 레이더를 향한(조명된) 면만 골라
  위상을 맞춰 더합니다:
      E(û) = Σ (n̂·û>0) (n̂·û) ΔA · exp(j·2k·(r·û))
      σ    = (4π/λ²) · |E|²
  û = 표적→레이더 방향, k=2π/λ, r=표면점 위치, n̂=면 법선.

검증 (이 모듈이 맞다는 근거)
  * 평판(넓이 A): 수직입사 σ = 4π A²/λ² (이론) — 일치 확인
  * 큰 구(반지름 r≫λ): σ = πr² (기하광학) — 일치 확인
  검증이 맞으면, 같은 코드로 드론 RCS(θ, 주파수)를 신뢰성 있게 뽑을 수 있습니다.
"""
from __future__ import annotations

import numpy as np

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  메쉬 → 표면 점구름(point cloud): 위치 r, 법선 n̂, 면적요소 ΔA
# --------------------------------------------------------------------------- #
def mesh_to_points(mesh, spacing):
    """삼각형들을 spacing[m] 간격 점으로 잘게 나눠 (P, N, dA) 를 돌려준다."""
    V = np.array(mesh.v)
    Ps, Ns, dAs = [], [], []
    for (ia, ib, ic) in mesh.f:
        v0, v1, v2 = V[ia], V[ib], V[ic]
        e1, e2 = v1 - v0, v2 - v0
        nrm = np.cross(e1, e2)
        area = 0.5 * np.linalg.norm(nrm)
        if area < 1e-12:
            continue
        nhat = nrm / (2 * area)
        emax = max(np.linalg.norm(e1), np.linalg.norm(e2), np.linalg.norm(v2 - v1))
        N = max(1, int(np.ceil(emax / spacing)))
        # 바리센트릭 격자 (u,v)=(i+.5)/N, 삼각형 내부(u+v<=1)만
        ij = [(i, j) for i in range(N) for j in range(N) if (i + 0.5) + (j + 0.5) <= N]
        if not ij:
            ij = [(0, 0)]
        uv = (np.array(ij) + 0.5) / N
        pts = v0 + uv[:, :1] * e1 + uv[:, 1:] * e2
        Ps.append(pts)
        Ns.append(np.tile(nhat, (len(pts), 1)))
        dAs.append(np.full(len(pts), area / len(pts)))
    return np.vstack(Ps), np.vstack(Ns), np.concatenate(dAs)


def _look_dirs(az_deg, el_deg=0.0):
    """방위각/고각[deg] → 표적→레이더 단위벡터 û (…,3)."""
    az = np.radians(np.atleast_1d(az_deg)); el = np.radians(el_deg)
    return np.stack([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az),
                     np.full_like(az, np.sin(el))], axis=-1)


def rcs_from_points(P, N, dA, fc, az_deg, el_deg=0.0):
    """점구름에서 PO 모노스태틱 RCS σ(az)[m²] 를 계산(벡터화)."""
    lam = C0 / fc; k = 2 * np.pi / lam
    U = _look_dirs(az_deg, el_deg)                 # (A,3)
    PU = P @ U.T                                   # (Np,A) 위상거리
    NU = N @ U.T                                   # (Np,A) 면법선·시선
    illum = NU > 0
    integrand = np.where(illum, NU, 0.0) * dA[:, None] * np.exp(1j * 2 * k * PU)
    E = integrand.sum(axis=0)                      # (A,)
    return (4 * np.pi / lam**2) * np.abs(E)**2     # (A,) σ [m²]


# --------------------------------------------------------------------------- #
#  드론 RCS (메쉬에서 바로)
# --------------------------------------------------------------------------- #
def drone_rcs_pattern(drone_key, fc, az_deg, el_deg=0.0, spacing=None):
    """드론 1종의 RCS(az)[m²]. spacing 기본 = λ/7 (정확도/속도 균형)."""
    from drones import DRONES, build_drone
    lam = C0 / fc
    spacing = spacing or lam / 7.0
    mesh = build_drone(DRONES[drone_key])
    P, N, dA = mesh_to_points(mesh, spacing)
    return rcs_from_points(P, N, dA, fc, az_deg, el_deg), len(dA)


def dbsm(sigma):
    """m² → dBsm."""
    return 10 * np.log10(np.maximum(sigma, 1e-30))


# --------------------------------------------------------------------------- #
#  검증용 표준 표적 (구 / 평판)
# --------------------------------------------------------------------------- #
def _sphere_mesh(r, seg=60, rings=30):
    from geom import uv_sphere
    return uv_sphere(r, seg=seg, rings=rings)


def _plate_mesh(a):
    """xy 평면(법선 +z) 한 변 a 정사각 평판."""
    from geom import Mesh
    m = Mesh("plate"); h = a/2
    i = [m.add_vertex(*p) for p in [(-h,-h,0),(h,-h,0),(h,h,0),(-h,h,0)]]
    m.add_quad(*i)
    return m


def validate(fc=3.5e9):
    lam = C0/fc
    print(f"== PO 검증 @ {fc/1e9:.1f} GHz (λ={lam*100:.1f} cm) ==")
    # 평판: 수직입사 이론 4πA²/λ²  (법선 +z → 시선 el=90°)
    a = 0.30; A = a*a
    mp = _plate_mesh(a); P,N,dA = mesh_to_points(mp, lam/10)
    s = rcs_from_points(P,N,dA, fc, az_deg=[0.0], el_deg=90.0)[0]
    th = 4*np.pi*A**2/lam**2
    print(f"  평판 {a}m: PO={dbsm(s):6.2f} dBsm  이론={dbsm(th):6.2f} dBsm  Δ={dbsm(s)-dbsm(th):+.2f}")
    # 구: 큰 구 σ=πr²  (정점 많이)
    for r in (0.30, 0.50):
        ms = _sphere_mesh(r, seg=90, rings=46); P,N,dA = mesh_to_points(ms, lam/8)
        s = rcs_from_points(P,N,dA, fc, az_deg=[0.0], el_deg=0.0)[0]
        th = np.pi*r*r
        print(f"  구 r={r}m ({r/lam:.1f}λ): PO={dbsm(s):6.2f} dBsm  이론(πr²)={dbsm(th):6.2f} dBsm  Δ={dbsm(s)-dbsm(th):+.2f}")


if __name__ == "__main__":
    validate(3.5e9)
    print()
    from drones import DRONES
    fc = 3.5e9
    az = np.arange(0, 360, 2.0)
    print(f"== 드론별 RCS @ {fc/1e9:.1f} GHz (방위 평균 / 최대) ==")
    for k in DRONES:
        sig, npts = drone_rcs_pattern(k, fc, az)
        print(f"  {k:10s} 점{npts:6d}  평균={dbsm(sig.mean()):6.2f} dBsm  "
              f"최대={dbsm(sig.max()):6.2f} dBsm  최소={dbsm(sig.min()):7.2f} dBsm")
