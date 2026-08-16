# -*- coding: utf-8 -*-
"""
mesh_symmetry.py — **대칭 · 손잡이 · 파생량** 검사 (감사 지도의 M11 · M13 칸)
==============================================================================
왜 따로 있나 (2026-08-16)
  `src/mesh_check.py` 는 «메쉬가 스스로 앞뒤가 맞는가»(구멍·법선·겹침)와 «치수가 스펙과
  맞는가»를 본다. 그 두 층을 **전부 통과하면서도 틀릴 수 있는** 자리가 남는다:

    · **손잡이(handedness)** — 프로펠러의 비틀림 방향. 네 로터에 전부 같은 프롭을 달아도
      수밀·법선·구멍·치수는 **하나도 안 걸린다**(2026-07-28 에 실제로 났던 버그).
    · **좌우 대칭** — 동체·암·다리·카메라가 좌우로 어긋나도 위 검사는 전부 통과한다.
    · **로터 회전방향 배치 규약** — «이웃끼리 반대로 돈다» 가 깨져도 안 걸린다. 각도·반경은
      스펙 그대로인데 **도는 방향만** 물리적으로 틀린 기체가 조용히 통과한다.
    · **파생량**(질량중심·관성·투영면적) — 성분이 서로 상쇄되면 부분 검사는 전부 통과하는데
      합은 틀린다. 투영면적은 PO 평판 극한에서 σ ∝ A² 이라 **σ 의 1차 결정자**다.

  감사 지도(`outputs/mesh_cert_map_0816.json`)가 이 두 칸을 이렇게 적어 놓았다:
    M11 대칭   — 「프롭 축만 본다. **기체 좌우 대칭과 로터 방향 배치 규약은 검사가 없다**」
    M13 파생량 — 「부피는 **부호만** 본다. …**이 라운드에서 파생량 축 양성 대조는 안 돌렸다**」
  이 파일이 그 두 문장을 지운다.

⭐ 이 파일이 지키는 규약 — **검사마다 자가 둘이다.**
  하나만 있으면 «0 이 나오는 자»와 «0 이 맞는 대상»을 구별할 수 없다. 그래서 축마다
  **서로 다른 원리의 자 두 개**를 대 본다. 질량·관성과 투영면적에서는 둘이 어긋나는 것
  자체를 결함으로 치고(양성 대조 있음), 손잡이에서는 감시값으로만 둔다
  (⚠양성 대조를 못 만들었다 — `twist_by_positions` 주석에 그대로 적어 뒀다).
    · 손잡이   : 자A = **법선**의 접선성분(mesh_check 와 같은 수식) / 자B = **위치**만 쓰는
                 (방위 편차 × 높이 편차) 공분산. 자B 는 감김(winding)을 아예 안 본다.
    · 좌우대칭 : 자A = 거울 점구름 → 원본 **표면**까지 거리(표본추출 차이에 안 흔들린다)
                 자B = 면적·부피의 **1차 모멘트**(적분량이라 표본추출과 무관)
    · 질량/관성: 자A = trimesh 의 mass_properties / 자B = **발산정리 손계산**(trimesh 미경유)
    · 투영면적 : 자A = **실루엣 래스터화**(가려진 면은 한 번만 센다)
                 자B = **한쪽면 합** Σ max(n̂·û,0)·A_f (PO 가 실제로 더하는 양)
                 둘의 비 = «PO 가 몇 배로 이중계상하는가».

⭐ 자 자체의 검정 — 답을 아는 도형에 대 본다(`selftest_rulers()`).
    · 한 변 1 m 정육면체: 축방향 투영면적 = 1.000000 m², 대각선 방향 = √3 = 1.7320508 m²
    · 밀도 ρ 인 직육면체: 질량 = ρ·abc, 관성 I_xx = m(b²+c²)/12 …  (닫힌 해)
  이 검정이 실패하면 **아래 모든 수는 무효**다. 그래서 check_all 이 맨 먼저 돌린다.

⭐ 무엇을 **안 하는가**(이게 «장담» 의 절반이다 — 자세한 목록은 인증서의 `limits` L1~L8):
  · 손잡이의 **절대 기준**은 `build_propeller(spec)` 에서 읽는다. 즉 «어느 회전방향이 어느
    비틀림인가» 는 **가정**이다 — 저장소 전체가 같은 방향으로 뒤집혀 있으면 안 걸린다(L1).
  · **기체 전체 거울상**은 결함이 아니라서 안 잡는다(L2). 이웃 로터가 반대로 도는 배치라
    통째로 뒤집으면 «로터 번호만 바꿔 단 같은 기체» 가 된다.
  · 질량·관성의 **크기**는 판정하지 않는다 — 메쉬 부피×밀도 질량이 공표 TOW 의 1.1~5.0 배다
    (감사 I9). 여기서 판정하는 것은 **좌우 불변량 · 물리적 타당성 · 두 자의 일치**뿐이다(L3).
  · 앞뒤·상하 대칭은 우리 기체가 원래 안 가진 대칭이라 검사 대상이 아니다. 그래서 **180° 요
    회전은 이 축이 못 잡는다**(작은 요 회전은 좌우 대칭을 깨므로 잡힌다)(L7).

⛔ 이 파일은 **형상을 하나도 안 바꾼다.** 읽고 재고 판정만 한다.
   (2026-08-16 현재 다른 라운드들이 짐벌·다리·모터z·축간거리를 실제로 바꾸는 중이다.)

실행:
  cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/mesh_symmetry.py
  ⛔ GPU 안 쓴다(전부 CPU). 파일도 안 쓴다 — 원장은 benchmark/mesh_cert_symmetry_derived_0816.py 가 쓴다.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


# =========================================================================== #
#  검사 잣대(예산표)
#
#  ⚠ 이 저장소의 기존 규약 그대로 — 아래 수는 **«지금 이만큼이다» 라는 선언**이지
#    «이만큼이 옳다» 가 아니다. 2026-08-16 전수 실측으로 초기화했고, 새로 생기는
#    비대칭은 예산을 넘겨 **실패한다**.
#  ⭐ 다만 이 파일의 예산은 두 종류로 **성격이 다르다**. 섞으면 안 된다:
#      (가) **불변량 예산** — 형상이 바뀌어도 0 이어야 하는 것(좌우대칭 잔차·CoM_y·Ixy·
#           프롭 짝맞춤). 병행 라운드가 치수를 바꿔도 이 값들은 0 근처에 있어야 한다.
#           ⇒ 게이트에 넣는다. 여기가 이 파일의 본체다.
#      (나) **크기 스냅샷** — 질량·관성 주값·투영면적처럼 형상이 바뀌면 같이 변하는 값.
#           ⇒ 게이트에 **안 넣는다**. 원장에 싣고 회귀는 골든 지문이 본다.
# =========================================================================== #

#  ⑴ 좌우(y) 거울 대칭 — 그룹별 **표면 잔차** RMS 예산 [mm].
#     잣대: 거울 뜬 정점 → 원본 **삼각형 표면**까지의 최단거리(점-대-점이 아니다).
#     왜 표면인가: 로프트 셸은 정점을 좌우로 똑같이 찍지 않는다. 점-대-점으로 재면
#     «표본추출이 다르다»가 «형상이 비대칭이다»로 둔갑한다(실측: s1000plus body
#     점-대-점 max 22.97 mm ↔ 표면 max 0.05 mm — 형상은 완벽히 대칭이었다).
LATERAL_SURF_RMS_BUDGET_MM = {
    #  기본값 0.15 mm — 실측 전 기종·전 그룹이 0.000~0.106 mm 다.
    #  ⚠ 이 0.1 mm 급 잔차의 정체는 **형상 비대칭이 아니라 면 분할(tessellation)**이다.
    #    로프트·회전체는 좌우에 정점을 똑같이 안 찍으므로, 거울 뜬 정점이 반대편 **면(현)**
    #    위에 떨어지면서 sagitta 만큼 어긋난다. 반경 10 mm·20분할 원통의 sagitta 는
    #    r(1−cos(π/20)) = 0.123 mm — 관측된 크기와 같은 급이다.
    #    이 주장은 추측이 아니라 대조로 확인한다: `benchmark/adv_mesh_symmetry_faults.py`
    #    의 «홀수 분할 원통» 항목이 **완벽히 대칭인 솔리드**를 비대칭 분할로 지어 같은 자로
    #    재고, 잔차가 해석 sagitta 안에 드는지 본다.
    "_default": 0.15,
    #  ↓ 선언된 **설계 의도** 비대칭. 실물이 비대칭이라 메쉬도 비대칭인 자리다.
    ("matrice4e", "camera"): 0.55,    # 실측 0.484
    #     근거: drone_cad.py `_gimbal_sensor_v2` 의 «정면 2×2 개구» 표가 좌우를 **일부러**
    #     다르게 짓는다 — 좌상 텔레(원형 r=0.155w) · 우상 미디엄텔레(사각 0.135w) ·
    #     우하 광각(0.175w, 가장 큼) · 좌하 레이저 거리계(0.085w). 실물 Matrice 4E 정면
    #     제품컷과 같은 배치다. 즉 **결함이 아니라 실물 충실도**다.
    ("m350rtk", "gear_cf"): 0.22,     # 실측 0.194 — 카본 튜브 다리(근거 미확인, 한계선언 L4)
}

#  ⑵ 프로펠러 **짝맞춤** — 거울 뜬 로터 k 의 프롭을 짝 로터 k′ 축 둘레로 Δ 만큼 돌리면
#     k′ 의 프롭과 **정확히** 겹쳐야 한다.
#     Δ 는 상수로 박지 않고 `rotor_layout` 에서 **매번 다시 읽는다**: Δ = base_ang[k]+base_ang[k′].
#     (지금 규약 base_ang = 각도 + 12° 에서는 Δ = 24° 가 나온다. 실측 전 기종 잔차 0.0000 mm.)
PROP_MIRROR_MAX_MM = 1.0e-6         # 마이크로미터 — 사실상 «부동소수 오차 말고는 0»

#  ⑶ 질량중심 · 관성의 **좌우 불변량**. 좌우대칭 기체는 이 넷이 원리적으로 0 이다.
#     정규화: CoM_y 는 기체 bbox 대각으로, 관성곱은 관성 주값 최대치로 나눈다(무차원).
COM_Y_BUDGET_REL = 2.0e-4           # |CoM_y| / bbox대각.  실측 최대 6e-6
PRODUCT_INERTIA_BUDGET_REL = 5.0e-4  # |Ixy|,|Iyz| / max(I_ii).  실측 최대 3e-5
PRINCIPAL_TILT_BUDGET_DEG = 0.5     # 관성 주축이 기체축(x,y,z)에서 벗어난 각. 실측 최대 0.03°

#  ⑷ 두 자의 일치 — 질량·부피·관성을 trimesh 와 손계산이 얼마나 다르게 보는가 [상대]
MASS_RULER_AGREE_REL = 1.0e-9

#  ⑸ 투영면적
PROJ_NPX = 1024                     # 실루엣 래스터 한 변 픽셀 수(정육면체 검정 오차 +0.08 %)
PROJ_MIRROR_TOL_REL = 8.0e-3        # 실루엣 A(방위 φ) ↔ A(−φ) 상대차. 프레임(비프롭) 기준(실측 최대 4.7e-3).
#     ⚠ 이 3e-3 은 **래스터의 잡음 바닥**이지 형상 허용오차가 아니다(같은 형상을 서로 다른
#       픽셀 격자에 두 번 그리면 그만큼 다르게 나온다). 그래서 훨씬 날카로운 자를 하나 더 건다:
PROJ_MIRROR_ONESIDED_TOL_REL = 5.0e-3   # **한쪽면 합**으로 잰 프레임 전체 좌우차(실측 최대 3.3e-3)
#  ⑸-2 ⭐ 한쪽면 합의 **그룹별** 좌우차 — 어느 부품이 좌우로 어긋났는지 **집어낸다**.
#     이 표가 이 라운드의 새 발견이다: 비대칭은 거의 전부 **착륙다리(gear·gear_cf)** 에 몰려
#     있고, 그것도 **빌더 종류를 따라간다** — gear='motor_legs'·'legs' 는 7.3e-3~2.5e-2,
#     gear='feet'(matrice4e)는 2.3e-9 로 사실상 대칭이다. 나머지 부품은 body 1e-5~2.0e-3 ·
#     canopy 1e-4 급이고 그 밖은 1e-16(부동소수 바닥)이다. 값은 2026-08-16 실측 + 약 30 % 여유.
#     ⚠ 크기의 뜻: 이건 «면적이 몇 % 다른가»가 아니라 «그 그룹의 한쪽면 합이 좌우로 몇 %
#       다른가»다. 프레임 전체로 환산하면 ≤0.33 % 다(다리는 면적이 작다).
PROJ_ONESIDED_GROUP_BUDGET = {
    "_default": 3.0e-3,               # body 1e-5~2.0e-3 · canopy 1.2e-4~2.3e-4 를 덮는다
    ("mini5pro", "gear"): 3.0e-2,     # 실측 2.22e-2
    ("mavic4pro", "gear"): 3.0e-2,    # 실측 2.48e-2
    ("phantom4", "gear"): 1.8e-2,     # 실측 1.35e-2
    ("mini2", "gear"): 1.8e-2,        # 실측 1.39e-2
    ("m350rtk", "gear_cf"): 1.2e-2,   # 실측 8.69e-3
    ("phantom3", "gear"): 1.0e-2,     # 실측 7.30e-3
}
PROJ_RULER_CAL_TOL_REL = 3.0e-3     # 정육면체 닫힌해 대비 래스터 오차 허용

#  ⑸-3 **이중계상 배수** = (한쪽면 합) ÷ (실루엣). «PO 가 실루엣의 몇 배를 더하는가».
#     ⚠ 성격이 다르다 — 이건 불변량이 아니라 **크기 스냅샷**이다(형상이 바뀌면 같이 변한다).
#       그래도 예산에 넣는 이유: **면적 이중계상**(같은 부품을 두 번 얹기 · 부품이 서로 파고들기)이
#       이 수를 곧장 밀어 올리는데, 다른 어떤 검사도 «투영 쪽에서» 그걸 안 본다.
#     ⛔ 형상이 바뀌면 이 표는 **다시 선언해야 한다**(실패 메시지가 그렇게 말한다).
#     값 = 2026-08-16 실측 최대 × 약 1.15.
PROJ_DOUBLE_COUNT_BUDGET = {
    "_default": 2.6,
    "mini5pro": 2.5,     # 실측 최대 2.245  ⭐주력 표적
    "mavic4pro": 2.4,    # 실측 최대 2.093  ⭐주력 표적
    "matrice4e": 2.3,    # 실측 최대 2.027
    "s1000plus": 2.4,    # 실측 최대 2.118
    "phantom4": 2.2,     # 실측 최대 1.925
    "typhoonh480": 2.0,  # 실측 최대 1.769
    "x500v2": 2.5,       # 실측 최대 2.196
    "phantom3": 1.9,     # 실측 최대 1.697
    "m350rtk": 2.2,      # 실측 최대 1.906
    "mini2": 2.5,        # 실측 최대 2.235
}
#     ⭐ «한쪽면 합 ≥ 실루엣» 은 닫힌 껍질에서 **원리적으로 참**이다(광선이 물체를 맞히면
#        반드시 앞면을 하나 이상 맞힌다). 이 부등식이 깨지면 자가 고장난 것이다.
PROJ_ONESIDED_GE_SIL_TOL_REL = 5.0e-3

#  ⑹ 로터 손잡이 지표의 최소 크기 — 이보다 작으면 «날이 안 비틀렸다»는 뜻이라 부호를 못 믿는다.
#     실측: 자A |h| = 0.16~0.29, 자B |h| = 0.85~0.94.
HAND_MIN_ABS_A = 0.05
HAND_MIN_ABS_B = 0.20


# =========================================================================== #
#  0.  자 검정 — 답을 아는 도형
# =========================================================================== #
def _unit_box(lo=(0.0, 0.0, 0.0), hi=(1.0, 1.0, 1.0)):
    """축정렬 직육면체 (정점, 면). 법선은 **바깥**(부호부피 > 0)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    V = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)], float)
    #  인덱스 = 4i+2j+k
    F = np.array([[0, 3, 1], [0, 2, 3],      # x−
                  [4, 5, 7], [4, 7, 6],      # x+
                  [0, 1, 5], [0, 5, 4],      # y−
                  [2, 7, 3], [2, 6, 7],      # y+
                  [0, 4, 6], [0, 6, 2],      # z−
                  [1, 3, 7], [1, 7, 5]], int)
    #  ⚠ 위 차례는 법선이 **안쪽**을 보는 순서다(손계산 부호부피로 확인 — 질량이 −129.57 kg
    #    으로 나왔다). 뒤집어서 내보낸다. 검정 도형이 안쪽 법선이면 검정 자체가 무의미하다.
    return V, F[:, ::-1].copy()


def selftest_rulers(npx: int = PROJ_NPX) -> dict:
    """⭐ **자 검정** — 닫힌 해가 있는 도형에 대 본다. 여기가 틀리면 아래 전부 무효다.

    ① 한 변 1 m 정육면체의 투영면적: 축방향 1.000000 m², 대각선(1,1,1) 방향 √3 m².
    ② 밀도 ρ, 변 (a,b,c) 직육면체: 질량 ρabc, 중심 (a,b,c)/2,
       중심 기준 관성 I_xx = m(b²+c²)/12 …
    두 질량 자(trimesh · 손계산)를 **둘 다** 이 닫힌 해에 댄다."""
    V, F = _unit_box()
    out = {"npx": int(npx)}

    #  ① 투영면적
    a_axis = silhouette_area(V, F, (0.0, 0.0, 1.0), npx=npx)
    a_diag = silhouette_area(V, F, (1.0, 1.0, 1.0), npx=npx)
    out["cube_axis_m2"] = round(float(a_axis), 8)
    out["cube_axis_err_rel"] = round(float(a_axis / 1.0 - 1.0), 8)
    out["cube_diag_m2"] = round(float(a_diag), 8)
    out["cube_diag_closed_form_m2"] = round(float(math.sqrt(3.0)), 8)
    out["cube_diag_err_rel"] = round(float(a_diag / math.sqrt(3.0) - 1.0), 8)
    #  한쪽면 합은 정육면체 축방향에서 정확히 1.0 이어야 한다(닫힌 해).
    out["cube_axis_onesided_m2"] = round(float(onesided_area(V, F, (0.0, 0.0, 1.0))), 10)

    #  ② 질량·관성 — 변 (0.3, 0.5, 0.7) m, 밀도 1234 kg/m³
    a, b, c, rho = 0.3, 0.5, 0.7, 1234.0
    Vb, Fb = _unit_box((0, 0, 0), (a, b, c))
    m_true = rho * a * b * c
    I_true = m_true / 12.0 * np.array([b * b + c * c, a * a + c * c, a * a + b * b])
    raw = mass_properties_raw(Vb, Fb, np.full(len(Fb), rho))
    tm_ = mass_properties_trimesh(Vb, Fb, rho)
    out["box_mass_true_kg"] = round(float(m_true), 10)
    out["box_mass_rawruler_kg"] = round(float(raw["mass"]), 10)
    out["box_mass_trimesh_kg"] = round(float(tm_["mass"]), 10)
    out["box_com_true_m"] = [a / 2, b / 2, c / 2]
    out["box_com_rawruler_m"] = [round(float(v), 12) for v in raw["com"]]
    out["box_I_true_diag"] = [round(float(v), 12) for v in I_true]
    out["box_I_rawruler_diag"] = [round(float(v), 12) for v in np.diag(raw["I_com"])]
    out["box_I_trimesh_diag"] = [round(float(v), 12) for v in np.diag(tm_["I_com"])]

    def rel(x, y):
        return float(abs(x - y) / max(abs(y), 1e-300))

    e = [rel(raw["mass"], m_true), rel(tm_["mass"], m_true)]
    e += [rel(raw["I_com"][i, i], I_true[i]) for i in range(3)]
    e += [rel(tm_["I_com"][i, i], I_true[i]) for i in range(3)]
    e += [rel(raw["com"][i], [a / 2, b / 2, c / 2][i]) for i in range(3)]
    out["mass_ruler_max_err_rel"] = round(float(max(e)), 12)

    out["ok"] = bool(abs(out["cube_axis_err_rel"]) <= PROJ_RULER_CAL_TOL_REL
                     and abs(out["cube_diag_err_rel"]) <= PROJ_RULER_CAL_TOL_REL
                     and abs(out["cube_axis_onesided_m2"] - 1.0) <= 1e-9
                     and out["mass_ruler_max_err_rel"] <= 1e-9)
    return out


# =========================================================================== #
#  1.  투영면적 — 자 두 개
# =========================================================================== #
def view_dir(az_deg: float, el_deg: float) -> np.ndarray:
    """방위 az(+x 기준, +y 로 증가) · 앙각 el 의 **보는 방향** 단위벡터(기체 → 관측자)."""
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)], float)


def silhouette_area(V, F, u, npx: int = PROJ_NPX) -> float:
    """⭐ 자A — **실루엣 면적** [m²]. û 방향에서 본 윤곽의 넓이. 겹쳐 있는 면은 **한 번만** 센다.

    래스터화로 잰다: û 에 수직한 평면에 삼각형을 던져 픽셀을 채우고, 픽셀이 **부분적으로**
    덮인 만큼까지 세도록 안티에일리어싱 계수를 그대로 무게로 쓴다(픽셀당 0~1).
    정육면체 닫힌 해 대비 오차는 npx=1024 에서 −0.005 %(축) / +0.075 %(대각선)다."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    u = np.asarray(u, float)
    u = u / np.linalg.norm(u)
    #  û 에 수직한 정규직교 기저
    a = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(a, u)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    P = np.c_[V @ e1, V @ e2]
    lo, hi = P.min(0), P.max(0)
    span = hi - lo
    pad = 0.02 * float(span.max())
    lo = lo - pad
    hi = hi + pad
    span = hi - lo
    fig = plt.figure(figsize=(npx / 100.0, npx / 100.0), dpi=100)
    try:
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(lo[0], hi[0])
        ax.set_ylim(lo[1], hi[1])
        ax.axis("off")
        ax.add_collection(PolyCollection(P[F], facecolors="k", edgecolors="none",
                                         antialiaseds=True))
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())[:, :, 0].astype(np.float64)
    finally:
        plt.close(fig)
    cov = float(((255.0 - buf) / 255.0).sum())
    px = (span[0] / buf.shape[1]) * (span[1] / buf.shape[0])
    return cov * px


def onesided_area(V, F, u) -> float:
    """⭐ 자B — **한쪽면 합** Σ max(n̂·û, 0)·A_f [m²]. **PO 가 실제로 더하는 양**이다
    (PO 는 가림을 안 본다 — rcs_po.py 자기선언). 가려진 면·파묻힌 면이 그대로 들어간다.
    닫힌 껍질에서는 항상 **실루엣 이상**이고, 둘의 비가 곧 «몇 배로 이중계상하는가»다."""
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    u = np.asarray(u, float)
    u = u / np.linalg.norm(u)
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(B - A, C - A) * 0.5          # 크기 = 면적, 방향 = 법선
    return float(np.maximum(n @ u, 0.0).sum())


def twosided_area(V, F, u) -> float:
    """Σ|n̂·û|·A_f / 2 — 닫힌 껍질에서는 한쪽면 합과 **정확히 같다**(앞뒤 면적이 같으므로).
    다르면 껍질이 안 닫혔거나 법선이 뒤섞인 것이다 — 그래서 셋째 자로 같이 잰다."""
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    u = np.asarray(u, float)
    u = u / np.linalg.norm(u)
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(B - A, C - A) * 0.5
    return float(np.abs(n @ u).sum() * 0.5)


# =========================================================================== #
#  2.  질량 · 관성 — 자 두 개
# =========================================================================== #
def _tetra_moments(V, F):
    """원점 기준 부호있는 (부피, 1차 모멘트, 2차 모멘트) — 발산정리(사면체 분해).
    trimesh 를 **전혀 안 거친다**. 면마다 값을 돌려주므로 그룹별 밀도를 곱해 합칠 수 있다."""
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    vol = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0            # 부호있는 사면체 부피
    m1 = vol[:, None] * (a + b + c) / 4.0                            # ∫x dV
    #  ∫ x xᵀ dV = V/20 · (S Sᵀ + Σ p pᵀ),  S = a+b+c  (원점이 네 번째 꼭짓점)
    S = a + b + c
    SS = S[:, :, None] * S[:, None, :]
    PP = (a[:, :, None] * a[:, None, :] + b[:, :, None] * b[:, None, :]
          + c[:, :, None] * c[:, None, :])
    m2 = vol[:, None, None] * (SS + PP) / 20.0                       # ∫ x xᵀ dV
    return vol, m1, m2


def _inertia_from_cov(M2, mass, com):
    """2차 모멘트(∫x xᵀ dm) → **질량중심 기준** 관성텐서."""
    #  원점 기준 관성 = tr(M2)·I − M2 ; 평행축 정리로 CoM 으로 옮긴다.
    I_o = np.trace(M2) * np.eye(3) - M2
    d = np.asarray(com, float)
    I_com = I_o - mass * ((d @ d) * np.eye(3) - np.outer(d, d))
    return I_com


def mass_properties_raw(V, F, rho_face) -> dict:
    """⭐ 자B — **손계산**(발산정리). 면별 밀도 배열을 받는다. trimesh 미경유."""
    vol, m1, m2 = _tetra_moments(V, F)
    rho = np.asarray(rho_face, float)
    mass = float((vol * rho).sum())
    volume = float(vol.sum())
    M1 = (m1 * rho[:, None]).sum(0)
    M2 = (m2 * rho[:, None, None]).sum(0)
    com = M1 / mass if mass != 0 else np.zeros(3)
    return dict(mass=mass, volume=volume, com=com, I_com=_inertia_from_cov(M2, mass, com),
                M2_origin=M2)


def mass_properties_trimesh(V, F, density: float) -> dict:
    """⭐ 자A — **trimesh** 의 mass_properties. `src/gazebo_export.py` 가 쓰는 것과 같은 통로.
    ⚠ `process=True`(웰딩)를 쓴다 — geom.Mesh 는 프리미티브마다 정점을 따로 쌓기 때문이다.
      웰딩은 형상을 안 바꾸므로 손계산과 **같은 답**이 나와야 한다. 안 나오면 그 자체가 결함이다."""
    import trimesh
    tm = trimesh.Trimesh(vertices=np.asarray(V, float), faces=np.asarray(F, np.int64),
                         process=True)
    tm.density = float(density)
    return dict(mass=float(tm.mass), volume=float(tm.volume),
                com=np.asarray(tm.center_mass, float),
                I_com=np.asarray(tm.moment_inertia, float))


# =========================================================================== #
#  3.  손잡이 — 자 두 개
# =========================================================================== #
def twist_by_normals(V, F, cx, cy) -> float:
    """⭐ 자A — **법선**으로 재는 비틀림 부호. `mesh_check._twist_chirality` 와 **같은 수식**이다
    (일부러 같게 뒀다 — 게이트가 쓰는 그 자를 여기서도 쓰고, 자B 로 교차검증한다).

    윗면(n_z>0) 삼각형만 골라 법선의 접선방향 성분을 면적가중 평균한다. 전면을 다 더하면
    닫힌 껍질에서 ∮(r×n)dS ≡ 0 이라 항등적으로 0 이 나오므로 윗면만 고른다."""
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(B - A, C - A)
    a2 = np.linalg.norm(n, axis=1)
    ok = a2 > 0
    if not ok.any():
        return 0.0
    nh = n[ok] / a2[ok][:, None]
    area = 0.5 * a2[ok]
    c = ((A + B + C) / 3.0)[ok]
    x, y = c[:, 0] - cx, c[:, 1] - cy
    rho = np.hypot(x, y)
    m = (rho > 1e-12) & (nh[:, 2] > 0.0)
    if not m.any():
        return 0.0
    tang = nh[m, 0] * (-y[m] / rho[m]) + nh[m, 1] * (x[m] / rho[m])
    return float((area[m] * tang).sum() / area[m].sum())


def twist_by_positions(V, F, cx, cy, n_blades: int, n_band: int = 12) -> float:
    """⭐ 자B — **위치만** 쓰는 비틀림 부호. 감김도 법선도 안 본다.

    어떻게: 반경을 띠로 자르고, 띠마다 삼각형 중심의 (방위 편차 δφ, 높이 편차 δz) 의
    면적가중 **상관계수**를 낸다. 날이 비틀려 있으면 앞전이 높고 뒷전이 낮으므로 상관이 선다.
    날 n 장은 방위로 360/n 주기라 «원형 평균»으로 접어 한 장처럼 본다.
    부호가 뒤집히는 이유: y 거울에서 φ → −φ 이고 z 는 그대로라 상관의 부호가 뒤집힌다.

    왜 자가 둘이어야 하나(정직판) — 자A 는 **법선·감김** 경로를 타고 자B 는 **정점** 만 탄다.
    두 경로 중 하나에 버그가 나도 나머지가 남으므로 «0 이 나오는 자»와 «0 이 맞는 대상»을
    구별할 수 있다. 그리고 자B 는 조건이 훨씬 좋다 — 실측 |자B| = 0.85~0.94 인데 |자A| 는
    0.16~0.29 라, «비틀림이 부호를 믿을 만큼 큰가»라는 문턱이 자B 에서 3~5 배 안전하다.
    ⚠ **여기까지가 근거다.** 처음에 «감김만 뒤집으면 두 자가 갈린다»고 적었는데 **틀렸다** —
      실측하니 자A 는 크기만 −0.2448 → −0.2728 로 변하고 **부호는 안 뒤집힌다**(윗면 선택
      n_z>0 이 뒤집힌 아랫면을 대신 고르기 때문이다). 그 결함은 `mesh_check` 의 안쪽법선·
      손계산 부호부피가 잡는다. 그래서 아래 `rulers_agree` 필드는 **양성 대조가 없고**,
      «있다»고 치지 않는다(감시값으로만 남긴다). 대조 파일의 [한계] 항목에 그대로 적혀 있다."""
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    nb = max(int(n_blades), 1)
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    ar = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    c = (A + B + C) / 3.0
    x, y, z = c[:, 0] - cx, c[:, 1] - cy, c[:, 2]
    rho = np.hypot(x, y)
    phi = np.arctan2(y, x)
    ok = (ar > 0) & (rho > 1e-9)
    if not ok.any():
        return 0.0
    ar, rho, phi, z = ar[ok], rho[ok], phi[ok], z[ok]
    R = float(rho.max())
    edges = np.linspace(0.25 * R, 0.98 * R, n_band + 1)   # 허브·팁 끝은 뺀다
    num = den = 0.0
    for i in range(n_band):
        m = (rho >= edges[i]) & (rho < edges[i + 1])
        if int(m.sum()) < 8:
            continue
        a, p, zz = ar[m], phi[m], z[m]
        mu = np.angle((a * np.exp(1j * nb * p)).sum()) / nb      # 원형 평균(날 n장 접기)
        d = (p - mu + np.pi / nb) % (2.0 * np.pi / nb) - np.pi / nb
        w = a.sum()
        db = (a * d).sum() / w
        zb = (a * zz).sum() / w
        sd = math.sqrt(float((a * (d - db) ** 2).sum() / w)) * \
            math.sqrt(float((a * (zz - zb) ** 2).sum() / w))
        if sd <= 0:
            continue
        num += w * float((a * (d - db) * (zz - zb)).sum() / w) / sd
        den += w
    return float(num / den) if den > 0 else 0.0


# =========================================================================== #
#  4.  공통 — 로터별 프롭 삼각형 나누기 · 거울 짝 찾기
# =========================================================================== #
def _rotor_frame(spec):
    """로터 배치를 한 번만 읽어 (중심[mm], dir, base_ang, 방위각[deg]) 로 돌려준다."""
    from drones import rotor_layout
    rl = rotor_layout(spec)
    C = np.asarray([r["center"] for r in rl], float) * 1000.0
    d = np.asarray([r["dir"] for r in rl], int)
    ba = np.asarray([r["base_ang"] for r in rl], float)
    phi = np.degrees(np.arctan2(C[:, 1], C[:, 0]))
    return C, d, ba, phi


def _mirror_partner(phi: np.ndarray) -> list[int]:
    """방위 φ 인 로터의 **거울 짝**(방위 −φ). 없으면 −1."""
    out = []
    for i in range(len(phi)):
        dd = np.abs(((-phi[i] - phi) + 180.0) % 360.0 - 180.0)
        j = int(np.argmin(dd))
        out.append(j if float(dd[j]) < 1.0 else -1)
    return out


def _prop_labels(V_mm, F_prop, C_mm) -> np.ndarray:
    """프롭 삼각형을 가장 가까운 로터 축에 배정한다."""
    Cp = V_mm[F_prop].mean(1)
    return np.linalg.norm(Cp[:, None, :2] - C_mm[None, :, :2], axis=2).argmin(1)


def _rotz(P, cx, cy, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    x, y = P[:, 0] - cx, P[:, 1] - cy
    return np.c_[cx + ca * x - sa * y, cy + sa * x + ca * y, P[:, 2]]


# =========================================================================== #
#  검사 ① — 로터 손잡이 (자 둘)
# =========================================================================== #
def check_rotor_handedness(spec, mesh=None, verbose=False) -> dict:
    """**로터 손잡이** — 로터마다 날 비틀림 방향이 그 로터의 회전방향(dir)과 맞는가.
    ⭐ **자 둘로 각각 판정하고, 둘이 어긋나는 것도 결함으로 친다.**

    기준(«어느 쪽이 dir=+1 인가»)은 코드에 박지 않고 **매번 `build_propeller(spec)` 에서
    다시 읽는다** — 규약이 바뀌면 기준도 같이 따라간다.

    표적은 실제로 위험한 둘이다(감사 I6 D4 의 정정):
      · 네 로터에 **전부 같은 손잡이** 프롭 (2026-07-28 에 났던 버그)
      · **한 로터만** 손잡이가 뒤집힘
    ⭐ 한계 — **기체 전체 거울상은 이 검사가 안 잡고, 안 잡는 게 맞다.** 이웃 로터가 반대로
      도는 배치라 통째로 뒤집으면 프롭이 «반대 회전방향을 가진 다른 로터 자리»로 옮겨가면서
      손잡이도 같이 뒤집힌다 — 두 번 뒤집혀 제자리다. 즉 «로터 번호만 바꿔 단 같은 기체»다."""
    from drones import build_drone, build_propeller
    m = mesh if mesh is not None else build_drone(spec)
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    if not (G == "prop").any():
        return dict(key=spec.key, checked=False, ok=True, reason="prop 그룹 없음")
    p = build_propeller(spec)
    Vr = np.asarray(p.v, float) * 1000.0
    Fr = np.asarray(p.f, np.int64)
    hA_ref = twist_by_normals(Vr, Fr, 0.0, 0.0)
    hB_ref = twist_by_positions(Vr, Fr, 0.0, 0.0, spec.prop_blades)
    if abs(hA_ref) < HAND_MIN_ABS_A or abs(hB_ref) < HAND_MIN_ABS_B:
        return dict(key=spec.key, checked=False, ok=True,
                    reason=f"기준 프롭의 비틀림이 너무 작다(|A|={abs(hA_ref):.4f}, "
                           f"|B|={abs(hB_ref):.4f}) — 부호를 믿을 수 없다")
    C, dirs, ba, phi = _rotor_frame(spec)
    Fp = F[G == "prop"]
    lab = _prop_labels(V, Fp, C)
    rows, bad = [], []
    for i in range(len(C)):
        sel = lab == i
        if not sel.any():
            bad.append(f"rotor{i}: 프롭 삼각형이 하나도 없다")
            continue
        hA = twist_by_normals(V, Fp[sel], C[i, 0], C[i, 1])
        hB = twist_by_positions(V, Fp[sel], C[i, 0], C[i, 1], spec.prop_blades)
        wantA = float(np.sign(hA_ref) * dirs[i])
        wantB = float(np.sign(hB_ref) * dirs[i])
        okA = (abs(hA) >= HAND_MIN_ABS_A) and (np.sign(hA) == wantA)
        okB = (abs(hB) >= HAND_MIN_ABS_B) and (np.sign(hB) == wantB)
        #  두 자의 일치 = «기준과 같은 손잡이인가» 라는 판정이 서로 같은가
        agree = bool((np.sign(hA) == np.sign(hA_ref)) == (np.sign(hB) == np.sign(hB_ref)))
        rows.append(dict(rotor=i, dir=int(dirs[i]), h_normals=round(float(hA), 5),
                         h_positions=round(float(hB), 5), ok_normals=bool(okA),
                         ok_positions=bool(okB), rulers_agree=agree))
        if not okA:
            bad.append(f"rotor{i}(dir {dirs[i]:+d}) 자A(법선) h={hA:+.4f}, 기대부호 {wantA:+.0f}")
        if not okB:
            bad.append(f"rotor{i}(dir {dirs[i]:+d}) 자B(위치) h={hB:+.4f}, 기대부호 {wantB:+.0f}")
        if not agree:
            bad.append(f"rotor{i} ⭐두 자가 어긋난다 — 법선 {hA:+.4f} vs 위치 {hB:+.4f} "
                       f"(정점은 그대로인데 감김만 뒤집혔을 때 이렇게 된다)")
    res = dict(key=spec.key, checked=True,
               h_ref_normals=round(float(hA_ref), 5), h_ref_positions=round(float(hB_ref), 5),
               per_rotor=rows, failures=bad, ok=not bad)
    if verbose:
        print(f"  손잡이(자 둘): 기준 A {hA_ref:+.4f} / B {hB_ref:+.4f} · 로터 {len(rows)}개 "
              f"{'✅' if res['ok'] else '❌'}" + (f"  {bad}" if bad else ""))
    return res


# =========================================================================== #
#  검사 ② — 로터 회전방향 **배치 규약**
# =========================================================================== #
def check_rotor_dir_convention(spec, verbose=False) -> dict:
    """**로터 배치 규약** — 메쉬가 아니라 `rotor_layout(spec)` 자체를 검사한다.

    멀티로터의 규약 넷(전부 물리에서 온다):
      ⑴ **이웃 반대** : 방위각으로 정렬했을 때 옆 로터는 반대로 돈다 → 반작용 토크가 상쇄된다.
      ⑵ **마주보는 쌍** : ⑴에서 **따라 나오는** 관계다 — d[k+n/2] = d[k]·(−1)^(n/2).
         ⭐ 즉 «대각쌍은 같다» 는 **n/2 가 짝수일 때만**(쿼드 n/2=2 · 옥토 n/2=4) 참이고,
           **헥사(n/2=3)에서는 마주보는 쌍이 서로 반대로 돈다.** `drones.rotor_layout` 의
           독스트링은 조건 없이 «대각쌍 동일» 이라고 적는데 typhoonh480(6로터)이 반례다 —
           메쉬 결함이 아니라 **문서의 문장이 좁다**. 이 검사는 n 에서 기대값을 유도해 본다.
      ⑶ **토크 합 0** : CW 와 CCW 의 수가 같다.
      ⑷ **거울 짝** : 방위 φ 인 로터의 거울 자리(−φ)에 로터가 있고, 반경·높이가 같고,
         회전방향은 **반대**다(거울상 프롭은 반대로 돈다).

    왜 필요한가: `rotor_layout` 은 회전방향을 **목록 순서**로 정한다(`dir = +1 if k%2==0`).
    즉 `rotor_deg` 를 방위 순서가 아닌 차례로 적으면 규약이 **조용히** 깨진다 — 각도도 반경도
    전부 스펙대로인데 도는 방향만 물리적으로 틀린 기체가 된다. 어떤 위상·치수 검사도 못 본다."""
    C, dirs, ba, phi = _rotor_frame(spec)
    n = len(C)
    order = np.argsort(phi)                    # 방위각 순서
    ds = dirs[order]
    bad = []

    alt = [bool(ds[k] * ds[(k + 1) % n] < 0) for k in range(n)]
    if not all(alt):
        bad.append(f"이웃이 같은 방향으로 돈다 — 방위순 dir {ds.tolist()}")

    opp_ok = True
    opp_expect = None
    if n % 2 == 0:
        opp_expect = int((-1) ** (n // 2))          # ⑴에서 유도 — 하드코딩하지 않는다
        opp_ok = all(bool(ds[(k + n // 2) % n] == opp_expect * ds[k]) for k in range(n // 2))
        if not opp_ok:
            bad.append(f"마주보는 쌍의 관계가 이웃규약과 안 맞는다 — n={n} 이면 "
                       f"d[k+n/2] = {opp_expect:+d}·d[k] 여야 한다. 방위순 dir {ds.tolist()}")

    torque = int(dirs.sum())
    if torque != 0:
        bad.append(f"토크 합이 0 이 아니다 — Σdir = {torque} (CW/CCW 수가 다르다)")

    part = _mirror_partner(phi)
    rho = np.hypot(C[:, 0], C[:, 1])
    mir_rows = []
    for i, j in enumerate(part):
        if j < 0:
            bad.append(f"rotor{i}(φ={phi[i]:.2f}°) 의 거울 짝이 없다")
            mir_rows.append(dict(rotor=i, partner=None))
            continue
        d_rho = float(rho[j] - rho[i])
        d_z = float(C[j, 2] - C[i, 2])
        d_ok = bool(dirs[i] * dirs[j] < 0) if i != j else True
        mir_rows.append(dict(rotor=i, partner=j, d_radius_mm=round(d_rho, 6),
                             d_z_mm=round(d_z, 6), dir_opposite=d_ok,
                             delta_phase_deg=round(float(ba[i] + ba[j]), 6)))
        if abs(d_rho) > 1e-6:
            bad.append(f"rotor{i}↔{j} 거울 짝의 반경이 다르다 ({d_rho:+.4f} mm)")
        if abs(d_z) > 1e-6:
            bad.append(f"rotor{i}↔{j} 거울 짝의 높이가 다르다 ({d_z:+.4f} mm)")
        if not d_ok:
            bad.append(f"rotor{i}↔{j} 거울 짝인데 회전방향이 같다 (dir {dirs[i]:+d}/{dirs[j]:+d})")

    res = dict(key=spec.key, checked=True, n_rotors=n,
               azimuth_deg=[round(float(v), 4) for v in phi],
               dir=[int(v) for v in dirs], azimuth_sorted_dir=[int(v) for v in ds],
               neighbors_alternate=bool(all(alt)),
               opposite_pair_expected_sign=opp_expect, opposite_pairs_ok=bool(opp_ok),
               torque_sum=torque, mirror_pairs=mir_rows, failures=bad, ok=not bad)
    if verbose:
        print(f"  로터 배치 규약: 이웃반대 {res['neighbors_alternate']} · 마주보는쌍 "
              f"{res['opposite_pairs_ok']}(기대부호 {opp_expect:+d}) · Σdir {torque}"
              f"  {'✅' if res['ok'] else '❌'}")
    return res


# =========================================================================== #
#  검사 ③ — 좌우(y) 거울 대칭
# =========================================================================== #
def _surface_mirror_residual(V_mm, F_local):
    """거울 뜬 정점 → 원본 **표면**까지 최단거리의 (RMS, 최대) [mm].
    ⚠ 점-대-점이 아니다 — 로프트 셸은 정점을 좌우로 똑같이 안 찍으므로 점-대-점으로 재면
      «표본추출 차이»가 «비대칭»으로 둔갑한다."""
    import trimesh
    if len(F_local) == 0:
        return 0.0, 0.0
    tm = trimesh.Trimesh(vertices=np.asarray(V_mm, float),
                         faces=np.asarray(F_local, np.int64), process=False)
    Q = np.asarray(V_mm, float).copy()
    Q[:, 1] = -Q[:, 1]
    _, d, _ = trimesh.proximity.closest_point(tm, Q)
    d = np.asarray(d, float)
    return float(np.sqrt((d ** 2).mean())), float(np.abs(d).max())


def _lateral_moments(V_mm, F):
    """면적·부피의 **y 1차 모멘트**(적분량 자) — 표본추출과 무관하다.
    좌우대칭이면 둘 다 0 이다. 정규화는 (면적·크기)/(부피·크기)."""
    V = np.asarray(V_mm, float)
    F = np.asarray(F, np.int64)
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nv = np.cross(B - A, C - A)
    ar = 0.5 * np.linalg.norm(nv, axis=1)
    cy = (A[:, 1] + B[:, 1] + C[:, 1]) / 3.0
    tot_a = float(ar.sum())
    size = float(np.linalg.norm(V.max(0) - V.min(0)))
    m_area = float((ar * cy).sum()) / max(tot_a * size, 1e-300)
    vol, m1, _ = _tetra_moments(V, F)
    tot_v = float(vol.sum())
    m_vol = float(m1[:, 1].sum()) / max(abs(tot_v) * size, 1e-300)
    return m_area, m_vol, tot_a, tot_v, size


def check_lateral_symmetry(spec, mesh=None, verbose=False) -> dict:
    """**좌우 거울 대칭** — 기체를 y→−y 로 뒤집으면 자기 자신과 겹쳐야 한다.

    ⭐ 프롭은 **따로** 본다. 이유가 있다 — `rotor_layout` 이 로터마다 프롭을 `base_ang`
      («각도 + 12°») 위상으로 세워 놓기 때문에, 거울 짝 두 로터의 날은 정확히
      Δ = base_ang[k] + base_ang[k′] 만큼 어긋나 있다(지금 규약에서 **24°**). 이건 정지 위상일
      뿐이고 프롭은 돈다 — 결함이 아니다. 그래서 프롭은 «거울 뜬 뒤 Δ 만큼 돌려서» 견준다.
      Δ 는 상수로 안 적고 rotor_layout 에서 다시 읽는다.
      ⇒ 실측: 전 기종 · 전 로터 잔차 **0.000000 mm**(부동소수 오차 이하). 즉 프롭 좌우 짝은
        **정확히** 맞는다. 이 검사는 그래서 µm 예산으로 조인다.

    프레임(비프롭)은 **표면 잔차**(자A)와 **1차 모멘트**(자B) 두 자로 본다."""
    from drones import build_drone
    m = mesh if mesh is not None else build_drone(spec)
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    size = float(np.linalg.norm(V.max(0) - V.min(0)))
    bad = []

    #  ── 자A: 그룹별 표면 잔차 ─────────────────────────────────────────────── #
    groups = {}
    for g in sorted(set(G.tolist())):
        if g == "prop":
            continue
        f = F[G == g]
        used = np.unique(f)
        remap = np.zeros(int(used.max()) + 1, np.int64)
        remap[used] = np.arange(len(used))
        rms, mx = _surface_mirror_residual(V[used], remap[f])
        budget = float(LATERAL_SURF_RMS_BUDGET_MM.get(
            (spec.key, g), LATERAL_SURF_RMS_BUDGET_MM["_default"]))
        ok = bool(rms <= budget)
        groups[g] = dict(n_faces=int(len(f)), surf_rms_mm=round(rms, 5),
                         surf_max_mm=round(mx, 5), budget_mm=budget, ok=ok)
        if not ok:
            bad.append(f"{g} 좌우 표면잔차 {rms:.4f} mm > 예산 {budget} mm")

    #  ── 자B: 1차 모멘트(적분량) ────────────────────────────────────────────── #
    nonp = G != "prop"
    ma, mv, tot_a, tot_v, _ = _lateral_moments(V, F[nonp])
    if abs(ma) > COM_Y_BUDGET_REL:
        bad.append(f"프레임 면적 y-모멘트 {ma:+.3e} > {COM_Y_BUDGET_REL:.1e}")
    if abs(mv) > COM_Y_BUDGET_REL:
        bad.append(f"프레임 부피 y-모멘트 {mv:+.3e} > {COM_Y_BUDGET_REL:.1e}")

    #  ── bbox 대칭 ─────────────────────────────────────────────────────────── #
    #  ⚠ **프레임(비프롭) bbox 로만 판정한다.** 프롭을 넣으면 정지 위상(base_ang) 때문에
    #    날 끝의 y 범위가 좌우로 달라진다 — 프롭이 돌면 사라지는 값이라 결함이 아니다.
    #    전체 bbox 값도 원장에 싣되(아래 full_bbox_y_offset_rel) 판정에는 안 쓴다.
    used_fr = np.unique(F[G != "prop"])
    ylo, yhi = float(V[used_fr, 1].min()), float(V[used_fr, 1].max())
    bbox_rel = abs(ylo + yhi) / max(yhi - ylo, 1e-300)
    ylo_f, yhi_f = float(V[:, 1].min()), float(V[:, 1].max())
    bbox_full_rel = abs(ylo_f + yhi_f) / max(yhi_f - ylo_f, 1e-300)
    if bbox_rel > 1e-3:
        bad.append(f"프레임 bbox 가 좌우로 치우쳤다 — (y_min+y_max)/폭 = {bbox_rel:.3e}")

    #  ── 프롭: 거울 + Δ 회전 짝맞춤 ─────────────────────────────────────────── #
    prop_rows = []
    if (G == "prop").any():
        from scipy.spatial import cKDTree
        C, dirs, ba, phi = _rotor_frame(spec)
        Fp = F[G == "prop"]
        lab = _prop_labels(V, Fp, C)
        part = _mirror_partner(phi)
        for i, j in enumerate(part):
            if j < 0:
                continue
            Pi = V[np.unique(Fp[lab == i])]
            Pj = V[np.unique(Fp[lab == j])]
            delta = float(ba[i] + ba[j])              # ⭐ 상수 아님 — 배치에서 읽는다
            Mi = Pi.copy()
            Mi[:, 1] = -Mi[:, 1]
            Mi = _rotz(Mi, C[j, 0], C[j, 1], delta)
            if len(Pj) == 0 or len(Mi) == 0:
                bad.append(f"rotor{i}↔{j} 프롭 정점이 없다")
                continue
            d1 = cKDTree(Pj).query(Mi)[0]
            d2 = cKDTree(Mi).query(Pj)[0]
            d = np.concatenate([d1, d2])
            rms = float(np.sqrt((d ** 2).mean()))
            mx = float(d.max())
            ok = bool(mx <= PROP_MIRROR_MAX_MM and len(Pi) == len(Pj))
            prop_rows.append(dict(rotor=i, partner=j, delta_deg=round(delta, 4),
                                  rms_mm=float(f"{rms:.3e}"), max_mm=float(f"{mx:.3e}"),
                                  n_pts=int(len(Pi)), n_pts_partner=int(len(Pj)), ok=ok))
            if not ok:
                bad.append(f"rotor{i}↔{j} 프롭 거울짝 잔차 {mx:.4g} mm > "
                           f"{PROP_MIRROR_MAX_MM:g} mm (Δ={delta:.2f}°)")

    res = dict(key=spec.key, checked=True, size_mm=round(size, 2), groups=groups,
               frame_area_y_moment_rel=float(f"{ma:.4e}"),
               frame_volume_y_moment_rel=float(f"{mv:.4e}"),
               bbox_y_offset_rel=float(f"{bbox_rel:.4e}"),
               #  ↓ 판정에 안 쓰는 참고값 — 프롭 정지 위상 때문에 0 이 아니다(위 주석)
               full_bbox_y_offset_rel=float(f"{bbox_full_rel:.4e}"),
               prop_mirror=prop_rows, failures=bad, ok=not bad)
    if verbose:
        worst = max((g["surf_rms_mm"] for g in groups.values()), default=0.0)
        pm = max((r["max_mm"] for r in prop_rows), default=0.0)
        print(f"  좌우대칭: 프레임 표면잔차 최대 {worst:.4f} mm · 면적 y-모멘트 {ma:+.2e} · "
              f"프롭 짝맞춤 최대 {pm:.2e} mm  {'✅' if res['ok'] else '❌'}")
    return res


# =========================================================================== #
#  검사 ④ — 질량중심 · 관성
# =========================================================================== #
def check_mass_inertia(spec, mesh=None, verbose=False) -> dict:
    """**질량중심 · 관성텐서** — 파생량은 성분이 상쇄돼도 합이 틀릴 수 있다.

    무엇을 **판정**하나(전부 «형상이 바뀌어도 0 이어야 하는» 불변량이다):
      ⑴ 물리적 타당성 — 부품 질량 > 0, 관성 고유값 > 0, **삼각부등식** I₁+I₂ ≥ I₃
      ⑵ 좌우 불변량 — |CoM_y| ≈ 0, 관성곱 |I_xy| ≈ |I_yz| ≈ 0, 주축이 기체축과 나란함
      ⑶ **두 자의 일치** — trimesh ↔ 손계산(발산정리)

    무엇을 **안 판정**하나 — 질량·관성의 **크기**다. 이유를 적어 둔다(감사 I9):
      메쉬 body 는 속이 꽉 찬 솔리드인데 밀도는 ABS 벌크값이라, 메쉬 부피×밀도 질량이
      공표 이륙중량의 **1.1~5.2 배**다. `gazebo_export` 는 총질량을 TOW 로 일괄 정규화하므로
      절대질량은 맞고 **배분만** 치우친다. 그건 이 라운드가 고칠 것이 아니라 **선언할 것**이다.
      ⇒ 아래 `mass_over_tow` 는 원장에 싣되 판정에는 안 쓴다."""
    from drones import build_drone
    from gazebo_export import DENSITY
    m = mesh if mesh is not None else build_drone(spec)
    V = np.asarray(m.v, float)                     # m 단위 그대로(질량이 kg 로 나오게)
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    size_mm = float(np.linalg.norm(V.max(0) - V.min(0))) * 1000.0
    bad = []

    #  면별 밀도 — ⚠ 조용한 폴백 금지. 표에 없는 그룹은 그 자리에서 실패시킨다.
    rho_face = np.zeros(len(F), float)
    unknown = []
    for g in sorted(set(G.tolist())):
        d = DENSITY.get(g)
        if d is None:
            unknown.append(g)
            continue
        rho_face[G == g] = float(d)
    if unknown:
        bad.append(f"밀도표(DENSITY)에 없는 그룹 {unknown} — 조용히 넘기지 않는다")

    raw = mass_properties_raw(V, F, rho_face)

    #  자A(trimesh) — 그룹마다 따로 계산해 합친다(밀도가 그룹마다 다르므로)
    mass_A = 0.0
    M1_A = np.zeros(3)
    I_o_A = np.zeros((3, 3))
    per_group = {}
    for g in sorted(set(G.tolist())):
        if DENSITY.get(g) is None:
            continue
        f = F[G == g]
        used = np.unique(f)
        remap = np.zeros(int(used.max()) + 1, np.int64)
        remap[used] = np.arange(len(used))
        try:
            a = mass_properties_trimesh(V[used], remap[f], float(DENSITY[g]))
        except Exception as e:                      # 못 재면 «못 잼» 이라고 적는다
            per_group[g] = dict(error=f"{type(e).__name__}: {e}")
            bad.append(f"{g} 그룹의 trimesh 질량계산 실패 — {type(e).__name__}")
            continue
        mass_A += a["mass"]
        M1_A += a["mass"] * a["com"]
        #  평행축 정리로 원점 기준으로 되돌려 합산
        d = a["com"]
        I_o_A += a["I_com"] + a["mass"] * ((d @ d) * np.eye(3) - np.outer(d, d))
        rb = mass_properties_raw(V[used], remap[f], np.full(len(f), float(DENSITY[g])))
        per_group[g] = dict(density=float(DENSITY[g]),
                            mass_kg=round(float(a["mass"]), 8),
                            volume_m3=float(f"{a['volume']:.6e}"),
                            com_mm=[round(float(v) * 1000.0, 4) for v in a["com"]],
                            mass_raw_kg=round(float(rb["mass"]), 8))
    com_A = M1_A / mass_A if mass_A else np.zeros(3)
    I_com_A = I_o_A - mass_A * ((com_A @ com_A) * np.eye(3) - np.outer(com_A, com_A))

    #  ⑶ 두 자의 일치
    def _rel(x, y):
        return float(abs(x - y) / max(abs(y), 1e-300))

    agree = dict(mass_rel=_rel(mass_A, raw["mass"]),
                 com_mm=[round(float((com_A - raw["com"])[i] * 1000.0), 9) for i in range(3)],
                 inertia_rel=float(np.abs(I_com_A - raw["I_com"]).max()
                                   / max(np.abs(raw["I_com"]).max(), 1e-300)))
    if agree["mass_rel"] > MASS_RULER_AGREE_REL:
        bad.append(f"두 자의 질량이 다르다 — trimesh {mass_A:.6f} kg ↔ 손계산 "
                   f"{raw['mass']:.6f} kg (상대 {agree['mass_rel']:.2e})")
    if agree["inertia_rel"] > MASS_RULER_AGREE_REL:
        bad.append(f"두 자의 관성이 다르다 — 상대 {agree['inertia_rel']:.2e}")

    #  ⑴ 물리적 타당성
    I = raw["I_com"]
    w, Vc = np.linalg.eigh(0.5 * (I + I.T))
    if raw["mass"] <= 0:
        bad.append(f"총질량이 0 이하다 ({raw['mass']:.6g} kg) — 법선이 안쪽이거나 부피가 음수다")
    neg = [k for k, v in per_group.items() if v.get("mass_kg", 1.0) <= 0.0]
    if neg:
        bad.append(f"질량이 0 이하인 그룹 {neg} — 그 부품의 법선이 안쪽을 본다")
    if (w <= 0).any():
        bad.append(f"관성 고유값에 0 이하가 있다 {[float(f'{v:.4g}') for v in w]}")
    tri_slack = float(w[0] + w[1] - w[2])
    if tri_slack < -1e-12 * max(abs(w[2]), 1e-300):
        bad.append(f"관성 삼각부등식 위반 I₁+I₂ < I₃ (여유 {tri_slack:.4g}) — "
                   f"실재하는 물체에서는 나올 수 없는 값이다")

    #  ⑵ 좌우 불변량
    com_y_rel = abs(float(raw["com"][1]) * 1000.0) / max(size_mm, 1e-300)
    Imax = float(np.abs(np.diag(I)).max())
    ixy = abs(float(I[0, 1])) / max(Imax, 1e-300)
    iyz = abs(float(I[1, 2])) / max(Imax, 1e-300)
    if com_y_rel > COM_Y_BUDGET_REL:
        bad.append(f"질량중심이 좌우로 치우쳤다 — CoM_y {raw['com'][1]*1000:.4f} mm "
                   f"(상대 {com_y_rel:.2e} > {COM_Y_BUDGET_REL:.1e})")
    if ixy > PRODUCT_INERTIA_BUDGET_REL:
        bad.append(f"관성곱 I_xy 가 크다 — 상대 {ixy:.2e}")
    if iyz > PRODUCT_INERTIA_BUDGET_REL:
        bad.append(f"관성곱 I_yz 가 크다 — 상대 {iyz:.2e}")
    #  주축이 기체축(x,y,z)에서 얼마나 벗어났나 — y 축은 좌우대칭이면 반드시 주축이다
    tilt = float(np.degrees(np.arccos(np.clip(np.abs(Vc[1, np.argmax(np.abs(Vc[1, :]))]), 0, 1))))
    if tilt > PRINCIPAL_TILT_BUDGET_DEG:
        bad.append(f"관성 주축이 y 축에서 {tilt:.3f}° 벗어났다 (예산 {PRINCIPAL_TILT_BUDGET_DEG}°)")

    tow_kg = float(spec.weight_g) / 1000.0
    res = dict(
        key=spec.key, checked=True,
        mass_mesh_kg=round(float(raw["mass"]), 6), tow_kg=round(tow_kg, 4),
        #  ⚠ 아래 비는 **판정에 안 쓴다** — 감사 I9 의 선언된 결함이다(머리말 참조)
        mass_over_tow=round(float(raw["mass"] / tow_kg), 4) if tow_kg else None,
        volume_m3=float(f"{raw['volume']:.6e}"),
        com_mm=[round(float(v) * 1000.0, 5) for v in raw["com"]],
        com_y_rel=float(f"{com_y_rel:.3e}"),
        inertia_com_kgm2=[[float(f"{I[i, j]:.6e}") for j in range(3)] for i in range(3)],
        principal_kgm2=[float(f"{v:.6e}") for v in w],
        principal_axis_tilt_deg=round(tilt, 5),
        triangle_inequality_slack=float(f"{tri_slack:.4e}"),
        product_inertia_rel=dict(Ixy=float(f"{ixy:.3e}"), Iyz=float(f"{iyz:.3e}"),
                                 Ixz=float(f"{abs(float(I[0, 2]))/max(Imax,1e-300):.3e}")),
        ruler_agreement=dict(mass_rel=float(f"{agree['mass_rel']:.3e}"),
                             inertia_rel=float(f"{agree['inertia_rel']:.3e}"),
                             com_diff_mm=agree["com_mm"]),
        per_group=per_group, failures=bad, ok=not bad)
    if verbose:
        print(f"  질량·관성: 메쉬질량 {raw['mass']*1000:.0f} g (TOW {spec.weight_g:.0f} g, "
              f"비 {res['mass_over_tow']}) · CoM {res['com_mm']} mm · "
              f"주축기울기 {tilt:.3f}° · 두 자 일치 {agree['mass_rel']:.1e}"
              f"  {'✅' if res['ok'] else '❌'}")
    return res


# =========================================================================== #
#  검사 ⑤ — 투영면적
# =========================================================================== #
def check_projected_area(spec, mesh=None, verbose=False, az_step: float = 30.0,
                         elevations=(0.0, 15.0), npx: int = PROJ_NPX) -> dict:
    """**투영면적** — PO 평판 극한에서 σ ∝ A² 이라 σ 의 1차 결정자다.

    자 둘로 잰다:
      · 자A **실루엣**  = û 방향 윤곽의 넓이. 겹친 면을 **한 번만** 센다(래스터화).
      · 자B **한쪽면 합** = Σ max(n̂·û,0)·A_f. **PO 가 실제로 더하는 양**이다.
    닫힌 껍질에서 자B ≥ 자A 는 **원리적으로 참**이고(광선이 물체를 맞히면 앞면을 하나 이상
    맞힌다), 둘의 비가 곧 «PO 가 몇 배로 이중계상하는가»다. 이 비는 매몰면 검사
    (`mesh_check.check_buried_faces`)와 **다른 통로로** 같은 사실을 잰다.

    판정에 쓰는 것(불변량):
      ⑴ 자B ≥ 자A (원리)
      ⑵ 프레임(비프롭) 실루엣의 **좌우 대칭**: A(방위 φ) = A(−φ)
      ⑶ 한쪽면 합 = 양면 합/2 (닫힌 껍질의 항등식)
    판정에 안 쓰는 것: 면적의 **크기**와 이중계상 배수 — 형상이 바뀌면 같이 변한다(스냅샷)."""
    from drones import build_drone
    m = mesh if mesh is not None else build_drone(spec)
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    Ffr = F[G != "prop"]
    bad = []
    az_list = [float(a) for a in np.arange(0.0, 360.0, az_step)]
    rows = []
    for el in elevations:
        for az in az_list:
            u = view_dir(az, el)
            a_sil = silhouette_area(V, F, u, npx=npx)
            a_one = onesided_area(V, F, u)
            a_two = twosided_area(V, F, u)
            a_sil_fr = silhouette_area(V, Ffr, u, npx=npx)
            a_one_fr = onesided_area(V, Ffr, u)
            rows.append(dict(el_deg=float(el), az_deg=az,
                             sil_m2=float(f"{a_sil:.6e}"), onesided_m2=float(f"{a_one:.6e}"),
                             twosided_half_m2=float(f"{a_two:.6e}"),
                             frame_sil_m2=float(f"{a_sil_fr:.6e}"),
                             frame_onesided_m2=float(f"{a_one_fr:.10e}"),
                             ratio=round(float(a_one / a_sil), 4) if a_sil > 0 else None))
            #  ⑴ 원리 부등식
            if a_one < a_sil * (1.0 - PROJ_ONESIDED_GE_SIL_TOL_REL):
                bad.append(f"el{el:g}/az{az:g}: 한쪽면 합 {a_one:.5f} < 실루엣 {a_sil:.5f} — "
                           f"닫힌 껍질에서는 나올 수 없다(자가 고장났거나 껍질이 열렸다)")
            #  ⑶ 닫힌 껍질 항등식
            if abs(a_one - a_two) > 1e-9 + 1e-6 * a_two:
                bad.append(f"el{el:g}/az{az:g}: 한쪽면 합 ≠ 양면합/2 "
                           f"({a_one:.6f} vs {a_two:.6f}) — 껍질이 안 닫혔거나 법선이 뒤섞였다")

    #  ⑵ 프레임 투영면적의 좌우 대칭 A(φ) = A(−φ) — **자 둘로** 본다
    by = {(r["el_deg"], r["az_deg"]): r for r in rows}
    mir = []
    for (el, az), r in by.items():
        az_m = (-az) % 360.0
        rm = by.get((el, az_m))
        if rm is None:
            continue
        a, b = r["frame_sil_m2"], rm["frame_sil_m2"]
        rel = abs(a - b) / max(abs(b), 1e-300)
        ae, be = r["frame_onesided_m2"], rm["frame_onesided_m2"]
        rel_e = abs(ae - be) / max(abs(be), 1e-300)
        mir.append(dict(el_deg=el, az_deg=az, sil_rel=float(f"{rel:.3e}"),
                        onesided_rel=float(f"{rel_e:.3e}")))
        if rel > PROJ_MIRROR_TOL_REL:
            bad.append(f"el{el:g}: 프레임 실루엣이 좌우로 다르다 — A({az:g}°)={a:.6f} "
                       f"↔ A({az_m:g}°)={b:.6f} (상대 {rel:.2e})")
        if rel_e > PROJ_MIRROR_ONESIDED_TOL_REL:
            bad.append(f"el{el:g}: 프레임 **한쪽면 합**이 좌우로 다르다 — "
                       f"A({az:g}°)={ae:.9f} ↔ A({az_m:g}°)={be:.9f} (상대 {rel_e:.2e}). "
                       f"적분량이라 래스터 잡음이 없다")

    #  ⑵-2 ⭐ **그룹별** 좌우차(한쪽면 합) — 어느 부품이 어긋났는지 집어낸다. 래스터를 안 쓰므로 싸다.
    grp_mirror = {}
    for g in sorted(set(G.tolist())):
        if g == "prop":
            continue
        f = F[G == g]
        worst, worst_at = 0.0, None
        for el in elevations:
            for az in az_list:
                a = onesided_area(V, f, view_dir(az, el))
                b = onesided_area(V, f, view_dir(-az, el))
                r = abs(a - b) / max(abs(b), 1e-300)
                if r > worst:
                    worst, worst_at = r, (float(el), az)
        budget = float(PROJ_ONESIDED_GROUP_BUDGET.get(
            (spec.key, g), PROJ_ONESIDED_GROUP_BUDGET["_default"]))
        okg = bool(worst <= budget)
        grp_mirror[g] = dict(onesided_mirror_max_rel=float(f"{worst:.3e}"),
                             at_el_az=worst_at, budget=budget, ok=okg)
        if not okg:
            bad.append(f"{g} 그룹의 한쪽면 합이 좌우로 {worst:.3e} 다르다 "
                       f"(예산 {budget:.1e}, el/az {worst_at})")

    #  ⑷ 이중계상 배수 — 스냅샷 예산(위 표의 주석 참조)
    ratios = [r["ratio"] for r in rows if r["ratio"]]
    dc_budget = float(PROJ_DOUBLE_COUNT_BUDGET.get(spec.key,
                                                   PROJ_DOUBLE_COUNT_BUDGET["_default"]))
    dc_max = float(np.max(ratios)) if ratios else 0.0
    if dc_max > dc_budget:
        bad.append(f"PO/실루엣 이중계상 배수 {dc_max:.3f} > 예산 {dc_budget} — 같은 면적을 "
                   f"두 번 세고 있을 수 있다(부품 복제·파고듦). ⚠형상을 일부러 바꿨다면 "
                   f"PROJ_DOUBLE_COUNT_BUDGET 을 **다시 선언**하라(값을 올리는 것이 아니라 "
                   f"새 실측을 적는 것이다)")

    res = dict(key=spec.key, checked=True, npx=int(npx), az_step_deg=az_step,
               elevations_deg=[float(e) for e in elevations], per_view=rows,
               mirror_pairs=mir, group_mirror=grp_mirror,
               mirror_max_rel=float(f"{max((d['sil_rel'] for d in mir), default=0.0):.3e}"),
               mirror_onesided_max_rel=float(
                   f"{max((d['onesided_rel'] for d in mir), default=0.0):.3e}"),
               #  ↓ 스냅샷(판정에 안 씀)
               sil_mean_m2=float(f"{np.mean([r['sil_m2'] for r in rows]):.6e}"),
               onesided_over_sil_mean=round(float(np.mean(ratios)), 4) if ratios else None,
               onesided_over_sil_max=round(dc_max, 4) if ratios else None,
               double_count_budget=dc_budget,
               failures=bad, ok=not bad)
    if verbose:
        print(f"  투영면적: 실루엣 평균 {res['sil_mean_m2']:.5f} m² · PO/실루엣 배수 "
              f"평균 {res['onesided_over_sil_mean']} (최대 {res['onesided_over_sil_max']}) · "
              f"좌우차 실루엣 {res['mirror_max_rel']:.1e} / 한쪽면합 "
              f"{res['mirror_onesided_max_rel']:.1e}  {'✅' if res['ok'] else '❌'}")
        top = sorted(grp_mirror.items(), key=lambda kv: -kv[1]["onesided_mirror_max_rel"])[:2]
        print("            그룹별 좌우차 상위: "
              + " · ".join(f"{g} {v['onesided_mirror_max_rel']:.1e}" for g, v in top))
    return res


# =========================================================================== #
#  전수 검사
# =========================================================================== #
def check_one(spec, mesh=None, verbose=False, with_area=True, **kw) -> dict:
    """기체 하나에 대해 이 파일의 검사 다섯을 전부 돌린다."""
    from drones import build_drone
    m = mesh if mesh is not None else build_drone(spec)
    out = dict(key=spec.key)
    out["handedness"] = check_rotor_handedness(spec, mesh=m, verbose=verbose)
    out["dir_convention"] = check_rotor_dir_convention(spec, verbose=verbose)
    out["lateral"] = check_lateral_symmetry(spec, mesh=m, verbose=verbose)
    out["mass_inertia"] = check_mass_inertia(spec, mesh=m, verbose=verbose)
    if with_area:
        out["projected_area"] = check_projected_area(spec, mesh=m, verbose=verbose, **kw)
    out["ok"] = all(v.get("ok", True) for k, v in out.items() if isinstance(v, dict))
    return out


def check_all(verbose=True, with_area=True, keys=None, **kw) -> dict:
    """DRONES 레지스트리 전 기종(또는 keys) 전수 검사.
    ⭐ **자 검정(selftest_rulers)을 맨 먼저** 돌린다 — 자가 틀렸으면 아래 수는 전부 무효다."""
    from drones import DRONES, build_drone
    st = selftest_rulers(npx=kw.get("npx", PROJ_NPX)) if with_area else \
        dict(ok=True, skipped="투영면적을 안 재는 실행이라 래스터 검정은 건너뛴다")
    if verbose:
        print(f"[자 검정] {'✅ 통과' if st['ok'] else '❌ 실패'} — "
              f"정육면체 축 {st.get('cube_axis_err_rel')} · 대각 {st.get('cube_diag_err_rel')} · "
              f"질량자 최대오차 {st.get('mass_ruler_max_err_rel')}")
    out = {"_selftest": st}
    if not st["ok"]:
        out["_ok"] = False
        return out
    for k, s in DRONES.items():
        if keys and k not in keys:
            continue
        try:
            m = build_drone(s)
        except Exception as e:
            #  ⭐ «모르면 모른다» — 못 지은 기체는 빈칸으로 남긴다. 통과로 세지 않는다.
            out[k] = dict(key=k, build_failed=f"{type(e).__name__}: {e}", ok=None)
            if verbose:
                print(f"\n[{k}]  ⚠ 메쉬를 못 지었다 — {type(e).__name__}: {e}")
            continue
        if verbose:
            print(f"\n[{k}]")
        r = check_one(s, mesh=m, verbose=verbose, with_area=with_area, **kw)
        out[k] = r
        if verbose:
            print(f"  ⇒ {'✅ 통과' if r['ok'] else '❌ 결함'}")
    graded = [v for k, v in out.items() if not k.startswith("_") and v.get("ok") is not None]
    out["_ok"] = bool(st["ok"] and all(v["ok"] for v in graded))
    return out


def assert_ok(keys=None, with_area=True, **kw):
    """게이트용 — 결함이 있으면 예외를 던진다(회귀 방지).
    ⚠ 메쉬를 **못 지은** 기체는 «통과» 로 세지 않고 여기서 같이 실패시킨다."""
    res = check_all(verbose=False, with_area=with_area, keys=keys, **kw)
    if not res["_selftest"]["ok"]:
        raise AssertionError(f"자 검정 실패 — {res['_selftest']}")
    bad = {}
    for k, r in res.items():
        if k.startswith("_"):
            continue
        if r.get("build_failed"):
            bad[k] = [f"메쉬 빌드 실패: {r['build_failed']}"]
            continue
        if r["ok"]:
            continue
        why = []
        for axis in ("handedness", "dir_convention", "lateral", "mass_inertia",
                     "projected_area"):
            why += list(r.get(axis, {}).get("failures", []))
        bad[k] = why
    if bad:
        raise AssertionError(f"대칭·파생량 검증 실패 — {bad}\n"
                             f"  python src/mesh_symmetry.py 로 상세 확인")
    return True


if __name__ == "__main__":
    keys = [a for a in sys.argv[1:] if not a.startswith("-")] or None
    fast = "--no-area" in sys.argv[1:]
    print("=" * 104)
    print("대칭 · 손잡이 · 파생량 검사 — 검사마다 자 둘 · 자 자체는 닫힌 해로 검정")
    print("=" * 104)
    res = check_all(verbose=True, with_area=not fast, keys=keys)
    graded = [v for k, v in res.items() if not k.startswith("_") and v.get("ok") is not None]
    blank = [k for k, v in res.items() if not k.startswith("_") and v.get("ok") is None]
    n_ok = sum(1 for v in graded if v["ok"])
    print(f"\n{'='*104}\n결과: {n_ok}/{len(graded)} 통과"
          + (f"  ⚠ 빈칸(메쉬를 못 지음) {blank}" if blank else ""))
    sys.exit(0 if res["_ok"] and not blank else 1)
