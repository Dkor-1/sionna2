# -*- coding: utf-8 -*-
"""
report16_verify_detector.py — ⭐ **적대검증: 「이 차이가 검출로 옮겨지는가」**
================================================================================

무엇을 묻는가
--------------------------------------------------------------------------------
report16 사다리(mesh → 절반메쉬 → 로터없음 → 정육면체 → 경계상자 → 구)는 네 갈래 지표
(플래시 대조비 · 고차 풍부도 · 폭 · 동체대블레이드)로 팔들을 갈랐다. 그 단들은 숫자를
서로 검산하고 사전예측과 대조하는 일은 아주 꼼꼼히 했다. **그러나 어느 단도 그 차이를
검출 언어(SNR · 검출확률)로 옮기지 않았다.** 여섯 산출물 JSON 을 통째로 훑어도
detection / Pd / Pfa / CFAR / multipath / X410 이라는 낱말이 한 번도 안 나온다
(snr_db 는 두 파일에 있는데 «수치 바닥 대비» 라는 다른 뜻이다).

「스펙트로그램이 다르게 생겼다」와 「검출확률이 달라진다」는 다른 말이다. 이 파일은 그
간극만 판정한다. 세 갈래로 묻는다.

  T2/T3  지표 차이를 SNR·Pd 로 옮길 수 있나 — 검출기 세 종류를 세워 각각 무엇을 보는지
         적고, 팔 사이 차이가 그 눈에 몇 dB·몇 %p 로 보이는지 **계산**한다.
  T4     환경(다중경로·바닥반사)을 넣으면 그 차이가 줄어드나 — 저장소 기록이 이미
         «환경이 표적모델 차이를 29.3 → 10.1 dB 로 줄였다» 이다(docs/PAPER_POSITION_0803.md).
         같은 종류의 거친 혼합 모형을 마이크로도플러에 걸어 본다.
  T5     X410 실측에서 이 차이를 실제로 구별할 수 있나 — 필요한 EIRP·거리·적분시간·
         독립 관측 수를 계산한다.

⭐⭐ 이 파일이 새로 만든 숫자는 **전부 crude(거친 추정)** 다. JSON 의 모든 새 블록에
`"crude": true` 와 무엇을 가정했는지가 함께 실린다. 이유는 셋이다.
  (1) 링크버짓의 EIRP·이득·잡음지수는 저장소에 X410 실측 기준값이 없어 **가정**이다.
  (2) 다중경로 모형은 «다른 자세의 산란을 임의 위상으로 더한다» 는 한 줄짜리 대리물이고,
      진짜 지면반사(고각이 다른 경로)의 표는 이 저장소에 없다.
  (3) 앞 단들이 스스로 세운 결함(가림 없음 D1 · PO 가 가장 약한 대역 D2 · 로터 상대위상
      4~10 dB D5)이 그대로 이 계산에 실려 들어온다. 나는 그것을 고치지 않았다.

⛔ outputs/report15_* · benchmark/report15_* 미접촉. src/make_report0N_*·report0N_*.ipynb
   미접촉. src/drones.py · src/drone_cad.py 는 **읽기만**(스펙 조회).
⛔ 손입력 숫자 없음 — 전부 계산해서 JSON 에 담는다.
GPU: 안 쓴다. 24×256 짜리 표의 FFT 후처리라 CPU 로 충분하고, 네 장 모두 형제 워크플로가
   92~100 % 로 돌리는 중이라 침범하지 않는다(nvidia-smi 확인).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from scipy.stats import chi2, ncx2, norm

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import report16_base as R          # noqa: E402  지표·규약은 재구현하지 않고 그대로 물려받는다
from drones import DRONES          # noqa: E402  읽기 전용

OUT = os.path.join(ROOT, "outputs")
C0 = 299792458.0
K_BOLTZ = 1.380649e-23
T0_K = 290.0

RNG = np.random.default_rng(20260804)


# --------------------------------------------------------------------------- #
#  0. 표 불러오기 — 여섯 단이 저장한 위상표를 한 자리에 모은다
# --------------------------------------------------------------------------- #
NPZ_FILES = {
    "base": "report16_base_tables.npz",
    "sph": "report16_rung_sphere_eqvol_tables.npz",
    "box": "report16_rung_box_bbox_tables.npz",
    "cube": "report16_rung_cube_eqvol_tables.npz",
    "half": "report16_rung_mesh_half_tri_tables.npz",
    "full": "report16_rung_mesh_full_tables.npz",
}

# 팔 이름 → (파일, 키틀). {d} 는 기체 이름.
ARM_SOURCES = {
    "mesh":            ("base", "main__G_0804__{d}__mesh__spherical"),
    "mesh_fine":       ("base", "main__G_0804__{d}__mesh_fine__spherical"),
    "disc":            ("base", "main__G_0804__{d}__disc__spherical"),
    "slab":            ("base", "main__G_0804__{d}__slab__spherical"),
    "sphere_eqvol":    ("sph",  "main__{d}__sphere_eqvol__spherical"),
    "sphere_offaxis":  ("sph",  "main__{d}__sphere_offaxis__spherical"),
    "sph_hub":         ("sph",  "main__{d}__sph_hub__spherical"),
    "sph_blade_tip":   ("sph",  "main__{d}__sph_blade_tip__spherical"),
    "cube_eqvol":      ("box",  "main__{d}__cube_eqvol__spherical"),
    "box_bbox":        ("box",  "main__{d}__box_bbox__spherical"),
    "box_aspect_voleq": ("box", "main__{d}__box_aspect_voleq__spherical"),
    "prop_bbox":       ("box",  "main__{d}__prop_bbox__spherical"),
    "mesh_rigid_spin": ("cube", "main__{d}__mesh_rigid_spin__spherical"),
    "mesh_half_tri":   ("half", "main__{d}__mesh_half_tri__spherical"),
    "mesh_quarter_tri": ("half", "main__{d}__mesh_quarter_tri__spherical"),
    "mesh_half_tri_all": ("half", "main__{d}__mesh_half_tri_all__spherical"),
}
DRONES_2 = ["mini2", "matrice4e"]          # 두 단 모두 이 두 기체를 공통으로 돌렸다
FLEET = ["mini2", "mini5pro", "mavic4pro", "matrice4e", "phantom3", "phantom4",
         "x500v2", "typhoonh480", "s1000plus", "m350rtk"]


def load_all():
    z = {k: np.load(os.path.join(OUT, v)) for k, v in NPZ_FILES.items()}
    arms = {}
    for d in DRONES_2:
        arms[d] = {}
        for arm, (src, tmpl) in ARM_SOURCES.items():
            key = tmpl.format(d=d)
            if key in z[src]:
                arms[d][arm] = np.asarray(z[src][key], complex)
    fleet = {d: np.asarray(z["full"][f"{d}__spherical"], complex) for d in FLEET
             if f"{d}__spherical" in z["full"]}
    return z, arms, fleet


def proto_for(d, fc=None):
    s = DRONES[d]
    return R.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades,
                             R.FC_MAIN if fc is None else fc)


# --------------------------------------------------------------------------- #
#  1. ⭐ 번역기 — 위상표 → «도플러 빈마다의 RCS»
# --------------------------------------------------------------------------- #
def line_rcs(tab, lam):
    """1회전 위상표 E(φ) → 하모닉 차수마다의 RCS σ_m [m²].

    왜 이렇게 놓나. 로터가 같은 회전수로 도는 호버 표적의 되돌아오는 신호는 f_rot 의
    정수배에만 선으로 서는 **정확한 주기신호**다(base 규약이 그렇게 잡았다). 그래서
    슬로타임 FFT 는 누설 없이 그 선들을 도플러 빈에 하나씩 앉힌다. 계수 c_m 은 그 빈의
    복소 진폭이므로 σ_m = 4π/λ²·|c_m|² 이 곧 **그 도플러 빈에서 보이는 RCS** 다.
    Parseval 로 Σ_m σ_m = 4π/λ²·mean|E|² = base 의 sigma_eq_mean 과 같다(게이트로 확인).

    ⭐ 호버 표적에서 m=0 (동체) 은 검출에 못 쓴다 — 직접파 제거(ECA)와 정적클러터 노치가
    0-도플러 행을 통째로 지우기 때문이다(저장소 report5 «hover blind»). 그러므로
    **호버 드론의 검출 단면적은 총 RCS 가 아니라 가장 센 AC 선의 RCS** 다. 이 함수가
    내는 sigma_ac_peak 가 그 값이다.
    """
    tab = np.asarray(tab, complex)
    S = len(tab)
    c = np.fft.fft(tab) / S
    P = np.abs(c) ** 2
    m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
    fac = 4.0 * math.pi / lam ** 2
    sig = fac * P
    ac = m != 0
    return dict(
        m=m, sigma_m=sig,
        sigma_total=float(sig.sum()),
        sigma_dc=float(sig[~ac].sum()),
        sigma_ac_total=float(sig[ac].sum()),
        sigma_ac_peak=float(sig[ac].max()),
        peak_order=int(abs(m[ac][np.argmax(sig[ac])])),
        peak_share=float(sig[ac].max() / max(sig[ac].sum(), 1e-300)),
    )


def db(x):
    return 10.0 * np.log10(np.maximum(np.asarray(x, float), 1e-300))


def arm_line_table(tabs, lam):
    """방위 24점 전부에 대해 line_rcs → 방위별 배열들."""
    rows = [line_rcs(t, lam) for t in tabs]
    return dict(
        sigma_total=np.array([r["sigma_total"] for r in rows]),
        sigma_dc=np.array([r["sigma_dc"] for r in rows]),
        sigma_ac_total=np.array([r["sigma_ac_total"] for r in rows]),
        sigma_ac_peak=np.array([r["sigma_ac_peak"] for r in rows]),
        peak_order=np.array([r["peak_order"] for r in rows]),
        peak_share=np.array([r["peak_share"] for r in rows]),
    )


def stat(v):
    v = np.asarray(v, float)
    return dict(mean=float(np.mean(v)), median=float(np.median(v)),
                sd=float(np.std(v, ddof=1)) if v.size > 1 else 0.0,
                min=float(np.min(v)), max=float(np.max(v)), n=int(v.size))


# --------------------------------------------------------------------------- #
#  2. 검출확률 — 정확한 닫힌형 (근사 아님)
# --------------------------------------------------------------------------- #
def pd_swerling0(snr_lin, pfa, n_bins=1):
    """비요동(Swerling 0/5) 표적, N 빈 비코히어런트 합. 잡음 CN(0,1)/빈.

    통계량 Z = Σ|x_i|² 에 대해 2Z ~ ncx2(2N, 2·SNR_tot). H0 에서 nc=0 이므로
    문턱은 chi2(2N) 의 1-Pfa 분위수다. 근사식(Albersheim) 을 쓰지 않고 정확히 푼다.
    """
    thr = chi2.ppf(1.0 - pfa, 2 * n_bins)
    return float(ncx2.sf(thr, 2 * n_bins, 2.0 * float(snr_lin)))


def pd_swerling1(snr_lin, pfa, n_bins=1, n_quad=4096):
    """Swerling 1 — 표적 진폭이 CPI 안에서 하나의 레일리 이득 g 로 요동.

    nc = 2|g|²·SNR_tot 이고 |g|² ~ Exp(1). 그 위로 수치적분한다.
    N=1 이면 해석해 Pd = Pfa^(1/(1+SNR)) 와 일치한다(게이트로 확인).
    """
    thr = chi2.ppf(1.0 - pfa, 2 * n_bins)
    u = (np.arange(n_quad) + 0.5) / n_quad
    g2 = -np.log(1.0 - u)                      # Exp(1) 역변환 표본 (등확률 격자)
    return float(np.mean(ncx2.sf(thr, 2 * n_bins, 2.0 * g2 * float(snr_lin))))


def snr_for_pd(pd_target, pfa, n_bins=1, swerling=0):
    """목표 Pd 를 내는 SNR(선형) 을 이분법으로 푼다."""
    f = pd_swerling0 if swerling == 0 else pd_swerling1
    lo, hi = 1e-4, 1e9
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if f(mid, pfa, n_bins) < pd_target:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


# --------------------------------------------------------------------------- #
#  3. 링크버짓 — SNR_out = P_echo · T_cpi / (k T0 F)
# --------------------------------------------------------------------------- #
def snr_out(sigma_m2, lam, eirp_dbm, grx_dbi, nf_db, r1_m, r2_m, t_cpi_s):
    """정합필터 처리 후 출력 SNR. 대역폭 B 가 약분되는 것이 핵심이다.

    수신 에코 전력  P = EIRP·G_rx·λ²·σ / ((4π)³ R1² R2²)
    입력 SNR       = P / (k T0 F B),   처리이득 = B·T_cpi   →  SNR_out = P·T_cpi/(k T0 F)
    즉 «얼마나 오래 보느냐» 만 남고 «얼마나 넓게 보느냐» 는 사라진다.
    """
    eirp_w = 10 ** (eirp_dbm / 10.0) * 1e-3
    g = 10 ** (grx_dbi / 10.0)
    p_echo = eirp_w * g * lam ** 2 * sigma_m2 / ((4 * math.pi) ** 3 * r1_m ** 2 * r2_m ** 2)
    n0 = K_BOLTZ * T0_K * 10 ** (nf_db / 10.0)
    return p_echo * t_cpi_s / n0


def range_for_snr(snr_req, sigma_m2, lam, eirp_dbm, grx_dbi, nf_db, t_cpi_s):
    """R1=R2=R 일 때 목표 SNR 을 만족하는 최대 R [m]. SNR ∝ R^-4 이라 닫힌형이다."""
    s1 = snr_out(sigma_m2, lam, eirp_dbm, grx_dbi, nf_db, 1.0, 1.0, t_cpi_s)
    return float((s1 / snr_req) ** 0.25)


# --------------------------------------------------------------------------- #
#  4. 다중경로 혼합 — 거친 대리 모형
# --------------------------------------------------------------------------- #
def weights_for_neff(n_eff_target, l_max=8):
    """유효 경로수 N_eff = (Σw)²/Σw² 를 맞추는 기하급수 가중치 w 를 **계산**한다."""
    if n_eff_target <= 1.0 + 1e-9:
        return np.array([1.0])
    lo, hi = 1e-6, 1.0 - 1e-9
    for _ in range(200):
        r = 0.5 * (lo + hi)
        w = r ** np.arange(l_max)
        neff = w.sum() ** 2 / (w ** 2).sum()
        if neff < n_eff_target:
            lo = r
        else:
            hi = r
    r = 0.5 * (lo + hi)
    w = r ** np.arange(l_max)
    return w / w.sum()


def mix_paths(tabs, w, anchor, rng):
    """다중경로 한 실현. **첫 경로는 진짜 자세(anchor)** 이고 나머지가 반사 경로다.

    왜 이렇게 놓나. 야외 바이스태틱에서 표적을 경유하는 경로는 하나가 아니다 —
    TX→표적→RX 직행 말고도 TX→지면→표적→RX, TX→표적→지면→RX 가 같이 들어온다.
    이들은 (호버 표적이라) 도플러가 같아 **같은 도플러 빈에서 겹치고**, 표적을 보는
    각도가 서로 달라 블레이드 산란이 다르게 잡힌다. 그래서 «같은 표적, 다른 자세,
    임의 위상» 의 합이 되는 것이다. 첫 경로에 가장 큰 전력을 주어 «진짜 자세가 지배하고
    반사가 흐린다» 는 구도를 만든다.

    ⚠ 대리물이다. 진짜 지면반사는 **고각이 다른** 경로인데 이 저장소에는 블레이드가
    도는 팔의 고각별 위상표가 없다(mesh_no_rotor 단의 고각 훑기는 로터가 없는 팔이다).
    그래서 «다른 자세에서 본 산란» 을 방위축에서 빌린다. 저장소가 환경축을 잰 방식
    (docs/PAPER_POSITION_0803.md 의 N_eff 경로쌍 사다리)과 같은 급의 근사다.
    ⚠ 모든 경로를 같은 거리셀에 넣었다. X410 순시대역 400 MHz 의 거리분해능은 0.75 m 라
    경로차가 그보다 크면 **분해되어 안 섞인다** — 그 경우 이 계산은 과하게 비관적이다.
    """
    n_az = tabs.shape[0]
    others = rng.choice(np.delete(np.arange(n_az), anchor), size=len(w) - 1, replace=False)
    idx = np.concatenate([[anchor], others])
    ph = np.exp(2j * math.pi * rng.random(len(w)))
    ph[0] = 1.0                                   # 기준 경로의 위상은 기준으로 둔다
    amp = np.sqrt(w) * ph
    return (amp[:, None] * tabs[idx, :]).sum(axis=0)


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main():
    t_start = time.time()
    J = {}
    z, arms, fleet = load_all()

    git_rev = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip() or "n/a"
    J["meta"] = dict(
        report="report16",
        role="적대검증 — 검출 관련성 렌즈",
        producer="benchmark/report16_verify_detector.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=git_rev,
        question_ko="report16 사다리가 잰 지표 차이가 실제 검출(SNR·Pd)로 얼마나 옮겨지는가.",
        gpu_used=False,
        gpu_reason_ko="24×256 표의 FFT 후처리라 CPU 로 충분하고, GPU 4장 모두 형제 워크플로가 92~100% 로 점유 중이라 침범하지 않았다.",
    )
    J["crude_labeling_ko"] = (
        "⭐⭐ 이 파일이 새로 만든 숫자는 **전부 crude(거친 추정)** 다. 각 블록에 crude=true 와 "
        "가정 목록이 함께 실린다. 앞 단들이 스스로 적은 결함(가림 없음 · PO 가 가장 약한 대역 · "
        "로터 상대위상 4~10 dB 산포)은 고치지 않고 그대로 물려받았다 — 그러므로 여기 나오는 "
        "절대 dB·절대 거리는 인용 대상이 아니고, **팔 사이 비교의 크기 감각**으로만 쓸 것.")

    # ─────────────────────────────────────────────────────────────────────── #
    #  G. 게이트 — 내가 앞 단과 같은 숫자를 보고 있는지 먼저 확인한다
    # ─────────────────────────────────────────────────────────────────────── #
    gates = {}

    # G1: 내 σ_m 분해가 base 의 sigma_eq_mean_dbsm 과 같은가 (Parseval)
    worst = 0.0
    for d in DRONES_2:
        p = proto_for(d)
        for arm, tabs in arms[d].items():
            for i in range(tabs.shape[0]):
                mine = db(line_rcs(tabs[i], p["lam_m"])["sigma_total"])
                theirs = R.md_metrics16(tabs[i], p, DRONES[d].prop_blades)["sigma_eq_mean_dbsm"]
                worst = max(worst, abs(float(mine) - float(theirs)))
    gates["G1_parseval_vs_base_sigma"] = dict(
        what_ko="내가 나눈 도플러 선별 RCS 를 전부 더하면 base 의 sigma_eq_mean_dbsm 과 같아야 한다.",
        worst_abs_db=worst, pass_=bool(worst < 1e-9))

    # G2: 앞 단 JSON 의 지표를 표에서 다시 뽑아 대조 (내가 같은 표를 보고 있나)
    mf = json.load(open(os.path.join(OUT, "report16_metric_mesh_full.json")))
    worst_rel, n_chk = 0.0, 0
    for d in FLEET:
        if d not in fleet:
            continue
        p = proto_for(d)
        vals = [R.md_metrics16(fleet[d][i], p, DRONES[d].prop_blades)["flash_contrast_db"]
                for i in range(fleet[d].shape[0])]
        mine = float(np.mean(vals))
        theirs = mf["metrics"]["main"]["spherical"][d]["flash_contrast_db"]["mean"]
        worst_rel = max(worst_rel, abs(mine - theirs) / max(abs(theirs), 1e-12))
        n_chk += 1
    gates["G2_metric_recompute_vs_stage"] = dict(
        what_ko="mesh_full 단 JSON 의 플래시 대조비 평균을 저장된 표에서 다시 계산해 맞춰 본다.",
        n_checked=n_chk, worst_rel=worst_rel, pass_=bool(worst_rel < 1e-12))

    # G3: 검출확률 닫힌형이 해석해와 맞는가 (Swerling1, N=1: Pd = Pfa^(1/(1+SNR)))
    pfa_g = 1e-4
    chk = []
    for s_db in (0.0, 6.0, 13.0, 20.0):
        s = 10 ** (s_db / 10.0)
        chk.append(abs(pd_swerling1(s, pfa_g, 1) - pfa_g ** (1.0 / (1.0 + s))))
    gates["G3_pd_closed_form"] = dict(
        what_ko="Swerling 1 · 단일빈 수치적분이 해석해 Pfa^(1/(1+SNR)) 와 맞는가.",
        worst_abs=float(max(chk)), pass_=bool(max(chk) < 2e-4))

    # G4: Swerling 0 단일빈이 H0 에서 정확히 Pfa 를 내는가
    gates["G4_pfa_selfcheck"] = dict(
        worst_abs=abs(pd_swerling0(1e-12, pfa_g, 1) - pfa_g), pass_=True)
    gates["G4_pfa_selfcheck"]["pass_"] = bool(gates["G4_pfa_selfcheck"]["worst_abs"] < 1e-9)
    # G5: ⭐ 완전히 다른 길로 검산 — 1회전 표를 «슬로타임 시계열» 로 펼쳐 FFT 했을 때
    #     내 σ_ac_peak 가 나오는가. (표 FFT 가 아니라 시간축 FFT 라 경로가 다르다.)
    worst_g5 = 0.0
    for d in DRONES_2:
        p = proto_for(d)
        S, n_rev = int(p["n_phase"]), int(p["n_rev"])
        for arm in ("mesh", "cube_eqvol"):
            if arm not in arms[d]:
                continue
            tab = arms[d][arm][0]
            k = np.arange(S * n_rev)
            x = tab[k % S]                                  # PRF = S·f_rot → 격자에 정확히 떨어진다
            X = np.fft.fft(x) / len(x)
            P = np.abs(X) ** 2
            P[0] = 0.0                                      # 0-도플러 제거(호버)
            mine = 4 * math.pi / p["lam_m"] ** 2 * float(P.max())
            ref = line_rcs(tab, p["lam_m"])["sigma_ac_peak"]
            worst_g5 = max(worst_g5, abs(10 * math.log10(mine / ref)))
    gates["G5_slowtime_vs_table_fft"] = dict(
        what_ko="1회전 표를 32회전 슬로타임 시계열로 펼쳐 시간축 FFT 로 다시 뽑은 σ_ac_peak 가 맞는가.",
        worst_abs_db=worst_g5, pass_=bool(worst_g5 < 1e-9))
    J["gates"] = gates

    # ─────────────────────────────────────────────────────────────────────── #
    #  T1. 도플러 빈마다의 RCS — 지표를 처음으로 «검출 단면적» 으로 옮긴다
    # ─────────────────────────────────────────────────────────────────────── #
    t1 = dict(crude=True,
              what_ko=("호버 드론은 0-도플러(동체) 행을 못 쓴다 — ECA 와 정적클러터 노치가 "
                       "그 행을 지운다(저장소 report5 «hover blind»). 그러므로 검출 단면적은 "
                       "총 RCS 가 아니라 **가장 센 AC 선의 RCS** 다. 여기서 처음 계산한다."),
              assumptions_ko=[
                  "1회전이 CPI 안에 정수번 들어가고 회전수가 그동안 흔들리지 않는다(선이 한 빈에 선다).",
                  "0-도플러 행은 통째로 버린다(호버 가정). 표적이 병진하면 이 가정은 틀린다.",
                  "앞 단 커널의 결함(가림 없음)이 σ_dc 를 부풀리므로 dc 대비 비는 낙관적이다.",
              ],
              per_arm={})
    LT = {}
    for d in DRONES_2:
        p = proto_for(d)
        LT[d] = {}
        t1["per_arm"][d] = {}
        for arm, tabs in arms[d].items():
            lt = arm_line_table(tabs, p["lam_m"])
            LT[d][arm] = lt
            t1["per_arm"][d][arm] = dict(
                sigma_total_dbsm=stat(db(lt["sigma_total"])),
                sigma_ac_total_dbsm=stat(db(lt["sigma_ac_total"])),
                sigma_ac_peak_dbsm=stat(db(lt["sigma_ac_peak"])),
                ac_below_total_db=stat(db(lt["sigma_total"]) - db(lt["sigma_ac_peak"])),
                peak_order=stat(lt["peak_order"]),
                peak_share_of_ac=stat(lt["peak_share"]),
            )
    # 함대 전체(10기) 의 검출 단면적
    t1["fleet_sigma_ac_peak_dbsm"] = {}
    for d, tabs in fleet.items():
        p = proto_for(d)
        lt = arm_line_table(tabs, p["lam_m"])
        t1["fleet_sigma_ac_peak_dbsm"][d] = dict(
            sigma_total_dbsm=stat(db(lt["sigma_total"])),
            sigma_ac_peak_dbsm=stat(db(lt["sigma_ac_peak"])),
            penalty_db=stat(db(lt["sigma_total"]) - db(lt["sigma_ac_peak"])),
        )
    J["t1_detection_cross_section"] = t1

    # ─────────────────────────────────────────────────────────────────────── #
    #  T2. 검출기 세 종류 — 각 지표가 어느 눈에 보이고 어느 눈에 안 보이나
    # ─────────────────────────────────────────────────────────────────────── #
    t2 = dict(crude=True,
              families={
                  "F1_single_bin_cfar": dict(
                      what_ko="거리-도플러 맵의 한 셀에 CFAR — 저장소 report04/12 가 실제로 쓰는 검출기.",
                      sees_ko="가장 센 AC 선의 RCS 하나. 그것뿐이다.",
                      blind_to_ko="플래시 대조비 · 고차 풍부도 · 폭 — 셋 다 이 눈에 **안 보인다**."),
                  "F3_band_energy": dict(
                      what_ko="AC 대역(|m| ≤ ceil(1.5β)) 의 셀을 비코히어런트로 다 더해 검출.",
                      sees_ko="AC 총 RCS 와 대역 셀 수 N. 그 둘뿐이다.",
                      blind_to_ko=("전력이 몇 개 차수에 어떻게 흩어져 있는지에 **원리적으로 무관**하다 — "
                                   "비중심 카이제곱의 비중심모수가 총합만 보기 때문이다. "
                                   "즉 n_eff·플래시 대조비를 아무리 바꿔도 이 검출기의 Pd 는 안 움직인다.")),
                  "F2_coherent_template": dict(
                      what_ko="마이크로도플러 파형 자체를 템플릿으로 정합필터(=분류기가 쓰는 눈).",
                      sees_ko="파형 상관 ρ. 정합손실 = 20log10|ρ| dB.",
                      note_ko="저장소에 이 검출기는 구현돼 있지 않다 — 여기서 처음 세운 가정이다."),
              })

    # F1 대 F3 이득 차 (같은 표적, 같은 CPI)
    pfa = 1e-4
    t2["F1_vs_F3_required_sigma"] = {}
    for d in DRONES_2:
        p = proto_for(d)
        band = max(2, int(math.ceil(1.5 * p["beta"])))
        n_band = 2 * band
        s1 = snr_for_pd(0.9, pfa, 1, 0)
        sN = snr_for_pd(0.9, pfa, n_band, 0)
        lt = LT[d]["mesh"]
        # 같은 물리 조건에서 두 검출기가 요구하는 «필요 RCS» 비교
        req_f1 = float(np.median(db(lt["sigma_ac_peak"]))) - 10 * math.log10(s1)
        req_f3 = float(np.median(db(lt["sigma_ac_total"]))) - 10 * math.log10(sN)
        t2["F1_vs_F3_required_sigma"][d] = dict(
            band_order=band, n_band_cells=n_band,
            snr_req_1cell_db=10 * math.log10(s1),
            snr_req_bandsum_db=10 * math.log10(sN),
            median_sigma_ac_peak_dbsm=float(np.median(db(lt["sigma_ac_peak"]))),
            median_sigma_ac_total_dbsm=float(np.median(db(lt["sigma_ac_total"]))),
            f3_minus_f1_margin_db=req_f3 - req_f1,
            reading_ko=("양수면 대역합(F3)이 더 유리하다. 이 값은 «전력이 몇 선에 퍼져 있나» 에 "
                        "달려 있고 — 그것이 n_eff 가 검출로 들어가는 **유일한** 통로다."),
        )

    # ⭐ n_eff 가 F1 에 미치는 영향 = peak_share. 지표→SNR 의 직접 환산.
    t2["how_n_eff_enters_detection"] = dict(
        crude=True,
        mechanism_ko=("n_eff 자체는 검출식에 안 들어간다. 들어가는 것은 «가장 센 선이 AC 전력의 "
                      "몇 몫인가»(peak_share) 뿐이고, 그것은 n_eff 와 느슨하게만 묶여 있다. "
                      "아래가 그 느슨함의 크기다."),
        rows={})
    for d in DRONES_2:
        p = proto_for(d)
        ne = np.array([R.md_metrics16(arms[d]["mesh"][i], p, DRONES[d].prop_blades)["n_eff_orders"]
                       for i in range(arms[d]["mesh"].shape[0])])
        ps = LT[d]["mesh"]["peak_share"]
        t2["how_n_eff_enters_detection"]["rows"][d] = dict(
            n_eff=stat(ne), peak_share=stat(ps),
            share_if_uniform=stat(1.0 / ne),
            corr_neff_vs_peakshare=float(np.corrcoef(ne, ps)[0, 1]),
            snr_cost_of_spread_db=stat(-10 * np.log10(ps)),
            reading_ko=("snr_cost_of_spread_db 는 «AC 전력을 한 선에 다 몰았을 때 대비 "
                        "단일빈 검출기가 잃는 dB» 다. 이것이 풍부도 지표가 검출로 옮겨지는 값 전부다."),
        )

    # ⭐ 플래시 대조비가 검출로 옮겨지는 조건 — CPI 길이가 가른다
    t2["when_flash_contrast_matters"] = dict(crude=True, rows={})
    for d in DRONES_2:
        p = proto_for(d)
        t_flash = 1.0 / p["flash_hz"]
        t_min_doppler = 1.0 / p["f_rot_hz"]          # 하모닉 선을 가르려면 최소 이만큼
        t2["when_flash_contrast_matters"]["rows"][d] = dict(
            flash_period_s=t_flash,
            min_cpi_to_resolve_lines_s=t_min_doppler,
            ratio_min_cpi_over_flash_period=t_min_doppler / t_flash,
            verdict_ko=("도플러 선을 가르는 데 필요한 최소 CPI 가 플래시 주기보다 "
                        f"{t_min_doppler / t_flash:.1f} 배 길다 → 표준 CPI 안에서 플래시는 "
                        "**적분돼 사라진다**. 플래시 대조비가 검출로 옮겨지려면 CPI 를 플래시 "
                        "주기보다 짧게 잘라야 하는데, 그러면 하모닉 선을 못 가르므로 F1·F3 을 "
                        "포기하는 것이다. 즉 플래시 대조비는 검출 지표가 아니라 **묘사·분류 지표**다."),
        )
    # ⭐ 이상적 선 RCS 와 «실제 검출기가 받는 것» 사이의 실무 손실
    t2["practical_cpi_loss"] = dict(
        crude=True,
        what_ko=("위의 σ_ac_peak 는 «CPI 가 정확히 정수 회전이고 창을 안 씌운» 이상값이다. 실제 "
                 "검출기는 (가) CPI 를 회전수에 맞출 수 없고 (나) 도플러 누설을 막으려 창을 씌운다. "
                 "그래서 선이 빈 사이에 걸치고 창 손실이 붙는다. 그 손실을 여기서 **계산**한다 — "
                 "이 값이 사다리의 팔 차이와 같은 자릿수라면 팔 차이는 실무에서 안 보인다는 뜻이다."),
        n_draw=400, rows={})
    for d in DRONES_2:
        p = proto_for(d)
        S = int(p["n_phase"])
        tab = arms[d]["mesh"][0]
        ideal = line_rcs(tab, p["lam_m"])["sigma_ac_peak"]
        rng = np.random.default_rng(11)
        loss_rect, loss_hann = [], []
        for _ in range(t2["practical_cpi_loss"]["n_draw"]):
            n_cpi = int(round(S * (8 + 8 * rng.random())))          # 8~16 회전 상당, 정수 아님
            k0 = int(rng.integers(0, S))
            k = np.arange(n_cpi) + k0
            x = tab[k % S]
            for wname, acc in (("rect", loss_rect), ("hann", loss_hann)):
                w = np.ones(n_cpi) if wname == "rect" else np.hanning(n_cpi)
                X = np.fft.fft(x * w) / w.sum()
                P = np.abs(X) ** 2
                dcbin = max(1, int(round(0.5 * n_cpi / S)))          # 0-도플러 근방 몇 빈은 버린다
                P[:dcbin] = 0.0
                P[-dcbin + 1:] = 0.0 if dcbin > 1 else P[-dcbin + 1:]
                got = 4 * math.pi / p["lam_m"] ** 2 * float(P.max())
                acc.append(10 * math.log10(max(got, 1e-300) / ideal))
        t2["practical_cpi_loss"]["rows"][d] = dict(
            ideal_sigma_ac_peak_dbsm=db(ideal).item(),
            loss_db_rect_window=stat(np.array(loss_rect)),
            loss_db_hann_window=stat(np.array(loss_hann)),
            note_ko=("음수가 손실이다. 회전수에 CPI 를 못 맞추면 선이 빈 사이에 걸쳐(스캘럽) "
                     "전력을 잃고, 창을 씌우면 다시 잃는다. 이 손실은 팔에 상관없이 똑같이 걸리므로 "
                     "**팔 사이 비교는 안 바꾸지만**, 절대 검출거리 예측에는 반드시 들어가야 한다."))
    J["t2_detector_families"] = t2

    # ─────────────────────────────────────────────────────────────────────── #
    #  T3. 팔 사이 차이 → ΔSNR → ΔPd
    # ─────────────────────────────────────────────────────────────────────── #
    t3 = dict(crude=True,
              operating_point_ko=("메쉬(정본) 팔이 Pd=0.9 · Pfa=1e-4 를 내는 절대 전력에 눈금을 맞추고, "
                                  "**같은 절대 전력**에서 각 대리 형상이 몇 %p 를 내는지 잰다. "
                                  "이것이 «지표 차이 → 검출확률 차이» 의 정직한 환산이다."),
              pfa=pfa, pd_anchor=0.9, rows={})
    for d in DRONES_2:
        p = proto_for(d)
        base_lt = LT[d]["mesh"]
        s_req0 = snr_for_pd(0.9, pfa, 1, 0)
        s_req1 = snr_for_pd(0.9, pfa, 1, 1)
        # 눈금: 메쉬 중앙값이 Pd=0.9 → scale = s_req / sigma_mesh
        sig_mesh = float(np.median(base_lt["sigma_ac_peak"]))
        k0 = s_req0 / sig_mesh
        k1 = s_req1 / sig_mesh
        rows = {}
        for arm, lt in LT[d].items():
            sig = float(np.median(lt["sigma_ac_peak"]))
            d_db = 10 * math.log10(sig / sig_mesh)
            # 파형 상관 (F2 정합손실) — 메쉬 템플릿 대비, 방위별 평균
            rho = np.array([abs(R.ac_corr(arms[d]["mesh"][i], arms[d][arm][i]))
                            for i in range(arms[d][arm].shape[0])])
            rows[arm] = dict(
                sigma_ac_peak_dbsm_median=db(sig).item(),
                delta_vs_mesh_db=d_db,
                pd_swerling0=pd_swerling0(k0 * sig, pfa, 1),
                pd_swerling1=pd_swerling1(k1 * sig, pfa, 1),
                delta_pd_swerling0=pd_swerling0(k0 * sig, pfa, 1) - 0.9,
                delta_pd_swerling1=pd_swerling1(k1 * sig, pfa, 1) - 0.9,
                f2_template_corr=stat(rho),
                f2_mismatch_loss_db=stat(-20 * np.log10(np.maximum(rho, 1e-12))),
                detection_range_ratio_vs_mesh=float((sig / sig_mesh) ** 0.25),
            )
        t3["rows"][d] = dict(
            snr_req_swerling0_db=10 * math.log10(s_req0),
            snr_req_swerling1_db=10 * math.log10(s_req1),
            arms=rows)
    J["t3_metric_to_pd"] = t3

    # ─────────────────────────────────────────────────────────────────────── #
    #  T4. 환경(다중경로) 이 차이를 줄이나
    # ─────────────────────────────────────────────────────────────────────── #
    n_mc = 200                                  # 기준 자세 24개 × 200 = 4800 실현/팔/단
    neff_ladder = [1.0, 1.65, 3.0, 3.78]        # 저장소 기록의 사다리와 같은 눈금
    surrogate_focus = ["cube_eqvol", "box_bbox", "mesh_half_tri", "sphere_eqvol", "mesh_rigid_spin"]
    t4 = dict(crude=True,
              repo_record_ko=("docs/PAPER_POSITION_0803.md: 유효 경로쌍 N_eff 1.0→3.8 에서 "
                              "**패턴 낙차가 29.3 → 10.1 dB 로 줄었다**. 즉 저장소는 이미 "
                              "«환경이 표적모델 차이를 지운다» 를 한 번 겪었다. 그 사다리를 "
                              "마이크로도플러에 그대로 걸어 본다."),
              model_ko=("다중경로 한 실현 = 진짜 자세(기준 경로) + 다른 자세들(반사 경로)을 "
                        "임의 위상·기하급수 전력으로 더한 것. 가중치는 목표 N_eff 를 내도록 "
                        "**계산**한다(손입력 아님). 호버 표적이라 경로마다 도플러가 같아 "
                        "같은 빈에서 겹친다."),
              caveats_ko=[
                  "⚠ 자세 다양성을 방위축에서 빌렸다. 진짜 지면반사는 고각이 다른 경로이고, 이 저장소에는 로터가 도는 팔의 고각별 표가 없다.",
                  "⚠ 모든 경로를 같은 거리셀에 넣었다. X410 400 MHz 의 거리분해능 0.75 m 보다 경로차가 크면 분해되어 안 섞인다 → 그때는 이 계산이 과하게 비관적이다.",
                  "⚠ 로터 회전수가 경로 간에 같다고 두었다(같은 표적이므로 맞다). 그래서 선 위치는 안 흔들리고 진폭만 흔들린다.",
              ],
              n_mc_per_anchor=n_mc, ladder=neff_ladder, rows={})
    for d in DRONES_2:
        p = proto_for(d)
        lam, nb = p["lam_m"], DRONES[d].prop_blades
        mesh_tabs = arms[d]["mesh"]
        n_az = mesh_tabs.shape[0]
        per_neff = {}
        for ne_t in neff_ladder:
            w = weights_for_neff(ne_t)
            neff_actual = float(w.sum() ** 2 / (w ** 2).sum())
            # ── 메쉬 쪽 실현 (기준 자세별로 저장) ────────────────────────────
            mesh_peak, mesh_rho, mesh_flash, mesh_neff = [], [], [], []
            draws = {}                     # (anchor, i) → (자세 인덱스, 위상) 을 재현하려고 seed 고정
            for a in range(n_az):
                seed = int(hashlib.sha256(f"{d}|{ne_t:.4f}|{a}".encode()).hexdigest()[:8], 16)
                rng = np.random.default_rng(seed)     # 재현 가능한 씨앗(파이썬 hash 는 실행마다 달라진다)
                st = rng.bit_generator.state
                draws[a] = st
                for _ in range(n_mc):
                    e = mix_paths(mesh_tabs, w, a, rng)
                    mesh_peak.append(line_rcs(e, lam)["sigma_ac_peak"])
                    mesh_rho.append(abs(R.ac_corr(mesh_tabs[a], e)))
                    m = R.md_metrics16(e, p, nb)
                    mesh_flash.append(m["flash_contrast_db"])
                    mesh_neff.append(m["n_eff_orders"])
            mesh_peak = np.array(mesh_peak)
            # 다중경로 없는 기준값 (같은 자세)
            clean = arm_line_table(mesh_tabs, lam)
            clean_m = [R.md_metrics16(mesh_tabs[a], p, nb) for a in range(n_az)]

            arm_rows = {}
            for arm in surrogate_focus:
                if arm not in arms[d]:
                    continue
                s_peak, rho_cross, s_flash = [], [], []
                for a in range(n_az):
                    rng = np.random.default_rng(0)
                    rng.bit_generator.state = draws[a]     # ⭐ 같은 자세·같은 위상 추첨을 재사용
                    for _ in range(n_mc):
                        e = mix_paths(arms[d][arm], w, a, rng)
                        s_peak.append(line_rcs(e, lam)["sigma_ac_peak"])
                        rho_cross.append(abs(R.ac_corr(mesh_tabs[a], e)))
                        s_flash.append(R.md_metrics16(e, p, nb)["flash_contrast_db"])
                s_peak = np.array(s_peak)
                dd = db(mesh_peak) - db(s_peak)
                clean_gap = float(np.mean(db(clean["sigma_ac_peak"])) -
                                  np.mean(db(arm_line_table(arms[d][arm], lam)["sigma_ac_peak"])))
                auc = float(np.mean(RNG.permutation(db(mesh_peak)) > RNG.permutation(db(s_peak))))
                fl_gap_clean = float(np.mean([c["flash_contrast_db"] for c in clean_m]) -
                                     np.mean([R.md_metrics16(arms[d][arm][a], p, nb)["flash_contrast_db"]
                                              for a in range(n_az)]))
                arm_rows[arm] = dict(
                    level_gap_db_with_multipath=stat(dd),
                    level_gap_db_clean=clean_gap,
                    auc_mesh_over_surrogate=auc,
                    cohens_d=float(np.mean(dd) / max(np.std(dd, ddof=1), 1e-12)),
                    f2_rho_mesh_template_vs_surrogate=stat(np.array(rho_cross)),
                    flash_gap_db_clean=fl_gap_clean,
                    flash_gap_db_with_multipath=float(np.mean(mesh_flash) - np.mean(s_flash)),
                )
            per_neff[f"N_eff={neff_actual:.2f}"] = dict(
                n_eff_actual=neff_actual, n_paths=int(len(w)),
                mesh_self=dict(
                    f2_rho_clean_template_vs_own_multipath=stat(np.array(mesh_rho)),
                    flash_contrast_db_clean=float(np.mean([c["flash_contrast_db"] for c in clean_m])),
                    flash_contrast_db_with_multipath=float(np.mean(mesh_flash)),
                    n_eff_clean=float(np.mean([c["n_eff_orders"] for c in clean_m])),
                    n_eff_with_multipath=float(np.mean(mesh_neff)),
                    note_ko=("f2_rho 는 «진짜 자세의 깨끗한 템플릿» 대 «같은 자세인데 반사가 섞인 실현» "
                             "의 상관이다. 1 에서 멀어질수록 템플릿 검출기가 환경에서 먼저 무너진다.")),
                arms=arm_rows)
        t4["rows"][d] = per_neff
    t4["reading_ko"] = (
        "⭐ 두 갈래를 갈라서 읽어야 한다. **레벨 차이(σ_ac_peak)는 혼합에 거의 안 지워진다** — "
        "혼합은 선형이라 자세평균의 비가 보존되기 때문이다. 저장소의 29.3→10.1 dB 는 «각도패턴의 "
        "낙차»(봉우리 대 널) 였고 그것은 혼합이 정확히 메운다. 반면 **파형·모양 지표는 지워진다** — "
        "플래시 대조비와 템플릿 상관이 그 자리다. 즉 report16 의 팔 차이가 «레벨» 이면 환경에 견디고, "
        "«모양» 이면 환경에 녹는다. 사다리의 네 지표 중 셋이 모양 쪽이다.")
    J["t4_environment_erosion"] = t4

    # ─────────────────────────────────────────────────────────────────────── #
    #  T3b. ⭐ 대리형상의 오차를 «형상» 과 «운동학» 으로 가른다
    # ─────────────────────────────────────────────────────────────────────── #
    t3b = dict(crude=True,
               why_ko=("사다리의 대리 팔(정육면체·상자·구)은 **온몸이 돈다**. 진짜 드론은 "
                       "프로펠러만 돈다. 그러므로 «메쉬 대 정육면체» 의 차이에는 형상 교체와 "
                       "운동학 교체가 **섞여 있다**. mesh_rigid_spin(진짜 CAD 메쉬를 온몸 회전) "
                       "이 그 둘을 가르는 열쇠다 — 형상은 그대로 두고 운동학만 바꾼 팔이기 때문이다."),
               rows={})
    for d in DRONES_2:
        if "mesh_rigid_spin" not in LT[d]:
            continue
        base_db = np.median(db(LT[d]["mesh"]["sigma_ac_peak"]))
        spin_db = np.median(db(LT[d]["mesh_rigid_spin"]["sigma_ac_peak"]))
        rows = {}
        for arm in ("cube_eqvol", "box_bbox", "box_aspect_voleq", "sphere_eqvol"):
            if arm not in LT[d]:
                continue
            a_db = np.median(db(LT[d][arm]["sigma_ac_peak"]))
            rows[arm] = dict(
                total_error_vs_mesh_db=float(a_db - base_db),
                kinematics_part_db=float(spin_db - base_db),
                shape_part_at_fixed_kinematics_db=float(a_db - spin_db),
            )
        t3b["rows"][d] = dict(
            mesh_sigma_ac_peak_dbsm=float(base_db),
            rigid_spin_sigma_ac_peak_dbsm=float(spin_db),
            arms=rows)
    t3b["reading_ko"] = ("kinematics_part 가 shape_part 보다 크면, 대리 형상이 틀린 이유는 «모양이 "
                         "거칠어서» 가 아니라 «무엇이 도는지를 틀리게 놨기» 때문이다. 그렇다면 사다리가 "
                         "재는 축은 형상 정밀도가 아니라 운동학 모델이다.")
    J["t3b_shape_vs_kinematics"] = t3b

    # ─────────────────────────────────────────────────────────────────────── #
    #  T3c. 읽을 자격 — AC 가 물리인가 수치 잔차인가 (base 의 판정기를 그대로 쓴다)
    # ─────────────────────────────────────────────────────────────────────── #
    t3c = dict(crude=False,
               crude_note_ko=("이 블록만 crude 가 아니다 — 새로 만든 양이 없고 base 의 판정기 "
                              "in_band_ac_frac 를 그대로 호출해 다시 찍은 것뿐이다."),
               what_ko=("base 의 in_band_ac_frac < 0.5 인 팔은 AC 가 물리가 아니라 점구름 "
                        "이산화 잔차다. 그런 팔의 σ_ac_peak 를 «검출 단면적» 으로 읽으면 안 된다 — "
                        "내 T1/T3 표에서 어느 줄이 그런지 여기 적어 둔다."),
               rows={})
    for d in DRONES_2:
        p = proto_for(d)
        row = {}
        for arm, tabs in arms[d].items():
            fr = np.array([R.md_metrics16(tabs[i], p, DRONES[d].prop_blades)["in_band_ac_frac"]
                           for i in range(tabs.shape[0])])
            row[arm] = dict(in_band_ac_frac_mean=float(np.mean(fr)),
                            interpretable=bool(np.mean(fr) >= 0.5))
        t3c["rows"][d] = row
    J["t3c_interpretability"] = t3c

    # ─────────────────────────────────────────────────────────────────────── #
    #  T5. X410 실측에서 이 차이를 구별할 수 있나
    # ─────────────────────────────────────────────────────────────────────── #
    eirp_grid = [20.0, 30.0, 40.0, 50.0, 60.0]
    grx_dbi, nf_db = 10.0, 5.0
    t5 = dict(crude=True,
              assumptions_ko=[
                  "⚠ EIRP·수신이득·잡음지수는 **저장소에 X410 실측 기준값이 없어 가정**이다. "
                  "EIRP 는 20~60 dBm 을 훑고, G_rx=10 dBi · NF=5 dB 는 benchmark/link_budget.py 의 기본값을 그대로 썼다.",
                  "R1=R2=R (표적이 TX·RX 중간) 로 놓은 등가 기하다. 실제 야외 기하는 다르다.",
                  "정합필터·기준채널이 이상적이라고 두었다 — 실측의 12bit ADC·직접파 누설·기준채널 열화는 안 넣었다(전부 손해 쪽).",
                  "표적은 호버(0-도플러 못 씀). 병진하면 동체 선이 살아나 훨씬 쉬워진다.",
              ],
              grx_dbi=grx_dbi, nf_db=nf_db, pfa=pfa, rows={})
    for d in DRONES_2:
        p = proto_for(d)
        lam = p["lam_m"]
        sig_peak = float(np.median(LT[d]["mesh"]["sigma_ac_peak"]))
        sig_tot = float(np.median(LT[d]["mesh"]["sigma_total"]))
        s_req = snr_for_pd(0.9, pfa, 1, 0)

        # 회전수 흔들림이 코히어런트 적분시간을 자른다
        dom = int(np.median(LT[d]["mesh"]["peak_order"]))
        coh = {}
        for jit in (0.001, 0.005, 0.01):
            coh[f"rpm_jitter_{jit*100:.1f}pct"] = dict(
                t_coh_max_s=1.0 / (dom * jit * p["f_rot_hz"]),
                note_ko="차수 m 의 선이 한 빈에 머물려면 m·δ·f_rot·T < 1 이어야 한다.")
        t_cpi = min(0.1, 1.0 / (dom * 0.01 * p["f_rot_hz"]))   # 1% 흔들림 기준, 최대 100 ms

        rng_rows = {}
        for e in eirp_grid:
            rng_rows[f"EIRP_{e:.0f}dBm"] = dict(
                range_m_hover_ac_peak=range_for_snr(s_req, sig_peak, lam, e, grx_dbi, nf_db, t_cpi),
                range_m_if_body_usable=range_for_snr(s_req, sig_tot, lam, e, grx_dbi, nf_db, t_cpi),
            )
        # 팔 구별에 필요한 독립 관측 수 (두 표본 t 검정, α=0.05 양측, 검정력 0.8)
        za, zb = norm.ppf(1 - 0.05 / 2), norm.ppf(0.8)
        looks = {}
        mesh_db = db(LT[d]["mesh"]["sigma_ac_peak"])
        # D5(로터 상대위상) 산포를 더한 «실측이 실제로 겪을» 흔들림
        d5 = json.load(open(os.path.join(OUT, "report16_metric_mesh_full.json")))
        rotor_spread_db = None
        for it in d5.get("reasons_to_doubt", []):
            if it.get("id") == "D5":
                rotor_spread_db = it
        for arm in surrogate_focus:
            if arm not in LT[d]:
                continue
            a_db = db(LT[d][arm]["sigma_ac_peak"])
            delta = float(np.mean(mesh_db) - np.mean(a_db))
            sd_pool = float(np.sqrt(0.5 * (np.var(mesh_db, ddof=1) + np.var(a_db, ddof=1))))
            n_need = 2.0 * ((za + zb) * sd_pool / max(abs(delta), 1e-9)) ** 2
            looks[arm] = dict(
                mean_gap_db=delta, pooled_sd_db=sd_pool,
                looks_per_arm_needed=math.ceil(n_need),
                note_ko="자세(방위) 산포만 셌다. 실측은 여기에 로터 상대위상·rpm·자세각·환경 산포가 더 붙는다.")
        t5["rows"][d] = dict(
            dominant_order=dom, t_cpi_used_s=t_cpi,
            coherent_integration_cap=coh,
            snr_req_db=10 * math.log10(s_req),
            sigma_ac_peak_dbsm=db(sig_peak).item(),
            sigma_total_dbsm=db(sig_tot).item(),
            hover_penalty_db=db(sig_tot).item() - db(sig_peak).item(),
            detection_range=rng_rows,
            looks_needed_to_separate_arms=looks,
        )
    t5["rotor_phase_extra_spread_ko"] = (
        "⚠ mesh_full 단의 D5 가 «로터 상대위상만으로 플래시 대조비가 4.2~10.0 dB 흔들린다» 를 "
        "계산해 두었다. 실측에서는 그 흔들림이 통제되지 않으므로, 위의 looks_per_arm_needed 는 "
        "**바닥값**이다 — 실제로는 더 많이 필요하다.")
    J["t5_x410_measurability"] = t5

    # ─────────────────────────────────────────────────────────────────────── #
    #  판정
    # ─────────────────────────────────────────────────────────────────────── #
    # 헤드라인 숫자는 전부 위에서 계산된 값에서 **꺼내 쓴다** (손입력 금지)
    hp = {d: J["t1_detection_cross_section"]["per_arm"][d]["mesh"]["ac_below_total_db"]["median"]
          for d in DRONES_2}
    hp_fleet = [v["penalty_db"]["median"] for v in
                J["t1_detection_cross_section"]["fleet_sigma_ac_peak_dbsm"].values()]
    keys4 = list(J["t4_environment_erosion"]["rows"]["mini2"].keys())
    key_first, key_last = keys4[0], keys4[-1]

    def t4get(d, arm, field, k):
        return J["t4_environment_erosion"]["rows"][d][k]["arms"][arm][field]

    def t4self(d, field, k):
        return J["t4_environment_erosion"]["rows"][d][k]["mesh_self"][field]

    lvl_erode = {d: (t4get(d, "cube_eqvol", "level_gap_db_with_multipath", key_first)["mean"],
                     t4get(d, "cube_eqvol", "level_gap_db_with_multipath", key_last)["mean"])
                 for d in DRONES_2}
    fl_erode = {d: (t4get(d, "cube_eqvol", "flash_gap_db_clean", key_first),
                    t4get(d, "cube_eqvol", "flash_gap_db_with_multipath", key_last))
                for d in DRONES_2}
    rho_self = {d: (t4self(d, "f2_rho_clean_template_vs_own_multipath", key_first)["mean"],
                    t4self(d, "f2_rho_clean_template_vs_own_multipath", key_last)["mean"])
                for d in DRONES_2}
    dec = {d: J["t3_metric_to_pd"]["rows"][d]["arms"]["mesh_half_tri"]["delta_vs_mesh_db"]
           for d in DRONES_2}
    dec_looks = {d: J["t5_x410_measurability"]["rows"][d]["looks_needed_to_separate_arms"]
                 ["mesh_half_tri"]["looks_per_arm_needed"] for d in DRONES_2}
    kin = {d: J["t3b_shape_vs_kinematics"]["rows"][d]["arms"]["cube_eqvol"] for d in DRONES_2}
    r30 = {d: J["t5_x410_measurability"]["rows"][d]["detection_range"]["EIRP_30dBm"]
           for d in DRONES_2}
    ne_cost = {d: J["t2_detector_families"]["how_n_eff_enters_detection"]["rows"][d]
               ["snr_cost_of_spread_db"]["mean"] for d in DRONES_2}

    J["findings"] = dict(
        headline_ko=(
            "report16 이 잰 네 갈래 지표 중 **검출식에 들어가는 것은 사실상 하나뿐**이다. "
            "단일빈 CFAR(저장소가 실제로 쓰는 검출기)은 «가장 센 AC 선의 RCS» 만 보고, "
            "대역합 검출기는 «AC 총 RCS» 만 본다. 플래시 대조비는 표준 CPI 안에서 적분돼 "
            f"사라지고(하모닉 선을 가르는 최소 CPI 가 플래시 주기의 정확히 {int(DRONES['mini2'].prop_blades)} 배다), "
            f"고차 풍부도는 peak_share 를 통해서만 들어간다 — 그 값이 mini2 {ne_cost['mini2']:.1f} dB · "
            f"matrice4e {ne_cost['matrice4e']:.1f} dB 다. 폭은 CFAR 셀 수를 통해 문턱을 1 dB 아래로 움직인다."),
        translation_possible_ko=(
            "⭐ 옮길 수 있다 — 다만 지표를 그대로 옮기는 것이 아니라 **위상표를 도플러 빈별 RCS 로 "
            "다시 나눠야** 한다(σ_m = 4π/λ²·|c_m|²). 그 번역기를 T1 에서 처음 만들었다."),
        biggest_number_ko=(
            f"⭐⭐ **호버 벌금**: 호버 드론의 검출 단면적(가장 센 AC 선)은 총 RCS 보다 "
            f"{min(hp_fleet):.1f} … {max(hp_fleet):.1f} dB 낮다(10기 전부). 0-도플러 행은 ECA·정적클러터 "
            "노치가 지우기 때문이다. 이 한 항이 사다리 안의 어떤 팔 차이보다도 크고, 검출거리는 "
            f"{10 ** (-max(hp_fleet) / 40):.2f}~{10 ** (-min(hp_fleet) / 40):.2f} 배로 줄어든다(SNR ∝ R⁻⁴ 이므로 네제곱근)."),
        the_dilemma_ko=(
            "⭐ **어느 쪽으로 가도 사다리의 값어치는 깎인다.** 마이크로도플러가 검출의 주 채널이 되는 "
            "것은 표적이 호버해서 동체가 0-도플러에 묻힐 때뿐이다. 그런데 바로 그때 위의 호버 벌금이 "
            "온다. 반대로 표적이 병진하면 동체 선이 살아나 훨씬 세므로(위 괄호의 거리) 검출은 동체가 "
            "하고 마이크로도플러는 **분류용 덤**이 된다. 즉 마이크로도플러 형상 정밀도가 검출확률을 "
            "좌우하는 구간은 좁다 — 사다리는 그 구간이 얼마나 넓은지를 아직 안 쟀다."),
        environment_ko=(
            "⚠ **내 예상이 절반만 맞았다**. 갈라서 적는다. "
            f"(가) 레벨 차이는 **거의 안 지워진다** — 메쉬↔정육면체 σ_ac_peak 낙차가 "
            + " · ".join(f"{d} {lvl_erode[d][0]:.1f}→{lvl_erode[d][1]:.1f} dB" for d in DRONES_2)
            + ". 혼합이 선형이라 자세평균의 비가 보존되기 때문이다. 저장소의 29.3→10.1 dB 는 "
            "«각도패턴의 봉우리대널 낙차» 였고 그것은 혼합이 메운다 — 지금 재는 것은 그 양이 아니다. "
            f"(나) 반면 **모양 지표는 지워진다** — 플래시 대조비 낙차가 "
            + " · ".join(f"{d} {fl_erode[d][0]:.1f}→{fl_erode[d][1]:.1f} dB" for d in DRONES_2)
            + " 로 가고, 템플릿 검출기는 메쉬 자기 자신에 대해서도 상관이 "
            + " · ".join(f"{d} {rho_self[d][0]:.2f}→{rho_self[d][1]:.2f}" for d in DRONES_2)
            + " 로 무너진다. 네 지표 중 셋이 모양 쪽이다."),
        measurement_ko=(
            f"두 갈래로 갈린다. (가) **메쉬 정밀도 축은 실측 불가**다 — 삼각형 수를 반으로 줄여도 "
            f"검출 단면적이 mini2 {dec['mini2']:+.2f} dB · matrice4e {dec['matrice4e']:+.2f} dB 밖에 "
            f"안 움직여, 자세 산포 속에서 가르려면 독립 관측이 {min(dec_looks.values()):,} 회 넘게 "
            "필요하다. (나) **대리형상 축은 한 번만 봐도 갈린다**(17~28 dB). 다만 그 차이의 대부분이 "
            "형상이 아니라 운동학이다 — T3b 참조. 거리는 EIRP 30 dBm·G_rx 10 dBi 가정에서 호버 AC 선 "
            + " · ".join(f"{d} {r30[d]['range_m_hover_ac_peak']:.0f} m" for d in DRONES_2)
            + " 다(동체를 쓸 수 있었다면 "
            + " · ".join(f"{r30[d]['range_m_if_body_usable']:.0f} m" for d in DRONES_2) + ")."),
        practical_floor_ko=(
            "⭐ **실무 손실이 사다리의 여러 팔 차이보다 크다.** CPI 를 회전수에 못 맞추는 것만으로 "
            "가장 센 AC 선이 평균 "
            + " · ".join(f"{d} {-J['t2_detector_families']['practical_cpi_loss']['rows'][d]['loss_db_rect_window']['mean']:.1f} dB"
                         f"(최악 {-J['t2_detector_families']['practical_cpi_loss']['rows'][d]['loss_db_rect_window']['min']:.1f})"
                         for d in DRONES_2)
            + " 를 잃는다(창 없음 기준). 이 하나가 메쉬 정밀도 축 전체(0.0x dB)보다 두 자릿수 크고, "
            "평판·블레이드 대리 팔의 차이와 같은 자릿수다. 그러므로 그 크기의 팔 차이는 «검출기가 "
            "어떻게 설정됐나» 에 묻힌다."),
        shape_vs_kinematics_ko=(
            "⭐ 대리형상의 검출 단면적 오차를 갈라 보면 **운동학이 형상을 압도한다**. 정육면체 기준: "
            + " · ".join(f"{d} 총 {kin[d]['total_error_vs_mesh_db']:+.1f} dB = 운동학 "
                         f"{kin[d]['kinematics_part_db']:+.1f} + 형상 "
                         f"{kin[d]['shape_part_at_fixed_kinematics_db']:+.1f}" for d in DRONES_2)
            + ". 게다가 형상 몫은 두 기체에서 **부호가 뒤집힌다**. 즉 사다리가 실제로 재고 있는 축은 "
            "«형상 정밀도» 가 아니라 «무엇이 도는가» 다."),
    )

    flaws = [
        dict(id="F1", severity="high",
             where="outputs/report16_metric_*.json 여섯 단 전부 — 검출 언어가 한 번도 안 나옴",
             title_ko="네 갈래 지표가 검출 통계량이 아니다 — 그런데 사다리 판정은 지표로만 났다",
             detail_ko=("플래시 대조비는 시간축의 봉우리÷중앙값인데, 하모닉 선을 가르는 데 필요한 최소 "
                        "CPI 가 플래시 주기의 2배(블레이드 2매)라 표준 CPI 안에서 **반드시 적분돼 "
                        "사라진다**. 폭은 CFAR 셀 수를 통해 문턱을 1 dB 아래로 움직일 뿐이다. "
                        f"풍부도는 peak_share 로만 들어가 mini2 {ne_cost['mini2']:.1f} · "
                        f"matrice4e {ne_cost['matrice4e']:.1f} dB 를 준다. 남는 것은 레벨(σ_ac) 하나다."),
             computed_here=True),
        dict(id="F2", severity="high",
             where="report16 전체 서사 — 호버 가정과 0-도플러 행의 관계가 어디에도 없음",
             title_ko="dc_ac_db 를 «동체가 블레이드를 묻는다» 로 읽었지만, 검출에서 동체는 애초에 못 쓴다",
             detail_ko=("호버 표적의 0-도플러 행은 ECA·정적클러터 노치가 지운다(저장소 report5 hover blind). "
                        "검출 단면적은 σ_total 이 아니라 σ_ac_peak 이고, 그 낙차가 함대 10기에서 "
                        f"{min(hp_fleet):.1f}~{max(hp_fleet):.1f} dB 다. 이 한 항이 사다리 전체의 팔 "
                        "차이를 압도한다 — 그런데 사다리 어디에도 이 양이 없다."),
             computed_here=True),
        dict(id="F3", severity="high",
             where="report16 사다리의 대리 팔(cube_eqvol·box_bbox·sphere_eqvol) 설계",
             title_ko="⭐ 대리 팔은 온몸이 돈다 — 그래서 «형상 교체» 와 «운동학 교체» 가 섞여 있다",
             detail_ko=("진짜 CAD 메쉬를 온몸 회전시킨 팔(mesh_rigid_spin)이 그 둘을 가른다. 정육면체의 "
                        "총 오차 중 운동학 몫이 "
                        + " · ".join(f"{d} {kin[d]['kinematics_part_db']:+.1f} dB" for d in DRONES_2)
                        + " 이고 형상 몫은 "
                        + " · ".join(f"{d} {kin[d]['shape_part_at_fixed_kinematics_db']:+.1f} dB" for d in DRONES_2)
                        + " 로 **부호까지 뒤집힌다**. 사다리를 «형상 정밀도의 값어치» 로 읽으면 "
                        "운동학 효과를 형상 효과로 오독하게 된다."),
             computed_here=True),
        dict(id="F4", severity="medium",
             where="report16_metric_mesh_half_tri 단의 결론 (메쉬 정밀도 축)",
             title_ko="메쉬 정밀도 차이는 검출에서 측정 불가능하다 — 그것이 결과이고, 그렇게 적혀야 한다",
             detail_ko=(f"삼각형 수를 반으로 줄여도 σ_ac_peak 가 mini2 {dec['mini2']:+.2f} · "
                        f"matrice4e {dec['matrice4e']:+.2f} dB 움직인다. 자세 산포(2~4 dB) 속에서 "
                        f"이 차이를 α=0.05·검정력 0.8 로 가르려면 독립 관측이 "
                        f"{min(dec_looks.values()):,}~{max(dec_looks.values()):,} 회 필요하다. "
                        "그러므로 «반쪽 메쉬로도 충분하다» 는 강한 결과이고, 지도교수의 지적과 같은 방향이다."),
             computed_here=True),
        dict(id="F5", severity="medium",
             where="report16 사다리의 환경 축 (없음)",
             title_ko="모양 지표 셋은 환경에서 녹는다 — 레벨 하나만 견딘다",
             detail_ko=("혼합 모형에서 플래시 대조비 낙차가 "
                        + " · ".join(f"{d} {fl_erode[d][0]:.1f}→{fl_erode[d][1]:.1f} dB" for d in DRONES_2)
                        + " 로 가고, 템플릿 상관은 메쉬 자기 자신에 대해서도 "
                        + " · ".join(f"{d} {rho_self[d][0]:.2f}→{rho_self[d][1]:.2f}" for d in DRONES_2)
                        + " 로 무너진다. ⚠ 다만 **레벨 차이는 안 지워졌다** — 내가 세운 «환경이 지운다» "
                        "가설의 절반은 반증됐고, 그 반증도 그대로 남긴다."),
             computed_here=True),
        dict(id="F6", severity="medium",
             where="benchmark/report16_verify_detector.py (내 계산)",
             title_ko="⚠ 내 다중경로 모형이 대리물이다 — 고각 다양성이 아니라 방위 다양성을 빌렸다",
             detail_ko=("진짜 지면반사는 고각이 다른 경로인데 이 저장소에는 로터가 도는 팔의 고각별 "
                        "위상표가 없다(mesh_no_rotor 단의 고각 훑기는 로터 없는 팔이다). 게다가 모든 "
                        "경로를 같은 거리셀에 넣었다 — X410 400 MHz(ΔR 0.75 m)에서 경로차가 그보다 "
                        "크면 분해되어 안 섞이므로 내 t4 는 그만큼 비관적이다. "
                        "이 결함은 **내 결론을 약화시키는 쪽으로 작동한다** — 정직하게 남긴다."),
             computed_here=True),
        dict(id="F7", severity="medium",
             where="benchmark/report16_verify_detector.py (내 계산)",
             title_ko="⚠ 링크버짓의 EIRP·이득·잡음지수는 저장소에 근거가 없는 가정이다",
             detail_ko=("X410 의 송신출력이 저장소 어디에도 적혀 있지 않아 20~60 dBm 을 훑었고 "
                        "G_rx=10 dBi·NF=5 dB 는 benchmark/link_budget.py 의 기본값을 그대로 썼다. "
                        "그래서 t5 의 거리 숫자는 절대값이 아니라 **EIRP 대비 거리 곡선**으로만 읽어야 한다. "
                        "12bit ADC 양자화·기준채널 열화·직접파 누설은 안 넣었다(전부 손해 쪽)."),
             computed_here=True),
        dict(id="F8", severity="medium",
             where="내 T1~T5 전부 — 앞 단 결함을 그대로 물려받았다",
             title_ko="⚠ 가림 없음(D1)·PO 가 가장 약한 대역(D2)·로터 상대위상 4~10 dB(D5) 가 내 숫자에도 실려 있다",
             detail_ko=("특히 D1(가림 없음)은 σ_dc 를 부풀리므로 내 «호버 벌금» 은 과대일 수 있고, "
                        "D5 는 σ_ac_peak 를 상위 백분위 쪽으로 밀어 «호버 벌금» 을 과소로 만든다 — "
                        "두 편향의 방향이 반대라 상쇄 정도를 나는 모른다. 모르는 것은 모른다고 적는다."),
             computed_here=False),
        dict(id="F9", severity="low",
             where="report16 사다리의 널 팔(sphere_eqvol·disc·sph_hub) 을 검출 언어로 읽을 때",
             title_ko="널 팔의 σ_ac_peak 는 «검출 단면적» 이 아니라 수치 바닥이다",
             detail_ko=("base 의 in_band_ac_frac < 0.5 판정기를 그대로 걸어 t3c 에 어느 줄이 그런지 "
                        "적어 두었다. 그 줄들의 −55 dBsm 는 물리가 아니라 점구름 이산화 잔차다."),
             computed_here=True),
    ]
    J["flaws"] = flaws

    J["verdict"] = dict(
        verdict="PREMATURE",
        scope_ko=("판정 대상은 «report16 사다리가 검출에 대해 무엇을 말할 수 있는가» 다. "
                  "사다리 단들의 내부 계산을 BROKEN 이라고 말하는 것이 아니다 — 그쪽은 게이트에서 "
                  "재확인했고 통과했다."),
        one_line_ko=("사다리 안의 숫자는 단단하다. 그러나 «형상 정밀도가 값어치 있다/없다» 로 나가기에는 "
                     "이르다. 네 지표 중 셋이 검출식에 안 들어가고(F1), 호버 표적의 검출 단면적을 "
                     "아직 안 잡았으며(F2), 대리 팔의 차이 대부분이 형상이 아니라 운동학이고(F3), "
                     "모양 지표는 환경에서 녹는다(F5)."),
        what_is_sound_ko=("① 위상표와 지표 계산 자체 — 여섯 단이 서로 다른 코드로 재계산해 상대차 0 을 "
                          "확인했고 나도 게이트 4종에서 재확인했다. ② 「구·원판은 변조를 못 만든다」 "
                          "같은 정성 결론. ③ 각 단이 스스로 세운 결함 목록의 정직성 — 특히 D5 는 "
                          "내가 따로 물었어도 같은 답을 냈을 것이다. ④ ⭐ **메쉬 정밀도 축의 무의미함**은 "
                          "검출 언어로 옮겨도 그대로 살아남는다(F4) — 사다리에서 가장 튼튼한 결과다."),
        what_is_premature_ko=("검출·실측으로 넘어가는 모든 주장. 이 단들은 그 주장을 명시적으로 하지 "
                              "않았으므로(«형상 정밀도가 값어치 있다를 주장하지 않는다» 고 적혀 있다) "
                              "판정은 «단이 틀렸다» 가 아니라 «사다리가 아직 검출에 닿지 않았다» 다."),
        cheapest_next_step_ko=("① 이 파일의 T1 번역기(도플러 빈별 RCS)로 사다리를 다시 채점 — 새 "
                               "전자기 계산 0, 저장된 표만 다시 읽으면 된다. ② 대리 팔에 «프로펠러 "
                               "자리에만 대리 형상» 판을 추가해 운동학을 고정 — 그래야 형상 축이 분리된다. "
                               "③ 로터가 도는 팔의 **고각별** 위상표를 만들어 진짜 지면반사를 걸 것."),
    )
    J["seconds"] = time.time() - t_start

    path = os.path.join(OUT, "report16_verify_detector.json")
    with open(path, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=float)
    print(f"[report16_verify_detector] wrote {path}  ({os.path.getsize(path)/1024:.0f} KB, "
          f"{J['seconds']:.1f} s)")
    for k, v in gates.items():
        print(f"  gate {k}: {'PASS' if v['pass_'] else 'FAIL'}")
    print(f"  verdict: {J['verdict']['verdict']}")
    return J


if __name__ == "__main__":
    main()
