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
    if not np.isfinite(np.asarray(a, complex)).all():
        n = int((~np.isfinite(np.asarray(a, complex))).sum())
        why.append(f"비유한 값이 {n} 자세에 있다(NaN·무한)")
    if n_poses is not None and a.size != int(n_poses):
        why.append(f"자세 수가 원장과 다르다(시계열 {a.size} · 원장 {int(n_poses)})")
    if prf is None:
        why.append("이 칸의 표집률을 모른다(원장에 prf_hz 가 없다)")
    if prf_seen is not None:
        seen = sorted({float(x) for x in prf_seen})
        if len(seen) > 1:
            why.append(f"한 칸에 표집률이 여럿 섞였다({seen})")
    if mixed_generations:
        why.append("굽기 세대가 섞였고 한 세대로 못 풀었다")
    return why


def _nonfinite_paths(o, path: str = "") -> list[str]:
    """비유한 수가 있는 자리를 경로째 찾는다 — 발간 전 거절의 근거."""
    out: list[str] = []
    if isinstance(o, dict):
        for k, v in o.items():
            out += _nonfinite_paths(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            out += _nonfinite_paths(v, f"{path}[{i}]")
    elif isinstance(o, float) and not math.isfinite(o):
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
            if isinstance(v, dict):
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
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                if isinstance(v, dict):
                    json.dump(v, f, ensure_ascii=False, indent=1)
                else:
                    f.write(v)
            tmps.append((tmp, p))
        for tmp, p in tmps:
            os.replace(tmp, p)
        tmps = []
    finally:
        for tmp, _ in tmps:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return {"published": sorted(items), "n": len(items)}
