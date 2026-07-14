# -*- coding: utf-8 -*-
"""
gazebo_export.py — **드론 메쉬를 Gazebo / PX4 SITL 모델로 내보낸다**
======================================================================
우리 메쉬는 처음부터 **Gazebo 구조**로 짜여 있다:
    build_frame(spec)      -> base_link  (동체 + 암 + 모터 + 짐벌 + 다리 — 안 도는 부분)
    build_propeller(spec)  -> rotor_N    (도는 부분, 허브가 원점)
    rotor_layout(spec)     -> 각 로터의 (위치, 장착각, 회전방향 ±1)
그래서 **링크 분리 · 관절 배치 · 회전방향**이 이미 준비돼 있다. 이 모듈이 나머지를 채운다.

■ Gazebo/PX4 가 요구하는 것과, 우리가 어떻게 채우는가
  | 필요한 것 | 어떻게 |
  |---|---|
  | `<visual>` 메쉬 | 우리 CAD 메쉬를 **STL 로 내보낸다** (링크별) |
  | `<collision>` 메쉬 | **볼록껍질(convex hull) + 데시메이션** — Gazebo 물리엔진은 단순 형상을 원한다 |
  | `<inertial>` (질량·CoM·관성텐서) | **trimesh 가 계산한다.** 부위별 밀도를 주고 평행축 정리로 합산 |
  | 로터 `<joint>` (revolute, z축) | rotor_layout 의 center/base_ang |
  | PX4 `gazebo_motor_model` 플러그인 | motor_constant k_T, moment_constant k_M, max_rot_velocity, rotor_inertia … |

■ 관성텐서를 **지어내지 않는다**
  DJI 는 관성모멘트를 공개하지 않는다. 그래서 **메쉬에서 계산한다**:
    1. 부위(그룹)별로 **밀도**를 준다 — 배터리·모터는 무겁고 셸은 가볍다
    2. trimesh 의 mass_properties 로 각 파트의 질량·CoM·관성텐서를 얻는다
    3. **평행축 정리**로 전체 CoM 기준 관성텐서를 합산한다
    4. **총질량이 공식 이륙중량(TOW)이 되도록 밀도를 일괄 스케일** — 이러면 질량은 공식값이고
       질량 **분포**만 우리 메쉬가 정한다. 이게 가장 정직한 방법이다.
  → 나온 값은 **추정**이다. 그렇게 표시한다.

■ 추력계수 k_T
  T = k_T · omega^2.  호버에서 T = m·g/N_rotor, omega = 2*pi*hover_rpm/60
    => k_T = m·g / (N · omega_hover^2)
  검산: omega_max 에서 T/W 가 2 근처면 타당하다(소형 멀티로터 전형).

실행:  python src/gazebo_export.py              (5종 전부 models/ 아래로)
       python src/gazebo_export.py mavic4pro    (1종만)
출력:  outputs/gazebo/<key>/model.sdf, model.config, meshes/*.stl
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np                      # noqa: E402
import trimesh                          # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs", "gazebo")
G = 9.80665
RHO_AIR = 1.225


# --------------------------------------------------------------------------- #
#  부위별 밀도 [kg/m^3] — 질량 **분포**를 정한다 (총질량은 나중에 공식 TOW 로 맞춘다)
# --------------------------------------------------------------------------- #
#  근거: 실제 부품의 대표 밀도. 정확한 값이 아니라 **상대적 무게 배분**이 목적이다.
DENSITY = {
    "battery": 2200.0,   # Li-ion 파우치 팩 (셀 + 알루미늄 케이스)
    "motor": 4500.0,     # 아웃러너 — 강판 벨 + NdFeB 자석 + 구리 권선
    "pcb": 1900.0,       # FR-4 + 구리
    "camera": 2600.0,    # 금속 하우징 + 유리 렌즈 + 짐벌 모터
    "arm": 1550.0,       # 카본 파이버
    "body": 1150.0,      # ABS/PC 사출 셸 (속이 빈 껍데기라 실효 밀도는 낮다)
    "canopy": 1150.0,
    "gear": 1150.0,
    "accent": 1150.0,
    "prop": 1300.0,      # 유리섬유 강화 나일론
}


def _mass_props(m: trimesh.Trimesh, density: float):
    """파트 하나의 (질량, CoM, 원점기준 관성텐서). trimesh 가 계산한다."""
    mm = m.copy()
    mm.density = float(density)
    return float(mm.mass), np.asarray(mm.center_mass, float), np.asarray(mm.moment_inertia, float)


def _parallel_axis(I_com, mass, d):
    """평행축 정리 — CoM 기준 관성텐서를 거리 d 만큼 떨어진 축으로 옮긴다."""
    d = np.asarray(d, float)
    return I_com + mass * (float(d @ d) * np.eye(3) - np.outer(d, d))


def inertia_from_mesh(spec, target_mass_kg=None):
    """**메쉬에서 질량·CoM·관성텐서를 계산한다.** 총질량을 공식 TOW 로 맞춘다.

    반환: dict(mass, com, I(3x3), per_group, density_scale)"""
    from drone_cad import build_frame_cad, build_propeller_cad
    from drones import rotor_layout, frame_fit_scale

    A = build_frame_cad(spec)
    sx, sy, sz = frame_fit_scale(spec)
    if (sx, sy, sz) != (1.0, 1.0, 1.0):
        A.scaled(sx, sy, sz)

    parts = []                                    # (group, mesh)
    for g, ms in A.parts.items():
        for m in ms:
            parts.append((g, m))
    # 프로펠러 — 로터마다 하나
    P = build_propeller_cad(spec)
    prop_ms = [m for ms in P.parts.values() for m in ms]
    for rot in rotor_layout(spec):
        for pm in prop_ms:
            q = pm.copy()
            q.apply_transform(trimesh.transformations.rotation_matrix(
                np.radians(rot["base_ang"]), [0, 0, 1]))
            q.apply_translation(rot["center"])
            parts.append(("prop", q))

    # 1) 부위별 질량·CoM·관성
    rows = []
    for g, m in parts:
        d = DENSITY.get(g, 1200.0)
        try:
            mass, com, I = _mass_props(m, d)
        except Exception:
            continue
        if not np.isfinite(mass) or mass <= 0:
            continue
        rows.append(dict(group=g, mass=mass, com=com, I=I))

    m_raw = sum(r["mass"] for r in rows)
    target = float(target_mass_kg if target_mass_kg else spec.weight_g / 1000.0)
    k = target / m_raw if m_raw > 0 else 1.0        # **밀도 일괄 스케일** → 총질량 = 공식 TOW

    # 2) 전체 CoM
    com = sum(r["mass"] * k * r["com"] for r in rows) / target

    # 3) 평행축 정리로 CoM 기준 관성텐서 합산
    I = np.zeros((3, 3))
    for r in rows:
        mi = r["mass"] * k
        I += _parallel_axis(r["I"] * k, mi, r["com"] - com)

    per_group = {}
    for r in rows:
        per_group.setdefault(r["group"], 0.0)
        per_group[r["group"]] += r["mass"] * k

    return dict(mass=target, com=com, I=I, per_group=per_group, density_scale=k,
                n_parts=len(rows))


def motor_constants(spec, mass_kg=None):
    """**추력계수 k_T · 모멘트계수 k_M** — 호버 조건에서 유도한다 (지어내지 않는다).
        T_hover = m*g / N,   omega_hover = 2*pi*rpm/60
        k_T = T_hover / omega_hover^2          [N*s^2/rad^2]
        k_M = moment_constant * k_T            (moment_constant [m] 은 프롭 전형값)
    검산으로 max_rpm 에서의 T/W 를 함께 낸다 — 2 근처면 타당하다."""
    m = float(mass_kg if mass_kg else spec.weight_g / 1000.0)
    N = int(spec.num_rotors)
    w_h = 2 * np.pi * float(spec.hover_rpm) / 60.0
    T_h = m * G / N
    kT = T_h / (w_h ** 2)
    # moment_constant [m]: 프롭 지름에 대략 비례. 소형 6인치 0.016, 대형 15인치 0.06 근방.
    D = spec.prop_dia_mm / 1000.0
    moment_const = float(np.clip(0.06 * D, 0.010, 0.070))
    w_max = 2 * np.pi * float(spec.max_rpm or spec.hover_rpm * 1.6) / 60.0
    T_max = kT * w_max ** 2
    # 프로펠러 관성 — 메쉬에서
    from drone_cad import build_propeller_cad
    P = build_propeller_cad(spec)
    pm = trimesh.util.concatenate([m2 for ms in P.parts.values() for m2 in ms])
    pm.density = DENSITY["prop"]
    Izz_prop = float(np.asarray(pm.moment_inertia)[2, 2])
    return dict(
        motor_constant=float(kT), moment_constant=moment_const,
        max_rot_velocity=float(w_max), hover_rot_velocity=float(w_h),
        rotor_inertia=Izz_prop, prop_mass_kg=float(pm.mass),
        thrust_hover_N=float(T_h), thrust_max_N=float(T_max),
        thrust_to_weight_max=float(T_max * N / (m * G)),
        time_constant_up=0.0125, time_constant_down=0.025,   # 소형 BLDC 전형 (추정)
        rotor_drag_coefficient=8.06428e-05,                  # rotors_simulator 기본값
        rolling_moment_coefficient=1e-06,
    )


# --------------------------------------------------------------------------- #
#  SDF 생성
# --------------------------------------------------------------------------- #
def _collision_hull(m: trimesh.Trimesh, max_faces=600) -> trimesh.Trimesh:
    """충돌용 **볼록껍질 + 데시메이션** — Gazebo 물리엔진은 단순 형상을 원한다."""
    try:
        h = m.convex_hull
        if len(h.faces) > max_faces:
            h = h.simplify_quadric_decimation(face_count=max_faces)
        return h
    except Exception:
        return m.bounding_box_oriented


def export(spec, outdir=None, verbose=True):
    """드론 1종 → Gazebo 모델 디렉터리 (model.sdf + model.config + meshes/*.stl)."""
    from drone_cad import build_frame_cad, build_propeller_cad
    from drones import rotor_layout, frame_fit_scale

    key = spec.key
    d = outdir or os.path.join(OUT, key)
    md = os.path.join(d, "meshes")
    os.makedirs(md, exist_ok=True)

    # ---- 메쉬 (base_link + rotor) --------------------------------------------
    A = build_frame_cad(spec)
    sx, sy, sz = frame_fit_scale(spec)
    if (sx, sy, sz) != (1.0, 1.0, 1.0):
        A.scaled(sx, sy, sz)
    base = trimesh.util.concatenate([m for ms in A.parts.values() for m in ms])
    P = build_propeller_cad(spec)
    prop = trimesh.util.concatenate([m for ms in P.parts.values() for m in ms])

    base.export(os.path.join(md, "base_link.stl"))
    prop.export(os.path.join(md, "rotor.stl"))
    _collision_hull(base).export(os.path.join(md, "base_link_collision.stl"))
    _collision_hull(prop, 200).export(os.path.join(md, "rotor_collision.stl"))

    # ---- 질량·관성 ------------------------------------------------------------
    MP = inertia_from_mesh(spec)
    MC = motor_constants(spec, MP["mass"])
    I = MP["I"]
    com = MP["com"]
    rl = rotor_layout(spec)

    # 로터 링크의 질량/관성 (프롭만)
    prop.density = DENSITY["prop"]
    m_rot = float(prop.mass) * MP["density_scale"]
    I_rot = np.asarray(prop.moment_inertia) * MP["density_scale"]
    # base_link 질량 = 총질량 - 로터 질량 합
    m_base = MP["mass"] - m_rot * len(rl)

    L = []
    L.append('<?xml version="1.0" ?>')
    L.append('<sdf version="1.9">')
    L.append(f'  <model name="{key}">')
    L.append('    <!-- 자동 생성: src/gazebo_export.py -->')
    L.append('    <!-- 메쉬: src/drone_cad.py (trimesh + manifold3d + shapely + scipy) -->')
    L.append(f'    <!-- 제원 출처: docs/drone_specs_2026.json (공식 DJI + 적대적 검증) -->')
    L.append('    <!-- ⚠ 질량 분포/관성텐서는 **메쉬에서 계산한 추정치**다. DJI 는 공개하지 않는다. -->')
    L.append(f'    <!--   총질량만 공식 TOW({spec.weight_g:.0f} g)에 맞췄고, 분포는 부위별 밀도가 정했다. -->')
    L.append('')
    L.append('    <link name="base_link">')
    L.append(f'      <pose>0 0 0 0 0 0</pose>')
    L.append('      <inertial>')
    L.append(f'        <mass>{m_base:.6f}</mass>')
    L.append(f'        <pose>{com[0]:.6f} {com[1]:.6f} {com[2]:.6f} 0 0 0</pose>')
    L.append('        <inertia>')
    L.append(f'          <ixx>{I[0,0]:.8f}</ixx> <ixy>{I[0,1]:.8f}</ixy> <ixz>{I[0,2]:.8f}</ixz>')
    L.append(f'          <iyy>{I[1,1]:.8f}</iyy> <iyz>{I[1,2]:.8f}</iyz> <izz>{I[2,2]:.8f}</izz>')
    L.append('        </inertia>')
    L.append('      </inertial>')
    L.append('      <collision name="base_collision">')
    L.append('        <geometry><mesh><uri>model://%s/meshes/base_link_collision.stl</uri></mesh></geometry>' % key)
    L.append('      </collision>')
    L.append('      <visual name="base_visual">')
    L.append('        <geometry><mesh><uri>model://%s/meshes/base_link.stl</uri></mesh></geometry>' % key)
    L.append('      </visual>')
    L.append('    </link>')
    L.append('')

    for i, rot in enumerate(rl):
        cx, cy, cz = rot["center"]
        cw = (rot["dir"] < 0)
        L.append(f'    <link name="rotor_{i}">')
        L.append(f'      <pose>{cx:.6f} {cy:.6f} {cz:.6f} 0 0 {np.radians(rot["base_ang"]):.6f}</pose>')
        L.append('      <inertial>')
        L.append(f'        <mass>{m_rot:.6f}</mass>')
        L.append('        <inertia>')
        L.append(f'          <ixx>{I_rot[0,0]:.10f}</ixx> <ixy>0</ixy> <ixz>0</ixz>')
        L.append(f'          <iyy>{I_rot[1,1]:.10f}</iyy> <iyz>0</iyz> <izz>{I_rot[2,2]:.10f}</izz>')
        L.append('        </inertia>')
        L.append('      </inertial>')
        L.append('      <collision name="rotor_collision">')
        L.append('        <geometry><mesh><uri>model://%s/meshes/rotor_collision.stl</uri></mesh></geometry>' % key)
        L.append('      </collision>')
        L.append('      <visual name="rotor_visual">')
        L.append('        <geometry><mesh><uri>model://%s/meshes/rotor.stl</uri></mesh></geometry>' % key)
        L.append('      </visual>')
        L.append('    </link>')
        L.append(f'    <joint name="rotor_{i}_joint" type="revolute">')
        L.append('      <parent>base_link</parent>')
        L.append(f'      <child>rotor_{i}</child>')
        L.append('      <axis><xyz>0 0 1</xyz>'
                 '<limit><lower>-1e16</lower><upper>1e16</upper></limit></axis>')
        L.append('    </joint>')
        L.append(f'    <plugin filename="gz-sim-multicopter-motor-model-system"'
                 f' name="gz::sim::systems::MulticopterMotorModel">')
        L.append('      <jointName>rotor_%d_joint</jointName>' % i)
        L.append('      <linkName>rotor_%d</linkName>' % i)
        L.append(f'      <turningDirection>{"cw" if cw else "ccw"}</turningDirection>')
        L.append(f'      <timeConstantUp>{MC["time_constant_up"]}</timeConstantUp>')
        L.append(f'      <timeConstantDown>{MC["time_constant_down"]}</timeConstantDown>')
        L.append(f'      <maxRotVelocity>{MC["max_rot_velocity"]:.2f}</maxRotVelocity>')
        L.append(f'      <motorConstant>{MC["motor_constant"]:.6e}</motorConstant>')
        L.append(f'      <momentConstant>{MC["moment_constant"]:.4f}</momentConstant>')
        L.append(f'      <rotorDragCoefficient>{MC["rotor_drag_coefficient"]:.6e}</rotorDragCoefficient>')
        L.append(f'      <rollingMomentCoefficient>{MC["rolling_moment_coefficient"]:.1e}</rollingMomentCoefficient>')
        L.append(f'      <rotorVelocitySlowdownSim>10</rotorVelocitySlowdownSim>')
        L.append(f'      <motorNumber>{i}</motorNumber>')
        L.append('      <commandSubTopic>command/motor_speed</commandSubTopic>')
        L.append('      <motorType>velocity</motorType>')
        L.append('    </plugin>')
        L.append('')

    L.append('  </model>')
    L.append('</sdf>')

    with open(os.path.join(d, "model.sdf"), "w") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(d, "model.config"), "w") as f:
        f.write(f'<?xml version="1.0"?>\n<model>\n  <name>{key}</name>\n'
                f'  <version>1.0</version>\n  <sdf version="1.9">model.sdf</sdf>\n'
                f'  <description>{spec.name} — sionna2 파라메트릭 CAD 에서 자동 생성.\n'
                f'  제원 출처: docs/drone_specs_2026.json. 관성텐서는 메쉬 기반 추정치.</description>\n'
                f'</model>\n')

    if verbose:
        print(f"[{key}] {spec.name}")
        print(f"   질량 {MP['mass']*1000:.0f} g (공식 TOW)  CoM ({com[0]*1000:+.1f}, {com[1]*1000:+.1f}, {com[2]*1000:+.1f}) mm")
        print(f"   관성 Ixx={I[0,0]:.5f}  Iyy={I[1,1]:.5f}  Izz={I[2,2]:.5f} kg*m^2"
              f"   (검산 Izz ~ Ixx+Iyy: {I[0,0]+I[1,1]:.5f})")
        print(f"   k_T={MC['motor_constant']:.3e} N*s^2/rad^2   k_M={MC['moment_constant']:.4f} m"
              f"   T/W(max)={MC['thrust_to_weight_max']:.2f}")
        print(f"   질량 배분: " + "  ".join(f"{g}={v*1000:.0f}g" for g, v in
                                         sorted(MP["per_group"].items(), key=lambda x: -x[1])[:5]))
        print(f"   → {os.path.relpath(d, ROOT)}/model.sdf")
    return dict(dir=d, mass=MP, motor=MC)


def main():
    from drones import DRONES
    keys = sys.argv[1:] or list(DRONES)
    print("=" * 88)
    print("Gazebo / PX4 SITL 모델 내보내기")
    print("  질량 분포·관성텐서는 **메쉬에서 계산**한다 (DJI 는 공개하지 않는다).")
    print("  총질량만 공식 TOW 에 맞추고, 분포는 부위별 밀도가 정한다.")
    print("=" * 88)
    for k in keys:
        if k not in DRONES:
            print(f"  (모르는 키: {k})"); continue
        export(DRONES[k])
        print()


if __name__ == "__main__":
    main()
