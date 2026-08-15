# -*- coding: utf-8 -*-
"""
classify_airframe.py — ⭐분류 첫 실험: 마이크로도플러 무늬만 보고 기체를 맞히나
================================================================================

질문
  원장(outputs/elevation_sweep_md.npz)의 자세 시계열 E 만 보고, 그 팔이 어느 기체
  (mini5pro / matrice4e / s1000plus)인지 **박자 빗살 정합**으로 맞힐 수 있는가.

데이터 (원장에서 실제로 뒤져 찾은 표준 팔 — 두 엔진 × 세 기체 × 앙각 7개)
  · 우리 커널 : ours_r15_n8192(기본기체=matrice4e) · ours_mini5pro_r15_n8192 · ours_s1000plus_r15_n8192
  · Sionna    : sionna_p4000000000{_기체}_r15_n8192_d1  (spp 4e9 · depth1 · phys 아님)
  선택 규칙: 15 m(원거리장 밖) · n_poses=8192 · 수정자(phys/sw*/only*/stockdef/free/ptd/az45/div24/pw) 없음.
  기체 태그가 붙은 팔 전체 목록은 JSON `arms_inventory` 에 문서화한다.

후보 템플릿 (⭐데이터에 맞추지 않는다 — src/drones.py 의 DRONES **스펙**에서 계산)
  f_flash = 날개수 × 호버rpm / 60
    mini5pro   : 2 × 5500/60 = 183.33 Hz
    matrice4e  : 2 × 3800/60 = 126.67 Hz
    s1000plus  : 2 × 4467/60 = 148.90 Hz
  교차확인: 원장 rows 의 f_tip_hz 를 스펙식 f_tip = 2·(π·D·rpm/60)/λ·cos(el) 과 대조,
  rows 의 track.beat_hz(원장 자체 측정 박자)를 스펙 f_flash 와 대조.

방법 (오늘의 교훈 반영: 레벨/에너지 잣대는 반드시 DC 제거 후)
  8192 자세 → 겹치지 않는 16 창 × 512 자세.
  창마다: x = E − mean(E)  (⭐창별 DC 제거) → hanning → FFT(제로패딩 nfft=8192,
  격자 2.405 Hz — 512점 원격자 38.5 Hz 로는 ±8 Hz 빗살 창이 비어 버리기 때문) →
  P = |X|².  후보 f 마다 빗살 점수 = Σ P(|fr| 이 f 의 정수배 k≥1 에서 ±8 Hz 이내)
  / Σ P(|fr| ≥ 8 Hz, 전체 AC).  argmax 후보 = 예측.  엔진×앙각별 3×3 혼동행렬.

대조군 (필수)
  자세 순서를 씨앗 고정(20260815)으로 섞은 널 대조 — 시간 구조가 죽어 스펙트럼이
  백색화되므로 정확도가 우연(1/3)으로 떨어져야 한다. ⚠기전: 백색 스펙트럼에서 raw
  빗살 몫 ≈ 빗살 덮개율(coverage)이고 덮개율은 f_flash 가 작은 matrice4e 가 최대라,
  널은 matrice4e 로 쏠려 정답률이 정확히 1/3 근방이 된다(균형 3클래스에서 한 클래스
  고정 예측 = 1/3). 덮개율은 JSON `templates.*.comb_coverage_frac` 에 남긴다.

−90°(직하방) 각주 — 정직하게
  f_tip = 0 이라 «f_tip 기반 대역» 잣대는 퇴화한다. 여기서는 모든 앙각에서 **전체 AC
  빗살 몫**으로 재므로 식 자체는 정의되지만, 물리적으로는 날개 속도가 시선에 수직이라
  마이크로도플러가 원리적으로 사라진 앙각이다 — −90° 성적은 «잔결 구조»만 시험한다.

산출
  outputs/classify_airframe.json          (혼동행렬·창 수·정확도·널 대조·팔 목록·교차확인)
  outputs/figures/classify_confusion.png  (엔진별 혼동행렬 + 앙각별 정확도, 영어)

실행
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/classify_airframe.py

⛔ GPU/솔버 호출 없음 — sionna.rt / mitsuba import 금지, 전부 저장된 원장을 읽는 CPU 분석.
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np

# ⛔ 무거운 GPU 스택이 아님을 보장: drones.py 는 numpy/dataclass 만 쓴다(geom 도 numpy 뿐).
from drones import DRONES

# --------------------------------------------------------------------------- #
#  상수 · 경로
# --------------------------------------------------------------------------- #
LEDGER_JSON = "outputs/elevation_sweep_md.json"
LEDGER_NPZ = "outputs/elevation_sweep_md.npz"
OUT_JSON = "outputs/classify_airframe.json"
OUT_FIG = "outputs/figures/classify_confusion.png"

AIRFRAMES = ["mini5pro", "matrice4e", "s1000plus"]   # 원장에 실제로 있는 3종(발견 순서 아님, 고정 순서)
N_WIN = 16            # 겹치지 않는 창 수
WIN_LEN = 512         # 창 길이(자세 수) — 16×512 = 8192
NFFT = 8192           # 제로패딩 FFT 길이(빗살 격자 2.405 Hz; 512점 원격자 38.5 Hz 는 ±8 창이 빔)
COMB_TOL_HZ = 8.0     # 빗살 허용폭 ±8 Hz (표준 레시피)
AC_MIN_HZ = 8.0       # AC 대역 하한 — DC 근방(|fr|<8 Hz) 제외(창별 평균 제거 후 잔류 누설 방지)
SEED = 20260815       # 널 대조 씨앗(고정)
C_LIGHT = 299_792_458.0

# 표준 팔 선택 규칙(위 모듈 주석 참조) — 태그 없는 접두사 = 기본 기체(matrice4e)
CHOSEN_ARM = {
    "ours": {
        "matrice4e": "ours_r15_n8192",
        "mini5pro": "ours_mini5pro_r15_n8192",
        "s1000plus": "ours_s1000plus_r15_n8192",
    },
    "sionna": {
        "matrice4e": "sionna_p4000000000_r15_n8192_d1",
        "mini5pro": "sionna_p4000000000_mini5pro_r15_n8192_d1",
        "s1000plus": "sionna_p4000000000_s1000plus_r15_n8192_d1",
    },
}
ENGINES = ["ours", "sionna"]


# --------------------------------------------------------------------------- #
#  1) 원장 로드 + 팔 목록 문서화(키를 실제로 뒤진다)
# --------------------------------------------------------------------------- #
def load_ledger():
    with open(LEDGER_JSON, encoding="utf-8") as f:
        led = json.load(f)
    npz = np.load(LEDGER_NPZ)
    return led, npz


def inventory_arms(npz) -> dict:
    """npz 키를 전부 뒤져 팔(접두사)별로 기체 태그·앙각·자세 수를 문서화한다."""
    inv: dict[str, dict] = {}
    for key in npz.files:
        if "/" not in key:            # phase_sign_v2 같은 메타 키
            continue
        prefix, elkey = key.split("/", 1)
        tag = "matrice4e"             # 태그 없음 = 기본 기체(원장 _meta.drone)
        for a in ("mini5pro", "s1000plus"):
            if a in prefix:
                tag = a
        d = inv.setdefault(prefix, {"airframe": tag, "elevations": [], "n_poses": int(npz[key].shape[0])})
        d["elevations"].append(elkey)
    for d in inv.values():
        d["elevations"] = sorted(d["elevations"])
        d["n_elevations"] = len(d["elevations"])
    return inv


# --------------------------------------------------------------------------- #
#  2) 스펙 템플릿(데이터에 맞추지 않음) + 원장 교차확인
# --------------------------------------------------------------------------- #
def spec_templates(lam_m: float) -> dict:
    out = {}
    for a in AIRFRAMES:
        s = DRONES[a]
        f_flash = s.prop_blades * s.hover_rpm / 60.0
        v_tip = math.pi * (s.prop_dia_mm / 1000.0) * s.hover_rpm / 60.0
        out[a] = {
            "prop_blades": s.prop_blades,
            "hover_rpm": s.hover_rpm,
            "prop_dia_mm": s.prop_dia_mm,
            "f_flash_hz_spec": round(f_flash, 3),
            "f_tip_hz_spec_el0": round(2.0 * v_tip / lam_m, 1),
        }
    return out


def crosscheck_rows(led, templates, lam_m) -> dict:
    """원장 rows 의 f_tip_hz(스펙식과), track.beat_hz(스펙 f_flash 와) 대조."""
    rows = led["rows"]
    per_arm = {}
    max_ftip_diff = 0.0
    for eng in ENGINES:
        for a in AIRFRAMES:
            arm = CHOSEN_ARM[eng][a]
            rs = [r for r in rows if r["engine"] == arm]
            t = templates[a]
            v_tip = math.pi * (t["prop_dia_mm"] / 1000.0) * t["hover_rpm"] / 60.0
            beats, ftip_diffs = [], []
            for r in rs:
                f_tip_spec = 2.0 * v_tip / lam_m * math.cos(math.radians(r["el_deg"]))
                d = abs(r["f_tip_hz"] - f_tip_spec)
                ftip_diffs.append(d)
                max_ftip_diff = max(max_ftip_diff, d)
                b = (r.get("track") or {}).get("beat_hz")
                if b is not None:
                    beats.append(b)
            med_beat = float(np.median(beats)) if beats else None
            per_arm[arm] = {
                "airframe": a,
                "n_rows": len(rs),
                "beat_hz_row_median": None if med_beat is None else round(med_beat, 2),
                "f_flash_hz_spec": t["f_flash_hz_spec"],
                "beat_minus_spec_hz": None if med_beat is None else round(med_beat - t["f_flash_hz_spec"], 2),
                "f_tip_absdiff_hz_max": round(max(ftip_diffs), 3) if ftip_diffs else None,
            }
    return {"per_arm": per_arm, "f_tip_absdiff_hz_max_overall": round(max_ftip_diff, 3),
            "note_ko": ("beat 중앙값 사용 — 원장 자체 추적기가 일부 앙각에서 고조파(2×)나 "
                        "하위 성분을 무는 행이 있어(예: mini el−15 의 367 Hz) 중앙값으로 대조한다.")}


# --------------------------------------------------------------------------- #
#  3) 빗살 정합 분류기
# --------------------------------------------------------------------------- #
def comb_masks(freqs: np.ndarray, f_flash: float) -> np.ndarray:
    """|fr| 이 f_flash 의 정수배 k≥1 에서 ±COMB_TOL_HZ 이내인 빈."""
    fa = np.abs(freqs)
    k = np.round(fa / f_flash)
    return (k >= 1) & (np.abs(fa - k * f_flash) <= COMB_TOL_HZ)


def window_scores(E: np.ndarray, prf: float, cand_f: dict) -> np.ndarray:
    """창별 × 후보별 빗살 몫[0..1]. 반환 shape = (N_WIN, n_cand). 후보 순서 = AIRFRAMES."""
    freqs = np.fft.fftfreq(NFFT, d=1.0 / prf)
    ac = np.abs(freqs) >= AC_MIN_HZ
    masks = {a: comb_masks(freqs, cand_f[a]) & ac for a in AIRFRAMES}
    han = np.hanning(WIN_LEN)
    out = np.zeros((N_WIN, len(AIRFRAMES)))
    for w in range(N_WIN):
        x = E[w * WIN_LEN:(w + 1) * WIN_LEN]
        x = x - x.mean()                       # ⭐창별 DC(정지성분) 제거 — 오늘의 교훈
        P = np.abs(np.fft.fft(x * han, NFFT)) ** 2
        tot = P[ac].sum()
        for j, a in enumerate(AIRFRAMES):
            out[w, j] = P[masks[a]].sum() / tot if tot > 0 else 0.0
    return out


def whole_series_scores(E: np.ndarray, prf: float, cand_f: dict) -> np.ndarray:
    """교차확인용: 8192 전체를 한 번에(원격자 2.405 Hz, 제로패딩 없음)."""
    n = E.size
    freqs = np.fft.fftfreq(n, d=1.0 / prf)
    ac = np.abs(freqs) >= AC_MIN_HZ
    x = (E - E.mean()) * np.hanning(n)
    P = np.abs(np.fft.fft(x)) ** 2
    tot = P[ac].sum()
    return np.array([P[comb_masks(freqs, cand_f[a]) & ac].sum() / tot for a in AIRFRAMES])


def coverage_fracs(prf: float, cand_f: dict) -> dict:
    """백색잡음 기대 빗살 몫 = AC 빈 중 빗살 마스크 비율(널 쏠림 기전의 문서화)."""
    freqs = np.fft.fftfreq(NFFT, d=1.0 / prf)
    ac = np.abs(freqs) >= AC_MIN_HZ
    return {a: round(float((comb_masks(freqs, cand_f[a]) & ac).sum() / ac.sum()), 4) for a in AIRFRAMES}


# --------------------------------------------------------------------------- #
#  4) 실행 — 혼동행렬(엔진×앙각) + 널 대조 + 전체시계열 교차확인
# --------------------------------------------------------------------------- #
def elkey_of(el: float) -> str:
    return f"el+{int(round(el))}" if el >= 0 else f"el{int(round(el))}"


def run():
    t0 = time.time()
    led, npz = load_ledger()
    meta = led["_meta"]
    prf = float(meta["prf_hz"])
    lam = C_LIGHT / float(meta["fc_hz"])
    els = [float(e) for e in meta["elevations_deg"]]

    inv = inventory_arms(npz)
    templates = spec_templates(lam)
    cand_f = {a: templates[a]["f_flash_hz_spec"] for a in AIRFRAMES}
    xcheck = crosscheck_rows(led, templates, lam)
    cover = coverage_fracs(prf, cand_f)

    # 표준 팔 존재 검증(키를 실제로 뒤진 목록과 대조)
    for eng in ENGINES:
        for a in AIRFRAMES:
            arm = CHOSEN_ARM[eng][a]
            assert arm in inv, f"표준 팔이 원장에 없음: {arm}"
            assert inv[arm]["n_poses"] == N_WIN * WIN_LEN, f"{arm}: n_poses={inv[arm]['n_poses']}"
            assert inv[arm]["n_elevations"] == len(els), f"{arm}: 앙각 {inv[arm]['n_elevations']}개"

    rng = np.random.default_rng(SEED)
    results = {}
    whole = {}
    for eng in ENGINES:
        per_el = {}
        agg = np.zeros((3, 3), dtype=int)
        agg_null = np.zeros((3, 3), dtype=int)
        margins = []          # (정답 몫 − 차점 몫) — 판정 여유
        for el in els:
            cm = np.zeros((3, 3), dtype=int)          # 행=정답, 열=예측
            cm_null = np.zeros((3, 3), dtype=int)
            for i, a in enumerate(AIRFRAMES):
                arm = CHOSEN_ARM[eng][a]
                E = np.asarray(npz[f"{arm}/{elkey_of(el)}"])
                sc = window_scores(E, prf, cand_f)
                pred = sc.argmax(axis=1)
                for p in pred:
                    cm[i, p] += 1
                srt = np.sort(sc, axis=1)
                margins.extend((sc[:, i] - np.where(pred == i, srt[:, -2], srt[:, -1])).tolist())
                # 널 대조: 같은 팔의 자세 순서를 통째로 섞고 같은 파이프라인
                En = E[rng.permutation(E.size)]
                for p in window_scores(En, prf, cand_f).argmax(axis=1):
                    cm_null[i, p] += 1
                # 전체 시계열(8192) 교차확인 — 팔·앙각당 판정 1개
                wpred = int(whole_series_scores(E, prf, cand_f).argmax())
                whole.setdefault(eng, {}).setdefault(a, {})[elkey_of(el)] = {
                    "pred": AIRFRAMES[wpred], "correct": bool(wpred == i)}
            n_el = cm.sum()
            per_el[f"{el:+.0f}"] = {
                "confusion": cm.tolist(),
                "accuracy": round(float(np.trace(cm)) / n_el, 4),
                "null_confusion": cm_null.tolist(),
                "null_accuracy": round(float(np.trace(cm_null)) / n_el, 4),
            }
            agg += cm
            agg_null += cm_null
        n_all = agg.sum()
        results[eng] = {
            "per_elevation": per_el,
            "aggregate_confusion": agg.tolist(),
            "aggregate_accuracy": round(float(np.trace(agg)) / n_all, 4),
            "null_aggregate_confusion": agg_null.tolist(),
            "null_aggregate_accuracy": round(float(np.trace(agg_null)) / n_all, 4),
            "n_windows_total": int(n_all),
            "decision_margin_median": round(float(np.median(margins)), 4),
        }

    # 전체 시계열 교차확인 요약
    for eng in ENGINES:
        ok = sum(v["correct"] for a in AIRFRAMES for v in whole[eng][a].values())
        tot = sum(len(whole[eng][a]) for a in AIRFRAMES)
        whole[eng]["_accuracy"] = round(ok / tot, 4)

    payload = {
        "_meta": {
            "generator": "benchmark/classify_airframe.py",
            "question_ko": "마이크로도플러 무늬(박자 빗살)만 보고 기체를 맞히나 — 분류 첫 실험",
            "sources": {"ledger_json": LEDGER_JSON, "ledger_npz": LEDGER_NPZ,
                        "templates": "src/drones.py DRONES (스펙에서 계산, 데이터에 맞추지 않음)"},
            "prf_hz": prf, "fc_hz": float(meta["fc_hz"]), "lambda_m": round(lam, 6),
            "elevations_deg": els,
            "window": {"n_windows": N_WIN, "win_len_poses": WIN_LEN, "nfft_zeropad": NFFT,
                       "grid_hz": round(prf / NFFT, 3),
                       "why_zeropad_ko": "512점 원격자 38.5 Hz 로는 ±8 Hz 빗살 창에 빈이 안 들어간다 — "
                                         "제로패딩은 정보를 만들지 않고 스펙트럼을 보간만 한다"},
            "comb_tol_hz": COMB_TOL_HZ, "ac_min_hz": AC_MIN_HZ,
            "dc_note_ko": "⭐창별로 시계열 평균(DC=정지성분)을 빼고 나서 잰다 — DC 를 끼우면 수 dB 아티팩트",
            "null_seed": SEED,
            "null_mechanism_ko": ("섞기로 스펙트럼이 백색화되면 raw 빗살 몫 ≈ 덮개율이고, 덮개율은 "
                                  "f_flash 최소(=이빨 최다)인 matrice4e 가 최대 → 널은 matrice4e 고정 "
                                  "예측으로 쏠려 균형 3클래스에서 정답률 1/3 이 된다"),
            "el_minus90_note_ko": ("−90°(직하방)는 f_tip=0 이라 f_tip 기반 대역 잣대가 퇴화한다. 본 "
                                   "분류기는 모든 앙각에서 전체 AC 빗살 몫으로 재므로 식은 정의되지만, "
                                   "물리적으로 마이크로도플러가 원리적으로 사라지는 앙각이라 −90° 성적은 "
                                   "잔결 구조만 시험한다 — 별도 앙각별 표에서 확인하라"),
            "chance_level": round(1.0 / 3.0, 4),
            "elapsed_s": None,  # 아래에서 채움
        },
        "arms_inventory": inv,
        "chosen_arms": CHOSEN_ARM,
        "airframes": AIRFRAMES,
        "templates": {a: {**templates[a], "comb_coverage_frac": cover[a]} for a in AIRFRAMES},
        "crosscheck_vs_ledger_rows": xcheck,
        "results": results,
        "whole_series_crosscheck": whole,
        "confusion_layout": "행=정답 기체, 열=예측 기체, 순서=airframes",
    }
    payload["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    return payload


# --------------------------------------------------------------------------- #
#  5) 그림 — 엔진별 혼동행렬(실측/널) + 앙각별 정확도 (전부 영어)
# --------------------------------------------------------------------------- #
def make_figure(payload):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    INK, INK2 = "#0b0b0b", "#52514e"
    BLUE, ORANGE = "#2a78d6", "#eb6834"
    GRID = "#d8d7d3"
    cmap = LinearSegmentedColormap.from_list("seq_blue", ["#f5f9fd", "#17457f"])
    LBL = {"mini5pro": "Mini 5 Pro", "matrice4e": "Matrice 4E", "s1000plus": "S1000+"}
    labels = [LBL[a] for a in payload["airframes"]]
    ENG_TITLE = {"ours": "Our kernel", "sionna": "Sionna PathSolver"}

    fig = plt.figure(figsize=(12.6, 8.4), dpi=160)
    gs = fig.add_gridspec(2, 4, height_ratios=[1.12, 1.0],
                          left=0.065, right=0.985, top=0.815, bottom=0.075,
                          hspace=0.45, wspace=0.38)
    fig.suptitle("Airframe classification from micro-Doppler comb matching",
                 fontsize=14, fontweight="bold", color=INK, y=0.978)
    fig.text(0.065, 0.935,
             "Per-window comb score: DC-removed AC spectrum, energy within ±8 Hz of integer multiples of each "
             "spec-predicted flash rate.\n16 non-overlapping windows × 512 poses per arm; templates from airframe "
             "specs (blades × hover RPM / 60), never fitted to data.",
             fontsize=8.5, color=INK2, va="top")

    def draw_cm(ax, cm, title, vmax):
        cm = np.asarray(cm, float)
        ax.imshow(cm, cmap=cmap, vmin=0, vmax=vmax, aspect="equal")
        n_row = cm.sum(axis=1, keepdims=True)
        for i in range(3):
            for j in range(3):
                frac = cm[i, j] / n_row[i, 0] if n_row[i, 0] else 0.0
                col = "white" if cm[i, j] > 0.55 * vmax else INK
                ax.text(j, i - 0.13, f"{int(cm[i, j])}", ha="center", va="center",
                        fontsize=10, fontweight="bold", color=col)
                ax.text(j, i + 0.24, f"{100 * frac:.0f}%", ha="center", va="center",
                        fontsize=7.5, color=col)
        ax.set_xticks(range(3), labels, fontsize=7.5, color=INK)
        ax.set_yticks(range(3), labels, fontsize=7.5, color=INK)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.set_title(title, fontsize=9.5, color=INK, pad=8)
        ax.set_xlabel("Predicted", fontsize=8, color=INK2)

    for k, eng in enumerate(ENGINES):
        r = payload["results"][eng]
        vmax = max(np.max(r["aggregate_confusion"]), 1)
        ax = fig.add_subplot(gs[0, 2 * k])
        draw_cm(ax, r["aggregate_confusion"],
                f"{ENG_TITLE[eng]} — real\naccuracy {100 * r['aggregate_accuracy']:.1f}%", vmax)
        if k == 0:
            ax.set_ylabel("True airframe", fontsize=8, color=INK2)
        ax2 = fig.add_subplot(gs[0, 2 * k + 1])
        draw_cm(ax2, r["null_aggregate_confusion"],
                f"{ENG_TITLE[eng]} — shuffled null\naccuracy {100 * r['null_aggregate_accuracy']:.1f}%", vmax)

    # 아래 행: 앙각별 정확도(실측 vs 널 vs 우연)
    els = payload["_meta"]["elevations_deg"]
    for k, eng in enumerate(ENGINES):
        ax = fig.add_subplot(gs[1, 2 * k:2 * k + 2])
        per = payload["results"][eng]["per_elevation"]
        acc = [100 * per[f"{e:+.0f}"]["accuracy"] for e in els]
        nul = [100 * per[f"{e:+.0f}"]["null_accuracy"] for e in els]
        ax.plot(els, acc, "-o", color=BLUE, lw=2, ms=5, label="Real")
        ax.plot(els, nul, "-s", color=ORANGE, lw=2, ms=4, label="Shuffled null")
        ax.axhline(100 / 3, color=INK2, lw=1, ls=(0, (4, 3)), label="Chance (1/3)")
        ax.set_xlim(2, -92)
        ax.set_ylim(-4, 104)
        ax.set_xticks(els)
        ax.set_xlabel("Elevation [deg]  (0 = side view, −90 = nadir)", fontsize=8.5, color=INK2)
        if k == 0:
            ax.set_ylabel("Accuracy over 48 windows [%]", fontsize=8.5, color=INK2)
        ax.set_title(f"{ENG_TITLE[eng]} — accuracy vs elevation", fontsize=9.5, color=INK)
        ax.grid(color=GRID, lw=0.6, alpha=0.7)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=7.5)
        ax.legend(loc="center left", fontsize=8, frameon=False)
        # −90° 각주(정직): f_tip=0 — 잔결 구조만 시험
        ax.annotate("f_tip = 0 at −90°:\nmicro-Doppler vanishes\nin principle (residual only)",
                    xy=(-90, acc[-1]), xytext=(-64, 62), fontsize=7, color=INK2,
                    arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------------------- #
#  6) 자가검사
# --------------------------------------------------------------------------- #
def selftest(payload) -> list[str]:
    msgs = []

    def chk(name, ok, detail=""):
        msgs.append(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        return ok

    ok = True
    m = payload["_meta"]
    # 창 개수·산출물
    for eng in ENGINES:
        r = payload["results"][eng]
        ok &= chk(f"{eng}: 창 수 = 3기체×7앙각×16창", r["n_windows_total"] == 3 * 7 * 16,
                  f"{r['n_windows_total']}")
        ok &= chk(f"{eng}: 실측 정확도 > 널 정확도",
                  r["aggregate_accuracy"] > r["null_aggregate_accuracy"],
                  f"{r['aggregate_accuracy']:.3f} vs {r['null_aggregate_accuracy']:.3f}")
        ok &= chk(f"{eng}: 널 ≈ 우연(1/3±0.15)",
                  abs(r["null_aggregate_accuracy"] - 1 / 3) < 0.15,
                  f"{r['null_aggregate_accuracy']:.3f}")
    # 스펙 f_tip 교차확인(원장 rows 와 1 Hz 이내)
    d = payload["crosscheck_vs_ledger_rows"]["f_tip_absdiff_hz_max_overall"]
    ok &= chk("스펙식 f_tip ↔ 원장 rows f_tip (최대 |Δ| < 1 Hz)", d < 1.0, f"{d} Hz")
    # 파일 존재
    ok &= chk("JSON 생성", os.path.getsize(OUT_JSON) > 1000, OUT_JSON)
    ok &= chk("PNG 생성", os.path.getsize(OUT_FIG) > 10000, OUT_FIG)
    msgs.append(f"[{'PASS' if ok else 'FAIL'}] 종합")
    return msgs


def main():
    payload = run()
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    make_figure(payload)
    print("=== 기체 분류 첫 실험 — 박자 빗살 정합 ===")
    for a in AIRFRAMES:
        t = payload["templates"][a]
        print(f"  템플릿 {a:10s}: f_flash={t['f_flash_hz_spec']:7.2f} Hz "
              f"(날개 {t['prop_blades']} × rpm {t['hover_rpm']}), 덮개율 {t['comb_coverage_frac']:.3f}")
    for eng in ENGINES:
        r = payload["results"][eng]
        print(f"  {eng:6s}: 정확도 {100 * r['aggregate_accuracy']:.1f}% "
              f"(널 {100 * r['null_aggregate_accuracy']:.1f}%, 창 {r['n_windows_total']}개, "
              f"전체시계열 교차확인 {100 * payload['whole_series_crosscheck'][eng]['_accuracy']:.1f}%)")
        for e in payload["_meta"]["elevations_deg"]:
            pe = r["per_elevation"][f"{e:+.0f}"]
            print(f"      el {e:+5.0f}°: acc {100 * pe['accuracy']:5.1f}%  null {100 * pe['null_accuracy']:5.1f}%")
    msgs = selftest(payload)
    print("=== 자가검사 ===")
    for msg in msgs:
        print("  " + msg)
    if any(msg.startswith("[FAIL]") for msg in msgs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
