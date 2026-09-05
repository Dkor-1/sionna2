# -*- coding: utf-8 -*-
"""
freespace_detect.py — report13 **자유공간 검출기 형상 · ECA · CFAR** (docs/REPORT13_SPEC.md §5, §9)
=====================================================================================================
report01~12 는 무향챔버(R_b ≤ 22 m) 안에서 돌았다. 자유공간(FS-1)으로 나가면 검출기의 **형상**이
바뀐다 — 거리창이 km 급이고, DPI 대 잡음비(DNR)가 70~130 dB 이며, 파형마다 fs/B_ref 오버샘플이
1.05배(WiFi)에서 17배(5G SSB)까지 벌어진다. 이 모듈은 그 형상만 정의하고 **커널은 재구현하지 않는다.**

  · 거리-도플러(CAF)  → `passive_process.range_doppler` / `detection_gpu.rd_batch`
  · 2D CA-CFAR        → `passive_process.ca_cfar_2d`     / `detection_gpu.cfar_batch`
  · ECA               → `passive_process.ECACanceller`
  (여기서 만드는 것은 **탭 수·거리창·가드폭·검출판정·경험 Pfa 교정** 같은 '형상' 뿐이다.)

■ 이번 리포트에서 **뒤집힌 설계 결정**을 코드로 박아둔 곳 (근거는 각 함수 docstring)
  R6 : ECA `ridge_rel = 0` 이 정본이다. 1e-6·1e-4 는 **상대** 대각로딩이라 |R[0]|(≈N·P_ref)이
       곱해져 오히려 큰 로딩이 되고, 고 DNR 에서 비-0도플러 셀로 누설을 만든다.
  F6 : `n_taps` 를 샘플 고정(128)이 아니라 **지연스팬 등가**(tap_span_m=60 m)로 잡는다.
       샘플 고정은 fs 가 4배 다른 파형끼리 지연커버리지를 4배 불균등하게 준다.
  R3§2 : 검출 판정은 전역 argmax 가 **아니다** — 표적 근방 ±2셀 문턱초과다.
  F7 : 오경보는 빈이 아니라 **분해능셀** 단위로 센다 — 오버샘플이 큰 파형(SSB, fs/B_ref≈17)은
       빈 기준과 분해능셀 기준에서 **순위가 뒤집힌다**(빈 기준 최악 ↔ 분해능셀 기준 최선).
       ⚠ 스펙 §10 의 49.2/2.88 은 도플러행 200(F1 이전 report12 타일링) 규약에서 나온 값이라
       정본 배관(F1, M=5)으로는 재현되지 않는다(아래 L3 · `false_alarms_per_cpi` docstring).
       **크기는 인용하지 말고 순위 뒤집힘만 읽을 것.**
  A5 : `passive_process.doppler_guard_mask` 는 **검출마스크만** 다룬다(코드 주석이 명시).
       훈련셀에서도 빼려면 가드행을 **제거한 부분맵에 CFAR 를 걸어야** 한다 → `_cfar_excl_rows`.

■ ⚠ **이 모듈이 혼자 못 고치는 것 — 다음 사람이 반드시 알고 있어야 하는 살아남은 한계**
  (전부 감사에서 재현된 사실이다. 지우지 말 것.)

  L1. **도플러축이 아직 물리가 아니다** (감사 A1/[1]). RD 커널은 `PRF = fs/Lf` 로 버퍼에서
      PRF 를 만든다 — M 은 자유 파라미터가 아니라 프레임 길이에 묶여 있다. report12 식
      `np.tile(wf.tx, M)` CPI 의 실측 PRF 는 W1 19.2× · **G1 40×** · G3 10× (L1 만 1.0×)로
      물리 반복률과 어긋난다. 이 모듈은 `check_kernel_prf()` 로 **탐지·기록**할 뿐이고
      (`meta.cpi.doppler_axis_physical`), 실제 수정은 CPI 를 만드는
      `experiment_freespace_range.stage_threshold` 가 프레임을 `Lf_required = round(fs/PRF)`
      샘플(반복주기, G1 이면 20 ms = 2.4576 M 샘플·CPI 12.288 M 샘플)로 잡아야 끝난다.
      메모리 비용이 크므로 대안은 F1 의 M-유도를 포기하고 SSB 핸디캡을 듀티/에너지 항
      (`freespace_link.duty_db_from_cpi`)으로 모델링하는 것 — **어느 쪽을 골랐는지 meta 에 박을 것.**
  L2. **스펙 §5.2 dopoff 격자 `{3,5,8,15,30}` 은 M 을 모른다.** F1 물리에서 G1 은 M=5 →
      `|dopoff|max = 2` 라 다섯 개 전부 불가능하고, G3 는 3/5/8 만 가능하다. 즉 스펙 §10 의
      `detector_transfer.S_G.G1.…dopoff.*` 가지는 **현재 물리로 생성 불가**다. 이 모듈은
      `feasible_dopoff_bins()` 로 걸러 `skipped`+사유를 남긴다 — 스펙 §5.2 를 M 의존으로
      재정의하는 것은 상위(스펙 개정) 몫이다.
  L3. **스펙 §10 의 ★FA 값은 정본 배관으로 재현되지 않는다.** ★W1 16.0/15.3·L1 6.1/3.6·
      G1 49.2/2.88 은 도플러행 100/100/**200** 에서 나온 값인데, G1 의 200 은 F1 이전
      (report12 타일링) 규약이다. `false_alarms_per_cpi` 는 두 규약(`valid`/`full`)을 모두
      내고 `spec_reference` 에 이 모순을 적어 보낸다 — **날조하지 않고 기록만 한다.**
  L4. **T_CPI=0.1 s 에서 L2/L3(LTE PRS, PRF 6.25 Hz)는 존재하지 않는 셀이다.** M 이 2로 클램프
      되고 0-도플러 가드가 축을 통째로 먹는다. `_cfar_excl_rows` 는 이제 조용히 전부 False 를
      돌려주는 대신 raise 하고, 상위는 `freespace_scene.cpi_feasibility()` 로 **먼저** 걸러
      `limit="cpi_too_short"`/`"doppler_axis_degenerate"` 회색 라벨을 달아야 한다.
  L5. **분해능셀 FA 는 거리 오버샘플만 나눈다.** slow-time Hann 주엽이 ★1.44빈(−3 dB 폭)이라
      도플러축도 상관돼 있어 전 모드 공통 ~1.4배 과대다(순위는 불변). `doppler_over` 인자로
      감도만 볼 수 있고 정본은 1.0 이다.
  L6. **`cfar_guard_bins` 의 튜플 순서는 `(도플러, 거리)`** (`ca_cfar_2d` 규약). 스펙 meta 의
      `G1_rescell:[11,2]` 는 [거리,도플러] 표기라 **JSON writer 가 전치**해야 한다(값은 동일).

그림 텍스트는 영어, 주석·docstring·print 는 한국어(프로젝트 규약).
"""
from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                      # noqa: E402

# ── 커널은 전부 기존 모듈에서 가져온다(재구현 금지) ─────────────────────────────
from passive_process import (ECACanceller, ca_cfar_2d, range_doppler,    # noqa: E402
                             PFA_CALIBRATION, check_detector_config)
# 시간축(F1 물리 반복률)의 단일 진리원 — 형상이 M 을 자기가 유도할 수 있어야 한다(감사 B2/A1)
import freespace_scene as _fss                                           # noqa: E402

C0 = 299792458.0

# ── 스펙 §5 선언 상수 ─────────────────────────────────────────────────────────
TAP_SPAN_M = 60.0            # F6: ECA 가 덮는 **지연 스팬**[m]. DPI 주엽+여유를 덮고,
                             #     표적 R_b(수백 m~km) ≫ 60 m 이라 표적 자기소거는 없다.
ECA_RIDGE_REL = 0.0          # R6: 정본. (ECACanceller 는 여기에 절대 1e-6 을 더한다)
N_RANGE_GATE = 64            # S-G(게이트) 거리빈 수 — 표적 진리 R_b 중심
RB_SPAN_DEFAULT_M = 6000.0   # S-W(전체창) 기본 거리 스팬[m] (스펙 §5.2 예시와 동일)
GUARD_FIXED = (2, 2)         # (도플러, 거리) — report01~12 와 비교가능성 유지
TRAIN_FIXED = (6, 6)
DOPPLER_GUARD_WIDTH = 3      # 0-도플러 능선 가드 폭(zd±1) — Hann DFT 가 ±1빈서 −5.75dB 뿐
PFA_CELL = 1e-4              # 셀당 명목 Pfa(정본)
TOL_CELL = 2                 # 표적 근방 허용 ±2빈 (R3§2)


# --------------------------------------------------------------------------- #
#  0. 소도구
# --------------------------------------------------------------------------- #
def _n_taps_for_span(fs, tap_span_m=TAP_SPAN_M):
    """F6 — 지연스팬 등가 ECA 탭 수 `ceil(tap_span_m / (c/fs))`.

    왜 샘플 고정(128)이 아닌가: fs 가 30.72 MHz(LTE)↔122.88 MHz(NR) 로 4배 다르면 같은 128탭이
    각각 1249 m 와 312 m 를 덮는다 — **파형마다 지연커버리지가 4배 불균등**해져 공정성이 깨진다.
    스펙 §5.1 의 정본 식은 `ceil` 이다.

    ⚠ 스펙 내부 불일치(정직 표기): §5.1 식(ceil)과 §10 표(`{nr:25, lte:7, wifi:16}`)가 안 맞는다.
      ★실측 — ceil: WiFi **17** / LTE **7** / NR 25,  round: 16 / **6** / 25.
      즉 §10 표는 lte 만 ceil, wifi 만 round 를 쓴 혼합값이다. 구현은 §5.1 식(ceil)을 따르고
      round 값은 `n_taps_round` 로 병기한다. ("LTE 7·NR 25 는 두 규약 동일" 은 **틀린 진술**이다 —
      LTE 의 round 는 6 이다. 초기 구현보고의 오류를 여기 적어 남긴다.)
    """
    dr = C0 / float(fs)
    return int(math.ceil(float(tap_span_m) / dr))


def _n_train_at(nd, nr, di, ri, guard, train):
    """(감사 ⑥/#8) `ca_cfar_2d` 가 **그 셀에서 실제로 쓰는** 학습셀 수.

    `ca_cfar_2d` 는 맵 가장자리에서 창을 자르므로(`ntr = (r1−r0)(c1−c0) − (gr1−gr0)(gc1−gc0)`,
    passive_process.py:161-173) 내부셀 해석식 `(2(g+t)+1)² − (2g+1)²` 은 **대부분의 셀에서 틀리다.**
    ★실측: S-G 부분맵 97×64·fixed(2,2)/(6,6) 는 중앙에서 264(=스펙 meta 값)지만,
      G1(M=5) 부분맵 2×64 는 **24**, G1 rescell 부분맵 17×64 는 **480**.
      Marcum 참조선이 264→24 에서 19.44→20.23 dB 로 0.8 dB 움직인다(G1 에서 F13 점선이 틀린다).
    """
    gd, gr = int(guard[0]), int(guard[1])
    td, tr = int(train[0]), int(train[1])
    r0, r1 = max(0, di - (gd + td)), min(nd, di + gd + td + 1)
    c0, c1 = max(0, ri - (gr + tr)), min(nr, ri + gr + tr + 1)
    g0, g1 = max(0, di - gd), min(nd, di + gd + 1)
    h0, h1 = max(0, ri - gr), min(nr, ri + gr + 1)
    return int((r1 - r0) * (c1 - c0) - (g1 - g0) * (h1 - h0))


def feasible_dopoff_bins(M, dopoff_bins, width=DOPPLER_GUARD_WIDTH):
    """(감사 A2/③/B2) 도플러축 M 에서 **실현 가능한 dopoff** 만 골라낸다.

    `zd = M//2` 이고 0-도플러 가드가 행 `[zd−w//2, zd+w//2]` 을 지우므로, 쓸 수 있는 오프셋은
        `0 ≤ zd+dop < M`  **그리고**  `zd+dop` 가 가드행 밖
    뿐이다. ★헤드라인 모드 G1(M=5)에서는 `|dop|=2` 하나만 남아 스펙 §5.2 의 정본 격자
    `{3,5,8,15,30}` 이 **다섯 개 전부 축 밖**이다 — 예전 구현은 여기서 ValueError 를 던져
    stage 전체를 멈췄다. 이제 사유를 붙여 건너뛰고 JSON 에 `skipped` 로 남긴다(스펙 §8.6
    "축을 자르지 않고 라벨만 단다" 정신).

    반환 `(used, skipped)` — `used`=[int], `skipped`={dop: 사유문자열}."""
    M = int(M)
    lo, hi, zd = _submap_rows(M, None, width)
    used, skipped = [], {}
    for dop in dopoff_bins:
        di = zd + int(dop)
        if not (0 <= di < M):
            skipped[int(dop)] = f"outside doppler axis (M={M}, |dopoff|max={max(zd, M - 1 - zd)})"
        elif lo <= di < hi:
            skipped[int(dop)] = f"inside zero-doppler guard rows [{lo},{hi})"
        else:
            used.append(int(dop))
    return used, skipped


def _submap_rows(nd, f_d=None, width=DOPPLER_GUARD_WIDTH):
    """0-도플러 가드로 **제거할 행 구간** [lo, hi) 를 돌려준다.

    f_d 가 있으면 `argmin|f_d|`(passive_process.doppler_guard_mask 규약), 없으면 fftshift 중앙
    `nd//2`(detection_gpu.peak_batch 규약). 두 규약은 짝수 M 에서 동일하다."""
    zd = int(np.argmin(np.abs(np.asarray(f_d)))) if f_d is not None else nd // 2
    h = int(width) // 2
    return max(0, zd - h), min(nd, zd + h + 1), zd


def _row_to_submap(di, lo, hi):
    """전체맵 도플러행 di → 가드행 제거 부분맵의 행 인덱스. 가드행 자체면 None."""
    di = int(di)
    if di < lo:
        return di
    if di >= hi:
        return di - (hi - lo)
    return None


def _is_torch(x):
    return type(x).__module__.startswith("torch")


def _wilson(k, n, z=1.96):
    """이항비율 Wilson 95% 신뢰구간 — K=4000 급에서 정규근사보다 꼬리에서 정직하다."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z / den * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, c - h), min(1.0, c + h))


def _interp_x_at(y_target, y, x):
    """단조화한 y(x) 에서 y=y_target 이 되는 x (선형보간). 범위 밖이면 None."""
    y = np.maximum.accumulate(np.asarray(y, float))     # Pd 는 SNR 에 단조 — MC 잡음만 제거
    x = np.asarray(x, float)
    if y.max() < y_target or y.min() > y_target:
        return None
    return float(np.interp(y_target, y, x))


def _batch_size(Ns, frac=0.6):
    """트라이얼 배치 크기 — GPU 를 크게 쓴다(사용자 방침). SIONNA2_DET_BATCH 로 실시간 조절."""
    env = int(os.environ.get("SIONNA2_DET_BATCH", "0") or 0)
    if env > 0:
        return env
    try:
        from gpu import budget_mb
        bud = budget_mb() * 1e6 * frac
    except Exception:
        bud = 6e9
    per = max(Ns, 1) * 8 * 10                      # surv + FFT 중간버퍼 대략 10배
    return int(max(2, min(128, bud / per)))


def _pre_fs(pre):
    """Precomputed(또는 그 오리(duck))에서 fs[Hz] 를 꺼낸다."""
    fs = getattr(pre, "fs_hz", None)
    if fs is None:
        wf = getattr(pre, "wf", None)
        fs = getattr(wf, "fs_hz", None)
    if fs is None:
        raise ValueError("pre 에 fs_hz(또는 wf.fs_hz)가 없다")
    return float(fs)


def _dev_of(pre, device=None):
    """연산 디바이스. **`gpu.pick()` 을 torch import 전에 부른다**(감사 #11/D).

    예전에는 그냥 `"cuda"`(=CUDA_VISIBLE_DEVICES 미설정이면 물리 GPU0)를 돌려줬다. GPU0/1 은
    다른 사용자 카드라 감사자의 `transfer_by_dopoff` 실행이 실제로 **cuda:0 OOM** 으로 죽었다.
    저장소 관례는 `gpu.pick()`(여유 메모리 기준 + `SIONNA2_GPU` 강제)이고, 이 리포트의 운영
    지시는 GPU3 전용이다 — `SIONNA2_GPU=3` 이 그대로 존중된다.
    ⚠ `pick()` 은 `CUDA_VISIBLE_DEVICES` 를 세팅하므로 **CUDA 컨텍스트가 생기기 전**에 불려야
      한다. 그래서 torch import 보다 먼저 호출한다."""
    if device is not None:
        return device
    t = getattr(pre, "_t", None)
    if isinstance(t, dict) and "dev" in t:
        return t["dev"]
    try:
        from gpu import pick
        pick(verbose=False)
    except Exception:
        pass
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _marcum_cfar_snr90_db(n_train, pfa, pd=0.9):
    """**CA-CFAR 인지형** 참조 곡선의 SNR (스펙 §5.5 / R3§4).

    `Pd = (1 + α/(N_tr(1+SNR)))^(−N_tr)`, `α = N_tr(Pfa^(−1/N_tr) − 1)` 를 SNR 로 푼 닫힌형:
        1+SNR = (Pfa^(−1/N) − 1) / (Pd^(−1/N) − 1)
    ⚠ 이 식은 **지수분포 포락(Swerling-1 류)** 표적 가정이다. report13 의 측정은 CPI 내부
    비요동이므로 이 점선은 우리 측정보다 **위**에 앉는 것이 정상이다 — 손실 dB 로 인용하지 말고
    F13 의 참조 점선으로만 쓴다(스펙 §5.5: cfar_loss 0.076 dB 는 '평균 문턱 오프셋'이지
    분산을 포함한 검출손실이 아니다)."""
    n = float(n_train)
    num = pfa ** (-1.0 / n) - 1.0
    den = pd ** (-1.0 / n) - 1.0
    return float(10.0 * np.log10(max(num / den - 1.0, 1e-30)))


# --------------------------------------------------------------------------- #
#  1. 검출기 형상 — S-G(게이트) / S-W(전체 창)
# --------------------------------------------------------------------------- #
def fs_shapes(wf, Rb_span=RB_SPAN_DEFAULT_M, fs=None, M=None, tap_span_m=TAP_SPAN_M,
              Rb_true_m=None, n_range_gate=N_RANGE_GATE, guard_width=DOPPLER_GUARD_WIDTH,
              frame_len=None, prf_hz=None, T_cpi_s=_fss.T_CPI_REF_S,
              wifi_packet_rate=1000.0, pfa=PFA_CELL):
    """자유공간 검출기 **두 형상**(S-G / S-W)의 형상 파라미터를 만든다 (스펙 §5.2, F6).

    챔버값(`experiment_detection.N_RANGE=32, N_TAPS=40`)은 자유공간에서 못 쓴다. 그렇다고 한쪽만
    고르면 게이트(=탐색 없이 얻은 거리)나 전체창(=CPI 당 오경보 수십 건) 중 한쪽 결함을 그대로
    물려받는다 → **둘 다 재고 표로 낸다.**

      S-G : n_range=64, 표적 진리 R_b 중심 게이트. 전이곡선·헤드라인용.
      S-W : Rb_span 전체(예: 6 km). 경험 Pfa·오경보 회계용.
      공통: n_taps = **지연스팬 등가**(F6), CA-CFAR guard/train 은 fixed(2,2)/(6,6) 과
            **분해능셀 등가**(rescell) 두 규약을 **둘 다** 실어 보낸다(F4 이중보고).

    인자
      wf        : waveforms.Waveform (fs_hz·ref_bw_hz·std·mode 를 읽는다)
      Rb_span   : S-W 가 덮을 바이스태틱 거리 스팬[m]
      fs        : 표본율[Hz] (None 이면 wf.fs_hz)
      M         : CPI 프레임 수(=도플러빈 수). **None 이면 물리 반복률에서 자기유도**한다(아래 ★).
      prf_hz    : 기준신호 반복률[Hz]. None 이면 `freespace_scene.prf_hz(wf.std, wf.mode)`.
      T_cpi_s   : CPI 길이[s] (기본 헤드라인 0.1 s)
      Rb_true_m : 주면 S-G 게이트를 그 R_b 중심으로 배치(`range_start_bin`).
      frame_len : CPI 한 프레임의 표본 수(b·블록길이). None 이면 `len(wf.tx)`(b=1). 거리창 상한.

    ★ **M 자기유도**(감사 B2 조치): 스펙 §9 는 `fs_shapes(wf, Rb_span, fs)` 3인자인데 `M` 이 없어
      `n_doppler=None` 이 되고, 그걸 그대로 `false_alarms_per_cpi` 에 넘기면 **예외**가 났다
      (스펙 §9 두 함수의 합성이 깨졌다). 이제 M 을 주지 않으면 F1 물리 규약으로 유도한다:
          `prf = freespace_scene.prf_hz(std, occ)` → `M = M_from_prf(T_cpi, prf)`
      (T_CPI=0.1 s 에서 W1 100 · L1 100 · **G1 5** · G3 20, L2/L3 는 클램프된 2 → 실현불가).

    ⚠⚠ **도플러축 물리성 경고**(감사 A1/[1] — 이 모듈이 혼자 못 고치는 것). RD 커널
      `passive_process.range_doppler` 는 `Lf = len(ref)//M`, `PRF_kernel = fs/Lf` 로 **버퍼에서**
      PRF 를 만든다. 즉 M 은 자유 파라미터가 아니라 프레임 길이에 묶여 있다. report12 식으로
      `np.tile(wf.tx, M)` 로 CPI 를 만들면 실측 PRF 는
          W1 19230.8 Hz(물리 1000, 19.2×) · L1 1000 Hz(1.0× 유일 일치) ·
          **G1 2000 Hz(물리 50, 40×)** · G3 2000 Hz(물리 200, 10×)
      이 된다. 물리 반복률을 실현하려면 프레임을 반복주기 길이로 잡아야 한다
      (`Lf_required = round(fs/prf)`, G1 이면 20 ms = 2.4576 M 샘플, CPI 12.288 M 샘플).
      이 형상 dict 는 그 요구값(`Lf_required`·`Ns_required`·`prf_hz`·`dfd_hz`)을 **실어 보내고**,
      `transfer_by_dopoff`/`calibrate_pfa` 가 진입부에서 커널 PRF 와 대조한다(`prf_check`).
      CPI 를 실제로 만드는 곳(`experiment_freespace_range.stage_threshold`)이 고칠 몫이다.

    반환 {"S_G": {...}, "S_W": {...}} — 각 dict 의 키:
      n_range, range_start_bin, n_taps, n_taps_round, tap_span_m, dr_bin_m,
      oversample_fs_over_bref, n_doppler, n_doppler_valid, n_doppler_source,
      prf_hz, t_cpi_s, dfd_hz, Lf_required, Ns_required, cpi_feasible,
      doppler_rows_left, doppler_axis_degenerate, limit_reason, dopoff_available,
      guard_fixed/train_fixed, guard_rescell/train_rescell, guard/train(=fixed 정본),
      n_train_center_fixed, r3_flag, repo_warnings, role, note

    ⚠ r3_flag: `n_range > n_taps` 는 report4 [R3] 경보 조건이다. report13 은 그것을 **없애지 않고**
      감수한다 — R6(ridge=0)+자유공간(정적 클러터 없음)이면 DPI 는 단일탭이라 완전소거되어
      누설이 ≈0 이기 때문(★스모크 확인). 대신 **경험 Pfa 를 반드시 측정**한다(`calibrate_pfa`).
      저장소 자체 검사기 `passive_process.check_detector_config` 도 이제 호출해
      `repo_warnings` 로 실어 보낸다(감사 #8: 아무도 안 부르던 검사기)."""
    fs = float(fs if fs is not None else wf.fs_hz)
    dr = C0 / fs
    n_taps = _n_taps_for_span(fs, tap_span_m)
    ref_bw = float(getattr(wf, "ref_bw_hz", fs))
    over = fs / max(ref_bw, 1.0)

    # --- 시간축: 물리 반복률 → M (F1). M 을 명시하면 그대로 쓰되 출처를 기록한다. ---
    std = str(getattr(wf, "std", ""))
    occ = str(getattr(wf, "mode", ""))
    prf = None
    if prf_hz is not None:
        prf = float(prf_hz)
    elif std:
        try:
            prf = float(_fss.prf_hz(std, occ, wifi_packet_rate=wifi_packet_rate))
        except Exception:
            prf = None
    if M is not None:
        nd = int(M)
        nd_src = "caller"
    elif prf:
        nd = _fss.M_from_prf(T_cpi_s, prf)
        nd_src = "derived from physical PRF (F1): M = max(2, round(T_cpi*PRF))"
    else:
        nd, nd_src = None, "unknown (no M, no PRF)"

    feas = _fss.cpi_feasibility(T_cpi_s, prf, guard_width) if (prf and nd is not None) else None
    if nd is not None:
        lo, hi, _zd = _submap_rows(nd, None, guard_width)
        nd_valid = int(nd - (hi - lo))
        dopoff_ok, dopoff_bad = feasible_dopoff_bins(nd, (3, 5, 8, 15, 30), guard_width)
    else:
        nd_valid, dopoff_ok, dopoff_bad = None, [], {}

    n_range_w = int(math.ceil(float(Rb_span) / dr))
    if frame_len is None and getattr(wf, "tx", None) is not None:
        frame_len = int(len(wf.tx))                                # b=1 프레임 가정(b>1 이면 caller 가 준다)
    if frame_len:
        n_range_w = min(n_range_w, int(frame_len))                 # 거리창은 프레임 길이를 못 넘는다

    start = 0
    if Rb_true_m is not None:
        b_true = int(round(float(Rb_true_m) / dr))
        start = max(0, b_true - int(n_range_gate) // 2)

    g_fix, t_fix = cfar_guard_bins(wf, fs, mode="fixed")
    g_res, t_res = cfar_guard_bins(wf, fs, mode="rescell")

    warns = []
    if nd is not None:
        try:
            warns = check_detector_config(wf, int(n_range_w), int(n_taps), int(nd),
                                          float(pfa), verbose=False)
        except Exception as e:                                  # 검사기가 죽어도 형상은 나와야 한다
            warns = [f"check_detector_config 실패: {e}"]

    def _mk(name, n_range, start_bin, role, note):
        sub_rows = int(nd_valid) if nd_valid else 0
        return dict(
            name=name, role=role, n_range=int(n_range), range_start_bin=int(start_bin),
            n_taps=int(n_taps), n_taps_round=int(round(float(tap_span_m) / dr)),
            tap_span_m=float(tap_span_m), dr_bin_m=float(dr),
            ref_bw_hz=ref_bw, fs_hz=fs, oversample_fs_over_bref=float(over),
            std=std, occ=occ,
            n_doppler=nd, n_doppler_valid=nd_valid, n_doppler_source=nd_src,
            doppler_guard_width=int(guard_width),
            # --- 시간축 물리(F1) + 커널 요구값(감사 A1) ---
            prf_hz=(float(prf) if prf else None), t_cpi_s=float(T_cpi_s),
            dfd_hz=(float(prf) / nd if (prf and nd) else None),
            Lf_required=(int(round(fs / prf)) if prf else None),
            Ns_required=(int(round(fs / prf)) * int(nd) if (prf and nd) else None),
            cpi_feasible=(bool(feas["feasible"]) if feas else None),
            doppler_rows_left=(int(feas["doppler_rows_left"]) if feas else nd_valid),
            doppler_axis_degenerate=bool(nd_valid is not None and nd_valid <= 0),
            limit_reason=(feas["reason"] if feas else None),
            dopoff_available=list(dopoff_ok), dopoff_infeasible=dict(dopoff_bad),
            guard_fixed=tuple(g_fix), train_fixed=tuple(t_fix),
            guard_rescell=tuple(g_res), train_rescell=tuple(t_res),
            guard=tuple(g_fix), train=tuple(t_fix),
            # 부분맵 중앙 셀에서 `ca_cfar_2d` 가 실제로 쓰는 학습셀 수(가장자리 클리핑 반영, 감사 ⑥)
            n_train_center_fixed=(_n_train_at(sub_rows, int(n_range), sub_rows // 2,
                                              int(n_range) // 2, g_fix, t_fix)
                                  if sub_rows > 0 else None),
            n_train_center_rescell=(_n_train_at(sub_rows, int(n_range), sub_rows // 2,
                                                int(n_range) // 2, g_res, t_res)
                                    if sub_rows > 0 else None),
            ridge_rel=ECA_RIDGE_REL, tol_cell=TOL_CELL,
            r3_flag=bool(n_range > n_taps), repo_warnings=list(warns), note=note)

    return {
        "S_G": _mk("S_G", n_range_gate, start, "transfer curve / headline",
                   "gate centred on true R_b — detector that knows where to look"),
        "S_W": _mk("S_W", n_range_w, 0, "empirical Pfa / false-alarm accounting",
                   f"whole R_b window {Rb_span:.0f} m — searching detector"),
    }


# --------------------------------------------------------------------------- #
#  2. ECA — ridge_rel = 0 정본 (R6)
# --------------------------------------------------------------------------- #
def eca_canceller(ref_cpi, fs, tap_span_m=TAP_SPAN_M, ridge_rel=ECA_RIDGE_REL):
    """자유공간 ECA 소거기 — **ridge_rel=0**(정본) + **지연스팬 등가 n_taps**(F6).

    ★R6 (이번 조사에서 뒤집힌 결정, 스모크로 재확인):
      `ECACanceller` 의 로딩은 `load = 1e-6 + ridge_rel·|R[0]|` 인데 `|R[0]| = Σ|ref|²` 는
      CPI 전체 에너지(≈ N·P_ref, 10^5~10^6 급)다. 따라서 `ridge_rel=1e-6` 은 절대 1e-6 보다
      **5~6 자릿수 큰 대각로딩**이고, 소거깊이를 얕게 만들어 고 DNR(≥100 dB)에서 비-0도플러
      셀로 누설을 만든다. 설계 원안(1e-6)이 아니라 **0 이 정답**이다.
      → 이 함수는 그 정본만 만든다. 다른 ridge 는 `eca_floor_sweep` 의 참조축으로만 쓴다.

    ⚠ 자유공간에서 DPI 는 **단일탭**(0지연·0도플러)이고 정적 클러터는 아예 없다(FS-1 가정).
      60 m 스팬은 DPI 주엽+여유를 덮고, 표적 R_b(수백 m~km)는 그보다 훨씬 밖이라 **표적 자기소거
      위험이 없다**.

    반환: `passive_process.ECACanceller` (자기상관 프리컴퓨트 1회 → 트라이얼마다 .cancel())."""
    n_taps = _n_taps_for_span(fs, tap_span_m)
    return ECACanceller(np.asarray(ref_cpi), n_taps=n_taps, ridge_rel=float(ridge_rel))


def rebuild_residuals(pre, y_echo=None, dpi_signal=None, ridge_rel=ECA_RIDGE_REL,
                      tap_span_m=TAP_SPAN_M, fs=None, inplace=False):
    """**정본 ECA(ridge_rel=0·지연등가 n_taps)로 잔차를 다시 만든다** (감사 [2]/③ 조치).

    ⚠ 왜 필요한가 — R6 이 정본으로 세운 `ridge_rel=0` 이 **데이터 경로에 도달하지 못했다.**
      `experiment_detection.Precomputed.__init__`(src/experiment_detection.py:189)에는
      `ECACanceller(ref_cpi, n_taps=N_TAPS, ridge_rel=1e-4)` 가 **리터럴로** 박혀 있다.
      스펙 §9 가 허용한 "인스턴스 생성 전 전역상수 속성 교체"는 `N_RANGE/N_TAPS/DPI_AMP`
      (모듈 전역)에만 통하고 이 값에는 안 통한다. 그런데 `calibrate_pfa`·`transfer_by_dopoff`
      는 `pre.resid_dpi`/`pre.resid_echo` 를 **그대로** 소비한다 → 정본 MC 가 R6 이 기각한
      1e-4 잔차 위에서 돌게 된다.
      ★측정(LTE 기준신호·지연등가 n_taps=7): 소거깊이 ridge 0 = **−193.5 dB** vs 1e-4 = **−70.4 dB**.
      자유공간 헤드라인 DNR 75.4 dB(L=500)에서 1e-4 잔차는 잡음바닥을 약 **+5 dB**,
      L=100(DNR≈89 dB)에서는 약 **+18 dB** 들어올린다.

    두 가지 모드
      ① **정확(권장)** — `y_echo`(ECA 전 표적 에코 CPI)·`dpi_signal`(ECA 전 직접파 CPI)을 주면
         정본 소거기로 처음부터 다시 소거한다. `experiment_freespace_range` 는 Sionna 체인에서
         raw 신호를 갖고 있으므로 이 경로를 써라.
      ② **재소거(근사)** — 안 주면 기존 잔차에 정본 소거기를 **한 번 더** 건다. DPI 는 통째로
         기준 부분공간 안에 있어 사실상 완전소거되지만, 표적 에코는 소거를 두 번 겪어
         0-도플러 능선 근처에서 **약간 더 깎인다**. `eca_rebuild_method` 에 근사임을 남긴다.

    반환: `pre`(또는 얕은 복사본)에 다음 필드가 붙은 것 —
      `eca_ridge_rel`, `eca_n_taps`, `eca_tap_span_m`, `eca_rebuild_method`, `eca_cancel_depth_db`.
      이 필드가 있어야 `calibrate_pfa`/`transfer_by_dopoff` 의 출처 검사가 통과한다."""
    import copy
    fs = float(fs if fs is not None else _pre_fs(pre))
    M = int(pre.M)
    ref_frame = np.asarray(pre.ref_frame)
    ref_cpi = np.tile(ref_frame, M)
    can = eca_canceller(ref_cpi, fs, tap_span_m=tap_span_m, ridge_rel=ridge_rel)

    out = pre if inplace else copy.copy(pre)
    if y_echo is not None and dpi_signal is not None:
        out.resid_echo = can.cancel(np.asarray(y_echo)).astype(np.complex64)
        out.resid_dpi = can.cancel(np.asarray(dpi_signal)).astype(np.complex64)
        method = "exact (canonical ECA applied to raw echo/DPI)"
    else:
        out.resid_echo = can.cancel(np.asarray(pre.resid_echo)).astype(np.complex64)
        out.resid_dpi = can.cancel(np.asarray(pre.resid_dpi)).astype(np.complex64)
        method = ("approximate (second ECA pass on existing residuals; DPI fully removed, "
                  "target echo takes one extra self-cancellation)")

    d_only = can.cancel(ref_cpi)
    depth = float(10 * np.log10((np.mean(np.abs(d_only) ** 2) + 1e-300)
                                / (np.mean(np.abs(ref_cpi) ** 2) + 1e-300)))
    out.eca_ridge_rel = float(ridge_rel)
    out.eca_n_taps = int(can.n_taps)
    out.eca_tap_span_m = float(tap_span_m)
    out.eca_rebuild_method = method
    out.eca_cancel_depth_db = depth
    if hasattr(out, "_t"):
        try:                                          # GPU 사본 무효화(다시 올리게)
            delattr(out, "_t")
        except Exception:
            pass
    return out


def check_eca_provenance(pre, shape=None, strict=False):
    """(감사 [2]/③) 소비 직전에 **이 잔차가 어떤 ECA 로 만들어졌는지** 확인한다.

    `rebuild_residuals()` 가 붙여둔 `pre.eca_ridge_rel` 을 읽는다. 없으면 출처 불명이고,
    저장소 기본 경로(`experiment_detection.Precomputed`)는 **1e-4 하드코딩**이므로 그렇게 경고한다.
    `strict=True` 면 raise. 반환 dict 는 그대로 결과 meta 에 실린다."""
    want = float((shape or {}).get("ridge_rel", ECA_RIDGE_REL))
    got = getattr(pre, "eca_ridge_rel", None)
    ok = (got is not None and abs(float(got) - want) <= 1e-15)
    msg = None
    if got is None:
        msg = ("pre 에 eca_ridge_rel 이 없다 — 출처 불명. experiment_detection.Precomputed 는 "
               "ridge_rel=1e-4 가 리터럴로 박혀 있어(★소거깊이 −70 dB, 정본 −193 dB) R6 정본이 "
               "아니다. freespace_detect.rebuild_residuals(pre, ...) 를 먼저 부를 것.")
    elif not ok:
        msg = f"잔차의 ridge_rel={got} 이 정본 {want} 과 다르다."
    if msg:
        if strict:
            raise ValueError(msg)
        print(f"⚠ ECA 출처 경고: {msg}")
    return dict(ok=bool(ok), ridge_rel_used=(float(got) if got is not None else None),
                ridge_rel_expected=want, n_taps=getattr(pre, "eca_n_taps", None),
                cancel_depth_db=getattr(pre, "eca_cancel_depth_db", None),
                rebuild_method=getattr(pre, "eca_rebuild_method", None), warning=msg)


def check_kernel_prf(pre, shape, mode="warn", tol_rel=1e-3):
    """(감사 A1/[1]) **RD 커널이 실제로 주는 PRF** 와 형상이 선언한 물리 PRF 를 대조한다.

    `passive_process.range_doppler` 는 `Lf = len(ref)//M`, `PRF_kernel = fs/Lf` 로 PRF 를
    **버퍼에서** 만든다 — M 은 자유 파라미터가 아니라 프레임 길이에 묶여 있다. report12 식
    `np.tile(wf.tx, M)` CPI 는 ★W1 19.2× · L1 1.0× · **G1 40×** · G3 10× 로 물리 반복률과
    어긋나고, 그 상태에서 나온 도플러 빈폭·무모호 범위·blind 비율은 물리가 아니라 버퍼 규약의
    산물이다(F1 이 폐기한 report12 단순화로 되돌아간다).

    `mode`: "warn"(기본 — 경고 출력 + dict 기록) / "raise" / "off".
    ⚠ 기본이 "warn" 인 이유: CPI 를 만드는 코드는 이 모듈이 아니라
      `experiment_freespace_range.stage_threshold` 다. 프레임을 반복주기 길이(제로패딩)로 잡아
      물리 CPI 를 만든 뒤에는 **"raise" 로 올려** 회귀를 잠글 것.
    반환 dict 는 `meta.cpi` 로 그대로 실린다 — `doppler_axis_physical` 이 핵심 플래그다."""
    fs = _pre_fs(pre)
    M = int(pre.M)
    Ns = int(getattr(pre, "Ns", len(getattr(pre, "resid_dpi", []))))
    Lf = Ns // M if M else 0
    prf_k = (fs / Lf) if Lf else float("nan")
    prf_p = (shape or {}).get("prf_hz")
    out = dict(prf_kernel_hz=float(prf_k), prf_physical_hz=(float(prf_p) if prf_p else None),
               M=M, Lf=int(Lf), Ns=int(Ns), fs_hz=float(fs),
               dfd_kernel_hz=(float(prf_k / M) if M else None),
               dfd_physical_hz=((float(prf_p) / M) if (prf_p and M) else None),
               t_cpi_kernel_s=(float(Ns / fs) if fs else None),
               Lf_required=(shape or {}).get("Lf_required"),
               doppler_axis_physical=None, warning=None)
    if not prf_p or str(mode).lower() == "off":
        return out
    rel = abs(prf_k / float(prf_p) - 1.0)
    out["prf_ratio_kernel_over_physical"] = float(prf_k / float(prf_p))
    out["doppler_axis_physical"] = bool(rel <= tol_rel)
    if rel > tol_rel:
        msg = (f"커널 PRF {prf_k:.1f} Hz 가 물리 반복률 {float(prf_p):.1f} Hz 의 "
               f"{prf_k / float(prf_p):.1f}배다 — 도플러 빈폭 {prf_k / M:.2f} Hz vs 물리 "
               f"{float(prf_p) / M:.2f} Hz. CPI 프레임을 Lf={out['Lf_required']} 샘플"
               f"(=반복주기)로 만들어야 F1 이 실현된다.")
        out["warning"] = msg
        if str(mode).lower() == "raise":
            raise ValueError(msg)
        print(f"⚠ 도플러축 경고: {msg}")
    return out


# --------------------------------------------------------------------------- #
#  3. CFAR 가드 — fixed / rescell 이중규약 (F4)
# --------------------------------------------------------------------------- #
def cfar_guard_bins(wf, fs=None, mode="fixed", train=TRAIN_FIXED, guard_d=GUARD_FIXED[0]):
    """CA-CFAR 의 (guard, train) 을 **두 규약**으로 준다 (F4).

    왜 두 개인가: 기준신호 대역 B_ref 가 fs 보다 훨씬 좁으면 거리축이 과표본돼 **표적 주엽이
    여러 빈에 걸친다**. ★5G SSB(G1)는 fs/B_ref=17.1 → 주엽 ≈18빈이라 고정 guard (2,2) 로는
    표적이 자기 훈련셀에 들어가 **자기가림**(self-masking)이 생긴다.
      · `fixed`   : (2,2)/(6,6) — report01~12 와 같은 규약. 리포트 간 비교가능성.
      · `rescell` : 거리 guard = `ceil(0.5·fs/B_ref) + 2` — 분해능셀 등가. 공정성.
        (★G1: ceil(0.5·17.07)+2 = 11 → 스펙 meta `G1_rescell:[11,2]` 재현)
    도플러축 guard 는 두 규약 모두 2 로 둔다(Hann 주엽 ±1빈 + 여유). 훈련창은 (6,6) 유지.
    ⚠ 튜플 순서는 **`ca_cfar_2d` 규약 (도플러, 거리)** 다 — 스펙 meta 의 `G1_rescell:[11,2]` 는
      [거리, 도플러] 표기라 여기서는 `(2, 11)` 로 나온다(같은 값, 순서만 다름).

    ⚠ Pd 는 **측정**이므로 자기가림은 SNR90 에 이미 흡수된다 — 쟁점은 '어느 규약으로 쟀는가'다.
      그래서 스펙은 두 규약의 SNR90 **병기**를 요구한다.

    반환: `((guard_d, guard_r), (train_d, train_r))` — 그대로 `ca_cfar_2d(rd, guard=…, train=…)`."""
    fs = float(fs if fs is not None else wf.fs_hz)
    m = str(mode).lower()
    if m == "fixed":
        return (tuple(GUARD_FIXED), tuple(train))
    if m == "rescell":
        ref_bw = float(getattr(wf, "ref_bw_hz", fs))
        over = fs / max(ref_bw, 1.0)
        gr = int(math.ceil(0.5 * over)) + 2
        return ((int(guard_d), gr), tuple(train))
    raise ValueError(f"mode 는 'fixed' 또는 'rescell' — 받은 값 {mode!r}")


# --------------------------------------------------------------------------- #
#  4. 가드행 제거 부분맵 CFAR (A5)
# --------------------------------------------------------------------------- #
def _cfar_excl_rows(rd, f_d=None, width=DOPPLER_GUARD_WIDTH, guard=GUARD_FIXED,
                    train=TRAIN_FIXED, pfa=PFA_CELL, return_extra=False):
    """0-도플러 가드행을 **훈련셀에서도 배제**한 CA-CFAR (A5).

    ★확인: `passive_process.doppler_guard_mask` 는 주석에 "이 함수는 검출 마스크만 다룬다"고
    명시돼 있다 — `also_exclude_from_training=True` 를 넘겨도 훈련셀은 안 바뀐다. 뜨거운 zd±1 행을
    검출에서만 빼면 이웃 행의 잡음추정이 부풀어 문턱이 과하게 올라간다(과보정, 배율 0.65~0.82).
    또 '가드행을 열 중앙값으로 치환'하는 우회는 지수분포 median=0.693·mean 이라 훈련평균을
    **1.59 dB 낮춰** 문턱을 내린다(반대 방향 오류).
      → 정답은 **가드행을 물리적으로 제거한 부분맵에 `ca_cfar_2d` 를 그대로 적용**하는 것.

    ⚠ 이음매(seam): 행을 빼고 이어붙이면 lo−1 행과 hi 행이 부분맵에서 인접해진다. CFAR 훈련창이
      그 이음매를 가로지르므로 **도플러 상관구조가 국소적으로 바뀐다**. 그래서 문턱을 이론값으로
      믿지 않고 `calibrate_pfa` 로 **경험 Pfa 를 재측정**한다(스펙 §5.2·설계 §1.5 규약).

    ⚠ **퇴화 입력은 조용히 죽지 않는다**(감사 A2/⑦). M ≤ width 면 가드가 도플러축을 통째로
      먹어 남는 행이 0개가 된다(★L2/L3 는 T_CPI 격자 5점 중 4점에서 M=2 → 0행). 예전 구현은
      그 경우 **예외도 경고도 없이 전부 False** 를 돌려줬다 — SNR 30 dB 에서도 Pd=0 이 나오고
      아무도 이유를 모른다. 이제 raise 한다. 상위 계층은 `fs_shapes(...)["doppler_axis_degenerate"]`
      나 `freespace_scene.cpi_feasibility()` 로 **미리** 걸러 회색 라벨을 달아야 한다.

    인자 rd: |RD| (도플러, 거리). f_d: 도플러축(없으면 fftshift 중앙을 0-도플러로 본다).
    반환: 기본은 **전체맵 크기의 검출마스크**(가드행은 항상 False).
          `return_extra=True` 면 `(det, thr, noise, (lo, hi))` — thr 은 진폭스케일, 가드행은 inf."""
    rd = np.asarray(rd)
    nd, nr = rd.shape
    lo, hi, _zd = _submap_rows(nd, f_d, width)
    keep = np.r_[np.arange(0, lo), np.arange(hi, nd)]
    if keep.size == 0:
        raise ValueError(
            f"0-도플러 가드(width={width})가 도플러축(M={nd})을 통째로 먹었다 — 남는 행 0개. "
            f"이 모드는 이 T_CPI 에서 검출 자체가 정의되지 않는다(limit='doppler_axis_degenerate'). "
            f"freespace_scene.cpi_feasibility() 로 먼저 걸러 회색 처리할 것.")
    sub = rd[keep, :]
    det_s, thr_s, noise_s = ca_cfar_2d(sub, guard=tuple(guard), train=tuple(train), pfa=pfa)
    det = np.zeros_like(rd, dtype=bool)
    det[keep, :] = det_s
    if not return_extra:
        return det
    thr = np.full_like(rd, np.inf, dtype=float)
    noise = np.zeros_like(rd, dtype=float)
    thr[keep, :] = thr_s
    noise[keep, :] = noise_s
    return det, thr, noise, (lo, hi)


def _cfar_excl_rows_batch(rd, width=DOPPLER_GUARD_WIDTH, guard=GUARD_FIXED,
                          train=TRAIN_FIXED, pfa=PFA_CELL):
    """`_cfar_excl_rows` 의 **배치(torch) 판** — 커널은 `detection_gpu.cfar_batch` 그대로.

    rd (B, nd, nr) → `(det_sub, thr_sub, rd_sub, (lo, hi))` 로, **부분맵 좌표**에서 돌려준다
    (numpy 판과 동일하게 가드행을 물리적으로 제거한 뒤 CFAR). 몬테카를로는 부분맵 좌표로
    표적셀을 찾으므로 `_row_to_submap` 로 행을 옮겨 쓴다."""
    import torch
    from detection_gpu import cfar_batch
    nd = rd.shape[1]
    lo, hi, _ = _submap_rows(nd, None, width)
    if nd - (hi - lo) <= 0:                      # 감사 A2 — numpy 판과 같은 규약으로 loud fail
        raise ValueError(
            f"0-도플러 가드(width={width})가 도플러축(M={nd})을 통째로 먹었다 — 남는 행 0개. "
            f"limit='doppler_axis_degenerate' 로 회색 처리할 셀이다.")
    sub = torch.cat([rd[:, :lo, :], rd[:, hi:, :]], dim=1)
    det, thr = cfar_batch(sub, guard=tuple(guard), train=tuple(train), pfa=pfa)
    return det, thr, sub, (lo, hi)


# --------------------------------------------------------------------------- #
#  5. 검출 판정 — 전역 argmax 가 아니라 표적 근방 (R3§2 / S4)
# --------------------------------------------------------------------------- #
def detect_target_neighborhood(rd, th, di_true, ri_true, tol=TOL_CELL):
    """**표적 근방 ±tol 셀에서 문턱을 넘었는가** — report13 의 검출 정의 (R3§2).

    ★확인(report12): `Precomputed.di_true/ri_true` 는 무잡음 RD 의 argmax 이고, hit 판정은
    `found & |di−di_true|≤2 & |ri−ri_true|≤2` 였다. 즉 **전역 최댓값이 표적 근방일 것**을
    요구한다 — 강한 오경보 하나가 표적보다 크면 표적이 문턱을 넘었어도 미검출로 센다. 그건
    검출(detection)이 아니라 '최강피크 동정(identification)'이다.
      → report13 정본: `det[표적근방].any()`. 전역최대 규약은 caveat 으로만 병기한다.

    인자
      rd  : |RD| — (nd, nr) 또는 배치 (B, nd, nr). numpy/torch 둘 다 받는다.
      th  : 같은 스케일(진폭)의 문턱 — 배열(브로드캐스트 가능) 또는 스칼라.
            `ca_cfar_2d`/`cfar_batch` 의 두 번째 반환값(=sqrt(전력문턱))을 그대로 넣으면 된다.
      di_true, ri_true : 표적 셀(도플러행, 거리빈). **rd 와 같은 좌표계**여야 한다
            (가드행 제거 부분맵을 쓴다면 `_row_to_submap` 으로 옮긴 행을 줄 것).
    반환: 2D 면 bool, 배치면 (B,) bool 배열(입력이 torch 면 torch bool 텐서)."""
    nd, nr = rd.shape[-2], rd.shape[-1]
    d0, d1 = max(0, int(di_true) - int(tol)), min(nd, int(di_true) + int(tol) + 1)
    r0, r1 = max(0, int(ri_true) - int(tol)), min(nr, int(ri_true) + int(tol) + 1)
    if d0 >= d1 or r0 >= r1:
        raise ValueError(f"표적 근방이 맵 밖이다: di={di_true} ri={ri_true} map=({nd},{nr})")
    if _is_torch(rd):
        sub = rd[..., d0:d1, r0:r1]
        tsub = th[..., d0:d1, r0:r1] if _is_torch(th) and th.dim() >= 2 else th
        hit = (sub > tsub).flatten(start_dim=-2).any(dim=-1)
        return hit if rd.dim() == 3 else bool(hit.item())
    rd = np.asarray(rd)
    sub = rd[..., d0:d1, r0:r1]
    tsub = np.asarray(th)[..., d0:d1, r0:r1] if np.ndim(th) >= 2 else th
    hit = (sub > tsub).any(axis=(-2, -1))
    return bool(hit) if rd.ndim == 2 else hit


# --------------------------------------------------------------------------- #
#  6. 경험 Pfa 재교정 (설계 §1.5 — 챔버 표는 안 쓴다)
# --------------------------------------------------------------------------- #
def calibrate_pfa(pre, shape, K_pfa=20000, pfa_target=PFA_CELL, sigma=1.0,
                  max_iter=4, tol_log10=0.05, seed=90210, batch=None, device=None,
                  prf_check="warn", eca_strict=False):
    """자유공간 형상에서 **경험 Pfa 를 측정해 명목 Pfa 를 재교정**한다.

    ★`passive_process.PFA_CALIBRATION` 표는 **쓰지 않는다** — 코드 주석이 "운용 형상: DPI+ECA,
    **챔버 거리창**, guard 2x2/train 6x6" 전용이라고 명시한다. 자유공간은 거리창·오버샘플·
    가드규약이 전부 다르므로 형상마다 다시 재는 게 맞다(챔버 표는 참조로만 병기 → `chamber_ref`).

    왜 경험 Pfa 가 명목과 다른가(report4 [E1]): slow-time Hann 이 도플러 인접셀을(ρ≈0.46),
    B_ref<fs 오버샘플이 거리 인접셀을 상관시켜 CA-CFAR 의 '훈련셀 독립' 가정이 깨진다.

    방법: 표적 없는 트라이얼(`resid_dpi + 잡음`)에서 `_cfar_excl_rows_batch` 로 검출을 세고
      Pfa_emp = FA / (유효셀 수) 를 잰다. 유효셀 = 가드행 제거 부분맵의 **전 셀**(분모에 제외셀을
      넣으면 저편향된다 — report12 가 밟았던 함정). 이어 log-log 에서 `emp ≈ c·nominal` 로 보고
      nominal ← nominal·(target/emp) 를 최대 `max_iter` 번 반복(할선법).

    인자 pre: `experiment_detection.Precomputed` 또는 같은 필드를 가진 오리
              (`resid_dpi`, `ref_frame`, `M`, `Ns`, `wf`/`fs_hz`).
         shape: `fs_shapes()` 의 한 항목(n_range·range_start_bin·guard·train 을 읽는다).
    반환 dict: nominal(=교정된 명목), empirical, target, probes[…], n_cells, K_pfa, chamber_ref …"""
    import torch
    from detection_gpu import rd_batch

    dev = _dev_of(pre, device)
    fs = _pre_fs(pre)
    M = int(pre.M)
    Ns = int(getattr(pre, "Ns", len(pre.resid_dpi)))
    n_range = int(shape["n_range"])
    start = int(shape.get("range_start_bin", 0))
    guard = tuple(shape.get("guard", GUARD_FIXED))
    train = tuple(shape.get("train", TRAIN_FIXED))
    width = int(shape.get("doppler_guard_width", DOPPLER_GUARD_WIDTH))
    batch = int(batch or _batch_size(Ns))
    # 소비 직전 두 가지 출처검사(감사 [2]/A1) — 결과는 반환 dict 에 실려 JSON 으로 나간다
    eca_prov = check_eca_provenance(pre, shape, strict=eca_strict)
    prf_info = check_kernel_prf(pre, shape, mode=prf_check)

    dpi = torch.as_tensor(np.asarray(pre.resid_dpi, np.complex64), device=dev)
    ref = torch.as_tensor(np.asarray(pre.ref_frame, np.complex64), device=dev)
    g = torch.Generator(device=dev).manual_seed(int(seed))

    def _measure(nominal):
        fa = 0; cells = 0; done = 0
        while done < K_pfa:
            b = int(min(batch, K_pfa - done))
            nz = ((torch.randn(b, Ns, generator=g, device=dev)
                   + 1j * torch.randn(b, Ns, generator=g, device=dev))
                  * (float(sigma) / np.sqrt(2))).to(torch.complex64)
            surv = dpi[None, :] + nz
            rd = rd_batch(surv, ref, M, start + n_range)[:, :, start:]
            det, _thr, _sub, _ = _cfar_excl_rows_batch(rd, width=width, guard=guard,
                                                       train=train, pfa=nominal)
            fa += int(det.sum().item()); cells += int(det.numel()); done += b
        return fa / max(cells, 1), fa, cells

    nominal = float(pfa_target)
    probes = []
    emp, fa, cells = _measure(nominal)
    probes.append(dict(nominal=nominal, empirical=emp, n_fa=fa, n_cells=cells))
    for _ in range(int(max_iter) - 1):
        if emp <= 0 or abs(np.log10(max(emp, 1e-12) / pfa_target)) <= tol_log10:
            break
        nominal = float(np.clip(nominal * (pfa_target / emp), 1e-12, 0.5))
        emp, fa, cells = _measure(nominal)
        probes.append(dict(nominal=nominal, empirical=emp, n_fa=fa, n_cells=cells))

    return dict(shape=shape.get("name"), mode=f"{shape.get('std','')}{shape.get('occ','')}",
                target=float(pfa_target), nominal=float(nominal), empirical=float(emp),
                ratio_emp_over_nominal=float(emp / nominal) if nominal > 0 else None,
                fs_hz=float(fs), eca_provenance=eca_prov, cpi=prf_info,
                n_fa=int(fa), n_cells=int(cells), K_pfa=int(K_pfa), probes=probes,
                converged=bool(emp > 0 and abs(np.log10(max(emp, 1e-12) / pfa_target)) <= tol_log10),
                guard=list(guard), train=list(train), doppler_guard_width=width,
                training_exclusion="submap CFAR (_cfar_excl_rows)",
                chamber_ref=PFA_CALIBRATION.get(str(shape.get("std", "")).lower()),
                note="chamber PFA_CALIBRATION table is reference only (chamber range window)")


# --------------------------------------------------------------------------- #
#  7. ECA 수치바닥 스윕 (R6 증거 — F14(b))
# --------------------------------------------------------------------------- #
def eca_floor_sweep(ref, dnr_grid=(80.0, 100.0, 120.0), ridge_list=(0.0, 1e-6, 1e-4),
                    ntaps_list=None, M=8, n_range=256, fs=None, seed=0,
                    width=DOPPLER_GUARD_WIDTH, tap_span_m=TAP_SPAN_M):
    """**ECA 의 수치바닥**을 잰다 — ridge × n_taps × DNR 격자 (R6 의 증거).

    측정량: 같은 잡음 실현에서
        resid = cancel(dpi_amp·ref + n),   base = cancel(n)
      의 |RD|² 를 **비-0도플러 셀**에서 비교한 med/p99/max [dB]. 0 dB = DPI 잔류가 잡음에
      묻혀 보이지 않음(=사실상 이상적 소거), 양수 = 잔류가 셀로 **새어나옴**.

    ★R6: `ridge_rel` 은 **상대** 로딩(`load = 1e-6 + ridge_rel·|R[0]|`)이고 `|R[0]|=Σ|ref|²` 는
      CPI 전체 에너지다. 그래서 1e-6·1e-4 는 절대 1e-6 보다 몇 자릿수 큰 로딩이 되고, 고 DNR 에서
      소거깊이가 모자라 누설한다. **0 이 정본**이라는 것을 이 함수가 매번 재확인한다.

    dpi_amp 규약: 잡음전력 1 기준으로 `DNR = 10log10(dpi_amp²·mean|ref|²)` 가 되도록 잡는다.
    반환 dict: dnr_db / ridge / n_taps / configs[{ridge,n_taps,cancel_depth_db}] /
               resid_med_db·resid_p99_db·resid_max_db (config × dnr) / clean_ridge0"""
    ref = np.asarray(ref)
    fs = float(fs if fs is not None else 1.0)
    if ntaps_list is None:
        ntaps_list = (_n_taps_for_span(fs, tap_span_m),) if fs > 1 else (64,)
    M = int(M)
    Lf = len(ref) // M
    n_range = int(min(n_range, Lf))
    p_ref = float(np.mean(np.abs(ref) ** 2))

    rng = np.random.default_rng(int(seed))
    noise = ((rng.standard_normal(len(ref)) + 1j * rng.standard_normal(len(ref)))
             / np.sqrt(2)).astype(np.complex128)          # 단위전력 잡음(같은 실현 재사용)

    _, f_d0, _ = range_doppler(noise, ref, fs, M, n_range=n_range)
    lo, hi, _ = _submap_rows(M, f_d0, width)
    keep = np.r_[np.arange(0, lo), np.arange(hi, M)]

    configs, med, p99, mx = [], [], [], []
    for ridge in ridge_list:
        for nt in ntaps_list:
            can = ECACanceller(ref, n_taps=int(nt), ridge_rel=float(ridge))
            d_only = can.cancel(ref)                       # 소거깊이(잡음 없이, dpi_amp=1)
            depth = 10 * np.log10((np.mean(np.abs(ref) ** 2) + 1e-300)
                                  / (np.mean(np.abs(d_only) ** 2) + 1e-300))
            base = can.cancel(noise)
            _, _, rd_b = range_doppler(base, ref, fs, M, n_range=n_range)
            pb = (rd_b[keep, :] ** 2)
            row_med, row_p99, row_mx = [], [], []
            for dnr in dnr_grid:
                amp = 10 ** (float(dnr) / 20.0) / np.sqrt(max(p_ref, 1e-300))
                res = can.cancel(amp * ref + noise)
                _, _, rd_r = range_doppler(res, ref, fs, M, n_range=n_range)
                pr = (rd_r[keep, :] ** 2)
                row_med.append(float(10 * np.log10((np.median(pr) + 1e-300) /
                                                   (np.median(pb) + 1e-300))))
                row_p99.append(float(10 * np.log10((np.percentile(pr, 99) + 1e-300) /
                                                   (np.percentile(pb, 99) + 1e-300))))
                row_mx.append(float(10 * np.log10((pr.max() + 1e-300) / (pb.max() + 1e-300))))
            configs.append(dict(ridge=float(ridge), n_taps=int(nt),
                                cancel_depth_db=float(-depth)))
            med.append(row_med); p99.append(row_p99); mx.append(row_mx)

    i0 = [i for i, c in enumerate(configs) if c["ridge"] == 0.0]
    clean0 = bool(all(max(p99[i]) <= 0.5 for i in i0)) if i0 else None
    return dict(dnr_db=[float(x) for x in dnr_grid], ridge=[float(r) for r in ridge_list],
                n_taps=[int(t) for t in ntaps_list], M=M, n_range=n_range,
                configs=configs, resid_med_db=med, resid_p99_db=p99, resid_max_db=mx,
                clean_ridge0=clean0, doppler_guard_width=int(width),
                metric="non-zero-doppler |RD|^2 vs noise-only, same noise realisation [dB]",
                canonical="ridge_rel=0 (R6)")


# --------------------------------------------------------------------------- #
#  8. 오경보 회계 — 빈이 아니라 분해능셀 (F7)
# --------------------------------------------------------------------------- #
def false_alarms_per_cpi(shape, mode=None, pfa=PFA_CELL, doppler_convention="valid",
                         doppler_over=1.0):
    """CPI 당 기대 오경보 수를 **빈 기준(참고)** 과 **분해능셀 기준(정본)** 둘로 낸다 (F7).

    ★왜 뒤집히는가: 셀당 Pfa 를 거리빈 수에 곱하면 **오버샘플이 큰 파형이 벌을 받는다.**
    5G SSB 는 fs/B_ref=17.1 이라 거리빈이 17배 촘촘할 뿐 **독립 분해능셀 수는 그만큼 적다.**
    빈 기준으로는 G1 이 최악인데 분해능셀 기준으로는 **최선**이다. 정본은 후자.

    ⚠⚠ **도플러 행수 규약이 정본을 가른다**(감사 B3/⑤/#7 — 예전 `or` 폴백 버그 포함).
      · `"valid"`(**정본**) : `n_doppler_valid = M − 가드행` — CFAR 가 **실제로 훑는 부분맵** 행수.
      · `"full"`            : `n_doppler = M` — 스펙 §10 의 ★값이 이 규약이다.
      예전 코드는 `shape.get("n_doppler_valid") or shape.get("n_doppler")` 였는데
      **`n_doppler_valid == 0` 이 falsy** 라 M=2(L2/L3)에서 조용히 전체 2행으로 되돌아가
      "도플러축이 없는 모드"에 FA 0.123 을 보고했다. 이제 `is not None` 로 고르고, 규약을
      인자로 노출해 결과 dict 에 `n_doppler_convention` 으로 박는다.

    ⚠ 스펙 §10 ★값(W1 16.0/15.3 · L1 6.1/3.6 · G1 49.2/2.88)은 도플러 행수 **100/100/200**
      에서 나온 값이다. G1 의 200 은 F1 이전(report12 타일링 M=112~200) 규약이라 **F1 정본
      (M=5)과 양립하지 않는다** — 스펙 내부 모순이며, 정본 배관으로는 재현되지 않는다.
      W1/L1 의 15.54 vs 16.0 차이는 규약(valid=M−3 vs full=M) 탓이다.
      `spec_reference` 필드에 그 사실과 두 규약 값을 **함께** 실어 보낸다(날조 금지).

    ⚠ 도플러축 오버샘플(감사 C3, 정직표기): 여기서는 도플러축을 오버샘플하지 않는다고 본다
      (`doppler_over=1.0`). 실제로는 slow-time Hann 주엽이 ★1.44빈(−3 dB 폭)이라 도플러축도
      1.4~2배 상관돼 있다 → 분해능셀 FA 는 전 모드 공통으로 그만큼 **과대**다(순위는 불변).
      필요하면 `doppler_over=1.44` 로 감도패널을 낼 것.

    인자 shape: `fs_shapes()` 항목(n_range·n_doppler(_valid)·oversample_fs_over_bref).
         mode : 라벨(예 'G1'). 계산에는 안 쓰고 결과에 실어 보낸다(JSON 키 대응).
    반환 dict: false_alarms_per_cpi_bins / _rescell, n_cells_bins, n_cells_rescell, …"""
    n_range = int(shape["n_range"])
    nd_full = shape.get("n_doppler")
    nd_valid = shape.get("n_doppler_valid")
    conv = str(doppler_convention).lower()
    nd = nd_valid if conv == "valid" else nd_full
    if nd is None:
        nd = nd_full if conv == "valid" else nd_valid          # 한쪽만 있으면 그거라도
    if nd is None:
        raise ValueError("shape 에 n_doppler(또는 n_doppler_valid)가 없다 — "
                         "fs_shapes(…) 가 M 을 유도하지 못했다(std/mode/PRF 확인)")
    if int(nd) <= 0:
        raise ValueError(
            f"유효 도플러행이 {int(nd)}개다(M={nd_full}, 가드 {shape.get('doppler_guard_width')}) — "
            f"이 모드는 이 T_CPI 에서 검출축이 없다(limit='doppler_axis_degenerate'). "
            f"오경보 회계를 내지 말고 회색 처리할 것.")
    over = float(shape.get("oversample_fs_over_bref", 1.0)) * float(doppler_over)
    cells_bins = int(nd) * n_range
    fa_bins = float(pfa) * cells_bins

    def _pair(n):
        c = int(n) * n_range
        return dict(n_doppler=int(n), n_cells_bins=c, fa_bins=float(pfa) * c,
                    fa_rescell=float(pfa) * c / max(over, 1e-9))

    return dict(shape=shape.get("name"), mode=mode, pfa_cell=float(pfa),
                n_doppler=int(nd), n_doppler_convention=conv,
                n_doppler_full=(int(nd_full) if nd_full else None),
                n_doppler_valid=(int(nd_valid) if nd_valid is not None else None),
                n_range=int(n_range),
                n_cells_bins=int(cells_bins), false_alarms_per_cpi_bins=float(fa_bins),
                cells_per_rescell_range=float(over), doppler_over=float(doppler_over),
                n_cells_rescell=float(cells_bins / max(over, 1e-9)),
                false_alarms_per_cpi_rescell=float(fa_bins / max(over, 1e-9)),
                by_convention={"full": _pair(nd_full) if nd_full else None,
                               "valid": _pair(nd_valid) if nd_valid else None},
                canonical="rescell x n_doppler_valid",
                spec_reference="REPORT13_SPEC §10 star values (W1 16.0/15.3, L1 6.1/3.6, "
                               "G1 49.2/2.88) assume n_doppler = 100/100/200 (FULL rows, and "
                               "G1=200 predates F1 M=5) — NOT reproducible from the F1 pipeline; "
                               "spec-internal contradiction, recorded not fabricated",
                note="bins column is reference only (F7); doppler axis assumed non-oversampled "
                     "(Hann mainlobe is 1.44 bins -> rescell FA is ~1.4x optimistic, rank unchanged)")


# --------------------------------------------------------------------------- #
#  9. 전이곡선 — 도플러 오프셋 축 (R3§1)
# --------------------------------------------------------------------------- #
def transfer_by_dopoff(pre, dopoff_bins=(3, 5, 8, 15, 30), K=4000, snr_grid_db=None,
                       shape=None, N=1, pfa=PFA_CELL, seed=7000, canceller=None,
                       k_pfa=0, batch=None, device=None, ri_true=None, n_noise_reps=3,
                       prf_check="warn", eca_strict=False, skip_infeasible=True):
    """Pd(SNR) **전이곡선을 도플러 오프셋마다** 잰다 (R3§1).

    왜 한 곡선으로는 안 되는가: 표적이 0-도플러 능선에서 3빈 떨어졌을 때와 30빈 떨어졌을 때
    검출기가 보는 것이 다르다. ECA 는 0-도플러 부분공간을 지우므로 **능선 근처의 표적은 자기도
    조금 깎이고**, CFAR 훈련셀도 능선의 영향을 받는다. 하나의 전이곡선을 도플러 위치와 무관하게
    재사용하면 헤딩 커버리지 적분에서 **연성 블라인드(soft blind)** 구간을 통째로 놓친다.
      → `dopoff∈{3,5,8,15,≥30}빈` 으로 여러 번 재고, 커버리지 적분은 헤딩별 실제 dopoff 로
        해당 곡선을 고른다.

    구현 규약
      · 도플러 이동은 `resid_echo` 를 0-도플러로 되돌린 뒤 `f_d = dopoff·Δf_d` 로 다시 램프.
        `canceller` 를 주면(권장) 이동 후 **ECA 를 다시 걸어** 능선 근처 자기소거까지 잰다.
        (안 주면 램프만 — `eca_recancelled=False` 로 정직하게 표기)
      · x축 SNR 은 **mean 규약**(스펙 §5.3 정본). median 규약(report12 `measure_single_snr`)과의
        오프셋(≈+1.59 dB = 10log10(1/ln2), 지수분포 셀에서의 이론값)도 함께 잰다.
        ⚠ 잡음통계는 **가드행을 뺀 부분맵**에서 잰다 — 능선이 남으면 mean 만 오염된다.
      · 검출 판정은 `detect_target_neighborhood`(±2셀) — 전역 argmax 아님(R3§2).
      · CFAR 는 `_cfar_excl_rows_batch`(가드행 제거 부분맵) — A5.
      · N>1 은 report12 규약(표적전압 √N, 잡음 그대로 → +10log10N)의 이상적 상한.

    ⚠ **실현 불가능한 dopoff 는 예외 대신 기록한다**(감사 A2/③/B3 조치). ★헤드라인 모드
      G1 은 F1 물리 규약에서 M=5 라 `zd=2` → 스펙 §5.2 정본 격자 `{3,5,8,15,30}` 이
      **다섯 개 전부** 도플러축 밖이다(살아남는 것은 |dopoff|=2 하나뿐). 예전 구현은 여기서
      ValueError 를 던져 stage 전체를 멈췄다 — 이제 `feasible_dopoff_bins()` 로 걸러
      `{"skipped": True, "reason": …}` 로 남기고 계속 간다(스펙 §8.6 "축을 자르지 않고 라벨만").
      **스펙 §10 스키마의 `detector_transfer.S_G.G1.N.1.dopoff.{3,5,8,15,30}` 가지는
      현재 물리(F1)에서 생성 불가능하다** — 스펙 §5.2 의 dopoff 격자를 M 의존으로 재정의해야 한다.

    ⚠ **SNR 눈금과 DPI 잔류**(감사 C2, 정직표기): x축 눈금 `snr_ref_mean` 은 σ=1 에서 쟀는데 MC 는
      σ≠1 에서 돌고 `resid_dpi` 는 고정이다. 정본(ridge=0·자유공간)에서는 `resid_dpi≈0` 이라
      무해하지만, FS-2(양자화)·`dpi_residual` 로 확장하면 실효 SNR ≠ 격자값이 된다.
      그래서 `meta.resid_dpi_power_frac`(잡음 σ=1 대비 DPI 잔류 전력비)를 항상 기록한다.

    반환 dict: {"dopoff": {"8": {snr_grid_db, Pd, wilson_lo/hi, Pfa_emp, snr50_db, snr90_db,
                                 snr90_lo_db, snr90_hi_db, marcum_cfar_snr90_db, …},
                           "3": {"skipped": True, "reason": …}}, "meta": {…}}"""
    import torch
    from detection_gpu import rd_batch

    dev = _dev_of(pre, device)
    fs = _pre_fs(pre)
    M = int(pre.M)
    Ns = int(getattr(pre, "Ns", len(pre.resid_echo)))
    Lf = Ns // M
    dfd = fs / Lf / M
    shape = shape or {}
    n_range = int(shape.get("n_range", getattr(pre, "n_range", 64)))
    start = int(shape.get("range_start_bin", 0))
    guard = tuple(shape.get("guard", GUARD_FIXED))
    train = tuple(shape.get("train", TRAIN_FIXED))
    width = int(shape.get("doppler_guard_width", DOPPLER_GUARD_WIDTH))
    tol = int(shape.get("tol_cell", TOL_CELL))
    batch = int(batch or _batch_size(Ns))
    snr_grid = np.asarray(snr_grid_db if snr_grid_db is not None
                          else np.linspace(-4.0, 20.0, 13), float)
    ri = int(ri_true if ri_true is not None else pre.ri_true) - start
    zd = M // 2

    # --- 소비 전 검사 (감사 [2]/A1/C5) ---
    eca_prov = check_eca_provenance(pre, shape, strict=eca_strict)
    prf_info = check_kernel_prf(pre, shape, mode=prf_check)
    if not (0 <= ri < n_range):
        raise ValueError(
            f"표적 거리빈이 게이트 밖이다: ri_true={int(ri_true if ri_true is not None else pre.ri_true)}, "
            f"range_start_bin={start} → 게이트 좌표 {ri} (0 ≤ ri < {n_range} 여야 한다). "
            f"pre 의 거리축과 shape 의 게이트 시작빈이 같은 좌표계인지 확인할 것 "
            f"(예전에는 음수 인덱스가 그대로 통과해 IndexError 로 죽었다).")
    lo_g, hi_g, _ = _submap_rows(M, None, width)
    if M - (hi_g - lo_g) <= 0:
        raise ValueError(
            f"도플러축(M={M})이 0-도플러 가드(width={width})에 통째로 먹혔다 — 전이곡선이 정의되지 "
            f"않는다(limit='doppler_axis_degenerate'). 상위에서 회색 처리할 셀이다.")

    # --- 실현 가능한 dopoff 만 고른다 (감사 A2) ---
    dop_ok, dop_bad = feasible_dopoff_bins(M, dopoff_bins, width)
    if not skip_infeasible and dop_bad:
        raise ValueError(f"실현 불가능한 dopoff: {dop_bad}")
    dop_max = max(zd, M - 1 - zd)

    # DPI 잔류가 잡음(σ=1) 대비 얼마나 큰지 — SNR 눈금 정직성 지표(감사 C2)
    _pd = float(np.mean(np.abs(np.asarray(pre.resid_dpi)) ** 2))

    # 원래 에코의 도플러 — meta 가 있으면 정확값, 없으면 빈 위치에서 유도
    fd_orig = None
    meta = getattr(pre, "meta", None)
    if isinstance(meta, dict):
        fd_orig = meta.get("fd")
    if fd_orig is None:
        fd_orig = (int(pre.di_true) - zd) * dfd
    n_idx = np.arange(Ns)
    base_echo = (np.asarray(pre.resid_echo, np.complex64)
                 * np.exp(-2j * np.pi * float(fd_orig) * n_idx / fs).astype(np.complex64))

    dpi_t = torch.as_tensor(np.asarray(pre.resid_dpi, np.complex64), device=dev)
    ref_t = torch.as_tensor(np.asarray(pre.ref_frame, np.complex64), device=dev)
    ref_cpi = np.tile(np.asarray(pre.ref_frame), M)
    out = {}

    for dop in dop_bad:                              # 실현 불가 — 사유를 남기고 건너뛴다
        out[str(int(dop))] = dict(dopoff_bins=int(dop), skipped=True, reason=dop_bad[dop],
                                  M=int(M), doppler_guard_width=int(width),
                                  dopoff_max_bins=int(dop_max), dfd_hz=float(dfd),
                                  snr90_db=None, snr50_db=None,
                                  note="spec §5.2 dopoff grid is not M-aware; this cell cannot "
                                       "exist at the physical PRF (F1)")

    for dop in dop_ok:
        fd_new = float(dop) * dfd
        echo = (base_echo * np.exp(2j * np.pi * fd_new * n_idx / fs).astype(np.complex64))
        if canceller is not None:
            echo = canceller.cancel(echo).astype(np.complex64)
        di = zd + int(dop)
        di_sub = _row_to_submap(di, lo_g, hi_g)

        # ① 무잡음 표적 피크 + 잡음전용 RD 통계 → 출력 SNR 눈금(mean 규약 정본)
        _, _, rd_e = range_doppler(echo, ref_cpi, fs, M, n_range=start + n_range)
        rd_e = rd_e[:, start:]
        peak0 = float(rd_e[di, ri])
        # 잡음전용 RD 를 n_noise_reps 회 뽑아 셀을 **풀링**한다 — 게이트(64빈)처럼 작은 맵에서는
        # 한 실현의 median/mean 산포가 ±0.13 dB(측정)라 x축 눈금이 그만큼 흔들린다.
        rngn = np.random.default_rng(int(seed) + 11)
        rd_n = []
        for _ in range(max(1, int(n_noise_reps))):
            nz = ((rngn.standard_normal(Ns) + 1j * rngn.standard_normal(Ns))
                  / np.sqrt(2)).astype(np.complex64)
            _, _, _rdn = range_doppler(np.asarray(pre.resid_dpi, np.complex64) + nz,
                                       ref_cpi, fs, M, n_range=start + n_range)
            rd_n.append(_rdn[:, start:])
        rd_n = np.concatenate(rd_n, axis=1)          # 거리축으로 이어붙여 셀 풀링
        # ⚠ 잡음셀 통계는 **가드행을 뺀 부분맵**에서 잰다 — CFAR 가 실제로 보는 셀이 그것이고,
        #   0-도플러 능선(DPI 잔류)이 남아 있으면 **mean 이 오염**된다(median 은 로버스트해서
        #   안 흔들린다). 전체맵으로 재면 mean-median 오프셋이 1.59 dB 가 아니라 2.4 dB 로
        #   부풀어, 규약 차이가 아니라 능선 오염을 재게 된다.
        glo, ghi, _ = _submap_rows(M, None, width)
        keep_rows = np.r_[np.arange(0, glo), np.arange(ghi, M)]
        rd_ns = rd_n[keep_rows, :]
        mean_pow = float(np.mean(rd_ns ** 2)); med_pow = float(np.median(rd_ns ** 2))
        med_pow_full = float(np.median(rd_n ** 2))          # report12 measure_single_snr 규약(전체맵)
        snr_ref_mean = 10 * np.log10(peak0 ** 2 / (mean_pow + 1e-300))
        snr_ref_med = 10 * np.log10(peak0 ** 2 / (med_pow + 1e-300))
        snr_ref_med_full = 10 * np.log10(peak0 ** 2 / (med_pow_full + 1e-300))

        echo_t = torch.as_tensor(echo, device=dev)
        g = torch.Generator(device=dev).manual_seed(int(seed) + int(dop))
        pds, los, his = [], [], []
        for s_db in snr_grid:
            sig = 10 ** ((snr_ref_mean - float(s_db)) / 20.0)
            hits = 0; done = 0
            while done < K:
                b = int(min(batch, K - done))
                nzt = ((torch.randn(b, Ns, generator=g, device=dev)
                        + 1j * torch.randn(b, Ns, generator=g, device=dev))
                       * (sig / np.sqrt(2))).to(torch.complex64)
                surv = float(np.sqrt(N)) * echo_t[None, :] + dpi_t[None, :] + nzt
                rd = rd_batch(surv, ref_t, M, start + n_range)[:, :, start:]
                _det, thr, sub, _ = _cfar_excl_rows_batch(rd, width=width, guard=guard,
                                                          train=train, pfa=pfa)
                hit = detect_target_neighborhood(sub, thr, di_sub, ri, tol=tol)
                hits += int(hit.sum().item()); done += b
            pds.append(hits / K)
            lo_, hi_ = _wilson(hits, K)
            los.append(lo_); his.append(hi_)

        pfa_emp = None
        if k_pfa:
            pfa_emp = calibrate_pfa(pre, dict(shape, n_range=n_range, range_start_bin=start,
                                              guard=guard, train=train,
                                              doppler_guard_width=width),
                                    K_pfa=int(k_pfa), pfa_target=pfa, max_iter=1,
                                    seed=int(seed) + 999, batch=batch, device=dev)["empirical"]

        # ★감사 ⑥ — `ca_cfar_2d` 는 가장자리에서 창을 자른다. 표적셀에서 **실제로 쓰이는**
        #   학습셀 수를 부분맵 크기로부터 계산한다(해석식 264 를 그대로 쓰면 G1 에서 11배 과대,
        #   Marcum 참조선이 19.44 → 20.23 dB 로 0.8 dB 어긋난다).
        n_sub_rows = M - (hi_g - lo_g)
        n_train = _n_train_at(n_sub_rows, n_range, di_sub, ri, guard, train)
        n_train_ideal = ((2 * (guard[0] + train[0]) + 1) * (2 * (guard[1] + train[1]) + 1)
                         - (2 * guard[0] + 1) * (2 * guard[1] + 1))
        snr90 = _interp_x_at(0.9, pds, snr_grid)
        marcum = _marcum_cfar_snr90_db(n_train, pfa)
        out[str(int(dop))] = dict(
            dopoff_bins=int(dop), fd_hz=float(fd_new), dfd_hz=float(dfd),
            snr_grid_db=[float(x) for x in snr_grid], Pd=[float(x) for x in pds],
            wilson_lo=[float(x) for x in los], wilson_hi=[float(x) for x in his],
            Pfa_emp=pfa_emp, K=int(K), N=int(N),
            snr50_db=_interp_x_at(0.5, pds, snr_grid), snr90_db=snr90,
            snr90_lo_db=_interp_x_at(0.9, his, snr_grid),   # 상단 CI 가 먼저 0.9 를 넘는다
            snr90_hi_db=_interp_x_at(0.9, los, snr_grid),
            snr_ref_mean_db=float(snr_ref_mean), snr_ref_median_db=float(snr_ref_med),
            snr_ref_median_fullmap_db=float(snr_ref_med_full),
            snr_median_offset_db=float(snr_ref_med - snr_ref_mean),
            peak0=float(peak0), di_true=int(di), di_submap=int(di_sub), ri_true=int(ri),
            n_train_cells=int(n_train), n_train_cells_interior_formula=int(n_train_ideal),
            n_train_note="actual clipped training-cell count at the target cell "
                         "(ca_cfar_2d truncates the window at map edges)",
            marcum_cfar_snr90_db=float(marcum),
            marcum_dev_db=(float(marcum - snr90) if snr90 is not None else None),
            marcum_note="CA-CFAR-aware Pd=(1+a/(N(1+SNR)))^-N assumes exponential (Swerling-1-like) "
                        "envelope; our CPI is non-fluctuating so it sits above the measurement")
    return dict(dopoff=out,
                meta=dict(M=M, Lf=int(Lf), fs_hz=fs, dfd_hz=float(dfd), n_range=n_range,
                          range_start_bin=start, guard=list(guard), train=list(train),
                          doppler_guard_width=width, tol_cell=tol, pfa_nominal=float(pfa),
                          N=int(N), K=int(K), batch=int(batch),
                          dopoff_used=list(dop_ok), dopoff_skipped=dict(dop_bad),
                          dopoff_max_bins=int(dop_max),
                          doppler_rows_submap=int(M - (hi_g - lo_g)),
                          eca_provenance=eca_prov, cpi=prf_info,
                          resid_dpi_power_frac=float(_pd),
                          resid_dpi_note="DPI residual power relative to unit-variance noise; "
                                         "the SNR x-axis is calibrated at sigma=1 while resid_dpi "
                                         "is held fixed, so a non-negligible value means the "
                                         "effective SNR differs from the grid label (audit C2)",
                          eca_recancelled=bool(canceller is not None),
                          snr_convention="peak^2 / MEAN noise-cell power (canonical, §5.3)",
                          detection_def="target-neighborhood +-%d threshold crossing "
                                        "(NOT global argmax)" % tol,
                          training_exclusion="submap CFAR (_cfar_excl_rows)"))


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    print(__doc__.strip().splitlines()[0])
    print("이 모듈은 형상 정의만 한다 — 스모크 검증은 experiment_freespace_range.py / "
          "benchmark/verify_freespace.py 가 부른다.")
