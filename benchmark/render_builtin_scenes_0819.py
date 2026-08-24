# -*- coding: utf-8 -*-
"""
render_builtin_scenes_0819.py — Sionna 2.0.1 이 기본으로 주는 씬을 **그려서 본다**
================================================================================

무엇을 위해
-----------
환경(바닥·벽·도심)을 넣으려는데, 무엇이 이미 있는지 **눈으로** 확인한다.
Sionna 2.0.1 설치본은 씬 16 개를 들고 있고 그중 넷은 **실제 도시**다(뮌헨·파리·피렌체·SF).

규약
----
  · 카메라는 씬 bbox 로 자동 배치한다 — 씬 규모가 4 m 부터 2 km 까지 제각각이다.
    비스듬히 내려다보는 각(45°)으로 통일해 서로 비교할 수 있게 한다.
  · 그림 안 글자는 **영어**(저장소 규약). 파일 이름에 씬 이름을 그대로 쓴다.
  · 삼각형 수·크기를 함께 재서 캡션에 남긴다 — 그림만 보면 규모를 못 읽는다.

⛔GPU 1 장. 산출: outputs/figs_builtin_scenes/*.png + outputs/builtin_scenes_0819.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIGD = os.path.join(ROOT, "outputs", "figs_builtin_scenes")
OUT = os.path.join(ROOT, "outputs", "builtin_scenes_0819.json")

#: (씬 이름, 한국어 설명, 영어 캡션)
SCENES = [
    ("floor_wall",      "바닥 + 벽 한 장",        "floor + one wall"),
    ("box",             "닫힌 상자",              "closed box"),
    ("simple_wedge",    "쐐기 (회절 시험용)",      "wedge (diffraction test)"),
    ("simple_reflector", "반사판 한 장",           "single reflector"),
    ("double_reflector", "반사판 두 장",           "two reflectors"),
    ("triple_reflector", "반사판 세 장",           "three reflectors"),
    ("box_one_screen",  "상자 + 가림막 1",         "box + one screen"),
    ("box_two_screens", "상자 + 가림막 2",         "box + two screens"),
    ("box_knife",       "상자 + 칼날 모서리",      "box + knife edge"),
    ("simple_street_canyon", "도심 협곡 (건물 6채)", "street canyon (6 buildings)"),
    ("simple_street_canyon_with_cars", "도심 협곡 + 자동차", "street canyon + cars"),
    ("etoile",          "파리 개선문 일대 (실제)",  "Paris, Place de l'Etoile (real)"),
    ("munich",          "뮌헨 시가지 (실제)",      "Munich city centre (real)"),
    ("florence",        "피렌체 (실제)",           "Florence (real)"),
    ("san_francisco",   "샌프란시스코 (실제)",      "San Francisco (real)"),
]

RES = (900, 640)
NSAMP = 96


def main():
    import sionna.rt as rt
    os.makedirs(FIGD, exist_ok=True)
    t00 = time.time()
    rows, failed = {}, []

    for name, ko, en in SCENES:
        try:
            sc = rt.load_scene(getattr(rt.scene, name))
            bb = sc.mi_scene.bbox()
            lo, hi = np.array(bb.min, float), np.array(bb.max, float)
            ctr = 0.5 * (lo + hi)
            ext = hi - lo
            span = float(max(ext[0], ext[1]))
            # ⭐45° 로 비스듬히 내려다본다 — 씬 규모에 비례한 거리에서
            d = max(span * 1.1, 6.0)
            cam = rt.Camera(position=[float(ctr[0] - d * 0.75), float(ctr[1] - d * 0.75),
                                      float(ctr[2] + d * 0.75)],
                            look_at=[float(ctr[0]), float(ctr[1]), float(ctr[2])])
            png = os.path.join(FIGD, f"{name}.png")
            sc.render_to_file(camera=cam, filename=png, resolution=RES, num_samples=NSAMP)

            ntri = sum(int(s.face_count()) for s in sc.mi_scene.shapes()
                       if hasattr(s, "face_count"))
            mats = sorted(sc.radio_materials.keys())
            rows[name] = dict(
                label_ko=ko, caption_en=en, png=os.path.relpath(png, ROOT),
                n_triangles=ntri, n_objects=len(sc.objects),
                extent_m=[round(float(v), 1) for v in ext],
                span_m=round(span, 1), materials=mats,
                png_kb=round(os.path.getsize(png) / 1024, 1))
            print(f"  ✅ {name:32s} tri {ntri:8,d}  {ext[0]:7.0f}×{ext[1]:7.0f}×{ext[2]:6.0f} m"
                  f"  재질 {len(mats)}")
        except Exception as e:                                     # noqa: BLE001
            failed.append(dict(scene=name, err=str(e)[:200]))
            print(f"  ⛔ {name:32s} {str(e)[:90]}")

    doc = {"_meta": {
        "generator": "benchmark/render_builtin_scenes_0819.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "Sionna 2.0.1 내장 씬을 렌더해 무엇이 이미 있는지 눈으로 확인한다",
        "gpu_used": True, "sionna": __import__("sionna").__version__,
        "camera_ko": "bbox 중심을 45° 비스듬히 내려다봄 · 거리는 씬 규모 비례",
        "elapsed_s": round(time.time() - t00, 1)},
        "scenes": rows, "failed": failed}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\n  {len(rows)} 개 렌더 · saved {FIGD}")


if __name__ == "__main__":
    main()
