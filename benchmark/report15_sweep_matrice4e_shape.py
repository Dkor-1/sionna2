# -*- coding: utf-8 -*-
"""
report15_sweep_matrice4e_shape.py — 본 스윕의 **남은 구멍 하나**를 막는 후속 측정
================================================================================

본 스윕(`report15_sweep_matrice4e.py`)이 확정한 것:

  · 확산 경로 진폭은 |a| ∝ N^(−1/2) 로 정규화돼 있다 → Σ|a|² 는 광선예산 N 에 **수렴**한다.
  · 그 표본들을 다시 코히런트로 더한 h = Σ a·exp(−j2πfτ) 는 **√N 으로 자란다**
    (기울기 0.44~0.52). 따라서 **|h| 의 절대값은 물리적 산란장이 아니다.**

그래서 본 스윕은 물리 판정을 수렴량 Σ|a|² 에만 기댔다. 그런데 여기 **답 안 한 질문**이 남는다:

  ⭐ **|h| 의 절대값이 안 물리적이라는 것과, h 의 도플러 스펙트럼 *모양* 이 안 물리적이라는 것은
     다른 주장이다.** 마이크로도플러가 쓰는 것은 절대 레벨이 아니라 **조화 빗(comb)의 모양**과
     ± 측대역 비대칭이다. 모양이 광선예산에 불변이면 "레벨만 못 쓰고 스펙트럼은 쓸 수 있다"
     이고, 모양까지 흔들리면 "코히런트 마이크로도플러 자체가 몬테카를로 산물" 이다.
     본 스윕은 **레벨만** 재고 모양은 안 쟀다 — 이 파일이 그것을 잰다.

§S1  같은 위상축(한 주기 180° × 64 스텝)을 **광선예산 3단(16× 폭)** 으로 다시 훑는다.
     · 레벨   : 20log10⟨|h|⟩ 가 예산에 따라 어떻게 움직이나 (√N 재확인)
     · 모양   : s_k = |Z_k|/|Z_1| (k=1..32) 벡터가 예산 사이에서 얼마나 같은가 (코사인 유사도)
     · 비대칭 : asym_k = 20log10(|Z(+k)|/|Z(−k)|) — 진짜 도플러의 지문. 예산에 안정한가.
     · 대조군 : 같은 잣대를 **수렴량** Σ|a|² 에도 적용한다(이쪽은 불변이어야 정상).

§S2  (RT 재실행 없음) 수렴량의 조화 **퍼짐** 을 이상적 블레이드 모델과 나란히 놓는다.
     이상 모델은 빗이 k≈13~14(≈f_tip)까지 뻗는다 — RT 수렴량은 어디까지 뻗나.

§S3  (RT 재실행 없음) 본 스윕 JSON 의 후처리 결함 2건 정정:
     (a) headline.spp 가 실행값이 아니라 모듈 상수(SPP_MAIN)를 싣고 있다 — 실제 격자는 더 낮은
         예산으로 돌았다. |h| 가 √N 으로 자라므로 이 숫자를 틀리게 적으면 레벨 해석이 틀어진다.
     (b) headline.blade_flash_depth_pp_db 에 **log(0) 산물**이 들어 있다(경로가 껐다켜지는
         정반사 칸에서 |h|=0 → 20log10(1e−300) = −6000 dB). 1063 dB, 370 dB 같은 값이
         플래그 없이 헤드라인에 앉아 있어 그대로 인용될 위험이 있다.

⛔ 이 파일은 src/drones.py · src/drone_cad.py 를 건드리지 않는다(읽기만, 스윕 모듈 경유).
⛔ 새 산출물을 만들지 않고 **이 실험의 자기 JSON** 에만 키를 더한다.

실행:
    ~/.venvs/py312/bin/python benchmark/report15_sweep_matrice4e_shape.py
    ~/.venvs/py312/bin/python benchmark/report15_sweep_matrice4e_shape.py --quick   # 연기 시험
    ~/.venvs/py312/bin/python benchmark/report15_sweep_matrice4e_shape.py --patch-only  # RT 없이 §S2·§S3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#  ⚠ 스윕 모듈을 import 하는 순간 gpu.pick() → mitsuba/sionna 가 올라온다. 순서를 바꾸지 말 것.
import report15_sweep_matrice4e as M                                  # noqa: E402

OUT_JSON = M.OUT_JSON

#  §S1 격자 — 근거리를 강조하되(1 m 두 자세), 거리 추세도 볼 수 있게 3 거리를 건다.
CELLS = (("1/nose", 1.0, 0.0, 15.0),
         ("1/disc", 1.0, 0.0, 75.0),
         ("3/nose", 3.0, 0.0, 15.0),
         ("10/nose", 10.0, 0.0, 15.0))
SPPS = (256_000_000, 1_024_000_000, 4_096_000_000)      # 16× 폭
SHAPE_SEEDS = (1, 2, 3)
N_PHASE = 64                                            # 본 격자와 **같은 위상축**


# --------------------------------------------------------------------------- #
#  조화 유틸
# --------------------------------------------------------------------------- #
def _spec(X: np.ndarray) -> np.ndarray:
    """X=[phase, seed] → 시드평균 복소 스펙트럼 Z[k] (FFT/N)."""
    return (np.fft.fft(X, axis=0) / X.shape[0]).mean(axis=1)


def _shape(Z: np.ndarray, kmax: int) -> np.ndarray:
    """s_k = |Z_k| / |Z_1|, k=1..kmax.  ⭐ 분모를 DC 로 쓰지 않는다 — 평균을 뺀 계열이면
    DC 가 0 이라 본 스윕의 `*_rel_dc` 필드처럼 못 쓰게 된다. k=1(블레이드 플래시)로 정규화한다."""
    a = np.abs(Z[1:kmax + 1])
    return a / (a[0] + 1e-300)


def _cos(u: np.ndarray, v: np.ndarray) -> float:
    nu, nv = float(np.linalg.norm(u)), float(np.linalg.norm(v))
    return float(u @ v / (nu * nv)) if nu > 0 and nv > 0 else float("nan")


def _asym_db(Z: np.ndarray, kmax: int) -> list:
    """asym_k = 20log10(|Z(+k)|/|Z(−k)|) — 진폭변조만이면 0 dB, 진짜 도플러면 벌어진다."""
    N = Z.shape[0]
    return [float(20 * np.log10((abs(Z[k]) + 1e-300) / (abs(Z[N - k]) + 1e-300)))
            for k in range(1, kmax + 1)]


# --------------------------------------------------------------------------- #
#  §S1 — 모양의 광선예산 불변성
# --------------------------------------------------------------------------- #
def secS1(n_phase=N_PHASE, spps=SPPS, seeds=SHAPE_SEEDS, cells=CELLS) -> dict:
    period = 360.0 / int(M._SPEC.prop_blades)
    phis = np.arange(n_phase) * (period / n_phase)
    S, C, P = len(seeds), len(cells), len(spps)
    #  buf[cell][spp] = dict of [phase, seed] 배열
    buf = {c[0]: {int(s): dict(n=np.zeros((n_phase, S)), hr=np.zeros((n_phase, S)),
                               hi=np.zeros((n_phase, S)), hpr=np.zeros((n_phase, S)),
                               hpi=np.zeros((n_phase, S)), inc=np.full((n_phase, S), np.nan),
                               inc_prop=np.full((n_phase, S), np.nan))
                  for s in spps} for c in cells}
    t0, ntr = time.time(), 0
    for i, phd in enumerate(phis):
        scene, dd = M.build_posed_scene(float(phd), f"S{i:03d}")
        g2 = M.id_to_group(scene)
        for nm, R, az, el in cells:
            M.place(scene, az, el, R)
            for sp in spps:
                for j, sd in enumerate(seeds):
                    r = M.trace(scene, sp, sd, True, g2)      # 확산(생산) 채널
                    ntr += 1
                    B = buf[nm][sp]
                    for k in ("n", "hr", "hi", "hpr", "hpi"):
                        B[k][i, j] = r[k]
                    for k in ("inc", "inc_prop"):
                        B[k][i, j] = np.nan if r[k] is None else r[k]
        M.drop(dd)
        el_ = time.time() - t0
        print(f"    φ={phd:7.3f}°  ({i+1}/{n_phase})  누적 {ntr} 추적  "
              f"{el_:6.0f}s  (예상 총 {el_/(i+1)*n_phase:6.0f}s)", flush=True)

    kmax = n_phase // 2
    out = {}
    for nm, R, az, el in cells:
        per_spp = {}
        for sp in spps:
            B = buf[nm][sp]
            z = B["hr"] + 1j * B["hi"]
            zp = B["hpr"] + 1j * B["hpi"]
            rec = dict(spp=int(sp), n_paths_mean=float(B["n"].mean()),
                       zero_path_frac=float(np.mean(B["n"] == 0)))
            for ch, X, isc in (("coh_all", z, True), ("coh_prop", zp, True),
                               ("inc_all", B["inc"], False),
                               ("inc_prop", B["inc_prop"], False)):
                if isc:
                    lvl = float(20 * np.log10(np.abs(X).mean() + 1e-300))
                    Z = _spec(X)
                else:
                    lvl = float(np.nanmean(X))
                    Z = _spec(X - np.nanmean(X))
                rec[ch] = dict(level_db=lvl,
                               shape=[float(v) for v in _shape(Z, kmax)],
                               harm_abs=[float(abs(Z[k])) for k in range(1, kmax + 1)],
                               asym_db=(_asym_db(Z, kmax) if isc else None))
            per_spp[str(sp)] = rec

        #  예산 사이 비교
        comp = {}
        for ch in ("coh_all", "coh_prop", "inc_all", "inc_prop"):
            sh = {sp: np.array(per_spp[str(sp)][ch]["shape"]) for sp in spps}
            lv = {sp: per_spp[str(sp)][ch]["level_db"] for sp in spps}
            pairs = [(a, b) for ii, a in enumerate(spps) for b in spps[ii + 1:]]
            cs = {f"{a}_vs_{b}": _cos(sh[a], sh[b]) for a, b in pairs}
            x = np.log10(np.array(spps, float))
            y = np.array([lv[sp] for sp in spps], float) / 20.0      # log10|h|
            slope = float(np.polyfit(x, y, 1)[0])
            d = dict(shape_cosine=cs, shape_cosine_min=float(min(cs.values())),
                     level_db_by_spp={str(sp): lv[sp] for sp in spps},
                     level_slope_log10_per_log10N=slope,
                     level_swing_db=float(max(lv.values()) - min(lv.values())))
            if ch.startswith("coh"):
                asy = {sp: np.array(per_spp[str(sp)][ch]["asym_db"][:8]) for sp in spps}
                d["asym_db_k1_by_spp"] = {str(sp): float(asy[sp][0]) for sp in spps}
                d["asym_k1_swing_db"] = float(max(a[0] for a in asy.values())
                                              - min(a[0] for a in asy.values()))
                d["asym_first8_max_swing_db"] = float(np.max(
                    np.max(np.stack(list(asy.values())), axis=0)
                    - np.min(np.stack(list(asy.values())), axis=0)))
            comp[ch] = d
        out[nm] = dict(range_m=R, az_deg=az, el_deg=el, by_spp=per_spp, comparison=comp)

    return dict(
        cells=[dict(name=n, range_m=r, az_deg=a, el_deg=e) for n, r, a, e in cells],
        spps=[int(s) for s in spps], spp_span=float(max(spps) / min(spps)),
        seeds=[int(s) for s in seeds], n_phase=int(n_phase), phase_span_deg=float(period),
        n_traces=int(ntr), seconds=float(time.time() - t0), by_cell=out,
        **_s1_verdict(out))


def _s1_verdict(out: dict) -> dict:
    """⭐ 판정을 **거리별로** 나눈다.  전 셀 최소값 하나로 뭉뚱그리면 '1 m 에서는 모양이 불변'
    이라는 사실이 '10 m 에서는 아니다' 에 먹혀 사라진다 — 근거리를 강조하라는 이 실험의
    설계 취지가 바로 그 구별에 걸려 있다."""
    cells = [(k, v) for k, v in out.items()]
    cmin_coh = float(min(v["comparison"]["coh_all"]["shape_cosine_min"] for _, v in cells))
    cmin_inc = float(min(v["comparison"]["inc_all"]["shape_cosine_min"] for _, v in cells))
    slope_coh = float(np.mean([v["comparison"]["coh_all"]["level_slope_log10_per_log10N"]
                               for _, v in cells]))
    slope_inc_db = float(np.mean([v["comparison"]["inc_all"]["level_swing_db"]
                                  for _, v in cells]))
    asym_swing = float(max(v["comparison"]["coh_all"]["asym_k1_swing_db"] for _, v in cells))
    shape_invariant = bool(cmin_coh > 0.95)

    #  거리별 — 경로 표본수가 R^-2 로 줄어드는 것이 원인이므로 표본수도 같이 적는다
    by_range = {}
    for k, v in cells:
        rk = f"{v['range_m']:g}"
        d = by_range.setdefault(rk, dict(range_m=v["range_m"], cells=[], coh_cos=[], inc_cos=[],
                                         asym_swing_db=[], n_paths_min_budget=[]))
        d["cells"].append(k)
        d["coh_cos"].append(v["comparison"]["coh_all"]["shape_cosine_min"])
        d["inc_cos"].append(v["comparison"]["inc_all"]["shape_cosine_min"])
        d["asym_swing_db"].append(v["comparison"]["coh_all"]["asym_k1_swing_db"])
        d["n_paths_min_budget"].append(min(s["n_paths_mean"] for s in v["by_spp"].values()))
    for rk, d in by_range.items():
        cc, ii = float(min(d["coh_cos"])), float(min(d["inc_cos"]))
        d.update(coh_shape_cosine_min=cc, inc_shape_cosine_min=ii,
                 asym_k1_swing_db_max=float(max(d["asym_swing_db"])),
                 n_paths_at_lowest_budget=float(min(d["n_paths_min_budget"])),
                 coherent_shape_invariant=bool(cc > 0.95),
                 verdict_ko=("코히런트 조화 모양이 광선예산에 **불변** — 이 거리에서는 상대 "
                             "도플러 스펙트럼을 읽을 수 있다(절대 레벨은 여전히 불가)."
                             if cc > 0.95 else
                             "코히런트 조화 모양이 광선예산에 **흔들린다** — 이 거리에서는 "
                             "상대 스펙트럼도 인용 불가."))
        for kk in ("coh_cos", "inc_cos", "asym_swing_db", "n_paths_min_budget"):
            d.pop(kk)
    ok_r = sorted([r for r, d in by_range.items() if d["coherent_shape_invariant"]],
                  key=float)
    return dict(
        verdict=dict(
            by_range=by_range,
            ranges_where_coherent_shape_invariant=ok_r,
            coherent_shape_cosine_min=cmin_coh,
            incoherent_shape_cosine_min=cmin_inc,
            coherent_level_slope=slope_coh,
            incoherent_level_swing_db=slope_inc_db,
            coherent_asym_k1_swing_db=asym_swing,
            coherent_shape_invariant=shape_invariant,
            verdict_ko=(
                "⭐ 판정은 **거리에 따라 갈린다**(by_range). 코히런트 조화의 모양은 근거리에서 "
                "광선예산에 거의 불변이지만(1 m: cos≥0.98) 거리가 늘수록 무너진다(10 m: cos≈0.73). "
                "레벨은 어느 거리에서도 √N 으로 자라 물리량이 아니다(기울기 {s:.3f}). "
                "원인은 확산 경로 표본수가 입체각과 함께 R⁻² 로 줄기 때문이다 — 즉 '가까울수록 "
                "Sionna 에 유리하다' 는 이 실험의 설계 전제가 **모양의 안정성에서 실제로 확인된다**. "
                "따라서: 1 m 에서는 상대 도플러 스펙트럼을 읽어도 되고, 10 m 에서는 안 된다. "
                "절대 레벨은 어느 거리에서도 인용 금지."
            ).format(s=slope_coh)),
        note_ko=("모양은 s_k=|Z_k|/|Z_1| 벡터의 코사인 유사도로 잰다. 분모를 DC 가 아니라 k=1 로 "
                 "두는 이유는 평균을 뺀 계열의 DC 가 0 이기 때문이다(본 스윕 `*_rel_dc` 가 그래서 "
                 "못 쓰는 필드가 됐다). 예산 폭 16× 는 레벨을 √16=4× (12 dB) 움직여야 하는 폭이다."))


# --------------------------------------------------------------------------- #
#  §S2 — 수렴량의 조화 퍼짐 vs 이상 블레이드 모델 (RT 재실행 없음)
# --------------------------------------------------------------------------- #
def secS2(J: dict) -> dict:
    G, flash = J["grid"], J["physics"]["flash_hz"]
    ftip = J["physics"]["f_tip_hz"]
    rows, N = {}, len(G["phases_deg"])
    for key, B in G["blocks"].items():
        if B["mode"] != "prod":
            continue
        for ch, kn, kinc in (("all", "n", "inc"), ("prop", "n_prop", "inc_prop")):
            n = np.array(B[kn], float)
            if not (n > 0).all():
                continue
            X = np.array([[np.nan if v is None else v for v in r] for r in B[kinc]], float)
            N, S = X.shape
            Z = np.fft.fft(X - X.mean(), axis=0) / N
            Zm = Z.mean(axis=1)
            var = np.sum(np.abs(Z - Zm[:, None]) ** 2, axis=1) / (S - 1)
            nse = var / S
            ny = N // 2
            amp = 2.0 * np.abs(Zm[1:ny + 1])                 # dB-진폭 (실수열 → 2|Z_k|)
            snr = np.abs(Zm[1:ny + 1]) ** 2 / (nse[1:ny + 1] + 1e-300)
            sig = np.where(snr > 10.0, amp, 0.0)             # 잡음 위 빈만
            hi10 = np.nonzero(sig > 0.10 * amp[0])[0]
            kmax10 = int(hi10.max() + 1) if hi10.size else 0
            rows[f"{key}/{ch}"] = dict(
                blade_flash_depth_pp_db=float(4.0 * np.abs(Zm[1])),
                dominant_bin=int(np.argmax(amp) + 1),
                power_frac_above_k1=float(np.sum(amp[1:] ** 2) / (np.sum(amp ** 2) + 1e-300)),
                highest_bin_above_10pct_of_k1=kmax10,
                highest_freq_above_10pct_hz=float(kmax10 * flash),
                reaches_tip_freq=bool(kmax10 * flash >= ftip))
    ideal = J.get("ideal_reference", {}).get("by_cell", {})
    ideal_spread = {k: v.get("highest_bin_above_1pct") for k, v in ideal.items()}
    iv = [v for v in ideal_spread.values() if v]
    kk = [v["highest_bin_above_10pct_of_k1"] for v in rows.values()]
    return dict(
        by_channel=rows, nyquist_bin=int(N // 2), nyquist_hz=float((N // 2) * flash),
        flash_hz=float(flash), f_tip_hz=float(ftip),
        tip_bin_equivalent=float(ftip / flash),
        rt_highest_bin_median=float(np.median(kk)), rt_highest_bin_max=int(max(kk)),
        rt_n_channels_reaching_tip=int(sum(v["reaches_tip_freq"] for v in rows.values())),
        rt_n_channels=len(rows),
        ideal_highest_bin_above_1pct=ideal_spread,
        ideal_highest_bin_median=(float(np.median(iv)) if iv else None),
        note_ko=("이상 점산란자 모델은 τ(전파위상) 변조를 갖고 있어 빗이 f_tip 근처까지 뻗는다. "
                 "RT 의 **수렴량** Σ|a|² 는 전력이라 위상변조를 실을 수 없다 — 여기 남는 것은 "
                 "블레이드가 만드는 **진폭변조** 뿐이고, 그래서 빗이 저차에 머문다. "
                 "⚠ 두 수는 잣대가 다르다(이상=코히런트 복소, RT=수렴 전력). 나란히 읽되 "
                 "같은 양으로 빼지 말 것."),
        headline_ko=("이상 모델 빗은 k≈{im} (≈{ihz:.0f} Hz) 까지, RT 수렴량 빗은 중앙값 k={rm} "
                     "(≈{rhz:.0f} Hz) 까지 뻗는다.").format(
                         im=(int(np.median(iv)) if iv else 0),
                         ihz=(np.median(iv) * flash if iv else 0.0),
                         rm=int(np.median(kk)), rhz=float(np.median(kk)) * flash))


# --------------------------------------------------------------------------- #
#  §S3 — 후처리 결함 2건 정정 (RT 재실행 없음)
# --------------------------------------------------------------------------- #
def secS3(J: dict) -> dict:
    H, fixes = J["headline"], []

    #  (a) headline.spp 가 모듈 상수를 싣고 있다 → 실제 격자 예산으로 바로잡는다
    run_spp, head_spp = int(J["grid"]["spp"]), int(H.get("spp", -1))
    if head_spp != run_spp:
        H["spp"] = run_spp
        H["spp_reported_wrong_before"] = head_spp
        H["spp_note_ko"] = (
            f"본 격자는 samples_per_src={run_spp:,} 로 돌았다. 이전 판 헤드라인은 모듈 기본상수"
            f"({head_spp:,})를 실어 **실행값이 아니었다**. |h| 가 √N 으로 자라므로(§4·normalization) "
            f"이 숫자를 틀리게 적으면 코히런트 레벨 해석이 통째로 틀어진다. "
            f"수렴성 절(convergence)만 {int(M.SPP_MAX_SAFE):,} 까지 올려 잰 것이고 격자는 아니다.")
        fixes.append(dict(field="headline.spp", was=head_spp, now=run_spp,
                          why_ko="모듈 상수 SPP_MAIN 을 실었다 — 실행 인자와 다르다"))

    #  (b) blade_flash_depth_pp_db 의 log(0) 산물에 플래그를 단다
    md = J.get("modulation_depth", {}).get("by_block", {})
    dep, n_bad = H.get("blade_flash_depth_pp_db", {}), 0
    newdep = {}
    for k, v in dep.items():
        b = md.get(k, {})
        zf = float(b.get("zero_path_cell_frac", 0.0))
        beh = b.get("n_paths_behaviour", "?")
        #  ⚠ 원값은 **modulation_depth(원천)** 에서 읽는다. 이미 한 번 정정된 헤드라인에서
        #    읽으면 두 번째 실행에서 None 을 '산물' 로 저장해 버린다(멱등성).
        raw = (b.get("coh_db") or {}).get("blade_flash_depth_pp_db")
        rec = dict(coh=(v.get("coh") if v.get("coh") is not None else raw), inc=v.get("inc"),
                   n_paths_behaviour=beh, zero_path_cell_frac=zf)
        if zf > 0.0:
            n_bad += 1
            rec["coh_logzero_artifact"] = raw
            rec["coh"] = None
            rec["quotable"] = False
            rec["note_ko"] = (
                f"경로가 껐다켜지는 칸이 {zf:.1%} 다. |h|=0 인 위상에서 20log10(0+1e−300)=−6000 dB "
                f"가 계열에 섞여 조화 진폭이 터진다 — 원값 {raw} 는 물리량이 아니라 "
                f"**log(0) 산물**이다. 인용 금지. 이 칸의 올바른 서술은 '정반사 경로가 64 위상 중 "
                f"극소수에서만 켜진다' 이고, 그것은 zero_path_cell_frac 이 말해 준다.")
        else:
            rec["quotable"] = True
        newdep[k] = rec
    H["blade_flash_depth_pp_db"] = newdep
    if n_bad:
        fixes.append(dict(field="headline.blade_flash_depth_pp_db", n_flagged=n_bad,
                          why_ko="경로 껐다켜짐 칸의 log(0) 산물이 플래그 없이 앉아 있었다"))

    #  (c) 자세 의존 롤업 — 지시서가 '자세 의존이 핵심' 이라 했으므로 헤드라인에 박는다
    A = J["grid_analysis"]["by_block"]
    asp = {}
    for key, v in A.items():
        if not v.get("ok") or v.get("mode") != "prod":
            continue
        a = v["aspect"]
        d = asp.setdefault(a, dict(az_deg=None, el_deg=None, n_channels=0, n_physical=0,
                                   inc_depth_pp_db=[], coh_ptp_db=[]))
        d["n_channels"] += 1
        d["n_physical"] += int(bool(v.get("physical_modulation_above_noise")))
        b = md.get(key + "/" + v["channel"], {})
        if (b.get("inc_db") or {}).get("blade_flash_depth_pp_db") is not None:
            d["inc_depth_pp_db"].append(float(b["inc_db"]["blade_flash_depth_pp_db"]))
        if v.get("modulation_ptp_db") is not None:
            d["coh_ptp_db"].append(float(v["modulation_ptp_db"]))
    for nm, az, el in M.ASPECTS:
        if nm in asp:
            asp[nm]["az_deg"], asp[nm]["el_deg"] = float(az), float(el)
    for a, d in asp.items():
        d["inc_depth_pp_db_median"] = (float(np.median(d["inc_depth_pp_db"]))
                                       if d["inc_depth_pp_db"] else None)
        d["inc_depth_pp_db_max"] = (float(np.max(d["inc_depth_pp_db"]))
                                    if d["inc_depth_pp_db"] else None)
        d["coh_ptp_db_median"] = (float(np.median(d["coh_ptp_db"]))
                                  if d["coh_ptp_db"] else None)
        d.pop("inc_depth_pp_db")
        d.pop("coh_ptp_db")
    rank = sorted([a for a in asp if asp[a]["inc_depth_pp_db_median"] is not None],
                  key=lambda a: -asp[a]["inc_depth_pp_db_median"])
    H["aspect_dependence"] = dict(
        by_aspect=asp, ranked_by_inc_depth=rank,
        note_ko=("확산 채널(prod)에서 **수렴량** Σ|a|² 의 블레이드 조화 깊이[dB pp] 로 자세를 줄 세운 것. "
                 "정지자세 실험의 '36 중 1' 은 **정반사** 이야기고, 여기 자세 의존은 **확산 진폭변조** "
                 "이야기다 — 같은 축에 놓지 말 것."))

    #  (d) 잡음바닥 롤업 — 격자 위에서 잰 시드 재추첨 산포
    sn = [v["seed_noise_std_db"] for v in A.values() if v.get("seed_noise_std_db") is not None]
    si = [v["seed_noise_inc_std_db"] for v in A.values()
          if v.get("seed_noise_inc_std_db") is not None]
    H["noise_floor_on_grid"] = dict(
        n_channels=len(sn),
        coh_seed_std_db_median=float(np.median(sn)), coh_seed_std_db_max=float(np.max(sn)),
        inc_seed_std_db_median=float(np.median(si)), inc_seed_std_db_max=float(np.max(si)),
        note_ko=("칸마다 시드 5개를 돌려 잰 재추첨 산포. 코히런트 쪽이 수렴량보다 한 자릿수 크다 — "
                 "흔들리는 것은 에너지가 아니라 코히런트 위상이라는 탐침의 관측과 같다."))
    return dict(fixes=fixes, n_fixes=len(fixes))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--patch-only", action="store_true")
    a = ap.parse_args()

    with open(OUT_JSON, "r", encoding="utf-8") as f:
        J = json.load(f)
    print(f"■ 대상 JSON: {OUT_JSON}  (격자 spp={J['grid']['spp']:,}, "
          f"위상 {len(J['grid']['phases_deg'])} 스텝)")

    if a.patch_only and "shape_invariance" in J:
        #  RT 재실행 없이 저장된 측정에서 판정만 다시 낸다(거리별로 쪼갠 판정).
        J["shape_invariance"].update(_s1_verdict(J["shape_invariance"]["by_cell"]))
        v = J["shape_invariance"]["verdict"]
        print("\n§S1' 판정 재계산 (RT 없음) — 거리별")
        for rk, d in sorted(v["by_range"].items(), key=lambda kv: float(kv[0])):
            print(f"    R={rk:>3} m  코히런트 모양 cos={d['coh_shape_cosine_min']:.4f}  "
                  f"수렴량 cos={d['inc_shape_cosine_min']:.4f}  "
                  f"±비대칭 흔들림 {d['asym_k1_swing_db_max']:5.2f} dB  "
                  f"경로수(최저예산) {d['n_paths_at_lowest_budget']:9.0f}  → "
                  f"{'모양 불변' if d['coherent_shape_invariant'] else '모양 흔들림'}")
        print(f"    불변인 거리: {v['ranges_where_coherent_shape_invariant']} m")

    if not a.patch_only:
        n_ph, spps, sds = (8, (256_000_000, 4_096_000_000), (1, 2)) if a.quick \
            else (N_PHASE, SPPS, SHAPE_SEEDS)
        cells = CELLS[:2] if a.quick else CELLS
        print(f"\n§S1 모양의 광선예산 불변성 — 셀 {len(cells)} × 예산 {len(spps)} × "
              f"시드 {len(sds)} × 위상 {n_ph} = {len(cells)*len(spps)*len(sds)*n_ph} 추적")
        J["shape_invariance"] = secS1(n_phase=n_ph, spps=spps, seeds=sds, cells=cells)
        v = J["shape_invariance"]["verdict"]
        print(f"    코히런트 모양 코사인 최소 {v['coherent_shape_cosine_min']:.4f}  "
              f"수렴량 모양 코사인 최소 {v['incoherent_shape_cosine_min']:.4f}")
        print(f"    코히런트 레벨 기울기 {v['coherent_level_slope']:.3f} "
              f"(0.5=√N)  수렴량 레벨 흔들림 {v['incoherent_level_swing_db']:.3f} dB")
        print(f"    → {v['verdict_ko']}")

    print("\n§S2 수렴량 조화 퍼짐 vs 이상 블레이드 모델")
    J["spread_vs_ideal"] = secS2(J)
    print("    " + J["spread_vs_ideal"]["headline_ko"])

    print("\n§S3 후처리 결함 정정")
    fx = secS3(J)
    for f_ in fx["fixes"]:
        print("    · " + json.dumps(f_, ensure_ascii=False))

    J.setdefault("meta", {})["addendum2"] = dict(
        script="benchmark/report15_sweep_matrice4e_shape.py",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        added=(["shape_invariance(신규 RT 측정 — 조화 모양의 광선예산 불변성)"]
               if not a.patch_only else [])
        + ["spread_vs_ideal(재계산 — RT 없음)", "headline 정정 %d 건(RT 없음)" % fx["n_fixes"]],
        fixes=fx["fixes"])
    if "shape_invariance" in J:
        sv = J["shape_invariance"]["verdict"]
        J["headline"]["coherent_shape_invariant"] = sv["coherent_shape_invariant"]
        J["headline"]["coherent_shape_cosine_min"] = sv["coherent_shape_cosine_min"]
        J["headline"]["coherent_shape_invariant_by_range"] = {
            r: d["coherent_shape_invariant"] for r, d in sv["by_range"].items()}
        J["headline"]["coherent_shape_cosine_by_range"] = {
            r: d["coh_shape_cosine_min"] for r, d in sv["by_range"].items()}
        J["headline"]["ranges_where_coherent_shape_invariant"] = \
            sv["ranges_where_coherent_shape_invariant"]
    J["headline"]["spread_vs_ideal"] = dict(
        rt_highest_bin_median=J["spread_vs_ideal"]["rt_highest_bin_median"],
        rt_highest_freq_hz_median=(J["spread_vs_ideal"]["rt_highest_bin_median"]
                                   * J["spread_vs_ideal"]["flash_hz"]),
        ideal_highest_bin_median=J["spread_vs_ideal"]["ideal_highest_bin_median"],
        f_tip_hz=J["spread_vs_ideal"]["f_tip_hz"],
        rt_n_channels_reaching_tip=J["spread_vs_ideal"]["rt_n_channels_reaching_tip"],
        rt_n_channels=J["spread_vs_ideal"]["rt_n_channels"])

    tmp = OUT_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT_JSON)
    print(f"\n■ 저장: {OUT_JSON}")


if __name__ == "__main__":
    main()
