# -*- coding: utf-8 -*-
"""
material_provenance.py — **재질 배정·재질 상수·출처 등급을 검사하는 층** (2026-08-16 신설)
===============================================================================================

■ 이 파일이 답하는 세 질문
    ① **부품마다 재질이 옳나** — 메쉬의 그룹 라벨이 표에 있고, 그 라벨이 붙은 자리가
       실제로 그 부품 자리인가(카메라와 착륙장치가 서로 바뀌지 않았나).
    ② **재질 상수가 문헌과 맞나** — εr·σ·|Γ| 하나하나가 «문헌 출처» 아니면 «모델링 선언»
       둘 중 하나를 갖고 있고, 문헌을 주장한 값은 그 문헌 구간 **안**에 있는가.
    ③ ⭐**출처 등급이 진짜 근거를 가리키나** — 기체 × 부품 칸마다 붙은 [A]~[D] 가
       **실재하는 파일**을 가리키고, 그 파일의 종류가 그 등급을 **버티는가**.
       («대리»인데 [B] 로 적힌 것, 죽은 링크, 없는 인용문 = **등급 인플레**)

■ 왜 새로 만드나 — 지금 없는 것
    메쉬 인증 범주 지도(`outputs/mesh_cert_map_0816.json`)가 이 두 칸을 이렇게 적었다:
      · **M12 그룹 라벨·재질 배정 — 상태 «없음»**. 심은 결함 중 «그룹 이름 바꾸기»와
        «camera↔gear 라벨 뒤바꾸기»가 **전 검사 통과**했다.
      · **M15 출처·등급 — 상태 «부분»**. 프로펠러 축만 기계가 읽는 등급표가 있고,
        **기체 × 부품 행렬은 없다**. 나머지 근거는 코드 주석·일회성 JSON·리포트 산문
        **세 곳에 흩어져** 있다(R20 사고의 원인이 바로 그 분산이었다).

■ 용어 한 줄 풀이
    · **|Γ|(감마)**   : 진폭 반사계수. 1 이면 전부 반사(금속), 0 이면 전부 통과. σ 는 |Γ|² 에 비례.
    · **벌크 프레넬** : 두께가 무한한 판의 반사. 얇은 판(셸·프롭 날)은 앞뒷면 간섭으로 다르다.
    · **표피깊이**    : 도체 안으로 전파가 1/e 로 줄어드는 깊이. 벽 두께 ≫ 표피깊이면 «불투명».
    · **조용한 폴백** : 모르는 이름이 들어와도 예외 없이 기본값으로 흐르는 것.
    · **양성 대조**   : 일부러 결함을 만들어 먹여 «걸리는가»를 보는 시험.
    · **음성 대조**   : 손대지 않은 것이 «통과하는가»를 보는 시험(거짓경보가 아님을 보인다).

■ 등급 눈금 (근거의 «종류»가 등급의 **상한**을 정한다 — 이것이 인플레를 막는 장치다)
    [A]  그 기체 **자신의 제조사 1차 자료**가 그 부품의 재질을 **직접** 말한다
         (예: Holybro 공식 STEP 안의 부품명 `CARBON-FIBER-TUBE`)
    [A-] 제조사 공식 **문서/지원페이지**의 재질 문장(파일로 인용문이 저장소에 있어야 한다)
    [B]  그 기체 **자신의 분해·부품 사진**에서 재질이 보인다
    [B-] 그 기체 **자신의 완성기 사진·공식 렌더**뿐(겉모습만)
    [C]  **계열 유추**(같은 제조사·같은 급) 또는 재질 클래스 문헌
    [D]  ⛔**대리** — 다른 기체·다른 제품의 자료를 빌려 씀
    **빈칸(None)** — 모르면 모른다. 다만 `unknown_reason` 을 반드시 적어야 통과한다.
    ⭐ 이 등급은 **재질 축**이다. 같은 칸의 «치수 축» 등급과 다를 수 있다
      (예: mini2 프롭은 치수 [A](공식 GLB) 인데 재질은 [C] — GLB 는 형상만 담는다).

■ 규약
    · ⛔**GPU 미사용** — sionna·mitsuba·torch 를 **임포트하지 않는다**. ITU 재질값은 설치본
      소스(`sionna/rt/radio_materials/itu.py`)의 표를 **정적으로 읽어** 같은 식으로 계산하고,
      그 결과가 예전 라운드의 Sionna 실측 원장(`outputs/material_sources.json`)과
      맞는지 **교차검증**한다(`check_constants` 의 `itu_crosscheck`).
    · ⛔**형상·재질 상수 무변경** — 이 파일은 읽기만 한다. 값을 고치지 않는다.
    · 검사마다 양성·음성 대조가 `benchmark/adv_material_provenance_faults.py` 에 있다.
      **대조가 없는 검사는 «있다» 고 치지 않는다.**

실행:  PYTHONPATH=src python src/material_provenance.py         # 사람이 읽는 요약
        PYTHONPATH=src python src/material_provenance.py --gate  # 게이트(실패면 종료코드 1)
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)

EPS0 = 8.8541878128e-12
MU0 = 4e-7 * np.pi

#  우리가 실제로 쓰는 세 대역 — 리포트·원장이 쓰는 이름 그대로.
BANDS = {"LTE 1.843 GHz": 1.843e9, "5G 3.5 GHz": 3.5e9, "WiFi 5.21 GHz": 5.21e9}

#  예전 라운드가 **살아 있는 Sionna 로** 만든 원장. 우리 정적 계산의 채점표로 쓴다.
MATERIAL_SOURCES_JSON = os.path.join(ROOT, "outputs", "material_sources.json")
#  설치본 Sionna 의 ITU 표(정적으로 읽는다 — 임포트하지 않는다).
SIONNA_ITU_PY = os.path.join(
    os.path.dirname(os.path.dirname(np.__file__)),      # site-packages
    "sionna", "rt", "radio_materials", "itu.py")


# =========================================================================== #
#  0. 작은 도구 — 물리
# =========================================================================== #
def db(x: float) -> float:
    """진폭비 → dB. |Γ| 는 진폭이므로 20·log10."""
    return 20.0 * float(np.log10(max(float(x), 1e-30)))


def gamma_bulk_from(eps_r: float, sigma: float, fc: float) -> float:
    """**벌크(반무한) 수직입사 프레넬 |Γ|** — (εr, σ) 에서 직접.
        Γ = (1 − √εc) / (1 + √εc),   εc = εr − j·σ/(ω·ε0)"""
    ec = float(eps_r) - 1j * float(sigma) / (2 * np.pi * float(fc) * EPS0)
    return float(abs((1.0 - np.sqrt(ec)) / (1.0 + np.sqrt(ec))))


def skin_depth_m(sigma: float, fc: float, mu_r: float = 1.0) -> float:
    """표피깊이 δ = √(2/(ω·μ·σ)) [m]. 좋은 도체 근사(σ ≫ ωε)."""
    w = 2 * np.pi * float(fc)
    return float(np.sqrt(2.0 / (w * MU0 * float(mu_r) * float(sigma))))


def thin_slab_gamma(eps_r: float, sigma: float, fc: float, d_m: float) -> float:
    """**얇은 판(슬래브) 수직입사 |Γ|** — 앞뒷면 반사의 간섭까지 담는다.
        Γ = r(1 − e^{−2jδ}) / (1 − r²e^{−2jδ}),  δ = k0·d·√εc
    (셸·프롭 날처럼 두께가 파장에 견줄 만큼 얇을 때 벌크식은 틀린다.)"""
    ec = float(eps_r) - 1j * float(sigma) / (2 * np.pi * float(fc) * EPS0)
    n = np.sqrt(ec)
    r = (1.0 - n) / (1.0 + n)
    k0 = 2 * np.pi * float(fc) / 2.99792458e8
    dl = k0 * float(d_m) * n
    e = np.exp(-2j * dl)
    return float(abs(r * (1.0 - e) / (1.0 - r ** 2 * e)))


# =========================================================================== #
#  1. ITU 표 — 설치본 소스를 **정적으로** 읽는다 (임포트 없음 = GPU 없음)
# =========================================================================== #
_ITU_CACHE: dict | None = None


def itu_table(path: str | None = None) -> dict:
    """설치본 `sionna/rt/radio_materials/itu.py` 의 `ITU_MATERIALS_PROPERTIES` 를 읽는다.
    형식: {재질명: {(f_min_GHz, f_max_GHz): (a, b, c, d)}}  —  εr = a·f^b, σ = c·f^d.
    ⚠ 임포트가 아니라 **텍스트 파싱**이다. sionna 를 불러오면 GPU 백엔드가 깨어난다."""
    global _ITU_CACHE
    if path is None and _ITU_CACHE is not None:
        return _ITU_CACHE
    p = path or SIONNA_ITU_PY
    with open(p, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"ITU_MATERIALS_PROPERTIES\s*=\s*(\{)", src)
    if not m:
        raise RuntimeError(f"ITU 표를 못 찾았다: {p}")
    i = m.start(1)
    depth, j = 0, i
    while j < len(src):                      # 중괄호 균형으로 딕셔너리 끝을 찾는다
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    tbl = ast.literal_eval(src[i:j + 1])     # 순수 리터럴이라 안전하게 평가된다
    if path is None:
        _ITU_CACHE = tbl
    return tbl


def itu_params(name: str, fc: float) -> tuple[float, float]:
    """ITU 재질 → (εr, σ[S/m]) — Sionna 와 **같은 식**(P.2040 §2.1.4).
    유효 주파수 구간 밖이면 예외(Sionna 도 예외를 던진다)."""
    tbl = itu_table()
    if name not in tbl:
        raise KeyError(f"ITU 표에 없는 재질: {name!r} (있는 것 = {sorted(tbl)})")
    f_ghz = float(fc) / 1e9
    for (lo, hi), (a, b, c, d) in tbl[name].items():
        if lo <= f_ghz <= hi:
            return float(a * f_ghz ** b), float(c * f_ghz ** d)
    raise ValueError(f"ITU 재질 {name!r} 는 {f_ghz:.3f} GHz 에서 정의되지 않는다 "
                     f"(유효구간 {sorted(tbl[name])})")


def material_params_static(mat_key: str, fc: float, materials_table: dict) -> tuple[float, float, float]:
    """재질 키 → (εr, σ, S). ITU 재질은 위 표에서, 커스텀은 MATERIALS 값 그대로.
    ⚠ `materials.material_params()` 와 **같은 값**이어야 한다 — 교차검증은
      `check_constants()` 의 `itu_crosscheck` 가 예전 Sionna 실측 원장으로 한다."""
    spec = materials_table[mat_key]
    if "itu" in spec:
        er, sg = itu_params(spec["itu"], fc)
    else:
        er, sg = float(spec["eps_r"]), float(spec["sigma"])
    return er, sg, float(spec.get("S", 0.0))


# =========================================================================== #
#  2. 등급 눈금과 근거 종류
# =========================================================================== #
GRADE_RANK = {"A": 6, "A-": 5, "B": 4, "B-": 3, "C": 2, "D": 1}

#  근거 «종류» → 그 근거만으로 받을 수 있는 **최고 등급**. 이것이 인플레 방지 장치다.
EVIDENCE_KIND_CAP = {
    "official_cad":    "A",    # 그 기체의 제조사 CAD/STEP 파일 자체(부품명·BOM 포함)
    "official_doc":    "A-",   # 제조사 공식 문서·지원페이지의 재질 문장(인용문이 저장소 파일에 있어야)
    "own_teardown":    "B",    # 그 기체 자신의 **분해** 사진(속이 열린 것)
    "own_component":   "B",    # 그 기체 자신의 **부품 단품·구조 근접** 사진(분해 없이도 부품이 드러난 것)
    "own_photo":       "B-",   # 그 기체 자신의 완성기 사진·공식 렌더(겉모습만)
    "sibling_variant": "C",    # 같은 계열 **다른 판**의 자료(예: Phantom 4 Pro+ V2.0 사진)
    "repo_prose":      "C",    # 우리 저장소의 서술(2차 — 우리가 쓴 문장은 근거가 아니라 정리다)
    "literature":      "C",    # 재질 클래스 문헌(그 기체 이야기가 아니다)
    "other_airframe":  "D",    # ⛔대리 — 다른 기체·다른 제품의 자료
}

#  모델 재질 키 → 물리 «클래스». 실물 클래스와 다르면 **대체 선언**을 요구한다.
MODEL_KEY_CLASS = {
    "plastic": "abs_pc", "plastic_blue": "abs_pc", "prop_plastic": "abs_pc",
    "carbon": "carbon", "metal": "metal", "pcb": "fr4_copper",
    "camera_assembly": "glass_metal", "absorber": "absorber",
    "concrete_light": "concrete", "concrete_dark": "concrete",
}


# =========================================================================== #
#  3. 근거 파일 등록부 — **여기에 적힌 파일이 실재해야 하고, 인용문은 실제로 그 파일 안에 있어야 한다**
# =========================================================================== #
#   kind   : 위 EVIDENCE_KIND_CAP 의 종류
#   path   : 저장소 상대경로 (없으면 죽은 링크 → FAIL)
#   owner  : 그 자료가 «누구의 것인가»(기체 키). own_* 종류는 칸의 기체와 같아야 한다.
#   quote  : (선택) 그 파일 안에 **글자 그대로** 있어야 하는 문장. 없으면 죽은 인용 → FAIL.
#   variant: (선택) 그 자료가 어느 «판»인가. 판이 다르면 쓰면 안 되는 칸이 있다(아래 규칙).
def _ph(key: str, fn: str) -> str:
    return f"assets/photos/{key}/{fn}"


EVIDENCE: dict[str, dict] = {
    # ---- 제조사 1차 자료 (파일 자체가 저장소에 있다) --------------------------------
    "x500v2.step_carbon_tube": dict(
        kind="official_cad", owner="x500v2",
        path="assets/meshes/reference/x500v2-frame.step",
        quote="CARBON-FIBER-TUBE",
        what_ko="Holybro 공식 X500 V2 프레임 STEP. 부품명이 재질을 **직접** 말한다"),
    "x500v2.step_nylon": dict(
        kind="official_cad", owner="x500v2",
        path="assets/meshes/reference/x500v2-frame.step",
        quote="NILONGZHU",
        what_ko="같은 STEP. `NILONGZHU`(나일론 기둥)·`LM-M3-NILONG`(나일론 너트) — "
                "프레임에 나일론 부재가 있다는 제조사 표기"),
    "x500v2.step_eva": dict(
        kind="official_cad", owner="x500v2",
        path="assets/meshes/reference/x500v2-frame.step",
        quote="JIAO-EVA",
        what_ko="같은 STEP. 스키드 발포 슬리브가 EVA 라는 부품명"),
    "x500v2.motor_step": dict(
        kind="official_cad", owner="x500v2",
        path="assets/meshes/reference/AIR2216II_Motor_3D.STEP",
        what_ko="Holybro AIR2216II 모터 단품 STEP. ⚠**형상만** 담는다 — 재질 표기는 없다"),

    # ---- 제조사 공식 문서의 재질 문장 (저장소 파일에 인용문이 보존돼 있다) --------------
    "dji.prop_material_1158F": dict(
        kind="official_doc", owner="mavic4pro",
        path="docs/drone_material_deepverify.json",
        quote="Enhanced Nylon Composite Material",
        what_ko="DJI 공식 지원문서 «Aircraft Propeller Materials» — Mavic 4 Pro 프롭 1158F 는 "
                "«강화 나일론 복합». **ABS/PC 가 아니다**"),
    "dji.prop_material_mini5pro": dict(
        kind="official_doc", owner="mini5pro",
        path="docs/drone_material_deepverify.json",
        quote="Nylon + Rubber",
        what_ko="같은 DJI 공식 프롭 재질표 — Mini 4 Pro·**Mini 5 Pro** 는 «나일론 + 고무(팁)»"),
    "dji.prop_material_composite_m4": dict(
        kind="official_doc", owner="matrice4e",
        path="docs/drone_material_deepverify.json",
        quote="Composite material",
        what_ko="같은 표 — Matrice 4 계열 프롭은 «복합재»(유리섬유 나일론), **카본 아님**"),
    "dji.s1000_arms_cf": dict(
        kind="official_doc", owner="s1000plus",
        path="docs/drone_material_deepverify.json",
        quote="the retractable landing gear are made from carbon fiber",
        what_ko="⭐DJI 공식 S1000 기능페이지 인용 — «모든 프레임 암»과 «접이식 착륙장치»가 "
                "카본이라고 **제조사가 직접** 적는다"),
    "dji.s1000_prop_plastic": dict(
        kind="official_doc", owner="s1000plus",
        path="docs/drone_material_deepverify.json",
        quote="High strength performance engineered plastics",
        what_ko="⭐DJI 공식 S1000 제원 — 순정 1552 프롭은 «고강도 엔지니어링 플라스틱»이다. "
                "**카본이 아니다**(그 구별이 |Γ| 0.90 ↔ 0.25 를 가른다)"),
    "dji.p4_magnesium_core": dict(
        kind="sibling_variant", owner="phantom4", variant="P4Pro V2.0",
        path="docs/drone_material_deepverify.json",
        quote="boards screw into a magnesium core",
        what_ko="⚠**Phantom 4 Pro V2.0** 분해 기록 — 마그네슘 코어에 보드가 조립된다. "
                "우리 키 `phantom4`(초판)와 판이 다르므로 계열 근거로만 쓴다. "
                "⛔그 항목의 모델코드 표기(WM331)는 **우리 phantom3 기록과 충돌한다**"),
    "dji.az91_practice": dict(
        kind="official_doc", owner="mavic4pro",
        path="docs/drone_material_deepverify.json",
        quote="AZ91",
        what_ko="DJI 가 Inspire 2·Mavic Air 에 AZ91 마그네슘 브래킷을 쓴다는 문서화된 관행. "
                "⚠ 그 기체(M4Pro/M4E) **자신**에 대한 1차 확인은 아니다 — 문서 자신이 그렇게 적는다"),

    # ---- 참조 자산 SOURCES (우리가 정리한 출처 문서) ------------------------------
    "ref.sources_md": dict(
        kind="repo_prose", owner="-",
        path="assets/meshes/reference/SOURCES.md",
        quote="1045 Propellers (6 pcs)",
        what_ko="참조자산 출처 문서 — X500 V2 킷 프롭이 1045 라는 Holybro 문서 인용"),
    "x500v2.sources_md": dict(
        kind="repo_prose", owner="x500v2",
        path="assets/photos/x500v2/SOURCES.md",
        quote="CARBON-FIBER-TUBE",
        what_ko="X500 V2 사진 출처 문서 — STEP BOM 판독 기록"),

    # ---- 그 기체 자신의 분해 사진 -------------------------------------------------
    "mini2.shell": dict(kind="own_teardown", owner="mini2",
                        path=_ph("mini2", "mini2_t20_fcc_mt2wd_topcover_off_ruler.jpg"),
                        what_ko="상부 커버를 연 FCC 내부사진 — 셸이 사출 플라스틱"),
    "mini2.heatsink": dict(kind="own_teardown", owner="mini2",
                           path=_ph("mini2", "mini2_t04_ifixit_heatsink_finned_closeup.jpg"),
                           what_ko="벨리를 채우는 **금속 방열판/실드** 근접 — 공용 «구조판»의 실물 대응물"),
    "mini2.mainboard": dict(kind="own_teardown", owner="mini2",
                            path=_ph("mini2", "mini2_t09_ifixit_mainboard_lifted.jpg"),
                            what_ko="메인보드 — FR-4 + 실드캔"),
    "mini2.shield_foil": dict(kind="own_teardown", owner="mini2",
                              path=_ph("mini2", "mini2_t18_ifixit_shielding_foil.jpg"),
                              what_ko="차폐 포일"),
    "mini2.battery": dict(kind="own_teardown", owner="mini2",
                          path=_ph("mini2", "mini2_c03_fcc_mt2wd_battery.jpg"),
                          what_ko="배터리 단품(파우치 팩 + 플라스틱 케이스)"),
    "mini2.motor_prop": dict(kind="own_teardown", owner="mini2",
                             path=_ph("mini2", "mini2_t28_fcc_mt2wd_propeller_motor_view.jpg"),
                             what_ko="프롭 허브의 **강철 십자나사 2개** + 모터"),
    "mini2.legs": dict(kind="own_photo", owner="mini2",
                       path=_ph("mini2", "mini2_d12_official_unfolded_front_elevation_flight.jpg"),
                       what_ko="공식 정면 도판 — 앞 암 아래 착륙 포스트 두 개가 보인다"),
    "mini2.gimbal": dict(kind="own_teardown", owner="mini2",
                         path=_ph("mini2", "mini2_t13_ifixit_gimbal_camera_block.jpg"),
                         what_ko="짐벌 카메라 블록"),
    "mini2.prop": dict(kind="own_teardown", owner="mini2",
                       path=_ph("mini2", "mini2_c07_fcc_mt2wd_propeller_2blade_ruler.jpg"),
                       what_ko="프롭 단품(자 포함) — **형상**은 보이나 재질 표기는 없다"),

    "phantom3.shell": dict(kind="own_teardown", owner="phantom3",
                           path=_ph("phantom3", "phantom3_t04_fccpro_upper_shell_inner_frame.jpg"),
                           what_ko="상부 셸 + 내부 프레임 — 흰색 사출 플라스틱"),
    "phantom3.motor": dict(kind="own_teardown", owner="phantom3",
                           path=_ph("phantom3", "phantom3_t18_fccse_brushless_motor_mm.jpg"),
                           what_ko="브러시리스 모터 단품(자 포함)"),
    "phantom3.pcb": dict(kind="own_teardown", owner="phantom3",
                         path=_ph("phantom3", "phantom3_t10_fccpro_main_pcb_top.jpg"),
                         what_ko="메인 PCB 상면"),
    "phantom3.battery": dict(kind="own_teardown", owner="phantom3",
                             path=_ph("phantom3", "phantom3_t15_fccpro_battery_side.jpg"),
                             what_ko="인텔리전트 배터리 측면"),
    "phantom3.gimbal": dict(kind="own_teardown", owner="phantom3",
                            path=_ph("phantom3", "phantom3_t27_fccpro_camera_module_housing.jpg"),
                            what_ko="카메라 모듈 하우징"),
    "phantom3.gear": dict(kind="own_teardown", owner="phantom3",
                          path=_ph("phantom3", "phantom3_c06_ifixit_std_landing_gear_pair.jpg"),
                          what_ko="착륙다리 한 쌍(분리품)"),
    "phantom3.shield_box": dict(kind="own_teardown", owner="phantom3",
                                path=_ph("phantom3", "phantom3_t29_ifixit_internal_top_shell_off.jpg"),
                                what_ko="셸 연 내부 — 중앙보드 위 **금속 실드 상자**"),

    "mavic4pro.chassis": dict(kind="own_teardown", owner="mavic4pro",
                              path=_ph("mavic4pro", "mavic4pro_t04_chassis_stripped_board_fan_ruler.jpg"),
                              what_ko="섀시만 남긴 분해(자 포함)"),
    "mavic4pro.arm_motor": dict(kind="own_teardown", owner="mavic4pro",
                                path=_ph("mavic4pro", "mavic4pro_c04_arm_front_left_motor_end.jpg"),
                                what_ko="암 끝단 + 모터"),
    "mavic4pro.board": dict(kind="own_teardown", owner="mavic4pro",
                            path=_ph("mavic4pro", "mavic4pro_t05_shield_frame_and_board_ruler.jpg"),
                            what_ko="실드 프레임 + 보드"),
    "mavic4pro.battery": dict(kind="own_teardown", owner="mavic4pro",
                              path=_ph("mavic4pro", "mavic4pro_t16_flight_battery_standalone_ruler.jpg"),
                              what_ko="배터리 단품(자 포함)"),
    "mavic4pro.gimbal": dict(kind="own_teardown", owner="mavic4pro",
                             path=_ph("mavic4pro", "mavic4pro_c13_gimbal_bracket_caps.jpg"),
                             what_ko="짐벌 브래킷·캡"),
    "mavic4pro.prop": dict(kind="own_teardown", owner="mavic4pro",
                           path=_ph("mavic4pro", "mavic4pro_c10_propeller_pair_1158F.jpg"),
                           what_ko="1158F 프롭 한 쌍"),
    "mavic4pro.legs": dict(kind="own_teardown", owner="mavic4pro",
                           path=_ph("mavic4pro", "mavic4pro_c06_arm_rear_left_no_leg.jpg"),
                           what_ko="뒤 암(다리 없음) — 앞 암에만 다리가 있다는 대조"),

    "matrice4e.shell": dict(kind="own_teardown", owner="matrice4e",
                            path=_ph("matrice4e", "matrice4e_t14_lower_shell_bare_structure.jpg"),
                            what_ko="하부 셸 골격"),
    "matrice4e.motor_arm": dict(kind="own_teardown", owner="matrice4e",
                                path=_ph("matrice4e", "matrice4e_t11_motor_and_arm_closeup.jpg"),
                                what_ko="모터 + 암 근접 — 회색 사출 암, 검은 금속 모터 벨"),
    "matrice4e.board": dict(kind="own_teardown", owner="matrice4e",
                            path=_ph("matrice4e", "matrice4e_t05_mainboard_in_shield_frame.jpg"),
                            what_ko="실드 프레임 안의 메인보드"),
    "matrice4e.battery": dict(kind="own_teardown", owner="matrice4e",
                              path=_ph("matrice4e", "matrice4e_c03_intelligent_flight_battery.jpg"),
                              what_ko="인텔리전트 배터리 단품"),
    "matrice4e.gimbal_4e": dict(kind="own_photo", owner="matrice4e", variant="M4E",
                                path=_ph("matrice4e", "matrice4e_m02_gimbal_4E_lens_layout.png"),
                                what_ko="⭐**4E 판** 짐벌 렌즈 배치 도판 — 4T 판과 섞으면 안 되는 자리"),
    "matrice4e.gimbal_4t": dict(kind="own_teardown", owner="matrice4e", variant="M4T",
                                path=_ph("matrice4e", "matrice4e_t15_gimbal_lens_cluster_M4T.jpg"),
                                what_ko="⛔**4T 판** 짐벌 분해 — 짐벌 칸에는 쓰면 안 된다(판이 다르다)"),
    "matrice4e.beacon": dict(kind="own_photo", owner="matrice4e",
                             path=_ph("matrice4e", "matrice4e_m17_beacon_topside.png"),
                             what_ko="상면 비콘·식별부 도판 — 'accent' 그룹의 실물 자리"),
    "matrice4e.prop": dict(kind="own_photo", owner="matrice4e",
                           path=_ph("matrice4e", "matrice4e_c02_prop_standard_1157F_pair.jpg"),
                           what_ko="순정 1157F 프롭 한 쌍(제품 렌더)"),
    "matrice4e.gear": dict(kind="own_photo", owner="matrice4e",
                           path=_ph("matrice4e", "matrice4e_m15_arm_led_landing_gear.png"),
                           what_ko="암 LED·착륙장치 도판"),

    "m350rtk.arm_weave": dict(kind="own_photo", owner="m350rtk",
                              path=_ph("m350rtk", "m350rtk_p07_folded_side_ruler.png"),
                              what_ko="접힌 측면(자 포함) — 암 튜브의 **직조 무늬**가 보인다"),
    "m350rtk.arm_tip": dict(kind="own_component", owner="m350rtk",
                            path=_ph("m350rtk", "m350rtk_d07_arm_tip_motor_prop_hub.jpg"),
                            what_ko="암 끝단·모터·프롭 허브 근접 — 튜브 표면이 가까이 보인다"),
    "m350rtk.shell": dict(kind="own_teardown", owner="m350rtk",
                          path=_ph("m350rtk", "m350rtk_t01_airframe_shell_removed_iso_ruler.png"),
                          what_ko="셸 제거 기체 골격(자 포함)"),
    "m350rtk.board": dict(kind="own_teardown", owner="m350rtk",
                          path=_ph("m350rtk", "m350rtk_t10_copper_shield_board_ruler.png"),
                          what_ko="**구리 실드** 보드(자 포함)"),
    "m350rtk.battery": dict(kind="own_component", owner="m350rtk",
                            path=_ph("m350rtk", "m350rtk_c02_tb65_battery.png"),
                            what_ko="TB65 배터리 단품 — **기체 밖에 노출**되는 케이스"),
    "m350rtk.motor": dict(kind="own_photo", owner="m350rtk",
                          path=_ph("m350rtk", "m350rtk_m05_maint_propulsion_motor_arm.png"),
                          what_ko="정비 매뉴얼의 추진계(모터·암) 도판"),
    "m350rtk.sensors": dict(kind="own_photo", owner="m350rtk",
                            path=_ph("m350rtk", "m350rtk_p08_nose_sensor_array_closeup.png"),
                            what_ko="기수 센서 어레이 근접 — 이 기체의 'camera' 그룹 실물"),
    "m350rtk.gear": dict(kind="own_photo", owner="m350rtk",
                         path=_ph("m350rtk", "m350rtk_m04_maint_aircraft_structure_arms_gear.png"),
                         what_ko="정비 매뉴얼의 구조(암·착륙장치) 도판"),
    "m350rtk.prop": dict(kind="own_photo", owner="m350rtk",
                         path=_ph("m350rtk", "m350rtk_c01_prop_2110s_pair.png"),
                         what_ko="2110s 프롭 한 쌍(제품 렌더)"),

    "x500v2.frame_photo": dict(kind="own_component", owner="x500v2",
                               path=_ph("x500v2", "x500v2_02_frame_front34.jpg"),
                               what_ko="프레임 정면 3/4 — **카본 능직 무늬**와 파란 나일론 클램프가 함께 보인다"),
    "x500v2.arm_tip": dict(kind="own_component", owner="x500v2",
                           path=_ph("x500v2", "x500v2_05_arm_tip_motor_mount.jpg"),
                           what_ko="암 끝단·모터 마운트"),
    "x500v2.fc_stack": dict(kind="own_component", owner="x500v2",
                            path=_ph("x500v2", "x500v2_12_fc_stack_pixhawk6c.png"),
                            what_ko="비행제어기 스택(Pixhawk 6C)"),
    "x500v2.prop": dict(kind="own_photo", owner="x500v2",
                        path=_ph("x500v2", "x500v2_10_prop_1045_on_2216.jpg"),
                        what_ko="2216 모터에 물린 1045 프롭"),

    "typhoonh480.official": dict(kind="own_photo", owner="typhoonh480",
                                 path=_ph("typhoonh480", "typhoonh480_y03_official_hero.png"),
                                 what_ko="Yuneec 공식 제품 사진 — **겉모습만**. 분해 자료 없음"),
    "typhoonh480.gear": dict(kind="own_photo", owner="typhoonh480",
                             path=_ph("typhoonh480", "typhoonh480_y01_official_gear_down.png"),
                             what_ko="공식 사진(다리 내림)"),
    "typhoonh480.cgo3": dict(kind="own_photo", owner="typhoonh480",
                             path=_ph("typhoonh480", "typhoonh480_y06_official_cgo3plus.png"),
                             what_ko="CGO3+ 짐벌 카메라 공식 사진"),

    "mini5pro.render": dict(kind="own_photo", owner="mini5pro",
                            path=_ph("mini5pro", "mini 5 pro_1.png"),
                            what_ko="공식 제품 렌더 3장 중 정면 — 회색 사출 셸·검은 프롭·짐벌이 보인다. "
                                    "⚠ 분해 자료는 **없다**"),

    "s1000plus.top": dict(kind="own_photo", owner="s1000plus",
                          path=_ph("s1000plus", "s1000+_1.png"),
                          what_ko="판매점 상면 사진 — 카본 튜브 암 8개·카본 센터플레이트·접이 프롭. "
                                  "⚠ 제조사 자료도 분해 자료도 **아니다**"),

    "phantom4.sibling": dict(kind="sibling_variant", owner="phantom4", variant="P4Pro+V2.0",
                             path=_ph("phantom4", "Phantom 4 pro + V2_1.png"),
                             what_ko="⚠ 폴더의 사진 5장은 **Phantom 4 Pro+ V2.0** 이다 — "
                                     "우리 키 `phantom4`(초판)와 다른 판"),

    # ---- 우리 저장소의 서술(2차) --------------------------------------------------
    "prose.typhoon_arm_unknown": dict(
        kind="repo_prose", owner="typhoonh480", path="src/drones.py",
        quote="Yuneec never stated the arm",
        what_ko="⭐암 재질 **모른다**는 선언 + 카본↔플라스틱 10.14 dB 감도 표기"),
    "prose.p3_no_magnesium": dict(
        kind="repo_prose", owner="phantom3", path="src/drones.py",
        quote="THE PHANTOM 3 HAS NO MAGNESIUM SKELETON",
        what_ko="Phantom 3 에 마그네슘 골격이 없다는 선언(마그네슘은 **Phantom 4** 의 개선점)"),
    "prose.p3_prop_fork": dict(
        kind="repo_prose", owner="phantom3", path="src/drones.py",
        quote="E305 9450 Carbon Fiber",
        what_ko="⚠Phantom 3 에는 **카본 강화 프롭 선택품**이 있었다 — 어느 쪽인지 통제 안 됨"),
    "prose.mini2_arms_plastic": dict(
        kind="repo_prose", owner="mini2", path="src/drones.py",
        quote="same family as the shell",
        what_ko="암이 셸과 같은 사출 플라스틱(iFixit 분해 + 공식 CAD 로 확인했다는 기록)"),
    "prose.mini2_heatsink": dict(
        kind="repo_prose", owner="mini2", path="src/drones.py",
        quote="heatsink/shield over the SoC filling much of the belly",
        what_ko="Mini 2 에는 마그네슘 섀시가 없지만 **큰 금속 방열판**이 있어 공용 판의 대응물이 된다"),
    "prose.m350_arm_carbon": dict(
        kind="repo_prose", owner="m350rtk", path="src/drones.py",
        quote="arm_style 'carbon' VERIFIED from the weave visible on p06",
        what_ko="암 카본 판정의 근거가 **직조 무늬**라는 기록"),
    "prose.s1000_carbon_frame": dict(
        kind="repo_prose", owner="s1000plus", path="src/drones.py",
        quote="Carbon frame, retractable landing gear, belly gimbal",
        what_ko="S1000+ 는 카본 프레임이라는 기록"),
    "prose.m350_no_camera": dict(
        kind="repo_prose", owner="m350rtk", path="src/drones.py",
        quote="NO camera in the base configuration",
        what_ko="기본 구성에 짐벌 카메라가 **없다** — 이 기체의 'camera' 그룹은 센서 포드다"),
    "prose.x500_nylon_clamp": dict(
        kind="repo_prose", owner="x500v2", path="src/drone_cad.py",
        quote="나일론 클램프",
        what_ko="파란 클램프가 나일론이라는 기록(STEP BOM 판독 근거)"),

    # ---- 문헌·물리 (재질 클래스 수준) ----------------------------------------------
    "lit.battery_foil": dict(
        kind="literature", owner="-", path="outputs/material_sources.json",
        quote="battery_pouch_foil",
        what_ko="파우치 셀 Al 배리어층 15~70 µm — GHz 에서 표피깊이의 7배 이상이라 «금속»"),
    "lit.abs_eps": dict(
        kind="literature", owner="-", path="outputs/material_sources.json",
        quote="plastic_eps_abs_zechmeister",
        what_ko="ABS 계열 εr 2.55~2.95 (1~10 GHz 측정)"),
    "lit.cfrp_sigma": dict(
        kind="literature", owner="-", path="outputs/material_sources.json",
        quote="carbon_sigma_artner",
        what_ko="CFRP 유효 도전율 1e3~1e6 S/m (4~6 GHz 도파관 NRW)"),
    "lit.fr4": dict(
        kind="literature", owner="-", path="outputs/material_sources.json",
        quote="fr4_ipc",
        what_ko="FR-4 εr 4.2~4.7 — ⚠우리 모델은 이 값을 **안 쓴다**(구리 그라운드가 지배)"),
    "lit.motor_class": dict(
        kind="literature", owner="-", path="docs/drone_material_deepverify.json",
        quote="brushless DC outrunner",
        what_ko="아웃러너 모터 = 구리 권선 + NdFeB 자석 + 전기강판 + 알루미늄/강 벨(클래스 관례)"),

    # ---- 앞선 라운드의 원장(수치 근거) --------------------------------------------
    "ledger.group_audit": dict(
        kind="repo_prose", owner="-", path="outputs/mesh_inspect_materials_check_0816.json",
        quote="assignment_audit",
        what_ko="**그룹 단위** 재질 배정 감사(2026-08-16 앞 라운드) — 이 라운드는 그것을 "
                "기체 × 부품 칸으로 쪼갠다"),
    "ledger.prop_law": dict(
        kind="repo_prose", owner="-", path="outputs/prop_law_by_airframe_0816.json",
        quote="C_law_by_airframe",
        what_ko="기체별 프로펠러 **형상** 등급표(치수 축). 재질 축은 여기서 안 나온다"),
}


# =========================================================================== #
#  4. 재질 상수의 출처 원장 — MATERIALS 의 **모든 수치**가 여기 등록돼야 한다
# =========================================================================== #
#   kind="literature"       : ref 가 material_sources.json 의 문헌 키. low/high 가 있으면 값이 그 안이어야 한다.
#   kind="itu_table"        : Sionna 내장 ITU 표에서 온다(우리가 지어낸 값이 아니다).
#   kind="modeling_choice"  : ⭐출처가 **없다**. 그러면 «없다»고 선언하고 왜 그 값인지 적는다.
_LIT = "outputs/material_sources.json"
CONSTANT_SOURCES: dict[tuple[str, str], dict] = {}


def _cs(keys, field, **kw):
    for k in (keys if isinstance(keys, (list, tuple)) else [keys]):
        CONSTANT_SOURCES[(k, field)] = dict(kw)


_cs(["plastic", "plastic_blue", "prop_plastic"], "eps_r", kind="literature",
    ref="plastic_eps_abs_zechmeister", low=2.55, high=2.95,
    why_ko="ABS/PC 문헌 구간의 한가운데(2.7). ITU plasterboard 2.73 과도 사실상 같다")
_cs(["plastic", "plastic_blue", "prop_plastic"], "sigma", kind="modeling_choice",
    why_ko="σ 0.02 S/m 은 문헌 인용이 아니라 «작은 손실»을 넣은 선택이다. tanδ 로 환산하면 "
           "3.5 GHz 에서 0.038 로 ABS 실측(0.0035~0.008)보다 5~10 배 크다. |Γ| 에는 "
           "0.24369 ↔ 0.22985(−0.5 dB) 만큼만 걸린다",
    impact_axis="gamma_bulk", impact_db_max=0.7)
_cs(["plastic", "plastic_blue", "prop_plastic"], "S", kind="modeling_choice",
    why_ko="확산 산란계수 0.20 — Sionna RT 팔 전용. 우리 SBR/PO 커널은 S 를 안 쓴다")
_cs("plastic", "gamma_po", kind="modeling_choice",
    why_ko="⭐**선언된 이탈**: 벌크 0.2437 대비 +1.21 dB. 셸이 1~3 mm 박막이라 |Γ| 가 두께·"
           "주파수에 따라 출렁이는 것을 «대표 실효값» 하나로 눌러 담았다. 0803 감사가 "
           "«2 mm 물리값(0.065~0.178)보다 높다»고 반증했고, 0816 정본이 **D3 동결**로 "
           "유지하기로 판정했다(우리 커널에는 두께 개념이 없다)",
    declared_deviation=True, deviation_ledger="outputs/material_canon_0816.json")
_cs("plastic_blue", "gamma_po", kind="modeling_choice",
    why_ko="plastic 과 같은 값·같은 근거(색만 다르다)", declared_deviation=True,
    deviation_ledger="outputs/material_canon_0816.json")
_cs("prop_plastic", "gamma_po", kind="modeling_choice",
    why_ko="⭐**선언된 이탈**: 벌크 대비 +0.22 dB. «날이 셸보다 얇다»는 방향만 반영한 0.25. "
           "그 근거 문장은 우리 CAD 가 반증했고(프롭이 셸보다 두꺼운 기체가 있다) 값은 "
           "동결 상태다 — 문면의 문제이지 값의 문제가 아니라는 것이 0816 판정",
    declared_deviation=True, deviation_ledger="outputs/material_canon_0816.json")
_cs("carbon", "eps_r", kind="modeling_choice",
    why_ko="5.0 은 문헌이 아니다(EMC 등가층 관용값은 2.0). 도체라 |Γ| 는 σ 가 정하므로 "
           "εr 2↔5 의 차이는 0.02 dB 미만이다 — 그래서 **하중을 지지 않는 상수**로 선언한다",
    impact_axis="gamma_bulk", impact_db_max=0.05)
_cs("carbon", "sigma", kind="literature", ref="carbon_sigma_artner", low=1.0e3, high=1.0e6,
    why_ko="3000 S/m 은 Artner 2017 측정 구간(1e3~1e6)의 **아래쪽**. 즉 보수적(반사를 덜 준다)")
_cs("carbon", "S", kind="modeling_choice", why_ko="확산 0.30 — Sionna RT 팔 전용")
_cs("carbon", "gamma_po", kind="modeling_choice",
    why_ko="⭐**선언된 이탈**: 벌크 0.9887 대비 −0.82 dB. 직조 섬유 사이 유전체 개구·이방성을 "
           "실효값 0.90 으로 눌렀다", declared_deviation=True)
_cs(["metal", "camera_assembly", "pcb"], "itu", kind="itu_table",
    why_ko="Sionna 내장 ITU-R P.2040 'metal'(σ=1e7 S/m). 우리가 지어낸 값이 아니다")
_cs(["concrete_light", "concrete_dark"], "itu", kind="itu_table",
    why_ko="Sionna 내장 ITU 'concrete' — 챔버 바닥")
_cs(["metal", "camera_assembly", "pcb", "concrete_light", "concrete_dark"], "thickness",
    kind="modeling_choice",
    why_ko="ITU 재질에 넘기는 슬래브 두께. 금속은 표피깊이 ≪ 두께라 값이 결과를 안 바꾼다")
_cs(["metal", "camera_assembly", "pcb", "concrete_light", "concrete_dark"], "S",
    kind="modeling_choice", why_ko="ITU 재질은 산란계수 0 고정(순수 정반사)")
_cs("camera_assembly", "gamma_po", kind="modeling_choice",
    why_ko="⭐**선언된 이탈**: ITU metal 벌크 0.9998 대비 −1.41 dB. 금속 하우징 + 유리 렌즈 + "
           "틈새를 실효 0.85 로. ⚠2026-07-14 이전에는 Sionna 쪽이 이 부품을 plastic 으로 "
           "보고 있어 두 엔진이 **10.9 dB** 어긋났다 — 그 버그를 없앤 항목이다",
    declared_deviation=True)
_cs("pcb", "gamma_po", kind="modeling_choice",
    why_ko="⭐**선언된 이탈**: −1.94 dB. 구리 그라운드플레인이 지배하되 커넥터·비도체 개구를 "
           "실효 0.80 으로. ⚠FR-4 의 εr 은 코드 어디에서도 안 읽힌다(참고 기록일 뿐)",
    declared_deviation=True)
_cs("absorber", "eps_r", kind="modeling_choice",
    why_ko="⛔**출처 없음 — 모델값이라고 선언한다.** 이 재질의 평평한 단일면 반사는 |Γ|=0.549 "
           "(−5.2 dB)로 전혀 낮지 않다. 무반사는 피라미드 골짜기의 **기하 효과**이지 재질의 성질이 아니다")
_cs("absorber", "sigma", kind="modeling_choice", why_ko="같은 선언(무출처 모델값)")
_cs("absorber", "S", kind="modeling_choice", why_ko="같은 선언(무출처 모델값)")


#  «금속으로 봐도 되는가» 를 떠받치는 물리 — 표피깊이 × 5 ≤ 실물 두께여야 한다.
METAL_OPACITY_CASES = [
    dict(name="배터리 파우치 Al 배리어층", sigma=3.5e7, thickness_m=15e-6,
         evidence="lit.battery_foil",
         why_ko="문헌 **하한** 15 µm 로 잡는다 — 하한에서도 통과해야 결론이 산다"),
    dict(name="PCB 구리 그라운드(1 oz)", sigma=5.8e7, thickness_m=35e-6,
         evidence="lit.fr4",
         why_ko="1 oz 구리 = 35 µm 는 업계 표준 두께. 두께 자체는 관용값이라 «모델링 선택»"),
    dict(name="모터 벨(알루미늄/강)", sigma=1.0e6, thickness_m=0.5e-3,
         evidence="lit.motor_class",
         why_ko="σ 는 강(1e6)으로 **보수적으로** 잡았다. 알루미늄이면 더 불투명하다"),
]
SKIN_DEPTH_MARGIN = 5.0     # 두께 ≥ 5·δ 면 «불투명»으로 본다(전력이 e^-10 = −87 dB 로 준다)


# =========================================================================== #
#  5. 기체 × 부품 출처 등급 행렬 — **이 라운드의 핵심 산출물**
# =========================================================================== #
#   model_key : 우리 표의 재질 키. `DRONE_GROUP_MAT` 과 자동 대조된다(어긋나면 FAIL).
#   real_class: 근거가 말하는 **실물 재질 클래스**. model_key 의 클래스와 다르면 `substitution` 필수.
#   grade     : [A]~[D] 또는 None(빈칸 — `unknown_reason` 필수)
#   evidence  : EVIDENCE 코드 목록. 파일이 없거나 인용문이 없으면 FAIL.
#   inferred_from / proxy_of : [C]/[D] 에 필수
def _c(model_key, real_class, grade, evidence, why, **kw):
    d = dict(model_key=model_key, real_class=real_class, grade=grade,
             evidence=list(evidence), why_ko=why)
    d.update(kw)
    return d


#  자주 쓰는 «클래스 관례» 근거 묶음
_MOTOR_EV = ["lit.motor_class"]
_SUB_NYLON = dict(
    why_ko="DJI 공식 프롭 재질표는 «나일론 복합»이라고 적는데 우리 모델 키는 ABS/PC(εr 2.7)다. "
           "나일론(PA66 건조 εr 3.15 · GF30 3.9)으로 바꾸면 벌크 |Γ| 가 +1.17~+2.30 dB 오른다 "
           "— 방향은 «우리가 과소평가»이고 크기는 프롭 그룹 한정이다.",
    measured_in="check_constants().substitution_impacts")

PART_PROVENANCE: dict[str, dict[str, dict]] = {

    # ------------------------------------------------------------------ mini2
    "mini2": {
        "body": _c("plastic", "abs_pc", "B", ["mini2.shell", "prose.mini2_arms_plastic"],
                   "FCC 내부사진에서 상·하 커버가 사출 플라스틱. 암도 같은 셸 계열이라 body 로 들어간다"),
        "canopy": _c("plastic", "abs_pc", "B", ["mini2.battery"],
                     "등에 얹히는 배터리 팩의 **바깥 플라스틱 케이스**. 안의 금속은 battery 그룹이 따로 센다"),
        "camera": _c("camera_assembly", "glass_metal", "B", ["mini2.gimbal"],
                     "짐벌 카메라 블록 — 금속 브래킷 + 렌즈"),
        "gear": _c("plastic", "abs_pc", "B-", ["mini2.legs"],
                   "앞 암 아래 두 개의 사출 착륙 포스트. 분해 근접이 아니라 공식 정면 도판이라 [B-]"),
        "motor": _c("metal", "metal", "B", ["mini2.motor_prop"] + _MOTOR_EV,
                    "프롭 허브의 강철 나사 2개와 모터 벨이 보인다. 아웃러너 = 금속(클래스 관례)"),
        "prop": _c("prop_plastic", "nylon", "C", ["mini2.prop", "dji.prop_material_mini5pro"],
                   "사진은 형상만 준다. DJI 공식 프롭 재질표에 **Mini 2 항목이 없다** — "
                   "Mini 계열(4/5 Pro = 나일론+고무, Mini 3 = 나일론+유리섬유)에서 유추",
                   inferred_from="mini5pro", substitution=_SUB_NYLON),
        "battery": _c("metal", "metal", "B", ["mini2.battery", "mini2.heatsink",
                                              "lit.battery_foil", "prose.mini2_heatsink"],
                      "⚠이 그룹은 **두 물체**다. ① 파우치 팩(Al 포일 → GHz 에서 금속) ② 공용 경로가 "
                      "심는 얇은 «구조판». Mini 2 에 마그네슘 섀시는 **없지만** SoC 위 큰 금속 "
                      "방열판/실드가 있어 대응물은 실재한다 — 다만 **치수는 공용 비율**이다",
                      declared_shared_plate=True),
        "pcb": _c("pcb", "fr4_copper", "B", ["mini2.mainboard", "mini2.shield_foil", "lit.fr4"],
                  "메인보드 + 차폐 포일. 반사면은 구리·실드캔이 지배"),
    },

    # --------------------------------------------------------------- phantom3
    "phantom3": {
        "body": _c("plastic", "abs_pc", "B", ["phantom3.shell"],
                   "흰색 일체형 사출 셸 — FCC 분해사진"),
        "canopy": _c("plastic", "abs_pc", "B", ["phantom3.battery"],
                     "배터리 팩 바깥 케이스"),
        "camera": _c("camera_assembly", "glass_metal", "B", ["phantom3.gimbal"],
                     "카메라 모듈 하우징 + 3축 짐벌"),
        "gear": _c("plastic", "abs_pc", "B", ["phantom3.gear"],
                   "볼트온 아치형 착륙다리(분리품 사진)"),
        "motor": _c("metal", "metal", "B", ["phantom3.motor"] + _MOTOR_EV,
                    "브러시리스 모터 단품 사진"),
        "prop": _c("prop_plastic", "unknown", None, ["prose.p3_prop_fork"],
                   "⛔**빈칸.** 순정 9450 과 선택품 «E305 9450 카본강화» 중 어느 쪽인지 통제되지 않았다. "
                   "카본강화면 |Γ| 0.90 ↔ 0.25 = **+11.1 dB** 라 프롭 그룹의 판정이 통째로 갈린다",
                   unknown_reason="재질 갈래가 통제되지 않음(구매 옵션) — 어느 쪽인지 정할 근거가 없다"),
        "battery": _c("metal", "metal", "B", ["phantom3.battery", "phantom3.shield_box",
                                              "lit.battery_foil", "prose.p3_no_magnesium"],
                      "인텔리전트 배터리(파우치 다발) + 중앙보드 위 **금속 실드 상자**. "
                      "⭐공용 «마그네슘 판»은 이 기체에서 **빠졌다** — P3 에는 마그네슘 골격이 없다는 "
                      "사실을 실측표(INTERNALS)가 반영했다"),
        "pcb": _c("pcb", "fr4_copper", "B", ["phantom3.pcb", "lit.fr4"],
                  "메인 PCB 상·하면 사진"),
    },

    # -------------------------------------------------------------- mavic4pro
    "mavic4pro": {
        "body": _c("plastic", "abs_pc", "B", ["mavic4pro.chassis", "dji.az91_practice"],
                   "섀시 분해사진. ⚠속 구조는 마그네슘 브래킷일 수 있으나 그 문장 자체가 "
                   "«이 기체에 대한 1차 확인은 아니다»라고 적는다"),
        "canopy": _c("plastic", "abs_pc", "B", ["mavic4pro.battery"],
                     "배터리 팩 바깥 케이스"),
        "camera": _c("camera_assembly", "glass_metal", "B", ["mavic4pro.gimbal"],
                     "짐벌 브래킷·캡 — 3카메라 클러스터"),
        "gear": _c("plastic", "abs_pc", "B", ["mavic4pro.legs"],
                   "앞 암에만 달린 사출 다리(뒤 암 사진이 대조)"),
        "motor": _c("metal", "metal", "B", ["mavic4pro.arm_motor"] + _MOTOR_EV,
                    "암 끝단 + 모터 근접"),
        "prop": _c("prop_plastic", "nylon", "A-", ["dji.prop_material_1158F", "mavic4pro.prop"],
                   "⭐DJI 공식 지원문서가 **이 기체의 프롭(1158F)** 을 «강화 나일론 복합»이라고 "
                   "직접 적는다 — 재질 축에서 이 저장소 최고 등급",
                   substitution=_SUB_NYLON),
        "battery": _c("metal", "metal", "B", ["mavic4pro.battery", "lit.battery_foil",
                                              "dji.az91_practice"],
                      "배터리 단품 + 공용 «구조판». ⚠구조판의 마그네슘 근거는 DJI 의 **관행 문서**이지 "
                      "이 기체 분해 확인이 아니다 — 그래서 판 자체는 [C] 로 따로 적는다",
                      declared_shared_plate=True, shared_plate_grade="C",
                      shared_plate_inferred_from="class:dji_mavic_az91"),
        "pcb": _c("pcb", "fr4_copper", "B", ["mavic4pro.board", "lit.fr4"],
                  "실드 프레임 + 메인보드"),
    },

    # -------------------------------------------------------------- matrice4e
    "matrice4e": {
        "body": _c("plastic", "abs_pc", "B", ["matrice4e.shell"],
                   "하부 셸 골격 분해사진"),
        "canopy": _c("plastic", "abs_pc", "B", ["matrice4e.battery"],
                     "배터리 팩 바깥 케이스"),
        "accent": _c("plastic", "abs_pc", "B-", ["matrice4e.beacon"],
                     "식별부(비콘) — 같은 셸 재질에 색만 다르다"),
        "camera": _c("camera_assembly", "glass_metal", "B-", ["matrice4e.gimbal_4e"],
                     "⭐**4E 판** 렌즈 배치 도판만 쓴다. 분해사진(t15·t16)은 **4T 판**이라 "
                     "이 칸에 쓰면 판이 섞인다(사용자 상시 규칙)"),
        "gear": _c("plastic", "abs_pc", "B-", ["matrice4e.gear"],
                   "암 LED·착륙장치 도판"),
        "motor": _c("metal", "metal", "B", ["matrice4e.motor_arm"] + _MOTOR_EV,
                    "모터 + 암 근접 — 검은 금속 벨"),
        "prop": _c("prop_plastic", "nylon", "A-", ["dji.prop_material_composite_m4", "matrice4e.prop"],
                   "DJI 공식 표가 Matrice 4 계열 프롭을 «복합재»(유리섬유 나일론)로 적고 "
                   "**카본이 아니라고** 못 박는다", substitution=_SUB_NYLON),
        "battery": _c("metal", "metal", "B", ["matrice4e.battery", "lit.battery_foil",
                                              "dji.az91_practice"],
                      "⚠이 그룹은 **두 물체**다. ① 배터리 팩 — 치수가 **공표 제원**(BPX345)이고 위치는 "
                      "공식 CAD 가 준다(셸 안 최대 금속 덩어리). ② 그 아래 얇은 «구조판»(142×68×7.1 mm, "
                      "금속 면적의 33 %) — ⛔**치수를 잰 적이 없다**. 공용 비율상자를 정정된 셸 안으로 "
                      "옮기기만 한 «엔진 손잡이»이고, 재질 근거는 DJI 의 AZ91 관행 문서뿐이다",
                      declared_shared_plate=True, shared_plate_grade="C",
                      shared_plate_inferred_from="class:dji_mavic_az91"),
        "pcb": _c("pcb", "fr4_copper", "B", ["matrice4e.board", "lit.fr4"],
                  "실드 프레임 안 메인보드"),
    },

    # ---------------------------------------------------------------- m350rtk
    "m350rtk": {
        "body": _c("plastic", "abs_pc", "B", ["m350rtk.shell"],
                   "셸 제거 기체 골격 사진 — 셸은 사출 플라스틱"),
        "arm": _c("carbon", "carbon", "B", ["m350rtk.arm_tip", "m350rtk.arm_weave",
                                            "prose.m350_arm_carbon"],
                  "접힌 측면 사진에 튜브 **직조 무늬**가 보인다. 뿌리 칼라·모터 포드는 사출이라 "
                  "따로 플라스틱 그룹으로 간다(이 기체는 튜브와 칼라를 안 뭉갠다)"),
        "gear_cf": _c("carbon", "carbon", "B-", ["m350rtk.gear"],
                      "A 프레임 튜브 다리 — 정비 매뉴얼 도판. 무늬가 보이는 근접은 없다"),
        "gear": _c("plastic", "abs_pc", "B-", ["m350rtk.gear"],
                   "다리 발·조인트의 사출 부분"),
        "motor": _c("metal", "metal", "B-", ["m350rtk.motor"] + _MOTOR_EV,
                    "정비 매뉴얼 추진계 도판(분해 근접은 아니다)"),
        "prop": _c("prop_plastic", "unknown", "C", ["m350rtk.prop"],
                   "2110s 프롭 — DJI 공식 재질표에 이 모델 항목이 없다. 산업용 대형 프롭은 "
                   "유리섬유 나일론이 관례",
                   inferred_from="class:dji_composite_prop", substitution=_SUB_NYLON),
        "battery": _c("metal", "metal", "B", ["m350rtk.battery", "lit.battery_foil"],
                      "TB65 두 팩. ⭐이 기체는 팩이 **기체 밖 후면**이라 금속이 유전체 셸 뒤에 "
                      "숨지 않는다 — 다른 기체와 산란 구조가 다르다"),
        "pcb": _c("pcb", "fr4_copper", "B", ["m350rtk.board", "lit.fr4"],
                  "**구리 실드** 보드 분해사진(자 포함)"),
        "camera": _c("camera_assembly", "unknown", None, ["m350rtk.sensors", "prose.m350_no_camera"],
                     "⛔**빈칸.** 이 기체의 'camera' 그룹은 짐벌 카메라가 아니라 **비전/FPV 센서 포드 12개**"
                     "(총 158 cm²)다. 실물은 플라스틱 하우징 + 유리창 + 속 금속이라 "
                     "camera_assembly(ITU metal + 실효 0.85)가 맞는지 **안 재봤다**",
                     unknown_reason="센서 포드의 재질 구성이 camera_assembly 와 같은지 판정한 자료가 없다"),
    },

    # ----------------------------------------------------------------- x500v2
    "x500v2": {
        "deck": _c("carbon", "carbon", "B", ["x500v2.frame_photo"],
                   "상·하판의 **카본 능직 무늬**가 사진에 그대로 보인다. ⚠STEP 의 판 부품명"
                   "(`TOP-PLATE-X500-V5`)은 재질을 말하지 않아 [A] 로 못 올린다"),
        "arm": _c("carbon", "carbon", "B", ["x500v2.frame_photo", "x500v2.arm_tip"],
                  "암 튜브의 능직 무늬. STEP 의 튜브 솔리드도 재질명은 없다"),
        "gear_cf": _c("carbon", "carbon", "A", ["x500v2.step_carbon_tube"],
                      "⭐제조사 STEP **부품명이 곧 재질**: `CARBON-FIBER-TUBE`. "
                      "이 저장소에서 재질 축 [A] 는 이 칸뿐이다"),
        "gear": _c("plastic", "abs_pc", "B", ["x500v2.step_eva", "x500v2.frame_photo"],
                   "다리 발포 슬리브는 STEP 이 `JIAO-EVA`(EVA 발포)라고 적는다. "
                   "⚠우리는 EVA 를 ABS/PC 로 모델링한다 — 아래 대체 선언 참조",
                   substitution=dict(
                       why_ko="EVA 발포는 공기가 대부분이라 εr 이 1 에 가깝고(≈1.1~1.5) ABS/PC(2.7)보다 "
                              "훨씬 덜 반사한다. 즉 **우리가 과대평가**하는 방향이다. 크기는 안 쟀다",
                       measured_in="⛔미측정")),
        "accent": _c("plastic", "abs_pc", "B", ["x500v2.frame_photo", "x500v2.step_nylon",
                                                "prose.x500_nylon_clamp"],
                     "파란 클램프·모터시트. STEP 에 `NILONGZHU`(나일론) 부재가 있고 클램프는 사출품이다",
                     real_class_note="nylon",
                     substitution=dict(
                         why_ko="나일론(PA66)을 ABS/PC 로 모델링한다. 건조 PA66 εr 3.15 → 벌크 |Γ| +1.17 dB, "
                                "흡습·GF 강화면 +1.8~+2.3 dB. 방향은 «우리가 과소평가»",
                         measured_in="check_constants().substitution_impacts")),
        "motor": _c("metal", "metal", "B", ["x500v2.arm_tip", "x500v2.motor_step"] + _MOTOR_EV,
                    "AIR2216II. ⚠제조사 STEP 은 **형상만** 준다 — 금속 판정은 클래스 물리다"),
        "prop": _c("prop_plastic", "unknown", "D", ["ref.sources_md"],
                   "⛔**대리.** 킷 프롭은 1045 지만 저장소의 프롭 기하 근거는 다른 프롭(1345)이고, "
                   "재질 표기는 어디에도 없다",
                   proxy_of="generic_1045_nylon_prop"),
        "battery": _c("metal", "metal", "C", ["lit.battery_foil"],
                      "킷에 배터리가 없다(사용자가 고른다). 4S LiPo 파우치를 가정",
                      inferred_from="class:lipo_pouch"),
        "pcb": _c("pcb", "fr4_copper", "B-", ["x500v2.fc_stack", "lit.fr4"],
                  "PM02/PM06 전원보드 — 사진은 스택 겉모습"),
        "fc": _c("pcb", "fr4_copper", "B", ["x500v2.fc_stack", "lit.fr4"],
                 "Pixhawk 6C 비행제어기 — 상판 위 노출"),
    },

    # ------------------------------------------------------------- typhoonh480
    "typhoonh480": {
        "body": _c("plastic", "abs_pc", "B-", ["typhoonh480.official", "prose.typhoon_arm_unknown"],
                   "⭐**이 기체의 가장 큰 구멍.** 공식 사진뿐이고 분해 자료가 없다. 게다가 **암이 "
                   "body 그룹에 들어간다** — 암이 카본이면 |Γ| 0.90 ↔ 0.28 = **10.14 dB** 다. "
                   "저장소는 «플라스틱으로 두고 카본은 라벨된 감도 사례» 라고 선언한다"),
        "canopy": _c("plastic", "abs_pc", "B-", ["typhoonh480.official"], "공식 사진의 상부 캐노피"),
        "camera": _c("camera_assembly", "glass_metal", "B-", ["typhoonh480.cgo3"],
                     "CGO3+ 짐벌 공식 사진"),
        "gear": _c("plastic", "abs_pc", "B-", ["typhoonh480.gear"], "접이 다리의 사출 부분"),
        "gear_cf": _c("carbon", "unknown", "C", ["typhoonh480.gear"],
                      "다리 튜브를 카본으로 본다. 공식 사진에서 검은 튜브로만 보이고 무늬는 안 보인다",
                      inferred_from="class:carbon_tube_leg"),
        "motor": _c("metal", "metal", "C", _MOTOR_EV,
                    "분해 자료가 없다. 아웃러너 클래스 관례로만 금속",
                    inferred_from="class:brushless_outrunner"),
        "prop": _c("prop_plastic", "unknown", "C", ["typhoonh480.official"],
                   "Yuneec 은 프롭 재질을 공표하지 않는다. 소비자기 프롭 = 나일론 계열 관례",
                   inferred_from="class:consumer_nylon_prop", substitution=_SUB_NYLON),
        "battery": _c("metal", "metal", "C", ["lit.battery_foil"],
                      "파우치 팩(클래스). 이 기체는 공용 «구조판»을 안 받는다",
                      inferred_from="class:lipo_pouch"),
        "pcb": _c("pcb", "fr4_copper", "C", ["lit.fr4"],
                  "분해 자료 없음 — FR-4 + 구리 + 실드캔 관례",
                  inferred_from="class:consumer_fc_board"),
    },

    # ---------------------------------------------------------------- mini5pro
    "mini5pro": {
        "body": _c("plastic", "abs_pc", "B-", ["mini5pro.render"],
                   "공식 렌더 3장뿐. 회색 사출 셸로 보이지만 분해 자료가 없다"),
        "canopy": _c("plastic", "abs_pc", "B-", ["mini5pro.render"], "배터리 팩 바깥 케이스"),
        "accent": _c("plastic", "abs_pc", "B-", ["mini5pro.render"], "전방 식별색"),
        "camera": _c("camera_assembly", "glass_metal", "B-", ["mini5pro.render"],
                     "짐벌 카메라 — 렌더에서 겉만 보인다"),
        "gear": _c("plastic", "abs_pc", "B-", ["mini5pro.render"],
                   "앞 모터 포드 아래 두 갈래 다리(렌더에서 확인된 부품)"),
        "motor": _c("metal", "metal", "C", _MOTOR_EV,
                    "분해 자료 없음 — 아웃러너 클래스 관례", inferred_from="class:brushless_outrunner"),
        "prop": _c("prop_plastic", "nylon", "A-", ["dji.prop_material_mini5pro"],
                   "⭐DJI 공식 프롭 재질표가 **Mini 5 Pro** 를 «나일론 + 고무(팁)»로 직접 적는다. "
                   "사진이 3장뿐인 기체인데 프롭 재질만은 1차 자료가 있다",
                   substitution=_SUB_NYLON),
        "battery": _c("metal", "metal", None, ["lit.battery_foil"],
                      "⛔**빈칸 — 이 라운드의 발견.** 파우치 팩은 [C] 로 방어되지만, 이 기체는 공용 "
                      "경로가 심는 **얇은 «구조판»(80×50×4.7 mm, 금속 그룹 면적의 29 %)** 을 받는다. "
                      "DJI Mini 계열에 마그네슘 섀시가 있다는 근거가 저장소에 **하나도 없고**, "
                      "형제기 Mini 2 는 «마그네슘 없음» 이라고 명시적으로 선언한다",
                      unknown_reason="공용 구조판의 실물 대응물이 이 기체에 있는지 근거가 없다",
                      declared_shared_plate=True, shared_plate_grade=None),
        "pcb": _c("pcb", "fr4_copper", "C", ["lit.fr4"],
                  "분해 자료 없음 — 클래스 관례", inferred_from="class:consumer_fc_board"),
    },

    # ---------------------------------------------------------------- phantom4
    "phantom4": {
        "body": _c("plastic", "abs_pc", "C", ["phantom4.sibling", "dji.p4_magnesium_core"],
                   "⚠폴더의 사진 5장은 **Phantom 4 Pro+ V2.0**(다른 판)이다. 셸이 사출 플라스틱인 "
                   "것은 계열 공통이라 [C] 로 둔다",
                   inferred_from="phantom3"),
        "canopy": _c("plastic", "abs_pc", "C", ["phantom4.sibling"], "배터리 팩 케이스",
                     inferred_from="phantom3"),
        "camera": _c("camera_assembly", "glass_metal", "C", ["phantom4.sibling"],
                     "함몰 짐벌 — 다른 판 사진", inferred_from="phantom3"),
        "gear": _c("plastic", "abs_pc", "C", ["phantom4.sibling"], "일체형 아치 다리",
                   inferred_from="phantom3"),
        "motor": _c("metal", "metal", "C", _MOTOR_EV, "아웃러너 클래스 관례",
                    inferred_from="class:brushless_outrunner"),
        "prop": _c("prop_plastic", "unknown", "C", ["phantom4.sibling"],
                   "9450S. DJI 공식 재질표에 항목이 없다 — 계열 유추",
                   inferred_from="phantom3", substitution=_SUB_NYLON),
        "battery": _c("metal", "metal", "C", ["lit.battery_foil", "prose.p3_no_magnesium",
                                            "dji.p4_magnesium_core"],
                      "파우치 팩 + 공용 «구조판». ⭐이 기체는 판의 근거가 **오히려 있다** — "
                      "마그네슘 코어는 Phantom 4 의 대표 구조 개선이라고 phantom3 기록이 적는다. "
                      "다만 그 문장도 우리 서술(2차)이라 [C] 다",
                      inferred_from="phantom3", declared_shared_plate=True, shared_plate_grade="C",
                      shared_plate_inferred_from="phantom3"),
        "pcb": _c("pcb", "fr4_copper", "C", ["lit.fr4"], "클래스 관례",
                  inferred_from="class:consumer_fc_board"),
    },

    # -------------------------------------------------------------- s1000plus
    "s1000plus": {
        "body": _c("plastic", "carbon", "B-", ["s1000plus.top", "prose.s1000_carbon_frame",
                                               "dji.s1000_arms_cf", "ledger.group_audit"],
                   "⛔⭐**알려진 배정 오류(선언).** 이 기체의 중앙은 셸이 아니라 **판 스택**이고 "
                   "판 재질은 카본 라미네이트로 본다(암·착륙장치는 DJI 공식 확인, **중앙판 자체는 "
                   "관례 추정**이다 — 그 구별을 뭉개지 않는다). 우리 메쉬는 여기에 3,555 cm² 짜리 "
                   "플라스틱 'body' 셸을 준다. |Γ| 0.28 ↔ 0.90 = **10.14 dB** 자리이고 이 기체에서 "
                   "면적이 가장 큰 그룹이다. 앞 라운드가 이미 A1 로 기록했다",
                   substitution=dict(
                       why_ko="플라스틱으로 모델링한 자리가 실물은 카본이다 — **우리가 과소평가**. "
                              "면적이 커서 이 기체의 σ 판정에 직접 걸린다",
                       measured_in="outputs/mesh_inspect_materials_check_0816.json::rf_estimates")),
        "arm": _c("carbon", "carbon", "A-", ["dji.s1000_arms_cf", "s1000plus.top",
                                             "prose.s1000_carbon_frame"],
                  "⭐DJI 공식 기능페이지가 «모든 프레임 암은 카본»이라고 직접 적는다. "
                  "판매점 상면 사진이 그것과 어긋나지 않는다"),
        "gear_cf": _c("carbon", "carbon", "A-", ["dji.s1000_arms_cf", "s1000plus.top"],
                      "⭐같은 공식 문장이 «접이식 착륙장치도 카본»이라고 적는다"),
        "gear": _c("plastic", "abs_pc", "B-", ["s1000plus.top"], "다리 조인트·발의 사출 부분"),
        "accent": _c("plastic", "abs_pc", "B-", ["s1000plus.top"], "붉은 식별색 부재"),
        "camera": _c("camera_assembly", "glass_metal", "C", ["s1000plus.top"],
                     "벨리 짐벌(제니뮤즈류). 사진에 짐벌이 안 달려 있어 계열 유추",
                     inferred_from="class:dji_gimbal"),
        "motor": _c("metal", "metal", "B-", ["s1000plus.top"] + _MOTOR_EV, "8개 아웃러너 모터"),
        "prop": _c("prop_plastic", "unknown", "A-", ["dji.s1000_prop_plastic", "s1000plus.top"],
                   "⭐DJI 공식 제원이 순정 1552 를 «고강도 엔지니어링 플라스틱»이라고 적는다 — "
                   "**카본이 아니라는 것**이 여기서 결정적이다(0.90 ↔ 0.25 = 11.1 dB). "
                   "다만 어떤 폴리머인지는 안 밝히므로 실물 클래스는 여전히 빈칸이다"),
        "battery": _c("metal", "metal", "C", ["lit.battery_foil"],
                      "상판 위 트레이의 LiPo 팩(기체 밖에 드러난다)", inferred_from="class:lipo_pouch"),
        "pcb": _c("pcb", "fr4_copper", "C", ["lit.fr4"], "전원분배판 — 클래스 관례",
                  inferred_from="class:consumer_fc_board"),
    },
}

#  ⛔**판 규칙** — 어떤 근거는 어떤 칸에 쓰면 안 된다(사용자 상시 규칙).
FORBIDDEN_VARIANT_USE = [
    dict(airframe="matrice4e", groups=("camera",), variant="M4T",
         why_ko="공식 CAD·분해사진의 4T 판 짐벌 치수를 4E 칸에 쓰지 않는다(사용자 지시)"),
]


# =========================================================================== #
#  6. 라벨↔형상 정합 — 이름이 그 자리에 맞나 (M12 의 «뒤바뀜» 축)
# =========================================================================== #
#   ⭐ 아래 잣대는 **10기체 전부를 실제로 재서** 고른 것이다(음성 대조가 전부 통과한다).
#     여백도 함께 적었다 — 여백이 없는 잣대는 거짓경보를 낸다.
GEAR_FAMILY = ("gear", "gear_cf")
ROTOR_XY_TOL_MM = 20.0          # 모터·프롭 부품이 로터 중심에서 벗어나도 되는 거리(실측 최대 0.1 mm)
#  내부 부품이 셸 bbox 안에 들어야 하는 기체에서 제외 — 실물이 밖에 드러난다(앞 라운드 선언과 같은 목록)
OPEN_INTERNALS = {"x500v2", "s1000plus"}


def _mesh_arrays(mesh):
    return (np.asarray(mesh.v, float), np.asarray(mesh.f, int), np.asarray(mesh.g))


def _group_area_centroid(V, F, G, grp):
    sel = G == grp
    if not sel.any():
        return None
    f = F[sel]
    a = 0.5 * np.linalg.norm(np.cross(V[f[:, 1]] - V[f[:, 0]], V[f[:, 2]] - V[f[:, 0]]), axis=1)
    c = V[f].mean(1)
    tot = float(a.sum())
    ctr = (c * a[:, None]).sum(0) / max(tot, 1e-30)
    return dict(area_m2=tot, centroid=ctr, zmin=float(V[np.unique(f)][:, 2].min()),
                zmax=float(V[np.unique(f)][:, 2].max()))


def check_label_geometry(spec, mesh=None, verbose=False) -> dict:
    """⭐**라벨이 그 자리에 맞나** — 이름과 형상이 어긋나면 잡는다.

    잣대 다섯(전부 실측으로 여백을 확인했다):
      L1 착륙장치가 **가장 낮다** — 기체 최저점은 gear/gear_cf 것이어야 한다
      L2 프로펠러가 **모터 위**에 있다 (무게중심 z 비교)
      L3 카메라는 **동체보다 아래, 착륙장치보다 위**
      L4 모터·프롭 부품은 전부 **로터 중심**에 붙어 있다 (xy 20 mm 안)
      L5 내부 부품(battery·pcb·fc)의 무게중심이 **셸 bbox 안**

    이 다섯이 왜 필요한가: 범주 지도 M12 가 심은 «camera↔gear 라벨 뒤바꾸기»가
    수밀·법선·치수·손대칭성 **전 검사를 통과**했다. 이름이 유효한지만 보고
    이름이 **맞는 자리에 있는지**는 아무도 안 봤기 때문이다."""
    from drones import rotor_layout, build_drone            # 지연 import(순환 방지)
    if mesh is None:
        mesh = build_drone(spec)
    V, F, G = _mesh_arrays(mesh)
    groups = set(G.tolist())
    st = {g: _group_area_centroid(V, F, G, g) for g in groups}
    fails, notes = [], []

    #  L1 — 최저점의 주인
    zmin_all = float(V[:, 2].min())
    owner = None
    for g in groups:
        if abs(st[g]["zmin"] - zmin_all) < 1e-9:
            owner = g
            break
    have_gear = any(g in groups for g in GEAR_FAMILY)
    if have_gear and owner not in GEAR_FAMILY:
        fails.append(f"L1 최저점({zmin_all*1000:.1f} mm)의 주인이 '{owner}' 다 — 착륙장치여야 한다")
    notes.append(f"L1 최저점 주인 = {owner}")

    #  L2 — 프롭이 모터 위
    if "prop" in st and "motor" in st:
        dz = (st["prop"]["centroid"][2] - st["motor"]["centroid"][2]) * 1000
        if dz <= 0:
            fails.append(f"L2 프롭 무게중심이 모터보다 {abs(dz):.1f} mm 아래다")
        notes.append(f"L2 프롭−모터 z = {dz:+.1f} mm")

    #  L3 — 카메라는 동체 아래·착륙장치 위
    shell = "body" if "body" in st else ("deck" if "deck" in st else None)
    if "camera" in st and shell:
        dzb = (st["camera"]["centroid"][2] - st[shell]["centroid"][2]) * 1000
        if dzb >= 0:
            fails.append(f"L3 카메라 무게중심이 '{shell}' 보다 {dzb:+.1f} mm 위다 — 짐벌은 아래에 매달린다")
        notes.append(f"L3 카메라−{shell} z = {dzb:+.1f} mm")
    if "camera" in st and "gear" in st:
        dzg = (st["camera"]["centroid"][2] - st["gear"]["centroid"][2]) * 1000
        if dzg <= 0:
            fails.append(f"L3 카메라가 착륙장치보다 {abs(dzg):.1f} mm 아래다 — 라벨이 뒤바뀐 모양")
        notes.append(f"L3 카메라−착륙장치 z = {dzg:+.1f} mm")

    #  L4 — 회전부는 로터 중심에
    import trimesh
    ctr = np.asarray([r["center"] for r in rotor_layout(spec)], float)
    for grp in ("motor", "prop"):
        if grp not in groups:
            continue
        tm = trimesh.Trimesh(vertices=V, faces=F[G == grp], process=False)
        comps = tm.split(only_watertight=False, repair=False)
        if not len(comps):
            continue
        cc = np.array([c.vertices.mean(0) for c in comps])
        d = np.linalg.norm(cc[:, None, :2] - ctr[None, :, :2], axis=2).min(1) * 1000
        if float(d.max()) > ROTOR_XY_TOL_MM:
            fails.append(f"L4 '{grp}' 부품이 로터 중심에서 {d.max():.1f} mm 떨어져 있다 "
                         f"(허용 {ROTOR_XY_TOL_MM} mm)")
        notes.append(f"L4 {grp} 부품 {len(comps)}개, 로터중심까지 최대 {d.max():.2f} mm")

    #  L5 — 내부 부품은 셸 안
    if shell and spec.key not in OPEN_INTERNALS:
        Vb = V[np.unique(F[G == shell])]
        lo, hi = Vb.min(0), Vb.max(0)
        for grp in ("battery", "pcb", "fc"):
            if grp not in groups:
                continue
            c = V[np.unique(F[G == grp])].mean(0)
            if not bool(((c >= lo) & (c <= hi)).all()):
                fails.append(f"L5 '{grp}' 무게중심이 '{shell}' bbox 밖이다 — 내부 부품이 아니다")
            notes.append(f"L5 {grp} 무게중심 셸 안 = {bool(((c >= lo) & (c <= hi)).all())}")

    if verbose:
        for n in notes:
            print("   ", n)
    return dict(ok=not fails, failures=fails, notes=notes, key=spec.key)


# =========================================================================== #
#  7. 그룹 라벨 ↔ 재질표 닫힘 (M12 의 «미등록·오타» 축)
# =========================================================================== #
def check_group_table_closure(meshes: dict | None = None) -> dict:
    """메쉬에 실린 **모든 그룹 라벨**이 세 표에 다 있는가.
      · `drones.DRONE_GROUP_MAT` (그룹 → 재질)
      · `materials.MATERIALS`    (재질 → 물성)
      · `gazebo_export.DENSITY`  (그룹 → 밀도)  ← 저장소에서 **유일하게** 예외를 던지는 자리
    그리고 반대 방향도 본다 — 표에만 있고 어느 메쉬에도 없는 그룹(죽은 항목)."""
    from drones import DRONES, DRONE_GROUP_MAT, build_drone
    from materials import MATERIALS
    try:
        from gazebo_export import DENSITY
    except Exception:
        DENSITY = None

    if meshes is None:
        meshes = {k: build_drone(s) for k, s in DRONES.items()}
    used, fails = {}, []
    for k, m in meshes.items():
        for g in sorted(set(np.asarray(m.g).tolist())):
            used.setdefault(g, []).append(k)
            if g not in DRONE_GROUP_MAT:
                fails.append(f"{k}: 그룹 '{g}' 가 DRONE_GROUP_MAT 에 없다 "
                             f"(→ rcs_sbr 는 plastic, rcs_po 는 PEC 로 **조용히** 흐른다)")
            elif DRONE_GROUP_MAT[g][0] not in MATERIALS:
                fails.append(f"{k}: 그룹 '{g}' 의 재질 '{DRONE_GROUP_MAT[g][0]}' 가 MATERIALS 에 없다")
            if DENSITY is not None and g not in DENSITY:
                fails.append(f"{k}: 그룹 '{g}' 가 gazebo_export.DENSITY 에 없다(등록 3곳 중 하나 누락)")
    unused = sorted(set(DRONE_GROUP_MAT) - set(used))
    return dict(ok=not fails, failures=fails, used_groups={g: v for g, v in sorted(used.items())},
                unused_table_entries=unused)


# =========================================================================== #
#  8. 조용한 폴백 — **코드가 지금도 그 폴백을 갖고 있는가**(정적 스캔, 표류 감지)
# =========================================================================== #
#   ⚠ 이 검사는 폴백을 **없애지 않는다**(고치면 σ 원장이 낡는다). 지금 어디에 무엇이 있는지
#     원장에 못 박고, **새로 생기거나 조용히 바뀌면** 걸리게 한다.
DECLARED_FALLBACK_SITES = [
    dict(file="src/rcs_sbr.py", pattern=r'group_mat\.get\(grp,\s*"plastic"\)',
         engine="SBR(Sionna Mitsuba 광선)", falls_to="plastic",
         why_ko="모르는 그룹이 유전체 셸(|Γ|=0.28)로 흐른다"),
    dict(file="src/rcs_sbr.py", pattern=r'group_mat\.get\(grp,\s*"plastic"\)',
         engine="SBR(PTD 모서리)", falls_to="plastic", occurrence=2,
         why_ko="PTD 모서리 |Γ| 지도도 같은 폴백을 쓴다"),
    dict(file="src/rcs_po.py", pattern=r'gamma\.get\(mesh\.g\[fi\],\s*1\.0\)',
         engine="PO(점구름)", falls_to="PEC(1.0)",
         why_ko="⭐같은 오타가 **반대 방향**으로 틀린다 — SBR 은 0.28, PO 는 1.0"),
]


def check_fallback_sites(root: str | None = None, sources: dict | None = None) -> dict:
    """선언된 폴백 자리들이 **지금도 그대로**인가. 새 폴백이 생기면 잡는다.

    `sources` 로 «파일경로 → 소스문자열» 을 주면 그것을 대신 읽는다(양성 대조용)."""
    root = root or ROOT
    found, fails = [], []
    for site in DECLARED_FALLBACK_SITES:
        path = site["file"]
        try:
            src = sources[path] if sources and path in sources else \
                open(os.path.join(root, path), encoding="utf-8").read()
        except FileNotFoundError:
            fails.append(f"{path}: 파일이 없다(선언된 폴백 자리가 사라졌다 — 원장을 갱신할 것)")
            continue
        n = len(re.findall(site["pattern"], src))
        need = site.get("occurrence", 1)
        found.append(dict(file=path, engine=site["engine"], falls_to=site["falls_to"], count=n))
        if n < need:
            fails.append(f"{path}: 선언된 폴백({site['engine']})이 안 보인다 — "
                         f"코드가 바뀌었으면 이 원장도 같이 고쳐야 한다")

    #  새로 생긴 폴백 찾기 — 그룹/재질 딕셔너리에 기본값을 주는 패턴 전수 스캔
    extra = []
    scan_pat = re.compile(r"(group_mat|gamma|matmap|group_to_mat|gm)\.get\([^,()\n]+,[^)\n]+\)")
    for rel in ("src/rcs_sbr.py", "src/rcs_po.py", "src/microdoppler.py", "src/scene_build.py"):
        try:
            src = sources[rel] if sources and rel in sources else \
                open(os.path.join(root, rel), encoding="utf-8").read()
        except FileNotFoundError:
            continue
        for m in scan_pat.finditer(src):
            line = src[:m.start()].count("\n") + 1
            txt = m.group(0)
            known = any(re.search(s["pattern"], txt) for s in DECLARED_FALLBACK_SITES
                        if s["file"] == rel)
            if not known:
                extra.append(dict(file=rel, line=line, code=txt.strip()))
    if extra:
        fails.append(f"⭐선언 안 된 조용한 폴백 {len(extra)}곳: "
                     + "; ".join(f"{e['file']}:{e['line']} {e['code']}" for e in extra[:5]))
    #  두 엔진의 폴백이 얼마나 다른가 — 숫자로 남긴다
    gap_db = db(1.0) - db(0.28)
    return dict(ok=not fails, failures=fails, sites=found, undeclared=extra,
                two_engine_gap_db=round(gap_db, 2),
                gap_note_ko=f"같은 미등록 그룹이 SBR 은 |Γ|=0.28, PO 는 1.0 으로 흐른다 = "
                            f"진폭 {gap_db:.2f} dB(σ 로는 그 두 배) 차이")


# =========================================================================== #
#  9. 재질 상수 검사 — 출처·문헌구간·ITU·표피깊이·두 엔진 어긋남
# =========================================================================== #
def _load_literature() -> dict:
    with open(MATERIAL_SOURCES_JSON, encoding="utf-8") as f:
        js = json.load(f)
    return {e["key"]: e for e in js.get("literature", [])}, js


def check_constants(materials_table: dict | None = None, verbose=False) -> dict:
    """재질 상수 하나하나가 **출처를 갖고 있고 그 출처와 맞는가**.

    다섯 갈래:
      C1 **선언 누락** — MATERIALS 의 모든 수치 필드가 CONSTANT_SOURCES 에 등록돼야 한다
      C2 **문헌 이탈** — 문헌을 주장한 값이 그 문헌 구간 밖이면 FAIL(«등급 인플레»의 재질판)
      C3 **ITU 키·대역** — itu 이름이 설치본 표에 있고, 우리 세 대역이 유효구간 안인가
      C4 **금속 불투명** — 금속으로 «분류»한 부품이 표피깊이 기준으로 정말 불투명한가
      C5 **두 엔진 어긋남** — Sionna 가 보는 벌크 |Γ| 와 PO 가 쓰는 |Γ| 의 차이가
         **선언돼 있는가**(2026-07-14 카메라 10.9 dB 버그가 이 축이다)
    덤: 앞 라운드의 Sionna 실측 원장과 우리 정적 계산이 맞는지 교차검증한다."""
    if materials_table is None:
        from materials import MATERIALS as materials_table
    lit, lit_js = _load_literature()
    fails, rows = [], []

    #  --- C1·C2 : 선언 + 문헌 구간 -----------------------------------------
    numeric_fields = ("eps_r", "sigma", "S", "gamma_po", "thickness", "itu")
    for key, spec in materials_table.items():
        for field in numeric_fields:
            if field not in spec:
                continue
            decl = CONSTANT_SOURCES.get((key, field))
            if decl is None:
                fails.append(f"C1 {key}.{field} — **출처 선언이 없다**. 문헌이든 «모델링 선택»이든 "
                             f"CONSTANT_SOURCES 에 적어야 한다")
                continue
            row = dict(material=key, field=field, value=spec[field], kind=decl["kind"])
            if decl["kind"] == "literature":
                ref = decl.get("ref")
                if ref not in lit:
                    fails.append(f"C2 {key}.{field} — 문헌 키 '{ref}' 가 {MATERIAL_SOURCES_JSON} 에 없다(죽은 참조)")
                else:
                    lo, hi = decl.get("low"), decl.get("high")
                    v = float(spec[field])
                    row.update(ref=ref, low=lo, high=hi)
                    if lo is not None and hi is not None and not (lo <= v <= hi):
                        fails.append(f"C2 {key}.{field}={v} 가 문헌 구간 [{lo}, {hi}] 밖이다 "
                                     f"— 문헌을 주장하려면 구간 안이어야 한다(ref={ref})")
            rows.append(row)

    #  --- C3 : ITU 키와 대역 -------------------------------------------------
    itu_rows = []
    tbl = itu_table()
    for key, spec in materials_table.items():
        if "itu" not in spec:
            continue
        name = spec["itu"]
        if name not in tbl:
            fails.append(f"C3 {key}.itu='{name}' 가 설치본 Sionna ITU 표에 없다 "
                         f"(있는 것 = {sorted(tbl)})")
            continue
        for bname, fc in BANDS.items():
            try:
                er, sg = itu_params(name, fc)
                itu_rows.append(dict(material=key, itu=name, band=bname,
                                     eps_r=er, sigma=sg))
            except ValueError as e:
                fails.append(f"C3 {key}({name}) 는 {bname} 에서 ITU 유효구간 밖이다 — {e}")

    #  --- 교차검증 : 우리 정적 계산 ↔ 예전 Sionna 실측 원장 ------------------
    xcheck, xfail = [], 0
    for cur in lit_js.get("current_values", []):
        k = cur["key"]
        if k not in materials_table:
            continue
        for bname, fc in BANDS.items():
            rec = cur.get("per_band", {}).get(bname)
            if not rec:
                continue
            try:
                er, sg, _ = material_params_static(k, fc, materials_table)
            except Exception as e:                       # 검사기는 **죽지 않는다** — 판정을 낸다
                fails.append(f"교차검증 {k}@{bname}: 값을 못 구했다 — {e}")
                xfail += 1
                continue
            gb = gamma_bulk_from(er, sg, fc)
            d = abs(gb - float(rec["gamma_bulk"]))
            xcheck.append(dict(material=k, band=bname, ours=round(gb, 6),
                               ledger=round(float(rec["gamma_bulk"]), 6), diff=round(d, 8)))
            if d > 1e-6:
                xfail += 1
    if xfail:
        fails.append(f"교차검증: 정적 ITU 계산이 예전 Sionna 실측 원장과 {xfail}곳 어긋난다")

    #  --- C4 : 금속 불투명 ---------------------------------------------------
    metal_rows = []
    fc_low = min(BANDS.values())
    for case in METAL_OPACITY_CASES:
        d = skin_depth_m(case["sigma"], fc_low)
        n = case["thickness_m"] / d
        ok = n >= SKIN_DEPTH_MARGIN
        metal_rows.append(dict(name=case["name"], skin_depth_um=round(d * 1e6, 3),
                               thickness_um=round(case["thickness_m"] * 1e6, 2),
                               skin_depths=round(n, 2), ok=ok, evidence=case["evidence"]))
        if not ok:
            fails.append(f"C4 «{case['name']}» 는 {fc_low/1e9:.3f} GHz 에서 두께가 표피깊이의 "
                         f"{n:.2f}배뿐이다 — «금속으로 본다»는 배정이 안 선다(기준 {SKIN_DEPTH_MARGIN}배)")

    #  --- C5 : 두 엔진 어긋남 -----------------------------------------------
    ENGINE_ALARM_DB = 6.0            # 이보다 크면 «선언»만으로는 안 되고 반드시 사유가 있어야 한다
    engine_rows = []
    for key, spec in materials_table.items():
        fc = 3.5e9
        try:
            er, sg, _ = material_params_static(key, fc, materials_table)
        except Exception as e:                           # 위 C3 가 이미 사유를 적었다
            fails.append(f"C5 {key}: 재질값을 못 구해 두 엔진 대조를 못 했다 — {e}")
            engine_rows.append(dict(material=key, gamma_bulk=None, gamma_po=None,
                                    gap_db=None, declared=None, error=str(e)))
            continue
        gb = gamma_bulk_from(er, sg, fc)
        gp = float(spec.get("gamma_po", gb))
        gap = db(gp) - db(gb)
        decl = CONSTANT_SOURCES.get((key, "gamma_po"), {})
        declared = bool(decl.get("declared_deviation"))
        engine_rows.append(dict(material=key, gamma_bulk=round(gb, 5), gamma_po=round(gp, 5),
                                gap_db=round(gap, 3), declared=declared))
        if abs(gap) > 1e-9 and not declared:
            fails.append(f"C5 {key}: Sionna 벌크 |Γ|={gb:.4f} 와 PO |Γ|={gp:.4f} 가 "
                         f"{gap:+.2f} dB 어긋나는데 **선언이 없다**")
        if abs(gap) > ENGINE_ALARM_DB:
            fails.append(f"C5 {key}: 두 엔진 차이가 {gap:+.2f} dB — 경보선({ENGINE_ALARM_DB} dB)을 넘는다. "
                         f"2026-07-14 카메라 버그가 10.9 dB 였다")

    #  --- 덤 : 대체 선언이 요구하는 «크기» 를 실제로 잰다 ----------------------
    subs = {}
    for name, er, td in [("우리 ABS/PC (plastic)", 2.7, None), ("PA66 건조", 3.15, 0.015),
                         ("PA66 흡습 2 %", 3.60, 0.030), ("PA66-GF30", 3.90, 0.018),
                         ("EVA 발포(추정 하한)", 1.20, 0.005)]:
        per = {}
        for bname, fc in BANDS.items():
            sg = 0.02 if td is None else td * 2 * np.pi * fc * EPS0 * er
            g = gamma_bulk_from(er, sg, fc)
            g0 = gamma_bulk_from(2.7, 0.02, fc)
            per[bname] = dict(eps_r=er, gamma_bulk=round(g, 5), dB_vs_ours=round(db(g) - db(g0), 3))
        subs[name] = per

    if verbose:
        print(f"  상수 {len(rows)}개 선언 · ITU {len(itu_rows)}행 · 금속 {len(metal_rows)}건 · "
              f"엔진대조 {len(engine_rows)}건 · 실패 {len(fails)}")
    return dict(ok=not fails, failures=fails, declarations=rows, itu=itu_rows,
                itu_crosscheck=dict(n=len(xcheck), mismatches=xfail, rows=xcheck[:12]),
                metal_opacity=metal_rows, engine_agreement=engine_rows,
                substitution_impacts=subs)


# =========================================================================== #
#  10. 출처 등급 검사 — 죽은 링크 · 죽은 인용 · 등급 인플레 · 대리 미표시
# =========================================================================== #
def _evidence_ok(code: str, root: str, evidence_table: dict) -> tuple[bool, str, dict]:
    ev = evidence_table.get(code)
    if ev is None:
        return False, f"근거 코드 '{code}' 가 등록부에 없다", {}
    p = os.path.join(root, ev["path"])
    if not os.path.exists(p):
        return False, f"근거 '{code}' 의 파일이 없다(죽은 링크): {ev['path']}", ev
    q = ev.get("quote")
    if q:
        try:
            with open(p, encoding="utf-8", errors="ignore") as f:
                txt = f.read()
        except Exception as e:                                  # 이진 파일에 인용문을 걸면 안 된다
            return False, f"근거 '{code}' 의 인용문을 읽을 수 없다: {e}", ev
        if q not in txt:
            return False, f"근거 '{code}' 의 인용문이 그 파일에 **없다**(죽은 인용): {q!r}", ev
    return True, "", ev


def check_provenance(root: str | None = None, ledger: dict | None = None,
                     evidence_table: dict | None = None, meshes: dict | None = None) -> dict:
    """⭐**등급이 진짜 근거를 가리키나.** 여덟 규칙을 건다.

      P1 **덮개(coverage)** — 메쉬에 실재하는 (기체, 그룹) 칸이 원장에 다 있는가
      P2 **재질 일치**       — 칸의 model_key 가 DRONE_GROUP_MAT 과 같은가
      P3 **죽은 링크·인용**  — 근거 파일이 실재하고, 인용문이 그 파일 안에 실제로 있는가
      P4 ⭐**등급 인플레**   — 등급이 근거 «종류»의 상한을 넘지 않는가
                              (사진뿐인데 [A], 대리인데 [B] 같은 것)
      P5 **주인 일치**       — own_* 근거의 주인이 그 기체인가(남의 사진을 자기 것처럼 쓰지 않는가)
      P6 **[C]/[D] 선언**    — [C] 는 inferred_from, [D] 는 proxy_of 가 있어야 한다.
                              반대로 [A]~[B-] 에 proxy_of 가 있으면 모순이다
      P7 **판(variant) 규칙**— 4T 판 근거를 4E 짐벌 칸에 쓰지 않는가
      P8 **대체 선언**       — 실물 클래스와 모델 키 클래스가 다르면 그 사실과 크기를 적었는가
      + **빈칸 규칙** — 등급이 없으면 `unknown_reason` 이 있어야 한다(모르면 모른다)"""
    from drones import DRONES, DRONE_GROUP_MAT, build_drone
    root = root or ROOT
    ledger = ledger if ledger is not None else PART_PROVENANCE
    evidence_table = evidence_table if evidence_table is not None else EVIDENCE
    if meshes is None:
        meshes = {k: build_drone(s) for k, s in DRONES.items()}

    fails, cells, coverage = [], [], {}
    for key, mesh in meshes.items():
        groups = sorted(set(np.asarray(mesh.g).tolist()))
        book = ledger.get(key, {})
        missing = [g for g in groups if g not in book or book.get(g) is None]
        extra = [g for g in book if g not in groups and book.get(g) is not None]
        coverage[key] = dict(n_groups=len(groups), n_cells=len([g for g in book if book[g]]),
                             missing=missing, extra=extra)
        if missing:
            fails.append(f"P1 {key}: 메쉬에 있는 그룹인데 원장에 칸이 없다 → {missing}")
        if extra:
            fails.append(f"P1 {key}: 원장에만 있고 메쉬에 없는 칸 → {extra}")

        for grp in groups:
            cell = book.get(grp)
            if cell is None:
                continue
            tag = f"{key}.{grp}"
            #  P2 재질 일치
            want = DRONE_GROUP_MAT.get(grp, (None,))[0]
            if cell["model_key"] != want:
                fails.append(f"P2 {tag}: 원장 재질 '{cell['model_key']}' ≠ DRONE_GROUP_MAT '{want}'")
            #  P3 근거 실재
            kinds, owners, variants = [], [], []
            for code in cell["evidence"]:
                ok, msg, ev = _evidence_ok(code, root, evidence_table)
                if not ok:
                    fails.append(f"P3 {tag}: {msg}")
                    continue
                kinds.append(ev["kind"])
                owners.append(ev.get("owner", "-"))
                variants.append(ev.get("variant"))
                #  P5 주인 일치
                if ev["kind"].startswith("own_") and ev.get("owner") not in (key, "-"):
                    fails.append(f"P5 {tag}: 근거 '{code}' 는 {ev.get('owner')} 의 자료다 "
                                 f"— 남의 기체 자료는 «대리»(D)로만 쓸 수 있다")
                #  P7 판 규칙
                for rule in FORBIDDEN_VARIANT_USE:
                    if (rule["airframe"] == key and grp in rule["groups"]
                            and ev.get("variant") == rule["variant"]):
                        fails.append(f"P7 {tag}: 판이 다른 근거 '{code}'({ev.get('variant')})를 썼다 "
                                     f"— {rule['why_ko']}")
            grade = cell.get("grade")
            #  빈칸 규칙
            if grade is None:
                if not cell.get("unknown_reason"):
                    fails.append(f"{tag}: 등급이 빈칸인데 `unknown_reason` 이 없다 "
                                 f"— «모른다»도 이유를 적어야 통과한다")
            else:
                if grade not in GRADE_RANK:
                    fails.append(f"{tag}: 모르는 등급 '{grade}'")
                else:
                    #  P4 등급 인플레
                    if not kinds:
                        fails.append(f"P4 {tag}: 등급 [{grade}] 인데 **살아 있는 근거가 0개**다")
                    else:
                        cap = max(GRADE_RANK[EVIDENCE_KIND_CAP[k]] for k in kinds)
                        if GRADE_RANK[grade] > cap:
                            best = [k for k in kinds
                                    if GRADE_RANK[EVIDENCE_KIND_CAP[k]] == cap][0]
                            capname = EVIDENCE_KIND_CAP[best]
                            fails.append(f"P4 {tag}: 등급 [{grade}] 인데 가장 센 근거가 "
                                         f"'{best}'(상한 [{capname}]) 다 — **등급 인플레**")
                    #  P6 [C]/[D] 선언
                    if grade == "C" and not cell.get("inferred_from"):
                        fails.append(f"P6 {tag}: [C](계열 유추)인데 `inferred_from` 이 없다")
                    if grade == "D" and not cell.get("proxy_of"):
                        fails.append(f"P6 {tag}: [D](대리)인데 `proxy_of` 가 없다")
                    if grade in ("A", "A-", "B", "B-") and cell.get("proxy_of"):
                        fails.append(f"P6 {tag}: 등급 [{grade}] 인데 `proxy_of` 가 붙어 있다 "
                                     f"— 대리는 [D] 다")
            #  P8 대체 선언
            mk_class = MODEL_KEY_CLASS.get(cell["model_key"])
            rc = cell.get("real_class")
            if rc not in (None, "unknown") and rc != mk_class and not cell.get("substitution"):
                fails.append(f"P8 {tag}: 실물 '{rc}' 인데 모델은 '{mk_class}'({cell['model_key']}) 다 "
                             f"— **대체 선언(substitution)** 이 없다")
            cells.append(dict(airframe=key, group=grp, model_key=cell["model_key"],
                              real_class=cell.get("real_class"), grade=grade,
                              evidence=cell["evidence"], evidence_kinds=kinds,
                              proxy_of=cell.get("proxy_of"),
                              inferred_from=cell.get("inferred_from"),
                              substitution=bool(cell.get("substitution")),
                              unknown_reason=cell.get("unknown_reason"),
                              why_ko=cell.get("why_ko")))

    #  등급 분포 — 인증서의 «못 하는 것» 절이 이 표에서 나온다
    dist = {}
    for c in cells:
        dist[str(c["grade"])] = dist.get(str(c["grade"]), 0) + 1
    return dict(ok=not fails, failures=fails, cells=cells, coverage=coverage,
                grade_distribution=dict(sorted(dist.items())))


# =========================================================================== #
#  11. 공용 «구조판» — 메쉬를 **재서** 찾고, 기체마다 선언을 요구한다
# =========================================================================== #
PLATE_FLATNESS = 0.12       # (최소변 / 최대변) 이 이보다 작으면 «얇은 판»


def check_shared_plate(meshes: dict | None = None, ledger: dict | None = None) -> dict:
    """금속 그룹 안에 **공용 비율로 심어진 얇은 판**이 있는 기체를 찾아, 그 기체 원장에
    `declared_shared_plate` 선언이 있는지 본다.

    왜 이 검사인가: 셸형 빌더의 공용 경로가 «마그네슘 합금 구조 프레임»이라는 이름으로
    얇은 상자를 **metal(battery) 그룹에** 넣는다. 근거는 «DJI Mavic 계열 AZ91 관행»
    하나인데, 그 관행이 성립하지 않는 기체에도 같은 판이 들어간다.
    ⚠ 이 검사는 **판을 빼지 않는다** — 기체마다 «이 판의 근거가 무엇인가»를 적게 만든다."""
    from drones import DRONES, build_drone
    import trimesh
    ledger = ledger if ledger is not None else PART_PROVENANCE
    if meshes is None:
        meshes = {k: build_drone(s) for k, s in DRONES.items()}
    fails, rows = [], []
    for key, mesh in meshes.items():
        V, F, G = _mesh_arrays(mesh)
        if "battery" not in set(G.tolist()):
            continue
        tm = trimesh.Trimesh(vertices=V, faces=F[G == "battery"], process=False)
        comps = tm.split(only_watertight=False, repair=False)
        metal_area = sum(_group_area_centroid(V, F, G, g)["area_m2"]
                         for g in ("battery", "motor") if (G == g).any())
        for c in comps:
            d = np.sort((c.bounds[1] - c.bounds[0]) * 1000)
            flat = float(d[0] / max(d[2], 1e-9))
            if flat >= PLATE_FLATNESS:
                continue
            share = float(c.area) / max(metal_area, 1e-12) * 100
            cell = (ledger.get(key) or {}).get("battery") or {}
            declared = bool(cell.get("declared_shared_plate"))
            rows.append(dict(airframe=key, size_mm=[round(float(x), 1) for x in d[::-1]],
                             flatness=round(flat, 3), area_cm2=round(float(c.area) * 1e4, 1),
                             pct_of_metal_area=round(share, 1), declared=declared,
                             grade=cell.get("shared_plate_grade", cell.get("grade"))))
            if not declared:
                fails.append(f"{key}: metal 그룹에 얇은 공용 판({d[2]:.0f}×{d[1]:.0f}×{d[0]:.1f} mm, "
                             f"금속 면적의 {share:.0f} %)이 있는데 원장에 선언이 없다")
    return dict(ok=not fails, failures=fails, plates=rows,
                what_ko="공용 경로가 metal(battery) 그룹에 넣는 얇은 «구조판». "
                        "기체마다 근거가 다르므로 칸마다 등급이 따로 붙어야 한다")


# =========================================================================== #
#  12. 회귀 봉인 — 지문 하나로 «조용히 바뀜» 을 막는다
# =========================================================================== #
def seal_fingerprint(materials_table: dict | None = None) -> dict:
    """재질·배정·원장의 **골든 지문**. 하나라도 바뀌면 값이 달라진다.
    ⭐ 인증서에 이 값을 박아 두면, 다음 사람이 재질을 조용히 고쳐도 게이트가 걸린다."""
    from drones import DRONE_GROUP_MAT
    if materials_table is None:
        from materials import MATERIALS as materials_table

    def h(obj) -> str:
        return hashlib.sha256(
            json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

    mat = {k: {f: v for f, v in s.items() if f != "note"} for k, s in materials_table.items()}
    led = {a: {g: dict(model_key=c["model_key"], grade=c.get("grade"),
                       evidence=sorted(c["evidence"]), real_class=c.get("real_class"))
               for g, c in b.items() if c} for a, b in PART_PROVENANCE.items()}
    return dict(materials=h(mat)[:16], group_mat=h(DRONE_GROUP_MAT)[:16],
                provenance=h(led)[:16], constant_sources=h(
                    {f"{k[0]}.{k[1]}": {a: b for a, b in v.items() if a != "why_ko"}
                     for k, v in CONSTANT_SOURCES.items()})[:16],
                evidence=h({k: dict(kind=v["kind"], path=v["path"], quote=v.get("quote"))
                            for k, v in EVIDENCE.items()})[:16])


def check_seal(expected: dict | None) -> dict:
    """지문 대조. `expected` 가 None 이면 «기준선 없음»으로 통과하되 그 사실을 적는다."""
    now = seal_fingerprint()
    if not expected:
        return dict(ok=True, failures=[], now=now,
                    note_ko="기준 지문이 없다 — 이번 값이 기준선이 된다")
    diff = {k: (expected.get(k), v) for k, v in now.items() if expected.get(k) != v}
    fails = [f"봉인 깨짐 — {k}: 기준 {a} → 지금 {b}" for k, (a, b) in diff.items()]
    return dict(ok=not fails, failures=fails, now=now, expected=expected, changed=sorted(diff))


# =========================================================================== #
#  13. 전체 검사 + 게이트
# =========================================================================== #
def check_all(verbose=True, expected_seal: dict | None = None) -> dict:
    from drones import DRONES, build_drone
    meshes = {k: build_drone(s) for k, s in DRONES.items()}
    out = {
        "group_table": check_group_table_closure(meshes),
        "fallback_sites": check_fallback_sites(),
        "constants": check_constants(),
        "provenance": check_provenance(meshes=meshes),
        "shared_plate": check_shared_plate(meshes),
        "seal": check_seal(expected_seal),
        "label_geometry": {},
    }
    for k, s in DRONES.items():
        out["label_geometry"][k] = check_label_geometry(s, mesh=meshes[k])
    out["ok"] = all(v["ok"] for kk, v in out.items() if kk != "label_geometry" and isinstance(v, dict)) \
        and all(r["ok"] for r in out["label_geometry"].values())
    if verbose:
        print(report(out))
    return out


def report(res: dict) -> str:
    L = []
    L.append("=" * 92)
    L.append("재질 배정 · 재질 상수 · 출처 등급 검사")
    L.append("=" * 92)
    for name, title in [("group_table", "그룹 라벨 ↔ 재질표 닫힘"),
                        ("fallback_sites", "조용한 폴백(선언 대조)"),
                        ("constants", "재질 상수 출처·문헌·ITU·표피깊이·두 엔진"),
                        ("provenance", "출처 등급 행렬"),
                        ("shared_plate", "공용 구조판 선언"),
                        ("seal", "회귀 봉인")]:
        r = res.get(name, {})
        L.append(f"{'✅' if r.get('ok') else '❌'} {title}")
        for f in r.get("failures", [])[:12]:
            L.append(f"     · {f}")
    lg = res.get("label_geometry", {})
    bad = {k: v for k, v in lg.items() if not v["ok"]}
    L.append(f"{'✅' if not bad else '❌'} 라벨↔형상 정합 ({len(lg)}기체)")
    for k, v in bad.items():
        for f in v["failures"]:
            L.append(f"     · {k}: {f}")
    p = res.get("provenance", {})
    if p:
        L.append("")
        L.append(f"등급 분포(기체 × 부품 {len(p['cells'])}칸): {p['grade_distribution']}")
    return "\n".join(L)


def assert_ok(expected_seal: dict | None = None):
    """빌드·게이트용 — 실패면 예외."""
    res = check_all(verbose=False, expected_seal=expected_seal)
    if not res["ok"]:
        msgs = []
        for k, v in res.items():
            if isinstance(v, dict) and v.get("failures"):
                msgs += [f"[{k}] {m}" for m in v["failures"]]
        for k, v in res.get("label_geometry", {}).items():
            msgs += [f"[label:{k}] {m}" for m in v["failures"]]
        raise AssertionError("재질·출처 검사 실패:\n  " + "\n  ".join(msgs))
    return True


if __name__ == "__main__":
    import sys
    res = check_all(verbose=True)
    if "--gate" in sys.argv:
        sys.exit(0 if res["ok"] else 1)
