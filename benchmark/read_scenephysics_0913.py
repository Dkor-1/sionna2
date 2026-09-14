#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""read_scenephysics_0913.py — **장면 축 × 물리 축**을 교차시켜 읽는다. (세 갈래 중 (가))

■ 왜 만들었나
  0910 덱 9 쪽이 스스로 열어 둔 ⚠ 가 있다:
    「회절을 켠 두 팔은 다섯 칸에서 필터 뒤 값이 빈 하늘보다 **높다** — 필터가 없던
      구조를 만들었는지 **안 갈랐다**. 그 팔에는 아직 안 쓴다.」
  그 판정을 하려면 켠 팔이 **여러 장면·여러 앙각에** 서야 하는데, 2026-09-12 재고로는
  장면을 조각낸 판(지면만·건물만)에 켠 팔이 **한 칸도 없었다**. 0928 큐가 그것을 산다.
  이 판독기는 **지금 있는 칸으로 먼저 돌고**, 0928 이 들어오면 그대로 다시 돌면 된다.

■ 무엇을 재나 — 칸마다 (장면, 팔, 앙각), 빈 하늘 짝이 있을 때만
  ① 장면이 얹은 몫  lift = 레벨(장면) − 레벨(빈 하늘)
  ② 갈아낀 자세 수  덱의 잣대 그대로(hampel_mask win=51 · k=5.0) — 96·339 를 만든 그 잣대
  ③ ⭐**필터 뒤 값이 빈 하늘보다 높은가** — 덱이 열어 둔 ⚠ 그 자체
     순서는 덱과 같다(bake_outdoor.py:465): **갈아끼우고 나서** 정지 성분을 뺀다.

■ ⛔이 판독기가 답하지 않는 것
  · ⛔「어느 팔이 맞는가」를 답하지 않는다. 다섯 팔은 전부 근사이고 현실은 실기 계측이
    정한다 — **실기 계측 대조는 0 건**이다.
  · ⛔팔 사이의 **절대 레벨을 견주지 않는다**(집 규약). 견주는 것은 각 팔이 **자기 빈 하늘
    짝과** 얼마나 떨어지는가다.
  · ⛔D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·후보 탐색
    차이가 함께 들어간다. 「장면이 얹은 몫」으로만 부른다(read_canyonnull_0910 과 같은 한정).
  · ⛔지면만·건물만은 **우리 장면을 조각낸 것**이라 솔버가 주는 협곡과 같지 않다.
    드론 고도도 다르다(우리 20 m · 솔버 25 m). 장면을 가로질러 더하지 않는다.
  · ⛔갈아낀 자세 수를 «사건» 으로 부르되 그것이 무엇인지는 이 판이 말하지 않는다.

쓰는 법 (⛔CPU 전용):
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/read_scenephysics_0913.py
"""
from __future__ import annotations

import contextlib
import glob
import importlib.util
import io
import json
import collections
import os
import re
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
#: ⭐팔 이름은 **문법으로** 되읽는다 — 정규식으로 긁지 않는다(2026-09-13(4)).
from arm_grammar import parse as parse_arm, unparse as unparse_arm   # noqa: E402
from reader_gate import check_series, check_shards, publish                        # noqa: E402
DECK = "/workspace/team_meeting/teammeeting_0910"
OUT = os.path.join(ROOT, "outputs/read_scenephysics_0913.json")
MD = os.path.join(ROOT, "docs/SCENEPHYSICS_0913.md")
#: ⛔⛔2026-09-13 정정 — **팔 이름을 틀리게 적었다.** 스위치 글자는
#    R = 굴절(refraction) · D = 회절(diffraction) · E = 모서리회절(edge) · F = 확산반사(diffuse)
#  다(elevation_sweep_md.py:745 `sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)`).
#  첫 판은 D 를 «굴절», R 을 «반사» 로 적어 **두 이름이 서로 바뀌어** 있었다.
#  ⛔그 탓에 「회절을 켠 팔」을 셀 때 D1 인 R1D1E1F1 이 «전부» 라는 이름 때문에 빠져
#    덱의 ⚠ 가 반대 방향으로 보였다. 이름 하나가 판정을 뒤집었다.
ARMS = {"R0D0E0F1": "확산만", "R0D1E0F1": "+회절", "R0D1E1F1": "+회절+모서리회절",
        "R1D0E0F1": "+굴절", "R1D1E1F1": "전부(굴절+회절+모서리)"}


def has_diffraction(arm: str) -> bool:
    """D 비트 — 회절을 켰나. ⛔이름 문자열로 세지 않는다(그래서 틀렸다)."""
    return arm[3] == "1"


def prod():
    """⛔병합을 다시 구현하지 않는다 — 생산 코드를 그대로 부른다."""
    spec = importlib.util.spec_from_file_location(
        "esm", os.path.join(ROOT, "benchmark/elevation_sweep_md.py"))
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass
    return m


def deck_filters():
    """⛔필터를 다시 구현하지 않는다 — 덱이 쓰는 그 함수를 부른다."""
    if DECK not in sys.path:
        sys.path.insert(0, DECK)
    from bake_outdoor import drop_outliers, hampel_mask       # noqa: PLC0415
    return hampel_mask, drop_outliers


def series(esm, arm, el, n_poses_ledger=None):
    """이 칸의 시계열 — **언제나 두 값**을 돌려준다: (전계 또는 None, (이름표, 글) 목록).

    ⛔⛔2026-09-14 정정. 이 함수는 자료 없음·표집률 혼합·조각 미완에서 **맨 None** 을
      돌려주는데, 부르는 쪽(:283·284)은 항상 두 값으로 풀었다. 그래서 창고가 비면
      `TypeError: cannot unpack non-iterable NoneType object` 로 **판독 전체가 죽었다.**
      ⚠이건 남아 있던 결함이 아니라 커밋 621f0a97 이 낸 **회귀**다 — 그 커밋이 같은 병을
      `read_wfsurvive_0912.cell_series` 에서는 고치면서 여기는 호출부만 두 값으로 바꾸고
      앞의 세 return 을 그대로 뒀다. 세 조건 다 실측으로 재현했다(2026-09-14).
      ⚠같은 커밋의 두 번째 피해자는 `benchmark/review_full_0912.py:481` 이다.
    ⭐사유를 (이름표, 글) 로 두는 까닭 — 부르는 쪽이 «자료 없음» 과 «관문 거절» 을
      가려서 적어야 한다. 평평한 글 목록으로 통일하면 그 구분이 깨진다.
    """
    fs = sorted(glob.glob(f"{esm.SHD}/{arm}_el{el:+g}_*.npz"))
    if not fs:
        return None, [("조각 없음", "그 칸의 조각이 창고에 없다")]
    #: ⛔⛔`one_generation` 은 세대를 고르려고 **제가 먼저 전계를 대입해 본다** — 그래서
    #  범위 밖 idx 가 든 샤드는 아래 `check_shards` 에 닿기 전에 IndexError 로 판독 전체를
    #  죽인다(2026-09-14 실측). 「그 칸만 건너뛴다」를 지키려면 여기서 받아야 한다.
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fs, gen = esm.one_generation(fs, f"{arm}/el{el:+g}")
    except Exception as e:                      # noqa: BLE001 — 까닭으로 돌려주는 것이 계약이다
        return None, [("세대 고르기 실패", f"세대를 고르다 죽었다({type(e).__name__}: {str(e)[:80]})")]
    #: ⭐⭐**대입하기 전에** 샤드를 전부 본다(src/reader_gate.check_shards).
    #  옛 판은 첫 샤드에서만 표본수·표집률을 뽑고 idx 는 검사 없이 대입해서,
    #  둘째 샤드의 NaN 표집률·음수 idx·소수 idx·표본수 불일치가 조용히 통과했다.
    #  범위 밖 idx 는 대입에서 IndexError 로 **판독 전체를 죽였다**(2026-09-14 실측).
    n0, prf0, _sw = check_shards(fs)
    if _sw:
        return None, [("샤드 검사", w) for w in _sw]
    E = np.zeros(n0, complex)
    seen = np.zeros(n0, bool)
    for f in fs:
        z = np.load(f)
        ii = z["idx"].astype(int)
        E[ii] = z["E"]
        seen[ii] = True
    if not seen.all():
        return None, [("조각 덜 참", f"조각이 덜 찼다({int(seen.sum())}/{seen.size} 자세)")]
    #: ⭐공통 입력 관문(src/reader_gate.py) — 비유한 값·길이·차원을 여기서 거른다.
    #: ⛔⛔`n_poses=E.size` 는 빈 검사였다 — 원장의 값을 받는다(2026-09-13(10)).
    #: ⭐세대 진단을 **버리지 않는다**(2026-09-14). 다만 «있으면 거절» 이 아니라
    #  갈린 자세가 남았는지로 판정한다 — 깨끗이 풀린 두 세대 칸까지 버리면 안 된다.
    _why = check_series(E, n_poses=n_poses_ledger, prf=prf0, mixed_generations=gen)
    return (None, [("입력 관문 거절", t) for t in _why]) if _why else (E, [])


def db(x):
    return round(float(20 * np.log10(float(x) + 1e-300)), 2)


def main() -> int:
    esm = prod()
    hampel_mask, drop_outliers = deck_filters()
    L = json.load(open(os.path.join(ROOT, "outputs/elevation_sweep_md.json"), encoding="utf-8"))

    #: ⛔⛔2026-09-13(2) 적대적 검증이 찾은 것 — 첫 판은 장면을 **네 이름 목록**으로 갈랐다.
    #  목록에 없는 장면은 «free»(빈 하늘)로 찍혔고, 그러면 `sc(...) == "free": continue` 에
    #  걸려 **행으로도 안 나오고 skipped 에도 안 남는다.** n_skipped == 0 이 «다 봤다» 가 아니다.
    #  ⛔실측: 원장에 `sionna-munich` 장면 칸이 4 개 있는데 그렇게 조용히 사라졌다.
    #  ⇒ 꼬리표를 **이름에서 뽑는다**(목록이 아니다). 모르는 장면도 제 이름으로 선다.
    #: ⛔⛔2026-09-13(4) 또 정정 — 위의 정규식은 `_mfix`/`_blper` 까지 **통째로 먹는다.**
    #  그 사이에 오는 꼬리표가 전부 장면 이름에 딸려 들어간다. 실측: 팔 844 개 중 **57 개**가
    #  이렇게 어긋난다 — `outdoor01_S0.3` · `outdoor01_az45` · `outdoor01_fc3450` ·
    #  `outdoor01_rotoutdoor_v2s1` · `outdoor01_ground_ps1.05_fs1.05` …
    #  ⇒ 이제 이름을 **문법으로 되읽는다**(src/arm_grammar.py). 그 문법은 이름을 «짓는»
    #    benchmark/elevation_sweep_md.py 에서 그대로 옮긴 것이고, 되읽은 것을 다시 지어
    #    원본과 글자까지 같은지 확인한다 — 조각이 조용히 딸려 오거나 사라질 수 없다.
    def env_tag(e):
        return parse_arm(e).get("env")

    SHORT = {"sionna-simple_street_canyon": "canyon", "outdoor01_ground": "gnd",
             "outdoor01_bldg": "bldg", "outdoor01": "outdoor", "sionna-munich": "munich"}

    def sc(e):
        t = env_tag(e)
        return "free" if t is None else SHORT.get(t, t)

    #: ⭐쓸 수 있는 팔의 꼬리표 **허용목록**. ⛔블록리스트를 쓰지 않는다 — 옛 판은
    #  `_(…|rot|…)[\d._]` 라 `_rot` 뒤에 글자가 오는 `rotoutdoor_v2s1` 이 **새어 들어왔고**,
    #  그 3 행이 로터 설정이 다른 빈 하늘과 짝지어졌다(2026-09-13(4) 실측).
    #  허용목록은 새로운 꼬리표가 생겨도 조용히 통과시키지 않는다 — 모르면 막는다.
    ALLOWED = {"engine", "spp", "switches", "range_m", "n_poses",
               "max_depth", "env", "mesh_fix", "blade_law"}

    def extra_tags(e):
        """허용목록 밖의 꼬리표. ⭐빈 집합이 아니면 그 팔은 안 쓰고 **왜인지 적는다**."""
        try:
            return sorted(set(parse_arm(e)) - ALLOWED)
        except Exception:
            return ["이름을 문법으로 못 읽었다"]

    #: 이 잣대가 요구하는 팔·원장 값. 어긋나면 **그 자리를 이름으로** 적는다.
    _WANT = (("engine", "sionna", "엔진"), ("spp", "4000000000", "광선 예산"),
             ("range_m", "15", "거리[m]"), ("n_poses", "8192", "자세 수"),
             ("max_depth", "2", "반사 깊이"))

    def why_unusable(r):
        """못 쓰는 **까닭 전부**를 (이름표, 글) 로 돌려준다 — 빈 목록이면 쓸 수 있다.

        ⛔⛔2026-09-13(10) 고쳤다. 옛 판 `usable()` 은 참·거짓만 돌려줬고, 부르는 쪽은
          **꼬리표 때문일 때만** 건너뜀에 적었다. 그래서 꼬리표는 깨끗한데 광선 예산·
          거리·깊이가 다른 칸이 행에도 건너뜀에도 없이 사라졌다 — 이 파일 머리말이
          스스로 「건너뜀 0 이 «다 봤다» 가 아니다」라고 적어 둔 바로 그 병이다.
        """
        e = r["engine"]
        try:
            f = parse_arm(e)
        except Exception:
            return [("이름을 못 읽음", "이름을 문법으로 못 읽었다")]
        why = []
        extra = sorted(set(f) - ALLOWED)
        if extra:
            why.append(("허용 밖 꼬리표",
                        "이 잣대가 허용하지 않는 꼬리표가 붙어 있다: " + " · ".join(extra)
                        + " — 장면×물리 표는 **다른 축이 안 섞인** 팔만 쓴다"))
        for k, v, ko in _WANT:
            if f.get(k) != v:
                why.append((f"{ko} 다름",
                            f"{ko}이(가) 이 잣대의 값과 다르다(팔 {f.get(k)!r} · 이 잣대 {v!r})"))
        if not f.get("switches"):
            why.append(("스위치 꼬리표 없음",
                        "스위치 꼬리표가 없다 — 어느 물리를 켠 판인지 이름이 안 말한다"))
        if r.get("n_missing") != 0:
            why.append(("자세 덜 참", f"자세가 덜 찼다(빠진 자세 {r.get('n_missing')})"))
        if r.get("n_poses") != 8192:
            why.append(("원장 자세 수 다름",
                        f"원장의 자세 수가 다르다({r.get('n_poses')} · 이 잣대 8192)"))
        if r.get("spp") != 4e9:
            why.append(("원장 광선 예산 다름",
                        f"원장의 광선 예산이 다르다({r.get('spp')} · 이 잣대 4e9)"))
        return why

    def usable(r):
        return not why_unusable(r)

    #: ⛔⛔2026-09-13 정정 — 첫 판은 빈 하늘 짝을 **(팔, 앙각) 사전**으로 찾았다.
    #  그 열쇠로는 같은 팔·앙각의 **다른 조건** 칸이 덮어쓴다.
    #  ⛔실측(2026-09-13): 63 행 중 **43 행**이 엉뚱한 짝을 골랐다 —
    #    `_rotoutdoor_v2`(다른 로터 설정) · `_prf78800`(다른 표집률) · `_x500v2`(다른 기체).
    #    거르개가 블록리스트였고 `_rot` 뒤에 숫자를 요구해 `rotoutdoor` 가 새어 들어왔다.
    #  ⇒ **이름을 지어서 고른다** — 장면 꼬리표만 뺀 이름이 원장에 있는지 본다.
    #    블록리스트가 아니라 구성이라 새는 곳이 없다. 그리고 쌍의 조건을 다시 검사한다.
    #: ⛔원장은 (팔, 앙각) 한 줄씩이다 — 팔 이름만으로 키를 잡으면 **마지막 앙각이 덮는다**
    #  (첫 수정에서 실제로 그랬다: el −30 을 찾는데 el −90 이 돌아와 58 칸이 거절됐다).
    by_engine = {(r["engine"], r["el_deg"]): r for r in L["rows"]}

    def twin_name(engine: str) -> str:
        """장면 꼬리표만 뺀 이름 — 이것이 유일한 대조군이다.

        ⛔⛔2026-09-13(2) — 첫 판은 네 이름 목록에서 찾아, **목록에 없는 장면이면 이름을
        그대로 돌려줬다.** 그러면 대조군이 **자기 자신**이 되어 얹은 몫이 0 dB 로 나오고
        쌍 검사도 통과한다(같은 행이니까). ⇒ 꼬리표를 이름에서 뽑아 **그것만** 뺀다.
        뽑히지 않으면 None 을 돌려주고 호출자가 거른다 — 조용히 자기 자신을 쓰지 않는다.
        """
        #: ⛔문자열 치환이 아니라 **꼬리표를 빼고 다시 짓는다**(2026-09-13(4)).
        #  치환은 장면 이름이 잘못 뽑히면 엉뚱한 자리를 지운다 — 로터 꼬리표까지 장면으로
        #  읽힌 3 행이 실제로 **로터 설정이 다른 빈 하늘**과 짝지어져 있었다.
        f = parse_arm(engine)
        if f.get("env") is None:
            return None
        f = {k: v for k, v in f.items() if k != "env"}
        return unparse_arm(f)

    rows, skipped = [], []
    for r in sorted(L["rows"], key=lambda r: (sc(r["engine"]), r["engine"], r["el_deg"])):
        if sc(r["engine"]) == "free":
            continue
        w = why_unusable(r)
        if w:
            #: ⛔⛔장면이 붙은 칸을 **조용히** 버리지 않는다. 이 파일의 머리말이 스스로
            #  「n_skipped == 0 이 «다 봤다» 가 아니다」라고 적었는데, 거르개가 행을
            #  보기 **전에** 걸러내면 그 말이 무의미해진다(2026-09-13(4)).
            #  ⛔2026-09-13(10) — 꼬리표 까닭만 적던 것을 **까닭 전부**로 넓혔다.
            skipped.append(dict(
                engine=r["engine"], el_deg=r["el_deg"], want=None,
                extra_tags=extra_tags(r["engine"]),
                why_codes=[c for c, _ in w], why=" · ".join(t for _, t in w)))
            continue
        a = re.search(r"_sw(R\dD\dE\dF\d)", r["engine"])
        if not a:
            skipped.append(dict(engine=r["engine"], el_deg=r["el_deg"], want=None,
                                why_codes=["스위치 이름 없음"],
                                why="이름에서 스위치 꼬리표(_swR?D?E?F?)를 못 찾았다"))
            continue
        arm, el = a.group(1), r["el_deg"]
        fengine = twin_name(r["engine"])
        if fengine is None:
            skipped.append(dict(engine=r["engine"], el_deg=el,
                                why="장면 꼬리표를 이름에서 못 뽑았다 — 대조군을 정할 수 없다",
                                want=None))
            continue
        fr = by_engine.get((fengine, el))
        if fr is None or not usable(fr):
            skipped.append(dict(engine=r["engine"], el_deg=el,
                                why="장면 꼬리표만 뺀 빈 하늘 짝이 원장에 없거나 쓸 수 없다",
                                want=fengine))
            continue
        #: ⭐쌍의 조건을 다시 검사한다 — 이름이 맞아도 원장 값이 어긋나면 안 쓴다
        bad = [k for k in ("n_poses", "spp", "fc_hz", "f_tip_hz", "range_m", "max_depth")
               if r.get(k) != fr.get(k)]
        if bad:
            skipped.append(dict(engine=r["engine"], el_deg=el,
                                why=f"쌍의 조건이 어긋난다: {bad}", want=fengine))
            continue
        Es, why_s = series(esm, r["engine"], el, r.get("n_poses"))
        Ef, why_f = series(esm, fengine, el, fr.get("n_poses"))
        if Es is None or Ef is None:
            #: ⭐**까닭을 가른다** — 「자료가 없다」와 「입력 관문이 거절했다」는 다른 일이다.
            #  옛 판은 둘 다 «미완» 으로 적어 원장에서 가릴 수 없었다(2026-09-13(10)).
            _w = (why_s or []) + (why_f or [])
            skipped.append(dict(
                engine=r["engine"], el_deg=el, want=fengine,
                #: ⭐이름표로 가른다 — 「자료가 없다」와 「관문이 거절했다」는 다른 일이다.
                gate_rejected=any(c == "입력 관문 거절" for c, _ in _w),
                why_codes=[c for c, _ in _w],
                why=" · ".join(t for _, t in _w) or "장면 또는 빈 하늘 칸을 못 읽었다"))
            continue
        #: ② 덱의 잣대 그대로 — 갈아낀 자세 수
        mask = hampel_mask(np.abs(Es), 51, 5.0)
        #: ③ ⭐순서가 중요하다 — **갈아끼우고 나서** 정지 성분을 뺀다(덱 bake_outdoor.py:465)
        Er, n_rep = drop_outliers(Es, 51, 5.0)
        rows.append(dict(
            scene=sc(r["engine"]), arm=arm, arm_ko=ARMS.get(arm, arm), el_deg=el,
            engine=r["engine"], free_engine=fengine,
            level_scene_db=db(np.abs(Es).mean()), level_free_db=db(np.abs(Ef).mean()),
            lift_db=round(db(np.abs(Es).mean()) - db(np.abs(Ef).mean()), 2),
            has_diffraction=has_diffraction(arm),
            n_replaced=int(mask.sum()), n_replaced_dropfn=int(n_rep),
            #: 정지 성분을 뺀 뒤의 변동 크기 — 이것을 빈 하늘과 견준다
            ac_after_db=db(np.std(Er - Er.mean())),
            ac_free_db=db(np.std(Ef - Ef.mean())),
            above_free_db=round(db(np.std(Er - Er.mean())) - db(np.std(Ef - Ef.mean())), 2),
        ))
        x = rows[-1]
        print(f"  {x['scene']:8s} {x['arm_ko']:10s} el{el:+4g} · 얹은 몫 {x['lift_db']:+7.2f} dB"
              f" · 갈아낀 {x['n_replaced']:4d} · 필터 뒤−빈하늘 {x['above_free_db']:+7.2f} dB"
              f" {'⛔위' if x['above_free_db'] > 0 else ''}", flush=True)

    out = dict(_meta=dict(
        generator="benchmark/read_scenephysics_0913.py",
        made_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        question_ko=("장면 축 × 물리 축 — 물리 스위치를 켜면 장면이 얹은 몫과 «필터 뒤가 "
                     "빈 하늘보다 높은가» 가 달라지나"),
        deck_open_warning_ko=("0910 덱 9 쪽: 「회절을 켠 두 팔은 다섯 칸에서 필터 뒤 값이 "
                              "빈 하늘보다 높다 — 필터가 없던 구조를 만들었는지 안 갈랐다」"),
        filter_ko="덱의 hampel_mask(win=51, k=5.0)·drop_outliers 를 그대로 부른다(재구현 없음)",
        order_ko="⭐갈아끼우고 나서 정지 성분을 뺀다 — 거꾸로 하면 4 칸 그림이 8~10 dB 달라진다",
        limits_ko=[
            "⛔「어느 팔이 맞는가」를 답하지 않는다 — 다섯 팔은 전부 근사다. 실기 계측 0 건.",
            "⛔팔 사이 절대 레벨을 견주지 않는다. 각 팔이 **자기 빈 하늘 짝과** 얼마나 떨어지는가만 본다.",
            "⛔D = 장면 − 빈 하늘 은 «환경 산란» 이 아니다 — 차폐·경로 변화·후보 탐색 차이가 함께 든다.",
            "⛔지면만·건물만은 우리 장면을 조각낸 것이라 솔버가 주는 협곡과 같지 않다(고도도 20 vs 25 m).",
            "⛔갈아낀 자세를 «사건» 으로 부르되 그것이 무엇인지는 이 판이 말하지 않는다.",
        ], pairing_ko=("대조군은 **장면 꼬리표만 뺀 이름**으로 고른다(구성이지 블록리스트가 "
                       "아니다). 고른 뒤 n_poses·spp·fc·f_tip·거리·깊이를 쌍으로 다시 검사한다."),
        n_skipped=len(skipped),
        #: ⭐⭐**셈이 닫히는지 보여 준다** — 원장 행 = 자유공간(이 잣대의 범위 밖) + 쓴 칸
        #  + 건너뜀. 이 줄이 맞아떨어져야 「건너뜀 N」을 «다 봤다» 로 읽어도 된다.
        n_ledger_rows=len(L["rows"]),
        n_free_out_of_scope=sum(1 for r in L["rows"] if sc(r["engine"]) == "free"),
        accounting_closes=(len(L["rows"]) ==
                           sum(1 for r in L["rows"] if sc(r["engine"]) == "free")
                           + len(rows) + len(skipped)),
        skipped_by_reason={k: v for k, v in sorted(
            collections.Counter(c for x in skipped for c in (x.get("why_codes") or ["까닭 없음"])
                                ).items(), key=lambda kv: -kv[1])},
        ), rows=rows, skipped=skipped)
    #: ⭐⭐다 만든 뒤 한 번에 발간한다(src/reader_gate.publish).
    publish({OUT: out, MD: render(out, to_string=True)})
    n_above = sum(1 for x in rows if x["above_free_db"] > 0)
    print(f"\n✅ {os.path.relpath(OUT, ROOT)} · {os.path.relpath(MD, ROOT)}  ({len(rows)} 칸)")
    print(f"   ⭐필터 뒤가 빈 하늘보다 **높은** 칸 {n_above}/{len(rows)}")
    return 0


def render(o, to_string: bool = False):
    rows, m = o["rows"], o["_meta"]
    lines = ["# 장면 축 × 물리 축 — 필터 뒤가 빈 하늘보다 높은가", "",
             f"> ⛔손으로 쓰지 않는다. `{m['generator']}` 가 굽는다. `{m['made_utc']}`", "",
             "덱이 열어 둔 ⚠ — " + m["deck_open_warning_ko"], "",
             m["filter_ko"] + " · " + m["order_ko"], "",
             "| 장면 | 팔 | 앙각 | 얹은 몫 | 갈아낀 자세 | 필터 뒤 − 빈 하늘 |",
             "|---|---|---:|---:|---:|---:|"]
    for r in rows:
        flag = " ⛔" if r["above_free_db"] > 0 else ""
        lines.append(f"| {r['scene']} | {r['arm_ko']} | {r['el_deg']:+g} | "
                     f"{r['lift_db']:+.2f} dB | {r['n_replaced']} | "
                     f"{r['above_free_db']:+.2f} dB{flag} |")
    n_above = sum(1 for x in rows if x["above_free_db"] > 0)
    lines += ["", f"⛔표시는 필터 뒤가 빈 하늘보다 **높은** 칸 — {n_above}/{len(rows)}.", "",
              "## ⛔이 판독이 말하지 않는 것", ""]
    lines += [f"- {x}" for x in m["limits_ko"]]
    lines.append("")
    txt = "\n".join(lines) + "\n"
    if to_string:
        return txt
    with open(MD, "w", encoding="utf-8") as f:
        f.write(txt)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
