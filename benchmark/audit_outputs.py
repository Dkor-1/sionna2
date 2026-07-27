#!/usr/bin/env python
"""outputs/*.json **전수 정산** — 누가 만들었고, 언제 만들었고, 지금 기준으로 낡았는가.

왜 필요한가
-----------
이 프로젝트의 숫자는 전부 `outputs/*.json` 을 거쳐 리포트로 간다. 그런데
  · 생산자가 사라진 **고아 파일**이 남아 있으면 → 아무리 코드를 고쳐도 그 숫자만 옛날에 멈춘다
  · 엔진(RCS)이나 메쉬(CAD)를 고친 **시점보다 오래된 파일**은 → 이미 틀린 값을 담고 있다
둘 다 조용히 일어나서, 리포트를 다시 빌드해도 티가 안 난다. 그래서 기계로 센다.

판정 기준
--------
  생산자    : 그 파일명을 문자열로 갖고 있으면서 `json.dump` 또는 open(...,"w") 를 하는 .py
  σ의존     : 생산자가 (직·간접으로) drones / rcs_sbr / rcs_po / channel 을 import 하면 True
  세대      : 파일 mtime 을 아래 기준시각과 비교
                ENGINE  = RCS 엔진 대공사 (커밋 9f26cee)
                MESH    = 프롭포함 엔벨로프 + 허브-블레이드 결합 수정
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "outputs")
SRC_DIRS = [os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")]

# σ/메쉬를 실제로 건드리는 뿌리 모듈
SIGMA_ROOTS = {"drones", "drone_cad", "rcs_sbr", "rcs_po", "channel", "microdoppler",
               "mesh_compare", "mesh_check", "scene_build", "radar_scene", "bistatic_scene"}


def _commit_time(sha: str) -> float | None:
    try:
        s = subprocess.run(["git", "-C", ROOT, "show", "-s", "--format=%ct", sha],
                           capture_output=True, text=True, timeout=10)
        return float(s.stdout.strip()) if s.returncode == 0 else None
    except Exception:
        return None


def _py_files() -> list[str]:
    out = []
    for d in SRC_DIRS:
        for f in sorted(os.listdir(d)):
            if f.endswith(".py"):
                out.append(os.path.join(d, f))
    return out


def _imports(path: str) -> set[str]:
    """이 파일이 직접 import 하는 로컬 모듈 이름."""
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except Exception:
        return set()
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            names.add(n.module.split(".")[0])
    return names


# 이 프로젝트가 실제로 쓰는 저장 관용구 전부 — os.replace(tmp, OUT) 원자적 교체까지 포함
_WRITE_PAT = ("json.dump", '"w"', "'w'", ".write(", "np.savez", "np.save", "os.replace(")


def _writes_json(path: str, name: str) -> bool:
    """이 파일이 `name` 을 **쓰는가**(단순 참조가 아니라).

    두 형태를 모두 잡는다:
      (a) 직접  — json.dump(J, open("…/report1.json", "w"))
      (b) 간접  — JSON_OUT = os.path.join(ROOT, "outputs", "report1.json")  …  open(JSON_OUT, "w")
          (모듈 상단에서 상수로 잡고 수백 줄 아래서 쓰는 게 이 프로젝트의 지배적 관용구다)
    """
    import re
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception:
        return False
    if name not in txt:
        return False
    lines = txt.splitlines()

    # (a) 파일명 리터럴이 있는 줄(또는 직전/직후 2줄)에 쓰기 호출이 있나
    for i, l in enumerate(lines):
        if name in l:
            near = "\n".join(lines[max(0, i - 2):i + 3])
            if any(p in near for p in _WRITE_PAT):
                return True

    # (b) 리터럴을 담은 **변수**를 찾아, 그 변수가 쓰기 문맥에 쓰였나
    for i, l in enumerate(lines):
        if name not in l:
            continue
        # NAME = …literal…            (모듈 상수)
        # ap.add_argument("--out", default=…literal…)  → 이후 a.out / args.out 으로 쓰인다
        m = re.match(r"\s*([A-Za-z_][A-Za-z_0-9]*)\s*=", l)
        if m:
            var = m.group(1)
        else:
            m2 = re.search(r'add_argument\(\s*["\']--([A-Za-z_0-9-]+)', l)
            if not m2:
                continue
            var = m2.group(1).replace("-", "_")     # argparse 는 - 를 _ 로 바꾼다
        pat = re.compile(rf"(?:\.|\b){re.escape(var)}\b")
        for l2 in lines:
            if not pat.search(l2):
                continue
            if any(p in l2 for p in _WRITE_PAT):
                return True
            # _save(fig, PATH) / dump_json(PATH) 처럼 헬퍼로 넘기는 형태
            if re.search(rf"\b(save|dump|write)\w*\s*\([^)]*{pat.pattern}", l2):
                return True
    return False


def main() -> int:
    engine = _commit_time("9f26cee")
    mesh_t = None
    for cand in ("src/drones.py", "src/drone_cad.py"):
        p = os.path.join(ROOT, cand)
        if os.path.exists(p):
            mesh_t = max(mesh_t or 0, os.path.getmtime(p))

    pys = _py_files()
    imp = {os.path.basename(p)[:-3]: _imports(p) for p in pys}

    def sigma_dep(mod: str, seen: set[str] | None = None) -> bool:
        seen = seen or set()
        if mod in seen:
            return False
        seen.add(mod)
        if mod in SIGMA_ROOTS:
            return True
        return any(sigma_dep(m, seen) for m in imp.get(mod, set()) if m in imp)

    rows = []
    for f in sorted(os.listdir(OUT)):
        if not f.endswith(".json"):
            continue
        p = os.path.join(OUT, f)
        mt = os.path.getmtime(p)
        producers = [os.path.basename(q) for q in pys if _writes_json(q, f)]
        dep = any(sigma_dep(q[:-3]) for q in producers)
        if not producers:
            verdict = "🔴 고아 — 생산자 없음"
        elif not dep:
            verdict = "⚪ σ 무관"
        elif engine and mt < engine:
            verdict = "🔴 엔진 이전 — 재생성 필요"
        elif mesh_t and mt < mesh_t:
            verdict = "🟠 메쉬 이전 — 재생성 권장"
        else:
            verdict = "🟢 최신"
        rows.append((f, time.strftime("%m-%d %H:%M", time.localtime(mt)),
                     os.path.getsize(p), "σ" if dep else "-",
                     ",".join(producers) or "—", verdict))

    w = max(len(r[0]) for r in rows)
    print(f"{'json':{w}} {'생성':11} {'크기':>9} {'dep':>4}  {'판정':22} 생산자")
    print("-" * (w + 78))
    for f, ts, sz, dep, prod, v in rows:
        print(f"{f:{w}} {ts:11} {sz:9,} {dep:>4}  {v:22} {prod}")

    n_bad = sum(1 for r in rows if r[5].startswith("🔴"))
    n_warn = sum(1 for r in rows if r[5].startswith("🟠"))
    print(f"\n총 {len(rows)}개 · 🔴 {n_bad} · 🟠 {n_warn} · "
          f"엔진기준 {time.strftime('%m-%d %H:%M', time.localtime(engine)) if engine else '?'} · "
          f"메쉬기준 {time.strftime('%m-%d %H:%M', time.localtime(mesh_t)) if mesh_t else '?'}")
    if "--json" in sys.argv:
        json.dump([dict(zip(("file", "mtime", "bytes", "dep", "producers", "verdict"), r))
                   for r in rows], open(os.path.join(OUT, "audit_outputs.json"), "w"),
                  ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
