# -*- coding: utf-8 -*-
"""
materials.py — **재질의 단일 진리원(single source of truth)**
==============================================================
이 파일이 정의한 재질을 **Sionna RT(전파 시뮬레이션)와 PO(RCS 계산)가 똑같이** 쓴다.

■ 왜 이렇게 바꿨나 (2026-07-14 감사)
  예전엔 재질 체계가 **두 개**였다:
    · Sionna RT  : materials.make_material() 의 RadioMaterial
    · PO(rcs_po) : drones.GROUP_GAMMA 라는 **손으로 적은 |Γ| 표**
  두 표가 조용히 어긋나 있었다 — 예: **camera 그룹**은 Sionna 에선 plastic(|Γ|=0.244),
  PO 에선 0.85 로 **10.9 dB** 차이. 같은 부품을 두 엔진이 다르게 보고 있었다.
  → 이제 **PO 의 |Γ| 는 여기 정의된 (εr, σ) 에서 프레넬로 유도**한다. 표를 손으로 안 적는다.

■ 원칙 — **ITU 가 있으면 ITU 를 쓴다**
  Sionna 는 ITU-R P.2040 재질(주파수 의존 εr·σ)을 내장한다. 우리가 숫자를 지어내는 대신
  Sionna 에게 물어본다(= scene.frequency 를 주고 값을 읽는다).
    metal, concrete → **ITU** (자동 주파수 보정)
  ITU 에 **없는** 것만 커스텀으로 둔다 — 그리고 근거를 적는다:
    plastic  : ITU 에 plastic 이 없다. 가장 가까운 ITU 는 plasterboard(εr=2.73, |Γ|=0.247)로
               우리 값(εr=2.7 → |Γ|=0.244)과 **사실상 같다**. 문헌값(ABS/PC εr≈2.6~3.0)을 쓴다.
    carbon   : 탄소섬유(도전성). ITU 에 없다. σ 를 크게 줘서 금속에 가깝게(|Γ|≈0.99). 이방성 무시.
    absorber : 전파흡수체. ITU 에 없다. **아래 주의 참고 — 실측치가 아니라 모델값.**

■ **모르는 재질 키는 예외**다 (조용한 폴백 금지, 2026-07-29)
  표에 없는 키는 예전에 조용히 plastic 으로 흘렀다 — `gamma_po('pec')` 가 아무 말 없이
  0.2437 을 돌려주는 식이다(의도한 PEC 1.0 대비 **−12.26 dB**). 이제 `_spec()` 이 즉시 예외를 던진다.
  **PEC 는 재질이 아니라 경계조건**이므로 'pec' 항목을 만들지 않는다 — group_mat 에 **float 1.0** 을 넣어라.

■ ITU 재질의 산란계수(S)는 전부 **0** 이다 (순수 정반사).
  확산 산란이 필요한 곳(흡수체·플라스틱·카본)은 커스텀 재질에서 S 를 준다.
  ※ 이것이 report6 [C] 의 "PEC 금속구에서 RT 가 경로를 아예 못 만든다"의 원인이다.

좌표/단위: 전부 SI. 주파수는 Hz.
"""
from __future__ import annotations

import numpy as np
import sionna.rt as rt

EPS0 = 8.8541878128e-12

# --------------------------------------------------------------------------- #
#  재질 표 — 여기가 유일한 정의. Sionna 도 PO 도 여기서 읽는다.
# --------------------------------------------------------------------------- #
#   itu      : Sionna 내장 ITU-R P.2040 재질 이름 (있으면 이것을 쓴다 → 주파수 자동 보정)
#   eps_r/σ  : ITU 가 없는 경우에만 직접 지정
#   S        : 산란계수(확산). ITU 재질은 0 고정.
#   gamma_po : **PO 전용 실효 |Γ| (선택)**. 벌크 프레넬로는 담을 수 없는 물리가 있을 때만 쓴다:
#              박막 간섭(얇은 셸), 복합 조립품(금속+유리+모터). 없으면 (εr,σ)에서 프레넬로 유도.
#              ⚠ 이 값이 있으면 **의도적으로** 벌크 프레넬과 다르다 — 반드시 note 에 근거를 적을 것.
#   note     : 근거/주의
MATERIALS: dict[str, dict] = {
    "metal": dict(
        itu="metal", thickness=0.02, S=0.0,
        note="ITU 'metal' — PEC 근사(σ=1e7 S/m). 모터·배터리·차폐벽·골조."),
    "camera_assembly": dict(
        itu="metal", thickness=0.02, S=0.0, gamma_po=0.85,
        note="짐벌 카메라 = **금속 하우징 + 유리 렌즈 + 짐벌 모터**. "
             "전파 반사면은 금속 하우징이 지배 → Sionna 는 ITU metal. "
             "PO 는 유리/틈새를 반영한 실효 0.85. "
             "⚠ 2026-07-14 이전에는 Sionna 가 이걸 **plastic**(|Γ|=0.244)으로 보고 있었다 "
             "— PO(0.85)와 **10.9 dB** 어긋난 버그. 이 항목이 그 버그를 없앤다."),
    "pcb": dict(
        itu="metal", thickness=0.002, S=0.0, gamma_po=0.80,
        note="ESC/메인보드 = FR-4 유전체 + **구리 그라운드플레인**. 반사면은 구리면이 지배 → ITU metal. "
             "PO 는 부분 개구(커넥터·비도체 영역)를 반영한 실효 0.80."),
    "concrete_light": dict(
        itu="concrete", thickness=0.30, S=0.0,
        note="ITU 'concrete' — 챔버 바닥 타일(밝은). **반사성** → semi-anechoic 의 원인."),
    "concrete_dark": dict(
        itu="concrete", thickness=0.30, S=0.0,
        note="ITU 'concrete' — 챔버 바닥 타일(어두운). 전파물성은 light 와 동일."),
    "plastic": dict(
        eps_r=2.7, sigma=0.02, S=0.20, gamma_po=0.28,
        note="드론 셸(ABS/PC). ITU 에 plastic 없음 — 문헌값 εr≈2.6~3.0. "
             "가장 가까운 ITU plasterboard(2.73)와 벌크 |Γ| 가 0.247 vs 0.244 로 사실상 동일. "
             "PO 실효 0.28: 셸이 1~3 mm **박막**이라 앞뒷면 간섭으로 |Γ| 가 0.1~0.45 를 오간다 "
             "(벌크 반무한 프레넬 0.244 는 그 하한 근처) → 대표값 0.28."),
    "plastic_blue": dict(
        eps_r=2.7, sigma=0.02, S=0.20, gamma_po=0.28,
        note="파란 모서리 트림 — 전파물성은 plastic 과 동일(색만 다름)."),
    "prop_plastic": dict(
        eps_r=2.7, sigma=0.02, S=0.20, gamma_po=0.25,
        note="프로펠러 — **재질은 plastic 과 동일**(같은 ABS/PC·εr 2.7 → 렌더 색도 회색 동일). "
             "날개가 셸(1~3 mm)보다 더 얇아 실효 |Γ| 가 낮다는 **방향**만 반영해 0.25 채택. "
             "⚠ **정밀 두께 모델이 아니다** — DJI 가 부품 두께를 공개하지 않고, 박막 |Γ| 는 두께·각도·"
             "주파수에 따라 0.1~0.45 로 출렁인다(모든 드론 프롭에 같은 0.25 를 쓴다). "
             "즉 재질 클래스별 **대표 실효값**이며, 이 정도 차이(셸 0.28↔프롭 0.25)는 우리 RCS 불확실도"
             "(±2~3 dB)·프롭 면적 비중 때문에 총 RCS 에 0.03 dB 미만이다. **색=재질(정밀), |Γ|=대표값**."),
    "carbon": dict(
        eps_r=5.0, sigma=3.0e3, S=0.30, gamma_po=0.90,
        note="탄소섬유(도전성) — ITU 에 없음. 벌크 |Γ|≈0.99(금속 근접). "
             "PO 실효 0.90: 직조 섬유 사이 유전체 개구·이방성을 반영."),
    "absorber": dict(
        eps_r=1.4, sigma=1.2, S=0.35,
        note="⚠ **실측치 아님 — 모델값**. 이 재질의 **평평한 단일면** 수직입사 반사는 |Γ|=0.549 "
             "(≈−5.2 dB)로 전혀 낮지 않다. 무반사(−25~−30 dB)는 **피라미드 골짜기 다중반사**"
             "(4~5회 × 회당 −5.2 dB)로 달성되는 **기하 효과**이지 재질 자체의 성질이 아니다. "
             "그리고 그 −25 dB 는 **설계 목표**이지 이 씬에서 측정한 값이 아니다."),
}

# ITU 재질값은 주파수 의존 → Sionna 에게 물어보고 캐시한다 (우리가 공식을 다시 짜지 않는다).
_PROBE_SCENE = None
_PARAM_CACHE: dict = {}


def _probe_scene(fc: float):
    global _PROBE_SCENE
    if _PROBE_SCENE is None:
        _PROBE_SCENE = rt.load_scene()
    _PROBE_SCENE.frequency = float(fc)
    return _PROBE_SCENE


def _spec(mat_key: str) -> dict:
    """재질 키 → MATERIALS 항목. **모르는 키는 조용히 넘어가지 않는다 — 즉시 예외.**

    ■ 왜 예외인가 (2026-07-29)
      예전엔 표에 없는 키가 조용히 **plastic 기본값**으로 흘렀다. 그래서
      `gamma_po('pec')` 가 경고 한 줄 없이 **0.2437**(plastic 벌크)을 돌려줬다 —
      의도한 PEC(|Γ|=1.0)와 **−12.26 dB** 어긋난 값이 그대로 σ 에 들어간다.
      (참고: `gamma_po('metal')`=0.99980. 즉 'pec' 오타는 '거의 맞는 값'이 아니라 완전히 다른 값이다.)
      이 저장소는 조용한 폴백에 반복해서 물렸다 → **|Γ|·(εr,σ) 를 내는 경로는 전부 여기서 막는다.**

    ■ 왜 MATERIALS 에 'pec' 항목을 만들지 않았나
      PEC 는 재질이 아니라 **경계조건**이다. 게다가 MATERIALS 를 **순회해서 리포트 원장/표**를
      만드는 곳이 여럿이라(viz_report1.materials 원장, viz_report2.fig_materials,
      viz_verify_sbr 의 재질표) 항목을 하나 늘리면 리포트 표가 같이 바뀐다.
      → PEC 가 필요하면 재질 문자열이 아니라 **float 1.0** 을 group_mat 에 직접 넣을 것
        (rcs_sbr/rcs_po 는 float 를 |Γ| 로 그대로 쓴다 — 예: rcs_po.py `{g: 1.0 for g in ...}`).
    """
    spec = MATERIALS.get(mat_key)
    if spec is None:
        raise KeyError(
            f"materials: 모르는 재질 키 {mat_key!r}. 아는 키 = {sorted(MATERIALS)}. "
            f"'pec' 는 재질 이름이 아니다 — 완전도체를 원하면 group_mat 에 **float 1.0**(=|Γ|)을 "
            f"넣을 것. (예전엔 이 자리에서 조용히 plastic 으로 흘러 |Γ|=0.2437, 즉 −12.26 dB 를 줬다.)")
    return spec


def material_params(mat_key: str, fc: float = 3.5e9) -> tuple[float, float, float]:
    """재질 키 → (εr, σ[S/m], S).  **ITU 재질은 Sionna 에서 직접 읽는다**(주파수 반영).
    ⚠ 모르는 키는 _spec() 이 예외를 던진다(옛 plastic 조용한 폴백 제거)."""
    ck = (mat_key, round(float(fc)))
    if ck in _PARAM_CACHE:
        return _PARAM_CACHE[ck]
    spec = _spec(mat_key)
    if "itu" in spec:
        m = rt.ITURadioMaterial(name=f"_probe_{mat_key}_{ck[1]}", itu_type=spec["itu"],
                                thickness=spec.get("thickness", 0.02))
        m.scene = _probe_scene(fc)
        er = float(np.asarray(m.relative_permittivity).reshape(-1)[0])
        sg = float(np.asarray(m.conductivity).reshape(-1)[0])
    else:
        er, sg = float(spec["eps_r"]), float(spec["sigma"])
    out = (er, sg, float(spec["S"]))
    _PARAM_CACHE[ck] = out
    return out


def gamma_bulk(mat_key: str, fc: float = 3.5e9) -> float:
    """**벌크(반무한) 수직입사 프레넬 |Γ|** — Sionna 가 쓰는 (εr, σ) 에서 직접 유도.
        Γ = (1 − √εc) / (1 + √εc),   εc = εr − j·σ/(ω·ε0)
    ⚠ 모르는 키는 예외(_spec) — 조용히 plastic 으로 흐르지 않는다."""
    er, sg, _ = material_params(mat_key, fc)
    eps_c = er - 1j * sg / (2 * np.pi * float(fc) * EPS0)
    return float(abs((1.0 - np.sqrt(eps_c)) / (1.0 + np.sqrt(eps_c))))


def gamma_po(mat_key: str, fc: float = 3.5e9) -> float:
    """**PO(rcs_po)가 쓰는 진폭 반사계수 |Γ|.**
    기본은 벌크 프레넬(gamma_bulk). 단, 벌크로 담을 수 없는 물리(박막 간섭·복합 조립품)가
    있는 재질은 MATERIALS[...]['gamma_po'] 의 실효값을 쓴다 — 근거는 각 note 에 있다.

    핵심: **어느 쪽이든 Sionna 와 같은 표에서 나온다.** 두 엔진이 조용히 어긋날 수 없다.

    ⚠ **모르는 키는 예외**다(_spec 참조). 특히 `gamma_po('pec')` 는 이제 죽는다 —
      예전엔 0.2437 을 조용히 돌려줬다(의도 1.0 대비 −12.26 dB). PEC 는 float 1.0 로 넘길 것."""
    spec = _spec(mat_key)
    if "gamma_po" in spec:
        return float(spec["gamma_po"])
    return gamma_bulk(mat_key, fc)


# 옛 이름 호환
gamma_normal = gamma_bulk


# --------------------------------------------------------------------------- #
#  ⭐ 셸 두께 손잡이 (2026-08-15 신설) — 비-ITU 재질이 Sionna 에 두께를 넘길 수 있게
# --------------------------------------------------------------------------- #
#  ■ 무엇이 결함이었나
#    아래 `make_material()` 의 **비-ITU 분기**가 `thickness` 를 안 넘겼다. 그래서 Sionna 의
#    상수 기본값 **0.1 m(=10 cm)** 이 쓰였다
#    (`sionna/rt/constants.py:80  DEFAULT_THICKNESS = 0.1`,
#     `sionna/rt/radio_materials/radio_material.py:94·134`).
#    드론 셸은 실제로 **1~3 mm** 다 — 즉 지금까지 모든 PathSolver 팔이 «10 cm 플라스틱 판»
#    위에서 반사·굴절을 계산했다. ITU 분기는 원래 두께를 넘기고 있었으므로
#    금속·콘크리트(metal·camera_assembly·pcb·concrete_*)는 해당 없다.
#
#  ■ 두께가 바꾸는 것 — 굴절만이 아니다
#    Sionna 는 «지정 두께의 단층 슬래브» 로 **반사 R 과 투과 T 를 같이** 낸다
#    (ITU-R P.2040 식 43·44, `sionna/rt/utils/electromagnetics.py:60-112`).
#    CPU 실측(`benchmark/slab_thickness_check.py` · `outputs/slab_thickness_check.json`):
#      플라스틱 셸 정반사 |R| — 100 mm −13.38 dB · 3 mm −14.97 · 2 mm −18.28 · 1 mm −24.16 dB
#      즉 2 mm 로 고치면 **−4.90 dB**(수직) · **−5.82 dB**(각도평균) 움직인다.
#    탄소섬유는 표피깊이가 0.155 mm 라 1 mm 도 이미 여러 표피깊이 — 두께를 **안 탄다**
#    (0.5 mm↔100 mm 차이 0.00 dB). 그래서 손잡이를 carbon 에는 안 건다.
#
#  ■ ⚠**두께에는 출처가 없다** (docs/RETRACTION_LOG.md A3)
#    A3 이 «진짜 출처 없는 건 셸 두께» 라고 적어 뒀다 — DJI 는 부품 두께를 공개하지 않는다.
#    그러므로 1·2·3 mm 는 측정값이 아니라 **민감도 축**이고, 결과는 «두께 d 를 가정하면»
#    이라는 조건문으로만 인용한다. 1↔3 mm 사이에서만 |R| 이 **9.19 dB** 갈리므로
#    단일값을 못 박는 것은 그 자체로 지어내기다.
#
#  ■ 기본은 **안 건드린다** — 비트동일
#    아무도 손잡이를 안 쓰면 예전과 **똑같이** thickness 를 안 넘긴다(=Sionna 기본 0.1 m).
#    그래야 옛 샤드·리포트 수치가 그대로 재현된다. 고친 값으로 돌리려면 **명시적으로**
#    켜고, 그 판은 파일명 꼬리표(_shell2mm 등)로 옛 샤드와 갈라 놓는다.
#
#  ■ 우리 커널(rcs_sbr)에는 두께 개념이 없다
#    우리 셸은 |Γ|=gamma_po('plastic')=0.28 과 τ=1−|Γ|²=−0.71 dB 뿐이다. 그러니 이 손잡이는
#    **Sionna 팔 전용**이다. (참고로 τ 는 1~3 mm 슬래브의 두 번 통과 손실 −0.10~−0.47 dB 와
#     0.24~0.61 dB 안에서 만난다 — 투과 축은 애초에 결함이 아니었다.)
THICKNESS_KNOBS: dict[str, tuple[str, ...]] = {
    "shell": ("plastic", "plastic_blue"),   # 동체·캐노피·착륙장치·식별색
    "prop":  ("prop_plastic",),             # 프로펠러 — 셸보다 얇다(표적 축을 가르는 손잡이)
}
_THICKNESS_M: dict[str, float] = {}         # 재질키 → 두께[m]. **비어 있으면 예전 그대로.**


def set_thickness_mm(shell: float | None = None, prop: float | None = None,
                     **extra: float) -> dict[str, float]:
    """⭐비-ITU 재질의 두께를 **밀리미터**로 정한다. 안 부르면 아무 일도 안 일어난다.

        set_thickness_mm(shell=2.0)          # plastic·plastic_blue → 2 mm
        set_thickness_mm(shell=2.0, prop=1.0)
        set_thickness_mm()                   # 전부 되돌린다(=Sionna 기본 0.1 m)

    `extra` 로 재질 키를 직접 줄 수도 있다(예: `carbon=1.0`) — 다만 carbon 은 두께를
    안 타므로 보통 필요 없다. 돌려주는 값은 «재질키 → 두께[m]» 현재 표다.
    ⚠ ITU 재질(metal·concrete·camera_assembly·pcb)은 MATERIALS 의 자기 두께를 쓰므로
      여기서 안 건드린다 — 건드리려 하면 예외다."""
    _THICKNESS_M.clear()
    for knob, val in (("shell", shell), ("prop", prop)):
        if val is None:
            continue
        if float(val) <= 0:
            raise ValueError(f"set_thickness_mm({knob}={val}): 두께는 양수여야 한다")
        for k in THICKNESS_KNOBS[knob]:
            _THICKNESS_M[k] = float(val) * 1e-3
    for k, val in extra.items():
        spec = _spec(k)                                  # 모르는 키는 여기서 죽는다
        if "itu" in spec:
            raise ValueError(f"set_thickness_mm: {k!r} 는 ITU 재질이다 — 두께는 "
                             f"MATERIALS[{k!r}]['thickness'] 에 있다. 손잡이는 비-ITU 전용.")
        if float(val) <= 0:
            raise ValueError(f"set_thickness_mm({k}={val}): 두께는 양수여야 한다")
        _THICKNESS_M[k] = float(val) * 1e-3
    return dict(_THICKNESS_M)


def thickness_state() -> dict[str, float]:
    """지금 걸린 두께 표(재질키 → m). 비어 있으면 «예전 그대로»(Sionna 기본 0.1 m)."""
    return dict(_THICKNESS_M)


#  ⭐ 2026-08-16 — `make_material()` 의 **조용한 폴백** 기록. 아래 설명 참조.
UNKNOWN_KEY_FALLBACKS: list[dict] = []


def make_material(mat_key: str, name: str, color=None, strict: bool = False) -> rt.RadioMaterial:
    """재질 키 → Sionna RadioMaterial 인스턴스 (전파 시뮬레이션용).
    color 는 렌더 표시용일 뿐 전파물성과 무관하다.

    ⭐두께: `set_thickness_mm()` 으로 켠 재질만 `thickness` 를 넘긴다. 안 켜면 **인자를
      아예 안 넘겨** 예전 호출과 비트동일하다(=Sionna DEFAULT_THICKNESS 0.1 m).

    ⭐ **모르는 키**(2026-08-16, 감사 라운드에서 실측):
      이 파일 머리말은 «|Γ|·(εr,σ) 를 내는 경로는 전부 여기서 막는다» 고 적는데,
      정작 이 함수만 예외였다 — `gamma_po('nylon')` 은 KeyError 로 죽지만
      `make_material('nylon', …)` 은 **경고 한 줄 없이 plastic(εr 2.7, σ 0.02)** 을 돌려줬다.
      즉 Sionna 쪽만 조용히 플라스틱으로 흐를 수 있었다.
      · `strict=False`(기본) — **숫자는 예전과 완전히 같다.** 다만 이제 조용하지 않다:
        경고를 띄우고 `UNKNOWN_KEY_FALLBACKS` 에 기록을 남긴다.
      · `strict=True`  — `gamma_po` 와 **같은 규약**으로 즉시 예외를 던진다.
      (현재 저장소에는 모르는 키를 넘기는 호출부가 **0 건**이다 — 전수 확인. 그래서 기본을
       바꾸지 않아도 아무것도 안 잃고, 새로 생기는 오타는 이제 보인다.)"""
    c = tuple(float(x) for x in color) if color is not None else None
    spec = MATERIALS.get(mat_key)
    if spec is None:                                    # 알 수 없는 키 → 회색 플라스틱
        if strict:
            _spec(mat_key)                              # gamma_po 와 같은 예외 문면
        import warnings
        rec = dict(mat_key=str(mat_key), name=str(name), fell_back_to="plastic")
        UNKNOWN_KEY_FALLBACKS.append(rec)
        warnings.warn(
            f"materials.make_material: 모르는 재질 키 {mat_key!r}(name={name!r}) → "
            f"**plastic 으로 조용히 흐른다**(εr 2.7, σ 0.02, |Γ|=0.244). "
            f"의도한 값이 아니면 Sionna 쪽만 틀린 재질로 돈다 — PO 쪽 gamma_po({mat_key!r}) 는 "
            f"예외를 던진다. 아는 키 = {sorted(MATERIALS)}. "
            f"완전도체를 원하면 재질 문자열이 아니라 float 1.0 을 쓸 것.",
            RuntimeWarning, stacklevel=2)
        spec = MATERIALS["plastic"]
        c = c or (0.6, 0.6, 0.6)
    if "itu" in spec:
        return rt.ITURadioMaterial(name=name, itu_type=spec["itu"],
                                   thickness=spec.get("thickness", 0.02), color=c)
    kw = {}
    if mat_key in _THICKNESS_M:                          # ⭐켰을 때만 넘긴다
        kw["thickness"] = _THICKNESS_M[mat_key]
    return rt.RadioMaterial(name=name,
                            relative_permittivity=spec["eps_r"],
                            conductivity=spec["sigma"],
                            scattering_coefficient=spec["S"],
                            color=c, **kw)


def table(fc: float = 3.5e9) -> str:
    """진단용 표 — 두 엔진이 같은 재질을 보는지, PO 실효값이 벌크와 왜 다른지 한눈에."""
    lines = [f"{'재질':16s} {'Sionna':8s} {'eps_r':>7} {'sigma[S/m]':>11} {'S':>5} "
             f"{'|Γ|벌크':>8} {'|Γ|PO':>7}  실효값 사유"]
    for k in MATERIALS:
        er, sg, S = material_params(k, fc)
        src = "ITU" if "itu" in MATERIALS[k] else "custom"
        gb, gp = gamma_bulk(k, fc), gamma_po(k, fc)
        why = "" if abs(gb - gp) < 1e-9 else f"실효({20*np.log10(gp/(gb+1e-12)):+.1f} dB) — note 참조"
        lines.append(f"{k:16s} {src:8s} {er:7.2f} {sg:11.4g} {S:5.2f} {gb:8.3f} {gp:7.2f}  {why}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("재질 표 @ 3.5 GHz — **Sionna(전파)와 PO(RCS)가 같은 표에서 읽는다**\n")
    print(table(3.5e9))
    print("\n※ ITU 재질의 εr·σ 는 Sionna 에게 물어본 값이다(주파수 자동 보정). 우리가 공식을 다시 짜지 않는다.")
    print("※ ITU 재질은 S=0 (순수 정반사). 확산이 필요한 흡수체·플라스틱·카본만 커스텀.")


# --------------------------------------------------------------------------- #
#  ⭐ 각도의존 반사계수 (2026-08-07 신설)
# --------------------------------------------------------------------------- #
#  왜 필요한가 — 측정된 결함
#    `gamma_po()` 는 **수직입사 값 하나**를 돌려주고, PO·SBR 커널이 그 값을 모든 입사각에
#    그대로 쓴다. 실제 프레넬 반사계수는 각도에 따라 커진다. 3.5 GHz 벌크값 기준 실측:
#
#        재질          30°     45°     60°     75°     85°
#        플라스틱     +1.18   +2.63   +4.59   **+6.96**  +8.67 dB
#        탄소섬유     +0.22   +0.48   +0.83   +1.22    +1.51 dB
#        금속          0       0       0       0        0    dB
#
#    ⭐ **프로펠러가 그 플라스틱**이고, 도는 날개는 대부분의 시간을 큰 입사각에서 보낸다.
#      즉 마이크로도플러가 이 오차를 정면으로 안고 있었다.
#    (선행 확인: 선배 홍지혁의 PO 커널 `fresnel_te_vec(cos_i, er, sigma, f_c)` 는 각도를 받는다.
#     우리 `gamma_po(mat_key, fc)` 에는 각도 인자 자체가 없었다.)
#
#  설계 — 보정값을 살리고 각도 모양만 얹는다
#    우리 재질 여섯은 벌크 프레넬이 아니라 **수직입사 실효값**을 쓴다(박막 간섭·복합 조립품).
#    그 보정을 버리면 안 되므로, 벌크의 **상대 각도 모양**만 곱한다:
#
#        |Γ(θ)| = |Γ_보정| · |Γ_벌크(θ)| / |Γ_벌크(0)|
#
#    θ=0 에서 예전 값과 **정확히 같다** — 기존 앵커·리포트가 안 흔들린다.
#
#  ⚠ 선언하는 근사 셋
#    (1) 얇은 판(프로펠러 날, 두께 ≪ λ)의 각도 거동은 벌크 프레넬과 다르다. 여기서는
#        벌크 모양을 빌려 쓴다 — 방향은 맞고 크기는 근사다.
#    (2) 우리 커널은 스칼라(|Γ|)라 편파를 안 쓴다. TE 와 TM 은 큰 각도에서 크게 갈리므로
#        **전력 평균** √((|Γ_TE|²+|Γ_TM|²)/2) 를 쓴다. TE 만 쓰면 과대평가된다.
#    (3) 도체(σ 큰 것)는 각도에 거의 무관하다 — 위 표의 금속 행이 그 확인이다.
def _fresnel_te_tm(cos_i, er, sigma, fc):
    """(Γ_TE, Γ_TM) — 복소 유전율 기준 프레넬 반사계수."""
    import numpy as _np
    w = 2 * _np.pi * float(fc)
    erc = er - 1j * sigma / (w * EPS0)
    ci = _np.clip(_np.asarray(cos_i, float), 0.0, 1.0)
    sq = _np.sqrt(erc - (1.0 - ci ** 2))
    te = (ci - sq) / (ci + sq)
    tm = (erc * ci - sq) / (erc * ci + sq)
    return te, tm


def gamma_shape(mat_key: str, fc: float, cos_i):
    """수직입사 대비 **상대** 각도 모양 |Γ(θ)|/|Γ(0)|. 배열을 받고 배열을 돌려준다."""
    import numpy as _np
    er, sg, _ = material_params(mat_key, fc)
    te, tm = _fresnel_te_tm(cos_i, er, sg, fc)
    g = _np.sqrt((_np.abs(te) ** 2 + _np.abs(tm) ** 2) / 2.0)      # 전력 평균
    te0, tm0 = _fresnel_te_tm(1.0, er, sg, fc)
    g0 = _np.sqrt((_np.abs(te0) ** 2 + _np.abs(tm0) ** 2) / 2.0)
    return g / max(float(g0), 1e-12)


def gamma_po_angle(mat_key: str, fc: float = 3.5e9, cos_i=1.0):
    """⭐ **각도의존 |Γ|** — `gamma_po` 의 각도 있는 판.

        |Γ(θ)| = gamma_po(재질) · gamma_shape(재질, θ)

    cos_i=1 이면 `gamma_po()` 와 **정확히 같다**(비트 동일). 배열도 받는다."""
    import numpy as _np
    return float(gamma_po(mat_key, fc)) * _np.asarray(gamma_shape(mat_key, fc, cos_i))
