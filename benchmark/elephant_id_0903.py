# -*- coding: utf-8 -*-
"""
elephant_id_0903.py — 낙차 자세에서 «빠진 그 경로» 의 정체를 밝힌다.

무엇을 보았나
    실외 낙차 칸(envoutdoor01 · az 45 · el 0 · R0D0E0F1)의 자세 14·15·16 을 통째로 덤프하니

        자세 14 (정상)  경로 1526 · 최대 |a| 6.711507e−05 · |E| 6.775e−05
        자세 15 (낙차)  경로 1521 · 최대 |a| 6.967173e−09 · |E| 8.390e−07
        자세 16 (정상)  경로 1520 · 최대 |a| 6.711507e−05 · |E| 6.775e−05

    ⭐정상 자세에서는 **경로 하나가 에너지를 사실상 전부** 진다(최대 |a| = 비간섭 합).
      그리고 그 값이 자세 14 와 16 에서 **일곱 자리까지 같다** — 자세와 무관한 «고정된 하나».
    ⭐낙차 자세에서는 그 하나가 **네 자릿수(≈ −80 dB) 아래**로 사라진다.
      「있는데 진폭이 0 에 가깝다」가 아니라 **목록에 없다**.

이 스크립트
    세 자세의 경로 목록을 지연(tau)으로 맞춰 놓고
      · 정상 자세에 있는데 낙차 자세에 **없는** 경로를 찾아
      · 그 지연·물체 열·진폭을 적는다. 지연에서 **기하**(몇 m 를 돌아왔나)를 읽는다.

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" ~/.venvs/py312/bin/python benchmark/elephant_id_0903.py \\
        --dir /tmp/.../pathdump
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re

import numpy as np

C = 2.99792458e8
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "outputs", "elephant_id_0903.json")


def load(f: str) -> dict:
    z = np.load(f)
    d = {k: z[k] for k in z.files}
    m = d.get("meta")
    if m is not None:
        d["pose"], d["el"], d["n_ret"], d["n_hit"] = int(m[0]), float(m[1]), int(m[2]), int(m[3])
    return d


def amp(d: dict) -> np.ndarray:
    """|a| — 덤프는 실수부·허수부를 따로 담는다."""
    if "a_re" in d:
        return np.abs(np.asarray(d["a_re"]) + 1j * np.asarray(d["a_im"]))
    a = d.get("a")
    if a is None:
        return np.zeros(0)
    a = np.asarray(a)
    return np.abs(a if np.iscomplexobj(a) else a[0] + 1j * a[1])


def describe(d: dict, k: int) -> str:
    """경로 하나의 정체 — 물체 이름·상호작용·정점을 사람 말로."""
    names = {int(i): str(n) for i, n in zip(d["oid"], d["oname"])} if "oid" in d else {}
    #: ⭐설치본에서 읽는다 — 손으로 적었더니 틀렸다(굴절 4·회절 8 인데 3·4 로 적었다).
    try:
        from sionna.rt.constants import InteractionType as _IT
        KO = {"NONE": "없음", "SPECULAR": "정반사", "DIFFUSE": "확산",
              "REFRACTION": "굴절", "DIFFRACTION": "회절"}
        KIND = {int(getattr(_IT, n)): KO.get(n, n) for n in dir(_IT) if n.isupper()}
    except Exception:
        KIND = {0: "없음", 1: "정반사", 2: "확산", 4: "굴절", 8: "회절"}
    out = []
    for dep in range(d["obj"].shape[0]):
        o = int(d["obj"][dep, k])
        it = int(d["interactions"][dep, k]) if "interactions" in d else -1
        if o < 0:
            continue
        v = d["vertices"][dep, k] if "vertices" in d else None
        vs = f" @({v[0]:+.2f},{v[1]:+.2f},{v[2]:+.2f})" if v is not None else ""
        out.append(f"{KIND.get(it, it)}→{names.get(o, o)}{vs}")
    return " · ".join(out) if out else "(상호작용 없음 — 직접파)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--drop-pose", type=int, default=15)
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, "pose*_el*.npz")))
    if not files:
        raise SystemExit(f"⛔덤프가 없다: {a.dir}")
    D = {}
    for f in files:
        m = re.search(r"pose(\d+)_el", os.path.basename(f))
        D[int(m.group(1))] = load(f)

    print(f"═══ 덤프 {len(D)} 자세 — {sorted(D)} ═══")
    print(f"  {'자세':>5} {'경로':>6} {'최대 |a|':>14} {'|E|':>14} {'열쇠':>34}")
    for p in sorted(D):
        d = D[p]
        A = amp(d)
        E = d.get("E")
        Ea = abs(complex(E[0], E[1])) if E is not None else float("nan")
        print(f"  {p:5d} {A.size:6d} {A.max() if A.size else 0:14.6e} {Ea:14.6e} "
              f"{str(sorted(d.keys()))[:34]:>34}")

    if a.drop_pose not in D:
        raise SystemExit(f"⛔낙차 자세 {a.drop_pose} 덤프가 없다")
    ref = [p for p in sorted(D) if p != a.drop_pose]
    if not ref:
        raise SystemExit("⛔견줄 정상 자세가 없다")

    dd = D[a.drop_pose]
    tau_d = np.asarray(dd["tau"]).ravel()
    cells = []
    print(f"\n═══ 정상 자세에 있는데 낙차 자세({a.drop_pose})에 없는 경로 ═══")
    for p in ref:
        d = D[p]
        A, T = amp(d), np.asarray(d["tau"]).ravel()
        order = np.argsort(-A)
        print(f"\n  ── 자세 {p} 의 가장 센 경로 다섯 ──")
        print(f"  {'순위':>4} {'|a|':>14} {'지연 ns':>10} {'거리 m':>9} "
              f"{'낙차 자세에 같은 지연?':>22}")
        for r, k in enumerate(order[:5]):
            near = np.min(np.abs(tau_d - T[k])) if tau_d.size else np.inf
            same = near < 1e-12
            print(f"  {r+1:4d} {A[k]:14.6e} {T[k]*1e9:10.3f} {T[k]*C:9.3f} "
                  f"{('있다' if same else f'없다 (가장 가까운 것 {near*1e9:.3f} ns)'):>22}")
            if r == 0:
                print(f"       정체: {describe(d, k)}")
                if "tx" in d and "rx" in d:
                    print(f"       송신 {np.asarray(d['tx']).ravel()} · "
                          f"수신 {np.asarray(d['rx']).ravel()}")
                cells.append(dict(ref_pose=p, drop_pose=a.drop_pose,
                                  top_abs_a=float(A[k]), tau_s=float(T[k]),
                                  path_len_m=float(T[k] * C),
                                  present_in_drop=bool(same),
                                  nearest_tau_gap_ns=float(near * 1e9)))

    Ad = amp(dd)
    print(f"\n═══ 낙차 자세 {a.drop_pose} ═══")
    print(f"  경로 {Ad.size} · 최대 |a| {Ad.max() if Ad.size else 0:.6e}")
    for p in ref:
        A = amp(D[p])
        if A.size and Ad.size:
            print(f"  자세 {p} 대비 최대 |a| 비 = {Ad.max()/A.max():.3e} "
                  f"({20*np.log10(Ad.max()/A.max()):+.1f} dB)")

    json.dump({"_meta": {
        "generator": "benchmark/elephant_id_0903.py",
        "question_ko": "낙차 자세에서 빠진 그 경로가 무엇인가 — 목록에 없나, 있는데 0 인가",
        "dump_dir": a.dir,
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "cells": cells}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
