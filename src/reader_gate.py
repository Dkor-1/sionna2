#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""판독기의 **공통 입력 관문**과 **원자적 발간** (2026-09-13).

왜 있나
-------
⛔⛔점검자가 임시 반례로 재현한 것(2026-09-13):
  · 대역 판독기 `main()` 에 NaN 이 섞인 시계열을 넣으면 **비유한 수 260 개가 든 JSON 을
    먼저 저장한 뒤** 그다음 계산에서 죽는다. 곧 **죽어도 발간물이 오염된 채 남는다.**
  · 길이가 잘못된 입력은 **정상 종료(exit 0)** 하면서 숫자 수십 개를 조용히 바꾼다.
  · 파형·장면 판독기는 표집률 불일치 · 세대 고른 뒤 남은 전계 충돌 · complex64 NaN 을
    그대로 받아들인다.
⚠지금 발간물이 오염됐다는 뜻이 아니다 — **오류 처리**의 결함이다. 그러나 다음에 창고가
  깨졌을 때 조용히 틀린 수를 내는 자리가 바로 여기다.

무엇을 하나
-----------
  check_series(E, …)  한 칸의 시계열이 쓸 만한지 본다. 못 쓰면 **까닭을 돌려준다**
                      (예외를 던지지 않는다 — 호출자가 그 칸만 건너뛰고 적을 수 있게).
  publish(paths, …)   ⭐**다 만든 뒤에 한 번에** 바꾼다. 임시 파일에 쓰고, 비유한 수가
                      있으면 **거절하고**, 통과하면 `os.replace` 로 제자리에 놓는다.
                      계산이 중간에 죽으면 옛 발간물이 **그대로 남는다.**

⛔여기서 새 낱말을 만들지 않는다. 「칸」「팔」「자세」「표집률」은 이미 쓰던 말이다.
"""
from __future__ import annotations

import json
import math
import os
import re
import tempfile
from typing import Iterable

import numpy as np


def check_series(E, *, n_poses: int | None = None, prf: float | None = None,
                 prf_seen: Iterable[float] | None = None,
                 mixed_generations=None, min_len: int = 8) -> list[str]:
    """이 칸의 시계열을 쓸 수 있나 — 못 쓰는 **까닭 목록**을 돌려준다(빈 목록이면 쓸 수 있다).

    ⛔예외를 던지지 않는다. 호출자가 그 칸만 건너뛰고 `skipped` 에 까닭을 적게 한다 —
      한 칸 때문에 판독 전체가 죽으면 나머지 답도 못 얻는다.
    """
    why: list[str] = []
    a = np.asarray(E)
    if a.size == 0:
        return ["시계열이 비어 있다"]
    if a.ndim != 1:
        why.append(f"시계열이 1 차원이 아니다(차원 {a.ndim})")
    if a.size < min_len:
        why.append(f"자세가 너무 적다({a.size} < {min_len})")
    try:
        c = np.asarray(a, complex)
    except (TypeError, ValueError):
        return why + [f"시계열을 복소수로 못 읽는다(dtype {a.dtype})"]
    if not np.isfinite(c).all():
        n = int((~np.isfinite(c)).sum())
        why.append(f"비유한 값이 {n} 자세에 있다(NaN·무한)")
    if n_poses is not None:
        #: ⛔예외를 던지지 않는다는 약속을 지킨다 — NaN·글자가 와도 까닭으로 돌려준다.
        try:
            want = int(n_poses)
        except (TypeError, ValueError):
            why.append(f"원장의 자세 수를 못 읽는다({n_poses!r})")
        else:
            if a.size != want:
                why.append(f"자세 수가 원장과 다르다(시계열 {a.size} · 원장 {want})")
    #: ⛔⛔표집률은 «있나» 만 보면 안 된다 — 0·음수·NaN 이면 시간축이 무너진다.
    if prf is None:
        why.append("이 칸의 표집률을 모른다(원장에 prf_hz 가 없다)")
    else:
        try:
            pv = float(prf)
        except (TypeError, ValueError):
            why.append(f"표집률을 수로 못 읽는다({prf!r})")
        else:
            if not math.isfinite(pv) or pv <= 0:
                why.append(f"표집률이 쓸 수 없는 값이다({pv})")
    if prf_seen is not None:
        seen = sorted({float(x) for x in prf_seen})
        if len(seen) > 1:
            why.append(f"한 칸에 표집률이 여럿 섞였다({seen})")
    if mixed_generations:
        why.append("굽기 세대가 섞였고 한 세대로 못 풀었다")
    return why


#: 글 안에 비유한 수가 **글자로** 찍힌 자리를 찾는 틀. ⛔`float('nan')` 을 `:.0f` 로
#  찍으면 «nan» 이라는 **글자**가 되어 JSON 검사를 빠져나간다 — 실제로 그렇게
#  docs/WFSURVIVE_0912.md 에 «nan» 이 20 개 실려 있었다(2026-09-13(10) 실측).
#
#: ⛔⛔그런데 «낱말이 보이나» 로만 보면 **글을 읽는 게 아니라 글자를 세는 것**이 된다.
#  2026-09-13(10) 실측으로 두 가지가 걸렸다:
#   ⓐ `check_series` 가 돌려주는 정상적인 건너뜀 사유 «비유한 값이 4 자세에 있다(NaN·무한)»
#     한 줄 때문에 **발간 전체가 막혔다** — 「그 칸만 건너뛰고 적는다」는 약속과 정반대다.
#   ⓑ outputs/ 의 JSON 45 개를 훑으니 낱말로 걸리는 594 자리가 **전부 사람이 NaN 을
#     논한 문장**이었다(「NaN → null 미수정 확인」 · 「converges … as R->inf」).
#     같은 훑기에서 **진짜 비유한 수는 206 자리 / JSON 13 개**였다.
#  ⇒ **값 자리에 찍힌 것만** 본다. 값 자리는 두 곳이다 —
#     ① 글 전체가 그 토막 하나인 것(«nan» · «-inf» · «nan Hz» · «+inf dB»)
#     ② 마크다운 표의 칸 하나가 그런 것(`| 1017.7 Hz | nan |`) ← 실제로 샌 모양
#  문장 속에서 낱말로 쓰인 것은 **막지 않는다.**
_NF_TOKEN = r"(?:nan|NaN|NAN|[-+]?inf|[-+]?Inf|[-+]?INF|[-+]?Infinity)"
#: 값 자리 = 토막 하나(+ 앞의 부호, 뒤의 단위) 뿐인 글.
_VALUE_ONLY = re.compile(r"^\s*[-+]?\s*" + _NF_TOKEN + r"\s*[%\w°/·()]{0,8}\s*$")
_TEXT_NONFINITE = re.compile(r"(?<![A-Za-z_])(" + _NF_TOKEN + r")(?![A-Za-z_])")


def _value_slots(s: str):
    """이 글에서 **값 자리**만 뽑아 준다 — 글 전체이거나, 마크다운 표의 한 칸이거나."""
    if _VALUE_ONLY.match(s):
        yield s.strip(), 0
        return
    for ln, line in enumerate(s.splitlines()):
        t = line.strip()
        if not (t.startswith("|") and t.endswith("|")):
            continue
        for cell in t[1:-1].split("|"):
            if _VALUE_ONLY.match(cell):
                yield cell.strip(), ln + 1


def _nonfinite_paths(o, path: str = "") -> list[str]:
    """비유한 수가 있는 자리를 경로째 찾는다 — 발간 전 거절의 근거.

    ⛔⛔2026-09-13(10) 넓혔다 — 옛 판은 `isinstance(o, float)` 만 봐서
      **numpy 형(np.float32·np.complex128)·0 차원 배열·복소수**를 놓쳤고,
      **글(마크다운)** 은 아예 안 봤다.
    """
    out: list[str] = []
    if isinstance(o, dict):
        for k, v in o.items():
            out += _nonfinite_paths(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            out += _nonfinite_paths(v, f"{path}[{i}]")
    elif isinstance(o, str):
        #: ⭐낱말이 아니라 **값 자리**만 본다(위 머리말 ⓐⓑ). 문장 속 «NaN» 은 통과시킨다.
        for tok, ln in _value_slots(o):
            where = f"{path or '(뿌리)'}" + (f":{ln}" if ln else "")
            out.append(f"{where}«{tok}»")
    elif isinstance(o, (bool, int)):
        pass
    else:
        try:
            v = complex(np.asarray(o).reshape(()))     # 0 차원·numpy 형·복소수까지
        except Exception:
            return out
        if not (math.isfinite(v.real) and math.isfinite(v.imag)):
            out.append(path or "(뿌리)")
    return out


def publish(items: dict, *, allow_nonfinite: bool = False) -> dict:
    """⭐**다 만든 뒤 한 번에** 발간한다. `items` 는 {최종경로: 내용}.

    내용이 dict 면 JSON 으로, str 이면 글자 그대로 쓴다.
    ⛔비유한 수가 있으면 **아무것도 안 바꾸고** SystemExit 로 멈춘다 — 중간에 죽어
      오염된 발간물이 남는 일을 구조적으로 없앤다.
    ⛔임시 파일은 **같은 디렉터리**에 만든다(다른 파일시스템이면 os.replace 가 원자적이지 않다).
    """
    bad: dict[str, list[str]] = {}
    if not allow_nonfinite:
        for p, v in items.items():
            #: ⭐dict 뿐 아니라 **글도** 본다 — «nan» 이 글자로 새어 나간 적이 있다.
            nf = _nonfinite_paths(v)
            if nf:
                bad[p] = nf
    if bad:
        msg = ["⛔ 발간을 멈춘다 — 비유한 수(NaN·무한)가 들어 있다. 옛 발간물은 그대로 둔다."]
        for p, nf in bad.items():
            msg.append(f"   {p}: {len(nf)} 자리 (예: {nf[:3]})")
        raise SystemExit("\n".join(msg))

    tmps: list[tuple[str, str]] = []
    try:
        for p, v in items.items():
            d = os.path.dirname(os.path.abspath(p)) or "."
            os.makedirs(d, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=d, prefix=".pub_", suffix=".tmp")
            #: ⛔⛔**만들자마자 목록에 넣는다**(2026-09-13(10) 정정). 옛 판은 `with` 가
            #  끝난 뒤에 넣어서, 쓰다 죽으면(디스크 참 · json.dump 의 TypeError) 그
            #  임시 파일을 finally 가 못 지우고 **고아로 남았다** — 실측으로 재현했다.
            tmps.append((tmp, p))
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                if isinstance(v, dict):
                    json.dump(v, f, ensure_ascii=False, indent=1)
                else:
                    f.write(v)
        #: ⚠**파일 하나하나는 원자적이지만 여럿에 걸쳐서는 아니다.** 두 os.replace 사이에서
        #  죽으면(SIGKILL·정전) JSON 은 새것, 글은 옛것으로 쪽이 갈릴 수 있다. 그 창을
        #  줄이려고 **쓰기를 모두 끝낸 뒤** 갈아끼우기만 몰아서 한다. 완전히 없애려면
        #  디렉터리 통째 교체가 필요한데 지금 구조에서는 과하다 — 그 사실을 여기 적어 둔다.
        done = []
        for tmp, p in list(tmps):
            os.replace(tmp, p)
            done.append((tmp, p))
            tmps.remove((tmp, p))
    finally:
        for tmp, _ in tmps:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return {"published": sorted(items), "n": len(items)}


def sweep_orphans(dirs: Iterable[str]) -> list[str]:
    """지난번에 죽어 남은 `.pub_*.tmp` 를 쓸어담는다. ⭐판독기가 시작할 때 부른다."""
    gone: list[str] = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for n in os.listdir(d):
            if n.startswith(".pub_") and n.endswith(".tmp"):
                try:
                    os.unlink(os.path.join(d, n))
                    gone.append(os.path.join(d, n))
                except OSError:
                    pass
    return gone
