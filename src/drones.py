# -*- coding: utf-8 -*-
"""
drones.py — DJI 드론 5종의 '실측 제원' + 파라메트릭 3D 모델 생성기
==================================================================

목표
  사진처럼 보이는 '대충 만든 드론'이 아니라, **실제 제원(대각거리/무게/프로펠러
  지름/로터 수 …)을 그대로 반영**한, 치수가 정확한 멀티로터 3D 모델을 만든다.

제원 출처
  src/.. 의 백그라운드 리서치(웹 검색 + 독립 검증, docs/drone_research.json)에서
  가져왔고, 검증 단계의 수정사항을 반영했다. 각 제원에는 confidence(신뢰도)와
  note(주의)를 함께 둔다. 대각거리 등 DJI 가 공개하지 않는 값은 외형에서 '추정'한
  값임을 분명히 표시한다.

만드는 부위(그룹)
  body(동체) / canopy(상단 배터리·캐노피) / arm(암) / motor(모터) /
  prop(프로펠러) / gear(착륙장치) / camera(짐벌 카메라) / accent(전방 식별색)

좌표(드론 로컬): z-up, 중심 (0,0,0), **전방 = +x**, 모터면 z=0.
  → 동체는 z 위/아래로, 프로펠러는 모터 위(z>0), 착륙장치는 아래(z<0).
단위: 전부 m. 제원 mm 는 /1000.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from geom import Mesh, box, cylinder, uv_sphere, blade, prop_blade, hull, rotate, translate


# --------------------------------------------------------------------------- #
#  드론 제원 + 외형 스타일
# --------------------------------------------------------------------------- #
@dataclass
class DroneSpec:
    key: str
    name: str
    # --- 실측 제원 (리서치+검증) ---
    diagonal_mm: float          # 모터-모터 대각거리(휠베이스)
    weight_g: float             # 이륙중량
    body_l_mm: float            # 동체(언폴드) 길이/폭/높이 — 외형 비율 참고용
    body_w_mm: float
    body_h_mm: float
    prop_dia_mm: float          # 프로펠러 지름
    prop_blades: int            # 날개 수
    num_rotors: int             # 로터 수 (=암 수, 비동축)
    coaxial: bool = False       # 동축(2개/암) 여부
    max_speed_ms: float | None = None
    rtk: bool = False
    release: str = "released"   # released / rumored_unreleased / discontinued
    confidence: str = "high"
    note: str = ""
    # --- 외형 스타일(렌더용) ---
    body_rgb: tuple = (0.5, 0.5, 0.5)
    arm_style: str = "carbon"   # 'carbon'(어두운 암) / 'body'(동체색 암; 고정형)
    fixed_arm: bool = False     # True 면 굵은 고정암(팬텀류)
    gear: str = "none"          # 'none' / 'legs'(팬텀) / 'tall'(S1000) / 'feet'
    gimbal: str = "front"       # 'front'(전방하단) / 'belly'(중앙하단)
    accent_rgb: tuple | None = None   # 전방 암/프롭팁 식별색 (없으면 None)
    body_frac: float = 0.42     # 동체 크기/대각 비율(외형 튜닝)
    # --- 드론별 개성(실루엣) — 스펙·대각·좌우대칭(비행안정) 유지하며 외형만 ---
    rotor_deg: tuple | None = None   # 모터 각도[deg] 목록. None=기본 X(쿼드)/옥토.
                                     #   접이형은 전방스윕(좌우대칭+마주보는 쌍 180°→대각 보존)
    body_lw: tuple = (1.15, 0.85)    # 동체 (길이,폭)/hub 비 — 접이 슬림기는 길쭉·좁게
    gimbal_style: str = "single"     # single / triple(마빅 3카메라) / sensor(매트리스+RTK)
                                     #   / recessed(팬텀 함몰) / belly(S1000 벨리)


# 화면표시 색(RGB)
_GRAY_D = (0.28, 0.30, 0.33)
_SILVER = (0.72, 0.73, 0.76)
_OFFWHT = (0.86, 0.86, 0.83)
_BLACK = (0.12, 0.12, 0.13)
_WHITE = (0.93, 0.93, 0.95)

DRONES: dict[str, DroneSpec] = {
    # 1) 초소형 (sub-250g) — 가장 작고 탐지하기 어려운 표적
    "mini5pro": DroneSpec(
        key="mini5pro", name="DJI Mini 5 Pro",
        diagonal_mm=250, weight_g=249.9,
        body_l_mm=255, body_w_mm=181, body_h_mm=91,
        prop_dia_mm=152, prop_blades=2, num_rotors=4,
        max_speed_ms=19, rtk=False, release="released", confidence="high",
        note="대각거리(250mm)는 DJI 비공개 → 언폴드 외형서 추정(±20mm). 무게/프롭/로터수 공식.",
        body_rgb=_GRAY_D, arm_style="body", gear="none", gimbal="front",
        accent_rgb=(0.95, 0.45, 0.05), body_frac=0.46,
        rotor_deg=(40, 140, 220, 320), body_lw=(1.42, 0.66), gimbal_style="single"),
    # 2) 대형 소비자 플래그십 (출시작)
    "mavic4pro": DroneSpec(
        key="mavic4pro", name="DJI Mavic 4 Pro",
        diagonal_mm=400, weight_g=1063,
        body_l_mm=329, body_w_mm=391, body_h_mm=135,
        prop_dia_mm=267, prop_blades=2, num_rotors=4,
        max_speed_ms=25, rtk=False, release="released", confidence="high",
        note="대형 소비자 플래그십(2025). 전방 3카메라 짐벌(360° 무한회전)이 특징. "
             "무게/외형 공식, 대각거리·프롭지름은 DJI 비공개라 외형서 추정.",
        body_rgb=_SILVER, arm_style="body", gear="none", gimbal="front",
        accent_rgb=None, body_frac=0.42,
        rotor_deg=(32, 148, 212, 328), body_lw=(1.52, 0.62), gimbal_style="triple"),
    # 3) 엔터프라이즈 측량기 (RTK 탑재)
    "matrice4e": DroneSpec(
        key="matrice4e", name="DJI Matrice 4E",
        diagonal_mm=438.8, weight_g=1219,
        body_l_mm=307, body_w_mm=388, body_h_mm=150,
        prop_dia_mm=274, prop_blades=2, num_rotors=4,
        max_speed_ms=21, rtk=True, release="released", confidence="high",
        note="검증으로 프롭 지름 274mm 확정(292→274). 온보드 RTK(정밀 측위 안테나).",
        body_rgb=_OFFWHT, arm_style="body", gear="feet", gimbal="front",
        accent_rgb=None, body_frac=0.42,
        rotor_deg=(45, 135, 225, 315), body_lw=(1.08, 0.98), gimbal_style="sensor"),
    # 4) 대형 산업용 옥토콥터 (8암) — 단종, 카본 프레임
    "s1000plus": DroneSpec(
        key="s1000plus", name="DJI S1000+",
        diagonal_mm=1045, weight_g=4400,
        body_l_mm=1045, body_w_mm=1045, body_h_mm=462,
        prop_dia_mm=381, prop_blades=2, num_rotors=8,
        max_speed_ms=None, rtk=False, release="discontinued", confidence="high",
        note="옥토콥터: 8암·암당 로터 1개(비동축). 카본 프레임, 접이식+격납형 착륙장치, 벨리 짐벌.",
        body_rgb=_BLACK, arm_style="carbon", gear="tall", gimbal="belly",
        accent_rgb=(0.85, 0.10, 0.10), body_frac=0.30,
        body_lw=(1.0, 1.0), gimbal_style="belly"),
    # 5) 고정암 쿼드 (클래식, 흰색 셸)
    "phantom4": DroneSpec(
        key="phantom4", name="DJI Phantom 4",
        diagonal_mm=350, weight_g=1380,
        body_l_mm=350, body_w_mm=350, body_h_mm=198,
        prop_dia_mm=239, prop_blades=2, num_rotors=4,
        max_speed_ms=20, rtk=False, release="released", confidence="high",
        note="고정암(접이 불가) 일체형 흰색 셸 + 일체형 착륙다리. 클래식 팬텀 형상.",
        body_rgb=_WHITE, arm_style="body", fixed_arm=True, gear="legs", gimbal="front",
        accent_rgb=None, body_frac=0.52,
        rotor_deg=(45, 135, 225, 315), body_lw=(1.06, 1.0), gimbal_style="recessed"),
}

# 부위(그룹) → (재질키, 한글설명). 색은 build_drone 가 스펙에서 직접 지정.
DRONE_GROUP_MAT = {
    "body":   ("plastic", "동체 셸"),
    "canopy": ("plastic", "상단 캐노피/배터리"),
    "arm":    ("carbon",  "암"),
    "motor":  ("metal",   "모터"),
    "prop":   ("plastic", "프로펠러"),
    "gear":   ("plastic", "착륙장치"),
    "camera": ("plastic", "짐벌 카메라"),
    "accent": ("plastic", "전방 식별색"),
}


# --------------------------------------------------------------------------- #
#  파라메트릭 멀티로터 생성기
# --------------------------------------------------------------------------- #
def _motor_angles(spec: DroneSpec) -> list[float]:
    """모터(=암) 각도[deg] 목록. spec.rotor_deg 가 있으면 그대로(드론별 실제 배치).
    없으면 기본 — 쿼드 X자(45/135/225/315), 옥토는 22.5° 오프셋.
    ※ rotor_deg 는 좌우대칭이고 마주보는 쌍이 180° → 대각거리 스펙 보존 + 무게중심 중앙(비행안정)."""
    if spec.rotor_deg is not None:
        return list(spec.rotor_deg)
    n = spec.num_rotors
    if n == 4:                          # 쿼드 X자: 45,135,225,315 (전방 비움)
        return [45, 135, 225, 315]
    # 옥토 등: 전방(0)·후방(180)이 비도록 22.5 오프셋
    return [(360.0 / n) * k + (360.0 / n) / 2 for k in range(n)]


def _drone_dims(spec: DroneSpec):
    """공용 치수: (diag, r, prop_r, bh, body_l, body_w, body_z)."""
    diag = spec.diagonal_mm / 1000.0
    r = diag / 2.0                                   # 모터 반경(중심→모터)
    prop_r = spec.prop_dia_mm / 1000.0 / 2.0
    bh = spec.body_h_mm / 1000.0
    hub = spec.body_frac * diag
    lf, wf = spec.body_lw                            # 드론별 동체 길이/폭 비(접이형은 길쭉)
    body_l = hub * lf; body_w = hub * wf; body_z = 0.35 * bh
    return diag, r, prop_r, bh, body_l, body_w, body_z


def build_frame(spec: DroneSpec) -> Mesh:
    """**회전하지 않는 부분**: 동체/캐노피/암/모터/착륙장치/카메라/액센트 (프로펠러 제외).
    드론 로컬 프레임(전방 +x). pose_articulated 에서 몸체 자세를 통째로 적용한다."""
    m = Mesh()
    diag, r, prop_r, bh, body_l, body_w, body_z = _drone_dims(spec)
    # 동체(둥근 hull) + 전방 코(테이퍼) + 캐노피(돔) — 박스 대신 곡면
    m.merge(hull(body_l, body_w, body_z, sides=16, taper_top=0.80,
                 center=(0, 0, 0), group="body"))
    m.merge(hull(body_l * 0.34, body_w * 0.6, body_z * 0.72, sides=12, taper_top=0.45,
                 center=(body_l * 0.44, 0, -body_z * 0.05), group="body"))     # 코(돌출·테이퍼)
    m.merge(hull(body_l * 0.62, body_w * 0.72, body_z * 1.1, sides=16, taper_top=0.32,
                 center=(-0.04 * body_l, 0, body_z * 0.7), group="canopy"))    # 캐노피 돔
    # 암(둥근 카본 튜브) + 모터(약간 벨형) — 프로펠러는 분리
    hub_r = max(body_l, body_w) * 0.5 * 0.9
    arm_rad = (0.050 if spec.fixed_arm else 0.028) * diag
    arm_t = (0.08 if spec.fixed_arm else 0.045) * diag                          # 모터 안착 높이 기준(유지)
    motor_r = 0.05 * diag; motor_h = 0.045 * diag
    for ang in _motor_angles(spec):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        mx, my = r * ca, r * sa
        L = r - hub_r; rc = (hub_r + r) / 2.0
        arm_grp = "arm" if spec.arm_style == "carbon" else "body"
        M = rotate("z", ang) @ translate(rc, 0, 0)
        m.merge(cylinder(arm_rad, L, axis="x", seg=12, center=(0, 0, 0)).transformed(M),
                group=arm_grp)
        if spec.accent_rgb is not None and ca > 0.1:                            # 전방 암 식별 컬러밴드
            Mc = rotate("z", ang) @ translate(r - L * 0.18, 0, 0)
            m.merge(cylinder(arm_rad * 1.25, L * 0.28, axis="x", seg=12,
                             center=(0, 0, 0)).transformed(Mc), group="accent")
        m.merge(cylinder(motor_r, motor_h, axis="z", seg=16, r_top=motor_r * 0.82,
                         center=(mx, my, motor_h / 2 + arm_t / 2), group="motor"))
    _add_gear(m, spec, body_l, body_w, body_z, diag)
    _add_camera(m, spec, body_l, body_z)
    if spec.rtk:                                     # 엔터프라이즈 RTK 안테나(매트리스)
        _add_antenna(m, spec, body_l, body_w, body_z)
    return m


def build_propeller(spec: DroneSpec) -> Mesh:
    """**프로펠러 1개**(prop_blades 장)를 허브 원점 기준으로 생성(스핀 적용 전, z축 회전).
    pose_articulated/마이크로도플러에서 이 메쉬를 z회전(스핀)시켜 각 로터에 배치한다."""
    _, _, prop_r, *_ = _drone_dims(spec)
    m = Mesh()
    for b in range(spec.prop_blades):
        bang = (360.0 / spec.prop_blades) * b
        m.merge(prop_blade(prop_r).transformed(rotate("z", bang)), group="prop")
    return m


def rotor_layout(spec: DroneSpec) -> list[dict]:
    """로터별 배치: {center:(x,y,z), base_ang:deg(장착 오프셋), dir:+1/-1(CCW/CW)}.
    dir 은 인접 로터가 반대로 도는 멀티로터 관례(대각쌍 동일). build_drone 과 동일 좌표."""
    diag, r, prop_r, bh, body_l, body_w, body_z = _drone_dims(spec)
    arm_t = (0.08 if spec.fixed_arm else 0.045) * diag
    motor_h = 0.045 * diag
    prop_z = motor_h + arm_t / 2 + 0.006
    out = []
    for k, ang in enumerate(_motor_angles(spec)):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        out.append(dict(center=(r * ca, r * sa, prop_z),
                        base_ang=ang + 12.0, dir=(1 if k % 2 == 0 else -1)))
    return out


def build_drone(spec: DroneSpec) -> Mesh:
    """정적 멀티로터 메쉬(프레임 + 프로펠러 초기위상). **기존과 동일 출력**(report1/2 RCS 호환).
    = build_frame + 각 로터에 build_propeller 를 초기위상(스핀 0)으로 배치."""
    m = build_frame(spec)
    prop = build_propeller(spec)
    for rot in rotor_layout(spec):
        cx, cy, cz = rot["center"]
        M = translate(cx, cy, cz) @ rotate("z", rot["base_ang"])
        m.merge(prop.transformed(M), group="prop")
    return m


def pose_articulated(spec: DroneSpec, body_rpy=(0., 0., 0.), body_pos=(0., 0., 0.),
                     rotor_phase_deg=None) -> Mesh:
    """**분절 스냅샷 메쉬**: 몸체 자세(roll,pitch,yaw [deg]) + 위치, 로터별 스핀위상[deg]로
    월드 프레임 메쉬를 만든다. **몸체 회전과 블레이드 회전이 분리되어** 적용된다:
      - 프레임(비회전부)에는 몸체변환 B 만,
      - 각 프로펠러에는 B ∘ (로터위치) ∘ (장착오프셋+스핀위상) 을 적용.
    rotor_phase_deg=None 이면 모두 0. RPY 상태에서도 로터마다 다른 위상을 줄 수 있다."""
    roll, pitch, yaw = body_rpy
    B = (translate(*[float(v) for v in body_pos])
         @ rotate("z", yaw) @ rotate("y", pitch) @ rotate("x", roll))
    out = build_frame(spec).transformed(B)               # 그룹 보존됨
    prop = build_propeller(spec)
    rl = rotor_layout(spec)
    if rotor_phase_deg is None:
        rotor_phase_deg = [0.0] * len(rl)
    for rot, ph in zip(rl, rotor_phase_deg):
        cx, cy, cz = rot["center"]
        M = B @ translate(cx, cy, cz) @ rotate("z", rot["base_ang"] + ph)
        out.merge(prop.transformed(M), group="prop")
    return out


def _add_gear(m, spec, body_l, body_w, body_z, diag):
    if spec.gear == "none":
        return
    if spec.gear == "feet":                          # 작은 발 4개(매트리스/소비자기)
        fz = -0.06 * diag
        for sx in (0.32, -0.32):
            for sy in (0.32, -0.32):
                m.merge(cylinder(0.012 * diag, abs(fz), axis="z",
                                 center=(sx * body_l, sy * body_w, fz / 2),
                                 group="gear"))
        return
    if spec.gear == "legs":                          # 팬텀: 아치형 다리 2개 + 스키드
        leg_h = 0.16 * diag
        for sy in (1, -1):
            y = sy * body_w * 0.45
            # 비스듬한 다리(박스) + 바닥 스키드
            m.merge(box(0.05 * diag, 0.05 * diag, leg_h,
                        center=(0, y * 1.1, -leg_h / 2 - body_z / 2), group="gear"))
            m.merge(box(body_l * 0.7, 0.05 * diag, 0.04 * diag,
                        center=(0, y * 1.15, -leg_h - body_z / 2), group="gear"))
        return
    if spec.gear == "tall":                          # S1000: 긴 격납형 다리 + 스키드
        leg_h = 0.22 * diag
        for sy in (1, -1):
            y = sy * body_w * 0.55
            m.merge(box(0.045 * diag, 0.045 * diag, leg_h,
                        center=(body_l * 0.2, y, -leg_h / 2 - body_z / 2), group="gear"))
            m.merge(box(0.045 * diag, 0.045 * diag, leg_h,
                        center=(-body_l * 0.2, y, -leg_h / 2 - body_z / 2), group="gear"))
            m.merge(box(body_l * 1.2, 0.06 * diag, 0.05 * diag,
                        center=(0, y, -leg_h - body_z / 2), group="gear"))


def _add_camera(m, spec, body_l, body_z):
    """드론별 개성 짐벌. gimbal=='belly' 면 벨리, 아니면 gimbal_style 로 분기."""
    if spec.gimbal == "belly" or spec.gimbal_style == "belly":   # S1000 중앙 하단 벨리
        cz = -body_z * 1.2
        m.merge(box(0.18 * body_l, 0.18 * body_l, 0.16 * body_l,
                    center=(0, 0, cz), group="camera"))
        m.merge(uv_sphere(0.07 * body_l, center=(0, 0, cz - 0.08 * body_l),
                          seg=12, rings=7, group="camera"))
        return
    cx, cz = body_l * 0.42, -body_z * 0.55
    st = spec.gimbal_style
    if st == "triple":                               # Mavic 3-카메라(가로로 넓은 블록 + 렌즈 3)
        m.merge(box(0.10 * body_l, 0.30 * body_l, 0.12 * body_l, center=(cx, 0, cz), group="camera"))
        for dy in (-0.085 * body_l, 0.0, 0.085 * body_l):
            m.merge(uv_sphere(0.038 * body_l, center=(cx + 0.05 * body_l, dy, cz),
                              seg=10, rings=6, group="camera"))
    elif st == "sensor":                             # Matrice 짐벌 + 측거센서 클러스터
        m.merge(box(0.12 * body_l, 0.17 * body_l, 0.12 * body_l, center=(cx, 0, cz), group="camera"))
        m.merge(uv_sphere(0.05 * body_l, center=(cx + 0.05 * body_l, 0.035 * body_l, cz),
                          seg=12, rings=7, group="camera"))
        m.merge(box(0.06 * body_l, 0.05 * body_l, 0.05 * body_l,
                    center=(cx + 0.02 * body_l, -0.07 * body_l, cz), group="camera"))   # 레이저 측거
    elif st == "recessed":                           # Phantom 함몰 짐벌(동체에 더 붙음)
        cx2 = body_l * 0.32
        m.merge(box(0.08 * body_l, 0.11 * body_l, 0.08 * body_l, center=(cx2, 0, cz * 0.8), group="camera"))
        m.merge(uv_sphere(0.042 * body_l, center=(cx2 + 0.03 * body_l, 0, cz * 0.8),
                          seg=12, rings=7, group="camera"))
    else:                                            # single (Mini 등 소형 전방 짐벌)
        m.merge(box(0.09 * body_l, 0.11 * body_l, 0.09 * body_l, center=(cx, 0, cz), group="camera"))
        m.merge(uv_sphere(0.045 * body_l, center=(cx + 0.05 * body_l, 0, cz),
                          seg=12, rings=7, group="camera"))


def _add_antenna(m, spec, body_l, body_w, body_z):
    """RTK GNSS 안테나(후방 상단 마스트 + 퍽) — Matrice 등 rtk=True 기체의 식별 특징."""
    mast_h = 0.45 * body_l
    mx = -0.18 * body_l
    z0 = body_z * 1.1
    m.merge(cylinder(0.022 * body_l, mast_h, axis="z", seg=10,
                     center=(mx, 0, z0 + mast_h / 2), group="body"))
    m.merge(cylinder(0.075 * body_l, 0.05 * body_l, axis="z", seg=14, r_top=0.06 * body_l,
                     center=(mx, 0, z0 + mast_h), group="body"))      # 퍽(돔)


def drone_colors(spec: DroneSpec) -> dict:
    """부위 그룹 → 표시색 RGB. (재질키는 DRONE_GROUP_MAT 사용)"""
    body = spec.body_rgb
    return {
        "body":   body,
        "canopy": tuple(0.85 * c for c in body),
        "arm":    (0.10, 0.10, 0.11) if spec.arm_style == "carbon" else body,
        "motor":  (0.20, 0.20, 0.22),
        "prop":   (0.15, 0.15, 0.16),
        "gear":   tuple(0.7 * c for c in body) if spec.fixed_arm else (0.12, 0.12, 0.13),
        "camera": (0.08, 0.08, 0.09),
        "accent": spec.accent_rgb or (0.85, 0.1, 0.1),
    }


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "drones")
    print(f"{'key':12s} {'rotors':>6s} {'diag_mm':>8s} {'prop_mm':>8s} {'tris':>7s}  release")
    for key, spec in DRONES.items():
        m = build_drone(spec)
        d = os.path.abspath(os.path.join(out, key))
        m.write_obj_per_group(d, key)
        b0, b1 = m.bounds()
        span = (b1 - b0)
        print(f"{key:12s} {spec.num_rotors:6d} {spec.diagonal_mm:8.0f} "
              f"{spec.prop_dia_mm:8.0f} {m.n_tris():7d}  {spec.release}"
              f"   span[m]={span[0]:.2f}x{span[1]:.2f}x{span[2]:.2f}")
