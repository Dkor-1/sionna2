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
  에일리어싱으로 진동) — 절대레벨엔 격자 불확실성이 있고 자세간 상대패턴만 안정하다(validate()).
  ⚠ 2026-07-30 정정: 이 진동 폭을 오래 **"±1.5 dB"** 라 적어왔는데 **단일 숫자가 아니다**.
    실측(`outputs/report2_waveform_rcs.json` sbr_validation.dither, 서브셀 오프셋 격자 산포):
      λ/8 **5.284 dB** (lo −4.843 / hi +0.441) · λ/12 **1.373 dB** · λ/16 **1.782 dB** (peak-to-peak).
    즉 **격자를 촘촘히 하면 좋아지지만 단조롭지도 않다**(12 < 16). 숫자를 인용할 때는 div 를 함께
    적고, 리포트에는 손으로 적지 말고 JSON dither 에서 주입할 것.

■ 검증 과녁 세 개 (validate())
  [1] PEC 구   — 해석 PO(커널의 과녁) + 정확 Mie(참값). 격자 수렴을 본다.
  [2] PEC 평판 — 정면입사 4πA²/λ² 는 점근이 아니라 **PO 의 정확한 답**.
  [3] PEC 직각 이면반사체 — 8πa²b²/λ². **오목**이라 다중반사 경로를 밟는 유일한 케이스다.
      [1][2] 는 볼록이라 `max_bounce≥2` 의 위상이 아무리 틀려도 통과한다(실제로 통과했다).
  세 과녁의 최신 수치는 `outputs/sbr_defect_fixes.json`(생성: benchmark/verify_sbr_defect_fixes.py).

실행:  CUDA_VISIBLE_DEVICES=2 python src/rcs_sbr.py          (기준해 검증 + 기존 PO 대조)
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
#  ⚠ 수렴은 곡면에서 단조롭지 않다(구 r=0.5m 잔차 실측, **πr² 점근 기준으로 잰 옛 값** — 지금 과녁은
#    해석 PO 이고 그만큼(3.5 GHz 에서 −0.107 dB) 밀린다, validate() 참조:
#    λ/6 +1.75 → λ/10 +0.40 → λ/12 +1.45 → λ/16 −0.58 dB,
#    0 을 관통해 진동 — 실루엣 grazing 광선의 위상 에일리어싱). 평판 정면(el=90°)은 위상항이
#    상수라 이 진동을 진단 못 한다 → **절대레벨엔 격자 불확실성**이 있다(자세간 상대패턴은 0.06 dB 로 안정).
#    ⚠ 그 폭은 div 의존이다 — λ/8 5.284 / λ/12 1.373 / λ/16 1.782 dB (실측, 위 정정 참조).
DEFAULT_DIV = 12

#  유전체 셸(투과 대상) — 이 그룹은 광선을 통과시켜 내부 금속(배터리/PCB)을 본다.
#  근거: SBR first-hit 은 셸을 불투명 처리해 내부 금속을 삭제하는데, 재질 모델(셸 |Γ|=0.28)의 전제가
#  '반투명 셸 통과 → 내부 금속 지배' 이므로 투과를 넣지 않으면 엔진이 자기모순이다(직접 검증: battery/pcb 0 히트).
_DIELECTRIC_SHELLS = frozenset({"body", "canopy"})

#  ⚠ **투과 판정은 재질이 아니라 그룹 이름으로 한다** — 이게 조용한 함정이다(2026-07-28 규명).
#    `penetrate=True` 면 위 이름의 그룹을 "반투명 셸" 로 보고 왕복 투과 τ = 1−|Γ|² 를 곱하며,
#    내부 패스에서는 그 그룹을 **씬에서 빼서** 뒤쪽 금속이 보이게 한다.
#    문제: 새 기체를 추가하며 **카본 데크**를 편의상 "body" 그룹에 넣으면,
#      · 엔진이 τ = 1 − 0.90² = 0.19 = **−7.2 dB** 투과를 허용하고(왕복 −14.4 dB),
#      · 실제 카본 2 mm 의 진폭투과는 σ=3000 S/m 기준 표피깊이 155 µm 의 12.9 배라
#        **≈ −112 dB** 다 → **약 97 dB 오차**,
#      · 게다가 그 데크가 **가림도 안 하게** 되어 아래 배터리가 그대로 보인다.
#    → 아래 `_resolve_shells()` 가 셸로 선언된 그룹의 |Γ| 를 검사해 **불투명 재질이면 즉시 예외**를
#      던진다. 이름 규약에만 기대지 않는다.
SHELL_GAMMA_MAX = 0.5               # 셸로 선언 가능한 |Γ| 상한 (플라스틱 0.28 ✓ / 카본 0.90 ✗)


def _resolve_shells(group_names, group_mat, shell_groups=None):
    """투과시킬 '유전체 셸' 그룹 집합을 정하고 **재질로 검증**한다.

    shell_groups=None 이면 기존 규약(_DIELECTRIC_SHELLS)을 쓴다. 새 기종은 명시로 넘길 것
    (열린 프레임은 셸이 아예 없으므로 `shell_groups=()`)."""
    from materials import gamma_po
    want = _DIELECTRIC_SHELLS if shell_groups is None else frozenset(shell_groups)
    present = [g for g in dict.fromkeys(group_names) if g in want]
    for g in present:
        mat = group_mat.get(g)
        if mat is None:
            continue
        try:
            gm = float(gamma_po(mat)) if isinstance(mat, str) else float(mat)
        except Exception:
            continue
        if gm >= SHELL_GAMMA_MAX:
            raise ValueError(
                f"rcs_sbr: 그룹 {g!r} 이 '유전체 셸'로 선언됐는데 재질 {mat!r} 의 |Γ|={gm:.3f} 로 "
                f"불투명하다(상한 {SHELL_GAMMA_MAX}). 그대로 두면 왕복 투과를 "
                f"{20*__import__('math').log10(max(1e-12, 1 - gm**2)):.1f} dB 로 잡아 "
                f"실제(금속·카본은 수십~100 dB 차단)와 크게 어긋나고, 가림도 사라진다. "
                f"→ 이 그룹을 shell_groups 에서 빼거나 별도 그룹(예: 'deck')으로 분리할 것.")
    return want


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
                  spacing=None, pad=1.15, cache_key=None, chunk_az=None, penetrate=True, jitter=2,
                  shell_groups=None):
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
    _shells = _resolve_shells(group_names, group_mat, shell_groups)
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_shells)
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

    # jitter: 격자 위상 평균으로 절대 σ 안정화. J² 오프셋.
    #   ⚠ 2026-07-30 정정 — 여기 오래 적혀 있던 '단일격자 ±1.5 dB → J=2 ±0.15 dB' 는 **측정 근거가 없는
    #     구전값**이다(어느 JSON 에도 그 짝이 없다). report07 §3 이 이 주석에서 그대로 베껴 손으로 적어
    #     두었다가, 같은 리포트 §4 가 JSON 에서 주입한 값과 어긋나 정정했다.
    #     측정된 것: outputs/report2_waveform_rcs.json 의 sbr_validation.dither — 구 r=0.5 m·3.5 GHz 에서
    #     격자 정렬(pad)만 흔든 **단일격자 산포**가 λ/16 에서 1.78 dB(peak-to-peak). J≥2 평균 뒤의 잔차는
    #     viz_report2.measure_sbr_validation() 이 spread_prod/avg_err_prod 로 기록하도록 바뀌었으나 아직
    #     그 JSON 이 재생성되지 않았다 → 숫자를 여기 적지 않는다. 인용은 JSON 키로만.
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


#  출사 가시성(shadow-ray) 자기교차 여유.
#  ⚠ **오프셋은 반드시 û_s 방향으로만 준다** — 측방으로 조금이라도 밀면 안 된다(반증 기록):
#    처음엔 o = P + eps·(û_s + n̂) 로 법선 성분을 섞었는데, 그러면 히트점이 출사선에서
#    ~eps 만큼 **옆으로** 밀린다. 오목한 이음매(팔뿌리가 동체에 파고든 곳)에서는 그 옆칸이
#    직각 벽이라 그림자광선이 곧바로 그 벽을 맞는다 → **모노스태틱(û_s=û_i)에서도 0 이 아닌**
#    가짜 가림이 생겼다(s1000plus 2875 히트 중 3~5 개, σ 로 −0.10 dB; mini5pro +0.16 dB).
#    û_s 방향으로만 밀면 원점이 출사선 **위에 그대로** 있으므로 그 인공물이 사라진다
#    (실측: 4기체 전부 β=0 에서 0.0000 dB, 즉 정확한 no-op).
#    대신 표면과의 간격이 t·(n̂·û_s) 이므로 grazing 에서 붕괴한다 → 간격이 EXIT_CLEARANCE 가
#    되도록 t 를 늘리되, 진짜 가림체를 건너뛰지 않게 (n̂·û_s) 를 EXIT_COSMIN 에서 자른다
#    (최대 전진거리 = EXIT_CLEARANCE/EXIT_COSMIN = 0.5 mm ≪ 광선격자 λ/16 ≈ 5.4 mm).
EXIT_CLEARANCE = 1e-5      # 표면에서 띄울 법선 여유 [m] (float32 좌표오차 ~6e-8 m 의 170배)
EXIT_COSMIN = 0.02         # (n̂·û_s) 하한 — 전진거리 폭주 방지


def _exit_visible(sc, P_abs, Nn, u_s, clearance=EXIT_CLEARANCE, cosmin=EXIT_COSMIN):
    """히트점에서 **수신기 방향 û_s 로 나가는 길이 뚫려 있는가**(그림자 광선 1발).

    Mitsuba `ray_test` 는 교차 '유무'만 보므로 ray_intersect 보다 싸다. 표적은 유한하니
    무한 광선으로 충분하다(û_s 로 나가서 아무것도 안 맞으면 수신기까지 자유공간)."""
    u_s = np.asarray(u_s, float)
    cs = np.maximum(np.asarray(Nn, float) @ u_s, cosmin)
    o = np.asarray(P_abs, float) + (clearance / cs)[:, None] * u_s[None, :]
    dd = np.tile(u_s, (o.shape[0], 1))
    ray = mi.Ray3f(o=mi.Point3f(*o.T.astype(np.float32)),
                   d=mi.Vector3f(*dd.T.astype(np.float32)))
    return ~np.asarray(sc.ray_test(ray)).astype(bool)


def rcs_sbr_multistatic(mesh: Mesh, group_mat: dict, fc: float, u_i, u_s_list,
                        spacing=None, pad=1.15, cache_key=None, penetrate=True, jitter=2,
                        shell_groups=None, exit_vis=True, symmetrize=False):
    """**바이스태틱/멀티스태틱** RCS σ(û_i,û_s)[m²].

    û_i = 표적→송신국, û_s = 표적→수신국 방향(둘 다 outward 단위벡터).
    일반 PO:  E ∝ Σ_hit |Γ| · e^{jk(û_i+û_s)·p} · d²,   σ = 4π/λ²|E|².
      · 조명면 판정 (n̂·û_i>0) — 광선을 û_i 로 쏘므로 dA_투영=d² 상쇄가 그대로 성립(추가 obliquity 없음).
      · 수신 가시 판정 (n̂·û_s>0) — û_s 로 되돌아가는 면만.
      · 모노스태틱은 û_s=û_i 특수해 → e^{j2k û·p} 로 rcs_sbr_batch 와 정확히 일치.

    **멀티스태틱 효율**: 조명(광선추적)은 û_i 로만 결정 → **한 번만** 쏘고, 각 û_s(∈u_s_list)에 대해
    싼 위상합 + 그림자광선 1발만 반복한다(Rx 를 늘려도 비싼 조명 추적은 재사용).
    u_s_list = [û_i] 면 모노(rcs_sbr_batch 와 0dB 일치).

    ■ exit_vis (기본 **True**) — **출사 가시성(bistatic exit visibility)**
      수신 게이트가 법선 판정 `n̂·û_s>0` 하나뿐이면 **수신기를 향한 면이 기체에 가려져 있어도**
      100% 진폭으로 계상된다. 입사경로 가림만 넣은 상태는 효과의 절반만 모형화한 것이다
      (우리 기체에서 입사 가림 하나가 −1.5~−3.1 dB). 그래서 히트점마다 û_s 로 그림자광선을
      1발 더 쏴서(같은 Mitsuba 씬 재사용, 새 씬 생성 없음) 실제로 수신기가 보이는 면만 남긴다.
      **모노스태틱(û_s=û_i)에는 필요 없다** — Sagitta(arXiv:2604.09243) 각주 1 이 같은 말을 한다:
        "A bistatic scattering calculation would require a visibility function to account for
         shadow regions between the reflection points and the final receiver. In a monostatic
         configuration this can be omitted, since the predominantly scattering surfaces are by
         assumption visible to the co-located launcher and receiver."
      우리 구현에서도 û_s=û_i 이면 first-hit 가 이미 그 가림을 뺐으므로 이 검사는 무해한 no-op 다
      (실측 0.000 dB). 끄려면 exit_vis=False.

    ■ symmetrize (기본 **False**, 옵트인) — σ_sym = √(σ(û_i,û_s)·σ(û_s,û_i))
      상반성(reciprocity)은 **정리**이므로 위반은 전부 모형오차다. 이 스위치는 두 상반기하를
      각각 평가해 기하평균을 돌려준다(조명 추적 1회 추가 비용). 결과적으로 σ_sym(i,s)=σ_sym(s,i)
      가 **구성상 정확히** 성립한다.
      ⚠ **정직 표기 — 이것은 오차를 "0 으로 만드는" 것이 아니라 대칭화일 뿐이다.** 두 평가값의
        dB 차이(=위반량)는 그대로 남아 있고, 참값이 어느 쪽인지에 대한 정보는 늘지 않는다.
        두 오차의 부호가 dB 에서 반대일 때만 최악오차가 절반으로 줄고, 같은 방향으로 틀려 있으면
        전혀 개선되지 않는다. 위반량 자체를 진단으로 남기려면 두 방향을 직접 호출해 비교할 것.
      ⚠ **혼동 금지 — 실패한 다른 시도와 다르다.** 예전에 시도한 것은 **obliquity 대칭화**
        (n̂·û_i) → √((n̂·û_i)(n̂·û_s)) 로, grazing 조명면(n̂·û_i→0)에서 √(cosθ_s/cosθ_i) 가
        이산 격자를 폭발시켜(단일 광선에 수백배 가중) **오히려 rms 오차를 키웠다** → 폐기.
        여기 것은 **출력 σ 레벨**의 기하평균이라 grazing 특이점이 없다.

    ⚠ **적용범위 한계(집중 적대검증으로 확인, 정직 표기):**
      (1) **전방산란 무효**: β→180°(û_s≈−û_i)에서 조명게이트(n̂·û_i>0)와 수신게이트(n̂·û_s>0)가
          상호배타 → σ≡0. lit-PO 는 그림자복사(Babinet 전방로브 σ_fwd=4πA²/λ²)를 못 낸다 →
          **후방~중간 바이스태틱각(β≲90°급, 조명면 일부가 여전히 Rx 가시)에만 유효.**
      (2) **상반성 부분성립**: σ(û_i,û_s)=σ(û_s,û_i)가 볼록·강반사에선 성립(구 ~0.2dB)하나
          **비볼록 표적에서는 β≤90° 안에서도 깨진다**(û_i 단일조명격자 재사용의 구조적 대가,
          격자세분으로 안 줄어듦). 실측치는 outputs/sbr_defect_fixes.json 의 `reciprocity` 참조.
          필요하면 symmetrize=True.
      (3) 투과 출사경로(û_s 로 셸 재통과)는 입사 τ 로 근사(1차 투과) → 바이스태틱 비대칭을 더 키움.
      (4) obliquity 는 표준 PO 의 (n̂·û_i) 를 그대로 쓴다(위 symmetrize 경고 참조)."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV
    u_i = np.asarray(u_i, float); u_i = u_i / np.linalg.norm(u_i)
    U_s = np.atleast_2d(np.asarray(u_s_list, float))
    U_s = U_s / np.linalg.norm(U_s, axis=1, keepdims=True)

    scene, shapes, gammas = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    _shells = _resolve_shells(group_names, group_mat, shell_groups)
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_shells)
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
        #   → 표준 (n̂·û_i) 유지. 상반성이 필요하면 symmetrize=True (σ 레벨 기하평균).
        for j, u_s in enumerate(U_s):
            lit = lit_i & ((Nn @ u_s) > 1e-6)   # + û_s 수신 게이트(법선)
            if exit_vis:                        # + û_s 로 나가는 길이 실제로 뚫려 있는가
                sel = np.where(lit)[0]
                if sel.size:
                    lit = lit.copy()
                    lit[sel] = _exit_visible(scene, Pc[sel] + ctr, Nn[sel], u_s)
            E = np.sum(np.where(lit, g, 0.0) * np.exp(1j * k * (Pc @ (u_i + u_s))))
            if do_pen:
                litp = lit2_i & ((Nn2 @ u_s) > 1e-6) & (tau > 0)
                if exit_vis:
                    #  투과 기여의 출사도 **셸을 뺀 내부 씬**으로 판정한다 — 입사 처리와 같은 전제
                    #  (셸은 투과 대상이므로 가림체가 아니고, 내부 금속끼리의 가림만 본다).
                    sel = np.where(litp)[0]
                    if sel.size:
                        litp = litp.copy()
                        litp[sel] = _exit_visible(scene_i, Pc2[sel] + ctr, Nn2[sel], u_s)
                E = E + np.sum(np.where(litp, tau * g2, 0.0) * np.exp(1j * k * (Pc2 @ (u_i + u_s))))
            sig_acc[j] += (4.0 * np.pi / lam ** 2) * np.abs(E * d * d) ** 2
    sig = sig_acc / len(offsets)

    if symmetrize:
        #  σ_sym = √(σ(i,s)·σ(s,i)) — 상반기하를 한 번 더 평가한다(조명 추적 1회 추가/Rx).
        rev = np.empty(len(U_s))
        for j, u_s in enumerate(U_s):
            rev[j] = float(np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, group_mat, fc, u_s, [u_i], spacing=spacing, pad=pad, cache_key=cache_key,
                penetrate=penetrate, jitter=jitter, shell_groups=shell_groups,
                exit_vis=exit_vis, symmetrize=False), float))[0])
        sig = np.sqrt(sig * rev)

    return sig if len(U_s) > 1 else float(sig[0])


def sbr_field(mesh: Mesh, group_mat: dict, fc: float, u, spacing=None, pad=1.15,
              cache_key=None, penetrate=True, shell_groups=None):
    """**복소 산란장 E(û)** 를 돌려준다 (σ 가 아니라 E — 마이크로도플러는 위상이 필요하다).

        E(û) = Σ_hits |Γ_i| · e^{j2k p_i·û} · d²          σ = (4π/λ²)|E|²

    û 는 표적 → 레이더 방향 단위벡터. penetrate=True 면 rcs_sbr_batch 와 동일하게 유전체 셸을
    투과시켜 내부 금속을 τ=1−|Γ|² 로 코히런트 가산(헤드라인과 일관)."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV
    u = np.asarray(u, float); u = u / np.linalg.norm(u)

    scene, shapes, gammas = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    _shells = _resolve_shells(group_names, group_mat, shell_groups)
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_shells)
        shptr_i = [mi.ShapePtr(s) for s in shapes_i]

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

    def _field(sc, shptr, gam):
        si = sc.ray_intersect(ray)
        valid = np.asarray(si.is_valid()).astype(bool)
        P = np.asarray(mi.Point3f(si.p)).T
        Nn = np.asarray(mi.Vector3f(si.n)).T
        g = np.zeros(P.shape[0])
        for sp, gm in zip(shptr, gam):
            g = np.where(np.asarray(si.shape == sp).astype(bool), gm, g)
        sgn = np.sign(Nn @ u); sgn[sgn == 0] = 1.0        # 법선을 광선 오는 쪽(û)으로 정렬
        Nn = Nn * sgn[:, None]
        lit = valid & ((Nn @ u) > 1e-6)
        return valid, lit, g, np.exp(1j * 2.0 * k * ((P - ctr) @ u)), si

    valid, lit, g, phase, si = _field(scene, shape_ptrs, gammas)
    E = np.sum(np.where(lit, g, 0.0) * phase)
    if do_pen:
        tau = np.zeros(valid.shape[0])
        for i in shell_pos:
            tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                           1.0 - gammas[i] ** 2, tau)
        _, lit2, g2, phase2, _ = _field(scene_i, shptr_i, gammas_i)
        E = E + np.sum(np.where(lit2 & (tau > 0), tau * g2, 0.0) * phase2)
    return complex(E) * d * d


def rcs_sbr(mesh: Mesh, group_mat: dict, fc: float, az_deg, el_deg=0.0,
            spacing=None, max_bounce=1, pad=1.15, return_hits=False):
    """SBR 로 **모노스태틱 RCS σ[m²]** 를 낸다. az_deg 는 스칼라 또는 배열.

      mesh      : geom.Mesh (표적)
      group_mat : 그룹 → 재질키(str, materials.MATERIALS) 또는 |Γ|(float)
      spacing   : 광선 격자 간격 [m]. 기본 λ/DEFAULT_DIV(현재 λ/12).
      max_bounce: 1 = 1차 PO(=기존 PO 와 동급, 단 가림 포함).
                  ≥2 = 반사 후 재추적 → **오목부(로터 아래·짐벌 그늘) 다중반사** 반영.
                  ⚠ ≥2 의 위상은 PEC 직각 이면반사체 해석해 8πa²b²/λ² 로 검증한다
                    (`validate()` [3]). 구·평판은 볼록이라 이 경로를 **전혀 못 밟는다**.
      pad       : 광선 격자를 표적 투영 bbox 대비 얼마나 넓게 (여유)

    ⚠ ≥2-bounce 의 **출사 가시성**은 검사하지 않는다 — 마지막 충돌점에서 û 로 나가는 길이
      막혀 있어도 계상된다. 1-bounce 는 first-hit 이 이미 그 가림을 뺐으므로 무관하고
      (Sagitta arXiv:2604.09243 각주 1), 생산 σ 는 전부 1-bounce 다. 바이스태틱 출사 가시성은
      `rcs_sbr_multistatic(exit_vis=True)` 에 구현되어 있다.

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
        amp = np.ones(O.shape[0])                 # 다중반사 시 누적 반사계수 Π|Γ|
        path = np.zeros(O.shape[0])               # **발사면부터** 직전 상호작용점까지의 누적 광로
        Pprev = O.copy()                          # 직전 상호작용점(첫 bounce 는 발사점 그 자체)
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
            #
            #  위상 규약(bounce 수와 무관한 일반형):
            #      φ = −k·(R_fwd − R_out) + k·(û_s·p′),      p′ = p − ctr
            #    R_fwd = **발사면에서 이 충돌점까지 광선이 실제로 지나온 거리**(도착 세그먼트 포함),
            #    R_out 은 발사면이 ctr 에서 떨어진 거리(모든 광선 공통 상수라 σ 에 무영향, 감산은
            #    float 안정용). 유도: 입사 평면파의 위상은 e^{jk û_i·x} 이고 GO 광선을 따라
            #    e^{−jk s} 로 진행하므로 충돌점의 입사위상 = const·e^{−jk R_fwd}, 거기서 û_s 로
            #    복사하면 e^{+jk û_s·p} 가 곱해진다.
            #  검산 ① 1-bounce 모노: R_fwd = R_out − û·p′ 이므로 φ = +2k(û·p′) — 옛 식과 **동일**.
            #  검산 ② 1-bounce 바이: φ = k(û_i+û_s)·p′ (rcs_sbr_multistatic 와 같은 형).
            #  검산 ③ 90° 이면반사체: R_fwd − û·p′ 가 개구 전체에서 **상수** → 코히런트 플래시.
            #
            #  ⚠ **반증 기록(2026-07-30)** — 여기 있던 식은 `exp(j2k(r·û − ½·path))` 였고
            #    `path` 는 기여를 계산한 **뒤에** 갱신되어(아래 ②) **도착 세그먼트가 빠진 값**이었다.
            #    1-bounce 에서는 path=0 이라 정확했으므로 생산 σ(전부 1-bounce)는 이 정정에
            #    영향받지 않는다. 그러나 ≥2-bounce 는 틀렸고, PEC 이면반사체(a=b=0.3 m·3.5 GHz)에서
            #    해석해 8πa²b²/λ² = +14.43 dBsm 에 대해 **−12.02 dBsm(−26.5 dB)** 을 냈다.
            #    "다중반사는 사소하다" 는 결론이 그 고장난 커널에서 나온 순환논법이었다.
            #  ⚠ **남은 근사(정직 표기)**: ≥2-bounce 의 PO 진폭에는 원래 obliquity 비
            #    (n̂·û_s)/(n̂·(−d̂_in)) 이 붙어야 하는데 여기서는 1 로 둔다. 마지막 반사가
            #    역반사(retro)면 두 각이 같아 정확하고(이면반사체 이등분선 입사가 그 경우),
            #    일반 각에서는 근사다. 이 비를 넣으려면 1/(n̂·d̂_in) 이 grazing 에서 폭발하는
            #    문제를 먼저 풀어야 한다(같은 이유로 실패한 시도는 rcs_sbr_multistatic 참조).
            cosr = Nh @ u
            lit = cosr > 1e-6
            seg = np.linalg.norm(Ph - Pprev[hit], axis=1)     # 직전 상호작용점 → 이 충돌점
            R_fwd = path[hit] + seg                           # 발사면 → 이 충돌점(도착분 포함)
            if lit.any():
                r_dot = (Ph[lit] - ctr) @ u        # 중심감산(float32 안정·σ 불변)
                phase = np.exp(-1j * k * (R_fwd[lit] - Rout - r_dot))
                E += np.sum(amp[hit][lit] * gh[lit] * phase) * d * d
                n_hit_total += int(lit.sum())

            if b + 1 >= max_bounce:
                break
            # ② 정반사 후 재추적 (오목부 다중반사)
            #   ⚠ 반증 기록 두 겹 — 이 자리는 두 번 틀렸다.
            #     (1) 2026-07-16 이전: 누적경로를 `* 0` 으로 죽여 2차+ 경로길이가 위상에 아예
            #         안 들어갔다.
            #     (2) 2026-07-16~07-30: 경로를 누적하기는 했으나 **기여 계산 뒤에** 더해서
            #         도착 세그먼트가 빠졌고, 게다가 `−½·path` 라는 반쪽 계수를 썼다(위 ① 참조).
            #   이제 R_fwd = path + seg 를 **기여에 쓰기 전에** 만든다.
            #   ⚠ 광로는 `Ocur`(1e-4 만큼 밀어낸 재추적 시작점)이 아니라 **직전 충돌점 Pprev**
            #     에서 잰다 — 그 오프셋만큼(0.1 mm) 광로가 짧아지는 계통오차를 없앤다.
            Dh = Dcur[hit]
            Dref = Dh - 2.0 * np.einsum("ij,ij->i", Dh, Nh)[:, None] * Nh
            newO = Ph + 1e-4 * Dref
            alive2 = np.zeros(O.shape[0], bool); alive2[hit] = True
            Ocur[hit] = newO; Dcur[hit] = Dref
            amp[hit] = amp[hit] * gh
            path[hit] = R_fwd                                     # 누적 경로길이(다음 bounce 용)
            Pprev[hit] = Ph
            alive = alive2

        sig[i] = (4.0 * np.pi / lam ** 2) * abs(E) ** 2
        diag.append(dict(az=float(az), n_rays=int(O.shape[0]), n_hits=n_hit_total,
                         spacing=d, rays_per_lambda=lam / d))

    out = sig if len(az_list) > 1 else float(sig[0])
    return (out, diag) if return_hits else out


# --------------------------------------------------------------------------- #
#  검증 — 기준해가 있는 표적
# --------------------------------------------------------------------------- #
#  검증용 PEC — **재질 문자열이 아니라 |Γ| 실수 1.0**.
#  ⚠ 'pec' 라는 재질 키는 존재하지 않는다. 예전엔 그 문자열을 넘기면 materials 가 조용히
#    plastic 으로 흘러 |Γ|=0.2437(−12.26 dB)을 돌려줬다 → 이제 materials._spec() 이 예외를 던진다.
#  ⚠ "metal" 도 여기선 쓰지 않는다 — ITU metal 은 |Γ|=0.99980 이라 기준해(전부 PEC 전제)와
#    0.0017 dB 어긋난다. 검증에서는 기준해의 전제를 **정확히** 재현한다.
#  (키 "metal" 은 재질이 아니라 uv_sphere/box 가 붙인 **그룹 이름**이다.)
_PEC_GROUP_MAT = {"metal": 1.0}


def dihedral_mesh(a, b=None, group="metal"):
    """**직각 이면반사체(dihedral corner reflector)** — 다중반사 위상의 유일한 해석 과녁.

    판 ①  z=0,  x∈[0,a], y∈[0,b]      판 ②  x=0,  z∈[0,a], y∈[0,b]
    이등분선 입사(az=0°, el=45° → û=(1,0,1)/√2)에서 **개구 전체가 2회 반사**로 정확히
    역방향(+û)으로 돌아오므로, 유효개구 √2·a·b 의 평판과 같아진다:

        σ_max = 4π(√2ab)²/λ² = **8π a²b²/λ²**   (b=None 이면 b=a → 8πa⁴/λ²)

    왜 이 표적인가: 구·평판은 **볼록**이라 1-bounce 로 끝나서 다중반사 위상을 **전혀 진단하지
    못한다**. 이면반사체는 (i) 해석해가 닫힌형이고 (ii) 답이 **2-bounce 위상이 개구 전체에서
    상수인가** 하나에만 달려 있어, 위상이 조금만 틀려도 즉시 수십 dB 로 무너진다."""
    from geom import Mesh, quad
    b = a if b is None else b
    m = Mesh(group)
    m.merge(quad((0, 0, 0), (a, 0, 0), (a, b, 0), (0, b, 0), group=group))
    m.merge(quad((0, 0, 0), (0, b, 0), (0, b, a), (0, 0, a), group=group))
    return m


def dihedral_exact_sigma(a, b=None, fc=3.5e9):
    """이면반사체 이등분선 최대 RCS 해석해 σ = 8πa²b²/λ² [m²]."""
    b = a if b is None else b
    lam = C0 / float(fc)
    return 8.0 * np.pi * (a * b) ** 2 / lam ** 2


def validate(fc=3.5e9, verbose=True):
    """구 · 평판(σ=4πA²/λ²) · **이면반사체(σ=8πa²b²/λ²)** 로 SBR 커널을 검증한다.

    ⚠ 2026-07-30 정정 — **구의 기준해는 두 개이고, πr² 은 그 중 하나도 아니다**.
      예전엔 `exact = πr²` 라 쓰고 그 잔차를 "오차" 로 적었는데, πr² 은 ka→∞ **광학 점근값**일
      뿐이다. r=0.5 m·3.5 GHz(kr=36.677)에서 πr² 은 두 기준해 **사이**에 있다 —
      해석 PO 가 +0.1065 dB 위, 정확 Mie 가 0.0451 dB 아래(둘 사이 0.152 dB). 생산 커널의 구
      잔차가 그 간극보다 **작아서**, 옛 숫자는 과녁을 고르는 임의성에 지배됐다. 이제 둘 다 적는다:
        · **해석 PO** = 커널이 SBR+**PO** 이므로 수치 수렴이 향하는 과녁(우리 수치오차의 자)
        · **정확 Mie** = 물리적 참값(PO 근사를 쓴 대가까지 포함한 절대 정확도의 자)
        · πr² 은 `_go` 접미사로 **라벨된 점근값**만 남긴다(합격 판정에 쓰지 않는다).
      기준해 구현은 `benchmark/mie_pec_sphere.sphere_reference_set` 한 곳뿐이다.
      ⚠ **평판은 그대로다** — 정면입사 4πA²/λ² 는 점근이 아니라 PO 의 정확한 답이다.

    ⚠ 2026-07-29 정정 — **생산 커널로 검증한다**: `rcs_sbr_batch(jitter=3, penetrate=False)`.
      예전엔 이 함수가 `rcs_sbr()`(단일격자·jitter 인자 없음)을 불렀다. 그런데 프로젝트의 드론 σ 는
      **전부** `rcs_sbr_batch(..., jitter≥2)` 에서 나온다 → 유일한 정확도 검증이 **아무 결과도 쓰지 않는
      경로**를 재고 있었고, 생산 경로가 서브셀 오프셋 평균으로 지우는 격자위상 편향을 그대로 안고 있었다.
      · 구·평판은 **볼록(convex)** 이라 배치 커널의 max_bounce=1 제한이 **정확**하다 —
        오목부가 없어 2차 반사가 표적으로 되돌아오는 경로 자체가 존재하지 않는다.
      · penetrate=False: 유전체 셸 그룹이 없어 어차피 무영향이지만, 검증은 명시한다.
      · 드론 생산 호출은 jitter=2(기본)이고 여기선 3(J²=9 오프셋) — **같은 코드경로, 더 촘촘한 평균**이다.

    ⚠ 2026-07-30 추가 — **[3] 이면반사체는 다중반사 경로에만 걸리는 게이트다**.
      [1] 구·[2] 평판은 볼록이라 `max_bounce` 를 아무 값으로 두어도 1-bounce 로 끝난다 →
      다중반사 위상이 아무리 틀려도 **검증이 통과한다**. 실제로 그런 일이 있었다(위상식에서
      도착 세그먼트가 빠져 이면반사체가 해석해보다 26.5 dB 낮았는데 구·평판은 멀쩡했다).
      그래서 오목 표적을 상설 케이스로 넣는다. 이 케이스만 `rcs_sbr(max_bounce=2)` 를 쓴다
      (배치 커널은 1-bounce 전용).
    """
    from geom import uv_sphere, box
    #  기준해는 **한 곳에서만** 온다(생산자별 재구현 금지) — benchmark/ 를 path 에 넣는다.
    _bench = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
    if _bench not in sys.path:
        sys.path.insert(0, _bench)
    from mie_pec_sphere import sphere_reference_set
    lam = C0 / fc
    res = {}

    if verbose:
        print("=" * 82)
        print(f"SBR 검증 @ {fc/1e9:.1f} GHz (λ={lam*100:.2f} cm) "
              f"— 생산 커널 rcs_sbr_batch(jitter=3, penetrate=False), |Γ|=1.0(PEC)")
        print("=" * 82)

    # --- 금속구: 기준해 둘(해석 PO = 커널의 과녁, 정확 Mie = 참값). πr² 은 점근 참고값. ---
    r = 0.5
    sph = uv_sphere(r, seg=180, rings=90, group="metal")
    REF = sphere_reference_set(r, fc)
    res["sphere_ref"] = REF
    if verbose:
        print(f"\n[1] 금속구 r={r} m  (r/λ={r/lam:.1f}, kr={REF['kr']:.3f})")
        print(f"    기준해  해석 PO {REF['po_dbsm']:+.3f} dBsm (커널의 과녁) · "
              f"정확 Mie {REF['mie_dbsm']:+.3f} dBsm (참값)")
        print(f"    참고    광학 점근 πr² {REF['go_dbsm']:+.3f} dBsm — **과녁 아님** "
              f"(PO {REF['po_minus_go_db']:+.3f} / Mie {REF['mie_minus_go_db']:+.3f} dB 떨어져 있다)")
        print(f"    {'격자 d':>10} {'λ/d':>6} {'광선수/오프셋':>10} {'σ_SBR':>10} "
              f"{'vs PO':>8} {'vs Mie':>8} {'vs πr²':>8}")
    for div in (4, 6, 10, 16):
        d = lam / div
        s = rcs_sbr_batch(sph, _PEC_GROUP_MAT, fc, az_deg=0.0, el_deg=0.0, spacing=d,
                          jitter=3, penetrate=False)
        e_po = 10 * np.log10(s / REF["po_sigma_m2"])
        e_mie = 10 * np.log10(s / REF["mie_sigma_m2"])
        e_go = 10 * np.log10(s / REF["go_sigma_m2"])
        res[f"sphere_lam/{div}_vs_po"] = e_po
        res[f"sphere_lam/{div}_vs_mie"] = e_mie
        res[f"sphere_lam/{div}_vs_go"] = e_go
        if verbose:
            n = int(np.ceil(2 * (r * 1.15 + 3 * d) / d)) ** 2
            print(f"    {d*1000:9.2f}mm {div:6d} {n:10,d} {10*np.log10(s):+9.3f} "
                  f"{e_po:+8.3f} {e_mie:+8.3f} {e_go:+8.3f}")

    # --- 금속 평판(정면): σ = 4πA²/λ² — 점근값이 아니라 **PO 의 정확한 답**이다 ---
    a = 0.4
    plate = box(a, a, 0.002, group="metal")
    exact_p = 4 * np.pi * (a * a) ** 2 / lam ** 2
    if verbose:
        print(f"\n[2] 금속 평판 {a}×{a} m (정면)   정확 PO σ=4πA²/λ²={10*np.log10(exact_p):+.2f} dBsm")
        print(f"    {'격자 d':>10} {'λ/d':>6} {'σ_SBR':>10} {'오차':>8}")
    for div in (4, 6, 10):
        d = lam / div
        s = rcs_sbr_batch(plate, _PEC_GROUP_MAT, fc, az_deg=0.0, el_deg=90.0, spacing=d,
                          jitter=3, penetrate=False)
        err = 10 * np.log10(s / exact_p)
        res[f"plate_lam/{div}"] = err
        if verbose:
            print(f"    {d*1000:9.2f}mm {div:6d} {10*np.log10(s):+9.2f} {err:+7.2f} dB")

    # --- 직각 이면반사체(오목): σ = 8πa²b²/λ² — **다중반사 위상**의 유일한 해석 과녁 ---
    #     1-bounce 열은 참고용이다(단일반사만으로는 이 표적을 못 낸다 → 크게 낮은 것이 정상).
    if verbose:
        print(f"\n[3] PEC 직각 이면반사체(이등분선 입사 el=45°)   해석해 σ=8πa²b²/λ²")
        print(f"    {'a=b [m]':>8} {'해석해':>10} {'SBR 1-bnc':>10} {'SBR 2-bnc':>10} {'2-bnc 오차':>10}")
    for a in (0.15, 0.20, 0.30, 0.40):
        dm = dihedral_mesh(a)
        ex = dihedral_exact_sigma(a, fc=fc)
        s1 = float(rcs_sbr(dm, _PEC_GROUP_MAT, fc, az_deg=0.0, el_deg=45.0,
                           spacing=lam / DEFAULT_DIV, max_bounce=1))
        s2 = float(rcs_sbr(dm, _PEC_GROUP_MAT, fc, az_deg=0.0, el_deg=45.0,
                           spacing=lam / DEFAULT_DIV, max_bounce=2))
        err2 = 10 * np.log10(s2 / ex)
        res[f"dihedral_a{a}_exact_dbsm"] = float(10 * np.log10(ex))
        res[f"dihedral_a{a}_b1_dbsm"] = float(10 * np.log10(max(s1, 1e-30)))
        res[f"dihedral_a{a}_b2_dbsm"] = float(10 * np.log10(s2))
        res[f"dihedral_a{a}_b2_err_db"] = float(err2)
        if verbose:
            print(f"    {a:8.2f} {10*np.log10(ex):+10.3f} {10*np.log10(max(s1,1e-30)):+10.3f} "
                  f"{10*np.log10(s2):+10.3f} {err2:+9.3f} dB")
    if verbose:
        print("    (잔차는 이등분선에서 상쇄가 덜 된 1-bounce 성분의 코히런트 가산 — a 가 커질수록"
              " 2-bounce σ∝a⁴ 가 1-bounce σ∝a²/k² 를 압도해 줄어든다.)")
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
