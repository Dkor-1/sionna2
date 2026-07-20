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


def material_params(mat_key: str, fc: float = 3.5e9) -> tuple[float, float, float]:
    """재질 키 → (εr, σ[S/m], S).  **ITU 재질은 Sionna 에서 직접 읽는다**(주파수 반영)."""
    ck = (mat_key, round(float(fc)))
    if ck in _PARAM_CACHE:
        return _PARAM_CACHE[ck]
    spec = MATERIALS.get(mat_key)
    if spec is None:
        spec = MATERIALS["plastic"]                     # 알 수 없는 키 → 안전한 기본
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
        Γ = (1 − √εc) / (1 + √εc),   εc = εr − j·σ/(ω·ε0)"""
    er, sg, _ = material_params(mat_key, fc)
    eps_c = er - 1j * sg / (2 * np.pi * float(fc) * EPS0)
    return float(abs((1.0 - np.sqrt(eps_c)) / (1.0 + np.sqrt(eps_c))))


def gamma_po(mat_key: str, fc: float = 3.5e9) -> float:
    """**PO(rcs_po)가 쓰는 진폭 반사계수 |Γ|.**
    기본은 벌크 프레넬(gamma_bulk). 단, 벌크로 담을 수 없는 물리(박막 간섭·복합 조립품)가
    있는 재질은 MATERIALS[...]['gamma_po'] 의 실효값을 쓴다 — 근거는 각 note 에 있다.

    핵심: **어느 쪽이든 Sionna 와 같은 표에서 나온다.** 두 엔진이 조용히 어긋날 수 없다."""
    spec = MATERIALS.get(mat_key)
    if spec is not None and "gamma_po" in spec:
        return float(spec["gamma_po"])
    return gamma_bulk(mat_key, fc)


# 옛 이름 호환
gamma_normal = gamma_bulk


def make_material(mat_key: str, name: str, color=None) -> rt.RadioMaterial:
    """재질 키 → Sionna RadioMaterial 인스턴스 (전파 시뮬레이션용).
    color 는 렌더 표시용일 뿐 전파물성과 무관하다."""
    c = tuple(float(x) for x in color) if color is not None else None
    spec = MATERIALS.get(mat_key)
    if spec is None:                                    # 알 수 없는 키 → 회색 플라스틱
        spec = MATERIALS["plastic"]
        c = c or (0.6, 0.6, 0.6)
    if "itu" in spec:
        return rt.ITURadioMaterial(name=name, itu_type=spec["itu"],
                                   thickness=spec.get("thickness", 0.02), color=c)
    return rt.RadioMaterial(name=name,
                            relative_permittivity=spec["eps_r"],
                            conductivity=spec["sigma"],
                            scattering_coefficient=spec["S"],
                            color=c)


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
