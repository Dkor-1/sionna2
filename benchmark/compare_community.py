# -*- coding: utf-8 -*-
"""
compare_community.py — **커뮤니티 구형 DJI 메쉬 vs 우리 파라메트릭 방법** (점검용)
==================================================================================
사용자 지시(2026-07-14): 커뮤니티에 구형 Mavic/Matrice 모델이 있으면 받아서 **점검** 하고,
구형 스펙시트를 자세히 확인해 **신형과 다를 수 있음을 성실히 명시**한 뒤 우리 메쉬와 비교.

■ 확보한 커뮤니티 메쉬 (github: TareqAlqutami/dji_ros_simulator, DJI Onboard-SDK HITL 용)
  · **DJI Matrice 100** (2015 쿼드) — dji_m100.dae
  · **DJI Matrice 600 Pro** (2016 헥사) — dji_m600.dae
  둘 다 **시각용 셸**(watertight 아님, 내부 금속 없음) → Typhoon 때와 같이 **PEC 형상만** 비교.
  · Mavic 2 Pro 는 Webots **PROTO 참조형**이라 삼각형 메쉬로 추출 불가 → 비교 제외(스펙만 기록).

■ ⚠ 신형 vs 구형 — 성실한 차이 명시 (이건 검증이 아니라 '방법 점검'인 이유)
  우리가 **실제로 쓰는** 드론과 이 구형들은 **완전히 다른 기체**다:
    · Matrice 100(2015): 대각 650 mm, 4로터, **비접이식**, 개발자 플랫폼, GPS 마스트 돌출
      ↔ 우리 **Matrice 4E**(2025): 대각 438.8 mm, 4로터, **접이식**, 컴팩트 엔터프라이즈. → 완전 다름.
    · Matrice 600 Pro(2016): 대각 1133 mm, **6로터**, 21" 프롭, 9.5 kg 대형
      ↔ 우리엔 대응 기종 없음(가장 가까운 s1000plus 는 8로터). → 다름.
    · Mavic 2 Pro(2018): 대각 354 mm ↔ 우리 **Mavic 4 Pro**(2025): 대각 ~440 mm(외형서 유도). → 다름.
  → 그래서 이 비교는 우리 **신형 모델의 검증이 아니라**, "우리 파라메트릭 *방법*이 **같은 구형 드론**의
    공식 스펙을 받으면 독립 커뮤니티 메쉬를 재현하는가" 라는 **방법 점검**이다.

■ 공식 스펙시트 (dji.com / dronespec datasheet, 2026-07-14 확인)
  M100     : 대각 650 mm · 프롭 DJI 1345(13.45"=342 mm) · 모터 3510 · 4로터 · 2431 g(TB47S 6셀)
  M600 Pro : 대각 1133 mm · 프롭 DJI 2170R(21"=533 mm) · 모터 6010 · 6로터 · 9.5 kg
  Mavic2Pro: 대각 354 mm · 프롭 8.7"(≈221 mm) · 907 g · 언폴드 322×242×84 mm

실행:  python benchmark/compare_community.py   → outputs/community_compare.json
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.abspath(os.path.join(_HERE, "..", "src")), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                    # noqa: E402
import trimesh                                        # noqa: E402

from mesh_compare import compare                      # noqa: E402
from drones import DroneSpec                          # noqa: E402
import drone_cad                                      # noqa: E402
from drones import rotor_layout                       # noqa: E402

COMM = "/tmp/claude-1015/-home-yunjung-workspace/ffa746a7-b94b-40cf-b506-e335cf593125/scratchpad/community/dji_ros_simulator/dji_drone_description/meshes"
OUT = os.path.abspath(os.path.join(_HERE, "..", "outputs", "community_compare.json"))

#  공식 스펙 → DroneSpec (구형 실물)
M100 = DroneSpec(
    key="dji_m100", name="DJI Matrice 100 (2015 quad)",
    diagonal_mm=650, weight_g=2431,
    body_l_mm=280, body_w_mm=280, body_h_mm=230,      # 중앙 프레임 + GPS 마스트(대략)
    prop_dia_mm=342, prop_blades=2, num_rotors=4,     # DJI 1345 = 13.45"
    hover_rpm=4500, max_rpm=7000, prop_pitch_in=4.5,
    arm_style="body", gear="legs", gimbal="belly",
    rotor_deg=(45, 135, 225, 315), body_lw=(1.0, 1.0), gimbal_style="belly",
    envelope_mm=None)
M600 = DroneSpec(
    key="dji_m600", name="DJI Matrice 600 Pro (2016 hexa)",
    diagonal_mm=1133, weight_g=9500,
    body_l_mm=430, body_w_mm=430, body_h_mm=350,
    prop_dia_mm=533, prop_blades=2, num_rotors=6,     # DJI 2170R = 21"
    hover_rpm=3000, max_rpm=5000, prop_pitch_in=7.0,
    arm_style="carbon", gear="tall", gimbal="belly",
    rotor_deg=(30, 90, 150, 210, 270, 330), body_lw=(1.0, 1.0), gimbal_style="belly",
    envelope_mm=None)


def ours_full(spec) -> trimesh.Trimesh:
    """우리 CAD 툴킷으로 이 스펙의 **전체 드론**(프레임+프롭)을 만든다 (커뮤니티 메쉬 안 보고)."""
    A = drone_cad.build_frame_cad(spec)
    P = drone_cad.build_propeller_cad(spec)
    parts = [m for ms in A.parts.values() for m in ms]
    prop_ms = [m for ms in P.parts.values() for m in ms]
    for rot in rotor_layout(spec):
        cx, cy, cz = rot["center"]
        for pm in prop_ms:
            q = pm.copy()
            q.apply_transform(trimesh.transformations.rotation_matrix(
                np.radians(rot["base_ang"]), [0, 0, 1]))
            q.apply_translation([cx, cy, cz])
            parts.append(q)
    m = trimesh.util.concatenate(parts)
    m.apply_translation(-m.bounds.mean(axis=0))
    return m


def load_community(fn) -> trimesh.Trimesh:
    """커뮤니티 .dae (미터 단위) → 원점중심 trimesh."""
    m = trimesh.load(os.path.join(COMM, fn), force="mesh")
    m.apply_translation(-m.bounds.mean(axis=0))
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    trimesh.repair.fix_normals(m)
    return m


def one(spec, comm_fn, tag):
    print("=" * 92)
    print(f"[{tag}] {spec.name} — 커뮤니티 메쉬 vs 우리 파라메트릭(공식 스펙에서)")
    print("=" * 92)
    real = load_community(comm_fn)
    ours = ours_full(spec)
    br = (real.bounds[1] - real.bounds[0]) * 1000
    bo = (ours.bounds[1] - ours.bounds[0]) * 1000
    print(f"  커뮤니티 : {len(real.faces):>7,d}면  {br[0]:6.0f} x {br[1]:6.0f} x {br[2]:6.0f} mm")
    print(f"  우리 메쉬 : {len(ours.faces):>7,d}면  {bo[0]:6.0f} x {bo[1]:6.0f} x {bo[2]:6.0f} mm")
    print(f"  공식 대각 {spec.diagonal_mm} mm · 프롭 {spec.prop_dia_mm} mm · {spec.num_rotors}로터")
    print("  ...SBR 로 방위 48점 σ 비교 (양쪽 PEC — 형상만)")
    r = compare(real, ours, fc=3.5e9, el=15.0, n_az=48,
                name_real=f"{spec.name} (community mesh)",
                name_ours=f"{spec.name} (ours from spec)")
    r["bbox_real_mm"] = br.tolist(); r["bbox_ours_mm"] = bo.tolist()
    r["diagonal_mm"] = spec.diagonal_mm; r["prop_dia_mm"] = spec.prop_dia_mm
    print(f"\n  최대치수(프롭포함) 비: 우리/커뮤니티 = "
          f"{bo.max()/br.max():.2f}  ({20*np.log10(bo.max()/br.max()):+.1f} dB)")
    print(f"  투영면적 : 커뮤니티 {r['area_mean_real']*1e4:6.0f} cm2  "
          f"우리 {r['area_mean_ours']*1e4:6.0f} cm2   → **{r['d_area_db']:+.2f} dB**")
    print(f"  SBR σ    : 커뮤니티 {r['sigma_mean_real_dbsm']:+6.2f} dBsm  "
          f"우리 {r['sigma_mean_ours_dbsm']:+6.2f} dBsm  → **{r['d_sigma_db']:+.2f} dB**")
    print(f"  방위각별 σ 차이 RMS : {r['d_sigma_rms_db']:.2f} dB")
    return r


def main():
    res = {}
    res["m100"] = one(M100, "dji_m100.dae", "A")
    print()
    res["m600"] = one(M600, "dji_m600.dae", "B")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print(f"\n→ {os.path.relpath(OUT)}")
    print("\n⚠ 다시 강조: 이 구형들은 우리가 실제 쓰는 신형(Matrice 4E·Mavic 4 Pro)과 **완전히 다른 기체**다.")
    print("   이건 신형 모델의 검증이 아니라, 우리 **파라메트릭 방법**이 같은 구형의 공식 스펙으로")
    print("   독립 커뮤니티 메쉬를 얼마나 재현하는가의 **점검**이다.")


if __name__ == "__main__":
    main()
