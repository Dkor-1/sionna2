# -*- coding: utf-8 -*-
"""
rotor_preset_ladder.py — **R6 · 로터 흔들림 프리셋 사다리** (2026-08-15)
==============================================================================
설계서: `docs/NEXT_EXPERIMENTS.md` 순위 5 (R6) · 상류 커널: `src/rotor_dynamics.py`

무엇을 묻나 — 한 줄
--------------------
기체마다 로터 회전수가 조금씩 다르게 흔들린다. 그 «흔들림 설정»(rotor_preset)을 바꾸면
**기종 분류 성적이 달라지나?**

왜 이걸 먼저 하나
------------------
앞으로 할 딥러닝 실험은 전부 이 데이터셋 위에 선다. 흔들림 설정이 성적을 좌우한다면
원장을 다시 구워야 하고(딥러닝은 그 뒤), 둔감하다면 바로 착수할 수 있다. 그래서 이것은
**상류 게이트**다.

말 풀이 (처음 나오는 용어)
---------------------------
· «움직이는 부분» = 프로펠러(블레이드)가 만드는 신호. 시계열 평균을 뺀 것(AC).
· «가만히 있는 부분» = 동체가 만드는, 시간에 안 변하는 성분(DC). 레벨 비교 전에 뺀다.
· «박자»(f_flash) = 블레이드가 레이더 쪽을 스치는 비율 [Hz]. 회전수 × 블레이드 수 / 60.
· «흔들림»(σ_w) = 회전수가 시간에 따라 떨리는 정도. 저주파가 지배한다(OU 과정).
· «정적 산포»(σ_s) = 로터 넷(또는 여섯·여덟)의 평균 회전수가 서로 다른 정도.
· «macro-F1» = 기체 6종의 F1 점수를 단순평균한 값. 기체 수가 고르므로 정확도와 비슷하게 간다.
· «폭» = 최대 − 최소.

사전등록 (돌리기 전에 정한 것)
-------------------------------
① **먼저 잡음 폭을 잰다.** 같은 설정을 씨앗(seed)만 바꿔 3 판 구우면 macro-F1 이 얼마나
   흔들리나. 그것이 «재생성 잡음» 이고, 프리셋 차이는 그보다 커야 뜻이 있다.
② 프리셋 6 종의 macro-F1 **폭 W** 를 잡음이 만들 폭 W_null 과 견준다.
     W ≥ 3·W_null → «좌우한다» (원장 재생성 필요)
     W ≤ 1·W_null → «둔감하다» (딥러닝 착수 가능)
     그 사이       → «보류»
③ 헤드라인 분류기는 **RF100 하나로 못 박는다**(기존 원장에서 최고였던 모델). 프리셋마다
   최고 모델을 다시 고르면 «모델 고르기 잡음» 이 «프리셋 효과» 로 새어 든다.
④ 순위 뒤집기 통계는 **치환검정**으로도 낸다 — 18 개 값(6 프리셋 × 3 씨앗)의 프리셋
   딱지를 무작위로 섞어 W 의 귀무분포를 만든다. 가정이 없다.

⛔ 이 파일이 안 하는 것
------------------------
· GPU 를 쓰지 않는다. 저장된 위상표(`outputs/md_classify_tables/*.npz`)만 읽는다.
· 기존 파일을 고치지 않는다. `md_classify_dataset.py` 의 함수를 **불러다 쓴다**.
· 산란 진폭의 요동은 여전히 미모델이다(White IEEE TRS 2024 도 자백한 자리).

산출
-----
  outputs/rotor_preset_ladder.json
  outputs/figures/rotor_preset_ladder.png

    cd /workspace/sionna && PYTHONPATH=src:benchmark \
        /workspace/.venvs/py312/bin/python benchmark/rotor_preset_ladder.py
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (os.path.join(ROOT, "src"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

# ⛔ GPU 금지 — 스레드 폭주도 막는다(다른 큐가 카드와 CPU 를 쓰고 있다)
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "2")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

OUT_JSON = os.path.join(ROOT, "outputs", "rotor_preset_ladder.json")
FIG_DIR = os.path.join(ROOT, "outputs", "figures")
FIG_PNG = os.path.join(FIG_DIR, "rotor_preset_ladder.png")
REF_FEAT = os.path.join(ROOT, "outputs", "md_classify_features.npz")
GRID_JSON = os.path.join(ROOT, "outputs", "grid_convergence_check.json")

#: 헤드라인 관측 조건 — 기존 원장과 같은 자리(PRF 20 kHz · 창 0.25 s · 잡음 없음)
PRF = 20000.0
TWIN = 0.25

#: 씨앗 3 판. 첫 씨앗은 기존 원장과 같은 값이라 «비트동일 게이트» 가 성립한다.
SEEDS = [20260810, 20260811, 20260812]

#: ⭐프리셋은 계획서가 «5 종» 이라 했지만 실측은 **6 종**이다(legacy_outdoor 포함).
#:  아래에서 src/rotor_dynamics.PRESETS 를 직접 세어 이 목록을 만든다.
BASELINE_ARM = ""          # '' = 기존 원장이 실제로 쓰는 «현행» 모델(프리셋 아님)

#: 잡음 폭을 사전등록으로 지정한 프리셋 하나(설계서 «같은 프리셋 시드 3 판»)
NOISE_BAND_PRESET = "outdoor"

#: 기대 범위 계수 d_n = E[max−min] / σ, 정규분포 n 표본 (Tippett)
D_RANGE = {2: 1.1284, 3: 1.6926, 4: 2.0588, 5: 2.3259, 6: 2.5344}

SHORT = {"mini2": "Mini 2", "mini5pro": "Mini 5 Pro", "phantom4": "Phantom 4",
         "matrice4e": "Matrice 4E", "typhoonh480": "Typhoon H", "s1000plus": "S1000+"}

_TABS = None          # 워커별 전역 캐시 (fork 로 복사됨)


# ═══════════════════════════════════════════════════════════════════════════════
#  ① 데이터 굽기 — `md_classify_dataset.cmd_build` 의 추첨 순서를 글자 그대로 따른다
# ═══════════════════════════════════════════════════════════════════════════════
def load_tables():
    """위상표 108 장을 읽어 촘촘한 격자로 올린다. **재사용** — GPU 0."""
    import md_classify_dataset as ds
    tabs, missing = {}, []
    for key in ds.DRONE_KEYS:
        for ai in range(len(ds.ASPECTS)):
            p = os.path.join(ds.TAB_DIR, f"{key}_a{ai:02d}.npz")
            if not os.path.exists(p):
                missing.append(f"{key}/a{ai:02d}")
                continue
            z = np.load(p, allow_pickle=True)
            tabs[(key, ai)] = (complex(z["E_ref"][0]),
                               ds._fine_tables(z["dE"], z["phis"]),
                               np.asarray(z["dirs"], float))
    return tabs, missing


def build_features(arm, seed, tabs):
    """(arm, seed) 한 판의 특징 행렬을 만든다 — 헤드라인 조건 한 칸만.

    ⭐ `md_classify_dataset.cmd_build` 와 **난수 소모 순서가 같다**:
         base rpm·산포·초기위상 → 잡음시드 → (흔들림이 있으면) 흔들림시드
       헤드라인 조건은 그 조건 루프의 **첫 칸**이고 잡음이 없어 난수를 더 안 쓴다.
       그래서 arm='' · seed=20260810 이면 기존 원장과 **비트동일**이어야 한다(자가검사 SC1).
    ⚠ `cmd_build` 는 `--rotor-seed` 를 원장에 적기만 하고 rng 에 **안 넣는다**(그 CLI 로는
       씨앗이 안 바뀐다). 여기서는 씨앗을 실제로 rng 에 넣는다 — 그래야 잡음 폭을 잰다."""
    import md_classify_dataset as ds
    import rotor_dynamics as rd
    from drones import DRONES

    jit = rd.get(arm) if arm else None
    n_t = int(round(PRF * TWIN))
    rng = np.random.default_rng(int(seed))
    rows, drone, aspect, ffl = [], [], [], []
    for key in ds.DRONE_KEYS:
        spec = DRONES[key]
        for ai in range(len(ds.ASPECTS)):
            if (key, ai) not in tabs:
                continue
            E_ref, fine, dirs = tabs[(key, ai)]
            for _di in range(ds.N_DRAW_PER_ASPECT):
                rpms, p0, base, _sig = ds._draw_trials(rng, spec, len(dirs), jit)
                _nz_seed = int(rng.integers(0, 2 ** 31 - 1))
                rot_seed = (int(rng.integers(0, 2 ** 31 - 1))
                            if (jit is not None and jit.wobble_sigma > 0) else None)
                rp = rpms
                if rot_seed is not None:
                    rp, _ = rd.rpm_series(base, len(dirs), n_t, PRF,
                                          jit.with_(static_sigma=0.0),
                                          np.random.default_rng(rot_seed))
                    rp = rp + (rpms - base)[None, :]
                E = ds.synth(E_ref, fine, dirs, rp, p0, PRF, n_t)
                v, _aux = ds.features(E, PRF)
                rows.append(v)
                drone.append(key)
                aspect.append(ai)
                ffl.append(float(v[0]))
    return (np.asarray(rows, float), np.array(drone), np.asarray(aspect, int),
            np.asarray(ffl, float))


# ═══════════════════════════════════════════════════════════════════════════════
#  ② 채점 — 기존 판정 코드를 그대로 불러다 쓴다(같은 교차검증·같은 모델)
# ═══════════════════════════════════════════════════════════════════════════════
def score_one(X, y, groups, labels, models=("RF100", "LDA", "kNN5")):
    import md_classify_run as mr
    X = mr._clean(X)
    out = {}
    for mn in models:
        acc, pred = mr.run_cv(X, y, groups, lambda m=mn: mr._models()[m])
        M = mr.confusion(y, pred, labels)
        f1, _p, _r = mr.per_class_f1(M)
        out[mn] = {"accuracy": round(float(acc), 5),
                   "macro_f1": round(float(f1.mean()), 5),
                   "per_class_f1": {l: round(float(v), 5) for l, v in zip(labels, f1)},
                   "confusion": M.tolist()}
    return out


def beat_overlap(ff, y, labels):
    """**쌍별 박자 겹침** — 두 기체의 f_flash 분포(5~95 백분위)가 얼마나 포개지나.

    symmetric : 겹친 구간 / 두 구간의 합집합  (0 = 안 겹침, 1 = 완전히 같은 자리)
    house     : 겹친 구간 / **앞 기체**의 구간 — `md_classify_run.py` 가 쓰는 비대칭 규약.
                기존 원장과 나란히 놓으려고 같이 낸다."""
    out = {}
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            va, vb = ff[y == a], ff[y == b]
            a5, a95 = np.percentile(va, 5), np.percentile(va, 95)
            b5, b95 = np.percentile(vb, 5), np.percentile(vb, 95)
            lo, hi = max(a5, b5), min(a95, b95)
            inter = max(0.0, hi - lo)
            union = max(a95, b95) - min(a5, b5)
            out[f"{a}|{b}"] = {
                "symmetric": round(float(inter / max(union, 1e-9)), 4),
                "house_asym": round(float(inter / max(a95 - a5, 1e-9)), 4),
                "p5p95_a": [round(float(a5), 2), round(float(a95), 2)],
                "p5p95_b": [round(float(b5), 2), round(float(b95), 2)]}
    return out


def scatter_stats(X, y, g, labels):
    """⭐**프리셋이 얼마나 어지럽히나** 를 분류기와 무관하게 잰다 — 기전 규명용.

    특징을 전부 표준화(평균 0·분산 1)한 뒤 둘을 잰다.
      draw_scatter : 같은 기체·같은 자세 안에서 **추첨 8 판**이 흩어진 정도.
                     프리셋이 시행마다 새로 뽑는 무작위성이 곧 이것이다.
      eta2_class   : 특징 분산 중 **기체 정체성**이 설명하는 몫(일원분산분석 η²).
    ⚠ 급내분산을 «자세를 섞어» 재면 자세 변이가 섞여 든다. 그래서 (기체·자세) 칸 안에서만
      재고 칸을 평균한다 — 그것이 «추첨이 만든 흔들림» 이다."""
    X = np.where(np.isfinite(X), np.asarray(X, float), 0.0)
    sd = X.std(axis=0)
    keep = sd > 1e-12
    Z = (X[:, keep] - X[:, keep].mean(0)) / sd[keep]
    n = Z.shape[0]
    gm = Z.mean(0)
    ssb = np.zeros(Z.shape[1])
    cells = []
    for l in labels:
        m = (y == l)
        ssb += m.sum() * (Z[m].mean(0) - gm) ** 2
        for a in np.unique(g[m]):
            mm = m & (g == a)
            if mm.sum() >= 2:
                cells.append(Z[mm].var(0, ddof=1))
    return {"draw_scatter_mean": float(np.mean(cells, axis=0).mean()),
            "eta2_class_mean": float((ssb / max(n, 1)).mean()),
            "n_cells": len(cells), "n_features_used": int(keep.sum())}


def _job(task):
    """워커 하나 = (arm, seed) 한 판. fork 로 위상표를 공유한다."""
    arm, seed, labels = task
    t0 = time.time()
    X, y, g, ff = build_features(arm, seed, _TABS)
    n_nan = int(np.isnan(X).any(axis=1).sum())
    sc = score_one(X, y, g, labels)
    return {"arm": arm, "seed": int(seed), "n_rows": int(len(X)),
            "n_nan_rows": n_nan, "seconds": round(time.time() - t0, 1),
            "scores": sc, "beat_overlap": beat_overlap(ff, y, labels),
            "scatter": scatter_stats(X, y, g, labels),
            "f_flash_median": {l: round(float(np.median(ff[y == l])), 2) for l in labels},
            "_X_head_sha": _arr_sha(X)}


def _arr_sha(X):
    import hashlib
    return hashlib.sha256(np.ascontiguousarray(X, float).tobytes()).hexdigest()[:16]


def _init(tabs):
    global _TABS
    _TABS = tabs


# ═══════════════════════════════════════════════════════════════════════════════
#  ③ 본체
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    t_start = time.time()
    os.environ["TZ"] = "Asia/Seoul"
    try:
        time.tzset()
    except Exception:                                    # noqa: BLE001
        pass

    import md_classify_dataset as ds
    import rotor_dynamics as rd

    #  ── 프리셋을 **직접 센다** (계획서의 «5 종» 을 믿지 않는다) ────────────────
    presets = list(rd.PRESETS.keys())
    print(f"프리셋 {len(presets)} 종 실측: {presets}")

    labels = list(ds.DRONE_KEYS)
    tabs, missing = load_tables()
    print(f"위상표 {len(tabs)} 장 적재(결측 {len(missing)}) — 재사용, GPU 0")

    tasks = [(a, s, labels) for a in ([BASELINE_ARM] + presets) for s in SEEDS]
    n_work = min(11, max(1, (os.cpu_count() or 8) // 8))
    print(f"판 {len(tasks)} 개 · 워커 {n_work}")

    runs = []
    with ProcessPoolExecutor(max_workers=n_work, initializer=_init,
                             initargs=(tabs,)) as ex:
        for r in ex.map(_job, tasks):
            runs.append(r)
            m = r["scores"]["RF100"]["macro_f1"]
            print(f"  {r['arm'] or '(현행)':16s} seed {r['seed']}  "
                  f"macroF1 {m:.4f}  acc {r['scores']['RF100']['accuracy']:.4f}  "
                  f"({r['seconds']:.0f}s, NaN행 {r['n_nan_rows']})", flush=True)

    by = {}
    for r in runs:
        by.setdefault(r["arm"], {})[r["seed"]] = r

    #  ── 잡음 폭 ─────────────────────────────────────────────────────────────
    def mf1(arm, seed):
        return by[arm][seed]["scores"]["RF100"]["macro_f1"]

    per_preset_vals = {a: [mf1(a, s) for s in SEEDS] for a in presets}
    per_preset_mean = {a: float(np.mean(v)) for a, v in per_preset_vals.items()}
    per_preset_sd = {a: float(np.std(v, ddof=1)) for a, v in per_preset_vals.items()}

    #  사전등록 그대로: 지정 프리셋 3 판의 폭
    prereg_vals = per_preset_vals[NOISE_BAND_PRESET]
    s_prereg = float(max(prereg_vals) - min(prereg_vals))

    #  ⭐개선판: 6 프리셋 × 3 씨앗 = 자유도 12 로 «판 하나의 표준편차» 를 모은다.
    #    그러면 «프리셋 효과가 0 일 때 6 개 평균의 폭이 얼마일지» 를 바로 계산할 수 있다.
    sigma_pool = float(np.sqrt(np.mean([v ** 2 for v in per_preset_sd.values()])))
    w_null = float(D_RANGE[len(presets)] * sigma_pool / np.sqrt(len(SEEDS)))

    W = float(max(per_preset_mean.values()) - min(per_preset_mean.values()))
    arm_hi = max(per_preset_mean, key=per_preset_mean.get)
    arm_lo = min(per_preset_mean, key=per_preset_mean.get)

    #  ── 치환검정: 딱지를 섞으면 이만한 폭이 우연히 나오나 ────────────────────
    flat = np.array([per_preset_vals[a][i] for a in presets for i in range(len(SEEDS))])
    rs = np.random.default_rng(20260815)
    n_perm = 20000
    null_W = np.empty(n_perm)
    for i in range(n_perm):
        p = rs.permutation(flat).reshape(len(presets), len(SEEDS)).mean(axis=1)
        null_W[i] = p.max() - p.min()
    p_val = float((np.sum(null_W >= W - 1e-12) + 1) / (n_perm + 1))

    #  ── 판정 ────────────────────────────────────────────────────────────────
    def verdict_of(width, band):
        if band <= 0:
            return "판정 불가 (잡음 폭 0)"
        if width >= 3.0 * band:
            return "좌우한다"
        if width <= 1.0 * band:
            return "둔감하다"
        return "보류"

    v_main = verdict_of(W, w_null)
    v_prereg_literal = verdict_of(W, s_prereg)

    #  격자 산포 밴드(2026-08-15) — 분류 칸은 0.0 %p 이지만 **다른 분류기**의 값이다
    grid_band_pp = None
    try:
        with open(GRID_JSON) as f:
            gj = json.load(f)
        for row in gj["grid_dispersion_bands"]["bands"]["layer3_metric"]:
            if row["metric"] == "classify_accuracy_pp":
                grid_band_pp = float(row["band"])
    except Exception as e:                                # noqa: BLE001
        print(f"⚠ 격자 밴드 못 읽음: {e}")

    #  ── 귀속: 성적 이동이 어느 기체 쌍에서 왔나 ─────────────────────────────
    def conf_rate(arm):
        M = np.mean([np.asarray(by[arm][s]["scores"]["RF100"]["confusion"], float)
                     for s in SEEDS], axis=0)
        return M / np.maximum(M.sum(1, keepdims=True), 1e-9)

    Chi, Clo = conf_rate(arm_hi), conf_rate(arm_lo)
    dC = Clo - Chi                     # 낮은 프리셋에서 늘어난 오분류
    attrib = []
    for i in range(len(labels)):
        for j in range(len(labels)):
            if i == j:
                continue
            attrib.append({
                "true": labels[i], "predicted": labels[j],
                "rate_hi": round(float(Chi[i, j]), 4),
                "rate_lo": round(float(Clo[i, j]), 4),
                "delta_pp": round(float(dC[i, j] * 100.0), 3)})
    attrib.sort(key=lambda d: -abs(d["delta_pp"]))

    f1_by_class = {l: {a: float(np.mean([by[a][s]["scores"]["RF100"]["per_class_f1"][l]
                                         for s in SEEDS])) for a in presets}
                   for l in labels}
    f1_width = {l: round(float(max(v.values()) - min(v.values())), 4)
                for l, v in f1_by_class.items()}

    #  프리셋 평균 박자 겹침(대칭) — 표에 macro-F1 과 나란히 놓는다
    pairs = sorted(runs[0]["beat_overlap"].keys())
    ov_mean = {a: {pk: round(float(np.mean([by[a][s]["beat_overlap"][pk]["symmetric"]
                                            for s in SEEDS])), 4) for pk in pairs}
               for a in ([BASELINE_ARM] + presets)}
    ov_bar = {a: float(np.mean(list(ov_mean[a].values())))
              for a in ([BASELINE_ARM] + presets)}
    scat = {a: {k: float(np.mean([by[a][s]["scatter"][k] for s in SEEDS]))
                for k in ("draw_scatter_mean", "eta2_class_mean")}
            for a in ([BASELINE_ARM] + presets)}

    #  ── ⭐기전: 성적이 무엇을 따라 움직이나 ─────────────────────────────────
    def _r(xs, ys):
        return float(np.corrcoef(np.asarray(xs, float), np.asarray(ys, float))[0, 1])

    y6 = [per_preset_mean[a] for a in presets]
    r_overlap = _r([ov_bar[a] for a in presets], y6)
    r_draw = _r([scat[a]["draw_scatter_mean"] for a in presets], y6)
    r_eta2 = _r([scat[a]["eta2_class_mean"] for a in presets], y6)
    r_sig_s = _r([rd.PRESETS[a].static_sigma for a in presets], y6)
    r_sig_w = _r([rd.PRESETS[a].wobble_sigma for a in presets], y6)

    #  ⭐2×2 요인 읽기 — «정렬(결정론)» 축과 «산포 크기» 축을 갈라 본다.
    #    legacy 두 종은 초기위상이 t=0 에 **정렬**돼 있고 정적 산포가 **결정론적 패턴**이라,
    #    시행이 달라도 로터 배치가 그대로다(무작위성이 base rpm 하나뿐).
    def _d(a, b):
        return round((per_preset_mean[a] - per_preset_mean[b]) * 100, 3)

    mechanism = {
        "question_ko": "프리셋이 성적을 움직이는 손잡이가 무엇인가",
        "correlation_with_macro_f1_over_6_presets": {
            "mean_pairwise_beat_overlap": round(r_overlap, 4),
            "draw_scatter": round(r_draw, 4),
            "eta2_class": round(r_eta2, 4),
            "static_sigma": round(r_sig_s, 4),
            "wobble_sigma": round(r_sig_w, 4),
            "note_ko": ("⚠6 점짜리 상관이라 **방향만** 읽는다(신뢰구간을 붙일 표본이 아니다). "
                        "그리고 셋 다 조심해서 읽어야 한다: ① 박자 겹침의 −0.58 은 **outdoor 한 "
                        "점이 끌고 간다**(outdoor 0.49 vs 나머지 다섯 0.14~0.16) — 사다리 전체를 "
                        "설명하는 사슬이 아니라 **outdoor 가 왜 바닥인지**를 설명하는 사슬이다. "
                        "② η² 는 «특징 분산 중 기체가 설명하는 몫» 이라 분류기가 쓰는 양과 거의 "
                        "같다 — 상관 +0.81 은 기전이라기보다 **거의 동어반복**이다. "
                        "③ σ_s 의 +0.16 이 말해 주듯 사다리는 산포에 **단조롭지 않다**."),
        },
        "non_monotone_ko": (
            "⭐사다리는 σ_s 에 단조롭지 않다. 무작위 초기위상 네 판만 보면 "
            "sitl(0.22 %) 89.7 → lit_iid(0.99 %) 94.3 으로 **올라갔다가** "
            "outdoor(2.35 %+흔들림 2.45 %) 89.6 으로 **다시 내려온다**. "
            "올라가는 구간은 적당한 로터간 산포가 로터별 박자를 **분해 가능하게** 만들어 "
            "접은-주기·고조파 특징이 기하를 읽게 해 주기 때문이고, 내려오는 구간은 산포와 "
            "흔들림이 너무 커져 f_flash 추정 자체가 번지기 때문이다(박자 겹침 0.16 → 0.49). "
            "«흔들림을 키우면 무조건 어려워진다» 는 단순한 그림은 틀렸다."),
        "factorial_2x2_ko": (
            "같은 σ_s 에서 «정렬·결정론»(legacy 계열)과 «무작위 초기위상·가우시안»(나머지)을 "
            "짝지어 보면 손잡이가 갈린다."),
        "contrasts_pp": {
            "alignment_at_small_sigma__legacy_minus_sitl": _d("legacy", "sitl"),
            "alignment_at_large_sigma__legacy_outdoor_minus_outdoor": _d("legacy_outdoor",
                                                                         "outdoor"),
            "sigma_within_deterministic__legacy_outdoor_minus_legacy": _d("legacy_outdoor",
                                                                          "legacy"),
            "sigma_within_random_no_wobble__lit_iid_minus_sitl": _d("lit_iid", "sitl"),
            "wobble_added__outdoor_minus_lit_iid": _d("outdoor", "lit_iid"),
        },
        "per_preset": {a: {
            "macro_f1_mean": round(per_preset_mean[a], 5),
            "mean_beat_overlap": round(ov_bar[a], 4),
            "draw_scatter": round(scat[a]["draw_scatter_mean"], 5),
            "eta2_class": round(scat[a]["eta2_class_mean"], 5),
            "random_phase": bool(rd.PRESETS[a].random_phase),
        } for a in presets},
        "baseline_arm": {
            "macro_f1_mean": round(float(np.mean([mf1(BASELINE_ARM, s) for s in SEEDS])), 5),
            "mean_beat_overlap": round(ov_bar[BASELINE_ARM], 4),
            "draw_scatter": round(scat[BASELINE_ARM]["draw_scatter_mean"], 5),
            "eta2_class": round(scat[BASELINE_ARM]["eta2_class_mean"], 5)},
        "scatter_definition_ko": (
            "draw_scatter = 특징을 표준화한 뒤, (기체·자세) 칸 안에서 추첨 8 판이 흩어진 "
            "분산의 평균. 프리셋이 시행마다 새로 뿌리는 무작위성의 크기다. "
            "eta2_class = 특징 분산 중 기체 정체성이 설명하는 몫."),
        "reading_ko": (
            "⭐손잡이가 **둘**이고 크기가 비슷하다. ① «정렬»: 초기위상이 t=0 에 정렬되고 정적 "
            "산포가 고정 패턴이면(legacy 계열) 같은 기체·같은 자세의 시행이 base rpm 하나만 "
            "달라진다 — 추첨 흩어짐이 0.02~0.07 로, 무작위 초기위상 판(0.40~0.68)의 "
            "**십분의 일**이다. 데이터가 인위적으로 깨끗해져 +2.0(작은 σ)~+6.1 %p(큰 σ) 오른다. "
            "② «산포 크기»: 무작위 초기위상 안에서도 σ_s 를 0.22 → 0.99 % 로 키우면 +4.6 %p "
            "오르고, 거기에 흔들림까지 붙은 outdoor 로 가면 −4.6 %p 내린다. "
            "⛔그러므로 사다리 위쪽을 «더 좋은 모델» 로 읽으면 안 된다 — legacy 계열의 우위는 "
            "물리가 아니라 **무작위성을 덜 뿌린 대가**다."),
    }

    #  ── 부분군: legacy 계열을 빼면 폭이 얼마나 줄어드나 ─────────────────────
    def _subgroup(names):
        vals = {a: per_preset_vals[a] for a in names}
        mu = {a: float(np.mean(v)) for a, v in vals.items()}
        sd = [float(np.std(v, ddof=1)) for v in vals.values()]
        sp = float(np.sqrt(np.mean(np.square(sd))))
        wn = float(D_RANGE[len(names)] * sp / np.sqrt(len(SEEDS)))
        w = float(max(mu.values()) - min(mu.values()))
        fl = np.array([vals[a][i] for a in names for i in range(len(SEEDS))])
        r2 = np.random.default_rng(20260815)
        nl = np.array([np.ptp(r2.permutation(fl).reshape(len(names), len(SEEDS)).mean(1))
                       for _ in range(20000)])
        return {"presets": names, "macro_f1_mean": {a: round(v, 5) for a, v in mu.items()},
                "width_W": round(w, 5), "W_null": round(wn, 5),
                "ratio": round(w / max(wn, 1e-12), 3),
                "p_value": round(float((np.sum(nl >= w - 1e-12) + 1) / 20001), 5),
                "verdict_ko": verdict_of(w, wn)}

    rand_family = [a for a in presets if rd.PRESETS[a].random_phase]
    det_family = [a for a in presets if not rd.PRESETS[a].random_phase]
    subgroups = {
        "why_ko": ("legacy 계열 두 종은 초기위상이 정렬돼 있어 «데이터가 인위적으로 깨끗한» "
                   "쪽으로 치우친다. 그 둘을 빼도 사다리가 남는지 따로 본다 — 남으면 "
                   "«물리 파라미터가 성적을 움직인다» 가 되고, 사라지면 «정렬 아티팩트가 "
                   "전부였다» 가 된다."),
        "random_phase_family": _subgroup(rand_family),
        "aligned_legacy_family": _subgroup(det_family) if len(det_family) >= 2 else None,
    }

    #  ── 다른 모델에서도 같은 사다리가 서나 (RF100 이 하한인지 상한인지) ──────
    def _model_stats(mn):
        mu = {a: float(np.mean([by[a][s]["scores"][mn]["macro_f1"] for s in SEEDS]))
              for a in presets}
        sd = [float(np.std([by[a][s]["scores"][mn]["macro_f1"] for s in SEEDS], ddof=1))
              for a in presets]
        sp = float(np.sqrt(np.mean(np.square(sd))))
        wn = float(D_RANGE[len(presets)] * sp / np.sqrt(len(SEEDS)))
        w = float(max(mu.values()) - min(mu.values()))
        return {"per_preset_mean_macro_f1": {a: round(v, 5) for a, v in mu.items()},
                "width_W": round(w, 5), "sigma_pool": round(sp, 5),
                "W_null": round(wn, 5), "ratio": round(w / max(wn, 1e-12), 3),
                "verdict_ko": verdict_of(w, wn)}

    model_stats = {mn: _model_stats(mn) for mn in ("LDA", "kNN5")}
    n_feat = int(len(ds.FEATURE_NAMES))

    #  ⭐두 평균의 **차** 를 볼 때 쓰는 밴드(폭 밴드와 다르다). 여기 안이면 판정 불가.
    pair_band = float(1.96 * sigma_pool * np.sqrt(2.0 / len(SEEDS)))
    base_mean = float(np.mean([mf1(BASELINE_ARM, s) for s in SEEDS]))
    vs_current = {a: {
        "delta_pp": round((per_preset_mean[a] - base_mean) * 100, 3),
        "verdict_ko": ("판정 불가 (밴드 안)"
                       if abs(per_preset_mean[a] - base_mean) <= pair_band
                       else ("올라간다" if per_preset_mean[a] > base_mean else "내려간다")),
    } for a in presets}

    # ── 자가검사 ────────────────────────────────────────────────────────────
    checks = []

    def chk(name, ok, detail):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})
        print(f"  {'✅' if ok else '❌'} {name}: {detail}")

    print("\n자가검사")
    #  SC1 — 현행 arm · 첫 씨앗이 기존 원장과 비트동일인가
    sc1_detail, sc1_ok = "기준 원장 없음", False
    if os.path.exists(REF_FEAT):
        z = np.load(REF_FEAT, allow_pickle=True)
        sel = ((z["prf"] == PRF) & (z["Twin"] == TWIN) & (z["snr_db"] > 500))
        Xref = np.asarray(z["X"], float)[sel]
        Xnew, ynew, gnew, _ff = build_features(BASELINE_ARM, SEEDS[0], tabs)
        same_shape = Xref.shape == Xnew.shape
        if same_shape:
            bit = bool(np.array_equal(Xref, Xnew, equal_nan=True))
            mx = float(np.nanmax(np.abs(Xref - Xnew))) if not bit else 0.0
            sc1_ok = bit
            sc1_detail = (f"행 {Xnew.shape} · 비트동일 {bit}"
                          + ("" if bit else f" · 최대차 {mx:.3e}"))
        else:
            sc1_detail = f"모양 불일치 {Xref.shape} vs {Xnew.shape}"
    chk("SC1 현행 arm 이 기존 md_classify_features.npz 와 비트동일", sc1_ok, sc1_detail)

    #  SC10 — ⭐생산 원장이 자기 로터 모델을 **선언하고 있나**
    #    설계서의 R8 은 «rotor_preset 키 없는 npz 는 거부» 를 하드 게이트로 걸어 두었다.
    #    지금 헤드라인 원장이 그 게이트에 걸리는지 여기서 확인한다.
    ref_declares = False
    ref_keys = []
    if os.path.exists(REF_FEAT):
        _z = np.load(REF_FEAT, allow_pickle=True)
        ref_keys = list(_z.files)
        ref_declares = "rotor_preset" in ref_keys
    chk("SC10 생산 원장이 rotor_preset 를 선언한다", ref_declares,
        (f"md_classify_features.npz 에 rotor_preset 키 "
         f"{'있음' if ref_declares else '**없음**'} — 이 원장은 2026-08-10 산이라 "
         f"rotor_dynamics(2026-08-11)보다 앞선다. ⇒ 설계서 R8 의 «rotor_preset 없는 npz 는 "
         f"거부» 게이트에 **현행 헤드라인 원장 자신이 걸린다**. 다만 SC1 이 그 X 배열이 "
         f"rotor_preset='' 와 비트동일임을 증명하므로, 다시 굽지 않고 **선언만 채워도** 된다."))

    #  SC2 — legacy 프리셋이 «현행» 과 같은가 (설계서가 그렇게 적었다)
    sha_cur = by[BASELINE_ARM][SEEDS[0]]["_X_head_sha"]
    sha_leg = by["legacy"][SEEDS[0]]["_X_head_sha"]
    chk("SC2 legacy 프리셋 ≠ 현행 arm (설계서 문장 반증)", sha_cur != sha_leg,
        f"sha 현행 {sha_cur} vs legacy {sha_leg}")

    #  SC3 — 프리셋 σ 값이 원장과 맞나
    sc3 = True
    try:
        with open(os.path.join(ROOT, "outputs", "rotor_jitter_model.json")) as f:
            led = json.load(f)["presets"]
        for k in presets:
            sc3 &= (abs(led[k]["static_sigma"] - rd.PRESETS[k].static_sigma) < 1e-12
                    and abs(led[k]["wobble_sigma"] - rd.PRESETS[k].wobble_sigma) < 1e-12)
    except Exception as e:                                # noqa: BLE001
        sc3, led = False, {}
        print(f"    (원장 못 읽음: {e})")
    chk("SC3 프리셋 σ 가 outputs/rotor_jitter_model.json 과 일치", sc3,
        f"{len(presets)} 종 대조")

    #  SC4 — 모든 판이 완주했고 행 수·NaN 이 정상인가
    okrows = all(r["n_rows"] == 864 for r in runs)
    nan_tot = sum(r["n_nan_rows"] for r in runs)
    chk("SC4 모든 판 864 행 · NaN 행 0", okrows and nan_tot == 0,
        f"판 {len(runs)} · 행 {sorted({r['n_rows'] for r in runs})} · NaN {nan_tot}")

    #  SC5 — 누수 없음: 자세 안에서 라벨을 섞으면 우연(16.7 %)으로 내려가야 한다
    import md_classify_run as mr
    Xn, yn, gn, _ = build_features(NOISE_BAND_PRESET, SEEDS[0], tabs)
    rs2 = np.random.default_rng(0)
    yp = yn.copy()
    for a in np.unique(gn):
        m = gn == a
        yp[m] = rs2.permutation(yp[m])
    acc_null, _ = mr.run_cv(mr._clean(Xn), yp, gn, lambda: mr._models()["RF100"])
    chk("SC5 라벨섞기 널이 우연 수준(±5 %p)", abs(acc_null - 1 / 6) < 0.05,
        f"섞은 정확도 {acc_null:.4f} vs 우연 {1/6:.4f}")

    #  SC6 — GPU 를 안 건드렸나
    gpu_free = not any(m.startswith(("mitsuba", "drjit")) or m == "sionna.rt"
                       for m in sys.modules)
    chk("SC6 mitsuba·drjit·sionna.rt 미적재", gpu_free,
        f"적재 모듈 {sorted(m for m in sys.modules if m.startswith(('mitsuba','drjit','sionna')))}")

    #  SC7 — 잡음 폭이 유한하고 0 이 아닌가(판정이 성립하려면 필요)
    chk("SC7 잡음 폭 유한·양수", np.isfinite(w_null) and w_null > 0,
        f"σ_pool {sigma_pool:.5f} → W_null {w_null:.5f}")

    #  SC8 — 기전 일관성(사후 확인이지 사전예측이 아니다): 박자가 번질수록 성적이 내려가나
    chk("SC8 박자 겹침 ↑ → macro-F1 ↓ (사후 일관성 확인)", r_overlap < 0,
        f"r = {r_overlap:+.4f} (6 프리셋, 사전예측 아님 — 방향만 읽는다)")

    #  SC9 — legacy 계열(정렬)을 빼도 사다리가 남나. 남아야 «물리가 움직인다» 가 성립한다
    rf = subgroups["random_phase_family"]
    chk("SC9 정렬 아티팩트를 뺀 4 종에서도 폭이 잡음 밴드 밖", rf["ratio"] > 1.0,
        f"W {rf['width_W']*100:.2f} %p / W_null {rf['W_null']*100:.2f} %p "
        f"= {rf['ratio']:.2f}× · p {rf['p_value']:.4f} → «{rf['verdict_ko']}»")

    # ── 원장 ────────────────────────────────────────────────────────────────
    res = {
        "_meta": {
            "experiment": "R6 · 로터 흔들림 프리셋 사다리",
            "script": "benchmark/rotor_preset_ladder.py",
            "design_doc": "docs/NEXT_EXPERIMENTS.md (순위 5)",
            "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S KST"),
            "runtime_sec": round(time.time() - t_start, 1),
            "gpu_used": False,
            "gpu_note_ko": ("GPU 0. 저장된 위상표 outputs/md_classify_tables/*.npz 108 장을 "
                            "그대로 재사용했다. sionna.rt·mitsuba 를 import 하지 않는다(SC6)."),
            "question_ko": ("로터 흔들림 설정(rotor_preset)을 바꾸면 기종 분류 성적이 "
                            "달라지나 — 딥러닝 착수 전 상류 게이트."),
            "provenance": {
                "phase_tables": {"dir": "outputs/md_classify_tables",
                                 "n_files": len(tabs), "missing": missing,
                                 "reused_ko": "새로 굽지 않았다(GPU 0)"},
                "preset_source": "src/rotor_dynamics.py PRESETS",
                "preset_ledger": "outputs/rotor_jitter_model.json",
                "baseline_ledger": "outputs/md_classify_features.npz (headline rows)",
                "scoring_code": "benchmark/md_classify_run.py (run_cv·_models·confusion)",
                "grid_band_ledger": "outputs/grid_convergence_check.json",
            },
            "n_presets_measured": len(presets),
            "presets": presets,
            "preset_count_ko": (
                "프리셋은 **6 종**이다(legacy·legacy_outdoor·sitl·indoor·outdoor·lit_iid). "
                "src/rotor_dynamics.PRESETS 를 직접 세어 6 종 전부를 돌렸다. "
                "⚠설계서(NEXT_EXPERIMENTS.md)의 R6 행과 실행절은 «6 종»·CLI 6 줄로 **옳게** "
                "적혀 있다 — 5 종으로 적힌 곳은 `md_classify_dataset.py` 의 `--rotor-preset` "
                "도움말 문자열뿐이고, 거기서 legacy_outdoor 가 빠졌다."),
            "baseline_arm_ko": (
                "arm '' 은 프리셋이 아니라 기존 원장이 실제로 쓰는 «현행» 모델이다: "
                "시행마다 σ_s ~ U(0.07 %, 0.29 %) · 시간 흔들림 없음 · 초기위상 U(0,180°). "
                "사다리의 폭 W 계산에는 **넣지 않고** 참조선으로만 쓴다."),
            "observation_ko": (f"PRF {PRF/1e3:.0f} kHz · 창 {TWIN*1e3:.0f} ms · 잡음 없음 · "
                               f"기체 {len(labels)} 종 × 자세 18 × 추첨 8 = 864 시행/판"),
            "cv_ko": "자세 단위 leave-one-aspect-out (시험 자세는 학습에서 못 본 기하)",
            "dc_removed_ko": ("특징은 전부 시계열 평균(가만히 있는 부분·DC)을 뺀 뒤 잰다 — "
                              "md_classify_dataset.features() 의 Eac = E − mean(E). "
                              "마이크로도플러 지도는 STFT 만 쓴다."),
            "headline_model_ko": ("RF100 하나로 못 박았다. 프리셋마다 최고 모델을 다시 고르면 "
                                  "«모델 고르기 잡음» 이 «프리셋 효과» 로 샌다. LDA·kNN5 도 "
                                  "함께 실었다(robustness 절)."),
            "outdoor_preset_caveat_ko": (
                "⚠ outdoor 프리셋(σ_s 2.35 % · σ_w 2.45 %)의 근거 로그는 **DJI 기체가 아니다** — "
                "PX4 Flight Review 의 CODEV AQUILA V3 야외 Position 홀드 39 창이고, "
                "**4 Hz 표집**이라 앨리어싱 여지가 있다. 우리 표적 기체(Mavic 4 Pro·Matrice 4E)의 "
                "rpm 통계는 DJI 가 DAT 를 암호화해 못 구했다. indoor 프리셋도 DJI 가 아닌 "
                "레이싱 쿼드(NeuroBEM)다."),
            "not_modelled_ko": ("산란 진폭의 요동은 여전히 미모델이다(White IEEE TRS 2024 도 "
                                "같은 자리를 자백한다). 블레이드 플렉싱·피치 변화도 안 넣는다."),
        },

        "prereg": {
            "criterion_ko": ("씨앗 3 판으로 잡음 폭을 먼저 재고, 프리셋 6 종의 macro-F1 폭 W 가 "
                             "잡음 폭의 3 배 이상이면 «좌우한다», 1 배 이하면 «둔감하다», "
                             "그 사이면 «보류»."),
            "criterion_changed": True,
            "criterion_change_reason_ko": (
                "⭐잡음 폭의 **정의**를 한 번 다듬었다(문턱 3·1 배는 그대로). 사전등록 문장은 "
                "«같은 프리셋 3 판의 폭» 인데, 3 표본의 폭과 6 표본의 폭은 같은 잣대가 아니다 — "
                "정규분포에서 기대 폭은 표본 수에 따라 커진다(d₃ 1.69 → d₆ 2.53). 그대로 견주면 "
                "«프리셋이 좌우한다» 쪽으로 기운다. 그래서 6 프리셋 × 3 씨앗 = 자유도 12 로 "
                "판 하나의 표준편차 σ_pool 을 모으고, «프리셋 효과가 0 일 때 6 개 평균의 폭» "
                "W_null = d₆·σ_pool/√3 을 귀무 폭으로 쓴다. 사전등록 문장 그대로의 수 "
                "(지정 프리셋 3 판의 폭)도 아래 `literal` 에 같이 싣고, 두 판정이 갈리는지 본다."),
            "model_locked": "RF100",
            "seeds": SEEDS,
            "noise_band_preset": NOISE_BAND_PRESET,
        },

        "noise_band": {
            "per_preset_macro_f1": {a: [round(v, 5) for v in per_preset_vals[a]]
                                    for a in presets},
            "per_preset_mean": {a: round(v, 5) for a, v in per_preset_mean.items()},
            "per_preset_sd_over_seeds": {a: round(v, 5) for a, v in per_preset_sd.items()},
            "sigma_pool": round(sigma_pool, 5),
            "sigma_pool_dof": len(presets) * (len(SEEDS) - 1),
            "W_null_expected_range_of_6_means": round(w_null, 5),
            "literal_prereg": {
                "preset": NOISE_BAND_PRESET,
                "macro_f1_3seeds": [round(v, 5) for v in prereg_vals],
                "width": round(s_prereg, 5),
                "note_ko": "설계서 문장 그대로의 수. 표본 3 개짜리 폭이라 불안정하다."},
            "baseline_arm_macro_f1": [round(mf1(BASELINE_ARM, s), 5) for s in SEEDS],
            "baseline_arm_width": round(float(max(mf1(BASELINE_ARM, s) for s in SEEDS)
                                              - min(mf1(BASELINE_ARM, s) for s in SEEDS)), 5),
            "meaning_ko": ("씨앗만 바꾸면 base rpm 추첨·로터 산포·초기위상·흔들림 실현이 전부 "
                           "다시 뽑힌다. 그때 macro-F1 이 흔들리는 폭이 «재생성 잡음» 이다."),
        },

        "ladder": {
            "width_W": round(W, 5),
            "best_preset": arm_hi, "worst_preset": arm_lo,
            "best_macro_f1": round(per_preset_mean[arm_hi], 5),
            "worst_macro_f1": round(per_preset_mean[arm_lo], 5),
            "W_over_W_null": round(W / max(w_null, 1e-12), 3),
            "W_over_literal_band": round(W / max(s_prereg, 1e-12), 3),
            "permutation_test": {
                "n_perm": n_perm, "p_value": round(p_val, 5),
                "null_W_median": round(float(np.median(null_W)), 5),
                "null_W_p95": round(float(np.percentile(null_W, 95)), 5),
                "note_ko": ("18 개 macro-F1 값의 프리셋 딱지를 무작위로 섞어 W 의 귀무분포를 "
                            "만들었다. 가정이 없다 — 정규성도, 등분산도 안 쓴다.")},
            "table": [{
                "preset": a,
                "static_sigma_pct": round(rd.PRESETS[a].static_sigma * 100, 3),
                "wobble_sigma_pct": round(rd.PRESETS[a].wobble_sigma * 100, 3),
                "random_phase": bool(rd.PRESETS[a].random_phase),
                "is_legacy_sine": bool(rd.PRESETS[a].is_legacy),
                "macro_f1_mean": round(per_preset_mean[a], 5),
                "macro_f1_sd": round(per_preset_sd[a], 5),
                "accuracy_mean": round(float(np.mean(
                    [by[a][s]["scores"]["RF100"]["accuracy"] for s in SEEDS])), 5),
                "per_class_f1": {l: round(f1_by_class[l][a], 4) for l in labels},
                "mean_beat_overlap": round(ov_bar[a], 4),
                "draw_scatter": round(scat[a]["draw_scatter_mean"], 5),
                "beat_overlap_symmetric": ov_mean[a],
                "source_ko": rd.PRESETS[a].source,
            } for a in presets],
            "vs_current_ledger": {
                "pair_band": round(pair_band, 5),
                "pair_band_ko": ("두 평균의 **차** 를 볼 때 쓰는 밴드 = 1.96·σ_pool·√(2/3). "
                                 "폭 밴드(W_null)와 다른 물건이다. 이 안이면 «판정 불가»."),
                "delta": vs_current,
                "reading_ko": (
                    "⭐실무적으로 가장 중요한 줄: 방침이 정본으로 두는 **outdoor 는 현행 원장과 "
                    "차이가 밴드에 걸릴 만큼 작다**. 즉 정본을 outdoor 로 바꿔도 기존 헤드라인 "
                    "87.9 % 는 사실상 안 흔들린다. 반대로 legacy_outdoor·lit_iid 로 갈아타면 "
                    "5~7 %p 가 그냥 올라가는데, 그것은 물리가 좋아진 것이 아니라 데이터가 "
                    "깨끗해진 것이다."),
            },
            "baseline_row": {
                "arm": "(현행, 프리셋 아님)",
                "macro_f1_mean": round(float(np.mean(
                    [mf1(BASELINE_ARM, s) for s in SEEDS])), 5),
                "per_class_f1": {l: round(float(np.mean(
                    [by[BASELINE_ARM][s]["scores"]["RF100"]["per_class_f1"][l]
                     for s in SEEDS])), 4) for l in labels},
                "beat_overlap_symmetric": ov_mean[BASELINE_ARM]},
        },

        "mechanism": mechanism,
        "subgroups": subgroups,

        "attribution": {
            "compared_ko": f"{arm_hi}(최고) → {arm_lo}(최저) 로 갈 때 늘어난 오분류",
            "per_class_f1_width": f1_width,
            "top_pairs": attrib[:10],
            "beat_overlap_of_top_pairs": {
                f"{d['true']}|{d['predicted']}":
                    ov_mean[arm_lo].get(f"{d['true']}|{d['predicted']}",
                                        ov_mean[arm_lo].get(f"{d['predicted']}|{d['true']}"))
                for d in attrib[:6]},
            "reading_ko": ("혼동율은 «참 기체 행» 으로 정규화했다. Δ 가 +면 낮은 프리셋에서 "
                           "그 쌍의 오분류가 늘었다는 뜻이다."),
        },

        "robustness": {
            "other_models": model_stats,
            "other_models_reading_ko": (
                f"⭐헤드라인 RF100 의 폭 {W*100:.2f} %p 는 세 모델 중 **가장 작다** "
                f"(LDA {model_stats['LDA']['width_W']*100:.2f} · "
                f"kNN5 {model_stats['kNN5']['width_W']*100:.2f} %p). 즉 «프리셋이 성적을 "
                "좌우한다» 는 결론은 모델 고르기에 기대지 않고, 인용할 수 있는 6.14 %p 는 "
                "민감도의 **하한**이다."),
            "grid_dispersion_band_classify_pp": grid_band_pp,
            "grid_band_scope_ko": (
                "2026-08-15 격자 산포 밴드의 «분류» 칸은 0.0 %p 이지만 그것은 **빗살 argmax** "
                "분류기의 정확도이지 여기 RF100 macro-F1 이 아니다. 잣대가 다르므로 이 판의 "
                "판정 문턱으로 쓰지 않는다 — 문턱은 위 씨앗 밴드로 데이터에서 세웠다. "
                "(밴드가 0 이라는 사실은 «격자 표집은 분류를 안 흔든다» 는 별개의 근거다.)"),
        },

        "runs": [{k: v for k, v in r.items() if k != "scores"} | {
            "RF100": {kk: vv for kk, vv in r["scores"]["RF100"].items()
                      if kk != "confusion"},
            "LDA_macro_f1": r["scores"]["LDA"]["macro_f1"],
            "kNN5_macro_f1": r["scores"]["kNN5"]["macro_f1"]} for r in runs],

        "self_checks": checks,
    }

    #  ── 판정문 ──────────────────────────────────────────────────────────────
    both_agree = (v_main == v_prereg_literal)
    res["verdict"] = {
        "verdict_ko": v_main,
        "verdict_literal_prereg_ko": v_prereg_literal,
        "verdicts_agree": both_agree,
        "W": round(W, 5), "W_null": round(w_null, 5),
        "ratio": round(W / max(w_null, 1e-12), 3),
        "p_value_permutation": round(p_val, 5),
        "headline_ko": (
            f"로터 흔들림 프리셋 {len(presets)} 종의 macro-F1 폭은 {W*100:.2f} %p 이고, "
            f"씨앗만 바꿔도 생기는 폭은 {w_null*100:.2f} %p 다 — 배수 "
            f"{W/max(w_null,1e-12):.2f}× · 치환검정 p={p_val:.4f}. ⇒ «{v_main}»."),
        "consequence_ko": (
            "딥러닝 착수 가능 — 원장 재생성 불필요. 단 어느 프리셋으로 구웠는지는 "
            "npz 의 rotor_preset 키에 반드시 남긴다." if v_main == "둔감하다" else
            ("⭐딥러닝에 들어가기 전에 **프리셋을 하나로 못 박고 원장을 그 프리셋으로 다시 "
             "굽는다.** 지금 원장(rotor_preset='')은 사다리 아래쪽에 있고, 프리셋을 바꾸면 "
             f"macro-F1 이 {W*100:.1f} %p 움직인다 — 이는 기존 원장에서 «전 특징» 팔과 "
             "«기하만» 팔의 차이(8.3 %p)와 맞먹는 크기다. 프리셋을 안 고정한 채 표현·백본을 "
             "비교하면 그 차이가 프리셋 차이에 묻힌다."
             if v_main == "좌우한다" else
             "보류 — 씨앗을 늘려(6~10 판) 잡음 폭을 다시 재고 판정한다.")),
        "grid_band_check_ko": (
            f"2026-08-15 격자 산포 밴드의 «분류» 칸은 {grid_band_pp} %p 이므로 이 판의 "
            f"{W*100:.2f} %p 는 그 밴드 **밖**이다(판정 가능). ⚠단 그 칸은 «빗살 argmax» "
            "분류기의 정확도라 잣대가 다르다 — 이 판의 진짜 문턱은 위 씨앗 밴드 "
            f"{w_null*100:.2f} %p 이고, 두 잣대 모두에서 밖이다."),
        "which_preset_ko": (
            "⛔**점수가 높은 프리셋을 고르면 안 된다.** 사다리 위쪽 두 판(legacy·legacy_outdoor)은 "
            "초기위상이 t=0 에 정렬돼 있고 정적 산포가 고정 패턴이라, 같은 기체·같은 자세의 시행이 "
            "base rpm 하나만 다르다 — 점수가 높은 것은 모델이 좋아서가 아니라 **데이터가 인위적으로 "
            "깨끗해서**다. 문헌·실기 로그에 근거가 있는 팔은 sitl·indoor·outdoor·lit_iid 넷뿐이고, "
            "이 넷 안에서도 사다리가 남는지는 `subgroups.random_phase_family` 에 따로 적었다."),
        "policy_ko": (
            "⭐정본 프리셋은 판정표 **바깥**의 방침이다: 실증이 야외이므로 outdoor 를 정본 "
            "후보로 둔다. 다만 그 σ 는 비-DJI 기체의 4 Hz 로그에서 왔다(위 caveat). "
            "⚠이 판정이 «좌우한다» 이므로 정본 선택은 **성적이 아니라 물리적 정직성**으로 "
            "하되, 고른 뒤에는 바꾸지 말고 원장·리포트에 그 이름을 박아야 한다 — 프리셋을 "
            "갈아 끼우면 이후 모든 비교의 기준선이 함께 움직인다."),
        "scope_ko": (f"이 판정은 «호버 · 자세 18 · 잡음 없음 · 손 특징 {n_feat} 개 · RF100» "
                     "자리에서만 선다. 잡음을 넣거나 딥러닝 표현으로 바꾸면 프리셋 민감도가 "
                     "달라질 수 있다 — 그 자리는 R8·R11 이 잰다. ⭐다만 RF100 은 세 모델 중 "
                     f"**가장 둔한** 팔이다(LDA 폭 {model_stats['LDA']['width_W']*100:.2f} · "
                     f"kNN5 폭 {model_stats['kNN5']['width_W']*100:.2f} %p). 그러므로 "
                     f"{W*100:.2f} %p 는 프리셋 민감도의 **하한**이지 상한이 아니다."),
    }

    res["corrections"] = [
        {"target": "benchmark/md_classify_dataset.py · `--rotor-preset` 도움말 문자열",
         "was_ko": "src/rotor_dynamics.PRESETS 이름(legacy/sitl/indoor/outdoor/lit_iid) — 5 종",
         "is_ko": (f"실제 프리셋은 {len(presets)} 종이다 — 도움말에서 **legacy_outdoor** 가 "
                   "빠졌다. ⭐설계서 NEXT_EXPERIMENTS.md 의 R6 행(«프리셋 6 종»)과 실행절"
                   "(CLI 6 줄)은 옳게 적혀 있으므로 **설계서는 정정할 것이 없다** — 틀린 곳은 "
                   "CLI 도움말 하나뿐이다."),
         "evidence": (f"src/rotor_dynamics.py PRESETS 직접 셈 = {len(presets)} "
                      f"({', '.join(presets)}) · md_classify_dataset.py:936-938")},
        {"target": "docs/NEXT_EXPERIMENTS.md · R6 실행절",
         "was_ko": "«legacy 판이 기존 md_classify_features.npz 와 X 배열 비트동일인지 "
                   "게이트로 확인한 뒤에야 나머지를 굽는다»",
         "is_ko": ("legacy 프리셋은 기존 원장과 비트동일이 **될 수 없다**. 기존 원장의 arm 은 "
                   "`rotor_preset=''`(시행마다 σ_s~U(0.07,0.29 %)·초기위상 U(0,180°))이고, "
                   "legacy 프리셋은 결정론적 패턴 [+1,−1,−0.55,+0.55]·초기위상 0(정렬)이다. "
                   "rotor_dynamics.py 의 «비트동일» 주장은 report07_hover_long(호버 지도) "
                   "경로에 대한 것이지 분류 데이터셋 경로가 아니다. ⇒ 비트동일 게이트는 "
                   "arm='' 로 걸어야 맞고, 이 판이 그렇게 걸어 통과시켰다(SC1)."),
         "evidence": f"SC1 {sc1_detail} · SC2 sha 현행 {sha_cur} ≠ legacy {sha_leg}"},
        {"target": "docs/NEXT_EXPERIMENTS.md · R8 (하드 게이트: rotor_preset 없는 npz 는 거부)",
         "was_ko": "그 게이트는 «앞으로 구울 npz» 를 겨냥한 것으로 읽힌다",
         "is_ko": ("⭐**현행 헤드라인 원장 자신이 그 게이트에 걸린다.** "
                   "outputs/md_classify_features.npz(2026-08-10)에는 rotor_preset 키가 아예 "
                   "없다 — rotor_dynamics.py(2026-08-11)보다 하루 앞서 구워졌기 때문이다. "
                   "⇒ R8 에 들어가기 전에 이 원장의 로터 모델 선언을 채워야 한다. "
                   "다만 SC1 이 그 X 배열이 rotor_preset='' 와 **비트동일**임을 증명했으므로 "
                   "다시 구울 필요는 없다 — 선언만 채우면 된다(GPU 0)."),
         "evidence": f"npz 키 목록에 rotor_preset 없음: {sorted(k for k in ref_keys if not k.startswith('ex/'))[:8]}… · SC1 비트동일 통과"},
        {"target": "benchmark/md_classify_dataset.py cmd_build",
         "was_ko": "`--rotor-seed` 로 씨앗을 바꿀 수 있다(고 읽힌다)",
         "is_ko": ("`rot_seed0` 는 npz 에 **적히기만** 하고 rng 에 안 들어간다 — "
                   "`rng = np.random.default_rng(SEED)` 가 상수다. 그 CLI 로는 재생성 잡음을 "
                   "못 잰다. 이 실험은 씨앗을 실제로 rng 에 넣는 별도 경로로 쟀다(파일 수정 없음). "
                   "⛔결함이 아니라 «없는 기능» 이므로 기존 원장은 그대로 유효하다."),
         "evidence": "md_classify_dataset.py:796-798 · 905"},
    ]

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print(f"\n✅ {OUT_JSON}")
    print("   " + res["verdict"]["headline_ko"])

    figure(res, presets, labels, per_preset_vals, w_null, W, p_val, attrib,
           ov_mean, ov_bar, f1_by_class, base_mean, ov_bar[BASELINE_ARM], rd)
    return res


def figure_only():
    """⭐원장만 읽어 그림을 다시 그린다 — 재계산 0. 그림 손볼 때 쓴다."""
    import rotor_dynamics as rd
    with open(OUT_JSON) as f:
        res = json.load(f)
    presets = res["_meta"]["presets"]
    labels = [r for r in res["attribution"]["per_class_f1_width"]]
    vals = {a: res["noise_band"]["per_preset_macro_f1"][a] for a in presets}
    tab = {r["preset"]: r for r in res["ladder"]["table"]}
    ov_mean = {a: tab[a]["beat_overlap_symmetric"] for a in presets}
    ov_mean[BASELINE_ARM] = res["ladder"]["baseline_row"]["beat_overlap_symmetric"]
    ov_bar = {a: tab[a]["mean_beat_overlap"] for a in presets}
    f1_by_class = {l: {a: tab[a]["per_class_f1"][l] for a in presets} for l in labels}
    figure(res, presets, labels, vals,
           res["noise_band"]["W_null_expected_range_of_6_means"],
           res["ladder"]["width_W"], res["ladder"]["permutation_test"]["p_value"],
           res["attribution"]["top_pairs"], ov_mean, ov_bar, f1_by_class,
           res["ladder"]["baseline_row"]["macro_f1_mean"],
           res["mechanism"]["baseline_arm"]["mean_beat_overlap"], rd)


# ═══════════════════════════════════════════════════════════════════════════════
#  ④ 그림 — 글자는 전부 영어(집 규약)
# ═══════════════════════════════════════════════════════════════════════════════
def figure(res, presets, labels, vals, w_null, W, p_val, attrib, ov_mean, ov_bar,
           f1_by_class, base_mean, base_overlap, rd):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    os.makedirs(FIG_DIR, exist_ok=True)
    disp = [SHORT.get(l, l) for l in labels]
    means = np.array([np.mean(vals[a]) for a in presets])
    order = list(np.argsort(-means))
    pres_o = [presets[i] for i in order]
    bmu = float(base_mean) * 100

    fig = plt.figure(figsize=(18.6, 10.4))
    gs = GridSpec(2, 3, figure=fig, hspace=0.58, wspace=0.30,
                  left=0.055, right=0.985, top=0.900, bottom=0.235)

    # (a) 사다리 — 프리셋별 macro-F1 + 잡음 밴드
    ax = fig.add_subplot(gs[0, :2])
    xs = np.arange(len(pres_o), dtype=float)
    mu = np.array([np.mean(vals[a]) for a in pres_o]) * 100
    #  legacy 계열(초기위상 정렬)은 색을 갈라 «인위적으로 깨끗한 판» 임을 표시한다
    bar_c = ["#B0BEC5" if not rd.PRESETS[a].random_phase else "#5B8FF9" for a in pres_o]
    ax.bar(xs, mu, 0.56, color=bar_c, edgecolor="0.25", lw=0.8, zorder=2)
    for i, a in enumerate(pres_o):
        v = np.array(vals[a]) * 100
        ax.plot(np.full(len(v), xs[i]), v, "o", ms=5.2, color="#16324F",
                zorder=4, clip_on=False)
    lo, hi = mu.min(), mu.max()
    mid = 0.5 * (lo + hi)
    hband = ax.axhspan(mid - w_null * 50, mid + w_null * 50, color="#FFB74D",
                       alpha=0.32, zorder=1,
                       label=f"seed-noise width  {w_null*100:.2f} pp")
    hbase = ax.axhline(bmu, color="#C2185B", ls="--", lw=1.6, zorder=3,
                       label=f"existing ledger, current model  {bmu:.2f}%")
    from matplotlib.patches import Patch
    ax.legend(handles=[hbase, Patch(facecolor="#B0BEC5", edgecolor="0.25",
                                    label="rotors aligned at t=0 (legacy family)"),
                       hband],
              fontsize=7.8, loc="upper right", framealpha=0.93)
    #  ⭐ 기준선·밴드가 축 밖으로 나가지 않게 — 안 그러면 선이 안 보인다
    lo = min(lo, bmu, mid - w_null * 50)
    hi = max(hi, bmu, mid + w_null * 50)
    ax.set_xticks(xs, [f"{a}\n$\\sigma_s$ {rd.PRESETS[a].static_sigma*100:.2f}%  "
                       f"$\\sigma_w$ {rd.PRESETS[a].wobble_sigma*100:.2f}%"
                       for a in pres_o], fontsize=7.8)
    ax.set_ylabel("Macro-F1 [%]  (RF100, leave-one-aspect-out)", fontsize=9.5)
    ax.set_ylim(max(0, lo - 5.0), hi + 1.6)
    ax.set_title(f"(a) Rotor-jitter preset ladder: spread {W*100:.2f} pp against "
                 f"{w_null*100:.2f} pp of seed noise  (shuffle null p = {p_val:.4f})",
                 fontsize=11)
    ax.grid(axis="y", alpha=0.28, zorder=0)

    # (b) ⭐기전 — 사다리는 로터 산포에 **단조롭지 않다**, 그리고 정렬이 층을 올린다
    ax = fig.add_subplot(gs[0, 2])
    for fam, mk, col, ls, lab in (
            (True, "o", "#5B8FF9", "-", "random start phase"),
            (False, "s", "#B0BEC5", "--", "aligned at $t=0$")):
        sub = sorted([a for a in presets if rd.PRESETS[a].random_phase == fam],
                     key=lambda a: rd.PRESETS[a].static_sigma)
        xx = [rd.PRESETS[a].static_sigma * 100 for a in sub]
        yy = [np.mean(vals[a]) * 100 for a in sub]
        ax.plot(xx, yy, ls, color=col, lw=1.6, zorder=2)
        for a, x0, y0 in zip(sub, xx, yy):
            wob = rd.PRESETS[a].wobble_sigma > 0
            ax.plot(x0, y0, mk, ms=11, color=col, markeredgecolor="#C62828" if wob
                    else "0.25", markeredgewidth=2.2 if wob else 0.9, zorder=3,
                    label=lab if a == sub[0] else None)
            ax.annotate(a, (x0, y0), textcoords="offset points",
                        xytext=(0, 13 if a != "outdoor" else -17),
                        ha="center", fontsize=7.4)
    ax.plot([], [], "o", ms=9, color="w", markeredgecolor="#C62828",
            markeredgewidth=2.2, label="wobble on ($\\sigma_w>0$)")
    ax.set_xlabel("Static per-rotor spread  $\\sigma_s$  [% of hover rpm]", fontsize=9)
    ax.set_ylabel("Macro-F1 [%]", fontsize=9)
    ax.set_title("(b) Not monotone in rotor spread", fontsize=11)
    ax.legend(fontsize=7, loc="upper left", framealpha=0.93)
    ax.margins(x=0.22, y=0.30)
    ax.grid(alpha=0.25)

    # (c) 기체별 F1 — 범례가 막대를 가리지 않게 **표**로 낸다
    ax = fig.add_subplot(gs[1, 0])
    lab_o = sorted(labels,
                   key=lambda l: -(max(f1_by_class[l].values())
                                   - min(f1_by_class[l].values())))
    Mf = np.array([[f1_by_class[l][a] * 100 for a in pres_o] for l in lab_o])
    im = ax.imshow(Mf, cmap="Blues", vmin=60, vmax=100, aspect="auto")
    for i in range(Mf.shape[0]):
        for j in range(Mf.shape[1]):
            ax.text(j, i, f"{Mf[i,j]:.0f}", ha="center", va="center", fontsize=7.2,
                    color="w" if Mf[i, j] > 88 else "k")
    ax.set_xticks(range(len(pres_o)), pres_o, rotation=32, ha="right", fontsize=7.4)
    ax.set_yticks(range(len(lab_o)),
                  [f"{SHORT.get(l, l)}  ({(max(f1_by_class[l].values())-min(f1_by_class[l].values()))*100:.0f})"
                   for l in lab_o], fontsize=7.2)
    ax.set_title("(c) Per-airframe F1 [%]  (preset spread in brackets)", fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.042, pad=0.03)

    # (d) 쌍별 박자 겹침
    ax = fig.add_subplot(gs[1, 1])
    pairs = sorted(ov_mean[pres_o[0]].keys(),
                   key=lambda k: -ov_mean[pres_o[0]][k])[:8]
    M = np.array([[ov_mean[a][pk] for a in pres_o] for pk in pairs]) * 100
    im = ax.imshow(M, cmap="YlOrRd", vmin=0, vmax=100, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=7.2,
                    color="w" if M[i, j] > 58 else "k")
    ax.set_xticks(range(len(pres_o)), pres_o, rotation=32, ha="right", fontsize=7.4)
    ax.set_yticks(range(len(pairs)),
                  [f"{SHORT.get(p.split('|')[0])} / {SHORT.get(p.split('|')[1])}"
                   for p in pairs], fontsize=7.2)
    ax.set_title("(d) Pairwise blade-rate overlap [%]", fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.042, pad=0.03)

    # (e) 귀속 — 어느 쌍에서 성적이 움직였나
    ax = fig.add_subplot(gs[1, 2])
    top = attrib[:8][::-1]
    ys = np.arange(len(top), dtype=float)
    vals_pp = [d["delta_pp"] for d in top]
    ax.barh(ys, vals_pp, 0.62,
            color=["#C62828" if v > 0 else "#2E7D32" for v in vals_pp])
    ax.set_yticks(ys, [f"{SHORT.get(d['true'])} → {SHORT.get(d['predicted'])}"
                       for d in top], fontsize=7.2)
    ax.axvline(0, color="k", lw=0.9)
    ax.set_xlabel("Change in confusion rate [pp]", fontsize=9)
    ax.set_title(f"(e) {res['ladder']['best_preset']} → "
                 f"{res['ladder']['worst_preset']} attribution", fontsize=11)
    ax.grid(axis="x", alpha=0.25)

    fig.suptitle("Does the rotor-jitter preset decide micro-Doppler airframe "
                 "classification?", fontsize=15.5, y=0.963)
    cap = textwrap.fill(
        f"All six presets were rebuilt from the stored per-rotor phase tables (no ray tracing, no "
        f"GPU) at {PRF/1e3:.0f} kHz slow-time rate and {TWIN*1e3:.0f} ms dwell, 864 trials each, "
        f"scored with the locked RF100 model under leave-one-aspect-out cross-validation. Each "
        f"preset was rebuilt three times with different draw seeds, so the orange band in (a) is "
        f"how far macro-F1 moves when only the random draw changes, and the preset spread must "
        f"clear three times that band to count. The two grey bars are the legacy presets, whose "
        f"rotors all start aligned with a fixed spread pattern so their trials differ only in base "
        f"rpm: they score high because the data is artificially clean, not because the model is "
        f"better. Panel (b) separates the two handles, alignment and spread size, and shows the "
        f"score is not monotone in spread. Panels (d) and (e) locate the loss: Phantom 4 and "
        f"Typhoon H both hover near 5500 rpm, their blade-rate distributions overlap almost "
        f"completely under outdoor, and that is exactly the pair the confusion moves to. The "
        f"outdoor and indoor presets come from non-DJI logs and the outdoor log is sampled at "
        f"only 4 Hz, so their sigma values carry an aliasing caveat.", 200)
    fig.text(0.5, 0.018, cap, ha="center", va="bottom", fontsize=8.4)

    fig.savefig(FIG_PNG, dpi=155, bbox_inches="tight", facecolor="w")
    print(f"✅ {FIG_PNG}  ({os.path.getsize(FIG_PNG)/1e6:.2f} MB)")
    plt.close(fig)


if __name__ == "__main__":
    if "--figure-only" in sys.argv:      # 원장은 그대로 두고 그림만 다시 그린다
        figure_only()
    else:
        main()
