# -*- coding: utf-8 -*-
"""
report16_rung_cube_eqvol.py — ⭐ **사다리 한 단: 등가부피 정육면체의 마이크로도플러**
================================================================================

무엇을 하는가 (한 줄)
--------------------------------------------------------------------------------
드론을 «부피만 같은 정육면체» 하나로 바꿔치기하고, **진짜로 돌려서** 되돌아오는 전파의
흔들림(마이크로도플러)을 잰다. 그리고 진짜 CAD 메쉬가 내는 흔들림과 나란히 놓는다.

왜 하는가 — 이 라운드의 배경
--------------------------------------------------------------------------------
지도교수의 지적은 «드론 RCS(전파를 되돌리는 세기) 정밀도는 연구 값어치가 없다» 이고,
**우리 데이터가 그 지적을 상당 부분 뒷받침한다**:
  · 절대 세기에서 **모수 0개짜리 등가부피 구**가 우리 정밀 메쉬를 이긴다
    (구 +0.96 dB · rms 1.98  vs  우리 메쉬 −3.30 dB · rms 3.72 — outputs/p3_validation_v2.json)
  · 환경을 넣으면 표적모델 간 차이가 29.3 → 10.1 dB 로 줄어든다
  · WiFi-JEPA(arXiv:2607.11064)에서도 기하 프리미티브가 사람 메쉬를 이겼다

⭐ 그런데 구가 **원리적으로 못 내는 것**이 하나 있다 — 방위(보는 각도)에 따른 산포 ε 이
   정확히 0.00 이다(어느 방향에서 봐도 같은 모양이니까). 우리 메쉬 오차 +1.42 dB,
   상자류 +4.0~4.5 dB.
   → 그래서 묻는다: 그 «구조» 우위가 **마이크로도플러에서는 얼마나 크게 나타나는가.**

이 단이 답하는 것
--------------------------------------------------------------------------------
사다리의 이 단은 «등가부피 정육면체» 다. 구는 돌려도 변조가 0 이어야 하지만(회전대칭),
정육면체는 변조가 나온다. 문제는 **그 변조가 무엇이 만든 변조인가** 다.

⚠ **결론을 미리 정하지 않는다.** 정육면체와 진짜 메쉬의 차이가 작게 나오면 그것이 더
   중요한 결과다 — 교수 지적이 마이크로도플러에서도 맞다는 뜻이고, 방향을 다시 잡아야 한다.

⭐⭐ 사전 예측 (계산 **전에** 적고, 파일로 못박은 다음 계산을 시작한다)
--------------------------------------------------------------------------------
아래 PREDICTION 딕셔너리가 그 예측이다. 실행하면 outputs/report16_rung_cube_eqvol_prereg.json
이 **계산보다 먼저** 기록되고(sha256 + 기록시각), 결과 JSON 은 그 sha256 과 두 시각을 같이
싣는다. 나중에 «맞췄다» 고 말할 수 없게 하는 장치다.

공정성 — 이 라운드의 급소
--------------------------------------------------------------------------------
· 정육면체를 **실제로 돌린다**. 같은 회전축(z), 같은 rpm, 같은 위상 격자.
  안 돌리고 0 을 얻으면 그건 증명이 아니라 동어반복이다.
· 재질·거리·자세·주파수·점밀도 규약을 기준 메쉬와 **완전히 동일**하게 둔다.
  기준 메쉬·구·평판·원판 표는 **다시 계산하지 않고** outputs/report16_base_tables.npz 에서
  그대로 읽는다 — 재계산하면 미세한 차이가 끼어들 수 있기 때문이다.
· 부피 등가는 **계산해서** 맞추고 그 값을 기록한다 (a = V^(1/3), V = 드론 메쉬 고체부피).
· ⭐ 정육면체는 **온몸이 도는** 물체다. 진짜 드론은 몸통이 돌지 않고 프로펠러만 돈다.
  그래서 «온몸 회전» 이라는 운동학을 정육면체에만 주면 불공평하다 — 진짜 드론 메쉬도
  **똑같이 온몸을 돌린** 팔(mesh_rigid_spin)을 같이 만들어 같은 운동학에서 맞붙인다.

⛔ src/drones.py · src/drone_cad.py 는 읽기만 한다.  ⛔ outputs/report15_* 미접촉.
⛔ 숫자 손입력 금지 — 예측 문턱값(판정선)만 사람이 미리 정하고, 나머지는 전부 계산값이다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
import report16_base as R                                              # noqa: E402

SCRATCH = os.environ.get("REPORT16_RUNG_SCRATCH",
                         "/tmp/claude-1015/-home-yunjung-workspace/"
                         "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report16_rung_cube")

OUT_JSON = os.path.join(ROOT, "outputs", "report16_rung_cube_eqvol.json")
OUT_PREREG = os.path.join(ROOT, "outputs", "report16_rung_cube_eqvol_prereg.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report16_rung_cube_eqvol_tables.npz")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_rung_cube_eqvol.png")
BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")

DRONE_KEYS = ("mini2", "matrice4e")
GEN = "G_0804"                      # 기준 세대(어제 CAD 정정 반영본) — base 와 동일


# =========================================================================== #
#  ⭐⭐ 사전 예측 — 계산 **전에** 확정된다. 문턱값(판정선)은 여기서만 사람이 정한다.
# =========================================================================== #
PREDICTION = {
    "written_before_any_field_computation": True,
    "one_line_ko": ("변조는 나온다. 다만 블레이드가 만든 변조가 아니라 **모서리·면이 만든 "
                    "변조**라서 주기와 모양이 달라야 한다."),
    "P1_cube_modulates_at_all": dict(
        claim_ko=("정육면체는 구와 달리 실제로 변조를 낸다. 구 팔(등가부피 구)이 주는 "
                  "«계산기 바닥» 보다 한참 위여야 한다."),
        statistic="in_band_ac_over_dc_db(cube) - in_band_ac_over_dc_db(sphere)",
        threshold_db=20.0, direction="greater",
        why_ko="구는 회전대칭이라 물리적 변조가 0 이다 — 남는 값은 수치잡음뿐이다."),
    "P2_period_is_90deg_not_180deg": dict(
        claim_ko=("정육면체를 z 축으로 돌리면 90° 마다 똑같은 모양이 된다(4겹 대칭). "
                  "그래서 AC 전력은 **4의 배수 차수**에만 실려야 한다. "
                  "나머지는 점 깔기(이산화)가 남긴 찌꺼기여야 하고, 점을 4배 촘촘히 깔면 줄어야 한다."),
        statistic="AC power fraction on orders with |m| mod 4 == 0",
        threshold=0.95, direction="greater",
        secondary="dominant AC order must be a multiple of 4",
        why_ko=("정육면체 옆면 4장이 차례로 돌아오기 때문이다. 위·아래 면은 삼각형 2장으로 "
                "쪼개져 있어 **점 배치만** 2겹 대칭이다 — 여기서 작은 order-2 찌꺼기가 나올 수 있다.")),
    "P3_blade_line_is_absent": dict(
        claim_ko=("진짜 드론의 으뜸 블레이드 선은 **차수 2**(블레이드 2장 → 180° 주기)다. "
                  "정육면체는 그 자리에 선을 세울 수 없다."),
        statistic_a="AC power fraction on orders |m| mod 4 == 2, CAD mesh (blades spinning)",
        threshold_a=0.10, direction_a="greater",
        statistic_b="AC power fraction on orders |m| mod 4 == 2, cube",
        threshold_b=0.05, direction_b="less",
        statistic_c="|AC waveform correlation| between cube and CAD mesh, mean over 24 azimuths",
        threshold_c=0.30, direction_c="less"),
    "P4_width_is_set_by_its_own_corner_radius": dict(
        claim_ko=("스펙트럼 폭은 **자기 모서리 반경**이 정한다 — 프로펠러 팁이 아니다. "
                  "회전축에서 가장 먼 점이 정육면체는 모서리(a/√2), 드론은 블레이드 팁(R)이다."),
        formula="beta_cube = 2*k*(a/sqrt(2))*cos(el) ,  beta_blade = 2*k*R*cos(el)",
        statistic="order_edge_20db(cube) / beta_cube",
        band=[0.40, 1.30],
        why_ko=("모든 산란점의 왕복 위상이 회전각에 대해 변하는 속도의 상한이 2k·ρ_max·cos(el) 이고, "
                "ρ_max 가 곧 회전축에서 가장 먼 거리다. 이 값이 베셀 차수 절단이자 f_tip/f_rot 이다."),
        note_ko="a/√2 < R 인 matrice4e 에서는 정육면체 쪽이 뚜렷이 좁아야 하고, 둘이 비슷한 mini2 에서는 비슷해야 한다."),
    "P5_azimuth_ensemble_is_degenerate_for_a_rigid_spinner": dict(
        claim_ko=("⭐ 온몸이 도는 물체는 «보는 방위를 바꾸는 것» 과 «회전 위상을 옮기는 것» 이 "
                  "같은 조작이다. 그래서 24 방위 앙상블이 서로 **독립이 아니다** — 같은 신호를 "
                  "시간축에서 밀어 본 것뿐이다. 스펙트럼 크기 지표는 방위에 따라 정확히 불변이어야 한다."),
        statistic="sd over 24 azimuths of n_eff_orders (cube)",
        threshold=1e-6, direction="less",
        contrast="same statistic for the real drone (blades spinning) is not degenerate",
        consequence_ko=("이 사실이 이 단의 핵심 함의다: **온몸 회전 프리미티브의 마이크로도플러는 "
                        "그 물체의 정적 방위 패턴을 회전 속도로 읽은 것과 같다.** 즉 ε(방위 산포) "
                        "축과 마이크로도플러 축이 **같은 축**이다 — 새 정보가 아니다. "
                        "진짜 드론은 몸통이 돌지 않으므로 두 축이 다르다.")),
    "P6_mechanism_identity": dict(
        claim_ko=("위 P5 의 기계적 증명. 도는 정육면체의 위상표 E(φ) 는 **가만히 있는** "
                  "정육면체를 방위 −φ 에서 본 값과 부동소수 오차까지 같아야 한다."),
        statistic="max relative difference between rotating table and static azimuth cut",
        threshold=1e-12, direction="less"),
    "thresholds_are_prereg_ko": ("문턱값(20 dB · 0.95 · 0.10 · 0.05 · 0.30 · [0.40,1.30] · 1e-6 · 1e-12)은 "
                                 "계산 전에 사람이 정한 **판정선**이다. 측정값·예측값은 전부 계산 결과다."),
    "what_would_falsify_ko": (
        "P2 가 깨지면(4의 배수 밖에 전력이 많으면) «모서리 변조» 라는 그림 자체가 틀린 것이다. "
        "P3-c 의 상관이 높게 나오면 정육면체가 블레이드 신호를 흉내낸다는 뜻이고, 그러면 "
        "«마이크로도플러에서는 형상이 값어치가 있다» 는 우리 기대가 무너진다 — 그 결과도 그대로 적는다."),
}


# =========================================================================== #
#  기하 도우미
# =========================================================================== #
def mesh_volume(m):
    """닫힌 삼각형 메쉬의 고체 부피 [m³] (발산정리)."""
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    return float(np.sum(np.einsum("ij,ij->i", p0, cr)) / 6.0)


def mesh_area(m):
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(0.5 * np.sum(np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)))


def mesh_sha(m):
    v = np.ascontiguousarray(np.asarray(m.v, float))
    f = np.ascontiguousarray(np.asarray(m.f, np.int64))
    return hashlib.sha1(v.tobytes() + f.tobytes()).hexdigest()[:16]


# =========================================================================== #
#  ⭐ 추가 지표 — «주기가 얼마인가» 를 숫자로. (base 의 md_metrics16 은 그대로 쓴다)
# =========================================================================== #
def comb_profile(tab, sig_db=30.0):
    """위상 표 E(φ) → AC 전력이 **어떤 차수에** 실려 있나.

    왜 필요한가: base 의 지표는 «얼마나 센가·얼마나 넓은가» 는 재지만 «주기가 얼마인가» 는
    재지 않는다. 이 단의 사전 예측이 바로 주기(90° vs 180°)에 관한 것이라 그 자를 새로 댄다.

      frac_mod4_0 : |m| ≡ 0 (mod 4) 에 실린 AC 전력 몫  → 4겹 대칭(90° 주기)의 표식
      frac_mod4_2 : |m| ≡ 2 (mod 4)                      → 180° 주기 성분. 블레이드 2장의 으뜸선이 여기다.
      frac_odd    : 홀수 차수                             → 회전당 1번짜리 비대칭(불균형)
      symmetry_order : 유의(첨두 대비 −sig_db 이상) 차수들의 **최대공약수**.
                       4 면 90° 주기, 2 면 180° 주기, 1 이면 대칭 없음.
    """
    tab = np.asarray(tab, complex)
    S = len(tab)
    c = np.fft.fft(tab) / S
    P = np.abs(c) ** 2
    m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
    ac = m != 0
    tot = float(P[ac].sum())
    if tot <= 0:
        return dict(frac_mod4_0=float("nan"), frac_mod4_2=float("nan"),
                    frac_odd=float("nan"), symmetry_order=0, period_deg=float("nan"))
    am = np.abs(m)
    out = dict(
        frac_mod4_0=float(P[ac & (am % 4 == 0)].sum() / tot),
        frac_mod4_2=float(P[ac & (am % 4 == 2)].sum() / tot),
        frac_odd=float(P[ac & (am % 2 == 1)].sum() / tot),
        frac_even=float(P[ac & (am % 2 == 0)].sum() / tot))
    # 차수별 전력(양수 차수로 접어서)
    opw = np.zeros(S // 2 + 1)
    np.add.at(opw, am[ac], P[ac] / tot)
    pk = float(opw.max())
    sig = [int(i) for i in np.where(opw >= pk * 10 ** (-sig_db / 10.0))[0] if i > 0]
    g = 0
    for i in sig:
        g = math.gcd(g, i)
    out["dominant_order"] = int(np.argmax(opw))
    out["dominant_order_frac"] = float(opw.max())
    out["significant_orders"] = sig[:24]
    out["n_significant_orders"] = len(sig)
    out["symmetry_order"] = int(g)
    out["period_deg"] = float(360.0 / g) if g > 0 else float("nan")
    out["sig_threshold_db"] = float(sig_db)
    #  ⚠ gcd 는 아주 작은 새어나옴 하나에도 1 로 무너지는 «범주형» 요약이다. 문턱을 달리해서
    #    같이 돌려준다 — 두 값이 다르면 그 차이가 곧 «새어나온 약한 선» 의 존재다.
    sig20 = [int(i) for i in np.where(opw >= pk * 10 ** (-20.0 / 10.0))[0] if i > 0]
    g20 = 0
    for i in sig20:
        g20 = math.gcd(g20, i)
    out["symmetry_order_20db"] = int(g20)
    out["period_deg_20db"] = float(360.0 / g20) if g20 > 0 else float("nan")
    out["order2_frac"] = float(opw[2]) if len(opw) > 2 else float("nan")
    out["order4_frac"] = float(opw[4]) if len(opw) > 4 else float("nan")
    return out


def own_beta_gauge(tab, beta_own):
    """⚠ **팔마다 다른 잣대** — 그 팔에서 실제로 움직이는 부분의 최대 반경으로 대역을 정한다.

    base 의 in_band_ac_frac 은 β = 프로펠러 팁 기준이다. 프로펠러만 도는 팔에서는 그것이 맞지만,
    **온몸이 도는 팔**(정육면체·구·강체회전 메쉬)에서는 회전축에서 가장 먼 점이 프로펠러 팁이
    아니다. 그래서 그 팔의 ρ_max 로 다시 계산한 β 로 잰다. 이걸 안 고치면 «몸통이 통째로 도는
    팔은 대역 밖 전력이 많다» 는 잘못된 경고가 뜬다."""
    tab = np.asarray(tab, complex)
    S = len(tab)
    c = np.fft.fft(tab) / S
    P = np.abs(c) ** 2
    m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
    ac = m != 0
    tot = float(P[ac].sum())
    band = max(2, int(math.ceil(1.5 * float(beta_own))))
    inb = float(P[ac & (np.abs(m) <= band)].sum())
    return dict(beta_own=float(beta_own), band_order_own=int(band),
                in_band_ac_frac_own=float(inb / max(tot, 1e-300)),
                in_band_ac_over_dc_db_own=float(
                    10 * np.log10(max(inb, 1e-300) / max(float(P[m == 0].sum()), 1e-300))))


def corr_decomposition(TA, TB, mod=4):
    """⭐ 파형 상관이 **어디서** 오는가. 정육면체는 4의 배수 차수에만 전력이 있으므로,
    상관은 상대 파형 중 «4의 배수 차수 부분» 하고만 생길 수 있다. 그 상한을 계산해 둔다.

      bound = sqrt( A 의 AC 전력 중 4의 배수 차수 몫 )          ← 코시-슈바르츠 상한
      corr_on_shared = 측정 상관 / bound                          ← 공유 차수 안에서의 정렬도
    """
    rows = []
    for i in range(TA.shape[0]):
        a = np.asarray(TA[i], complex) - np.mean(TA[i])
        b = np.asarray(TB[i], complex) - np.mean(TB[i])
        S = len(a)
        ca, cb = np.fft.fft(a), np.fft.fft(b)
        m = np.abs(np.fft.fftfreq(S, d=1.0 / S).astype(int))
        keep = (m % mod == 0)
        fa = float(np.sum(np.abs(ca[keep]) ** 2) / max(float(np.sum(np.abs(ca) ** 2)), 1e-300))
        fb = float(np.sum(np.abs(cb[keep]) ** 2) / max(float(np.sum(np.abs(cb) ** 2)), 1e-300))
        cc = R.ac_corr(a, b)
        bound = math.sqrt(max(fa, 0.0) * max(fb, 0.0))
        rows.append(dict(corr=cc, frac_A_on_shared=fa, frac_B_on_shared=fb,
                         corr_upper_bound=bound,
                         corr_within_shared=cc / max(bound, 1e-300)))
    return {k: R.summarize([r[k] for r in rows]) for k in rows[0]}


def level_spread(tab, lam):
    """한 바퀴 도는 동안 되돌아오는 세기가 얼마나 출렁이나 [dB].
    ⭐ 온몸이 도는 물체에서는 이 값이 곧 **정적 방위 산포 ε** 와 같은 양이다(P5 참조)."""
    tab = np.asarray(tab, complex)
    s = (4 * np.pi / lam ** 2) * np.abs(tab) ** 2
    db = 10 * np.log10(np.maximum(s, 1e-300))
    return dict(sd_db=float(db.std(ddof=1)), ptp_db=float(db.max() - db.min()),
                mean_dbsm=float(db.mean()),
                mu_linear_dbsm=float(10 * np.log10(max(float(np.mean(s)), 1e-300))))


# =========================================================================== #
#  WORKER — GPU 에서 위상 표를 만든다 (별도 프로세스: gpu.pick 이 torch 앞에 와야 한다)
# =========================================================================== #
def _worker(spec_path: str):
    spec = json.load(open(spec_path))
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from gpu import pick                                   # ⚠ torch 보다 먼저
    picked = pick(verbose=True)
    import torch

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from drones import (DRONES, build_drone, build_frame, build_propeller,     # noqa: E402
                        drone_gamma_map)
    from rcs_po import mesh_to_points                                          # noqa: E402
    from geom import box, uv_sphere                                            # noqa: E402

    fc = float(spec["fc"])
    tag = spec["tag"]
    lam = R.C0 / fc
    k_wav = 2.0 * math.pi / lam
    #  ⭐ 점 간격 규약은 base 산출물에서 읽어 온다 — 손으로 다시 적지 않는다.
    BLADE_DIV = float(json.load(open(BASE_JSON))["protocol"]["blade_div"])

    def _odd(n):
        return int(n) if int(n) % 2 == 1 else int(n) + 1

    def nn_spacing(P, n_probe=4000, seed=0):
        from scipy.spatial import cKDTree
        P = np.asarray(P, float)
        if len(P) < 4:
            return float("nan")
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(P), size=min(n_probe, len(P)), replace=False)
        d, _ = cKDTree(P).query(P[idx], k=2)
        return float(np.median(d[:, 1]))

    def build_arm(key, arm):
        """팔 하나의 «도는 점구름» 을 만든다. 전부 원점(z 축) 둘레를 온몸으로 돈다."""
        s = DRONES[key]
        base_arm, fine = (arm[:-5], 4.0) if arm.endswith("_fine") else (arm, 1.0)
        spac = lam / (BLADE_DIV * fine)          # base 규약: 회전부 λ/11
        drone = build_drone(s)
        vol = abs(mesh_volume(drone))
        meta = dict(drone_solid_volume_m3=vol, n_tris_drone=len(drone.f),
                    drone_mesh_sha=mesh_sha(drone),
                    frame_sha=mesh_sha(build_frame(s)),
                    prop_sha=mesh_sha(build_propeller(s, n=26)),
                    requested_spacing_m=float(spac),
                    requested_lambda_over=float(11.0 * fine))
        if base_arm == "cube_eqvol":
            a = vol ** (1.0 / 3.0)
            m = box(a, a, a, center=(0.0, 0.0, 0.0), group="cube")
            P, N, dA = mesh_to_points(m, spac)
            W = dA                                        # PEC |Γ|=1 (구 팔과 같은 규약)
            meta.update(kind="cube_equal_volume", side_m=a,
                        volume_m3=a ** 3,
                        volume_ratio_to_drone=a ** 3 / vol,
                        rmax_inplane_m=a / math.sqrt(2.0),
                        rmax_body_m=a * math.sqrt(3.0) / 2.0,
                        surface_area_m2=mesh_area(m), n_tris=len(m.f),
                        gamma_abs=1.0,
                        note_ko=("기체 전체를 **부피가 같은 정육면체** 하나로 교체(|Γ|=1, PEC). "
                                 "한 변 a = V^(1/3). 같은 z 축·같은 rpm·같은 위상격자로 실제로 돌린다."))
        elif base_arm == "sphere_eqvol":
            r_eq = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
            seg = _odd(max(9, int(math.ceil(2 * math.pi * r_eq / spac))))
            rings = max(3, int(math.ceil(math.pi * r_eq / spac)))
            m = uv_sphere(r_eq, seg=seg, rings=rings, group="sph")
            P, N, dA = mesh_to_points(m, spac)
            W = dA
            meta.update(kind="sphere_equal_volume", r_equal_volume_m=r_eq,
                        volume_m3=4.0 / 3.0 * math.pi * r_eq ** 3,
                        volume_ratio_to_drone=(4.0 / 3.0 * math.pi * r_eq ** 3) / vol,
                        rmax_inplane_m=r_eq, seg=seg, rings=rings,
                        surface_area_m2=mesh_area(m), n_tris=len(m.f), gamma_abs=1.0,
                        note_ko="base 의 sphere 팔과 같은 구성 — 고주파 대역의 «계산기 바닥» 을 잡는다.")
        elif base_arm in ("mesh_rigid_spin", "mesh_rigid_spin_pec"):
            gm = drone_gamma_map(s) if base_arm == "mesh_rigid_spin" else None
            got = mesh_to_points(drone, spac, gamma=gm)
            if gm is None:
                P, N, dA = got
                W = dA
            else:
                P, N, dA, w = got
                W = dA * w
            V = np.asarray(drone.v, float)
            rho = np.linalg.norm(V[:, :2], axis=1)
            meta.update(kind=base_arm, volume_m3=vol, volume_ratio_to_drone=1.0,
                        rmax_inplane_m=float(rho.max()),
                        surface_area_m2=mesh_area(drone), n_tris=len(drone.f),
                        gamma_abs=("material map" if gm is not None else 1.0),
                        note_ko=("⭐ 공정성 대조군 — 진짜 CAD 드론을 **온몸째** 같은 z 축·같은 rpm 으로 "
                                 "돌린다. 정육면체와 운동학이 완전히 같고 형상만 다르다. "
                                 "(프로펠러는 만들어진 자세로 굳어 함께 돈다.) "
                                 "⚠ 온몸이 회전부이므로 프레임도 λ/11 로 깐다 — base 의 mesh 팔은 "
                                 "고정 프레임을 λ/6 로 깔았다. 더 촘촘한 쪽이므로 안전한 차이다."))
        else:
            raise ValueError(arm)
        meta["actual_spacing_m"] = nn_spacing(P)
        meta["lambda_over_actual"] = float(lam / max(meta["actual_spacing_m"], 1e-12))
        meta["n_pts"] = int(len(W))
        return P, N, W, meta

    res, tables = {}, {}
    for key, arms in spec["plan"]:
        s = DRONES[key]
        proto = R.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
        phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
        az_list = np.arange(R.N_AZ) * (360.0 / R.N_AZ)
        entry = dict(protocol=proto, arms={})
        for arm, wfs in arms:
            t0 = time.time()
            P, N, W, meta = build_arm(key, arm)
            for wf in wfs:
                T = np.zeros((len(az_list), proto["n_phase"]), complex)
                for ia, az in enumerate(az_list):
                    u, A, R_t = R.look_and_antenna(az, R.EL_DEG, R.RANGE_M)
                    T[ia] = R.field_rotor(torch, dev, P, N, W, k_wav, A, R_t,
                                          (0.0, 0.0, 0.0), 0.0, 1.0, phis, wf)
                tables[f"{tag}|{key}|{arm}|{wf}"] = T
            # ── P6 기계적 항등식: 도는 물체 ≡ 가만있는 물체를 방위로 훑기 ──────────
            if arm in ("cube_eqvol", "mesh_rigid_spin_pec") and "spherical" in wfs:
                Sst = np.zeros(proto["n_phase"], complex)
                for j in range(proto["n_phase"]):
                    azj = 360.0 * j / proto["n_phase"]
                    u, A, R_t = R.look_and_antenna(azj, R.EL_DEG, R.RANGE_M)
                    Sst[j] = R.field_static(torch, dev, P, N, W, k_wav, A, R_t, "spherical")
                tables[f"{tag}|{key}|{arm}|static_az"] = Sst[None, :]
            # ── ⭐ P5 보강: **위상 격자에 정확히 떨어지는 방위**로만 잰다 ────────────
            #   기본 24 방위(15° 간격)는 위상 스텝의 정수배가 아니다. 그러면 같은 함수를
            #   «어긋난 격자» 로 표집하는 셈이라 접힘(aliasing)이 방위마다 미세하게 달라진다.
            #   격자에 정확히 떨어지는 방위만 골라 재면 그 미세차가 사라져야 한다 —
            #   방위 축퇴가 «거의» 가 아니라 «정확히» 성립한다는 것을 그렇게 증명한다.
            if arm == "cube_eqvol" and "spherical" in wfs:
                S_ = proto["n_phase"]
                jj = sorted({0, 1, S_ // 8, S_ // 3})
                Tx = np.zeros((len(jj), S_), complex)
                for r_, j0 in enumerate(jj):
                    u, A, R_t = R.look_and_antenna(360.0 * j0 / S_, R.EL_DEG, R.RANGE_M)
                    Tx[r_] = R.field_rotor(torch, dev, P, N, W, k_wav, A, R_t,
                                           (0.0, 0.0, 0.0), 0.0, 1.0, phis, "spherical")
                tables[f"{tag}|{key}|{arm}|az_exact"] = Tx
                meta["az_exact_phase_indices"] = [int(x) for x in jj]
                meta["az_exact_deg"] = [360.0 * x / S_ for x in jj]
            meta["seconds"] = float(time.time() - t0)
            entry["arms"][arm] = meta
            print(f"  [{tag}] {key:10s} {arm:22s} pts={meta['n_pts']:>8d} "
                  f"n_phase={proto['n_phase']:4d}  [{meta['seconds']:.1f}s]", flush=True)
        res[key] = entry

    os.makedirs(SCRATCH, exist_ok=True)
    np.savez_compressed(os.path.join(SCRATCH, f"tab_{tag}.npz"),
                        **{k.replace("|", "__"): v for k, v in tables.items()})
    with open(os.path.join(SCRATCH, f"meta_{tag}.json"), "w") as f:
        json.dump(dict(tag=tag, fc=fc, gpu=picked, drones=res,
                       az_deg=list(np.arange(R.N_AZ) * (360.0 / R.N_AZ))), f, ensure_ascii=False)


def run_worker(plan, fc, tag):
    os.makedirs(SCRATCH, exist_ok=True)
    sp = os.path.join(SCRATCH, f"spec_{tag}.json")
    with open(sp, "w") as f:
        json.dump(dict(plan=plan, fc=fc, tag=tag), f)
    launcher = os.path.join(SCRATCH, f"run_{tag}.py")
    with open(launcher, "w") as f:
        f.write(f"import sys\nsys.path.insert(0, {_HERE!r})\n"
                "import report16_rung_cube_eqvol as M\nM._worker(sys.argv[1])\n")
    print(f"▶ worker {tag}  fc={fc/1e9:.2f} GHz", flush=True)
    r = subprocess.run([sys.executable, launcher, sp], cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"worker {tag} failed ({r.returncode})")


def load_new(tag):
    pz = os.path.join(SCRATCH, f"tab_{tag}.npz")
    mj = os.path.join(SCRATCH, f"meta_{tag}.json")
    if not os.path.exists(pz):
        return {}, {}
    z = np.load(pz)
    return ({kk.replace("__", "|"): z[kk] for kk in z.files}, json.load(open(mj)))


def load_base_tables():
    """기준 팔(mesh·sphere·slab·disc)의 표를 **재계산 없이** base 산출물에서 읽는다."""
    z = np.load(BASE_NPZ)
    main, hi = {}, {}
    for kk in z.files:
        parts = kk.split("__")
        if parts[0] == "hi":                      # hi__hi__G_0804__key__arm__wf
            _, _, gen, key, arm, wf = parts
            hi[f"{key}|{arm}|{wf}"] = z[kk]
        else:                                     # main__GEN__key__arm__wf
            _, gen, key, arm, wf = parts
            if gen == GEN:
                main[f"{key}|{arm}|{wf}"] = z[kk]
    return main, hi


# =========================================================================== #
#  분석
# =========================================================================== #
def arm_metrics(T, proto, prop_blades, lam, beta_own=None, rmax_m=None):
    """한 팔의 (24 방위 × n_phase) 표 → 지표 묶음."""
    per = [R.md_metrics16(T[i], proto, prop_blades) for i in range(T.shape[0])]
    cmb = [comb_profile(T[i]) for i in range(T.shape[0])]
    lev = [level_spread(T[i], lam) for i in range(T.shape[0])]
    mk = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90", "dominant_order",
          "blade_comb_frac", "fd_edge_hz", "width_ratio", "width_ratio_10db",
          "width_ratio_30db", "order_edge_20db", "dc_ac_db", "ac_frac_db",
          "sigma_eq_mean_dbsm", "in_band_ac_frac", "in_band_ac_over_dc_db",
          "ac_over_floor_db")
    ck = ("frac_mod4_0", "frac_mod4_2", "frac_odd", "frac_even", "order2_frac",
          "order4_frac", "symmetry_order", "period_deg", "symmetry_order_20db",
          "period_deg_20db", "dominant_order_frac", "n_significant_orders")
    out = dict(per_az={x: R.summarize([m[x] for m in per]) for x in mk},
               comb={x: R.summarize([m[x] for m in cmb]) for x in ck},
               level={x: R.summarize([m[x] for m in lev])
                      for x in ("sd_db", "ptp_db", "mean_dbsm", "mu_linear_dbsm")},
               az0=dict({x: per[0][x] for x in mk}, **{x: cmb[0][x] for x in ck}),
               significant_orders_az0=cmb[0]["significant_orders"],
               interpretable_frac=float(np.mean([m["metrics_interpretable"] for m in per])),
               band_order=int(per[0]["band_order"]), n_az=int(T.shape[0]))
    # ⭐ 방위 앙상블이 독립인가 (P5) — 스펙트럼 크기 지표의 방위간 산포
    out["azimuth_degeneracy"] = dict(
        sd_n_eff_orders=out["per_az"]["n_eff_orders"]["sd"],
        sd_dc_ac_db=out["per_az"]["dc_ac_db"]["sd"],
        sd_flash_contrast_db=out["per_az"]["flash_contrast_db"]["sd"],
        sd_sigma_eq_mean_dbsm=out["per_az"]["sigma_eq_mean_dbsm"]["sd"],
        sd_level_sd_db=out["level"]["sd_db"]["sd"])
    # ⚠ 팔마다 다른 «운동학 천장» 으로 다시 잰 대역 판정 (own_beta_gauge 설명 참조)
    if beta_own is not None and np.isfinite(beta_own):
        og = [own_beta_gauge(T[i], beta_own) for i in range(T.shape[0])]
        out["own_beta_gauge"] = dict(
            rmax_moving_part_m=rmax_m, beta_own=float(beta_own),
            band_order_own=int(og[0]["band_order_own"]),
            **{x: R.summarize([o[x] for o in og])
               for x in ("in_band_ac_frac_own", "in_band_ac_over_dc_db_own")})
        out["own_beta_gauge"]["interpretable_own"] = bool(
            out["own_beta_gauge"]["in_band_ac_frac_own"]["mean"] >= 0.5)
    return out


def paired(TA, TB, proto, nb, lam, keys):
    """같은 방위에서 두 팔을 뺀다 (B − A). 자세 산포가 공통분이라 짝지어 빼면 사라진다."""
    ma = [dict(R.md_metrics16(TA[i], proto, nb), **comb_profile(TA[i]),
               **level_spread(TA[i], lam)) for i in range(TA.shape[0])]
    mb = [dict(R.md_metrics16(TB[i], proto, nb), **comb_profile(TB[i]),
               **level_spread(TB[i], lam)) for i in range(TB.shape[0])]
    row = {}
    for kk in keys:
        d = np.array([y[kk] - x[kk] for x, y in zip(ma, mb)], float)
        d = d[np.isfinite(d)]
        if d.size == 0:
            continue
        sd = float(d.std(ddof=1)) if d.size > 1 else 0.0
        row[kk] = dict(mean=float(d.mean()), sd=sd,
                       sem=float(sd / max(math.sqrt(d.size), 1.0)),
                       frac_positive=float(np.mean(d > 0)), n=int(d.size),
                       min=float(d.min()), max=float(d.max()))
    return row


def waveform_corr(TA, TB):
    return R.summarize([R.ac_corr(TA[i], TB[i]) for i in range(TA.shape[0])])


# =========================================================================== #
#  사전등록 파일 — 계산 **전에** 쓴다
# =========================================================================== #
def write_prereg():
    """예측 + 기하만으로 계산되는 예측값을 계산 전에 파일로 못박는다."""
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from drones import DRONES, build_drone

    geo = {}
    for key in DRONE_KEYS:
        s = DRONES[key]
        vol = abs(mesh_volume(build_drone(s)))
        a = vol ** (1.0 / 3.0)
        r_eq = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
        row = dict(drone_solid_volume_m3=vol, cube_side_m=a,
                   cube_rmax_inplane_m=a / math.sqrt(2.0),
                   sphere_r_equal_volume_m=r_eq,
                   prop_tip_radius_m=float(s.prop_dia_mm) / 2000.0,
                   prop_blades=int(s.prop_blades), hover_rpm=float(s.hover_rpm))
        for lab, fc in (("main", R.FC_MAIN), ("hi", R.FC_PO_KNEE)):
            lam = R.C0 / fc
            kk = 2 * math.pi / lam
            ce = math.cos(math.radians(R.EL_DEG))
            proto = R.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
            bc = 2 * kk * (a / math.sqrt(2.0)) * ce
            row[lab] = dict(
                fc_hz=fc, lambda_m=lam,
                beta_cube_predicted=bc, beta_blade=proto["beta"],
                ratio_beta_cube_over_blade=bc / proto["beta"],
                predicted_edge_order_cube=bc,
                predicted_edge_order_cube_quantised_to_multiple_of_4=int(4 * round(bc / 4.0)),
                predicted_fd_edge_cube_hz=bc * proto["f_rot_hz"],
                blade_fundamental_order=int(s.prop_blades),
                cube_fundamental_order=4,
                n_phase=proto["n_phase"], f_rot_hz=proto["f_rot_hz"],
                cube_side_over_lambda=a / lam)
        geo[key] = row

    payload = dict(
        what=("report16 사다리 — 등가부피 정육면체 마이크로도플러. "
              "⭐ 이 파일은 어떤 전자기 계산보다 **먼저** 기록된다."),
        written_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        written_at_epoch=time.time(),
        producer="benchmark/report16_rung_cube_eqvol.py :: write_prereg()",
        prediction=PREDICTION,
        geometry_only_predictions=geo,
        geometry_note_ko=("이 값들은 메쉬 부피와 파장만으로 나온다 — 산란 계산이 전혀 들어가지 않는다. "
                          "그래서 예측으로 미리 적을 자격이 있다."))
    body = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True)
    payload["sha256_of_body"] = hashlib.sha256(body.encode()).hexdigest()
    os.makedirs(os.path.dirname(OUT_PREREG), exist_ok=True)
    with open(OUT_PREREG, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)
    return payload


# =========================================================================== #
#  MAIN
# =========================================================================== #
PLAN_MAIN = [[k, [["cube_eqvol", ["spherical", "plane"]],
                  ["cube_eqvol_fine", ["spherical"]],
                  ["mesh_rigid_spin", ["spherical"]],
                  ["mesh_rigid_spin_pec", ["spherical"]]]] for k in DRONE_KEYS]
PLAN_HI = [[k, [["cube_eqvol", ["spherical"]],
                ["sphere_eqvol", ["spherical"]]]] for k in DRONE_KEYS]


def main(skip_compute=False, with_hi=True):
    t0 = time.time()

    # ── ① 사전등록 (계산 전) ────────────────────────────────────────────────
    pre = write_prereg()
    print(f"⭐ 사전등록 기록: {os.path.relpath(OUT_PREREG, ROOT)}  "
          f"sha256={pre['sha256_of_body'][:16]}…  ({pre['written_at']})")
    compute_started = time.strftime("%Y-%m-%dT%H:%M:%S")
    t_compute_start = time.time()

    # ── ② 계산 ──────────────────────────────────────────────────────────────
    if not skip_compute:
        run_worker(PLAN_MAIN, R.FC_MAIN, "main")
        if with_hi:
            run_worker(PLAN_HI, R.FC_PO_KNEE, "hi")

    tabs_new, meta_new = load_new("main")
    tabs_hi_new, meta_hi_new = load_new("hi")
    tabs_base, tabs_base_hi = load_base_tables()

    sys.path.insert(0, os.path.join(ROOT, "src"))
    from drones import DRONES
    BJ = json.load(open(BASE_JSON))

    J = dict(meta=dict(
        report="report16 rung — cube_eqvol",
        producer="benchmark/report16_rung_cube_eqvol.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        base_round=os.path.relpath(BASE_JSON, ROOT),
        base_tables=os.path.relpath(BASE_NPZ, ROOT),
        question_ko=("드론을 부피만 같은 정육면체로 바꿔치기하고 **실제로 돌리면** "
                     "어떤 마이크로도플러가 나오는가. 진짜 블레이드 변조와 얼마나 다른가."),
        gpu=dict(main=meta_new.get("gpu"), hi=meta_hi_new.get("gpu"))))

    # ── ③ 사전등록 증적 ─────────────────────────────────────────────────────
    J["prediction_preregistered"] = dict(
        file=os.path.relpath(OUT_PREREG, ROOT),
        sha256=pre["sha256_of_body"],
        written_at=pre["written_at"],
        compute_started_at=compute_started,
        seconds_between=float(t_compute_start - pre["written_at_epoch"]),
        prediction=PREDICTION,
        geometry_only_predictions=pre["geometry_only_predictions"],
        proof_of_order_ko=("예측 파일이 계산 시작보다 먼저 기록됐다(위 두 시각). 파일 본문의 "
                           "sha256 을 여기 그대로 실어 두었으므로 사후 수정도 드러난다."))

    # ── ④ 규약이 base 와 **똑같은지** 기계적으로 확인 ─────────────────────────
    proto = {}
    ok = {}
    for key in DRONE_KEYS:
        s = DRONES[key]
        proto[key] = R.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, R.FC_MAIN)
        proto[key]["hi_band"] = R.derive_protocol(s.prop_dia_mm, s.hover_rpm,
                                                  s.prop_blades, R.FC_PO_KNEE)
        b = BJ["protocol_per_drone"][key]
        ok[key] = {kk: bool(abs(float(proto[key][kk]) - float(b[kk])) <= 1e-9 * max(1.0, abs(float(b[kk]))))
                   for kk in ("beta", "n_phase", "prf_hz", "n_t", "f_tip_hz", "f_rot_hz", "lam_m")}
    J["protocol"] = dict(
        inherited_from="benchmark/report16_base.py (하나도 바꾸지 않았다)",
        fc_main_hz=R.FC_MAIN, fc_po_knee_hz=R.FC_PO_KNEE, el_deg=R.EL_DEG,
        range_m=R.RANGE_M, n_az=R.N_AZ, n_rev=R.N_REV, os_factor=R.OS_FACTOR,
        wavefront_headline="spherical", monostatic=True, period_deg=360.0,
        engine="pure PO on point clouds (no occlusion, no edge diffraction, scalar |Gamma|)",
        blade_div=11.0, frame_div=6.0,
        per_drone=proto,
        identical_to_base=ok,
        identical_to_base_all=bool(all(all(v.values()) for v in ok.values())),
        why_ko=("규약을 하나라도 바꾸면 base 의 mesh·sphere·slab 표와 비교할 수 없다. "
                "그래서 표를 다시 만들지 않고 base 산출물에서 그대로 읽는다."))

    # ── ⑤ 부피 등가 구성 (계산값) ───────────────────────────────────────────
    eq = {}
    for key in DRONE_KEYS:
        am = meta_new["drones"][key]["arms"]
        cub = am["cube_eqvol"]
        sph_base = BJ["arms"][key]["sphere"]["geometry"]
        lam = R.C0 / R.FC_MAIN
        eq[key] = dict(
            drone_solid_volume_m3=cub["drone_solid_volume_m3"],
            cube_side_m=cub["side_m"],
            cube_volume_m3=cub["volume_m3"],
            cube_volume_ratio=cub["volume_ratio_to_drone"],
            sphere_r_equal_volume_m=sph_base["r_equal_volume_m"],
            sphere_volume_m3=sph_base["volume_m3"],
            sphere_volume_ratio=sph_base["volume_m3"] / cub["drone_solid_volume_m3"],
            cube_surface_area_m2=cub["surface_area_m2"],
            sphere_surface_area_m2=4 * math.pi * sph_base["r_equal_volume_m"] ** 2,
            cube_over_sphere_area=cub["surface_area_m2"] /
            (4 * math.pi * sph_base["r_equal_volume_m"] ** 2),
            rmax_inplane_cube_m=cub["rmax_inplane_m"],
            rmax_inplane_drone_m=am["mesh_rigid_spin"]["rmax_inplane_m"],
            prop_tip_radius_m=float(DRONES[key].prop_dia_mm) / 2000.0,
            cube_side_over_lambda_main=cub["side_m"] / lam,
            cube_side_over_lambda_hi=cub["side_m"] / (R.C0 / R.FC_PO_KNEE),
            drone_mesh_sha=cub["drone_mesh_sha"],
            frame_sha_matches_base_G0804=bool(
                cub["frame_sha"] == BJ["mesh_generations"]["fingerprints"][GEN][key]["frame_sha"]),
            prop_sha_matches_base_G0804=bool(
                cub["prop_sha"] == BJ["mesh_generations"]["fingerprints"][GEN][key]["prop_sha"]),
            n_pts_cube=cub["n_pts"], n_pts_cube_fine=am["cube_eqvol_fine"]["n_pts"],
            n_pts_drone=am["mesh_rigid_spin"]["n_pts"],
            actual_spacing_cube_m=cub["actual_spacing_m"],
            actual_spacing_drone_m=am["mesh_rigid_spin"]["actual_spacing_m"])
    J["equal_volume_construction"] = dict(
        values=eq,
        rule_ko=("정육면체 한 변 a = V^(1/3), 구 반지름 r = (3V/4π)^(1/3). V 는 드론 CAD 메쉬의 "
                 "고체 부피를 발산정리로 **계산**한 값이다(손입력 없음). 둘 다 |Γ|=1(완전도체)로, "
                 "재질 모수가 하나도 없는 «모수 0개» 모델이다."),
        fairness_ko=("드론 메쉬 지문(frame_sha·prop_sha)이 base 의 G_0804 와 같은지 확인한다 — "
                     "같은 몸으로 잰 것임을 증명한다."))

    # ── ⑥ 팔별 지표 ─────────────────────────────────────────────────────────
    lam_main = R.C0 / R.FC_MAIN
    J["arms"] = {}
    ARM_SOURCE = {
        "mesh": ("base", "진짜 CAD 드론 — 몸통 고정, 프로펠러만 회전 (기준)"),
        "sphere": ("base", "등가부피 구 — 온몸 회전 (수치 바닥, 물리적 변조 0)"),
        "slab": ("base", "프로펠러를 같은 스팬·코드·부피의 평판으로 교체"),
        "disc": ("base", "프로펠러를 회전대칭 원판으로 교체 (물리적 변조 0)"),
        "mesh_fine": ("base", "mesh 팔을 점 4배 촘촘히 (약한 선이 진짜인지 판정)"),
        "slab_fine": ("base", "slab 팔을 점 4배 촘촘히"),
        "disc_fine": ("base", "disc 팔을 점 4배 촘촘히"),
        "cube_eqvol": ("new", "⭐ 이 단 — 등가부피 정육면체, 온몸 회전"),
        "cube_eqvol_fine": ("new", "정육면체, 점 4배 촘촘 (밀도 반론 차단)"),
        "mesh_rigid_spin": ("new", "진짜 CAD 드론을 **온몸째** 회전 (정육면체와 같은 운동학, 재질 가중)"),
        "mesh_rigid_spin_pec": ("new", "위와 같으나 |Γ|=1 — 정육면체와 재질까지 같은 순수 형상 대조"),
    }
    #  ⭐ 팔마다 «실제로 도는 부분의 최대 반경» ρ_max — 운동학 천장 β_own = 2k·ρ_max·cos(el)
    #     전부 기하에서 계산한다.
    k_main = 2 * math.pi / lam_main
    ce = math.cos(math.radians(R.EL_DEG))
    RMAX = {}
    for key in DRONE_KEYS:
        am = meta_new["drones"][key]["arms"]
        rp = float(DRONES[key].prop_dia_mm) / 2000.0
        RMAX[key] = {
            "mesh": rp, "slab": rp, "disc": rp,                    # 프로펠러만 돈다
            "mesh_fine": rp, "slab_fine": rp, "disc_fine": rp,
            "sphere": BJ["arms"][key]["sphere"]["geometry"]["r_equal_volume_m"],
            "cube_eqvol": am["cube_eqvol"]["rmax_inplane_m"],
            "cube_eqvol_fine": am["cube_eqvol_fine"]["rmax_inplane_m"],
            "mesh_rigid_spin": am["mesh_rigid_spin"]["rmax_inplane_m"],
            "mesh_rigid_spin_pec": am["mesh_rigid_spin_pec"]["rmax_inplane_m"]}
    J["kinematic_ceiling"] = dict(
        rmax_moving_part_m=RMAX,
        beta_own={key: {a: 2 * k_main * v * ce for a, v in row.items()}
                  for key, row in RMAX.items()},
        formula="beta_own = 2*k*rmax*cos(el)  [orders per revolution]",
        why_ko=("⚠ base 의 대역 판정기(in_band_ac_frac)는 프로펠러 팁 기준이다. 프로펠러만 도는 "
                "팔에서는 옳지만 **온몸이 도는 팔**에서는 회전축에서 가장 먼 점이 다르다. "
                "그래서 팔마다 자기 ρ_max 로 다시 잰 값을 own_beta_gauge 에 같이 싣는다. "
                "이걸 안 고치면 «강체회전 메쉬는 대역 밖 전력이 많다» 는 잘못된 경고가 뜬다."))

    for key in DRONE_KEYS:
        nb = int(DRONES[key].prop_blades)
        pr = proto[key]
        J["arms"][key] = {}
        for arm, (src, desc) in ARM_SOURCE.items():
            for wf in ("spherical", "plane"):
                T = (tabs_base.get(f"{key}|{arm}|{wf}") if src == "base"
                     else tabs_new.get(f"main|{key}|{arm}|{wf}"))
                if T is None:
                    continue
                rmx = RMAX[key].get(arm)
                blk = arm_metrics(T, pr, nb, lam_main,
                                  beta_own=(2 * k_main * rmx * ce) if rmx else None,
                                  rmax_m=rmx)
                blk["source"] = src
                blk["what_ko"] = desc
                blk["spins"] = ("whole body" if arm in ("sphere", "cube_eqvol", "cube_eqvol_fine",
                                                        "mesh_rigid_spin", "mesh_rigid_spin_pec")
                                else "rotors only")
                if src == "new":
                    blk["geometry"] = meta_new["drones"][key]["arms"][arm]
                else:
                    blk["geometry"] = BJ["arms"][key][arm].get("geometry", {})
                J["arms"][key].setdefault(arm, {})[wf] = blk

    # ── ⑦ P6 기계적 항등식 — 도는 물체 ≡ 정적 방위 패턴 ──────────────────────
    ident = {}
    for key in DRONE_KEYS:
        for arm in ("cube_eqvol", "mesh_rigid_spin_pec"):
            kst = f"main|{key}|{arm}|static_az"
            krt = f"main|{key}|{arm}|spherical"
            if kst not in tabs_new or krt not in tabs_new:
                continue
            Sst = tabs_new[kst][0]
            Trt = tabs_new[krt][0]                        # az = 0
            S = len(Sst)
            pred = Sst[(-np.arange(S)) % S]               # g(-phi_j)
            num = float(np.max(np.abs(Trt - pred)))
            den = float(np.max(np.abs(Sst)))
            ident[f"{key}|{arm}"] = dict(max_abs_diff=num, max_abs_ref=den,
                                         max_rel=num / max(den, 1e-300))
    J["mechanism_identity"] = dict(
        values=ident,
        claim_ko=("온몸이 z 축으로 도는 물체는 «몸을 +φ 돌리기» 와 «보는 방위를 −φ 돌리기» 가 "
                  "같은 조작이다. 그래서 회전 위상표 E(φ) 는 가만히 있는 물체의 정적 방위 패턴 "
                  "g(−φ) 와 **같아야 한다**. 근거리(구면파)에서도 안테나가 같은 원뿔 위에 있으므로 성립한다."),
        consequence_ko=("⭐⭐ 이 항등식이 이 단의 알맹이다. 온몸 회전 프리미티브의 «마이크로도플러» 는 "
                        "그 물체의 **정적 방위 패턴을 회전 속도로 읽은 것**일 뿐이다. 즉 새 정보 축이 "
                        "아니라 이미 있던 ε(방위 산포) 축이다. 진짜 드론은 몸통이 돌지 않으므로 "
                        "블레이드 변조는 몸통 방위 패턴과 **다른 축**이다."))

    # ── ⑧ 짝지은 비교 ───────────────────────────────────────────────────────
    PKEYS = ("flash_contrast_db", "n_eff_orders", "dc_ac_db", "in_band_ac_over_dc_db",
             "width_ratio", "sigma_eq_mean_dbsm", "frac_mod4_0", "frac_mod4_2",
             "order2_frac", "order4_frac", "sd_db")
    pairs = [("mesh", "cube_eqvol"), ("sphere", "cube_eqvol"),
             ("mesh_rigid_spin_pec", "cube_eqvol"), ("cube_eqvol", "cube_eqvol_fine"),
             ("mesh", "mesh_rigid_spin"), ("mesh_rigid_spin", "mesh_rigid_spin_pec")]
    pr_out, corr = {}, {}
    for key in DRONE_KEYS:
        nb = int(DRONES[key].prop_blades)
        for a, b in pairs:
            TA = tabs_base.get(f"{key}|{a}|spherical", tabs_new.get(f"main|{key}|{a}|spherical"))
            TB = tabs_base.get(f"{key}|{b}|spherical", tabs_new.get(f"main|{key}|{b}|spherical"))
            if TA is None or TB is None:
                continue
            pr_out[f"{key}|{b} - {a}"] = paired(TA, TB, proto[key], nb, lam_main, PKEYS)
            corr[f"{key}|{a} vs {b}"] = waveform_corr(TA, TB)
    J["paired_arm_difference"] = dict(
        values=pr_out,
        what_ko=("같은 방위에서 두 팔의 지표를 뺀 값(B − A). frac_positive 는 24 방위 중 B 가 "
                 "더 큰 비율이다 — 1.0 이면 어느 자세에서 봐도 한 방향이라는 뜻이다."),
        why_paired_ko=("자세 산포는 두 팔에 공통이라 짝지어 빼면 사라진다. 평균±산포만 보면 "
                       "공통 산포에 차이가 묻힌다."))
    # ⭐ 상관이 «어디서» 오는가 — 정육면체는 4의 배수 차수에만 있으므로 그 부분하고만 닮을 수 있다
    cdec = {}
    for key in DRONE_KEYS:
        for a in ("mesh", "mesh_rigid_spin_pec"):
            TA = tabs_base.get(f"{key}|{a}|spherical", tabs_new.get(f"main|{key}|{a}|spherical"))
            TB = tabs_new.get(f"main|{key}|cube_eqvol|spherical")
            if TA is None or TB is None:
                continue
            cdec[f"{key}|{a} vs cube_eqvol"] = corr_decomposition(TA, TB, mod=4)
    J["waveform_correlation"] = dict(
        values=corr,
        decomposition_mod4=cdec,
        what_ko=("AC 성분(평균 제거) 복소 상관. 1 이면 파형이 같다 = 정합필터·템플릿 분류가 "
                 "구별하지 못한다. 0 에 가까우면 완전히 다른 신호다."),
        decomposition_ko=("정육면체는 4의 배수 차수에만 전력이 있다. 그래서 상대 파형과의 상관은 "
                          "상대의 «4의 배수 차수 성분» 하고만 생길 수 있고, 그 몫의 제곱근이 "
                          "상관의 상한(corr_upper_bound)이다. corr_within_shared 는 그 공유 차수 "
                          "안에서 실제로 얼마나 정렬돼 있나다."))

    # ⭐ P5 보강 — 위상 격자에 정확히 떨어지는 방위끼리만 비교
    azx = {}
    for key in DRONE_KEYS:
        T = tabs_new.get(f"main|{key}|cube_eqvol|az_exact")
        if T is None:
            continue
        nb = int(DRONES[key].prop_blades)
        mm = [R.md_metrics16(T[i], proto[key], nb) for i in range(T.shape[0])]
        spec = [np.abs(np.fft.fft(T[i])) for i in range(T.shape[0])]
        ref = spec[0]
        rel = max(float(np.max(np.abs(s - ref)) / max(float(np.max(ref)), 1e-300))
                  for s in spec[1:]) if len(spec) > 1 else 0.0
        azx[key] = dict(
            azimuths_deg=meta_new["drones"][key]["arms"]["cube_eqvol"]["az_exact_deg"],
            n_az=int(T.shape[0]),
            max_rel_spectrum_difference=rel,
            sd_n_eff_orders=float(np.std([m["n_eff_orders"] for m in mm], ddof=1)),
            sd_dc_ac_db=float(np.std([m["dc_ac_db"] for m in mm], ddof=1)),
            sd_flash_contrast_db=float(np.std([m["flash_contrast_db"] for m in mm], ddof=1)),
            sd_on_15deg_grid_n_eff=J["arms"][key]["cube_eqvol"]["spherical"]
            ["azimuth_degeneracy"]["sd_n_eff_orders"])
    J["azimuth_degeneracy_exact_grid"] = dict(
        values=azx,
        what_ko=("기본 24 방위(15° 간격)는 위상 스텝의 정수배가 **아니다**. 그래서 같은 함수를 "
                 "조금씩 어긋난 격자로 표집하게 되고, 접힘(aliasing)이 방위마다 미세하게 달라진다 "
                 "— 지표가 «정확히» 같지 않고 «거의» 같은 이유가 그것이다. "
                 "여기서는 위상 격자에 **정확히** 떨어지는 방위만 골라 다시 잰다."),
        expectation_ko=("축퇴가 진짜라면 이 방위들 사이에서는 스펙트럼 크기가 부동소수 오차까지 "
                        "같아야 한다. 그러면 15° 격자에서 남던 미세차의 원인이 «어긋난 표집» 이라는 "
                        "것이 확정된다."))

    # ── ⑨ 점밀도 반론 차단 ──────────────────────────────────────────────────
    dens = {}
    for key in DRONE_KEYS:
        a = J["arms"][key].get("cube_eqvol", {}).get("spherical")
        b = J["arms"][key].get("cube_eqvol_fine", {}).get("spherical")
        if not a or not b:
            continue
        dens[key] = dict(
            pts_coarse=a["geometry"]["n_pts"], pts_fine=b["geometry"]["n_pts"],
            spacing_coarse_m=a["geometry"]["actual_spacing_m"],
            spacing_fine_m=b["geometry"]["actual_spacing_m"],
            delta={kk: b["per_az"][kk]["mean"] - a["per_az"][kk]["mean"]
                   for kk in ("flash_contrast_db", "n_eff_orders", "width_ratio",
                              "dc_ac_db", "sigma_eq_mean_dbsm", "in_band_ac_over_dc_db")},
            delta_comb={kk: b["comb"][kk]["mean"] - a["comb"][kk]["mean"]
                        for kk in ("frac_mod4_0", "frac_mod4_2", "frac_odd")})
    J["point_density_control"] = dict(
        refine_x4="rotating part lambda/11 -> lambda/44",
        deltas=dens,
        question_ko=("«정육면체가 성기게 깔려서 다르게 보이는 것 아니냐» 는 반론을 차단한다. "
                     "특히 4의 배수가 아닌 차수(frac_mod4_2)는 위·아래 면의 삼각분할이 "
                     "2겹 대칭뿐이라 생기는 **점 배치 찌꺼기**로 예측했다 — 촘촘히 깔면 줄어야 한다."))

    # ── ⑨-2 재질 반론 차단 ─────────────────────────────────────────────────
    #   «정육면체는 완전도체(|Γ|=1)인데 드론은 손실 재질이니 그래서 세게 변조하는 것 아니냐»
    #   → 같은 드론을 재질표로 한 번, |Γ|=1 로 한 번 돌려 그 차이의 크기를 재 둔다.
    mat = {}
    for key in DRONE_KEYS:
        d = J["paired_arm_difference"]["values"].get(
            f"{key}|mesh_rigid_spin_pec - mesh_rigid_spin", {})
        cm = J["paired_arm_difference"]["values"].get(f"{key}|cube_eqvol - mesh", {})
        if not d:
            continue
        mat[key] = dict(
            material_effect_on_dc_ac_db=d.get("dc_ac_db", {}).get("mean"),
            material_effect_on_flash_db=d.get("flash_contrast_db", {}).get("mean"),
            material_effect_on_n_eff=d.get("n_eff_orders", {}).get("mean"),
            material_effect_on_level_db=d.get("sigma_eq_mean_dbsm", {}).get("mean"),
            cube_minus_real_dc_ac_db=cm.get("dc_ac_db", {}).get("mean"),
            ratio_material_over_cube_gap=abs(d.get("dc_ac_db", {}).get("mean", np.nan)) /
            max(abs(cm.get("dc_ac_db", {}).get("mean", np.nan)), 1e-12))
    J["material_control"] = dict(
        values=mat,
        what_ko=("같은 드론 메쉬를 **재질표** 로 한 번, **완전도체(|Γ|=1)** 로 한 번 돌린 차이. "
                 "정육면체는 완전도체라 «재질이 달라서 정육면체가 더 세게 변조하는 것 아니냐» 는 "
                 "반론이 가능한데, 그 반론이 설명할 수 있는 크기가 여기 있다."),
        how_to_read_ko=("ratio_material_over_cube_gap 이 1 보다 훨씬 작으면 재질로는 정육면체와 "
                        "진짜 드론의 격차를 설명할 수 없다는 뜻이다."))

    # ── ⑩ 고주파(PO 유효 무릎) 대조 ────────────────────────────────────────
    if tabs_hi_new:
        hi = {}
        for key in DRONE_KEYS:
            nb = int(DRONES[key].prop_blades)
            prh = proto[key]["hi_band"]
            lam_hi = R.C0 / R.FC_PO_KNEE
            k_hi = 2 * math.pi / lam_hi
            rmx_hi = dict(RMAX[key])
            rmx_hi["sphere_eqvol"] = rmx_hi["sphere"]
            for arm in ("mesh", "slab", "cube_eqvol", "sphere_eqvol"):
                T = (tabs_base_hi.get(f"{key}|{arm}|spherical")
                     if arm in ("mesh", "slab") else
                     tabs_hi_new.get(f"hi|{key}|{arm}|spherical"))
                if T is None:
                    continue
                rr = rmx_hi.get(arm)
                hi[f"{key}|{arm}"] = arm_metrics(T, prh, nb, lam_hi,
                                                 beta_own=(2 * k_hi * rr * ce) if rr else None,
                                                 rmax_m=rr)
            for a, b in (("mesh", "cube_eqvol"), ("sphere_eqvol", "cube_eqvol")):
                TA = (tabs_base_hi.get(f"{key}|{a}|spherical")
                      if a in ("mesh", "slab") else tabs_hi_new.get(f"hi|{key}|{a}|spherical"))
                TB = tabs_hi_new.get(f"hi|{key}|{b}|spherical")
                if TA is None or TB is None:
                    continue
                hi[f"{key}|paired {b} - {a}"] = paired(TA, TB, prh, nb, lam_hi, PKEYS)
                hi[f"{key}|corr {a} vs {b}"] = waveform_corr(TA, TB)
        J["hi_band"] = dict(
            fc_hz=R.FC_PO_KNEE, metrics=hi,
            note_ko=("블레이드가 PO 유효 무릎(폭 ≥ 0.729λ)을 넘는 주파수에서 같은 지표를 다시 잰다. "
                     "3.5 GHz 결론이 «커널이 약한 대역» 의 산물인지 확인하는 자리다. "
                     "여기서는 정육면체 한 변이 파장의 몇 배가 되어 면 반사가 훨씬 날카로워진다."))

    # ── ⑪ 예측 채점 (자동) ─────────────────────────────────────────────────
    J["prediction_scorecard"] = _score(J, pre)

    # ── ⑫ RCS 축과의 연결 ───────────────────────────────────────────────────
    try:
        P3 = json.load(open(os.path.join(ROOT, "outputs", "p3_validation_v2.json")))
        tb = P3["controls"]["table"]
        J["rcs_axis_crosslink"] = dict(
            source="outputs/p3_validation_v2.json (Phantom 3, 1.8–18.2 GHz, Yuan θ90 실측곡선 기준)",
            cube_vol=dict(level_err_db=tb["cube_vol_v2"]["level_err_db"],
                          rms_db=tb["cube_vol_v2"]["rms_db"],
                          eps_mean_db=tb["cube_vol_v2"]["eps_mean_db"],
                          eps_err_db=tb["cube_vol_v2"]["eps_err_vs_das_db"]),
            sphere_vol=dict(level_err_db=tb["sphere_vol_v2"]["level_err_db"],
                            rms_db=tb["sphere_vol_v2"]["rms_db"],
                            eps_mean_db=tb["sphere_vol_v2"]["eps_mean_db"],
                            eps_err_db=tb["sphere_vol_v2"]["eps_err_vs_das_db"]),
            sphere_best=dict(what=tb["sphere_eqvol_paperbox"]["what"],
                             level_err_db=tb["sphere_eqvol_paperbox"]["level_err_db"],
                             rms_db=tb["sphere_eqvol_paperbox"]["rms_db"],
                             eps_err_db=tb["sphere_eqvol_paperbox"]["eps_err_vs_das_db"]),
            our_mesh=dict(level_err_db=tb["ours_phantom3_mesh_v2"]["level_err_db"],
                          rms_db=tb["ours_phantom3_mesh_v2"]["rms_db"],
                          eps_err_db=tb["ours_phantom3_mesh_v2"]["eps_err_vs_das_db"]),
            reading_ko=("같은 «등가부피 정육면체» 모델이 RCS 축에서 받은 성적표다 — 레벨도 ε(방위 산포)도 "
                        "구·우리 메쉬보다 나쁘다(위 숫자 참조). "
                        "⚠ 대상 기체가 다르다(Phantom 3) — 같은 «모델 종류» 의 성적표를 참고로 붙인 것이지 "
                        "이 단의 mini2·matrice4e 수치가 아니다."),
            why_here_ko=("⭐ P5/P6 항등식 때문에 이 연결이 단순 참고가 아니다. 온몸 회전 프리미티브의 "
                         "마이크로도플러는 그 물체의 방위 패턴이므로, ε 이 틀린 모델은 "
                         "마이크로도플러도 **같은 방식으로** 틀린다."))
    except Exception as e:                                          # pragma: no cover
        J["rcs_axis_crosslink"] = dict(error=str(e))

    # ── ⑬ 한계 ──────────────────────────────────────────────────────────────
    knee = json.load(open(os.path.join(ROOT, "outputs", "report00_po_case.json")))["s4_limits"]
    J["limits"] = dict(
        po_validity=dict(
            knee_a_over_lambda=knee["po_validity_knee_a_over_lambda"],
            blade_knee_ghz=knee["feature_knee_frequencies"]["prop_blade_13p78mm_ghz"],
            production_band_ghz=R.FC_MAIN / 1e9,
            statement_ko=("⚠ 마이크로도플러를 만드는 부품(프로펠러 블레이드, 폭 13.78 mm)은 "
                          f"{knee['feature_knee_frequencies']['prop_blade_13p78mm_ghz']} GHz 에서야 "
                          "PO 유효 무릎을 넘는다. 생산 대역 3.5 GHz 에서는 **커널이 가장 약한 부품이 "
                          "곧 신호원**이다. 그래서 15.86 GHz 를 같이 돌렸다. "
                          "⭐ 반대로 정육면체는 한 변이 파장급 이상이라 PO 가 가장 잘 맞는 물체다 — "
                          "즉 이 비교는 **정육면체 쪽에 유리하게** 기울어 있다."))
        ,
        occlusion=("이 커널에는 가림이 없다. 다만 정육면체·구는 볼록체라 자기가림이 원래 없고, "
                   "PO 조명 판정(n̂·û>0)이 그 역할을 정확히 한다. 드론 메쉬 팔에서는 동체 뒤 "
                   "블레이드가 계속 세어져 dc_ac_db 가 오염된다 — 절대값 인용 금지."),
        rigid_spin_is_generous_ko=("⭐ 정육면체를 온몸째 로터 rpm 으로 돌리는 것은 **프리미티브에게 "
                                   "후한** 설정이다. 진짜 드론은 몸통이 돌지 않는다. 그래도 그렇게 한 "
                                   "이유는 «안 돌려서 0 을 얻으면 동어반복» 이기 때문이다. "
                                   "같은 후함을 진짜 메쉬에도 주려고 mesh_rigid_spin 팔을 함께 만들었다."),
        not_a_detector_claim=("여기 숫자는 표적 모델의 신호 구조 차이지 탐지 성능이 아니다. "
                              "탐지로 옮기려면 잡음·적분시간·CFAR 이 필요하다(report12 계열)."))

    # ── ⑭ 결론 (숫자는 위에서 계산된 것만 참조) ─────────────────────────────
    J["findings"] = _findings(J)

    # ── 저장 ────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    save = {k.replace("|", "__"): v for k, v in tabs_new.items()}
    save.update({("hi__" + k.replace("|", "__")): v for k, v in tabs_hi_new.items()})
    np.savez_compressed(OUT_NPZ, **save)
    J["meta"]["tables_npz"] = os.path.relpath(OUT_NPZ, ROOT)
    try:
        J["figures"] = dict(main=make_figure(J, tabs_new, tabs_base, tabs_hi_new,
                                             tabs_base_hi, proto))
    except Exception as e:                                          # pragma: no cover
        import traceback
        traceback.print_exc()
        J["figures"] = dict(error=str(e))
    J["meta"]["seconds"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✅ {os.path.relpath(OUT_JSON, ROOT)}  [{J['meta']['seconds']:.0f}s]")
    return J


# --------------------------------------------------------------------------- #
#  예측 채점
# --------------------------------------------------------------------------- #
def _score(J, pre):
    S = {}

    def arm(key, a, what, wf="spherical"):
        return J["arms"].get(key, {}).get(a, {}).get(wf, {}).get(what, {})

    for key in DRONE_KEYS:
        row = {}
        # P1 — 변조가 나오는가
        c = arm(key, "cube_eqvol", "per_az").get("in_band_ac_over_dc_db", {})
        s = arm(key, "sphere", "per_az").get("in_band_ac_over_dc_db", {})
        if c and s:
            d = c["mean"] - s["mean"]
            row["P1_cube_modulates_at_all"] = dict(
                cube_db=c["mean"], sphere_floor_db=s["mean"], delta_db=d,
                threshold_db=PREDICTION["P1_cube_modulates_at_all"]["threshold_db"],
                verdict="PASS" if d > PREDICTION["P1_cube_modulates_at_all"]["threshold_db"] else "FAIL")
        # P2 — 90° 주기 (4의 배수 차수)
        cb = arm(key, "cube_eqvol", "comb")
        if cb:
            f4 = cb["frac_mod4_0"]["mean"]
            dom = arm(key, "cube_eqvol", "per_az")["dominant_order"]["mean"]
            symo = cb["symmetry_order"]["mean"]
            row["P2_period_is_90deg"] = dict(
                frac_on_multiples_of_4=f4, threshold=PREDICTION["P2_period_is_90deg_not_180deg"]["threshold"],
                mean_dominant_order=dom, mean_symmetry_order=symo,
                mean_period_deg=cb["period_deg"]["mean"],
                dominant_is_multiple_of_4=bool(abs(dom / 4.0 - round(dom / 4.0)) < 1e-9),
                verdict=("PASS" if (f4 > PREDICTION["P2_period_is_90deg_not_180deg"]["threshold"]
                                    and abs(dom / 4.0 - round(dom / 4.0)) < 1e-9) else "FAIL"))
        # P3 — 블레이드 선(차수 2)은 정육면체에 없다
        mb = arm(key, "mesh", "comb")
        cc = J["waveform_correlation"]["values"].get(f"{key}|mesh vs cube_eqvol", {})
        if cb and mb and cc:
            a_ = mb["frac_mod4_2"]["mean"]
            b_ = cb["frac_mod4_2"]["mean"]
            c_ = cc["mean"]
            P = PREDICTION["P3_blade_line_is_absent"]
            dec = J["waveform_correlation"]["decomposition_mod4"].get(
                f"{key}|mesh vs cube_eqvol", {})
            sub = dict(a_mesh_has_order2_family=bool(a_ > P["threshold_a"]),
                       b_cube_has_none=bool(b_ < P["threshold_b"]),
                       c_waveforms_uncorrelated=bool(c_ < P["threshold_c"]))
            row["P3_blade_line_absent"] = dict(
                mesh_frac_mod4_2=a_, threshold_a=P["threshold_a"],
                cube_frac_mod4_2=b_, threshold_b=P["threshold_b"],
                waveform_corr_mesh_vs_cube=c_, threshold_c=P["threshold_c"],
                mesh_order2_frac=mb["order2_frac"]["mean"],
                cube_order2_frac=cb["order2_frac"]["mean"],
                subcriteria=sub,
                corr_upper_bound_from_shared_orders=dec.get("corr_upper_bound", {}).get("mean"),
                corr_within_shared_orders=dec.get("corr_within_shared", {}).get("mean"),
                mesh_frac_on_multiples_of_4=dec.get("frac_A_on_shared", {}).get("mean"),
                verdict=("PASS" if all(sub.values()) else "FAIL"),
                verdict_note_ko=("하위 조건별로 갈렸다면 어느 것이 깨졌는지 subcriteria 를 볼 것. "
                                 "상관은 정육면체가 가진 유일한 자리(4의 배수 차수)에서만 생길 수 "
                                 "있으므로 corr_upper_bound 와 나란히 읽어야 한다."))
        # P4 — 폭은 자기 모서리 반경이 정한다
        g = pre["geometry_only_predictions"][key]["main"]
        e = arm(key, "cube_eqvol", "per_az").get("order_edge_20db", {})
        em = arm(key, "mesh", "per_az").get("order_edge_20db", {})
        if e:
            r = e["mean"] / g["beta_cube_predicted"]
            lo, hi = PREDICTION["P4_width_is_set_by_its_own_corner_radius"]["band"]
            row["P4_width_from_own_corner_radius"] = dict(
                beta_cube_predicted=g["beta_cube_predicted"],
                beta_blade=g["beta_blade"],
                measured_edge_order_cube=e["mean"],
                measured_edge_order_mesh=em.get("mean"),
                ratio_measured_over_predicted=r, band=[lo, hi],
                cube_edge_hz=e["mean"] * J["protocol"]["per_drone"][key]["f_rot_hz"],
                verdict="PASS" if lo <= r <= hi else "FAIL")
        # P5 — 방위 앙상블 축퇴
        dg = arm(key, "cube_eqvol", "azimuth_degeneracy")
        dm = arm(key, "mesh", "azimuth_degeneracy")
        if dg:
            th = PREDICTION["P5_azimuth_ensemble_is_degenerate_for_a_rigid_spinner"]["threshold"]
            ex = J.get("azimuth_degeneracy_exact_grid", {}).get("values", {}).get(key, {})
            row["P5_azimuth_degenerate"] = dict(
                cube_sd_n_eff_orders=dg["sd_n_eff_orders"],
                cube_sd_dc_ac_db=dg["sd_dc_ac_db"],
                drone_sd_n_eff_orders=dm.get("sd_n_eff_orders"),
                drone_sd_dc_ac_db=dm.get("sd_dc_ac_db"),
                ratio_cube_over_drone_sd=(dg["sd_n_eff_orders"] /
                                          max(dm.get("sd_n_eff_orders") or np.nan, 1e-300)),
                threshold=th,
                verdict="PASS" if dg["sd_n_eff_orders"] < th else "FAIL",
                on_exact_phase_grid=ex,
                verdict_note_ko=("문턱값은 «부동소수 오차» 를 염두에 두고 정한 것인데, 15° 방위 격자는 "
                                 "위상 스텝의 정수배가 아니라서 표집 격자가 방위마다 어긋난다 — "
                                 "그 어긋남이 남긴 미세차가 문턱보다 크면 여기서 FAIL 이 난다. "
                                 "주장 자체(축퇴)가 맞는지는 on_exact_phase_grid 와 "
                                 "ratio_cube_over_drone_sd 로 판단할 것."))
        # P6 — 기계적 항등식
        idv = J["mechanism_identity"]["values"].get(f"{key}|cube_eqvol")
        if idv:
            th = PREDICTION["P6_mechanism_identity"]["threshold"]
            row["P6_mechanism_identity"] = dict(
                max_rel=idv["max_rel"], threshold=th,
                verdict="PASS" if idv["max_rel"] < th else "FAIL")
        S[key] = row
    verds = [v["verdict"] for r in S.values() for v in r.values() if isinstance(v, dict)]
    S["_summary"] = dict(
        band="3.5 GHz (headline)",
        n_pass=int(sum(1 for v in verds if v == "PASS")), n_total=len(verds),
        all_pass=bool(all(v == "PASS" for v in verds)),
        rule_ko=("⭐ 이 채점표의 문턱값은 계산 전에 사전등록 파일에 박아 둔 값이다. "
                 "FAIL 이 나오면 그대로 둔다 — 예측이 틀린 것도 결과다."))

    # ── 같은 예측을 **고주파(15.86 GHz)** 에서도 그대로 채점한다 ────────────────
    #    사전등록 파일이 두 대역의 기하 예측을 모두 담고 있으므로 사후 고르기가 아니다.
    #    통과한 것만 고르지 않고 P2·P3·P4 전부를 다시 잰다.
    hb = J.get("hi_band", {}).get("metrics", {})
    if hb:
        H = {}
        for key in DRONE_KEYS:
            cbm = hb.get(f"{key}|cube_eqvol")
            msh = hb.get(f"{key}|mesh")
            if not cbm or not msh:
                continue
            g = pre["geometry_only_predictions"][key]["hi"]
            f4 = cbm["comb"]["frac_mod4_0"]["mean"]
            dom = cbm["per_az"]["dominant_order"]["mean"]
            a_ = msh["comb"]["frac_mod4_2"]["mean"]
            b_ = cbm["comb"]["frac_mod4_2"]["mean"]
            c_ = hb.get(f"{key}|corr mesh vs cube_eqvol", {}).get("mean", float("nan"))
            e_ = cbm["per_az"]["order_edge_20db"]["mean"]
            r_ = e_ / g["beta_cube_predicted"]
            P3P = PREDICTION["P3_blade_line_is_absent"]
            lo, hi_ = PREDICTION["P4_width_is_set_by_its_own_corner_radius"]["band"]
            sub = dict(a_mesh_has_order2_family=bool(a_ > P3P["threshold_a"]),
                       b_cube_has_none=bool(b_ < P3P["threshold_b"]),
                       c_waveforms_uncorrelated=bool(c_ < P3P["threshold_c"]))
            H[key] = dict(
                P2_period_is_90deg=dict(
                    frac_on_multiples_of_4=f4, mean_dominant_order=dom,
                    threshold=PREDICTION["P2_period_is_90deg_not_180deg"]["threshold"],
                    verdict=("PASS" if (f4 > PREDICTION["P2_period_is_90deg_not_180deg"]["threshold"]
                                        and abs(dom / 4.0 - round(dom / 4.0)) < 1e-9) else "FAIL")),
                P3_blade_line_absent=dict(
                    mesh_frac_mod4_2=a_, cube_frac_mod4_2=b_,
                    waveform_corr_mesh_vs_cube=c_, subcriteria=sub,
                    verdict="PASS" if all(sub.values()) else "FAIL"),
                P4_width_from_own_corner_radius=dict(
                    beta_cube_predicted=g["beta_cube_predicted"], beta_blade=g["beta_blade"],
                    measured_edge_order_cube=e_,
                    measured_edge_order_mesh=msh["per_az"]["order_edge_20db"]["mean"],
                    ratio_measured_over_predicted=r_, band=[lo, hi_],
                    verdict="PASS" if lo <= r_ <= hi_ else "FAIL"))
        hv = [v["verdict"] for r in H.values() for v in r.values()]
        H["_summary"] = dict(band=f"{R.FC_PO_KNEE/1e9:.2f} GHz (PO validity knee for the blade)",
                             n_pass=int(sum(1 for v in hv if v == "PASS")), n_total=len(hv),
                             all_pass=bool(all(v == "PASS" for v in hv)),
                             why_ko=("3.5 GHz 결론이 «커널이 가장 약한 대역» 의 산물인지 확인하는 자리. "
                                     "두 대역에서 판정이 같으면 대역 탓이 아니다."))
        S["hi_band"] = H
    return S


# --------------------------------------------------------------------------- #
#  결론
# --------------------------------------------------------------------------- #
def _odd_leak(J, a, key):
    """홀수 차수에 남는 전력이 «점 깔기 찌꺼기» 인지 검사한다.

    2엽 프로펠러는 원리적으로 짝수 차수만 낸다(180° 마다 같은 모양). 정육면체는 4의 배수만 낸다.
    그러니 홀수에 남는 것은 원리상 0 이어야 하고, 점을 4배 촘촘히 깔아 **줄어들면** 찌꺼기가 맞다.
    ⚠ 안 줄어들면 찌꺼기가 아니라 **메쉬 자체의 비대칭**(두 날개가 정말로 다름)일 수 있다 —
      그 경우를 «확인됨» 으로 적지 않는다."""
    out = {}
    for lab, c, f in (("real_drone", "mesh", "mesh_fine"),
                      ("cube", "cube_eqvol", "cube_eqvol_fine")):
        v0 = a(key, c, "comb", "frac_odd").get("mean")
        v1 = a(key, f, "comb", "frac_odd").get("mean")
        row = dict(coarse=v0, refined_x4=v1)
        if v0 and v1:
            row["ratio_coarse_over_refined"] = v0 / max(v1, 1e-300)
            row["verdict"] = ("discretisation residue (shrinks with refinement)"
                              if v1 < 0.5 * v0 else
                              "NOT explained by point density — likely real mesh asymmetry")
        out[lab] = row
    out["statistic_ko"] = ("홀수 차수 전력 몫. 원리상 0 이어야 하는 자리다. 4배 촘촘히 깔았을 때 "
                           "줄면 점 깔기 찌꺼기, 안 줄면 메쉬 자체의 비대칭이다.")
    return out


def _findings(J):
    F = {}

    def a(key, arm, blk, what, wf="spherical"):
        return J["arms"].get(key, {}).get(arm, {}).get(wf, {}).get(blk, {}).get(what, {})

    # Q0 — 한 줄 요약에 쓸 숫자 (전부 위에서 계산된 값을 골라 온 것)
    head = {}
    for key in DRONE_KEYS:
        pm = J["paired_arm_difference"]["values"].get(f"{key}|cube_eqvol - mesh", {})
        pr_ = J["paired_arm_difference"]["values"].get(
            f"{key}|cube_eqvol - mesh_rigid_spin_pec", {})
        sc = J["prediction_scorecard"].get(key, {})
        head[key] = dict(
            modulation_depth_error_db=dict(
                statistic="dc_ac_db(cube) - dc_ac_db(real drone).  음수 = 정육면체가 과변조",
                paired_mean=pm.get("dc_ac_db", {}).get("mean"),
                frac_positive=pm.get("dc_ac_db", {}).get("frac_positive"),
                n=pm.get("dc_ac_db", {}).get("n")),
            per_revolution_level_swing_db=dict(
                statistic="한 바퀴 도는 동안 σ 의 표준편차 [dB] (온몸 회전 팔에서는 곧 방위 산포 ε)",
                cube=a(key, "cube_eqvol", "level", "sd_db").get("mean"),
                real_drone_rotors_only=a(key, "mesh", "level", "sd_db").get("mean"),
                real_drone_rigid_spin=a(key, "mesh_rigid_spin_pec", "level", "sd_db").get("mean"),
                sphere=a(key, "sphere", "level", "sd_db").get("mean")),
            harmonic_richness=dict(
                statistic="n_eff_orders — 실질적으로 살아 있는 하모닉 차수 개수",
                cube=a(key, "cube_eqvol", "per_az", "n_eff_orders").get("mean"),
                real_drone_rigid_spin=a(key, "mesh_rigid_spin_pec", "per_az",
                                        "n_eff_orders").get("mean"),
                real_drone_rotors_only=a(key, "mesh", "per_az", "n_eff_orders").get("mean"),
                paired_cube_minus_rigid=pr_.get("n_eff_orders", {}).get("mean"),
                paired_frac_positive=pr_.get("n_eff_orders", {}).get("frac_positive")),
            period=dict(
                statistic_ko=("유의 차수들의 최대공약수 → 360/그것 = 주기. ⚠ gcd 는 약한 새어나옴 "
                              "하나에 무너지므로 −30 dB·−20 dB 두 문턱을 같이 본다. "
                              "진짜 증거는 아래 전력 몫이다."),
                cube_deg=a(key, "cube_eqvol", "comb", "period_deg").get("mean"),
                cube_deg_20db=a(key, "cube_eqvol", "comb", "period_deg_20db").get("mean"),
                real_drone_rotors_only_deg=a(key, "mesh", "comb", "period_deg").get("mean"),
                real_drone_rotors_only_deg_20db=a(key, "mesh", "comb",
                                                  "period_deg_20db").get("mean"),
                real_drone_rigid_spin_deg=a(key, "mesh_rigid_spin_pec", "comb",
                                            "period_deg").get("mean"),
                power_fractions={x: dict(
                    on_multiples_of_4=a(key, x, "comb", "frac_mod4_0").get("mean"),
                    on_orders_2_6_10=a(key, x, "comb", "frac_mod4_2").get("mean"),
                    on_odd_orders=a(key, x, "comb", "frac_odd").get("mean"))
                    for x in ("cube_eqvol", "mesh", "mesh_fine", "mesh_rigid_spin_pec")}),
            odd_order_leak_check=_odd_leak(J, a, key),
            scorecard={k2: v2.get("verdict") for k2, v2 in sc.items() if isinstance(v2, dict)})
    F["q0_headline_numbers"] = dict(
        values=head,
        what_ko=("이 단에서 인용할 숫자만 모았다. 전부 위 블록에서 계산된 값이며 손으로 적은 것이 없다."),
        how_to_read_ko=("modulation_depth_error_db 가 음수면 정육면체가 진짜 드론보다 **더 깊게** "
                        "변조한다는 뜻이다 — 프리미티브가 «변조가 모자라서» 가 아니라 «너무 많아서» "
                        "틀릴 수 있다는 점이 이 단에서 처음 드러난 것이다."))

    # Q1 — 정육면체는 변조를 내는가, 그리고 그 변조는 무엇인가
    q1 = {}
    for key in DRONE_KEYS:
        q1[key] = dict(
            in_band_ac_over_dc_db={x: a(key, x, "per_az", "in_band_ac_over_dc_db").get("mean")
                                   for x in ("sphere", "cube_eqvol", "mesh_rigid_spin_pec", "mesh")},
            period_deg={x: a(key, x, "comb", "period_deg").get("mean")
                        for x in ("cube_eqvol", "mesh_rigid_spin_pec", "mesh")},
            dominant_order={x: a(key, x, "per_az", "dominant_order").get("mean")
                            for x in ("cube_eqvol", "mesh_rigid_spin_pec", "mesh")},
            frac_mod4_2={x: a(key, x, "comb", "frac_mod4_2").get("mean")
                         for x in ("cube_eqvol", "mesh_rigid_spin_pec", "mesh")},
            flash_contrast_db={x: a(key, x, "per_az", "flash_contrast_db").get("mean")
                               for x in ("sphere", "cube_eqvol", "mesh_rigid_spin_pec", "mesh")},
            n_eff_orders={x: a(key, x, "per_az", "n_eff_orders").get("mean")
                          for x in ("cube_eqvol", "mesh_rigid_spin_pec", "mesh")})
    F["q1_what_does_a_spinning_cube_produce"] = dict(
        question_ko="등가부피 정육면체를 실제로 돌리면 무엇이 나오는가",
        values=q1,
        reading_ko=("sphere = 계산기 바닥(물리적 변조 0). cube_eqvol = 이 단. "
                    "mesh_rigid_spin_pec = 진짜 드론을 같은 방식으로 온몸째 돌린 것(형상만 다른 대조). "
                    "mesh = 진짜 드론(몸통 고정, 프로펠러만 회전) — 실제로 우리가 잡으려는 신호."))

    # Q2 — 주기·모양이 다른가 (사전 예측의 핵심)
    F["q2_is_it_a_different_kind_of_modulation"] = dict(
        question_ko="⭐ 그 변조가 블레이드 변조와 **다른 종류**인가 (주기·모양)",
        scorecard=J["prediction_scorecard"],
        waveform_correlation=J["waveform_correlation"]["values"],
        how_to_read_ko=("주기(period_deg)와 으뜸 차수(dominant_order)가 다르면 «다른 종류» 다. "
                        "정육면체는 4겹 대칭이라 90° 주기(차수 4의 배수), 2엽 프로펠러는 180° 주기 "
                        "(차수 2의 배수)다. 파형 상관이 낮으면 정합필터가 둘을 구별한다는 뜻이다."))

    # Q3 — 같은 운동학에서 형상이 값어치가 있나
    q3 = {}
    for key in DRONE_KEYS:
        q3[key] = dict(
            paired_cube_minus_rigidmesh=J["paired_arm_difference"]["values"].get(
                f"{key}|cube_eqvol - mesh_rigid_spin_pec"),
            paired_cube_minus_mesh=J["paired_arm_difference"]["values"].get(
                f"{key}|cube_eqvol - mesh"),
            corr_rigidmesh_vs_cube=J["waveform_correlation"]["values"].get(
                f"{key}|mesh_rigid_spin_pec vs cube_eqvol"))
    F["q3_shape_value_under_identical_kinematics"] = dict(
        question_ko=("같은 운동학(온몸 회전)에서 진짜 형상과 정육면체가 얼마나 다른가 — "
                     "이것이 «형상 정밀도의 값어치» 를 이 단에서 재는 가장 공정한 자다"),
        values=q3,
        how_to_read_ko=("⛔ 부호를 미리 정하지 말 것. frac_positive 가 0.5 근처면 «차이 없음»(자세를 "
                        "바꾸면 부호가 뒤집힌다), 1.00 이면 «어느 자세에서도 한 방향» 이다. "
                        "차이가 작게 나오면 그것이 더 중요한 결과다 — 마이크로도플러에서도 형상 "
                        "정밀도가 값어치가 없다는 뜻이 되고, 방향을 다시 잡아야 한다."))

    # Q4 — 이 단의 함의
    F["q4_implication"] = dict(
        question_ko="이 단이 사다리에서 뜻하는 것",
        mechanism_identity=J["mechanism_identity"]["values"],
        statement_ko=("⭐⭐ 온몸 회전 프리미티브(구·정육면체)의 마이크로도플러는 **그 물체의 정적 방위 "
                      "패턴을 회전 속도로 읽은 것**과 부동소수 오차까지 같다(mechanism_identity). "
                      "그래서 구는 0 이고 정육면체는 0 이 아니지만, 정육면체가 내는 것도 **새 정보 축이 "
                      "아니라 이미 RCS 쪽에서 재던 ε(방위 산포) 축**이다. "
                      "진짜 드론은 몸통이 돌지 않고 프로펠러만 도니까 블레이드 변조는 몸통 방위 패턴과 "
                      "독립인 **다른 축**이다 — 프리미티브 가족이 구조적으로 낼 수 없는 축이 여기다."),
        caveat_ko=("⚠ 이것은 «형상 정밀도가 값어치 있다» 와 같은 말이 아니다. 블레이드가 있다는 사실만 "
                   "있으면 되는지(회전 평판이면 충분한지), 아니면 진짜 블레이드 형상까지 필요한지는 "
                   "base 의 slab 대조와 이 단의 q3 가 따로 답한다."),
        rcs_axis=J.get("rcs_axis_crosslink", {}))
    return F


# --------------------------------------------------------------------------- #
#  그림 (그림 안 글씨는 전부 영어 — 저장소 규약)
# --------------------------------------------------------------------------- #
def make_figure(J, tabs_new, tabs_base, tabs_hi_new, tabs_base_hi, proto):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import gridspec

    plt.rcParams.update({"figure.facecolor": "white", "savefig.facecolor": "white",
                         "axes.grid": True, "grid.alpha": 0.25, "font.size": 8.5})
    C_CUBE, C_MESH, C_SPH, C_RIG = "#c62828", "#1565c0", "#9e9e9e", "#2e7d32"

    fig = plt.figure(figsize=(15.5, 10.0))
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.26,
                           left=0.055, right=0.985, top=0.925, bottom=0.055)
    fig.suptitle("report16 rung — equal-volume CUBE micro-Doppler vs the real CAD drone "
                 "(same spin axis, same rpm, same phase grid)", fontsize=12.5, y=0.975)

    def get(key, arm, wf="spherical"):
        return tabs_base.get(f"{key}|{arm}|{wf}", tabs_new.get(f"main|{key}|{arm}|{wf}"))

    # (a,b) 회전각에 따른 AC 포락선
    for c, key in enumerate(DRONE_KEYS):
        ax = fig.add_subplot(gs[0, c])
        S = proto[key]["n_phase"]
        ph = np.arange(S) * 360.0 / S
        for arm, col, lab in (("mesh", C_MESH, "CAD drone (rotors only)"),
                              ("cube_eqvol", C_CUBE, "equal-volume cube (whole body)"),
                              ("mesh_rigid_spin_pec", C_RIG, "CAD drone, rigid whole-body spin"),
                              ("sphere", C_SPH, "equal-volume sphere")):
            T = get(key, arm)
            if T is None:
                continue
            e = np.abs(T[0] - T[0].mean())
            #  ⭐ 기준은 그 모델 자신의 DC(동체) 성분 — 그래야 «변조 깊이» 를 모델끼리 비교할 수 있다
            e = 20 * np.log10(np.maximum(e, 1e-300) / max(abs(T[0].mean()), 1e-300))
            ax.plot(ph, e, color=col, lw=1.1, label=lab)
        for x in (90, 180, 270):
            ax.axvline(x, color="0.6", lw=0.7, ls=":")
        ax.axhline(0, color="0.35", lw=0.8)
        ax.set_xlim(0, 360)
        ax.set_ylim(-120, 15)
        ax.set_xticks([0, 90, 180, 270, 360])
        ax.set_xlabel("rotation angle [deg]")
        ax.set_ylabel("|AC field| [dB rel. own DC / body term]")
        ax.set_title(f"{key} — modulation vs rotation angle (az 0 deg, 3.5 GHz)", fontsize=9)
        if c == 0:
            ax.legend(fontsize=6.6, loc="lower right", framealpha=0.9)

    # (c) 예측 채점표
    ax = fig.add_subplot(gs[0, 2])
    ax.axis("off")
    sc = J["prediction_scorecard"]
    lines = ["PRE-REGISTERED PREDICTIONS (written before any field computation)",
             f"sha256 {J['prediction_preregistered']['sha256'][:24]}...",
             f"written {J['prediction_preregistered']['written_at']}  ->  "
             f"compute {J['prediction_preregistered']['compute_started_at']}", ""]
    hb = sc.get("hi_band", {})
    for key in DRONE_KEYS:
        lines.append(f"[{key}]                       3.5GHz   15.86GHz")
        for pk, pv in sc.get(key, {}).items():
            if not isinstance(pv, dict):
                continue
            hv = hb.get(key, {}).get(pk, {}).get("verdict", "-")
            lines.append(f"   {pk[:26]:26s} {pv['verdict']:6s}  {hv}")
    su = sc["_summary"]
    lines += ["", f"3.5 GHz: passed {su['n_pass']} / {su['n_total']}"]
    if hb.get("_summary"):
        lines += [f"15.86 GHz: passed {hb['_summary']['n_pass']} / {hb['_summary']['n_total']}"]
    ax.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=7.4, family="monospace",
            transform=ax.transAxes)
    ax.set_title("prediction scorecard", fontsize=9)

    # (d,e) 선 스펙트럼
    for c, key in enumerate(DRONE_KEYS):
        ax = fig.add_subplot(gs[1, c])
        S = proto[key]["n_phase"]
        m = np.arange(S // 2 + 1)
        for arm, col, lab, off in (("mesh", C_MESH, "CAD drone (rotors only)", 0.0),
                                   ("cube_eqvol", C_CUBE, "equal-volume cube", 0.28),
                                   ("sphere", C_SPH, "equal-volume sphere (floor)", -0.28)):
            T = get(key, arm)
            if T is None:
                continue
            cf = np.fft.fft(T[0]) / S
            P = np.abs(cf) ** 2
            mm = np.fft.fftfreq(S, d=1.0 / S).astype(int)
            opw = np.zeros(S // 2 + 1)
            np.add.at(opw, np.abs(mm), P)
            ref = opw[0]                       # ⭐ 그 모델 자신의 DC(동체) 선을 기준으로
            db = 10 * np.log10(np.maximum(opw, 1e-300) / max(ref, 1e-300))
            ax.vlines(m + off, -130, db, color=col, lw=1.0, label=lab)
        bc = J["prediction_preregistered"]["geometry_only_predictions"][key]["main"]
        ax.axvline(bc["beta_cube_predicted"], color=C_CUBE, ls="--", lw=1.0)
        ax.axvline(bc["beta_blade"], color=C_MESH, ls="--", lw=1.0)
        ax.text(bc["beta_cube_predicted"], 4, r" $\beta_{cube}$", color=C_CUBE, fontsize=7)
        ax.text(bc["beta_blade"], -8, r" $\beta_{blade}$", color=C_MESH, fontsize=7)
        ax.set_xlim(-0.6, min(S // 2, max(28, 1.6 * bc["beta_blade"])))
        ax.set_ylim(-130, 12)
        ax.set_xlabel("harmonic order m  (Doppler = m x f_rot)")
        ax.set_ylabel("line power [dB rel. own DC / body line]")
        ax.set_title(f"{key} — line spectrum: cube comb sits on multiples of 4", fontsize=9)
        if c == 0:
            ax.legend(fontsize=6.6, loc="upper right", framealpha=0.9)

    # (f) 차수 나머지별 전력 몫
    ax = fig.add_subplot(gs[1, 2])
    arms = ["mesh", "cube_eqvol", "mesh_rigid_spin_pec", "sphere"]
    albl = ["CAD\n(rotors)", "cube\n(rigid)", "CAD\n(rigid)", "sphere"]
    w = 0.36
    xs = np.arange(len(arms))
    for i, key in enumerate(DRONE_KEYS):
        v0 = [J["arms"][key].get(x, {}).get("spherical", {}).get("comb", {})
              .get("frac_mod4_0", {}).get("mean", np.nan) for x in arms]
        v2 = [J["arms"][key].get(x, {}).get("spherical", {}).get("comb", {})
              .get("frac_mod4_2", {}).get("mean", np.nan) for x in arms]
        ax.bar(xs + (i - 0.5) * w, v0, w * 0.92, color=("#1565c0" if i == 0 else "#2e7d32"),
               alpha=0.85, label=f"{DRONE_KEYS[i]}: orders m=4,8,12,... (90 deg period)")
        ax.bar(xs + (i - 0.5) * w, v2, w * 0.92, bottom=v0,
               color=("#1565c0" if i == 0 else "#2e7d32"), alpha=0.35, hatch="//",
               label=f"{DRONE_KEYS[i]}: orders m=2,6,10,... (180 deg period)")
    ax.set_xticks(xs)
    ax.set_xticklabels(albl, fontsize=7.5)
    ax.set_ylabel("fraction of AC power")
    ax.set_ylim(0, 1.05)
    ax.set_title("where the AC power sits (order residue mod 4)", fontsize=9)
    ax.legend(fontsize=6.0, loc="lower left", framealpha=0.9)

    # (g) 기계적 항등식
    ax = fig.add_subplot(gs[2, 0])
    key = DRONE_KEYS[-1]
    Tst = tabs_new.get(f"main|{key}|cube_eqvol|static_az")
    Trt = tabs_new.get(f"main|{key}|cube_eqvol|spherical")
    if Tst is not None and Trt is not None:
        S = Tst.shape[1]
        ph = np.arange(S) * 360.0 / S
        lam = R.C0 / R.FC_MAIN
        st = 10 * np.log10((4 * np.pi / lam ** 2) * np.abs(Tst[0][(-np.arange(S)) % S]) ** 2)
        rt = 10 * np.log10((4 * np.pi / lam ** 2) * np.abs(Trt[0]) ** 2)
        ax.plot(ph, st, color="#000000", lw=2.6, alpha=0.28,
                label="static cube, azimuth cut  g(-phi)")
        ax.plot(ph, rt, color=C_CUBE, lw=1.0, label="spinning cube, phase table E(phi)")
        ax.set_xlim(0, 360)
        ax.set_xticks([0, 90, 180, 270, 360])
        ax.set_xlabel("rotation angle / azimuth [deg]")
        ax.set_ylabel("sigma [dBsm]")
        rel = J["mechanism_identity"]["values"].get(f"{key}|cube_eqvol", {}).get("max_rel", np.nan)
        ax.set_title(f"{key} — spinning == static azimuth pattern (max rel {rel:.1e})", fontsize=9)
        ax.legend(fontsize=6.8, loc="lower right", framealpha=0.9)

    # (h) 지표 막대
    ax = fig.add_subplot(gs[2, 1])
    mets = ["flash_contrast_db", "n_eff_orders", "in_band_ac_over_dc_db"]
    mlab = ["flash contrast\n[dB]", "n_eff orders\n[count]", "in-band AC/DC\n[dB]"]
    xs = np.arange(len(mets))
    cols = {"mesh": C_MESH, "cube_eqvol": C_CUBE, "mesh_rigid_spin_pec": C_RIG, "sphere": C_SPH}
    key = DRONE_KEYS[-1]
    w = 0.2
    LO, HI = -42.0, 26.0
    for i, arm in enumerate(arms):
        v = [J["arms"][key].get(arm, {}).get("spherical", {}).get("per_az", {})
             .get(x, {}).get("mean", np.nan) for x in mets]
        ax.bar(xs + (i - 1.5) * w, np.clip(v, LO, HI), w * 0.9, color=cols[arm], alpha=0.9,
               label=albl[i].replace("\n", " "))
        for xx, vv in zip(xs + (i - 1.5) * w, v):          # 잘린 막대는 실제 값을 적어 준다
            if np.isfinite(vv) and vv < LO:
                ax.annotate(f"{vv:.0f}", (xx, LO), ha="center", va="bottom", fontsize=6.2,
                            rotation=90, color="0.15")
    ax.axhline(0, color="0.4", lw=0.8)
    ax.set_ylim(LO, HI)
    ax.set_xticks(xs)
    ax.set_xticklabels(mlab, fontsize=7.5)
    ax.set_title(f"{key} — headline metrics by target model", fontsize=9)
    ax.legend(fontsize=6.6, framealpha=0.9)

    # (i) 기하 요약
    ax = fig.add_subplot(gs[2, 2])
    ax.axis("off")
    rows = ["EQUAL-VOLUME CONSTRUCTION (all computed, nothing typed in)", ""]
    for key in DRONE_KEYS:
        e = J["equal_volume_construction"]["values"][key]
        rows += [f"[{key}]",
                 f"  drone solid volume   {e['drone_solid_volume_m3']*1e3:9.4f} L",
                 f"  cube side a=V^(1/3)  {e['cube_side_m']*1e3:9.2f} mm   "
                 f"(a/lambda={e['cube_side_over_lambda_main']:.2f} @3.5GHz)",
                 f"  sphere radius        {e['sphere_r_equal_volume_m']*1e3:9.2f} mm",
                 f"  cube corner radius   {e['rmax_inplane_cube_m']*1e3:9.2f} mm  (a/sqrt2)",
                 f"  prop tip radius      {e['prop_tip_radius_m']*1e3:9.2f} mm",
                 f"  volume ratio cube    {e['cube_volume_ratio']:9.6f}",
                 f"  cube/sphere area     {e['cube_over_sphere_area']:9.4f}", ""]
    ax.text(0.0, 1.0, "\n".join(rows), va="top", ha="left", fontsize=7.0,
            family="monospace", transform=ax.transAxes)
    ax.set_title("geometry", fontsize=9)

    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=155)
    plt.close(fig)
    return os.path.relpath(OUT_FIG, ROOT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compute", action="store_true")
    ap.add_argument("--no-hi", action="store_true")
    a = ap.parse_args()
    main(skip_compute=a.skip_compute, with_hi=not a.no_hi)
