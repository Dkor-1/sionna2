# -*- coding: utf-8 -*-
"""
facet_count_0903.py — 0° 낙차의 «벌 수 N» 이 메쉬의 무엇을 따라가나.

여기까지 갈린 것
    · el 0° 낙차 깊이가 기체마다 **정수 N 의 (N−1)/N 자리**에 극도로 좁게 뭉친다
        mini5pro 0.50000 (N=2) · matrice4e 0.66670 (N=3) · mavic4pro 0.74990 (N=4)
    · matrice4e 자세 47 의 경로 목록에는 진폭·지연·정점이 **똑같은**
      «정반사 → camera» 항목이 **셋** 있었고, 그 합이 곧 |E| 였다.

⭐물음 — 그 «벌 수» 가 메쉬의 무엇인가.
   가설 ⓐ 정반사가 일어나는 면이 **삼각형 N 장**으로 쪼개져 있어 장마다 한 벌씩 나온다
   가설 ⓑ 시선에 수직인 **평행 면이 N 겹** 있다(앞뒤 판·덮개 등)
   가설 ⓒ 메쉬와 무관하고 솔버 안의 무엇이다

무엇을 재나
    기체마다 그 부품(camera 등) OBJ 를 읽어
      · 삼각형 수 · 법선의 무리(같은 방향끼리 묶기)
      · **정면(−x 또는 +x)을 보는 삼각형이 몇 장인지** — 시선이 그 축이다
      · 그 삼각형들이 몇 개의 «평면» 에 놓이나(법선+거리로 묶기)

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" ~/.venvs/py312/bin/python benchmark/facet_count_0903.py
"""
from __future__ import annotations

import collections
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "outputs", "facet_count_0903.json")

#: el 0 에서 읽은 벌 수 (outputs/el0_copies_0903.json 의 뭉치는 자리)
N_SEEN = {"mini5pro": 2, "matrice4e": 3, "mavic4pro": 4}


def read_obj(p: str):
    V, F = [], []
    for ln in open(p, encoding="utf-8", errors="replace"):
        if ln.startswith("v "):
            V.append([float(x) for x in ln.split()[1:4]])
        elif ln.startswith("f "):
            idx = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
            for k in range(1, len(idx) - 1):          # 팬 삼각화
                F.append([idx[0], idx[k], idx[k + 1]])
    return np.array(V, float), np.array(F, int)


def normals(V, F):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(b - a, c - a)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ok = ln[:, 0] > 0
    n = np.where(ln > 0, n / np.where(ln == 0, 1, ln), 0.0)
    area = 0.5 * ln[:, 0]
    return n, area, ok


def main() -> None:
    rows = []
    for af, Nseen in sorted(N_SEEN.items()):
        d = os.path.join(ROOT, "assets", "meshes", "drones", af)
        print(f"═══ {af} — el 0° 에서 읽은 벌 수 N = {Nseen} ═══")
        best = []
        for p in sorted(glob.glob(os.path.join(d, "*.obj"))):
            V, F = read_obj(p)
            if F.size == 0:
                continue
            n, area, ok = normals(V, F)
            #: 시선은 x 축이다(방위 0·앙각 0 에서 레이다가 +x 쪽에 선다).
            #  시선에 «수직인 면» = 법선이 ±x 와 나란한 면.
            face_x = np.abs(n[:, 0]) > 0.999
            if not face_x.any():
                continue
            #: 그런 삼각형이 놓인 **평면**을 (법선 부호, x 오프셋) 으로 묶는다.
            off = np.round(V[F[face_x][:, 0]][:, 0], 4)
            sgn = np.sign(n[face_x][:, 0])
            planes = collections.Counter(zip(sgn.tolist(), off.tolist()))
            tot_area = float(area[face_x].sum())
            best.append((tot_area, os.path.basename(p), int(face_x.sum()),
                         len(planes), planes.most_common(4)))
        best.sort(reverse=True)
        for tot_area, name, ntri, npl, top in best[:4]:
            print(f"  {name:26s} 정면 삼각형 {ntri:4d} · 평면 {npl:3d} · "
                  f"넓이 {tot_area*1e4:8.2f} cm²")
            for (s, o), c in top:
                print(f"      법선 {'+x' if s > 0 else '−x'} · x={o:+.4f} m → 삼각형 {c}")
        if best:
            tot_area, name, ntri, npl, top = best[0]
            rows.append(dict(airframe=af, N_seen=Nseen, part=name,
                             n_tri_facing_x=ntri, n_planes=npl,
                             biggest_plane_tris=top[0][1] if top else None,
                             area_cm2=round(tot_area * 1e4, 2)))
        print()

    print("═══ 벌 수 N 과 메쉬 수의 대조 ═══")
    print(f"  {'기체':12s} {'N(관측)':>7s} {'가장 큰 부품':22s} {'정면삼각형':>9s} "
          f"{'평면수':>6s} {'최대평면 삼각형':>13s}")
    for x in rows:
        print(f"  {x['airframe']:12s} {x['N_seen']:7d} {x['part'][:22]:22s} "
              f"{x['n_tri_facing_x']:9d} {x['n_planes']:6d} {str(x['biggest_plane_tris']):>13s}")

    json.dump({"_meta": {
        "generator": "benchmark/facet_count_0903.py",
        "question_ko": "el 0° 낙차의 «벌 수 N» 이 메쉬의 무엇을 따라가나",
        "N_seen_ko": "outputs/el0_copies_0903.json 의 낙차 깊이에서 읽은 값",
        "geometry_ko": "시선은 x 축 — 법선이 ±x 와 0.999 이상 나란한 삼각형만 센다",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
