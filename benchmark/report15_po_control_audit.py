# -*- coding: utf-8 -*-
"""
report15_po_control_audit.py — **대조군 A 의 자체 감사** (mini2 · matrice4e)
================================================================================

`benchmark/report15_po_control.py` 가 낸 `outputs/report15_po_control.json` 을 두 방향에서 캔다.
새 실험이 아니라 **같은 실험의 반증 시도**다. 출력은 새 파일 하나뿐이다.

■ 감사 ① — 저장된 PO 파형이 진짜 그 커널에서 나온 것인가
   `arm_po` 를 **같은 인자로 다시 돌려** 저장된 32점 복소 파형과 비트 수준으로 대조한다.
   우리 커널은 결정론적이므로 Δ = 0 이어야 한다. 0 이 아니면 저장물이 그 코드의 산출이 아니다.

■ 감사 ② — ⭐ **헤드라인 상관 0.93 이 사소한 값인가**
   대조군 A 의 헤드라인은 "우리 PO 파형과 Sionna 파형의 AC 상관 = 0.93" 이다. 그런데
   AC 상관은 상수 복소배에 불변이라, **두 파형이 같은 하모닉 하나에 몰려 있으면 물리와 무관하게
   |c| → 1** 이 된다(둘 다 2/rev 사인파면 위상이 뭐든 크기 상관은 1). 그래서 세 가지를 잰다:

     (a) **천장** ceiling = Σ_m √(p_a[m]·p_b[m])
         두 스펙트럼이 주어졌을 때 위상을 최적으로 맞췄을 때의 |c| 상한(코시-슈바르츠).
     (b) **귀무분포** — Sionna 파형의 하모닉 **위상만** 무작위로 다시 뽑고(크기 보존) |c| 재계산.
         관측값이 이 분포 안에 들어가면, 일치한 것은 '파형' 이 아니라 '스펙트럼 모양' 뿐이다.
     (c) **잔차 상관** — 지배 하모닉 ±m* 를 두 파형에서 **빼고** 남은 것끼리의 상관.
         이것이 0 근처면 일치는 사인파 한 개가 전부다.

   추가로 (d) **하모닉 위상 정합**: φ 축 이동 Δφ 와 상수 위상 θ 를 최소제곱으로 맞춘다.
   하모닉이 2개 이상 있어야 (θ + m·Δφ) 가 식별된다 — 식별 안 되면 그렇다고 적는다.
   (e) 시드평균이 아니라 **시드 하나하나**와 우리 파형의 상관.

⛔ src/drones.py · src/drone_cad.py 는 읽기만 한다.
⛔ 기존 산출물 덮어쓰기 금지 — 출력은 outputs/report15_po_control_audit.json.
그림 없음. print·주석 한국어.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import report15_po_control as pc                                       # noqa: E402
from drones import DRONES                                              # noqa: E402

OUT = os.path.join(ROOT, "outputs", "report15_po_control_audit.json")
PC_JSON = pc.OUT_JSON
PROBE_JSON = pc.PROBE_JSON
N_NULL = 20000
RNG = np.random.default_rng(20260804)


# --------------------------------------------------------------------------- #
def E_from_wave(w):
    """저장된 wave 블록(amp_db·phase_deg) → 복소 파형 복원."""
    a = np.asarray(w["amp_db"], float)
    p = np.radians(np.asarray(w["phase_deg"], float))
    return 10.0 ** (a / 20.0) * np.exp(1j * p)


def ac_corr(a, b):
    a = np.asarray(a, complex); b = np.asarray(b, complex)
    a = a - a.mean(); b = b - b.mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(abs(np.vdot(a, b)) / (na * nb)) if na > 0 and nb > 0 else 0.0


def sionna_H(J, key, which, mode="prod"):
    """probe JSON → 시드×위상 복소 행렬 h (probe 의 관측량 정의 그대로)."""
    R = J["airframes"][key][which]
    rows = R["by_mode"][mode]
    seeds = sorted({x["seed"] for r in rows for x in r["runs"]})
    H = np.zeros((len(seeds), len(rows)), complex)
    for j, r in enumerate(rows):
        for x in r["runs"]:
            i = seeds.index(x["seed"])
            H[i, j] = 10.0 ** (x["amp_db"] / 20.0) * np.exp(1j * np.radians(x["phase_deg"]))
    ph = np.array([float(r["phase_deg"]) for r in rows], float)
    return ph, H, [int(s) for s in seeds]


# --------------------------------------------------------------------------- #
#  감사 ② 의 수치들
# --------------------------------------------------------------------------- #
def _phase_null(a, B, n_null, rng):
    """a 는 고정, B(=b 의 FFT) 의 **위상만** 무작위로 다시 뽑아 |c| 귀무분포를 만든다."""
    absB = np.abs(B)
    na = np.linalg.norm(a)
    nulls = np.empty(int(n_null))
    for i in range(int(n_null)):
        Bn = absB * np.exp(1j * rng.uniform(0, 2 * np.pi, size=absB.size))
        Bn[0] = 0.0                                            # DC 는 제거된 상태 유지
        bn = np.fft.ifft(Bn)
        nb = np.linalg.norm(bn)
        nulls[i] = abs(np.vdot(a, bn)) / (na * nb) if nb > 0 else 0.0
    return nulls


def triviality(Eo, Hs, n_null=N_NULL, rng=RNG):
    """관측 |c| 가 '스펙트럼 모양만으로 자동으로 나오는 값' 인지 판정한다."""
    a = np.asarray(Eo, complex); b = np.asarray(Hs, complex)
    n = min(a.size, b.size); a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    A, B = np.fft.fft(a), np.fft.fft(b)
    pa = np.abs(A) ** 2; pb = np.abs(B) ** 2
    pa = pa / pa.sum(); pb = pb / pb.sum()
    obs = float(abs(np.vdot(a, b)) / (np.linalg.norm(a) * np.linalg.norm(b)))
    ceiling = float(np.sum(np.sqrt(pa * pb)))                 # 위상 최적정렬 상한
    rms_null = float(np.sqrt(np.sum(pa * pb)))                # 위상 무작위 시 E[|c|²]^½

    #  (b) 위상 무작위 귀무분포 — 크기 보존, 위상만 재추첨
    nulls = _phase_null(a, B, n_null, rng)
    p = float((nulls >= obs).mean())

    #  지배 하모닉
    m = np.fft.fftfreq(n, d=1.0 / n).astype(int)
    ma = int(abs(m[int(np.argmax(pa))])); mb = int(abs(m[int(np.argmax(pb))]))

    #  (c) 지배 하모닉 ±m* 를 두 파형에서 모두 제거한 잔차 상관
    #      ⚠ 잔차도 **같은 방식으로** 귀무검정한다 — "rms 의 2배" 같은 임의 문턱은 검정이 아니다.
    sel = np.abs(m) == ma
    A2, B2 = A.copy(), B.copy()
    A2[sel] = 0.0; B2[sel] = 0.0
    ra, rb = np.fft.ifft(A2), np.fft.ifft(B2)
    res = ac_corr(ra, rb)
    res_pow_a = float(pa[~sel].sum()); res_pow_b = float(pb[~sel].sum())
    qa = pa[~sel] / max(pa[~sel].sum(), 1e-300)
    qb = pb[~sel] / max(pb[~sel].sum(), 1e-300)
    res_rms_null = float(np.sqrt(np.sum(qa * qb)))
    res_ceiling = float(np.sum(np.sqrt(qa * qb)))
    res_nulls = _phase_null(ra - ra.mean(), B2, n_null, rng)
    res_p = float((res_nulls >= res).mean())
    res_null_mean = float(res_nulls.mean()); res_null_p95 = float(np.percentile(res_nulls, 95))

    #  (d) 하모닉 위상 정합: arg(A_m)−arg(B_m) = θ + m·Δφ 로 맞는가
    use = np.where((np.abs(m) > 0) & (pa > 0.01 * pa.max()) & (pb > 0.01 * pb.max()))[0]
    fit = dict(n_harmonics_used=int(use.size), identifiable=bool(use.size >= 3))
    if use.size >= 3:
        dphi = np.angle(A[use] * np.conj(B[use]))
        mm = m[use].astype(float)
        w = np.sqrt(pa[use] * pb[use])
        #  Δφ 를 격자탐색 (원형 잔차라 선형 최소제곱이 안 된다)
        grid = np.linspace(-np.pi, np.pi, 3601)
        best = None
        for d in grid:
            r = np.angle(np.exp(1j * (dphi - mm * d)))
            th = np.angle(np.sum(w * np.exp(1j * r)))
            resid = np.angle(np.exp(1j * (r - th)))
            cost = float(np.sum(w * resid ** 2) / np.sum(w))
            if best is None or cost < best[0]:
                best = (cost, float(d), float(th))
        fit.update(phase_slope_rad_per_harmonic=best[1],
                   const_phase_rad=best[2],
                   weighted_rms_resid_deg=float(math.degrees(math.sqrt(best[0]))),
                   phi_shift_deg=float(math.degrees(best[1])))
    return dict(
        n=int(n), observed_ac_corr=obs,
        ceiling_phase_aligned=ceiling, null_rms_random_phase=rms_null,
        null_mean=float(nulls.mean()), null_p95=float(np.percentile(nulls, 95)),
        null_p99=float(np.percentile(nulls, 99)), null_max=float(nulls.max()),
        p_value=p, n_null=int(n_null),
        excess_over_null_mean=float(obs - nulls.mean()),
        z_vs_null=float((obs - nulls.mean()) / nulls.std()) if nulls.std() > 0 else None,
        dominant_harmonic_ours=ma, dominant_harmonic_sionna=mb,
        dominant_power_frac_ours=float(pa[np.abs(m) == ma].sum()),
        dominant_power_frac_sionna=float(pb[np.abs(m) == mb].sum()),
        residual_ac_corr=res, residual_power_frac_ours=res_pow_a,
        residual_power_frac_sionna=res_pow_b,
        residual_null_rms=res_rms_null, residual_ceiling=res_ceiling,
        residual_null_mean=res_null_mean, residual_null_p95=res_null_p95,
        residual_p_value=res_p,
        harmonic_phase_fit=fit,
        note_ko=("observed 가 null_p95 를 못 넘으면 '두 파형이 닮았다' 는 주장은 "
                 "스펙트럼 모양만으로 설명된다 — 위상(=블레이드 각위치) 정보는 일치하지 않는다."))


# --------------------------------------------------------------------------- #
def main():
    t_all = time.time()
    JP = json.load(open(PC_JSON, encoding="utf-8"))
    JB = json.load(open(PROBE_JSON, encoding="utf-8"))
    idx_matched = np.arange(0, pc.N_PHASE // 2, 2)

    out = dict(meta=dict(
        script="benchmark/report15_po_control_audit.py",
        role=("대조군 A(report15_po_control.json) 의 자체 감사 — 재실행 재현성 + "
              "헤드라인 상관의 귀무검정"),
        audited_json=os.path.relpath(PC_JSON, ROOT),
        probe_json=os.path.relpath(PROBE_JSON, ROOT),
        audited_stamp=JP["meta"].get("post_stamp") or JP["meta"].get("stamp"),
        n_null=N_NULL, rng_seed=20260804,
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), airframes={})

    for key in pc.KEYS:
        spec = DRONES[key]
        R = JP["airframes"][key]
        rec = dict(rerun={}, triviality={}, per_seed={})
        print(f"[{key}] 감사 시작", flush=True)

        #  ── 감사 ① 재실행 재현성 ──
        for arm, (wf, bis) in {"po_spherical_bistatic": ("spherical", True),
                               "po_plane_mono": ("plane", False)}.items():
            t0 = time.time()
            _, Ea, Ep, info = pc.arm_po(spec, pc.AZ_DEG, pc.EL_DEG, wavefront=wf,
                                        bistatic=bis, n_phase=pc.N_PHASE, disc=pc.PO_MATCHED)
            new = Ea[idx_matched]
            old = E_from_wave(R["arms"][f"ref/{arm}"]["matched32"]["wave"])
            #  저장은 dB·deg 로 반올림돼 있으므로 상대오차로 본다
            rel = float(np.max(np.abs(new - old)) / np.max(np.abs(old)))
            rec["rerun"][arm] = dict(
                max_rel_diff=rel,
                max_abs_db_diff=float(np.max(np.abs(
                    20 * np.log10(np.abs(new)) - 20 * np.log10(np.abs(old))))),
                max_abs_phase_diff_deg=float(np.max(np.abs(np.angle(
                    new * np.conj(old), deg=True)))),
                ac_corr_new_vs_old=ac_corr(new, old),
                ptp_db_new=float(np.ptp(20 * np.log10(np.abs(new)))),
                ptp_db_stored=float(R["arms"][f"ref/{arm}"]["matched32"]["wave"]["amp_db_ptp"]),
                seconds=float(time.time() - t0),
                verdict=("동일(결정론적 재현)" if rel < 1e-9 else "⚠ 불일치"))
            print(f"   재실행 {arm}: 상대차 {rel:.3e}  ptp {rec['rerun'][arm]['ptp_db_new']:.4f} dB "
                  f"(저장 {rec['rerun'][arm]['ptp_db_stored']:.4f})  [{time.time()-t0:.0f}s]",
                  flush=True)

        #  ── 감사 ② 헤드라인 상관의 귀무검정 ──
        for lab, skey in (("ref", "D_sweep"), ("hot", "D_sweep_hot")):
            Eo = E_from_wave(R["arms"][f"{lab}/po_spherical_bistatic"]["matched32"]["wave"])
            ph, H, seeds = sionna_H(JB, key, skey)
            Hm = H.mean(axis=0)
            rec["triviality"][lab] = triviality(Eo, Hm)
            rec["triviality"][lab]["stored_headline_corr"] = \
                R["headline"][lab]["ours_vs_sionna_ac_corr"]
            #  (e) 시드 하나하나와의 상관 — 시드평균이 만든 착시인가
            cs = [ac_corr(Eo, H[i]) for i in range(H.shape[0])]
            #  시드평균 파형 자체의 재현성(시드쌍 상관)도 다시 계산해 대조
            pair = [ac_corr(H[i], H[j]) for i in range(H.shape[0])
                    for j in range(i + 1, H.shape[0])]
            rec["per_seed"][lab] = dict(
                seeds=seeds, corr_ours_vs_each_seed=[float(x) for x in cs],
                mean=float(np.mean(cs)), min=float(np.min(cs)), max=float(np.max(cs)),
                seed_pair_corr_mean=float(np.mean(pair)),
                note_ko=("시드평균과의 상관이 시드개별 상관보다 크게 높으면, 일치의 상당부분은 "
                         "평균이 몬테카를로 잡음을 지운 덕이다."))
            t = rec["triviality"][lab]
            print(f"   [{lab}] 관측 |c|={t['observed_ac_corr']:.4f}  "
                  f"귀무평균={t['null_mean']:.4f} p95={t['null_p95']:.4f}  p={t['p_value']:.4f}  "
                  f"잔차상관={t['residual_ac_corr']:.4f}", flush=True)

        out["airframes"][key] = pc._j(rec)

    #  ── 감사 ③ 특이성 대조 (cross control) ──
    #  ⭐ "우리 PO 가 Sionna 와 닮았다" 가 의미를 가지려면, **틀린 짝**과는 덜 닮아야 한다.
    #     같은 φ 축(0…174.375°, 32점) 위에서 기체·자세를 어긋나게 짝지어 본다.
    ours, sion = {}, {}
    for key in pc.KEYS:
        R = JP["airframes"][key]
        for lab, skey in (("ref", "D_sweep"), ("hot", "D_sweep_hot")):
            ours[(key, lab)] = E_from_wave(
                R["arms"][f"{lab}/po_spherical_bistatic"]["matched32"]["wave"])
            _, H, _ = sionna_H(JB, key, skey)
            sion[(key, lab)] = H.mean(axis=0)
    cross = {}
    for ko, lo in ours:
        for ks, ls in sion:
            c = ac_corr(ours[(ko, lo)], sion[(ks, ls)])
            cross[f"po[{ko}/{lo}] vs sionna[{ks}/{ls}]"] = dict(
                ac_corr=c, matched=bool(ko == ks and lo == ls),
                same_airframe=bool(ko == ks), same_aspect=bool(lo == ls))
    mt = [v["ac_corr"] for v in cross.values() if v["matched"]]
    mm = [v["ac_corr"] for v in cross.values() if not v["matched"]]
    #  ⭐ 올바른 특이성 통계는 **열별 순위**다. Sionna 파형 하나를 표적으로 놓고 우리 PO 팔 4개 중
    #     맞는 짝이 1등인가를 본다. (전역 min-vs-max 는 표적마다 잡음이 달라 성립하지 않는다.)
    cols = {}
    for ks, ls in sion:
        cand = {f"{ko}/{lo}": ac_corr(ours[(ko, lo)], sion[(ks, ls)]) for ko, lo in ours}
        order = sorted(cand.items(), key=lambda kv: -kv[1])
        rank = [k for k, _ in order].index(f"{ks}/{ls}") + 1
        cols[f"sionna[{ks}/{ls}]"] = dict(
            matched_corr=cand[f"{ks}/{ls}"], rank_of_matched=int(rank), n_candidates=len(cand),
            runner_up=order[1][0] if order[0][0] == f"{ks}/{ls}" else order[0][0],
            runner_up_corr=float(order[1][1] if order[0][0] == f"{ks}/{ls}" else order[0][1]),
            margin=float(cand[f"{ks}/{ls}"] -
                         (order[1][1] if order[0][0] == f"{ks}/{ls}" else order[0][1])),
            best_cross_airframe=float(max(v for k, v in cand.items()
                                          if k.split("/")[0] != ks)),
            all_candidates=cand)
    ranks = [v["rank_of_matched"] for v in cols.values()]
    out["cross_control"] = dict(
        pairs=cross, by_sionna_target=cols,
        n_matched=len(mt), n_mismatched=len(mm),
        matched_mean=float(np.mean(mt)), matched_min=float(np.min(mt)),
        mismatched_mean=float(np.mean(mm)), mismatched_max=float(np.max(mm)),
        matched_is_rank1_everywhere=bool(all(r == 1 for r in ranks)),
        n_targets=len(ranks), n_rank1=int(sum(1 for r in ranks if r == 1)),
        min_margin=float(min(v["margin"] for v in cols.values())),
        worst_cross_airframe=float(max(v["best_cross_airframe"] for v in cols.values())),
        note_ko=("같은 φ 축 위에서 기체·자세를 어긋나게 짝지은 상관. 판정은 **열별 순위**로 한다: "
                 "Sionna 파형마다 우리 PO 팔 4개 중 맞는 짝이 1등이어야 '일치가 특이적' 이다. "
                 "⚠ 어긋난 기체 짝은 회전수가 달라 물리적으로 같은 주파수축이 아니다 — "
                 "이것은 물리 비교가 아니라 **형상 특이성** 대조다."))
    print(f"\n[특이성] 맞는 짝이 1등인 표적 {out['cross_control']['n_rank1']}/"
          f"{out['cross_control']['n_targets']}  최소여유={out['cross_control']['min_margin']:+.4f}  "
          f"교차기체 최대={out['cross_control']['worst_cross_airframe']:.4f}", flush=True)

    out["meta"]["seconds_total"] = float(time.time() - t_all)

    #  ── 결론을 코드가 쓴다 (손으로 타이핑 금지) ──
    verdicts = {}
    for key in pc.KEYS:
        A = out["airframes"][key]
        v = {}
        for lab in ("ref", "hot"):
            t = A["triviality"][lab]
            beats_null = bool(t["p_value"] < 0.05)
            res_real = bool(t["residual_p_value"] < 0.05)
            v[lab] = dict(
                headline_corr=t["observed_ac_corr"],
                p_value=t["p_value"], residual_p_value=t["residual_p_value"],
                explained_by_spectrum_shape_alone=not beats_null,
                residual_agreement_beyond_dominant_harmonic=res_real,
                statement_ko=(
                    ("상관 {c:.3f} 은 귀무분포(위상 무작위) 평균 {m:.3f}·p95 {p95:.3f} 를 "
                     + ("넘는다 → 스펙트럼 모양만으로는 설명 안 되는 위상 일치가 있다."
                        if beats_null else
                        "넘지 못한다 → 두 파형이 '닮았다' 는 것은 같은 하모닉에 전력이 몰려 "
                        "있다는 뜻일 뿐, 블레이드 각위치가 일치한다는 뜻이 아니다.")
                     ).format(c=t["observed_ac_corr"], m=t["null_mean"], p95=t["null_p95"])))
        verdicts[key] = v
    out["verdict"] = verdicts

    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pc._j(out), f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print(f"\n[저장] {OUT}  ({time.time()-t_all:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
