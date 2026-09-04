# -*- coding: utf-8 -*-
"""
sigma_anchor.py — 측정 앵커 σ(f) 레이어. 표준화 문헌의 분해형

        σ(f, φ, θ)  =  A(f) · B1(φ, θ) · B2

    · B1(φ,θ) **각도패턴** ← 우리 SBR+PO 커널 (부위별 재질 + 광선추적 가림).
    · A(f)    **레벨과 주파수의존** ← **측정**. 우리 PO 기울기가 알려진 이유로 3~8배 가파르기 때문.
    · B2      **잔차분포** ← 이미 적합돼 있다 (benchmark/rcs_anchor.py, Rician/Gamma/LogNormal).

  분해형 자체는 Zhang et al., "A Unified RCS Modeling of Typical Targets for 3GPP ISAC Channel
  Standardization", IEEE JSAC 44:702, 2026 이 쓰는 형태다. A(f) 를 측정에서 가져오는 것도 그쪽이다.

================================================================================================
⭐ 이 모듈이 하는 일은 **재보정(re-levelling)** 이지 **검증(validation)** 이 아니다.
   우리 σ 의 절대값이 맞다는 증거는 이 파일 어디에도 없다. 있는 것은 "외부 측정 한 건에
   맞춰 레벨과 기울기를 옮겼다" 는 사실과, 무엇을 얼마나 옮겼는지의 원장(ledger)뿐이다.
   리포트는 반드시 **어느 양이 기하에서 왔고 어느 양이 측정에서 왔는지** 나눠 적어야 한다.
================================================================================================

■ 왜 필요한가 — 반증된 것이 아니라 **측정된** 결함
  우리 커널의 σ(f) 기울기(el=0, 1.8→5.21 GHz 3밴드 최소자승)는 기종별 0.742~1.699 dB/GHz 다
  (outputs/rcs_anchor.json 에서 계산; 1.8~6.0 GHz 22점 회귀로는 0.94~1.54). 같은 급 기체의
  **측정** 기울기는 0.175~0.315 dB/GHz (Yuan θ별) 또는 0.21 dB/GHz (Das) 다.
  ⛔**«3~8배 가파르다» 는 부분대역↔전대역을 섞은 값이라 내린다**(2026-09-04,
    `docs/ANCHOR_SUBBAND.md`). 측정 넷은 **1.8~18.2 GHz 전대역 적합**이고 우리 수는
    3밴드/좁은대역 적합이다. **같은 창에서 재면 1.8~6.0 GHz 에서 +1.45 대 +0.41 = 3.5배**다.
  ⚠ 이 0.175~0.315 는 **우리 대역과 겹치는 행만** 센 값이다(SLOPE_CENSUS.overlaps_our_band=True,
    4행 = Phantom 3 한 측정의 네 통계). **전 기체 총람은 0.07~0.315** 이지만 하한 0.07 은
    das_mini2 의 **21~27 GHz** 값이라 1.843/3.5/5.21 GHz 비교에 넣으면 외삽이다.
    → 어느 쪽을 쓰든 **구간을 함께 적는다**. 범위를 안 밝히면 둘 다 틀린 인용이 된다.
    (docs/RETRACTION_LOG.md A2 · A11)
  원인은 알려져 있다: PO 는 정반사항(∝f²)만 남기고 **모서리 회절항(주파수 무관)** 을 버린다.
  우리 커널에 PTD 보정이 없으므로 이 오차는 무작위가 아니라 **계통적**이다. 계통오차는
  모형으로 고칠 수 없고, 측정으로 앵커링하거나 PTD 를 넣어야 한다. 여기서는 앵커링을 한다.

■ 규약 선언 (statistic convention) — ⚠ 비교 전에 통계부터 맞춘다
  이 모듈이 다루는 σ 통계는 **방위 선형평균**이다:

        μ_lin(f) ≜ 10·log10( (1/K) Σ_k σ(f, φ_k) )   [dBsm]

  우리 benchmark/rcs_anchor.py 의 `mean_dbsm` 이 정확히 이 양이다. 문헌 계수를 이 규약으로
  옮기는 변환은 `to_linear_mean_offset_db()` 가 담당하고, 그 변환이 맞는지는
  `reconcile_das_yuan()` 이 **두 논문을 서로 맞춰보며** 확인한다 (가정이 아니라 검산).

실행 (GPU 불필요 — 이미 계산된 outputs/*.json 만 읽는다):
  cd /workspace/sionna
  PYTHONPATH=src:benchmark SIONNA2_CPU=1 ~/.venvs/py312/bin/python src/sigma_anchor.py
"""
from __future__ import annotations

import json
import os

import numpy as np

# --------------------------------------------------------------------------- #
#  0. 문헌 앵커 계수 — ⚠ 전부 원문 PDF 에서 **직접** 읽었다. 브리핑에서 옮기지 않았다.
# --------------------------------------------------------------------------- #
#  Das 논문의 Table I~III 은 **텍스트 레이어가 없다**(fitz 로 추출하면 빈 문자열). 그래서
#  해당 페이지를 300~700 dpi 로 렌더해 표를 눈으로 읽었다. 아래 `verified` 필드가 그 사실을
#  기록한다. 읽지 못한 값은 아예 넣지 않는다 (UNVERIFIED 로 남기는 편이 낫다).
#
#  Yuan 논문은 텍스트 레이어가 살아 있어 §IV 본문에서 {a,b,c,d} 를 그대로 추출했다.

DAS = {
    "citation": ("S. Das, P. Zhang, V. Hovinen, M. E. Leinonen, A. Parssinen, P. Kyosti, "
                 "\"Multiband Monostatic and Bistatic RCS Characterization of AAVs for ISAC "
                 "Channel Modeling,\" IEEE Wireless Commun. Lett., vol. 15, pp. 3731-3735, 2026, "
                 "doi:10.1109/LWC.2026.3705634"),
    "verified": ("PDF metadata(subject='IEEE Wireless Communications Letters;2026;15') 로 게재확인. "
                 "Table I/III 은 텍스트 레이어 없음 → page 1/3 을 500~700 dpi 렌더해 판독."),
    "pdf": ("/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/"
            "Multiband_Monostatic_and_Bistatic_RCS_Characterization_of_AAVs_for_ISAC_Channel_Modeling.pdf"),
    # Table III: μ(f)=a·f+b [dBsm], ε(f)=c·f+d [dB], f in GHz, 열 = 바이스태틱각 θb.
    #   ⚠ Phantom 3 / Mini 2 / M350 RTK 는 θb 가 바뀌어도 **기울기가 같고 절편만** 움직인다
    #     (원문 표 그대로). Phantom 2 만 기울기가 θb 마다 다르다.
    "table3": {
        # AAV: {θb_deg: (a, b, c, d)}
        "phantom2": {0: (0.21, -12.10, 0.10, 1.81), 15: (0.50, -19.31, 0.07, 2.73),
                     30: (0.22, -13.30, 0.06, 3.06), 45: (0.21, -14.76, 0.07, 2.87),
                     60: (0.12, -14.18, 0.02, 3.85), 75: (-0.13, -7.85, 0.08, 2.80),
                     90: (0.08, -10.40, 0.05, 3.16)},
        "phantom3": {0: (0.21, -19.19, 0.03, 5.16), 15: (0.21, -19.23, 0.03, 5.16),
                     30: (0.21, -19.33, 0.03, 5.16), 45: (0.21, -19.48, 0.03, 5.16),
                     60: (0.21, -19.64, 0.03, 5.16), 75: (0.21, -19.77, 0.03, 5.16),
                     90: (0.21, -19.82, 0.03, 5.16)},
        "mini2": {0: (0.07, -25.85, 0.01, 5.47), 15: (0.07, -25.89, 0.01, 5.47),
                  30: (0.07, -25.99, 0.01, 5.47), 45: (0.07, -26.14, 0.01, 5.47),
                  60: (0.07, -26.30, 0.01, 5.47), 75: (0.07, -26.43, 0.01, 5.47),
                  90: (0.07, -26.47, 0.01, 5.47)},
        "m350rtk": {0: (0.17, -18.85, 0.01, 6.61), 15: (0.17, -18.89, 0.01, 6.61),
                    30: (0.17, -18.99, 0.01, 6.61), 45: (0.17, -19.15, 0.01, 6.61),
                    60: (0.17, -19.31, 0.01, 6.61), 75: (0.17, -19.43, 0.01, 6.61),
                    90: (0.17, -19.48, 0.01, 6.61)},
    },
    # Table I (측정 설정) — ⚠ **밴드 유효구간**이다. 이걸 벗어나 외삽하면 앵커가 아니다.
    "table1": {
        "mini2":    dict(dim_mm=(159, 203), band_ghz=(21.0, 27.0), n_freq=501,
                         az="0:0.5:360", dist="far-field", env="anechoic"),
        "m350rtk":  dict(dim_mm=(810, 670), band_ghz=(21.0, 27.0), n_freq=501,
                         az="0:0.5:360", dist="far-field", env="anechoic"),
        "phantom2": dict(dim_mm=(350, 200), band_ghz=(11.0, 26.0), n_freq=2001,
                         az="0:1:360", dist="near-field 2.6 m", env="controlled non-anechoic indoor"),
        "phantom3": dict(dim_mm=(350, 200), band_ghz=(1.8, 18.2), n_freq=2801,
                         az="-90:2:90", dist="far-field", env="anechoic"),
    },
    "polarisation": "VV (TX/RX 모두 수직편파 지향성 안테나, §II-1)",
    "calibration": "금속 원기둥 r=5.5 cm, h=30 cm, σ_Cal=+2.8 dBsm · 배경 코히런트 차감 · 6차 Kaiser 레인지게이팅",
    # ⚠ 원문 내부 모순 (§III-1 vs 3GPP remark) — 아래 STAT_AMBIGUITY 참조.
    "mean_defined_as": "sigma_m(theta_b, f_i) = (1/K) sum_k sigma(theta_b, f_i, phi_k)   [§III-1 본문]",
    "lognormal_remark": "ln(sigma) ~ N( (ln10/10)*mu, ((ln10/10)*eps)^2 )   [§III-2 3GPP remark]",
}

YUAN = {
    "citation": ("Z. Yuan, L. Yu, C. Li, W. Fan, \"On Experimental Analysis of Mono-Static 3D UAV "
                 "RCS for ISAC Channel Modeling,\" 2025 19th European Conf. on Antennas and "
                 "Propagation (EuCAP), doi:10.23919/EuCAP63536.2025.10999912"),
    "verified": ("PDF metadata(subject='2025 19th European Conference on Antennas and Propagation') "
                 "로 게재확인. §IV 본문에 {a,b,c,d} 가 텍스트로 있어 그대로 추출."),
    "pdf": ("/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/"
            "On_Experimental_Analysis_of_Mono-Static_3D_UAV_RCS_for_ISAC_Channel_Modeling.pdf"),
    # μ = a·f + b [dBsm], ε = c·f + d, f in GHz. θ = UAV 고도측면 {90=방위면, 0=위, 180=아래}.
    "abcd": {90: (0.315, -16.15, 0.0045, 0.07),
             0:  (0.231, -17.92, 0.0024, 0.06),
             180: (0.175, -17.12, 0.0019, 0.07)},
    "target": "DJI Phantom 3 — 수평대각 35 cm, 높이 20 cm (§II-A)",
    "band_ghz": (1.8, 18.2),
    "az": "-90:2:90 (기체 대칭 이용), 2801 주파수점",
    "polarisation": "VV (TX/RX 모두 수직편파 지향성 안테나, §II-A). "
                    "원문 스스로 '이상적으로는 전 편파상태를 재야 하나 시간제약으로 못 했다' 고 적었다.",
    "calibration": "금속구 r=17.8 cm, σ_Cal=-10 dBsm · CATR 원거리장 · 배경 차감 + 6차 Kaiser 게이팅",
}

# ─────────────────────────────────────────────────────────────────────────── #
#  ⭐ 두 논문의 관계 — 재조사 금지용 확정 사실
# ─────────────────────────────────────────────────────────────────────────── #
SOURCE_RELATION = """\
Das 의 Phantom 3 행은 **Yuan 의 원자료를 재분석한 것**이다. 독립 2건이 아니다.
  근거 1  Das Table I 의 Phantom 3 열 = 35x20 cm · 1.8~18.2 GHz · 2801 주파수점 ·
          방위 -90:2:90 — Yuan §II-A 의 설정과 **글자 단위로 같다**.
  근거 2  Das ACKNOWLEDGMENT: "thank Prof. Wei Fan from Southeast University for providing the
          measured RCS data for the DJI Mini 2, DJI Phantom 3, and DJI M350 RTK."
          Wei Fan 은 Yuan 논문의 교신저자다.
=> 우리 앵커는 **한 기체(DJI Phantom 3) · 한 측정체인(Southeast Univ. CATR)** 위에 서 있다.
   두 논문이 일치한다는 사실은 '독립 재현' 이 아니라 '같은 자료의 두 통계' 라는 뜻이다.
   그 대신 그 일치는 **통계 규약을 역산하는 데** 쓸 수 있다 (reconcile_das_yuan)."""

STAT_AMBIGUITY = """\
Das 원문은 μ 의 정의를 두 곳에서 **서로 다르게** 적는다.
  (A) §III-1  : sigma_m = (1/K) sum_k sigma(phi_k)          → 선형(전력) 방위평균
  (B) §III-2  : ln(sigma) ~ N((ln10/10)mu, ((ln10/10)eps)^2) → mu = E[10log10 sigma], dB 영역평균
  둘은 같은 양이 아니다. 변환량은 분포가정에 걸린다:
      지수(Swerling I/II) → +10/ln10*gamma = +2.507 dB (레벨·주파수 무관 상수)
      로그정규            → +(ln10/20)*eps^2, eps 의존 (Das eps 는 우리 대역에서 5.2~5.3 dB)
  → `reconcile_das_yuan()` 이 Yuan 과 맞춰본다. 두 논문이 **같은 원자료**이므로 잔차가 0 에
    가장 가까운 변환이 Das 의 실제 규약이다. 실행 결과는 statistic_resolution 필드가 들고 있고,
    채택 상수와 탈락 상수의 차이가 **해소되지 않은 규약 불확도**로 앵커에 딸려 다닌다."""

# ε 의 단위도 두 논문이 다르다 — 이것도 검산으로 확정했다 (`verify_eps_units`).
EPS_UNITS = """\
Das ε [dB]   : Table III 표제가 명시 — "STANDARD DEVIATION eps [DB]". Phantom 3 는 5.21~5.71 dB.
               지수분포(Swerling I/II) 이론값 (10/ln10)*pi/sqrt(6) = 5.570 dB 와 7% 안에서 일치한다.
Yuan ε [선형] : 원문은 단위를 안 적는다. Fig.5 우축 눈금이 0~0.25 (무차원) 이고 값도 0.07~0.15 다.
               검산: 레일리 진폭 가정에서 std(sqrt(sigma)) = sqrt(4/pi-1)*sqrt(pi/4*E[sigma]) 를
               Yuan μ 로부터 예측하면 1.8~18.2 GHz 전 구간에서 ε 의 0.89~0.99 배가 된다
               (dB 영역평균 가정은 1.19~1.23 배, 선형전력 표준편차 가정은 0.33~0.45 배로 어긋난다).
               => Yuan ε 는 **선형 진폭 sqrt(sigma) 의 표준편차** 다.
=> 두 ε 는 **다른 양이고 단위도 다르다**. 나란히 놓고 비교하면 안 된다."""

# --------------------------------------------------------------------------- #
#  1. 통계 규약 변환
# --------------------------------------------------------------------------- #
_EULER = 0.5772156649015329
LOG_TO_LIN_EXPONENTIAL_DB = 10.0 / np.log(10.0) * _EULER        # 2.5068 dB


def to_linear_mean_offset_db(kind: str = "exponential", eps_db: float | None = None) -> float:
    """dB 영역평균 E[10log10 σ] → 선형평균 10log10 E[σ] 로 옮길 때 **더할** 값 [dB].

    kind='exponential' : σ 가 지수분포(Swerling I/II, 레일리 진폭) → +10/ln10·γ = +2.5068 dB.
                         γ 는 오일러-마스케로니 상수. σ 레벨과 무관한 상수다.
    kind='lognormal'   : σ 가 로그정규(Das 가 3GPP remark 에서 가정) → +(ln10/20)·ε², ε 은 dB.
    kind='none'        : 0 (이미 선형평균 규약인 계수에 쓴다).

    ⚠ 어느 쪽이 맞는지는 논문이 말해주지 않는다. `reconcile_das_yuan()` 이 두 논문을 맞춰
      경험적으로 고른다. 여기서는 계산만 하고 고르지 않는다."""
    if kind == "exponential":
        return float(LOG_TO_LIN_EXPONENTIAL_DB)
    if kind == "lognormal":
        if eps_db is None:
            raise ValueError("kind='lognormal' 은 eps_db 가 필요하다 (변환량이 ε 에 의존한다)")
        return float(np.log(10.0) / 20.0 * float(eps_db) ** 2)
    if kind == "none":
        return 0.0
    raise ValueError(f"알 수 없는 kind={kind!r} — exponential/lognormal/none 중 하나여야 한다")


def yuan_pooled_linear_mean_db(f_ghz):
    """Yuan 의 세 고도측면(θ=90/0/180)을 **선형영역에서** 평균한 μ [dBsm].

    Das 의 Phantom 3 행은 같은 자료를 (고도측면 포함) 통째로 적합한 것이므로, Das 와
    사과-대-사과로 놓으려면 Yuan 도 세 측면을 합쳐야 한다. 합치는 영역은 **선형**이다
    (Yuan μ 가 선형평균이므로 — EPS_UNITS 검산 참조)."""
    f = np.asarray(f_ghz, float)
    lin = np.mean([10.0 ** ((a * f + b) / 10.0) for a, b, _, _ in YUAN["abcd"].values()], axis=0)
    return 10.0 * np.log10(lin)


def reconcile_das_yuan(f_ghz=None, kinds=("exponential", "lognormal")) -> dict:
    """Das μ 를 선형평균 규약으로 옮긴 값 vs Yuan 고도풀링 선형평균 — **잔차로 규약을 고른다**.

    두 논문이 같은 원자료를 쓰므로(SOURCE_RELATION) 잔차는 0 이어야 한다. 0 에 가장 가까운
    변환이 Das 의 실제 규약이다. 이것이 STAT_AMBIGUITY 를 해소하는 유일한 증거다."""
    f = np.linspace(*DAS["table1"]["phantom3"]["band_ghz"], 200) if f_ghz is None \
        else np.asarray(f_ghz, float)
    a, b, c, d = DAS["table3"]["phantom3"][0]
    das_db = a * f + b
    yuan_db = yuan_pooled_linear_mean_db(f)
    out = {}
    for kind in kinds:
        off = to_linear_mean_offset_db(kind, eps_db=float(np.mean(c * f + d)))
        res = yuan_db - (das_db + off)
        out[kind] = dict(offset_db=off, resid_min_db=float(res.min()), resid_max_db=float(res.max()),
                         resid_rms_db=float(np.sqrt(np.mean(res ** 2))),
                         resid_absmax_db=float(np.max(np.abs(res))))
    best = min(out, key=lambda k: out[k]["resid_absmax_db"])
    return dict(f_ghz=[float(f.min()), float(f.max())], by_kind=out, best_kind=best,
                spread_between_kinds_db=float(abs(out[kinds[0]]["offset_db"] - out[kinds[1]]["offset_db"]))
                if len(kinds) == 2 else None,
                note="잔차가 가장 작은 kind 가 Das 의 실제 μ 규약이다. 두 kind 의 차이는 미해소 불확도.")


def verify_eps_units(f_ghz=None) -> dict:
    """Yuan ε 의 단위를 **세 가설로 검산**한다 (EPS_UNITS 의 근거를 코드로 남긴다).

      H1 ε = std(sqrt(σ)) , μ = 10log10 E[σ]   (레일리 진폭)
      H2 ε = std(sqrt(σ)) , μ = E[10log10 σ]   (dB 영역평균)
      H3 ε = std(σ)       , μ = 10log10 E[σ]   (선형 전력 표준편차)
    각 가설이 예측한 ε 을 원문 ε 으로 나눈 비를 돌려준다. 1 에 가까울수록 맞는 가설."""
    f = np.linspace(*YUAN["band_ghz"], 100) if f_ghz is None else np.asarray(f_ghz, float)
    ray = np.sqrt(4.0 / np.pi - 1.0)              # 레일리 진폭 std/mean
    out = {}
    for th, (a, b, c, d) in YUAN["abcd"].items():
        mu_db, eps = a * f + b, c * f + d
        Es1 = 10.0 ** (mu_db / 10.0)
        Es2 = 10.0 ** ((mu_db + LOG_TO_LIN_EXPONENTIAL_DB) / 10.0)
        pred = {"H1_amp_linmean": ray * np.sqrt(np.pi / 4.0 * Es1),
                "H2_amp_dbmean":  ray * np.sqrt(np.pi / 4.0 * Es2),
                "H3_power_linmean": Es1}
        out[f"theta{th}"] = {k: dict(ratio_mean=float(np.mean(v / eps)),
                                     ratio_min=float(np.min(v / eps)),
                                     ratio_max=float(np.max(v / eps)))
                             for k, v in pred.items()}
    return dict(by_theta=out, verdict="ratio 가 1 에 가장 가까운 가설이 Yuan ε 의 단위다")


# --------------------------------------------------------------------------- #
#  2. 앵커 정의 — A(f)
# --------------------------------------------------------------------------- #
#  각 앵커는 (a, b) [dBsm, f in GHz] 와 **어느 통계 규약인지**, **어느 밴드에서 유효한지**,
#  **어느 편파인지**, **어느 기체·크기인지** 를 함께 들고 다닌다. 규약 없는 계수는 쓰지 않는다.
ANCHORS = {
    "das_phantom3_mono": dict(
        a=DAS["table3"]["phantom3"][0][0], b=DAS["table3"]["phantom3"][0][1],
        eps_c=DAS["table3"]["phantom3"][0][2], eps_d=DAS["table3"]["phantom3"][0][3],
        statistic="dB azimuth mean (E[10log10 sigma])",
        stat_evidence="reconcile_das_yuan() 잔차 최소 — STAT_AMBIGUITY 참조",
        to_linear_kind="exponential",
        platform="DJI Phantom 3", D_ref_m=0.350, D_ref_def="motor-to-motor diagonal (Table I 35 cm)",
        band_ghz=DAS["table1"]["phantom3"]["band_ghz"], geometry="monostatic far-field anechoic",
        polarisation="VV", source="DAS Table III, theta_b=0",
        elevation="Table I 방위 -90:2:90 · Yuan 자료 3 고도측면 통합 적합(추정)",
    ),
    "yuan_phantom3_azplane": dict(
        a=YUAN["abcd"][90][0], b=YUAN["abcd"][90][1],
        eps_c=YUAN["abcd"][90][2], eps_d=YUAN["abcd"][90][3],
        statistic="linear azimuth mean (10log10 E[sigma])",
        stat_evidence="verify_eps_units() H1 — EPS_UNITS 참조",
        to_linear_kind="none",
        platform="DJI Phantom 3", D_ref_m=0.350, D_ref_def="horizontal diagonal 35 cm (§II-A)",
        band_ghz=YUAN["band_ghz"], geometry="monostatic CATR far-field anechoic",
        polarisation="VV", source="YUAN §IV, theta=90 (azimuth plane)",
        elevation="방위면(우리 el=0 과 **고도 정합**)",
    ),
    "yuan_phantom3_top": dict(
        a=YUAN["abcd"][0][0], b=YUAN["abcd"][0][1],
        eps_c=YUAN["abcd"][0][2], eps_d=YUAN["abcd"][0][3],
        statistic="linear azimuth mean (10log10 E[sigma])",
        stat_evidence="verify_eps_units() H1", to_linear_kind="none",
        platform="DJI Phantom 3", D_ref_m=0.350, D_ref_def="horizontal diagonal 35 cm",
        band_ghz=YUAN["band_ghz"], geometry="monostatic CATR far-field anechoic",
        polarisation="VV", source="YUAN §IV, theta=0 (top)", elevation="위에서 봄",
    ),
    "yuan_phantom3_bottom": dict(
        a=YUAN["abcd"][180][0], b=YUAN["abcd"][180][1],
        eps_c=YUAN["abcd"][180][2], eps_d=YUAN["abcd"][180][3],
        statistic="linear azimuth mean (10log10 E[sigma])",
        stat_evidence="verify_eps_units() H1", to_linear_kind="none",
        platform="DJI Phantom 3", D_ref_m=0.350, D_ref_def="horizontal diagonal 35 cm",
        band_ghz=YUAN["band_ghz"], geometry="monostatic CATR far-field anechoic",
        polarisation="VV", source="YUAN §IV, theta=180 (bottom)", elevation="아래에서 봄",
    ),
}
DEFAULT_ANCHOR = "das_phantom3_mono"

#  ⚠ 기울기 인구조사 — **밴드 유효구간과 함께** 본다. 유효구간을 벗어난 기울기를 우리 대역
#     (1.8~5.21 GHz)으로 끌어오면 그건 앵커가 아니라 외삽이다. Mini 2 의 0.07 dB/GHz 가
#     21~27 GHz 값이라는 사실이 대표적이다.
SLOPE_CENSUS = {
    "das_phantom3_mono":  dict(slope=0.21,  band_ghz=(1.8, 18.2), overlaps_our_band=True),
    "das_phantom2_mono":  dict(slope=0.21,  band_ghz=(11.0, 26.0), overlaps_our_band=False),
    "das_mini2_mono":     dict(slope=0.07,  band_ghz=(21.0, 27.0), overlaps_our_band=False),
    "das_m350rtk_mono":   dict(slope=0.17,  band_ghz=(21.0, 27.0), overlaps_our_band=False),
    "yuan_phantom3_az":   dict(slope=0.315, band_ghz=(1.8, 18.2), overlaps_our_band=True),
    "yuan_phantom3_top":  dict(slope=0.231, band_ghz=(1.8, 18.2), overlaps_our_band=True),
    "yuan_phantom3_bot":  dict(slope=0.175, band_ghz=(1.8, 18.2), overlaps_our_band=True),
}


def anchor_mu_dbsm(f_ghz, anchor: str = DEFAULT_ANCHOR, to_linear_mean: bool = True,
                   allow_extrapolation: bool = False):
    """앵커 A(f) [dBsm] — **우리 규약(방위 선형평균)** 으로 환산해서 돌려준다.

    to_linear_mean=False 면 원문 규약 그대로(변환 없이). 기본은 True — 이 모듈 전체가
    선형평균 규약이므로, 규약을 섞지 않으려면 여기서 한 번만 맞춘다.
    ⚠ 밴드 유효구간 밖은 **예외로 죽는다**. 조용히 외삽하지 않는다."""
    if anchor not in ANCHORS:
        raise KeyError(f"모르는 앵커 {anchor!r} — {sorted(ANCHORS)} 중 하나여야 한다")
    A = ANCHORS[anchor]
    f = np.asarray(f_ghz, float)
    lo, hi = A["band_ghz"]
    if not allow_extrapolation:
        bad = (f < lo - 1e-9) | (f > hi + 1e-9)
        if np.any(bad):
            raise ValueError(
                f"앵커 {anchor!r} 의 측정 유효구간은 {lo}~{hi} GHz 인데 {np.asarray(f)[bad].tolist()} GHz "
                f"를 요청했다. 밖에서 쓰려면 allow_extrapolation=True 로 **명시**하고 리포트에 적을 것.")
    mu = A["a"] * f + A["b"]
    if to_linear_mean:
        eps_db = A["eps_c"] * f + A["eps_d"] if A["to_linear_kind"] == "lognormal" else None
        mu = mu + to_linear_mean_offset_db(A["to_linear_kind"],
                                           eps_db=float(np.mean(eps_db)) if eps_db is not None else None)
    return mu


def literature_mu_eps(bands=None) -> dict:
    """benchmark/rcs_anchor.py 의 LITERATURE['mu_eps'] 를 **여기서** 만든다.

    왜: 같은 문헌 계수를 두 파일에 손으로 적어두면 한쪽만 고쳐질 수 있다(실제로 그랬다 —
    옛 주석은 Das μ 를 'linear average' 라고 적었지만 STAT_AMBIGUITY 대로 dB 영역평균이다).
    밴드별 μ 값도 하드코딩하지 않고 계산한다."""
    bands = BAND_F_GHZ if bands is None else bands
    out = {}
    for name, A in ANCHORS.items():
        out[name] = dict(
            target=A["platform"], D_ref_m=A["D_ref_m"], geom=A["geometry"],
            polarisation=A["polarisation"], band_ghz=list(A["band_ghz"]), source=A["source"],
            mu_a=A["a"], mu_b=A["b"], eps_c=A["eps_c"], eps_d=A["eps_d"],
            statistic_as_published=A["statistic"],
            mu_at_bands_as_published={b: float(anchor_mu_dbsm(f, anchor=name, to_linear_mean=False))
                                      for b, f in bands.items()},
            mu_at_bands_linear_mean={b: float(anchor_mu_dbsm(f, anchor=name))
                                     for b, f in bands.items()},
            note=("mu_at_bands_linear_mean 이 우리 mean_dbsm(방위 선형평균)과 사과-대-사과다. "
                  "as_published 는 원문 규약 그대로 — 섞지 말 것."),
        )
    out["_convention"] = dict(stat_ambiguity=STAT_AMBIGUITY, eps_units=EPS_UNITS,
                              source_relation=SOURCE_RELATION,
                              resolution=reconcile_das_yuan(), slope_census=SLOPE_CENSUS)
    return out


# --------------------------------------------------------------------------- #
#  3. 크기 전이 — ⭐ 앵커의 가장 약한 고리
# --------------------------------------------------------------------------- #
SIZE_LAWS = {
    "L2": dict(exponent=2.0, why=("σ ∝ 투영면적. 산란체 개수가 면적에 비례하는 확산형 표적 가정. "
                                  "광학영역 기하단면(σ≈A)의 스케일링이기도 하다.")),
    "L4": dict(exponent=4.0, why=("σ ∝ A²/λ². 지배적 평판/정반사면이 기체와 함께 커진다는 가정. "
                                  "평판 정반사 σ=4πA²/λ² 의 스케일링.")),
}


def size_correction_db(drone_key: str, law: str = "L2", D_ref_m: float | None = None,
                       drone_D_m: float | None = None) -> float:
    """앵커 기체 → 우리 기체 크기 전이량 [dB].  Δ = 10·n·log10(D/D_ref), n=2 또는 4.

    D 정의는 **모터-모터 대각**이다 (앵커 문헌이 그 값을 쓴다 — Das Table I '35 cm',
    Yuan §II-A '수평대각 35 cm'). 프로펠러 포함 bbox 스팬(radar_scene.target_extent)이
    **아니다** — 규약을 섞으면 mini5pro 에서 2 dB 넘게 어긋난다."""
    if law not in SIZE_LAWS:
        raise KeyError(f"모르는 크기법칙 {law!r} — {sorted(SIZE_LAWS)}")
    if drone_D_m is None:
        from drones import DRONES
        if drone_key not in DRONES:
            raise KeyError(f"모르는 기체 {drone_key!r}")
        drone_D_m = DRONES[drone_key].diagonal_mm / 1000.0
    if D_ref_m is None:
        D_ref_m = ANCHORS[DEFAULT_ANCHOR]["D_ref_m"]
    return float(10.0 * SIZE_LAWS[law]["exponent"] * np.log10(float(drone_D_m) / float(D_ref_m)))


def comparability(drone_key: str, anchor: str = DEFAULT_ANCHOR) -> dict:
    """⭐ 이 기체가 앵커 기체와 **비교 가능한가** 를 기록으로 남긴다.

    앵커는 DJI Phantom 3 **한 대**다. 나머지 기체에는 측정 대응물이 없다. 그 사실을
    기종마다 명시하고, 크기보정 가정(L² vs L⁴)이 답을 얼마나 바꾸는지 **둘 다** 적는다.
    verdict 는 세 단계: 'direct'(같은 급·같은 대각) / 'scaled'(같은 위상·크기만 다름) /
    'not_comparable'(위상 자체가 다름 — 외삽이라고 부를 것)."""
    from drones import DRONES
    if drone_key not in DRONES:
        raise KeyError(f"모르는 기체 {drone_key!r} — {sorted(DRONES)}")
    s = DRONES[drone_key]
    A = ANCHORS[anchor]
    D, Dref = s.diagonal_mm / 1000.0, A["D_ref_m"]
    ratio = D / Dref
    d2 = size_correction_db(drone_key, "L2", Dref)
    d4 = size_correction_db(drone_key, "L4", Dref)
    # 위상(topology): 앵커는 쉘드 바디 4로터. 개방프레임/8로터/6로터는 위상이 다르다.
    shelled_quad = (s.num_rotors == 4)
    if abs(20 * np.log10(ratio)) < 0.5 and shelled_quad:
        verdict, why = "direct", "대각 35 cm · 4로터 — 앵커 기체(Phantom 3)와 같은 급"
    elif shelled_quad and 0.5 <= ratio <= 2.0:
        verdict, why = "scaled", f"같은 4로터 위상, 대각만 {ratio:.2f}배 — 크기법칙으로 전이"
    elif not shelled_quad and ratio <= 2.0:
        verdict, why = "scaled", (f"로터 {s.num_rotors}개로 위상이 다르다(앵커는 4). "
                                  f"대각 {ratio:.2f}배 — 전이하되 위상차는 보정 못 한다")
    else:
        verdict, why = "not_comparable", (
            f"대각 {ratio:.2f}배 · 로터 {s.num_rotors}개 — 앵커 기체와 위상도 크기도 다르다. "
            f"L²/L⁴ 가 {abs(d4 - d2):.1f} dB 갈리므로 크기보정 자체가 결론을 지배한다")
    return dict(drone=drone_key, name=s.name, anchor=anchor, anchor_platform=A["platform"],
                D_m=float(D), D_ref_m=float(Dref), D_def="motor-to-motor diagonal",
                size_ratio=float(ratio), size_corr_L2_db=d2, size_corr_L4_db=d4,
                size_law_spread_db=float(abs(d4 - d2)),
                num_rotors=int(s.num_rotors), anchor_num_rotors=4,
                verdict=verdict, why=why,
                measured_analogue=("DJI Phantom 3 (same class)" if verdict == "direct"
                                   else "none — 측정 대응물 없음"))


# --------------------------------------------------------------------------- #
#  4. 미통제 항 — 리포트가 반드시 싣는다
# --------------------------------------------------------------------------- #
def uncontrolled_terms(drone_keys=None) -> list:
    """미통제·미해소 항의 원장. ⚠ `size_db` 는 **계산값**이다 — 손으로 적은 숫자가 없다."""
    rc = reconcile_das_yuan()
    conv_spread = rc["spread_between_kinds_db"]
    # 고도정합: 1.843 GHz 에서 das 변환값과 yuan 방위면의 차
    f0 = 1.843
    el_gap = float(anchor_mu_dbsm(f0, "yuan_phantom3_azplane")
                   - anchor_mu_dbsm(f0, "das_phantom3_mono"))
    if drone_keys is None:
        from drones import DRONES
        drone_keys = sorted(DRONES)
    spreads = {d: comparability(d)["size_law_spread_db"] for d in drone_keys}
    hi = max(spreads, key=lambda k: spreads[k])
    lo = min(spreads, key=lambda k: spreads[k])
    return [
        dict(term="polarisation",
             status="UNRESOLVED",
             detail=("Das·Yuan 둘 다 **VV** 다. 우리 커널은 편파 상태가 아예 없다 — "
                     "materials.gamma_po() 가 재질당 스칼라 |Γ|(수직입사 프레넬) 하나를 돌려주고 "
                     "rcs_sbr 은 그것을 그대로 쓴다. 즉 우리 σ 는 무편파 스칼라다. "
                     "따라서 이 재보정은 VV 측정을 무편파 모형에 붙이는 것이고, 그 차이는 "
                     "보정되지 않은 채 레벨에 흡수된다."),
             size_db=None,
             size_note="unknown — 우리 쪽에 편파 자유도가 없어 자체 산정 불가"),
        dict(term="statistic convention (Das mu)",
             status="RESOLVED_EMPIRICALLY",
             detail=STAT_AMBIGUITY,
             size_db=float(conv_spread),
             size_note=f"채택({rc['best_kind']}) 과 탈락 변환상수의 차 [dB]"),
        dict(term="size transfer law",
             status="UNRESOLVED",
             detail=("L² 와 L⁴ 중 무엇인지 문헌이 말해주지 않는다. 우리 자체 커널의 7기종 회귀는 "
                     "σ ∝ L^1.3 근처(r≈0.65)로 **둘 다 아니고 산포도 크다** — 크기보다 위상이 "
                     "세다는 뜻. 그래서 단일값을 쓰지 않고 L²/L⁴ 를 괄호로 함께 싣는다."),
             size_db=float(spreads[hi]),
             size_note=f"기종별 |ΔL⁴−ΔL²| 최대 {hi} {spreads[hi]:.2f} dB · 최소 {lo} {spreads[lo]:.2f} dB"),
        dict(term="single platform / single lab",
             status="UNRESOLVED",
             detail=SOURCE_RELATION,
             size_db=None,
             size_note="unknown — 실험실 간 재현성 자료가 없다"),
        dict(term="elevation matching",
             status="PARTIAL",
             detail=("Das 의 Phantom 3 적합은 세 고도측면(방위면/위/아래)을 통합한 것으로 보이고, "
                     "우리가 앵커링하는 컷은 el=0(방위면) 하나다. Yuan 은 그 셋을 분리해 두었고 "
                     "방위면이 위/아래보다 높다. 고도정합 앵커가 필요하면 "
                     "'yuan_phantom3_azplane' 을 쓸 것."),
             size_db=el_gap,
             size_note=f"{f0} GHz 에서 yuan 방위면 − das 변환값 [dB]"),
        dict(term="near-field vs far-field, environment",
             status="OK",
             detail=("Phantom 3 자료는 무향실 CATR **원거리장** 이다(Das Table I·Yuan §II-A). "
                     "Das 의 Phantom 2 만 근접장 2.6 m 비무향이고, 우리는 그 행을 앵커로 쓰지 않는다."),
             size_db=0.0, size_note="해당 없음"),
    ]

DISCLAIMER = (
    "이것은 외부 측정 한 건에 대한 **재보정(re-levelling)** 이지 검증이 아니다. "
    "각도패턴 B1(φ,θ) 는 우리 SBR+PO 기하에서 왔고, 레벨과 주파수의존 A(f) 는 측정에서 왔다. "
    "보정 후의 σ 가 참값에 가깝다는 증거는 이 계산 어디에도 없다.")


# --------------------------------------------------------------------------- #
#  5. 재보정 본체
# --------------------------------------------------------------------------- #
def linear_mean_dbsm(sigma_lin) -> float:
    """선언한 규약: 방위 **선형평균**을 dBsm 으로.  μ = 10log10( mean(σ_lin) )."""
    s = np.asarray(sigma_lin, float)
    if s.size == 0:
        raise ValueError("빈 패턴에는 평균이 없다")
    if not np.all(np.isfinite(s)):
        raise ValueError("σ 에 비유한값이 있다 — 앞단에서 죽어야 할 값이 흘러왔다")
    if np.any(s < 0):
        raise ValueError("σ 가 음수다 — 선형 m² 를 넘겨야 한다 (dBsm 아님)")
    return float(10.0 * np.log10(np.mean(s)))


def convention_gap_db(sigma_lin) -> float:
    """우리 패턴에서 **직접 잰** 선형평균 − dB영역평균 [dB].

    문헌 규약 모호성(STAT_AMBIGUITY)이 우리 자료에서 얼마짜리인지 가정 없이 재는 자.
    지수분포라면 2.507 dB 여야 한다."""
    s = np.asarray(sigma_lin, float)
    s = s[s > 0]
    return float(10.0 * np.log10(np.mean(s)) - np.mean(10.0 * np.log10(s)))


def fit_slope_db_per_ghz(f_ghz, mu_dbsm):
    """μ(f) = a·f + b 최소자승. 반환 (a, b)."""
    f = np.asarray(f_ghz, float)
    y = np.asarray(mu_dbsm, float)
    if f.size < 2:
        raise ValueError("기울기를 내려면 밴드가 2개 이상이어야 한다")
    a, b = np.polyfit(f, y, 1)
    return float(a), float(b)


def relevel(sigma_by_band: dict, f_ghz_by_band: dict, drone_key: str,
            mode: str = "level_and_slope", anchor: str = DEFAULT_ANCHOR,
            size_law: str = "L2", allow_extrapolation: bool = False,
            mu_our_dbsm: dict | None = None) -> dict:
    """⭐ 밴드별 각도패턴을 **측정 A(f)** 에 맞춰 재보정한다. 밴드 안 모양은 그대로 둔다.

    입력
      sigma_by_band : {밴드이름: σ 선형배열 [m²]}  — 우리 SBR+PO 원시 패턴 (평활 금지)
      f_ghz_by_band : {밴드이름: 중심주파수 [GHz]}
      drone_key     : 우리 기체 키 (크기전이·비교가능성 기록용)
      mode
        'level_and_slope' : A(f) = 앵커 μ(f) + 크기보정. **레벨과 기울기 둘 다** 측정에서.
                            크기전이 가정(L²/L⁴)에 결과가 걸린다.
        'slope_only'      : 밴드평균 레벨은 **우리 것을 보존**하고 기울기만 측정으로 교체.
                            크기 가정이 필요 없다 → 측정 대응물이 없는 기체의 정직한 기본값.
      size_law : 'L2' | 'L4' (mode='level_and_slope' 일 때만 쓰인다)
      mu_our_dbsm : {밴드: μ [dBsm]} 로 **우리 레벨을 외부에서 지정**. 넘긴 σ 배열이 성긴
                    격자(방위 120점 시연용)이고 헤드라인 μ 는 수렴한 720점에서 왔을 때 쓴다.
                    ⚠ 이러면 σ_corrected 의 실제 평균은 mu_after 와 조금 어긋난다
                    (`mu_override_gap_db` 로 그 어긋남을 기록한다 — 숨기지 않는다).

    보정 규칙 (밴드 b, 보정량은 스칼라 한 개):
        Δ_b = A(f_b) − μ_our(f_b),        μ_our = 10log10(mean σ)   ← 선언한 선형평균 규약
        σ_corr(φ, f_b) = σ_our(φ, f_b) · 10^(Δ_b/10)
    스칼라 곱이므로 **밴드 안의 각도 모양·정규화 잔차분포 B2 는 비트단위로 불변**이다
    (정규화 분위점 P10/P1, 분포족 선택, 널 위치가 모두 그대로). 리포트가 그 불변을 확인한다.

    반환 dict: sigma_corrected / delta_db / mu_before_dbsm / mu_after_dbsm / slope_* /
               comparability / provenance / uncontrolled / disclaimer"""
    if mode not in ("level_and_slope", "slope_only"):
        raise ValueError(f"모르는 mode={mode!r} — 'level_and_slope' 또는 'slope_only'")
    bands = list(sigma_by_band)
    missing = [b for b in bands if b not in f_ghz_by_band]
    if missing:
        raise KeyError(f"주파수가 없는 밴드: {missing} — 밴드이름 규약이 어긋났다")
    f = np.array([float(f_ghz_by_band[b]) for b in bands])

    mu_pattern = np.array([linear_mean_dbsm(sigma_by_band[b]) for b in bands])
    if mu_our_dbsm is None:
        mu_our = mu_pattern
    else:
        miss = [b for b in bands if b not in mu_our_dbsm]
        if miss:
            raise KeyError(f"mu_our_dbsm 에 없는 밴드: {miss}")
        mu_our = np.array([float(mu_our_dbsm[b]) for b in bands])
    mu_anchor = np.asarray(anchor_mu_dbsm(f, anchor=anchor, to_linear_mean=True,
                                          allow_extrapolation=allow_extrapolation), float)

    if mode == "level_and_slope":
        dsize = size_correction_db(drone_key, size_law, ANCHORS[anchor]["D_ref_m"])
        target = mu_anchor + dsize
        pivot_note = f"크기보정 {size_law} = {dsize:+.2f} dB (D/D_ref 로 전이)"
    else:
        dsize = 0.0
        # 밴드 비가중 평균 레벨을 보존하고 기울기만 앵커로 — 크기 가정이 필요 없다.
        target = mu_anchor + (mu_our.mean() - mu_anchor.mean())
        pivot_note = (f"레벨 보존 축(pivot) = 밴드 비가중 평균 {mu_our.mean():+.2f} dBsm "
                      f"(= f̄ {f.mean():.3f} GHz 에서 회전). 크기 가정 없음")

    delta = target - mu_our
    corrected = {b: np.asarray(sigma_by_band[b], float) * 10.0 ** (delta[i] / 10.0)
                 for i, b in enumerate(bands)}
    mu_after = mu_our + delta                      # = target, 정의상
    mu_after_pattern = np.array([linear_mean_dbsm(corrected[b]) for b in bands])

    a_bef, b_bef = fit_slope_db_per_ghz(f, mu_our)
    a_aft, b_aft = fit_slope_db_per_ghz(f, mu_after)

    return dict(
        drone=drone_key, mode=mode, anchor=anchor, size_law=(size_law if mode == "level_and_slope" else None),
        bands=bands, f_ghz=f.tolist(),
        sigma_corrected=corrected,
        delta_db={b: float(delta[i]) for i, b in enumerate(bands)},
        mu_before_dbsm={b: float(mu_our[i]) for i, b in enumerate(bands)},
        mu_after_dbsm={b: float(mu_after[i]) for i, b in enumerate(bands)},
        mu_anchor_dbsm={b: float(mu_anchor[i]) for i, b in enumerate(bands)},
        mu_override_gap_db=({b: float(mu_after_pattern[i] - mu_after[i]) for i, b in enumerate(bands)}
                            if mu_our_dbsm is not None else None),
        size_correction_db=float(dsize), pivot_note=pivot_note,
        slope_before_db_per_ghz=a_bef, slope_after_db_per_ghz=a_aft,
        slope_anchor_db_per_ghz=float(ANCHORS[anchor]["a"]),
        convention_gap_db={b: convention_gap_db(sigma_by_band[b]) for b in bands},
        comparability=comparability(drone_key, anchor),
        provenance=dict(
            from_geometry="B1(phi,theta) 각도패턴 · 밴드 안 각도구조 · 널 위치 · 정규화 잔차분포 B2",
            from_measurement=("A(f) 레벨과 주파수기울기" if mode == "level_and_slope"
                              else "A(f) 주파수기울기만 (레벨은 우리 기하 유지)"),
            anchor_detail=dict(ANCHORS[anchor]),
            our_kernel="rcs_sbr (1-bounce SBR + PO, 무편파 스칼라 |Γ|), 원시 σ(az) 평활 없음",
        ),
        uncontrolled=uncontrolled_terms([drone_key]),
        disclaimer=DISCLAIMER,
    )


# --------------------------------------------------------------------------- #
#  6. 리포트 — 이미 계산된 outputs/*.json 만 읽는다 (GPU 불필요)
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR_JSON = os.path.join(HERE, "outputs", "rcs_anchor.json")
GRID_JSON = os.path.join(HERE, "outputs", "report13_sigma_grid.json")
OUT_JSON = os.path.join(HERE, "outputs", "sigma_anchor.json")

#  rcs_anchor.json 의 밴드이름 ↔ 중심주파수 [GHz]
BAND_F_GHZ = {"LTE 1.843 GHz": 1.843, "5G 3.5 GHz": 3.500, "WiFi 5.21 GHz": 5.210}
#  report13_sigma_grid.json 은 같은 주파수를 다른 이름으로 쓴다 — 이름으로 잇지 말고 fc 로 잇는다.
GRID_BAND_ALIAS = {"LTE 1.8 GHz": "LTE 1.843 GHz", "5G NR 3.5 GHz": "5G 3.5 GHz",
                   "WiFi 5.2 GHz": "WiFi 5.21 GHz"}


def _load(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} 가 없다 — 앞선 실험이 안 돌았다. 조용히 넘어가지 않는다.")
    with open(path) as fh:
        return json.load(fh)


def pattern_from_grid(grid, drone, el_deg=0.0):
    """report13_sigma_grid.json 에서 **실제 각도패턴 배열**을 꺼낸다 (선형 m²).

    rcs_anchor.json 은 통계만 들고 있어 '스칼라 곱이 모양을 안 바꾼다' 를 배열로 보일 수 없다.
    그래서 배열 시연은 이 격자를 쓴다 (el=0 행, 120 방위). 밴드이름은 fc 로 대조 확인한다."""
    out, fgh = {}, {}
    els = None
    for gname, entry in grid["sigma"]["grid"][drone].items():
        std = GRID_BAND_ALIAS.get(gname, gname)
        els = np.asarray(entry["el_deg"], float)
        idx = int(np.argmin(np.abs(els - el_deg)))
        if abs(els[idx] - el_deg) > 1e-6:
            raise ValueError(f"{drone}/{gname}: el={el_deg} 행이 격자에 없다 (있는 el: {els.tolist()})")
        sig_db = np.asarray(entry["sigma_dbsm"], float)[idx]
        fc = float(entry["fc_hz"]) / 1e9
        if abs(fc - BAND_F_GHZ[std]) > 1e-6:
            raise ValueError(f"밴드이름-주파수 불일치: {gname}→{std} 인데 fc={fc} GHz")
        out[std] = 10.0 ** (sig_db / 10.0)
        fgh[std] = fc
    return out, fgh


def build_report(out_path=OUT_JSON, el_key="el0", el_deg=0.0):
    """7기종 전부에 대해 재보정을 돌리고 원장을 JSON 으로 남긴다. **숫자는 전부 계산이다.**"""
    A = _load(ANCHOR_JSON)
    G = _load(GRID_JSON)
    drones = sorted(A["drones"])

    rep = {
        "meta": dict(
            producer="src/sigma_anchor.py",
            reads=[os.path.relpath(ANCHOR_JSON, HERE), os.path.relpath(GRID_JSON, HERE)],
            source_anchor_json_generated=A["meta"]["generated"],
            source_grid_json_generated=G["meta"]["generated"],
            convention="sigma statistic = linear azimuth mean, mu = 10log10(mean(sigma_lin)) [dBsm]",
            elevation_cut=f"{el_key} (el={el_deg} deg, 방위면)",
            disclaimer=DISCLAIMER,
        ),
        "sources": dict(das=DAS, yuan=YUAN, source_relation=SOURCE_RELATION,
                        stat_ambiguity=STAT_AMBIGUITY, eps_units=EPS_UNITS,
                        anchors=ANCHORS, default_anchor=DEFAULT_ANCHOR,
                        slope_census=SLOPE_CENSUS),
        "statistic_resolution": dict(reconcile=reconcile_das_yuan(),
                                     eps_units=verify_eps_units()),
        "uncontrolled": uncontrolled_terms(drones),
        "size_laws": SIZE_LAWS,
        "drones": {},
    }

    #  우리 커널 자체의 크기 지수 — L²/L⁴ 중 무엇도 아니라는 근거를 계산으로 남긴다.
    from drones import DRONES
    Dm = np.array([DRONES[d].diagonal_mm / 1000.0 for d in drones])
    own = {}
    for bname, fg in BAND_F_GHZ.items():
        y = np.array([A["drones"][d]["bands"][bname][el_key]["mean_dbsm"] for d in drones])
        n, _ = np.polyfit(10 * np.log10(Dm), y, 1)
        own[bname] = dict(exponent=float(n), pearson_r=float(np.corrcoef(10 * np.log10(Dm), y)[0, 1]))
    #  앵커 선택 민감도 — 어느 앵커를 골랐느냐가 A(f) 를 얼마나 흔드는가 (우리 3밴드에서).
    rep["anchor_sensitivity"] = {
        name: dict(slope_db_per_ghz=float(ANCHORS[name]["a"]),
                   statistic=ANCHORS[name]["statistic"],
                   mu_linear_mean_dbsm={b: float(anchor_mu_dbsm(fg, anchor=name))
                                        for b, fg in BAND_F_GHZ.items()},
                   source=ANCHORS[name]["source"], elevation=ANCHORS[name]["elevation"])
        for name in ANCHORS}
    rep["anchor_sensitivity"]["_spread_db"] = {
        b: float(max(rep["anchor_sensitivity"][n]["mu_linear_mean_dbsm"][b] for n in ANCHORS)
                 - min(rep["anchor_sensitivity"][n]["mu_linear_mean_dbsm"][b] for n in ANCHORS))
        for b in BAND_F_GHZ}

    rep["our_kernel_size_exponent"] = dict(
        by_band=own, D_def="motor-to-motor diagonal", n_drones=len(drones),
        note=("우리 기하가 스스로 내는 크기지수. L²(=2)도 L⁴(=4)도 아니고 산포가 크다 → "
              "크기전이는 앵커의 가장 약한 고리이며 단일값으로 못 쓴다."))

    for dk in drones:
        sig, fgh = pattern_from_grid(G, dk, el_deg=el_deg)
        # 헤드라인 통계는 720 방위로 수렴한 rcs_anchor.json 을 쓴다 (격자는 120 방위 시연용).
        mu720 = {b: A["drones"][dk]["bands"][b][el_key]["mean_dbsm"] for b in BAND_F_GHZ}
        entry = {"name": A["drones"][dk]["name"],
                 "mu_ours_720az_dbsm": mu720,
                 "mu_ours_grid120az_dbsm": {b: linear_mean_dbsm(sig[b]) for b in sig},
                 "grid_vs_720az_db": {b: linear_mean_dbsm(sig[b]) - mu720[b] for b in sig},
                 "regression_22pt": {k: A["drones"][dk]["regression"][el_key][k]
                                     for k in ("a", "b", "R2_mu")},
                 "modes": {}}
        f3 = np.array([BAND_F_GHZ[b] for b in BAND_F_GHZ])
        y3 = np.array([mu720[b] for b in BAND_F_GHZ])
        entry["slope_ours_3band_db_per_ghz"] = fit_slope_db_per_ghz(f3, y3)[0]
        #  ⭐ 기울기 오차가 우리 대역에서 실제로 얼마짜리인가 — 누적 dB (1.843→5.21 GHz).
        span = float(f3.max() - f3.min())
        entry["band_span_ghz"] = span
        entry["accumulated_db_over_band"] = dict(
            ours_3band=float(entry["slope_ours_3band_db_per_ghz"] * span),
            ours_22pt=float(entry["regression_22pt"]["a"] * span),
            measured_anchor=float(ANCHORS[DEFAULT_ANCHOR]["a"] * span),
            note="μ(f_max) − μ(f_min) 를 회귀선에서 읽은 값. 이 차이가 재보정이 없앤 양이다.")

        for mode, law in (("level_and_slope", "L2"), ("level_and_slope", "L4"), ("slope_only", None)):
            #  ⚠ 레벨은 **수렴한 720방위** μ(rcs_anchor.json)를 쓰고, 곱해지는 배열은 격자
            #     120방위다. 두 규약이 섞이지 않도록 mu_our_dbsm 로 명시 주입하고, 그 어긋남은
            #     r['mu_override_gap_db'] 가 기록한다.
            r = relevel({b: sig[b] for b in sig}, fgh, dk, mode=mode,
                        size_law=(law or "L2"), mu_our_dbsm=mu720)
            key = mode if law is None else f"{mode}_{law}"
            entry["modes"][key] = {k: r[k] for k in
                                   ("delta_db", "mu_before_dbsm", "mu_after_dbsm", "mu_anchor_dbsm",
                                    "mu_override_gap_db", "size_correction_db", "pivot_note",
                                    "slope_before_db_per_ghz", "slope_after_db_per_ghz",
                                    "slope_anchor_db_per_ghz")}
            #  ⭐ 모양 불변 검사 — 스칼라 곱이 정규화 패턴을 바꾸지 않는지 배열로 확인.
            if key == "level_and_slope_L2":
                b0 = r["bands"][0]
                s0, s1 = np.asarray(sig[b0], float), np.asarray(r["sigma_corrected"][b0], float)
                nrm0, nrm1 = s0 / s0.mean(), s1 / s1.mean()
                entry["shape_invariance_max_abs_db"] = float(
                    np.max(np.abs(10 * np.log10(nrm1 / nrm0))))
                entry["provenance"] = r["provenance"]
        entry["comparability"] = comparability(dk)
        entry["convention_gap_ours_db"] = {b: convention_gap_db(sig[b]) for b in sig}
        rep["drones"][dk] = entry

    with open(out_path, "w") as fh:
        json.dump(rep, fh, indent=2, ensure_ascii=False)
    return rep


# --------------------------------------------------------------------------- #
#  7. 우리 실측 캠페인 설계 — **교정된 σ(f)** 를 얻기 위한 요구조건 (설계만, 실행 아님)
# --------------------------------------------------------------------------- #
C0 = 299792458.0
PLAN_DRONES = ("matrice4e", "mini5pro")          # 구매 확정 2종
PLAN_SPHERES_M = (0.100, 0.150, 0.178, 0.200, 0.250, 0.300)
PLAN_BW_HZ = (400e6, 200e6, 100e6, 50e6)


def measurement_plan(drone_keys=PLAN_DRONES, bands=None, spheres_m=PLAN_SPHERES_M,
                     bw_hz=PLAN_BW_HZ) -> dict:
    """실측 캠페인이 **탐지성능이 아니라 교정된 σ(f)** 를 내려면 무엇을 재야 하는가 — 숫자편.

    ⚠ 이 함수는 설계값만 계산한다. 아무것도 측정하지 않고 아무 장비도 건드리지 않는다.
    산출: 원거리장 거리 2D²/λ, 방위 각도 나이퀴스트, 교정구 정확 Mie σ, 점표적 조건(대역폭),
          기대 σ 레벨(앵커 기준)과 교정표적 대비 여유, 지면반사 분리 조건."""
    from drones import DRONES
    from radar_scene import target_extent, farfield_distance
    from mie_pec_sphere import sphere_reference_set
    bands = BAND_F_GHZ if bands is None else bands

    out = {"note": ("설계값 계산만 — 측정 아님. D 정의 두 가지를 **모두** 싣는다: "
                    "bbox(프로펠러 포함) = 우리 관례(radar_scene.target_extent), "
                    "diagonal(모터-모터) = 앵커 문헌 관례(Das Table I / Yuan §II-A)."),
           "airframes": {}, "calibration_spheres": {}, "point_target_condition": {},
           "ground_bounce": {}}

    for dk in drone_keys:
        s = DRONES[dk]
        D_bbox = float(target_extent(dk))
        D_diag = float(s.diagonal_mm) / 1000.0
        rec = dict(name=s.name, D_bbox_m=D_bbox, D_diagonal_m=D_diag,
                   prop_dia_mm=float(s.prop_dia_mm), num_rotors=int(s.num_rotors),
                   comparability=comparability(dk), by_band={})
        for b, fg in bands.items():
            f = fg * 1e9
            lam = C0 / f
            # 방위 각도 나이퀴스트: 회전축에서 D/2 떨어진 산란점의 왕복 경로변화 D·Δφ 를
            #   λ/2 미만으로 (나이퀴스트) 또는 λ/4 미만으로 (여유) 유지.
            rec["by_band"][b] = dict(
                lambda_mm=lam * 1000.0,
                D_over_lambda_bbox=D_bbox / lam, D_over_lambda_diag=D_diag / lam,
                farfield_m_bbox=float(farfield_distance(D_bbox, f)),
                farfield_m_diag=float(farfield_distance(D_diag, f)),
                az_step_nyquist_deg=float(np.degrees(lam / (2.0 * D_bbox))),
                az_step_recommended_deg=float(np.degrees(lam / (4.0 * D_bbox))),
            )
        out["airframes"][dk] = rec

    for r in spheres_m:
        row = {}
        for b, fg in bands.items():
            ref = sphere_reference_set(float(r), fg * 1e9)
            row[b] = dict(ka=ref["kr"], mie_dbsm=ref["mie_dbsm"], go_dbsm=ref["go_dbsm"],
                          mie_minus_go_db=ref["mie_minus_go_db"])
        out["calibration_spheres"][f"r={r:.3f}m"] = row
    out["calibration_spheres"]["_rule"] = (
        "교정표적 σ 는 πr²(광학 점근) 이 아니라 **정확 Mie** 로 쓴다 — 우리 대역에서 πr² 는 "
        "구 반경에 따라 0.0~0.9 dB 틀린다(mie_minus_go_db 참조). benchmark/mie_pec_sphere.py 가 "
        "자체검증(selfcheck)을 가진 단일 출처다.")

    for dk in drone_keys:
        D = out["airframes"][dk]["D_bbox_m"]
        out["point_target_condition"][dk] = {
            f"B={int(b/1e6)}MHz": dict(range_res_m=float(C0 / (2.0 * b)),
                                       point_like=bool(C0 / (2.0 * b) > D),
                                       margin_m=float(C0 / (2.0 * b) - D))
            for b in bw_hz}
    out["point_target_condition"]["_rule"] = (
        "Das §II-3c 가 쓴 조건: 서브밴드 거리분해능이 표적 최대치수보다 커야 표적이 "
        "**점표적**이 되고 그때만 peak |s|² 를 σ 로 쓸 수 있다. 넓은 대역을 통째로 쓰면 "
        "표적이 여러 거리빈으로 퍼져 peak 법이 σ 를 과소평가한다 → 서브밴드로 쪼갤 것.")

    # 지면반사 유령의 거리분리: 안테나 높이 h, 표적 높이 H, 지상거리 R 에서
    #   경로차 ≈ 2hH/R. 이것이 거리분해능보다 커야 게이팅으로 뗀다.
    for h in (1.5, 2.0, 3.0):
        for H in (5.0, 10.0, 20.0):
            for R in (20.0, 30.0, 50.0):
                out["ground_bounce"][f"h={h}m,H={H}m,R={R}m"] = float(2.0 * h * H / R)
    out["ground_bounce"]["_rule"] = (
        "야외 실측은 무향실이 아니다 — 지면반사 유령이 표적 리턴과 겹치면 σ 가 오염된다. "
        "경로차 2hH/R 이 서브밴드 거리분해능보다 커야 레인지게이팅으로 분리된다.")

    # 기대 σ 레벨 (앵커 기준) 과 교정구 대비 여유 — 동적범위 요구의 근거.
    lvl = {}
    for dk in drone_keys:
        lvl[dk] = {}
        for law in ("L2", "L4"):
            dsz = size_correction_db(dk, law)
            lvl[dk][law] = {b: float(anchor_mu_dbsm(fg) + dsz) for b, fg in bands.items()}
    out["expected_sigma_dbsm_from_anchor"] = dict(
        by_drone=lvl, anchor=DEFAULT_ANCHOR,
        note="앵커+크기보정으로 **예상**한 레벨. 측정 전 동적범위 설계용이지 예측 주장 아님.")
    return out


MEASUREMENT_PLAN_MD = os.path.join(HERE, "docs", "MEASUREMENT_PLAN.md")
PLAN_JSON = os.path.join(HERE, "outputs", "measurement_plan.json")
_AUTO_BEGIN = "<!-- AUTO:BEGIN 이 블록은 src/sigma_anchor.py 가 생성한다. 손으로 고치지 말 것 -->"
_AUTO_END = "<!-- AUTO:END -->"


def _md_tables(plan) -> str:
    L = [_AUTO_BEGIN, ""]
    L.append("### A. 원거리장·각도표본 요구 (계산값)\n")
    L.append("`D_bbox` = 프로펠러 포함 bbox 최대 수평치수 (우리 관례) · "
             "`D_diag` = 모터-모터 대각 (앵커 문헌 관례).\n")
    for dk, rec in plan["airframes"].items():
        L.append(f"**{dk}** ({rec['name']}) — D_bbox = {rec['D_bbox_m']*1000:.1f} mm, "
                 f"D_diag = {rec['D_diagonal_m']*1000:.1f} mm, "
                 f"프로펠러 {rec['prop_dia_mm']:.0f} mm × {rec['num_rotors']}\n")
        L.append("| band | λ [mm] | D_bbox/λ | 2D²/λ (bbox) [m] | 2D²/λ (diag) [m] | "
                 "Δφ Nyquist [deg] | Δφ 권장 [deg] |")
        L.append("|---|---|---|---|---|---|---|")
        for b, v in rec["by_band"].items():
            L.append(f"| {b} | {v['lambda_mm']:.1f} | {v['D_over_lambda_bbox']:.2f} | "
                     f"**{v['farfield_m_bbox']:.2f}** | {v['farfield_m_diag']:.2f} | "
                     f"{v['az_step_nyquist_deg']:.2f} | {v['az_step_recommended_deg']:.2f} |")
        L.append("")
    L.append("### B. 교정표적 — PEC 구의 정확 Mie σ (계산값)\n")
    L.append("| 반경 [m] | " + " | ".join(f"{b} ka / σ_Mie [dBsm] / (Mie−πr²) [dB]"
                                          for b in BAND_F_GHZ) + " |")
    L.append("|---|" + "---|" * len(BAND_F_GHZ))
    for k, row in plan["calibration_spheres"].items():
        if k.startswith("_"):
            continue
        cells = [f"{row[b]['ka']:.2f} / {row[b]['mie_dbsm']:+.2f} / {row[b]['mie_minus_go_db']:+.2f}"
                 for b in BAND_F_GHZ]
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("### C. 점표적 조건 — 서브밴드 거리분해능 vs 표적 크기 (계산값)\n")
    L.append("| drone | " + " | ".join(f"B={int(b/1e6)} MHz" for b in PLAN_BW_HZ) + " |")
    L.append("|---|" + "---|" * len(PLAN_BW_HZ))
    for dk in plan["airframes"]:
        cells = []
        for b in PLAN_BW_HZ:
            v = plan["point_target_condition"][dk][f"B={int(b/1e6)}MHz"]
            cells.append(f"ΔR={v['range_res_m']:.3f} m · {'점표적 OK' if v['point_like'] else '⚠ 퍼짐'} "
                         f"(여유 {v['margin_m']:+.3f} m)")
        L.append(f"| {dk} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("### D. 지면반사 유령의 경로차 2hH/R [m] (계산값)\n")
    L.append("| 기하 | 경로차 [m] |")
    L.append("|---|---|")
    for k, v in plan["ground_bounce"].items():
        if k.startswith("_"):
            continue
        L.append(f"| {k} | {v:.2f} |")
    L.append("")
    L.append("### E. 앵커가 **예상**하는 σ 레벨 [dBsm] — 동적범위 설계용 (예측 주장 아님)\n")
    L.append("| drone | 크기법칙 | " + " | ".join(BAND_F_GHZ) + " |")
    L.append("|---|---|" + "---|" * len(BAND_F_GHZ))
    for dk, laws in plan["expected_sigma_dbsm_from_anchor"]["by_drone"].items():
        for law, row in laws.items():
            L.append(f"| {dk} | {law} | " + " | ".join(f"{row[b]:+.2f}" for b in BAND_F_GHZ) + " |")
    L.append("")
    L.append(_AUTO_END)
    return "\n".join(L)


def write_measurement_plan(md_path=MEASUREMENT_PLAN_MD, json_path=PLAN_JSON):
    """계산표를 docs/MEASUREMENT_PLAN.md 의 AUTO 블록에 주입하고 JSON 도 남긴다.

    ⚠ 문서의 **숫자는 손으로 적지 않는다**. AUTO 블록 밖의 산문만 사람이 쓴다."""
    plan = measurement_plan()
    with open(json_path, "w") as fh:
        json.dump(plan, fh, indent=2, ensure_ascii=False)
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"{md_path} 가 없다 — 산문 뼈대를 먼저 만들 것")
    with open(md_path) as fh:
        txt = fh.read()
    if _AUTO_BEGIN not in txt or _AUTO_END not in txt:
        raise ValueError(f"{md_path} 에 AUTO 마커가 없다 — 주입 위치를 못 찾았다")
    head, rest = txt.split(_AUTO_BEGIN, 1)
    _, tail = rest.split(_AUTO_END, 1)
    with open(md_path, "w") as fh:
        fh.write(head + _md_tables(plan) + tail)
    return plan


def _print(rep):
    print("=" * 100)
    print("측정 앵커 σ(f) 재보정 — sigma = A(f)·B1(phi)·B2   [재보정이지 검증이 아니다]")
    print("=" * 100)
    rc = rep["statistic_resolution"]["reconcile"]
    print(f"\n[통계 규약 해소] Das μ 를 선형평균으로 옮기는 상수 후보")
    for k, v in rc["by_kind"].items():
        print(f"   {k:12s} offset={v['offset_db']:+.3f} dB  |resid|max={v['resid_absmax_db']:.3f} dB "
              f"rms={v['resid_rms_db']:.3f}")
    print(f"   → 채택: {rc['best_kind']}  (두 후보 차이 {rc['spread_between_kinds_db']:.2f} dB 는 미해소 불확도)")

    ex = rep["statistic_resolution"]["eps_units"]["by_theta"]["theta90"]
    print(f"\n[Yuan ε 단위 검산] 예측/원문 비 (1 에 가까울수록 맞음, θ=90)")
    for h, v in ex.items():
        print(f"   {h:18s} mean={v['ratio_mean']:.3f}  ({v['ratio_min']:.3f}~{v['ratio_max']:.3f})")

    print(f"\n[우리 커널의 크기지수]")
    for b, v in rep["our_kernel_size_exponent"]["by_band"].items():
        print(f"   {b:16s} sigma ∝ L^{v['exponent']:.2f}  r={v['pearson_r']:+.3f}")

    A = ANCHORS[DEFAULT_ANCHOR]
    print(f"\n[앵커] {DEFAULT_ANCHOR}: μ={A['a']}f{A['b']:+.2f} dBsm ({A['statistic']}), "
          f"{A['band_ghz'][0]}~{A['band_ghz'][1]} GHz, {A['polarisation']}, {A['platform']}")

    print(f"\n[앵커 선택 민감도] 같은 기체(Phantom 3)를 어느 통계로 읽느냐에 따른 A(f) [dBsm]")
    for n, v in rep["anchor_sensitivity"].items():
        if n.startswith("_"):
            continue
        m = v["mu_linear_mean_dbsm"]
        print(f"   {n:24s} slope={v['slope_db_per_ghz']:5.3f}  "
              f"{m['LTE 1.843 GHz']:7.2f} {m['5G 3.5 GHz']:7.2f} {m['WiFi 5.21 GHz']:7.2f}  ({v['elevation']})")
    sp = rep["anchor_sensitivity"]["_spread_db"]
    print(f"   {'앵커간 산포':24s}          "
          f"{sp['LTE 1.843 GHz']:7.2f} {sp['5G 3.5 GHz']:7.2f} {sp['WiFi 5.21 GHz']:7.2f}")

    any_d = next(iter(rep["drones"].values()))
    print(f"\n[기울기 오차의 값어치] 1.843→5.21 GHz ({any_d['band_span_ghz']:.3f} GHz) 누적 [dB]")
    print(f"{'drone':12s} {'slope3':>7s} {'slope22':>8s} {'R2':>5s} | "
          f"{'acc_3band':>9s} {'acc_22pt':>8s} {'acc_meas':>8s}")
    for dk, e in rep["drones"].items():
        acc = e["accumulated_db_over_band"]
        print(f"{dk:12s} {e['slope_ours_3band_db_per_ghz']:7.3f} {e['regression_22pt']['a']:8.3f} "
              f"{e['regression_22pt']['R2_mu']:5.2f} | {acc['ours_3band']:+9.2f} "
              f"{acc['ours_22pt']:+8.2f} {acc['measured_anchor']:+8.2f}")

    for mode in ("level_and_slope_L2", "level_and_slope_L4", "slope_only"):
        print(f"\n{'─'*100}\n[mode = {mode}]  Δ = 적용된 보정 [dB]")
        print(f"{'drone':12s} {'cmp':14s} {'ΔLTE':>7s} {'Δ5G':>7s} {'ΔWiFi':>7s} | "
              f"{'slope_before':>12s} {'slope_after':>11s} {'anchor':>7s}")
        for dk, e in rep["drones"].items():
            m = e["modes"][mode]
            d = m["delta_db"]
            print(f"{dk:12s} {e['comparability']['verdict']:14s} "
                  f"{d['LTE 1.843 GHz']:+7.2f} {d['5G 3.5 GHz']:+7.2f} {d['WiFi 5.21 GHz']:+7.2f} | "
                  f"{m['slope_before_db_per_ghz']:12.3f} {m['slope_after_db_per_ghz']:11.3f} "
                  f"{m['slope_anchor_db_per_ghz']:7.3f}")

    print(f"\n[모양 불변 검사] 스칼라 재보정이 정규화 각도패턴을 바꾸는 최대량 [dB]")
    for dk, e in rep["drones"].items():
        print(f"   {dk:12s} {e['shape_invariance_max_abs_db']:.3e}")

    print(f"\n[비교가능성 원장]")
    for dk, e in rep["drones"].items():
        c = e["comparability"]
        print(f"   {dk:12s} D={c['D_m']*1000:6.1f}mm ratio={c['size_ratio']:.2f} "
              f"L2={c['size_corr_L2_db']:+6.2f} L4={c['size_corr_L4_db']:+6.2f} "
              f"(spread {c['size_law_spread_db']:5.2f})  {c['verdict']:14s} {c['why']}")

    print(f"\n[미통제 항]")
    for u in rep["uncontrolled"]:
        sz = "unknown" if u["size_db"] is None else f"{u['size_db']:+.2f} dB"
        print(f"   · {u['term']:32s} [{u['status']:21s}] 크기={sz:>10s}  {u['size_note']}")
    print(f"\n{DISCLAIMER}\n")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--el", default="el0", choices=("el0", "el15"))
    a = ap.parse_args()
    r = build_report(out_path=a.out, el_key=a.el, el_deg=0.0 if a.el == "el0" else 15.0)
    _print(r)
    print(f"[saved] {a.out}")
