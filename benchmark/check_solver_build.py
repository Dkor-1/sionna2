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
import json
import os
import tempfile
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
    """① 판마다 옳은 꼬리표가 나오나 — **덮어쓰기·건너뛰기를 막는 함수**라 여기가 제일 중요하다.

    ⛔⛔2026-09-14 적대 검증이 잡은 것 둘을 여기서 시험한다:
      ⓐ 문지기가 **기준 판일 때만** 섰다 — 올린 뒤 mitsuba·drjit 가 따로 움직여도 안 섰다.
      ⓑ 빌더가 **자기가 지은 이름을 되읽어 보지 않았다** — rc·post 판이면 문법이 못 읽는다.
    """
    import elevation_sweep_md as esm
    base = esm.BUILD_BASELINE
    keep_b, keep_r = esm.SOLVER_BUILD, esm.BUILD_REGISTRY
    B210 = "sionna=2.1.0 sionna-rt=2.1.0 mitsuba=3.9.1 drjit=1.5.0"
    #: ⛔장부를 임시 파일로 돌려 **운영 장부를 건드리지 않는다**
    fd, reg = tempfile.mkstemp(prefix="solverbuilds_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"builds": {"_rt210": B210}}, f)
    esm.BUILD_REGISTRY = reg

    cases = [
        ("기준 판 그대로", base, ""),
        ("2.1.0 · 장부와 같다", B210, "_rt210"),
        #: ⭐ⓐ 같은 꼬리표인데 판 묶음이 다르다 — 이름이 겹쳐 옛 샤드를 건너뛴다
        ("2.1.0 인데 mitsuba 만 움직임",
         "sionna=2.1.0 sionna-rt=2.1.0 mitsuba=3.9.5 drjit=1.5.0", SystemExit),
        ("2.1.0 인데 drjit 만 움직임",
         "sionna=2.1.0 sionna-rt=2.1.0 mitsuba=3.9.1 drjit=1.7.0", SystemExit),
        ("장부에 없는 판(2.2.0)",
         "sionna=2.2.0 sionna-rt=2.2.0 mitsuba=3.9.1 drjit=1.5.0", SystemExit),
        #: ⭐ⓑ 문법이 못 읽는 꼬리표
        ("정식 판이 아닌 것(2.1.0rc1)",
         "sionna=2.1.0rc1 sionna-rt=2.1.0rc1 mitsuba=3.9.1 drjit=1.5.0", SystemExit),
        ("정식 판이 아닌 것(2.1.0.post1)",
         "sionna=2.1.0 sionna-rt=2.1.0.post1 mitsuba=3.9.1 drjit=1.5.0", SystemExit),
        ("이름이 못 담는 차이(기준 rt + 다른 꾸러미)",
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
        except SystemExit:
            got = SystemExit
        ok = (got is want) if want is SystemExit else (got == want)
        bad += not ok
        shown = "⛔멈춘다" if got is SystemExit else repr(got)
        print(f"  {'✅' if ok else '⛔'} {name:<34} → {shown}"
              + ("" if ok else f"  (바람 {want!r})"))
    esm.SOLVER_BUILD, esm.BUILD_REGISTRY = keep_b, keep_r
    try:
        os.remove(reg)
    except OSError:
        pass
    return bad


def check_runtime() -> int:
    """⑤ **적힌 판이 실제로 도는 판인가** — 제자리 업그레이드 중에 어긋나는 자리다.

    ⛔`SOLVER_BUILD` 는 import 때 dist-info 를 읽는데 솔버는 한참 뒤에 import 된다.
      그 사이에 판이 갈리면 새 판으로 굽고 옛 이름·도장으로 저장한다.
    """
    import elevation_sweep_md as esm
    keep = esm.SOLVER_BUILD
    bad = 0
    print("── ⑤ 적힌 판 ↔ 도는 판 ──")
    #: 지금 올라온 모듈이 없으면 아무 말도 안 해야 한다(dry-run 이 막히면 큐를 못 짠다)
    esm._RT_CHECKED["v"] = False
    esm.SOLVER_BUILD = keep
    try:
        esm._check_runtime_build()
        ok1 = True
    except SystemExit as e:
        ok1, why = False, str(e).splitlines()[0]
    bad += not ok1
    print(f"  {'✅' if ok1 else '⛔'} 지금 판 그대로면 안 선다" + ("" if ok1 else f" — {why}"))
    #: 거짓 판을 적어 두면 서야 한다 — 단, 그 꾸러미가 실제로 올라와 있을 때만
    import sys as _s
    live = [m for m in ("mitsuba", "drjit", "sionna") if _s.modules.get(m) is not None]
    if not live:
        print("  ⚠솔버가 아직 안 올라와 있어 «어긋남» 갈래는 시험 못 했다(dry-run 경로)")
        esm.SOLVER_BUILD = keep
        return bad
    esm._RT_CHECKED["v"] = False
    esm.SOLVER_BUILD = "sionna=9.9.9 sionna-rt=9.9.9 mitsuba=9.9.9 drjit=9.9.9"
    try:
        esm._check_runtime_build()
        ok2 = False
    except SystemExit:
        ok2 = True
    bad += not ok2
    print(f"  {'✅' if ok2 else '⛔'} 거짓 판을 적어 두면 멈춘다 (올라온 꾸러미 {live})")
    esm.SOLVER_BUILD = keep
    esm._RT_CHECKED["v"] = False
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
    n_skip_name = n_skip_parse = 0          # ⭐말없이 건너뛴 수 — 전에는 세지도 찍지도 않았다
    bad = []
    for p in paths:
        m = rx.match(os.path.basename(p))
        if not m:
            n_skip_name += 1                # ⛔샤드 이름 규약에 안 맞는 파일
            continue
        try:
            tag = parse(m.group("arm")).get("solver_build")
        except ArmNameError:
            n_skip_parse += 1               # ⛔문법이 못 읽는 이름 — 여기가 눈이 멀던 자리다
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
    #: ⭐**셈이 맞나** — 전에는 건너뛴 것을 세지 않아 a+b < N 이어도 아무도 몰랐다
    acct = n_stamp + n_none + n_skip_name + n_skip_parse
    print(f"  셈: {n_stamp} + {n_none} + 이름규약 밖 {n_skip_name} + 문법이 못 읽음 {n_skip_parse}"
          f" = {acct} {'✅' if acct == len(paths) else '⛔'} {len(paths)}")
    if acct != len(paths):
        bad.append(("(셈)", f"합이 {acct} 인데 샤드는 {len(paths)} 개다"))
    if n_skip_parse:
        bad.append(("(문법)", f"문법이 못 읽는 이름이 {n_skip_parse} 개 — 이 샤드는 대조에서 빠진다"))
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
    bad = (check_build_tag() + check_runtime()
           + check_grammar() + check_shards())
    if bad:
        print(f"\n⛔어긋남 {bad} 곳 — 판이 섞일 수 있다. 굽기 전에 고쳐라.")
        return 1
    print("\n✅ 판 꼬리표·문법·창고 도장이 서로 맞는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
