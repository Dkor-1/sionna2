#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""고도 사다리 판독 — 0930 B 묶음 (2026-09-14).

    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/read_altitude_0914.py

무엇을 묻나
-----------
실외 판의 바닥이 **지면 때문인가**. 0930 B 묶음이 그 축을 사려고 `--env-alt` 를 흔들었다.

⛔⛔**그런데 이 축이 무엇을 옮기는지부터 적어야 한다.** 생산 구현
`benchmark/elevation_sweep_md.py:200 env_parts` 는 드론을 올리는 것이 아니라 **환경 부품을
통째로 내린다**(`position=(0,0,dz)`, `dz = -alt`). 그리고 같은 파일 :114 가 적어 두었듯
**드론이 원점이고 레이다는 `rng·sin(el)` 깊이에 온다** — 곧 레이다도 드론에 매여 있다.
⇒ 이 축은 「드론이 높이 난다(레이다는 땅에 있다)」가 **아니다.** 「드론과 레이다가 **함께**
  지면에서 멀어진다」이다. 상대 기하 실험으로 읽는다.

⛔이 판독은 **관측만** 낸다. 「지면 탓이다/아니다」로 닫지 않는다 — 그 판정은 이 표 하나로
  설 수 없다(아래 limits_ko).

⭐왜 리듬 몫만 보면 안 되나
---------------------------
리듬 몫은 **비**다. 분자(빗살)와 분모(움직이는 몫 전체)가 **함께** 줄면 비는 안 변한다.
그래서 「리듬 몫이 널 근처라 지면 탓이 아니다」로 읽으면 안 된다 — 이 표는 비와 **절대
전력**을 같은 줄에 나란히 놓아 그 읽기를 막는다.
"""
from __future__ import annotations

import collections
import glob
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)
from arm_grammar import parse as parse_arm, unparse as unparse_arm   # noqa: E402
from reader_gate import cell, check_series, check_shards, publish, sweep_orphans  # noqa: E402

LED_J = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "read_altitude_0914.json")
MD = os.path.join(ROOT, "docs", "ALTITUDE_0914.md")

#: 이 판독이 요구하는 팔의 꼴. ⛔꼬리표 **허용목록**으로 고른다 — 블록리스트는 샌다.
BASE_TAGS = {"engine", "spp", "switches", "range_m", "n_poses",
             "max_depth", "env", "env_alt", "mesh_fix", "blade_law"}
WANT = (("engine", "sionna", "엔진"), ("spp", "4000000000", "광선 예산"),
        ("range_m", "15", "거리[m]"), ("n_poses", "8192", "자세 수"),
        ("max_depth", "2", "반사 깊이"))
#: 기준 고도 — `env_parts` 가 항목의 기본값으로 쓰는 값(ENV_SPECS["outdoor01"]["alt_m"]).
#  ⛔손으로 친 수가 아니라 생산 파일에서 읽는다(아래 `_default_alt`).
#: ⛔⛔2026-09-14(2) 정정 — 바로 위 주석이 「손으로 치지 않는다」인데 그 아래가 손으로 친
#  `RANGE_M = 15.0` 이었다. 게다가 생산 기본값은 10 m 다(elevation_sweep_md.py 의 --range-m).
#  ⇒ **원장 행의 `range_m` 을 쓴다.** 쌍마다 다를 수 있으므로 칸에서 읽는다.


def gen_note(row) -> dict | None:
    """그 칸이 **두 세대였나** — 발간 행에 실을 한 줄 요약(아니면 None).

    ⛔⛔2026-09-14(2) 신설. 공통 관문이 세대를 「고른 **뒤** 갈린 자세가 남았나」로 판정하게
      완화했는데(그건 옳다 — 깨끗이 풀린 칸까지 버리면 안 된다), 그 바람에 **고르기 전에는
      크게 갈렸다는 사실**이 발간물 어디에도 안 남았다.
    ⛔실측(2026-09-14): 원장의 두 세대 칸 4 개는 고른 뒤 갈린 자세가 0 이지만, 고르기 **전**
      에는 자세 3,057~3,981 / 8,192(37~49 %)가 다르고 최대 상대차가 0.0075~0.4999 다.
      그 칸에서 나온 발간 행 6 개에 그 사실을 적은 열이 하나도 없었다.
    ⇒ 관문은 그대로 통과시키되(값은 한 세대로 풀렸다) **행이 스스로 말하게** 한다.
    """
    m = (row or {}).get("mixed_generations")
    if not isinstance(m, dict):
        return None
    return {"n_generations": m.get("n_generations"),
            "selected_by": m.get("selected_by"),
            "kept_conflicting_poses": m.get("kept_conflicting_poses"),
            "n_poses_differing_before_pick": m.get("n_poses_differing"),
            "rel_diff_max_before_pick": m.get("rel_diff_max"),
            "note_ko": ("이 칸에는 굽기 세대가 둘이었고 하나를 골랐다. 고른 뒤 갈린 자세는 "
                        f"{m.get('kept_conflicting_poses')} 개지만, 고르기 **전**에는 "
                        f"{m.get('n_poses_differing')} 자세가 달랐다(최대 상대차 "
                        f"{m.get('rel_diff_max')}). ⛔두 세대를 가로지르는 비교에 쓰지 않는다.")}


def _default_alt() -> float:
    """생산 파일이 쓰는 기본 고도 [m] — 손으로 치지 않고 읽어 온다."""
    import ast
    src = open(os.path.join(HERE, "elevation_sweep_md.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and node.targets
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "ENV_SPECS"):
            for k, v in zip(node.value.keys, node.value.values):
                if getattr(k, "value", None) != "outdoor01":
                    continue
                for kw in getattr(v, "keywords", []):
                    if kw.arg == "alt_m":
                        return float(ast.literal_eval(kw.value))
    raise SystemExit("⛔ elevation_sweep_md.py 에서 기본 고도(ENV_SPECS.outdoor01.alt_m)를 못 읽었다")


def cell_series(arm: str, el: float, n_poses_ledger=None):
    """한 칸의 복소 시계열 — (전계, 표집률) 또는 (None, 까닭)."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+g}_*.npz"))
    if not fs:
        return None, "그 칸의 조각이 창고에 없다"
    n0, prf, why = check_shards(fs)
    if why:
        return None, " · ".join(why)
    E = np.zeros(n0, complex)
    seen = np.zeros(n0, bool)
    for f in fs:
        z = np.load(f)
        ii = z["idx"].astype(int)
        E[ii] = z["E"]
        seen[ii] = True
    if not seen.all():
        return None, f"자세가 덜 찼다({int(seen.sum())}/{seen.size})"
    w = check_series(E, n_poses=n_poses_ledger, prf=prf)
    if w:
        return None, " · ".join(w)
    return (E, prf), None


def lag_corr(E: np.ndarray, k: int = 1):
    """움직이는 몫의 **정규화된 복소 지연 상관** — (실수부, 크기) 를 돌려준다.

    ⛔⛔2026-09-14(4) 정정 — 옛 판은 **실수부만** 돌려주고 그것으로 「자세를 따라 흐르는
      신호가 아니다」라고 결론지었다. 그 결론은 이 통계에서 안 나온다:
        · 주기 4 표본의 **결정적** 신호 exp(2πi·n/4) 는 실수부가 **0** 인데 복소 크기는
          **1.0** 이다(실측 재현). 곧 실수부가 0 이라고 «신호가 없다» 가 아니다.
      ⇒ **크기도 함께** 내고, 결론은 «실외와 빈 하늘의 상관 구조가 다르다» 까지로 낮춘다.
    ⭐지연을 둘 본다 — 이웃 자세(k=1)와 **날개 박자 한 주기**(k ≈ prf/f_flash).
      로터 위상에 반응하는 전계는 둘 다에서 상관이 서야 한다.
    ⚠이것으로 «잡음의 종류» 를 판정하지 않는다 — 그건 다른 대조의 몫이다.
    """
    x = np.asarray(E) - np.asarray(E).mean()
    if x.size < k + 2 or k < 1:
        return None, None
    a, b = x[:-k], x[k:]
    da = float(np.real(np.vdot(a, a))); db = float(np.real(np.vdot(b, b)))
    if da <= 0 or db <= 0:
        return None, None
    c = np.vdot(a, b) / math.sqrt(da * db)
    return round(float(c.real), 4), round(float(abs(c)), 4)


def lag1_corr(E: np.ndarray):
    """뒤에 쓰던 이름 — 실수부만 돌려준다(표는 크기도 함께 싣는다)."""
    return lag_corr(E, 1)[0]


def parts(E: np.ndarray) -> dict:
    """정지 성분과 움직이는 성분. ⭐둘을 갈라야 «바닥이 지면인가» 를 물을 수 있다."""
    dc = float(np.abs(E.mean()) ** 2)
    ac = float(np.mean(np.abs(E - E.mean()) ** 2))
    return {"dc_power": dc, "ac_power": ac, "mean_abs": float(np.abs(E).mean())}


def rhythm_share_pct(E: np.ndarray, prf: float, f_flash: float, f_tip: float,
                     half_hz: float = 8.0):
    """움직이는 몫 가운데 **날개 박자 빗살**이 차지하는 비 [%].

    ⛔정의는 `benchmark/build_deck_maps.py:structure_bars` 의 창 반폭 8 Hz 를 따른다 —
      이 저장소가 이미 쓰던 정의이고 새로 만들지 않는다.
    ⛔날개끝 상한이 0 인 칸(직하방)은 «상한 위» 띠가 없으므로 None 을 돌려준다.
    """
    if not (f_tip and f_tip > 0) or not (f_flash and f_flash > 0):
        return None
    x = E - E.mean()
    n = x.size
    w = np.hanning(n)
    P = np.abs(np.fft.fft(x * w)) ** 2 / (n * np.sum(w ** 2))
    fr = np.fft.fftfreq(n, 1.0 / prf)
    above = np.abs(fr) >= f_tip
    k = np.round(np.abs(fr) / f_flash)
    on = np.abs(np.abs(fr) - k * f_flash) <= half_hz
    tot = float(P[above].sum())
    if tot <= 0:
        return None
    return round(100.0 * float(P[above & on].sum()) / tot, 2)


def db_ratio(a: float, b: float):
    return None if (a <= 0 or b <= 0) else round(float(10 * np.log10(a / b)), 3)


def main() -> int:
    #: ⭐죽은 프로세스의 임시 파일만 지운다 — 살아 있는 남의 발간은 안 건드린다.
    _orph = sweep_orphans([os.path.dirname(OUT), os.path.dirname(MD)])
    L = json.load(open(LED_J, encoding="utf-8"))
    ROW = {(r["engine"], float(r["el_deg"])): r for r in L["rows"]}
    DEFAULT_ALT = _default_alt()

    def usable(r):
        """못 쓰는 까닭 — 빈 목록이면 쓸 수 있다. ⛔버린 칸은 까닭과 함께 적는다."""
        try:
            f = parse_arm(r["engine"])
        except Exception:
            return [("이름을 못 읽음", "이름을 문법으로 못 읽었다")]
        why = []
        extra = sorted(set(f) - BASE_TAGS)
        if extra:
            why.append(("허용 밖 꼬리표", "이 판독이 허용하지 않는 꼬리표가 붙어 있다: "
                        + " · ".join(extra)))
        for k, v, ko in WANT:
            if f.get(k) != v:
                why.append((f"{ko} 다름",
                            f"{ko}이(가) 이 판독의 값과 다르다(팔 {f.get(k)!r} · 이 판독 {v!r})"))
        if r.get("n_missing") != 0:
            why.append(("자세 덜 참", f"자세가 덜 찼다(빠진 자세 {r.get('n_missing')})"))
        return why

    rows, skipped = [], []
    n_no_alt = 0
    for r in sorted(L["rows"], key=lambda r: (r["engine"], r["el_deg"])):
        #: ⛔⛔2026-09-14(2) 정정 — 옛 판은 이름을 못 읽으면 `f = {}` 로 두고 그 행을
        #  «고도 꼬리표 없음(범위 밖)» 으로 셌다. 그러면 **버린 칸이 소리 없이 범위 밖에
        #  섞인다** — 아래 `usable()` 의 «이름을 못 읽음» 사유는 닿지 않는 죽은 가지였다.
        try:
            f = parse_arm(r["engine"])
        except Exception as e:                 # noqa: BLE001
            skipped.append(dict(engine=r["engine"], el_deg=float(r["el_deg"]),
                                why_codes=["이름을 못 읽음"],
                                why=f"이름을 문법으로 못 읽었다({type(e).__name__})"))
            continue
        if not f.get("env_alt"):
            n_no_alt += 1                      # 고도 꼬리표가 없는 팔 = 이 축의 범위 밖
            continue
        el = float(r["el_deg"])
        w = usable(r)
        if w:
            skipped.append(dict(engine=r["engine"], el_deg=el,
                                why_codes=[c for c, _ in w],
                                why=" · ".join(t for _, t in w)))
            continue
        #: ⭐짝은 **고도 꼬리표만 뺀 같은 팔**이다 — 이름을 긁지 않고 문법으로 짓는다.
        base_arm = unparse_arm({k: v for k, v in f.items() if k != "env_alt"})
        rb = ROW.get((base_arm, el))
        if rb is None:
            skipped.append(dict(engine=r["engine"], el_deg=el, want=base_arm,
                                why_codes=["기준 고도 짝 없음"],
                                why="고도 꼬리표만 뺀 기준 팔이 원장에 없다"))
            continue
        #: ⭐쌍의 조건을 **다시** 검사한다 — 이름이 맞아도 원장 값이 어긋나면 안 쓴다.
        bad = [k for k in ("n_poses", "spp", "fc_hz", "f_tip_hz", "range_m",
                           "max_depth", "prf_hz", "f_flash_hz")
               if r.get(k) != rb.get(k)]
        #: ⛔⛔2026-09-14(4) — **도장을 적는 것과 비교에서 혼합을 막는 것은 다른 일이다.**
        #  서로 다른 솔버 판으로 구운 두 칸이 쌍이 되면 그 차는 고도가 아니라 판 갈이다.
        #  ⚠지금 원장 2,408 행은 이 필드를 아직 안 들고 있다(샤드 7,720 중 7,704 장이
        #    도장 전 세대다). 그래서 지금은 «둘 다 없음» 으로 통과한다 — 그것도 적는다.
        #  ⛔없는 판을 설치본에서 역산하지 않는다(출처를 만들어 내게 된다).
        _ba, _bb = r.get("solver_build"), rb.get("solver_build")
        _sa, _sb = r.get("solver_build_seen"), rb.get("solver_build_seen")
        if _sa or _sb:
            bad.append("solver_build_seen(한 칸에 판이 여럿)")
        elif _ba != _bb:
            bad.append(f"solver_build({_ba} ↔ {_bb})")
        if bad:
            skipped.append(dict(engine=r["engine"], el_deg=el, want=base_arm,
                                why_codes=["쌍의 조건 어긋남"],
                                why=f"쌍의 조건이 어긋난다: {bad}"))
            continue
        got_a, why_a = cell_series(r["engine"], el, r.get("n_poses"))
        got_b, why_b = cell_series(base_arm, el, rb.get("n_poses"))
        #: ⭐⭐**빈 하늘 팔**(환경 꼬리표를 전부 뺀 같은 팔) — «움직임» 열이 물리인지 가르는
        #  유일한 대조다. 기준 고도 팔은 **같은 실외 장면**이라 대조가 안 된다(둘 다 ≈0).
        #  ⛔이 줄이 없을 때 나는 「빈 하늘 팔은 …」이라 적고 실제로는 기준 고도 팔의 수를
        #  실었다(2026-09-14(2) 정정). 없으면 None 이고 문장도 그 사실을 적는다.
        free_arm = unparse_arm({k: v for k, v in f.items()
                                if k not in ("env", "env_alt")})
        rf = ROW.get((free_arm, el))
        got_f, _why_f = (cell_series(free_arm, el, rf.get("n_poses"))
                         if rf is not None else (None, "빈 하늘 짝이 원장에 없다"))
        if got_a is None or got_b is None:
            skipped.append(dict(engine=r["engine"], el_deg=el, want=base_arm,
                                why_codes=["시계열을 못 읽음"],
                                why=" · ".join(x for x in (why_a, why_b) if x)))
            continue
        Ea, prf = got_a
        Eb, prf_b = got_b
        #: ⛔⛔2026-09-14(4) — 쌍의 조건 검사(:위)는 **원장끼리만** 봤다. 그래서 원장 값은
        #  같은데 **샤드의 저장 표집률**만 다른 쌍이 그대로 통과했다. 실측 반례: 기준 샤드의
        #  표집률만 10,000 Hz 로 바꾸면 기준 시계열의 올바른 리듬 몫 0.00 % 가 높은 고도
        #  쪽 표집률로 계산돼 **99.99 %** 로 발간됐다(양쪽이 원장과 함께 어긋나도 통과).
        #  ⇒ ⓐ 각 시계열의 **저장** 표집률을 그 칸의 **원장** 값과 대조하고
        #    ⓑ 쌍의 두 저장 표집률이 서로 같은지도 본다. 빈 하늘 대조도 같은 계약이다.
        _pw = []
        for _nm, _row, _p in (("고도 팔", r, prf), ("기준 고도 팔", rb, prf_b),
                              ("빈 하늘 팔", rf, (got_f[1] if got_f else None))):
            if _p is None or _row is None:
                continue
            _lp = _row.get("prf_hz")
            if _lp is not None and abs(float(_lp) - float(_p)) > 1.0:
                _pw.append(f"{_nm}의 저장 표집률이 원장과 다르다(샤드 {_p} · 원장 {_lp})")
        if prf_b is not None and abs(float(prf) - float(prf_b)) > 1.0:
            _pw.append(f"쌍의 저장 표집률이 서로 다르다(고도 {prf} · 기준 {prf_b})")
        if got_f is not None and abs(float(prf) - float(got_f[1])) > 1.0:
            _pw.append(f"빈 하늘 대조의 저장 표집률이 다르다(고도 {prf} · 빈 하늘 {got_f[1]})")
        if _pw:
            skipped.append(dict(engine=r["engine"], el_deg=el, want=base_arm,
                                why_codes=["저장 표집률 어긋남"], why=" · ".join(_pw)))
            continue
        pa, pb = parts(Ea), parts(Eb)
        alt = float(f["env_alt"])
        ftip = float(r.get("f_tip_hz") or 0.0)
        ffl = float(r.get("f_flash_hz") or 0.0)
        #: ⭐날개 박자 한 주기가 몇 자세인가 — 자세 번호가 곧 날개 각도다.
        k_blade = int(round(prf / ffl)) if (ffl and prf and ffl > 0) else 0
        #: ⭐레이다가 지면 위로 뜬 높이 — 드론이 원점이고 레이다는 rng·sin(el) 깊이다.
        rng_m = float(r.get("range_m") or 0.0)
        h_new = alt - rng_m * abs(math.sin(math.radians(el)))
        h_ref = DEFAULT_ALT - rng_m * abs(math.sin(math.radians(el)))
        pred = (None if (h_new <= 0 or h_ref <= 0)
                else round(float(-20 * math.log10(h_new / h_ref)), 3))
        d_dc = db_ratio(pa["dc_power"], pb["dc_power"])
        rows.append(dict(
            mixed_generations=gen_note(r), base_mixed_generations=gen_note(rb),
            engine=r["engine"], base_engine=base_arm, env=f.get("env"),
            el_deg=el, alt_m=alt, base_alt_m=DEFAULT_ALT, range_m=rng_m,
            radar_height_m=round(h_new, 3), base_radar_height_m=round(h_ref, 3),
            prf_hz=prf, f_tip_hz=ftip, f_flash_hz=ffl,
            d_mean_abs_db=(None if (pa["mean_abs"] <= 0 or pb["mean_abs"] <= 0) else
                           round(float(20 * np.log10(pa["mean_abs"] / pb["mean_abs"])), 3)),
            d_dc_power_db=d_dc,
            d_ac_power_db=db_ratio(pa["ac_power"], pb["ac_power"]),
            inverse_square_pred_db=pred,
            d_dc_minus_pred_db=(None if (d_dc is None or pred is None)
                                else round(d_dc - pred, 3)),
            rhythm_share_pct=rhythm_share_pct(Ea, prf, ffl, ftip),
            base_rhythm_share_pct=rhythm_share_pct(Eb, prf, ffl, ftip),
            #: ⭐«움직임» 열의 상관 구조 — 실수부·크기를 **두 지연**에서 본다(lag_corr 머리말).
            #  k=1 은 이웃 자세, k_blade 는 날개 박자 한 주기다.
            lag1_corr=lag_corr(Ea, 1)[0], lag1_abs=lag_corr(Ea, 1)[1],
            base_lag1_corr=lag_corr(Eb, 1)[0], base_lag1_abs=lag_corr(Eb, 1)[1],
            blade_lag=k_blade,
            blade_lag_abs=(lag_corr(Ea, k_blade)[1] if k_blade else None),
            base_blade_lag_abs=(lag_corr(Eb, k_blade)[1] if k_blade else None),
            #: ⭐이 쌍이 어느 솔버 판으로 구워졌나 — 없으면 «도장 전 세대» 다.
            solver_build=(r.get("solver_build") or "(도장 전 세대)"),
            base_solver_build=(rb.get("solver_build") or "(도장 전 세대)"),
            free_engine=(free_arm if rf is not None else None),
            free_lag1_corr=(lag_corr(got_f[0], 1)[0] if got_f is not None else None),
            free_lag1_abs=(lag_corr(got_f[0], 1)[1] if got_f is not None else None),
            free_blade_lag_abs=((lag_corr(got_f[0], k_blade)[1])
                                if (got_f is not None and k_blade) else None),
            #: ⭐리듬 몫의 **기하 바닥** 2·hw/f_flash — 실린 값이 이 바닥 근처면 아무것도 안 잰다.
            rhythm_floor_pct=(None if not ffl else round(200.0 * 8.0 / ffl, 2)),
        ))

    n_pairs = len(rows)
    dd = [r["d_dc_minus_pred_db"] for r in rows if r["d_dc_minus_pred_db"] is not None]
    #: ⛔⛔2026-09-14(2) 정정 — 옛 판은 `abs()` 로 부호를 지우고 「내려간다」로 적었다.
    #  그런데 고도를 20 → 10 m 로 **내린** 쌍은 +14.003 dB **올라간다.** 발간 문장이 제
    #  표와 어긋났다. ⇒ 부호를 그대로 쓴다.
    d_dcs = [r["d_dc_power_db"] for r in rows if r["d_dc_power_db"] is not None]
    #: ⭐⭐**크기로 센다**(2026-09-14(4) 정정) — 실수부만 보면 주기 4 표본의 결정적 신호도
    #  0 이 나온다(복소 크기는 1.0). 실자료에서는 위상이 작아 둘이 거의 같지만, 그건
    #  **자료의 성질**이지 자의 성질이 아니다.
    corr = ([r["lag1_abs"] for r in rows if r.get("lag1_abs") is not None]
            + [r["base_lag1_abs"] for r in rows if r.get("base_lag1_abs") is not None])
    #: ⭐대조는 **빈 하늘 팔**이다(같은 실외 장면의 기준 고도 팔이 아니다).
    fcorr = [r["free_lag1_abs"] for r in rows if r.get("free_lag1_abs") is not None]
    bl = [r["blade_lag_abs"] for r in rows if r.get("blade_lag_abs") is not None]
    fbl = [r["free_blade_lag_abs"] for r in rows if r.get("free_blade_lag_abs") is not None]

    out = dict(_meta=dict(
        generator="benchmark/read_altitude_0914.py",
        reads=["outputs/elevation_sweep_md.json", "outputs/elev_sweep_shards/*.npz",
               "benchmark/elevation_sweep_md.py (기본 고도)"],
        question_ko="실외 판의 바닥이 지면에서 오나 — 고도를 흔들었을 때 정지·움직이는 성분이 "
                    "어떻게 가나",
        axis_ko=(f"`--env-alt` 는 드론을 올리는 것이 아니라 **환경 부품을 통째로 내린다**"
                 f"(elevation_sweep_md.py:200 `env_parts`, position z = -alt). 드론이 원점이고 "
                 f"레이다는 rng·sin(el) 깊이에 매여 있으므로(같은 파일 :114) 드론과 레이다가 "
                 f"**함께** 지면에서 멀어진다. 기준 고도는 {DEFAULT_ALT:g} m 다(거리는 칸마다 원장에서 읽는다)."),
        default_alt_m=DEFAULT_ALT,
        range_m_seen=sorted({float(x["range_m"]) for x in rows}) if rows else [],
        n_ledger_rows=len(L["rows"]),
        n_out_of_scope_no_alt_tag=n_no_alt,
        n_pairs=n_pairs, n_skipped=len(skipped),
        accounting_closes=(len(L["rows"]) == n_no_alt + n_pairs + len(skipped)),
        skipped_by_reason={k: v for k, v in sorted(
            collections.Counter(c for x in skipped for c in x["why_codes"]).items(),
            key=lambda kv: -kv[1])},
        ruler_ko=("정지 성분 = |평균 E|² · 움직이는 성분 = 평균 |E − 평균 E|² · "
                  "이웃/날개주기 «상관» 은 **정규화된 복소 상관의 크기**다(실수부도 행에 "
                  "함께 싣는다). ⭐리듬 몫의 **분모는 움직이는 몫 전체가 아니라 «날개끝 상한 "
                  "f_tip 위» 전력**이다 — 조건이 걸린 비다. 정의는 "
                  "`benchmark/build_deck_maps.py:structure_bars` 의 창 반폭 8 Hz 를 그대로 "
                  "쓴다(새로 만들지 않았다)."),
        inverse_square_ko=("«1/h² 예측» 은 레이다↔지면 높이가 h_ref → h_new 로 바뀔 때 "
                           "−20·log10(h_new/h_ref) 다. ⛔이것은 **기하 예측과의 일치를 재는 "
                           "자**이지 기작의 증명이 아니다 — 레이다↔지면 거리에 반비례하는 "
                           "어떤 법칙이든 같은 수를 낸다."),
        limits_ko=[
            "⛔이 축은 「드론이 높이 난다」가 아니다 — 드론과 레이다가 함께 멀어진다. "
            "레이다가 땅에 남는 실제 비행 기하는 이 자료에 없다.",
            "⛔「바닥이 지면 탓이다/아니다」로 닫지 않는다. 이 표가 보이는 것은 고도를 "
            "흔들었을 때 두 성분이 **어떻게 가는가** 뿐이다.",
            "⛔⛔리듬 몫은 **비**다. 분자와 분모가 함께 줄면 비는 안 변한다 — 「리듬 몫이 "
            "널 근처라 지면 탓이 아니다」로 읽지 않는다. 이 표가 비와 절대 전력을 같은 줄에 "
            "두는 까닭이 그것이다.",
            "⛔⛔«움직이는 몫» 열의 상관은 빈 하늘 팔과 크게 다르다(표의 두 «상관» 칸 — "
            "이웃 자세와 날개 박자 한 주기, 둘 다 **복소 상관의 크기**다). ⛔그 차이에서 "
            "「날개 신호가 없다」로 넘어가지 않는다 — 상관 통계는 신호의 유무를 못 가른다"
            "(주기 4 표본의 결정적 신호도 실수부가 0 이다). 말할 수 있는 것은 «구조가 "
            "다르다» 까지다.",
            "⛔리듬 몫 크기는 인용 대상이 아니다(RETRACTION_LOG R29) — 창 반폭 hw 가 그 수를 "
            "지배한다. 표에 기하 바닥을 함께 적어 두었다.",
            "⛔쌍의 조건 검사는 원장 값 여덟 개만 본다 — **굽기 세대**는 아직 안 본다. 실측: "
            "아홉 쌍 전부 기준 팔과 고도 팔의 샤드 세대가 다르다(기준 팔에는 run_id·n_trunc 가 "
            "없다). 잔차가 세대가 아니라 앙각을 따라가므로 수치가 그 때문에 틀렸다는 증거는 "
            "없지만, 열린 구멍이다.",
            "⛔실기 계측 대조는 0 건이다. 이 판독으로도 생기지 않는다.",
        ]), rows=rows, skipped=skipped)

    #: ⛔⛔머리기사에서 **리듬 몫 크기를 뺐다**(2026-09-14(2) 정정). RETRACTION_LOG R29 가
    #  그 퍼센티지는 자료의 성질이 아니라 **우리가 고른 창 반폭의 성질**이라고 철회해 둔
    #  수다. 실린 값 11.6~13.1 % 는 hw = 8 Hz 의 기하 바닥 2·hw/f_flash ≈ 12.6 % 바로 위라
    #  아무것도 안 재고 있다. 표에는 바닥과 함께 남겨 읽는 이가 보게 두고, 머리기사에서는 뺀다.
    if dd:
        out["_meta"]["headline_ko"] = (
            f"고도 쌍 {n_pairs} 개에서 정지 성분이 {min(d_dcs):+.2f}~{max(d_dcs):+.2f} dB "
            f"움직이고, 그 값이 레이다↔지면 높이의 1/h² 예측과 "
            f"{min(dd):+.2f}~{max(dd):+.2f} dB 안에서 맞는다"
            + (f". ⛔같은 칸의 «움직이는 몫» 은 정규화된 복소 이웃 상관의 **크기**가 "
               f"{min(corr):.4f}~{max(corr):.4f} 인데, 환경 꼬리표만 뺀 **빈 하늘 팔**은 "
               f"{min(fcorr):.4f}~{max(fcorr):.4f} 다 — 두 자료의 상관 구조가 다르다. "
               "⛔여기서 말할 수 있는 것은 그 차이까지다(신호의 유무나 잡음의 종류는 "
               "이 통계가 못 가른다)."
               if corr and fcorr else
               (f". ⛔같은 칸의 «움직이는 몫» 은 이웃 자세 상관이 "
                f"{min(corr):.4f}~{max(corr):.4f} 로 자세를 따라 흐르지 않는다 "
                "(빈 하늘 대조 팔이 원장에 없어 견줄 짝이 없다)." if corr else ".")))
    else:
        out["_meta"]["headline_ko"] = f"고도 쌍 {n_pairs} 개 — 견줄 수 있는 값이 없다"

    #: ── 문서 ────────────────────────────────────────────────────────────
    a = []
    a.append("# 고도 사다리 — 0930 B 묶음 판독")
    a.append("")
    a.append(f"> ⛔손으로 쓰지 않는다. `{out['_meta']['generator']}` 가 굽는다.")
    a.append("")
    a.append(f"⭐{out['_meta']['headline_ko']}")
    a.append("")
    a.append(f"⚠**이 축이 무엇을 옮기나** — {out['_meta']['axis_ko']}")
    a.append("")
    a.append("| 장면 | 앙각 | 고도 m | 레이다 높이 m | 정지 dB | 1/h² 예측 dB | 차 dB "
             "| 움직임 dB | 이웃 상관 크기 기준→새 | 날개주기 지연 크기 기준→새 "
             "| 리듬 몫 기준→새 % (바닥) |")
    a.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["env"], r["el_deg"], r["alt_m"])):
        a.append(
            f"| {r['env']} | {cell(r['el_deg'], '+.0f')} | {cell(r['alt_m'], 'g')} "
            f"| {cell(r['radar_height_m'], '.2f')} | {cell(r['d_dc_power_db'], '+.3f', ' dB')} "
            f"| {cell(r['inverse_square_pred_db'], '+.3f', ' dB')} "
            f"| {cell(r['d_dc_minus_pred_db'], '+.3f', ' dB')} "
            f"| {cell(r['d_ac_power_db'], '+.3f', ' dB')} "
            f"| {cell(r['base_lag1_abs'], '.4f')} → {cell(r['lag1_abs'], '.4f')} "
            f"| {cell(r['base_blade_lag_abs'], '.4f')} → {cell(r['blade_lag_abs'], '.4f')} "
            f"| {cell(r['base_rhythm_share_pct'], '.2f')} → {cell(r['rhythm_share_pct'], '.2f')} "
            f"({cell(r['rhythm_floor_pct'], '.1f')}) |")
    a.append("")
    a.append("⭐**«움직임» 열의 상관 구조가 빈 하늘과 다르다.** 정규화된 복소 상관의 "
             "**크기**로 재면 — 이웃 자세(k = 1)에서 "
             + (f"{min(corr):.4f}~{max(corr):.4f}" if corr else "—")
             + ", 날개 박자 한 주기 지연"
             + (f"(k = {rows[0]['blade_lag']} 자세)" if rows and rows[0].get("blade_lag") else "")
             + "에서 "
             + (f"{min(bl):.4f}~{max(bl):.4f}" if bl else "—")
             + " 다. **환경 꼬리표만 뺀 빈 하늘 팔**은 같은 자로 "
             + (f"{min(fcorr):.4f}~{max(fcorr):.4f}(k=1) · {min(fbl):.4f}~{max(fbl):.4f}"
                f"(k={rows[0]['blade_lag']})" if fcorr and fbl and rows else "(원장에 없다)")
             + " 다.")
    a.append("")
    a.append("⛔⛔**그 차이에서 «날개 신호가 없다» 로 넘어가지 않는다**(2026-09-14(4) 정정). "
             "이 자는 상관의 **실수부·크기**일 뿐이다 — 주기 4 표본의 **결정적** 신호도 "
             "실수부가 0 이 나온다(복소 크기는 1.0). 실자료에서는 위상이 작아 실수부와 크기가 "
             "거의 같지만, 그건 **자료의 성질**이지 자의 성질이 아니다. ⛔이 판독이 말할 수 "
             "있는 것은 **두 자료의 상관 구조가 다르다**까지이고, 신호의 유무나 잡음의 종류는 "
             "다른 대조의 몫이다. ⚠기준 고도 팔은 **같은 실외 장면**이라 대조가 안 된다.")
    a.append("")
    a.append("⛔⛔**리듬 몫 크기를 인용하지 않는다**(RETRACTION_LOG R29). 그 퍼센티지는 자료의 "
             "성질이 아니라 우리가 고른 창 반폭 hw = 8 Hz 의 성질이다 — 표의 괄호 안 «바닥» 이 "
             "기하 바닥 2·hw/f_flash 이고, 실린 값이 그 바닥 근처면 아무것도 안 재고 있다는 "
             "뜻이다. 이 열은 «비만 보면 절대 변화가 안 보인다» 를 눈으로 보이려고 남긴 것이지 "
             "측정값으로 인용하라고 둔 것이 아니다.")
    a.append("")
    for t in out["_meta"]["limits_ko"]:
        a.append(f"- {t}")
    a.append("")
    a.append(f"셈: 원장 {out['_meta']['n_ledger_rows']} 행 = 고도 꼬리표 없음 "
             f"{out['_meta']['n_out_of_scope_no_alt_tag']} + 쌍 {n_pairs} + 건너뜀 "
             f"{len(skipped)} — 닫힘 {out['_meta']['accounting_closes']}")
    if out["_meta"]["skipped_by_reason"]:
        a.append("")
        a.append("| 건너뛴 까닭 | 칸 |")
        a.append("|---|---:|")
        for k, v in out["_meta"]["skipped_by_reason"].items():
            a.append(f"| {k} | {v} |")
    a.append("")
    a.append(f"자: {out['_meta']['ruler_ko']}")
    a.append("")
    a.append(f"1/h² 예측: {out['_meta']['inverse_square_ko']}")
    a.append("")

    publish({OUT: out, MD: "\n".join(a) + "\n"})
    print(f"\n✅ {os.path.relpath(OUT, ROOT)} · {os.path.relpath(MD, ROOT)}  ({n_pairs} 쌍)")
    print(f"   {out['_meta']['headline_ko']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
