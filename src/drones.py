# -*- coding: utf-8 -*-
"""
drones.py — DJI 드론 5종의 '실측 제원' + 파라메트릭 3D 모델 생성기
==================================================================

목표
  사진처럼 보이는 '대충 만든 드론'이 아니라, **실제 제원(대각거리/무게/프로펠러
  지름/로터 수 …)을 그대로 반영**한 멀티로터 3D 모델을 만든다. 대각거리·프로펠러·
  로터 수는 제원 그대로, 동체 높이/두께는 비율 근사한다.

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
from dataclasses import dataclass

from geom import Mesh, rotate, translate


# --------------------------------------------------------------------------- #
#  드론 제원 + 외형 스타일
# --------------------------------------------------------------------------- #
@dataclass
class DroneSpec:
    key: str
    name: str
    # --- 실측 제원 (리서치+검증) ---
    diagonal_mm: float          # 모터-모터 대각거리(휠베이스)
    weight_g: float             # 무게[g] — 이륙중량(TOW). 단 S1000+ 는 기체(airframe) 자중 4.4 kg
                                #   (권장 TOW 6.0~11.0 kg, 대표 ~9.5, 최대 11)
    body_l_mm: float            # 동체(언폴드) 길이/폭/높이 — 외형 비율 참고용
    body_w_mm: float
    body_h_mm: float
    prop_dia_mm: float          # 프로펠러 지름
    prop_blades: int            # 날개 수
    num_rotors: int             # 로터 수 (=암 수, 비동축)
    coaxial: bool = False       # 동축(2개/암) 여부
    max_speed_ms: float | None = None
    max_rpm: float | None = None       # 최대 프로펠러 회전수[rpm] — DJI 인증표(C0/C1/C2)에 공식값이 있다
    prop_pitch_in: float | None = None # 프로펠러 피치[inch]
    hover_rpm: float = 6000.0    # 대표 호버 회전수[rpm] — 프로펠러 크기에 맞춘 현실값(마이크로도플러용).
                                 #   큰 프로펠러는 느리게(예: S1000 15in ~3500), 작은건 빠르게 돈다.
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
    # --- 공식 외형(암 펼침·**프로펠러 제외**) L×W×H [mm] — build_frame 이 여기에 맞춰진다 ---
    #   축별로 None 이면 그 축은 맞추지 않는다(= 공식값이 없음).
    #   ⚠ body_l_mm/body_w_mm/body_h_mm 는 '비율 참고용'이고 s1000plus·phantom4 는 L/W 자리에
    #     **대각선 값이 placeholder 로** 들어가 있다 → 그걸 외형으로 쓰면 안 된다. 그래서 별도 필드.
    envelope_mm: tuple | None = None
    # --- 드론별 개성(실루엣) — 스펙·대각·좌우대칭(비행안정) 유지하며 외형만 ---
    rotor_deg: tuple | None = None   # 모터 각도[deg] 목록. None=기본 X(쿼드)/옥토.
                                     #   접이형은 전방스윕(좌우대칭+마주보는 쌍 180°→대각 보존)
    body_lw: tuple = (1.15, 0.85)    # 동체 (길이,폭)/hub 비 — 접이 슬림기는 길쭉·좁게
    rotor_z_mm: tuple | None = None  # 로터별 z 오프셋[mm] — 프롭 디스크가 겹치는 기체(Mini)는
                                     #   앞/뒤 모터 높이가 다르다. None = 전부 같은 높이.
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
        diagonal_mm=275, weight_g=249.9,
        body_l_mm=255, body_w_mm=181, body_h_mm=91,
        prop_dia_mm=152.4, prop_blades=2, num_rotors=4,
        max_speed_ms=19, hover_rpm=5500, max_rpm=7800, prop_pitch_in=2.8, rtk=False, release="released", confidence="high",
        note="Diagonal (250 mm) not published by DJI — was estimated from the unfolded shape. "
             "⚠ 2026-07-14: after fitting the frame to the OFFICIAL envelope (255×181×91 mm), the "
             "implied motor-to-motor diagonal is 274.6 mm, i.e. the old 250 mm estimate was ~9% low. "
             "diagonal_mm is kept as-is (it only sizes arm/motor thickness); the envelope now rules. "
             "Weight/prop/rotor count official.",
        body_rgb=_GRAY_D, arm_style="body", gear="none", gimbal="front",
        accent_rgb=(0.95, 0.45, 0.05), body_frac=0.46,
        rotor_deg=(56.3, 123.7, 236.3, 303.7), body_lw=(1.42, 0.66), gimbal_style="single",
        rotor_z_mm=(-12.0, +2.0, +2.0, -12.0),   # ⚠ 프롭(152.4) > 앞뒤 모터간격(152) → 디스크가 겹친다.
                                                 #   실물은 **앞 모터가 더 낮다**(간섭 회피). 조사 확인.
        envelope_mm=(None, None, 91.0)),          # ⚠ **높이만** 공식이다.
        # DJI 는 Mini 5 Pro 의 **언폴드(프롭 제외) L×W 를 공개하지 않는다**(2026-07-14 심층조사 확인).
        # 공개된 것: 폴디드(프롭제외) 157×95×68,  언폴드(**프롭 포함**) 304×380×91.
        # 우리가 쓰던 (255, 181, 91) 은 x>y 인데 공식 언폴드는 380(y) > 304(x) 로 **방향이 반대**다
        # → 그 값은 틀렸다. 이제 **높이(91 mm)만** 강제하고, L/W 는 로터 배치가 정하게 둔다.
        # 로터 좌표는 조사 근거 (±76, ±114) mm → 각도 56.3°, 대각 275 mm → 좌우로 넓다(실물과 일치).
    # 2) 대형 소비자 플래그십 (출시작)
    "mavic4pro": DroneSpec(
        key="mavic4pro", name="DJI Mavic 4 Pro",
        diagonal_mm=441, weight_g=1063,
        body_l_mm=329, body_w_mm=391, body_h_mm=135,
        prop_dia_mm=267, prop_blades=2, num_rotors=4,
        max_speed_ms=25, hover_rpm=3600, max_rpm=6000, prop_pitch_in=5.8, rtk=False, release="released", confidence="high",
        note="Large consumer flagship (2025); front triple-camera gimbal (360° infinity). "
             "Weight/dimensions/propeller official (prop 266.7 mm, shown rounded to 267 mm). "
             "⚠ diagonal was ESTIMATED (400 mm) and is geometrically INCONSISTENT with the official "
             "envelope: 328.7×390.5 mm cannot be spanned by a 400 mm motor diagonal. Fitting the frame "
             "to the official envelope implies a diagonal of 440.9 mm. The envelope (official) wins; "
             "diagonal_mm is kept only as an arm/motor thickness scale.",
        body_rgb=_SILVER, arm_style="body", gear="none", gimbal="front",
        accent_rgb=None, body_frac=0.42,
        rotor_deg=(32, 148, 212, 328), body_lw=(1.52, 0.62), gimbal_style="triple",
        envelope_mm=(328.7, 390.5, 135.2)),      # DJI 공식(언폴드·프롭제외),
    # 3) 엔터프라이즈 측량기 (RTK 탑재)
    "matrice4e": DroneSpec(
        key="matrice4e", name="DJI Matrice 4E",
        diagonal_mm=438.8, weight_g=1219,
        body_l_mm=307, body_w_mm=388, body_h_mm=150,
        prop_dia_mm=274, prop_blades=2, num_rotors=4,
        max_speed_ms=21, hover_rpm=3800, max_rpm=7500, prop_pitch_in=5.7, rtk=True, release="released", confidence="high",
        note="Prop diameter confirmed 274 mm by verification (292->274). Onboard RTK. "
             "Max propeller speed 7500 RPM / 82 dB — DJI manual C2 certification (official). "
             "⚠ HOVER RPM UNRESOLVED: the C_T method (C_T 0.08-0.10) gives 3950-4410 rpm, but "
             "anchoring on the official max (7500 rpm) with a typical T/W of 2.0-2.5 gives 4740-5300 rpm. "
             "We currently use 3800 (C_T=0.108), which implies T/W(max)=3.9 — higher than the typical 2-2.5. "
             "**We do not know which is right.** Micro-Doppler flash/tip scale linearly with this. "
             "Needs telemetry or acoustic measurement to settle.",
        body_rgb=_OFFWHT, arm_style="body", gear="feet", gimbal="front",
        accent_rgb=None, body_frac=0.42,
        rotor_deg=(45, 135, 225, 315), body_lw=(1.08, 0.98), gimbal_style="sensor",
        envelope_mm=(307.0, 387.5, 149.5)),      # DJI 공식(언폴드·프롭제외),
    # 4) 대형 산업용 옥토콥터 (8암) — 단종, 카본 프레임
    "s1000plus": DroneSpec(
        key="s1000plus", name="DJI S1000+",
        diagonal_mm=1045, weight_g=9500,
        body_l_mm=1016, body_w_mm=1016, body_h_mm=380,
        prop_dia_mm=381, prop_blades=2, num_rotors=8,
        max_speed_ms=None, hover_rpm=3600, max_rpm=5600, prop_pitch_in=5.2, rtk=False, release="discontinued", confidence="high",
        note="Octocopter: 8 arms, 1 rotor per arm (non-coaxial). Carbon frame, retractable landing gear, belly gimbal. "
             "4400 g is the AIRFRAME weight; recommended takeoff weight 6.0-11.0 kg.",
        body_rgb=_BLACK, arm_style="carbon", gear="tall", gimbal="belly",
        accent_rgb=(0.85, 0.10, 0.10), body_frac=0.30,
        body_lw=(1.0, 1.0), gimbal_style="belly",
        envelope_mm=(1016.0, 1016.0, 380.0)),   # DJI 공식 — 센터프레임 337.5mm, 암 386mm, 랜딩기어 460x511x305,
    # 5) 고정암 쿼드 (클래식, 흰색 셸)
    "phantom4": DroneSpec(
        key="phantom4", name="DJI Phantom 4",
        diagonal_mm=350, weight_g=1380,
        body_l_mm=289.5, body_w_mm=289.5, body_h_mm=196,
        prop_dia_mm=240, prop_blades=2, num_rotors=4,
        max_speed_ms=20, hover_rpm=5500, max_rpm=8500, prop_pitch_in=5.0, rtk=False, release="released", confidence="high",
        note="Fixed (non-folding) arms, one-piece white shell + integrated landing legs. Classic Phantom shape.",
        body_rgb=_WHITE, arm_style="body", fixed_arm=True, gear="legs", gimbal="front",
        accent_rgb=None, body_frac=0.52,
        rotor_deg=(45, 135, 225, 315), body_lw=(1.06, 1.0), gimbal_style="recessed",
        envelope_mm=(289.5, 289.5, 196.0)),     # DJI 공식 Quick Start Guide v1.2 (프롭 제외),
}

# 부위(그룹) → (재질키, 한글설명).  **재질 정의는 materials.MATERIALS 가 유일한 진리원**이고,
#   Sionna RT(전파)와 PO(RCS)가 **둘 다 거기서 읽는다**. 여기선 '어느 부위가 어느 재질인가'만 정한다.
#   색은 build_drone 가 스펙에서 직접 지정(전파물성과 무관).
DRONE_GROUP_MAT = {
    "body":    ("plastic",         "동체 셸"),
    "canopy":  ("plastic",         "상단 캐노피/배터리"),
    "arm":     ("carbon",          "암"),
    "motor":   ("metal",           "모터"),
    "prop":    ("plastic",         "프로펠러"),
    "gear":    ("plastic",         "착륙장치"),
    "camera":  ("camera_assembly", "짐벌 카메라(금속 하우징+유리렌즈)"),
    "accent":  ("plastic",         "전방 식별색"),
    "battery": ("metal",           "배터리팩(내부) — GHz 에서 파우치 포일은 사실상 금속"),
    "pcb":     ("pcb",             "ESC/메인보드(내부) — FR-4 + 구리 그라운드플레인"),
}
#  ⚠ 2026-07-14 수정: camera 는 Sionna 에서 **plastic**(|Γ|=0.244)이었는데 PO 에선 0.85 였다
#     — 같은 부품을 두 엔진이 **10.9 dB** 다르게 본 버그. 이제 'camera_assembly'(ITU metal +
#     PO 실효 0.85)로 통합되어 그런 어긋남이 구조적으로 불가능하다.


def drone_gamma_map(spec: DroneSpec, fc: float = 3.5e9) -> dict:
    """드론 1종의 **그룹 → PO 진폭 반사계수 |Γ|** 맵.
    ⚠ 더 이상 손으로 적은 표가 아니다 — **materials.MATERIALS 에서 유도**한다(Sionna 와 동일 출처).
    셸형 암(arm_style≠carbon)은 build_frame 이 'body' 그룹으로 넣으므로 자동으로 플라스틱이 적용된다."""
    from materials import gamma_po
    return {grp: gamma_po(mat, fc) for grp, (mat, _) in DRONE_GROUP_MAT.items()}


# --------------------------------------------------------------------------- #
#  파라메트릭 멀티로터 생성기
# --------------------------------------------------------------------------- #
def motor_angles(spec: DroneSpec) -> list[float]:
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


_motor_angles = motor_angles    # 하위호환 별칭(viz_diagram 등 구버전 import 용)


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


# --------------------------------------------------------------------------- #
#  메쉬 엔진 — "cad"(기본) / "legacy"
# --------------------------------------------------------------------------- #
#  cad    : src/drone_cad.py — trimesh + manifold3d(불리언) + shapely + scipy 로 **실물 형상**에 맞춤.
#           매끈한 로프트 동체, 익형 프로펠러, 기종별 짐벌(Mavic4 = 구형 Infinity 짐벌),
#           착륙장치, RTK 돔. **불리언 합집합**으로 겹친 파트의 내부 면을 녹여 없앤다.
#  legacy : 예전 프리미티브 스택(비교·회귀용).
def _build_frame_raw(spec: DroneSpec) -> Mesh:
    """(내부) 외형보정 **전** 프레임 — CAD(trimesh+manifold3d 로프트/불리언) 단일 경로.
    (예전 프리미티브 조립 legacy 경로는 2026-07-20 제거 — git 히스토리에만 남음.)"""
    from drone_cad import build_frame_cad
    return build_frame_cad(spec).to_geom()


# --------------------------------------------------------------------------- #
#  공식 외형 맞춤 (envelope fit) — RCS 를 위해 **투영면적이 제원과 같아야** 한다
# --------------------------------------------------------------------------- #
#  왜 필요한가 (2026-07-14 감사):
#    파라메트릭 실루엣만으로 만든 프레임은 공식 외형과 크게 어긋나 있었다.
#      높이  : 전 기종 **−25 ~ −47 %**  (원인: _drone_dims 의 body_z = 0.35·body_h)
#      폭    : mavic4pro **−36 %**
#    저앙각(챔버 기하 el≈15°) 관측에선 **높이가 측면 투영면적을 지배**하고, 평판극한에서
#    σ ∝ (투영면적)² 이므로 높이 −44 % 는 σ 를 ~5 dB 과소평가한다 → RCS·Pd 에 직접 파급.
#  무엇을 하나:
#    실루엣(파라메트릭)은 그대로 두고, **프레임 바운딩박스가 공식 L×W×H 와 같아지도록**
#    축별 배율을 건다. 프로펠러는 제원 지름(prop_dia_mm)이 따로 있으므로 **스케일하지 않는다.**
#    모터 위치(rotor_layout)에는 같은 배율을 걸어 프로펠러가 모터 위에 정확히 앉게 한다.
#  대가(정직하게):
#    비등방 배율이라 모터 원통이 약간 타원이 된다(시각적 미세 왜곡). RCS 가 보는 것은
#    **투영면적과 외형**이므로 이쪽을 맞추는 것이 옳다는 판단.
#  ⚠ 대각선(diagonal_mm)은 모터-모터 거리이고 이 배율에 따라 **변한다** — 원래 스펙의
#    diagonal 은 mavic4pro 의 경우 '추정값'이고 공식 외형과 기하학적으로 모순이었다
#    (400 mm 로는 329×391 외형이 불가능; 외형에서 유도하면 ~440 mm). 공식 외형을 우선한다.
_FIT_CACHE: dict = {}


def frame_fit_scale(spec: DroneSpec) -> tuple[float, float, float]:
    """프레임을 공식 외형(spec.envelope_mm)에 맞추는 축별 배율 (sx, sy, sz).
    envelope_mm 이 없거나 해당 축이 None 이면 그 축 배율은 1.0."""
    if spec.key in _FIT_CACHE:
        return _FIT_CACHE[spec.key]
    env = spec.envelope_mm
    if not env:
        _FIT_CACHE[spec.key] = (1.0, 1.0, 1.0)
        return _FIT_CACHE[spec.key]
    import numpy as _np
    V = _np.asarray(_build_frame_raw(spec).v, float)
    ext = (V.max(0) - V.min(0)) * 1000.0                  # 현재 바운딩박스 [mm]
    s = []
    for i in range(3):
        tgt = env[i]
        s.append(1.0 if (tgt is None or ext[i] <= 1e-9) else float(tgt) / float(ext[i]))
    _FIT_CACHE[spec.key] = tuple(s)
    return _FIT_CACHE[spec.key]


def build_frame(spec: DroneSpec) -> Mesh:
    """**회전하지 않는 부분**: 동체/캐노피/암/모터/착륙장치/카메라/액센트 (프로펠러 제외).
    드론 로컬 프레임(전방 +x). 바운딩박스는 **공식 외형(envelope_mm)과 일치**한다.
    pose_articulated 에서 몸체 자세를 통째로 적용한다."""
    m = _build_frame_raw(spec)
    sx, sy, sz = frame_fit_scale(spec)
    return m if (sx, sy, sz) == (1.0, 1.0, 1.0) else m.scaled(sx, sy, sz)


def build_propeller(spec: DroneSpec, n: int = 10) -> Mesh:
    """프로펠러 1개 — **진짜 익형(NACA-4)** 로프트 블레이드 + 허브 (CAD 단일 경로).
    n 은 블레이드 스팬 분할 힌트(마이크로도플러는 크게 줘서 단면을 촘촘히).
    pose_articulated 가 이 메쉬를 z회전(스핀)시켜 각 로터에 배치한다."""
    from drone_cad import build_propeller_cad
    return build_propeller_cad(spec, n_sec=max(12, n * 2)).to_geom()


def rotor_layout(spec: DroneSpec) -> list[dict]:
    """로터별 배치: {center:(x,y,z), base_ang:deg(장착 오프셋), dir:+1/-1(CCW/CW)}.
    dir 은 인접 로터가 반대로 도는 멀티로터 관례(대각쌍 동일). build_drone 과 동일 좌표."""
    diag, r, prop_r, bh, body_l, body_w, body_z = _drone_dims(spec)
    arm_t = (0.08 if spec.fixed_arm else 0.045) * diag
    motor_h = 0.045 * diag
    prop_z = motor_h + arm_t / 2 + 0.006
    sx, sy, sz = frame_fit_scale(spec)            # 프레임과 **같은** 외형보정 배율
    zoff = spec.rotor_z_mm or ((0.0,) * spec.num_rotors)
    out = []
    for k, ang in enumerate(motor_angles(spec)):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        dz = float(zoff[k]) / 1000.0 if k < len(zoff) else 0.0   # 로터별 z 오프셋(프롭 디스크 겹침 회피)
        out.append(dict(center=(r * ca * sx, r * sa * sy, (prop_z + dz) * sz),
                        base_ang=ang + 12.0, dir=(1 if k % 2 == 0 else -1)))
    return out


def frame_envelope_mm(spec: DroneSpec) -> dict:
    """진단용: 이 스펙이 만드는 프레임의 실제 외형/대각선을 재서 공식값과 비교한다."""
    import numpy as _np
    V = _np.asarray(build_frame(spec).v, float)
    ext = (V.max(0) - V.min(0)) * 1000.0
    C = _np.array([r["center"] for r in rotor_layout(spec)], float)
    diag_eff = 2.0 * float(_np.linalg.norm(C[:, :2], axis=1).mean()) * 1000.0
    return dict(lwh_mm=tuple(map(float, ext)), official_mm=spec.envelope_mm,
                diagonal_spec_mm=spec.diagonal_mm, diagonal_effective_mm=diag_eff,
                fit_scale=frame_fit_scale(spec))


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




MATERIAL_COLOR = {
    # 색 = 순수 재질 분류(2026-07-20 사용자 지시). 물리적으로 같은 재질이면 같은 색 —
    # 프로펠러는 몸체와 같은 플라스틱이므로 같은 회색이다(별도 재질 아님).
    # 5색 팔레트(2026-07-20 재선정): 재질 수가 적으니 상호 구분 최대화 —
    # 무채색 2(회/흑) + 파랑/주황/초록. 같은 계열 색(강청 vs 청록) 혼동 제거.
    "plastic":         (0.82, 0.82, 0.85),   # 밝은 회색 — 플라스틱(셸/캐노피/착륙장치/식별색/프로펠러)
    "carbon":          (0.09, 0.09, 0.10),   # 검정 — 탄소섬유(CFRP) 암
    "metal":           (0.30, 0.50, 0.85),   # 파랑 — 금속(모터·배터리 포일)
    "camera_assembly": (0.90, 0.50, 0.10),   # 주황 — 금속하우징+유리렌즈 복합체(별개 재질)
    "pcb":             (0.10, 0.60, 0.25),   # 초록 — FR-4+구리(별개 재질)
}


def drone_colors(spec: DroneSpec) -> dict:
    """부위 그룹 → **재질별** 표시색 RGB. **모든 드론이 같은 규칙**이라 색만 보면 재질을 안다:
      plastic=회색(프로펠러 포함) · carbon=검정 · metal=파랑 · camera=주황 · pcb=초록.
    (색과 전파재질은 **같은 그룹**(DRONE_GROUP_MAT)에서 나온다 — 이제 렌더 색이 곧 재질이다.)
    이전의 드론별 개성 색(body_rgb/accent_rgb 기반)은 재질이 헷갈려 폐기했다."""
    return {grp: MATERIAL_COLOR.get(mat, (0.7, 0.7, 0.7))
            for grp, (mat, _) in DRONE_GROUP_MAT.items()}


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
