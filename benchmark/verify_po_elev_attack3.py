# -*- coding: utf-8 -*-
"""verify_po_elev_attack3.py — 반증 라운드의 결정적 두 건을 원장에 못 박는다.

 (1) 옛 「−20 dB 폭」의 규약 복원 — 지시문 목록 0.80/2.88/2.31/0.99/1.00/0.77 은
     출처 불명이 아니다. Hann · 제로패딩 없음 · **평균 제거(AC)** · 진폭 −20 dB ·
     f_tip(el) 로 정규화 하면 소수 둘째 자리까지 재현된다.
     ⇒ 앞 라운드의 부검(`old_fft_width`, 평균 **미**제거 · pad 8)은 **다른 잣대**를 해부했다.
 (2) 금지대역(|f| > 2·f_tip(0) = 2546 Hz)에 우리 커널만 **이산선**을 낸다.
     f_flash 의 정수배에 정확히 앉고(21.0·27.0·34.1·42.1 배), 가장 센 것은 최고선 대비
     −17.8 dB(−15°). 같은 메쉬·같은 자세열의 기하 기준은 −158 dB(수치 영).
     ⇒ 「한계 초과 에너지」는 FM 측대역도 표본잡음도 아니고 **광선격자 이산화 잔차**다.
        그런데 새 잣대 W_q 는 이 대역의 평균을 «잡음»으로 빼도록 정의되어 있어
        **정의상 이 결함을 못 본다.**

⛔ 기존 원장 수정 금지 · GPU 미사용.
"""
from __future__ import annotations
import json, sys, time
import numpy as np

ROOT = "/home/yunjung/workspace/sionna2"
for p in (ROOT + "/src", ROOT + "/benchmark"):
    if p not in sys.path:
        sys.path.insert(0, p)

PRF = 19700.0
F0 = 1272.91
FF = 126.66666666666667
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
LAM = 299792458.0 / 3.5e9
OUT = ROOT + "/outputs/verify_po_elev_attack3.json"
d = np.load(ROOT + "/outputs/elevation_sweep_md.npz")


def w_orig(x, thr_db=20.0, ac=True, pad=1, win="hann"):
    """복원한 **원** 규약."""
    x = np.asarray(x, complex)
    if ac:
        x = x - x.mean()
    n = len(x)
    w = np.hanning(n) if win == "hann" else np.ones(n)
    Z = np.fft.fftshift(np.fft.fft(x * w, n=pad * n))
    f = np.fft.fftshift(np.fft.fftfreq(pad * n, 1.0 / PRF))
    S = np.abs(Z)
    m = S > S.max() * 10 ** (-thr_db / 20)
    return float(np.abs(f[m]).max()) if m.any() else 0.0


# ── 기하 기준(대조군) 재생성 ────────────────────────────────────────
import articulated_fast as AF
from drones import DRONES
fp = AF.FastPoser(DRONES["matrice4e"])
F = np.asarray(fp.f, int)
g = np.asarray(fp.g, dtype=object)
sel = np.unique(F[g == "prop"].ravel())
ph = AF.rotor_phases(np.arange(4096) / PRF,
                     np.array([3808.36, 3791.64, 3795.402, 3804.598]), fp.dirs)
k = 2 * np.pi / LAM
V0 = np.asarray(fp.pose(ph[0]).v, float)
cen = 0.5 * (V0.min(0) + V0.max(0))


def los(a, e):
    a, e = np.radians(a), np.radians(e)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


hp = {e: np.zeros(4096, complex) for e in ELS}
for s in range(0, 4096, 256):
    ee = min(4096, s + 256)
    Vs = np.stack([np.asarray(fp.pose(ph[i]).v, float) for i in range(s, ee)])[:, sel, :]
    for e in ELS:
        hp[e][s:ee] = np.exp(-2j * k * np.linalg.norm(Vs - (cen + 10 * los(0, e)),
                                                      axis=2)).sum(1)


def forbidden(x):
    x = np.asarray(x, complex) - np.mean(x)
    n = len(x)
    Z = np.fft.fftshift(np.fft.fft(x * np.hanning(n), n=4 * n))
    f = np.fft.fftshift(np.fft.fftfreq(4 * n, 1.0 / PRF))
    P = np.abs(Z) ** 2
    nb = np.abs(f) >= 2 * F0
    fm = float(abs(f[nb][np.argmax(P[nb])]))
    return dict(peak_over_forbidden_max_db=round(float(10 * np.log10(P.max() / P[nb].max())), 1),
                peak_over_forbidden_mean_db=round(float(10 * np.log10(P.max() / P[nb].mean())), 1),
                forbidden_max_hz=round(fm, 0),
                forbidden_max_in_flash_units=round(fm / FF, 2),
                forbidden_peak_to_mean=round(float(P[nb].max() / P[nb].mean()), 1),
                implied_speed_mps=round(fm * LAM / 2, 1))


J = dict(_meta=dict(generator="benchmark/verify_po_elev_attack3.py",
                    date=time.strftime("%Y-%m-%d %H:%M:%S"), gpu="사용 안 함",
                    f_forbid_hz=2 * F0, f_flash_hz=FF, v_tip_el0_mps=round(F0 * LAM / 2, 1)))

# (1) 규약 복원
rec = {}
for e in ELS[:6]:
    ft = F0 * np.cos(np.radians(e))
    rec[f"{e:+.0f}"] = dict(w_hz=round(w_orig(d[f"ours/el{e:+.0f}"]), 1),
                            over_ftip_el=round(w_orig(d[f"ours/el{e:+.0f}"]) / ft, 2))
J["old_w20_convention_recovered"] = dict(
    convention="Hann · 제로패딩 없음 · 평균 제거(AC) · 진폭 −20 dB · f_tip(el) 로 나눔",
    instruction_list=[0.80, 2.88, 2.31, 0.99, 1.00, 0.77],
    reproduced=[rec[f"{e:+.0f}"]["over_ftip_el"] for e in ELS[:6]],
    per_el=rec,
    prior_round_variant="평균 **미**제거 · pad 8 → [761.7, 7.8, 1015.4, 762.9, 636.1, 132.3] Hz",
    note_ko=("앞 라운드는 「출처 불명이니 인용하지 마라」고 했으나 규약이 확정된다. "
             "따라서 그 라운드의 −20 dB 부검(전역 최대 = 동체 DC 선 기전, 169~442x 문턱표)은 "
             "**실제로 쓰이지 않은 변종**을 해부한 것이다."),
    threshold_sensitivity_true_convention={
        f"{e:+.0f}": {f"{t}dB": round(w_orig(d[f'ours/el{e:+.0f}'], t), 0)
                      for t in (10, 15, 20, 25, 30, 40)} for e in ELS[:6]})

# (2) 금지대역 이산선
J["forbidden_band_lines"] = {
    f"{e:+.0f}": dict(ours=forbidden(d[f"ours/el{e:+.0f}"]), geom_prop=forbidden(hp[e]))
    for e in ELS}
J["forbidden_band_verdict_ko"] = (
    "우리 커널은 |f| > 2546 Hz 에 **이산선**을 낸다(첨두/평균 56~96 배). 그 선은 f_flash 의 "
    "정수배에 소수 둘째 자리까지 앉고(21.0·27.0·27.96·34.05·42.07 배), −15° 에서는 최고선 "
    "대비 −17.8 dB 밖에 안 내려간다. 같은 메쉬·같은 자세열·같은 송신점의 기하 기준은 같은 "
    "대역이 −158~−170 dB(배정밀도 반올림) 다. ⇒ 메쉬도 자세열도 아니고 **얼린 광선격자의 "
    "이산화**가 원인이다. 5329 Hz 는 시선속도 228 m/s 를 함의한다(날개끝 54.5 m/s 의 4.2 배). "
    "⚠새 잣대 W_q 는 바로 이 대역의 평균을 «잡음»으로 정의해 빼므로 **이 결함을 정의상 못 본다**.")

with open(OUT, "w") as fh:
    json.dump(J, fh, ensure_ascii=False, indent=1)
print("복원한 원 규약 =", J["old_w20_convention_recovered"]["reproduced"])
print("지시문 목록     =", J["old_w20_convention_recovered"]["instruction_list"])
for e in ELS:
    a = J["forbidden_band_lines"][f"{e:+.0f}"]
    print(f"el{e:+4.0f}  ours −{a['ours']['peak_over_forbidden_max_db']:5.1f} dB "
          f"@ {a['ours']['forbidden_max_hz']:6.0f} Hz ({a['ours']['forbidden_max_in_flash_units']:5.2f}×flash, "
          f"{a['ours']['implied_speed_mps']:6.1f} m/s)   geom −{a['geom_prop']['peak_over_forbidden_max_db']:6.1f} dB")
print("OK", OUT)
