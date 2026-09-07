# -*- coding: utf-8 -*-
"""
check_new_file_rules.py — **새로 만든 파일이 다시 못 굽는 꼴이 되는 것**을 막는 관문
==========================================================================================
왜 있나
    2026-09-04~06 전수조사에서 확정한 900 건 가운데 되풀이가 가장 많았던 것은
    「고침이 빌더에 들어갔는데 생성물은 옛 문면으로 남았다」였다(마지막 90 건 중 **64 건**).
    그리고 재빌드를 돌려 보니 **빌더 자신이 다시 못 도는** 자리가 셋 나왔다.
    이 관문은 그 셋처럼 **기계로 잡을 수 있는 것만** 잡는다. 문면 판단은 안 한다.

무엇을 잡나 — 전부 이번에 **실제로 걸린 것**이다
    ⓐ 죽은 임시 경로   `/tmp/claude-…/scratchpad/…` 를 소스에 박았다.
                      그 세션이 끝나면 그 파일은 없다 ⇒ 영영 다시 못 굽는다.
                      (benchmark/canon_0816/build_md_class_ledger.py 가 그랬다)
    ⓑ 없는 파이썬     `~/.venvs` 를 실행법에 적었다. 이 기계엔 없다.
                      (여러 독스트링이 그랬다 — 그대로 치면 시스템 파이썬이 잡힌다)
    ⓒ 레포 밖 쓰기     `/data/…` 같은 저장소 밖 경로에 **쓰기**로 연다.
    ⓓ 안 적힌 필수 인자 argparse 에 `required=True` 인데 독스트링에 그 인자가 없다.
                      재빌드 때 usage 만 뱉고 죽는다(rc=2 로 셋이 걸렸다).
    ⓔ 못 굽는 원장     outputs/*.json 에 `_meta.generator` 가 없거나, 있는데 그 스크립트가
                      **레포에 없다**. 전수조사 900 건의 근본 원인 가운데 **148 건**이 이것이다
                      — 정정이 되돌아올 자리가 없어 옛 수가 문서로 계속 흘러간다.
    ⓕ 자리표시자      발행되는 산문에 `TBD`·`nan`·`???` 가 남았다. 수가 채워지기 전에 결론
                      문장을 먼저 확정한 자리다.

⛔**넣으려다 뺀 것 — 「시뮬을 실측이라 부름」(규약 ⑥)은 낱말로 못 잡는다**
    2026-09-07 에 넣어 봤다가 걷었다. 「실측」이 이 저장소에 **2,816 곳** 있는데 대부분이
    「실제로 돌려 잰 소요 시간·경로 수」라는 **정당한 용법**이다. 좁혀서 「검증됐·확증」만
    보면 66 곳인데, 열어 보니 거의 다 이미 옳은 문장이다(「검증됐다 가 아니라」 같은 부정문,
    또는 공표 도면·문헌을 가리키는 자리).
    ⇒ 이 규약은 **문맥을 읽어야** 판정된다. 관문이 아니라 **감사**로 잡는다.
      (실제로 그날 걸린 한 곳도 사람이 읽어서 찾았다 — `runners/make_jobs_0911.py` 의
       「기능은 검증됐지만」. 낱말 규칙으로는 그 줄이 다른 2,816 곳과 구별되지 않는다.)
    ⚠오탐이 많은 관문은 아무도 안 쓴다. 못 잡는 것은 **못 잡는다고 적는 편**이 낫다.

전문: `docs/NEW_FILE_RULES.md` (900 건 → 근본 원인 16 가지)

⛔여기서 문장의 옳고 그름은 안 본다 — 그건 check_retracted.py · CLAIM_GATE 의 몫이다.
⛔오탐이 한 건이라도 나면 아무도 안 쓴다. 규칙마다 면제를 좁게 달았다.

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/check_new_file_rules.py
    (막힌 것이 있으면 종료 코드 1)
"""
from __future__ import annotations

import ast
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKIP_DIRS = {".git", "__pycache__", "archive", "node_modules", ".venvs",
             "shards", "elev_sweep_shards", "partial"}
MAX_BYTES = 2_000_000

#: ⓐ 죽은 임시 경로. 이 세션의 scratchpad 도 **똑같이** 죽는다 — 예외를 두지 않는다.
DEAD_TMP = re.compile(r"[\"'](/tmp/[^\"']*(?:scratchpad|claude-)[^\"']*)[\"']")
#: ⓑ 이 기계에 없는 파이썬
NO_VENV = re.compile(r"~/\.venvs")
#: ⓒ 저장소 밖으로 **쓰기**. open(...,"w") 의 첫 인자가 절대경로 문자열일 때만 본다.
OUT_ROOTS = ("/data/", "/home/", "/root/", "/mnt/", "/media/")


def files():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(fns):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield p


def _lineno(txt: str, idx: int) -> int:
    return txt.count("\n", 0, idx) + 1


def check_text(rel: str, txt: str, out: list) -> None:
    for m in DEAD_TMP.finditer(txt):
        out.append((rel, _lineno(txt, m.start()), "ⓐ죽은 임시 경로",
                    m.group(1)[:90],
                    "저장소 안 경로로 옮기고 그 파일을 커밋해라 — 세션이 끝나면 이 경로는 없다"))
    for m in NO_VENV.finditer(txt):
        out.append((rel, _lineno(txt, m.start()), "ⓑ없는 파이썬", "~/.venvs",
                    "/workspace/.venvs/py312/bin/python 으로 적어라"))


def check_ast(rel: str, txt: str, out: list) -> None:
    try:
        tree = ast.parse(txt)
    except SyntaxError:
        return

    doc = (ast.get_docstring(tree) or "")
    #: ⓓ 필수 인자가 독스트링에 있나
    req = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "add_argument"):
            continue
        if not any(isinstance(k, ast.keyword) and k.arg == "required"
                   and isinstance(k.value, ast.Constant) and k.value.value is True
                   for k in n.keywords):
            continue
        for a in n.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("--"):
                req.append(a.value)
    for flag in req:
        if flag not in doc:
            out.append((rel, 1, "ⓓ안 적힌 필수 인자", flag,
                        "독스트링 «실행» 줄에 이 인자를 넣어라 — 없으면 재빌드가 usage 만 뱉고 죽는다"))

    #: ⓒ 저장소 밖으로 쓰기
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "open"):
            continue
        mode = ""
        if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
            mode = str(n.args[1].value)
        for k in n.keywords:
            if k.arg == "mode" and isinstance(k.value, ast.Constant):
                mode = str(k.value.value)
        if not any(c in mode for c in "wax"):
            continue
        if n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
            tgt = n.args[0].value
            if tgt.startswith(OUT_ROOTS) and not tgt.startswith(ROOT + "/"):
                out.append((rel, n.lineno, "ⓒ레포 밖 쓰기", tgt[:90],
                            "저장소 안으로 써라 — 밖의 파일은 남의 것이고 되돌릴 수 없다"))


BASELINE = os.path.join(ROOT, "benchmark", "new_file_rules_baseline.json")


def _key(rel: str, kind: str, what: str) -> str:
    """줄 번호는 넣지 않는다 — 위아래로 한 줄 밀렸다고 새 위반이 되면 안 된다."""
    return f"{rel}\t{kind}\t{what}"


def load_baseline() -> set:
    """⭐**이미 쌓인 빚**은 세되 막지는 않는다.

    이 관문을 처음 켠 날(2026-09-06) 저장소에는 382 곳이 걸렸다. 첫날부터 382 개로
    막히는 관문은 **아무도 안 쓴다.** 그래서 그날 자리를 기준선에 적고, 그 뒤로
    **새로 생기는 것만** 막는다. 기준선은 줄어들기만 해야 한다(늘리려면 손으로 적어라).
    """
    if not os.path.exists(BASELINE):
        return set()
    import json                                            # noqa: PLC0415
    with io.open(BASELINE, encoding="utf-8") as f:
        return set(json.load(f).get("known", []))


#: ⓕ 발행되는 산문에 남으면 안 되는 자리표시자. 좁게 잡는다 — 오탐이 나면 관문이 죽는다.
PLACEHOLDER = re.compile(r"\b(TBD|TODO_FILL|FIXME_NUM|\?\?\?|nan\s*(dB|%|배))\b")
#: 원장의 «누가 나를 구웠나» 를 적는 자리. 이 가운데 하나는 있어야 한다.
GEN_KEYS = ("generator", "producer", "builder", "generated_by", "made_by")


_PY_NAMES: set = set()


def _repo_py_names() -> set:
    """레포 안 모든 .py 의 **파일 이름**. 경로를 짧게 적은 생성기를 오탐하지 않으려고 쓴다."""
    if not _PY_NAMES:
        for dp, dns, fns in os.walk(ROOT):
            dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
            _PY_NAMES.update(f for f in fns if f.endswith(".py"))
    return _PY_NAMES


def check_ledgers(out: list) -> None:
    """ⓔⓕ outputs/*.json 이 **다시 구워지는가**와 자리표시자."""
    import json                                            # noqa: PLC0415
    od = os.path.join(ROOT, "outputs")
    for dp, dns, fns in os.walk(od):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(fns):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, ROOT)
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
                with io.open(p, encoding="utf-8") as f:
                    doc = json.load(f)
            except (OSError, ValueError, UnicodeDecodeError):
                continue
            if not isinstance(doc, dict):
                continue
            meta = doc.get("_meta")
            meta = meta if isinstance(meta, dict) else {}
            gen = next((str(meta[k]) for k in GEN_KEYS if k in meta), "")
            if not gen:
                out.append((rel, 1, "ⓔ못 굽는 원장", "_meta.generator 없음",
                            "이 원장을 다시 구울 스크립트 경로를 _meta.generator 에 적어라"))
            else:
                #: ⚠경로를 짧게 적은 것(«report_style.py» 처럼 src/ 를 뺀 것)은 위반이 아니다.
                #  이름으로도 못 찾을 때만 잡는다 — 오탐이 한 건 나면 관문이 죽는다.
                for m in re.finditer(r"[\w./-]+\.py", gen):
                    nm = m.group(0)
                    if os.path.exists(os.path.join(ROOT, nm.lstrip("/"))) or os.path.exists(nm):
                        continue
                    if os.path.basename(nm) in _repo_py_names():
                        continue
                    out.append((rel, 1, "ⓔ못 굽는 원장", f"{nm} 가 레포에 없다",
                                "실재하는 경로로 고쳐라 — 없으면 이 원장은 영영 못 굽는다"))
            #: 산문 필드의 자리표시자만 본다(수치 필드는 안 본다)
            for k, v in meta.items():
                if isinstance(v, str):
                    m = PLACEHOLDER.search(v)
                    if m:
                        out.append((rel, 1, "ⓕ자리표시자", f"_meta.{k} 에 {m.group(0)}",
                                    "수가 채워진 뒤에 문장을 쓴다 — 수 없는 결론은 안 내보낸다"))


def main() -> int:
    out: list = []
    check_ledgers(out)
    for p in files():
        rel = os.path.relpath(p, ROOT)
        try:
            txt = io.open(p, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        if rel == os.path.relpath(__file__, ROOT):
            continue                       # 자기 자신의 예시 문자열은 안 본다
        check_text(rel, txt, out)
        check_ast(rel, txt, out)

    if "--baseline" in sys.argv:                            # 기준선을 새로 깐다
        import json                                         # noqa: PLC0415
        doc = {
            "_meta": {
                "why_ko": "관문을 켠 날 이미 걸려 있던 자리. 새로 생기는 것만 막기 위한 기준선이다.",
                "shrink_only_ko": "⛔이 목록은 줄어들기만 한다. 늘리려면 왜 늘리는지 적고 손으로 넣어라.",
                "generator": "benchmark/check_new_file_rules.py --baseline",
            },
            "known": sorted({_key(r, k, w) for r, _l, k, w, _f in out}),
        }
        with io.open(BASELINE, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        print(f"기준선 {len(doc['known'])} 자리 → {os.path.relpath(BASELINE, ROOT)}")
        return 0

    known = load_baseline()
    fresh = [o for o in out if _key(o[0], o[2], o[3]) not in known]
    old_n = len(out) - len(fresh)
    if not fresh:
        print(f"✅ 새로 생긴 것 없음  (기준선에 남은 빚 {old_n} 자리)")
        return 0
    print(f"⛔새로 생긴 것 {len(fresh)} 곳  (기준선에 남은 빚 {old_n} 자리)\n")
    for rel, ln, kind, what, fix in fresh:
        print(f"  {kind}  {rel}:{ln}\n      {what}\n      → {fix}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
