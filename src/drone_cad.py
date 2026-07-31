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


# --------------------------------------------------------------------------- #
#  블레이드 법칙 — **실물 참조 프롭 3종 측정에서 유도** (2026-07-28)
# --------------------------------------------------------------------------- #
#  근거 원장: outputs/reference_props.json  (생산자 benchmark/measure_reference_props.py)
#  측정 대상: Holybro 1345(13in) · 3DR Solo(10in) · Yuneec Typhoon H480
#  측정법: **원통 단면**(프로펠러 단면의 정식 정의). 평면절단은 스윕 큰 프롭에서 팁을 빗나가고
#          비폐곡면 어셈블리에서 폴리곤이 안 나와 못 쓴다.
#
#  ⚠ 이 값들은 **DJI 프롭의 참값이 아니다.** 저장소에 DJI 프로펠러 실물 기하는 하나도 없다
#    (Phantom 4 스캔에도 프롭이 없다). 같은 급 소형 프롭의 **대표값**이며, 세 CAD 모두
#    계측 스캔이 아니라 시뮬레이터용 CAD 다. 절대 σ 앵커는 계속 docs/DRONE_SPECS.md §4 의
#    실측 문헌에 의존해야 한다.
#
#  ⛔ **폐기된 옛 근거**: "chord_max 0.26R — 실물 1345 는 0.30R 이라 소비자용이 더 슬림".
#     0.30R 은 1345 STL 의 **bbox x-폭**(52.03/173.0)이지 시위가 아니다. 실측 시위는
#     1345 0.225R · Solo 0.273R 이라, 옛 주장은 방향까지 뒤집혀 있었다.

# 시위 분포 c(r/R)/c_max — 3DR Solo 측정(소비자용 쿼드 프롭, DJI 급에 가장 가까움)
#   ⚠ 옛 코드는 이 곡선을 tt(=루트~팁 정규화)에 걸어 피크가 r/R=0.396 에 있었다.
#     실측 피크는 Solo 0.275 · 1345 0.300 이라 **r/R 기준으로 다시 건다.**
CHORD_RR = (0.00, 0.070, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40,
            0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00)
CHORD_FRAC = (0.38, 0.45, 0.725, 0.868, 0.978, 0.989, 0.922, 0.865,
              0.760, 0.665, 0.577, 0.489, 0.403, 0.352, 0.10)
CHORD_MAX_OVER_R = 0.25       # 실측 Solo 0.273 · 1345 0.225 의 중간 (옛 0.26 은 bbox 유래)

# 국소 기하피치 분포 k(r/R) = P_local(r) / P_nominal — 3DR Solo 측정
#   실물 프롭은 **정피치가 아니다.** 공칭 피치는 ~0.5R 에서 맞는 기준값이고, 국소 피치는
#   루트에서 낮게 시작해 0.6~0.7R 에서 최대가 됐다가 팁에서 다시 떨어진다.
#   Solo 실측 국소피치[in]: 1.07(0.15R) 2.92(0.30) 4.50(0.50) 4.99(0.70) 4.56(0.80) 3.37(0.90)
#   ⛔ 옛 코드는 k≡1 (정피치)이라 θ(0.070R)=57.6~68.3° 라는 **물리적으로 불가능한 루트**를 만들었다.
#      실측 최대 트위스트: Solo 17.2° · 1345 20.2° · Typhoon 29.6° — 어느 실물도 30° 를 안 넘는다.
PITCH_RR = (0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40,
            0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00)
PITCH_K = (0.07, 0.08, 0.13, 0.238, 0.369, 0.516, 0.649, 0.751, 0.833,
           1.000, 1.106, 1.109, 1.013, 0.748, 0.732, 0.72)

# 두께비 t/c — 루트 → 팁. 실측 범위: 1345 5.9~9.3% · Solo 6.1~8.2% · Typhoon 8.6~12.8%
#   ⛔ 옛 값 9.2~13.5% 는 소비자용 프롭 셋 중 어느 것보다도 두꺼웠다.
TC_ROOT, TC_TIP = 0.095, 0.065

# 캠버(NACA-4 평균선) — 실측: 1345 8.32% · Solo 4.37% · Typhoon 6.80%,
#   피크 위치는 **셋 다 x/c ≈ 0.50**(0.49/0.52/0.51). p=0.5 면 평균선이 yc = 4m·x(1−x) 로 단순화된다.
#   ⛔ 옛 `_airfoil` 은 **대칭**이라 캠버가 정확히 0 이었고, docstring 은 그걸 "실제 프로펠러 단면"
#      이라고 불렀다. 실물 참조 셋이 전부 캠버를 갖는다.
#   RF 영향은 유계다(시위/λ ≤ 0.86, 캠버 곡률반경 0.17~1.23λ) — 방위평균 σ 로는 1 dB 미만.
CAMBER_M, CAMBER_P = 0.05, 0.50


def _airfoil(chord, thick_ratio=0.10, pts=40, camber_m=CAMBER_M, camber_p=CAMBER_P):
    """NACA-4 익형 단면(y=시위, z=두께). **캠버 포함**(camber_m=0 이면 대칭).

    두께는 표준 NACA-4 분포, 평균선은 표준 NACA-4 2구간 포물선.
    좌표는 평균선에 **수직**으로 두께를 얹는 정식 구성(단순 상하 오프셋이 아니다)."""
    t = float(thick_ratio)
    m, pp = float(camber_m), float(camber_p)
    x = (1 - np.cos(np.linspace(0, np.pi, pts // 2))) / 2          # 코사인 클러스터링(앞전 촘촘)
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2
                  + 0.2843 * x**3 - 0.1015 * x**4)
    if m > 0:
        yc = np.where(x <= pp,
                      m / pp**2 * (2 * pp * x - x**2),
                      m / (1 - pp)**2 * ((1 - 2 * pp) + 2 * pp * x - x**2))
        dyc = np.where(x <= pp,
                       2 * m / pp**2 * (pp - x),
                       2 * m / (1 - pp)**2 * (pp - x))
        th = np.arctan(dyc)
        xu, yu = x - yt * np.sin(th), yc + yt * np.cos(th)
        xl, yl = x + yt * np.sin(th), yc - yt * np.cos(th)
    else:
        xu, yu, xl, yl = x, yt, x, -yt
    up = np.c_[xu, yu]
    lo = np.c_[xl[::-1], yl[::-1]]
    P = np.vstack([up, lo[1:-1]]) * chord
    P[:, 0] -= chord * 0.30                                         # 시위 30% 를 원점(피치축)으로
    from shapely.geometry import Polygon
    return Polygon(P)


def _blade(R, root_frac=0.14, chord_max=CHORD_MAX_OVER_R, pitch_deg=20.0, twist_deg=13.0,
           sweep_frac=0.10, n_sec=22, n_pts=36, pitch_m=None):
    """**진짜 익형 프로펠러 블레이드 1장** — 로프트(테이퍼 + 워시아웃 트위스트 + 시미터 스윕).
    +x = 스팬. 익형 단면을 스팬을 따라 회전(피치)·축소(테이퍼)·후퇴(스윕)시키며 잇는다.
      chord_max : **R 에 대한 비율**(0.26 = 최대시위 0.26·R). ⚠ 절대길이를 넣지 말 것.
      pitch_m   : 프로펠러 **기하 피치**[m] (1회전 전진량). 주면 각 단면 피치각을
                  θ(r)=atan(P/(2πr)) 로 **물리적으로** 준다(모델별로 다름). None 이면
                  pitch_deg/twist_deg 의 선형 워시아웃(구버전)."""
    from shapely import affinity as aff
    r0 = root_frac * R
    xs = np.linspace(r0, R, n_sec)
    tt = (xs - r0) / (R - r0)
    rr = xs / R                                                      # ⭐ r/R (tt 가 아니다)

    # 시위 분포 — **r/R 기준** 실측 곡선(3DR Solo). 옛 코드는 tt 에 걸어 피크가 0.396R 이었다.
    c = np.interp(rr, CHORD_RR, CHORD_FRAC) * float(chord_max) * R
    if pitch_m is not None:
        # 국소 기하피치 분포 k(r/R) 를 곱한다 — 실물 프롭은 정피치가 아니다.
        k = np.interp(rr, PITCH_RR, PITCH_K)
        th = np.arctan(k * float(pitch_m) / (2 * np.pi * xs))
    else:
        th = np.radians(pitch_deg - twist_deg * tt)                 # 워시아웃(선형 근사, 구버전)
    yc = sweep_frac * R * np.sin(np.pi / 2 * tt)                    # 시미터 스윕

    rings = []
    for x, ci, ti, yi, rri in zip(xs, c, th, yc, rr):
        # 두께비 테이퍼(실측 대역 안) — 루트 9.5% → 팁 6.5%
        f = np.clip((rri - root_frac) / max(1e-9, 1.0 - root_frac), 0.0, 1.0)
        p = _airfoil(max(ci, 1e-4), thick_ratio=TC_TIP + (TC_ROOT - TC_TIP) * (1 - f))
        p = aff.rotate(p, np.degrees(ti), origin=(0, 0), use_radians=False)
        p = aff.translate(p, yi, 0.0)
        rings.append((float(x), p))
    return loft(rings, n_pts=n_pts, cap=True)


# --------------------------------------------------------------------------- #
#  열린 프레임 내부 산란체 — 실물 킷 부품치수를 **판 치수의 비율**로 적는다
# --------------------------------------------------------------------------- #
#  (가로, 세로, 높이) = (·L, ·W, ·gap).  앵커: Holybro X500 V2 Full Kit (판 144×144, 간격 28)
#    배터리 4S 5000 mAh LiPo      ≈ 145×43×25 mm  → (1.00, 0.30, 0.90) = 144.0×43.2×25.2
#    전원분배(PM02)+ESC 보드      ≈  45×30×12 mm  → (0.31, 0.21, 0.43) =  44.6×30.2×12.0
#    비행제어기 Pixhawk 6C(케이스) ≈  85×43×15 mm  → (0.59, 0.30, 0.54) =  85.0×43.2×15.1
#  ⚠ 비율은 X500 부품치수에 맞도록 **역산한 것**이다(비율 자체가 물리법칙은 아니다). 다른 열린
#    프레임에 그대로 쓰면 그 기체 부품과 어긋날 수 있다 — 그때는 스펙 필드로 승격할 것.
OPEN_BATTERY_FRAC = (1.00, 0.30, 0.90)
OPEN_ESC_FRAC = (0.31, 0.21, 0.43)
OPEN_FC_FRAC = (0.59, 0.30, 0.54)


# --------------------------------------------------------------------------- #
#  기종별 동체
# --------------------------------------------------------------------------- #
def _body_folding(L, W, H, nose_drop=0.18, tail_w=0.95, n_pow=2.9,
                  hw_f=None, hh_f=None, zo_f=None):
    """접이식 소비자기(미니/마빅/매트리스) 공용 눈물방울 동체.
    코는 좁고 살짝 처지고, 허리에서 가장 넓고, 꼬리는 완만히 좁아진다.

    ⭐ 2026-07-30 사진대조 라운드: 단면 법칙을 **인자로 뺐다**. 기본값은 옛 하드코딩 배열
      그대로라 안 주면 기존 메쉬와 **비트동일**하다. 실물 상면/측면 사진에서 반폭·반높이
      프로파일을 재면(예: matrice4e 는 최대폭 스테이션이 **중앙보다 앞**, 꼬리는 배터리 평면,
      코는 뭉툭) 그 값을 넣어 실루엣을 맞춘다.
      hw_f/hh_f : xs=(-0.50,-0.30,-0.05,0.18,0.38,0.50)·L 에서의 반폭/반높이 (W·H 대비 비).
      zo_f      : 같은 스테이션의 중심선 z 오프셋(H 대비 비). None 이면 nose_drop 규약."""
    xs = np.array([-0.50, -0.30, -0.05, 0.18, 0.38, 0.50]) * L
    hw = np.array(hw_f if hw_f is not None else (0.30, 0.46, 0.50, 0.44, 0.28, 0.10)) * W * tail_w
    hh = np.array(hh_f if hh_f is not None else (0.30, 0.46, 0.50, 0.46, 0.34, 0.16)) * H
    zo = np.array(zo_f if zo_f is not None
                  else (0.02, 0.01, 0.00, -0.04, -0.10, -nose_drop)) * H
    return smooth(loft(spline_sections(xs, hw, hh, zo, n_pow=n_pow, n_sec=30, n_pts=72),
                       n_pts=72), iters=4)


#  기종별 셸 형상표 — **사진 실측**으로 얻은 것만 여기에 넣는다(없으면 _SHELL_DEFAULT).
#    fl/fw/fh   : 셸 (길이,폭,높이) = spec.body_l/w/h_mm 대비 비율
#    ndrop/npow : _body_folding 의 nose_drop · 단면 초타원 지수
#    cx0/cfrac/cfh : _canopy 의 x0 · frac · 높이배율(bh 대비)
#    hubf       : 암 시작 반경 = hubf · max(bl,bw)
#    hw/hh/zo   : _body_folding 단면 법칙(None 이면 공용 눈물방울)
_SHELL_DEFAULT = dict(fl=0.62, fw=0.40, fh=0.45, ndrop=0.22, npow=2.9,
                      cx0=-0.06, cfrac=0.62, cfh=1.0, hubf=0.30,
                      hw=None, hh=None, zo=None)
#  암 단면비 — (h_ratio, c_ratio). 없으면 (1.35, 0.55) = 옛 하드코딩 값(기존 메쉬 비트동일).
_ARM_SECTION = {
    "matrice4e": (2.00, 1.00),   # 원형 튜브 (정사각 + 최대 모서리반경 → 원)
    "phantom4":  (0.98, 0.40),   # 셸 일체 납작 페어링 (폭 대비 높이 ≈0.49)
    #  Mini/Mavic — 사진의 암은 **거의 원통에 가까운 살짝 눌린 타원**(정면컷의 세로 두께가
    #  평면컷의 가로 폭의 0.75~0.80). h_ratio 1.55 → 높이 = 폭×0.775.
    "mini5pro":  (1.55, 0.72),
    "mavic4pro": (1.55, 0.72),
}
#  암 **폭**[mm] (뿌리, 끝). 없으면 대각비례(0.055/0.035·diag, 고정암은 0.085/0.060).
#  ⚠ matrice4e 는 여기 대신 스펙 필드 `arm_od_mm` 을 쓴다(등단면 원형 튜브).
_ARM_WIDTH = {
    "phantom4": (45.0, 30.0),
    #  ⭐ Mini 5 Pro — assets/photos/mini5pro/mini 5 pro_3.png(평면컷) **픽셀 실측**.
    #     축척 2.885 px/mm(앞뒤 모터 간격 440 px = 152.6 mm = 대각 275·cos 56.3°).
    #     암을 가로지르는 수직 절단의 현(chord) 13.5~16.3 px→mm 를 암 축과 y축이 이루는
    #     각으로 보정하면 **앞암 11.8 mm · 뒷암 12.2 mm** — 거의 등단면 12 mm 다.
    #     뿌리는 셸 페어링에 묻히므로 16.5(뿌리) → 11.6(끝) 로 완만한 테이퍼만 남긴다.
    #     ⛔ 옛 대각비례는 뿌리 30.2 · 끝 19.3 mm 로 **실측의 1.7~2.6배**였다(정면·평면 겹치기에서
    #        메쉬 암이 사진 암을 통째로 덮어버린 원인).
    "mini5pro": (16.5, 11.6),
    #  ⭐ Mavic 4 Pro — mavic 4 pro_2.png 정면컷의 암 두께 ≈19 mm 관측 + Mini 실측비 이전.
    #     Mini 의 실측 폭/대각 = 12.0/275 = 0.0436 을 같은 설계언어의 Mavic(441)에 적용하면
    #     19.2 mm 로, 사진 관측과 일치한다. **DERIVED**(Mini 실측의 스케일 이전).
    #     옛 대각비례는 뿌리 48.5 · 끝 24.4 mm 였다.
    "mavic4pro": (26.5, 18.5),
}
#  암 끝 아래 원뿔 다리(`_gear_arm_spikes`)의 길이[m]. 없으면 옛 하드코딩 0.072 (비트동일).
#  ⭐ matrice4e 0.079 = 2026-07-31 측면사진 실측. `assets/photos/matrice4e/matrice 4E_3.png` 는
#     앙각이 거의 0 이다(근/원 다리발 화면차 23 px → sin e ≈ 0.033) → 세로 픽셀이 곧 세로 mm 다.
#     축척은 공식 총높이 149.5 mm ↔ RTK 꼭대기 y=152 에서 발끝 y=459 까지 307 px → 0.487 mm/px.
#     landmark: RTK 꼭대기 152 · 셸 crown 197 · 셸 벨리 380 · 발끝 459
#       ⇒ RTK 돌출 21.9 · **셸 높이 89.1** · **벨리→발 38.5 mm** (합 149.5, 자기정합).
#     옛 메쉬는 같은 세 구간이 24.7 / 95.6 / 28.8 이었다 — 셸이 +7 %, 다리가 −25 %.
GEAR_SPIKE_H = {"matrice4e": 0.079}
_SHELL_SHAPE = {
    #  ⭐ Matrice 4E — assets/photos/matrice4e/ _5(상면)·_4(후면)·_3(측면) 실측.
    #     축척은 **프롭 팁-투-팁 438.5 px = 274 mm(공식)** 로 잡았고(0.6249 mm/px), 그 축척이
    #     공식 언폴드 폭 387.5·길이 307 을 각각 −0.03%/−2.5% 로 재현해 **교차검증**된다.
    #     동체 245.0 × 94.4 × ~105 mm  ← 옛 코드는 190.3 × 155.2 × 67.3 (폭 +64%, 길이 −22%).
    #     최대폭 스테이션이 중앙보다 **앞**(x=+0.18L)이고 꼬리는 배터리 평면(반폭 0.17)이며
    #     코는 뭉툭(0.12)하고 **살짝 들려** 있다(JSON silhouette 과 일치).
    #  ⭐ 2026-07-31 — fh 0.669 → 0.594. 측면사진 _3 은 앙각 ≈0 이라 세로 픽셀이 곧 세로 mm 다
    #     (근/원 다리발 화면차 23 px ⇒ sin e ≈ 0.033). 공식 총높이 149.5 mm ↔ 307 px 로 축척내면
    #     셸 crown(y=197)→벨리(y=380) 가 **89.1 mm** 이고 옛 값은 95.6 mm 였다.
    #     같은 사진이 벨리→발 38.5 mm 를 주므로 그만큼은 다리(GEAR_SPIKE_H)로 간다.
    #  ⭐ 2026-07-31 (2) — fw 0.263 → 0.2561. **위 주석의 94.4 와 코드가 어긋나 있었다.**
    #     `_body_folding` 은 반폭에 `tail_w=0.95` 를 곱하므로 셸 실폭 = 0.95·bw = 0.95·388·fw 다.
    #       fw=0.263 → 96.94 mm  (주석의 94.4 보다 +2.7%)
    #       fw=0.2561 → 94.40 mm ✓
    #     같은 표의 나머지 둘은 실측과 정확히 맞아 있었다(fl·307=245.0, fh·150=89.1) — fw 만
    #     tail_w 를 빼먹은 채 남아 있었다. mini5pro 는 이미 맞다(0.4095·181·0.95 = 70.42 ↔ 실측 70.4).
    #     [독립 검증] 축척이 필요 없는 **종횡비**로 재확인했다. 평면컷 _5 에서 셸(암 접합부 제외)은
    #       길이 370 px · 최대폭 143 px → 2.587.  주석값 245.0/94.4 = 2.595.  옛 코드 245.0/96.94 = 2.528.
    #     ⚠ IoU 로는 검증되지 않는다(효과가 잡음 바닥 아래다 — 1° 자세오차만으로 0.09 IoU).
    #        이 변경의 근거는 실측이지 IoU 가 아니다.
    "matrice4e": dict(fl=0.798, fw=0.2561, fh=0.594, ndrop=0.0, npow=3.2,
                      cx0=-0.16, cfrac=0.62, cfh=1.0, hubf=0.20,
                      hw=(0.17, 0.38, 0.445, 0.50, 0.44, 0.12),
                      hh=(0.42, 0.50, 0.48, 0.42, 0.32, 0.14),
                      zo=(0.00, 0.00, 0.00, 0.02, 0.045, 0.06)),
    #  ⭐ Phantom 4 — assets/photos/phantom4/ _5(상면)·_3(정면) 실측 + drone_specs_2026.json.
    #     동체 ~175 × 150 × 82 mm(상면은 모서리 둥근 정사각, 측면은 렌즈형).
    #     옛 코드는 179.5 × 191.1 × 101.9 → 폭 +27%·높이 +24% 라 "뚱뚱한 덩어리"가 됐고,
    #     그만큼 다리 높이를 잡아먹어 실물의 긴 아치가 짧아졌다.
    #     캐노피 돌출은 실물에 **없다**(배터리가 등판과 매끈하게 연속) → 낮고 넓게(cfh 0.5).
    "phantom4": dict(fl=0.605, fw=0.545, fh=0.418, ndrop=0.09, npow=3.4,
                     cx0=-0.10, cfrac=0.78, cfh=0.50, hubf=0.30,
                     hw=(0.34, 0.46, 0.50, 0.49, 0.42, 0.24),
                     hh=(0.30, 0.44, 0.50, 0.47, 0.36, 0.20),
                     zo=None),
    #  ⭐ Mini 5 Pro — assets/photos/mini5pro/ _3(평면컷)·_1(정면컷) 실측.
    #     축척은 **앞뒤 모터 간격 440 px = 152.6 mm**(= 대각 275 × cos 56.3°, 스펙 유도값)로
    #     잡았다(2.883 px/mm). 그 축척으로 재면 셸은 **150 × 80.4 × ~45 mm** 이고,
    #     이는 DJI 공식 **폴디드 157 × 95 × 68 mm**(프롭 제외)와 독립적으로 맞물린다:
    #       길이 150 ≲ 157(접힌 암이 셸 길이 안), 폭 80.4 + 접힌 암 양쪽 ≈ 95,
    #       높이 45 + 짐벌 매달림 ≈ 23  →  68.  ⇒ 사진축척이 교차검증된다.
    #     ⛔ 옛 값(fl 0.62 · fw 0.40 · fh 0.45 = 158 × 72.4 × 41 mm)은 폭이 −10% 였고,
    #        무엇보다 단면 법칙이 기수 반폭 0.10 이라 **뾰족한 어뢰코**였다. 실물 기수는
    #        어안 2 + 그릴 + 짐벌 요크가 얹히는 **뭉툭한 면**이고 허리~꼬리는 폭이 거의 일정하다.
    #     ⭐ 평면컷 **픽셀 프로파일**(2.885 px/mm, 몸통만 — 암이 섞이는 스테이션은 제외):
    #       y195 67.6 · y215~305 76.6→79.0 · y355~520 65→55(**허리**) · y525~610 58→(암) · y625 41.6
    #       ⇒ 실물 평면형은 매끈한 눈물방울이 아니라 **넓은 앞머리 + 잘록한 허리 + 뒤쪽 재확장**이다.
    #  ⭐⭐ 2026-07-31 재측정 — fl 0.612 → 0.541, fw 0.460 → 0.4095 (셸이 12 % 컸다).
    #     [무엇이 틀렸나] 옛 값의 축척 앵커는 "앞뒤 모터 간격 440 px = 152.6 mm"(대칭 배치에서
    #     역산한 값)였는데, 팁-중점법으로 다시 재면 그 간격은 **447.25 px** 이고 대칭 가정 자체가
    #     이번 라운드에 깨졌다(drones.py mini5pro note 의 사다리꼴 절).
    #     [새 축척] 공식 프롭포함 폭 380 mm ⇒ 앞 로터 좌우 간격 227.6 mm ↔ 692.7 px → 0.32858,
    #     뒤 165.6 mm ↔ 517.4 px → 0.32006 mm/px. 동체는 그 사이 → **0.3243 ± 0.004**.
    #       자기검사: 두 축척의 비 1.0266 이 같은 사진의 프롭 팁-투-팁 비 445.4/434.0 = 1.0263 과
    #       **0.03 % 로 일치**한다(전혀 다른 두 양이 같은 원근을 본다).
    #     [측정] 평면컷 _3 에서 셸 폭 217 px = **70.4 mm**, 길이 425 px = **137.8 mm**.
    #     [독립 검증] DJI 공식 **폴디드**(프롭 제외) 157 × 95 × 68 mm 와 맞물린다 —
    #       길이 137.8 + 짐벌 전방 돌출 ≈ 19 → 157 ✓,  폭 70.4 + 접힌 암 양쪽 ≈ 12+12 → 94.4 ≈ 95 ✓.
    #       옛 값(156 × 79.1)은 같은 검사에서 폭 79.1 + 24 = 103 > 95 로 **기하학적으로 불가능**했다.
    "mini5pro": dict(fl=0.541, fw=0.4095, fh=0.495, ndrop=0.18, npow=3.2,
                     cx0=-0.14, cfrac=0.70, cfh=0.55, hubf=0.30,
                     hw=(0.228, 0.392, 0.356, 0.500, 0.496, 0.278),
                     hh=(0.42, 0.48, 0.50, 0.48, 0.40, 0.26),
                     zo=None),
    #  ⭐ Mavic 4 Pro — assets/photos/mavic4pro/ _2(정면컷)·_4(3/4)·_3(배면) 실측 + 공식 폴디드.
    #     공식 폴디드(프롭 제외) 257.6 × 123.1 × 105.9 mm 에서 셸을 ~205 × 112 × 62 mm 로 잡는다
    #     (폭 112 + 옆에 접힌 암 ≈ 123, 높이 62 + 짐벌 볼 ≈ 106).
    #     ⛔ 옛 값(fw 0.40 = 156 mm)은 **폴디드 폭 123 mm 보다도 넓어** 기하학적으로 불가능했다
    #        — 접었을 때 셸이 폴디드 치수를 넘을 수는 없다. 이 모순이 정면컷의 '뚱뚱한 덩어리'
    #        실루엣의 직접 원인이다.
    "mavic4pro": dict(fl=0.620, fw=0.302, fh=0.460, ndrop=0.14, npow=3.1,
                      cx0=-0.06, cfrac=0.66, cfh=0.70, hubf=0.30,
                      hw=(0.38, 0.46, 0.50, 0.50, 0.44, 0.26),
                      hh=(0.46, 0.50, 0.50, 0.48, 0.42, 0.30),
                      zo=None),
}


def _canopy(L, W, H, x0=-0.10, frac=0.55):
    """상단 배터리 캐노피 — 낮고 평평한 돔(실물은 배터리가 등에 얹힌 모양)."""
    xs = np.array([-0.5, -0.2, 0.1, 0.42]) * L * frac
    hw = np.array([0.24, 0.44, 0.42, 0.20]) * W
    hh = np.array([0.10, 0.24, 0.22, 0.08]) * H
    zo = np.zeros(4)
    m = smooth(loft(spline_sections(xs, hw, hh, zo, n_pow=3.2, n_sec=20, n_pts=56), n_pts=56),
               iters=3)
    return mv(m, x=x0 * L, z=0.30 * H)


def _body_plate_stack(L, W, t_bot, gap, t_top, shape="rect", corner_r=None,
                      n_post=4, post_r=None, post_inset=0.72,
                      plate_seg=64, post_seg=12, chamfer=None, posts=True):
    """**열린 프레임 센터플레이트** — 하판 + 간격 + 상판 + 스탠드오프 기둥. (2026-07-30)

    s1000plus 의 원형 카본 상·하판 분기를 일반화한 것이다.
      shape="round" : 지름 L 의 원판 2장 (s1000plus. L=W 여야 한다)
      shape="rect"  : L×W 사각판 2장 (Holybro X500 류 사각 카본 데크)
    `gap` 은 **두 판의 마주보는 면 사이 빈 간격**이다(총높이 = t_bot + gap + t_top).
    기둥은 두 판의 **중심끼리** 잇는다(판 두께 안쪽까지 물린다 = 실물 스탠드오프).

    chamfer : ⭐ 2026-07-30 추가. **45° 코너 챔퍼의 직각변 길이[m]**(shape="rect" 전용).
      주면 판 외곽이 둥근사각이 아니라 **팔각형**이 된다 — Holybro X500 V2 의 실제 판 모양이고,
      그 챔퍼면이 곧 암이 빠져나오는 자리다(제조사 STEP 실측 22.95 mm). None 이면 옛 둥근사각.
    posts : False 면 스탠드오프 기둥을 만들지 않는다. X500 V2 는 상·하판을 잇는 것이
      **기둥이 아니라 네 모서리의 나일론 암 클램프**다(STEP BOM: 별도 스탠드오프 부품 없음) —
      기둥을 세우면 없는 부품이 생긴다. 기본 True 는 기존 호출부 보존용.

    ■ 왜 필요한가
      열린 프레임은 몰드 셸이 없다. 셸형 경로(`_body_folding` + `_canopy`)로 억지로 만들면
      **존재하지 않는 유전체 셸**이 생기고, 그 셸 치수의 비율로 놓이는 내부 산란체까지
      기준을 잃는다. 셸이 없다는 사실을 형상으로 표현할 수단이 필요하다.

    ■ 반환
      [상판, 하판, 기둥...] 순서 — **옛 s1000plus 코드와 같은 순서**여야 정점 인덱스가 같다.
      그룹은 붙이지 않는다(호출부가 s1000plus 는 'body', 열린 프레임은 'deck' 으로 넣는다).
      ⚠ 기둥은 실물이 알루미늄/나일론이라 카본('deck')과 |Γ| 가 다르다(0.90 ↔ ~1.0).
        면적 비중이 판보다 훨씬 작아 영향은 작을 것으로 보지만 **정량은 측정하지 않았다**.

    ⚠ z 좌표를 1 pm(1e-12 m)로 반올림한다. 부동소수 **결합순서**가 마지막 비트를 흔들어
      (실측: 0.084/2 + 0.006/2 = 0.045000000000000005 ≠ 0.045) 이 helper 로 갈아탄 기존
      기종의 **비트동일성**을 깨기 때문이다. 1 pm 는 물리적으로 무의미한 자리다."""
    z_top = round(gap / 2 + t_top / 2, 12)
    z_bot = round(-(gap / 2 + t_bot / 2), 12)
    post_h = round(z_top - z_bot, 12)                    # 중심-중심
    post_z = round(0.5 * (z_top + z_bot), 12)
    pr = float(post_r) if post_r is not None else 0.030 * min(L, W)
    out = []
    if shape == "round":
        Rp = L / 2.0
        out.append(cyl(Rp, t_top, center=(0, 0, z_top), seg=plate_seg))       # 상판
        out.append(cyl(Rp, t_bot, center=(0, 0, z_bot), seg=plate_seg))       # 하판
        rr = Rp * post_inset
        for a in np.linspace(0, 360, n_post, endpoint=False):
            out.append(cyl(pr, post_h, center=(rr * np.cos(np.radians(a)),
                                               rr * np.sin(np.radians(a)), post_z), seg=post_seg))
    elif shape == "octa":
        #  ⭐ 2026-07-30 (외형감사): S1000+ 의 센터플레이트는 **원판이 아니라 정팔각판**이다
        #    (탑뷰 제품사진에 직선 변 8개가 그대로 보인다). L = **맞변거리**(across flats).
        #    `cyl(seg=8)` 로는 못 만든다 — 그건 외접원 기준이라 맞변거리가 L·cos(22.5°) 로 줄고,
        #    변의 위상도 0° 에서 시작해 실물(맞변이 ±x·±y)과 45° 어긋난다.
        from shapely.geometry import Polygon as _Poly
        Rc = (L / 2.0) / np.cos(np.radians(22.5))          # 외접원 반경(꼭짓점까지)
        ang = np.radians(np.arange(8) * 45.0 + 22.5)       # 꼭짓점 = ±22.5°+45k → 맞변이 축과 평행
        oct_poly = _Poly(np.column_stack([Rc * np.cos(ang), Rc * np.sin(ang)]))
        for t, z in ((t_top, z_top), (t_bot, z_bot)):                          # 상판 → 하판
            p = trimesh.creation.extrude_polygon(oct_poly, float(t))
            p.apply_translation([0.0, 0.0, z - t / 2.0])
            out.append(p)
        rr = (L / 2.0) * post_inset
        for a in np.linspace(0, 360, n_post, endpoint=False):
            out.append(cyl(pr, post_h, center=(rr * np.cos(np.radians(a)),
                                               rr * np.sin(np.radians(a)), post_z), seg=post_seg))
    elif shape == "rect":
        if chamfer:
            from shapely.geometry import Polygon as _Poly
            a, b, c = L / 2.0, W / 2.0, float(chamfer)
            poly = _Poly([(a, b - c), (a - c, b), (-a + c, b), (-a, b - c),
                          (-a, -b + c), (-a + c, -b), (a - c, -b), (a, -b + c)])
        else:
            cr = float(corner_r) if corner_r is not None else 0.06 * min(L, W)
            poly = rounded_rect(L, W, cr, pts=64)
        for t, z in ((t_top, z_top), (t_bot, z_bot)):                          # 상판 → 하판
            p = trimesh.creation.extrude_polygon(poly, float(t))
            p.apply_translation([0.0, 0.0, z - t / 2.0])
            out.append(p)
        if posts:
            for sx in (+1, -1):                                                # 네 귀퉁이 스탠드오프
                for sy in (+1, -1):
                    out.append(cyl(pr, post_h, center=(sx * 0.5 * L * post_inset,
                                                       sy * 0.5 * W * post_inset, post_z), seg=post_seg))
    else:
        raise ValueError(f"_body_plate_stack: 모르는 shape={shape!r} ('rect'|'round')")
    return out


def _arm_folding(r_motor, ang_deg, arm_r0, arm_r1, hub_r, z0=0.0, z1=0.0, bend=0.10,
                 h_ratio=1.35, c_ratio=0.55):
    """접이식 암 — 허브에서 모터까지 **완만히 휘는 테이퍼 튜브**(단면은 둥근 직사각).

    단면은 sweep 의 로컬축에서 (폭 = 2·arm_r, 높이 = h_ratio·arm_r) 이고 모서리 반경은
    c_ratio·arm_r 이다. 폭은 수평(암에 수직), 높이는 연직이다.
      h_ratio : 높이/arm_r. **기본 1.35 는 옛 하드코딩 값** — 안 주면 기존 메쉬와 비트동일.
                실물 대조로 얻은 값: matrice4e 는 원형 튜브(2.0=정사각→모서리로 원형화),
                phantom4 는 셸 일체형 **납작 페어링**(0.98 = 폭의 절반 높이).
      c_ratio : 모서리 반경/arm_r. 1.0 이면 rounded_rect 가 0.49·min(w,h) 로 잘려 **원**이 된다.
    """
    from shapely import affinity as aff
    a = np.radians(ang_deg)
    p0 = np.array([hub_r * np.cos(a), hub_r * np.sin(a), z0])
    p1 = np.array([r_motor * np.cos(a), r_motor * np.sin(a), z1])
    mid = 0.5 * (p0 + p1) + np.array([0, 0, bend * np.linalg.norm(p1 - p0)])
    t = np.linspace(0, 1, 14)[:, None]
    path = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t ** 2 * p1     # 2차 베지에

    def prof(s):
        w = arm_r0 + (arm_r1 - arm_r0) * s
        return rounded_rect(w * 2.0, w * h_ratio, w * c_ratio, pts=32)
    return sweep(path, prof, n_pts=28)


def _arm_tube(r_motor, ang_deg, od, hub_r, z0=0.0, z1=0.0, n_pts=24, quad_segs=8):
    """**직선 등단면 원형 튜브 암** — 카본 파이프 그대로 (테이퍼 0, bend 0). (2026-07-30)

    `_arm_folding` 은 접이식 소비자기용이라 단면이 둥근 직사각이고 테이퍼·벤드가 붙는다.
    개발용 프레임의 암은 **그냥 파이프**다 — 그걸 테이퍼 튜브로 만들면 실루엣과 투영면적이
    둘 다 틀린다.

    ■ 왜 솔리드인가 (실물은 중공 파이프, 예: X500 V2 는 16 mm OD / 14 mm ID)
      · SBR/PO 는 외면만 본다 — 카본은 |Γ|=0.90 으로 불투명해 보어 안쪽까지 빛이 안 든다.
      · 보어를 뚫으면 **열린 관 끝**이 생겨 first-hit 이 관 내벽을 보고 가짜 산란을 만든다.
      ⚠ 대가: Gazebo 질량 배분에서 암 부피가 중공 대비 1/(1−(14/16)²) ≈ 4.3 배 과대다.
        총질량은 공식 TOW 로 정규화되므로 **분포**에만 영향이 있다(gazebo_export 참조)."""
    from shapely.geometry import Point
    a = np.radians(ang_deg)
    p0 = np.array([hub_r * np.cos(a), hub_r * np.sin(a), z0])
    p1 = np.array([r_motor * np.cos(a), r_motor * np.sin(a), z1])
    t = np.linspace(0, 1, 6)[:, None]
    path = (1 - t) * p0 + t * p1                                  # 직선
    circ = Point(0.0, 0.0).buffer(od / 2.0, quad_segs=quad_segs)  # 등단면 원
    return sweep(path, lambda s: circ, n_pts=n_pts)


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


def _gimbal_hasselblad(s, cx, cz, x_squash=0.86):
    """Mavic 4 Pro **v2** — 기수 **아래에 매달린** 큰 Hasselblad 짐벌 볼.

    실물(assets/photos/mavic4pro/mavic 4 pro_2.png 확대 · _4.png 3/4):
      · 검은 하우징은 **좌우로 넓고 앞뒤로 얕은 배럴**이다(정면폭 ≈ 동체 셸 폭의 85%).
      · 정면에 **큰 사각 메인렌즈 1개(위·중앙, 'HASSELBLAD' 각인) + 원형 보조 2개(아래)**.
      · 기수 셸이 볼의 **위쪽을 감싸 덮는**다 — 볼이 기수보다 앞으로 튀어나오지 않는다.
    좌표: +x=기수앞, y=좌우, z=상하.

    ⭐ 2026-07-30 버그 수정: `hous.apply_scale([...])` 는 **원점 기준** 배율이라 이미
      (cx, 0, cz) 로 옮겨둔 구를 x 로도 함께 이동시켰다(옛 1.05 → 하우징만 cx·1.05 로 밀림,
      렌즈는 안 밀림 → 하우징과 렌즈열이 미세하게 어긋난 채 유니온됐다). 원점에서 짓고
      배율을 건 뒤 옮기도록 순서를 바꾼다."""
    A = []
    # 롤축 요크(좌우 팔) — 하우징을 감싸 바디로 연결
    A.append(("camera", cyl(s * 0.26, s * 2.0, center=(cx - 0.15 * s, 0, cz), axis="y", seg=20)))
    hous = sphere(s * 0.95, subdiv=3)                 # 원점에서 짓고
    hous.apply_scale([x_squash, 1.00, 1.00])          # 중심 기준으로 눌러서
    hous.apply_translation([cx, 0.0, cz])             # 제자리로
    A.append(("camera", hous))
    # 정면 3렌즈 — 메인(사각) 위·중앙 + 보조 2개 아래. 앞(+x)면에 붙는다.
    cxl = cx + s * 0.95 * x_squash * 0.86
    A.append(("camera", box(s * 0.44, s * 0.68, s * 0.62, center=(cxl, 0, cz + s * 0.26))))  # 메인 사각통
    A.append(("camera", cyl(s * 0.26, s * 0.30, center=(cxl + s * 0.24, 0, cz + s * 0.26),
                            axis="x", seg=28)))                                              # 메인 유리
    for dy in (-0.30, 0.30):                                                                 # 보조 원형 2
        A.append(("camera", cyl(s * 0.24, s * 0.46, center=(cxl, dy * s, cz - s * 0.36),
                                axis="x", seg=26)))
        A.append(("camera", cyl(s * 0.17, s * 0.10, center=(cxl + s * 0.26, dy * s, cz - s * 0.36),
                                axis="x", seg=20)))
    return A


def _gimbal_compact3(w, h, d, cx, cz):
    """Mini 5 Pro — 기수 아래 **3축 소형 짐벌**. (2026-07-30 사진대조 라운드)

    실물 근거: assets/photos/mini5pro/mini 5 pro_1.png (정면 제품컷) · _2.png (3/4).
      · 검은 하우징이 **좌우로 넓다** — 기수 폭의 60% 남짓(사진 실측 ≈50 mm, 동체폭 ≈81 mm 대비).
      · 가운데에 **각진(원통 아닌) 렌즈통**이 앞으로 튀어나오고, 그 좌우로 롤축 요크 치크가 있다.
      · 하우징 **아래로 짧은 요(yaw) 원통**이 하나 더 내려온다.
    ⛔ 폐기된 옛 형상: `_gimbal_hanging(0.020, 0.021, 0.024, ...)` = 24×20×21 mm 상자 + 방진판.
       방진판(w·1.5 정사각)은 매달림 짐벌(Phantom)의 특징이지 Mini 의 것이 아니고,
       좌우폭이 실물의 **40%** 밖에 안 돼 정면 실루엣에서 짐벌이 사실상 보이지 않았다.

    인자는 `_gimbal_hanging` 과 같은 뜻이다 — w=좌우폭, h=높이, d=앞뒤깊이."""
    A = []
    for sy in (+1, -1):                                    # 롤축 요크 치크(좌우)
        A.append(("camera", box(d * 0.86, w * 0.19, h * 0.90,
                                center=(cx - d * 0.04, sy * 0.405 * w, cz))))
    A.append(("camera", box(d, w * 0.62, h, center=(cx, 0, cz))))            # 중앙 하우징
    A.append(("camera", box(d * 0.44, w * 0.42, h * 0.66,                    # 각진 렌즈통
                            center=(cx + d * 0.55, 0, cz))))
    A.append(("camera", cyl(h * 0.26, d * 0.22,                              # 렌즈 유리
                            center=(cx + d * 0.78, 0, cz), axis="x", seg=24)))
    #  ⭐ 2026-07-31 — 아래로 뻗던 **요(yaw) 원통**을 얕은 바닥 캡으로 바꾼다.
    #    [무엇이 틀렸나] 옛 형상은 cz − 0.83·h 까지 내려가 어셈블리 세로 실루엣을 선언 h 의
    #    1.73배로 만들었고, 그 결과 짐벌 밑면이 **착륙발보다 −8.2 mm 낮았다** — 기체가 카메라로
    #    착지한다는 뜻이고, `frame_fit_scale` 은 그 최저점을 기준으로 공식 높이 91 mm 를 맞추느라
    #    sz 를 1.247 로 올려 **셸까지 25 % 세로로 늘리고** 있었다(에러는 안 난다).
    #    [근거] 3축 짐벌의 요 축은 하우징 **위**(기수 안쪽)에 있다 — 아래로 내려오는 축은 없다.
    #    mini 5 pro_1.png 확대에서 하우징 밑에 보이는 것은 지름 ~20 mm·깊이 ~5 mm 의 둥근
    #    바닥 캡뿐이고, 그 아래로는 착륙다리가 더 내려간다.
    A.append(("camera", cyl(w * 0.20, h * 0.20,                              # 하우징 바닥 캡
                            center=(cx, 0, cz - h * 0.40), axis="z", seg=20)))
    A.append(("camera", box(d * 0.60, w * 0.42, h * 0.55,                    # 기수 안으로 물리는 마운트
                            center=(cx - d * 0.26, 0, cz + h * 0.62))))
    return A


def _nose_grille(cx, cz, w, h, d, n_fin=5, group="body"):
    """기수 정면의 **검은 핀 그릴**(Mini 5 Pro 앞면에서 가장 눈에 띄는 특징). (2026-07-30)

    실물 근거: mini 5 pro_1.png 확대 — 어안 2개 사이·짐벌 위에 세로 핀이 늘어선 큰 검은 사각창.
    ⚠ 그룹을 **'body'(플라스틱 셸)** 로 둔다. 실물 그릴 뒤가 금속 히트싱크인지 플라스틱 배플인지는
      사진으로 판별 불가(UNKNOWN)이므로, 확인되지 않은 금속을 새로 만들지 않는 쪽을 택한다.
      금속으로 밝혀지면 그룹만 바꾸면 된다(형상은 그대로)."""
    A = [(group, box(d * 0.5, w, h, center=(cx - d * 0.25, 0, cz)))]         # 함몰 프레임
    for k in range(n_fin):                                                    # 세로 핀
        y = (k - (n_fin - 1) / 2) * (w / n_fin)
        A.append((group, box(d, w / n_fin * 0.42, h * 0.88, center=(cx, y, cz))))
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
    """Matrice 4E **v1** — 측량 페이로드(3축 짐벌 + 렌즈 여러 개 + 레이저).
    ⚠ v2 는 `_gimbal_sensor_v2` 를 쓴다(사진대조로 형상이 다름). 이 함수는 v1 호환용."""
    A = []
    A.append(("camera", cyl(w * 0.30, h * 0.9, center=(cx, 0, cz + h * 0.55), axis="z", seg=20)))
    A.append(("camera", box(d, w * 1.25, h, center=(cx, 0, cz))))
    for dy in (-0.34, 0.0, 0.34):
        A.append(("camera", cyl(h * 0.28, d * 0.5, center=(cx + d * 0.52, dy * w, cz), axis="x", seg=22)))
    return A


def _gimbal_sensor_v2(w, h, d, cx, cz):
    """Matrice 4E **v2** — 기수 앞 각진 **큐브형 3축 짐벌**. (2026-07-30 사진대조 라운드)

    실물 근거: assets/photos/matrice4e/matrice 4E_1.png(정면 제품컷) 확대 + 매뉴얼 도해.
      · 카메라 블록은 상자다 — 정면이 **68 × 74 mm**(사진 실측, 축척 0.6249 mm/px),
        깊이 55~65 mm. 아래로 갈수록 살짝 좁아지는 사다리꼴.
      · 정면 개구는 **2×2 사분면 4개**: 좌상 텔레(원형), 우상 미디엄텔레(라운디드 사각),
        우하 광각 4/3(가장 큼), 좌하 레이저 거리계(작은 사각). ⛔ 옛 v2 형상은 렌즈 3개를
        **가로 일렬**로 놓았고 블록이 77.5(폭)×60(높이)×75(깊이)로 **깊이가 폭보다 컸다**.
      · 블록 좌우를 **주름진 원통형 롤축 모터 배럴** 2개가 관통해 요크에 물린다(정면 실루엣의
        폭을 68 → 89 mm 로 넓히는 것이 바로 이 배럴이다).
      · 위쪽에 요(yaw) 원통 + 기수 아래 댐핑 플레이트.
    인자: w=좌우폭, h=높이, d=앞뒤깊이, (cx,cz)=블록 중심."""
    A = []
    #  요 축 원통 + 댐핑 플레이트(기수 아래로 물림).
    #  ⚠ z 오프셋(0.60/0.76)은 **기수 껍질 안쪽**에 들어가도록 잡은 값이다 — 더 키우면
    #    플레이트가 기수 위로 삐져나와 '공중에 뜬 판'이 되고, 그건 에러 없이 산란만 늘린다.
    A.append(("camera", cyl(w * 0.22, h * 0.34, center=(cx - d * 0.10, 0, cz + h * 0.60),
                            axis="z", seg=20)))
    A.append(("camera", box(d * 0.9, w * 0.86, h * 0.10,
                            center=(cx - d * 0.14, 0, cz + h * 0.76))))
    #  카메라 블록(라운디드 큐브 근사 — 위가 살짝 넓은 사다리꼴을 두 상자로)
    A.append(("camera", box(d, w, h * 0.62, center=(cx, 0, cz + h * 0.16))))
    A.append(("camera", box(d * 0.94, w * 0.88, h * 0.40, center=(cx, 0, cz - h * 0.28))))
    #  롤축 모터 배럴(좌우 관통) — 주름 링 2개로 표현
    for sy in (+1, -1):
        A.append(("camera", cyl(h * 0.24, w * 0.16, center=(cx - d * 0.06, sy * w * 0.55, cz + h * 0.12),
                                axis="y", seg=24)))
        A.append(("camera", cyl(h * 0.19, w * 0.05, center=(cx - d * 0.06, sy * w * 0.66, cz + h * 0.12),
                                axis="y", seg=20)))
    #  정면 2×2 개구 (dy, dz, 반경/반폭, 원형여부)
    xf = cx + d * 0.50
    for (dy, dz, rr, round_) in [(-0.24, +0.17, 0.155, True),    # 좌상 텔레
                                 (+0.24, +0.17, 0.135, False),   # 우상 미디엄텔레
                                 (+0.24, -0.20, 0.175, False),   # 우하 광각(가장 큼)
                                 (-0.26, -0.21, 0.085, False)]:  # 좌하 레이저 거리계
        c = (xf, dy * w, cz + dz * h)
        if round_:
            A.append(("camera", cyl(rr * w, d * 0.16, center=c, axis="x", seg=24)))
        else:
            A.append(("camera", box(d * 0.16, rr * 2 * w, rr * 2 * w, center=c)))
    return A


def _rtk_cylinder(cx, cz, d_base, d_top, h, seg=36):
    """Matrice 4E **상단 GNSS/RTK 안테나** — 윗면이 평평한 살짝 테이퍼진 원통.
    (2026-07-30 사진대조 라운드)

    실물 근거: matrice 4E_4.png(후면 정투영에 가까움) 실측 — 지름 **44 mm**(밑 46 / 위 43),
    동체 crown 위로 **32 mm**, 윗면 **평평**. matrice 4E_5.png(상면)에서 원의 중심이
    동체 중앙보다 **68 mm 뒤**(= −0.27·bl).
    ⛔ 폐기된 옛 형상: 반구형 **돔**(반경 36 → 0 으로 둥글게 닫힘) + 그 위에 지름 12 mm ·
       길이 28 mm 의 'pcb' **안테나 봉**. 실물에 봉은 **없다**(사진 4장 어디에도 없음).
       돔이라 상면 실루엣이 둥글게 사라져 이 기종의 최대 식별점이 흐려져 있었다."""
    rb, rt = d_base / 2.0, d_top / 2.0
    pr = np.array([[0.0, 0.0], [rb, 0.0], [rb, h * 0.10],
                   [rt, h * 0.88], [rt * 0.90, h], [0.0, h]])
    return revolve(pr, seg=seg, center=(cx, 0.0, cz))


# --------------------------------------------------------------------------- #
#  센서(어안 비전·LiDAR·레이저 거리계) — v2 상세
# --------------------------------------------------------------------------- #
def _fisheye(cx, cy, cz, r, axis="x"):
    """어안 장애물감지 카메라 1개(작은 반구+렌즈)."""
    return [("camera", sphere(r, center=(cx, cy, cz), subdiv=2)),
            ("camera", cyl(r * 0.55, r * 0.7, center=(cx, cy, cz), axis=axis, seg=12))]


def _lidar(cx, cz, w):
    """전방 LiDAR 모듈(Mini 5 Pro) — 기수 앞 작은 직사각 창."""
    return [("camera", box(w * 0.5, w * 1.4, w * 0.8, center=(cx, 0, cz))),
            ("camera", cyl(w * 0.34, w * 0.3, center=(cx + w * 0.3, 0, cz), axis="x", seg=16))]


# --------------------------------------------------------------------------- #
#  착륙장치
# --------------------------------------------------------------------------- #
def _capsule_wt(r, h, center=(0, 0, 0), axis="z", _s=100.0):
    """**watertight 를 보장하는** capsule. (2026-07-30)

    `trimesh.creation.capsule` 은 **절대** 병합 허용오차(`tol.merge = 1e-8`, 단위 m)에 걸려
    반경이 작아지면 극(pole) 근처 링이 한 점으로 병합되고 그 자리에 **구멍이 남는다**.
    실측(trimesh 4.12.2): r=1.9 mm · h=101 mm → 면 1056→960, **열린 변 96개**,
    `is_watertight=False`, 부피가 −3.5% 로 어긋남(1.116e−6 vs 1.157e−6 m³).
      · s1000plus 의 스키드는 r=10.8 mm 라 이 함정에 **걸리지 않았고**,
      · `_gear_tall` 의 `0.016·R` 규약을 훨씬 작은 기체(typhoonh480, R=0.119 m → r=1.9 mm)에
        쓰면서 **처음 밟았다**.
    비watertight 파트는 SBR first-hit 이 껍질 내부를 보게 만들고(가짜 산란) trimesh 의
    질량·관성 계산도 못 하게 된다 → 조용히 틀리기 전에 여기서 막는다.

    ⚠ **깨진 경우에만** 100배 크기로 지어 되축소한다(균등 배율이라 형상은 완전 상사).
      정상인 파트는 옛 경로 그대로여서 기존 5종 메쉬는 **비트단위로 동일**하다."""
    m = capsule(r, h, center=center, axis=axis)
    if m.is_watertight:
        return m
    q = capsule(r * _s, h * _s, axis=axis)          # 중심은 배율 뒤에 옮긴다(원점 기준 상사)
    q.apply_scale(1.0 / _s)
    q.apply_translation(np.asarray(center, float))
    return q


def _gear_arch(L, W, zbot, leg_h):
    """Phantom v2 — 아치형(inverted-U) 착륙다리 2개(좌우), 안테나 내장 후방 다리.

    ⭐ 2026-07-30 사진대조 라운드로 4가지를 고쳤다(근거: assets/photos/phantom4/ _3 정면·
       _1 3/4·_5 상면, 축척은 공식 총높이 196 mm = 정면사진 415 px → 0.472 mm/px):
      1) **벌림각 15.5° → 3.8°.** 실물 다리는 거의 수직이다(정면사진에서 붙는 곳 141 mm,
         발 157 mm, 높이 113 mm). 옛 값은 발이 지나치게 밖으로 나가 실루엣이 A자였다.
      2) **다리 단면 9.1 × 9.1 mm → 24(앞뒤) × 13(좌우) mm 납작 블레이드.** 실물은 판형
         스트럿이라 옛 값은 정면 렌더에서 **철사**처럼 보였다.
         (sweep 로컬축: rounded_rect 의 1번째 인자가 좌우, 2번째가 앞뒤다.)
      3) **발 길이 0.60·L → 0.85·L**(상면사진 레일 ≈145 mm). 발은 둥근 봉이 아니라
         바닥이 평평한 레일이지만, 여기서는 캡슐을 눌러 근사한다.
      4) 아치 앞뒤 스팬을 발 길이에 맞춰 넓혔다(0.36/−0.34 · L).
    """
    A = []
    #  ⚠ sweep 의 로컬 1번축(N)은 up×T 다. 다리는 거의 연직이고 **좌우(±y)로만** 기울어지므로
    #    N 은 사실상 **앞뒤(x)** 방향이 된다 → rounded_rect 의 첫 인자가 앞뒤, 둘째가 좌우다.
    #    (처음 이 값을 뒤집어 넣었더니 정면뷰에서 다리가 24 mm 로 뚱뚱하게 보였다.)
    leg_w_lat, leg_w_fa = 0.013, 0.024          # 좌우 13 mm · 앞뒤 24 mm (실측)
    for sy in (1, -1):
        #  붙는 곳 반폭 0.447·W · 발 반폭 0.497·W → 스팬 141 / 157 mm, 벌림 **3.8°** (정면사진 실측).
        y_top, y_foot = sy * 0.447 * W, sy * 0.497 * W
        top_f = np.array([0.36 * L, y_top, zbot])
        top_r = np.array([-0.34 * L, y_top, zbot])
        foot_f = np.array([0.34 * L, y_foot, zbot - leg_h])
        foot_r = np.array([-0.32 * L, y_foot, zbot - leg_h])
        # 앞다리·뒷다리(납작 블레이드) + 발 스키드(앞뒤 레일)로 inverted-U
        for a, b in ((top_f, foot_f), (top_r, foot_r)):
            t = np.linspace(0, 1, 10)[:, None]
            A.append(("gear", sweep((1 - t) * a + t * b,
                                    lambda s: rounded_rect(leg_w_fa, leg_w_lat, 0.004),
                                    n_pts=16)))
        A.append(("gear", _capsule_wt(0.009, L * 0.85,
                                      center=(0.01 * L, y_foot, zbot - leg_h), axis="x")))
    return A


def _gear_arm_spikes(r_motor, angles, z_arm, h, d_root, d_tip,
                     splay_deg=20.0, inboard=0.87):
    """Matrice 4E — **암 끝(모터 바로 안쪽) 아래로 뻗은 테이퍼 원뿔 다리 4개**.
    (2026-07-30 사진대조 라운드)

    실물 근거: matrice 4E_1.png(정면)·_4.png(후면 좌측 암 확대)·_2/_3(측면) — 각 암의 아래쪽,
    모터 마운트 캐스팅 바로 안쪽에서 **뿌리가 넓고 끝이 뾰족한 판/원뿔** 다리가 아래-바깥으로
    내려온다. 벨리보다 ~35 mm 낮은 곳에서 끝난다. 매뉴얼은 이 다리에 **안테나가 내장**돼
    있다고 적는다(O4 Enterprise) — 재질 그룹은 플라스틱 셸이지만 안쪽은 금속이다(미모델링).
    치수는 docs/drone_specs_2026.json 의 '길이 60~75 mm, 뿌리 ~14 mm → 끝 ~7 mm, 15~25°'.

    ⛔ 폐기된 옛 형상: `_gear_feet` — **동체 밑면**(±0.30·bl, ±0.30·bw)에 붙은 길이 20 mm
       짜리 캡슐 4개. 실물에는 동체 밑에 다리가 아예 없다(벨리는 센서·벤트뿐). 위치가 통째로
       틀려서 저앙각 실루엣과 지면 반사 기하가 둘 다 어긋났다.
      r_motor : 모터 반경[m], angles : 모터 각도[deg] 목록
      z_arm   : 다리가 붙는 암 아랫면의 z[m]
      h       : 다리 길이[m], d_root/d_tip : 뿌리/끝 지름[m]
    """
    from shapely.geometry import Point
    A = []
    dr = h * np.tan(np.radians(splay_deg))         # 벌림에 따른 발끝의 바깥 이동
    #  ⭐ 2026-07-31 — r_motor 는 스칼라(한 원 배치) 또는 **각도별 목록**(사다리꼴)이다.
    rs = [float(r_motor)] * len(angles) if np.isscalar(r_motor) else [float(v) for v in r_motor]
    for a, rm in zip(angles, rs):
        r0, r1 = rm * inboard, rm * inboard + dr
        ca, sa = np.cos(np.radians(a)), np.sin(np.radians(a))
        top = np.array([r0 * ca, r0 * sa, z_arm])
        bot = np.array([r1 * ca, r1 * sa, z_arm - h])
        t = np.linspace(0, 1, 8)[:, None]

        def prof(s, _d0=d_root, _d1=d_tip):
            return Point(0.0, 0.0).buffer((_d0 + (_d1 - _d0) * s) / 2.0, quad_segs=6)
        A.append(("gear", sweep((1 - t) * top + t * bot, prof, n_pts=20)))
        A.append(("gear", sphere(d_tip / 2.0, center=tuple(bot), subdiv=2)))   # 둥근 발끝
    return A


def _gear_skids(L, W, zbot, leg_h):
    """Phantom — 일체형 스키드(다리 4 + 좌우 스키드 바). 실물은 셸과 한 몸."""
    A = []
    for sx in (0.34, -0.30):
        for sy in (0.30, -0.30):
            A.append(("gear", _capsule_wt(leg_h * 0.10, leg_h * 0.80,
                                          center=(sx * L, sy * W, zbot - leg_h * 0.45), axis="z")))
    for sy in (0.30, -0.30):
        A.append(("gear", _capsule_wt(leg_h * 0.11, L * 0.62,
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
        A.append(("gear", _capsule_wt(0.016 * R, R * 0.85,
                                      center=(0.0, sy * R * 0.52, zbot - leg_h), axis="x")))
    return A


# --------------------------------------------------------------------------- #
#  외형감사(2026-07-30) 전용 형상 — s1000plus · typhoonh480
#    이 절의 helper 는 **실물 사진/실물 CAD 실측치를 그대로 먹는다**. 비율식이 하나도 없다.
#    (기존 5종 중 나머지 3종은 이 helper 를 부르지 않으므로 메쉬 불변)
# --------------------------------------------------------------------------- #
def _planform_poly(psi_deg, r_m, n_pts=144):
    """r(ψ) 표(전방 ψ=0, 좌현 +ψ)를 좌우대칭 폐곡선 폴리곤으로. 주기 스플라인 보간.

    왜 표인가: Typhoon H480 의 셸 평면형은 타원도 눈물방울도 아니고 **'땅콩'** 이다 —
    코가 가장 길고(r=100), 암 사이 허리가 잘록하고(74), 꼬리는 배터리 면이라 평평하다(96).
    `_body_folding` 의 (넓은 허리 + 뾰족한 코) 로프트는 이 순서를 **거꾸로** 만든다."""
    from shapely.geometry import Polygon as _Poly
    p = np.asarray(psi_deg, float); r = np.asarray(r_m, float)
    #  0~180 표를 180~360 으로 거울대칭 확장한 뒤 주기보간(좌우대칭 = 비행 안정 규약 유지)
    pp = np.concatenate([p, 360.0 - p[::-1][1:-1]])
    rr = np.concatenate([r, r[::-1][1:-1]])
    q = np.linspace(0.0, 360.0, n_pts, endpoint=False)
    rq = np.interp(q, pp, rr, period=360.0)
    a = np.radians(q)
    return _Poly(np.column_stack([rq * np.cos(a), rq * np.sin(a)]))


def _body_profiled(planform, z_lo, z_hi, z_full, p_up=2.6, p_dn=2.2,
                   cap_up=0.30, cap_dn=0.16, n_sec=17):
    """평면형 폴리곤을 z 로 **초타원 배율**해 쌓은 매끈한 셸.

      z_full : 평면형이 100% 로 나오는 높이(가장 넓은 단면)
      p_*    : 위/아래 초타원 지수 — 클수록 옆면이 수직에 가깝다(실물 셸은 옆이 서 있다)
      cap_*  : 위/아래 끝단의 최소 배율(0 이면 뾰족해진다. 실물은 평평한 천장·바닥이 있다)
    `_body_folding` 처럼 x 를 따라 단면을 놓는 대신 **z 를 따라** 놓는다 — 그래야 평면형이
    설계된 그대로 남는다(x-로프트는 평면형을 스플라인이 다시 정한다)."""
    zs = np.linspace(z_lo, z_hi, n_sec)
    secs = []
    for z in zs:
        if z >= z_full:
            u = (z - z_full) / max(z_hi - z_full, 1e-9); p, c = p_up, cap_up
        else:
            u = (z_full - z) / max(z_full - z_lo, 1e-9); p, c = p_dn, cap_dn
        s = max(float((1.0 - min(u, 1.0) ** p) ** (1.0 / p)), c)
        secs.append((float(z), _aff_scale(planform, s)))
    m = smooth(loft(secs, n_pts=96), iters=2)
    #  ⚠ `cadkit.loft` 는 단면을 **x** 를 따라 쌓고 폴리곤을 (y, z) 로 읽는다(눈물방울 동체용 규약).
    #    우리는 평면형을 (x, y) 로 주고 **z** 로 쌓았으므로 축을 되돌려야 한다:
    #    loft 결과 (level, px, py) → 우리 (px, py, level). 순환치환이라 행렬식 +1 = winding 보존.
    T = np.array([[0.0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]])
    m.apply_transform(T)
    return m


def _aff_scale(poly, s):
    from shapely import affinity as aff
    return aff.scale(poly, xfact=s, yfact=s, origin=(0.0, 0.0))


def _arm_dihedral(ang_deg, s0, s1, z0, dihedral_deg, od,
                  collar=None, n_pts=20):
    """**상반각(dihedral)이 있는 직선 카본 튜브 암** + 뿌리 플라스틱 페어링. (2026-07-30)

      s0, s1        : 튜브 시작/끝 반경 [m]
      z0            : s0 에서의 축 높이 [m]
      dihedral_deg  : 축이 수평과 이루는 각[deg] (위로 +)
      collar        : (cs0, cs1, w0, w1) 뿌리 페어링 구간과 폭 [m]. None 이면 안 만든다.

    ⚠ 왜 필요한가: Typhoon H480 의 여섯 암은 전부 +17.7~17.8° 로 올라간다(실물 CAD 에서
      암 3방향 독립 선형피팅, 0.1° 재현). 평평한 암은 측면 실루엣과, 기체에서 가장 긴
      선형부재의 정반사 기하를 **둘 다** 틀리게 만든다."""
    from shapely.geometry import Point
    a = np.radians(ang_deg); t = np.tan(np.radians(dihedral_deg))
    ca, sa = np.cos(a), np.sin(a)
    out = []
    p0 = np.array([s0 * ca, s0 * sa, z0])
    p1 = np.array([s1 * ca, s1 * sa, z0 + (s1 - s0) * t])
    u = np.linspace(0, 1, 6)[:, None]
    circ = Point(0.0, 0.0).buffer(od / 2.0, quad_segs=10)
    out.append(("tube", sweep((1 - u) * p0 + u * p1, lambda q: circ, n_pts=n_pts)))
    if collar:
        cs0, cs1, w0, w1 = collar
        q0 = np.array([cs0 * ca, cs0 * sa, z0 + (cs0 - s0) * t])
        q1 = np.array([cs1 * ca, cs1 * sa, z0 + (cs1 - s0) * t])
        u = np.linspace(0, 1, 8)[:, None]
        out.append(("collar", sweep((1 - u) * q0 + u * q1,
                                    lambda q: rounded_rect(w0 + (w1 - w0) * q,
                                                           (w0 + (w1 - w0) * q) * 0.82,
                                                           (w0 + (w1 - w0) * q) * 0.30, pts=28),
                                    n_pts=24)))
    return out


def _motor_pod(cx, cy, cz, w, l, h, seg=32):
    """Typhoon H480 의 **눈물방울 모터 포드**(플라스틱) — 암 끝을 감싸는 유선형 하우징."""
    pr = np.array([[0.0, -h / 2], [w * 0.30, -h * 0.46], [w * 0.46, -h * 0.30],
                   [w * 0.50, 0.0], [w * 0.47, h * 0.22], [w * 0.36, h * 0.40],
                   [w * 0.20, h * 0.48], [0.0, h / 2]])
    m = revolve(pr, seg=seg, center=(0, 0, 0))
    m.apply_scale([l / w, 1.0, 1.0])
    m.apply_translation([cx, cy, cz])
    return m


def _ultrasonic(cx, cy, cz, r, depth):
    """전방 초음파 트랜스듀서 1개 — 크롬 링 + 금색 다이어프램(둘 다 금속). 기수 정면 돌출."""
    return [cyl(r, depth, center=(cx, cy, cz), axis="x", seg=20),
            cyl(r * 0.62, depth * 0.55, center=(cx + depth * 0.5, cy, cz), axis="x", seg=16)]


def _gimbal_cgo3(parts_mm, z_off_mm=0.0):
    """CGO3+ 3축 짐벌 — **4파트 체인**(마운트판 → 요 암 → 롤 요크 → 카메라 볼).

    ⚠ 예전에는 **카메라 볼 하나**만 있었다(치수도 cgo3_camera STL bbox 하나뿐). 실물은 그 위에
      145.5 mm 의 구조물(마운트 −125.6~−54.8 · 요 −175.0~−99.8 · 롤 −183.2~−140.8, base_link)이
      더 있고, 짐벌은 이 기체에서 **동체 아래 유일한 큰 산란체**다.
      parts_mm 는 (부위, cx, cz, l, w, h) [mm] 목록(실물 CAD STL bbox 그대로)."""
    A = []
    for kind, cx, cz, l, w, h in parts_mm:
        c = (cx / 1000.0, 0.0, (cz + z_off_mm) / 1000.0)
        if kind == "ball":
            m = sphere(0.5 * max(l, w, h) / 1000.0, center=(0, 0, 0), subdiv=3)
            m.apply_scale([l / max(l, w, h), w / max(l, w, h), h / max(l, w, h)])
            m.apply_translation(c)
            A.append(m)
            A.append(cyl(0.24 * h / 1000.0, 0.30 * l / 1000.0,
                         center=(c[0] + 0.42 * l / 1000.0, 0.0, c[2]), axis="x", seg=28))
        else:
            A.append(box(l / 1000.0, w / 1000.0, h / 1000.0, center=c))
    return A


def _gear_tall_tube(zbot, h, leg_od, skid_od, splay_deg,
                    leg_top_y, leg_x, skid_len, skid_axis_z,
                    foam_od=None, foam_len=None, foam_inner=None,
                    top_clamp=None, foot_clamp=None):
    """열린 프레임용 **카본 튜브 착륙장치** — 좌우 **1조씩, 조당 다리 1개 + 스키드 1개**.

    ⭐ 2026-07-30 전면 정정(제조사 STEP 실측). 초판은 조당 다리 **2개**로 inverted-U 를
      세웠는데 실물은 다리가 **총 2개**다(BOM: GUAN-CHENG ×2 · 상단 클램프 JIA-LIANJIE ×2 ·
      발 T커넥터 JIAO-LIANJIE ×2 · 스키드 CARBON-FIBER-TUBE ×2 · EVA 발포 JIAO-EVA ×4).
      다리 4개는 측면 실루엣을 '탁자'로 만들어 실물의 넓은 V 와 완전히 달랐다.
      또한 초판은 다리/스키드 위치를 판 치수의 **비율**로 지어냈는데, 이제 전부 실측이다.

    좌표: 다리 축은 전후 성분이 0 이고(STEP gear_splay_azimuth 90°) 순수 좌우로만 벌어진다.
      zbot        : 다리 상단이 붙는 면의 z [m] (열린 프레임은 하판 **아랫면**)
      h           : 다리 상단이 그 면보다 아래로 들어간 깊이 [m]
      leg_top_y   : 다리 상단 축의 |y| [m]
      leg_x       : 다리·스키드의 x [m]
      skid_len    : 스키드 튜브 길이 [m]
      skid_axis_z : 스키드 축의 z [m]
      splay_deg   : 다리 축이 수직과 이루는 각[deg] — 좌우 위치는 이 각과 z 차이로 **유도**한다
                    (bottom_y = leg_top_y + (z_top − skid_axis_z)·tan splay)
      foam_*      : EVA 발포 슬리브 (외경 / 1개 길이 / 안쪽 끝의 |x|). None 이면 안 만든다.
      top_clamp   : (dx, dy, z_lo, z_hi) 상단 나일론 클램프 블록 [m]. None 이면 안 만든다.
      foot_clamp  : (dx, dy, dz) 발 T커넥터 블록 크기 [m]. None 이면 안 만든다.

    그룹: 카본 튜브 = **`gear_cf`**, 나일론·EVA = **`gear`**(플라스틱 |Γ|=0.28).
      둘을 섞으면 재질이 **조용히** 틀린다(카본 0.90 ↔ 플라스틱 0.28 = 10 dB 급)."""
    from shapely.geometry import Point
    A = []
    z_top = zbot - h
    dy = (z_top - skid_axis_z) * np.tan(np.radians(splay_deg))
    leg = Point(0.0, 0.0).buffer(leg_od / 2.0, quad_segs=8)
    for sy in (1, -1):
        top = np.array([leg_x, sy * leg_top_y, z_top])
        bot = np.array([leg_x, sy * (leg_top_y + dy), skid_axis_z])
        t = np.linspace(0, 1, 6)[:, None]
        A.append(("gear_cf", sweep((1 - t) * top + t * bot, lambda s: leg, n_pts=20)))
        A.append(("gear_cf", cyl(skid_od / 2.0, skid_len,
                                 center=(leg_x, sy * (leg_top_y + dy), skid_axis_z),
                                 axis="x", seg=20)))
        if foam_od and foam_len:
            for sx in (+1, -1):
                cx = leg_x + sx * (foam_inner + foam_len / 2.0)
                A.append(("gear", cyl(foam_od / 2.0, foam_len,
                                      center=(cx, sy * (leg_top_y + dy), skid_axis_z),
                                      axis="x", seg=20)))
        if top_clamp:
            cdx, cdy, z_lo, z_hi = top_clamp
            A.append(("gear", box(cdx, cdy, z_hi - z_lo,
                                  center=(leg_x, sy * leg_top_y, 0.5 * (z_lo + z_hi)))))
        if foot_clamp:
            fdx, fdy, fdz = foot_clamp
            A.append(("gear", box(fdx, fdy, fdz,
                                  center=(leg_x, sy * (leg_top_y + dy), skid_axis_z))))
    return A


# --------------------------------------------------------------------------- #
#  Holybro X500 V2 전용 실측 형상 — 제조사 STEP 에서 나온 값만 쓴다
# --------------------------------------------------------------------------- #
#  ⭐ 단일 출처: assets/meshes/reference/x500v2-frame.step (Holybro 공식 STEP, 2022-07-19)
#     측정기 benchmark/measure_x500v2_cad.py → 원장 outputs/x500v2_cad.json (51항목 VERIFIED).
#     CAD 는 공표값 4건(판두께 2.000 · 판간격 28.000 · 판 143.72↔144 · 다리높이 215.28↔215)을
#     **독립 재현**하므로 신뢰한다. 휠베이스만 502.8 vs 공표 500(공표가 반올림).
#  ⚠ 등급을 올리지 않는다. 아래 값 중 **CAD 에서 직접 읽은 것만 VERIFIED** 이고, 폭 프로파일의
#     보간점·나일론 클램프 크기는 **DERIVED**(사진 + CAD 점군 구간폭에서 잡았다)로 적었다.
#  ⚠ z 원점은 우리 메쉬 규약대로 **판 간극 정중앙**이다. STEP 은 하판 아랫면이 원점이고
#     +y 가 상방이므로  z_ours[mm] = y_step[mm] − 16.0  으로 옮겼다.
X500V2 = dict(
    plate_chamfer_mm=22.95,        # VERIFIED — 45° 코너 챔퍼 직각변
    arm_tube_r0_mm=67.15,          # VERIFIED — 암 튜브 안쪽 끝 반경(판 간극 안)
    arm_tube_r1_mm=232.15,         # VERIFIED — 암 튜브 바깥쪽 끝 반경 (길이 165.0)
    corner_clamp_r_mm=(65.1, 93.2),   # VERIFIED — 뿌리 클램프 반경 구간(HMX5V-JIBI-JIA-MUJU)
    corner_clamp_w_mm=26.0,        # DERIVED — 점군 |lat| 주모드 ±8.6 의 몸통 + 살
    mount_plate_r_mm=(206.4, 270.65),  # VERIFIED — 카본 모터마운트 판 반경 구간(BAN-DJ-DIAN-F2)
    mount_plate_z_mm=(4.0, 6.0),   # VERIFIED — y_step 20.0/22.0 (두께 2.0)
    #  물방울꼴 폭 법칙 — (반경, 폭)[mm]. 굵은 4점은 CAD 구간폭(VERIFIED), 양 끝단은 DERIVED.
    mount_plate_width=((206.4, 21.0), (215.0, 27.0), (226.0, 32.5), (234.0, 30.3),
                       (242.0, 31.8), (250.0, 42.5), (258.0, 38.0), (266.0, 28.5),
                       (269.5, 22.0), (270.65, 11.0)),
    tip_clamp_r_mm=(192.0, 216.0),  # DERIVED(사진 _05) — 튜브를 무는 파란 나일론 칼라.
    tip_clamp_w_mm=24.0,           # DERIVED
    tip_clamp_z_mm=(-12.0, 10.0),  # DERIVED — 칼라 꼭대기는 카본 판(4~6)보다 **높다**(사진 _05·_03)
    motor_seat_r_mm=(208.0, 268.0),  # DERIVED — 마운트 판 아래 나일론 시트
    motor_axis_r_mm=251.4,         # VERIFIED — 모터 4기 중심의 중심거리(휠베이스 502.8, 공표 500 은 반올림)
    motor_base_od_mm=32.3,         # VERIFIED — 모터 밑판 최대 반경 16.13×2
    motor_base_z_mm=(6.0, 12.7),   # VERIFIED — y_step 22.0..28.7
    motor_bell_z_mm=(12.7, 37.2),  # VERIFIED — y_step 28.7..53.2 (벨 OD 27.7)
    gear_leg_top_y_mm=56.78,       # VERIFIED
    gear_leg_top_below_plate_mm=6.55,   # VERIFIED
    skid_axis_z_mm=-221.78,        # VERIFIED — y_step −205.78 (발포 최하점이 공표 215 를 만든다)
    skid_len_mm=248.0,             # VERIFIED
    skid_track_mm=239.91,          # VERIFIED (다리 각·z 차이에서 유도되는 값과 0.05 mm 일치)
    foam_od_mm=19.0,               # VERIFIED — EVA 리브 최대 외경
    foam_len_mm=93.0,              # VERIFIED
    foam_inner_x_mm=21.0,          # VERIFIED — 발포 안쪽 끝 |x|
    rail_od_mm=9.4,                # VERIFIED — 페이로드 레일(공표 명목 10)
    rail_len_mm=250.0,             # VERIFIED
    rail_y_mm=30.0,                # VERIFIED — 좌우 레일 축 |y| (간격 60.0)
    rail_z_mm=-29.0,               # VERIFIED — y_step −13.0
    rail_x_centre_mm=5.0,          # VERIFIED — x −120..+130
    rail_clamp_x_mm=50.0,          # VERIFIED — 하판 아래 레일 클램프(JIA-GUAN) x ±50
    batt_tray_mm=(100.0, 56.2, 2.0),   # VERIFIED — BATTERY-MOUNTING-PLAT x±50 · z±28.1
    batt_tray_z_mm=-71.3,          # VERIFIED — y_step −56.3 바닥 + 판 두께 절반
    batt_pack_mm=(145.0, 45.0, 25.0),  # DERIVED — 4S 5000 mAh 팩 대표치(CAD 에 팩은 없다)
    pylon_x_mm=35.0,               # VERIFIED — PYLONS-X500 x 17.3..52.1 중앙
    pylon_y_mm=30.0,               # VERIFIED — z_step ±35.2 의 기둥 위치
    pm06_mm=(55.0, 35.0, 12.0),    # VERIFIED — PCB-PM06 (전원분배 보드)
    pm06_centre_mm=(10.0, 0.0, -3.0),  # VERIFIED — y_step 13 → z −3
    front_board_mm=(65.0, 93.0, 2.0),  # VERIFIED — PLATFORM-PLAT-X500
    front_board_centre_mm=(99.0, 0.0, -42.4),   # VERIFIED — y_step −26.4
    mast_base_mm=(32.2, 32.2, 18.7),   # VERIFIED — GPS-ZHIJIA-ZUO
    mast_base_z_mm=-32.6,          # VERIFIED — y_step −26.0..−7.3 중앙 −16.65
    mast_rod_od_mm=4.0,            # VERIFIED — 3.95
    mast_x_mm=99.6,                # VERIFIED — GAN-GPSV5-ZHIJIA x 97.6..101.5
    mast_top_z_mm=89.5,            # VERIFIED — 상판 윗면 +73.5
    gps_puck_mm=(50.0, 14.0),      # DERIVED(사진 _15/_16) — M8N 퍽 지름·높이. CAD 는 마운트만 담는다
)


def _x500v2_arm_tip(A, ang_deg, ca, sa, gap, t_bot, t_top, mot_r, mot_h):
    """X500 V2 암 **끝단 조립체** — 나일론 칼라 + 카본 모터마운트 판 + 나일론 시트 + 모터.

    실물(사진 `_05`)의 순서는 아래에서 위로 [나일론 시트] → [카본 판 2 mm] → [모터]이고,
    튜브는 그 사이를 **파란 나일론 칼라**가 문다. 초판 메쉬는 이 셋이 전부 없었고 튜브 끝에
    지름 52 mm 짜리 벨 하나만 얹혀 있었다 — 암 끝의 실루엣이 통째로 달랐다.

    모터도 한 덩어리가 아니다. 실물 2216 은 **밑판(OD 32.3, z 6.0~12.7)** 위에
    **캔(OD 27.7, z 12.7~37.2)** 이 앉는 2단이다(제조사 STEP y_step 22.0/28.7/53.2)."""
    q = X500V2
    r0, r1 = (v / 1000.0 for v in q["mount_plate_r_mm"])
    zp0, zp1 = (v / 1000.0 for v in q["mount_plate_z_mm"])
    law = tuple((rr / 1000.0, ww / 1000.0) for rr, ww in q["mount_plate_width"])
    A.add(_teardrop_plate(law, zp0, zp1, ang_deg), "arm")           # 카본 판(=arm 과 같은 CFRP)

    #  나일론 시트 — 카본 판 **아래**에서 튜브까지 받친다. 판 폭의 0.78 로 좁혀 실물처럼 안쪽에 둔다.
    s0, s1 = (v / 1000.0 for v in q["motor_seat_r_mm"])
    seat = tuple((rr, ww * 0.78) for rr, ww in law if s0 - 1e-9 <= rr <= s1 + 1e-9)
    if len(seat) >= 3:
        A.add(_teardrop_plate(seat, -0.004, zp0, ang_deg), "accent")
    #  튜브를 무는 파란 칼라 — 카본 판보다 **안쪽(반경이 작은 쪽)** 에 있고 판보다 조금 **높다**.
    #  사진 _05·_03 이 그렇다. 판 밑으로 숨기면 위에서 봤을 때 실물의 파란 칼라가 사라진다.
    c0, c1 = (v / 1000.0 for v in q["tip_clamp_r_mm"])
    cw = q["tip_clamp_w_mm"] / 1000.0
    cz0, cz1 = (v / 1000.0 for v in q["tip_clamp_z_mm"])
    A.add(rot_z(box(c1 - c0, cw, cz1 - cz0, center=(0.5 * (c0 + c1), 0.0, 0.5 * (cz0 + cz1))),
                ang_deg), "accent")

    #  모터 2단 — 밑판 + 캔. mot_r/mot_h 는 스펙(motor_dia_mm/motor_h_mm)에서 온 **캔** 치수다.
    #  ⚠ 모터축 반경은 spec.diagonal_mm/2(=250, 공표 500 의 반)이 아니라 CAD 실측 251.4 다.
    bz0, bz1 = (v / 1000.0 for v in q["motor_base_z_mm"])
    mz0, _mz1 = (v / 1000.0 for v in q["motor_bell_z_mm"])
    from drones import OPEN_MOTOR_BASE_M          # 프롭 장착 높이를 정하는 쪽과 **같은 z** 인지 대조
    if abs(mz0 - OPEN_MOTOR_BASE_M) > 1e-9:
        raise ValueError(
            f"_x500v2_arm_tip: 캔 바닥 z 가 두 곳에서 다르다 — 여기 {mz0*1000:.3f} mm vs "
            f"drones.OPEN_MOTOR_BASE_M {OPEN_MOTOR_BASE_M*1000:.3f} mm. 그대로 두면 프롭이 "
            f"모터 위가 아니라 공중에 뜨는데 **예외가 안 나므로** 여기서 막는다.")
    R = q["motor_axis_r_mm"] / 1000.0
    cx, cy = R * ca, R * sa
    A.add(cyl(q["motor_base_od_mm"] / 2000.0, bz1 - bz0,
              center=(cx, cy, 0.5 * (bz0 + bz1)), seg=28), "motor")
    bell = _motor_bell(mot_r, mot_h)
    bell.apply_translation([cx, cy, mz0])
    A.add(bell, "motor")
    return A


def _x500v2_underslung(A, z_deck_bot, z_deck_top):
    """X500 V2 의 **하부 페이로드 구조 + GPS 마스트** — 전부 제조사 STEP 실측(X500V2 표).

    초판 메쉬는 하판 아래에 얇은 배터리 상자 하나뿐이었다. 실물은
      · 전후로 250 mm 뻗은 **카본 레일 2줄**(⌀9.4, 간격 60)과 그 클램프,
      · 레일에 매달린 **배터리 트레이**(100×56) + 파일런 기둥 + 4S 팩,
      · 앞쪽 아래로 튀어나온 **페이로드 보드**(65×93)와 그 위로 솟은 **GPS 마스트**(꼭대기 +89.5)
    가 있고, 이들이 측면·정면 실루엣의 아래 절반을 만든다.

    ⚠ 배터리 팩 자체는 CAD 에 없다(사용자 부품). 145×45×25 는 4S 5000 mAh 대표치 = **DERIVED**."""
    q = X500V2
    mm = 1e-3
    #  페이로드 레일 2줄 + 하판 아래 클램프
    for sy in (1, -1):
        A.add(cyl(q["rail_od_mm"] / 2000.0, q["rail_len_mm"] * mm,
                  center=(q["rail_x_centre_mm"] * mm, sy * q["rail_y_mm"] * mm,
                          q["rail_z_mm"] * mm), axis="x", seg=18), "deck")
        for sx in (1, -1):
            A.add(box(0.006, 0.021, abs(q["rail_z_mm"] * mm - z_deck_bot) + 0.004,
                      center=(sx * q["rail_clamp_x_mm"] * mm, sy * q["rail_y_mm"] * mm,
                              0.5 * (q["rail_z_mm"] * mm + z_deck_bot))), "accent")
    #  배터리 트레이 + 파일런 기둥 4 + 팩
    tl, tw, tt = (v * mm for v in q["batt_tray_mm"])
    tz = q["batt_tray_z_mm"] * mm
    A.add(box(tl, tw, tt, center=(0, 0, tz)), "deck")
    for sx in (1, -1):
        for sy in (1, -1):
            A.add(box(0.008, 0.008, q["rail_z_mm"] * mm - tz,
                      center=(sx * q["pylon_x_mm"] * mm, sy * q["pylon_y_mm"] * mm,
                              0.5 * (q["rail_z_mm"] * mm + tz))), "accent")
    bl_, bw_, bh_ = (v * mm for v in q["batt_pack_mm"])
    A.add(box(bl_, bw_, bh_, center=(0, 0, tz + tt / 2 + bh_ / 2)), "battery")

    #  전원분배 보드(PM06) — 판 사이
    pl, pw, ph = (v * mm for v in q["pm06_mm"])
    px, py, pz = (v * mm for v in q["pm06_centre_mm"])
    A.add(box(pl, pw, ph, center=(px, py, pz)), "pcb")

    #  앞쪽 페이로드 보드 + GPS 마스트(봉 + 퍽). 마스트는 상판 위 73.5 mm 까지 솟는다.
    fl, fw, ft = (v * mm for v in q["front_board_mm"])
    fx, fy, fz = (v * mm for v in q["front_board_centre_mm"])
    A.add(box(fl, fw, ft, center=(fx, fy, fz)), "deck")
    for sx in (1, -1):                                   # 보드를 하판에 매다는 스탠드오프 2
        A.add(box(0.008, 0.008, abs(z_deck_bot - fz),
                  center=(fx + sx * 0.024, 0.0, 0.5 * (z_deck_bot + fz))), "accent")
    mbl, mbw, mbh = (v * mm for v in q["mast_base_mm"])
    A.add(box(mbl, mbw, mbh, center=(q["mast_x_mm"] * mm, 0.0, q["mast_base_z_mm"] * mm)), "accent")
    rod_z0 = q["mast_base_z_mm"] * mm + mbh / 2
    rod_z1 = q["mast_top_z_mm"] * mm
    A.add(cyl(q["mast_rod_od_mm"] / 2000.0, rod_z1 - rod_z0,
              center=(q["mast_x_mm"] * mm, 0.0, 0.5 * (rod_z0 + rod_z1)), seg=14), "deck")
    pd, phk = (v * mm for v in q["gps_puck_mm"])
    A.add(cyl(pd / 2, phk, center=(q["mast_x_mm"] * mm, 0.0, rod_z1 + phk / 2), seg=28), "accent")
    return A


def _teardrop_plate(width_law, z_lo, z_hi, ang_deg, seg_scale=1.0):
    """물방울꼴 수평 판 하나 — `width_law` = ((반경[m], 폭[m]), …) 을 위/아래 대칭으로 잇는다.
    +x 축 위에 만들고 z 로 `ang_deg` 회전한다(암 방향). X500 V2 모터마운트 판·모터시트 공용."""
    from shapely.geometry import Polygon as _Poly
    up = [(r, +w / 2.0) for r, w in width_law]
    dn = [(r, -w / 2.0) for r, w in reversed(width_law)]
    p = trimesh.creation.extrude_polygon(_Poly(up + dn).buffer(0), float(z_hi - z_lo))
    p.apply_translation([0.0, 0.0, z_lo])
    return rot_z(p, ang_deg)


def _gear_feet(L, W, zbot, h):
    A = []
    for sx in (0.30, -0.30):
        for sy in (0.30, -0.30):
            A.append(("gear", _capsule_wt(h * 0.20, h * 0.6, center=(sx * L, sy * W, zbot - h * 0.4),
                                          axis="z")))
    return A


def _gear_motor_legs(r_motor, angs, z_arm, h, w, spread, taper=0.55, n_pts=16):
    """접이식 소비자기(Mini/Mavic)의 **모터포드 착륙다리** — 앞 두 암에만 달린다. (2026-07-30)

    ■ 실물 근거 (assets/photos/ 원본 확대 관찰)
      · mini5pro/mini 5 pro_1.png  : 앞 두 모터포드 아래에 회색 **두 갈래** 다리가 내려온다.
        같은 사진의 **뒤 모터를 확대하면 다리가 없다** — 좌우 4개가 아니라 앞 2개다.
      · mavic4pro/mavic 4 pro_2.png · _4.png : 같은 배치. 다리가 더 길고 테이퍼가 뚜렷하며
        바깥쪽 갈래에 항법등(LED)이 박혀 있다(등 자체는 형상으로 모델링하지 않는다).
      · mavic 4 pro_3.png(배면) : 뒤 모터포드 아래는 매끈한 불룩면뿐 — 다리 없음 재확인.
      갈래는 **암 방향(반경방향)으로** 벌어진다 — 정면컷에서 두 갈래가 좌우로 갈라져 보이는 것이
      그 증거다(앞 암은 기수에서 ±56°(Mini)·±51°(Mavic) 라 반경방향이 거의 좌우다).

    ■ 왜 중요한가 (형상 말고도)
      이 다리는 기체의 **최하단**이다. mini5pro 의 envelope 높이(91 mm, 프롭 포함)는
      '다리 밑 → 프롭 위' 를 재는 값인데, 다리가 없으면 그 91 mm 를 짧은 프레임에 억지로
      맞추느라 `frame_fit_scale` 의 sz 가 1.68 까지 뛰어 **동체가 세로로 68% 늘어나 있었다.**
      다리를 만들면 sz 가 1 쪽으로 돌아오면서 동체 비율이 저절로 맞는다.

      r_motor : 모터 중심 반경 [m]        angs : 모터 각도[deg] 목록(전방 판정에 씀)
      z_arm   : 다리가 붙는 z(암 끝 안쪽) h    : 그 z 에서 발까지 깊이 [m]
      w       : 갈래 반폭 [m]             spread : 두 발의 반경방향 ± 벌림 [m]
      taper   : 발 끝에서 줄어드는 비율(0=등단면)"""
    A = []
    #  ⭐ 2026-07-31 — r_motor 는 스칼라 또는 **각도별 목록**(사다리꼴 기체)이다.
    rs = [float(r_motor)] * len(angs) if np.isscalar(r_motor) else [float(v) for v in r_motor]
    for ang, r_motor_k in zip(angs, rs):
        ca, sa = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        if ca <= 1e-9:                    # 뒤쪽 암 — 실물에 다리가 없다
            continue
        for s in (+1.0, -1.0):
            rr = r_motor_k + s * spread
            top = np.array([r_motor_k * ca, r_motor_k * sa, z_arm])
            foot = np.array([rr * ca, rr * sa, z_arm - h])
            t = np.linspace(0.0, 1.0, 8)[:, None]
            path = (1 - t) * top + t * foot

            def prof(u, _w=w):
                k = 1.0 - taper * u
                return rounded_rect(_w * 2.0 * k, _w * 1.7 * k, _w * 0.55 * k, pts=24)
            A.append(("gear", sweep(path, prof, n_pts=n_pts)))
    return A


# --------------------------------------------------------------------------- #
#  프레임 (프로펠러 제외) — 기종별
# --------------------------------------------------------------------------- #
def build_frame_cad(spec) -> "trimesh.Trimesh":
    """geom.Mesh 로 반환 (기존 파이프라인 호환). 그룹 이름 보존."""
    from drones import motor_angles, motor_radii, DRONE_GROUP_MAT   # 순환 import 회피용 지연

    key = spec.key
    diag = spec.diagonal_mm / 1000.0
    #  ⭐ 2026-07-31 — 로터 반경은 **drones.motor_radii 가 유일 출처**다. spec.rotor_r_mm 이 없으면
    #    전 로터가 diagonal_mm/2 원 위에 있어 옛 동작과 같고, 있으면 로터마다 다른 반경(사다리꼴)이
    #    된다. `r` 은 그 목록의 대푯값(비율식·다리·짐벌이 쓰던 스칼라)으로만 남긴다.
    r_list = motor_radii(spec)
    r = max(r_list)
    A = Assembly()

    # ---- 기종별 치수 --------------------------------------------------------
    if key == "s1000plus":
        # ------------------------------------------------------------------ #
        #  DJI S1000+ — 옥토. 카본 **정팔각** 센터플레이트(상·하판) + 25 mm 튜브 8암
        #  + 넓게 벌어진 카본 튜브 착륙장치 + 벨리 짐벌.
        # ------------------------------------------------------------------ #
        #  ⭐ 2026-07-30 **외형감사 전면 개정**. 이 기종은 실물 CAD 가 없다 —
        #    대신 탑뷰 제품사진의 **픽셀 스케일을 앵커링**해서 쟀다:
        #      앵커 : 모터 허브 반경 332.5 px = 522.5 mm(공표 대각 1045/2) → **1.5714 mm/px**
        #      교차검증(독립) : 그 스케일로 잰 암 튜브 폭 15.8 px = **24.8 mm**
        #                       ↔ 널리 알려진 S1000 **25 mm 카본 암 튜브** (0.8% 차)
        #      교차검증(독립) : 스키드 트랙 509.2 mm · 스키드 길이 455.7 mm
        #                       ↔ 공표 랜딩기어 **511 × 460 mm** (0.4% / 0.9% 차)
        #    → 스케일이 세 번 독립적으로 맞았다. 아래 MEASURED 값들의 오차대는 ~1%.
        #
        #  ⛔ 개정 전 형상과 무엇이 달랐나(전부 사진과 어긋났다):
        #    · 센터플레이트가 **지름 337 mm 원판**이었다 → 실물은 **맞변 270 mm 정팔각판**이고
        #      337.5 mm 는 판이 아니라 **암 마운트 피치원** 지름이다(사진에서 팔각 직선변 8개가
        #      그대로 보인다). 원판은 탑뷰 투영면적을 약 +48% 부풀렸다.
        #    · 암이 40→28 mm 로 가늘어지는 **둥근 직사각 테이퍼**였다 → 실물은 등단면 **원형 25 mm**.
        #    · 판 간격이 84 mm(총 96 mm)였다 → 실물 사진의 샌드위치는 40 mm 급.
        #    · 착륙장치가 단면 2.6×2.6 mm 봉 + 지름 3.8 mm·길이 286 mm 스키드, 트랙 350 mm 였다
        #      → 실물은 16 mm 급 튜브, 스키드 460 mm, **트랙 511 mm**. 실루엣이 통째로 달랐다.
        PLATE_AF = 0.290          # 팔각 카본판 **맞변거리**(MEASURED 사진 292.4, ±8 mm)
        PLATE_T = 0.0025          # 판 두께(DERIVED — 카본판 2~3 mm 급)
        PLATE_GAP = 0.040         # 상·하판 사이 빈 간격(MEASURED 사진 비율, ±5 mm)
        MOUNT_R = 0.16875         # 암 마운트 피치원 반경 = 공표 센터프레임 337.5/2 (VERIFIED)
        ARM_OD = 0.025            # 카본 암 튜브 외경 (MEASURED 24.8 → 25 mm 급)
        z_top = PLATE_GAP / 2 + PLATE_T          # 상판 윗면
        z_bot = -(PLATE_GAP / 2 + PLATE_T)       # 하판 아랫면
        for m in _body_plate_stack(PLATE_AF, PLATE_AF, PLATE_T, PLATE_GAP, PLATE_T,
                                   shape="octa", n_post=8, post_r=0.008, post_inset=0.72,
                                   plate_seg=64, post_seg=12):
            A.add(m, "body")
        for i, a in enumerate(motor_angles(spec)):
            ca, sa = np.cos(np.radians(a)), np.sin(np.radians(a))
            #  암 마운트 블록(플라스틱/알루미늄) — 판 가장자리에서 피치원까지, 스택 높이를 채운다
            #    (팔각판의 **꼭짓점이 곧 암 방향**이다 — 맞변 법선이 0/45/90/…° 이므로
            #     꼭짓점은 22.5+45k°, 사진의 '앞면 직선변 + 45° 모따기'와 정확히 일치한다)
            blk = box(0.048, 0.046, PLATE_GAP + 2 * PLATE_T, center=(0.154, 0.0, 0.0))
            A.add(rot_z(blk, a), "body")
            #  등단면 25 mm 카본 튜브 — 테이퍼도 벤드도 없다(사진: 곧은 파이프)
            A.add(_arm_tube(r, a, ARM_OD, 0.130, z0=0.0, z1=0.0), "arm")
            #  빨간 접이 잠금 레버 — 마운트 블록 **위**, 상판보다 높게 튀어나온다(사진의 상징)
            A.add(box(0.026, 0.021, 0.018,
                      center=(0.163 * ca, 0.163 * sa, z_top + 0.009)), "accent")
            #  모터 마운트 클램프 + 벨(DJI 4114) — 팔 끝 위.
            #  ⚠ 클램프를 **사각판**으로 두면 그 모서리가 모터 벨(반경 26 mm)보다 밖으로 나가
            #    프레임 bbox 를 키우고, envelope(1016 mm = 모터 벨 끝-끝)이 그만큼 전체를 줄여
            #    **유효 대각이 1045 → 1018 mm(−2.5%)** 로 무너진다(실측 확인). 벨과 같은 반경의
            #    원판으로 두면 bbox 에 아무것도 더하지 않는다 — 실물도 튜브를 감싸는 원형 클램프다.
            A.add(cyl(0.026, 0.006, center=(r * ca, r * sa, ARM_OD / 2 + 0.003), seg=24), "motor")
            bell = _motor_bell(0.026, 0.030)
            bell.apply_translation([r * ca, r * sa, ARM_OD / 2])
            A.add(bell, "motor")
        #  착륙장치 — 좌우 1조, 조당 **굵은 스플레이 스트럿 1 + 전후 스키드 1**(사진 확인).
        #    트랙 511 · 스키드 460 · 높이 305 는 공표 "Landing Gear 460 × 511 × 305 mm" 이고,
        #    앞의 두 개는 탑뷰 사진에서 455.7 / 509.2 로 **독립 재현**됐다.
        SKID_Z = -(0.3050 + PLATE_T + PLATE_GAP / 2) + 0.008    # 스키드 축 z(바닥 = 하판밑 −305)
        for g, m in _gear_tall_tube(z_bot, 0.020, 0.016, 0.016, 30.9,
                                    leg_top_y=0.090, leg_x=0.0, skid_len=0.460,
                                    skid_axis_z=SKID_Z,
                                    foam_od=0.020, foam_len=0.028, foam_inner=0.202,
                                    top_clamp=(0.034, 0.030, z_bot - 0.020, z_bot),
                                    foot_clamp=(0.046, 0.030, 0.024)):
            A.add(m, g)
        #  리트랙트 액추에이터 가는 봉 2개 — 몸통에서 스트럿 중간까지(사진에 은색으로 보인다)
        for sy in (1, -1):
            t = np.linspace(0, 1, 6)[:, None]
            p0 = np.array([0.0, sy * 0.045, z_bot])
            p1 = np.array([0.0, sy * 0.170, 0.5 * (z_bot - 0.020 + SKID_Z)])
            A.add(sweep((1 - t) * p0 + t * p1,
                        lambda s: rounded_rect(0.008, 0.008, 0.003, pts=16), n_pts=14), "gear")
        for g, m in _gimbal_hanging(0.10, 0.075, 0.10, 0.0, -0.077, n_lens=1):
            A.add(m, g)
        #  상단 배터리팩(6S 15 Ah 급, 스트랩 고정) — 셸이 없으므로 **직접 노출된 금속면**이다
        A.add(box(0.175, 0.075, 0.055, center=(0, 0, z_top + 0.0275)), "battery")
        #  판 사이 전원분배/ESC 보드
        A.add(box(0.150, 0.120, 0.003, center=(0, 0, 0.0)), "pcb")
        #  전방 GPS 퍽 — 중앙 꼭대기가 아니라 **상판 앞 가장자리 브래킷**(탑뷰 사진)
        A.add(cyl(0.019, 0.012, center=(0.150, 0, z_top + 0.020), seg=20), "accent")
        A.add(cyl(0.006, 0.020, center=(0.150, 0, z_top + 0.010), seg=12), "body")

    elif key == "typhoonh480":
        # ------------------------------------------------------------------ #
        #  Yuneec Typhoon H480 — 헥사. **저장소에서 유일하게 실물 CAD 가 있는 표적**이므로
        #  이 분기는 비율식을 하나도 쓰지 않는다: 전부 그 CAD 실측 좌표다.
        #    출처 assets/meshes/reference/*.stl (ethz-asl/rotors_simulator, Apache-2.0)
        #          + rotors_gazebo/models/typhoon_h480/typhoon_h480.sdf (파트 포즈·회전방향)
        #    CAD 신뢰도 보정(공표값 대비): 동체 455.4×520.3 ↔ 457×520 (−0.35% / +0.07%),
        #      모터원 485.6 ↔ 480 (+1.17%), 프롭 230.2 ↔ 9.0 in (+0.7%), 팁 716.2 ↔ 711 (+0.73%).
        # ------------------------------------------------------------------ #
        #  ⛔ 개정 전에는 이 기체가 **접이식 소비자기 공용 경로**(`_body_folding` + `_canopy`)를
        #    탔고, 그 결과 사진·CAD 어느 쪽과도 닮지 않았다:
        #      · 셸이 283 × 198 × 179 mm 의 **거대한 달걀**이었다(실물 196 × 150 × 117 = +44/+32/+53%),
        #      · 그 달걀이 **로터면 위로 +98 mm 솟아** 있었다 — 실물 셸 천장은 로터면 **아래 48 mm** 다,
        #      · 평면형이 실물과 **앞뒤가 뒤집혀** 있었다(실물은 코가 가장 길고 r=100, 허리가 74,
        #        꼬리가 배터리면이라 평평한 96 — 눈물방울 로프트는 정확히 그 반대를 만든다),
        #      · 암이 상반각 0°(실물 +17.8°)의 굵은 테이퍼 각재였다,
        #      · 착륙장치가 단면 2.6 mm 봉 + 지름 3.8 mm·길이 101 mm 스키드, 트랙 128 mm 였다
        #        (실물 12/10 mm 튜브, 스키드 275 mm, 트랙 288 mm, 발포 슬리브 24.5 mm),
        #      · 짐벌이 **4파트 중 1파트**(카메라 볼)뿐이었다 — 위쪽 145 mm 구조물이 통째로 없었다,
        #      · 기수 초음파 트랜스듀서 2개가 없었다.
        #
        #  좌표 규약: 우리 프레임의 z=0 은 **모터 스테이션에서 암 튜브 축**이다.
        #    실물 CAD 의 base_link up 좌표계에서 그 높이는 +45.7 mm 이므로 `_c()` 로 옮긴다.
        #    (그래야 rotor_layout 이 주는 prop_z 와 여기 형상이 같은 원점을 쓴다.)
        Z0 = 45.7                                   # base_link up[mm] → 우리 z=0
        def _c(u_mm):                               # noqa: E306  (CAD up[mm] → 우리 z[m])
            return (u_mm - Z0) / 1000.0

        #  ── 셸 평면형 r(ψ) [mm] — 실물 CAD 표면 150만점 샘플링(암 섹터 ±16° 제외 후 보간)
        #     코 100.0 · 앞허리 75.2 · 옆 78.0 · 뒷허리 75.7 · 꼬리 96(배터리 평면).
        PSI = (0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180)
        RAD = (100.0, 98.5, 92.0, 82.0, 75.2, 76.5, 78.0, 78.0, 75.7, 82.0, 90.0, 96.0, 96.0)
        pl = _planform_poly(PSI, [v / 1000.0 for v in RAD])
        A.add(_body_profiled(pl, _c(-83.48), _c(33.9), _c(0.0),
                             p_up=4.0, p_dn=2.4, cap_up=0.80, cap_dn=0.25, n_sec=19), "body")
        #  상단 캐노피 — 실물은 셸 천장(+29.1)에서 4.8 mm 더 솟은 크라운(+33.9)에 세로 슬롯 벤트
        A.add(_body_profiled(_aff_scale(pl, 0.62), _c(24.0), _c(37.0), _c(24.0),
                             p_up=2.4, p_dn=2.0, cap_up=0.55, cap_dn=0.92, n_sec=7), "canopy")

        #  ── 암 6개 — 카본 튜브 OD 12.00(암 3방향 실측 12.002/12.005/12.005),
        #     상반각 +17.75°(실측 17.82/17.73/17.71, s=140~202 선형피팅), 노출구간 s=130~203,
        #     뿌리 페어링 s=95~135 폭 40.6→15.4, 모터 포드 s=225~262 (35.4 W × 47.8 H).
        DIH, ARM_OD = 17.75, 0.01200
        #  ⚠ 모터 스테이션은 **스펙 대각 480/2 = 240 mm** 를 쓴다(사용자 매뉴얼 VERIFIED).
        #    실물 CAD 는 242.80 으로 +1.17% 크지만, 프롭을 놓는 `rotor_layout` 이 스펙 대각을
        #    쓰므로 여기서 CAD 값을 쓰면 포드와 프롭이 2.8 mm 어긋난다(조용한 오류).
        s_mot = r
        for a in motor_angles(spec):
            ca, sa = np.cos(np.radians(a)), np.sin(np.radians(a))
            for part, m in _arm_dihedral(a, 0.128, 0.228, _c(8.96), DIH, ARM_OD,
                                         collar=(0.095, 0.135, 0.0406, 0.0154)):
                #  ⚠ 재질 주의: 실물은 **노출 튜브 73 mm 만 카본**이고 뿌리 칼라·포드는 플라스틱이다.
                #    지금은 spec.arm_style 규약(='body')을 그대로 따라 둘 다 셸 그룹에 넣는다 —
                #    재질 분리는 RCS 파급(|Γ| 0.90↔0.28 = 10.1 dB)이 있어 **별도 라운드**의 결정이다.
                A.add(m, "arm" if spec.arm_style == "carbon" else "body")
            A.add(rot_z(_motor_pod(s_mot, 0.0, _c(50.9), 0.0354, 0.0370, 0.0478), a), "body")
            #  모터 벨 + 프롭 허브 축 — 포드 위로 나와 프롭(z=+36.5)까지 이어진다
            A.add(cyl(0.009, 0.009, center=(s_mot * ca, s_mot * sa, _c(70.0)), seg=20), "motor")
            A.add(cyl(0.0135, 0.012, center=(s_mot * ca, s_mot * sa, _c(78.0)), seg=24), "motor")

        #  ── 기수 초음파 트랜스듀서 2개(전방 충돌감지) — 이 기체 기수면의 **유일한 돌출부**.
        #     2016 플랫폼이라 어안 배열·LiDAR·하방비전은 아예 없다(§5 VERIFIED) →
        #     `_fisheye`·`_lidar` 를 부르지 않는다. 대신 없던 이 둘을 넣는다.
        for sy in (1, -1):
            for m in _ultrasonic(0.0955, sy * 0.021, _c(-39.0), 0.0085, 0.008):
                A.add(m, "camera")

        #  ── CGO3+ 3축 짐벌 4파트 (전부 실물 STL bbox; 위치는 SDF 조인트 체인)
        for m in _gimbal_cgo3([("box", 29.3, -90.18, 82.55, 76.94, 70.80),    # 방진 마운트판
                               ("box", 7.8, -137.41, 79.20, 43.80, 75.27),    # 요(yaw) 암
                               ("box", 21.1, -161.97, 82.51, 80.48, 42.36),   # 롤 요크
                               ("ball", 41.8, -164.12, 69.30, 55.00, 72.31)],  # 카메라 볼 + 렌즈
                              z_off_mm=-Z0):
            A.add(m, "camera")

        #  ── 착륙장치 — 스트럿 OD 12.00, 스키드 노출 OD 10.00 + **EVA 발포 슬리브 OD 24.5**
        #     (|fwd| 85~137.5, 즉 양 끝 52.5 mm). 스키드 길이 275.0, 축 |left| 144.16 → 트랙 288.3.
        #     ⚠ 스플레이 32.0° 는 **실측 29.7° 와 다르다**: 29.7° 는 up −40~−190 구간 피팅이고,
        #       발끝의 T커넥터가 마지막 18 mm 에서 |left| 를 123.5→144.2 로 더 밀어낸다.
        #       직선 스트럿 하나로 **피벗(|left| 39~40.5)과 스키드 축(144.16)을 동시에** 맞추려면
        #       32.0° 가 된다. 두 끝점이 실측이고 중간 굽힘만 흡수한 것이다.
        for g, m in _gear_tall_tube(_c(-30.0), 0.010, 0.01200, 0.01000, 32.0,
                                    leg_top_y=0.0392, leg_x=0.0, skid_len=0.2750,
                                    skid_axis_z=_c(-207.99),
                                    foam_od=0.0245, foam_len=0.0525, foam_inner=0.0850,
                                    top_clamp=None, foot_clamp=(0.048, 0.024, 0.024)):
            A.add(m, g)

        #  ── 내부 금속 산란체. 실물의 배터리 팩은 **후면 전체 + 배 불룩이**를 이룬다
        #     (그래서 CAD 의 꼬리 r≈96 이 평평하고 배 최저점 −83.5 가 후방 중심선에 있다).
        A.add(box(0.110, 0.095, 0.055, center=(-0.045, 0, _c(-55.0))), "battery")
        A.add(box(0.100, 0.090, 0.004, center=(0.0, 0, _c(20.0))), "pcb")

    else:
        #  ⭐ 2026-07-30: 열린 프레임(성형 셸 없음) 분기. 기존 5종은 전부 body_style="shell".
        open_frame = getattr(spec, "body_style", "shell") == "plate_stack"
        x500, arm_tip_r = False, None      # 셸형 분기에서도 이름이 있어야 한다(아래에서 읽는다)
        if open_frame:
            if not spec.plate_mm or len(spec.plate_mm) != 5:
                raise ValueError(
                    f"build_frame_cad: body_style='plate_stack' 인데 plate_mm 이 없다/모양이 틀렸다 "
                    f"(key={key!r}, plate_mm={spec.plate_mm!r}). (L, W, t_bottom, gap, t_top) [mm] 5개다.")
            L, W, t_bot, gap, t_top = (float(v) / 1000.0 for v in spec.plate_mm)
            H = t_bot + gap + t_top
            #  ⚠ 같은 치수가 **두 곳에** 적혀 있다 — plate_mm(메쉬가 쓰는 것)과 body_l/w/h_mm
            #    (`_drone_dims`·viz_diagram 이 쓰는 것). 어긋나면 그림과 메쉬가 다른 기체를
            #    그리는데 **예외가 안 난다** → 여기서 일치를 강제한다(열린 프레임은 판이 곧 동체다).
            want = (L * 1000.0, W * 1000.0, H * 1000.0)
            got = (float(spec.body_l_mm), float(spec.body_w_mm), float(spec.body_h_mm))
            if max(abs(a - b) for a, b in zip(want, got)) > 1e-6:
                raise ValueError(
                    f"build_frame_cad: 열린 프레임(key={key!r})의 body_l/w/h_mm={got} 가 "
                    f"plate_mm 에서 나오는 {want} 와 다르다. 열린 프레임은 **판이 곧 동체**이므로 "
                    f"둘을 같게 적어야 한다(H = t_bottom + gap + t_top).")
            #  ⚠ 셸형은 bl/bw/bh 를 '셸 치수 × 비율' 로 잡지만, 열린 프레임엔 셸이 없다 —
            #    **판 치수가 곧 기준 치수**다. 아래 짐벌/착륙장치/산란체가 이 값을 쓴다.
            bl, bw, bh = L, W, H
            z_deck_top = round(gap / 2 + t_top, 12)      # 상판 **윗면**  (FC 가 여기 얹힌다)
            z_deck_bot = round(-(gap / 2 + t_bot), 12)   # 하판 **아랫면**(배터리·다리가 여기 붙는다)
            #  ⭐ 2026-07-30 형상 정정(x500v2 만 해당): 판 외곽을 **팔각형**(45° 챔퍼)으로 만들고
            #    가짜 스탠드오프 기둥을 없앤다. 실물의 상·하판을 잇는 것은 기둥이 아니라
            #    네 모서리의 나일론 암 클램프다(아래에서 만든다). 근거는 X500V2 표 주석.
            x500 = (key == "x500v2")
            for m in _body_plate_stack(L, W, t_bot, gap, t_top, shape="rect",   # noqa: E128
                                       chamfer=(X500V2["plate_chamfer_mm"] / 1000.0) if x500 else None,
                                       posts=not x500):
                A.add(m, "deck")
            #  튜브 시작 반경. x500v2 는 **CAD 실측**(67.15 mm), 그 외 열린 프레임은 옛 DERIVED 비율.
            hub_r = X500V2["arm_tube_r0_mm"] / 1000.0 if x500 else 0.35 * min(L, W)
            arm_tip_r = X500V2["arm_tube_r1_mm"] / 1000.0 if x500 else None
            if spec.arm_style != "carbon":
                raise ValueError(
                    f"build_frame_cad: 열린 프레임(key={key!r})의 arm_style={spec.arm_style!r} 이 "
                    f"'carbon' 이 아니다 → 아래에서 암이 **'body' 그룹**으로 들어간다. 열린 프레임엔 "
                    f"셸이 없는데 'body' 는 rcs_sbr 의 유전체 셸(투과) 규약 대상이라, 있지도 않은 "
                    f"셸을 광선이 통과하게 된다. 플라스틱 암이 실제라면 전용 그룹을 새로 만들 것"
                    f"(DRONE_GROUP_MAT · union 목록 · gazebo DENSITY 세 곳 등록).")
        else:
            L = spec.body_l_mm / 1000.0
            W = spec.body_w_mm / 1000.0
            H = spec.body_h_mm / 1000.0
            #  ⭐ 2026-07-30: 셸 비율을 기종별 표(_SHELL_SHAPE)로 뺐다. 표에 없는 기종은
            #    _SHELL_DEFAULT = 옛 하드코딩 값 그대로 → 그 기종들의 메쉬는 **비트동일**이다.
            #    (옛 코드는 `0.40 if key != "phantom4" else 0.66` 처럼 **한 기종만 예외**라
            #     사진과 맞춰야 할 기종이 늘어날수록 조건식이 길어지는 구조였다.)
            sh = _SHELL_SHAPE.get(key, _SHELL_DEFAULT)
            bl = L * sh["fl"]                                # 동체 자체 길이(암 제외)
            bw = W * sh["fw"]
            bh = H * sh["fh"]

            A.add(_body_folding(bl, bw, bh, nose_drop=sh["ndrop"], n_pow=sh["npow"],
                                hw_f=sh["hw"], hh_f=sh["hh"], zo_f=sh["zo"]), "body")
            A.add(_canopy(bl, bw, bh * sh["cfh"], x0=sh["cx0"], frac=sh["cfrac"]), "canopy")

            hub_r = sh["hubf"] * max(bl, bw)

        arm_r0 = 0.055 * diag if not spec.fixed_arm else 0.085 * diag
        arm_r1 = 0.035 * diag if not spec.fixed_arm else 0.060 * diag
        #  ⭐ 2026-07-30 사진대조: 대각비례 대신 **실측 폭**을 쓰는 기종 표(_ARM_WIDTH).
        #    phantom4 — 실물 암은 셸 일체 페어링으로 뿌리 폭 45 mm → 끝 30 mm 다
        #    (docs/drone_specs_2026.json silhouette, 상면사진 _5 와 부합).
        #    옛 대각비례는 뿌리 59.5 · 끝 42.0 mm 로 각각 +32% / +40% 였다.
        if key in _ARM_WIDTH:
            arm_r0, arm_r1 = (v / 2000.0 for v in _ARM_WIDTH[key])
        mot_r, mot_h = 0.052 * diag, 0.048 * diag
        #  ⭐ **대각비례 탈출** (2026-07-30). 위 세 줄은 접이식 소비자기 5종에서 역산한 비율이라
        #    500 mm 개발 프레임에 그대로 쓰면 **반경 27.5 mm(폭 55 mm) 암**과 **지름 52 mm 모터**가
        #    나온다 — 실물은 16 mm 파이프에 28 mm 급 모터다. 에러는 안 나고 σ 만 틀린다.
        #    스펙에 실측 부품치수가 있으면 비율을 **덮는다**(None 이면 옛 식 그대로 → 기존 5종 불변).
        #    drones._arm_motor_dims 가 프롭 장착 높이에 **같은 오버라이드**를 적용한다.
        if getattr(spec, "arm_od_mm", None) is not None:
            arm_r0 = arm_r1 = float(spec.arm_od_mm) / 2000.0          # 등단면(테이퍼 없음)
        if getattr(spec, "motor_dia_mm", None) is not None:
            mot_r = float(spec.motor_dia_mm) / 2000.0
        if getattr(spec, "motor_h_mm", None) is not None:
            mot_h = float(spec.motor_h_mm) / 1000.0
        tube_arm = getattr(spec, "arm_shape", "folding") == "tube"

        for i, a in enumerate(motor_angles(spec)):
            ca, sa = np.cos(np.radians(a)), np.sin(np.radians(a))
            #  ⭐ 2026-07-31 — 반경은 **로터마다** 다를 수 있다(사다리꼴 기체). `r` 은 스칼라
            #     대푯값이므로 여기서 덮어쓰면 뒤의 다리·짐벌이 마지막 로터 값을 물려받는다
            #     → 반드시 지역 이름(`r_k`)을 쓴다.
            r_k = r_list[i]
            grp = "arm" if spec.arm_style == "carbon" else "body"
            if tube_arm:
                #  ⭐ 튜브는 모터축까지 가지 않는다. X500 V2 는 튜브가 r=232.15 에서 끝나고
                #    그 위에 **카본 물방울꼴 모터마운트 판**(r 206.4~270.65)이 얹혀 모터를 든다.
                #    예전엔 튜브를 모터축(r=250)까지 뽑고 판을 안 만들어서 암 끝이 밋밋했다.
                A.add(_arm_tube(arm_tip_r if arm_tip_r else r_k, a, arm_r0 * 2.0, hub_r,
                                z0=0.0, z1=0.0), grp)
            else:
                #  단면비(h_ratio·c_ratio)는 기종별이다 — 기본 (1.35, 0.55) 는 옛 하드코딩 값.
                #    matrice4e : 실물은 **원형 튜브**(사진 실측 ≈17 mm, 매뉴얼급 자료 18~22 mm)
                #                → (2.0, 1.0) 로 정사각+최대모서리 = 원.
                #    phantom4  : 실물은 셸과 일체로 성형된 **납작 페어링**(뿌리 45 → 끝 30 mm 폭,
                #                높이는 폭의 절반쯤) → (0.98, 0.40).
                _hr, _cr = _ARM_SECTION.get(key, (1.35, 0.55))
                A.add(_arm_folding(r_k, a, arm_r0, arm_r1, hub_r,
                                   z0=0.0, z1=0.012 * diag, bend=0.06 if not spec.fixed_arm else 0.02,
                                   h_ratio=_hr, c_ratio=_cr),
                      grp)
            if x500:
                _x500v2_arm_tip(A, a, ca, sa, gap, t_bot, t_top, mot_r, mot_h)
            else:
                bell = _motor_bell(mot_r, mot_h)
                bell.apply_translation([r_k * ca, r_k * sa, 0.014 * diag])
                A.add(bell, "motor")
            if spec.accent_rgb is not None and ca > 0.1:
                A.add(cyl(arm_r1 * 1.35, 0.06 * diag,
                          center=(r_k * ca * 0.80, r_k * sa * 0.80, 0.006 * diag), axis="x", seg=16),
                      "accent")

        # 짐벌 — 기종별 실루엣
        nose_x = 0.50 * bl
        v2 = getattr(spec, "cad_version", "v1") == "v2"
        if key == "mavic4pro":
            if v2:
                #  ⭐ 2026-07-30 사진대조 라운드 — Hasselblad 짐벌 **치수·위치 정정**.
                #  실물(mavic 4 pro_2.png 확대 · _4.png): 기수 **아래에 매달린 큰 검은 볼**이고
                #  앞으로 튀어나온 통이 아니다. 좌우폭이 동체 셸 폭(≈112 mm)의 85% 수준(≈95 mm),
                #  앞뒤 깊이는 그보다 **얕다**(납작한 배럴). 정면에 큰 사각 메인렌즈 1 + 아래 원형 2.
                #  ⛔ 옛 값 s=0.038·cz=-0.07·bh 는 (a) 볼이 작고 (b) 기수보다 **앞**에 놓여 있어,
                #     비등방 외형보정(sx0.78/sz1.84)까지 겹치면서 정면컷에서 '거대한 계란'이 됐다.
                gx = nose_x - 0.030               # 하우징이 기수 아래로 물려 들어간다
                for g, m in _gimbal_hasselblad(0.050, gx, -0.30 * bh):
                    A.add(m, g)
                A.add(box(0.030, 0.032, 0.032, center=(nose_x - 0.012, 0, -0.05 * bh)), "camera")  # 기수-짐벌 연결 마운트
                # 어안 비전 — 전방 2(앞면)·하방 2(배)·상방 2(등판), 전부 본체 표면에 밀착(bh 절반=0.5 안쪽)
                for (cxf, dy, dz, rr) in [(0.96, -0.24, 0.02, 0.009), (0.96, 0.24, 0.02, 0.009),    # 전방(앞면)
                                          (0.30, -0.26, -0.40, 0.009), (0.30, 0.26, -0.40, 0.009),  # 하방(배)
                                          (-0.10, -0.24, 0.40, 0.009), (-0.10, 0.24, 0.40, 0.009)]: # 후방-상방(등판)
                    for g, m in _fisheye(nose_x * cxf, dy * bw, dz * bh, rr):
                        A.add(m, g)
                for g, m in _lidar(nose_x * 0.99, 0.12 * bh, 0.010):    # 전방 LiDAR — 기수 정면 고정창(짐벌 위, 스펙 확인)
                    A.add(m, g)
            else:
                for g, m in _gimbal_infinity(0.032, nose_x + 0.006, -0.12 * bh):   # 볼 지름 64mm
                    A.add(m, g)
        elif key == "matrice4e":
            if v2:
                #  ⭐ 2026-07-30 사진대조 라운드 — 짐벌·RTK·비콘·어안 위치를 전부 실측에 맞췄다.
                #  큐브형 3축 측량 짐벌: 정면 68(폭) × 74(높이), 깊이 60 mm, 기수 앞 ~35 mm 돌출.
                #  ⭐ 2026-07-31 치수·높이 재측정 (정면컷 _1, 축척은 앞 로터쌍 641.55 px = 362.7 mm
                #     로 앵커 → 기수 평면에서 0.522 mm/px, 앙각 19.2°):
                #       롤 배럴 포함 폭 160 px = 83 mm · 카메라 블록 폭 114 px = **59 mm** ·
                #       블록 정면 높이 85 px / cos19.2° = **47 mm**.
                #     옛 값 68 × 74 × 60 은 높이가 **+57 %** 였다. 게다가 이 helper 는 선언 h 의
                #     0.48배를 아래로, 0.81배를 위로 더 붙이므로 실제 세로 실루엣은 선언값의
                #     ~1.3배다 — 그래서 '카메라' 그룹이 사진에 없는 자리를 메쉬만 채우고 있었다.
                #     z 는 블록 바닥이 발끝보다 ~8 mm 위에 오도록 잡는다(사진에서 최하단은 항상 발).
                for g, m in _gimbal_sensor_v2(0.059, 0.047, 0.052, nose_x - 0.004, -0.60 * bh):
                    A.add(m, g)
                #  ★ 상단-후방 RTK 원통 — 이 기종의 결정적 식별점. 지름 44 · 높이 32 mm,
                #    중심은 동체 중앙보다 27% 뒤(상면사진 실측). 윗면은 평평하고 봉은 없다.
                #  ⚠ 2026-07-31: 셸이 낮아졌으므로(fh 0.669→0.594) 같은 0.44·bh 는 돌출을 26.6 mm
                #    로 만든다. 측면사진의 돌출은 21.9 mm 라 밑동을 0.42·bh 로 낮춘다(밑동은 여전히
                #    셸 crown 0.50·bh 안쪽이라 공중에 뜨지 않는다).
                A.add(_rtk_cylinder(-0.27 * bl, 0.42 * bh, 0.046, 0.043, 0.032), "canopy")
                #  충돌방지 비콘 — 상면 **꼬리쪽 중심선**(상면사진에서 금색 렌즈). 옛 코드는
                #  중앙 부근에서 좌우로 6% 치우친 자리에 있었다.
                A.add(cyl(0.007, 0.005, center=(-0.44 * bl, 0.0, 0.36 * bh), seg=16), "accent")
                # 어안 6개 — 전방**코너** 2 · 후방**숄더** 2 · 벨리하방 2
                #   (상면사진: 앞 2개는 기수 양 모서리에, 뒤 2개는 암 뿌리 어깨에 있다.)
                for (cx, cy, cz) in [(0.44 * bl, -0.31 * bw, 0.02 * bh), (0.44 * bl, 0.31 * bw, 0.02 * bh),
                                     (-0.36 * bl, -0.36 * bw, 0.20 * bh), (-0.36 * bl, 0.36 * bw, 0.20 * bh),
                                     (0.06 * bl, -0.24 * bw, -0.40 * bh), (0.06 * bl, 0.24 * bw, -0.40 * bh)]:
                    for g, m in _fisheye(cx, cy, cz, 0.009):
                        A.add(m, g)
            else:
                for g, m in _gimbal_sensor(0.055, 0.052, 0.062, nose_x + 0.012, -0.34 * bh):
                    A.add(m, g)
                A.add(revolve(np.array([[0, 0], [0.030, 0], [0.028, 0.012], [0.016, 0.024], [0, 0.028]]),
                              seg=32, center=(-0.10 * bl, 0, 0.52 * bh)), "canopy")   # RTK 돔
                A.add(cyl(0.004, 0.05, center=(-0.10 * bl, 0, 0.52 * bh + 0.04), seg=10), "pcb")
        elif key == "phantom4":
            for g, m in _gimbal_hanging(0.052, 0.048, 0.056, nose_x * 0.62, -0.62 * bh, n_lens=1):
                A.add(m, g)
            for dy in (-0.22, 0.22):                                  # 전방 비전(스테레오)
                A.add(cyl(0.006, 0.008, center=(nose_x * 0.96, dy * bw, -0.18 * bh),
                          axis="x", seg=12), "camera")
            for dy in (-0.20, 0.20):                                  # 후방 비전(스테레오)
                A.add(cyl(0.006, 0.008, center=(-0.42 * bl, dy * bw, -0.16 * bh),
                          axis="x", seg=12), "camera")
            for sy in (-1, 1):                                        # 측면 3D IR
                #  ⚠ 2026-07-30 수정: y 를 0.52·bw → **0.44·bw**. 셸 반폭은 0.475·bw 이므로
                #    0.52 는 껍질 **밖 9.7 mm** 에 떠 있었다(옛 치수에서도 8.6 mm 떠 있었다).
                #    공중에 뜬 파트는 에러 없이 산란만 더한다 — 표면에 물리게 넣는다.
                A.add(box(0.008, 0.005, 0.012, center=(-0.02 * bl, sy * 0.44 * bw, -0.14 * bh)), "camera")
            for dy in (-0.14, 0.14):                                  # 하방 비전
                A.add(cyl(0.005, 0.006, center=(0.06 * bl, dy * bw, -0.46 * bh), axis="z", seg=10), "camera")
            #  상단 GPS/컴퍼스 커버 — **납작한 원형 퍽**이지 구가 아니다. (2026-07-30 사진대조)
            #  근거: Phantom 4 Pro+ V2.0_5.png(상면) 에서 지름 ≈32 mm 의 회색 원판이
            #  DJI 로고보다 앞쪽(동체 중심에서 앞으로 ~59 mm = 0.34·bl)에 얹혀 있다.
            #  ⛔ 옛 형상: 반경 12 mm **구** — 위로 12 mm 튀어나온 혹이라 상면 실루엣이 틀렸다.
            A.add(cyl(0.016, 0.009, center=(0.34 * bl, 0, 0.50 * bh), seg=24), "canopy")
        elif key == "mini5pro":
            # ⚠ 2026-07-28: 여기는 예전에 `else:` 였다 — **묵음 catch-all**이라 새 기종 키가
            #   전부 여기로 떨어져 Mini 5 Pro 의 매달림 짐벌 + 어안 6 + 전방 LiDAR 를
            #   **카메라가 없는 기체에도** 붙였다(프로브로 실증: X500 에 190면 카메라 그룹).
            #   명시 분기로 바꾸고, 아래에 '카메라 없음'을 **선언적으로** 처리한다.
            if v2:   # 컴팩트 짐벌 + 전방향 비전(앞2·뒤2·하2) + 전방 LiDAR(Mini 5 Pro 는 Mini 최초 LiDAR 탑재, 스펙)
                #  ⭐ 2026-07-30 사진대조 라운드 — 짐벌 **치수·형상 정정**.
                #  실물(mini 5 pro_1.png 정면컷 확대): 좌우로 넓은 검은 3축 유닛(폭 ≈50 mm =
                #  셸 폭 80 mm 의 62%), 높이 ≈33 mm, 앞뒤 ≈30 mm, 아래로 요(yaw) 원통이 하나 더.
                #  ⛔ 옛 값 `_gimbal_hanging(0.020, 0.021, 0.024)` = 24×20×21 mm 상자 + 방진판.
                #     좌우폭이 실물의 40% 라 정면 실루엣에서 짐벌이 **사실상 사라져** 있었고,
                #     방진판(w·1.5 정사각)은 Phantom 류 매달림 짐벌의 특징이지 Mini 것이 아니다.
                for g, m in _gimbal_compact3(0.050, 0.033, 0.030, nose_x * 0.92, -0.30 * bh):
                    A.add(m, g)
                #  기수 정면 **검은 핀 그릴**(실물에서 가장 눈에 띄는 앞면 특징) — 어안 2개 사이.
                for g, m in _nose_grille(nose_x * 0.97, -0.06 * bh, 0.030, 0.024, 0.006):
                    A.add(m, g)
                # 전방향 비전 어안 — 실물 배치(앞면 2·등판후방 2·배 2), 본체 표면 밀착, Mavic 만큼 크게
                for (cxf, dy, dz) in [(0.92, -0.26, 0.06), (0.92, 0.26, 0.06),      # 전방(앞면, 짐벌 좌우)
                                      (-0.60, -0.24, 0.30), (-0.60, 0.24, 0.30),    # 후방(등판)
                                      (0.20, -0.24, -0.38), (0.20, 0.24, -0.38)]:   # 하방(배)
                    for g, m in _fisheye(nose_x * cxf, dy * bw, dz * bh, 0.008):
                        A.add(m, g)
                for g, m in _lidar(nose_x * 0.98, 0.14 * bh, 0.008):    # 전방 LiDAR — 기수 정면 짐벌 위(스펙 확인)
                    A.add(m, g)
            else:
                for g, m in _gimbal_hanging(0.036, 0.034, 0.040, nose_x * 0.92, -0.30 * bh, n_lens=1):
                    A.add(m, g)
        elif key == "typhoonh480":
            #  ⛔ 여기로 오면 안 된다. typhoonh480 은 2026-07-30 외형감사에서 **최상위 전용 분기**로
            #    옮겼다(실물 CAD 실측 좌표로 셸·암·짐벌·다리를 통째로 다시 짓는다).
            #    예전 이 자리의 코드는 CGO3+ 를 **4파트 중 카메라 볼 1개**로만 붙이고 있었고,
            #    그 위 145.5 mm 의 마운트판·요암·롤요크는 존재하지 않았다 — 동체 아래 유일한
            #    큰 산란체가 절반 넘게 비어 있었다는 뜻이다. 되돌리지 말 것.
            raise AssertionError(
                "build_frame_cad: typhoonh480 은 최상위 전용 분기에서 처리된다 — 여기 도달했다면 "
                "그 분기가 사라졌거나 key 비교가 깨진 것이다.")
        elif spec.gimbal_style in (None, "none"):
            pass                                # 카메라 없는 기체(예: X500 개발 프레임) — **선언적으로** 아무것도 안 붙인다
        elif spec.gimbal_style == "belly":
            #  ⭐ 2026-07-30 (Phase 3): **키가 아니라 `gimbal_style` 로 갈리는 첫 분기.**
            #    위 분기들이 전부 `key ==` 라서, 레지스트리에 없는 스펙(= 검증용 대조 기체)은
            #    Phase 1 의 catch-all 가드에 걸려 `NotImplementedError` 로 죽었다 — 실제로
            #    `benchmark/compare_community.py` 의 M100·M600(둘 다 gimbal_style='belly')이
            #    죽고 있었고, 그건 재생성 파이프라인 stage 1 이 통째로 멈추는 것이었다.
            #    표적 7종은 이 분기를 타지 않는다(s1000plus 는 자기 최상위 key 분기에서 이미
            #    _gimbal_hanging 을 직접 부르고 여기까지 내려오지 않는다) → 7종 메쉬는 불변.
            #  ⚠ 치수는 **공표값이 아니라 DERIVED 비율**이다. s1000plus 의 벨리 짐벌
            #    (100×75×100 mm)을 그 센터프레임 지름 337 mm 로 정규화한 0.30·0.22·0.30 을
            #    동체 치수에 적용한다. 대조 기체의 실루엣 대역만 맞추는 용도이며 RCS 표적이
            #    아니다 — 표적으로 승격할 때는 반드시 실측 치수로 갈아탈 것.
            g_w, g_h, g_d = 0.30 * bw, 0.22 * bh, 0.30 * bl
            for g, m in _gimbal_hanging(g_w, g_h, g_d, 0.0,
                                        -0.50 * bh - 0.5 * g_h, n_lens=1):
                A.add(m, g)
        else:
            raise NotImplementedError(
                f"build_frame_cad: 짐벌/카메라 분기가 없는 기종 key={key!r} "
                f"(gimbal_style={spec.gimbal_style!r}). 새 기종을 추가했다면 여기에 분기를 쓰거나 "
                f"gimbal_style='none'/'belly' 로 선언할 것 — 예전처럼 조용히 mini5pro 형상이 붙지 않는다.")

        # 착륙장치
        if spec.gear == "legs":
            gear_fn = _gear_arch if v2 else _gear_skids     # Phantom v2 = 아치형(inverted-U)
            #  ⭐ 다리 높이 0.42·H → **0.58·H** (2026-07-30 사진대조). 실물 Phantom 4 는
            #    벨리~발 113 mm / 셸 두께 83 mm 로 **다리가 동체보다 높다**(정면사진 실측,
            #    축척 = 공식 총높이 196 mm). 옛 조합(동체 0.52·H + 다리 0.42·H)은 그 비를
            #    거꾸로 뒤집어 놓아 "뚱뚱한 몸통에 짧은 다리"가 됐다.
            for g, m in gear_fn(bl, bw, -0.50 * bh, 0.58 * H):
                A.add(m, g)
        elif spec.gear == "feet":
            #  ⭐ Matrice 4E — 다리는 동체 밑이 아니라 **각 암 끝(모터 안쪽) 아래**에 있다.
            #    붙는 z 는 암 아랫면: 암 중심이 모터쪽에서 0.012·diag 로 올라가므로 그 위치의
            #    암 중심 z 에서 암 반높이(arm_r0·h_ratio/2)만큼 내린다.
            _hr = _ARM_SECTION.get(key, (1.35, 0.55))[0]
            z_arm = 0.012 * diag * 0.87 - arm_r0 * _hr / 2.0
            for g, m in _gear_arm_spikes(r_list, motor_angles(spec), z_arm,
                                         GEAR_SPIKE_H.get(key, 0.072), 0.014, 0.007, splay_deg=20.0):
                A.add(m, g)
        elif spec.gear == "motor_legs":
            #  ⭐ 2026-07-30 사진대조 라운드 — Mini 5 Pro · Mavic 4 Pro.
            #    두 기종 다 예전엔 gear="none" 이라 **착륙장치가 통째로 없었다.** 그런데 사진에는
            #    앞 두 모터포드 아래에 두 갈래 다리가 분명히 있고, 그게 기체의 **최하단**이다
            #    (`_gear_motor_legs` docstring 에 사진별 근거). 없으면 실루엣도 틀리고
            #    envelope 높이를 맞추느라 sz 가 부풀어 동체까지 세로로 늘어난다.
            if not getattr(spec, "gear_h_mm", None):
                raise ValueError(
                    f"build_frame_cad: gear='motor_legs'(key={key!r}) 에는 gear_h_mm[mm] 이 "
                    f"필요하다(암 아랫면에서 발까지 깊이). 현재 {spec.gear_h_mm!r}.")
            _hr = _ARM_SECTION.get(key, (1.35, 0.55))[0]
            z_arm = 0.012 * diag - arm_r1 * _hr / 2.0          # 암 끝의 아랫면
            for g, m in _gear_motor_legs(r_list, motor_angles(spec), z_arm,
                                         float(spec.gear_h_mm) / 1000.0,
                                         w=arm_r1 * 0.62, spread=mot_r * 0.95):
                A.add(m, g)
        elif spec.gear == "tall":
            # ⚠ 2026-07-28: 이 분기가 **없었다.** gear="tall" 이 조용히 무시돼 다리가 통째로
            #   사라지고 에러도 안 났다(프로브 확인: gear='tall' 결과가 gear='none' 과 동일).
            #   기존 5종은 s1000plus 가 자기 키 분기에서 _gear_tall 을 직접 부르고 있어 무사했지만,
            #   새로 추가되는 기종은 여기 떨어진다.
            if open_frame:
                #  열린 프레임은 **카본 튜브 다리**다(그룹 gear_cf). 치수를 비율로 지어내지 않고
                #  스펙에서 받는다 — 없으면 조용히 엉뚱한 다리가 생기므로 즉시 예외.
                if not getattr(spec, "gear_h_mm", None) or not getattr(spec, "gear_tube_mm", None):
                    raise ValueError(
                        f"build_frame_cad: 열린 프레임(key={key!r})의 gear='tall' 에는 "
                        f"gear_h_mm 과 gear_tube_mm=(다리OD, 스키드OD)[mm] 가 **둘 다** 필요하다 "
                        f"(현재 {spec.gear_h_mm!r} / {spec.gear_tube_mm!r}). 셸형의 0.30·body_h 규약은 "
                        f"열린 프레임에서 판 두께의 30%(수 mm)가 되어 다리가 사라진다.")
                leg_od, skid_od = (float(v) / 1000.0 for v in spec.gear_tube_mm)
                if not x500:
                    raise NotImplementedError(
                        f"build_frame_cad: 열린 프레임 gear='tall' 의 다리 배치는 이제 **실측 전용**이다"
                        f"(key={key!r}). 예전의 판 치수 비율(x_frac/y_frac/skid_len_frac)은 X500 V2 "
                        f"제조사 STEP 과 맞춰보니 다리 개수(4→2)·스키드 길이·간격이 전부 틀렸다 → 삭제했다. "
                        f"새 열린 프레임을 넣으려면 그 기체의 실측을 X500V2 처럼 표로 적을 것.")
                q = X500V2
                for g, m in _gear_tall_tube(
                        z_deck_bot, q["gear_leg_top_below_plate_mm"] / 1000.0,
                        leg_od, skid_od,
                        splay_deg=float(getattr(spec, "gear_splay_deg", 20.0)),
                        leg_top_y=q["gear_leg_top_y_mm"] / 1000.0, leg_x=0.0,
                        skid_len=q["skid_len_mm"] / 1000.0,
                        skid_axis_z=q["skid_axis_z_mm"] / 1000.0,
                        foam_od=q["foam_od_mm"] / 1000.0, foam_len=q["foam_len_mm"] / 1000.0,
                        foam_inner=q["foam_inner_x_mm"] / 1000.0,
                        #  상단 브래킷은 판 **사이**에 있다(위에서 보면 상판이 덮는다).
                        #  발 T커넥터 높이 19 = 발포 외경 → **접지점은 발포**여야 한다(공표 215 mm).
                        top_clamp=(0.040, 0.030, z_deck_bot - 0.010, gap / 2),
                        foot_clamp=(0.040, 0.026, 0.019)):
                    A.add(m, g)
            else:
                for g, m in _gear_tall(0.42 * max(bl, bw), -0.50 * bh, spec.gear_h_mm / 1000.0
                                       if getattr(spec, "gear_h_mm", None) else 0.30 * H):
                    A.add(m, g)
        elif spec.gear not in (None, "none"):
            raise ValueError(f"build_frame_cad: 모르는 gear={spec.gear!r} (key={key!r}). "
                             f"'none'|'legs'|'feet'|'tall' 중 하나여야 한다 — "
                             f"예전에는 오타가 나도 다리 없이 조용히 지나갔다.")

        if open_frame:
            # ---- 열린 프레임의 산란체 배치 (2026-07-30) --------------------------------
            #  ⚠ **왜 별도 경로인가**: 셸형(아래 else)은 battery/pcb 를 셸 치수(bl·bw·bh)의
            #    비율로 놓는다. 셸이 없는 프레임에 그 코드를 쓰면 기준이 없어 부품이 **허공에
            #    뜬다** — 그런데 예외는 안 난다(조용히 틀린 메쉬). 판 스택 기준으로 다시 잡는다.
            #  실물 킷 배치(Holybro X500 V2 Full Kit):
            #    배터리(4S LiPo)   = **하판 아래 노출**, 스트랩 고정
            #    전원분배/ESC 보드 = 판 **사이**(28 mm 간격 안)
            #    비행제어기(FC)    = **상판 위**
            #  ⭐ RCS 함의: 이 배터리는 **셸형 기체와 달리** 유전체 셸의 감쇠를 받지 않는다.
            #    (개수를 적지 않는다 — 셸형인지는 body_style 이 정한다. 예전 주석은 "셸형 5종" 이었다.)
            #    셸형에서는 광선이 플라스틱 셸을 왕복 투과(τ=1−0.28² 를 두 번)한 뒤 배터리를
            #    보지만, 열린 프레임에서는 금속 상자가 **직접** 보이는 강한 정반사체다.
            #    → 같은 크기 셸형보다 σ 가 높게 나오면 1차 용의자가 이것이다.
            ffl, ffw, ffh = OPEN_FC_FRAC
            hf = ffh * gap
            A.add(box(ffl * L, ffw * W, hf, center=(0, 0, z_deck_top + hf / 2)), "fc")
            if x500:
                #  ⭐ 2026-07-30: 배터리·전원보드·하부 구조를 **비율 상자에서 실측 형상으로** 바꿨다.
                #    옛 코드는 하판 바로 아래에 얇은 상자 하나(144×43×25)를 붙였는데, 실물은
                #    레일 2줄에 트레이가 매달리고 팩이 그 위에 얹혀 판보다 **55 mm 더 아래**에 있다.
                _x500v2_underslung(A, z_deck_bot, z_deck_top)
                #  네 모서리 나일론 암 클램프 — 상·하판을 잇는 실제 부재(스탠드오프 대체)
                q = X500V2
                c0, c1 = (v / 1000.0 for v in q["corner_clamp_r_mm"])
                cw = q["corner_clamp_w_mm"] / 1000.0
                for a in motor_angles(spec):
                    A.add(rot_z(box(c1 - c0, cw, t_bot + gap + t_top,
                                    center=(0.5 * (c0 + c1), 0.0, 0.0)), a), "accent")
            else:
                bfl, bfw, bfh = OPEN_BATTERY_FRAC
                efl, efw, efh = OPEN_ESC_FRAC
                hb = bfh * gap
                A.add(box(bfl * L, bfw * W, hb, center=(0, 0, z_deck_bot - hb / 2)), "battery")
                A.add(box(efl * L, efw * W, efh * gap, center=(0, 0, 0.0)), "pcb")
        else:
            # 내부 금속 산란체 (RCS 지배) — 셸 안이라 렌더엔 안 보이지만 PO/SBR 이 센다.
            #   배터리(Li-NMC 파우치, 최대 밀집 금속) + PCB(FR-4+구리) + 마그네슘합금 내부 구조프레임.
            #   1차출처: 프롭=나일론복합(DJI공식), 배터리 Li-NMC, DJI Mavic계열 AZ91 마그네슘 섀시,
            #   RCS 지배=배터리≈모터>짐벌/PCB (arXiv:1911.05926). → docs/drone_material_deepverify.json
            A.add(box(bl * 0.50, bw * 0.62, bh * 0.55, center=(-0.06 * bl, 0, 0.02 * bh)), "battery")
            A.add(box(bl * 0.38, bw * 0.54, bh * 0.06, center=(0.02 * bl, 0, 0.26 * bh)), "pcb")
            if v2:  # 마그네슘합금 구조 프레임(얇은 판) — 확인된 재질 명시 반영
                A.add(box(bl * 0.58, bw * 0.68, bh * 0.08, center=(-0.02 * bl, 0, -0.04 * bh)), "battery")

    # ---- 불리언: 겹친 파트의 **내부 면을 녹여 없앤다** ------------------------
    #   프리미티브를 겹쳐 놓으면 속에 파묻힌 면이 남아 PO/SBR 이 헛센다.
    #   합집합으로 하나의 껍질을 만들면 그런 면이 **애초에 존재하지 않는다.**
    #  ⚠ 새 그룹을 추가하면 **여기에도** 넣어야 한다(등록 3곳 중 두 번째:
    #    drones.DRONE_GROUP_MAT · 이 목록 · gazebo_export.DENSITY).
    #    빠지면 겹친 파트의 내부 면이 남아 PO/SBR 이 헛센다 — 예외는 안 난다.
    for g in ("body", "arm", "motor", "camera", "gear", "canopy", "accent",
              "deck", "gear_cf", "fc"):
        A.union_group(g)

    return A


def build_propeller_cad(spec, n_sec=22) -> Assembly:
    """프로펠러 1개 — **진짜 익형** 블레이드 + 허브. **모델별로 다르다**(반경·날개수·피치).

    ⚠ 2026-07-16 버그 수정 2건:
      1) chord_max 에 `0.26*R`(절대길이)를 넘겨 내부에서 R 이 한 번 더 곱해졌다 → 시위가 **R 배
         (≈7.5배) 좁아** 블레이드가 실 없이 얇았다. chord_max 는 **비율**이므로 0.26 을 넘긴다.
         (Mavic 최대시위 4.6mm → 34.7mm. 실물 DJI 프롭 ≈30mm 와 부합.)
      2) 전 모델이 기본 pitch_deg=20°·twist=13° 로 **똑같은 형상**이었다. 스펙의 prop_pitch_in
         (Mini 2.8" ~ Mavic 5.8")을 써서 θ(r)=atan(P/(2πr)) 로 **모델별 실제 피치**를 준다.
    """
    R = spec.prop_dia_mm / 1000.0 / 2.0
    P = float(spec.prop_pitch_in or 5.0) * 0.0254          # 피치[inch] → [m]
    hub_r = R * 0.085

    def _one_blade(Rb):
        # chord_max·트위스트·두께·캠버는 전부 실측 앵커(모듈 상단 상수, outputs/reference_props.json).
        # 루트는 허브 반경(0.085R)보다 **안쪽**에서 시작해 허브와 겹치게 둔다 — 실물 프롭은
        # 블레이드 생크가 허브에 물려 하나의 솔리드다. 떨어뜨리면 공중에 뜬 루트 모서리가
        # 생겨 산란에 가짜로 기여한다(간극이 λ/20~λ/8 수준이라 무시할 크기가 아니다).
        return _blade(Rb, root_frac=0.070, chord_max=CHORD_MAX_OVER_R, pitch_m=P, n_sec=n_sec)

    # ⭐ **스윕디스크 정규화** (2026-07-28 수정)
    #   제조사가 말하는 "직경" 은 프롭이 쓸고 지나가는 **원의 지름**이다. 그런데 스키미터 스윕
    #   (0.10R)과 팁 시위의 후단이 팁을 측방으로 밀어내므로, 스팬을 R 로 잡으면 실제 최대반경은
    #   r_max = R·√(1+(y_tip/R)²) > R 이 된다. 옛 코드가 그래서 5기종 전부 **+0.84%** 초과였다
    #   (report_mesh mesh_verify C_dims prop_dia err_pct 0.8397~0.8432 — 원인 미규명 상태로 방치).
    #   상수로 보정하면 법칙을 바꿀 때마다 다시 틀리므로, **빌드해서 재고 그 비율로 되돌린다.**
    probe = _one_blade(R)
    V = np.asarray(probe.vertices)
    r_max = float(np.sqrt(V[:, 0] ** 2 + V[:, 1] ** 2).max())
    scale = R / max(r_max, 1e-12)

    A = Assembly()
    A.add(_prop_hub(hub_r, R * 0.09), "prop")
    for b in range(spec.prop_blades):
        bl = _one_blade(R * scale)
        A.add(rot_z(bl, (360.0 / spec.prop_blades) * b), "prop")
    A.union_group("prop")
    return A
