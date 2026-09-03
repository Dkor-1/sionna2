# -*- coding: utf-8 -*-
"""
hit_triangle_0903.py — 같은 줄이 여러 번 적히는 «횟수» 가 무엇을 따라가나.

실마리
    정면(el 0°)에서 목록 맨 위 줄이 기체마다 이렇게 적힌다 —
      mini5pro 2 번 · matrice4e 3 번 · mavic4pro 4 번
    그런데 **그 한 줄의 세기는 기체가 달라도 거의 같다**
      2.283565e−04 · 2.298327e−04 · 2.287632e−04 (0.6 % 안)

    면이 다른데 세기가 같다 ⇒ 그 한 줄은 «면 전체의 되돌림» 이 아니라
    **광선 한 다발의 몫**일 수 있다. 그렇다면 **횟수가 면 넓이를 따라가야** 한다.

이 스크립트
    경로 덤프가 적어 둔 **물체 id 와 삼각형 id** 로 그 삼각형을 메쉬에서 찾아
      · 그 삼각형의 넓이
      · 시선(x 축)에 정사영한 넓이
    를 재고, 기체 사이 비를 «적히는 횟수» 의 비와 견준다.

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=benchmark \\
        ~/.venvs/py312/bin/python benchmark/hit_triangle_0903.py --dumps <dir> ...
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "outputs", "hit_triangle_0903.json")


def read_obj(p: str):
    V, F = [], []
    for ln in open(p, encoding="utf-8", errors="replace"):
        if ln.startswith("v "):
            V.append([float(x) for x in ln.split()[1:4]])
        elif ln.startswith("f "):
            idx = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
            for k in range(1, len(idx) - 1):
                F.append([idx[0], idx[k], idx[k + 1]])
    return np.array(V, float), np.array(F, int)


def main() -> None:
    sys.path.insert(0, HERE)
    from elephant_id_0903 import load, amp

    ap = argparse.ArgumentParser()
    ap.add_argument("--dumps", nargs="+", required=True)
    a = ap.parse_args()

    rows = []
    for d in a.dumps:
        fs = sorted(glob.glob(os.path.join(d, "pose*_el*.npz")))
        if not fs:
            continue
        z = load(fs[0])
        A = amp(z)
        top = float(A.max())
        k = np.where(np.abs(A - top) / top < 1e-6)[0]
        oid = int(z["obj"][0, k[0]])
        pid = int(z["primitives"][0, k[0]])
        names = {int(i): str(n) for i, n in zip(z["oid"], z["oname"])}
        part = names.get(oid, str(oid))
        af = next((x for x in ("mini5pro", "mavic4pro", "matrice4e")
                   if x in part or x in d), "?")
        #: 부품 이름은 «<기체>_<그룹>» 꼴 — OBJ 는 «<기체>__<그룹>.obj» 다
        grp = part.split("_", 1)[1] if "_" in part else part
        objp = os.path.join(ROOT, "assets", "meshes", "drones", af, f"{af}__{grp}.obj")
        area = proj = ntri = None
        if os.path.exists(objp):
            V, F = read_obj(objp)
            ntri = int(F.shape[0])
            if 0 <= pid < ntri:
                t = V[F[pid]]
                n = np.cross(t[1] - t[0], t[2] - t[0])
                area = float(0.5 * np.linalg.norm(n))
                proj = float(0.5 * abs(n[0]))          # x 축(시선)에 정사영
        print(f"═══ {af} ═══")
        print(f"  적히는 횟수 {k.size} · 한 줄 세기 {top:.6e}")
        print(f"  부품 {part} (물체 {oid}) · 삼각형 {pid} / {ntri}")
        if area is not None:
            print(f"  그 삼각형 넓이 {area*1e4:.4f} cm² · 시선 정사영 {proj*1e4:.4f} cm²")
        else:
            print(f"  ⛔메쉬에서 그 삼각형을 못 찾았다 — {os.path.relpath(objp, ROOT)}")
        rows.append(dict(airframe=af, n_rows=int(k.size), abs_a=top, part=part,
                         obj_id=oid, prim_id=pid, n_tri_in_part=ntri,
                         area_cm2=(area * 1e4) if area else None,
                         proj_area_cm2=(proj * 1e4) if proj else None))
        print()

    ok = [r for r in rows if r["proj_area_cm2"]]
    if len(ok) > 1:
        ok.sort(key=lambda r: r["n_rows"])
        b = ok[0]
        print("═══ 횟수의 비 ↔ 넓이의 비 ═══")
        print(f"  {'기체':12s} {'횟수':>4s} {'횟수비':>7s} {'정사영 cm²':>11s} {'넓이비':>7s} "
              f"{'한 줄 세기':>13s}")
        for r in ok:
            print(f"  {r['airframe']:12s} {r['n_rows']:4d} {r['n_rows']/b['n_rows']:7.3f} "
                  f"{r['proj_area_cm2']:11.4f} {r['proj_area_cm2']/b['proj_area_cm2']:7.3f} "
                  f"{r['abs_a']:13.6e}")
        print("  ⇒ 두 비가 같으면 «한 줄 = 광선 한 다발의 몫» 이고 합이 옳다.")
        print("    다르면 그 읽기는 못 쓴다.")

    json.dump({"_meta": {
        "generator": "benchmark/hit_triangle_0903.py",
        "question_ko": "같은 줄이 적히는 횟수가 그 삼각형의 넓이를 따라가나",
        "why_ko": "한 줄의 세기가 기체와 무관하게 거의 같다 — 면 전체가 아니라 "
                  "광선 한 다발의 몫일 수 있다. 그러면 횟수가 넓이를 따라가야 한다.",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
