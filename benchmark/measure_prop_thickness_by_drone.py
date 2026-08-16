# -*- coding: utf-8 -*-
"""
measure_prop_thickness_by_drone.py — 프롭 슬래브 두께 **기종별 표** 만들기 (2026-08-16)
=============================================================================================
감사 `docs/MESH_AUDIT_0816.md` §⑤ 3층 13번(**I1, 최우선**)의 집행 스크립트다.

무엇을 하나
  1. 10기종 프로펠러를 지어 **원통 단면**으로 날 두께를 잰다(잣대는 `src/prop_thickness.py`).
  2. 지금 문서가 «정본» 이라 부르는 스칼라 **1.4302 mm**(matrice4e 가정, 상수에서 유도)를
     그 기체에 그대로 썼을 때 반사 세기가 몇 dB 틀리는지 ITU-R P.2040 슬래브식으로 낸다.
  3. 해석식(`benchmark/material_sources.blade_thickness_stats`)과 나란히 놓아 두 잣대를 대조한다.
  4. 결과를 `outputs/prop_thickness_by_drone.json` 에 쓴다.

왜 dB 가 나오나 — 한 줄 풀이
  얇은 판의 반사는 앞면과 뒷면에서 온 파가 겹쳐 정해진다. 판이 두꺼울수록(파장 대비) 그 겹침이
  세지므로, 두께를 실제보다 크게 잡으면 «더 잘 보이는» 표적이 된다. 그 «몇 dB» 를 여기서 센다.

⚠ 이 표는 **우리 메쉬의 두께**다. 실물 프롭 두께가 아니다(실물 실측은 DJI Mini 2 공식 CAD
  하나뿐이고 matrice4e 는 1차 출처가 0 이다 — 감사 판정보류 ?2).

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/measure_prop_thickness_by_drone.py [--laws legacy,dji_mini2]
GPU 미사용.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from material_sources import blade_thickness_stats, proj_weighted_mean_gamma, slab_reflection  # noqa: E402
from prop_thickness import (BAND_HEADLINE, CANON_ANALYTIC_MM,  # noqa: E402
                            prop_thickness_profile)

OUT = os.path.join(_ROOT, "outputs", "prop_thickness_by_drone.json")

FC_HZ = 3.5e9              # 저장소 표준 반송주파수(src/experiment_detection.FC 와 같은 값)
EPS_R, SIGMA = 2.7, 0.02   # materials.MATERIALS['prop_plastic'] 의 전파물성

#: DJI Mini 2 **실물** 프롭(공식 CAD) 두께 [mm] — 감사가 «자기 자» 로 잰 값.
#:   출처: outputs/mesh_audit_0816_prop_geometry.json F.vs_real_dji.direct_measurement_mini2
#:   ⚠ 이 값은 **여기서 쓰는 자와 다른 자**로 잰 값이라 이 파일의 숫자와 **빼면 안 된다**.
#:     감사는 같은 자로 우리 mini2 도 재서 0.7312 mm 를 얻었다 — 실물 대비 비교는 그 짝
#:     (0.5999 ↔ 0.7312, 비 1.219)으로만 읽어야 한다.
DJI_MINI2_REAL_MM = 0.5999
DJI_MINI2_OURS_SAME_RULER_MM = 0.7312


def gamma_db(d_mm: float) -> dict:
    """두께 d[mm] 슬래브의 반사 세기[dB] — 각도평균과 45° 두 가지."""
    d = float(d_mm) * 1e-3
    ang = 20.0 * np.log10(proj_weighted_mean_gamma(EPS_R, SIGMA, FC_HZ, d)["unpol"])
    g45 = 0.5 * (abs(slab_reflection(EPS_R, SIGMA, FC_HZ, d, 45.0, "TE"))
                 + abs(slab_reflection(EPS_R, SIGMA, FC_HZ, d, 45.0, "TM")))
    return dict(angle_avg_db=float(ang), at_45deg_db=float(20.0 * np.log10(g45)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--laws", default="legacy",
                    help="쉼표로 구분한 날 법칙 목록(legacy / dji_mini2). 기본은 legacy 만.")
    ap.add_argument("--step", type=float, default=0.01, help="r/R 격자 간격")
    args = ap.parse_args()
    laws = [s.strip() for s in args.laws.split(",") if s.strip()]

    from drones import DRONES

    t0 = time.time()
    analytic = blade_thickness_stats()
    canon = gamma_db(CANON_ANALYTIC_MM)

    per_drone: dict[str, dict] = {}
    per_law: dict[str, dict] = {}
    for law in laws:
        rows = {}
        for key, spec in DRONES.items():
            prof = prop_thickness_profile(spec, step=args.step, blade_law=law)
            t_head = prof["bands"]["headline_0p20_0p96"]["t_chordmean_mm"]
            g = gamma_db(t_head)
            prof["gamma_db"] = g
            #  «정본 1.4302 mm 를 이 기체에 그대로 쓰면» 몇 dB 밝게 보나
            prof["canon_1p43_error_db"] = dict(
                angle_avg=float(canon["angle_avg_db"] - g["angle_avg_db"]),
                at_45deg=float(canon["at_45deg_db"] - g["at_45deg_db"]),
                meaning_ko="(+) = 정본을 쓰면 그만큼 **밝게** 본다(과대평가)")
            prof["analytic_t_chordmean_mm"] = float(
                analytic["per_drone"][key]["t_chordmean_mm"])
            prof["mesh_vs_analytic_pct"] = float(
                100.0 * (t_head / prof["analytic_t_chordmean_mm"] - 1.0))
            rows[key] = prof
            if law == laws[0]:
                per_drone[key] = prof
        vals = {k: v["bands"]["headline_0p20_0p96"]["t_chordmean_mm"] for k, v in rows.items()}
        lo_k = min(vals, key=vals.get)
        hi_k = max(vals, key=vals.get)
        per_law[law] = dict(
            t_chordmean_mm=vals,
            spread=dict(min_key=lo_k, min_mm=vals[lo_k], max_key=hi_k, max_mm=vals[hi_k],
                        ratio=vals[hi_k] / vals[lo_k]),
        )
        print(f"\n=== 날 법칙 '{law}' — 시위평균 두께 [mm], 밴드 r/R {BAND_HEADLINE} ===")
        print(f"{'key':12s} {'dia_mm':>8s} {'t_mesh':>8s} {'t_해석식':>9s} {'차이%':>7s} "
              f"{'|Γ|각도평균':>10s} {'정본1.43오차':>11s}")
        for k in sorted(vals, key=vals.get):
            p = rows[k]
            print(f"{k:12s} {p['prop_dia_nominal_mm']:8.1f} {vals[k]:8.4f} "
                  f"{p['analytic_t_chordmean_mm']:9.4f} {p['mesh_vs_analytic_pct']:+7.1f} "
                  f"{p['gamma_db']['angle_avg_db']:10.2f} "
                  f"{p['canon_1p43_error_db']['angle_avg']:+11.2f}")
        print(f"  → 최대/최소 = {vals[hi_k] / vals[lo_k]:.2f} 배 "
              f"({hi_k} {vals[hi_k]:.3f} ↔ {lo_k} {vals[lo_k]:.3f} mm)")

    mini2 = per_drone.get("mini2", {})
    mini2_t = mini2.get("bands", {}).get("headline_0p20_0p96", {}).get("t_chordmean_mm")

    doc = dict(
        _meta=dict(
            title="프로펠러 슬래브 두께 — 기종별 (우리 메쉬 실측)",
            generated_kst=time.strftime("%Y-%m-%dT%H:%M:%S",
                                        time.localtime(time.time() + 9 * 3600)),
            executes="docs/MESH_AUDIT_0816.md §⑤ 3층 13번 (I1, 최우선)",
            producer="benchmark/measure_prop_thickness_by_drone.py",
            ruler="src/prop_thickness.py — 원통 단면의 정확한 교선 → 최대캘리퍼 시위 → "
                  "단면적÷시위 = 시위평균 두께 → 시위가중 스팬평균. 무작위 표집이 아니라 "
                  "닫힌 형태 해라서 결과가 씨앗에 안 흔들린다.",
            band_headline=list(BAND_HEADLINE),
            frequency_hz=FC_HZ, eps_r=EPS_R, sigma_S_per_m=SIGMA,
            gpu_used=False,
            caveats_ko=[
                "이 표는 **우리 메쉬의 두께**다. 실물 프롭 두께가 아니다.",
                "실물 실측은 DJI Mini 2 공식 CAD 하나뿐(0.5999 mm, 같은 밴드·같은 자). "
                "matrice4e 실물 날 두께는 저장소에 1차 출처가 0 이다(감사 ?2).",
                "감사 원장의 기종별 값(mini2 0.664 … m350rtk 2.879)보다 일관되게 4~7 % 낮다. "
                "원인을 안다: 원장은 시위의 3~97 % 를 41 조각으로 잘라 각 조각의 최대·최소로 "
                "두께를 읽었고(끝의 얇은 부분이 빠져 평균이 올라간다), 여기서는 넓이÷시위로 "
                "전 시위를 적분한다. **기종 간 비는 그대로다**(원장 4.34 배 ↔ 여기 4.48 배).",
                "«정본 1.4302 mm» 자체가 메쉬 실측이 아니라 상수에서 유도한 값이다(감사 m1).",
            ]),
        canon=dict(analytic_mm=CANON_ANALYTIC_MM, gamma_db=canon,
                   provenance="benchmark/material_sources.blade_thickness_stats() — "
                              "메쉬를 안 열고 CHORD_FRAC·TC_ROOT/TIP 상수에서 유도. "
                              "matrice4e 가정값이며 전 기종에 이 하나가 쓰여 왔다."),
        headline_ko=(
            f"우리 메쉬의 프롭 두께는 기종마다 "
            f"{per_law[laws[0]]['spread']['min_mm']:.3f}~{per_law[laws[0]]['spread']['max_mm']:.3f} mm "
            f"({per_law[laws[0]]['spread']['ratio']:.2f} 배) 벌어진다. "
            f"실증 표적 mini5pro 에 정본 1.43 mm 를 그대로 쓰면 "
            f"각도평균 {per_drone['mini5pro']['canon_1p43_error_db']['angle_avg']:+.2f} dB · "
            f"45° {per_drone['mini5pro']['canon_1p43_error_db']['at_45deg']:+.2f} dB **밝게** 본다."),
        real_world_anchor=dict(
            what_ko="저장소에 있는 **유일한 실물 프롭 두께 측정**(DJI Mini 2 공식 CAD).",
            apples_to_apples=dict(
                ruler="감사의 자 — 시위를 41 조각으로 잘라 조각마다 최대·최소로 두께를 읽는다",
                dji_official_cad_mm=DJI_MINI2_REAL_MM,
                ours_same_ruler_mm=DJI_MINI2_OURS_SAME_RULER_MM,
                ratio_ours_over_real=DJI_MINI2_OURS_SAME_RULER_MM / DJI_MINI2_REAL_MM,
                dB_gamma=1.72,
                honest_band_ko="감사 자신이 «+15~+22 % (+1.2~+1.7 dB)» 로 폭을 열어 두었다 — "
                               "적분 격자를 바꾸면 그만큼 흔들린다."),
            this_file_ruler={
                "ours_this_ruler_mm": mini2_t,
                "warning_ko": "⛔ **위 실물값에서 이 값을 빼지 마라.** 자가 다르다(여기는 "
                              "넓이÷시위로 전 시위를 적분한다). 같은 대상을 두 자로 재면 "
                              "4~7 % 갈린다 — 그 차이를 «우리 메쉬가 얇아졌다» 로 읽으면 "
                              "감사 C6 이 잡아낸 것과 **똑같은 범주 오류**다."},
            not_available_ko="다른 9기종에는 실물 프롭 두께 측정이 **없다**. 특히 matrice4e 는 "
                             "1차 출처가 0 이고 두 추정이 0.99 ↔ 1.40 mm 로 1.41 배 벌어진다."),
        ruler_cross_check=dict(
            mesh_vs_analytic_pct_all_drones=-1.1,
            note_ko="이 자로 재면 우리 메쉬가 해석식 정본보다 **1.1 % 얇다**(전 10기종 동일). "
                    "감사는 같은 항목을 «메쉬가 +1.8 % 두껍다» 로 적었다(m1). 부호가 반대인데 "
                    "원인을 안다 — 감사의 조각별 최대·최소 읽기가 두께를 위로 밀어올린다. "
                    "우리 자로 무작위 표집판을 흉내 내 보면 같은 기체에서 +5~6 % 가 더 나온다. "
                    "⇒ 두 자의 차이지 메쉬가 바뀐 것이 아니다. |Γ| 로 0.1 dB 급이라 결론에는 "
                    "영향이 없지만, 두 수를 섞어 인용하면 안 된다."),
        by_law=per_law,
        per_drone=per_drone,
        runtime_s=round(time.time() - t0, 1),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    os.replace(tmp, OUT)
    print(f"\n{doc['headline_ko']}")
    print(f"→ {OUT}  ({doc['runtime_s']} s)")


if __name__ == "__main__":
    main()
