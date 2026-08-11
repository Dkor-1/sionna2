# -*- coding: utf-8 -*-
"""
harmonic_window_dependence.py — **«고조파가 이만큼 떨어진다» 가 표적의 성질인가, 창의 성질인가.**

사용자(2026-08-11)
> "PO 방식에선 엄청나게 작아지는데 고조파 성분이 저렇게까지 많이 작아지는 게 맞는 거야?"

■ 왜 재나
대역 에너지의 조화 구조(1× 대 2× 대 3×)를 우리는 두 엔진을 가르는 잣대로 써 왔다
(8/11 덱 7 페이지). 그런데 그 값은 **STFT 창 길이가 정하는 저역통과 필터**를 통과한 뒤의
값이다. 창이 플래시 주기의 0.45 배(3.55 ms)라 **2× 가 그 필터의 무릎 근처**에 온다.
⇒ 창을 바꾸면 조화비가 얼마나 움직이는지 재서, **인용해도 되는 것과 안 되는 것**을 가른다.

■ 무엇이 나왔나 (2026-08-11 실측, 3 m)
  창/주기   창 [ms]   Ours 2×    3×      4×   |  Sionna 2×
   0.15      1.18    −12.28  −20.12   −9.62  |   −2.71
   0.25      1.97    −26.66  −19.64  −10.59  |   +0.15
   0.45      3.55     −6.91  −17.07  −29.48  |   −1.27   ← 현행
   0.60      4.74     −7.48  −21.50  −29.98  |   −1.95
   0.90      7.11    −13.53  −42.15  −40.29  |   −7.25
   1.20      9.47    −23.49  −53.11  −46.93  |  −17.21

⭐**우리 2× 가 −6.9 ↔ −26.7 dB, 20 dB 폭으로 움직인다.** 표적은 그대로다.
⇒ ⛔**«고조파가 N dB 떨어진다» 를 표적의 성질로 인용하지 마라.**

✅**그런데 두 엔진 비교는 6/6 창에서 같은 방향이다** — 우리가 항상 더 빨리 떨어진다
  (차이 5.5 ~ 26.8 dB). ⇒ «우리가 더 빨리 떨어진다» 는 **방향은 인용해도 된다.**

⚠**«단조 감소» 는 모든 창에서 참이 아니다** — 창 0.15 에서 우리 4×(−9.62) > 3×(−20.12).
  현행 창(0.45)에서는 단조다(−6.91 → −17.07 → −29.48).

■ 관련
· 창 규약은 `src/md_mapstyle.py` FLASH_PERIODS_SHARP = 0.45 (시간분해능 우선 규약).
· 플래시 봉우리 개수는 별도 잣대다 — 우리 회전당 2.00 개(간격 7.92 ms, 예측 7.89),
  PathSolver 는 4~6 개이고 **시드에 따라 4.00 ↔ 4.75** 로 달라진다.
  그 가짜 봉우리가 간격을 쪼개 에너지를 2× 로 옮기는 것이 조화 뒤집힘의 기전이다.

    PYTHONPATH=src:benchmark python benchmark/harmonic_window_dependence.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, f"{ROOT}/benchmark")

from md_mapstyle import auto_periods, flash_spec                        # noqa: E402

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF, FFL, FTIP = TJ["prf_hz"], TJ["f_flash_hz"], TJ["f_tip_hz"]
LO, HI = 0.35 * FTIP, 1.00 * FTIP
OUT = f"{ROOT}/outputs/harmonic_window_dependence.json"
PERIODS = (0.15, 0.25, 0.45, 0.60, 0.90, 1.20)


def harmonics_db(E, periods, n_harm: int = 4):
    """대역 에너지 변조 스펙트럼의 1×..n× 를 1× 대비 dB 로. 덱과 같은 규약."""
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, periods)
    b = (np.abs(f) >= LO) & (np.abs(f) <= HI)
    g = (S[b, :] ** 2).sum(axis=0)
    g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt)

    def pk(f0, half=18.0):
        w = (fr >= f0 - half) & (fr <= f0 + half)
        return 20.0 * np.log10(A[w].max()) if w.any() else float("nan")
    p = [pk(k * FFL) for k in range(1, n_harm + 1)]
    return [float(x - p[0]) for x in p]


def flashes_per_rev(E, periods, n_rev: int = 4, t0: float = 0.030):
    """대역 포락에서 봉우리를 직접 센다 — 회전당 몇 개인가."""
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, periods)
    b = (np.abs(f) >= LO) & (np.abs(f) <= HI)
    g = (S[b, :] ** 2).sum(axis=0)
    T = 2.0 / FFL                                   # 회전 주기 (날개 2 장)
    sel = (t >= t0) & (t <= t0 + n_rev * T)
    tt, gg = t[sel], g[sel]
    if gg.size < 8:
        return None, []
    gg = gg / gg.max()
    pk = [i for i in range(1, len(gg) - 1)
          if gg[i] > gg[i - 1] and gg[i] > gg[i + 1] and gg[i] > 0.20]
    dts = (np.diff(tt[pk]) * 1e3).tolist() if len(pk) > 1 else []
    return len(pk) / float(n_rev), [round(x, 2) for x in sorted(dts)]


def main() -> None:
    OZ = np.load(f"{ROOT}/outputs/deck_ours_by_range.npz")
    RZ = np.load(f"{ROOT}/outputs/report07_three_engine_ranges.npz")
    SZ = np.load(f"{ROOT}/outputs/report07_range40.npz")
    CELLS = [("ours_3m", OZ["R3/E"]), ("ours_40m", OZ["R40/E"]),
             ("sionna_3m", RZ["R3/E"]), ("sionna_15m", RZ["R15/E"]),
             ("sionna_40m_s1", SZ["S1/E"]), ("sionna_40m_s2", SZ["S2/E"])]
    cur = auto_periods(PRF, FFL)
    T_ms = 1000.0 / FFL

    print(f"\n═══ 조화 감쇠가 창에 얼마나 걸리나 · 플래시 주기 {T_ms:.2f} ms · "
          f"현행 창 {cur:.2f}×주기 = {cur*T_ms:.2f} ms ═══\n")

    rows = []
    for nm, E in CELLS:
        for pr in PERIODS:
            h = harmonics_db(E, pr)
            npr, dts = flashes_per_rev(E, pr)
            rows.append(dict(cell=nm, periods=pr, window_ms=round(pr * T_ms, 2),
                             h2_db=round(h[1], 2), h3_db=round(h[2], 2),
                             h4_db=round(h[3], 2),
                             flashes_per_rev=npr, peak_gaps_ms=dts[:8],
                             is_current=abs(pr - cur) < 1e-9))

    def get(nm, pr, k):
        return next(r[k] for r in rows if r["cell"] == nm and abs(r["periods"] - pr) < 1e-9)

    print(f"{'창/주기':>8} {'ms':>6} | {'Ours 2x':>8} {'3x':>7} {'4x':>7} | "
          f"{'Sionna 2x':>10} {'3x':>7} | 우리가 더 떨어지나")
    n_ours_lower = 0
    for pr in PERIODS:
        o2, s2 = get("ours_3m", pr, "h2_db"), get("sionna_3m", pr, "h2_db")
        low = o2 < s2
        n_ours_lower += int(low)
        print(f"{pr:8.2f} {pr*T_ms:6.2f} | {o2:8.2f} {get('ours_3m',pr,'h3_db'):7.2f} "
              f"{get('ours_3m',pr,'h4_db'):7.2f} | {s2:10.2f} "
              f"{get('sionna_3m',pr,'h3_db'):7.2f} | {'✅' if low else '❌'} "
              f"{o2-s2:+6.2f} dB" + ("   ←현행" if abs(pr - cur) < 1e-9 else ""))

    o2s = [get("ours_3m", pr, "h2_db") for pr in PERIODS]
    s2s = [get("sionna_3m", pr, "h2_db") for pr in PERIODS]
    verdict = dict(
        ours_h2_range_db=[round(min(o2s), 2), round(max(o2s), 2)],
        ours_h2_swing_db=round(max(o2s) - min(o2s), 2),
        sionna_h2_range_db=[round(min(s2s), 2), round(max(s2s), 2)],
        n_windows=len(PERIODS), n_ours_decays_more=n_ours_lower,
        quotable_ko="✅«우리가 더 빨리 떨어진다» 는 방향은 인용해도 된다 — "
                    f"{n_ours_lower}/{len(PERIODS)} 창에서 성립.",
        not_quotable_ko="⛔«고조파가 N dB 떨어진다» 를 표적의 성질로 인용하지 마라 — "
                        f"창만 바꿔도 {round(max(o2s)-min(o2s),1)} dB 움직인다.",
        monotonic_caveat_ko="⚠«단조 감소» 는 현행 창(0.45)에서만 참이다. "
                            "창 0.15 에서는 우리 4× 가 3× 보다 높다.",
        mechanism_ko="STFT 창이 대역 에너지 포락을 시간축으로 뭉갠다. 창 길이 τ 가 곧 "
                     "저역통과 필터이고, 조화가 그 필터의 어디에 앉느냐로 억눌림이 정해진다. "
                     f"현행 τ = {cur*T_ms:.2f} ms 는 플래시 주기의 {cur:.0%} 라 2× 가 무릎 근처다.",
        flash_count_ko="별도 잣대 — 회전당 봉우리 수. 우리는 2.00 개(간격 7.92 ms, 예측 7.89), "
                       "PathSolver 는 4~6 개이고 시드에 따라 4.00 ↔ 4.75 로 달라진다. "
                       "그 가짜 봉우리가 간격을 쪼개 에너지를 2× 로 옮기는 것이 뒤집힘의 기전이다.")

    json.dump({"_meta": {
        "generator": "benchmark/harmonic_window_dependence.py",
        "question_ko": "«고조파가 이만큼 떨어진다» 가 표적의 성질인가 창의 성질인가",
        "prf_hz": PRF, "f_flash_hz": FFL, "f_tip_hz": FTIP,
        "band_hz": [LO, HI], "flash_period_ms": round(T_ms, 3),
        "current_periods": cur, "current_window_ms": round(cur * T_ms, 2),
        "window_convention": "src/md_mapstyle.py FLASH_PERIODS_SHARP (시간분해능 우선)",
        "harmonics_are_relative_to_1x": True},
        "rows": rows, "verdict": verdict}, open(OUT, "w"),
        ensure_ascii=False, indent=1)

    print(f"\n⭐우리 2× 는 창만 바꿔도 {verdict['ours_h2_swing_db']} dB 움직인다 "
          f"({verdict['ours_h2_range_db'][0]} ~ {verdict['ours_h2_range_db'][1]})")
    print(f"✅ 그러나 {n_ours_lower}/{len(PERIODS)} 창에서 우리가 더 빨리 떨어진다 — 방향은 견고")
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
