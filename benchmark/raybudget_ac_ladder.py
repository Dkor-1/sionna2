# -*- coding: utf-8 -*-
"""
raybudget_ac_ladder.py — **R17 · 광선 예산 사다리를 AC 로 다시 읽는다**
================================================================================

묻는 것
--------------------------------------------------------------------------------
«광선을 더 부으면 마이크로도플러 **구조** 가 생기나, 아니면 **바닥만** 내려가나.»

지금까지 「40 억 발에서 수렴했다」의 근거는 **정지 성분(DC)** 이었다. 정지 성분은 시계열의
평균이고, 마이크로도플러는 그 평균을 뺀 **요동(AC)** 에만 산다. 그러니 DC 가 모였다는 말은
마이크로도플러가 수렴했다는 뜻이 아니다. 이 파일은 같은 원장을 **AC 절대 전력**으로 다시 읽는다.

사전 등록 판정 (docs/NEXT_EXPERIMENTS.md 표 순위 1 · §3-1 «R17»)
--------------------------------------------------------------------------------
계단마다 절대 전력 세 열을 낸다.

  ① DC 제거 AC 전력          = 10log10 mean|E − mean(E)|²          (전 대역)
  ② 상한(f_tip) 위 **바닥**   = 빗살 이빨 **밖** 빈의 중앙값 전력
  ③ 상한 위 **빗살 선** 전력  = 박자 f_flash 정수배 ±8 Hz 빈의 전력 합

  판정 ① 바닥이 1/spp 를 따라가나 — 예산 4 배마다 **−6 dB**(= −3.01 dB/옥타브)인가?
  판정 ② 빗살 선은 spp 에 **불변**인가 — 기울기 0 인가?
  ①성립 · ②불변 이면 「구조 없음」이 아니라 **「이 예산의 몬테카를로 바닥 위로는 구조가
  없다」** 로 문장을 고친다.

  ⭐기울기는 눈대중이 아니라 **회귀**로 재고 95 % 신뢰구간을 붙인다(dB / spp 옥타브).
    MC 잡음이면 −3.01 dB/옥타브(= 전력 ∝ spp^−1), 불변이면 0.

⚠ 판정 기준은 설계서 그대로 쓴다. 바꾼 곳이 있으면 JSON `_prereg.deviations` 에 이유를 남긴다.

무엇을 읽나 (⛔ GPU 0 · `sionna.rt`·`mitsuba` 임포트 안 함 · 원장은 읽기만)
--------------------------------------------------------------------------------
  outputs/elevation_sweep_md.npz / .json     앙각 원장 — **사다리 A**(10 m · 자세 4096 · 깊이 1)
  outputs/raybudget_ladder/spp*_s*_*.npz     40 m 예산 사다리 — **사다리 B**(8 계단 × 시드)
  outputs/report07_range40_raybudget.json    사다리 B 의 규약(PRF·f_tip·f_flash)

⚠ 두 사다리를 **절대 섞지 않는다** — 사다리 A 는 10 m 로 원거리장 경계 2D²/λ ≈ 14.08 m 의
  **안쪽**, 사다리 B 는 40 m 로 **바깥**이다. 리포트 정본인 15 m 판은 예산 축이 아예 없다
  (15 m 팔은 전부 4e9 한 계단뿐). 그 사실도 census 에 적는다.

산출물 (전부 새 파일 — 기존 파일은 하나도 안 건드린다)
--------------------------------------------------------------------------------
  outputs/raybudget_ac_ladder.json
  outputs/figures/raybudget_ac_ladder.png        ⭐ spp 축 3 열 사다리 (2 행 × 3 열)
  outputs/figures/raybudget_ac_ladder_diag.png   진단 — 빗살 몫 · 경로 수 · 기울기 숲그림

실행
    cd /workspace/sionna && PYTHONPATH=src:benchmark \\
        /workspace/.venvs/py312/bin/python benchmark/raybudget_ac_ladder.py
"""
from __future__ import annotations

import collections
import datetime as _dt
import glob
import json
import os
import re
import socket
import sys

import numpy as np
from scipy import stats

# ⛔ 자가검사 1 — 이 스크립트는 GPU 를 안 쓴다. 렌더러가 딸려 들어오면 즉시 죽는다.
for _bad in ("sionna.rt", "mitsuba", "drjit"):
    if _bad in sys.modules:
        raise SystemExit(f"⛔ {_bad} 가 임포트됐다 — 이 스크립트는 GPU 0 이어야 한다")

import matplotlib                                                        # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ELEV_NPZ = f"{ROOT}/outputs/elevation_sweep_md.npz"
ELEV_JSON = f"{ROOT}/outputs/elevation_sweep_md.json"
LAD40_DIR = f"{ROOT}/outputs/raybudget_ladder"
LAD40_JSON = f"{ROOT}/outputs/report07_range40_raybudget.json"

OUT_JSON = f"{ROOT}/outputs/raybudget_ac_ladder.json"
OUT_FIG = f"{ROOT}/outputs/figures/raybudget_ac_ladder.png"
OUT_FIG2 = f"{ROOT}/outputs/figures/raybudget_ac_ladder_diag.png"

# ─────────────────────────────────────────────────────────────────────────────
#  잣대 규약 — 저장소 표준 레시피를 **그대로** 쓴다 (손입력 문턱은 이 두 개뿐)
#    · P = |FFT((E − mean(E))·hanning)|²  … benchmark/bridge_cross_precise.py:225
#    · 빗살 반폭 ±8 Hz                     … benchmark/detection_curves.py:81 (HW_HZ)
#    · above = |fr| ≥ f_tip(el)            … benchmark/build_switch_grid_figs.py:107
#  ⭐다만 전력을 **절대량**으로 읽어야 하므로 Parseval 정규화를 붙인다
#    (benchmark/ledger_outofband_power.py:periodogram 규약) — ΣP = mean|x|².
# ─────────────────────────────────────────────────────────────────────────────
COMB_HW_HZ = 8.0            # 빗살 반폭 [Hz] — 표준 레시피
DB_PER_OCT_MC = -3.0103     # 몬테카를로 분산 바닥의 예측 기울기 (전력 ∝ 1/spp)
DB_PER_OCT_FLAT = 0.0       # 불변 예측
TINY = 1e-300


def _db(x):
    x = float(x)
    return float("-inf") if x <= 0 else float(10.0 * np.log10(x))


def _r(x, nd=2):
    if x is None:
        return None
    x = float(x)
    if not np.isfinite(x):
        return None
    return round(x, nd)


# ═══════════════════════════════════════════════════════════════════════════ #
#  ① 셀 하나의 절대 전력 세 열 (+ 진단)
# ═══════════════════════════════════════════════════════════════════════════ #
def cell_metrics(E, f_tip, prf, f_flash, comb_hw=COMB_HW_HZ):
    """복소 슬로타임 열 하나 → 절대 전력 세 열과 진단값.

    ⭐레벨 비교는 전부 **정지 성분(DC = 시계열 평균) 제거 후**다. DC 는 따로 싣는다.

    반환 dict 의 단위: 전력은 |E|² 와 같은 눈금(엔진 안에서만 비교 가능). PSD 는 /Hz.
    빗살 창이 원격자보다 좁으면(Δf > 2·hw) 창에 빈이 안 들어갈 수 있으므로 허용폭을
    `max(hw, 1.5·Δf)` 로 넓히고(bridge_cross_precise.py:244 규약) 그 사실을 남긴다.
    """
    E = np.asarray(E, complex)
    n = int(E.size)
    out = {"n": n}

    # ── 구조적 0(에코 없음) 과 «값이 있는데 요동이 없는» 판을 가른다 ──────────
    dc_c = complex(E.mean())
    x = E - dc_c
    ac_lin = float(np.mean(np.abs(x) ** 2))
    dc_lin = float(abs(dc_c) ** 2)
    out["all_zero"] = bool(np.all(E == 0))
    out["zero_frac"] = float(np.mean(np.abs(E) == 0))
    # 퇴화 = «에코가 아예 없다» 또는 «값은 있는데 자세를 바꿔도 안 움직인다»(경로 1 개 상수열)
    # 또는 «자세의 절반 넘게 경로가 안 잡힌다». 셋 다 결측 자리표시자가 아니라 물리적 공백이다.
    out["degenerate"] = bool(out["all_zero"] or ac_lin <= 0.0
                             or ac_lin < 1e-30 * max(dc_lin, TINY)
                             or out["zero_frac"] > 0.5)
    out["degenerate_reason_ko"] = (
        "에코 없음(전부 0)" if out["all_zero"] else
        "요동 0(경로 1 개 상수열)" if (ac_lin <= 0.0 or ac_lin < 1e-30 * max(dc_lin, TINY)) else
        f"자세 {out['zero_frac'] * 100:.0f} % 에서 경로 없음" if out["zero_frac"] > 0.5 else None)
    out["dc_power_db"] = _db(dc_lin)
    out["ac_power_db"] = _db(ac_lin)                       # ⭐① 열
    out["level_db_recomputed"] = _db(float(np.mean(np.abs(E))) ** 2)

    if out["degenerate"]:
        for k in ("floor_above_db", "floor_above_psd_db_per_hz", "floor_above_int_db",
                  "comb_above_db", "comb_excess_db", "comb_share_pct",
                  "comb_shift_share_pct", "comb_over_shift_db", "ac_above_tip_db",
                  "ac_below_tip_db", "blade_band_db", "ac_power_spectral_db",
                  "window_bias_db"):
            out[k] = None
        out["white_neutral_pct"] = None
        out["df_hz"] = _r(prf / n, 3)
        out["comb_tol_hz"] = None
        out["parseval_rel_err"] = None
        return out

    w = np.hanning(n)
    sw2 = float(np.sum(w ** 2))
    X = np.fft.fft(x * w)
    # Parseval 정규화 — ΣP = Σ|x·w|² / Σw² = **창 가중 평균 전력**. 창을 안 쓴 평균
    # mean|x|² 와는 신호가 기록 안에서 고르지 않을 때 조금 다르다. 두 값을 다 싣고
    # 그 차(창 편향)를 남긴다 — 사다리 안에서 그 차가 움직이면 기울기가 오염되기 때문이다.
    P = np.abs(X) ** 2 / (n * sw2)
    fr = np.fft.fftfreq(n, 1.0 / prf)
    df = float(prf / n)

    wmean = float(np.sum(np.abs(x * w) ** 2) / sw2)
    out["parseval_rel_err"] = float(abs(P.sum() - wmean) / max(wmean, TINY))
    out["ac_power_spectral_db"] = _db(float(P.sum()))
    out["window_bias_db"] = _r(_db(float(P.sum())) - _db(ac_lin), 3)

    tol = max(comb_hw, 1.5 * df)
    out["df_hz"] = _r(df, 3)
    out["comb_tol_hz"] = _r(tol, 2)
    out["comb_tol_widened"] = bool(tol > comb_hw + 1e-9)

    above = np.abs(fr) >= f_tip
    kk = np.round(np.abs(fr) / f_flash)
    on = np.abs(np.abs(fr) - kk * f_flash) <= tol            # 박자 정수배 ±tol
    on_shift = np.abs(np.abs(fr) - (kk + 0.5) * f_flash) <= tol   # 반 이빨 어긋난 널

    a_on = above & on
    a_off = above & ~on
    a_sh = above & on_shift

    n_above = int(above.sum())
    n_on = int(a_on.sum())
    p_above = float(P[above].sum())
    p_on = float(P[a_on].sum())
    p_off = float(P[a_off].sum())
    p_sh = float(P[a_sh].sum())
    floor_med = float(np.median(P[a_off])) if a_off.sum() else float("nan")

    out["n_bins_above"] = n_above
    out["n_bins_comb"] = n_on
    out["n_bins_shift"] = int(a_sh.sum())
    out["floor_above_db"] = _db(floor_med)                       # ⭐② 열 (빈당 중앙값)
    out["floor_above_psd_db_per_hz"] = _db(floor_med / df)       #    (n 이 다른 팔끼리)
    out["floor_above_int_db"] = _db(p_off)                       #    (이빨 밖 적분)
    out["comb_above_db"] = _db(p_on)                             # ⭐③ 열
    # 빗살 «선» 만: 이빨 아래 깔린 바닥 몫을 뺀 초과분. 음수면 선이 없다는 뜻.
    excess = p_on - n_on * floor_med
    out["comb_excess_db"] = _db(excess) if excess > 0 else None
    out["comb_share_pct"] = float(100.0 * p_on / p_above) if p_above > 0 else None
    out["white_neutral_pct"] = float(100.0 * n_on / n_above) if n_above else None
    out["comb_shift_share_pct"] = float(100.0 * p_sh / p_above) if p_above > 0 else None
    out["comb_over_shift_db"] = (_db(p_on / max(p_sh, TINY))
                                 if (p_sh > 0 and p_on > 0) else None)

    out["ac_above_tip_db"] = _db(p_above)
    out["ac_below_tip_db"] = _db(float(P[~above].sum()))
    band = (np.abs(fr) >= 0.35 * f_tip) & (np.abs(fr) <= f_tip)
    out["blade_band_db"] = _db(float(P[band].sum()))
    return out


# ═══════════════════════════════════════════════════════════════════════════ #
#  ② 회귀 — dB / spp 옥타브 + 95 % 신뢰구간
# ═══════════════════════════════════════════════════════════════════════════ #
def slope_db_per_octave(spp, y_db, groups=None, conf=0.95):
    """y[dB] = a(+집단 고정효과) + b·log2(spp) 를 최소제곱으로 풀고 b 와 CI 를 낸다.

    groups 가 있으면 **집단(앙각)마다 절편을 따로** 둔다 — 앙각끼리 레벨이 수십 dB
    다르므로 절편을 공유하면 기울기가 오염된다. 기울기 b 는 집단 공통 하나다.
    n − p ≤ 0 이면(자유도 없음) CI 는 None 으로 내고 기울기만 남긴다.
    """
    spp = np.asarray(spp, float)
    y = np.asarray(y_db, float)
    ok = np.isfinite(spp) & np.isfinite(y) & (spp > 0)
    spp, y = spp[ok], y[ok]
    if groups is None:
        g = np.zeros(len(y), int)
    else:
        gg = np.asarray(groups)[ok]
        uq = list(dict.fromkeys(gg.tolist()))
        g = np.array([uq.index(v) for v in gg.tolist()], int)
    n = len(y)
    if n < 3:
        return dict(n=n, slope_db_per_octave=None, ci95=None, note_ko="점이 3 개 미만")
    x = np.log2(spp)
    ng = int(g.max()) + 1
    D = np.zeros((n, ng + 1))
    D[np.arange(n), g] = 1.0
    D[:, ng] = x
    beta, *_ = np.linalg.lstsq(D, y, rcond=None)
    resid = y - D @ beta
    dof = n - np.linalg.matrix_rank(D)
    b = float(beta[-1])
    out = dict(n=int(n), n_groups=int(ng), dof=int(dof),
               slope_db_per_octave=_r(b, 3),
               slope_db_per_4x=_r(2.0 * b, 3),
               power_law_exponent=_r(b / 3.0103, 3))
    if dof <= 0:
        out.update(ci95=None, se=None, note_ko="자유도 0 — 신뢰구간 계산 불가")
        return out
    s2 = float(resid @ resid) / dof
    XtXi = np.linalg.pinv(D.T @ D)
    se = float(np.sqrt(max(s2 * XtXi[-1, -1], 0.0)))
    tcrit = float(stats.t.ppf(0.5 + conf / 2.0, dof))
    lo, hi = b - tcrit * se, b + tcrit * se
    out.update(se=_r(se, 4), ci95=[_r(lo, 3), _r(hi, 3)],
               rmse_db=_r(float(np.sqrt(s2)), 3),
               covers_mc_minus3=bool(lo <= DB_PER_OCT_MC <= hi),
               covers_flat_zero=bool(lo <= DB_PER_OCT_FLAT <= hi))
    return out


# ═══════════════════════════════════════════════════════════════════════════ #
#  ③ 원장 전수조사 — 예산 계단이 실제로 어디에 몇 개 있나
# ═══════════════════════════════════════════════════════════════════════════ #
def census(rows, npz_files):
    """`p<숫자>` 토큰과 spp 열을 전수조사해 «예산 축» 이 성립하는 자리를 찾는다."""
    tok = collections.Counter()
    for k in npz_files:
        m = re.search(r"_p(\d+)", k.split("/")[0])
        if m:
            tok[int(m.group(1))] += 1
    cfg = collections.defaultdict(set)
    for r in rows:
        if not str(r["engine"]).startswith("sionna"):
            continue
        key = (r.get("max_depth"), r.get("n_poses"), r.get("range_m"),
               bool(r.get("physics")), r.get("az_deg"), r.get("drone", "matrice4e"))
        cfg[key].add(int(r["spp"]))
    axes = []
    for key, spps in sorted(cfg.items(), key=lambda kv: -len(kv[1])):
        d, npo, rng, phy, az, drn = key
        axes.append(dict(max_depth=d, n_poses=npo, range_m=rng, physics=phy,
                         az_deg=az, n_rungs=len(spps), spp_present=sorted(spps),
                         is_budget_axis=bool(len(spps) >= 2)))
    return dict(
        p_token_counts={str(k): v for k, v in sorted(tok.items())},
        distinct_spp_in_elevation_ledger=sorted({int(r["spp"]) for r in rows
                                                 if str(r["engine"]).startswith("sionna")}),
        configurations=axes,
        note_ko="같은 (깊이·자세수·거리·물리·방위) 조합 안에서 spp 가 2 개 이상이어야 "
                "«예산 축» 이다. 표에서 보듯 앙각 원장에서 그 조건을 만족하는 자리는 "
                "물리끔 10 m·4096·깊이1 의 4 계단과 물리켬 10 m·4096·깊이3 의 2 계단뿐이다. "
                "⚠리포트 정본인 15 m 판에는 예산 축이 **없다**(전부 4e9 한 계단).")


# ═══════════════════════════════════════════════════════════════════════════ #
#  ④ 사다리 A — 앙각 원장 (10 m · 자세 4096 · 깊이 1 · 물리 끔)
# ═══════════════════════════════════════════════════════════════════════════ #
LADDER_A = [("sionna", 11_111_111), ("sionna_p250000000", 250_000_000),
            ("sionna_p1000000000", 1_000_000_000), ("sionna_p4000000000", 4_000_000_000)]
LADDER_A_PHYS = [("sionna_phys", 11_111_111), ("sionna_p250000000_phys", 250_000_000)]
BASELINE_A = "ours"


def el_key(el):
    return f"el{'+' if el == 0 else '-'}{abs(int(el))}"


def build_ladder_a(Z, J):
    prf = float(J["_meta"]["prf_hz"])
    ffl = float(J["_meta"]["f_flash_hz"])
    rows = {(r["engine"], float(r["el_deg"])): r for r in J["rows"]}

    # 어느 앙각이 4 계단 전부에 살아 있나 — 결측은 제외하고 제외 사실을 남긴다
    els_all = sorted({float(r["el_deg"]) for r in J["rows"]
                      if r["engine"] == "sionna"}, reverse=True)
    usable, excluded = [], []
    for el in els_all:
        why = []
        for eng, _ in LADDER_A:
            r = rows.get((eng, el))
            if r is None:
                why.append(f"{eng}: 팔 없음")
            elif int(r.get("n_missing") or 0) > 0:
                why.append(f"{eng}: n_missing={r['n_missing']}")
        if why:
            excluded.append(dict(el_deg=el, reasons_ko=why))
        else:
            usable.append(el)

    cells, table = {}, []
    for el in usable:
        for eng, spp in LADDER_A:
            r = rows[(eng, el)]
            m = cell_metrics(np.asarray(Z[f"{eng}/{el_key(el)}"], complex),
                             float(r["f_tip_hz"]), prf, ffl)
            m.update(arm=eng, spp=spp, el_deg=el, f_tip_hz=float(r["f_tip_hz"]),
                     npaths_median=r.get("npaths_median"),
                     n_missing=r.get("n_missing"),
                     level_db_ledger=r.get("level_db"),
                     seconds=r.get("seconds"),
                     npz_key=f"{eng}/{el_key(el)}")
            cells[f"{eng}|{el:+.0f}"] = m
            table.append(m)
    # 기준선(우리 커널) — 사다리가 아니라 «같은 자세 격자에서 구조가 어떻게 생겼나» 의 참조
    base = {}
    for el in usable:
        r = rows.get((BASELINE_A, el))
        if r is None:
            continue
        m = cell_metrics(np.asarray(Z[f"{BASELINE_A}/{el_key(el)}"], complex),
                         float(r["f_tip_hz"]), prf, ffl)
        m.update(arm=BASELINE_A, el_deg=el, f_tip_hz=float(r["f_tip_hz"]),
                 level_db_ledger=r.get("level_db"), npz_key=f"{BASELINE_A}/{el_key(el)}")
        base[f"{el:+.0f}"] = m
    return dict(prf=prf, f_flash=ffl, usable_els=usable, excluded_els=excluded,
                cells=cells, table=table, baseline_ours=base, rows=rows)


def build_ladder_a_phys(Z, J):
    """물리 켬 — ⚠예산 축이 아니다(깊이·자세가 섞였다). 설계서 §② «렌즈 갈림» 처리 그대로."""
    prf = float(J["_meta"]["prf_hz"])
    ffl = float(J["_meta"]["f_flash_hz"])
    rows = {(r["engine"], float(r["el_deg"])): r for r in J["rows"]}
    els = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]
    clean, confound = [], []
    for el in els:
        for eng, spp in LADDER_A_PHYS:
            r = rows.get((eng, el))
            if r is None or int(r.get("n_missing") or 0) > 0:
                continue
            m = cell_metrics(np.asarray(Z[f"{eng}/{el_key(el)}"], complex),
                             float(r["f_tip_hz"]), prf, ffl)
            m.update(arm=eng, spp=spp, el_deg=el, max_depth=r["max_depth"],
                     n_poses=r["n_poses"], npaths_median=r.get("npaths_median"),
                     level_db_ledger=r.get("level_db"))
            clean.append(m)
        r = rows.get(("sionna_p4000000000_phys_n8192_d1", el))
        if r is not None and int(r.get("n_missing") or 0) == 0:
            m = cell_metrics(
                np.asarray(Z[f"sionna_p4000000000_phys_n8192_d1/{el_key(el)}"], complex),
                float(r["f_tip_hz"]), prf, ffl)
            m.update(arm="sionna_p4000000000_phys_n8192_d1", spp=4_000_000_000,
                     el_deg=el, max_depth=r["max_depth"], n_poses=r["n_poses"],
                     npaths_median=r.get("npaths_median"), level_db_ledger=r.get("level_db"))
            confound.append(m)
    return dict(clean_rungs=clean, confounded_rungs=confound)


# ═══════════════════════════════════════════════════════════════════════════ #
#  ⑤ 사다리 B — 40 m 예산 사다리 (8 계단 × 시드) : 시드가 있어 **진짜** 오차막대가 나온다
# ═══════════════════════════════════════════════════════════════════════════ #
def build_ladder_b():
    if not os.path.isdir(LAD40_DIR):
        return None
    M = json.load(open(LAD40_JSON))["_meta"]
    prf = float(M["prf_hz"])
    ffl = float(M["f_flash_hz"])
    ftip = float(M["f_tip_hz"])
    cens = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in glob.glob(f"{LAD40_DIR}/spp*_s*_*.npz"):
        b = os.path.basename(f)
        cens[int(b.split("_")[0][3:])][int(b.split("_")[1][1:])].append(f)
    arms = []
    for spp in sorted(cens):
        for seed in sorted(cens[spp]):
            fs = sorted(cens[spp][seed])
            E, idx, npa, secs, nfull, nsh = [], [], [], 0.0, None, None
            for f in fs:
                z = np.load(f, allow_pickle=True)
                mt = np.asarray(z["meta"], float)
                E.append(z["E"]); idx.append(z["idx"]); npa.append(z["npaths"])
                secs += float(mt[5]); nfull = int(mt[4]); nsh = int(mt[2])
            idx = np.concatenate(idx); o = np.argsort(idx)
            Ec = np.concatenate(E)[o]; npc = np.concatenate(npa)[o].astype(float)
            complete = bool(len(fs) == nsh and len(idx) == nfull)
            m = cell_metrics(Ec, ftip, prf, ffl)
            m.update(spp=spp, seed=seed, complete=complete, n_shards=len(fs),
                     n_shards_expected=nsh, npaths_median=float(np.median(npc)),
                     npaths_zero_frac=float(np.mean(npc == 0)), seconds=round(secs, 1))
            arms.append(m)
    # ⭐계단 단위 유효성 — 시드 하나라도 퇴화면 **계단째** 뺀다. 살아남은 시드만 쓰면
    #   «에코를 찾은 판만 골라 본» 생존 편향이 생기고, 그 편향은 사다리 왼쪽을 위로
    #   끌어올려 기울기를 **가짜로 음수**로 만든다(실측: 4M 계단이 그랬다).
    valid = {}
    for spp in sorted(cens):
        comp = [m for m in arms if m["spp"] == spp and m["complete"]]
        bad = [m for m in comp if m["degenerate"]]
        valid[spp] = dict(
            n_complete=len(comp), n_degenerate=len(bad),
            usable=bool(comp and not bad),
            reason_ko=(None if (comp and not bad) else
                       ("완결 샤드 팔이 없다" if not comp else
                        "시드 " + ", ".join(f"s{m['seed']}({m['degenerate_reason_ko']})"
                                            for m in bad) + " 가 퇴화 — 계단째 제외")))
    return dict(prf=prf, f_flash=ffl, f_tip=ftip, arms=arms,
                spp_present=sorted(cens), rung_validity=valid,
                seeds_per_spp={str(s): len(cens[s]) for s in sorted(cens)})


# ═══════════════════════════════════════════════════════════════════════════ #
#  ⑥ 부수 산출 — 11.1 M 값·「수렴」 문장을 인용하는 자리 목록
# ═══════════════════════════════════════════════════════════════════════════ #
SCAN_GLOBS = ["reports/*.ipynb", "reports/_parts/*.ipynb", "reports/*.md",
              "docs/*.md", "src/*.py", "README.md"]
SCAN_PAT = [
    ("11.1M_arm", re.compile(r"11\.1\s?M|11111111")),
    ("converged_0p03dB", re.compile(r"0\.03\s?dB")),
    ("budget_360x", re.compile(r"360\s?배")),
]


def scan_citations():
    hits = []
    for g in SCAN_GLOBS:
        for path in sorted(glob.glob(os.path.join(ROOT, g))):
            try:
                txt = open(path, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            for i, line in enumerate(txt, 1):
                tags = [nm for nm, pat in SCAN_PAT if pat.search(line)]
                if not tags:
                    continue
                s = line.strip()
                if len(s) > 220:
                    s = s[:217] + "…"
                claims_conv = bool(re.search(r"수렴|모인다|모이고|안에 머문|converg", line))
                # 이미 «정지 성분/레벨/평균장» 으로 범위가 좁혀져 있으면 문장 자체는 참이다.
                scoped = bool(re.search(r"정지\s*성분|레벨|평균장|DC", line))
                ban = (None if not claims_conv else
                       ("OK_AS_WRITTEN__DC_ONLY" if scoped else "NEEDS_SCOPE_TAG"))
                hits.append(dict(file=os.path.relpath(path, ROOT), line=i, tags=tags,
                                 claims_convergence=claims_conv, reuse_ban=ban, excerpt=s))
    return hits


# ═══════════════════════════════════════════════════════════════════════════ #
#  ⑦ 그림 — ⭐집 규약: 그림 안 글자는 **전부 영어**, 겹침 금지
#     dataviz 규약: 앙각은 **순서 있는** 축이므로 범주색이 아니라 **단일 색조 순서 램프**
#     (참조 팔레트 §Sequential hue, 라이트면 250 단계보다 밝게 가지 않는다).
#     ⚠ scripts/validate_palette.js 는 이 컨테이너에 node 가 없어 **못 돌렸다** —
#       그래서 새 색을 만들지 않고 **검증된 문서값을 그대로** 썼다.
# ═══════════════════════════════════════════════════════════════════════════ #
RAMP = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]   # ordinal blue 250·400·550·700
C_B = "#eb6834"        # 사다리 B (두 번째 순서 문맥 = orange)
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
SURF = "#fcfcfb"


def _spp_label(s):
    if s >= 1e9:
        return f"{s / 1e9:g}G"
    if s >= 1e6:
        return f"{s / 1e6:.3g}M"
    return f"{s:g}"


def _panel(ax, title):
    ax.set_facecolor(SURF)
    ax.set_title(title, fontsize=10.5, color=INK, pad=7)
    ax.grid(True, which="major", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelsize=9)


def _guides(ax, x0, y0, xs, label=False):
    """물리 진리선 — 중성 회색 파선. 1/spp(−3.01 dB/oct) 와 불변(0).

    기준점 y0 은 계열들의 **첫 계단 중앙값**에 건다 — 한 계열(정면)에 걸면 안내선이
    데이터 밖으로 나가 읽히지 않는다. ⚠불변선은 결론상 데이터와 겹치므로 글자를 안 붙이고
    (겹침 금지) 설명은 그림 밑 한 줄에 둔다. 글자는 데이터에서 떨어지는 1/spp 선에만."""
    xx = np.array([min(xs), max(xs)], float)
    ax.plot(xx, y0 + DB_PER_OCT_MC * (np.log2(xx) - np.log2(x0)),
            ls="--", lw=1.3, color=MUTED, zorder=1)
    ax.plot(xx, np.array([y0, y0]), ls=":", lw=1.3, color=MUTED, zorder=1)
    if label:
        xl = float(np.exp(0.5 * (np.log(xx[0]) + np.log(xx[1]))))
        ax.annotate("1/spp", xy=(xl, y0 + DB_PER_OCT_MC * (np.log2(xl) - np.log2(x0))),
                    xytext=(2, -11), textcoords="offset points", fontsize=8.4,
                    color=MUTED, ha="left", va="top")


def make_main_fig(A, B, path):
    fig, ax = plt.subplots(2, 3, figsize=(15.4, 9.4))
    fig.patch.set_facecolor(SURF)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.815, bottom=0.085,
                        hspace=0.52, wspace=0.24)
    cols = [("ac_power_db", "(1)  AC power  (DC removed, all bands)"),
            ("floor_above_db", "(2)  Floor above tip  (median off-tooth bin)"),
            ("comb_above_db", "(3)  Comb lines above tip  (k x f_flash +/- 8 Hz)")]

    # ── 1 행: 사다리 A ────────────────────────────────────────────────────
    els = A["usable_els"]
    xs = [s for _, s in LADDER_A]
    for j, (key, ttl) in enumerate(cols):
        a = ax[0, j]
        _panel(a, ttl)
        ys_all = []
        for i, el in enumerate(els):
            y = [A["cells"][f"{e}|{el:+.0f}"][key] for e, _ in LADDER_A]
            ys_all += [v for v in y if v is not None and np.isfinite(v)]
            a.plot(xs, y, "-o", color=RAMP[i], lw=2.0, ms=7, mew=1.6,
                   mec=SURF, zorder=3, label=f"el {el:+.0f} deg")
        y0 = float(np.median([A["cells"][f"sionna|{el:+.0f}"][key] for el in els]))
        _guides(a, xs[0], y0, xs, label=(j == 0))
        a.set_xscale("log", base=2)
        a.set_xticks(xs)
        a.set_xticklabels([_spp_label(s) for s in xs])
        a.set_xlim(xs[0] / 1.9, xs[-1] * 2.6)
        lo, hi = min(ys_all), max(ys_all)
        mid = 0.5 * (lo + hi)
        a.set_ylim(mid - 42, mid + 42)          # 세 판의 dB **폭을 같게** — 기울기 비교용
        if j == 0:
            a.set_ylabel("absolute power  [dB]", fontsize=10, color=INK2)
    # 범례는 판 **바깥** 여백에 가로로 — 판 안에 두면 어느 자리든 선과 겹친다
    h, lb = ax[0, 0].get_legend_handles_labels()
    fig.legend(h, lb, loc="upper center", bbox_to_anchor=(0.5, 0.882), ncol=4,
               frameon=False, fontsize=9.5, labelcolor=INK2, handlelength=2.0,
               columnspacing=2.4)
    # 직접 라벨은 선이 가장 잘 벌어진 3 열에만 (겹침 방지)
    a = ax[0, 2]
    for i, el in enumerate(els):
        yv = A["cells"][f"sionna_p4000000000|{el:+.0f}"]["comb_above_db"]
        a.annotate(f"el {el:+.0f}", xy=(xs[-1], yv), xytext=(7, 0),
                   textcoords="offset points", color=RAMP[i], fontsize=8.5,
                   va="center", ha="left", clip_on=False)

    # ── 2 행: 사다리 B ────────────────────────────────────────────────────
    good = [m for m in B["arms"] if m["complete"] and not m["degenerate"]
            and B["rung_validity"][m["spp"]]["usable"]]
    sppB = sorted({m["spp"] for m in good})
    for j, (key, ttl) in enumerate(cols):
        a = ax[1, j]
        _panel(a, ttl)
        xv = [m["spp"] for m in good]
        yv = [m[key] for m in good]
        a.plot(xv, yv, "o", color=C_B, ms=6.5, mew=1.4, mec=SURF, alpha=0.85, zorder=3)
        mu = [float(np.mean([m[key] for m in good if m["spp"] == s])) for s in sppB]
        a.plot(sppB, mu, "-", color=C_B, lw=2.0, zorder=4)
        _guides(a, sppB[0], mu[0], sppB, label=(j == 0))
        a.set_xscale("log", base=2)
        # 2.848G 와 4G 는 0.49 옥타브밖에 안 떨어져 라벨이 겹친다 — 촘촘한 쪽을 비운다
        keep = [s for i, s in enumerate(sppB)
                if i == len(sppB) - 1 or np.log2(sppB[i + 1] / s) > 0.7]
        a.set_xticks(sppB)
        a.set_xticklabels([_spp_label(s) if s in keep else "" for s in sppB],
                          rotation=30, ha="right", fontsize=8.6)
        a.set_xlim(sppB[0] / 1.6, sppB[-1] * 1.8)
        fin = [v for v in yv if v is not None and np.isfinite(v)]
        mid = 0.5 * (min(fin) + max(fin))
        a.set_ylim(mid - 22, mid + 22)
        a.set_xlabel("rays per pose  (spp)", fontsize=10, color=INK2)
        if j == 0:
            a.set_ylabel("absolute power  [dB]", fontsize=10, color=INK2)

    fig.text(0.008, 0.930, "Ladder A  —  10 m, 4096 poses, depth 1, physics off "
                           "(inside far-field boundary 14.08 m)",
             fontsize=11.0, color=INK, weight="bold")
    fig.text(0.008, 0.425, "Ladder B  —  40 m, 1024 poses, el -15 deg, one dot per seed, "
                           "rungs below 64M dropped (no echo)",
             fontsize=11.0, color=INK, weight="bold")
    fig.text(0.008, 0.014,
             "Dashed grey = Monte-Carlo prediction (power ∝ 1/spp, −6 dB per 4x).   "
             "Dotted grey = invariance (0 dB per octave); it runs through the data, "
             "which is the result.   Both anchored at the first rung.   "
             "Panels share one dB span within a row.",
             fontsize=8.8, color=MUTED)
    fig.suptitle("Ray budget ladder read as absolute AC power  —  does structure appear, "
                 "or does only the floor move?",
                 fontsize=13.6, color=INK, y=0.982)
    fig.savefig(path, dpi=150, facecolor=SURF)
    plt.close(fig)


def make_diag_fig(A, B, regs, path):
    fig, ax = plt.subplots(1, 3, figsize=(15.4, 4.9))
    fig.patch.set_facecolor(SURF)
    els = A["usable_els"]
    xs = [s for _, s in LADDER_A]

    a = ax[0]
    _panel(a, "(a)  Comb share of above-tip power")
    for i, el in enumerate(els):
        y = [A["cells"][f"{e}|{el:+.0f}"]["comb_share_pct"] for e, _ in LADDER_A]
        a.plot(xs, y, "-o", color=RAMP[i], lw=2.0, ms=7, mew=1.6, mec=SURF, zorder=3,
               label=f"el {el:+.0f} deg")
    wn = float(np.mean([A["cells"][f"sionna|{el:+.0f}"]["white_neutral_pct"]
                        for el in els]))
    a.axhline(wn, ls="--", lw=1.3, color=MUTED, zorder=1)
    a.annotate(f"white noise = {wn:.1f} %", xy=(xs[0], wn), xytext=(0, 6),
               textcoords="offset points", fontsize=8.6, color=MUTED)
    a.set_xscale("log", base=2); a.set_xticks(xs)
    a.set_xticklabels([_spp_label(s) for s in xs])
    a.set_xlim(xs[0] / 1.9, xs[-1] * 1.9)
    a.set_ylim(-4, 104)
    a.set_ylabel("share  [%]", fontsize=10, color=INK2)
    a.set_xlabel("rays per pose  (spp)", fontsize=10, color=INK2)
    a.legend(frameon=False, fontsize=9, loc="center right", labelcolor=INK2)

    a = ax[1]
    _panel(a, "(b)  Paths found per pose (median)")
    for i, el in enumerate(els):
        y = [A["cells"][f"{e}|{el:+.0f}"]["npaths_median"] for e, _ in LADDER_A]
        a.plot(xs, y, "-o", color=RAMP[i], lw=2.0, ms=7, mew=1.6, mec=SURF, zorder=3)
    xx = np.array([xs[0], xs[-1]], float)
    y0 = A["cells"][f"sionna|{els[0]:+.0f}"]["npaths_median"]
    a.plot(xx, y0 * xx / xx[0], ls="--", lw=1.3, color=MUTED, zorder=1)
    a.text(0.03, 0.95, "grey dashed:  ∝ spp", transform=a.transAxes,
           fontsize=8.8, color=MUTED, ha="left", va="top")
    a.set_xscale("log", base=2); a.set_yscale("log")
    a.set_xticks(xs); a.set_xticklabels([_spp_label(s) for s in xs])
    a.set_xlim(xs[0] / 1.9, xs[-1] * 1.9)
    a.set_ylabel("paths / pose", fontsize=10, color=INK2)
    a.set_xlabel("rays per pose  (spp)", fontsize=10, color=INK2)

    a = ax[2]
    _panel(a, "(c)  Fitted slope  [dB per octave of spp]")
    rows = regs["forest"]
    ypos = np.arange(len(rows))[::-1]
    for yp, r in zip(ypos, rows):
        col = C_B if r["ladder"] == "B" else RAMP[2]
        if r["ci95"]:
            a.plot(r["ci95"], [yp, yp], "-", color=col, lw=2.4, solid_capstyle="round",
                   zorder=3)
        a.plot([r["slope"]], [yp], "o", color=col, ms=8, mew=1.6, mec=SURF, zorder=4)
    a.axvline(DB_PER_OCT_MC, ls="--", lw=1.3, color=MUTED, zorder=1)
    a.axvline(0.0, ls=":", lw=1.3, color=MUTED, zorder=1)
    a.set_yticks(ypos)
    a.set_yticklabels([r["label"] for r in rows], fontsize=8.8, color=INK2)
    a.set_xlabel("dB per octave of spp", fontsize=10, color=INK2)
    a.set_xlim(-5.2, 5.2)
    a.set_ylim(-1.35, len(rows) - 0.35)
    # 기준선 이름표는 행 **아래** 빈 띠에 — 행 라벨·막대와 겹치지 않는 유일한 자리다
    a.annotate("1/spp (MC)", xy=(DB_PER_OCT_MC, -1.0), fontsize=8.4,
               color=MUTED, ha="center", va="center")
    a.annotate("invariant", xy=(0.0, -1.0), xytext=(0, 0), textcoords="offset points",
               fontsize=8.4, color=MUTED, ha="center", va="center")

    fig.suptitle("Diagnostics — where the comb sits, how paths grow, and what the "
                 "regression says", fontsize=12.4, color=INK, y=0.995)
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.93])
    fig.savefig(path, dpi=150, facecolor=SURF)
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════ #
#  ⑧ 자가검사
# ═══════════════════════════════════════════════════════════════════════════ #
def self_checks(A, B, regs):
    ck = []

    def add(name, ok, detail, hard=True):
        ck.append(dict(name=name, pass_=bool(ok), hard=bool(hard), detail_ko=detail))

    # 1 · Parseval — ΣP 가 창 가중 평균 전력과 같아야 «절대 전력» 이라고 부를 수 있다
    errs = [c["parseval_rel_err"] for c in A["table"] if c["parseval_rel_err"] is not None]
    errs += [c["parseval_rel_err"] for c in B["arms"] if c["parseval_rel_err"] is not None]
    add("parseval", max(errs) < 1e-9,
        f"ΣP 와 Σ|x·w|²/Σw² 의 최대 상대오차 {max(errs):.2e} < 1e-9 — "
        "스펙트럼 열의 dB 가 절대 전력이다")

    # 1b · 창 편향이 **사다리를 따라 움직이지 않나** — 움직이면 기울기가 창의 산물이다.
    #      헤드라인 회귀는 el<0 이므로 거기서만 게이트로 걸고, el 0 은 진단으로 남긴다.
    bias = collections.defaultdict(list)
    for c in A["table"]:
        bias[c["el_deg"]].append(c["window_bias_db"])
    sw_head = max(max(v) - min(v) for el, v in bias.items() if el != 0)
    sw_el0 = max(bias[0.0]) - min(bias[0.0])
    add("window_bias_stable_headline", sw_head < 1.0,
        f"헤드라인 앙각(el<0)에서 창 가중 평균 − 평범한 평균 의 차가 최대 {sw_head:.2f} dB "
        f"만 움직인다(<1 dB) — 측정된 기울기가 창의 산물이 아니다. "
        f"⚠el 0 은 {sw_el0:.2f} dB 로 크다 — 정면의 요동이 기록 안에서 **고르지 않다**"
        "(몇몇 자세에 몰려 있다)는 뜻이고, 그래서 el 0 을 헤드라인에서 뗀 근거가 하나 더 된다")

    # 2 · 마스크 분할 — 이빨 안/밖이 겹치지 않고 합이 상한 위 전체
    c = A["table"][0]
    add("mask_partition", c["n_bins_comb"] < c["n_bins_above"],
        f"상한 위 {c['n_bins_above']} 빈 중 이빨 {c['n_bins_comb']} 빈 — 나머지가 바닥 표본")

    # 3 · 백색 중립값 — 백색 잡음을 넣으면 빗살 몫이 이론값(빈 수 비율)에 붙어야 한다
    rng = np.random.default_rng(17)
    prf, ffl = A["prf"], A["f_flash"]
    ftip = A["table"][0]["f_tip_hz"]
    sh = []
    for _ in range(80):
        w = rng.normal(size=4096) + 1j * rng.normal(size=4096)
        sh.append(cell_metrics(w, ftip, prf, ffl)["comb_share_pct"])
    neutral = A["table"][0]["white_neutral_pct"]
    add("white_neutral", abs(float(np.mean(sh)) - neutral) < 1.5,
        f"백색 잡음 80 판의 빗살 몫 평균 {np.mean(sh):.2f} % vs 이론 중립값 "
        f"{neutral:.2f} % (차 {abs(np.mean(sh) - neutral):.2f} %p < 1.5)")

    # 4 · 회귀가 1/spp 를 실제로 −3.01 로 읽나 (합성 주입)
    spp = np.array([s for _, s in LADDER_A], float)
    syn = 10 * np.log10(1.0 / spp) + 100.0
    r = slope_db_per_octave(spp, syn)
    add("regression_recovers_mc", abs(r["slope_db_per_octave"] - DB_PER_OCT_MC) < 0.02,
        f"합성 1/spp 열의 회귀 기울기 {r['slope_db_per_octave']} dB/oct "
        f"(예측 {DB_PER_OCT_MC})")

    # 5 · 회귀가 불변을 0 으로 읽나
    r0 = slope_db_per_octave(spp, np.full(4, -120.0))
    add("regression_recovers_flat", abs(r0["slope_db_per_octave"]) < 1e-9,
        f"상수열의 회귀 기울기 {r0['slope_db_per_octave']} dB/oct (예측 0)")

    # 6 · 원장 대조 — 재계산한 레벨이 원장 level_db 와 같아야 같은 데이터다
    d = [abs(c["level_db_recomputed"] - c["level_db_ledger"]) for c in A["table"]]
    add("level_matches_ledger", max(d) < 0.011,
        f"20log10 mean|E| 재계산 vs 원장 level_db 최대 차 {max(d):.4f} dB < 0.011 "
        "(원장은 소수 2 자리 반올림)")

    # 7 · 퇴화 팔 검출 — 사다리 B 의 낮은 계단은 에코가 아예 없다(구조적 0)
    deg = [f"{_spp_label(m['spp'])}/s{m['seed']}({m['degenerate_reason_ko']})"
           for m in B["arms"] if m["degenerate"]]
    add("degenerate_detected", len(deg) > 0,
        f"퇴화 팔 {len(deg)} 개를 검출해 회귀에서 제외했다 — 결측 자리표시자(−6000 dB)가 "
        f"아니라 «물리적으로 아무것도 없음» 이다: {', '.join(deg)}")

    # 8 · 빗살 널 — 반 이빨 어긋난 창이 훨씬 낮아야 «이빨 위» 라는 말이 성립한다
    offn = [c for c in A["table"] if c["el_deg"] != 0 and c["comb_over_shift_db"]]
    add("comb_null_control", min(c["comb_over_shift_db"] for c in offn) > 6.0,
        f"정면 밖 셀 {len(offn)} 개 전부에서 이빨 위 / 반 이빨 어긋남 ≥ "
        f"{min(c['comb_over_shift_db'] for c in offn):.1f} dB — 마스크가 아무 데나 "
        "걸리는 것이 아니다")

    # 9 · 사다리를 섞지 않았나
    add("ladders_not_pooled",
        all(r["ladder"] in ("A", "B") for r in regs["forest"]),
        "회귀는 사다리 A(10 m)·B(40 m) 를 따로 적합했다 — 거리가 다르면 같은 축이 아니다")

    # 10 · GPU 를 안 썼나
    add("no_gpu", not any(m in sys.modules for m in ("sionna.rt", "mitsuba", "drjit")),
        "sionna.rt·mitsuba·drjit 어느 것도 임포트되지 않았다")
    return ck


# ═══════════════════════════════════════════════════════════════════════════ #
#  ⑨ 본체
# ═══════════════════════════════════════════════════════════════════════════ #
def main():
    t0 = _dt.datetime.now()
    Z = np.load(ELEV_NPZ, allow_pickle=True)
    J = json.load(open(ELEV_JSON))
    print("■ 원장 적재 완료 — 키 %d 개, 행 %d 개" % (len(Z.files), len(J["rows"])))

    CEN = census(J["rows"], Z.files)
    print("■ 전수조사 — 앙각 원장의 spp 계단:",
          [_spp_label(s) for s in CEN["distinct_spp_in_elevation_ledger"]])

    A = build_ladder_a(Z, J)
    APH = build_ladder_a_phys(Z, J)
    B = build_ladder_b()
    print("■ 사다리 A 채점 앙각:", A["usable_els"], "· 제외:",
          [e["el_deg"] for e in A["excluded_els"]])
    print("■ 사다리 B 계단:", [_spp_label(s) for s in B["spp_present"]],
          "· 시드:", B["seeds_per_spp"])

    # ── 회귀 ────────────────────────────────────────────────────────────
    COLS = [("ac_power_db", "(1) AC power"),
            ("floor_above_db", "(2) floor above tip"),
            ("comb_above_db", "(3) comb above tip"),
            ("dc_power_db", "DC power"),
            ("ac_below_tip_db", "AC below tip"),
            ("ac_above_tip_db", "AC above tip")]
    regA, regA_per_el, forest = {}, {}, []
    els = A["usable_els"]
    for key, lbl in COLS:
        spp = [c["spp"] for c in A["table"]]
        y = [c[key] for c in A["table"]]
        g = [c["el_deg"] for c in A["table"]]
        regA[key] = slope_db_per_octave(spp, y, groups=g)
        # el 0 을 뺀 판 — 정면은 정반사가 지배해 다른 체제다
        m = [i for i, c in enumerate(A["table"]) if c["el_deg"] != 0]
        regA[key + "__excl_el0"] = slope_db_per_octave(
            [spp[i] for i in m], [y[i] for i in m], groups=[g[i] for i in m])
        per = {}
        for el in els:
            sub = [c for c in A["table"] if c["el_deg"] == el]
            per[f"{el:+.0f}"] = slope_db_per_octave([c["spp"] for c in sub],
                                                    [c[key] for c in sub])
        # 앙각 하나씩 빼 보는 민감도 (표본 4 개짜리 팔이라 반드시 확인한다)
        loo = []
        for el in els:
            m2 = [i for i, c in enumerate(A["table"]) if c["el_deg"] != el]
            loo.append(dict(dropped_el=el, slope=slope_db_per_octave(
                [spp[i] for i in m2], [y[i] for i in m2],
                groups=[g[i] for i in m2])["slope_db_per_octave"]))
        regA_per_el[key] = dict(per_elevation=per, leave_one_elevation_out=loo)
        if key in ("ac_power_db", "floor_above_db", "comb_above_db", "dc_power_db"):
            r = regA[key + "__excl_el0"]
            forest.append(dict(ladder="A", label=f"A {lbl}  (el<0)",
                               slope=r["slope_db_per_octave"], ci95=r["ci95"]))

    good = [m for m in B["arms"] if m["complete"] and not m["degenerate"]
            and B["rung_validity"][m["spp"]]["usable"]]
    regB = {}
    for key, lbl in COLS:
        regB[key] = slope_db_per_octave([m["spp"] for m in good],
                                        [m[key] for m in good])
        if key in ("ac_power_db", "floor_above_db", "comb_above_db", "dc_power_db"):
            r = regB[key]
            forest.append(dict(ladder="B", label=f"B {lbl}",
                               slope=r["slope_db_per_octave"], ci95=r["ci95"]))
    # 계단 사이 실제 변화 — 회귀 한 줄이 «로그-선형» 을 가정하므로 원자료를 함께 낸다
    steps = {}
    for key, _ in COLS:
        rows_s = []
        for el in els:
            for (e0, s0), (e1, s1) in zip(LADDER_A[:-1], LADDER_A[1:]):
                y0 = A["cells"][f"{e0}|{el:+.0f}"][key]
                y1 = A["cells"][f"{e1}|{el:+.0f}"][key]
                oct_ = float(np.log2(s1 / s0))
                rows_s.append(dict(el_deg=el, frm=_spp_label(s0), to=_spp_label(s1),
                                   octaves=_r(oct_, 2), delta_db=_r(y1 - y0, 2),
                                   db_per_octave=_r((y1 - y0) / oct_, 3)))
        steps[key] = rows_s
    # 사다리 B 민감도 — 계단째 배제 규칙을 풀고 «살아남은 시드» 만 넣으면 기울기가 어떻게
    # 되나. 생존 편향이 결론을 만들지 않았음을 보이는 자리다(그리고 편향의 방향도 남긴다).
    lax = [m for m in B["arms"] if m["complete"] and not m["degenerate"]]
    sens_b = {k: slope_db_per_octave([m["spp"] for m in lax], [m[k] for m in lax])
              ["slope_db_per_octave"]
              for k in ("ac_power_db", "floor_above_db", "comb_above_db")}
    regs = dict(ladder_a=regA, ladder_a_detail=regA_per_el, ladder_b=regB,
                ladder_a_per_step=steps, forest=forest,
                ladder_b_sensitivity_survivor_seeds=dict(
                    note_ko="계단째 배제 규칙을 풀고 «퇴화하지 않은 시드만» 넣어 다시 적합한 "
                            "판. 결론이 규칙에 매달리지 않는지, 생존 편향이 어느 쪽으로 "
                            "미는지 보는 자리다.",
                    n=len(lax), slopes=sens_b))

    # ── 사전등록 판정 ────────────────────────────────────────────────────
    #  ⚠ «신뢰구간이 0 을 덮나» 만으로 판정하면 표본이 많아질수록(사다리 B) 물리적으로
    #    무의미한 −0.3 dB/옥타브도 «불변 아님» 이 된다. 그래서 판정을 **세 갈래 분류 +
    #    효과 크기**로 낸다 — 규칙 자체(신뢰구간이 예측을 덮나)는 사전등록 그대로다.
    def classify(reg, span_oct):
        s = reg["slope_db_per_octave"]
        ci = reg["ci95"]
        cov_mc = bool(reg.get("covers_mc_minus3"))
        cov_0 = bool(reg.get("covers_flat_zero"))
        frac = s / DB_PER_OCT_MC                       # MC 예측 대비 몇 배인가
        if cov_mc and not cov_0:
            lab = "MC_FLOOR"
        elif cov_0 and not cov_mc:
            lab = "INVARIANT"
        elif cov_0 and cov_mc:
            lab = "UNDETERMINED"
        else:
            lab = "NEITHER"
        # 이 기울기로 10 dB 를 벌려면 광선을 몇 배나 더 사야 하나 (지출 결정용)
        need = (None if abs(s) < 1e-6 else float(2.0 ** (10.0 / abs(s))))
        return dict(slope_db_per_octave=s, ci95=ci, class_=lab,
                    frac_of_mc_rate=_r(frac, 3),
                    total_change_over_ladder_db=_r(s * span_oct, 2),
                    mc_would_change_db=_r(DB_PER_OCT_MC * span_oct, 2),
                    rays_multiplier_for_10dB=(None if need is None or need > 1e30
                                              else float(f"{need:.3g}")),
                    covers_mc_minus3=cov_mc, covers_flat_zero=cov_0)

    span_a = float(np.log2(LADDER_A[-1][1] / LADDER_A[0][1]))
    sppB_ok = sorted({m["spp"] for m in good})
    span_b = float(np.log2(sppB_ok[-1] / sppB_ok[0]))
    fa = regA["floor_above_db__excl_el0"]
    ca = regA["comb_above_db__excl_el0"]
    fb, cb = regB["floor_above_db"], regB["comb_above_db"]
    cls = {"A_floor": classify(fa, span_a), "A_comb": classify(ca, span_a),
           "A_ac": classify(regA["ac_power_db__excl_el0"], span_a),
           "B_floor": classify(fb, span_b), "B_comb": classify(cb, span_b),
           "B_ac": classify(regB["ac_power_db"], span_b),
           "B_dc": classify(regB["dc_power_db"], span_b)}

    #  ① 「바닥이 1/spp 를 따라가나」 — 두 사다리 모두 −3.01 을 덮으면 성립,
    #     두 사다리 모두 안 덮으면 불성립(반증), 갈리면 판정 보류
    c1 = (cls["A_floor"]["covers_mc_minus3"] and cls["B_floor"]["covers_mc_minus3"])
    c1_falsified = ((not cls["A_floor"]["covers_mc_minus3"])
                    and (not cls["B_floor"]["covers_mc_minus3"]))
    #  ② 「빗살 선이 spp 에 불변인가」 — 실질 불변: MC 율의 1/4 미만이고 −3.01 을 안 덮는다
    c2 = (abs(cls["A_comb"]["frac_of_mc_rate"]) < 0.25
          and abs(cls["B_comb"]["frac_of_mc_rate"]) < 0.25
          and not cls["A_comb"]["covers_mc_minus3"]
          and not cls["B_comb"]["covers_mc_minus3"])
    floor_flat = (abs(cls["A_floor"]["frac_of_mc_rate"]) < 0.25
                  and abs(cls["B_floor"]["frac_of_mc_rate"]) < 0.25)

    if c1_falsified and c2 and floor_flat:
        verdict_id = "PREREG_1_FALSIFIED__ABOVE_TIP_IS_RAY_INVARIANT"
        verdict_ko = (
            "①**불성립** · ②**성립**. 상한 위 **바닥은 1/spp 를 안 따라간다** — 내려가지 "
            f"않고 사실상 평평하다(사다리 A {fa['slope_db_per_octave']:+.2f} · "
            f"B {fb['slope_db_per_octave']:+.2f} dB/옥타브, MC 예측 −3.01 의 각각 "
            f"{100 * abs(cls['A_floor']['frac_of_mc_rate']):.0f} % · "
            f"{100 * abs(cls['B_floor']['frac_of_mc_rate']):.0f} %; 두 사다리 모두 "
            "신뢰구간이 −3.01 을 안 덮는다). 빗살 선도 같은 뜻으로 평평하다"
            f"(A {ca['slope_db_per_octave']:+.2f} · B {cb['slope_db_per_octave']:+.2f}). "
            "그러므로 사전등록이 예비했던 문장 「이 예산의 몬테카를로 바닥 위로는 구조가 "
            "없다」를 **그대로 쓸 수 없다** — 상한 위에 있는 것은 몬테카를로 **바닥이 "
            "아니다**(몬테카를로 바닥이면 광선에 반비례해 내려가야 하는데 안 내려간다). "
            "옳은 문장은 **「날개끝 상한 위의 내용물은 광선 수에 불변이다 — 광선을 더 부어도 "
            "바닥이 안 내려가고 구조도 안 생긴다. 광선이 사는 것은 상한 **아래**(에코 레벨) "
            "뿐이고 그것도 4e9 에서 안 멈췄다」** 다. "
            "지출 언어로 옮기면 — 상한 위 바닥을 10 dB 낮추는 데 필요한 광선 배수는 "
            + " · ".join(
                f"사다리 {nm}: " + ("10^30 배 초과(사실상 불가)"
                                    if cls[k]["rays_multiplier_for_10dB"] is None
                                    else f"{cls[k]['rays_multiplier_for_10dB']:.3g} 배")
                for nm, k in (("A", "A_floor"), ("B", "B_floor")))
            + " 다. 「GPU 를 더 사면 되나」의 답은 **아니오** 다.")
    elif c1_falsified and not c2:
        verdict_id = "PREREG_1_FALSIFIED__COMB_NOT_INVARIANT"
        verdict_ko = ("①불성립(바닥이 1/spp 를 안 따라간다) · ②불성립(빗살 선이 예산에 "
                      "따라 움직인다) — 아래 분류표를 그대로 읽는다.")
    elif c1 and c2:
        verdict_id = "PREREG_CONFIRMED"
        verdict_ko = ("①성립 · ②성립 — 사전등록대로 「이 예산의 몬테카를로 바닥 위로는 "
                      "구조가 없다」로 문장을 고친다.")
    else:
        verdict_id = "MIXED"
        verdict_ko = ("판정이 갈렸다 — 아래 분류표를 그대로 읽는다. "
                      f"①(바닥 ∝1/spp) {c1} · ②(빗살 실질 불변) {c2}")

    # ── 물리 켬 두 계단 읽기 (별도 축) ───────────────────────────────────
    ph = collections.defaultdict(dict)
    for c in APH["clean_rungs"]:
        ph[c["el_deg"]][c["spp"]] = c
    PHYS_DELTA, dfl, dcb, dsh = [], [], [], []
    for el in sorted(ph, reverse=True):
        d = ph[el]
        if len(d) != 2:
            continue
        a0, a1 = d[11_111_111], d[250_000_000]
        row = dict(el_deg=el, octaves=_r(np.log2(250e6 / 11111111), 2),
                   d_ac_db=_r(a1["ac_power_db"] - a0["ac_power_db"], 2),
                   d_floor_db=_r(a1["floor_above_db"] - a0["floor_above_db"], 2),
                   d_comb_db=_r(a1["comb_above_db"] - a0["comb_above_db"], 2),
                   comb_share_pct=[_r(a0["comb_share_pct"], 1), _r(a1["comb_share_pct"], 1)])
        PHYS_DELTA.append(row)
        dfl.append(row["d_floor_db"]); dcb.append(row["d_comb_db"])
        dsh.append(row["comb_share_pct"])
    PHYS_READ = (
        f"⚠물리를 켜면 상한 위가 **더 이상 예산에 불변이 아니다**. 같은 22.5 배(4.49 옥타브) "
        f"한 계단에 상한 위 바닥이 {min(dfl):+.1f}~{max(dfl):+.1f} dB, 빗살 선이 "
        f"{min(dcb):+.1f}~{max(dcb):+.1f} dB **올라간다**. 그리고 빗살 몫이 "
        f"{min(s[0] for s in dsh):.0f}~{max(s[0] for s in dsh):.0f} % 에서 "
        f"{min(s[1] for s in dsh):.0f}~{max(s[1] for s in dsh):.0f} % 로 내려가 "
        f"백색 중립값({A['table'][0]['white_neutral_pct']:.1f} %)에 붙는다 — 즉 광선을 부으면 "
        "물리 켠 팔에서는 **리듬 없는 넓은 잡음이 얹혀 구조를 덮는다**. ⚠단 이 두 계단은 "
        "깊이 3 이고 물리끔 사다리는 깊이 1 이라, 이 상승을 «회절의 성질» 로 귀속하려면 "
        "R13 의 스위치 분해가 필요하다 — 여기서는 **현상만** 기록한다.")

    # ── 헤드라인 수치 ────────────────────────────────────────────────────
    def span(key, el):
        c0 = A["cells"][f"sionna|{el:+.0f}"][key]
        c1 = A["cells"][f"sionna_p4000000000|{el:+.0f}"][key]
        return _r(c1 - c0, 2)

    head = dict(
        ladder_a_360x_change_db={
            f"el{el:+.0f}": {k: span(k, el) for k in
                             ("ac_power_db", "dc_power_db", "floor_above_db",
                              "comb_above_db", "ac_below_tip_db", "ac_above_tip_db")}
            for el in els},
        slope_db_per_octave={
            "A_ac_power_el_lt0": regA["ac_power_db__excl_el0"]["slope_db_per_octave"],
            "A_floor_above_el_lt0": fa["slope_db_per_octave"],
            "A_comb_above_el_lt0": ca["slope_db_per_octave"],
            "B_ac_power": regB["ac_power_db"]["slope_db_per_octave"],
            "B_floor_above": fb["slope_db_per_octave"],
            "B_comb_above": cb["slope_db_per_octave"],
            "B_dc_power": regB["dc_power_db"]["slope_db_per_octave"]},
        comb_share_pct={f"el{el:+.0f}": [_r(A["cells"][f"{e}|{el:+.0f}"]["comb_share_pct"], 1)
                                         for e, _ in LADDER_A] for el in els},
        white_neutral_pct=_r(A["table"][0]["white_neutral_pct"], 2))

    # ── 그림 ────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    make_main_fig(A, B, OUT_FIG)
    make_diag_fig(A, B, regs, OUT_FIG2)
    print(f"■ 그림 저장: {OUT_FIG}")
    print(f"■ 그림 저장: {OUT_FIG2}")

    CK = self_checks(A, B, regs)
    for c in CK:
        print(("  ✅" if c["pass_"] else "  ⛔") + f" {c['name']:26s} {c['detail_ko']}")
    hard_fail = [c["name"] for c in CK if c["hard"] and not c["pass_"]]

    CIT = scan_citations()

    # ── 원장 ────────────────────────────────────────────────────────────
    def strip(c):
        return {k: (_r(v, 3) if isinstance(v, float) else v) for k, v in c.items()}

    OUT = {
        "_meta": {
            "generator": "benchmark/raybudget_ac_ladder.py",
            "experiment": "R17 · 광선 예산 사다리를 AC 로 다시 읽기",
            "design_doc": "docs/NEXT_EXPERIMENTS.md (순위 1 · §3-1 R17)",
            "date_kst": (t0 + _dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST"),
            "host": socket.gethostname(),
            "question_ko": "광선을 더 부으면 마이크로도플러 «구조» 가 생기나, "
                           "아니면 바닥만 내려가나",
            "compute_ko": "⛔GPU 0 — sionna.rt·mitsuba 임포트 없이 저장된 원장 npz 만 읽었다",
            "reads_only": ["outputs/elevation_sweep_md.npz", "outputs/elevation_sweep_md.json",
                           "outputs/raybudget_ladder/spp*_s*_*.npz",
                           "outputs/report07_range40_raybudget.json"],
            "writes": [os.path.relpath(OUT_JSON, ROOT), os.path.relpath(OUT_FIG, ROOT),
                       os.path.relpath(OUT_FIG2, ROOT)],
            "metric_recipe_ko": (
                "P = |FFT((E − mean(E))·hanning)|² / (n·Σw²)  → ΣP = mean|E−mean|² "
                "(Parseval 정규화라 dB 가 **절대 전력**이다). "
                "above = |fr| ≥ f_tip(el). 빗살 = 박자 f_flash 정수배 ±8 Hz "
                "(원격자가 성길 때만 ±1.5Δf 로 넓히고 그 사실을 셀마다 기록). "
                "바닥 = above ∩ 이빨 **밖** 빈의 **중앙값**. "
                "⭐레벨 비교는 전부 정지 성분(DC = 시계열 평균) 제거 후다."),
            "distance_warning_ko": (
                "⚠사다리 A 는 **10 m**(원거리장 경계 2D²/λ ≈ 14.08 m 의 **안쪽**), "
                "사다리 B 는 **40 m**(바깥)다. 둘을 한 회귀에 섞지 않았고 표에서도 "
                "나란히 놓지 않는다. 리포트 정본인 **15 m** 판에는 예산 축이 아예 없다."),
            "units_ko": "sionna 팔은 채널계수 h(경로손실 포함, 무차원)라 dB 값은 "
                        "**같은 엔진·같은 거리 안에서만** 비교한다. 우리 커널(ours)은 "
                        "산란장 E[m²]로 눈금이 달라 사다리에 넣지 않고 참조로만 싣는다.",
        },
        "_prereg": {
            "criterion_1_ko": "상한 위 **바닥 절대전력**이 1/spp 를 따라가나 "
                              "(예산 4 배마다 −6 dB = −3.01 dB/옥타브)",
            "criterion_2_ko": "상한 위 **빗살 선 전력**은 spp 에 불변인가 (0 dB/옥타브)",
            "decision_rule_ko": "기울기 회귀의 95 % 신뢰구간이 예측값을 덮으면 성립, "
                                "안 덮으면 불성립. ①성립·②불변이면 「구조 없음」을 "
                                "「이 예산의 MC 바닥 위로는 구조가 없다」로 고친다.",
            "deviations_ko": [
                "설계서는 물리끔 4 계단만 지정했다. 전수조사에서 **40 m 예산 사다리**"
                "(outputs/raybudget_ladder, 8 계단 × 시드 3~8)를 찾았고, 시드가 있어 "
                "**모형이 아니라 재현으로** 신뢰구간을 낼 수 있으므로 **사다리 B** 로 "
                "같은 세 열을 함께 낸다. 거리(40 m)가 다르므로 사다리 A 와 절대 안 섞는다.",
                "설계서 판정문의 «구조 없음/MC 바닥» 두 갈래 어디에도 안 들어맞는 결과가 "
                "나올 수 있어, 판정문에 세 번째 갈래(바닥이 **안 내려가는** 경우)를 "
                "미리 넣었다. 판정 규칙(신뢰구간이 예측을 덮나) 자체는 안 바꿨다.",
                "빗살 선은 원(raw) 합과 **바닥을 뺀 초과분**을 둘 다 싣는다. 사전등록 "
                "열은 원 합이고 초과분은 보조다 — 원 합만 보면 이빨 아래 깔린 바닥이 "
                "섞여 들어간다.",
                "el 0 은 정반사가 지배해 다른 체제이므로 **el<0 만의 회귀**를 헤드라인으로 "
                "쓰고 el 0 포함 판을 함께 싣는다(설계서에 없던 구분 — 이유는 §regime_split).",
                "②의 판정을 «신뢰구간이 0 을 덮나» 에서 «MC 율의 1/4 미만 + −3.01 을 "
                "안 덮음» 으로 **적었다**. 사다리 B 는 시드 재현이 30 판이라 신뢰구간이 "
                "±0.3 dB/옥타브까지 좁아지는데, 그 잣대로는 «6 옥타브에 −3 dB» 같은 "
                "물리적으로 무의미한 기울기도 «불변 아님» 이 된다. ①의 규칙은 안 바꿨다.",
                "사다리 B 에는 사전등록에 없는 **퇴화 배제 규칙**이 필요했다 — 낮은 계단은 "
                "경로가 아예 안 잡혀 시계열이 0 이거나 상수다. 배제 규칙(전부 0 · 요동 0 · "
                "자세 절반 초과에서 경로 없음)과 규칙을 푼 민감도 판을 둘 다 싣는다."],
        },
        "tldr_ko": [
            "광선을 360 배 부어도 **날개끝 상한 위**(마이크로도플러 구조가 살 수 있는 "
            f"유일하게 남은 자리)는 안 움직인다 — 바닥 {min(head['ladder_a_360x_change_db'][f'el{el:+.0f}']['floor_above_db'] for el in els if el != 0):+.1f}"
            f"~{max(head['ladder_a_360x_change_db'][f'el{el:+.0f}']['floor_above_db'] for el in els if el != 0):+.1f} dB · "
            f"빗살 {min(head['ladder_a_360x_change_db'][f'el{el:+.0f}']['comb_above_db'] for el in els if el != 0):+.1f}"
            f"~{max(head['ladder_a_360x_change_db'][f'el{el:+.0f}']['comb_above_db'] for el in els if el != 0):+.1f} dB.",
            "같은 360 배에 **상한 아래**는 크게 오른다 — "
            f"{min(head['ladder_a_360x_change_db'][f'el{el:+.0f}']['ac_below_tip_db'] for el in els if el != 0):+.1f}"
            f"~{max(head['ladder_a_360x_change_db'][f'el{el:+.0f}']['ac_below_tip_db'] for el in els if el != 0):+.1f} dB. "
            "광선이 사는 것은 **에코 자체의 크기**이지 그 안의 무늬가 아니다.",
            "그러므로 「구조가 없다」도 「몬테카를로 바닥에 묻혔다」도 아니다. 옳은 말은 "
            "**「이 예산 축에서는 상한 위가 광선 수에 불변이다」** — 그래서 GPU 를 더 사도 "
            "이 자리는 안 바뀐다.",
            "예외는 정면(el 0) 하나다. 거기서는 정지 성분이 이미 수렴해 있고, 새로 찾는 "
            f"경로가 전부 요동으로만 들어가 상한 위가 오히려 "
            f"{head['ladder_a_360x_change_db']['el+0']['floor_above_db']:+.0f} dB **올라간다** "
            "(그리고 그 요동은 백색이라 리듬이 없다).",
            "빗살은 진짜 있다 — 상한 위 전력의 "
            f"{min(head['comb_share_pct'][f'el{el:+.0f}'][-1] for el in els if el != 0):.0f}"
            f"~{max(head['comb_share_pct'][f'el{el:+.0f}'][-1] for el in els if el != 0):.0f} % 가 "
            f"박자 정수배 ±8 Hz 에 앉아 있고(백색 중립값 {head['white_neutral_pct']:.1f} %), "
            "반 이빨 어긋난 창보다 22 dB 넘게 높다. 다만 **상한 위에는 물리가 없으므로** "
            "그 빗살은 신호가 아니라 자세 격자가 만든 결정론적 인공물이고, 광선으로는 "
            "지워지지 않는다.",
        ],
        "census": CEN,
        "ladder_a": {
            "arms": [dict(engine=e, spp=s) for e, s in LADDER_A],
            "held_fixed_ko": "matrice4e · 3.5 GHz · 10 m · 자세 4096 · 깊이 1 · 방위 0° · "
                             "물리(굴절·회절·모서리) 끔 · 확산 켬",
            "scored_elevations_deg": els,
            "excluded_elevations": A["excluded_els"],
            "cells": {k: strip(v) for k, v in A["cells"].items()},
            "baseline_reading_ko": (
                "⭐우리 커널(ours)도 같은 앙각에서 상한 위 빗살 몫이 "
                + "~".join(f"{v:.0f}" for v in (
                    min(A["baseline_ours"][f"{el:+.0f}"]["comb_share_pct"] for el in els),
                    max(A["baseline_ours"][f"{el:+.0f}"]["comb_share_pct"] for el in els)))
                + " % 이고 반 이빨 어긋난 창보다 "
                + f"{min(A['baseline_ours'][f'{el:+.0f}']['comb_over_shift_db'] for el in els):.0f}"
                + " dB 넘게 높다. 즉 **상한 위 빗살은 PathSolver 만의 병이 아니다** — "
                "두 엔진이 같은 자세 격자(결정론적 로터 위상열)를 쓰기 때문에 생기는 "
                "공통 인공물이다. 이 결과로 엔진을 탓하면 안 된다. ⚠눈금이 달라(ours 는 "
                "산란장 E[m²], sionna 는 무차원 h) 절대 dB 는 나란히 놓지 않는다 — "
                "여기서 비교 가능한 것은 **몫과 널 대비 여유**뿐이다."),
            "baseline_ours_reference": {k: strip(v) for k, v in A["baseline_ours"].items()},
        },
        "ladder_a_physics_on": {
            "warning_ko": "⚠**예산 축이 아니다** — 11.1M·250M 은 깊이 3·자세 4096 인데 "
                          "4e9 판은 깊이 1·자세 8192 라 깊이·자세가 예산과 섞였다. "
                          "설계서 §② 렌즈 3 처리대로 헤드라인에서 내리고 별도로만 싣는다. "
                          "아래 «깨끗한 두 계단» 만 같은 조건(d3·4096·10 m)이라 비교 가능하다.",
            "reading_ko": PHYS_READ,
            "clean_two_rungs_delta": PHYS_DELTA,
            "clean_two_rungs": [strip(c) for c in APH["clean_rungs"]],
            "confounded_4e9_rung": [strip(c) for c in APH["confounded_rungs"]],
        },
        "ladder_b_40m": {
            "note_ko": "40 m · el −15° · 자세 1024 · 시드 3~8 판. 계단 8 개 중 1M·16M 일부는 "
                       "경로가 아예 안 잡혀 **구조적 0(에코 없음)** 이고, 4M 의 두 시드는 "
                       "경로 1 개짜리 상수열이라 요동이 0 이다 — 둘 다 결측이 아니라 "
                       "«물리적으로 아무것도 없음» 이며 회귀에서 뺐다.",
            "spp_present": B["spp_present"], "seeds_per_spp": B["seeds_per_spp"],
            "rung_validity": {str(k): v for k, v in B["rung_validity"].items()},
            "rung_rule_ko": "⭐계단 안의 시드가 **하나라도** 퇴화면 계단째 뺀다. 살아남은 "
                            "시드만 쓰면 «에코를 찾은 판만 골라 본» 생존 편향이 생기고, 그 "
                            "편향이 사다리 왼쪽을 위로 끌어올려 기울기를 가짜로 음수로 만든다 "
                            "— 실측으로 4M 계단에서 그 일이 일어났다(민감도 절 참조).",
            "n_used_in_regression": len(good),
            "arms": [strip(m) for m in B["arms"]],
        },
        "regressions": regs,
        "headline": head,
        "verdict": {
            "id": verdict_id, "text_ko": verdict_ko,
            "criterion_1_floor_follows_1_over_spp": bool(c1),
            "criterion_1_falsified": bool(c1_falsified),
            "criterion_2_comb_invariant": bool(c2),
            "floor_is_effectively_flat": bool(floor_flat),
            "decision_note_ko": (
                "①은 사전등록 그대로 «신뢰구간이 −3.01 을 덮나» 로 판정했다. "
                "②는 «0 을 덮나» 만으로 보면 사다리 B 처럼 표본이 많은 판에서 "
                "물리적으로 무의미한 −0.3 dB/옥타브도 «불변 아님» 이 되므로, "
                "**MC 율의 1/4 미만 + −3.01 을 안 덮음** 을 «실질 불변» 으로 정의했다. "
                "판정 규칙을 이렇게 적은 이유를 _prereg.deviations 에도 남겼다."),
            "classification": cls,
        },
        "regime_split_ko": (
            "el 0 은 나머지와 **다른 체제**다. 정면에서는 동체 정반사가 지배해 정지 성분이 "
            "11.1M 에서 이미 수렴해 있고(360 배에 0.03 dB), 광선을 부으면 새로 찾는 경로가 "
            "전부 **요동**으로만 들어간다 — 그래서 el 0 에서는 상한 위 바닥도 빗살도 "
            "**올라간다**. 정반사가 꺼지는 앙각(−15·−45·−60)에서는 반대로 상한 위가 "
            "평평하고 상한 **아래**만 오른다. 한 회귀에 섞으면 이 두 체제가 상쇄된다."),
        "self_checks": CK,
        "citations_of_11p1M_and_convergence": {
            "note_ko": "11.1 M 계단 값과 「0.03 dB 안에 모인다(수렴)」 문장을 인용하는 자리다. "
                       "⭐«수렴» 을 말하는 줄은 전부 **정지 성분(DC)에 한정된 참**이다 — "
                       "같은 문장을 마이크로도플러(AC)나 «예산이 충분하다» 의 근거로 "
                       "**재인용 금지**. AC 는 같은 360 배에서 수렴하지 않는다.",
            "reuse_ban_legend_ko": {
                "OK_AS_WRITTEN__DC_ONLY": "원문이 이미 «정지 성분·레벨» 로 범위를 좁혀 놓아 "
                                          "문장 자체는 참이다. 인용할 때 그 단서를 **떼면 "
                                          "안 된다**.",
                "NEEDS_SCOPE_TAG": "«수렴» 을 범위 없이 말한다 — 인용 전에 «정지 성분에 "
                                   "한해» 단서를 붙여야 한다."},
            "n_hits": len(CIT),
            "n_claiming_convergence": sum(1 for h in CIT if h["claims_convergence"]),
            "n_needs_scope_tag": sum(1 for h in CIT if h["reuse_ban"] == "NEEDS_SCOPE_TAG"),
            "convergence_claims": [h for h in CIT if h["claims_convergence"]],
            "other_mentions": [h for h in CIT if not h["claims_convergence"]],
        },
        "corrections": [],
    }

    # ── 정정 목록 (파일은 안 고친다 — 어디를 무엇으로 고칠지만 적는다) ──────
    ac0 = regA["ac_power_db__excl_el0"]
    OUT["corrections"] = [
        dict(where="docs/NEXT_EXPERIMENTS.md:22 (①TL;DR)",
             old="요동(AC)은 광선을 4 배 할 때마다 +3 dB 로 전혀 안 수렴했다",
             new=f"요동(AC)은 광선을 4 배 할 때마다 "
                 f"{2 * ac0['slope_db_per_octave']:+.1f} dB "
                 f"(95 % CI {2 * ac0['ci95'][0]:+.1f}~{2 * ac0['ci95'][1]:+.1f}) 로 "
                 f"오르며 수렴하지 않았다 — ⭐다만 그 상승은 **날개끝 상한 아래**에서만 "
                 f"일어난다. 상한 **위**(바닥·빗살)는 예산에 불변이다"
                 f"(바닥 {fa['slope_db_per_octave']:+.2f} · "
                 f"빗살 {ca['slope_db_per_octave']:+.2f} dB/옥타브). "
                 f"그리고 40 m 사다리(8 계단·시드 재현)에서는 AC 조차 평평하다"
                 f"({regB['ac_power_db']['slope_db_per_octave']:+.2f} dB/옥타브) — "
                 f"거기서 오르는 것은 DC 뿐이다"
                 f"({regB['dc_power_db']['slope_db_per_octave']:+.2f}).",
             why_ko="크기(+3 dB/4배)는 맞다. 틀린 것은 **귀속**이다 — 그 상승은 "
                    "마이크로도플러가 자라는 것이 아니라 상한 아래 에코가 자라는 것이고, "
                    "구조가 사는 자리(상한 위)는 360 배를 부어도 안 움직인다."),
        dict(where="docs/NEXT_EXPERIMENTS.md:37 (순위 표 R17 판정 기준)",
             old="①성립·②불변 ⇒ 「구조 없음」이 아니라 「이 예산의 MC 바닥 위로는 구조가 "
                 "없다」로 문장을 고친다",
             new="①은 **불성립**이다 — 상한 위 바닥은 1/spp 를 안 따라간다(내려가지 않고 "
                 "평평하다). 그러므로 「MC 바닥」이라는 이름을 쓸 수 없다. 옳은 문장은 "
                 "「상한 위 내용물은 광선 수에 **불변**이다 — 더 사도 바닥이 안 내려가고 "
                 "구조도 안 생긴다」다.",
             why_ko="바닥의 회귀 기울기가 0 을 덮고 −3.01 을 안 덮는다(두 사다리 모두)."),
        dict(where="docs/RESUME.md:158",
             old="레벨은 360 배 예산에 0.03 dB 안에서 같은데(수렴) 박자는 헤맨다 — "
                 "«수렴했는데 틀렸다».",
             new="**정지 성분(DC) 레벨**은 360 배 예산에 0.03 dB 안에서 같은데(수렴) "
                 "박자는 헤맨다 — «수렴했는데 틀렸다». ⚠그 수렴은 **el 0 의 DC 한 칸**이다. "
                 "같은 360 배에서 DC 제거 AC 는 el 0 에서 "
                 f"{span('ac_power_db', 0.0):+.1f} dB 움직인다.",
             why_ko="「수렴」이 마이크로도플러까지 덮는 말로 재인용되는 것을 막는다."),
        dict(where="reports/16_elevation-coverage.ipynb 절 5 · reports/_parts/"
                   "87_budget-not-physics.ipynb · reports/README.md:212 · reports/01_map.ipynb:274",
             old="el 0 에서 광선을 360 배 늘리면 정지 성분은 0.03 dB 안에 모이고, 같은 한 "
                 "계단이 el −75 의 레벨을 12.55 dB 옮긴다",
             new="(문장 자체는 맞다 — 정지 성분으로 한정돼 있다) ⭐**한 줄 덧붙임**: "
                 "같은 360 배에서 DC 제거 AC 는 el 0 에서 "
                 f"{span('ac_power_db', 0.0):+.1f} dB 오른다. 정지 성분의 수렴은 "
                 "마이크로도플러의 수렴이 아니다.",
             why_ko="원문은 틀리지 않았지만, 이 문장이 덱·요약에서 «예산은 충분하다» 로 "
                    "번역돼 재인용되는 경로를 막는다."),
        dict(where="benchmark/verify_el0_acdc_lens3.py 의 verdict_ko "
                   "(outputs/verify_el0_acdc_lens3.json)",
             old="표본화 잡음이다. 250 M 이상에서 변동 스펙트럼은 백색이고, AC 전력은 경로 "
                 "수에 비례한다. 11.1 M 이 갖고 있던 빗살 구조는 예산을 올리면 사라진다.",
             new="(el 0 에 한해 맞다) ⭐**적용 범위 단서 필요**: 그 백색화는 **el 0 전용**이다. "
                 "el −15·−45·−60 에서는 예산을 4e9 까지 올려도 상한 위 빗살 몫이 "
                 f"{min(head['comb_share_pct'][f'el{el:+.0f}'][-1] for el in els if el != 0):.0f}"
                 f"~{max(head['comb_share_pct'][f'el{el:+.0f}'][-1] for el in els if el != 0):.0f} % "
                 "로 백색 중립값의 6 배 넘게 남는다.",
             why_ko="같은 원장을 절대 전력으로 다시 읽으면 백색화는 정면에서만 일어난다."),
    ]

    json.dump(OUT, open(OUT_JSON, "w"), ensure_ascii=False, indent=1,
              default=lambda o: None if isinstance(o, float) and not np.isfinite(o) else str(o))
    print(f"■ 원장 저장: {OUT_JSON}")

    # ── 화면 요약 ───────────────────────────────────────────────────────
    print("\n" + "=" * 96)
    print("사다리 A — 10 m · 자세 4096 · 깊이 1 · 물리 끔   [절대 dB, DC 제거 후]")
    print("=" * 96)
    print(f"{'el':>4} {'spp':>7} {'경로':>6} | {'①AC':>9} {'DC':>9} "
          f"{'②바닥':>9} {'③빗살':>9} | {'빗살몫%':>8} {'상한아래':>9}")
    for el in els:
        for e, s in LADDER_A:
            c = A["cells"][f"{e}|{el:+.0f}"]
            print(f"{el:>4.0f} {_spp_label(s):>7} {c['npaths_median']:>6} | "
                  f"{c['ac_power_db']:>9.2f} {c['dc_power_db']:>9.2f} "
                  f"{c['floor_above_db']:>9.2f} {c['comb_above_db']:>9.2f} | "
                  f"{c['comb_share_pct']:>8.1f} {c['ac_below_tip_db']:>9.2f}")
        print("-" * 96)
    print(f"\n기울기 [dB / spp 옥타브]  (MC 예측 {DB_PER_OCT_MC:+.2f} · 불변 0)")
    for r in forest:
        ci = r["ci95"]
        print(f"  {r['label']:26s} {r['slope']:+7.3f}  95%CI "
              f"[{ci[0]:+7.3f}, {ci[1]:+7.3f}]" if ci else f"  {r['label']:26s} "
              f"{r['slope']:+7.3f}  CI 없음")
    print(f"\n■ 판정 [{verdict_id}]\n  {verdict_ko}")
    print(f"\n■ 11.1M·수렴 인용 자리 {len(CIT)} 곳 (재인용 금지 표시는 JSON 참조)")
    print(f"■ 소요 {(_dt.datetime.now() - t0).total_seconds():.1f} s")

    # ── 산출물이 실제로 생겼나 (자가검사 마지막) ──────────────────────────
    for p in (OUT_JSON, OUT_FIG, OUT_FIG2):
        if not (os.path.isfile(p) and os.path.getsize(p) > 1024):
            raise SystemExit(f"⛔ 산출물이 없거나 비었다: {p}")
    print("■ 산출물 3 개 확인 완료")
    if hard_fail:
        raise SystemExit(f"⛔ 자가검사 실패: {hard_fail}")


if __name__ == "__main__":
    main()
