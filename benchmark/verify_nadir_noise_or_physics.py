# -*- coding: utf-8 -*-
"""
verify_nadir_noise_or_physics.py — **직하방(el −90°) 잔여 «도플러» 는 물리인가 표본잡음인가.**

⛔GPU 를 쓰지 않는다. 이미 저장된 원장(npz/json)을 CPU 로 다시 읽고 다시 재고,
  격자가 아예 없는 평면패싯 PO 대리모형만 numpy 로 새로 돌린다.

■ 가르는 시험 (사용자 지시)
  물리라면 **광선을 더 쏴도 안 변한다**. 잡음이면 예산에 반비례해 **줄어든다**.
  우리 팔의 «예산» 은 광선 수가 아니라 **격자 간격**이므로 같은 논리를 격자 사다리로 건다.

■ ⚠라운드 중에 뒤집힌 것 — 빗살은 증거가 아니다
  처음엔 «잡음이면 스펙트럼이 평평(백색)할 것» 이라 봤는데 **틀렸다.** PathSolver 는
  seed=1 고정, 우리 팔은 격자가 얼려 있어 **두 팔 다 표본화가 자세의 결정론적 함수**다.
  자세는 로터 주기로 반복하므로 표본오차도 **플래시 빗살에 정확히 얹힌다**(측정: 나딧에서
  우리 79 %, PathSolver 92~94 % 가 빗살 위). ⇒ 빗살 구조는 물리의 증거가 못 된다.
  대신 쓸 수 있는 잣대는 두 개다 — (a) 예산 사다리, (b) **격자 없는 독립 모형과의 상관**.

■ 입력 (전부 기존 원장, 덮어쓰지 않는다)
  outputs/elevation_sweep_md.npz / .json      시계열 E(자세)·요약행
  outputs/elev_sweep_shards/*.npz             자세별 npaths (sionna 팔)
  outputs/verify_nadir_flash.json             B_decomposition·A_instrument_audit·C_D_geometry
  outputs/verify_po_elev_unit.json            해석 점산란체 단위시험 (격자 사다리 λ/12·24·48)
  outputs/verify_po_elev_gridscale.json       ⭐드론 el−90 격자 사다리 (λ/8·12·16, E 시계열)

■ 출력
  outputs/verify_nadir_noise_or_physics.json
  outputs/figs/verify_nadir_noise_or_physics.png
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = ""          # ⛔GPU 금지

import numpy as np                                                    # noqa: E402

ROOT = "/workspace/sionna"
for _p in (f"{ROOT}/src", f"{ROOT}/benchmark"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = f"{ROOT}/outputs/verify_nadir_noise_or_physics.json"
FIG = f"{ROOT}/outputs/figs/verify_nadir_noise_or_physics.png"

SW = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
SJ = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
NF = json.load(open(f"{ROOT}/outputs/verify_nadir_flash.json"))
UT = json.load(open(f"{ROOT}/outputs/verify_po_elev_unit.json"))
GS = json.load(open(f"{ROOT}/outputs/verify_po_elev_gridscale.json"))
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]

PRF = float(SJ["_meta"]["prf_hz"])
FFL = float(SJ["_meta"]["f_flash_hz"])
N = int(TJ["n"])
SPP0 = int(SJ["_meta"]["sionna_spp"])
FC, RANGE_M = 3.5e9, 10.0
KW = 2 * np.pi * FC / 2.998e8
ARM_SPP = {"sionna": SPP0, "sionna_p250000000": 250_000_000,
           "sionna_p1000000000": 1_000_000_000, "sionna_p4000000000": 4_000_000_000}


# ═══ 잣대 ═══════════════════════════════════════════════════════════════════
def rel(x):
    x = np.asarray(x, complex)
    return x / x.mean() - 1.0


def acdc_db(E):
    """AC/DC 전력비 [dB] = 10log10(⟨|E/⟨E⟩−1|²⟩). verify_nadir_flash 와 같은 식."""
    return float(10 * np.log10(np.mean(np.abs(rel(E)) ** 2) + 1e-300))


def acdc_db_fft(E):
    """같은 양을 FFT 0 Hz 빈으로 — verify_po_elev_unit 의 ac_below_dc_db 정의."""
    E = np.asarray(E, complex)
    P = np.abs(np.fft.fft(E) / E.size) ** 2
    dc = P[0] / P.sum()
    return float(10 * np.log10((1 - dc) / dc))


def cxcorr(a, b):
    """복소 상관 크기. 팔마다 위상규약이 반대(+j vs −j)라 켤레도 재고 큰 쪽을 쓴다."""
    a = np.asarray(a, complex) - np.mean(a)
    b = np.asarray(b, complex) - np.mean(b)
    n = np.linalg.norm(a) * np.linalg.norm(b) + 1e-300
    r1, r2 = abs(np.vdot(a, b)) / n, abs(np.vdot(a, np.conj(b))) / n
    return (float(r1), "direct") if r1 >= r2 else (float(r2), "conjugated")


def harm_pick(x, ks, half=None):
    """플래시 고조파 k·f_flash 만 통과시킨 성분."""
    x = np.asarray(x, complex)
    n = x.size
    if half is None:
        half = max(12.0, 1.3 * PRF / n)
    fq = np.fft.fftfreq(n, 1 / PRF)
    m = np.zeros(n, bool)
    for k in ks:
        m |= np.abs(np.abs(fq) - k * FFL) <= half
    return np.fft.ifft(np.where(m, np.fft.fft(x), 0)), m


def harm_env(x, nh=70):
    """고조파 봉투 — k 번째 고조파 전력을 k=1 기준 dB 로."""
    x = np.asarray(x, complex)
    n = x.size
    half = max(8.0, 1.3 * PRF / n)
    d = rel(x)
    fq = np.fft.fftfreq(n, 1 / PRF)
    P = np.abs(np.fft.fft(d * np.hanning(n))) ** 2
    out = []
    for k in range(1, nh + 1):
        if k * FFL > 0.98 * PRF / 2:
            out.append(np.nan); continue
        m = np.abs(np.abs(fq) - k * FFL) <= half
        out.append(P[m].max() if m.any() else np.nan)
    out = np.asarray(out, float)
    return 10 * np.log10(out / out[0])


def env_slope(v):
    k = np.arange(1, v.size + 1)
    m = np.isfinite(v)
    return float(np.polyfit(np.log10(k[m]), v[m], 1)[0] * np.log10(2.0))


def npaths_of(arm, el):
    fs = sorted(glob.glob(f"{ROOT}/outputs/elev_sweep_shards/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None
    ii, vv = [], []
    for f in fs:
        z = np.load(f)
        if "npaths" not in z.files:
            return None
        ii.append(z["idx"]); vv.append(z["npaths"])
    ii = np.concatenate(ii); vv = np.concatenate(vv)
    return vv[np.argsort(ii)].astype(float)


# ═══ 격자 없는 평면패싯 PO 대리모형 (CPU, numpy) ══════════════════════════════
def build_proxy():
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES
    fp = FastPoser(DRONES[TJ.get("drone", "matrice4e")])
    f = np.asarray(fp.f)
    isp = np.asarray(fp.g) == "prop"
    c0 = 0.5 * (fp.v.min(0) + fp.v.max(0))
    u = np.array([0.0, 0.0, -1.0])
    ph = rotor_phases(np.arange(N) / PRF, np.asarray(TJ["rpm_per_rotor"], float), fp.dirs)
    RS = [10.0, 20.0, 40.0, 80.0, 160.0]
    S = {R: np.zeros(N, complex) for R in RS}
    Spl = np.zeros(N, complex)
    Spr = np.zeros(N, complex)
    Sbd = np.zeros(N, complex)
    t0 = time.time()
    for i in range(N):
        v = fp.pose(ph[i]).v
        a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        nn = np.cross(b - a, c - a)
        ar2 = np.linalg.norm(nn, axis=1)
        nn = nn / (ar2[:, None] + 1e-300)
        cen = (a + b + c) / 3.0
        w = np.maximum(nn @ u, 0.0) * 0.5 * ar2
        for R in RS:
            q = w * np.exp(-1j * 2 * KW * np.linalg.norm(cen - (c0 + R * u), axis=1))
            S[R][i] = q.sum()
            if R == 10.0:
                Spr[i] = q[isp].sum(); Sbd[i] = q[~isp].sum()
        Spl[i] = (w * np.exp(-1j * 2 * KW * (cen @ u))).sum()
        if i and i % 1024 == 0:
            print(f"   proxy {i}/{N} {time.time()-t0:.0f}s", flush=True)
    print(f"   proxy done {time.time()-t0:.0f}s", flush=True)
    return S, Spl, Spr, Sbd


PXC = f"{ROOT}/outputs/verify_nadir_noise_or_physics_proxy.npz"
if os.path.exists(PXC):
    _z = np.load(PXC)
    SPH = {float(k[4:]): _z[k] for k in _z.files if k.startswith("sph_")}
    PLW, PPR, PBD = _z["plane"], _z["props"], _z["body"]
else:
    SPH, PLW, PPR, PBD = build_proxy()
    np.savez_compressed(PXC, plane=PLW, props=PPR, body=PBD,
                        **{f"sph_{R:g}": v for R, v in SPH.items()})
P10 = SPH[10.0]

J: dict = {"_meta": {
    "generator": "benchmark/verify_nadir_noise_or_physics.py",
    "question_ko": "직하방(el −90°) 잔여 «도플러» 가 물리인가 광선/격자 표본잡음인가",
    "gpu_ko": "⛔GPU 미사용. 기존 원장을 CPU 로 다시 잰 것과, 격자 없는 numpy PO 대리모형뿐.",
    "criterion_ko": "물리는 예산(광선 수·격자 조밀도)에 안 변하고, 표본잡음은 예산에 반비례해 준다.",
    "proxy_ko": ("대리모형 E = Σ_facet (n·û)_+ · area · exp(−j2k|c−p_tx|). "
                 "광선격자·재질·가림·다중반사 전부 없음. 절대레벨은 비교 금지, AC/DC 는 무차원."),
    "prf_hz": PRF, "f_flash_hz": FFL, "n_poses": N, "sionna_spp_base": SPP0,
    "range_m": RANGE_M, "fc_hz": FC,
    "inputs": ["outputs/elevation_sweep_md.npz", "outputs/elevation_sweep_md.json",
               "outputs/verify_nadir_flash.json", "outputs/verify_po_elev_unit.json",
               "outputs/verify_po_elev_gridscale.json", "outputs/elev_sweep_shards/*.npz"],
}}

# ═══ S0. 원장 재측정 ════════════════════════════════════════════════════════
rows = {}
for key in ("ours/el+0", "ours/el-15", "ours/el-45", "ours/el-75", "ours/el-90",
            "sionna/el+0", "sionna/el-15", "sionna/el-90",
            "sionna_p250000000/el+0", "sionna_p250000000/el-15",
            "sionna_p250000000/el-90",
            "sionna_p1000000000/el+0", "sionna_p4000000000/el+0"):
    if key not in SW.files:
        continue
    E = np.asarray(SW[key], complex)
    d = rel(E)
    r = dict(n=int(E.size),
             level_meanabs_db=round(float(20 * np.log10(np.abs(E).mean())), 2),
             level_absmean_db=round(float(20 * np.log10(abs(E.mean()))), 2),
             ac_over_dc_db=round(acdc_db(E), 2),
             ac_over_dc_db_fft=round(acdc_db_fft(E), 2),
             am_rms=round(float(d.real.std()), 6),
             pm_rms_deg=round(float(np.degrees(d.imag.std())), 3),
             phase_dev_p95_deg=round(float(np.degrees(np.percentile(np.abs(d.imag), 95))), 3))
    old = NF["B_decomposition"].get(key)
    if old:
        r["ledger"] = dict(ac_over_dc_db=old["ac_over_dc_db"], pm_rms_deg=old["pm_rms_deg"],
                           phase_dev_p95_deg=old["phase_dev_p95_deg"])
        r["reproduces_ledger"] = bool(
            abs(r["ac_over_dc_db"] - old["ac_over_dc_db"]) <= 0.02 and
            abs(r["pm_rms_deg"] - old["pm_rms_deg"]) <= 0.02 and
            abs(r["phase_dev_p95_deg"] - old["phase_dev_p95_deg"]) <= 0.02)
    rows[key] = r
J["S0_remeasured"] = {
    "note_ko": "verify_nadir_flash.json 의 B 표를 npz 에서 직접 다시 잰 값.",
    "rows": rows,
    "ledger_reproduced_all": bool(all(r.get("reproduces_ledger", True) for r in rows.values())),
    "two_ledger_definitions_identical": bool(all(
        abs(r["ac_over_dc_db"] - r["ac_over_dc_db_fft"]) < 0.01 for r in rows.values())),
    "definition_proof_ko": (
        "⭐verify_nadir_flash 의 ac_over_dc_db = 10log10(⟨|E/⟨E⟩−1|²⟩) 와 "
        "verify_po_elev_unit 의 ac_below_dc_db = 10log10(AC%/DC%) 는 **같은 양**이다. "
        "창 없는 FFT 에서 P[0]=|⟨E⟩|², ΣP=⟨|E|²⟩ 이므로 AC%/DC% = "
        "(⟨|E|²⟩−|⟨E⟩|²)/|⟨E⟩|² = ⟨|E−⟨E⟩|²⟩/|⟨E⟩|² 로 정확히 일치한다. "
        "위 표의 두 열이 소수 둘째자리까지 같은 것으로 수치 확인했다."),
}

# ═══ S1. 광선 예산 사다리 (PathSolver) ═══════════════════════════════════════
ladder = {}
for el in (0, -90):
    rung = []
    for arm, spp in ARM_SPP.items():
        key = f"{arm}/el{el:+.0f}"
        if key not in SW.files:
            continue
        E = np.asarray(SW[key], complex)
        npv = npaths_of(arm, el)
        sjr = next((r for r in SJ["rows"]
                    if r["engine"] == arm and abs(r["el_deg"] - el) < 1e-6), None)
        A = np.abs(E)
        rung.append(dict(
            arm=arm, spp=spp, el_deg=el,
            npaths_mean=(round(float(npv.mean()), 2) if npv is not None else None),
            npaths_median=(float(np.median(npv)) if npv is not None else None),
            npaths_cv=(round(float(npv.std() / npv.mean()), 5) if npv is not None else None),
            level_meanabs_db=round(float(20 * np.log10(A.mean())), 2),
            absE_cv=round(float(A.std() / A.mean()), 5),
            ac_over_dc_db=round(acdc_db(E), 2),
            corr_npaths_vs_absE=(round(float(np.corrcoef(npv, A)[0, 1]), 4)
                                 if npv is not None else None),
            ledger_beat_hz=(sjr["track"]["beat_hz"] if sjr else None),
            ledger_band_power_db=(sjr["track"]["band_power_db"] if sjr else None),
            ledger_level_db=(sjr["level_db"] if sjr else None)))
    rung.sort(key=lambda r: r["spp"])
    ladder[f"el{el:+.0f}"] = rung
s0, s90 = ladder["el+0"], ladder["el-90"]
rN = 250_000_000 / SPP0
dmeas = s90[1]["ac_over_dc_db"] - s90[0]["ac_over_dc_db"]
J["S1_ray_budget_ladder"] = {
    "note_ko": ("AC/DC 가 광선 예산 N 에 어떻게 걸리나. 몬테카를로 표본잡음이면 분산 ∝ 1/N "
                "→ 예산 22.5 배에 −13.52 dB. 물리면 0 dB."),
    "el+0": s0, "el-90": s90,
    "el-90_two_point": {
        "spp_ratio": round(rN, 4),
        "delta_ac_db_measured": round(dmeas, 2),
        "delta_ac_db_if_power_1_over_N": round(-10 * np.log10(rN), 2),
        "delta_ac_db_if_amplitude_1_over_sqrtN": round(-10 * np.log10(rN), 2),
        "note_units_ko": ("⚠«√N 이면 −13.5 dB, 1/N 이면 −13.5 dB» 는 같은 말이다 — "
                          "진폭이 1/√N 이면 전력이 1/N 이고, ac_over_dc_db 는 **전력비**의 "
                          "dB 라 두 표현이 같은 −10log10(22.5) = −13.52 dB 를 가리킨다. "
                          "잡음이 진폭 기준으로 1/N 까지 떨어지는(= 전력 1/N²) 일은 없다."),
        "npaths_ratio": round(s90[1]["npaths_median"] / s90[0]["npaths_median"], 3),
        "delta_ac_db_if_power_1_over_npaths": round(
            -10 * np.log10(s90[1]["npaths_median"] / s90[0]["npaths_median"]), 2),
        "measured_fraction_of_1_over_N": round(dmeas / (-10 * np.log10(rN)), 3),
        "apparent_power_law_exponent": round(dmeas / (10 * np.log10(rN)), 4),
        "level_also_moved_db": round(s90[1]["level_meanabs_db"] - s90[0]["level_meanabs_db"], 2),
        "reading_ko": ("실측 −11.24 dB 는 순수 1/N 인 −13.52 dB 의 83 % 다. 물리(0 dB)가 "
                       "아니라 명백히 잡음 쪽이다. ⚠단, 아래 «절대 대 상대» 를 반드시 같이 읽어라."),
    },
}
_dc = [r["level_absmean_db"] for r in
       (rows["sionna/el-90"], rows["sionna_p250000000/el-90"])]
_ac_abs = [rows["sionna/el-90"]["ac_over_dc_db"] + _dc[0],
           rows["sionna_p250000000/el-90"]["ac_over_dc_db"] + _dc[1]]
J["S1_ray_budget_ladder"]["el-90_absolute_vs_relative"] = {
    "note_ko": ("⭐이 라운드에서 스스로 잡은 함정. AC/DC 는 **비**다. 나딧에서는 분모도 "
                "움직였으므로 비의 감소를 그대로 «잡음이 준 양» 으로 읽으면 안 된다."),
    "carrier_10log10_absmeanE2_db": [round(x, 2) for x in _dc],
    "carrier_change_db": round(_dc[1] - _dc[0], 2),
    "absolute_ac_power_db": [round(x, 2) for x in _ac_abs],
    "absolute_ac_change_db": round(_ac_abs[1] - _ac_abs[0], 2),
    "reading_ko": (
        "광선을 22.5 배 올리자 —\n"
        "• 반송파(|⟨E⟩|²) 가 **+13.64 dB 올랐다**. 즉 저예산 판은 나딧에서 표적을 거의 "
        "못 찾고 있었다(레벨 −130 dB 대 el 0 의 −60 dB).\n"
        "• 절대 요동전력은 **+2.40 dB 올랐다** — 줄지 않았다.\n"
        "• 비(AC/DC)만 −11.24 dB 줄었다.\n"
        "⇒ «잡음이 1/N 으로 줄었다» 는 단순 서술은 **틀렸다.** 맞는 서술은 «나딧에서는 "
        "반송파도 요동도 둘 다 수렴 안 했고, 반송파가 더 빨리 올라 변조 깊이가 줄었다» 다. "
        "그래도 판정은 그대로 «잡음» 이다 — 물리라면 예산을 올려도 두 양 **모두** 안 움직여야 "
        "하는데 하나는 13.6 dB, 다른 하나는 2.4 dB 움직였다. 그리고 S5 에서 기본파 크기가 "
        "물리값 대비 +31.9 → +15.2 dB 로 내려온 것이 «물리 위에 얹힌 과잉» 을 직접 보여준다."),
}
a1, a2 = 10 ** (s90[0]["ac_over_dc_db"] / 10), 10 ** (s90[1]["ac_over_dc_db"] / 10)
J["S1_ray_budget_ladder"]["el-90_floor_two_point_fit"] = {
    "floor_if_exactly_1_over_N_db": round(float(10 * np.log10(max((a2 - a1 / rN) / (1 - 1 / rN),
                                                                 1e-12))), 2),
    "caveat_ko": ("⚠두 점으로 «1/N 잡음 + 물리 바닥» 을 풀면 바닥이 하나 나오지만 "
                  "**식별되지 않는다** — 같은 두 점은 바닥 없는 N^(−0.83) 순수 잡음으로도 "
                  "똑같이 설명된다. 세 번째 예산이 있어야 갈린다."),
}

# ═══ S2. el 0 사다리 — 무엇이 수렴하고 무엇이 안 했나 ════════════════════════
lvl = [r["ledger_level_db"] for r in s0]
bp = [r["ledger_band_power_db"] for r in s0]
beat = [r["ledger_beat_hz"] for r in s0]
leak = NF["A_instrument_audit"]["synthetic_tests"]["constant (no modulation at all)"]
J["S2_el0_what_converged"] = {
    "question_ko": "«수렴했는데 틀렸다» 가 맞는 서술인가",
    "rungs": [dict(spp=r["spp"], npaths_median=r["npaths_median"], npaths_cv=r["npaths_cv"],
                   level_db=r["ledger_level_db"], band_power_db=r["ledger_band_power_db"],
                   band_minus_level_db=round(r["ledger_band_power_db"] - r["ledger_level_db"], 2),
                   beat_hz=r["ledger_beat_hz"], ac_over_dc_db=r["ac_over_dc_db"],
                   absE_cv=r["absE_cv"],
                   corr_npaths_vs_absE=r["corr_npaths_vs_absE"]) for r in s0],
    "budget_span": round(4e9 / SPP0, 1),
    "level_spread_db": round(max(lvl) - min(lvl), 3),
    "band_power_spread_db": round(max(bp) - min(bp), 3),
    "beat_spread_hz": round(max(beat) - min(beat), 2),
    "beat_true_hz": round(FFL, 2),
    "beat_err_pct": [round(100 * (b - FFL) / FFL, 1) for b in beat],
    "leakage_control": {
        "synthetic_constant_band_minus_carrier_db": leak["reported_band_power_db"],
        "measured_band_minus_level_db": [round(b - l, 2) for b, l in zip(bp, lvl)],
        "verdict_ko": ("⭐결정적. A 절 통제군 — «변조가 전혀 없는 상수» 를 같은 계측기에 넣으면 "
                       "대역전력이 반송파보다 −14.04 dB 로 «보인다»(순수 창 누설). PathSolver 의 "
                       "el 0 실측 대역전력은 네 예산 모두 −14.03 ~ −14.07 dB 다. "
                       "⇒ PathSolver 의 el 0 블레이드 대역에는 **진짜 변조가 없다**. "
                       "보고된 대역전력·박자는 전부 계측기의 누설을 읽은 것이다."),
    },
    "answer_ko": (
        "«수렴했는데 틀렸다» 는 **반쯤만 맞다.** 정확히는 —\n"
        "(1) **수렴한 것**: 평균장(반송파). 예산 360 배에 레벨이 0.03 dB 안이다. 이건 진짜 "
        "수렴이고, 정지한 동체의 정반사 경로 9 개가 예산과 무관하게 잡히기 때문이다.\n"
        "(2) **애초에 없던 것**: 로터 변조. 최저예산에서 AC/DC 가 −83.6 dB (|E| 변동 0.004 %) "
        "로 **신호가 사실상 상수**다. 틀린 게 아니라 비어 있었다.\n"
        "(3) **수렴 안 한 것**: AC. 예산을 올리면 −83.6 → −39.7 → −33.9 → −30.8 dB 로 "
        "**올라간다**(잡음이 줄어드는 게 아니라, 없던 약한 경로를 새로 찾으면서 표본잡음이 "
        "생긴다). 4,000 M 에서도 아직 오르는 중이고, 우리 커널의 el 0 값 −15.3 dB 보다 "
        "15 dB 아래다.\n"
        "(4) **박자**: 없는 변조 위에서 argmax 를 뜨니 예산마다 다른 잡음 봉우리를 문다 "
        "(376.7 → 50.3 → 122.1 → 58.2 Hz, 참값 126.67 Hz).\n"
        "⇒ 옳은 서술은 «레벨은 수렴했고, 마이크로도플러는 처음부터 없었으며, 보고된 박자는 "
        "계측기 누설의 argmax 다». «수렴한 값이 틀렸다» 가 아니라 **서로 다른 두 양이고 "
        "그중 하나만 수렴했다**."),
    "other_reading_ko": (
        "⚠다른 해석 가능성 — 레벨 수렴이 «정답에 수렴» 이 아니라 «같은 편향에 갇힘» 일 수 "
        "있다. PathSolver 에는 산란적분이 없어 로터 같은 few-λ 구조를 원리적으로 못 내므로, "
        "예산을 아무리 올려도 **없는 항이 생기지는 않는다**. 그러면 레벨은 «동체 정반사만의 "
        "정답» 에 수렴한 것이고 표적 전체의 정답은 아니다. 이 두 해석은 지금 데이터로 못 "
        "가른다 — 가르려면 로터만 있는 표적으로 같은 사다리를 태워야 한다."),
}

# ═══ S3. 나딧 경로 수 변동 vs |E| ═══════════════════════════════════════════
s3 = {}
for arm in ("sionna", "sionna_p250000000"):
    for el in (0, -90):
        key = f"{arm}/el{el:+.0f}"
        npv = npaths_of(arm, el)
        if key not in SW.files or npv is None:
            continue
        E = np.asarray(SW[key], complex)
        A = np.abs(E)
        s3[f"{arm}/el{el:+.0f}"] = dict(
            spp=ARM_SPP[arm],
            npaths_mean=round(float(npv.mean()), 2),
            npaths_cv=round(float(npv.std() / npv.mean()), 5),
            npaths_min=int(npv.min()), npaths_max=int(npv.max()),
            absE_cv=round(float(A.std() / A.mean()), 5),
            absE_max_over_min=round(float(A.max() / A.min()), 1),
            corr_npaths_vs_absE=round(float(np.corrcoef(npv, A)[0, 1]), 4),
            ac_over_dc_db=round(acdc_db(E), 2))
Eo = np.asarray(SW["ours/el-90"], complex)
s3["ours/el-90"] = dict(spp=None, npaths_cv=None,
                        absE_cv=round(float(np.abs(Eo).std() / np.abs(Eo).mean()), 5),
                        absE_max_over_min=round(float(np.abs(Eo).max() / np.abs(Eo).min()), 3),
                        ac_over_dc_db=round(acdc_db(Eo), 2))
J["S3_path_churn"] = {
    "hypothesis_ko": ("사용자 가설: 자세마다 경로 집합이 갈아엎히면 |E| 가 충격처럼 튀고, "
                      "그것이 주파수축에서 **평평한 빗살**이 된다."),
    "arms": s3,
    "verdict_ko": (
        "**절반 맞고 절반 틀렸다.**\n"
        "✔맞은 절반 — 나딧에서 경로 수와 |E| 는 실제로 같이 움직인다. corr(npaths,|E|) 가 "
        "11.1 M 에서 **0.869**, 250 M 에서 0.807 이다. 그리고 |E| 는 «충격처럼» 튄다 — "
        "11.1 M 나딧에서 |E| 최대/최소 비가 **214 배**다(4.3e−9 ~ 9.3e−7).\n"
        "✔대조 — el 0 에서는 같은 경로 수 변동(CV 0.150, 6~9 개)이 있는데도 corr 이 "
        "**0.005**, |E| 변동계수가 4e−5 다. 즉 el 0 에서 갈아엎히는 경로는 에너지를 안 "
        "실어 나른다. **나딧에서만** 경로 하나하나가 신호 전체를 좌우한다.\n"
        "✘틀린 절반 — 그 결과가 **평평하지 않다**. 나딧 요동 전력의 92~94 % 가 플래시 빗살 "
        "위에 얹혀 있다(빗살이 차지한 빈은 14.6 % 뿐). 이유는 seed=1 이 고정이라 "
        "**표본화가 자세의 결정론적 함수**이고 자세가 로터 주기로 반복하기 때문이다. "
        "⇒ 잡음도 주기적이라 빗살에 얹힌다. 진짜 백색은 딱 한 자리에서만 나온다 — "
        "sionna el 0 최고예산(4,000 M), 빗살 비중 0.134 ≈ 빈 비중 0.146."),
    "consequence_ko": ("⭐이것이 이 라운드에서 뒤집힌 것이다. **빗살 구조는 두 팔 모두에서 "
                       "물리의 증거가 못 된다.** 우리 팔의 격자도 얼려 있어 같은 논리가 걸린다."),
}

# ═══ S4. 우리 팔 — 격자 사다리 + 격자 없는 대리모형과의 상관 ═════════════════
unit = []
for c in UT["cases"]:
    if c["target"] == "one_sphere" and c["el_deg"] == -90.0:
        ac = 100.0 - c["kernel"]["dc_power_pct"]
        unit.append(dict(div=c["div"], spacing_mm=round(c["spacing_m"] * 1000, 4),
                         n_rays=c["n_rays"],
                         ac_below_dc_db=round(float(10 * np.log10(ac / (100 - ac))), 2),
                         rho_vs_analytic=round(c["match"]["rho"], 6)))
unit.sort(key=lambda r: r["div"])


def split_row(E, P, tag=None):
    """AC 전력을 (기본파=물리) / (k≥2 빗살+빗살밖=격자) 로 가르고 대리모형과 상관."""
    E = np.asarray(E, complex)
    n = E.size
    dE, dP = rel(E), rel(P[:n])
    tot = float(np.mean(np.abs(dE) ** 2))
    k1, _ = harm_pick(dE, [1])
    hi, _ = harm_pick(dE, range(3, 71))
    p1 = float(np.mean(np.abs(k1) ** 2) / tot)
    pk1, _ = harm_pick(dP, [1])
    rall, cv = cxcorr(dE, dP)
    r1, _ = cxcorr(k1, pk1)
    amp = float(np.sqrt(np.mean(np.abs(k1) ** 2) / np.mean(np.abs(pk1) ** 2)))
    env = harm_env(E)
    out = dict(n_poses=n, ac_over_dc_db=round(10 * np.log10(tot), 2),
               fundamental_share=round(p1, 4),
               harmonics_k3plus_share=round(float(np.mean(np.abs(hi) ** 2) / tot), 4),
               corr_with_gridless_proxy=round(rall, 4), corr_convention=cv,
               explained_power_share=round(rall ** 2, 4),
               corr_of_fundamental=round(r1, 4),
               fundamental_amp_over_proxy_db=round(20 * np.log10(amp), 2),
               physics_part_db=round(10 * np.log10(tot * p1), 2),
               grid_part_db=round(10 * np.log10(tot * (1 - p1)), 2),
               harmonic_envelope_slope_db_per_octave=round(env_slope(env), 2),
               harmonic_plateau_k20plus_db=round(float(np.nanmean(env[19:])), 2))
    if tag:
        out["tag"] = tag
    return out


drone = []
for tag in sorted(GS["runs"], key=lambda t: GS["runs"][t]["div"]):
    r = GS["runs"][tag]
    E = np.asarray(r["E_re"], float) + 1j * np.asarray(r["E_im"], float)
    row = split_row(E, P10, tag)
    row.update(div=r["div"], spacing_mm=round(r["spacing_m"] * 1000, 4), n_grid=r["n_grid"],
               level_db=round(float(20 * np.log10(np.abs(E).mean())), 2))
    drone.append(row)
full = split_row(Eo, P10, "lambda12_full4096")
full.update(div=12, spacing_mm=7.1379)
proxy_self = split_row(P10, P10, "gridless_proxy")


def slope_per_halving(xs, ys):
    x = np.log10(np.asarray(xs, float)); y = np.asarray(ys, float)
    return float(np.polyfit(x, y, 1)[0] * np.log10(2.0))


geo = NF["C_D_geometry"]
gp = [10 ** (r["grid_part_db"] / 10) for r in drone]
J["S4_our_arm"] = {
    "note_ko": "우리 팔의 «예산» 은 격자 간격이다. 조이면 격자잡음은 떨어지고 물리는 안 떨어진다.",
    "gridless_proxy_self": {
        **proxy_self,
        "plane_wave_far_field_ac_db": round(acdc_db(PLW), 2),
        "spherical_by_range_db": {f"{int(R)}m": round(acdc_db(v), 2)
                                  for R, v in sorted(SPH.items())},
        "range_power_law_exponent": round(
            (acdc_db(SPH[160.0]) - acdc_db(SPH[10.0])) / (10 * np.log10(16.0)), 3),
        "props_only_db": round(acdc_db(PPR), 2),
        "body_only_db": round(acdc_db(PBD), 2),
        "reading_ko": ("⭐대리모형의 나딧 변조는 **기본파 하나뿐**이다 — 고조파 봉투가 "
                       "−26.2 dB/옥타브로 무너져 k=3 에서 이미 −111 dB 다. 기본파가 전력의 "
                       "93.8 % 를 갖는다. 그리고 동체만 남기면 −312 dB 로 사라지고 프로펠러만 "
                       "남기면 전체와 같다 ⇒ 전적으로 회전날개 때문이다. "
                       "평면파(원거리장)에서는 −307 dB, 즉 **정확히 0** 이다 — 나딧 시선에서 "
                       "z 축 회전은 면 법선의 z 성분도 면 중심의 z 좌표도 안 바꾸기 때문이다. "
                       "거리에는 전력 1/r^4.07 로 죽는다."),
    },
    "unit_test_one_sphere_el-90": {
        "target_ko": "반지름 2 cm 구 하나가 0.137 m 반경으로 공전 — 해석해가 있는 최소 표적",
        "rungs": unit,
        "db_per_halving_of_spacing": round(
            slope_per_halving([r["spacing_mm"] for r in unit],
                              [r["ac_below_dc_db"] for r in unit]), 2),
        "meaning_ko": "이 표적의 잔여는 **전부** 격자잡음이다(해석 도플러가 정확히 0).",
    },
    "drone_grid_ladder_el-90": {
        "source": "outputs/verify_po_elev_gridscale.json runs[div8|div12|div16], 자세 0..511",
        "rungs": drone,
        "full_sweep_lambda12": full,
        "sign_convention_ko": "양수 = 간격을 절반으로 조일 때 그만큼 dB 가 **떨어진다**.",
        "total_db_per_halving": round(
            slope_per_halving([r["spacing_mm"] for r in drone],
                              [r["ac_over_dc_db"] for r in drone]), 2),
        "grid_part_db_per_halving": round(
            slope_per_halving([r["spacing_mm"] for r in drone],
                              [r["grid_part_db"] for r in drone]), 2),
        "physics_part_db_per_halving": round(
            slope_per_halving([r["spacing_mm"] for r in drone],
                              [r["physics_part_db"] for r in drone]), 2),
        "reading_ko": ("격자 지분은 간격 반감에 **6.83 dB** 떨어지고(−37.98 → −40.89 → "
                       "−44.94), 물리 지분은 −44.56 → −41.36 → −42.84 로 3 dB 폭 안에서 "
                       "제자리다(단조가 아니다 — λ/8 에서는 격자가 너무 성겨 코히어런트 항 "
                       "자체를 과소평가한다. 기본파 상관이 0.876 밖에 안 된다). "
                       "⚠세 점뿐이라 지수는 ±2 dB/옥타브 열려 있다."),
    },
    "answer_to_the_-38_vs_-21_paradox_ko": (
        "질문 4(a)/(b) 정면 답 —\n"
        "(a) **두 수의 정의는 같다.** S0 에서 두 경로로 계산해 소수 둘째자리까지 일치를 "
        "확인했다.\n"
        "(b) 같은 정의인데 드론(−38.3)이 단위구(−21.8)보다 낮은 것은 **모순이 아니다.** "
        "격자잡음은 보편 바닥이 아니라 **표적에 얹히는 격자 칸 수**에 걸린다. 단위구는 "
        "투영면적 1.26e−3 m² 라 λ/12 칸이 ~25 개뿐이고, 드론은 나딧 투영면적 0.0949 m² 라 "
        "~1,862 개다(75 배). 칸 수에 반비례하면 18.7 dB 더 낮은 −40.5 dB 가 나온다 — "
        "실측 −38.3 과 2 dB 차이다. ⇒ 이 외삽 하나만으로는 «우리 잔여도 잡음» 을 배제 못 한다.\n"
        "⭐그래서 외삽 대신 **드론 자체의 격자 사다리와 격자 없는 대리모형**으로 갈랐다. "
        "결과: λ/12 에서 잔여의 **44.6 % 가 물리**(기본파, 대리모형과 상관 0.966), "
        "**55.4 % 가 격자 모아레**(k≥3 빗살, Nyquist 까지 평평). 격자를 λ/8→λ/16 으로 조이면 "
        "물리 비중이 18 % → 47 % → 62 % 로 오르고 대리모형과의 전체 상관이 "
        "0.398 → 0.696 → 0.825 로 오른다. **격자를 조일수록 남는 것이 물리다.**"),
    "cells_estimate": {
        "unit_sphere_proj_area_m2": round(float(np.pi * 0.02 ** 2), 6),
        "drone_nadir_proj_area_m2": geo["projected_area_m2_vs_el"]["-90"],
        "ratio": round(float(geo["projected_area_m2_vs_el"]["-90"] / (np.pi * 0.02 ** 2)), 1),
        "extrapolated_grid_floor_db": round(float(
            unit[0]["ac_below_dc_db"] -
            10 * np.log10(geo["projected_area_m2_vs_el"]["-90"] / (np.pi * 0.02 ** 2))), 2),
    },
}

# ═══ S5. PathSolver 나딧 vs 물리 ════════════════════════════════════════════
ps = {}
for arm in ("sionna", "sionna_p250000000"):
    E = np.asarray(SW[f"{arm}/el-90"], complex)
    r = split_row(E, P10)
    r.update(spp=ARM_SPP[arm], corr_with_our_kernel=round(cxcorr(rel(E), rel(Eo))[0], 4))
    ps[arm] = r
rng = np.random.default_rng(0)
ctrl = [cxcorr(rng.normal(size=N) + 1j * rng.normal(size=N), rel(P10))[0] for _ in range(32)]
J["S5_pathsolver_vs_physics"] = {
    "note_ko": ("PathSolver 의 나딧 요동을 «격자 없는 물리» 와 맞대본다. 기본파를 떼어내 "
                "크기까지 견준다 — 물리면 크기가 맞아야 한다."),
    "arms": ps,
    "gridless_proxy_fundamental_is_the_truth_ko": (
        "대리모형의 기본파를 «참값 1» 로 놓으면 — PathSolver 의 나딧 기본파는 11.1 M 에서 "
        "**39.3 배(+31.9 dB)**, 250 M 에서 **5.76 배(+15.2 dB)** 로 **너무 크다**. "
        "우리 커널은 0.71 배(−2.98 dB)로 같은 자리에 있다(재질 |Γ|<1·가림이 있어 대리모형보다 "
        "약간 작은 것은 예상대로다)."),
    "white_noise_control": {"n_draws": len(ctrl),
                            "corr_mean": round(float(np.mean(ctrl)), 4),
                            "corr_p95": round(float(np.percentile(ctrl, 95)), 4)},
}

# ═══ S6. 사용자의 실증 관찰 — 나딧 널은 면도날처럼 얇다 ══════════════════════
J["S6_why_the_field_sees_doppler"] = {
    "note_ko": ("사용자의 관찰(«실증에서도 나딧 도플러가 남더라»)은 근접장 곡률로는 설명이 "
                "안 된다 — 그건 10 m 에서 −38.6 dB, 160 m 에서 −87.5 dB 라 야외 거리에서는 "
                "없는 것과 같다. 진짜 이유는 훨씬 단순하다."),
    "far_field_plane_wave_ac_vs_off_nadir_deg": geo["offnadir_farfield"],
    "reading_ko": ("원거리장 평면파에서도 나딧을 **0.5° 만 벗어나면** AC/DC 가 −55.9 dB, "
                   "1° 에서 −44.1, 2° 에서 −32.8, **5° 에서 −11.9 dB** 로 사실상 만조가 된다. "
                   "정확히 0° 일 때만 −305 dB 다. ⇒ 나딧 널은 **폭이 몇 도짜리 면도날**이라, "
                   "실측에서는 기체 자세 기울기·바람·비행 위치 오차만으로도 늘 벗어난다. "
                   "«90° 에서도 도플러가 남는다» 는 관찰은 **정확히 90° 가 실현되지 않기 "
                   "때문**이라고 보는 게 가장 단순한 설명이다."),
    "not_refraction_ko": ("⭐사용자 가설의 기전(굴절·회절)은 이 실행에서는 성립하지 않는다. "
                          "앙각 스윕의 PathSolver 호출은 max_depth=1·refraction=False 이고 "
                          "diffraction·edge_diffraction 을 아예 안 넘겨 기본값 False 였다. "
                          "굴절·회절·다중반사가 **전부 꺼져 있었다**. 반대로 우리 팔은 "
                          "penetrate=True(투과 켜짐)라 이 축에서는 우리가 물리를 더 담았다. "
                          "그리고 두 팔 다 구면파라 «평면파 가정» 은 어느 쪽에도 없다."),
}

# ═══ S7. 판정 ═══════════════════════════════════════════════════════════════
J["S7_verdict"] = {
    "pathsolver_nadir": {
        "verdict": "NOISE",
        "confidence": "high",
        "ko": ("**표본잡음이다.** 근거 네 겹 — "
               f"(1) 광선을 22.5 배 올리자 AC/DC 가 {dmeas:+.2f} dB 줄었다. 물리면 0 dB, "
               "순수 1/N 이면 −13.52 dB 인데 실측은 잡음 쪽 83 % 자리다. "
               "(2) 기본파의 **크기**가 격자 없는 물리보다 11.1 M 에서 +31.9 dB, 250 M 에서 "
               "+15.2 dB 크다 — 물리를 재현한 게 아니라 물리 위에 잡음이 얹힌 것이고, 예산을 "
               "올리자 물리 쪽으로 16.7 dB 내려왔다. "
               "(3) 나딧에서 corr(경로 수, |E|) = 0.87, |E| 최대/최소 214 배 — 신호가 "
               "«이번 자세에 경로가 몇 개 잡혔나» 로 결정된다. "
               "(4) 평균 레벨조차 +13.6 dB 움직였다 — 나딧에서는 반송파도 수렴 안 했다. "
               "⚠정직하게 덧붙인다 — **절대** 요동전력은 오히려 +2.4 dB 올랐다. AC/DC 가 준 "
               "것은 반송파가 더 빨리 올랐기 때문이다. 그래서 «1/N 으로 준다» 는 단순한 "
               "잡음 법칙 서술은 쓰면 안 되고, 쓸 수 있는 서술은 «나딧에서 PathSolver 는 "
               "아무것도 수렴시키지 못했고 기본파 크기가 물리보다 15~32 dB 과하다» 다. "
               "⚠«무엇으로 수렴하는가» 는 모른다 — 250 M 에서도 바닥이 안 보인다."),
    },
    "ours_nadir": {
        "verdict": "MOSTLY PHYSICS (about half physics, half grid moiré at λ/12)",
        "confidence": "medium-high",
        "ko": ("**절반이 물리, 절반이 격자 모아레다.** λ/12 에서 —\n"
               "• 물리 44.6 % : 플래시 기본파 하나. 격자가 아예 없는 PO 대리모형의 기본파와 "
               "상관 **0.966**, 크기 0.71 배(−2.98 dB). 대리모형은 평면파로 바꾸면 −307 dB 로 "
               "사라지고 거리에 1/r^4.07 로 죽는다 ⇒ 기전은 **근접장 파면 곡률**이다.\n"
               "• 격자 55.4 % : 내역은 2 차 고조파 2.8 % + 3 차 이상 빗살 32.8 % + 빗살 밖 "
               "20.0 %. 물리(대리모형)의 고조파 봉투는 −26.2 dB/옥타브로 무너져 2 차가 이미 "
               "−57 dB 이므로 **2 차 이상은 전부 물리가 아니다**.\n"
               "• 격자를 λ/8 → λ/12 → λ/16 으로 조이면 물리 비중이 18 → 47 → 62 % 로 오르고 "
               "대리모형과의 상관이 0.398 → 0.696 → 0.825 로 오른다. "
               "**조일수록 남는 것이 물리다** — 이게 이 축의 결론이다.\n"
               "⚠남는 불확실성 — 물리 지분의 절대값(−41.8 dB)은 대리모형이라는 하나의 "
               "독립 모형에만 기대고 있다. 대리모형은 재질·가림·다중반사가 없다."),
    },
    "user_hypothesis": {
        "mechanism_claim": "REFUTED (for this run)",
        "observation_claim": "SUPPORTED, different mechanism",
        "ko": ("기전 주장(«PathSolver 가 굴절·회절을 더 담아서») 은 **반증됐다** — 그 호출에는 "
               "굴절·회절·다중반사가 전부 꺼져 있었고 우리 팔이 오히려 투과를 켜고 있었다. "
               "«평면파 가정» 도 어느 팔에도 없다(둘 다 구면파). "
               "관찰(«실증에서도 나딧 도플러가 남는다») 은 **지지된다** — 다만 이유는 회절이 "
               "아니라, (i) 근거리에서는 파면 곡률이 −38 dB 짜리 기본파를 남기고, "
               "(ii) 무엇보다 **나딧 널이 폭 몇 도짜리 면도날**이라 5° 만 벗어나도 −11.9 dB 로 "
               "만조가 되기 때문이다. 야외에서 정확히 90° 는 실현되지 않는다."),
    },
    "needs_gpu": [
        "⭐el −90 에서 세 번째 광선 예산(1,000 M 또는 4,000 M). 두 점으로는 «1/N 잡음» 과 "
        "«잡음 + 물리 바닥» 이 식별되지 않는다. 이것 하나면 PathSolver 판정의 «무엇으로 "
        "수렴하는가» 가 채워진다.",
        "⭐드론 el −90 격자 사다리를 λ/24·λ/48 까지 — 지금 물리 지분 외삽이 세 점에 기대고 있다.",
        "굴절·회절을 실제로 켠 sionna_phys 팔의 el −90 (GPU 3 에서 진행 중) — 사용자 가설의 "
        "진짜 시험은 «물리를 켜면 나딧 기본파 크기가 대리모형 값으로 내려오는가» 다.",
        "우리 팔 + PTD(모서리 회절) 의 el −90 (ours_ptd, 진행 중) — 회절이 나딧 기본파를 "
        "얼마나 바꾸는가.",
        "⚠(선택) 로터만 있는 표적으로 el 0 예산 사다리 — S2 의 «레벨 수렴이 정답인가 편향인가» "
        "를 가르려면 필요하다.",
    ],
    "unknowns_ko": [
        "PathSolver 나딧 AC 가 **무엇으로** 수렴하는지 모른다(바닥 미관측).",
        "우리 팔 물리 지분의 절대값은 독립 모형이 대리모형 하나뿐이라 ±2~3 dB 는 열려 있다.",
        "대리모형의 거리 지수가 1/r^4.07 인 이유를 유도하지 못했다 — 소박한 근접장 논변은 "
        "1/r² 를 준다. 실측만 적는다.",
        "el 0 에서 PathSolver 레벨이 수렴한 것이 «정답» 인지 «동체 정반사만의 정답» 인지 못 갈랐다.",
    ],
}

os.makedirs(f"{ROOT}/outputs/figs", exist_ok=True)
json.dump(J, open(OUT, "w"), ensure_ascii=False, indent=1)
print("wrote", OUT)


# ═══ 그림 ═══════════════════════════════════════════════════════════════════
def figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    C_OURS, C_PS, C_PX, C_UNIT = "tab:green", "tab:red", "0.15", "tab:blue"
    fig, ax = plt.subplots(2, 3, figsize=(19.5, 10.4))

    # (a) 광선 예산 사다리
    a = ax[0, 0]
    x0 = [r["spp"] for r in s0]; y0 = [r["ac_over_dc_db"] for r in s0]
    x9 = [r["spp"] for r in s90]; y9 = [r["ac_over_dc_db"] for r in s90]
    a.semilogx(x9, y9, "s-", color=C_PS, ms=10, lw=2.4, label="PathSolver  el −90° (nadir)")
    a.semilogx(x0, y0, "o-", color="tab:orange", ms=8, lw=2, label="PathSolver  el 0°")
    xr = np.array([x9[0], 6e9])
    a.semilogx(xr, y9[0] - 10 * np.log10(xr / x9[0]), "--", color=C_PS, alpha=.5, lw=1.6,
               label="pure Monte-Carlo noise  ∝ 1/N")
    a.axhline(acdc_db(Eo), color=C_OURS, lw=2.4, label="our PO/SBR kernel  el −90°")
    a.axhline(acdc_db(P10), color=C_PX, ls=":", lw=2,
              label="grid-free PO proxy (the physics)")
    a.annotate(f"{dmeas:+.2f} dB for 22.5× rays\n(physics would give 0,\n pure 1/N would give "
               f"{-10*np.log10(rN):.2f})",
               xy=(x9[1], y9[1]), xytext=(2.2e8, 8), fontsize=9.6, color="0.15",
               arrowprops=dict(arrowstyle="->", color="0.4"))
    a.set_xlabel("samples_per_src   (ray budget N)")
    a.set_ylabel("AC / DC  [dB]   (fluctuation power ÷ carrier power)")
    a.set_title("(a) Ray budget: physics would not move. It moved.", fontsize=12)
    a.grid(alpha=.3); a.legend(fontsize=8.5, loc="lower left"); a.set_ylim(-46, 22)

    # (b) el 0 — 레벨 수렴 vs 박자 방황
    b = ax[0, 1]
    b.semilogx(x0, lvl, "o-", color=C_UNIT, ms=9, lw=2.4)
    b.set_xlabel("samples_per_src   (ray budget N)")
    b.set_ylabel("carrier level  20·log10⟨|E|⟩  [dB]", color=C_UNIT)
    b.tick_params(axis="y", labelcolor=C_UNIT); b.set_ylim(-59.9, -59.45)
    b.set_title("(b) el 0°: the carrier converged, the beat never existed", fontsize=12)
    b2 = b.twinx()
    b2.semilogx(x0, beat, "D--", color="tab:orange", ms=10, lw=1.8)
    b2.axhline(FFL, color="k", ls="-.", lw=1.6)
    b2.text(1.3e7, FFL + 14, f"true blade-flash rate  {FFL:.1f} Hz", fontsize=9.2)
    b2.set_ylabel("reported beat  [Hz]", color="tab:orange")
    b2.tick_params(axis="y", labelcolor="tab:orange"); b2.set_ylim(0, 430)
    for xx, yy in zip(x0, beat):
        b2.annotate(f"{yy:.0f}", (xx, yy), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=8.8, color="tab:orange")
    b.text(.03, .05, f"level spread over {4e9/SPP0:.0f}× budget : {max(lvl)-min(lvl):.2f} dB\n"
                     f"beat spread : {max(beat)-min(beat):.0f} Hz\n"
                     f"band power − carrier : {bp[0]-lvl[0]:.2f} dB\n"
                     f"same instrument on a CONSTANT : {leak['reported_band_power_db']:.2f} dB",
           transform=b.transAxes, fontsize=9.1, va="bottom",
           bbox=dict(fc="w", ec="0.65", alpha=.93))
    b.grid(alpha=.3)

    # (c) 나딧 스펙트럼
    c = ax[0, 2]
    for E, col, lab, lw in ((P10, C_PX, "grid-free PO proxy (physics)", 2.2),
                            (Eo, C_OURS, "our PO/SBR kernel  λ/12", 1.2),
                            (np.asarray(SW["sionna_p250000000/el-90"], complex), C_PS,
                             "PathSolver  N = 250 M", 1.1)):
        d = rel(E)
        fr = np.fft.fftshift(np.fft.fftfreq(N, 1 / PRF))
        P = np.abs(np.fft.fftshift(np.fft.fft(d * np.hanning(N)))) ** 2
        P = 10 * np.log10(P / P.max())
        m = (fr >= 20) & (fr <= 1400)
        c.plot(fr[m], P[m], color=col, lw=lw, label=lab, alpha=.92)
    for k in range(1, 11):
        c.axvline(k * FFL, color="0.6", ls=":", lw=.9, zorder=0)
    c.text(4.2 * FFL, 5, "blade-flash comb  k × 126.7 Hz", fontsize=9.2, color="0.35")
    c.set_xlabel("frequency  [Hz]")
    c.set_ylabel("AC spectrum, normalised to own peak  [dB]")
    c.set_title("(c) Physics is one line. Everything else is a comb.", fontsize=12)
    c.set_ylim(-62, 12); c.grid(alpha=.3); c.legend(fontsize=8.6, loc="lower right")

    # (d) 고조파 봉투
    d_ = ax[1, 0]
    kk = np.arange(1, 71)
    for E, col, lab, ls in ((P10, C_PX, "grid-free PO proxy (physics)", "-"),
                            (np.asarray(SW["sionna_p250000000/el-90"], complex), C_PS,
                             "PathSolver  N = 250 M", "-"),
                            (Eo, C_OURS, "ours  λ/12", "-")):
        d_.semilogx(kk, harm_env(E), ls, color=col, lw=2.2, label=lab)
    for r, al in zip(drone, (.35, .55, .8)):
        E = (np.asarray(GS["runs"][r["tag"]]["E_re"], float) +
             1j * np.asarray(GS["runs"][r["tag"]]["E_im"], float))
        d_.semilogx(kk, harm_env(E), "--", color=C_OURS, lw=1.1, alpha=al,
                    label=f"ours  λ/{r['div']}  (512 poses)")
    d_.set_xlabel("harmonic order  k   of the blade-flash rate")
    d_.set_ylabel("harmonic power relative to k = 1  [dB]")
    d_.set_title("(d) The physics collapses after k = 1.  A flat comb is sampling error.",
                 fontsize=12)
    d_.set_ylim(-135, 22); d_.grid(alpha=.3, which="both"); d_.legend(fontsize=8, loc="lower left")

    # (e) 우리 팔 격자 사다리 분해
    e = ax[1, 1]
    hs = [r["spacing_mm"] for r in drone]
    e.plot(hs, [r["ac_over_dc_db"] for r in drone], "o-", color="0.35", ms=10, lw=2.2,
           label="total residual")
    e.plot(hs, [r["physics_part_db"] for r in drone], "o-", color=C_OURS, ms=10, lw=2.6,
           label="physics part  (fundamental)")
    e.plot(hs, [r["grid_part_db"] for r in drone], "o--", color="tab:purple", ms=10, lw=2.2,
           label="grid-moiré part  (k ≥ 2 + off-comb)")
    e.plot([r["spacing_mm"] for r in unit], [r["ac_below_dc_db"] for r in unit], "^:",
           color=C_UNIT, ms=10, lw=2,
           label="analytic point target — pure grid noise")
    e.axhline(acdc_db(P10), color=C_PX, ls=":", lw=1.8, label="grid-free proxy level")
    for r in drone:
        e.annotate(f"λ/{r['div']}", (r["spacing_mm"], r["ac_over_dc_db"]),
                   textcoords="offset points", xytext=(2, 9), fontsize=9, color="0.3")
    for r in unit:
        e.annotate(f"λ/{r['div']}", (r["spacing_mm"], r["ac_below_dc_db"]),
                   textcoords="offset points", xytext=(2, -14), fontsize=9, color=C_UNIT)
    e.set_xscale("log")
    e.set_xlabel("ray-grid spacing  [mm]        (finer  →)")
    e.set_ylabel("AC / DC  [dB]   (identical definition in both ledgers)")
    e.set_title("(e) Refine the grid: the moiré falls, the physics stays", fontsize=12)
    e.grid(alpha=.3, which="both")
    e.legend(fontsize=8.1, loc="upper center", bbox_to_anchor=(.5, -.135), ncol=2,
             frameon=False)
    e.set_ylim(-47, -18)
    e.invert_xaxis()

    # (f) 상관 사다리 + 면도날 널
    f_ = ax[1, 2]
    f_.plot(hs, [r["corr_with_gridless_proxy"] for r in drone], "o-", color=C_OURS,
            ms=11, lw=2.6, label="ours — correlation with the grid-free physics")
    f_.plot(hs, [r["fundamental_share"] for r in drone], "s--", color=C_OURS, ms=9,
            lw=1.8, alpha=.6, label="ours — fundamental's share of the residual")
    f_.set_xscale("log"); f_.invert_xaxis()
    f_.set_xlabel("ray-grid spacing  [mm]        (finer  →)")
    f_.set_ylabel("correlation  /  power share")
    f_.set_ylim(0, 1.05)
    f_.axhline(np.percentile(ctrl, 95), color="0.55", ls=":", lw=1.4)
    f_.text(hs[0], np.percentile(ctrl, 95) + .02, "chance level", fontsize=8.6, color="0.4")
    for r in drone:
        f_.annotate(f"λ/{r['div']}", (r["spacing_mm"], r["corr_with_gridless_proxy"]),
                    textcoords="offset points", xytext=(3, -15), fontsize=9, color=C_OURS)
    f_.set_title("(f) Finer grid → more of what is left is the physics", fontsize=12)
    f_.grid(alpha=.3, which="both")
    f_.legend(fontsize=8.3, loc="upper center", bbox_to_anchor=(.5, -.135), ncol=1,
              frameon=False)

    ins = f_.inset_axes([0.10, 0.50, 0.44, 0.42])
    off = sorted((v["off_nadir_deg"], v["ac_over_dc_db"])
                 for v in geo["offnadir_farfield"].values())
    ins.plot([o for o, _ in off][1:], [v for _, v in off][1:], "o-", color="tab:brown", ms=5,
             lw=1.7)
    ins.set_xlabel("degrees off nadir", fontsize=7.6, labelpad=1)
    ins.set_ylabel("AC/DC [dB]", fontsize=7.6, labelpad=1)
    ins.tick_params(labelsize=7)
    ins.text(.97, .06, "far-field null is razor thin", transform=ins.transAxes,
             fontsize=7.8, ha="right", color="0.25")
    ins.grid(alpha=.3)

    fig.suptitle("Nadir residual — sampling noise or physics?   "
                 "(re-measured from stored ledgers + a grid-free proxy, CPU only)",
                 fontsize=14.5, y=.985)
    fig.tight_layout(rect=(0, .035, 1, .962))
    fig.savefig(FIG, dpi=150)
    print("wrote", FIG)


figure()
