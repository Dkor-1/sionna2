# -*- coding: utf-8 -*-
"""
materials.py — Sionna RT 전파재질(RadioMaterial) 사전
======================================================

Sionna 의 광선추적(ray tracing)에서 "재질"은 전파가 그 표면을 만났을 때
얼마나 **반사/투과/산란/흡수**되는지를 정합니다. 우리는 부위마다 알맞은
재질을 줍니다.

재질 키(mat_key) 요약
  metal           : 금속(완전도체에 가까움) — 차폐벽, 모터, 강철골조, RTK 안테나
  concrete_light  : 콘크리트(밝은 바닥 타일)
  concrete_dark   : 콘크리트(어두운 바닥 타일)
  absorber        : 전파흡수체 — 손실이 큰 유전체. 피라미드 기하구조와 합쳐져
                    여러 번 반사되며 에너지를 잡아먹어 '무반사'를 만든다.
  plastic         : 일반 플라스틱(드론 동체 셸)
  plastic_blue    : 파란 플라스틱(모서리 트림)
  carbon          : 탄소섬유(도전성↑) — S1000 암/프로펠러 등

주의: 'absorber' 의 유전율/도전율 값은 실제 특정 폼의 측정치가 아니라,
      "피라미드 + 손실재질 → 거의 반사 없음"을 만들기 위한 **모델 값**입니다.
      (나중에 RT 로 반사량을 직접 측정해 -30 dB 수준인지 검증할 수 있습니다.)

color 인자: 화면 렌더에서 보이는 색(RGB 0..1). matplotlib 도식의 색과 맞춰
            사진처럼 보이게 합니다. 전파 물성과는 무관(표시용).
"""
from __future__ import annotations

import sionna.rt as rt


# mat_key -> 만드는 방법. color 는 호출부에서 부위별로 따로 넘긴다(표시용).
def make_material(mat_key: str, name: str, color=None) -> rt.RadioMaterial:
    """재질 키와 표시색으로 Sionna RadioMaterial 인스턴스를 만든다."""
    c = tuple(float(x) for x in color) if color is not None else None

    if mat_key == "metal":
        return rt.ITURadioMaterial(name=name, itu_type="metal",
                                   thickness=0.02, color=c)
    if mat_key == "concrete_light" or mat_key == "concrete_dark":
        return rt.ITURadioMaterial(name=name, itu_type="concrete",
                                   thickness=0.30, color=c)
    if mat_key == "absorber":
        # 손실이 큰 유전체: 유전율 약간↑, 도전율 크게 → 침투한 전파를 감쇠.
        # 피라미드 기하와 합쳐져 순(net) 반사가 매우 작아진다.
        return rt.RadioMaterial(name=name, relative_permittivity=1.4,
                                conductivity=1.2, scattering_coefficient=0.35,
                                color=c)
    if mat_key == "plastic" or mat_key == "plastic_blue":
        return rt.RadioMaterial(name=name, relative_permittivity=2.7,
                                conductivity=0.02, scattering_coefficient=0.20,
                                color=c)
    if mat_key == "carbon":
        # 탄소섬유: 도전성이 높아 금속에 가깝게 반사. (이방성은 무시한 근사)
        return rt.RadioMaterial(name=name, relative_permittivity=5.0,
                                conductivity=3.0e3, scattering_coefficient=0.30,
                                color=c)
    # 알 수 없는 키 → 회색 플라스틱으로 안전 처리
    return rt.RadioMaterial(name=name, relative_permittivity=2.7,
                            conductivity=0.02, color=c or (0.6, 0.6, 0.6))
