# -*- coding: utf-8 -*-
"""
detection_curves_attack.py — detection_curves.py 반증(적대적 검증) 하네스
=========================================================================

공격 렌즈: 교정·누출·통계 —
  (A) audit     : 마스크 기하(빗살 겹침·로터 RPM 이탈·대역 빈 수)·앵커/링크버짓 수식 폐합·
                  원장 JSON 내부 일관성(R50 재계산, comb≥band 집계) 재검증
  (B) repro     : 같은 씨앗으로 본체 main() 전체 재실행(산출 경로만 바꿔서) → 발표 JSON 과
                  숫자 단위 diff — 손으로 고친 숫자·비결정성 유무
  (C) seed      : 다른 마스터 씨앗으로 전체 재실행(문턱 재교정 포함) → R50 이동량
  (D) nulls     : 널/셔플 대조 —
                  ① 잡음 전용(제3 씨앗) Pd ≈ Pfa,
                  ② CW(순수 DC) 신호 → DC 제거가 정말 지우는지 (Pd ≈ Pfa 기대),
                  ③ 시간 셔플 신호(리듬 파괴·전력 보존) → 빗살 우위 붕괴 여부,
                  ④ 대역 밖 전용 신호 → 한나 창 옆동이(sidelobe) 누설로 오검출 나는지,
                  ⑤ 참신호 Pd 를 내 씨앗으로 재측정 → 발표 곡선과 비교
  (E) bootstrap : 발표 Pd 표(240시행)의 이항 부트스트랩 → R50 95% CI·주장 유의성
                  (ours 앙각 차이, comb vs band 우위)

⛔GPU/솔버 없음 — 저장된 원장·npz·발표 JSON 만 읽는 CPU 분석.
⛔기존 파일 수정 없음 — 산출은 전부 outputs/detection_curves_attack_*.json
  (+repro/seed 는 outputs/figures/detection_pd_curves_attack_*.png).

실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/detection_curves_attack.py <phase>
"""
from __future__ import annotations

import argparse
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

import detection_curves as dc                                   # noqa: E402
from rx_noise import sigma_kernel_m2, anchor_scale, noise_power_w, RxSpec  # noqa: E402
from link_budget import LinkBudget, C0, lin2db                  # noqa: E402

PUB_JSON = os.path.join(ROOT, "outputs", "detection_curves.json")
OUTDIR = os.path.join(ROOT, "outputs")


def _load_pub():
    return json.load(open(PUB_JSON))


def _setup_pipeline():
    """본체 main() 앞부분과 동일한 파이프라인 상태(팔·앵커·마스크·N_w)를 재구성."""
    arms, meta = dc.load_arms()
    fc, prf, f_flash, n = meta["fc_hz"], meta["prf_hz"], meta["f_flash_hz"], meta["n"]
    lam = C0 / fc
    w = np.hanning(n)
    spec = RxSpec(eirp_dbm=dc.EIRP_DBM)
    N_w = noise_power_w(spec, prf)
    lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                    noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)
    from rx_noise import sigma_ref_from_literature
    ref = sigma_ref_from_literature(fc, meta["drone"])
    c_anchor = {}
    for short, eng, _ in dc.ENGINES:
        E30 = next(a["E"] for a in arms
                   if a["engine_short"] == short and a["el_deg"] == dc.EL_MAIN)
        c_anchor[short] = anchor_scale(E30, fc, ref["sigma_ref_dbsm"])
    ftip_by_el = {}
    for a in arms:
        ftip_by_el.setdefault(a["el_deg"], set()).add(a["f_tip_hz"])
    ftip_by_el = {el: s.pop() for el, s in ftip_by_el.items()}
    masks = {el: dc.make_masks(n, prf, ft, f_flash)
             for el, ft in ftip_by_el.items()}
    return dict(arms=arms, meta=meta, fc=fc, prf=prf, f_flash=f_flash, n=n,
                lam=lam, w=w, spec=spec, N_w=N_w, lb=lb, ref=ref,
                c_anchor=c_anchor, masks=masks, ftip_by_el=ftip_by_el)


# --------------------------------------------------------------------------- #
#  (A) audit — 마스크·앵커·링크버짓·JSON 내부 일관성
# --------------------------------------------------------------------------- #
def phase_audit():
    P = _setup_pipeline()
    pub = _load_pub()
    n, prf, f_flash = P["n"], P["prf"], P["f_flash"]
    df = prf / n
    fr = np.fft.fftfreq(n, 1.0 / prf)
    audit = dict(df_hz=df)

    # 1) 빗살 이 사이 겹침: 이웃 정수배의 ±8 Hz 창이 서로 닿는가
    audit["comb_teeth_overlap"] = bool(2 * dc.HW_HZ >= f_flash)   # 16 < 126.67 기대 False

    # 2) 로터 RPM 산포 vs ±8 Hz: 원장 rpm_per_rotor 로 실제 플래시선 이탈 최대값
    led = json.load(open(dc.LEDGER_JSON))
    rpms = led["_meta"].get("rpm_per_rotor")
    detune = None
    if rpms:
        bpf = [2.0 * r / 60.0 for r in rpms]                      # 날개 2장 가정(플래시)
        kmax = int(np.floor(max(P["ftip_by_el"].values()) / f_flash))
        detune = max(abs(k * b - k * f_flash) for b in bpf for k in range(1, kmax + 1))
        audit["rotor_bpf_hz"] = [round(b, 3) for b in bpf]
        audit["max_harmonic_detune_hz"] = round(detune, 3)
        audit["detune_within_hw"] = bool(detune <= dc.HW_HZ)

    # 3) 마스크 빈 수·포함 관계
    audit["masks"] = {}
    for el, (band, comb) in P["masks"].items():
        audit["masks"][f"{el:+.0f}"] = dict(
            band_bins=int(band.sum()), comb_bins=int(comb.sum()),
            comb_subset_of_band=bool(np.all(band[comb])))

    # 4) 링크버짓 폐합: snr@100m 을 수식으로 독립 재계산 → 발표값과 대조
    closure = {}
    for a in P["arms"]:
        c = P["c_anchor"][a["engine_short"]]["c_anchor"]
        sig = sigma_kernel_m2(a["E"], P["fc"]) * c
        snr = float(lin2db(P["lb"].echo_power_w(P["lam"], sig, 100.0, 100.0).mean()
                           / P["N_w"]))
        pubA = next(x for x in pub["arms"] if x["arm_id"] == a["arm_id"])
        closure[a["arm_id"]] = dict(
            snr100_recomputed_db=round(snr, 4),
            snr100_published_db=round(pubA["snr_sample_db_at_100m"], 4),
            match=bool(abs(snr - pubA["snr_sample_db_at_100m"]) < 1e-6))
    audit["snr100_closure"] = closure

    # 5) 발표 JSON 내부 일관성: R50 을 pd 표에서 재계산, comb≥band 집계 재검증
    Rg = np.asarray(pub["_meta"]["R_grid_m"], float)

    def r50(pd):
        pd = np.asarray(pd, float)
        if pd[0] < 0.5:
            return None
        below = pd < 0.5
        if not below.any():
            return None
        i = int(np.argmax(below))
        x0, x1 = np.log10(Rg[i - 1]), np.log10(Rg[i])
        y0, y1 = pd[i - 1], pd[i]
        return float(10 ** (x0 + (y0 - 0.5) / max(y0 - y1, 1e-12) * (x1 - x0)))

    r50_ok, cgb = True, 0
    for a in pub["arms"]:
        for st in ("comb", "band"):
            r = r50(a[f"pd_{st}"])
            p = a["R50_m"][st]
            if (r is None) != (p is None) or (r and abs(r - p) > 1e-6):
                r50_ok = False
        if a["R50_m"]["comb"] and a["R50_m"]["band"] \
                and a["R50_m"]["comb"] >= a["R50_m"]["band"]:
            cgb += 1
    audit["r50_recompute_matches"] = bool(r50_ok)
    audit["comb_ge_band_recount"] = f"{cgb}/{len(pub['arms'])}"

    # 6) Pfa 자가검사 경계 nit: 코드 주석은 3σ 라는데 실제 상한 2.5e-3 은 3σ(1.55e-3)보다 넓다
    audit["pfa_gate_nit"] = dict(
        coded_bounds=[0.4e-3, 2.5e-3],
        binomial_3sigma_bounds=[round((30 - 3 * np.sqrt(30 * 0.999)) / 30000, 6),
                                round((30 + 3 * np.sqrt(30 * 0.999)) / 30000, 6)])

    # 7) 대역 안 AC 에너지 몫(한나 창 기준) — 셔플 널 해석에 쓸 기준량
    frac = {}
    for a in P["arms"]:
        E = a["E"] - a["E"].mean()
        Pw = np.abs(np.fft.fft(E * P["w"])) ** 2
        band, comb = P["masks"][a["el_deg"]]
        frac[a["arm_id"]] = dict(
            band_energy_frac=round(float(Pw[band].sum() / Pw.sum()), 4),
            comb_energy_frac=round(float(Pw[comb].sum() / Pw.sum()), 4),
            comb_over_band=round(float(Pw[comb].sum() / max(Pw[band].sum(), 1e-300)), 4))
    audit["ac_energy_fractions"] = frac

    out = dict(_meta=dict(generator="benchmark/detection_curves_attack.py audit",
                          note_ko="detection_curves 반증 1단계 — 마스크·앵커·일관성 감사"),
               audit=audit)
    p = os.path.join(OUTDIR, "detection_curves_attack_audit.json")
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(audit, ensure_ascii=False, indent=1))
    print(f"  -> {p}")


# --------------------------------------------------------------------------- #
#  (B)/(C) repro·seed — 본체 main() 전체 재실행(산출 경로/씨앗만 패치)
# --------------------------------------------------------------------------- #
def phase_full(tag: str, seed: int | None):
    dc.OUT_JSON = os.path.join(OUTDIR, f"detection_curves_attack_{tag}.json")
    dc.OUT_PNG = os.path.join(OUTDIR, "figures",
                              f"detection_pd_curves_attack_{tag}.png")
    if seed is not None:
        dc.SEED = int(seed)
    t0 = time.time()
    dc.main()
    print(f"[attack:{tag}] took {time.time() - t0:.1f}s -> {dc.OUT_JSON}")


def _num_diff(a, b, path="", diffs=None, atol=0.0):
    """재귀 diff — elapsed_s 만 무시. 숫자·문자·구조 전부 비교."""
    if diffs is None:
        diffs = []
    if path.endswith("elapsed_s"):
        return diffs
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                diffs.append(f"{path}.{k}: missing on one side")
            else:
                _num_diff(a[k], b[k], f"{path}.{k}", diffs, atol)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: len {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                _num_diff(x, y, f"{path}[{i}]", diffs, atol)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not (a == b or (np.isfinite(a) and np.isfinite(b)
                           and abs(a - b) <= atol * max(1.0, abs(a), abs(b)))):
            diffs.append(f"{path}: {a} != {b}")
    elif a != b:
        diffs.append(f"{path}: {a!r} != {b!r}")
    return diffs


def phase_diff(tag: str):
    pub = _load_pub()
    att = json.load(open(os.path.join(OUTDIR, f"detection_curves_attack_{tag}.json")))
    diffs = _num_diff(pub, att)
    print(f"[diff {tag}] {len(diffs)} numeric differences (elapsed_s ignored)")
    for d in diffs[:40]:
        print("  ", d)
    p = os.path.join(OUTDIR, f"detection_curves_attack_{tag}_diff.json")
    json.dump(dict(n_diffs=len(diffs), diffs=diffs[:400]), open(p, "w"),
              ensure_ascii=False, indent=1)
    print(f"  -> {p}")


def phase_seed_compare(tag: str):
    """씨앗 바꾼 전체 재실행 vs 발표본 — R50·Pfa 이동량."""
    pub, att = _load_pub(), json.load(
        open(os.path.join(OUTDIR, f"detection_curves_attack_{tag}.json")))
    rows = []
    for a in pub["arms"]:
        b = next(x for x in att["arms"] if x["arm_id"] == a["arm_id"])
        for st in ("comb", "band"):
            r0, r1 = a["R50_m"][st], b["R50_m"][st]
            rows.append(dict(arm=a["arm_id"], stat=st, R50_pub=r0, R50_seed=r1,
                             rel_shift_pct=(None if not (r0 and r1)
                                            else round(100 * (r1 / r0 - 1), 2))))
    out = dict(_meta=dict(generator="attack seed_compare",
                          seed_pub=pub["_meta"]["seed"], seed_att=att["_meta"]["seed"]),
               pfa_att=att["pfa_measured"], rows=rows)
    p = os.path.join(OUTDIR, f"detection_curves_attack_{tag}_compare.json")
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"  -> {p}")


# --------------------------------------------------------------------------- #
#  (D) nulls — 널·셔플 대조 (발표 문턱 = 잡음전용 교정이므로 그대로 사용 가능)
# --------------------------------------------------------------------------- #
def _pd_once(x0, n_trial, rng, P, el, thr):
    band, comb = P["masks"][el]
    hits_c = hits_b = 0
    done = 0
    while done < n_trial:
        m = min(dc.BATCH, n_trial - done)
        X = x0[None, :] + dc.noise_batch(rng, m, P["n"], P["N_w"])
        Tc, Tb = dc.batch_stats(X, P["w"], band, comb)
        hits_c += int((Tc > thr["comb"]).sum())
        hits_b += int((Tb > thr["band"]).sum())
        done += m
    return hits_c / n_trial, hits_b / n_trial


def phase_nulls(seed: int = 990815):
    P = _setup_pipeline()
    pub = _load_pub()
    thr = {float(k): v for k, v in pub["thresholds"].items()}
    rng = np.random.default_rng(seed)
    res = dict(_meta=dict(generator="attack nulls", seed=seed,
                          thresholds_from="outputs/detection_curves.json (잡음전용 교정)",
                          note_ko="널·셔플 대조 — 문턱은 발표본 그대로(잡음전용이라 누설 없음)"))

    # ① 잡음 전용(제3 씨앗): Pd ≈ Pfa=1e-3 이어야 한다
    zero = np.zeros(P["n"], complex)
    nn = 12000
    res["noise_only_third_seed"] = {}
    for el in sorted(thr):
        pc, pb = _pd_once(zero, nn, rng, P, el, thr[el])
        res["noise_only_third_seed"][f"{el:+.0f}"] = dict(
            n_trial=nn, pfa_comb=pc, pfa_band=pb)

    def arm(aid):
        return next(a for a in P["arms"] if a["arm_id"] == aid)

    def x_signal(a, R):
        c = P["c_anchor"][a["engine_short"]]["c_anchor"]
        sig = sigma_kernel_m2(a["E"], P["fc"]) * c
        Pe = P["lb"].echo_power_w(P["lam"], sig, R, R)
        E = a["E"]
        ph = np.where(np.abs(E) > 0, E / np.maximum(np.abs(E), 1e-300), 1.0)
        return np.sqrt(Pe) * ph

    # ② CW(순수 DC) — 같은 총전력의 상수 신호: DC 제거가 지우면 Pd≈Pfa
    a30 = arm("ours_el-30")
    res["cw_null"] = {}
    for R in (150.0, 300.0):
        x0 = x_signal(a30, R)
        cw = np.full(P["n"], np.sqrt(np.mean(np.abs(x0) ** 2)), complex)
        pc, pb = _pd_once(cw, 6000, rng, P, -30.0, thr[-30.0])
        res["cw_null"][f"R{R:.0f}"] = dict(n_trial=6000, pd_comb=pc, pd_band=pb,
                                           expect_ko="≈1e-3 (DC 제거가 상수를 지움)")

    # ③ 시간 셔플 — 리듬 파괴·전력/DC 보존: 빗살 우위 붕괴 여부
    res["shuffle_null"] = {}
    for aid in ("ours_el-30", "sionna_el-30"):
        a = arm(aid)
        res["shuffle_null"][aid] = {}
        for R in (400.0, 700.0):
            x0 = x_signal(a, R)
            hits = dict(comb=0, band=0)
            n_perm, n_noise = 8, 500
            for _ in range(n_perm):
                xs = x0[rng.permutation(P["n"])]
                pc, pb = _pd_once(xs, n_noise, rng, P, a["el_deg"],
                                  thr[a["el_deg"]])
                hits["comb"] += pc * n_noise
                hits["band"] += pb * n_noise
            tot = n_perm * n_noise
            pt_c, pt_b = _pd_once(x0, 2000, rng, P, a["el_deg"], thr[a["el_deg"]])
            res["shuffle_null"][aid][f"R{R:.0f}"] = dict(
                n_trial=tot, pd_comb_shuffled=hits["comb"] / tot,
                pd_band_shuffled=hits["band"] / tot,
                pd_comb_true=pt_c, pd_band_true=pt_b,
                expect_ko="셔플이 진짜 신호보다 한참 아래면 통계량이 리듬을 재는 것")

    # ④ 대역 밖 전용 신호 — 창 옆동이 누설 검사(총전력은 참신호와 동일하게 맞춤)
    res["out_of_band_null"] = {}
    for R in (150.0, 300.0):
        x0 = x_signal(a30, R)
        Xf = np.fft.fft(x0 - x0.mean())
        band, _ = P["masks"][-30.0]
        Xf[band] = 0.0
        xo = np.fft.ifft(Xf)
        xo *= np.sqrt(np.mean(np.abs(x0) ** 2) / max(np.mean(np.abs(xo) ** 2), 1e-300))
        pc, pb = _pd_once(xo, 6000, rng, P, -30.0, thr[-30.0])
        res["out_of_band_null"][f"R{R:.0f}"] = dict(
            n_trial=6000, pd_comb=pc, pd_band=pb,
            expect_ko="≈1e-3 이어야 대역 잣대가 대역 밖 에너지에 안 속는 것")

    # ⑤ 참신호 Pd 를 내 씨앗·더 많은 시행으로 재측정 → 발표 곡선 보간과 대조
    res["true_signal_recheck"] = {}
    Rg = np.asarray(pub["_meta"]["R_grid_m"], float)
    for aid in ("ours_el-30", "sionna_el-30", "ours_el+0"):
        a = arm(aid)
        pubA = next(x for x in pub["arms"] if x["arm_id"] == aid)
        res["true_signal_recheck"][aid] = {}
        for R in (500.0, 700.0, 900.0):
            x0 = x_signal(a, R)
            pc, pb = _pd_once(x0, 2000, rng, P, a["el_deg"], thr[a["el_deg"]])
            ip_c = float(np.interp(np.log10(R), np.log10(Rg), pubA["pd_comb"]))
            ip_b = float(np.interp(np.log10(R), np.log10(Rg), pubA["pd_band"]))
            res["true_signal_recheck"][aid][f"R{R:.0f}"] = dict(
                n_trial=2000, pd_comb=pc, pd_band=pb,
                pub_interp_comb=round(ip_c, 4), pub_interp_band=round(ip_b, 4))

    p = os.path.join(OUTDIR, "detection_curves_attack_nulls.json")
    json.dump(res, open(p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"  -> {p}")


# --------------------------------------------------------------------------- #
#  (E) bootstrap — 발표 Pd 표(240시행) 이항 부트스트랩 → R50 CI·주장 유의성
# --------------------------------------------------------------------------- #
def phase_bootstrap(K: int = 4000, seed: int = 991123):
    pub = _load_pub()
    Rg = np.asarray(pub["_meta"]["R_grid_m"], float)
    n_mc = int(pub["_meta"]["n_mc"])
    rng = np.random.default_rng(seed)
    lg = np.log10(Rg)

    def r50_vec(pd_mat):
        """행렬(K×21) → R50 벡터(첫 하강 교차, 로그 보간; 본체 r50 과 같은 규칙)."""
        out = np.full(pd_mat.shape[0], np.nan)
        for j, pd in enumerate(pd_mat):
            if pd[0] < 0.5:
                continue
            below = pd < 0.5
            if not below.any():
                continue
            i = int(np.argmax(below))
            y0, y1 = pd[i - 1], pd[i]
            out[j] = 10 ** (lg[i - 1] + (y0 - 0.5) / max(y0 - y1, 1e-12)
                            * (lg[i] - lg[i - 1]))
        return out

    boots = {}
    for a in pub["arms"]:
        boots[a["arm_id"]] = {}
        for st in ("comb", "band"):
            p_hat = np.asarray(a[f"pd_{st}"], float)
            sim = rng.binomial(n_mc, np.tile(p_hat, (K, 1))) / n_mc
            r = r50_vec(sim)
            ok = np.isfinite(r)
            boots[a["arm_id"]][st] = dict(
                R50_point=a["R50_m"][st],
                ci95=[round(float(np.nanpercentile(r, 2.5)), 1),
                      round(float(np.nanpercentile(r, 97.5)), 1)],
                frac_defined=round(float(ok.mean()), 4),
                samples=r)
    # 주장 유의성 (부트스트랩 독립 표본끼리 비교 — MC 도 실제로 독립 스트림)
    def pgt(a1, s1, a2, s2):
        x, y = boots[a1][s1]["samples"], boots[a2][s2]["samples"]
        m = np.isfinite(x) & np.isfinite(y)
        return round(float((x[m] > y[m]).mean()), 4)

    claims = dict(
        comb_gt_band_per_arm={aid: pgt(aid, "comb", aid, "band") for aid in boots},
        ours_el30_gt_el0_comb=pgt("ours_el-30", "comb", "ours_el+0", "comb"),
        ours_el30_gt_el60_comb=pgt("ours_el-30", "comb", "ours_el-60", "comb"),
        sionna30_gt_ours30_comb=pgt("sionna_el-30", "comb", "ours_el-30", "comb"),
        note_ko="값=P(앞>뒤). 0.5 근처면 240시행으로는 구별 불가라는 뜻")
    for aid in boots:                                   # samples 는 저장 전 제거
        for st in boots[aid]:
            del boots[aid][st]["samples"]
    out = dict(_meta=dict(generator="attack bootstrap", K=K, n_mc=n_mc, seed=seed,
                          note_ko="발표 Pd 표의 이항 재표집 — 문턱 불확실성은 seed 단계가 커버"),
               R50_bootstrap=boots, claims=claims)
    p = os.path.join(OUTDIR, "detection_curves_attack_bootstrap.json")
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(dict(R50=boots, claims=claims), ensure_ascii=False, indent=1))
    print(f"  -> {p}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["audit", "repro", "seed", "diff",
                                      "seed_compare", "nulls", "bootstrap"])
    ap.add_argument("--seed", type=int, default=777)
    a = ap.parse_args()
    if a.phase == "audit":
        phase_audit()
    elif a.phase == "repro":
        phase_full("repro", None)
    elif a.phase == "seed":
        phase_full(f"seed{a.seed}", a.seed)
    elif a.phase == "diff":
        phase_diff("repro")
    elif a.phase == "seed_compare":
        phase_seed_compare(f"seed{a.seed}")
    elif a.phase == "nulls":
        phase_nulls()
    elif a.phase == "bootstrap":
        phase_bootstrap()
