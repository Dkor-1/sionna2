# -*- coding: utf-8 -*-
"""make_notebook08.py — report08.ipynb 생성기

report08: **드론 RCS·마이크로도플러 결과 (밴드별·자세별)**
질문: **"드론 5종은 실제로 얼마나 밝고, 프로펠러는 어떤 지문을 남기나?"**

⚠ 노트북은 **생성물**이다. report08.ipynb 를 직접 고치지 말고 이 파일을 고쳐 다시 실행할 것.
⚠ 본문 수치는 전부 **측정 JSON 에서 읽어 주입**한다 — 그림과 글이 어긋날 수 없다.
   · outputs/report2_waveform_rcs.json 의 rcs / materials  (5종 RCS, 재질 분해)
   · outputs/report1.json 의 articulation / microdoppler   (호버 rpm·flash·f_tip, 블레이드 지문)

이 리포트가 다루는 **한 주제**: SBR 로 잰 드론 5종의 밝기(RCS)와, 프로펠러가 만드는
마이크로도플러 지문. SBR '방법 자체'(왜 옳은가·가림)는 report07 소관 → 여기선 결과만.
"""
from __future__ import annotations

import json
import math
import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# ⚠ 이 파일은 **스크립트**다 (main() 없이 최상위에서 전부 실행된다).
#   임포트하면 그 자리에서 리포트 노트북을 **덮어쓴다**. 2026-07-29 실제로 검증 에이전트가
#   "임포트 되는지" 점검하다가 report07/08/13 을 덮어썼고 복구해야 했다. linter·문서도구·
#   테스트수집기도 같은 사고를 낸다 — 게다가 계산이 도는 중이면 **중간 숫자**가 박힌다.
#   → 실행은 `python src/make_notebook08.py` 로만.
if __name__ != "__main__":
    raise RuntimeError(
        "make_notebook08.py 는 스크립트다 — 임포트하면 리포트를 덮어쓴다. "
        "`python src/make_notebook08.py` 로 실행할 것. (2026-07-29 실사고)")
# ─────────────────────────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from provenance import provenance_cells   # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
NB = os.path.join(ROOT, "report08.ipynb")
JS2 = os.path.join(ROOT, "outputs", "report2_waveform_rcs.json")   # RCS + 재질
JS1 = os.path.join(ROOT, "outputs", "report1.json")                # 호버 rpm + 마이크로도플러


def _m(x, fmt="+.2f"):
    """음수를 표에서 문헌값(−, U+2212)과 같은 글리프로 찍는다."""
    return format(x, fmt).replace("-", "−")


def _need(d, key, where):
    """⚠ 기준해 정정(2026-07-30) 이전 판 JSON 을 **조용히 싣지 않는다**.

    구 검증의 과녁이 πr²(광학 점근) → 정확 Mie + 해석 PO 로 바뀌었다. 옛 JSON 에는 새 키가
    없으므로, 없으면 여기서 멈추고 재생성을 요구한다(옛 숫자를 새 라벨로 싣는 것이 최악)."""
    if key not in d:
        raise RuntimeError(
            f"{where}: '{key}' 가 없다 — 기준해 정정(πr² → Mie/해석 PO) 이전 판 JSON 이다. "
            f"해당 산출물을 다시 생성한 뒤 이 노트북을 빌드할 것.")
    return d[key]


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def code(*l):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _s(list(l))}


# --------------------------------------------------------------------------- #
#  측정값 로드 — 손으로 안 적는다
# --------------------------------------------------------------------------- #
with open(JS2) as f:
    J2 = json.load(f)
with open(JS1) as f:
    J1 = json.load(f)

DR = J2["rcs"]["drones"]                 # 드론별 3밴드 RCS
MAT = J2["materials"]                     # 재질 분해 (mavic4pro)
EL = J2["rcs"]["el"]
SBR_DIV = J2["meta"]["sbr_div"]
BANDS = [b[0] for b in J2["meta"]["bands"]]     # ["LTE 1.8 GHz", "5G NR 3.5 GHz", "WiFi 5.2 GHz"]

MD = J1["microdoppler"]["drones"]        # 블레이드 지문 (호버 rpm 유도값)
ART = J1["articulation"]["hover"]        # 호버 rpm 유도 (T = C_T ρ n² D⁴)
MDCFG = J1["microdoppler"]["cfg"]

# 표시 순서 (작은 → 큰 기체)
ORDER = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"]

# 밴드평균 밝기 헤드라인 — 가장 밝은/어두운 (드론별 '밴드 평균'끼리 비교; 밴드 혼합 금지)
def _band_avg(d):
    return sum(DR[d]["bands"][b]["mean_dbsm"] for b in BANDS) / len(BANDS)


_best = max(ORDER, key=_band_avg)
_dim = min(ORDER, key=_band_avg)
_best_v = _band_avg(_best)
_dim_v = _band_avg(_dim)
_span = _best_v - _dim_v

# 밴드가 한 기체를 얼마나 흔드나 (드론별 밴드 최대-최소, 평균)
_band_swing = sum(
    max(DR[d]["bands"][b]["mean_dbsm"] for b in BANDS)
    - min(DR[d]["bands"][b]["mean_dbsm"] for b in BANDS) for d in ORDER
) / len(ORDER)

# mavic4pro 의 **가장 밝은 자세**(aspect-peak).
# ⚠ 밴드를 맞춰야 한다 — 비교 대상 Li & Ling 2017 은 **3–6 GHz** 측정이다. 전 밴드 최대를 쓰면
#   WiFi 5.2 GHz 의 정반사 플래시(−4.0 dBsm)가 잡혀 밴드가 어긋난 채로 "문헌 범위 안"이라 말하게 된다.
_BAND_35 = "5G NR 3.5 GHz"
_PEAK = DR["mavic4pro"]["bands"][_BAND_35]["peak_dbsm"]
# 방위평균 헤드라인 값 — report12 가 인용하는 값과 **같은 출처**여야 한다
_AZAVG_35 = DR["mavic4pro"]["bands"]["5G NR 3.5 GHz"]["mean_dbsm"]


# 재질 분해 행 뽑기 (라벨로)
def _matrow(key):
    for r in MAT["rows"]:
        if key in r["label"]:
            return r
    return None
_full = _matrow("Full drone")
_noshell = _matrow("- shell")
_metal = _matrow("metal core")
_diel = _matrow("dielectric only")
_noprop = _matrow("propellers only")

# 마이크로도플러 PO→SBR pedestal 이득 범위
_gains = [MD[d]["gain_db"] for d in ORDER]
_gmin, _gmax = min(_gains), max(_gains)

# DC(정지 몸통)↔AC(블레이드 변조) 비 — JSON 시간영역 |DC|/std(AC) [dB]
_SBR_RATIO = [MD[d]["sbr"]["ratio_db"] for d in ORDER]
_PO_RATIO = [MD[d]["po"]["ratio_db"] for d in ORDER]
# md-props(Costa·Thomä, TU Ilmenau, RadarConf24) — **유일한 바이스태틱 마이크로도플러 실측**.
#   Fig.3 축 판독: DC 피크 ≈83 dB, 블레이드 선 ≈32–36 dB → **DC↔블레이드선 ≈47 dB**(스펙트럼 선 피크).
#   조건: 4개 중 1개 로터만 회전·자작 탄소골격(밀폐 DJI 아님)·β=60°·3.7 GHz·편파 미기재·무보정 상대 dB.
#   출처: 노트 §3-3(PDF 확인). ⚠ 우리 JSON ratio_db 는 **시간영역 |DC|/std(AC)** 라 정의가 다르다 —
#     선 피크 대 선 피크 스펙트럼 재계산은 다음 단계. 여기선 **방향성만** 쓴다.
PRIOR_MDPROPS_DCBLADE_DB = 47.0

# --------------------------------------------------------------------------- #
#  선행 **문헌값** (상수 — 우리 JSON 에 없으므로 여기 둔다. 출처를 반드시 병기)
# --------------------------------------------------------------------------- #
# Li & Ling 2017 (IEEE AWPL) — VNA 턴테이블 + 구 교정 S11, **3–6 GHz**, aspect-peak.
#   출처: refs/drone_papers/Li_Ling_2017_Radar_Signatures_Small_Consumer_Drones_IEEE_AWPL.md
#   등급 [N] — 워크스페이스 노트만 존재(PDF 부재)이므로 인용 시 "노트 근거" 를 밝힌다.
#   값: (기체 대각 [mm], aspect-peak [dBsm])
PRIOR_LILING = {"DJI Phantom 2": (350.0, -27.5),
                "3DR Solo":      (460.0, -24.2),
                "DJI Inspire 1": (560.0, -13.7)}
# Semkin 2020 (IEEE Access 8:48958-48969) 26–40 GHz 무향실 quasi-monostatic, mean HH, 로터 정지.
#   출처: refs/drone_papers/Semkin_2020_Drone_RCS_mmWave_IEEE_Access.md  (등급 [N])
#   재질 이득 수치는 인용하지 않는다 — 아래 면적 스케일링으로 크기 효과를 먼저 뺀다.
PRIOR_SEMKIN_MM = {"m100_carbon": 650.0, "mavicpro_plastic": 335.0}
# Güvenç/NCSU 서베이 arXiv:2402.05909 — DJI Mavic Pro @2.4 GHz ≈ 0.03 m².
#   출처: prior_work/outputs/prior_work.json → measured_rcs_anchor.rows[0] (등급 [W], 웹 메타데이터)
#   같은 블록의 `verdict` 문자열은 2026-07-24 rcs_anchor.json 기준으로 갱신됨(el0 평균 −16.6·중앙값 −19.7·봉우리 −8.4).
#      다만 이 리포트의 절대 σ 판정 원장은 아래 f-string 이 읽는 outputs/rcs_anchor.json 이므로,
#      리포트는 rows[0] 의 **문헌 수치만** 쓰고 verdict 문장은 인용하지 않는다(원장 이원화 방지).
#   ⚠ 지표 정의(peak/mean)가 원문에서 확인되지 않아 부등호 판정에는 쓰지 않는다.
PRIOR_GUVENC_MAVICPRO_24G_DBSM = -15.2
_SEMKIN_SIZE_DB = 20.0 * math.log10(PRIOR_SEMKIN_MM["m100_carbon"]
                                    / PRIOR_SEMKIN_MM["mavicpro_plastic"])

# --------------------------------------------------------------------------- #
#  ⭐사과-대-사과 절대앵커 — DJI Phantom 3 (350×200 mm), **우리 세 밴드를 전부 커버**
#     둘 다 원문 PDF 확인(paper_sionna_Ray/): multiband·mono3d 는 **같은 측정 캠페인**
#     (Wei Fan/Southeast Univ. 데이터)을 서로 다른 평균 규약으로 요약한 것이다.
#     ⚠ 우리 `mean_dbsm` = 방위 **선형평균**(viz_report2.py:841, 10log₁₀(mean σ)).
#       평균 규약이 정렬되는 것은 **multiband 쪽**(§III-1 이 선형평균이라 명시).
#       mono3d 는 같은 데이터를 **dB영역 평균**으로 요약해 3.2~3.6 dB 위로 나온다
#       (로그정규 (ln10/20)·ε² ≈ 3.2 dB 로 설명됨 — 노트 §2-2, PDF 확인).
# --------------------------------------------------------------------------- #
# multiband — Das·Zhang 외, IEEE WCL 15:3731-3735 (2026), Table III(p.3734).
#   Phantom 3, θb=0°(모노스태틱), 무향실 far-field, **수평면 el=0°**. μ(f)=0.21·f_GHz−19.19 [dBsm].
PRIOR_MB_P3 = dict(mm=350.0, avg="선형", a=0.21, b=-19.19,
                   cite="multiband · IEEE WCL 15:3731 · Table III · [PDF]")
# mono3d — Yuan·Yu·Li·Fan, EuCAP 2025, IV절(p.4). 같은 Phantom 3(동일 캠페인).
#   θ=90°(**수평면 el=0°**), CATR 모노스태틱, VV. μ(f)=0.315·f_GHz−16.15 [dBsm], dB영역 평균.
PRIOR_M3D_P3 = dict(mm=350.0, avg="dB영역", a=0.315, b=-16.15,
                    cite="mono3d · EuCAP 2025 · IV절 · [PDF]")


def _lit_mean(anchor, fc_ghz):
    """선행 회귀 μ(f)=a·f+b 를 우리 밴드 중심주파수에서 평가한 방위평균 [dBsm]."""
    return anchor["a"] * fc_ghz + anchor["b"]


# 우리 350 mm 정합기(phantom4 — Phantom 3 와 대각 정확히 일치)로 사과-대-사과 Δ 를 낸다.
# 손으로 안 적는다: JSON mean − 문헌 회귀값(밴드 fc 에서 평가).
_AA = "phantom4"
_AA_FC = {b: DR[_AA]["bands"][b]["fc_ghz"] for b in BANDS}
_AA_DB = {b: DR[_AA]["bands"][b]["mean_dbsm"] for b in BANDS}
_MB_MEAN = {b: _lit_mean(PRIOR_MB_P3, _AA_FC[b]) for b in BANDS}
_M3D_MEAN = {b: _lit_mean(PRIOR_M3D_P3, _AA_FC[b]) for b in BANDS}
_AA_DMB = {b: _AA_DB[b] - _MB_MEAN[b] for b in BANDS}      # 우리 − multiband(선형↔선형)
_AA_DM3D = {b: _AA_DB[b] - _M3D_MEAN[b] for b in BANDS}    # 우리 − mono3d(선형↔dB영역)
# 같은 측정을 두 논문이 요약한 값이 얼마나 벌어지나 = 평균규약 차 (절대판정 하한 불확도)
_CONV_SPREAD = {b: _M3D_MEAN[b] - _MB_MEAN[b] for b in BANDS}
# 문헌 절대앵커의 산포: Li&Ling **peak**(−27.5) 가 두 실험실 **mean** 보다도 아래다(물리 불가) →
#   두 앵커 절대교정 레벨 차 (3.5 GHz 기준). peak<mean 이므로 실제 교정차는 이 값보다 더 크다.
_LILING_PEAK35 = PRIOR_LILING["DJI Phantom 2"][1]         # −27.5 (Phantom 2 aspect-peak @3–6 GHz)
_ANCHOR_SPREAD = _M3D_MEAN[_BAND_35] - _LILING_PEAK35     # mono3d mean − Li&Ling peak @3.5


# --- 크기 짝 aspect-peak 대조 (밴드 3–6 GHz · 모노스태틱 · 방위최대, 3축 정합) ------- #
def _size_pair(d):
    """우리 기체 d 와 대각이 가장 가까운 Li&Ling 실측 기체를 짝짓고 Δ[dB] 를 낸다."""
    ours_mm = float(DR[d]["diagonal_mm"])
    name = min(PRIOR_LILING, key=lambda k: abs(PRIOR_LILING[k][0] - ours_mm))
    lit_mm, lit_db = PRIOR_LILING[name]
    return name, lit_mm, lit_db, DR[d]["bands"][_BAND_35]["peak_dbsm"] - lit_db


_PAIR = {d: _size_pair(d) for d in ORDER}


def _pair_ratio(d):
    """짝의 대각 비(우리/문헌). 1 에서 멀수록 '크기 짝' 이라는 말이 약해진다."""
    return float(DR[d]["diagonal_mm"]) / _PAIR[d][1]


def _pair_sizecorr_db(d):
    """광학영역 면적 스케일링 20·log10(대각비) — 이 절이 Semkin 행에서 쓰는 바로 그 보정."""
    return 20.0 * math.log10(_pair_ratio(d))


# 문헌 최대 기체가 560 mm 라 1045 mm 짜리에는 대응 짝이 아예 없다. 그래서 peak↔peak 참고범위는
# **대각비가 ±10 % 안인 짝**에서만 잡고, 벗어난 짝은 같은 면적 스케일링으로 보정해 따로 적는다.
_PAIR_TOL = 0.10
_PAIR_OK = [d for d in ORDER if abs(_pair_ratio(d) - 1.0) <= _PAIR_TOL]
_PAIR_LOOSE = [d for d in ORDER if d not in _PAIR_OK]
_PAIR_LO = min(_PAIR[d][3] for d in _PAIR_OK)
_PAIR_HI = max(_PAIR[d][3] for d in _PAIR_OK)
# 보정 후에도 부호가 유지되는지 — 유지되면 결론(우리가 밝다)이 짝짓기 규약에 의존하지 않는다.
_PAIR_ADJ = {d: _PAIR[d][3] - _pair_sizecorr_db(d) for d in ORDER}
_PAIR_ADJ_LO = min(_PAIR_ADJ.values())
_loose_txt = "·".join("{} ×{:.2f}".format(DR[d]["name"], _pair_ratio(d)) for d in _PAIR_LOOSE)
# 대각이 정확히 같은 최정합 짝(둘 다 350 mm DJI 쿼드)
_TIGHT = min(ORDER, key=lambda d: abs(DR[d]["diagonal_mm"] - _PAIR[d][1]))


# --- 방위패턴 보조 (§4) — sigma_smooth 에서 직접 유도, 손으로 안 적는다 -------------- #
def _pat_db(d, band=_BAND_35):
    s = DR[d]["bands"][band]["sigma_smooth"]
    return [10.0 * math.log10(v) for v in s[:-1]]        # 361점 → 360° 중복 제거


def _peak_az(d):
    y = _pat_db(d)
    return max(range(len(y)), key=lambda i: y[i])


def _sector_dev(d, c, half=15):
    """방위 c°±half 구간 평균이 방위평균(dB)보다 몇 dB 위인가."""
    y = _pat_db(d)
    m = sum(y) / len(y)
    sel = [y[i] for i in range(len(y)) if min(abs(i - c), len(y) - abs(i - c)) <= half]
    return sum(sel) / len(sel) - m


# 검사 방위 0/90/180/270° 는 우리가 고른 집합이 아니라 선행 규약이다 —
#   Zhang 외 arXiv:2505.20673 Fig.7(d): DJI M350 무향실 모노스태틱에서 "higher RCS values around
#   0°, 90°, 180°, and 270°, forming a four-leaf shape"(사각 동체 탓). 우리는 그 축만 빌려 쓴다.
#   ⚠ 그들의 four-leaf 는 방위 **포락선** 모델이라 로브 '개수' 판정에 쓰면 범주 오류다(잔차 리플).
_CARD = (0, 90, 180, 270)
_P4_DEV = [_sector_dev("phantom4", c) for c in _CARD]
_M5_DEV = [_sector_dev("mini5pro", c) for c in _CARD]


# --- 밴드 기울기의 구속력 (§6) — 3점 최소제곱 R², 선형회귀를 손으로 안 적는다 -------- #
def _band_r2(d):
    xs = [DR[d]["bands"][b]["fc_ghz"] for b in BANDS]
    ys = [DR[d]["bands"][b]["mean_dbsm"] for b in BANDS]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = sxy / sxx
    b = my - a * mx
    ss_res = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return 1.0 - ss_res / ss_tot


_R2 = {d: _band_r2(d) for d in ORDER}


# --- flash rate 의 식별력 (§5) — 값이 몇 개나 되나 -------------------------------- #
def _flash_groups():
    g = {}
    for d in ORDER:
        g.setdefault(round(MD[d]["flash_hz"], 2), []).append(DR[d]["name"])
    return g


_FLASH_G = _flash_groups()
_FLASH_TIE = [v for v in _FLASH_G.values() if len(v) > 1]


# =========================================================================== #
#  ⭐선행 방법론 정량 대조 앵커 — outputs/rcs_anchor.json (없으면 graceful)
#  benchmark/rcs_anchor.py 가 **원시 σ(az)**(단일주파수·평활 없음)로 회귀·분포·금속구·
#  분위점을 계산해 남긴다. 정독노트 §4-P1(9~16)·§2 의 절차를 그대로 차용한 것.
#  ⚠ 여기 숫자는 문헌 기준값(literature)·우리 값 모두 **그 JSON 에서만** 읽어 주입한다.
# =========================================================================== #
JSA = os.path.join(ROOT, "outputs", "rcs_anchor.json")
A = None
if os.path.exists(JSA):
    try:
        with open(JSA) as _f:
            A = json.load(_f)
    except Exception:
        A = None
_HAS_ANCHOR = A is not None

# el=0° 문헌 대조컷이 이제 계산됐으므로 "다음 단계" 유예 문구를 실제 산출로 교체.
_EL0_PHRASE = ("el=0° 문헌 대조컷은 아래 **§6.1(선행 방법론 정량 대조)** 에서 5기종×3밴드로 산출했다"
               if _HAS_ANCHOR else "el=0° 문헌 대조컷 산출은 다음 단계다")
_EL0_TAIL = ("대조컷은 §6.1 산출완료" if _HAS_ANCHOR else "대조컷은 다음 단계")

_DISP = {"rician": "Rician", "gamma": "Gamma", "lognormal": "LogN"}


def _anchor_cells():
    """A(rcs_anchor.json)에서 §6.1 정량 대조 md 셀을 만든다. A 없으면 [] (graceful)."""
    if A is None:
        return []
    AB = list(A["meta"]["bands"].keys())               # ["LTE 1.843 GHz","5G 3.5 GHz","WiFi 5.21 GHz"]
    LAB = {AB[0]: "1.8", AB[1]: "3.5", AB[2]: "5.2"}    # 표시용 GHz
    B35 = AB[1]
    lit = A["literature"]
    mb = lit["mu_eps"]["multiband_phantom3"]
    m3 = lit["mu_eps"]["mono3d_theta90"]
    dlit = lit["distribution"]
    mb_ad = dlit["multiband_phantom3"]["rician"]
    m3c = dlit["mono3d_avg"]
    slit = lit["sphere_calibration"]["unified_rcs_0p5m"]
    sth = lit["sphere_calibration"]["pass_threshold_db"]
    P = lit["percentiles_norm"]
    fav, poor = P["favorable_dominant_present"], P["poor_dominant_absent"]
    D = A["drones"]
    AO = [d for d in ORDER if d in D]   # 결측 기종(계산 미완)에 graceful

    # ── (1) μ(f)=a·f+b 회귀 (el=0, 원시 방위 선형평균) ────────────────────── #
    reg = {d: D[d]["regression"]["el0"] for d in AO}
    t1 = ["| 기체 (대각 mm) | a [dB/GHz] | b [dBsm] | R²_μ | ε 기울기 c |",
          "|---|---|---|---|---|"]
    for d in AO:
        r = reg[d]
        t1.append(f"| {DR[d]['name']} ({DR[d]['diagonal_mm']:.0f}) | {_m(r['a'])} | "
                  f"{_m(r['b'])} | {r['R2_mu']:.2f} | {_m(r['c'], '+.3f')} |")
    t1 += [f"| **multiband Phantom 3 (350)** | **{mb['mu_a']:.3f}** | {_m(mb['mu_b'])} | — | "
           f"{mb['eps_c']:.3f} |",
           f"| **mono3d θ=90° (350)** | **{m3['mu_a']:.3f}** | {_m(m3['mu_b'])} | — | — |"]

    # ── (2) 분포 적합 (3.5 GHz, el=0, **진폭 √σ** 도메인 = 문헌 Rician 규약) ── #
    t2 = ["| 기체 (3.5 GHz · 진폭 √σ) | d_AD Rician | d_CvM Ric / Gam / LogN | 최선 AD·CvM |",
          "|---|---|---|---|"]
    ric_ad_n = ric_cvm_n = 0
    for d in AO:
        am = D[d]["bands"][B35]["el0"]["distributions"]["amplitude"]
        f = am["fits"]
        ad_r = f["rician"]["d_AD_textbook"]
        cvm = (f["rician"]["d_C"], f["gamma"]["d_C"], f["lognormal"]["d_C"])
        if am["best_by_AD"] == "rician":
            ric_ad_n += 1
        if am["best_by_CvM"] == "rician":
            ric_cvm_n += 1
        t2.append(f"| {DR[d]['name']} | {ad_r:.3f} | "
                  f"{cvm[0]:.3f} / {cvm[1]:.3f} / {cvm[2]:.3f} | "
                  f"{_DISP[am['best_by_AD']]}·{_DISP[am['best_by_CvM']]} |")
    t2 += [f"| **multiband Phantom 3 (AD)** | **{mb_ad:.3f}** (Rician 최선) | — | Rician |",
           f"| **mono3d 평균 (CvM)** | — | **{m3c['rician']:.2f} / {m3c['gamma']:.2f} / "
           f"{m3c['lognormal']:.2f}** | Rician<Gamma<LogN |"]

    # ── (3) 금속구 절대교정 — 기준해는 **정확 Mie**(판정)와 **해석 PO**(커널의 과녁) 둘이고,
    #        πr² 은 문헌 관례를 맞추기 위한 **라벨된 점근값**일 뿐이다(참값 아님).
    t3 = ["| 밴드 | 정확 Mie (0.25 / 0.178 m) | 우리 SBR | 편차 vs Mie | 편차 vs 해석 PO | "
          "편차 vs πr² 점근 | 합격 <2 dB |",
          "|---|---|---|---|---|---|---|"]
    sph_dev_mie, sph_dev_po = [], []
    _asym = []                                          # πr² 점근 자체가 Mie 에서 벗어난 양
    _kas = []                                           # 교정구의 ka 범위(밴드·반지름 순서에 의존하지 않게)
    for bk in AB:
        sp = A["sphere_calibration"][bk]["spheres"]
        s0, s1 = sp[0], sp[1]
        for s in sp:
            _need(s, "dev_db_vs_mie", "rcs_anchor.json sphere_calibration")
        sph_dev_mie += [abs(s0["dev_db_vs_mie"]), abs(s1["dev_db_vs_mie"])]
        sph_dev_po += [abs(s0["dev_db_vs_po"]), abs(s1["dev_db_vs_po"])]
        _asym += [abs(s0["asymptote_err_db"]), abs(s1["asymptote_err_db"])]
        _kas += [s0["ka"], s1["ka"]]
        ok = "✅" if all(s["pass_lt2db"] for s in sp) else "⚠"
        t3.append(f"| {LAB[bk]} GHz | {_m(s0['mie_dbsm'])} / {_m(s1['mie_dbsm'])} | "
                  f"{_m(s0['sbr_dbsm'])} / {_m(s1['sbr_dbsm'])} | "
                  f"**{_m(s0['dev_db_vs_mie'])} / {_m(s1['dev_db_vs_mie'])}** | "
                  f"{_m(s0['dev_db_vs_po'])} / {_m(s1['dev_db_vs_po'])} | "
                  f"{_m(s0['dev_db_vs_go'])} / {_m(s1['dev_db_vs_go'])} | {ok} |")
    t3.append(f"| **unified-rcs 실측 (28 GHz)** | — | {_m(slit['measured_dbsm'])} | — | — | "
              f"**{slit['dev_db']:.2f}** (πr² {_m(slit['theory_dbsm'])}, 0.25 m) | "
              f"✅ (합격선 {sth:.0f}) |")
    sph_max = max(sph_dev_mie)
    sph_max_po = max(sph_dev_po)
    sph_asym_max = max(_asym)
    ka_lo, ka_hi = min(_kas), max(_kas)

    # ── (4) el=0° vs el=15° 컷 (원시 방위 선형평균) — 앙각 편향 정량 ───────── #
    t4 = ["| 기체 | LTE el0−el15 | 5G el0−el15 | WiFi el0−el15 |",
          "|---|---|---|---|"]
    cut_all = []
    for d in AO:
        row = []
        for bk in AB:
            e0 = D[d]["bands"][bk]["el0"]["mean_dbsm"]
            e15 = D[d]["bands"][bk]["el15"]["mean_dbsm"]
            row.append(e0 - e15)
            cut_all.append(e0 - e15)
        t4.append(f"| {DR[d]['name']} | {_m(row[0])} | {_m(row[1])} | {_m(row[2])} |")
    cut_lo, cut_hi = min(cut_all), max(cut_all)

    # ── (5) 평균전력 정규화 분위점 P10/P1 (원시 el=0) ────────────────────── #
    t5 = ["| 기체 | LTE P10/P1 | 5G P10/P1 | WiFi P10/P1 |",
          "|---|---|---|---|"]
    p1_all = []
    for d in AO:
        cells_p = []
        for bk in AB:
            pc = D[d]["bands"][bk]["el0"]["percentiles"]
            cells_p.append(f"{_m(pc['P10_db'])} / {_m(pc['P1_db'])}")
            p1_all.append(pc["P1_db"])
        t5.append(f"| {DR[d]['name']} | {cells_p[0]} | {cells_p[1]} | {cells_p[2]} |")
    p1_lo, p1_hi = min(p1_all), max(p1_all)

    ph4a = reg["phantom4"]["a"]

    return [md(
        "---",
        "### §6.1. 선행 방법론을 그대로 차용한 정량 대조 (원시 σ 로)",
        "",
        "위 §6 은 **평활·대역평균 후** 값(`sigma_smooth`)으로 절대 레벨을 견줬다. 여기서는 정독노트 "
        "§4-P1(9~16)이 지목한 선행 절차 — **분포적합·μ/ε 회귀·금속구 교정·el컷·분위점** — 을 그대로 "
        "가져와 우리 σ 를 문헌과 **정량비교**한다. ⚠ **입력은 전부 원시 σ(az)**다 — 단일 주파수·평활 없이 "
        f"`rcs_sbr` 를 직접 호출한 값(방위 {A['meta']['n_az_band']}점, 회귀 {A['meta']['n_az_reg']}점). "
        "`sigma_smooth`(밴드 5주파수 평균 + 3° 각도창)는 널을 ~18 dB 메워 분포·분위점을 왜곡하므로 통계에 "
        "쓰지 않는다(`src/rcs_po.py:191-193`). 문헌 기준값은 원문 PDF 로 확인한 것만 상수로 넣었다"
        f"(`benchmark/rcs_anchor.py` LITERATURE, 산출 {A['meta']['generated']}).",
        "",
        "**(1) μ(f)=a·f+b 방위 선형평균 회귀** (1.8–6 GHz 0.2 GHz 간격 22점, el=0°). 문헌 기울기와 나란히:",
        "",
        *t1,
        "",
        f"<sub>기울기 a 는 σ 의 **대역 상승률**이다. 우리 값은 문헌(multiband {mb['mu_a']:.2f}·"
        f"mono3d {m3['mu_a']:.3f} dB/GHz)보다 대체로 **가파르다** — 우리 밴드(1.8–6 GHz)가 소형 표적의 "
        "**few-λ 공진영역**이라 σ 가 주파수에 민감하고, 광대역 단일 선형적합이 그 곡률을 한 기울기로 "
        f"뭉치기 때문이다(R²_μ 도 {min(reg[d]['R2_mu'] for d in AO):.2f}~"
        f"{max(reg[d]['R2_mu'] for d in AO):.2f} 로 낮아 선형성이 약함을 스스로 보고한다). 같은 대각 "
        f"350 mm 정합기(phantom4)조차 a={_m(ph4a)} 로 문헌보다 크다 — 절대 기울기는 정량 대조하되 "
        "**일치를 주장하지 않는다**.</sub>",
        "",
        "**(2) 분포 적합** Rician/Gamma/LogNormal 을 원시 방위 표본에 MLE 적합(3.5 GHz, el=0°). "
        "적합도거리 두 종 — Anderson–Darling(multiband 식5)·Cramér–von Mises(mono3d). ⚠ scipy `rice` 는 "
        "**진폭** 분포이고 문헌 Rician 도 통상 진폭 규약이라, 사과-대-사과가 되도록 **진폭 √σ 도메인**에서 "
        "적합한다(전력 σ 도메인은 Rician 이 구조적으로 불리):",
        "",
        *t2,
        "",
        f"<sub>진폭 도메인에서 CvM 최선이 **Rician 인 기종은 {ric_cvm_n}/5**, AD 최선이 Rician 인 기종은 "
        f"{ric_ad_n}/5 다 — mono3d 가 보고한 **Rician<Gamma<LogNormal** 순위(CvM 0.28/0.31/0.48)와 "
        "**정성적으로 일치**한다. 우리 d_AD(Rician)는 multiband 기준 0.436 과 자릿수가 같다. ⚠ 한계: "
        "d_CvM 은 노트 식이 √ 를 포함해 **절대치가 √-스케일**이라 **순위 비교만** 안전하다(절대 등치 금지). "
        "또 전력 σ 도메인에서는 변량 불일치로 Gamma/LogNormal 이 이기므로, 분포 선택 결론은 "
        "**진폭 도메인 한정**이다.</sub>",
        "",
        f"**(3) 금속구 절대교정.** 지름 0.5 m(r=0.25)·r=17.8 cm PEC 구를 우리 "
        f"SBR+PO(`group_mat={{'metal':'metal'}}`)로 돌려 편차를 낸다. 합격선 **< {sth:.0f} dB** "
        f"(unified-rcs 실측 편차 {slit['dev_db']:.2f} dB). **기준해를 두 개 놓는다** — 커널이 "
        "SBR+**PO** 이므로 수치 수렴의 과녁은 **해석 PO** 이고, 절대 정확도의 자는 **정확 Mie** 다. "
        f"이 교정구들은 ka={ka_lo:.1f}~{ka_hi:.1f} 로 작아서 광학 점근 πr² 자체가 "
        f"Mie 에서 최대 {sph_asym_max:.2f} dB 어긋난다 → πr² 은 **문헌 관례 비교용 점근값**으로만 "
        "싣고 판정에는 쓰지 않는다:",
        "",
        *t3,
        "",
        f"<sub>세 밴드·두 반지름 전부 정확 Mie 대비 편차 **≤ {sph_max:.2f} dB** 로 **합격선 "
        f"{sth:.0f} dB 를 통과**한다(unified-rcs 실측 편차 {slit['dev_db']:.2f} dB 와 같은 자릿수). "
        f"해석 PO 대비로는 **≤ {sph_max_po:.2f} dB** 로 더 작다 — 그 차이가 곧 **PO 근사를 쓴 대가**이고 "
        "우리 수치오차가 아니다. 즉 절대 스케일 자체는 옳고, 남는 편차의 성분이 두 갈래(격자 수치오차 + "
        "PO 모델오차)로 분리된다. ⚠ 옛 판은 이 편차를 πr² 하나에 적었는데, 그러면 점근 오차가 우리 "
        "편차를 상쇄해 **실제보다 좋아 보인다**(5G·r=0.178 m: πr² 기준 "
        f"{_m(A['sphere_calibration'][AB[1]]['spheres'][1]['dev_db_vs_go'], '+.3f')} dB ↔ Mie 기준 "
        f"{_m(A['sphere_calibration'][AB[1]]['spheres'][1]['dev_db_vs_mie'], '+.3f')} dB). 드론 절대값의 "
        "불확실성은 교정이 아니라 **few-λ 유전체 형상·편파·자세**에서 온다.</sub>",
        "",
        "**(4) el=0° 문헌 대조컷** (원시 방위 선형평균, 5기종×3밴드). 문헌은 전부 **수평면(el=0°)**인데 우리 "
        f"기본 자세는 el={EL:.0f}° 라, 그 앙각 편향을 el0−el15 로 정량화한다(§2-3 이 2기종만 냈던 것을 5기종으로 확장):",
        "",
        *t4,
        "",
        f"<sub>앙각 편향은 **{_m(cut_lo, '+.1f')} ~ {_m(cut_hi, '+.1f')} dB** 이고 **부호가 밴드·기종마다 "
        "다르다**(고역일수록 el=0° 가 밝은 경향). 즉 우리 el=15° 값을 문헌 el=0° 과 견줄 때 밴드에 따라 "
        "수 dB 어긋날 수 있으며, 이 표가 그 보정량이다. 문헌과 자세를 맞추려면 el=0° 열을 써야 한다.</sub>",
        "",
        "**(5) 평균전력 정규화 분위점 P10/P1** (원시 el=0°, mono3d IV절 지표). 문헌: **−8.5/−18.5 dB "
        "(우세성분 有)** · **−10/−20 dB (無, 지수분포 이론 −9.77/−19.98=Swerling I/II)**:",
        "",
        *t5,
        "",
        f"<sub>우리 P1 은 {_m(p1_lo, '+.1f')}~{_m(p1_hi, '+.1f')} dB 로 문헌 두 극단(−18.5 / −20) "
        "**보다 얕다** — 원시 단일주파수라도 우리 방위 표본이 문헌 실측만큼 깊은 페이딩 꼬리를 만들지 "
        "않는다는 뜻이다(우세 정반사 성분이 상대적으로 강함 = Rician 이 이기는 것과 정합). 이 지표를 "
        "요동 Swerling 모델의 기종별 선택 근거로 쓸 수 있다(→ Pd 후속).</sub>",
        "",
        "---",
        "**추가 선행 방법론 메모 (P1-17·P1-18, 계산 불필요 — md-multiprop 유도).**",
        "",
        "- **P1-17 바이스태틱 근사오차 상한.** 산란점을 표적 중심으로 뭉개는 근사의 오차는 "
        "`Err ≤ (l²/2)(1/R_T + 1/R_R)` (md-multiprop Appendix D). 우리 챔버 R_T=18.75, R_R=18.61 m, 최대 "
        "블레이드 반길이 l≈0.19 m → **Err ≤ 1.9 mm**, 바이스태틱 거리합의 **0.005%** — 표적을 점산란체로 "
        "봐도 무방하다.",
        "- **P1-18 거리분해능 이중표기.** 우리 규약은 **바이스태틱 거리합** `ΔR = c/B`; md-multiprop"
        "(Willis)은 **이등분선 방향** `ΔR = c/[2B·cos(β/2)]`. 같은 물리인데 축이 다르다(WiFi 예: "
        "3.916 m ÷ (2×0.915) = 2.14 m). ⚠ md-props **학회판**은 `c/(2B)` 라 적었고 **저널판이 정정**했다 — "
        "학회판만 읽고 우리 규약을 '2배 틀렸다' 판정하면 안 된다.",
        "",
        "<sub>**§6.1 이 바꾼 것 / 여전히 남는 한계.** 이 정량 대조는 §6 의 *el=0° 대조컷 유예*와 *분포·회귀·"
        "구교정 미실시*를 **실제 수치로 대체**한다. 그러나 **절대 dBsm 판정은 여전히 보류**다 — (a) 문헌 "
        "앵커 자체가 서로 3.2~3.6 dB(multiband↔mono3d 평균규약)·그 이상(Li&Ling peak<mean) 산포하고, "
        "(b) 우리 SBR 은 **스칼라 Γ 라 편파(co/cross)를 분리하지 않는데** 문헌은 co-pol 측정이며, "
        "(c) 표적이 문헌은 **Phantom 3**, 우리는 대각만 같은 **Phantom 4**(세대·부품 다름)다. 구 교정이 "
        "<0.1 dB 로 통과한다는 것은 **절대 스케일 파이프라인이 옳다**는 뜻이지 드론 절대 σ 가 검증됐다는 뜻이 "
        "아니다. 분포 순위(진폭 Rician 우세)·대역 기울기·앙각 편향·분위점은 문헌과 **정성적으로 정합**하되, "
        "절대 점값은 위 세 미정렬 축이 열려 있는 한 판정 보류를 유지한다.</sub>",
    )]


cells = []

# =========================================================================== #
#  0. 앞머리 (provenance) — 라이브러리 척추 리드
# =========================================================================== #
cells += provenance_cells(
    report="report08",
    what="드론 RCS·마이크로도플러 결과 (밴드별·자세별)",
    question="드론 5종은 실제로 얼마나 밝고, 프로펠러는 어떤 지문을 남기나?",

    spine=dict(
        core=("탐지는 표적이 레이더 눈에 **얼마나 밝은가(RCS, σ)**에서 출발한다. 이 리포트는 드론 5종의 "
              "**절대 RCS** 와 프로펠러 **마이크로도플러 지문**을 자작 SBR+PO 로 산출하고, 그 절대값을 "
              "**실측 문헌과 밴드·지표·크기·평균규약을 맞춰** 견준다. **절대 dBsm 판정은 보류한다** — "
              f"소형 쿼드의 문헌 절대앵커 자체가 서로 **{_ANCHOR_SPREAD:.0f} dB 넘게** 어긋나(같은 자세-peak 이 "
              "다른 실험실 방위-mean 보다 아래에 오는, 물리적으로 불가능한 산포) 절대 판정의 기준이 될 수 없기 "
              "때문이다(§6). 밴드·지표·크기·평균규약을 모두 맞춘 **유일한 사과-대-사과 앵커**(multiband Phantom 3 "
              f"방위 선형평균)와는 우리 350 mm 정합기가 **{min(abs(v) for v in _AA_DMB.values()):.1f}~"
              f"{max(abs(v) for v in _AA_DMB.values()):.1f} dB 안**에서 맞는다. 그래서 검출은 σ 밴드로 제시하고 "
              "**상대 결론(모드·파형 비교)만** 주장한다."),
        gap=(f"스톡 Sionna `PathSolver` 는 표적 σ 를 아예 주지 않고(→report06), 그 위에 얹은 SBR+PO 도 "
             f"기준해(평판 정확 PO σ=4πA²/λ²·구 해석 PO/정확 Mie)로는 **방법이 옳음만** 검증될 뿐 — "
             f"파이프라인 안에 드론의 "
             f"**절대 σ 를 대조할 자체 기준이 없다.** 밝기 차이는 크게는 {_span:.0f} dB 에 이른다."),
        prior=("소형 멀티로터의 RCS 는 **실측 문헌**이 기준이다. S밴드(3–6 GHz) 실측 aspect-peak 은 "
               "Li & Ling 2017(IEEE AWPL): Phantom 2(350 mm) "
               f"**{_m(PRIOR_LILING['DJI Phantom 2'][1], '+.1f')}** ~ Inspire 1(560 mm) "
               f"**{_m(PRIOR_LILING['DJI Inspire 1'][1], '+.1f')} dBsm**"
               "(등급 [N] — 워크스페이스 노트 근거, PDF 부재). "
               "⚠ 그 문헌은 **방위평균을 보고하지 않는다** — 'S밴드 방위평균 포락선' 은 aspect-peak 과 자세 "
               "스프레드에서 **유도해야 하는 2차 산물**이므로 판정 근거로 쓰지 않는다. 대조는 **peak↔peak** 로만 한다. "
               "⚠ 소형드론 RCS 는 **저주파로 갈수록 떨어진다**(공진/레일리) — "
               "同 문헌에서 3–6 GHz 는 12–15 GHz 보다 평균 ~12 dB 낮다(15 GHz 방위평균: Mavic Pro −17·Phantom 4 "
               "−15 dBsm, Ezuma arXiv:1911.05926/2102.11954)."),
        lib=("표적 σ 는 **자작 SBR+PO** 로 계산한다(절차 →report07) — Sionna 가 쓰는 **Mitsuba 3 광선엔진을 "
             "그대로 재사용**하고 그 위에 PO 표면적분만 얹어(새 광선엔진 없음·중복계산 없음) 복소장 E 를 "
             "직접 낸다. BVH SBR+PO(arXiv:2604.09243)와 같은 계열이다(적용범위 차이는 report06 §4)."),
        verify=("우리 σ 는 **크기 순서·자세 구조·자릿수·대역 추세**를 재현한다. **절대 레벨은 판정 보류다**: "
                "밴드·지표·기하·평균규약을 모두 맞춘 사과-대-사과 앵커(multiband Phantom 3, 방위 **선형평균**)와 "
                f"우리 350 mm 정합기(phantom4)는 3.5/5.2 GHz 에서 **{abs(_AA_DMB[_BAND_35]):.1f}/"
                f"{abs(_AA_DMB['WiFi 5.2 GHz']):.1f} dB**, 1.8 GHz 에서 **{abs(_AA_DMB['LTE 1.8 GHz']):.1f} dB** "
                "안에서 맞는다(우리가 약간 어두운 쪽). 같은 측정을 다른 규약으로 요약한 mono3d 와는 "
                f"{abs(_AA_DM3D[_BAND_35]):.1f}~{abs(_AA_DM3D['LTE 1.8 GHz']):.1f} dB 어긋나는데, 그 "
                f"{_CONV_SPREAD[_BAND_35]:.1f} dB 벌어짐 자체가 **선형↔dB영역 평균 규약 차**다(§6). ⚠ 앙각(우리 "
                "el=15° ↔ 문헌 el=0°)·편파(우리 스칼라 Γ ↔ 문헌 co-pol)는 아직 정렬되지 않았다. 그래서 검출은 "
                "σ 밴드로 제시해 **상대 결론(모드·파형 비교)의 robust 함**을 보인다."),
    ),

    sources=[
        dict(item="드론 물리 스펙 (대각·무게·프로펠러·로터 수)",
             src="DJI 공식 제품 스펙 (Mini 5 Pro · Mavic 4 Pro · Matrice 4E · S1000+ · Phantom 4)",
             kind="📄 제조사 스펙"),
        dict(item="5종 RCS (3밴드) · 재질 분해",
             src="**`outputs/report2_waveform_rcs.json`** 의 `rcs` / `materials`. "
                 "`src/viz_report2.py` 가 `src/rcs_sbr.py`(SBR)를 돌려 남긴다",
             kind="🟡 측정 (SBR = Mitsuba 광선 + PO)"),
        dict(item="호버 rpm 유도 · 블레이드 마이크로도플러",
             src="**`outputs/report1.json`** 의 `articulation`(추력 균형) / `microdoppler`. "
                 "`src/viz_report3.py` + `src/microdoppler.py` 가 남긴다",
             kind="🟡 측정 (자세별 SBR 산란장)"),
        dict(item="재질별 반사계수",
             src="**`src/materials.py`** — Sionna RT 와 SBR 이 함께 읽는 단일 진리원 "
                 "(ITU-R P.2040 기반 + custom)",
             kind="📐 물성표"),
        dict(item="실측 문헌 드론 RCS (절대값 앵커)",
             src="Li & Ling 2017(IEEE AWPL) · Ezuma/Güvenç(arXiv:1911.05926) · "
                 "Güvenç/NCSU 서베이(arXiv:2402.05909) · Semkin 2020 · Frankford/Björklund(IET RSN)",
             kind="📚 실측 문헌 (검증 기준)"),
    ],

    engines=["sbr", "microdoppler", "sionna-render", "po", "matplotlib"],
    libs=["sionna", "mitsuba", "drjit", "trimesh", "scipy", "numpy", "matplotlib"],

    reproduce=[
        "cd /home/yunjung/workspace/sionna2",
        "",
        "# 5종 RCS(3밴드) + 재질 분해  -> report2_waveform_rcs.json",
        "~/.venvs/py312/bin/python src/viz_report2.py",
        "",
        "# 호버 rpm 유도 + 블레이드 마이크로도플러  -> report1.json",
        "~/.venvs/py312/bin/python src/viz_report3.py",
        "",
        "# JSON -> report08.ipynb (이 파일)",
        "~/.venvs/py312/bin/python src/make_notebook08.py",
    ],

    artifacts=[
        dict(file="outputs/report2_waveform_rcs.json",
             what="**이 노트북의 RCS 숫자.** rcs(5종×3밴드) / materials(재질 분해)"),
        dict(file="outputs/report1.json",
             what="**이 노트북의 마이크로도플러 숫자.** articulation(호버 rpm) / microdoppler(지문)"),
        dict(file="outputs/figures/report2_rcs_bars.png", what="§2 5종 밝기 · 크기 추세"),
        dict(file="outputs/figures/report2_materials.png", what="§3 재질 분해 (껍데기 vs 금속)"),
        dict(file="outputs/figures/report2_rcs_polar.png", what="§4 방위 패턴 (로브 vs 널)"),
        dict(file="outputs/figures/report1_hover_rpm.png", what="§5 호버 rpm 유도"),
        dict(file="outputs/figures/report1_microdoppler.png", what="§5 블레이드 지문 + 가림 대가"),
    ],

    caveats=[
        f"**절대 RCS 를 보장하지 않는다.** SBR 은 기준해(구·평판)로 검증되고(방법 검증은 report07), 드론 절대값은 "
        f"§6 에서 **실측 문헌에 대조**했다 — 사과-대-사과 앵커(multiband Phantom 3 방위 선형평균)와는 "
        f"**{min(abs(v) for v in _AA_DMB.values()):.1f}~{max(abs(v) for v in _AA_DMB.values()):.1f} dB 안**에서 "
        f"맞지만, 문헌 앵커 자체가 **{_ANCHOR_SPREAD:.0f} dB 넘게 산포**해 절대 dBsm 은 **판정 보류**다. 이 리포트가 "
        "지지하는 것은 **상대 순서**(큰 기체가 밝다)와 **대역 추세**(밴드는 몇 dB만 움직인다)이지 특정 드론의 "
        "절대 dBsm 점값이 아니다.",

        f"**플라스틱 셸의 밝기는 불확실 구간이다.** 1~3 mm 셸은 1.8~5.2 GHz 에서 **반투명**인데 "
        f"first-hit SBR 은 셸을 뚫지 못한다. 그래서 진실은 '통드론'과 '셸 제거' 두 막대 사이에 "
        f"있고, 그 간격 **{abs(_noshell['delta_db']):.1f} dB** 는 측정오차가 아니라 **모델링 "
        "불확실도**로 읽어야 한다.",

        "**방위 패턴의 '널(골)'은 인용 금지.** 로브 사이 골은 격자밀도·대역평균·평활에 10 dB 넘게 "
        "흔들린다. **로브(봉우리)와 방위평균만** 믿는다.",

        "**호버 rpm 은 가정값이다.** 추력=무게 균형(C_T≈0.11)에서 유도한 물리 추정치이지 텔레메트리 "
        "실측이 아니다. flash·f_tip 은 이 rpm 에 선형으로 비례하므로, 실제 비행 rpm 이 다르면 지문 "
        "주파수도 그만큼 이동한다.",

        "**마이크로도플러는 슬로타임 모델이다.** 자세별 산란장은 SBR(Mitsuba 광선)로 재계산하지만, "
        "블레이드 유연·와류 등 공기역학은 넣지 않았다. 지문의 **구조**(깜빡임·f_tip 경계)는 믿을 만 "
        "하나 절대 세기는 아니다.",
    ],

    cost="5종 × 3밴드 RCS 는 GPU 한 장에서 수십 분(광선격자 λ/16). "
         "마이크로도플러는 자세 144개 × SBR 재계산이라 드론당 수~십수 분.",

    related=[
        dict(rep="**앞** — [report07](report07.ipynb)",
             rel="이 숫자를 낸 **방법(SBR)** — 왜 옳은가·가림이 무엇인가"),
        dict(rep="**다음** — [report09](report09.ipynb)",
             rel="이제 탐지로. 먼저 챔버 **바닥이 놓는 함정**(표적 경유 유령)"),
    ],

    glossary=[
        ("RCS (σ)", "레이더 되비침 밝기 [m²]. '이 표적이 얼마나 밝게 되쏘나'. dBsm = 10·log₁₀(σ/1 m²)"),
        ("dBsm", "1 m² 대비 dB. −20 dBsm = 0.01 m² = 되비침이 사방 10 cm 판 만큼"),
        ("광학영역", "표적이 파장보다 훨씬 클 때. 밝기가 대략 **투영 넓이**를 따라가고 주파수엔 둔감"),
        ("SBR / PO", "**SBR**=광선 쏴 보이는 면·가림 찾는 기하 단계(Sionna 의 Mitsuba 엔진 재사용). "
                     "**PO**=그 밝은 면 위 산란장을 위상 맞춰 적분하는 물리 단계(=밝기). 스톡 Sionna 엔 PO 가 없어 우리가 얹음"),
        ("가림(occlusion)", "앞 부품에 막혀 안 보이는 면. 이걸 안 빼면 밝기·정지신호를 과대평가한다"),
        ("로브 / 널", "방위 패턴의 봉우리(로브)와 골(널). 로브는 안정, 널은 불안정 → 널은 인용 금지"),
        ("마이크로도플러", "표적의 **부분 운동**(프로펠러 회전)이 만드는 도플러 미세구조. 드론의 지문"),
        ("flash rate", "블레이드가 정면을 보여 번쩍이는 초당 횟수 = 날개수 × 회전수/60"),
        ("f_tip", "날개 끝 속도가 만드는 최대 도플러 폭. f_tip = 2·v_tip/λ·cos(el)"),
        ("pedestal(정지 몸통 신호)", "회전 안 하는 몸통이 만드는 0 Hz 근처 강한 성분. 블레이드 깜빡임은 "
                                     "이 위로 솟아야 보인다"),
        ("C_T (추력계수)", "프로펠러 추력을 회전수로 잇는 무차원 계수. T = C_T ρ n² D⁴, 소형 로터 ≈0.11"),
    ],
)

# =========================================================================== #
#  §1  스톡 파이프라인의 공백 — 무엇을 왜 재는가
# =========================================================================== #
cells.append(md(
    "## §1. 무엇을 왜 재는가 — 스톡 파이프라인의 공백",
    "",
    "탐지는 표적이 레이더 눈에 **얼마나 밝은가(RCS, σ)**에서 출발한다. 그런데 스톡 Sionna 의 기본 "
    "광선추적(`PathSolver`)은 경로별 복소이득만 반환할 뿐 표적 표면 위 산란적분이 없어 σ 를 내지 "
    "못한다(→[report06](report06.ipynb)). ISAC 선행 연구는 이 밝기를 세 갈래로 다룬다 — 확산계수 S "
    "가정, RCS 점표적 주입, 그리고 자작 SBR+PO. 우리는 세 번째, 선행이 실제로 쓰는 **SBR+PO** "
    "방식으로 σ 를 계산했다(BVH SBR+PO, arXiv:2604.09243 과 같은 계열 — Sionna 가 쓰는 Mitsuba 3 "
    "광선엔진을 그대로 재사용하고 그 위에 PO 표면적분만 얹어 복소장 E 를 직접 낸다; 절차는 "
    "→[report07](report07.ipynb)).",
    "",
    "이 리포트는 그 **결과**다 — 5종의 밝기(§2), 밝기가 어디서 나오나(§3), 방위 패턴(§4), 프로펠러 "
    "마이크로도플러 지문(§5). 다만 SBR+PO 의 기준해 검증(평판·구, report07)은 방법이 옳음만 보일 뿐 "
    "드론의 **절대 σ** 를 대조할 자체 기준이 파이프라인 안에 없다. 그래서 절대 스케일은 리포트 끝에서 "
    "**공개 실측 문헌 드론 RCS 로 앵커**한다(§6).",
))

# =========================================================================== #
#  §2  5종 얼마나 밝나 (증거)
# =========================================================================== #
_rows = []
for d in ORDER:
    v = DR[d]
    cells_b = " | ".join(f"{v['bands'][b]['mean_dbsm']:+.1f}" for b in BANDS)
    _rows.append(f"| {v['name']} | {v['diagonal_mm']} | {v['weight_g']:.0f} | {cells_b} |")

cells.append(md(
    "## §2. 5종 얼마나 밝나 — 밝기를 정하는 건 크기지 주파수가 아니다",
    "",
    "![rcs bars](outputs/figures/report2_rcs_bars.png)",
    "",
    "각 드론을 **360° 다 돌려가며**(방위) 세 통신대역에서 재고, 그 **방위평균**을 밝기 대표값으로 "
    "씁니다. (봉우리 값이 아니라 평균입니다 — 링크버짓에 넣을 정직한 숫자는 이쪽입니다.)",
    "",
    f"**밴드평균 방위평균 RCS [dBsm]** (el = {EL:.0f}°, 격자 λ/{SBR_DIV}):",
    "",
    "| 드론 | 대각 [mm] | 무게 [g] | " + " | ".join(BANDS) + " |",
    "|---|---|---|---|---|---|",
    *_rows,
    "",
    "**두 가지가 한눈에 보입니다.**",
    "",
    f"1. **크기가 밝기를 정합니다.** 가장 큰 {DR[_best]['name']}(대각 {DR[_best]['diagonal_mm']} mm, "
    f"{DR[_best]['weight_g']/1000:.1f} kg 8로터)가 가장 밝고, 가장 작은 {DR[_dim]['name']}"
    f"({DR[_dim]['diagonal_mm']} mm, {DR[_dim]['weight_g']:.0f} g)가 가장 어둡습니다. 둘 사이가 "
    f"**{_span:.1f} dB** — 퍼센트 수준이 아니라 **약 {10 ** (_span / 10):.1f} 배**(선형 σ 비) "
    "차이입니다. 오른쪽 산점도가 대각↔밝기 추세를 그대로 보여줍니다.",
    "",
    f"2. **대역(주파수)은 별로 안 움직입니다.** 같은 드론을 1.8 → 5.2 GHz 로 옮겨도 밝기는 평균 "
    f"**{_band_swing:.1f} dB** 밖에 안 변합니다. 드론이 이미 파장(λ = 6~17 cm)보다 훨씬 커서 "
    "**측정한 좁은 대역(1.8~5.2 GHz) 안에서는** 밴드 스윙이 작기 때문입니다 — 이 범위에선 밝기가 대략 **투영 넓이**를 따라가고 파장엔 "
    "둔감합니다.",
    "",
    "> **크기 순서가 무게 순서와 살짝 다른 이유.** RCS 는 무게가 아니라 **되비추는 금속 표면**이 "
    f"정합니다. {DR['phantom4']['name']}는 무겁지만(1.38 kg) 몸체가 매끈해 측면 로브가 좁고, "
    f"{DR['mini5pro']['name']}는 250 g 급이라 되쏠 금속 자체가 작습니다. 순서는 **투영된 금속 넓이** "
    "쪽을 따릅니다.",
    "",
    "> **링크버짓으로 가져갈 숫자는 방위평균입니다.** 봉우리(peak)는 순간적으로 더 밝지만 방위가 "
    "조금만 틀어져도 사라집니다 — 탐지 성능을 보수적으로 보려면 평균을 씁니다.",
))

# =========================================================================== #
#  §3  밝기는 속 금속이 지배 (증거)
# =========================================================================== #
cells.append(md(
    "## §3. 밝기는 속 금속이 지배한다 — 껍데기는 스크린이다",
    "",
    "![materials](outputs/figures/report2_materials.png)",
    "",
    f"밝기가 **어디서** 나오는지 보려면 드론을 부품별로 벗겨가며 재보면 됩니다. "
    f"{MAT['name']} 한 대를 {MAT['fc']/1e9:.1f} GHz 에서, 부품을 하나씩 지우며 방위평균 밝기를 "
    "다시 쟀습니다(밝은 쪽이 위):",
    "",
    "| 무엇을 남겼나 | 방위평균 RCS | 통드론 대비 |",
    "|---|---|---|",
    f"| **통드론** (플라스틱 셸 포함) | {_full['mean_dbsm']:+.2f} dBsm | 기준 |",
    f"| 셸 **제거** (전파가 플라스틱을 통과) | {_noshell['mean_dbsm']:+.2f} dBsm | "
    f"**{_noshell['delta_db']:+.2f} dB** |",
    f"| 프로펠러만 제거 | {_noprop['mean_dbsm']:+.2f} dBsm | {_noprop['delta_db']:+.2f} dB |",
    f"| **금속 코어만** (모터+배터리+PCB+카메라) | {_metal['mean_dbsm']:+.2f} dBsm | "
    f"**{_metal['delta_db']:+.2f} dB** |",
    f"| 유전체만 (금속 하나도 없이) | {_diel['mean_dbsm']:+.2f} dBsm | {_diel['delta_db']:+.2f} dB |",
    "",
    "**세 줄로 요약됩니다.**",
    "",
    f"- **플라스틱 껍데기를 지웠더니 오히려 {_noshell['delta_db']:+.2f} dB 밝아졌습니다.** 셸은 "
    "밝기에 거의 기여하지 않으면서, 뒤에 있는 금속으로 갈 광선을 약하게 가로막던 **가림막**이었기 "
    "때문입니다. (지운다는 건 페인트를 칠하는 게 아니라 그 면을 메쉬에서 **삭제**해 전파가 통과하게 "
    "하는 것입니다.)",
    f"- **금속 코어만 남겨도 {_metal['delta_db']:+.2f} dB** — 통드론과 사실상 같습니다. "
    f"반대로 **금속을 전부 빼면 {_diel['delta_db']:+.2f} dB** 어두워집니다. "
    "**밝기를 만드는 건 속 금속이고, 플라스틱은 조연**입니다.",
    f"- 프로펠러(플라스틱)는 정지 상태에서 **{_noprop['delta_db']:+.2f} dB** — 밝기엔 거의 무의미합니다. "
    "(단, **돌면** 이야기가 완전히 달라집니다 → §5.)",
    "",
    "> ⚠️ **정직한 한계 하나.** 1~3 mm 플라스틱 셸은 1.8~5.2 GHz 에서 실제로는 **반투명**입니다 — "
    "전파가 얼마쯤 통과합니다. 그런데 우리 SBR 은 광선이 **첫 충돌에서 멈추므로** 셸을 뚫지 못합니다. "
    f"그래서 진실은 '통드론(불투명 셸)'과 '셸 제거(투명 셸)' **두 막대 사이 어딘가**에 있습니다. "
    f"그 간격 **{abs(_noshell['delta_db']):.1f} dB** 는 측정오차가 아니라 **모델링 불확실도**로 "
    "읽으십시오.",
    "",
    "> 두 엔진(전파용 Sionna RT · RCS용 SBR)이 **같은 재질표**(`src/materials.py`)를 읽습니다. "
    "오른쪽 표의 반사계수가 그것 — 조용히 어긋날 수 없습니다.",
))

# =========================================================================== #
#  §4  방위 패턴 (증거)
# =========================================================================== #
cells.append(md(
    "## §4. 방위 패턴 — '봉우리'는 인용, '골'은 인용 금지",
    "",
    "![rcs polar](outputs/figures/report2_rcs_polar.png)",
    "",
    "드론을 한 바퀴 돌리면 밝기는 방위에 따라 **꽃잎 모양**으로 오르내립니다. 넓은 금속면이 정면으로 "
    "보이는 방위에서 **봉우리(로브)** 가 서고, 그 사이에서 **골(널)** 로 떨어집니다.",
    "",
    "**검사 방위 네 개는 선행 규약입니다.** 코(0°)·꼬리(180°)·측면(90°/270°) 라는 집합은 우리가 고른 "
    "것이 아니라 Zhang 외(arXiv:2505.20673)가 DJI M350 을 무향실 모노스태틱으로 재고 사각 동체 때문에 "
    "0°·90°·180°·270° 에서 RCS 가 솟는 **four-leaf** 형태를 보고한 그 축입니다(Fig. 7(d)). ⚠ 밴드"
    f"(우리 {DR[_AA]['bands'][_BAND_35]['fc_ghz']:.1f} GHz vs 그들 10–36 GHz)와 앙각 규약(그들 수평면 "
    f"vs 우리 el = {EL:.0f}°)이 달라 **수치 대조가 아니라 검사축 차용**이고, 그들의 four-leaf 는 방위 "
    "**포락선** 모델이라 로브 **개수**로 판정하는 데는 쓸 수 없습니다.",
    "",
    "**봉우리가 어디에 서는지는 기체 대칭성이 정합니다 — 5종 공통이 아닙니다.** 그 네 방향에서 고르게 "
    "서는 것은 직사각 대칭 쿼드"
    f"({DR['phantom4']['name']})뿐입니다: 네 방위 ±15° 구간 평균이 방위평균보다 각각 "
    f"{' / '.join(_m(v, '+.1f') for v in _P4_DEV)} dB 로, 서로 "
    f"{max(_P4_DEV) - min(_P4_DEV):.2f} dB 안에 모입니다. 반면 {DR['mini5pro']['name']}는 코·꼬리가 "
    f"방위평균보다 오히려 {_m(_M5_DEV[0], '+.1f')} / {_m(_M5_DEV[2], '+.1f')} dB **낮고** 측면"
    f"({_m(_M5_DEV[1], '+.1f')} / {_m(_M5_DEV[3], '+.1f')} dB)에서만 섭니다. 접이식 암(Mavic 계열)·8암 "
    "옥토는 네 방향 대칭을 보이지 않습니다 — 3.5 GHz 최강 로브 방위도 기체마다 다릅니다("
    + ", ".join(f"{DR[d]['name']} {_peak_az(d)}°" for d in ORDER) + ").",
    "",
    "**여기서 반드시 지켜야 할 규칙:**",
    "",
    "- **봉우리(로브)는 대역평균(5개 주파수)과 3° 평활을 거친 뒤에는 인용해도 됩니다.** 평활 전 "
    "단일 주파수의 개별각은 격자를 반절해도 평균 ~2 dB 흔들립니다(`report_mesh/outputs/mesh_verify.json` "
    "H·I). 링크버짓의 '최선의 경우'로 쓸 수 있습니다.",
    "- **골(널)은 절대 인용하지 마십시오.** 골의 깊이는 여러 반사가 서로 상쇄돼 생기는 것이라, "
    "격자를 조금만 바꿔도 **10 dB 넘게** 출렁입니다. '이 각도에서 −40 dBsm 으로 안 보인다' 같은 "
    "주장은 하면 안 됩니다.",
    "",
    "> 그래서 이 리포트가 밖으로 내보내는 숫자는 **§2 의 방위평균**과 **로브 높이**뿐입니다. "
    "특정 방위의 널 깊이는 내부 그림에서만 봅니다.",
    "",
    f"> 각 곡선은 361개 방위 × 대역 내 5개 주파수 평균 × 3° 평활입니다(el = {EL:.0f}°). "
    "큰 기체(S1000+)일수록 로브가 잘게 갈라지는 건 전기적 크기(size/λ)가 커서 로브가 촘촘해지기 "
    "때문입니다.",
))

cells.append(md(
    "![.](outputs/renders/anim/rcs_azimuth_matrice4e.gif)",
    "",
    "<sub>Matrice 4E RCS 방위각 폴라 — 각도마다 수 dB~수십 dB 출렁인다(SBR 결과).</sub>",
))

# =========================================================================== #
#  §5  마이크로도플러 (증거)
# =========================================================================== #
_mdrows = []
for d in ORDER:
    v = MD[d]
    _mdrows.append(
        f"| {DR[d]['name']} | {v['n_rotors']} | {ART[d]['hover_rpm']:.0f} | "
        f"{v['flash_hz']:.0f} | ±{v['f_tip_hz']/1e3:.2f} | {v['gain_db']:.0f} |")

# 선행(OpenISAC Fig. 13)의 '능선 간격'과 우리 flash 를 나란히 놓기 위한 환산.
#   flash = 날개수 × 회전율이므로, 비교 전에 날개수로 나눠 로터 회전율 f_rot 로 되돌린다.
#   ⚠ 반증 기록: 예전 원고는 "선행은 능선 간격을 회전수/60 으로 읽으므로 우리와 규약이 2배
#     어긋난다"고 단언했다. 2026-07-30 원문(PDF p.14, Fig. 13 서술) 확인 결과 선행 본문은
#     "The spacing between these ridges reflects the rotor angular velocity" 한 문장뿐이고
#     **식도 등호도 각속도의 단위(rad/s vs 회전/s)도 없다.** 논문 전체에 날개수 언급도 없다.
#     따라서 '선행이 충돌하는 규약을 명시한다'는 주장은 근거가 없어 철회했고, 환산을 밝히는
#     신중함만 남겼다(선행이 식을 주지 않으므로 환산 명시는 우리 몫).
_BLADE_SET = sorted({ART[d]["blades"] for d in ORDER})
_FROT_STR = " · ".join(
    f"{DR[d]['name']} {ART[d]['f_rot_hz']:.0f} Hz" for d in ORDER)

cells.append(md(
    "## §5. 프로펠러 지문 — 마이크로도플러",
    "",
    "지금까지는 드론이 **가만히** 있을 때의 밝기였습니다. 하지만 드론의 프로펠러는 초당 수십 바퀴를 "
    "돕니다. 돌아가는 블레이드는 **정면을 보일 때마다 반사가 번쩍**이고, 날개 끝은 시속 200 km 급으로 "
    "움직여 큰 도플러(주파수 변화)를 만듭니다. 이 미세구조가 드론을 새·잡음과 가르는 **지문**입니다.",
    "",
    "다중 프로펠러 드론의 **바이스태틱 마이크로도플러**를 모델링하는 것은 선행 연구가 이미 측정으로 "
    "검증해 둔 접근입니다 — Costa & Thomä(TU Ilmenau, IEEE J-STEAP 2025, arXiv:2504.05168)는 "
    "프로펠러를 thin-wire 점산란체 + PO 로터 RCS 로 놓고 분산 ISAC OFDM 에서 실측 대조했습니다. "
    "우리는 같은 목표를 **전체 메쉬 SBR** 로 풀어(점산란체 근사 없이 가림까지 포함) 아래 지문을 얻습니다.",
    "",
    "### 5.1 지문의 두 눈금은 호버 회전수에서 나온다",
    "",
    "![hover rpm](outputs/figures/report1_hover_rpm.png)",
    "",
    "지문에는 두 개의 눈금이 있습니다.",
    "",
    "- **flash rate(번쩍임 주기)** = 날개수 × 회전수/60. 2엽 프로펠러는 한 바퀴에 정면을 **두 번** "
    "보이므로 flash = 회전수/30. → 프로펠러가 **크고 느린** 기체는 드물게, **작고 빠른** 기체는 "
    f"자주 번쩍입니다. ⚠ **선행 수치와 나란히 놓으려면 눈금을 먼저 되돌려야 합니다.** "
    f"OpenISAC(arXiv:2601.03535)은 스펙트로그램의 등간격 능선 간격이 **로터 각속도를 반영한다**고 "
    f"서술할 뿐(Fig. 13), **식도 등호도 각속도의 단위(rad/s 인지 회전/s 인지)도 밝히지 않습니다.** "
    f"그러므로 선행이 우리와 다른 규약을 명시했다고 말할 수는 없고, 두 수를 비교 가능하게 만드는 "
    f"**환산을 명시하는 일이 우리 몫**입니다. 우리 flash 는 회전율에 날개수를 곱한 값이므로, 능선 "
    f"간격에 대기 전에 **날개수로 나눠 로터 회전율로 되돌립니다** — 5종 모두 "
    f"{'/'.join(str(b) for b in _BLADE_SET)}엽이라 f_rot = flash/"
    f"{'/'.join(str(b) for b in _BLADE_SET)} 이고, 값은 {_FROT_STR} 입니다. 이 환산 없이 flash 를 "
    f"그대로 능선 간격에 대면 날개수만큼 어긋난 양을 비교하게 됩니다.",
    "- **f_tip(날개끝 도플러 폭)** = 2·v_tip/λ·cos(el). 날개 끝 속도 v_tip = ω·R 가 만드는 "
    "**최대** 도플러입니다. 모델 안에서 이보다 빨리 움직이는 산란체는 없으므로, 진짜 마이크로도플러는 "
    "**±f_tip 안에** 갇힙니다.",
    "",
    "둘 다 **호버 회전수**만 알면 정해집니다. 회전수는 텔레메트리가 없으니 **물리로 유도**합니다 — "
    "호버란 4(또는 8)개 로터의 추력이 정확히 무게를 받치는 상태이고, 추력은 T = C_T ρ n² D⁴ "
    "(C_T ≈ 0.10~0.12) 로 회전수 n 과 이어집니다. 무게와 프로펠러 지름 D 를 넣어 n 을 풀면 "
    "**아래 표의 호버 rpm**이 나옵니다(가정값이지만 물리 범위 안입니다).",
    "",
    f"**5종의 프로펠러 지문** ({MDCFG['fc']/1e9:.1f} GHz, el = {MDCFG['el']:.0f}°):",
    "",
    "| 드론 | 로터 수 | 호버 rpm | flash [Hz] | f_tip [kHz] | 가림 이득 [dB] |",
    "|---|---|---|---|---|---|",
    *_mdrows,
    "",
    f"→ **flash rate 는 프로펠러 크기·회전수를 그대로 반영합니다.** 큰 프로펠러(S1000+ 15인치)는 느리게 "
    f"돌아 {MD['s1000plus']['flash_hz']:.0f} Hz, 작은 프로펠러(Mini 5 Pro 6인치)는 빠르게 돌아 "
    f"{MD['mini5pro']['flash_hz']:.0f} Hz 로 번쩍입니다.",
    "",
    f"> ⚠ **그러나 flash 하나로는 기체가 갈리지 않습니다.** 위 표의 5종이 내는 flash 는 "
    f"**{len(_FLASH_G)}개 값뿐**이고 "
    + " · ".join("**" + " = ".join(v) + "**" for v in _FLASH_TIE)
    + f" 가 각각 같은 값에서 겹칩니다. flash = 날개수 × rpm/60 이라 로터 수·프로펠러 지름이 달라도 "
      f"호버 rpm 이 같으면 같은 값이 나오기 때문입니다. 겹친 짝은 f_tip 이 갈라 줍니다"
      f"(예: {DR['mavic4pro']['name']} ±{MD['mavic4pro']['f_tip_hz']/1e3:.2f} kHz vs "
      f"{DR['s1000plus']['name']} ±{MD['s1000plus']['f_tip_hz']/1e3:.2f} kHz) — 즉 지문은 "
      f"**(flash, f_tip) 한 쌍**이지 flash 단독이 아니고, 두 눈금 모두 호버 rpm 가정에 비례합니다.",
    "",
    "### 5.2 지문을 보려면 '가림'이 필수다",
    "",
    "![microdoppler](outputs/figures/report1_microdoppler.png)",
    "",
    "위 그림의 각 판은 시간(가로) × 도플러(세로)로 그린 **슬로타임 반사장**입니다. 프레임마다 "
    "블레이드 자세를 다시 놓고 SBR 로 산란장을 새로 계산합니다 — 세로 줄무늬가 바로 블레이드 번쩍임, "
    "파란 점선이 ±f_tip 경계입니다.",
    "",
    "**판독 규약은 선행을 그대로 씁니다.** OpenISAC(arXiv:2601.03535)은 스펙트로그램을 "
    "$|\\mathrm{STFT}|^2$ 로 정의하고(식 (24)), **0-도플러 = 준정적 동체 산란**, **대칭·등간격 능선 = "
    "회전 블레이드**, **능선 간격 ↔ 로터 각속도를 반영**, **전체 도플러 폭 = 날개끝 최대 시선속도**로 "
    "읽습니다. 우리 판의 dB 눈금은 $20\\log_{10}|\\mathrm{STFT}|$ 라 $|\\mathrm{STFT}|^2$ 의 dB 와 같은 "
    "축이고, 파란 점선 ±f_tip 이 바로 그 '전체 도플러 폭' 경계입니다. ⚠ 두 군데는 우리가 따로 밝혀 "
    "둡니다 — (i) **능선 간격**은 선행이 식으로 못 박지 않았으므로, 우리 flash 와 견주려면 날개수로 "
    "나눠 로터 회전율로 되돌리는 **환산이 필요하고 그 환산은 우리 규약**입니다(§5.1), "
    "(ii) OpenISAC 은 STFT 앞에 **MTI(0-도플러 노치)** 를 겁니다. 위 스펙트로그램 판도 DC 를 빼고 "
    "그리므로(`src/microdoppler.py:103-104`, `remove_dc` 기본 True) 그림끼리는 같은 규약이지만, "
    "**오른쪽 아래 막대의 |DC|/std(AC) 는 노치 전 원신호에서 잰 값**이라 그들의 0-도플러 잔차와 같은 "
    "양이 아닙니다.",
    "",
    "여기서 **가림이 왜 필수인지**가 오른쪽 아래 막대에 있습니다. 블레이드가 몸통 뒤로 돌아가면 "
    "**안 보여야** 하는데, 가림을 안 하는 순수 PO 는 **몸통에 가려 안 보이는 날개까지 다 세어** 0 Hz "
    "근처의 **정지 몸통 신호(pedestal)를 부풀립니다.** 그 부풀림이 드론마다 "
    f"**{_gmin:.0f}~{_gmax:.0f} dB** — 그만큼 블레이드 깜빡임이 몸통 신호 아래 묻힙니다.",
    "",
    "SBR 은 광선이 **첫 충돌에서 멈춰** 가림이 공짜라, 부풀린 pedestal 을 걷어내고 "
    "**깜빡임을 몸통 위로 되살립니다.** 그래서 §3 에서 '정지 상태 프로펠러는 밝기에 무의미'했지만, "
    "**돌면** 프로펠러가 지문의 주역이 됩니다 — 정지 밝기가 아니라 **시간에 따른 변조**가 정보이기 "
    "때문입니다.",
    "",
    "> ⚠ **범위 주의.** 이 pedestal 비교는 **가림(몸통 뒤 숨은 블레이드)만** 격리하려 first-hit "
    "SBR(투과 미적용)을 쓴다. **셸 속 내부 금속**(배터리·PCB)은 실재하는 정적 산란체라 pedestal 에 "
    "정당히 들어가야 하며, 헤드라인 σ 엔진은 그걸 **셸 투과로 되살린다**(§3) — 즉 '내부 금속을 걷어내는 "
    "것'은 가림의 역할이 아니다. (sbr_field·다중반사 경로의 투과 일관화는 후속 과제.)",
    "",
    "> ⚠ **선행 실측과의 방향 — 아직 확정 아님(정직하게).** 이 분야 **유일한 바이스태틱 마이크로도플러 "
    "실측**(Costa·Thomä, TU Ilmenau, RadarConf24)은 스펙트럼에서 **DC(정지 몸통)가 블레이드 선보다 "
    f"≈{PRIOR_MDPROPS_DCBLADE_DB:.0f} dB 우세**하다고 판독된다 — 즉 정지 몸통이 매우 지배적이다. 우리 "
    f"JSON 의 DC↔AC 비(|DC|/std(AC))는 **SBR {min(_SBR_RATIO):+.1f}~{max(_SBR_RATIO):+.1f} dB** 인 반면 "
    f"가림을 안 한 **PO 는 {min(_PO_RATIO):+.1f}~{max(_PO_RATIO):+.1f} dB** 로, **PO 쪽이 그 실측(강한 "
    "몸통 우세)에 더 가깝다.** 즉 SBR 가림이 pedestal 을 낮춰 깜빡임을 살리는 방향은 **이 한 실측에서는 "
    "멀어지는 방향**이다. 다만 (ⓐ 정의가 다르고 — 우리 값은 시간영역, 실측은 스펙트럼 선 피크, 선-피크 "
    "재계산은 다음 단계, ⓑ 실측은 4개 중 1개 로터만 회전·탄소 골격·β=60°·편파 미기재) **방향은 보이나 "
    "확정은 아니다.** 가림 자체의 기하 타당성(몸통 뒤 블레이드는 안 보인다)은 그대로 유지하되, "
    "'PO 과대·SBR 교정' 이라는 **절대 세기 판정은 유보**한다.",
    "",
    "> **직관 하나.** 선풍기 날개에 손전등을 비추면, 날개가 정면을 보이는 순간마다 규칙적으로 "
    "반짝입니다. 그런데 날개가 **선풍기 몸통 뒤로** 넘어가는 동안은 안 보이죠(가림). 이 '보였다 안 "
    "보였다'가 규칙적 반짝임을 만듭니다. 몸통 뒤 날개까지 억지로 세면(가림 무시) 밋밋한 몸통 밝기만 "
    "커져서 정작 반짝임이 안 보입니다.",
    "",
    "> ⚠️ 호버 rpm 은 추력 균형에서 유도한 **가정값**입니다. flash·f_tip 은 rpm 에 비례하므로, 실제 "
    "비행 회전수가 다르면 지문 주파수도 그만큼 이동합니다. 지문의 **구조**(깜빡임·±f_tip 경계·기체별 "
    "순서)는 믿을 만하나 절대 주파수는 rpm 가정에 달려 있습니다.",
))

# =========================================================================== #
#  재현 코드
# =========================================================================== #
cells.append(code(
    "# §2 재현 — 한 드론의 밝기를 한 대역에서 직접 재본다 (SBR)",
    "import numpy as np",
    "from rcs_po import drone_rcs_pattern_bw, dbsm      # 기본 엔진은 'sbr'",
    "",
    "az = np.arange(0, 361, 2.0)",
    "sig, n_rays = drone_rcs_pattern_bw('s1000plus', 5.21e9, 80e6, az, el_deg=15.0, n_f=5)",
    "print(f'방위당 광선 {n_rays:,}발  (격자 lambda/16)')",
    "print(f'S1000+ @ 5.2 GHz  방위평균 {dbsm(np.mean(sig)):+.2f} dBsm  '",
    "      f'(로브 최대 {dbsm(np.max(sig)):+.2f} dBsm)')",
))

cells.append(code(
    "# §5 재현 — 호버 rpm 유도 + 블레이드 지문의 두 눈금",
    "#   flash = blades * rpm/60,   f_tip = 2*v_tip/lambda * cos(el)",
    "import numpy as np",
    "",
    "specs = dict(mini5pro=(0.2499,0.1524,4), mavic4pro=(1.063,0.267,4),",
    "             matrice4e=(1.219,0.274,4), s1000plus=(9.5,0.381,8),",
    "             phantom4=(1.38,0.240,4))       # (질량 kg, 프로펠러 지름 m, 로터 수)",
    "rho, CT, blades = 1.225, 0.11, 2",
    "lam, el = 3e8/3.5e9, np.deg2rad(15.0)",
    "for d,(m,D,nr) in specs.items():",
    "    T = m*9.81/nr                                  # 로터당 추력 = 무게/로터수",
    "    n = np.sqrt(T/(CT*rho*D**4))                   # T = CT rho n^2 D^4  ->  n [rev/s]",
    "    rpm = n*60",
    "    flash = blades*rpm/60",
    "    v_tip = (2*np.pi*n)*(D/2)",
    "    f_tip = 2*v_tip/lam*np.cos(el)",
    "    print(f'{d:10s} rpm~{rpm:5.0f}  flash {flash:5.1f} Hz  f_tip +-{f_tip/1e3:4.2f} kHz')",
    "# ↑ 같은 물리(T=CT·rho·n^2·D^4)에서 나온다. 단 report1.json 은 로터별로 CT 를 세밀 보정하므로,",
    "#   이 고정 CT=0.11 스니펫은 자릿수 수준의 예시일 뿐 §5.1 표값과 정확히 일치하지는 않는다.",
))

# =========================================================================== #
#  §6  선행 연구의 방식과 실측 대조 — 절대값 검증
# =========================================================================== #
cells.append(md(
    "---",
    "## §6. 선행 연구의 방식과 실측 대조 — 절대값 검증",
    "",
    "기준해(평판·구, report07)는 SBR+PO 라는 **방법**이 옳음을 보이지만 드론의 **절대 σ** 는 보장하지 "
    "못한다. 절대 스케일의 기준은 선행 연구가 남긴 **실측 문헌 드론 RCS** 다.",
    "",
    "ISAC 문헌에서 표적 밝기는 세 갈래로 처리된다 — **(b) 확산계수 S 가정**(Great-X arXiv:2507.08716 · "
    "Deterministic-Modeling arXiv:2603.28736, EuCAP 2026), **(c) RCS 상수 주입**(3GPP · 오픈 MATLAB "
    "arXiv:2606.07328), **(d) 자작 SBR+PO / 산란 add-on**(Sionna-RT 확장 계열). 우리는 **(d)** 를 택했다 — "
    "소형 드론은 확산 S 실측 보정 데이터가 없고 부위별 재질 차이가 RCS 를 지배하기 때문이다.",
    "",
    "⚠ **이 계열의 대표 선행은 우리 방법을 명시적으로 비판한다.** Ziganshin(arXiv:2604.05991)은 서론에서 "
    "SBR+PO 를 자기 방법의 **대척점**으로 놓는다 — *\"This SBR+PO approach, however, is limited to the "
    "illuminated region and is not suitable to predict the scattered field in the shadow region of the "
    "obstacle. Furthermore, the need to cascade PO after RT negates the computational advantages of RT.\"* "
    "그들은 Sionna-RT 솔버 자체를 UTD+정점회절로 확장해 **PEC 차량·구(2–10 GHz, facet E>1.5λ)** 를 "
    "다루고, 우리는 그 솔버가 쓰는 Mitsuba 광선엔진 위에 PO 를 얹어 **few-λ 부위별 유전체 소형 드론**을 "
    "다룬다 — UTD 유효조건(E>1.5λ)이 성립하지 않는 영역이라 방법 선택이 갈린다. 그리고 그들이 지적한 "
    "**그늘영역·상반성 한계는 우리도 이미 자발적으로 공개한다**: report07 §5 는 이 리포트의 σ 가 "
    "*전방산란(β→180°)에서 σ≡0, 깊은 널에서 상반성 σ(û_i,û_s)=σ(û_s,û_i) 붕괴* 하는 **모노스태틱 "
    "등가값**임을 명시한다(물리적 인식은 있고, 필요한 것은 인용 프레이밍이다). 상용 CADFEKO"
    "(LAMBDA arXiv:2607.03826)·비공개 RadarSimPy·독립엔진 BVH SBR+PO(arXiv:2604.09243) 대신 "
    "**선행이 실제로 쓰는 자작 SBR+PO** 를 따랐고, 검증은 라이브러리 대조가 아니라 아래 **실측 문헌 "
    "앵커**로 세운다(근거: `prior_work/pw01`).",
    "",
    "우리가 쓰는 신형(Mavic 4 Pro·Matrice 4E)의 실측 RCS 는 아직 논문에 없습니다(2024~25 출시). 절대 "
    "판정의 **1급 근거는 우리 세 밴드를 전부 커버하는 Phantom 3 실측**이다(아래 첫 표). 밴드나 지표가 "
    "어긋나는 나머지 실측(Li & Ling·Ezuma·Semkin·Quevedo)은 **방향성 참고**로만 쓴다.",
    "",
    "#### 1급 절대앵커 — DJI Phantom 3, 우리 세 밴드를 전부 커버",
    "",
    "우리 phantom4 는 Phantom 3 와 **대각이 정확히 같은 350 mm DJI 쿼드**다. Phantom 3 는 두 편이 "
    "**같은 측정 캠페인**(Wei Fan/Southeast Univ. 데이터)을 서로 다른 평균 규약으로 요약해, 우리 세 "
    "밴드(1.8/3.5/5.2 GHz)를 모두 덮는 유일한 실측 앵커다:",
    "",
    "| 앵커 (Phantom 3, 350 mm) | 평균 규약 | @1.8 | @3.5 | @5.2 GHz | 출처 |",
    "|---|---|---|---|---|---|",
    f"| multiband (Das 2026) | **선형** ★우리와 동일 | {_m(_MB_MEAN['LTE 1.8 GHz'])} | "
    f"{_m(_MB_MEAN['5G NR 3.5 GHz'])} | {_m(_MB_MEAN['WiFi 5.2 GHz'])} | {PRIOR_MB_P3['cite']} |",
    f"| mono3d (Yuan 2025, 같은 캠페인) | dB영역 | {_m(_M3D_MEAN['LTE 1.8 GHz'])} | "
    f"{_m(_M3D_MEAN['5G NR 3.5 GHz'])} | {_m(_M3D_MEAN['WiFi 5.2 GHz'])} | {PRIOR_M3D_P3['cite']} |",
    f"| **우리 phantom4** (방위 선형평균) | 선형 | {_m(_AA_DB['LTE 1.8 GHz'])} | "
    f"{_m(_AA_DB['5G NR 3.5 GHz'])} | {_m(_AA_DB['WiFi 5.2 GHz'])} | JSON |",
    f"| **Δ (우리 − multiband, 선형↔선형)** | 사과-대-사과 | **{_m(_AA_DMB['LTE 1.8 GHz'])}** | "
    f"**{_m(_AA_DMB['5G NR 3.5 GHz'])}** | **{_m(_AA_DMB['WiFi 5.2 GHz'])}** | Δ [dB] |",
    f"| Δ (우리 − mono3d, 선형↔dB영역) | 규약 미정렬 | {_m(_AA_DM3D['LTE 1.8 GHz'])} | "
    f"{_m(_AA_DM3D['5G NR 3.5 GHz'])} | {_m(_AA_DM3D['WiFi 5.2 GHz'])} | Δ [dB] |",
    "",
    "<sub>**판정 (P0 — 평균 규약 열).** 평균 규약까지 맞춘 **multiband 행이 유일한 사과-대-사과**다 — 우리 "
    "`mean_dbsm` 은 방위 **선형평균**(10log₁₀(mean σ), `viz_report2.py:841`)이고 multiband §III-1 도 "
    f"선형평균이다. 그 앵커와 우리 350 mm 기체는 3.5/5.2 GHz 에서 {abs(_AA_DMB['5G NR 3.5 GHz']):.1f}/"
    f"{abs(_AA_DMB['WiFi 5.2 GHz']):.1f} dB, 1.8 GHz 에서 {abs(_AA_DMB['LTE 1.8 GHz']):.1f} dB 안에서 "
    "맞는다(우리가 약간 어두운 쪽). **mono3d 는 같은 측정**을 dB영역 평균으로 요약해 "
    f"{_CONV_SPREAD['5G NR 3.5 GHz']:.1f} dB 위로 나오는데, 이는 로그정규에서 (선형평균 − dB영역평균) = "
    "(ln10/20)·ε² 로 설명되는 **순수 규약 차**다(ε≈5.2 dB → ≈3.2 dB, 노트 §2-2, PDF 확인). 즉 이 "
    f"{_CONV_SPREAD['5G NR 3.5 GHz']:.1f} dB 가 **절대판정의 하한 불확도**이며, 규약을 안 밝힌 두 요약을 "
    "그냥 병치하면 우리가 3.4 dB 만큼 자의로 밝거나 어두워 보인다. ⚠ 아직 정렬 안 된 축: 앙각(우리 "
    f"el={EL:.0f}° ↔ 문헌 el=0° 수평면)·편파(스칼라 Γ ↔ co-pol). **{_EL0_PHRASE}.**</sub>",
    "",
    "이 1급 앵커와 견주면 우리 절대 레벨은 **수 dB 안**이다. 그런데 아래 방향성 참고표의 Li & Ling "
    f"**aspect-peak**({_m(_LILING_PEAK35, '+.1f')} dBsm)는 위 두 실험실의 **방위 mean**("
    f"{_m(_MB_MEAN[_BAND_35], '+.1f')} / {_m(_M3D_MEAN[_BAND_35], '+.1f')})보다도 "
    f"{_MB_MEAN[_BAND_35]-_LILING_PEAK35:.0f}~{_ANCHOR_SPREAD:.0f} dB **아래**다 — peak 가 다른 실험실 "
    "mean 보다 낮을 수는 없다(자세-peak ≥ 방위-mean). 즉 **문헌 절대앵커끼리가 이미 물리적으로 불가능한 "
    f"방향으로 {_ANCHOR_SPREAD:.0f} dB 넘게 어긋나 있고**, 이 산포가 우리 오차보다 크다. 그래서 **절대 "
    "dBsm 판정은 보류**하고, 아래 표는 방향성 참고로만 읽는다:",
    "",
    "| 문헌 (실측) | 밴드 | 측정 RCS | 우리와의 관계 |",
    "|---|---|---|---|",
    "| **Li & Ling 2017** (IEEE AWPL, ~99인용) · 등급 **[N]**(PDF 부재) | **3–6 GHz** ★밴드일치 | "
    f"Phantom 2(350 mm) **{_m(PRIOR_LILING['DJI Phantom 2'][1], '+.1f')}**, "
    f"3DR Solo(460) {_m(PRIOR_LILING['3DR Solo'][1], '+.1f')}, "
    f"Inspire 1(560) {_m(PRIOR_LILING['DJI Inspire 1'][1], '+.1f')} dBsm "
    "(모두 **aspect-peak**, 자세 스프레드 ~14 dB) | 지표는 우리 peak 와 맞지만(peak↔peak, 대각 짝) "
    f"**절대 판정엔 못 쓴다** — 이 peak(−27.5)가 위 1급 앵커의 mean 보다 {_ANCHOR_SPREAD:.0f} dB 아래라 "
    "(peak<mean, 물리 불가) 절대교정이 낮다. peak↔peak 로 재면 우리가 "
    f"**+{_PAIR_LO:.1f}~+{_PAIR_HI:.1f} dB**(대각비 ±{_PAIR_TOL*100:.0f}% 짝, 최정합 350 mm 짝 "
    f"{_PAIR[_TIGHT][3]:+.1f} dB)로 나오지만 이는 **Li & Ling 의 낮은 교정 탓**이지 우리가 밝다는 증거가 "
    "아니다(같은 기체 mean 은 1급 앵커와 −0.4 dB 로 맞는다). 짝짓기 원장은 아래 |",
    "| Ezuma 2019 (compact-range) · 등급 **[N]** | 15 / 25 GHz | Phantom 4 Pro −15.0 / −12.4 dBsm | "
    "밴드갭이 커서 **절대값 대조는 하지 않는다**. **기울기 대조도 하지 않는다** — 우리 1.8~5.2 GHz 는 "
    f"3점뿐이라 회귀가 구속되지 않는다(R² {min(_R2.values()):.2f}~{max(_R2.values()):.2f}, "
    f"mavic4pro {_R2['mavic4pro']:.2f}). 인용하는 것은 §2 의 **밴드 스윙**({_band_swing:.1f} dB)뿐 |",
    "| Semkin 2020 (IEEE Access) · 등급 **[N]** | 26–40 GHz | Mavic Pro(335 mm 플라스틱) −16.8, "
    "Phantom 4 Pro −16.4, Matrice 100(650 mm 카본) −10.5 dBsm | **규약만 차용**(재질·로터 정지·편파 HH 를 "
    "명기하는 보고 방식). **재질 이득 수치는 인용하지 않는다** — M100 은 카본인 동시에 거의 2배 크고, "
    f"광학영역 면적 스케일링만으로 20·log₁₀(650/335) = **{_SEMKIN_SIZE_DB:+.1f} dB** 라 두 기체 차이의 "
    "대부분이 크기 효과다 |",
    "| Quevedo 2019 (IET RSN) · 등급 **[N]** | X-band 8.75 GHz | Phantom 4 −20~−4.6 dBsm(프롭 회전 의존) | "
    "범위가 15 dB 폭이라 **정량 대조에는 쓰지 않는다**. 차용하는 것은 방향성뿐 — 프로펠러 회전이 σ 를 "
    "크게 흔든다(우리 마이크로도플러 서사) |",
    "",
    "**짝짓기 원장** (Li & Ling peak↔peak — 방향성 참고) — 위 peak↔peak 범위가 어느 짝에서 나왔는지, "
    "그리고 크기 불일치를 이 절이 Semkin 행에서 쓰는 것과 **같은 면적 스케일링**으로 뺐을 때 무엇이 "
    "남는지 그대로 편다. ⚠ 이 표는 **Li & Ling 절대교정이 위 1급 앵커보다 낮다**는 전제 위에 있어 "
    "절대 판정이 아니라 **크기-순서 재현 확인용**이다:",
    "",
    "| 우리 기체 | 대각 (mm) | 짝 (Li & Ling) | 대각 (mm) | 대각비 | Δpeak | 크기보정 20log₁₀(비) | 보정 후 |",
    "|---|---|---|---|---|---|---|---|",
    *[f"| {DR[d]['name']}{'' if d in _PAIR_OK else ' ⚠'} | {DR[d]['diagonal_mm']:.0f} | {_PAIR[d][0]} | "
      f"{_PAIR[d][1]:.0f} | ×{_pair_ratio(d):.2f} | **{_PAIR[d][3]:+.2f} dB** | "
      f"{_m(_pair_sizecorr_db(d), '+.2f')} dB | {_PAIR_ADJ[d]:+.2f} dB |" for d in ORDER],
    "",
    f"<sub>⚠ 표시한 {len(_PAIR_LOOSE)}행은 **짝이 아니다** — 문헌의 최대 기체가 "
    f"{max(v[0] for v in PRIOR_LILING.values()):.0f} mm 라 그보다 크거나 훨씬 작은 우리 기체에는 대응 "
    f"실측이 없다(대각비 "
    f"{_loose_txt}). "
    f"그래서 peak↔peak 범위 +{_PAIR_LO:.1f}~+{_PAIR_HI:.1f} dB 는 대각비 ±{_PAIR_TOL*100:.0f}% 안인 "
    f"{len(_PAIR_OK)}행에서만 잡았다. 이 표가 말하는 것은 <b>크기 순서가 재현된다</b>는 것뿐이다 — 벗어난 "
    f"행까지 면적 스케일링으로 보정해도 부호가 유지된다(최솟값 {_PAIR_ADJ_LO:+.1f} dB). "
    "(광학영역 σ∝면적 가정을 few-λ 영역에 그대로 적용한 거친 보정이라 <b>보정값 자체는 인용하지 않고</b> "
    "부호 확인용으로만 쓴다.)</sub>",
    "",
    "<sub>**정리 — 절대 σ 는 판정 보류, 상대 결론만.** (1) 밴드·지표·기하·**평균규약**을 모두 맞춘 유일한 "
    "사과-대-사과는 위 **1급 앵커(multiband Phantom 3, 방위 선형평균)**다. 그와 우리 350 mm 정합기는 "
    f"3.5/5.2 GHz 에서 {abs(_AA_DMB['5G NR 3.5 GHz']):.1f}/{abs(_AA_DMB['WiFi 5.2 GHz']):.1f} dB, 1.8 GHz "
    f"에서 {abs(_AA_DMB['LTE 1.8 GHz']):.1f} dB **안**에서 맞는다. Li & Ling peak↔peak 로는 "
    f"+{_PAIR_LO:.1f}~+{_PAIR_HI:.1f} dB '위'로 나오지만 그 앵커의 절대교정이 1급 앵커 mean 보다 "
    f"{_ANCHOR_SPREAD:.0f} dB 낮다(peak<mean, 물리 불가)는 것이 확인되므로 **절대 밝기 증거가 아니다**. "
    "(2) **낮은 밴드에서 우리가 오히려 어둡다는 신호도 있다** — 우리 1.8 GHz 는 1급 앵커보다 "
    f"{abs(_AA_DMB['LTE 1.8 GHz']):.1f} dB 어둡고, 같은 측정을 두 논문이 요약한 값이 "
    f"{_CONV_SPREAD['5G NR 3.5 GHz']:.1f} dB(순수 평균규약 차) 벌어진다. Li & Ling 12–15 GHz 하강분으로 "
    f"외삽하면 3.5 GHz 진값이 −25~−28 dBsm 쪽이어야 한다는 논리도 있으나, 이는 **1급 앵커의 직접 실측"
    f"(3.5 GHz {_m(_MB_MEAN['5G NR 3.5 GHz'])}) 과 정면충돌**한다(우리 mavic4pro {_m(_AZAVG_35)} dBsm 과 "
    "거의 같다) — 즉 그 외삽은 신뢰할 수 없고, 절대오차의 **방향은 단정할 수 없다**. 이 모든 어긋남이 "
    "**앵커 산포 > 우리 오차** 라는 한 사실을 가리킨다. (3) ⚠ **아직 정렬되지 않은 축.** 앙각 — 우리는 "
    f"el = {EL:.0f}°, **문헌은 전부 수평면(el=0°)**(mono3d θ={{90,0,180}}°·unified-rcs 'elevation fixed "
    f"at 90°'·multiband 수평 원호) → **미정렬**이며, {_EL0_PHRASE}. 편파 — "
    "우리 SBR 은 스칼라 Γ 라 co-pol/cross-pol 을 분리하지 않고(`src/rcs_sbr.py`) 문헌은 co-pol 측정이다. "
    "지표 — 우리 peak 는 방위 361점·대역 내 5주파수 평균의 **평활 전** 최대다. 출처 등급 — Li & Ling·"
    "Ezuma·Semkin·Quevedo 는 전부 **[N]**(워크스페이스 노트 근거, PDF 부재)이라 절대 판정에 못 쓰고, "
    "1급 앵커 multiband·mono3d 만 **PDF 확인**이다. (4) 그래서 절대 dBsm 은 판정을 **보류**하고, 검출은 "
    "**σ 밴드**로 제시해 상대 결론(모드·파형 비교)이 밴드 전체에서 흔들리지 않음을 보인다. 서지 노트: "
    "`refs/drone_papers/` · 1급 앵커 PDF: `paper_sionna_Ray/`.</sub>",
    "",
    "### 절대값 앵커 — 실측 문헌 RCS 와 교차검증",
    "",
    "밴드가 더 가까운 실측(2.4~4.5 GHz)과도 자릿수를 맞춰 본다. 값 출처는 `prior_work` 파일럿 조사이고, "
    "**등급을 행마다 표기**한다 — [N]은 워크스페이스 노트 근거, [W]는 웹 메타데이터 근거(원문 미확인)다:",
    "",
    "| 실측 (동종 드론) | 밴드 | 측정 RCS | 출처 · 등급 |",
    "|---|---|---|---|",
    f"| DJI Mavic Pro | **2.4 GHz** ★밴드·기체급 근접 | "
    f"**≈ {_m(PRIOR_GUVENC_MAVICPRO_24G_DBSM, '+.1f')} dBsm** "
    "(0.03 m²) | Güvenç/NCSU 서베이(arXiv:2402.05909) · [W] |",
    "| DJI Mavic Pro | 15 / 25 GHz | −17.1 / −16.2 dBsm | Ezuma/Güvenç(arXiv:1911.05926) · [N] |",
    "| DJI Phantom 4 Pro | 15 / 25 GHz | −15.0 / −12.4 dBsm | 〃 |",
    "| 소형기(바이스태틱, 무향실) | 2.75 / 4.51 GHz | −9.8→−5.3 / −7.8→−5.0 dBsm | Frankford/Björklund(IET RSN) · **[W] 원문 미확보(paywall)** |",
    "",
    "<sub>**교차검증 판정 — 행마다 자격이 다르다.** (1) **Mavic Pro @2.4 GHz** 행은 소형 쿼드·sub-6 이라 "
    "크기·밴드 어느 쪽으로도 실격 사유가 없다. 우리 mavic4pro 3.5 GHz 는 방위평균 "
    f"{_m(_AZAVG_35)} / 봉우리 {_m(_PEAK)} dBsm 이므로 문헌값 "
    f"{_m(PRIOR_GUVENC_MAVICPRO_24G_DBSM, '+.1f')} dBsm 은 우리 방위평균보다 "
    f"{_m(PRIOR_GUVENC_MAVICPRO_24G_DBSM - _AZAVG_35, '+.1f')} dB, 우리 봉우리보다 "
    f"{_m(PRIOR_GUVENC_MAVICPRO_24G_DBSM - _PEAK, '+.1f')} dB 다. ⚠ 단 그 서베이 값의 "
    "**지표 정의(peak/mean)가 미상**이고 기체 세대가 달라, 부등호를 세우지 않고 **자릿수 sanity check** 로만 "
    "쓴다. (2) **소형기 바이스태틱** 행은 원문이 paywall 이라 기종·자세·편파·지표를 확인하지 못했다 — "
    "방향성 참고로만 쓴다. (3) **15 / 25 GHz** 두 행은 밴드갭이 커서 절대값 대조에 쓰지 않는다. "
    "⚠ 공통 한계: 우리 SBR 은 스칼라 Γ 라 **편파를 분리하지 않고**(`src/rcs_sbr.py`) 문헌은 co-pol 측정이며, "
    "앙각·자세 규약도 다르다. 즉 이 표는 자릿수 확인이지 점일치 검증이 아니고, **절대 레벨의 사과-대-사과 "
    "근거는 밴드·지표·기하·평균규약이 모두 정렬된 위 1급 앵커(multiband Phantom 3)뿐**이다. 그 대조가 "
    f"말하는 것은 **크기 순서·자릿수·대역 추세는 재현되고 절대 레벨은 그 앵커와 수 dB 안에서 맞지만, 문헌 "
    f"앵커 자체의 산포({_ANCHOR_SPREAD:.0f} dB↑)가 우리 오차보다 커 절대 dBsm 판정은 보류**한다는 것이다.</sub>",
))

# §6.1 — 선행 방법론(회귀·분포·금속구·el컷·분위점) 정량 대조 (outputs/rcs_anchor.json).
#         앵커 JSON 없으면 _anchor_cells()가 [] 를 반환해 리포트는 그대로 빌드된다(graceful).
cells += _anchor_cells()

# =========================================================================== #
#  정리 + 다음 리포트
# =========================================================================== #
cells.append(md(
    "---",
    "## 정리",
    "",
    f"1. **밝기는 크기가 정한다.** 가장 큰 기체가 가장 작은 기체보다 **{_span:.1f} dB** 밝고, "
    f"대역(주파수)은 같은 드론을 **{_band_swing:.1f} dB** 밖에 못 움직인다(광학영역). 그리고 그 "
    "밝기는 플라스틱 껍데기가 아니라 **속 금속**(모터·배터리·PCB)에서 나온다 — 껍데기는 반투명 "
    "스크린일 뿐이다(§2·§3).",
    f"2. **프로펠러는 지문을 남긴다.** 돌면 "
    f"**{MD['s1000plus']['flash_hz']:.0f}~{MD['mini5pro']['flash_hz']:.0f} Hz** 의 규칙적 깜빡임과 "
    f"**±{MD['mini5pro']['f_tip_hz']/1e3:.1f}~{MD['s1000plus']['f_tip_hz']/1e3:.1f} kHz** 의 날개끝 "
    f"도플러가 생긴다. 이 지문을 보려면 **가림**이 필수다 — 몸통 뒤 숨은 날개를 세지 않아야 정지 몸통 "
    f"신호가 부풀지 않고(순수 PO 는 **{_gmin:.0f}~{_gmax:.0f} dB** 부풀린다), 깜빡임이 그 위로 "
    "드러난다(§3·§5).",
    f"3. **절대값은 판정 보류, 상대 결론만.** 스톡 Sionna 는 표적 σ 를 못 주므로(→report06) 자작 SBR+PO 로 "
    "계산했고(→report07), 그 절대값을 우리 세 밴드를 전부 커버하는 **1급 실측 앵커**(multiband Phantom 3, "
    "방위 **선형평균** — 우리 규약과 동일)와 대각 350 mm 정합기로 견주면 "
    f"**{min(abs(v) for v in _AA_DMB.values()):.1f}~{max(abs(v) for v in _AA_DMB.values()):.1f} dB 안**에서 "
    f"맞는다. 다만 문헌 절대앵커 자체가 **{_ANCHOR_SPREAD:.0f} dB 넘게 산포**하고(Li & Ling aspect-peak 이 "
    "다른 실험실 방위-mean 보다도 아래, 물리적으로 불가능) 그 산포가 우리 오차보다 커, **절대 dBsm 은 "
    "판정을 보류**한다. 크기 순서·자릿수·대역 추세는 재현되므로 검출은 σ 밴드로 제시해 상대 결론의 robust "
    "함을 보인다(§6).",
    "",
    "**이 리포트가 보장하지 않는 것.** 특정 드론의 **절대 dBsm 점값**(문헌 앵커 산포가 우리 오차보다 크다), "
    "플라스틱 셸의 정확한 기여(반투명 불확실 구간), 방위 패턴의 **널 깊이**와 **절대 회전수**(§4·§5 인용 "
    f"금지), 그리고 아직 정렬 안 된 **앙각 축**(우리 el=15° ↔ 문헌 el=0°, {_EL0_TAIL})과 **편파 축**"
    "(스칼라 Γ 라 co-pol/cross-pol 을 분리하지 않는다). 지지하는 것은 상대 순서·대역 추세·자세 구조다.",
    "",
    "> **다음 리포트**: [report09](report09.ipynb) — 이제 **탐지**로 넘어간다. 그 전에 챔버 "
    "**바닥이 놓는 함정**(표적을 경유해 되돌아오는 유령 신호)을 먼저 본다.",
))

# =========================================================================== #
nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
                   "language_info": {"name": "python", "version": "3.12"}},
      "nbformat": 4, "nbformat_minor": 5}

with open(NB, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f"✅ {os.path.relpath(NB, ROOT)} 생성 — 셀 {len(cells)}개 "
      f"(측정 JSON: {os.path.relpath(JS2, ROOT)} + {os.path.relpath(JS1, ROOT)})")
