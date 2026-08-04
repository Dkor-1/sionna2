# -*- coding: utf-8 -*-
"""
report15_sweep_matrice4e.py — **matrice4e 거리 스윕: 스톡 Sionna PathSolver 가 로터를
돌려가며 다시 추적했을 때 블레이드 마이크로도플러를 내는가**
================================================================================

묻는 것은 정확히 두 갈래다(탐침 report15_probe.py 와 같은 질문, 이번엔 **본 실험**).

  ① `Paths.doppler` 로 자동으로 나오나 → **아니다(확정)**. SceneObject.velocity 는 객체당
     강체 3성분 1벡터뿐이라 회전을 넣을 자리가 없다. 탐침 §A 에서 이미 실측했고 여기서
     다시 재지 않는다(재확인 결과는 meta.settled 에 인용만 한다).
  ② **로터 위상을 스텝하고 매번 재추적**해서 복소 진폭을 이어붙이면 나오나 → **열린 질문**.
     선례: WiFi-JEPA(arXiv:2607.11064) 가 프레임당 20 패스로 시간축을 만들었다.

⭐ 근거리를 강조하는 이유(= Sionna 에게 가장 유리한 조건)
   (a) 드론이 큰 입체각을 차지해 광선이 많이 맞고 (b) 기체 각 부분이 분해될 수 있고
   (c) Sionna 는 원래 구면 파면을 추적하므로 평면파 가정이 깨지는 것이 불리하지 않다.
   여기서도 안 되면 다른 데선 더 안 된다. → 격자를 R = 1 · 3 · 10 m 로 잡는다.

⚠⚠ **관측량 — 세 가지를 따로 낸다. 하나로 뭉뚱그리면 틀린 결론이 나온다.**
   `Paths.a` 는 **패스밴드 계수**라 전파위상이 없다(imag 성분이 정확히 0). 위상은 τ 가 나른다.

     h_coh = Σ_p a_p·exp(−j2πf_c τ_p)     코히런트 합 (탐침이 쓴 관측량)
     E_inc = Σ_p |a_p|²                     위상무관 에너지
     (둘 다 '표적경유 전 경로(all)' 와 '프로펠러를 맞은 경로(prop)' 로 각각)

   ⭐⭐ **이 실험이 새로 밝힌 것(§4)**: 확산 채널에서 `E_inc` 는 spp 에 대해 **수렴하지만**
     `h_coh` 는 **수렴하지 않고 √spp 로 자란다**. 즉 Sionna 의 확산 경로 진폭은
     |a|∝1/√N 로 **전력합이 보존되도록** 정규화돼 있고(=Σ|a|² 수렴), 그 표본들의 위상은
     서로 독립이 아니라 기하에서 결정되므로 코히런트로 다시 더하면 √N 배 부풀려진다.
     → **h_coh 의 절대값은 물리적 산란장이 아니다.** 이 파일은 그 사실을 측정해 기록하고,
       판정은 (i) 수렴하는 E_inc, (ii) 결정론적인 정반사 채널, (iii) 대칭 널(아래)에
       근거해서만 내린다.

⭐ **대칭 널(이 실험의 급소)** — 2날 프로펠러는 φ 와 φ+180° 에서 형상이 **집합으로 동일**하다
   (§1 에서 1e−16 m 로 실측). 그래서 한 바퀴(360°)를 64 스텝으로 돌면
     · 회전당 **짝수** 조화(2,4,6,…) = 물리가 실을 수 있는 유일한 자리
     · 회전당 **홀수** 조화(1,3,5,…) = 기하가 0 을 보장 → **그 자리에 있는 것은 전부 잡음**
   잡음바닥을 따로 가정할 필요가 없다. **같은 격자 안에 내장된 널**이다.
   추가로 (φ, φ+180°) 짝을 같은 시드로 직접 빼서 짝지은 널도 낸다.

⭐ **왜 정반사가 없는가(§6 기구)** — 준-모노스태틱에서 평면 조각(변 d)이 정반사를 내려면
   그 법선이 이등분선에서 δ_acc ≈ atan(d/2R) 안에 들어야 한다(평판 사다리로 실측).
   곡률반경 ρ 인 곡면을 삼각형으로 쪼개면 이웃 면 법선 간격은 Δθ ≈ d/ρ 다. 따라서
        Δθ / δ_acc ≈ 2R/ρ
   — **테셀레이션(d)이 약분된다.** 잘게 쪼개도 좋아지지 않는다. 정반사가 살아나려면
   **R ≲ ρ/2** 여야 한다. 프로펠러 날의 곡률반경은 cm 급이므로 m 급 거리에서는 원리적으로 없다.

⛔ src/drones.py · src/drone_cad.py 는 **읽기만** 한다.
⛔ 기존 산출물 덮어쓰기 금지 — 출력은 outputs/report15_sionna_sweep_matrice4e.json 하나뿐.
그림 없음(순수 측정). 본문·주석·print 한국어. 숫자는 **전부 계산**해서 JSON 에 담는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick as _pick_gpu, gpu_status                      # noqa: E402
_pick_gpu(verbose=True)                                            # ⚠ mitsuba import 전에!

import mitsuba as mi                                               # noqa: E402
import sionna                                                      # noqa: E402
import sionna.rt as rt                                             # noqa: E402

from geom import Mesh                                              # noqa: E402
from materials import MATERIALS, material_params, gamma_bulk, gamma_po   # noqa: E402
from drones import (DRONES, DRONE_GROUP_MAT, build_drone,          # noqa: E402
                    pose_articulated, rotor_layout, drone_colors, motor_radii)
from scene_build import build_scene, Part                          # noqa: E402

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
NO_OBJ = 4294967295                       # Sionna 의 '상호작용 없음' 표식 (uint32 −1)
KEY = "matrice4e"
BASELINE_M = 0.20                         # 준-모노스태틱 송수신 간격 (탐침·facet_count 와 같은 규약)
MAX_PATHS = 50_000_000

#  ⚠ samples_per_src 는 uint32 로 넘어간다 — 2³²−1 을 넘으면 Sionna 가 TypeError 를 던진다
#    (실측: 16.384e9 에서 죽음). 그래서 실용 최대치를 4.096e9 로 둔다.
SPP_MAX_SAFE = 4_096_000_000
SPP_MAIN = 4_096_000_000                  # 본 격자 광선예산 (여유 GPU 를 화끈하게 쓴다)

RANGES = (1.0, 3.0, 10.0)                 # ⭐ 근거리 강조
#  자세: az 3점(정면·비스듬·측면)을 하우스 기준 el=15° 에서. 여기에 두 개를 더 얹는다 —
#   · hot  : 탐침이 찾은 **정지자세 유일 정반사 자세**(az 0, el 0)
#   · disc : 프롭 면법선의 **중앙값 고도각**(§0 에서 계산) 근처 — 블레이드 정반사가
#            있어야 한다면 물리적으로 여기 있어야 한다. 없으면 그것이 결론이다.
ASPECTS = (("nose", 0.0, 15.0), ("oblique", 45.0, 15.0), ("side", 90.0, 15.0),
           ("hot", 0.0, 0.0), ("disc", 0.0, 75.0))
N_PHASE = 64                              # 한 바퀴(360°) 를 64 스텝 → 주기(180°)당 32
SEEDS = (1, 2, 3)
MODES = (("spec", False), ("prod", True))

OUT_JSON = os.path.join(ROOT, "outputs", "report15_sionna_sweep_matrice4e.json")
SCRATCH = os.environ.get("REPORT15_SCRATCH",
                         "/tmp/claude-1015/-home-yunjung-workspace/"
                         "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/r15sweep")


# --------------------------------------------------------------------------- #
#  기하 유틸
# --------------------------------------------------------------------------- #
def look_dir(az_deg, el_deg):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


def basis_perp(u):
    t = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, t); e1 /= np.linalg.norm(e1)
    return e1, np.cross(u, e1)


def place(scene, az, el, rng, baseline=BASELINE_M):
    """준-모노스태틱 TX/RX 배치(원점 표적). 반환값은 그 배치의 기하 사실들."""
    u = look_dir(az, el)
    e1, _ = basis_perp(u)
    tx = rng * u + 0.5 * baseline * e1
    rx = rng * u - 0.5 * baseline * e1
    for nm in list(scene.transmitters):
        scene.remove(nm)
    for nm in list(scene.receivers):
        scene.remove(nm)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in tx])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in rx])))
    R1 = float(np.linalg.norm(tx)); R2 = float(np.linalg.norm(rx))
    bi = float(np.degrees(np.arccos(np.clip(float((tx / R1) @ (rx / R2)), -1.0, 1.0))))
    return dict(az_deg=float(az), el_deg=float(el), range_m=float(rng),
                baseline_m=float(baseline), bistatic_deg=bi,
                tau_expect_ns=float((R1 + R2) / C0 * 1e9),
                tx=[float(v) for v in tx], rx=[float(v) for v in rx])


# --------------------------------------------------------------------------- #
#  로터 위상 → 메쉬 → 씬
# --------------------------------------------------------------------------- #
_SPEC = DRONES[KEY]
_DIRS = [r["dir"] for r in rotor_layout(_SPEC)]


def posed_mesh(phase_deg: float):
    """로터 위상 φ[deg] 의 분절 스냅샷 메쉬. 로터 k 의 스핀 = dir_k·φ
    (microdoppler_sbr · report15_probe 와 **같은 규약** — 위상축이 정렬된다)."""
    return pose_articulated(_SPEC, rotor_phase_deg=[d * float(phase_deg) for d in _DIRS])


def build_posed_scene(phase_deg: float, tag: str, prop_mat: str | None = None):
    """위상 φ 의 드론 한 대만 있는 자유공간 씬. prop_mat 을 주면 **프롭 그룹만** 그 재질로
    바꾼다(재질 반사실 실험용). tag 에 '.' 가 들어가면 Mitsuba 가 죽으므로 정수 태그만 쓴다."""
    m = posed_mesh(phase_deg)
    d = os.path.join(SCRATCH, f"{KEY}_{tag}")
    paths = m.write_obj_per_group(d, KEY)
    cols = drone_colors(_SPEC)
    parts = []
    for g, p in paths.items():
        mk = DRONE_GROUP_MAT[g][0]
        if g == "prop" and prop_mat:
            mk = prop_mat
        parts.append(Part(name=f"{KEY}_{g}_{tag}", obj=p, mat_key=mk, color=cols[g]))
    return build_scene(parts, fc=FC), d


def drop(d):
    try:
        shutil.rmtree(d)
    except OSError:
        pass


def id_to_group(scene) -> dict:
    def grp(name):
        s = name[len(KEY) + 1:] if name.startswith(KEY + "_") else name
        return s.rsplit("_", 1)[0] if "_" in s else s
    return {int(o.object_id): grp(n) for n, o in scene.objects.items()}


# --------------------------------------------------------------------------- #
#  한 번 추적 → 관측량 3종 × 채널 2종
# --------------------------------------------------------------------------- #
def trace(scene, spp, seed, diffuse, id2grp, max_depth=1, want_groups=False):
    """표적경유 경로만 골라 관측량을 낸다.

    반환 키
      n, n_prop            경로수 (all / prop 채널)
      hr, hi, hpr, hpi     코히런트 합 h = Σ a·exp(−j2πf τ) 의 실·허수 (all / prop)
      inc, inc_prop        위상무관 에너지 Σ|a|²  [dB]
      nophase              위상을 빼먹었을 때의 |Σa| [dB] — 위상이 관측량을 지배함의 증거
      sec                  소요시간
      groups               (want_groups) 부위 그룹별 경로수
    """
    t0 = time.time()
    p = rt.PathSolver()(scene, max_depth=int(max_depth), los=True,
                        specular_reflection=True, diffuse_reflection=bool(diffuse),
                        refraction=False, samples_per_src=int(spp),
                        max_num_paths_per_src=MAX_PATHS, seed=int(seed))
    ar = np.asarray(p.a[0]); ai = np.asarray(p.a[1])
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
    P = int(a.shape[0])
    out = dict(n=0, n_prop=0, hr=0.0, hi=0.0, hpr=0.0, hpi=0.0,
               inc=None, inc_prop=None, nophase=None, sec=0.0, n_raw=P)
    if P == 0:
        out["sec"] = float(time.time() - t0)
        return out
    tau = np.asarray(p.tau, dtype=np.float64).reshape(-1, P)[0]
    O = np.asarray(p.objects)[:, 0, 0, :]
    hit = (O != NO_OBJ).any(axis=0)
    ph = np.exp(-1j * 2.0 * np.pi * FC * tau)
    gm = np.full(O.shape, "", dtype=object)
    for oid, g in id2grp.items():
        gm[O == oid] = g
    pm = (gm == "prop").any(axis=0)
    s = complex(np.sum(a[hit] * ph[hit])) if hit.any() else 0j
    sp = complex(np.sum(a[pm] * ph[pm])) if pm.any() else 0j
    out.update(n=int(hit.sum()), n_prop=int(pm.sum()),
               hr=float(s.real), hi=float(s.imag),
               hpr=float(sp.real), hpi=float(sp.imag),
               inc=(float(10 * np.log10(float(np.sum(np.abs(a[hit]) ** 2)) + 1e-300))
                    if hit.any() else None),
               inc_prop=(float(10 * np.log10(float(np.sum(np.abs(a[pm]) ** 2)) + 1e-300))
                         if pm.any() else None),
               nophase=(float(20 * np.log10(abs(complex(np.sum(a[hit]))) + 1e-300))
                        if hit.any() else None),
               truncated=bool(P >= MAX_PATHS))
    if want_groups:
        out["groups"] = {g: int((gm == g).any(axis=0).sum())
                         for g in sorted(set(id2grp.values()))
                         if (gm == g).any()}
        out["a_imag_absmax"] = float(np.abs(np.imag(a)).max())
        out["tau_min_ns"] = float(tau[hit].min() * 1e9) if hit.any() else None
        out["tau_ptp_ns"] = float(np.ptp(tau[hit]) * 1e9) if hit.any() else None
    out["sec"] = float(time.time() - t0)
    return out


def db_amp(hr, hi):
    return float(20 * np.log10(abs(complex(hr, hi)) + 1e-300))


# --------------------------------------------------------------------------- #
#  §0 — 물리·재질·격자 사실 (전부 계산)
# --------------------------------------------------------------------------- #
def sec0_physics(n_phase: int) -> dict:
    m = build_drone(_SPEC)
    V = np.asarray(m.v, float)
    b0, b1 = V.min(axis=0), V.max(axis=0)
    D_h = float(max(b1[0] - b0[0], b1[1] - b0[1]))
    D_3 = float(np.linalg.norm(b1 - b0))
    rpm = float(_SPEC.hover_rpm)
    omega = 2.0 * math.pi * rpm / 60.0
    prop_R = float(_SPEC.prop_dia_mm) / 2000.0
    v_tip = omega * prop_R
    f_tip = 2.0 * v_tip / LAM
    blades = int(_SPEC.prop_blades)
    flash = blades * rpm / 60.0
    rev_hz = rpm / 60.0
    ff_h, ff_3 = 2.0 * D_h * D_h / LAM, 2.0 * D_3 * D_3 / LAM
    #  한 바퀴 n_phase 스텝 → 등가 슬로타임 샘플률 = n_phase · rev_hz
    prf = float(n_phase) * rev_hz
    per_range = {}
    for R in RANGES:
        tau = 2.0 * R / C0
        #  τ 는 float32 다 → 위상 양자화 오차 = 360·f_c·τ·eps32
        dphi = 360.0 * FC * tau * float(np.finfo(np.float32).eps)
        per_range[f"{R:g}"] = dict(
            range_m=float(R),
            farfield_2D2_lam_m=ff_h, in_farfield=bool(R >= ff_h),
            range_over_farfield=float(R / ff_h),
            farfield_diag3d_m=ff_3, in_farfield_diag3d=bool(R >= ff_3),
            #  Fraunhofer 뿐 아니라 Fresnel(radiating near field) 하한도 함께
            fresnel_inner_m=float(0.62 * math.sqrt(D_h ** 3 / LAM)),
            subtended_deg=float(2 * math.degrees(math.atan(0.5 * D_h / R))),
            solid_angle_frac=float((math.pi * (D_h / 2) ** 2) / (4 * math.pi * R * R)),
            rays_on_target_at_main_spp=float(SPP_MAIN * (math.pi * (D_h / 2) ** 2)
                                             / (4 * math.pi * R * R)),
            tau_roundtrip_ns=float(tau * 1e9),
            tau_float32_phase_quantum_deg=float(dphi),
            bistatic_deg_at_fixed_baseline=float(
                2 * math.degrees(math.atan(0.5 * BASELINE_M / R))))
    return dict(
        drone=KEY, name=_SPEC.name, fc_hz=FC, lambda_m=LAM,
        D_horizontal_m=D_h, D_diag3d_m=D_3, span_m=[float(x) for x in (b1 - b0)],
        diagonal_spec_mm=float(_SPEC.diagonal_mm),
        n_rotors=int(_SPEC.num_rotors), prop_blades=blades,
        prop_dia_mm=float(_SPEC.prop_dia_mm), prop_radius_m=prop_R,
        rotor_radii_m=[float(x) for x in motor_radii(_SPEC)],
        hover_rpm=rpm, rev_hz=rev_hz, omega_rad_s=omega,
        v_tip_ms=v_tip, v_tip_mach=float(v_tip / 343.0),
        f_tip_hz=f_tip, flash_hz=flash,
        phase_period_deg=float(360.0 / blades),
        n_phase_steps_per_rev=int(n_phase),
        n_phase_steps_per_period=int(n_phase // blades),
        equivalent_prf_hz=prf, prf_min_hz=2.0 * f_tip,
        aliased=bool(prf < 2.0 * f_tip), alias_margin=float(prf / (2.0 * f_tip)),
        n_steps_min_for_nyquist=int(math.ceil(2.0 * f_tip / rev_hz)),
        tip_travel_per_step_m=float(prop_R * 2 * math.pi / n_phase),
        tip_travel_per_step_lambda=float(prop_R * 2 * math.pi / n_phase / LAM),
        max_roundtrip_phase_swing_deg=float(360.0 * 2.0 * (2.0 * prop_R) / LAM),
        by_range=per_range,
        note_ko=("한 바퀴 N 스텝 = 등가 슬로타임 샘플률 N·rev_hz. f_tip 을 접지 않으려면 "
                 "N ≥ 2·f_tip/rev_hz. 원거리장 경계는 **기체 크기로 정해지므로 기체마다 다르다** "
                 "— farfield_table 참조."))


def sec0_farfield_table() -> dict:
    """⚠ 기체가 다르면 원거리장 경계도 다르다 — 격자 거리 1·3·10 m 가 어느 기체에서
    근거리장인지 **기체별로** 판정해 표로 남긴다(손으로 고르지 않기 위해)."""
    out = {}
    for k, sp in DRONES.items():
        try:
            V = np.asarray(build_drone(sp).v, float)
        except Exception:
            continue
        b0, b1 = V.min(axis=0), V.max(axis=0)
        D = float(max(b1[0] - b0[0], b1[1] - b0[1]))
        ff = 2.0 * D * D / LAM
        out[k] = dict(name=sp.name, D_horizontal_m=D, farfield_2D2_lam_m=ff,
                      in_farfield={f"{R:g}": bool(R >= ff) for R in RANGES})
    return out


def sec0_materials() -> dict:
    """⭐ **이 기체의 로터가 어느 재질 그룹으로 배정되는가.** 블레이드 반사계수가 곧
    변조 크기의 상한을 정한다 — 그래서 Sionna 가 실제로 받는 (εr, σ, S) 까지 읽어서 적는다."""
    rows = {}
    for grp, (mat, desc) in DRONE_GROUP_MAT.items():
        er, sg, S = material_params(mat, FC)
        gb = gamma_bulk(mat, FC)
        rows[grp] = dict(
            material_key=mat, desc_ko=desc,
            sionna_kind=("ITURadioMaterial(" + MATERIALS[mat]["itu"] + ")"
                         if "itu" in MATERIALS[mat] else "RadioMaterial(eps_r,sigma,S)"),
            eps_r=float(er), sigma_S_per_m=float(sg), scattering_coefficient_S=float(S),
            gamma_bulk_fresnel=float(gb), gamma_po_effective=float(gamma_po(mat, FC)),
            gamma_db_vs_pec=float(20 * np.log10(gb + 1e-300)))
    prop = rows["prop"]
    motor = rows["motor"]
    #  프롭 그룹의 면적·삼각형 통계 (변조를 낼 수 있는 표면의 크기)
    m = posed_mesh(0.0)
    V = np.asarray(m.v, float); F = np.asarray(m.f, int); G = np.asarray(m.g, dtype=object)
    Fp = F[G == "prop"]
    nv = np.cross(V[Fp[:, 1]] - V[Fp[:, 0]], V[Fp[:, 2]] - V[Fp[:, 0]])
    A = 0.5 * np.linalg.norm(nv, axis=1)
    tot = float(np.sum(0.5 * np.linalg.norm(
        np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)))
    return dict(
        by_group=rows,
        rotor_verdict_ko=(
            f"⭐ 이 기체의 로터(prop 그룹)는 **{prop['material_key']}** 로 배정된다 — 금속이 아니라 "
            f"**플라스틱 유전체**다(εr={prop['eps_r']:.2f}, σ={prop['sigma_S_per_m']:.3g} S/m, "
            f"산란계수 S={prop['scattering_coefficient_S']:.2f}). 수직입사 벌크 프레넬 "
            f"|Γ|={prop['gamma_bulk_fresnel']:.4f} = {prop['gamma_db_vs_pec']:.2f} dB "
            f"(PEC 대비). 바로 아래 모터는 {motor['material_key']}(|Γ|="
            f"{motor['gamma_bulk_fresnel']:.4f}) 라 **금속 모터가 플라스틱 날보다 "
            f"{20*math.log10(motor['gamma_bulk_fresnel']/prop['gamma_bulk_fresnel']):.1f} dB "
            f"더 잘 반사한다** — 블레이드 변조를 볼 때 이것이 배경이다."),
        prop_area_m2=float(A.sum()), prop_area_frac_of_drone=float(A.sum() / tot),
        prop_n_tris=int(A.size), drone_area_m2=tot,
        prop_tri_edge_median_mm=float(np.median(np.sqrt(2 * A)) * 1000.0),
        note_ko=("재질은 materials.MATERIALS 가 유일한 출처다. gamma_po 는 PO 엔진 전용 실효값이고 "
                 "Sionna 가 보는 것은 (εr, σ, S) 다 — 둘을 섞지 말 것."))


def sec0_prop_normals() -> dict:
    """프롭 면법선의 방향 분포 — **정반사가 있어야 할 시선 고도각**을 예측한다.
    준-모노스태틱에서 법선 고도각 θ 인 면은 시선 고도 θ 에서 정반사한다."""
    m = posed_mesh(0.0)
    V = np.asarray(m.v, float); F = np.asarray(m.f, int); G = np.asarray(m.g, dtype=object)
    out = {}
    for grp in ("prop", "camera", "body", "motor"):
        Fg = F[G == grp]
        if Fg.size == 0:
            continue
        nv = np.cross(V[Fg[:, 1]] - V[Fg[:, 0]], V[Fg[:, 2]] - V[Fg[:, 0]])
        A = 0.5 * np.linalg.norm(nv, axis=1)
        nn = nv / (np.linalg.norm(nv, axis=1, keepdims=True) + 1e-30)
        el = np.degrees(np.arcsin(np.clip(np.abs(nn[:, 2]), 0, 1)))
        edges = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
        h, _ = np.histogram(el, bins=edges, weights=A)
        o = np.argsort(A)[::-1]
        w = A[o] / A.sum()
        out[grp] = dict(
            n_tris=int(A.size), area_m2=float(A.sum()),
            normal_el_deg_pct={str(q): float(np.percentile(el, q))
                               for q in (0, 5, 25, 50, 75, 95, 100)},
            normal_el_area_weighted_median_deg=float(
                el[o][np.searchsorted(np.cumsum(w), 0.5)]),
            area_frac_by_normal_el={f"{edges[i]}-{edges[i+1]}": float(h[i] / A.sum())
                                    for i in range(len(h))})
    return dict(by_group=out,
                note_ko=("프롭 법선은 대부분 고도 60~90° 를 향한다 — 즉 블레이드 정반사가 "
                         "있으려면 **디스크를 내려다보는 시선**이어야 한다. 격자에 disc "
                         "(az 0, el 75) 자세를 넣은 이유다."))


# --------------------------------------------------------------------------- #
#  §1 — 로터 위상 스텝이 정말 씬을 바꾸는가 + 대칭 널이 성립하는가
# --------------------------------------------------------------------------- #
def sec1_period() -> dict:
    """φ↔φ+180° 는 **집합으로 같고 배열 순서는 다르다**(2날 대칭). 이 성질이 이 실험의 널이다.
    φ↔φ+360° 는 원소별로 같아야 한다(같은 파일 → 같은 결과, 결정성 확인용)."""
    V0 = np.asarray(posed_mesh(0.0).v, float)
    V180 = np.asarray(posed_mesh(180.0).v, float)
    V360 = np.asarray(posed_mesh(360.0).v, float)
    V45 = np.asarray(posed_mesh(45.0).v, float)
    try:
        from scipy.spatial import cKDTree
        set_dev = float(cKDTree(V0).query(V180)[0].max())
    except Exception:
        set_dev = None
    sh = lambda A: hashlib.sha1(np.ascontiguousarray(np.round(A, 9)).tobytes()).hexdigest()  # noqa: E731
    d45 = np.linalg.norm(V45 - V0, axis=1)
    F = np.asarray(posed_mesh(0.0).f, int); G = np.asarray(posed_mesh(0.0).g, dtype=object)
    moved = {}
    for grp in sorted(set(G.tolist())):
        vi = np.unique(F[G == grp].ravel())
        moved[str(grp)] = float(d45[vi].max())
    return dict(
        sha1={"0": sh(V0), "180": sh(V180), "360": sh(V360)},
        elementwise_max_dev_0_vs_180_m=float(np.abs(V180 - V0).max()),
        elementwise_max_dev_0_vs_360_m=float(np.abs(V360 - V0).max()),
        setwise_max_dev_0_vs_180_m=set_dev,
        symmetry_null_valid=bool(set_dev is not None and set_dev < 1e-9
                                 and np.abs(V180 - V0).max() > 1e-6),
        full_turn_identical=bool(np.abs(V360 - V0).max() < 1e-12),
        max_shift_45deg_m=float(d45.max()),
        max_shift_45deg_lambda=float(d45.max() / LAM),
        max_roundtrip_phase_45deg_deg=float(360.0 * 2.0 * d45.max() / LAM),
        n_moved_vertices=int(np.count_nonzero(d45 > 1e-9)),
        max_shift_by_group_m=moved,
        note_ko=("φ↔φ+180° 가 '집합은 같고 정점 순서는 다르다' 는 것이 핵심이다. OBJ 바이트가 "
                 "달라 BVH·표본이 독립이므로, 두 값의 차이는 **기하가 0 을 보장하는 순수 잡음**이다. "
                 "→ 회전당 홀수 조화 = 잡음, 짝수 조화 = 물리가 실을 수 있는 자리."))


# --------------------------------------------------------------------------- #
#  §2 — ⭐ 본 격자
# --------------------------------------------------------------------------- #
def sec2_grid(n_phase=N_PHASE, seeds=SEEDS, spp=SPP_MAIN, ranges=RANGES,
              aspects=ASPECTS, modes=MODES) -> dict:
    """(거리 × 자세 × 위상 × 시드 × 채널) 마다 **복소 h 와 경로수**를 남긴다.

    루프 순서는 **위상이 바깥**이다 — 씬 조립(메쉬+OBJ 쓰기)이 가장 비싸므로 위상당 한 번만
    만들고 그 안에서 TX/RX 만 옮긴다. 시드 목록을 모든 칸에 똑같이 써서 짝지은 분석이 된다."""
    phis = np.arange(n_phase) * (360.0 / n_phase)
    keys = [(f"{R:g}", nm) for R in ranges for nm, _, _ in aspects]
    blocks = {f"{rk}/{ak}/{mn}": dict(
        range_m=float(rk), aspect=ak, mode=mn, diffuse=bool(df),
        n=[[0] * len(seeds) for _ in range(n_phase)],
        n_prop=[[0] * len(seeds) for _ in range(n_phase)],
        hr=[[0.0] * len(seeds) for _ in range(n_phase)],
        hi=[[0.0] * len(seeds) for _ in range(n_phase)],
        hpr=[[0.0] * len(seeds) for _ in range(n_phase)],
        hpi=[[0.0] * len(seeds) for _ in range(n_phase)],
        inc=[[None] * len(seeds) for _ in range(n_phase)],
        inc_prop=[[None] * len(seeds) for _ in range(n_phase)],
        nophase=[[None] * len(seeds) for _ in range(n_phase)])
        for (rk, ak) in keys for mn, df in modes}
    geo = {}
    gsum: dict = {}
    t0 = time.time()
    n_trace = 0
    for i, phd in enumerate(phis):
        scene, dd = build_posed_scene(float(phd), f"G{i:03d}")
        g2 = id_to_group(scene)
        for R in ranges:
            for ak, az, el in aspects:
                g = place(scene, az, el, R)
                geo[f"{R:g}/{ak}"] = g
                for mn, df in modes:
                    B = blocks[f"{R:g}/{ak}/{mn}"]
                    for j, sd in enumerate(seeds):
                        r = trace(scene, spp, sd, df, g2, want_groups=(j == 0))
                        n_trace += 1
                        for k in ("n", "n_prop", "hr", "hi", "hpr", "hpi",
                                  "inc", "inc_prop", "nophase"):
                            B[k][i][j] = r[k]
                        if j == 0 and r.get("groups"):
                            gk = f"{R:g}/{ak}/{mn}"
                            for gg, c in r["groups"].items():
                                gsum.setdefault(gk, {}).setdefault(gg, []).append(c)
        drop(dd)
        el_ = time.time() - t0
        print(f"    φ={phd:7.3f}°  ({i+1}/{n_phase})  누적 {n_trace} 추적  "
              f"{el_:6.0f}s  (예상 총 {el_/(i+1)*n_phase:6.0f}s)", flush=True)
    for gk, dv in gsum.items():
        blocks[gk]["groups_n_mean"] = {g: float(np.mean(v)) for g, v in sorted(dv.items())}
    return dict(phases_deg=[float(x) for x in phis], seeds=[int(s) for s in seeds],
                spp=int(spp), ranges=[float(r) for r in ranges],
                aspects=[dict(name=n, az_deg=a, el_deg=e) for n, a, e in aspects],
                modes=[m for m, _ in modes], max_depth=1, baseline_m=BASELINE_M,
                geometry=geo, n_traces=int(n_trace), seconds=float(time.time() - t0),
                blocks=blocks)


# --------------------------------------------------------------------------- #
#  §3 — 격자 분석: 경로수 거동 · 0-경로 비율 · 잡음바닥 · 대칭 널 · 조화
# --------------------------------------------------------------------------- #
def _harmonics(z: np.ndarray) -> dict:
    """한 바퀴 N 표본의 복소열 → 회전당 조화 분해.
    ⭐ 2날 대칭 때문에 **홀수 조화는 기하가 0 을 보장**한다 → 그것이 잡음바닥이다."""
    N = z.shape[0]
    Z = np.fft.fft(z) / N
    k = np.arange(N)
    mag = np.abs(Z)
    ny = N // 2
    ev = [i for i in range(1, ny + 1) if i % 2 == 0]
    od = [i for i in range(1, ny + 1) if i % 2 == 1]
    pe = float(np.sum(mag[ev] ** 2)); po = float(np.sum(mag[od] ** 2))
    #  홀수 조화 1개당 평균 전력 = 잡음 1빈 전력 → 짝수 빈에서 그만큼 빼면 순 신호
    n1 = po / max(1, len(od))
    net = max(0.0, pe - n1 * len(ev))
    top = int(ev[int(np.argmax(mag[ev]))]) if ev else None
    return dict(
        n_samples=int(N), dc_abs=float(mag[0]),
        even_power=pe, odd_power=po,
        even_over_odd_db=float(10 * np.log10((pe + 1e-300) / (po + 1e-300))),
        net_even_power=net,
        net_even_over_odd_db=float(10 * np.log10((net + 1e-300) / (po + 1e-300))),
        snr_even_vs_oddbin_db=float(10 * np.log10((net / max(1, len(ev)) + 1e-300)
                                                  / (n1 + 1e-300))),
        dominant_even_harmonic=top,
        dominant_even_over_noisebin_db=(float(20 * np.log10((mag[top] + 1e-300)
                                                            / (math.sqrt(n1) + 1e-300)))
                                        if top else None),
        harm_abs_rel_dc=[float(mag[i] / (mag[0] + 1e-300)) for i in range(0, ny + 1)],
        harm_index=[int(i) for i in range(0, ny + 1)],
        note_ko=("빈 k = 회전당 k 사이클. 2날이면 물리는 짝수 k 에만 실릴 수 있다(블레이드 "
                 "플래시 = k=2). 홀수 k 의 전력은 **기하가 0 을 보장한 자리**라 잡음의 직접 측정이다."))


def _stat_block(B, n_phase, n_seed, channel="all") -> dict:
    """한 블록(거리·자세·채널) 분석."""
    kn = "n" if channel == "all" else "n_prop"
    kr, ki = ("hr", "hi") if channel == "all" else ("hpr", "hpi")
    kinc = "inc" if channel == "all" else "inc_prop"
    n = np.array(B[kn], float)                              # [phase, seed]
    z = np.array(B[kr], float) + 1j * np.array(B[ki], float)
    inc = np.array([[np.nan if v is None else v for v in row] for row in B[kinc]], float)
    amp = 20 * np.log10(np.abs(z) + 1e-300)
    amp = np.where(n > 0, amp, np.nan)

    zero = float(np.mean(n == 0))
    behaviour = ("모든 칸에서 경로 0" if zero == 1.0 else
                 ("껐다켜짐 (경로수가 0 을 오간다)" if zero > 0 else "연속 (모든 칸에 경로 존재)"))
    out = dict(channel=channel, n_phase=int(n_phase), n_seed=int(n_seed),
               n_paths_mean=float(n.mean()), n_paths_std=float(n.std(ddof=1)),
               n_paths_min=int(n.min()), n_paths_max=int(n.max()),
               n_paths_cv=(float(n.std(ddof=1) / n.mean()) if n.mean() > 0 else None),
               zero_path_cell_frac=zero, n_paths_behaviour=behaviour,
               n_paths_by_phase=[float(x) for x in n.mean(axis=1)])
    if zero == 1.0:
        return dict(out, ok=False, verdict="판정 불가 — 경로가 없다")

    #  경로수 거동: 위상축에서 매끈한가, 튀는가
    npm = n.mean(axis=1)
    dif = np.abs(np.diff(np.r_[npm, npm[0]]))
    out.update(n_paths_step_median_frac=float(np.median(dif) / max(1e-9, npm.mean())),
               n_paths_step_max_frac=float(dif.max() / max(1e-9, npm.mean())))

    #  잡음바닥 — 같은 칸을 시드만 바꿔 반복 (격자 위에서 재확인)
    with np.errstate(invalid="ignore"):
        within = np.nanstd(amp, axis=1, ddof=1)
    out["seed_noise_std_db"] = float(np.nanmean(within))
    out["seed_noise_std_db_max"] = float(np.nanmax(within))
    out["seed_noise_inc_std_db"] = float(np.nanmean(np.nanstd(inc, axis=1, ddof=1)))

    #  위상축 변동
    pm_amp = np.nanmean(amp, axis=1)
    pm_inc = np.nanmean(inc, axis=1)
    out.update(modulation_ptp_db=float(np.nanmax(pm_amp) - np.nanmin(pm_amp)),
               modulation_std_db=float(np.nanstd(pm_amp, ddof=1)),
               amp_db_mean=float(np.nanmean(pm_amp)),
               inc_db_mean=float(np.nanmean(pm_inc)),
               inc_modulation_ptp_db=float(np.nanmax(pm_inc) - np.nanmin(pm_inc)),
               inc_modulation_std_db=float(np.nanstd(pm_inc, ddof=1)),
               phase_mean_amp_db=[float(x) for x in pm_amp],
               phase_mean_inc_db=[float(x) for x in pm_inc])

    #  ⭐ 대칭 널 — φ 와 φ+180° 는 기하가 같다. 같은 시드로 뺀 차이 = 순수 잡음.
    half = n_phase // 2
    if n_phase % 2 == 0:
        d_amp = amp[:half, :] - amp[half:, :]
        out["sym_null_rms_db"] = float(np.sqrt(np.nanmean(d_amp ** 2)))
        out["sym_null_ptp_db"] = float(np.nanmax(np.abs(d_amp)))
        d_n = n[:half, :] - n[half:, :]
        out["sym_null_n_paths_rms"] = float(np.sqrt(np.mean(d_n ** 2)))
        d_inc = inc[:half, :] - inc[half:, :]
        out["sym_null_inc_rms_db"] = float(np.sqrt(np.nanmean(d_inc ** 2)))
        #  신호 대 널: 반주기 평균끼리의 변동 vs 대칭 널 변동
        sig = np.nanstd(np.nanmean(amp, axis=1), ddof=1)
        out["signal_std_over_symnull_rms"] = float(sig / (out["sym_null_rms_db"] /
                                                          math.sqrt(2) + 1e-300))

    #  ⭐ 조화 분해 — 시드별로 하고 평균 (시드 잡음을 섞지 않는다)
    H = [_harmonics(z[:, j]) for j in range(z.shape[1]) if np.all(n[:, j] > 0)]
    if H:
        out["harmonics_complex"] = dict(
            even_over_odd_db=float(np.mean([h["even_over_odd_db"] for h in H])),
            net_even_over_odd_db=float(np.mean([h["net_even_over_odd_db"] for h in H])),
            snr_even_vs_oddbin_db=float(np.mean([h["snr_even_vs_oddbin_db"] for h in H])),
            dominant_even_harmonic=int(np.median([h["dominant_even_harmonic"] for h in H])),
            per_seed=[{k: h[k] for k in ("even_over_odd_db", "net_even_over_odd_db",
                                         "dominant_even_harmonic",
                                         "dominant_even_over_noisebin_db")} for h in H],
            harm_abs_rel_dc_mean=[float(x) for x in
                                  np.mean([h["harm_abs_rel_dc"] for h in H], axis=0)],
            harm_index=H[0]["harm_index"])
    #  dB 열(진폭만)의 조화 — 코히런트 위상에 의존하지 않는 관점
    ad = np.where(np.isfinite(amp), amp, 0.0)
    Ha = [_harmonics(ad[:, j] - ad[:, j].mean()) for j in range(ad.shape[1])]
    out["harmonics_absdb"] = dict(
        even_over_odd_db=float(np.mean([h["even_over_odd_db"] for h in Ha])),
        net_even_over_odd_db=float(np.mean([h["net_even_over_odd_db"] for h in Ha])),
        dominant_even_harmonic=int(np.median([h["dominant_even_harmonic"] for h in Ha])))
    idb = np.where(np.isfinite(inc), inc, 0.0)
    Hi = [_harmonics(idb[:, j] - idb[:, j].mean()) for j in range(idb.shape[1])]
    out["harmonics_incdb"] = dict(
        even_over_odd_db=float(np.mean([h["even_over_odd_db"] for h in Hi])),
        net_even_over_odd_db=float(np.mean([h["net_even_over_odd_db"] for h in Hi])),
        dominant_even_harmonic=int(np.median([h["dominant_even_harmonic"] for h in Hi])))

    #  ANOVA: 위상간 분산 / 위상내(시드) 분산
    per = [amp[i, np.isfinite(amp[i])] for i in range(n_phase)]
    per = [g for g in per if g.size]
    k_, nn_ = len(per), int(sum(g.size for g in per))
    grand = float(np.mean(np.concatenate(per)))
    ssb = float(sum(g.size * (g.mean() - grand) ** 2 for g in per))
    ssw = float(sum(float(np.sum((g - g.mean()) ** 2)) for g in per))
    dfb, dfw = k_ - 1, nn_ - k_
    F = ((ssb / dfb) / (ssw / dfw)) if (dfw > 0 and ssw > 0) else (0.0 if ssb <= 1e-30
                                                                  else float("inf"))
    p = None
    try:
        from scipy.stats import f as _fd
        p = float(_fd.sf(F, dfb, dfw)) if np.isfinite(F) and dfw > 0 else (1.0 if F == 0 else 0.0)
    except Exception:
        pass
    out["anova"] = dict(F=float(F), df_between=int(dfb), df_within=int(dfw), p_value=p)

    #  판정 — 세 검정을 **모두** 통과해야 '유의'
    ok_anova = bool(p is not None and p < 1e-3)
    ok_sym = bool(out.get("signal_std_over_symnull_rms", 0.0) > 3.0)
    ok_harm = bool(out.get("harmonics_complex", {}).get("net_even_over_odd_db", -99) > 4.77)
    out.update(test_anova_pass=ok_anova, test_symmetry_null_pass=ok_sym,
               test_even_harmonic_pass=ok_harm,
               modulation_above_noise=bool(ok_anova and ok_sym and ok_harm),
               verdict=("유의 — 세 검정 통과(위상 변동이 대칭 널·조화 널을 넘는다)"
                        if (ok_anova and ok_sym and ok_harm) else
                        ("경계 — 일부 검정만 통과" if (ok_anova or ok_sym or ok_harm)
                         else "잡음과 구별 안 됨")), ok=True)
    return out


def sec3_analyze(grid: dict) -> dict:
    n_phase, n_seed = len(grid["phases_deg"]), len(grid["seeds"])
    out, cells_zero, cells_tot = {}, {}, {}
    for key, B in grid["blocks"].items():
        for ch in ("all", "prop"):
            st = _stat_block(B, n_phase, n_seed, ch)
            st.update(range_m=B["range_m"], aspect=B["aspect"], mode=B["mode"])
            out[f"{key}/{ch}"] = st
            mk = f"{B['mode']}/{ch}"
            n = np.array(B["n" if ch == "all" else "n_prop"], float)
            cells_zero[mk] = cells_zero.get(mk, 0) + int(np.sum(n == 0))
            cells_tot[mk] = cells_tot.get(mk, 0) + int(n.size)
    census = {mk: dict(n_cells=cells_tot[mk], n_cells_zero=cells_zero[mk],
                       zero_frac=float(cells_zero[mk] / cells_tot[mk]))
              for mk in cells_tot}
    return dict(by_block=out, zero_path_census=census,
                note_ko=("zero_path_census 의 칸 = (거리, 자세, 위상, 시드) 하나. "
                         "spec 채널이 100% 0 이면 '정반사 에코가 아예 없다' 는 뜻이고, "
                         "그때 위상 스텝이 흔들 수 있는 것은 확산(몬테카를로) 채널뿐이다."))


# --------------------------------------------------------------------------- #
#  §4 — ⭐⭐ 수렴성: 코히런트 합은 수렴하는가
# --------------------------------------------------------------------------- #
def sec4_convergence(spps=(16_000_000, 64_000_000, 256_000_000,
                           1_024_000_000, SPP_MAX_SAFE), n_seed=3) -> dict:
    """같은 씬에서 spp 만 올려가며 세 관측량을 본다.
      · E_inc = Σ|a|²        → 수렴해야 정상(전력 정규화)
      · |h_coh| = |Σa e^{−jωτ}| → 수렴하나?
      · <|a|>                 → 1/√N 로 줄면 '전력합 보존' 정규화라는 직접 증거
    수렴 지수는 log|h| vs log N 의 기울기로 **계산**한다(손으로 안 적는다)."""
    scene, dd = build_posed_scene(0.0, "CV")
    g2 = id_to_group(scene)
    res = {}
    for R in RANGES:
        place(scene, 0.0, 15.0, R)
        rows = []
        for spp in spps:
            v = [trace(scene, spp, s, True, g2) for s in range(1, n_seed + 1)]
            amp = [db_amp(r["hr"], r["hi"]) for r in v if r["n"]]
            inc = [r["inc"] for r in v if r["n"]]
            npa = [r["n"] for r in v]
            rows.append(dict(spp=int(spp), n_paths_mean=float(np.mean(npa)),
                             coh_db_mean=float(np.mean(amp)) if amp else None,
                             coh_db_std=float(np.std(amp, ddof=1)) if len(amp) > 1 else None,
                             inc_db_mean=float(np.mean(inc)) if inc else None,
                             inc_db_std=float(np.std(inc, ddof=1)) if len(inc) > 1 else None,
                             sec=float(np.mean([r["sec"] for r in v]))))
        ok = [r for r in rows if r["coh_db_mean"] is not None and r["n_paths_mean"] > 0]
        slope = None
        if len(ok) >= 3:
            x = np.log10([r["n_paths_mean"] for r in ok])
            y = np.array([r["coh_db_mean"] for r in ok]) / 20.0     # log10|h|
            slope = float(np.polyfit(x, y, 1)[0])
        inc_ok = [r["inc_db_mean"] for r in ok]
        res[f"{R:g}"] = dict(
            range_m=float(R), rows=rows,
            coh_slope_log10h_per_log10N=slope,
            coh_total_swing_db=(float(ok[-1]["coh_db_mean"] - ok[0]["coh_db_mean"])
                                if len(ok) >= 2 else None),
            inc_total_swing_db=(float(inc_ok[-1] - inc_ok[0]) if len(inc_ok) >= 2 else None),
            inc_converged=bool(len(inc_ok) >= 2 and abs(inc_ok[-1] - inc_ok[0]) < 1.0),
            coh_converged=bool(len(ok) >= 2 and abs(ok[-1]["coh_db_mean"]
                                                    - ok[0]["coh_db_mean"]) < 1.0))
    drop(dd)
    return dict(by_range=res, seeds=int(n_seed), az_deg=0.0, el_deg=15.0,
                spp_max_safe=int(SPP_MAX_SAFE),
                note_ko=("기울기 0.5 = |h| ∝ √N — 표본 위상이 서로 독립이 아니라 기하에서 "
                         "결정되므로 코히런트로 다시 더하면 표본수만큼 부풀려진다는 뜻이다. "
                         "0 이면 수렴. Σ|a|² 가 평평하면 Sionna 의 정규화는 **전력합 보존**이다."))


# --------------------------------------------------------------------------- #
#  §5 — 정반사 인구조사 (거리 × 자세) + 재질 반사실
# --------------------------------------------------------------------------- #
def sec5_specular_census(spp=SPP_MAIN, az_list=None, el_list=None,
                         phases=(0.0, 22.5, 45.0, 67.5), prop_mat=None) -> dict:
    """정반사만(diffuse=False) 켜고 (거리 × 자세 × 위상) 칸마다 경로 유무와 **부위**를 센다.
    ⭐ 고도각을 90° 까지 촘촘히 — 프롭 법선이 향하는 곳이 거기다."""
    az_list = list(az_list if az_list is not None else np.arange(0.0, 360.0, 45.0))
    el_list = list(el_list if el_list is not None else
                   (0.0, 15.0, 30.0, 45.0, 60.0, 70.0, 75.0, 80.0, 85.0, 90.0))
    rows = []
    for i, phd in enumerate(phases):
        scene, dd = build_posed_scene(float(phd), f"S{i:02d}", prop_mat=prop_mat)
        g2 = id_to_group(scene)
        for R in RANGES:
            for el in el_list:
                for az in az_list:
                    place(scene, az, el, R)
                    r = trace(scene, spp, 1, False, g2, want_groups=True)
                    rows.append(dict(phase_deg=float(phd), range_m=float(R),
                                     az_deg=float(az), el_deg=float(el),
                                     n=int(r["n"]), n_prop=int(r["n_prop"]),
                                     amp_db=(db_amp(r["hr"], r["hi"]) if r["n"] else None),
                                     groups=r.get("groups", {})))
        drop(dd)
        print(f"    정반사 인구조사 φ={phd:5.1f}° 완료 ({i+1}/{len(phases)})", flush=True)
    tot = len(rows)
    hit = [r for r in rows if r["n"] > 0]
    ph = [r for r in rows if r["n_prop"] > 0]
    gc: dict = {}
    for r in hit:
        for g, c in (r["groups"] or {}).items():
            gc[g] = gc.get(g, 0) + int(c)
    by_R = {}
    for R in RANGES:
        sub = [r for r in rows if r["range_m"] == R]
        by_R[f"{R:g}"] = dict(n_cells=len(sub),
                              n_with_specular=sum(1 for r in sub if r["n"] > 0),
                              n_with_prop_specular=sum(1 for r in sub if r["n_prop"] > 0),
                              frac_with_specular=float(sum(1 for r in sub if r["n"] > 0) / len(sub)))
    return dict(prop_material=(prop_mat or "production(prop_plastic)"),
                spp=int(spp), az_deg=az_list, el_deg=el_list,
                phases_deg=[float(x) for x in phases],
                n_cells=tot, n_cells_with_specular=len(hit),
                frac_cells_with_specular=float(len(hit) / max(1, tot)),
                n_cells_with_prop_specular=len(ph),
                frac_cells_with_prop_specular=float(len(ph) / max(1, tot)),
                specular_paths_by_group=dict(sorted(gc.items())),
                by_range=by_R,
                hit_cells=[{k: r[k] for k in ("phase_deg", "range_m", "az_deg", "el_deg",
                                              "n", "n_prop", "amp_db", "groups")}
                           for r in hit],
                note_ko=("교과서적 '블레이드 플래시' 가 스톡 RT 에 있으려면 프롭을 맞은 정반사 "
                         "경로가 적어도 일부 칸에서 나와야 한다. 여기서 0 이면 없는 것이다."))


# --------------------------------------------------------------------------- #
#  §6 — 기구: 정반사 수용각 · 곡률 법칙 (자작 통제 표적)
# --------------------------------------------------------------------------- #
def _one_obj_scene(mesh, tag, mat="metal"):
    d = os.path.join(SCRATCH, tag)
    pth = os.path.join(d, "o.obj")
    mesh.write_obj(pth)
    return build_scene([Part(name=tag, obj=pth, mat_key=mat)], fc=FC), d


def _plate(side, u, tilt_deg=0.0):
    e1, e2 = basis_perp(u)
    th = math.radians(tilt_deg)
    n = math.cos(th) * u + math.sin(th) * e2
    a1 = np.cross(n, e1); a1 /= np.linalg.norm(a1)
    a2 = np.cross(n, a1)
    h = side / 2.0
    m = Mesh("plate")
    idx = [m.add_vertex(*(sx * h * a1 + sy * h * a2))
           for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    m.add_quad(*idx, group="plate")
    return m


def _cylinder(radius, length, nseg):
    """축이 y 인 원기둥(곡면). nseg 로 테셀레이션을, radius 로 곡률반경을 조절한다."""
    m = Mesh("cyl")
    for k in range(nseg):
        a0 = 2 * math.pi * k / nseg
        a1 = 2 * math.pi * (k + 1) / nseg
        p = [m.add_vertex(radius * math.cos(a0), -length / 2, radius * math.sin(a0)),
             m.add_vertex(radius * math.cos(a1), -length / 2, radius * math.sin(a1)),
             m.add_vertex(radius * math.cos(a1), length / 2, radius * math.sin(a1)),
             m.add_vertex(radius * math.cos(a0), length / 2, radius * math.sin(a0))]
        m.add_quad(*p, group="cyl")
    return m


def _n_spec(scene, spp):
    p = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                        diffuse_reflection=False, refraction=False,
                        samples_per_src=int(spp), max_num_paths_per_src=MAX_PATHS, seed=1)
    ar = np.asarray(p.a[0])
    P = ar.reshape(-1, ar.shape[-1]).shape[1]
    if P == 0:
        return 0
    O = np.asarray(p.objects)[:, 0, 0, :]
    return int((O != NO_OBJ).any(axis=0).sum())


def sec6_mechanism(spp=1_024_000_000) -> dict:
    """왜 프롭 정반사가 0 인가 — **주장 대신 통제 표적으로 잰다.**

    (a) 양성대조: 법선을 이등분선에 정확히 맞춘 금속 평판. 변 길이 사다리 × 거리.
    (b) 수용각  : 그 평판을 δ 만큼 기울여 정반사가 언제 사라지나 → δ_max 실측.
                  예측 δ_max ≈ atan((변/2)/R) 과 비교.
    (c) 곡률법칙: 금속 **원기둥**(곡면)을 (테셀레이션 nseg) × (곡률반경 ρ) 로 흔든다.
                  Δθ/δ_acc ≈ 2R/ρ 이므로 **nseg 는 약분되고 ρ 만 남는다** — 예측은
                  'ρ ≳ 2R 이면 정반사가 산다'. 그대로 나오는지 본다.
    (d) 프롭 실측: 프롭 면의 등가 변 길이와 이웃 법선 간격을 재서 위 법칙에 대입한다.
    """
    u = look_dir(0.0, 15.0)
    out = {}

    sizes = (0.30, 0.10, 0.03, 0.01, 0.003)
    a = {}
    for R in RANGES:
        row = {}
        for s in sizes:
            sc, d = _one_obj_scene(_plate(s, u), f"PL{int(s*1000)}_{int(R)}")
            place(sc, 0.0, 15.0, R)
            row[f"{s*1000:.0f}mm"] = int(_n_spec(sc, spp))
            drop(d)
        a[f"{R:g}"] = row
    out["a_plate_size"] = dict(side_m=list(sizes), n_specular=a,
                               note_ko="법선이 정확히 맞으면 3 mm 평판도 잡는다 — 탐색기 자체는 살아 있다.")

    tilts = (0.0, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0)
    b = {}
    for R in RANGES:
        for s in (0.10, 0.01):
            got = {}
            for t in tilts:
                sc, d = _one_obj_scene(_plate(s, u, t), f"TL{int(s*1000)}_{int(R)}_{int(t*100)}")
                place(sc, 0.0, 15.0, R)
                got[f"{t:g}"] = int(_n_spec(sc, spp))
                drop(d)
            ok = [t for t in tilts if got[f"{t:g}"] > 0]
            pred = math.degrees(math.atan((s / 2) / R))
            b[f"{R:g}/{s*1000:.0f}mm"] = dict(
                range_m=float(R), side_m=float(s), n_specular_by_tilt_deg=got,
                last_tilt_with_specular_deg=(float(max(ok)) if ok else None),
                first_tilt_without_deg=next((float(t) for t in tilts if got[f"{t:g}"] == 0), None),
                predicted_delta_max_deg=float(pred))
    out["b_plate_tilt_acceptance"] = dict(
        tilt_deg=list(tilts), by_case=b,
        note_ko="δ_max ≈ atan((변/2)/R) — 평면 조각이 정반사를 내려면 법선이 이 안에 들어야 한다.")

    c = {}
    for R in RANGES:
        for nseg in (8, 64, 512, 4096):
            sc, d = _one_obj_scene(_cylinder(0.05, 0.20, nseg), f"CT{nseg}_{int(R)}")
            place(sc, 0.0, 15.0, R)
            c[f"{R:g}/nseg{nseg}"] = int(_n_spec(sc, spp))
            drop(d)
    out["c1_curved_tessellation"] = dict(
        radius_m=0.05, length_m=0.20, n_specular=c,
        note_ko=("곡률반경 5 cm 고정, 테셀레이션만 32~512배. Δθ/δ_acc = 2R/ρ 는 nseg 가 "
                 "약분되므로 **아무리 잘게 쪼개도 달라지지 않아야** 한다."))

    c2 = {}
    for R in RANGES:
        for rho in (0.05, 0.2, 1.0, 2.0, 5.0, 20.0, 100.0):
            sc, d = _one_obj_scene(_cylinder(rho, 0.20, 256), f"CR{int(rho*100)}_{int(R)}")
            place(sc, 0.0, 15.0, R)
            #  원기둥 표면이 원점에 오도록 — 표면 최상단을 시선 쪽으로 두려면 중심을 밀어야 하나,
            #  여기서는 반경을 키우면 표면이 멀어지므로 정반사 유무만 본다(거리 변화는 기록).
            c2[f"{R:g}/rho{rho:g}"] = dict(n_specular=int(_n_spec(sc, spp)),
                                           ratio_2R_over_rho=float(2 * R / rho),
                                           predicted_specular=bool(2 * R / rho <= 1.0))
            drop(d)
    out["c2_curvature_law"] = dict(
        by_case=c2, nseg=256, length_m=0.20,
        note_ko=("예측: 2R/ρ ≤ 1 (즉 R ≤ ρ/2) 일 때만 정반사가 산다. "
                 "⚠ 반경을 키우면 표면이 원점에서 멀어지므로 이 사다리는 '유무'만 읽는다."))

    m = posed_mesh(0.0)
    V = np.asarray(m.v, float); F = np.asarray(m.f, int); G = np.asarray(m.g, dtype=object)
    prop_stat = {}
    for grp in ("prop", "camera"):
        Fg = F[G == grp]
        if Fg.size == 0:
            continue
        nv = np.cross(V[Fg[:, 1]] - V[Fg[:, 0]], V[Fg[:, 2]] - V[Fg[:, 0]])
        A = 0.5 * np.linalg.norm(nv, axis=1)
        nn = nv / (np.linalg.norm(nv, axis=1, keepdims=True) + 1e-30)
        d_eq = np.sqrt(2 * A)
        sep = None
        try:
            from scipy.spatial import cKDTree
            dd_, _ = cKDTree(nn).query(nn, k=2)
            sep = np.degrees(2 * np.arcsin(np.clip(dd_[:, 1] / 2, 0, 1)))
        except Exception:
            pass
        prop_stat[grp] = dict(
            n_tris=int(A.size),
            tri_edge_median_mm=float(np.median(d_eq) * 1000.0),
            normal_neighbour_sep_median_deg=(float(np.median(sep)) if sep is not None else None),
            normal_neighbour_sep_p25_deg=(float(np.percentile(sep, 25)) if sep is not None else None),
            by_range={f"{R:g}": dict(
                acceptance_deg=float(math.degrees(math.atan((np.median(d_eq) / 2) / R))),
                sep_over_acceptance=(float(np.median(sep) /
                                           math.degrees(math.atan((np.median(d_eq) / 2) / R)))
                                     if sep is not None else None),
                specular_possible=bool(sep is not None and
                                       np.median(sep) <=
                                       math.degrees(math.atan((np.median(d_eq) / 2) / R))))
                for R in RANGES})
    out["d_prop_facet_stats"] = dict(
        by_group=prop_stat,
        note_ko=("법선간격/수용각 > 1 이면 '이등분선을 만족하는 면이 메쉬에 존재하지 않는다' — "
                 "즉 정반사가 원리적으로 안 나온다. camera 는 **평면**이라 이 비가 정의되지 않거나 "
                 "매우 작다(그래서 유일하게 글린트가 난다)."))
    return out


# --------------------------------------------------------------------------- #
#  §7 — 해석적 기준: '진짜' 블레이드 마이크로도플러는 이 관측량에서 어떤 모습인가
# --------------------------------------------------------------------------- #
def sec7_ideal(n_phase=N_PHASE) -> dict:
    """RT 를 쓰지 않고, 날개를 **점산란자 열**로 두고 h(φ) 를 해석적으로 만든다.
    같은 조화 분해를 걸어 '있어야 할 모습'의 짝수/홀수 비를 낸다 — RT 결과와 나란히 놓기 위함.
    ⚠ 이것은 **기준선이지 진리가 아니다**(등방 점산란자 가정)."""
    k = 2 * math.pi / LAM
    rl = rotor_layout(_SPEC)
    Rp = float(_SPEC.prop_dia_mm) / 2000.0
    blades = int(_SPEC.prop_blades)
    rr = np.linspace(0.25 * Rp, Rp, 12)            # 날개 스팬 위 점산란자
    w = rr / rr.sum()                              # 팁쪽 가중(면적·속도 대리)
    phis = np.arange(n_phase) * (360.0 / n_phase)
    res = {}
    for R in RANGES:
        for ak, az, el in ASPECTS:
            u = look_dir(az, el)
            tx = R * u + 0.5 * BASELINE_M * basis_perp(u)[0]
            rx = R * u - 0.5 * BASELINE_M * basis_perp(u)[0]
            z = np.zeros(n_phase, complex)
            for i, phd in enumerate(phis):
                s = 0j
                for rot, dirn in zip(rl, _DIRS):
                    c = np.array(rot["center"], float)
                    for b in range(blades):
                        ang = math.radians(rot["base_ang"] + dirn * phd + b * 360.0 / blades)
                        d = np.array([math.cos(ang), math.sin(ang), 0.0])
                        P = c[None, :] + rr[:, None] * d[None, :]
                        rng = (np.linalg.norm(tx - P, axis=1) + np.linalg.norm(rx - P, axis=1))
                        s += complex(np.sum(w * np.exp(-1j * k * rng)))
                z[i] = s
            H = _harmonics(z)
            adb = 20 * np.log10(np.abs(z) + 1e-300)
            Ha = _harmonics(adb - adb.mean())
            res[f"{R:g}/{ak}"] = dict(
                range_m=float(R), aspect=ak,
                even_over_odd_db=H["even_over_odd_db"],
                net_even_over_odd_db=H["net_even_over_odd_db"],
                dominant_even_harmonic=H["dominant_even_harmonic"],
                harm_abs_rel_dc=H["harm_abs_rel_dc"],
                absdb_ptp=float(adb.max() - adb.min()),
                absdb_even_over_odd_db=Ha["even_over_odd_db"])
    return dict(model="등방 점산란자 12개/날 × 2날 × 4로터, 가중 ∝ 반경",
                n_phase=int(n_phase), by_cell=res,
                note_ko=("이상적 블레이드 변조는 **짝수 조화가 홀수 조화를 압도**하고 고차까지 "
                         "퍼진다(팁 왕복위상 스윙이 λ 를 여러 번 넘기 때문). RT 결과의 조화 "
                         "구조를 이것과 비교하면 '블레이드 같은가' 를 눈이 아니라 수로 말할 수 있다."))


# --------------------------------------------------------------------------- #
#  §8 — 기선 통제 (거리 추세가 기선 각도 탓인가)
# --------------------------------------------------------------------------- #
def sec8_baseline_control(spp=SPP_MAIN, n_phase=16, seeds=(1, 2)) -> dict:
    """고정 기선 0.2 m 는 거리에 따라 바이스태틱 각이 변한다(R=1 에서 11.4°, R=10 에서 1.15°).
    거리 추세가 그 탓이 아님을 보이려면 **바이스태틱 각을 고정**한 대조가 필요하다 —
    기선을 R 에 비례시켜 R=3 의 각도로 맞춘다."""
    phis = np.arange(n_phase) * (360.0 / n_phase)
    base_at3 = BASELINE_M
    out = {}
    store = {f"{R:g}": dict(n=[], amp=[], inc=[]) for R in RANGES}
    for i, phd in enumerate(phis):
        scene, dd = build_posed_scene(float(phd), f"B{i:02d}")
        g2 = id_to_group(scene)
        for R in RANGES:
            bl = base_at3 * R / 3.0
            place(scene, 0.0, 15.0, R, baseline=bl)
            v = [trace(scene, spp, s, True, g2) for s in seeds]
            store[f"{R:g}"]["n"].append([r["n"] for r in v])
            store[f"{R:g}"]["amp"].append([db_amp(r["hr"], r["hi"]) if r["n"] else None
                                           for r in v])
            store[f"{R:g}"]["inc"].append([r["inc"] for r in v])
        drop(dd)
    for R in RANGES:
        s = store[f"{R:g}"]
        amp = np.array([[np.nan if x is None else x for x in row] for row in s["amp"]], float)
        inc = np.array([[np.nan if x is None else x for x in row] for row in s["inc"]], float)
        n = np.array(s["n"], float)
        pm = np.nanmean(amp, axis=1)
        out[f"{R:g}"] = dict(
            range_m=float(R), baseline_m=float(base_at3 * R / 3.0),
            bistatic_deg=float(2 * math.degrees(math.atan(0.5 * base_at3 / 3.0))),
            n_paths_mean=float(n.mean()), zero_frac=float(np.mean(n == 0)),
            amp_db_mean=float(np.nanmean(pm)),
            modulation_ptp_db=float(np.nanmax(pm) - np.nanmin(pm)),
            seed_noise_std_db=float(np.nanmean(np.nanstd(amp, axis=1, ddof=1))),
            inc_db_mean=float(np.nanmean(inc)),
            inc_modulation_ptp_db=float(np.nanmax(np.nanmean(inc, axis=1))
                                        - np.nanmin(np.nanmean(inc, axis=1))))
    return dict(n_phase=int(n_phase), seeds=[int(s) for s in seeds], spp=int(spp),
                az_deg=0.0, el_deg=15.0, by_range=out,
                note_ko="바이스태틱 각을 R=3 의 값으로 고정한 대조. 본 격자는 기선 0.2 m 고정이다.")


# --------------------------------------------------------------------------- #
#  헤드라인
# --------------------------------------------------------------------------- #
def headline(J: dict) -> dict:
    A = J["grid_analysis"]["by_block"]
    cen = J["grid_analysis"]["zero_path_census"]
    ph = J["physics"]
    sc = J["specular_census"]["production"]
    sig = sorted([k for k, v in A.items() if v.get("modulation_above_noise")])
    per_cell = {}
    for k, v in A.items():
        if v.get("ok"):
            per_cell[k] = dict(
                n_paths_behaviour=v["n_paths_behaviour"],
                zero_path_cell_frac=v["zero_path_cell_frac"],
                modulation_ptp_db=v.get("modulation_ptp_db"),
                seed_noise_std_db=v.get("seed_noise_std_db"),
                sym_null_rms_db=v.get("sym_null_rms_db"),
                net_even_over_odd_db=(v.get("harmonics_complex") or {}).get("net_even_over_odd_db"),
                verdict=v["verdict"])
    cv = J["convergence"]["by_range"]
    return dict(
        drone=KEY, name=_SPEC.name, fc_ghz=FC / 1e9,
        ranges_m=list(RANGES), n_phase_steps_per_rev=int(ph["n_phase_steps_per_rev"]),
        aspects=[a for a, _, _ in ASPECTS], seeds_per_cell=len(SEEDS), spp=int(SPP_MAIN),
        # ⭐ 로터 재질
        rotor_material_key=J["materials"]["by_group"]["prop"]["material_key"],
        rotor_is_metal=bool(J["materials"]["by_group"]["prop"]["sionna_kind"].startswith("ITU")),
        rotor_gamma_bulk=J["materials"]["by_group"]["prop"]["gamma_bulk_fresnel"],
        rotor_gamma_db_vs_pec=J["materials"]["by_group"]["prop"]["gamma_db_vs_pec"],
        # ⭐ 원거리장
        farfield_2D2_lam_m=ph["farfield_2D2_lam_m"] if "farfield_2D2_lam_m" in ph
        else ph["by_range"]["3"]["farfield_2D2_lam_m"],
        in_farfield_by_range={k: v["in_farfield"] for k, v in ph["by_range"].items()},
        # ⭐ 주기
        rotor_period_deg=ph["phase_period_deg"],
        symmetry_null_valid=J["period_check"]["symmetry_null_valid"],
        aliased=ph["aliased"], alias_margin=ph["alias_margin"],
        n_steps_min_for_nyquist=ph["n_steps_min_for_nyquist"],
        # ⭐ 정반사
        zero_path_census=cen,
        specular_cells_frac=sc["frac_cells_with_specular"],
        prop_specular_cells_frac=sc["frac_cells_with_prop_specular"],
        specular_paths_by_group=sc["specular_paths_by_group"],
        prop_specular_with_pec=(J["specular_census"].get("pec_prop") or {})
        .get("frac_cells_with_prop_specular"),
        # ⭐ 수렴성
        coherent_slope_by_range={k: v["coh_slope_log10h_per_log10N"] for k, v in cv.items()},
        incoherent_converged_by_range={k: v["inc_converged"] for k, v in cv.items()},
        coherent_converged_by_range={k: v["coh_converged"] for k, v in cv.items()},
        # ⭐ 판정
        channels_significant=sig, n_channels_significant=len(sig),
        n_channels_total=len(A),
        by_cell=per_cell)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phases", type=int, default=N_PHASE)
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--spp", type=int, default=SPP_MAIN)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-grid", action="store_true")
    a = ap.parse_args()

    n_phase = a.phases
    seeds = tuple(range(1, a.seeds + 1))
    spp = int(a.spp)
    if a.quick:
        n_phase, seeds, spp = 8, (1, 2), 64_000_000

    os.makedirs(SCRATCH, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    t_all = time.time()

    J = dict(meta=dict(
        script="benchmark/report15_sweep_matrice4e.py",
        drone=KEY,
        question=("스톡 Sionna PathSolver 가 로터 위상을 스텝하고 매번 재추적했을 때 "
                  "블레이드 마이크로도플러를 내는가 (거리 1·3·10 m 스윕)"),
        settled_branch_1=("① Paths.doppler 로 자동으로는 **아니다** — SceneObject.velocity 는 "
                          "객체당 3성분 강체 1벡터라 회전 자유도가 없다. "
                          "outputs/report15_probe.json §A 에서 실측(velocity_dof_per_object=3, "
                          "프롭에 강체속도를 줘도 전 경로가 같은 부호·같은 크기 도플러). 재측정 안 함."),
        open_branch_2="② 위상 스텝 + 재추적으로 h(φ) 를 이어붙이면 나오나 — 이 파일이 그것을 잰다.",
        observable=("h_coh = Σ_p a_p·exp(−j2πf_c τ_p) (코히런트) / E_inc = Σ_p|a_p|² (위상무관). "
                    "Paths.a 는 패스밴드라 전파위상이 없다. Paths.cir() 은 normalize_delays=True 로 "
                    "절대위상을 지우므로 쓰지 않는다."),
        symmetry_null=("2날 → φ 와 φ+180° 는 기하가 동일. 한 바퀴 FFT 에서 **홀수 조화는 0 이 "
                       "보장된 자리** → 내장 잡음바닥. 짝수 조화만 물리를 실을 수 있다."),
        fc_hz=FC, lambda_m=LAM, baseline_m=BASELINE_M, max_depth=1,
        ranges_m=list(RANGES),
        aspects=[dict(name=n, az_deg=az, el_deg=el) for n, az, el in ASPECTS],
        n_phase_steps=int(n_phase), seeds=list(seeds), spp=int(spp),
        max_num_paths_per_src=MAX_PATHS, spp_max_safe=int(SPP_MAX_SAFE),
        spp_cap_reason="samples_per_src 는 uint32 — 2³²−1 초과 시 Sionna 가 TypeError",
        sionna_version=getattr(sionna, "__version__", "?"),
        mitsuba_version=getattr(mi, "__version__", "?"),
        mitsuba_variant=mi.variant(),
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        gpu_status_at_start=gpu_status(),
        materials="production per-group (DRONE_GROUP_MAT)",
        prior="WiFi-JEPA arXiv:2607.11064 — frame 당 20 pass 로 시간축 생성",
        related=["outputs/report15_probe.json", "outputs/facet_count.json"],
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")))

    def save():
        with open(OUT_JSON, "w") as f:
            json.dump(J, f, ensure_ascii=False, indent=1)

    print("\n§0  물리·재질·기하 …", flush=True)
    J["physics"] = sec0_physics(n_phase)
    J["farfield_table"] = sec0_farfield_table()
    J["materials"] = sec0_materials()
    J["prop_normals"] = sec0_prop_normals()
    p = J["physics"]
    print(f"    D={p['D_horizontal_m']:.3f} m  2D²/λ={p['by_range']['3']['farfield_2D2_lam_m']:.3f} m")
    for k, v in p["by_range"].items():
        print(f"      R={k:>4} m  원거리장 {'OK' if v['in_farfield'] else '미달'}  "
              f"입체각비 {v['solid_angle_frac']:.3e}  표적광선 {v['rays_on_target_at_main_spp']:,.0f}  "
              f"바이스태틱 {v['bistatic_deg_at_fixed_baseline']:.2f}°  "
              f"τ위상양자 {v['tau_float32_phase_quantum_deg']:.4f}°")
    print(f"    f_tip={p['f_tip_hz']:.0f} Hz  등가PRF={p['equivalent_prf_hz']:.0f} Hz  "
          f"접힘={p['aliased']} (여유 {p['alias_margin']:.2f}×, 최소스텝 {p['n_steps_min_for_nyquist']})")
    print("    " + J["materials"]["rotor_verdict_ko"], flush=True)
    save()

    print("\n§1  로터 주기·대칭 널 …", flush=True)
    J["period_check"] = sec1_period()
    pc = J["period_check"]
    print(f"    원소별 0↔180 최대차 {pc['elementwise_max_dev_0_vs_180_m']:.3e} m / "
          f"집합 {pc['setwise_max_dev_0_vs_180_m']:.3e} m → 대칭 널 유효={pc['symmetry_null_valid']}  "
          f"(0↔360 원소별 {pc['elementwise_max_dev_0_vs_360_m']:.3e} m)", flush=True)
    save()

    print("\n§4  ⭐ 수렴성 (코히런트 합이 수렴하나) …", flush=True)
    J["convergence"] = sec4_convergence()
    for k, v in J["convergence"]["by_range"].items():
        print(f"    R={k:>4} m  |h| 기울기 {v['coh_slope_log10h_per_log10N']:.3f} "
              f"(0=수렴, 0.5=√N)  총스윙 코히런트 {v['coh_total_swing_db']:+.2f} dB / "
              f"위상무관 {v['inc_total_swing_db']:+.3f} dB  → 수렴 코히런트={v['coh_converged']} "
              f"위상무관={v['inc_converged']}", flush=True)
    save()

    print("\n§5  정반사 인구조사 (거리 × 자세 × 위상, 생산재질) …", flush=True)
    J["specular_census"] = dict(production=sec5_specular_census(
        spp=spp, phases=(0.0, 22.5, 45.0, 67.5) if not a.quick else (0.0,)))
    s = J["specular_census"]["production"]
    print(f"    정반사 칸 {s['n_cells_with_specular']}/{s['n_cells']} "
          f"({100*s['frac_cells_with_specular']:.2f}%)  프롭 정반사 칸 "
          f"{s['n_cells_with_prop_specular']} ({100*s['frac_cells_with_prop_specular']:.2f}%)  "
          f"부위별 {s['specular_paths_by_group']}", flush=True)
    save()

    print("\n§5b 재질 반사실 — 프롭을 PEC(metal)로 바꾸면 정반사가 생기나 …", flush=True)
    J["specular_census"]["pec_prop"] = sec5_specular_census(
        spp=spp, phases=(0.0, 45.0) if not a.quick else (0.0,), prop_mat="metal")
    s2 = J["specular_census"]["pec_prop"]
    print(f"    (PEC 프롭) 정반사 칸 {s2['n_cells_with_specular']}/{s2['n_cells']}  "
          f"프롭 정반사 칸 {s2['n_cells_with_prop_specular']}  "
          f"부위별 {s2['specular_paths_by_group']}", flush=True)
    save()

    print("\n§6  기구 — 정반사 수용각·곡률 법칙 …", flush=True)
    J["mechanism"] = sec6_mechanism()
    for kk, vv in J["mechanism"]["b_plate_tilt_acceptance"]["by_case"].items():
        print(f"    수용각 {kk}: 실측 마지막성공 {vv['last_tilt_with_specular_deg']}° / "
              f"예측 {vv['predicted_delta_max_deg']:.3f}°", flush=True)
    print(f"    곡률법칙 {J['mechanism']['c2_curvature_law']['by_case']}", flush=True)
    for g, v in J["mechanism"]["d_prop_facet_stats"]["by_group"].items():
        print(f"    {g}: 삼각형 등가변 {v['tri_edge_median_mm']:.2f} mm  "
              f"법선간격 {v['normal_neighbour_sep_median_deg']}°  "
              f"→ " + "  ".join(f"R={k}:비 {x['sep_over_acceptance']:.1f}"
                                for k, x in v["by_range"].items()), flush=True)
    save()

    print("\n§7  해석적 기준(이상적 블레이드 변조) …", flush=True)
    J["ideal_reference"] = sec7_ideal(n_phase)
    save()

    if not a.skip_grid:
        print(f"\n§2  ⭐ 본 격자 — {len(RANGES)}거리 × {len(ASPECTS)}자세 × {n_phase}위상 × "
              f"{len(seeds)}시드 × {len(MODES)}채널 …", flush=True)
        J["grid"] = sec2_grid(n_phase=n_phase, seeds=seeds, spp=spp)
        save()
        print("\n§3  격자 분석 …", flush=True)
        J["grid_analysis"] = sec3_analyze(J["grid"])
        for k, v in sorted(J["grid_analysis"]["by_block"].items()):
            if not v.get("ok"):
                print(f"    {k:34s}  {v['verdict']}  (0경로 {100*v['zero_path_cell_frac']:.0f}%)")
                continue
            print(f"    {k:34s}  n̄={v['n_paths_mean']:9.1f}  ptp={v['modulation_ptp_db']:6.3f} dB  "
                  f"시드σ={v['seed_noise_std_db']:6.3f}  대칭널={v['sym_null_rms_db']:6.3f}  "
                  f"짝/홀={v['harmonics_complex']['net_even_over_odd_db']:7.2f} dB  → {v['verdict']}",
                  flush=True)
        print(f"    0-경로 인구조사: {J['grid_analysis']['zero_path_census']}", flush=True)
        save()

        print("\n§8  기선 통제 …", flush=True)
        J["baseline_control"] = sec8_baseline_control(spp=spp,
                                                      n_phase=16 if not a.quick else 4)
        save()

        J["headline"] = headline(J)
        save()

    J["meta"]["seconds_total"] = float(time.time() - t_all)
    J["meta"]["gpu_status_at_end"] = gpu_status()
    save()
    drop(SCRATCH)
    print(f"\n✅ 저장 → {OUT_JSON}   ({J['meta']['seconds_total']:.0f}s)")
    return J


if __name__ == "__main__":
    main()
