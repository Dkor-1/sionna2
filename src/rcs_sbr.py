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
import time
from typing import NamedTuple

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

# ─────────────────────────────────────────────────────────────────────────── #
#  ⭐ 각도의존 반사계수 스위치 (2026-08-07)
# ─────────────────────────────────────────────────────────────────────────── #
#  옛 커널은 재질마다 **수직입사 |Γ| 하나**를 모든 입사각에 썼다. 실제 프레넬은 각도에 따라
#  커진다 — 3.5 GHz 에서 플라스틱이 75°에 +6.67 dB, 85°에 +10.22 dB (전력평균 TE·TM).
#  ⭐ 프로펠러가 그 플라스틱이고 도는 날개는 큰 입사각을 오래 본다 → 마이크로도플러가 정면으로 영향.
#  (선행 확인: 선배 홍지혁 PO 커널은 `fresnel_te_vec(cos_i, …)` 로 각도를 받는다.)
#
#  ⚠ False 로 두면 이 인자가 없던 때와 **비트 단위로 같다**. 회귀 검사를 그렇게 한다.
ANGLE_GAMMA = bool(int(os.environ.get("SIONNA2_ANGLE_GAMMA", "1")))

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

    shapes_d, gammas, mat_keys = {}, [], []
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
        mat_keys.append(val if isinstance(val, str) else None)   # ⭐각도 모양용 재질 키
    scene = mi.load_dict({"type": "scene", **shapes_d})
    return scene, list(scene.shapes()), np.asarray(gammas, float), list(mat_keys)


def _look(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], float)


# --------------------------------------------------------------------------- #
#  SBR — 모노스태틱 후방산란 RCS
# --------------------------------------------------------------------------- #
_SCENE_CACHE: dict = {}


def _scene_for(mesh: Mesh, group_mat: dict, key=None, fc: float = 3.5e9, exclude=()):
    # 반환은 (scene, shapes, gammas, mat_keys) 4-튜플이다 — mat_keys 는 각도의존 Γ 용.
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
                  shell_groups=None, ptd=False, ptd_pol="V", ptd_opts=None):
    """**방위각 전체를 한 배치로** GPU 에 올려 1-bounce SBR σ 를 낸다 (가림 포함).

    왜 배치인가: 방위각 하나당 Mitsuba 호출을 따로 하면 커널 실행 오버헤드가 지배한다.
    광선 격자 여러 방위를 **하나의 큰 광선 다발**로 합쳐 쏘면 GPU 를 제대로 쓴다.

    penetrate=True 면 **유전체 셸(_DIELECTRIC_SHELLS)을 통과시켜 내부 금속(배터리/PCB)**을
    왕복 투과 진폭 τ=1−|Γ_shell|² 로 가중해 외부 기여와 **코히런트 합산**한다 — first-hit 가
    내부를 삭제하는 자기모순(직접 검증: battery/pcb 0 히트)을 없앤다. 셸 없는 표적(구·평판)엔 무영향.
    ⚠ 근사: 얇은 셸의 굴절(광로 굴곡)·유전체 내 위상지연은 무시(1차 투과·기하위상만).

    ptd (기본 **False**) : True 면 모서리 프린지 항 A_FW 를 **코히어런트로** 더한다
      (σ = 4π/λ²|E_면적분 + A_FW|²). 규약·게이트·근사는 위 「PTD 배선」 절 참조.
      ptd_pol : 프린지 항의 편파("V"/"H"). 면적분은 스칼라라 편파가 없다 → PO 는 두 편파에 공통.
      ptd_opts : dict. occlusion(기본 True) 및 extract_edges/edge_field 로 넘길 키.
      ⚠ **ptd=False 는 이 인자들이 없던 때와 비트 단위로 같은 값을 낸다**(outputs/ptd_wiring.json).

    다중반사가 필요하면 rcs_sbr(..., max_bounce≥2) 를 쓸 것 (배치 안 함)."""
    from gpu import budget_mb
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV

    scene, shapes, gammas, matk = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]

    # 유전체 셸 투과 준비 — 셸 shape 위치(=그룹 정렬순) + 셸 제거한 '내부 씬'
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    _shells = _resolve_shells(group_names, group_mat, shell_groups)
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i, matk_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_shells)
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

    def _lit_g_phase(si, shptr, gam, D, U, _mk=None):
        """히트 → (lit 마스크, g[|Γ|], 위상, valid). 외부/내부 패스 공통."""
        valid = np.asarray(si.is_valid()).astype(bool)
        P = np.asarray(mi.Point3f(si.p)).T
        Nn = np.asarray(mi.Vector3f(si.n)).T
        g = np.zeros(P.shape[0])
        which = np.full(P.shape[0], -1, int)
        for _i, (sp, gm) in enumerate(zip(shptr, gam)):
            hit = np.asarray(si.shape == sp).astype(bool)
            g = np.where(hit, gm, g)
            which = np.where(hit, _i, which)
        sgn = np.sign(np.einsum("ij,ij->i", Nn, -D)); sgn[sgn == 0] = 1.0
        Nn = Nn * sgn[:, None]
        cos_i = np.einsum("ij,ij->i", Nn, U)                     # ⭐국소 입사 코사인
        lit = valid & (cos_i > 1e-6)                             # 조명·수신 게이트
        # ⭐ 각도의존 Γ (2026-08-07) — 수직입사 보정값은 그대로 두고 **상대 각도 모양**만 곱한다.
        #   ANGLE_GAMMA=False 면 이 블록을 건너뛰어 예전과 비트 동일하다.
        if ANGLE_GAMMA and _mk is not None:
            from materials import gamma_shape as _gsh
            for _i, _key in enumerate(_mk):
                if _key is None:                                  # float 로 넘어온 재질은 상수
                    continue
                sel = (which == _i) & lit
                if sel.any():
                    g[sel] = g[sel] * _gsh(_key, fc, cos_i[sel])
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

    #  모서리 프린지 항 — 방위각마다 1 개(격자 오프셋에 무관하므로 jitter 루프 **밖**에서 한 번).
    if ptd:
        _ptd_spacing_warn(d, lam, "rcs_sbr_batch")
        _u = [_look(a, el_deg) for a in az]
        A_ptd = _ptd_edge_A(mesh, group_mat, fc, [(u, u) for u in _u], ctr, scene,
                            pol=ptd_pol, cache_key=cache_key, opts=ptd_opts)[0]

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
            lit, g, phase, valid, si = _lit_g_phase(si, shape_ptrs, gammas, D, U, matk)
            contrib = np.where(lit, g, 0.0) * phase

            # ── 유전체 셸 투과: 셸 맞은 광선만 내부 금속을 τ 가중 코히런트 가산 ──
            if do_pen:
                tau = np.zeros(valid.shape[0])                    # 왕복 투과 진폭(셸 아니면 0)
                for i in shell_pos:
                    tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                                   1.0 - gammas[i] ** 2, tau)
                si2 = scene_i.ray_intersect(ray)
                lit2, g2, phase2, _, _ = _lit_g_phase(si2, shptr_i, gammas_i, D, U, matk_i)
                contrib = contrib + np.where(lit2 & (tau > 0), tau * g2, 0.0) * phase2

            E = np.zeros(len(sub), complex)
            np.add.at(E, aidx, contrib)
            Etot = E * d * d                                  # 면적분 [m²]
            if ptd:
                Etot = Etot + A_ptd[s0:s0 + len(sub)]         # + 모서리 프린지 [m²]
            sig_acc += (4.0 * np.pi / lam ** 2) * np.abs(Etot) ** 2
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


# --------------------------------------------------------------------------- #
#  PTD (모서리 프린지) 배선 — **기본 꺼짐**. ptd=False 경로는 한 줄도 달라지지 않는다.
# --------------------------------------------------------------------------- #
#  PO/SBR 면적분이 세는 것은 균일전류 J⁰ 뿐이다. Ufimtsev 의 비균일(프린지) 전류 J¹ = J − J⁰
#  는 모서리 근방에만 살아 있고 통째로 빠져 있다 → `src/ptd_edges.py` 가 그 항 A_FW [m²] 를
#  낸다. 여기서 하는 일은 **배선뿐**이다: 같은 위상원점·같은 단위·같은 게이트로 코히어런트 가산.
#
#      σ = (4π/λ²) |E_면적분 + A_FW|²          (ptd=True 일 때만)
#
#  ■ 위상 규약 일치 — 이게 배선의 전부다
#      면적분 : e^{+j k (û_i+û_s)·(P − ctr)},   ctr = 면적분이 실제로 쓴 격자 중심
#               (grid_ref 없으면 0.5·(V.max+V.min), 얼린 격자면 grid_ref.ctr)
#      모서리 : e^{+j k q·(R_c − ctr)},         q = û_i + û_s            [ptd_edges.edge_field]
#    → 모서리항 원점은 **면적분이 실제로 쓴 ctr 그 자체**를 넘긴다(2026-08-14 수리) —
#      코히어런트 합의 물리 요건은 「두 항의 원점이 같다」 하나뿐이고, 같은 변수를 넘기므로
#      구성으로 보장된다. 원점·부호·계수(모노에서 2k)가 전부 같다. 모노스태틱 특수화도
#      정확히 겹친다: q=2û → e^{+j2k û·(R_c−ctr)} ↔ 면적분 e^{+j2k û·(P−ctr)}.
#    → 배선검사(D-10): `ptd_edges.sbr_phase_origin(mesh)` 이 원점을 **메쉬에서 독립 유도**하고,
#      `_ptd_edge_A()` 가 얼리지 않은 경로(frozen=False)에서 ctr 와 대조해 어긋나면 예외를
#      던진다(같은 식이라 정상이면 비트 0). **얼린 경로(frozen=True)** 는 ctr 가 자세 합집합
#      bbox 의 얼린 중심이라 현재 자세 bbox 중심과 로터 흔들림만큼(cm 단위) 정당하게 다르다
#      → 대조 대신 편차를 진단 메타로 기록하고, 격자가 자세를 덮는지는 상류 GRID_REF_CHECK
#      가 검사한다. ⚠2026-08-14 이전에는 모서리항이 org(자세 bbox 중심)를 원점으로 쓰고
#      frozen 구분 없이 대조했다 — 얼린 격자 + 로터 자세에서 편차 0.004~0.026 m 로 λ/1000 을
#      306 배 초과해 ptd=True 가 아예 돌지 않았다(elevation_sweep_md --ptd 재현).
#    → 단위도 같다: 면적분 Σ|Γ|e^{jφ}·d² [m²], 모서리항도 [m²].
#
#  ■ 게이트 일치
#    · 조명: 면적분은 first-hit + (n̂·û_i > 1e-6). 모서리는 edge_field 안에서 **인접면 중
#      하나라도 lit**(n̂₁·û_i>0 또는 n̂₂·û_i>0)이면 후보다 — 같은 규칙이고 문턱만 1e-6 ↔ 0 이다
#      (그 사이 구간은 grazing 극한). 양쪽 lit / 한쪽 lit 은 Michaeli 단위계단이 자동 처리한다.
#    · 가림: 면적분은 입사쪽을 first-hit 으로, 출사쪽을 `_exit_visible()` 로 끊는다. ptd_edges
#      기본값은 **가림 없음**(모듈 미구현 목록)이라 그대로 두면 몸통 뒤 모서리까지 계상된다
#      → 여기서 **같은 Mitsuba 씬**에 그림자광선을 쏘는 visible_fn 을 만들어 넣는다
#      (입사 û_i · 출사 û_s 양쪽. 모노스태틱은 û_s=û_i 라 1 발). ptd_opts={"occlusion": False}
#      로 끌 수 있다(진단용).
#
#  ■ 남는 근사 (정직 표기)
#    · 투과(penetrate) 기여에는 모서리항을 **붙이지 않는다** — 셸 안쪽 금속 모서리는 위 가림
#      판정(외부 씬)에서 대부분 떨어진다. 프린지 계수가 PEC 유도이고(metal_only) 셸 통과
#      투과계수를 프린지에 곱하는 근거가 없어서 값을 지어내지 않는다.
#    · ptd_edges 자체의 미구현(TW 절단·2 차 회절·코너)은 그대로 남는다. 그 목록은
#      ptd_edges.NOT_IMPLEMENTED / APPROXIMATIONS 에 있고 진단 메타로 실려 나온다.
#
#  모서리점은 표면 **위에** 정확히 놓여 있어 그림자광선이 자기 면을 맞을 수 있다 → 광선을
#  û 로만 밀어낸다(측방 오프셋이 만드는 가짜 가림은 `_exit_visible` 주석의 반증기록 참조).
#  전진거리는 면적분이 허용하는 **최대 전진거리와 같은 값** EXIT_CLEARANCE/EXIT_COSMIN
#  = 0.5 mm 로 고정한다 — 광선격자(λ/12 ≈ 7 mm)보다 훨씬 작아 진짜 가림체를 건너뛰지 않고,
#  (n̂·û) ≥ EXIT_COSMIN 인 면에서 수직여유가 EXIT_CLEARANCE 이상이 된다(면적분과 같은 보장).
EDGE_EXIT_ADVANCE = EXIT_CLEARANCE / EXIT_COSMIN

_EDGE_CACHE: dict = {}
#  마지막 PTD 호출의 진단 요약(비용·가림·조각수). **전역 상태이므로 진단 전용**이다.
_LAST_PTD: dict = {}
#  extract_edges 로 넘길 키(나머지 ptd_opts 는 edge_field 로 간다)
_PTD_EXTRACT_KEYS = ("sharp_deg", "weld_tol", "keep_flat", "n_min", "keep_reentrant")


_PTD_SPACING_WARNED = set()


def _ptd_spacing_warn(d, lam, where):
    """PTD 를 켤 때 **면적분 격자가 성기면** 경고한다 (ptd_edges D-8). 막지는 않는다.

    왜: 프린지 항은 *정확* PO 전류에 대해 정의됐는데 우리가 더하는 상대는 이산 격자로 잰
    면적분이다. ptd_edges.rcs_po_ptd 는 이 이유로 PO 점구름 간격을 λ/20 이하로 **강제**한다.
    SBR 광선격자는 다른 이산화(투영면적 격자)라 그 문턱을 그대로 옮길 근거가 없어서
    **차단하지 않는다** — 대신 같은 위험을 눈에 보이게 한다. 게다가 SBR 격자 자체의 위상
    산포(dither)가 λ/12 에서 1.37 dB(peak-to-peak, 파일 상단 실측)로 프린지 보정과 같은
    크기이거나 더 크다 → ptd=True 결과를 인용할 때는 격자 의존성을 함께 보고할 것."""
    import ptd_edges as pe
    div = lam / float(d)
    if div >= float(pe.PTD_SPACING_MAX_DIV) - 1e-9:
        return
    key = (where, round(div, 3))
    if key in _PTD_SPACING_WARNED:
        return
    _PTD_SPACING_WARNED.add(key)
    print(f"[rcs_sbr] ⚠ ptd=True 인데 광선격자가 λ/{div:.1f} 다 "
          f"(ptd_edges 권고 λ/{pe.PTD_SPACING_MAX_DIV:g} 이상, D-8). 면적분의 격자 오차가 "
          f"프린지 항과 섞인다 — 격자 의존성을 함께 보고할 것. [{where}]", flush=True)


def _ray_clear(sc, P, u, advance=EDGE_EXIT_ADVANCE):
    """P(표면 위 점)에서 û 로 나가는 길이 뚫려 있는가 — 그림자광선 1발(ray_test)."""
    u = np.asarray(u, float)
    o = np.asarray(P, float) + advance * u[None, :]
    dd = np.tile(u, (o.shape[0], 1))
    ray = mi.Ray3f(o=mi.Point3f(*o.T.astype(np.float32)),
                   d=mi.Vector3f(*dd.T.astype(np.float32)))
    return ~np.asarray(sc.ray_test(ray)).astype(bool)


def _ptd_gamma_map(mesh: Mesh, group_mat: dict, fc: float):
    """그룹 → |Γ| — **씬이 실제로 붙인 값과 같은 규약**(누락 그룹 기본 'plastic')."""
    out = {}
    for grp in sorted(set(np.asarray(mesh.g).tolist())):
        val = group_mat.get(grp, "plastic")
        out[grp] = float(val) if not isinstance(val, str) else float(gamma_po(val, fc))
    return out


def _ptd_edges_for(mesh: Mesh, group_mat: dict, fc: float, cache_key=None, extract_kw=None):
    """모서리 추출(파이썬 루프라 비싸다) 캐시. 키에 fc(|Γ| 의존)·추출 파라미터를 접어 넣는다."""
    import ptd_edges as pe
    ek = dict(extract_kw or {})
    ck = ((cache_key, round(float(fc) / 1e6), tuple(sorted(ek.items())))
          if cache_key is not None else None)
    if ck is not None and ck in _EDGE_CACHE:
        return _EDGE_CACHE[ck]
    es = pe.extract_edges(mesh, gamma=_ptd_gamma_map(mesh, group_mat, fc), **ek)
    if ck is not None:
        _EDGE_CACHE[ck] = es
    return es


def _ptd_edge_A(mesh: Mesh, group_mat: dict, fc: float, pairs, ctr, scene,
                pol="V", cache_key=None, opts=None, exit_vis=True, frozen=False):
    """(û_i, û_s) 쌍 목록에 대한 모서리 프린지 장 A_FW [m²] 배열.

    ctr : 면적분이 **실제로 쓴** 위상원점. 모서리항도 **바로 이 값**을 원점으로 쓴다 —
      코히어런트 합의 물리 요건은 두 항의 원점이 *같다* 는 것 하나뿐이고, 여기서 그 요건은
      구성으로 보장된다(같은 변수를 edge_field 에 그대로 넘긴다).
    frozen : 호출자가 얼린 격자(grid_ref)를 쓰는가. **False**(생산 기본: rcs_sbr_batch·
      rcs_sbr_multistatic·grid_ref 없는 sbr_field)면 ctr 는 이 메쉬의 bbox 중심이어야
      하므로 메쉬에서 **독립 유도**한 원점과 대조해 어긋나면 예외를 던진다(D-10 배선검사).
      **True**(grid_ref 경로)면 ctr 는 자세 합집합 bbox 의 얼린 중심이라 현재 자세의 bbox
      중심과 **정당하게** 다르다(로터가 자세 bbox 를 cm 단위로 흔든다 — 실측 매트리스4E
      0.004~0.026 m). 그때 대조 상대가 없으므로 편차는 진단 메타로만 기록한다. 얼린 격자가
      이 자세를 덮는지는 상류 `_grid_for`(GRID_REF_CHECK)가 이미 검사했다.
    scene : 가림 판정에 쓸 Mitsuba 씬 — 면적분이 조명 추적에 쓴 **그 씬**.
    exit_vis : 면적분의 같은 이름 스위치를 **그대로 물려받는다**. 면적분에서 입사쪽 가림은
      first-hit 이라 끌 수 없고 출사쪽만 선택인데, 모서리항도 정확히 그 대응을 따른다
      (입사 그림자광선은 항상, 출사 그림자광선은 exit_vis 일 때만).
    반환: (A[len(pairs)] complex, edges, summary dict)."""
    import ptd_edges as pe
    o = dict(opts or {})
    occl = bool(o.pop("occlusion", True))
    edges = o.pop("edges", None)
    ek = {kk: o.pop(kk) for kk in list(o) if kk in _PTD_EXTRACT_KEYS}

    t0 = time.perf_counter()
    if edges is None:
        edges = _ptd_edges_for(mesh, group_mat, fc, cache_key, ek)
    t_ext = time.perf_counter() - t0

    #  ⭐ 위상원점 (D-10) — 면적분과 모서리항이 다른 원점을 쓰면 코히어런트 합이 무의미해진다.
    #    모서리항 원점은 아래에서 **면적분이 실제로 쓴 ctr 그 자체**를 쓰므로 동일성은 구성으로
    #    보장된다. 남는 검사는 배선검사다: 얼리지 않은 경로(frozen=False)에서는 ctr 가 메쉬
    #    bbox 중심과 같아야 하고(같은 식이라 실제 편차는 비트 0), 어긋나면 호출자가 엉뚱한
    #    ctr 를 넘긴 것이니 막는다. 얼린 경로(frozen=True)는 ctr≠자세 bbox 중심이 정상이다.
    org = pe.sbr_phase_origin(mesh)                     # 현재 자세 bbox 중심(독립 유도, 진단·대조용)
    ctr = np.asarray(ctr, float)
    dev = float(np.max(np.abs(org - ctr)))
    tol = (C0 / float(fc)) / 1000.0                     # λ/1000 = 위상 0.36°
    if not frozen and dev > tol:
        raise ValueError(
            "rcs_sbr PTD: 모서리 위상원점이 면적분 원점(bbox 중심)과 %.4g m 어긋난다 "
            "(허용 %.4g m). 두 항이 다른 원점을 쓰면 상대위상이 무의미해진다. "
            "얼린 격자(grid_ref)를 쓰고 있다면 frozen=True 를 물려줘야 한다." % (dev, tol))

    t0 = time.perf_counter()
    A = np.zeros(len(pairs), complex)
    agg = {}
    for i, (u_i, u_s) in enumerate(pairs):
        vf = None
        if occl:
            def vf(pts, ui, us, _sc=scene, _ev=bool(exit_vis)):
                v = _ray_clear(_sc, pts, ui)                # 입사 가림(면적분의 first-hit 대응)
                if _ev and not np.array_equal(np.asarray(us, float), np.asarray(ui, float)):
                    v = v & _ray_clear(_sc, pts, us)        # 출사 가시성(바이스태틱만 추가 1발)
                return v
        #  ⭐원점은 면적분이 실제로 쓴 ctr **그 자체** — org(자세 bbox 중심)가 아니다.
        #    frozen=False 면 둘이 비트 동일하고, frozen=True 면 ctr(얼린 원점)만이 옳다.
        a, m = pe.edge_field(edges, fc, u_i, u_s=u_s, pol=pol, origin=ctr, visible_fn=vf, **o)
        A[i] = a
        for kk, vv in m.items():
            if vv is None:
                continue
            if kk.startswith(("n_", "length_")):
                agg[kk] = agg.get(kk, 0) + vv
            elif kk == "sin_a_min":
                agg[kk] = vv if agg.get(kk) is None else min(agg[kk], vv)
    t_edge = time.perf_counter() - t0

    _LAST_PTD.clear()
    _LAST_PTD.update(pol=str(pol), n_dirs=len(pairs), occlusion=bool(occl),
                     origin=[float(x) for x in ctr],            # 실제 사용 원점(=면적분 ctr)
                     origin_frozen=bool(frozen),
                     mesh_bbox_center=[float(x) for x in org],
                     origin_dev_from_surface_m=dev,
                     t_extract_s=t_ext, t_edge_s=t_edge, edge_meta=agg,
                     edges_stats=dict(edges.stats),
                     A_abs=[float(abs(x)) for x in A])
    return A, edges, dict(_LAST_PTD)


def rcs_sbr_multistatic(mesh: Mesh, group_mat: dict, fc: float, u_i, u_s_list,
                        spacing=None, pad=1.15, cache_key=None, penetrate=True, jitter=2,
                        shell_groups=None, exit_vis=True, symmetrize=False,
                        ptd=False, ptd_pol="V", ptd_opts=None):
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

    scene, shapes, gammas, matk = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    _shells = _resolve_shells(group_names, group_mat, shell_groups)
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i, matk_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_shells)
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

    #  모서리 프린지 항 — 수신방향마다 1 개. 조명(û_i)은 하나이므로 모서리 추출·가림도 재사용된다.
    if ptd:
        _ptd_spacing_warn(d, lam, "rcs_sbr_multistatic")
        A_ptd = _ptd_edge_A(mesh, group_mat, fc, [(u_i, us) for us in U_s], ctr, scene,
                            pol=ptd_pol, cache_key=cache_key, opts=ptd_opts,
                            exit_vis=exit_vis)[0]

    sig_acc = np.zeros(len(U_s))
    for ox, oy in offsets:
        O = (ctr + Rout * u_i)[None, :] + (A + ox)[:, None] * e1 + (B + oy)[:, None] * e2
        D = np.tile(-u_i, (A.size, 1))
        ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)), d=mi.Vector3f(*D.T.astype(np.float32)))

        def _hits(sc, shptr, gam, mk=None):
            """⭐2026-08-10 — 각도의존 Γ(θ) 를 여기에도 배선했다.

            그전까지 이 함수는 **수직입사 Γ 상수만** 곱했다. 같은 저장소의 `sbr_field`(모노)와
            `sbr_field_bistatic`(바이스태틱 복소장)은 둘 다 `gamma_shape(재질, fc, cosθ_i)` 를
            곱하므로, 이 함수만 **다른 물리**를 쓰고 있었다.
            ⚠ 그 격차는 계통편차가 아니라 **산포**다 — `outputs/verify_bistatic_field.json` 의
              24 케이스에서 평균 +0.33 dB · 중앙 +0.27 dB 인데 11 건이 음수이고 폭이
              −2.70 ~ +3.62 dB 다. 즉 «σ 가 일정하게 낮았다» 가 아니라 «자세마다 몇 dB 씩
              달랐다» 이고, 그래서 눈에 안 띄었다.
            ⚠ 이 배선은 `ANGLE_GAMMA=False` 에서 예전과 **비트 동일**이다(그 경우 블록을 건너뛴다).
            """
            si = sc.ray_intersect(ray)
            valid = np.asarray(si.is_valid()).astype(bool)
            P = np.asarray(mi.Point3f(si.p)).T
            Nn = np.asarray(mi.Vector3f(si.n)).T
            g = np.zeros(P.shape[0])
            which = np.full(P.shape[0], -1, int)          # 어느 그룹을 맞았나(각도 Γ 용)
            for _i, (sp, gm) in enumerate(zip(shptr, gam)):
                hit = np.asarray(si.shape == sp).astype(bool)
                g = np.where(hit, gm, g)
                which = np.where(hit, _i, which)
            sgn = np.sign(np.einsum("ij,ij->i", Nn, -D)); sgn[sgn == 0] = 1.0
            Nn = Nn * sgn[:, None]
            if ANGLE_GAMMA and mk is not None:
                from materials import gamma_shape as _gsh
                cos_i = Nn @ u_i                          # 국소 입사 코사인(조명은 û_i 하나)
                lit_here = valid & (cos_i > 1e-6)
                for _i, _key in enumerate(mk):
                    if _key is None:                      # float 로 넘어온 재질은 상수
                        continue
                    sel = (which == _i) & lit_here
                    if sel.any():
                        g[sel] = g[sel] * _gsh(_key, fc, cos_i[sel])
            return valid, P - ctr, Nn, g, si

        valid, Pc, Nn, g, si = _hits(scene, shape_ptrs, gammas, matk)  # 외부 조명 히트
        lit_i = valid & ((Nn @ u_i) > 1e-6)      # û_i 조명 게이트
        if do_pen:
            tau = np.zeros(valid.shape[0])
            for i in shell_pos:
                tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                               1.0 - gammas[i] ** 2, tau)
            valid2, Pc2, Nn2, g2, _ = _hits(scene_i, shptr_i, gammas_i, matk_i)  # 내부 금속
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
            Etot = E * d * d                                  # 면적분 [m²]
            if ptd:
                Etot = Etot + A_ptd[j]                        # + 모서리 프린지 [m²]
            sig_acc[j] += (4.0 * np.pi / lam ** 2) * np.abs(Etot) ** 2
    sig = sig_acc / len(offsets)

    if symmetrize:
        #  σ_sym = √(σ(i,s)·σ(s,i)) — 상반기하를 한 번 더 평가한다(조명 추적 1회 추가/Rx).
        rev = np.empty(len(U_s))
        for j, u_s in enumerate(U_s):
            rev[j] = float(np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, group_mat, fc, u_s, [u_i], spacing=spacing, pad=pad, cache_key=cache_key,
                penetrate=penetrate, jitter=jitter, shell_groups=shell_groups,
                exit_vis=exit_vis, symmetrize=False,
                ptd=ptd, ptd_pol=ptd_pol, ptd_opts=ptd_opts), float))[0])
        sig = np.sqrt(sig * rev)

    return sig if len(U_s) > 1 else float(sig[0])


# ─────────────────────────────────────────────────────────────────────────── #
#  ⭐ 얼린 광선 격자 (grid_ref) — 2026-08-10
# ─────────────────────────────────────────────────────────────────────────── #
#  ■ 무엇이 문제였나
#    `sbr_field` 는 격자를 **메쉬에서** 만든다 — ctr=½(V.max+V.min), Rout=max|V−ctr|·pad+3d,
#    n=ceil(2Rout/d). 정지비행이라 몸체가 안 움직여도 **로터가 돌면 정점 bbox 가 흔들려서**
#    자세마다 이 셋이 다시 정해진다. 슬로타임(마이크로도플러)에서는 그게 신호로 둔갑한다:
#      · ctr 이동  = 위상 원점 흔들림. E 의 크기·σ 에는 영향이 **정확히 0** 이지만(전역 위상),
#                    프레임 사이 위상차가 신호인 마이크로도플러에는 그대로 실린다.
#                    실측(matrice4e, 4096 자세): ctr·û 가 39.9 mm = **5.85 rad p-p** 흔들린다.
#      · Rout·n 변화 = 표본 집합 갈아엎기. n 은 정수라 한 칸 튀면 t 격자가 통째로 d/2 밀린다
#                    (λ/12 에서 4095 스텝 중 **1636 번**). 서브셀 오프셋이 자세마다 새로
#                    뽑히고(std 0.2887 ≈ 균등분포 1/√12), 그 «주사위» 의 크기가 곧 파일 상단의
#                    dither(λ/12 1.373 dB p-p) 다. 즉 1.4 dB 주사위를 프레임마다 다시 굴린다.
#
#  ■ 실험 근거 (outputs/sbr_grid_convergence.json, benchmark/sbr_grid_convergence_md.py)
#    격자를 촘촘히 해서는 안 내려간다 — 생산 팔은 λ/12→λ/32 에서 대역밖 비율이 2.2 dB 만
#    줄고 log-log 기울기가 **−0.55**(R² 0.94; d² 이산화 잡음이면 −2 여야 한다).
#    같은 자세에서 격자를 **얼리면** 같은 광선 수로 바로 내려가고(λ/12 에서 논문 지표 9.3 dB /
#    절대 대역밖 전력으로는 13.1 dB), 기울기가 **−2.09**(R² 0.987)로 예측대로 수렴한다.
#    ⚠ 「반만 고치기」는 신뢰할 수 없다 — 위상 원점만 사후 보정하면 λ/8 에서 오히려 0.57 dB
#      나빠진다(두 인공물이 그 격자에서 부분상쇄하고 있었다). 얼리려면 ctr·Rout·n 을 **다** 얼린다.
#
#  ■ 얼리기의 대가 (정직하게 적는다 — 공짜가 아니다)
#    (1) 광선 수 +8.3 % (λ/12, matrice4e: 얼린 n₀=124 → 15376발 vs 자세평균 14194발).
#    (2) 백색 슬로타임 잡음이 **결정론적 레벨 편향**으로 바뀐다 — 얼린 팔은 오프셋 «한 판» 에
#        레벨이 걸린다(같은 λ/12 에서 반 칸 옮기면 1.4 dB 차). 절대 σ 를 인용할 때 유의.
#    (3) 격자를 덮개로 삼으므로 **모든 자세를 덮는 기준**이어야 한다 → `grid_ref_from` 에
#        자세들을 다 넣고, 커널이 자세마다 덮개를 검사한다(GRID_REF_CHECK).
#
#  ■ 기본값은 안 바뀐다
#    `grid_ref=None` 이면 이 인자가 없던 때와 **비트 단위로 같다**(회귀 게이트:
#    benchmark/verify_frozen_grid.py, 원장 outputs/verify_frozen_grid.json).
#    기존 원장(report07 계열)은 전부 grid_ref 없이 난 값이므로 그대로 살아 있다.
GRID_REF_CHECK = bool(int(os.environ.get("SIONNA2_GRID_REF_CHECK", "1")))
_GRID_REF_RTOL = 1e-9              # grid_ref.spacing ↔ 실제 d 허용 상대오차


class GridRef(NamedTuple):
    """얼린 광선 격자 한 판. 물리는 (ctr, Rout, n) 셋이 전부고 나머지는 대조용 꼬리표다.

      ctr     : (3,) 격자 중심 = **위상 원점**  e^{j2k(P−ctr)·û}
      Rout    : 광선 출발 평면까지의 거리 [m] (ctr + Rout·û 에서 −û 로 쏜다)
      n       : 격자 한 변 칸 수 → n² 발
      spacing : 이 판이 전제하는 격자 간격 d [m]. 커널이 실제 d 와 다르면 **예외를 던진다**
                (d 가 바뀌면 n·Rout 의 뜻이 바뀐다 — 사다리마다 판을 새로 만들라는 뜻).
      fc·pad·n_mesh : 만든 조건 기록(판정에 안 쓴다).
    """
    ctr: np.ndarray
    Rout: float
    n: int
    spacing: float
    fc: float | None = None
    pad: float = 1.15
    n_mesh: int = 0

    def asjson(self):
        """원장(JSON)에 그대로 넣을 수 있는 dict — 되읽으면 다시 grid_ref 로 쓸 수 있다."""
        return dict(ctr=[float(x) for x in np.asarray(self.ctr, float)],
                    Rout=float(self.Rout), n=int(self.n),
                    spacing=(None if self.spacing is None else float(self.spacing)),
                    fc=(None if self.fc is None else float(self.fc)),
                    pad=float(self.pad), n_mesh=int(self.n_mesh))


def as_grid_ref(ref) -> GridRef:
    """GridRef · dict · (ctr, Rout, n[, spacing]) 를 GridRef 로 정규화하고 **검사**한다."""
    if isinstance(ref, GridRef):
        g = ref._replace(ctr=np.asarray(ref.ctr, float))
    elif isinstance(ref, dict):
        miss = [k for k in ("ctr", "Rout", "n") if k not in ref]
        if miss:
            raise ValueError(f"grid_ref dict 에 {miss} 가 없다 — (ctr, Rout, n) 은 필수다.")
        g = GridRef(ctr=np.asarray(ref["ctr"], float), Rout=float(ref["Rout"]),
                    n=int(ref["n"]),
                    spacing=(None if ref.get("spacing") is None else float(ref["spacing"])),
                    fc=(None if ref.get("fc") is None else float(ref["fc"])),
                    pad=float(ref.get("pad", 1.15)), n_mesh=int(ref.get("n_mesh", 0)))
    else:
        seq = tuple(ref)
        if len(seq) not in (3, 4):
            raise ValueError("grid_ref 시퀀스는 (ctr, Rout, n) 또는 (ctr, Rout, n, spacing) 이다.")
        g = GridRef(ctr=np.asarray(seq[0], float), Rout=float(seq[1]), n=int(seq[2]),
                    spacing=(float(seq[3]) if len(seq) == 4 else None))
    if np.asarray(g.ctr).shape != (3,) or not np.all(np.isfinite(g.ctr)):
        raise ValueError(f"grid_ref.ctr 는 유한한 (3,) 이어야 한다 — 받은 것 {g.ctr!r}")
    if not (np.isfinite(g.Rout) and g.Rout > 0):
        raise ValueError(f"grid_ref.Rout 는 양의 유한값이어야 한다 — 받은 것 {g.Rout!r}")
    if g.n < 1:
        raise ValueError(f"grid_ref.n 은 1 이상 정수여야 한다 — 받은 것 {g.n!r}")
    return g


def _verts_of(meshes):
    """Mesh · (N,3) 배열 · 그것들의 열(列) 을 **정점 배열 리스트**로 만든다.

    ⚠ 반복자(generator)를 주면 여기서 통째로 물질화한다(중심을 먼저 구한 뒤 반경을 재려면
      두 번 훑어야 한다). 자세 4096 개를 통째로 넣지 말고 **로터 한 바퀴를 고르게 훑는
      수십 개**를 넣어라 — 덮개는 그것으로 충분하고 커널이 자세마다 검사한다."""
    if hasattr(meshes, "v"):
        return [np.asarray(meshes.v, float)]
    if isinstance(meshes, np.ndarray) and meshes.ndim == 2 and meshes.shape[1] == 3:
        return [np.asarray(meshes, float)]
    out = []
    for m in meshes:
        out.append(np.asarray(m.v, float) if hasattr(m, "v") else np.asarray(m, float))
        if out[-1].ndim != 2 or out[-1].shape[1] != 3:
            raise ValueError(f"정점 배열이 (N,3) 이 아니다 — {out[-1].shape}")
    if not out:
        raise ValueError("grid_ref_from: 메쉬가 하나도 없다.")
    return out


def grid_ref_from(meshes, fc: float, spacing=None, pad=1.15) -> GridRef:
    """메쉬(들)의 **합집합 경계상자**로 얼린 격자 기준 (ctr, Rout, n) 을 만든다.

        ref = grid_ref_from([fp.pose(p) for p in phases], fc)     # 로터 위상 전 구간
        E   = [sbr_field(fp.pose(p), gmat, fc, u, grid_ref=ref) for p in phases]

    · meshes : Mesh 하나, (N,3) 정점 배열, 또는 그것들의 열(列). **여러 자세를 넣으면
      합집합 bbox** 로 중심을 잡고 그 중심에서 잰 최대 반경으로 격자를 키운다 —
      로터 위상 전 구간을 한 판으로 덮으려면 이렇게 해야 한다.
    · 식은 생산 경로와 **같다**: ctr=½(lo+hi) · Rout=Rmax·pad+3d · n=ceil(2Rout/d).
      메쉬를 하나만 주면 그 자세의 생산 격자와 정확히 같은 판이 나온다(게이트가 검사한다).
    · spacing 을 안 주면 λ/DEFAULT_DIV. **격자 간격마다 판이 다르다** — 사다리를 돌리면
      div 마다 `grid_ref_from(..., spacing=λ/div)` 를 새로 만들어야 한다.
    """
    lam = C0 / float(fc)
    d = float(spacing) if spacing else lam / DEFAULT_DIV
    items = _verts_of(meshes)
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for V in items:
        lo = np.minimum(lo, V.min(0))
        hi = np.maximum(hi, V.max(0))
    ctr = 0.5 * (lo + hi)
    Rmax = 0.0
    for V in items:
        Rmax = max(Rmax, float(np.linalg.norm(V - ctr, axis=1).max()))
    Rout = Rmax * pad + 3 * d
    return GridRef(ctr=ctr, Rout=float(Rout), n=int(np.ceil(2 * Rout / d)),
                   spacing=float(d), fc=float(fc), pad=float(pad), n_mesh=len(items))


#  ── ⭐ 하류 슬로타임 경로가 공유하는 스위치 + 판 만들기 ─────────────────────── #
#  왜 스위치인가: 전후 비교를 **같은 코드**로 돌릴 수 있어야 「얼리니 이렇게 달라졌다」가
#  증거가 된다. SIONNA2_FREEZE_GRID=0 이면 하류가 grid_ref=None 을 넘기므로 옛 값과
#  비트 단위로 같다(커널의 기본 동작은 여전히 «안 얼림» 이고, 켜는 쪽은 호출자다).
_FREEZE_ENV = "SIONNA2_FREEZE_GRID"


def freeze_grid_enabled() -> bool:
    """슬로타임(마이크로도플러) 경로가 격자를 얼릴지 — 기본 **True**.

    ⚠ 호출할 때마다 환경변수를 읽는다(import 시점이 아니다). 한 프로세스 안에서
      `os.environ["SIONNA2_FREEZE_GRID"]="0"` 로 옛 동작을 되살려 A/B 를 낼 수 있다.
    0 · false · no · off (대소문자 무관) 면 끈다."""
    v = os.environ.get(_FREEZE_ENV, "1").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def grid_ref_for_slowtime(pose_fn, dirs, fc, spacing=None, pad=1.15, n_probe=24):
    """슬로타임 열이 쓸 **한 판** — 로터 한 바퀴를 고르게 훑은 자세들의 합집합 bbox.

        gref = grid_ref_for_slowtime(fp.pose, fp.dirs, FC, spacing=None)
        E[i] = sbr_field(fp.pose(ph[i]), gmat, FC, u, grid_ref=gref)   # None 이면 옛 동작

    · pose_fn : 로터 위상 리스트[deg] → 메쉬(.v 를 가진 것이면 무엇이든). FastPoser.pose 나
      `lambda p: pose_articulated(spec, rotor_phase_deg=p)` 를 그대로 넣는다.
    · dirs    : 로터별 회전 방향(±1). 위상은 dir_k·φ 로 준다 — 생산 경로와 같은 규약이다.
    · n_probe : φ ∈ [0,360) 을 몇 등분해 훑을지. bbox 는 **정점별 최댓값**이라 로터마다
      위상이 달라도(rpm 흩어짐) 이 봉투 안에 든다 — 각 로터가 이 스윕에서 자기 극단을
      다 지나기 때문이다. 그래도 커널이 자세마다 덮개를 검사한다.
    · **SIONNA2_FREEZE_GRID=0 이면 None 을 돌려준다** → 호출자가 그대로 넘기면 옛 동작.
    ⚠ 격자 간격마다 판이 다르다 — 사다리를 돌리면 div 마다 이 함수를 다시 불러라."""
    if not freeze_grid_enabled():
        return None
    dirs = [float(d) for d in dirs]
    phis = np.linspace(0.0, 360.0, int(n_probe), endpoint=False)
    meshes = [pose_fn([d * float(p) for d in dirs]) for p in phis]
    return grid_ref_from(meshes, fc, spacing=spacing, pad=pad)


def _grid_basis(u):
    """광선 격자의 가로축 (e1, e2) — û 하나로 정해지는 **규약**이다(물리 아님).
    ⚠ `sbr_field` 와 `sbr_field_bistatic` 이 같은 basis 를 써야 모노 회귀 게이트가 위상까지
      겹친다. 그래서 한 군데에 둔다."""
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    return e1, e2


def grid_ref_margin(mesh, u, grid_ref, spacing=None, fc=None) -> dict:
    """얼린 격자가 이 자세를 **덮는가** — 여유[m]를 재서 돌려준다(예외는 안 던진다).

    가로 두 축은 광선 원점이 실제로 깔린 범위 ±(n−1)d/2 로, 세로(û)는 광선 출발 평면
    Rout 으로 잰다. 셋 다 양수여야 표적이 격자 안에 든다. 회귀 게이트 ③ 이 이걸 쓴다."""
    ref = as_grid_ref(grid_ref)
    d = float(spacing) if spacing else (
        ref.spacing if ref.spacing else C0 / float(fc if fc else ref.fc) / DEFAULT_DIV)
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    V = np.asarray(mesh.v, float) if hasattr(mesh, "v") else np.asarray(mesh, float)
    return _grid_cover(V, np.asarray(ref.ctr, float), float(ref.Rout), int(ref.n), float(d), u)


def _grid_cover(V, ctr, Rout, n, d, u) -> dict:
    e1, e2 = _grid_basis(u)
    W = V - ctr
    half = (n - 1) / 2.0 * d
    m1 = float(half - np.abs(W @ e1).max())
    m2 = float(half - np.abs(W @ e2).max())
    mu = float(Rout - (W @ u).max())
    return dict(n=int(n), spacing_m=float(d), half_extent_m=float(half),
                margin_e1_m=m1, margin_e2_m=m2, margin_u_m=mu,
                margin_min_m=float(min(m1, m2, mu)),
                margin_min_cells=float(min(m1, m2, mu) / d),
                covered=bool(min(m1, m2, mu) >= 0.0))


def _grid_for(mesh, d, pad, grid_ref, u, where):
    """이 호출이 쓸 격자 (ctr, Rout, n) 을 정한다 — 모노·바이스태틱이 **같이** 쓴다.

    grid_ref=None 이면 옛 코드와 **같은 세 줄**(비트 동일)이고, 주어지면 그 판을 쓴다."""
    if grid_ref is None:
        V = np.asarray(mesh.v, float)
        ctr = 0.5 * (V.max(0) + V.min(0))
        Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d
        return ctr, Rout, int(np.ceil(2 * Rout / d))
    ref = as_grid_ref(grid_ref)
    if ref.spacing is not None and abs(d - ref.spacing) > _GRID_REF_RTOL * max(d, ref.spacing):
        raise ValueError(
            f"{where}: grid_ref 의 격자 간격이 이 호출과 다르다 "
            f"(ref {ref.spacing*1e3:.6f} mm ↔ 지금 {d*1e3:.6f} mm). n·Rout 은 d 에 매인 값이라 "
            f"섞어 쓰면 덮개가 깨진다 — `grid_ref_from(..., spacing={d!r})` 로 판을 새로 만들라.")
    ctr = np.asarray(ref.ctr, float)
    Rout = float(ref.Rout)
    n = int(ref.n)
    if GRID_REF_CHECK:
        V = np.asarray(mesh.v, float)
        cov = _grid_cover(V, ctr, Rout, n, d, np.asarray(u, float))
        if not cov["covered"]:
            raise ValueError(
                f"{where}: 얼린 격자가 이 자세를 못 덮는다 — 여유 "
                f"e1 {cov['margin_e1_m']*1e3:+.2f} · e2 {cov['margin_e2_m']*1e3:+.2f} · "
                f"û {cov['margin_u_m']*1e3:+.2f} mm (음수 = 밖으로 삐져나옴). "
                f"grid_ref_from 에 이 자세를 포함시켜 판을 다시 만들라 "
                f"(검사를 끄려면 SIONNA2_GRID_REF_CHECK=0 — 권하지 않는다).")
    return ctr, Rout, n


def _ray_grid(ctr, Rout, n, d, u):
    """격자 (ctr, Rout, n, d) 와 방향 û 에서 **평행 광선 다발**을 만든다(n² 발).
    ⚠ 모노·바이스태틱이 같은 코드를 쓰도록 한 군데에 둔다 — 옛 두 벌과 식이 같다."""
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    e1, e2 = _grid_basis(u)
    O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
    D = np.tile(-u, (O.shape[0], 1))
    return mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                    d=mi.Vector3f(*D.T.astype(np.float32)))


def grid_used(mesh, fc: float, u, spacing=None, pad=1.15, grid_ref=None) -> dict:
    """이 호출이 **실제로 쓸** 격자를 그대로 돌려준다(광선은 안 쏜다) — 진단·게이트용.

    커널과 같은 `_grid_for` 를 부르므로 재구현이 아니다. 회귀 게이트 ② 가 자세를 바꿔 가며
    이 값이 변하는지(생산) / 안 변하는지(얼림) 를 이걸로 본다."""
    lam = C0 / float(fc)
    d = float(spacing) if spacing else lam / DEFAULT_DIV
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    ctr, Rout, n = _grid_for(mesh, d, pad, grid_ref, u, "grid_used")
    return dict(ctr=[float(x) for x in ctr], Rout=float(Rout), n=int(n),
                spacing_m=float(d), n_rays=int(n) ** 2,
                ctr_dot_u=float(np.asarray(ctr, float) @ u), frozen=bool(grid_ref is not None))


def sbr_field(mesh: Mesh, group_mat: dict, fc: float, u, spacing=None, pad=1.15,
              cache_key=None, penetrate=True, shell_groups=None,
              ptd=False, ptd_pol="V", ptd_opts=None, *, grid_ref=None, range_m=None):
    """**복소 산란장 E(û)** 를 돌려준다 (σ 가 아니라 E — 마이크로도플러는 위상이 필요하다).

        E(û) = Σ_hits |Γ_i| · e^{j2k p_i·û} · d²          σ = (4π/λ²)|E|²

    û 는 표적 → 레이더 방향 단위벡터. penetrate=True 면 rcs_sbr_batch 와 동일하게 유전체 셸을
    투과시켜 내부 금속을 τ=1−|Γ|² 로 코히런트 가산(헤드라인과 일관).

    ptd (기본 **False**) : True 면 같은 위상원점(bbox 중심)의 모서리 프린지 A_FW [m²] 를 더한
    **복소장**을 돌려준다 — 위상을 쓰는 하류(마이크로도플러)가 그대로 쓸 수 있다.
    ⚠ ptd=False 는 이 인자들이 없던 때와 비트 단위로 같다.

    range_m (기본 **None**, keyword-only) : ⭐**구면파 조명**. None 이면 **평면파**(원거리장
    근사)이고 이 인자가 없던 때와 **비트 동일**하다. 값을 주면 표적 중심에서 그 거리만큼
    떨어진 점에 레이더가 있다고 보고 **실제 왕복 거리**로 위상을 준다.

        평면파(기본)  exp(j2k (p−ctr)·û)      ← 파면이 평평하다는 가정
        구면파        exp(j2k (R − |p−p_tx|)) ← p_tx = ctr + R·û, 중심 감산은 그대로

    ⭐부호는 두 갈래가 **같아야** 한다 — 원거리장 극한에서 (R − |p−p_tx|) → (p−ctr)·û 다.
      2026-08-11 이전에는 구면파가 (|p−p_tx| − R) 이라 평면파와 정확히 반대였다.
      아래 «위상 부호 규약» 주석에 판정 근거를 적었다.

    ⚠ **왜 필요한가** — 평면파는 원거리장 근사다. 이 기체의 경계는 2D²/λ ≈ 8 m 인데
      우리 주력 거리가 3 m 라 **경계 안쪽**이다. 거기서는 파면이 휘어 기체 앞뒤가 다른
      위상을 받으므로 간섭 무늬가 실제로 달라진다. 그 차이를 재려면 이 인자가 필요하다.
      2차 위상 오차의 크기는 대략 k·D²/(4R) 이고, D=0.6 m·R=3 m·3.5 GHz 에서 **약 2.2 rad**
      이다 — 무시할 수 없다.
    ⚠ **이 배선이 하는 것과 안 하는 것** — 위상만 구면파로 바꾼다. 광선은 여전히
      **평행 격자**이고 1/r 확산도 안 넣는다. 근거리장의 지배적 효과가 **위상 곡률**이라
      그것부터 잰다. 광선을 발산시키고 확산을 넣는 것은 별개의 다음 단계다.

    grid_ref (기본 **None**, keyword-only) : ⭐**얼린 광선 격자**. None 이면 자세마다 격자를
      메쉬에서 다시 만든다(옛 동작, 비트 동일). `grid_ref_from(자세들, fc, spacing)` 이 준
      판을 넣으면 모든 자세가 **같은 ctr·Rout·n** 을 쓴다 — 위상 원점이 안 흔들리고 표본
      집합이 안 갈아엎어진다(왜 필요한지는 위 「얼린 광선 격자」 절). ptd=True 면 모서리
      프린지의 위상 원점도 같이 얼어붙는다(둘이 같은 ctr 을 쓴다 — `_ptd_edge_A` 에
      frozen=True 로 물려주고, 그때 D-10 배선검사는 대조 상대가 없어 진단 기록으로 바뀐다).
      ⚠ 커널이 자세마다 덮개를 검사해 삐져나오면 예외를 던진다(GRID_REF_CHECK).

    ⚠ ptd=True + range_m 동시 사용의 **정직 표기** — 면적분은 구면파 위상(실제 왕복거리)을
      쓰지만 모서리 프린지 항은 **평면파 위상뿐**이다(ptd_edges.edge_field 에 구면 갈래가
      없다). 두 항이 원점(ctr)을 공유하므로 1차(경사) 위상까지는 정합하고, 남는 것은 파면
      곡률(2차) 누락 ≈ k·ρ⊥²/R — 3.5 GHz·R=15 m·반폭 ρ⊥≈0.3 m 에서 최대 ≈0.4 rad 다.
      프린지가 수 % 보정이라 전체 오차는 그 일부에 그치지만, 「정확 결합」 주장은
      평면파(range_m=None)로 한정할 것. 어느 갈래였는지 `_LAST_PTD["fringe_wavefront"]`
      에 실린다."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV
    u = np.asarray(u, float); u = u / np.linalg.norm(u)

    scene, shapes, gammas, matk = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    _shells = _resolve_shells(group_names, group_mat, shell_groups)
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i, matk_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_shells)
        shptr_i = [mi.ShapePtr(s) for s in shapes_i]

    ctr, Rout, n = _grid_for(mesh, d, pad, grid_ref, u, "sbr_field")
    ray = _ray_grid(ctr, Rout, n, d, u)

    def _field(sc, shptr, gam, mk=None):
        si = sc.ray_intersect(ray)
        valid = np.asarray(si.is_valid()).astype(bool)
        P = np.asarray(mi.Point3f(si.p)).T
        Nn = np.asarray(mi.Vector3f(si.n)).T
        g = np.zeros(P.shape[0])
        which = np.full(P.shape[0], -1, int)
        for _i, (sp, gm) in enumerate(zip(shptr, gam)):
            hit = np.asarray(si.shape == sp).astype(bool)
            g = np.where(hit, gm, g)
            which = np.where(hit, _i, which)
        sgn = np.sign(Nn @ u); sgn[sgn == 0] = 1.0        # 법선을 광선 오는 쪽(û)으로 정렬
        Nn = Nn * sgn[:, None]
        cos_i = Nn @ u                                    # ⭐국소 입사 코사인
        lit = valid & (cos_i > 1e-6)
        if ANGLE_GAMMA and mk is not None:                # ⭐각도 모양을 곱한다
            from materials import gamma_shape as _gsh
            for _i, _key in enumerate(mk):
                if _key is None:
                    continue
                sel = (which == _i) & lit
                if sel.any():
                    g[sel] = g[sel] * _gsh(_key, fc, cos_i[sel])
        if range_m is None:                               # 평면파 — 옛 동작과 비트 동일
            ph = np.exp(1j * 2.0 * k * ((P - ctr) @ u))
        else:                                             # ⭐구면파 — 실제 왕복 거리
            p_tx = ctr + float(range_m) * np.asarray(u, float)
            # ⭐부호 정정(2026-08-11) — 아래 «위상 부호 규약» 주석 참조.
            #   전에는 (|P−p_tx| − R) 이었고, 그건 평면파 갈래와 **정확히 반대**였다.
            ph = np.exp(1j * 2.0 * k *
                        (float(range_m) - np.linalg.norm(P - p_tx, axis=1)))
        return valid, lit, g, ph, si

    valid, lit, g, phase, si = _field(scene, shape_ptrs, gammas, matk)
    E = np.sum(np.where(lit, g, 0.0) * phase)
    if do_pen:
        tau = np.zeros(valid.shape[0])
        for i in shell_pos:
            tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                           1.0 - gammas[i] ** 2, tau)
        _, lit2, g2, phase2, _ = _field(scene_i, shptr_i, gammas_i, matk_i)
        E = E + np.sum(np.where(lit2 & (tau > 0), tau * g2, 0.0) * phase2)
    Etot = complex(E) * d * d                                 # 면적분 [m²]
    if ptd:
        _ptd_spacing_warn(d, lam, "sbr_field")
        Etot = Etot + complex(_ptd_edge_A(mesh, group_mat, fc, [(u, u)], ctr, scene,
                                          pol=ptd_pol, cache_key=cache_key, opts=ptd_opts,
                                          frozen=(grid_ref is not None))[0][0])
        #  ⭐정직 표기 — 프린지 항은 **평면파 위상뿐**이다(edge_field 에 구면 갈래가 없다).
        #    range_m 구면파와 섞이면 원점 공유로 1차(경사) 위상까지는 정합하고, 파면 곡률
        #    (2차) ≈ k·ρ⊥²/R 만 프린지에 빠진다(docstring 참조). 갈래를 진단 메타에 남긴다.
        _LAST_PTD["fringe_wavefront"] = ("planar_vs_spherical_po" if range_m is not None
                                         else "planar")
    return Etot


# ─────────────────────────────────────────────────────────────────────────────
# ⭐⭐ 위상 부호 규약 (2026-08-11 확정 · 결함 하나를 고쳤다)
#
# **표준(레이다·Sionna PathSolver)** 은 수신 신호를 exp(−j2πf τ), τ = 2R/c 로 적는다.
# 표적 중심에서 잰 산란점 P 와 «표적에서 레이다를 보는» 단위벡터 û 에 대해
#     R = R₀ − P·û   ⇒   exp(−j2πf τ) = exp(−j2kR₀) · **exp(+j2k P·û)**
# 이므로 **투영에 대한 +j 는 옳다.** 우리 평면파 갈래가 바로 그 꼴이다.
#
# ⛔그런데 구면파 갈래는 **거리**에 +j 를 걸고 있었다: exp(+j2k(|P−p_tx| − R)).
#   거리와 투영은 부호가 반대이므로(원거리장에서 정확히 −1 배, 잔차 8.9e−16 m)
#   `range_m` 을 주는 순간 도플러 부호가 뒤집혔다.
#
# 답을 아는 문제로 판정했다 — 5 m/s 로 **다가오는** 산란체(참값 f_d = +116.75 Hz):
#     평면파  exp(+j2k P·û)          →  +117.19 Hz   ✓
#     구면파  exp(+j2k(|P−p_tx|−R))  →  −117.19 Hz   ✗  ← 결함
#     수정판  exp(+j2k(R−|P−p_tx|))  →  +117.19 Hz   ✓  (표준과 |ρ| = 1.000000)
#
# ⭐**σ 는 영향이 없다** — σ = 4π/λ²·|E|² 이고 |conj(E)| = |E| 이므로 **비트 단위로 동일**하다.
#   기존 σ 원장·검증(das_fleet · sbr_kr_sweep · box_control)은 하나도 무효가 아니다.
# ⭐**재계산도 필요 없다** — 이미 계산된 구면파 복소 시계열은 `np.conj` 한 번으로 정정된다.
# ⚠**영향 범위**: `range_m` 을 준 실행의 **도플러 부호**뿐이다(평면파 실행은 무관).
#   · 영향 없음 — f_tip 크기 · 대역 에너지 · 플래시 박자 · 조화비 · 분류 정확도
#     (전부 크기 대칭이거나 거울에 불변인 양이다)
#   · 영향 있음 — ⊕/⊖ 스펙트럼 비대칭 · 접근 대 후퇴 · **ours ↔ PathSolver 의 부호 비교**
#     (앙각 스윕에서 우리 팔은 주로 ⊖, Sionna 팔은 주로 ⊕ 로 기울어 있었다 — 이 결함의 지문)
# ─────────────────────────────────────────────────────────────────────────────


def sbr_field_bistatic(mesh: Mesh, group_mat: dict, fc: float, u_i, u_s,
                       spacing=None, pad=1.15, cache_key=None, penetrate=True,
                       shell_groups=None, exit_vis=True,
                       ptd=False, ptd_pol="V", ptd_opts=None, *, grid_ref=None):
    """**바이스태틱 복소 산란장 E(û_i, û_s)** — `sbr_field` 의 바이스태틱 판(σ 가 아니라 E).

        E(û_i,û_s) = Σ_hits |Γ_i| · e^{jk(û_i+û_s)·p} · d²        σ = (4π/λ²)|E|²

    û_i = 표적→송신국, û_s = 표적→수신국 (둘 다 outward 단위벡터). û_s=û_i 면 모노스태틱이고
    `sbr_field` 와 **수치적으로 같다**(회귀 게이트: benchmark/verify_bistatic_field.py,
    원장 outputs/verify_bistatic_field.json).

    ■ 왜 이 함수가 따로 필요한가 — `rcs_sbr_multistatic` 을 그냥 쓰면 안 되는 이유
      그 함수는 마지막에 |E|² 로 **σ 를 내고 위상을 버린다**. 마이크로도플러(슬로타임 위상)는
      프레임 사이의 **상대 위상**이 신호 그 자체라 σ 로는 복원할 수 없다. 게다가 그 함수는
      jitter 오프셋마다 σ 를 **비코히어런트 평균**한다 — 위상을 쓰는 하류에서는 그 평균이
      의미를 바꾼다(서로 다른 격자의 장을 더하면 격자 위상차가 신호로 둔갑한다).
      → 여기서는 **jitter 를 두지 않는다**. `sbr_field` 와 같은 **단일 격자**(오프셋 0)다.
        절대레벨의 격자 산포(파일 상단 dither 실측)는 그대로 남는다 — 슬로타임 계열은 같은
        격자를 쓰므로 그 오차가 프레임 간 **공통 모드**로 들어가고, 마이크로도플러가 보는
        것은 그 차이다.

    ■ 물리는 `rcs_sbr_multistatic` 과 같다 (그 함수를 고치지 않고 그대로 따랐다)
      · 위상 e^{jk(û_i+û_s)·p} (모노 특수화 e^{j2k û·p} 와 정확히 겹친다)
      · 조명 게이트 (n̂·û_i > 1e-6) — 광선을 û_i 로 쏘므로 dA_투영=d² 상쇄가 성립
      · 수신 게이트 (n̂·û_s > 1e-6)
      · exit_vis(기본 True): 히트점마다 û_s 로 그림자광선 1발 — 수신기를 향하지만 **가려진**
        면을 뺀다. 모노(û_s=û_i)에서는 first-hit 이 이미 그 가림을 뺐으므로 no-op 다.
      · penetrate: 유전체 셸 왕복 투과 τ=1−|Γ|² 로 내부 금속을 코히어런트 가산(입사/출사 가림은
        **셸을 뺀 내부 씬**으로 판정 — 셸은 투과 대상이므로 가림체가 아니다).

    ■ Γ(θ) 각도의존 — **켜져 있다**(모노 경로와 같은 규약)
      `ANGLE_GAMMA` 가 True 면 `materials.gamma_shape(재질, fc, cosθ_i)` 를 곱한다. 각도는
      **국소 입사각** cosθ_i = n̂·û_i 다(표준 PO 의 Γ 는 입사각에서 평가한다). `sbr_field`·
      `rcs_sbr_batch` 와 같은 규약이므로 û_s=û_i 에서 비트 단위로 겹친다.
      ⚠ **`rcs_sbr_multistatic` 은 이 각도 모양을 곱하지 않는다**(그 함수는 matk 를 받고도 쓰지
        않는다). 따라서 ANGLE_GAMMA=True 에서 (4π/λ²)|E|² 는 그 함수의 σ 와 **일치하지 않는다** —
        차이는 재질 각도 모양뿐이고, 실측치는 outputs/verify_bistatic_field.json 의
        `sigma_cross_check.angle_gamma_on` 에 있다. 두 경로를 나란히 인용하지 말 것.

    ⚠ **적용범위 한계 — `rcs_sbr_multistatic` 의 것을 그대로 물려받는다**(계약이므로 코드에 남긴다):
      (1) **전방산란 무효**: β→180°(û_s≈−û_i)에서 조명게이트와 수신게이트가 상호배타 → E≡0.
          lit-PO 는 그림자복사(Babinet 전방로브 σ_fwd=4πA²/λ²)를 못 낸다 →
          **후방~중간 바이스태틱각(β≲90°급, 조명면 일부가 여전히 Rx 가시)에만 유효.**
      (2) **상반성 부분성립**: E(û_i,û_s) ↔ E(û_s,û_i) 가 볼록·강반사에선 거의 맞으나
          **비볼록 표적에서는 β≤90° 안에서도 깨진다**(û_i 단일 조명격자 재사용의 구조적 대가,
          격자세분으로 안 줄어듦). σ 레벨 실측은 outputs/sbr_defect_fixes.json `reciprocity`.
          ⚠ σ 의 `symmetrize` 같은 대칭화는 여기 **없다** — √(σσ) 는 위상을 정의하지 않는다.
      (3) 투과 출사경로(û_s 로 셸 재통과)는 입사 τ 로 근사(1차 투과) → 바이스태틱 비대칭을 더 키움.
      (4) obliquity 는 표준 PO 의 (n̂·û_i) 를 그대로 쓴다(대칭 √((n̂·û_i)(n̂·û_s)) 는 grazing
          조명면에서 이산 격자를 폭발시켜 rms 오차를 키웠다 → 폐기된 시도다).

    u_s : (3,) 이면 **복소 스칼라**를 돌려준다. (N,3) 이면 길이 N 복소 배열 —
      조명(광선추적)은 û_i 로만 결정되므로 **한 번만 쏘고** 수신방향마다 싼 위상합 +
      그림자광선 1발만 반복한다(멀티 Rx 패시브에서 그대로 쓰라고 넣은 경로다).

    ptd (기본 **False**) : True 면 같은 위상원점(bbox 중심)의 모서리 프린지 A_FW [m²] 를 더한
      복소장을 돌려준다(규약·게이트는 「PTD 배선」 절). ⚠ ptd=False 는 이 인자들이 없던 때와
      비트 단위로 같다.

    grid_ref (기본 **None**, keyword-only) : ⭐**얼린 광선 격자** — `sbr_field` 와 **같은 인자·
      같은 뜻·같은 코드**(`_grid_for`/`_ray_grid` 를 공유한다). 둘이 갈리면 û_s=û_i 모노 회귀
      게이트가 깨지므로 한 군데에서만 정한다. 격자는 조명 방향 û_i 로 깔리고, 위상 원점도
      얼린 ctr 이다(멀티 Rx 를 한 번의 조명으로 재사용하는 경로에도 그대로 걸린다)."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / DEFAULT_DIV
    u_i = np.asarray(u_i, float); u_i = u_i / np.linalg.norm(u_i)
    _one = np.asarray(u_s, float).ndim == 1
    #  ⚠ 정규화는 û_i 와 **같은 코드경로**(1-D np.linalg.norm)로 한다. 축방향 norm 은 BLAS 축약이
    #    달라 1 ulp 가 어긋날 수 있고, û_s=û_i 회귀 게이트가 그 1 ulp 때문에 게이트 경계에서
    #    히트 하나를 뒤집으면 «물리가 다른 것»처럼 보인다(측정하려는 것은 물리다).
    U_s = np.stack([v / np.linalg.norm(v) for v in np.atleast_2d(np.asarray(u_s, float))])

    scene, shapes, gammas, matk = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    _shells = _resolve_shells(group_names, group_mat, shell_groups)
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i, matk_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_shells)
        shptr_i = [mi.ShapePtr(s) for s in shapes_i]

    # ⭐ 격자(중심·반경·칸수)와 basis 는 `sbr_field` 와 **같은 함수**로 û_i 에서 만든다 — 다른
    #   basis 를 쓰면 히트점 집합이 미세하게 달라져 모노 회귀 게이트가 위상 수준에서 깨진다
    #   (격자는 물리가 아니라 규약이다). grid_ref 도 그래서 두 함수가 같이 받는다.
    ctr, Rout, n = _grid_for(mesh, d, pad, grid_ref, u_i, "sbr_field_bistatic")
    ray = _ray_grid(ctr, Rout, n, d, u_i)

    def _illum(sc, shptr, gam, mk=None):
        """조명 패스 — û_i 에만 의존한다(수신방향마다 재사용). 반환: (P절대, P−ctr, n̂, |Γ|, lit_i, si)."""
        si = sc.ray_intersect(ray)
        valid = np.asarray(si.is_valid()).astype(bool)
        P = np.asarray(mi.Point3f(si.p)).T
        Nn = np.asarray(mi.Vector3f(si.n)).T
        g = np.zeros(P.shape[0])
        which = np.full(P.shape[0], -1, int)
        for _i, (sp, gm) in enumerate(zip(shptr, gam)):
            hit = np.asarray(si.shape == sp).astype(bool)
            g = np.where(hit, gm, g)
            which = np.where(hit, _i, which)
        sgn = np.sign(Nn @ u_i); sgn[sgn == 0] = 1.0     # 법선을 광선 오는 쪽(û_i)으로 정렬
        Nn = Nn * sgn[:, None]
        cos_i = Nn @ u_i                                  # ⭐국소 입사 코사인
        lit_i = valid & (cos_i > 1e-6)                    # 조명 게이트
        if ANGLE_GAMMA and mk is not None:                # ⭐각도 모양 — 모노 경로와 같은 규약
            from materials import gamma_shape as _gsh
            for _i, _key in enumerate(mk):
                if _key is None:
                    continue
                sel = (which == _i) & lit_i
                if sel.any():
                    g[sel] = g[sel] * _gsh(_key, fc, cos_i[sel])
        return P, P - ctr, Nn, g, lit_i, valid, si

    P, Pc, Nn, g, lit_i, valid, si = _illum(scene, shape_ptrs, gammas, matk)
    if do_pen:
        tau = np.zeros(valid.shape[0])
        for i in shell_pos:
            tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                           1.0 - gammas[i] ** 2, tau)
        P2, Pc2, Nn2, g2, lit2_i, _, _ = _illum(scene_i, shptr_i, gammas_i, matk_i)
        lit2_i = lit2_i & (tau > 0)

    if ptd:
        _ptd_spacing_warn(d, lam, "sbr_field_bistatic")
        A_ptd = _ptd_edge_A(mesh, group_mat, fc, [(u_i, us) for us in U_s], ctr, scene,
                            pol=ptd_pol, cache_key=cache_key, opts=ptd_opts,
                            exit_vis=exit_vis, frozen=(grid_ref is not None))[0]

    out = np.zeros(len(U_s), complex)
    for j, us in enumerate(U_s):
        q = u_i + us                                      # 위상 벡터(모노면 정확히 2û)
        lit = lit_i & ((Nn @ us) > 1e-6)                  # + 수신 게이트(법선)
        if exit_vis:                                      # + û_s 로 나가는 길이 뚫려 있는가
            sel = np.where(lit)[0]
            if sel.size:
                lit = lit.copy()
                lit[sel] = _exit_visible(scene, P[sel], Nn[sel], us)
        E = np.sum(np.where(lit, g, 0.0) * np.exp(1j * k * (Pc @ q)))
        if do_pen:
            litp = lit2_i & ((Nn2 @ us) > 1e-6)
            if exit_vis:
                sel = np.where(litp)[0]
                if sel.size:
                    litp = litp.copy()
                    litp[sel] = _exit_visible(scene_i, P2[sel], Nn2[sel], us)
            E = E + np.sum(np.where(litp, tau * g2, 0.0) * np.exp(1j * k * (Pc2 @ q)))
        Etot = complex(E) * d * d                         # 면적분 [m²]
        if ptd:
            Etot = Etot + complex(A_ptd[j])               # + 모서리 프린지 [m²]
        out[j] = Etot
    return complex(out[0]) if _one else out


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

    scene, shapes, gammas, matk = _mi_scene_from_mesh(mesh, group_mat)
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
