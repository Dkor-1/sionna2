# -*- coding: utf-8 -*-
"""
report16_base.py — ⭐⭐ **새 메쉬로 PO 마이크로도플러를 다시 세운다 (기반 라운드)**
================================================================================

무엇을 하는가
--------------------------------------------------------------------------------
드론이 제자리에 떠 있어도 **프로펠러가 돌기 때문에** 되돌아오는 전파의 위상이 시간에 따라
흔들린다. 그 흔들림을 «마이크로도플러(micro-Doppler)» 라고 부른다 — 표적 전체가 움직여서
생기는 도플러가 아니라, 표적의 **일부(블레이드)가 움직여서** 생기는 도플러라는 뜻이다.

이 파일은 그 신호를 **처음부터 다시** 만든다. 이유는 하나다: 저장소에 남아 있는
`outputs/report1_microdoppler.npz` 는 **2026-07-29** 것이고, 그 뒤로 드론 3D 형상(메쉬)이
두 번 바뀌었다(2026-07-31, 2026-08-04 CAD 정정). 옛 신호는 옛 몸으로 만든 것이다.

왜 지금 이걸 하는가 (배경 — 결론을 미리 정하지 않기 위해 적어 둔다)
--------------------------------------------------------------------------------
지도교수의 지적은 «드론 RCS 정밀도는 연구 값어치가 없다» 이고, **우리 데이터가 그 지적을
상당 부분 뒷받침한다** — 절대 세기(RCS)만 놓고 보면 매개변수가 하나도 없는 «등가부피 구»
가 우리 정밀 메쉬를 이긴다(outputs/p3_validation_v2.json).

다만 구가 **원리적으로 못 내는 것**이 하나 있다. 구는 어느 방향에서 봐도 똑같이 생겨서
**방향에 따른 변동이 정확히 0** 이다. 그래서 묻는다 — 그 «구조» 우위가 마이크로도플러에서는
얼마나 크게 나타나는가?

⚠ 이 라운드는 그 질문에 **답하지 않는다**. 이 라운드가 하는 일은 두 가지뿐이다:
   (1) 뒤 단계 전부가 쓸 **재생성 규약**과 **지표 정의**를 못박는다,
   (2) 새 메쉬 기준 마이크로도플러를 내고 **옛 메쉬와 나란히** 놓는다.
   메쉬를 바꿨는데 마이크로도플러가 거의 안 변한다면, 그것은 «형상 정밀도가 여기서도
   값어치가 없다» 는 뜻이고 우리는 방향을 다시 잡아야 한다. 그 결과도 그대로 적는다.

⚠⚠ 반드시 같이 읽어야 할 한계
--------------------------------------------------------------------------------
우리 PO 커널이 믿을 만하려면 부품의 **특징 폭이 0.729λ 이상**이어야 한다
(outputs/report00_po_case.json: s4_limits.po_validity_knee_a_over_lambda).
프로펠러 블레이드 폭 13.78 mm 는 **15.86 GHz** 에서야 그 문턱을 넘는다. 즉 3.5 GHz 에서
**마이크로도플러를 만드는 바로 그 부품이 우리 커널이 가장 약한 부품**이다.
그래서 이 파일은 3.5 GHz(생산 대역)와 15.86 GHz(문턱)를 **둘 다** 돌려 그 차이를 남긴다.

또한 이 커널에는 **가림(occlusion)이 없다** — 블레이드가 동체 뒤로 돌아가도 계속 산란체로
센다. 이것은 의도된 통제다(가림을 넣으면 «메쉬가 바뀌어서» 인지 «가림이 바뀌어서» 인지
갈리지 않는다). 대신 동체 대 블레이드 세기비(dc_ac_db)는 이 결함에 가장 크게 오염된다.

측정 팔(arm) 구성
--------------------------------------------------------------------------------
 · mesh   : 진짜 CAD 메쉬 (프레임 + 실제 프로펠러 4벌, 반대회전 로터는 거울상)
 · disc   : 프로펠러를 **같은 반경·같은 두께의 회전대칭 원판**으로 교체 → 물리적 변조 0.
            "돌긴 도는데 구조가 없는" 표적. **지표의 0점**을 실측으로 잡는다.
 · slab   : 프로펠러를 **같은 스팬·같은 두께·같은 부피의 평판 2장**으로 교체 →
            마이크로도플러 문헌의 고전 «회전 강체 막대/판» 모델. 기하 프리미티브 판.
 · sphere : 기체 전체를 **등가부피 구** 하나로 교체하고 시선을 같은 위상격자로 돌린다 →
            물리적 변조는 0 이어야 한다. 남는 값이 곧 **계산기 자체의 바닥(수치 잡음)** 이다.

메쉬 세대(generation)
--------------------------------------------------------------------------------
 · G_0727 = git c81bb4c  (report1_microdoppler.npz 를 만든 시절의 형상)
 · G_0803 = git b983706  (어제 CAD 정정 **직전**)
 · G_0804 = 작업트리 HEAD (어제 CAD 정정 **직후** = 현재)
세 세대 모두 **현재의 재질표·현재의 PO 커널**로 돌린다 — 그래야 차이가 오직 «형상» 에
귀속된다. (src/drones.py·src/drone_cad.py 는 읽기만 하고, 옛 판은 git 에서 꺼내 쓴다.)

⛔ src/drones.py · src/drone_cad.py 편집 금지(읽기 전용). outputs/report15_* 건드리지 않음.
⛔ 숫자 손입력 금지 — 규약 값(위상 스텝 수·PRF·표본 수)은 전부 기하에서 **계산**한다.
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
SCRATCH = os.environ.get("REPORT16_SCRATCH",
                         "/tmp/claude-1015/-workspace/"
                         "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report16")

OUT_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_base.png")

# --------------------------------------------------------------------------- #
#  ⭐ 재생성 규약 (이 라운드 전체가 이 값을 쓴다) — 손입력은 여기 3개 뿐이고
#     나머지(위상 스텝·PRF·표본 수)는 전부 기하에서 유도한다.
# --------------------------------------------------------------------------- #
FC_MAIN = 3.5e9          # 생산 대역 (5G NR n78) — 저장소 전 리포트의 기준 주파수
FC_PO_KNEE = 15.86e9     # 블레이드 폭 13.78 mm 가 PO 유효 무릎(0.729λ)을 넘는 주파수
EL_DEG = 15.0            # 고각 — 저장소 기본(레이더가 드론을 아래에서 15° 올려다 봄)
RANGE_M = 10.0           # 거리 — 30×20×11 m 무향실 안에서 성립하는 모노스태틱 스탠드오프
N_AZ = 24                # 방위 앙상블(15° 간격). 단일 자세 결론은 뒤집힌 전례가 있다.
N_REV = 32               # 슬로타임 길이 = 로터 32회전
OS_FACTOR = 8.0          # 위상 표본화 여유배수 (나이퀴스트 2β 대비 4배)
EDGE_DROP_DB = 20.0      # 도플러 폭 판정 문턱 (첨두 대비 −20 dB)

GEN_COMMITS = {"G_0727": "c81bb4c", "G_0803": "b983706", "G_0804": None}   # None = 작업트리
GEN_LABEL = {"G_0727": "2026-07-27 mesh (npz era)",
             "G_0803": "2026-08-03 mesh (pre CAD fix)",
             "G_0804": "2026-08-04 mesh (post CAD fix, current)"}

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  규약 유도 — 기체마다 다르다. f_tip 을 접지 않도록 **계산해서** 정한다.
# --------------------------------------------------------------------------- #
def derive_protocol(prop_dia_mm, hover_rpm, prop_blades, fc, el_deg=EL_DEG,
                    os_factor=OS_FACTOR, n_rev=N_REV):
    """기체 하나의 마이크로도플러 표본화 규약을 **계산**한다.

    핵심 수식 — 블레이드 팁이 만드는 최대 위상흔들림의 진폭이 곧 «몇 차 하모닉까지
    살아 있나» 다. 팁은 허브에서 반경 R 만큼 떨어져 돌므로 왕복 위상은
        2k·R·cos(el)·sin(회전각)
    이고, 그 진폭 β = 2kR·cos(el) = 4πR·cos(el)/λ 가 **베셀 차수 절단값**이다.
    같은 β 가 «팁 도플러 ÷ 회전수» 이기도 하다:  f_tip / f_rot = β.

    따라서
      · 1회전을 S 등분해 표를 만들면 접힘(aliasing) 없는 조건은 S ≥ 2β,
      · 슬로타임 PRF = S·f_rot 로 두면 PRF ≥ 2·f_tip 이 **자동으로** 만족된다.
    여기서는 S = 2^ceil(log2(os_factor·β)) 로 잡아 나이퀴스트 대비 os_factor/2 배 여유를 둔다.

    ⭐ S 표본/회전으로 표를 만들고 PRF = S·f_rot 로 읽으면 슬로타임 표본이 표의 격자에
      **정확히** 떨어진다 → 보간 오차가 0 이다. 게다가 4개 로터가 같은 rpm 이므로 E(t) 는
      1회전 주기의 **정확한 주기신호**다. 그래서 스펙트럼은 f_rot 의 정수배에만 선으로 선다.
    """
    lam = C0 / float(fc)
    R = float(prop_dia_mm) / 2000.0
    f_rot = float(hover_rpm) / 60.0
    beta = 4.0 * math.pi * R * math.cos(math.radians(el_deg)) / lam
    S = int(2 ** math.ceil(math.log2(max(64.0, os_factor * beta))))
    prf = S * f_rot
    n_t = S * int(n_rev)
    f_tip = beta * f_rot
    return dict(
        lam_m=lam, prop_radius_m=R, f_rot_hz=f_rot, beta=beta,
        beta_note_ko="β = 4πR·cos(el)/λ = 베셀 차수 절단 = f_tip/f_rot (rpm 과 무관)",
        n_phase=S, samples_per_rev=S, prf_hz=prf, n_t=n_t, n_rev=int(n_rev),
        period_deg=360.0, f_tip_hz=f_tip,
        flash_hz=float(prop_blades) * f_rot,
        blade_flash_order=int(prop_blades),
        nyquist_margin_x=prf / (2.0 * f_tip),
        phase_step_deg=360.0 / S,
        freq_resolution_hz=f_rot / float(n_rev),
        order_quantum_rel=1.0 / beta,
        order_quantum_note_ko=("도플러 폭 지표의 최소 눈금은 1차수 = f_rot 이다. "
                               "f_tip 대비 1/β 이므로 그보다 작은 폭 변화는 잴 수 없다."),
        interp_error="none (slow-time grid lands exactly on the phase table)",
    )


# --------------------------------------------------------------------------- #
#  ⭐⭐ 지표 정의 — **여기서 못박는다**. 뒤 단계는 전부 이 함수를 부른다(재구현 금지).
# --------------------------------------------------------------------------- #
def md_metrics16(tab, proto, prop_blades):
    """위상 표 E(φ) (1회전, n_phase 등간격) → 마이크로도플러 지표.

    입력이 «시계열» 이 아니라 «1회전 표» 인 것이 핵심이다. 4개 로터가 같은 rpm 으로 도는
    한 E(t) 는 1회전 주기의 정확한 주기신호이므로, 표를 그대로 FFT 하면 **누설 없는
    선 스펙트럼**이 나온다. 차수 m 의 선은 도플러 m·f_rot 에 해당한다.

    ── 지표 넷 (각각 무엇에 둔감하고 무엇에 민감한지 함께 적는다) ────────────────────
    ① flash_contrast_db  «플래시가 바닥보다 몇 dB 위인가»
         정의: 20log10( max_φ|E_ac(φ)| / median_φ|E_ac(φ)| ), E_ac = E − 평균E.
         민감: 블레이드가 시선에 수직으로 정렬될 때의 정합(플래시), 위상격자 촘촘함,
               점구름 밀도, 파면(평면/구면).
         둔감: 절대 RCS 크기, 동체 DC 세기(빼고 잰다), rpm, PRF, 슬로타임 길이.
         회전대칭체의 이론값 = 0 dB. 실측 하한은 sphere/disc 팔이 준다.

    ② n_eff_orders / order_p90 / blade_comb_frac  «고차 성분이 얼마나 풍부한가»
         선 스펙트럼 전력 p_m (m≠0, 합=1) 에서
           n_eff_orders   = exp(−Σ p_m ln p_m)   «실질적으로 몇 개의 차수가 살아 있나»
           order_p50/p90  = 누적 전력이 50%/90% 에 닿는 최소 차수
           dominant_order = 가장 센 차수
           blade_comb_frac= 블레이드 수의 배수 차수(2,4,6,…)에 실린 AC 전력 몫
                            → «진짜 블레이드 플래시 빗» 인지 «비대칭·불균형 선» 인지 가른다
         민감: 블레이드 형상의 복잡도, β(=반경/λ), 점구름 밀도.
         둔감: 절대 크기, rpm, PRF, 동체 DC.
         ⚠ AC 가 수치바닥에 가까우면 n_eff_orders 는 «잡음이 고르게 퍼진 값» 으로 커진다.
            반드시 ac_over_floor_db 와 함께 읽을 것. 그래서 같이 돌려준다.

    ③ fd_edge_hz / width_ratio  «스펙트럼 폭이 f_tip 예측과 맞는가»
         정의: |c_m|² 가 첨두 대비 −20 dB 이상인 가장 바깥 차수 → fd_edge = 그 차수·f_rot,
               width_ratio = fd_edge / f_tip  (운동학이 맞으면 ≈1).
         민감: 팁반경·λ·고각(cos el), 문턱값(−10/−20/−30 dB 를 모두 돌려준다).
         둔감: 절대 크기, 동체 DC, 표본화 S(2·차수보다 크기만 하면).
         ⚠ 최소 눈금이 **1차수 = f_rot** 이다. f_tip 대비 1/β 라 그보다 작은 변화는 잴 수 없다.

    ④ dc_ac_db  «동체 대 블레이드 세기비»
         정의: 20log10( |c_0| / sqrt(Σ_{m≠0}|c_m|²) ). 저장소 기존 정의와 같은 양이다.
         민감: 고각·방위(동체 투영면적), 재질 가중, **가림 유무**.
         둔감: 절대 크기, PRF, rpm.
         ⚠⚠ 우리 커널에 가림이 없어서 동체가 과대 계상된다 → 이 지표가 네 지표 중
            **결함에 가장 크게 오염**된다. 절대값을 인용하지 말고 팔 사이 차이만 쓸 것.
    """
    tab = np.asarray(tab, complex)
    S = len(tab)
    f_rot = float(proto["f_rot_hz"])
    c = np.fft.fft(tab) / S                      # c[m], m = 0..S-1 (m>S/2 는 음수 차수)
    P = np.abs(c) ** 2
    m_idx = np.fft.fftfreq(S, d=1.0 / S).astype(int)      # 부호 있는 차수
    ac_mask = m_idx != 0
    p_ac_tot = float(P[ac_mask].sum())
    p_dc = float(P[m_idx == 0].sum())

    out = {}
    # ④ 동체 대 블레이드
    out["dc_ac_db"] = float(20 * np.log10(max(math.sqrt(p_dc), 1e-300) /
                                          max(math.sqrt(p_ac_tot), 1e-300)))
    out["ac_frac_db"] = -out["dc_ac_db"]
    out["mean_sigma_proxy"] = float(np.mean(np.abs(tab) ** 2))
    out["sigma_eq_mean_dbsm"] = float(
        10 * np.log10(max((4 * np.pi / proto["lam_m"] ** 2) * out["mean_sigma_proxy"], 1e-300)))

    # ① 플래시 대조비
    ac_t = tab - tab.mean()
    env = np.abs(ac_t)
    out["flash_contrast_db"] = float(20 * np.log10(max(env.max(), 1e-300) /
                                                   max(float(np.median(env)), 1e-300)))

    # ── ⭐ 대역 안/밖 가르기 — 이 지표들을 읽을 «자격» 을 판정한다 ────────────────
    #   운동학이 허용하는 최고 차수는 β 다(팁보다 빨리 도는 것은 없다). 여유 1.5배를 두고
    #   그 위에 있는 전력은 **물리가 아니라 이산화 잔차**로 본다(원판·구 널이 정확히 그렇다).
    band = max(2, int(math.ceil(1.5 * float(proto["beta"]))))
    in_band = ac_mask & (np.abs(m_idx) <= band)
    p_in = float(P[in_band].sum())
    out["band_order"] = int(band)
    out["in_band_ac_frac"] = float(p_in / max(p_ac_tot, 1e-300))
    out["in_band_ac_over_dc_db"] = float(10 * np.log10(max(p_in, 1e-300) / max(p_dc, 1e-300)))
    out["metrics_interpretable"] = bool(out["in_band_ac_frac"] >= 0.5)
    out["interpretable_note_ko"] = (
        "in_band_ac_frac < 0.5 이면 AC 전력의 절반 이상이 β(=f_tip/f_rot) 의 1.5배 위에 있다 "
        "— 운동학적으로 불가능한 자리다. 그런 팔(회전대칭 원판·구)의 폭·풍부도 지표는 "
        "이산화 잔차를 잰 것이므로 **해석하면 안 된다**. dc_ac_db 와 in_band_ac_over_dc_db 만 읽을 것.")
    # 수치바닥 대비 AC (참고) — 차수 상위 25% 의 중앙 전력을 바닥으로 본다
    hi = np.abs(m_idx) > max(4, int(0.75 * (S // 2)))
    floor = float(np.median(P[hi])) if hi.any() else 0.0
    out["spec_floor_power"] = floor
    out["ac_over_floor_db"] = float(10 * np.log10(max(p_ac_tot / max(floor * ac_mask.sum(), 1e-300),
                                                      1e-300))) if floor > 0 else float("inf")

    # ② 고차 풍부도
    if p_ac_tot > 0:
        p = P[ac_mask] / p_ac_tot
        nz = p[p > 0]
        H = float(-(nz * np.log(nz)).sum())
        out["n_eff_orders"] = float(math.exp(H))
        orders = np.abs(m_idx[ac_mask])
        order_pow = np.zeros(S // 2 + 1)
        np.add.at(order_pow, orders, p)
        cum = np.cumsum(order_pow)
        out["dominant_order"] = int(np.argmax(order_pow))
        out["order_p50"] = int(np.searchsorted(cum, 0.50) )
        out["order_p90"] = int(np.searchsorted(cum, 0.90))
        nb = max(1, int(prop_blades))
        comb = np.zeros_like(order_pow, dtype=bool)
        comb[nb::nb] = True
        out["blade_comb_frac"] = float(order_pow[comb].sum())
        out["blade_comb_order_step"] = nb
        # ③ 도플러 폭 (여러 문턱)
        pk = float(order_pow.max())
        for drop in (10.0, 20.0, 30.0):
            thr = pk * 10 ** (-drop / 10.0)
            above = np.where(order_pow >= thr)[0]
            edge = int(above.max()) if len(above) else 0
            out[f"order_edge_{int(drop)}db"] = edge
            out[f"fd_edge_{int(drop)}db_hz"] = float(edge * f_rot)
            out[f"width_ratio_{int(drop)}db"] = float(edge * f_rot / max(proto["f_tip_hz"], 1e-30))
        out["fd_edge_hz"] = out[f"fd_edge_{int(EDGE_DROP_DB)}db_hz"]
        out["width_ratio"] = out[f"width_ratio_{int(EDGE_DROP_DB)}db"]
    else:
        for kk in ("n_eff_orders", "dominant_order", "order_p50", "order_p90",
                   "blade_comb_frac", "fd_edge_hz", "width_ratio"):
            out[kk] = float("nan")
    return out


def ac_corr(a, b):
    """두 위상 표의 **AC 성분** 정규화 복소상관 (1.0 = 패턴 동일)."""
    a = np.asarray(a, complex) - np.mean(a)
    b = np.asarray(b, complex) - np.mean(b)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.abs(np.vdot(a, b)) / (na * nb)) if na > 0 and nb > 0 else 0.0


def summarize(vals):
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    if v.size == 0:
        return dict(mean=float("nan"), sd=float("nan"), n=0)
    return dict(mean=float(v.mean()), sd=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                min=float(v.min()), max=float(v.max()), n=int(v.size))


# =========================================================================== #
#          GPU PO 커널 — 조명된 면을 전부 **위상 맞춰** 더한다
# =========================================================================== #
#  왜 GPU 인가: 위상 격자 × 방위 24점 × 팔 4종 × 세대 3벌 을 다 돌려야 하고, 구면파 팔은
#  점마다 시선벡터가 달라 (위상, 점, 3) 짜리 배열을 만든다. 배치로 밀어야 현실적이다.
#
#  ⚠ 이 커널에는 정반사/확산 구분이 없다 — 조명된 면을 전부 위상 맞춰 더한다. 그래서
#    블레이드가 시선에 수직으로 설 때 **플래시가 저절로 나온다**(따로 넣은 항이 아니다).
def _rz(th):
    c, s = math.cos(th), math.sin(th)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _chunk_for(np_pts, wavefront, budget_bytes=None):
    """(위상, 점) 배열이 GPU 예산을 넘지 않도록 위상 묶음 크기를 정한다.
    구면파는 (위상, 점, 3) 짜리를 여러 벌 만들어 훨씬 무겁다."""
    if budget_bytes is None:
        try:
            from gpu import budget_mb
            budget_bytes = 0.35 * budget_mb() * 1024 ** 2
        except Exception:
            budget_bytes = 1.0e9
    per_row = (10.0 if wavefront != "plane" else 4.0) * float(np_pts) * 8.0
    return max(1, min(512, int(budget_bytes / max(per_row, 1.0))))


def field_static(torch, dev, P, N, W, k, A, R_t, wavefront):
    """비회전 부품(프레임·구)의 복소 산란장 — 스칼라 하나."""
    Pt = torch.as_tensor(np.ascontiguousarray(P), dtype=torch.float64, device=dev)
    Nt = torch.as_tensor(np.ascontiguousarray(N), dtype=torch.float64, device=dev)
    Wt = torch.as_tensor(np.ascontiguousarray(W), dtype=torch.float64, device=dev)
    zero = torch.zeros((), dtype=torch.float64, device=dev)
    if wavefront == "plane":
        u = torch.as_tensor(np.ascontiguousarray(A / R_t), dtype=torch.float64, device=dev)
        nu = Nt @ u
        ph = 2.0 * k * (Pt @ u)
        amp = torch.where(nu > 0, nu, zero) * Wt
    else:
        At = torch.as_tensor(np.ascontiguousarray(A), dtype=torch.float64, device=dev)
        D = At.unsqueeze(0) - Pt
        r = torch.linalg.norm(D, dim=1)
        ui = D / r.unsqueeze(1)
        nu = torch.einsum("ij,ij->i", Nt, ui)
        amp = torch.where(nu > 0, nu, zero) * Wt * (R_t * R_t) / (r * r)
        ph = -k * (2.0 * r - 2.0 * R_t)
    return complex(torch.sum(amp * torch.cos(ph)).item(),
                   torch.sum(amp * torch.sin(ph)).item())


def field_rotor(torch, dev, P, N, W, k, A, R_t, center, base_rad, dirn, phis_rad, wavefront):
    """로터 1개의 위상 표 E(φ).

    ⭐ 블레이드를 θ 만큼 돌리는 것은 **안테나를 −θ 만큼 돌려** 허브 로컬좌표에서 보는 것과
      엄밀히 같다(근사가 아니다):  |A − (Rz(θ)P + C)| = |Rz(−θ)(A−C) − P|.
      그래서 무거운 점구름은 한 번만 만들고, 위상마다 안테나 3벡터 하나만 돌린다."""
    Pt = torch.as_tensor(np.ascontiguousarray(P), dtype=torch.float64, device=dev)
    Nt = torch.as_tensor(np.ascontiguousarray(N), dtype=torch.float64, device=dev)
    Wt = torch.as_tensor(np.ascontiguousarray(W), dtype=torch.float64, device=dev)
    zero = torch.zeros((), dtype=torch.float64, device=dev)
    u = A / R_t
    Ac = A - np.asarray(center, float)
    n_ph = len(phis_rad)
    out = np.zeros(n_ph, complex)
    hub_ph = 2.0 * k * float(np.dot(np.asarray(center, float), u))
    hub = complex(math.cos(hub_ph), math.sin(hub_ph))
    chunk = _chunk_for(len(W), wavefront)
    s0 = 0
    while s0 < n_ph:
        ph_blk = np.asarray(phis_rad[s0:s0 + chunk], float)
        th = base_rad + dirn * ph_blk
        Rm = np.stack([_rz(-t) for t in th])                            # (b,3,3)
        try:
            if wavefront == "plane":
                Ul = torch.as_tensor(np.ascontiguousarray(np.einsum("bij,j->bi", Rm, u)),
                                     dtype=torch.float64, device=dev)   # (b,3)
                nu = Nt @ Ul.T                                          # (Np,b)
                phz = 2.0 * k * (Pt @ Ul.T)
                amp = torch.where(nu > 0, nu, zero) * Wt.unsqueeze(1)
                re = torch.sum(amp * torch.cos(phz), dim=0)
                im = torch.sum(amp * torch.sin(phz), dim=0)
                blk = (re.cpu().numpy() + 1j * im.cpu().numpy()) * hub
                del nu, phz, amp, re, im
            else:
                Al = torch.as_tensor(np.ascontiguousarray(np.einsum("bij,j->bi", Rm, Ac)),
                                     dtype=torch.float64, device=dev)   # (b,3)
                D = Al.unsqueeze(1) - Pt.unsqueeze(0)                   # (b,Np,3)
                r = torch.linalg.norm(D, dim=2)
                ui = D / r.unsqueeze(2)
                nu = torch.einsum("pj,bpj->bp", Nt, ui)
                amp = torch.where(nu > 0, nu, zero) * Wt.unsqueeze(0) * (R_t * R_t) / (r * r)
                phz = -k * (2.0 * r - 2.0 * R_t)
                re = torch.sum(amp * torch.cos(phz), dim=1)
                im = torch.sum(amp * torch.sin(phz), dim=1)
                blk = re.cpu().numpy() + 1j * im.cpu().numpy()
                del D, r, ui, nu, amp, phz, re, im
        except torch.OutOfMemoryError:
            # 공용 GPU 라 남의 작업이 언제든 들어온다 — 죽지 말고 배치를 반으로 줄여 계속한다.
            torch.cuda.empty_cache()
            if chunk == 1:
                raise
            chunk = max(1, chunk // 2)
            continue
        out[s0:s0 + len(ph_blk)] = blk
        s0 += len(ph_blk)
    return out


def look_and_antenna(az_deg, el_deg, range_m):
    a, e = math.radians(float(az_deg)), math.radians(float(el_deg))
    u = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    return u, range_m * u, float(range_m)


# =========================================================================== #
#                              WORKER (세대별 별도 프로세스)
# =========================================================================== #
def _worker(gen: str, gen_dir: str, drones_arms: list, fc: float, tag: str):
    """한 메쉬 세대에서 위상 표를 전부 계산해 npz 로 떨군다.

    별도 프로세스인 이유: 세대마다 다른 drones.py 를 import 해야 하는데 한 프로세스 안에서는
    모듈을 두 번 다르게 올릴 수 없다. sys.path 앞에 세대 디렉터리를 꽂고 새로 띄운다."""
    sys.path.insert(0, os.path.join(ROOT, "src"))
    if gen_dir:
        sys.path.insert(0, gen_dir)

    from gpu import pick                                 # ⚠ torch 보다 먼저 (CUDA 컨텍스트 고정)
    picked = pick(verbose=True)
    import torch

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from drones import (DRONES, build_frame, build_propeller, rotor_layout,   # noqa: E402
                        drone_gamma_map, build_drone)
    from rcs_po import mesh_to_points                                          # noqa: E402
    from geom import box, cylinder, uv_sphere                                  # noqa: E402

    lam = C0 / fc

    # ---------------- 프리미티브 팔 만들기 ---------------- #
    def _odd(n):
        return int(n) if int(n) % 2 == 1 else int(n) + 1

    def mesh_volume(m):
        V = np.asarray(m.v, float); F = np.asarray(m.f, int)
        p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        cr = np.cross(p1 - p0, p2 - p0)
        return float(np.sum(np.einsum("ij,ij->i", p0, cr)) / 6.0)

    def nn_spacing(P, n_probe=4000, seed=0):
        """점구름의 **실측 최근접이웃 간격 중앙값**[m].
        ⚠ `mesh_to_points` 는 삼각형당 최소 1점을 깔기 때문에, 프로펠러처럼 이미 촘촘한 메쉬는
          요청한 λ/N 이 구속되지 않는다. 팔끼리 «같은 λ/N» 을 썼다고 같은 촘촘함이 아니다.
          그래서 팔 사이 비교는 **실측 간격**으로 맞춘다."""
        from scipy.spatial import cKDTree
        P = np.asarray(P, float)
        if len(P) < 4:
            return float("nan")
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(P), size=min(n_probe, len(P)), replace=False)
        d, _ = cKDTree(P).query(P[idx], k=2)
        return float(np.median(d[:, 1]))

    def disc_mesh(R, thick, zc, target):
        """⭐ **균일 격자** 원판(위·아래 면 + 테두리 벽). geom.cylinder 의 부채꼴 캡은 중심으로
        갈수록 삼각형이 길쭉해 점밀도가 들쭉날쭉해진다 — 널 대조의 바닥을 재는 데 방해가 된다."""
        from geom import Mesh
        n_seg = _odd(max(9, int(math.ceil(2 * math.pi * R / target))))
        n_ring = max(2, int(math.ceil(R / target)))
        m = Mesh("prop")
        ang = np.arange(n_seg) * (2 * math.pi / n_seg)
        rad = np.linspace(0.0, R, n_ring + 1)
        idx = {}
        for ir, rr in enumerate(rad):
            for ia in range(n_seg):
                for sgn, zz in ((0, zc - thick / 2), (1, zc + thick / 2)):
                    idx[(ir, ia, sgn)] = m.add_vertex(rr * math.cos(ang[ia]),
                                                      rr * math.sin(ang[ia]), zz)
        for ir in range(n_ring):
            for ia in range(n_seg):
                ja = (ia + 1) % n_seg
                a, b = idx[(ir, ia, 1)], idx[(ir, ja, 1)]
                c, d = idx[(ir + 1, ja, 1)], idx[(ir + 1, ia, 1)]
                m.add_quad(a, b, c, d, "prop")                      # 윗면 (법선 +z)
                a, b = idx[(ir, ia, 0)], idx[(ir + 1, ia, 0)]
                c, d = idx[(ir + 1, ja, 0)], idx[(ir, ja, 0)]
                m.add_quad(a, b, c, d, "prop")                      # 아랫면 (법선 −z)
        for ia in range(n_seg):
            ja = (ia + 1) % n_seg
            m.add_quad(idx[(n_ring, ia, 0)], idx[(n_ring, ja, 0)],
                       idx[(n_ring, ja, 1)], idx[(n_ring, ia, 1)], "prop")   # 테두리 벽
        return m, n_seg, n_ring

    def disc_prop(prop, R, target):
        """프로펠러 → 같은 반경·같은 두께의 **회전대칭 원판** (물리적 변조가 정확히 0).

        블레이드와 «같은 크기로 움직이는데» 형상은 회전에 불변이다. 여기서 나오는 값이
        곧 «돌기만 하고 구조가 없을 때» 의 지표값이다.
        ⚠ 격자가 n_seg 각도로 잘려 있어 이산화 잔차는 **차수 n_seg** 에 나타난다 —
          관심 대역(≤β)보다 훨씬 위다. 그래서 대역 안에서는 깨끗한 널이다."""
        V = np.asarray(prop.v, float)
        th = float(V[:, 2].max() - V[:, 2].min()); zc = float(0.5 * (V[:, 2].max() + V[:, 2].min()))
        m, n_seg, n_ring = disc_mesh(R, th, zc, target)
        return m, dict(kind="disc", radius_m=R, thickness_m=th, z_center_m=zc,
                       n_seg=n_seg, n_ring=n_ring, n_tris=len(m.f),
                       n_tris_template=len(prop.f),
                       residual_order=n_seg,
                       note_ko=("균일 격자 원판. 이산화 잔차는 차수 n_seg 에만 나타나므로 "
                                "관심 대역 안에서는 물리적 변조 0 의 깨끗한 널이다."))

    def slab_prop(prop, R, Pcloud=None):
        """프로펠러 → **기하 프리미티브 블레이드**: 로터 평면에 누운 평판 2장(=하나의 판).

        구성 규칙(전부 실제 프로펠러 메쉬에서 계산한다):
          · 스팬  lx = 팁–팁 x 폭      ← 도플러 폭(f_tip)을 정하는 양이므로 **반드시 보존**
          · 코드  ly = 최대 y 폭        ← 정반사 면적을 정하는 양이므로 **보존**
          · 두께  lz = 부피 / (lx·ly)   ← 나머지 하나를 부피가 같아지도록 **푼다**
          · 높이  zc = 점구름의 면적가중 평균 z ← 블레이드가 실제로 놓인 높이

        ⚠ 스팬·코드를 놔두고 두께를 푸는 순서가 중요하다. 두께를 놔두고 코드를 풀면
          «날 세운 지느러미»(큰 면의 법선이 ±y)가 나와 회전 평판이 아니라 전혀 다른 물체가 된다.
        ⚠ 프롭 메쉬의 z 폭에는 허브가 들어 있어 «블레이드 두께» 가 아니다. 그래서 두께는
          z 폭에서 읽지 않고 부피에서 푼다."""
        V = np.asarray(prop.v, float)
        lx = float(V[:, 0].max() - V[:, 0].min())
        ly = float(V[:, 1].max() - V[:, 1].min())
        vol = abs(mesh_volume(prop))
        lz = vol / max(lx * ly, 1e-30)
        zc = float(np.mean(Pcloud[:, 2])) if Pcloud is not None else \
            float(0.5 * (V[:, 2].max() + V[:, 2].min()))
        m = box(lx, ly, lz, center=(0.0, 0.0, zc), group="prop")
        zb = float(V[:, 2].max() - V[:, 2].min())
        return m, dict(kind="slab", span_m=lx, chord_m=ly, thickness_m=lz, z_center_m=zc,
                       volume_m3=vol, aspect_chord_over_thickness=ly / max(lz, 1e-30),
                       prop_bbox_z_extent_m=zb,
                       thickness_over_bbox_z=lz / max(zb, 1e-30),
                       planform_area_m2=lx * ly,
                       n_tris=len(m.f), n_tris_template=len(prop.f),
                       note_ko=("스팬·코드는 실제 프롭 bbox 그대로, 두께는 부피가 같아지도록 풀었다. "
                                "큰 면의 법선이 ±z 라 로터 평면에 누운 평판이다(고전 회전평판 모델)."))

    # ---------------- 팔별 점구름 준비 ---------------- #
    FRAME_DIV, BLADE_DIV, BLADE_N = 6.0, 11.0, 26

    def clouds_for(key, arm):
        """팔 하나의 점구름을 만든다.

        ⭐ **모든 팔이 같은 요청 간격(프레임 λ/6 · 회전부 λ/11, 저장소 규약)을 쓴다.**
          다만 실효 간격은 팔마다 다르다 — `mesh_to_points` 가 삼각형당 최소 1점을 깔기 때문에
          이미 촘촘히 삼각분할된 CAD 블레이드는 λ/11 을 요청해도 실효 λ/100~λ/300 이 되고,
          프리미티브(원판·평판·구)는 λ/11 근처에 머문다.
          ⚠ 그래서 «프리미티브가 성겨서 달라 보이는 것 아니냐» 는 반론이 가능하다.
            이 반론은 팔 이름에 `_fine` 을 붙인 4배 촘촘한 팔로 정면 반박한다 — 4배 촘촘히
            깔아도 지표가 안 움직이면 밀도 차이는 원인이 아니다.
          ⚠ 두 밀도 모두 λ/4 보다 훨씬 촘촘하다(인접점 왕복 위상차 ≪ π) — 즉 둘 다 수렴 영역이다."""
        s = DRONES[key]
        base_arm, fine = (arm[:-5], True) if arm.endswith("_fine") else (arm, False)
        bdiv = BLADE_DIV * (4.0 if fine else 1.0)
        fdiv = FRAME_DIV * (4.0 if fine else 1.0)
        spac = lam / bdiv
        gm = drone_gamma_map(s)
        frame = build_frame(s)
        Pf, Nf, dAf, wf = mesh_to_points(frame, lam / fdiv, gamma=gm)
        Wf = dAf * wf
        prop = build_propeller(s, n=BLADE_N)
        R = float(s.prop_dia_mm) / 2000.0
        meta = {}
        if base_arm == "mesh":
            pa, pb = prop, None                      # pb=None → 점구름을 y-거울로 만든다
        elif base_arm == "disc":
            pa, meta = disc_prop(prop, R, spac); pb = pa
        elif base_arm == "slab":
            P0, _, _, _ = mesh_to_points(prop, spac, gamma=gm)
            pa, meta = slab_prop(prop, R, P0); pb = pa
        elif base_arm == "sphere":
            drone = build_drone(s)
            vol = abs(mesh_volume(drone))
            r_eq = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
            seg = _odd(max(9, int(math.ceil(2 * math.pi * r_eq / spac))))
            rings = max(3, int(math.ceil(math.pi * r_eq / spac)))
            sph = uv_sphere(r_eq, seg=seg, rings=rings, group="sph")
            Ps, Ns, dAs = mesh_to_points(sph, spac)
            meta = dict(kind="sphere_whole", r_equal_volume_m=r_eq, volume_m3=vol,
                        seg=seg, rings=rings, n_tris=len(sph.f), n_tris_drone=len(drone.f),
                        gamma_abs=1.0, requested_spacing_m=float(spac),
                        actual_spacing_m=nn_spacing(Ps), residual_order=seg,
                        note_ko=("기체 전체를 등가부피 구 하나로 교체(|Γ|=1, PEC). 시선을 같은 "
                                 "위상격자로 돌린다 — 물리적 변조는 0 이므로 남는 값이 "
                                 "**계산기 자체의 바닥**이다. 지표의 0점을 여기서 잡는다."))
            return dict(arm=arm, frame=None, rotor_cloud=(Ps, Ns, dAs),
                        rotor_cloud_m=(Ps, Ns, dAs),
                        rotors=[dict(center=(0.0, 0.0, 0.0), base_ang=0.0, dir=1)],
                        meta=meta, spec=s, n_frame_pts=0, n_blade_pts=len(Ps))
        else:
            raise ValueError(arm)
        Pp, Np_, dAp, wp = mesh_to_points(pa, spac, gamma=gm)
        if pb is None:
            # ⭐ 반대회전 로터에는 **거울상 프롭**이 달린다(실물 멀티로터 규약).
            #   여기서는 점구름을 y-거울로 뒤집어 만든다 — 세대마다 drones.py 가
            #   mirror= 인자를 갖고 있기도 없기도 해서(2026-07-28 도입), 세대 사이 비교가
            #   «형상» 이 아니라 «코드 기능» 차이로 오염되는 것을 막기 위해서다.
            #   반사 M=diag(1,−1,1) 에서 바깥법선은 M·n̂ 로 그대로 간다(부호 보정 불필요).
            Pm = Pp * np.array([1.0, -1.0, 1.0])
            Nm_ = Np_ * np.array([1.0, -1.0, 1.0])
            dAm, wm = dAp, wp
        else:
            Pm, Nm_, dAm, wm = mesh_to_points(pb, spac, gamma=gm)
        act = float(nn_spacing(Pp))
        meta = dict(meta, requested_spacing_m=float(spac),
                    requested_lambda_over=float(bdiv),
                    actual_spacing_m=act, lambda_over_actual=float(lam / max(act, 1e-12)),
                    n_tris_rotating=len(pa.f))
        return dict(arm=arm, frame=(Pf, Nf, Wf), rotor_cloud=(Pp, Np_, dAp * wp),
                    rotor_cloud_m=(Pm, Nm_, dAm * wm), rotors=rotor_layout(s),
                    meta=meta, spec=s, n_frame_pts=len(Wf), n_blade_pts=len(Pp))

    # ---------------- 실행 ---------------- #
    res = {}
    tables = {}
    for key, arms in drones_arms:
        if key not in DRONES:
            res[key] = dict(absent=True)
            continue
        s = DRONES[key]
        proto = derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
        k_wav = 2.0 * math.pi / lam
        phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
        az_list = np.arange(N_AZ) * (360.0 / N_AZ)
        entry = dict(protocol=proto, spec=dict(
            name=s.name, prop_dia_mm=float(s.prop_dia_mm), prop_blades=int(s.prop_blades),
            hover_rpm=float(s.hover_rpm), num_rotors=int(s.num_rotors),
            body_lwh_mm=[float(s.body_l_mm), float(s.body_w_mm), float(s.body_h_mm)]),
            arms={})
        try:
            dr = build_drone(s)
            V = np.asarray(dr.v, float)
            span = float(max(V[:, 0].max() - V[:, 0].min(), V[:, 1].max() - V[:, 1].min()))
            entry["extent_m"] = span
            entry["farfield_2D2_over_lam_m"] = 2.0 * span ** 2 / lam
            entry["range_over_farfield"] = RANGE_M / (2.0 * span ** 2 / lam)
        except Exception as e:                                    # pragma: no cover
            entry["extent_error"] = str(e)

        for arm in arms:
            t0 = time.time()
            cl = clouds_for(key, arm)
            am = dict(meta=cl["meta"], n_frame_pts=cl["n_frame_pts"],
                      n_blade_pts=cl["n_blade_pts"], wavefronts={})
            for wf in ("spherical", "plane"):
                T = np.zeros((len(az_list), proto["n_phase"]), complex)
                for ia, az in enumerate(az_list):
                    u, A, R_t = look_and_antenna(az, EL_DEG, RANGE_M)
                    Ef = 0.0 + 0.0j
                    if cl["frame"] is not None:
                        Pf, Nf, Wf = cl["frame"]
                        Ef = field_static(torch, dev, Pf, Nf, Wf, k_wav, A, R_t, wf)
                    tot = np.full(proto["n_phase"], Ef, complex)
                    for rot in cl["rotors"]:
                        d = float(rot["dir"])
                        P, N, W = cl["rotor_cloud"] if d > 0 else cl["rotor_cloud_m"]
                        tot += field_rotor(torch, dev, P, N, W, k_wav, A, R_t, rot["center"],
                                           math.radians(float(rot["base_ang"])), d,
                                           phis, wf)
                    T[ia] = tot
                am["wavefronts"][wf] = True
                tables[f"{tag}|{gen}|{key}|{arm}|{wf}"] = T
            am["seconds"] = float(time.time() - t0)
            entry["arms"][arm] = am
            print(f"  [{gen}/{tag}] {key:10s} {arm:7s} "
                  f"n_phase={proto['n_phase']:4d} pts(f/b)={cl['n_frame_pts']}/{cl['n_blade_pts']} "
                  f"[{am['seconds']:.1f}s]", flush=True)
        res[key] = entry

    os.makedirs(SCRATCH, exist_ok=True)
    npz_path = os.path.join(SCRATCH, f"tab_{tag}_{gen}.npz")
    np.savez_compressed(npz_path, **{k.replace("|", "__"): v for k, v in tables.items()})
    with open(os.path.join(SCRATCH, f"meta_{tag}_{gen}.json"), "w") as f:
        json.dump(dict(gen=gen, fc=fc, tag=tag, gpu=picked, drones=res,
                       az_deg=list(np.arange(N_AZ) * (360.0 / N_AZ))), f, ensure_ascii=False)
    print(f"  → {npz_path}", flush=True)


# =========================================================================== #
#                    커널 검증 게이트 — 저장소 numpy 판과 일치하는가
# =========================================================================== #
def _verify_gate():
    """⭐ 이 파일의 GPU 커널이 저장소의 numpy 판과 **같은 값**을 내는가.

    기준은 `src/microdoppler_nearfield.phase_table` 이다 — 저장소가 이미 쓰고 있는, 검증을
    거친 구면파/평면파 PO 위상표 구현이다. 같은 점구름·같은 규약이므로 두 결과는
    부동소수 오차 수준으로 같아야 한다. 여기서 틀리면 아래 숫자는 전부 무효다."""
    p = os.path.join(SCRATCH, "r16_gate.py")
    code = '''
import sys, json, math, os
import numpy as np
sys.path.insert(0, %r)
sys.path.insert(0, %r)
import report16_base as R
from gpu import pick
pick(verbose=False)
import torch
import microdoppler_nearfield as mdnf
from drones import DRONES, build_frame, build_propeller, rotor_layout, drone_gamma_map
from rcs_po import mesh_to_points
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
out = {"device": str(dev)}
n_phase = 32
for key in ("mini2", "matrice4e"):
    s = DRONES[key]
    lam = R.C0 / R.FC_MAIN
    k = 2 * math.pi / lam
    gm = drone_gamma_map(s)
    Pf, Nf, dAf, wf_ = mesh_to_points(build_frame(s), lam / 6.0, gamma=gm)
    Pp, Np_, dAp, wp = mesh_to_points(build_propeller(s, n=26), lam / 11.0, gamma=gm)
    Pm, Nm_, dAm, wm = mesh_to_points(build_propeller(s, n=26, mirror=True), lam / 11.0, gamma=gm)
    phis = np.linspace(0.0, 2 * math.pi, n_phase, endpoint=False)
    u, A, R_t = R.look_and_antenna(0.0, R.EL_DEG, R.RANGE_M)
    for wfront in ("plane", "spherical"):
        _, ref, info = mdnf.phase_table(s, R.FC_MAIN, R.RANGE_M, 0.0, R.EL_DEG,
                                        wavefront=wfront, n_phase=n_phase, period_deg=360.0,
                                        frame_div=6.0, blade_div=11.0, blade_n=26)
        got = np.full(n_phase, R.field_static(torch, dev, Pf, Nf, dAf * wf_, k, A, R_t, wfront),
                      complex)
        for rot in rotor_layout(s):
            d = float(rot["dir"])
            P, N, W = (Pp, Np_, dAp * wp) if d > 0 else (Pm, Nm_, dAm * wm)
            got += R.field_rotor(torch, dev, P, N, W, k, A, R_t, rot["center"],
                                 math.radians(float(rot["base_ang"])), d, phis, wfront)
        num = float(np.max(np.abs(got - ref))); den = float(np.max(np.abs(ref)))
        out["%%s|%%s" %% (key, wfront)] = dict(max_abs_diff=num, max_abs_ref=den,
                                            max_rel=num / max(den, 1e-300), n_phase=n_phase)
# ── 거울상 프롭 규약 자기검사 ────────────────────────────────────────────────
#   세대마다 drones.build_propeller 가 mirror= 인자를 갖고 있기도 없기도 해서(2026-07-28 도입),
#   report16 은 점구름을 y-거울로 뒤집어 만든다. 그 방식이 저장소의 mirror=True 와 같은
#   산란장을 내는지 확인한다. 삼각분할 표본 위치가 달라 비트 단위로 같지는 않다 — 크기를 잰다.
mir = {}
for key in ("mini2", "matrice4e"):
    s = DRONES[key]
    lam = R.C0 / R.FC_MAIN; k = 2 * math.pi / lam
    gm = drone_gamma_map(s)
    Pp, Np_, dAp, wp = mesh_to_points(build_propeller(s, n=26), lam / 11.0, gamma=gm)
    Pm, Nm_, dAm, wm = mesh_to_points(build_propeller(s, n=26, mirror=True), lam / 11.0, gamma=gm)
    Pr = Pp * np.array([1.0, -1.0, 1.0]); Nr = Np_ * np.array([1.0, -1.0, 1.0])
    u, A, R_t = R.look_and_antenna(0.0, R.EL_DEG, R.RANGE_M)
    phis = np.linspace(0.0, 2 * math.pi, 64, endpoint=False)
    a = R.field_rotor(torch, dev, Pm, Nm_, dAm * wm, k, A, R_t, (0., 0., 0.), 0.0, -1.0,
                      phis, "spherical")
    b = R.field_rotor(torch, dev, Pr, Nr, dAp * wp, k, A, R_t, (0., 0., 0.), 0.0, -1.0,
                      phis, "spherical")
    ca = a - a.mean(); cb = b - b.mean()
    mir[key] = dict(
        ac_corr=float(abs(np.vdot(ca, cb)) / (np.linalg.norm(ca) * np.linalg.norm(cb))),
        level_ratio_db=float(10 * np.log10(np.mean(abs(b) ** 2) / np.mean(abs(a) ** 2))),
        rel_rms=float(np.linalg.norm(b - a) / np.linalg.norm(a)))
out["mirror_convention_selfcheck"] = mir
print("JSON" + json.dumps(out))
''' % (os.path.dirname(os.path.abspath(__file__)), os.path.join(ROOT, "src"))
    os.makedirs(SCRATCH, exist_ok=True)
    with open(p, "w") as f:
        f.write(code)
    r = subprocess.run([sys.executable, p], cwd=ROOT, capture_output=True, text=True)
    line = [x for x in r.stdout.splitlines() if x.startswith("JSON")]
    if not line:
        return dict(verdict="ERROR", stderr=r.stderr[-1500:])
    out = json.loads(line[0][4:])
    rels = [v["max_rel"] for v in out.values() if isinstance(v, dict) and "max_rel" in v]
    out["tolerance"] = 1e-9
    out["verdict"] = "PASS" if rels and max(rels) < 1e-9 else "FAIL"
    out["reference"] = "src/microdoppler_nearfield.phase_table (numpy, repo-standard)"
    out["what_ko"] = ("이 파일의 GPU 커널이 저장소 numpy 판과 같은 위상표를 내는가. "
                      "같은 점구름·같은 규약이므로 상대오차 1e-9 미만이어야 한다. "
                      "여기서 틀리면 아래 숫자는 전부 무효다.")
    return out


# =========================================================================== #
#                                   DRIVER
# =========================================================================== #
def _prepare_gen_dirs():
    """옛 세대의 drones.py / drone_cad.py 를 git 에서 꺼내 스크래치에 놓는다(원본 불변)."""
    os.makedirs(SCRATCH, exist_ok=True)
    dirs = {}
    for gen, commit in GEN_COMMITS.items():
        if commit is None:
            dirs[gen] = None
            continue
        d = os.path.join(SCRATCH, f"src_{gen}")
        os.makedirs(d, exist_ok=True)
        for fn in ("drones.py", "drone_cad.py"):
            p = os.path.join(d, fn)
            if not os.path.exists(p):
                blob = subprocess.run(["git", "show", f"{commit}:src/{fn}"], cwd=ROOT,
                                      capture_output=True, text=True, check=True).stdout
                with open(p, "w") as f:
                    f.write(blob)
        dirs[gen] = d
    return dirs


def _mesh_fingerprints(gen_dirs):
    """세대별 메쉬 지문 — «무엇이 실제로 바뀌었나» 를 해시로 확정한다."""
    code = r'''
import sys, hashlib, json
import numpy as np
extra = sys.argv[1]
sys.path.insert(0, sys.argv[2])
if extra != "-": sys.path.insert(0, extra)
from drones import DRONES, build_frame, build_propeller, rotor_layout
def h(m):
    v = np.ascontiguousarray(np.asarray(m.v, float))
    f = np.ascontiguousarray(np.asarray(m.f, np.int64))
    return hashlib.sha1(v.tobytes() + f.tobytes()).hexdigest()[:16]
o = {}
for k in json.loads(sys.argv[3]):
    if k not in DRONES: o[k] = None; continue
    s = DRONES[k]
    o[k] = dict(frame_sha=h(build_frame(s)), prop_sha=h(build_propeller(s, n=26)),
                rotor_centers=[[round(float(c),6) for c in r["center"]] for r in rotor_layout(s)],
                base_ang=[float(r["base_ang"]) for r in rotor_layout(s)],
                prop_dia_mm=float(s.prop_dia_mm), hover_rpm=float(s.hover_rpm))
print("JSON" + json.dumps(o))
'''
    p = os.path.join(SCRATCH, "r16_fp.py")
    with open(p, "w") as f:
        f.write(code)
    keys = json.dumps(["matrice4e", "mini2", "mavic4pro"])
    out = {}
    for gen, d in gen_dirs.items():
        r = subprocess.run([sys.executable, p, d or "-", os.path.join(ROOT, "src"), keys],
                           cwd=ROOT, capture_output=True, text=True)
        line = [x for x in r.stdout.splitlines() if x.startswith("JSON")]
        out[gen] = json.loads(line[0][4:]) if line else dict(error=r.stderr[-400:])
    return out


def run_workers(gen_dirs, plan, fc, tag):
    for gen, drones_arms in plan.items():
        p = os.path.join(SCRATCH, f"r16_worker_{tag}_{gen}.py")
        with open(p, "w") as f:
            f.write("import sys, json\n"
                    f"sys.path.insert(0, {os.path.dirname(os.path.abspath(__file__))!r})\n"
                    "import report16_base as R\n"
                    "R._worker(sys.argv[1], sys.argv[2] or None, json.loads(sys.argv[3]),"
                    " float(sys.argv[4]), sys.argv[5])\n")
        print(f"▶ worker {tag}/{gen}: {drones_arms}", flush=True)
        r = subprocess.run([sys.executable, p, gen, gen_dirs[gen] or "",
                            json.dumps(drones_arms), str(fc), tag],
                           cwd=ROOT)
        if r.returncode != 0:
            raise RuntimeError(f"worker {gen} failed ({r.returncode})")


def load_tables(tag):
    tabs, metas = {}, {}
    for gen in GEN_COMMITS:
        pz = os.path.join(SCRATCH, f"tab_{tag}_{gen}.npz")
        mj = os.path.join(SCRATCH, f"meta_{tag}_{gen}.json")
        if not os.path.exists(pz):
            continue
        z = np.load(pz)
        for k in z.files:
            tabs[k.replace("__", "|")] = z[k]
        metas[gen] = json.load(open(mj))
    return tabs, metas


def metrics_block(tabs, metas, tag, gen, key, arm, wf):
    k = f"{tag}|{gen}|{key}|{arm}|{wf}"
    if k not in tabs:
        return None
    T = tabs[k]
    proto = metas[gen]["drones"][key]["protocol"]
    nb = metas[gen]["drones"][key]["spec"]["prop_blades"]
    per_az = [md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]
    keys = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90", "dominant_order",
            "blade_comb_frac", "fd_edge_hz", "width_ratio", "dc_ac_db", "ac_frac_db",
            "sigma_eq_mean_dbsm", "ac_over_floor_db", "in_band_ac_frac",
            "in_band_ac_over_dc_db", "width_ratio_10db", "width_ratio_30db")
    return dict(per_az={kk: summarize([m[kk] for m in per_az]) for kk in keys},
                az0={kk: per_az[0][kk] for kk in keys},
                interpretable_frac=float(np.mean([m["metrics_interpretable"] for m in per_az])),
                band_order=int(per_az[0]["band_order"]),
                n_az=int(T.shape[0]))


# --------------------------------------------------------------------------- #
#  07-29 아카이브 대조 — 그때 저장된 복소장에 **같은 지표**를 적용한다
# --------------------------------------------------------------------------- #
def archive_0729():
    """outputs/report1_microdoppler.npz (2026-07-29) 에 같은 지표를 대 본다.

    ⚠ 세 가지가 한꺼번에 다르다: 메쉬 세대(07-27), **엔진(SBR=가림 있음)**, 표본화 규약
      (n_phase=144·period=180°·prf=20000·평면파·거리 무한). 그래서 이 숫자는 «옛날 값이
      대략 어디 있었나» 의 참고점이지 통제된 A/B 가 아니다. 통제된 A/B 는 G_0727 팔이다."""
    p = os.path.join(ROOT, "outputs", "report1_microdoppler.npz")
    if not os.path.exists(p):
        return dict(absent=True)
    z = np.load(p)
    prf = float(z["prf"])
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from microdoppler_nearfield import md_metrics as legacy_metrics
    out = dict(file=os.path.relpath(p, ROOT),
               mtime=time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p))),
               prf_hz=prf, engine="SBR (occlusion) via microdoppler.microdoppler_sbr",
               config_note_ko=("cfg: fc 3.5 GHz · az 0° · el 15° · prf 20 kHz · n_t 6144 · "
                               "n_phase 144 · period 180°(=360/블레이드수, 근사) · 평면파 · 무한거리"),
               drones={})
    r1 = json.load(open(os.path.join(ROOT, "outputs", "report1.json")))
    for kdr in z.files:
        if kdr == "prf":
            continue
        E = z[kdr]
        d = r1.get("microdoppler", {}).get("drones", {}).get(kdr, {})
        m = legacy_metrics(E, prf, flash_hz=d.get("flash_hz"), f_tip=d.get("f_tip_hz"))
        out["drones"][kdr] = dict(
            legacy=dict(dc_ac_db=m["dc_ac_db"], flash_contrast_db=m["flash_contrast_db"],
                        fd_edge_hz=m["fd_edge_hz"], harmonic_frac=m["harmonic_frac"]),
            in_band=in_band_hz(E, prf, d.get("f_tip_hz")),
            reported=dict(rpm=d.get("rpm"), f_tip_hz=d.get("f_tip_hz"),
                          flash_hz=d.get("flash_hz"),
                          sbr_ratio_db=d.get("sbr", {}).get("ratio_db"),
                          po_ratio_db=d.get("po", {}).get("ratio_db")))
    out["in_band_finding_ko"] = (
        "⭐ 같은 «대역 안» 잣대를 07-29 아카이브에 대 본 결과다. in_band_ac_frac 은 AC 전력 중 "
        "|f| ≤ 1.5·f_tip 에 있는 몫이다 — 팁속도보다 빠른 자리에 있는 전력은 물리가 아니다. "
        "새 PO 판은 전부 1.000 인데, 07-29 SBR 판은 그보다 훨씬 낮다: SBR 은 위상마다 광선을 "
        "다시 쏘기 때문에 재추적 잡음이 도플러축 전체에 깔린다. 그래서 그때 적혀 있던 "
        "fd_edge_hz 가 f_tip 의 5배씩 나왔던 것이다(잡음의 가장자리를 잰 것).")
    return out


def in_band_hz(E, prf, f_tip):
    """시계열 → «운동학적으로 가능한 대역(|f| ≤ 1.5·f_tip)» 에 있는 AC 전력 몫.
    위상표가 아니라 임의 시계열에도 쓸 수 있는 판(아카이브 대조용)."""
    if not f_tip or not np.isfinite(f_tip):
        return dict(in_band_ac_frac=float("nan"))
    E = np.asarray(E)
    ac = E - E.mean()
    n = len(ac)
    S = np.abs(np.fft.fft(ac * np.hanning(n))) ** 2
    f = np.fft.fftfreq(n, d=1.0 / float(prf))
    tot = float(S.sum())
    inb = float(S[np.abs(f) <= 1.5 * float(f_tip)].sum())
    return dict(in_band_ac_frac=inb / max(tot, 1e-300),
                band_hz=1.5 * float(f_tip),
                dc_ac_db=float(20 * np.log10(max(abs(E.mean()), 1e-300) /
                                             max(np.std(E), 1e-300))))


def legacy_on_new(tabs, metas, tag, gen, key, arm, wf):
    """새 위상 표를 **옛 지표 구현**(microdoppler_nearfield.md_metrics)으로도 재 본다.
    지표를 갈아끼운 것이 결과를 바꾼 것은 아닌지 확인하는 다리."""
    k = f"{tag}|{gen}|{key}|{arm}|{wf}"
    if k not in tabs:
        return None
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from microdoppler_nearfield import md_metrics as legacy_metrics
    T = tabs[k]
    proto = metas[gen]["drones"][key]["protocol"]
    prf = proto["prf_hz"]; S = proto["n_phase"]; nrev = proto["n_rev"]
    rows = []
    for i in range(T.shape[0]):
        E = np.tile(T[i], nrev)                       # 표를 그대로 이어 붙이면 슬로타임이다
        rows.append(legacy_metrics(E, prf, flash_hz=proto["flash_hz"], f_tip=proto["f_tip_hz"]))
    return {kk: summarize([r[kk] for r in rows])
            for kk in ("dc_ac_db", "flash_contrast_db", "fd_edge_hz", "harmonic_frac")}


# --------------------------------------------------------------------------- #
#  수렴 점검 — 규약이 «충분히 촘촘한가» 를 스스로 검사한다
# --------------------------------------------------------------------------- #
def convergence_check(gen_dirs):
    """위상 스텝 수 S 와 점구름 밀도를 각각 2배로 올려 지표가 흔들리는지 본다.
    규약이 방어 가능하려면, 2배로 올려도 지표가 «측정하려는 차이» 보다 훨씬 덜 움직여야 한다."""
    p = os.path.join(SCRATCH, "r16_conv.py")
    code = '''
import sys, json, math, os
import numpy as np
sys.path.insert(0, %r)
sys.path.insert(0, %r)
import report16_base as R
sys.path.insert(0, os.path.join(R.ROOT, "src"))
from gpu import pick
pick(verbose=False)
from drones import DRONES
import microdoppler_nearfield as mdnf
out = {}
for key in ("mini2", "matrice4e"):
    s = DRONES[key]
    base = R.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, R.FC_MAIN)
    rows = {}
    for label, npz, bdiv, fdiv in (("base", base["n_phase"], 11.0, 6.0),
                                   ("phase_x2", base["n_phase"] * 2, 11.0, 6.0),
                                   ("points_fine", base["n_phase"], 44.0, 24.0)):
        _, tab, info = mdnf.phase_table(s, R.FC_MAIN, R.RANGE_M, 0.0, R.EL_DEG,
                                        wavefront="spherical", n_phase=npz, period_deg=360.0,
                                        frame_div=fdiv, blade_div=bdiv, blade_n=26)
        pr = dict(base); pr["n_phase"] = npz
        m = R.md_metrics16(tab, pr, s.prop_blades)
        rows[label] = dict(n_phase=npz, blade_div=bdiv, frame_div=fdiv,
                           n_blade_pts=int(info["n_blade_pts"]),
                           n_frame_pts=int(info["n_frame_pts"]),
                           blade_spacing_actual_median_m=float(info["blade_spacing_actual_median_m"]),
                           flash_contrast_db=m["flash_contrast_db"],
                           n_eff_orders=m["n_eff_orders"], order_p90=m["order_p90"],
                           width_ratio=m["width_ratio"], dc_ac_db=m["dc_ac_db"],
                           sigma_eq_mean_dbsm=m["sigma_eq_mean_dbsm"])
    out[key] = rows
print("JSON" + json.dumps(out))
''' % (os.path.dirname(os.path.abspath(__file__)), os.path.join(ROOT, "src"))
    with open(p, "w") as f:
        f.write(code)
    r = subprocess.run([sys.executable, p], cwd=ROOT, capture_output=True, text=True)
    line = [x for x in r.stdout.splitlines() if x.startswith("JSON")]
    if not line:
        return dict(error=r.stderr[-1200:])
    res = json.loads(line[0][4:])
    for key, rows in res.items():
        b = rows["base"]
        for lab in ("phase_x2", "points_fine"):
            rows[lab + "_delta"] = {kk: rows[lab][kk] - b[kk]
                                    for kk in ("flash_contrast_db", "n_eff_orders",
                                               "width_ratio", "dc_ac_db", "sigma_eq_mean_dbsm")}
    res["_what_ko"] = ("위상 스텝 수를 2배로, 점구름을 촘촘히 2배로 올렸을 때 지표가 얼마나 "
                       "움직이나. 이 흔들림보다 작은 «메쉬 세대 차이» 는 주장할 수 없다.")
    return res


# --------------------------------------------------------------------------- #
#  그림
# --------------------------------------------------------------------------- #
def make_figure(J, tabs, metas, tabs_hi, metas_hi, tag="main"):
    """4×3 판. 그림 안 글씨는 전부 영어(저장소 규약)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import gridspec
    from scipy.signal import spectrogram as _sp

    plt.rcParams.update({"figure.facecolor": "white", "savefig.facecolor": "white",
                         "axes.grid": True, "grid.alpha": 0.25, "font.size": 9})
    C_MINI, C_M4E = "#1565c0", "#2e7d32"
    C_SLAB, C_DISC, C_SPH, C_OLD = "#ef6c00", "#00838f", "#c62828", "#9e9e9e"
    DCOL = {"mini2": C_MINI, "matrice4e": C_M4E}
    ARMS = ["sphere", "disc", "slab", "mesh"]
    ALAB = ["sphere\n(whole body)", "disc\n(spins, no structure)",
            "slab\n(primitive blade)", "CAD mesh\n(real blade)"]

    fig = plt.figure(figsize=(16.8, 17.2))
    gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.58, wspace=0.32,
                           top=0.918, bottom=0.055, left=0.062, right=0.978)

    def per_az(key, arm, wf="spherical"):
        return J["arms"].get(key, {}).get(arm, {}).get(wf, {}).get("per_az", {})

    def bars(ax, metric, arms=ARMS, labels=ALAB, keys=("mini2", "matrice4e")):
        w = 0.38
        for i, key in enumerate(keys):
            ys = [per_az(key, a).get(metric, {}).get("mean", np.nan) for a in arms]
            es = [per_az(key, a).get(metric, {}).get("sd", np.nan) for a in arms]
            ax.bar(np.arange(len(arms)) + (i - 0.5) * w, ys, w, yerr=es, capsize=2.5,
                   color=DCOL[key], label=key, zorder=3)
        ax.set_xticks(np.arange(len(arms)))
        ax.set_xticklabels(labels, fontsize=7.6)
        ax.legend(fontsize=8)

    # ── row 0 ─────────────────────────────────────────────────────────────── #
    for col, key in enumerate(("mini2", "matrice4e")):
        ax = fig.add_subplot(gs[0, col])
        T = tabs[f"{tag}|G_0804|{key}|mesh|spherical"]
        pr = metas["G_0804"]["drones"][key]["protocol"]
        S, prf = pr["n_phase"], pr["prf_hz"]
        E = np.tile(T[0], 8)
        nper = max(32, S // 4)
        f, tt, Sxx = _sp(E - E.mean(), fs=prf, nperseg=nper,
                         noverlap=nper - max(1, nper // 16), nfft=4 * nper, detrend=False,
                         window="hann", return_onesided=False, scaling="spectrum",
                         mode="magnitude")
        f = np.fft.fftshift(f); Sxx = np.fft.fftshift(Sxx, axes=0)
        Sdb = 20 * np.log10(Sxx / (Sxx.max() + 1e-30) + 1e-12)
        m = ax.pcolormesh(tt * 1e3, f, Sdb, cmap="magma", vmin=-45, vmax=0, shading="auto")
        for sgn in (1, -1):
            ax.axhline(sgn * pr["f_tip_hz"], color="#4fc3f7", ls="--", lw=1.2)
        ax.set_ylim(-1.45 * pr["f_tip_hz"], 1.45 * pr["f_tip_hz"])
        ax.set_xlabel("slow time [ms]"); ax.set_ylabel("Doppler [Hz]")
        ax.set_title(f"{key} · new mesh (2026-08-04) · az 0°\n"
                     f"{pr['f_rot_hz']*60:.0f} rpm · $f_{{tip}}$ {pr['f_tip_hz']:.0f} Hz "
                     f"(dashed) · blade flash {pr['flash_hz']:.0f} Hz",
                     fontsize=9.3, fontweight="bold")
        ax.grid(False)
        fig.colorbar(m, ax=ax, fraction=0.046, pad=0.02, label="dB (peak = 0)")

    ax = fig.add_subplot(gs[0, 2])
    pr = metas["G_0804"]["drones"]["matrice4e"]["protocol"]
    for arm, c_, lab, lw in (("slab", C_SLAB, "flat-slab blades (primitive)", 1.0),
                             ("mesh", C_M4E, "CAD mesh blades", 1.7),
                             ("disc", C_DISC, "rotationally symmetric disc", 1.0),
                             ("sphere", C_SPH, "equal-volume sphere (whole body)", 1.0)):
        k = f"{tag}|G_0804|matrice4e|{arm}|spherical"
        if k not in tabs:
            continue
        T = tabs[k]; S = T.shape[1]
        c = np.fft.fft(T[0]) / S
        mo = np.fft.fftfreq(S, d=1.0 / S).astype(int)
        o = np.argsort(mo)
        # ⭐ 각 팔을 **자기 DC** 로 정규화한다 — 팔마다 따로 최대값으로 맞추면 널이 얼마나
        #   아래에 있는지가 사라진다(이 그림의 핵심이 바로 그 간격이다).
        ref = max(abs(c[0]) ** 2, 1e-300)
        ax.plot(mo[o], 10 * np.log10(np.maximum(np.abs(c[o]) ** 2 / ref, 1e-18)),
                lw=lw, color=c_, label=lab)
    for sgn in (1, -1):
        ax.axvline(sgn * pr["beta"], color="#455a64", ls=":", lw=1.3)
    ax.annotate(r"$\beta = f_{tip}/f_{rot}$" + f" = {pr['beta']:.1f}",
                (pr["beta"] * 0.97, -8), fontsize=8, ha="right", va="top", color="#455a64",
                rotation=90)
    nullmin = min(per_az("matrice4e", a).get("in_band_ac_over_dc_db", {}).get("mean", 0)
                  for a in ("disc", "sphere"))
    ax.axhspan(-175, nullmin, color="#eceff1", zorder=0)
    ax.annotate(f"kernel's numerical floor\n(nulls {nullmin:.0f} dB below the body)",
                (0.02, 0.02), xycoords="axes fraction", fontsize=7.2, va="bottom",
                color="#455a64", bbox=dict(fc="white", ec="#b0bec5", alpha=0.92, pad=2.0))
    ax.set_xlim(-1.8 * pr["beta"], 1.8 * pr["beta"]); ax.set_ylim(-175, 8)
    ax.set_xlabel("rotor-harmonic order $m$   (Doppler = $m \\cdot f_{rot}$)")
    ax.set_ylabel("line power relative to that arm's own DC [dB]")
    ax.set_title("matrice4e — what the blade structure adds\n"
                 "every arm referenced to its own 0-Doppler body return",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=7.3, loc="lower right", framealpha=0.95)

    # ── row 1 ─────────────────────────────────────────────────────────────── #
    ax = fig.add_subplot(gs[1, 0])
    for gen, c_, lw, z in (("G_0727", C_OLD, 1.6, 2), ("G_0803", "#000000", 2.6, 1),
                           ("G_0804", C_M4E, 1.2, 3)):
        k = f"{tag}|{gen}|matrice4e|mesh|spherical"
        if k not in tabs:
            continue
        T = tabs[k]; S = T.shape[1]
        c = np.fft.fft(T[0]) / S
        mo = np.fft.fftfreq(S, d=1.0 / S).astype(int); o = np.argsort(mo)
        ref = max(abs(c[0]) ** 2, 1e-300)
        ax.plot(mo[o], 10 * np.log10(np.maximum(np.abs(c[o]) ** 2 / ref, 1e-16)),
                lw=lw, color=c_, label=GEN_LABEL[gen], zorder=z)
    ax.set_xlim(-1.8 * pr["beta"], 1.8 * pr["beta"]); ax.set_ylim(-95, 5)
    ax.set_xlabel("rotor-harmonic order $m$")
    ax.set_ylabel("line power relative to DC [dB]")
    ax.set_title("matrice4e — three mesh generations\n"
                 "same kernel, same materials, same protocol: only the shape differs",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=7.0, loc="upper left")
    _cc = J["mesh_generations"]["pattern_change"]["matrice4e|G_0803->G_0804"]["ac_corr"]["mean"]
    ax.annotate(f"08-03 and 08-04 coincide\n(waveform correlation {_cc:.4f}):\n"
                f"the CAD fix left the\npropeller mesh untouched",
                (0.02, 0.03), xycoords="axes fraction", fontsize=7.0, va="bottom",
                color="#37474f", bbox=dict(fc="white", ec="#b0bec5", alpha=0.92, pad=2.2))

    ax = fig.add_subplot(gs[1, 1])
    pairs, vals, cols = [], [], []
    for key, c_ in (("matrice4e", C_M4E), ("mavic4pro", C_OLD)):
        for (ga, gb) in (("G_0727", "G_0803"), ("G_0803", "G_0804"), ("G_0727", "G_0804")):
            d = J["mesh_generations"]["pattern_change"].get(f"{key}|{ga}->{gb}")
            if d is None:
                continue
            pairs.append(f"{key}\n{ga[2:]}$\\to${gb[2:]}")
            vals.append(d["ac_corr"]["mean"]); cols.append(c_)
    x = np.arange(len(pairs))
    ax.bar(x, vals, 0.62, color=cols, zorder=3)
    for xi, v in zip(x, vals):
        ax.annotate(f"{v:.3f}", (xi, v + 0.02), ha="center", va="bottom", fontsize=7.8)
    ax.axhline(1.0, color="#455a64", ls="--", lw=1.0)
    ax.set_xticks(x); ax.set_xticklabels(pairs, fontsize=6.9)
    ax.set_ylim(0, 1.15); ax.set_ylabel("AC pattern correlation  $|\\langle a,b\\rangle|$")
    ax.set_title("Did the mesh change the micro-Doppler waveform?\n"
                 "1.0 = identical waveform   (grey = mavic4pro, negative control)",
                 fontsize=9.3, fontweight="bold")

    ax = fig.add_subplot(gs[1, 2])
    mc = J["mesh_generations"]["metric_change"]
    mk = ("flash_contrast_db", "dc_ac_db", "sigma_eq_mean_dbsm")
    mlab = ["flash\ncontrast", "body/blade\nratio", "$\\sigma_{eq}$\nlevel"]
    x = np.arange(len(mk)); w = 0.36
    for i, (pair, c_, lab) in enumerate((("matrice4e|G_0727->G_0803", C_OLD,
                                          "07-27 $\\to$ 08-03 (blade mesh changed)"),
                                         ("matrice4e|G_0803->G_0804", C_M4E,
                                          "08-03 $\\to$ 08-04 (CAD fix, blade untouched)"))):
        d = mc.get(pair, {})
        ys = [d.get(k, {}).get("delta", np.nan) for k in mk]
        sd = [d.get(k, {}).get("sd_b", np.nan) for k in mk]
        ax.bar(x + (i - 0.5) * w, ys, w, color=c_, label=lab, zorder=3)
        ax.errorbar(x + (i - 0.5) * w, [0] * len(mk), yerr=sd, fmt="none",
                    ecolor="#455a64", capsize=4, lw=1.1, zorder=4)
    ax.axhline(0, color="#455a64", lw=1.0)
    ax.set_xticks(x); ax.set_xticklabels(mlab, fontsize=8)
    _sd = [mc.get("matrice4e|G_0803->G_0804", {}).get(k, {}).get("sd_b", 0.0) for k in mk]
    ax.set_ylim(-1.25 * max(_sd), 1.55 * max(_sd))
    ax.set_ylabel("change in metric [dB]")
    ax.set_title("How big is the mesh effect vs the aspect spread?\n"
                 "bars = change · whiskers = sd across the 24 azimuths",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=7.1, loc="upper left")

    # ── row 2 : 지표 눈금 ─────────────────────────────────────────────────── #
    ax = fig.add_subplot(gs[2, 0])
    bars(ax, "flash_contrast_db")
    ax.set_ylabel("flash contrast [dB]   peak / median of $|AC|$")
    ax.set_title("Metric anchor 1 — flash contrast\nmean ± sd over 24 azimuths",
                 fontsize=9.3, fontweight="bold")

    ax = fig.add_subplot(gs[2, 1])
    bars(ax, "n_eff_orders")
    ax.set_ylabel("effective number of harmonic orders")
    ax.set_title("Metric anchor 2 — higher-order richness\n"
                 "$\\exp(-\\Sigma p_m \\ln p_m)$ over the AC lines",
                 fontsize=9.3, fontweight="bold")

    ax = fig.add_subplot(gs[2, 2])
    w = 0.38
    for i, key in enumerate(("mini2", "matrice4e")):
        ys = [per_az(key, a).get("in_band_ac_over_dc_db", {}).get("mean", np.nan) for a in ARMS]
        es = [per_az(key, a).get("in_band_ac_over_dc_db", {}).get("sd", np.nan) for a in ARMS]
        ax.bar(np.arange(len(ARMS)) + (i - 0.5) * w, ys, w, yerr=es, capsize=2.5,
               color=DCOL[key], label=key, zorder=3)
    ax.set_xticks(np.arange(len(ARMS))); ax.set_xticklabels(ALAB, fontsize=7.6)
    ax.set_ylabel("in-band blade return / body return [dB]")
    _nulls = [per_az(k2, a).get("in_band_ac_over_dc_db", {}).get("mean", np.nan)
              for k2 in ("mini2", "matrice4e") for a in ("sphere", "disc")]
    _real = [per_az(k2, a).get("in_band_ac_over_dc_db", {}).get("mean", np.nan)
             for k2 in ("mini2", "matrice4e") for a in ("slab", "mesh")]
    ax.set_title("Metric anchor 3 — above the numerical floor?\n"
                 f"nulls {np.nanmax(_nulls):.0f}…{np.nanmin(_nulls):.0f} dB · real blades "
                 f"{np.nanmax(_real):.0f}…{np.nanmin(_real):.0f} dB\n"
                 f"margin {np.nanmin(_real)-np.nanmax(_nulls):.0f} dB",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=8, loc="lower right")

    # ── row 3 : 검증 ───────────────────────────────────────────────────────── #
    ax = fig.add_subplot(gs[3, 0])
    xs, ys, es, cs, lb = [], [], [], [], []
    for key in ("mini2", "matrice4e"):
        for a, hatch in (("mesh", ""), ("slab", "//")):
            v = per_az(key, a).get("width_ratio", {})
            if not v:
                continue
            xs.append(len(xs)); ys.append(v["mean"]); es.append(v["sd"])
            cs.append(DCOL[key]); lb.append(f"{key}\n{a}")
    b = ax.bar(xs, ys, 0.6, yerr=es, capsize=3, color=cs, zorder=3)
    for i, bb in enumerate(b):
        if "slab" in lb[i]:
            bb.set_hatch("//"); bb.set_edgecolor("white")
    ax.axhline(1.0, color="#c62828", ls="--", lw=1.4)
    ax.annotate("kinematic prediction $f_{tip}$", (len(xs) - 0.45, 1.02), fontsize=7.8,
                ha="right", va="bottom", color="#c62828")
    q = {k: J["protocol_per_drone"][k]["order_quantum_rel"] for k in ("mini2", "matrice4e")}
    ax.set_xticks(xs); ax.set_xticklabels(lb, fontsize=7.4)
    ax.set_ylim(0, 1.35)
    ax.set_ylabel("measured $-20$ dB edge / $f_{tip}$")
    ax.set_title("Protocol check — width vs tip speed\n"
                 f"quantum = 1 order = {100*q['mini2']:.1f}% / "
                 f"{100*q['matrice4e']:.1f}% of $f_{{tip}}$   (hatched = slab)",
                 fontsize=9.3, fontweight="bold")

    ax = fig.add_subplot(gs[3, 1])
    lo, hi_ = FC_MAIN / 1e9, FC_PO_KNEE / 1e9
    x = np.arange(2); w = 0.36
    for i, key in enumerate(("mini2", "matrice4e")):
        for j, (a, hatch) in enumerate((("mesh", ""), ("slab", "//"))):
            lo_v = per_az(key, a).get("flash_contrast_db", {}).get("mean", np.nan)
            hb = J.get("hi_band", {}).get("metrics", {}).get(f"{key}|{a}", {})
            hi_v = hb.get("flash_contrast_db", {}).get("mean", np.nan)
            ax.plot([0, 1], [lo_v, hi_v], marker="o", ms=6, lw=1.8, color=DCOL[key],
                    ls="--" if a == "slab" else "-",
                    label=f"{key} · {a}")
    ax.set_xticks([0, 1]); ax.set_xticklabels([f"{lo:.2f} GHz\n(production band)",
                                               f"{hi_:.2f} GHz\n(PO validity knee)"],
                                              fontsize=8)
    ax.set_ylabel("flash contrast [dB]")
    _gaps = []
    for key in ("mini2", "matrice4e"):
        _gaps.append(per_az(key, "slab").get("flash_contrast_db", {}).get("mean", np.nan)
                     - per_az(key, "mesh").get("flash_contrast_db", {}).get("mean", np.nan))
        hbm = J.get("hi_band", {}).get("metrics", {})
        if f"{key}|slab" in hbm and f"{key}|mesh" in hbm:
            _gaps.append(hbm[f"{key}|slab"]["flash_contrast_db"]["mean"]
                         - hbm[f"{key}|mesh"]["flash_contrast_db"]["mean"])
    _sign = ("above" if min(_gaps) > 0 else "below" if max(_gaps) < 0 else "mixed vs")
    ax.set_title("Robustness — artefact of the weak band?\n"
                 f"slab stays {_sign} mesh at both bands\n"
                 f"(gap {min(_gaps):+.1f} to {max(_gaps):+.1f} dB)",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=7.2, loc="upper left")

    ax = fig.add_subplot(gs[3, 2])
    #  ⭐ «수치 흔들림» 과 «주장하려는 효과» 를 같은 축에 나란히 둔다. 흔들림보다 큰 효과만
    #     주장할 수 있고, 그 판정을 독자가 눈으로 하게 만든다.
    dens = J["point_density_control"]["deltas"]
    pv = J["paired_arm_difference"]["values"]
    groups = [("flash contrast\n[dB]", "flash_contrast_db"),
              ("higher-order richness\n[orders]", "n_eff_orders")]
    x = np.arange(len(groups)); w = 0.2
    for i, key in enumerate(("mini2", "matrice4e")):
        wob = [abs(dens.get(f"{key}|mesh", {}).get("delta", {}).get(mk_, np.nan))
               for _, mk_ in groups]
        eff = [abs(pv.get(f"{key}|slab - mesh", {}).get(mk_, {}).get("mean", np.nan))
               for _, mk_ in groups]
        ax.bar(x + (2 * i - 1.5) * w, wob, w, color="#b0bec5",
               label="4× finer point cloud (numerical wobble)" if i == 0 else None, zorder=3)
        ax.bar(x + (2 * i - 0.5) * w, eff, w, color=DCOL[key],
               label=f"{key}: |slab − CAD mesh| (paired)", zorder=3)
    for i, key in enumerate(("mini2", "matrice4e")):
        for j, (_, mk_) in enumerate(groups):
            fp = pv.get(f"{key}|slab - mesh", {}).get(mk_, {}).get("frac_positive", np.nan)
            v = abs(pv.get(f"{key}|slab - mesh", {}).get(mk_, {}).get("mean", np.nan))
            ax.annotate(f"{100*fp:.0f}%", (j + (2 * i - 0.5) * w, v), ha="center",
                        va="bottom", fontsize=7.0, color="#37474f")
    ax.set_xticks(x); ax.set_xticklabels([g_ for g_, _ in groups], fontsize=8)
    ax.set_ylabel("magnitude of the change")
    ax.set_title("Is the effect bigger than the numerical wobble?\n"
                 "grey = 4× refinement · coloured = slab vs CAD mesh\n"
                 "% on top = azimuths agreeing on the sign (24 total)",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=6.9, loc="upper left")

    fig.suptitle("report16 base — PO micro-Doppler rebuilt on the new drone meshes\n"
                 f"{FC_MAIN/1e9:.2f} GHz · monostatic at {RANGE_M:.0f} m · el {EL_DEG:.0f}° · "
                 f"{N_AZ} azimuths · spherical wavefront · full-revolution phase table · "
                 "no occlusion",
                 fontsize=13, fontweight="bold", y=0.982)
    pv = J["po_validity_warning"]
    fig.text(0.5, 0.014,
             f"⚠ The propeller blade needs {pv['blade_knee_ghz']:.2f} GHz to clear the PO "
             f"validity knee of {pv['knee_a_over_lambda']:.3f} λ — at "
             f"{pv['production_band_ghz']:.2f} GHz the very part that makes the micro-Doppler "
             f"is where this kernel is weakest (the body clears it at "
             f"{pv['body_knee_ghz']:.2f} GHz). No occlusion, no edge diffraction, scalar |Γ|, "
             "identical rpm on all four rotors.",
             ha="center", fontsize=8.4, color="#b71c1c")
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=150)
    plt.close(fig)
    return os.path.relpath(OUT_FIG, ROOT)


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
PLAN_MAIN = {
    "G_0727": [["matrice4e", ["mesh"]], ["mavic4pro", ["mesh"]]],
    "G_0803": [["matrice4e", ["mesh"]], ["mavic4pro", ["mesh"]]],
    "G_0804": [["matrice4e", ["mesh", "disc", "slab", "sphere",
                              "mesh_fine", "slab_fine", "disc_fine"]],
               ["mavic4pro", ["mesh"]],
               ["mini2", ["mesh", "disc", "slab", "sphere",
                          "mesh_fine", "slab_fine", "disc_fine"]]],
}
PLAN_HI = {"G_0804": [["matrice4e", ["mesh", "slab"]], ["mini2", ["mesh", "slab"]]]}


def main(skip_compute=False, with_hi=True):
    t_start = time.time()
    gen_dirs = _prepare_gen_dirs()
    J = dict(meta=dict(
        report="report16", producer="benchmark/report16_base.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        purpose_ko=("새 드론 메쉬로 PO 마이크로도플러를 재생성하고, 뒤 단계 전부가 쓸 "
                    "재생성 규약과 지표 정의를 못박는다."),
        headline_question_ko=("메쉬(형상 정밀도)를 바꾸면 마이크로도플러가 얼마나 바뀌는가. "
                              "안 바뀌면 «형상 정밀도는 여기서도 값어치가 없다» 가 결과다.")))

    # ── 규약 ───────────────────────────────────────────────────────────────
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from drones import DRONES
    proto_all = {}
    for k in ("mini2", "matrice4e", "mavic4pro"):
        s = DRONES[k]
        proto_all[k] = derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, FC_MAIN)
        proto_all[k]["hi_band"] = derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades,
                                                  FC_PO_KNEE)
    J["protocol"] = dict(
        fc_main_hz=FC_MAIN, fc_po_knee_hz=FC_PO_KNEE, el_deg=EL_DEG, range_m=RANGE_M,
        n_az=N_AZ, az_step_deg=360.0 / N_AZ, n_rev=N_REV, os_factor=OS_FACTOR,
        wavefront_headline="spherical", wavefront_control="plane",
        period_deg=360.0, monostatic=True,
        engine="pure PO on point clouds (no occlusion, no edge diffraction, scalar |Gamma|)",
        frame_div=6.0, blade_div=11.0, blade_n=26,
        decisions_ko={
            "주파수": ("3.5 GHz 가 헤드라인 — 저장소 전 리포트·5G n78 생산 대역이다. "
                     f"블레이드 폭이 PO 유효 무릎을 넘는 {FC_PO_KNEE/1e9:.2f} GHz 를 같이 돌려 "
                     "«커널이 약한 대역에서 잰 것» 이 결론을 좌우하는지 본다."),
            "거리": (f"{RANGE_M:.0f} m 모노스태틱 — 30×20×11 m 무향실 안에서 성립하는 스탠드오프. "
                   "matrice4e 는 이 거리가 원거리장 경계 바로 근처라 파면 곡률이 무시되지 않는다."),
            "파면": ("헤드라인은 **구면파**다. 평면파는 거리가 진폭 상수배일 뿐이라 근거리 여부를 "
                   "물을 수 없다. 평면파는 대조군으로 같이 돌린다."),
            "자세": (f"고각 {EL_DEG:.0f}° 고정, 방위 {N_AZ} 점 앙상블. 단일 자세 결론이 자세평균에서 "
                   "뒤집힌 전례가 있어(microdoppler_nearfield 문서) 앙상블을 기본으로 한다."),
            "위상 스텝": ("β = 4πR·cos(el)/λ 가 베셀 차수 절단이자 f_tip/f_rot 다. "
                       f"1회전을 S = 2^ceil(log2({OS_FACTOR:.0f}β)) 등분 → 나이퀴스트 대비 "
                       f"{OS_FACTOR/2:.0f}배 여유. 기체마다 다르게 **계산**한다."),
            "PRF": ("PRF = S·f_rot 로 두면 PRF ≥ 2·f_tip 이 자동 만족되고, 슬로타임 표본이 "
                   "위상 표 격자에 정확히 떨어져 **보간 오차가 0** 이다."),
            "주기": ("360°(1회전) 전체를 표로 잡는다. 360/블레이드수 근사는 홀수 하모닉을 "
                   "통째로 버린다(microdoppler_nearfield 문서의 측정 근거)."),
        })
    J["protocol_per_drone"] = proto_all

    # PO 유효성 경고
    knee = json.load(open(os.path.join(ROOT, "outputs", "report00_po_case.json")))["s4_limits"]
    J["po_validity_warning"] = dict(
        knee_a_over_lambda=knee["po_validity_knee_a_over_lambda"],
        knee_rule=knee["po_validity_knee_rule"],
        blade_knee_ghz=knee["feature_knee_frequencies"]["prop_blade_13p78mm_ghz"],
        body_knee_ghz=knee["feature_knee_frequencies"]["body_81p51mm_ghz"],
        production_band_ghz=FC_MAIN / 1e9,
        statement_ko=("마이크로도플러를 만드는 부품(프로펠러 블레이드, 폭 13.78 mm)은 "
                      f"{knee['feature_knee_frequencies']['prop_blade_13p78mm_ghz']} GHz 에서야 "
                      f"PO 유효 무릎(폭 ≥ {knee['po_validity_knee_a_over_lambda']:.3f}λ)을 넘는다. "
                      f"생산 대역 {FC_MAIN/1e9:.1f} GHz 에서는 **커널이 가장 약한 부품이 곧 신호원**이다. "
                      "이 라운드의 모든 절대값은 그 조건 아래에서 읽어야 한다."))

    # ── 메쉬 지문 ──────────────────────────────────────────────────────────
    fp = _mesh_fingerprints(gen_dirs)
    J["mesh_generations"] = dict(commits={g: (c or "worktree") for g, c in GEN_COMMITS.items()},
                                 labels=GEN_LABEL, fingerprints=fp)
    changed = {}
    for key in ("matrice4e", "mavic4pro", "mini2"):
        rows = {}
        for (ga, gb) in (("G_0727", "G_0803"), ("G_0803", "G_0804")):
            a, b = fp[ga].get(key), fp[gb].get(key)
            if a is None or b is None:
                rows[f"{ga}->{gb}"] = "absent in one generation"
                continue
            rows[f"{ga}->{gb}"] = dict(
                frame_changed=a["frame_sha"] != b["frame_sha"],
                prop_changed=a["prop_sha"] != b["prop_sha"],
                rotor_center_max_shift_mm=float(1000 * np.max(np.abs(
                    np.asarray(a["rotor_centers"]) - np.asarray(b["rotor_centers"]))))
                if len(a["rotor_centers"]) == len(b["rotor_centers"]) else None)
        changed[key] = rows
    J["mesh_generations"]["what_changed"] = changed
    J["mesh_generations"]["what_changed_note_ko"] = (
        "⭐ 2026-08-04 CAD 정정은 matrice4e 의 **프레임만** 바꿨다 — 프로펠러 메쉬는 해시가 같다. "
        "즉 그 정정이 마이크로도플러에 미치는 영향은 «동체 DC» 와 «로터 허브 위치» 를 통해서만 "
        "온다. mini2 는 그날 새로 추가된 기체라 옛 판이 존재하지 않는다.")

    # ── 계산 ───────────────────────────────────────────────────────────────
    if not skip_compute:
        J["kernel_gate"] = _verify_gate()
        print(f"▶ 커널 검증 게이트: {J['kernel_gate']['verdict']}", flush=True)
        run_workers(gen_dirs, PLAN_MAIN, FC_MAIN, "main")
        if with_hi:
            run_workers({k: v for k, v in gen_dirs.items() if k in PLAN_HI},
                        PLAN_HI, FC_PO_KNEE, "hi")
    else:
        prev = json.load(open(OUT_JSON)) if os.path.exists(OUT_JSON) else {}
        J["kernel_gate"] = prev.get("kernel_gate", {})

    tabs, metas = load_tables("main")
    tabs_hi, metas_hi = load_tables("hi")
    J["gpu_used"] = {g: m.get("gpu") for g, m in metas.items()}

    # ── 팔별 지표 ──────────────────────────────────────────────────────────
    J["arms"] = {}
    ARMS_FULL = ["mesh", "disc", "slab", "sphere", "mesh_fine", "slab_fine", "disc_fine"]
    for key, arms in (("mini2", ARMS_FULL), ("matrice4e", ARMS_FULL),
                      ("mavic4pro", ["mesh"])):
        J["arms"][key] = {}
        for arm in arms:
            blk = {}
            for wf in ("spherical", "plane"):
                mb = metrics_block(tabs, metas, "main", "G_0804", key, arm, wf)
                if mb:
                    blk[wf] = mb
            meta = metas["G_0804"]["drones"][key]["arms"].get(arm, {})
            blk["geometry"] = meta.get("meta", {})
            blk["n_frame_pts"] = meta.get("n_frame_pts")
            blk["n_blade_pts"] = meta.get("n_blade_pts")
            if arm == "mesh":
                blk["legacy_metrics_on_same_table"] = legacy_on_new(
                    tabs, metas, "main", "G_0804", key, arm, "spherical")
            if blk:
                J["arms"][key][arm] = blk
        J["arms"][key]["farfield"] = dict(
            extent_m=metas["G_0804"]["drones"][key].get("extent_m"),
            farfield_2D2_over_lam_m=metas["G_0804"]["drones"][key].get("farfield_2D2_over_lam_m"),
            range_over_farfield=metas["G_0804"]["drones"][key].get("range_over_farfield"))

    # ── 메쉬 세대 비교 ─────────────────────────────────────────────────────
    pat, dmet = {}, {}
    for key in ("matrice4e", "mavic4pro"):
        gens = [g for g in ("G_0727", "G_0803", "G_0804")
                if f"main|{g}|{key}|mesh|spherical" in tabs]
        for i in range(len(gens)):
            for j in range(i + 1, len(gens)):
                ga, gb = gens[i], gens[j]
                Ta = tabs[f"main|{ga}|{key}|mesh|spherical"]
                Tb = tabs[f"main|{gb}|{key}|mesh|spherical"]
                cc = [ac_corr(Ta[i2], Tb[i2]) for i2 in range(Ta.shape[0])]
                pat[f"{key}|{ga}->{gb}"] = dict(ac_corr=summarize(cc))
                ma = metrics_block(tabs, metas, "main", ga, key, "mesh", "spherical")
                mb = metrics_block(tabs, metas, "main", gb, key, "mesh", "spherical")
                dmet[f"{key}|{ga}->{gb}"] = {
                    kk: dict(a=ma["per_az"][kk]["mean"], b=mb["per_az"][kk]["mean"],
                             delta=mb["per_az"][kk]["mean"] - ma["per_az"][kk]["mean"],
                             sd_a=ma["per_az"][kk]["sd"], sd_b=mb["per_az"][kk]["sd"])
                    for kk in ("flash_contrast_db", "n_eff_orders", "order_p90",
                               "blade_comb_frac", "width_ratio", "dc_ac_db",
                               "sigma_eq_mean_dbsm")}
    J["mesh_generations"]["pattern_change"] = pat
    J["mesh_generations"]["metric_change"] = dmet
    J["mesh_generations"]["per_generation_metrics"] = {
        f"{key}|{g}": metrics_block(tabs, metas, "main", g, key, "mesh", "spherical")
        for key in ("matrice4e", "mavic4pro")
        for g in ("G_0727", "G_0803", "G_0804")
        if f"main|{g}|{key}|mesh|spherical" in tabs}

    # ── ⭐ 짝지은 비교 (같은 방위끼리) — 평균끼리 빼는 것보다 훨씬 예리하다 ──────
    #    자세에 따른 산포가 크기 때문에, «평균 차이 vs 산포» 로 보면 아무것도 유의하지 않아
    #    보인다. 옳은 검정은 **같은 방위에서 두 팔을 빼는 것**이다(짝지은 차이).
    paired = {}
    for key in ("mini2", "matrice4e"):
        for (a, b) in (("mesh", "slab"), ("mesh", "disc"), ("mesh", "mesh_fine")):
            ka = f"main|G_0804|{key}|{a}|spherical"; kb = f"main|G_0804|{key}|{b}|spherical"
            if ka not in tabs or kb not in tabs:
                continue
            pr = metas["G_0804"]["drones"][key]["protocol"]
            nb = metas["G_0804"]["drones"][key]["spec"]["prop_blades"]
            ma = [md_metrics16(tabs[ka][i], pr, nb) for i in range(tabs[ka].shape[0])]
            mb = [md_metrics16(tabs[kb][i], pr, nb) for i in range(tabs[kb].shape[0])]
            row = {}
            for kk in ("flash_contrast_db", "n_eff_orders", "dc_ac_db",
                       "in_band_ac_over_dc_db", "width_ratio", "sigma_eq_mean_dbsm"):
                d = np.array([y[kk] - x[kk] for x, y in zip(ma, mb)], float)
                d = d[np.isfinite(d)]
                sd = float(d.std(ddof=1)) if d.size > 1 else 0.0
                row[kk] = dict(mean=float(d.mean()), sd=sd,
                               sem=float(sd / max(math.sqrt(d.size), 1.0)),
                               frac_positive=float(np.mean(d > 0)), n=int(d.size),
                               min=float(d.min()), max=float(d.max()))
            paired[f"{key}|{b} - {a}"] = row
    J["paired_arm_difference"] = dict(
        values=paired,
        what_ko=("같은 방위에서 두 팔의 지표를 뺀 값(팔 B − 팔 A). frac_positive 는 24 방위 중 "
                 "B 가 더 큰 비율이다 — 1.0 이면 모든 자세에서 한 방향이라는 뜻이고, 이것이 "
                 "평균±산포보다 훨씬 강한 증거다."),
        why_paired_ko=("자세에 따른 산포(sd 2~3 dB)가 팔 사이 차이와 비슷해 보이지만, 그 산포는 "
                       "두 팔에 **공통**이다(같은 동체·같은 시선). 짝지어 빼면 공통분이 사라진다."))

    # ── 점밀도 반론 차단 ───────────────────────────────────────────────────
    dens = {}
    for key in ("mini2", "matrice4e"):
        for arm in ("mesh", "slab", "disc"):
            a = J["arms"].get(key, {}).get(arm, {}).get("spherical", {}).get("per_az")
            b = J["arms"].get(key, {}).get(arm + "_fine", {}).get("spherical", {}).get("per_az")
            if not a or not b:
                continue
            dens[f"{key}|{arm}"] = dict(
                pts_coarse=J["arms"][key][arm]["n_blade_pts"],
                pts_fine=J["arms"][key][arm + "_fine"]["n_blade_pts"],
                delta={kk: b[kk]["mean"] - a[kk]["mean"]
                       for kk in ("flash_contrast_db", "n_eff_orders", "width_ratio",
                                  "dc_ac_db", "sigma_eq_mean_dbsm", "in_band_ac_over_dc_db")})
    J["point_density_control"] = dict(
        refine_x4="frame lambda/6 -> lambda/24,  rotating part lambda/11 -> lambda/44",
        deltas=dens,
        question_ko=("«프리미티브(평판·원판)가 CAD 블레이드보다 성기게 깔려서 달라 보이는 것 "
                     "아니냐» 는 반론을 차단한다. 4배 촘촘히 깔아도 지표가 안 움직이면 "
                     "밀도 차이는 원인이 아니다."))

    # ── 파면 대조 (구면 vs 평면) ───────────────────────────────────────────
    wfc = {}
    for key in ("mini2", "matrice4e"):
        ka = f"main|G_0804|{key}|mesh|spherical"; kb = f"main|G_0804|{key}|mesh|plane"
        if ka in tabs and kb in tabs:
            Ta, Tb = tabs[ka], tabs[kb]
            wfc[key] = dict(ac_corr=summarize([ac_corr(Ta[i], Tb[i]) for i in range(Ta.shape[0])]),
                            level_delta_db=summarize([
                                10 * np.log10(np.mean(np.abs(Tb[i]) ** 2) /
                                              np.mean(np.abs(Ta[i]) ** 2))
                                for i in range(Ta.shape[0])]))
    J["wavefront_control"] = dict(
        spherical_vs_plane=wfc,
        note_ko=("구면파(헤드라인)와 평면파(무한거리 등가)의 차이. 상관이 1 에 가까우면 "
                 f"{RANGE_M:.0f} m 는 이 표적에게 사실상 원거리장이라는 뜻이다."))

    # ── 고주파(PO 유효 무릎) 대조 ─────────────────────────────────────────
    if tabs_hi:
        hi = {}
        for key in ("mini2", "matrice4e"):
            for arm in ("mesh", "slab"):
                mb = metrics_block(tabs_hi, metas_hi, "hi", "G_0804", key, arm, "spherical")
                if mb:
                    hi[f"{key}|{arm}"] = mb["per_az"]
        J["hi_band"] = dict(fc_hz=FC_PO_KNEE, metrics=hi,
                            note_ko=("블레이드가 PO 유효 무릎을 넘는 주파수에서 같은 지표를 다시 잰다. "
                                     "3.5 GHz 결론이 «커널이 약한 대역» 의 산물인지 확인하는 자리다."))

    # ── 아카이브·수렴 ──────────────────────────────────────────────────────
    J["archive_2026_07_29"] = archive_0729()
    #  같은 «대역 안» 잣대를 새 판에도 대서 나란히 놓는다
    side = {}
    for key in ("mini2", "matrice4e", "mavic4pro"):
        k = f"main|G_0804|{key}|mesh|spherical"
        if k not in tabs:
            continue
        pr = metas["G_0804"]["drones"][key]["protocol"]
        rows = [in_band_hz(np.tile(tabs[k][i], pr["n_rev"]), pr["prf_hz"], pr["f_tip_hz"])
                for i in range(tabs[k].shape[0])]
        side[key] = dict(in_band_ac_frac=summarize([r["in_band_ac_frac"] for r in rows]),
                         dc_ac_db=summarize([r["dc_ac_db"] for r in rows]))
    J["archive_2026_07_29"]["same_gauge_on_new_run"] = dict(
        engine="pure PO (this file), spherical wavefront, R=10 m, new mesh",
        values=side,
        note_ko=("같은 in_band 잣대를 새 판에 댄 값. 07-29 SBR 판의 in_band 값과 나란히 읽을 것. "
                 "⚠ 엔진(PO vs SBR)·메쉬·규약이 모두 달라 통제된 A/B 가 아니다 — "
                 "통제된 A/B 는 mesh_generations 블록이다."))
    if not skip_compute:
        J["convergence"] = convergence_check(gen_dirs)
    else:
        prev = json.load(open(OUT_JSON)) if os.path.exists(OUT_JSON) else {}
        J["convergence"] = prev.get("convergence", {})

    # ── 지표 정의를 JSON 안에 못박는다 ─────────────────────────────────────
    J["metric_definitions"] = dict(
        implementation="benchmark/report16_base.py :: md_metrics16(table, protocol, prop_blades)",
        input="one full-revolution complex phase table E(phi), n_phase samples, endpoint excluded",
        flash_contrast_db=dict(
            formula="20*log10( max_phi |E-mean(E)| / median_phi |E-mean(E)| )",
            means_ko="플래시 봉우리가 바닥보다 몇 dB 위인가",
            sensitive_to_ko="블레이드 정합(플래시), 위상격자 촘촘함, 점구름 밀도, 파면",
            insensitive_to_ko="절대 RCS 크기, 동체 DC 세기, rpm, PRF, 슬로타임 길이",
            null_value_db=0.0,
            null_meaning_ko="회전대칭체의 이론값. 실측 바닥은 sphere/disc 팔이 준다."),
        n_eff_orders=dict(
            formula="exp(-sum p_m ln p_m) over AC lines m!=0, p normalized",
            means_ko="실질적으로 몇 개의 하모닉 차수가 살아 있나 (고차 성분 풍부도)",
            sensitive_to_ko="블레이드 형상 복잡도, beta(=반경/λ), 점구름 밀도",
            insensitive_to_ko="절대 크기, rpm, PRF, 동체 DC",
            caveat_ko="⚠ AC 가 수치바닥이면 잡음이 고르게 퍼져 값이 커진다 — ac_over_floor_db 와 함께 읽을 것"),
        blade_comb_frac=dict(
            formula="AC power fraction on orders that are multiples of prop_blades",
            means_ko="진짜 블레이드 플래시 빗(2,4,6,…)에 실린 몫 — 비대칭·불균형 선과 가른다",
            sensitive_to_ko="블레이드 수, 로터 간 위상, 형상 대칭성",
            insensitive_to_ko="절대 크기, rpm"),
        width_ratio=dict(
            formula=f"(largest order with line power >= peak-{EDGE_DROP_DB:.0f}dB) * f_rot / f_tip",
            means_ko="스펙트럼 폭이 팁속도 예측(f_tip)과 맞는가. 운동학이 맞으면 ≈1",
            sensitive_to_ko="팁반경·λ·cos(el), 문턱값(10/20/30 dB 모두 저장)",
            insensitive_to_ko="절대 크기, 동체 DC, 표본화 S",
            quantum_ko="⚠ 최소 눈금 = 1차수 = f_rot = f_tip/beta. 그보다 작은 폭 변화는 잴 수 없다"),
        dc_ac_db=dict(
            formula="20*log10( |c_0| / sqrt(sum_{m!=0} |c_m|^2) )",
            means_ko="동체(0-도플러) 대 블레이드(AC) 세기비. 클수록 블레이드가 묻힌다",
            sensitive_to_ko="고각·방위, 재질 가중, **가림 유무**",
            insensitive_to_ko="절대 크기, PRF, rpm",
            caveat_ko="⚠⚠ 이 커널에 가림이 없어 동체가 과대 계상된다 — 네 지표 중 가장 오염됐다. "
                      "절대값 인용 금지, 팔 사이 차이만 쓸 것"),
        in_band_ac_frac=dict(
            formula="AC power fraction at orders |m| <= ceil(1.5*beta)",
            means_ko="AC 전력 중 운동학적으로 가능한 대역(팁속도 이하)에 있는 몫",
            role_ko=("⭐ **읽을 자격 판정기**다. 0.5 미만이면 AC 의 절반 이상이 팁보다 빠른 자리에 "
                     "있다는 뜻이고, 그것은 물리가 아니라 점구름 이산화 잔차다 → 폭·풍부도 지표를 "
                     "해석하면 안 된다. 회전대칭 널(원판·구)이 정확히 이 상태다."),
            sensitive_to_ko="점구름 격자의 각도 분해능, 표적의 회전대칭성",
            insensitive_to_ko="절대 크기, rpm, PRF"))

    # ── 결론 문장 (숫자는 전부 위에서 계산된 값을 참조) ────────────────────
    J["findings"] = _findings(J)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    np.savez_compressed(OUT_NPZ, **{k.replace("|", "__"): v for k, v in tabs.items()},
                        **{("hi__" + k.replace("|", "__")): v for k, v in tabs_hi.items()})
    J["figures"] = dict(base=make_figure(J, tabs, metas, tabs_hi, metas_hi, "main"))
    J["meta"]["seconds"] = float(time.time() - t_start)
    J["meta"]["tables_npz"] = os.path.relpath(OUT_NPZ, ROOT)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✅ {os.path.relpath(OUT_JSON, ROOT)}  ·  {J['figures']['base']}  "
          f"[{J['meta']['seconds']:.0f}s]")
    return J


def _findings(J):
    """숫자를 손으로 적지 않는다 — 위에서 계산된 값만 골라 문장을 만든다."""
    F = {}
    mc = J["mesh_generations"]["metric_change"]
    pc = J["mesh_generations"]["pattern_change"]

    def g(d, *ks):
        for k in ks:
            d = d.get(k, {}) if isinstance(d, dict) else {}
        return d

    key_pairs = [k for k in pc if k.startswith("matrice4e")]
    F["q1_did_the_mesh_change_the_micro_doppler"] = dict(
        question_ko="메쉬(형상)를 바꾸면 마이크로도플러가 바뀌는가",
        matrice4e_pattern_corr={k: pc[k]["ac_corr"] for k in key_pairs},
        matrice4e_metric_delta={k: mc[k] for k in key_pairs if k in mc},
        control_mavic4pro={k: pc[k]["ac_corr"] for k in pc if k.startswith("mavic4pro")},
        control_note_ko=("mavic4pro 는 2026-08-04 정정이 건드리지 않은 기체다 — "
                         "G_0803→G_0804 상관이 정확히 1 이면 파이프라인 자체는 흔들리지 않는다는 뜻이고, "
                         "matrice4e 에서 보이는 변화는 전부 메쉬 때문이다."),
        two_kinds_of_sensitivity_ko=(
            "⭐ 이 블록의 두 숫자는 **다른 질문**에 답한다. ac_corr 는 «파형이 같은가»(정합필터·템플릿 "
            "분류가 보는 것), metric_change 는 «요약 지표가 같은가»(플래시 세기·대역폭 같은 특징이 "
            "보는 것)다. 둘이 크게 어긋날 수 있다 — 파형은 알아볼 수 없이 바뀌었는데 요약 지표는 "
            "자세 산포 안에 머무는 경우가 그렇다. 어느 쪽을 쓸 계획인지에 따라 «메쉬 정밀도가 "
            "필요한가» 의 답이 갈린다."),
        why_the_cad_fix_barely_moved_it_ko=(
            "2026-08-04 정정이 matrice4e 에서 프레임만 바꾸고 프로펠러 메쉬는 그대로 두었기 때문이다. "
            "게다가 네 로터의 허브 z 가 **같은 양만큼** 움직였다 — 그러면 로터 합에 공통 위상이 곱해질 "
            "뿐이라 AC 파형의 모양이 원리적으로 보존된다(상관이 정확히 1.0000 인 이유). 바뀌는 것은 "
            "동체가 만드는 0-도플러 항뿐이고, 그래서 dc_ac_db·σ 만 움직인다."))

    anchors = {}
    for key in ("mini2", "matrice4e"):
        row = {}
        for arm in ("sphere", "disc", "slab", "mesh"):
            b = g(J["arms"], key, arm, "spherical", "per_az")
            if not b:
                continue
            row[arm] = {kk: b[kk]["mean"] for kk in
                        ("flash_contrast_db", "n_eff_orders", "order_p90", "blade_comb_frac",
                         "width_ratio", "dc_ac_db", "in_band_ac_frac", "in_band_ac_over_dc_db")}
            row[arm]["metrics_interpretable_frac"] = \
                J["arms"][key][arm]["spherical"].get("interpretable_frac")
        anchors[key] = row
    F["q2_metric_anchors"] = dict(
        question_ko="지표의 0점과 눈금 — 구조가 없는 표적은 얼마를 내는가",
        values=anchors,
        reading_ko=("sphere = 계산기 자체의 수치 바닥(물리적 변조 0). "
                    "disc = 돌지만 구조가 없는 표적(물리적 변조 0). "
                    "slab = 기하 프리미티브 블레이드(평판 2장). mesh = 진짜 CAD 블레이드. "
                    "⭐ mesh 와 slab 의 간격이 곧 «형상 정밀도가 마이크로도플러에서 갖는 값어치» 다. "
                    "⚠ 널 팔(sphere·disc)은 in_band_ac_frac 이 낮아 폭·풍부도 지표를 해석하면 안 된다 "
                    "— 그 값들은 이산화 잔차다. 널 팔에서 읽을 수 있는 것은 dc_ac_db 와 "
                    "in_band_ac_over_dc_db 뿐이고, 그 둘이 곧 «바닥» 이다."))

    # ⭐ 이 라운드의 헤드라인 숫자 — 손으로 적지 않고 위 값에서 뽑는다
    gap = {}
    for key in ("mini2", "matrice4e"):
        row = {}
        for kk in ("flash_contrast_db", "n_eff_orders", "dc_ac_db", "in_band_ac_over_dc_db",
                   "width_ratio"):
            a = g(J["arms"], key, "mesh", "spherical", "per_az").get(kk, {})
            b = g(J["arms"], key, "slab", "spherical", "per_az").get(kk, {})
            if not a or not b:
                continue
            row[kk] = dict(cad_mesh=a["mean"], primitive_slab=b["mean"],
                           slab_minus_mesh=b["mean"] - a["mean"],
                           aspect_sd_mesh=a["sd"])
        hb_m = J.get("hi_band", {}).get("metrics", {}).get(f"{key}|mesh", {})
        hb_s = J.get("hi_band", {}).get("metrics", {}).get(f"{key}|slab", {})
        if hb_m and hb_s:
            row["hi_band_check"] = {
                kk: dict(cad_mesh=hb_m[kk]["mean"], primitive_slab=hb_s[kk]["mean"],
                         slab_minus_mesh=hb_s[kk]["mean"] - hb_m[kk]["mean"])
                for kk in ("flash_contrast_db", "n_eff_orders", "dc_ac_db")}
        row["paired_slab_minus_mesh"] = J.get("paired_arm_difference", {}) \
                                         .get("values", {}).get(f"{key}|slab - mesh")
        gap[key] = row
    F["q4_does_shape_detail_add_micro_doppler"] = dict(
        question_ko=("⭐⭐ 형상 정밀도가 마이크로도플러를 «더 풍부하게» 만드는가 — "
                     "진짜 CAD 블레이드 vs 같은 스팬·같은 두께·같은 부피의 평판 프리미티브"),
        values=gap,
        primitive_construction_ko=(
            "평판은 실제 프롭에서 **스팬과 코드를 그대로 가져오고**(도플러 폭과 정반사 면적을 "
            "정하는 두 양) 두께만 부피가 같아지도록 풀어 만든다. 비틀림·캠버·테이퍼·허브 형상만 "
            "사라진 물체다 — 즉 «CAD 정밀도» 라고 부르는 것의 알맹이만 제거한 대조군이다."),
        how_to_read_ko=(
            "⛔ 부호를 미리 정하지 말 것. 지표마다 방향이 다르게 나올 수 있고 실제로 다르게 나온다. "
            "paired_slab_minus_mesh 의 frac_positive 를 먼저 볼 것 — 24 방위 중 몇 번이 같은 방향인가. "
            "0.5 근처면 «차이 없음» 이고(자세를 바꾸면 부호가 뒤집힌다), 1.00 이면 «어느 자세에서 봐도 "
            "한 방향» 이다. 평균±산포만 보면 자세 산포가 공통분이라 차이가 묻힌다. "
            "hi_band_check 도 함께 볼 것 — 3.5 GHz 에서는 블레이드가 파장보다 작아 형상이 거의 "
            "안 보이지만, 15.86 GHz 에서는 형상이 분해된다. 두 대역에서 방향이 같아야 형상 효과다."),
        mechanism_ko=(
            "물리적으로 예상되는 방향은 이렇다 — 평판은 스팬 전체가 한 순간에 시선과 나란히 서서 "
            "통짜 정반사를 낸다. 진짜 블레이드는 비틀림·캠버·테이퍼 때문에 스팬이 동시에 정렬되지 "
            "못해 그 봉우리가 번진다. 그래서 «형상 정밀도» 는 마이크로도플러를 더해 주기보다 "
            "깎는 쪽으로 작용할 수 있다. 이 예상이 맞는지는 위 숫자가 답한다."))

    F["q3_kernel_validity"] = dict(
        question_ko="이 결과를 어디까지 믿을 수 있나",
        kernel_gate=J.get("kernel_gate", {}).get("verdict"),
        convergence=J.get("convergence", {}),
        po_validity=J["po_validity_warning"],
        wavefront=J.get("wavefront_control", {}).get("spherical_vs_plane", {}))
    return F


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compute", action="store_true", help="이미 만든 표로 JSON/그림만 다시")
    ap.add_argument("--no-hi", action="store_true", help="15.86 GHz 대조 생략")
    a = ap.parse_args()
    main(skip_compute=a.skip_compute, with_hi=not a.no_hi)
