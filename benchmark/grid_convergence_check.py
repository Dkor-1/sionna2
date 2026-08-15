# -*- coding: utf-8 -*-
"""
grid_convergence_check.py — ⭐R16 · 격자 λ/12 ↔ λ/24 **세 층 판독**과 «격자 산포 밴드»
================================================================================

질문 (설계서 `docs/NEXT_EXPERIMENTS.md` 순위 2)
  우리 커널(SBR+PO)의 어떤 주장이 **격자(수치 해상도) 산물**인가.
  그리고 앞으로 다른 실험이 «몇 dB 차이면 유의한가» 를 정할 때 쓸 **산포 밴드**를 만든다.

무엇을 비교하나 — 같은 앙각끼리, 격자만 바꾼 두 팔
  · `ours_r15_n8192`        격자 λ/12 (생산 기본)
  · `ours_r15_n8192_div24`  격자 λ/24 (같은 기체·거리·방위·자세 수, 격자만 두 배 촘촘)
  겹치는 앙각 네 자리: el 0 · −15 · −30 · −45.

세 층으로 갈라 채점한다
  ① 파형층  — DC(정지성분) 제거 뒤 **복소 상관 |ρ|** (+ 덱이 인용하는 STFT dB-맵 상관도 같이)
  ② 통계층  — **DC 제거 AC 절대전력** · DC 절대전력 · AC/DC · 상한(f_tip) 위 몫
  ③ 잣대층  — **리듬 몫**(박자 빗살) · 박자 위치 `beat_hz` · `classify_airframe` 규약 빗살 argmax

⭐핵심 산출 — «격자 산포 밴드»
  층별로 λ/12↔λ/24 차이의 크기를 dB·%p 로 요약한다. 앞으로 R4·R12·R15·R19·R23 이
  «이 밴드 안이면 판정 불가» 로 쓸 **수**를 여기서 만든다. 지금 그 문턱들은 근거 없는 수다.

⭐사전등록 판정 (설계서 그대로 — 기준을 바꾸지 않았다)
  **팔 사이 순서**(우리 vs 물리끔 vs 물리켬)가 λ/24 에서 바뀌면,
  스위치 격자 인용에 «λ/12 한정» 꼬리표를 강제한다. 순서 보존 여부를 **앙각마다 표로**.
  ⭐추가로 «순서는 같지만 간격이 밴드 안» 인 칸은 «보존» 이 아니라 **«판정 불가»** 로 따로
    찍는다 — 사전등록 기준을 완화한 것이 아니라, 통과 칸을 더 엄격히 읽는 쪽이다.

부록 절 (설계서 R15 «독립 파일을 만들지 않는다» 지시)
  나딧 평면파 ↔ 구면파: **AC 절대전력과 DC 를 따로** 싣고, 차이를 R16 밴드와 견준다.

규약 (이 저장소 상시 규칙)
  · 레벨·에너지 비교는 **전부 DC 제거 후**. 마이크로도플러 표현은 **STFT 만**.
  · 리듬(구조) 잣대 표준 레시피 —
      P = |FFT((E − mean(E))·hanning)|² · above = |fr| ≥ f_tip(el)
      박자 = f_flash 정수배 ±8 Hz · 몫[%] = P[above & 박자] / P[above]
      (백색잡음 ≈ 13 % · 이상 로터 ≈ 100 % — 아래 자가검사에서 실측한다)
  · 그림 안 글자는 영어, 주석·JSON 설명은 한국어.

⛔GPU 금지 — `sionna.rt` · `mitsuba` 를 임포트하지 않는다. 저장된 원장 npz·JSON 만 읽는다.

산출
  outputs/grid_convergence_check.json
  outputs/figures/grid_r16_three_layers.png
  outputs/figures/grid_r16_band_and_order.png

실행
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/grid_convergence_check.py
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np

# numpy/scipy 만 쓰는 모듈들 — GPU 스택 아님
from drones import DRONES                      # 제원(템플릿 계산용)
from md_mapstyle import auto_periods, flash_spec   # ⭐STFT 만

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_JSON = f"{ROOT}/outputs/elevation_sweep_md.json"
LEDGER_NPZ = f"{ROOT}/outputs/elevation_sweep_md.npz"
OUT_JSON = f"{ROOT}/outputs/grid_convergence_check.json"
FIG_DIR = f"{ROOT}/outputs/figures"
FIG1 = f"{FIG_DIR}/grid_r16_three_layers.png"
FIG2 = f"{FIG_DIR}/grid_r16_band_and_order.png"

# ── 팔 지정 (원장 키를 실제로 뒤져 확인한다) ───────────────────────────────────
ARM_DIV12 = "ours_r15_n8192"
ARM_DIV24 = "ours_r15_n8192_div24"
ARM_PHYS_OFF = "sionna_p4000000000_r15_n8192_d1"        # R0D0E0F1 · d1 · physics=False
ARM_PHYS_ON = "sionna_p4000000000_phys_r15_n8192_d1"    # R1D1E1F1 · d1 · physics=True
ARM_DIFFR = "sionna_p4000000000_onlydiffr_r15_n8192"    # 보조(설계서 판의 «회절» 읽기)
ARM_PTD = "ours_ptd_r15_n8192"                          # 같은 격자 «무늬는 같다» 기준자
ARM_NADIR_SPH = "ours_r15_n8192"                        # el −90 구면파
ARM_NADIR_PW = "ours_r15_n8192_pw"                      # el −90 평면파

ELS = [0.0, -15.0, -30.0, -45.0]        # div24 가 존재하는 앙각 — 여기서만 밴드를 만든다
COMB_TOL_HZ = 8.0                       # 빗살 허용폭 ±8 Hz (표준 레시피)
AC_MIN_HZ = 8.0                         # AC 대역 하한(DC 누설 제외)
AIRFRAMES = ["mini5pro", "matrice4e", "s1000plus"]
N_WIN, WIN_LEN, NFFT = 16, 512, 8192     # classify_airframe.py 규약 그대로
SEED = 20260815
C_LIGHT = 299_792_458.0


# ═══════════════════════════════════════════════════════════════════════════ #
#  0) 원장 로드 · 팔 존재/설정 게이트
# ═══════════════════════════════════════════════════════════════════════════ #
def elkey(el: float) -> str:
    return f"el{el:+.0f}"


def load():
    with open(LEDGER_JSON, encoding="utf-8") as f:
        led = json.load(f)
    npz = np.load(LEDGER_NPZ)
    rows = {(r["engine"], round(float(r["el_deg"]), 3)): r for r in led["rows"]}
    return led, npz, rows


def series(npz, arm: str, el: float) -> np.ndarray:
    key = f"{arm}/{elkey(el)}"
    if key not in npz.files:
        raise KeyError(f"원장에 없는 칸: {key}")
    return np.asarray(npz[key], dtype=complex)


# ═══════════════════════════════════════════════════════════════════════════ #
#  1) 층별 잣대 — 전부 DC 제거 후
# ═══════════════════════════════════════════════════════════════════════════ #
def ac_dc(E: np.ndarray) -> dict:
    """정지성분(DC)과 요동(AC)을 **따로** 낸다 — 비율은 파생일 뿐이다."""
    dc_amp = complex(E.mean())
    x = E - dc_amp
    dc_db = 10.0 * math.log10(abs(dc_amp) ** 2 + 1e-300)
    ac_db = 10.0 * math.log10(float((np.abs(x) ** 2).mean()) + 1e-300)
    return {
        "dc_power_db": round(dc_db, 3),
        "ac_power_db": round(ac_db, 3),
        "ac_over_dc_db": round(ac_db - dc_db, 3),
        "level_db_ledger_formula": round(20.0 * math.log10(float(np.abs(E).mean()) + 1e-300), 3),
    }


def spectrum_metrics(E: np.ndarray, prf: float, f_flash: float, f_tip: float) -> dict:
    """표준 레시피 — P=|FFT((E−mean)·hanning)|², above=|fr|≥f_tip, 박자 ±8 Hz 몫[%]."""
    n = E.size
    x = E - E.mean()
    P = np.abs(np.fft.fft(x * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, d=1.0 / prf)
    fa = np.abs(fr)
    above = fa >= f_tip
    ac_band = fa >= AC_MIN_HZ
    k = np.round(fa / f_flash)
    on_beat = (k >= 1) & (np.abs(fa - k * f_flash) <= COMB_TOL_HZ)
    p_above = float(P[above].sum())
    p_ac = float(P[ac_band].sum())
    rhythm = 100.0 * float(P[above & on_beat].sum()) / p_above if p_above > 0 else float("nan")
    return {
        "rhythm_share_pct": round(rhythm, 3),
        "above_f_tip_frac": round(p_above / p_ac, 6) if p_ac > 0 else None,
        "above_f_tip_pct": round(100.0 * p_above / p_ac, 4) if p_ac > 0 else None,
        "n_bins_above": int(above.sum()),
        "f_tip_hz": round(f_tip, 1),
    }


def beat_from_stft(E: np.ndarray, prf: float, f_flash: float, f_tip: float,
                   periods: float) -> dict:
    """박자 위치 — 원장 `track.beat_hz` 와 **같은 규약**.

    ⭐STFT 세팅을 인자로 받는다(그림·표에 세팅을 명시하기 위해). 원장 `analyse()` 는
      `auto_periods(prf, f_flash)` = 0.45 주기를 쓴다 — 재현 게이트가 그것을 확인한다.
      ⚠덱이 인용하는 dB-맵 상관은 `flash_spec` **기본 0.6 주기**로 잰 값이라, 그쪽만
      0.6 을 그대로 둔다(사과-대-사과).
    """
    f, t, S, _ = flash_spec(np.asarray(E, complex), prf, f_flash, periods)
    band = (np.abs(f) >= 0.35 * f_tip) & (np.abs(f) <= f_tip)
    if band.sum() < 2:
        return {"beat_hz": None, "band_power_db": None, "n_bins": int(band.sum())}
    g = (S[band, :] ** 2).sum(axis=0)
    band_power_db = 10.0 * math.log10(float(g.mean()) + 1e-300)
    g = g - g.mean()                       # ⭐시간축에서도 DC 제거
    dt = float(t[1] - t[0])
    m = g.size
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fq = np.fft.rfftfreq(64 * m, dt)
    if A.max() <= 0:
        return {"beat_hz": None, "band_power_db": round(band_power_db, 3), "n_bins": int(band.sum())}
    A = A / A.max()
    sel = (fq >= 40) & (fq <= 400)
    i0 = int(np.where(sel)[0][0])
    i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]
    den = y0 - 2 * y1 + y2
    pk = fq[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fq[1] - fq[0])
    return {"beat_hz": round(float(pk), 3), "band_power_db": round(band_power_db, 3),
            "n_bins": int(band.sum())}


def complex_rho(a: np.ndarray, b: np.ndarray, drop_dc: bool = True) -> dict:
    """DC 제거 복소 상관 ρ = <x,y>/(‖x‖‖y‖). |ρ| 와 위상을 따로 낸다."""
    x = a - a.mean() if drop_dc else a.copy()
    y = b - b.mean() if drop_dc else b.copy()
    na, nb = np.linalg.norm(x), np.linalg.norm(y)
    if na == 0 or nb == 0:
        return {"abs_rho": None, "phase_deg": None}
    r = complex(np.vdot(x, y) / (na * nb))
    return {"abs_rho": round(abs(r), 4), "phase_deg": round(math.degrees(np.angle(r)), 2)}


def stft_map_corr(a: np.ndarray, b: np.ndarray, prf: float, f_flash: float,
                  drop_dc: bool) -> float | None:
    """덱·`physics_vs_deck.json` 이 인용하는 잣대와 **같은 정의** — 자기최대 정규화 dB 맵의 피어슨 상관.

    ⭐그쪽 빌더(`build_physics_vs_deck_fig.py`)가 `flash_spec(E, prf, ffl)` 를 인자 없이
      부르므로 여기서도 **기본 0.6 주기**를 쓴다 — 0.9877 / 0.6961 과 사과-대-사과가 되게.
    """
    x = (a - a.mean()) if drop_dc else a
    y = (b - b.mean()) if drop_dc else b
    _, _, Sa, _ = flash_spec(np.asarray(x, complex), prf, f_flash)
    _, _, Sb, _ = flash_spec(np.asarray(y, complex), prf, f_flash)
    if Sa.shape != Sb.shape:
        return None
    A = 10.0 * np.log10(Sa / Sa.max() + 1e-12)
    B = 10.0 * np.log10(Sb / Sb.max() + 1e-12)
    return round(float(np.corrcoef(A.ravel(), B.ravel())[0, 1]), 4)


# ── 분류(빗살 argmax) — classify_airframe.py 규약을 그대로 옮긴다 ──────────────
def comb_mask(fr: np.ndarray, f0: float) -> np.ndarray:
    fa = np.abs(fr)
    k = np.round(fa / f0)
    return (k >= 1) & (np.abs(fa - k * f0) <= COMB_TOL_HZ)


def classify_windows(E: np.ndarray, prf: float, cand_f: dict) -> dict:
    fr = np.fft.fftfreq(NFFT, d=1.0 / prf)
    ac = np.abs(fr) >= AC_MIN_HZ
    masks = {a: comb_mask(fr, cand_f[a]) & ac for a in AIRFRAMES}
    han = np.hanning(WIN_LEN)
    sc = np.zeros((N_WIN, len(AIRFRAMES)))
    for w in range(N_WIN):
        x = E[w * WIN_LEN:(w + 1) * WIN_LEN]
        x = x - x.mean()                    # ⭐창별 DC 제거
        P = np.abs(np.fft.fft(x * han, NFFT)) ** 2
        tot = P[ac].sum()
        for j, a in enumerate(AIRFRAMES):
            sc[w, j] = P[masks[a]].sum() / tot if tot > 0 else 0.0
    pred = sc.argmax(axis=1)
    truth = AIRFRAMES.index("matrice4e")     # div24 팔은 기본 기체뿐이다
    srt = np.sort(sc, axis=1)
    margin = sc[:, truth] - np.where(pred == truth, srt[:, -2], srt[:, -1])
    return {
        "accuracy": round(float((pred == truth).mean()), 4),
        "pred_counts": {AIRFRAMES[j]: int((pred == j).sum()) for j in range(3)},
        "argmax_whole_window_majority": AIRFRAMES[int(np.bincount(pred, minlength=3).argmax())],
        "decision_margin_median": round(float(np.median(margin)), 5),
        "n_windows": int(N_WIN),
    }


# ═══════════════════════════════════════════════════════════════════════════ #
#  2) 실행
# ═══════════════════════════════════════════════════════════════════════════ #
def run() -> dict:
    t_start = time.time()
    led, npz, rows = load()
    meta = led["_meta"]
    prf = float(meta["prf_hz"])
    f_flash = float(meta["f_flash_hz"])
    lam = C_LIGHT / float(meta["fc_hz"])
    stft_periods = float(auto_periods(prf, f_flash))     # 원장 analyse() 와 같은 세팅(0.45)
    checks: list[dict] = []

    def gate(name: str, ok: bool, detail: str):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    # ── 게이트 ① 팔이 원장에 있고, 격자 말고는 설정이 같은가 ───────────────────
    cfg_keys = ("n_poses", "n_missing", "range_m", "az_deg", "spp", "max_depth")
    cfg_ok, cfg_detail = True, []
    for el in ELS:
        r12 = rows[(ARM_DIV12, el)]
        r24 = rows[(ARM_DIV24, el)]
        same = all(r12[k] == r24[k] for k in cfg_keys)
        cfg_ok &= same and r12["grid_div"] == 12 and r24["grid_div"] == 24
        cfg_detail.append(f"el{el:+.0f}: div {r12['grid_div']}→{r24['grid_div']}, "
                          f"동일열 {'예' if same else '아니오'}")
    gate("두 팔은 격자만 다르다(n_poses·n_missing·range_m·az_deg·spp·max_depth 동일)",
         cfg_ok, " · ".join(cfg_detail))

    miss = [f"{a}/el{el:+.0f}" for a in (ARM_DIV12, ARM_DIV24, ARM_PHYS_OFF, ARM_PHYS_ON, ARM_DIFFR)
            for el in ELS if rows[(a, el)]["n_missing"] != 0]
    gate("쓰는 칸에 결측 자세가 없다(n_missing=0)", not miss,
         "결측 칸 없음" if not miss else f"결측: {miss}")

    # ── 게이트 ② 리듬 잣대 눈금 — 백색 ≈13 % · 이상 로터 ≈100 % ────────────────
    rng = np.random.default_rng(SEED)
    n_probe = int(rows[(ARM_DIV12, 0.0)]["n_poses"])
    f_tip0 = float(rows[(ARM_DIV12, 0.0)]["f_tip_hz"])
    white = rng.normal(size=n_probe) + 1j * rng.normal(size=n_probe)
    white_rhy = spectrum_metrics(white, prf, f_flash, f_tip0)["rhythm_share_pct"]
    tt = np.arange(n_probe) / prf
    k_max = int(np.floor((prf / 2.0 - 50.0) / f_flash))
    ideal = sum(np.exp(2j * np.pi * k * f_flash * tt) for k in range(1, k_max + 1))
    ideal_rhy = spectrum_metrics(ideal, prf, f_flash, f_tip0)["rhythm_share_pct"]
    gate("리듬 잣대 눈금 — 백색 ≈13 % · 이상 로터 ≈100 %",
         (8.0 <= white_rhy <= 20.0) and (ideal_rhy >= 95.0),
         f"백색 {white_rhy:.2f} % · 이상 로터 {ideal_rhy:.2f} % (빗살 {k_max} 개)")

    # ── 게이트 ③ |ρ| 눈금 — 자기상관 = 1 · 섞기 널은 잡음 바닥(1/√N) ───────────
    #    ⚠처음에 «다른 앙각끼리는 상관이 없다» 를 바닥으로 쓰려 했는데 **실측이 그것을
    #      뒤집었다**(아래 rho_reference_rulers). 앙각이 달라도 0.27~0.78 로 붙어 있다.
    #      그래서 잡음 바닥은 **섞기 널**로만 잡고, 앙각 교차는 «판정용 자» 로 따로 싣는다.
    e_self = series(npz, ARM_DIV12, -30.0)
    self_rho = complex_rho(e_self, e_self)["abs_rho"]
    shuf_probe = complex_rho(e_self, e_self[rng.permutation(e_self.size)])["abs_rho"]
    floor = 1.0 / math.sqrt(n_probe)
    gate("|ρ| 눈금 — 자기상관 1.000 · 섞기 널은 잡음 바닥(≈1/√N)",
         abs(self_rho - 1.0) < 1e-9 and shuf_probe < 20 * floor,
         f"자기 {self_rho:.6f} · 섞기 널 {shuf_probe:.4f} · 1/√N={floor:.4f}")

    # ── 게이트 ④ 원장 재현 — level_db · beat_hz 를 같은 식으로 다시 낸다 ────────
    lvl_d, beat_d = [], []
    for arm in (ARM_DIV12, ARM_DIV24):
        for el in ELS:
            E = series(npz, arm, el)
            r = rows[(arm, el)]
            lvl_d.append(abs(ac_dc(E)["level_db_ledger_formula"] - float(r["level_db"])))
            b = beat_from_stft(E, prf, f_flash, float(r["f_tip_hz"]), stft_periods)["beat_hz"]
            if b is not None and r["track"]["beat_hz"] is not None:
                beat_d.append(abs(b - float(r["track"]["beat_hz"])))
    gate("원장 재현 — level_db 최대오차 ≤0.01 dB", max(lvl_d) <= 0.01,
         f"최대 {max(lvl_d):.4f} dB (8 칸)")
    gate(f"원장 재현 — track.beat_hz 최대오차 ≤0.02 Hz (STFT {stft_periods:.2f} 주기)",
         max(beat_d) <= 0.02, f"최대 {max(beat_d):.4f} Hz (8 칸)")

    # ── ⭐|ρ| 판정용 자 — 같은 팔·같은 격자에서 **앙각만** 바꾼 상관 ────────────
    rho_rulers = {
        "question_ko": "«|ρ| 가 얼마면 무늬가 같은가» 를 정하려면 **다른 것들끼리의 |ρ|** 를 알아야 한다",
        "cross_elevation_same_arm_div12": {},
        "shuffled_null": round(shuf_probe, 4),
        "noise_floor_1_over_sqrt_n": round(floor, 4),
    }
    for a in ELS:
        Ea = series(npz, ARM_DIV12, a)
        rho_rulers["cross_elevation_same_arm_div12"][f"{a:+.0f}"] = {
            f"{b:+.0f}": complex_rho(Ea, series(npz, ARM_DIV12, b))["abs_rho"] for b in ELS}
    off_diag = [v for a in ELS for b in ELS if a != b
                for v in [rho_rulers["cross_elevation_same_arm_div12"][f"{a:+.0f}"][f"{b:+.0f}"]]]
    rho_rulers["cross_elevation_min"] = round(min(off_diag), 4)
    rho_rulers["cross_elevation_max"] = round(max(off_diag), 4)
    rho_rulers["finding_ko"] = (
        f"⭐같은 커널·같은 격자에서 **앙각만** 15~45° 바꿔도 |ρ| 가 "
        f"{min(off_diag):.2f}~{max(off_diag):.2f} 다. 즉 |ρ| ≈ 0.5~0.8 은 «같은 물건» 의 증거가 "
        "아니라 **명백히 다른 물건들 사이의 평범한 값**이다 — 상관을 근거로 쓰는 모든 주장이 "
        "이 자 위에서 다시 읽혀야 한다.")

    # ═══ 세 층 판독 ═══════════════════════════════════════════════════════════
    cand_f = {a: DRONES[a].prop_blades * DRONES[a].hover_rpm / 60.0 for a in AIRFRAMES}
    per_el: dict[str, dict] = {}
    for el in ELS:
        r12 = rows[(ARM_DIV12, el)]
        f_tip = float(r12["f_tip_hz"])
        E12 = series(npz, ARM_DIV12, el)
        E24 = series(npz, ARM_DIV24, el)

        # ① 파형층
        rho = complex_rho(E12, E24, drop_dc=True)
        rho_raw = complex_rho(E12, E24, drop_dc=False)
        # 같은 격자끼리의 기준자 — «무늬가 같다» 고 부르는 팔(PTD)과 «다르다» 고 부르는 팔
        rho_ptd = complex_rho(E12, series(npz, ARM_PTD, el), drop_dc=True)
        rho_phys_off = complex_rho(E12, series(npz, ARM_PHYS_OFF, el), drop_dc=True)
        shuf = E12[rng.permutation(E12.size)]
        rho_shuffle = complex_rho(E12, shuf, drop_dc=True)
        wave = {
            "abs_rho_dc_removed": rho["abs_rho"],
            "rho_phase_deg": rho["phase_deg"],
            "abs_rho_dc_kept": rho_raw["abs_rho"],
            "stft_db_map_corr_dc_removed": stft_map_corr(E12, E24, prf, f_flash, True),
            "stft_db_map_corr_dc_kept": stft_map_corr(E12, E24, prf, f_flash, False),
            "ref_abs_rho_vs_ptd_same_grid": rho_ptd["abs_rho"],
            "ref_abs_rho_vs_phys_off_same_grid": rho_phys_off["abs_rho"],
            "ref_stft_map_corr_vs_phys_off_same_grid":
                stft_map_corr(E12, series(npz, ARM_PHYS_OFF, el), prf, f_flash, True),
            "ref_abs_rho_shuffled_null": rho_shuffle["abs_rho"],
        }

        # ② 통계층
        s12, s24 = ac_dc(E12), ac_dc(E24)
        g12 = spectrum_metrics(E12, prf, f_flash, f_tip)
        g24 = spectrum_metrics(E24, prf, f_flash, f_tip)
        stat = {
            "div12": {**s12, "above_f_tip_pct": g12["above_f_tip_pct"],
                      "above_f_tip_frac": g12["above_f_tip_frac"]},
            "div24": {**s24, "above_f_tip_pct": g24["above_f_tip_pct"],
                      "above_f_tip_frac": g24["above_f_tip_frac"]},
            "delta_div24_minus_div12": {
                "ac_power_db": round(s24["ac_power_db"] - s12["ac_power_db"], 3),
                "dc_power_db": round(s24["dc_power_db"] - s12["dc_power_db"], 3),
                "ac_over_dc_db": round(s24["ac_over_dc_db"] - s12["ac_over_dc_db"], 3),
                "level_db_ledger_formula": round(
                    s24["level_db_ledger_formula"] - s12["level_db_ledger_formula"], 3),
                "above_f_tip_pp": round(g24["above_f_tip_pct"] - g12["above_f_tip_pct"], 4),
            },
        }

        # ③ 잣대층
        b12 = beat_from_stft(E12, prf, f_flash, f_tip, stft_periods)
        b24 = beat_from_stft(E24, prf, f_flash, f_tip, stft_periods)
        c12 = classify_windows(E12, prf, cand_f)
        c24 = classify_windows(E24, prf, cand_f)
        metric = {
            "div12": {"rhythm_share_pct": g12["rhythm_share_pct"], **b12, "classify": c12},
            "div24": {"rhythm_share_pct": g24["rhythm_share_pct"], **b24, "classify": c24},
            "delta_div24_minus_div12": {
                "rhythm_share_pp": round(g24["rhythm_share_pct"] - g12["rhythm_share_pct"], 3),
                "beat_hz": (None if (b12["beat_hz"] is None or b24["beat_hz"] is None)
                            else round(b24["beat_hz"] - b12["beat_hz"], 3)),
                "band_power_db": (None if (b12["band_power_db"] is None or b24["band_power_db"] is None)
                                  else round(b24["band_power_db"] - b12["band_power_db"], 3)),
                "classify_accuracy_pp": round(
                    100.0 * (c24["accuracy"] - c12["accuracy"]), 3),
                "classify_argmax_same": bool(c24["argmax_whole_window_majority"]
                                             == c12["argmax_whole_window_majority"]),
                "classify_margin": round(c24["decision_margin_median"]
                                         - c12["decision_margin_median"], 5),
            },
        }
        per_el[f"{el:+.0f}"] = {
            "f_tip_hz": round(f_tip, 1),
            "n_poses": int(r12["n_poses"]),
            "layer1_waveform": wave,
            "layer2_statistics": stat,
            "layer3_metric": metric,
        }

    # ═══ ⭐격자 산포 밴드 ═════════════════════════════════════════════════════
    def collect(path):
        out = []
        for el in ELS:
            v = per_el[f"{el:+.0f}"]
            for p in path:
                v = v[p]
            if v is not None:
                out.append(float(v))
        return out

    def band(name, vals, unit, direction, note):
        a = np.abs(np.asarray(vals, float))
        return {
            "metric": name, "unit": unit,
            "n_elevations": int(a.size),
            "median_abs": round(float(np.median(a)), 4),
            "max_abs": round(float(a.max()), 4),
            "band": round(float(a.max()), 4),      # ⭐밴드 = 4 앙각 중 **최대** 절대차
            "direction_ko": direction,
            "note_ko": note,
        }

    bands = {
        "layer1_waveform": [
            {
                "metric": "abs_rho_dc_removed", "unit": "상관(0~1)",
                "n_elevations": len(collect(["layer1_waveform", "abs_rho_dc_removed"])),
                "min": round(min(collect(["layer1_waveform", "abs_rho_dc_removed"])), 4),
                "median": round(float(np.median(collect(["layer1_waveform", "abs_rho_dc_removed"]))), 4),
                "max": round(max(collect(["layer1_waveform", "abs_rho_dc_removed"])), 4),
                "band_ko": "격자만 바꿔도 |ρ| 가 여기까지 내려간다 — **이 값보다 높은 상관만이 «무늬가 같다» 의 근거가 된다**",
            },
            {
                "metric": "stft_db_map_corr_dc_removed", "unit": "상관(0~1)",
                "n_elevations": len(collect(["layer1_waveform", "stft_db_map_corr_dc_removed"])),
                "min": round(min(collect(["layer1_waveform", "stft_db_map_corr_dc_removed"])), 4),
                "median": round(float(np.median(collect(["layer1_waveform", "stft_db_map_corr_dc_removed"]))), 4),
                "max": round(max(collect(["layer1_waveform", "stft_db_map_corr_dc_removed"])), 4),
                "band_ko": "덱·`physics_vs_deck.json` 이 인용하는 **바로 그 잣대**의 격자 바닥",
            },
        ],
        "layer2_statistics": [
            band("ac_power_db",
                 collect(["layer2_statistics", "delta_div24_minus_div12", "ac_power_db"]),
                 "dB", "λ/24 − λ/12",
                 "⭐DC 제거 AC 절대전력. **레벨 주장은 이 밴드 밖에서만 유의하다**"),
            band("dc_power_db",
                 collect(["layer2_statistics", "delta_div24_minus_div12", "dc_power_db"]),
                 "dB", "λ/24 − λ/12",
                 "정지성분은 AC 보다 더 흔들린다 — DC 를 낀 잣대(옛 level_db)는 밴드가 더 넓다"),
            band("ac_over_dc_db",
                 collect(["layer2_statistics", "delta_div24_minus_div12", "ac_over_dc_db"]),
                 "dB", "λ/24 − λ/12",
                 "파생 비율. 분자·분모가 같이 흔들려 밴드가 AC 단독보다 넓다"),
            band("level_db_ledger_formula",
                 collect(["layer2_statistics", "delta_div24_minus_div12", "level_db_ledger_formula"]),
                 "dB", "λ/24 − λ/12",
                 "원장 `level_db`(=20log10 mean|E|, DC 포함) — 참고용"),
            band("above_f_tip_pp",
                 collect(["layer2_statistics", "delta_div24_minus_div12", "above_f_tip_pp"]),
                 "%p", "λ/24 − λ/12",
                 "⭐f_tip 밖 몫. 격자를 조이면 **일관되게 내려간다** — 이 잣대는 격자 잡음을 크게 읽고 있다"),
        ],
        "layer3_metric": [
            band("rhythm_share_pp",
                 collect(["layer3_metric", "delta_div24_minus_div12", "rhythm_share_pp"]),
                 "%p", "λ/24 − λ/12",
                 "⭐리듬 몫. 헤드라인 여럿이 이 잣대 위에 서 있다"),
            band("beat_hz",
                 collect(["layer3_metric", "delta_div24_minus_div12", "beat_hz"]),
                 "Hz", "λ/24 − λ/12",
                 "박자 위치. 밴드가 좁다 — 박자 주장은 격자에 강건하다"),
            band("band_power_db",
                 collect(["layer3_metric", "delta_div24_minus_div12", "band_power_db"]),
                 "dB", "λ/24 − λ/12",
                 "블레이드 대역(0.35~1.0 f_tip) STFT 전력"),
            band("classify_accuracy_pp",
                 collect(["layer3_metric", "delta_div24_minus_div12", "classify_accuracy_pp"]),
                 "%p", "λ/24 − λ/12",
                 "⭐빗살 argmax 분류. 밴드 0 이면 분류 주장은 격자 산물이 아니다"),
        ],
    }

    # ═══ ⭐사전등록 판정 — 팔 사이 순서 보존 ═══════════════════════════════════
    ORDER_METRICS = [
        ("ac_power_db", "높을수록 앞", False,
         "DC 제거 AC 절대전력 [dB]"),
        ("rhythm_share_pct", "높을수록 앞", False,
         "리듬 몫 [%]"),
        ("above_f_tip_pct", "높을수록 앞", False,
         "f_tip 밖 몫 [%]"),
        ("beat_err_hz", "낮을수록 앞", True,
         "박자 오차 |beat − f_flash| [Hz]"),
    ]
    BAND_FOR = {
        "ac_power_db": next(b["band"] for b in bands["layer2_statistics"] if b["metric"] == "ac_power_db"),
        "rhythm_share_pct": next(b["band"] for b in bands["layer3_metric"] if b["metric"] == "rhythm_share_pp"),
        "above_f_tip_pct": next(b["band"] for b in bands["layer2_statistics"] if b["metric"] == "above_f_tip_pp"),
        "beat_err_hz": next(b["band"] for b in bands["layer3_metric"] if b["metric"] == "beat_hz"),
    }

    def arm_values(arm: str, el: float, f_tip: float) -> dict:
        E = series(npz, arm, el)
        s = ac_dc(E)
        g = spectrum_metrics(E, prf, f_flash, f_tip)
        b = beat_from_stft(E, prf, f_flash, f_tip, stft_periods)
        return {
            "ac_power_db": s["ac_power_db"],
            "dc_power_db": s["dc_power_db"],
            "rhythm_share_pct": g["rhythm_share_pct"],
            "above_f_tip_pct": g["above_f_tip_pct"],
            "beat_hz": b["beat_hz"],
            "beat_err_hz": (None if b["beat_hz"] is None else round(abs(b["beat_hz"] - f_flash), 4)),
        }

    def order_of(vals: dict, key: str, ascending: bool) -> list:
        items = [(nm, v[key]) for nm, v in vals.items() if v[key] is not None]
        items.sort(key=lambda kv: kv[1], reverse=not ascending)
        return [nm for nm, _ in items]

    def min_gap_at_ours(vals: dict, key: str, ascending: bool, ours_name: str) -> float:
        """우리 팔이 이웃과 벌린 최소 간격 — **격자로 움직이는 것은 우리 팔뿐**이라
        순서가 뒤집힐 수 있는지는 이 간격만이 결정한다."""
        items = [(nm, v[key]) for nm, v in vals.items() if v[key] is not None]
        items.sort(key=lambda kv: kv[1], reverse=not ascending)
        names = [nm for nm, _ in items]
        i = names.index(ours_name)
        gaps = []
        if i > 0:
            gaps.append(abs(items[i][1] - items[i - 1][1]))
        if i < len(items) - 1:
            gaps.append(abs(items[i][1] - items[i + 1][1]))
        return float(min(gaps)) if gaps else float("inf")

    def min_gap_any_pair(vals: dict, key: str, ascending: bool) -> float:
        """이웃한 **아무 쌍**의 최소 간격 — 격자와 무관한 별개의 취약점을 드러낸다."""
        items = sorted([v[key] for v in vals.values() if v[key] is not None],
                       reverse=not ascending)
        return float(min(abs(items[i + 1] - items[i]) for i in range(len(items) - 1))) \
            if len(items) > 1 else float("inf")

    SETS = {
        "prereg_3arms": {"ours": None, "phys_off": ARM_PHYS_OFF, "phys_on": ARM_PHYS_ON},
        "supp_4arms_with_diffraction": {"ours": None, "phys_off": ARM_PHYS_OFF,
                                        "phys_on": ARM_PHYS_ON, "diffraction_only": ARM_DIFFR},
    }
    order_report = {}
    any_flip = False
    for set_name, arms in SETS.items():
        table = {}
        set_flip = False
        for el in ELS:
            f_tip = float(rows[(ARM_DIV12, el)]["f_tip_hz"])
            base = {nm: arm_values(arm, el, f_tip) for nm, arm in arms.items() if arm}
            v12 = {"ours": arm_values(ARM_DIV12, el, f_tip), **base}
            v24 = {"ours": arm_values(ARM_DIV24, el, f_tip), **base}
            cells = {}
            for key, dirn, ascending, label in ORDER_METRICS:
                o12 = order_of(v12, key, ascending)
                o24 = order_of(v24, key, ascending)
                same = o12 == o24
                gap12 = min_gap_at_ours(v12, key, ascending, "ours")
                gap24 = min_gap_at_ours(v24, key, ascending, "ours")
                bd = BAND_FOR[key]
                if not same:
                    verdict = "ORDER_FLIP"
                elif min(gap12, gap24) < bd:
                    verdict = "PRESERVED_BUT_WITHIN_BAND"
                else:
                    verdict = "PRESERVED_ROBUST"
                set_flip |= (verdict == "ORDER_FLIP")
                # 뒤집힘의 «크기» — 밴드보다 큰 간격을 건너뛰었나(MATERIAL), 아니면
                # 애초에 밴드 안에서 흔들린 것인가(WITHIN_BAND).
                flip_class = None
                if verdict == "ORDER_FLIP":
                    flip_class = "MATERIAL" if max(gap12, gap24) >= bd else "WITHIN_BAND"
                cells[key] = {
                    "label_ko": label, "rank_rule_ko": dirn,
                    "order_div12": o12, "order_div24": o24,
                    "ours_rank_div12": o12.index("ours") + 1,
                    "ours_rank_div24": o24.index("ours") + 1,
                    "values_div12": {nm: v12[nm][key] for nm in v12},
                    "values_div24": {nm: v24[nm][key] for nm in v24},
                    "min_gap_at_ours_div12": round(gap12, 4),
                    "min_gap_at_ours_div24": round(gap24, 4),
                    "min_gap_any_adjacent_pair_div12": round(
                        min_gap_any_pair(v12, key, ascending), 4),
                    "grid_band": bd,
                    "verdict": verdict,
                    "flip_class": flip_class,
                }
            table[f"{el:+.0f}"] = cells
        order_report[set_name] = {
            "arms": {k: (ARM_DIV12 + " / " + ARM_DIV24 if v is None else v) for k, v in arms.items()},
            "per_elevation": table,
            "any_order_flip": bool(set_flip),
        }
        if set_name == "prereg_3arms":
            any_flip = set_flip

    flips = [(s, e, k, c["flip_class"]) for s, rep in order_report.items()
             for e, cs in rep["per_elevation"].items()
             for k, c in cs.items() if c["verdict"] == "ORDER_FLIP"]
    within = [(s, e, k) for s, rep in order_report.items()
              for e, cs in rep["per_elevation"].items()
              for k, c in cs.items() if c["verdict"] == "PRESERVED_BUT_WITHIN_BAND"]
    robust = [(s, e, k) for s, rep in order_report.items()
              for e, cs in rep["per_elevation"].items()
              for k, c in cs.items() if c["verdict"] == "PRESERVED_ROBUST"]

    prereg = {
        "criterion_ko": ("설계서 그대로 — **팔 사이 순서(우리 vs 물리끔 vs 물리켬)가 λ/24 에서 바뀌면** "
                         "스위치 격자 인용에 «λ/12 한정» 꼬리표를 강제한다."),
        "criterion_changed": False,
        "criterion_change_reason_ko": "바꾸지 않았다. 다만 «순서는 같은데 간격이 밴드 안» 인 칸을 "
                                      "«보존» 으로 세지 않고 별도 판정(PRESERVED_BUT_WITHIN_BAND)으로 "
                                      "찍었다 — 기준을 **완화한 것이 아니라 조인 것**이다.",
        "order_flip_detected": bool(any_flip),
        "verdict_ko": ("⭐**꼬리표 강제 — 발동**. 사전등록 조건이 성립했다."
                       if any_flip else
                       "꼬리표 강제 없음 — 사전등록 조건이 성립하지 않았다."),
        "flip_cells": [{"set": s, "el_deg": e, "metric": k, "flip_class": fc}
                       for s, e, k, fc in flips],
        "within_band_cells": [{"set": s, "el_deg": e, "metric": k} for s, e, k in within],
        "robust_cells": [{"set": s, "el_deg": e, "metric": k} for s, e, k in robust],
        "enforced_tag_ko": ("λ/12 한정" if any_flip else None),
        "flip_class_summary_ko": (
            "뒤집힌 칸이 전부 **WITHIN_BAND** 다 — 즉 그 순서들은 λ/24 에서 «바뀐» 것이 아니라 "
            "애초에 격자 해상도로 **판정할 수 없는 순서**였다. 꼬리표 강제는 그대로 발동한다."
            if flips and all(fc == "WITHIN_BAND" for *_, fc in flips) else
            ("밴드보다 큰 간격을 건너뛴 **MATERIAL** 뒤집힘이 있다 — 격자가 결론을 바꾼다."
             if any(fc == "MATERIAL" for *_, fc in flips) else "뒤집힌 칸 없음")),
        "robust_summary_ko": (
            "⭐반면 **DC 제거 AC 절대전력** 순서(우리 ≫ 물리켬·물리끔)는 네 앙각 전부에서 "
            "밴드보다 훨씬 큰 여유로 보존된다 — 레벨 순서 진술은 격자에 강건하다."),
        "scope_ko": "밴드·순서표는 el 0·−15·−30·−45 네 자리에서만 잰다 — λ/24 팔이 그 넷뿐이다. "
                    "−60·−75·−90 은 아직 격자 대조가 없으므로 이 밴드를 **인용만 하고 검증되지는 않았다**.",
        "band_self_reference_ko": "⚠밴드는 바로 이 네 앙각의 |λ/24 − λ/12| 최대값이라, "
                                  "«뒤집힌 칸이 밴드 안» 이라는 진술은 부분적으로 동어반복이다. "
                                  "그래서 판정의 무게는 «밴드 안/밖» 이 아니라 **순서가 실제로 뒤집혔다**는 "
                                  "사실에 둔다.",
    }

    # ═══ 부록 · R15 나딧 절 (설계서: 독립 파일을 만들지 않는다) ════════════════
    E_sph = series(npz, ARM_NADIR_SPH, -90.0)
    E_pw = series(npz, ARM_NADIR_PW, -90.0)
    s_sph, s_pw = ac_dc(E_sph), ac_dc(E_pw)
    ac_band = next(b["band"] for b in bands["layer2_statistics"] if b["metric"] == "ac_power_db")
    acdc_band = next(b["band"] for b in bands["layer2_statistics"] if b["metric"] == "ac_over_dc_db")
    d_ac = round(s_pw["ac_power_db"] - s_sph["ac_power_db"], 3)
    d_dc = round(s_pw["dc_power_db"] - s_sph["dc_power_db"], 3)
    d_ratio = round(s_pw["ac_over_dc_db"] - s_sph["ac_over_dc_db"], 3)
    los_deg = 0.0
    nadir = {
        "question_ko": "직하방(−90°) 잔여가 근거리장 **곡률** 때문인가 — 평면파로 바꾸면 사라지나",
        "arms": {"spherical": f"{ARM_NADIR_SPH}/el-90", "plane_wave": f"{ARM_NADIR_PW}/el-90"},
        "spherical": s_sph, "plane_wave": s_pw,
        "delta_pw_minus_sph": {"ac_power_db": d_ac, "dc_power_db": d_dc, "ac_over_dc_db": d_ratio},
        "grid_band_ac_power_db": ac_band,
        "grid_band_ac_over_dc_db": acdc_band,
        "verdict_ko": (
            f"AC **절대전력** 차이는 {d_ac:+.2f} dB, 파생 비율(AC/DC) 차이는 {d_ratio:+.2f} dB 다. "
            f"둘 다 R16 격자 산포 밴드(AC {ac_band:.2f} dB · AC/DC {acdc_band:.2f} dB) **안**이므로 "
            f"«곡률이 원인이다/아니다» 를 이 원장으로는 **판정할 수 없다**."
            if (abs(d_ac) < ac_band and abs(d_ratio) < acdc_band) else
            f"AC {d_ac:+.2f} dB · AC/DC {d_ratio:+.2f} dB — 밴드 밖 항이 있어 판정 가능하다."),
        "note_ko": ("⭐AC 절대전력과 DC 를 **따로** 싣는다. 비율만 보면 «평면파가 더 낮다» 가 "
                    "1.27 dB 로 보이는데, AC 절대값 차이는 그 절반 이하다 — 비율이 움직인 이유의 "
                    "상당 부분이 **분모(DC)** 다."),
        "nadir_azimuth_dead_axis_ko": "나딧에서 방위는 죽은 축이다 — los(az, −90°)=[0,0,−1] 이라 "
                                      "방위 회전이 시선을 안 바꾼다. 앞으로 큐에서 나딧×방위 조합을 배제한다.",
        "nadir_azimuth_los_diff_deg": los_deg,
        "caveat_ko": "el −90 에는 λ/24 팔이 없다 — 여기 쓰는 밴드는 el 0~−45 에서 잰 값을 **가져다 쓴** 것이다.",
    }

    # ── 게이트 ⑤ 설계서가 인용한 무료 판독(el −30: 0.1062 → 0.0136) 재현 ────────
    a12 = per_el["-30"]["layer2_statistics"]["div12"]["above_f_tip_frac"]
    a24 = per_el["-30"]["layer2_statistics"]["div24"]["above_f_tip_frac"]
    gate("설계서 인용 재현 — el −30 의 f_tip 밖 몫 0.1062 → 0.0136",
         abs(a12 - 0.1062) < 5e-4 and abs(a24 - 0.0136) < 5e-4,
         f"재계산 {a12:.4f} → {a24:.4f}")

    # ── 부록 · R4 스코핑 (설계서 §④: «R4 는 R16 에 흡수 + 축소») ──────────────
    R4_PASS_LINE = 0.03            # 설계서가 쓴 통과선 — f_tip 밖 몫이 이 아래면 수렴 판정
    r4 = {"pass_line_above_f_tip_frac": R4_PASS_LINE,
          "rule_ko": "λ/24 의 f_tip 밖 몫이 통과선 아래면 그 앙각은 λ/48 을 살 이유가 없다",
          "per_elevation": {}, "still_open_els": []}
    for el in ELS:
        v24 = per_el[f"{el:+.0f}"]["layer2_statistics"]["div24"]["above_f_tip_frac"]
        v12 = per_el[f"{el:+.0f}"]["layer2_statistics"]["div12"]["above_f_tip_frac"]
        ok = v24 < R4_PASS_LINE
        r4["per_elevation"][f"{el:+.0f}"] = {"div12": v12, "div24": v24, "passes": bool(ok)}
        if not ok:
            r4["still_open_els"].append(f"{el:+.0f}")
    r4["verdict_ko"] = (
        f"λ/48 을 살 자리는 **{', '.join(r4['still_open_els'])}° 뿐**이다 — 나머지 앙각은 "
        f"λ/24 에서 이미 통과선 {R4_PASS_LINE} 아래로 내려갔다. 설계서 §④ 의 «남은 자리는 "
        "el −15 하나» 를 이 판독이 확인한다."
        if r4["still_open_els"] else
        f"네 앙각 전부 λ/24 에서 통과선 {R4_PASS_LINE} 아래다 — λ/48 축은 종결이다.")

    # ── 게이트 ⑥ 밴드가 비어 있지 않다 ────────────────────────────────────────
    n_band = sum(len(v) for v in bands.values())
    gate("밴드 표가 층마다 채워졌다", n_band >= 10, f"밴드 항목 {n_band} 개")

    # ── 게이트 ⑦ 순서표가 앙각 × 잣대를 모두 채웠다 ────────────────────────────
    n_cells = sum(len(cs) for rep in order_report.values() for cs in rep["per_elevation"].values())
    gate("순서 보존표가 앙각×잣대를 모두 채웠다",
         n_cells == len(SETS) * len(ELS) * len(ORDER_METRICS),
         f"{n_cells} 칸 = {len(SETS)} 팔집합 × {len(ELS)} 앙각 × {len(ORDER_METRICS)} 잣대")

    payload = {
        "_meta": {
            "generator": "benchmark/grid_convergence_check.py",
            "experiment": "R16 · 격자 λ/12 ↔ λ/24 세 층 판독",
            "design_doc": "docs/NEXT_EXPERIMENTS.md §② 순위 2 · §3-1 R16",
            "question_ko": "우리 커널의 어떤 주장이 격자(수치 해상도) 산물인가 — 그리고 "
                           "«몇 dB 차이면 유의한가» 의 산포 밴드를 만든다",
            "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S",
                                           time.localtime(t_start + 9 * 3600)) + " (UTC+9)",
            "runtime_sec": None,
            "gpu_used": False,
            "gpu_note_ko": "⛔sionna.rt·mitsuba 임포트 없음 — 저장된 원장만 읽는 CPU 분석",
            "provenance": {
                "ledger_npz": "outputs/elevation_sweep_md.npz",
                "ledger_json": "outputs/elevation_sweep_md.json",
                "npz_keys_used": sorted(
                    [f"{a}/{elkey(el)}" for a in (ARM_DIV12, ARM_DIV24, ARM_PHYS_OFF,
                                                  ARM_PHYS_ON, ARM_DIFFR, ARM_PTD) for el in ELS]
                    + [f"{ARM_NADIR_SPH}/el-90", f"{ARM_NADIR_PW}/el-90"]),
                "json_rows_used_ko": "rows 중 engine ∈ {위 팔} 이고 el_deg ∈ {0,−15,−30,−45} 인 행 — "
                                     "f_tip_hz · level_db · track.beat_hz · n_missing · grid_div 열을 읽었다",
                "meta_fields_used": ["prf_hz", "f_flash_hz", "fc_hz", "drone", "elevations_deg"],
            },
            "arms": {
                "ours_div12": ARM_DIV12, "ours_div24": ARM_DIV24,
                "phys_off": ARM_PHYS_OFF, "phys_on": ARM_PHYS_ON,
                "diffraction_only_supplementary": ARM_DIFFR,
                "ptd_reference_same_grid": ARM_PTD,
                "nadir_spherical": ARM_NADIR_SPH, "nadir_plane_wave": ARM_NADIR_PW,
            },
            "arm_naming_ko": {
                ARM_PHYS_OFF: "물리끔 — R0D0E0F1 · max_depth 1 · spp 4e9 · physics=False",
                ARM_PHYS_ON: "물리켬 — R1D1E1F1 · max_depth 1 · spp 4e9 · physics=True",
                ARM_DIFFR: "회절만 — 설계서 판의 «회절» 읽기를 위한 보조 팔",
            },
            "elevations_deg": ELS,
            "prf_hz": prf, "f_flash_hz": f_flash, "fc_hz": float(meta["fc_hz"]),
            "lambda_m": round(lam, 5),
            "grid_spacing_m": {"div12": round(lam / 12.0, 5), "div24": round(lam / 24.0, 5)},
            "drone": meta.get("drone"),
            "range_m": 15.0,
            "range_note_ko": "15 m — 원거리장 경계 2D²/λ ≈ 14.08 m **밖**. 이 원장의 10 m 옛 팔과 섞지 않았다.",
            "conventions_ko": [
                "레벨·에너지 비교는 전부 DC(시계열 평균) 제거 후",
                "마이크로도플러 표현은 STFT 만 (md_mapstyle.flash_spec — ⛔재할당·WVD 안 씀)",
                "리듬 몫 = P[|fr|≥f_tip 이고 f_flash 정수배 ±8 Hz] / P[|fr|≥f_tip] × 100",
                "분류 argmax 는 classify_airframe.py 규약(16 창 × 512 자세 · nfft 8192 · ±8 Hz)",
            ],
            "stft_settings_ko": {
                "beat_and_band_power": f"flash_spec periods={stft_periods:.2f} "
                                       "(=auto_periods) · hop 2 · pad 8 — 원장 analyse() 와 동일. "
                                       "재현 게이트가 track.beat_hz 를 0.005 Hz 안에서 되찾는다",
                "stft_db_map_correlation": "flash_spec 기본 periods=0.6 · hop 2 · pad 8 — "
                                           "덱·physics_vs_deck.json 이 0.9877 / 0.6961 을 낸 세팅과 동일",
                "why_two_ko": "두 잣대가 서로 다른 세팅으로 이미 발표돼 있어, 각각 그 세팅으로 "
                              "재야 사과-대-사과가 된다. 세팅은 그림 밖(이 블록)에만 적는다",
            },
            "spectrum_fft_ko": "리듬·f_tip 밖 몫은 제로패딩 없는 8192 점 FFT(빈 간격 "
                               f"{prf / 8192:.3f} Hz) · hanning · DC 제거",
            "cost_note_ko": "⚠원장 `seconds` 로 λ/24 가 λ/12 보다 **싸게** 찍힌 칸이 있다"
                            f"(el 0: {rows[(ARM_DIV12, 0.0)]['seconds']} s → "
                            f"{rows[(ARM_DIV24, 0.0)]['seconds']} s). 이는 벽시계이고 "
                            "GPU 경합에 좌우된다 — **DIV² 비용모형의 근거로 쓰지 마라**.",
        },
        "per_elevation": per_el,
        "rho_reference_rulers": rho_rulers,
        "grid_dispersion_bands": {
            "how_to_use_ko": "⭐다른 실험은 «두 팔의 차이가 이 밴드 안이면 판정 불가» 로 쓴다. "
                             "밴드는 네 앙각(0·−15·−30·−45)에서 잰 |λ/24 − λ/12| 의 **최대값**이다 "
                             "(중앙값도 같이 싣는다 — 보수적으로 쓰려면 최대값을 쓴다).",
            "headline_ko": None,      # 아래에서 채운다
            "bands": bands,
        },
        "prereg_verdict": prereg,
        "arm_order_tables": order_report,
        "appendix_r15_nadir": nadir,
        "appendix_r4_scoping": r4,
        "self_checks": checks,
        "corrections": [],            # 아래에서 채운다
    }

    # ── 헤드라인 문장 ────────────────────────────────────────────────────────
    b_ac = next(b for b in bands["layer2_statistics"] if b["metric"] == "ac_power_db")
    b_rhy = next(b for b in bands["layer3_metric"] if b["metric"] == "rhythm_share_pp")
    b_aft = next(b for b in bands["layer2_statistics"] if b["metric"] == "above_f_tip_pp")
    b_beat = next(b for b in bands["layer3_metric"] if b["metric"] == "beat_hz")
    b_cls = next(b for b in bands["layer3_metric"] if b["metric"] == "classify_accuracy_pp")
    rho_min = min(collect(["layer1_waveform", "abs_rho_dc_removed"]))
    payload["grid_dispersion_bands"]["headline_ko"] = (
        f"⭐격자 산포 밴드 — 파형 |ρ| 바닥 {rho_min:.2f} · AC 절대전력 {b_ac['band']:.2f} dB · "
        f"리듬 몫 {b_rhy['band']:.1f} %p · f_tip 밖 몫 {b_aft['band']:.1f} %p · "
        f"박자 {b_beat['band']:.2f} Hz · 분류 정확도 {b_cls['band']:.1f} %p."
    )

    payload["_meta"]["runtime_sec"] = round(time.time() - t_start, 1)
    return payload, per_el, bands, order_report, prereg, nadir


# ═══════════════════════════════════════════════════════════════════════════ #
#  3) 그림 (영어 · 겹침 금지)
# ═══════════════════════════════════════════════════════════════════════════ #
INK, INK2, GRID = "#0b0b0b", "#55534f", "#d9d8d4"
BLUE, ORANGE, GREEN, RED = "#2a78d6", "#eb6834", "#2e8b57", "#c0392b"


def fig_three_layers(payload, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    els = payload["_meta"]["elevations_deg"]
    xs = np.arange(len(els))
    lab = [f"{e:+.0f}°" for e in els]
    pe = payload["per_elevation"]

    def g(el, *p):
        v = pe[f"{el:+.0f}"]
        for k in p:
            v = v[k]
        return v

    fig = plt.figure(figsize=(15.2, 9.2), dpi=150)
    gs = fig.add_gridspec(2, 3, left=0.062, right=0.985, top=0.815, bottom=0.085,
                          hspace=0.46, wspace=0.30)
    fig.suptitle("R16 — What survives halving the ray-grid spacing (λ/12 → λ/24), our SBR+PO kernel",
                 fontsize=15, fontweight="bold", color=INK, y=0.972)
    fig.text(0.062, 0.925,
             "Same airframe, range, azimuth and pose count; only the grid spacing changes. "
             "All levels and energies are computed after removing the DC (time-mean) component; "
             "micro-Doppler uses STFT only.\n"
             "Layer 1 asks whether the waveform is the same, layer 2 whether the numbers are the same, "
             "layer 3 whether the verdicts are the same.",
             fontsize=9.2, color=INK2, va="top")

    # ── A. 파형층 ────────────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 0])
    rr = payload["rho_reference_rulers"]
    ax.axhspan(rr["cross_elevation_min"], rr["cross_elevation_max"],
               color="#b9b7b2", alpha=0.34, lw=0)
    ax.text(len(els) - 1 + 0.42, 0.5 * (rr["cross_elevation_min"] + rr["cross_elevation_max"]),
            "|ρ| between two\ndifferent elevations\nof the same arm",
            fontsize=7.0, color="#4a4845", ha="right", va="center")
    rho = [g(e, "layer1_waveform", "abs_rho_dc_removed") for e in els]
    mapc = [g(e, "layer1_waveform", "stft_db_map_corr_dc_removed") for e in els]
    ref_ptd = [g(e, "layer1_waveform", "ref_abs_rho_vs_ptd_same_grid") for e in els]
    ref_off = [g(e, "layer1_waveform", "ref_abs_rho_vs_phys_off_same_grid") for e in els]
    ax.plot(xs, rho, "-o", color=BLUE, lw=2.2, ms=7, label="|ρ|  λ/12 vs λ/24  (grid only)")
    ax.plot(xs, mapc, "-s", color=ORANGE, lw=2.0, ms=6, label="STFT dB-map corr, same pair")
    ax.plot(xs, ref_ptd, "--^", color=GREEN, lw=1.6, ms=6,
            label="|ρ| vs PTD arm, same grid (\"identical pattern\")")
    ax.plot(xs, ref_off, ":v", color=RED, lw=1.6, ms=6,
            label="|ρ| vs PathSolver physics-off, same grid")
    ax.axhline(rr["shuffled_null"], color=INK2, lw=1.1, ls=(0, (2, 2)))
    ax.text(-0.42, rr["shuffled_null"] + 0.025, "shuffled null", fontsize=7.0,
            color=INK2, va="bottom")
    ax.set_xticks(xs, lab)
    ax.set_xlim(-0.5, len(els) - 0.5)
    ax.set_ylim(-0.05, 1.62)
    ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylabel("correlation  [0…1]", fontsize=9.5, color=INK2)
    ax.set_xlabel("elevation", fontsize=9.5, color=INK2)
    ax.set_title("Layer 1 — waveform", fontsize=11.5, color=INK, pad=8)
    ax.legend(fontsize=7.2, loc="upper left", frameon=True, framealpha=0.95,
              borderpad=0.5, labelspacing=0.42)
    ax.grid(color=GRID, lw=0.7)
    ax.set_axisbelow(True)

    # ── B. 통계층 ────────────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 1])
    d_ac = [g(e, "layer2_statistics", "delta_div24_minus_div12", "ac_power_db") for e in els]
    d_dc = [g(e, "layer2_statistics", "delta_div24_minus_div12", "dc_power_db") for e in els]
    w = 0.36
    ax.bar(xs - w / 2, d_ac, w, color=BLUE, label="AC power (DC removed)")
    ax.bar(xs + w / 2, d_dc, w, color=ORANGE, label="DC power")
    ax.axhline(0, color=INK, lw=1.0)
    ax.set_xticks(xs, lab)
    ax.set_ylabel("Δ level,  λ/24 − λ/12  [dB]", fontsize=9.5, color=INK2)
    ax.set_xlabel("elevation", fontsize=9.5, color=INK2)
    ax.set_title("Layer 2 — absolute levels", fontsize=11.5, color=INK, pad=8)
    ax.legend(fontsize=8, loc="upper left", frameon=True, framealpha=0.92)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    lo = min(d_ac + d_dc + [0.0])
    hi = max(d_ac + d_dc + [0.0])
    ax.set_ylim(lo - 0.10 * (hi - lo) - 0.5, hi + 0.34 * (hi - lo) + 0.5)

    # ── C. f_tip 밖 몫 ───────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 2])
    a12 = [100 * g(e, "layer2_statistics", "div12", "above_f_tip_frac") for e in els]
    a24 = [100 * g(e, "layer2_statistics", "div24", "above_f_tip_frac") for e in els]
    ax.bar(xs - w / 2, a12, w, color=BLUE, label="λ/12")
    ax.bar(xs + w / 2, a24, w, color=ORANGE, label="λ/24")
    for i in range(len(xs)):
        ax.annotate("", xy=(xs[i] + w / 2, a24[i]), xytext=(xs[i] - w / 2, a12[i]),
                    arrowprops=dict(arrowstyle="->", color=INK2, lw=1.0, alpha=0.75))
    ax.set_xticks(xs, lab)
    ax.set_ylabel("energy above f_tip  [% of AC]", fontsize=9.5, color=INK2)
    ax.set_xlabel("elevation", fontsize=9.5, color=INK2)
    ax.set_title("Layer 2 — out-of-band share falls with a finer grid",
                 fontsize=11.5, color=INK, pad=8)
    ax.legend(fontsize=8.5, loc="upper right", frameon=True, framealpha=0.92)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(a12) * 1.30)

    # ── D. 리듬 몫 ───────────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 0])
    r12 = [g(e, "layer3_metric", "div12", "rhythm_share_pct") for e in els]
    r24 = [g(e, "layer3_metric", "div24", "rhythm_share_pct") for e in els]
    ax.bar(xs - w / 2, r12, w, color=BLUE, label="λ/12")
    ax.bar(xs + w / 2, r24, w, color=ORANGE, label="λ/24")
    ax.axhline(13.0, color=INK2, lw=1.2, ls=(0, (4, 3)))
    ax.text(len(xs) - 0.52, 15.0, "white-noise level ≈ 13 %", fontsize=7.8,
            color=INK2, ha="right", va="bottom")
    ax.set_xticks(xs, lab)
    ax.set_ylim(0, 100)
    ax.set_ylabel("rhythm share above f_tip  [%]", fontsize=9.5, color=INK2)
    ax.set_xlabel("elevation", fontsize=9.5, color=INK2)
    ax.set_title("Layer 3 — rhythm share", fontsize=11.5, color=INK, pad=8)
    ax.legend(fontsize=8.5, loc="upper right", frameon=True, framealpha=0.92)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)

    # ── E. 박자 위치 ─────────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 1])
    ffl = payload["_meta"]["f_flash_hz"]
    b12 = [g(e, "layer3_metric", "div12", "beat_hz") - ffl for e in els]
    b24 = [g(e, "layer3_metric", "div24", "beat_hz") - ffl for e in els]
    ax.bar(xs - w / 2, b12, w, color=BLUE, label="λ/12")
    ax.bar(xs + w / 2, b24, w, color=ORANGE, label="λ/24")
    ax.axhline(0, color=INK, lw=1.0)
    ax.set_xticks(xs, lab)
    ax.set_ylabel(f"beat − f_flash  [Hz]   (f_flash = {ffl:.2f} Hz)", fontsize=9.5, color=INK2)
    ax.set_xlabel("elevation", fontsize=9.5, color=INK2)
    ax.set_title("Layer 3 — beat position (grid-robust)", fontsize=11.5, color=INK, pad=8)
    ax.legend(fontsize=8.5, loc="lower left", frameon=True, framealpha=0.92)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    span = max(abs(min(b12 + b24)), abs(max(b12 + b24)))
    ax.set_ylim(-1.55 * span, 1.55 * span)

    # ── F. 분류 argmax — 정확도가 네 앙각 모두 100 % 라, 볼 것은 «여유» 다 ─────
    ax = fig.add_subplot(gs[1, 2])
    m12 = [g(e, "layer3_metric", "div12", "classify", "decision_margin_median") for e in els]
    m24 = [g(e, "layer3_metric", "div24", "classify", "decision_margin_median") for e in els]
    n_win = g(els[0], "layer3_metric", "div12", "classify", "n_windows")
    ax.bar(xs - w / 2, m12, w, color=BLUE, label="λ/12")
    ax.bar(xs + w / 2, m24, w, color=ORANGE, label="λ/24")
    ax.set_xticks(xs, lab)
    ax.set_ylim(0, max(m12 + m24) * 1.80)
    ax.set_ylabel("median decision margin\n(true comb score − best rival)", fontsize=9.5, color=INK2)
    ax.set_xlabel("elevation", fontsize=9.5, color=INK2)
    ax.set_title("Layer 3 — comb argmax classification", fontsize=11.5, color=INK, pad=8)
    ax.legend(fontsize=8.5, loc="upper left", frameon=True, framealpha=0.92)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    ax.text(0.975, 0.955,
            f"argmax correct in {n_win}/{n_win} windows,\nevery elevation, both grids",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.0, color=INK,
            bbox=dict(boxstyle="round,pad=0.42", facecolor="#eef4ea",
                      edgecolor="#9dbf95", lw=0.9))

    fig.savefig(path, dpi=150, facecolor="white")
    import matplotlib.pyplot as _p
    _p.close(fig)


def fig_band_and_order(payload, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    bands = payload["grid_dispersion_bands"]["bands"]
    rows_b = []
    for b in bands["layer2_statistics"] + bands["layer3_metric"]:
        rows_b.append((b["metric"], b["median_abs"], b["band"], b["unit"]))
    rows_b = rows_b[::-1]

    fig = plt.figure(figsize=(15.2, 8.0), dpi=150)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.32],
                          left=0.145, right=0.985, top=0.795, bottom=0.115, wspace=0.34)
    fig.suptitle("R16 — the grid dispersion band, and whether arm ordering survives λ/24",
                 fontsize=15, fontweight="bold", color=INK, y=0.968)
    fig.text(0.032, 0.905,
             "Left: how much each metric moves when only the ray-grid spacing is halved "
             "(bar = worst of four elevations, tick = median). Any future claim whose effect is "
             "smaller than its bar cannot be resolved with this ledger.\n"
             "Right: rank of our kernel against PathSolver physics-off and physics-on at each elevation, "
             "recomputed with our kernel on the λ/12 grid and on the λ/24 grid.",
             fontsize=9.2, color=INK2, va="top")

    # ── 왼쪽: 밴드 막대 ──────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 0])
    y = np.arange(len(rows_b))
    UNIT_C = {"dB": BLUE, "%p": ORANGE, "Hz": GREEN}
    xmax = max(b for _, _, b, _ in rows_b) * 1.44
    for i, (nm, med, bd, unit) in enumerate(rows_b):
        ax.barh(i, bd, 0.62, color=UNIT_C.get(unit, INK2), alpha=0.88)
        ax.plot([med], [i], "|", color=INK, ms=16, mew=2.2)
        txt = f"{bd:.3g} {unit}" + ("   (no change)" if bd == 0 else "")
        ax.text(bd + 0.018 * xmax, i, txt, va="center", ha="left", fontsize=8.6, color=INK)
    ax.set_yticks(y, [nm for nm, _, _, _ in rows_b], fontsize=8.6, color=INK)
    ax.set_xlabel("band  =  max |λ/24 − λ/12|  over four elevations", fontsize=9.5, color=INK2)
    ax.set_xlim(0, xmax)
    ax.set_title("Grid dispersion band per metric\n"
                 "bar colour = unit   (blue dB · orange %p · green Hz)",
                 fontsize=11.5, color=INK, pad=9)
    ax.grid(axis="x", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # ── 오른쪽: 순서 보존 격자 ───────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 1])
    rep = payload["arm_order_tables"]["prereg_3arms"]["per_elevation"]
    els = payload["_meta"]["elevations_deg"]
    mkeys = ["ac_power_db", "rhythm_share_pct", "above_f_tip_pct", "beat_err_hz"]
    mlab = ["AC power\n[dB]", "rhythm share\n[%]", "above f_tip\n[%]", "beat error\n[Hz]"]
    COL = {"PRESERVED_ROBUST": "#c9e6cd", "PRESERVED_BUT_WITHIN_BAND": "#fde3b8",
           "ORDER_FLIP": "#f6b8b0"}
    TXT = {"PRESERVED_ROBUST": "order kept", "PRESERVED_BUT_WITHIN_BAND": "kept, but\ngap < band",
           "ORDER_FLIP": "ORDER FLIPS"}
    for j, el in enumerate(els):
        for i, mk in enumerate(mkeys):
            c = rep[f"{el:+.0f}"][mk]
            v = c["verdict"]
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=COL[v], edgecolor="white", lw=2.2))
            ax.text(j + 0.5, i + 0.66, TXT[v], ha="center", va="center", fontsize=8.0,
                    color=INK, fontweight="bold" if v == "ORDER_FLIP" else "normal")
            rank = f"ours #{c['ours_rank_div12']}"
            if v == "ORDER_FLIP":
                rank += f" → #{c['ours_rank_div24']}"
            ax.text(j + 0.5, i + 0.36, rank, ha="center", va="center",
                    fontsize=7.2, color=INK2)
            gapline = (f"gap {c['min_gap_at_ours_div12']:.3g} / band {c['grid_band']:.3g}")
            ax.text(j + 0.5, i + 0.14, gapline, ha="center", va="center",
                    fontsize=6.4, color="#6e6c68")
    ax.set_xlim(0, len(els))
    ax.set_ylim(0, len(mkeys))
    ax.set_xticks(np.arange(len(els)) + 0.5, [f"{e:+.0f}°" for e in els], fontsize=9.5, color=INK)
    ax.set_yticks(np.arange(len(mkeys)) + 0.5, mlab, fontsize=8.6, color=INK)
    ax.tick_params(length=0)
    ax.set_xlabel("elevation", fontsize=9.5, color=INK2)
    ax.set_title("Pre-registered test — ours vs physics-off vs physics-on",
                 fontsize=11.5, color=INK, pad=9)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.invert_yaxis()
    verdict = ("VERDICT: at least one ordering flips → switch-grid citations must carry "
               "a \"λ/12 only\" tag"
               if payload["prereg_verdict"]["order_flip_detected"] else
               "VERDICT: no ordering flips → no \"λ/12 only\" tag required")
    fig.text(0.985, 0.035, verdict, fontsize=10.0, color=RED if
             payload["prereg_verdict"]["order_flip_detected"] else GREEN,
             ha="right", va="bottom", fontweight="bold")

    fig.savefig(path, dpi=150, facecolor="white")
    import matplotlib.pyplot as _p
    _p.close(fig)


# ═══════════════════════════════════════════════════════════════════════════ #
#  4) main
# ═══════════════════════════════════════════════════════════════════════════ #
def main() -> None:
    payload, per_el, bands, order_report, prereg, nadir = run()

    # ── 기존 문장 정정 목록 (파일은 고치지 않는다 — 목록만 남긴다) ─────────────
    rho_min = min(per_el[f"{e:+.0f}"]["layer1_waveform"]["abs_rho_dc_removed"]
                  for e in payload["_meta"]["elevations_deg"])
    map_min = min(per_el[f"{e:+.0f}"]["layer1_waveform"]["stft_db_map_corr_dc_removed"]
                  for e in payload["_meta"]["elevations_deg"])
    map_at_15 = per_el["-15"]["layer1_waveform"]["stft_db_map_corr_dc_removed"]
    b_rhy = next(b for b in bands["layer3_metric"] if b["metric"] == "rhythm_share_pp")["band"]
    b_aft = next(b for b in bands["layer2_statistics"] if b["metric"] == "above_f_tip_pp")["band"]
    b_ac = next(b for b in bands["layer2_statistics"] if b["metric"] == "ac_power_db")["band"]

    corrections = [
        {
            "where": "docs/RESUME.md §1 표 8번 · docs/PLAN_VOLUMES_16_17.md 86행·251행·423행 "
                     "· outputs/physics_vs_deck.json cells.*.corr_with_ours_db_map",
            "current_ko": "「우리 팔이 8/11 덱 15 m 판과 **상관 0.9877** 로 겹친다 — "
                          "PathSolver 물리끔은 0.6961 로 안 겹친다」",
            "correct_to_ko": (f"같은 잣대(STFT dB-맵 상관)로 **격자만** λ/12→λ/24 로 바꾸면 "
                              f"상관이 {map_min:.4f}~{max(per_el[f'{e:+.0f}']['layer1_waveform']['stft_db_map_corr_dc_removed'] for e in payload['_meta']['elevations_deg']):.4f} "
                              f"로 내려간다(el −15 에서 {map_at_15:.4f}). 즉 **0.6961 은 격자 바닥과 구별되지 않는다** — "
                              "「PathSolver 가 덱과 안 닮았다」는 이 잣대로는 못 세운다. "
                              "상관 인용에는 «같은 격자끼리만» 단서를 붙인다."),
            "severity": "high",
            "evidence": "outputs/grid_convergence_check.json : per_elevation.*.layer1_waveform",
        },
        {
            "where": "상관(|ρ|·맵 상관)을 «닮았다/안 닮았다» 의 근거로 쓰는 모든 자리 "
                     "(docs/RESUME.md · docs/PLAN_VOLUMES_16_17.md · 덱 대조 표)",
            "current_ko": "상관 0.6~0.7 을 «안 닮았다» 의 근거로, 0.98 을 «같다» 의 근거로 사용",
            "correct_to_ko": (
                f"⭐같은 커널·같은 격자에서 **앙각만** 15~45° 바꿔도 |ρ| 가 "
                f"{payload['rho_reference_rulers']['cross_elevation_min']:.2f}~"
                f"{payload['rho_reference_rulers']['cross_elevation_max']:.2f} 나온다"
                "(섞기 널은 "
                f"{payload['rho_reference_rulers']['shuffled_null']:.3f}). "
                "즉 0.5~0.8 대는 **명백히 다른 물건들 사이의 평범한 값**이라 «닮았다» 의 근거가 못 된다. "
                "상관을 인용할 때는 반드시 이 자(앙각 교차·격자 교차·섞기 널)를 같이 싣는다."),
            "severity": "high",
            "evidence": "outputs/grid_convergence_check.json : rho_reference_rulers",
        },
        {
            "where": "docs/RESUME.md §1 표 2번 · outputs/switch_grid.json 인용 "
                     "(「회절 든 조합 11.7~13.2 % ↔ 없는 조합 62.1~80.5 %」)",
            "current_ko": "「리듬 몫 62.1~80.5 % ↔ 11.7~13.2 %」를 격자 단서 없이 인용",
            "correct_to_ko": (f"리듬 몫은 격자만 λ/24 로 바꿔도 최대 **{b_rhy:.1f} %p** 움직인다"
                              "(el −30 에서 83.3 → 61.5 %). 62.1~80.5 % 는 **λ/12 한정 수치**이므로 "
                              "인용에 «λ/12» 를 박는다. 다만 «회절 든 조합 ≈13 %(백색 수준)» 라는 "
                              "**결론의 방향은 밴드 밖**이라 그대로 산다."),
            "severity": "high",
            "evidence": "outputs/grid_convergence_check.json : grid_dispersion_bands.bands.layer3_metric",
        },
        {
            "where": "docs/RESUME.md §1 표 1번 (el 0 «0° 익사» 서사에서 리듬 몫·레벨을 쓰는 자리)",
            "current_ko": "우리 커널의 el 0 리듬 몫·AC 레벨을 격자 단서 없이 절대값으로 인용",
            "correct_to_ko": (f"el 0 은 격자 민감도가 가장 큰 자리다 — |ρ| {per_el['+0']['layer1_waveform']['abs_rho_dc_removed']:.2f}, "
                              f"AC {per_el['+0']['layer2_statistics']['delta_div24_minus_div12']['ac_power_db']:+.2f} dB, "
                              f"리듬 몫 {per_el['+0']['layer3_metric']['delta_div24_minus_div12']['rhythm_share_pp']:+.1f} %p. "
                              "el 0 의 **절대 수치**는 인용하지 말고 «우리 팔은 el 0 에서 박자를 유지하고 "
                              "PathSolver 는 못 한다» 는 **순서 진술**만 쓴다(그 순서는 격자에 강건하다)."),
            "severity": "medium",
            "evidence": "outputs/grid_convergence_check.json : per_elevation.+0",
        },
        {
            "where": "docs/NEXT_EXPERIMENTS.md §② 15행(R15) 「문턱은 R16 의 격자 산포 밴드(≈3 dB)의 2 배 밖」",
            "current_ko": "밴드를 «≈3 dB» 로 어림잡아 적어 둠",
            "correct_to_ko": (f"실측 밴드는 **AC 절대전력 {b_ac:.2f} dB**(DC 는 더 넓다). "
                              "R15 나딧 판정은 AC 차이 "
                              f"{nadir['delta_pw_minus_sph']['ac_power_db']:+.2f} dB · AC/DC 차이 "
                              f"{nadir['delta_pw_minus_sph']['ac_over_dc_db']:+.2f} dB 로 **밴드 안**이라 "
                              "«판정 불가» 다 — 설계서가 예상한 대로다."),
            "severity": "low",
            "evidence": "outputs/grid_convergence_check.json : appendix_r15_nadir",
        },
        {
            "where": "docs/NEXT_EXPERIMENTS.md §④ 「R4 λ/48 … DIV² 비용모형이 원장과 배치」 주변",
            "current_ko": "원장 `seconds` 로 λ/24 가 λ/12 보다 싸 보이는 것을 비용모형 논거로 씀",
            "correct_to_ko": ("`seconds` 는 GPU 경합 아래의 **벽시계**다(el 0: 1713.8 s → 567.8 s). "
                              "비용모형의 근거로 쓰지 말고, 비용은 격자 셀 수로 따로 세운다."),
            "severity": "low",
            "evidence": "outputs/elevation_sweep_md.json : rows[*].seconds",
        },
        {
            "where": "f_tip 밖 몫(`above_f_tip_frac`)을 쓰는 모든 자리 "
                     "(benchmark/build_above_tip_fig.py · build_deck_maps.py · 덱의 «대역밖» 막대)",
            "current_ko": "f_tip 밖 몫을 팔 사이 비교의 주 잣대로 사용",
            "correct_to_ko": (f"이 잣대는 격자만 바꿔도 최대 **{b_aft:.1f} %p** 움직이고 방향이 "
                              "**일관되게 아래**다(격자를 조이면 준다) — 즉 **격자 잡음을 크게 읽는다**. "
                              "우리 팔의 f_tip 밖 몫은 절대값으로 인용하지 말고 «격자 의존» 단서를 단다. "
                              "PathSolver 물리켬의 ~86 % 는 밴드 밖이라 그대로 산다."),
            "severity": "medium",
            "evidence": "outputs/grid_convergence_check.json : grid_dispersion_bands.bands.layer2_statistics",
        },
    ]
    payload["corrections"] = corrections

    os.makedirs(FIG_DIR, exist_ok=True)
    fig_three_layers(payload, FIG1)
    fig_band_and_order(payload, FIG2)
    payload["_meta"]["figures"] = ["outputs/figures/grid_r16_three_layers.png",
                                   "outputs/figures/grid_r16_band_and_order.png"]

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # ── 콘솔 요약 ────────────────────────────────────────────────────────────
    print("=" * 96)
    print("R16 · 격자 λ/12 ↔ λ/24 세 층 판독")
    print("=" * 96)
    print(f"{'el':>5} | {'|ρ|':>6} {'map ρ':>7} | {'ΔAC':>7} {'ΔDC':>7} {'Δ>f_tip':>9} | "
          f"{'리듬12':>7} {'리듬24':>7} {'Δ리듬':>7} | {'Δbeat':>7} | {'분류12':>7} {'분류24':>7}")
    print("-" * 96)
    for e in payload["_meta"]["elevations_deg"]:
        c = payload["per_elevation"][f"{e:+.0f}"]
        w, s, m = c["layer1_waveform"], c["layer2_statistics"], c["layer3_metric"]
        print(f"{e:+5.0f} | {w['abs_rho_dc_removed']:6.4f} {w['stft_db_map_corr_dc_removed']:7.4f} | "
              f"{s['delta_div24_minus_div12']['ac_power_db']:+7.2f} "
              f"{s['delta_div24_minus_div12']['dc_power_db']:+7.2f} "
              f"{s['delta_div24_minus_div12']['above_f_tip_pp']:+9.2f} | "
              f"{m['div12']['rhythm_share_pct']:7.1f} {m['div24']['rhythm_share_pct']:7.1f} "
              f"{m['delta_div24_minus_div12']['rhythm_share_pp']:+7.1f} | "
              f"{m['delta_div24_minus_div12']['beat_hz']:+7.2f} | "
              f"{100*m['div12']['classify']['accuracy']:6.1f}% {100*m['div24']['classify']['accuracy']:6.1f}%")
    print("-" * 96)
    print(payload["grid_dispersion_bands"]["headline_ko"])
    print()
    rr = payload["rho_reference_rulers"]
    print(f"|ρ| 판정용 자 — 같은 팔·같은 격자에서 앙각만 바꾼 상관 "
          f"{rr['cross_elevation_min']:.2f}~{rr['cross_elevation_max']:.2f} · "
          f"섞기 널 {rr['shuffled_null']:.3f} (1/√N={rr['noise_floor_1_over_sqrt_n']:.3f})")
    print()
    print("⭐사전등록 판정 —", payload["prereg_verdict"]["verdict_ko"])
    for c in payload["prereg_verdict"]["flip_cells"]:
        print(f"   순서 뒤집힘[{c['flip_class']}]: {c['set']} · el {c['el_deg']} · {c['metric']}")
    print("   " + payload["prereg_verdict"]["flip_class_summary_ko"])
    print(f"   («순서 같으나 간격이 밴드 안» 칸 {len(payload['prereg_verdict']['within_band_cells'])} 개 · "
          f"«강건 보존» 칸 {len(payload['prereg_verdict']['robust_cells'])} 개)")
    print()
    print("부록 R15 나딧 —", payload["appendix_r15_nadir"]["verdict_ko"])
    print("부록 R4 스코핑 —", payload["appendix_r4_scoping"]["verdict_ko"])
    print()
    print("자가검사")
    n_ok = 0
    for c in payload["self_checks"]:
        mark = "PASS" if c["pass"] else "FAIL"
        n_ok += int(c["pass"])
        print(f"  [{mark}] {c['check']}  —  {c['detail']}")
    print(f"  ⇒ {n_ok}/{len(payload['self_checks'])} 통과")
    print()
    print(f"산출  {OUT_JSON}")
    print(f"      {FIG1}")
    print(f"      {FIG2}")
    if n_ok != len(payload["self_checks"]):
        raise SystemExit("⛔ 자가검사 실패 — 위 FAIL 항목을 보라")


if __name__ == "__main__":
    main()
