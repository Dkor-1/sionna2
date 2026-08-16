# -*- coding: utf-8 -*-
"""
gate_fc_bitidentical.py — **`--fc-ghz` 를 안 주면 기존과 비트동일인가** (회귀 게이트)

■ 왜 있나
`elevation_sweep_md.py` 에 반송파 인자를 붙였다(R23② 선행 배관). 이 저장소에서 가장 비싼
사고는 «꼬리표를 안 붙여 원장이 조용히 오염되는 것» 이라, 배관을 바꾼 직후 반드시
**「인자를 안 주면 옛 샤드와 이름도 값도 같다」** 를 기계로 확인해야 한다.

■ ⛔GPU 를 안 쓴다
`sionna.rt`·`mitsuba` 를 임포트하지 않는다. 스윕 모듈은 무거운 것을 전부 `run()` 안에서
임포트하므로 모듈 자체는 그냥 읽힌다. 그래서 이 게이트는 **두 가지**만 본다 —
  ① 파일 이름(꼬리표) — 실제 소스의 `tagr`/`tagd`/`tagp` 식을 **ast 로 떼어다 그대로 실행**한다.
     식을 베껴 적으면 게이트가 소스와 어긋나므로 베끼지 않는다.
  ② 파장에서 갈라져 나오는 파생값(격자 간격 d·파수 k·f_tip) — float 비트까지 같은지 본다.
그리고 ③ 이미 쌓인 실제 샤드 이름이 `_fc` 규칙에 안 걸리는지(옛 팔이 5.8 로 오독되지 않는지).

    PYTHONPATH=src:benchmark python benchmark/gate_fc_bitidentical.py
"""
from __future__ import annotations

import ast
import glob
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import elevation_sweep_md as M                                        # noqa: E402

SRC = open(M.__file__, encoding="utf-8").read()
TREE = ast.parse(SRC)
FAILS: list[str] = []


def bits(x) -> str:
    """float 를 8 바이트 그대로 16 진수로 — «값이 비슷하다» 가 아니라 «비트가 같다» 를 본다."""
    return struct.pack(">d", float(x)).hex()


def ok(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'✅' if cond else '⛔'} {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


# ── 소스에서 식을 떼어 온다 ────────────────────────────────────────────────────
def run_body() -> list:
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            return node.body
    raise SystemExit("⛔ run() 을 못 찾았다")


def assign_segments() -> list[str]:
    """run() 안의 **모든 단순 대입문 원문**을 소스 순서대로.

    ⚠식을 베껴 적지 않는 것이 요점이다 — 형제 인자(--shell-mm·--grid-shift …)가 꼬리표를
      더해도 게이트가 저절로 따라간다. 세울 수 없는 문장(GPU 객체가 필요한 것)은 그냥
      NameError 로 걸러진다."""
    out, seen = [], set()
    for node in ast.walk(ast.Module(body=run_body(), type_ignores=[])):
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            seg = ast.get_source_segment(SRC, node)
            if seg and (node.lineno, seg) not in seen:
                seen.add((node.lineno, seg))
                out.append((node.lineno, seg))
    return [s for _, s in sorted(out)]


def args_for(argv: list[str]):
    """진짜 argparse 파서를 태워 Namespace 를 얻는다 — 형제 인자까지 기본값이 다 들어온다."""
    cap = {}
    real_run, real_analyse = M.run, M.analyse
    M.run = lambda a: cap.setdefault("a", a)
    M.analyse = lambda: None
    old = sys.argv
    try:
        sys.argv = ["elevation_sweep_md.py"] + argv
        M.main()
    finally:
        sys.argv = old
        M.run, M.analyse = real_run, real_analyse
    return cap["a"]


SEGS = assign_segments()


def shard_names(argv: list[str]) -> dict:
    """그 인자로 돌리면 나올 **샤드 파일 이름**을 소스의 식을 그대로 실행해 만든다.

    모듈 전역을 바탕에 깔고 run() 의 대입문을 여러 번 훑는다 — 앞 문장이 못 서면 다음
    바퀴에서 다시 시도한다. 여전히 못 서는 것(GPU 객체)은 꼬리표와 무관하다."""
    a = args_for(argv)
    env = dict(M.__dict__)
    env.update(a=a, el=-15.0)
    for _ in range(4):
        before = len(env)
        for seg in SEGS:
            try:
                exec(seg, env)                       # noqa: S102 — 소스 그대로 도는 것이 요점
            except Exception:
                pass
        if len(env) == before:
            break
    out = {}
    if "tagd" in env:
        out["ours"] = f"ours{env['tagd']}_el{-15.0:+.0f}_{a.shard:02d}.npz"
    if "tagp" in env:
        out["sionna"] = f"sionna{env['tagp']}_el{-15.0:+.0f}_{a.shard:02d}.npz"
    out["_d"] = env.get("d")
    out["_fc"] = env.get("fc")
    return out


# ═══ ① 꼬리표 — 안 주면 옛 이름과 글자 하나까지 같다 ══════════════════════════
print("\n① 파일 이름(꼬리표)  — 소스의 tagr/tagd/tagp 식을 그대로 실행")
CASES = [
    ["--engine", "ours"],
    ["--engine", "ours", "--range-m", "15", "--n-poses", "8192"],
    ["--engine", "ours", "--drone", "mini5pro", "--range-m", "15", "--div", "24"],
    ["--engine", "sionna", "--spp", "4000000000", "--range-m", "15",
     "--n-poses", "8192", "--max-depth", "1"],
    ["--engine", "sionna", "--drone", "mini5pro", "--spp", "4000000000",
     "--range-m", "15", "--n-poses", "8192", "--max-depth", "1", "--els", "0,-30,-60"],
    ["--engine", "sionna", "--parts", "fc"],          # ⚠«fc» 그룹 이름이 꼬리표에 든다
    ["--engine", "sionna", "--parts=-prop", "--sw", "R1D0E0F1"],
    ["--engine", "ours_free", "--range-m", "15", "--ptd"],
]
for argv in CASES:
    base = shard_names(argv)
    same = shard_names(argv + ["--fc-ghz", "3.5"])
    diff = shard_names(argv + ["--fc-ghz", "5.8"])
    lbl = " ".join(argv)
    for eng in ("ours", "sionna"):
        if eng not in base:
            continue
        ok(f"{lbl:58s} 무인자 == --fc-ghz 3.5", base[eng] == same[eng], base[eng])
        ok(f"{lbl:58s} 5.8 → _fc5800 으로 갈린다",
           diff[eng] != base[eng] and "_fc5800" in diff[eng], diff[eng])

# ═══ ② 파생값 — 파장에서 갈라져 나오는 것들의 비트 ═══════════════════════════
print("\n② 파생값 비트 — 격자 간격 d · 파수 k · f_tip")
a0, a1 = args_for(["--engine", "ours"]), args_for(["--engine", "ours", "--fc-ghz", "3.5"])
fc0, tag0 = M.carrier(a0)
fc1, tag1 = M.carrier(a1)
ok("carrier() 가 모듈 상수 FC 를 **그 객체 그대로** 돌려준다",
   fc0 is M.FC and fc1 is M.FC, f"{bits(fc0)} / {bits(fc1)}")
ok("꼬리표가 둘 다 빈 문자열", tag0 == "" and tag1 == "", repr(tag0))

d_old = (2.998e8 / M.FC) / M.DIV                    # 옛 코드의 식(FC 상수)
d_new = (2.998e8 / fc1) / M.DIV                     # 새 코드의 식(fc 인자)
ok("격자 간격 d 비트동일", bits(d_old) == bits(d_new), f"{d_old!r}  {bits(d_new)}")
k_old = 2.0 * np.pi / (299792458.0 / M.FC)
k_new = 2.0 * np.pi / (299792458.0 / fc1)
ok("파수 k 비트동일", bits(k_old) == bits(k_new), bits(k_new))
ph_old = np.exp(-1j * 2 * np.pi * M.FC * 1.0009e-7)
ph_new = np.exp(-1j * 2 * np.pi * fc1 * 1.0009e-7)
ok("PathSolver 위상 exp(−j2πfc·τ) 비트동일", ph_old == ph_new, repr(ph_new))

d58 = (2.998e8 / 5.8e9) / M.DIV
ok("5.8 GHz 는 격자가 실제로 촘촘해진다(λ/12 유지)",
   abs(d_old / d58 - 5.8 / 3.5) < 1e-12,
   f"{d_old*1e3:.4f} mm → {d58*1e3:.4f} mm (×{d_old/d58:.4f})")

# ═══ ③ 병합 쪽 — 옛 팔 이름이 _fc 규칙에 안 걸린다 ═══════════════════════════
print("\n③ 병합 — carrier_of() 가 옛 팔을 3.5 GHz 로 읽는다")
arms = sorted({os.path.basename(f).rsplit("_el", 1)[0]
               for f in glob.glob(f"{M.SHD}/*_el*.npz")})
bad = [x for x in arms if M.carrier_of(x) != M.FC]
ok(f"쌓인 팔 {len(arms)} 개 전부 규약값으로 읽힌다", not bad, f"오독 {bad[:3]}")
ok("가짜 이름 _partsfc 는 안 걸린다", M.carrier_of("sionna_partsfc_r15") == M.FC)
ok("가짜 이름 _partsnofc 는 안 걸린다", M.carrier_of("sionna_partsnofc_r15") == M.FC)
ok("_fc5800 은 5.8 GHz 로 읽힌다", M.carrier_of("sionna_r15_fc5800") == 5.8e9)
ok("f_tip 도 팔마다 갈린다",
   abs(M.f_tip_at(-15.0, "sionna_r15_fc5800") / M.f_tip_at(-15.0, "sionna_r15")
       - 5.8 / 3.5) < 1e-9,
   f"{M.f_tip_at(-15.0, 'sionna_r15'):.1f} → {M.f_tip_at(-15.0, 'sionna_r15_fc5800'):.1f} Hz")

# ═══ ④ 정적 검사 — run() 안에 FC 가 남아 있으면 안 된다 ═════════════════════
print("\n④ 정적 — run() 의 계산 경로에 상수 FC 가 안 남았다")
left = [n.id for n in ast.walk(ast.Module(body=run_body(), type_ignores=[]))
        if isinstance(n, ast.Name) and n.id == "FC"]
ok("run() 안에 FC 참조 0 개", not left, f"남은 것 {len(left)} 개")

print("\n" + ("✅ 전부 통과" if not FAILS else f"⛔ 실패 {len(FAILS)} 건: {FAILS}"))
sys.exit(1 if FAILS else 0)
