# -*- coding: utf-8 -*-
"""
build_scaled_maps.py — ⭐**세기가 보이는** 마이크로도플러 맵 (눈금 세 가지)

왜 만드나 (2026-08-15 사용자 지시)
------------------------------------
지금 나가는 맵은 **전부 패널별 최댓값 정규화**다 — 패널마다 자기 최댓값을 0 dB 로 잡는다.
그래서 100 배 약한 판도 똑같이 밝게 보이고, **거리·엔진 사이의 세기 차이가 그림에서 사라진다**.
`md_mapstyle.draw()` 주석이 이미 그렇게 경고하고 있었는데(«ref=None 이면 거리 정보가 그림에서
사라진다») 아무도 안 썼다. 이 스크립트가 나머지 두 눈금을 실제로 굽는다.

세 눈금 (이름은 docs/MAP_SCALING.md 가 정본)
--------------------------------------------
  ① 패널별 최댓값  `draw(mode="peak", ref=None)`   0 dB = **그 패널의** 최댓값
  ② 공통 기준      `draw(mode="peak", ref=스칼라)` 0 dB = **한 판**의 최댓값(전 패널 공유)
  ③ 잡음 기준      `draw(mode="over_noise", ...)`  0 dB = **측정한 잡음 바닥** ⇒ 곧 SNR

무엇을 굽나
-----------
  1 scaled_range_common.png     ② 거리 사다리 15·30·60·120 m — 팔마다 15 m 판이 기준
  2 scaled_azimuth_common.png   ② 방위 0·22.5·45·67.5° — 줄마다 0° 판이 기준
  3 scaled_range_noise.png      ③ 거리 사다리(우리 커널) — 0 dB = 잡음 바닥
  4 scaled_engines_noise.png    ③ 엔진 비교 15 m — 무차원이라 엔진끼리 열린다
  5 scaled_three_scales_same_data.png  ⭐같은 데이터를 세 눈금으로 (자가검사 그림)
  6 scaled_anchor_sensitivity.png      ⚠앵커를 다르게 잡으면 결론이 어떻게 바뀌나

⭐판정 막대 — «판정하는 그 양» 의 귀무분포에서 세운다
------------------------------------------------------
빨강/초록을 가르는 양은 `line_level_over_noise_db` (블레이드 대역에서 **시간평균·잡음차감**한
선 레벨)다. 그러므로 막대도 **그 양** 을 잡음만으로 여러 번 재서 세워야 한다.
`noise_floor()` 가 같이 내는 `only_max_db` 는 «잡음만 있는 맵의 **화소 최댓값**» 이라
**다른 통계량**이다 — 시간평균도 잡음차감도 안 한 값이라 같은 잡음에서도 17 dB 가량 높다.
⛔ 그것을 판정 막대로 쓰면 안 된다(§`corrections` 참조).

  · 귀무분포  : 잡음만 `NULL_TRIALS` 회를 **같은 STFT·같은 대역 마스크**로 통과시켜
                `line_level_over_noise_db` 자체의 분포를 만든다(씨앗 고정, 마스크마다 따로).
  · 막대      : 그 분포의 (1−`NULL_PFA`) 분위수. `NULL_PFA = 1e-3` 은
                `detection_curves.py` 의 Pfa 목표와 **같은 수**라 두 원장이 나란히 선다.
  · 판정      : 막대를 넘느냐를 한 판으로 정하지 않고, 같은 신호에 잡음을 `MC_TRIALS` 회
                다시 태워 **Pd** 를 잰다(Pd≥0.9 탐지 · 0.1<Pd<0.9 애매 · Pd≤0.1 미탐지 —
                `noise_distance_frame.py` 의 판정 어휘와 같다).
  · 검산      : 이 막대로 나오는 R50 을 `detection_curves.json` 의 R50 과 **앵커 차이를
                환산해** 실제로 맞춰 본다(`crosscheck` 절). 말로만 «검산된다» 고 쓰지 않는다.

⚠ 이 스크립트가 지키는 경계
---------------------------
· GPU·솔버 호출 **없음**. 저장된 원장(outputs/elevation_sweep_md.{npz,json})만 읽는다.
· `md_mapstyle` · `rx_noise` · `link_budget` · `detection_curves` 를 **고치지 않고 재사용**한다.
  규약 상수(EIRP·대역·주판 앙각)는 `detection_curves` 에서 그대로 빌려 온다 — 두 원장이
  같은 눈금 위에 서 있어야 R50 = 724 m 같은 헤드라인과 이 그림이 서로를 검산할 수 있다.
· ⚠**엔진 사이 절대 세기 비교 금지**는 ①②에만 걸린다. 우리 커널의 E 는 면적 차원
  (σ = 4π/λ²|E|²)이고 PathSolver 의 계수는 무차원이라 두 수를 나란히 놓을 수 없다.
  ③ 은 **문헌 σ 앵커로 둘 다 절대 RCS 로 환산한 뒤 잡음으로 나눈** 무차원 수라서 열린다.
  대신 «앵커를 어디에 걸었나» 가 결론을 흔든다 — 그래서 그림 6 이 감도를 같이 낸다.
· ⚠**절대 세기는 잠정이다.** 셸 두께·우리 커널 반사율 정정이 진행 중이라(원장
  `_meta.thickness_note_ko`) ③ 의 절대 dB 는 바뀔 수 있다. 그림과 JSON 에 «PROVISIONAL» 을 박는다.

실행
    cd /workspace/sionna && /workspace/.venvs/py312/bin/python benchmark/build_scaled_maps.py
    (--quick 은 시간창을 더 줄여 빠르게 한 바퀴 돈다 — 수치 검사용, 그림 품질용 아님)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                     # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, ListedColormap  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from md_mapstyle import (NOISE_VMIN, VMAX, VMIN, auto_periods,          # noqa: E402
                         draw, flash_spec, line_level_over_noise_db,
                         noise_rms_from)
from rx_noise import (RxSpec, anchor_scale, noise_power_w,              # noqa: E402
                      sigma_kernel_m2, sigma_ref_from_literature)
from link_budget import C0, LinkBudget                                  # noqa: E402
import detection_curves as DC                                           # noqa: E402

# --------------------------------------------------------------------------- #
#  규약 — 남의 파일에서 빌려 오고, 여기서 새로 정하는 것은 표시 관련뿐
# --------------------------------------------------------------------------- #
EIRP_DBM = DC.EIRP_DBM            # 30 dBm 선언값 (detection_curves 와 **같은 수**)
BAND_LO = DC.BAND_LO              # 0.35 — 블레이드 대역 하한 (원장 band_track 정본)
BAND_HI = 1.00                    # f_tip 상한
EL_ANCHOR = DC.EL_MAIN            # −30° — detection_curves 가 앵커를 건 주판
R_ANCHOR = 15.0                   # 앵커를 거는 거리 [m]
ELS_ALL = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]   # 원장의 앙각 격자

#: ⭐**이 그림들의 기준 앵커** — 자세 평균(7 앙각의 |E|² 선형평균)을 σ_ref 에 맞춘다.
#:
#: ⚠ `detection_curves.py` 는 el −30° 한 자세에 건다. 그 선택은 거기서 옳다 — 그 원장은
#:   **엔진 하나 · 자세 하나**씩 거리 사다리만 내므로 보고하는 자세에 거는 것이 보수적이다.
#:   그러나 이 그림은 **여러 자세와 여러 엔진을 한 틀에** 놓는다. 한 자세에 걸면 그 자세가
#:   정의상 전부 같아지고(2026-08-15 실측: el −30 에서 네 팔이 +57/+60/+58 dB 로 붙어 버린다)
#:   차이가 전부 다른 자세로 밀려나 «PathSolver 가 정면에서 +100 dB» 같은 앵커의 그림자가
#:   결과처럼 읽힌다. 문헌 앵커 σ_ref 자체가 **자세 평균**(방위 선형평균 규약)이므로,
#:   자세를 비교하는 그림에서는 자세 평균에 거는 것이 앵커의 원래 뜻과도 맞는다.
#:   ⇒ 기준은 자세 평균, `detection_curves` 의 선택은 **감도 변형**으로 함께 낸다.
ANCHOR_BASE = "all_el_mean"

#: ③ 잡음 기준 맵의 색역 [dB above noise]. 하한은 md_mapstyle 규약(NOISE_VMIN=−6),
#: 상한은 40 대신 **50** — 거리 사다리 하나가 이미 36 dB(1/R⁴, 15→120 m)를 먹기 때문이다.
#: 선례: benchmark/build_md_noise_range_fig.py 도 같은 이유로 −6..50 을 쓴다.
NOISE_VMAX_FIG = 50.0
DEAD_TO_DB = 0.0                  # 이 아래(=잡음 바닥 아래)는 색을 죽인다

#: 그림에 실제로 그리는 시간창 [ms]. 계산·잣대는 **전 구간(416 ms)** 에서 하고 표시만 자른다.
#: 자르는 이유는 둘 — (a) 플래시(7.9 ms 주기)가 눈에 보이고 (b) gouraud 폴리곤이 1/7 로 준다.
SHOW_T0_MS, SHOW_MS = 20.0, 60.0

#: ⭐판정 막대를 세우는 귀무분포 — «잡음만» 시행 수. 마스크마다 따로 분포를 만든다.
#: Pfa 1e-3 분위수를 쓰려면 꼬리에 표본이 남아야 한다(20,000 회면 상위 20 개).
NULL_TRIALS = 20000
NULL_PFA = 1e-3                   # detection_curves.PFA_TARGET 과 같은 수
#: 판정용 Pd 몬테카를로 — 같은 신호에 잡음만 다시 태운다.
MC_TRIALS = 400
#: R50(Pd=0.5) 를 실제로 재는 거리 격자 [m] — detection_curves 의 R50 과 맞대려고 잰다.
R50_GRID_M = [120.0, 150.0, 180.0, 210.0, 235.0, 260.0, 290.0, 320.0, 360.0, 420.0]
#: 판정 어휘 — noise_distance_frame.verdict() 와 같은 문턱을 쓴다.
PD_DETECT, PD_MISS = 0.9, 0.1
VERDICT_COLOUR = {"detected": "#1b5e20", "marginal": "#8d6e63", "not detected": "#b71c1c"}

LEDGER_JSON = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LEDGER_NPZ = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
FIGDIR = os.path.join(ROOT, "outputs", "figures", "scaled_maps")
OUT_JSON = os.path.join(ROOT, "outputs", "scaled_maps.json")

PROVISIONAL = ("PROVISIONAL absolute level - the shell-thickness / kernel-reflectivity "
               "correction is still in flight, so every dB in the noise-referenced panels "
               "may move as a block. The comparisons (which panel is darker) are what "
               "this figure claims.")

FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1.5, "ytick.labelsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 160, "savefig.dpi": 160,
    "font.family": "DejaVu Sans",
})

#: 감도 그림 색 — 검증된 기성 팔레트의 1·2·3 슬롯(all-pairs 통과). node 검증기가 이
#: 환경에 없으므로 자작 색을 만들지 않는다(rx_noise._demo_figure 와 같은 원칙).
PAL = ["#2a78d6", "#eb6834", "#1baf7a"]
MARK = ["o", "s", "^"]


# --------------------------------------------------------------------------- #
#  0. 원장 읽기
# --------------------------------------------------------------------------- #
def el_key(el: float) -> str:
    return "el+0" if float(el) == 0.0 else f"el{int(el):d}"


class Ledger:
    """저장된 원장 한 벌. **읽기 전용**."""

    def __init__(self):
        doc = json.load(open(LEDGER_JSON))
        self.meta = doc["_meta"]
        self.rows = doc["rows"]
        self.z = np.load(LEDGER_NPZ)
        self.fc = float(self.meta["fc_hz"])
        self.prf = float(self.meta["prf_hz"])
        self.f_flash = float(self.meta["f_flash_hz"])
        self.drone = str(self.meta["drone"])
        self.periods = auto_periods(self.prf, self.f_flash)
        self._stft: dict[str, tuple] = {}

    def row(self, engine: str, el: float) -> dict | None:
        r = [x for x in self.rows
             if x.get("engine") == engine and float(x.get("el_deg")) == float(el)]
        return r[-1] if r else None                    # 재실행 시 마지막 행이 정본

    def series(self, engine: str, el: float):
        """(E, row) — 없으면 (None, None). 없는 팔은 그림에 «원장에 없음» 으로 남긴다."""
        row = self.row(engine, el)
        key = f"{engine}/{el_key(el)}"
        if row is None or key not in self.z.files:
            return None, None
        E = np.asarray(self.z[key], complex)
        if E.size != int(row["n_poses"]):
            raise ValueError(f"{key}: npz {E.size} ≠ 원장 n_poses {row['n_poses']}")
        return E, row

    def stft(self, x, cache_key: str | None = None):
        """규약 STFT(flash_spec). 같은 열을 두 번 안 푼다."""
        if cache_key is not None and cache_key in self._stft:
            return self._stft[cache_key]
        out = flash_spec(x, self.prf, self.f_flash, self.periods)
        if cache_key is not None:
            self._stft[cache_key] = out
        return out


# --------------------------------------------------------------------------- #
#  1. 잡음 눈금 — 단위분산으로 옮겨서 다룬다
# --------------------------------------------------------------------------- #
def rx_unit_noise(E, R_m: float, c_anchor: float, fc: float, prf: float,
                  spec: RxSpec, rng: np.random.Generator | None):
    """⭐**앵커를 고정한** 수신 열 — 잡음이 단위분산이 되도록 눈금을 옮긴다.

        σ(t) = (4π/λ²)|E|²·c_anchor        (c_anchor 는 **밖에서** 준다)
        P(t) = radar_eq(σ(t), R, R)        (1/R⁴ 은 여기서만)
        x(t) = √(P/N)·e^{j∠E} + n,  n ~ CN(0,1)

    ⚠ `rx_noise.rx_series` 를 그대로 못 쓰는 이유: 그 함수는 **호출할 때마다 자기 E 로
      다시 앵커를 건다**(anchor_scale). 거리마다 부르면 거리 차이가 눈금에서 지워진다.
      우리 커널은 |E| 가 거리에 거의 불변이라(자가검사 SC-A) 결과가 같지만, 거리를 품는
      팔에서는 조용히 틀린다. 그래서 앵커를 **인자로** 받는 이 함수를 따로 둔다.
    ⚠ 이중계상 아님: 커널의 구면파 조명은 위상 곡률만 넣고 1/r 확산은 안 넣는다
      (rcs_sbr «이 배선이 하는 것과 안 하는 것» · rx_noise 서두).
    """
    E = np.asarray(E, complex)
    lam = C0 / float(fc)
    sig = sigma_kernel_m2(E, fc) * float(c_anchor)
    lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                    noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)
    P = np.asarray(lb.echo_power_w(lam, sig, float(R_m), float(R_m)), float)
    N = noise_power_w(spec, prf)
    amp = np.sqrt(P / N)                                   # 표본당 전압 SNR
    ph = np.where(np.abs(E) > 0, E / np.maximum(np.abs(E), 1e-300), 1.0 + 0j)
    x = amp * ph
    if rng is not None:
        x = x + rng.normal(scale=np.sqrt(0.5), size=(E.size, 2)).view(complex).ravel()
    return x, dict(snr_sample_db=float(10 * np.log10(np.mean(amp ** 2))),
                   sigma_mean_dbsm=float(10 * np.log10(sig.mean())),
                   N_w=float(N), R_m=float(R_m))


def noise_floor(led: Ledger, n: int, seed: int):
    """단위분산 복소잡음을 **같은 STFT** 로 통과시켜 잡음 바닥 rms 를 잰다(예측식 아님).

    같이 내는 `only_max_db` 는 «잡음만 있는 맵의 **화소** 최댓값» 이다 — 지수분포 빈 N 개의
    최대는 rms 대비 10log10(ln N) ≈ 11 dB. 색역·그림 설명에 쓰는 참고값이고
    ⛔**판정 막대가 아니다**. 판정량(`line_level_over_noise_db`)은 시간평균·잡음차감을 거쳐
    같은 잡음에서도 17 dB 가량 낮게 나온다 — 막대는 `bar_from_null()` 이 세운다.
    """
    rng = np.random.default_rng(seed)
    n0 = rng.normal(scale=np.sqrt(0.5), size=(n, 2)).view(complex).ravel()
    f, t, S, nper = led.stft(n0, cache_key=f"noise{n}_{seed}")
    rms = noise_rms_from(S)
    return dict(rms=float(rms), f=f, t=t, S=S, nper=int(nper),
                only_max_db=float(20 * np.log10(S.max() / rms)),
                only_max_theory_db=float(10 * np.log10(np.log(S.size))))


# --------------------------------------------------------------------------- #
#  1-b. ⭐판정 막대 — **판정하는 그 양** 의 귀무분포
# --------------------------------------------------------------------------- #
def _stat_from_pm(Pm, mask, n2: float, floor_db: float = -60.0) -> float:
    """`line_level_over_noise_db` 와 **비트동일**한 계산을, 미리 낸 시간평균 전력에서.

    md_mapstyle 의 함수를 그대로 부르면 시행마다 S(560×4062) 를 들고 있어야 한다.
    시간평균 `Pm = ⟨S²⟩_t` 만 남기면 560 개 수로 줄고, 이후 어떤 마스크로도 다시 잴 수 있다.
    (자가검사 SC8-a 가 두 경로가 같은 수를 내는지 확인한다.)"""
    v = np.asarray(Pm, float)
    v = v[np.asarray(mask, bool)] if mask is not None else v
    p = float(v.max()) - float(n2)
    return float(floor_db) if p <= 0 else float(10.0 * np.log10(p / float(n2)))


def _null_worker(a):
    """잡음만 한 묶음 — 시간평균 전력 Pm 과 그 판의 rms 를 돌려준다."""
    seed, i0, i1, n, prf, f_flash, periods = a
    pm, rm = [], []
    for i in range(i0, i1):
        rng = np.random.default_rng([int(seed), int(i)])
        x = rng.normal(scale=np.sqrt(0.5), size=(int(n), 2)).view(complex).ravel()
        _, _, S, _ = flash_spec(x, prf, f_flash, periods)
        P = np.asarray(S, float) ** 2
        pm.append(P.mean(axis=1))
        rm.append(float(np.sqrt(P.mean())))
    return np.asarray(pm, float), np.asarray(rm, float)


def _signal_worker(a):
    """같은 신호에 잡음만 다시 태운 묶음 — 판정량 값들을 돌려준다."""
    x0, seed, i0, i1, prf, f_flash, periods, mask, n2 = a
    x0 = np.asarray(x0, complex)
    out = []
    for i in range(i0, i1):
        rng = np.random.default_rng([int(seed), int(i)])
        x = x0 + rng.normal(scale=np.sqrt(0.5), size=(x0.size, 2)).view(complex).ravel()
        _, _, S, _ = flash_spec(x, prf, f_flash, periods)
        out.append(_stat_from_pm((np.asarray(S, float) ** 2).mean(axis=1), mask, n2))
    return np.asarray(out, float)


def _chunks(n_trial: int, workers: int):
    step = max(1, int(math.ceil(n_trial / max(1, workers))))
    return [(i, min(n_trial, i + step)) for i in range(0, n_trial, step)]


def null_pm(led: Ledger, n: int, seed: int, n_trial: int, workers: int):
    """⭐잡음만 `n_trial` 회를 같은 STFT 로 통과시킨 **시간평균 전력** 다발.

    돌려주는 `Pm` 은 (시행 × 주파수빈) 이라, 대역 마스크가 달라도 다시 돌 필요가 없다.
    씨앗은 시행 번호마다 `default_rng([seed, i])` 라 **워커 수와 무관하게 재현된다**."""
    t0 = time.time()
    tasks = [(seed, i0, i1, n, led.prf, led.f_flash, led.periods)
             for i0, i1 in _chunks(n_trial, workers)]
    if workers <= 1:
        res = [_null_worker(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            res = list(ex.map(_null_worker, tasks))
    Pm = np.concatenate([r[0] for r in res], axis=0)
    rms = np.concatenate([r[1] for r in res], axis=0)
    print(f"  귀무분포 {n_trial} 회 · {time.time()-t0:.0f} s "
          f"(rms {rms.mean():.5g} ± {rms.std():.2g})", flush=True)
    return Pm, rms


def bar_from_null(Pm, mask, noise_rms: float, pfa: float = NULL_PFA) -> dict:
    """⭐마스크 하나에 대한 판정 막대 — 판정량 자체의 귀무분포 분위수.

    ⚠ 마스크가 넓을수록(빈이 많을수록) 최댓값 통계라 막대가 **올라간다**. 그래서 마스크마다
      따로 세운다 — el 이 다르면 f_tip 이 달라 블레이드 대역의 빈 수가 달라진다."""
    n2 = float(noise_rms) ** 2
    d = np.array([_stat_from_pm(p, mask, n2) for p in np.asarray(Pm, float)], float)
    q = np.percentile(d, [50, 90, 99, 100.0 * (1.0 - pfa)])
    return dict(bar_db=float(q[3]), pfa=float(pfa),
                p50_db=float(q[0]), p90_db=float(q[1]), p99_db=float(q[2]),
                max_db=float(d.max()), mean_db=float(d.mean()), std_db=float(d.std()),
                n_bins=int(np.asarray(mask, bool).sum()), n_trial=int(d.size),
                statistic="md_mapstyle.line_level_over_noise_db (time-averaged, "
                          "noise-subtracted, max over the masked bins)")


def pd_at_bar(x_clean, led: Ledger, mask, noise_rms: float, bar_db: float,
              seed: int, n_trial: int, workers: int) -> dict:
    """같은 신호에 잡음을 `n_trial` 회 다시 태워 **Pd** 를 잰다(막대는 위에서 세운 것)."""
    n2 = float(noise_rms) ** 2
    tasks = [(np.asarray(x_clean, complex), seed, i0, i1, led.prf, led.f_flash,
              led.periods, np.asarray(mask, bool), n2)
             for i0, i1 in _chunks(n_trial, workers)]
    if workers <= 1:
        vals = np.concatenate([_signal_worker(t) for t in tasks])
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            vals = np.concatenate(list(ex.map(_signal_worker, tasks)))
    return dict(pd=float((vals > float(bar_db)).mean()),
                stat_mean_db=float(vals.mean()), stat_std_db=float(vals.std()),
                n_trial=int(vals.size))


def verdict_of(pd: float) -> str:
    return ("detected" if pd >= PD_DETECT
            else ("not detected" if pd <= PD_MISS else "marginal"))


def band_masks(f, f_tip: float, f_flash: float, df_hz: float):
    """블레이드 대역 · 동체(0 도플러) 마스크. 대역 하한은 동체 주엽이 못 새게 3 빈 띄운다."""
    lo = max(BAND_LO * float(f_tip), 3.0 * float(df_hz))
    blade = (np.abs(f) >= lo) & (np.abs(f) <= BAND_HI * float(f_tip))
    body = np.abs(f) <= 0.5 * float(f_flash)
    return blade, body, lo


def clean_line_db(S, noise_rms: float, mask) -> float:
    """잡음을 **안 넣은** 맵의 선 레벨 [dB, 잡음 rms 위].

    `line_level_over_noise_db` 는 잡음 몫을 빼는데(잡음 있는 맵에서 옳다), 잡음이 없는
    맵에서는 뺄 것이 없어 약한 팔에서 음수 로그로 무너진다. 감도 표는 **앵커를 바꾸면
    정확히 그만큼 평행이동한다** 는 성질을 써야 하므로 뺄셈 없는 이 판을 쓴다.
    """
    P = np.asarray(S, float) ** 2
    Pm = P.mean(axis=1)[np.asarray(mask, bool)]
    if Pm.size == 0 or Pm.max() <= 0:
        return float("nan")
    return float(10.0 * np.log10(Pm.max() / float(noise_rms) ** 2))


# --------------------------------------------------------------------------- #
#  2. 표시 도우미
# --------------------------------------------------------------------------- #
def crop(f, S, f_tip: float, t=None, quick: bool = False):
    """그리기 전에 (a) 도플러축을 ±2.05·f_tip 로, (b) 시간축을 표시창으로 자른다.

    ⚠ 잣대는 자르기 **전** 전 구간에서 잰다 — 자르는 것은 표시뿐이다."""
    fm = np.abs(f) <= 2.05 * max(float(f_tip), 1.0)
    if t is None:
        return f[fm], S[fm]
    ms = np.asarray(t, float) * 1e3
    span = (SHOW_MS * 0.35) if quick else SHOW_MS
    tm = (ms >= SHOW_T0_MS) & (ms <= SHOW_T0_MS + span)
    if tm.sum() < 8:
        tm = np.ones_like(ms, bool)
    return f[fm], S[np.ix_(fm, tm)], t[tm]


def dead_cmap(vmin: float, vmax: float, dead_to: float = DEAD_TO_DB):
    """잡음 바닥 **아래**를 죽은 색으로 — 그게 이 그림의 요점이다.

    vmin..dead_to 는 거의 검정→어두운 회색, dead_to..vmax 는 규약색(jet) 그대로.
    vmin 아래로 잘린 값은 set_under 로 가장 어두운 색을 받는다."""
    n = 768
    frac = float(np.clip((dead_to - vmin) / (vmax - vmin), 0.0, 1.0))
    n_dead = max(1, int(round(n * frac)))
    dead = LinearSegmentedColormap.from_list(
        "dead", ["#0b0b10", "#43434e"])(np.linspace(0, 1, n_dead))
    live = plt.get_cmap("jet")(np.linspace(0, 1, n - n_dead))
    cm = ListedColormap(np.vstack([dead, live]), name="jet_dead_below_noise")
    cm.set_under("#0b0b10")
    return cm


def panel_noise(ax, led: Ledger, t, f, S, f_tip: float, nrms: float, quick=False):
    """③ 잡음 기준 한 패널. 규약 draw() 를 그대로 쓰고 색만 «죽은 바닥» 판으로 바꾼다."""
    fc_, Sc, tc = crop(f, S, f_tip, t, quick)
    m = draw(ax, tc, fc_, Sc, f_tip, mode="over_noise", noise_rms=nrms,
             vmin=NOISE_VMIN, vmax=NOISE_VMAX_FIG)
    m.set_cmap(dead_cmap(NOISE_VMIN, NOISE_VMAX_FIG))
    return m


def panel_peak(ax, led: Ledger, t, f, S, f_tip: float, ref=None, quick=False,
               vmax=None):
    """①/② 최댓값 눈금 한 패널. ref=None 이면 ①(패널별), 스칼라면 ②(공통).

    vmax : ⭐공통 기준에서 **기준 판보다 밝은 판**이 있으면(방위 스윕이 그렇다) 위쪽이
      잘려 대비가 죽는다. 그럴 때 색역을 통째로 위로 민다 — 폭은 규약 40 dB 그대로.
    """
    fc_, Sc, tc = crop(f, S, f_tip, t, quick)
    hi = None if vmax is None else float(vmax)
    lo = None if hi is None else hi - (VMAX - VMIN)
    return draw(ax, tc, fc_, Sc, f_tip, mode="peak", ref=ref, vmin=lo, vmax=hi)


def shift_vmax(peaks_db) -> float | None:
    """공통 기준 그림의 색역 상한 — 기준보다 밝은 판이 없으면 규약값(None=0 dB)."""
    v = [p for p in peaks_db if np.isfinite(p)]
    return float(np.ceil(max(v))) if v and max(v) > 0.05 else None


def tidy(ax, first_col: bool, last_row: bool, ylab="Doppler [Hz]"):
    if first_col:
        ax.set_ylabel(ylab)
    else:
        plt.setp(ax.get_yticklabels(), visible=False)
    if last_row:
        ax.set_xlabel("Slow time [ms]")
    else:
        plt.setp(ax.get_xticklabels(), visible=False)


def footer(fig, text, y=0.012, size=None):
    """그림 밖 각주. ⚠**반드시 접는다** — 한 줄이 길면 `bbox_inches="tight"` 가 그림 폭을
    각주에 맞춰 늘려서 패널이 왼쪽에 몰리고 오른쪽이 하얗게 남는다(2026-08-10 f12 에서
    4652 px 로 벌어진 것과 같은 사고). 접는 폭은 그림 폭에 맞춰 계산한다."""
    import textwrap
    w = max(60, int(fig.get_figwidth() * 13.5))
    body = "\n".join(textwrap.fill(p, w) for p in str(text).split("\n"))
    fig.text(0.055, y, body, fontsize=(size or FS - 2.0), color="0.30", va="bottom")


def save(fig, name: str) -> str:
    os.makedirs(FIGDIR, exist_ok=True)
    p = os.path.join(FIGDIR, f"{name}.png")
    fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✅ {os.path.relpath(p, ROOT)}", flush=True)
    return os.path.relpath(p, ROOT)


# --------------------------------------------------------------------------- #
#  3. 팔 정의
# --------------------------------------------------------------------------- #
def key_ours(R): return f"ours_r{R:g}_n8192"
def key_sionna_off(R): return f"sionna_p4000000000_r{R:g}_n8192_d1"


ENG_OURS = "ours_r15_n8192"
ENG_OFF = "sionna_p4000000000_r15_n8192_d1"
ENG_REFR = "sionna_p4000000000_onlyrefr_r15_n8192"
ENG_DIFFR = "sionna_p4000000000_onlydiffr_r15_n8192"

ENGINE_LABEL = {
    ENG_OURS: "Ours (SBR+PO)",
    ENG_OFF: "PathSolver, everything off",
    ENG_REFR: "PathSolver, refraction only",
    ENG_DIFFR: "PathSolver, diffraction on  [reference]",
}
ENGINE_NOTE = {
    ENG_OURS: "spherical illumination at 15 m",
    ENG_OFF: "R0 D0 E0, depth 1, diffuse on",
    ENG_REFR: "R1 D0 E0, depth 1",
    ENG_DIFFR: "D1 - outside the standard frame, shown for reference only",
}
RANGES = [15.0, 30.0, 60.0, 120.0]
AZIMUTHS = [0.0, 22.5, 45.0, 67.5]


def key_ours_az(az: float) -> str:
    return "ours_r15_n8192" if az == 0 else f"ours_r15_n8192_az{az:g}"


# --------------------------------------------------------------------------- #
#  4. 그림 1 — ② 공통 기준 거리 사다리
# --------------------------------------------------------------------------- #
def fig_range_common(led: Ledger, spec: RxSpec, c_ours: float, el: float, quick: bool):
    """거리 15·30·60·120 m 를 **한 눈금**으로. 팔마다 그 팔의 15 m 판이 기준(0 dB)."""
    lam = C0 / led.fc
    rows = [
        dict(id="ours_raw", label="Ours (SBR+PO) - kernel field exactly as stored",
             key=key_ours, scale=None,
             why="the kernel carries sigma only (no 1/r spreading), so range CANNOT dim it"),
        dict(id="ours_radar", label="Ours (SBR+PO) x radar equation (literature sigma anchor, 1/R^4)",
             key=key_ours, scale="radar",
             why="same shapes, level supplied by the radar equation: -40log10(R/15) dB"),
        dict(id="sionna_off", label="PathSolver, everything off (R0 D0 E0, depth 1)",
             key=key_sionna_off, scale=None,
             why="RT path coefficients already carry spreading over the unfolded path"),
    ]
    fig = plt.figure(figsize=(13.2, 9.6))
    gs = fig.add_gridspec(len(rows), len(RANGES) + 1,
                          width_ratios=[1] * len(RANGES) + [0.035],
                          left=0.055, right=0.925, top=0.875, bottom=0.125,
                          wspace=0.10, hspace=0.55)
    out, m = [], None
    for r, spc in enumerate(rows):
        Ss, refs = {}, None
        for R in RANGES:
            E, row = led.series(spc["key"](R), el)
            if E is None:
                Ss[R] = None
                continue
            x = E
            if spc["scale"] == "radar":
                sig = sigma_kernel_m2(E, led.fc) * c_ours
                lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                                noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)
                x = np.sqrt(np.asarray(lb.echo_power_w(lam, sig, R, R), float)) * \
                    np.where(np.abs(E) > 0, E / np.maximum(np.abs(E), 1e-300), 1.0 + 0j)
            f, t, S, nper = led.stft(x, cache_key=f"{spc['id']}|{spc['key'](R)}|{el}")
            Ss[R] = dict(f=f, t=t, S=S, ftip=float(row["f_tip_hz"]),
                         level_db=float(row["level_db"]))
        first = next((v for v in Ss.values() if v is not None), None)
        refs = None if first is None else float(first["S"].max())
        for c, R in enumerate(RANGES):
            ax = fig.add_subplot(gs[r, c])
            v = Ss[R]
            if v is None:
                ax.text(0.5, 0.5, "not in the ledger", ha="center", va="center",
                        fontsize=FS, color="0.45", transform=ax.transAxes)
                ax.set_xticks([]); ax.set_yticks([])
                continue
            m = panel_peak(ax, led, v["t"], v["f"], v["S"], v["ftip"], ref=refs, quick=quick)
            d = float(20 * np.log10(v["S"].max() / refs))
            dl = float(v["level_db"] - Ss[RANGES[0]]["level_db"]) if Ss[RANGES[0]] else float("nan")
            ax.set_title(f"R = {R:g} m\npeak {d:+.1f} dB vs ref   |   mean {dl:+.1f} dB",
                         fontsize=FS - 0.5)
            tidy(ax, c == 0, r == len(rows) - 1)
            out.append(dict(figure="scaled_range_common", row=spc["id"], el_deg=el,
                            range_m=R, peak_minus_ref_db=round(d, 3),
                            mean_level_minus_ref_db=round(dl, 3),
                            ref_is=f"{spc['id']} @ R={RANGES[0]:g} m peak"))
        # ⚠ 줄 머리글은 **새 축을 만들지 않고** 그리드 좌표만 읽어서 얹는다
        #   (같은 gs 칸으로 add_subplot 을 다시 부르면 이미 그린 패널이 되돌아온다).
        fig.text(0.055, gs[r, 0].get_position(fig).y1 + 0.052,
                 f"{spc['label']}   —   {spc['why']}", fontsize=FS + 0.5,
                 color="#222222")
    cb = fig.colorbar(m, cax=fig.add_subplot(gs[:, len(RANGES)]))
    cb.set_label("dB below the reference panel (each row: its own 15 m map)", fontsize=FS - 0.5)
    fig.suptitle(
        f"Common scale, one reference per row - {led.drone}, el {el:+.0f} deg, "
        f"{led.fc/1e9:.1f} GHz, R ladder\n"
        "0 dB is the 15 m panel of that row, NOT each panel's own peak - "
        "so the panels are allowed to go dark",
        fontsize=FS + 2.0, y=0.975)
    footer(fig, "Row 1 stays flat on purpose: our kernel's stored field is an RCS-like "
                "quantity, so distance is simply not in it - that is what row 2 adds. "
                "Row 3 dims by 20log10(R/15), i.e. the RT coefficient spreads as 1/(path "
                "length), not as the radar equation's 1/R^2 in amplitude.\n"
                f"Displayed window {SHOW_T0_MS:.0f}-{SHOW_T0_MS+SHOW_MS:.0f} ms of a "
                f"{led.z[key_ours(15)+'/'+el_key(el)].size/led.prf*1e3:.0f} ms record; "
                "every number is measured on the full record.")
    return save(fig, "scaled_range_common"), out


# --------------------------------------------------------------------------- #
#  5. 그림 2 — ② 공통 기준 방위 스윕
# --------------------------------------------------------------------------- #
def fig_azimuth_common(led: Ledger, els, quick: bool):
    fig = plt.figure(figsize=(13.2, 6.9))
    gs = fig.add_gridspec(len(els), len(AZIMUTHS) + 1,
                          width_ratios=[1] * len(AZIMUTHS) + [0.035],
                          left=0.062, right=0.925, top=0.855, bottom=0.185,
                          wspace=0.10, hspace=0.34)
    grid, refs = {}, {}
    for el in els:                       # ① 먼저 다 재고 ② 색역을 정한 뒤 ③ 그린다
        for az in AZIMUTHS:
            E, row = led.series(key_ours_az(az), el)
            if E is None:
                grid[(el, az)] = None
                continue
            f, t, S, nper = led.stft(E, cache_key=f"az|{key_ours_az(az)}|{el}")
            grid[(el, az)] = dict(f=f, t=t, S=S, ftip=float(row["f_tip_hz"]),
                                  level_db=float(row["level_db"]))
        b = grid[(el, 0.0)]
        refs[el] = None if b is None else float(b["S"].max())
    peaks = [20 * np.log10(v["S"].max() / refs[el])
             for (el, az), v in grid.items() if v is not None and refs.get(el)]
    vtop = shift_vmax(peaks)
    out, m = [], None
    for r, el in enumerate(els):
        base, ref = grid[(el, 0.0)], refs[el]
        for c, az in enumerate(AZIMUTHS):
            ax = fig.add_subplot(gs[r, c])
            v = grid[(el, az)]
            if v is None or ref is None:
                ax.text(0.5, 0.5, "not in the ledger", ha="center", va="center",
                        fontsize=FS, color="0.45", transform=ax.transAxes)
                ax.set_xticks([]); ax.set_yticks([])
                continue
            m = panel_peak(ax, led, v["t"], v["f"], v["S"], v["ftip"], ref=ref,
                           quick=quick, vmax=vtop)
            d = float(20 * np.log10(v["S"].max() / ref))
            dl = float(v["level_db"] - base["level_db"])
            ax.set_title(f"az {az:g} deg\npeak {d:+.1f} dB vs ref  |  mean {dl:+.1f} dB",
                         fontsize=FS - 0.5)
            tidy(ax, c == 0, r == len(els) - 1,
                 ylab=f"el {el:+.0f} deg\nDoppler [Hz]")
            out.append(dict(figure="scaled_azimuth_common", el_deg=el, az_deg=az,
                            peak_minus_ref_db=round(d, 3),
                            mean_level_minus_ref_db=round(dl, 3),
                            ref_is=f"ours az 0 deg, el {el:+.0f} deg peak"))
    cb = fig.colorbar(m, cax=fig.add_subplot(gs[:, len(AZIMUTHS)]))
    cb.set_label("dB relative to the az 0 deg panel of the same row", fontsize=FS - 0.5)
    fig.suptitle(f"Common scale, one reference per row - {led.drone}, ours (SBR+PO), "
                 f"R = 15 m, azimuth sweep\n"
                 "0 dB is the az 0 deg panel of that row",
                 fontsize=FS + 2.0, y=0.975)
    footer(fig, "The reference is stated on the colour bar because a common scale is only "
                "readable if the reader knows what 0 dB is. Two numbers per panel: the peak "
                "(what the colour shows) and the mean level from the ledger (what the "
                "detector integrates) - they are not the same statistic and can disagree.\n"
                + (f"Here the reference is not the brightest panel, so the colour window is "
                   f"shifted up to +{vtop:.0f} dB (width kept at the house 40 dB) - without "
                   f"that, every off-axis panel would clip and the sweep would look flat again."
                   if vtop else "Every panel is at or below the reference, so the colour "
                                "window is the house default 0 to -40 dB."))
    return save(fig, "scaled_azimuth_common"), out


# --------------------------------------------------------------------------- #
#  6. 그림 3 — ③ 잡음 기준 거리 사다리 (우리 커널)
# --------------------------------------------------------------------------- #
def fig_range_noise(led: Ledger, spec: RxSpec, c_ours: float, els, nf: dict,
                    bars: dict, seed: int, quick: bool, workers: int):
    fig = plt.figure(figsize=(13.2, 7.9))
    gs = fig.add_gridspec(len(els), len(RANGES) + 1,
                          width_ratios=[1] * len(RANGES) + [0.035],
                          left=0.062, right=0.925, top=0.845, bottom=0.235,
                          wspace=0.10, hspace=0.44)
    out, m = [], None
    for r, el in enumerate(els):
        for c, R in enumerate(RANGES):
            ax = fig.add_subplot(gs[r, c])
            E, row = led.series(key_ours(R), el)
            if E is None:
                ax.text(0.5, 0.5, "not in the ledger", ha="center", va="center",
                        fontsize=FS, color="0.45", transform=ax.transAxes)
                ax.set_xticks([]); ax.set_yticks([])
                continue
            rng = np.random.default_rng(seed + int(R) * 131 + int(el))
            x, info = rx_unit_noise(E, R, c_ours, led.fc, led.prf, spec, rng)
            f, t, S, nper = led.stft(x, cache_key=f"noisy|{key_ours(R)}|{el}|{seed}")
            ftip = float(row["f_tip_hz"])
            blade, body, lo = band_masks(f, ftip, led.f_flash, led.prf / nper)
            bl = line_level_over_noise_db(S, nf["rms"], blade)
            bd = line_level_over_noise_db(S, nf["rms"], body)
            m = panel_noise(ax, led, t, f, S, ftip, nf["rms"], quick)
            # ⭐판정 — 한 판이 막대를 넘었나가 아니라, 같은 신호에 잡음을 다시 태운 Pd
            bar = bars[("blade", el)]
            x0, _ = rx_unit_noise(E, R, c_ours, led.fc, led.prf, spec, None)
            mc = pd_at_bar(x0, led, blade, nf["rms"], bar["bar_db"],
                           seed + 5000 + int(R) * 13 + int(el), MC_TRIALS, workers)
            vd = verdict_of(mc["pd"])
            # ⚠제목은 **패널 폭 안에** 들어가야 한다 — 한 줄이 길면 옆 패널 제목과 겹친다.
            #   세 줄로 쪼개고 줄마다 30 자 안쪽으로 유지한다(2026-08-15 겹침 사고).
            ax.set_title(f"R = {R:g} m   ·   Pd {mc['pd']:.2f}  {vd}\n"
                         f"blade line {bl:+.1f} dB   (bar {bar['bar_db']:+.1f})\n"
                         f"body {bd:+.1f} dB · SNR/sample {info['snr_sample_db']:+.1f}",
                         fontsize=FS - 1.5, color=VERDICT_COLOUR[vd])
            tidy(ax, c == 0, r == len(els) - 1, ylab=f"el {el:+.0f} deg\nDoppler [Hz]")
            out.append(dict(figure="scaled_range_noise", engine=ENG_OURS, el_deg=el,
                            range_m=R, blade_line_over_noise_db=round(bl, 3),
                            body_line_over_noise_db=round(bd, 3),
                            snr_sample_db=round(info["snr_sample_db"], 3),
                            bar_db=round(bar["bar_db"], 3),
                            margin_over_bar_db=round(bl - bar["bar_db"], 3),
                            pd_at_bar=round(mc["pd"], 4),
                            stat_mean_db=round(mc["stat_mean_db"], 3),
                            verdict=vd))
    cb = fig.colorbar(m, cax=fig.add_subplot(gs[:, len(RANGES)]))
    cb.set_label("dB above the measured noise floor  (0 dB = noise, same scale everywhere)",
                 fontsize=FS - 0.5)
    fig.suptitle(f"Noise-referenced scale - {led.drone}, ours (SBR+PO), thermal noise only, "
                 f"EIRP {EIRP_DBM:g} dBm declared\n"
                 "0 dB is the measured noise floor; everything below it is painted dead",
                 fontsize=FS + 2.0, y=0.977)
    bl0, bl30 = bars[("blade", els[0])], bars[("blade", els[-1])]
    footer(fig, f"{PROVISIONAL}\nNoise floor measured, not predicted: unit-variance complex "
                f"noise through the identical STFT (rms {nf['rms']:.4g}). "
                f"DECISION BAR = the noise-only {100*(1-NULL_PFA):g}th percentile OF THE SAME "
                f"STATISTIC (Pfa = {NULL_PFA:g}, the same false-alarm target as "
                f"detection_curves.py): {NULL_TRIALS} noise-only trials through the identical "
                f"STFT and the identical band mask give "
                f"{bl0['bar_db']:+.1f} dB at el {els[0]:+.0f} and "
                f"{bl30['bar_db']:+.1f} dB at el {els[-1]:+.0f} deg (the two masks differ in "
                f"width, so the bars differ). The colour of each title is NOT a single "
                f"crossing: the same signal is re-run with {MC_TRIALS} independent noise draws "
                f"and Pd is measured against that bar - green Pd>={PD_DETECT:g}, brown "
                f"marginal, red Pd<={PD_MISS:g}. Green means DETECTABLE, not READABLE: the "
                f"statistic averages the whole {led.z[key_ours(15)+'/'+el_key(els[0])].size/led.prf*1e3:.0f} ms "
                f"record, so a line can clear the bar while every single pixel of the map "
                f"drawn here still sits at the noise floor - that is what averaging buys. "
                f"Anchor: the literature sigma is hung once, on "
                f"the mean over all 7 elevations of the {R_ANCHOR:g} m ledger; the radar "
                f"equation's 1/R^4 then supplies every other cell "
                f"(link_budget.echo_power_w), and the kernel itself carries no spreading "
                f"(self-check SC3), so nothing is counted twice.")
    return save(fig, "scaled_range_noise"), out


# --------------------------------------------------------------------------- #
#  7. 그림 4 — ③ 잡음 기준 엔진 비교 (15 m)
# --------------------------------------------------------------------------- #
def fig_engines_noise(led: Ledger, spec: RxSpec, anchors: dict, els, nf: dict,
                      bars: dict, seed: int, quick: bool, workers: int):
    cols = [ENG_OURS, ENG_OFF, ENG_REFR, ENG_DIFFR]
    fig = plt.figure(figsize=(13.2, 8.4))
    gs = fig.add_gridspec(len(els), len(cols) + 1,
                          width_ratios=[1] * len(cols) + [0.035],
                          left=0.062, right=0.925, top=0.855, bottom=0.245,
                          wspace=0.10, hspace=0.34)
    out, m = [], None
    for r, el in enumerate(els):
        for c, eng in enumerate(cols):
            ax = fig.add_subplot(gs[r, c])
            E, row = led.series(eng, el)
            if E is None or eng not in anchors:
                ax.text(0.5, 0.5, "not in the ledger", ha="center", va="center",
                        fontsize=FS, color="0.45", transform=ax.transAxes)
                ax.set_xticks([]); ax.set_yticks([])
                continue
            rng = np.random.default_rng(seed + 977 * (c + 1) + int(el))
            x, info = rx_unit_noise(E, R_ANCHOR, anchors[eng], led.fc, led.prf, spec, rng)
            f, t, S, nper = led.stft(x, cache_key=f"eng|{eng}|{el}|{seed}")
            ftip = float(row["f_tip_hz"])
            blade, body, lo = band_masks(f, ftip, led.f_flash, led.prf / nper)
            bl = line_level_over_noise_db(S, nf["rms"], blade)
            bd = line_level_over_noise_db(S, nf["rms"], body)
            m = panel_noise(ax, led, t, f, S, ftip, nf["rms"], quick)
            bar = bars[("blade", el)]
            x0, _ = rx_unit_noise(E, R_ANCHOR, anchors[eng], led.fc, led.prf, spec, None)
            mc = pd_at_bar(x0, led, blade, nf["rms"], bar["bar_db"],
                           seed + 8000 + 131 * (c + 1) + int(el), MC_TRIALS, workers)
            vd = verdict_of(mc["pd"])
            if r == 0:
                ax.text(0.5, 1.36, ENGINE_LABEL[eng], transform=ax.transAxes,
                        ha="center", va="bottom", fontsize=FS + 0.5, color="#222222")
                ax.text(0.5, 1.24, ENGINE_NOTE[eng], transform=ax.transAxes,
                        ha="center", va="bottom", fontsize=FS - 2.0, color="0.42")
            ax.set_title(f"blade line {bl:+.1f} dB  (bar {bar['bar_db']:+.1f})\n"
                         f"Pd {mc['pd']:.2f} - {vd}   ·   body {bd:+.1f} dB",
                         fontsize=FS - 0.5, color=VERDICT_COLOUR[vd])
            tidy(ax, c == 0, r == len(els) - 1, ylab=f"el {el:+.0f} deg\nDoppler [Hz]")
            out.append(dict(figure="scaled_engines_noise", engine=eng, el_deg=el,
                            range_m=R_ANCHOR, blade_line_over_noise_db=round(bl, 3),
                            body_line_over_noise_db=round(bd, 3),
                            snr_sample_db=round(info["snr_sample_db"], 3),
                            sigma_mean_anchored_dbsm=round(info["sigma_mean_dbsm"], 3),
                            bar_db=round(bar["bar_db"], 3),
                            margin_over_bar_db=round(bl - bar["bar_db"], 3),
                            pd_at_bar=round(mc["pd"], 4),
                            stat_mean_db=round(mc["stat_mean_db"], 3),
                            verdict=vd))
    cb = fig.colorbar(m, cax=fig.add_subplot(gs[:, len(cols)]))
    cb.set_label("dB above the measured noise floor  (dimensionless - engines are comparable here)",
                 fontsize=FS - 0.5)
    fig.suptitle(f"Noise-referenced scale opens the cross-engine comparison - {led.drone}, "
                 f"R = {R_ANCHOR:g} m, EIRP {EIRP_DBM:g} dBm declared",
                 fontsize=FS + 2.0, y=0.983)
    footer(fig, "\n".join([
        "How the engines were put on one scale - this is the trap, so read it before the "
        "panels. Each engine is re-levelled on its own so that its ASPECT-AVERAGED anchored "
        "RCS (mean over the 7 elevations of the 15 m ledger) equals the literature anchor. "
        "Equal aspect-averaged RCS by construction: these panels do NOT claim which engine "
        "scatters harder, they show how much of that same RCS lands in the blade lines and how "
        "each engine falls away off broadside.",
        "Hanging the anchor on one elevation instead - what detection_curves.py does, "
        "correctly, for its own single-aspect question - would make that elevation equal for "
        "every engine by definition. scaled_anchor_sensitivity.png measures how far each "
        "choice moves each arm, and which statement survives all of them.",
        f"DECISION BAR = the noise-only {100*(1-NULL_PFA):g}th percentile OF THE SAME "
        f"STATISTIC (Pfa = {NULL_PFA:g}), from {NULL_TRIALS} noise-only trials through the "
        f"identical STFT and band mask: "
        + ", ".join(f"{bars[('blade', e)]['bar_db']:+.1f} dB at el {e:+.0f} deg"
                    for e in els)
        + f". Title colour is a measured Pd against that bar ({MC_TRIALS} independent noise "
          f"draws on the same signal): green Pd>={PD_DETECT:g}, brown marginal, "
          f"red Pd<={PD_MISS:g}. Green means DETECTABLE, not READABLE - the statistic averages "
          f"the whole record, so the PathSolver panels at el -30 deg clear the bar while their "
          f"maps show no pattern at all. Those are two different questions and this figure "
          f"answers only the first.",
        PROVISIONAL]))
    return save(fig, "scaled_engines_noise"), out


# --------------------------------------------------------------------------- #
#  8. 그림 5 — 같은 데이터를 세 눈금으로 (자가검사 그림)
# --------------------------------------------------------------------------- #
def fig_three_scales(led: Ledger, spec: RxSpec, c_ours: float, el: float,
                     nf: dict, bars: dict, seed: int, quick: bool, workers: int):
    """⭐한 장으로 끝나는 설명. 위/아래 = 15 m / 120 m, 왼→오 = 세 눈금."""
    lam = C0 / led.fc
    lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                    noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)
    Rs = [RANGES[0], RANGES[-1]]
    data = {}
    for R in Rs:
        E, row = led.series(key_ours(R), el)
        rng = np.random.default_rng(seed + 31 * int(R))
        x, info = rx_unit_noise(E, R, c_ours, led.fc, led.prf, spec, rng)
        f, t, S, nper = led.stft(x, cache_key=f"noisy|{key_ours(R)}|{el}|{seed}")
        data[R] = dict(f=f, t=t, S=S, ftip=float(row["f_tip_hz"]), nper=nper, info=info)
    ref_common = float(data[Rs[0]]["S"].max())

    fig = plt.figure(figsize=(12.6, 8.1))
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 0.038],
                          left=0.065, right=0.915, top=0.795, bottom=0.205,
                          wspace=0.12, hspace=0.30)
    titles = ["(1) each panel to its own peak\n(what every figure does today)",
              f"(2) common reference\n(0 dB = the {Rs[0]:g} m panel)",
              "(3) noise reference\n(0 dB = measured noise floor)"]
    out, mp, mn, three_out = [], None, None, []
    for r, R in enumerate(Rs):
        v = data[R]
        for c in range(3):
            ax = fig.add_subplot(gs[r, c])
            if c == 0:
                mp = panel_peak(ax, led, v["t"], v["f"], v["S"], v["ftip"], None, quick)
                lab = "0.0 dB by definition"
            elif c == 1:
                mp = panel_peak(ax, led, v["t"], v["f"], v["S"], v["ftip"], ref_common, quick)
                lab = f"{20*np.log10(v['S'].max()/ref_common):+.1f} dB vs ref"
            else:
                mn = panel_noise(ax, led, v["t"], v["f"], v["S"], v["ftip"], nf["rms"], quick)
                blade, _, _ = band_masks(v["f"], v["ftip"], led.f_flash, led.prf / v["nper"])
                bar = bars[("blade", el)]
                blv = line_level_over_noise_db(v["S"], nf["rms"], blade)
                x0, _ = rx_unit_noise(led.series(key_ours(R), el)[0], R, c_ours,
                                      led.fc, led.prf, spec, None)
                mc = pd_at_bar(x0, led, blade, nf["rms"], bar["bar_db"],
                               seed + 9000 + int(R), MC_TRIALS, workers)
                vd = verdict_of(mc["pd"])
                lab = (f"blade line {blv:+.1f} dB over noise   "
                       f"(bar {bar['bar_db']:+.1f}, Pd {mc['pd']:.2f} - {vd})")
                three_out.append(dict(range_m=R, el_deg=el,
                                      blade_line_over_noise_db=round(blv, 3),
                                      bar_db=round(bar["bar_db"], 3),
                                      pd_at_bar=round(mc["pd"], 4), verdict=vd))
            if r == 0:
                ax.text(0.5, 1.18, titles[c], transform=ax.transAxes, ha="center",
                        va="bottom", fontsize=FS + 0.3, color="#222222")
            # ⚠3 열은 문장이 길다 — 컬러바를 침범하지 않게 활자를 줄인다(겹침 금지)
            ax.set_title(lab, fontsize=(FS - 0.5 if c < 2 else FS - 2.0))
            tidy(ax, c == 0, r == 1, ylab=f"R = {R:g} m\nDoppler [Hz]")
    fig.colorbar(mp, cax=fig.add_subplot(gs[0, 3])).set_label("dB (peak scales)",
                                                              fontsize=FS - 1.0)
    fig.colorbar(mn, cax=fig.add_subplot(gs[1, 3])).set_label("dB over noise",
                                                              fontsize=FS - 1.0)
    fig.suptitle("Same data, three scales - only the scale changes, never the data\n"
                 f"{led.drone}, ours (SBR+PO), el {el:+.0f} deg, radar equation applied, "
                 f"EIRP {EIRP_DBM:g} dBm",
                 fontsize=FS + 2.0, y=0.985, va="top")
    footer(fig, "Column 1 is the deception in one picture: 15 m and 120 m are the same "
                "brightness although the echo is 36 dB weaker. Column 2 restores the "
                "difference but the zero point is an arbitrary panel. Column 3 has a "
                "physical zero - the noise floor - so it also says whether the line would "
                "be detectable at all, and it is dimensionless, so other engines may join.\n"
                f"The bar quoted in column 3 is the noise-only {100*(1-NULL_PFA):g}th "
                f"percentile of that same blade-line statistic (Pfa = {NULL_PFA:g}, "
                f"{NULL_TRIALS} noise-only trials, identical STFT and band mask); Pd is "
                f"measured with {MC_TRIALS} independent noise draws on the same signal.\n"
                + PROVISIONAL)
    out.append(dict(figure="scaled_three_scales_same_data", el_deg=el,
                    ranges_m=Rs, ref_common_is=f"ours R={Rs[0]:g} m peak",
                    noise_scale_cells=three_out))
    return save(fig, "scaled_three_scales_same_data"), out


# --------------------------------------------------------------------------- #
#  9. 그림 6 + 감도표 — 앵커를 다르게 잡으면 결론이 어떻게 바뀌나
# --------------------------------------------------------------------------- #
def anchor_variants(led: Ledger, engines, sigma_ref_dbsm: float):
    """⚠«엔진 사이 기준 맞추기» 의 선택지들. 전부 **합리적인** 선택이라는 것이 요점이다.

    all_el_mean  : 7 앙각을 모은 ⟨σ⟩ (기준 — 문헌 앵커가 자세 평균이라 결이 같다)
    el-30_mean   : detection_curves.py 가 쓰는 선택(엔진당 주판 한 자세)
    el0_mean     : 정면 한 자세
    el-30_median : 평균 대신 중앙값 — 튀는 자세 하나에 안 끌리게
    """
    ref_lin = 10.0 ** (float(sigma_ref_dbsm) / 10.0)
    var = {}
    for eng in engines:
        E30, _ = led.series(eng, EL_ANCHOR)
        E0, _ = led.series(eng, 0.0)
        pool = [sigma_kernel_m2(led.series(eng, e)[0], led.fc)
                for e in ELS_ALL if led.series(eng, e)[0] is not None]
        d = {}
        if pool:
            d["all_el_mean"] = ref_lin / float(np.mean(np.concatenate(pool)))
            d["_n_el_pooled"] = float(len(pool))
        if E30 is not None:
            d["el-30_mean"] = anchor_scale(E30, led.fc, sigma_ref_dbsm)["c_anchor"]
        if E0 is not None:
            d["el0_mean"] = anchor_scale(E0, led.fc, sigma_ref_dbsm)["c_anchor"]
        if E30 is not None:
            med = float(np.median(sigma_kernel_m2(E30, led.fc)))
            if med > 0:
                d["el-30_median"] = ref_lin / med
        var[eng] = d
    return var


def sensitivity_table(led: Ledger, spec: RxSpec, variants: dict, engines, els,
                      nf: dict, bars: dict) -> list[dict]:
    """앵커 변형별 «블레이드 대역 선이 잡음 위 몇 dB» — **잡음 없는** 맵에서 잰다.

    앵커는 곱셈 상수라 이 잣대를 정확히 평행이동시킨다. 그래서 변형 하나당 맵을 다시
    굽지 않아도 되고, 표가 정확해진다(잡음을 넣으면 바닥 근처에서 포화한다)."""
    rows = []
    for eng in engines:
        for el in els:
            E, row = led.series(eng, el)
            if E is None or eng not in variants:
                continue
            base = variants[eng].get(ANCHOR_BASE)
            if base is None:
                continue
            x, info = rx_unit_noise(E, R_ANCHOR, base, led.fc, led.prf, spec, rng=None)
            f, t, S, nper = led.stft(x, cache_key=f"clean|{eng}|{el}")
            blade, body, lo = band_masks(f, float(row["f_tip_hz"]), led.f_flash,
                                         led.prf / nper)
            b0 = clean_line_db(S, nf["rms"], blade)
            d0 = clean_line_db(S, nf["rms"], body)
            bar = bars[("blade", el)]["bar_db"]
            for name, c in variants[eng].items():
                if name.startswith("_"):
                    continue
                off = float(10 * np.log10(c / base))
                rows.append(dict(engine=eng, el_deg=el, variant=name,
                                 anchor_offset_db=round(off, 3),
                                 blade_line_over_noise_db=round(b0 + off, 3),
                                 body_line_over_noise_db=round(d0 + off, 3),
                                 bar_db=round(bar, 3),
                                 margin_over_bar_db=round(b0 + off - bar, 3),
                                 # ⚠잡음 없는 판이라 이것은 **기대값**이 막대를 넘느냐다
                                 #   ⇒ 대략 Pd ≈ 0.5 선. 판정 그림의 Pd 와 뜻이 다르다.
                                 above_bar_in_expectation=bool(b0 + off > bar)))
    return rows


def aspect_contrast(rows: list[dict], engines, el_a: float = 0.0, el_b: float = -30.0):
    """⭐**앵커에 안 흔들리는** 양 — 한 엔진 안에서 자세를 바꿀 때 블레이드선이 몇 dB 변하나.

    앵커는 엔진마다 걸리는 곱셈 상수라 같은 엔진의 두 자세에서 **약분된다**. 그래서 이 값은
    «어느 앵커가 옳으냐» 와 무관하다 — 앵커가 흔드는 판(엔진 사이 절대 비교) 옆에 이것을
    같이 두는 것이 정직한 보고다."""
    out = []
    for eng in engines:
        per_variant = {}
        for r in rows:
            if r["engine"] != eng:
                continue
            per_variant.setdefault(r["variant"], {})[r["el_deg"]] = \
                r["blade_line_over_noise_db"]
        vals = {v: d[el_a] - d[el_b] for v, d in per_variant.items()
                if el_a in d and el_b in d}
        if not vals:
            continue
        spread = max(vals.values()) - min(vals.values())
        out.append(dict(engine=eng, el_from=el_a, el_to=el_b,
                        drop_db=round(float(np.mean(list(vals.values()))), 3),
                        spread_across_anchors_db=round(float(spread), 9),
                        anchor_invariant=bool(spread < 1e-6)))
    return out


def fig_sensitivity(rows: list[dict], contrast: list[dict], nf: dict, bars: dict,
                    engines, els):
    """점 그림 — 축 하나, 계열 셋(앵커 변형), 표식 모양이 색을 거들게."""
    import textwrap
    from matplotlib.lines import Line2D
    order = [ANCHOR_BASE, "el-30_mean", "el0_mean"]
    nice = {ANCHOR_BASE: "anchor on the mean over all 7 elevations  (baseline here)",
            "el-30_mean": "anchor at el -30 deg only  (detection_curves.py choice)",
            "el0_mean": "anchor at el 0 deg only"}
    # ⚠각주가 다섯 문단이라 그림 높이를 늘리고 범례를 그 **위**로 올린다
    #   (2026-08-15: 범례가 각주 위에 겹쳐 찍혔다 — 집 규약 «겹침 금지»)
    fig, axes = plt.subplots(1, len(els), figsize=(11.4, 7.9), sharex=True, sharey=True)
    axes = np.atleast_1d(axes)
    labels = [ENGINE_LABEL[e].replace("  [reference]", "\n[reference]") for e in engines]
    xs_all = [r["blade_line_over_noise_db"] for r in rows if r["variant"] in order]
    lo = min(xs_all) - 14.0
    hi = max(xs_all) + 14.0
    for ax, el in zip(axes, els):
        ax.axvspan(lo, 0.0, color="#ececf1", lw=0, zorder=0)
        ax.axvline(0.0, color="#444444", lw=1.1, zorder=1)
        ax.axvline(bars[("blade", el)]["bar_db"], color="#8d6e63", lw=1.4, ls="-.",
                   zorder=1)
        for j, name in enumerate(order):
            xs, ys = [], []
            for i, eng in enumerate(engines):
                m = [r for r in rows if r["engine"] == eng and r["el_deg"] == el
                     and r["variant"] == name]
                if m:
                    xs.append(m[0]["blade_line_over_noise_db"]); ys.append(i)
            ax.plot(xs, ys, MARK[j], ms=9, mfc=PAL[j], mec="white", mew=1.4,
                    ls="none", zorder=3)
            if name == order[0]:
                for xv, yv in zip(xs, ys):
                    ax.annotate(f"{xv:+.0f}", (xv, yv), textcoords="offset points",
                                xytext=(0, 12), ha="center", fontsize=FS - 2.0,
                                color="#333333")
        ax.set_yticks(range(len(engines)))
        if ax is axes[0]:
            ax.set_yticklabels(labels, fontsize=FS - 1.0)
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
        ax.set_xlim(lo, hi)
        ax.set_ylim(-0.7, len(engines) - 0.35)
        ax.set_title(f"el {el:+.0f} deg", fontsize=FS + 0.5)
        ax.set_xlabel("blade-band line level [dB above the noise floor]")
        ax.grid(True, axis="x", color="0.90", lw=0.7)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
    handles = [Line2D([], [], ls="none", marker=MARK[j], ms=9, mfc=PAL[j],
                      mec="white", mew=1.4, label=nice[n]) for j, n in enumerate(order)]
    barlab = " / ".join(f"{bars[('blade', e)]['bar_db']:+.1f} dB at el {e:+.0f}"
                        for e in els)
    handles += [Line2D([], [], color="#444444", lw=1.1, label="noise floor (0 dB)"),
                Line2D([], [], color="#8d6e63", lw=1.4, ls="-.",
                       label=f"decision bar: noise-only {100*(1-NULL_PFA):g}th pct of the "
                             f"SAME statistic ({barlab})")]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=FS - 1.5,
               frameon=False, bbox_to_anchor=(0.5, 0.255))
    fig.suptitle("How much does the answer depend on where the anchor is hung?",
                 fontsize=FS + 2.0, y=0.975)
    fig.tight_layout(rect=(0.0, 0.36, 1.0, 0.94))
    inv = ",   ".join(f"{ENGINE_LABEL[c['engine']].replace('  [reference]','')} "
                      f"{c['drop_db']:+.1f}" for c in contrast)
    footer(fig, "\n".join(textwrap.fill(p, 128) for p in (
        "Every marker is the same measurement re-levelled a different, equally defensible way. "
        "Shifts common to all arms (sigma_ref +-3 dB, EIRP, Rx gain, noise figure) slide the "
        "whole picture sideways and change no comparison. The anchor aspect does not: hanging "
        "it on one elevation makes that elevation equal by construction - under the orange "
        "choice the four arms tie at el -30 deg because that choice defines them to.",
        "What survives every anchor, because the constant cancels inside one engine: how far "
        "the blade line falls from el 0 to el -30 deg [dB, positive = falls] -- " + inv
        + ".   That is the comparison to quote.",
        f"The dash-dotted bar is the noise-only {100*(1-NULL_PFA):g}th percentile of THIS "
        f"statistic (Pfa = {NULL_PFA:g}), measured on {NULL_TRIALS} noise-only trials through "
        f"the identical STFT and band mask - it is not the peak pixel of a noise map, which is "
        f"a different statistic and sits about 17 dB higher. Markers are noise-free levels, so "
        f"a marker on the bar means Pd is about 0.5, not 'just detectable'.",
        PROVISIONAL)), y=0.012)
    return save(fig, "scaled_anchor_sensitivity")


# --------------------------------------------------------------------------- #
#  9-b. ⭐세 원장 검산 — «검산된다» 고 쓰지 말고 **실제로 한다**
# --------------------------------------------------------------------------- #
DC_JSON = os.path.join(ROOT, "outputs", "detection_curves.json")
NDF_JSON = os.path.join(ROOT, "outputs", "noise_distance_frame.json")


def measure_r50(led: Ledger, spec: RxSpec, c_ours: float, el: float, bars: dict,
                nf: dict, seed: int, workers: int, grid=R50_GRID_M) -> dict:
    """⭐이 그림의 잣대로 **R50 을 직접 잰다** — detection_curves 의 R50 과 맞대려고.

    거리마다 잡음을 `MC_TRIALS` 회 다시 태워 Pd 를 재고, Pd = 0.5 를 지나는 자리를
    log R 위에서 선형보간한다. 비교 상대(detection_curves.R50_m)도 Pd = 0.5 정의라 같은 뜻이다.
    """
    E, row = led.series(key_ours(15.0), el)
    ftip = float(row["f_tip_hz"])
    f, t, S, nper = led.stft(E, cache_key=f"r50probe|{el}")
    blade, _, _ = band_masks(f, ftip, led.f_flash, led.prf / nper)
    bar = bars[("blade", el)]["bar_db"]
    pts = []
    for R in grid:
        # ⚠거리는 레이더식으로만 들어간다 — 커널 E 는 15 m 판 하나를 그대로 쓴다
        #   (SC3: |E| 는 거리 불변). 원장 4 점 밖(>120 m)까지 가려면 이 «얼린 모양» 이
        #   유일한 정직한 방법이고, noise_distance_frame 의 A1 연장선과 같은 규약이다.
        x0, info = rx_unit_noise(E, R, c_ours, led.fc, led.prf, spec, None)
        mc = pd_at_bar(x0, led, blade, nf["rms"], bar,
                       seed + 12000 + int(R) + int(el), MC_TRIALS, workers)
        pts.append(dict(R_m=float(R), pd=round(mc["pd"], 4),
                        stat_mean_db=round(mc["stat_mean_db"], 3),
                        snr_sample_db=round(info["snr_sample_db"], 3)))
    r50 = None
    for a, b in zip(pts, pts[1:]):
        if a["pd"] >= 0.5 > b["pd"]:
            la, lb = math.log10(a["R_m"]), math.log10(b["R_m"])
            w = (a["pd"] - 0.5) / (a["pd"] - b["pd"])
            r50 = float(10 ** (la + w * (lb - la)))
            break
    # 잡음 없는 기대값이 막대와 만나는 자리 — 해석적 예측(Pd≈0.5 와 같은 뜻)
    x0, _ = rx_unit_noise(E, 15.0, c_ours, led.fc, led.prf, spec, None)
    f2, t2, S2, nper2 = led.stft(x0, cache_key=f"clean|{key_ours(15.0)}|{el}")
    clean15 = clean_line_db(S2, nf["rms"], blade)
    return dict(el_deg=float(el), bar_db=round(bar, 3),
                clean_line_15m_db=round(clean15, 3),
                r50_measured_m=None if r50 is None else round(r50, 1),
                r50_predicted_m=round(15.0 * 10 ** ((clean15 - bar) / 40.0), 1),
                predicted_from="R = 15 m x 10^((clean 15 m line - bar)/40), i.e. 1/R^4",
                curve=pts, n_trial_per_point=MC_TRIALS)


def crosscheck_ledgers(r50s: list[dict], variants: dict, sigma_ref_dbsm: float) -> dict:
    """⭐세 원장이 서로 검산되는지 **실제로 계산해서** 표로 낸다.

    세 원장은 앵커를 서로 다른 곳에 건다. 절대 dB·절대 거리는 그래서 그냥 못 나란히 놓는다 —
    앵커 오프셋만큼 환산해야 한다. 환산은 곱셈 상수라 1/R⁴ 위에서 거리에 10^(Δ/40) 로 붙는다.
    """
    dc = json.load(open(DC_JSON)) if os.path.exists(DC_JSON) else None
    ndf = json.load(open(NDF_JSON)) if os.path.exists(NDF_JSON) else None

    # ── (1) 앵커 원장 표 ────────────────────────────────────────────────────
    ours_all = float(10 * np.log10(variants[ENG_OURS][ANCHOR_BASE]))
    ours_el30 = float(10 * np.log10(variants[ENG_OURS]["el-30_mean"]))
    off = ours_el30 - ours_all                     # detection_curves - scaled_maps
    anchors_tbl = [
        dict(ledger="outputs/scaled_maps.json",
             anchor_scope_en="per engine, mean over all 7 elevations of the 15 m ledger",
             anchor_scope_ko="엔진마다 7 앙각 평균",
             c_anchor_db_ours=round(ours_all, 3), offset_vs_this_ledger_db=0.0,
             decision_statistic="line_level_over_noise_db (max over blade-band bins of the "
                                "time-averaged, noise-subtracted power)",
             bar_rule=f"noise-only {100*(1-NULL_PFA):g}th percentile of that same statistic "
                      f"({NULL_TRIALS} trials)"),
        dict(ledger="outputs/detection_curves.json",
             anchor_scope_en="per engine, the el -30 deg panel of the 15 m ledger",
             anchor_scope_ko="엔진마다 el −30° 판",
             c_anchor_db_ours=round(ours_el30, 3), offset_vs_this_ledger_db=round(off, 3),
             decision_statistic="comb energy (f_flash harmonics) and total blade-band energy, "
                                "DC removed",
             bar_rule="(1-Pfa) quantile of 30000 noise-only trials, Pfa = 1e-3"),
        dict(ledger="outputs/noise_distance_frame.json",
             anchor_scope_en="per (arm, elevation), that arm's own 15 m panel",
             anchor_scope_ko="(팔, 앙각)마다 그 팔의 15 m 판",
             c_anchor_db_ours=round(ours_el30, 3),
             offset_vs_this_ledger_db=round(off, 3),
             offset_note_ko="el −30° 에서는 detection_curves 와 **같은 수**다 "
                            "(엔진당 앵커 = (팔,앙각) 앵커). 다른 앙각에서는 갈라진다",
             decision_statistic="comb_contrast_db (comb contrast) and rhythm share",
             bar_rule="read_lines: null mean + grid-shake band 3.861 dB (readable), "
                      "null mean + 2 sigma (undecidable)"),
    ]
    if ndf is not None:
        rl = ndf["read_lines"]["-30"]
        nc = ndf["null_control"]["-30"]["comb_contrast_db"]
        anchors_tbl[2]["read_lines_minus30"] = dict(
            readable_db=round(float(rl["readable_db"]), 3),
            undecidable_db=round(float(rl["undecidable_db"]), 3),
            null_mean_db=round(float(nc["mean"]), 4), null_std_db=round(float(nc["std"]), 4),
            n_trial=int(nc.get("n_trial", 0)) if isinstance(nc, dict) else None)

    # ── (2) read_lines 를 이 그림의 막대로 쓸 수 있나 — 결론: **못 쓴다** ────
    read_lines_verdict = dict(
        question_ko="noise_distance_frame 의 read_lines(3.84 / 1.71 dB)를 이 그림의 막대로 "
                    "그대로 쓸 수 있나",
        answer_ko="⛔못 쓴다 — **다른 통계량의 막대**다. read_lines 는 빗살 대비"
                  "(comb_contrast_db)의 막대이고, 이 그림이 판정하는 양은 블레이드 대역의 "
                  "선 레벨(line_level_over_noise_db)이다.",
        why_ko=["빗살 대비는 «빗살 칸 / 빗살 아닌 칸» 비율이라 잡음만 넣으면 귀무평균이 "
                "정의상 ≈0 dB 다(실측 −0.018 dB). 선 레벨은 잡음 몫을 빼고 남은 것이라 "
                "귀무 중앙값이 −13 dB 대다. 두 수의 dB 는 서로 다른 자에 찍힌 눈금이다.",
                "read_lines 의 readable 은 Pfa 분위수가 아니라 «격자 흔들림 밴드»(3.861 dB) "
                "이고, undecidable 은 평균+2σ(가우스면 Pfa ≈ 2.3 %)다. 이 그림은 "
                "detection_curves 와 맞추려고 Pfa = 1e-3 분위수를 쓴다.",
                "⭐다만 **방법은 같다** — 판정하는 그 양을 잡음만으로 여러 번 재서 막대를 "
                "세운다. noise_distance_frame 은 자기 통계량에 대해 그것을 제대로 했고, "
                "이 파일은 그 방법을 자기 통계량에 대해 다시 해야 했다."],
        transferable_ko="옮길 수 있는 것은 **수가 아니라 방법**이다.")

    # ── (3) R50 검산 ────────────────────────────────────────────────────────
    rows, worst = [], 0.0
    if dc is not None:
        arms = {a["arm_id"]: a for a in dc["arms"]}
        for r in r50s:
            el = r["el_deg"]
            aid = "ours_el-30" if el == -30.0 else ("ours_el+0" if el == 0.0 else None)
            a = arms.get(aid)
            if a is None:
                continue
            k = 10.0 ** (-off / 40.0)             # 앵커를 이 그림 눈금으로 낮추면 거리도 준다
            for stat in ("band", "comb"):
                conv = float(a["R50_m"][stat]) * k
                mine = r["r50_measured_m"] or r["r50_predicted_m"]
                dev = 100.0 * (mine - conv) / conv
                rows.append(dict(
                    el_deg=el, dc_arm=aid, dc_statistic=stat,
                    dc_r50_m=round(float(a["R50_m"][stat]), 1),
                    dc_anchor_db=round(ours_el30, 3),
                    converted_to_this_anchor_m=round(conv, 1),
                    this_ledger_r50_measured_m=r["r50_measured_m"],
                    this_ledger_r50_predicted_m=r["r50_predicted_m"],
                    deviation_pct=round(dev, 2),
                    apples_to_apples=(stat == "band")))
                if stat == "band":
                    worst = max(worst, abs(dev))
    return dict(
        what_ko="세 원장의 앵커가 다르다는 사실과, 환산 후 서로 검산이 되는지의 **실측 결과**",
        anchor_offset_db=dict(
            value=round(off, 3),
            meaning_ko="detection_curves(el −30° 앵커) 가 이 원장(7 앙각 평균 앵커)보다 "
                       "이만큼 높다 — 거리로는 10^(Δ/40) = "
                       f"{10 ** (off / 40.0):.3f} 배",
            range_factor=round(float(10 ** (off / 40.0)), 4),
            sigma_ref_dbsm=round(float(sigma_ref_dbsm), 3)),
        anchors=anchors_tbl,
        read_lines_transfer=read_lines_verdict,
        r50_rows=rows,
        r50_by_el=r50s,
        agreement_ko="⭐사과-대-사과는 detection_curves 의 **band**(대역 에너지) 팔이다 — "
                     "우리 잣대도 블레이드 대역의 세기이기 때문이다. comb 팔은 f_flash "
                     "정수배만 모으는 더 센 검출기라 같은 앵커에서 더 멀리 간다(약 +28 %).",
        worst_band_deviation_pct=round(worst, 2),
        ok=bool(worst < 10.0))


# --------------------------------------------------------------------------- #
#  10. 자가검사
# --------------------------------------------------------------------------- #
def selfchecks(led: Ledger, spec: RxSpec, c_ours: float, nf: dict, seed: int,
               bars: dict, null_pm_arr, cross: dict) -> dict:
    """⭐눈금을 바꿔도 **데이터는 안 바뀐다** 는 것을 수치로 못 박는다."""
    ck = {}
    el = EL_ANCHOR
    # ⭐ 자가검사는 **잡음 눈금으로 옮긴 열**로 한다 — 커널 원판 E 는 절대값이 1e-6 급이라
    #   잡음 rms(≈0.15)와 나란히 놓으면 세 눈금이 서로 다른 자릿수를 보게 되어 검사가 뜻을 잃는다.
    E15, row15 = led.series(key_ours(15.0), el)
    x15, _ = rx_unit_noise(E15, R_ANCHOR, c_ours, led.fc, led.prf, spec,
                           np.random.default_rng(seed + 3))
    f, t, S, nper = led.stft(x15, cache_key=f"sc|{key_ours(15.0)}|{el}|{seed}")

    # SC1 — 같은 S 를 세 눈금으로 그리면 세 dB 판은 **상수 차이**뿐이다(모양 보존).
    #   ⚠ 완전한 0 은 아니다: draw() 안의 +1e-12 은 **비율에 더하는** 방어값이라
    #     S/ref 이 그 값 근처로 내려간 화소에서만 미세하게 어긋난다. 그래서 두 가지를 잰다 —
    #     (a) 맵 전체 (b) **실제로 색이 칠해지는 구간**(색역 안). (b) 는 정확히 0 이어야 한다.
    Z1 = 20 * np.log10(S / (S.max() + 1e-30) + 1e-12)
    Z2 = 20 * np.log10(S / (0.001 * S.max() + 1e-30) + 1e-12)
    Z3 = 20 * np.log10(S / (nf["rms"] + 1e-30) + 1e-12)
    inrange = Z1 >= VMIN
    dev = {}
    for nm, (A, B) in dict(peak_vs_common=(Z1, Z2), peak_vs_noise=(Z1, Z3)).items():
        d = A - B
        dev[nm + "_all_db"] = float(np.abs(d - np.median(d)).max())
        di = d[inrange]
        dev[nm + "_in_colour_range_db"] = float(np.abs(di - np.median(di)).max())
    ck["SC1_shape_preserved"] = dict(
        what="peak / common / noise 세 눈금의 dB 판은 상수만큼만 다르다(=모양이 보존된다)",
        **{k: round(v, 12) for k, v in dev.items()},
        argmax_same=bool(np.argmax(Z1) == np.argmax(Z2) == np.argmax(Z3)),
        note_ko="맵 전체의 미세 편차는 draw() 의 +1e-12 방어값 때문이고 색역 안에서는 0 이다",
        ok=bool(max(dev.values()) < 0.01
                and dev["peak_vs_common_in_colour_range_db"] < 1e-9
                and dev["peak_vs_noise_in_colour_range_db"] < 1e-9))

    # SC2 — 그런데 **색역에 자르는 순간** 모양이 달라진다. 얼마나 잘리나를 센다.
    def clipped(Z, lo, hi):
        return float(np.mean((Z <= lo) | (Z >= hi)))
    ck["SC2_clipping_is_where_shape_is_lost"] = dict(
        what="자르기 전에는 같지만, 색역 밖으로 나간 화소는 눈금마다 다르다",
        peak_own_clipped_frac=round(clipped(Z1, VMIN, VMAX), 4),
        noise_clipped_frac=round(clipped(Z3, NOISE_VMIN, NOISE_VMAX_FIG), 4),
        note="이것이 «세 눈금이 같은 그림이 아니다» 의 진짜 이유다 — 데이터가 아니라 색역이 자른다")

    # SC3 — 우리 커널의 |E| 는 거리에 불변인가(= 1/R⁴ 를 얹어도 이중계상이 아닌가)
    lv = {}
    for R in RANGES:
        _, r = led.series(key_ours(R), el)
        if r:
            lv[R] = float(r["level_db"])
    spread = (max(lv.values()) - min(lv.values())) if lv else float("nan")
    ck["SC3_kernel_has_no_spreading"] = dict(
        what="커널 E 의 평균레벨이 거리에 불변이어야 1/R⁴ 을 새로 얹는 것이 이중계상이 아니다",
        level_db_by_range=lv, spread_db=round(spread, 3), ok=bool(spread < 1.0))

    # SC4 — 레이더식을 얹은 판은 정확히 −40log10(R/15) 만큼 내려가야 한다
    lam = C0 / led.fc
    lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                    noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)
    meas, pred = {}, {}
    for R in RANGES:
        E, r = led.series(key_ours(R), el)
        if E is None:
            continue
        sig = sigma_kernel_m2(E, led.fc) * c_ours
        P = np.asarray(lb.echo_power_w(lam, sig, R, R), float)
        meas[R] = float(10 * np.log10(P.mean()))
        pred[R] = -40.0 * np.log10(R / RANGES[0])
    if meas:
        b = meas[RANGES[0]]
        err = {R: round(meas[R] - b - pred[R], 4) for R in meas}
        ck["SC4_radar_equation_slope"] = dict(
            what="레이더식을 얹으면 −40log10(R/15) [dB] 이어야 한다(모양은 안 바뀐다)",
            measured_minus_predicted_db=err,
            ok=bool(max(abs(v) for v in err.values()) < 0.5))

    # SC5 — PathSolver 팔은 스스로 1/R 을 품는가(그래서 거리축을 우리 팔에만 그린 이유)
    sv = {}
    for R in RANGES:
        _, r = led.series(key_sionna_off(R), 0.0)      # el 0 = 이 팔이 에코를 갖는 자세
        if r:
            sv[R] = float(r["level_db"])
    if len(sv) > 1:
        b = sv[RANGES[0]]
        err = {R: round(sv[R] - b + 20.0 * np.log10(R / RANGES[0]), 3) for R in sv}
        ck["SC5_pathsolver_carries_1_over_path"] = dict(
            what="PathSolver 계수는 «펼친 경로 길이» 로 1/d 확산을 이미 품는다 "
                 "— 레이더식 1/R² (진폭)이 아니다",
            level_db_by_range=sv,
            residual_vs_minus20log10R_db=err,
            ok=bool(max(abs(v) for v in err.values()) < 0.5),
            consequence="그래서 이 팔에 1/R⁴ 을 또 얹으면 이중계상이다 — "
                        "잡음 기준 **거리** 사다리는 우리 팔에만 그렸고, 엔진 비교는 "
                        "거리를 15 m 로 고정했다")

    # SC6 — 앵커는 커널의 임의 단위를 지운다(E 를 1000 배 해도 잡음 기준 맵은 동일)
    E, _ = led.series(key_ours(15.0), el)
    c_a = anchor_scale(E, led.fc, DC_SIGMA_REF)["c_anchor"]
    c_b = anchor_scale(E * 1000.0, led.fc, DC_SIGMA_REF)["c_anchor"]
    xa, _ = rx_unit_noise(E, R_ANCHOR, c_a, led.fc, led.prf, spec, None)
    xb, _ = rx_unit_noise(E * 1000.0, R_ANCHOR, c_b, led.fc, led.prf, spec, None)
    ck["SC6_anchor_removes_kernel_units"] = dict(
        what="E 에 임의 상수를 곱해도 앵커를 다시 걸면 잡음 기준 맵이 같다",
        max_abs_diff=float(np.abs(np.abs(xa) - np.abs(xb)).max()),
        ok=bool(np.allclose(np.abs(xa), np.abs(xb), rtol=1e-9, atol=1e-12)))

    # SC7 — 잡음 바닥은 이론과 맞나(측정 rms 위 **화소** 최댓값 ≈ 10log10(ln N))
    ck["SC7_noise_floor"] = dict(
        what="잡음 전용 맵의 화소 최댓값은 rms 위 10log10(ln N) 근처여야 한다 "
             "(⛔이 값은 판정 막대가 아니다 — SC8 참조)",
        measured_db=round(nf["only_max_db"], 3),
        theory_db=round(nf["only_max_theory_db"], 3),
        ok=bool(abs(nf["only_max_db"] - nf["only_max_theory_db"]) < 3.0))

    # SC8 — ⭐판정 막대는 **판정량 자체**의 귀무분포에서 나왔나
    #   (a) 시간평균 지름길이 md_mapstyle 원함수와 같은 수를 내나
    #   (b) 막대가 «화소 최댓값» 과 얼마나 다른가 — 다른 통계량이라는 증거
    n2 = float(nf["rms"]) ** 2
    E0, row0 = led.series(key_ours(15.0), EL_ANCHOR)
    xs, _ = rx_unit_noise(E0, 60.0, c_ours, led.fc, led.prf, spec,
                          np.random.default_rng(seed + 11))
    fS, tS, SS, nperS = led.stft(xs, cache_key=f"sc8|{seed}")
    bmask, _, _ = band_masks(fS, float(row0["f_tip_hz"]), led.f_flash, led.prf / nperS)
    ref = line_level_over_noise_db(SS, nf["rms"], bmask)
    fast = _stat_from_pm((np.asarray(SS, float) ** 2).mean(axis=1), bmask, n2)
    gaps = {f"blade_el{k[1]:+.0f}": round(nf["only_max_db"] - v["bar_db"], 3)
            for k, v in bars.items() if k[0] == "blade"}
    ck["SC8_bar_is_from_the_statistics_own_null"] = dict(
        what="판정 막대는 판정량(line_level_over_noise_db) 자체의 귀무분포 분위수여야 한다",
        shortcut_vs_md_mapstyle_db=round(abs(ref - fast), 12),
        bars_db={f"blade_el{k[1]:+.0f}": round(v["bar_db"], 3)
                 for k, v in bars.items() if k[0] == "blade"},
        null_trials=int(NULL_TRIALS), pfa=float(NULL_PFA),
        pixel_peak_bar_would_be_db=round(nf["only_max_db"], 3),
        pixel_peak_is_higher_by_db=gaps,
        why_ko="«화소 최댓값» 은 시간평균도 잡음차감도 안 한 다른 통계량이라 같은 잡음에서 "
               "17 dB 가량 높다 — 그것을 막대로 쓰면 실제 Pfa 가 1e-3 이 아니라 0 에 가깝다",
        ok=bool(abs(ref - fast) < 1e-9))

    # SC9 — ⭐세 원장 검산을 **실제로 했나**, 그리고 통과했나
    ck["SC9_crosschecked_against_detection_curves"] = dict(
        what="이 그림의 R50 을 detection_curves 의 R50 과 앵커 환산해 실제로 맞춰 봤다",
        anchor_offset_db=cross["anchor_offset_db"]["value"],
        worst_band_deviation_pct=cross["worst_band_deviation_pct"],
        rows=[{k: r[k] for k in ("el_deg", "dc_statistic", "converted_to_this_anchor_m",
                                 "this_ledger_r50_measured_m", "deviation_pct")}
              for r in cross["r50_rows"] if r["apples_to_apples"]],
        ok=bool(cross["ok"]))

    ck["all_ok"] = bool(all(v.get("ok", True) for v in ck.values() if isinstance(v, dict)))
    return ck


DC_SIGMA_REF = None          # main() 에서 채운다(자가검사가 같은 수를 쓰게)


# --------------------------------------------------------------------------- #
#  10-a. 정정 경위 — 무엇이 왜 틀렸고 무엇으로 바뀌었나
# --------------------------------------------------------------------------- #
def corrections_record(nf: dict, bars: dict, cross: dict, panels: list[dict]) -> list[dict]:
    """⭐이 원장이 **한 번 틀렸다가 고쳐졌다** 는 사실을 수와 함께 남긴다."""
    flips = [p for p in panels
             if p.get("figure") in ("scaled_range_noise", "scaled_engines_noise")
             and p.get("verdict") is not None
             and p["blade_line_over_noise_db"] <= nf["only_max_db"]]
    bar_db = {f"el{k[1]:+.0f}": round(v["bar_db"], 3)
              for k, v in bars.items() if k[0] == "blade"}
    return [
        dict(id="C1_wrong_bar",
             date="2026-08-15",
             severity="critical",
             what_ko="빨강/초록 판정 막대로 «잡음만 있는 맵의 **화소** 최댓값»"
                     f"(+{nf['only_max_db']:.1f} dB)을 썼다.",
             why_wrong_ko="판정하는 양은 «시간평균·잡음차감된 블레이드 선 레벨»"
                          "(line_level_over_noise_db)인데 막대는 다른 통계량에서 나왔다. "
                          "두 양은 같은 잡음에서도 값이 다르다 — 시간평균이 잡음의 요동을 "
                          "누르고 잡음 몫을 빼기까지 하므로 선 레벨의 귀무분포는 훨씬 낮다.",
             evidence_ko=f"같은 STFT·같은 마스크로 잡음만 {NULL_TRIALS} 회 통과시켜 판정량 "
                         f"자체의 분포를 재니 Pfa {NULL_PFA:g} 분위수가 "
                         + " · ".join(f"{k} {v:+.2f} dB" for k, v in bar_db.items())
                         + " 다(귀무 중앙값은 "
                         + " · ".join(
                             f"{f'el{k[1]:+.0f}'} {v['p50_db']:+.1f}"
                             for k, v in bars.items() if k[0] == "blade")
                         + " dB). 옛 막대가 "
                         + " · ".join(
                             f"{f'el{k[1]:+.0f}'} {nf['only_max_db'] - v['bar_db']:+.1f}"
                             for k, v in bars.items() if k[0] == "blade")
                         + " dB 만큼 높았다.",
             was=dict(rule="peak pixel of a noise-only map",
                      value_db=round(nf["only_max_db"], 3),
                      implied_pfa_ko="사실상 0 — 이 막대를 넘는 잡음 시행이 없다"),
             now=dict(rule=f"noise-only {100*(1-NULL_PFA):g}th percentile of the same "
                           f"statistic",
                      value_db=bar_db, pfa=float(NULL_PFA), n_trial=int(NULL_TRIALS),
                      verdict_ko=f"막대 넘김 한 판이 아니라 Pd({MC_TRIALS} 회)로 판정"),
             consequence_ko="빨간 칸 5 개(거리 사다리 120 m 두 칸 · el −30° PathSolver 세 칸)가 "
                            "전부 오판이었다. 새 막대로 다시 구우면 판정이 바뀐다.",
             flipped_cells=[dict(figure=p["figure"], engine=p.get("engine"),
                                 el_deg=p["el_deg"], range_m=p.get("range_m"),
                                 blade_line_over_noise_db=p["blade_line_over_noise_db"],
                                 old_verdict="not detected (wrong bar)",
                                 new_verdict=p["verdict"],
                                 pd_at_bar=p.get("pd_at_bar")) for p in flips],
             headline_change_ko="«120 m 는 판정 불가» 는 틀렸다. 이 잣대로 재면 "
                                f"Pd=0.5 사거리가 "
                                + " · ".join(f"el {r['el_deg']:+.0f}° {r['r50_measured_m']} m"
                                             for r in cross["r50_by_el"]) + " 다."),
        dict(id="C2_crosscheck_claimed_but_not_done",
             date="2026-08-15",
             severity="process",
             what_ko="docs/MAP_SCALING.md §7 이 «detection_curves 의 R50 과 서로 검산이 된다» "
                     "고 써 놓고 실제로 맞춰 보지 않았다.",
             why_wrong_ko="검산했다면 막대가 17 dB 어긋난 것이 그 자리에서 드러났다. "
                          "«검산된다» 는 문장은 검산을 **수행한 결과**가 있을 때만 쓴다.",
             now=dict(rule="crosscheck_ledgers() 가 앵커 오프셋을 환산해 R50 을 실제로 대조하고 "
                           "그 표를 원장·문서에 싣는다",
                      anchor_offset_db=cross["anchor_offset_db"]["value"],
                      worst_band_deviation_pct=cross["worst_band_deviation_pct"],
                      ok=cross["ok"])),
        dict(id="C3_read_lines_not_transferable",
             date="2026-08-15",
             severity="clarification",
             what_ko="«noise_distance_frame 의 read_lines(3.84 / 1.71 dB)를 가져다 썼어야 "
                     "했다» 는 지적을 검토했다.",
             finding_ko="⛔그 수는 못 가져온다 — **다른 통계량**(빗살 대비 comb_contrast_db)의 "
                        "막대다. 가져올 수 있는 것은 수가 아니라 **방법**(판정량 자체의 "
                        "귀무분포에서 막대를 세운다)이고, 이번 정정이 그 방법을 따랐다.",
             detail=cross["read_lines_transfer"]),
    ]


# --------------------------------------------------------------------------- #
#  10-b. 기존 그림 감사 — «어느 그림이 어느 눈금인가» 를 손으로 안 세고 코드에서 읽는다
# --------------------------------------------------------------------------- #
def audit_existing_scales() -> dict:
    """저장소의 모든 `draw(...)` 호출을 훑어 눈금을 분류한다.

    docs/MAP_SCALING.md 의 «기존 그림 목록» 이 이 결과 위에 선다 — 손으로 세면 다음 달에
    틀린다. 분류는 호출 인자만 본다(정적 판독이라 실행하지 않는다):
        ref 도 mode 도 없음        → ① 패널별 최댓값
        ref= 있음                  → ② 공통 기준
        mode="over_noise"          → ③ 잡음 기준
    ⚠ `ref=None` 을 명시한 호출은 ① 이다. 한 파일에서 여러 눈금을 쓰면 그대로 여러 번 센다.
    """
    import re
    pat = re.compile(r"(?<![A-Za-z_])(?:MS\.|md_)?draw\s*\(", re.S)
    rows, tally = [], {"per_panel_peak": 0, "common_ref": 0, "over_noise": 0}
    figs_of: dict[str, list] = {}
    #: savefig 의 **첫 인자를 그대로** 뜬다 — 대부분 f-string 이라 리터럴 경로로는 안 잡힌다.
    fpat = re.compile(r"savefig\(\s*([^,\)]{3,90})")
    for sub in ("benchmark", "src"):
        d = os.path.join(ROOT, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py") or fn in (os.path.basename(__file__),
                                                "md_mapstyle.py"):
                continue
            path = os.path.join(d, fn)
            try:
                src = open(path, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            if "md_mapstyle" not in src:
                continue
            for m in pat.finditer(src):
                i, depth = m.end(), 1
                while i < len(src) and depth:                # 괄호 짝 맞추기
                    depth += (src[i] == "(") - (src[i] == ")")
                    i += 1
                call = src[m.end():i - 1]
                if "fig.canvas" in src[max(0, m.start() - 12):m.start()]:
                    continue
                if "over_noise" in call:
                    kind = "over_noise"
                elif re.search(r"\bref\s*=\s*(?!None)", call):
                    kind = "common_ref"
                elif "ax" not in call and "," not in call:
                    continue
                else:
                    kind = "per_panel_peak"
                tally[kind] += 1
                rows.append(dict(file=f"{sub}/{fn}",
                                 line=src[:m.start()].count("\n") + 1, scale=kind))
                figs_of[f"{sub}/{fn}"] = sorted({g.strip() for g in fpat.findall(src)})[:6]
    by_file: dict[str, set] = {}
    for r in rows:
        by_file.setdefault(r["file"], set()).add(r["scale"])
    return dict(
        what_ko="저장소의 draw() 호출을 정적으로 분류한 목록 — MAP_SCALING.md 표의 근거",
        tally=tally,
        files_by_scale={k: sorted(f for f, s in by_file.items() if s == {k})
                        for k in ("per_panel_peak", "common_ref", "over_noise")},
        files_mixed=sorted(f for f, s in by_file.items() if len(s) > 1),
        figures_written={f: figs_of.get(f, []) for f in sorted(by_file)},
        calls=rows)


# --------------------------------------------------------------------------- #
#  11. main
# --------------------------------------------------------------------------- #
def main():
    global DC_SIGMA_REF, NULL_TRIALS, MC_TRIALS
    ap = argparse.ArgumentParser(description="세기가 보이는 마이크로도플러 맵 굽기")
    ap.add_argument("--seed", type=int, default=20260815)
    ap.add_argument("--quick", action="store_true",
                    help="시간창을 줄여 빠르게 한 바퀴(수치 검사용)")
    ap.add_argument("--only", default="",
                    help="쉼표로 그림 고르기: range_common,azimuth_common,range_noise,"
                         "engines_noise,three_scales,sensitivity")
    ap.add_argument("--null-trials", type=int, default=NULL_TRIALS,
                    help="판정 막대를 세우는 «잡음만» 시행 수(기본 20000)")
    ap.add_argument("--mc-trials", type=int, default=MC_TRIALS,
                    help="판정 Pd 몬테카를로 시행 수(기본 400)")
    ap.add_argument("--workers", type=int, default=min(32, os.cpu_count() or 1),
                    help="CPU 워커 수(GPU 안 씀)")
    a = ap.parse_args()
    NULL_TRIALS, MC_TRIALS = int(a.null_trials), int(a.mc_trials)
    t0 = time.time()
    pick = {s.strip() for s in a.only.split(",") if s.strip()}

    led = Ledger()
    spec = RxSpec(eirp_dbm=EIRP_DBM)
    ref = sigma_ref_from_literature(led.fc, led.drone)
    DC_SIGMA_REF = float(ref["sigma_ref_dbsm"])
    print(f"원장 {led.drone} · fc {led.fc/1e9:.2f} GHz · PRF {led.prf:.0f} Hz · "
          f"f_flash {led.f_flash:.2f} Hz · σ_ref {DC_SIGMA_REF:.2f} dBsm · "
          f"EIRP {EIRP_DBM:g} dBm", flush=True)

    engines = [ENG_OURS, ENG_OFF, ENG_REFR, ENG_DIFFR]
    variants = anchor_variants(led, engines, DC_SIGMA_REF)
    anchors = {e: v[ANCHOR_BASE] for e, v in variants.items() if ANCHOR_BASE in v}
    c_ours = anchors[ENG_OURS]
    print("앵커(기준 = " + ANCHOR_BASE + "):  "
          + " · ".join(f"{ENGINE_LABEL[e]} {10*np.log10(anchors[e]):+.1f} dB"
                       for e in engines if e in anchors), flush=True)

    n_pose = int(led.series(key_ours(15.0), EL_ANCHOR)[0].size)
    nf = noise_floor(led, n_pose, a.seed + 7)
    print(f"잡음 바닥 rms {nf['rms']:.5g} · 잡음만 맵의 **화소** 최댓값 "
          f"{nf['only_max_db']:+.2f} dB (이론 {nf['only_max_theory_db']:+.2f}) "
          f"— ⛔이건 판정 막대가 아니다", flush=True)

    # ── ⭐판정 막대 — 판정량 자체의 귀무분포 ─────────────────────────────────
    ELS_FIG = [0.0, -30.0]
    Pm_null, rms_null = null_pm(led, n_pose, a.seed + 101, NULL_TRIALS, a.workers)
    probe, _ = led.series(key_ours(15.0), EL_ANCHOR)
    f_ax, _, _, nper_ax = led.stft(probe, cache_key=f"probe|{EL_ANCHOR}")
    bars, masks_used = {}, {}
    for el in ELS_FIG:
        row = led.row(ENG_OURS, el)
        blade, body, lo = band_masks(f_ax, float(row["f_tip_hz"]), led.f_flash,
                                     led.prf / nper_ax)
        bars[("blade", el)] = bar_from_null(Pm_null, blade, nf["rms"])
        bars[("body", el)] = bar_from_null(Pm_null, body, nf["rms"])
        masks_used[el] = dict(f_tip_hz=float(row["f_tip_hz"]), band_lo_hz=round(lo, 1),
                              band_hi_hz=round(BAND_HI * float(row["f_tip_hz"]), 1),
                              blade_bins=int(blade.sum()), body_bins=int(body.sum()))
        b = bars[("blade", el)]
        print(f"  판정 막대 el {el:+.0f}° : {b['bar_db']:+.2f} dB "
              f"(Pfa {NULL_PFA:g} · 빈 {b['n_bins']} · p50 {b['p50_db']:+.2f} · "
              f"p99 {b['p99_db']:+.2f} · 최댓값 {b['max_db']:+.2f}) — "
              f"화소 최댓값 막대였다면 {nf['only_max_db']:+.2f}, "
              f"{nf['only_max_db']-b['bar_db']:+.1f} dB 높다", flush=True)

    figs, panels = [], []
    if not pick or "range_common" in pick:
        p, o = fig_range_common(led, spec, c_ours, 0.0, a.quick); figs.append(p); panels += o
    if not pick or "azimuth_common" in pick:
        p, o = fig_azimuth_common(led, ELS_FIG, a.quick); figs.append(p); panels += o
    if not pick or "range_noise" in pick:
        p, o = fig_range_noise(led, spec, c_ours, ELS_FIG, nf, bars, a.seed, a.quick,
                               a.workers)
        figs.append(p); panels += o
    if not pick or "engines_noise" in pick:
        p, o = fig_engines_noise(led, spec, anchors, ELS_FIG, nf, bars, a.seed, a.quick,
                                 a.workers)
        figs.append(p); panels += o
    if not pick or "three_scales" in pick:
        p, o = fig_three_scales(led, spec, c_ours, EL_ANCHOR, nf, bars, a.seed, a.quick,
                                a.workers)
        figs.append(p); panels += o

    sens = sensitivity_table(led, spec, variants, engines, ELS_FIG, nf, bars)
    contrast = aspect_contrast(sens, engines)
    if not pick or "sensitivity" in pick:
        figs.append(fig_sensitivity(sens, contrast, nf, bars, engines, ELS_FIG))

    # ── ⭐검산 — 말이 아니라 수로 ────────────────────────────────────────────
    r50s = [measure_r50(led, spec, c_ours, el, bars, nf, a.seed, a.workers)
            for el in ELS_FIG]
    cross = crosscheck_ledgers(r50s, variants, DC_SIGMA_REF)
    for r in r50s:
        print(f"  R50(이 잣대) el {r['el_deg']:+.0f}° = {r['r50_measured_m']} m "
              f"(예측 {r['r50_predicted_m']} m)", flush=True)
    for r in cross["r50_rows"]:
        if r["apples_to_apples"]:
            print(f"  ↔ detection_curves band R50 {r['dc_r50_m']} m → 환산 "
                  f"{r['converted_to_this_anchor_m']} m · 편차 {r['deviation_pct']:+.2f} %",
                  flush=True)

    ck = selfchecks(led, spec, c_ours, nf, a.seed, bars, Pm_null, cross)
    corr = corrections_record(nf, bars, cross, panels)

    # ── 원장 ────────────────────────────────────────────────────────────────
    led_out = dict(
        _meta=dict(
            generator="benchmark/build_scaled_maps.py",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            question_ko="맵을 «패널별 최댓값» 이 아닌 눈금으로 다시 그려 세기를 되살린다",
            gpu_ko="GPU·솔버 호출 없음 — 저장된 원장만 읽은 CPU 작업",
            provisional_ko="⚠절대 세기는 **잠정**이다 — 셸 두께·커널 반사율 정정이 진행 중이라 "
                           "잡음 기준 판의 절대 dB 는 통째로 움직일 수 있다. 이 그림이 주장하는 "
                           "것은 판 사이의 **차이**다",
            provisional=True,
            scales=dict(
                per_panel_peak="draw(mode='peak', ref=None) — 0 dB = 그 패널의 최댓값",
                common_ref="draw(mode='peak', ref=스칼라) — 0 dB = 지정한 한 판의 최댓값",
                over_noise="draw(mode='over_noise', noise_rms=…) — 0 dB = 측정한 잡음 바닥"),
            source=dict(ledger_json=os.path.relpath(LEDGER_JSON, ROOT),
                        ledger_npz=os.path.relpath(LEDGER_NPZ, ROOT),
                        drone=led.drone, fc_hz=led.fc, prf_hz=led.prf,
                        f_flash_hz=led.f_flash, n_poses=n_pose),
            stft=dict(module="src/md_mapstyle.flash_spec", periods=float(led.periods),
                      nperseg=int(nf["nper"]), hop=2, zero_pad=8, window="hann",
                      df_hz=round(led.prf / nf["nper"], 2),
                      dt_ms=round(nf["nper"] / led.prf * 1e3, 3)),
            display=dict(t_window_ms=[SHOW_T0_MS, SHOW_T0_MS + SHOW_MS],
                         f_window="|f| <= 2.05 f_tip",
                         note_ko="표시만 자른다 — 모든 잣대는 전 구간에서 쟀다"),
            colour=dict(peak_vmin_db=VMIN, peak_vmax_db=VMAX,
                        noise_vmin_db=NOISE_VMIN, noise_vmax_db=NOISE_VMAX_FIG,
                        noise_vmax_note_ko="규약 기본은 40 이지만 거리 사다리 하나가 36 dB 를 "
                                           "먹어 50 으로 넓혔다(build_md_noise_range_fig 선례)",
                        dead_below_db=DEAD_TO_DB,
                        dead_note_ko="잡음 바닥 아래는 무채색으로 죽인다 — 그게 이 그림의 요점"),
            budget=dict(eirp_dbm=EIRP_DBM, rx_gain_dbi=spec.grx_dbi, nf_db=spec.nf_db,
                        capture=spec.capture,
                        noise_w_per_sample=float(noise_power_w(spec, led.prf)),
                        source="benchmark/detection_curves.EIRP_DBM (같은 선언값)"),
            anchor=dict(sigma_ref_dbsm=DC_SIGMA_REF, provenance=ref["provenance"],
                        baseline=ANCHOR_BASE,
                        baseline_ko="엔진당 하나 — 7 앙각을 모은 ⟨σ_kernel⟩(15 m 판)을 σ_ref 에 "
                                    "맞춘다. 문헌 앵커 자체가 자세 평균이라 결이 같다",
                        differs_from_detection_curves_ko=
                            "⚠benchmark/detection_curves.py 는 el −30° 한 자세에 건다. 거기서는 "
                            "엔진 하나·자세 하나씩만 보고하므로 옳다. 이 그림은 자세와 엔진을 "
                            "함께 놓으므로 한 자세에 걸면 그 자세가 정의상 같아진다(실측: el −30 "
                            "에서 네 팔이 +57/+60/+58 dB 로 붙는다). 두 원장의 절대 dB 를 나란히 "
                            "인용하려면 이 차이를 먼저 환산해야 한다 — 오프셋은 sensitivity.rows",
                        c_anchor={k: float(v) for k, v in anchors.items()},
                        c_anchor_db={k: round(float(10 * np.log10(v)), 3)
                                     for k, v in anchors.items()},
                        variants={k: {kk: float(vv) for kk, vv in v.items()}
                                  for k, v in variants.items()},
                        els_pooled_deg=ELS_ALL),
            band=dict(blade=f"{BAND_LO}..{BAND_HI} x f_tip(el), 하한은 3 빈 이상",
                      body="|f| <= 0.5 f_flash"),
            related_ledgers=dict(
                note_ko="⚠잡음 기준 원장이 셋이고 **앵커 범위가 서로 다르다** — 절대 dB 를 "
                        "그냥 나란히 인용하면 안 된다. 고르는 법과 환산은 docs/MAP_SCALING.md §4-b",
                items=[
                    dict(json="outputs/detection_curves.json",
                         anchor_scope="엔진마다 el −30° 판",
                         answers_ko="이 팔은 몇 m 까지 탐지되나(R50)"),
                    dict(json="outputs/noise_distance_frame.json",
                         anchor_scope="(팔, 앙각)마다 그 팔의 15 m 판",
                         answers_ko="거리를 늘리면 무엇이 먼저 안 읽히나",
                         cross_check_ko="⭐그쪽 자가검사 3(거리 지수 p = 0.02 우리 · 2.008 "
                                        "PathSolver el 0°)과 이쪽 SC3·SC5(산포 0.30 dB · "
                                        "잔차 0.07 dB)가 **독립적으로 같은 사실**을 쟀다"),
                    dict(json="outputs/scaled_maps.json",
                         anchor_scope="엔진마다 7 앙각 평균",
                         answers_ko="같은 평균 RCS 를 줬을 때 무늬가 자세에 따라 어떻게 무너지나")]),
            forbidden_ko="⚠①② 에서 엔진 사이 절대 세기 비교 금지(우리 E 는 면적 차원, "
                         "PathSolver 계수는 무차원). ③ 은 둘 다 σ 로 환산 뒤 잡음으로 나눠 "
                         "무차원이라 열린다 — 대신 앵커 선택이 결론을 흔든다(sensitivity)",
            figures_dir=os.path.relpath(FIGDIR, ROOT)),
        noise_floor=dict(rms=nf["rms"], only_max_over_rms_db=round(nf["only_max_db"], 3),
                         only_max_theory_db=round(nf["only_max_theory_db"], 3),
                         probe="unit-variance circular complex Gaussian, same STFT",
                         meaning_ko="잡음만 있는 맵의 **화소** 최댓값 — 색역·설명용 참고값",
                         not_a_decision_bar_ko="⛔판정 막대가 아니다. 판정량은 시간평균·"
                                               "잡음차감을 거치므로 막대는 decision_bar 에 "
                                               "있는 값을 쓴다(약 17 dB 아래)"),
        decision_bar=dict(
            what_ko="⭐빨강/초록을 가르는 막대 — **판정량 자체**의 귀무분포에서 세웠다",
            statistic="src/md_mapstyle.line_level_over_noise_db",
            statistic_ko="블레이드 대역 빈들의 시간평균 전력에서 잡음 몫을 빼고 남은 최댓값",
            rule=f"noise-only {100*(1-NULL_PFA):g}th percentile (Pfa = {NULL_PFA:g}) of that "
                 f"same statistic",
            rule_ko=f"잡음만 {NULL_TRIALS} 회를 **같은 STFT·같은 대역 마스크**로 통과시켜 "
                    f"만든 분포의 (1−{NULL_PFA:g}) 분위수. Pfa 목표는 detection_curves 와 같다",
            n_trial=int(NULL_TRIALS), pfa=float(NULL_PFA), seed=int(a.seed + 101),
            noise_rms_used=float(nf["rms"]),
            rms_across_null_trials=dict(mean=float(rms_null.mean()),
                                        std=float(rms_null.std())),
            per_mask={f"{k[0]}_el{k[1]:+.0f}": v for k, v in bars.items()},
            masks=masks_used,
            mask_note_ko="⚠마스크가 넓을수록 최댓값 통계라 막대가 올라간다 — el 마다 f_tip 이 "
                         "달라 빈 수가 달라지므로 막대를 따로 세운다",
            verdict_rule_ko=f"막대 넘김을 한 판으로 정하지 않는다 — 같은 신호에 잡음을 "
                            f"{MC_TRIALS} 회 다시 태워 Pd 를 재고 "
                            f"Pd≥{PD_DETECT:g} 탐지 · {PD_MISS:g}<Pd<{PD_DETECT:g} 애매 · "
                            f"Pd≤{PD_MISS:g} 미탐지 (noise_distance_frame 판정 어휘와 동일)",
            mc_trials=int(MC_TRIALS)),
        crosscheck=cross,
        corrections=corr,
        figures=figs,
        panels=panels,
        sensitivity=dict(
            what_ko="앵커를 다르게 걸면 «블레이드 대역 선이 잡음 위 몇 dB» 가 어떻게 바뀌나",
            method_ko="앵커는 곱셈 상수라 잣대를 정확히 평행이동시킨다 — 잡음 없는 맵에서 재고 "
                      "변형별 오프셋을 더한다",
            common_mode_offsets_db=dict(
                sigma_ref_plus_3="+3.0 (모든 팔 동일 — 비교 불변)",
                sigma_ref_minus_3="-3.0 (모든 팔 동일 — 비교 불변)",
                eirp_63_dBm=f"{63.0 - EIRP_DBM:+.1f} (모든 팔 동일)",
                eirp_12_dBm=f"{12.0 - EIRP_DBM:+.1f} (모든 팔 동일)",
                note_ko="이 넷은 그림을 통째로 옆으로 민다 — 어떤 비교도 안 바꾼다. "
                        "결론을 흔드는 것은 **앵커를 어느 자세에 거나** 하나뿐이다"),
            verdict_ko="⚠el −30° 에서 «우리 커널이 PathSolver 보다 낫다» 는 **앵커에 의존한다** — "
                       "el −30° 에 앵커를 걸면 네 팔이 정의상 붙는다. 앵커와 무관하게 참인 문장은 "
                       "아래 aspect_contrast 다(엔진 안에서 상수가 약분된다)",
            aspect_contrast=contrast,
            rows=sens),
        existing_figure_scales=audit_existing_scales(),
        selfcheck=ck,
        runtime_s=round(time.time() - t0, 1))
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    tmp = OUT_JSON + ".tmp"
    json.dump(led_out, open(tmp, "w"), ensure_ascii=False, indent=1, default=float)
    os.replace(tmp, OUT_JSON)

    print(f"\n자가검사 all_ok = {ck['all_ok']}")
    for k, v in ck.items():
        if isinstance(v, dict):
            print(f"  {'✅' if v.get('ok', True) else '⛔'} {k}: {v.get('what', '')}")
    print(f"\n→ {os.path.relpath(OUT_JSON, ROOT)}  ({time.time()-t0:.0f} s)")


if __name__ == "__main__":
    main()
