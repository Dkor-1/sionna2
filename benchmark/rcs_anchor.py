# -*- coding: utf-8 -*-
"""
rcs_anchor.py — 선행 방법론(분포적합·μ/ε 회귀·금속구 교정·분위점·RMSE)을 그대로 차용해
                우리 SBR+PO σ 를 문헌과 **정량비교**한다  →  outputs/rcs_anchor.json
================================================================================================
report08 이 "보류(defer)" 로 남긴 절대 σ 판정을, 문헌이 실제로 쓴 절차로 채운다.
정독노트: docs/DRONE_ISAC_PRIOR_READING.md  §2 · §4-P1(9~16).

■ 핵심 규칙 (왜 이렇게 짰나)
  1. ⚠ **원시 σ(az) 로만** 분포적합·회귀·분위점을 낸다. report2 의 `sigma_smooth` 는 밴드 5주파수
     평균 + 3° 각도창을 거쳐 **널을 ~18 dB 메운** 값이다(rcs_po.py:191-193). 통계에 쓰면 왜곡된다.
     원시는 rcs_sbr.rcs_sbr_batch 를 **단일 주파수·단일 az격자·평활 없이** 호출해 얻는다.
  2. **커널 재구현 금지** — σ 는 rcs_sbr, 재질은 drones.DRONE_GROUP_MAT 을 쓴다.
  3. **날조 금지** — 문헌 기준값은 노트가 PDF 로 검증한 것만 출처주석과 함께 상수(LITERATURE)로.
     우리 값은 전부 계산으로.

실행:
  cd /home/yunjung/workspace/sionna2
  SIONNA2_GPU=3 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/rcs_anchor.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
from scipy import stats as st

# rcs_sbr 는 import 시점에 gpu.pick() 을 부른다 (mitsuba 전에 GPU 고정). SIONNA2_GPU 로 강제.
from rcs_sbr import rcs_sbr_batch, DEFAULT_DIV      # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT  # noqa: E402
from geom import uv_sphere                          # noqa: E402

C0 = 299792458.0

# 드론 메쉬는 spec 결정적 → 회귀 22 주파수마다 재빌드하지 않도록 캐시(정정성 무관, 속도만).
_MESH_CACHE = {}


def _mesh_for(drone):
    if drone not in _MESH_CACHE:
        _MESH_CACHE[drone] = build_drone(DRONES[drone])
    return _MESH_CACHE[drone]

#  우리 3 밴드 (report2_waveform_rcs.json meta 와 동일) — 문헌 밴드와 겹치는 sub-6 만.
BANDS = {
    "LTE 1.843 GHz": 1.843e9,
    "5G 3.5 GHz":    3.500e9,
    "WiFi 5.21 GHz": 5.210e9,
}

DRONE_KEYS = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"]


# --------------------------------------------------------------------------- #
#  문헌 기준값 (전부 정독노트가 원문 PDF 로 검증한 것 — §2·§4-P1). 우리 값 아님.
# --------------------------------------------------------------------------- #
LITERATURE = {
    "_provenance": "docs/DRONE_ISAC_PRIOR_READING.md §2·§4-P1, 원문 PDF 확인분만",
    # μ(f)=a·f+b [dBsm, f in GHz], ε(f)=c·f+d [dB]. 둘 다 방위 통계(선형평균 μ / dB표준편차 ε).
    "mu_eps": {
        "multiband_phantom3": {   # Das et al., IEEE WCL 15:3731, 2026 · Table III θb=0°
            "target": "DJI Phantom 3 (350x200 mm)", "geom": "monostatic far-field",
            "mu_a": 0.21, "mu_b": -19.19, "eps_c": 0.03, "eps_d": 5.16,
            "mu_at_bands": {"LTE 1.843 GHz": -18.80, "5G 3.5 GHz": -18.46, "WiFi 5.21 GHz": -18.10},
            "note": "본문 명시 linear average → 우리 mean_dbsm 과 사과-대-사과",
        },
        "mono3d_theta90": {       # Yuan et al., EuCAP 2025 · §IV θ=90°
            "target": "DJI Phantom 3 (350x200 mm)", "geom": "monostatic CATR, VV",
            "mu_a": 0.315, "mu_b": -16.15,
            "mu_at_bands": {"LTE 1.843 GHz": -15.57, "5G 3.5 GHz": -15.05, "WiFi 5.21 GHz": -14.51},
            "note": "같은 캠페인인데 multiband 와 3.2~3.6 dB 높다 = dB영역평균 의심(§2-2)",
        },
    },
    # 분포 적합도 거리 (작을수록 좋음). Rician / Gamma / LogNormal.
    "distribution": {
        "multiband_phantom3": {"metric": "Anderson-Darling", "rician": 0.436,
                               "note": "Rician 최선(식5). Gamma/LogNormal 개별값은 노트에 없음"},
        "mono3d_avg": {"metric": "Cramer-von Mises (avg over aspects)",
                       "rician": 0.28, "gamma": 0.31, "lognormal": 0.48,
                       "note": "Rician < Gamma < LogNormal"},
    },
    # 평균전력 정규화 σ 의 분위점 [dB] (mono3d §IV). P10 / P1.
    "percentiles_norm": {
        "favorable_dominant_present": {"P10": -8.5, "P1": -18.5},
        "poor_dominant_absent":       {"P10": -10.0, "P1": -20.0,
                                       "note": "지수분포 이론 −9.77/−19.98 과 일치 = Swerling I/II"},
    },
    # 적합 RMSE [dB] (unified-rcs Eq.18)
    "fit_rmse_db": {"AAV": 2.414, "vehicle": 1.831, "human": 2.245,
                    "source": "Zhang et al., IEEE JSAC 44:702, 2026"},
    # 금속구 절대교정
    "sphere_calibration": {
        "unified_rcs_0p5m": {"diameter_m": 0.5, "radius_m": 0.25, "freq_ghz": 28.0,
                             "theory_dbsm": -7.07, "measured_dbsm": -8.96, "dev_db": 1.89,
                             "source": "unified-rcs §III-B p.709"},
        "mono3d_r17p8cm": {"radius_m": 0.178, "theory_dbsm": -10.02,
                           "source": "mono3d, 병행 교정구"},
        "pass_threshold_db": 2.0,
        "note": "합격선 <2 dB = unified-rcs 실측 편차 1.89 dB 를 따른다",
    },
}


# --------------------------------------------------------------------------- #
#  1. 원시 σ(az) — 단일 주파수·단일 격자·평활 없음
# --------------------------------------------------------------------------- #
def raw_sigma_az(drone, fc, el, n_az=360, div=16):
    """드론 1종의 **원시** 모노스태틱 σ(az) 배열 [m²] (평활·대역평균 없음, 단일 fc).

    rcs_sbr.rcs_sbr_batch 를 az=linspace(0,360,n_az,endpoint=False) 로 호출한다.
    재질은 DRONE_GROUP_MAT (Sionna 와 동일 출처), 격자 = λ/div (report2 는 div=16).
    ⚠ report2 의 sigma_smooth (밴드평균+3°창) 과 달리 이 값이 분포/회귀/분위점의 유일한 입력이다."""
    mesh = _mesh_for(drone)
    gm = {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}   # rcs_po.drone_rcs_pattern 과 동일 규약
    lam = C0 / float(fc)
    az = np.linspace(0.0, 360.0, int(n_az), endpoint=False)
    sig = rcs_sbr_batch(mesh, gm, fc, az_deg=az, el_deg=float(el), spacing=lam / div,
                        cache_key=(drone, round(fc / 1e6), float(el), "raw"))
    return np.atleast_1d(np.asarray(sig, float))


# --------------------------------------------------------------------------- #
#  2. μ(f)=a·f+b, ε(f)=c·f+d 선형회귀 (1.8–6 GHz, 0.2 GHz 간격 ≥20점)
# --------------------------------------------------------------------------- #
def mu_eps_regression(drone, band_fc, el, freqs=None, n_az=360, div=16):
    """1.8–6 GHz 를 0.2 GHz 간격으로 스윕(≥20점). 각 fc 에서
        μ(f) = 10log10(mean(σ_lin))   [dBsm]   (방위 선형평균 = 우리 mean_dbsm 규약)
        ε(f) = std(10log10(σ_lin))    [dB]     (방위 dBsm 표준편차)
    를 만들고 μ=a·f+b, ε=c·f+d 를 최소자승 회귀한다 (f 단위 GHz — 문헌 계수와 같은 축).

    band_fc: 관심 밴드. 회귀선에서 그 밴드의 μ̂·ε̂ 를 함께 돌려준다(대조 편의).
    반환: dict(a,b,c,d, R2_mu, R2_eps, freqs_ghz, mu, eps, mu_at_band, eps_at_band)."""
    if freqs is None:
        freqs = np.arange(1.8e9, 6.0e9 + 1.0, 0.2e9)     # 1.8,2.0,...,6.0 → 22점
    freqs = np.asarray(freqs, float)
    fghz = freqs / 1e9
    mu, eps = [], []
    for f in freqs:
        s = raw_sigma_az(drone, f, el, n_az=n_az, div=div)
        s = np.maximum(s, 1e-30)
        mu.append(10.0 * np.log10(np.mean(s)))
        eps.append(float(np.std(10.0 * np.log10(s))))
    mu = np.asarray(mu); eps = np.asarray(eps)

    def _lin(x, y):
        a, b = np.polyfit(x, y, 1)
        yhat = a * x + b
        ss_res = float(np.sum((y - yhat) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        return float(a), float(b), r2

    a, b, r2_mu = _lin(fghz, mu)
    c, d, r2_eps = _lin(fghz, eps)
    fb = float(band_fc) / 1e9
    return dict(a=a, b=b, c=c, d=d, R2_mu=r2_mu, R2_eps=r2_eps,
                n_points=len(freqs), freqs_ghz=fghz.tolist(),
                mu=mu.tolist(), eps=eps.tolist(),
                mu_at_band=a * fb + b, eps_at_band=c * fb + d)


# --------------------------------------------------------------------------- #
#  3. 분포 적합 (Rician / Gamma / LogNormal) + 적합도 거리 (AD·CvM)
# --------------------------------------------------------------------------- #
def _ad_distance(F, literal=True):
    """Anderson–Darling 거리. F = 오름차순 σ 에서의 적합 CDF 값 (정렬 필수).

    literal=True  : 정독노트 §4-P1-13 이 준 형태 그대로 —
                    d_AD = −K − (1/K)Σ_k(2k−1)[ln F(σ_(k)) + ln F(σ_(K+1−k))]
    literal=False : 교과서 Anderson–Darling (multiband 기준 0.436 이 근거로 하는 형태) —
                    A² = −K − (1/K)Σ_k(2k−1)[ln F(σ_(k)) + ln(1 − F(σ_(K+1−k)))]
    ⚠ 노트 필사본은 둘째항의 (1−·) 가 빠져 있어 교과서 AD 와 다르다. 대조는 교과서형이 apples-to-apples."""
    F = np.clip(np.asarray(F, float), 1e-12, 1.0 - 1e-12)
    K = len(F)
    kk = np.arange(1, K + 1)
    Frev = F[::-1]                                   # F(σ_(K+1−k))
    if literal:
        s = np.sum((2 * kk - 1) * (np.log(F) + np.log(Frev)))
    else:
        s = np.sum((2 * kk - 1) * (np.log(F) + np.log(1.0 - Frev)))
    return float(-K - s / K)


def _cvm_distance(F, N):
    """Cramér–von Mises 거리 (mono3d):  d_C = √( 1/(12N) + Σ_i |F(σ_(i)) − (2i−1)/(2N)|² )."""
    F = np.asarray(F, float)
    i = np.arange(1, N + 1)
    w2 = 1.0 / (12.0 * N) + np.sum((F - (2 * i - 1) / (2.0 * N)) ** 2)
    return float(np.sqrt(w2))


def _fit_one_domain(x_sorted, N):
    """오름차순 표본 x_sorted 한 도메인에 Rician/Gamma/LogNormal MLE(loc=0) → 거리 3종."""
    dists = {"rician": st.rice, "gamma": st.gamma, "lognormal": st.lognorm}
    out, frozen = {}, {}
    for name, dist in dists.items():
        params = dist.fit(x_sorted, floc=0.0)        # 양수 support → loc=0 고정
        fz = dist(*params)
        F = fz.cdf(x_sorted)                         # x 오름차순 → F 오름차순
        out[name] = dict(
            params=[float(p) for p in params],
            d_AD=_ad_distance(F, literal=True),
            d_AD_textbook=_ad_distance(F, literal=False),
            d_C=_cvm_distance(F, N),
        )
        frozen[name] = fz
    best_AD = min(out, key=lambda k: out[k]["d_AD_textbook"])   # 대조는 교과서형으로
    best_CvM = min(out, key=lambda k: out[k]["d_C"])
    return dict(N=N, fits=out, best_by_AD=best_AD, best_by_CvM=best_CvM), frozen


def fit_distributions(sigma_lin):
    """원시 방위 표본에 Rician/Gamma/LogNormal MLE 적합 — **두 변량 도메인**으로 낸다.

    ⚠ 변량 정합(감사 지적, formulas §5): scipy.stats.rice 는 **진폭**(복소가우시안 크기)
    분포다. 문헌(mono3d/multiband)이 Rician 을 채택한 대상도 통상 **진폭**(정합필터/채널
    계수의 크기)이다. 따라서 σ[m²](전력)에만 적합하면 Rician 이 구조적으로 불리해져
    사과-대-사과가 깨진다. 두 도메인을 모두 실어 report08 이 올바른 열로 비교하게 한다:
      · power     : σ_lin [m²] 그대로 (Swerling 전력 관점 — Gamma/LogNormal 유리)
      · amplitude : √σ (문헌 Rician + scipy.stats.rice 규약과 정합)
    Gamma 는 제곱변환에 닫혀있지 않고 LogNormal 은 닫혀있으므로 세 분포 모두 도메인의존.
    ⚠ σ 는 선형[m²], 각 도메인에서 오름차순 정렬한다.
    반환: (summary{power,amplitude}, frozen{power,amplitude})."""
    x = np.sort(np.asarray(sigma_lin, float))
    x = x[x > 0]
    N = len(x)
    pow_sum, pow_frz = _fit_one_domain(x, N)                       # 전력 σ[m²]
    amp = np.sort(np.sqrt(x))                                      # 진폭 √σ
    amp_sum, amp_frz = _fit_one_domain(amp, N)
    pow_sum["variate"] = "power sigma [m^2]"
    amp_sum["variate"] = "amplitude sqrt(sigma) — matches literature Rician / scipy.stats.rice"
    summary = dict(power=pow_sum, amplitude=amp_sum)
    frozen = dict(power=pow_frz, amplitude=amp_frz)
    return summary, frozen


# --------------------------------------------------------------------------- #
#  4. 금속구 절대교정 — PEC 구 SBR+PO σ vs 이론 πr²
# --------------------------------------------------------------------------- #
def sphere_calibration(fc, radius_m=(0.25, 0.178), n_az=8, div=16, seg=180, rings=90):
    """지름 0.5 m (r=0.25, 이론 πr²=−7.07 dBsm) 및 mono3d r=17.8 cm (−10.02 dBsm) PEC 구를
    우리 rcs_sbr(group_mat={"metal":"metal"}) 로 돌려 편차[dB] 를 낸다. 합격선 <2 dB.
    ⚠ 곡면 격자 위상 에일리어싱(±1.5 dB) 을 줄이려 n_az 방위 평균 + 내장 jitter 를 쓴다.
    ⚠ 스펙 시그니처의 둘째 반지름 0.089 는 πr²=−16.04 로 mono3d −10.02 앵커와 안 맞아
       원문값 r=0.178 로 교정했다(아래 return 리포트 참조)."""
    lam = C0 / float(fc)
    az = np.linspace(0.0, 360.0, int(n_az), endpoint=False)
    res = []
    for r in radius_m:
        sph = uv_sphere(float(r), seg=seg, rings=rings, group="metal")
        sig = rcs_sbr_batch(sph, {"metal": "metal"}, fc, az_deg=az, el_deg=0.0,
                            spacing=lam / div,
                            cache_key=("sphere", round(r * 1e4), round(fc / 1e6), seg, rings))
        sig = np.atleast_1d(np.asarray(sig, float))
        sbr = float(np.mean(sig))
        theory = float(np.pi * r * r)
        sbr_db = 10.0 * np.log10(max(sbr, 1e-30))
        th_db = 10.0 * np.log10(theory)
        res.append(dict(radius_m=float(r), r_over_lambda=float(r / lam),
                        theory_dbsm=th_db, sbr_dbsm=sbr_db, dev_db=sbr_db - th_db,
                        pass_lt2db=bool(abs(sbr_db - th_db) < 2.0)))
    return dict(fc_ghz=float(fc) / 1e9, div=div, spheres=res)


# --------------------------------------------------------------------------- #
#  5. 평균전력 정규화 분위점 P10 / P1 [dB]
# --------------------------------------------------------------------------- #
def percentiles_norm(sigma_lin):
    """평균전력(선형평균) 으로 정규화한 σ 의 10%/1% 분위점 [dB] (mono3d §IV).
    P10 = 표본의 10% 가 그 아래인 dB 값. 문헌: −8.5/−18.5 (우세성분 有), −10/−20 (無)."""
    s = np.asarray(sigma_lin, float)
    s = s[s > 0]
    snorm = s / np.mean(s)
    sdb = 10.0 * np.log10(snorm)
    return dict(P10_db=float(np.percentile(sdb, 10)),
                P1_db=float(np.percentile(sdb, 1)),
                mean_lin=float(np.mean(s)))


# --------------------------------------------------------------------------- #
#  6. 적합 RMSE [dB] — QQ 잔차 (unified-rcs Eq.18 정신: 측정 dB vs 적합 dB)
# --------------------------------------------------------------------------- #
def fit_rmse_db(sigma_lin, frozen_by_domain):
    """분포 적합의 RMSE[dB] (QQ 잔차). 정렬 표본의 경험분위 p_i=(i−0.5)/N 에서
       측정 σ_dB(정렬) 와 적합분포 이론분위를 **σ_dBsm 축에서** 비교한다.
       amplitude 도메인 ppf 는 진폭이므로 σ=(진폭)² 로 환산해 같은 dBsm 축에 놓는다.
       RMSE = √(mean((σ_dB − σ̂_dB)²)). frozen_by_domain = {power:{..}, amplitude:{..}}.
       ⚠ 감사 지적(formulas §4): 이 값은 **분포적합 QQ-RMSE(우리 정의)** 이지 unified-rcs
         Eq.18(AAV 2.414 = B1(φ) 각도패턴 적합잔차로 추정) 과 같은 양이 아니다. 직접 등치 금지.
       반환: {power:{분포:rmse,best}, amplitude:{분포:rmse,best}}."""
    x = np.sort(np.asarray(sigma_lin, float))
    x = x[x > 0]
    N = len(x)
    p = (np.arange(1, N + 1) - 0.5) / N
    x_db = 10.0 * np.log10(x)                                 # 측정 σ [dBsm]
    res = {}
    for dom, frozen in frozen_by_domain.items():
        out = {}
        for name, fz in frozen.items():
            q = np.maximum(fz.ppf(p), 1e-30)
            q_pow = q if dom == "power" else q * q            # 진폭→전력 σ
            q_db = 10.0 * np.log10(np.maximum(q_pow, 1e-30))
            m = np.isfinite(q_db)
            out[name] = float(np.sqrt(np.mean((x_db[m] - q_db[m]) ** 2)))
        out["best"] = min((k for k in out), key=lambda k: out[k])
        res[dom] = out
    return res


# --------------------------------------------------------------------------- #
#  main — 5기종 × 3밴드 × {el=0, el=15} 원시σ → 전부 계산 → JSON
# --------------------------------------------------------------------------- #
def run_all(drones=DRONE_KEYS, bands=BANDS, els=(0.0, 15.0),
            n_az_band=720, n_az_reg=360, div=16, out_path=None):
    """전체 산출. ⚠ 감사 반영:
      · n_az_band=720 — 분위점(특히 P1)이 360 에서 미수렴(360↔720 에서 −1.1 dB 이동,
        raw-not-smooth 결함1)이므로 밴드 σ(→percentiles/dist/RMSE)는 720 로 산출.
      · n_az_reg=360  — 회귀 μ/ε(선형평균·dB표준편차)는 360 에서 수렴하므로 유지(속도).
    """
    t0 = time.time()
    result = {
        "meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "gpu": os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
            "n_az_band": n_az_band, "n_az_reg": n_az_reg,
            "div": div, "sbr_default_div": DEFAULT_DIV,
            "els_deg": list(els), "bands": {k: v for k, v in bands.items()},
            "regression_sweep": "1.8-6.0 GHz @ 0.2 GHz (22 pts)",
            "raw_only": "분포/회귀/분위점은 전부 원시 σ(az) — sigma_smooth 아님",
            "caveats": {
                "min_dbsm": ("min/median/peak/mean 은 커널 기본 jitter=2(2×2 격자위상 평균) "
                             "산출. min 은 코히런트 진짜 널바닥이 아니라 격자평균 진단값 "
                             "(jitter 1↔3 에서 ~3 dB 이동). P1/P10/mean/분포선택은 jitter-강건."),
                "n_az_band": ("분위점 수렴: P1 은 n_az=360→720 에서 ~1.1 dB 깊어진 뒤 수렴. "
                              "그래서 밴드 σ 는 720 로 산출. mean/P10/분포선택은 360 에서 이미 수렴."),
                "distribution_variate": ("분포적합은 두 도메인: power(σ[m²]) / amplitude(√σ). "
                    "scipy.stats.rice 는 진폭분포이고 문헌 Rician 도 통상 진폭 규약이므로 "
                    "문헌 Rician 과의 사과-대-사과는 amplitude 도메인. power 도메인은 "
                    "Gamma/LogNormal 이 구조적으로 유리(변량 불일치)."),
                "fit_rmse": ("fit_rmse_db 는 분포적합 QQ-RMSE(우리 정의). unified-rcs Eq.18 "
                             "(AAV 2.414)은 B1(φ) 각도패턴 적합잔차로 추정 — 측정대상 다름, 직접 등치 금지."),
                "cvm": "d_C = √W² (노트 식이 √ 포함). 순위비교 안전, 절대치는 √스케일.",
            },
        },
        "literature": LITERATURE,
        "sphere_calibration": {},
        "drones": {},
    }

    # 금속구 교정 — 밴드마다 (주파수 의존 확인). el 무관이라 els 중복 실행돼도 동일값.
    for bname, fc in bands.items():
        result["sphere_calibration"][bname] = sphere_calibration(fc, div=div)

    for dk in drones:
        result["drones"][dk] = {"name": DRONES[dk].name, "bands": {}, "regression": {}}
        for el in els:
            reg = mu_eps_regression(dk, bands["5G 3.5 GHz"], el, n_az=n_az_reg, div=div)
            result["drones"][dk]["regression"][f"el{int(el)}"] = reg
        for bname, fc in bands.items():
            result["drones"][dk]["bands"][bname] = {}
            for el in els:
                sig = raw_sigma_az(dk, fc, el, n_az=n_az_band, div=div)
                fit_sum, frozen = fit_distributions(sig)
                s = np.maximum(sig, 1e-30)
                entry = dict(
                    fc_ghz=fc / 1e9, el_deg=el, n_az=n_az_band,
                    mean_dbsm=float(10 * np.log10(np.mean(s))),
                    median_dbsm=float(np.median(10 * np.log10(s))),
                    peak_dbsm=float(10 * np.log10(np.max(s))),
                    min_dbsm=float(10 * np.log10(np.min(s))),
                    distributions=fit_sum,
                    percentiles=percentiles_norm(sig),
                    fit_rmse_db=fit_rmse_db(sig, frozen),
                )
                result["drones"][dk]["bands"][bname][f"el{int(el)}"] = entry
                print(f"  {dk:10s} {bname:14s} el{int(el):2d}  "
                      f"mean={entry['mean_dbsm']:+6.2f} P10/P1={entry['percentiles']['P10_db']:+6.2f}/"
                      f"{entry['percentiles']['P1_db']:+6.2f}  "
                      f"best[pow/amp CvM]={fit_sum['power']['best_by_CvM']}/{fit_sum['amplitude']['best_by_CvM']}",
                      flush=True)

    result["meta"]["runtime_s"] = time.time() - t0
    if out_path:
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n[saved] {out_path}  ({result['meta']['runtime_s']:.0f}s)", flush=True)
    return result


if __name__ == "__main__":
    import argparse
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(here, "outputs", "rcs_anchor.json"))
    ap.add_argument("--els", default="0,15", help="쉼표구분 el 목록 (예: '0' 또는 '0,15')")
    ap.add_argument("--n-az-band", type=int, default=720)
    ap.add_argument("--n-az-reg", type=int, default=360)
    ap.add_argument("--drones", default=",".join(DRONE_KEYS))
    a = ap.parse_args()
    els = tuple(float(x) for x in a.els.split(","))
    dks = a.drones.split(",")
    run_all(drones=dks, els=els, n_az_band=a.n_az_band, n_az_reg=a.n_az_reg,
            out_path=a.out)
