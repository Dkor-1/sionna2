# -*- coding: utf-8 -*-
"""
rename_outputs.py — 은퇴한 13편 번호가 박힌 산출물 이름을 내용 기반 이름으로 옮긴다
================================================================================
⚠ **기본은 예행(dry-run)이다. 아무것도 바꾸지 않는다.** 실제 이름을 옮기려면
  `--apply --pipeline-is-idle` 를 둘 다 줘야 한다(§실행).

무엇이 문제인가
--------------
산출물 8종이 **은퇴한 13편 체계**의 번호를 이름에 달고 있다. 지금 리포트는 1~6편이므로
그 번호가 **새 번호와 충돌**한다.

    outputs/report5_results.json   → 읽는 편은 05편이 아니라 **03편**이다
    outputs/report13_freespace.json→ "13편" 은 이제 없다. 읽는 편은 05편이다
    outputs/report1.json           → 읽는 편은 02편(§1.2 재질)이다
    outputs/figures/report2_*.png  → 7장 중 4장은 **03편**이 싣는다

새 이름의 규칙 (이 저장소의 이름 규약)
------------------------------------
| 산출물 | 이름 규칙 | 왜 |
|---|---|---|
| 계산 JSON | **내용**으로 짓는다 (`sigma_grid.json`) | JSON 하나를 여러 편이 읽는다 — 편 번호는 태생적으로 거짓말이 된다 |
| 그림 PNG | **싣는 편**으로 짓는다 (`report03_occupancy.png`) | 그림 한 장은 정확히 한 편에 실린다 |
| 빌더 파생 JSON | `report0N_derived.json` | 그 편의 빌더가 만들고 그 편만 읽는다 — 1:1 이 구조적으로 보장된다 |

이미 잘 지어진 이름들이 이 규칙의 증거다 — `sigma_anchor.json`(02·05·06 이 읽는다) ·
`verify_cfar.json`(01·04) · `prior_census.json`(01·04) · `sbr_kr_sweep.json`(01·02).
전부 내용 이름이고, 전부 여러 편이 읽는다.

무엇을 건드리고 무엇을 안 건드리나
--------------------------------
| 분류 | 대상 | 이 스크립트의 처리 |
|---|---|---|
| `EDIT`    | `*.py` · 살아 있는 `docs/*.md` · `README.md` | 문자열을 직접 바꾼다 |
| `REBUILD` | `report0N_*.ipynb` | **안 바꾼다** — 빌더(stage 9)가 다시 써야 반영된다 |
| `REGEN`   | `outputs/*.json` 안의 경로 문자열 | **안 바꾼다** — 생산자가 다시 돌면 새 이름이 박힌다 |
| `FROZEN`  | 날짜 기록(`docs/RESUME_*` 등) · 타작업줄 문서 · 해독표 구간 | **안 바꾼다** — §FROZEN_DOCS |

`_legacy_reports/` · `src/_legacy_builders/` · `refs/` · `report_mesh/` 는 아예 훑지 않는다(`SKIP_DIRS`).
살아 있는 문서 안의 해독표는 `<!-- keep-old-names:on/off -->` 로 감싸면 그 줄만 건너뛴다.

실행
----
    # 예행 — 옮길 파일과 바꿀 참조를 전부 찍는다 (기본값)
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/rename_outputs.py

    # 한 항목만 자세히
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/rename_outputs.py --only report13_freespace.json

    # 실제 적용 — 파이프라인이 멈춰 있을 때만
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/rename_outputs.py --apply --pipeline-is-idle

적용 뒤 반드시 할 일 (스크립트가 마지막에 다시 찍는다)
--------------------------------------------------
 1. `benchmark/regen_mesh_dependents.py --check`  — 고아 감사 통과 확인
 2. 리포트 6편 재빌드 (stage 9) — 노트북 안의 출처태그가 새 이름으로 바뀐다
 3. `src/report_style.py :: check_budget` 6편 — 태그가 실제 JSON 을 여는지 재확인

지도 원본: `docs/OUTPUT_NAMING.md` (옛이름 → 내용 → 읽는 편 → 새이름).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)

# ──────────────────────────────────────────────────────────────────────────────
#  이름 지도 — (옛이름, 새이름, 생산자, 읽는 편, 무엇이 들었나)
#  ⭐ 생산자·읽는 편은 **grep 으로 확인한 것**이다(2026-07-31). 이름에서 유추하지 않았다.
# ──────────────────────────────────────────────────────────────────────────────
JSON_RENAMES: list[tuple[str, str, str, str, str]] = [
    ("outputs/report1.json", "outputs/mesh_materials.json",
     "src/viz_report1.py --only mesh,cad  +  benchmark/refresh_material_table.py",
     "02 §1.2 (chamber.materials 12태그)",
     "메쉬 삼각형수·외형봉투 + 재질 γ(bulk·PO) 표 + 관절·렌더 목록"),

    ("outputs/report2_waveform_rcs.json", "outputs/waveform_rcs.json",
     "src/viz_report2.py",
     "02 §2·§5.1 (25태그) · 03 §1·§1.1·§3.1 (42태그)",
     "3파형 제원·Sionna PHY 교차대조·모호함수·SBR 검증·가림·RCS·재질"),

    ("outputs/report3_rt.json", "outputs/rt_stock_solver.json",
     "benchmark/rt_experiments.py",
     "02 §2 (2태그: C_metal.*)",
     "Sionna RT 스톡 solver 실험 — 광선수·산란·금속판·구 (A_rays~E_sphere)"),

    ("outputs/report4_fixups.json", "outputs/convention_constants.json",
     "benchmark/report4_fixups.py",
     "03 §2·§2.1·§2.2 (12태그) · src/viz_report4.py (F1~F6 전부)",
     "규약 상수 — 듀티·√(B/fs)·CPI 비대칭·straddle·CFAR 손실·CRLB (F1~F6)"),

    ("outputs/report5_results.json", "outputs/bench_matrix.json",
     "benchmark/run_matrix.py --only a",
     "03 §2.1 (2태그: A_occupancy 만)",
     "챔버 벤치 매트릭스 A~E. **A_occupancy 만 살아 있다**(B~E 는 챔버 배제로 중단)",
     ),

    ("outputs/report6_sbr.json", "outputs/sbr_kernel_verify.json",
     "src/viz_verify_sbr.py --force",
     "02 §2 (3태그)",
     "SBR 커널 검증 — 구·판 기준해 오차, 기종별 가림, 프로펠러 법선, 메쉬 게이트"),

    ("outputs/report13_freespace.json", "outputs/freespace_range.json",
     "src/experiment_freespace_range.py",
     "05 §1~§3 (51태그) ⭐헤드라인 검지거리",
     "자유공간 검지거리 4단계 — 문턱·교정·풀이·검증 + ranges/curves/coverage/sensitivity"),

    ("outputs/report13_sigma_grid.json", "outputs/sigma_grid.json",
     "src/experiment_freespace_sigma.py",
     "05 §1.1 (2태그) · src/sigma_anchor.py(자세패턴 배열)",
     "σ 격자(자세 × 밴드) + 신뢰구간 + 멀티스태틱 Δσ(β)"),
]

#: 기종별로 쪼개 돌린 σ 격자 조각. **읽는 코드가 없다** — 병합 뒤 남은 중간산출물이다.
PART_RENAMES: list[tuple[str, str, str, str, str]] = [
    (f"outputs/report13_sigma_grid.{d}.json", f"outputs/parts/sigma_grid.{d}.json",
     "src/experiment_freespace_sigma.py --drones <한종> (GPU 분할 실행)",
     "없음 — 병합본 sigma_grid.json 만 읽힌다",
     "σ 격자 조각 1기종분(2026-07-24 분할 실행 잔여물)")
    for d in ("matrice4e", "mavic4pro", "mini5pro", "phantom4", "s1000plus")
]

#: 그림 — 편 번호가 곧 이름이다. report2_*.png 7장 중 **4장은 03편이 싣는다**.
FIG_RENAMES: list[tuple[str, str, str, str, str]] = [
    ("outputs/figures/report2_gallery.png", "outputs/figures/report02_gallery.png",
     "src/viz_report2.py:1231", "02 §1", "7기종 갤러리"),
    ("outputs/figures/report2_occlusion.png", "outputs/figures/report02_occlusion.png",
     "src/viz_report2.py:950", "02 §2", "가림 — first-hit 광선"),
    ("outputs/figures/report2_rcs_polar.png", "outputs/figures/report02_rcs_polar.png",
     "src/viz_report2.py:1015", "02 §5", "자세 RCS 극좌표"),
    ("outputs/figures/report2_resource_grid.png", "outputs/figures/report03_resource_grid.png",
     "src/viz_report2.py:318", "03 §1", "리소스 그리드"),
    ("outputs/figures/report2_ref_signal.png", "outputs/figures/report03_ref_signal.png",
     "src/viz_report2.py:265", "03 §1.1", "기준신호 예산"),
    ("outputs/figures/report2_occupancy.png", "outputs/figures/report03_occupancy.png",
     "src/viz_report2.py:358", "03 §2.1", "점유 대가"),
    ("outputs/figures/report2_crosscheck.png", "outputs/figures/report03_crosscheck.png",
     "src/viz_report2.py:461", "03 §3", "Sionna PHY 교차대조"),
]

#: 같은 PNG 를 **두 곳이 쓴다** — 파이프라인 밖의 옛 생산자가 살아 있다.
#: 이름만 옮기면 옛 생산자가 옛 이름으로 다시 그려 유령 파일이 생긴다. 그래서 `--apply` 를 막는다.
FIG_DUP_WRITERS: dict[str, list[str]] = {
    "outputs/figures/report2_occupancy.png": ["src/viz_occupancy.py:174 (파이프라인 밖)"],
    "outputs/figures/report2_rcs_polar.png": ["src/viz_radar.py:110 (파이프라인 밖)"],
}

#: 이름은 옛 체계지만 **6편 중 아무도 읽지 않는** 산출물. 지금 옮길 이유가 없다 — 기록만 남긴다.
NOT_READ_BY_ANY_REPORT: list[tuple[str, str, str]] = [
    ("outputs/report1_microdoppler.npz", "src/viz_report1.py:787 (--only md, 파이프라인에서 제외)",
     "마이크로도플러 복소장 — future work 강등(regen_mesh_dependents.DROPPED)"),
    ("outputs/figures/report1_*.png (8장)", "src/viz_report1.py", "6편 중 싣는 편 없음"),
    ("outputs/figures/report3_*.png (11장)", "src/viz_report3.py (DROPPED)", "6편 중 싣는 편 없음"),
    ("outputs/figures/report4_*.png (11장)", "src/viz_report4.py", "04편은 report04_f*.png 를 쓴다"),
    ("outputs/figures/report5_*.png (6장)", "benchmark/run_matrix.py", "05편은 report05_f*.png 를 쓴다"),
    ("outputs/figures/report13_*.png (16장)", "src/viz_report13.py", "6편 중 싣는 편 없음"),
    ("outputs/figures/report2_*.png (나머지 21장)", "src/viz_report2.py 외", "6편 중 싣는 편 없음"),
]

#: 이름이 서로를 가리키는 것처럼 보이는 **혼동쌍** — 옮기지는 않되 지도에 적어 둔다.
CONFUSING_PAIRS: list[tuple[str, str, str]] = [
    ("outputs/report06_measurement.json", "benchmark/plan_measurement.py",
     "이름은 `report06_*` 인데 생산자는 `plan_measurement`"),
    ("outputs/measurement_plan.json", "src/sigma_anchor.py :: write_measurement_plan",
     "이름은 `measurement_plan` 인데 생산자는 `sigma_anchor`"),
]

SCAN_EXT_EDIT = (".py", ".md")
SCAN_EXT_REBUILD = (".ipynb",)
SKIP_DIRS = {".git", "__pycache__", "_legacy_reports", "_legacy_builders",
             "outputs", "refs", "assets", "report_mesh", "prior_work", ".venv", "node_modules"}

#: ⛔ **고치면 안 되는 문서** — 두 부류다.
#:   (a) 날짜가 박힌 기록 — 그 날 그 이름이었다는 사실 자체가 기록이다. 바꾸면 기록이 거짓이 된다.
#:   (b) 다른 작업줄이 소유한 문서 — 이 스크립트가 남의 파일을 건드리지 않는다.
#:   (c) 이름 지도 본인 — 옛이름과 새이름을 **둘 다** 담는 것이 목적이라 치환하면 지도가 망가진다.
#: 여기 걸린 문서를 읽는 사람은 `docs/OUTPUT_NAMING.md` 표에서 옛이름을 찾아 새이름으로 옮긴다.
FROZEN_DOCS: tuple[str, ...] = (
    "docs/OUTPUT_NAMING.md",            # (c) 지도 본인
    "docs/PRIOR_WORK_COMPARISON.md",    # (b) 선행연구 작업줄 소유
    "docs/DRONE_ISAC_PRIOR_READING.md", # (b) 선행연구 작업줄 소유
    "docs/REBUILD_2026-07-30.md",       # (a) 재편 설계 기록
    "docs/ARCHIVE.md",                  # (a)
)
#: (a) 날짜/은퇴체계 기록 — 접두사로 건다
FROZEN_PREFIX: tuple[str, ...] = ("docs/RESUME_", "docs/AUDIT_FINDINGS_",
                                  "docs/READING_", "docs/REPORT13_", "docs/REPORT14_")


def _frozen(rel: str) -> bool:
    rel = rel.replace(os.sep, "/")
    return rel in FROZEN_DOCS or rel.startswith(FROZEN_PREFIX)


#: 살아 있는 문서 안에도 **옛 이름을 일부러 적어 둔 구간**이 있다 — 해독표가 그렇다.
#: 그 구간은 이 표시로 감싼다. 마크다운에서는 안 보이고(HTML 주석), 스크립트는 건너뛴다.
KEEP_ON = "<!-- keep-old-names:on -->"
KEEP_OFF = "<!-- keep-old-names:off -->"


def _protected_lines(txt: str) -> set[int]:
    """`keep-old-names` 구간에 들어가는 줄번호(1-based)를 모은다."""
    prot, on = set(), False
    for i, line in enumerate(txt.splitlines(), 1):
        if KEEP_ON in line:
            on = True
        if on:
            prot.add(i)
        if KEEP_OFF in line:
            on = False
    return prot


def _iter_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def _rel(p: str) -> str:
    return os.path.relpath(p, ROOT)


def scan(old_rel: str) -> dict:
    """옛 이름 문자열이 나오는 곳을 전부 찾아 분류한다.

    두 가지를 따로 센다 —
      full : `report13_freespace.json` 처럼 **확장자까지** 맞는 참조 (스크립트가 바꿀 대상)
      stem : `report13_sigma_grid` 처럼 확장자 없는 언급 (사람이 읽고 판단할 대상)
    """
    base = os.path.basename(old_rel)
    stem = os.path.splitext(base)[0]
    pat_full = re.compile(re.escape(base))
    pat_stem = re.compile(re.escape(stem) + r"(?![\w.])")

    hits = {"EDIT": [], "REBUILD": [], "STEM": [], "FROZEN": []}
    for p in _iter_files():
        ext = os.path.splitext(p)[1]
        if ext not in SCAN_EXT_EDIT + SCAN_EXT_REBUILD:
            continue
        if os.path.basename(p) == os.path.basename(__file__):
            continue
        try:
            txt = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if base not in txt and stem not in txt:
            continue
        kind = ("REBUILD" if ext in SCAN_EXT_REBUILD
                else "FROZEN" if _frozen(_rel(p)) else "EDIT")
        prot = _protected_lines(txt) if kind == "EDIT" else set()
        for i, line in enumerate(txt.splitlines(), 1):
            if i in prot:
                if pat_full.search(line):
                    hits["FROZEN"].append((_rel(p), i, line.strip()[:110]))
                continue
            if pat_full.search(line):
                hits[kind].append((_rel(p), i, line.strip()[:110]))
            elif pat_stem.search(line) and kind != "FROZEN":
                hits["STEM"].append((_rel(p), i, line.strip()[:110]))

    # outputs/*.json 안의 경로 문자열 — 생산자가 다시 돌면 저절로 바뀐다
    regen = []
    outdir = os.path.join(ROOT, "outputs")
    for fn in sorted(os.listdir(outdir)):
        if not fn.endswith(".json") or fn == base:
            continue
        p = os.path.join(outdir, fn)
        try:
            if base in open(p, encoding="utf-8").read():
                regen.append(_rel(p))
        except (UnicodeDecodeError, OSError):
            continue
    hits["REGEN"] = regen
    return hits


def _exists(rel: str) -> tuple[bool, float]:
    p = os.path.join(ROOT, rel)
    return (os.path.exists(p), os.path.getsize(p) / 1e6 if os.path.exists(p) else 0.0)


def _busy() -> list[str]:
    """산출물을 쓰고 있을 수 있는 프로세스를 찾는다. (죽이지 않는다 — 보고만 한다)

    ⚠ 생산자 목록을 손으로 나열하면 **빠진다**. 실제로 2026-07-31 예행 때 `viz_mesh_photo.py` ·
      `viz_cad_compare.py` 가 돌고 있었는데 손목록에는 없었다. 그래서 두 갈래로 넓게 잡는다 —
        (a) 이 저장소의 `src/` · `benchmark/` 스크립트를 돌리는 프로세스
        (b) 파이프라인 오케스트레이터(`regen_mesh_dependents`)
      넓게 잡아 헛경보가 나는 대가는 "조금 기다린다" 이고, 좁게 잡아 놓치는 대가는 반쪽 이름이다.
    """
    try:
        ps = subprocess.run(["ps", "-eo", "pid,etime,args"], capture_output=True, text=True,
                            timeout=20).stdout
    except Exception:
        return ["ps 실행 실패 — 수동으로 확인해라"]
    scripts = {f for f in os.listdir(os.path.join(ROOT, "src")) if f.endswith(".py")}
    scripts |= {f for f in os.listdir(_HERE) if f.endswith(".py")}
    scripts.discard(os.path.basename(__file__))
    out = []
    for line in ps.splitlines():
        if "rename_outputs" in line:
            continue
        toks = line.split()
        if any(os.path.basename(t) in scripts and ("src/" in t or "benchmark/" in t)
               for t in toks) or "regen_mesh_dependents" in line:
            out.append(line.strip()[:150])
    return out


def _all_renames(include_figs: bool, include_parts: bool):
    rows = list(JSON_RENAMES)
    if include_parts:
        rows += PART_RENAMES
    if include_figs:
        rows += FIG_RENAMES
    return rows


def dry_run(rows, verbose: bool) -> dict:
    tot = {"EDIT": 0, "REBUILD": 0, "STEM": 0, "REGEN": 0, "FROZEN": 0}
    files_edit: set[str] = set()
    files_frozen: set[str] = set()
    print("=" * 96)
    print(" 예행(dry-run) — 아무것도 바꾸지 않았다.  실제 적용: --apply --pipeline-is-idle")
    print("=" * 96)
    for old, new, producer, readers, holds in rows:
        ok, mb = _exists(old)
        h = scan(old)
        for k in tot:
            tot[k] += len(h[k])
        files_edit |= {f for f, _, _ in h["EDIT"]}
        files_frozen |= {f for f, _, _ in h["FROZEN"]}
        print(f"\n▶ {old}")
        print(f"   → {new}")
        print(f"   디스크   : {'있음' if ok else '⚠ 없음'}  {mb:.2f} MB")
        print(f"   생산자   : {producer}")
        print(f"   읽는 편  : {readers}")
        print(f"   내용     : {holds}")
        print(f"   참조     : EDIT {len(h['EDIT'])} · REBUILD(노트북) {len(h['REBUILD'])} · "
              f"REGEN(outputs/*.json) {len(h['REGEN'])} · FROZEN(기록·타작업줄) {len(h['FROZEN'])} · "
              f"확장자없는 언급 {len(h['STEM'])}")
        if old in FIG_DUP_WRITERS:
            print(f"   ⛔ 중복 생산자: {', '.join(FIG_DUP_WRITERS[old])} — 적용 차단")
        for f, i, line in h["EDIT"]:
            print(f"      EDIT     {f}:{i}  {line}")
        if verbose:
            for f, i, line in h["REBUILD"]:
                print(f"      REBUILD  {f}:{i}  {line}")
            for f, i, line in h["STEM"]:
                print(f"      STEM?    {f}:{i}  {line}")
        else:
            nb = sorted({f for f, _, _ in h["REBUILD"]})
            if nb:
                print(f"      REBUILD  {', '.join(nb)}  (빌더가 다시 쓴다 — 여기서 안 고친다)")
            fz = sorted({f for f, _, _ in h["FROZEN"]})
            if fz:
                print(f"      FROZEN   {', '.join(fz)}  (기록·타작업줄 — 옛이름 그대로 둔다)")
        if h["REGEN"]:
            print(f"      REGEN    {', '.join(h['REGEN'])}  (생산자 재실행으로 갱신)")
    print("\n" + "-" * 96)
    print(f" 합계 : 옮길 파일 {len(rows)}개 · 고칠 코드/문서 참조 {tot['EDIT']}곳"
          f"({len(files_edit)}개 파일) · 빌더가 다시 쓸 노트북 참조 {tot['REBUILD']}곳 · "
          f"재생성으로 따라올 JSON 내부 참조 {tot['REGEN']}곳")
    print(f" 그대로 두는 것 : 기록·타작업줄 문서 {tot['FROZEN']}곳({len(files_frozen)}개 파일) · "
          f"확장자 없는 언급 {tot['STEM']}곳(문장 속 표현 — 사람이 읽고 고친다)")
    print("-" * 96)
    return {"rows": len(rows), **tot,
            "edit_files": sorted(files_edit), "frozen_files": sorted(files_frozen)}


def apply(rows) -> int:
    blocked = [old for old, *_ in rows if old in FIG_DUP_WRITERS]
    if blocked:
        print("⛔ 적용 중단 — 같은 PNG 를 파이프라인 밖 생산자가 함께 쓴다:")
        for b in blocked:
            print(f"   {b} ← {', '.join(FIG_DUP_WRITERS[b])}")
        print("   옛 생산자를 정리하거나 --no-figs 로 그림을 빼고 돌려라.")
        return 2
    busy = _busy()
    if busy:
        print("⛔ 적용 중단 — 산출물을 쓰고 있을 수 있는 프로세스가 있다:")
        for b in busy:
            print(f"   {b}")
        print("   ⚠ 죽이지 마라. 끝나기를 기다려라.")
        return 3

    moved, edited = 0, 0
    for old, new, *_ in rows:
        # ⚠ 참조는 **옮기기 전에** 모은다 — 옮긴 뒤에 세면 순서에 따라 결과가 달라진다.
        targets = sorted({f for f, _, _ in scan(old)["EDIT"]})
        src, dst = os.path.join(ROOT, old), os.path.join(ROOT, new)
        if not os.path.exists(src):
            print(f"   건너뜀(없음) {old}")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if subprocess.run(["git", "mv", old, new], cwd=ROOT).returncode != 0:
            os.rename(src, dst)
        moved += 1
        ob, nb = os.path.basename(old), os.path.basename(new)
        for f in targets:
            p = os.path.join(ROOT, f)
            txt = open(p, encoding="utf-8").read()
            prot = _protected_lines(txt)
            lines = txt.splitlines(keepends=True)
            for i, line in enumerate(lines, 1):
                if i not in prot:
                    lines[i - 1] = line.replace(ob, nb)
            open(p, "w", encoding="utf-8").write("".join(lines))
            edited += 1
        print(f"   옮김 {old} → {new}   (참조 파일 {len(targets)}개 갱신)")
    print(f"\n✅ 파일 {moved}개 · 참조 파일 {edited}개 갱신 완료.")
    print("다음을 이 순서로 돌려라 —")
    print("  1) 그림 안에 구워진 옛 이름 4곳 수정 — src/make_report03_illuminators.py:237·242·245·252")
    print("     (docs/OUTPUT_NAMING.md §5.3 · 확장자가 없어 이 스크립트가 못 바꾼다)")
    print("  2) PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/regen_mesh_dependents.py --check")
    print("  3) 리포트 6편 재빌드 (regen_mesh_dependents stage 9)")
    print("  4) report_style.check_budget 6편 — 출처태그가 실제 JSON 을 여는지 확인")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="은퇴한 13편 번호 산출물 이름 이전 (기본 예행)")
    ap.add_argument("--apply", action="store_true", help="실제로 옮긴다(--pipeline-is-idle 동반 필수)")
    ap.add_argument("--pipeline-is-idle", action="store_true", help="재생성이 멈춰 있음을 확인했다")
    ap.add_argument("--only", default=None, help="옛 이름 하나만 (예: report13_freespace.json)")
    ap.add_argument("--no-figs", action="store_true", help="그림 이름은 건드리지 않는다")
    ap.add_argument("--no-parts", action="store_true", help="σ 격자 조각은 건드리지 않는다")
    ap.add_argument("-v", "--verbose", action="store_true", help="노트북·확장자없는 언급까지 전부 찍는다")
    ap.add_argument("--json", default=None, help="예행 요약을 이 경로에 JSON 으로 쓴다")
    a = ap.parse_args()

    rows = _all_renames(not a.no_figs, not a.no_parts)
    if a.only:
        rows = [r for r in rows if os.path.basename(r[0]) == a.only or r[0] == a.only]
        if not rows:
            print(f"그런 이름이 지도에 없다: {a.only}")
            return 1

    if a.apply:
        if not a.pipeline_is_idle:
            print("⛔ --apply 는 --pipeline-is-idle 과 함께 줘야 한다. 예행만 하려면 인자 없이 돌려라.")
            return 1
        return apply(rows)

    summary = dry_run(rows, a.verbose)
    print("\n[옮기지 않는 것]")
    print("  · 6편이 읽지 않는 옛 이름 산출물 —", len(NOT_READ_BY_ANY_REPORT), "묶음:")
    for name, prod, why in NOT_READ_BY_ANY_REPORT:
        print(f"      {name:<44} {prod:<52} {why}")
    print("  · 혼동쌍(이름 ↔ 생산자가 엇갈려 보이는 것):")
    for name, prod, why in CONFUSING_PAIRS:
        print(f"      {name:<44} {prod:<52} {why}")
    print("\n지도 원본: docs/OUTPUT_NAMING.md · 절↔코드 지도: docs/REPORT_CODE_MAP.md §7.1")
    if a.json:
        with open(os.path.join(ROOT, a.json) if not os.path.isabs(a.json) else a.json,
                  "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"요약 저장 → {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
