# -*- coding: utf-8 -*-
"""
noise_bar_and_gates.py — ⭐판정 막대와 «칸 입장 자격» 을 정본으로 못 박는다
===========================================================================

무엇을 정하나 (2026-08-16, 8/25 팀미팅 본판 설계)
------------------------------------------------
잡음을 얹은 판에서 «몇 미터» 를 내려면 먼저 두 가지가 잠겨야 한다.

  ① **판정 막대** — 얼마를 넘어야 «무늬가 읽힌다» 인가.
     사용자 규칙(docs/MAP_SCALING.md §2-b): 막대는 **판정하는 그 양**을 잡음만 넣고
     여러 번 재서 세운다. 다른 통계량의 막대를 빌려 오면 판정이 뒤집힌다.
     ⇒ 여기서는 헤드라인 잣대인 **빗살 대비**(comb contrast) 의 귀무분포에서
        **p99.9 (Pfa 1e−3)** 를 뽑는다. detection_curves.py 와 같은 Pfa 목표라
        두 원장의 사거리를 나란히 놓을 수 있다.

  ② **칸 입장 자격** — 그 칸이 «몇 미터» 를 낼 자격이 있나.
     원장에는 수치 바닥에 닿은 칸(움직이는 몫이 −100 dB 대)과 광선 추첨으로
     **자세 서너 개**가 전체 요동을 지고 있는 칸이 섞여 있다. 그런 칸의 빗살 대비는
     물리가 아니라 반올림·추첨이다. 그런데 지금은 그 칸들이 다른 칸과 같은 표에
     실려 사다리·연장선을 만든다. ⇒ 게이트를 코드로 못 박는다.

⭐막대는 **두 길로 낸다 — 그리고 서로 검산한다**
------------------------------------------------
  (a) 해석식  빗살 대비는 «빗살 칸 평균 ÷ 빗살 아닌 칸 평균» 이다. 백색 복소 잡음에서
      각 칸 전력은 지수분포이므로 그 비는 **F 분포**를 따른다. 단 한나 창을 쓰면 이웃
      칸이 상관되어 자유도가 줄어든다. 창의 상관은 정확히 계산된다 —
      cov(|X(k)|², |X(l)|²) = |W₂(k−l)|²,  W₂ = DFT(w²) 이고 한나 창은 w² 가
      코사인 두 개뿐이라 **Δ = 0, ±1, ±2 에서만** 0 이 아니다.
        ρ(0)=1 · ρ(±1)=(0.25/0.375)²=0.4444 · ρ(±2)=(0.0625/0.375)²=0.02778
      ⇒ 유효 칸 수 ν = M² / ΣΣρ,  막대 = 10·log10 F_{1−Pfa}(2ν_on, 2ν_off).
      ⭐이 식은 **표본이 필요 없다** — 마스크만 있으면 앙각마다 정확한 값이 나온다.

  (b) 몬테카를로  같은 마스크·같은 창으로 잡음만 N 번 통과시켜 경험 분위수를 뽑는다.
      (a) 와 (b) 가 안 맞으면 둘 중 하나가 틀린 것이다 — 자가검사 3 이 그것을 본다.

  ⚠ **표본 수를 왜 정해야 하나.** p99.9 의 표준오차는 √(p(1−p)/N)/f(x_p) 다.
     N=4,000 이면 ±0.26 dB(95 %), N=20,000 이면 ±0.11 dB — 막대 0.11 dB 는 건강한
     팔에서 판독거리 ±1.4 %, 천장에 붙은 팔(물리 켬)에서 ±4.4 % 다. ⇒ **정본 N = 20,000**
     (scaled_maps.json 이 같은 목적에 쓴 수와 같다).

⭐칸 입장 자격 — 네 개의 게이트
-------------------------------
  G0 온전함        원장 n_missing = 0 이고 0 표본이 없다.
  G1 수치 바닥     움직이는 몫 ac_fraction_db ≥ −60 dB.
                   (−100 dB 대는 배정밀도 반올림이다. 480 m PathSolver 정면 칸은
                    −322 dB 이고 그 «스펙트럼» 은 백색이다.)
  G2 자세 지지     유효 자세 수 ν_eff = (Σp)²/Σp²  (p = 자세별 요동 전력) 가
                   N/100 = 82 자세 이상. 그 아래면 요동을 **자세 서너 개**가 지고 있다.
  G3 자세 집중     상위 8 자세 몫 ≤ 20 %.
  · ν_eff < N/10 = 819 이면 통과시키되 **호박색(sparse)** 으로 표시한다 —
    그 칸의 수는 블록 부트스트랩 구간과 함께만 인용한다.

⛔GPU/솔버 없음 — 저장된 원장만 읽는 CPU 계산(자가검사 1).
⛔기존 파일 수정 없음 — 산출은 outputs/noise_bar_and_gates.json 하나.

실행:
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
  /workspace/.venvs/py312/bin/python benchmark/noise_bar_and_gates.py --mc 20000 --workers 24
  (막대만 해석식으로 빠르게: --mc 0)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 재사용(재발명 금지) — 마스크·통계량·잡음 생성은 잡음 틀 본체의 정의를 그대로 쓴다.
from noise_distance_frame import (make_masks, stats_batch, noise_batch,   # noqa: E402
                                  el_key, HW_HZ, BAND_LO, PFA)

LEDGER_JSON = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LEDGER_NPZ = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
FRAME_JSON = os.path.join(ROOT, "outputs", "noise_distance_frame.json")
OUT_JSON = os.path.join(ROOT, "outputs", "noise_bar_and_gates.json")

SEED = 20260816
ELS = [0.0, -30.0, -60.0]
RANGES = [15, 30, 60, 120, 240, 480]
QUANTS = [0.5, 0.9, 0.95, 0.99, 0.999, 0.9999]

# 게이트 문턱 — 위 docstring 의 근거
G1_AC_FLOOR_DB = -60.0
G2_NU_MIN_FRAC = 0.01        # ν_eff ≥ N/100
G3_TOP8_MAX_PCT = 20.0
AMBER_NU_FRAC = 0.10         # ν_eff < N/10 이면 호박색

# G4 모양 드리프트 허용폭 = 2 × max(그 앙각의 빗살 격자 밴드, 귀무 σ)
#   빗살 격자 밴드: outputs/material_canon_0816.json : metric_protocol.comb_grid_band_db_by_el
#   ⚠el +0 의 밴드 0.105 dB 는 «머리카락 밴드» 라 canon 자신의 규약대로 물리적 뜻을 안 붙인다 —
#     그래서 귀무 σ(잣대 자체의 잡음 요동)로 바닥을 깐다.
COMB_GRID_BAND_DB_BY_EL = {"+0": 0.105, "-15": 4.038, "-30": 4.616, "-45": 4.669, "-60": 4.053}

ARMS = {
    "ours":     dict(pat="ours_r{R}_n8192", label_en="Ours (SBR+PO)"),
    "ours_ptd": dict(pat="ours_ptd_r{R}_n8192", label_en="Ours + PTD"),
    "ps_off":   dict(pat="sionna_p4000000000_r{R}_n8192_d1",
                     label_en="PathSolver all-off (R0D0E0F1)"),
    "ps_refr":  dict(pat="sionna_p4000000000_onlyrefr_r{R}_n8192",
                     label_en="PathSolver refraction-only (R1D0E0F1)"),
    "ps_phys":  dict(pat="sionna_p4000000000_phys_r{R}_n8192_d1",
                     label_en="PathSolver all physics ON"),
}


# --------------------------------------------------------------------------- #
#  (a) 해석식 막대 — 한나 창의 칸 상관까지 정확히
# --------------------------------------------------------------------------- #
def hann_bin_rho(n: int) -> dict:
    """한나 창 주기도의 **칸 사이 상관** ρ(Δ) = |W₂(Δ)|²/|W₂(0)|², W₂ = DFT(w²).

    w = 0.5(1−cos) ⇒ w² = 0.375 − 0.5cos + 0.125cos2 이므로 Δ = 0,±1,±2 에서만 산다."""
    w2 = np.hanning(n) ** 2
    W2 = np.abs(np.fft.fft(w2)) ** 2
    W2 = W2 / W2[0]
    return {0: 1.0, 1: float(W2[1]), 2: float(W2[2]), 3: float(W2[3])}


def effective_bins(mask: np.ndarray, rho: dict) -> float:
    """마스크가 고르는 칸들의 **유효(독립) 개수** ν = M² / ΣΣρ(|i−j|).

    ⭐가정 없이 마스크 자체에서 센다 — 빗살 이 하나가 몇 칸을 덮는지, 대역 끝에서 잘리는지가
    자동으로 들어간다. 켤레 칸(+f ↔ −f)은 복소 잡음이라 독립이고, 인덱스 차가 커서 ρ=0 이다."""
    idx = np.flatnonzero(np.asarray(mask, bool)).astype(np.int64)
    M = idx.size
    if M == 0:
        raise ValueError("빈 마스크")
    d = np.abs(idx[:, None] - idx[None, :])
    S = float(np.sum([np.count_nonzero(d == k) * rho.get(int(k), 0.0)
                      for k in range(0, 4)]))
    return float(M * M / S)


def analytic_bar(mask_on, mask_off, n: int, quants=QUANTS) -> dict:
    rho = hann_bin_rho(n)
    nu_on, nu_off = effective_bins(mask_on, rho), effective_bins(mask_off, rho)
    C = 10.0 / math.log(10.0)
    sd = C * math.sqrt(stats.gamma(a=nu_on).std() ** 0)      # 자리표시(아래에서 정확히)
    from scipy.special import polygamma, digamma
    sd = C * math.sqrt(polygamma(1, nu_on) + polygamma(1, nu_off))
    mu = C * (digamma(nu_on) - math.log(nu_on) - digamma(nu_off) + math.log(nu_off))
    F = stats.f(2 * nu_on, 2 * nu_off)
    q = {f"p{100 * p:g}": float(10.0 * math.log10(F.ppf(p))) for p in quants}
    # 분위수 표준오차(표본 N 마다) — 표본 수 결정 근거
    se = {}
    for p in (0.99, 0.999):
        xq = F.ppf(p)
        f_db = float(F.pdf(xq) * xq * math.log(10.0) / 10.0)   # dB 축 밀도
        se[f"p{100 * p:g}"] = {str(N): round(math.sqrt(p * (1 - p) / N) / f_db, 4)
                               for N in (4000, 20000, 60000)}
    return dict(M_on=int(np.count_nonzero(mask_on)), M_off=int(np.count_nonzero(mask_off)),
                nu_on=round(nu_on, 3), nu_off=round(nu_off, 3),
                var_inflation_on=round(np.count_nonzero(mask_on) / nu_on, 4),
                mean_db=round(mu, 4), sd_db=round(sd, 4),
                quantiles_db={k: round(v, 4) for k, v in q.items()},
                quantile_se_db_by_N=se,
                bar_db=round(float(10.0 * math.log10(F.ppf(1.0 - PFA))), 4),
                rho_hann={str(k): round(v, 6) for k, v in rho.items()})


# --------------------------------------------------------------------------- #
#  (b) 몬테카를로 막대
# --------------------------------------------------------------------------- #
_W = {}


def _mc_chunk(args):
    """잡음 **전용** 조각 — 신호는 인자에도 없다(문턱 누설 원천 차단)."""
    seed, n_trial, n, ftips, prf, f_flash = args
    rng = np.random.default_rng(seed)
    w = np.hanning(n)
    masks = {el: make_masks(n, prf, ft, f_flash) for el, ft in ftips.items()}
    out = {el: {"comb_db": [], "rhythm_pct": []} for el in masks}
    done = 0
    while done < n_trial:
        mb = min(250, n_trial - done)
        Z = noise_batch(rng, mb, n)
        for el, mk in masks.items():
            s = stats_batch(Z, w, mk)
            out[el]["comb_db"].append(s["comb_db"])
            out[el]["rhythm_pct"].append(s["rhythm_pct"])
        done += mb
    return {el: {k: np.concatenate(v) for k, v in d.items()} for el, d in out.items()}


def run_mc(n_trial: int, n: int, ftips: dict, prf: float, f_flash: float,
           workers: int) -> dict:
    if n_trial <= 0:
        return {}
    per = max(1, math.ceil(n_trial / workers))
    jobs = [(SEED + 1000 * i, min(per, n_trial - i * per), n, ftips, prf, f_flash)
            for i in range(workers) if n_trial - i * per > 0]
    with ProcessPoolExecutor(max_workers=len(jobs)) as ex:
        parts = list(ex.map(_mc_chunk, jobs))
    merged = {}
    for el in ftips:
        merged[el] = {k: np.concatenate([p[el][k] for p in parts])
                      for k in ("comb_db", "rhythm_pct")}
    return merged


def empirical(v: np.ndarray, n_boot: int, rng) -> dict:
    q = {f"p{100 * p:g}": float(np.quantile(v, p)) for p in QUANTS}
    bar = float(np.quantile(v, 1.0 - PFA))
    idx = rng.integers(0, v.size, size=(n_boot, v.size))
    bs = np.quantile(v[idx], 1.0 - PFA, axis=1)
    return dict(n=int(v.size), mean_db=round(float(v.mean()), 4),
                sd_db=round(float(v.std()), 4),
                quantiles_db={k: round(x, 4) for k, x in q.items()},
                bar_db=round(bar, 4),
                bar_ci95_db=[round(float(np.quantile(bs, 0.025)), 4),
                             round(float(np.quantile(bs, 0.975)), 4)],
                bar_boot_se_db=round(float(bs.std()), 4))


# --------------------------------------------------------------------------- #
#  칸 입장 자격
# --------------------------------------------------------------------------- #
def cell_gate(E: np.ndarray, n_missing: int, w, mk: dict) -> dict:
    n = E.size
    A = E - E.mean()
    p = np.abs(A) ** 2
    tot = float(np.mean(np.abs(E) ** 2))
    ac = float(np.mean(p))
    nu_eff = float((p.sum() ** 2) / np.sum(p ** 2)) if p.sum() > 0 else 0.0
    top8 = float(100.0 * np.sort(p)[-8:].sum() / p.sum()) if p.sum() > 0 else 100.0
    ac_db = 10.0 * math.log10(ac / tot) if (ac > 0 and tot > 0) else -400.0
    s = stats_batch(E[None, :], w, mk)
    zeros = int(np.count_nonzero(E == 0))
    reasons = []
    if n_missing or zeros:
        reasons.append("G0_incomplete")
    if ac_db < G1_AC_FLOOR_DB:
        reasons.append("G1_numeric_floor")
    if nu_eff < G2_NU_MIN_FRAC * n:
        reasons.append("G2_pose_support")
    if top8 > G3_TOP8_MAX_PCT:
        reasons.append("G3_pose_concentration")
    verdict = "reject" if reasons else (
        "admit_sparse" if nu_eff < AMBER_NU_FRAC * n else "admit")
    return dict(verdict=verdict, reject_reasons=reasons,
                may_claim=dict(
                    distance=bool(verdict != "reject"),
                    absence=True,
                    note_ko="⭐게이트는 «몇 미터» 를 지킨다 — «여기엔 무늬가 없다» 는 "
                            "부정 주장은 탈락한 칸으로도 할 수 있다(사유를 함께 적는다)"),
                n_missing=int(n_missing), n_zero=zeros,
                ac_fraction_db=round(ac_db, 2), nu_eff_poses=round(nu_eff, 1),
                nu_eff_pct=round(100.0 * nu_eff / n, 2), top8_pose_pct=round(top8, 2),
                peak_over_median_db=round(
                    10 * math.log10(float(p.max() / max(np.median(p), 1e-300))), 1),
                clean_comb_contrast_db=round(float(s["comb_db"][0]), 2),
                clean_rhythm_share_pct=round(float(s["rhythm_pct"][0]), 1))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mc", type=int, default=20000, help="귀무 몬테카를로 시행 수(0=해석식만)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--boot", type=int, default=400)
    ap.add_argument("--out", default=OUT_JSON)
    a = ap.parse_args()
    t0 = time.time()

    led = json.load(open(LEDGER_JSON))
    z = np.load(LEDGER_NPZ)
    rows = {(r["engine"], float(r["el_deg"])): r for r in led["rows"]}
    prf = float(led["_meta"]["prf_hz"])
    f_flash = float(led["_meta"]["f_flash_hz"])
    n = 8192
    w = np.hanning(n)

    # ⚠원장에는 다른 기체·다른 반송파 팔이 함께 산다 — f_tip 은 **이 프레임의 팔들**에서만 센다
    frame_engines = {spec["pat"].format(R=R) for spec in ARMS.values() for R in RANGES}
    ftips, fcs = {}, set()
    for el in ELS:
        got = {float(r["f_tip_hz"]) for (e, ee), r in rows.items()
               if ee == el and e in frame_engines and f"{e}/{el_key(el)}" in z.files}
        got = {v for v in got if v > 0}
        if len(got) != 1:
            raise ValueError(f"el={el}: 프레임 팔 안에서 f_tip 불일치 {sorted(got)[:5]}")
        ftips[el] = got.pop()
        fcs |= {float(r["fc_hz"]) for (e, ee), r in rows.items()
                if ee == el and e in frame_engines and f"{e}/{el_key(el)}" in z.files}
    if len(fcs) != 1:
        raise ValueError(f"프레임 팔 안에서 반송파가 섞였다 {sorted(fcs)}")
    masks = {el: make_masks(n, prf, ft, f_flash) for el, ft in ftips.items()}

    # --- 막대 (a) 해석식 ------------------------------------------------------ #
    ana = {f"{el:+.0f}": analytic_bar(masks[el]["comb_on"], masks[el]["comb_off"], n)
           for el in ELS}

    # --- 막대 (b) 몬테카를로 -------------------------------------------------- #
    rng = np.random.default_rng(SEED + 7)
    mc = run_mc(a.mc, n, ftips, prf, f_flash, a.workers)
    emp = {f"{el:+.0f}": dict(
        comb_contrast_db=empirical(mc[el]["comb_db"], a.boot, rng),
        rhythm_share_pct=empirical(mc[el]["rhythm_pct"], a.boot, rng),
        rhythm_null_analytic_pct=round(masks[el]["rhythm_null_pct"], 2))
        for el in ELS} if mc else {}

    # --- 칸 입장 자격 --------------------------------------------------------- #
    gates, admitted = {}, {}
    for arm, spec in ARMS.items():
        for el in ELS:
            for R in RANGES:
                eng = spec["pat"].format(R=R)
                key = f"{eng}/{el_key(el)}"
                if key not in z.files or (eng, el) not in rows:
                    continue
                row = rows[(eng, el)]
                g = cell_gate(np.asarray(z[key], complex),
                              int(row.get("n_missing") or 0), w, masks[el])
                cid = f"{arm}_r{R}_el{int(el):+d}"
                gates[cid] = dict(arm=arm, range_m=R, el_deg=el, engine=eng,
                                  npz_key=key, engine_level_db=float(row["level_db"]),
                                  **g)
                if g["verdict"] != "reject":
                    admitted.setdefault(f"{arm}_el{int(el):+d}", []).append(R)

    # --- G4 모양 드리프트 — 15 m 판 대비. 연장선(A1)을 어디까지 믿나 ------------ #
    drift = {}
    for arm in ARMS:
        for el in ELS:
            ek = f"{el:+.0f}"
            base = gates.get(f"{arm}_r15_el{int(el):+d}")
            if base is None or base["verdict"] == "reject":
                continue
            tol = 2.0 * max(COMB_GRID_BAND_DB_BY_EL.get(ek, 4.0),
                            (emp[ek]["comb_contrast_db"]["sd_db"] if emp
                             else ana[ek]["sd_db"]))
            rowsd = {}
            for R in RANGES:
                c = gates.get(f"{arm}_r{R}_el{int(el):+d}")
                if c is None or c["verdict"] == "reject":
                    continue
                d = c["clean_comb_contrast_db"] - base["clean_comb_contrast_db"]
                rowsd[str(R)] = round(d, 2)
                gates[f"{arm}_r{R}_el{int(el):+d}"]["shape_drift_vs_15m_db"] = round(d, 2)
                if abs(d) > tol:
                    gates[f"{arm}_r{R}_el{int(el):+d}"].setdefault("flags", []).append(
                        "G4_shape_drift")
            mx = max((abs(v) for v in rowsd.values()), default=0.0)
            drift[f"{arm}_el{int(el):+d}"] = dict(
                drift_db=rowsd, max_abs_drift_db=round(mx, 2), tol_db=round(tol, 2),
                trust_A1=bool(mx <= tol),
                note_ko="A1(15 m 모양을 얼린 연장선)을 그대로 인용해도 되나 — "
                        "드리프트가 허용폭을 넘으면 «기울기만» 으로 읽는다")

    # --- 자가검사 ------------------------------------------------------------- #
    st = {}
    st["1_no_gpu_import"] = dict(
        ok=not any(m.startswith(("sionna", "mitsuba", "drjit")) for m in sys.modules),
        loaded=[m for m in sys.modules if m.startswith(("sionna", "mitsuba", "drjit"))])
    # 2. 해석식 표준편차가 **기존 원장의 실측 귀무 σ**(N=4000) 와 맞나
    fr = json.load(open(FRAME_JSON))
    n2 = []
    for k, v in fr["null_control"].items():
        if k not in ana:
            continue
        meas = v["comb_contrast_db"]["std"]
        pred = ana[k]["sd_db"]
        # N=4000 에서 σ 자체의 상대 오차는 1/√(2N) ≈ 1.1 % — 3 % 를 허용폭으로 둔다
        n2.append(dict(el=k, measured_sd=round(meas, 4), analytic_sd=pred,
                       rel_err_pct=round(100 * (pred - meas) / meas, 2),
                       ok=bool(abs(pred - meas) / meas < 0.03)))
    st["2_analytic_sd_matches_stored_null"] = dict(ok=all(r["ok"] for r in n2), rows=n2)
    # 3. 해석식 막대 ↔ 몬테카를로 막대
    n3 = []
    for k in ana:
        if not emp:
            break
        e = emp[k]["comb_contrast_db"]
        d = e["bar_db"] - ana[k]["bar_db"]
        tol = max(0.15, 2.0 * e["bar_boot_se_db"])
        n3.append(dict(el=k, analytic=ana[k]["bar_db"], mc=e["bar_db"],
                       diff_db=round(d, 4), tol_db=round(tol, 4),
                       ok=bool(abs(d) <= tol)))
    st["3_analytic_vs_mc_bar"] = dict(ok=(all(r["ok"] for r in n3) if n3 else None),
                                      rows=n3, n_mc=a.mc)
    # 4. 귀무 평균 ≈ 0 dB (빗살 대비의 정의상)
    n4 = [dict(el=k, mean_db=ana[k]["mean_db"], ok=bool(abs(ana[k]["mean_db"]) < 0.05))
          for k in ana]
    st["4_null_mean_is_zero"] = dict(ok=all(r["ok"] for r in n4), rows=n4)
    # 5. 게이트가 알려진 쓰레기 칸을 실제로 막나
    known_bad = ["ps_phys_r120_el-30", "ps_off_r480_el-30", "ps_off_r240_el+0",
                 "ps_off_r480_el+0", "ps_refr_r120_el+0"]
    n5 = [dict(cell=c, present=c in gates,
               verdict=gates.get(c, {}).get("verdict"),
               reasons=gates.get(c, {}).get("reject_reasons"),
               ok=bool(c not in gates or gates[c]["verdict"] == "reject"))
          for c in known_bad]
    st["5_gates_catch_known_bad"] = dict(ok=all(r["ok"] for r in n5), rows=n5)
    # 6. 마스크 위생 — on/off 가 겹치지 않고 각각 4 칸 이상
    n6 = []
    for el in ELS:
        mk = masks[el]
        n6.append(dict(el=f"{el:+.0f}", overlap=int(np.count_nonzero(
            mk["comb_on"] & mk["comb_off"])), n_on=mk["n_comb_on"],
            n_off=mk["n_comb_off"],
            ok=bool(not np.any(mk["comb_on"] & mk["comb_off"])
                    and mk["n_comb_on"] >= 4 and mk["n_comb_off"] >= 4)))
    st["6_mask_hygiene"] = dict(ok=all(r["ok"] for r in n6), rows=n6)
    st["ok"] = all(v.get("ok") for v in st.values()
                   if isinstance(v, dict) and v.get("ok") is not None)

    out = dict(
        _meta=dict(
            generator="benchmark/noise_bar_and_gates.py",
            generated_kst=time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(time.time() + 9 * 3600)) + " (UTC+9)",
            purpose_ko="① 빗살 대비의 귀무분포 p99.9 판정 막대(해석식+몬테카를로) "
                       "② 칸이 «몇 미터» 를 낼 자격이 있는지의 게이트",
            rule_ko="막대는 **판정하는 그 양**의 귀무분포에서 세운다(docs/MAP_SCALING.md §2-b). "
                    "다른 통계량의 막대를 빌려 오면 판정이 뒤집힌다",
            inputs=[os.path.relpath(p, ROOT) for p in (LEDGER_JSON, LEDGER_NPZ, FRAME_JSON)],
            reused_code=["benchmark/noise_distance_frame.py (make_masks·stats_batch·noise_batch)"],
            gpu_ko="⛔GPU/솔버 호출 없음 — 저장된 원장만 읽는 CPU 계산(자가검사 1)",
            pfa=PFA, hw_hz=HW_HZ, band_lo_frac=BAND_LO, prf_hz=prf, f_flash_hz=f_flash,
            n_slow=n, f_tip_hz_by_el={f"{el:+.0f}": v for el, v in ftips.items()},
            seed=SEED, n_mc=a.mc, n_boot=a.boot,
            gates_ko=dict(
                G0="원장 n_missing = 0 · 0 표본 없음",
                G1=f"ac_fraction_db ≥ {G1_AC_FLOOR_DB} dB (아래는 배정밀도 반올림)",
                G2=f"유효 자세 수 ν_eff ≥ N/{int(1 / G2_NU_MIN_FRAC)} = "
                   f"{int(G2_NU_MIN_FRAC * n)} 자세",
                G3=f"상위 8 자세 몫 ≤ {G3_TOP8_MAX_PCT} %",
                amber=f"ν_eff < N/{int(1 / AMBER_NU_FRAC)} = {int(AMBER_NU_FRAC * n)} 이면 "
                      f"통과시키되 호박색 — 블록 부트스트랩 구간과 함께만 인용",
                threshold_provenance_ko="⚠문턱은 원장의 ν_eff 분포를 **보고** 정했다(사후). "
                                        "그 사실을 숨기지 않는다 — 건강한 칸은 ν_eff 2,000~4,200 "
                                        "(24~51 %), 쓰레기 칸은 3~10 자세로 두 무리가 두 자릿수 "
                                        "떨어져 있어 1 %/10 % 선의 위치에 결론이 민감하지 않다. "
                                        "⭐단 ps_phys 15 m el −30 은 ν_eff 180(2.2 %)로 두 선 "
                                        "사이에 있다 — 그래서 «호박색» 등급을 따로 둔다"),
            method_bar_ko="(a) 해석식: 빗살 대비는 F 분포 — 한나 창의 칸 상관 "
                          "ρ = |DFT(w²)|² 로 유효 칸 수 ν = M²/ΣΣρ 를 세고 "
                          "막대 = 10log10 F_{1−Pfa}(2ν_on, 2ν_off). "
                          "(b) 몬테카를로: 같은 마스크·같은 창으로 잡음만 N 번. "
                          "⭐둘이 안 맞으면 하나가 틀린 것이다(자가검사 3)"),
        analytic_bar=ana,
        mc_bar=emp,
        cell_gates=gates,
        admitted_ranges_by_arm_el=admitted,
        shape_drift_A1=drift,
        selftest=st)
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {a.out}")
    print(json.dumps(dict(
        selftest_ok=st["ok"],
        bar_db={k: ana[k]["bar_db"] for k in ana},
        mc_bar_db={k: emp[k]["comb_contrast_db"]["bar_db"] for k in emp},
        rejected=[c for c, g in gates.items() if g["verdict"] == "reject"],
        sparse=[c for c, g in gates.items() if g["verdict"] == "admit_sparse"]),
        ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
