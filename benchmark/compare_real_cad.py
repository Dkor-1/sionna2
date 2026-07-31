# -*- coding: utf-8 -*-
"""
compare_real_cad.py — **우리 파라메트릭 방법 vs 실물 3D CAD** (report1 §2.5)
==============================================================================
답할 질문: *"스펙시트 숫자로 코드가 만든 메쉬가, 실물 CAD 와 얼마나 다른가? σ 로 몇 dB 인가?"*

■ 왜 DJI 로 못 하나 (정직하게)
  **DJI 는 공식 CAD 를 공개하지 않는다.** 인터넷의 DJI 3D 모델들은
    · **껍데기만** — 배터리·PCB·모터 같은 **내부 금속 산란체가 없다**.
      그런데 드론 RCS 는 **내부 금속이 지배한다**(플라스틱 셸은 |Γ|≈0.28 로 반투명).
    · 치수 검증 안 됨 (예쁘게만 만든 것)
    · watertight/법선 보장 없음 → 조명판정(n̂·û>0)이 오염됨
    · 라이선스 제약
  → RCS 에 쓸 수 없다. 그래서 **CAD 가 공개된 실물 드론**으로 **우리 방법 자체**를 검증한다.

■ 비교 대상 (assets/meshes/reference/SOURCES.md — 전부 허용적 라이선스)
  [A] **Yuneec Typhoon H480** (Apache-2.0, ethz-asl/rotors_simulator)
      실제 상용 헥사콥터의 CAD. 동체 + 다리 + 프롭 6 + CGO3 짐벌.
      → 같은 기체를 **우리 방식으로 스펙시트에서 생성**하고 σ 를 비교한다.
      ⭐ 2026-07-30: 이 기체는 이제 **정식 표적**(`DRONES['typhoonh480']`)이다. 그래서 비교는
        "외부 기체로 방법을 시험" 이 아니라 **우리가 실제로 쏘는 표적 메쉬 자체의 검증**이 됐다.
        아래 `TYPHOON` 은 레지스트리에서 파생한다 — 스펙을 두 벌 적지 않는다.
  [B] **Holybro 1345 프로펠러** (BSD-3, PX4/PX4-gazebo-models)
      실제 13.45인치 프롭의 CAD.
      → 같은 지름의 **우리 NACA-4 익형 프롭**과 비교. 마이크로도플러에 직결된다.

■ 공정성 규칙 (중요)
  실물 CAD 는 껍데기뿐이므로 **양쪽을 전부 PEC(금속)로 두고** 껍데기 형상만 비교한다.
  그러면 남는 차이는 **순수하게 기하(실루엣) 차이**다. 그게 우리가 알고 싶은 것이다.

실행:  python benchmark/compare_real_cad.py     (GPU — gpu.py 가 자동 선택)
출력:  outputs/real_cad_compare.json
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.abspath(os.path.join(_HERE, "..", "src")), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                    # noqa: E402
import trimesh                                        # noqa: E402
from dataclasses import replace                       # noqa: E402

from mesh_compare import (load_reference, typhoon_h480_real, compare)   # noqa: E402
from drones import DRONES                             # noqa: E402
import drone_cad                                      # noqa: E402
import cadkit                                         # noqa: E402

OUT = os.path.abspath(os.path.join(_HERE, "..", "outputs", "real_cad_compare.json"))


# --------------------------------------------------------------------------- #
#  Typhoon H480 을 **우리 방식으로** (스펙시트 → 파라메트릭)
# --------------------------------------------------------------------------- #
#  ⭐ 2026-07-30 (Phase 3): 여기에 **손으로 적은 두 번째 Typhoon 스펙**이 있었다. 이제
#     `typhoonh480` 이 정식 표적(`DRONES`)이라 같은 기체의 제원이 두 벌 존재했고, 그건
#     저장소가 이미 값을 치른 실패 유형이다(제원 3갈래 분산). → **레지스트리에서 파생**한다.
#  ⚠ 옛 리터럴은 값 자체가 틀려 있었다 — diag **520** · 프롭 **241** · TOW **1700 g** 은
#     Typhoon **H Plus**(다른 변종)의 수치다. `docs/RESUME_0729.md` §5 가 변종을 5중으로
#     확정했고(상류 디렉터리명·cgo3_* 메쉬명·측정 대각 485.4·bbox 455×520·프롭 230),
#     이 저장소의 실물 CAD 는 **H480**이다. 즉 여태 §2.5 는 서로 다른 변종을 견주고 있었다.
#  ⚠ 옛 리터럴은 `key='typhoon_h480_ours'` 여서, Phase 1 이 `build_frame_cad` 에 넣은
#     "모르는 기종 키" 가드에 걸려 **이 스크립트 전체가 NotImplementedError 로 죽고 있었다**
#     (재생성 파이프라인 stage 1). 레지스트리 key 를 쓰면 CGO3+ 짐벌 분기가 정상 적용된다.
#  · 비교 목적상 딱 하나만 덮는다: `envelope_mm=None` — 실물 CAD 와 **같은 조건**으로 견주려면
#    공식 외형 강제 정합을 끈다(정본 typhoonh480 은 높이만 강제한다).
TYPHOON = replace(
    DRONES["typhoonh480"],
    name="Yuneec Typhoon H480 (우리 파라메트릭)",
    envelope_mm=None,
)


def ours_typhoon() -> trimesh.Trimesh:
    """우리 CAD 툴킷으로 Typhoon H480 을 만든다 (실물 CAD 를 **안 보고**, 스펙만으로)."""
    A = drone_cad.build_frame_cad(TYPHOON)
    P = drone_cad.build_propeller_cad(TYPHOON)
    from drones import rotor_layout
    parts = []
    for g, ms in A.parts.items():
        parts += ms
    prop_ms = [m for ms in P.parts.values() for m in ms]
    for rot in rotor_layout(TYPHOON):
        cx, cy, cz = rot["center"]
        for pm in prop_ms:
            q = pm.copy()
            q.apply_transform(trimesh.transformations.rotation_matrix(
                np.radians(rot["base_ang"]), [0, 0, 1]))
            q.apply_translation([cx, cy, cz])
            parts.append(q)
    m = trimesh.util.concatenate(parts)
    m.apply_translation(-m.bounds.mean(axis=0))
    return m


def ours_body_only() -> trimesh.Trimesh:
    """우리 방식으로 만든 Typhoon **동체(프레임)만** — 실물 main_body STL 과 같은 부위.
    실물 동체 STL 의 바운딩박스에 맞춰 외형만 정합한다(프롭·다리 제외)."""
    real = load_reference("main_body_remeshed_v3.stl")
    e = (real.bounds[1] - real.bounds[0]) * 1000.0                 # mm
    spec = replace(TYPHOON, envelope_mm=(float(e[0]), float(e[1]), float(e[2])))
    #  ⭐ 옛 코드는 여기서 `drones._FIT_CACHE.pop(spec.key)` 를 손수 불렀다 — 캐시가 `spec.key`
    #     하나로만 색인돼 있어서, 같은 key 의 **다른 외형** 변종이 앞서 계산된 배율을 조용히
    #     물려받았기 때문이다. 이제 캐시 키가 spec 전체(`drones._fit_cache_key`)라 불필요하다.
    A = drone_cad.build_frame_cad(spec)
    # 공식 외형 정합(우리 규약)과 동일하게 실물 바운딩박스에 맞춘다
    V = np.vstack([np.asarray(m.vertices) for ms in A.parts.values() for m in ms])
    ext = (V.max(0) - V.min(0)) * 1000.0
    A.scaled(*[float(t) / float(x) if x > 1e-9 else 1.0 for t, x in zip(e, ext)])
    ms = [m for msl in A.parts.values() for m in msl]
    m = trimesh.util.concatenate(ms)
    m.apply_translation(-m.bounds.mean(axis=0))
    return m


def ours_prop(dia_m: float) -> trimesh.Trimesh:
    """우리 NACA-4 익형 프롭 1장 (허브 포함), 지름을 실물에 맞춘다."""
    spec = replace(TYPHOON, prop_dia_mm=dia_m * 1000.0, prop_blades=2)
    A = drone_cad.build_propeller_cad(spec, n_sec=26)
    ms = [m for msl in A.parts.values() for m in msl]
    m = trimesh.util.concatenate(ms)
    m.apply_translation(-m.bounds.mean(axis=0))
    return m


def main():
    fc = 3.5e9
    res = {}

    print("=" * 92)
    print("[A] Yuneec Typhoon H480 **동체** — 실물 CAD vs 우리 파라메트릭")
    print("    (조립 전체가 아니라 **동체만** 비교한다 — 로터 배치는 우리 추측이라 비교를 오염시킨다)")
    print("=" * 92)
    real = load_reference("main_body_remeshed_v3.stl")
    ours = ours_body_only()
    br = (real.bounds[1] - real.bounds[0]) * 1000
    bo = (ours.bounds[1] - ours.bounds[0]) * 1000
    print(f"  실물 CAD  : {len(real.faces):>7,d}면  {br[0]:6.1f} x {br[1]:6.1f} x {br[2]:6.1f} mm")
    print(f"  우리 메쉬 : {len(ours.faces):>7,d}면  {bo[0]:6.1f} x {bo[1]:6.1f} x {bo[2]:6.1f} mm")
    print("  ...SBR 로 방위 72점 σ 비교 (양쪽 전부 PEC — 형상만 비교)")
    A = compare(real, ours, fc=fc, el=15.0, n_az=72,
                name_real="Typhoon H480 (real CAD, Apache-2.0)",
                name_ours="Typhoon H480 (ours, from spec sheet)")
    res["typhoon"] = A
    print(f"\n  투영면적 : 실물 {A['area_mean_real']*1e4:6.1f} cm2  "
          f"우리 {A['area_mean_ours']*1e4:6.1f} cm2   → **{A['d_area_db']:+.2f} dB**")
    print(f"  SBR σ    : 실물 {A['sigma_mean_real_dbsm']:+6.2f} dBsm  "
          f"우리 {A['sigma_mean_ours_dbsm']:+6.2f} dBsm  → **{A['d_sigma_db']:+.2f} dB**")
    print(f"  방위각별 σ 차이의 RMS : {A['d_sigma_rms_db']:.2f} dB  "
          "(평균만 맞고 패턴이 다를 수도 있으므로 함께 본다)")

    print("\n" + "=" * 92)
    print("[B] 프로펠러 — **Holybro 1345 실물 CAD** vs **우리 NACA-4 익형**")
    print("=" * 92)
    rp = load_reference("1345_prop_cw.stl")
    dia = float((rp.bounds[1] - rp.bounds[0])[:2].max())
    op = ours_prop(dia)
    br = (rp.bounds[1] - rp.bounds[0]) * 1000
    bo = (op.bounds[1] - op.bounds[0]) * 1000
    print(f"  실물 1345 : {len(rp.faces):>7,d}면  {br[0]:6.1f} x {br[1]:6.1f} x {br[2]:6.1f} mm")
    print(f"  우리 익형 : {len(op.faces):>7,d}면  {bo[0]:6.1f} x {bo[1]:6.1f} x {bo[2]:6.1f} mm")
    B = compare(rp, op, fc=fc, el=0.0, n_az=72,
                name_real="Holybro 1345 prop (real CAD, BSD-3)",
                name_ours="our NACA-4 airfoil prop (same diameter)")
    res["prop"] = B
    print(f"\n  투영면적 : 실물 {B['area_mean_real']*1e4:6.1f} cm2  "
          f"우리 {B['area_mean_ours']*1e4:6.1f} cm2   → **{B['d_area_db']:+.2f} dB**")
    print(f"  SBR σ    : 실물 {B['sigma_mean_real_dbsm']:+6.2f} dBsm  "
          f"우리 {B['sigma_mean_ours_dbsm']:+6.2f} dBsm  → **{B['d_sigma_db']:+.2f} dB**")
    print(f"  방위각별 RMS : {B['d_sigma_rms_db']:.2f} dB")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print(f"\n→ {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
