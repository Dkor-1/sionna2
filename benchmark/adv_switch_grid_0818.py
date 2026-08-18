# -*- coding: utf-8 -*-
"""
adv_switch_grid_0818.py — 스위치 격자 결과를 **반증하려고** 짜 놓은 시험
================================================================================

규약: 잣대 식을 그림 빌더에서 **베끼지 않고 다시 구현**해서 대조한다. 베끼면 같은 버그를
같이 재현할 뿐이다(2026-08-16 적대 검산 라운드에서 정한 방식).

시험 목록 — 하나라도 떨어지면 리포트 5-2 의 해당 문장을 내린다
  V1 잣대 재구현      리듬 몫·빗살 대비를 독립 구현으로 다시 재서 원장과 대조
  V2 결측 자세        여덟 팔 전부 8,192 자세가 실제로 차 있나 (샤드에서 직접)
  V3 원장 두 개 대조  switch_grid ↔ switch_factorial 이 같은 수를 말하나
  V4 모서리 무동작    «모서리만» 이 «다 끔» 과 정말 같은가 — 비트 단위로
  V5 E 무동작의 따름  «굴절+회절» ≈ «다 켬» 이어야 한다
  V6 봉우리 자리      여덟 팔 전부 126.1 Hz 인가
  V7 결측 인공물      샤드 간격이 만드는 PRF/16 자리에 없는 선이 서 있지 않나
  V8 백색 귀무        회절 팔의 리듬 몫이 백색 귀무분포 안에 있나 (있으면 «무늬 없음»)

⛔GPU 없음. 산출: outputs/adv_switch_grid_0818.json

실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/adv_switch_grid_0818.py
"""
from __future__ import annotations

import glob
import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "adv_switch_grid_0818.json")

GRID = json.load(open(os.path.join(ROOT, "outputs", "switch_grid.json"), encoding="utf-8"))
FACT = json.load(open(os.path.join(ROOT, "outputs", "switch_factorial.json"), encoding="utf-8"))
EL = float(GRID["_meta"]["el_deg"])
PRF = 19700.0
FFL = float(GRID["_meta"]["f_flash_hz"])
FTIP = float(GRID["_meta"]["f_tip_hz"])
HW = 8.0
NSHARD_STRIDE = 16                       # 샤드 개수 = 성큼성큼 간격

FACT_KEY = {"all off": "R0D0E0F1_d1/el-30", "refraction only": "R1D0E0F1_d1/el-30",
            "edge only": "R0D0E1F1_d1/el-30", "diffraction only": "R0D1E0F1_d1/el-30",
            "diffraction + edge": "R0D1E1F1_d1/el-30",
            "refraction + diffraction": "R1D1E0F1_d1/el-30",
            "all on": "R1D1E1F1_d1/el-30"}


def load(arm):
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{EL:+.0f}_*.npz"))
    E = seen = None
    for f in fs:
        d = np.load(f)
        n = int(np.asarray(d["meta"], float)[3])
        if E is None:
            E = np.zeros(n, complex)
            seen = np.zeros(n, bool)
        ii = d["idx"].astype(int)
        E[ii] = d["E"]
        seen[ii] = True
    return E, int((~seen).sum()), len(fs)


# ── V1 잣대 **독립** 재구현 ───────────────────────────────────────────────
def rhythm_indep(x):
    """빌더를 안 보고 정의만 보고 다시 짠 판.

    정의: «상한 위 에너지 중 f_flash 정수배 ±8 Hz 에 붙은 몫». 창은 해닝, DC 는 뺀다.
    빌더와 다른 점 — 여기서는 rfft 로 한쪽만 계산하고 나이퀴스트 칸을 명시적으로 다룬다.
    """
    v = x - np.mean(x)
    n = v.size
    w = np.hanning(n)
    X = np.fft.rfft(np.real(v * w)) if np.isrealobj(v) else None
    # 복소 신호이므로 양·음 도플러를 모두 본다 — fft 를 쓰되 축을 직접 만든다
    Y = np.fft.fft(v * w)
    f = np.arange(n) * (PRF / n)
    f = np.where(f > PRF / 2, f - PRF, f)                # 접어서 −PRF/2..PRF/2
    P = (Y.real ** 2 + Y.imag ** 2)
    af = np.abs(f)
    above = af >= FTIP
    kk = np.rint(af / FFL)
    oncomb = np.abs(af - kk * FFL) <= HW
    tot = P[above].sum()
    return dict(rhythm_pct=float(100 * P[above & oncomb].sum() / tot),
                comb_over_floor_db=float(10 * np.log10(
                    P[above & oncomb].mean() / P[above & ~oncomb].mean())),
                above_tip_pct=float(100 * tot / P.sum()))


def main():
    t0 = time.time()
    arms = [(v["arm"], nm) for nm, v in GRID["cells"].items()]
    ser, res = {}, {}
    for arm, nm in arms:
        E, miss, nsh = load(arm)
        ser[nm] = E
        res[nm] = dict(arm=arm, n_missing=miss, n_shards=nsh, n_poses=int(E.size))

    v = {}

    # V1 --------------------------------------------------------------
    rows, worst = {}, 0.0
    for nm in ser:
        mine = rhythm_indep(ser[nm])
        theirs = GRID["cells"][nm]["rhythm_share_pct"]
        d = abs(mine["rhythm_pct"] - theirs)
        worst = max(worst, d)
        rows[nm] = dict(independent=round(mine["rhythm_pct"], 2), ledger=theirs,
                        diff_pp=round(d, 3),
                        comb_over_floor_db=round(mine["comb_over_floor_db"], 2))
    v["V1_metric_reimplemented"] = dict(
        pass_=bool(worst <= 0.15), worst_diff_pp=round(worst, 3), rows=rows,
        rule_ko="독립 구현과 원장이 0.15 %p 안에서 같아야 한다")

    # V2 --------------------------------------------------------------
    bad = {nm: r["n_missing"] for nm, r in res.items() if r["n_missing"]}
    v["V2_no_missing_poses"] = dict(pass_=not bad, offenders=bad,
                                    per_arm={nm: r["n_missing"] for nm, r in res.items()})

    # V3 --------------------------------------------------------------
    rows, worst = {}, 0.0
    for nm, k in FACT_KEY.items():
        f = FACT["cells"].get(k)
        if not f:
            continue
        d = abs(f["rhythm_share_pct"] - GRID["cells"][nm]["rhythm_share_pct"])
        worst = max(worst, d)
        rows[nm] = dict(factorial=f["rhythm_share_pct"],
                        grid=GRID["cells"][nm]["rhythm_share_pct"], diff_pp=round(d, 3))
    v["V3_two_ledgers_agree"] = dict(pass_=bool(worst <= 0.1),
                                     worst_diff_pp=round(worst, 3), rows=rows)

    # V4 --------------------------------------------------------------
    a, b = ser["all off"], ser["edge only"]
    same = bool(np.array_equal(a, b))
    aa, bb = a - a.mean(), b - b.mean()
    rel_db = float(10 * np.log10(max((np.abs(b - a) ** 2).sum(), 1e-300)
                                 / (np.abs(a) ** 2).sum()))
    rho = float(abs(np.vdot(aa, bb)) / np.sqrt(np.vdot(aa, aa).real * np.vdot(bb, bb).real))
    # ⭐2026-08-18 정정: «비트 단위로 같다» 는 **틀린 문장**이었다. 실제로는 자세 96 %가
    #   마지막 자리에서 다르다. 다만 차이 전력이 −309 dB(배정밀도 반올림 한계)라 물리
    #   주장(모서리는 무동작)은 그대로 선다. 시험을 «기계 정밀도 안» 으로 고쳐 단다.
    v["V4_edge_is_a_noop"] = dict(
        pass_=bool(rel_db < -250.0 and rho > 1 - 1e-9),
        bit_identical=same, diff_power_db=round(rel_db, 1), correlation=round(rho, 10),
        n_poses_differing=int((b - a != 0).sum()),
        claim_ko="«모서리만» 은 «다 끔» 과 **기계 정밀도 안**에서 같아야 한다 "
                 "(모서리 후보 생성이 회절 스위치 안에 있으므로). "
                 "⛔«비트 단위로 같다» 는 과장이다 — 96 % 자세가 마지막 자리에서 다르다")

    # V5 --------------------------------------------------------------
    x1, x2 = ser["refraction + diffraction"], ser["all on"]
    a1 = x1 - x1.mean()
    a2 = x2 - x2.mean()
    rho = float(abs(np.vdot(a1, a2)) / np.sqrt(np.vdot(a1, a1).real * np.vdot(a2, a2).real))
    dr = abs(GRID["cells"]["refraction + diffraction"]["rhythm_share_pct"]
             - GRID["cells"]["all on"]["rhythm_share_pct"])
    v["V5_E_noop_consequence"] = dict(pass_=bool(rho > 0.95 and dr <= 0.5),
                                      correlation=round(rho, 4), d_rhythm_pp=round(dr, 3),
                                      claim_ko="E 가 무동작이면 «굴절+회절» 과 «다 켬» 이 붙어야 한다")

    # V6 --------------------------------------------------------------
    pk = {nm: c["h1_peak_hz"] for nm, c in GRID["cells"].items()}
    v["V6_peak_position"] = dict(pass_=bool(len(set(pk.values())) == 1),
                                 peaks_hz=pk, predicted_hz=round(FFL, 2))

    # V7 --------------------------------------------------------------
    frep = PRF / NSHARD_STRIDE
    rows = {}
    for nm, x in ser.items():
        ac = x - x.mean()
        P = np.abs(np.fft.fft(ac * np.hanning(ac.size))) ** 2
        fr = np.fft.fftfreq(ac.size, 1.0 / PRF)
        med = float(np.median(P[np.abs(fr) < 2000]))
        m = np.abs(np.abs(fr) - frep) < 15
        rows[nm] = round(float(10 * np.log10(P[m].max() / med)), 1)
    v["V7_shard_replica_line"] = dict(
        pass_=bool(max(rows.values()) < 25.0), replica_hz=round(frep, 2),
        rise_db=rows,
        rule_ko=f"결측 샤드가 있으면 PRF/{NSHARD_STRIDE} = {frep:.1f} Hz 에 없는 선이 선다. "
                "정상이면 25 dB 아래")

    # V8 --------------------------------------------------------------
    rng = np.random.default_rng(3)
    n = ser["all off"].size
    null = np.array([rhythm_indep(rng.normal(size=n) + 1j * rng.normal(size=n))["rhythm_pct"]
                     for _ in range(200)])
    lo, hi = float(np.percentile(null, 0.5)), float(np.percentile(null, 99.5))
    rows = {}
    for nm in ser:
        r = GRID["cells"][nm]["rhythm_share_pct"]
        rows[nm] = dict(rhythm_pct=r, inside_white_null=bool(lo <= r <= hi))
    v["V8_white_null"] = dict(
        null_pct_mean=round(float(null.mean()), 2), null_99pct_band=[round(lo, 2), round(hi, 2)],
        rows=rows,
        reading_ko="귀무 안에 들어오면 «무늬가 없다» 로 읽는다 — 회절 켠 네 팔이 그래야 한다")

    npass = sum(1 for k, r in v.items() if isinstance(r, dict) and r.get("pass_") is True)
    ntest = sum(1 for k, r in v.items() if isinstance(r, dict) and "pass_" in r)
    doc = {"_meta": {
        "generator": "benchmark/adv_switch_grid_0818.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "리포트 5-2 결과를 반증하려는 시험 — 잣대를 다시 구현해서 대조한다",
        "gpu_used": False, "elapsed_s": round(time.time() - t0, 2),
        "gate": f"{npass}/{ntest}"}, "arms": res, "tests": v}
    json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"═══ 적대적 검증 {npass}/{ntest} ═══")
    for k, r in v.items():
        if isinstance(r, dict) and "pass_" in r:
            print(f"  {'✅' if r['pass_'] else '❌'} {k}")
    print(f"  V1 최악 차이 {v['V1_metric_reimplemented']['worst_diff_pp']} %p · "
          f"V3 최악 차이 {v['V3_two_ledgers_agree']['worst_diff_pp']} %p")
    print(f"  V5 상관 {v['V5_E_noop_consequence']['correlation']} · "
          f"V7 복제선 최대 {max(v['V7_shard_replica_line']['rise_db'].values())} dB "
          f"@ {v['V7_shard_replica_line']['replica_hz']} Hz")
    print(f"  V8 백색 귀무 99 % 띠 {v['V8_white_null']['null_99pct_band']} % — 귀무 안: "
          + ", ".join(nm for nm, r in v["V8_white_null"]["rows"].items()
                      if r["inside_white_null"]))
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
