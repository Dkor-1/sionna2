# -*- coding: utf-8 -*-
"""
regress_blade_law_bitidentical.py — **«안 고르면 안 바뀐다» 를 증명한다** (2026-08-16)
=============================================================================================
2026-08-16 라운드에서 `src/drone_cad.py` 의 블레이드 법칙에 손잡이를 붙였다
(`blade_law` · `pitch_law` · λ 로 삼각형 크기 묶기 — 감사 §⑤ 3층 13·15·16·17·18).

지금까지의 **모든** 원장·리포트·덱이 옛 법칙으로 나온 값이다. 그러니 이 수리의 제1 조건은
«손잡이를 안 건드리면 메쉬가 **비트 단위로** 예전 그대로일 것» 이다. 이 파일이 그것을 증명한다.

무엇을 검사하나
  A. **비트동일** — 인자 없이 지은 프로펠러의 SHA-256 지문이 수리 **직전**에 떠 둔
     `outputs/regress_blade_law_baseline.json` 과 한 글자도 안 다른가.
     (지문은 정점 float64 와 면 int64 의 **메모리 바이트**를 그대로 해시한 것이라,
      반올림 마지막 자리만 달라져도 깨진다.)
  B. **기본값 동치** — `blade_law='legacy', pitch_law=None` 을 **명시로** 줘도 같은가.
  C. **손잡이가 실제로 배선돼 있나** — 새 판을 고르면 메쉬가 **달라져야** 한다.
     (A 만 있으면 «손잡이가 아무것도 안 하는» 코드도 통과해 버린다. 양성 대조다.)
  D. **λ 로 묶기는 형상을 안 바꾼다** — 표면적이 그대로이고 최장 모서리만 줄어드는가.
  E. **레지스트리가 깨끗한가** — 새 스펙 필드 `prop_chord_max_over_r` 가 전 기종 None 인가.
     (누가 값을 채우면 legacy 메쉬도 바뀐다 — 그건 의도적 결정이어야 하고, 여기서 잡힌다.)

⚠ 검사 범위는 **프로펠러뿐**이다 — 날 법칙이 건드리는 것이 프롭뿐이기 때문이다.
  ⭐[정정 2026-08-16 적대검증] 예전 이 자리에 «프레임은 같은 라운드의 다른 수리가 일부러
  바꾸고 있어서 넣으면 거짓 실패가 난다» 고 적혀 있었는데 **사실이 아니다.** 이 라운드가
  프레임 쪽에 붙인 손잡이(`_body_folding(smooth_iters=…)` · `_gear_arm_spikes(inboard=시퀀스)`)
  는 전부 **기본값이 옛 값**이라, 지금 트리에서 `build_drone()` 을 10기종 전부 지어 정점·면·
  그룹 바이트를 해시해 보면 수리 **직전 코드와 비트동일**이다(적대검증에서 직접 확인).
  ⇒ 프레임을 이 시험에 넣어도 거짓 실패는 안 난다. 넣지 않은 이유는 «범위» 이지 «불가» 가 아니다.

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/regress_blade_law_bitidentical.py
종료코드 0 = 통과. GPU 미사용.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BASELINE = os.path.join(_ROOT, "outputs", "regress_blade_law_baseline.json")
LAMBDA_35GHZ = 299_792_458.0 / 3.5e9          # 3.5 GHz 파장 [m] = 85.65 mm


def fingerprint(mesh) -> str:
    """메쉬의 지문 — 정점(float64)·면(int64) 바이트를 그대로 SHA-256."""
    v = np.asarray(mesh.v, float)
    f = np.asarray(mesh.f, np.int64)
    return hashlib.sha256(v.tobytes() + f.tobytes()).hexdigest()


def surface_area_mm2(mesh) -> float:
    import trimesh
    t = trimesh.Trimesh(vertices=np.asarray(mesh.v, float),
                        faces=np.asarray(mesh.f, np.int64), process=False)
    return float(t.area) * 1e6


def max_edge_mm(mesh) -> float:
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    return float(np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1).max()) * 1000.0


def main() -> int:
    from drones import DRONES, build_propeller
    from drone_cad import build_propeller_cad

    if not os.path.exists(BASELINE):
        print(f"⛔ 기준선 파일이 없다: {BASELINE}")
        return 2
    with open(BASELINE) as f:
        base = json.load(f)["per_drone"]

    fails: list[str] = []
    checked = 0

    # ── A. 비트동일 ────────────────────────────────────────────────────────
    for key, spec in DRONES.items():
        arms = {
            "build_propeller": build_propeller(spec),
            "build_propeller_mirror": build_propeller(spec, mirror=True),
            "cad_nsec22": build_propeller_cad(spec, n_sec=22).to_geom(),
        }
        for tag, mesh in arms.items():
            checked += 1
            want = base.get(key, {}).get(tag, {})
            got = fingerprint(mesh)
            if not want:
                fails.append(f"A {key}/{tag}: 기준선에 항목이 없다")
            elif got != want["sha"]:
                fails.append(f"A {key}/{tag}: 지문 불일치 "
                             f"(면 {len(mesh.f)} ↔ 기준선 {want['nf']})")
    print(f"A 비트동일 : {checked} 개 팔 검사 — "
          f"{'통과' if not fails else str(len(fails)) + ' 건 실패'}")

    # ── B. 기본값 동치(명시로 legacy 를 줘도 같아야) ────────────────────────
    nb = 0
    for key, spec in DRONES.items():
        a = fingerprint(build_propeller(spec))
        b = fingerprint(build_propeller(spec, blade_law="legacy", pitch_law=None,
                                        max_edge_m=None, lambda_m=None))
        nb += 1
        if a != b:
            fails.append(f"B {key}: 기본값과 명시 legacy 가 다르다")
    print(f"B 기본값 동치: {nb} 기종 — {'통과' if not any(x.startswith('B ') for x in fails) else '실패'}")

    # ── C. 손잡이가 실제로 배선돼 있나(양성 대조) ──────────────────────────
    probe = DRONES["matrice4e"]
    ref = fingerprint(build_propeller(probe))
    for name, kw in (("blade_law='dji_mini2'", dict(blade_law="dji_mini2")),
                     ("pitch_law='dji_mini2'", dict(pitch_law="dji_mini2")),
                     ("lambda_m=λ(3.5GHz)", dict(lambda_m=LAMBDA_35GHZ))):
        if fingerprint(build_propeller(probe, **kw)) == ref:
            fails.append(f"C {name}: 손잡이를 줬는데 메쉬가 **안 바뀌었다** — 배선이 끊겼다")
    print("C 배선(양성대조): 3 개 손잡이 — "
          f"{'통과' if not any(x.startswith('C ') for x in fails) else '실패'}")

    # ── D. λ 로 묶기는 형상을 안 바꾼다 ────────────────────────────────────
    tgt_mm = LAMBDA_35GHZ / 10.0 * 1000.0
    rows = []
    for key in ("m350rtk", "mavic4pro", "mini2"):
        spec = DRONES[key]
        a = build_propeller(spec)
        b = build_propeller(spec, lambda_m=LAMBDA_35GHZ)
        da = abs(surface_area_mm2(b) - surface_area_mm2(a))
        if da > 1e-6 * max(surface_area_mm2(a), 1.0):
            fails.append(f"D {key}: 세분이 표면적을 바꿨다 (Δ {da:.3e} mm²)")
        if max_edge_mm(b) > tgt_mm * 1.02:
            fails.append(f"D {key}: 세분 후에도 최장 모서리가 목표를 넘는다 "
                         f"({max_edge_mm(b):.2f} > {tgt_mm:.2f} mm)")
        rows.append((key, len(a.f), len(b.f), max_edge_mm(a), max_edge_mm(b), da))
    print(f"D λ/10 묶기 : 목표 {tgt_mm:.2f} mm — "
          f"{'통과' if not any(x.startswith('D ') for x in fails) else '실패'}")
    for k, na, nb2, ea, eb, da in rows:
        print(f"    {k:10s} 면 {na:6d}→{nb2:6d}  최장 {ea:6.2f}→{eb:5.2f} mm  |Δ면적| {da:.2e} mm²")

    # ── E. 레지스트리가 깨끗한가 ──────────────────────────────────────────
    dirty = [k for k, s in DRONES.items() if getattr(s, "prop_chord_max_over_r", None) is not None]
    if dirty:
        fails.append(f"E prop_chord_max_over_r 가 채워진 기종이 있다: {dirty} "
                     f"— 그러면 legacy 메쉬도 바뀐다(의도한 것인지 확인할 것)")
    print(f"E 스펙 필드 : 전 기종 None — {'통과' if not dirty else '실패: ' + str(dirty)}")

    print()
    if fails:
        print(f"⛔ 실패 {len(fails)} 건")
        for x in fails:
            print("   -", x)
        return 1
    print("✅ 전부 통과 — 손잡이를 안 건드리면 프로펠러 메쉬는 비트 단위로 예전 그대로다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
