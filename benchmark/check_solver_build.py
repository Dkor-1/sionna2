#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""솔버 판이 이름·도장·설치와 어긋나지 않나 — 상시 검사 (2026-09-14).

    CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/check_solver_build.py

왜 있나
-------
2026-09-09 에 sionna-rt 2.1.0 이 나왔고 릴리스 노트가 **재질(ITU-R P.2040-4)·회절 모형·
도플러 계산**을 함께 바꿨다고 적는다 — 곧 절대 레벨이 움직이는 판 갈이다.
⛔그런데 2026-09-14 아침까지 창고와 원장 어디에도 **어느 판으로 구웠나** 가 안 적혀 있었다.

판을 올리는 날 같은 칸에 두 판의 조각이 섞이면 `one_generation` 은 덮개가 넓은 쪽을 고를 뿐
상류가 무엇인지 모른다. 더 나쁜 것은 **이름이 같아 옛 샤드를 덮어쓰는 것**이다 —
2026-08-17 에 메쉬 수리로 똑같은 사고가 났다(이름이 같아 옛 샤드를 재사용, 재계산이 무효).

이 검사가 보는 것 넷
  ① `build_tag()` 가 판마다 옳은 꼬리표를 내나 (덮어쓰기를 막는 그 함수다)
  ② 문법이 그 꼬리표를 되읽고 되짓나
  ③ 창고 샤드의 **이름 꼬리표 ↔ 도장** 이 서로 맞나
  ④ 지금 설치된 판이 무엇이고, PathSolver 가 어떤 인자를 받나

⛔이 검사는 「2.1.0 이 옳다」거나 「2.0.1 이 틀렸다」를 말하지 않는다. 섞이지 않게만 한다.
"""
from __future__ import annotations

import glob
import inspect
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")


def _versions() -> dict:
    import importlib.metadata as md
    out = {}
    for n in ("sionna", "sionna-rt", "mitsuba", "drjit"):
        try:
            out[n] = md.version(n)
        except Exception:                                      # noqa: BLE001
            out[n] = "없음"
    return out


def check_build_tag() -> int:
    """① 판마다 옳은 꼬리표가 나오나 — **덮어쓰기를 막는 함수**라 여기가 제일 중요하다."""
    import elevation_sweep_md as esm
    base = esm.BUILD_BASELINE
    keep = esm.SOLVER_BUILD
    cases = [
        ("기준 판 그대로", base, ""),
        ("2.1.0", "sionna=2.1.0 sionna-rt=2.1.0 mitsuba=3.9.1 drjit=1.5.0", "_rt210"),
        ("2.2.0", "sionna=2.2.0 sionna-rt=2.2.0 mitsuba=3.9.1 drjit=1.5.0", "_rt220"),
        #: ⛔이름이 못 담는 차이 — 멈춰야 한다
        ("rt 는 그대로인데 mitsuba 만 움직임",
         "sionna=2.0.1 sionna-rt=2.0.1 mitsuba=3.9.1 drjit=1.3.1", SystemExit),
        ("sionna-rt 를 못 읽음",
         "sionna=2.0.1 sionna-rt=없음 mitsuba=3.8.0 drjit=1.3.1", SystemExit),
    ]
    bad = 0
    print("── ① build_tag() ──")
    for name, build, want in cases:
        esm.SOLVER_BUILD = build
        try:
            got = esm.build_tag()
        except SystemExit as e:
            got = SystemExit
            first = str(e).splitlines()[0]
        ok = (got is want) if want is SystemExit else (got == want)
        bad += not ok
        shown = "⛔멈춘다" if got is SystemExit else repr(got)
        print(f"  {'✅' if ok else '⛔'} {name:<32} → {shown}"
              + ("" if ok else f"  (바람 {want!r})"))
    esm.SOLVER_BUILD = keep
    return bad


def check_grammar() -> int:
    """② 문법이 꼬리표를 되읽고 되짓나 — ⛔꼬리표 없는 옛 이름도 그대로 읽혀야 한다."""
    from arm_grammar import parse, unparse, warnings_for
    tests = [
        ("sionna_p4000000000_swR0D0E0F1_r15_n8192_prf39400_envoutdoor01"
         "_mfixbatteryi5_blperairframe_rt210_d2", "210"),
        ("ours_r15_n8192_prf157600_mfixbatteryi5_rt210", "210"),
        ("sionna_p4000000000_swR0D0E0F1_r15_n8192_prf39400_envoutdoor01"
         "_mfixbatteryi5_blperairframe_d2", None),
    ]
    bad = 0
    print("── ② 문법 왕복 ──")
    for t, want in tests:
        try:
            f = parse(t)
            ok = unparse(f) == t and f.get("solver_build") == want
        except Exception as e:                                 # noqa: BLE001
            ok, f = False, {"오류": f"{type(e).__name__}: {e}"}
        bad += not ok
        print(f"  {'✅' if ok else '⛔'} 판 {f.get('solver_build')!r:>7}  {t[-56:]}")
    #: 처음 보는 판은 ⚠ 로만 — 막지 않는다
    w = warnings_for(parse("sionna_p4000000000_swR0D0E0F1_r15_n8192"
                           "_mfixbatteryi5_blperairframe_rt999_d2"))
    ok = bool(w)
    bad += not ok
    print(f"  {'✅' if ok else '⛔'} 처음 보는 판 rt999 → {w or '⛔경고가 나와야 한다'}")
    return bad


def check_shards(limit: int = 0) -> int:
    """③ 창고의 **이름 꼬리표 ↔ 도장** 이 맞나.

    ⛔도장이 없는 샤드는 «적히기 전 세대» 다 — 틀린 것이 아니라 안 적힌 것이다.
      그런 샤드는 이름에도 꼬리표가 없어야 한다(기준 판이라는 뜻).
    """
    from arm_grammar import ArmNameError, parse
    import re
    rx = re.compile(r"^(?P<arm>.+)_el(?P<el>[-+][\d.]+)_(?P<sh>\d+)\.npz$")
    paths = sorted(glob.glob(os.path.join(SHD, "*.npz")))
    if limit:
        paths = paths[:limit]
    n_stamp = n_none = 0
    bad = []
    for p in paths:
        m = rx.match(os.path.basename(p))
        if not m:
            continue
        try:
            tag = parse(m.group("arm")).get("solver_build")
        except ArmNameError:
            continue
        try:
            z = np.load(p, allow_pickle=True)
            stamp = str(z["solver_build"]) if "solver_build" in z.files else None
        except Exception as e:                                 # noqa: BLE001
            bad.append((p, f"못 읽음 {type(e).__name__}: {e}"))
            continue
        if stamp is None:
            n_none += 1
            if tag is not None:
                bad.append((p, f"도장이 없는데 이름에 판 꼬리표 _rt{tag} 가 있다"))
            continue
        n_stamp += 1
        rt = ""
        for part in stamp.split():
            if part.startswith("sionna-rt="):
                rt = part.split("=", 1)[1]
        want = None if rt == "2.0.1" else rt.replace(".", "")
        if tag != want:
            bad.append((p, f"이름 꼬리표 {tag!r} ↔ 도장 sionna-rt={rt!r}"))
    print("── ③ 창고 이름 ↔ 도장 ──")
    print(f"  샤드 {len(paths)} · 도장 있음 {n_stamp} · 도장 없음(적히기 전 세대) {n_none}"
          f" · ⛔어긋남 {len(bad)}")
    for p, why in bad[:12]:
        print(f"   ⛔ {os.path.basename(p)[-64:]}\n      {why}")
    return len(bad)


def show_env() -> None:
    """④ 지금 설치된 판과 PathSolver 가 받는 인자."""
    v = _versions()
    print("── ④ 지금 설치된 판 ──")
    for k, x in v.items():
        print(f"  {k:<10} {x}")
    try:
        from sionna.rt import PathSolver
        sig = inspect.signature(PathSolver.__init__)
        call = inspect.signature(PathSolver.__call__)
        print(f"  PathSolver.__init__{sig}")
        print(f"  PathSolver.__call__ 인자 "
              f"{[p for p in call.parameters if p != 'self']}")
        for want in ("deterministic", "rr_depth", "seed"):
            where = ("__init__" if want in sig.parameters else
                     "__call__" if want in call.parameters else None)
            print(f"  {'✅' if where else '⛔'} {want!r} "
                  + (f"→ {where} 에 있다" if where else "→ 없다"))
    except Exception as e:                                     # noqa: BLE001
        print(f"  ⚠PathSolver 를 못 봤다 ({type(e).__name__}: {e})")


def main() -> int:
    print("═══ 솔버 판 검사 ═══")
    show_env()
    bad = check_build_tag() + check_grammar() + check_shards()
    if bad:
        print(f"\n⛔어긋남 {bad} 곳 — 판이 섞일 수 있다. 굽기 전에 고쳐라.")
        return 1
    print("\n✅ 판 꼬리표·문법·창고 도장이 서로 맞는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
