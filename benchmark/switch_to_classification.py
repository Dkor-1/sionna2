# -*- coding: utf-8 -*-
"""
switch_to_classification.py — R14 · 엔진 설정이 «기체 분류» 에 얼마를 물리나
================================================================================
설계서 : docs/NEXT_EXPERIMENTS.md §② 순위 6 · §3-1 «R14 · classify_airframe_configs»
의존   : R13(outputs/switch_factorial.json) · R16 밴드(outputs/grid_convergence_check.json)
⛔GPU 0 — sionna.rt·mitsuba 임포트 없음. 저장된 원장(npz·json)만 읽는 CPU 분석.
⛔기존 파일 수정 없음 — 새 파일만 쓴다(원본 benchmark/classify_airframe.py 는 안 건드린다).

질문
  같은 분류기(제원에서 만든 «박자 빗살» 템플릿 정합)를 **엔진 설정 축**으로 다시 채점하면
  성적이 얼마나 달라지나. 그리고 성적이 떨어질 때, 그것은 «날개 신호가 사라져서» 인가
  «바닥이 올라와 덮여서» 인가.

용어 먼저 (쉬운 말)
  · **움직이는 부분 / 가만히 있는 부분** — 시계열 E 의 평균을 «가만히 있는 부분(DC)»,
    평균을 뺀 나머지를 «움직이는 부분(AC)» 이라 부른다. 레벨 비교는 **전부 평균을 뺀 뒤** 한다.
  · **박자(f_flash)** — 날개가 시선을 스치는 초당 횟수 = 날개수 × 호버 rpm / 60. 기체마다 다르다.
  · **빗살** — 그 박자의 정수배마다 서는 스펙트럼 선들. 빗살의 «이빨» 간격이 기체의 지문이다.
  · **날개끝(f_tip)** — 날개 끝 속도가 만드는 최대 도플러. 그 위(|f| ≥ f_tip)는 동체가 아니라
    날개만 만들 수 있는 자리라 «상한 위» 라고 부른다.
  · **선(line)과 바닥(floor)** — 상한 위에서 빗살 빈에 서는 초과분이 «선», 빗살 밖 빈의 전력이
    «바닥». 선/바닥 대비(dB)가 곧 «빗살 신호 대 바닥» 이다.
  · **덮개율(coverage)** — 빗살 마스크가 차지하는 빈 비율. 스펙트럼이 백색이면 빗살 몫 ≈ 덮개율이
    되어, 덮개율이 최대인 기체로 예측이 쏠린다(= 상수 예측기).

설정 축 (⭐이름 두 벌이 돌아다녀 여기서 못 박는다)
  본 산출물 이름      설계서 §3-1 이름   스위치            뜻
  ours              (공통 기준선)      —                 우리 커널(SBR+PO)
  sionna_off        설정 A            R0D0E0F1 · d1     Sionna PathSolver, 물리 스위치 전부 끔
  sionna_refr       설정 B            R1D0E0F1 · d1     굴절만 켬
  sionna_phys       설정 C            R1D1E1F1 · d1     물리 전부 켬(굴절+쐐기회절+모서리회절)
  ⚠과제문의 «(A) 우리 커널 (B) 물리 끔 (C) 물리 켬» 과 설계서의 «A/B/C» 가 어긋난다 —
    본 산출물은 위 네 이름만 쓰고, JSON `_meta.naming_map` 에 두 벌을 다 적어 둔다.

클래스
  sionna_phys 에는 **mini5pro 팔이 없다**(설계서가 2 단계 GPU 발주로 남겨 둔 자리). 그래서
  헤드라인 표는 **2 클래스(matrice4e · s1000plus)** 로만 짠다 — 네 설정이 같은 판 위에 선다.
  3 클래스 표는 ours·sionna_off·sionna_refr 만 실을 수 있고 «다른 판» 이라고 못 박는다.

채점 규약 (기존 classify_airframe.py 그대로 — 한 줄도 안 바꿈)
  겹치지 않는 16 창 × 512 자세 · 창별 DC 제거 · hanning · nfft 8192 제로패딩 ·
  빗살 ±8 Hz · AC 하한 8 Hz · 템플릿은 src/drones.py 제원에서 계산(데이터에 안 맞춘다).

필수 세 열 (설계서 §3-1)
  ① 정확도  ② 섞기 널(씨앗 5 종)  ③ 덮개율 기반 상수 예측 정확도
  — ③ 없이 «우연 아래로 갔다» 를 인용하면 틀린다. 그것은 성능 저하가 아니라 **편향된 예측**이다.

⭐판정의 두 잣대
  (1) **시계열 단위 부트스트랩 CI** — 창 단위로 세면 증거력이 부풀려진다(같은 시계열 안 16 창은
      독립이 아니다). 표본 단위는 **(기체, 앙각) 시계열**이고, 2 클래스에서 14 개뿐이다.
      창 단위 CI 를 나란히 실어 얼마나 부풀려지는지 보인다.
  (2) **R16 격자 산포 밴드** — 분류 정확도의 격자 밴드는 **0.0 %p** 다. 즉 격자는 이 잣대에
      아무 보호막도 주지 않는다 ⇒ 판정의 부담을 **전부 CI 가 진다**. 절대 dB 주장에는
      AC 밴드 3.86 dB 를 쓴다(그 안이면 «판정 불가»).

⭐«지웠나 덮었나» 를 가르는 근거 (R13 언어로)
  (a) **담김 시험** — sionna_refr 을 sionna_phys 가 계수 1 로 품고 있나(a = <e0,e1>/<e0,e0>,
      R13 과 같은 식·같은 σ). 1 이면 원래 시계열이 그대로 남아 있다는 뜻 = 지운 게 아니다.
  (b) **얹힌 항의 리듬 몫** — 잔차 r = e1 − e0 의 상한 위 빗살 몫이 백색(≈덮개율)이면
      얹힌 것은 리듬 없는 에코다.
  (c) ⭐**주입 대조군(결정적 근거)** — sionna_refr 에 **리듬 없는 백색 잡음**만 더해
      바닥을 sionna_phys 의 바닥에 맞춘 가짜 팔을 만들고 같은 분류기로 채점한다.
      가짜 팔의 성적이 sionna_phys 의 성적과 같으면, 성적 하락은 **전부 «바닥이 올라와 덮었다»**
      로 설명된다(빗살을 건드리지 않았는데 같은 성적이 나오므로).
      성적이 훨씬 좋으면 남는 몫이 «지움/변형» 이다.

스위치 단일축 팔
  굴절만·회절만·모서리만 팔은 **matrice4e 한 기체만** 있다(다른 기체 짝이 없다) ⇒ 분류 채점 불가.
  대신 (c) 에서 검증된 **가산 모형**으로 대리 채점한다 — 그 축이 matrice4e 에서 올린 바닥 상승분을
  두 클래스 모두에 같은 dB 로 얹어 채점. **측정이 아니라 대리 추정**이라고 못 박고, 대리 모형의
  검증 오차(sionna_phys 에서 잰 값)를 옆에 붙인다. 굴절 R 은 R13 이 «바꾸는 축»(담김 0.52)이라
  가산 대리가 성립하지 않으므로 대리하지 않는다 — 굴절은 실제 팔(sionna_refr)이 있다.

산출
  outputs/switch_to_classification.json
  outputs/figures/switch_classification.png   (그림 글자는 전부 영어)

실행
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/switch_to_classification.py
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np

from drones import DRONES                     # numpy/dataclass 뿐 — GPU 스택 아님

# ═══════════════════════════════════════════════════════════════════════════
# 0. 상수 · 경로 · 사전등록 문턱
# ═══════════════════════════════════════════════════════════════════════════
LEDGER_JSON = "outputs/elevation_sweep_md.json"
LEDGER_NPZ = "outputs/elevation_sweep_md.npz"
R13_JSON = "outputs/switch_factorial.json"
R16_JSON = "outputs/grid_convergence_check.json"
REF_CLASSIFY_JSON = "outputs/classify_airframe.json"     # 재현 게이트용(읽기만)
OUT_JSON = "outputs/switch_to_classification.json"
OUT_FIG = "outputs/figures/switch_classification.png"

AIRFRAMES3 = ["mini5pro", "matrice4e", "s1000plus"]
CLASSES2 = ["matrice4e", "s1000plus"]          # 헤드라인 판 — sionna_phys 에 mini5pro 없음
ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]

N_WIN, WIN_LEN, NFFT = 16, 512, 8192           # 기존 채점 규약 그대로
COMB_TOL_HZ, AC_MIN_HZ = 8.0, 8.0
NULL_SEEDS = [20260815, 20260816, 20260817, 20260818, 20260819]   # 섞기 널 5 종
INJ_SEEDS = [7001, 7002, 7003, 7004, 7005]                        # 주입 대조군 5 종
N_BOOT = 20000
BOOT_SEED = 314159
C_LIGHT = 299_792_458.0

# ⭐R16 격자 산포 밴드(2026-08-15, outputs/grid_convergence_check.json)
BAND = {
    "ac_power_db": 3.861,          # 움직이는 부분 세기
    "rhythm_share_pp": 21.819,     # 리듬 몫
    "above_f_tip_pp": 12.5549,     # 날개끝 밖 몫
    "beat_hz": 0.152,              # 박자
    "classify_accuracy_pp": 0.0,   # ⭐분류 — 밴드 0 ⇒ 격자는 보호막을 안 준다
}

# 설정 축 — 팔 이름은 원장 키를 실제로 뒤져 확인한 것이다(자가검사에서 다시 검증)
CONFIGS = {
    "ours": {
        "label_en": "Our kernel (SBR+PO)",
        "switch": None, "depth": None, "engine_ko": "우리 커널",
        "design_doc_name": "공통 기준선",
        "arms": {"mini5pro": "ours_mini5pro_r15_n8192",
                 "matrice4e": "ours_r15_n8192",
                 "s1000plus": "ours_s1000plus_r15_n8192"},
    },
    "sionna_off": {
        "label_en": "Sionna · physics OFF",
        "switch": "R0D0E0F1", "depth": 1, "engine_ko": "Sionna PathSolver · 물리 끔",
        "design_doc_name": "설정 A",
        "arms": {"mini5pro": "sionna_p4000000000_mini5pro_r15_n8192_d1",
                 "matrice4e": "sionna_p4000000000_r15_n8192_d1",
                 "s1000plus": "sionna_p4000000000_s1000plus_r15_n8192_d1"},
    },
    "sionna_refr": {
        "label_en": "Sionna · refraction only",
        "switch": "R1D0E0F1", "depth": 1, "engine_ko": "Sionna PathSolver · 굴절만",
        "design_doc_name": "설정 B",
        "arms": {"mini5pro": "sionna_p4000000000_swR1D0E0F1_mini5pro_r15_n8192_d1",
                 "matrice4e": "sionna_p4000000000_onlyrefr_r15_n8192",
                 "s1000plus": "sionna_p4000000000_swR1D0E0F1_s1000plus_r15_n8192_d1"},
    },
    "sionna_phys": {
        "label_en": "Sionna · physics ON",
        "switch": "R1D1E1F1", "depth": 1, "engine_ko": "Sionna PathSolver · 물리 켬",
        "design_doc_name": "설정 C",
        "arms": {"matrice4e": "sionna_p4000000000_phys_r15_n8192_d1",
                 "s1000plus": "sionna_p4000000000_phys_s1000plus_r15_n8192_d1"},
    },
}
CFG_ORDER = ["ours", "sionna_off", "sionna_refr", "sionna_phys"]

# 단일축 팔 — matrice4e 한 기체뿐(분류 채점 불가 ⇒ 대리 추정 전용)
SINGLE_AXIS = {
    "diffraction_only": {"arm": "sionna_p4000000000_onlydiffr_r15_n8192",
                         "switch": "R0D1E0F1", "base": "sionna_off",
                         "axis_ko": "쐐기 회절만", "label_en": "Diffraction only"},
    "edge_only": {"arm": "sionna_p4000000000_onlyedge_r15_n8192",
                  "switch": "R0D0E1F1", "base": "sionna_off",
                  "axis_ko": "모서리 회절만", "label_en": "Edge diffraction only"},
}


def kst(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")


def elkey(el: float) -> str:
    return f"el+{int(round(el))}" if el >= 0 else f"el{int(round(el))}"


# ═══════════════════════════════════════════════════════════════════════════
# 1. 잣대 — (a) 분류 점수  (b) 선/바닥 분해(R13 과 같은 식)
# ═══════════════════════════════════════════════════════════════════════════
class Scorer:
    """빗살 정합 분류기 — classify_airframe.py 의 규약을 그대로 옮긴 독립 구현."""

    def __init__(self, prf: float, cand_f: dict):
        self.prf = prf
        self.cand_f = cand_f
        self.freqs = np.fft.fftfreq(NFFT, d=1.0 / prf)
        self.ac = np.abs(self.freqs) >= AC_MIN_HZ
        self.masks = {a: self._comb(cand_f[a]) & self.ac for a in cand_f}
        self.han = np.hanning(WIN_LEN)

    def _comb(self, f: float) -> np.ndarray:
        fa = np.abs(self.freqs)
        k = np.round(fa / f)
        return (k >= 1) & (np.abs(fa - k * f) <= COMB_TOL_HZ)

    def coverage(self) -> dict:
        """백색 스펙트럼이면 빗살 몫 ≈ 이 값 — 상수 예측기의 기전."""
        n_ac = int(self.ac.sum())
        return {a: float(self.masks[a].sum()) / n_ac for a in self.masks}

    def window_scores(self, E: np.ndarray, cands: list) -> np.ndarray:
        out = np.zeros((N_WIN, len(cands)))
        for w in range(N_WIN):
            x = E[w * WIN_LEN:(w + 1) * WIN_LEN]
            x = x - x.mean()                                    # ⭐창별 DC(가만히 있는 부분) 제거
            P = np.abs(np.fft.fft(x * self.han, NFFT)) ** 2
            tot = P[self.ac].sum()
            if tot <= 0:
                continue
            for j, a in enumerate(cands):
                out[w, j] = P[self.masks[a]].sum() / tot
        return out

    def series(self, E: np.ndarray, true_a: str, cands: list) -> dict:
        sc = self.window_scores(E, cands)
        pred = sc.argmax(axis=1)
        i = cands.index(true_a)
        srt = np.sort(sc, axis=1)
        margin = sc[:, i] - np.where(pred == i, srt[:, -2], srt[:, -1])
        return {"n_correct": int((pred == i).sum()), "n_win": N_WIN,
                "acc": float((pred == i).mean()),
                "pred_counts": {c: int((pred == j).sum()) for j, c in enumerate(cands)},
                "margin_median": float(np.median(margin))}


def db(v):
    return None if (v is None or not np.isfinite(v) or v <= 0) else round(float(10 * np.log10(v)), 2)


def line_floor(E: np.ndarray, prf: float, f_flash: float, f_tip: float) -> dict:
    """⭐R13(switch_factorial.py:columns)과 같은 식 — 절대 dB 로 선/바닥을 가른다.
    다만 f_flash·f_tip 은 **그 팔의 진짜 기체 것**을 쓴다(R13 은 판 전체를 matrice4e 로 쟀다)."""
    E = np.asarray(E, complex)
    n = E.size
    x = E - E.mean()
    w = np.hanning(n)
    P = np.abs(np.fft.fft(x * w)) ** 2 / (n * np.sum(w ** 2))     # Parseval 정규화
    fr = np.fft.fftfreq(n, 1.0 / prf)
    above = np.abs(fr) >= f_tip
    k = np.round(np.abs(fr) / f_flash)
    on = np.abs(np.abs(fr) - k * f_flash) <= COMB_TOL_HZ
    m_fl, m_cb = above & ~on, above & on
    nb_f, nb_c = int(m_fl.sum()), int(m_cb.sum())
    p_fl, p_cb = float(P[m_fl].sum()), float(P[m_cb].sum())
    dens_f = p_fl / nb_f if nb_f else np.nan
    dens_c = p_cb / nb_c if nb_c else np.nan
    excess = p_cb - dens_f * nb_c
    return {
        "ac_db": db(float(np.mean(np.abs(x) ** 2))),
        "above_floor_db": db(p_fl), "above_comb_db": db(p_cb),
        "above_comb_line_db": db(excess) if excess > 0 else None,
        "comb_over_floor_db": (round(float(10 * np.log10(dens_c / dens_f)), 2)
                               if (nb_f and nb_c and dens_f > 0 and dens_c > 0) else None),
        "floor_density_db": db(dens_f),
        "floor_in_comb_bins_db": (db(dens_f * nb_c) if (nb_f and dens_f > 0) else None),
        "rhythm_share_pct": (round(100.0 * p_cb / (p_cb + p_fl), 2) if (p_cb + p_fl) > 0 else None),
        "white_expect_pct": round(100.0 * nb_c / max(nb_c + nb_f, 1), 2),
        "n_bins_comb": nb_c, "n_bins_floor": nb_f,
        "_p_floor_lin": p_fl, "_n_poses": n,
        "above_is_degenerate": bool(f_tip <= 1.0),
    }


def rhythm_share(E: np.ndarray, prf: float, f_flash: float, f_tip: float):
    """상한 위 빗살 몫 [%] — R13 rhythm_share_ref 와 같은 식."""
    E = np.asarray(E, complex)
    n = E.size
    P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / prf)
    above = np.abs(fr) >= f_tip
    k = np.round(np.abs(fr) / f_flash)
    on = np.abs(np.abs(fr) - k * f_flash) <= COMB_TOL_HZ
    tot = P[above].sum()
    return float(100.0 * P[above & on].sum() / tot) if tot > 0 else None


# ═══════════════════════════════════════════════════════════════════════════
# 2. 부트스트랩 — ⭐표본 단위는 «시계열»(창이 아니다)
# ═══════════════════════════════════════════════════════════════════════════
def boot_ci(per_series_acc: np.ndarray, rng, n_boot=N_BOOT, q=(2.5, 97.5)) -> dict:
    """시계열 단위 재표집: 시계열을 복원추출해 그 평균 정확도의 분포를 만든다."""
    n = per_series_acc.size
    idx = rng.integers(0, n, size=(n_boot, n))
    draws = per_series_acc[idx].mean(axis=1)
    lo, hi = np.percentile(draws, q)
    return {"mean": round(float(per_series_acc.mean()), 4),
            "ci_lo": round(float(lo), 4), "ci_hi": round(float(hi), 4),
            "n_series": int(n), "n_boot": int(n_boot), "unit_ko": "시계열(기체×앙각)"}


def boot_window_ci(n_correct: int, n_win: int, rng, n_boot=N_BOOT) -> dict:
    """⚠비교용 — 창을 독립 표본으로 **잘못** 취급했을 때의 CI(부풀려진 증거력)."""
    p = n_correct / n_win
    draws = rng.binomial(n_win, p, size=n_boot) / n_win
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"mean": round(float(p), 4), "ci_lo": round(float(lo), 4), "ci_hi": round(float(hi), 4),
            "n_windows": int(n_win),
            "warn_ko": "⚠창은 독립이 아니다 — 이 구간은 증거력을 부풀린다. 판정에 쓰지 않는다."}


def boot_paired_delta(acc_a: np.ndarray, acc_b: np.ndarray, rng, n_boot=N_BOOT) -> dict:
    """같은 (기체·앙각) 시계열 짝을 함께 재표집한 Δ = b − a 의 CI."""
    n = acc_a.size
    idx = rng.integers(0, n, size=(n_boot, n))
    d = (acc_b[idx] - acc_a[idx]).mean(axis=1)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"delta_pp": round(float(100 * (acc_b.mean() - acc_a.mean())), 2),
            "ci_lo_pp": round(float(100 * lo), 2), "ci_hi_pp": round(float(100 * hi), 2),
            "crosses_zero": bool(lo <= 0.0 <= hi), "n_series": int(n),
            "frac_draws_ge_zero": round(float((d >= 0).mean()), 4),
            "frac_draws_note_ko": ("한쪽 꼬리 참고값 — 사전등록 관문은 «CI 가 0 을 걸치나» 다. "
                                   "이 값은 판정에 쓰지 않고 «얼마나 아슬아슬한가» 만 보인다."),
            "boundary_ko": ("⚠구간 끝이 정확히 0 이다 — 한 팔이 천장(100 %)이라 Δ 가 0 보다 클 수 "
                            "없는 자리다. 이때 «걸친다» 는 «증거가 없다» 가 아니라 «이 표본 크기로는 "
                            "못 가른다» 로 읽는다."
                            if abs(hi) < 1e-12 or abs(lo) < 1e-12 else None)}


# ═══════════════════════════════════════════════════════════════════════════
# 3. 본체
# ═══════════════════════════════════════════════════════════════════════════
def run() -> dict:
    t0 = time.time()
    with open(LEDGER_JSON, encoding="utf-8") as f:
        led = json.load(f)
    npz = np.load(LEDGER_NPZ)
    meta = led["_meta"]
    prf = float(meta["prf_hz"])
    lam = C_LIGHT / float(meta["fc_hz"])
    rows = {(r["engine"], float(r["el_deg"])): r for r in led["rows"]}

    # ── 3-1. 템플릿(제원에서 계산 — 데이터에 안 맞춘다) ─────────────────────
    templates = {}
    for a in AIRFRAMES3:
        s = DRONES[a]
        f_flash = s.prop_blades * s.hover_rpm / 60.0
        v_tip = math.pi * (s.prop_dia_mm / 1000.0) * s.hover_rpm / 60.0
        templates[a] = {"prop_blades": s.prop_blades, "hover_rpm": s.hover_rpm,
                        "prop_dia_mm": s.prop_dia_mm,
                        "f_flash_hz_spec": round(f_flash, 3),
                        "f_tip_hz_spec_el0": round(2.0 * v_tip / lam, 1)}
    F_FLASH = {a: templates[a]["f_flash_hz_spec"] for a in AIRFRAMES3}

    sc3 = Scorer(prf, {a: F_FLASH[a] for a in AIRFRAMES3})
    sc2 = Scorer(prf, {a: F_FLASH[a] for a in CLASSES2})
    cov3, cov2 = sc3.coverage(), sc2.coverage()
    for a in AIRFRAMES3:
        templates[a]["comb_coverage_frac_3class"] = round(cov3[a], 4)
        if a in CLASSES2:
            templates[a]["comb_coverage_frac_2class"] = round(cov2[a], 4)

    # 덮개율 기반 상수 예측기 — 백색이면 이 클래스로 전부 쏠린다
    const_pred3 = max(cov3, key=cov3.get)
    const_pred2 = max(cov2, key=cov2.get)

    def series_of(cfg: str, a: str, el: float) -> np.ndarray:
        return np.asarray(npz[f"{CONFIGS[cfg]['arms'][a]}/{elkey(el)}"], complex)

    def ftip(cfg: str, a: str, el: float) -> float:
        return float(rows[(CONFIGS[cfg]["arms"][a], el)]["f_tip_hz"])

    # ── 3-2. 설정별 채점 (2 클래스 헤드라인 · 3 클래스 부차) ───────────────
    rng = np.random.default_rng(BOOT_SEED)
    tables = {}
    for tag, (cands, scorer, cov, const_pred) in {
            "two_class": (CLASSES2, sc2, cov2, const_pred2),
            "three_class": (AIRFRAMES3, sc3, cov3, const_pred3)}.items():
        per_cfg = {}
        for cfg in CFG_ORDER:
            arms = CONFIGS[cfg]["arms"]
            if not all(a in arms for a in cands):
                continue
            cells, accs, keys = {}, [], []
            per_class = {a: [] for a in cands}
            conf = np.zeros((len(cands), len(cands)), int)
            margins = []
            for a in cands:
                for el in ELS:
                    E = series_of(cfg, a, el)
                    r = scorer.series(E, a, cands)
                    lf = line_floor(E, prf, F_FLASH[a], ftip(cfg, a, el))
                    cells[f"{a}/{elkey(el)}"] = {
                        **{k: v for k, v in r.items() if not k.startswith("_")},
                        "comb_over_floor_db": lf["comb_over_floor_db"],
                        "above_floor_db": lf["above_floor_db"],
                        "above_comb_line_db": lf["above_comb_line_db"],
                        "ac_db": lf["ac_db"],
                        "rhythm_share_pct": lf["rhythm_share_pct"],
                        "f_tip_hz": round(ftip(cfg, a, el), 1),
                        "above_is_degenerate": lf["above_is_degenerate"]}
                    accs.append(r["acc"])
                    keys.append(f"{a}/{elkey(el)}")
                    per_class[a].append(r["acc"])
                    margins.append(r["margin_median"])
                    i = cands.index(a)
                    for j, c in enumerate(cands):
                        conf[i, j] += r["pred_counts"][c]
            accs = np.asarray(accs)
            n_win_tot = int(len(accs) * N_WIN)
            n_cor_tot = int(round(accs.sum() * N_WIN))

            # 섞기 널 — 씨앗 5 종
            null_accs = []
            for s in NULL_SEEDS:
                g = np.random.default_rng(s)
                v = []
                for a in cands:
                    for el in ELS:
                        E = series_of(cfg, a, el)
                        v.append(scorer.series(E[g.permutation(E.size)], a, cands)["acc"])
                null_accs.append(float(np.mean(v)))

            per_cfg[cfg] = {
                "accuracy": round(float(accs.mean()), 4),
                "bootstrap_series": boot_ci(accs, rng),
                "bootstrap_window_INFLATED": boot_window_ci(n_cor_tot, n_win_tot, rng),
                "shuffle_null_accuracy_by_seed": [round(v, 4) for v in null_accs],
                "shuffle_null_mean": round(float(np.mean(null_accs)), 4),
                "coverage_constant_predictor": {
                    "predicts": const_pred, "accuracy": round(1.0 / len(cands), 4),
                    "why_ko": f"백색이면 빗살 몫 ≈ 덮개율 → 덮개율 최대인 {const_pred} 로 전부 예측. "
                              f"균형 {len(cands)} 클래스라 정확도 = 1/{len(cands)}"},
                "per_class_recall": {a: round(float(np.mean(per_class[a])), 4) for a in cands},
                "confusion": conf.tolist(),
                "confusion_layout": "행=정답, 열=예측, 순서=classes",
                "margin_median": round(float(np.median(margins)), 4),
                "series_keys": keys,
                "per_series_acc": [round(float(v), 4) for v in accs],
                "cells": cells,
            }
        tables[tag] = {"classes": cands, "n_series_per_config": len(cands) * len(ELS),
                       "coverage_frac": {a: round(cov[a], 4) for a in cands},
                       "constant_predictor": const_pred,
                       "chance_accuracy": round(1.0 / len(cands), 4),
                       "configs": per_cfg}

    # ── 3-3. 짝 비교(같은 시계열 짝으로 재표집) ────────────────────────────
    two = tables["two_class"]["configs"]
    pair_rows = []
    order = [c for c in CFG_ORDER if c in two]
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            ka = two[a]["series_keys"]
            kb = two[b]["series_keys"]
            assert ka == kb, "시계열 키가 어긋나면 짝 재표집이 성립하지 않는다"
            d = boot_paired_delta(np.asarray(two[a]["per_series_acc"]),
                                  np.asarray(two[b]["per_series_acc"]), rng)
            band = BAND["classify_accuracy_pp"]
            inside_band = bool(abs(d["delta_pp"]) <= band)
            pair_rows.append({
                "from": a, "to": b, **d,
                "grid_band_pp": band,
                "inside_grid_band": inside_band,
                "verdict_ko": ("판정 보류 — CI 가 0 을 걸친다" if d["crosses_zero"]
                               else f"유의: {b} 가 {a} 대비 {d['delta_pp']:+.1f} %p"),
            })

    # ── 3-4. ⭐지웠나 덮었나 — 담김·잔차·주입 대조군 ────────────────────────
    burial = {"pairs": [], "note_ko": (
        "기준 팔은 **sionna_refr(굴절만)** 이다 — sionna_phys 와 «쐐기회절 D·모서리회절 E» 두 비트만 "
        "다르다. sionna_off 를 기준으로 잡으면 굴절 R 까지 함께 뒤집혀 R13 이 «바꾸는 축» 이라 부른 "
        "성분이 섞인다(담김계수 ≈0.5).")}
    inj_rows = []
    for a in CLASSES2:
        for el in ELS:
            e0 = series_of("sionna_refr", a, el)
            e1 = series_of("sionna_phys", a, el)
            e0 = e0 - e0.mean()
            e1 = e1 - e1.mean()                                  # ⭐레벨 비교는 정지성분 제거 후
            ft = ftip("sionna_phys", a, el)
            coef = np.vdot(e0, e1) / np.vdot(e0, e0)
            res = e1 - e0
            sig = float(np.linalg.norm(res) / (np.linalg.norm(e0) * np.sqrt(e0.size)))
            lf0 = line_floor(e0, prf, F_FLASH[a], ft)
            lf1 = line_floor(e1, prf, F_FLASH[a], ft)
            res_rhy = rhythm_share(res, prf, F_FLASH[a], ft)
            burial_depth = (None if (lf0["above_comb_db"] is None
                                     or lf1["floor_in_comb_bins_db"] is None)
                            else round(lf1["floor_in_comb_bins_db"] - lf0["above_comb_db"], 2))
            coef_db = float(20 * np.log10(abs(coef))) if abs(coef) > 0 else None
            burial["pairs"].append({
                "class": a, "el_deg": el,
                "contain_coeff": round(float(abs(coef)), 4),
                "contain_coeff_db": None if coef_db is None else round(coef_db, 2),
                "contain_within_grid_band": (None if coef_db is None
                                             else bool(abs(coef_db) <= BAND["ac_power_db"])),
                "contain_phase_deg": round(float(np.degrees(np.angle(coef))), 2),
                "contain_sigma": round(sig, 4),
                "contains_unit_within_3sigma": bool(sig > 0 and abs(abs(coef) - 1.0) <= 3 * sig),
                "residual_rhythm_pct": None if res_rhy is None else round(res_rhy, 2),
                "white_expect_pct": lf1["white_expect_pct"],
                "d_above_floor_db": (None if (lf0["above_floor_db"] is None
                                              or lf1["above_floor_db"] is None)
                                     else round(lf1["above_floor_db"] - lf0["above_floor_db"], 2)),
                "refr_comb_line_db": lf0["above_comb_line_db"],
                "phys_comb_line_db": lf1["above_comb_line_db"],
                "d_comb_over_floor_db": (None if (lf0["comb_over_floor_db"] is None
                                                  or lf1["comb_over_floor_db"] is None)
                                         else round(lf1["comb_over_floor_db"]
                                                    - lf0["comb_over_floor_db"], 2)),
                "burial_depth_db": burial_depth,
                "acc_refr": two["sionna_refr"]["cells"][f"{a}/{elkey(el)}"]["acc"],
                "acc_phys": two["sionna_phys"]["cells"][f"{a}/{elkey(el)}"]["acc"],
            })

            # ⭐주입 대조군 — 굴절만 팔에 «리듬 없는 백색 잡음» 만 얹어 바닥을 물리켬에 맞춘다
            p_fl_target = lf1["_p_floor_lin"]
            p_fl_base = float(abs(coef) ** 2) * lf0["_p_floor_lin"]
            n = e0.size
            nb_f = lf0["n_bins_floor"]
            need = p_fl_target - p_fl_base
            accs_i, floors_i = [], []
            for s in INJ_SEEDS:
                g = np.random.default_rng(s + int(abs(el)) * 17 + (0 if a == CLASSES2[0] else 991))
                if need > 0 and nb_f > 0:
                    sigma = math.sqrt(need * n / nb_f)
                    noise = (g.normal(size=n) + 1j * g.normal(size=n)) / math.sqrt(2.0) * sigma
                else:
                    noise = np.zeros(n, complex)
                syn = coef * e0 + noise
                accs_i.append(sc2.series(syn, a, CLASSES2)["acc"])
                floors_i.append(line_floor(syn, prf, F_FLASH[a], ft)["above_floor_db"])
            inj_rows.append({
                "class": a, "el_deg": el,
                "acc_measured_phys": two["sionna_phys"]["cells"][f"{a}/{elkey(el)}"]["acc"],
                "acc_injection_mean": round(float(np.mean(accs_i)), 4),
                "acc_injection_by_seed": [round(v, 4) for v in accs_i],
                "target_floor_db": lf1["above_floor_db"],
                "achieved_floor_db": round(float(np.mean([f for f in floors_i if f is not None])), 2),
                "floor_match_err_db": (None if lf1["above_floor_db"] is None else
                                       round(float(np.mean([f for f in floors_i if f is not None]))
                                             - lf1["above_floor_db"], 2)),
                "noise_needed": bool(need > 0),
            })

    # 담김 요약 — «1 이냐» 를 두 잣대로(엄격한 3σ · 실용적인 R16 AC 밴드) 정직하게 나눠 적는다
    cdb = [r["contain_coeff_db"] for r in burial["pairs"] if r["contain_coeff_db"] is not None]
    burial["containment_summary"] = {
        "coeff_db_min": round(float(np.min(cdb)), 2), "coeff_db_max": round(float(np.max(cdb)), 2),
        "coeff_db_median": round(float(np.median(cdb)), 2),
        "n_within_3sigma": sum(1 for r in burial["pairs"] if r["contains_unit_within_3sigma"]),
        "n_within_grid_band": sum(1 for r in burial["pairs"] if r["contain_within_grid_band"]),
        "n_pairs": len(burial["pairs"]),
        "reading_ko": (
            "⭐«정확히 1» 은 아니다 — R13 의 3σ 시험은 일부 칸에서 떨어진다. 그러나 계수는 전부 1 의 "
            "**위쪽** 근처이지 0 쪽이 아니다. 지웠다면 계수가 0 으로 가야 한다. 실용 잣대(R16 AC 밴드 "
            "3.861 dB = 계수 0.64~1.56)로는 대부분이 «1 과 구별 불가» 자리다. 밴드 밖으로 나가는 칸은 "
            "따로 적는다."),
        "outside_band_cells": [f"{r['class']}/{r['el_deg']:+.0f} ({r['contain_coeff_db']:+.1f} dB)"
                               for r in burial["pairs"] if r["contain_within_grid_band"] is False],
    }

    # 설정별 «바닥이 얼마나 올라왔나» — 물리 끔 대비 중앙값(같은 14 칸)
    floor_rise = {}
    for cfg in CFG_ORDER:
        if cfg == "sionna_off" or not all(a in CONFIGS[cfg]["arms"] for a in CLASSES2):
            floor_rise[cfg] = 0.0 if cfg == "sionna_off" else None
            continue
        vals = []
        for a in CLASSES2:
            for el in ELS:
                ft = ftip("sionna_off", a, el)
                f1 = line_floor(series_of(cfg, a, el), prf, F_FLASH[a], ft)["above_floor_db"]
                f0 = line_floor(series_of("sionna_off", a, el), prf, F_FLASH[a], ft)["above_floor_db"]
                if f1 is not None and f0 is not None:
                    vals.append(f1 - f0)
        floor_rise[cfg] = round(float(np.median(vals)), 2) if vals else None
    burial["floor_rise_vs_physics_off_db_median"] = floor_rise
    burial["floor_rise_note_ko"] = ("같은 14 칸(2 기체 × 7 앙각)에서 잰 상한 위 바닥의 중앙값 차이. "
                                    "우리 커널은 엔진이 달라 절대 눈금이 다르므로 이 칸에서 제외한다.")
    floor_rise["ours"] = None

    inj_meas = np.asarray([r["acc_measured_phys"] for r in inj_rows])
    inj_syn = np.asarray([r["acc_injection_mean"] for r in inj_rows])
    inj_delta = boot_paired_delta(inj_meas, inj_syn, rng)
    injection = {
        "what_ko": ("굴절만 팔 + «리듬 없는 백색 잡음»(바닥을 물리켬 바닥에 맞춤) → 같은 분류기로 채점. "
                    "빗살은 한 번도 건드리지 않았다."),
        "per_cell": inj_rows,
        "acc_measured_phys": round(float(inj_meas.mean()), 4),
        "acc_injection": round(float(inj_syn.mean()), 4),
        "delta_injection_minus_measured": inj_delta,
        "max_abs_cell_gap_pp": round(float(100 * np.max(np.abs(inj_syn - inj_meas))), 2),
        "n_seeds": len(INJ_SEEDS),
        "verdict_ko": None,        # 아래에서 채움
    }
    reproduces = bool(inj_delta["crosses_zero"])
    injection["verdict_ko"] = (
        "⭐**덮은 것이다** — 빗살을 건드리지 않고 바닥만 올린 가짜 팔이 물리켬의 성적을 "
        f"{abs(inj_delta['delta_pp']):.1f} %p 안에서 재현한다"
        f"(짝 CI {inj_delta['ci_lo_pp']:+.1f}~{inj_delta['ci_hi_pp']:+.1f} %p, 0 을 "
        f"{'걸친다' if reproduces else '안 걸친다'})."
        if reproduces else
        "⚠주입만으로는 물리켬 성적이 재현되지 않는다 — 바닥 상승 밖의 몫이 남는다"
        f"(Δ {inj_delta['delta_pp']:+.1f} %p, CI {inj_delta['ci_lo_pp']:+.1f}~"
        f"{inj_delta['ci_hi_pp']:+.1f} %p).")

    # ── 3-5. 단일축 팔 — 가산 모형 대리 추정(측정 아님) ─────────────────────
    single = {}
    for name, spec in SINGLE_AXIS.items():
        base_cfg = spec["base"]
        arm = spec["arm"]
        els_here = [el for el in ELS if (arm, el) in rows]
        d_floor, cells_ax = {}, {}
        rel_db = []
        for el in els_here:
            E_ax = np.asarray(npz[f"{arm}/{elkey(el)}"], complex)
            E_bs = series_of(base_cfg, "matrice4e", el)
            den = float(np.linalg.norm(E_bs))
            num = float(np.linalg.norm(E_ax - E_bs))
            rel_db.append(-400.0 if num <= 0 else round(float(20 * np.log10(num / den)), 1))
            ft = float(rows[(arm, el)]["f_tip_hz"])
            lf_ax = line_floor(E_ax, prf, F_FLASH["matrice4e"], ft)
            lf_bs = line_floor(E_bs, prf, F_FLASH["matrice4e"], ft)
            d = (None if (lf_ax["above_floor_db"] is None or lf_bs["above_floor_db"] is None)
                 else round(lf_ax["above_floor_db"] - lf_bs["above_floor_db"], 2))
            d_floor[el] = d
            cells_ax[elkey(el)] = {
                "floor_db_axis": lf_ax["above_floor_db"], "floor_db_base": lf_bs["above_floor_db"],
                "d_floor_db": d,
                "comb_over_floor_db_axis": lf_ax["comb_over_floor_db"],
                "comb_over_floor_db_base": lf_bs["comb_over_floor_db"],
                "rhythm_share_pct_axis": lf_ax["rhythm_share_pct"],
                "white_expect_pct": lf_ax["white_expect_pct"]}
        # 대리 채점 — 같은 dB 상승을 두 클래스 모두에 얹는다
        accs_sur, per_cell = [], []
        for a in CLASSES2:
            for el in els_here:
                if d_floor[el] is None or d_floor[el] <= 0:
                    continue
                E = series_of(base_cfg, a, el)
                E = E - E.mean()
                ft_a = ftip(base_cfg, a, el)
                lf = line_floor(E, prf, F_FLASH[a], ft_a)
                need = lf["_p_floor_lin"] * (10 ** (d_floor[el] / 10.0) - 1.0)
                vals = []
                for s in INJ_SEEDS:
                    g = np.random.default_rng(s + 50000 + int(abs(el)) * 13
                                              + (0 if a == CLASSES2[0] else 777))
                    sigma = math.sqrt(need * E.size / max(lf["n_bins_floor"], 1))
                    noise = (g.normal(size=E.size) + 1j * g.normal(size=E.size)) / math.sqrt(2.0) * sigma
                    vals.append(sc2.series(E + noise, a, CLASSES2)["acc"])
                accs_sur.append(float(np.mean(vals)))
                per_cell.append({"class": a, "el_deg": el, "d_floor_db": d_floor[el],
                                 "acc_surrogate": round(float(np.mean(vals)), 4)})
        is_noop = bool(rel_db and max(rel_db) <= -100.0)      # 수치 바닥 아래 = 사실상 같은 시계열
        base_acc = tables["two_class"]["configs"][base_cfg]["accuracy"]
        single[name] = {
            "arm": arm, "switch": spec["switch"], "axis_ko": spec["axis_ko"],
            "label_en": spec["label_en"],
            "elevations_available": els_here,
            "airframes_available": ["matrice4e"],
            "why_not_scored_ko": ("이 팔은 matrice4e 한 기체만 있다 — 같은 설정의 다른 기체 팔이 없어 "
                                  "분류 채점 자체가 성립하지 않는다."),
            "cells_matrice4e": cells_ax,
            "is_noop_vs_base": is_noop,
            "rel_diff_db_vs_base": rel_db,
            "noop_note_ko": (f"⭐이 스위치는 **아무것도 안 바꾼다** — 기준 팔과의 차이가 "
                             f"{max(rel_db):.0f} dB(모든 앙각)로 수치 바닥 아래다. R13 의 "
                             f"«모서리 회절은 무동작» 과 같은 결론이다. 그러므로 대리 추정도 필요 "
                             f"없다: 성적 = 기준 팔의 **측정값** 그대로."
                             if is_noop else None),
            "d_floor_db_median": (None if not [v for v in d_floor.values() if v is not None]
                                  else round(float(np.median([v for v in d_floor.values()
                                                              if v is not None])), 2)),
            "surrogate_accuracy_2class": (round(base_acc, 4) if is_noop else
                                          (None if not accs_sur
                                           else round(float(np.mean(accs_sur)), 4))),
            "surrogate_is_measured": is_noop,
            "surrogate_per_cell": per_cell,
            "surrogate_status_ko": ("무동작 스위치라 기준 팔의 **측정값** 그대로다." if is_noop else
                                    "⚠**측정이 아니라 대리 추정**이다 — matrice4e 에서 잰 바닥 상승분을 "
                                    "두 클래스에 같은 dB 로 얹은 가산 모형의 결과다. 모형의 검증 오차는 "
                                    "injection_control (물리켬 재현 오차) 에 있다."),
        }

    # ── 3-6. 번역 곡선 — 성적은 «빗살 선 대 바닥» 의 번역인가 ───────────────
    tx = {"points": [], "note_ko": (
        "가로축은 그 시계열 자신의 «선/바닥 대비»(진짜 기체의 f_flash·f_tip 으로 잰 값), "
        "세로축은 그 시계열의 창 16 개 정확도. 네 설정 전부를 한 판에 얹는다.")}
    for cfg in CFG_ORDER:
        if cfg not in two:
            continue
        for key, c in two[cfg]["cells"].items():
            a = key.split("/")[0]
            if c["comb_over_floor_db"] is None:
                continue
            tx["points"].append({"config": cfg, "class": a, "cell": key,
                                 "contrast_db": c["comb_over_floor_db"], "acc": c["acc"],
                                 "margin_median": c["margin_median"],
                                 "degenerate_f_tip": c["above_is_degenerate"]})
    xs = np.asarray([p["contrast_db"] for p in tx["points"]])
    ys = np.asarray([p["acc"] for p in tx["points"]])
    ms = np.asarray([p["margin_median"] for p in tx["points"]])
    cl = np.asarray([p["class"] for p in tx["points"]])

    def spearman(x, y):
        rx = np.argsort(np.argsort(x)).astype(float)
        ry = np.argsort(np.argsort(y)).astype(float)
        rx -= rx.mean(); ry -= ry.mean()
        return float((rx @ ry) / math.sqrt((rx @ rx) * (ry @ ry)))

    def thresholds(x, y):
        pf, im = x[y >= 1.0], x[y < 1.0]
        return {"n": int(x.size),
                "min_contrast_db_among_perfect": round(float(pf.min()), 2) if pf.size else None,
                "max_contrast_db_among_imperfect": round(float(im.max()), 2) if im.size else None,
                "overlap_band_db": ([round(float(pf.min()), 2), round(float(im.max()), 2)]
                                    if (pf.size and im.size and pf.min() < im.max()) else None),
                "clean_separation": bool(pf.size and im.size and pf.min() > im.max())}

    tx["spearman_contrast_vs_accuracy"] = {"all": round(spearman(xs, ys), 4)}
    tx["spearman_contrast_vs_margin"] = {"all": round(spearman(xs, ms), 4)}
    tx["thresholds"] = {"all": thresholds(xs, ys)}
    for a in CLASSES2:
        m = cl == a
        tx["spearman_contrast_vs_accuracy"][a] = round(spearman(xs[m], ys[m]), 4)
        tx["spearman_contrast_vs_margin"][a] = round(spearman(xs[m], ms[m]), 4)
        tx["thresholds"][a] = thresholds(xs[m], ys[m])
    tx["margin_note_ko"] = ("⭐정확도는 대부분의 칸에서 100 % 에 붙어 있어(천장) 순위상관이 낮게 나온다. "
                            "천장이 없는 연속 잣대인 **판정 여유**(정답 몫 − 차점 몫)로 다시 재면 "
                            "번역이 훨씬 또렷하다 — 아래 spearman_contrast_vs_margin 을 볼 것.")
    tx["bias_caveat_ko"] = (
        "⭐두 클래스의 곡선이 다르다 — 덮개율이 큰 matrice4e 는 대비가 0 dB 로 무너져도 성적이 높게 "
        "남는다(상수 예측기가 그 클래스를 찍기 때문). 번역이 깨끗한 쪽은 **불리한 클래스 s1000plus** 다. "
        "그래서 «전체» 순위상관을 헤드라인으로 쓰면 안 되고, 반드시 클래스별로 읽어야 한다.")

    payload = {
        "_meta": {
            "generator": "benchmark/switch_to_classification.py",
            "experiment": "R14 · 엔진 설정 → 기체 분류 성적",
            "design_doc": "docs/NEXT_EXPERIMENTS.md §② 순위 6 · §3-1 R14",
            "generated_kst": kst(time.time()),
            "gpu_used": False,
            "gpu_note_ko": "⛔sionna.rt·mitsuba 임포트 없음 — 저장된 원장만 읽는 CPU 분석",
            "question_ko": "엔진 물리 설정을 켜고 끄면 기체 분류 성적이 얼마나 달라지고, 그 차이의 기전은 무엇인가",
            "naming_map": {
                "ours": {"task_prompt": "(A) 우리 커널", "design_doc": "공통 기준선"},
                "sionna_off": {"task_prompt": "(B) Sionna 물리 끔", "design_doc": "설정 A · R0D0E0F1·d1"},
                "sionna_refr": {"task_prompt": "(중간) 굴절만", "design_doc": "설정 B · R1D0E0F1·d1"},
                "sionna_phys": {"task_prompt": "(C) Sionna 물리 켬", "design_doc": "설정 C · R1D1E1F1·d1"},
                "warn_ko": "과제문 A/B/C 와 설계서 A/B/C 가 어긋난다 — 인용할 때 이 표를 함께 붙일 것",
            },
            "switch_meaning_ko": {"R": "굴절", "D": "쐐기 회절", "E": "모서리 회절", "F": "확산 반사"},
            "provenance": {
                "ledger_json": {"path": LEDGER_JSON, "mtime": kst(os.path.getmtime(LEDGER_JSON)),
                                "n_rows": len(led["rows"])},
                "ledger_npz": {"path": LEDGER_NPZ, "mtime": kst(os.path.getmtime(LEDGER_NPZ)),
                               "n_keys": len(npz.files)},
                "r13": {"path": R13_JSON, "mtime": kst(os.path.getmtime(R13_JSON))},
                "r16_bands": {"path": R16_JSON, "mtime": kst(os.path.getmtime(R16_JSON))},
                "reference_classifier": {"path": REF_CLASSIFY_JSON,
                                         "mtime": kst(os.path.getmtime(REF_CLASSIFY_JSON)),
                                         "role_ko": "재현 게이트(읽기 전용) — 3 클래스 성적이 같아야 한다"},
                "templates_from": "src/drones.py DRONES (제원 계산 — 데이터에 맞추지 않음)",
                "npz_keys_used": sorted({f"{CONFIGS[c]['arms'][a]}/{elkey(e)}"
                                         for c in CFG_ORDER for a in CONFIGS[c]["arms"]
                                         for e in ELS}
                                        | {f"{s['arm']}/{elkey(e)}" for s in SINGLE_AXIS.values()
                                           for e in ELS if (s["arm"], e) in rows}),
            },
            "prf_hz": prf, "fc_hz": float(meta["fc_hz"]), "lambda_m": round(lam, 6),
            "range_m": 15.0, "az_deg": 0.0,
            "range_note_ko": "네 설정 전부 15 m · 방위 0° — 원거리장 경계 2D²/λ ≈ 14.08 m 의 밖",
            "recipe_ko": ("겹치지 않는 16 창 × 512 자세 · 창별 DC 제거 · hanning · nfft 8192 · "
                          "빗살 ±8 Hz · AC 하한 8 Hz · argmax 예측. classify_airframe.py 규약 그대로."),
            "line_floor_recipe_ko": ("R13(switch_factorial.py:columns)과 같은 식. 다만 f_flash·f_tip 은 "
                                     "그 팔의 진짜 기체 것을 쓴다 — R13 은 판 전체를 matrice4e 로 쟀다."),
            "dc_rule_ko": "⭐모든 레벨·에너지 비교는 정지성분(시계열 평균) 제거 후. 마이크로도플러는 STFT 만.",
            "grid_bands_r16": BAND,
            "grid_band_use_ko": ("분류 정확도의 격자 밴드는 **0.0 %p** 다 — 격자는 이 잣대에 보호막을 "
                                 "주지 않는다. 그래서 판정의 부담을 전부 부트스트랩 CI 가 진다. "
                                 "절대 dB 주장에는 AC 밴드 3.861 dB 를 쓴다."),
            "bootstrap_ko": ("⭐표본 단위는 «시계열(기체×앙각)». 창 단위로 세면 같은 시계열 안 16 창이 "
                             "독립이 아니라 증거력이 부풀려진다 — 부풀린 값도 "
                             "`bootstrap_window_INFLATED` 에 나란히 실어 비교한다."),
            "null_seeds": NULL_SEEDS, "injection_seeds": INJ_SEEDS,
            "n_boot": N_BOOT, "boot_seed": BOOT_SEED,
            "el_minus90_note_ko": ("−90°(직하방)는 f_tip=0 이라 «상한 위» 가 전 대역이 된다. 물리적으로 "
                                   "날개 속도가 시선에 수직이라 마이크로도플러가 원리적으로 사라지는 "
                                   "앙각이다 — 그 칸의 성적은 잔결 구조만 시험한다."),
            "elapsed_s": None,
        },
        "configs": {c: {k: v for k, v in CONFIGS[c].items()} for c in CFG_ORDER},
        "templates": templates,
        "tables": tables,
        "pairwise_paired_bootstrap": pair_rows,
        "burial_vs_erasure": burial,
        "injection_control": injection,
        "single_axis": single,
        "translation_curve": tx,
    }
    payload["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# 4. 판정문
# ═══════════════════════════════════════════════════════════════════════════
def verdict(p: dict) -> dict:
    two = p["tables"]["two_class"]["configs"]
    chance = p["tables"]["two_class"]["chance_accuracy"]
    band = BAND["classify_accuracy_pp"]

    def line(cfg):
        r = two[cfg]
        b = r["bootstrap_series"]
        above_const = b["ci_lo"] > chance
        return {
            "config": cfg, "label_en": CONFIGS[cfg]["label_en"],
            "accuracy_pct": round(100 * r["accuracy"], 2),
            "ci95_series_pct": [round(100 * b["ci_lo"], 2), round(100 * b["ci_hi"], 2)],
            "ci95_window_INFLATED_pct": [round(100 * r["bootstrap_window_INFLATED"]["ci_lo"], 2),
                                         round(100 * r["bootstrap_window_INFLATED"]["ci_hi"], 2)],
            "shuffle_null_pct": round(100 * r["shuffle_null_mean"], 2),
            "coverage_constant_pct": round(100 * r["coverage_constant_predictor"]["accuracy"], 2),
            "per_class_recall_pct": {k: round(100 * v, 2) for k, v in r["per_class_recall"].items()},
            "beats_constant_predictor": bool(above_const),
            "verdict_ko": ("상수 예측선 위 — 빗살 정보가 남아 있다" if above_const
                           else "⚠상수 예측선을 CI 가 걸친다 — «맞혔다» 고 못 쓴다(판정 보류)"),
        }

    rows = [line(c) for c in CFG_ORDER if c in two]
    phys = two["sionna_phys"]
    refr = two["sionna_refr"]
    d_rp = next(r for r in p["pairwise_paired_bootstrap"]
                if r["from"] == "sionna_refr" and r["to"] == "sionna_phys")
    d_op = next(r for r in p["pairwise_paired_bootstrap"]
                if r["from"] == "sionna_off" and r["to"] == "sionna_phys")
    d_or = next(r for r in p["pairwise_paired_bootstrap"]
                if r["from"] == "sionna_off" and r["to"] == "sionna_refr")
    d_uo = next(r for r in p["pairwise_paired_bootstrap"]
                if r["from"] == "ours" and r["to"] == "sionna_off")

    bp = p["burial_vs_erasure"]["pairs"]
    cs = p["burial_vs_erasure"]["containment_summary"]
    n_contain = sum(1 for r in bp if r["contains_unit_within_3sigma"])
    rhy = [r["residual_rhythm_pct"] for r in bp if r["residual_rhythm_pct"] is not None]
    dfl = [r["d_above_floor_db"] for r in bp if r["d_above_floor_db"] is not None]
    dcon = [r["d_comb_over_floor_db"] for r in bp if r["d_comb_over_floor_db"] is not None]
    bur = [r["burial_depth_db"] for r in bp if r["burial_depth_db"] is not None]
    inj = p["injection_control"]

    # 사전등록된 2 단계 발주 관문 (설계서 §④): «2 클래스 65 % 미만이면 발주»
    gate_lo = phys["bootstrap_series"]["ci_lo"]
    gate_hi = phys["bootstrap_series"]["ci_hi"]
    gate_undecided = bool(gate_lo <= 0.65 <= gate_hi)

    v = {
        "headline_ko": [
            f"⭐엔진 물리를 켜는 값은 **{abs(d_rp['delta_pp']):.1f} %p**다 — 같은 2 클래스 판에서 "
            f"굴절만 {100 * refr['accuracy']:.1f} % → 물리 켬 {100 * phys['accuracy']:.1f} % "
            f"(짝 CI {d_rp['ci_lo_pp']:+.1f}~{d_rp['ci_hi_pp']:+.1f} %p, 0 을 "
            f"{'걸친다 ⇒ 판정 보류' if d_rp['crosses_zero'] else '안 걸친다 ⇒ 유의'}).",
            f"⭐**이 성적은 빗살 선 대 바닥의 번역이다** — 덮개율이 불리한 클래스(s1000plus)에서 "
            f"선/바닥 대비가 "
            f"{p['translation_curve']['thresholds']['s1000plus']['max_contrast_db_among_imperfect']:.1f} dB "
            f"를 넘는 시계열은 **전부 100 %**, "
            f"{p['translation_curve']['thresholds']['s1000plus']['min_contrast_db_among_perfect']:.1f} dB "
            f"아래는 **한 칸도 100 % 가 아니다**. 대비 ↔ 판정 여유 순위상관 "
            f"{p['translation_curve']['spearman_contrast_vs_margin']['s1000plus']:+.2f} "
            f"(전체 {p['translation_curve']['spearman_contrast_vs_margin']['all']:+.2f}).",
            f"⭐성적이 떨어진 것은 «날개 신호가 사라져서» 가 아니라 «바닥이 올라와 덮여서» 다 — "
            f"빗살을 한 번도 건드리지 않고 바닥만 물리켬 높이로 올린 가짜 팔이 물리켬 성적을 "
            f"{abs(inj['delta_injection_minus_measured']['delta_pp']):.1f} %p 안에서 재현한다.",
            f"⚠물리 켬의 성적은 **클래스가 갈린다** — matrice4e "
            f"{100 * phys['per_class_recall']['matrice4e']:.1f} % ↔ s1000plus "
            f"{100 * phys['per_class_recall']['s1000plus']:.1f} %. 앞의 숫자는 실력이 아니라 "
            f"덮개율 편향(상수 예측기가 찍는 클래스)이다.",
        ],
        "table_two_class": rows,
        "engine_cost_ko": {
            "ours_to_physics_off_pp": d_uo["delta_pp"],
            "physics_off_to_refraction_pp": d_or["delta_pp"],
            "refraction_to_physics_on_pp": d_rp["delta_pp"],
            "physics_off_to_physics_on_pp": d_op["delta_pp"],
            "reading_ko": ("굴절 축(R)은 성적을 거의 안 물린다(CI 가 0 을 걸친다). 값을 물리는 것은 "
                           "굴절만 → 물리 켬 한 걸음이다."),
        },
        "which_switch_ko": {
            "diffraction_only_surrogate_pct": (
                None if p["single_axis"]["diffraction_only"]["surrogate_accuracy_2class"] is None
                else round(100 * p["single_axis"]["diffraction_only"]["surrogate_accuracy_2class"], 2)),
            "edge_only_is_noop": p["single_axis"]["edge_only"]["is_noop_vs_base"],
            "edge_only_rel_diff_db": max(p["single_axis"]["edge_only"]["rel_diff_db_vs_base"]),
            "statement_ko": (
                f"⭐범인은 **쐐기 회절(D)** 하나다. 모서리 회절(E) 팔은 기준 팔과 차이가 "
                f"{max(p['single_axis']['edge_only']['rel_diff_db_vs_base']):.0f} dB — 수치 바닥 "
                f"아래라 **아무것도 안 바꾼다**(무동작). 쐐기 회절이 matrice4e 에서 올린 바닥 상승분"
                f"(중앙값 {p['single_axis']['diffraction_only']['d_floor_db_median']:+.1f} dB)을 "
                f"두 클래스에 그대로 얹은 대리 판은 "
                f"{100 * p['single_axis']['diffraction_only']['surrogate_accuracy_2class']:.1f} % 로, "
                f"실제 물리켬 {100 * phys['accuracy']:.1f} % 자리에 떨어진다."),
            "caveat_ko": ("대리 판은 «측정» 이 아니다 — 그 설정에 다른 기체 팔이 없어서 쓴 가산 모형이고, "
                          "모형의 검증 오차는 물리켬 재현 오차"
                          f"({inj['delta_injection_minus_measured']['delta_pp']:+.1f} %p)로 잰다."),
        },
        "mechanism_ko": {
            "claim": "덮었다(지운 게 아니다)",
            "evidence_1_containment_ko": (
                f"담김 시험 — 물리켬이 굴절만 팔을 계수 1 로 품고 있나: 담김계수는 "
                f"{cs['coeff_db_min']:+.1f}~{cs['coeff_db_max']:+.1f} dB(중앙값 "
                f"{cs['coeff_db_median']:+.1f} dB)로 전부 **1 의 위쪽 근처**다. R13 의 엄격한 3σ "
                f"시험은 {n_contain}/{len(bp)} 칸만 통과하지만(즉 «정확히 1» 은 아니다), R16 AC "
                f"밴드(±3.86 dB = 계수 0.64~1.56)로는 {cs['n_within_grid_band']}/{len(bp)} 칸이 "
                f"1 과 구별되지 않는다. **지웠다면 계수가 0 쪽으로 가야 한다** — 그 반대다."),
            "evidence_2_white_residual_ko": (
                f"얹힌 항 r = 물리켬 − 굴절만 의 상한 위 빗살 몫은 {min(rhy):.1f}~{max(rhy):.1f} % 로 "
                f"백색 기대치({bp[0]['white_expect_pct']:.1f} %) 자리다 — 리듬이 없는 에코다."),
            "evidence_3_floor_up_ko": (
                f"바닥은 {min(dfl):+.1f}~{max(dfl):+.1f} dB 오르고(중앙값 {np.median(dfl):+.1f} dB) "
                f"선/바닥 대비는 중앙값 {np.median(dcon):+.1f} dB 로 무너진다. 원래 빗살이 새 바닥 밑으로 "
                f"잠기는 깊이는 중앙값 {np.median(bur):+.1f} dB(최대 {max(bur):+.1f} dB)이며, "
                f"{sum(1 for v in bur if v < 0)} 칸은 음수 = 안 잠긴 칸이다 — 그 칸들은 성적도 안 떨어진다."),
            "evidence_4_injection_ko": inj["verdict_ko"],
            "what_would_have_falsified_ko": (
                "① 담김계수가 1 에서 벗어나거나 ② 잔차가 백색이 아니거나 ③ 바닥만 올린 가짜 팔이 "
                "물리켬보다 훨씬 잘 맞혔다면, «덮었다» 가 아니라 «지웠다/바꿨다» 가 된다."),
        },
        "translation_statement_ko": (
            "⭐**이 성적은 빗살 신호 대 바닥의 번역이다.** 분류기는 창마다 «상한 위 빗살 몫» 을 재서 "
            "제일 큰 후보를 찍는다. 얹힌 리듬 없는 에코는 분자를 줄이지 않고 **분모를 키운다** — "
            "그래서 대비가 무너지면 몫이 전부 덮개율 쪽으로 수렴하고, 예측은 덮개율이 큰 클래스로 쏠린다. "
            "설정 사이의 정확도 차이는 물리의 «옳고 그름» 이 아니라 그 대비가 몇 dB 남았는지의 번역이다."),
        "grid_band_note_ko": (
            f"R16 격자 밴드는 분류 정확도에서 {band} %p 다 — 즉 격자 산포로 설명되는 몫이 없다. "
            "그래서 «밴드 안이라 판정 불가» 로 빠져나갈 자리가 없고, 판정의 부담은 전부 "
            "시계열 단위 CI 가 진다. 절대 dB 주장(바닥 상승·대비 붕괴)은 AC 밴드 3.861 dB 밖이다."),
        "undecided_ko": [],
        "prereg_stage2_gate": {
            "rule_ko": "설계서 §④ — «1 단계에서 설정 C 가 2 클래스 65 % 미만일 때만 2 단계(mini5pro 물리켬, "
                       "14~21 GPU-h) 발주»",
            "measured_pct": round(100 * phys["accuracy"], 2),
            "ci95_series_pct": [round(100 * gate_lo, 2), round(100 * gate_hi, 2)],
            "decision_ko": ("⚠**판정 보류 — 발주하지 않는다(지금은)**: 점추정 "
                            f"{100 * phys['accuracy']:.1f} % 는 65 % 위지만 시계열 단위 95 % 구간 "
                            f"{100 * gate_lo:.1f}~{100 * gate_hi:.1f} % 가 65 % 를 걸친다. "
                            "14 개 시계열로는 이 관문을 못 가른다 — 관문을 가르려면 표본(기체·앙각·방위)을 "
                            "늘려야지 GPU 를 더 태울 일이 아니다."
                            if gate_undecided else
                            (f"발주 조건 성립(상한 {100 * gate_hi:.1f} % < 65 %)"
                             if gate_hi < 0.65 else
                             f"발주 조건 불성립(하한 {100 * gate_lo:.1f} % > 65 %)")),
            "undecided": gate_undecided,
        },
        "scope_ko": [
            "방위 0° · 거리 15 m · 앙각 7 점 한정 — R12 가 방위 불변이 아님을 보였으므로 다른 방위로 "
            "옮겨 인용하지 않는다.",
            "sionna_phys 에 mini5pro 팔이 없어 헤드라인은 **2 클래스**다. 3 클래스 표(ours·물리끔·굴절만)는 "
            "다른 판이며 두 표의 숫자를 나란히 빼지 않는다.",
            "분류기는 학습기가 아니라 **제원 템플릿 정합**이다 — 여기 성적은 «규칙 분류기 기준» 이고 "
            "학습 기반 분류기로 옮겨 인용하지 않는다.",
            "단일축(회절만·모서리만) 숫자는 **대리 추정**이다 — 그 설정에 다른 기체 팔이 없다.",
        ],
    }
    for r in rows:
        if not r["beats_constant_predictor"]:
            v["undecided_ko"].append(
                f"{r['config']}: 정확도 CI {r['ci95_series_pct'][0]:.1f}~{r['ci95_series_pct'][1]:.1f} % 가 "
                f"상수 예측선 {r['coverage_constant_pct']:.1f} % 를 걸친다 ⇒ **판정 보류**")
    for pr in p["pairwise_paired_bootstrap"]:
        if pr["crosses_zero"]:
            v["undecided_ko"].append(
                f"{pr['from']} → {pr['to']}: Δ {pr['delta_pp']:+.1f} %p, CI "
                f"{pr['ci_lo_pp']:+.1f}~{pr['ci_hi_pp']:+.1f} %p 가 0 을 걸친다 ⇒ **판정 보류**")
    if gate_undecided:
        v["undecided_ko"].append(v["prereg_stage2_gate"]["decision_ko"])
    if not v["undecided_ko"]:
        v["undecided_ko"].append("없음 — 실린 판정은 모두 CI 가 문턱을 안 걸친다")
    return v


def corrections_of(p: dict, v: dict) -> list:
    two = p["tables"]["two_class"]["configs"]
    three = p["tables"]["three_class"]["configs"]
    phys = two["sionna_phys"]
    inj = p["injection_control"]
    d_rp = next(r for r in p["pairwise_paired_bootstrap"]
                if r["from"] == "sionna_refr" and r["to"] == "sionna_phys")
    return [
        {
            "where": "docs/RESUME.md:25 (분석 ① 분류 첫 실험)",
            "old": "PathSolver 팔 94.64 %(혼동은 mini5pro→matrice4e 13, s1000plus→matrice4e 5)",
            "new": (f"PathSolver **물리 끔** 팔 94.64 % (3 클래스). ⚠«PathSolver» 라고만 쓰면 안 된다 — "
                    f"같은 2 클래스 판에서 물리 끔 {100 * two['sionna_off']['accuracy']:.1f} % ↔ "
                    f"물리 켬 {100 * phys['accuracy']:.1f} % 다."),
            "why_ko": ("원장의 «sionna» 표준 팔은 R0D0E0F1(물리 스위치 전부 끔)이다. 엔진 이름만 붙여 "
                       "인용하면 «PathSolver 는 94.6 % 로 분류한다» 로 읽히는데, 물리를 켜면 그 성적이 "
                       "아니다. 엔진 이름 옆에 스위치 상태를 반드시 붙인다."),
            "evidence": "outputs/switch_to_classification.json · tables.two_class.configs",
        },
        {
            "where": "docs/NEXT_EXPERIMENTS.md §② 순위 6 (R14 판정 기준 문장)",
            "old": "«회절이 얹은 바닥이 빗살을 21.5 dB 아래로 묻었다» 의 번역이다",
            "new": (f"«회절이 얹은 바닥이 빗살을 덮었다» 의 번역이다 — 묻힌 깊이는 **한 값이 아니라 "
                    f"칸마다 갈린다**: 분류 판 14 칸에서 중앙값 "
                    f"{np.median([r['burial_depth_db'] for r in p['burial_vs_erasure']['pairs'] if r['burial_depth_db'] is not None]):+.1f} dB · "
                    f"최대 "
                    f"{max(r['burial_depth_db'] for r in p['burial_vs_erasure']['pairs'] if r['burial_depth_db'] is not None):+.1f} dB, "
                    f"그리고 "
                    f"{sum(1 for r in p['burial_vs_erasure']['pairs'] if r['burial_depth_db'] is not None and r['burial_depth_db'] < 0)} 칸은 "
                    f"음수(= 안 묻힌 칸)다"),
            "why_ko": ("21.5 dB 는 R13 이 **el −30 · matrice4e 한 칸**에서 잰 값이다. 분류 판(2 기체 × "
                       "7 앙각)에서 다시 재면 칸마다 크게 다르고(음수 칸도 있다), 성적이 무너지는 칸은 "
                       "묻힌 깊이가 큰 칸이다. 한 칸 숫자를 판 전체의 값으로 인용하지 않는다."),
            "evidence": "outputs/switch_to_classification.json · burial_vs_erasure.pairs[].burial_depth_db",
        },
        {
            "where": "분류 성적을 인용하는 모든 자리 (설정 C 를 «성능 저하» 로 읽는 문장)",
            "old": "물리를 켜면 분류 성능이 떨어진다",
            "new": (f"물리를 켜면 분류 성적이 {100 * two['sionna_refr']['accuracy']:.1f} % → "
                    f"{100 * phys['accuracy']:.1f} % 로 내려가는데, 이는 **클래스 쏠림**이다 — "
                    f"matrice4e {100 * phys['per_class_recall']['matrice4e']:.1f} % ↔ s1000plus "
                    f"{100 * phys['per_class_recall']['s1000plus']:.1f} %. 덮개율이 큰 클래스로 "
                    f"예측이 쏠린 결과이지 두 클래스가 고르게 나빠진 것이 아니다."),
            "why_ko": ("평균만 인용하면 «조금 나빠졌다» 로 읽힌다. 실제로는 한 클래스가 거의 안 맞고 "
                       "다른 클래스가 상수 예측 덕에 높게 나온 것이라, 운용 의미가 전혀 다르다."),
            "evidence": "outputs/switch_to_classification.json · tables.two_class.configs.sionna_phys.per_class_recall",
        },
        {
            "where": "R14 서술 언어 (설계서가 예고한 «회절이 빗살을 지웠다» 표현)",
            "old": "회절이 빗살을 지워 분류가 무너진다",
            "new": (f"회절이 **리듬 없는 에코를 얹어** 빗살을 덮어 분류가 무너진다 — 빗살을 안 건드리고 "
                    f"바닥만 같은 높이로 올린 가짜 팔이 물리켬 성적을 "
                    f"{abs(inj['delta_injection_minus_measured']['delta_pp']):.1f} %p 안에서 재현한다"
                    f"(짝 CI {inj['delta_injection_minus_measured']['ci_lo_pp']:+.1f}~"
                    f"{inj['delta_injection_minus_measured']['ci_hi_pp']:+.1f} %p)."),
            "why_ko": ("R13 이 신호층에서 세운 «덮는다» 를 이번에 **태스크층에서 직접 시험**했다. "
                       "기전이 다르면 처방이 다르다 — 지웠다면 회절 모형을 고쳐야 하고, 덮었다면 "
                       "얹힌 항의 절대 크기(또는 그것을 빼는 처리)가 손잡이다."),
            "evidence": "outputs/switch_to_classification.json · injection_control",
        },
        {
            "where": "3 클래스 성적을 설정 축 비교에 쓰는 자리",
            "old": f"3 클래스 정확도로 엔진 설정을 비교한다 (ours 100 % · 물리끔 "
                   f"{100 * three['sionna_off']['accuracy']:.2f} %)",
            "new": ("설정 축 비교는 **2 클래스 판**에서만 한다 — sionna_phys 에 mini5pro 팔이 없어 "
                    "3 클래스로는 물리 켬을 채점할 수 없다. 3 클래스 숫자와 2 클래스 숫자를 빼면 안 된다."),
            "why_ko": "클래스 수가 다르면 우연선(1/3 ↔ 1/2)도 상수 예측선도 달라진다.",
            "evidence": "outputs/switch_to_classification.json · tables.three_class (configs 에 sionna_phys 없음)",
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════
# 5. 그림 (글자는 전부 영어)
# ═══════════════════════════════════════════════════════════════════════════
def make_figure(p: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    INK, INK2, GRID = "#0b0b0b", "#52514e", "#d8d7d3"
    BLUE, ORANGE, GREEN, PURPLE, RED = "#2a78d6", "#eb6834", "#2e8b57", "#7a5cc4", "#c0392b"
    CFG_COL = {"ours": GREEN, "sionna_off": BLUE, "sionna_refr": PURPLE, "sionna_phys": ORANGE}
    CFG_LBL = {"ours": "Our kernel", "sionna_off": "Sionna\nphysics OFF",
               "sionna_refr": "Sionna\nrefraction only", "sionna_phys": "Sionna\nphysics ON"}
    CLS_LBL = {"matrice4e": "Matrice 4E", "s1000plus": "S1000+"}
    CLS_COL = {"matrice4e": BLUE, "s1000plus": RED}

    two = p["tables"]["two_class"]["configs"]
    order = [c for c in CFG_ORDER if c in two]
    chance = p["tables"]["two_class"]["chance_accuracy"]

    fig = plt.figure(figsize=(15.6, 9.6), dpi=155)
    gs = fig.add_gridspec(2, 3, left=0.058, right=0.985, top=0.845, bottom=0.075,
                          hspace=0.44, wspace=0.30)
    fig.suptitle("What engine physics settings cost the airframe-classification task",
                 fontsize=15.5, fontweight="bold", color=INK, y=0.975)
    fig.text(0.058, 0.925,
             "Same comb-template classifier (16 non-overlapping windows x 512 poses, per-window DC removal, "
             "nfft 8192, +/-8 Hz comb, templates from airframe specs).\n"
             "Two classes (Matrice 4E, S1000+) so that all four engine settings sit on one plate — the "
             "physics-ON arm has no Mini 5 Pro run. Range 15 m, azimuth 0, 7 elevations.",
             fontsize=9.0, color=INK2, va="top")

    def clean(ax):
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8.5, length=3)
        ax.grid(color=GRID, lw=0.6, alpha=0.75, axis="y")
        ax.set_axisbelow(True)

    # ── (a) 설정별 정확도 + 시계열 CI(굵게) vs 창 CI(가늘게) ────────────────
    ax = fig.add_subplot(gs[0, 0])
    xs = np.arange(len(order))
    for i, c in enumerate(order):
        r = two[c]
        acc = 100 * r["accuracy"]
        bs, bw = r["bootstrap_series"], r["bootstrap_window_INFLATED"]
        ax.bar(i, acc, width=0.56, color=CFG_COL[c], alpha=0.9,
               label="Accuracy" if i == 0 else None)
        ax.plot([i, i], [100 * bs["ci_lo"], 100 * bs["ci_hi"]], color=INK, lw=2.6, solid_capstyle="butt",
                label="95% CI, time-series unit" if i == 0 else None)
        ax.plot([i + 0.20, i + 0.20], [100 * bw["ci_lo"], 100 * bw["ci_hi"]],
                color=INK2, lw=1.2, ls=(0, (2, 2)),
                label="95% CI, per-window (inflated)" if i == 0 else None)
        ax.plot(i, 100 * r["shuffle_null_mean"], "D", ms=6, mfc="white", mec=INK, mew=1.2,
                label="Shuffled null (5 seeds)" if i == 0 else None)
        ax.text(i, acc + 1.6, f"{acc:.1f}", ha="center", fontsize=9, fontweight="bold", color=INK)
    ax.axhline(100 * chance, color=INK2, lw=1.2, ls=(0, (5, 3)),
               label="Coverage-based constant predictor (50%)")
    ax.set_xticks(xs, [CFG_LBL[c] for c in order], fontsize=8.2, color=INK)
    ax.set_ylim(0, 156)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("2-class accuracy [%]", fontsize=9.5, color=INK2)
    ax.set_title("(a) Accuracy by engine setting", fontsize=11, color=INK, pad=9)
    clean(ax)
    ax.legend(loc="upper center", fontsize=7.0, frameon=False, ncol=1,
              handlelength=1.8, borderpad=0.2, labelspacing=0.35)

    # ── (b) 클래스별 재현율 ────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 1])
    w = 0.36
    for j, a in enumerate(CLASSES2):
        vals = [100 * two[c]["per_class_recall"][a] for c in order]
        ax.bar(xs + (j - 0.5) * w, vals, width=w, color=CLS_COL[a], alpha=0.9, label=CLS_LBL[a])
        for i, v in enumerate(vals):
            ax.text(i + (j - 0.5) * w, v + 1.6, f"{v:.0f}", ha="center", fontsize=8, color=INK)
    ax.axhline(100 * chance, color=INK2, lw=1.2, ls=(0, (5, 3)))
    ax.text(-0.45, 100 * chance + 3.0, "constant predictor", fontsize=7.2, color=INK2, ha="left",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.2))
    ax.set_xticks(xs, [CFG_LBL[c] for c in order], fontsize=8.2, color=INK)
    ax.set_ylim(0, 118)
    ax.set_ylabel("Per-class recall [%]", fontsize=9.5, color=INK2)
    ax.set_title("(b) The average hides a class collapse", fontsize=11, color=INK, pad=9)
    clean(ax)
    ax.legend(loc="lower left", fontsize=8, frameon=False)

    # ── (c) 묻힌 깊이 ─────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0, 2])
    bp = [r for r in p["burial_vs_erasure"]["pairs"] if r["burial_depth_db"] is not None]
    labs = [f"{CLS_LBL[r['class']][:3]} {r['el_deg']:+.0f}" for r in bp]
    vals = [r["burial_depth_db"] for r in bp]
    cols = [CLS_COL[r["class"]] for r in bp]
    ax.barh(np.arange(len(bp)), vals, color=cols, alpha=0.9, height=0.72)
    ax.axvline(BAND["ac_power_db"], color=INK, lw=1.3, ls=(0, (4, 3)))
    ax.text(BAND["ac_power_db"] + 0.7, len(bp) - 0.4, "grid band 3.86 dB",
            fontsize=7.5, color=INK, va="center")
    ax.set_yticks(np.arange(len(bp)), labs, fontsize=7.2, color=INK2)
    ax.invert_yaxis()
    ax.set_xlabel("Burial depth [dB]  (comb line of refraction-only arm,\nrelative to the "
                  "physics-ON floor inside the comb bins)", fontsize=8.6, color=INK2)
    ax.set_title("(c) How deep the comb is buried", fontsize=11, color=INK, pad=9)
    ax.grid(color=GRID, lw=0.6, alpha=0.75, axis="x")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8, length=3)

    # ── (d) 번역 곡선 ─────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 0])
    MK = {"ours": "o", "sionna_off": "s", "sionna_refr": "^", "sionna_phys": "v"}
    seen = set()
    for pt in p["translation_curve"]["points"]:
        lab = None
        if pt["class"] not in seen:
            lab = CLS_LBL[pt["class"]]
            seen.add(pt["class"])
        ax.plot(pt["contrast_db"], 100 * pt["acc"], MK[pt["config"]], ms=5.8,
                mfc=CLS_COL[pt["class"]], mec="white", mew=0.7, alpha=0.85, label=lab)
    th = p["translation_curve"]["thresholds"]["s1000plus"]
    lo_t, hi_t = th["min_contrast_db_among_perfect"], th["max_contrast_db_among_imperfect"]
    if lo_t is not None and hi_t is not None:
        ax.axvspan(min(lo_t, hi_t), max(lo_t, hi_t), color=RED, alpha=0.10)
        ax.text((lo_t + hi_t) / 2, 33,
                f"S1000+ crossover\n{min(lo_t, hi_t):.1f} to {max(lo_t, hi_t):.1f} dB",
                fontsize=7.0, color=RED, ha="center")
    ax.axhline(100 * chance, color=INK2, lw=1.1, ls=(0, (5, 3)))
    ax.set_xlabel("Comb line over floor, above tip [dB]", fontsize=9.5, color=INK2)
    ax.set_ylabel("Per-series accuracy [%]", fontsize=9.5, color=INK2)
    sp = p["translation_curve"]["spearman_contrast_vs_margin"]
    ax.set_title("(d) The score is a translation of comb-over-floor\n"
                 f"S1000+: every series above {max(lo_t, hi_t):.1f} dB scores 100%, none below "
                 f"{min(lo_t, hi_t):.1f} dB does\n"
                 f"(decision margin vs contrast: Spearman {sp['s1000plus']:+.2f} S1000+, "
                 f"{sp['matrice4e']:+.2f} Matrice 4E)",
                 fontsize=9.2, color=INK, pad=7)
    ax.set_ylim(-6, 112)
    clean(ax)
    ax.grid(color=GRID, lw=0.6, alpha=0.75)
    h = [plt.Line2D([], [], marker=MK[c], ls="", mfc=INK2, mec="white", ms=6.5,
                    label=CFG_LBL[c].replace("\n", " ")) for c in order]
    h += [plt.Line2D([], [], marker="o", ls="", mfc=CLS_COL[a], mec="white", ms=6.5,
                     label=CLS_LBL[a]) for a in CLASSES2]
    ax.legend(handles=h, loc="lower right", fontsize=7.0, frameon=False, ncol=2)

    # ── (e) 주입 대조군 ────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 1])
    inj = p["injection_control"]
    mx = [100 * r["acc_measured_phys"] for r in inj["per_cell"]]
    my = [100 * r["acc_injection_mean"] for r in inj["per_cell"]]
    cc = [CLS_COL[r["class"]] for r in inj["per_cell"]]
    ax.plot([-5, 105], [-5, 105], color=INK2, lw=1.1, ls=(0, (4, 3)), label="y = x")
    ax.scatter(mx, my, s=62, c=cc, edgecolors="white", linewidths=0.8, zorder=3)
    ax.set_xlim(-6, 106)
    ax.set_ylim(-6, 106)
    ax.set_xlabel("Measured accuracy, physics ON [%]", fontsize=9.5, color=INK2)
    ax.set_ylabel("Refraction-only + rhythm-free noise\nmatched to that floor [%]",
                  fontsize=9.5, color=INK2)
    d = inj["delta_injection_minus_measured"]
    ax.set_title(f"(e) Burial control: raise only the floor\n"
                 f"mean {100 * inj['acc_injection']:.1f}% vs {100 * inj['acc_measured_phys']:.1f}% "
                 f"(paired CI {d['ci_lo_pp']:+.1f} to {d['ci_hi_pp']:+.1f} pp)",
                 fontsize=10.5, color=INK, pad=9)
    clean(ax)
    ax.grid(color=GRID, lw=0.6, alpha=0.75)
    h = [plt.Line2D([], [], marker="o", ls="", mfc=CLS_COL[a], mec="white", ms=7, label=CLS_LBL[a])
         for a in CLASSES2]
    h += [plt.Line2D([], [], color=INK2, ls=(0, (4, 3)), lw=1.1, label="y = x")]
    ax.legend(handles=h, loc="upper left", fontsize=7.6, frameon=False)

    # ── (f) 단일축 — 바닥 상승과 대리 성적 ────────────────────────────────
    ax = fig.add_subplot(gs[1, 2])
    rise = p["burial_vs_erasure"]["floor_rise_vs_physics_off_db_median"]
    sa = p["single_axis"]
    bars = [("Physics\nOFF", 0.0, 100 * two["sionna_off"]["accuracy"], BLUE, False),
            ("Edge\nonly", sa["edge_only"]["d_floor_db_median"] or 0.0,
             100 * (sa["edge_only"]["surrogate_accuracy_2class"] or 0.0), BLUE, False),
            ("Refraction\nonly", rise.get("sionna_refr") or 0.0,
             100 * two["sionna_refr"]["accuracy"], PURPLE, False),
            ("Diffraction\nonly *", sa["diffraction_only"]["d_floor_db_median"] or 0.0,
             100 * (sa["diffraction_only"]["surrogate_accuracy_2class"] or 0.0), ORANGE, True),
            ("Physics\nON", rise.get("sionna_phys") or 0.0,
             100 * two["sionna_phys"]["accuracy"], ORANGE, False)]
    xi = np.arange(len(bars))
    ax.bar(xi, [b[2] for b in bars], width=0.6,
           color=[b[3] for b in bars], alpha=0.9,
           hatch=["//" if b[4] else "" for b in bars], edgecolor="white", linewidth=0.8)
    for i, b in enumerate(bars):
        ax.text(i, b[2] + 8.5, f"{b[2]:.1f}", ha="center", fontsize=8.6, fontweight="bold", color=INK)
        ax.text(i, b[2] + 2.2, f"floor {b[1]:+.0f} dB", ha="center", fontsize=7.0, color=INK2)
    ax.axhline(100 * chance, color=INK2, lw=1.2, ls=(0, (5, 3)))
    ax.text(-0.45, 100 * chance + 3.0, "constant predictor", fontsize=7.2, color=INK2, ha="left",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.2))
    ax.set_xticks(xi, [b[0] for b in bars], fontsize=7.6, color=INK)
    ax.set_ylim(0, 150)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("2-class accuracy [%]", fontsize=9.5, color=INK2)
    ax.set_title("(f) Which switch buys the loss\n"
                 "floor rise measured against physics OFF; edge-only is a no-op",
                 fontsize=10.0, color=INK, pad=9)
    clean(ax)
    h = [plt.Rectangle((0, 0), 1, 1, fc=ORANGE, alpha=0.9, hatch="//", ec="white",
                       label="* surrogate: floor rise applied to both\n  classes (no measured arm exists)")]
    ax.legend(handles=h, loc="upper center", fontsize=7.0, frameon=False, handlelength=1.6)

    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, facecolor="white")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════
# 6. 자가검사
# ═══════════════════════════════════════════════════════════════════════════
def selftest(p: dict) -> dict:
    checks = {}

    def add(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail_ko": detail}

    # ① 팔 존재·자세 수·앙각 수
    npz = np.load(LEDGER_NPZ)
    bad = []
    for c in CFG_ORDER:
        for a, arm in CONFIGS[c]["arms"].items():
            for el in ELS:
                k = f"{arm}/{elkey(el)}"
                if k not in npz.files or npz[k].shape[0] != N_WIN * WIN_LEN:
                    bad.append(k)
    add("arms_exist_8192", not bad, f"결측/길이 이상 {len(bad)} 개" + (f" — {bad[:3]}" if bad else ""))

    # ② 재현 게이트 — 기존 classify_airframe.json 의 3 클래스 성적과 정확히 같아야 한다
    with open(REF_CLASSIFY_JSON, encoding="utf-8") as f:
        ref = json.load(f)
    three = p["tables"]["three_class"]["configs"]
    d_ours = abs(three["ours"]["accuracy"] - ref["results"]["ours"]["aggregate_accuracy"])
    d_sio = abs(three["sionna_off"]["accuracy"] - ref["results"]["sionna"]["aggregate_accuracy"])
    add("reproduces_classify_airframe", d_ours < 1e-9 and d_sio < 1e-9,
        f"ours Δ={d_ours:.2e} · sionna(물리끔) Δ={d_sio:.2e} — 채점 규약이 원본과 같음을 확인")

    # ③ 선/바닥 분해가 R13 원장을 되찾나(같은 팔·같은 f_flash=126.67·같은 f_tip)
    with open(R13_JSON, encoding="utf-8") as f:
        r13 = json.load(f)
    with open(LEDGER_JSON, encoding="utf-8") as f:
        led = json.load(f)
    prf = float(led["_meta"]["prf_hz"])
    ffl13 = float(r13["_meta"]["f_flash_hz"])
    errs = []
    for key, cell in list(r13["cells"].items()) + list(r13["other_drone_switch_arms"].items()):
        k = cell["npz_key"]
        if k not in npz.files or cell.get("zero_echo"):
            continue
        mine = line_floor(np.asarray(npz[k], complex), prf, ffl13, float(cell["f_tip_hz"]))
        for col in ("ac_db", "above_floor_db", "above_comb_db"):
            if cell[col] is not None and mine[col] is not None:
                errs.append(abs(mine[col] - cell[col]))
    add("reproduces_switch_factorial", errs and max(errs) <= 0.02,
        f"R13 셀 {len(errs)} 개 열 비교 · 최대 |Δ| = {max(errs):.4f} dB (허용 0.02)")

    # ④ 잣대가 배율에 불변인가 — 성적은 절대 세기가 아니라 «대비» 의 함수여야 한다
    sc2 = Scorer(prf, {a: p["templates"][a]["f_flash_hz_spec"] for a in CLASSES2})
    E = np.asarray(npz[f"{CONFIGS['sionna_phys']['arms']['s1000plus']}/el-45"], complex)
    a1 = sc2.series(E, "s1000plus", CLASSES2)["acc"]
    a2 = sc2.series(E * 1e6, "s1000plus", CLASSES2)["acc"]
    add("metric_is_scale_free", a1 == a2,
        f"×1e6 배율에도 정확도 동일({a1:.4f}) — 성적은 절대 레벨이 아니라 선/바닥 대비의 함수다")

    # ⑤ 주입 대조군이 목표 바닥을 실제로 맞췄나
    gaps = [abs(r["floor_match_err_db"]) for r in p["injection_control"]["per_cell"]
            if r["floor_match_err_db"] is not None and r["noise_needed"]]
    add("injection_floor_matched", gaps and max(gaps) <= 0.5,
        f"바닥 정합 오차 최대 {max(gaps):.3f} dB (허용 0.5) · 칸 {len(gaps)} 개")

    # ⑥ 널이 상수 예측선 근처인가(백색화 기전)
    ok, det = True, []
    for tag, tb in p["tables"].items():
        ch = tb["chance_accuracy"]
        for c, r in tb["configs"].items():
            v = r["shuffle_null_mean"]
            ok &= abs(v - ch) < 0.06
            det.append(f"{tag}/{c}={v:.3f}")
    add("shuffle_null_near_constant_predictor", ok, "널 평균 " + " · ".join(det) + f" (기준 1/k)")

    # ⑦ 시계열 CI 가 창 CI 보다 넓은가(부풀림의 증거)
    wide = True
    for tag, tb in p["tables"].items():
        for c, r in tb["configs"].items():
            s = r["bootstrap_series"]; w = r["bootstrap_window_INFLATED"]
            if (s["ci_hi"] - s["ci_lo"]) + 1e-12 < (w["ci_hi"] - w["ci_lo"]):
                wide = False
    add("series_ci_wider_than_window_ci", wide,
        "모든 칸에서 시계열 단위 구간이 창 단위 구간보다 넓다 — 창 단위는 증거력을 부풀린다")

    # ⑧ 클래스 수·시계열 수
    add("plate_shapes", p["tables"]["two_class"]["n_series_per_config"] == 14
        and p["tables"]["three_class"]["n_series_per_config"] == 21,
        "2 클래스 14 시계열 · 3 클래스 21 시계열")

    # ⑨ 산출물
    add("json_written", os.path.exists(OUT_JSON) and os.path.getsize(OUT_JSON) > 20000, OUT_JSON)
    add("figure_written", os.path.exists(OUT_FIG) and os.path.getsize(OUT_FIG) > 60000, OUT_FIG)

    checks["all_pass"] = all(v["pass"] for k, v in checks.items() if isinstance(v, dict))
    return checks


# ═══════════════════════════════════════════════════════════════════════════
# 7. main
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    payload = run()
    payload["verdict"] = verdict(payload)
    payload["corrections"] = corrections_of(payload, payload["verdict"])
    payload["figures"] = {"main": OUT_FIG}

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    make_figure(payload)

    payload["selfcheck"] = selftest(payload)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # ── 콘솔 요약 ─────────────────────────────────────────────────────────
    two = payload["tables"]["two_class"]["configs"]
    print("=== R14 · 엔진 설정 → 기체 분류 성적 (2 클래스: matrice4e · s1000plus) ===")
    print(f"  {'설정':<22s} {'정확도':>8s} {'시계열CI95':>18s} {'창CI95(부풀림)':>18s} "
          f"{'섞기널':>7s} {'상수예측':>8s}")
    for c in CFG_ORDER:
        if c not in two:
            continue
        r = two[c]
        b, w = r["bootstrap_series"], r["bootstrap_window_INFLATED"]
        print(f"  {CONFIGS[c]['label_en']:<22s} {100 * r['accuracy']:7.2f}% "
              f"{100 * b['ci_lo']:7.1f}~{100 * b['ci_hi']:<7.1f} "
              f"{100 * w['ci_lo']:7.1f}~{100 * w['ci_hi']:<7.1f} "
              f"{100 * r['shuffle_null_mean']:6.1f}% "
              f"{100 * r['coverage_constant_predictor']['accuracy']:7.1f}%")
        print(f"      클래스별 재현율: " + " · ".join(
            f"{k} {100 * v:.1f}%" for k, v in r["per_class_recall"].items()))
    print("  --- 짝 비교(같은 시계열 짝 재표집) ---")
    for pr in payload["pairwise_paired_bootstrap"]:
        print(f"      {pr['from']:>12s} → {pr['to']:<12s} Δ {pr['delta_pp']:+6.2f} %p "
              f"[{pr['ci_lo_pp']:+6.2f}, {pr['ci_hi_pp']:+6.2f}] "
              f"{'판정 보류(0 걸침)' if pr['crosses_zero'] else '유의'}")
    inj = payload["injection_control"]
    print("  --- 지웠나 덮었나 ---")
    print(f"      주입 대조군: 물리켬 {100 * inj['acc_measured_phys']:.2f} % ↔ "
          f"바닥만 올린 가짜 팔 {100 * inj['acc_injection']:.2f} % "
          f"(Δ {inj['delta_injection_minus_measured']['delta_pp']:+.2f} %p, CI "
          f"{inj['delta_injection_minus_measured']['ci_lo_pp']:+.2f}~"
          f"{inj['delta_injection_minus_measured']['ci_hi_pp']:+.2f})")
    for h in payload["verdict"]["headline_ko"]:
        print("  ⭐ " + h)
    print("  --- 판정 보류 ---")
    for u in payload["verdict"]["undecided_ko"]:
        print("      · " + u)
    print("=== 자가검사 ===")
    for k, v in payload["selfcheck"].items():
        if k == "all_pass":
            continue
        print(f"  [{'PASS' if v['pass'] else 'FAIL'}] {k} — {v['detail_ko']}")
    print(f"  [{'PASS' if payload['selfcheck']['all_pass'] else 'FAIL'}] 종합 "
          f"({payload['_meta']['elapsed_s']} s)")
    if not payload["selfcheck"]["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
