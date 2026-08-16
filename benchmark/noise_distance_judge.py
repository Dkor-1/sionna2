# -*- coding: utf-8 -*-
"""
noise_distance_judge.py — 본판 «잡음을 얹으면 얼마나 멀리 읽히나» 의 **판정·검산 층**
======================================================================================

무엇을 하는 파일인가
--------------------
`benchmark/noise_distance_frame.py` 는 «신호를 만들고 잡음을 섞어 잣대를 재는» 층이다.
이 파일은 그 위에 얹는 **판정 층**이다 — 잰 수를 놓고

  ⓐ 이 칸이 잣대를 낼 **자격**이 있나 (이상값·수치바닥 스크리닝)
  ⓑ 얼마를 넘어야 «읽힘» 인가 (판정 막대 — 세 겹의 max)
  ⓒ 그래서 **몇 미터**인가 (R_read50 · R_read90 · R50 · Pd90 의 정의)
  ⓓ 그 수가 다른 원장과 **맞나** (detection_curves.json 교차검산)
  ⓔ 규약을 흔들어도 **살아남는 주장**이 무엇인가 (생존 등급)

을 정한다. 본판은 이 파일을 import 해서 쓰고, 이 파일은 아무것도 새로 계산하지 않는
순수 판정 규약 + 그 규약을 원장에 대고 돌려 보는 자가검사로만 이루어진다.

⭐왜 판정 층을 따로 두나 — 규약이 결론을 지배한 전례가 두 번 있었다
--------------------------------------------------------------------
  1) 앵커 규약을 바꾸니 엔진 간 배수가 12배 → 1.3배로 변했다.
  2) 판정 막대를 «다른 통계량» 에서 빌려 오니 실제로는 보이는 판이 «안 보임» 이 됐다
     (docs/MAP_SCALING.md §2-b, 화소 첨두 막대가 16.6 dB 높았다).
그래서 «막대를 어디서 세우나» 를 신호 만드는 코드와 **분리**하고, 막대의 출처를
칸마다 원장에 적는다.

⭐판정 막대 — 세 겹의 max (이 파일의 핵심)
-------------------------------------------
사용자 규칙은 «막대는 **판정하는 그 양**의 귀무분포 p99.9» 다. 지키되, 귀무가 하나가
아니라는 것이 이번 설계의 요지다.

  B1  잡음 귀무   백색 CN(0,1) 을 같은 마스크로 통과시킨 빗살 대비의 p99.9.
                  «잡음만으로 이 값이 나오나» 를 묻는다.
                  실측(8192 표본): el −30 **2.701** · el +0 **2.467** · el −60 **4.034** dB.

  B2  구조 귀무   ⭐**칸마다 다시 세운다.** 그 칸의 움직이는 성분(AC)을 슬로타임에서
                  **뒤섞어** 리듬만 부수고(진폭 분포·희소성은 그대로) 같은 SNR 로 잡음을
                  얹은 뒤 p99.9. «이 칸의 진폭 분포로, 리듬 없이 이 값이 나오나» 를 묻는다.
                  ⚠B1 은 8192 표본에 **고르게** 실린 열의 막대다. 움직이는 몫이 몇 자세에
                  몰린 칸은 리듬이 하나도 없어도 빗살 대비가 크게 흔들린다 — 실측으로
                  유효 자세 수 N_eff = 3 인 칸의 뒤섞기 막대는 **8.92 dB** 로 B1(2.47)의
                  3.6 배다. B1 만 쓰면 그 칸이 «읽힘» 으로 잘못 넘어간다.
                  ⭐낮은 SNR(먼 거리) 에서는 B2 → B1 로 수렴한다. 즉 B2 는 **가까운 거리의
                  원장 칸**을 지키고, B1 은 **판독거리 교차점**을 지킨다.

  B3  격자 밴드   우리 자신의 수치 손잡이를 조였을 때 이 잣대가 움직이는 폭.
                  앙각마다 다르다(canon metric_protocol.comb_grid_band_db_by_el):
                  el −30 **4.616** · el +0 **0.105** · el −60 **4.053** dB.
                  ⚠**엔진마다 손잡이가 다르다** — 우리 커널은 격자 λ/12↔λ/24, PathSolver 는
                  광선 예산(spp)·깊이다. 지금 원장에 있는 것은 우리 커널의 밴드뿐이라
                  PathSolver 팔에는 그 값을 **빌려 쓰고 빌렸다고 적는다**(BAND_BORROWED).

  **판정 막대 = max(B1, B2, B3).**  셋 다 넘어야 «무늬 읽힘» 이다.
  이 규칙은 «정본 앙각 밴드를 써라» 와 «귀무 p99.9 를 써라» 라는 두 정정 요구를 동시에
  만족시킨다 — 둘 다 넘어야 하니 큰 쪽이 이긴다.

  ⭐머리카락 밴드 규칙(canon): B3 < 0.5 dB 이면 그 폭에 물리적 의미를 붙이지 않는다.
  el +0 의 0.105 dB 가 여기 걸리므로 el +0 막대는 사실상 B1 이 정한다.

⭐자격 심사(스크리닝) — **두 층**이다
------------------------------------
처음에 다섯 관문을 전부 «자격 박탈» 로 설계했다가 자가검사에서 되돌렸다. 유효 자세 수가
적다는 것은 «잣대를 못 낸다» 가 아니라 «**백색 막대를 쓸 자격이 없다**» 는 뜻이기 때문이다.
그래서 층을 나눈다.

  1층 — 자격 박탈(판정 금지, 수만 기록)
    T1 완결성      n_missing · 0 표본 = 0
    T2 수치 바닥    ac_fraction_db ≥ **−60 dB**
    T3 한 줌 자세   상위 8 자세가 AC 전력의 **< 50 %**  (넘으면 물리가 아니라 사건 몇 개다)
    T4 균일 재표집  짝/홀 자세 판의 빗살 대비 차 ≤ **3 dB** (⛔삭제 솎기 금지 — canon J1)

  2층 — 주의 딱지(판정은 하되 조건이 붙는다)
    W1 희소       N_eff = (Σp)²/Σp² < **256**  (p = |E−mean|²)
       ⇒ ⓐ 막대를 **반드시 B2 로** 세운다(백색 막대 단독 사용 금지)
         ⓑ **A1 연장선 금지** — 이 칸의 모양을 얼려 먼 거리로 밀지 않는다
         ⓒ 인용할 때 «움직이는 몫을 자세 N 개가 지고 있다» 를 함께 적는다
    W2 이웃 불연속 같은 팔·같은 앙각의 이웃 거리와 N_eff 가 10 배 또는 잣대가 10 dB
       이상 튀면 조사 대상으로 표시한다(자동 탈락은 아니다)

거리의 정의 — 못 박는다
-----------------------
  R_read50  잡음을 다시 태웠을 때 **시행의 50 %** 가 판정 막대를 넘는 거리
  R_read90  같은 것의 **90 %**  ⭐덱 헤드라인은 이 수를 쓴다(«읽힌다» 는 열에 아홉)
  R50       탐지 통계량의 Pd = 0.5 인 거리 (detection_curves.py 와 같은 규약)
  Pd90      같은 것의 Pd = 0.9
  ⚠현행 방법판은 «평균 곡선이 막대를 지나는 자리» 하나뿐이었다 — 평균은 분포의 반쪽만
  말한다. R_read50 은 그것과 거의 같고, R_read90 은 약 0.90~0.92 배 짧다.

⛔GPU/솔버 없음. 저장된 원장만 읽는다.
실행(자가검사):
    cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/noise_distance_judge.py
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

CANON_JSON = os.path.join(ROOT, "outputs", "material_canon_0816.json")
LEDGER_JSON = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LEDGER_NPZ = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
DETECTION_JSON = os.path.join(ROOT, "outputs", "detection_curves.json")
OUT_JSON = os.path.join(ROOT, "outputs", "noise_distance_judge_selftest.json")

# --------------------------------------------------------------------------- #
#  판정 규약 상수 — 바꾸면 결론이 바뀐다. 바꿀 때는 원장에 사유를 적는다.
# --------------------------------------------------------------------------- #
PFA = 1e-3                  # detection_curves 와 같은 수 — 두 원장을 나란히 놓기 위해
Q_BAR = 1.0 - PFA           # 막대 분위수 = p99.9
N_NULL_BAR = 20_000         # ⭐B1·B2 시행수. 4,000 이면 막대 sd 0.15~0.18 dB(거리 1.2~1.9 %),
                            #   20,000 이면 0.05~0.07 dB(거리 0.5 %). scaled_maps 선례와 같은 수.
N_MC_DIST = 2_000           # 거리점·규약당 몬테카를로(240 → 2,000). Pd 0.5 근처 거리 오차 0.3 %.
READ_FRACTIONS = (0.5, 0.9)  # R_read50 · R_read90
PD_LEVELS = (0.5, 0.9)       # R50 · Pd90

SPARSE_NEFF_MIN = 256.0     # W1 — 2층 주의 딱지(자격 박탈 아님): 아래면 막대를 B2 로, A1 금지
GATE_TOP8_MAX_PCT = 50.0    # T3 — 1층 자격 박탈: 상위 8 자세가 절반을 넘으면 물리가 아니다
GATE_AC_FRAC_MIN_DB = -60.0  # T2 — 1층
GATE_RESAMPLE_MAX_DB = 3.0  # T4 — 1층 (짝/홀 재표집 차)
NEIGHBOUR_NEFF_RATIO = 10.0  # W2 — 이웃 거리와 N_eff 가 이 배수 넘게 튀면 조사 대상
NEIGHBOUR_COMB_JUMP_DB = 10.0
HAIRLINE_BAND_DB = 0.5      # canon — 이보다 좁은 밴드에는 물리 의미를 안 붙인다

CROSSCHECK_TOL_PCT = 2.0    # X1 합격선 — 정렬 후 R50 편차
A1_A2_TOL_MULT = 1.0        # X3 합격선 — 격자 밴드의 몇 배까지 봐주나

# ⭐규약 손잡이 — 생존 검사에서 흔드는 것들(이름과 대안을 코드에 박아 둔다)
KNOBS = {
    "K1_anchor_scope": ["S1_total_sigma", "S3_ac_sigma", "scaled_maps_7el_mean"],
    "K2_decision_bar": ["B1_only", "B3_only", "max_B1_B2_B3"],
    "K3_eirp_dbm": [12.0, 30.0, 63.0],
    "K4_capture": ["full_waveform", "always_on_pilot"],
    "K5_range_axis": ["A1_frozen_shape", "A2_ledger_points"],
    "K6_elevation": [-30.0, 0.0, -60.0],
}


# --------------------------------------------------------------------------- #
#  1. 정본 밴드(B3) — canon 에서 읽는다. 손으로 적지 않는다.
# --------------------------------------------------------------------------- #
def canon_bands() -> dict:
    """material_canon_0816.json 의 앙각별 빗살 격자 밴드. 없으면 예외 — 빌려 쓰기 금지."""
    d = json.load(open(CANON_JSON))
    mp = d["metric_protocol"]
    return dict(
        comb_db_by_el={k: float(v) for k, v in mp["comb_grid_band_db_by_el"].items()},
        rhythm_pp_by_el={k: float(v) for k, v in mp["rhythm_grid_band_pp_by_el"].items()},
        ac_db_by_el={k: float(v) for k, v in mp["ac_grid_band_db_by_el"].items()},
        source="outputs/material_canon_0816.json : metric_protocol",
        knob_ko="우리 커널의 손잡이는 격자 λ/12 ↔ λ/24 다",
        borrowed_for_ko="⚠PathSolver 팔에는 이 밴드를 **빌려 쓴다** — 그쪽 손잡이는 "
                        "광선 예산(spp)·깊이이고 그 밴드는 생산 설정에서 아직 안 쟀다",
    )


def el_band_db(bands: dict, el: float) -> tuple[float, bool]:
    """(밴드 dB, 머리카락인가). 머리카락 밴드는 판정에서 폭에 의미를 안 준다."""
    key = "+0" if el == 0 else f"{int(el):d}"
    v = bands["comb_db_by_el"].get(key)
    if v is None:
        raise KeyError(f"canon 에 el {key} 의 빗살 밴드가 없다 — 빌려 쓰지 말고 재라")
    return float(v), bool(v < HAIRLINE_BAND_DB)


# --------------------------------------------------------------------------- #
#  2. 잣대 — build_md_atlas 정의 그대로(재발명 금지). 마스크는 호출자가 준다.
# --------------------------------------------------------------------------- #
def comb_contrast_db(X: np.ndarray, w: np.ndarray, m_on, m_off) -> np.ndarray:
    """행렬 X(시행×n) → 빗살 대비 [dB]. ⭐행마다 DC 제거 후 한나창 FFT."""
    Xc = (X - X.mean(axis=1, keepdims=True)) * w
    P = np.abs(np.fft.fft(Xc, axis=1)) ** 2
    on = P[:, m_on].mean(axis=1)
    off = P[:, m_off].mean(axis=1)
    return 10.0 * np.log10(np.maximum(on, 1e-300) / np.maximum(off, 1e-300))


def _cn(rng, m: int, n: int, var: float = 1.0) -> np.ndarray:
    return ((rng.standard_normal((m, n)) + 1j * rng.standard_normal((m, n)))
            * math.sqrt(var / 2.0))


# --------------------------------------------------------------------------- #
#  3. 막대 B1 · B2
# --------------------------------------------------------------------------- #
def white_null_bar(n: int, w, m_on, m_off, n_trial: int = N_NULL_BAR,
                   seed: int = 20260816, batch: int = 2000) -> dict:
    """B1 — 백색 잡음만의 빗살 대비 분포. ⭐신호는 인자에도 없다(문턱 누설 원천 차단)."""
    rng = np.random.default_rng(seed)
    acc, done = [], 0
    while done < n_trial:
        mb = min(batch, n_trial - done)
        acc.append(comb_contrast_db(_cn(rng, mb, n), w, m_on, m_off))
        done += mb
    v = np.concatenate(acc)
    return dict(bar_db=float(np.quantile(v, Q_BAR)), mean_db=float(v.mean()),
                std_db=float(v.std()), p99_db=float(np.quantile(v, 0.99)),
                max_db=float(v.max()), n_trial=int(v.size),
                what_ko="잡음만으로 이 빗살 대비가 나오나 (판정량 자체의 귀무 p99.9)")


def surrogate_bar(E: np.ndarray, snr_ac_db: float | None, w, m_on, m_off,
                  n_trial: int = N_NULL_BAR, seed: int = 20260817,
                  batch: int = 1000) -> dict:
    """B2 — ⭐이 칸의 AC 를 **뒤섞어** 리듬만 부순 귀무. 진폭 분포·희소성은 보존된다.

    snr_ac_db=None 이면 무잡음(SNR→∞) 막대. 값을 주면 그 SNR 로 잡음을 얹는다.
    잡음이 세질수록(먼 거리) B2 → B1 로 수렴한다."""
    rng = np.random.default_rng(seed)
    ac = E - E.mean()
    n = ac.size
    unit = ac / math.sqrt(float(np.mean(np.abs(ac) ** 2)))
    a = 0.0 if snr_ac_db is None else 10.0 ** (snr_ac_db / 20.0)
    acc, done = [], 0
    while done < n_trial:
        mb = min(batch, n_trial - done)
        S = np.empty((mb, n), complex)
        for i in range(mb):
            S[i] = rng.permutation(unit)
        X = S if snr_ac_db is None else a * S + _cn(rng, mb, n)
        acc.append(comb_contrast_db(X, w, m_on, m_off))
        done += mb
    v = np.concatenate(acc)
    return dict(bar_db=float(np.quantile(v, Q_BAR)), median_db=float(np.median(v)),
                n_trial=int(v.size), snr_ac_db=snr_ac_db,
                what_ko="이 칸의 진폭 분포로, 리듬 없이 이 값이 나오나 "
                        "(자세를 뒤섞어 리듬만 부순 귀무의 p99.9)")


def decision_bar(b1: dict, b2: dict | None, b3_db: float, b3_hairline: bool,
                 b3_borrowed: bool, sparse: bool = False) -> dict:
    """⭐판정 막대 = max(B1, B2, B3). 어느 것이 이겼는지 원장에 남긴다.

    sparse=True(W1 딱지) 인데 B2 가 없으면 예외 — 희소한 칸에 백색 막대를 쓰는 것이
    이 설계가 막으려는 바로 그 오류다."""
    if sparse and b2 is None:
        raise ValueError("희소한 칸(W1)은 B2 구조 귀무 없이 판정할 수 없다")
    parts = {"B1_white_null": b1["bar_db"], "B3_grid_band": b3_db}
    if b2 is not None:
        parts["B2_surrogate_null"] = b2["bar_db"]
    who = max(parts, key=parts.get)
    return dict(bar_db=float(parts[who]), decided_by=who, parts_db=parts,
                b3_hairline=bool(b3_hairline), b3_borrowed=bool(b3_borrowed),
                sparse=bool(sparse),
                rule_ko="셋 다 넘어야 «무늬 읽힘». 큰 쪽이 막대가 된다",
                caveat_ko=("⚠B3 를 다른 엔진에서 빌려 왔다 — 이 팔의 수치 재현 밴드는 "
                           "아직 안 쟀다" if b3_borrowed else
                           ("⚠B3 가 머리카락 밴드(<0.5 dB)라 폭에 의미를 안 준다"
                            if b3_hairline else "")))


# --------------------------------------------------------------------------- #
#  4. 자격 심사(스크리닝)
# --------------------------------------------------------------------------- #
def eligibility(E: np.ndarray, ledger_row: dict, w, m_on, m_off,
                prf_hz: float, f_flash_hz: float, hw_hz: float,
                f_tip_hz: float) -> dict:
    """칸이 잣대를 낼 자격이 있나. 하나라도 걸리면 판정에서 뺀다(수는 기록)."""
    n = E.size
    ac = E - E.mean()
    p = np.abs(ac) ** 2
    tot = float(np.mean(np.abs(E) ** 2))
    ac_mean = float(p.mean())
    neff = float(p.sum() ** 2 / (p ** 2).sum()) if p.sum() > 0 else 0.0
    srt = np.sort(p)[::-1]
    top8 = float(100.0 * srt[:8].sum() / max(p.sum(), 1e-300))
    iso = float(srt[0] / max(srt[1], 1e-300))
    ac_db = 10.0 * math.log10(max(ac_mean / max(tot, 1e-300), 1e-300))

    # G5 — 짝/홀 균일 재표집(canon 이 권하는 방식: 삭제 대신 균일 재표집)
    def _sub(idx):
        e = E[idx]
        nn = e.size
        ww = np.hanning(nn)
        fr = np.abs(np.fft.fftfreq(nn, 2.0 / prf_hz))
        k = fr / f_flash_hz
        band = (fr >= 2 * f_flash_hz) & (fr <= f_tip_hz)
        on = band & (np.abs(k - np.round(k)) * f_flash_hz <= hw_hz)
        off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash_hz <= hw_hz)
        if on.sum() < 4 or off.sum() < 4:
            return None
        return float(comb_contrast_db(e[None, :], ww, on, off)[0])

    ce, co = _sub(slice(0, None, 2)), _sub(slice(1, None, 2))
    resample_db = None if (ce is None or co is None) else abs(ce - co)

    tier1 = {
        "T1_complete": dict(
            ok=bool(int(ledger_row.get("n_missing") or 0) == 0
                    and int(np.count_nonzero(E == 0)) == 0),
            n_missing=int(ledger_row.get("n_missing") or 0),
            zeros=int(np.count_nonzero(E == 0))),
        "T2_ac_fraction_db": dict(ok=bool(ac_db >= GATE_AC_FRAC_MIN_DB),
                                  value=round(ac_db, 2),
                                  threshold=GATE_AC_FRAC_MIN_DB,
                                  what_ko="움직이는 몫이 총 전력의 몇 dB — 수치 바닥 판별"),
        "T3_top8_share_pct": dict(ok=bool(top8 < GATE_TOP8_MAX_PCT),
                                  value=round(top8, 2), threshold=GATE_TOP8_MAX_PCT,
                                  what_ko="상위 8 자세가 움직이는 전력의 몇 % — 절반을 넘으면 "
                                          "물리가 아니라 사건 몇 개다"),
        "T4_uniform_resample_db": dict(
            ok=bool(resample_db is not None and resample_db <= GATE_RESAMPLE_MAX_DB),
            value=None if resample_db is None else round(resample_db, 2),
            threshold=GATE_RESAMPLE_MAX_DB,
            what_ko="짝수 자세 판 ↔ 홀수 자세 판의 빗살 대비 차(⛔삭제 솎기 금지, canon J1)"),
    }
    sparse = bool(neff < SPARSE_NEFF_MIN)
    tier2 = {
        "W1_sparse": dict(flag=sparse, n_eff=round(neff, 1), threshold=SPARSE_NEFF_MIN,
                          consequences_ko=["막대는 반드시 B2(구조 귀무)로 — 백색 막대 단독 금지",
                                           "A1 연장선 금지 — 이 모양을 얼려 먼 거리로 밀지 않는다",
                                           "인용할 때 «자세 N 개가 지고 있다» 를 함께 적는다"]
                          if sparse else []),
    }
    bad = [k for k, v in tier1.items() if not v["ok"]]
    return dict(eligible=bool(not bad), failed=bad, tier1=tier1, tier2=tier2,
                sparse=sparse, n_eff=round(neff, 1),
                must_use_surrogate_bar=sparse, forbid_A1=sparse,
                isolation_max_over_2nd=round(iso, 3),
                note_ko="1층에 걸리면 판정 금지(수만 기록). 2층은 판정하되 조건이 붙는다")


# --------------------------------------------------------------------------- #
#  5. 거리의 정의
# --------------------------------------------------------------------------- #
def _cross(x, y, level, rising=True):
    """단조 가정 아래 y 가 level 을 지나는 x — 선형보간. 없으면 None."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = y >= level if rising else y <= level
    if ok.all():
        return float(x[0])
    if not ok.any():
        return None
    i = int(np.argmax(ok))
    if i == 0:
        return float(x[0])
    if abs(y[i] - y[i - 1]) < 1e-12:
        return float(x[i])
    return float(x[i - 1] + (level - y[i - 1]) / (y[i] - y[i - 1]) * (x[i] - x[i - 1]))


def read_distances(snr_grid_db, frac_above_bar, snr_at_ref_m: float,
                   ref_m: float = 15.0) -> dict:
    """R_read50 · R_read90 — «시행의 f 배가 막대를 넘는» 거리.

    frac_above_bar[i] = SNR grid[i] 에서 막대를 넘은 시행의 비율.
    거리 지도는 1/R⁴: SNR(R) = SNR(ref) − 40·log10(R/ref)."""
    out = {}
    for f in READ_FRACTIONS:
        s = _cross(snr_grid_db, frac_above_bar, f)
        out[f"R_read{int(f * 100)}_m"] = (
            None if s is None else float(ref_m * 10.0 ** ((snr_at_ref_m - s) / 40.0)))
        out[f"snr_read{int(f * 100)}_db"] = s
    out["definition_ko"] = ("잡음을 다시 태웠을 때 시행의 50 %/90 % 가 판정 막대를 넘는 "
                            "거리. ⭐덱 헤드라인은 R_read90 을 쓴다")
    return out


def pd_distances(snr_grid_db, pd_curve, snr_at_ref_m: float,
                 ref_m: float = 15.0) -> dict:
    """R50 · Pd90 — 탐지 통계량의 Pd 가 0.5 / 0.9 인 거리(detection_curves 와 같은 규약)."""
    out = {}
    for lv in PD_LEVELS:
        s = _cross(snr_grid_db, pd_curve, lv)
        tag = "R50" if lv == 0.5 else "R_pd90"
        out[f"{tag}_m"] = (None if s is None
                           else float(ref_m * 10.0 ** ((snr_at_ref_m - s) / 40.0)))
        out[f"snr_{tag}_db"] = s
    out["definition_ko"] = "Pd(빗살 통계량) = 0.5 / 0.9 인 거리, Pfa 1e−3"
    return out


# --------------------------------------------------------------------------- #
#  6. ⭐교차검산 — detection_curves.json 과 사과-대-사과로 맞댄다
# --------------------------------------------------------------------------- #
def crosscheck_alignment_notes() -> dict:
    """맞대기 전에 **반드시** 맞춰야 하는 세 가지. 안 맞추면 편차가 규약 차이로 오염된다."""
    return {
        "i_sigma_of_the_snr_label": dict(
            issue_ko="⭐detection_curves 의 snr_sample_db_at_100m 은 **총 σ**(DC 포함) 기준이고 "
                     "프레임의 snr_ac_db 는 **AC** 기준이다. 두 라벨을 그냥 나란히 놓으면 "
                     "그 칸의 ac_fraction_db 만큼 어긋난다",
            measured_offset_db=dict(ours_el_minus30=-5.62, ps_off_el_minus30=-2.36),
            rule_ko="⇒ 교차검산은 **미터**로만 한다. SNR 라벨을 인용할 때는 총/AC 를 함께 적는다"),
        "ii_same_range_grid": dict(
            issue_ko="detection_curves 는 100~10,000 m 를 21 점(옥타브당 4.0 dB SNR)으로 훑는다. "
                     "Pd 가 0.97 → 0.18 로 떨어지는 한 칸을 선형보간하므로 편향이 있다",
            rule_ko="⇒ 교차검산은 **그 21 점 위에서** 프레임 기계로 Pd 를 다시 재고 "
                    "**같은 보간식**(log R 위 선형)을 쓴다. 헤드라인 수는 미세 격자로 따로 낸다"),
        "iii_same_trials": dict(
            issue_ko="N_MC=240 은 Pd 0.5 근처에서 SNR sd 0.13 dB(거리 0.7~0.8 %)를 준다",
            rule_ko=f"⇒ 본판은 N_MC = {N_MC_DIST} (거리 0.3 %)로 올린다"),
        "pass_rule_ko": f"세 정렬 뒤 편차 |Δ| ≤ {CROSSCHECK_TOL_PCT} %. 넘으면 원장에 «미해결» 로 "
                        "적고 원인을 찾을 때까지 미터를 덱에 안 올린다",
    }


def r50_loginterp(R_grid, pd) -> float | None:
    """detection_curves.py 의 R50 보간식 그대로 — 첫 하강 교차를 log R 위에서 선형보간."""
    pd = np.asarray(pd, float)
    R_grid = np.asarray(R_grid, float)
    if pd[0] < 0.5 or not (pd < 0.5).any():
        return None
    i = int(np.argmax(pd < 0.5))
    x0, x1 = math.log10(R_grid[i - 1]), math.log10(R_grid[i])
    return float(10 ** (x0 + (pd[i - 1] - 0.5) / max(pd[i - 1] - pd[i], 1e-12) * (x1 - x0)))


def crosscheck_r50(ours_r50_m: float | None, arm_id: str, metric: str = "comb") -> dict:
    """정렬된 R50 을 detection_curves.json 의 같은 팔·같은 잣대와 맞댄다."""
    dc = json.load(open(DETECTION_JSON))
    row = next((a for a in dc["arms"] if a["arm_id"] == arm_id), None)
    if row is None or ours_r50_m is None:
        return dict(ok=None, why_ko=f"{arm_id} 를 detection_curves 에서 못 찾았다")
    theirs = row["R50_m"].get(metric)
    if theirs is None:
        return dict(ok=None, why_ko="상대 원장에 이 잣대의 R50 이 없다")
    dev = 100.0 * (ours_r50_m / theirs - 1.0)
    return dict(ok=bool(abs(dev) <= CROSSCHECK_TOL_PCT), arm_id=arm_id, metric=metric,
                ours_m=round(ours_r50_m, 1), theirs_m=round(theirs, 1),
                deviation_pct=round(dev, 2), tolerance_pct=CROSSCHECK_TOL_PCT,
                anchor_same_ko="el −30 에서 두 원장의 앵커는 같은 수다(c_anchor 비트동일). "
                               "다른 앙각에서는 앵커 범위가 달라 이 검산을 쓸 수 없다")


def crosscheck_anchor(c_anchor_frame: float, engine_short: str = "ours") -> dict:
    """앵커가 비트동일한가 — 이게 어긋나면 다른 검산은 다 무의미하다."""
    dc = json.load(open(DETECTION_JSON))
    theirs = float(dc["_meta"]["c_anchor"][engine_short]["c_anchor"])
    d_db = 10.0 * math.log10(c_anchor_frame / theirs)
    return dict(ok=bool(abs(d_db) < 1e-3), engine=engine_short,
                frame=c_anchor_frame, detection_curves=theirs,
                delta_db=round(d_db, 6))


def a1_tolerance_db(band_b3_db: float, bar_b1_db: float) -> float:
    """⭐A1 허용 오차 = max(B3 격자 밴드, B1 잡음 막대).

    B3 만 쓰면 머리카락 밴드(el +0 0.105 dB)에서 «연장선 못 믿음» 이 잘못 뜬다 — 잣대의
    잡음 흔들림(2.4 dB)보다 좁은 밴드를 기준으로 삼는 것은 뜻이 없다."""
    return float(max(band_b3_db, bar_b1_db))


def crosscheck_a1_a2(comb_a1_db: float, comb_a2_db: float, band_db: float,
                     bar_b1_db: float = 0.0) -> dict:
    """A1(15 m 모양 얼림) 연장선이 A2(엔진 재계산) 실판과 맞나. ⭐ours 는 480 m 실판이 있다."""
    d = abs(comb_a1_db - comb_a2_db)
    tol = A1_A2_TOL_MULT * a1_tolerance_db(band_db, bar_b1_db)
    return dict(ok=bool(d <= tol), delta_db=round(d, 2), tolerance_db=round(tol, 2),
                what_ko="연장선을 어디까지 믿어도 되나 — 판독거리 코앞의 실판으로 검증")


# --------------------------------------------------------------------------- #
#  7. ⭐규약 무관 생존 검사
# --------------------------------------------------------------------------- #
def survival_grade(claim: str, immune_to: list[str], moved_by: dict) -> dict:
    """주장 하나가 손잡이 여섯 중 몇 개에서 살아남나. 덱 큰 글자는 등급 A 만."""
    n_all = len(KNOBS)
    n_ok = len([k for k in KNOBS if k in immune_to])
    grade = "A" if n_ok == n_all else ("A-" if n_ok == n_all - 1
                                       else ("B" if n_ok >= n_all - 2 else "C"))
    return dict(claim_ko=claim, grade=grade, survives=f"{n_ok}/{n_all}",
                immune_to=immune_to, moved_by=moved_by,
                deck_rule_ko=("덱 큰 글자로 써도 된다" if grade == "A" else
                              "조건절과 함께만" if grade in ("A-", "B") else
                              "⛔단독으로 덱에 올리지 않는다"))


# --------------------------------------------------------------------------- #
#  8. 자가검사 — 위 규약을 지금 원장에 대고 실제로 돌려 본다
# --------------------------------------------------------------------------- #
ARM_PATTERNS = {
    "ours": "ours_r{R}_n8192",
    "ours_ptd": "ours_ptd_r{R}_n8192",
    "ps_off": "sionna_p4000000000_r{R}_n8192_d1",
    "ps_refr": "sionna_p4000000000_onlyrefr_r{R}_n8192",
    "ps_phys": "sionna_p4000000000_phys_r{R}_n8192_d1",
}
ARM_ENGINE_FAMILY = {"ours": "ours", "ours_ptd": "ours",
                     "ps_off": "sionna", "ps_refr": "sionna", "ps_phys": "sionna"}
SELFTEST_RANGES = [15, 30, 60, 120, 240, 480]
SELFTEST_ELS = [-30.0, 0.0, -60.0]
HW_HZ = 8.0


def _el_key(el: float) -> str:
    return "el+0" if el == 0 else f"el{int(el):d}"


def _masks(n, prf, f_tip, f_flash):
    fr = np.abs(np.fft.fftfreq(n, 1.0 / prf))
    k = fr / f_flash
    band = (fr >= 2.0 * f_flash) & (fr <= f_tip)
    on = band & (np.abs(k - np.round(k)) * f_flash <= HW_HZ)
    off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash <= HW_HZ)
    return on, off


def selftest(n_bar: int = 4000) -> dict:
    """CPU 만. n_bar 는 자가검사용(본판은 N_NULL_BAR)."""
    t0 = time.time()
    led = json.load(open(LEDGER_JSON))
    z = np.load(LEDGER_NPZ)
    meta = led["_meta"]
    prf, f_flash = float(meta["prf_hz"]), float(meta["f_flash_hz"])
    rows = {(r["engine"], float(r["el_deg"])): r for r in led["rows"]}
    bands = canon_bands()

    ftip, cells = {}, {}
    for arm, pat in ARM_PATTERNS.items():
        for R in SELFTEST_RANGES:
            eng = pat.format(R=R)
            for el in SELFTEST_ELS:
                key = f"{eng}/{_el_key(el)}"
                if key not in z.files or (eng, el) not in rows:
                    continue
                E = np.asarray(z[key], complex)
                if E.size != 8192:
                    continue
                ftip.setdefault(el, float(rows[(eng, el)]["f_tip_hz"]))
                cells[(arm, R, el)] = (E, rows[(eng, el)])

    w = np.hanning(8192)
    masks = {el: _masks(8192, prf, ft, f_flash) for el, ft in ftip.items()}

    # --- B1 (앙각당) ------------------------------------------------------- #
    b1 = {}
    for el, (on, off) in masks.items():
        b1[el] = white_null_bar(8192, w, on, off, n_trial=n_bar, seed=20260816)
        b1[el]["n_comb_on"] = int(on.sum())
        b1[el]["n_comb_off"] = int(off.sum())

    # --- 칸마다: 자격 · 무잡음 잣대 · B2(무잡음 극한) · 막대 ------------------ #
    out_cells = {}
    for (arm, R, el), (E, row) in sorted(cells.items()):
        on, off = masks[el]
        elig = eligibility(E, row, w, on, off, prf, f_flash, HW_HZ, ftip[el])
        clean = float(comb_contrast_db(E[None, :], w, on, off)[0])
        b3, hair = el_band_db(bands, el)
        borrowed = ARM_ENGINE_FAMILY[arm] != "ours"
        b2 = (surrogate_bar(E, None, w, on, off, n_trial=min(n_bar, 4000))
              if elig["tier1"]["T1_complete"]["ok"] else None)
        bar = (decision_bar(b1[el], b2, b3, hair, borrowed, sparse=elig["sparse"])
               if elig["eligible"] else None)
        out_cells[f"{arm}_r{R}_el{int(el):+d}"] = dict(
            arm=arm, range_m=R, el_deg=el, eligible=elig["eligible"],
            failed_gates=elig["failed"], tier1=elig["tier1"], tier2=elig["tier2"],
            sparse=elig["sparse"], n_eff=elig["n_eff"], forbid_A1=elig["forbid_A1"],
            clean_comb_db=round(clean, 2), bar=bar,
            margin_db=None if bar is None else round(clean - bar["bar_db"], 2),
            verdict_ko=("자격 없음" if not elig["eligible"] else
                        ("무늬 읽힘" if clean >= bar["bar_db"] else "무늬 안 읽힘")
                        + ("  ⚠희소(자세 %.0f 개가 지고 있다)" % elig["n_eff"]
                           if elig["sparse"] else "")))

    # --- W2 이웃 불연속(자동 탈락 아님, 조사 표시) --------------------------- #
    w2 = []
    for arm in ARM_PATTERNS:
        for el in SELFTEST_ELS:
            seq = [(R, out_cells[f"{arm}_r{R}_el{int(el):+d}"])
                   for R in SELFTEST_RANGES if f"{arm}_r{R}_el{int(el):+d}" in out_cells]
            for (r0, c0), (r1, c1) in zip(seq, seq[1:]):
                ratio = max(c1["n_eff"], 1e-9) / max(c0["n_eff"], 1e-9)
                jump = abs(c1["clean_comb_db"] - c0["clean_comb_db"])
                if ratio > NEIGHBOUR_NEFF_RATIO or ratio < 1 / NEIGHBOUR_NEFF_RATIO \
                        or jump > NEIGHBOUR_COMB_JUMP_DB:
                    w2.append(dict(arm=arm, el_deg=el, pair_m=[r0, r1],
                                   n_eff=[c0["n_eff"], c1["n_eff"]],
                                   clean_comb_db=[c0["clean_comb_db"], c1["clean_comb_db"]],
                                   why_ko="이웃 거리와 유효 자세 수/잣대가 크게 튄다 — 조사 대상"))

    # --- 검산 ------------------------------------------------------------- #
    dc = json.load(open(DETECTION_JSON))
    checks = dict(
        anchor=crosscheck_anchor(52.07030119796651, "ours"),
        alignment=crosscheck_alignment_notes(),
        detection_curves_meta=dict(
            R_grid_points=len(dc["_meta"]["R_grid_m"]),
            snr_step_per_grid_db=round(40 * math.log10(
                dc["_meta"]["R_grid_m"][1] / dc["_meta"]["R_grid_m"][0]), 2),
            n_mc=dc["_meta"]["n_mc"], pfa=dc["_meta"]["pfa_target"],
            snr_label_uses_ko="총 σ (DC 포함) — 프레임의 snr_ac_db 와 다른 라벨"),
    )

    # A1↔A2: ours el −30 은 480 m 실판이 있다 — 연장선의 가장 강한 검증
    a1a2 = {}
    for arm in ARM_PATTERNS:
        for el in SELFTEST_ELS:
            got = [(R, out_cells[f"{arm}_r{R}_el{int(el):+d}"]["clean_comb_db"])
                   for R in SELFTEST_RANGES
                   if f"{arm}_r{R}_el{int(el):+d}" in out_cells
                   and out_cells[f"{arm}_r{R}_el{int(el):+d}"]["eligible"]]
            if len(got) < 2:
                continue
            b3, _ = el_band_db(bands, el)
            tol = a1_tolerance_db(b3, b1[el]["bar_db"])
            drift = max(abs(v - got[0][1]) for _, v in got)
            a1a2[f"{arm}_el{int(el):+d}"] = dict(
                ledger_points={str(R): v for R, v in got},
                max_shape_drift_db=round(drift, 2), band_b3_db=b3,
                tolerance_db=round(tol, 2), trust_A1=bool(drift <= tol),
                farthest_ledger_m=max(R for R, _ in got))
    checks["A1_vs_A2"] = a1a2
    checks["W2_neighbour_discontinuity"] = w2

    # --- 생존 등급 ---------------------------------------------------------- #
    surv = [
        survival_grade(
            "물리를 전부 켜면 날개 무늬의 «천장»(무잡음 빗살 대비)이 한 자릿수 dB 에 "
            "머문다 — 같은 자세의 다 끔 팔은 40~52 dB 다. 그 간격 40~46 dB 가 결론이다",
            immune_to=list(KNOBS),
            moved_by=dict(measured_gap_db_el_minus30=45.7, measured_gap_db_el_minus60=41.3,
                          why_immune_ko="무잡음 값이라 앵커·EIRP·캡처·거리와 무관하고, "
                                        "두 팔의 차라 공통 상수는 약분된다")),
        survival_grade(
            "우리 커널의 천장(42.9 dB)은 PathSolver 다 끔(52.0 dB)보다 9 dB 낮다",
            immune_to=[k for k in KNOBS if k != "K5_range_axis"],
            moved_by=dict(K5_range_axis_ko="ps_off 은 거리마다 40.5~52.0 dB 로 11.5 dB 흔들린다")),
        survival_grade(
            "판독거리는 수백 m 다",
            immune_to=["K2_decision_bar", "K5_range_axis"],
            moved_by=dict(K3_eirp_ko="12/30/63 dBm 에서 0.32×/1×/6.7×",
                          K4_capture_ko="상시 기준신호면 정합필터 이득 37~43 dB 를 잃는다(×0.12)")),
        survival_grade(
            "물리 켬은 47 m 다",
            immune_to=[],
            moved_by=dict(K1_anchor_ko="S1 47 m ↔ S3 280 m (6배)",
                          K2_bar_ko="막대에 따라 40~56 m",
                          verdict_ko="⛔덱에 단독으로 올리지 않는다")),
    ]

    out = dict(
        _meta=dict(
            generator="benchmark/noise_distance_judge.py (판정·검산 층 자가검사)",
            role_ko="본판 noise_distance_frame 이 import 할 판정 규약. 이 파일 자체는 "
                    "신호를 만들지 않는다 — 막대·자격·거리 정의·교차검산만 담는다",
            generated_kst=time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(time.time() + 9 * 3600)) + " (UTC+9)",
            gpu_ko="⛔GPU/솔버 임포트 없음 — 저장된 원장만 읽는 CPU 판정",
            inputs=[os.path.relpath(p, ROOT) for p in
                    (LEDGER_JSON, LEDGER_NPZ, CANON_JSON, DETECTION_JSON)],
            n_bar_used=n_bar,
            n_bar_for_production=N_NULL_BAR,
            gate_tiers_ko="1층(자격 박탈) T1 완결성 · T2 수치바닥 · T3 한줌자세 · T4 균일재표집 / "
                          "2층(주의 딱지) W1 희소(N_eff<256 → 막대는 B2 로·A1 금지) · "
                          "W2 이웃 불연속(조사 표시)",
            design_correction_ko="⭐처음에는 N_eff<256 도 자격 박탈로 설계했다가 자가검사에서 "
                                 "되돌렸다 — 그 규칙은 덱 헤드라인 칸(ps_phys 15 m, N_eff 180)을 "
                                 "통째로 지웠다. 희소는 «잣대를 못 낸다» 가 아니라 «백색 막대를 "
                                 "쓸 자격이 없다» 는 뜻이고, 그건 B2 가 푼다",
            bar_precision_ko="p99.9 추정 sd — 4,000 시행 0.15~0.18 dB · 20,000 시행 "
                             "0.05~0.07 dB. 잣대 곡선 기울기 0.44~0.76 dB/dB 이므로 "
                             "막대 0.1 dB = 거리 0.8~1.3 %",
            constants=dict(PFA=PFA, N_NULL_BAR=N_NULL_BAR, N_MC_DIST=N_MC_DIST,
                           SPARSE_NEFF_MIN=SPARSE_NEFF_MIN,
                           GATE_TOP8_MAX_PCT=GATE_TOP8_MAX_PCT,
                           GATE_AC_FRAC_MIN_DB=GATE_AC_FRAC_MIN_DB,
                           GATE_RESAMPLE_MAX_DB=GATE_RESAMPLE_MAX_DB,
                           NEIGHBOUR_NEFF_RATIO=NEIGHBOUR_NEFF_RATIO,
                           NEIGHBOUR_COMB_JUMP_DB=NEIGHBOUR_COMB_JUMP_DB,
                           CROSSCHECK_TOL_PCT=CROSSCHECK_TOL_PCT),
            knobs=KNOBS),
        bands_B3=bands,
        bars_B1={f"{el:+.0f}": v for el, v in b1.items()},
        cells=out_cells,
        crosschecks=checks,
        survival=surv,
    )
    n_bad = [k for k, v in out_cells.items() if not v["eligible"]]
    n_sparse = [k for k, v in out_cells.items() if v["eligible"] and v["sparse"]]
    out["summary_ko"] = [
        f"칸 {len(out_cells)} 개 중 1층 자격 박탈 {len(n_bad)} 개: " + ", ".join(n_bad),
        f"2층 희소 딱지(판정은 하되 B2 막대·A1 금지) {len(n_sparse)} 개: " + ", ".join(n_sparse),
        "막대는 max(B1 잡음귀무, B2 구조귀무, B3 격자밴드) — 칸마다 어느 것이 이겼는지 "
        "cells[*].bar.decided_by 에 남는다",
        "⭐PathSolver 팔의 B3 는 우리 커널 밴드를 빌려 쓴 것이다(bar.b3_borrowed=true) — "
        "생산 설정의 반예산 쌍이 원장에 착지해야 자기 밴드를 갖는다",
    ]
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(out, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {OUT_JSON}")
    print(json.dumps(dict(cells=len(out_cells), ineligible=len(n_bad),
                          bars={k: round(v["bar_db"], 3) for k, v in out["bars_B1"].items()}),
                     ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    selftest(n_bar=int(sys.argv[1]) if len(sys.argv) > 1 else 4000)
