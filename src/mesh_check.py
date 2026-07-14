# -*- coding: utf-8 -*-
"""
mesh_check.py — **trimesh 로 메쉬를 검증한다** (자작 geom.py 가 못 잡는 것들)
==============================================================================
왜 필요한가 (2026-07-14)
  geom.py 는 의존성 없이 삼각형을 쌓는 도구다. 대신 **메쉬가 옳은지 검사할 능력이 없다.**
  실제로 조용히 살아 있던 버그:
    · prop_blade 의 **캡 2장이 뒤집혀 있었다**(법선 안쪽). 주석엔 "outward" 라고 적혀 있었다.
      → PO 의 조명 판정(n̂·û>0)이 그 면들을 **잘못 포함/제외**한다.
      → 프로펠러는 **마이크로도플러의 신호 그 자체**라 특히 민감하다.
  trimesh 는 이걸 1초 만에 잡는다. (설치 가능하다 — py312 는 사용자 소유 uv venv 다.
  geom.py 주석의 "설치 권한 없음" 은 **낡은 이유**였다.)

무엇을 검사하나 — **부품(연결요소) 단위**로. 드론은 프리미티브의 합집합이라 전체 메쉬는
원래 watertight 가 아니다. 의미 있는 검사는 **부품별** 검사다.
  1. watertight   : 부품이 닫힌 껍질인가 (구멍 없음)
  2. winding      : 이웃한 면들이 같은 방향으로 감겼는가
  3. 법선 방향    : 바깥을 향하는가 (닫힌 부품의 부호있는 부피 > 0)
  4. 퇴화면·중복정점

실행:  python src/mesh_check.py          (드론 5종 + 챔버 전수 검사)
       assert_ok() 를 빌드 파이프라인에서 부르면 회귀를 막는다.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _tm(v, f):
    import trimesh
    return trimesh.Trimesh(vertices=np.asarray(v, float),
                           faces=np.asarray(f, int), process=True)


def check_mesh(mesh, name="mesh") -> dict:
    """geom.Mesh → 부품별 검진 결과. 그룹(부위) 단위로 쪼개서 본다."""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g)
    groups = {}
    for grp in sorted(set(G.tolist())):
        f = F[G == grp]
        used = np.unique(f)
        remap = {int(o): i for i, o in enumerate(used)}
        tm = _tm(V[used], np.vectorize(remap.get)(f))
        comps = tm.split(only_watertight=False)
        n_wt = sum(1 for c in comps if c.is_watertight)
        n_inward = sum(1 for c in comps if c.is_watertight and c.volume < 0)
        n_badwind = sum(1 for c in comps if not c.is_winding_consistent)
        n_degen = int((tm.area_faces < 1e-14).sum())
        groups[grp] = dict(
            n_faces=int(len(f)), n_parts=len(comps),
            watertight=f"{n_wt}/{len(comps)}",
            inward_normals=n_inward, bad_winding=n_badwind, degenerate=n_degen,
            ok=(n_wt == len(comps) and n_inward == 0 and n_badwind == 0 and n_degen == 0),
        )
    return dict(name=name, groups=groups, ok=all(g["ok"] for g in groups.values()))


def report(res: dict) -> str:
    lines = [f"  {'그룹':10s} {'면':>6} {'부품':>5} {'watertight':>11} {'법선안쪽':>8} "
             f"{'winding깨짐':>11} {'퇴화면':>6}  판정"]
    for grp, g in res["groups"].items():
        lines.append(f"  {grp:10s} {g['n_faces']:6d} {g['n_parts']:5d} {g['watertight']:>11s} "
                     f"{g['inward_normals']:8d} {g['bad_winding']:11d} {g['degenerate']:6d}"
                     f"  {'✅' if g['ok'] else '❌'}")
    return "\n".join(lines)


def check_all(verbose=True) -> dict:
    """드론 5종 + 챔버 전수 검사."""
    from drones import DRONES, build_drone
    out = {}
    for k, s in DRONES.items():
        r = check_mesh(build_drone(s), k)
        out[k] = r
        if verbose:
            print(f"\n[{k}]  {'✅ 통과' if r['ok'] else '❌ 결함'}")
            print(report(r))
    return out


def assert_ok():
    """빌드 파이프라인용 — 결함이 있으면 예외를 던진다(회귀 방지)."""
    res = check_all(verbose=False)
    bad = {k: [g for g, v in r["groups"].items() if not v["ok"]]
           for k, r in res.items() if not r["ok"]}
    if bad:
        raise AssertionError(f"메쉬 검증 실패 — 결함 그룹: {bad}\n"
                             f"  python src/mesh_check.py 로 상세 확인")
    return True


if __name__ == "__main__":
    print("=" * 84)
    print("trimesh 메쉬 검증 — 부품(연결요소) 단위")
    print("=" * 84)
    res = check_all()
    n_ok = sum(1 for r in res.values() if r["ok"])
    print(f"\n{'='*84}\n결과: {n_ok}/{len(res)} 통과")
    if n_ok < len(res):
        sys.exit(1)
