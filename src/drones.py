# -*- coding: utf-8 -*-
"""
drones.py — 표적 드론의 '실측 제원' + 파라메트릭 3D 모델 생성기
==================================================================

표적 목록은 아래 `DRONES` 레지스트리 **하나**가 정한다 — 저장소의 개수 출처는 `len(DRONES)` 뿐이다.
  현재 **10종**: DJI 8종(Mini 5 Pro · Mavic 4 Pro · Matrice 4E · S1000+ · Phantom 4
  · Phantom 3, 2026-08-03 추가 · Matrice 350 RTK, 2026-08-03 추가 · Mini 2, 2026-08-03 추가)
  + 비-DJI 2종(Yuneec Typhoon H480 · Holybro X500 V2, 2026-07-30 추가).
  ⚠ 이 문장이 저장소에서 개수를 산문으로 적는 **유일한 자리**다. 코드·다른 문서는 개수를
    하드코딩하지 말고 `len(DRONES)` / `drone_keys()` / `drone_order()` 를 쓴다(그 함수들 주석 참조).

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
from dataclasses import dataclass, fields as _dc_fields

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
    max_rpm: float | None = None       # 최대 프로펠러 회전수[rpm]
    #   ⚠ **물리적 최대치가 아니라 인증 등급(C0/C1/C2)·펌웨어 상한이다.** DJI Mini 5 Pro 매뉴얼은
    #     동일 기체·동일 6028F 프롭·동일 배터리에 대해 C0 모델 7800 RPM, C1 모델 11200 RPM 을
    #     선언한다(43% 차이). 따라서 (n_max/n_hover)² 를 추력비로 쓰면 안 된다.
    #     matrice4e 는 코드 7500 vs docs/drone_specs_2026.json 6130 으로 충돌 상태 — 미해결.
    prop_pitch_in: float | None = None # 프로펠러 기하피치[inch] — 제조사 공표값(출처는 기종별 note)
    hover_rpm: float = 6000.0    # 대표 호버 회전수[rpm] — 마이크로도플러 flash_hz·f_tip 이 여기 **선형**으로 걸린다.
    #   ⚠ **provenance 정정(2026-07-28)**: docs/DRONE_SPECS.md·ARCHIVE.md 는 이 값이 추력균형
    #     T = C_T·ρ·n²·D⁴ 에서 "유도된다" 고 적어 왔지만 **거짓이다** — 기종별 하드코딩 리터럴이고,
    #     추력균형은 src/viz_report1.py 의 **사후 표시용 역산**(이미 정한 rpm 에서 C_T 를 되푼다)일
    #     뿐이다. 따라서 weight_g·prop_dia_mm 를 고쳐도 hover_rpm 은 **따라오지 않는다**.
    #     값의 근거는 기종별 note 를 볼 것(s1000plus·matrice4e 는 NASA 실측 C_T 앵커).
    rtk: bool = False
    release: str = "released"   # released / rumored_unreleased / discontinued
    # ⚠ 2026-07-31 — `confidence` 는 **제원(스펙 숫자)의 신뢰도**지 **형상 충실도가 아니다**.
    #   둘을 같은 이름으로 읽다가 정반대로 해석한 적이 있다. 실측한 사진↔메쉬 실루엣 일치도
    #   (`outputs/mesh_compare_photo.json`, 자기복제 상한으로 정규화)는 이 플래그와 **역순**이다:
    #     x500v2  confidence=medium → 상한대비 91 %  (제조사 STEP 기반)
    #     mini5pro confidence=high  → 상한대비 50 %  (스펙시트+사진 기반)
    #   즉 제원은 잘 알려져 있어도(high) 형상은 추정이다. 형상 충실도는 `shape_fidelity` 를 보라.
    confidence: str = "high"
    # 형상 충실도의 **출처**. 사진 일치도가 이것을 따라간다 — 지표가 아니라 근거를 적는다.
    #   'manufacturer_cad' : 제조사 STEP/CAD 실측 기반
    #   'spec_photo'       : 공개 제원 + 사진 대조 기반(추정 구간 있음)
    shape_source: str = "spec_photo"
    note: str = ""
    # --- 외형 스타일(렌더용) ---
    body_rgb: tuple = (0.5, 0.5, 0.5)
    arm_style: str = "carbon"   # 'carbon'(어두운 암) / 'body'(동체색 암; 고정형)
    fixed_arm: bool = False     # True 면 굵은 고정암(팬텀류)
    gear: str = "none"          # 'none' / 'legs'(팬텀) / 'tall'(S1000) / 'feet'
    gimbal: str = "front"       # 'front'(전방하단) / 'belly'(중앙하단) / 'none'(카메라 없음)
                                #   ⚠ 이 필드는 **아무도 읽지 않는다**(2026-07-30 확인) — 형상을 정하는 것은
                                #     gimbal_style 이다. 라벨용으로만 남아 있으니 둘을 어긋나게 적지 말 것.
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
    rotor_r_mm: tuple | None = None  # ⭐ 2026-07-31 추가 — **로터별 중심반경**[mm].
    #   None 이면 전 로터가 한 원(diagonal_mm/2) 위에 있다(기존 동작, 기존 메쉬 비트동일).
    #   값을 주면 `rotor_deg` 와 **같은 순서·같은 길이**여야 하고, 로터 k 는
    #   (r_k·cos θ_k, r_k·sin θ_k) 에 놓인다 → **사다리꼴(trapezoid) 배치**를 표현할 수 있다.
    #   왜 필요한가: DJI 접이식 기체의 앞 암은 뒤 암보다 길고 더 벌어져 있다. 한 원 위의
    #   각도만으로는 그 형상을 표현할 수 없어서, 폭을 맞추려면 모터 지름을 실물의 1.7배로
    #   부풀리는 수밖에 없었다(matrice4e note 의 '매듭'). 반경을 열면 그 매듭이 풀린다.
    #   ⚠ diagonal_mm 은 이 필드가 있으면 **로터 위치를 정하지 않는다** — 암 두께·모터 크기
    #     같은 비례식 기본값의 스케일로만 남는다(x500v2 가 이미 쓰는 규약과 같다).
    body_lw: tuple = (1.15, 0.85)    # 동체 (길이,폭)/hub 비 — 접이 슬림기는 길쭉·좁게
    rotor_z_mm: tuple | None = None  # 로터별 z 오프셋[mm] — 프롭 디스크가 겹치는 기체(Mini)는
                                     #   앞/뒤 모터 높이가 다르다. None = 전부 같은 높이.
    gimbal_style: str = "single"     # single / triple(마빅 3카메라) / sensor(매트리스+RTK)
                                     #   / recessed(팬텀 함몰) / belly(S1000 벨리)
    cad_version: str = "v1"          # "v1"(기존) / "v2"(실사진 대조로 형상 개선; 스펙 치수는 그대로)
    env_props_included: bool = False  # envelope_mm 의 높이가 **프롭 포함**값이면 True
                                      #   (프레임만 맞추면 프롭이 위로 더 올라가 총높이 초과 — frame_fit_scale 참고)
    # ----------------------------------------------------------------------- #
    #  열린 프레임(open-frame) + **실물 부품치수 오버라이드** (2026-07-30 추가)
    # ----------------------------------------------------------------------- #
    #  ⚠ 전부 기본값이 None/기존값이다 → 기존 5종의 메쉬는 **비트단위로 동일**하다(증거는 아래 참조).
    body_style: str = "shell"        # "shell"  = 성형 셸 동체(눈물방울 로프트 + 캐노피). 현재 기본값이므로
                                     #   레지스트리에서 몇 종이 셸형인지는 세지 말고 body_style 로 판정할 것
                                     # "plate_stack" = **셸이 없는 열린 프레임**(카본 판 2장 + 간격).
                                     #   개발용 프레임(Holybro X500 류)은 몰드 셸이 아예 없어서
                                     #   'body' 그룹으로 표현하면 존재하지 않는 유전체 셸을 만든다.
    plate_mm: tuple | None = None    # plate_stack 전용 (L, W, t_bottom, gap, t_top) [mm].
                                     #   gap 은 두 판의 **마주보는 면 사이 빈 간격**(총높이=t_bot+gap+t_top).
    arm_shape: str = "folding"       # "folding" = 테이퍼 + 벤드(접이식/고정암). 기본값 — 개수를 적지 않는다
                                     # "tube"    = **직선 등단면 원형 튜브**(카본 파이프, bend=0)
    #  ⭐ 아래 3개는 **대각비례 기본값을 덮는다**. drone_cad 는 암 반경·모터 크기를 대각의 비율
    #     (0.055·diag 등)로 잡는데, 그 법칙은 접이식 소비자기에서 역산된 것이라 500 mm 개발
    #     프레임에 쓰면 **반경 27.5 mm(폭 55 mm) 암**이 나온다 — 실물은 16 mm 파이프다.
    #     실측 부품치수가 있으면 비율을 쓰지 않는다. None 이면 기존 비례식 그대로.
    arm_od_mm: float | None = None      # 암 외경[mm] (튜브면 그대로 지름, 테이퍼암이면 등단면화)
    motor_dia_mm: float | None = None   # 모터 벨 지름[mm]
    motor_h_mm: float | None = None     # 모터 벨 높이[mm]
    gear_h_mm: float | None = None      # 착륙장치 높이[mm]. None 이면 0.30·body_h (기존 규약)
    gear_tube_mm: tuple | None = None   # 카본 튜브 착륙장치 (다리 OD, 스키드 OD) [mm]
    gear_splay_deg: float = 20.0        # 튜브 다리 벌림각[deg] (수직 기준 바깥쪽)
    #  rcs_sbr 에 넘길 '유전체 셸' 그룹. **열린 프레임은 () — 셸이 아예 없다.**
    #  ⚠ 현재 소비자는 없다(각 호출부가 rcs_sbr 기본 규약 _DIELECTRIC_SHELLS={body,canopy} 를 쓴다).
    #    열린 프레임에는 body·canopy 그룹이 **존재하지 않으므로** 기본값도 결과적으로 안전하다
    #    (셸 후보가 0개 → 투과 패스 없음). 배선은 Phase 3(저장소 전체 5종→7종)에서 한다.
    shell_groups: tuple | None = None
    # ----------------------------------------------------------------------- #
    #  ⭐⭐ 프로펠러 «최대 시위 / 반경» (2026-08-16 추가 — 감사 I2)
    # ----------------------------------------------------------------------- #
    #  시위(chord) = 날 단면의 앞전~뒷전 길이 = 날의 «폭». 그 최댓값을 프롭 반경으로 나눈 값이
    #  `c_max/R` 이고, 날이 얼마나 통통한지를 정한다.
    #  ⛔ 지금까지 **8기종 전부 `drone_cad.CHORD_MAX_OVER_R = 0.25` 하나**를 썼다. 실측은
    #    0.177~0.273 으로 두 배 가까이 벌어지고 **프롭이 클수록 작아진다** — 그래서 기종마다
    #    오차 부호가 뒤집혔다(mini2 −5 % · matrice4e +31 % · mavic4pro +37 %).
    #  ⚠ **None 이면 예전 그대로**(0.25) — 전 기종 None 이라 기존 메쉬는 비트 단위로 동일하다.
    #  ⛔⛔ 이 필드만 채우고 시위 «분포» 를 그대로 두면 안 된다. 둘은 한 묶음이다
    #    (감사 §⑤ 15). 분포는 `build_propeller(..., blade_law='dji_mini2')` 로 고르고,
    #    그 판을 고르면 c_max/R 도 기종별로 **같이** 따라온다
    #    (`drone_cad.resolve_chord_max_over_r`). 이 필드는 그 자동 선택을 **덮어쓰는**
    #    수동 손잡이다 — 실험용으로만 쓸 것.
    prop_chord_max_over_r: float | None = None
    # ----------------------------------------------------------------------- #
    #  ⭐⭐ 기체별 «그 기체의 진짜 프로펠러» (2026-08-16 라운드)
    # ----------------------------------------------------------------------- #
    #  왜 생겼나: 위의 `prop_chord_max_over_r` 는 **한 수(통통한 정도)** 만 고칠 수 있다.
    #  그런데 지금까지 10기종이 c_max/R = 0.25 라는 상수 하나 **와** 3DR Solo 에서 베낀
    #  시위 분포 하나를 같이 쓰고 있었다 — 즉 «모든 드론에 같은 프로펠러를 달아 놓은» 상태다.
    #  기종 비교(=분류)가 그 위에 서 있으므로, 기체마다 **평면형까지** 따로 있어야 한다.
    #
    #  ⚠⚠ **전부 기본값 None 이고, 읽는 쪽은 `blade_law='per_airframe'` 하나뿐이다.**
    #     → 인자를 안 주면 메쉬는 비트 단위로 예전 그대로다. 값은 아래 `PROP_LAW_0816`
    #       표가 import 때 채워 넣는다(한 곳에서 감사할 수 있게 레지스트리 밖에 뒀다).
    #  용어 한 줄: **시위(chord)** = 날 단면의 앞전~뒷전 길이 = 날의 «폭».
    #             **평면형(planform)** = 위에서 본 날 윤곽 = 시위가 반경 따라 어떻게 변하나.
    prop_law_model: str | None = None        # 순정 프롭 **제품 모델명**(예: 'DJI 1157F')
    prop_law_cmax_over_r: float | None = None  # 최대시위/반경 — **설계 시위(원통단면 캘리퍼) 축**.
    #   ⛔ 사진에서 바로 나온 «투영 호폭» 이 아니다. 사진 유래 값은 다리 ×1.031 이 이미 곱해져 있다.
    prop_law_chord_rr: tuple | None = None   # 평면형 가로축 r/R
    prop_law_chord_frac: tuple | None = None #   〃   세로축 c(r)/c_max (최댓값이 정확히 1.0)
    prop_law_t_mm: float | None = None       # 날 두께[mm] — 시위가중 평균. **모르면 None**
    prop_law_tc_max: float | None = None     # 최대 두께비 t/c. **모르면 None**
    prop_law_grade: str | None = None        # 근거 등급 'A'(그 프롭의 공식 3D) / 'A-' / 'B'(그 프롭
    #   사진 계측) / 'B-' / 'C'(같은 계열에서 유추) / 'D'(대리 — 다른 프롭을 빌려 씀)
    prop_law_source: str | None = None       # 근거 파일 한 줄


#  DroneSpec 의 전체 필드 이름 — 필드를 추가하면 자동으로 따라온다(캐시 키가 낡지 않는다).
_SPEC_FIELDS = tuple(f.name for f in _dc_fields(DroneSpec))


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
             "Weight/prop/rotor count official. "
             "⭐ 2026-07-30 PHOTO-AUDIT ROUND (assets/photos/mini5pro/, 3 official product shots). "
             "LANDING GEAR EXISTS AND WAS MISSING: gear was 'none', but _1.png (head-on) shows a "
             "grey TWO-PRONGED leg hanging under EACH OF THE TWO FRONT motor pods, and the same "
             "photo's rear motor, enlarged, has none. gear='motor_legs' + gear_h_mm now builds them. "
             "*** LEG LENGTH RE-MEASURED 2026-07-31, 28.0 -> 31.0 mm. The old 28 mm came from a "
             "plan-view scale anchor (body width 79 mm) that this round replaced: the shell is "
             "70.4 mm wide, not 79. Re-measuring on _1.png with the scale anchored on the FRONT "
             "rotor pair (641.55 px = 227.6 mm from the official 380 mm props-included width) gives "
             "a projected leg of 85 px = 30.2 mm; removing the fore-aft component at the fitted "
             "elevation (~40 deg, read off the fore-aft hub offset 262.7 px) leaves 31.1 mm. "
             "Band +/-15% - DJI publishes no leg dimension. *** "
             "The legs are the aircraft's LOWEST point, so their absence also inflated "
             "frame_fit_scale's sz to 1.68 (the props-included 91 mm height was being met by "
             "stretching the shell vertically by 68%). "
             "Shell proportions, arm width and arm section are now photo-measured too - the numbers "
             "and their pixel provenance live in drone_cad._SHELL_SHAPE / _ARM_WIDTH / _ARM_SECTION. "
             "REFUTED HYPOTHESIS (kept on purpose): the plan shot _3.png measures the FRONT motor "
             "pair ~25% wider in track than the REAR pair, i.e. a trapezoid rather than our "
             "symmetric 56.3 deg rectangle. It was NOT adopted, because the two official "
             "props-included figures each independently imply a SYMMETRIC layout - 380 mm width "
             "gives 55.8 deg and 304 mm length gives 56.6 deg - which a trapezoid cannot satisfy "
             "at both ends. The photo reading is most likely perspective in a marketing render.",
        body_rgb=_GRAY_D, arm_style="body", gear="motor_legs", gear_h_mm=31.0, gimbal="front",
        accent_rgb=(0.95, 0.45, 0.05), body_frac=0.46, shape_source="spec_photo",
        rotor_deg=(56.33, 132.47, 227.53, 303.67), rotor_r_mm=(136.73, 112.26, 112.26, 136.73),
        body_lw=(1.42, 0.66), gimbal_style="single", cad_version="v2",
        # ⭐⭐ 2026-07-31 — **사다리꼴 채택**, 그리고 그 부산물로 프롭 디스크 겹침이 사라졌다.
        #   [옛 상태] 대칭 56.3° 한 원(r=137.5) → 앞뒤 모터간격 152.6 mm 인데 프롭이 152.4 라
        #     여유가 사실상 0(−0.8 mm 계산에 따라 음수)이라 rotor_z_mm 으로 피하고 있었다.
        #   [측정] 평면컷 `_3.png` 의 주황 프롭팁 8개 → 허브 (부분픽셀):
        #     앞 (174.36, 243.84)/(867.10, 243.20) · 뒤 (261.70, 690.41)/(779.12, 691.12) px.
        #   [원근 배제] 같은 사진의 팁-투-팁이 그 행의 배율이다 — 앞 434.0, 뒤 445.4 px → 배율비
        #     0.974. 좌우 span 비는 692.7/517.4 = **1.339**. 배율 2.6% 로 34% 를 만들 수 없다.
        #   [앞/뒤 판정] 정면컷 `_1.png` 에서 앞쌍 641.55 px, 뒷쌍 424.75 px (비 1.5104). 넓은 쪽이
        #     **앞**이면 원근계수 1.128(카메라 1.6 m)로 설명되고, 넓은 쪽이 뒤라면 2.02(카메라
        #     0.15 m)를 요구한다 ⇒ **넓은 쪽이 앞**. 두 사진이 서로를 지지한다.
        #   [축척은 공식값으로] 공식 언폴드(**프롭 포함**) 380 폭 · 304 길이 →
        #     앞 y = 380/2 − 76.2 = **113.8** · x = 304/2 − 76.2 = **75.8**.
        #     사진의 뒤/앞 span 비(배율보정 0.7278)를 걸어 뒤 y = **82.8**.
        #   ⛔ 옛 주석의 반증("380 은 55.8°, 304 는 56.6° 를 주므로 사다리꼴은 둘을 동시에 못
        #     만족한다")은 **틀린 추론**이었다: 그 두 공식값은 **앞 로터의 y 와 x** 만 묶는다(가장
        #     바깥에 닿는 것이 앞 프롭이므로). 뒤 로터의 y 에는 아무 제약도 걸지 않는다.
        #   [프롭 여유] 앞쌍 227.6−152.4 = +75.2 · 뒷쌍 165.6−152.4 = +13.2 ·
        #     같은쪽 앞뒤 √(151.6²+31.0²)−152.4 = **+2.3 mm** → 전부 양수(옛 배치는 0 이하).
        #   ⚠ 휠베이스는 그래서 274.6 → **248.3 mm** 가 된다. `diagonal_mm=275` 는 그대로 두되
        #     이제 **로터 위치를 정하지 않는다**(암 두께·모터 비례식의 스케일로만 남는다) —
        #     275 자체가 '대칭 가정 위에서 공식 외형으로부터 역산한 값' 이었기 때문이다.
        # ⭐⭐ 2026-08-07 게이트 ② (outputs/meshgate_mini5pro.json) — (−12,+2,+2,−12) → **(−7,+7,+7,−7)**.
        #   [부호는 근거가 있다] DJI 공식 **사용자 매뉴얼**(한국어, 2025-12-10판, md5
        #     b71b2c60f06d9c5d2c64a7c0818da508) p.11 암 펼치기 도면 · p.14 부위도: **뒤 암은 동체
        #     윗면**에 접혀 있다가 펴지고 **앞 암은 동체 밑면**에서 내려오며 펴진다. 경첩 높이가
        #     다르다는 것을 제조사 도면이 직접 보여준다 ⇒ 앞 로터가 뒤보다 **낮다**.
        #     공식 제품 렌더 2컷(_1 정면 · _2 전좌상)도 같은 것을 보여 준다(앞 암 뿌리 = 짐벌 블록
        #     높이, 뒤 암 뿌리 = 윗면 어깨).
        #   [크기 14 mm 는 **추정**이다 — 「조사 확인」 은 거짓이었다] 그 표현을 지운다. 값은
        #     2026-07-14 `3dd4794` 가 «프롭 152.4 > 앞뒤 모터간격 152 → 디스크가 겹치니 앞이
        #     12 mm 낮을 것» 이라는 **추론**으로 넣었고, 같은 날 우리 적대검증 문서
        #     (docs/drone_specs_2026.json)가 «어떤 소스에도 없다 … 자기 추론의 부산물을 관측으로
        #     승격» 이라고 이미 적발했다. 2026-07-31 사다리꼴 채택으로 그 전제(겹침)마저 사라졌다.
        #     DJI 는 Mini 5 Pro 의 CAD/3D 모델을 공개하지 않아 mm 를 잴 1차 출처가 없다.
        #   [왜 철회하지 않았나] 철회(네 로터를 한 평면)는 «층차가 없다» 고 **적극적으로 주장**하는
        #     것이고 그 주장은 위 매뉴얼 도면과 정면으로 어긋난다. 무출처인 크기를 지우려다
        #     출처 있는 부호까지 지우게 된다. 게다가 층차 0 이면 공식 높이 91 mm(프롭 포함)를
        #     맞추느라 기체를 세로로 47 % 늘려야 한다(sz 1.468) — 14 mm 면 18 %.
        #     실측 CAD 를 가진 DJI 두 대의 층차가 8.0~21.3 mm 이고 공식 높이는 26.9 mm 까지도
        #     허용하므로 14 는 그 안쪽의 **보수적인** 값이다. 근거 없는 값을 다른 근거 없는 값으로
        #     바꾸는 것은 개선이 아니라서 크기는 그대로 두고 **추정으로 강등**한다.
        #   [무엇을 바꿨나] 평균을 0 으로 되돌렸다. 옛 튜플은 평균이 **−5 mm** 였는데 그것은
        #     아무도 주장한 적이 없는 부작용이다(앞 프롭을 뒤 디스크 밑으로 밀어 넣다가 생겼다).
        #     층차(14 mm)는 그대로이고 메쉬 품질도 그대로다 — 주장만 하나 줄었다.
        #   ⚠ 이제 `drone_cad.ARM_Z_FOLLOWS_ROTOR` 에 mini5pro 가 있어 **암·모터 벨·다리가 이
        #     값을 따라간다**(예전에는 프로펠러만 따라가서 앞 프롭이 벨 속에 박혔다).
        #     다리가 앞 암에 붙어 있어 함께 7 mm 내려간다 — 지상고 계열 수치는 다시 봐야 한다.
        rotor_z_mm=(-7.0, +7.0, +7.0, -7.0),
        envelope_mm=(None, None, 91.0), env_props_included=True),   # ⚠ **높이만** 공식이고, **프롭 포함**값이다.
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
        max_speed_ms=25, hover_rpm=3600, max_rpm=8400, prop_pitch_in=5.8, rtk=False, release="released", confidence="high",
        note="Large consumer flagship (2025); front triple-camera gimbal (360° infinity). "
             "Weight/dimensions/propeller official (DJI part 1158F, 26.7x14.7 cm => 267 mm dia, 5.787 in pitch; "
             "prop_pitch_in=5.8 is therefore MANUFACTURER-PUBLISHED, not an estimate - corrected 2026-07-28). "
             "⭐ MAX RPM CORRECTED 2026-07-28: 6000 -> 8400. DJI Mavic 4 Pro User Manual v1.0 (2025.05) p.88, "
             "UAS Class C2 certification table: MTOM 1085 g / 83 dB / Maximum Propeller Speed 8400 RPM. "
             "⚠ max_rpm is a CLASS/FIRMWARE CEILING, not a measured full-throttle rpm - see the note in "
             "matrice4e. It does NOT touch flash_hz or f_tip (those use hover_rpm). "
             "⚠ diagonal was ESTIMATED (400 mm) and is geometrically INCONSISTENT with the official "
             "envelope: 328.7×390.5 mm cannot be spanned by a 400 mm motor diagonal. Fitting the frame "
             "to the official envelope implies a diagonal of 440.9 mm. The envelope (official) wins; "
             "diagonal_mm is kept only as an arm/motor thickness scale. "
             "⭐⭐ 2026-07-30 PHOTO-AUDIT ROUND - ROTOR LAYOUT CORRECTED 32 deg -> 51.4 deg and the "
             "L/W envelope forcing RELEASED. This is the same defect, and the same fix, as the "
             "matrice4e round of 2026-07-28. Forcing the frame bbox to 328.7 x 390.5 made "
             "frame_fit_scale squash x by 0.783 and stretch y by 1.397, which turns the rotor CIRCLE "
             "into an ELLIPSE: the coded 32 deg arms came out at an effective 48.1 deg, and every "
             "part of the airframe - shell, arms, motors, gimbal - was distorted by the same "
             "anisotropic factors (z was stretched 1.836 on top of that). The photos show it plainly: "
             "the mesh read as a fat round blob where mavic 4 pro_2.png shows a slim fore-aft body. "
             "SOLVING INSTEAD OF FORCING: put the rotors on the diagonal/2 = 220.5 mm circle and let "
             "the lateral span set the angle - 441*sin(a) + motor_dia 45.9 = official width 390.5 "
             "gives a = 51.40 deg. Cross-check from the OTHER official figure (length): "
             "441*cos(a) + 45.9 = 328.7 gives a = 50.1 deg, so both official dimensions agree on "
             "roughly 51 deg and neither is anywhere near 32 deg. Prop-disc clearance (house rule, "
             "must stay positive): front-to-front 441*sin(a) = 344.6 vs prop 267 -> +77.6 mm; "
             "front-to-rear 441*cos(a) = 275.1 vs 267 -> +8.1 mm. Both positive, and far safer than "
             "the +1.09 mm the matrice4e solution leaves. NOTE the released forcing means the frame "
             "length is now built, not asserted (~321 mm from the rotors + the gimbal's forward "
             "overhang, vs the official 328.7); as report02 already records, a 0% envelope match was "
             "a CONSTRAINT that frame_fit_scale manufactured, not evidence. "
             "LANDING GEAR EXISTS AND WAS MISSING: gear was 'none', but mavic 4 pro_2.png and _4.png "
             "show a two-pronged leg under each of the TWO FRONT motor pods (the rear pods, enlarged "
             "in _3.png, are smooth). gear='motor_legs' + gear_h_mm=48.0 (MEASURED off _2.png, "
             "+/-15%). Gimbal, shell proportions and arm width are photo-measured too - provenance "
             "in drone_cad._gimbal_hasselblad / _SHELL_SHAPE / _ARM_WIDTH.",
        body_rgb=_SILVER, arm_style="body", gear="motor_legs", gear_h_mm=48.0, gimbal="front",
        accent_rgb=None, body_frac=0.42, shape_source="spec_photo",
        rotor_deg=(51.4, 128.6, 231.4, 308.6), body_lw=(1.52, 0.62), gimbal_style="triple", cad_version="v2",
        envelope_mm=(None, None, 135.2)),        # DJI 공식(언폴드·프롭제외) 중 **높이만** 강제 — 위 note 참조,
    # 3) 엔터프라이즈 측량기 (RTK 탑재)
    "matrice4e": DroneSpec(
        key="matrice4e", name="DJI Matrice 4E",
        diagonal_mm=438.8, weight_g=1219,
        body_l_mm=307, body_w_mm=388, body_h_mm=150,
        prop_dia_mm=274, prop_blades=2, num_rotors=4,
        max_speed_ms=21, hover_rpm=3800, max_rpm=7500, prop_pitch_in=5.7, rtk=True, release="released", confidence="high",
        note="Prop diameter confirmed 274 mm by verification (292->274); DJI part 1157F (std) / 1154F (low-noise), "
             "M4 series manual p.101 lists 1154F as 27.4x13.7 cm. Onboard RTK. "
             "⭐ HOVER RPM RESOLVED 2026-07-28 (was 'UNRESOLVED'): the C_T method wins at essentially the coded "
             "value. NASA/US Army measured full-vehicle hover C_T = T/(rho A (Omega R)^2) = 0.0132 at 3500 rpm "
             "rising to 0.0142 at 7500 rpm for the DJI Phantom 3 + 9450 prop (Russell/Jung/Willink/Glasner, "
             "AHS Forum 72, 2016, Fig.38). The 1157F pitch ratio is 0.53 vs the 9450's 0.532, so the transfer needs "
             "no extrapolation. Solving T = 2.989 N/rotor at D = 0.274 m with C_T = 0.0140 gives 3789 rpm; the coded "
             "3800 is +0.3%. The old ARCHIVE range C_T 0.08-0.10 (Renard) was simply too low - the measured 9450 "
             "value converts to Renard C_T = 0.0140*pi^3/4 = 0.1085, i.e. exactly the 0.108 this code implies. "
             "Residual uncertainty band +/-5% (3613-3994 rpm => flash 120-133 Hz, f_tip 1169-1292 Hz @3.5 GHz). "
             "⚠ MAX RPM IS AMBIGUOUS AND IS NOT A PHYSICAL LIMIT: this code says 7500 RPM / 82 dB while "
             "docs/drone_specs_2026.json records 6130 RPM / 85 dB from User Manual v1.2 8.10 - both labelled "
             "'official C2 certification'. Unresolved. More importantly the declared maximum is a CLASS/FIRMWARE "
             "ceiling, not a loaded full-throttle speed: the DJI Mini 5 Pro manual declares 7800 RPM for its C0 "
             "model and 11200 RPM for its C1 model with the SAME airframe, SAME 6028F prop and SAME battery - "
             "43% apart. Therefore (n_max/n_hover)^2 is NOT a thrust ratio, which removes the entire 4740-5300 rpm "
             "branch of the old dispute and explains the 'anomalous' T/W(max)=3.9 flagged here previously.",
        body_rgb=_OFFWHT, arm_style="body", gear="feet", gimbal="front",
        accent_rgb=None, body_frac=0.42, shape_source="spec_photo",
        rotor_deg=(52.45, 131.53, 228.47, 307.55), rotor_r_mm=(228.77, 210.36, 210.36, 228.77),
        #  ⭐⭐ 2026-08-16 (B7 / meshfix F21) — 앞 로터가 뒤보다 **7.82 mm 높다**. 공식 STEP 의
        #    벨 솔리드 z 범위(앞 [−8.51, +8.03] · 뒤 [−16.33, −0.20])에서 두 밑동의 평균
        #    −12.42 를 drone_cad.MOTOR_BASE_Z 에 적고, 여기에는 그 평균에서의 **편차**만 적는다.
        #    ⚠ 이 값이 실제로 암·벨·다리까지 움직이려면 drone_cad.ARM_Z_FOLLOWS_ROTOR 에
        #      'matrice4e' 가 있어야 한다(둘은 짝이다). 없으면 프롭만 뜬다 — F21 의 경고.
        rotor_z_mm=(3.91, -3.91, -3.91, 3.91),
        body_lw=(1.08, 0.98), gimbal_style="sensor", cad_version="v2",
        envelope_mm=(None, None, 149.5),
        arm_od_mm=13.6, motor_dia_mm=27.0, motor_h_mm=16.3),   # ⭐ 공식 STEP 실측 — 아래 주석
        # ⭐⭐ 2026-08-04 형상 라운드 — 근거는 **DJI 공식 STEP CAD**
        #   `assets/meshes/reference/matrice4-M4T_v2.step` 의 모서리(1D) 실측이다
        #   (추출 방법·축척 검증·좌표 규약은 drone_cad._SHELL_SHAPE["matrice4e"] 주석).
        #   [암 굵기] `arm_od_mm = 13.6`. 암 솔리드(앞 107/97 · 뒤 86/91)를 **암 축에 수직**으로
        #     잘라 r = 100~200 mm 6단면을 재면 앞 폭 13.2~15.7 · 높이 11.7~13.2, 뒤 폭
        #     12.1~14.5 · 높이 14.2~16.5 → 앞뒤 평균 **폭 13.6 · 높이 13.7** = 사실상 원형이다.
        #     (상면투영으로 잰 값은 암 축 경사 때문에 실폭보다 크게 나온다.)
        #     단면 형상비 `_ARM_SECTION["matrice4e"] = (2.00, 1.00)` = 원형은 CAD 가 확인한다 —
        #     틀린 것은 지름뿐이었다.
        #   [모터 벨 높이] `motor_h_mm = 16.3`. 회전 캔(벨) 솔리드 104(앞) 16.53 · 94(뒤) 16.13 mm.
        #     None 이면 0.045·diag = 19.75 가 쓰인다.
        #   ⚠ arm_od 는 `drone_cad` 의 암 단면과 `drones._arm_motor_dims` 의 프롭 장착 높이에
        #     **둘 다** 들어가고, 다리 부착 z(z_arm)를 통해 GEAR_SPIKE_H 와 짝을 이룬다.
        #   ⚠ `motor_dia_mm = 27.0` 은 그대로 둔다 — CAD 벨 지름은 앞 25.6~27.5 · 뒤 26.8~27.8
        #     (평균 26.9)로 0.4 % 차, 측정 산포 안이다.
        # ⭐⭐ 2026-07-31 로터 배치 — **사다리꼴 채택, 매듭 해소**. (rotor_r_mm 신설)
        #   [측정] `assets/photos/matrice4e/matrice 4E_5.png`(상면)에서 **주황 프롭팁 8개**의
        #     무게중심을 찾고 2날 프롭의 두 팁의 중점을 허브로 삼았다(부분픽셀).
        #       앞좌 (180.62, 632.22) · 앞우 (753.12, 632.22) · 뒤좌 (218.21, 192.05) · 뒤우 (715.40, 191.96) px
        #     자기검사: 앞쌍 중심선 466.87, 뒷쌍 466.81 — **0.06 px** 일치. 앞뒤 행의 y 도 각각 동일.
        #   [원근 배제 — 이번엔 대조군이 있다] 같은 사진에서 프롭 **팁-투-팁 픽셀**이 곧 그 로터
        #     평면의 배율이다: 앞 407.13/407.16, 뒤 405.13/404.81 → 배율비 **1.0054**. 그런데
        #     좌우 span 픽셀비는 572.50/497.19 = **1.1514** 다. 배율 0.5% 로는 15% 를 만들 수 없다
        #     ⇒ 실물이 사다리꼴이다. (옛 주석의 "정투영이니 원근 아님" 을 정량 대조군으로 승격.)
        #   [축척] 공식 대각 438.8 mm ↔ 앞좌↔뒤우 692.66 px → **0.63351 mm/px**.
        #     ⚠ 대각을 앵커로 썼으므로 대각 일치는 **순환**이다. 독립 검사는 아래 둘이다.
        #   [결과] 앞 (x=+139.45, y=±181.35) · 뒤 (x=−139.45, y=±157.50) mm
        #     → rotor_deg/rotor_r_mm 이 그 좌표를 그대로 낸다(각 52.45°/131.53°, 반경 228.77/210.36).
        #   [독립 검사 2건] 모터벨 27 mm 로 두면
        #       폭 2·181.35 + 27 = 389.7  ↔ 공식 387.5  (**+0.57 %**)
        #       길이 2·139.45 + 27 = 305.9 ↔ 공식 307    (**−0.36 %**)
        #   ⛔ **2026-08-16 정정 — 위 두 수는 «로터 배치 검산» 이지 «프레임 치수» 가 아니다.**
        #     그대로 프레임 오차로 인용하면 틀린다. 실제로 지어진 프레임 bbox 를 재면:
        #       폭   **389.75 mm** ↔ 공식 387.5 = **+0.58 %**  ← 검산과 사실상 같다(우연이 아니라
        #                                                        폭은 로터가 정하기 때문)
        #       길이 **331.43 mm** ↔ 공식 307   = **+7.96 %**  ← 검산 305.9(−0.36 %)와 **다르다**
        #     이유: 길이 검산은 x 방향 끝을 «앞 모터 벨 앞끝»(139.45+13.5=152.95)으로 놓는데,
        #     실제 프레임은 그 앞으로 더 나간다(코·짐벌 쪽이 x 최대점을 만든다 — 165.7 mm).
        #     즉 로터 배치의 근거로는 여전히 유효하고, **프레임 길이 오차의 근거로는 못 쓴다.**
        #     ⇒ 이 기체의 프레임 길이는 지금 «공표 대비 +7.96 %» 로 적어야 한다(선언).
        #        (감사 docs/MESH_AUDIT_0816.md I10① · 적대검증에서 331.43 mm 로 재현)
        #     옛 대칭 X(51.2°)는 같은 검사에서 길이 320.4(**+4.4 %**)였고, 폭을 맞추려고
        #     모터벨을 **45.6 mm**(실물 27~32 의 1.7배)로 부풀려야만 성립했다 — 그 매듭이 풀렸다.
        #   [3번째 사진의 독립 확인] 정면컷 _1 에서도 같은 방법으로 허브를 재면 앞쌍 641.55 px,
        #     뒷쌍 424.75 px 로 비 **1.3106** 이다. 대칭 X 라면 이 비가 통째로 원근이어야 해서
        #     카메라 거리 1.04 m 를 요구하는데, 사다리꼴이면 1.1514 를 뺀 나머지 **1.138** 만
        #     원근이면 되고 그건 카메라 2.16 m 다 — 제품컷으로 후자가 자연스럽다.
        #   [프롭 여유(집안 규칙: 항상 양수)] 앞쌍 362.7−274 = **+88.7** · 뒷쌍 315.0−274 = **+41.0** ·
        #     같은쪽 앞뒤 √(278.89²+23.85²)−274 = **+5.9 mm**. 전부 양수 —
        #     옛 주석이 사다리꼴을 접었던 이유(−0.5 mm)는 그때의 뒷쌍 읽기(±155.2)에서 나온 것이고,
        #     팁-중점법으로 다시 재면 ±157.5 라 여유가 양수로 돌아선다.
        #   ⚠ 남는 것: 사진은 **제품 렌더**다. 렌더 자체가 실물과 다를 가능성은 사진으로 못 지운다.
        #     지운 것은 '원근 때문에 사다리꼴로 보였다' 는 대안설명뿐이다.
        # ⭐ 2026-07-28 로터 배치 정정 — 45° X → 51.2° (그 뒤 2026-07-31 사다리꼴로 대체됨),
        #   그리고 envelope 은 **높이만** 강제(이 결정은 그대로 유효하다).
        #   [문제] 예전 조합(45° X + L/W 를 307×387.5 로 강제)은 `frame_fit_scale` 이 로터 원을
        #     (0.8507, 1.0887) 로 **타원으로 찌그러뜨려** 두 가지를 동시에 만들고 있었다:
        #       · 인접 로터 간격 264.0 mm < 프롭 274.0 mm → **−10.04 mm 물리적 상호침투**(z차 0),
        #       · 실효 대각 428.7 mm → **−2.30% 오차**, 저장소 전 기종 **최악 치수오차**(mesh_verify worst_err_pct).
        #     즉 한 원인이 두 증상을 만들고 있었다.
        #   [진단] 공식 대각 438.8 과 공식 외형 307×387.5 는 **평면 4로터로 동시 만족 불가능**이다.
        #     둘 다 참이라면 코너 반경이 √(153.5²+193.75²)=247.2 → 대각 494.4 여서 438.8 과 어긋난다.
        #     ⇒ 실물 M4E 의 로터는 45° 가 아니고, 공식 L 은 로터가 아니라 **동체**가 정한다.
        #   [해] 로터를 대각/2 원 위에 두고 각을 푼다:
        #       · 좌우 span + 모터지름 = 공식 폭 387.5  →  a = 51.18°
        #       · 겹침 없는 상한 a ≤ arccos(프롭/대각) = 51.36°  →  해가 **유효**(여유 +1.09 mm)
        #       · 대각은 정의상 438.8 **정확**
        #     ⇒ rotor_deg = 51.2°. envelope 의 L/W 강제는 **해제**한다(mini5pro 와 같은 처리) —
        #       report02 가 이미 적어둔 대로 0% 외형일치는 `frame_fit_scale` 이 만든 **제약이지 증거가 아니고**,
        #       프롭 상호침투는 **물리적 불가능**이라 후자를 우선한다.
        #   ⚠ 여유 +1.09 mm 는 빠듯하다 — 실물도 그렇다(Mini 5 Pro 는 아예 겹쳐서 rotor_z 로 피한다).
    # 4) 대형 산업용 옥토콥터 (8암) — 단종, 카본 프레임
    "s1000plus": DroneSpec(
        key="s1000plus", name="DJI S1000+",
        diagonal_mm=1045, weight_g=9500,
        body_l_mm=1016, body_w_mm=1016, body_h_mm=380,
        prop_dia_mm=381, prop_blades=2, num_rotors=8,
        max_speed_ms=None, hover_rpm=4467, max_rpm=5600, prop_pitch_in=5.2, rtk=False, release="discontinued", confidence="high",
        note="Octocopter: 8 arms, 1 rotor per arm (non-coaxial). Carbon frame, retractable landing gear, belly gimbal. "
             "4400 g is the AIRFRAME weight; recommended takeoff weight 6.0-11.0 kg. "
             "⭐ HOVER RPM CORRECTED 2026-07-28: 3600 -> 4467. The old value implied C_T = 0.01617 "
             "(T/rho/A/(Omega R)^2 at TOW 9.5 kg over 8 rotors), which EXCEEDS the highest value NASA/US Army "
             "ever measured on a small multirotor (0.0142, the high-pitch DJI 9450; Russell et al., AHS Forum 72, "
             "2016). The 1552 prop is 15x5.2 in, pitch ratio 0.347 - LOWER than any prop in that campaign - so its "
             "C_T should sit BELOW 0.0105, not above 0.0142. C_T 0.0085-0.0140 gives 3868-4996 rpm; central 4467. "
             "Independent cross-check: DJI publishes max thrust 2.5 kg per arm, and hover/max = sqrt(11.645/24.5) "
             "= 0.689 regardless of C_T, so the old (3600 hover / 5600 max) pair implied 2.87 kg per arm = 15% above "
             "DJI's own figure. Micro-Doppler consequence: flash 120.0 -> 148.9 Hz, f_tip 1620 -> 2010 Hz @3.5 GHz.",
        body_rgb=_BLACK, arm_style="carbon", gear="tall", gimbal="belly",
        accent_rgb=(0.85, 0.10, 0.10), body_frac=0.30, shape_source="spec_photo",
        body_lw=(1.0, 1.0), gimbal_style="belly", cad_version="v2",
        arm_od_mm=25.0, motor_dia_mm=52.0, motor_h_mm=30.0,
        #  ⭐ 2026-07-30 외형감사에서 추가. 이 셋이 **없을 때** `_arm_motor_dims` 는 대각비례
        #    (0.045·1045 = 47 mm)로 되돌아가 prop_z = 76.5 mm 를 내놓았는데, drone_cad 의
        #    s1000plus 분기는 모터 벨을 z=21..53 mm 에 그리고 있었다 → **프롭이 벨 위 23 mm 허공에
        #    떠 있었다**(에러 없음). 이제 벨(12.5~42.5)과 프롭(48.5)이 같은 수치에서 나온다.
        #    arm_od 25.0 = MEASURED(탑뷰 사진 24.8, 스케일 앵커는 note 참조) · 널리 알려진 25 mm 튜브와 일치.
        #    motor 52 × 30 = DERIVED(DJI 4114 급 아웃러너 벨).
        envelope_mm=(1016.0, 1016.0, 380.0)),   # DJI 공식 — 센터프레임 337.5mm, 암 386mm, 랜딩기어 460x511x305,
    # 5) 고정암 쿼드 (클래식, 흰색 셸)
    "phantom4": DroneSpec(
        key="phantom4", name="DJI Phantom 4",
        diagonal_mm=350, weight_g=1380,
        body_l_mm=289.5, body_w_mm=289.5, body_h_mm=196,
        prop_dia_mm=240, prop_blades=2, num_rotors=4,
        max_speed_ms=20, hover_rpm=5500, max_rpm=8500, prop_pitch_in=5.0, rtk=False, release="released", confidence="high",
        note="Fixed (non-folding) arms, one-piece white shell + integrated landing legs. Classic Phantom shape. "
             "Propeller is DJI part 9450; DJI's own propeller-dimensions table gives 24 x 12.7 cm, hence "
             "prop_dia_mm=240. (The part number literally reads 9.4 in = 238.8 mm, 0.5% smaller - we follow "
             "DJI's published table, and the 0.5% is inside the mesh tolerance.) "
             "⭐⭐ 2026-08-16 L/W ENVELOPE FORCING RELEASED (audit finding B6). This was the last "
             "airframe in the repo still forcing all three axes; mavic4pro (2026-07-30) and "
             "matrice4e (2026-07-28) had already been released for the same defect. "
             "WHAT WAS WRONG: forcing the frame bbox to 289.5 x 289.5 made frame_fit_scale "
             "multiply the whole airframe in-plane by 1.019771, and that factor rides straight "
             "through to the MOTOR POSITIONS - the wheelbase came out 356.92 mm against DJI's "
             "published 350 mm diagonal (+1.98%). Two official figures were fighting and the "
             "scale factor silently picked the loser: 350 mm is the DIAGONAL (motor to motor), "
             "289.5 mm is the BODY square, and our built frame cannot satisfy both because the "
             "289.5 square is set by the shell and legs, not by the motors. "
             "THE FIX: release L/W, keep HEIGHT forced (196 mm), exactly the house rule the other "
             "eight airframes follow. Fixed arms put the rotors at 45/135/225/315 deg by "
             "construction, so nothing has to be re-solved - the rotor radius is diagonal/2 = "
             "175 mm and the wheelbase lands on 350.000 mm (error 0.000%). "
             "WHAT IT COSTS (declared, not hidden): the frame L/W is now BUILT, not asserted - it "
             "measures 283.89 mm against the official 289.5 (-1.94%). As report02 already records, "
             "a 0% envelope match was a CONSTRAINT that frame_fit_scale manufactured, not evidence. "
             "PROP CLEARANCE (house rule, must stay positive): adjacent rotors sit 247.49 mm apart "
             "against a 240 mm prop -> +7.49 mm, still positive (it was +12.38 mm inflated). "
             "Numbers and the sigma re-measure: outputs/mesh_apply_caps_envelope_0816.json",
        body_rgb=_WHITE, arm_style="body", fixed_arm=True, gear="legs", gimbal="front",
        accent_rgb=None, body_frac=0.52, shape_source="spec_photo",
        rotor_deg=(45, 135, 225, 315), body_lw=(1.06, 1.0), gimbal_style="recessed", cad_version="v2",
        envelope_mm=(None, None, 196.0)),       # ⭐ 높이만 강제(2026-08-16, B6) — 위 note 참조.
                                                #   공식 289.5 × 289.5 × 196 = Quick Start Guide v1.2(프롭 제외)
    # ----------------------------------------------------------------------- #
    #  비-DJI 2기종 (2026-07-30 추가). 제원은 docs/RESUME_0729.md §5 가 단일 출처이고
    #  등급(VERIFIED / MEASURED / DERIVED / UNKNOWN)은 아래 note 에 그대로 옮겼다 — **올리지 않았다.**
    # ----------------------------------------------------------------------- #
    # 6) 헥사콥터 (2016) — 이 저장소가 **실물 3D CAD 를 가진** 유일한 표적
    "typhoonh480": DroneSpec(
        key="typhoonh480", name="Yuneec Typhoon H (H480)",
        diagonal_mm=480, weight_g=1950,
        body_l_mm=457, body_w_mm=520, body_h_mm=310,
        prop_dia_mm=230.2, prop_blades=2, num_rotors=6,
        max_speed_ms=13.5, hover_rpm=5600, max_rpm=None, prop_pitch_in=6.0,
        rtk=False, release="discontinued", confidence="high",
        note="Hexacopter, and the only target in this repo whose REAL 3D CAD we hold "
             "(ethz-asl/rotors_simulator, Apache-2.0 - assets/meshes/reference/SOURCES.md). "
             "VARIANT: this is the H480 (2016), NOT the Typhoon H Plus (2018). Five independent "
             "checks agree: upstream directory typhoon_h480, cgo3_* mesh names, CAD diagonal 485.4 vs "
             "H Plus 520, body bbox 455x520 vs H Plus 556x485, prop 230 vs H Plus 248. "
             "diagonal_mm 480 VERIFIED (user manual V1.2 p.3); our own CAD measures 485.4 (+1.1%). "
             "weight_g 1950 VERIFIED and self-consistent (1695 g airframe+battery + 255 g CGO3+). "
             "body L/W/H 457/520/310 VERIFIED - but Yuneec PUBLISHES WIDTH FIRST ('520 x 457 x 310 mm') "
             "and the real CAD confirms 520 = LEFT-RIGHT (body STL bbox 455.41 x 520.35 x 158.25 mm), "
             "so the published triple must be RE-ORDERED before it lands in (l, w, h). Do not swap it "
             "back. Those official L/W exclude propellers (the CAD bbox reproduces them to 0.4%). "
             "prop_dia_mm 230.2 MEASURED from that CAD (our ledger 230.098 mm agrees to 0.1 mm, and "
             "480 + 230 = 710 also reproduces Yuneec's published 711 mm tip envelope). "
             "prop_pitch_in 6.0 DERIVED - Yuneec never published a pitch; the CAD ensemble gives "
             "5.84 +/- 0.20. rotor_deg 30/90/150/210/270/330 VERIFIED (exact extraction from the "
             "PX4/RotorS SDF, rotor radius 242.8 mm). "
             "hover_rpm 5600 DERIVED, band +/-4.5% (PX4 motorConstant implies 5831 rpm, the C_T method "
             "5544-5753). Like all five DJI entries this is a HARDCODED LITERAL, not solved from thrust "
             "balance - changing weight_g or prop_dia_mm does NOT move it (see the field note above). "
             "Consistency check done at registration: 5600 rpm implies full-vehicle "
             "C_T = T/(rho A (Omega R)^2) = 0.0137, and this prop's pitch ratio 6.0/9.06 = 0.662 is "
             "HIGHER than the DJI 9450's 0.532 whose measured C_T is 0.0140 - so 0.0137 is where a "
             "high-pitch prop belongs, no anomaly. "
             "max_rpm None = UNKNOWN: Yuneec publishes no certification/firmware propeller-speed "
             "ceiling. An electrical no-load figure (KV x pack voltage) must NOT be substituted - "
             "max_rpm here means a CLASS/FIRMWARE ceiling (see the mavic4pro and matrice4e notes) and "
             "mixing the two is exactly the error those notes warn about. "
             "max_speed_ms 13.5 VERIFIED (Angle mode). "
             "*** arm_style IS THE SINGLE LARGEST UNKNOWN ON THIS AIRFRAME. Yuneec never stated the arm "
             "material and we have no teardown. carbon vs plastic is |Gamma| 0.90 vs 0.28 = 10.14 dB on "
             "the arms - the biggest single-parameter RCS lever here. We DEFAULT TO PLASTIC "
             "(arm_style='body', so the arms join the plastic shell group). CARBON IS A LABELLED "
             "SENSITIVITY CASE, not a second spec: run it by overriding arm_style='carbon' and report "
             "both numbers. *** "
             "arm/motor PART dimensions are UNKNOWN (unpublished, and not extractable from one fused "
             "body STL), so the mesh falls back to the diagonal-proportional rule - arm root half-width "
             "0.055*diag = 26.4 mm (a 52.8 mm wide profile) and a motor bell 0.104*diag = 49.9 mm in "
             "diameter. *** CORRECTED 2026-08-16 (audit I10-2): the frame bbox this actually builds is "
             "452.17 x 517.00 mm, i.e. -1.06% / -0.58% versus the official 457 x 520 - UNDER, not over. "
             "The old note said '465.6 x 529.9 mm, +1.9%', which is stale in magnitude AND in sign; do "
             "not quote it. The clearance argument below still holds because it is about the official "
             "envelope, not about our bbox. *** "
             "the official width leaves only 520 - 2*240 = 40.0 mm for the bell on "
             "our 480 mm diagonal (34.4 mm if the CAD's measured 242.8 mm rotor radius is used instead). "
             "arm_od_mm / motor_dia_mm / motor_h_mm exist to fix this the moment a graded figure lands. "
             "envelope_mm forces HEIGHT ONLY (310 mm), like mini5pro and matrice4e: forcing L/W too "
             "would shrink the effective motor diagonal below the VERIFIED 480 mm and eat the "
             "adjacent-prop clearance, and the 2026-07-28 matrice4e round settled that the diagonal and "
             "prop non-interpenetration beat a 0% envelope match. "
             "gear 'tall' = retractable legs VERIFIED, but the leg LENGTH is not published, so it stays "
             "on the shell convention 0.30*body_h (DERIVED) and the official 310 mm total height is "
             "reached by the envelope fit. gimbal = CGO3+ front-hanging single lens VERIFIED (no "
             "fisheye array, no LiDAR - a 2016 platform); the gimbal box is MEASURED from "
             "cgo3_camera_remeshed_v1.stl (69.30 x 55.00 x 72.31 mm).",
        body_rgb=_BLACK, arm_style="body", gear="tall", gimbal="front",
        accent_rgb=None, body_frac=0.42, shape_source="spec_photo",
        rotor_deg=(30, 90, 150, 210, 270, 330), body_lw=(1.15, 0.85),
        gimbal_style="single", cad_version="v2",
        arm_od_mm=12.0, motor_dia_mm=35.4, motor_h_mm=24.5,
        #  ⭐ 2026-07-30 외형감사. 앞의 note 가 "arm_od_mm / motor_dia_mm / motor_h_mm 는
        #    graded 수치가 나오는 순간 여기를 고치려고 있다" 고 적어둔 그 순간이 왔다.
        #    arm_od 12.00 = MEASURED(실물 CAD, 암 3방향 12.002/12.005/12.005 ±0.004).
        #      ⚠ 다리 스트럿도 정확히 12.00 이다 — 파라메트릭 제도의 흔적일 수 있어
        #        reference/SOURCES.md 가 '12 mm 급'으로 취급하라고 기록해 두었다. 유효숫자 4자리로 읽지 말 것.
        #    motor_dia 35.4 = MEASURED(모터 포드 폭 35.4 × 높이 47.8, s=225~262).
        #    motor_h 24.5 = **DERIVED, 그리고 이 값의 목적은 벨 높이가 아니라 `prop_z` 다**:
        #      prop_z = motor_h + arm_od/2 + 6 = 36.5 mm 여야 실물 로터면(base_link up 82.22)이
        #      우리 z=0(= 모터 스테이션 암 축, base_link up 45.7)에서 정확히 +36.5 mm 에 온다.
        #      이 셋을 안 주면 대각비례로 되돌아가 prop_z = 26.4 mm 가 되고 프롭이 포드 속에 박힌다.
        envelope_mm=(None, None, 310.0)),
        # ⚠ 라이선스: 이 기종의 형상 근거는 Apache-2.0 CAD 다(SOURCES.md) — 표적 모델이 배포되면
        #   의무가 따라온다. 우리 메쉬는 그 CAD 를 복사하지 않고 공표 제원에서 파라메트릭으로 짓는다.
    # 7) 열린 프레임 개발용 쿼드 — 셸이 아예 없고 카메라도 없다(우리 첫 open-frame 표적)
    "x500v2": DroneSpec(
        key="x500v2", name="Holybro X500 V2",
        diagonal_mm=500, weight_g=1650,
        body_l_mm=143.72, body_w_mm=143.72, body_h_mm=32,
        prop_dia_mm=254.0, prop_blades=2, num_rotors=4,
        max_speed_ms=None, hover_rpm=5450, max_rpm=None, prop_pitch_in=4.5,
        rtk=False, release="released", confidence="medium",
        note="Development frame: our first OPEN-FRAME target - no moulded shell at all "
             "(body_style='plate_stack', shell_groups=()) and no camera (gimbal_style='none'). "
             "diagonal_mm 500 VERIFIED (docs.holybro.com X500 V2, 'Wheelbase: 500mm'). "
             "plate 143.72 mm across flats MEASURED off the manufacturer STEP by edge sampling "
             "(the straight flats sit at x = 71.86 and the LINE runs (71.860, +/-48.906), length "
             "97.812), against the published 144 - the published figure is the rounded one, "
             "-0.19 %. plate thickness 2.000 and gap 28.000 VERIFIED, reproduced exactly; "
             "body_h_mm 32 is therefore DERIVED (2+28+2), not a published overall height. "
             "prop 254.0 mm / 4.5 in VERIFIED - the kit ships 1045 propellers (10 x 4.5 in). The 1345 "
             "prop in the community CAD is NOT the X500 prop (13 in nominal, 346.9 mm measured); "
             "assets/meshes/reference/SOURCES.md records that correction - do not re-adopt it. "
             "arm_od_mm 16.0 VERIFIED (16 mm carbon tube; Holybro's own STEP has the clamp bores at "
             "15.90 root / 16.00 tip, and its tube solid is drawn 15.4 = clearance, not the real size). "
             "Our arm mesh is SOLID, not hollow - reasoning and price (Gazebo mass "
             "DISTRIBUTION, not total mass) in drone_cad._arm_tube. "
             "gear 'tall' 215 mm and tubes 16/14 (legs) / 10/8 (skids) VERIFIED. "
             "*** gear_splay_deg CORRECTED 2026-07-30, 20.0 -> 17.59 VERIFIED. The old 20.0 was "
             "carried over from NXP-HGD-CF.dae, which is a DIFFERENT AIRCRAFT (see the last paragraph); "
             "17.59 deg is read off the leg cylinder axes in Holybro's own STEP. The leg count, leg "
             "positions and skid length are no longer DERIVED ratios either - see drone_cad.X500V2, "
             "which carries the whole measured table (leg top |y| 56.78, skid track 239.91, skid length "
             "248.0, EVA foam sleeves 19.0 OD x 93.0, four of them). The mesh used to build FOUR legs; "
             "the real aircraft has TWO (BOM: GUAN-CHENG x2). *** "
             "*** motor_dia_mm / motor_h_mm are both MEASURED off manufacturer CAD, replacing the "
             "diagonal-proportional fallback that this note used to warn about (52.0 mm dia x 24.0 mm, "
             "~1.9x a real 22xx bell, overstating motor projected area by ~3.5x). Holybro's "
             "AIR2216II_Motor_3D.STEP - the CURRENT kit motor - puts the r = 13.85 (OD 27.70) can "
             "circles at axial 11.0 and 39.5 only, i.e. a 28.5 mm can, standing on a 24.7 mm OD base "
             "disc at axial 9.5. The frame STEP corroborates the height independently on its own "
             "(earlier-configuration) DJ-2216-KV880: can from y 23.5 to 52.5 = 29.0 mm, two sources "
             "agreeing to 0.5 mm. In our frame the can sits 1.5 mm above the carbon plate top, "
             "z 7.5..36.0, with the base disc at 6.0..7.5. The mesh builds both stages. "
             "*** THE BASE-FLANGE DIAMETER IS A CONFIGURATION CHOICE, NOT A MEASUREMENT BAND: the "
             "frame STEP's DJ-2216 carries lugs of OD 34..36.6 in y 22..27, i.e. a base WIDER than "
             "its can, which the AIR2216II does not have. We follow the AIR2216II because that is "
             "what the kit ships; if that is falsified, only motor_base_od_mm reverts. *** "
             "weight_g 1650 DERIVED - Holybro does not publish a TOW, this is a PX4 Full-Kit build-up "
             "(610 g frame + electronics + 4S 5000 mAh pack). "
             "hover_rpm 5450 DERIVED. Working, using the same C_T anchors as the matrice4e and "
             "s1000plus notes: T_hover = m g / N = 1.650 * 9.80665 / 4 = 4.045 N per rotor, D = 0.254 m, "
             "R = 0.127 m, A = pi R^2. The 1045's pitch ratio 4.5/10 = 0.450 sits BETWEEN the two "
             "measured anchors - the DJI 9450 (ratio 0.532, NASA/US Army full-vehicle hover "
             "C_T = T/(rho A (Omega R)^2) = 0.0140; Russell/Jung/Willink/Glasner, AHS Forum 72, 2016) "
             "and the DJI 1552 (ratio 0.347, bounded BELOW 0.0105 in the s1000plus note). Linear "
             "interpolation in pitch ratio gives C_T = 0.01245, and T = C_T rho A (Omega R)^2 then "
             "gives 5440 rpm -> adopted 5450 (rounded to the nearest 50; the implied C_T is then "
             "0.01240). Band: C_T 0.0105-0.0140 spans 5130-5924 rpm, i.e. +8.7%/-5.9% about the adopted "
             "value. CROSS-CHECK, NOT ADOPTED: the PX4/RotorS iris default "
             "motorConstant k_T = 8.54858e-06 N s^2/rad^2 (recorded in docs/drone_specs_2026.json) with "
             "T = k_T omega^2 gives 6569 rpm, +20.7% above the C_T central value. iris is the same class "
             "(10-inch quad, ~1.5 kg) but that constant is a SIMULATOR DEFAULT, not a measurement, so it "
             "bounds the estimate instead of setting it. Like every entry here hover_rpm is a HARDCODED "
             "LITERAL (see the field note above) - it does not re-solve if weight_g or prop_dia_mm "
             "change, and since weight_g is itself DERIVED this rpm inherits that grade. "
             "max_rpm None = UNKNOWN - a development frame carries no C-class certification or firmware "
             "ceiling, and an electrical no-load figure is a different quantity (matrice4e note). "
             "max_speed_ms None = UNKNOWN (airframe kit; speed depends on the build). "
             "SHAPE SOURCE: the manufacturer's own STEP assembly is in-repo at "
             "assets/meshes/reference/x500v2-frame.step (57 parts / 244 placed instances). The shape "
             "constants live in drone_cad.X500V2 and are EDGE-BASED (1D): EDGE_CURVE -> VERTEX_POINT "
             "plus same-sense circular-arc sampling at 0.25 mm arc length, with cylinder diameters read "
             "off CYLINDRICAL_SURFACE radii. A whole-point-cloud reading of a STEP file is NOT "
             "equivalent: its CARTESIAN_POINTs mix circle CENTRES, untrimmed-LINE parametric endpoints "
             "and B-spline control points, all of which can lie outside the solid, so point-cloud boxes "
             "run large and point-cloud centroids get pulled toward asymmetric features. "
             "The CAD reproduces NINE published values: plate 143.72 vs 144 (-0.19 %), thickness 2.000, "
             "gap 28.000, WHEELBASE 500.28 vs 500 (+0.06 %), gear 215.28 vs 215, arm-tube clamp bore "
             "16.00, skid 10.0, leg 16.0, payload rail 250.0 - worst 0.19 %. drone_cad.X500V2 is the "
             "table the mesh builds from, and it is the reason this airframe has an octagonal (45 deg "
             "chamfered) plate, carbon teardrop motor mount plates, nylon corner/tip clamps, two legs "
             "with foam sleeves, payload rails, a slung battery tray on two pylon side-plates, a GPS "
             "mast with its tray and an optical-flow cover. diagonal_mm stays at the published 500 (it "
             "only scales arm/motor fallbacks that this airframe no longer uses); the motor ring itself "
             "is built at the measured 250.141 mm radius, i.e. the vertical-axis CIRCLE centres of all "
             "eight motor instances land on (+/-176.876, +/-176.876) at exactly +/-45.000 deg. "
             "*** DECLARED, NOT APPLIED: rotor_r_mm is left unset, so the PROPELLERS are still placed "
             "at diagonal_mm/2 = 250.0 while the motors sit at 250.141 - a 0.141 mm offset. Setting "
             "rotor_r_mm = 250.141 would close it, at the cost of moving the reported "
             "wheelbase_opposite_mm / diagonal_effective_mm from 500.0 to 500.28 wherever a table "
             "expects 500.0. Not worth 0.141 mm inside a geometry-only round. *** "
             "NOT a BOM or geometry source: assets/meshes/reference/NXP-HGD-CF.dae is the ReadytoSky "
             "LJI X4 500 from the NXP HoverGames kit - proven by the FMUK66 flight-controller mesh "
             "inside it - and NOT a Holybro X500. Cousin-class LAYOUT reference only; every number "
             "above is a published value, not a measurement off that DAE.",
        body_rgb=_BLACK, arm_style="carbon", gear="tall", gimbal="none",
        accent_rgb=None, body_frac=0.28744,      # = 143.72/500 → _drone_dims 의 동체치수 = 실제 판
        shape_source="manufacturer_cad",         # ⭐ 저장소에서 유일 — 제조사 STEP 실측(위 note 의 SHAPE SOURCE 절)
        body_lw=(1.0, 1.0), gimbal_style="none", cad_version="v2",
        envelope_mm=None,                        # Holybro 는 전체 외형(L×W×H)을 공표하지 않는다 → 맞출 대상이 없다
        #  ⭐ 2026-08-04 — 판 맞변거리 144.0 → **143.72** (모서리 실측). body_l/w_mm 과 반드시
        #    같아야 한다(build_frame_cad 가 ValueError 로 막는다). body_frac 도 함께 따라간다.
        body_style="plate_stack", plate_mm=(143.72, 143.72, 2.0, 28.0, 2.0),
        arm_shape="tube", arm_od_mm=16.0,
        motor_dia_mm=27.7, motor_h_mm=28.5,      # ⭐ 제조사 CAD 실측 — 위 note 의 모터 절 참조
        gear_h_mm=215.0, gear_tube_mm=(16.0, 10.0), gear_splay_deg=17.59,
        shell_groups=()),                        # ⭐ 셸이 없다 — body·canopy 그룹이 존재하지 않는다
    # ----------------------------------------------------------------------- #
    # 8) 검증 표적 (2026-08-03 추가) — 공개 실측 σ 가 존재하는 유일한 기체.
    #    제원의 단일 출처는 `outputs/p3_specs.json` 이고, 등급(VERIFIED / MEASURED /
    #    DERIVED / UNKNOWN)은 그 파일이 적은 대로 아래 note 에 **올리지 않고** 옮겼다.
    # ----------------------------------------------------------------------- #
    "phantom3": DroneSpec(
        key="phantom3", name="DJI Phantom 3 Professional",
        diagonal_mm=350.0, weight_g=1280.0,
        body_l_mm=289.5, body_w_mm=289.0, body_h_mm=185.0,
        prop_dia_mm=240.0, prop_blades=2, num_rotors=4,
        max_speed_ms=16.0, hover_rpm=5100.0, max_rpm=None, prop_pitch_in=5.0,
        rtk=False, release="discontinued", confidence="high",
        note="Fixed-arm quad, one-piece white plastic shell, bolt-on arch landing legs, exposed "
             "3-axis gimbal hung under the belly on a vibration-damping plate. Spec provenance is "
             "outputs/p3_specs.json (manufacturer documents + a pixel audit of DJI's own 4-view "
             "line art); grades are copied from there, not upgraded. "
             "VARIANT: the Professional (WM331). It does not matter geometrically - DJI sells ONE "
             "two-piece shell part for Pro/Adv/SE/Standard, all variants share the 350 mm motor "
             "diagonal, the 9450 propeller, the PH3 battery and the SAME published envelope "
             "289.5 x 289 x 185 mm (the Standard Quick Start Guide V1.0 and the Professional Quick "
             "Start Guide V1.2 carry the identical dimension diagram). Only mass differs "
             "(1216 / 1236 / 1280 g) and 1280 g is the modal value; the Professional also carries "
             "the belly Vision Positioning System, so choosing it is the more-scatterer option. "
             "diagonal_mm 350 DERIVED and exact: DJI's archived spec pages publish 'Diagonal Size "
             "(Including Propellers) 590 mm' and the E305 table gives the 9450 as 24 x 12.7 cm, so "
             "590 - 240 = 350 mm; third-party datasheets state 350 mm props-excluded directly. "
             "weight_g 1280 VERIFIED (User Manual v1.8 Appendix, battery and propellers included). "
             "prop 240 mm / 5.0 in / 2 blades VERIFIED from DJI's own E305 propulsion table - the "
             "SAME 9450 part number as the phantom4 entry, and the same 0.5% part-number/table "
             "discrepancy that entry already documents. "
             "body_l/w/h 289.5 / 289.0 / 185.0 VERIFIED - DJI's dimension diagram, propellers "
             "EXCLUDED, height measured from the MOTOR TOP down to the feet (proved by the pixel "
             "audit: taking the prop tops instead gives 206.4 mm, +11.6%). "
             "*** HEIGHT DISCREPANCY, FLAGGED NOT RESOLVED: the measurement literature that makes "
             "this airframe interesting quotes '35 cm x 20 cm'. The 35 cm is the 350 mm motor "
             "diagonal exactly; the 20 cm is +8.1% over DJI's published 185 mm and is most likely "
             "a rounding or a props-fitted height. THIS ENTRY USES DJI'S 185 mm, i.e. the "
             "manufacturer value, not the paper's. Anyone comparing against that literature must "
             "know the model is 7.5% shorter than the number printed there. *** "
             "rotor_deg 45/135/225/315 DERIVED and forced by the two official plan dimensions: "
             "350 cos(a) + p = 289.5 and 350 sin(a) + p = 289.0 subtract to a = 44.94 deg, i.e. a "
             "symmetric X within 0.06 deg. Implied outermost overhang p = 41.5 mm at the rotor "
             "station. Prop clearance (house rule, must stay positive): adjacent motors "
             "350/sqrt(2) = 247.49 vs prop 240 -> +7.49 mm; opposite 350 vs 240 -> +110 mm. "
             "rotor_r_mm / rotor_z_mm None = UNKNOWN: no plan-view photograph exists to test a "
             "trapezoid, and one circle at diagonal/2 satisfies both official plan figures. "
             "hover_rpm 5100 DERIVED, band 5030-5210 (C_T 0.0132-0.0142). This is the ONE airframe "
             "in the registry where the NASA/US Army full-vehicle hover C_T anchor was measured on "
             "THIS aircraft with THIS propeller ('DJI Phantom 3 + 9450'; Russell/Jung/Willink/"
             "Glasner, AHS Forum 72, 2016, Fig.38) - every other entry transfers that number across "
             "pitch ratios. Self-consistency: our phantom4 uses 5500 on the same prop at 1380 g, and "
             "n ~ sqrt(m) implies 5296 for the P4 from this value, so the two agree to +3.8%. Like "
             "every hover_rpm here it is a HARDCODED LITERAL (see the field note) and it does not "
             "enter the static mesh at all. "
             "max_rpm None = UNKNOWN - a 2015 product predating C-class certification; an "
             "electrical no-load figure (KV x pack voltage) is a different quantity and must not be "
             "substituted (see the matrice4e note). "
             "gear_h_mm 120.5 MEASURED (+/-8%), belly to foot, off the User Manual v1.8 p.8 front "
             "elevation at 0.39320 mm/px. The scale is anchored on the props-excluded WIDTH 289.0 mm "
             "and then reproduces the published HEIGHT to -0.32% (184.4 vs 185.0), which is an "
             "independent check that the drawing is orthographic. The height decomposes "
             "self-consistently as shell 63.9 + legs 120.5 = 184.4 mm. Compared with our phantom4 "
             "(shell 83, legs 113 on 196 mm) the Phantom 3 has a ~23% THINNER shell and ~7% LONGER "
             "legs - the two airframes are interchangeable in rotor layout only, not in silhouette. "
             "arm_style 'body' VERIFIED, and it is NOT a judgement call here: the arms are moulded "
             "into the shell (one DJI part number, 'Shell incl. Top & Bottom Covers', covers arms "
             "and body), so they join the plastic group. Had they been carbon this would be "
             "|Gamma| 0.90 vs 0.28 = 10.1 dB on the arms. "
             "envelope_mm forces HEIGHT ONLY (185 mm), the house rule shared with mini5pro / "
             "mavic4pro / matrice4e / typhoonh480. L/W would in fact be nearly self-consistent here "
             "(the 45 deg solve reproduces them to 0.06 deg) but forcing three axes is what turns "
             "frame_fit_scale into an anisotropic squash. "
             "*** MATERIAL FORK, UNCONTROLLED: DJI also sold an optional 'E305 9450 Carbon Fiber "
             "Reinforced' propeller for the Phantom 3. Carbon-loaded blades are conductive - in our "
             "table carbon |Gamma| 0.90 vs prop_plastic 0.25, i.e. +11.1 dB on the propeller group. "
             "This entry models the STOCK polymer prop. Treat the CF prop as a labelled sensitivity "
             "case, not a second spec. *** "
             "*** THE PHANTOM 3 HAS NO MAGNESIUM SKELETON. The magnesium-alloy core was introduced "
             "ON the Phantom 4 and is its headline structural upgrade over the plastic Phantom 3; "
             "DJI's Phantom 3 parts catalogue contains no magnesium part. The shared shell-v2 path "
             "in drone_cad nonetheless inserts a magnesium structural plate into the 'battery' "
             "group for every v2 shell airframe. It was NOT removed for this entry, because "
             "removing it would be a phantom3-only carve-out in shared code. CONSEQUENCE: this mesh "
             "over-metals the fuselage by one plate (0.58 bl x 0.68 bw x 0.08 bh). Declared bias. *** "
             "SHAPE IS MEASURED (2026-08-03 rebuild). The previous entry inherited the phantom4 "
             "photo-audit tables because the repository held no Phantom 3 photograph; 145 reference "
             "images now exist (assets/photos/phantom3/SOURCES.md) and the shape tables in "
             "drone_cad (_SHELL_SHAPE / _ARM_WIDTH / _ARM_SECTION / GEAR_ARCH / INTERNALS) are now "
             "pixel measurements off DJI's own orthographic 4-view line art, DJI's official top "
             "render and FCC / iFixit teardown photographs. Every constant carries its scale anchor "
             "in the drone_cad comments. "
             "*** MEASUREMENT THAT OVERTURNS THE PREVIOUS ENTRY: the published 185 mm is the SHELL "
             "CROWN to the feet, NOT the motor top to the feet. The front elevation and the rear "
             "elevation independently give 184.1 and 185.4 mm for crown->feet, and the front "
             "elevation's own motor-separation anchor (247.49 mm = 350 sin45 across the two bells) "
             "reproduces the same millimetres-per-pixel to five digits. Motor top to feet is only "
             "175 mm. Consequence: the shell is 78.6 mm thick, not the 63.9 mm this entry used to "
             "record, and the legs are 111.6 mm, not 120.5 mm. The old numbers came from taking the "
             "motor top as the crown; on a Phantom the body dome is 10 mm ABOVE the motors. *** "
             "motor_dia_mm 28.3 / motor_h_mm 13.7 MEASURED off the front elevation (bell 37.7 px "
             "wide, 18.3 px tall at 0.74929 mm/px); this matches the published DJI 2312 stator "
             "23 x 12 mm with an aluminium bell around it. Before this they were UNKNOWN and the "
             "diagonal-proportional fallback produced a 36.4 mm bell, +29%. "
             "*** FIXED 2026-08-07 (was: prop_z is a house formula motor_h + arm_t/2 + 6 mm, giving "
             "33.7 mm where the drawing shows the blade plane at 27.7 mm). prop_z is now derived "
             "from the motor bell top (drone_cad.motor_bell_top_z_m = 24.7 mm here) plus a "
             "per-airframe standoff; the P3 has a SCREW-ON hub, so its standoff is 1.55 mm = the "
             "drawing's 3.0 mm blade-plane clearance minus our own measured blade-neutral-plane "
             "offset 1.452 mm. Result: our blade plane lands at 27.702 mm against the drawing's "
             "27.7 mm. This did touch every airframe - that was the point, the two formulas had to "
             "become one. *** "
             "body_lw and body_frac remain UNKNOWN for the P3 and carry the phantom4 values - they "
             "do not enter the CAD shell path (build_frame_cad reads body_l/w/h_mm directly) and "
             "affect diagrams only.",
        body_rgb=_WHITE, arm_style="body", fixed_arm=True, gear="legs", gear_h_mm=106.1,
        motor_dia_mm=28.3, motor_h_mm=13.7,
        gimbal="belly", accent_rgb=None, body_frac=0.52, shape_source="spec_photo",
        rotor_deg=(45, 135, 225, 315), body_lw=(1.06, 1.0),
        gimbal_style="hanging_damped", cad_version="v2",
        envelope_mm=(None, None, 185.0)),
    # ----------------------------------------------------------------------- #
    # 9) 산업용 대형 쿼드 (2026-08-03 추가) — Das Table I 대조용 두 번째 형상 가족.
    #    제원의 단일 출처는 `outputs/m350rtk_specs.json`, 사진 65장의 출처는
    #    `assets/photos/m350rtk/SOURCES.md` 다. 등급(VERIFIED/SECONDARY/MEASURED/
    #    DERIVED/JUDGED)은 그 파일들이 적은 대로 **올리지 않고** 옮겼다.
    # ----------------------------------------------------------------------- #
    "m350rtk": DroneSpec(
        key="m350rtk", name="DJI Matrice 350 RTK",
        diagonal_mm=895.0, weight_g=6470.0,
        body_l_mm=285.0, body_w_mm=175.0, body_h_mm=200.0,
        prop_dia_mm=533.4, prop_blades=2, num_rotors=4,
        max_speed_ms=23.0, hover_rpm=2400.0, max_rpm=None, prop_pitch_in=10.0,
        rtk=True, release="released", confidence="high",
        note="Industrial quad: boxy fuselage, four FOLDING straight carbon-tube arms, two TB65 "
             "batteries carried EXTERNALLY in the rear bay, a tall detachable A-frame tube "
             "landing gear, and NO camera in the base configuration (DGC2.0 payload port only). "
             "It is the second SHAPE FAMILY in this registry with a published-sigma counterpart, "
             "which is the whole point of adding it - phantom3 rides the phantom4 shell table, so "
             "one anchor could not separate 'our method' from 'that one shell table'. "
             "VARIANT PROOF: the FCC nameplate in the applications photos reads 'DJI MATRICE 350 "
             "RTK / M350 RTK / FCC ID SS3-M3502301'; the M300 RTK, whose airframe is nearly "
             "identical, is SS3-M3001910. All 65 photographs used here come from that one "
             "application or from DJI's own product page and manuals (SOURCES.md). "
             "diagonal_mm 895 VERIFIED (enterprise.dji.com/matrice-350-rtk/specs, 'Diagonal "
             "Wheelbase'). weight_g 6470 VERIFIED but is the AIRCRAFT WITH TWO TB65 AND NO "
             "PAYLOAD - i.e. exactly what this mesh builds. Max takeoff weight is 9.2 kg; using "
             "that would put a payload on the aircraft that the mesh does not have. "
             "prop 533.4 mm / 10.0 in / 2 blades is SECONDARY, not DJI: DJI publishes the model "
             "name (2110s) but no geometry, and 21 x 10 in is a retailer figure. The ruler photos "
             "p05/p06 could cross-check the folded blade length and have NOT been used for that "
             "yet - so this number carries the weakest grade in the entry. "
             "rotor_deg 38.65 deg DERIVED, and the layout is EXACTLY determined rather than "
             "checked: DJI publishes the unfolded props-excluded box 810 x 670 mm and the 895 mm "
             "wheelbase. Put four rotors on the 447.5 mm circle at +/-a and let one isotropic "
             "overhang p at the rotor station close both equations - 895 cos a + p = 810 and "
             "895 sin a + p = 670 subtract to a = 38.65 deg and then p = 111.0 mm. "
             "*** RETRACTED 2026-08-03, an earlier revision of this note claimed the agreement of "
             "the two p values was a check on the layout. IT IS NOT. Two equations in two unknowns "
             "return the same p identically, for ANY box: run the nonsense box 1000 x 500 mm "
             "through the same algebra and it returns a = 21.73 deg with the two p values agreeing "
             "to 1e-13 mm. There is no redundancy left over to test anything with. What actually "
             "remains is (i) p = 111 mm has to be physically plausible, and (ii) a competing model "
             "- overhang purely RADIAL along the arm - closes the same two equations at "
             "a = 39.60 deg with q = 78 mm. The angle is therefore good to about 1 deg and no "
             "photograph in the folder narrows it further. *** The t02 reading (airframe, shell "
             "off, arms UNFOLDED, from above) lands on cot(38.65 deg) = 1.251 only after a camera "
             "tilt cosine is FITTED, i.e. one free parameter absorbs the one measurement, so it "
             "corroborates and does not test either. Prop clearance (house rule, must stay "
             "positive): front-to-front "
             "895 sin a = 559.0 vs prop 533.4 -> +25.6 mm; same-side fore-and-aft 895 cos a = 699.0 "
             "-> +165.6 mm. Both positive, the lateral one tight - as it is on the real aircraft. "
             "*** THE 111 mm OVERHANG IS LARGER THAN THE MOTOR POD WE MEASURE (about 60 mm across "
             "on p06), so either the pod reading is low or DJI's box touches something else at the "
             "rotor station. The competing model - overhang purely RADIAL along the arm - closes "
             "the same two equations exactly with a = 39.60 deg. The angle is therefore good to "
             "about 1 deg, and that 1 deg is the honest band on this layout. *** "
             "rotor_r_mm / rotor_z_mm None = one circle, flat: no photograph in the folder shows "
             "the unfolded aircraft from straight above, so a trapezoid cannot be tested, and one "
             "circle already satisfies both official plan dimensions. "
             "body_l/w/h 285 / 175 / 200 mm MEASURED, band about +/-6 %, and each from a "
             "DIFFERENT image so the three are not one reading repeated: length and max width from "
             "p06 (folded from above) at 0.706 mm/px, that scale being anchored on the VERIFIED "
             "folded width 420 mm and then reproducing the VERIFIED folded length 430 mm to "
             "-2.3 % as an independent check; width also from t05, where the fuselage lower shell "
             "lies in the same plane as a steel rule and measures 165 mm across (the 175 adopted "
             "here is the mean of the 184 mm outer reading on p06 and that 165). Height from the "
             "vertical proportions of d01 (official front elevation): body 130 px : gear 152 px, "
             "so setting the body to 200 mm returns a total of 434 mm against the VERIFIED 430 - "
             "+0.9 %, again an independent check rather than an assertion. "
             "arm_od_mm 22.0 MEASURED, +/-10 %, from two photographs that do not share a scale: "
             "p06 gives 19.1 mm (chord across the tilted tube, corrected by the tube's screen "
             "angle) and p07 gives 22.5 mm against the body height. "
             "motor_dia_mm 56.0 MEASURED from the prop-hub cover diameter on p06; motor_h_mm 30.0 "
             "DERIVED (bell height is not visible in any view - it only has to put prop_z above "
             "the bell top). "
             "gear_h_mm 230.0 DERIVED from the same d01 decomposition (430 - 200), and the gear "
             "itself is built from measured numbers in drone_cad, not from the 0.30*body_h shell "
             "convention. "
             "hover_rpm 2400 DERIVED with the registry's own C_T ladder: the 2110s pitch ratio "
             "10/21 = 0.476 sits between the DJI 9450 (0.532, NASA/US Army full-vehicle hover "
             "C_T = 0.0140; Russell/Jung/Willink/Glasner, AHS Forum 72, 2016) and the DJI 1552 "
             "(0.347, bounded below 0.0105 in the s1000plus note). Interpolating gives C_T = "
             "0.01294 and T = 6.47*9.80665/4 = 15.86 N per rotor at D = 0.5334 m gives 2396 rpm. "
             "Like every hover_rpm here it is a HARDCODED LITERAL and does not re-solve. "
             "max_rpm None = UNKNOWN: an industrial platform predating and outside C-class "
             "certification publishes no firmware propeller-speed ceiling. "
             "envelope_mm forces HEIGHT ONLY (430 mm, props excluded), the house rule shared with "
             "mini5pro / mavic4pro / matrice4e / typhoonh480 / phantom3. Forcing L and W too would "
             "hand frame_fit_scale an anisotropic squash, and here it would also be wrong in a "
             "specific way: our frame reaches only about 760 x 620 mm because we build the pod we "
             "can measure rather than the 111 mm overhang the box implies. That gap is REPORTED, "
             "not scaled away - report02 already records that a 0 % envelope match is a constraint "
             "frame_fit_scale manufactures, not evidence. "
             "gimbal 'none' is an OBSERVATION, not a simplification: every external photograph in "
             "the application shows the aircraft with the DGC2.0 port empty, and DJI sells the "
             "Zenmuse payloads separately. The mesh therefore carries the payload MOUNT and no "
             "camera - which is also why this entry inherits none of the repository's gimbal "
             "constant blocks. "
             "arm_style 'carbon' VERIFIED from the weave visible on p06/p07; the root collars and "
             "the motor pods are moulded plastic and drone_cad puts them in the plastic group "
             "SEPARATELY - this airframe does not repeat the typhoonh480 simplification that folds "
             "collar and tube into one material. "
             "*** THE TWO TB65 BATTERIES ARE OUTSIDE THE SHELL. They slide into the rear bay and "
             "their own cases are the aircraft's rear surface, so on this airframe the dominant "
             "metal scatterer is NOT behind a dielectric shell the way it is on every folding "
             "consumer entry here. The mesh places them at the measured rear-bay position; the "
             "residual bias is that rcs_sbr still treats the surrounding 'body' group as a shell. "
             "Declared, not fixed. *** "
             "NOT MODELLED, declared: the CSM Radar (an accessory, and the FCC unit wears one), "
             "the four white motor protection caps of the test unit, the GNSS antennas as separate "
             "bodies (the motor top covers stand in), and the aircraft's six-direction vision "
             "system beyond the eight lens ports that are actually placed.",
        body_rgb=_GRAY_D, arm_style="carbon", gear="tall", gear_h_mm=230.0,
        gimbal="none", accent_rgb=None, body_frac=285.0 / 895.0, shape_source="spec_photo",
        rotor_deg=(38.65, 141.35, 218.65, 321.35), body_lw=(1.0, 175.0 / 285.0),
        gimbal_style="none", cad_version="v2",
        #  ⚠ arm_shape 는 기본값("folding")을 그대로 둔다. "tube" 로 두면 `_arm_motor_dims` 가
        #    **열린 프레임 식**(OPEN_MOTOR_BASE_M = X500 V2 의 모터마운트 판 높이 12.7 mm)으로
        #    갈아타는데, M350 의 모터는 판이 아니라 **암 끝 포드** 위에 앉는다. 형상은 어차피
        #    drone_cad 의 전용 분기가 짓고, 이 필드는 prop_z 공식만 고른다.
        arm_od_mm=22.0, motor_dia_mm=56.0, motor_h_mm=30.0,
        envelope_mm=(None, None, 430.0)),
    # ----------------------------------------------------------------------- #
    # 10) 초소형 접이식 (2026-08-03 추가) — ⭐ **제조사 자기 CAD 로 지은 첫 DJI 기체.**
    #     제원의 단일 출처는 `outputs/mini2_specs.json`, 참조자료 84장의 출처는
    #     `assets/photos/mini2/SOURCES.md` 다. 등급(VERIFIED/MEASURED/DERIVED/UNKNOWN)은
    #     그 파일들이 적은 대로 **올리지 않고** 옮겼고, 형상 상수는 전부 아래 note 의
    #     GLB 실측에서 나온다(drone_cad._SHELL_SHAPE["mini2"] 주석에 픽셀급 근거).
    # ----------------------------------------------------------------------- #
    "mini2": DroneSpec(
        key="mini2", name="DJI Mini 2",
        diagonal_mm=213.0, weight_g=249.0,
        body_l_mm=159.0, body_w_mm=203.0, body_h_mm=56.0,
        prop_dia_mm=119.1, prop_blades=2, num_rotors=4,
        max_speed_ms=16.0, hover_rpm=9200.0, max_rpm=None, prop_pitch_in=2.6,
        rtk=False, release="discontinued", confidence="high",
        note="Sub-250 g folding quad, the smallest airframe in the registry by a wide margin "
             "(213 mm diagonal vs phantom3 350, m350rtk 895). Moulded plastic shell and moulded "
             "plastic arms, a compact 3-axis gimbal recessed into the nose, two landing posts on "
             "the FRONT arms only, and no obstacle sensing except downward vision + infrared. "
             "*** SHAPE SOURCE IS DJI'S OWN 3D CAD, NOT PHOTOGRAPHS. DJI's product page served two "
             "GLB models of the WM161 (the Mini 2's internal code), unfolded and folded, and they "
             "are still up (SOURCES.md section 4). Every shape constant in this entry and in "
             "drone_cad._SHELL_SHAPE['mini2'] / _ARM_SECTION['mini2'] / _ARM_WIDTH['mini2'] was "
             "measured off the unfolded GLB. NOTHING was inherited from another airframe - which is "
             "the exact opposite of the phantom3 entry, whose shell table, arm width and arm "
             "section are all copied from phantom4. Only x500v2 (Holybro STEP) had "
             "shape_source='manufacturer_cad' before this. *** "
             "THE CAD VALIDATES ITSELF against DJI's own specification table: with the eight "
             "propeller-blade meshes removed its bounding box is 159.1 x 203.4 x 56.0 mm against "
             "the published 159 x 203 x 56 (+0.06 / +0.2 / 0.0 %), and the motor-to-motor diagonal "
             "measures 213.05 mm against the published 213 mm (+0.02 %). Two independent DJI "
             "artefacts agreeing to 0.2 % is what licences using the CAD as the shape source. "
             "diagonal_mm 213 VERIFIED (User Manual v1.0 2020.11 p.45, 'Diagonal Distance'). "
             "weight_g 249 VERIFIED but it is a REGULATORY CEILING ('<249 g', the sub-250 g class), "
             "not a measured mass, so every mass-derived quantity here is an upper bound. The "
             "Japan-market 199 g version is a DIFFERENT aircraft and is not modelled. "
             "body_l/w/h 159 / 203 / 56 = the published unfolded props-excluded envelope, used here "
             "only as the denominator of the shell ratios fl/fw/fh; the SHELL itself measures "
             "137.66 x 66.85 x 46.16 mm (GLB part 'Default_4', 23,912 triangles) and that is what "
             "the mesh builds. Cross-check on the shell length: DJI's published FOLDED length is "
             "138 mm and the folded envelope is set by the fuselage - 137.66 vs 138 is 0.2 %. "
             "*** THE SHELL IS NOT CENTRED ON THE ROTOR ARRAY. Its fore-aft centre sits 20.2 mm "
             "AHEAD of the rotor centroid. build_frame_cad always builds the shell at the origin, "
             "so the origin here is defined as the SHELL centre and the rotors are expressed about "
             "that - which is why rotor_deg/rotor_r_mm are fore-aft ASYMMETRIC (63.14 deg / 98.43 mm "
             "front, 133.70 deg / 116.92 mm rear) where every other folding entry is symmetric. "
             "Centring on the rotors instead would pull the nose back by 20.2 mm and shorten the "
             "props-excluded length from 159.1 to 140.5 mm, -11.7 %. The price of this choice is "
             "that 2 x mean rotor radius (215.4 mm) is no longer the wheelbase; the wheelbase is "
             "still exactly right at 213.05 mm and frame_envelope_mm reports both. *** "
             "rotor_deg / rotor_r_mm MEASURED from the four motor-bell centres in the GLB: front "
             "(x +44.47, y +/-87.81), rear (x -80.77, y +/-84.54) mm about the shell centre. Front "
             "track 175.6, rear track 169.1, fore-aft spacing 125.2 mm - a trapezoid, not a square. "
             "Prop clearance (house rule, must stay positive): front pair 175.6 - 119.1 = +56.5, "
             "rear pair 169.1 - 119.1 = +50.0, same-side fore-and-aft 125.3 - 119.1 = +6.2, "
             "diagonal 213.05 - 119.1 = +94.0 mm. All positive. "
             "rotor_z_mm +/-10.63 MEASURED from the two propeller mid-planes (front 21.25 mm above "
             "rear). The Mini 2 hinges its FRONT arms off the TOP of the fuselage and its REAR arms "
             "off the BOTTOM, so the two rotor pairs really are at different heights. "
             "*** THE ARMS, MOTOR BELLS AND LANDING POSTS FOLLOW rotor_z_mm on this airframe "
             "(drone_cad.ARM_Z_FOLLOWS_ROTOR, key-gated so no other airframe is affected). The two "
             "arm axes are 21.44 mm apart in the CAD (front +13.68, rear -7.76, measured on sections "
             "cut PERPENDICULAR to each arm's own axis at r 70-100 mm); half of that, 10.72, agrees "
             "with the independently measured propeller-plane offset 10.63 to 0.09 mm. "
             "RESIDUAL, DECLARED: a uniform dz per rotor keeps the engine's upward tip rise, whereas "
             "the real rear arm slopes DOWN going outboard (-5.89 at r 60-70 to -8.19 at r 90-100) - "
             "a 2.5 mm slope-sign error over 40 mm that this airframe still carries. Second residual: "
             "the bell bases are 21.81 mm apart (half 10.905) against the 10.63 used, because "
             "rotor_z_mm is what positions the propellers and the propellers are already right; the "
             "0.275 mm is left rather than chased. *** "
             "prop_dia_mm 119.1 MEASURED (outputs/mini2_specs.json, DJI's GLB). Re-measured here "
             "about the motor-bell centres as 118.6 (front) / 119.9 (rear), mean 119.2, i.e. +0.1 % "
             "- inside the noise, so the registered 119.1 is kept. DJI publishes NO propeller "
             "geometry for the Mini 2 anywhere (manual, QSG, and the standalone Propellers User "
             "Guide were all checked). "
             "prop_pitch_in 2.6 MEASURED, band 2.0-3.0, and this UPGRADES the UNKNOWN that "
             "outputs/mini2_specs.json records. Method: for each of the four modelled blades, take "
             "vertex annuli at r/R = 0.30...0.90, fit the chord axis in the (tangential, axial) "
             "plane by SVD to get the local blade angle beta(r), and invert our own twist law "
             "theta = atan(k(r/R) P / (2 pi r)) with the repository's PITCH_K table for P. Blade "
             "medians: 2.76 / 2.49 in (front pair), 2.00 / 3.00 in (rear pair, which is modelled "
             "with a visible coning tilt that splits its two blades); overall median 2.56 in, "
             "adopted 2.6. THE SPREAD IS THE HONEST STATEMENT - report the band, not the point. "
             "This lands on the 2.6 in implied by the widely quoted '4726F' part designation. That "
             "designation was NOT the source of the value, but it IS legible on a DJI-submitted "
             "federal exhibit - assets/photos/mini2/mini2_t28_fcc_mt2wd_propeller_motor_view.jpg "
             "shows '4726 F' printed on both propeller blades of the certification unit - so the "
             "agreement is an independent corroboration, not a coincidence of hearsay. The value "
             "stays MEASURED from blade twist and is not re-sourced to a part number after the fact; "
             "outputs/mini2_specs.json's instruction not to substitute 4726F is respected. Leaving "
             "it None would have dropped this airframe alone onto the legacy linear-washout blade "
             "law (MESH_METHOD section 4c). "
             "hover_rpm 9200 DERIVED, band 9000-9335 (C_T 0.0132-0.0142), copied from "
             "outputs/mini2_specs.json. The C_T anchor is the NASA/US Army Phantom 3 + 9450 "
             "measurement (Russell/Jung/Willink/Glasner, AHS Forum 72, 2016) - a TRANSFER across "
             "pitch ratio, not a same-aircraft anchor, and its justification leans on the measured "
             "pitch above. Like every hover_rpm here it is a HARDCODED LITERAL and does not "
             "re-solve if weight_g or prop_dia_mm change. Tip speed 57.4 m/s. "
             "max_rpm None = UNKNOWN - a 2020 product predating C-class marking; an electrical "
             "no-load figure is a different quantity (matrice4e note). "
             "arm_style 'body' VERIFIED from the iFixit teardown and the CAD: the arms are moulded "
             "plastic of the same family as the shell, so they join the plastic group. Had they "
             "been carbon this would be |Gamma| 0.90 vs 0.28 = 10.1 dB on the arms. "
             "gear 'motor_legs' with gear_h_mm 30.8 MEASURED = front-arm underside (z +6.3) to foot "
             "(z -24.5) in the GLB. ONE post per front arm, matching the aircraft: polySurface202, "
             "9.16 x 9.53 mm in section and 37.25 mm long, centre (49.74, +/-94.90) = radius 107.15 "
             "at azimuth 62.35 deg, i.e. 8.72 mm OUTBOARD of the motor axis. The engine's outer "
             "prong sits at r_motor + 0.95*mot_r = 107.08 mm, 0.07 mm from it; the prong count and "
             "half-width are per-key (drone_cad.GEAR_LEG_N_PRONG / GEAR_LEG_W_M) so mini5pro and "
             "mavic4pro, which photograph with two prongs, are untouched. RESIDUAL, DECLARED: the "
             "helper builds 2w x 1.7w, so w = 4.77 reproduces the 9.53 mm lateral dimension exactly "
             "and leaves the fore-aft at 8.11 against a real 9.16 (-11 %). "
             "*** RETRACTED, 2026-08-04: outputs/mini2_mesh_audit.json declares 'two small rear pads "
             "at the rear-arm roots, (x -47, y +/-26, down to z -19.8)' as an unmodelled defect. NOT "
             "REPRODUCED. Taking every non-propeller part with x < -20 and its lowest z gives "
             "Default_4 (fuselage shell) -20.13, pSphere3 -16.16, polySurface10 -15.94, "
             "polySurface101/21 (rear arms) -14.90, Mesh/zengjia_3 -14.80, Default_23 -14.44. "
             "Nothing at (x -47, y +/-26) reaches -19.8 except the shell itself, whose belly is the "
             "lowest structure in the rear half. There appear to be no separate rear landing pads on "
             "this airframe, so none are modelled and the audit entry is the thing to correct - an "
             "unverified declared defect is a false debt that invites modelling a part that does not "
             "exist. *** "
             "envelope_mm - see the ENVELOPE note below the constructor. "
             "gimbal_style 'single' VERIFIED: one 3-axis stabilised camera (tilt -110/+35, roll "
             "+/-35, pan +/-20, manual p.46), recessed into the nose. drone_cad reuses the Mini "
             "family's _gimbal_compact3 and back-solves its arguments from the measured 40.57 x "
             "32.24 x 34.01 mm block so the built assembly's bounding box matches by construction. "
             "*** NO FISHEYES, NO LiDAR, NO NOSE GRILLE. DJI's own sensing table says the Mini 2 "
             "has downward vision + infrared and NOTHING else - no forward, backward or lateral "
             "obstacle sensing. Copying the mini5pro branch would have bolted six to eight sensors "
             "that do not exist onto this airframe. Only the two downward-vision lenses are placed, "
             "at the measured belly position. *** "
             "accent_rgb None: the orange propeller tips are paint, and an accent ring would build "
             "a part the aircraft does not have. "
             "*** NO MAGNESIUM SKELETON, same declared bias as phantom3. The shared shell-v2 path "
             "inserts a 'magnesium structural plate' into the metal 'battery' group for every v2 "
             "shell airframe. The Mini 2 has no magnesium chassis - but it DOES have a large finned "
             "metal heatsink/shield over the SoC filling much of the belly (iFixit t03-t05, FCC "
             "t21), so on this airframe that plate has a real counterpart even though its size is a "
             "shared ratio, not a measurement. Declared either way. *** "
             "*** THE HIGHEST POINTS ARE THE PROPELLER-MOUNT SCREW HEADS, and they are modelled "
             "(drone_cad.PROP_SCREW_POSTS, two solid 3.79 mm square posts per rotor at radius 5.0 mm "
             "from the motor axis, standing 5.47 mm above the bell top). Four separate GLB parts, "
             "two per rotor, put their tops at z +31.46 (front). *** CLAIM STRENGTH CORRECTED "
             "2026-08-07 (M2/C5): -24.52 is NOT an independent measurement - the mini2 round DEFINES "
             "the props-excluded lowest point to be z = -24.52 (see outputs/meshfix_mini2.json "
             "frame_convention: 'origin_z ... 를 -24.52 로 정의한다'). So +31.46 is a coordinate in "
             "that datum, not a second fact. The ONE quantity measured independently is the vertical "
             "SPAN 55.97734 mm, and it matches the published 56 mm to -0.040 %. Read the two numbers "
             "as one span, not as two agreeing measurements. Corroborated, not "
             "measured, by the FCC exhibit mini2_t28: two steel cross-head screws per propeller hub, "
             "diametrically opposite - steel, hence the metal 'motor' group. DECLARED: the CAD's "
             "screw heads float 4.6 mm above the bell top because the propeller hub that fills the "
             "gap belongs to the blade meshes; a floating box would add an unsupported interior "
             "surface, so the shank is built solid and those 4.6 mm are geometry the CAD does not "
             "draw. Their azimuth is a JUDGED choice (they rotate with the motor, so the CAD pose is "
             "arbitrary); at r = 5.0 mm they stay inside the 9.1 mm bell radius and cannot change "
             "any silhouette. *** "
             "The arm-end fairings that carry the true width are modelled through "
             "drone_cad.ARM_TIP_OVERHANG (per-rotor, front 15.09 / rear 9.30 mm); the frame width "
             "now overshoots by +1.6 % instead of falling short by -4.7 %, because the swept tip "
             "section stays 9.0 mm wide where the real fairing has tapered to 6.96 - see that table "
             "for why the envelope-solved 13.33 mm was refused. "
             "NOT MODELLED, declared: the GPS patch antenna as a separate body, and the ESC board.",
        body_rgb=_SILVER, arm_style="body", gear="motor_legs", gear_h_mm=30.8,
        gimbal="front", accent_rgb=None, body_frac=137.66 / 213.0,
        shape_source="manufacturer_cad",
        rotor_deg=(63.14, 133.70, 226.30, 296.86),
        rotor_r_mm=(98.43, 116.92, 116.92, 98.43),
        rotor_z_mm=(10.63, -10.63, -10.63, 10.63),
        body_lw=(1.0, 66.85 / 137.66), gimbal_style="single", cad_version="v2",
        motor_dia_mm=18.2, motor_h_mm=7.1,
        #  ⚠ arm_od_mm 은 **일부러 비워 둔다.** 주면 `_arm_folding` 이 등단면이 되어
        #    _ARM_WIDTH["mini2"] 의 완만한 테이퍼(9.9→9.0)가 죽고, `_arm_motor_dims` 의
        #    arm_t 도 갈아탄다. 실측 암은 9.0~9.9 로 거의 등단면이라 두 경로 차이는 1 mm 미만이고,
        #    대각비례가 주는 arm_t = 0.045·213 = 9.59 mm 는 실측 평균 9.24 와 +3.8 % 다 —
        #    이 기체에서는 비례식이 우연히 실측과 맞는 드문 경우다(그래서 덮을 이유가 없다).
        envelope_mm=(None, None, 56.0)),
        # ⭐ ENVELOPE — **높이만** 강제(집안 규칙, mini5pro/mavic4pro/matrice4e/typhoonh480/
        #   phantom3/m350rtk 와 같다). 강제 전 원본 프레임은 **160.09 × 206.92 × 55.93 mm** 다.
        #     길이 160.09 ↔ CAD 159.11 → **+0.62 %**  (강제하지 않았는데 맞는다.
        #        원점을 로터 중심이 아니라 셸 중심에 둔 것이 이 값을 만든다 — 위 note 참조)
        #     폭   206.92 ↔ CAD 203.43 → **+1.7 %**  (암 끝 페어링 스윕이 끝단면을 실물의
        #        6.96 mm 로 좁히지 못하고 9.0 mm 로 쓸어가는 잔차 — ARM_TIP_OVERHANG 주석 참조.
        #        ⛔ 목표 폭에서 역산한 오버행 13.33 mm 는 채택하지 않는다. 부품에서 잰 값이 아니다.)
        #     높이  55.93 ↔ 공표  56   → **−0.13 %** → sz = 1.0013.
        #        최저점은 앞 착륙포스트(−24.75, CAD −24.52), 최고점은 프롭 나사머리(+31.19, CAD +31.46).
        #   ⛔⛔ **L/W 를 추가로 강제하지 말 것.** 자유롭게 둔 길이·폭이 0.6 %/1.7 % 안에 들어오면
        #     "그것도 맞춰버리자" 가 유혹적으로 보인다. 그 순간 frame_fit_scale 이 비등방 압축으로
        #     바뀌고, 0 % 일치는 **증거가 아니라 구속조건**이 된다.
        #   ⚠ 셸 자체의 남는 잔차(선언): 지어진 셸 bbox 높이는 CAD 46.16 보다 +4.8 % 다. 이것은
        #     로프트 스플라인 오버슈트(엔진 아티팩트)이고 22개 스테이션 숫자가 **측정값**이다 —
        #     fh 를 깎아 흡수하면 엔진을 고치려고 측정을 망가뜨리는 것이 된다. 셸은 더 이상
        #     bbox 를 정하지 않으므로 이 잔차는 fit 스케일에 닿지 않는다.
        #   [참고] 예전 실루엣 IoU 측정(quick 모드, 같은 파이프라인, 강제 ↔ 비강제):
        #        d06 정면(알파) 0.670 ↔ 0.678   d05 3/4 0.695 ↔ 0.705
        #     ⚠ 그 값은 sz = 0.906 시절의 것이라 지금(sz = 1.0013)은 다시 재야 한다.
        #     강제를 유지하는 이유는 IoU 가 아니다 — 저앙각 σ 가 기체 높이에 직접 걸리므로
        #     레지스트리 전 기종을 같은 규약(공표 높이)에 두어야 기종 간 비교가 성립한다.
}


# --------------------------------------------------------------------------- #
#  ⭐⭐ 기체별 프로펠러 법칙 — «그 기체의 진짜 프롭» (2026-08-16)
# --------------------------------------------------------------------------- #
#  고친 것 하나: 지금까지 **10기종 전부가 같은 프로펠러**를 달고 있었다.
#    · 통통한 정도 c_max/R = 0.25 상수 하나 (drone_cad.CHORD_MAX_OVER_R)
#    · 평면형(시위 분포)은 3DR Solo 프롭 **하나**에서 베낀 곡선 하나
#  실측하면 c_max/R 은 0.177~0.271 로 **기종 사이가 53 % 벌어지고 크기와 반비례**한다.
#  기종 비교(=분류)가 이 위에 서 있으므로 «같은 프롭» 은 그냥 두면 안 되는 결함이다.
#
#  ⚠⚠ **켜는 법**: `drone_cad.build_propeller_cad(spec, blade_law="per_airframe")`.
#     인자를 안 주면 예전 그대로다(legacy). 이 표는 필드를 채워 둘 뿐 아무도 안 읽는다.
#
#  ⭐ 축을 밝힌다: `cmax_over_r` 은 **설계 시위**(반경 r 원통 단면의 최대 캘리퍼) 축이다 —
#     `drone_cad` 의 로프트가 익형을 세울 때 쓰는 바로 그 길이. 사진은 **투영 호폭**(r·Δθ)
#     밖에 못 주므로, 사진 유래 기종은 실측 다리 **×1.031** 이 이미 곱해져 있다.
#     그 다리는 3D 가 있는 프롭 둘에서 직접 쟀다(Mini 2 완전전개 1.020 · Yuneec 1.045).
#     ⛔ «1/cos θ 로 되돌리기» 는 그 둘 다에서 +3.8 % 높게 나온다 — 두께와 스윕이 각폭을
#       넓히는 몫을 무시하기 때문이다. 그래서 안 쓴다.
#
#  근거 등급
#    [A]  그 프롭 **자체**의 제조사 공식 3D 기하        — mini2 하나뿐이다
#    [A-] 그 프롭 자체의 3D 인데 출처 문서가 없다        — typhoonh480
#    [B]  그 프롭 자체의 사진을 정밀 계측               — matrice4e · phantom3
#    [B-] 같은데 시점·출처·문턱값 중 하나가 약하다        — mavic4pro · s1000plus · m350rtk
#    [C]  같은 계열 다른 프롭에서 유추 / 기체 동일성 미확정 — phantom4 · mini5pro
#    [D]  ⛔**대리** — 다른 회사·다른 계열 프롭을 빌려 씀   — x500v2
#
#  정본 후보 원장: outputs/prop_law_by_airframe_0816.json
#  생산자        : benchmark/prop_law_by_airframe_0816.py   (계측 원장 넷을 한 자로 모은다)
#  계측 원장     : outputs/prop_measure_{mini2_reference,mini2_xcheck,matrice4e,
#                  mavic4pro_mini5pro,others}_0816.json · outputs/prop_identity_0816.json
#  서술          : docs/MESH_AUDIT_0816.md §⑦
#
#  ⛔ 빈칸은 빈칸이다. `t_mm`·`tc_max` 가 None 인 8기종은 **두께 근거가 없다** — 사진으로는
#     원리적으로 못 잰다(겉보기 높이 = c·sinβ + t·cosβ 이고 앞항이 두께의 5배다).
#     없는 수를 만들어 채우지 않았다.
PROP_LAW_0816: dict[str, dict] = {
    # ── mini5pro — DJI 6028F · 등급 [C]
    #    152.4 × 71.1 mm (6.0 × 2.8 in), 2날 접이식, 2.8 g
    "mini5pro": dict(
        model='DJI 6028F',
        cmax_over_r=0.20914, grade='C',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.1924, 0.2693, 0.3527, 0.4631, 0.5778, 0.6848, 0.7859, 0.8758, 0.9495, 0.9939,
            1.0, 0.9768, 0.9343, 0.8859, 0.8313, 0.7747, 0.6929, 0.6081, 0.5283, 0.452, 0.2225
        ),
        t_mm=None, tc_max=None,
        source="assets/photos/mini5pro/'mini 5 pro_3.png' (로터 4개; 평면형은 가장 정면인 프롭 0·1 평균)"),
    # ── mavic4pro — DJI 1158F · 등급 [B-]
    #    267 × 147 mm (10.5 × 5.8 in), 2날 접이식, 11.8 g
    "mavic4pro": dict(
        model='DJI 1158F',
        cmax_over_r=0.1791, grade='B-',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.2448, 0.3427, 0.4488, 0.5893, 0.7352, 0.8299, 0.8849, 0.9358, 0.9745, 0.9959,
            1.0, 0.9878, 0.9399, 0.8788, 0.8065, 0.7291, 0.6365, 0.5092, 0.3646, 0.3119,
            0.1535
        ),
        t_mm=None, tc_max=None,
        source='assets/photos/mavic4pro/mavic4pro_c10_propeller_pair_1158F.jpg (프롭 2개, 산포 1.6 %)'),
    # ── matrice4e — DJI 1157F (표준·순정 동봉) · 등급 [B]
    #    274 mm (10.8 in) × 피치 5.7 in [DERIVED 부품번호 규약], 2날 접이 퀵릴리즈
    "matrice4e": dict(
        model='DJI 1157F (표준·순정 동봉)',
        cmax_over_r=0.20038, grade='B',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.3216, 0.4502, 0.5896, 0.7741, 0.9532, 1.0, 0.9929, 0.9735, 0.9486, 0.9143,
            0.8903, 0.8517, 0.814, 0.7731, 0.7313, 0.683, 0.608, 0.5257, 0.4386, 0.3646,
            0.1795
        ),
        t_mm=None, tc_max=None,
        source='assets/photos/matrice4e/matrice4e_c02_prop_standard_1157F_pair.jpg (DJI 스토어 제품 렌더, 날 4장)'),
    # ── s1000plus — DJI 1552 / 1552R (거울쌍) · 등급 [B-]
    #    381 × 132.1 mm (15 × 5.2 in), 2날 접이 탄소 블레이드 + 금속 브래킷
    "s1000plus": dict(
        model='DJI 1552 / 1552R (거울쌍)',
        cmax_over_r=0.1756, grade='B-',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.2857, 0.3999, 0.5238, 0.6877, 0.858, 1.0, 0.9923, 0.9144, 0.8353, 0.7803, 0.7259,
            0.6815, 0.6458, 0.6128, 0.5793, 0.5423, 0.5067, 0.4861, 0.4531, 0.3877, 0.1908
        ),
        t_mm=None, tc_max=None,
        source='assets/photos/s1000plus/s1000+_1.png (상면 평면, 로터 8개 중 뿌리를 본 «깨끗한» 날 9장)'),
    # ── phantom4 — DJI 9450S (유력·미해결) · 등급 [C]  ⟵ **대리**(phantom3)
    #    240 × 127 mm (9.4 × 5.0 in), 2날 고정
    "phantom4": dict(
        model='DJI 9450S (유력·미해결)',
        cmax_over_r=0.26874, grade='C',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.2906, 0.4068, 0.5328, 0.6995, 0.8728, 0.9603, 1.0, 0.9415, 0.8432, 0.7766,
            0.7153, 0.6655, 0.6163, 0.5747, 0.5345, 0.5, 0.462, 0.4278, 0.3951, 0.338, 0.1664
        ),
        t_mm=None, tc_max=None,
        source='⚠자체 측정 없음 — phantom3 의 9450 을 그대로 쓴다(같은 세대·같은 공칭 9.4×5.0 in)'),
    # ── typhoonh480 — Yuneec Propeller A / B (YUNTYH118A / YUNTYH118B) · 등급 [A-]
    #    228.6 mm (9.0 in) × 피치 6.0 in [DERIVED], 2날 고정, 헥사 A3+B3
    "typhoonh480": dict(
        model='Yuneec Propeller A / B (YUNTYH118A / YUNTYH118B)',
        cmax_over_r=0.17664, grade='A-',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.2543, 0.356, 0.4662, 0.6121, 0.7637, 0.8699, 0.9475, 0.9884, 1.0, 0.9927, 0.9768,
            0.956, 0.9203, 0.8813, 0.8302, 0.7706, 0.6952, 0.6134, 0.5215, 0.4462, 0.2196
        ),
        t_mm=None, tc_max=0.128,
        source='assets/meshes/reference/prop_cw_assembly_remeshed_v3.stl + prop_ccw…(CW·CCW 날 4장)'),
    # ── x500v2 — 1045 (범용 규격 — Holybro X500 V2 킷 동봉) · 등급 [D]  ⟵ **대리**(phantom3)
    #    254 × 114.3 mm (10 × 4.5 in), 2날 고정
    "x500v2": dict(
        model='1045 (범용 규격 — Holybro X500 V2 킷 동봉)',
        cmax_over_r=0.26874, grade='D',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.2906, 0.4068, 0.5328, 0.6995, 0.8728, 0.9603, 1.0, 0.9415, 0.8432, 0.7766,
            0.7153, 0.6655, 0.6163, 0.5747, 0.5345, 0.5, 0.462, 0.4278, 0.3951, 0.338, 0.1664
        ),
        t_mm=None, tc_max=None,
        source='⛔**근거 없음.** 10인치급 실측 둘(DJI 9450 9.4in 0.271 · 3DR Solo 10in 0.273)이 붙는다는 것만 근거로 9450 의 평면형을 **대리**로 쓴다'),
    # ── phantom3 — DJI 9450 (자동조임) · 등급 [B]
    #    240 × 127 mm (9.4 × 5.0 in), 2날 고정, 12 g, 유리섬유강화 나일론
    "phantom3": dict(
        model='DJI 9450 (자동조임)',
        cmax_over_r=0.26874, grade='B',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.2906, 0.4068, 0.5328, 0.6995, 0.8728, 0.9603, 1.0, 0.9415, 0.8432, 0.7766,
            0.7153, 0.6655, 0.6163, 0.5747, 0.5345, 0.5, 0.462, 0.4278, 0.3951, 0.338, 0.1664
        ),
        t_mm=None, tc_max=None,
        source='assets/photos/phantom3/phantom3_d03_official_top.png (DJI 공식 상면 렌더, 날 4장, 산포 1.5 %)'),
    # ── m350rtk — DJI 2110s · 등급 [B-]
    #    533.4 × 254 mm (21 × 10 in), 2날 접이식
    "m350rtk": dict(
        model='DJI 2110s',
        cmax_over_r=0.18092, grade='B-',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.333, 0.4661, 0.6105, 0.8015, 1.0, 0.9674, 0.9617, 0.9617, 0.9634, 0.9432, 0.9318,
            0.8965, 0.8508, 0.8094, 0.7616, 0.7105, 0.6403, 0.5631, 0.4393, 0.3758, 0.185
        ),
        t_mm=None, tc_max=None,
        source='assets/photos/m350rtk/… (접힌 프롭 쌍 제품사진; 축척은 그림 안에서 조립 R = r_h + L)'),
    # ── mini2 — DJI 4726F · 등급 [A]
    #    119.4 × 66.0 mm (4.7 × 2.6 in), 2날 접이식
    "mini2": dict(
        model='DJI 4726F',
        cmax_over_r=0.25724, grade='A',
        chord_rr=(
            0.0, 0.07, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
            0.8, 0.85, 0.9, 0.95, 0.98, 1.0
        ),
        chord_frac=(
            0.2677, 0.3747, 0.4907, 0.6442, 0.8038, 0.9038, 0.9504, 0.9839, 1.0, 0.9975,
            0.9839, 0.9557, 0.9202, 0.8691, 0.8118, 0.7475, 0.6662, 0.579, 0.4726, 0.4043,
            0.199
        ),
        t_mm=0.478, tc_max=0.058,
        source='assets/meshes/reference/WM161_zhankai_1k.glb (DJI 공식 3D, 완전전개 앞 프롭 날 4장)'),
}

#  표 → 레지스트리. **레지스트리 밖에 둔 이유**: 10기종의 note 가 이미 수백 줄이라 그 안에
#  21점짜리 곡선을 끼우면 아무도 대조를 못 한다. 여기 모아 두면 «기체별로 정말 다른가» 를
#  한 화면에서 확인할 수 있다. 필드는 전부 기본값 None 이므로 이 루프가 없어도 안 죽는다.
for _k, _law in PROP_LAW_0816.items():
    _s = DRONES[_k]
    _s.prop_law_model = _law["model"]
    _s.prop_law_cmax_over_r = _law["cmax_over_r"]
    _s.prop_law_chord_rr = _law["chord_rr"]
    _s.prop_law_chord_frac = _law["chord_frac"]
    _s.prop_law_t_mm = _law["t_mm"]
    _s.prop_law_tc_max = _law["tc_max"]
    _s.prop_law_grade = _law["grade"]
    _s.prop_law_source = _law["source"]
del _k, _law, _s



# --------------------------------------------------------------------------- #
#  표적 목록·표시명·기종색 — **전부 DRONES 레지스트리에서 유도한다**
# --------------------------------------------------------------------------- #
#  ⭐ 2026-07-30 (Phase 3, 저장소 전체 5종→7종). 저장소 20여 곳에
#     `["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"]` 가 하드코딩돼 있었다.
#     그 목록의 결함은 **에러가 아니라 침묵**이다 — 기종을 추가해도 예외 하나 없이 새 기체가
#     그림·검증·벤치마크에서 그냥 빠진다(오늘 신규 2종이 실제로 전부 빠졌다).
#     ⇒ **개수를 세는 코드는 상수를 쓰지 않는다.** 소비자는 아래 세 함수를 쓴다.
#  ⚠ `len(DRONES)` 가 유일한 개수 출처다. 산문에 개수를 적어야 하면 한 번만 적고 여기를 가리킨다.

def drone_keys() -> list[str]:
    """레지스트리 등록 순서 그대로의 전체 표적 키. 기종 추가/삭제가 자동 반영된다."""
    return list(DRONES)


def drone_order(preferred=()) -> list[str]:
    """`preferred` 로 **앞머리 순서만** 고정하고, 레지스트리의 나머지는 등록 순서로 뒤에 붙인다.

    왜 이 형태인가: 파일마다 기존 정렬 근거(크기순·target_extent 순·그림 배치)가 서로 달라
    한 정렬로 통일하면 기존 그림 순서가 전부 바뀐다. `preferred` 에 그 파일의 기존 5종 순서를
    그대로 주면 **기존 배치는 보존되고 신규 기종만 뒤에 자동 추가**된다 — 목록이 낡지 않는다.
    preferred 에 레지스트리에 없는 키가 있으면 조용히 무시한다(기종을 지워도 안 죽는다)."""
    head = [k for k in preferred if k in DRONES]
    return head + [k for k in DRONES if k not in head]


#  표시명에서 떼는 제조사 접두어. 기존 5종은 `name.replace("DJI ", "")` 규약으로 만든 라벨
#  ("Mini 5 Pro" · "Mavic 4 Pro" · "Matrice 4E" · "S1000+" · "Phantom 4")을 쓰고 있었고,
#  비-DJI 기종이 들어오면서 그 규약이 제조사별로 갈라졌다 → 한 군데로 모은다.
_VENDOR_PREFIXES = ("DJI ", "Yuneec ", "Holybro ")


def drone_label(key: str) -> str:
    """그림·표용 짧은 표시명. **손으로 적은 이름 사전 금지** — DroneSpec.name 에서 유도한다.
    (기존 5종의 결과 문자열은 옛 `_NAME`/`DRONE_LABEL` 사전과 **완전히 같다**.)"""
    nm = DRONES[key].name.split("  ")[0]
    for p in _VENDOR_PREFIXES:
        if nm.startswith(p):
            return nm[len(p):]
    return nm


#  ⚠⚠ **기종색은 재질색과 다른 팔레트다.** 저장소 규약의 "5색 = 순수 재질"은 아래
#     `MATERIAL_COLOR`(plastic/carbon/metal/camera_assembly/pcb) 이야기이고, 기종별 선 색은
#     그것과 **무관한 별개 팔레트**다. 둘을 섞으면 재질 그림의 '색=재질' 규약이 깨진다.
#     그래서 기종색은 여기서 **개수만** 유도하고, 색상 자체는 각 그림 모듈이 자기 팔레트를 준다.
#  Okabe-Ito 색맹안전 8색(기본 순환) — 앞 5색은 viz_report13 이 이미 쓰던 순서와 같다.
DRONE_CYCLE_OKABE_ITO = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00",
                         "#56B4E9", "#F0E442", "#000000")


def drone_cycle_map(cycle, order=None) -> dict:
    """기종 → 순환 팔레트 원소. `order` 는 `drone_order(...)` 결과(없으면 등록 순서).
    팔레트가 기종 수보다 짧으면 **되감는다**(색이 겹칠 수는 있어도 KeyError 로 죽지 않는다)."""
    keys = list(order) if order is not None else drone_keys()
    return {k: cycle[i % len(cycle)] for i, k in enumerate(keys)}


# 부위(그룹) → (재질키, 한글설명).  **재질 정의는 materials.MATERIALS 가 유일한 진리원**이고,
#   Sionna RT(전파)와 PO(RCS)가 **둘 다 거기서 읽는다**. 여기선 '어느 부위가 어느 재질인가'만 정한다.
#   색은 build_drone 가 스펙에서 직접 지정(전파물성과 무관).
DRONE_GROUP_MAT = {
    "body":    ("plastic",         "동체 셸"),
    "canopy":  ("plastic",         "상단 캐노피/배터리"),
    "arm":     ("carbon",          "암"),
    "motor":   ("metal",           "모터"),
    "prop":    ("prop_plastic",    "프로펠러"),
    "gear":    ("plastic",         "착륙장치"),
    "camera":  ("camera_assembly", "짐벌 카메라(금속 하우징+유리렌즈)"),
    "accent":  ("plastic",         "전방 식별색"),
    "battery": ("metal",           "배터리팩(내부) — GHz 에서 파우치 포일은 사실상 금속"),
    "pcb":     ("pcb",             "ESC/메인보드(내부) — FR-4 + 구리 그라운드플레인"),
    # --- 열린 프레임(open-frame) 전용 그룹 (2026-07-30) ---
    #  ⚠ 새 그룹은 **세 곳에 다 등록해야** 한다: 여기 · drone_cad 의 union 목록 ·
    #    gazebo_export.DENSITY. 하나만 빠지면 조용히(또는 이제는 요란하게) 틀린다.
    "deck":    ("carbon",          "카본 데크(상·하판 + 스탠드오프) — 셸 없는 열린 프레임"),
    "gear_cf": ("carbon",          "카본 튜브 착륙장치 — 'gear'(플라스틱)와 재질이 다르다"),
    "fc":      ("pcb",             "비행제어기(Pixhawk 류) — 상판 위 노출"),
}
#  ⛔ deck·gear_cf 를 rcs_sbr 의 '유전체 셸'로 선언하면 안 된다 — carbon |Γ|=0.90 은 **불투명**이고
#     rcs_sbr._resolve_shells 가 SHELL_GAMMA_MAX=0.5 로 즉시 예외를 던진다(의도된 가드).
#     열린 프레임은 shell_groups=() 로 넘긴다.
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


def motor_radii(spec: DroneSpec) -> list[float]:
    """모터(=암) **중심반경**[m] 목록 — `motor_angles` 와 같은 순서·같은 길이.

    `spec.rotor_r_mm` 이 있으면 그대로(사다리꼴 배치), 없으면 전 로터가 `diagonal_mm/2` 원 위에
    있다(기존 규약). 이 함수가 로터 반경의 **유일한 출처**다 — `rotor_layout`(프롭 위치)과
    `drone_cad.build_frame_cad`(암·모터·다리)가 둘 다 여기서 읽는다.
    ⚠ 예전에는 `r = diagonal_mm/2` 가 두 파일에 따로 적혀 있었다. 한쪽만 사다리꼴을 알면
      프롭이 모터 위가 아니라 허공에 앉는데 **예외는 나지 않는다** — 그래서 한 군데로 모은다."""
    angs = motor_angles(spec)
    rr = getattr(spec, "rotor_r_mm", None)
    if rr is None:
        return [spec.diagonal_mm / 2000.0] * len(angs)
    if len(rr) != len(angs):
        raise ValueError(
            f"motor_radii: rotor_r_mm 길이 {len(rr)} 가 로터 수 {len(angs)} 와 다르다 "
            f"(key={spec.key!r}). rotor_deg 와 **같은 순서·같은 길이**여야 한다.")
    return [float(v) / 1000.0 for v in rr]


#  열린 프레임(튜브 암)에서 **모터 캔(벨)이 시작하는 z** [m] — 암 중심선 기준.
#  ⭐ Holybro X500 V2 제조사 STEP 모서리(1D) 실측: 암 축 y_step 16.0, 카본 모터마운트 판 윗면
#  y_step 22.0(= z 6.0), OD 27.7 캔이 y_step 23.5 부터 시작 → 캔 바닥 = 판 위 1.5 mm = **z 7.5**.
#  ⚠ drone_cad.X500V2["motor_bell_z_mm"][0] 과 **같은 값**이어야 한다 — 어긋나면 프롭이
#    모터 위가 아니라 공중에 뜨는데 예외는 안 난다. drone_cad._x500v2_arm_tip 이 대조 검사한다.
OPEN_MOTOR_BASE_M = 0.0075


def _arm_motor_dims(spec: DroneSpec, diag: float) -> tuple[float, float, float]:
    """(arm_t, motor_h, prop_z) [m] — 암 두께 · 모터 벨 높이 · **프롭 장착 z**.

    기본은 **대각 비례**(접이식 소비자기 5종에서 역산한 옛 법칙)이고, 스펙에 실측 부품치수
    (`arm_od_mm` / `motor_h_mm`)가 있으면 그쪽이 이긴다 — drone_cad 의 오버라이드와 **같은 규약**.
    ⚠ 이 식은 예전에 `rotor_layout` 과 `frame_fit_scale` 두 곳에 따로 적혀 있었다. 한쪽만
      오버라이드를 받으면 프롭 장착 높이가 모터 벨 높이와 따로 놀아 **프롭이 공중에 뜬 메쉬**가
      에러 없이 나온다 → 식을 여기 하나로 모은다.

    ⭐ 2026-07-30: 튜브 암(열린 프레임)은 **다른 식**을 쓴다. 셸형은 모터가 암 중심선에서
      시작하지만, 열린 프레임의 모터는 암 위에 얹힌 **모터마운트 판** 위에 앉는다. 옛 식을
      그대로 쓰면 X500 V2 의 프롭이 모터 캔 꼭대기보다 7 mm 위에 떠 있었다(렌더로 확인).

    ⭐⭐ 2026-08-07 (C1·C2 / P1·P2) — **프롭 장착 z 를 벨 윗면에서 유도한다.**
      [옛 식] `prop_z = motor_h + arm_t/2 + 0.006`.  그 6 mm 와 arm_t/2 는 어떤 실측에도
        닿아 있지 않은 **집안 규칙**이었고, 벨이 실제로 어디서 시작하는지(drone_cad.MOTOR_BASE_Z)를
        **한 번도 읽지 않았다**. 그래서 벨을 움직여도 프롭은 제자리였고, 어긋나도 예외가 안 났다.
        실측: 프롭이 벨 위 3.6~13.2 mm 에 떠 있었다(outputs/meshdef_prop_gap.json).
      [새 식] `prop_z = drone_cad.motor_bell_top_z_m(spec, diag) + PROP_STANDOFF_M[key]`.
        벨 높이도 이제 `drone_cad.motor_bell_h_m` 하나뿐이다 — 여기 있던 0.045·diag 는
        drone_cad 의 0.048·diag 와 **다른 값**이었고(mavic4pro 에서 1.32 mm), 그 차이가
        그대로 간격에 실렸다.
      ⚠ 이 함수가 돌려주는 `motor_h` 도 이제 그 단일 출처 값이다(0.048·diag 계열).
        `arm_t` 는 더 이상 프롭 높이에 안 쓰인다 — 암 두께로만 남는다."""
    from drone_cad import (motor_bell_h_m, motor_bell_top_z_m,      # noqa: E402  (순환 import 회피)
                           PROP_STANDOFF_M)
    arm_t = (0.08 if spec.fixed_arm else 0.045) * diag
    motor_h = motor_bell_h_m(spec, diag)
    if getattr(spec, "arm_od_mm", None) is not None:
        arm_t = float(spec.arm_od_mm) / 1000.0
    if getattr(spec, "arm_shape", "folding") == "tube":
        #  ⭐ 2026-08-04 — 캔 위 클리어런스 0.8 → **2.0 mm**. 프롭이 앉는 면은 제조사 STEP 의
        #    프롭어댑터 플랜지(y_step 53.08~54.0 → z 37.1~38.0)다. 캔이 z 7.5~36.0 으로
        #    정정되면서 prop_z 를 38.0 mm 로 유지하려면 클리어런스가 2.0 이어야 한다.
        #    (안 고치면 프롭이 1.2 mm 내려앉아 캔 꼭대기에 파묻히고, 프롭 루트가 불리언
        #     합집합에서 캔에 먹힌다 — 예외는 안 난다.)
        #    ⚠ 이 분기는 arm_shape=='tube' 전용이고 현재 그 기체는 x500v2 뿐이다.
        return arm_t, motor_h, OPEN_MOTOR_BASE_M + motor_h + 0.002
    return arm_t, motor_h, motor_bell_top_z_m(spec, diag) + PROP_STANDOFF_M.get(spec.key, 0.0)


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
def _build_frame_raw(spec: DroneSpec, mesh_fix=None) -> Mesh:
    """(내부) 외형보정 **전** 프레임 — CAD(trimesh+manifold3d 로프트/불리언) 단일 경로.
    (예전 프리미티브 조립 legacy 경로는 2026-07-20 제거 — git 히스토리에만 남음.)

    mesh_fix : ⭐선택 메쉬 수리 스위치. 기본 None = **끔** = 예전 메쉬와 비트동일.
        id 는 `geom.MESH_FIX_KNOWN`/`drone_cad.MESH_FIX_TOKENS`(예: 'battery')."""
    from drone_cad import build_frame_cad
    return build_frame_cad(spec, mesh_fix=mesh_fix).to_geom()


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


def _fit_cache_key(spec: DroneSpec):
    """`_FIT_CACHE` 의 캐시 키 — **spec 전체**(모든 필드)다. `spec.key` 만 쓰면 안 된다.

    ⚠ 2026-07-30 (Phase 3) 정정: 예전엔 `spec.key` 하나가 캐시 키였다. 그런데
      `dataclasses.replace(spec, envelope_mm=...)` 로 만든 **같은 key·다른 외형**의 변종을
      쓰는 호출부가 실재한다(`benchmark/compare_real_cad.ours_body_only` — 실물 CAD 바운딩박스로
      외형을 갈아끼운다). 그러면 먼저 계산된 쪽 배율이 뒤쪽에 **조용히 재사용**돼 엉뚱한
      크기의 메쉬가 나오고 **예외는 안 난다**. 그 호출부가 `_FIT_CACHE.pop(key)` 로 손수
      막고 있었는데, 그건 순서를 아는 사람만 지킬 수 있는 규약이다.
      → 캐시 키를 spec 전체로 바꿔 **구조적으로 불가능**하게 만든다. 레지스트리 7종은
        key ↔ spec 이 1:1 이므로 결과·성능 모두 그대로다(빌드 지문으로 확인)."""
    return tuple(getattr(spec, f) for f in _SPEC_FIELDS)


def frame_fit_scale(spec: DroneSpec, mesh_fix=None) -> tuple[float, float, float]:
    """프레임을 공식 외형(spec.envelope_mm)에 맞추는 축별 배율 (sx, sy, sz).
    envelope_mm 이 없거나 해당 축이 None 이면 그 축 배율은 1.0.

    ⚠ 수리 스위치는 **캐시 키에 들어간다**. 수리가 바운딩박스를 바꾸는 경우(예: 묻힌 부품을
    빼는 수리) 캐시가 남의 배율을 조용히 물려주면 «엉뚱한 크기의 메쉬 + 예외 없음» 이 된다 —
    이 저장소가 2026-07-30 에 이미 한 번 걸린 함정이다(_fit_cache_key 주석).
    ⭐ 키에는 **전역 스위치(MESH_FIX)까지** 넣는다. 이 함수가 안 읽는 수리(cadkit 의 i5 등)도
    프레임 형상을 바꿀 수 있어서다 — 스위치 상태가 다르면 캐시 칸도 달라야 한다.
    스위치가 하나도 안 켜져 있으면 키 모양이 예전 그대로라 기존 동작과 비트동일이다."""
    from drone_cad import normalize_mesh_fix
    from geom import mesh_fix_set
    fix = normalize_mesh_fix(mesh_fix)
    _sw = frozenset(mesh_fix_set()) | (fix if mesh_fix is not None else frozenset())
    _ck = _fit_cache_key(spec) if not _sw else (_fit_cache_key(spec), _sw)
    if _ck in _FIT_CACHE:
        return _FIT_CACHE[_ck]
    env = spec.envelope_mm
    if not env:
        _FIT_CACHE[_ck] = (1.0, 1.0, 1.0)
        return _FIT_CACHE[_ck]
    import numpy as _np
    V = _np.asarray(_build_frame_raw(spec, mesh_fix=fix).v, float)
    ext = (V.max(0) - V.min(0)) * 1000.0                  # 현재 바운딩박스 [mm]
    s = []
    for i in range(3):
        tgt = env[i]
        s.append(1.0 if (tgt is None or ext[i] <= 1e-9) else float(tgt) / float(ext[i]))

    # ⚠ 공식 높이가 **프롭 포함**인 기체는 프레임만 맞추면 프롭이 위로 더 올라가 총높이가 초과된다
    #   (mini5pro: 프레임을 91 mm 에 맞췄더니 전체 106 mm = +16.5%). 프롭 포함으로 다시 푼다:
    #     total(sz) = (프롭 장착z_raw + |프레임 바닥z_raw|)·sz + 프롭 자체 반두께
    #   → sz = (목표 − 프롭반두께) / (장착z_raw + |바닥z_raw|)
    if getattr(spec, "env_props_included", False) and env[2] is not None:
        diag, r, prop_r, bh, body_l, body_w, body_z = _drone_dims(spec)
        arm_t, motor_h, prop_z = _arm_motor_dims(spec, diag)        # rotor_layout 과 **같은 함수**(raw)
        zoff = spec.rotor_z_mm or ((0.0,) * spec.num_rotors)
        pm_raw = max(prop_z + float(z) / 1000.0 for z in zoff)      # 최상단 장착 z [m]
        Pv = _np.asarray(build_propeller(spec).v, float)
        prop_half = float(Pv[:, 2].max()) * 1000.0                 # 프롭 최상단 − 장착중심 [mm]
                                                                   #   (허브가 위로 비대칭이라 반두께가 아니다)
        fbot = abs(float(V[:, 2].min())) * 1000.0                  # 프레임 바닥 |z| [mm]
        denom = pm_raw * 1000.0 + fbot
        if denom > 1e-9:
            s[2] = max(1e-6, (float(env[2]) - prop_half) / denom)

    _FIT_CACHE[_ck] = tuple(s)
    return _FIT_CACHE[_ck]


def build_frame(spec: DroneSpec, mesh_fix=None) -> Mesh:
    """**회전하지 않는 부분**: 동체/캐노피/암/모터/착륙장치/카메라/액센트 (프로펠러 제외).
    드론 로컬 프레임(전방 +x). 바운딩박스는 **공식 외형(envelope_mm)과 일치**한다.
    pose_articulated 에서 몸체 자세를 통째로 적용한다.

    mesh_fix : ⭐선택 메쉬 수리(기본 None = 끔 = 예전 메쉬와 비트동일).
        `drone_cad.MESH_FIX_TOKENS` 참조 — 예 build_frame(spec, mesh_fix='battery').
        ⚠**여러 수리를 함께 켤 때는 환경변수 `MESH_FIX` 를 쓸 것** — 인자는 drone_cad 담당
        수리만 켠다(cadkit 의 i5·geom 의 m6 는 환경변수만 읽는다). drone_cad 머리말 참조."""
    m = _build_frame_raw(spec, mesh_fix=mesh_fix)
    sx, sy, sz = frame_fit_scale(spec, mesh_fix=mesh_fix)
    return m if (sx, sy, sz) == (1.0, 1.0, 1.0) else m.scaled(sx, sy, sz)


def _mirror_y(m: Mesh) -> Mesh:
    """y→−y 거울상. 반사는 행렬식이 −1 이라 **면 winding 을 뒤집어야** 법선이 바깥을 유지한다.
    (PO·SBR 은 조명면 판정을 n̂·û>0 으로 하므로 법선이 뒤집히면 산란이 통째로 틀린다.)"""
    out = Mesh(m._group)
    out.v = [(x, -y, z) for (x, y, z) in m.v]
    out.f = [(a, c, b) for (a, b, c) in m.f]         # winding 반전
    out.g = list(m.g)
    return out


def build_propeller(spec: DroneSpec, n: int = 10, mirror: bool = False,
                    blade_law: str | None = None, pitch_law=None,
                    max_edge_m=None, lambda_m=None, edge_over_lambda: float = 10.0) -> Mesh:
    """프로펠러 1개 — **진짜 익형(NACA-4, 캠버 포함)** 로프트 블레이드 + 허브 (CAD 단일 경로).
    n 은 블레이드 스팬 분할 힌트(마이크로도플러는 크게 줘서 단면을 촘촘히).
    pose_articulated 가 이 메쉬를 z회전(스핀)시켜 각 로터에 배치한다.

    mirror : **반대 회전방향(CCW) 프롭**. 실물 멀티로터는 CW/CCW 프롭이 서로 **거울상**이다
             — 스윕 방향과 피치 부호가 함께 뒤집힌다. 옛 코드는 한 메쉬를 z회전으로만 복제해
             네 로터가 전부 같은 손잡이였다(2026-07-28 수정). 산란 패턴 지표에 유의미하다.
             ⚠ DJI 는 기종별 절대 회전방향을 공개하지 않는다(docs/drone_specs_2026.json
               rotor_directions '미확인'). 여기서는 `rotor_layout` 의 dir(대각쌍 동일) 관례를 따른다.

    ⭐ 2026-08-16 — 날 법칙을 고르는 손잡이가 붙었다(감사 §⑤ 3층). **기본은 예전 그대로**:
      blade_law  'legacy'(기본) / 'dji_mini2'  — 시위 분포 + 기종별 c_max/R + 뭉툭한 팁
                 / ⭐'per_airframe' — **그 기체의 순정 프롭**(평면형·c_max/R 을 둘 다
                   `PROP_LAW_0816` 에서 꺼낸다). 서술: docs/MESH_AUDIT_0816.md §⑦
      pitch_law  None(=legacy) / 'dji_mini2'   — ⚠기본으로 안 켜진다(감사 I7)
      lambda_m   파장[m]. 주면 λ/`edge_over_lambda` 보다 긴 삼각형 모서리만 쪼갠다(형상 불변)
    인자를 안 주면 나오는 메쉬는 **비트 단위로 예전과 같다**
    (증명: benchmark/regress_blade_law_bitidentical.py ·
     per_airframe 의 실현 충실도: benchmark/verify_prop_law_per_airframe_0816.py)."""
    from drone_cad import build_propeller_cad
    m = build_propeller_cad(spec, n_sec=max(12, n * 2), blade_law=blade_law,
                            pitch_law=pitch_law, max_edge_m=max_edge_m,
                            lambda_m=lambda_m, edge_over_lambda=edge_over_lambda).to_geom()
    return _mirror_y(m) if mirror else m


def rotor_layout(spec: DroneSpec) -> list[dict]:
    """로터별 배치: {center:(x,y,z), base_ang:deg(장착 오프셋), dir:+1/-1(CCW/CW)}.
    dir 은 인접 로터가 반대로 도는 멀티로터 관례(대각쌍 동일). build_drone 과 동일 좌표."""
    diag, r, prop_r, bh, body_l, body_w, body_z = _drone_dims(spec)
    arm_t, motor_h, prop_z = _arm_motor_dims(spec, diag)   # 실측 부품치수가 있으면 대각비례를 덮는다
    sx, sy, sz = frame_fit_scale(spec)            # 프레임과 **같은** 외형보정 배율
    zoff = spec.rotor_z_mm or ((0.0,) * spec.num_rotors)
    radii = motor_radii(spec)                     # 로터별 반경(사다리꼴 기체) — 단일 출처
    out = []
    for k, ang in enumerate(motor_angles(spec)):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        r = radii[k]
        dz = float(zoff[k]) / 1000.0 if k < len(zoff) else 0.0   # 로터별 z 오프셋(프롭 디스크 겹침 회피)
        out.append(dict(center=(r * ca * sx, r * sa * sy, (prop_z + dz) * sz),
                        base_ang=ang + 12.0, dir=(1 if k % 2 == 0 else -1)))
    return out


def frame_envelope_mm(spec: DroneSpec) -> dict:
    """진단용: 이 스펙이 만드는 프레임의 실제 외형/대각선을 재서 공식값과 비교한다."""
    import numpy as _np
    V = _np.asarray(build_frame(spec).v, float)
    ext = (V.max(0) - V.min(0)) * 1000.0
    W = _np.asarray(build_drone(spec).v, float)
    ext_full = (W.max(0) - W.min(0)) * 1000.0                  # 프롭 얹은 전체 드론
    C = _np.array([r["center"] for r in rotor_layout(spec)], float)
    diag_eff = 2.0 * float(_np.linalg.norm(C[:, :2], axis=1).mean()) * 1000.0
    #  ⭐ 2026-07-31 — 사다리꼴 배치(rotor_r_mm)에서는 위의 `2·평균반경` 이 **휠베이스가 아니다**.
    #    휠베이스의 정의는 '마주보는 로터 사이 거리' 이므로 그대로 잰 값을 따로 낸다.
    #    (한 원 위 배치에서는 둘이 같으므로 기존 기종의 숫자는 변하지 않는다.)
    n = len(C)
    opp = [float(_np.linalg.norm(C[k, :2] - C[(k + n // 2) % n, :2])) * 1000.0
           for k in range(n)] if n >= 2 else [0.0]
    wheelbase_mm = float(_np.mean(opp))
    # 프롭 디스크 엔벨로프 — 정적 메쉬 bbox 는 블레이드 방위에 따라 달라지므로(2날은 선이지 원반이 아니다)
    # '프롭 포함' 공식 L/W 와 견줄 값은 회전 디스크 기준이다.
    pr = spec.prop_dia_mm / 2.0
    disc_mm = (2.0 * (float(_np.abs(C[:, 0]).max()) * 1000.0 + pr),
               2.0 * (float(_np.abs(C[:, 1]).max()) * 1000.0 + pr))
    # 공식 치수가 **프롭 포함**이면 전체 드론을, 아니면 프레임을 공식값과 견준다.
    cmp_mm = ext_full if getattr(spec, "env_props_included", False) else ext
    return dict(lwh_mm=tuple(map(float, ext)), lwh_full_mm=tuple(map(float, ext_full)),
                lwh_compare_mm=tuple(map(float, cmp_mm)),
                official_includes_props=bool(getattr(spec, "env_props_included", False)),
                prop_disc_lw_mm=disc_mm,
                # ⚠ 2026-07-31 — 공식 외형치수는 **축별로 없을 수도, 통째로 없을 수도** 있다.
                #   x500v2 는 Holybro 가 대각선(500 mm)만 내고 L/W/H 를 안 내서 통째로 None 이다.
                #   소비자들은 `off[i] is not None` 만 검사하고 있어서 x500v2 에서 TypeError 로 죽었다
                #   (원소는 검사하고 그릇은 안 봤다). 여기서 **항상 3-튜플**로 정규화해 소비자 쪽
                #   분기를 없앤다 — 없는 축은 None 이고, 그건 "미공개" 라는 사실이지 결함이 아니다.
                official_mm=tuple(spec.envelope_mm) if spec.envelope_mm is not None
                            else (None, None, None),
                diagonal_spec_mm=spec.diagonal_mm, diagonal_effective_mm=diag_eff,
                wheelbase_opposite_mm=wheelbase_mm,
                rotor_radii_mm=[float(v) * 1000.0 for v in motor_radii(spec)],
                fit_scale=frame_fit_scale(spec))


def build_drone(spec: DroneSpec, mesh_fix=None) -> Mesh:
    """정적 멀티로터 메쉬(프레임 + 프로펠러 초기위상). **기존과 동일 출력**(report1/2 RCS 호환).
    = build_frame + 각 로터에 build_propeller 를 초기위상(스핀 0)으로 배치.

    mesh_fix : ⭐선택 메쉬 수리(기본 None = 끔 = 예전 메쉬와 비트동일). 프로펠러는 프레임과
        별개 경로라 이 스위치가 안 닿는다(프롭 쪽 손잡이는 blade_law/pitch_law 다)."""
    m = build_frame(spec, mesh_fix=mesh_fix)
    # ⚠ 명명 규약: rotor_layout 의 dir 은 **+1 = CCW / −1 = CW** 다(그 docstring 참조).
    #   2026-07-28 최초 판은 dir>0 에 prop_cw 를 줘서 **이름이 반대**였다(적대검증 지적).
    #   물리적으로는 기체 전체가 거울상이 될 뿐이고 DJI 는 절대 회전방향을 공개하지 않지만,
    #   우리 문서 규약과 코드가 어긋나면 안 되므로 바로잡는다.
    prop_ccw = build_propeller(spec)                    # 기준 형상을 CCW 로 둔다
    prop_cw = build_propeller(spec, mirror=True)        # 반대 회전 로터는 거울상
    for rot in rotor_layout(spec):
        cx, cy, cz = rot["center"]
        M = translate(cx, cy, cz) @ rotate("z", rot["base_ang"])
        prop = prop_ccw if rot["dir"] > 0 else prop_cw
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
    prop_ccw = build_propeller(spec)                     # dir=+1(CCW) 기준 형상
    prop_cw = build_propeller(spec, mirror=True)         # dir=−1(CW) 는 거울상
    rl = rotor_layout(spec)
    if rotor_phase_deg is None:
        rotor_phase_deg = [0.0] * len(rl)
    for rot, ph in zip(rl, rotor_phase_deg):
        cx, cy, cz = rot["center"]
        M = B @ translate(cx, cy, cz) @ rotate("z", rot["base_ang"] + ph)
        out.merge((prop_ccw if rot["dir"] > 0 else prop_cw).transformed(M), group="prop")
    return out




MATERIAL_COLOR = {
    # 색 = 순수 재질 분류(2026-07-20 사용자 지시). 물리적으로 같은 재질이면 같은 색 —
    # 프로펠러는 몸체와 같은 플라스틱이라 같은 회색이다(색=재질). 단 날개가 더 얇아 |Γ| 만 0.25 로 보정(prop_plastic).
    # 5색 팔레트(2026-07-20 재선정): 재질 수가 적으니 상호 구분 최대화 —
    # 무채색 2(회/흑) + 파랑/주황/초록. 같은 계열 색(강청 vs 청록) 혼동 제거.
    "plastic":         (0.82, 0.82, 0.85),   # 밝은 회색 — 플라스틱(셸/캐노피/착륙장치/식별색/프로펠러)
    "carbon":          (0.09, 0.09, 0.10),   # 검정 — 탄소섬유(CFRP) 암
    "metal":           (0.30, 0.50, 0.85),   # 파랑 — 금속(모터·배터리 포일)
    "camera_assembly": (0.90, 0.50, 0.10),   # 주황 — 금속하우징+유리렌즈 복합체(별개 재질)
    "pcb":             (0.10, 0.60, 0.25),   # 초록 — FR-4+구리(별개 재질)
    "prop_plastic":    (0.82, 0.82, 0.85),   # = plastic 회색 (같은 재질; |Γ|만 얇은날개 0.25 보정)
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
    #  ⭐⭐ 2026-08-16 — **회귀 게이트를 여기에 배선한다**(감사 C2).
    #    `mesh_check.assert_ok()` 는 «상시 가동» 이라 적혀 있었지만 저장소 전체에 호출부가
    #    0 건이었다. 메쉬가 밖으로 나가는 문은 이 스크립트(OBJ 내보내기)뿐이므로 여기서
    #    막는다 — 검사에 걸린 메쉬는 **파일로 나가지 못한다.**
    #    ⚠ 이 게이트가 덮는 범위는 정직하게: 인메모리로 `build_drone()` 을 직접 부르는
    #      경로(RCS·렌더·마이크로도플러)는 이 문을 안 지난다. 그 경로까지 막으려면
    #      import 시점에 검사를 걸어야 하는데, 전 기종 검사가 ~35 초라 그렇게 안 한다.
    #    탈출구: MESH_GATE=off 로 끌 수 있다(끄면 경고를 크게 찍는다).
    if os.environ.get("MESH_GATE", "on").lower() in ("off", "0", "false", "no"):
        print("⚠⚠ MESH_GATE=off — 메쉬 검증 게이트를 끄고 내보낸다. "
              "여기서 나온 OBJ 는 검증되지 않은 메쉬다.")
    else:
        from mesh_check import assert_ok
        print("메쉬 검증 게이트(mesh_check.assert_ok) 실행 중 …", flush=True)
        assert_ok()
        print("메쉬 검증 게이트 통과 — 내보내기를 시작한다.\n")
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
