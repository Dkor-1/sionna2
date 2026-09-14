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

    ⛔**창고에서 온 값**(E · n_poses · prf · prf_seen · mixed_generations)에는 예외를
      던지지 않는다. 호출자가 그 칸만 건너뛰고 `skipped` 에 까닭을 적게 한다 —
      한 칸 때문에 판독 전체가 죽으면 나머지 답도 못 얻는다.
    ⚠단서(2026-09-14) — `min_len` 은 **부르는 쪽이 정하는 손잡이**이지 창고에서 온 값이
      아니다. 잘못된 min_len 을 조용한 사유로 덮으면 `8 < nan` 이 False 라 **최소 길이
      검사가 통째로 무력화된 것을 아무도 모른다.** 그래서 그것만 예외를 던진다.

    ⛔⛔2026-09-14 넓혔다. 옛 판은 예외가 **일곱 자리**에서 새어 나갔다(외부 점검이
      둘을 짚었고, 적대 검증이 나머지를 실측으로 찾았다):
        · `np.asarray(E)` 가 울퉁불퉁한 중첩 목록에서 ValueError
        · `np.asarray(a, complex)` 가 아주 큰 정수에서 OverflowError
        · `int(n_poses)` 가 ±무한대에서 OverflowError
        · `float(prf)` 가 아주 큰 정수에서 OverflowError
        · `{float(x) for x in prf_seen}` 가 글자·목록 아닌 것에서 ValueError·TypeError
      그리고 조용히 **틀리게 통과**하던 자리가 둘 있었다:
        · 소수인 자세 수(8192.7)가 int 로 잘려 길이가 같으면 통과
        · 유일한 prf_seen 값이 원장 prf 와 달라도 통과
    """
    #: ⭐손잡이 검사 — 창고 값이 아니므로 여기서는 던진다(위 단서).
    if isinstance(min_len, bool) or not isinstance(min_len, (int, np.integer)) or min_len < 0:
        raise TypeError(f"min_len 은 0 이상 정수여야 한다(받은 {min_len!r})")

    why: list[str] = []
    try:
        a = np.asarray(E)
    except Exception as e:                      # noqa: BLE001 — 까닭으로 돌려주는 것이 계약이다
        return [f"시계열을 배열로 못 읽는다({type(e).__name__}: {str(e)[:60]})"]
    if a.size == 0:
        return ["시계열이 비어 있다"]
    if a.ndim != 1:
        why.append(f"시계열이 1 차원이 아니다(차원 {a.ndim})")
    if a.size < min_len:
        why.append(f"자세가 너무 적다({a.size} < {min_len})")
    try:
        c = np.asarray(a, complex)
    except Exception as e:                      # noqa: BLE001
        return why + [f"시계열을 복소수로 못 읽는다(dtype {a.dtype} · {type(e).__name__})"]
    if not np.isfinite(c).all():
        n = int((~np.isfinite(c)).sum())
        why.append(f"비유한 값이 {n} 자세에 있다(NaN·무한)")
    if n_poses is not None:
        #: ⛔예외를 던지지 않는다는 약속을 지킨다 — NaN·글자·±무한대가 와도 까닭으로.
        #: ⭐**변환 전후로** 본다 — `int(8192.7)` 은 8192 라 길이가 같으면 조용히 통과했다.
        try:
            fv = float(n_poses)
            if not math.isfinite(fv) or not float(fv).is_integer():
                raise ValueError("정수가 아니다")
            want = int(fv)
        except Exception:                       # noqa: BLE001
            why.append(f"원장의 자세 수를 못 읽는다({n_poses!r})")
        else:
            if a.size != want:
                why.append(f"자세 수가 원장과 다르다(시계열 {a.size} · 원장 {want})")
    #: ⛔⛔표집률은 «있나» 만 보면 안 된다 — 0·음수·NaN 이면 시간축이 무너진다.
    pv = None
    if prf is None:
        why.append("이 칸의 표집률을 모른다(원장에 prf_hz 가 없다)")
    else:
        try:
            pv = float(prf)
        except Exception:                       # noqa: BLE001
            why.append(f"표집률을 수로 못 읽는다({prf!r})")
            pv = None
        else:
            if not math.isfinite(pv) or pv <= 0:
                why.append(f"표집률이 쓸 수 없는 값이다({pv})")
                pv = None
    if prf_seen is not None:
        #: ⭐목록인지부터 본다 — 글자는 «한 자씩» 돌아 엉뚱한 사유를 낸다.
        if isinstance(prf_seen, (str, bytes)) or not hasattr(prf_seen, "__iter__"):
            why.append(f"본 표집률 목록이 목록이 아니다({prf_seen!r})")
        else:
            try:
                vals = [float(x) for x in prf_seen]
            except Exception:                   # noqa: BLE001
                why.append(f"본 표집률 목록을 수로 못 읽는다({prf_seen!r})")
            else:
                bad = [v for v in vals if not math.isfinite(v) or v <= 0]
                if bad:
                    why.append(f"본 표집률에 쓸 수 없는 값이 있다({sorted(bad)})")
                seen = sorted({v for v in vals if math.isfinite(v)})
                if len(seen) > 1:
                    why.append(f"한 칸에 표집률이 여럿 섞였다({seen})")
                #: ⭐⭐**원장과 맞대 본다**(2026-09-14 추가). 옛 판은 목록 안에서 갈리는지만
                #  보고, 유일한 값이 원장 prf 와 **달라도 통과**시켰다.
                elif len(seen) == 1 and pv is not None and abs(seen[0] - pv) > 1.0:
                    why.append(f"샤드가 본 표집률이 원장과 다르다(샤드 {seen[0]} · 원장 {pv})")
    #: ⛔⛔2026-09-14 — `mixed_generations` 가 **dict** 로 오면 «있다» 만 보고 거절하던
    #  것을 고쳤다. `one_generation` 은 세대를 **깨끗이 푼** 칸에도 진단 dict 를 돌려준다.
    #  참·거짓만 보면 그런 칸까지 일괄 거절한다 — 실측(2026-09-14): 창고의 두 세대 칸 4 개는
    #  전부 `kept_conflicting_poses=0 · tie_unresolved=False` 로 깨끗이 풀렸고,
    #  발간본 outputs/read_wfsurvive_0912.json 의 4 행이 거기서 나온다.
    if isinstance(mixed_generations, dict):
        _k = int(mixed_generations.get("kept_conflicting_poses") or 0)
        _t = bool(mixed_generations.get("tie_unresolved"))
        _d = mixed_generations.get("n_poses_disagree")
        if _k or _t or _d:
            why.append(f"굽기 세대를 하나로 못 풀었다(갈린 자세 {_k} · 동점 {_t} · 표본수 {_d})")
    elif mixed_generations:
        why.append("굽기 세대가 섞였고 한 세대로 못 풀었다")
    return why


#: 샤드 검사가 보는 meta 자리. ⛔빌더가 적는 차례다(elevation_sweep_md.py 의 `meta=`).
_META_N_POSES, _META_PRF = 3, 4


def check_shards(paths) -> tuple[int | None, float | None, list[str]]:
    """⭐**배열에 대입하기 전에** 그 칸의 샤드를 전부 본다 — (표본수, 표집률, 까닭목록).

    왜 있나 (2026-09-14 · 외부 점검 + 적대 검증이 합성 샤드로 재현)
    ------------------------------------------------------------
    두 판독기는 첫 샤드에서만 표본수·표집률을 뽑고, `idx` 는 **검사 없이 대입**했다.
    그래서 아래가 전부 조용히 통과했다(전부 실측 재현):
      · 둘째 샤드의 표집률이 NaN — `abs(nan - 19700) > 1.0` 이 **언제나 거짓**이라 샌다
        (0.0 은 제대로 거절된다. NaN 만 새는 까닭이 이것이다)
      · 음수 idx — NumPy 가 끝 기준 인덱스로 받아 **시간 순서가 뒤집힌 채** 통과
      · 소수 idx — `.astype(int)` 가 4.9 → 4 로 조용히 자름
      · 샤드마다 표본수(meta[3])가 다름 — 첫 샤드가 작은 쪽일 때만 통과
      · 한 샤드 안 같은 자세가 두 번
    그리고 범위 밖 idx 는 대입에서 **IndexError 로 판독 전체를 죽였다** — 그 칸만
    건너뛰는 것이 아니다.
    ⚠실제 창고에는 이런 샤드가 **한 장도 없다**(2026-09-14 전수: 파일 7,685 · 칸 2,408 ·
      이상 0). 이것은 창고가 깨졌을 때 조용히 틀린 수를 내지 않게 하는 관문이다.

    ⛔예외를 던지지 않는다(`check_series` 와 같은 계약). 못 읽는 파일도 까닭으로 돌려준다.
    ⛔겹친 자세는 **값이 다를 때만** 거절한다 — 창고의 `ours_*` 11 칸이 겹치되 값이 같다.
    """
    why: list[str] = []
    n0 = prf = None
    #: ⛔빈 목록에서 «까닭 없음 + n0 None» 을 돌려주면 부르는 쪽의 `np.zeros(n0, …)` 가
    #  TypeError 로 죽는다 — 「까닭이 없다 = 쓸 수 있다」가 깨지는 유일한 자리였다.
    if not list(paths):
        return None, None, ["그 칸의 샤드 목록이 비었다"]
    ns, prfs, seen_vals = [], [], {}
    for p in list(paths):
        #: ⛔⛔2026-09-14(2) 정정 — 옛 판은 `np.load(p)` 와 `set(z.files)` **두 줄만** try 로
        #  감쌌다. 그런데 npz 는 **게으르게** 읽히므로 열기는 늘 성공하고 실제 읽기는
        #  `z["meta"]`·`z["idx"]`·`z["E"]` 에서 일어난다 — 전부 try 밖이었다.
        #  ⛔적대 검증 실측(2026-09-14): 다섯 꼴이 예외로 새어 **판독 전체를 죽였다** —
        #    비트 하나 뒤집힌 샤드(BadZipFile: Bad CRC-32) · object 배열 E(ValueError) ·
        #    글자 meta(ValueError) · 2 차원 idx(TypeError) · 0 차원 idx(TypeError).
        #  ⛔⛔그중 2 차원 idx 는 **이 관문이 새로 만든 것**이었다 — 옛 대입 고리
        #    `E[ii] = z["E"]` 는 그것을 멀쩡히 받았는데 겹침 검사의 `zip(…tolist())` 가
        #    중첩 목록을 열쇠로 써서 죽는다. 죽는 자리를 하나 없애고 다섯을 만든 셈이었다.
        #  ⚠가장 크게 노출된 곳은 `benchmark/read_altitude_0914.py` 다 — 그 판독기는
        #    `one_generation` 을 안 부르고 곧장 여기로 오므로 앞에서 받아 줄 try 가 없다.
        #  ⇒ 고리 **몸통 전체**를 감싼다. 「그 칸만 건너뛰고 까닭을 적는다」가 계약이다.
        try:
            z = np.load(p)
            keys = set(z.files)
            if not {"idx", "E", "meta"} <= keys:
                why.append(f"샤드에 idx·E·meta 가 다 있지 않다({os.path.basename(str(p))})")
                continue
            meta = np.asarray(z["meta"], float).ravel()
            if meta.size <= _META_PRF:
                why.append(f"샤드의 meta 가 짧다({os.path.basename(str(p))} · 길이 {meta.size})")
                continue
            n_i, prf_i = float(meta[_META_N_POSES]), float(meta[_META_PRF])
            if not math.isfinite(n_i) or n_i <= 0 or not float(n_i).is_integer():
                why.append(f"샤드의 표본수가 쓸 수 없는 값이다({os.path.basename(str(p))}: {n_i})")
            else:
                ns.append(int(n_i))
            if not math.isfinite(prf_i) or prf_i <= 0:
                why.append(f"샤드의 표집률이 쓸 수 없는 값이다({os.path.basename(str(p))}: {prf_i})")
            else:
                prfs.append(prf_i)
            idx = np.asarray(z["idx"])
            E = np.asarray(z["E"])
            #: ⛔차원부터 본다 — 2 차원 idx 가 아래 겹침 고리까지 가면 TypeError 로 죽는다.
            if idx.ndim != 1 or E.ndim != 1:
                why.append(f"샤드의 idx·E 가 1 차원이 아니다({os.path.basename(str(p))} · "
                           f"idx {idx.ndim} 차원 · E {E.ndim} 차원)")
                continue
            if idx.size != E.size:
                why.append(f"샤드의 idx 와 E 의 길이가 다르다({idx.size} · {E.size})")
                continue
            if not np.issubdtype(idx.dtype, np.integer):
                #: ⛔⛔값이 아니라 **자료형**으로 본다. 옛 판은 `np.asarray(idx, float)` 로 바꿔
                #  봤는데, 그러면 글자 배열 ["0","1",…] 이 수로 바뀌어 **까닭 하나 없이 통과**했다
                #  (2026-09-14(2) 적대 검증). 자료형을 보는 것이 이 관문의 일이다.
                why.append(f"샤드의 idx 가 정수형이 아니다({os.path.basename(str(p))} · "
                           f"dtype {idx.dtype})")
                continue
            ii = np.asarray(idx).astype(np.int64)
            if np.unique(ii).size != ii.size:
                why.append(f"한 샤드 안에 같은 자세가 두 번 있다({os.path.basename(str(p))})")
            lo, hi = (int(ii.min()), int(ii.max())) if ii.size else (0, -1)
            if ii.size and (lo < 0 or (ns and hi >= max(ns))):
                why.append(f"샤드의 idx 가 범위를 벗어난다(최소 {lo} · 최대 {hi} · 표본수 "
                           f"{max(ns) if ns else '?'})")
            #: ⭐겹친 자세는 값이 **다를 때만** 거절한다.
            #: ⛔⛔2026-09-14(2) — 옛 판은 **처음 걸린 자세**에서 `break` 했다. 그런데 처음
            #  걸리는 것은 대개 마지막 자릿수 차이라, 찍힌 두 값이 눈으로는 같아 보였다
            #  (실측: -0.00041002931253579283 ↔ -0.0004100293125357928). 같은 칸에서 진짜
            #  갈리는 자세의 상대차는 최대 4.995e-01 인데도 그렇다 — 읽는 사람이 그 까닭을
            #  보고 「관문이 예민하다」로 잘못 닫을 자리였다. ⇒ **전부 세고 가장 큰 것**을 적는다.
            Ec = np.asarray(E).ravel()
            _n_clash, _worst = 0, None
            for k, v in zip(ii.tolist(), Ec.tolist()):
                if k in seen_vals:
                    o = seen_vals[k]
                    if o != v:
                        _n_clash += 1
                        rel = abs(v - o) / max(abs(o), 1e-300)
                        if _worst is None or rel > _worst[0]:
                            _worst = (rel, k, o, v)
                else:
                    seen_vals[k] = v
            if _worst:
                why.append(f"샤드 사이에 같은 자세의 값이 다르다(갈린 자세 {_n_clash} 개 · "
                           f"가장 큰 상대차 {_worst[0]:.3e} @ 자세 {_worst[1]} · "
                           f"{_worst[2]!r} ↔ {_worst[3]!r})")
        except Exception as _e:                 # noqa: BLE001 — 까닭이 계약이다
            why.append(f"샤드를 못 읽는다({os.path.basename(str(p))} · "
                       f"{type(_e).__name__}: {str(_e)[:60]})")
            continue
    if ns:
        if len(set(ns)) > 1:
            why.append(f"샤드마다 표본수가 다르다({sorted(set(ns))})")
        else:
            n0 = ns[0]
    if prfs:
        if max(prfs) - min(prfs) > 1.0:
            why.append(f"샤드마다 표집률이 다르다({sorted(set(prfs))})")
        else:
            prf = prfs[0]
    #: 같은 까닭이 여러 샤드에서 나오면 한 번만 적는다 — 읽는 이가 세기 쉽게.
    out, seen_why = [], set()
    for w in why:
        if w not in seen_why:
            seen_why.add(w)
            out.append(w)
    return n0, prf, out


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
#: ⭐표 칸이 쓸 수 있는 **닫힌 단위 목록**. 여기 없는 단위를 쓰면 그 칸은 값 자리로
#  안 보이고 글 검사가 지나간다 — 그래서 `cell()`(아래)이 **진짜 방벽**이고 글 검사는 보조다.
_UNITS = ("dBsm", "dBm", "dBi", "dB", "GHz", "MHz", "kHz", "Hz", "%p", "%",
          "ms", "µs", "us", "ns", "mm", "cm", "km", "m", "s", "°",
          "점", "판", "칸", "개", "배", "자리", "쌍", "행")
#: ⛔「자세」는 일부러 **뺐다**(2026-09-14). 자세 수는 언제나 정수라 비유한 수가 될 수
#  없는데, 단위로 두면 `check_series` 의 사유 「비유한 값이 4 자세에 있다(NaN·무한)」가
#  표 칸 안에서 값 자리로 읽혀 거절됐다 — 사유는 실려야 하는 글이다.
_UNIT_RE = "(?:" + "|".join(re.escape(u) for u in sorted(_UNITS, key=len, reverse=True)) + ")"
#: 값 자리 = **짧은 이름표** + 부호 + 토막 + **닫힌 단위**. 왼쪽 낱말 경계를 강제한다.
#  ⛔⛔2026-09-14 세 번째 정정. 옛 판은
#   ⓐ 왼쪽 경계가 없어 낱말 **끝**이 nan·inf 이면 값으로 봤다 — 실제 저자 이름
#     «P. V. Brennan»(outputs/reflib_sweep_venues.json)과 «second_prf_nan» 이 거절됐다.
#   ⓑ 뒷글자를 `[%\w°/·()]{0,8}` 로 두어 **한글을 단위로 삼켰다** — 「NaN 감지」·
#     「NaN 때문에 제외했다」가 거절됐다(뒤가 각각 2 자·8 자).
#   ⓒ 이름표에 숫자를 금지해 «h1 nan»·«b3 nan»·«1 차 조화 nan» 이 **검사를 통째로 껐다**.
#   ⓓ 꾸밈을 안 벗겨 «**nan**» · «`nan`» · «ｎａｎ»(전각) 이 틀에 아예 안 걸렸다.
_LABEL_MAX = 12
#: 표 칸에서 수·부호·단위·구분자를 지우고 **남는 글자**가 이보다 많으면 산문으로 본다.
#  ⚠이건 내가 정한 손잡이다 — 머리기사 숫자가 아니므로 흔드는 대신 아래 시험 32 줄로 못 박는다.
#  8 로 잡은 근거: 「띠 안 최강선」(5 자) 같은 이름표는 값 자리로 남기고,
#  「비유한 값이 4 자세에 있다(NaN·무한)」(12 자)는 산문으로 넘긴다.
_PROSE_MAX = 8
_VALUE_ONLY_RE = re.compile(
    r"^(?P<pre>.*?)(?:(?<=^)|(?<=[\s~=(\[]))[-+±]?\s*"
    r"(?P<tok>" + _NF_TOKEN + r")(?![A-Za-z0-9_])"
    r"(?P<post>\s*" + _UNIT_RE + r"?)\s*$")

#: 가장자리 꾸밈만 벗긴다. ⛔가운데 `_` 까지 벗기면 «second_prf_nan» 이 도로 거짓 거절이 된다.
_TRIM = " \t*_`~\"'«»‹›“”‘’"


def _undecorate(t: str) -> str:
    """표 칸의 꾸밈을 벗긴다 — 굵게·기울임·코드·HTML 태그·링크·각주·전각."""
    t = re.sub(r"<[^<>]{1,40}>", "", t)                 # <b>nan</b> · <td>nan</td>
    t = re.sub(r"\[([^\]]{0,60})\]\([^)]{0,80}\)", r"\1", t)   # [nan](#x)
    t = re.sub(r"\[\^[^\]]{1,20}\]", "", t)              # 각주 [^1]
    t = "".join(chr(ord(ch) - 0xFEE0) if 0xFF01 <= ord(ch) <= 0xFF5E else ch for ch in t)
    return t.strip(_TRIM)


def _VALUE_ONLY(t: str):
    """이 토막이 «값 자리» 인가 — 맞으면 match 처럼 참을 돌려준다."""
    m = _VALUE_ONLY_RE.match(_undecorate(t))
    if not m:
        return None
    if len(m.group("pre").strip(_TRIM)) > _LABEL_MAX:
        return None
    return m


#: 표 한 칸 안에서 값이 여럿 붙는 자리 — «1272.9 · 380.3 ( -6.0 dB)» 처럼 쓴다.
_PART_SPLIT = re.compile(r"[·,;()\[\]]|\s{2,}")
#: 산문인지 가르는 데 쓴다 — 수·부호·단위·구분자를 지우고 남는 글자 수를 센다.
_STRIP_VALUEISH = re.compile(r"[\d\s.,;:()\[\]~·+\-±/%°]|" + _UNIT_RE + "|" + _NF_TOKEN)


def _is_prose(cell: str) -> bool:
    """이 표 칸이 **산문**인가 — 그렇다면 토막으로 가르지 않는다.

    ⛔`check_series` 가 돌려주는 진짜 사유 「비유한 값이 4 자세에 있다(NaN·무한)」가
      표 칸에 들어가면 `_PART_SPLIT` 이 괄호와 «·» 로 갈라 맨 «NaN» 토막을 만들어
      거절됐다(2026-09-14 실측). 사유 문장은 발간을 막는 것이 아니라 실려야 한다.
    """
    return len(_STRIP_VALUEISH.sub("", _undecorate(cell))) > _PROSE_MAX


def _value_slots(s: str):
    """이 글에서 **값 자리**만 뽑아 준다 — 글 전체이거나, 마크다운 표의 한 칸(의 토막)이거나."""
    if _VALUE_ONLY(s):
        yield s.strip(), 0
        return
    for ln, line in enumerate(s.splitlines()):
        t = line.strip()
        if not (t.startswith("|") and t.endswith("|")):
            continue
        for cell_txt in t[1:-1].split("|"):
            if _VALUE_ONLY(cell_txt):
                yield cell_txt.strip(), ln + 1
            elif not _is_prose(cell_txt):
                for part in _PART_SPLIT.split(cell_txt):
                    if _VALUE_ONLY(part):
                        yield part.strip(), ln + 1


def cell(v, spec: str = "", unit: str = "", *, none: str = "없음") -> str:
    """⭐표 한 칸에 수를 찍는 **유일한 문**. 없으면 «없음», 비유한 수면 여기서 멈춘다.

    왜 있나 — 글 검사(위)는 **글자를 세는 일**이라 표기가 늘어날 때마다 구멍이 난다.
    2026-09-14 에 표기 53 가지로 재니 옛 틀이 21 가지를 틀리게 갈랐다. 진짜 방벽은
    **수가 글로 바뀌는 그 자리**에 두어야 한다 — `float` 와 표 칸 사이에 문이 하나도
    없어서 `docs/WFSURVIVE_0912.md` 에 «nan» 이 20 자리 실렸던 것이다.
    ⛔유한한 값에서는 `format(x, spec)` 과 **한 글자도 다르지 않다** — 옮겨도 문서가 안 바뀐다.
    """
    if v is None:
        return none
    x = float(v)
    if not math.isfinite(x):
        raise ValueError(f"표 칸에 비유한 수를 찍으려 한다({x!r} · 서식 {spec!r}{unit!r}) — "
                         "값이 없으면 None 을 넘겨라(«없음» 으로 찍힌다)")
    return format(x, spec) + unit


def _nonfinite_paths(o, path: str = "") -> list[str]:
    """비유한 수가 있는 자리를 경로째 찾는다 — 발간 전 거절의 근거.

    ⛔⛔2026-09-13(10) 넓혔다 — 옛 판은 `isinstance(o, float)` 만 봐서
      **numpy 형(np.float32·np.complex128)·0 차원 배열·복소수**를 놓쳤고,
      **글(마크다운)** 은 아예 안 봤다.
    ⭐글은 «값 자리» 만 본다(`_value_slots`). 문장 속 낱말은 막지 않는다.
    """
    out: list[str] = []
    if isinstance(o, dict):
        for k, v in o.items():
            out += _nonfinite_paths(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            out += _nonfinite_paths(v, f"{path}[{i}]")
    elif isinstance(o, str):
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
