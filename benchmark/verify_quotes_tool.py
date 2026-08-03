#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_quotes_tool.py — 우리 기록물에 박힌 모든 (pdf, page, quote) 삼중항을 원문 PDF 에 대고
기계적으로 채점하는 게이트.

왜 있는가
---------
이번 세션에서만 여덟 건을 철회했다. 전부 "원문을 열기 전에 단언" 했기 때문이다.
그래서 규칙을 하나로 못박는다: 주장은 PDF 경로 + 페이지 + 인용문을 달고 다니며,
그 인용문은 이 도구를 통과해야 한다. 통과 못 하면 UNVERIFIED 이고, 그것도 정직한 결과다.
빈칸을 그럴듯하게 채우는 것이 이 라운드가 막으려는 실패다.

채점 등급 (요구된 네 가지)
--------------------------
  verbatim       명시된 페이지에서 연속 문자열로 발견 (공백/하이픈/합자 정규화 후)
  verbatim_doc   문서 어딘가에는 연속으로 있으나 명시된 페이지가 아님 (= 페이지가 틀림)
  reconstructed  연속은 아니지만 내용어가 전부 그 페이지에 있음.
                 표를 이미지에서 눈으로 읽어 옮기면 이 모양이 된다. 정당하다. 다만 '인용'은 아니다.
  unverified     내용어가 없다. 이것이 실패 케이스 — 날조이거나 오귀속이며 둘 다 중요하다.

채점에 못 들어간 것은 grade 가 아니라 status 로 따로 센다 (pdf_unresolved / pdf_missing /
source_not_pdf 등). "확인됨"과 "확인 못 함"을 절대 섞지 않는다.

함정 처리
---------
  * 합자(fi, fl, ffi …)          → NFKC 정규화
  * soft hyphen(U+00AD)          → 제거
  * 줄바꿈 하이픈("scat-\ntering") → squash 비교에서 자동 해소
  * 유니코드 따옴표/대시/공백     → 정규화
  * 2단 조판 읽기순서            → get_text 를 raw/sorted 두 모드로 뽑아 둘 다에 대고 시도
  * 페이지 경계를 걸친 인용       → 문서 전체 연결본에서 찾고 걸친 페이지 집합을 되돌려 판정
  * 0-base / 1-base 페이지 혼용   → 두 해석 모두 후보로 놓고 어느 쪽이 맞았는지 기록
  * 텍스트 레이어 없는 이미지 표  → unverified 로 떨어뜨리지 않는다. reconstructed +
                                    machine_can_decide=false 로 격리해서 따로 센다.
  * 생략부호("…", "[...]")       → 조각별로 나눠 전부 연속이면 verbatim(+elided)

사용법
------
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_quotes_tool.py
  ... --only deepread_w4.json prior_settled_h8.json   # 파일 일부만
  ... --summary-only                                  # 콘솔 요약만
  ... --no-cache                                      # 페이지 텍스트 디스크 캐시 끄기

출력: outputs/quote_audit.json (원본 JSON 하나 처리할 때마다 증분 저장 → 중간에 죽어도 남는다)
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict

# ----------------------------------------------------------------------------- 설정
REPO = "/home/yunjung/workspace/sionna2"
OUTPUTS = os.path.join(REPO, "outputs")
OUT_PATH = os.path.join(OUTPUTS, "quote_audit.json")
SELF_NAME = "quote_audit.json"          # 자기 출력은 다시 훑지 않는다

PDF_ROOTS = [
    "/data/public/sionna_jeong/papers_isac_sionna",
    "/data/public/sionna_jeong/sionna_papers_by_task",
    "/data/public/sionna_jeong/reference_library",
    "/data/public/jeong/papers",
    "/data/public/OpenISAC",
    "/home/yunjung/workspace/sionna2",
]
CACHE_DIR = os.environ.get("QUOTE_CACHE_DIR", "/tmp/sionna2_quote_cache")

DO_HUNT = True          # unverified 건을 아카이브 전수 추적할지 (--no-hunt 로 끈다)
TEXT_SOURCE_EXT = (".py", ".md", ".txt", ".rst", ".bib", ".tex", ".json", ".yaml", ".yml")

# quote 로 인정할 키
QUOTE_KEY_RE = re.compile(r"quote", re.I)
# quote 컨테이너 안에서 본문을 담는 키
INNER_TEXT_KEYS = {"q", "text", "quote", "verbatim", "sentence", "line", "value", "excerpt"}
# quote 처럼 보이지만 인용문이 아닌 키 (카운트·정책·메모)
QUOTE_KEY_DENY = re.compile(
    r"(n_quotes|quotes?_(verified|checked|total|count|coverage|policy|selfcheck|"
    r"flagged|carried|recorded|rechecked|failing|re_verified|scope|method|note|"
    r"page|source|fragment_checked|independently_reverified|partially_verified|"
    r"unverified_by_machine|variant|frequency)|quoted_(hz|db|but_not)|"
    r"facts_quoted|_quoted_for_|long_quote|quote_of_what|asymptotic_quoted)",
    re.I,
)
PAGE_KEYS_SELF = ["page", "page_no", "page_num", "page_number", "page0", "page_idx",
                  "page_index", "pp", "p", "pages", "where", "loc", "location"]
PAGE_KEYS_ANCESTOR = ["page", "page_no", "page_num", "page_number", "page0", "page_idx"]
# pdf 후보 키: 정확 일치 우선순위 + 느슨한 패턴(pdf_path_published, pdf_path_preprint …)
PDF_KEYS = ["pdf_path", "pdf", "pdf_file", "source_pdf", "path", "file", "filepath",
            "file_path", "basename", "doc", "document", "source", "src", "where"]
PDF_KEY_RE = re.compile(r"(pdf|path|file|basename|source|doc)", re.I)
# "인용문이 없다"고 정직하게 적어둔 자리 — 실패가 아니라 기권이다. 따로 센다.
ABSTAIN_RE = re.compile(
    r"^\s*[⚠⭐\-–—•\(\[]*\s*(unverified|not\s*found|not_found|no\s*quote|none\b|n/?a\b|"
    r"없음|해당\s*없음|인용\s*없음|미확인|확인\s*불가|없다)", re.I)

STOP = set("""a an the of to in on for and or but with without by as at from into over under
this that these those is are was were be been being it its it's their there here we our us they
he she his her which who whom whose what when where why how not no nor so if then than
can could may might must shall should will would do does did done have has had having
such per via each any all both more most other others same only also very much many few
i ii iii iv v vi about between within across during after before while against upon
one two three e.g eg i.e ie etc et al fig figure table section eq equation ref refs
""".split())

# ------------------------------------------------------------------- 텍스트 정규화
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−⁃﹘﹣－"), "-")
_QUOTES = {ord("‘"): "'", ord("’"): "'", ord("‚"): "'", ord("‛"): "'",
           ord("′"): "'", ord("ʼ"): "'",
           ord("“"): '"', ord("”"): '"', ord("„"): '"', ord("″"): '"'}
_SPACES = dict.fromkeys(map(ord, "         "
                                 "     　​‌‍﻿"), " ")
_DROP = dict.fromkeys(map(ord, "­​‌‍﻿"), None)


def norm(s: str) -> str:
    """공백 보존 정규화 — 사람 눈에 '같은 문장'이면 같아지도록."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)      # 합자 fi/fl/ffi -> f i, 전각 -> 반각
    s = s.translate(_DROP)                    # soft hyphen 등 제거
    s = s.translate(_DASHES).translate(_QUOTES).translate(_SPACES)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


# 우리 기록물은 수식 기호를 ASCII 이름으로 옮겨 적는다("sigma = -12 dBsm", "lambda").
# PDF 에는 글리프(σ, λ)가 들어 있다. 양쪽을 같은 이름으로 펴 주지 않으면 멀쩡한 인용이
# 전부 unverified 로 떨어진다 — reference_library 의 첫 채점에서 실제로 그렇게 됐다.
_GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ϵ": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ϑ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi", "ρ": "rho",
    "σ": "sigma", "ς": "sigma", "τ": "tau", "υ": "upsilon", "φ": "phi", "ϕ": "phi",
    "χ": "chi", "ψ": "psi", "ω": "omega",
    "Α": "alpha", "Β": "beta", "Γ": "gamma", "Δ": "delta", "Ε": "epsilon", "Ζ": "zeta",
    "Η": "eta", "Θ": "theta", "Ι": "iota", "Κ": "kappa", "Λ": "lambda", "Μ": "mu",
    "Ν": "nu", "Ξ": "xi", "Ο": "omicron", "Π": "pi", "Ρ": "rho", "Σ": "sigma", "Τ": "tau",
    "Υ": "upsilon", "Φ": "phi", "Χ": "chi", "Ψ": "psi", "Ω": "omega",
}
_GREEK_RE = re.compile("[" + "".join(_GREEK) + "]")


_DEG_RE = re.compile(r"°|\bdegrees?\b", re.I)


def degreek(s: str) -> str:
    """그리스 문자와 도(°) 기호를 이름으로 편다. 우리 기록은 'sigma'/'90 degrees',
    PDF 는 'σ'/'90°' 로 적는다. 펴 주지 않으면 멀쩡한 인용이 unverified 로 떨어진다."""
    if not s:
        return s
    return _DEG_RE.sub("deg", _GREEK_RE.sub(lambda m: _GREEK[m.group(0)], s))


def squash(s: str) -> str:
    """영숫자만 남긴 압축본 — 공백·구두점·줄바꿈 하이픈·조판 차이를 한 번에 흡수."""
    if not s:
        return ""
    s = degreek(unicodedata.normalize("NFKC", s).lower())
    return re.sub(r"[^0-9a-zÀ-ɏ一-鿿가-힣]+", "", s)


_WORD_RE = re.compile(r"[0-9a-zÀ-ɏͰ-Ͽ가-힣]+")


def content_words(s: str):
    """내용어 = 불용어·1~2글자 잡음을 뺀 토큰. 숫자는 유의미하므로 남긴다."""
    toks = _WORD_RE.findall(degreek(norm(s)))
    out = []
    for t in toks:
        if t in STOP:
            continue
        if len(t) < 3 and not t.isdigit():
            continue
        out.append(t)
    return out


def hangul_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    han = sum(1 for c in letters if "가" <= c <= "힣")
    return han / len(letters)


# --------------------------------------------------------------------- PDF 인덱스
_pdf_index = None


def pdf_index():
    global _pdf_index
    if _pdf_index is not None:
        return _pdf_index
    idx = defaultdict(list)
    for root in PDF_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
            for fn in filenames:
                if fn.lower().endswith(".pdf"):
                    idx[fn.lower()].append(os.path.join(dirpath, fn))
                    idx[squash(fn[:-4])].append(os.path.join(dirpath, fn))
    _pdf_index = idx
    return idx


_PATHLIKE = re.compile(r"[/\w][\w./\-+ ()가-힣,'&]*\.pdf", re.I)


def resolve_source(val: str):
    """문자열에서 실제로 열 수 있는 파일 경로를 뽑아낸다. (path, how) 또는 (None, reason)."""
    if not isinstance(val, str) or not val.strip():
        return None, "empty"
    v = val.strip()
    if os.path.isfile(v):
        return v, "direct"
    if v.lower().endswith(TEXT_SOURCE_EXT) and os.path.isfile(os.path.join(REPO, v)):
        return os.path.join(REPO, v), "repo_rel"
    m = _PATHLIKE.search(v)
    cand = m.group(0).strip() if m else (v if v.lower().endswith(".pdf") else None)
    if cand is None:
        return None, "not_a_path"
    if os.path.isfile(cand):
        return cand, "direct"
    idx = pdf_index()
    base = os.path.basename(cand).lower()
    if base in idx:
        return idx[base][0], "basename"
    sq = squash(base[:-4])
    if sq in idx:
        return idx[sq][0], "squashed_basename"
    # 접두 매칭 (arXiv 번호 등)
    for k in (base, sq):
        hits = [p for kk, vv in idx.items() if kk.startswith(k[:14]) and len(k) >= 8 for p in vv]
        if len(set(hits)) == 1:
            return sorted(set(hits))[0], "prefix"
    return None, "unresolved:" + os.path.basename(cand)


# ------------------------------------------------------- 제목으로 PDF 찾기(경로 미기재분)
_head_index = None
LABEL_KEYS = ["title", "citation", "citation_ko", "work", "paper", "short", "name", "id",
              "key", "ref", "reference", "basename", "doc", "source", "venue_and_pub_status"]


def head_index():
    """아카이브 전 PDF 의 1쪽 머리(제목/저자)를 인덱싱한다. 경로가 안 적힌 인용문을
    제목으로 되찾기 위한 것 — 되찾은 건은 provenance 를 'inferred' 로 따로 센다."""
    global _head_index
    if _head_index is not None:
        return _head_index
    cache = os.path.join(CACHE_DIR, "head_index_v1.json")
    paths = sorted({p for v in pdf_index().values() for p in v})
    sig = hashlib.sha1(("|".join(paths)).encode()).hexdigest()
    if os.path.isfile(cache):
        try:
            blob = json.load(open(cache, encoding="utf-8"))
            if blob.get("sig") == sig:
                _head_index = blob["items"]
                return _head_index
        except Exception:
            pass
    items = []
    try:
        import fitz
    except Exception:
        _head_index = []
        return _head_index
    for p in paths:
        head = ""
        try:
            d = fitz.open(p)
            head = "\n".join(d[i].get_text() for i in range(min(2, len(d))))[:4000]
            d.close()
        except Exception:
            pass
        items.append({"path": p,
                      "tokens": sorted(set(content_words(os.path.basename(p)[:-4].replace("_", " "))
                                           + content_words(head)))})
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        json.dump({"sig": sig, "items": items}, open(cache, "w", encoding="utf-8"))
    except Exception:
        pass
    _head_index = items
    return _head_index


_title_memo = {}


def resolve_by_title(label, min_cov=0.8, min_tokens=4, margin=0.08):
    if not label or len(label) < 12:
        return None, None
    if label in _title_memo:
        return _title_memo[label]
    toks = [t for t in dict.fromkeys(content_words(label)) if len(t) >= 3][:40]
    if len(toks) < min_tokens:
        return None, None
    scored = []
    for it in head_index():
        s = set(it["tokens"])
        cov = sum(1 for t in toks if t in s) / len(toks)
        scored.append((cov, it["path"]))
    scored.sort(reverse=True)
    res = (None, None)
    if scored and scored[0][0] >= min_cov:
        if len(scored) > 1 and scored[0][0] - scored[1][0] < margin and scored[0][0] < 0.95:
            res = (None, "ambiguous")
        else:
            res = (scored[0][1], round(scored[0][0], 3))
    _title_memo[label] = res
    return res


# ------------------------------------------------------------------ 문서 텍스트 캐시
class Doc:
    """PDF/텍스트 파일 하나의 정규화된 본문. 페이지 오프셋을 들고 있어 span→page 역산이 된다."""

    def __init__(self, path):
        self.path = path
        self.kind = "pdf" if path.lower().endswith(".pdf") else "text"
        self.pages_raw = []      # get_text() 기본
        self.pages_sorted = []   # get_text(sort=True)
        self.meta = {}           # PDF 메타데이터(제작 도구 주장 검증용)
        self.page_imgs = []      # 페이지별 래스터 이미지 수(그림 속 표 판별용)
        self.error = None
        self._load()
        self.n_pages = len(self.pages_raw)
        self.page_sq = [squash(t) for t in self.pages_raw]
        self.page_sq_sorted = [squash(t) for t in self.pages_sorted]
        self.page_norm = [norm(t) for t in self.pages_raw]
        self.page_norm_sorted = [norm(t) for t in self.pages_sorted]
        self.page_words = [set(content_words(t)) | set(content_words(s))
                           for t, s in zip(self.pages_raw, self.pages_sorted)]
        # 문서 전체 연결본 + 페이지 경계
        self.doc_sq = ""
        self.bounds = []
        for i, t in enumerate(self.page_sq):
            self.bounds.append((len(self.doc_sq), len(self.doc_sq) + len(t), i))
            self.doc_sq += t
        self.doc_sq_sorted = "".join(self.page_sq_sorted)
        self.doc_words = set().union(*self.page_words) if self.page_words else set()
        self.no_text_layer = [len(t.strip()) < 40 for t in self.pages_raw]

    def _load(self):
        if self.kind == "text":
            try:
                txt = open(self.path, encoding="utf-8", errors="replace").read()
            except Exception as e:                      # pragma: no cover
                self.error = f"read_error:{e}"
                txt = ""
            self.pages_raw = [txt]
            self.pages_sorted = [txt]
            return
        try:
            import fitz
            d = fitz.open(self.path)
            try:
                self.meta = dict(d.metadata or {})
            except Exception:
                self.meta = {}
            for pg in d:
                self.pages_raw.append(pg.get_text())
                try:
                    self.page_imgs.append(len(pg.get_images()))
                except Exception:
                    self.page_imgs.append(0)
                try:
                    self.pages_sorted.append(pg.get_text("text", sort=True))
                except Exception:
                    self.pages_sorted.append("")
            d.close()
        except Exception as e:
            self.error = f"open_error:{type(e).__name__}:{e}"
            self.pages_raw, self.pages_sorted = [], []

    def pages_of_span(self, a, b):
        return [i for (s, e, i) in self.bounds if a < e and b > s]


_doc_cache = {}


def get_doc(path, use_cache=True):
    if path in _doc_cache:
        return _doc_cache[path]
    d = None
    key = None
    if use_cache:
        try:
            st = os.stat(path)
            key = hashlib.sha1(f"{path}|{st.st_size}|{int(st.st_mtime)}|v6".encode()).hexdigest()
            cp = os.path.join(CACHE_DIR, key + ".pkl")
            if os.path.isfile(cp):
                with open(cp, "rb") as f:
                    d = pickle.load(f)
        except Exception:
            d = None
    if d is None:
        d = Doc(path)
        if use_cache and key:
            try:
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(os.path.join(CACHE_DIR, key + ".pkl"), "wb") as f:
                    pickle.dump(d, f, protocol=4)
            except Exception:
                pass
    _doc_cache[path] = d
    return d


# -------------------------------------------------- 아카이브 전수 추적(오귀속 vs 날조)
_archive_sq = None


def archive_sq_index(quiet=False):
    """아카이브 전 PDF 의 squash 본문 + 페이지 경계. unverified 인용문이 '어느 논문에도
    없는 문장(날조)'인지 '다른 논문의 문장(오귀속)'인지 가르는 데 쓴다. 이 구분이 없으면
    unverified 목록은 조치 불가능한 명단일 뿐이다."""
    global _archive_sq
    if _archive_sq is not None:
        return _archive_sq
    paths = sorted({p for v in pdf_index().values() for p in v})
    sig = hashlib.sha1(("|".join(paths) + "|v1").encode()).hexdigest()
    cache = os.path.join(CACHE_DIR, "archive_sq_" + sig[:12] + ".pkl")
    if os.path.isfile(cache):
        try:
            with open(cache, "rb") as f:
                _archive_sq = pickle.load(f)
            return _archive_sq
        except Exception:
            pass
    if not quiet:
        print(f"      아카이브 전수 색인 생성 중 ({len(paths)} PDF) — 최초 1회만 …")
    idx = []
    try:
        import fitz
    except Exception:
        _archive_sq = idx
        return idx
    for n, p in enumerate(paths):
        try:
            d = fitz.open(p)
            txt, bounds = "", []
            for i, pg in enumerate(d):
                t = squash(pg.get_text())
                bounds.append((len(txt), len(txt) + len(t), i))
                txt += t
            d.close()
            idx.append({"path": p, "sq": txt, "bounds": bounds})
        except Exception:
            continue
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump(idx, f, protocol=4)
    except Exception:
        pass
    _archive_sq = idx
    return idx


def _sq_of(path):
    for it in archive_sq_index():
        if it["path"] == path:
            return it["sq"]
    return ""


def relation(attributed, other):
    """찾은 곳이 '같은 파일의 사본'인지 '같은 연구의 다른 판'인지 '아예 다른 논문'인지.
    이걸 구분하지 않으면 중복 사본을 오귀속이라고 부풀리게 된다."""
    if not attributed:
        return "unknown"
    if os.path.basename(attributed).lower() == os.path.basename(other).lower():
        return "duplicate_copy"
    a, b = _sq_of(attributed), _sq_of(other)
    if a and b and (a[:4000] == b[:4000] or a == b):
        return "duplicate_copy"
    hi = {it["path"]: set(it["tokens"]) for it in head_index()}
    ta, tb = hi.get(attributed, set()), hi.get(other, set())
    if ta and tb:
        j = len(ta & tb) / max(1, len(ta | tb))
        if j >= 0.55:
            return "same_work_other_version"
    return "different_work"


def hunt(qsq, exclude=None, anchor=70, max_hits=4):
    """이 문장이 아카이브 어디에 실제로 있는가 — 오귀속 vs 날조를 가르는 유일한 방법."""
    if len(qsq) < 30:
        return []
    mid = max(0, (len(qsq) - anchor) // 2)
    probes = [qsq[mid:mid + anchor], qsq[:anchor], qsq[-anchor:]]
    hits = []
    for it in archive_sq_index():
        if exclude and os.path.abspath(it["path"]) == os.path.abspath(exclude):
            continue
        for pr in probes:
            if len(pr) < 30:
                continue
            j = it["sq"].find(pr)
            if j >= 0:
                pg = next((b[2] for b in it["bounds"] if b[0] <= j < b[1]), None)
                hits.append({"pdf": it["path"], "page_1based": (pg + 1) if pg is not None else None,
                             "relation_to_attributed_pdf": relation(exclude, it["path"])})
                break
        if len(hits) >= max_hits:
            break
    return hits


# ------------------------------------------------------------------ 기록물에서 수집
_ELLIPSIS = re.compile(r"(\.\.\.|…|\[\s*\.\.\.\s*\]|\[…\]|\s+/\s+|\s+;;\s+)")


def parse_pages(val):
    """페이지 값에서 정수 후보를 뽑는다. '17', 17, 'p.3476', '1-2', [3,4] 모두 허용."""
    if val is None:
        return []
    if isinstance(val, bool):
        return []
    if isinstance(val, int):
        return [val]
    if isinstance(val, float):
        return [int(val)] if val == int(val) else []
    if isinstance(val, (list, tuple)):
        out = []
        for v in val:
            out += parse_pages(v)
        return out
    if isinstance(val, str):
        s = val.strip()
        if len(s) > 60:                     # 산문이지 페이지 표기가 아니다
            return []
        nums = [int(x) for x in re.findall(r"\d{1,4}", s)]
        return [n for n in nums if 0 <= n <= 2000][:4]
    return []


def page_keys_for(quote_key):
    """quote2 -> page2 · quote_eca -> page_eca · quote -> page.
    한 dict 안에 quote/quote2/quote3 가 나란히 사는 스키마가 흔하다. 접미사를 맞추지 않으면
    quote2 를 quote 의 페이지로 채점해서 '페이지 틀림'을 대량으로 날조하게 된다."""
    m = re.match(r"(.*?)quote(.*)$", str(quote_key), re.I)
    if not m:
        return list(PAGE_KEYS_SELF), False
    pre, suf = m.group(1), m.group(2)
    exact = []
    for cand in (f"{pre}page{suf}", f"page{suf}", f"{pre}pg{suf}", f"p{suf}"):
        if cand and cand not in exact:
            exact.append(cand)
    return exact, True


def find_page(node, ancestors, quote_key=None):
    exact, suffixed = page_keys_for(quote_key) if quote_key else ([], False)
    if isinstance(node, dict):
        for k in exact:
            if k in node:
                pp = parse_pages(node[k])
                if pp:
                    return pp, k, "self_suffix_matched"
        for k in PAGE_KEYS_SELF:
            if k in node:
                pp = parse_pages(node[k])
                if pp:
                    where = "self"
                    if suffixed and quote_key.lower() not in ("quote", "q", "text") and k == "page":
                        where = "self_generic_page_for_suffixed_quote"
                    return pp, k, where
    for anc, akey in reversed(ancestors):
        for k in PAGE_KEYS_ANCESTOR:
            if k in anc:
                pp = parse_pages(anc[k])
                if pp:
                    return pp, k, "ancestor"
    return [], None, None


def _pdf_key_order(d):
    """같은 dict 에 pdf 후보가 여럿이면(published/preprint 등) 전부 돌려준다."""
    keys = [k for k in PDF_KEYS if k in d and isinstance(d[k], str)]
    extra = [k for k in d
             if isinstance(k, str) and isinstance(d[k], str) and k not in keys
             and PDF_KEY_RE.search(k) and (".pdf" in d[k].lower() or d[k].lower().endswith(TEXT_SOURCE_EXT))]
    return keys + sorted(extra)


def find_sources(node, ancestors):
    """열 수 있는 소스 후보를 우선순위대로 모두 돌려준다. [(path, raw, prov), ...]"""
    chain = ([(node, "self")] if isinstance(node, dict) else []) + \
            [(a, "ancestor") for a, _ in reversed(ancestors)]
    out, seen, tried = [], set(), []
    for d, where in chain:
        for k in _pdf_key_order(d):
            v = d[k]
            if not v.strip():
                continue
            p, how = resolve_source(v)
            if p and p not in seen:
                seen.add(p)
                out.append((p, v, f"{where}:{k}:{how}"))
            elif not p and ".pdf" in v.lower():
                tried.append((v, f"{where}:{k}:{how}"))
        if out:
            break            # 가장 가까운 층에서 찾았으면 더 위로 올라가지 않는다
    if out:
        return out, tried
    # 경로가 없다 → 가까운 조상에 붙은 제목/인용문구로 아카이브에서 되찾아 본다.
    for d, where in chain:
        label = " ".join(str(d[k]) for k in LABEL_KEYS
                         if isinstance(d.get(k), str) and 8 <= len(d[k]) <= 400)
        if not label:
            continue
        p, cov = resolve_by_title(label)
        if p:
            return [(p, label[:120], f"{where}:title_match:{cov}")], tried
    return [], tried


FILE_CANDS = {}


def collect(files):
    """outputs/*.json 을 전부 걸어 (pdf, page, quote) 삼중항을 뽑는다."""
    records = []

    def walk(node, ancestors, jpath, src_file, container_key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                kl = str(k).lower()
                sub = f"{jpath}/{k}"
                if isinstance(v, str):
                    is_quote = (QUOTE_KEY_RE.search(kl) and not QUOTE_KEY_DENY.search(kl))
                    if not is_quote and container_key and QUOTE_KEY_RE.search(container_key) \
                            and not QUOTE_KEY_DENY.search(container_key) and kl in INNER_TEXT_KEYS:
                        is_quote = True
                    if is_quote and len(v.strip()) >= 12:
                        records.append(mk(v, node, ancestors, sub, src_file, quote_key=k))
                else:
                    walk(v, ancestors + [(node, k)], sub, src_file,
                         container_key=k if isinstance(v, (list, dict)) else container_key)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                sub = f"{jpath}[{i}]"
                if isinstance(v, str):
                    if container_key and QUOTE_KEY_RE.search(container_key) \
                            and not QUOTE_KEY_DENY.search(container_key) and len(v.strip()) >= 12:
                        parent = ancestors[-1][0] if ancestors else {}
                        records.append(mk(v, parent, ancestors[:-1] if ancestors else [], sub, src_file,
                                          quote_key=container_key))
                else:
                    walk(v, ancestors, sub, src_file, container_key=container_key)

    def mk(text, node, ancestors, jpath, src_file, quote_key=None):
        pages, pkey, pwhere = find_page(node, ancestors, quote_key)
        srcs, tried = find_sources(node, ancestors)
        return {
            "source_json": os.path.basename(src_file),
            "json_path": jpath,
            "quote_key": quote_key,
            "quote": text,
            "quote_len": len(text),
            "stated_page": pages[0] if pages else None,
            "stated_pages_all": pages,
            "page_key": pkey,
            "page_from": pwhere,
            "pdf_path": srcs[0][0] if srcs else None,
            "pdf_raw_value": (srcs[0][1] if srcs else (tried[0][0] if tried else None)),
            "pdf_resolved_via": (srcs[0][2] if srcs else (tried[0][1] if tried else None)),
            "_alt_sources": [s[0] for s in srcs[1:]],
            "_unresolved_tried": [t[0] for t in tried] if not srcs else [],
            "_file_candidates": [] if srcs else list(FILE_CANDS.get(os.path.basename(src_file), [])),
        }

    for f in files:
        try:
            raw = open(f, encoding="utf-8").read()
            d = json.loads(raw)
        except Exception as e:
            print(f"  !! JSON 파싱 실패 {f}: {e}", file=sys.stderr)
            continue
        # 파일 전체가 소수의 PDF 만 다루면(예: sionnart_* = Sionna RT 기술보고서 + 창설논문),
        # 경로가 안 붙은 인용문도 그 후보집합에 대고 채점할 수 있다. 단, 맞았을 때만
        # 결과로 인정하고 provenance 를 'inferred_from_file' 로 따로 센다.
        cands = []
        for m in re.finditer(r"[\w./\-+ ()가-힣,']*\.pdf", raw, re.I):
            p, _ = resolve_source(m.group(0).strip())
            if p and p not in cands:
                cands.append(p)
        FILE_CANDS[os.path.basename(f)] = cands if 0 < len(cands) <= 10 else []
        walk(d, [], "", f)
    return records


# ------------------------------------------------------------------------- 채점
GRADE_RANK = {"verbatim": 4, "verbatim_doc": 3, "reconstructed": 2, "unverified": 1, None: 0}


def longest_prefix_hit(qsq, hay):
    """인용문이 원문과 어디서 갈라지는지 — squash 접두사가 몇 글자까지 붙어 있는가."""
    if not qsq or not hay:
        return 0
    lo, hi = 0, len(qsq)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if qsq[:mid] in hay:
            lo = mid
        else:
            hi = mid - 1
    return lo


def find_anchor(qsq, hay, k=40):
    """인용문의 어느 조각이 원문 어디에 붙는지 — 정렬 창을 잡기 위한 닻."""
    step = max(1, k // 2)
    for off in range(0, max(1, len(qsq) - k + 1), step):
        chunk = qsq[off:off + k]
        if len(chunk) < 12:
            break
        p = hay.find(chunk)
        if p >= 0:
            return off, p
    return None


def align_quote(qsq, doc, max_gap=900, min_chunk=8, max_anchor_tries=3):
    """인용문을 원문에 국소 정렬해서 '무엇이 끼어들었고 무엇이 다른가'를 뽑는다.

    이게 필요한 이유: 학술지 PDF 는 문장 한복판에 페이지 머리글/꼬리글
    ('8814 IEEE TRANSACTIONS ON …', 'Authorized licensed use limited to: DGIST …')과
    그림 캡션을 끼워 넣는다. 단순 연속 탐색은 그런 멀쩡한 축자 인용을 전부 unverified 로
    떨어뜨린다. 실제로 이 도구 첫 판이 그랬다(Taylor & Poullin TAES 2025 인용 2건).

    difflib 이 아니라 단조 전진 워커를 쓴다. difflib 은 창 밖 꼬리를 억지로 물어서
    '끼어든 텍스트'를 날조했다. 여기서는 이전 매치 뒤 max_gap 안에서만 다음 조각을 찾는다.
    """
    hay = doc.doc_sq
    best = None
    anchor_off = 0
    for _ in range(max_anchor_tries):
        a = find_anchor(qsq[anchor_off:], hay)
        if a is None:
            break
        off, pos0 = a[0] + anchor_off, a[1]
        start = max(0, pos0 - off - 60)
        i, pos = 0, start
        pieces, skipped, edits, pending = [], 0, [], ""
        ok = True
        while i < len(qsq):
            lo, hi, bl, bp = 0, len(qsq) - i, 0, -1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                p = hay.find(qsq[i:i + mid], pos, pos + max_gap + mid)
                if p >= 0:
                    bl, bp, lo = mid, p, mid
                else:
                    hi = mid - 1
            if bl >= min_chunk:
                if pending:
                    edits.append({"quote_says": pending[:60],
                                  "pdf_says_here": hay[pos:min(bp, pos + 60)]})
                    pending = ""
                pieces.append((i, i + bl, bp, bp + bl))
                i += bl
                pos = bp + bl
            else:
                pending += qsq[i]
                i += 1
                skipped += 1
                if skipped > max(6, 0.15 * len(qsq)):
                    ok = False
                    break
        if ok and pieces:
            covered = sum(b - a2 for a2, b, _, _ in pieces)
            gaps = []
            for k in range(len(pieces) - 1):
                gs, ge = pieces[k][3], pieces[k + 1][2]
                if ge > gs:
                    crosses = any(gs < b0 <= ge for (b0, _b1, _i) in doc.bounds if b0 > 0)
                    gaps.append({"len": ge - gs, "at_page_boundary": crosses,
                                 "pdf_text_skipped": hay[gs:ge][:100]})
            res = {"match_ratio": round(covered / max(1, len(qsq)), 4),
                   "quote_chars_unmatched": skipped,
                   "doc_inserts": gaps,
                   "quote_edits": edits[:8],
                   "span_pages_1based": [p + 1 for p in
                                         doc.pages_of_span(pieces[0][2], pieces[-1][3])]}
            if best is None or res["match_ratio"] > best["match_ratio"]:
                best = res
            if best["match_ratio"] > 0.999:
                break
        anchor_off = off + 25
        if anchor_off >= len(qsq) - 12:
            break
    return best


_INLINE_PAGE = re.compile(r"\(\s*p{1,2}\.?\s*\d{1,4}\s*\)", re.I)
_BRACKET_INS = re.compile(r"\[[^\[\]]{0,60}\]")
_INNER_QUOTED = re.compile(r"['\"“”‘’]([^'\"“”‘’]{60,})['\"“”‘’]")


def quote_variants(q):
    """인용문이 '있는 그대로' 안 맞을 때 시도할 변형들. 각 변형은 이름을 달고 다니므로
    결과에 '무엇을 깎아서 맞췄는지'가 남는다 — 조용히 통과시키지 않는다."""
    out = []
    v = _BRACKET_INS.sub(" ", _INLINE_PAGE.sub(" ", q))
    if squash(v) != squash(q) and len(squash(v)) >= 30:
        out.append((v, "stripping_editorial_brackets_and_inline_page_markers"))
    m = max(_INNER_QUOTED.findall(q), key=len) if _INNER_QUOTED.search(q) else None
    if m and len(squash(m)) >= 50 and len(squash(m)) < len(squash(q)) * 0.9:
        out.append((m, "grading_only_the_inner_quoted_span"))
    return out


def _grade_against(q, stated_pages, doc, _variant=None):
    """PDF 한 편에 대고 채점. rec 조각(dict) 을 돌려준다."""
    r = {"grade": None, "flags": [], "doc_pages": doc.n_pages}
    flags = r["flags"]
    cands = []
    for p in stated_pages:
        for conv, idx in (("1-based", p - 1), ("0-based", p)):
            if 0 <= idx < doc.n_pages and (conv, idx) not in cands:
                cands.append((conv, idx))
    if stated_pages and not cands:
        flags.append("stated_page_out_of_range")     # 학술지 인쇄 쪽번호(p.3476) 등
    r["candidate_page_indices"] = sorted({i for _, i in cands})

    frags = [f for f in _ELLIPSIS.split(q) if f and not _ELLIPSIS.fullmatch(f)]
    elided = len(frags) > 1
    if elided:
        flags.append("elided_quote")
    frag_sq = [squash(f) for f in frags if len(squash(f)) >= 8] or [squash(q)]
    qsq = squash(q)

    # 1) 문서 전체 연결본에서 연속 탐색 → 걸친 페이지 역산
    hit_pages, mode = None, None
    if qsq:
        i = doc.doc_sq.find(qsq)
        if i >= 0:
            hit_pages, mode = doc.pages_of_span(i, i + len(qsq)), "contiguous_raw"
        elif qsq in doc.doc_sq_sorted:
            pgs = [j for j, t in enumerate(doc.page_sq_sorted) if qsq in t]
            if pgs:
                hit_pages, mode = pgs, "contiguous_sorted"
    if hit_pages is None and elided:
        pgs = [j for j, t in enumerate(doc.page_sq) if all(fr in t for fr in frag_sq)] or \
              [j for j, t in enumerate(doc.page_sq_sorted) if all(fr in t for fr in frag_sq)]
        if pgs:
            hit_pages, mode = pgs, "fragments_all_on_page"
        else:
            # 조각들이 서로 다른 페이지에 흩어져 있는 '…' 인용 — 각 조각은 축자다.
            long_frags = [fr for fr in frag_sq if len(fr) >= 20]
            if long_frags and len(long_frags) == len([f for f in frag_sq if len(f) >= 20]):
                per = []
                for fr in long_frags:
                    hits = [j for j, t in enumerate(doc.page_sq) if fr in t] or \
                           [j for j, t in enumerate(doc.page_sq_sorted) if fr in t]
                    per.append(hits)
                if all(per):
                    hit_pages = sorted({p for hh in per for p in hh})
                    mode = "fragments_verbatim_on_different_pages"
                    flags.append("elided_fragments_span_multiple_pages")

    # 1b) 연속 실패 → 정렬. 페이지 머리글/꼬리글이 문장을 자른 것뿐인지 본다.
    aln = None
    if hit_pages is None and len(qsq) >= 25:
        aln = align_quote(qsq, doc)
        if aln:
            r["alignment"] = aln
            whole = aln["match_ratio"] > 0.999 and aln["quote_chars_unmatched"] == 0
            furniture_only = whole and all(
                (ins["at_page_boundary"] and ins["len"] <= 800) or ins["len"] <= 3
                for ins in aln["doc_inserts"])
            if whole and aln["doc_inserts"] and (furniture_only or elided):
                # 머리글/꼬리글·그림 캡션이 문장을 자른 것뿐이거나, 생략을 '…' 로 표시한 인용.
                hit_pages = [p - 1 for p in aln["span_pages_1based"]]
                mode = ("contiguous_except_page_header_footer" if furniture_only
                        else "contiguous_with_marked_ellipsis")
                flags.append("interrupted_by_page_furniture" if furniture_only
                             else "marked_ellipsis_gaps")

    if hit_pages:
        r["found_pages_1based"] = [p + 1 for p in hit_pages]
        r["match_mode"] = mode
        nq = norm(q)
        r["strict_whitespace_match"] = any(nq in doc.page_norm[p] or nq in doc.page_norm_sorted[p]
                                           for p in hit_pages)
        conv_ok = [c for c, i in cands if i in hit_pages]
        if conv_ok:
            r["grade"] = "verbatim"
            r["page_convention"] = "/".join(sorted(set(conv_ok)))
            if len(hit_pages) > 1:
                flags.append("spans_page_break")
        else:
            r["grade"] = "verbatim_doc"
            flags.append("page_not_stated" if not stated_pages else "stated_page_wrong")
        return r

    # 1c) 표를 눈으로 읽어 옮긴 자리는 독자가 붙인 뼈대말(row/column/TABLE III)이 섞인다.
    #     그 뼈대말 때문에 내용어 검사가 오염되므로, 셀 값만 뽑아 따로 본다.
    if TABLE_SCAFFOLD_RE.search(q):
        flags.append("table_cell_reading_scaffolded")

    # 2) 연속 실패 → 정렬 결과를 먼저 읽는다
    if aln:
        if aln["match_ratio"] > 0.999:
            # 인용문의 모든 글자가 원문에 순서대로 있으나 중간에 원문 일부가 빠졌다 =
            # 표시 없는 생략. 날조가 아니라 인용 위생 문제다.
            flags.append("unmarked_elision_pdf_text_omitted_inside_quote")
        elif aln["match_ratio"] >= 0.95:
            flags.append("near_verbatim_wording_differs")
        if aln["span_pages_1based"] and stated_pages and \
                not ({p - 1 for p in aln["span_pages_1based"]} & {i for _, i in cands}):
            flags.append("aligned_to_a_different_page")

    # 3) 내용어 재구성 판정
    cw = content_words(q)
    if "table_cell_reading_scaffolded" in flags:
        scaffold = {"table", "row", "column", "col", "cell", "deg", "value", "entry",
                    "행", "열", "표"}
        cw2 = [w for w in cw if w not in scaffold]
        if len(cw2) >= 4:
            cw = cw2
    r["n_content_words"] = len(cw)

    def cover(page_idx):
        words = doc.page_words[page_idx]
        sq = doc.page_sq[page_idx] + doc.page_sq_sorted[page_idx]
        return [w for w in cw
                if w not in words and not (len(w) >= 4 and w in sq)]

    best = None
    for _, i in cands:
        miss = cover(i)
        if best is None or len(miss) < len(best[1]):
            best = (i, miss)
    # 페이지를 걸친 인용은 명시 페이지 + 정렬이 짚은 페이지들의 합집합으로 본다
    if best is not None and best[1] and aln and aln["span_pages_1based"]:
        span = {p - 1 for p in aln["span_pages_1based"]}
        if span & {i for _, i in cands}:
            union = set()
            for i in span | {i for _, i in cands}:
                union |= doc.page_words[i]
            union_sq = "".join(doc.page_sq[i] for i in sorted(span | {i for _, i in cands}))
            miss_u = [w for w in cw if w not in union and not (len(w) >= 4 and w in union_sq)]
            if len(miss_u) < len(best[1]):
                best = (best[0], miss_u)
                flags.append("quote_spans_pages_%s" % "-".join(
                    str(p) for p in sorted(span | {i + 1 for _, i in cands})))

    miss_doc = [w for w in cw if w not in doc.doc_words and not (len(w) >= 4 and w in doc.doc_sq)]
    r["coverage_doc"] = round(1 - len(miss_doc) / max(1, len(cw)), 3)
    r["missing_words_doc"] = miss_doc[:25]
    r["longest_contiguous_prefix_chars"] = longest_prefix_hit(qsq, doc.doc_sq)
    r["quote_squashed_chars"] = len(qsq)

    if best is None:                       # 페이지 미기재/범위밖 → 문서 전체로만 판정
        if not stated_pages:
            flags.append("page_not_stated")
        r["missing_words"] = miss_doc[:25]
        r["coverage_page"] = None
        if not miss_doc:
            flags.append("content_words_found_doc_wide_only")
            r["grade"] = "reconstructed"
        else:
            r["grade"] = "unverified"
        if all(doc.no_text_layer):
            r["grade"] = "reconstructed"
            flags.append("pdf_has_no_text_layer")
            r["machine_can_decide"] = False
        return r

    pidx, miss = best
    r["checked_page_1based"] = pidx + 1
    r["coverage_page"] = round(1 - len(miss) / max(1, len(cw)), 3)
    r["missing_words"] = miss[:25]

    # 이미지 표 함정: 그 페이지에 텍스트 레이어가 없으면 기계는 판정할 수 없다.
    # unverified 로 떨어뜨리면 멀쩡한 작업을 버리게 되므로 보류시킨다.
    if any(doc.no_text_layer[i] for _, i in cands) or all(doc.no_text_layer):
        r["grade"] = "reconstructed"
        flags.append("image_only_page_no_text_layer" if not all(doc.no_text_layer)
                     else "pdf_has_no_text_layer")
        r["machine_can_decide"] = False
        return r

    if not miss:
        r["grade"] = "reconstructed"
        return r
    if not miss_doc:
        flags.append("content_words_present_elsewhere_in_doc")

    # ⭐ 함정 4의 절반짜리 형태: 페이지에는 텍스트가 있는데 '표의 몸통만' 래스터 이미지인 경우.
    #   (실제 사례: Das Multiband RCS 논문 p4 TABLE III — 캡션은 텍스트, 숫자 셀은 그림)
    #   여기서 눈으로 읽어 옮긴 표 수치를 unverified 로 떨어뜨리면 멀쩡한 작업을 버린다.
    numeric_miss = [w for w in miss if re.fullmatch(r"[\d.,]+", w)]
    page_imgs = getattr(doc, "page_imgs", [])
    has_img = any(page_imgs[i] > 0 for _, i in cands if i < len(page_imgs))
    if has_img and r["coverage_page"] and r["coverage_page"] >= 0.3 and (
            "table_cell_reading_scaffolded" in flags
            or (numeric_miss and len(numeric_miss) >= 0.5 * len(miss))):
        r["grade"] = "reconstructed"
        flags.append("table_body_not_in_text_layer__page_carries_raster_images")
        r["machine_can_decide"] = False
        return r

    # 마지막으로: 편집 표시(대괄호 삽입·(p.7) 같은 인라인 쪽표시)나 우리 해설이 섞여서
    # 못 맞춘 것인지 확인한다. 맞으면 등급을 올리되 '무엇을 깎았는지'를 반드시 남긴다.
    if _variant is None:
        for vq, tag in quote_variants(q):
            rv = _grade_against(vq, stated_pages, doc, _variant=tag)
            if rv["grade"] in ("verbatim", "verbatim_doc"):
                rv["flags"].append("matched_only_after_" + tag)
                rv["variant_used"] = tag
                rv["original_field_is_not_a_clean_quote"] = True
                return rv
    # 수식 기호를 ASCII 로 옮겨 적다 어긋난 것인지 표시 (LT0, T^SSB_dist 같은 것들)
    mathish = [w for w in miss if re.fullmatch(r"[a-z]{1,4}\d+|\d+[a-z]{1,3}", w)]
    if miss and len(mathish) >= max(1, 0.5 * len(miss)):
        flags.append("math_symbol_transcription_suspected")
    r["grade"] = "unverified"
    return r


# ------------------------------------------------ quote 필드에 들어앉은 '인용문 아닌 것'
# 우리 기록물의 quote 칸에는 세 종류의 비(非)인용문이 산다. 이것들을 축자 매칭에 넣으면
# 전부 unverified 로 떨어져 진짜 실패를 덮어버린다. 대신 각자의 방식으로 기계 검증한다.
#   (1) 부재 주장  "ZERO HITS for 'RCS' in the full text layer"  → 실제로 세어 본다
#   (2) 메타데이터 "creator 'arXiv GenPDF (tex2pdf:a6404ea)'"     → PDF 메타데이터와 대조
#   (3) 파일 경로  "/data/public/.../x.pdf"                       → 존재 확인
NEG_RE = re.compile(r"(zero\s*hits|0\s*(occurrences|hits|times|회)|no\s+(occurrence|hit)s?\b)", re.I)
QUOTED_TERM_RE = re.compile(r"['\"“”‘’]([^'\"“”‘’]{2,40})['\"“”‘’]|/\\?b?([A-Za-z][\w\- ]{1,30})\\?b?/i?")
META_RE = re.compile(r"\b(creator|producer|/Subject|/Title|metadata)\b", re.I)
TABLE_SCAFFOLD_RE = re.compile(r"\btable\b[^.]{0,80}\b(row|column|열|행)\b", re.I)


def check_negative_assertion(q, doc, docs_by_name=None):
    """'그 논문에 X 는 0회' 라는 주장을 실제로 세어서 검증한다. 틀렸으면 그것이 BREAK 다."""
    terms = []
    for m in QUOTED_TERM_RE.finditer(q):
        t = (m.group(1) or m.group(2) or "").strip()
        if t and not t.lower().endswith(".pdf") and len(t) >= 2:
            terms += [x.strip() for x in t.split("|") if x.strip()]
    terms = [t for t in dict.fromkeys(terms) if len(t) >= 3][:6]
    if not terms:
        return None
    hay = norm("\n".join(doc.pages_raw))
    counts = {t: hay.count(norm(t)) for t in terms}
    return {"terms_counted": counts, "all_zero": all(v == 0 for v in counts.values())}


def check_metadata_assertion(q, doc):
    md = getattr(doc, "meta", None) or {}
    vals = " | ".join(str(v) for v in md.values() if v)
    hits, miss = [], []
    for m in QUOTED_TERM_RE.finditer(q):
        t = (m.group(1) or m.group(2) or "").strip()
        if len(t) < 4:
            continue
        (hits if squash(t) and squash(t) in squash(vals) else miss).append(t)
    if not hits and not miss:
        return None
    return {"metadata": {k: v for k, v in md.items() if v}, "matched": hits, "not_matched": miss,
            "all_matched": not miss}


# 그림/표를 눈으로 읽어 옮긴 자리 — 문장이 아니므로 축자 매칭 대상이 아니다.
FIGURE_READ_RE = re.compile(r"(axis label|axis title|legend|curve[s]? label|"
                            r"read off|눈금|축 ?라벨|그림에서 읽|\bcolou?r bar\b)", re.I)


def classify_non_quote(q, doc, rec):
    """quote 칸에 들어앉은 비인용문을 판별하고 그 자체의 방식으로 검증한다."""
    s = q.strip()
    # (3) 파일 경로만 적힌 경우
    if re.fullmatch(r"[/~][\w./\-+ ()가-힣,'&]+\.(pdf|py|md|json|txt)", s):
        return {"status": "path_not_a_quote_" + ("exists" if os.path.isfile(s) else "MISSING"),
                "path_checked": s}
    # (1) 부재 주장 — 실제로 세어 본다. 이 논문이 아니라 다른 파일을 지목하면 그 파일을 연다.
    if NEG_RE.search(s):
        target = doc
        m = re.search(r"([\w\-.]+\.pdf)", s)
        if m:
            p, _ = resolve_source(m.group(1))
            if p and os.path.isfile(p):
                target = get_doc(p)
        res = check_negative_assertion(s, target)
        if res:
            return {"status": ("negative_assertion_VERIFIED" if res["all_zero"]
                               else "negative_assertion_REFUTED_term_does_occur"),
                    "negative_assertion": res,
                    "counted_in_pdf": os.path.basename(target.path)}
    # (2) PDF 메타데이터 주장
    if META_RE.search(s) and len(s) < 400:
        res = check_metadata_assertion(s, doc)
        if res:
            return {"status": ("metadata_assertion_VERIFIED" if res["all_matched"]
                               else "metadata_assertion_PARTIAL"),
                    "metadata_check": res}
    return None


def grade_one(rec, use_cache=True):
    q = rec["quote"]
    rec["flags"] = []
    rec["hangul_ratio"] = round(hangul_ratio(q), 3)
    if FIGURE_READ_RE.search(q) or (q.strip().startswith("[") and q.strip().endswith("]")):
        rec["flags"].append("figure_or_axis_reading_not_a_sentence")

    # (a) 정직한 기권 자리 — "UNVERIFIED by absence" 등. 실패로 세면 통계를 오염시킨다.
    if ABSTAIN_RE.match(q.strip()):
        rec["status"], rec["grade"] = "explicit_abstention", None
        return rec

    alts = rec.pop("_alt_sources", [])
    tried = rec.pop("_unresolved_tried", [])
    fcands = rec.pop("_file_candidates", [])
    srcs = ([rec["pdf_path"]] + alts) if rec["pdf_path"] else []
    if not srcs and fcands:
        srcs = list(fcands)
        rec["pdf_resolved_via"] = f"file_level_candidate_set({len(fcands)})"
    if not srcs:
        rec["status"] = "pdf_unresolved" if (rec["pdf_raw_value"] or tried) else "no_source_recorded"
        rec["grade"] = None
        return rec

    best, best_path, attempts = None, None, []
    for path in srcs:
        if not os.path.isfile(path):
            attempts.append({"pdf": path, "result": "missing"})
            continue
        doc = get_doc(path, use_cache)
        if doc.error or doc.n_pages == 0:
            attempts.append({"pdf": path, "result": "unreadable:" + str(doc.error)})
            continue
        r = _grade_against(q, rec["stated_pages_all"], doc)
        attempts.append({"pdf": os.path.basename(path), "grade": r["grade"],
                         "found_pages_1based": r.get("found_pages_1based"),
                         "coverage_page": r.get("coverage_page")})
        if best is None or GRADE_RANK[r["grade"]] > GRADE_RANK[best["grade"]]:
            best, best_path = r, path
    if best is None:
        rec["status"] = "pdf_missing"
        rec["grade"] = None
        rec["attempts"] = attempts
        return rec

    # 인용문이 아닌 것들은 각자의 방식으로 검증하고 등급 통계 밖으로 뺀다.
    doc0 = get_doc(best_path, use_cache)
    nonq = classify_non_quote(q, doc0, rec)
    if nonq:
        rec.update(nonq)
        rec["grade"] = None
        rec["matched_pdf"] = best_path
        return rec

    rec["status"] = "graded"
    rec["source_provenance"] = prov(rec)
    flags = rec["flags"]
    rec.update({k: v for k, v in best.items() if k != "flags"})
    flags.extend(best["flags"])
    rec["flags"] = flags
    rec["matched_pdf"] = best_path
    if len(srcs) > 1:
        rec["source_candidates"] = attempts
        if best_path != srcs[0]:
            flags.append("matched_alternate_source_not_the_primary_one")
    if rec.get("page_from") == "self_generic_page_for_suffixed_quote" and \
            "stated_page_wrong" in flags:
        flags.append("page_key_ambiguous_multi_quote_dict")   # 스키마 탓일 수 있다
    # (b) unverified 는 아카이브 전수 추적으로 '오귀속'과 '날조'를 가른다.
    if rec["grade"] == "unverified" and DO_HUNT:
        h = hunt(squash(q), exclude=best_path)
        if h:
            rec["found_in_other_pdf"] = h
            rels = {x["relation_to_attributed_pdf"] for x in h}
            # 출처를 우리가 추측한 건이면, 다른 곳에서 찾았다는 사실은 기록물의 실패가 아니라
            # 출처가 복구된 것이다. 등급 통계에서 빼되 어디 있었는지는 남긴다.
            if rec["source_provenance"] != "stated_path":
                rec["status"] = ("inferred_source_MISMATCH_quote_lives_in_another_work"
                                 if "different_work" in rels
                                 else "source_recovered_by_archive_hunt")
                rec["grade_if_inference_were_right"] = "unverified"
                rec["grade"] = None
                return rec
            if "different_work" in rels:
                flags.append("MISATTRIBUTED_text_lives_in_a_different_work")
            elif "same_work_other_version" in rels:
                flags.append("text_is_in_another_VERSION_of_the_same_work")
            else:
                flags.append("text_is_in_a_duplicate_copy_of_the_same_file")
        else:
            flags.append("not_found_anywhere_in_archive")
            if rec["source_provenance"] != "stated_path":
                # 출처를 우리가 추측한 건이다. 못 맞췄다고 기록물의 실패로 셀 수 없다.
                rec["status"] = "source_inferred_and_quote_not_found__NOT_a_graded_failure"
                rec["grade_if_inference_were_right"] = "unverified"
                rec["grade"] = None
    # (c) 우리말 메모가 quote 필드에 들어앉은 경우 — 실패가 아니라 애초에 인용문이 아니다.
    if rec["grade"] == "unverified" and rec["hangul_ratio"] > 0.30:
        rec["status"], rec["grade_if_treated_as_quote"] = "korean_note_not_a_quote", "unverified"
        rec["grade"] = None
    return rec


# -------------------------------------------------------------------------- 실행
def prov(r):
    v = r.get("pdf_resolved_via") or ""
    if "title_match" in v:
        return "inferred_by_title"
    if "file_level_candidate_set" in v:
        return "inferred_from_file_candidate_set"
    return "stated_path" if r.get("pdf_path") else "none"


def summarize(records):
    by_grade = Counter(r.get("grade") or ("STATUS:" + r.get("status", "?")) for r in records)
    by_status = Counter(r.get("status", "?") for r in records)
    flags = Counter(f for r in records for f in r.get("flags", []))
    by_file = defaultdict(Counter)
    for r in records:
        by_file[r["source_json"]][r.get("grade") or ("STATUS:" + r.get("status", "?"))] += 1
    graded = [r for r in records if r.get("grade")]
    fl = lambda r, f: f in r.get("flags", [])          # noqa: E731
    vd = [r for r in records if r.get("grade") == "verbatim_doc"]
    rc = [r for r in records if r.get("grade") == "reconstructed"]
    by_prov = defaultdict(Counter)
    for r in records:
        by_prov[prov(r)][r.get("grade") or ("STATUS:" + r.get("status", "?"))] += 1
    return {
        "records_total": len(records),
        "graded": len(graded),
        "by_grade": dict(by_grade.most_common()),
        "by_status": dict(by_status.most_common()),
        "flags": dict(flags.most_common()),
        "grade_share_of_graded": {
            g: round(by_grade[g] / max(1, len(graded)), 4)
            for g in ("verbatim", "verbatim_doc", "reconstructed", "unverified")
        },
        # ⭐ 'verbatim_doc' 는 두 종류가 섞이면 안 된다: 페이지를 틀리게 적은 것 vs 아예 안 적은 것
        "verbatim_doc_breakdown": {
            "stated_page_is_wrong": sum(1 for r in vd if fl(r, "stated_page_wrong")),
            "page_never_stated": sum(1 for r in vd if fl(r, "page_not_stated")),
            "stated_page_out_of_range_printed_page_label": sum(
                1 for r in vd if fl(r, "stated_page_out_of_range")),
        },
        "reconstructed_breakdown": {
            "machine_decided_all_content_words_on_page": sum(
                1 for r in rc if r.get("machine_can_decide") is not False),
            "undecidable_image_only_page": sum(1 for r in rc if r.get("machine_can_decide") is False),
        },
        "by_source_provenance": {k: dict(v.most_common()) for k, v in sorted(by_prov.items())},
        "by_source_json": {k: dict(v.most_common()) for k, v in sorted(by_file.items())},
        "distinct_pdfs": len({r["pdf_path"] for r in records if r.get("pdf_path")}),
    }


# ------------------------------------------------------------------ 자체 음성대조
SELFTEST_PDFS = [
    "/data/public/jeong/papers/LTE/25_Drone_Detection_Using_4G-LTE-Based_Passive_Radar.pdf",
    "/data/public/sionna_jeong/papers_isac_sionna/2604.05991__ziganshin_curved-body-scattering.pdf",
]


def selftest(use_cache=True):
    """이 도구가 '날조된 인용문'을 실제로 떨어뜨리는지 증명한다.
    통과만 하는 검사기는 검사기가 아니다. 음성대조가 없으면 이 게이트는 무의미하다."""
    path = next((p for p in SELFTEST_PDFS if os.path.isfile(p)), None)
    if path is None:
        print("selftest: 기준 PDF 를 찾지 못했다"); return 1
    doc = get_doc(path, use_cache)
    # 진짜 문장 하나를 원문에서 뽑는다(길고 평범한 문장)
    real, real_pg = None, None
    for pg in range(2, min(doc.n_pages, 9)):
        for s in re.split(r"(?<=[.]) ", norm(doc.pages_raw[pg])):
            if 120 <= len(s) <= 240 and s.count("[") == 0 and len(content_words(s)) >= 14:
                real, real_pg = s, pg
                break
        if real:
            break
    if not real:
        print("selftest: 기준 문장을 못 뽑았다"); return 1
    words = real.split()
    fabricated = ("the measured bistatic radar cross section of the quadcopter reached "
                  "17.4 dBsm at a bistatic angle of 63 degrees, validated against an "
                  "mlfmm reference solver in an anechoic chamber")
    reworded = " ".join(w if i % 5 else "notwithstanding" for i, w in enumerate(words))
    cases = [
        ("진짜 문장, 페이지 맞음",          real, real_pg + 1, "verbatim"),
        ("진짜 문장, 페이지 틀림",          real, real_pg + 4, "verbatim_doc"),
        ("진짜 문장, 앞뒤 잘라 …로 표시",   words[0] + " " + " ".join(words[1:4]) + " ... " +
                                            " ".join(words[-6:]), real_pg + 1, "verbatim"),
        ("단어 5개 중 1개를 치환",          reworded, real_pg + 1, ("reconstructed", "unverified")),
        ("완전 날조(도메인 단어만 그럴듯)", fabricated, real_pg + 1, "unverified"),
        ("다른 논문 문장을 이 논문에 귀속",
         "in this paper we propose a novel deep unfolding network for massive mimo channel "
         "estimation under one-bit quantization with provable convergence guarantees",
         real_pg + 1, "unverified"),
    ]
    print(f"selftest 기준: {os.path.basename(path)} p{real_pg+1}\n")
    ok = True
    # 함정 4: 텍스트 레이어가 없는 이미지 페이지. 여기서 나온 인용문을 unverified 로
    # 떨어뜨리면 멀쩡한 작업을 버린다. reconstructed + machine_can_decide=False 여야 한다.
    img = "/data/public/sionna_jeong/papers_isac_sionna/new_0731/bilkent_thesis__ptd-implementation-rcs.pdf"
    if os.path.isfile(img):
        idoc = get_doc(img, use_cache)
        ip = next((i for i, b in enumerate(idoc.no_text_layer) if b), None)
        if ip is not None:
            r = _grade_against("physical theory of diffraction fringe wave current on the edge",
                               [ip + 1], idoc)
            good = r["grade"] == "reconstructed" and r.get("machine_can_decide") is False
            ok &= good
            print(f"  [{'PASS' if good else 'FAIL'}] {'이미지 전용 페이지(텍스트층 없음)':<30} -> "
                  f"{str(r['grade']):<14} (기대 reconstructed/보류) {r['flags']}")
    for name, q, pg, want in cases:
        r = _grade_against(q, [pg], doc)
        want_t = (want,) if isinstance(want, str) else want
        good = r["grade"] in want_t
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] {name:<30} -> {r['grade']:<14} "
              f"(기대 {'/'.join(want_t)}) cov={r.get('coverage_page')} {r['flags']}")
    print("\n" + ("selftest 통과 — 날조는 걸러지고 진짜는 통과한다."
                  if ok else "⚠ selftest 실패 — 채점 규칙을 고쳐야 한다."))
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None, help="outputs 안의 파일명만 지정")
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--min-len", type=int, default=12)
    ap.add_argument("--selftest", action="store_true", help="날조 인용문이 걸러지는지 음성대조")
    ap.add_argument("--no-hunt", action="store_true", help="unverified 아카이브 전수 추적 끄기")
    ap.add_argument("--gate", action="store_true", help="stated_path unverified 가 있으면 exit 1")
    args = ap.parse_args()
    globals()["DO_HUNT"] = not args.no_hunt

    if args.selftest:
        sys.exit(selftest(use_cache=not args.no_cache))

    files = sorted(glob.glob(os.path.join(OUTPUTS, "*.json")))
    files = [f for f in files if os.path.basename(f) != SELF_NAME]
    if args.only:
        want = {os.path.basename(x) for x in args.only}
        files = [f for f in files if os.path.basename(f) in want]
    t0 = time.time()
    print(f"[1/3] {len(files)} 개 JSON 에서 인용 삼중항 수집 중 …")
    records = collect(files)
    records = [r for r in records if len(r["quote"].strip()) >= args.min_len]
    print(f"      {len(records)} 건 수집. PDF 인덱스 {sum(len(v) for v in pdf_index().values())} 항목.")

    print("[2/3] 채점 중 …")
    by_src = defaultdict(list)
    for r in records:
        by_src[r["source_json"]].append(r)
    done = []
    for n, (src, rs) in enumerate(sorted(by_src.items()), 1):
        for r in rs:
            grade_one(r, use_cache=not args.no_cache)
        done += rs
        payload = {
            "meta": {
                "file": args.out,
                "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tool": os.path.abspath(__file__),
                "partial": True,
                "sources_done": n,
                "sources_total": len(by_src),
            },
            "counts": summarize(done),
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        print(f"      [{n:>3}/{len(by_src)}] {src:<44} {len(rs):>4} 건")

    print("[3/3] 저장 …")
    counts = summarize(records)
    unver = sorted([r for r in records if r.get("grade") == "unverified"],
                   key=lambda r: (r.get("coverage_page") if r.get("coverage_page") is not None
                                  else (r.get("coverage_doc") or 0)))
    wrongpage = [r for r in records if r.get("grade") == "verbatim_doc"]
    unresolved = Counter(r["pdf_raw_value"] for r in records
                         if r.get("status") in ("pdf_unresolved", "pdf_missing") and r.get("pdf_raw_value"))
    payload = {
        "meta": {
            "file": args.out,
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tool": os.path.abspath(__file__),
            "partial": False,
            "runtime_s": round(time.time() - t0, 1),
            "what_ko": "우리 기록물의 모든 (pdf,page,quote) 삼중항을 원문에 대고 기계 채점한 결과",
            "grades_ko": {
                "verbatim": "명시 페이지에서 연속 문자열로 발견",
                "verbatim_doc": "문서에는 연속으로 있으나 명시 페이지가 아님(또는 페이지 미기재)",
                "reconstructed": "연속은 아니나 내용어가 전부 그 페이지에 있음 — 정당하지만 '인용'은 아님",
                "unverified": "내용어가 없음 — 실패 케이스",
            },
            "caveats_ko": [
                "squash 비교는 구두점·공백·줄바꿈 하이픈을 무시한다. 부호(마이너스)만 다른 경우는 잡지 못한다.",
                "image_only_page_no_text_layer 플래그가 붙은 reconstructed 는 기계가 판정한 것이 아니라 판정을 보류한 것이다(machine_can_decide=false).",
                "grade 가 null 인 건은 채점에 들어가지 못한 건이며 '확인됨'이 아니다.",
            ],
        },
        "counts": counts,
        "unverified_cases": unver,
        "inferred_source_mismatches": [r for r in records if r.get("status") ==
                                       "inferred_source_MISMATCH_quote_lives_in_another_work"],
        "wrong_or_missing_page_cases": wrongpage,
        "unresolved_sources": dict(unresolved.most_common()),
        "records": records,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print("\n==== 분포 ====")
    for k, v in counts["by_grade"].items():
        print(f"  {k:<28} {v:>5}")
    print(f"  (graded {counts['graded']} / total {counts['records_total']}, "
          f"pdfs {counts['distinct_pdfs']}, {payload['meta']['runtime_s']}s)")
    if not args.summary_only:
        print("\n==== unverified ====")
        for r in unver[:80]:
            print(f"  {r['source_json']}{r['json_path']}  p={r['stated_page']} "
                  f"cov={r.get('coverage_page')} miss={r.get('missing_words', [])[:6]}")
            print(f"      {r['quote'][:110]!r}")
    print(f"\n-> {args.out}")

    if args.gate:
        # 읽기 라운드 뒤 게이트로 쓰는 모드: 출처를 직접 적어놓고 원문에 없는 인용문이
        # 하나라도 있으면 실패로 끝낸다. 추론 출처는 우리 잘못이 아니므로 세지 않는다.
        hard = [r for r in unver if r.get("source_provenance") == "stated_path"]
        print(f"\n[GATE] stated_path unverified = {len(hard)}")
        for r in hard[:20]:
            print(f"   ✗ {r['source_json']}{r['json_path']} p={r['stated_page']} "
                  f"cov={r.get('coverage_page')}")
        sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
