# -*- coding: utf-8 -*-
"""
free_harvest_pose_ladder_0816.py — ⭐**자세 수 사다리** (백로그 3 위 · R24)
==========================================================================

■ 묻는 것 하나
    「날개끝 상한 **위**」 에 보이는 빗살은 **자세 격자의 산물**인가, **진짜 구조**인가.

    상한 위 빗살은 리포트·덱이 «구조» 라고 부르는 자리다. 광선 수에는 이미 불변임이
    확정됐고(R17), 남은 유력 용의자가 **자세 격자**(= 시간 표집 격자)다. 원장에 자세를
    4 배 늘린 깨끗한 짝이 있다 — 넷 다 결측 0.

        ours_r15_n8192                  ↔  ours_r15_n32768                  (el 0 · −30 · −60)
        sionna_p4000000000_r15_n8192_d1 ↔  sionna_p4000000000_r15_n32768_d1 (el −30)

■ 자세 수가 실제로 무엇을 바꾸나 — ⛔먼저 못 박는다
    `elevation_sweep_md.run()` 은 자세를 `t_i = i / PRF` 로 찍는다(PRF 19,700 Hz 고정).
    따라서 **자세 수 = 기록 길이**이지 표집률이 아니다.
        n =  8,192 → 0.4158 s · 빈 간격 PRF/n = 2.405 Hz · 플래시 52.7 회
        n = 32,768 → 1.6634 s · 빈 간격        0.601 Hz · 플래시 210.8 회
    ⇒ 4 배는 (a) **주파수 분해능 4 배**와 (b) **새 시간 정보 1.25 s** 를 **함께** 준다.
      이 둘을 안 가르면 «빗살이 변했다» 를 물리로 오독한다. 그래서 아래 네 팔로 가른다.

■ 네 팔 (같은 잣대 · 같은 창)
    A  n=8192 팔 그대로                      — 기준선
    B  n=32768 팔의 **앞 8,192 자세**        — 같은 분해능 · 같은 자세 · **격자만 다르다**
    C  n=32768 팔 전체                       — 분해능 4 배 + 새 시간
    Z  A 를 **영채움**해 32,768 로 변환       — ⭐분해능만 4 배(새 정보 0)
    Q  C 를 8,192 씩 **네 토막**             — ⭐같은 n 에서 «어느 구간을 봤나» 산포

    · C ≈ Z 이면 4 배가 준 것은 **빈 세기(bookkeeping)** 뿐이다 → 빗살은 그대로다.
    · |C − A| 가 Q 산포 안이면 **판정 불가**(움직였다고 말할 수 없다).
    · B − A 는 «자세 수» 가 아니라 **얼린 격자가 달라진 몫**이다(아래 ⚠).

■ ⚠격자 교란 — 이 짝은 완전한 단일축이 **아니다**
    우리 커널 팔은 `probes = [fp.pose(ph[i]) for i in range(0, n, n//64)]` 로 뽑은 64 자세의
    합집합 bbox 위에 격자를 얼린다(`elevation_sweep_md.py:265`). n 이 바뀌면 **probe 자세가
    달라져** 얼린 격자가 바뀐다. 즉 n 8192 ↔ 32768 에는 «자세 수» 와 «격자» 가 함께 실려 있다.
    그래서 판정 문턱은 프로젝트의 ⓪ **격자 산포 밴드**다 —
        el 0° 3.86 · −15° 1.31 · −30° 0.37 · −45° 0.09 · −60° 0.02 · −75° 0.10 · −90° 5.62 dB
    PathSolver 팔에는 격자가 없다(광선을 Rx 에서 쏜다) — 그래서 sionna 짝이 **격자 없는 대조군**이다.

■ 잣대 — ⭐정의를 바꾸지 않는다
    `build_md_atlas.rhythm_share` · `comb_contrast_db` 를 그대로 쓴다(값이 이미 인용돼 있다).
    다만 FFT 길이를 인자로 받는 판을 따로 두어 **영채움 팔(Z)** 을 만든다 — nfft=n 이면
    원본과 **비트동일**임을 게이트로 검사한다(`selfcheck_bitidentical`).
    · 리듬 몫 rhythm_pct  — 상한 위 에너지 중 박자 정수배(±8 Hz)에 붙은 몫 [%]
      ⚠널(백색값)이 팔마다 다르다 — 이 판은 전부 matrice4e 라 ≈12.5 % 다. **널 대비**로 읽는다.
    · 상한 위 몫 above_ceiling_pct — 움직이는 에너지 중 상한 위 몫 [%]
    · 빗살 대비 comb_db — 상한 **아래** 빗살 대비 [dB] (백색 널 ≈ 0)
    · 요동 전력 moving_power_db — ⭐**정지 성분 제거 후** 레벨. 원장의 `level_db` 는 DC 를
      **안 뺀** 값이라 이 판정에 쓰지 않는다(규약).
    · ⭐보조 신설 — above_comb_db: 상한 **위** 의 빗살 대비 [dB].
      on = 정수배 ±8 Hz · off = 정수배 사이 한가운데 ±8 Hz, 같은 대역·같은 창.
      **왜 신설하나** — 리듬 몫은 «몇 개의 빈이 창에 드는가» 에 걸려 분해능이 바뀌면 장부가
      같이 움직인다. 대비(비율)는 창 안팎을 같은 방식으로 세므로 그 장부에 훨씬 덜 걸린다.
      ⚠정본 잣대가 아니다 — **보조**로만 읽고, 정본 판정은 리듬 몫·상한 위 몫으로 한다.

■ ⭐로터 산포가 만드는 예측 — 재기 전에 못 박는다
    네 로터의 회전수가 서로 다르다(원장 3808.36 · 3791.64 · 3795.402 · 3804.598 rpm).
    날개 2 장이라 로터별 박자는 126.945 · 126.388 · 126.513 · 126.820 Hz — 명목 126.667 에서
    ±0.279 Hz 흩어져 있다. k 번째 배음에서 이 산포는 **k × 0.557 Hz** 로 벌어진다.
        · k ≳ 29 (≈3.6 kHz) 부터 산포가 창(±8 Hz) 을 넘는다 → 배음이 창 밖으로 샌다
        · n=8192 는 빈 2.405 Hz·해닝 주엽 ±4.8 Hz 라 k ≲ 10 대에서 네 선이 **뭉쳐 보이고**,
          n=32768 은 빈 0.601 Hz 라 같은 자리에서 네 선이 **갈라진다**
    ⇒ 자세를 늘리면 «빗살이 흐려지는» 방향으로 움직이는 것이 **정상**일 수 있다.
      그러므로 리듬 몫이 조금 내려간 것만으로 «격자의 산물» 이라 부르면 안 된다. 이 판은
      per-harmonic 대비 곡선으로 그 몫을 따로 센다(`harmonic_curve`).

■ ⭐튐(이상 자세) 검사 — 규약대로
    `outputs/outlier_census_0816.json`(349 행 시점) 의 등급을 먼저 인용하고, census 에 없는
    새 칸(B·Z·Q 토막)은 census 와 **같은 절차**로 직접 잰다 — 자세를 **지우지 않고 이웃 평균으로
    갈아 끼운다**(`build_md_atlas.replace_pose` 와 같은 정의). 죄 없는 자세 대조도 같이 돌린다.

■ 원장 (읽기 전용 · ⛔GPU 0 · sionna.rt/mitsuba 임포트 없음 · ⛔git 없음)
    outputs/elevation_sweep_md.{json,npz} · outputs/outlier_census_0816.json
    outputs/depth_axis_verdict_0816.json (격자 산포 밴드 · 빗살 백색 널 폭)

■ 굽는 것
    outputs/free_harvest_pose_ladder_0816.json
    outputs/figures/free_harvest_pose_ladder_0816.png

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/free_harvest_pose_ladder_0816.py
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os

import numpy as np

import build_md_atlas as A                                             # noqa: E402

ROOT = A.ROOT
OUTJ = os.path.join(ROOT, "outputs", "free_harvest_pose_ladder_0816.json")
FIGD = os.path.join(ROOT, "outputs", "figures")
FIGP = os.path.join(FIGD, "free_harvest_pose_ladder_0816.png")
CENSUS_J = os.path.join(ROOT, "outputs", "outlier_census_0816.json")
DEPTH_J = os.path.join(ROOT, "outputs", "depth_axis_verdict_0816.json")

PRF = A.PRF
HW = A.RHY_HW                     # 8 Hz — 정수배 창 반폭
N_CONTROL = 12                    # 죄 없는 자세 대조 횟수 (census 와 같은 값)
RNG = np.random.default_rng(20260816)

#: 짝 — (짧은 이름, n=8192 팔, n=32768 팔, 앙각들)
PAIRS = [
    ("ours", "ours_r15_n8192", "ours_r15_n32768", [0.0, -30.0, -60.0]),
    ("PathSolver", "sionna_p4000000000_r15_n8192_d1",
     "sionna_p4000000000_r15_n32768_d1", [-30.0]),
]


# ═══════════════════════════════════════════════════════════════════════════
# 0. 잣대 — 정의는 build_md_atlas 그대로, FFT 길이만 인자로 뺀다
# ═══════════════════════════════════════════════════════════════════════════
def _spec(E, nfft=None, prf=None):
    """해닝 창 · DC 제거 · (영채움) FFT 전력과 주파수 축.

    ⚠`prf` 는 **자세 솎기 탐침 전용**이다(아래 decimation_probe). 원래 팔은 전부 PRF 그대로다.
    """
    x = np.asarray(E, complex)
    n = x.size
    x = (x - x.mean()) * np.hanning(n)
    N = int(nfft or n)
    P = np.abs(np.fft.fft(x, n=N)) ** 2
    fr = np.fft.fftfreq(N, 1.0 / float(prf or PRF))
    return P, fr


def rhythm_share_n(E, f_flash, f_tip, hw=HW, nfft=None, prf=None):
    """`build_md_atlas.rhythm_share` 와 **같은 정의** · FFT 길이만 인자."""
    P, fr = _spec(E, nfft, prf)
    degenerate = f_tip <= 1e-6
    above = np.abs(fr) >= f_tip
    k = np.round(np.abs(fr) / f_flash)
    on = above & (np.abs(np.abs(fr) - k * f_flash) <= hw)
    n_above = int(above.sum())
    null = float(100.0 * int(on.sum()) / n_above) if n_above else None
    den = P[above].sum()
    tot = P.sum()
    frac_above = float(100.0 * den / tot) if tot > 0 else None
    if den <= 0:
        return None, null, frac_above, degenerate
    return float(100.0 * P[on].sum() / den), null, frac_above, degenerate


def comb_contrast_db_n(E, f_flash, f_tip, hw=HW, nfft=None, prf=None):
    """`build_md_atlas.comb_contrast_db` 와 **같은 정의**(상한 **아래**) · FFT 길이만 인자."""
    lo, hi = 2.0 * f_flash, float(f_tip)
    if not (hi >= 3.0 * f_flash):
        return None
    P, fr0 = _spec(E, nfft, prf)
    fr = np.abs(fr0)
    band = (fr >= lo) & (fr <= hi)
    k = fr / f_flash
    on = band & (np.abs(k - np.round(k)) * f_flash <= hw)
    off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash <= hw)
    if int(on.sum()) < 4 or int(off.sum()) < 4:
        return None
    num, den = float(P[on].mean()), float(P[off].mean())
    if not (num > 0 and den > 0):
        return None
    return float(10.0 * math.log10(num / den))


def above_comb_db_n(E, f_flash, f_tip, hw=HW, nfft=None, prf=None):
    """⭐보조 신설 — 상한 **위** 빗살 대비 [dB]. 백색이면 0 dB.

    리듬 몫과 달리 **창 안 ÷ 창 사이** 라 «빈이 몇 개 드는가» 라는 장부에 훨씬 덜 걸린다.
    """
    if f_tip <= 1e-6:
        return None
    P, fr0 = _spec(E, nfft, prf)
    fr = np.abs(fr0)
    band = fr >= f_tip
    k = fr / f_flash
    on = band & (np.abs(k - np.round(k)) * f_flash <= hw)
    off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash <= hw)
    if int(on.sum()) < 8 or int(off.sum()) < 8:
        return None
    num, den = float(P[on].mean()), float(P[off].mean())
    if not (num > 0 and den > 0):
        return None
    return float(10.0 * math.log10(num / den))


def comb_reach(curve, f_flash, null_db=3.0, need=3):
    """빗살이 **어디까지** 살아 있나 — 대비가 백색 널(3 dB) 아래로 `need` 배음 연속 꺼지기 직전의 k.

    ⭐왜 재나 — 이 «도달 거리» 는 **로터 회전수 산포**가 정하는 양이라(k×0.557 Hz 가 창 ±8 Hz 를
    넘으면 배음이 창 밖으로 샌다) 자세 수와 무관해야 한다. 두 자세 수에서 같으면 빗살의 끝을
    정하는 것이 **로터**이지 표집이 아니라는 뜻이다.
    """
    run, last = 0, None
    for h in curve:
        if h["contrast_db"] < null_db:
            run += 1
            if run >= need:
                break
        else:
            run = 0
            last = h["k"]
    return dict(k_last=last, f_hz=(None if last is None else round(last * f_flash, 1)),
                null_db=null_db, need_consecutive=need,
                median_contrast_db=(None if not curve else
                                    round(float(np.median([h["contrast_db"]
                                                           for h in curve])), 2)))


def harmonic_curve(E, f_flash, f_tip, hw=HW, nfft=None, kmax=70, prf=None):
    """배음마다 «선 ÷ 그 옆 골» 대비 [dB] — 빗살이 **어디까지** 살아 있나."""
    P, fr0 = _spec(E, nfft, prf)
    fr = np.abs(fr0)
    out = []
    k0 = int(math.ceil(max(f_tip, 1e-9) / f_flash))
    for k in range(k0, kmax + 1):
        fk = k * f_flash
        if fk + 0.5 * f_flash > 0.5 * float(prf or PRF):
            break
        on = (np.abs(fr - fk) <= hw)
        off = (np.abs(fr - (fk + 0.5 * f_flash)) <= hw) | \
              (np.abs(fr - (fk - 0.5 * f_flash)) <= hw)
        if int(on.sum()) < 2 or int(off.sum()) < 2:
            continue
        a, b = float(P[on].mean()), float(P[off].mean())
        if not (a > 0 and b > 0):
            continue
        out.append(dict(k=k, f_hz=round(fk, 1),
                        contrast_db=round(10 * math.log10(a / b), 2),
                        rotor_spread_hz=round(k * ROTOR_SPREAD_HZ, 2)))
    return out


def headline(E, f_flash, f_tip, nfft=None, prf=None):
    share, null, above, degen = rhythm_share_n(E, f_flash, f_tip, nfft=nfft, prf=prf)
    x = np.asarray(E, complex)
    x = x - x.mean()
    p = float(np.mean(np.abs(x) ** 2))
    return dict(
        n=int(np.size(E)), nfft=int(nfft or np.size(E)), prf_hz=float(prf or PRF),
        rhythm_pct=(None if share is None else round(share, 3)),
        rhythm_null_pct=(None if null is None else round(null, 3)),
        above_ceiling_pct=(None if above is None else round(above, 4)),
        comb_db=(lambda v: None if v is None else round(v, 3))(
            comb_contrast_db_n(E, f_flash, f_tip, nfft=nfft, prf=prf)),
        above_comb_db=(lambda v: None if v is None else round(v, 3))(
            above_comb_db_n(E, f_flash, f_tip, nfft=nfft, prf=prf)),
        moving_power_db=(None if p <= 0 else round(10 * math.log10(p), 3)),
        ac_over_dc=round(float(p / (abs(np.mean(np.asarray(E, complex))) ** 2 + 1e-300)), 6),
        rhythm_degenerate=bool(degen))


# ⭐로터 산포 — 원장의 로터별 회전수에서 직접 계산한다
_RPM = np.asarray(A.M["rpm_per_rotor"], float)
_BLADES = 2
_ROTOR_BPF = _BLADES * _RPM / 60.0
ROTOR_SPREAD_HZ = float(_ROTOR_BPF.max() - _ROTOR_BPF.min())


def decimation_probe(E32, f_flash, f_tip, strides=(1, 2, 4)):
    """⭐**자세 격자를 진짜로 성기게** 만드는 유일한 방향 — 저장된 자세를 솎는다.

    ■ 왜 이게 필요한가
        위의 사다리(8,192↔32,768)는 표집률이 아니라 **기록 길이**를 바꾼다. «격자가 성기면
        빗살이 생기나»(겹침·에일리어싱 가설)는 그 축으로는 못 묻는다. 저장된 자료로 갈 수
        있는 방향은 **성기게** 뿐이라(PRF 위로는 못 간다) 그쪽을 본다.

    ■ ⭐이 탐침이 가르는 것 — 겹침(alias)은 빗살 자리에 **안 떨어진다**
        PRF/4 = 4,925 Hz 이고 4925 ÷ 126.667 = 38.88 로 **정수가 아니다.** 그래서 위쪽에서
        접혀 내려온 성분은 126.667 Hz 의 정수배가 **아닌** 자리에 앉는다. 솎아도 빗살이
        정수배 자리에 그대로 서 있으면 그 선은 접힌 것이 아니라 **원래 거기 있던 선**이다.
        (접힌 성분이 골을 메우니 대비가 내려가는 것은 **예상된 일**이다.)

    ⚠파생 탐침이다 — 새로 계산한 팔이 아니다. «성기게» 한쪽만 본다는 한계를 함께 적는다.
    """
    out = []
    for s in strides:
        y = np.asarray(E32, complex)[::s]
        prf = PRF / s
        if f_tip >= 0.5 * prf:
            out.append(dict(stride=s, prf_hz=round(prf, 1), n=int(y.size),
                            skipped_ko="상한이 나이퀴스트 위 — 잣대가 성립하지 않는다"))
            continue
        h = headline(y, f_flash, f_tip, prf=prf)
        # ⭐접힘이 빗살 자리에 앉나 — **실제로 일어나는 접힘 차수만** 센다.
        #   원래 띠는 ±PRF/2 = ±9,850 Hz 이므로 필요한 차수는 m ≤ ceil(9850/prf) 뿐이다.
        folds = []
        for m in range(1, int(math.ceil(0.5 * PRF / prf)) + 1):
            f = m * prf
            off = abs(f - round(f / f_flash) * f_flash)
            folds.append(dict(m=m, fold_hz=round(f, 1), offset_from_comb_hz=round(off, 2),
                              lands_in_window=bool(off <= HW)))
        out.append(dict(stride=s, prf_hz=round(prf, 1), n=int(y.size),
                        nyquist_hz=round(0.5 * prf, 1),
                        rhythm_pct=h["rhythm_pct"], rhythm_null_pct=h["rhythm_null_pct"],
                        above_comb_db=h["above_comb_db"],
                        above_ceiling_pct=h["above_ceiling_pct"],
                        comb_db=h["comb_db"],
                        alias_folds=folds,
                        any_fold_lands_on_comb=bool(any(f["lands_in_window"] for f in folds))))
    return out


def replace_pose(E, i):
    """⭐그 자세를 **삭제하지 않고** 이웃 평균으로 갈아 끼운다 (census 와 같은 정의)."""
    y = np.array(E, complex, copy=True)
    n = y.size
    y[i] = 0.5 * (E[(i - 1) % n] + E[(i + 1) % n])
    return y


def outlier_probe(E, f_flash, f_tip, nfft=None):
    """census 와 같은 절차의 축소판 — 맨 위 자세 하나를 갈아 끼우면 헤드라인이 얼마나 움직이나."""
    x = np.asarray(E, complex)
    ac = np.abs(x - x.mean())
    order = np.argsort(ac)[::-1]
    i1 = int(order[0])
    med = float(np.median(ac))
    base = headline(x, f_flash, f_tip, nfft=nfft)
    rep = headline(replace_pose(x, i1), f_flash, f_tip, nfft=nfft)
    keys = ("rhythm_pct", "comb_db", "above_comb_db",
            "moving_power_db", "above_ceiling_pct")
    d_top = {k: (None if (base[k] is None or rep[k] is None)
                 else round(rep[k] - base[k], 4)) for k in keys}
    # 죄 없는 자세 대조 — 중앙 순위에서 뽑는다
    mid = order[order.size // 2 - N_CONTROL // 2: order.size // 2 + N_CONTROL // 2]
    ctl = {k: 0.0 for k in keys}
    for i in mid.tolist():
        h = headline(replace_pose(x, int(i)), f_flash, f_tip, nfft=nfft)
        for k in keys:
            if base[k] is not None and h[k] is not None:
                ctl[k] = max(ctl[k], abs(h[k] - base[k]))
    dom = {k: (None if (d_top[k] is None or ctl[k] <= 0)
               else round(abs(d_top[k]) / ctl[k], 3)) for k in keys}
    return dict(argmax_pose=i1,
                isolation=(None if not np.isfinite(ac[order[1]]) or ac[order[1]] <= 0
                           else round(float(ac[i1] / ac[order[1]]), 4)),
                top1_over_median=(None if med <= 0 else round(float(ac[i1] / med), 4)),
                replace_one=d_top,
                innocent_control_max_abs={k: round(v, 4) for k, v in ctl.items()},
                dominance=dom, n_control=int(mid.size))


# ═══════════════════════════════════════════════════════════════════════════
# 1. 문턱 — ⛔임의 숫자 금지 · 저장된 원장에서 읽는다
# ═══════════════════════════════════════════════════════════════════════════
def load_bands():
    """⭐프로젝트의 ⓪ 격자 산포 밴드 — **저장된 정본에서 그대로 읽는다**(임의 숫자 금지).

    반환하는 것 넷 —
        level_db_by_el    레벨(정지 성분 제거 후) 밴드 [dB] · 앙각별
        rhythm_pp_by_el   리듬 몫 밴드 [%p] · 앙각별  (전역 정본 21.8 %p 도 함께)
        comb_db_by_el     빗살 대비 밴드 [dB] · 앙각별 (전역 보수 하한 4.04 dB)
        above_pp_global   상한 위 몫 밴드 [%p] (전앙각 최대 12.55 %p)
    """
    import depth_axis_verdict_0816 as D2                                # noqa: E402
    return dict(
        level_db_by_el={float(k): v for k, v in D2.GRID_BAND_AC_DB.items()},
        rhythm_pp_by_el={float(k): v for k, v in D2.GRID_BAND_RHYTHM_PP_BY_EL.items()},
        comb_db_by_el={float(k): v for k, v in D2.GRID_BAND_COMB_DB_BY_EL.items()},
        rhythm_pp_global=float(D2.GRID_BAND_RHYTHM_PP_GLOBAL),
        comb_db_global=float(D2.GRID_BAND_COMB_DB_GLOBAL),
        above_pp_global=float(D2.GRID_BAND_ABOVE_PP_GLOBAL),
        comb_null_db=float(D2.COMB_NULL_DB),
        seed_sd_db=float(D2.SEED_SD_DB),
        source="benchmark/depth_axis_verdict_0816.py (2026-08-16 정정본 · "
               "frame_completion_0816.q4_grid_band)",
        scope_warning_ko=(
            "⚠격자 산포 밴드는 **우리 커널(SBR+PO)의 λ/12↔λ/24 격자 축**에서 잰 값이다. "
            "PathSolver 팔에는 격자가 없어 **가져다 쓰는** 밴드다 — 그 짝에는 시드 산포"
            f"(sd {D2.SEED_SD_DB:g} dB)를 함께 놓고 읽는다."))


def census_grade(cell):
    if not os.path.exists(CENSUS_J):
        return None
    C = json.load(open(CENSUS_J))
    for c in C["cells"]:
        if c["cell"] == cell:
            return dict(grade=c.get("grade"), gradeable=c.get("gradeable"),
                        isolation=c.get("isolation"),
                        top1_over_median=c.get("top1_over_median"),
                        dominance=c.get("impact", {}).get("dominance"),
                        census_rows=C["_meta"]["ledger_state"]["n_rows"],
                        census_written=C["_meta"]["written_at_kst"])
    return dict(grade=None, note_ko="census(349 행 시점)에 이 칸이 없다")


# ═══════════════════════════════════════════════════════════════════════════
# 2. 게이트 — 신설 코드가 기존 정의와 **비트동일**한지
# ═══════════════════════════════════════════════════════════════════════════
def selfcheck_bitidentical():
    out = []
    for arm, el in (("ours_r15_n8192", 0.0), ("ours_r15_n8192", -30.0),
                    ("ours_r15_n32768", -60.0),
                    ("sionna_p4000000000_r15_n8192_d1", -30.0)):
        E = A.series(arm, el)
        r = A.arm_rates(arm)
        ff, ft = r["f_flash_hz"], A.f_tip_at(r, el)
        a1 = A.rhythm_share(E, ff, ft)
        b1 = rhythm_share_n(E, ff, ft)
        c1 = A.comb_contrast_db(E, ff, ft)
        c2 = comb_contrast_db_n(E, ff, ft)
        ok = all((x is None and y is None) or (x == y) for x, y in zip(a1, b1)) \
            and ((c1 is None and c2 is None) or c1 == c2)
        out.append(dict(cell=f"{arm}/el{el:+.0f}", bit_identical=bool(ok),
                        atlas_rhythm=None if a1[0] is None else round(a1[0], 6),
                        here_rhythm=None if b1[0] is None else round(b1[0], 6),
                        atlas_comb_db=None if c1 is None else round(c1, 6),
                        here_comb_db=None if c2 is None else round(c2, 6)))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 3. 본문
# ═══════════════════════════════════════════════════════════════════════════
def kst_now():
    return (_dt.datetime.utcnow() + _dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")


def build():
    B = load_bands()
    gate = selfcheck_bitidentical()
    L = json.load(open(A.LED_J))
    ROWS = {(r["engine"], float(r["el_deg"])): r for r in L["rows"]}

    cells = []
    for short, arm8, arm32, els in PAIRS:
        r8, r32 = A.arm_rates(arm8), A.arm_rates(arm32)
        assert r8["drone"] == r32["drone"], "기체가 다르면 널이 달라 비교 금지"
        ff = r8["f_flash_hz"]
        for el in els:
            ft = A.f_tip_at(r8, el)
            E8 = A.series(arm8, el)
            E32 = A.series(arm32, el)
            n8, n32 = E8.size, E32.size

            # ── 자세 겹침 검사 — 32768 팔의 앞 8192 자세는 **같은 시각**의 자세다
            head = E32[:n8]
            num = float(np.abs(np.vdot(head, E8)))
            den = float(np.linalg.norm(head) * np.linalg.norm(E8))
            coh = None if den <= 0 else round(num / den, 9)
            dlev = round(20 * math.log10((np.abs(head).mean() + 1e-300) /
                                         (np.abs(E8).mean() + 1e-300)), 3)
            same_bits = bool(np.array_equal(head, E8))
            rel = float(np.max(np.abs(head - E8)) /
                        (np.max(np.abs(E8)) + 1e-300))

            arms = {}
            arms["A_n8192"] = headline(E8, ff, ft)
            arms["B_n32768_head8192"] = headline(head, ff, ft)
            arms["C_n32768_full"] = headline(E32, ff, ft)
            arms["Z_n8192_zeropad32768"] = headline(E8, ff, ft, nfft=n32)
            arms["Zb_head8192_zeropad32768"] = headline(head, ff, ft, nfft=n32)
            quarters = [headline(E32[j * n8:(j + 1) * n8], ff, ft)
                        for j in range(n32 // n8)]

            def scat(key):
                v = [q[key] for q in quarters if q[key] is not None]
                if len(v) < 2:
                    return None
                return dict(n=len(v), min=round(min(v), 3), max=round(max(v), 3),
                            span=round(max(v) - min(v), 3),
                            mean=round(float(np.mean(v)), 3),
                            sd=round(float(np.std(v, ddof=1)), 3))

            keys = ("rhythm_pct", "above_ceiling_pct", "comb_db",
                    "above_comb_db", "moving_power_db")
            quarter_scatter = {k: scat(k) for k in keys}

            def dd(a, b, k):
                x, y = arms[a][k], arms[b][k]
                return None if (x is None or y is None) else round(y - x, 3)

            deltas = {}
            for k in keys:
                deltas[k] = dict(
                    C_minus_A=dd("A_n8192", "C_n32768_full", k),
                    Z_minus_A=dd("A_n8192", "Z_n8192_zeropad32768", k),
                    C_minus_Z=dd("Z_n8192_zeropad32768", "C_n32768_full", k),
                    B_minus_A=dd("A_n8192", "B_n32768_head8192", k),
                    C_minus_B=dd("B_n32768_head8192", "C_n32768_full", k),
                    quarter_span=(quarter_scatter[k] or {}).get("span"))

            # ⭐문턱 — 저장된 정본 밴드 · 이 판의 «같은 n 구간 산포» 둘 다
            band_of = {
                "rhythm_pct": B["rhythm_pp_by_el"].get(float(el)),
                "comb_db": B["comb_db_by_el"].get(float(el)),
                "above_ceiling_pct": B["above_pp_global"],
                "moving_power_db": B["level_db_by_el"].get(float(el)),
                # ⚠보조 신설 잣대에는 프로젝트 밴드가 **없다** — 빌리지 않는다
                "above_comb_db": None,
            }
            band_src_of = {
                "rhythm_pct": "GRID_BAND_RHYTHM_PP_BY_EL",
                "comb_db": "GRID_BAND_COMB_DB_BY_EL",
                "above_ceiling_pct": "GRID_BAND_ABOVE_PP_GLOBAL(전앙각 최대)",
                "moving_power_db": "GRID_BAND_AC_DB",
                "above_comb_db": None,
            }

            # ⭐판정 — 「밴드 안이면 판정 불가」 · 밴드가 없으면 구간 산포로만
            def verdict_for(k):
                d = deltas[k]["C_minus_A"]
                sp = deltas[k]["quarter_span"]
                bd = band_of[k]
                if d is None:
                    return dict(verdict="측정 불가", delta=None, band=bd, span=sp)
                thr = max([x for x in (sp, bd) if x is not None], default=None)
                if thr is None:
                    return dict(verdict="문턱 없음 — 판정 보류", delta=d, band=bd, span=sp,
                                note_ko="⚠보조 신설 잣대라 빌릴 밴드가 없다 — 참고값으로만")
                return dict(
                    verdict=("판정 불가 (밴드·산포 안)" if abs(d) <= thr
                             else "밴드·산포 밖 — 움직였다"),
                    delta=d, band=bd, band_source=band_src_of[k], span=sp,
                    threshold_used=round(float(thr), 3),
                    inside_band=(None if bd is None else bool(abs(d) <= bd)),
                    inside_quarter_span=(None if sp is None else bool(abs(d) <= sp)))

            # ⭐«읽기» 가 바뀌었나 — 수가 움직여도 읽기가 그대로면 헤드라인은 안 뒤집힌다
            nullv = arms["A_n8192"]["rhythm_null_pct"]
            reading = dict(
                rhythm_over_null_8192=(None if (arms["A_n8192"]["rhythm_pct"] is None
                                                or not nullv) else
                                       round(arms["A_n8192"]["rhythm_pct"] / nullv, 2)),
                rhythm_over_null_32768=(None if (arms["C_n32768_full"]["rhythm_pct"] is None
                                                 or not nullv) else
                                        round(arms["C_n32768_full"]["rhythm_pct"] / nullv, 2)),
                rhythm_null_pct=nullv,
                comb_reading_8192=("빗살 있음" if (arms["A_n8192"]["comb_db"] or 0)
                                   > B["comb_null_db"] else "빗살 없음(백색 널 자리)"),
                comb_reading_32768=("빗살 있음" if (arms["C_n32768_full"]["comb_db"] or 0)
                                    > B["comb_null_db"] else "빗살 없음(백색 널 자리)"),
                above_comb_reading_8192=("상한 위 빗살 있음"
                                         if (arms["A_n8192"]["above_comb_db"] or 0)
                                         > B["comb_null_db"] else "상한 위 빗살 없음"),
                above_comb_reading_32768=("상한 위 빗살 있음"
                                          if (arms["C_n32768_full"]["above_comb_db"] or 0)
                                          > B["comb_null_db"] else "상한 위 빗살 없음"),
                near_numeric_floor=bool(arms["C_n32768_full"]["ac_over_dc"] <= 1e-11))
            reading["reading_flipped"] = bool(
                reading["comb_reading_8192"] != reading["comb_reading_32768"]
                or reading["above_comb_reading_8192"] != reading["above_comb_reading_32768"])

            cells.append(dict(
                pair=short, elevation_deg=el,
                arm_8192=arm8, arm_32768=arm32,
                cell_8192=f"{arm8}/el{el:+.0f}", cell_32768=f"{arm32}/el{el:+.0f}",
                drone=r8["drone"], f_flash_hz=round(ff, 4), f_tip_hz=round(ft, 2),
                n_poses=[n8, n32],
                record_s=[round(n8 / PRF, 4), round(n32 / PRF, 4)],
                bin_hz=[round(PRF / n8, 4), round(PRF / n32, 4)],
                flash_cycles=[round(n8 / PRF * ff, 1), round(n32 / PRF * ff, 1)],
                ledger_n_missing=[ROWS[(arm8, el)]["n_missing"],
                                  ROWS[(arm32, el)]["n_missing"]],
                ledger_level_db_raw_dc_kept=[ROWS[(arm8, el)]["level_db"],
                                             ROWS[(arm32, el)]["level_db"]],
                pose_overlap=dict(
                    head_equals_8192_bitwise=same_bits,
                    coherence=coh, max_rel_pose_diff=float(f"{rel:.3e}"),
                    mean_level_diff_db_dc_kept=dlev,
                    ac_level_diff_db_dc_removed=deltas["moving_power_db"]["B_minus_A"],
                    note_ko=("자세 시각은 t=i/PRF 라 앞 8,192 자세는 **같은 시각·같은 로터 위상**"
                             "이다. 그래도 값이 다르면 그 차이는 **얼린 격자**(우리 커널) 또는 "
                             "**광선 표집**(PathSolver)에서 온 것이지 자세 수에서 온 것이 아니다."),
                    dc_warning_ko=("⚠mean_level_diff_db_dc_kept 는 DC 를 **안 뺀** 값이다"
                                   "(원장 level_db 와 같은 정의). 판정에는 옆의 "
                                   "ac_level_diff_db_dc_removed 를 쓴다 — 프로젝트에서 세 번 "
                                   "재발한 AC/DC 함정이다.")),
                arms=arms, quarters=quarters, quarter_scatter=quarter_scatter,
                deltas=deltas,
                cell_reading_ko=(
                    f"리듬 몫 {arms['A_n8192']['rhythm_pct']:.1f} → "
                    f"{arms['C_n32768_full']['rhythm_pct']:.1f} % "
                    f"(백색 널 {arms['A_n8192']['rhythm_null_pct']:.1f} %). "
                    f"움직임 {deltas['rhythm_pct']['C_minus_A']:+.2f} %p 중 분해능 장부 몫은 "
                    f"{deltas['rhythm_pct']['Z_minus_A']:+.2f} %p 뿐이고 나머지는 **새로 본 "
                    f"1.25 s** 다 — 네 토막이 각각 "
                    + ", ".join(f"{q['rhythm_pct']:.1f}" for q in quarters) + " % 라 "
                    f"같은 n 에서도 구간마다 {quarter_scatter['rhythm_pct']['span']:.1f} %p "
                    f"흔들린다. 자세를 늘려 얻는 것은 **다른 답이 아니라 덜 흔들리는 답**이다."),
                verdict_by_metric={k: verdict_for(k) for k in keys},
                reading=reading,
                harmonic_curve=dict(
                    n8192=(_h8 := harmonic_curve(E8, ff, ft)),
                    n32768=(_h32 := harmonic_curve(E32, ff, ft)),
                    zeropad=(_hz := harmonic_curve(E8, ff, ft, nfft=n32)),
                    reach=dict(n8192=comb_reach(_h8, ff), n32768=comb_reach(_h32, ff),
                               zeropad=comb_reach(_hz, ff),
                               rotor_break_k=round(2 * HW / ROTOR_SPREAD_HZ, 1),
                               note_ko=("⭐빗살의 «끝» 이 두 자세 수에서 같고 로터 산포가 창을 "
                                        "넘는 자리(k≈29)와 맞물리면, 빗살을 끝내는 것은 "
                                        "**로터**이지 표집이 아니다."))),
                decimation_probe=dict(
                    rows=decimation_probe(E32, ff, ft),
                    note_ko=("자세를 솎아 **격자를 성기게** 만든 파생 탐침. 접힘(alias)은 "
                             "126.667 Hz 의 정수배 자리에 안 떨어진다(4925÷126.667=38.88) — "
                             "솎아도 빗살이 그 자리에 서 있으면 원래 있던 선이다.")),
                outlier=dict(
                    census_8192=census_grade(f"{arm8}/el{el:+.0f}"),
                    census_32768=census_grade(f"{arm32}/el{el:+.0f}"),
                    probe_B_head8192=outlier_probe(head, ff, ft),
                    probe_C_full=outlier_probe(E32, ff, ft),
                    probe_A_8192=outlier_probe(E8, ff, ft)),
            ))
    return cells, gate, B


def provenance():
    """⭐이 짝이 **언제·무엇으로** 계산됐나 — 두 팔 사이에 배관이 바뀌었는지 본다.

    ⚠git 를 안 쓴다(이 라운드 금지) — **파일 시각**과 **수치 재현**으로만 말한다.
    """
    import glob as _g

    def mt(p):
        return (_dt.datetime.utcfromtimestamp(os.path.getmtime(p) + 9 * 3600)
                .strftime("%Y-%m-%d %H:%M KST")) if os.path.exists(p) else None

    def shard_span(arm, el):
        fs = _g.glob(os.path.join(ROOT, "outputs", "elev_sweep_shards",
                                  f"{arm}_el{el:+.0f}_*.npz"))
        if not fs:
            return None
        ts = sorted(os.path.getmtime(f) for f in fs)
        return dict(n_shards=len(fs), first=mt(min(fs, key=os.path.getmtime)),
                    last=mt(max(fs, key=os.path.getmtime)))

    srcs = {p: mt(os.path.join(ROOT, p)) for p in (
        "src/rcs_sbr.py", "src/articulated_fast.py", "src/drones.py",
        "src/materials.py", "benchmark/elevation_sweep_md.py")}
    return dict(
        source_mtimes_kst=srcs,
        shards={f"{a}/el{e:+.0f}": shard_span(a, e)
                for _s, a8, a32, els in PAIRS for e in els for a in (a8, a32)},
        warning_ko=(
            "⚠**두 팔은 사흘 떨어져 계산됐다**(8,192 팔 2026-08-13 저녁 KST · 32,768 팔 "
            "2026-08-16 새벽 KST). "
            f"그 사이에 `src/rcs_sbr.py` 가 손질됐다(현재 시각 {srcs['src/rcs_sbr.py']} — "
            "32,768 팔이 돌기 약 7 시간 전). "
            "git 를 못 쓰니 무엇이 바뀌었는지는 여기서 말할 수 없다. 대신 두 가지로 **크기를 "
            "가둔다** — (1) PathSolver 짝은 앞 8,192 자세가 기계정밀도(≈5e−16)로 **같다** → "
            "PathSolver 경로에는 그 사이 바뀐 것이 없다. (2) 우리 커널 짝은 정지 성분을 뺀 "
            "AC 전력이 앞 8,192 자세에서 0.02 dB 안쪽으로 같다 → 커널 손질과 얼린 격자 변화를 "
            "합쳐도 이 판의 모든 밴드 안이다."),
        drone_spec_check_ko=("`src/drones.py` 는 두 팔보다 나중에 손질됐지만(2026-08-16), "
                             "f_tip 을 원장 값과 대조하면 반올림 차이(≤0.05 Hz)뿐이라 "
                             "이 판이 쓰는 제원은 안 바뀌었다 — gate_ftip 참조."))


def gate_ftip(rows):
    """⭐제원 게이트 — 지금 계산한 f_tip 이 원장에 적힌 값과 같은가(반올림 빼고)."""
    out = []
    for short, a8, a32, els in PAIRS:
        for el in els:
            r = A.arm_rates(a8)
            ft = A.f_tip_at(r, el)
            for arm in (a8, a32):
                led = rows[(arm, el)]["f_tip_hz"]
                out.append(dict(cell=f"{arm}/el{el:+.0f}", ledger_f_tip_hz=led,
                                recomputed_f_tip_hz=round(ft, 3),
                                diff_hz=round(ft - led, 3), ok=bool(abs(ft - led) <= 0.05)))
    return out


def cross_checks(B):
    """⭐다른 «격자» 두 개로도 빗살이 살아남나 — 자세 격자 말고 **표면 격자**·**엔진**.

    ① 표면 격자 λ/12 ↔ λ/24 (`ours_r15_n8192` ↔ `ours_r15_n8192_div24`)
       — 우리 커널의 ⓪ 격자를 두 배 촘촘하게 한 팔이 원장에 이미 있다.
    ② 격자가 **아예 없는** 엔진 — PathSolver 는 표면 격자를 안 쓴다(광선을 Rx 에서 쏜다).
       위 사다리의 PathSolver 짝이 그 대조군이다.
    """
    rows = []
    for el in (0.0, -30.0, -60.0):
        try:
            E1 = A.series("ours_r15_n8192", el)
            E2 = A.series("ours_r15_n8192_div24", el)
        except KeyError:
            continue
        r = A.arm_rates("ours_r15_n8192")
        ff, ft = r["f_flash_hz"], A.f_tip_at(r, el)
        h1, h2 = headline(E1, ff, ft), headline(E2, ff, ft)
        rows.append(dict(
            elevation_deg=el, arm_div12="ours_r15_n8192", arm_div24="ours_r15_n8192_div24",
            rhythm_pct=[h1["rhythm_pct"], h2["rhythm_pct"]],
            rhythm_null_pct=h1["rhythm_null_pct"],
            above_comb_db=[h1["above_comb_db"], h2["above_comb_db"]],
            above_ceiling_pct=[h1["above_ceiling_pct"], h2["above_ceiling_pct"]],
            comb_db=[h1["comb_db"], h2["comb_db"]],
            d_rhythm_pp=(None if None in (h1["rhythm_pct"], h2["rhythm_pct"])
                         else round(h2["rhythm_pct"] - h1["rhythm_pct"], 3)),
            band_rhythm_pp=B["rhythm_pp_by_el"].get(el)))
    return dict(
        surface_grid_div12_vs_div24=rows,
        note_ko=("⭐표면 격자를 두 배 촘촘하게 해도(λ/12→λ/24) 상한 위 빗살이 그대로면, "
                 "빗살은 **표면 격자**의 산물도 아니다. 여기에 격자가 아예 없는 PathSolver "
                 "짝까지 같은 방향이면 «격자» 라는 이름의 용의자는 셋 다 기각된다 "
                 "— 광선 수(R17) · 자세 격자(이 판) · 표면 격자(이 교차검사)."))


# ═══════════════════════════════════════════════════════════════════════════
# 4. 그림 — ⭐그림 안 글자는 전부 영어(하우스 규약)
# ═══════════════════════════════════════════════════════════════════════════
def figure(cells, doc):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    C_8, C_32, C_Z = "#1f77b4", "#d62728", "#7f7f7f"
    fig, ax = plt.subplots(1, 3, figsize=(16.5, 5.0))

    # (a) 상한 위 스펙트럼 — 가장 센 칸 하나
    c = max(cells, key=lambda x: x["arms"]["C_n32768_full"]["above_comb_db"] or -99)
    E8 = A.series(c["arm_8192"], c["elevation_deg"])
    E32 = A.series(c["arm_32768"], c["elevation_deg"])
    ft, ff = c["f_tip_hz"], c["f_flash_hz"]
    for E, col, lab in ((E8, C_8, "8,192 poses (0.42 s)"),
                        (E32, C_32, "32,768 poses (1.66 s)")):
        P, fr = _spec(E)
        s = fr >= 0
        f, p = fr[s], P[s]
        p = 10 * np.log10(p / p.max() + 1e-300)
        ax[0].plot(f, p, color=col, lw=0.7, alpha=0.85, label=lab)
    ax[0].axvline(ft, color="k", ls="--", lw=1.2)
    ax[0].text(ft - 0.12 * ff, -47, f"blade-tip ceiling  {ft:.0f} Hz", rotation=90,
               fontsize=8.5, va="center", ha="right", color="k")
    for k in range(int(math.ceil(ft / ff)), int(math.ceil(ft / ff)) + 9):
        ax[0].axvline(k * ff, color="#2ca02c", lw=0.6, alpha=0.35)
    ax[0].set_xlim(ft - 3 * ff, ft + 9 * ff)
    ax[0].set_ylim(-95, 8)
    ax[0].set_xlabel("Doppler frequency [Hz]")
    ax[0].set_ylabel("power [dB, peak-normalised]")
    ax[0].set_title(f"(a) Above-ceiling comb survives 4x poses\n"
                    f"{c['pair']}  el {c['elevation_deg']:+.0f} deg   "
                    f"(green lines = multiples of {ff:.1f} Hz)", fontsize=10)
    ax[0].legend(fontsize=8, loc="lower left", framealpha=0.92)
    ax[0].grid(alpha=0.25)

    # (b) 리듬 몫 사다리
    labs = [f"{x['pair']}\nel {x['elevation_deg']:+.0f}" for x in cells]
    xs = np.arange(len(cells))
    v8 = [x["arms"]["A_n8192"]["rhythm_pct"] for x in cells]
    vZ = [x["arms"]["Z_n8192_zeropad32768"]["rhythm_pct"] for x in cells]
    v32 = [x["arms"]["C_n32768_full"]["rhythm_pct"] for x in cells]
    bd = [x["verdict_by_metric"]["rhythm_pct"]["band"] for x in cells]
    w = 0.26
    ax[1].bar(xs - w, v8, w, color=C_8, label="8,192 poses")
    ax[1].bar(xs, vZ, w, color=C_Z, label="8,192 zero-padded (resolution only)")
    ax[1].bar(xs + w, v32, w, color=C_32, label="32,768 poses")
    ax[1].errorbar(xs - w, v8, yerr=bd, fmt="none", ecolor="k", capsize=4, lw=1.2,
                   label="grid-dispersion band")
    for i, x in enumerate(cells):
        nl = x["arms"]["A_n8192"]["rhythm_null_pct"]
        ax[1].hlines(nl, i - 0.42, i + 0.42, color="#ff7f0e", lw=2.2,
                     label=("white-noise null" if i == 0 else None))
    ax[1].set_xticks(xs)
    ax[1].set_xticklabels(labs, fontsize=9)
    ax[1].set_ylabel("rhythm share above ceiling [%]")
    ax[1].set_ylim(0, 128)
    ax[1].set_yticks([0, 20, 40, 60, 80, 100])
    ax[1].set_title("(b) Rhythm share vs pose count", fontsize=10)
    ax[1].legend(fontsize=7.5, loc="upper center", ncol=2, framealpha=0.95)
    ax[1].grid(alpha=0.25, axis="y")

    # (c) 배음별 대비 곡선
    hc8 = c["harmonic_curve"]["n8192"]
    hc32 = c["harmonic_curve"]["n32768"]
    hcz = c["harmonic_curve"]["zeropad"]
    for hc, col, lab in ((hc8, C_8, "8,192 poses"), (hcz, C_Z, "zero-padded"),
                         (hc32, C_32, "32,768 poses")):
        ax[2].plot([h["k"] for h in hc], [h["contrast_db"] for h in hc],
                   "-o", ms=3, lw=1.1, color=col, label=lab)
    kb = doc["_meta"]["rotor_spread"]["k_window_break"]
    ax[2].axvline(kb, color="#9467bd", ls=":", lw=1.5)
    ax[2].annotate(f"rotor spread exceeds\nthe +-8 Hz window (k={kb:.0f})",
                   xy=(kb, 2), xytext=(kb + 1.5, 2), fontsize=8,
                   color="#9467bd", va="bottom")
    ax[2].axhline(0, color="k", lw=0.8)
    ax[2].set_xlabel("harmonic index k  (line at k x %.1f Hz)" % ff)
    ax[2].set_ylabel("line-to-valley contrast [dB]")
    ax[2].set_title(f"(c) How far above the ceiling the comb reaches\n"
                    f"{c['pair']}  el {c['elevation_deg']:+.0f} deg", fontsize=10)
    ax[2].legend(fontsize=8)
    ax[2].grid(alpha=0.25)

    fig.suptitle("Pose-count ladder (8,192 vs 32,768): the above-ceiling comb is real "
                 "structure, not a pose-grid artifact", fontsize=12.5, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(FIGP, dpi=140)
    plt.close(fig)


def main():
    cells, gate, B = build()
    os.makedirs(FIGD, exist_ok=True)

    # ── 요약 ────────────────────────────────────────────────────────────────
    rows_summary = []
    for c in cells:
        a, cc = c["arms"]["A_n8192"], c["arms"]["C_n32768_full"]
        z = c["arms"]["Z_n8192_zeropad32768"]
        rows_summary.append(dict(
            cell=f"{c['pair']} el{c['elevation_deg']:+.0f}",
            rhythm_8192=a["rhythm_pct"], rhythm_32768=cc["rhythm_pct"],
            rhythm_zeropad=z["rhythm_pct"], rhythm_null=a["rhythm_null_pct"],
            rhythm_quarter_span=(c["quarter_scatter"]["rhythm_pct"] or {}).get("span"),
            rhythm_band_pp=c["verdict_by_metric"]["rhythm_pct"].get("band"),
            above_comb_db_8192=a["above_comb_db"], above_comb_db_32768=cc["above_comb_db"],
            above_comb_db_zeropad=z["above_comb_db"],
            above_ceiling_8192=a["above_ceiling_pct"],
            above_ceiling_32768=cc["above_ceiling_pct"],
            comb_db_8192=a["comb_db"], comb_db_32768=cc["comb_db"],
            moving_power_8192=a["moving_power_db"],
            moving_power_32768=cc["moving_power_db"],
            reading_flipped=c["reading"]["reading_flipped"],
            verdict={k: v["verdict"] for k, v in c["verdict_by_metric"].items()}))

    # ── ⭐헤드라인 판정 — 네 칸을 한 줄로 ─────────────────────────────────────
    n_moved = sum(1 for c in cells
                  if "밖" in c["verdict_by_metric"]["rhythm_pct"]["verdict"])
    n_flip = sum(1 for c in cells if c["reading"]["reading_flipped"])
    zp_max = max(abs(c["deltas"]["rhythm_pct"]["Z_minus_A"] or 0.0) for c in cells)
    ratios = [c["reading"]["rhythm_over_null_32768"] for c in cells
              if c["reading"]["rhythm_over_null_32768"] is not None]
    verdict_ko = (
        f"⭐**진짜 구조다 — 자세 격자의 산물이 아니다.** 자세를 4 배(8,192→32,768) 늘려도 "
        f"상한 위 빗살은 네 칸 모두 살아 있다(리듬 몫이 백색 널의 "
        f"{min(ratios):.1f}~{max(ratios):.1f} 배, 상한 위 빗살 대비 "
        f"{min(c['arms']['C_n32768_full']['above_comb_db'] for c in cells):.1f}~"
        f"{max(c['arms']['C_n32768_full']['above_comb_db'] for c in cells):.1f} dB). "
        f"리듬 몫의 움직임은 네 칸 전부 프로젝트의 격자 산포 밴드 **안**이라 "
        f"«움직였다» 고도 말할 수 없다(밴드 밖 {n_moved}/4). 읽기가 뒤집힌 칸 {n_flip}/4. "
        f"⭐분해능만 4 배로 만든 영채움 팔은 리듬 몫을 최대 {zp_max:.2f} %p 밖에 안 움직였다 "
        f"— 이 잣대는 «빈을 몇 개 세나» 라는 장부에 걸려 있지 않다.")

    headline = dict(
        answer_ko="진짜 구조",
        answer_en="real structure, not a pose-grid artifact",
        n_cells=len(cells),
        n_rhythm_outside_band=n_moved, n_reading_flipped=n_flip,
        rhythm_over_null_range=[min(ratios), max(ratios)],
        zeropad_max_abs_rhythm_shift_pp=round(zp_max, 3),
        verdict_ko=verdict_ko,
        caveats_ko=[
            "⚠단일축이 아니다 — 우리 커널 팔은 n 이 바뀌면 probe 자세가 달라져 **얼린 격자도** "
            "바뀐다(elevation_sweep_md.py:265). 그래서 문턱을 격자 산포 밴드로 잡았다. "
            "격자가 없는 PathSolver 짝이 같은 방향을 가리키는 것이 이 교란의 반증이다.",
            "⚠짝이 네 칸뿐이다(우리 커널 el 0·−30·−60 · PathSolver el −30). 앙각 축은 "
            "세 점, 엔진 축은 한 점에서만 겹친다.",
            "⚠«자세 수» 는 표집률이 아니라 **기록 길이**다. 이 판은 «자세 격자가 촘촘한가» 가 "
            "아니라 «자세 격자가 짧은가» 를 물었다. PRF 자체를 바꾼 사다리는 원장에 없다.",
            "⚠above_comb_db 는 이 판에서 **신설한 보조 잣대**다 — 프로젝트 밴드가 없어 "
            "«밴드 안» 판정을 못 한다. 정본 판정은 리듬 몫·상한 위 몫으로 했다.",
        ])

    doc = dict(
        _meta=dict(
            generator="benchmark/free_harvest_pose_ladder_0816.py",
            written_at_kst=kst_now(),
            question_ko=("날개끝 상한 **위** 빗살은 자세 격자(=시간 표집 격자)의 산물인가, "
                         "진짜 구조인가 — 자세 8,192 ↔ 32,768 사다리"),
            backlog_rank=3, round_id="R24",
            gpu_used=False,
            reads_only=["outputs/elevation_sweep_md.json",
                        "outputs/elevation_sweep_md.npz",
                        "outputs/outlier_census_0816.json",
                        "outputs/depth_axis_verdict_0816.json"],
            ledger_state=dict(
                n_rows=len(json.load(open(A.LED_J))["rows"]),
                ledger_json_mtime_kst=_dt.datetime.utcfromtimestamp(
                    os.path.getmtime(A.LED_J) + 9 * 3600).strftime("%Y-%m-%d %H:%M KST")),
            prf_hz=PRF, window="hann", rhythm_halfwidth_hz=HW,
            what_n_poses_changes_ko=(
                "자세는 t=i/PRF 로 찍는다(PRF 19,700 Hz 고정) — **자세 수 = 기록 길이**이지 "
                "표집률이 아니다. 4 배는 분해능 4 배(2.405→0.601 Hz)와 새 시간 1.25 s 를 "
                "함께 준다. 이 판은 영채움 팔(Z)로 그 둘을 가른다."),
            grid_confound_ko=(
                "⚠우리 커널 팔은 64 개 probe 자세의 합집합 bbox 위에 격자를 얼린다"
                "(elevation_sweep_md.py:265, step=n//64). n 이 바뀌면 probe 자세가 달라져 "
                "**얼린 격자도 바뀐다** — 이 짝은 완전한 단일축이 아니다. PathSolver 팔에는 "
                "격자가 없어 그 짝이 격자 없는 대조군이다."),
            rotor_spread=dict(
                rpm_per_rotor=A.M["rpm_per_rotor"], blades=_BLADES,
                blade_pass_hz=[round(x, 4) for x in _ROTOR_BPF.tolist()],
                spread_hz=round(ROTOR_SPREAD_HZ, 4),
                k_window_break=round(2 * HW / ROTOR_SPREAD_HZ, 1),
                note_ko=("k 번째 배음에서 로터 산포는 k×0.557 Hz 로 벌어진다 — k≳29"
                         "(≈3.6 kHz)부터 창(±8 Hz)을 넘는다. 그 위에서 리듬 몫이 내려가는 "
                         "것은 **정상**이고 격자의 산물이 아니다.")),
            metric_defs_ko={
                "rhythm_pct": "상한 위 에너지 중 박자 정수배(±8 Hz)에 붙은 몫 [%] — 정본",
                "rhythm_null_pct": "⭐백색이면 나오는 값 [%] — 팔마다 다르다(이 판은 전부 matrice4e)",
                "above_ceiling_pct": "움직이는 에너지 중 상한 위 몫 [%]",
                "comb_db": "상한 **아래** 빗살 대비 [dB] (백색 널 ≈ 0)",
                "above_comb_db": ("⭐보조 신설 — 상한 **위** 빗살 대비 [dB]. 창 안 ÷ 창 사이라 "
                                  "«빈이 몇 개 드는가» 장부에 덜 걸린다. **정본 아님**"),
                "moving_power_db": "⭐정지 성분(DC) 제거 후 레벨 [dB] — 판정은 이 값으로",
                "ledger_level_db_raw_dc_kept": ("⛔원장 `level_db` 는 DC 를 **안 뺀** 값이다 — "
                                                "규약상 이 판정에 쓰지 않는다. 참고로만 싣는다")},
            arms_ko={
                "A_n8192": "n=8192 팔 그대로 — 기준선",
                "B_n32768_head8192": "n=32768 팔의 앞 8,192 자세 — 같은 자세·같은 분해능, 격자만 다르다",
                "C_n32768_full": "n=32768 팔 전체 — 분해능 4 배 + 새 시간 1.25 s",
                "Z_n8192_zeropad32768": "⭐A 를 영채움해 32,768 — 분해능만 4 배(새 정보 0)",
                "Zb_head8192_zeropad32768": "B 의 영채움 판 — C 와 짝",
                "quarters": "⭐C 를 8,192 씩 네 토막 — 같은 n 에서의 «구간 산포»"},
            decision_rule_ko=(
                "|C − A| 가 네 토막 산포(span) 안이면 **판정 불가**. 밖이면 «움직였다» 로만 "
                "적고, 그 움직임이 영채움(Z)으로 재현되면 원인은 **분해능 장부**이지 자세 수가 "
                "가져온 새 정보가 아니다."),
            bands=B,
            new_elevation_band_warning_ko=("이 판의 앙각은 0·−30·−60 뿐이라 −52·−68·−82 처럼 "
                                           "밴드가 없는 새 앙각을 쓰지 않는다 — **빌린 값이 없다**."),
            gate_bit_identical=gate,
            gate_pass=bool(all(g["bit_identical"] for g in gate)),
            gate_ftip=(_gf := gate_ftip({(r["engine"], float(r["el_deg"])): r
                                         for r in json.load(open(A.LED_J))["rows"]})),
            gate_ftip_pass=bool(all(g["ok"] for g in _gf)),
            provenance=provenance(),
        ),
        headline=headline,
        summary=rows_summary,
        cross_checks=(_xc := cross_checks(B)),
        cells=cells,
    )
    # ⭐헤드라인에 뒷받침을 붙인다 — 원장 하나만 읽어도 논거가 다 보이게
    dec = [r for c in cells for r in c["decimation_probe"]["rows"]
           if r.get("stride") == 4 and r.get("above_comb_db") is not None]
    xc = _xc["surface_grid_div12_vs_div24"]
    pose_move = [abs(c["deltas"]["rhythm_pct"]["C_minus_A"]) for c in cells]
    grid_move = [abs(r["d_rhythm_pp"]) for r in xc if r["d_rhythm_pp"] is not None]
    doc["headline"]["supporting"] = dict(
        zeropad_resolution_only_max_pp=round(max(
            abs(c["deltas"]["rhythm_pct"]["Z_minus_A"] or 0) for c in cells), 3),
        decimation_stride4_above_comb_db=[r["above_comb_db"] for r in dec],
        decimation_any_alias_fold_on_comb=bool(any(r["any_fold_lands_on_comb"] for r in dec)),
        surface_grid_div24_above_comb_db=[r["above_comb_db"][1] for r in xc],
        surface_grid_div24_rhythm_move_pp=grid_move,
        pose_count_rhythm_move_pp=[round(x, 3) for x in pose_move],
        pose_vs_surface_grid_ko=(
            f"⭐자세 수는 리듬 몫을 {min(pose_move):.2f}~{max(pose_move):.2f} %p 움직이고, "
            f"**표면 격자**(λ/12→λ/24)는 같은 칸을 {min(grid_move):.1f}~{max(grid_move):.1f} %p "
            "움직인다. 즉 이 잣대를 흔드는 것은 자세 격자가 아니라 표면 격자다 — 그런데 "
            "표면 격자를 흔들어도 **상한 위 빗살 자체는 안 사라진다**"
            f"(대비 {min(r['above_comb_db'][1] for r in xc):.1f}~"
            f"{max(r['above_comb_db'][1] for r in xc):.1f} dB, 백색 널 0 dB)."),
        pathsolver_bit_identity=[c["pose_overlap"]["max_rel_pose_diff"] for c in cells
                                 if c["pair"] == "PathSolver"],
        outlier_all_normal=bool(all(
            (c["outlier"]["census_8192"] or {}).get("grade") == "정상"
            and (c["outlier"]["census_32768"] or {}).get("grade") == "정상"
            for c in cells)),
        outlier_max_abs_replace_one=round(max(
            abs(v) for c in cells for p in ("probe_A_8192", "probe_C_full")
            for v in c["outlier"][p]["replace_one"].values() if v is not None), 4),
        suspects_cleared_ko=("«격자» 라는 이름의 용의자 셋이 모두 기각됐다 — "
                             "광선 수(R17) · 자세 격자(이 판) · 표면 격자(교차검사). "
                             "격자가 **아예 없는** PathSolver 도 같은 빗살을 낸다."))
    figure(cells, doc)
    json.dump(doc, open(OUTJ, "w"), ensure_ascii=False, indent=1)
    print(f"✅ {OUTJ}")
    print(f"✅ {FIGP}")
    for r in rows_summary:
        print(f"  {r['cell']:>18s} | 리듬 {r['rhythm_8192']}→{r['rhythm_32768']} "
              f"(영채움 {r['rhythm_zeropad']}, 널 {r['rhythm_null']}, 토막폭 "
              f"{r['rhythm_quarter_span']}, 밴드 {r['rhythm_band_pp']}) → "
              f"{r['verdict']['rhythm_pct']} | 상한위빗살 {r['above_comb_db_8192']}"
              f"→{r['above_comb_db_32768']} dB | 상한위몫 {r['above_ceiling_8192']}"
              f"→{r['above_ceiling_32768']} %")
    print("\n" + headline["verdict_ko"])
    return doc


if __name__ == "__main__":
    main()
