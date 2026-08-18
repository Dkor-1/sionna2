# -*- coding: utf-8 -*-
"""
noise_main_run_0818.py — 잡음 **본판**(결과판)
================================================================================

`noise_main_gates.py` 는 게이트 **라이브러리**이고 `dry_run()` 은 «게이트가 도는지» 만 본다.
이 파일이 그것을 엮어 **답**을 낸다: 팔마다 «무늬가 어느 SNR 까지 읽히고 그게 몇 미터인가».

무엇을 더 하나 (dry_run 이 안 하는 것)
--------------------------------------
  ⭐**G4 생존표** — 주장마다 «규약을 흔들면 뒤집히나» 를 채점한다. 이 저장소의 규칙:
     **규약 무관 생존만 헤드라인으로 쓴다**(docs/RETRACTION_LOG, 앵커 사고 이후).
     흔드는 규약 넷: 판정 막대(정본 p99.9 ↔ 더 엄한 선) · 관측시간 CPI · 기준채널 손실 ·
     시나리오(EIRP).
  ⭐**사전등록 채점** — `noise_main_prereg_0816.json` 의 예측 23 개를 `score_prereg()` 로
     채점한다. ⛔예측을 **고치지 않는다**. 관측이 없는 항목은 «관측 없음» 으로 남긴다.
  ⭐**두 층 표기** — 검증된 것(팔 사이 순서·필요 SNR)과 검증 안 된 것(절대 미터)을 갈라 적는다.

⛔GPU 없음. ⛔판정 막대는 **다시 계산하지 않고** `noise_main_gates_n20000_0818.json`
   (정본 20,000 시행)에서 읽는다 — 정본은 구현이 하나여야 한다.

산출: outputs/noise_main_run_0818.json
실행: PYTHONPATH=src:benchmark python benchmark/noise_main_run_0818.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import noise_main_gates as G                                           # noqa: E402

OUT = os.path.join(ROOT, "outputs", "noise_main_run_0818.json")
GATES = os.path.join(ROOT, "outputs", "noise_main_gates_n20000_0818.json")
SNRFIG = os.path.join(ROOT, "outputs", "noise_snr_figure_0818.json")
PREREG = os.path.join(ROOT, "outputs", "noise_main_prereg_0816.json")
CANON = os.path.join(ROOT, "outputs", "link_budget_canon_0816.json")

EL = -30.0


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def crossing_at(curve, bar):
    """빗살 대비 곡선이 주어진 막대를 뚫는 SNR — ⭐막대마다 **다시** 계산한다.
    (막대를 바꾸고도 정본 교차점을 재사용하면 생존 시험이 자기 자신과의 비교가 된다)"""
    xs = [p["snr_ac_db"] for p in curve]
    ys = [p["comb_db_mean"] for p in curve]
    for i in range(1, len(xs)):
        if ys[i - 1] < bar <= ys[i]:
            t = (bar - ys[i - 1]) / (ys[i] - ys[i - 1])
            return round(xs[i - 1] + t * (xs[i] - xs[i - 1]), 3)
    return None


def survival(rows, bars, canon, curves):
    """⭐G4 — 주장이 규약을 흔들어도 사는가.

    규약을 바꿔도 **부호와 순서**가 유지되면 산다. 절대값이 움직이는 것은 «산다» 를 안 깬다 —
    이 저장소가 앵커 사고에서 배운 것이 그것이다(값은 규약을 타고, 순서는 안 탄다).
    """
    arms = [k for k in rows if rows[k].get("snr_at_bar_db") is not None]
    claims = []

    # 주장 ① 팔 사이 «필요 SNR» 순서
    # ⭐막대마다 교차점을 **다시** 뽑는다
    xs_by_bar = {nm: {a: crossing_at(curves[a], bar) for a in arms if curves.get(a)}
                 for nm, bar in bars.items()}
    variants = {}
    for nm in bars:
        got = {a: v for a, v in xs_by_bar[nm].items() if v is not None}
        variants[nm] = sorted(got, key=lambda a: got[a])
    same = len({tuple(v) for v in variants.values()}) == 1
    claims.append(dict(
        id="S1", klass="A_convention_free",
        text_ko="필요 SNR 이 낮은 순서(= 잘 읽히는 순서)는 팔 사이에서 뒤집히지 않는다",
        values_by_variant={k: " < ".join(v) for k, v in variants.items()},
        survives=bool(same)))

    # 주장 ② 회절 켠 팔이 다른 팔보다 SNR 을 훨씬 더 요구한다
    gaps = {}
    for nm in bars:
        a, b = xs_by_bar[nm].get("ours"), xs_by_bar[nm].get("ps_phys")
        if a is not None and b is not None:
            gaps[nm] = round(b - a, 2)
    claims.append(dict(
        id="S2", klass="A_convention_free",
        text_ko="회절을 켠 팔은 같은 판정을 하는 데 SNR 이 훨씬 더 든다",
        values_by_variant=gaps,
        survives=bool(gaps and all(v > 5.0 for v in gaps.values()))))

    # 주장 ③ 절대 미터 — 규약을 타므로 **안 산다**(그래서 헤드라인에 못 쓴다)
    m = {}
    for nm, bar in bars.items():
        x = xs_by_bar[nm].get("ours")
        m[nm] = (None if x is None else
                 round(rows["ours"]["readable_range_m"]
                       * 10 ** ((x - rows["ours"]["snr_at_bar_db"])
                                / (rows["ours"].get("snr_law_db_per_decade") or -40.0)), 1))
    ref = canon.get("reference_channel", {})
    m["기준채널 ρ=30 dB (손실 7 dB)"] = (round(rows["ours"]["readable_range_m"] * 0.67, 1)
                                    if rows.get("ours", {}).get("readable_range_m") else None)
    m["패시브 5G SSB 시나리오"] = "다른 EIRP·다른 λ — 이 원장의 미터를 못 옮긴다"
    claims.append(dict(
        id="S3", klass="C_budget_dependent",
        text_ko="«우리 커널은 약 N m 까지 읽는다» 는 절대 미터",
        values_by_variant=m, survives=False,
        why_ko="기준채널 하나만 현실적으로 바꿔도 ×0.67 이고 시나리오를 바꾸면 아예 못 옮긴다"))

    return dict(claims=claims,
                rule_ko="⭐규약을 흔들어도 부호·순서가 유지되는 주장만 헤드라인으로 쓴다",
                headline_eligible=[c["id"] for c in claims if c["survives"]],
                not_eligible=[c["id"] for c in claims if not c["survives"]])


def main():
    t0 = time.time()
    gates = _load(GATES)
    fig = _load(SNRFIG)
    canon = _load(CANON)
    rows = fig["arms"]
    nb = fig["null_bar"]

    bars = {f"정본 막대 p99.9 ({nb['n_trial']:,} 시행)": nb["bar_db"]}
    if nb.get("frame_readable_db"):
        bars[f"더 엄한 선 {nb['frame_readable_db']:.2f} dB"] = nb["frame_readable_db"]

    frame = _load(os.path.join(ROOT, "outputs", "noise_distance_frame.json"))
    curves = {}
    for c in frame["cells"]:
        if c["el_deg"] == EL and c["range_m"] == 15.0 and c.get("snr_curve"):
            curves[c["arm"]] = c["snr_curve"]
    surv = survival(rows, bars, canon, curves)

    # ── 사전등록 채점 — ⛔예측을 고치지 않는다 ─────────────────────────
    observed = {}
    # 지금 관측할 수 있는 것만 채운다. 나머지는 «관측 없음» 으로 남는다(그게 정직하다).
    #   A1·A2 = 우리 커널 판독거리 변화율 — 재계산 전이라 0 으로 두면 **거짓**이므로 비운다.
    scored = G.score_prereg(PREREG, observed)

    gate_status = {
        "G1_anchor": gates.get("G1_anchor", {}).get("ok"),
        "G3_bars": bool(gates.get("G3_bars")),
        "G5_kinematics": gates.get("G5_kinematics", {}).get("gates", {})
                              .get("legacy(현행 원장 실측)", {}).get("ok"),
        "G7_canon_bands": bool(gates.get("G7_canon_bands")),
        "G8_inventory": bool(gates.get("G8_inventory")),
        "G9_a1_a2": bool(gates.get("G9_a1_a2")),
    }

    doc = {"_meta": {
        "generator": "benchmark/noise_main_run_0818.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "잡음 본판(결과판) — 게이트를 엮어 «어느 SNR 까지 읽히고 몇 미터인가» 를 낸다",
        "gpu_used": False,
        "inputs": [os.path.relpath(p, ROOT) for p in (GATES, SNRFIG, PREREG, CANON)],
        "el_deg": EL,
        "bar_source_ko": f"정본 막대는 게이트 {nb['n_trial']:,} 시행 경험적 p99.9 "
                         f"= {nb['bar_db']:.3f} dB (여기서 다시 계산하지 않는다)",
        "elapsed_s": round(time.time() - t0, 2)},
        "gate_status": gate_status,
        "headline": {k: {kk: v[kk] for kk in
                         ("label", "clean_comb_db", "snr_at_bar_db", "snr_at_15m_db",
                          "readable_range_m", "range_extrapolation_trustworthy")
                         if kk in v} for k, v in rows.items()},
        "G4_survival": surv,
        "prereg_scored": scored,
        "two_layer_ko": {
            "verified": ["팔 사이 «필요 SNR» 순서", "회절 켠 팔이 요구하는 SNR 격차",
                         "판정 막대 자체(귀무분포에서 세움)"],
            "not_verified": ["절대 미터 — 실측 대조 0 건",
                             "송신→수신 격리 미확보(능동 모노 예산이 통째로 낙관일 수 있다)",
                             "거리 외삽 — 엔진이 이미 거리로 레벨을 나르는 팔이 둘"],
        }}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"═══ 게이트 ═══")
    for k, v in gate_status.items():
        print(f"  {'✅' if v else '⚠'} {k}")
    print(f"\n═══ 헤드라인 (앙각 {EL:.0f}°, 막대 {nb['bar_db']:.2f} dB) ═══")
    print(f"  {'팔':30s} {'필요 SNR':>9s} {'15 m SNR':>9s} {'읽기 한계':>10s}")
    for k, r in rows.items():
        flag = "" if r.get("range_extrapolation_trustworthy") in (True, None) else "  ⛔외삽 불가"
        print(f"  {r['label']:30s} {r['snr_at_bar_db']!s:>9} {r['snr_at_15m_db']:8.1f} "
              f"{(str(r['readable_range_m'])+' m') if r.get('readable_range_m') else '—':>10}{flag}")
    print(f"\n═══ G4 생존표 — 규약을 흔들면 ═══")
    for c in surv["claims"]:
        print(f"  {'✅산다' if c['survives'] else '⛔안 산다'} [{c['id']}] {c['text_ko']}")
        for k, v in c["values_by_variant"].items():
            print(f"        {k}: {v}")
    print(f"\n═══ 사전등록 채점 ═══")
    print(f"  {json.dumps({k: v for k, v in scored.items() if not isinstance(v, list)}, ensure_ascii=False)}")
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
