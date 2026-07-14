# -*- coding: utf-8 -*-
"""
drone_cad.py — **실물 형상에 맞춘 고충실도 드론 CAD** (trimesh + manifold3d + shapely + scipy)
=================================================================================================
기존 `drones.py` 의 파라메트릭 메쉬는 프리미티브(원기둥·다각기둥)를 **겹쳐 쌓은** 것이라
  · 동체가 각진 다각기둥이었고(실물은 매끈한 눈물방울),
  · 짐벌·카메라가 상자였고(Mavic 4 는 **구형 Infinity 짐벌**),
  · 착륙장치·RTK 안테나 같은 실루엣 특징이 없었고,
  · **불리언이 없어** 겹친 파트의 **내부 면이 그대로 남아** PO/SBR 이 헛세는 원인이 됐다.

이 모듈은 `cadkit.py`(trimesh/manifold3d/shapely/scipy)로 **실물 사진·제원에 맞춰** 다시 만든다.

■ 기종별 실루엣 (공식 자료·제품 사진 기준)
  mini5pro   초슬림 접이식. 낮고 길쭉한 동체. 앞팔은 수평으로 펴지고 뒷팔은 아래로. 착륙장치 없음.
             전방 하단에 작은 2축 짐벌(1인치 센서).
  mavic4pro  **구형 "Infinity 짐벌"** — 매달린 게 아니라 **기수와 일직선인 볼 마운트**, 360° 회전.
             볼 전면에 **3개 렌즈**(100MP 광각 + 중망원 + 망원). 넓은 눈물방울 동체 + 상단 배터리 캐노피.
  matrice4e  Mavic 3 계열 동체 + **상단 RTK 돔**. 전방 3축 짐벌(측량 페이로드). 작은 발 4개.
  s1000plus  옥토. **원형 카본 센터프레임(상·하판)** + 8암. **긴 접이식 착륙다리**. 벨리 짐벌.
  phantom4   고정암 일체형 흰 셸. **일체형 스키드 착륙다리**. 코 아래 매달린 짐벌(방진판).
             기수에 비전센서.

■ 왜 이게 RCS 에 중요한가
  RCS 는 **외형(투영면적)과 재질 분포**가 결정한다. 실루엣이 틀리면 σ 가 틀린다.
  그리고 **불리언 합집합**으로 겹친 파트의 내부 면을 녹여 없애면, SBR 이 가림으로 걸러내기 **전에**
  애초에 그런 면이 존재하지 않게 된다 — 더 정확하고 더 빠르다.

■ 공식 외형 정합
  마지막에 `spec.envelope_mm`(DJI 공식 언폴드·프롭제외 L×W×H)에 프레임 바운딩박스를 맞춘다.
  (drones.frame_fit_scale 과 같은 규약)
"""
from __future__ import annotations

import numpy as np
import trimesh

from cadkit import (Assembly, loft, spline_sections, superellipse, rounded_rect, sweep,
                    revolve, smooth, box, cyl, sphere, capsule, rot_z, mv)


# --------------------------------------------------------------------------- #
#  공통 부품
# --------------------------------------------------------------------------- #
def _motor_bell(r, h, seg=36):
    """모터 벨 — 아래가 잘록하고 위가 부푼 실제 아웃러너 형상(회전체)."""
    pr = np.array([
        [0.00, 0.00], [r * 0.55, 0.00], [r * 0.72, h * 0.10],
        [r * 0.94, h * 0.22], [r * 1.00, h * 0.55], [r * 0.96, h * 0.82],
        [r * 0.80, h * 0.95], [r * 0.42, h * 1.00], [0.00, h * 1.00],
    ])
    return revolve(pr, seg=seg)


def _prop_hub(r, h, seg=28):
    pr = np.array([[0, 0], [r, 0], [r * 0.92, h * 0.6], [r * 0.55, h], [0, h]])
    return revolve(pr, seg=seg)


def _airfoil(chord, thick_ratio=0.10, pts=40):
    """NACA-4 계열 대칭 익형 단면(y=시위, z=두께) — 실제 프로펠러 단면."""
    t = thick_ratio
    x = (1 - np.cos(np.linspace(0, np.pi, pts // 2))) / 2          # 코사인 클러스터링(앞전 촘촘)
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2
                  + 0.2843 * x**3 - 0.1015 * x**4)
    up = np.c_[x, yt]
    lo = np.c_[x[::-1], -yt[::-1]]
    P = np.vstack([up, lo[1:-1]]) * chord
    P[:, 0] -= chord * 0.30                                         # 시위 30% 를 원점(피치축)으로
    from shapely.geometry import Polygon
    return Polygon(P)


def _blade(R, root_frac=0.14, chord_max=0.20, pitch_deg=20.0, twist_deg=13.0,
           sweep_frac=0.10, n_sec=22, n_pts=36):
    """**진짜 익형 프로펠러 블레이드 1장** — 로프트(테이퍼 + 워시아웃 트위스트 + 시미터 스윕).
    +x = 스팬. 익형 단면을 스팬을 따라 회전(피치)·축소(테이퍼)·후퇴(스윕)시키며 잇는다."""
    from shapely import affinity as aff
    r0 = root_frac * R
    xs = np.linspace(r0, R, n_sec)
    tt = (xs - r0) / (R - r0)

    # 시위 분포: 루트 좁 → 30% 최대 → 팁 둥글게 (실제 프로펠러)
    c = np.interp(tt, [0, .15, .35, .80, 1.0],
                  np.array([.10, .19, .21, .15, .035]) * chord_max / 0.21 * R)
    th = np.radians(pitch_deg - twist_deg * tt)                     # 워시아웃
    yc = sweep_frac * R * np.sin(np.pi / 2 * tt)                    # 시미터 스윕

    rings = []
    for x, ci, ti, yi in zip(xs, c, th, yc):
        p = _airfoil(max(ci, 1e-4), thick_ratio=0.09 + 0.05 * (1 - tt[0]))
        p = aff.rotate(p, np.degrees(ti), origin=(0, 0), use_radians=False)
        p = aff.translate(p, yi, 0.0)
        rings.append((float(x), p))
    return loft(rings, n_pts=n_pts, cap=True)


# --------------------------------------------------------------------------- #
#  기종별 동체
# --------------------------------------------------------------------------- #
def _body_folding(L, W, H, nose_drop=0.18, tail_w=0.95, n_pow=2.9):
    """접이식 소비자기(미니/마빅/매트리스) 공용 눈물방울 동체.
    코는 좁고 살짝 처지고, 허리에서 가장 넓고, 꼬리는 완만히 좁아진다."""
    xs = np.array([-0.50, -0.30, -0.05, 0.18, 0.38, 0.50]) * L
    hw = np.array([0.30, 0.46, 0.50, 0.44, 0.28, 0.10]) * W * tail_w
    hh = np.array([0.30, 0.46, 0.50, 0.46, 0.34, 0.16]) * H
    zo = np.array([0.02, 0.01, 0.00, -0.04, -0.10, -nose_drop]) * H
    return smooth(loft(spline_sections(xs, hw, hh, zo, n_pow=n_pow, n_sec=30, n_pts=72),
                       n_pts=72), iters=4)


def _canopy(L, W, H, x0=-0.10, frac=0.55):
    """상단 배터리 캐노피 — 낮고 평평한 돔(실물은 배터리가 등에 얹힌 모양)."""
    xs = np.array([-0.5, -0.2, 0.1, 0.42]) * L * frac
    hw = np.array([0.24, 0.44, 0.42, 0.20]) * W
    hh = np.array([0.10, 0.24, 0.22, 0.08]) * H
    zo = np.zeros(4)
    m = smooth(loft(spline_sections(xs, hw, hh, zo, n_pow=3.2, n_sec=20, n_pts=56), n_pts=56),
               iters=3)
    return mv(m, x=x0 * L, z=0.30 * H)


def _arm_folding(r_motor, ang_deg, arm_r0, arm_r1, hub_r, z0=0.0, z1=0.0, bend=0.10):
    """접이식 암 — 허브에서 모터까지 **완만히 휘는 테이퍼 튜브**(단면은 둥근 직사각)."""
    from shapely import affinity as aff
    a = np.radians(ang_deg)
    p0 = np.array([hub_r * np.cos(a), hub_r * np.sin(a), z0])
    p1 = np.array([r_motor * np.cos(a), r_motor * np.sin(a), z1])
    mid = 0.5 * (p0 + p1) + np.array([0, 0, bend * np.linalg.norm(p1 - p0)])
    t = np.linspace(0, 1, 14)[:, None]
    path = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t ** 2 * p1     # 2차 베지에

    def prof(s):
        w = arm_r0 + (arm_r1 - arm_r0) * s
        return rounded_rect(w * 2.0, w * 1.35, w * 0.55, pts=32)
    return sweep(path, prof, n_pts=28)


# --------------------------------------------------------------------------- #
#  기종별 짐벌/카메라 — **실루엣의 핵심**
# --------------------------------------------------------------------------- #
def _gimbal_infinity(R, cx, cz):
    """Mavic 4 Pro — **구형 Infinity 짐벌**. 볼 + 전면 3렌즈. 매달리지 않고 기수와 일직선."""
    A = []
    ball = sphere(R, center=(cx, 0, cz), subdiv=3)
    A.append(("camera", ball))
    for k, (dy, dz, lr) in enumerate([(0.0, 0.0, 0.46), (-0.52, -0.30, 0.26), (0.52, -0.30, 0.24)]):
        lens = cyl(R * lr, R * 0.42, center=(cx + R * 0.82, dy * R, cz + dz * R), axis="x", seg=28)
        A.append(("camera", lens))
    yoke = cyl(R * 0.30, R * 2.3, center=(cx, 0, cz), axis="y", seg=20)   # 롤 축 요크
    A.append(("camera", yoke))
    return A


def _gimbal_hanging(w, h, d, cx, cz, n_lens=1):
    """매달린 짐벌(Mini/Phantom) — 방진판 + 요크 + 카메라 박스 + 렌즈."""
    A = []
    A.append(("camera", box(w * 1.5, w * 1.5, h * 0.12, center=(cx, 0, cz + h * 0.62))))  # 방진판
    A.append(("camera", cyl(w * 0.16, h * 0.55, center=(cx, 0, cz + h * 0.30), axis="z", seg=16)))
    A.append(("camera", box(d, w, h, center=(cx, 0, cz))))
    for k in range(n_lens):
        off = 0.0 if n_lens == 1 else (k - (n_lens - 1) / 2) * w * 0.55
        A.append(("camera", cyl(h * 0.34, d * 0.55, center=(cx + d * 0.55, off, cz), axis="x", seg=24)))
    return A


def _gimbal_sensor(w, h, d, cx, cz):
    """Matrice 4E — 측량 페이로드(3축 짐벌 + 렌즈 여러 개 + 레이저)."""
    A = []
    A.append(("camera", cyl(w * 0.30, h * 0.9, center=(cx, 0, cz + h * 0.55), axis="z", seg=20)))
    A.append(("camera", box(d, w * 1.25, h, center=(cx, 0, cz))))
    for dy in (-0.34, 0.0, 0.34):
        A.append(("camera", cyl(h * 0.28, d * 0.5, center=(cx + d * 0.52, dy * w, cz), axis="x", seg=22)))
    return A


# --------------------------------------------------------------------------- #
#  착륙장치
# --------------------------------------------------------------------------- #
def _gear_skids(L, W, zbot, leg_h):
    """Phantom — 일체형 스키드(다리 4 + 좌우 스키드 바). 실물은 셸과 한 몸."""
    A = []
    for sx in (0.34, -0.30):
        for sy in (0.30, -0.30):
            A.append(("gear", capsule(leg_h * 0.10, leg_h * 0.80,
                                      center=(sx * L, sy * W, zbot - leg_h * 0.45), axis="z")))
    for sy in (0.30, -0.30):
        A.append(("gear", capsule(leg_h * 0.11, L * 0.62,
                                  center=(0.02 * L, sy * W, zbot - leg_h * 0.86), axis="x")))
    return A


def _gear_tall(R, zbot, leg_h):
    """S1000+ — 긴 접이식 다리 2개(아래로 벌어지며 내려가는 카본 봉 + 발 바)."""
    A = []
    for sy in (1, -1):
        top = np.array([0.0, sy * R * 0.26, zbot])
        bot = np.array([0.0, sy * R * 0.52, zbot - leg_h])
        t = np.linspace(0, 1, 10)[:, None]
        path = (1 - t) * top + t * bot
        A.append(("gear", sweep(path, lambda s: rounded_rect(0.022 * R, 0.022 * R, 0.008 * R),
                                n_pts=16)))
        A.append(("gear", capsule(0.016 * R, R * 0.85,
                                  center=(0.0, sy * R * 0.52, zbot - leg_h), axis="x")))
    return A


def _gear_feet(L, W, zbot, h):
    A = []
    for sx in (0.30, -0.30):
        for sy in (0.30, -0.30):
            A.append(("gear", capsule(h * 0.20, h * 0.6, center=(sx * L, sy * W, zbot - h * 0.4),
                                      axis="z")))
    return A


# --------------------------------------------------------------------------- #
#  프레임 (프로펠러 제외) — 기종별
# --------------------------------------------------------------------------- #
def build_frame_cad(spec) -> "trimesh.Trimesh":
    """geom.Mesh 로 반환 (기존 파이프라인 호환). 그룹 이름 보존."""
    from drones import motor_angles, DRONE_GROUP_MAT   # 순환 import 회피용 지연

    key = spec.key
    diag = spec.diagonal_mm / 1000.0
    r = diag / 2.0
    A = Assembly()

    # ---- 기종별 치수 --------------------------------------------------------
    if key == "s1000plus":
        # 옥토 — 원형 카본 센터프레임(상·하판) + 8암 + 긴 다리 + 벨리 짐벌
        Rc = 0.337 / 2                                   # 센터프레임 지름 337 mm (공식)
        plate_t = 0.006
        A.add(cyl(Rc, plate_t, center=(0, 0, +0.045), seg=64), "body")     # 상판
        A.add(cyl(Rc, plate_t, center=(0, 0, -0.045), seg=64), "body")     # 하판
        for a in np.linspace(0, 360, 8, endpoint=False):                    # 기둥
            A.add(cyl(0.010, 0.090, center=(Rc * 0.72 * np.cos(np.radians(a)),
                                            Rc * 0.72 * np.sin(np.radians(a)), 0), seg=12), "body")
        for i, a in enumerate(motor_angles(spec)):
            A.add(_arm_folding(r, a, 0.020, 0.014, Rc * 0.95, z0=0.0, z1=0.005, bend=0.02), "arm")
            ca, sa = np.cos(np.radians(a)), np.sin(np.radians(a))
            A.add(_motor_bell(0.026, 0.032), "motor")
            A.parts["motor"][-1].apply_translation([r * ca, r * sa, 0.021])
            A.add(cyl(0.030, 0.006, center=(r * ca * 0.86, r * sa * 0.86, -0.004), seg=16), "accent")
        for g, m in _gear_tall(Rc * 2, -0.048, 0.30):
            A.add(m, g)
        for g, m in _gimbal_hanging(0.10, 0.075, 0.10, 0.0, -0.10, n_lens=1):
            A.add(m, g)
        A.add(box(0.16, 0.11, 0.055, center=(0, 0, 0.075)), "battery")      # 상단 배터리팩
        A.add(box(0.13, 0.10, 0.004, center=(0, 0, 0.010)), "pcb")
        A.add(box(0.14, 0.10, 0.030, center=(0, 0, -0.020)), "canopy")

    else:
        L = spec.body_l_mm / 1000.0
        W = spec.body_w_mm / 1000.0
        H = spec.body_h_mm / 1000.0
        bl = L * 0.62                                    # 동체 자체 길이(암 제외)
        bw = W * (0.40 if key != "phantom4" else 0.66)
        bh = H * (0.45 if key != "phantom4" else 0.52)

        A.add(_body_folding(bl, bw, bh,
                            nose_drop=0.22 if key != "phantom4" else 0.05,
                            n_pow=2.9 if key != "phantom4" else 3.4), "body")
        A.add(_canopy(bl, bw, bh, x0=-0.06, frac=0.62), "canopy")

        hub_r = 0.30 * max(bl, bw)
        arm_r0 = 0.055 * diag if not spec.fixed_arm else 0.085 * diag
        arm_r1 = 0.035 * diag if not spec.fixed_arm else 0.060 * diag
        mot_r, mot_h = 0.052 * diag, 0.048 * diag

        for i, a in enumerate(motor_angles(spec)):
            ca, sa = np.cos(np.radians(a)), np.sin(np.radians(a))
            grp = "arm" if spec.arm_style == "carbon" else "body"
            A.add(_arm_folding(r, a, arm_r0, arm_r1, hub_r,
                               z0=0.0, z1=0.012 * diag, bend=0.06 if not spec.fixed_arm else 0.02),
                  grp)
            bell = _motor_bell(mot_r, mot_h)
            bell.apply_translation([r * ca, r * sa, 0.014 * diag])
            A.add(bell, "motor")
            if spec.accent_rgb is not None and ca > 0.1:
                A.add(cyl(arm_r1 * 1.35, 0.06 * diag,
                          center=(r * ca * 0.80, r * sa * 0.80, 0.006 * diag), axis="x", seg=16),
                      "accent")

        # 짐벌 — 기종별 실루엣
        nose_x = 0.50 * bl
        if key == "mavic4pro":
            for g, m in _gimbal_infinity(0.032, nose_x + 0.006, -0.12 * bh):   # 볼 지름 64mm (실물 60~70mm)
                A.add(m, g)
        elif key == "matrice4e":
            for g, m in _gimbal_sensor(0.055, 0.052, 0.062, nose_x + 0.012, -0.34 * bh):
                A.add(m, g)
            A.add(revolve(np.array([[0, 0], [0.030, 0], [0.028, 0.012], [0.016, 0.024], [0, 0.028]]),
                          seg=32, center=(-0.10 * bl, 0, 0.52 * bh)), "canopy")   # RTK 돔
            A.add(cyl(0.004, 0.05, center=(-0.10 * bl, 0, 0.52 * bh + 0.04), seg=10), "pcb")
        elif key == "phantom4":
            for g, m in _gimbal_hanging(0.052, 0.048, 0.056, nose_x * 0.62, -0.62 * bh, n_lens=1):
                A.add(m, g)
            for dy in (-0.22, 0.22):                                  # 기수 비전센서
                A.add(cyl(0.006, 0.008, center=(nose_x * 0.96, dy * bw, -0.18 * bh),
                          axis="x", seg=12), "camera")
        else:                                                          # mini5pro
            for g, m in _gimbal_hanging(0.036, 0.034, 0.040, nose_x * 0.92, -0.30 * bh, n_lens=1):
                A.add(m, g)

        # 착륙장치
        if spec.gear == "legs":
            for g, m in _gear_skids(bl, bw, -0.50 * bh, 0.42 * H):
                A.add(m, g)
        elif spec.gear == "feet":
            for g, m in _gear_feet(bl, bw, -0.48 * bh, 0.22 * H):
                A.add(m, g)

        # 내부 금속 산란체 (RCS 지배) — 셸 안이라 렌더엔 안 보이지만 PO/SBR 이 센다
        A.add(box(bl * 0.50, bw * 0.62, bh * 0.55, center=(-0.06 * bl, 0, 0.02 * bh)), "battery")
        A.add(box(bl * 0.38, bw * 0.54, bh * 0.06, center=(0.02 * bl, 0, 0.26 * bh)), "pcb")

    # ---- 불리언: 겹친 파트의 **내부 면을 녹여 없앤다** ------------------------
    #   프리미티브를 겹쳐 놓으면 속에 파묻힌 면이 남아 PO/SBR 이 헛센다.
    #   합집합으로 하나의 껍질을 만들면 그런 면이 **애초에 존재하지 않는다.**
    for g in ("body", "arm", "motor", "camera", "gear", "canopy", "accent"):
        A.union_group(g)

    return A


def build_propeller_cad(spec, n_sec=22) -> Assembly:
    """프로펠러 1개 — **진짜 익형** 블레이드 + 허브."""
    R = spec.prop_dia_mm / 1000.0 / 2.0
    A = Assembly()
    A.add(_prop_hub(R * 0.085, R * 0.09), "prop")
    for b in range(spec.prop_blades):
        bl = _blade(R, chord_max=0.20 * R, n_sec=n_sec)
        A.add(rot_z(bl, (360.0 / spec.prop_blades) * b), "prop")
    A.union_group("prop")
    return A
