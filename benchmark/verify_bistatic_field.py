# -*- coding: utf-8 -*-
"""
verify_bistatic_field.py — **바이스태틱 복소장 `sbr_field_bistatic` 의 계약 검사**
=============================================================================
새로 더한 `rcs_sbr.sbr_field_bistatic()` 가 **정말로 기존 커널의 특수해를 품는가**를 숫자로
남긴다. 리포트는 손으로 적지 말고 `outputs/verify_bistatic_field.json` 에서 주입할 것.

무엇을 재는가 — 다섯 과녁
  [G1] **모노 회귀 게이트** (핵심): û_s = û_i 면 `sbr_field` 와 **수치적으로 같아야 한다**.
       복소장이므로 크기뿐 아니라 **위상**까지 같아야 한다 — 마이크로도플러가 쓰는 것이 위상이다.
       여러 기체·자세·주파수·시선·스위치 조합에서 상대오차 |E_bi−E_mono|/|E_mono| 의 최대값.
  [G2] **σ 교차검증**: (4π/λ²)|E_bi|² 이 `rcs_sbr_multistatic(..., jitter=1)` 의 σ 와 맞는가.
       ⚠ 두 경로는 **Γ(θ) 각도 모양에서 갈린다** — 새 함수는 모노 경로(`sbr_field`)와 같은 규약으로
       `gamma_shape` 를 곱하는데 `rcs_sbr_multistatic` 은 곱하지 않는다. 그래서
         · `angle_gamma_off` : 사과-대-사과(둘 다 각도 모양 없음) → 여기서 일치해야 한다.
         · `angle_gamma_on`  : 생산 기본값에서 두 경로가 실제로 얼마나 갈리는지(정직 표기용).
  [G3] **멀티 Rx 벡터화 일치**: E(û_i, [û_s…]) 가 û_s 하나씩 부른 것과 같은가(조명 재사용의 대가 0).
  [G4] **전방산란 한계 확인**: β→180° 에서 E≡0 (docstring 한계 (1)이 코드에서 실제로 그렇게 나오는가).
  [G5] **상반성 위반량**(진단, 통과/실패 아님): |E(û_i,û_s)| ↔ |E(û_s,û_i)| 의 dB 차 — docstring
       한계 (2)를 **장(field) 수준에서** 계량한다.

⚠ 이 스크립트는 커널을 고치지 않는다. 숫자가 안 맞으면 맞추지 말고 **왜 다른지** 적는다.

실행:  cd sionna2 && SIONNA2_GPU=2 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
         benchmark/verify_bistatic_field.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import socket
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")          # ⭐사용자 지시(2026-08-10): 오늘은 GPU 2 만.

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                  # noqa: E402

import rcs_sbr as rsb                                               # noqa: E402
from rcs_sbr import (C0, _look, rcs_sbr_multistatic, sbr_field,      # noqa: E402
                     sbr_field_bistatic)
from drones import DRONES, DRONE_GROUP_MAT, pose_articulated        # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "verify_bistatic_field.json")

GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}

AIRFRAMES = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus"]
BANDS = [1.8e9, 3.5e9, 5.5e9]            # LTE / 5G n78 / 상단 대역
LOOKS = [(0.0, -15.0), (37.0, 8.0)]      # (az, el) [deg] — 표적→레이더
GATE = 1e-9                              # 회귀 게이트 목표 상대오차


def _iso():
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _db(x):
    return float(10.0 * np.log10(max(float(x), 1e-300)))


def _poses(spec):
    """자세 두 개 — (a) 정렬 상태, (b) 몸체 기울임 + 로터별 다른 위상."""
    n = int(spec.num_rotors)
    yield "aligned", pose_articulated(spec, rotor_phase_deg=[0.0] * n)
    yield "tilted", pose_articulated(spec, body_rpy=(4.0, -7.0, 23.0),
                                     rotor_phase_deg=[37.2 + 9.1 * i for i in range(n)])


def _relerr(a, b):
    """복소 상대오차 |a−b|/|b| (위상 포함)."""
    a, b = complex(a), complex(b)
    den = abs(b)
    return float(abs(a - b) / den) if den > 0 else float(abs(a - b))


# ─────────────────────────────────────────────────────────────────────────── #
#  [G1] 모노 회귀 게이트
# ─────────────────────────────────────────────────────────────────────────── #
def gate_mono_regression():
    cases = []
    t0 = time.time()
    for key in AIRFRAMES:
        spec = DRONES[key]
        for pname, mesh in _poses(spec):
            for fc in BANDS:
                for (az, el) in LOOKS:
                    u = _look(az, el)
                    ck = ("vbf", key, pname, round(fc / 1e6), az, el)
                    for variant, kw_m, kw_b in (
                        # 생산 기본값(투과 O, 출사가시성 O)
                        ("default", dict(), dict(exit_vis=True)),
                        # 출사 가시성을 끈 판 — 모노에서 exit_vis 가 no-op 인지 분리해서 본다
                        ("exit_vis_off", dict(), dict(exit_vis=False)),
                        # 투과 없는 순수 외피 — 셸 경로가 회귀에 개입하지 않는지 본다
                        ("no_penetrate", dict(penetrate=False),
                         dict(penetrate=False, exit_vis=True)),
                    ):
                        Em = sbr_field(mesh, GM, fc, u, cache_key=ck, **kw_m)
                        Eb = sbr_field_bistatic(mesh, GM, fc, u, u, cache_key=ck, **kw_b)
                        re = _relerr(Eb, Em)
                        cases.append(dict(
                            drone=key, pose=pname, fc_ghz=round(fc / 1e9, 3), az=az, el=el,
                            variant=variant, rel_err=re,
                            abs_mono=float(abs(Em)), abs_bi=float(abs(complex(Eb))),
                            d_abs_db=_db(abs(complex(Eb)) ** 2) - _db(abs(Em) ** 2),
                            d_phase_deg=float(np.degrees(np.angle(complex(Eb) / Em)))
                            if abs(Em) > 0 else None,
                            bit_identical=bool(complex(Eb) == complex(Em)),
                        ))
            rsb._SCENE_CACHE.clear()          # 자세마다 씬이 다르다 — 메모리 눌러둔다
    dt = time.time() - t0

    by_var = {}
    for v in sorted({c["variant"] for c in cases}):
        sub = [c for c in cases if c["variant"] == v]
        by_var[v] = dict(n=len(sub),
                         max_rel_err=max(c["rel_err"] for c in sub),
                         n_bit_identical=sum(c["bit_identical"] for c in sub))
    worst = max(cases, key=lambda c: c["rel_err"])
    return dict(
        n_cases=len(cases), seconds=dt, gate=GATE,
        max_rel_err=worst["rel_err"], worst_case=worst,
        n_bit_identical=sum(c["bit_identical"] for c in cases),
        by_variant=by_var,
        passed=bool(worst["rel_err"] <= GATE),
        cases=cases,
        note=("û_s=û_i 에서 sbr_field 와의 복소 상대오차. 위상까지 포함한다 — "
              "마이크로도플러가 쓰는 것이 프레임 간 상대위상이기 때문이다."),
    )


def gate_mono_regression_angle_gamma_off():
    """같은 게이트를 ANGLE_GAMMA=False 에서 한 번 더 — 각도 모양 배선이 회귀를 가리지 않는지."""
    old = rsb.ANGLE_GAMMA
    rsb.ANGLE_GAMMA = False
    try:
        cases = []
        for key in ("mavic4pro", "s1000plus"):
            spec = DRONES[key]
            mesh = pose_articulated(spec, rotor_phase_deg=[0.0] * int(spec.num_rotors))
            for fc in (1.8e9, 3.5e9):
                u = _look(11.0, -9.0)
                ck = ("vbf-ag0", key, round(fc / 1e6))
                Em = sbr_field(mesh, GM, fc, u, cache_key=ck)
                Eb = sbr_field_bistatic(mesh, GM, fc, u, u, cache_key=ck)
                cases.append(dict(drone=key, fc_ghz=round(fc / 1e9, 3),
                                  rel_err=_relerr(Eb, Em),
                                  bit_identical=bool(complex(Eb) == complex(Em))))
            rsb._SCENE_CACHE.clear()
    finally:
        rsb.ANGLE_GAMMA = old
    return dict(n_cases=len(cases), max_rel_err=max(c["rel_err"] for c in cases),
                n_bit_identical=sum(c["bit_identical"] for c in cases), cases=cases)


def gate_scene_rebuild():
    """cache_key=None (생산 마이크로도플러 경로: 자세마다 씬 재생성) 에서도 같은가.

    씬을 두 번 짓는 것이 결과를 바꾸면(BVH 비결정성) 회귀오차가 물리가 아니라 빌드 탓이다 →
    분리해서 본다."""
    cases = []
    for key in ("mini5pro", "matrice4e"):
        spec = DRONES[key]
        mesh = pose_articulated(spec, rotor_phase_deg=[13.0 * i for i in range(int(spec.num_rotors))])
        u = _look(-24.0, 6.0)
        Em = sbr_field(mesh, GM, 3.5e9, u)                        # cache_key 없음 → 씬 새로
        Eb = sbr_field_bistatic(mesh, GM, 3.5e9, u, u)            # 또 새로
        cases.append(dict(drone=key, rel_err=_relerr(Eb, Em),
                          bit_identical=bool(complex(Eb) == complex(Em))))
    return dict(n_cases=len(cases), max_rel_err=max(c["rel_err"] for c in cases),
                n_bit_identical=sum(c["bit_identical"] for c in cases), cases=cases,
                note="씬 캐시 없이(자세마다 재생성) 같은 값이 나오는지 — Mitsuba 빌드 비결정성 분리.")


def gate_ptd():
    """ptd=True 경로도 모노에서 겹치는가 (모서리 프린지 배선의 계약)."""
    spec = DRONES["mavic4pro"]
    mesh = pose_articulated(spec, rotor_phase_deg=[0.0] * int(spec.num_rotors))
    fc, u = 3.5e9, _look(0.0, -15.0)
    ck = ("vbf-ptd", "mavic4pro")
    t0 = time.time()
    try:
        Em = sbr_field(mesh, GM, fc, u, cache_key=ck, ptd=True)
        Eb = sbr_field_bistatic(mesh, GM, fc, u, u, cache_key=ck, ptd=True)
    except Exception as e:                                        # noqa: BLE001
        return dict(available=False, error=f"{type(e).__name__}: {e}")
    finally:
        rsb._SCENE_CACHE.clear()
    return dict(available=True, seconds=time.time() - t0, rel_err=_relerr(Eb, Em),
                bit_identical=bool(complex(Eb) == complex(Em)),
                abs_mono=float(abs(Em)), abs_bi=float(abs(complex(Eb))))


# ─────────────────────────────────────────────────────────────────────────── #
#  [G2] σ 교차검증 — (4π/λ²)|E_bi|²  vs  rcs_sbr_multistatic(jitter=1)
# ─────────────────────────────────────────────────────────────────────────── #
BETAS = [0.0, 15.0, 30.0, 45.0, 60.0, 90.0]


def _beta_pairs(az, el, betas):
    u_i = _look(az, el)
    out = []
    for b in betas:
        u_s = _look(az + b, el)
        beta_true = float(np.degrees(np.arccos(np.clip(u_i @ u_s, -1, 1))))
        out.append((b, beta_true, u_s))
    return u_i, out


def cross_check_sigma(angle_gamma: bool):
    old = rsb.ANGLE_GAMMA
    rsb.ANGLE_GAMMA = bool(angle_gamma)
    rows = []
    try:
        for key in AIRFRAMES:
            spec = DRONES[key]
            mesh = pose_articulated(spec, rotor_phase_deg=[0.0] * int(spec.num_rotors))
            fc = 3.5e9
            lam = C0 / fc
            u_i, pairs = _beta_pairs(0.0, -2.0, BETAS)
            ck = ("vbf-sig", key, int(angle_gamma))
            U_s = [p[2] for p in pairs]
            E = np.atleast_1d(sbr_field_bistatic(mesh, GM, fc, u_i, U_s, cache_key=ck))
            sig_field = (4.0 * np.pi / lam ** 2) * np.abs(E) ** 2
            sig_ms = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, GM, fc, u_i, U_s, cache_key=ck, jitter=1), float))
            for (b, bt, _), sf, sm in zip(pairs, sig_field, sig_ms):
                rows.append(dict(drone=key, beta_nominal_deg=b, beta_deg=round(bt, 3),
                                 sigma_field_m2=float(sf), sigma_multistatic_m2=float(sm),
                                 sigma_field_dbsm=_db(sf), sigma_multistatic_dbsm=_db(sm),
                                 rel_err=float(abs(sf - sm) / sm) if sm > 0 else float(abs(sf - sm)),
                                 d_db=_db(sf) - _db(sm)))
            rsb._SCENE_CACHE.clear()
    finally:
        rsb.ANGLE_GAMMA = old
    worst = max(rows, key=lambda r: r["rel_err"])
    return dict(angle_gamma=bool(angle_gamma), n=len(rows),
                max_rel_err=worst["rel_err"], max_abs_d_db=max(abs(r["d_db"]) for r in rows),
                worst=worst, rows=rows)


# ─────────────────────────────────────────────────────────────────────────── #
#  [G3] 멀티 Rx 벡터화 · [G4] 전방산란 · [G5] 상반성
# ─────────────────────────────────────────────────────────────────────────── #
def gate_multi_rx():
    spec = DRONES["matrice4e"]
    mesh = pose_articulated(spec, rotor_phase_deg=[0.0] * int(spec.num_rotors))
    fc = 3.5e9
    u_i, pairs = _beta_pairs(0.0, -2.0, [10.0, 35.0, 70.0])
    U_s = [p[2] for p in pairs]
    ck = ("vbf-mrx",)
    Evec = np.atleast_1d(sbr_field_bistatic(mesh, GM, fc, u_i, U_s, cache_key=ck))
    Eone = [complex(sbr_field_bistatic(mesh, GM, fc, u_i, us, cache_key=ck)) for us in U_s]
    errs = [_relerr(a, b) for a, b in zip(Evec, Eone)]
    rsb._SCENE_CACHE.clear()
    return dict(n=len(errs), max_rel_err=max(errs), errs=[float(e) for e in errs],
                note="조명 광선을 한 번만 쏘고 û_s 만 반복하는 경로가 개별 호출과 같은지.")


def gate_forward_scatter():
    """β→180° 에서 E≡0 — docstring 한계 (1)이 코드에서 실제로 그렇게 나오는지 확인."""
    rows = []
    for key in ("mavic4pro", "s1000plus"):
        spec = DRONES[key]
        mesh = pose_articulated(spec, rotor_phase_deg=[0.0] * int(spec.num_rotors))
        u_i = _look(0.0, -2.0)
        for b in (170.0, 180.0):
            u_s = -u_i if b == 180.0 else _look(0.0 + b, -2.0)
            E = complex(sbr_field_bistatic(mesh, GM, 3.5e9, u_i, u_s, cache_key=("vbf-fs", key)))
            rows.append(dict(drone=key, beta_deg=b, abs_E=float(abs(E)), is_zero=bool(E == 0)))
        rsb._SCENE_CACHE.clear()
    return dict(rows=rows,
                note=("조명게이트(n̂·û_i>0)와 수신게이트(n̂·û_s>0)가 상호배타가 되면 E=0 이다. "
                      "이것은 버그가 아니라 lit-PO 의 적용범위 한계(전방로브 없음)이며 "
                      "docstring 한계 (1)로 계약되어 있다."))


def gate_reciprocity():
    """|E(û_i,û_s)| ↔ |E(û_s,û_i)| dB 차 — 한계 (2)를 장 수준에서 계량(진단)."""
    rows = []
    for key in AIRFRAMES:
        spec = DRONES[key]
        mesh = pose_articulated(spec, rotor_phase_deg=[0.0] * int(spec.num_rotors))
        u_i, pairs = _beta_pairs(0.0, -2.0, [15.0, 45.0, 90.0])
        for b, bt, u_s in pairs:
            ck = ("vbf-rec", key)
            E1 = complex(sbr_field_bistatic(mesh, GM, 3.5e9, u_i, u_s, cache_key=ck))
            E2 = complex(sbr_field_bistatic(mesh, GM, 3.5e9, u_s, u_i, cache_key=ck))
            rows.append(dict(drone=key, beta_deg=round(bt, 3),
                             abs_db_is=_db(abs(E1) ** 2), abs_db_si=_db(abs(E2) ** 2),
                             d_db=_db(abs(E1) ** 2) - _db(abs(E2) ** 2),
                             d_phase_deg=float(np.degrees(np.angle(E1 / E2)))
                             if abs(E2) > 0 else None))
        rsb._SCENE_CACHE.clear()
    return dict(n=len(rows), max_abs_d_db=max(abs(r["d_db"]) for r in rows), rows=rows,
                note=("상반성은 정리이므로 위반은 전부 모형오차다. û_i 단일 조명격자 재사용의 "
                      "구조적 대가이며 격자세분으로 줄지 않는다(한계 (2)). 위상차도 함께 남긴다 — "
                      "복소장을 쓰는 하류(마이크로도플러)는 크기뿐 아니라 위상 비대칭도 본다."))


def main():
    t0 = time.time()
    print("═══ sbr_field_bistatic 계약 검사 ═══", flush=True)

    print("  [G1] 모노 회귀 게이트 …", flush=True)
    g1 = gate_mono_regression()
    print(f"       n={g1['n_cases']} 최대 상대오차 {g1['max_rel_err']:.3e} "
          f"(비트동일 {g1['n_bit_identical']}/{g1['n_cases']}) "
          f"{'PASS' if g1['passed'] else 'FAIL'}  [{g1['seconds']:.0f}s]", flush=True)

    g1b = gate_mono_regression_angle_gamma_off()
    print(f"  [G1b] ANGLE_GAMMA=False: 최대 {g1b['max_rel_err']:.3e}", flush=True)
    g1c = gate_scene_rebuild()
    print(f"  [G1c] 씬 재생성 경로: 최대 {g1c['max_rel_err']:.3e}", flush=True)
    g1d = gate_ptd()
    print(f"  [G1d] ptd=True: {g1d.get('rel_err')}", flush=True)

    print("  [G2] σ 교차검증 …", flush=True)
    g2off = cross_check_sigma(False)
    g2on = cross_check_sigma(True)
    print(f"       각도Γ off: 최대 상대오차 {g2off['max_rel_err']:.3e} "
          f"(|Δ| ≤ {g2off['max_abs_d_db']:.2e} dB)", flush=True)
    print(f"       각도Γ on : |Δ| 최대 {g2on['max_abs_d_db']:.3f} dB ← 두 경로의 물리 차이", flush=True)

    print("  [G3] 멀티 Rx …", flush=True)
    g3 = gate_multi_rx()
    print(f"       최대 상대오차 {g3['max_rel_err']:.3e}", flush=True)
    g4 = gate_forward_scatter()
    print(f"  [G4] 전방산란: {[(r['beta_deg'], r['abs_E']) for r in g4['rows']]}", flush=True)
    g5 = gate_reciprocity()
    print(f"  [G5] 상반성 위반 최대 {g5['max_abs_d_db']:.2f} dB (진단)", flush=True)

    doc = dict(
        generated=_iso(), host=socket.gethostname(),
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES"),
        script="benchmark/verify_bistatic_field.py",
        kernel=dict(
            function="rcs_sbr.sbr_field_bistatic",
            reference="rcs_sbr.sbr_field (모노 복소장)",
            sigma_reference="rcs_sbr.rcs_sbr_multistatic (바이스태틱 σ)",
            angle_gamma_default=bool(rsb.ANGLE_GAMMA),
            angle_gamma_wired=True,
            angle_gamma_convention="gamma_shape(재질, fc, cosθ_i), θ_i = 국소 입사각(n̂·û_i) — sbr_field·rcs_sbr_batch 와 동일",
            angle_gamma_note=("⚠ rcs_sbr_multistatic 은 각도 모양을 곱하지 않는다(matk 를 받고도 쓰지 않음). "
                              "따라서 생산 기본값(ANGLE_GAMMA=True)에서 (4π/λ²)|E_bi|² 와 그 함수의 σ 는 "
                              "sigma_cross_check.angle_gamma_on 만큼 갈린다. 두 경로를 나란히 인용하지 말 것."),
            jitter="없음(단일 격자) — 위상을 쓰는 하류라 격자 평균이 의미를 바꾼다",
            spacing=f"λ/{rsb.DEFAULT_DIV}",
        ),
        config=dict(airframes=AIRFRAMES, bands_hz=BANDS, looks_az_el_deg=LOOKS,
                    betas_deg=BETAS, gate=GATE, div=rsb.DEFAULT_DIV),
        regression_mono_gate=g1,
        regression_angle_gamma_off=g1b,
        regression_scene_rebuild=g1c,
        regression_ptd=g1d,
        sigma_cross_check=dict(angle_gamma_off=g2off, angle_gamma_on=g2on),
        multi_rx=g3, forward_scatter=g4, reciprocity=g5,
        verdict=dict(
            mono_gate_passed=bool(g1["passed"]),
            mono_gate_max_rel_err=g1["max_rel_err"],
            sigma_cross_check_max_rel_err=g2off["max_rel_err"],
            sigma_angle_gamma_gap_db=g2on["max_abs_d_db"],
            seconds=time.time() - t0,
        ),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"\n▶ {OUT}  [{time.time() - t0:.0f}s]", flush=True)
    return 0 if g1["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
