# -*- coding: utf-8 -*-
"""
measure_mini2_prop_thickness.py — **DJI 공식 3D 모델에서 프로펠러 날 두께를 mm 로 잰다**
=========================================================================================
왜 필요한가
  `src/materials.py` 의 `prop_plastic` 은 «셸보다 얇다» 는 **방향만** 반영한 상수 0.25 를 쓰고,
  Sionna 쪽에는 두께를 아예 안 넘겨 **기본 100 mm** 판이 쓰였다. 그런데 프로펠러는 이 저장소의
  메인 태스크(마이크로도플러)를 **혼자 지고 있는 부품**이다. 그 부품의 실제 두께를 모르면
  안 된다.

  `outputs/reference_props.json` 은 시뮬레이터용 CAD 3종(Holybro 1345 · 3DR Solo · Yuneec)만
  쟀고, 그 파일 스스로 «저장소에 DJI 프로펠러 실물 기하는 존재하지 않는다» 라고 적었다.
  ⭐ **그 문장은 2026-08-07 이후로 참이 아니다** — `assets/meshes/reference/WM161_zhankai_1k.glb`
  (DJI Mini 2 공식 3D 모델, 펼침판)에는 **프로펠러 8장이 들어 있다**.

무엇을 재나
  GLB 를 월드좌표로 펼쳐 «얇고 긴» 조각 8개를 고른다(면 800↑ · 최장축 40 mm↑ · 최단축 12 mm↓ ·
  가로세로비 4↑). 그 8개가 좌우 대칭 4쌍으로 놓여 있으면 프로펠러다(이 파일이 그것도 검사한다).
  한 장을 표면 샘플링해 주성분(=스팬축)으로 정렬한 뒤, 스팬을 따라 단면을 잘라
  **최대 캘리퍼 = 시위(chord)**, 시위에 수직한 폭 = **두께**를 뽑는다.

⚠ 선언하는 한계
  · GLB 는 제품 페이지 뷰어용으로 **간략화(1k)** 된 판이다. 겉모양 치수는 공표값과 0.07~0.2 %
    안에서 맞지만(`outputs/meshdef_mini2_glb.json`), 날 두께는 그만큼 검증된 값이 아니다.
  · 스팬 바깥쪽(0.85 이상) 값은 믿지 말 것. 날이 휘어 있어(시미터) 주성분축에 수직한 절단이
    **비스듬히** 잘리고, 그래서 두께가 커 보인다. 이 파일은 그 구간을 따로 표시한다.
  · Mini 2 는 소형기다. 큰 프롭(S1000 급)은 이보다 두껍다 — 기종을 넘겨 쓰지 말 것.

실행:  PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/measure_mini2_prop_thickness.py
GPU 미사용 — trimesh·numpy·scipy 만 쓴다.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB = os.path.join(ROOT, "assets", "meshes", "reference", "WM161_zhankai_1k.glb")
#: DJI Mini 2 순정 프롭 4726F — 4.7 in = 119.4 mm
NOMINAL_DIA_MM = 119.4


def blade_parts(scene) -> list:
    """씬에서 «얇고 긴» 조각만 고른다 = 프로펠러 날 후보."""
    out = []
    for g in scene.dump():                       # dump() 가 월드좌표로 펴 준다
        e = np.sort(np.asarray(g.extents, float)) * 1000.0
        if len(g.faces) > 800 and e[2] > 40 and e[0] < 12 and e[2] / max(e[0], 1e-9) > 4:
            out.append(g)
    return out


def blade_sections(g, n_station: int = 13, n_sample: int = 200_000) -> list[dict]:
    P = trimesh.sample.sample_surface(g, int(n_sample), seed=0)[0] * 1000.0    # mm
    X = P - P.mean(0)
    _, _, vt = np.linalg.svd(X - X.mean(0), full_matrices=False)
    span = vt[0]
    t = X @ span
    lo, hi = np.percentile(t, 0.2), np.percentile(t, 99.8)
    rows = []
    for f in np.linspace(0.10, 0.95, n_station):
        x0 = lo + f * (hi - lo)
        m = np.abs(t - x0) <= 0.012 * (hi - lo)
        if m.sum() < 60:
            continue
        Q = X[m]
        Qp = Q - np.outer(Q @ span, span)                 # 스팬 성분 제거 → 단면
        _, _, vv = np.linalg.svd(Qp - Qp.mean(0), full_matrices=False)
        A = np.c_[Qp @ vv[0], Qp @ vv[1]]
        try:
            H = A[ConvexHull(A).vertices]
        except Exception:
            continue
        D = H[:, None, :] - H[None, :, :]
        d2 = (D ** 2).sum(-1)
        i, j = np.unravel_index(np.argmax(d2), d2.shape)
        chord = float(np.sqrt(d2[i, j]))
        ev = (H[j] - H[i]) / chord
        B = (A - H[i]) @ np.array([[ev[0], ev[1]], [-ev[1], ev[0]]]).T
        xs = np.linspace(0.03, 0.97, 41) * chord
        hw = chord / 40 * 0.9
        th = [float(np.ptp(B[np.abs(B[:, 0] - x) <= hw, 1]))
              for x in xs if (np.abs(B[:, 0] - x) <= hw).sum() >= 3]
        if len(th) < 8:
            continue
        th = np.asarray(th, float)
        rows.append(dict(span_frac=round(float(f), 3), chord_mm=round(chord, 2),
                         t_max_mm=round(float(th.max()), 3),
                         t_mean_mm=round(float(th.mean()), 3),
                         t_over_c=round(float(th.max() / chord), 4),
                         span_len_mm=round(float(hi - lo), 2),
                         trust=bool(f <= 0.85)))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", default=GLB)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    scene = trimesh.load(a.glb, process=False)
    blades = blade_parts(scene)
    print(f"■ 날 후보 {len(blades)}장  (Mini 2 는 4프롭 × 2날 = 8장이어야 한다)")
    allp = np.vstack([np.asarray(g.vertices) for g in scene.dump()]) * 1000.0
    c_all = allp.mean(0)
    ctrs = np.array([np.asarray(g.vertices).mean(0) * 1000.0 - c_all for g in blades])
    print("   좌우 대칭 검사 — 각 날의 좌우 짝이 있는가:",
          all(any(abs(c[0] + d[0]) < 3 and abs(c[2] - d[2]) < 3 for d in ctrs) for c in ctrs))

    rows = blade_sections(blades[0])
    print(f"\n   스팬 길이 {rows[0]['span_len_mm']:.1f} mm · 공칭 프롭 지름 {NOMINAL_DIA_MM} mm")
    print(f"   {'스팬':>6} {'시위[mm]':>9} {'최대두께[mm]':>12} {'평균두께[mm]':>12} {'t/c':>7}  신뢰")
    for r in rows:
        print(f"   {r['span_frac']:>6.2f} {r['chord_mm']:>9.2f} {r['t_max_mm']:>12.2f} "
              f"{r['t_mean_mm']:>12.2f} {r['t_over_c']:>7.3f}  {'O' if r['trust'] else '× (사각절단)'}")
    good = [r for r in rows if r["trust"]]
    tm = [r["t_max_mm"] for r in good]
    print(f"\n⭐ 믿는 구간(스팬 0.10~0.85) 최대두께 {min(tm):.2f}~{max(tm):.2f} mm · "
          f"t/c {min(r['t_over_c'] for r in good):.3f}~{max(r['t_over_c'] for r in good):.3f}")
    print("   대조: src/drone_cad.py 는 TC_ROOT 0.095 → TC_TIP 0.065 를 쓴다 "
          "(루트가 DJI 실측보다 두껍다).")
    if a.json:
        json.dump(dict(blades=len(blades), stations=rows), open(a.json, "w"),
                  ensure_ascii=False, indent=1)
        print("→", a.json)


if __name__ == "__main__":
    main()
