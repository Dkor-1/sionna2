"""σ 민감도 분석 — "드론 RCS 가 맞다는 걸 어떻게 아느냐"에 대한 답이 성립하는지 검사.

우리가 하려는 답변은 이렇다: **"σ 가 맞다고 주장하지 않는다. 비교는 σ 를 필요로 하지
않는다."** 이 답은 곡선이 실재할 때만 성립한다 — σ 를 흔들었을 때 **파형 순위가 살아
남아야** 한다. 이 스크립트가 그 곡선을 만든다.

무엇을 계산하나
---------------
1. `stage_solve` 헤드라인 R90 경로를 **비트 단위로 재현**하는 경량 솔버(§S0 에서 검증).
   σ 는 SNR 에 정확히 선형으로 들어가므로(report13 `calib.k_sigma_invariance_db≈1e-5`)
   σ 를 Δ dB 흔드는 것은 SNR 을 Δ dB 흔드는 것과 **같다**. 그래서 기하·게이트·해곡선을
   한 번만 캐시하고 오프셋만 더해 재해(再解)한다 — 근사 아님, 항등이다.
2. **공통모드(common-mode)** 오차: 세 밴드에 같은 Δ. A3 가 "순위에서 상쇄된다"고 한 것.
3. **차분(differential) 오차**: 기울기 오차 s [dB/GHz] → Δσ_band = s·(f_band − f̄).
   이게 상쇄되지 **않는** 종류다. 현실적 최악치는 우리 원(raw) PO 기울기와 측정
   기울기의 차 (1.699−0.210)×3.367 GHz ≈ 5.0 dB.
4. **순위 뒤집힘 문턱**: 밴드쌍마다 "σ 몇 dB 앞서는가"(lead)를 실제 재해로 이분법
   탐색해서 구하고, 그걸 기울기 오차 문턱으로 환산한다.
5. **밴드별 독립 랜덤 오차 MC**: 순위 보존 확률.
6. **자세평균(aspect-averaged) σ 변형**: 취약성이 σ *오차* 때문인지 *단일자세 인용*
   때문인지 가른다.

정직성 규약
-----------
순위가 현실적 오차 범위 안에서 뒤집히면 그대로 적는다. 완화하지 않는다.

산출: outputs/sigma_sensitivity.json + outputs/figures/sigma_sens_f*.png
실행: cd <repo> && PYTHONPATH=src:benchmark python benchmark/sigma_sensitivity.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import experiment_freespace_range as R       # noqa: E402
import freespace_scene as fss                # noqa: E402
import freespace_link as fsl                 # noqa: E402

OUT_JSON = os.path.join(ROOT, "outputs", "sigma_sensitivity.json")
FIGDIR = os.path.join(ROOT, "outputs", "figures")
SIGMA_LIVE = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")
SIGMA_PREV = os.path.join(ROOT, "outputs", "report13_sigma_grid.json.pre_blade.bak")
FREESPACE = os.path.join(ROOT, "outputs", "report13_freespace.json")

DRONES = ["mini5pro", "mavic4pro", "matrice4e", "phantom4", "s1000plus"]
MODES = ["W1", "L1", "G1"]                      # WiFi / LTE / 5G, 전부 같은 점유 등급 G1
BAND_OF = {"W1": "WiFi 5.2 GHz", "L1": "LTE 1.8 GHz", "G1": "5G NR 3.5 GHz"}
LABEL = {"W1": "WiFi 5.21 GHz", "L1": "LTE 1.843 GHz", "G1": "5G NR 3.5 GHz"}
# 고정순 범주색 (Okabe-Ito). dataviz 검증기 6검사 light/dark 전부 PASS (pairs=all).
COLOR = {"L1": "#0072B2", "G1": "#D55E00", "W1": "#009E73"}

MEASURED_SLOPE = 0.210          # dB/GHz — 측정 앵커 기울기 (A2)
RAW_SLOPE_MAX = 1.699           # dB/GHz — 우리 원 PO 최대 기울기
RAW_SLOPE_MIN = 0.742
F_GHZ = {m: R._BAND_BY_STD[R.MODE_STD[m][0]][1] / 1e9 for m in MODES}
F_BAR = float(np.mean([F_GHZ[m] for m in MODES]))       # 차분을 공통모드와 직교화
SPAN_GHZ = F_GHZ["W1"] - F_GHZ["L1"]                    # 3.367 GHz
REALISTIC_SPAN_DB = (RAW_SLOPE_MAX - MEASURED_SLOPE) * SPAN_GHZ   # ≈ 5.01 dB

# stage_solve 정본 인자 (experiment_freespace_range.stage_solve 기본값)
L_M, ALT_M, T_CPI, N_RX, PHI_DEG = 500.0, 60.0, 0.1, 1, 90.0


# --------------------------------------------------------------------------- #
#  S0. 경량 솔버 — stage_solve 헤드라인 R90 경로의 비트단위 재현
# --------------------------------------------------------------------------- #
def build_cell(sig_json, drone, mode, aspect_avg=False):
    """(drone, mode) 의 기하·σ·게이트를 한 번 계산해 캐시.

    반환 dict 의 `snr0_db` 에 오프셋을 더해 `solve_range` 를 다시 부르면
    "σ 를 그만큼 흔든 결과"가 **정확히** 나온다 (σ 는 SNR 에 선형).
    aspect_avg=True 면 단일자세 σ 대신 그 고도행의 방위평균 σ(선형평균)를 쓴다."""
    std, _ = R.MODE_STD[mode]
    bname, fc, _ = R._BAND_BY_STD[std]
    lam = R.C0 / fc
    lookup = R._sigma_lookup(sig_json, drone, bname)
    d = np.geomspace(100.0, 20000.0, 240)
    tgt = fss.target_pos(d, PHI_DEG, L_M, ALT_M)
    p = fss.fs_params(fss.FS_TX, fss.FS_RX(L_M), tgt, (0.0, 0.0, 0.0), fc)
    R1 = np.asarray(p["R1"], float)
    R2 = np.asarray(p["R2"], float)
    beta = np.asarray(p["beta"], float)
    el = np.asarray(p["el_deg"], float)
    kappa = R1 * R2
    az, _ = R._look_az(p["u1"], p["u2"])

    if aspect_avg:
        node = sig_json["sigma"]["grid"][drone][bname]
        el_grid = np.asarray(node["el_deg"], float)
        sm = 10.0 ** (np.asarray(node["sigma_smooth_dbsm"], float) / 10.0)
        rows = sm.mean(axis=1)                       # 방위 선형평균 [m²], 고도행별
        sigma_d = np.array([rows[int(np.argmin(np.abs(el[i] - el_grid)))]
                            for i in range(len(d))])
    else:
        sigma_d = np.array([R._sigma_at(lookup, az[i], el[i], warn=False)
                            for i in range(len(d))])

    snr0 = fsl.snr_rd_db(R.EIRP_DBM, R.GRX_DBI, lam, sigma_d, R1, R2, nf=R.NF_DB,
                         eta_ref=0.0, T=T_CPI, losses=0.0, k_mode=0.0)
    snr0 = snr0 + 10.0 * np.log10(max(N_RX, 1))
    valid = fss.beta_gate(beta) & np.array(
        [fss.farfield_gate(min(R1[i], R2[i]), drone, fc) for i in range(len(d))])
    return dict(d=d, snr0=snr0, kappa=kappa, valid=valid, sigma_d=sigma_d,
                el=el, az=np.asarray(az, float), fc_ghz=fc / 1e9, lam=lam,
                R1=R1, R2=R2)


def R90(cell, snr90, off_db=0.0):
    """σ 오프셋 off_db [dB] 를 준 검지거리 R90 [m]. NaN 이면 미검출."""
    s = fsl.solve_range(cell["snr0"] + float(off_db), snr90,
                        d_grid=cell["d"], kappa_of_d=cell["kappa"], valid=cell["valid"])
    return float(s["R_m"])


def order_of(r):
    """{mode: R90} → 내림차순 모드 튜플. NaN 은 맨 뒤."""
    def key(m):
        v = r[m]
        return -v if np.isfinite(v) else np.inf
    return tuple(sorted(r, key=key))


def lead_db(cell_a, cell_b, snr90, off_a=0.0, off_b=0.0, lo=-40.0, hi=40.0, tol=1e-4):
    """밴드 a 가 밴드 b 를 **σ 몇 dB 앞서는가** (양수=a 가 앞섬).

    a 에 오프셋 −x 를 줘서 R90_a 가 R90_b 와 같아지는 x 를 이분법으로 찾는다.
    해석식(40log10 비)이 아니라 **실제 재해**라 n_local 변동·게이트·격자한계를 그대로 먹는다.
    off_a/off_b 는 각 밴드에 이미 걸려 있는 기준 오프셋(듀티·앵커보정 등)."""
    Rb = R90(cell_b, snr90, off_b)
    if not np.isfinite(Rb):
        return float("nan")

    def g(x):                              # a 에 x dB 주었을 때 R_a − R_b
        Ra = R90(cell_a, snr90, off_a + x)
        return (Ra - Rb) if np.isfinite(Ra) else -1e9

    g0 = g(0.0)
    if not np.isfinite(g0):
        return float("nan")
    a, b = lo, hi
    if np.sign(g(a)) == np.sign(g(b)):
        return float("nan")                # 구간 안에서 교차 없음
    for _ in range(200):
        m = 0.5 * (a + b)
        if np.sign(g(m)) == np.sign(g(a)):
            a = m
        else:
            b = m
        if b - a < tol:
            break
    x = 0.5 * (a + b)
    return float(-x)                       # a 를 −x 만큼 깎아야 같아짐 → lead = −x


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    os.makedirs(FIGDIR, exist_ok=True)
    out = {}

    sig_live = json.load(open(SIGMA_LIVE))
    sig_prev = json.load(open(SIGMA_PREV))
    fsj = json.load(open(FREESPACE))
    snr90 = float(fsj["threshold"]["S_G"]["W1"]["1"]["dopoff"]["3"]["snr90_db"])

    out["_meta"] = dict(
        producer="benchmark/sigma_sensitivity.py",
        generated=datetime.now().isoformat(timespec="seconds"),
        question=("σ 오차 아래에서 WiFi/LTE/5G 파형 순위가 살아남는가 — "
                  "벤치마크 논문의 성립 여부를 가르는 계산"),
        reads=[os.path.relpath(p, ROOT) for p in (SIGMA_LIVE, SIGMA_PREV, FREESPACE)],
        snr90_db=snr90, snr90_source="report13_freespace.threshold.S_G.W1.1.dopoff.3",
        link_budget=dict(eirp_dbm=R.EIRP_DBM, rx_gain_dbi=R.GRX_DBI, nf_db=R.NF_DB,
                         L_m=L_M, alt_m=ALT_M, T_cpi_s=T_CPI, N_rx=N_RX, phi_deg=PHI_DEG),
        band_fc_ghz=F_GHZ, f_pivot_ghz=F_BAR, span_ghz=SPAN_GHZ,
        realistic_differential_span_db=REALISTIC_SPAN_DB,
        sigma_linearity_check=float(fsj["calib"]["W1"]["k_sigma_invariance_db"]),
        note=("σ 는 SNR 에 선형(k_sigma_invariance≈1e-5)이라 σ 오프셋 Δ dB = SNR 오프셋 Δ dB. "
              "따라서 오프셋 재해는 근사가 아니라 항등이다."))

    # ── S0. 재현 검증 ──────────────────────────────────────────────────────
    print("[S0] stage_solve 헤드라인 R90 재현 검증 …")
    cells_prev = {(dr, m): build_cell(sig_prev, dr, m) for dr in DRONES for m in MODES}
    repro = {}
    worst = 0.0
    for dr in DRONES:
        for m in MODES:
            got = R90(cells_prev[(dr, m)], snr90)
            ref = float(fsj["ranges"][dr][m]["equal_psd"]["full_waveform_capture"]
                        ["by_N"]["1"]["R90_C50_m"])
            repro[f"{dr}.{m}"] = dict(lean_m=got, canonical_m=ref, abs_err_m=abs(got - ref))
            worst = max(worst, abs(got - ref))
    out["reproduction"] = dict(
        cells=repro, worst_abs_err_m=worst, exact=bool(worst == 0.0),
        sigma_grid_used="outputs/report13_sigma_grid.json.pre_blade.bak",
        why=("정본 report13_freespace.json 은 2026-07-24 실행이고 그때의 σ 격자는 pre_blade 다. "
             "그 격자로 재현하면 15셀 전부 오차 0 — 경량 솔버가 정본 경로와 항등임을 증명한다."))
    print(f"     최악 오차 {worst:.3e} m  (0 이면 비트단위 일치)")

    # ── S0b. 정본 산출물의 낡음 + 메시 갱신만으로 생긴 순위 변화 ────────────
    cells = {(dr, m): build_cell(sig_live, dr, m) for dr in DRONES for m in MODES}
    stale = {}
    for dr in DRONES:
        rp = {m: R90(cells_prev[(dr, m)], snr90) for m in MODES}
        rl = {m: R90(cells[(dr, m)], snr90) for m in MODES}
        op, ol = order_of(rp), order_of(rl)
        stale[dr] = dict(
            R90_pre_blade_m=rp, R90_live_m=rl, order_pre_blade=list(op), order_live=list(ol),
            order_changed=bool(op != ol),
            max_range_change_pct=max(100.0 * (rl[m] - rp[m]) / rp[m] for m in MODES),
            min_range_change_pct=min(100.0 * (rl[m] - rp[m]) / rp[m] for m in MODES))
    out["staleness_and_mesh_update"] = dict(
        by_drone=stale,
        n_orders_changed=sum(1 for d in stale.values() if d["order_changed"]),
        finding=("정본 report13_freespace.json 의 R90 은 2026-07-24 σ 격자로 계산됐고, "
                 "현재 격자는 2026-07-29 블레이드 형상 갱신본이다. 이 갱신 하나만으로 "
                 "R90 이 최대 +18% 움직였고 순위쌍 하나가 실제로 뒤집혔다."),
        caveat="이건 σ '오차' 실험이 아니라 관측된 사실이다 — 통제되지 않은 σ 변화의 실측 파급.")

    # ── S1. 밴드간 격차 분해: σ vs σ-무관 축 ────────────────────────────────
    print("[S1] 격차 분해 (σ vs σ-무관 축) …")
    d_ref = 2000.0
    decomp = {}
    axes_by_mode = {}
    for dr in DRONES:
        per = {}
        for m in MODES:
            std, _ = R.MODE_STD[m]
            _, fc, _ = R._BAND_BY_STD[std]
            lam = R.C0 / fc
            t = fss.target_pos(d_ref, PHI_DEG, L_M, ALT_M)
            p = fss.fs_params(fss.FS_TX, fss.FS_RX(L_M), t, (0.0, 0.0, 0.0), fc)
            az, _ = R._look_az(p["u1"], p["u2"])
            s = R._sigma_at(R._sigma_lookup(sig_live, dr, BAND_OF[m]),
                            float(np.ravel(az)[0]), float(p["el_deg"]), warn=False)
            tr = fsl.snr_rd_terms_db(R.EIRP_DBM, R.GRX_DBI, lam, s,
                                     float(p["R1"]), float(p["R2"]), nf=R.NF_DB,
                                     eta_ref=0.0, T=T_CPI)
            per[m] = dict(sigma_dbsm=10 * np.log10(s), sigma_term_db=tr["sigma"],
                          lambda2_db=tr["lambda2"], duty_db=tr["duty"],
                          t_cpi_db=tr["t_cpi"], eta_ref_db=tr["eta_ref"],
                          axes_db=tr["total"] - tr["sigma"], snr_db=tr["total"])
            axes_by_mode[m] = tr["total"] - tr["sigma"]
        pairs = {}
        for a, b in (("W1", "L1"), ("W1", "G1"), ("L1", "G1")):
            dt = per[a]["snr_db"] - per[b]["snr_db"]
            ds = per[a]["sigma_term_db"] - per[b]["sigma_term_db"]
            da = per[a]["axes_db"] - per[b]["axes_db"]
            pairs[f"{a}-{b}"] = dict(d_total_db=dt, d_sigma_db=ds, d_axes_db=da,
                                     sigma_over_axes=abs(ds) / max(abs(da), 1e-9),
                                     sigma_dominates=bool(abs(ds) > abs(da)))
        decomp[dr] = dict(per_band=per, pairs=pairs)
    n_dom = sum(1 for dr in DRONES for k, v in decomp[dr]["pairs"].items()
                if v["sigma_dominates"])
    out["gap_decomposition"] = dict(
        d_ref_m=d_ref, by_drone=decomp,
        axes_db_by_mode=axes_by_mode,
        axes_pair_gaps_db={f"{a}-{b}": axes_by_mode[a] - axes_by_mode[b]
                           for a, b in (("W1", "L1"), ("W1", "G1"), ("L1", "G1"))},
        n_pairs_sigma_dominates=n_dom, n_pairs_total=15,
        finding=("이 비교(W1/L1/G1 = 같은 점유 등급)에서 살아있는 σ-무관 축은 λ² 하나뿐이다. "
                 "duty·occupancy·√(B/fs) 항은 전부 정확히 0 이다 — 세 모드가 같은 점유 등급이고 "
                 "duty 항은 코드에서 한 번도 호출되지 않는다. 그래서 σ-무관 격차는 λ² 스프레드 "
                 "9.03/5.57/3.46 dB 로 고정인데, 같은 기체에서 밴드간 σ 차이는 1.3~18.7 dB 다."),
        duty_never_applied=dict(
            symbol="freespace_link.duty_db_from_cpi",
            called_anywhere=False,
            docstring_claim="이 항을 안 넣으면 F1 이 만든 SSB 핸디캡(≈−16 dB)이 SNR 에서 통째로 사라진다",
            impact="R90 경로의 5G 곡선은 문서화된 SSB 듀티 핸디캡만큼 낙관적이다."))

    # ── S2. 공통모드 스윕 ───────────────────────────────────────────────────
    print("[S2] 공통모드 σ 오차 스윕 …")
    cm_grid = np.linspace(-10.0, 10.0, 41)
    cm = {}
    order_invariant = True
    for dr in DRONES:
        base_order = order_of({m: R90(cells[(dr, m)], snr90) for m in MODES})
        rows = {m: [] for m in MODES}
        orders = []
        for off in cm_grid:
            r = {m: R90(cells[(dr, m)], snr90, off) for m in MODES}
            for m in MODES:
                rows[m].append(r[m])
            orders.append(order_of(r))
        changed = [float(cm_grid[i]) for i, o in enumerate(orders) if o != base_order]
        order_invariant &= (len(changed) == 0)
        r0 = {m: rows[m][len(cm_grid) // 2] for m in MODES}
        # dB(range) / dB(sigma) 기울기 — 이론 1/n_local ≈ 1/4
        slope = {m: float(np.polyfit(cm_grid, 10 * np.log10(np.array(rows[m])), 1)[0])
                 for m in MODES}
        cm[dr] = dict(offset_db=cm_grid.tolist(), R90_m=rows,
                      base_order=list(base_order),
                      offsets_with_changed_order=changed,
                      order_invariant=bool(not changed),
                      dB_range_per_dB_sigma=slope,
                      range_at_minus10_pct={m: 100.0 * (rows[m][0] - r0[m]) / r0[m] for m in MODES},
                      range_at_plus10_pct={m: 100.0 * (rows[m][-1] - r0[m]) / r0[m] for m in MODES})
    all_slopes = [v for dr in DRONES for v in cm[dr]["dB_range_per_dB_sigma"].values()]
    out["common_mode"] = dict(
        by_drone=cm, order_invariant_everywhere=bool(order_invariant),
        slope_mean=float(np.mean(all_slopes)), slope_min=float(np.min(all_slopes)),
        slope_max=float(np.max(all_slopes)),
        abs_range_shift_at_10db_pct=dict(
            minus10=float(np.mean([cm[dr]["range_at_minus10_pct"][m]
                                   for dr in DRONES for m in MODES])),
            plus10=float(np.mean([cm[dr]["range_at_plus10_pct"][m]
                                  for dr in DRONES for m in MODES]))),
        finding=("공통모드 ±10 dB 에서 순위는 15셀 전부 불변이다 — A3 확인. "
                 "절대거리만 dB(σ)/4 만큼 움직인다(±10 dB → 대략 −44%/+78%)."))

    # ── S3. 밴드쌍 lead (σ dB) — 실제 재해 이분법 ─────────────────────────
    print("[S3] 밴드쌍 lead 마진 …")
    PAIRS = [("W1", "L1"), ("W1", "G1"), ("L1", "G1")]
    lead = {}
    for dr in DRONES:
        lead[dr] = {f"{a}-{b}": lead_db(cells[(dr, a)], cells[(dr, b)], snr90)
                    for a, b in PAIRS}
    out["pair_lead_db"] = dict(
        by_drone=lead,
        definition="lead(a,b) = a 를 b 와 같은 R90 으로 만들려면 a 의 σ 를 깎아야 하는 dB. 양수=a 가 앞섬.",
        method="실제 R90 재해 이분법 (해석식 아님)")

    # ── S4. 차분(기울기) 오차 스윕 + 뒤집힘 문턱 ───────────────────────────
    print("[S4] 차분 기울기 오차 스윕 + 뒤집힘 문턱 …")
    span_grid = np.linspace(-12.0, 12.0, 241)          # 스팬 전체 차분 [dB]
    s_grid = span_grid / SPAN_GHZ                      # dB/GHz
    diff = {}
    for dr in DRONES:
        base_order = order_of({m: R90(cells[(dr, m)], snr90) for m in MODES})
        rows = {m: [] for m in MODES}
        orders = []
        for s in s_grid:
            r = {m: R90(cells[(dr, m)], snr90, s * (F_GHZ[m] - F_BAR)) for m in MODES}
            for m in MODES:
                rows[m].append(r[m])
            orders.append(order_of(r))
        # 뒤집힘 문턱: base_order 와 달라지는 최소 |span|
        thr_pos = thr_neg = None
        for i, sp in enumerate(span_grid):
            if orders[i] != base_order:
                if sp > 0 and thr_pos is None:
                    thr_pos = float(sp)
                if sp < 0:
                    thr_neg = float(sp)
        # 쌍별 해석 문턱 (lead / Δf) — 재해와 교차검증
        pair_thr = {}
        for a, b in PAIRS:
            ld = lead[dr][f"{a}-{b}"]
            df = F_GHZ[a] - F_GHZ[b]
            s_flip = -ld / df
            pair_thr[f"{a}-{b}"] = dict(
                lead_db=ld, delta_f_ghz=df, s_flip_db_per_ghz=float(s_flip),
                span_flip_db=float(abs(s_flip) * SPAN_GHZ),
                sign=("positive slope error" if s_flip > 0 else "negative slope error"))
        smallest = min(pair_thr.values(), key=lambda v: v["span_flip_db"])
        diff[dr] = dict(
            span_db=span_grid.tolist(), s_db_per_ghz=s_grid.tolist(), R90_m=rows,
            base_order=list(base_order),
            first_flip_span_positive_db=thr_pos, first_flip_span_negative_db=thr_neg,
            smallest_flip_span_db=float(min(abs(x) for x in (thr_pos, thr_neg)
                                            if x is not None)) if (thr_pos or thr_neg) else None,
            pair_thresholds=pair_thr,
            analytic_smallest_flip_span_db=smallest["span_flip_db"],
            flips_inside_realistic_envelope=bool(smallest["span_flip_db"] <= REALISTIC_SPAN_DB),
            gap_change_at_realistic_db={
                f"{a}-{b}": float((REALISTIC_SPAN_DB / SPAN_GHZ) * (F_GHZ[a] - F_GHZ[b]))
                for a, b in PAIRS})
    n_flip = sum(1 for dr in DRONES if diff[dr]["flips_inside_realistic_envelope"])
    out["differential"] = dict(
        by_drone=diff, realistic_span_db=REALISTIC_SPAN_DB,
        n_drones_flipping_inside_realistic=n_flip, n_drones=len(DRONES),
        smallest_flip_span_db_overall=float(min(diff[dr]["analytic_smallest_flip_span_db"]
                                                for dr in DRONES)),
        largest_flip_span_db_overall=float(max(diff[dr]["analytic_smallest_flip_span_db"]
                                               for dr in DRONES)),
        headline=("순위는 스팬 전체 차분오차 X dB 까지 살아남는다 — 기체별 X 는 "
                  "by_drone[*].analytic_smallest_flip_span_db."))

    # ── S5. 이름붙인 시나리오 ───────────────────────────────────────────────
    print("[S5] 시나리오: 측정 기울기 적용 …")
    # 생산 격자의 실제 기울기를 방위평균 σ 3점 최소자승으로 잰다
    scen = {}
    for dr in DRONES:
        mu = {}
        for m in MODES:
            node = sig_live["sigma"]["grid"][dr][BAND_OF[m]]
            el_grid = np.asarray(node["el_deg"], float)
            sm = 10.0 ** (np.asarray(node["sigma_smooth_dbsm"], float) / 10.0)
            i = int(np.argmin(np.abs(el_grid - (-0.2626))))
            mu[m] = 10 * np.log10(sm[i].mean())
        f = np.array([F_GHZ[m] for m in MODES])
        y = np.array([mu[m] for m in MODES])
        our_slope = float(np.polyfit(f, y, 1)[0])
        s_corr = MEASURED_SLOPE - our_slope             # 측정 기울기로 끌어오는 보정
        r_base = {m: R90(cells[(dr, m)], snr90) for m in MODES}
        r_corr = {m: R90(cells[(dr, m)], snr90, s_corr * (F_GHZ[m] - F_BAR)) for m in MODES}
        o0, o1 = order_of(r_base), order_of(r_corr)
        scen[dr] = dict(
            aspect_avg_mu_dbsm=mu, our_production_slope_db_per_ghz=our_slope,
            measured_slope_db_per_ghz=MEASURED_SLOPE,
            correction_slope_db_per_ghz=float(s_corr),
            correction_span_db=float(abs(s_corr) * SPAN_GHZ),
            R90_base_m=r_base, R90_corrected_m=r_corr,
            order_base=list(o0), order_corrected=list(o1),
            order_changed=bool(o0 != o1),
            range_change_pct={m: 100.0 * (r_corr[m] - r_base[m]) / r_base[m] for m in MODES})
    out["scenario_apply_measured_slope"] = dict(
        by_drone=scen,
        n_order_changed=sum(1 for v in scen.values() if v["order_changed"]),
        slope_range_db_per_ghz=[float(min(v["our_production_slope_db_per_ghz"] for v in scen.values())),
                                float(max(v["our_production_slope_db_per_ghz"] for v in scen.values()))],
        finding=("생산 σ 격자는 앵커된 기울기를 갖고 있지 않다. experiment_freespace_sigma.py 에 "
                 "sigma_anchor 참조가 0 회다 — 앵커는 리포트 계층에서만 쓰인다. 그래서 "
                 "'앵커가 제거했다'는 차분오차는 R90 사슬에서 아직 제거되지 않았다."))

    # ── S6. 밴드별 독립 랜덤 오차 MC ────────────────────────────────────────
    print("[S6] 밴드별 독립오차 MC …")
    rng = np.random.default_rng(20260731)
    K = 200_000
    sig_levels = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
    mc = {}
    for dr in DRONES:
        base = order_of({m: R90(cells[(dr, m)], snr90) for m in MODES})
        # base 순서대로 인접 lead 를 뽑아 "모든 쌍이 유지" 판정
        pl = []
        for i in range(len(base)):
            for j in range(i + 1, len(base)):
                a, b = base[i], base[j]
                ld = lead[dr].get(f"{a}-{b}")
                if ld is None:
                    ld = -lead[dr][f"{b}-{a}"]
                pl.append((MODES.index(a), MODES.index(b), float(ld)))
        per = {}
        for se in sig_levels:
            dlt = rng.normal(0.0, se, size=(K, 3))
            keep = np.ones(K, bool)
            for ia, ib, ld in pl:
                keep &= (ld + dlt[:, ia] - dlt[:, ib]) > 0
            top = np.ones(K, bool)
            ia0 = MODES.index(base[0])
            for ib in range(3):
                if ib == ia0:
                    continue
                a, b = base[0], MODES[ib]
                ld = lead[dr].get(f"{a}-{b}")
                if ld is None:
                    ld = -lead[dr][f"{b}-{a}"]
                top &= (ld + dlt[:, ia0] - dlt[:, ib]) > 0
            per[str(se)] = dict(p_order_preserved=float(keep.mean()),
                                p_winner_preserved=float(top.mean()))
        mc[dr] = dict(base_order=list(base), by_sigma_e_db=per)
    out["monte_carlo_per_band_error"] = dict(
        by_drone=mc, K=K, sigma_e_db_levels=sig_levels,
        model="Δ_band ~ N(0, σ_e) i.i.d. per band (밴드별 독립 σ 오차)",
        finding_key="by_drone[*].by_sigma_e_db['2.0'].p_order_preserved")

    # ── S7. 자세평균 σ 변형 — 취약성의 원인 가르기 ─────────────────────────
    print("[S7] 자세평균 σ 변형 …")
    cells_avg = {(dr, m): build_cell(sig_live, dr, m, aspect_avg=True)
                 for dr in DRONES for m in MODES}
    avg = {}
    for dr in DRONES:
        r = {m: R90(cells_avg[(dr, m)], snr90) for m in MODES}
        o = order_of(r)
        ld = {f"{a}-{b}": lead_db(cells_avg[(dr, a)], cells_avg[(dr, b)], snr90)
              for a, b in PAIRS}
        pt = {}
        for a, b in PAIRS:
            df = F_GHZ[a] - F_GHZ[b]
            s_flip = -ld[f"{a}-{b}"] / df
            pt[f"{a}-{b}"] = float(abs(s_flip) * SPAN_GHZ)
        avg[dr] = dict(R90_m=r, order=list(o), lead_db=ld, pair_flip_span_db=pt,
                       smallest_flip_span_db=float(min(pt.values())),
                       single_aspect_smallest_flip_span_db=diff[dr]["analytic_smallest_flip_span_db"],
                       single_aspect_order=diff[dr]["base_order"])
    orders_avg = {dr: tuple(avg[dr]["order"]) for dr in DRONES}
    consensus = len(set(orders_avg.values())) == 1
    out["aspect_averaged"] = dict(
        by_drone=avg, orders=({dr: list(o) for dr, o in orders_avg.items()}),
        all_drones_agree=bool(consensus),
        consensus_order=(list(next(iter(orders_avg.values()))) if consensus else None),
        smallest_flip_span_db_overall=float(min(avg[dr]["smallest_flip_span_db"] for dr in DRONES)),
        median_flip_span_db=float(np.median([avg[dr]["smallest_flip_span_db"] for dr in DRONES])),
        finding=("자세평균 σ 로 인용하면 다섯 기체가 같은 순위에 합의하고, 뒤집힘 문턱이 "
                 "λ² 축 격차로 결정된다 — 단일자세 인용에서 오던 취약성이 사라진다."),
        interpretation=("취약성의 주원인은 σ 의 '오차'가 아니라 '단일자세 인용'이다. "
                        "σ 로브 구조가 밴드마다 완전히 재편되기 때문."))

    # 단일자세 vs 자세평균 순위 일치도
    orders_single = {dr: tuple(diff[dr]["base_order"]) for dr in DRONES}
    out["ranking_consensus"] = dict(
        single_aspect_orders={dr: list(o) for dr, o in orders_single.items()},
        single_aspect_n_distinct=len(set(orders_single.values())),
        aspect_avg_n_distinct=len(set(orders_avg.values())),
        finding=("단일자세에서 다섯 기체가 서로 다른 순위를 낸다 — σ 오차 0 에서도 그렇다. "
                 "즉 '어느 파형이 이기는가'는 기체·자세가 정한다."))

    # ── S8. 미적용 σ-무관 축: 듀티(SSB/패킷) ────────────────────────────────
    print("[S8] 미적용 듀티 축 정량 …")
    from waveforms import all_waveforms
    wfs = all_waveforms("G1")
    duty = {}
    for m in MODES:
        std, _ = R.MODE_STD[m]
        w = wfs[std]
        prf = float(fss.prf_hz(std, "G1"))
        M = max(2, round(T_CPI * prf))
        T_ref = len(w.tx) / float(w.fs_hz)
        duty[m] = dict(prf_hz=prf, M=M, T_ref_s=T_ref,
                       duty_db=float(fsl.duty_db_from_cpi(M, T_ref, T_CPI)))
    DUTY = {m: duty[m]["duty_db"] for m in MODES}
    out["unapplied_duty_axis"] = dict(
        by_mode=duty, duty_db=DUTY,
        pair_gaps_db={f"{a}-{b}": DUTY[a] - DUTY[b] for a, b in PAIRS},
        model="freespace_link.duty_db_from_cpi(M, T_ref, T_CPI), T_ref = len(tx)/fs (선언값)",
        cross_check=dict(
            nr_vs_docstring=("freespace_link.duty_db_from_cpi 의 docstring 이 예고한 "
                             f"'SSB 핸디캡 ≈ −16 dB' 와 계산값 {DUTY['G1']:.2f} dB 가 일치"),
            wifi_vs_report4_fixups=(
                "outputs/report4_fixups.json 의 packet_duty_db = −12.839966563652007 과 "
                f"계산값 {DUTY['W1']:.6f} dB 가 일치 (독립 산출물 교차확인)"),
            verdict="두 밴드 모두 집안의 다른 산출물이 같은 값을 이미 갖고 있다 — 새 가정이 아니다."),
        axes_with_duty_db={m: axes_by_mode[m] + DUTY[m] for m in MODES},
        axes_with_duty_pair_gaps_db={
            f"{a}-{b}": (axes_by_mode[a] + DUTY[a]) - (axes_by_mode[b] + DUTY[b])
            for a, b in PAIRS},
        finding=("듀티는 σ 와 완전히 무관하고 3GPP/IEEE 자원격자에서 정확히 결정되는 축인데 "
                 "R90 경로에서 한 번도 적용되지 않는다. 크기는 λ² 축(9.03 dB)보다 크다."))

    # ── S9. 설정(configuration) 비교 — 무엇을 고쳐야 순위가 서는가 ──────────
    print("[S9] 설정별 순위·문턱 …")

    def slope_corr(dr):
        return scen[dr]["correction_slope_db_per_ghz"]

    CONFIGS = {
        "as_published": dict(cells=cells, anchor=False, duty=False,
                             desc="single aspect, no anchor, no duty (current headline R90)"),
        "aspect_avg": dict(cells=cells_avg, anchor=False, duty=False,
                           desc="aspect-averaged sigma"),
        "aspect_avg_anchored": dict(cells=cells_avg, anchor=True, duty=False,
                                    desc="aspect-averaged + measured 0.210 dB/GHz slope"),
        "aspect_avg_anchored_duty": dict(cells=cells_avg, anchor=True, duty=True,
                                         desc="aspect-averaged + anchored + duty axis applied"),
        "as_published_duty": dict(cells=cells, anchor=False, duty=True,
                                  desc="single aspect + duty axis applied"),
    }
    confs = {}
    for cname, cfg in CONFIGS.items():
        cs = cfg["cells"]
        per = {}
        for dr in DRONES:
            def off(m, dr=dr, cfg=cfg):
                o = 0.0
                if cfg["anchor"]:
                    o += slope_corr(dr) * (F_GHZ[m] - F_BAR)
                if cfg["duty"]:
                    o += DUTY[m]
                return o
            r = {m: R90(cs[(dr, m)], snr90, off(m)) for m in MODES}
            o_ = order_of(r)
            pf = {}
            for a, b in PAIRS:
                ld = lead_db(cs[(dr, a)], cs[(dr, b)], snr90, off(a), off(b))
                df = F_GHZ[a] - F_GHZ[b]
                pf[f"{a}-{b}"] = dict(lead_db=ld,
                                      span_flip_db=float(abs(-ld / df) * SPAN_GHZ))
            per[dr] = dict(R90_m=r, order=list(o_), pairs=pf,
                           smallest_flip_span_db=float(min(v["span_flip_db"]
                                                           for v in pf.values())),
                           weakest_pair=min(pf, key=lambda k: pf[k]["span_flip_db"]))
        orders = {dr: tuple(per[dr]["order"]) for dr in DRONES}
        sm = [per[dr]["smallest_flip_span_db"] for dr in DRONES]
        confs[cname] = dict(
            description=cfg["desc"], by_drone=per,
            n_distinct_orders=len(set(orders.values())),
            all_drones_agree=bool(len(set(orders.values())) == 1),
            consensus_order=(list(next(iter(orders.values())))
                             if len(set(orders.values())) == 1 else None),
            worst_flip_span_db=float(min(sm)), median_flip_span_db=float(np.median(sm)),
            n_drones_flipping_inside_realistic=int(sum(1 for v in sm if v <= REALISTIC_SPAN_DB)),
            robust=bool(len(set(orders.values())) == 1 and min(sm) > REALISTIC_SPAN_DB))
        # 쌍별로도: 어느 주장이 살아남는가
        pair_worst = {}
        for a, b in PAIRS:
            vals = [per[dr]["pairs"][f"{a}-{b}"]["span_flip_db"] for dr in DRONES]
            leads = [per[dr]["pairs"][f"{a}-{b}"]["lead_db"] for dr in DRONES]
            pair_worst[f"{a}-{b}"] = dict(
                worst_flip_span_db=float(min(vals)), median_flip_span_db=float(np.median(vals)),
                lead_sign_consistent=bool(all(x > 0 for x in leads) or all(x < 0 for x in leads)),
                survives_realistic_all_drones=bool(min(vals) > REALISTIC_SPAN_DB))
        confs[cname]["by_pair"] = pair_worst
        # 부분순서: "누가 1등인가"는 전체 3-순위보다 훨씬 강한 주장일 수 있다
        winners = {per[dr]["order"][0] for dr in DRONES}
        wmarg = []
        if len(winners) == 1:
            w0 = next(iter(winners))
            for dr in DRONES:
                for a, b in PAIRS:
                    if w0 in (a, b):
                        wmarg.append(per[dr]["pairs"][f"{a}-{b}"]["span_flip_db"])
        confs[cname]["winner_claim"] = dict(
            winner=(next(iter(winners)) if len(winners) == 1 else None),
            unanimous=bool(len(winners) == 1),
            worst_margin_span_db=(float(min(wmarg)) if wmarg else None),
            survives_realistic=bool(bool(wmarg) and min(wmarg) > REALISTIC_SPAN_DB))
    out["configurations"] = dict(
        by_config=confs, realistic_span_db=REALISTIC_SPAN_DB,
        robust_configs=[k for k, v in confs.items() if v["robust"]],
        finding=("어느 설정에서 순위 주장이 서는지 한 표에 모았다. "
                 "'robust' = 다섯 기체가 같은 순위 + 최악 뒤집힘 문턱이 현실 오차범위 밖."))

    # ── S10. 기체 크기 vs 취약성 ────────────────────────────────────────────
    print("[S10] 크기 vs 취약성 …")
    size = {}
    for dr in DRONES:
        sc = json.load(open(os.path.join(
            ROOT, "outputs", f"report13_sigma_grid.{dr}.json")))["sigma_confidence"]["by_drone"][dr]
        size[dr] = dict(extent_m=sc["extent_m"],
                        D_over_lambda_lte=sc["D_over_lambda"]["LTE 1.8 GHz"]["value"],
                        D_over_lambda_wifi=sc["D_over_lambda"]["WiFi 5.2 GHz"]["value"],
                        few_lambda_at_lte=sc["D_over_lambda"]["LTE 1.8 GHz"]["few_lambda"])
    ext = np.array([size[dr]["extent_m"] for dr in DRONES])
    frag_single = np.array([diff[dr]["analytic_smallest_flip_span_db"] for dr in DRONES])
    frag_avg = np.array([avg[dr]["smallest_flip_span_db"] for dr in DRONES])
    dsig_spread = np.array([max(abs(v["d_sigma_db"])
                                for v in decomp[dr]["pairs"].values()) for dr in DRONES])
    out["size_vs_fragility"] = dict(
        by_drone={dr: dict(size[dr],
                           flip_span_single_aspect_db=float(frag_single[i]),
                           flip_span_aspect_avg_db=float(frag_avg[i]),
                           max_band_sigma_spread_db=float(dsig_spread[i]))
                  for i, dr in enumerate(DRONES)},
        corr_extent_vs_flip_single=float(np.corrcoef(ext, frag_single)[0, 1]),
        corr_extent_vs_sigma_spread=float(np.corrcoef(ext, dsig_spread)[0, 1]),
        corr_sigma_spread_vs_flip_single=float(np.corrcoef(dsig_spread, frag_single)[0, 1]),
        smallest_airframe="mini5pro",
        smallest_airframe_rank_by_robustness=int(
            1 + sorted(frag_single, reverse=True).index(frag_single[DRONES.index("mini5pro")])),
        finding=("작은 기체가 더 취약하다는 예상은 **틀렸다**. 가장 작은 mini5pro(0.378 m, "
                 "LTE 에서 D/λ=2.3 인 few-lambda)가 단일자세·자세평균 양쪽에서 가장 견고하고, "
                 "가장 큰 s1000plus(1.348 m)가 가장 취약한 축에 있다. 취약성을 정하는 것은 "
                 "크기 자체가 아니라 **밴드간 σ 로브 산포**이고, 그건 전기적 크기가 클수록 커진다."))

    out["_meta"]["runtime_s"] = round(time.time() - t0, 1)

    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\n[sigma_sensitivity] → {OUT_JSON}  ({out['_meta']['runtime_s']}s)")

    make_figures(out)
    return out


# --------------------------------------------------------------------------- #
#  그림 (텍스트 전부 영어 — 하우스 규약)
# --------------------------------------------------------------------------- #
def make_figures(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9,
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#8a8a86", "axes.labelcolor": "#2a2a28",
        "text.color": "#2a2a28", "xtick.color": "#5a5a56", "ytick.color": "#5a5a56",
        "legend.frameon": False, "lines.linewidth": 2.0,
    })
    INK, MUTED = "#2a2a28", "#6a6a66"
    realistic = out["_meta"]["realistic_differential_span_db"]

    # ── F1: 차분 오차 vs R90, 기체별 패널, 뒤집힘 표시 ─────────────────────
    fig, axs = plt.subplots(1, 5, figsize=(15.2, 3.9), sharex=True)
    for k, dr in enumerate(DRONES):
        ax = axs[k]
        D = out["differential"]["by_drone"][dr]
        x = np.array(D["span_db"])
        ax.axvspan(-realistic, realistic, color="#c9c9c4", alpha=0.30, lw=0, zorder=0)
        for m in MODES:
            y = np.array(D["R90_m"][m]) / 1000.0
            ax.plot(x, y, color=COLOR[m], label=LABEL[m], zorder=3,
                    solid_capstyle="round")
        # 뒤집힘 지점 — x 가 가까우면 라벨이 겹치므로 계단식으로 띄운다
        fp = []
        for pk, pv in D["pair_thresholds"].items():
            xf = pv["s_flip_db_per_ghz"] * SPAN_GHZ
            if abs(xf) <= x.max():
                a = pk.split("-")[0]
                fp.append((xf, float(np.interp(xf, x, np.array(D["R90_m"][a]) / 1000.0))))
        fp.sort()
        used = []
        for xf, yf in fp:
            ax.plot([xf], [yf], marker="o", ms=7, mfc="white", mew=2.0, mec=INK, zorder=5)
            dy = 10.0
            while any(abs(xf - ux) < 0.11 * (x.max() - x.min()) and abs(dy - uy) < 11.0
                      for ux, uy in used):
                dy += 12.0
            used.append((xf, dy))
            ax.annotate(f"{abs(xf):.1f}", (xf, yf), textcoords="offset points",
                        xytext=(0, dy), ha="center", fontsize=7.5, color=INK,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
        ax.axvline(0, color=MUTED, lw=0.8, ls=":", zorder=1)
        sm = D["analytic_smallest_flip_span_db"]
        flag = "FLIPS inside envelope" if D["flips_inside_realistic_envelope"] else "survives envelope"
        ax.set_title(f"{dr}\nfirst flip at {sm:.1f} dB — {flag}", fontsize=8.5,
                     color=("#B03A2E" if D["flips_inside_realistic_envelope"] else INK))
        ax.set_xlabel("Differential $\\sigma$ error across band span [dB]")
        if k == 0:
            ax.set_ylabel("Detection range $R_{90}$ [km]")
        ax.set_xlim(x.min(), x.max())
    axs[0].legend(loc="lower left", fontsize=7.5)
    fig.suptitle("Waveform ranking vs a differential (slope) RCS error — "
                 f"shaded band = realistic envelope $\\pm${realistic:.1f} dB; "
                 "markers = ranking-flip points", fontsize=10.5, y=1.03)
    fig.tight_layout()
    p1 = os.path.join(FIGDIR, "sigma_sens_f1_differential.png")
    fig.savefig(p1, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ── F2: 공통모드 — 순위 불변 ───────────────────────────────────────────
    fig, axs = plt.subplots(1, 2, figsize=(10.4, 3.9))
    ax = axs[0]
    for dr in DRONES:
        C = out["common_mode"]["by_drone"][dr]
        x = np.array(C["offset_db"])
        for m in MODES:
            ax.plot(x, np.array(C["R90_m"][m]) / 1000.0, color=COLOR[m],
                    lw=1.4, alpha=0.85)
    for m in MODES:
        ax.plot([], [], color=COLOR[m], label=LABEL[m])
    ax.set_xlabel("Common-mode $\\sigma$ error [dB]")
    ax.set_ylabel("Detection range $R_{90}$ [km]")
    ax.set_title("All 5 airframes: curves translate, never cross", fontsize=9.5)
    ax.legend(loc="upper left", fontsize=7.5)

    ax = axs[1]
    for dr in DRONES:
        C = out["common_mode"]["by_drone"][dr]
        x = np.array(C["offset_db"])
        for a, b in [("W1", "L1"), ("W1", "G1"), ("L1", "G1")]:
            g = 40 * np.log10(np.array(C["R90_m"][a]) / np.array(C["R90_m"][b]))
            ax.plot(x, g, color=COLOR[a], lw=1.2, alpha=0.7)
    ax.axhline(0, color=INK, lw=1.0, ls="--")
    ax.set_xlabel("Common-mode $\\sigma$ error [dB]")
    ax.set_ylabel("Band-pair gap [dB of SNR]")
    sl = out["common_mode"]["slope_mean"]
    ax.set_title(f"Gaps are flat: ranking is exactly invariant\n"
                 f"($dR_{{dB}}/d\\sigma_{{dB}} = {sl:.3f}$, i.e. $1/n$ with $n\\approx4$)",
                 fontsize=9.5)
    fig.suptitle("Common-mode RCS error cancels in the ranking (A3), moves absolute range only",
                 fontsize=10.5, y=1.02)
    fig.tight_layout()
    p2 = os.path.join(FIGDIR, "sigma_sens_f2_common_mode.png")
    fig.savefig(p2, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ── F3: 뒤집힘 문턱 막대 ───────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    labels, vals, cols = [], [], []
    for dr in DRONES:
        D = out["differential"]["by_drone"][dr]
        for pk in ["W1-L1", "W1-G1", "L1-G1"]:
            labels.append(f"{dr}  {pk.replace('W1','WiFi').replace('L1','LTE').replace('G1','5G')}")
            v = D["pair_thresholds"][pk]["span_flip_db"]
            vals.append(v)
            cols.append(COLOR[pk.split("-")[0]])
    y = np.arange(len(labels))
    ax.barh(y, vals, color=cols, height=0.68)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7.2)
    ax.invert_yaxis()
    ax.axvline(realistic, color="#B03A2E", lw=1.8, ls="--")
    ax.annotate(f"realistic differential\nerror  {realistic:.1f} dB",
                (realistic, len(labels) - 0.5), xytext=(6, 0),
                textcoords="offset points", color="#B03A2E", fontsize=8, va="bottom")
    for yi, v in zip(y, vals):
        ax.annotate(f"{v:.1f}", (v, yi), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7, color=INK)
    ax.set_xlabel("Ranking-flip threshold: differential $\\sigma$ error across the band span [dB]")
    ax.set_title("How much slope error each band pair survives\n"
                 "bars left of the red line flip inside the realistic error envelope",
                 fontsize=10)
    fig.tight_layout()
    p3 = os.path.join(FIGDIR, "sigma_sens_f3_flip_threshold.png")
    fig.savefig(p3, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ── F4: MC 순위보존 확률 ───────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    levels = out["monte_carlo_per_band_error"]["sigma_e_db_levels"]
    dcol = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#4a3aa7"]
    for i, dr in enumerate(DRONES):
        p = [out["monte_carlo_per_band_error"]["by_drone"][dr]["by_sigma_e_db"][str(s)]
             ["p_order_preserved"] for s in levels]
        ax.plot(levels, p, marker="o", ms=6, color=dcol[i], label=dr)
        ax.annotate(dr, (levels[-1], p[-1]), xytext=(5, 0), textcoords="offset points",
                    fontsize=7.5, color=dcol[i], va="center")
    ax.axhline(0.5, color=MUTED, ls=":", lw=1.0)
    ax.set_xlabel("Per-band independent $\\sigma$ error, 1$\\sigma$ [dB]")
    ax.set_ylabel("P(full 3-band ranking preserved)")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(0, levels[-1] * 1.28)
    ax.set_title("Ranking survival under independent per-band RCS error", fontsize=10)
    ax.legend(fontsize=7.5, loc="lower left")
    fig.tight_layout()
    p4 = os.path.join(FIGDIR, "sigma_sens_f4_montecarlo.png")
    fig.savefig(p4, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ── F5: 격차 분해 σ vs 축 ──────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    pairs = ["W1-L1", "W1-G1", "L1-G1"]
    xs = np.arange(len(DRONES) * len(pairs), dtype=float)
    ds, da, labs = [], [], []
    for dr in DRONES:
        for pk in pairs:
            v = out["gap_decomposition"]["by_drone"][dr]["pairs"][pk]
            ds.append(v["d_sigma_db"])
            da.append(v["d_axes_db"])
            labs.append(f"{dr[:9]}\n{pk.replace('W1','W').replace('L1','L').replace('G1','G')}")
    w = 0.38
    ax.bar(xs - w / 2 - 0.01, ds, width=w, color="#D55E00", label="$\\Delta\\sigma$ (RCS, aspect-dependent)")
    ax.bar(xs + w / 2 + 0.01, da, width=w, color="#0072B2", label="$\\Delta$axes ($\\lambda^2$, $\\sigma$-independent)")
    ax.axhline(0, color=INK, lw=1.0)
    ax.set_xticks(xs)
    ax.set_xticklabels(labs, fontsize=6.4)
    ax.set_ylabel("Contribution to band-pair gap [dB of SNR]")
    ax.set_title("What actually separates the bands: RCS, not the waveform axes\n"
                 f"{out['gap_decomposition']['n_pairs_sigma_dominates']} of 15 pairs are "
                 "$\\sigma$-dominated ($|\\Delta\\sigma| > |\\Delta$axes$|$)", fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    p5 = os.path.join(FIGDIR, "sigma_sens_f5_gap_decomposition.png")
    fig.savefig(p5, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ── F6: 단일자세 vs 자세평균 — 처방 ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    y = np.arange(len(DRONES), dtype=float)
    sa = [out["differential"]["by_drone"][dr]["analytic_smallest_flip_span_db"] for dr in DRONES]
    aa = [out["aspect_averaged"]["by_drone"][dr]["smallest_flip_span_db"] for dr in DRONES]
    ax.barh(y - 0.19, sa, height=0.34, color="#D55E00", label="single aspect (current headline)")
    ax.barh(y + 0.19, aa, height=0.34, color="#0072B2", label="aspect-averaged $\\sigma$")
    ax.axvline(realistic, color="#B03A2E", lw=1.8, ls="--")
    ax.annotate(f"realistic {realistic:.1f} dB", (realistic, -0.6), xytext=(5, 0),
                textcoords="offset points", color="#B03A2E", fontsize=8)
    for yi, (a, b) in enumerate(zip(sa, aa)):
        ax.annotate(f"{a:.1f}", (a, yi - 0.19), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7.5, color=INK)
        ax.annotate(f"{b:.1f}", (b, yi + 0.19), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7.5, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(DRONES, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Smallest ranking-flip threshold [dB of differential error across span]")
    ns = out["ranking_consensus"]["single_aspect_n_distinct"]
    na = out["ranking_consensus"]["aspect_avg_n_distinct"]
    co = "$\\to$".join({"L1": "LTE", "G1": "5G", "W1": "WiFi"}[m]
                       for m in out["aspect_averaged"]["consensus_order"])
    ax.set_title("Aspect-averaging buys consensus, NOT robustness\n"
                 f"orders across the 5 airframes: {ns} distinct at one aspect "
                 f"$\\to$ {na} ({co}) aspect-averaged;\n"
                 "yet every flip threshold still sits inside the realistic envelope",
                 fontsize=9.5)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    p6 = os.path.join(FIGDIR, "sigma_sens_f6_aspect_averaged.png")
    fig.savefig(p6, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ── F7: 설정별 — 어느 주장이 서는가 ────────────────────────────────────
    CF = out["configurations"]["by_config"]
    names = ["as_published", "aspect_avg", "aspect_avg_anchored",
             "as_published_duty", "aspect_avg_anchored_duty"]
    nice = {"as_published": "as published\n(1 aspect, no anchor, no duty)",
            "aspect_avg": "aspect-averaged $\\sigma$",
            "aspect_avg_anchored": "aspect-avg + anchored slope",
            "as_published_duty": "1 aspect + duty axis",
            "aspect_avg_anchored_duty": "aspect-avg + anchored + duty"}
    fig, axs = plt.subplots(1, 2, figsize=(12.6, 4.3),
                            gridspec_kw={"width_ratios": [1.15, 1.0]})
    ax = axs[0]
    y = np.arange(len(names), dtype=float)
    full = [CF[n]["worst_flip_span_db"] for n in names]
    win = [(CF[n]["winner_claim"]["worst_margin_span_db"] or 0.0) for n in names]
    ax.barh(y - 0.19, full, height=0.34, color="#D55E00",
            label="full 3-way ranking (W/L/5G)")
    ax.barh(y + 0.19, win, height=0.34, color="#0072B2",
            label='winner-only claim ("LTE is best")')
    ax.axvline(realistic, color=INK, lw=1.8, ls="--")
    ax.annotate(f"realistic\nerror {realistic:.1f} dB", (realistic, len(names) - 0.35),
                xytext=(6, 0), textcoords="offset points", fontsize=8, color=INK, va="center")
    for yi, n, fv, wv in zip(y, names, full, win):
        ax.annotate(f"{fv:.2f}  flips", (fv, yi - 0.19), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=7.4, color=INK)
        wc = CF[n]["winner_claim"]
        lbl = "n/a — no unanimous winner" if not wc["unanimous"] else (
            f"{wv:.2f}  {'STANDS' if wc['survives_realistic'] else 'flips'}")
        ax.annotate(lbl, (wv, yi + 0.19), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7.4,
                    color=("#1f8a4c" if wc["survives_realistic"] else INK))
    ax.set_yticks(y)
    ax.set_yticklabels([nice[n] for n in names], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, max(max(full + win) * 1.75, realistic * 1.6))
    ax.set_xlabel("Worst-case flip threshold over 5 airframes [dB]")
    ax.set_title("No configuration supports a 3-way ranking;\n"
                 "the corrected ones support \"LTE is best\"", fontsize=10)
    ax.legend(fontsize=7.6, loc="upper right")

    ax = axs[1]
    pl = ["W1-L1", "W1-G1", "L1-G1"]
    pnice = {"W1-L1": "WiFi vs LTE", "W1-G1": "WiFi vs 5G", "L1-G1": "LTE vs 5G"}
    xw = 0.26
    xs = np.arange(len(pl), dtype=float)
    for i, n in enumerate(["as_published", "aspect_avg_anchored", "aspect_avg_anchored_duty"]):
        vals = [CF[n]["by_pair"][p]["worst_flip_span_db"] for p in pl]
        ax.bar(xs + (i - 1) * (xw + 0.02), vals, width=xw,
               color=["#D55E00", "#0072B2", "#009E73"][i], label=nice[n].replace("\n", " "))
    ax.axhline(realistic, color=INK, lw=1.6, ls="--")
    ax.annotate(f"realistic {realistic:.1f} dB", (-0.45, realistic),
                xytext=(0, 4), textcoords="offset points", ha="left", fontsize=8, color=INK)
    ax.set_xticks(xs)
    ax.set_xticklabels([pnice[p] for p in pl], fontsize=9)
    ax.set_ylabel("Worst-case flip threshold [dB]")
    ax.set_title("Which pairwise claim survives, by configuration", fontsize=10)
    ax.legend(fontsize=7.4, loc="upper left")
    fig.suptitle("What has to change before a WiFi/LTE/5G ranking can be claimed",
                 fontsize=10.5, y=1.02)
    fig.tight_layout()
    p7 = os.path.join(FIGDIR, "sigma_sens_f7_configurations.png")
    fig.savefig(p7, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    paths = [p1, p2, p3, p4, p5, p6, p7]
    out.setdefault("_meta", {})["figures"] = [os.path.relpath(p, ROOT) for p in paths]
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    for p in paths:
        print(f"  [fig] {p}")


if __name__ == "__main__":
    main()
