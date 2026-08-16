# -*- coding: utf-8 -*-
"""① 실측 로그 시계열 vs 우리 모델 시계열 — **같은 잣대** 비교 (2026-08-16)

공정성 규칙 셋
1. 통계 함수는 `rstats.full` **하나만** 쓴다(실측·모델 동일).
2. 모델도 **같은 계측기를 통과시킨다** — 200 Hz 로 만들고 그 로그의 표집률로
   표본유지(sample-hold) 강등. 실측 ESC 텔레메트리가 그렇게 기록되기 때문이다.
3. 창 길이·로터 수·표집률을 세그먼트마다 맞춘다.

팔(arm)
  measured  : 실측
  outdoor   : PRESETS['outdoor']  (σ_s 2.35 % · σ_w 2.45 %)
  indoor    : PRESETS['indoor']   (0.54 / 0.65 %)
  matched   : 그 세그먼트의 실측 σ_s·σ_w 에 **레벨을 맞춘** OU — 남는 차이는 순수 «모양» 차이
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rotor_dynamics as rd        # noqa: E402
import rstats                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = f"{HERE}/rotor_corpus.npz"
N_SEED = 8
COARSE = 200.0


def sample_hold(x, fs_hi, fs_lo):
    """(4,N_hi) 고속 열 → 저속 로거가 봤을 열. 틱마다 직전 표본 유지."""
    n_hi = x.shape[1]
    t_hi = np.arange(n_hi) / fs_hi
    ticks = np.arange(0, t_hi[-1], 1.0 / fs_lo)
    idx = np.clip(np.searchsorted(t_hi, ticks, side="right") - 1, 0, n_hi - 1)
    return x[:, idx]


def model_seg(jit, n_out, fs_out, seed, n_rot=4, rpm0=3800.0):
    """모델 열을 200 Hz 로 만들고 fs_out 으로 표본유지 강등 → (4, n_out)."""
    rng = np.random.default_rng(seed)
    dur = n_out / fs_out
    n_hi = int(np.ceil(dur * COARSE)) + 4
    rpm_t, _ = rd.rpm_series(rpm0, n_rot, n_hi, COARSE, jit, rng, coarse_hz=None)
    x = sample_hold(rpm_t.T, COARSE, fs_out)
    return x[:, :n_out] if x.shape[1] >= n_out else np.pad(x, ((0, 0), (0, n_out - x.shape[1])),
                                                           mode="edge")


def matched_jitter(st, dur_s):
    """실측 세그먼트 통계 st 에 레벨을 맞춘 OU 파라미터.

    창 안에서 보이는 시간 변동 std 는 OU 전체 σ_w 보다 작다 — 창평균으로 흡수되는
    몫(window_mean_variance_fraction) 만큼. 그래서 되돌려서 σ_w 를 정한다."""
    fwm = rd.window_mean_variance_fraction(rd.TAU_CTL_S, dur_s)
    sw = st["wobble_std_rel"] / np.sqrt(max(1e-6, 1.0 - fwm))
    return rd.RotorJitter(name="matched", static_sigma=float(st["static_std_rel"]) * 2.0 / np.sqrt(3.0),
                          wobble_sigma=float(sw), random_phase=True,
                          source="세그먼트별 실측 레벨에 맞춘 OU(모양만 비교)")
    # static_sigma: 실현 std 는 σ_s·√((n−1)/n)=0.866σ_s (n=4) 이므로 되돌린다 → σ_s = std/0.866


def main():
    z = np.load(CORPUS)
    keys = sorted({k.split("__")[0] for k in z.files})
    meta = json.load(open(f"{HERE}/rotor_corpus_meta.json"))
    rows = []
    for k in keys:
        rpm = z[f"{k}__rpm"]
        fs = float(z[f"{k}__fs"][0])
        st = rstats.full(rpm, fs)
        st["_key"] = k
        st["_arm"] = "measured"
        st["_family"] = ("px4_s500" if k.startswith("px4_s500") else
                         "px4_race_manv" if "race_manv" in k else
                         "dregon_meas" if "_meas_" in k else "dregon_cmd")
        rows.append(st)

        dur = rpm.shape[1] / fs
        jm = matched_jitter(st, dur)
        for arm, jit in [("outdoor", rd.PRESETS["outdoor"]),
                         ("indoor", rd.PRESETS["indoor"]),
                         ("matched", jm)]:
            for s in range(N_SEED):
                x = model_seg(jit, rpm.shape[1], fs, seed=hash((k, arm, s)) % (2 ** 31))
                m = rstats.full(x, fs)
                m["_key"] = k
                m["_arm"] = arm
                m["_family"] = rows[-1 - 0]["_family"] if False else st["_family"]
                m["_seed"] = s
                rows.append(m)
        print("done", k, flush=True)

    with open(f"{HERE}/compare_rows.json", "w") as fh:
        json.dump(dict(rows=rows, corpus_meta=meta, n_seed=N_SEED, coarse_hz=COARSE), fh)
    print("rows", len(rows))


if __name__ == "__main__":
    main()
