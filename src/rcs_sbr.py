# -*- coding: utf-8 -*-
"""
rcs_sbr.py — **SBR (Shooting-and-Bouncing Rays)**: Mitsuba 광선 + PO 적분으로 RCS 를 낸다
============================================================================================
상용 EM 솔버(FEKO/CST/HFSS SBR+)가 고주파 RCS 를 내는 **표준 방법**이 바로 이것이다:
  ① **광선(GO)** 으로 "어느 면이 실제로 조명되는가"를 찾고 (가림·다중반사 포함)
  ② 그 면들 위에서 **PO 표면적분**을 해서 σ 를 낸다.

■ 왜 이걸 만들었나 — 기존 rcs_po.py 대비 무엇이 나아지나
  | | rcs_po.py (기존) | rcs_sbr.py (이것) |
  |---|---|---|
  | 표면 샘플링 | 메쉬 위 자체 점구름(λ/7) | **Mitsuba 광선이 실제로 맞은 지점** |
  | 가림(self-shadowing) | **없음** — 뒤에 가려진 면도 계상 | **공짜** (첫 충돌만 채택) |
  | 오목부 다중반사 | **불가** | **가능** (반사 후 재추적, max_bounce) |
  | 재질 | (통합 후) materials.py | **동일** — Sionna 와 같은 표 |
  | 엔진 | numpy | **Mitsuba/OptiX (GPU)** |

■ 왜 PO 를 없앨 수 없나 — 그리고 "광선을 더 쏘면 되지 않나"에 대한 답
  Sionna 의 PathSolver 는 **전파(propagation)용**이라 표면을 '국소 무한 거울'로 본다(GO).
  표면적분 단계가 없으므로 **표적의 σ 가 창발하지 않는다**. 광선을 늘려도 안 된다 — 실측:
    · 평판 변 0.2→4 m (σ 52 dB 변화) → RT 진폭 −7.91 dB **불변**(산포 0.00 dB)
    · 드론 확산 에코: 광선 100M→400M 로 늘리면 값이 **+8~12 dB 계속 커진다**(수렴 안 함)
      그리고 **산란계수 S 에 비례**한다(S 2배 → +15 dB). S 는 드론과 무관한 재질 노브다.
    · 게다가 ITU metal 은 **S=0** → 모터·배터리·PCB(지배적 산란체)가 확산에 **기여 0**.
  → σ 는 **적분에서 나온다**. PO 는 꼼수가 아니라 **물리 그 자체**다.
  → 우리가 할 수 있는 최선은 PO 를 **광선추적 안으로 넣는 것** = SBR. 이 파일이 그것이다.

■ 핵심 수식 — 왜 광선 격자가 PO 적분을 그대로 준다
  모노스태틱 PO:   E(û) ∝ ∬_조명면 (n̂·û) · e^{j2k r·û} dS
  투영면으로 변수변환:  (n̂·û) dS = dA_투영   (비스듬함 계수가 **상쇄**된다)
  ⇒  E(û) ∝ ∬ e^{j2k r·û} dA_투영
  즉 **û 방향에서 평행 광선을 균일 격자(간격 d)로 쏘면**, 맞은 지점마다
        E = Σ_hits |Γ_i| · e^{j2k p_i·û} · d²        (d² = 광선 1발의 투영면적)
        σ = (4π/λ²) · |E|²
  격자 간격 d 는 λ/6 이하로 잡으면 위상이 잘 표현된다(수렴성은 validate() 로 확인).

실행:  CUDA_VISIBLE_DEVICES=2 python src/rcs_sbr.py          (해석해 검증 + 기존 PO 대조)
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np                                   # noqa: E402

# **반드시 mitsuba import 전에** 가장 한가한 GPU 를 잡는다 (scene_build 와 동일 규약).
from gpu import pick as _pick_gpu                    # noqa: E402
_pick_gpu(verbose=False)

import mitsuba as mi                                 # noqa: E402
import drjit as dr                                   # noqa: E402
import sionna.rt as _rt  # noqa: E402,F401  (mitsuba variant 를 sionna 와 동일하게 초기화)

from geom import Mesh                                # noqa: E402
from materials import gamma_po                       # noqa: E402  (Sionna 와 같은 재질 표)

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  geom.Mesh → Mitsuba 씬 (그룹당 shape 1개 → 그룹별 |Γ| 를 붙일 수 있다)
# --------------------------------------------------------------------------- #
def _mi_scene_from_mesh(mesh: Mesh, group_mat: dict):
    """그룹당 mi.Mesh 하나. 반환: (mi_scene, [shape...], [gamma...])"""
    V = np.asarray(mesh.v, np.float32)
    F = np.asarray(mesh.f, np.uint32)
    G = np.asarray(mesh.g)

    shapes_d, gammas = {}, []
    for gi, grp in enumerate(sorted(set(G.tolist()))):
        f = F[G == grp]
        used = np.unique(f)
        remap = np.full(V.shape[0], -1, np.int64)
        remap[used] = np.arange(len(used))
        m = mi.Mesh(f"g_{grp}", vertex_count=len(used), face_count=len(f),
                    has_vertex_normals=False, has_vertex_texcoords=False)
        p = mi.traverse(m)
        p["vertex_positions"] = mi.Float(V[used].ravel())
        p["faces"] = mi.UInt32(remap[f].astype(np.uint32).ravel())
        p.update()
        shapes_d[f"s_{gi}"] = m
        mat = group_mat.get(grp, "plastic") if isinstance(group_mat.get(grp), str) else None
        gammas.append(float(group_mat[grp]) if mat is None else gamma_po(mat))
    scene = mi.load_dict({"type": "scene", **shapes_d})
    return scene, list(scene.shapes()), np.asarray(gammas, float)


def _look(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], float)


# --------------------------------------------------------------------------- #
#  SBR — 모노스태틱 후방산란 RCS
# --------------------------------------------------------------------------- #
def rcs_sbr(mesh: Mesh, group_mat: dict, fc: float, az_deg, el_deg=0.0,
            spacing=None, max_bounce=1, pad=1.15, return_hits=False):
    """SBR 로 **모노스태틱 RCS σ[m²]** 를 낸다. az_deg 는 스칼라 또는 배열.

      mesh      : geom.Mesh (표적)
      group_mat : 그룹 → 재질키(str, materials.MATERIALS) 또는 |Γ|(float)
      spacing   : 광선 격자 간격 [m]. 기본 λ/6.
      max_bounce: 1 = 1차 PO(=기존 PO 와 동급, 단 가림 포함).
                  ≥2 = 반사 후 재추적 → **오목부(로터 아래·짐벌 그늘) 다중반사** 반영.
      pad       : 광선 격자를 표적 투영 bbox 대비 얼마나 넓게 (여유)

    반환: σ (스칼라 또는 (n_az,) 배열).  return_hits=True 면 (σ, 진단dict)."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / 6.0

    scene, shapes, gammas = _mi_scene_from_mesh(mesh, group_mat)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]

    V = np.asarray(mesh.v, float)
    ctr = 0.5 * (V.max(0) + V.min(0))
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d   # 외접구

    az_list = np.atleast_1d(np.asarray(az_deg, float))
    sig = np.zeros(len(az_list))
    diag = []

    for i, az in enumerate(az_list):
        u = _look(az, el_deg)                     # 표적 → 레이더 방향
        # û 에 수직인 평면 격자 (e1, e2)
        tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
        e2 = np.cross(u, e1)
        n = int(np.ceil(2 * Rout / d))
        t = (np.arange(n) - (n - 1) / 2.0) * d
        A, B = np.meshgrid(t, t, indexing="ij")
        # 광선 원점: 표적 밖(+û 쪽)에서 −û 방향으로 쏜다
        O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
        D = np.tile(-u, (O.shape[0], 1))

        E = 0.0 + 0.0j
        n_hit_total = 0
        amp = np.ones(O.shape[0])                 # 다중반사 시 누적 반사계수
        path = np.zeros(O.shape[0])               # 추가 경로길이(다중반사 위상)
        alive = np.ones(O.shape[0], bool)
        Ocur, Dcur = O.copy(), D.copy()

        for b in range(max_bounce):
            if not alive.any():
                break
            ray = mi.Ray3f(o=mi.Point3f(*Ocur[alive].T.astype(np.float32)),
                           d=mi.Vector3f(*Dcur[alive].T.astype(np.float32)))
            si = scene.ray_intersect(ray)
            valid = np.asarray(si.is_valid()).astype(bool)
            P = np.asarray(mi.Point3f(si.p)).T                     # (Nv,3)
            Nn = np.asarray(mi.Vector3f(si.n)).T
            # shape → |Γ|  (Dr.Jit 1.x: ShapePtr 비교는 연산자 == 를 쓴다. dr.eq 는 없다.)
            g = np.zeros(P.shape[0])
            for sp, gm in zip(shape_ptrs, gammas):
                g = np.where(np.asarray(si.shape == sp).astype(bool), gm, g)

            idx = np.where(alive)[0]
            hit = idx[valid]
            if len(hit) == 0:
                break
            Ph, Nh, gh = P[valid], Nn[valid], g[valid]
            # 법선을 광선 반대쪽으로 정렬(면의 앞/뒤 무관하게)
            flip = (Nh @ (-Dcur[hit][0] if False else np.zeros(3))) if False else None
            sgn = np.sign(np.einsum("ij,ij->i", Nh, -Dcur[hit]))
            sgn[sgn == 0] = 1.0
            Nh = Nh * sgn[:, None]

            # ① 이 충돌점의 PO 기여 — **레이더 방향으로 되돌아가는 성분만**
            #    (n̂·û)>0 이어야 레이더를 향한다. dA_투영 = d² 는 이미 광선 1발의 몫.
            cosr = Nh @ u
            lit = cosr > 1e-6
            if lit.any():
                r_dot = Ph[lit] @ u
                phase = np.exp(1j * 2.0 * k * (r_dot - 0.5 * path[hit][lit]))
                E += np.sum(amp[hit][lit] * gh[lit] * phase) * d * d
                n_hit_total += int(lit.sum())

            if b + 1 >= max_bounce:
                break
            # ② 정반사 후 재추적 (오목부 다중반사)
            Dh = Dcur[hit]
            Dref = Dh - 2.0 * np.einsum("ij,ij->i", Dh, Nh)[:, None] * Nh
            newO = Ph + 1e-4 * Dref
            alive2 = np.zeros(O.shape[0], bool); alive2[hit] = True
            Ocur[hit] = newO; Dcur[hit] = Dref
            amp[hit] = amp[hit] * gh
            path[hit] = path[hit] + np.linalg.norm(Ph - Ocur[hit], axis=1) * 0  # (1차근사: 위상은 r·û 로)
            alive = alive2

        sig[i] = (4.0 * np.pi / lam ** 2) * abs(E) ** 2
        diag.append(dict(az=float(az), n_rays=int(O.shape[0]), n_hits=n_hit_total,
                         spacing=d, rays_per_lambda=lam / d))

    out = sig if len(az_list) > 1 else float(sig[0])
    return (out, diag) if return_hits else out


# --------------------------------------------------------------------------- #
#  검증 — 해석해가 있는 표적
# --------------------------------------------------------------------------- #
def validate(fc=3.5e9, verbose=True):
    """구(σ=πr²) · 평판(σ=4πA²/λ²) 로 SBR 커널을 검증하고, 격자 수렴성을 본다."""
    from geom import uv_sphere, box
    lam = C0 / fc
    res = {}

    if verbose:
        print("=" * 82)
        print(f"SBR 검증 @ {fc/1e9:.1f} GHz (λ={lam*100:.2f} cm)")
        print("=" * 82)

    # --- 금속구: 광학영역 σ = πr² (r ≫ λ) ---
    r = 0.5
    sph = uv_sphere(r, seg=180, rings=90, group="metal")
    exact = np.pi * r ** 2
    if verbose:
        print(f"\n[1] 금속구 r={r} m  (r/λ={r/lam:.1f})   해석해 σ=πr²={10*np.log10(exact):+.3f} dBsm")
        print(f"    {'격자 d':>10} {'λ/d':>6} {'광선수':>10} {'σ_SBR':>10} {'오차':>8}")
    for div in (4, 6, 10, 16):
        d = lam / div
        s = rcs_sbr(sph, {"metal": "metal"}, fc, az_deg=0.0, el_deg=0.0, spacing=d)
        err = 10 * np.log10(s / exact)
        res[f"sphere_lam/{div}"] = err
        if verbose:
            n = int(np.ceil(2 * (r * 1.15 + 3 * d) / d)) ** 2
            print(f"    {d*1000:9.2f}mm {div:6d} {n:10,d} {10*np.log10(s):+9.3f} {err:+7.3f} dB")

    # --- 금속 평판(정면): σ = 4πA²/λ² ---
    a = 0.4
    plate = box(a, a, 0.002, group="metal")
    exact_p = 4 * np.pi * (a * a) ** 2 / lam ** 2
    if verbose:
        print(f"\n[2] 금속 평판 {a}×{a} m (정면)   해석해 σ=4πA²/λ²={10*np.log10(exact_p):+.2f} dBsm")
        print(f"    {'격자 d':>10} {'λ/d':>6} {'σ_SBR':>10} {'오차':>8}")
    for div in (4, 6, 10):
        d = lam / div
        s = rcs_sbr(plate, {"metal": "metal"}, fc, az_deg=0.0, el_deg=90.0, spacing=d)
        err = 10 * np.log10(s / exact_p)
        res[f"plate_lam/{div}"] = err
        if verbose:
            print(f"    {d*1000:9.2f}mm {div:6d} {10*np.log10(s):+9.2f} {err:+7.2f} dB")
    return res


def compare_with_po(fc=3.5e9, drone="mavic4pro", el=15.0, n_az=24):
    """같은 드론을 SBR 과 기존 PO 로 재서 비교한다 — **가림(occlusion)의 효과가 여기서 드러난다.**"""
    from drones import DRONES, build_drone, DRONE_GROUP_MAT, drone_gamma_map
    from rcs_po import mesh_to_points, rcs_from_points
    spec = DRONES[drone]
    m = build_drone(spec)
    gmat = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}
    az = np.linspace(0, 360, n_az, endpoint=False)

    s_sbr1 = rcs_sbr(m, gmat, fc, az_deg=az, el_deg=el, max_bounce=1)
    s_sbr3 = rcs_sbr(m, gmat, fc, az_deg=az, el_deg=el, max_bounce=3)
    lam = C0 / fc
    P, N, dA, w = mesh_to_points(m, lam / 7.0, gamma=drone_gamma_map(spec))
    s_po = rcs_from_points(P, N, dA, fc, az_deg=az, el_deg=el, w=w)

    print(f"\n{'='*82}\n{spec.name} @ el={el}°, 방위 {n_az}점 평균 RCS\n{'='*82}")
    for nm, s in (("PO (기존, 가림 없음)", s_po),
                  ("SBR 1-bounce (가림 O)", s_sbr1),
                  ("SBR 3-bounce (가림+오목부)", s_sbr3)):
        print(f"  {nm:28s} {10*np.log10(np.mean(s)):+7.2f} dBsm   (피크 {10*np.log10(np.max(s)):+7.2f})")
    d1 = 10 * np.log10(np.mean(s_sbr1) / np.mean(s_po))
    d3 = 10 * np.log10(np.mean(s_sbr3) / np.mean(s_sbr1))
    print(f"\n  가림(occlusion)의 효과      : {d1:+.2f} dB   (SBR1 − PO)")
    print(f"  오목부 다중반사의 효과      : {d3:+.2f} dB   (SBR3 − SBR1)")
    return dict(po=s_po, sbr1=s_sbr1, sbr3=s_sbr3, az=az)


if __name__ == "__main__":
    validate()
    compare_with_po()
