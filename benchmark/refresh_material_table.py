#!/usr/bin/env python
"""재질 표 — `src/materials.py` 를 읽어 `outputs/report1.json` 의 재질 블록을 다시 만든다.

무엇을 하는 스크립트인가
------------------------
02편 §1.2 "부품별 재질" 표는 두 엔진이 읽는 반사계수를 나란히 싣고, 그 숫자를
`report1.json : chamber.materials.<재질>.gamma_bulk / gamma_po` 에서 가져온다
(`src/make_report02_target.py:582`). 그 키를 쓰는 생산자는 `src/viz_report1.py` 의
`chamber` 블록 하나뿐인데, 파이프라인은 메쉬 블록(`--only mesh,cad`)만 돌린다 —
챔버는 리포트 6편에서 뺐기 때문이다(docs/REBUILD_2026-07-30.md §3).

그래서 이 스크립트가 **그 표만** materials.py 에서 직접 다시 계산해 같은 키에 넣는다.
`materials.py` 를 고치면 02편 표가 같이 움직인다. 2초, GPU 계산 없음.

값의 출처는 materials.py 함수 그대로다
--------------------------------------
  gamma_bulk = materials.gamma_bulk(k, fc)   Sionna RT 가 쓰는 벌크 Fresnel
  gamma_po   = materials.gamma_po(k, fc)     PO/SBR 이 쓰는 실효 반사계수
  eps_r, sigma, S = materials.material_params(k, fc)
  fc         = materials 함수의 기본 주파수 (여기서 손으로 적지 않고 서명에서 읽는다)

실행
----
  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/refresh_material_table.py
  → outputs/report1.json 의 chamber.materials · chamber.table · _provenance.materials 갱신
"""
from __future__ import annotations

import inspect
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick as _pick_gpu          # noqa: E402  ← mitsuba import 전에 부른다
_pick_gpu(verbose=False)

import materials as M                      # noqa: E402  (sionna.rt 를 끌고 온다)

JSON_OUT = os.path.join(ROOT, "outputs", "report1.json")

#: 메쉬·재질 소스 지문 — viz_report1.build_all 과 같은 형식으로 남긴다(부분 낡음 추적용).
SRC_FILES = ("src/materials.py", "src/drones.py", "src/drone_cad.py")


def _fc_default() -> float:
    """materials 함수의 기본 주파수를 서명에서 읽는다 — 숫자를 두 곳에 적지 않는다."""
    return float(inspect.signature(M.gamma_bulk).parameters["fc"].default)


def material_block(fc: float) -> dict:
    """`chamber.materials` 와 같은 모양의 표를 만든다 (viz_report1.measure_chamber 와 동일 키)."""
    out = {}
    for k, spec in M.MATERIALS.items():
        er, sg, S = M.material_params(k, fc)
        out[k] = dict(source="ITU" if "itu" in spec else "custom",
                      itu=spec.get("itu", ""), eps_r=float(er), sigma=float(sg),
                      S=float(S), gamma_bulk=float(M.gamma_bulk(k, fc)),
                      gamma_po=float(M.gamma_po(k, fc)), note=spec["note"])
    return out


def main() -> int:
    fc = _fc_default()
    mats = material_block(fc)

    J = {}
    if os.path.exists(JSON_OUT):
        with open(JSON_OUT, encoding="utf-8") as f:
            J = json.load(f)
    old = (J.get("chamber") or {}).get("materials") or {}

    moved = [(k, old[k]["gamma_po"], v["gamma_po"]) for k, v in mats.items()
             if k in old and abs(old[k]["gamma_po"] - v["gamma_po"]) > 1e-12]
    added = [k for k in mats if k not in old]
    gone = [k for k in old if k not in mats]

    ch = J.setdefault("chamber", {})
    ch["materials"] = mats
    ch["table"] = M.table(fc)
    prov = J.setdefault("_provenance", {})
    prov["materials"] = dict(
        stamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        producer="benchmark/refresh_material_table.py",
        fc_hz=fc,
        sources={rel: time.strftime("%Y-%m-%d %H:%M:%S",
                                    time.localtime(os.path.getmtime(os.path.join(ROOT, rel))))
                 for rel in SRC_FILES if os.path.exists(os.path.join(ROOT, rel))})

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)

    print(f"재질 {len(mats)}종 @ {fc/1e9:.2f} GHz → outputs/report1.json : chamber.materials")
    for k, a, b in moved:
        print(f"  · {k:16s} gamma_po {a:.4f} → {b:.4f}")
    if added:
        print(f"  + 새 재질: {', '.join(added)}")
    if gone:
        print(f"  - materials.py 에서 사라진 재질(02편이 인용 중이면 빌드가 멈춘다): {', '.join(gone)}")
    if not (moved or added or gone):
        print("  변화 없음 — 02편 §1.2 표는 그대로다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
