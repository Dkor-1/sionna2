# -*- coding: utf-8 -*-
"""
freespace_link.py — report13(자유공간 드론 검지거리) **닫힌형 링크 계층**
==========================================================================

이 모듈이 하는 일 하나: **기하·σ·수신기 예산 → RD 출력 SNR → 검지거리 R**.
그 반대(측정·MC·CFAR·ECA)는 여기 없다(`freespace_detect`·`experiment_freespace_range` 담당).

■ 재구현 금지 규약(스펙 §9 서두, 프로젝트 규칙 3)
  바이스태틱 레이더 방정식·직접파 Friis·열잡음은 **`benchmark/link_budget.LinkBudget`** 을
  호출한다. 여기서 다시 쓰지 않는다. ADC 동적범위 공식도 `experiment_x410.X410` 을 쓴다
  (6.0206·bits+1.76 을 손으로 옮겨 적지 않는다).

■ ⚠ 왜 이렇게 짰나 — 스펙이 명시한 세 개의 함정
  1) **S6(치명) — SNR(d) 는 φ 의 상당수에서 비단조다.**
     이 기하는 표적이 RX 위를 지나가므로 κ=R1·R2 가 **d 내부에서 최소**를 갖는다.
     (★재현: L=500·alt=60 에서 φ=0/10/30° 의 SNR 최대가 d≈244/235/166 m — §스모크)
     따라서 "SNR 은 d 에 대해 단조감소" 를 전제하는 **이분법은 무효**다.
     `solve_range` 는 d 격자 위에서 `SNR(d)−th(d)` 의 **부호변화 중 마지막 하강교차**
     (=최외곽 교차)를 해로 잡고, `snr_ceiling_db`(전 d 최대)·`monotone_ok`·
     `frac_never_detectable`(천장이 문턱 아래 → 어떤 거리에서도 미검출)을 함께 낸다.
  2) **S1 — R ∝ σ^(1/4) 는 d 축에서 거짓이다.**
     SNR ∝ κ^(−2) 이므로 국소지수는 `n = 2·dlnκ/dlnd` 이고, d≫L 에서만 4 로 수렴한다.
     (★재현: L=500·alt=60·φ=90°, d=150 → n=1.032, d=1000 → 3.757 — 스펙 1.03/3.76)
     `n_local()` 로 계산해 반환하고, dB↔거리배율 환산은 **반드시 n_local 을 끼워** 한다.
  3) **R5 — 가장 큰 벽은 DPI 잔류(실장 유한 소거깊이)다.**
     `n0_dpi()` 를 1급 잡음항으로 두고 `eca_depth_db ∈ {40,60,90,∞}` 를 스윕한다.
     항등식: `N0_dpi/N0_thermal [dB] = DNR[dB] − eca_depth_db`(같은 B_noise 규약일 때).

■ ⚠ 단위 규약 — N0 는 **PSD [W/Hz]** 로 더한다 (스펙 §8 의 식들을 물리적으로 일관화)
  스펙 §8 은 `N0_thermal = kT₀F·B_noise`(전력)로 쓰고 `N0_quant = P_dir·10^(−(DR+supp)/10)/fs`,
  `N0_dpi = P_dir·10^(−depth/10)/B_noise`(둘 다 PSD)로 쓴다 — 셋을 그대로 더하면 차원이 안 맞는다.
  ★설계 §1.7 의 검증표(`N0_quant−N0_thermal`: L=100·EIRP63·DR74·supp0 에서 LTE +15.4 / NR +3.8 /
  WiFi +2.2 dB)가 재현되는 규약은 **PSD 규약**뿐이다(스모크에서 세 값 전부 재현 확인).
  그래서 이 모듈의 `n0_*` 는 전부 **PSD** 를 반환한다 — 다만 대역 인자에 **기본값을 주지 않는다**
  (감사 A3/B6): `n0_thermal(nf, 1.0)` 이 PSD, `n0_thermal(nf, 30.72e6)` 이 그 대역의 전력이다.
  기본값 1.0 을 뒀더니 `dnr_db` 가 75 dB 대신 150 dB, `n0_effective` 가 +15.5 dB 대신 +90 dB 를
  **예외도 경고도 없이** 뱉었다(오차 = 10log10 B = 74.87 dB, 거리로 75배). 대역은 말해야 한다.
  SNR 닫힌형(설계 §2.5)도 `10log10(P_echo/N0_psd) + 10log10(η_ref·T_CPI)` 형태라 PSD 가 정합이다.
  ※ 설계 §2.5 의 손글씨 식 `EIRP−30 … +174 − NF` 는 30 dB 어긋나 있다(kT₀ = −203.98 dBW/Hz
    = −173.98 dBm/Hz 이므로 dBW 기준이면 +204, dBm 기준이면 EIRP 를 dBm 그대로 써야 한다).
    이 모듈은 손식 대신 `LinkBudget` 의 물리량[W] 을 그대로 나눈다 — 어긋날 여지가 없다.

■ 이 모듈이 **못 하는 것**(스펙 §7.4 의 풍부한 반환 중 여기서 못 내는 값)
  `Rb·beta·el_look` 은 기하 모듈(`src/freespace_scene.py`) 소관이다. `solve_range` 는
  호출자가 `kappa_of_d` 를 주면 `kappa_at_R`·`R_eq_m` 까지 내주고, 나머지 기하량은
  호출자(`experiment_freespace_range.stage_solve`)가 해 d 에서 다시 계산해 붙인다.

작성: report13 / 2026-07. 그림 텍스트 없음(순수 계산 모듈).
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Mapping, Sequence

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", "benchmark"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from link_budget import LinkBudget, db2lin, lin2db, K_BOLTZ, T0, C0   # noqa: E402
from experiment_x410 import X410                                      # noqa: E402

EPS0 = 8.8541878128e-12          # 진공 유전율 [F/m] — FS-3 프레넬 반사계수용

#: 스펙 §3 표시격자(수평거리 d). solve_range 의 기본 평가격자.
D_GRID_DEFAULT = np.geomspace(100.0, 20000.0, 240)

#: §8 `limit` enum (FS-3 에서 "ghost_resolved" 가 추가된다)
LIMIT_ENUM = ("thermal", "adc", "dpi_residual", "eca", "walk", "farfield",
              "beta", "geometry_nonlinear", "dpi_unsuppressible")

__all__ = [
    # --- 스펙 §9 시그니처 (12개) ---
    "n0_thermal", "n0_quant", "n0_dpi", "n0_inr", "snr_rd_db", "solve_range",
    "dnr_db", "coverage_fraction", "e_psi_pd", "cassini_contour", "two_ray_F",
    "n_local",
    # --- 보조(스펙 §9 목록 밖, §7~8 구현에 필요한 것만) ---
    "direct_power_w", "echo_power_w", "adc_dr_db", "supp_eff_db",
    "eca_depth_required_db", "n0_effective", "classify_limit",
    "snr_rd_terms_db", "range_factor", "fresnel_gamma", "two_ray_path_diff",
    "two_ray_f4_db", "D_GRID_DEFAULT", "LIMIT_ENUM",
    "dnr_vs_noise_db", "duty_db_from_cpi", "duty_terms",
    "DUTY_POLICY_DEFAULT", "DUTY_POLICIES",
    "GROUND_REPO_CONCRETE", "GROUND_FS3_SOIL",
]


# --------------------------------------------------------------------------- #
#  내부 유틸
# --------------------------------------------------------------------------- #
def _as_float(x):
    """0-d 이면 파이썬 float, 아니면 ndarray 로 돌려준다(스펙은 `-> float` 이지만
    solve_range 가 d 격자를 통째로 넘기므로 배열도 그대로 통과시켜야 한다)."""
    a = np.asarray(x, float)
    return float(a) if a.ndim == 0 else a


def _eval_on(fn, x):
    """callable 을 배열 x 에 평가한다. 벡터화 실패하면 원소별로 부른다."""
    if not callable(fn):
        return np.asarray(fn, float)
    x = np.asarray(x, float)
    try:
        y = np.asarray(fn(x), float)
        if y.shape == x.shape:
            return y
    except Exception:
        pass
    return np.asarray([float(fn(float(v))) for v in np.atleast_1d(x)], float).reshape(x.shape)


def _sum_losses_db(losses):
    """손실 인자를 dB 스칼라로 접는다. dict(항목별 dB) 또는 스칼라/시퀀스 허용.

    규약: **모든 항목은 부호까지 포함한 dB 보정치**(창손실·straddle·CFAR 은 음수).
    설계 §2.5 의 `L_win + L_straddle + L_CFAR` 를 그대로 더한다.
    """
    if losses is None:
        return 0.0
    if isinstance(losses, Mapping):
        return float(np.sum([float(v) for v in losses.values()]))
    a = np.asarray(losses, float)
    return float(a.sum()) if a.ndim else float(a)


# --------------------------------------------------------------------------- #
#  1. 잡음 바닥 항 (§8.1~8.5) — 전부 PSD [W/Hz]
# --------------------------------------------------------------------------- #
def n0_thermal(nf_db, B_noise):
    """열잡음 (§8.1). `kT₀·F·B_noise`.  **인자명·필수 여부는 스펙 §9 그대로.**

    · `B_noise = 1.0`      → **PSD [W/Hz]** (이 모듈의 잡음 합산 규약, 모듈 docstring 단위 규약)
    · `B_noise = 30.72e6`  → 그 대역의 **전력 [W]** (예: `dnr_db(P_dir, n0_thermal(5, 30.72e6))`)

    ⚠ 기본값을 **일부러 안 준다**(감사 A3/B6/⑤/#5). 예전 구현은 `b_noise_hz=1.0` 기본값을 줬는데,
      모듈 관례대로 1인자로 부르면 `dnr_db` 가 75.36 dB 대신 **150.24 dB**(=+10log10 B = +74.87 dB)
      를 뱉고 그대로 `eca_depth_required_db` 로 흘러가 "150 dB 소거 필요" 라는 리포트가 나온다.
      예외도 경고도 없는 무언의 함정이라, 대역을 **말하지 않으면 못 부르게** 막았다.
    계산은 `link_budget.LinkBudget.noise_power_w` 를 호출한다(재구현 금지 규약).
    """
    return _as_float(LinkBudget(noise_figure_db=float(nf_db)).noise_power_w(B_noise))


def n0_quant(P_dir, dr_db, supp_db, fs):
    """ADC 양자화 잡음 PSD (§8.2).  `P_dir·10^(−(DR+supp)/10)/fs` [W/Hz].

    · `P_dir`  : 수신단 직접파 전력 [W] (`direct_power_w`).  AGC 가 직접파에 걸린다는 가정.
    · `dr_db`  : ADC 동적범위(=`adc_dr_db(bits, backoff)`). 12 bit → 74.0 dB.
    · `supp_db`: ADC 앞단 DPI 억압(안테나 널·아날로그 소거). φ 의존 게이트는 `supp_eff_db`.
    · `fs`     : 샘플링률 [Hz] — 양자화 잡음은 fs 전체에 흰색으로 퍼진다(그래서 ∝1/fs).
    ★검증(설계 §1.7 표, L=100·EIRP63·DR74·supp0): 열잡음 대비 LTE +15.4 / NR +3.8 / WiFi +2.2 dB
      — 스모크에서 15.35 / 3.75 / 2.16 dB 로 재현.
    """
    return _as_float(np.asarray(P_dir, float) * db2lin(-(np.asarray(dr_db, float)
                                                        + np.asarray(supp_db, float)))
                     / np.asarray(fs, float))


def n0_dpi(P_dir, eca_depth_db, B_noise):
    """**실장 유한 소거깊이가 남기는 DPI 잔류** PSD (§8.3, R5 — 가장 큰 벽).

    `P_dir·10^(−eca_depth_db/10)/B_noise` [W/Hz].

    왜 1급 항인가: 우리 float64 ECA 는 ★측정상 사실상 이상적(ridge_rel=0 에서 잔류≈0 dB)이라
    **모델 안에는 벽이 없다**. 진짜 낙관은 여기다 — 실장 ECA·아날로그 소거는 통상 40~90 dB 에서
    멈추고, 그 잔류가 잡음바닥을 들어올린다. 그래서 `eca_depth_db∈{40,60,90,∞}` 를 스윕한다.

    항등식(같은 `B_noise` 규약): `10log10(N0_dpi/N0_thermal) = DNR_db − eca_depth_db`.
    ★L=500·LTE·EIRP63 에서 DNR≈75.4 dB → 소거 60 dB 면 +15.4 dB → 거리 ×0.41(스모크 재현).
    `eca_depth_db=np.inf`(또는 None) → 0.0(이상소거, 헤드라인 정본).
    """
    if eca_depth_db is None:
        return 0.0
    depth = np.asarray(eca_depth_db, float)
    val = np.asarray(P_dir, float) * db2lin(-depth) / np.asarray(B_noise, float)
    return _as_float(np.where(np.isfinite(depth), val, 0.0))


def n0_inr(inr_db, n0_thermal):
    """동일채널 간섭 PSD (§8.5, R9).  `10^(INR/10)·N0_thermal`.

    두 번째 인자는 **열잡음 PSD 값**(모듈 함수 `n0_thermal()` 의 반환)이다 — 스펙 §9 의
    인자명을 그대로 지켜 함수명과 같은 이름을 쓴다(내부에서 함수를 부르지 않으므로 무해).
    간섭도 표적과 같은 코히런트 이득을 받는다는 가정(=잡음처럼 취급)이며, 이 항 하나로
    거리가 한 자릿수 줄 수 있어 정본에는 넣지 않고 감도축으로만 낸다(§15-23).
    `inr_db=None` → 0.0.
    """
    if inr_db is None:
        return 0.0
    return _as_float(db2lin(np.asarray(inr_db, float)) * np.asarray(n0_thermal, float))


def n0_effective(P_dir, nf_db, b_noise_hz, fs_hz=None, dr_db=None,
                 supp_db=0.0, eca_depth_db=None, inr_db=None):
    """(보조) 잡음 4항을 한 번에 — `dict(thermal, adc, dpi_residual, inr, total)` [W/Hz].

    `N0_eff = N0_thermal + N0_quant + N0_dpi + N0_inr` (§8.3). **전부 PSD** 로 더한다.
    `fs_hz/dr_db` 가 없으면 ADC 항 0(FS-0/FS-1), `eca_depth_db` 없으면 DPI 잔류 0(이상소거).

    ⚠ `b_noise_hz` 는 **DPI 잔류가 퍼지는 대역**이다(열잡음은 항상 1 Hz PSD 로 둔다).
      **기본값을 안 준다**(감사 A3/④/#5): 예전 기본값 1.0 은 "잔류 전력 전체를 1 Hz 에 몰아넣기"
      라서 `N0_dpi/N0_th` 가 +15.36 dB 대신 **+90.24 dB**(오차 = 10log10 B = 74.87 dB, 거리로 75배)
      가 되고, `classify_limit` 의 벽 라벨이 전 셀에서 `dpi_residual` 로 굳어 §1.1-5("어느 하나를
      헤드라인으로 세우지 않는다")가 인자 하나로 무너졌다. 보통 `b_noise_hz = fs` 또는 수신 잡음대역.
    ★재현(L=500·LTE·EIRP63·depth 60): `b_noise_hz=30.72e6` → total/thermal = **+15.49 dB** → 거리 ×0.41.
    """
    if eca_depth_db is not None and np.all(np.isfinite(np.asarray(eca_depth_db, float))) \
            and float(b_noise_hz) == 1.0:
        raise ValueError(
            "b_noise_hz=1.0 인데 eca_depth_db 가 유한하다 — DPI 잔류를 1 Hz 에 몰아넣으면 "
            "10log10(B) 만큼(수십 dB) 부풀어 벽 라벨이 뒤집힌다. 수신 잡음대역(보통 fs)을 줄 것.")
    th = n0_thermal(nf_db, 1.0)
    adc = n0_quant(P_dir, dr_db, supp_db, fs_hz) if (fs_hz and dr_db is not None) else 0.0
    dpi = n0_dpi(P_dir, eca_depth_db, b_noise_hz)
    inr = n0_inr(inr_db, th)
    return dict(thermal=th, adc=adc, dpi_residual=dpi, inr=inr,
                total=th + adc + dpi + inr, b_noise_hz=float(b_noise_hz))


def dnr_db(P_dir, n0, bw_hz=1.0):
    """**직접파 대 잡음** 비 DNR [dB] = `10log10(P_dir/(n0·bw_hz))`.  (스펙 §9 `dnr_db(P_dir, n0)`)

    `n0` 를 **전력**으로 주면 스펙대로 2인자로 부르면 된다(권장):
        `dnr_db(P_dir, n0_thermal(5.0, 30.72e6))` → ★75.36 dB (설계 "헤드라인 DNR 75 dB" 재현)
    PSD 를 주는 경우에만 `bw_hz` 에 수신 잡음대역을 넣는다. `n0_thermal` 이 대역을 필수로 받게
    바뀌었으므로(감사 A3) 이제 실수로 PSD 를 흘려보내기 어렵다.

    ⚠⚠ **이름 충돌 경고**(감사 B5/#6). 저장소에는 같은 이름의 **다른 물리량**이 이미 있다:
        `benchmark/link_budget.link_terms["dnr_db"]` = 직접파 / **에코**  (★같은 기하에서 98.60 dB)
        이 함수                                       = 직접파 / **잡음**  (★75.36 dB)
      report05/12 JSON 은 전자 규약이다. §8.3 의 항등식(`N0_dpi/N0_th = DNR − depth`)에 맞는 것은
      **후자**이므로 report13 은 이 함수를 쓰되, JSON 키는 반드시 구별되게 쓸 것:
        스펙 §10 의 `ranges..dnr_at_R90_db` → **`dnr_noise_at_R90_db`** 로 쓰고
        `meta` 에 두 정의를 병기한다. 코드에서는 별칭 `dnr_vs_noise_db` 를 쓰면 오독이 준다.
    이 값이 `n0_dpi` 의 스케일을 정한다 — 소거깊이가 DNR 을 못 넘으면 잔류가 열잡음을 넘는다.
    """
    return _as_float(lin2db(np.asarray(P_dir, float)
                            / (np.asarray(n0, float) * np.asarray(bw_hz, float))))


#: `dnr_db` 의 명시적 별칭 — 호출부에서 '직접파/에코'(link_budget) 와 헷갈리지 않게 쓸 것.
dnr_vs_noise_db = dnr_db


def eca_depth_required_db(dnr, margin_db=0.0):
    """(보조) **요구** 소거깊이 [dB] — 잔류를 열잡음보다 `margin_db` 만큼 아래로 누르려면.

    `depth ≥ DNR + margin`. ⚠ 이건 요구량이지 달성치가 아니다(§15-7). 달성치 스윕은
    `eca_depth_db∈{40,60,90,∞}` 쪽이다.
    """
    return _as_float(np.asarray(dnr, float) + float(margin_db))


def adc_dr_db(bits=12, backoff_db=0.0):
    """(보조) ADC 동적범위 [dB] = `X410.dynamic_range_db` − PAPR 백오프.

    공식은 `experiment_x410.X410`(6.0206·bits+1.76)을 그대로 쓴다 — 12 bit → 74.0 dB.
    `bits=None`(∞ 비트) → `np.inf`.
    """
    if bits is None or (isinstance(bits, float) and not np.isfinite(bits)):
        return float("inf")
    return float(X410(adc_bits=int(bits)).dynamic_range_db - float(backoff_db))


def supp_eff_db(supp_db, dtheta_deg, beamwidth_deg=30.0):
    """(보조) **φ 의존 DPI 억압** (§8.4, R7).  `supp_eff = min(supp, supp_max(Δθ))`.

    Δθ = RX 에서 본 TX↔표적 각분리(`freespace_scene.angular_sep_tx_target_deg`).
    표적이 직접파와 같은 방향에 있으면(Δθ < 빔폭/2) 널·빔조향으로 DPI 만 죽일 수 없다 →
    억압 0 dB. 그 위로는 각분리에 비례해 선형(dB)으로 회복한다고 **선언**한다
    (빔폭·회복모형 모두 선언값 — 근거문서 없음, `meta` 에 그렇게 적을 것).
    반환 `(supp_eff_db, unsuppressible)` — 후자가 True 면 `limit="dpi_unsuppressible"`.
    """
    supp = np.asarray(supp_db, float)
    dth = np.abs(np.asarray(dtheta_deg, float))
    half = 0.5 * float(beamwidth_deg)
    ratio = np.clip((dth - half) / max(half, 1e-9), 0.0, 1.0)
    eff = supp * ratio
    unsup = dth < half
    if eff.ndim == 0:
        return float(eff), bool(unsup)
    return eff, unsup


# --------------------------------------------------------------------------- #
#  2. 전력·SNR 닫힌형 (§2.5, §7) — 레이더 방정식은 link_budget 호출
# --------------------------------------------------------------------------- #
def direct_power_w(eirp_dbm, grx_dbi, lam, L, sys_loss_db=0.0):
    """(보조) 직접파 수신전력 [W]. `LinkBudget.direct_power_w` 호출(재구현 금지)."""
    lb = LinkBudget(eirp_dbm=float(eirp_dbm), rx_gain_dbi=float(grx_dbi),
                    sys_loss_db=float(sys_loss_db))
    return _as_float(lb.direct_power_w(lam, L))


def echo_power_w(eirp_dbm, grx_dbi, lam, sigma_m2, R1, R2, sys_loss_db=0.0):
    """(보조) 표적 에코 수신전력 [W]. `LinkBudget.echo_power_w` 호출(재구현 금지)."""
    lb = LinkBudget(eirp_dbm=float(eirp_dbm), rx_gain_dbi=float(grx_dbi),
                    sys_loss_db=float(sys_loss_db))
    return _as_float(lb.echo_power_w(lam, sigma_m2, R1, R2))


def duty_db_from_cpi(M, T_ref_s, T_cpi_s):
    """(보조, 감사 ⑪) **듀티 항** [dB] = `10log10(M·T_ref / T_CPI)` — 음수(항상 벌점).

    왜 필요한가: `snr_rd_db` 의 코히런트 이득 항은 `10log10(T_CPI)` 인데, 이건 **T_CPI 내내
    기준신호가 켜져 있다**는 뜻이다. 스펙 F1 이 확정한 물리(SSB PRF=50 Hz → T_CPI 100 ms 에
    버스트 M=5개)에서는 실제 조명 시간이 `M·T_ref` 뿐이라 그 차이가 SSB 의 진짜 핸디캡이다.
    이 항을 안 넣으면 9모드가 전부 같은 `10log10(0.1)` 을 받아 **F1 이 만든 SSB 핸디캡(≈−16 dB)이
    SNR 에서 통째로 사라지고**, 그 16 dB 를 경험 교정상수 `k_mode` 가 조용히 흡수한다
    (§7.6 의 "잔차 |Δ|<0.5 dB" 어서션은 그래도 통과해버린다 — 검증이 못 잡는 종류의 오류다).

    · `T_ref_s` : 반복 1회당 기준신호가 실제로 켜져 있는 시간[s](예 SSB 버스트 길이).
      **선언값**이며 근거문서가 없다 — `meta.cpi.t_ref_s` 에 그렇게 적을 것.
    · 연속조명(LTE CRS 처럼 매 프레임이 이어짐)이면 `M·T_ref ≈ T_CPI` 라 0 dB 다.
    스펙 §3/F13 이 EIRP 를 "in-burst peak, duty 별도" 로 정의한 것과 짝이 되는 항이다.
    """
    return float(10.0 * np.log10(max(float(M) * float(T_ref_s) / float(T_cpi_s), 1e-30)))


# --------------------------------------------------------------------------- #
#  2b. ⭐ 듀티 **정책 스위치** (결함 D-C 수리, 2026-08-03)
# --------------------------------------------------------------------------- #
#  왜 이 절이 생겼나 — `duty_db_from_cpi` 는 **정의만 돼 있었다.**
#    · 저장소 전체 문자열 등장 25회 중 실제 파이썬 호출은 3곳뿐이고
#      (`benchmark/mono_link.py:119` · `benchmark/sigma_sensitivity.py:523` ·
#       `benchmark/geometry_grid.py:183`) 셋 다 **표를 찍기 위해 값만 계산**한다.
#    · 그 값이 SNR 로 들어갈 수 있는 유일한 자리는 `mono_link.scene_arm(..., duty_on=False)`
#      인데 9개 호출부가 **전부 기본값 False** 다(`duty_on=True` 는 저장소에 0회).
#    · R90 생산경로(`src/experiment_freespace_range.stage_solve`)는 값을 계산조차 안 한다.
#    ⇒ 즉 **어떤 SNR 에도 한 번도 도달한 적이 없다.** 크기는 σ 와 완전히 무관한
#      W1 −12.84 / L1 0.00 / G1 −16.02 dB 로, 반송파 λ² 축(9.03 dB)보다 크다.
#
#  ⚠⚠ **이중계상 금지**(`experiment_freespace_range._power_normalization_facts` 의 경고와 짝):
#    점유율 파생 평균방사전력 감쇠(`radiated_power_frac_db_vs_g3`, = `deploy` 뷰)와 이 듀티항은
#    **같은 물리손실의 대체 파라미터화**다. 둘을 곱하면 이중계상이다.
#    정본 뷰가 `equal_psd`(= 밴드별 per-RE 전력 동일, 평균전력 감쇠 미적용)인 동안에만
#    듀티를 켠다. `deploy` 뷰로 옮기면 듀티를 꺼야 한다 — `duty_policy="off"`.
#
#: 정책 기본값. **리포트가 이미 선언한 규약**(EIRP = in-burst peak, 듀티 별도; 스펙 §3/F13,
#: report03 조명원 원장의 "WiFi 패킷 듀티 −12.84 dB" 행)이 곧 `"cpi_on_fraction"` 이다.
DUTY_POLICY_DEFAULT = "cpi_on_fraction"
DUTY_POLICIES = ("cpi_on_fraction", "off")

#: 모드라벨 첫 글자 → 표준. `experiment_freespace_range.MODE_STD` 의 **거울**이며,
#: `duty_terms()` 가 그 모듈을 import 할 수 있으면 런타임에 대조해 불일치를 예외로 띄운다
#: (freespace_link 는 하위 계층이라 상위 실험모듈을 정적 의존하지 않는다).
_DUTY_STD_OF = {"W": "wifi", "L": "lte", "G": "nr"}


def duty_terms(mode, T_cpi_s=0.1, policy=None, wifi_packet_rate_hz=1000.0,
               strict=True) -> dict:
    """(D-C) 모드 라벨 → **듀티 항과 그 유래**. 값은 전부 저장소 단일진리원에서 읽는다.

        PRF   ← `freespace_scene.prf_hz(std, mode, wifi_packet_rate_hz)`   (3GPP/IEEE 자원격자)
        M     ← `freespace_scene.M_from_prf(T_CPI, PRF)`
        T_ref ← `waveforms.all_waveforms(occ)[std]` 의 `len(tx)/fs_hz`     (**선언값**)
        duty  ← `duty_db_from_cpi(M, T_ref, T_CPI)`  (policy="cpi_on_fraction")
                또는 0.0                              (policy="off", 수리 전 거동)

    ★재현(T_CPI=0.1 s, wifi_packet_rate=1000): W1 −12.8400 / L1 +0.0000 / G1 −16.0206 dB
      — `outputs/sigma_sensitivity.json : unapplied_duty_axis.duty_db` 와 같은 값이고,
      WiFi 는 `outputs/report4_fixups.json : packet_duty_db` 와도 일치한다(독립 산출물 2건).

    ⚠ `duty_db > 0` 은 물리적으로 불가능하다(기준신호가 CPI 보다 오래 켜져 있다는 뜻).
      `strict=True` 면 예외, False 면 0 으로 clip 하고 `clipped=True` 를 남긴다.
    반환 dict: std, occ, prf_hz, M, T_ref_s, T_cpi_s, duty_db, policy, provenance, clipped
    """
    pol = DUTY_POLICY_DEFAULT if policy is None else str(policy)
    if pol not in DUTY_POLICIES:
        raise ValueError(f"모르는 duty_policy={pol!r} — {DUTY_POLICIES} 중 하나여야 한다")
    m = str(mode).upper()
    if len(m) != 2 or m[0] not in _DUTY_STD_OF or m[1] not in "123":
        raise ValueError(f"모드 라벨은 W/L/G + 1/2/3 이어야 한다 — {mode!r}")
    std, occ = _DUTY_STD_OF[m[0]], "G" + m[1]
    try:                                  # 상위 모듈이 있으면 매핑을 대조한다(정적 의존 아님)
        import experiment_freespace_range as _efr
        if _efr.MODE_STD[m] != (std, occ):
            raise ValueError(
                f"모드 매핑 불일치 — freespace_link 는 {(std, occ)}, "
                f"experiment_freespace_range.MODE_STD 는 {_efr.MODE_STD[m]}")
    except ImportError:
        pass
    from freespace_scene import prf_hz, M_from_prf          # noqa: E402  (하위→상위 아님)
    from waveforms import all_waveforms                     # noqa: E402
    wf = all_waveforms(occ)[std]
    prf = float(prf_hz(std, m, wifi_packet_rate_hz))
    M = int(M_from_prf(float(T_cpi_s), prf))
    t_ref = float(len(wf.tx) / float(wf.fs_hz))
    duty = duty_db_from_cpi(M, t_ref, float(T_cpi_s)) if pol == "cpi_on_fraction" else 0.0
    clipped = False
    if duty > 0.0:
        if strict:
            raise ValueError(
                f"duty_db={duty:+.3f} dB > 0 — 기준신호 점등시간 M·T_ref={M * t_ref:.6g}s 가 "
                f"T_CPI={float(T_cpi_s):.6g}s 보다 길다. 물리적으로 불가능하다.")
        duty, clipped = 0.0, True
    return dict(mode=m, std=std, occ=occ, prf_hz=prf, M=M, T_ref_s=t_ref,
                T_cpi_s=float(T_cpi_s), duty_db=float(duty), policy=pol, clipped=clipped,
                wifi_packet_rate_hz=float(wifi_packet_rate_hz),
                provenance=dict(
                    prf="freespace_scene.prf_hz (3GPP/IEEE resource grid; wifi packet rate is a "
                        "declared free parameter, spec F9)",
                    M="freespace_scene.M_from_prf(T_cpi, prf)",
                    T_ref="waveforms.all_waveforms(occ)[std]: len(tx)/fs_hz (declared)",
                    duty="freespace_link.duty_db_from_cpi(M, T_ref, T_cpi)"),
                double_count_guard=("MUST NOT be combined with the 'deploy' occupancy-derived "
                                    "average-radiated-power derating (radiated_power_frac_db_vs_g3) "
                                    "— same physical loss, alternative parameterisation. Canonical "
                                    "view is equal_psd, where duty is the only time-domain term."))


def _resolve_duty(duty_db, mode, duty_policy, T, wifi_packet_rate_hz=1000.0):
    """(내부) `snr_rd_db`/`snr_rd_terms_db` 의 듀티 인자 해석 — **한 자리에서만** 판단한다.

    · `mode is None`  → `duty_db` 를 **그대로** 쓴다(기본 0.0). 즉 기존 호출부는 **비트 불변**이다.
      (다른 세션이 돌리고 있는 산출물 숫자가 이 수리로 조용히 움직이면 안 된다.)
    · `mode` 를 주면 `duty_terms(mode, T, duty_policy)` 로 정책에서 해석한다. 이때 `duty_db` 를
      **동시에** 0 이 아닌 값으로 주면 이중계상이므로 예외.
    """
    if mode is None:
        if duty_policy is not None:
            raise ValueError("duty_policy 를 주려면 mode 도 줘야 한다 — 정책은 모드에서 값을 만든다")
        return float(duty_db), None
    if float(duty_db) != 0.0:
        raise ValueError(
            f"mode={mode!r} 와 duty_db={duty_db} 를 동시에 줬다 — 이중계상이다. "
            "정책으로 풀려면 duty_db 를 생략하고, 손으로 넣으려면 mode 를 생략할 것.")
    t = duty_terms(mode, T_cpi_s=(float(np.asarray(T).ravel()[0]) if np.ndim(T) else float(T)),
                   policy=duty_policy, wifi_packet_rate_hz=wifi_packet_rate_hz)
    return float(t["duty_db"]), t


def snr_rd_db(eirp, grx, lam, sigma, R1, R2, nf=5.0, eta_ref=0.0, T=0.1,
              losses=0.0, k_mode=0.0, n0_extra=0.0, sys_loss=0.0,
              eta_ref_is_db=True, duty_db=0.0, mode=None, duty_policy=None,
              wifi_packet_rate_hz=1000.0):
    """**RD 맵 출력 SNR [dB]** — 닫힌형(설계 §2.5, 스펙 §7.6).

        SNR_RD = 10log10(P_echo / N0_eff) + 10log10(η_ref) + 10log10(T_CPI) + duty
                 + Σ losses + k_mode

    · `eirp` [dBm], `grx` [dBi], `nf` [dB] — 세 값 모두 **선언값**(§15-1).
    · `sigma` [m²] (dBsm 아님). `R1`,`R2` [m] — 배열 가능(d 격자 통째로 넘겨도 됨).
    · `eta_ref` : 기준신호 이용효율. 기본 **dB 해석**(JSON 키가 `eta_ref_db` 라서).
                  선형값을 주려면 `eta_ref_is_db=False`.
    · `T`       : T_CPI [s]. 코히런트 적분이득 = 정합필터(B_ref·T_ref)×도플러 FFT(M) 인데
                  닫힌형에서는 B 가 약분돼 **대역폭 B 는 SNR 항에 없다**(★verify_linkbudget).
                  B 는 ΔR_b=c/B 와 walk 상한에만 들어간다(F2·F15 가 이걸 그림으로 증명).
    · `losses`  : dB 보정 스칼라 또는 dict(창손실·straddle·CFAR 문턱오프셋; 전부 음수).
    · `k_mode`  : 경험 교정상수 [dB](§7.6). ⚠ **곱셈상수라 S1/S6 기하 비선형은 못 흡수**한다.
    · `n0_extra`: 열잡음 위에 더할 PSD [W/Hz] (`n0_quant + n0_dpi + n0_inr`).
    · `duty_db` : **듀티 항**(감사 ⑪, 기본 0 = 연속조명). `duty_db_from_cpi(M, T_ref, T_CPI)`.
                  9모드에 T=0.1 만 넣고 이 항을 0 으로 두면 F1 의 SSB 핸디갭이 SNR 에서 사라진다.
    · `mode`/`duty_policy` : ⭐**듀티 정책 스위치**(결함 D-C 수리). `mode="W1"/"L1"/"G1"…` 을 주면
                  `duty_terms()` 가 저장소 단일진리원(PRF·M·T_ref)에서 듀티를 만들어 넣는다
                  (기본 정책 `DUTY_POLICY_DEFAULT="cpi_on_fraction"` = **켬**, 리포트가 이미
                  선언한 규약). `duty_policy="off"` 로 끈다. `mode=None`(기본)이면 옛 거동 그대로
                  `duty_db` 만 쓴다 — **기존 호출부의 숫자는 비트 불변**이다.
                  ⚠ `mode` 와 `duty_db≠0` 을 동시에 주면 이중계상이라 예외.

    ★자기검증: `k_mode=0, losses=0, η=1` 이면 이 값은 `10log10(E_echo/N0)` 그 자체이고,
      LinkBudget 물리량[W]에서 직접 나오므로 설계 §2.5 손식의 30 dB 모호성이 없다.
    """
    duty_db, _ = _resolve_duty(duty_db, mode, duty_policy, T, wifi_packet_rate_hz)
    Pe = echo_power_w(eirp, grx, lam, sigma, R1, R2, sys_loss_db=sys_loss)
    n0 = np.asarray(n0_thermal(nf, 1.0), float) + np.asarray(n0_extra, float)
    eta_db = float(eta_ref) if eta_ref_is_db else float(lin2db(eta_ref))
    snr = (lin2db(np.asarray(Pe, float) / n0) + eta_db
           + 10.0 * np.log10(np.asarray(T, float)) + float(duty_db)
           + _sum_losses_db(losses) + float(k_mode))
    return _as_float(snr)


def snr_rd_terms_db(eirp, grx, lam, sigma, R1, R2, nf=5.0, eta_ref=0.0, T=0.1,
                    losses=0.0, k_mode=0.0, n0_extra=0.0, sys_loss=0.0,
                    eta_ref_is_db=True, duty_db=0.0, mode=None, duty_policy=None,
                    wifi_packet_rate_hz=1000.0):
    """(보조) F2 폭포그림용 **예산 항목 분해** — `ranges..budget_terms_db` 스키마 그대로.

    keys: eirp, grx, lambda2, sigma, spread(−30log10(4π)−20log10R1−20log10R2), n0,
          eta_ref, t_cpi, duty, losses, k_mode, total.
    합이 `snr_rd_db` 와 같아야 한다(★스모크: sys_loss∈{0,3}×σ∈{0.01,0.5}×duty∈{0,−16} 전조합에서
    |Δ| ≤ 3e-14 dB).
    `mode`/`duty_policy` 는 `snr_rd_db` 와 **같은 뜻**이다(D-C 스위치). 폭포의 `duty` 칸이
    정책에서 온 값으로 채워지므로 그림이 스스로 근거를 들고 다닌다.
    """
    duty_db, _ = _resolve_duty(duty_db, mode, duty_policy, T, wifi_packet_rate_hz)
    R1a, R2a = np.asarray(R1, float), np.asarray(R2, float)
    n0 = np.asarray(n0_thermal(nf, 1.0), float) + np.asarray(n0_extra, float)
    t = dict(
        eirp=float(eirp) - 30.0,                                  # dBm → dBW
        grx=float(grx),
        lambda2=float(20.0 * np.log10(lam)),
        sigma=_as_float(10.0 * np.log10(np.asarray(sigma, float))),
        spread=_as_float(-30.0 * np.log10(4 * np.pi) - 20.0 * np.log10(R1a)
                         - 20.0 * np.log10(R2a)),
        n0=_as_float(-lin2db(n0)),
        eta_ref=float(eta_ref) if eta_ref_is_db else float(lin2db(eta_ref)),
        t_cpi=_as_float(10.0 * np.log10(np.asarray(T, float))),
        duty=float(duty_db),
        losses=_sum_losses_db(losses) - float(sys_loss),
        k_mode=float(k_mode),
    )
    t["total"] = sum(np.asarray(v, float) for v in t.values())
    return t


def range_factor(d_snr_db_signed, n=4.0):
    """(보조) 거리배율 = `10^(ΔSNR/(10·n))`.  **ΔSNR 은 부호 있는 값**(음수 = 열화).

    ⚠ 부호 규약(감사 A4 — 두 docstring 이 서로 반대로 설명하던 것을 통일):
        ΔSNR = SNR_new − SNR_old  [dB]
        잡음이 +15.49 dB 올라감  → ΔSNR = **−15.49** → `range_factor(-15.49)` = ★0.41
        지면 2-ray 로 F⁴ = +11.5 dB 이득 → ΔSNR = **+11.5** → 1.94
      소거깊이 페널티(양수 dB)를 부호 없이 그대로 넣으면 0.41 이 아니라 2.44 가 나온다(5.9배 과대).
    ⚠ S1: `n` 은 4 가 아니라 `n_local()`(또는 `solve_range` 의 `range_conv_exponent`)이다.
      4 를 쓰면 d 축 근거리에서 최대 40배 틀린다.
    """
    return _as_float(10.0 ** (np.asarray(d_snr_db_signed, float) / (10.0 * float(n))))


# --------------------------------------------------------------------------- #
#  3. 거리 역해 (§7.4) — **이분법 금지, 최외곽 하강교차** (S6)
# --------------------------------------------------------------------------- #
def n_local(kappa_of_d, d, at=None):
    """**국소지수 n** — `R ∝ σ^(1/n)` (S1).  `n = 2·dlnκ/dlnd`,  κ = R1·R2.

    유도: SNR ∝ σ/κ² ⇒ 10log10SNR 의 기울기 = −20·dlog10κ/dlog10 d [dB/decade].
    문턱을 고정한 채 σ 를 Δ[dB] 올리면 해가 Δlog10 d = Δ/(20·dlog10κ/dlog10 d) 만큼 움직이고,
    이를 `d'/d = σ배율^(1/n)` 과 맞추면 `n = 2·dlnκ/dlnd`. d≫L 에서 κ→d² 라 n→4 이지만,
    표적이 RX 근처를 지나는 근거리에서는 κ 가 거의 안 변해 **n≈1 이하**까지 떨어진다.

    ★재현(L=500, TX(0,0,25)/RX(500,0,3), alt=60, φ=90°): d=150 → 1.032, d=1000 → 3.757
      (스펙 S1 의 "1.03 / 3.76" 재현. d=19800 에서 3.999 → 정말 d≫L 에서만 4다).

    인자:
      kappa_of_d : κ 배열(길이=len(d)) 또는 callable κ(d)
      d          : 배열 또는 스칼라(**callable 일 때만** 스칼라 허용)
      at         : 주면 그 d 에서 로그보간한 **스칼라** 반환
    반환: `float | ndarray` — 스펙 §9 는 `-> float` 이라고만 썼지만, 배열 κ 를 배열 d 위에서
      미분하면 당연히 배열이 나온다. `at=` 을 주면 스칼라다(스펙 §10 `n_local_at_R90` 이 그것).

    ⚠ **깨지던 호출**(감사 #4/C1): `n_local(kappa_배열, d=스칼라)` 는 예외 없이 **2000배 틀린 배열**을
      돌려줬다 — `np.gradient(log κ, log d)` 의 두 번째 인자가 스칼라면 numpy 가 그것을 '균일간격'
      (log 20000/100 = 6.9078)으로 해석하기 때문이다(d=1000 에서 3.76 대신 0.00175).
      배열 κ 는 자기가 어느 d 격자 위에 있는지 모르므로 그 호출은 **원리적으로 답을 낼 수 없다.**
      → 이제 명시적으로 raise 한다. 올바른 사용은 `n_local(kap, d_grid, at=1000.0)` 이다.
    """
    if callable(kappa_of_d):
        x = np.atleast_1d(np.asarray(d if at is None else at, float))
        h = 1e-3
        k_lo = _eval_on(kappa_of_d, x * (1 - h))
        k_hi = _eval_on(kappa_of_d, x * (1 + h))
        n = 2.0 * (np.log(k_hi) - np.log(k_lo)) / (np.log(x * (1 + h)) - np.log(x * (1 - h)))
        return float(n[0]) if (at is not None or np.asarray(d).ndim == 0) else n
    kap = np.asarray(kappa_of_d, float)
    dd = np.asarray(d, float)
    if kap.ndim > 0 and dd.ndim == 0:
        raise ValueError(
            "n_local(κ 배열, d 스칼라)는 정의할 수 없다 — 배열 κ 가 어느 d 격자 위에 있는지 모른다. "
            "`n_local(kappa_grid, d_grid, at=d0)`(격자+평가점) 또는 `n_local(callable, d0)` 로 부를 것.")
    if kap.shape != dd.shape:
        raise ValueError(f"kappa_of_d {kap.shape} 와 d {dd.shape} 의 모양이 다르다")
    n = 2.0 * np.gradient(np.log(kap), np.log(dd))
    if at is None:
        return n
    return float(np.interp(np.log(float(at)), np.log(dd), n))


def solve_range(snr_of_d, th_db, d_grid=None, kappa_of_d=None, valid=None,
                mono_tol_db=0.05):
    """**검지거리 역해 — 최외곽 하강교차** (스펙 §7.4, S6/S1).

    ⚠ 왜 이분법이 아닌가: 이 기하에서 SNR(d) 는 φ 의 상당수에서 **내부 최대**를 갖는다
    (표적이 RX 위를 지나며 κ=R1R2 가 d 내부에서 최소가 되기 때문). 이분법은 "단조감소"를
    전제하므로 그런 φ 에서 아무 값이나 뱉는다. 여기서는 d 격자 위 `g(d)=SNR(d)−th(d)` 의
    부호변화를 **전부** 찾고 그중 **마지막 하강교차(+→−)** 를 해로 잡는다. 곧 "검출되는
    가장 바깥 거리"이며, 안쪽의 미검출 구멍(있으면)은 `n_ascending`·`crossings_m` 에 남는다.

    인자:
      snr_of_d  : SNR[dB] 배열(길이=len(d_grid)) 또는 callable f(d)->dB
      th_db     : 문턱[dB] 스칼라 또는 d 별 배열(dopoff 가 d 에 따라 변하면 배열)
      d_grid    : 평가격자[m]. None 이면 `D_GRID_DEFAULT`(geomspace(100,20000,240))
      kappa_of_d: (선택) κ=R1R2 배열/callable — 주면 `n_local`·`kappa_at_R`·`R_eq_m` 산출
      valid     : (선택) 유효범위 게이트 bool 배열(β≤90°·원거리장 등). False 셀은 **검출로
                  세지 않는다**(그림 축은 안 자르되 해에는 못 들어온다 — 스펙 §8.6)
      mono_tol_db: 단조성 판정 허용치

    반환 dict:
      R_m, R_eq_m, kappa_at_R, n_local(=n_geom), n_geom, n_local_from_snr,
      range_conv_exponent, n_local_source, snr_at_R_db, th_at_R_db,
      snr_ceiling_db(**valid 게이트 적용**), snr_ceiling_ungated_db, snr_peak_d_m,
      snr_peak_d_ungated_m, monotone_ok, snr_rise_db, never_detectable,
      frac_never_detectable, grid_limited, n_crossings, n_ascending, crossings_m,
      d_min_m, d_max_m, geometry_nonlinear
    ※ `frac_never_detectable` 은 **이 한 곡선**에 대해 0.0/1.0 이다. 스펙의 셀 단위 값은
      호출자가 헤딩 ψ 전체에 대해 평균해서 만든다(§7.3 커버리지 적분과 같은 자리).
    ※ Rb·β·el_look 은 기하 모듈 소관이라 여기서 내지 않는다(모듈 docstring 참조).

    ⚠ 고친 두 곳(감사 ①/#5/B4/⑧) — **둘 다 헤드라인 부호를 뒤집던 버그**다.
      (a) `grid_limited` 판정이 `np.all(det)` 였다. 그런데 스펙 §8.6 은 근거리 셀에 `valid=False`
          (β>90°·원거리장)를 **상시** 강제하므로(★L=500·alt=60·φ=90°: 240칸 중 앞 41칸이 β>90°)
          `np.all(det)` 는 영원히 참이 될 수 없다. 그래서 "20 km 격자 끝까지 검출" 인 셀이
          `R=nan, frac_never_detectable=1.0`("어떤 거리에서도 미검출")로 보고됐다 — EIRP 80/90 dBm,
          N=4, T_CPI=1 s 같은 **가장 강한 설정이 정확히 이 조건**이라 F8/F10/F11 상단이 통째로 비었다.
          → `det[-1]`(격자 바깥 끝이 검출인가)로 판정하고, `never` 는 `not det.any()` 로만 센다.
      (b) `snr_ceiling_db`·`snr_peak_d_m` 이 `valid` 를 **적용하지 않은** raw SNR 에서 나왔다.
          β>90° 구역은 항상 근거리=SNR 최대쪽이라 "수치 인용 금지 셀"의 값이 천장으로 보고됐다
          (★L=500·alt=60·φ=90°: 65.75 dB @d=100 m(valid=False) vs 유효구역 61.26 dB @d=246 m).
          → 천장·피크는 게이트 적용값이 정본이고, raw 는 `*_ungated_*` 로 병기한다."""
    d = D_GRID_DEFAULT if d_grid is None else np.asarray(d_grid, float)
    snr = _eval_on(snr_of_d, d)
    if snr.shape != d.shape:
        raise ValueError(f"snr_of_d 길이 {snr.shape} != d_grid {d.shape}")
    th = np.broadcast_to(np.asarray(th_db, float), d.shape)

    vmask = (np.ones(d.shape, bool) if valid is None
             else np.broadcast_to(np.asarray(valid, bool), d.shape))

    g = snr - th
    g = np.where(np.isfinite(g), g, -np.inf)          # σ 결측 등은 미검출로
    g = np.where(vmask, g, -np.inf)

    det = g >= 0.0                                     # 문턱 이상 = 검출

    def _ceil(mask):
        s = np.where(np.isfinite(snr) & mask, snr, -np.inf)
        if not np.any(np.isfinite(s)):
            return float("nan"), float("nan")
        i = int(np.argmax(s))
        return float(s[i]), float(d[i])

    ceiling, peak_d = _ceil(vmask)                     # ★valid 게이트 적용(정본)
    ceiling_raw, peak_d_raw = _ceil(np.ones(d.shape, bool))   # 참고(인용 금지 셀 포함)

    # --- 단조성(하강) 판정 ---
    # ⚠ 격자 무관하게 재야 한다. 이웃차분 `diff<=tol` 로 재면 격자를 촘촘히 할수록 한 칸
    #   상승폭이 작아져 φ=0/10/30° 의 명백한 내부최대도 "단조"로 통과한다(스모크에서 실제로 겪음).
    #   그래서 **직전 최소값 대비 최대 상승폭**(=내부 봉우리 높이)으로 판정한다.
    s_fin = np.where(np.isfinite(snr), snr, np.nan)
    rise = np.nanmax(s_fin - np.fmin.accumulate(s_fin))
    monotone_ok = bool(np.isfinite(rise) and rise <= mono_tol_db)

    # --- 모든 부호변화 ---
    sgn = np.where(det, 1, -1)
    ch = np.nonzero(np.diff(sgn) != 0)[0]
    desc = [i for i in ch if sgn[i] == 1]              # +→−  (하강교차)
    asc = [i for i in ch if sgn[i] == -1]              # −→+

    def _interp(i):
        """log10(d) 축 선형보간(SNR 은 log d 에 대해 거의 선형)."""
        g0, g1 = g[i], g[i + 1]
        if not np.isfinite(g0) or not np.isfinite(g1) or g1 == g0:
            return float(d[i])
        w = g0 / (g0 - g1)
        return float(10.0 ** (np.log10(d[i]) + w * (np.log10(d[i + 1]) - np.log10(d[i]))))

    grid_limited = False
    never = False
    if desc:
        R = _interp(desc[-1])                          # ★최외곽 하강교차
    elif det[-1]:
        # 격자 **바깥 끝**이 아직 검출 → 축이 짧은 것이지 '미검출' 이 아니다.
        # (근거리 valid=False 셀 때문에 `np.all(det)` 는 절대 성립하지 않는다 — 감사 ① 참조)
        R = float(d[-1]); grid_limited = True
    elif not det.any():
        R = float("nan"); never = True                 # 어떤 거리에서도 미검출(천장<문턱)
    else:
        # 검출 구간은 있는데 하강교차도, 바깥 끝 검출도 없다 = 게이트가 바깥을 잘랐다.
        # 가장 바깥 검출 셀을 해로 잡고 `gate_limited` 로 표시한다(수치는 격자 해상도 한계).
        R = float(d[int(np.nonzero(det)[0][-1])]); grid_limited = True

    # --- 국소지수 ---
    with np.errstate(invalid="ignore", divide="ignore"):
        n_snr_arr = -np.gradient(np.where(np.isfinite(snr), snr, np.nan),
                                 np.log10(d)) / 10.0
    n_from_snr = (float(np.interp(np.log10(R), np.log10(d), n_snr_arr))
                  if np.isfinite(R) else float("nan"))
    n_kap, kap_at_R, req = float("nan"), float("nan"), float("nan")
    if kappa_of_d is not None and np.isfinite(R):
        kap = _eval_on(kappa_of_d, d)
        n_kap = float(n_local(kap, d, at=R))
        kap_at_R = float(np.interp(np.log10(R), np.log10(d), kap))
        req = float(np.sqrt(kap_at_R))
    n_pri = n_kap if np.isfinite(n_kap) else n_from_snr
    # ⚠ 감사 C1 — 두 지수는 **쓰임이 다르다.** 헷갈리면 σ 밴드 폭이 통째로 틀린다.
    #   n_geom (=n_kap, 2·dlnκ/dlnd) : 순수 기하 지수. 스펙 S1 의 ★1.03/3.76 이 이것이고
    #                                   `n_local_at_R90` 으로 인용하는 값이다.
    #   n_local_from_snr             : SNR(d) **총** 기울기. σ 가 el_look(d) 를 통해 d 에 의존하면
    #                                   둘이 갈린다(σ 고정 검증에서는 3.994 로 일치해 안 보인다).
    #   range_conv_exponent          : **dB↔거리 환산에 써야 하는 값** = 총기울기 우선.
    conv = n_from_snr if np.isfinite(n_from_snr) else n_kap

    return dict(
        R_m=R, R_eq_m=req, kappa_at_R=kap_at_R,
        n_local=n_pri, n_geom=n_kap, n_local_from_snr=n_from_snr,
        range_conv_exponent=conv,
        n_local_source=("kappa" if np.isfinite(n_kap) else "snr_slope"),
        snr_at_R_db=(float(np.interp(np.log10(R), np.log10(d), snr))
                     if np.isfinite(R) else float("nan")),
        th_at_R_db=(float(np.interp(np.log10(R), np.log10(d), th))
                    if np.isfinite(R) else float("nan")),
        snr_ceiling_db=ceiling, snr_peak_d_m=peak_d,
        snr_ceiling_ungated_db=ceiling_raw, snr_peak_d_ungated_m=peak_d_raw,
        monotone_ok=monotone_ok, snr_rise_db=float(rise),
        never_detectable=bool(never), frac_never_detectable=(1.0 if never else 0.0),
        grid_limited=bool(grid_limited),
        n_valid_cells=int(vmask.sum()), n_detected_cells=int(det.sum()),
        n_crossings=int(len(desc)), n_ascending=int(len(asc)),
        crossings_m=[_interp(i) for i in desc],
        d_min_m=float(d[0]), d_max_m=float(d[-1]),
        geometry_nonlinear=bool(np.isfinite(n_pri) and n_pri < 3.5),
        # 안쪽에 미검출 구멍이 있는데 하강교차가 하나도 없으면 격자·게이트가 해를 가린 것이다.
        inner_hole_warning=bool(len(asc) > 0 and len(desc) == 0),
    )


# --------------------------------------------------------------------------- #
#  4. 커버리지 (§7.3) — 블라인드/σ 두 인자로 분해 (S3/S4)
# --------------------------------------------------------------------------- #
def coverage_fraction(pd_of_psi, blind_mask, pd_th=0.9):
    """헤딩 커버리지 `C(d)` 를 **두 인자로 분해**해 반환 (S3).

        C = (1 − b_blind) · P_ψ[ Pd ≥ pd_th | 비블라인드 ]
          = factor_blind · factor_sigma

    왜 분해하나: 블라인드 검열은 σ 와 **완전상관**(항상 기체 ±90° 자세)이라 한 숫자로 뭉치면
    "자세 때문인지 도플러 때문인지" 를 못 읽는다. 캡션에 "블라인드=랜덤 아님" 을 박기 위한 분해다.
    블라인드 헤딩은 SNR 이 아무리 높아도 미검출로 센다(§7.2).

    인자: `pd_of_psi` Pd 배열(ψ 균등격자), `blind_mask` 같은 길이 bool(도플러 블라인드/앨리어싱).
    반환: `(C, factor_blind, factor_sigma)` — 전부 float.
    """
    pd = np.asarray(pd_of_psi, float)
    bm = (np.zeros(pd.shape, bool) if blind_mask is None
          else np.broadcast_to(np.asarray(blind_mask, bool), pd.shape))
    ok = ~bm
    f_blind = float(np.mean(ok))
    f_sigma = float(np.mean(pd[ok] >= pd_th)) if np.any(ok) else 0.0
    return float(f_blind * f_sigma), f_blind, f_sigma


def e_psi_pd(pd_of_psi, blind_mask=None):
    """헤딩 평균 검출확률 `E_ψ[Pd]` (S4).

    "Pd 0.9 @R90" 은 **헤딩의 절반이 0.9 를 넘는 거리**라서 그 지점의 평균 Pd 는 0.9 가 아니다
    (★스펙 인용 0.67~0.71). 헤드라인에는 두 숫자를 나란히 쓴다.
    블라인드 헤딩은 Pd=0 으로 계상한다(`blind_mask` 주면 그 자리를 0 으로 덮음).
    """
    pd = np.asarray(pd_of_psi, float).copy()
    if blind_mask is not None:
        pd[np.broadcast_to(np.asarray(blind_mask, bool), pd.shape)] = 0.0
    return float(np.mean(pd))


# --------------------------------------------------------------------------- #
#  5. 등감도선 Cassini (F1/R8)
# --------------------------------------------------------------------------- #
def cassini_contour(kappa, TX, RX, n=721, alt=None, r_max_factor=40.0, n_r=2000):
    """등감도선 **Cassini oval** `R1·R2 = κ` 의 xy 좌표 (N,2) [m].

    패시브의 감도는 `1/(R1²R2²)` 이므로 등감도선은 원도 타원도 아닌 Cassini oval 이다.
    κ < (L/2)² 이면 **두 잎(TX 주변·RX 주변)** 으로 갈라진다 — L 스윕 GIF(R8)의 핵심 그림.

    · `alt=None` : TX/RX 의 수평좌표를 초점으로 한 **평면 해석해**.
        극형식 r⁴ − 2a²r²cos2θ + (a⁴ − κ²) = 0 → r² = a²cos2θ ± √(κ² − a⁴sin²2θ), a=L/2.
        두 잎일 때는 바깥가지(+)와 안쪽가지(−)를 이어 닫힌 고리로 만든다.
        ⚠ 유효조건은 판별식 disc≥0 **만이 아니다** — r²≥0 도 함께 봐야 한다.
        (θ=π/2 에서 disc=κ²≥0 이지만 r²₊ = −a²+κ < 0 이다. 이걸 빼먹고 max(r²,0) 로
         뭉갰다가 스모크에서 R1R2 오차 300% 가 났다.)
    · `alt=<고도>` : 표적이 그 고도에 있을 때의 **진짜** 등κ선(3D 사거리 사용, TX/RX 의 z 반영).
        각 방위마다 반경축을 훑어 **최외곽 교차**를 취한다(solve_range 와 같은 철학).
    분리된 가지 사이에는 `np.nan` 행을 넣어 matplotlib 이 이어 그리지 않게 한다.
    """
    tx = np.asarray(TX, float).ravel()
    rx = np.asarray(RX, float).ravel()
    mid = 0.5 * (tx[:2] + rx[:2])
    axis = rx[:2] - tx[:2]
    L = float(np.hypot(*axis))
    ang0 = float(np.arctan2(axis[1], axis[0]))
    a = 0.5 * L
    kap = float(kappa)

    def _world(r, t):
        return np.stack([mid[0] + r * np.cos(t + ang0), mid[1] + r * np.sin(t + ang0)], -1)

    if alt is None:
        th = np.linspace(0.0, 2.0 * np.pi, int(n), endpoint=False)
        disc = kap ** 2 - (a ** 4) * np.sin(2 * th) ** 2
        root = np.sqrt(np.maximum(disc, 0.0))
        r2p = a ** 2 * np.cos(2 * th) + root
        r2m = a ** 2 * np.cos(2 * th) - root
        ok = (disc >= 0.0) & (r2p >= 0.0)
        if kap >= a ** 2:                                   # 단일 고리(닫아서 반환)
            xy = _world(np.sqrt(np.maximum(r2p, 0.0)), th)
            return np.r_[xy, xy[:1]]
        if not ok.any():
            return np.empty((0, 2))
        # 두 잎: θ 를 굴려 배열이 '무효'에서 시작하게 만든 뒤 연속구간마다 고리 하나
        sh = int(np.argmin(ok))
        th, r2p, r2m, ok = (np.roll(v, -sh) for v in (th, r2p, r2m, ok))
        segs, i = [], 0
        while i < len(th):
            if not ok[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(th) and ok[j + 1]:
                j += 1
            sl = slice(i, j + 1)
            out = _world(np.sqrt(np.maximum(r2p[sl], 0.0)), th[sl])
            inn = _world(np.sqrt(np.maximum(r2m[sl], 0.0)), th[sl])[::-1]
            segs.append(np.r_[out, inn, out[:1], np.full((1, 2), np.nan)])
            i = j + 1
        return np.vstack(segs) if segs else np.empty((0, 2))

    th = np.linspace(0.0, 2.0 * np.pi, int(n))

    # --- 고도 있는 진짜 등κ선: 방위마다 반경 훑어 최외곽 교차 ---
    z = float(alt)
    rr = np.linspace(1.0, r_max_factor * max(a, 1.0), int(n_r))
    pts = []
    for t in th:
        p = np.stack([mid[0] + rr * np.cos(t + ang0), mid[1] + rr * np.sin(t + ang0),
                      np.full_like(rr, z)], -1)
        k = (np.linalg.norm(p - tx, axis=1) * np.linalg.norm(p - rx, axis=1)) - kap
        s = np.sign(k)
        idx = np.nonzero(np.diff(s) != 0)[0]
        idx = [i for i in idx if s[i] < 0]                  # −→+ (안에서 밖으로 나가는 교차)
        if not idx:
            pts.append([np.nan, np.nan])
            continue
        i = idx[-1]
        w = k[i] / (k[i] - k[i + 1])
        r = rr[i] + w * (rr[i + 1] - rr[i])
        pts.append([mid[0] + r * np.cos(t + ang0), mid[1] + r * np.sin(t + ang0)])
    return np.asarray(pts, float)


# --------------------------------------------------------------------------- #
#  6. FS-3 평면지면 2-ray (§8.8, R1/R2) — 동반 사다리(헤드라인 아님)
# --------------------------------------------------------------------------- #
#: report09(챔버 바닥유령)이 쓰는 지면 상수 — `benchmark/geometry.py:92-100` 의
#: `FLOOR_EPS_R=5.24`(ITU-R P.2040 콘크리트 @3.5 GHz), `FLOOR_SIGMA = 0.0462·f_GHz^0.7822`.
#: FS-3 는 스펙 §8.8 이 지정한 **습토**(ε_r=15·σ=0.005 평탄)를 쓰므로 값이 다르다 — F16 이
#: 챔버 바닥유령(콘크리트)과 FS-3(습토)를 같은 축에 나란히 놓으므로 **캡션에 두 지면을 병기**할 것.
GROUND_REPO_CONCRETE = dict(eps_r=5.24, sigma_at_3p5GHz=0.1231,
                            sigma_model="0.0462 * f_GHz**0.7822",
                            source="benchmark/geometry.py FLOOR_EPS_R / FLOOR_SIGMA (report09)")
GROUND_FS3_SOIL = dict(eps_r=15.0, sigma=0.005, sigma_model="flat (declared)",
                       source="REPORT13_SPEC.md §8.8 (declared, no source doc)")


def fresnel_gamma(psi_i, eps_r=15.0, cond=0.005, pol="v", lam=None, fc=None,
                  psi_in_deg=True):
    """(보조) 평면지면 프레넬 반사계수 Γ(ψ) — ψ 는 **grazing(수평면 기준) 각**.

    ε_c = ε_r − j·σ/(ω ε₀)  (σ=`cond` [S/m]).  선언값 ε_r=15·σ=0.005(습토 대표값, 스펙 §8.8).
      수평(⊥) : Γ = (sinψ − √(ε_c−cos²ψ)) / (sinψ + √(ε_c−cos²ψ))
      수직(∥) : Γ = (ε_c sinψ − √(ε_c−cos²ψ)) / (ε_c sinψ + √(ε_c−cos²ψ))
    ψ→0(스침)에서 두 편파 모두 Γ→−1 → 상쇄(F→0)가 저각 다중로브의 원인이다.

    ⚠ **저장소에 같은 커널이 이미 있다**(감사 [4]): `benchmark/geometry._fresnel_floor`.
      그대로 import 하지 **못하는** 이유는 그 함수가 `abs(Γ)` 만 돌려줘 2-ray 위상
      `e^{−jkΔ}` 를 만들 수 없기 때문이다(각도 규약도 grazing↔normal 로 반대다).
      그래서 식을 옮겨 적었고, **상수를 맞추면 두 구현이 일치한다**(★스모크 max|Δ|Γ| = 1.0e-15).
      다만 지면이 다르다 — `GROUND_REPO_CONCRETE`(report09) vs `GROUND_FS3_SOIL`(스펙 §8.8):
        ψ=3° |Γ|_V 0.765(콘크리트) vs 0.653(습토) = −1.37 dB, ψ=30° 는 +9.57 dB **반대 방향**.
      에코는 F₁²F₂² 라 이 차이가 dB 로 최대 4배까지 벌어진다. 값 자체는 스펙이 이기지만,
      **F16 캡션·`meta.ground` 에 두 지면을 병기**하고 `benchmark/verify_freespace.py` 에
      "상수를 맞추면 `_fresnel_floor` 와 일치" 회귀 assert 를 박을 것(감사 [4] 조치).
    """
    if lam is None:
        if fc is None:
            raise ValueError("lam 또는 fc 중 하나는 필요하다(ε_c 의 도전율 항 때문)")
        lam = C0 / float(fc)
    f = C0 / float(lam)
    psi = np.radians(np.asarray(psi_i, float)) if psi_in_deg else np.asarray(psi_i, float)
    eps_c = float(eps_r) - 1j * float(cond) / (2 * np.pi * f * EPS0)
    root = np.sqrt(eps_c - np.cos(psi) ** 2)
    s = np.sin(psi)
    if str(pol).lower().startswith("v"):
        g = (eps_c * s - root) / (eps_c * s + root)
    else:
        g = (s - root) / (s + root)
    return g if np.ndim(g) else complex(g)


def two_ray_F(psi_i, dR, gamma, lam, fc=None, eps_r=15.0, cond=0.005,
              pol="v", psi_in_deg=True):
    """평면지면 **2-ray 진폭인자** `F = |1 + Γ(ψ)·e^{−jkΔ}|` (FS-3, §8.8).

    · `psi_i` : 지면 반사점의 grazing 각[deg 기본]
    · `dR`    : 직접경로↔반사경로 행로차 Δ [m] (`two_ray_path_diff` 로 계산)
    · `gamma` : 반사계수(복소). **None 을 주면** `fresnel_gamma(psi_i, ε_r, σ, pol)` 로 계산
    · `lam`   : 파장[m] — `fc` 를 대신 주려면 `lam=None, fc=…`

    ⚠ **스펙 §9 정정 요청**(감사 B1). 스펙은 `two_ray_F(psi_i, dR, gamma)` 로 적었지만
      Δ 만으로는 위상 `e^{−jkΔ}` 를 만들 수 없다 — k=2π/λ 가 물리적으로 필수다. 예전 구현은
      λ 를 꼬리 kwarg 로 두어 **스펙대로 3인자로 부르면 런타임 깊은 곳에서 ValueError** 가 났고
      (FS-3 스윕 중간에 죽는다), 이제 `lam` 을 **4번째 필수 위치인자**로 올려 불일치가
      호출 즉시 TypeError 로 보이게 했다. 자동 Γ 가 필요하면 `two_ray_F(ψ, Δ, None, λ)`.

    에코는 leg 두 개(TX→표적, 표적→RX)를 각각 겪으므로 전력배율은 `F₁²F₂²`
    (=`two_ray_f4_db`). ★스펙 인용 범위 F⁴∈[−20,+11.5] dB = 거리 0.32~1.94배 —
    **자유공간은 상한이 아니다**(R1). 이 함수가 그 정직성 점검의 커널이다.
    """
    if lam is None:
        if fc is None:
            raise ValueError("lam 또는 fc 가 필요하다(위상 k=2π/λ)")
        lam = C0 / float(fc)
    if gamma is None:
        gamma = fresnel_gamma(psi_i, eps_r=eps_r, cond=cond, pol=pol, lam=lam,
                              psi_in_deg=psi_in_deg)
    k = 2.0 * np.pi / float(lam)
    F = np.abs(1.0 + np.asarray(gamma) * np.exp(-1j * k * np.asarray(dR, float)))
    return _as_float(F)


def two_ray_path_diff(h_t, h_r, ground_range):
    """(보조) 평면지면 행로차 Δ 와 grazing 각 ψ.  반환 `(dR_m, psi_deg)`.

    Δ = √(d² + (h_t+h_r)²) − √(d² + (h_t−h_r)²),  ψ = atan((h_t+h_r)/d)  (평면지구).
    """
    d = np.asarray(ground_range, float)
    s, dh = float(h_t) + float(h_r), float(h_t) - float(h_r)
    dR = np.sqrt(d ** 2 + s ** 2) - np.sqrt(d ** 2 + dh ** 2)
    psi = np.degrees(np.arctan2(s, d))
    return _as_float(dR), _as_float(psi)


def two_ray_f4_db(F1, F2):
    """(보조) 두 leg 의 전력배율 `F⁴ = F₁²F₂²` 을 dB 로 = `20log10(F₁F₂)`.

    거리배율은 `range_factor(F4_db, n=n_local)` — **F4_db 는 이미 부호 있는 ΔSNR** 이므로
    그대로 넣는다(감사 A4 규약): +11.5 dB → ×1.94, −20 dB → ×0.32 (n=4 기준).
    """
    p = np.asarray(F1, float) * np.asarray(F2, float)
    return _as_float(20.0 * np.log10(np.maximum(p, 1e-12)))


# --------------------------------------------------------------------------- #
#  7. 벽 지도 라벨 (§8) — 어느 하나를 헤드라인으로 세우지 않는다
# --------------------------------------------------------------------------- #
def classify_limit(n0_parts, gates=None, geometry_nonlinear=False):
    """(보조) 셀의 `limit` 라벨 (§8, LIMIT_ENUM).

    우선순위: **유효범위 게이트 위반**(수치 인용 금지 셀) → 그다음 **지배 잡음항**.
      게이트: beta_ok(β≤90°) / farfield_ok(d≥2D²/λ) / walk_ok(T_CPI<ΔR_b/v_r) /
              dpi_unsuppressible(Δθ<빔폭/2)
      잡음항: thermal / adc / dpi_residual / inr 중 최대
    부라벨(따로 반환): `geometry_nonlinear`(n_local<3.5, S1), `nyquist_alias`(|f_d|≥PRF/2, F8).
    나이퀴스트는 **거리를 정하는 벽이 아니라 헤딩 검열**이라 LIMIT_ENUM 에 넣지 않고
    `ranges..nyquist_ok`·`alias_heading_frac` 로 따로 보고한다(스펙 §10 스키마와 일치).
    반환 `(limit, extras)`.
    """
    g = dict(gates or {})
    extras = ["geometry_nonlinear"] if geometry_nonlinear else []
    if "nyquist_ok" in g and not g["nyquist_ok"]:
        extras.append("nyquist_alias")
    if g.get("dpi_unsuppressible", False):
        return "dpi_unsuppressible", extras
    for key, lab in (("beta_ok", "beta"), ("farfield_ok", "farfield"),
                     ("walk_ok", "walk")):
        if key in g and not g[key]:
            return lab, extras
    parts = {k: float(v) for k, v in n0_parts.items()
             if k in ("thermal", "adc", "dpi_residual", "inr")}
    if not parts:
        return "thermal", extras
    return max(parts, key=parts.get), extras


if __name__ == "__main__":                       # 간단 자기점검(스모크는 별도 스크립트)
    lam = C0 / 1.843e9
    Pd = direct_power_w(63.0, 10.0, lam, 500.0)
    B = 30.72e6
    th_psd = n0_thermal(5.0, 1.0)                # PSD [W/Hz]
    print(f"LTE L=500  P_dir={Pd:.4g} W  DNR = {dnr_db(Pd, n0_thermal(5.0, B)):.2f} dB (직접파/잡음)")
    print(f"  N0_dpi(60dB)/N0_th = {lin2db(n0_dpi(Pd, 60.0, B) / th_psd):+.2f} dB"
          f"  → 거리 ×{range_factor(-lin2db(n0_effective(Pd, 5.0, B, eca_depth_db=60.0)['total'] / th_psd)):.4f}")
