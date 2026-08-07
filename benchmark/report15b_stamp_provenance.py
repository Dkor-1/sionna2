# -*- coding: utf-8 -*-
"""
report15b_stamp_provenance.py — 산출물이 **어떤 메쉬로 계산됐는지** 스스로 적게 한다.

왜 필요한가
------------
2026-08-03 에 같은 종류의 사고가 있었다(`docs/RETRACTION_LOG.md` R15) — σ 앵커가
어떤 메쉬로 계산됐는지 자기 안에 안 적어 둬서, 나중에 «낡았나 아닌가» 를 판정할 수 없었다.
그래서 그 뒤로 무거운 산출물은 **자기가 쓴 메쉬의 지문**을 함께 적는다.

⚠ 이번 라운드는 특히 위험했다 — 메쉬 게이트가 `src/drones.py`·`src/drone_cad.py` 를
  **14:56 에 고쳤고**, 마이크로도플러 재계산은 **16:00 에 시작**했다. 64분 차이라 안전하지만,
  그 사실이 산출물 안에 적혀 있지 않으면 나중에 확인할 방법이 없다.

    python benchmark/report15b_stamp_provenance.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import numpy as np                                                     # noqa: E402
from drones import DRONES, build_drone                                 # noqa: E402

TARGET = os.path.join(ROOT, "outputs", "report15b_microdoppler.json")
SRC_FILES = ("src/drones.py", "src/geom.py", "src/materials.py",
             "src/drone_cad.py", "src/rcs_sbr.py", "src/microdoppler.py",
             "src/articulated_fast.py")


def _sha_file(rel: str) -> dict:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return {"missing": True}
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    return {"sha256_16": h, "mtime": time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p)))}


def mesh_provenance(drone_keys) -> dict:
    src = {rel: _sha_file(rel) for rel in SRC_FILES}
    built = {}
    for key in drone_keys:
        m = build_drone(DRONES[key])
        h = hashlib.sha256()
        h.update(np.asarray(m.v, dtype=np.float32).tobytes())
        h.update(np.asarray(m.f, dtype=np.int32).tobytes())
        built[key] = {"sha256_16": h.hexdigest()[:16],
                      "n_vert": len(m.v), "n_tri": len(m.f)}
    return {
        "note_ko": "이 산출물이 **어떤 메쉬로** 계산됐는지의 지문. "
                   "built_mesh 해시가 현재 메쉬와 다르면 이 파일은 낡았다.",
        "source_sha256_16": src,
        "built_mesh": built,
        "stamped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def main():
    res = json.load(open(TARGET))
    keys = sorted({c["drone"] for c in res["cells"].values()})
    prov = mesh_provenance(keys)

    # 산출 시각과 소스 수정 시각을 맞대 본다 — 계산 중에 메쉬가 바뀌었나
    gen = res["_meta"].get("generated", "")
    newer = [rel for rel, d in prov["source_sha256_16"].items()
             if not d.get("missing") and gen and d["mtime"] > gen]
    prov["sources_modified_after_run_started"] = newer
    prov["verdict_ko"] = (
        "⚠ 계산 시작 뒤에 바뀐 소스가 있다 — 이 산출물은 섞였을 수 있다: " + ", ".join(newer)
        if newer else
        "✅ 계산 시작 시각보다 나중에 바뀐 소스가 없다. 한 벌의 메쉬로 끝까지 돌았다.")

    res["mesh_provenance"] = prov
    with open(TARGET, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)

    print(f"  산출 시각 {gen}")
    for rel, d in prov["source_sha256_16"].items():
        if not d.get("missing"):
            print(f"    {rel:28s} {d['sha256_16']}  {d['mtime']}")
    for k, d in prov["built_mesh"].items():
        print(f"    메쉬 {k:12s} {d['sha256_16']}  정점 {d['n_vert']:6d}  삼각형 {d['n_tri']:6d}")
    print(f"  {prov['verdict_ko']}")
    print(f"  ✅ {TARGET}")


if __name__ == "__main__":
    main()
