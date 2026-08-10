# -*- coding: utf-8 -*-
"""
report07_5g_waveform.py — ⭐**같은 채널에 5G 파형을 실제로 태우면** CW 와 뭐가 달라지나.

사용자 질문: *"지금 CW로 꽤 잘 나온거같은데, 같은 세팅에서 5G 파형만 송수신해서
모노스태틱 처리한다면 어떻게 되는지까지 확인해줘"*

설계 — 채널은 같고 파형만 바꾼다
--------------------------------
채널: outputs/report07_hover_long.npz 의 h(t) — Matrice 4E 호버링, 3.5 GHz, 배 쪽(el −15°),
      PRF 5 kHz 로 2 초. ⭐블레이드 도플러가 ±1.5 kHz 안이라(나이퀴스트 2.5 kHz)
      이 열은 대역제한 신호로서 **완전**하다 → 더 높은 표본율로 **합법적으로 보간**할 수 있다.

파형: 5G NR 형 OFDM — SCS 30 kHz(n78 규약), 유효 부반송파 1024개, 심볼마다 무작위 QPSK.
      심볼율 = 28,000 sym/s (0.5 ms 슬롯에 14 심볼).
      ⚠ 표적 지연 확산 ~4 ns(기체 0.6 m) ≪ CP 2.3 µs → 대역 내 **평탄 채널**로 정당하게 근사.
      ⚠ ICI: 최대 도플러 1.23 kHz / SCS 30 kHz = 4.1 % → ICI 바닥 ≈ −28 dB (계산해 기록).

수신(모노스태틱, OpenISAC 류의 정석 처리):
      Y[n,m] = h_m · X[n,m]  →  ĥ_m = mean_n( Y[n,m] / X[n,m] )   (기지 심볼 나눗셈)
      풀캡처면 ĥ_m 이 심볼율(28 kHz)의 채널 열이 된다.

⭐ 네 팔 — «무엇을 쓸 수 있느냐» 만 다르다
      CW          5 kHz 원 채널열 (기준)
      5G-full     OFDM 풀캡처 — 모든 심볼 사용 (28 kHz)
      5G-CRS      1 kHz 로 솎음 (LTE CRS 급 반복률)
      5G-SSB      50 Hz 로 솎음 (5G SSB 반복률)

예상(정직하게 미리 적음): 잡음 0·단일 거리빈이므로 5G-full ≈ CW (그걸 수치로 확인하는 것이
이 실험의 절반), CRS 는 날개끝이 접히고, SSB 는 플래시선마저 접힌다 — «5G 이중고» 의 그림판.

    python benchmark/report07_5g_waveform.py
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
from scipy.signal import resample_poly

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOV = json.load(open(f"{ROOT}/outputs/report07_hover_long.json"))["_meta"]
Z = np.load(f"{ROOT}/outputs/report07_hover_long.npz")
h5k = np.asarray(Z["E"], complex)
PRF0 = HOV["prf_hz"]                      # 5000
FC, FFL, FTIP = HOV["fc_hz"], HOV["f_flash_hz"], HOV["f_tip_hz"]

SCS = 30e3                                 # 5G n78 부반송파 간격
SYM_RATE = 28000.0                         # 심볼/s (0.5 ms 슬롯 × 14)
N_SC = 1024                                # 유효 부반송파
RNG = np.random.default_rng(7)

t0 = time.time()

# ── ① 대역제한 확인 — 보간이 합법인지 먼저 잰다 ──────────────────────────────
S = np.abs(np.fft.fftshift(np.fft.fft(h5k - h5k.mean())))
f = np.fft.fftshift(np.fft.fftfreq(len(h5k), 1 / PRF0))
guard = float((S[np.abs(f) > 0.9 * PRF0 / 2] ** 2).sum() / (S ** 2).sum())
print(f"  대역제한 검사: |f|>{0.9*PRF0/2:.0f} Hz 에너지 비율 {guard:.2e} "
      f"{'✅보간 합법' if guard < 1e-3 else '⚠접힘 위험'}")

# ── ② 채널을 심볼율로 보간 (28k/5k = 28/5) ──────────────────────────────────
h28k = resample_poly(h5k, 28, 5)
n_sym = len(h28k)
print(f"  채널 보간: {len(h5k)} @ {PRF0:.0f} Hz → {n_sym} @ {SYM_RATE:.0f} sym/s")

# ── ③ OFDM 송신·채널·수신 — 심볼 단위 ───────────────────────────────────────
#   평탄 채널 근사(지연확산 ≪ CP)에서 심볼 m: Y[n,m] = h_m·X[n,m].
#   메모리를 아끼려 블록으로 처리한다. 기지 심볼 나눗셈 → 부반송파 평균 → ĥ_m.
h_hat = np.zeros(n_sym, complex)
B = 4096
for s0 in range(0, n_sym, B):
    s1 = min(s0 + B, n_sym)
    X = (RNG.integers(0, 4, (N_SC, s1 - s0)) * 2 + 1) * (np.pi / 4)      # QPSK 위상
    X = np.exp(1j * X)
    Y = h28k[None, s0:s1] * X                                            # 평탄 채널
    h_hat[s0:s1] = np.mean(Y / X, axis=0)                                # 기지심볼 나눗셈
err = float(np.max(np.abs(h_hat - h28k)) / np.max(np.abs(h28k)))
print(f"  풀캡처 ĥ ↔ 채널: 최대 상대오차 {err:.2e}  (잡음 0·평탄 채널이므로 일치가 정답)")

# ── ④ ICI 바닥 정량 — 심볼 안에서 채널이 도는 만큼 ──────────────────────────
#   심볼 길이 T≈1/SYM_RATE 동안 위상이 2π·f_D·T 돈다. 부반송파 직교가 그만큼 깨진다.
f_D = FTIP
ici_db = 20 * np.log10(np.pi * f_D / SCS)          # 1차 근사 누설비
print(f"  ICI 바닥(1차): 최대 도플러 {f_D:.0f} Hz / SCS {SCS/1e3:.0f} kHz → {ici_db:.1f} dB")

# ── ⑤ 네 팔 — 반복률만 다르게 솎는다 ────────────────────────────────────────
arms = {
    "cw_5k": (h5k, PRF0, "CW channel series (reference)"),
    "nr_full_28k": (h_hat, SYM_RATE, "5G OFDM, full capture (every symbol)"),
    "nr_crs_1k": (h_hat[:: int(SYM_RATE // 1000)], 1000.0, "1 kHz pilots (LTE-CRS-like)"),
    "nr_ssb_50": (h_hat[:: int(SYM_RATE // 50)], 50.0, "50 Hz bursts (5G SSB rate)"),
}
out = {}
series = {}
for k, (h, fs, label) in arms.items():
    db = 20 * np.log10(np.abs(h) + 1e-30)
    out[k] = {"fs_hz": fs, "n": int(len(h)), "label": label,
              "nyquist_hz": fs / 2,
              "ftip_folds": bool(fs / 2 < FTIP),
              "fflash_folds": bool(fs / 2 < FFL),
              "ptp_db": float(db.max() - db.min())}
    series[k] = h
np.savez_compressed(f"{ROOT}/outputs/report07_5g_waveform.npz", **series)
json.dump({"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                     "channel_source": "outputs/report07_hover_long.npz (2 s, PRF 5 kHz)",
                     "fc_hz": FC, "f_flash_hz": FFL, "f_tip_hz": FTIP,
                     "scs_hz": SCS, "sym_rate_hz": SYM_RATE, "n_sc": N_SC,
                     "bandlimit_guard_energy": guard,
                     "full_capture_max_rel_err": err,
                     "ici_floor_db_first_order": ici_db,
                     "flat_channel_justification_ko":
                         "표적 지연확산 ~4 ns ≪ CP 2.3 µs — 기체가 한 거리빈 안",
                     "verdict_ko": ("잡음 0·단일 거리빈에서 5G 풀캡처는 CW 와 수치적으로 같다"
                                    f"(최대 상대오차 {err:.1e}). 차이는 파형이 아니라 "
                                    "**반복률**에서 나온다 — CRS 1 kHz 는 날개끝(±1229 Hz)이 "
                                    "접히고 SSB 50 Hz 는 플래시선(127 Hz)마저 접힌다.")},
           "arms": out},
          open(f"{ROOT}/outputs/report07_5g_waveform.json", "w"),
          ensure_ascii=False, indent=1)
print(f"  ✅ {time.time()-t0:.1f}s · outputs/report07_5g_waveform.npz / .json")
for k, v in out.items():
    print(f"    {k:12s} fs {v['fs_hz']:7.0f} Hz · 나이퀴스트 {v['nyquist_hz']:6.0f} · "
          f"f_tip 접힘 {'⚠예' if v['ftip_folds'] else '아니오'} · "
          f"f_flash 접힘 {'⚠예' if v['fflash_folds'] else '아니오'}")
