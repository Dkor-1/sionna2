# -*- coding: utf-8 -*-
"""
make_shards.py — 전수조사 샤드를 **결정적으로** 다시 만든다
==========================================================================================
왜 이 파일이 있나
    2026-09-04 전수조사의 샤드(18 MB · 223,975 줄)는 세션 스크래치패드(`/tmp`)에만 있었다.
    세션이 끊기면 통째로 사라진다. 이 스크립트가 **같은 입력에서 같은 샤드**를 다시 낸다 —
    파일 순서를 이름으로 고정하고, 무작위·시각을 쓰지 않는다.

무엇을 자르나
    저장소의 모든 `.md .py .ipynb .json .html` 에서
      ① 한국어가 든 줄            → 물결 1·2 (샤드 0000~0270)
      ② 한국어가 없는 영문 산문 줄  → 물결 3   (샤드 0271~)
    각 줄에 **원본 줄 번호**를 붙인다(노트북은 `c<셀>:<줄>`). 조사자가 원본을 되짚을 수 있게.

    ⛔수치 배열은 뺀다 — 그건 `benchmark/check_retracted.py` 가 따로 잰다.
    ⛔`assets/ vendor/ elev_sweep_shards/ partial/` 는 산문이 없어 뺀다.

샤드 묶음(id 범위는 아래 GROUPS 순서가 정한다)
    A 발행면   docs · reports · atlas · 루트 md
    B 코드     src · benchmark · runners
    C 원장     outputs
    D 미조사   prior_work · report_mesh · jihyuck · archive · refs · work

실행
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" python3 work/sweep_0904/make_shards.py [출력폴더]
        기본 출력폴더: work/sweep_0904/shards  (git 에 안 올린다 — .gitignore 참조)

    끝나면 `STATE.json` 의 `ranges` 와 대조해 id 범위가 같은지 확인한다.
    다르면 저장소가 그 뒤로 바뀐 것이다 — STATE.json 을 새로 적고 물결을 다시 돌린다.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else \
    os.path.join(ROOT, "work", "sweep_0904", "shards")

SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", "node_modules", ".venvs",
             "elev_sweep_shards", "assets", "vendor", "partial"}
EXTS = (".md", ".py", ".ipynb", ".json", ".html")
MAX_BYTES = 4_000_000          # 이보다 큰 파일은 산문이 아니라 데이터다
CAP = 80_000                   # 샤드 하나의 최대 글자수
MIN_KO = 50                    # 한국어 글자가 이보다 적으면 산문이 아니다

KO = re.compile(r"[가-힣]")
#: 영문 «산문» — 알파벳 낱말 다섯 개 이상이 이어지는 줄. 코드·경로·수치는 안 걸린다.
EN = re.compile(r"(?:[A-Za-z][A-Za-z'-]{2,}\s+){5,}")

GROUPS = [("A_발행면", ("docs/", "reports/", "atlas/", "README.md", "CLAUDE.md", "AGENTS.md")),
          ("B_코드", ("src/", "benchmark/", "runners/")),
          ("C_원장", ("outputs/",)),
          ("D_미조사", ("prior_work/", "report_mesh/", "jihyuck/", "archive/", "refs/", "work/"))]


def group_of(rel: str) -> str:
    for g, prefixes in GROUPS:
        if any(rel == p or rel.startswith(p) for p in prefixes):
            return g
    return "D_미조사"


def walk() -> list:
    """레포 상대경로 — **이름순으로 고정**한다(결정성)."""
    out = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(fns):
            if fn.endswith(EXTS):
                out.append(os.path.relpath(os.path.join(dp, fn), ROOT))
    return sorted(out)


def ko_lines(rel: str) -> list:
    """(줄표시, 글) — 한국어가 든 줄만. 노트북은 **마크다운 셀**만 본다."""
    path = os.path.join(ROOT, rel)
    out = []
    if rel.endswith(".ipynb"):
        try:
            nb = json.load(io.open(path, encoding="utf-8"))
        except Exception:
            return out
        for ci, c in enumerate(nb.get("cells", [])):
            if c.get("cell_type") != "markdown":
                continue
            for li, ln in enumerate(c.get("source", []), 1):
                if KO.search(ln):
                    out.append((f"c{ci}:{li}", ln.rstrip("\n")))
        return out
    try:
        s = io.open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return out
    for i, ln in enumerate(s.split("\n"), 1):
        if KO.search(ln):
            out.append((str(i), ln.rstrip()))
    return out


def en_lines(rel: str) -> list:
    """한국어가 **없는** 영문 산문 줄. 짧은 줄은 뺀다(경로·키 이름이라서)."""
    path = os.path.join(ROOT, rel)
    try:
        s = io.open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return []
    out = []
    for i, ln in enumerate(s.split("\n"), 1):
        if KO.search(ln) or len(ln) < 40 or not EN.search(ln):
            continue
        out.append((str(i), ln.strip()[:400]))
    return out


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    files = walk()

    #: ── 물결 1·2 — 한국어 산문 ────────────────────────────────────────────
    digests, manifest = {}, []
    for rel in files:
        p = os.path.join(ROOT, rel)
        try:
            if os.path.getsize(p) > MAX_BYTES:
                continue
        except OSError:
            continue
        L = ko_lines(rel)
        if len(L) < 1:
            continue
        try:
            if len(KO.findall(io.open(p, encoding="utf-8", errors="ignore").read())) < MIN_KO:
                continue
        except OSError:
            continue
        body = "\n".join(f"{n}\t{t[:900]}" for n, t in L)
        digests[rel] = f"### {rel}  (한국어 든 줄 {len(L)}개)\n{body}\n"
        manifest.append({"file": rel, "n_lines": len(L), "chars": len(digests[rel])})

    sid, ranges = 0, {}
    for g, _ in GROUPS:
        first = sid
        cur, sz = [], 0
        for rec in manifest:
            if group_of(rec["file"]) != g:
                continue
            txt = digests[rec["file"]]
            if len(txt) > CAP:                       # 큰 파일은 줄 단위로 쪼갠다
                head, lines = txt.split("\n", 1)[0], txt.split("\n")[1:]
                buf, bs, part = [], 0, 1
                for ln in lines:
                    if bs + len(ln) > CAP and buf:
                        io.open(f"{OUT}/{sid:04d}.txt", "w", encoding="utf-8").write(
                            f"{head}  [조각 {part}]\n" + "\n".join(buf))
                        sid += 1
                        part += 1
                        buf, bs = [], 0
                    buf.append(ln)
                    bs += len(ln) + 1
                if buf:
                    io.open(f"{OUT}/{sid:04d}.txt", "w", encoding="utf-8").write(
                        f"{head}  [조각 {part}]\n" + "\n".join(buf))
                    sid += 1
                continue
            if sz + len(txt) > CAP and cur:
                io.open(f"{OUT}/{sid:04d}.txt", "w", encoding="utf-8").write("\n\n".join(cur))
                sid += 1
                cur, sz = [], 0
            cur.append(txt)
            sz += len(txt)
        if cur:
            io.open(f"{OUT}/{sid:04d}.txt", "w", encoding="utf-8").write("\n\n".join(cur))
            sid += 1
        ranges[g] = [first, sid - 1]

    #: ── 물결 3 — 영문 산문 ────────────────────────────────────────────────
    first = sid
    cur, sz = [], 0
    for rel in files:
        p = os.path.join(ROOT, rel)
        try:
            if os.path.getsize(p) > MAX_BYTES:
                continue
        except OSError:
            continue
        L = en_lines(rel)
        if not L:
            continue
        body = (f"### {rel}  (영문 산문 줄 {len(L)}개)\n"
                + "\n".join(f"{n}\t{t}" for n, t in L))
        if sz + len(body) > CAP and cur:
            io.open(f"{OUT}/{sid:04d}.txt", "w", encoding="utf-8").write("\n\n".join(cur))
            sid += 1
            cur, sz = [], 0
        cur.append(body)
        sz += len(body)
    if cur:
        io.open(f"{OUT}/{sid:04d}.txt", "w", encoding="utf-8").write("\n\n".join(cur))
        sid += 1
    ranges["E_영문"] = [first, sid - 1]

    #: ── 검산 — 한 줄도 안 빠졌나 ──────────────────────────────────────────
    want = sum(r["n_lines"] for r in manifest)
    got, seen = 0, set()
    for i in range(ranges["A_발행면"][0], ranges["D_미조사"][1] + 1):
        for ln in io.open(f"{OUT}/{i:04d}.txt", encoding="utf-8"):
            if ln.startswith("### "):
                seen.add(ln[4:].split("  (")[0])
            elif ln.strip():
                got += 1
    ok = (want == got) and (len({r["file"] for r in manifest} - seen) == 0)
    print(f"샤드 {sid}개 → {OUT}")
    for k, v in ranges.items():
        print(f"   {k:10s} {v[0]:4d}~{v[1]:4d}  ({v[1] - v[0] + 1}개)")
    print(f"\n검산 — 한국어 줄 원본 {want:,} · 샤드 {got:,} (차 {want - got:+,}) · "
          f"파일 {len(manifest):,}/{len(seen):,}  → {'✅ 손실 없음' if ok else '⛔ 빠진 것이 있다'}")
    json.dump({"ranges": ranges, "n_shards": sid, "n_ko_lines": want,
               "n_files": len(manifest), "lossless": ok},
              io.open(os.path.join(os.path.dirname(OUT), "SHARDS.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
