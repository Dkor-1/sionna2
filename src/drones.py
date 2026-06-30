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
from geom import Mesh, box, cylinder, uv_sphere, blade, rotate, translate


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
        accent_rgb=(0.95, 0.45, 0.05), body_frac=0.46),
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
        accent_rgb=None, body_frac=0.42),
    # 3) 엔터프라이즈 측량기 (RTK 탑재)
    "matrice4e": DroneSpec(
        key="matrice4e", name="DJI Matrice 4E",
        diagonal_mm=438.8, weight_g=1219,
        body_l_mm=307, body_w_mm=388, body_h_mm=150,
        prop_dia_mm=274, prop_blades=2, num_rotors=4,
        max_speed_ms=21, rtk=True, release="released", confidence="high",
        note="검증으로 프롭 지름 274mm 확정(292→274). 온보드 RTK(정밀 측위 안테나).",
        body_rgb=_OFFWHT, arm_style="body", gear="feet", gimbal="front",
        accent_rgb=None, body_frac=0.42),
    # 4) 대형 산업용 옥토콥터 (8암) — 단종, 카본 프레임
    "s1000plus": DroneSpec(
        key="s1000plus", name="DJI S1000+",
        diagonal_mm=1045, weight_g=4400,
        body_l_mm=1045, body_w_mm=1045, body_h_mm=462,
        prop_dia_mm=381, prop_blades=2, num_rotors=8,
        max_speed_ms=None, rtk=False, release="discontinued", confidence="high",
        note="옥토콥터: 8암·암당 로터 1개(비동축). 카본 프레임, 접이식+격납형 착륙장치, 벨리 짐벌.",
        body_rgb=_BLACK, arm_style="carbon", gear="tall", gimbal="belly",
        accent_rgb=(0.85, 0.10, 0.10), body_frac=0.30),
    # 5) 고정암 쿼드 (클래식, 흰색 셸)
    "phantom4": DroneSpec(
        key="phantom4", name="DJI Phantom 4",
        diagonal_mm=350, weight_g=1380,
        body_l_mm=350, body_w_mm=350, body_h_mm=198,
        prop_dia_mm=239, prop_blades=2, num_rotors=4,
        max_speed_ms=20, rtk=False, release="released", confidence="high",
        note="고정암(접이 불가) 일체형 흰색 셸 + 일체형 착륙다리. 클래식 팬텀 형상.",
        body_rgb=_WHITE, arm_style="body", fixed_arm=True, gear="legs", gimbal="front",
        accent_rgb=None, body_frac=0.52),
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
    """모터(=암) 각도[deg] 목록. 전방(+x)이 비도록 배치."""
    n = spec.num_rotors
    if n == 4:                          # 쿼드 X자: 45,135,225,315 (전방 비움)
        return [45, 135, 225, 315]
    # 옥토 등: 전방(0)·후방(180)이 비도록 22.5 오프셋
    return [(360.0 / n) * k + (360.0 / n) / 2 for k in range(n)]


def build_drone(spec: DroneSpec) -> Mesh:
    """제원에 맞춘 멀티로터 메쉬(부위 그룹 포함)를 만든다. 전방 = +x."""
    m = Mesh()
    diag = spec.diagonal_mm / 1000.0
    r = diag / 2.0                                   # 모터 반경(중심→모터)
    prop_r = spec.prop_dia_mm / 1000.0 / 2.0
    bh = spec.body_h_mm / 1000.0

    # ---- 동체(중앙 허브) : 살짝 납작한 박스 + 전방으로 좁아지는 느낌 ---------- #
    hub = spec.body_frac * diag                      # 동체 평면 크기 기준
    body_l = hub * 1.15                              # 전후로 약간 길게
    body_w = hub * 0.85
    body_z = 0.35 * bh                               # 동체 두께(모터면 위로 약간)
    m.merge(box(body_l, body_w, body_z, center=(0, 0, 0), group="body"))
    # 상단 캐노피/배터리 험프
    m.merge(box(body_l * 0.6, body_w * 0.7, body_z * 0.9,
                center=(-0.04 * body_l, 0, body_z * 0.8), group="canopy"))
    # 전방 코(살짝 돌출) — 방향성 강조
    m.merge(box(body_l * 0.25, body_w * 0.5, body_z * 0.7,
                center=(body_l * 0.5, 0, 0), group="body"))

    # ---- 암 + 모터 + 프로펠러 ------------------------------------------------ #
    hub_r = max(body_l, body_w) * 0.5 * 0.9          # 허브 가장자리 반경
    arm_w = (0.10 if spec.fixed_arm else 0.05) * diag
    arm_t = (0.08 if spec.fixed_arm else 0.045) * diag
    motor_r = 0.05 * diag
    motor_h = 0.045 * diag
    for ang in _motor_angles(spec):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        mx, my = r * ca, r * sa                       # 모터 위치
        # 암: 허브 가장자리 ~ 모터. +x로 만든 박스를 반경 위치로 옮기고 각도 회전.
        L = r - hub_r
        rc = (hub_r + r) / 2.0
        arm_grp = "arm" if spec.arm_style == "carbon" else "body"
        M = rotate("z", ang) @ translate(rc, 0, 0)
        m.merge(box(L, arm_w, arm_t, center=(0, 0, 0)).transformed(M), group=arm_grp)
        # 전방 암 식별색(있으면): 암 끝에 작은 컬러 캡
        if spec.accent_rgb is not None and ca > 0.1:
            Mc = rotate("z", ang) @ translate(r - L * 0.18, 0, 0)
            m.merge(box(L * 0.30, arm_w * 1.05, arm_t * 1.05,
                        center=(0, 0, 0)).transformed(Mc), group="accent")
        # 모터(세로 원기둥)
        m.merge(cylinder(motor_r, motor_h, axis="z",
                         center=(mx, my, motor_h / 2 + arm_t / 2), group="motor"))
        # 프로펠러(모터 위)
        prop_z = motor_h + arm_t / 2 + 0.006
        for b in range(spec.prop_blades):
            bang = ang + (360.0 / spec.prop_blades) * b + 12.0
            Mb = translate(mx, my, prop_z) @ rotate("z", bang)
            m.merge(blade(prop_r, prop_r * 0.22, 0.004).transformed(Mb), group="prop")

    # ---- 착륙장치 ------------------------------------------------------------ #
    _add_gear(m, spec, body_l, body_w, body_z, diag)

    # ---- 짐벌 카메라 --------------------------------------------------------- #
    _add_camera(m, spec, body_l, body_z)
    return m


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
    if spec.gimbal == "front":                       # 전방 하단 짐벌
        cx, cz = body_l * 0.42, -body_z * 0.55
        m.merge(box(0.10 * body_l, 0.12 * body_l, 0.10 * body_l,
                    center=(cx, 0, cz), group="camera"))
        m.merge(uv_sphere(0.045 * body_l, center=(cx + 0.05 * body_l, 0, cz),
                          seg=12, rings=7, group="camera"))
    elif spec.gimbal == "belly":                     # 중앙 하단 벨리 짐벌(브래킷)
        cz = -body_z * 1.2
        m.merge(box(0.18 * body_l, 0.18 * body_l, 0.16 * body_l,
                    center=(0, 0, cz), group="camera"))
        m.merge(uv_sphere(0.07 * body_l, center=(0, 0, cz - 0.08 * body_l),
                          seg=12, rings=7, group="camera"))


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
