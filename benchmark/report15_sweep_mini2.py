# -*- coding: utf-8 -*-
"""
report15_sweep_mini2.py — **mini2 를 Sionna 로 거리스윕** (본 실험)
================================================================================

묻는 것 (탐침 report15_probe.py 와 같은 두 갈래, 섞지 않는다)
  ① `Paths.doppler` 로 자동으로 나오나 → **아니다(확정)**. 속도가 객체당 강체 1벡터라
     회전을 표현할 자리가 없다. §A 에서 재확인만 한다.
  ② **로터 위상을 스텝하고 매번 재추적**해서 h(φ) 를 이어붙이면 나오나 → **열린 질문**.
     선례: WiFi-JEPA arXiv:2607.11064 — 프레임당 20 패스로 시간축 생성.

이 기체를 쓰는 이유
  mini2 는 **검증된 기준자**다(Das 실측 4기체 대조 ΔL −0.51 dB 로 1위, 형상 근거는
  DJI 공표 GLB WM161 축척 +0.07 %). 결과가 이상하면 "메쉬 탓인가 방법 탓인가" 를 이 기체가 가른다.

⭐ 근거리를 강조하는 이유 — 가까우면 (a) 드론이 큰 입체각을 차지해 광선이 많이 맞고
   (b) 부위별 경로가 분해되고 (c) Sionna 는 원래 구면 파면을 추적하므로 평면파 가정이
   깨지는 것이 불리하지 않다. 즉 **Sionna 에게 가장 유리한 조건**이다.

관측량 (⚠ 탐침에서 한 번 틀렸던 자리 — 반복 기록)
  `Paths.a` 는 **패스밴드 계수**라 전파 위상이 없다(imag 성분이 정확히 0). 위상은 τ 가 나른다.
      h = Σ_p a_p · exp(−j 2π f_c τ_p)          ← 코히런트 채널
      P = Σ_p |a_p|²                             ← **위상무관 에너지 채널**
  `Paths.cir()` 은 기본이 normalize_delays=True 라 절대위상 기준을 지운다 — 쓰지 않는다.

  ⭐ 두 채널을 **둘 다** 본다. 탐침 이후 확인된 사실 때문이다:
     확산채널의 **코히런트 합 h 는 광선예산에 대해 수렴하지 않는다**(경로수 ∝ spp 로 늘면
     |h| 가 함께 커진다). 반면 Σ|a|² 는 spp 를 192 배 늘려도 ±0.2 dB 안에서 상수다.
     즉 h 로 잰 변조는 "수렴하지 않는 양 위에서 잰 변조"다. §L 이 이것을 격자 위에서 정량화한다.

⭐⭐ 이 실험만의 결정적 대조 — **180° 대칭 널(null)**
  2날 프로펠러는 형상이 **180° 주기**다(탐침 실측: 180° 회전 후 최근접점 최대편차 3.1e−17 m).
  그래서 φ 를 **한 바퀴(360°) 64 스텝**으로 돌리면 h(φ) 는 원리적으로 **짝수 하모닉만** 가진다.
  → FFT 의 **홀수 빈 = 순수 잡음**, **짝수 빈 = 신호+잡음**. 같은 데이터 안에서, 같은 조건으로,
    잡음바닥이 공짜로 딸려 나온다. 이 대조는 시드·씬재조립 대조보다 강하다 —
    기하가 **집합으로 완전히 동일**한데 정점 색인만 다른 두 스냅샷을 비교하기 때문이다.

⛔ src/drones.py · src/drone_cad.py 는 **읽기만** 한다(어제 CAD 정정 미커밋).
⛔ 기존 산출물 덮어쓰기 금지 — 출력은 outputs/report15_sionna_sweep_mini2.json 하나.
⛔ 숫자는 전부 계산해서 JSON 에 담는다(손입력 금지).
본문·주석·print 한국어. 그림 없음(순수 측정).
"""
from __future__ import annotations

import argparse
import gc
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

from gpu import pick as _pick_gpu                                     # noqa: E402
_pick_gpu(verbose=True)                                               # ⚠ mitsuba import 전에!

import mitsuba as mi                                                  # noqa: E402
import sionna.rt as rt                                                # noqa: E402

# ⭐ 탐침의 계측 하네스를 그대로 재사용한다 — 관측량 정의가 갈라지면 두 실험을 나란히 못 놓는다.
import report15_probe as PB                                           # noqa: E402
from drones import (DRONES, DRONE_GROUP_MAT, build_drone,             # noqa: E402
                    pose_articulated, rotor_layout)
from materials import MATERIALS, material_params, gamma_bulk, gamma_po  # noqa: E402

C0 = 299792458.0
FC = PB.FC
LAM = PB.LAM
KEY = "mini2"

#  격자 — 근거리 강조
RANGES_M = (1.0, 3.0, 10.0)
#  자세: 정면 · 비스듬 · 측면 (하우스 기준 el=15°) + 탐침이 찾아낸 유일한 정반사 자세(el=0°)
ASPECTS = (
    dict(tag="front",   az=0.0,  el=15.0, why="하우스 기준 시선(정면·앙각 15°)"),
    dict(tag="oblique", az=45.0, el=15.0, why="비스듬 — 프롭 원판이 비대칭으로 보인다"),
    dict(tag="side",    az=90.0, el=15.0, why="측면 — 동체 장축이 시선에 직교"),
    dict(tag="hot",     az=0.0,  el=0.0,  why="탐침이 찾은 **유일한 정반사 보유 자세**(짐벌 렌즈면)"),
)
N_STEPS = 64                       # ⭐ 한 바퀴(360°)를 64 등분 — 180° 대칭 널을 쓰기 위해 **온바퀴**
SPP_REF = 256_000_000              # 균일 조건 & 경로수 맞춤의 기준 광선예산
SPP_MIN, SPP_MAX = 4_000_000, 3_072_000_000
SEEDS = (1, 2, 3, 4)
SPP_LADDER = (16_000_000, 64_000_000, 256_000_000, 1_024_000_000, 3_072_000_000)

from proc_scratch import proc_scratch                                  # noqa: E402
SCRATCH = proc_scratch(os.path.join(ROOT, "outputs", "meshes", "report15_sweep_mini2"))
OUT_JSON = os.path.join(ROOT, "outputs", "report15_sionna_sweep_mini2.json")


# --------------------------------------------------------------------------- #
#  직렬화 — 부피를 줄이되 정보는 남긴다
# --------------------------------------------------------------------------- #
def _f(x, nd=6):
    if x is None:
        return None
    v = float(x)
    if not math.isfinite(v):
        return None
    return float(f"%.{nd}g" % v)


def _fl(seq, nd=6):
    return [_f(x, nd) for x in seq]


# --------------------------------------------------------------------------- #
#  §0 — 물리 (거리별 원거리장 판정 · 위상 스텝 나이퀴스트 · 로터 재질)
# --------------------------------------------------------------------------- #
def sec0_physics(spec) -> dict:
    """⛔ 손입력 금지 — 전부 메쉬와 스펙에서 계산한다.

    · 원거리장 경계는 **무엇을 D 로 잡느냐에 따라 달라진다**. 세 가지를 다 낸다:
        D_prop  = 프로펠러 원판 지름       → '블레이드' 하나만 표적으로 볼 때
        D_horiz = 기체 최대 수평 크기      → 통상적인 관례 (프롭 포함)
        D_diag  = 3차원 대각               → 가장 보수적
      ⚠ 기체가 다르면 경계도 다르다 — 이 표는 **mini2 전용**이다.
    · RT 는 구면파를 추적하므로 근거리장이라고 계산이 틀리는 것은 아니다. 다만 그 결과를
      σ(RCS, 평면파·원거리장 정의) 로 환산해 인용하면 안 된다. 그 경계를 여기서 못 박는다.
    """
    m = build_drone(spec)
    V = np.asarray(m.v, float)
    b0, b1 = V.min(axis=0), V.max(axis=0)
    D_h = float(max(b1[0] - b0[0], b1[1] - b0[1]))
    D_3 = float(np.linalg.norm(b1 - b0))
    D_p = float(spec.prop_dia_mm) / 1000.0
    rpm = float(spec.hover_rpm)
    blades = int(spec.prop_blades)
    omega = 2.0 * math.pi * rpm / 60.0
    prop_R = D_p / 2.0
    v_tip = omega * prop_R
    f_tip = 2.0 * v_tip / LAM                       # 왕복 최대 마이크로도플러 [Hz]
    f_rev = rpm / 60.0                              # 회전수 [Hz] = 온바퀴 기록의 주파수 분해능
    f_flash = blades * f_rev                        # 블레이드 플래시율 [Hz]
    fs_slow = float(N_STEPS) * f_rev                # 등가 슬로타임 표본률 (온바퀴 N 스텝)

    def ff(D):
        return dict(D_m=float(D),
                    fraunhofer_m=float(2.0 * D * D / LAM),
                    reactive_m=float(0.62 * math.sqrt(max(D, 0.0) ** 3 / LAM)))

    bounds = dict(prop_disc=ff(D_p), horizontal=ff(D_h), diag3d=ff(D_3))
    per_range = {}
    for R in RANGES_M:
        row = dict(range_m=float(R))
        for nm, b in bounds.items():
            row[nm] = dict(
                fraunhofer_m=b["fraunhofer_m"],
                R_over_fraunhofer=float(R / b["fraunhofer_m"]),
                in_farfield=bool(R >= b["fraunhofer_m"]),
                in_reactive=bool(R < b["reactive_m"]))
        # 표적 폭에 걸친 **왕복 경로장 곡률 오차** = 2·D²/(8R) = D²/(4R) — 평면파 가정의 실제 대가
        row["curvature_err_m_horiz"] = float(D_h * D_h / (4.0 * R))
        row["curvature_phase_deg_horiz"] = float(360.0 * (D_h * D_h / (4.0 * R)) / LAM)
        row["curvature_phase_deg_prop"] = float(360.0 * (D_p * D_p / (4.0 * R)) / LAM)
        # 드론이 차지하는 입체각 비율 — 광선이 몇 개나 맞을지의 1차 예측 (∝ 1/R²)
        row["solid_angle_frac"] = float((math.pi * (D_h / 2.0) ** 2 / (R * R)) / (4.0 * math.pi))
        per_range[str(R)] = row

    alias = {}
    for N in sorted({16, 32, 64, N_STEPS}):
        alias[str(N)] = dict(
            n_steps=int(N), turn_deg=360.0,
            slow_fs_hz=float(N * f_rev), nyquist_hz=float(N * f_rev / 2.0),
            aliased=bool(N * f_rev / 2.0 < f_tip),
            margin=float((N * f_rev / 2.0) / f_tip),
            tip_travel_per_step_lambda=float(prop_R * (2.0 * math.pi / N) / LAM))

    return dict(
        drone=spec.key, name=spec.name, fc_hz=FC, lambda_m=LAM,
        span_m=_fl(b1 - b0), D_horizontal_m=D_h, D_diag3d_m=D_3, D_prop_disc_m=D_p,
        diagonal_spec_mm=float(spec.diagonal_mm),
        n_rotors=int(spec.num_rotors), prop_blades=blades,
        hover_rpm=rpm, omega_rad_s=omega, v_tip_ms=v_tip, v_tip_mach=float(v_tip / 343.0),
        f_tip_hz=f_tip, f_rev_hz=f_rev, f_flash_hz=f_flash,
        T_rev_s=float(60.0 / rpm),
        farfield_bounds=bounds, per_range=per_range,
        n_steps=int(N_STEPS), phase_step_deg=float(360.0 / N_STEPS),
        slow_fs_hz=fs_slow, slow_nyquist_hz=float(fs_slow / 2.0),
        doppler_bin_hz=f_rev, f_tip_in_bins=float(f_tip / f_rev),
        aliased=bool(fs_slow / 2.0 < f_tip), alias_by_n_steps=alias,
        mesh_period_deg=float(360.0 / blades),
        note_ko=("온바퀴 N 스텝 기록 → 슬로타임 표본률 N·f_rev, 도플러 빈 간격 f_rev. "
                 "2날 프롭은 형상 주기가 180° 라 h(φ) 는 **짝수 하모닉만** 가진다 "
                 "→ 홀수 빈은 그 자리에서 잡음바닥이 된다."))


def sec0_materials(spec) -> dict:
    """⭐ **이 기체의 로터가 어느 그룹으로 재질 배정되는지** — 블레이드 반사계수가 변조 크기를 정한다.

    ⚠ 갈라지는 지점: Sionna 는 (εr, σ, S) 를 쓰고 PO 는 실효 |Γ| 를 쓴다. 프로펠러는 두 값이
      다르다(벌크 프레넬 vs 얇은날개 실효). **이 실험은 Sionna 쪽이므로 (εr, σ, S) 가 지배한다.**
    """
    m = build_drone(spec)
    gl = np.asarray(m.g, dtype=object)
    F = np.asarray(m.f, int)
    V = np.asarray(m.v, float)
    # 그룹별 삼각형 면적 합 — 어느 부위가 반사면을 얼마나 차지하나
    tri = V[F]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    out, tot = {}, float(area.sum())
    for g in sorted(set(gl.tolist())):
        mk = DRONE_GROUP_MAT[g][0]
        er, sg, S = material_params(mk, FC)
        msk = (gl == g)
        gb = gamma_bulk(mk, FC)
        out[str(g)] = dict(
            mat_key=mk, itu=("itu" in MATERIALS[mk]),
            eps_r=_f(er), sigma_S_m=_f(sg), scattering_coefficient_S=_f(S),
            gamma_bulk=_f(gb), gamma_bulk_db=_f(20 * math.log10(gb + 1e-30)),
            gamma_po=_f(gamma_po(mk, FC)),
            n_tris=int(msk.sum()), area_m2=_f(float(area[msk].sum())),
            area_frac=_f(float(area[msk].sum()) / tot))
    pk = DRONE_GROUP_MAT["prop"][0]
    per, psg, pS = material_params(pk, FC)
    return dict(
        by_group=out, total_area_m2=_f(tot),
        rotor_group="prop", rotor_mat_key=pk,
        rotor_is_metal=bool(psg > 1e3),
        rotor_verdict=(f"mini2 의 로터는 그룹 'prop' → 재질 '{pk}' = **플라스틱 유전체**"
                       f"(εr={per:.2f}, σ={psg:.3g} S/m, 산란계수 S={pS:.2f}). 금속이 아니다. "
                       f"Sionna 가 보는 수직입사 벌크 |Γ| = {gamma_bulk(pk, FC):.4f} "
                       f"({20*math.log10(gamma_bulk(pk, FC)):.2f} dB) — 금속 "
                       f"({20*math.log10(gamma_bulk('metal', FC)):.2f} dB) 대비 "
                       f"{20*math.log10(gamma_bulk(pk, FC)/gamma_bulk('metal', FC)):.2f} dB. "
                       f"게다가 S={pS:.2f} 라 반사전력의 일부가 **확산**으로 빠진다 — "
                       f"블레이드 정반사 글린트를 기대할 근거가 재질 쪽에서도 약하다."),
        note_ko=("Sionna(전파)와 PO(RCS)는 같은 표(src/materials.py)에서 읽지만 프로펠러는 "
                 "벌크 프레넬(Sionna)과 얇은날개 실효 |Γ|(PO)가 다르다. 이 실험은 Sionna 쪽."))


# --------------------------------------------------------------------------- #
#  §A — ① 갈래 재확인 (짧게)
# --------------------------------------------------------------------------- #
def secA_doppler(spec, spp=32_000_000) -> dict:
    """SceneObject.velocity 의 **자유도**를 직접 세고, 정지 씬의 doppler 를 읽는다.
    주장이 아니라 관측이다. (탐침 §A 의 축약 재확인 — 결론이 흔들리지 않는지만 본다.)"""
    scene, _, d = PB.build_posed_scene(spec, 0.0, "A")
    g2 = PB.id_to_group(scene, spec.key)
    PB.place(scene, az=ASPECTS[0]["az"], el=ASPECTS[0]["el"], rng=3.0)
    r0 = PB.rt_echo(scene, spp, seed=1, diffuse=True, id2grp=g2)
    p = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                        diffuse_reflection=True, refraction=False,
                        samples_per_src=int(spp), max_num_paths_per_src=PB.MAX_PATHS, seed=1)
    _, _, dop0, _ = PB.unpack(p)
    dof = {}
    for nm, o in scene.objects.items():
        dof[nm] = int(np.asarray(o.velocity).reshape(-1).size)
    PB.drop_scratch(d)
    return dict(n_paths=int(r0["n_paths"]),
                doppler_nonzero=int(np.count_nonzero(dop0)),
                doppler_max_abs_hz=_f(float(np.max(np.abs(dop0))) if dop0.size else 0.0),
                velocity_dof_per_object=dict(sorted(dof.items())),
                max_dof=int(max(dof.values())) if dof else 0,
                verdict=("SceneObject.velocity 는 객체당 3성분(강체 1벡터)뿐 — 회전 자유도가 없다. "
                         "Paths.doppler 만으로는 블레이드 마이크로도플러가 원리적으로 불가. "
                         "그래서 ② 갈래(위상 스텝 + 재추적)만 남는다."))


# --------------------------------------------------------------------------- #
#  §B — 로터 위상 주기 확인 (⭐ 180° 대칭 널의 근거)
# --------------------------------------------------------------------------- #
def secB_period(spec, n_probe=8) -> dict:
    """2날 프롭의 형상 주기가 **정말** 180° 인가 — 최근접점 거리(집합 일치)로 확인한다.
    ⚠ 원소별 비교는 틀린다: 180° 회전은 정점 i 를 반대편 날의 대응점으로 보내므로
      배열 순서가 같아도 좌표는 다르다. **집합으로 같고 색인만 다른 것**이 요점이며,
      그 '색인만 다름' 이 곧 우리가 쓰려는 널의 성질이다."""
    dirs = [r["dir"] for r in rotor_layout(spec)]

    def mesh_at(ph):
        return pose_articulated(spec, rotor_phase_deg=[d * float(ph) for d in dirs])

    per = 360.0 / max(1, int(spec.prop_blades))
    rows, ok = [], True
    try:
        from scipy.spatial import cKDTree
    except Exception:
        cKDTree = None
    step = 360.0 / N_STEPS
    for i in range(n_probe):
        ph = i * step
        V0 = np.asarray(mesh_at(ph).v, float)
        V1 = np.asarray(mesh_at(ph + per).v, float)
        if cKDTree is not None and V0.shape == V1.shape:
            dev = float(cKDTree(V0).query(V1)[0].max())
        else:
            dev = float(np.abs(V1 - V0).max())
        idxdev = float(np.linalg.norm(V1 - V0, axis=1).max()) if V0.shape == V1.shape else None
        rows.append(dict(phase_deg=_f(ph), setwise_max_dev_m=_f(dev, 4),
                         elementwise_max_dev_m=_f(idxdev, 4)))
        ok = ok and dev < 1e-9
    # 위상축 전체에서 형상이 얼마나 움직이나 — ⚠ **두 가지를 구별해야 한다**
    #   · 색인별(elementwise) 이동 : 정점 i 가 얼마나 옮겨갔나. φ=180° 에서 최대(≈프롭 지름)지만
    #     그때 **형상은 그대로**다(반대편 날이 그 자리를 채운다) → 변조 크기의 척도가 **아니다**.
    #   · 집합별(Hausdorff) 편차   : 형상 자체가 φ=0 과 얼마나 다른가 → 이것이 진짜 기하 변화량.
    m0 = mesh_at(0.0)
    V0 = np.asarray(m0.v, float)
    F = np.asarray(m0.f, int)
    gl = np.asarray(m0.g, dtype=object)
    tree0 = cKDTree(V0) if cKDTree is not None else None
    mx_idx, mx_set, grp_mx, per_phase = 0.0, 0.0, {}, []
    for i in range(1, N_STEPS):
        V = np.asarray(mesh_at(i * step).v, float)
        dd = np.linalg.norm(V - V0, axis=1)
        mx_idx = max(mx_idx, float(dd.max()))
        hd = float(tree0.query(V)[0].max()) if tree0 is not None else None
        if hd is not None:
            mx_set = max(mx_set, hd)
        per_phase.append(dict(phase_deg=_f(i * step), elementwise_m=_f(float(dd.max()), 4),
                              hausdorff_m=_f(hd, 4)))
        for g in sorted(set(gl.tolist())):
            vi = np.unique(F[gl == g].ravel())
            grp_mx[str(g)] = max(grp_mx.get(str(g), 0.0), float(dd[vi].max()) if vi.size else 0.0)
    return dict(
        period_deg=float(per), n_probe=int(n_probe), rows=rows,
        period_symmetry_ok=bool(ok),
        max_setwise_dev_m=_f(max(r["setwise_max_dev_m"] for r in rows), 4),
        max_vertex_shift_m=_f(mx_idx), max_vertex_shift_lambda=_f(mx_idx / LAM),
        geom_excursion_m=_f(mx_set), geom_excursion_lambda=_f(mx_set / LAM),
        geom_excursion_roundtrip_phase_deg=_f(360.0 * 2.0 * mx_set / LAM),
        shift_by_phase=per_phase,
        max_shift_by_group_m={k: _f(v) for k, v in sorted(grp_mx.items())},
        note_ko=("집합 일치(≈0)이고 색인만 다르다 → h(φ) 와 h(φ+180°) 는 **같은 기하**의 두 스냅샷이다. "
                 "따라서 온바퀴 FFT 의 홀수 빈은 신호가 원리적으로 들어갈 수 없는 자리 = 잡음바닥. "
                 "⚠ geom_excursion(집합 Hausdorff) 이 '기하가 실제로 변한 크기'이고, "
                 "max_vertex_shift(색인별) 는 같은 형상의 정점 재배치까지 포함하므로 과대평가다."))


# --------------------------------------------------------------------------- #
#  셀 계측 — rt_echo 를 그대로 쓰되 필요한 값만 뽑는다
# --------------------------------------------------------------------------- #
def cell_run(scene, g2, spp, seed, diffuse):
    r = PB.rt_echo(scene, spp, seed, max_depth=1, diffuse=diffuse, id2grp=g2)
    inc = r.get("incoh_db")
    pinc = r.get("prop_incoh_db")
    return dict(
        n=int(r["n_paths"]), np_=int(r["n_prop"]),
        hr=r["h_re"], hi=r["h_im"], pr=r["hp_re"], pi=r["hp_im"],
        # 위상무관 에너지는 **선형**으로 담는다(평균이 물리적으로 옳은 쪽)
        e=(10.0 ** (inc / 10.0) if inc is not None else 0.0),
        pe=(10.0 ** (pinc / 10.0) if pinc is not None else 0.0),
        sec=r["sec"])


def cell_series(scene, g2, spp, seeds, diffuse):
    return [cell_run(scene, g2, spp, s, diffuse) for s in seeds]


# --------------------------------------------------------------------------- #
#  스펙트럼 — ⭐ 180° 대칭 널을 쓴 판정
# --------------------------------------------------------------------------- #
def spectrum(series_complex, series_power, f_rev, f_tip, thresh_db=6.0) -> dict:
    """온바퀴 N 스텝 계열 → 도플러 스펙트럼 + **짝수/홀수 빈 판정**.

    2날 프롭 형상은 180° 주기 → 신호는 **짝수 하모닉에만** 들어갈 수 있다.
      · 짝수 빈(k≠0) : 신호 + 잡음
      · 홀수 빈       : **잡음뿐** — 같은 데이터·같은 조건의 잡음바닥
    판정: 짝수 빈 평균전력 / 홀수 빈 평균전력. 1(0 dB)이면 변조 없음.

    스펙트럼 확산: 잡음바닥보다 thresh_db 이상 높은 **가장 높은 짝수 빈**을 f_extent 로 잡고,
    물리적 블레이드 팁 도플러 f_tip 과 비교한다. 진짜 블레이드 마이크로도플러라면 ±f_tip 까지
    에너지가 퍼져야 한다(교과서적 성질). k=2 (플래시 기본파)에만 있으면 '깜빡임'일 뿐이다.
    """
    def _one(x, kind):
        z = np.asarray(x)
        N = z.size
        Z = np.fft.fft(z) / N
        k = np.fft.fftfreq(N, d=1.0 / N).astype(int)
        P = np.abs(Z) ** 2
        dc = float(P[k == 0][0])
        ac = k != 0
        ev = ac & (k % 2 == 0)
        od = (k % 2 != 0)
        pe = float(P[ev].mean()) if ev.any() else 0.0
        po = float(P[od].mean()) if od.any() else 0.0
        ratio_db = (10 * math.log10(pe / po) if (pe > 0 and po > 0) else None)
        thr = po * (10.0 ** (thresh_db / 10.0))
        sig = ev & (P > thr)
        kext = int(np.abs(k[sig]).max()) if sig.any() else 0
        order = np.argsort(-P * ev)
        top = [dict(k=int(k[i]), f_hz=_f(k[i] * f_rev),
                    p_db=_f(10 * math.log10(P[i] + 1e-300), 5),
                    over_noise_db=_f(10 * math.log10(P[i] / po) if po > 0 else None, 4))
               for i in order[:6] if ev[i]]
        return dict(
            kind=kind, n=int(N),
            dc_db=_f(10 * math.log10(dc + 1e-300), 5),
            ac_total_db=_f(10 * math.log10(float(P[ac].sum()) + 1e-300), 5),
            ac_over_dc_db=_f(10 * math.log10(float(P[ac].sum()) / (dc + 1e-300)), 4),
            even_mean_db=_f(10 * math.log10(pe + 1e-300), 5),
            odd_mean_db=_f(10 * math.log10(po + 1e-300), 5),
            even_over_odd_db=_f(ratio_db, 4),
            n_even_above_noise=int(sig.sum()),
            k_extent=kext, f_extent_hz=_f(kext * f_rev),
            f_extent_over_f_tip=_f(kext * f_rev / f_tip if f_tip > 0 else None),
            top_even_bins=top,
            modulated=bool(ratio_db is not None and ratio_db > thresh_db),
            spectrum_k=[int(x) for x in k],
            spectrum_p_db=_fl(10 * np.log10(P + 1e-300), 5))

    out = dict(f_rev_hz=_f(f_rev), f_tip_hz=_f(f_tip), thresh_db=float(thresh_db))
    if series_complex is not None:
        out["coherent"] = _one(series_complex, "h = Σ a·exp(−j2πfτ)  (코히런트)")
    if series_power is not None:
        out["power"] = _one(series_power, "P = Σ|a|²  (위상무관 에너지)")
    return out


def db(x):
    """20log10|x| — 0 은 계열 최대의 1e−15 배로 바닥을 깐다(−300 dB).
    ⚠ 1e−300 을 그대로 쓰면 −6000 dB 가 나와 ptp·표준편차가 통째로 망가진다."""
    x = np.abs(np.asarray(x, dtype=complex))
    fl = float(x.max()) * 1e-15 if x.size and float(x.max()) > 0 else 1e-300
    return 20.0 * np.log10(np.maximum(x, fl))


def db10(x):
    """10log10(x) — 같은 바닥 규약(전력 계열용)."""
    x = np.asarray(x, float)
    fl = float(x.max()) * 1e-15 if x.size and float(x.max()) > 0 else 1e-300
    return 10.0 * np.log10(np.maximum(x, fl))


def summarize_cell(runs, f_rev, f_tip) -> dict:
    """(위상 × 시드) 배열 → 계열 통계 + 스펙트럼 판정.

    runs[i][j] = cell_run 결과 (i=위상, j=시드)
    · 신호계열 : 시드 **코히런트 평균** (복소평균) — 잡음이 √S 만큼 줄어든 계열
    · 잡음추정 : ① 같은 위상 안의 시드 산포(직접) ② 온바퀴 FFT 홀수 빈(⭐ 대칭 널)
    """
    n_ph, n_sd = len(runs), len(runs[0])
    H = np.array([[complex(r["hr"], r["hi"]) for r in row] for row in runs])
    Hp = np.array([[complex(r["pr"], r["pi"]) for r in row] for row in runs])
    E = np.array([[r["e"] for r in row] for row in runs], float)
    Ep = np.array([[r["pe"] for r in row] for row in runs], float)
    N = np.array([[r["n"] for r in row] for row in runs], float)
    Np = np.array([[r["np_"] for r in row] for row in runs], float)

    zbar, zpbar = H.mean(axis=1), Hp.mean(axis=1)
    ebar, epbar = E.mean(axis=1), Ep.mean(axis=1)

    # 위상내 시드 산포 = 재추적 잡음바닥 (직접 측정)
    seed_std_db = float(np.mean([np.std(db(H[i]), ddof=1) for i in range(n_ph)])) if n_sd > 1 else None
    seed_std_db_p = (float(np.mean([np.std(db(Hp[i]), ddof=1) for i in range(n_ph)]))
                     if n_sd > 1 else None)
    seed_std_e_db = (float(np.mean([np.std(db10(E[i]), ddof=1)
                                    for i in range(n_ph)])) if n_sd > 1 else None)

    amp = db(zbar)
    ampp = db(zpbar)
    edb = db10(ebar)
    epdb = db10(epbar)

    # ⭐ 180° 대칭 짝(φ, φ+180°) — 기하는 집합으로 동일, 색인만 다르다
    half = n_ph // 2
    pair_db = np.abs(amp[:half] - amp[half:])
    pair_e_db = np.abs(edb[:half] - edb[half:])
    pair_n = np.abs(N.mean(axis=1)[:half] - N.mean(axis=1)[half:])

    out = dict(
        n_phase=int(n_ph), n_seed=int(n_sd),
        n_paths_mean=_f(N.mean()), n_paths_std=_f(N.std(ddof=1)),
        n_paths_min=int(N.min()), n_paths_max=int(N.max()),
        n_paths_by_phase=_fl(N.mean(axis=1), 5),
        n_prop_mean=_f(Np.mean()), n_prop_min=int(Np.min()), n_prop_max=int(Np.max()),
        zero_path_cells=int(np.sum(N == 0)), zero_path_frac=_f(float(np.mean(N == 0)), 4),
        zero_prop_cells=int(np.sum(Np == 0)), zero_prop_frac=_f(float(np.mean(Np == 0)), 4),
        n_paths_behaviour=("모든 위상·시드에서 경로 0" if float(N.max()) == 0 else
                           ("껐다켜짐 (0 을 오간다)" if float(N.min()) == 0 else
                            "연속 (모든 칸에 경로 존재)")),
        # 계열
        amp_db=_fl(amp, 5), amp_db_ptp=_f(float(amp.max() - amp.min())),
        amp_db_std=_f(float(amp.std(ddof=1))),
        prop_amp_db=_fl(ampp, 5), prop_amp_db_ptp=_f(float(ampp.max() - ampp.min())),
        energy_db=_fl(edb, 5), energy_db_ptp=_f(float(edb.max() - edb.min())),
        energy_db_std=_f(float(edb.std(ddof=1))),
        prop_energy_db=_fl(epdb, 5), prop_energy_db_ptp=_f(float(epdb.max() - epdb.min())),
        # 잡음
        seed_std_db=_f(seed_std_db), prop_seed_std_db=_f(seed_std_db_p),
        seed_std_energy_db=_f(seed_std_e_db),
        # ⭐ 대칭 널
        sym_pair=dict(
            n_pairs=int(half),
            amp_db_mean=_f(float(pair_db.mean())), amp_db_max=_f(float(pair_db.max())),
            energy_db_mean=_f(float(pair_e_db.mean())), energy_db_max=_f(float(pair_e_db.max())),
            n_paths_mean=_f(float(pair_n.mean())), n_paths_max=_f(float(pair_n.max())),
            note=("기하가 집합으로 동일한 두 스냅샷의 차이 — 0 이 아니면 그만큼이 "
                  "'기하와 무관한 변동'(몬테카를로·색인 순서)이다.")),
        spectrum=spectrum(zbar, ebar, f_rev, f_tip),
        spectrum_prop=spectrum(zpbar, epbar, f_rev, f_tip),
        # ⭐ 광선예산 무관 형태: 코히런트장을 그 자리의 위상무관 에너지로 정규화한 것.
        #    |h| 자체는 spp 에 따라 √N 으로 커지지만 이 비는 스케일이 빠진다.
        spectrum_norm=spectrum(zbar / np.sqrt(np.maximum(ebar, 1e-300)), None, f_rev, f_tip),
    )
    # 판정 — 짝수/홀수 비 > 6 dB 이고, ptp 가 시드 잡음의 3σ/√S 를 넘는가
    se = (seed_std_db / math.sqrt(n_sd)) if seed_std_db else None
    out["ptp_over_seed_se"] = _f(out["amp_db_ptp"] / se if se else None)
    out["modulation_coherent"] = bool(out["spectrum"]["coherent"]["modulated"])
    out["modulation_power"] = bool(out["spectrum"]["power"]["modulated"])
    return out


# --------------------------------------------------------------------------- #
#  §L — ⭐ 광선예산 수렴 시험 (코히런트 h 가 수렴하는가)
# --------------------------------------------------------------------------- #
def secL_ladder(spec, ranges, aspects, ladder=SPP_LADDER, seeds=(1, 2)) -> dict:
    """spp 를 사다리로 올리며 |h| 와 Σ|a|² 를 잰다. **두 위상**(φ=0, φ=90°)에서 같이 재서
    변조 자체도 예산에 수렴하는지 본다.

    ⭐ 판정: log-log 기울기.
      · Σ|a|²  기울기 ≈ 0  → 위상무관 에너지는 **수렴한다**(추정량으로 성립).
      · |h|²   기울기 ≈ 1  → 코히런트 합은 경로수에 비례해 **커진다** = 랜덤워크·비수렴.
        비수렴이면 그 위에서 잰 변조의 **절대값**은 물리량이 아니다(상대비만 의미 있다).
    """
    phases = (0.0, 360.0 / N_STEPS * (N_STEPS // 4))     # φ=0 과 1/4 바퀴
    scenes = []
    for i, ph in enumerate(phases):
        sc, _, d = PB.build_posed_scene(spec, float(ph), f"L{i}")
        scenes.append((ph, sc, PB.id_to_group(sc, spec.key), d))
    out = {}
    for R in ranges:
        for asp in aspects:
            rows = []
            for spp in ladder:
                rec = dict(spp=int(spp))
                for j, (ph, sc, g2, _) in enumerate(scenes):
                    PB.place(sc, az=asp["az"], el=asp["el"], rng=R)
                    rr = [cell_run(sc, g2, spp, s, True) for s in seeds]
                    z = np.mean([complex(r["hr"], r["hi"]) for r in rr])
                    e = float(np.mean([r["e"] for r in rr]))
                    n = float(np.mean([r["n"] for r in rr]))
                    rec[f"phase{j}"] = dict(
                        phase_deg=_f(ph), n_paths=_f(n),
                        amp_db=_f(float(db(z))), energy_db=_f(10 * math.log10(e + 1e-300)),
                        coh_over_incoh_db=_f(float(db(z)) - 10 * math.log10(e + 1e-300)))
                rec["delta_amp_db"] = _f(rec["phase1"]["amp_db"] - rec["phase0"]["amp_db"])
                rec["delta_energy_db"] = _f(rec["phase1"]["energy_db"] - rec["phase0"]["energy_db"])
                rows.append(rec)
            x = np.log10([r["spp"] for r in rows])
            #  20log10|h| /10 = log10(|h|²)  ·  10log10Σ|a|² /10 = log10(Σ|a|²) — 둘 다 '전력의 상용로그'
            ya = np.array([r["phase0"]["amp_db"] for r in rows]) / 10.0
            ye = np.array([r["phase0"]["energy_db"] for r in rows]) / 10.0
            yn = np.log10(np.array([max(r["phase0"]["n_paths"], 1e-9) for r in rows]))
            sa = float(np.polyfit(x, ya, 1)[0]) if len(rows) > 1 else None
            se = float(np.polyfit(x, ye, 1)[0]) if len(rows) > 1 else None
            sn = float(np.polyfit(x, yn, 1)[0]) if len(rows) > 1 else None
            out[f"R{R:g}/{asp['tag']}"] = dict(
                range_m=float(R), aspect=asp["tag"], az_deg=asp["az"], el_deg=asp["el"],
                rows=rows,
                slope_coh_pow_per_decade=_f(sa),
                slope_incoh_pow_per_decade=_f(se),
                slope_n_paths_per_decade=_f(sn),
                coherent_converges=bool(sa is not None and abs(sa) < 0.2),
                incoherent_converges=bool(se is not None and abs(se) < 0.2),
                delta_amp_db_range=_f(float(np.ptp([r["delta_amp_db"] for r in rows]))),
                delta_energy_db_range=_f(float(np.ptp([r["delta_energy_db"] for r in rows]))))
    for _, _, _, d in scenes:
        PB.drop_scratch(d)
    return dict(
        ladder=[int(s) for s in ladder], seeds=[int(s) for s in seeds],
        phases_deg=_fl(phases), by_cell=out,
        note_ko=("기울기는 **decade 당 dB/10** 이 아니라 '광선예산 10 배당 전력 몇 decade' 로 읽는다. "
                 "1.0 이면 예산 10 배에 전력 10 배 = 랜덤워크 누적(비수렴), 0.0 이면 수렴."))


# --------------------------------------------------------------------------- #
#  §S — SBR 대조 (우리 커널이 같은 위상축에서 무엇을 내는가)
# --------------------------------------------------------------------------- #
def secS_sbr(spec, aspects, f_rev, f_tip) -> dict:
    """⭐ **대조군**: 같은 메쉬·같은 위상축을 우리 SBR+PO 커널에 넣으면 무엇이 나오나.

    ⚠ 이것은 '정답'이 아니다. 우리 커널도 근사(SBR+PO, 단일산란, 평면파 원거리장 모노스태틱)다.
      여기 쓰는 이유는 오직 하나 — **같은 기하에서 블레이드 변조가 나올 수 있는 형태가 어떤 것인지**
      를 옆에 놓기 위해서다. 거리 의존은 없다(원거리장 평면파).
    """
    try:
        from rcs_sbr import sbr_field, grid_ref_for_slowtime
    except Exception as e:
        return dict(available=False, error=f"{type(e).__name__}: {e}")
    gmat = {g: mt for g, (mt, _) in DRONE_GROUP_MAT.items()}
    dirs = [r["dir"] for r in rotor_layout(spec)]
    step = 360.0 / N_STEPS
    # ⭐ 광선 격자를 얼린다 — 이 팔도 φ 마다 값을 늘어놓는 **슬로타임 열**이다.
    #   격자가 자세의 bbox 에서 나오면 위상 원점(ctr)과 표본 집합(Rout·n)이 φ 마다 바뀌어
    #   블레이드 변조에 가짜 변조가 섞인다. 판은 자세에 무관하므로 자세 루프 밖에서 한 번 만든다.
    #   SIONNA2_FREEZE_GRID=0 이면 None → 옛 동작.
    gref = grid_ref_for_slowtime(
        lambda p: pose_articulated(spec, rotor_phase_deg=p), dirs, FC)
    out = {}
    for asp in aspects:
        u = PB.look_dir(asp["az"], asp["el"])
        E = np.zeros(N_STEPS, complex)
        t0 = time.time()
        for i in range(N_STEPS):
            mesh = pose_articulated(spec, rotor_phase_deg=[d * (i * step) for d in dirs])
            E[i] = complex(sbr_field(mesh, gmat, FC, u, grid_ref=gref))
        a = db(E)
        out[asp["tag"]] = dict(
            az_deg=asp["az"], el_deg=asp["el"], sec=_f(time.time() - t0),
            amp_db=_fl(a, 5), amp_db_ptp=_f(float(a.max() - a.min())),
            spectrum=spectrum(E, np.abs(E) ** 2, f_rev, f_tip))
        print(f"    [SBR/{asp['tag']}] ptp={a.max()-a.min():.2f} dB  "
              f"짝/홀={out[asp['tag']]['spectrum']['coherent']['even_over_odd_db']} dB  "
              f"확산={out[asp['tag']]['spectrum']['coherent']['f_extent_hz']} Hz "
              f"({out[asp['tag']]['spectrum']['coherent']['f_extent_over_f_tip']}×f_tip)  "
              f"[{time.time()-t0:.0f}s]", flush=True)
    return dict(available=True, engine="rcs_sbr.sbr_field (우리 커널, SBR+PO 단일산란)",
                grid_frozen=bool(gref is not None),
                grid_ref=(gref.asjson() if gref is not None else None),
                by_aspect=out,
                caveat=("대조군이지 정답이 아니다. 평면파 원거리장 모노스태틱이라 거리 의존이 없고, "
                        "Sionna 와 달리 산란적분을 우리가 직접 편다."))


# --------------------------------------------------------------------------- #
#  본 스윕
# --------------------------------------------------------------------------- #
def main():
    global N_STEPS
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=N_STEPS)
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--no-sbr", action="store_true")
    ap.add_argument("--no-null", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()

    N_STEPS = int(a.steps)
    seeds = tuple(range(1, a.seeds + 1))
    ranges = RANGES_M
    aspects = ASPECTS
    if a.quick:
        N_STEPS = 8
        ranges = (3.0,)
        aspects = ASPECTS[:2]
        seeds = seeds[:2]

    os.makedirs(SCRATCH, exist_ok=True)
    spec = DRONES[KEY]
    t_all = time.time()

    J = dict(meta=dict(
        script="benchmark/report15_sweep_mini2.py",
        drone=KEY,
        question=("Sionna PathSolver 가 로터를 돌려가며 다시 추적했을 때 "
                  "블레이드 마이크로도플러를 내는가 — 거리 1·3·10 m 스윕"),
        observable=("h = Σ_p a_p·exp(−j2πf_c·τ_p) (코히런트) · P = Σ_p|a_p|² (위상무관 에너지). "
                    "Paths.a 는 패스밴드라 전파위상이 없다. Paths.cir() 은 "
                    "normalize_delays=True 로 절대위상을 지우므로 쓰지 않았다."),
        why_this_airframe=("mini2 = 검증된 기준자(Das 실측 4기체 대조 ΔL −0.51 dB 1위, "
                           "형상 근거 DJI 공표 GLB WM161 축척 +0.07 %) — "
                           "이상이 나오면 메쉬 탓인지 방법 탓인지 이 기체가 가른다."),
        why_near_range=("가까우면 (a) 입체각이 커서 광선이 많이 맞고 (b) 부위 경로가 분해되고 "
                        "(c) Sionna 는 원래 구면파를 추적한다 → Sionna 에게 가장 유리한 조건."),
        null_design=("⭐ 2날 프롭은 형상이 180° 주기 → 온바퀴 64 스텝 FFT 의 **홀수 빈은 "
                     "신호가 원리적으로 들어갈 수 없는 자리** = 같은 데이터 안의 잡음바닥."),
        fc_hz=FC, lambda_m=LAM, max_depth=1, baseline_m=PB.BASELINE_M,
        ranges_m=list(ranges), aspects=[dict(a) for a in aspects],
        n_phase_steps=int(N_STEPS), turn_deg=360.0, seeds=list(seeds),
        spp_ref=int(SPP_REF), spp_conditions=["uniform", "matched"],
        max_paths=PB.MAX_PATHS,
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        materials="production per-group (DRONE_GROUP_MAT)",
        prior="WiFi-JEPA arXiv:2607.11064 — frame 당 20 pass 로 시간축 생성",
        related=["outputs/report15_probe.json", "outputs/facet_count.json"],
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")))

    def _save():
        with open(OUT_JSON, "w") as f:
            json.dump(J, f, ensure_ascii=False, indent=1)

    print(f"\n══ {KEY} ({spec.name}) — Sionna 거리스윕 ══", flush=True)

    # ---------------- §0 물리 · 재질 ----------------
    J["physics"] = sec0_physics(spec)
    ph = J["physics"]
    print(f"  λ={LAM*1000:.2f} mm  f_rev={ph['f_rev_hz']:.2f} Hz  f_flash={ph['f_flash_hz']:.1f} Hz  "
          f"f_tip={ph['f_tip_hz']:.1f} Hz  (= {ph['f_tip_in_bins']:.2f} 빈)", flush=True)
    for R in ranges:
        r = ph["per_range"][str(R)]
        print(f"    R={R:5.1f} m | 2D²/λ  prop {r['prop_disc']['fraunhofer_m']:.3f} "
              f"/ horiz {r['horizontal']['fraunhofer_m']:.3f} "
              f"/ diag3d {r['diag3d']['fraunhofer_m']:.3f} m  →  far-field "
              f"prop {'O' if r['prop_disc']['in_farfield'] else 'X'} "
              f"horiz {'O' if r['horizontal']['in_farfield'] else 'X'} "
              f"diag {'O' if r['diag3d']['in_farfield'] else 'X'}  "
              f"| 곡률위상 {r['curvature_phase_deg_horiz']:.0f}°", flush=True)
    J["materials"] = sec0_materials(spec)
    print("  " + J["materials"]["rotor_verdict"].replace("\n", " "), flush=True)

    # ---------------- §A 도플러 재확인 ----------------
    print("  §A  Paths.doppler 재확인 …", flush=True)
    J["A_doppler"] = secA_doppler(spec)
    print(f"      velocity 자유도/객체 = {J['A_doppler']['max_dof']}, "
          f"정지 씬 doppler≠0 경로 = {J['A_doppler']['doppler_nonzero']}", flush=True)

    # ---------------- §B 주기 ----------------
    print("  §B  로터 위상 주기 (180° 대칭 널의 근거) …", flush=True)
    J["B_period"] = secB_period(spec)
    print(f"      집합 최대편차 {J['B_period']['max_setwise_dev_m']} m → 주기 "
          f"{J['B_period']['period_deg']}° {'확인' if J['B_period']['period_symmetry_ok'] else '실패'}"
          f" · 기하 변화량(집합 Hausdorff) {J['B_period']['geom_excursion_m']} m "
          f"= {J['B_period']['geom_excursion_lambda']} λ "
          f"(왕복 위상 {J['B_period']['geom_excursion_roundtrip_phase_deg']}°) "
          f"· 색인별 최대이동 {J['B_period']['max_vertex_shift_m']} m", flush=True)
    _save()

    # ---------------- 보정: 경로수 맞춤 spp ----------------
    print("  §K  경로수 맞춤 보정 (거리·자세마다 광선예산을 다르게) …", flush=True)
    sc0, _, d0 = PB.build_posed_scene(spec, 0.0, "K")
    g20 = PB.id_to_group(sc0, KEY)
    calib = {}
    ref_n = None
    for R in ranges:
        for asp in aspects:
            PB.place(sc0, az=asp["az"], el=asp["el"], rng=R)
            r = cell_run(sc0, g20, SPP_REF, 1, True)
            calib[f"R{R:g}/{asp['tag']}"] = dict(range_m=float(R), aspect=asp["tag"],
                                                 n_at_ref=int(r["n"]))
            if R == 3.0 and asp["tag"] == "front":
                ref_n = int(r["n"])
    if not ref_n:
        ref_n = max(1, int(np.median([v["n_at_ref"] for v in calib.values()])))
    for k, v in calib.items():
        s = SPP_REF * ref_n / max(1, v["n_at_ref"])
        v["spp_matched"] = int(min(SPP_MAX, max(SPP_MIN, round(s))))
        v["n_target"] = int(ref_n)
        print(f"      {k:>16}  n@ref={v['n_at_ref']:6d}  →  맞춤 spp={v['spp_matched']:>13,}",
              flush=True)
    PB.drop_scratch(d0)
    del sc0
    gc.collect()
    J["calibration"] = dict(spp_ref=int(SPP_REF), n_target=int(ref_n), by_cell=calib,
                            note_ko=("거리가 멀면 드론이 차지하는 입체각이 작아 같은 spp 로도 "
                                     "경로가 훨씬 적게 잡힌다(∝1/R²). 'uniform' 조건은 광선예산을, "
                                     "'matched' 조건은 **경로수**를 맞춘다 — 둘 다 남겨야 "
                                     "'거리 탓'과 '광선예산 탓'이 갈린다."))
    _save()

    # ---------------- §L 광선예산 수렴 ----------------
    print("  §L  ⭐ 광선예산 수렴 시험 (코히런트 합이 수렴하는가) …", flush=True)
    J["L_ladder"] = secL_ladder(spec, ranges, aspects)
    for k, v in J["L_ladder"]["by_cell"].items():
        print(f"      {k:>16}  기울기  |h|² {v['slope_coh_pow_per_decade']:+.3f} / "
              f"Σ|a|² {v['slope_incoh_pow_per_decade']:+.3f} / n {v['slope_n_paths_per_decade']:+.3f}"
              f"  → 코히런트 수렴={v['coherent_converges']}, 에너지 수렴={v['incoherent_converges']}",
              flush=True)
    _save()

    # ---------------- §G 본 격자 스윕 ----------------
    print(f"  §G  본 격자: {len(ranges)} 거리 × {len(aspects)} 자세 × {N_STEPS} 위상 "
          f"× 2 예산조건 × 2 모드 × {len(seeds)} 시드 …", flush=True)
    step = 360.0 / N_STEPS
    #  결과 통 — grid[cond][mode][cellkey] = 위상 리스트 of 시드 리스트
    grid = {c: {m: {k: [] for k in calib} for m in ("spec", "prod")}
            for c in ("uniform", "matched")}
    t_g = time.time()
    for i in range(N_STEPS):
        phi = i * step
        scene, _, dd = PB.build_posed_scene(spec, float(phi), f"G{i:03d}")
        g2 = PB.id_to_group(scene, KEY)
        for R in ranges:
            for asp in aspects:
                ck = f"R{R:g}/{asp['tag']}"
                PB.place(scene, az=asp["az"], el=asp["el"], rng=R)
                spp_u = SPP_REF
                spp_m = calib[ck]["spp_matched"]
                for cond, spp in (("uniform", spp_u), ("matched", spp_m)):
                    if cond == "matched" and spp == spp_u:
                        for mode in ("spec", "prod"):
                            grid["matched"][mode][ck].append(grid["uniform"][mode][ck][-1])
                        continue
                    for mode, diff in (("spec", False), ("prod", True)):
                        grid[cond][mode][ck].append(cell_series(scene, g2, spp, seeds, diff))
        PB.drop_scratch(dd)
        del scene
        if i % 8 == 0:
            gc.collect()
        if i % 4 == 0 or i == N_STEPS - 1:
            el = time.time() - t_g
            print(f"      φ={phi:7.2f}°  [{i+1}/{N_STEPS}]  {el:6.0f}s  "
                  f"(예상 총 {el/(i+1)*N_STEPS:.0f}s)", flush=True)
    print(f"      §G 완료 {time.time()-t_g:.0f}s", flush=True)

    # ---------------- §N 널 계열 (같은 위상, 새 시드) ----------------
    null = {}
    if not a.no_null:
        print("  §N  널 계열: φ 를 **고정**하고 시드만 새로 뽑아 같은 길이의 계열을 만든다 …",
              flush=True)
        scn, _, dn = PB.build_posed_scene(spec, 0.0, "N")
        g2n = PB.id_to_group(scn, KEY)
        t_n = time.time()
        for R in ranges:
            for asp in aspects:
                ck = f"R{R:g}/{asp['tag']}"
                PB.place(scn, az=asp["az"], el=asp["el"], rng=R)
                spp = calib[ck]["spp_matched"]
                rows = []
                for i in range(N_STEPS):
                    sd = [10_000 + i * len(seeds) + j for j in range(len(seeds))]
                    rows.append([cell_run(scn, g2n, spp, s, True) for s in sd])
                null[ck] = rows
        PB.drop_scratch(dn)
        del scn
        gc.collect()
        print(f"      §N 완료 {time.time()-t_n:.0f}s", flush=True)

    # ---------------- 요약 · 판정 ----------------
    print("  §V  판정 …", flush=True)
    f_rev, f_tip = ph["f_rev_hz"], ph["f_tip_hz"]
    cells = {}
    for cond in ("uniform", "matched"):
        for mode in ("spec", "prod"):
            for ck, rows in grid[cond][mode].items():
                key = f"{cond}/{mode}/{ck}"
                Nn = np.array([[r["n"] for r in row] for row in rows], float)
                if float(Nn.max()) == 0:
                    cells[key] = dict(
                        condition=cond, mode=mode, cell=ck,
                        range_m=calib[ck]["range_m"], aspect=calib[ck]["aspect"],
                        spp=int(SPP_REF if cond == "uniform" else calib[ck]["spp_matched"]),
                        n_phase=int(N_STEPS), n_seed=len(seeds),
                        n_paths_mean=0.0, zero_path_frac=1.0,
                        n_paths_behaviour="모든 위상·시드에서 경로 0",
                        empty_channel=True,
                        modulation_coherent=False, modulation_power=False,
                        verdict="경로 없음 — 변조를 논할 수 없다")
                    continue
                s = summarize_cell(rows, f_rev, f_tip)
                s.update(condition=cond, mode=mode, cell=ck, empty_channel=False,
                         range_m=calib[ck]["range_m"], aspect=calib[ck]["aspect"],
                         az_deg=next(x["az"] for x in aspects if x["tag"] == calib[ck]["aspect"]),
                         el_deg=next(x["el"] for x in aspects if x["tag"] == calib[ck]["aspect"]),
                         spp=int(SPP_REF if cond == "uniform" else calib[ck]["spp_matched"]))
                cells[key] = s
    null_cells = {}
    for ck, rows in null.items():
        s = summarize_cell(rows, f_rev, f_tip)
        s.update(cell=ck, kind="null(φ 고정 · 시드만 새로)",
                 range_m=calib[ck]["range_m"], aspect=calib[ck]["aspect"],
                 spp=int(calib[ck]["spp_matched"]))
        null_cells[ck] = s

    J["grid_cells"] = cells
    J["null_cells"] = null_cells
    #  원자료 — (거리, 자세, 위상) 마다 복소 a 와 경로수 (지시사항)
    J["raw"] = dict(
        note_ko=("각 (조건, 모드, 거리·자세) 에 대해 [위상][시드] 배열. "
                 "hr/hi = 코히런트 h 실·허, pr/pi = 프롭경유 h, e/pe = Σ|a|² (선형), "
                 "n = 표적경유 경로수, np = 프롭경유 경로수."),
        phase_deg=_fl([i * step for i in range(N_STEPS)]),
        seeds=list(seeds),
        by_key={f"{c}/{m}/{ck}": dict(
            hr=[[_f(r["hr"]) for r in row] for row in rows],
            hi=[[_f(r["hi"]) for r in row] for row in rows],
            pr=[[_f(r["pr"]) for r in row] for row in rows],
            pi=[[_f(r["pi"]) for r in row] for row in rows],
            e=[[_f(r["e"]) for r in row] for row in rows],
            pe=[[_f(r["pe"]) for r in row] for row in rows],
            n=[[int(r["n"]) for r in row] for row in rows],
            np=[[int(r["np_"]) for r in row] for row in rows])
            for c in grid for m in grid[c] for ck, rows in grid[c][m].items()})
    _save()

    # ---------------- §S SBR 대조 ----------------
    if not a.no_sbr:
        print("  §S  SBR 대조군 (같은 위상축, 우리 커널) …", flush=True)
        J["S_sbr"] = secS_sbr(spec, aspects, f_rev, f_tip)
    _save()

    # ---------------- 헤드라인 ----------------
    J["headline"] = headline(J, ranges, aspects, seeds)
    J["meta"]["seconds_total"] = _f(time.time() - t_all)
    _save()
    print(f"\n✅ 저장 → {OUT_JSON}   ({J['meta']['seconds_total']:.0f}s)", flush=True)
    for ln in J["headline"]["summary_lines"]:
        print("   " + ln, flush=True)
    return J


def headline(J, ranges, aspects, seeds) -> dict:
    """⭐ 인용 가능한 요약 — 소비자가 손으로 숫자를 고르지 않게 여기서 정한다."""
    C = J["grid_cells"]
    ph = J["physics"]
    prod = {k: v for k, v in C.items() if v["mode"] == "prod"}
    spec_ = {k: v for k, v in C.items() if v["mode"] == "spec"}

    n_spec_cells = len(spec_)
    n_spec_nonempty = sum(1 for v in spec_.values() if not v.get("empty_channel"))
    spec_cells_with = sorted(k for k, v in spec_.items() if not v.get("empty_channel"))
    # 정반사 채널의 (거리,자세,위상,시드) 칸 중 경로가 있는 칸 비율
    tot = 0
    hit = 0
    for k, v in J["raw"]["by_key"].items():
        if "/spec/" not in k:
            continue
        arr = np.array(v["n"])
        tot += arr.size
        hit += int((arr > 0).sum())

    def pick(cond, mode, R, tag):
        return C.get(f"{cond}/{mode}/R{R:g}/{tag}")

    by_range = {}
    for R in ranges:
        rows = {}
        for asp in aspects:
            for cond in ("uniform", "matched"):
                v = pick(cond, "prod", R, asp["tag"])
                if not v or v.get("empty_channel"):
                    continue
                sp = v["spectrum"]["coherent"]
                spp_ = v["spectrum"]["power"]
                snm = v["spectrum_norm"]["coherent"]
                spr = v["spectrum_prop"]["coherent"]
                rows[f"{cond}/{asp['tag']}"] = dict(
                    spp=v["spp"], n_paths_mean=v["n_paths_mean"],
                    zero_path_frac=v["zero_path_frac"],
                    n_paths_behaviour=v["n_paths_behaviour"],
                    amp_ptp_db=v["amp_db_ptp"], seed_std_db=v["seed_std_db"],
                    sym_pair_amp_db=v["sym_pair"]["amp_db_mean"],
                    coh_even_over_odd_db=sp["even_over_odd_db"],
                    coh_f_extent_hz=sp["f_extent_hz"],
                    coh_f_extent_over_f_tip=sp["f_extent_over_f_tip"],
                    coh_modulated=sp["modulated"],
                    pow_ptp_db=v["energy_db_ptp"], pow_seed_std_db=v["seed_std_energy_db"],
                    pow_even_over_odd_db=spp_["even_over_odd_db"],
                    pow_f_extent_hz=spp_["f_extent_hz"],
                    pow_f_extent_over_f_tip=spp_["f_extent_over_f_tip"],
                    pow_modulated=spp_["modulated"],
                    norm_even_over_odd_db=snm["even_over_odd_db"],
                    norm_f_extent_over_f_tip=snm["f_extent_over_f_tip"],
                    norm_ac_over_dc_db=snm["ac_over_dc_db"],
                    prop_even_over_odd_db=spr["even_over_odd_db"],
                    prop_f_extent_over_f_tip=spr["f_extent_over_f_tip"],
                    prop_ptp_db=v["prop_amp_db_ptp"],
                    n_prop_mean=v["n_prop_mean"], zero_prop_frac=v["zero_prop_frac"])
        by_range[str(R)] = rows

    nulls = J.get("null_cells") or {}
    null_even_odd = [v["spectrum"]["coherent"]["even_over_odd_db"] for v in nulls.values()
                     if v.get("spectrum")]
    lad = J.get("L_ladder", {}).get("by_cell", {})
    sl_c = [v["slope_coh_pow_per_decade"] for v in lad.values()
            if v.get("slope_coh_pow_per_decade") is not None]
    sl_e = [v["slope_incoh_pow_per_decade"] for v in lad.values()
            if v.get("slope_incoh_pow_per_decade") is not None]

    sbr = (J.get("S_sbr") or {}).get("by_aspect") or {}
    sbr_row = {k: dict(ptp_db=v["amp_db_ptp"],
                       even_over_odd_db=v["spectrum"]["coherent"]["even_over_odd_db"],
                       f_extent_hz=v["spectrum"]["coherent"]["f_extent_hz"],
                       f_extent_over_f_tip=v["spectrum"]["coherent"]["f_extent_over_f_tip"])
               for k, v in sbr.items()}

    pw = [v for v in prod.values() if not v.get("empty_channel")]
    n_mod_coh = sum(1 for v in pw if v["spectrum"]["coherent"]["modulated"])
    n_mod_pow = sum(1 for v in pw if v["spectrum"]["power"]["modulated"])
    ext = [v["spectrum"]["coherent"]["f_extent_over_f_tip"] for v in pw
           if v["spectrum"]["coherent"]["f_extent_over_f_tip"] is not None]

    def _m(v, nd=3):
        return ("%.*f" % (nd, float(np.median(v)))) if len(v) else "n/a"

    npath_line = " / ".join(
        str((by_range[str(R)].get("uniform/front") or {}).get("n_paths_mean")) for R in ranges)
    lines = [
        f"① Paths.doppler: velocity 자유도 = {J['A_doppler']['max_dof']} (강체 1벡터) → 회전 불가, 재확인.",
        f"로터 재질: 그룹 'prop' → '{J['materials']['rotor_mat_key']}' "
        f"= 플라스틱 유전체(금속 아님), |Γ|벌크 "
        f"{J['materials']['by_group']['prop']['gamma_bulk_db']} dB, S="
        f"{J['materials']['by_group']['prop']['scattering_coefficient_S']}.",
        f"정반사 채널: {tot} 칸 중 경로가 있는 칸 {hit} "
        f"({100.0*hit/max(1,tot):.2f} %) — 비어 있는 셀 {n_spec_cells-n_spec_nonempty}/{n_spec_cells}.",
        f"확산 채널 경로수(front, spp={SPP_REF:,} 고정): R=1/3/10 m → {npath_line}  (∝1/R²).",
        f"광선예산 수렴: |h|² 기울기 중앙값 {_m(sl_c)} (1.0 = 랜덤워크 비수렴), "
        f"Σ|a|² 기울기 중앙값 {_m(sl_e)} (0.0 = 수렴).",
        f"180° 대칭 널: 확산·프로덕션 셀 {len(pw)} 개 중 코히런트 변조 유의 {n_mod_coh}, "
        f"에너지 변조 유의 {n_mod_pow}.",
        f"스펙트럼 확산: 짝수빈 확산 한계 / f_tip 의 중앙값 {_m(ext)} "
        f"(1.0 이어야 교과서적 블레이드 마이크로도플러).",
        f"널 계열(φ 고정·시드만) 짝/홀 중앙값 {_m(null_even_odd, 2)} dB "
        f"(0 dB 이어야 널이 널답다).",
    ]
    return dict(
        drone=KEY, name=DRONES[KEY].name,
        f_tip_hz=ph["f_tip_hz"], f_flash_hz=ph["f_flash_hz"], f_rev_hz=ph["f_rev_hz"],
        doppler_bin_hz=ph["doppler_bin_hz"], n_steps=int(N_STEPS),
        aliased=ph["aliased"], alias_margin=ph["alias_by_n_steps"][str(N_STEPS)]["margin"],
        farfield_by_range={str(R): dict(
            prop_disc_m=ph["per_range"][str(R)]["prop_disc"]["fraunhofer_m"],
            horizontal_m=ph["per_range"][str(R)]["horizontal"]["fraunhofer_m"],
            diag3d_m=ph["per_range"][str(R)]["diag3d"]["fraunhofer_m"],
            in_farfield_horizontal=ph["per_range"][str(R)]["horizontal"]["in_farfield"],
            in_farfield_diag3d=ph["per_range"][str(R)]["diag3d"]["in_farfield"],
            curvature_phase_deg=ph["per_range"][str(R)]["curvature_phase_deg_horiz"])
            for R in ranges},
        rotor_material=dict(
            group="prop", mat_key=J["materials"]["rotor_mat_key"],
            is_metal=J["materials"]["rotor_is_metal"],
            eps_r=J["materials"]["by_group"]["prop"]["eps_r"],
            sigma_S_m=J["materials"]["by_group"]["prop"]["sigma_S_m"],
            S=J["materials"]["by_group"]["prop"]["scattering_coefficient_S"],
            gamma_bulk_db=J["materials"]["by_group"]["prop"]["gamma_bulk_db"],
            area_frac=J["materials"]["by_group"]["prop"]["area_frac"]),
        mesh_period_deg=J["B_period"]["period_deg"],
        mesh_period_verified=J["B_period"]["period_symmetry_ok"],
        geom_excursion_lambda=J["B_period"]["geom_excursion_lambda"],
        geom_excursion_roundtrip_phase_deg=J["B_period"]["geom_excursion_roundtrip_phase_deg"],
        specular_cells_total=int(tot), specular_cells_with_paths=int(hit),
        specular_cell_frac=_f(hit / max(1, tot), 4),
        specular_channel_nonempty_cells=spec_cells_with,
        ladder_slope_coh_median=_f(float(np.median(sl_c)) if sl_c else None),
        ladder_slope_incoh_median=_f(float(np.median(sl_e)) if sl_e else None),
        coherent_sum_converges=bool(sl_c and abs(float(np.median(sl_c))) < 0.2),
        incoherent_energy_converges=bool(sl_e and abs(float(np.median(sl_e))) < 0.2),
        null_even_over_odd_db=_fl(null_even_odd, 4),
        null_even_over_odd_median_db=_f(float(np.median(null_even_odd))
                                        if null_even_odd else None),
        n_prod_cells=len(pw),
        n_prod_cells_modulated_coherent=int(n_mod_coh),
        n_prod_cells_modulated_power=int(n_mod_pow),
        f_extent_over_f_tip_median=_f(float(np.median(ext)) if ext else None),
        by_range=by_range, sbr_reference=sbr_row,
        summary_lines=lines)


if __name__ == "__main__":
    main()
