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
  격자 간격 d = λ/DEFAULT_DIV(현재 λ/12). ⚠ 곡면 수렴은 단조롭지 않다(실루엣 grazing 위상
  에일리어싱으로 ±1.5 dB 진동) — 절대레벨엔 격자 불확실성이 있고 자세간 상대패턴만 안정하다(validate()).

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

#  광선 격자 간격 = λ / DEFAULT_DIV.
#  ⚠ 수렴은 곡면에서 단조롭지 않다(구 r=0.5m 오차 실측: λ/6 +1.75 → λ/10 +0.40 → λ/12 +1.45 → λ/16 −0.58 dB,
#    0 을 관통해 ±1.5 dB 진동 — 실루엣 grazing 광선의 위상 에일리어싱). 평판 정면(el=90°)은 위상항이
#    상수라 이 진동을 진단 못 한다 → **절대레벨엔 ±1.5 dB 격자 불확실성**이 있다(자세간 상대패턴은 0.06 dB 로 안정).
DEFAULT_DIV = 12

#  유전체 셸(투과 대상) — 이 그룹은 광선을 통과시켜 내부 금속(배터리/PCB)을 본다.
#  근거: SBR first-hit 은 셸을 불투명 처리해 내부 금속을 삭제하는데, 재질 모델(셸 |Γ|=0.28)의 전제가
#  '반투명 셸 통과 → 내부 금속 지배' 이므로 투과를 넣지 않으면 엔진이 자기모순이다(직접 검증: battery/pcb 0 히트).
_DIELECTRIC_SHELLS = frozenset({"body", "canopy"})


# --------------------------------------------------------------------------- #
#  geom.Mesh → Mitsuba 씬 (그룹당 shape 1개 → 그룹별 |Γ| 를 붙일 수 있다)
# --------------------------------------------------------------------------- #
def _mi_scene_from_mesh(mesh: Mesh, group_mat: dict, fc: float = 3.5e9, exclude=()):
    """그룹당 mi.Mesh 하나. 반환: (mi_scene, [shape...], [gamma...]).
    fc: |Γ| 를 주파수에 맞춰 계산(override 재질은 상수라 무영향, 잠복버그 예방).
    exclude: 이 그룹들을 씬에서 뺀다 — 유전체 셸을 빼고 쏘면 광선이 통과해 내부를 본다(투과 패스용)."""
    V = np.asarray(mesh.v, np.float32)
    F = np.asarray(mesh.f, np.uint32)
    G = np.asarray(mesh.g)

    shapes_d, gammas = {}, []
    for gi, grp in enumerate(sorted(set(G.tolist()))):
        if grp in exclude:
            continue
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
        val = group_mat.get(grp, "plastic")             # 누락 그룹은 안전 기본(plastic) — KeyError 방지
        gammas.append(float(val) if not isinstance(val, str) else gamma_po(val, fc))
    scene = mi.load_dict({"type": "scene", **shapes_d})
    return scene, list(scene.shapes()), np.asarray(gammas, float)


def _look(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], float)


# --------------------------------------------------------------------------- #
#  SBR — 모노스태틱 후방산란 RCS
# --------------------------------------------------------------------------- #
_SCENE_CACHE: dict = {}


def _scene_for(mesh: Mesh, group_mat: dict, key=None, fc: float = 3.5e9, exclude=()):
    """씬 재사용 — 같은 메쉬로 방위각을 스윕할 때 매번 다시 만들지 않는다.
    ⚠ gammas 는 fc 의존이므로 캐시키에 fc(MHz)·exclude 를 접어 넣는다(과거엔 stale 위험)."""
    ck = (key, round(float(fc) / 1e6), tuple(sorted(exclude))) if key is not None else None
    if ck is not None and ck in _SCENE_CACHE:
        return _SCENE_CACHE[ck]
    out = _mi_scene_from_mesh(mesh, group_mat, fc, exclude)
    if ck is not None:
        _SCENE_CACHE[ck] = out
    return out


def rcs_sbr_batch(mesh: Mesh, group_mat: dict, fc: float, az_deg, el_deg=0.0,
                  spacing=None, pad=1.15, cache_key=None, chunk_az=None, penetrate=True, jitter=2):
    """**방위각 전체를 한 배치로** GPU 에 올려 1-bounce SBR σ 를 낸다 (가림 포함).

    왜 배치인가: 방위각 하나당 Mitsuba 호출을 따로 하면 커널 실행 오버헤드가 지배한다.
    광선 격자 여러 방위를 **하나의 큰 광선 다발**로 합쳐 쏘면 GPU 를 제대로 쓴다.

    penetrate=True 면 **유전체 셸(_DIELECTRIC_SHELLS)을 통과시켜 내부 금속(배터리/PCB)**을
    왕복 투과 진폭 τ=1−|Γ_shell|² 로 가중해 외부 기여와 **코히런트 합산**한다 — first-hit 가
    내부를 삭제하는 자기모순(직접 검증: battery/pcb 0 히트)을 없앤다. 셸 없는 표적(구·평판)엔 무영향.
    ⚠ 근사: 얇은 셸의 굴절(광로 굴곡)·유전체 내 위상지연은 무시(1차 투과·기하위상만).

    다중반사가 필요하면 rcs_sbr(..., max_bounce≥2) 를 쓸 것 (배치 안 함)."""
    from gpu import budget_mb
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV

    scene, shapes, gammas = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]

    # 유전체 셸 투과 준비 — 셸 shape 위치(=그룹 정렬순) + 셸 제거한 '내부 씬'
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _DIELECTRIC_SHELLS]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_DIELECTRIC_SHELLS)
        shptr_i = [mi.ShapePtr(s) for s in shapes_i]

    V = np.asarray(mesh.v, float)
    ctr = 0.5 * (V.max(0) + V.min(0))
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d

    n = int(np.ceil(2 * Rout / d))
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    A, B = A.ravel(), B.ravel()
    rays_per_az = A.size

    az = np.atleast_1d(np.asarray(az_deg, float))
    if chunk_az is None:
        per_az_bytes = rays_per_az * 160 * (2 if do_pen else 1)   # 투과 패스면 광선 2배
        chunk_az = int(max(1, min(len(az), budget_mb() * 1024 * 1024 * 0.85 / per_az_bytes)))

    def _lit_g_phase(si, shptr, gam, D, U):
        """히트 → (lit 마스크, g[|Γ|], 위상, valid). 외부/내부 패스 공통."""
        valid = np.asarray(si.is_valid()).astype(bool)
        P = np.asarray(mi.Point3f(si.p)).T
        Nn = np.asarray(mi.Vector3f(si.n)).T
        g = np.zeros(P.shape[0])
        for sp, gm in zip(shptr, gam):
            g = np.where(np.asarray(si.shape == sp).astype(bool), gm, g)
        sgn = np.sign(np.einsum("ij,ij->i", Nn, -D)); sgn[sgn == 0] = 1.0
        Nn = Nn * sgn[:, None]
        lit = valid & (np.einsum("ij,ij->i", Nn, U) > 1e-6)      # 조명·수신 게이트
        phase = np.exp(1j * 2.0 * k * np.einsum("ij,ij->i", P - ctr, U))  # 중심감산(float32 안정·σ 불변)
        return lit, g, phase, valid, si

    # jitter: 격자 위상 평균으로 절대 σ 안정화(단일격자 ±1.5 dB → J=2 ±0.15 dB). J² 오프셋.
    J = max(1, int(jitter))
    fr = (np.arange(J) + 0.5) / J - 0.5
    offsets = [(ox * d, oy * d) for ox in fr for oy in fr]

    sig = np.zeros(len(az))
    for s0 in range(0, len(az), chunk_az):
        sub = az[s0:s0 + chunk_az]
        bases = []
        for a in sub:
            u = _look(a, el_deg)
            tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
            e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
            e2 = np.cross(u, e1)
            bases.append((u, e1, e2))
        aidx = np.repeat(np.arange(len(sub)), rays_per_az)
        sig_acc = np.zeros(len(sub))
        for ox, oy in offsets:                                    # 격자 위상 평균
            O_all, D_all, U_all = [], [], []
            for u, e1, e2 in bases:
                O_all.append((ctr + Rout * u)[None, :] + (A + ox)[:, None] * e1 + (B + oy)[:, None] * e2)
                D_all.append(np.tile(-u, (rays_per_az, 1)))
                U_all.append(np.tile(u, (rays_per_az, 1)))
            O = np.concatenate(O_all); D = np.concatenate(D_all); U = np.concatenate(U_all)

            ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                           d=mi.Vector3f(*D.T.astype(np.float32)))
            si = scene.ray_intersect(ray)
            lit, g, phase, valid, si = _lit_g_phase(si, shape_ptrs, gammas, D, U)
            contrib = np.where(lit, g, 0.0) * phase

            # ── 유전체 셸 투과: 셸 맞은 광선만 내부 금속을 τ 가중 코히런트 가산 ──
            if do_pen:
                tau = np.zeros(valid.shape[0])                    # 왕복 투과 진폭(셸 아니면 0)
                for i in shell_pos:
                    tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                                   1.0 - gammas[i] ** 2, tau)
                si2 = scene_i.ray_intersect(ray)
                lit2, g2, phase2, _, _ = _lit_g_phase(si2, shptr_i, gammas_i, D, U)
                contrib = contrib + np.where(lit2 & (tau > 0), tau * g2, 0.0) * phase2

            E = np.zeros(len(sub), complex)
            np.add.at(E, aidx, contrib)
            sig_acc += (4.0 * np.pi / lam ** 2) * np.abs(E * d * d) ** 2
        sig[s0:s0 + len(sub)] = sig_acc / len(offsets)

    return sig if len(az) > 1 else float(sig[0])


def rcs_sbr_multistatic(mesh: Mesh, group_mat: dict, fc: float, u_i, u_s_list,
                        spacing=None, pad=1.15, cache_key=None, penetrate=True, jitter=2):
    """**바이스태틱/멀티스태틱** RCS σ(û_i,û_s)[m²].

    û_i = 표적→송신국, û_s = 표적→수신국 방향(둘 다 outward 단위벡터).
    일반 PO:  E ∝ Σ_hit |Γ| · e^{jk(û_i+û_s)·p} · d²,   σ = 4π/λ²|E|².
      · 조명면 판정 (n̂·û_i>0) — 광선을 û_i 로 쏘므로 dA_투영=d² 상쇄가 그대로 성립(추가 obliquity 없음).
      · 수신 가시 판정 (n̂·û_s>0) — û_s 로 되돌아가는 면만.
      · 모노스태틱은 û_s=û_i 특수해 → e^{j2k û·p} 로 rcs_sbr_batch 와 정확히 일치.

    **멀티스태틱 효율**: 조명(광선추적)은 û_i 로만 결정 → **한 번만** 쏘고, 각 û_s(∈u_s_list)에 대해
    싼 위상합만 반복한다(Rx 를 늘려도 비싼 광선추적 재사용). u_s_list = [û_i] 면 모노(rcs_sbr_batch 와 0dB 일치).

    ⚠ **적용범위 한계(집중 적대검증으로 확인, 정직 표기):**
      (1) **전방산란 무효**: β→180°(û_s≈−û_i)에서 조명게이트(n̂·û_i>0)와 수신게이트(n̂·û_s>0)가
          상호배타 → σ≡0. lit-PO 는 그림자복사(Babinet 전방로브 σ_fwd=4πA²/λ²)를 못 낸다 →
          **후방~중간 바이스태틱각(β≲90°급, 조명면 일부가 여전히 Rx 가시)에만 유효.**
      (2) **상반성 부분성립**: σ(û_i,û_s)=σ(û_s,û_i)가 볼록·강반사에선 성립(구 ~0.2dB)하나
          **비볼록 표적의 깊은 널에선 rms~5~9dB(최대 18dB) 깨진다**(û_i 단일조명격자 재사용의 구조적 대가,
          격자세분으로 안 줄어듦). 상반성이 필요하면 σ_sym=√(σ(i,s)·σ(s,i)) 로 σ레벨 대칭화할 것.
      (3) 투과 출사경로(û_s 로 셸 재통과)는 입사 τ 로 근사(1차 투과) → 바이스태틱 비대칭을 더 키움."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV
    u_i = np.asarray(u_i, float); u_i = u_i / np.linalg.norm(u_i)
    U_s = np.atleast_2d(np.asarray(u_s_list, float))
    U_s = U_s / np.linalg.norm(U_s, axis=1, keepdims=True)

    scene, shapes, gammas = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _DIELECTRIC_SHELLS]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_DIELECTRIC_SHELLS)
        shptr_i = [mi.ShapePtr(s) for s in shapes_i]

    V = np.asarray(mesh.v, float)
    ctr = 0.5 * (V.max(0) + V.min(0))
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d

    # 조명 격자(û_i 수직 평면) basis + jitter 오프셋(격자 위상 평균)
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u_i[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u_i, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u_i, e1)
    n = int(np.ceil(2 * Rout / d))
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij"); A, B = A.ravel(), B.ravel()
    J = max(1, int(jitter))
    fr = (np.arange(J) + 0.5) / J - 0.5
    offsets = [(ox * d, oy * d) for ox in fr for oy in fr]

    sig_acc = np.zeros(len(U_s))
    for ox, oy in offsets:
        O = (ctr + Rout * u_i)[None, :] + (A + ox)[:, None] * e1 + (B + oy)[:, None] * e2
        D = np.tile(-u_i, (A.size, 1))
        ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)), d=mi.Vector3f(*D.T.astype(np.float32)))

        def _hits(sc, shptr, gam):
            si = sc.ray_intersect(ray)
            valid = np.asarray(si.is_valid()).astype(bool)
            P = np.asarray(mi.Point3f(si.p)).T
            Nn = np.asarray(mi.Vector3f(si.n)).T
            g = np.zeros(P.shape[0])
            for sp, gm in zip(shptr, gam):
                g = np.where(np.asarray(si.shape == sp).astype(bool), gm, g)
            sgn = np.sign(np.einsum("ij,ij->i", Nn, -D)); sgn[sgn == 0] = 1.0
            return valid, P - ctr, Nn * sgn[:, None], g, si

        valid, Pc, Nn, g, si = _hits(scene, shape_ptrs, gammas)      # 외부 조명 히트
        lit_i = valid & ((Nn @ u_i) > 1e-6)      # û_i 조명 게이트
        if do_pen:
            tau = np.zeros(valid.shape[0])
            for i in shell_pos:
                tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                               1.0 - gammas[i] ** 2, tau)
            valid2, Pc2, Nn2, g2, _ = _hits(scene_i, shptr_i, gammas_i)   # 내부 금속 히트
            lit2_i = valid2 & ((Nn2 @ u_i) > 1e-6)

        # ⚠ obliquity 는 û_i 개구 샘플링에 내재한 (n̂·û_i) 를 그대로 쓴다(표준 PO). 대칭
        #   √((n̂·û_i)(n̂·û_s)) 로 승격하면 이론상 상반성이 복원되나, grazing 조명면(n̂·û_i→0)에서
        #   √(cosθ_s/cosθ_i) 가 이산 격자를 폭발시켜(단일광선 수백배 가중) 오히려 rms 오차가 커진다.
        #   → 표준 (n̂·û_i) 유지. 상반성이 필요하면 σ_sym=√(σ(i,s)·σ(s,i)) 로 σ 레벨에서 대칭화할 것.
        for j, u_s in enumerate(U_s):
            lit = lit_i & ((Nn @ u_s) > 1e-6)   # + û_s 수신 게이트
            E = np.sum(np.where(lit, g, 0.0) * np.exp(1j * k * (Pc @ (u_i + u_s))))
            if do_pen:
                litp = lit2_i & ((Nn2 @ u_s) > 1e-6) & (tau > 0)
                E = E + np.sum(np.where(litp, tau * g2, 0.0) * np.exp(1j * k * (Pc2 @ (u_i + u_s))))
            sig_acc[j] += (4.0 * np.pi / lam ** 2) * np.abs(E * d * d) ** 2
    sig = sig_acc / len(offsets)
    return sig if len(U_s) > 1 else float(sig[0])


def sbr_field(mesh: Mesh, group_mat: dict, fc: float, u, spacing=None, pad=1.15,
              cache_key=None):
    """**복소 산란장 E(û)** 를 돌려준다 (σ 가 아니라 E — 마이크로도플러는 위상이 필요하다).

        E(û) = Σ_hits |Γ_i| · e^{j2k p_i·û} · d²          σ = (4π/λ²)|E|²

    û 는 표적 → 레이더 방향 단위벡터."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV
    u = np.asarray(u, float); u = u / np.linalg.norm(u)

    scene, shapes, gammas = _scene_for(mesh, group_mat, cache_key)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]

    V = np.asarray(mesh.v, float)
    ctr = 0.5 * (V.max(0) + V.min(0))
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d
    n = int(np.ceil(2 * Rout / d))
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
    D = np.tile(-u, (O.shape[0], 1))

    ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                   d=mi.Vector3f(*D.T.astype(np.float32)))
    si = scene.ray_intersect(ray)
    valid = np.asarray(si.is_valid()).astype(bool)
    P = np.asarray(mi.Point3f(si.p)).T
    Nn = np.asarray(mi.Vector3f(si.n)).T
    g = np.zeros(P.shape[0])
    for sp, gm in zip(shape_ptrs, gammas):
        g = np.where(np.asarray(si.shape == sp).astype(bool), gm, g)
    # 법선을 **광선이 오는 쪽**(= 레이더 방향 û)으로 정렬한다.
    #   광선 방향 D = −û 이므로 광선 반대쪽은 −D = +û.  ⚠ 여기서 부호를 틀리면 조명면이
    #   0개가 되어 E ≡ 0 이 된다(실제로 한 번 그랬다).
    sgn = np.sign(Nn @ u); sgn[sgn == 0] = 1.0
    Nn = Nn * sgn[:, None]
    lit = valid & ((Nn @ u) > 1e-6)
    return complex(np.sum(np.where(lit, g, 0.0) * np.exp(1j * 2.0 * k * ((P - ctr) @ u)))) * d * d


def rcs_sbr(mesh: Mesh, group_mat: dict, fc: float, az_deg, el_deg=0.0,
            spacing=None, max_bounce=1, pad=1.15, return_hits=False):
    """SBR 로 **모노스태틱 RCS σ[m²]** 를 낸다. az_deg 는 스칼라 또는 배열.

      mesh      : geom.Mesh (표적)
      group_mat : 그룹 → 재질키(str, materials.MATERIALS) 또는 |Γ|(float)
      spacing   : 광선 격자 간격 [m]. 기본 λ/DEFAULT_DIV(현재 λ/12).
      max_bounce: 1 = 1차 PO(=기존 PO 와 동급, 단 가림 포함).
                  ≥2 = 반사 후 재추적 → **오목부(로터 아래·짐벌 그늘) 다중반사** 반영.
      pad       : 광선 격자를 표적 투영 bbox 대비 얼마나 넓게 (여유)

    반환: σ (스칼라 또는 (n_az,) 배열).  return_hits=True 면 (σ, 진단dict)."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV

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
            sgn = np.sign(np.einsum("ij,ij->i", Nh, -Dcur[hit]))
            sgn[sgn == 0] = 1.0
            Nh = Nh * sgn[:, None]

            # ① 이 충돌점의 PO 기여 — **레이더 방향으로 되돌아가는 성분만**
            #    (n̂·û)>0 이어야 레이더를 향한다. dA_투영 = d² 는 이미 광선 1발의 몫.
            cosr = Nh @ u
            lit = cosr > 1e-6
            if lit.any():
                r_dot = (Ph[lit] - ctr) @ u        # 중심감산(float32 안정·σ 불변)
                phase = np.exp(1j * 2.0 * k * (r_dot - 0.5 * path[hit][lit]))
                E += np.sum(amp[hit][lit] * gh[lit] * phase) * d * d
                n_hit_total += int(lit.sum())

            if b + 1 >= max_bounce:
                break
            # ② 정반사 후 재추적 (오목부 다중반사)
            #   ⚠ 2026-07-16 버그수정(적대적 감사): 이전엔 이 누적경로를 `* 0` 으로 죽여
            #   2차+ 반사의 경로길이가 위상 e^{j2k(r·û − ½·path)} 에 안 들어갔다 → 오목부 다중반사가
            #   물리적으로 틀렸고(이면반사체 ~34 dB), '다중반사는 사소하다'는 결론이 그 고장난
            #   커널에서 나온 순환논법이었다. 이제 **직전 충돌점까지의 실제 이동거리를 누적**한다.
            Dh = Dcur[hit]
            Dref = Dh - 2.0 * np.einsum("ij,ij->i", Dh, Nh)[:, None] * Nh
            seg = np.linalg.norm(Ph - Ocur[hit], axis=1)          # 이 bounce 에서 실제 이동한 거리
            newO = Ph + 1e-4 * Dref
            alive2 = np.zeros(O.shape[0], bool); alive2[hit] = True
            Ocur[hit] = newO; Dcur[hit] = Dref
            amp[hit] = amp[hit] * gh
            path[hit] = path[hit] + seg                           # 누적 경로길이(위상에 반영)
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
