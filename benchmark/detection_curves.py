# -*- coding: utf-8 -*-
"""
detection_curves.py — 탐지 곡선: 원장 E 시계열 + 교정된 수신 잡음 → 거리별 탐지확률
====================================================================================

무엇을 재나
-----------
원장(outputs/elevation_sweep_md.npz)의 **15 m 판** 복소 슬로타임 열 E 를 신호로,
src/rx_noise.py 의 잡음 규약(N = k·T0·F·PRF, 풀캡처 v2)으로 만든 열잡음을 배경으로,
거리 R 을 로그 격자로 바꿔 가며 **네이만-피어슨 탐지확률 Pd(R)** 를 몬테카를로로 잰다.

팔(arm) 6개 — 엔진 2 × 앙각 3:
  · ours   = ours_r15_n8192                      (우리 커널, 15 m 구면파 조명)
  · sionna = sionna_p4000000000_r15_n8192_d1     (Sionna stock PathSolver, 부가물리 다 끔
                                                  = ch1 원장의 sionna_off 별칭, depth 1)
  · 앙각 −30°(주판) + 0°/−60°(보조) — f_tip 은 원장 행에서 읽는다.

절대 눈금·거리 스케일 (⭐한 번만 적용 — rx_noise 규약 그대로)
------------------------------------------------------------
커널 E 는 15 m 구면파 **조명**으로 위상 곡률만 담고 1/r 확산은 담지 않는다(rcs_sbr 규약).
그래서 E 는 σ(t) = (4π/λ²)|E(t)|² 로 **RCS 로만** 읽고, 절대 레벨은 문헌 앵커로 재보정한다:

    c_anchor  = σ_ref / ⟨σ_kernel(el=−30°)⟩          (엔진마다 하나 — 아래 주석)
    P_echo(t,R) = link_budget.echo_power_w(λ, σ(t)·c_anchor, R, R)   ∝ 1/R⁴
    x_sig(t,R)  = √P_echo(t,R) · E(t)/|E(t)|          (진폭 √W, 위상 보존)

1/R⁴ 은 **레이더 방정식에서만** 들어간다(이중적용 금지 — E 의 구면파는 위상 곡률뿐).
장 진폭으로 보면 amp(R)/amp(15 m) = (15/R)² 그대로다(스크립트가 수치로 자가검증).

⚠ 앵커를 rx_noise.rx_series 처럼 팔마다 걸지 않고 **엔진당 하나(주판 −30°)** 로 건 이유:
팔마다 걸면 여섯 팔의 평균 σ 가 전부 σ_ref 로 눌려 앙각·엔진의 레벨 차이가 지워진다.
주판에서 두 엔진을 같은 문헌 레벨로 맞추고(공정 비교), 보조 앙각의 상대 레벨은
엔진이 말한 그대로 둔다. anchor_scale·sigma_ref_from_literature 는 rx_noise 재사용.

검정 규약
---------
통계량(⭐오늘의 교훈 — DC(시계열 평균) 제거 후 계산, 두 잣대 모두):
    P = |FFT((x − mean(x))·hanning)|²,  블레이드 대역 = 0.35~1.0 × f_tip(el) (원장 band_track 정본)
  · 주(comb):  대역 안에서 f_flash 정수배 ±8 Hz 빗살 빈의 에너지 합
  · 보조(band): 대역 전체 에너지 합
문턱: **잡음 전용** 시행 N_CAL 개의 (1−Pfa) 분위수 — 교정 루틴은 E 를 인자로 받지도
않아 신호가 문턱에 샐 길이 없다. 별도 씨앗의 잡음 홀드아웃 N_VER 개로 Pfa 실측 검증.
문턱은 (앙각, 잣대)당 하나 — 잡음 분포는 거리·엔진과 무관하다(대역 마스크만 다름).

⛔GPU/솔버 없음 — sionna.rt·mitsuba import 없음. 저장된 원장·npz 만 읽는 CPU 분석.
⛔기존 파일 수정 없음 — 산출은 outputs/detection_curves.json +
outputs/figures/detection_pd_curves.png 뿐.

실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/detection_curves.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))          # = <root>/benchmark
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 재사용(재발명 금지): 잡음 N=kT0·F·PRF, σ=(4π/λ²)|E|², 문헌 앵커, 1/R⁴ 레이더 방정식
from rx_noise import (RxSpec, anchor_scale, noise_power_w,          # noqa: E402
                      sigma_kernel_m2, sigma_ref_from_literature)
from link_budget import LinkBudget, C0, lin2db                       # noqa: E402

# --------------------------------------------------------------------------- #
#  설정 — 전부 원장에 기록된다
# --------------------------------------------------------------------------- #
SEED = 20260815            # 마스터 씨앗(교정/홀드아웃/Pd 세 스트림으로 파생)
PFA = 1e-3                 # 목표 오경보율
N_MC = 240                 # 거리·팔당 몬테카를로 시행 수 (요구 ≥200)
N_CAL = 30000              # 문턱 교정용 잡음 전용 시행
N_VER = 30000              # Pfa 실측 검증용 잡음 홀드아웃(다른 씨앗)
HW_HZ = 8.0                # 빗살 반폭 [Hz] — 표준 레시피 ±8 Hz
BAND_LO = 0.35             # 블레이드 대역 하한 = 0.35·f_tip (원장 band_track 정본)
R_GRID = np.geomspace(100.0, 10000.0, 21)   # 로그 거리 격자 [m]
EIRP_DBM = 30.0            # ⭐선언값 — 소형 모노스태틱 센서급(rx_noise 데모와 동일)
BATCH = 1500               # 잡음 FFT 배치 크기(메모리 절충)

ENGINES = [
    # (짧은이름, npz/원장 engine 키, 설명)
    ("ours", "ours_r15_n8192", "our SBR+PO kernel, spherical illumination at 15 m"),
    ("sionna", "sionna_p4000000000_r15_n8192_d1",
     "Sionna stock PathSolver, extras all off (depth 1, spp 4e9) — ch1 alias sionna_off"),
]
ELS = [-30.0, 0.0, -60.0]   # 주판 −30° 먼저, 보조 0°/−60°
EL_MAIN = -30.0

LEDGER_JSON = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LEDGER_NPZ = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
OUT_JSON = os.path.join(ROOT, "outputs", "detection_curves.json")
OUT_PNG = os.path.join(ROOT, "outputs", "figures", "detection_pd_curves.png")


def _el_key(el: float) -> str:
    """npz 키 규약: 0 → 'el+0', −30 → 'el-30'."""
    return "el+0" if el == 0 else f"el{int(el):d}"


# --------------------------------------------------------------------------- #
#  원장 읽기
# --------------------------------------------------------------------------- #
def load_arms():
    """원장 JSON(수치 provenance) + npz(E 시계열) → 팔 6개. 전부 실행 시점에 읽는다."""
    led = json.load(open(LEDGER_JSON))
    meta = led["_meta"]
    fc, prf = float(meta["fc_hz"]), float(meta["prf_hz"])
    f_flash = float(meta["f_flash_hz"])   # ⚠ _meta 값은 기본 기체(matrice4e) 것 —
    drone = str(meta["drone"])            #   우리 팔 6개가 전부 matrice4e 라 그대로 유효
    z = np.load(LEDGER_NPZ)
    arms = []
    for short, eng, desc in ENGINES:
        for el in ELS:
            rows = [r for r in led["rows"]
                    if r.get("engine") == eng and float(r.get("el_deg")) == el]
            if not rows:
                raise KeyError(f"원장에 {eng}/el={el} 행이 없다")
            row = rows[-1]                              # 재실행 시 마지막 행이 정본
            if float(row.get("range_m", meta.get("range_m_legacy_default"))) != 15.0:
                raise ValueError(f"{eng}/el={el} 은 15 m 판이 아니다: {row}")
            key = f"{eng}/{_el_key(el)}"
            if key not in z.files:
                raise KeyError(f"{key} 가 npz 에 없다")
            E = np.asarray(z[key], complex)
            if E.size != int(row["n_poses"]):
                raise ValueError(f"{key}: npz 길이 {E.size} ≠ 원장 n_poses {row['n_poses']}")
            arms.append(dict(arm_id=f"{short}_el{int(el):+d}", engine_short=short,
                             engine=eng, engine_desc=desc, el_deg=el,
                             f_tip_hz=float(row["f_tip_hz"]), npz_key=key, E=E,
                             ledger_row=dict(n_poses=int(row["n_poses"]),
                                             seconds=float(row["seconds"]),
                                             range_m=float(row.get("range_m", 15.0)),
                                             max_depth=row.get("max_depth"),
                                             spp=row.get("spp"),
                                             physics=row.get("physics"))))
    ns = {a["E"].size for a in arms}
    if len(ns) != 1:
        raise ValueError(f"팔들의 시계열 길이가 다르다 {ns} — 문턱 공유 전제가 깨진다")
    return arms, dict(fc_hz=fc, prf_hz=prf, f_flash_hz=f_flash, drone=drone,
                      n=int(ns.pop()))


# --------------------------------------------------------------------------- #
#  통계량 — DC 제거 후 블레이드 대역 (주: 빗살 / 보조: 단순 대역)
# --------------------------------------------------------------------------- #
def make_masks(n: int, prf: float, f_tip: float, f_flash: float):
    """블레이드 대역·빗살 마스크. band = 0.35~1.0×f_tip(양측), comb = band ∩ (k·f_flash ±8 Hz)."""
    fr = np.fft.fftfreq(n, 1.0 / prf)
    band = (np.abs(fr) >= BAND_LO * f_tip) & (np.abs(fr) <= f_tip)
    kk = np.round(np.abs(fr) / f_flash)
    comb = band & (np.abs(np.abs(fr) - kk * f_flash) <= HW_HZ) & (kk >= 1)
    if not comb.any():
        raise ValueError(f"빗살 마스크가 비었다 (f_tip={f_tip})")
    return band, comb


def batch_stats(X: np.ndarray, w: np.ndarray, band, comb):
    """행렬 X(시행×n) → (T_comb, T_band). ⭐행마다 평균(DC) 제거 후 한나 창 FFT."""
    Xc = (X - X.mean(axis=1, keepdims=True)) * w
    P = np.abs(np.fft.fft(Xc, axis=1)) ** 2
    return P[:, comb].sum(axis=1), P[:, band].sum(axis=1)


def noise_batch(rng, m: int, n: int, N_w: float):
    """복소 백색가우스 n ~ CN(0, N) — 실·허 각각 분산 N/2 (rx_noise 규약)."""
    return ((rng.standard_normal((m, n)) + 1j * rng.standard_normal((m, n)))
            * np.sqrt(N_w / 2.0))


def noise_only_stats(rng, n_trial: int, n: int, N_w: float, w, masks_by_el):
    """잡음 **전용** 통계량 표본 — 신호 E 는 인자에도 없다(문턱 누설 원천 차단).

    masks_by_el: {el: (band, comb)} — 같은 잡음 배치를 앙각 마스크마다 재사용.
    반환 {el: {"comb": arr, "band": arr}}."""
    out = {el: {"comb": [], "band": []} for el in masks_by_el}
    done = 0
    while done < n_trial:
        m = min(BATCH, n_trial - done)
        Z = noise_batch(rng, m, n, N_w)
        Zc = (Z - Z.mean(axis=1, keepdims=True)) * w
        P = np.abs(np.fft.fft(Zc, axis=1)) ** 2
        for el, (band, comb) in masks_by_el.items():
            out[el]["comb"].append(P[:, comb].sum(axis=1))
            out[el]["band"].append(P[:, band].sum(axis=1))
        done += m
    return {el: {k: np.concatenate(v) for k, v in d.items()} for el, d in out.items()}


# --------------------------------------------------------------------------- #
#  본체
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    arms, meta = load_arms()
    fc, prf, f_flash, n = meta["fc_hz"], meta["prf_hz"], meta["f_flash_hz"], meta["n"]
    lam = C0 / fc
    w = np.hanning(n)

    # --- 수신 예산(선언값) + 잡음 전력 — rx_noise/link_budget 재사용 ---------- #
    spec = RxSpec(eirp_dbm=EIRP_DBM)
    N_w = noise_power_w(spec, prf)                      # N = k·T0·F·PRF
    lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                    noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)

    # --- 절대 눈금: 문헌 앵커(엔진당 하나, 주판 −30°) ------------------------- #
    ref = sigma_ref_from_literature(fc, meta["drone"])
    c_anchor = {}
    for short, eng, _ in ENGINES:
        E30 = next(a["E"] for a in arms
                   if a["engine_short"] == short and a["el_deg"] == EL_MAIN)
        c_anchor[short] = anchor_scale(E30, fc, ref["sigma_ref_dbsm"])

    # --- 마스크(앙각당) — f_tip 은 두 엔진이 같음(원장 행으로 확인) ------------ #
    ftip_by_el = {}
    for a in arms:
        ftip_by_el.setdefault(a["el_deg"], set()).add(a["f_tip_hz"])
    for el, s in ftip_by_el.items():
        if len(s) != 1:
            raise ValueError(f"el={el}: 엔진 간 f_tip 불일치 {s}")
    ftip_by_el = {el: s.pop() for el, s in ftip_by_el.items()}
    masks = {el: make_masks(n, prf, ft, f_flash) for el, ft in ftip_by_el.items()}

    # --- 문턱 교정(잡음 전용) + 홀드아웃 Pfa 실측 ----------------------------- #
    rng_cal = np.random.default_rng(SEED)
    rng_ver = np.random.default_rng(SEED + 1)
    rng_pd = np.random.default_rng(SEED + 2)
    cal = noise_only_stats(rng_cal, N_CAL, n, N_w, w, masks)
    ver = noise_only_stats(rng_ver, N_VER, n, N_w, w, masks)
    thr, pfa_meas, noise_stat = {}, {}, {}
    for el in masks:
        thr[el], pfa_meas[el], noise_stat[el] = {}, {}, {}
        for st in ("comb", "band"):
            t = float(np.quantile(cal[el][st], 1.0 - PFA))
            thr[el][st] = t
            pfa_meas[el][st] = float((ver[el][st] > t).mean())
            noise_stat[el][st] = dict(mean=float(cal[el][st].mean()),
                                      std=float(cal[el][st].std()))

    # --- Pd(R) 몬테카를로 ----------------------------------------------------- #
    for a in arms:
        E = a["E"]
        c = c_anchor[a["engine_short"]]["c_anchor"]
        sig_t = sigma_kernel_m2(E, fc) * c                      # σ(t)·c_anchor [m²]
        phase = np.where(np.abs(E) > 0, E / np.maximum(np.abs(E), 1e-300), 1.0)
        band, comb = masks[a["el_deg"]]
        Eac = E - E.mean()                                       # 레벨 기록은 DC 제거 후도
        a["sigma_mean_anchored_dbsm"] = float(lin2db(sig_t.mean()))
        a["sigma_ac_mean_anchored_dbsm"] = float(
            lin2db((sigma_kernel_m2(Eac, fc) * c).mean()))
        a["snr_sample_db_at_100m"] = float(
            lin2db(lb.echo_power_w(lam, sig_t, 100.0, 100.0).mean() / N_w))
        pd_comb, pd_band = [], []
        for R in R_GRID:
            P_echo = lb.echo_power_w(lam, sig_t, R, R)           # 1/R⁴ 은 여기 한 번뿐
            x0 = np.sqrt(P_echo) * phase
            X = x0[None, :] + noise_batch(rng_pd, N_MC, n, N_w)
            Tc, Tb = batch_stats(X, w, band, comb)
            pd_comb.append(float((Tc > thr[a["el_deg"]]["comb"]).mean()))
            pd_band.append(float((Tb > thr[a["el_deg"]]["band"]).mean()))
        a["pd_comb"], a["pd_band"] = pd_comb, pd_band

    # --- R50 (Pd=0.5 첫 하강 교차, 로그 보간) --------------------------------- #
    def r50(pd):
        pd = np.asarray(pd, float)
        if pd[0] < 0.5:
            return None                                          # 시작부터 못 봄
        below = pd < 0.5
        if not below.any():
            return None                                          # 격자 끝까지 Pd≥0.5
        i = int(np.argmax(below))
        x0, x1 = np.log10(R_GRID[i - 1]), np.log10(R_GRID[i])
        y0, y1 = pd[i - 1], pd[i]
        return float(10 ** (x0 + (y0 - 0.5) / max(y0 - y1, 1e-12) * (x1 - x0)))

    for a in arms:
        a["R50_m"] = dict(comb=r50(a["pd_comb"]), band=r50(a["pd_band"]))

    # --- 자가검사 ------------------------------------------------------------- #
    # (1) 거리 스케일 단일 적용: P(R)/P(15) == (15/R)⁴ (장 진폭 (15/R)² 와 동치)
    sig_probe = sigma_kernel_m2(arms[0]["E"], fc)[:8] + 1e-6
    ratio = (lb.echo_power_w(lam, sig_probe, 150.0, 150.0)
             / lb.echo_power_w(lam, sig_probe, 15.0, 15.0))
    scale_ok = bool(np.allclose(ratio, (15.0 / 150.0) ** 4, rtol=1e-9))
    # (2) Pfa 실측이 목표의 3σ 이항 범위 안(30000 시행, 기대 30±16.4 → 느슨히 0.4~2.5e-3)
    pfa_vals = [pfa_meas[el][st] for el in pfa_meas for st in ("comb", "band")]
    pfa_ok = bool(all(0.4e-3 <= v <= 2.5e-3 for v in pfa_vals))
    # (3) 곡선 끝점: 근거리 Pd≈1, 원거리 Pd≈Pfa 수준
    near_ok = bool(all(a["pd_comb"][0] >= 0.95 and a["pd_band"][0] >= 0.95 for a in arms))
    far_ok = bool(all(a["pd_comb"][-1] <= 0.10 for a in arms))
    # (4) R50 존재(격자 안에서 1→0 전이를 다 봤는가)
    r50_ok = bool(all(a["R50_m"]["comb"] is not None for a in arms))
    # (5) 물리 기대: 빗살(주) ≥ 단순 대역(보조) — 잡음 빈이 적어 문턱이 낮다
    comb_ge_band = sum(1 for a in arms
                       if a["R50_m"]["comb"] and a["R50_m"]["band"]
                       and a["R50_m"]["comb"] >= a["R50_m"]["band"])
    selftest = dict(
        scale_applied_once_ok=scale_ok,
        pfa_within_binomial_ok=pfa_ok,
        near_pd_ge_095_ok=near_ok,
        far_pd_le_010_ok=far_ok,
        r50_found_all_arms_ok=r50_ok,
        comb_ge_band_arms=f"{comb_ge_band}/{len(arms)}",
        threshold_no_signal_leak_ok=True,   # noise_only_stats 는 E 를 인자로도 안 받는다
        ok=bool(scale_ok and pfa_ok and near_ok and far_ok and r50_ok))

    # --- JSON 원장 ------------------------------------------------------------ #
    out = dict(
        _meta=dict(
            generator="benchmark/detection_curves.py",
            question_ko="원장 15 m 판 E + 교정된 열잡음으로 거리별 탐지확률 Pd(R)",
            inputs=[os.path.relpath(LEDGER_JSON, ROOT), os.path.relpath(LEDGER_NPZ, ROOT)],
            gpu_ko="GPU/솔버 호출 없음 — 저장된 원장만 읽은 CPU 몬테카를로",
            convention=dict(
                scale_ko="E 는 σ=(4π/λ²)|E|² 로만 읽고 문헌 앵커로 재보정, 1/R⁴ 은 "
                         "link_budget.echo_power_w 한 곳에서만(장 진폭 (15/R)² 와 동치, "
                         "이중적용 없음 — selftest.scale_applied_once_ok)",
                anchor_ko="c_anchor = σ_ref/⟨σ_kernel(el−30°)⟩ 를 엔진당 하나 — 팔마다 "
                          "걸면 앙각·엔진 레벨 차이가 지워져서 주판에서만 맞춘다. "
                          "⟨σ⟩ 는 앵커 규약상 DC 포함(문헌 RCS 가 전체 RCS), 탐지 "
                          "통계량은 DC 제거 후(오늘의 교훈) — 두 층위를 섞지 않는다",
                noise_ko="N = k·T0·F·PRF (rx_noise 풀캡처 v2), CN(0,N) 백색",
                statistic_ko="DC 제거 후 한나 창 FFT, 블레이드 대역 0.35~1.0×f_tip(el); "
                             "주=f_flash 정수배 ±8 Hz 빗살 에너지, 보조=대역 전체 에너지",
                threshold_ko="잡음 전용 30000 시행의 (1−Pfa) 분위수, (앙각,잣대)당 하나; "
                             "교정 루틴은 신호 E 를 인자로도 받지 않는다",
                detection_ko="Pd = 시행 240 중 통계량>문턱 비율, 씨앗 고정"),
            fc_hz=fc, prf_hz=prf, f_flash_hz=f_flash, drone=meta["drone"], n_slow=n,
            pfa_target=PFA, n_mc=N_MC, n_cal=N_CAL, n_ver=N_VER, seed=SEED,
            hw_hz=HW_HZ, band_lo_frac=BAND_LO,
            rx_spec=dict(asdict(spec),
                         note_ko="EIRP 30 dBm 은 선언값(소형 모노스태틱 센서급, "
                                 "rx_noise 데모와 동일)"),
            noise_power_w=N_w,
            sigma_anchor=dict(sigma_ref_dbsm=ref["sigma_ref_dbsm"], **ref["provenance"]),
            c_anchor={k: v for k, v in c_anchor.items()},
            f_tip_hz_by_el={f"{el:+.0f}": v for el, v in ftip_by_el.items()},
            R_grid_m=[round(float(r), 1) for r in R_GRID],
            elapsed_s=None),
        thresholds={f"{el:+.0f}": thr[el] for el in thr},
        noise_stat={f"{el:+.0f}": noise_stat[el] for el in noise_stat},
        pfa_measured={f"{el:+.0f}": pfa_meas[el] for el in pfa_meas},
        arms=[{k: v for k, v in a.items() if k != "E"} for a in arms],
        selftest=selftest)
    for a in out["arms"]:                       # rows 표 형태도 함께(읽기 편의)
        a["rows"] = [dict(R_m=round(float(R), 1), pd_comb=a["pd_comb"][i],
                          pd_band=a["pd_band"][i]) for i, R in enumerate(R_GRID)]
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(out, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {OUT_JSON}")

    make_figure(out)
    print(json.dumps(dict(selftest=selftest,
                          R50_comb={a['arm_id']: a['R50_m']['comb'] for a in out['arms']}),
                     ensure_ascii=False))
    return out


# --------------------------------------------------------------------------- #
#  그림 — Pd vs R, 팔별 색 (영어, 겹침 금지)
# --------------------------------------------------------------------------- #
# 검증된 기성 카테고리 팔레트(dataviz 스킬 reference 팔레트, 인접쌍 CVD 검증 완료 —
# node 검증기가 이 환경에 없어 문서화된 검증값을 그대로 쓴다). 팔=색 고정 배정,
# 엔진=선 스타일(실선/파선) 이중 부호화.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
SURFACE, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"


def make_figure(out: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    R = np.asarray(out["_meta"]["R_grid_m"], float)
    arms = out["arms"]
    order = [f"{s}_el{int(e):+d}" for s in ("ours", "sionna") for e in (-30, 0, -60)]
    arms = sorted(arms, key=lambda a: order.index(a["arm_id"]))
    labels = {a["arm_id"]:
              f"{'ours' if a['engine_short'] == 'ours' else 'Sionna stock'} "
              f"el {int(a['el_deg']):+d}°"
              + (" (main)" if a["el_deg"] == EL_MAIN else "") for a in arms}

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.1), sharey=True,
                             facecolor=SURFACE)
    panels = [("pd_comb", "Primary statistic: flash-comb energy in blade band"),
              ("pd_band", "Secondary statistic: plain blade-band energy")]
    for ax, (key, title) in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        for i, a in enumerate(arms):
            ls = "-" if a["engine_short"] == "ours" else "--"
            ax.plot(R, a[key], color=PALETTE[i], ls=ls, lw=2.0, marker="o", ms=4,
                    label=labels[a["arm_id"]])
        ax.axhline(0.5, color=INK2, lw=1.0, ls=":")
        ax.set_xscale("log")
        ax.set_xlim(R[0], R[-1])
        ax.set_ylim(-0.03, 1.05)
        ax.set_xlabel("Range R [m]  (log scale)", color=INK)
        ax.set_title(title, fontsize=11, color=INK)
        ax.grid(True, which="both", color="0.92", lw=0.7)
        ax.set_axisbelow(True)
        ax.tick_params(colors=INK2)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(INK2)
    axes[0].set_ylabel("Detection probability Pd", color=INK)
    axes[0].text(R[0] * 1.12, 0.53, "Pd = 0.5 (defines R50)", fontsize=8.5,
                 color=INK2, va="bottom")
    axes[0].legend(loc="lower left", fontsize=8.5, framealpha=0.95,
                   edgecolor="0.85", title="engine / elevation", title_fontsize=8.5)
    m = out["_meta"]
    fig.suptitle("Drone rotor detection probability vs range "
                 f"(Pfa = {m['pfa_target']:g}, {m['n_mc']} trials per point)",
                 fontsize=13, color=INK)
    fig.text(0.5, 0.005,
             "Signal: 15 m ledger slow-time series (matrice4e), literature-anchored "
             f"σ, monostatic 1/R⁴ budget · EIRP {m['rx_spec']['eirp_dbm']:.0f} dBm "
             f"(declared) · NF {m['rx_spec']['nf_db']:.0f} dB · PRF "
             f"{m['prf_hz'] / 1e3:.1f} kHz · N = kT₀F·PRF · DC removed "
             "before both statistics", ha="center", fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"  ✅ {OUT_PNG}")


if __name__ == "__main__":
    main()
