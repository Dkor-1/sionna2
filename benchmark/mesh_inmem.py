# -*- coding: utf-8 -*-
"""
mesh_inmem.py — 메쉬를 **디스크를 안 거치고** 바로 Mitsuba 로 올린다 (2026-08-20)
================================================================================

무엇을 없애나
-------------
지금 자세 루프는 정점 191 kB 를 GPU 로 보내려고 이런 길을 간다:

    numpy float64
      → 파이썬 float 튜플로 하나씩 변환   `articulated_fast.py:65 to_mesh()`   34.9 ms
      → 십진 텍스트 "%.6f" 로 찍기        `geom.py:243 write_obj`              28.3 ms
      → 디스크에 983 kB 쓰기
      → Mitsuba OBJ 파서가 텍스트를 다시 읽기                                   ~4.7 ms
      → GPU 버퍼                          ← **진짜 왕복은 여기, 0.02 ms**

즉 **왕복은 0.02 ms 인데 그 앞에 63 ms 짜리 우회로**가 서 있다. 이 모듈이 그 우회로를 뺀다.

⭐값이 안 바뀌는 이유 — 두 가지를 그대로 흉내낸다
------------------------------------------------
  ① **정점 반올림.** OBJ 는 `%.6f` 로 쓰므로 소수 6 자리에서 잘린다.
     그냥 float64 를 올리면 **더 정확해져서** 옛 샤드와 값이 달라진다.
     ⇒ 일부러 같은 자리에서 반올림한다. (더 정확한 게 «같은» 것보다 나쁘다 — 회귀가 깨진다)
  ② **정점 재번호 순서.** `write_obj` 는 면을 훑으며 «처음 나온 순서» 로 정점을 다시 매긴다.
     Mitsuba 가 읽는 순서가 그 순서다. 순서가 달라지면 정점 배열이 달라진다.
     ⇒ 같은 규칙으로 번호를 매긴다.

⛔**기본값이 아니다.** 이 모듈은 불러야만 쓰인다. 옛 경로는 그대로 두어
   인자를 안 주면 기존 샤드와 같은 길을 간다.

검증: `python benchmark/mesh_inmem.py <기체>` → OBJ 경로와 정점·면을 **비트 대조**한다.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#: OBJ 가 쓰는 소수 자릿수 — `src/geom.py:243` 의 `f"v {x:.6f} ..."` 와 같아야 한다
OBJ_DECIMALS = 6


def group_layout(faces: np.ndarray, groups, group_name: str):
    """한 그룹의 (쓰이는 정점 색인, 그 그룹 면의 지역 색인) — **OBJ 와 같은 순서**로.

    `geom.Mesh.write_obj` 의 재번호 규칙을 그대로 옮긴 것이다::

        remap = {}; used = []
        for fi in keep:                      # 그룹에 속한 면을 원래 순서대로
            for vi in self.f[fi]:            # 면의 세 꼭짓점을 순서대로
                if vi not in remap:          # 처음 보면 다음 번호를 준다
                    remap[vi] = len(used); used.append(vi)

    ⚠순서를 바꾸면 정점 배열이 달라져 **옛 샤드와 값이 안 맞는다.**
    """
    keep = [i for i, g in enumerate(groups) if g == group_name]
    remap: dict[int, int] = {}
    used: list[int] = []
    loc = np.empty((len(keep), 3), np.uint32)
    for r, fi in enumerate(keep):
        for c, vi in enumerate(faces[fi]):
            vi = int(vi)
            j = remap.get(vi)
            if j is None:
                j = remap[vi] = len(used)
                used.append(vi)
            loc[r, c] = j
    return np.asarray(used, np.int64), loc


class InMemGroups:
    """자세가 바뀌어도 **안 변하는 것**을 한 번만 계산해 두고, 자세마다 정점만 갱신한다.

    안 변하는 것: 면 연결 · 그룹 분할 · 정점 재번호표.
    `articulated_fast.FastPoser` 가 자세마다 같은 `f`·`g` 객체를 돌려주므로 구조적으로 보장된다
    (`src/articulated_fast.py:120-126, 147`).
    """

    def __init__(self, faces: np.ndarray, groups, group_names=None, *,
                 decimals: int = OBJ_DECIMALS):
        self.faces = np.asarray(faces)
        self.groups = list(groups)
        self.decimals = int(decimals)
        names = group_names if group_names is not None else sorted(set(self.groups))
        self.names = [g for g in names if any(x == g for x in self.groups)]
        self.layout = {g: group_layout(self.faces, self.groups, g) for g in self.names}

    # ── 정점 ────────────────────────────────────────────────────────────
    def vertices_for(self, v: np.ndarray, group: str) -> np.ndarray:
        """그룹의 정점 (n,3) float32 — ⭐OBJ 와 **같은 자리에서 반올림**해서 돌려준다."""
        used, _ = self.layout[group]
        vv = np.asarray(v, np.float64)[used]
        # ⭐`%.6f` 로 찍었다가 다시 읽는 것과 같은 값이 되게 자른다.
        #   반올림을 빼면 «더 정확한» 값이 나오는데, 그러면 옛 샤드와 안 맞는다.
        return np.round(vv, self.decimals).astype(np.float32)

    def faces_for(self, group: str) -> np.ndarray:
        return self.layout[group][1].ravel().astype(np.uint32)

    # ── Mitsuba ─────────────────────────────────────────────────────────
    def make_mesh(self, mi, v: np.ndarray, group: str, name: str | None = None):
        """`mi.Mesh` 하나를 만들어 돌려준다(정점 채운 상태)."""
        used, loc = self.layout[group]
        nv, nf = len(used), len(loc)
        m = mi.Mesh(name or f"g_{group}", vertex_count=nv, face_count=nf,
                    has_vertex_normals=False, has_vertex_texcoords=False)
        p = mi.traverse(m)
        p["faces"] = mi.UInt32(self.faces_for(group))
        p["vertex_positions"] = mi.Float(self.vertices_for(v, group).ravel())
        p.update()
        return m, p

    def update_vertices(self, mi, params, v: np.ndarray, group: str) -> None:
        """이미 만든 메쉬의 정점만 갈아 끼운다(면은 안 건드린다)."""
        params["vertex_positions"] = mi.Float(self.vertices_for(v, group).ravel())
        params.update()


# ────────────────────────────────────────────────────────────────────────────
def verify(drone_key: str = "matrice4e", n_poses: int = 3) -> dict:
    """⭐OBJ 경로와 인메모리 경로가 **비트 단위로 같은지** 대조한다.

    OBJ 를 실제로 쓰고 파서로 다시 읽어, 정점·면을 인메모리 판과 견준다.
    """
    import tempfile
    import time
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES

    spec = DRONES[drone_key]
    fp = FastPoser(spec)
    _r = getattr(spec, "rpms", None)
    rpms = np.asarray(_r if _r is not None else [spec.hover_rpm] * len(fp.dirs), float)
    ph = rotor_phases(np.arange(n_poses) / 19700.0, rpms, fp.dirs)

    rows, t_obj, t_mem = [], 0.0, 0.0
    lay = None
    with tempfile.TemporaryDirectory() as td:
        for j in range(n_poses):
            mv = fp.pose(ph[j])
            if lay is None:
                lay = InMemGroups(mv.f, mv.g)

            t0 = time.perf_counter()
            m = mv.to_mesh()
            paths = m.write_obj_per_group(os.path.join(td, f"p{j}"), spec.key)
            t_obj += time.perf_counter() - t0

            t0 = time.perf_counter()
            mem = {g: (lay.vertices_for(mv.v, g), lay.faces_for(g)) for g in lay.names}
            t_mem += time.perf_counter() - t0

            for g, pth in paths.items():
                vs, fs = [], []
                for ln in open(pth):
                    if ln.startswith("v "):
                        vs.append([float(x) for x in ln.split()[1:4]])
                    elif ln.startswith("f "):
                        fs.append([int(x) - 1 for x in ln.split()[1:4]])
                vo = np.asarray(vs, np.float32)
                fo = np.asarray(fs, np.uint32).ravel()
                vm, fm = mem[g]
                rows.append(dict(pose=j, group=g, n_v=len(vo), n_f=len(fo) // 3,
                                 v_bit_equal=bool(vo.shape == vm.shape
                                                  and (vo.tobytes() == vm.tobytes())),
                                 f_equal=bool(fo.shape == fm.shape and np.array_equal(fo, fm))))
    bad = [r for r in rows if not (r["v_bit_equal"] and r["f_equal"])]
    return dict(drone=drone_key, n_poses=n_poses, n_checks=len(rows),
                n_mismatch=len(bad), mismatches=bad[:10],
                obj_ms_per_pose=round(t_obj / n_poses * 1000, 2),
                inmem_ms_per_pose=round(t_mem / n_poses * 1000, 3),
                speedup=(None if t_mem <= 0 else round(t_obj / t_mem, 1)))


if __name__ == "__main__":
    import json
    key = sys.argv[1] if len(sys.argv) > 1 else "matrice4e"
    r = verify(key, int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    print(json.dumps({k: v for k, v in r.items() if k != "mismatches"},
                     ensure_ascii=False, indent=1))
    if r["n_mismatch"]:
        print("⛔ 불일치:", json.dumps(r["mismatches"], ensure_ascii=False, indent=1))
    else:
        print(f"✅ {r['n_checks']} 건 전부 비트 동일 · "
              f"{r['obj_ms_per_pose']} → {r['inmem_ms_per_pose']} ms/자세 ({r['speedup']}배)")
