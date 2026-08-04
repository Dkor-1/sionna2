# -*- coding: utf-8 -*-
"""
airframe_phantom3.py — **측정된 기체(DJI Phantom 3)를 우리 파라메트릭 방식으로 짓는다**
========================================================================================
왜 이 파일이 따로 있나
  우리 σ 는 지금까지 **실측된 기체와 한 번도 맞대본 적이 없다**. 맞대볼 수 있는 유일한 기체가
  DJI Phantom 3 다 — Das(WCL 2026)와 Yuan(EuCAP 2025)이 잰 그 기체이고, 무향실 · 원거리장 ·
  1.8~18.2 GHz 로 **우리 세 밴드를 전부 덮는** 유일한 플랫폼이다
  (근거·판정 전문은 outputs/validation_feasibility.json).

  ⛔ 이 파일은 `src/drones.py` · `src/drone_cad.py` 를 **건드리지 않는다**(다른 워크플로가 그 안에
     있다). 대신 두 파일의 **헬퍼를 그대로 import** 해서 같은 프리미티브·같은 그룹 규약·같은
     불리언 합집합으로 P3 를 짓는다. 레지스트리 등록 패치는 `registration_patch()` 가 문자열로
     돌려준다(적용은 소유 워크플로가 한다).

■ 치수의 1차 제약 = **측정 논문이 적은 값** (표적과 같은 물건을 만드는 것이 목적이므로)
    Das Table I  : "DJI Phantom 3 … 35 cm x 20 cm"           (대각 350 · 높이 200 mm)
    Yuan §II-A   : "the DJI Phantom 3, featuring four symmetrical rotors with a horizontal
                    diagonal of 35 cm and a height of 20 cm"
  제조사 공표로 교차확인:
    DJI Phantom 3 Professional/Advanced/Standard 지원페이지 — **Diagonal Size (Propellers
      Excluded) 350 mm**, Weight (battery & propellers included) **1280 g**(Pro/Adv),
      Max Speed 57.6 km/h(=16 m/s, ATTI·무풍).
    프로펠러 **DJI 9450 self-tightening**, DJI 프롭 치수표 **24 × 12.7 cm** → 지름 240 mm ·
      기하피치 5.0 in. (P4 와 **같은 부품번호**다 — 저장소 phantom4 note 와 동일 근거.)
    독립 확인: NASA/US Army 가 "DJI Phantom 3 + 9450 prop" 로 호버 C_T 를 실측했다
      (Russell/Jung/Willink/Glasner, AHS Forum 72, 2016) — 저장소가 이미 인용 중인 그 자료다.

■ ⚠ **정직 표기 — 무엇이 측정이고 무엇이 상속인가**
  (a) 대각 350 · 높이 200 · 프롭 240 · 45° X 고정암 : 측정논문 + 제조사 공표 (VERIFIED)
  (b) 셸 단면법칙(_SHELL_SHAPE) · 암 폭(_ARM_WIDTH) · 아치 다리 비율 :
      **Phantom 4 사진실측표를 상속**했다. 저장소에 Phantom 3 사진이 한 장도 없다.
      P3/P4 는 같은 350 mm 급 · 같은 일체형 흰 셸 · 같은 고정 X 암 · 같은 9450 프롭 · 같은
      아치 다리 가족이지만, **같은 형상은 아니다**. 이것이 이 메쉬의 최대 불확도이고
      그래서 검증 스크립트가 P4 를 **형상 민감도 대조군**으로 같이 돌린다.
  (c) P3 에만 맞춘 것(= P4 에서 뺀 것): 전방/후방 장애물감지 스테레오 카메라 4개와 측면 3D IR
      2개는 **P4 에서 처음 들어간 부품**이라 뺐다. P3 Pro/Adv 의 벨리 센서는
      하방 비전카메라 2 + 초음파 2(VPS) 뿐이다. 상단 GPS 퍽도 P4 사진실측에서 나온 것이라 뺐다.
  (d) 변종 미상: Yuan/Das 는 "DJI Phantom 3" 라고만 적는다(Standard/4K/Advanced/Professional).
      네 변종은 대각·셸·프롭이 같고 카메라/짐벌/(Standard)모터가 다르다 → **통제되지 않은 항**.

좌표·단위·그룹 규약은 drones.py 와 완전히 동일하다(전방 +x, z-up, 모터면 z=0, m 단위).
"""
from __future__ import annotations

import math
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import numpy as np                                            # noqa: E402

from cadkit import Assembly, box, cyl                          # noqa: E402
from drone_cad import (_ARM_SECTION, _ARM_WIDTH, _SHELL_SHAPE,  # noqa: E402
                       _arm_folding, _body_folding, _canopy, _gear_arch,
                       _gimbal_hanging, _motor_bell)
from drones import (DRONES, DroneSpec, _arm_motor_dims, build_propeller,  # noqa: E402
                    motor_angles, motor_radii)
from geom import Mesh, rotate, translate                        # noqa: E402

_WHITE = (0.93, 0.93, 0.95)

#  P3 형상을 상속받는 원본 기종 — **한 곳에만 적는다**(어디서 왔는지 흐려지지 않게).
SHAPE_DONOR = "phantom4"

PHANTOM3 = DroneSpec(
    key="phantom3", name="DJI Phantom 3",
    #  ⭐ 대각: 측정논문 2편 + DJI 지원페이지 3변종 전부 350 mm 로 일치.
    diagonal_mm=350.0,
    #  무게: DJI Phantom 3 Professional/Advanced 공표 1280 g(배터리·프롭 포함).
    #    (Standard 는 1216 g — 변종 미상이므로 Pro/Adv 값을 쓰고 note 에 남긴다. RCS 무관.)
    weight_g=1280.0,
    #  동체 기준치수 [mm] — L/W 는 **공표값이 아니라 유도값**이다:
    #    대각 350 · 45° X 배치이므로 모터 중심은 ±123.74 mm, 모터벨 지름 2·0.052·350 = 36.4 mm
    #    → 모터 끝-끝 폭 = 247.5 + 36.4 = 283.9 mm. 여기에 셸 어깨를 더한 값이 P4 의 **공표**
    #    외형 289.5 × 289.5 와 사실상 같다(P4 도 대각 350 · 45° X 다) → 289.5 를 그대로 쓴다.
    #    ⚠ 이것은 '같은 기하에서 나온 유도값' 이지 P3 의 공표 외형이 아니다(DJI 미공개).
    #    높이 200 mm 는 **측정논문이 직접 적은 값**이다(Das Table I · Yuan §II-A).
    body_l_mm=289.5, body_w_mm=289.5, body_h_mm=200.0,
    #  프로펠러: DJI 9450(P4 와 같은 부품) — DJI 프롭 치수표 24 × 12.7 cm.
    prop_dia_mm=240.0, prop_blades=2, num_rotors=4,
    max_speed_ms=16.0,
    #  호버 rpm — RCS 에 **전혀 들어가지 않는다**(정적 메쉬). 마이크로도플러용 자리표시자로만 둔다.
    #    P4 의 코드값 5500 rpm 을 추력비로 옮긴 값: rpm ∝ √T ∝ √m → 5500·√(1280/1380) = 5297.
    hover_rpm=5300.0, max_rpm=None, prop_pitch_in=5.0,
    rtk=False, release="discontinued", confidence="high",
    note=("VALIDATION TARGET — the airframe that Das (IEEE WCL 15:3731, 2026) and Yuan (EuCAP "
          "2025) actually measured. Dimensions are the measurement papers' own: Das Table I "
          "'35 cm x 20 cm', Yuan II-A 'horizontal diagonal of 35 cm and a height of 20 cm'. "
          "DJI support pages give Diagonal Size (Propellers Excluded) 350 mm for Standard / "
          "4K / Advanced / Professional alike, weight 1280 g (Pro/Adv), and the propeller is "
          "the DJI 9450 self-tightening (24 x 12.7 cm per DJI's propeller table) - the SAME "
          "part number as the Phantom 4. "
          "INHERITED, NOT MEASURED: the shell cross-section law, the arm width table and the "
          "arch-leg proportions are the Phantom 4 photo-audit values (no Phantom 3 photograph "
          "exists in this repository). P3 and P4 share the 350 mm class, the one-piece white "
          "shell, the fixed 45 deg X arms, the 9450 propeller and the arch legs - they are not "
          "the same shape. That is this mesh's dominant uncertainty and the reason the "
          "validation script also runs the P4 as a shape-sensitivity control. "
          "REMOVED vs P4 (P4-only hardware): forward/backward obstacle-sensing stereo pairs, "
          "side 3D infrared modules, top GPS/compass puck. P3 Pro/Adv carry only the downward "
          "Vision Positioning System (2 cameras + 2 ultrasonic transducers), which is built. "
          "UNCONTROLLED: which Phantom 3 variant was measured (Standard / 4K / Advanced / "
          "Professional) - the papers say only 'DJI Phantom 3'."),
    body_rgb=_WHITE, arm_style="body", fixed_arm=True, gear="legs", gimbal="front",
    accent_rgb=None, body_frac=0.52, shape_source="spec_photo",
    rotor_deg=(45, 135, 225, 315), body_lw=(1.06, 1.0),
    gimbal_style="recessed", cad_version="v2",
    #  ⭐ **높이만** 강제한다 — 200 mm 는 측정논문이 적은 값이다. L/W 는 로터 배치가 정하게 둔다
    #    (mini5pro·mavic4pro·matrice4e 와 같은 처리). DJI 는 P3 의 L/W 를 공표하지 않는다.
    envelope_mm=(None, None, 200.0))


# --------------------------------------------------------------------------- #
#  프레임 — drone_cad 의 phantom(셸형·고정암) 경로를 **그대로** 밟되 P3 부품만 얹는다
# --------------------------------------------------------------------------- #
def build_p3_frame_raw(spec: DroneSpec = PHANTOM3) -> Assembly:
    """외형보정 **전** 프레임. drone_cad.build_frame_cad 의 셸 분기와 같은 순서·같은 헬퍼."""
    diag = spec.diagonal_mm / 1000.0
    r_list = motor_radii(spec)
    A = Assembly()

    L, W, H = spec.body_l_mm / 1000.0, spec.body_w_mm / 1000.0, spec.body_h_mm / 1000.0
    sh = _SHELL_SHAPE[SHAPE_DONOR]                 # ⚠ 상속(P4 사진실측) — 파일 헤더 (b) 참조
    bl, bw, bh = L * sh["fl"], W * sh["fw"], H * sh["fh"]

    A.add(_body_folding(bl, bw, bh, nose_drop=sh["ndrop"], n_pow=sh["npow"],
                        hw_f=sh["hw"], hh_f=sh["hh"], zo_f=sh["zo"]), "body")
    A.add(_canopy(bl, bw, bh * sh["cfh"], x0=sh["cx0"], frac=sh["cfrac"]), "canopy")
    hub_r = sh["hubf"] * max(bl, bw)

    arm_r0, arm_r1 = (v / 2000.0 for v in _ARM_WIDTH[SHAPE_DONOR])     # ⚠ 상속
    _hr, _cr = _ARM_SECTION[SHAPE_DONOR]                               # ⚠ 상속
    mot_r, mot_h = 0.052 * diag, 0.048 * diag
    for i, a in enumerate(motor_angles(spec)):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        r_k = r_list[i]
        #  arm_style='body' → 암은 **셸과 같은 그룹**이다(팬텀 실물이 그렇다: 암이 셸 일체 성형).
        A.add(_arm_folding(r_k, a, arm_r0, arm_r1, hub_r, z0=0.0, z1=0.012 * diag,
                           bend=0.02, h_ratio=_hr, c_ratio=_cr), "body")
        bell = _motor_bell(mot_r, mot_h)
        bell.apply_translation([r_k * ca, r_k * sa, 0.014 * diag])
        A.add(bell, "motor")

    #  짐벌 — 코 아래 매달린 3축(방진판 + 요크 + 카메라 박스 + 렌즈). P4 와 같은 급이다.
    nose_x = 0.50 * bl
    for g, m in _gimbal_hanging(0.052, 0.048, 0.056, nose_x * 0.62, -0.62 * bh, n_lens=1):
        A.add(m, g)

    #  ⭐ P3 Pro/Adv 의 벨리 센서 = **하방 비전 2 + 초음파 2** (Vision Positioning System).
    #    P4 의 전/후방 스테레오 4 · 측면 3D IR 2 · 상단 GPS 퍽은 **P4 부품이라 넣지 않는다.**
    for dy in (-0.14, 0.14):                                   # 하방 비전 카메라
        A.add(cyl(0.005, 0.006, center=(0.06 * bl, dy * bw, -0.46 * bh), axis="z", seg=10), "camera")
    for dy in (-0.26, 0.26):                                   # 초음파 트랜스듀서(금속 캔)
        A.add(cyl(0.008, 0.007, center=(0.02 * bl, dy * bw, -0.46 * bh), axis="z", seg=16), "camera")

    #  착륙장치 — 아치형(inverted-U) 2개. 비율은 P4 사진실측 상속.
    for g, m in _gear_arch(bl, bw, -0.50 * bh, 0.58 * H):
        A.add(m, g)

    #  내부 금속 산란체 — 셸형 기체 공용 규약(drone_cad 의 셸 분기와 **같은 식**).
    #    배터리(Li-NMC 파우치) + PCB(FR-4+구리) + 마그네슘합금 구조판.
    A.add(box(bl * 0.50, bw * 0.62, bh * 0.55, center=(-0.06 * bl, 0, 0.02 * bh)), "battery")
    A.add(box(bl * 0.38, bw * 0.54, bh * 0.06, center=(0.02 * bl, 0, 0.26 * bh)), "pcb")
    A.add(box(bl * 0.58, bw * 0.68, bh * 0.08, center=(-0.02 * bl, 0, -0.04 * bh)), "battery")

    for g in ("body", "motor", "camera", "gear", "canopy"):
        A.union_group(g)
    return A


_FIT: dict = {}


def p3_fit_scale(spec: DroneSpec = PHANTOM3) -> tuple:
    """`spec.envelope_mm` 에 프레임 bbox 를 맞추는 축별 배율 — drones.frame_fit_scale 과 같은 규약."""
    ck = (spec.key, spec.envelope_mm, spec.body_l_mm, spec.body_w_mm, spec.body_h_mm,
          spec.diagonal_mm)
    if ck in _FIT:
        return _FIT[ck]
    env = spec.envelope_mm
    if not env:
        _FIT[ck] = (1.0, 1.0, 1.0)
        return _FIT[ck]
    V = np.asarray(build_p3_frame_raw(spec).to_geom().v, float)
    ext = (V.max(0) - V.min(0)) * 1000.0
    s = [1.0 if (env[i] is None or ext[i] <= 1e-9) else float(env[i]) / float(ext[i])
         for i in range(3)]
    _FIT[ck] = tuple(s)
    return _FIT[ck]


def build_phantom3_frame(spec: DroneSpec = PHANTOM3) -> Mesh:
    A = build_p3_frame_raw(spec)
    sx, sy, sz = p3_fit_scale(spec)
    m = A.to_geom()
    if (sx, sy, sz) == (1.0, 1.0, 1.0):
        return m
    out = Mesh()
    out.v = [(x * sx, y * sy, z * sz) for (x, y, z) in m.v]
    out.f = list(m.f)
    out.g = list(m.g)
    return out


def p3_rotor_layout(spec: DroneSpec = PHANTOM3) -> list:
    """drones.rotor_layout 와 **같은 식**(같은 _arm_motor_dims·같은 base_ang·같은 dir 관례)."""
    diag = spec.diagonal_mm / 1000.0
    _arm_t, _motor_h, prop_z = _arm_motor_dims(spec, diag)
    sx, sy, sz = p3_fit_scale(spec)
    radii = motor_radii(spec)
    out = []
    for k, ang in enumerate(motor_angles(spec)):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        out.append(dict(center=(radii[k] * ca * sx, radii[k] * sa * sy, prop_z * sz),
                        base_ang=ang + 12.0, dir=(1 if k % 2 == 0 else -1)))
    return out


def build_phantom3(spec: DroneSpec = PHANTOM3) -> Mesh:
    """정적 P3 메쉬(프레임 + 프로펠러 4개) — drones.build_drone 과 같은 조립 규약."""
    m = build_phantom3_frame(spec)
    prop_ccw = build_propeller(spec)
    prop_cw = build_propeller(spec, mirror=True)
    for rot in p3_rotor_layout(spec):
        cx, cy, cz = rot["center"]
        M = translate(cx, cy, cz) @ rotate("z", rot["base_ang"])
        m.merge((prop_ccw if rot["dir"] > 0 else prop_cw).transformed(M), group="prop")
    return m


# --------------------------------------------------------------------------- #
#  진단 — 만들어진 것이 실제로 P3 치수인가
# --------------------------------------------------------------------------- #
def p3_envelope_report(spec: DroneSpec = PHANTOM3) -> dict:
    F = np.asarray(build_phantom3_frame(spec).v, float)
    D = np.asarray(build_phantom3(spec).v, float)
    C = np.array([r["center"] for r in p3_rotor_layout(spec)], float)
    n = len(C)
    opp = [float(np.linalg.norm(C[k, :2] - C[(k + n // 2) % n, :2])) * 1000.0 for k in range(n)]
    pr = spec.prop_dia_mm / 2.0
    return dict(
        frame_lwh_mm=[float(v) for v in (F.max(0) - F.min(0)) * 1000.0],
        full_lwh_mm=[float(v) for v in (D.max(0) - D.min(0)) * 1000.0],
        wheelbase_opposite_mm=float(np.mean(opp)),
        wheelbase_spec_mm=float(spec.diagonal_mm),
        wheelbase_err_pct=float(100.0 * (np.mean(opp) - spec.diagonal_mm) / spec.diagonal_mm),
        height_mm=float((F.max(0) - F.min(0))[2] * 1000.0),
        height_paper_mm=200.0,
        prop_disc_span_mm=float(2.0 * (np.abs(C[:, :2]).max() * 1000.0 + pr)),
        prop_tip_clearance_adjacent_mm=float(
            np.linalg.norm(C[0, :2] - C[1, :2]) * 1000.0 - spec.prop_dia_mm),
        fit_scale=[float(v) for v in p3_fit_scale(spec)],
        n_tris=int(len(build_phantom3(spec).f)),
        groups=sorted(set(build_phantom3(spec).g)))


def registration_patch() -> str:
    """레지스트리에 P3 를 넣으려면 소유 워크플로가 적용할 패치(문자열). **여기서 적용하지 않는다.**"""
    return (
        "# --- src/drones.py : DRONES 레지스트리에 추가 -------------------------------\n"
        "#   benchmark/airframe_phantom3.PHANTOM3 을 그대로 붙여넣으면 된다(DroneSpec 리터럴).\n"
        "#   ⚠ key='phantom3' 은 drone_cad.build_frame_cad 에 분기가 없어 NotImplementedError 로\n"
        "#     죽는다 → 아래 둘 중 하나가 **반드시** 함께 들어가야 한다.\n"
        "# --- src/drone_cad.py : build_frame_cad 의 짐벌 분기 ------------------------\n"
        "#   elif key in ('phantom4', 'phantom3'):\n"
        "#       for g, m in _gimbal_hanging(0.052, 0.048, 0.056, nose_x * 0.62, -0.62 * bh, n_lens=1):\n"
        "#           A.add(m, g)\n"
        "#       if key == 'phantom4':\n"
        "#           ... (전/후방 스테레오 4 · 측면 3D IR 2 · 상단 GPS 퍽 = P4 전용 부품)\n"
        "#       else:   # phantom3 — VPS 만\n"
        "#           for dy in (-0.14, 0.14):\n"
        "#               A.add(cyl(0.005, 0.006, center=(0.06*bl, dy*bw, -0.46*bh), axis='z', seg=10), 'camera')\n"
        "#           for dy in (-0.26, 0.26):\n"
        "#               A.add(cyl(0.008, 0.007, center=(0.02*bl, dy*bw, -0.46*bh), axis='z', seg=16), 'camera')\n"
        "#   그리고 _SHELL_SHAPE / _ARM_WIDTH / _ARM_SECTION 에 'phantom3' 키를 넣지 **않으면**\n"
        "#   _SHELL_DEFAULT 로 떨어져 형상이 달라진다 → phantom4 값을 명시 복사하거나\n"
        "#   `_SHELL_SHAPE['phantom3'] = _SHELL_SHAPE['phantom4']` 로 **상속을 눈에 보이게** 적을 것.\n"
        "# --- benchmark/rcs_anchor.py : DRONE_KEYS 에 'phantom3' 추가 ----------------\n"
        "# --- src/gazebo_export.py DENSITY · viz 팔레트는 그룹이 기존과 같아 수정 불필요 ---\n")


if __name__ == "__main__":
    import json
    rep = p3_envelope_report()
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    p4 = DRONES["phantom4"]
    print(f"\n[대조] phantom4 대각 {p4.diagonal_mm} · 프롭 {p4.prop_dia_mm} · 높이 {p4.body_h_mm}")
    print(f"       phantom3 대각 {PHANTOM3.diagonal_mm} · 프롭 {PHANTOM3.prop_dia_mm} "
          f"· 높이 {PHANTOM3.body_h_mm}")
