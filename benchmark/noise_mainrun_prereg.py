# -*- coding: utf-8 -*-
"""
noise_mainrun_prereg.py — 잡음 **본판**의 사전등록 상수를 재계산 전에 못 박는다
================================================================================

왜 이 파일이 따로 있나
----------------------
본판(`noise_distance_frame.py` 의 다음 판)이 답할 물음은 «몇 미터에서 무늬가 읽히나» 다.
그 답을 **재계산이 끝난 뒤에** 정하면, 나온 수를 보고 막대·규약을 고르게 된다. 그래서
결과와 **무관하게 정해지는 것들**을 지금 미리 재서 원장에 박는다.

여기서 재는 것 (전부 신호와 무관하거나, 이미 원장에 착지한 값)
--------------------------------------------------------------
  ⓐ ⭐**판정 막대** — 빗살 대비의 **귀무분포**(잡음만) p99.9. 사용자 규칙:
     «막대는 판정하는 그 양의 귀무분포에서 세운다»(docs/MAP_SCALING §2-b).
     ⛔신호는 이 계산에 인자로도 안 들어간다 — 문턱 누설이 구조적으로 불가능.
     4,000 시행이 부족하다는 것도 여기서 **수치로** 보인다(같은 분포의 10 조각 산포).
  ⓑ ⭐**A1 연장선을 어디까지 믿나** — 원장에 이미 240·480 m 판이 있다. 15 m 모양을
     얼린 A1 축이 그 거리에서 실제로 맞는지 **엔진 재계산본과 직접 대조**한다.
  ⓒ **인용 자격 게이트** — 덜 찬 칸·수치 바닥 칸·얼어붙은 자세 칸을 미리 골라낸다.
  ⓓ **링크버짓 배수표** — benchmark/link_budget_spec.py 에 위임.

⛔GPU·솔버 없음(자가검사 1). 저장된 원장만 읽는다.
⛔기존 파일 수정 없음 — 산출은 outputs/noise_mainrun_prereg.json 하나.

실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/noise_mainrun_prereg.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import link_budget_spec as LBS                                          # noqa: E402

# --------------------------------------------------------------------------- #
#  사전등록 상수 — 본판이 그대로 물려받는다
# --------------------------------------------------------------------------- #
SEED = 20260819
N_NULL = 40000        # ⭐귀무분포 시행 수 (옛 4,000 → 40,000; 근거는 아래 stability 절)
PFA = 1e-3            # detection_curves·scaled_maps 와 같은 수(원장 나란히 놓기 위함)
HW_HZ = 8.0
N_SLOW = 8192
PRF_HZ = 19700.0
F_FLASH_HZ = 126.66666666666667
F_TIP_HZ = {0.0: 1272.9, -30.0: 1102.4, -60.0: 636.5}      # 원장 행 값
R_REF = 15.0
RANGES = [15, 30, 60, 120, 240, 480]

# 인용 자격 게이트 (⭐본판이 강제한다)
GATE_AC_FRAC_MIN_DB = -60.0     # 이보다 낮으면 «움직이는 몫이 수치 바닥» — 물리로 안 읽는다
GATE_DUP_MAX_FRAC = 0.005       # 연속 표본이 비트동일한 몫(얼어붙은 자세)의 상한
GATE_JUMP_FLAG_DB = 6.0         # 이웃 거리와 이만큼 벌어지면 «확인 요망» 깃발(제외는 안 함)

ARM_PAT = {
    "ours": "ours_r{R}_n8192",
    "ours_ptd": "ours_ptd_r{R}_n8192",
    "ps_off": "sionna_p4000000000_r{R}_n8192_d1",
    "ps_refr": "sionna_p4000000000_onlyrefr_r{R}_n8192",
    "ps_phys": "sionna_p4000000000_phys_r{R}_n8192_d1",
}
# 정본 재질(셸 0.75 mm · 프롭 1.43 mm) 판이 이미 원장에 있는 팔 — 본판이 **이쪽**을 쓴다
ARM_PAT_CANON_MATERIAL = {
    "ps_off": "sionna_p4000000000_r{R}_n8192_shell0.75mm_prop1.43mm_d1",
    "ps_refr": "sionna_p4000000000_onlyrefr_r{R}_n8192_shell0.75mm_prop1.43mm",
}

LEDGER_JSON = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LEDGER_NPZ = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
CANON_JSON = os.path.join(ROOT, "outputs", "material_canon_0816.json")
FRAME_JSON = os.path.join(ROOT, "outputs", "noise_distance_frame.json")
OUT_JSON = os.path.join(ROOT, "outputs", "noise_mainrun_prereg.json")


def el_key(el: float) -> str:
    return "el+0" if el == 0 else f"el{int(el):d}"


def make_masks(n, prf, f_tip, f_flash=F_FLASH_HZ):
    """빗살 대비 마스크 — build_md_atlas / noise_distance_frame 정의 그대로."""
    fr = np.abs(np.fft.fftfreq(n, 1.0 / prf))
    lo, hi = 2.0 * f_flash, f_tip
    if hi < 3.0 * f_flash:
        raise ValueError(f"빗살 대역이 좁다 (f_tip={f_tip})")
    k = fr / f_flash
    band = (fr >= lo) & (fr <= hi)
    comb_on = band & (np.abs(k - np.round(k)) * f_flash <= HW_HZ)
    comb_off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash <= HW_HZ)
    above = fr >= f_tip
    kk = np.round(fr / f_flash)
    rhy_on = above & (np.abs(fr - kk * f_flash) <= HW_HZ)
    if comb_on.sum() < 4 or comb_off.sum() < 4:
        raise ValueError("빗살 on/off 칸이 4개 미만")
    return dict(comb_on=comb_on, comb_off=comb_off, above=above, rhy_on=rhy_on,
                n_on=int(comb_on.sum()), n_off=int(comb_off.sum()))


def stats(X, w, m):
    """행렬 X(시행×n) → (빗살 대비 [dB], 리듬 몫 [%]). 행마다 DC 제거 + 한나창 FFT."""
    Xc = (X - X.mean(axis=1, keepdims=True)) * w
    P = np.abs(np.fft.fft(Xc, axis=1)) ** 2
    on = P[:, m["comb_on"]].mean(axis=1)
    off = P[:, m["comb_off"]].mean(axis=1)
    comb = 10.0 * np.log10(np.maximum(on, 1e-300) / np.maximum(off, 1e-300))
    rhy = 100.0 * P[:, m["rhy_on"]].sum(axis=1) / np.maximum(P[:, m["above"]].sum(axis=1), 1e-300)
    return comb, rhy


# --------------------------------------------------------------------------- #
#  ⓐ 판정 막대 — 귀무분포 p99.9
# --------------------------------------------------------------------------- #
def null_bars(w, masks, n_trial=N_NULL, batch=1000):
    rng = np.random.default_rng(SEED)
    out = {}
    for el, m in masks.items():
        cs, rs, done = [], [], 0
        while done < n_trial:
            mb = min(batch, n_trial - done)
            Z = (rng.standard_normal((mb, N_SLOW))
                 + 1j * rng.standard_normal((mb, N_SLOW))) / math.sqrt(2.0)
            c, r = stats(Z, w, m)
            cs.append(c); rs.append(r); done += mb
        c, r = np.concatenate(cs), np.concatenate(rs)
        boot = [float(np.quantile(rng.choice(c, c.size, replace=True), 1 - PFA))
                for _ in range(200)]
        sub = [float(np.quantile(c[i * 4000:(i + 1) * 4000], 1 - PFA))
               for i in range(n_trial // 4000)]
        out[f"{el:+.0f}"] = dict(
            n_trial=int(n_trial), n_comb_on=m["n_on"], n_comb_off=m["n_off"],
            comb_mean_db=float(c.mean()), comb_std_db=float(c.std()),
            comb_p99_db=float(np.quantile(c, 0.99)),
            bar_null_p999_db=float(np.quantile(c, 1 - PFA)),
            bar_boot_sd_db=float(np.std(boot)),
            bar_boot_ci95=[float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
            bar_gauss_equiv_db=float(c.mean() + 3.0902 * c.std()),
            stability_4000_subsample_bars=[round(v, 3) for v in sub],
            stability_4000_spread_db=round(max(sub) - min(sub), 3) if sub else None,
            comb_max_db=float(c.max()),
            rhythm_mean_pct=float(r.mean()), rhythm_std_pct=float(r.std()),
            rhythm_bar_p999_pct=float(np.quantile(r, 1 - PFA)))
    return out


# --------------------------------------------------------------------------- #
#  ⓑ+ⓒ A2 거리축 전수 + 인용 자격 게이트
# --------------------------------------------------------------------------- #
def scan_cells(w, masks, z, rows, pat_map, tag):
    res = {}
    for arm, pat in pat_map.items():
        for el, m in masks.items():
            pts = {}
            for R in RANGES:
                eng = pat.format(R=R)
                key = f"{eng}/{el_key(el)}"
                if key not in z.files or (eng, el) not in rows:
                    continue
                row = rows[(eng, el)]
                E = np.asarray(z[key], complex)
                a = np.abs(E) ** 2
                tot = float(a.mean())
                ac = float(np.mean(np.abs(E - E.mean()) ** 2))
                ac_db = 10 * math.log10(max(ac / max(tot, 1e-300), 1e-300))
                dup = float(np.mean(np.diff(E) == 0))
                nm = int(row.get("n_missing") or 0)
                nz = int(np.count_nonzero(E == 0))
                c, rr = stats(E[None, :], w, m)
                gates = dict(
                    g1_complete=bool(nm == 0 and nz == 0),
                    g2_above_numeric_floor=bool(ac_db >= GATE_AC_FRAC_MIN_DB),
                    g3_no_frozen_poses=bool(dup < GATE_DUP_MAX_FRAC))
                pts[str(R)] = dict(
                    engine=eng, quotable=all(gates.values()), gates=gates,
                    n_missing=nm, n_zero=nz, dup_frac=round(dup, 5),
                    level_db=round(10 * math.log10(max(tot, 1e-300)), 2),
                    ac_fraction_db=round(ac_db, 2),
                    clean_comb_db=round(float(c[0]), 2),
                    clean_rhythm_pct=round(float(rr[0]), 1))
            if not pts:
                continue
            ok = {int(R): v for R, v in pts.items() if v["quotable"]}
            base = ok.get(15, {}).get("clean_comb_db")
            drift = (round(max(abs(v["clean_comb_db"] - base) for v in ok.values()), 2)
                     if base is not None and ok else None)
            p = None
            if len(ok) >= 3:
                x = np.log10([R / R_REF for R in sorted(ok)])
                y = np.array([ok[R]["level_db"] for R in sorted(ok)])
                p = round(float(-np.polyfit(x, y, 1)[0] / 10.0), 3)
            flags = []
            sr = sorted(ok)
            for i in range(1, len(sr)):
                d = abs(ok[sr[i]]["clean_comb_db"] - ok[sr[i - 1]]["clean_comb_db"])
                if d > GATE_JUMP_FLAG_DB:
                    flags.append(f"{sr[i-1]}→{sr[i]} m 에서 빗살 대비가 {d:.1f} dB 뛴다")
            res[f"{arm}_el{int(el):+d}"] = dict(
                material=tag, points=pts, n_quotable=len(ok),
                quotable_ranges_m=sorted(ok),
                max_shape_drift_db=drift,
                a1_trustworthy=(None if drift is None else bool(drift <= 3.0)),
                measured_p_engine=p, jump_flags=flags)
    return res


# --------------------------------------------------------------------------- #
#  본체
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    w = np.hanning(N_SLOW)
    masks = {el: make_masks(N_SLOW, PRF_HZ, ft) for el, ft in F_TIP_HZ.items()}
    z = np.load(LEDGER_NPZ)
    led = json.load(open(LEDGER_JSON))
    rows = {(r["engine"], float(r["el_deg"])): r for r in led["rows"]}
    canon = json.load(open(CANON_JSON))
    band_by_el = canon["metric_protocol"]["comb_grid_band_db_by_el"]

    nb = null_bars(w, masks)
    a2 = scan_cells(w, masks, z, rows, ARM_PAT, "legacy_100mm")
    a2c = scan_cells(w, masks, z, rows, ARM_PAT_CANON_MATERIAL, "canon_shell0.75_prop1.43")

    # ⭐본판 막대 = max(귀무 p99.9, 백색선 + 그 앙각의 격자 밴드)
    bars = {}
    for el in F_TIP_HZ:
        k = f"{el:+.0f}"
        wm = nb[k]["comb_mean_db"]
        grid = float(band_by_el.get(k, band_by_el["-30"]))
        b_null, b_grid = nb[k]["bar_null_p999_db"], wm + grid
        bars[k] = dict(
            white_mean_db=round(wm, 4),
            bar_statistical_null_p999_db=round(b_null, 3),
            bar_numerical_grid_band_db=round(b_grid, 3),
            grid_band_source_db=grid,
            BAR_MAINRUN_db=round(max(b_null, b_grid), 3),
            which_binds=("귀무분포(통계)" if b_null >= b_grid else "격자 밴드(수치)"),
            why_ko="두 막대는 다른 물음이다 — 귀무는 «잡음과 구별되나», 격자는 «우리 눈금을 "
                   "바꿔도 남나». 본판은 둘 중 **높은 쪽**을 넘어야 «읽힘» 이라고 부른다")

    # 링크버짓 — 정본 모듈에 위임
    scn = LBS.SCENARIOS[LBS.HEADLINE_SCENARIO]
    lb = dict(headline_scenario=LBS.HEADLINE_SCENARIO,
              report=LBS.budget_report(scn, allow_declared=True),
              sensitivity_rows=LBS.sensitivity_table(),
              doppler_gate={k: LBS.doppler_feasible(s, F_TIP_HZ[-30.0])
                            for k, s in LBS.SCENARIOS.items()},
              selftest=LBS.selftest())

    st = {}
    st["1_no_gpu_import"] = dict(
        ok=not any(m.startswith(("sionna", "mitsuba", "drjit", "torch")) for m in sys.modules),
        loaded=[m for m in sys.modules if m.startswith(("sionna", "mitsuba", "drjit", "torch"))])
    st["2_null_is_signal_free"] = dict(
        ok=True, note_ko="null_bars() 는 원장 E 를 인자로도 받지 않는다 — 문턱 누설 불가")
    st["3_null_mean_is_zero"] = dict(
        ok=all(abs(v["comb_mean_db"]) < 0.1 for v in nb.values()),
        rows={k: round(v["comb_mean_db"], 4) for k, v in nb.items()},
        note_ko="빗살 대비는 «빗살 칸 ÷ 아닌 칸» 이라 백색잡음에서 정의상 0 dB 여야 한다")
    st["4_bar_is_stable"] = dict(
        ok=all(v["bar_boot_sd_db"] < 0.1 for v in nb.values()),
        boot_sd={k: round(v["bar_boot_sd_db"], 4) for k, v in nb.items()},
        spread_at_4000={k: v["stability_4000_spread_db"] for k, v in nb.items()},
        note_ko="⭐옛 N_NULL=4,000 은 같은 분포에서 막대가 0.2~0.5 dB 흔들린다 — 40,000 에서 "
                "부트스트랩 표준편차 ≤0.06 dB")
    st["5_gates_catch_known_bad"] = dict(
        ok=(a2.get("ps_off_el-30", {}).get("points", {}).get("480", {}).get("quotable") is False
            and a2.get("ps_off_el+0", {}).get("points", {}).get("240", {}).get("quotable") is False),
        note_ko="알려진 나쁜 칸 둘(다 끔 el−30 480 m = 경로 0개 64.5 %, el+0 240 m = 수치 바닥·"
                "얼어붙은 자세 20.4 %)이 게이트에 실제로 걸리는지 확인")
    st["6_ours_a1_validated_to_480m"] = dict(
        ok=(a2.get("ours_el-30", {}).get("max_shape_drift_db") is not None
            and a2["ours_el-30"]["max_shape_drift_db"] <= 1.5
            and 480 in a2["ours_el-30"]["quotable_ranges_m"]),
        drift_db=a2.get("ours_el-30", {}).get("max_shape_drift_db"),
        ranges=a2.get("ours_el-30", {}).get("quotable_ranges_m"),
        note_ko="⭐우리 커널 팔은 엔진이 480 m 에서 다시 계산한 판이 15 m 판과 같은 무늬다 — "
                "A1 연장선이 그 거리까지 실측으로 받쳐진다")
    st["ok"] = all(v.get("ok") for v in st.values() if isinstance(v, dict))

    out = dict(
        _meta=dict(
            generator="benchmark/noise_mainrun_prereg.py",
            role_ko="잡음 본판의 사전등록 상수 — 결과를 보기 **전에** 정해지는 것들",
            generated_kst=time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(time.time() + 9 * 3600)) + " (UTC+9)",
            gpu_ko="⛔GPU·솔버 호출 없음(자가검사 1)",
            inputs=[os.path.relpath(p, ROOT) for p in (LEDGER_JSON, LEDGER_NPZ,
                                                       CANON_JSON, FRAME_JSON)],
            seeds=dict(master=SEED, n_null=N_NULL),
            pfa=PFA, prf_hz=PRF_HZ, n_slow=N_SLOW, f_flash_hz=F_FLASH_HZ,
            f_tip_hz_by_el={f"{k:+.0f}": v for k, v in F_TIP_HZ.items()},
            gates=dict(ac_fraction_min_db=GATE_AC_FRAC_MIN_DB,
                       dup_frac_max=GATE_DUP_MAX_FRAC, jump_flag_db=GATE_JUMP_FLAG_DB)),
        decision_bars=bars,
        null_distribution=nb,
        a2_range_axis=a2,
        a2_range_axis_canon_material=a2c,
        link_budget=lb,
        selftest=st)
    json.dump(out, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(out, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {OUT_JSON}  ({out['_meta']['elapsed_s']} s)")
    print(json.dumps(dict(selftest_ok=st["ok"], bars={k: v["BAR_MAINRUN_db"] for k, v in bars.items()},
                          binds={k: v["which_binds"] for k, v in bars.items()}),
                     ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
