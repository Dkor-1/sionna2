#!/usr/bin/env python3
"""정정 전파 스윕 — 철회된 표현이 아직 살아 있는 파일·줄을 전수로 찾는다.

docs/RETRACTION_LOG.md 의 R1~R8 · A1~A7 (+ 신규 A8·A9) 각각에 대해
**표현 패턴**을 정의하고 저장소 전체에서 생존 인스턴스를 센다.

핵심 설계: JSON 은 파싱해서 **문자열 값과 키만** 훑는다. 숫자 배열을 정규식으로
긁으면 report13_sigma_grid 같은 격자 파일이 오탐을 수천 건 낸다(실제로 냈다).

usage:  PYTHONPATH=src:benchmark python benchmark/correction_sweep.py
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = "/workspace/sionna"
SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", "node_modules"}
# 이 파일 자신과 정본 기록은 "생존 인스턴스" 가 아니라 "정정 그 자체" 다.
CANONICAL = {
    "docs/RETRACTION_LOG.md",
    "benchmark/correction_sweep.py",
    "outputs/correction_sweep.json",
}


# --------------------------------------------------------------------------- #
#  패턴 정의 — (id, 설명, 판정함수)
#  판정함수는 문자열 한 덩이(줄 또는 JSON 문자열값)를 받아 bool 을 돌려준다.
# --------------------------------------------------------------------------- #
def _has(s: str, *words: str) -> bool:
    low = s.lower()
    return any(w.lower() in low for w in words)


PRIORITY_WORDS = ("우선권", "priority", "먼저", "prior art", "holder", "귀속",
                  "same equation", "같은 식", "two years earlier", "first")
VLAW_WORDS = ("v_max", "vmax", "무모호", "unambiguous", "prf/4", "prf / 4",
              "λ·prf", "lambda*prf", "lambda·prf", "속도식", "velocity law",
              "무모호 속도", "refrate", "도플러 범위")
NOVEL_WORDS = ("우리 발견", "our discovery", "우리가 처음", "최초", "novel", "novelty",
               "we are the first", "first to", "new law", "신규", "our contribution",
               "우리 기여", "ours")
STOCK_WORDS = ("sionna", "스톡", "stock")
DIFFR_NONE = ("회절이 없다", "회절 없", "no diffraction", "without diffraction",
              "회절을 지원하지 않", "lacks diffraction", "diffraction 없", "무회절",
              "diffraction is not", "does not support diffraction", "회절 미지원")


def p_r1_chen_priority(s: str) -> bool:
    """R1 — Chen 2024 를 우선권 보유자로 세운 표현."""
    if "chen" not in s.lower():
        return False
    if not _has(s, *PRIORITY_WORDS):
        return False
    return _has(s, *VLAW_WORDS) or _has(s, "식", "equation", "formula", "law")


def p_r1_ours_first(s: str) -> bool:
    """R1 — 속도식에 '우리가 처음/신규' 를 붙인 표현."""
    return _has(s, *VLAW_WORDS) and _has(s, *NOVEL_WORDS)


def p_r6_no_diffraction(s: str) -> bool:
    """R6 — 스톡 Sionna 에 회절이 없다는 표현."""
    return _has(s, *STOCK_WORDS) and _has(s, *DIFFR_NONE)


def p_r7_sbr48(s: str) -> bool:
    """R7 — SBR 48 회."""
    if "48" not in s:
        return False
    return bool(re.search(r"(?i)sbr[^.\n]{0,40}\b48\b|\b48\b[^.\n]{0,40}sbr", s))


def p_r8_19papers(s: str) -> bool:
    """R8 — 표적을 씬에 세운 저작 19편."""
    if "19" not in s:
        return False
    if not re.search(r"\b19\s*(편|papers|works|studies|건)", s):
        return False
    return _has(s, "target", "표적", "in_scene", "in scene", "씬에", "role_target")


def p_a1_2646(s: str) -> bool:
    """A1 — 이면각 오차 −26.46 dB."""
    if not re.search(r"[-−]?\b26\.46\b", s):
        return False
    return _has(s, "db", "이면각", "dihedral", "오차", "error")


def p_a2_slope_range(s: str) -> bool:
    """A2 — 측정 기울기 하한을 0.175 로 적은 구간 표기 (옳은 하한은 0.07)."""
    return bool(re.search(r"0\.175\s*(~|-|–|—|to|:)\s*0\.315", s))


def p_a2_two_anchors(s: str) -> bool:
    """A2 — Das·Yuan 을 독립 앵커 2건으로 센 표현."""
    low = s.lower()
    if not ("das" in low and "yuan" in low):
        return False
    return bool(re.search(r"(?i)독립.{0,12}(앵커|측정|2|두)|(two|2)\s+independent|"
                          r"독립\s*재현|independent\s+(anchor|measurement|source)|"
                          r"앵커\s*2\s*건|2\s*건의?\s*독립", s))


def p_a3_plastic_unsourced(s: str) -> bool:
    """A3 — plastic εr 2.7 이 출처 없다는 표현 (셸 두께가 진짜 무출처)."""
    if not _has(s, "2.7"):
        return False
    if not _has(s, "plastic", "플라스틱", "eps_r", "epsilon", "εr", "유전율"):
        return False
    return _has(s, "출처 없", "무출처", "unsourced", "no source", "출처가 없",
                "근거 없", "tier 2", "출처 미상")


def p_a4_battery(s: str) -> bool:
    """A4 — εr 1.4 / σ 1.2 를 배터리로 귀속한 표현 (실제로는 챔버 흡수체)."""
    if not (("1.4" in s) and ("1.2" in s)):
        return False
    return _has(s, "배터리", "battery")


def p_a5_mlfmm(s: str) -> bool:
    """A5 — Ziganshin 차량 dBsm 을 MLFMM 대조로 적은 표현 (실제는 FEKO PO 솔버)."""
    low = s.lower()
    if "mlfmm" not in low:
        return False
    if not _has(s, "car", "vehicle", "차량", "ziganshin"):
        return False
    return _has(s, "검증", "validat", "대조", "against", "compar", "vs")


def p_a7_report_v1(s: str) -> bool:
    """A7 — 기술보고서를 v1 으로 적은 표현 (내용은 v2 / Version 1.2)."""
    return bool(re.search(r"(?i)2504\.21719v1|기술보고서[^.\n]{0,30}v1\b", s))


def p_phantom_inversion(s: str) -> bool:
    """신규 — Phantom 2 를 1.8~18.2 GHz 원거리장 기체로 적은 표현 (그건 Phantom 3)."""
    low = s.lower()
    if "phantom 2" not in low and "phantom2" not in low:
        return False
    return bool(re.search(r"1\.8\s*[-–~]\s*18\.2|18\.2\s*ghz|원거리장|far.?field|무향", low))


def p_ziganshin_perpose(s: str) -> bool:
    """신규 — Ziganshin 0.7→19.0 s 를 per-pose 로 읽히게 적은 표현.
    실제는 360 각도점 **전체 스윕** 시간 (per point 1.94 / 52.8 ms)."""
    if not re.search(r"19\.0\s*s|0\.7\s*(s|초)|15\s*[-–~]\s*27\s*(배|x|×)", s):
        return False
    if not _has(s, "ziganshin", "회절", "diffraction", "ladder", "사다리"):
        return False
    # per-angular-point 정정이 같은 문자열에 이미 붙어 있으면 생존 인스턴스가 아니다
    return not _has(s, "angular point", "각도점", "360", "per point", "1.94", "52.8")


PATTERNS = [
    ("R1_chen_as_priority_holder", "Chen 2024 를 무모호 속도식 우선권 보유자로 세운 표현 "
     "(정본: Abratkiewicz IEEE JSTARS 2023 식(16) p.3476)", p_r1_chen_priority),
    ("R1_velocity_law_ours_or_novel", "속도식에 '우리 것/최초/신규' 를 붙인 표현", p_r1_ours_first),
    ("R6_stock_sionna_no_diffraction", "스톡 Sionna 에 회절이 없다는 표현 "
     "(정본: 1차 UTD 쐐기회절 구현됨, 기본값만 꺼져 있음)", p_r6_no_diffraction),
    ("R7_sbr_48_occurrences", "기술보고서 SBR 48 회 (정본: 44 회)", p_r7_sbr48),
    ("R8_19_papers_target_in_scene", "표적을 씬에 세운 저작 19 편 (정본: 7 히트 / 고유 6 편)",
     p_r8_19papers),
    ("A1_dihedral_minus_26_46_db", "이면각 오차 −26.46 dB (정본: 출처 없음)", p_a1_2646),
    ("A2_slope_range_0175_0315", "측정 기울기 구간 0.175~0.315 (정본: 0.07~0.315)",
     p_a2_slope_range),
    ("A2_das_yuan_two_independent", "Das·Yuan 을 독립 앵커 2 건으로 센 표현 "
     "(정본: Das 는 Yuan 원자료의 재분석 = 측정 1 건)", p_a2_two_anchors),
    ("A3_plastic_eps_unsourced", "plastic εr 2.7 무출처 표현 "
     "(정본: Zechmeister & Lacik COMITE 2019. 무출처인 건 셸 두께)", p_a3_plastic_unsourced),
    ("A4_battery_eps_mixup", "εr 1.4 / σ 1.2 를 배터리로 귀속 (정본: 챔버 흡수체)", p_a4_battery),
    ("A5_ziganshin_mlfmm_validation", "Ziganshin 차량 dBsm 을 MLFMM 대조로 표기 "
     "(정본: FEKO PO 솔버)", p_a5_mlfmm),
    ("A7_techreport_v1", "기술보고서를 v1 으로 표기 (정본: arXiv:2504.21719v2 / Version 1.2)",
     p_a7_report_v1),
    ("NEW_phantom2_phantom3_inversion", "Phantom 2 를 1.8~18.2 GHz 원거리장 기체로 표기 "
     "(정본: Phantom 2 = 11~26 GHz 근거리장, Phantom 3 = 1.8~18.2 GHz 무향실)",
     p_phantom_inversion),
    ("NEW_ziganshin_runtime_per_pose", "Ziganshin 0.7→19.0 s 를 per-pose 로 읽히게 표기 "
     "(정본: 360 각도점 전체 스윕. per point 1.94 → 52.8 ms)", p_ziganshin_perpose),
]


# --------------------------------------------------------------------------- #
#  파일 순회
# --------------------------------------------------------------------------- #
def iter_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            if rel in CANONICAL:
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".md", ".py", ".txt", ".bib", ".json", ".ipynb", ".csv"):
                yield rel, full, ext


def line_of(raw_lines: list[str], needle: str, start: int = 0) -> int:
    """raw 텍스트에서 needle 을 담은 첫 줄 번호(1-base). 못 찾으면 0."""
    probe = needle[:80]
    for i in range(start, len(raw_lines)):
        if probe and probe in raw_lines[i]:
            return i + 1
    return 0


def scan_text(rel, path, results):
    try:
        raw = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return
    for ln, line in enumerate(raw.splitlines(), 1):
        if len(line) > 4000:
            line = line[:4000]
        for pid, _desc, fn in PATTERNS:
            try:
                if fn(line):
                    results[pid].append(dict(file=rel, line=ln, text=line.strip()[:400]))
            except Exception:
                pass


def scan_json(rel, path, results):
    try:
        raw = open(path, encoding="utf-8", errors="replace").read()
        data = json.loads(raw)
    except Exception:
        return scan_text(rel, path, results)
    raw_lines = raw.splitlines()
    hits = []

    def walk(o, p=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str):
                    hits.append((p + "." + k, k))
                walk(v, p + "." + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, p + "[%d]" % i)
        elif isinstance(o, str):
            hits.append((p, o))

    walk(data)
    for jpath, s in hits:
        if len(s) > 6000:
            s = s[:6000]
        for pid, _desc, fn in PATTERNS:
            try:
                if fn(s):
                    results[pid].append(dict(file=rel, line=line_of(raw_lines, s),
                                             json_path=jpath, text=s.strip()[:400]))
            except Exception:
                pass


def scan_ipynb(rel, path, results):
    try:
        nb = json.load(open(path, encoding="utf-8", errors="replace"))
    except Exception:
        return
    for ci, cell in enumerate(nb.get("cells", [])):
        src = cell.get("source", [])
        if isinstance(src, str):
            src = src.splitlines(True)
        for li, line in enumerate(src, 1):
            line = line.rstrip("\n")[:4000]
            for pid, _desc, fn in PATTERNS:
                try:
                    if fn(line):
                        results[pid].append(dict(file=rel, cell=ci, cell_line=li,
                                                 line=0, text=line.strip()[:400]))
                except Exception:
                    pass


def main():
    results = {pid: [] for pid, _d, _f in PATTERNS}
    n_files = 0
    for rel, full, ext in iter_files():
        n_files += 1
        if ext == ".json":
            scan_json(rel, full, results)
        elif ext == ".ipynb":
            scan_ipynb(rel, full, results)
        else:
            scan_text(rel, full, results)

    out = dict(
        meta=dict(
            purpose="철회 R1~R8 · 정정 A1~A7 (+신규) 의 생존 인스턴스 전수 조사",
            root=ROOT,
            files_scanned=n_files,
            json_policy="JSON 은 파싱 후 문자열 값·키만 검사 (숫자 배열 오탐 제거)",
            excluded=sorted(CANONICAL),
        ),
        patterns=[dict(id=pid, description=desc, n_hits=len(results[pid]))
                  for pid, desc, _f in PATTERNS],
        hits=results,
    )
    dest = os.path.join(ROOT, "outputs", "correction_sweep_raw.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("files scanned:", n_files)
    for pid, desc, _f in PATTERNS:
        print("%-38s %4d" % (pid, len(results[pid])))
    print("->", dest)


if __name__ == "__main__":
    sys.exit(main())
