# -*- coding: utf-8 -*-
"""
monostatic_scene.py — 자유공간 **모노스태틱(공배치 TX=RX)** 기하·시간축·링크 (순수함수)
==============================================================================================

`freespace_scene.py`(패시브 바이스태틱 FS-1)의 **짝**이다. 같은 질문을 같은 규약으로 묻되
조명원과 수신기가 **한 자리**에 있는 경우를 다룬다 — LaSen 류 5G-NR 모노스태틱 ISAC 센서,
즉 "기지국이 자기 신호의 에코를 스스로 듣는" 형태다.

■ 이 모듈의 존재 이유(사용자 질문)
    "검증에 바이스태틱뿐 아니라 모노스태틱(LaSen 같은 기법)도 고려됐나?"
  → 도플러 축은 이미 덮여 있었다(모노 = 바이스태틱 β=0 절편, ⟨outputs/mono_vs_passive.json §1⟩).
    **검출 계층만 바이스태틱 전용**이었다. 이 파일이 그 구멍을 메운다.

■ ⭐ 재구현이 아니라 **호출**이다 — 모노스태틱은 저장소 함수의 퇴화입력이다
  `mono_params(tgt, v, fc)` 는 `freespace_scene.fs_params(S, S, tgt, v, fc)` 를 **그대로 부른다**
  (TX 위치와 RX 위치에 같은 점 S 를 넣는다). 그러면 저장소 식 자체가 모노스태틱 값을 낸다:

      u1 = u2 = u = (S − P)/R      →  β = ∠(u1,u2) = 0
      Rb = R1 + R2 − L = 2R − 0    →  RD 맵 가로축이 **왕복거리**로 붕괴
      f_d = v·(u1+u2)/λ = 2 v·u/λ  →  교과서 모노스태틱 도플러
      κ  = R1R2 = R²               →  `snr ∝ σ/κ²` 가 곧 **1/R⁴**
      el = look_el_deg(u,u)        →  이등분선이 시선 그 자체

  링크도 같다: `freespace_link.echo_power_w(λ,σ,R1=R,R2=R)` 는
  `EIRP·G_rx·λ²σ / ((4π)³R⁴)` 이고 이것이 **모노스태틱 레이더 방정식 그 자체**다.
  그래서 이 모듈에는 새 물리식이 없다 — 있는 것은 (a) 퇴화입력을 부르는 얇은 래퍼,
  (b) 그 퇴화가 정말 성립하는지 깨뜨리려는 회귀잠금(`selfcheck_vs_freespace`),
  (c) 바이스태틱에는 없고 모노스태틱에만 있는 항(자기간섭)뿐이다.

■ ⚠ 두 효과를 **절대 섞지 않는다**(이 파일에서 가장 틀리기 쉬운 곳)
  ① **링크 계층은 바뀐다.** 1/R⁴ ↔ 1/(R1²R2²), 그리고 기준채널이 없어진다
     (패시브의 DPI 잔류 → 모노의 자기간섭 SI). 이건 **거리**를 바꾼다.
  ② **도플러 모호 바닥은 안 바뀐다.** v_max = λ·PRF/4 는 모노 = 바이스태틱 β=0 이라
     기하가 아니라 **반복률**이 정한다. 이건 거리와 무관하다.
  두 개를 한 문장에 섞어 "모노스태틱이라 더 좋다/나쁘다"고 쓰면 그 문장은 틀린다.
  단, ②의 *비율*(블라인드·앨리어싱 헤딩 비율)은 기하에 의존한다 — 투영인자
  |u1+u2| = 2cos(β/2) 가 모노에서 정확히 2(최대)이기 때문이다. 법칙은 같고 비율은 다르다.

■ 규약 승계(새로 만들지 않는다 — `freespace_scene` 것을 그대로 쓴다)
  · 가드 두 규약 : 선언 2.5빈(`GUARD_DOPPLER_BINS`) / 하드 1.5빈(`DOPPLER_GUARD_HARD_BINS`)
                   — 저장소가 이미 둘이 다르다고 기록해 둔 그 규약이다(감사 B1).
  · 접힘        : `folded_doppler` 로 판정(F8). 블라인드는 **접힌** 도플러로만 잰다.
  · 나이퀴스트  : `nyquist_gate`(|f_d| < PRF/2), 퇴화입력 규약(inf→True, ≤0→False)까지 승계.
  · 빈폭        : `doppler_bin_hz(T, prf, M)` 실현값 우선(감사 B2).
  · 반복률      : `prf_hz(std, mode)` — **같은 PRF 로 두 기하를 비교해야** ②가 검증된다.
                   모노스태틱이 PRF 를 고를 수 있다는 자유도는 별개 축이고 그 크기는
                   ⟨outputs/mono_vs_passive.json §2 D1⟩ 에 이미 정량화돼 있다(13단 사다리, 천장 500 Hz).
  · 원거리장    : `farfield_gate(min(R1,R2), …)` = `farfield_gate(R, …)`.
  · 드론 순서   : `freespace_scene.DRONE_ORDER`.

■ 배치(선언값)
    MONO_POS = (0, 0, 25)   공배치 TX/RX — 높이는 `freespace_scene.FS_TX` 의 마스트 25 m 를
                            **그대로 물려받는다**(새 선언값을 만들지 않기 위해). 모노스태틱
                            ISAC 센서 = 조명원 자리에 앉은 기지국이라는 그림과도 맞는다.
    P(d,φ) = MONO_POS_xy + d·(cosφ, sinφ) , z = alt
    → d 는 **센서 기준 수평거리**다. 바이스태틱 d(중점 기준)와 같은 축이며, φ=90°·d≫L 이면
      두 기하의 사거리가 사실상 같아진다(그래서 사과-대-사과 비교가 성립한다).

■ ⭐ σ 는 바꿀 필요가 없다 — 오히려 여기서 **더 정확하다**
  `outputs/report13_sigma_grid.json` 은 `rcs_sbr.rcs_sbr_batch`(1-bounce SBR, penetrate=True)
  로 만든 **모노스태틱** σ 격자다. 바이스태틱 리포트는 그 모노 σ 를 이등분선 방향에서 조회하는
  **바이스태틱 등가 근사**로 쓴다(β 가 커질수록 근사가 나빠져 β≤90° 게이트가 붙어 있다).
  모노스태틱 시나리오에서는 이등분선 = 시선이므로 그 근사가 **불필요**하다. 즉 이 시나리오는
  저장소에서 가장 잘 검증된 RCS 층 위에 그대로 선다 — 이 사실을 리포트에 적을 것.

■ 그림 텍스트 없음(순수 계산 모듈). 주석·docstring 한국어(하우스 규약).
작성: 2026-07 / 사용자 질문 "모노스태틱까지 고려됐나" 에 대한 검출계층 응답.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", "benchmark"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import freespace_scene as fss           # noqa: E402  (기하·시간축 규약의 단일 진리원)
import freespace_link as fsl            # noqa: E402  (링크 닫힌형 — 재구현 금지)
from link_budget import LinkBudget, lin2db   # noqa: E402

C0 = fss.C0

__all__ = [
    "MONO_H", "MONO_POS", "MONO_PRF_CEILING_HZ",
    "mono_pos", "mono_target_pos", "mono_params", "mono_params_closed",
    "mono_R_of_d", "mono_kappa_of_d",
    "mono_fd_of_heading", "mono_blind_sector", "mono_blind_fractions",
    "v_max_ms", "bistatic_relief",
    "mono_beta_gate", "mono_farfield_gate",
    "mono_echo_power_w", "mono_snr_rd_db",
    "mono_required_isolation_db", "si_residual_psd", "isolation_gap_vs_passive_db",
    "usable_heading_fraction", "selfcheck_vs_freespace",
]

# --------------------------------------------------------------------------- #
#  배치 상수 — 새 선언값을 만들지 않는다(전부 freespace_scene 승계)
# --------------------------------------------------------------------------- #
MONO_H = float(fss.FS_TX[2])                  # 25 m — 조명원 마스트 높이를 그대로 물려받음
MONO_POS = (0.0, 0.0, MONO_H)                 # 공배치 TX=RX

#: 3GPP sub-6 CSI-RS 최대 반복률 [Hz] — 모노스태틱의 PRF '자유도'가 닫히는 천장.
#: 출처: LaSen (Proc. ACM/IEEE SenSys '26, 게재, DOI 10.1145/3774906.3800504) §1, TS 38.331 인용.
#: ⚠ 이 모듈은 이 값을 **쓰지 않는다**(같은 PRF 로 두 기하를 비교하는 것이 검증의 요점).
#:   자유도 축의 정량화는 ⟨outputs/mono_vs_passive.json §2 D1⟩ 에 이미 있다.
MONO_PRF_CEILING_HZ = 500.0


def mono_pos(h=MONO_H, xy=(0.0, 0.0)):
    """공배치 센서 위치 (x, y, h). 기본은 `MONO_POS`(조명원 마스트 자리)."""
    return (float(xy[0]), float(xy[1]), float(h))


# --------------------------------------------------------------------------- #
#  ① 기하 — 전부 fs_params 퇴화입력(TX=RX). 새 식 없음.
# --------------------------------------------------------------------------- #
def mono_target_pos(d, phi_deg, alt, sensor=MONO_POS) -> np.ndarray:
    """(수평거리 d[m], 방위 φ[deg], 고도 alt[m]) → 표적 위치 (…,3).

    `freespace_scene.target_pos(d, φ, L=0, alt)` 를 그대로 쓰고 센서 수평좌표만 더한다
    (L=0 이면 중점 O 가 센서 자신이라 두 축의 의미가 정확히 일치한다).

    ⭐ φ 는 **모노스태틱에서 무의미하다** — 기하가 센서의 연직축에 대해 회전대칭이기 때문이다.
      바이스태틱은 베이스라인이 대칭을 깨서 φ 가 1급 변수이고, 그래서 저장소 규약이 모든
      캡션에 φ=90° 를 명시하게 돼 있다(S7). 모노에서는 그 선언이 필요 없다. 여기서 φ 인자를
      **남겨두는 이유는 그 사실 자체를 수치로 보이기 위해서다**(회전대칭 검증).
    """
    p = fss.target_pos(d, phi_deg, 0.0, alt)
    s = np.asarray(sensor, float)
    return p + np.array([s[0], s[1], 0.0])


def mono_params(tgt, vel, fc, sensor=MONO_POS) -> dict:
    """표적위치[m]·표적속도[m/s]·반송파[Hz] → 모노스태틱 파라미터 dict.

    구현은 **`fss.fs_params(sensor, sensor, tgt, vel, fc)` 한 줄**이다. 반환키는
    바이스태틱과 완전히 같고(L,R1,R2,Rb,tau,fd,beta,lam,u1,u2,kappa,R_eq,el_deg),
    거기에 모노 전용 별칭 `R_m`(=R1=R2)·`u`(=u1=u2)·`Rb_over_2R` 를 덧붙인다.

    퇴화가 만드는 값(이 함수가 주장하는 것이 아니라 저장소 식이 내놓는 것):
        L = 0 · R1 = R2 = R · β = 0 · Rb = 2R · κ = R² · R_eq = R · f_d = 2 v·u/λ
    이 등식들이 정말 성립하는지는 `selfcheck_vs_freespace()` 가 매 실행마다 깨뜨려 본다.
    """
    p = fss.fs_params(sensor, sensor, tgt, vel, fc)
    R = np.asarray(p["R1"], float)
    out = dict(p)
    out["R_m"] = p["R1"]
    out["u"] = p["u1"]
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.asarray(p["Rb"], float) / np.maximum(2.0 * R, 1e-12)
    out["Rb_over_2R"] = float(ratio) if np.ndim(ratio) == 0 else ratio
    return out


def mono_params_closed(tgt, vel, fc, sensor=MONO_POS) -> dict:
    """**독립 닫힌형** 모노스태틱 파라미터 — 회귀잠금 전용(생산 경로 아님).

    `mono_params` 는 저장소 식의 퇴화입력이라 "저장소가 틀리면 같이 틀린다". 그래서 교과서
    식을 따로 적어 두 값을 대조한다(`freespace_scene.selfcheck_vs_repo` 와 같은 철학).

        R = |S − P| ,  u = (S − P)/R ,  f_d = 2 v·u / λ ,  R_b = 2R ,  τ = 2R/c ,
        β = 0 ,  κ = R² ,  el = arcsin(u_z)
    """
    S = np.asarray(sensor, float)
    P = np.asarray(tgt, float)
    V = np.asarray(vel, float)
    lam = C0 / float(fc)
    dvec = S - P
    R = np.linalg.norm(dvec, axis=-1)
    u = dvec / np.maximum(R, 1e-9)[..., None]
    fd = 2.0 * np.sum(V * u, axis=-1) / lam

    def _s(x):
        a = np.asarray(x, float)
        return float(a) if a.ndim == 0 else a

    return dict(L=0.0, R1=_s(R), R2=_s(R), R_m=_s(R), Rb=_s(2.0 * R), tau=_s(2.0 * R / C0),
                fd=_s(fd), beta=_s(np.zeros_like(R)), lam=lam, u1=u, u2=u, u=u,
                kappa=_s(R ** 2), R_eq=_s(R),
                el_deg=_s(np.degrees(np.arcsin(np.clip(u[..., 2], -1.0, 1.0)))))


def mono_R_of_d(d, alt, sensor=MONO_POS):
    """수평거리 d[m]·고도 alt[m] → 사거리 R[m] = √(d² + (alt − h_s)²).  배열 허용."""
    dh = float(alt) - float(np.asarray(sensor, float)[2])
    return np.sqrt(np.asarray(d, float) ** 2 + dh ** 2)


def mono_kappa_of_d(d, alt, sensor=MONO_POS):
    """κ(d) = R1·R2 = **R²** — `freespace_link.solve_range(kappa_of_d=…)`/`n_local` 에 그대로 넣는다.

    ⭐ 여기서 S1/S6 두 함정이 **동시에 약해진다**. κ=R²=d²+Δh² 는 d 에 대해 **단조증가**라
      (a) SNR(d) 가 단조감소이고(이분법이 유효해진다 — 바이스태틱에서 무효였던 그 이분법),
      (b) 국소지수 n = 2·dlnκ/dlnd = 4d²/(d²+Δh²) 가 **아래에서 4 로 빠르게 수렴**한다.
      바이스태틱은 표적이 RX 위를 지나며 κ 가 d 내부에서 최소를 가져 둘 다 깨진다.
      `solve_range` 의 '최외곽 하강교차'는 모노에서도 옳게 동작하므로 **호출부는 그대로 둔다**
      (단조여도 최외곽 교차 = 유일 교차라 답이 같다).
    """
    return mono_R_of_d(d, alt, sensor) ** 2


# --------------------------------------------------------------------------- #
#  ② 시간축 — 접힘·가드·나이퀴스트 전부 freespace_scene 승계
# --------------------------------------------------------------------------- #
def mono_fd_of_heading(psi_grid, phi, d, alt, speed, lam, sensor=MONO_POS):
    """(내부/공개) 헤딩격자 ψ[deg] 각각의 도플러 f_d[Hz] 와 그 지점의 기하 dict.

    `freespace_scene._fd_of_heading` 의 모노스태틱 판박이다 — 같은 순서로 같은 함수를 부른다
    (`target_pos → params → heading_velocity → V·(u1+u2)/λ`). u1=u2 이므로 이 내적은
    자동으로 `2 V·u/λ` 가 된다.
    """
    tgt = mono_target_pos(d, phi, alt, sensor)
    p = mono_params(tgt, (0.0, 0.0, 0.0), C0 / float(lam), sensor)
    V = fss.heading_velocity(np.asarray(psi_grid, float), float(speed))      # (N,3)
    fd = (V @ (p["u1"] + p["u2"])) / float(lam)                              # (N,)
    return fd, p


def mono_blind_sector(psi_grid, phi, d, alt, T, prf, speed, lam,
                      guard_bins=fss.GUARD_DOPPLER_BINS, M=None, sensor=MONO_POS) -> np.ndarray:
    """헤딩격자 ψ 각각 **도플러 블라인드인가**(True). `fss.blind_sector` 의 모노 판박이.

    blind ⇔ |folded_doppler(f_d(ψ), PRF)| < guard_bins·Δf_d  (F8 — 반드시 접은 값으로).
    """
    fd, _ = mono_fd_of_heading(psi_grid, phi, d, alt, speed, lam, sensor)
    return np.abs(fss.folded_doppler(fd, prf)) < fss.doppler_guard_hz(T, prf, M, guard_bins)


def mono_blind_fractions(psi_grid, phi, d, alt, T, prf, speed, lam, M=None,
                         sensor=MONO_POS,
                         hard_bins=fss.DOPPLER_GUARD_HARD_BINS,
                         declared_bins=fss.GUARD_DOPPLER_BINS) -> dict:
    """블라인드 비율을 **두 가드 규약 + 앨리어싱**으로 — `fss.blind_fractions` 와 **같은 키**.

    같은 키를 쓰는 것이 요점이다: 두 기하의 표를 나란히 놓고 뺄셈할 수 있어야 한다.
    추가키는 `beta_deg`(≡0 확인용)·`el_deg`·`proj_factor`(=|u1+u2|, 모노는 2)뿐이다.

    ⚠ 여기서 나오는 숫자가 기하에 의존하는 이유는 **법칙이 달라서가 아니라 투영인자 때문**이다:
      |u1+u2| = 2cos(β/2) 이고 모노는 β=0 이라 2(최대)다. 같은 속도·같은 PRF 에서
      모노가 바이스태틱보다 |f_d| 가 크므로 → 0-도플러 가드에 덜 걸리고(블라인드↓)
      나이퀴스트를 더 자주 넘는다(앨리어싱↑). 두 방향이 **반대**이며, 그래서 어느 한쪽만
      인용하면 결론이 뒤집힌다.
    """
    fd, p = mono_fd_of_heading(psi_grid, phi, d, alt, speed, lam, sensor)
    fb = fss.folded_doppler(fd, prf)
    bw = fss.doppler_bin_hz(T, prf, M)
    g_hard = float(hard_bins) * bw
    g_decl = float(declared_bins) * bw
    hard = np.abs(fb) < g_hard
    decl = np.abs(fb) < g_decl
    proj = float(np.linalg.norm(np.ravel(p["u1"]) + np.ravel(p["u2"])))
    return dict(blind_hard=float(np.mean(hard)), blind_declared=float(np.mean(decl)),
                soft_blind_frac=float(np.mean(decl & ~hard)),
                alias_frac=float(np.mean(~fss.nyquist_gate(fd, prf))),
                bin_hz=float(bw), f_guard_hard_hz=g_hard, f_guard_declared_hz=g_decl,
                guard_bins_hard=float(hard_bins), guard_bins_declared=float(declared_bins),
                prf_hz=float(prf), M=(int(M) if M else None),
                fd_hz=fd, fd_folded_hz=fb,
                beta_deg=float(np.ravel(p["beta"])[0]), el_deg=float(np.ravel(p["el_deg"])[0]),
                proj_factor=proj, R_m=float(np.ravel(p["R_m"])[0]),
                canonical="blind_hard (detector actually removes zd+-1 = 1.5 bins)")


def v_max_ms(lam, prf, beta_deg=0.0, delta_deg=0.0) -> float:
    """무모호 반경속도 v_max [m/s] = λ·PRF / (4·cos(β/2)·cos δ).

    **`benchmark/refrate_law.law_v_max` 에 위임한다**(식을 두 번 적지 않는다). 모노스태틱은
    β=0 이므로 정확히 `λ·PRF/4` 이고, 이것이 바이스태틱의 **최악값(하한)** 이다.
    ⇒ 발표한 1.07 m/s(5G SSB 50 Hz @3.5 GHz)는 모노스태틱 값이자 동시에 바이스태틱 바닥이다.
    """
    from refrate_law import law_v_max
    return float(law_v_max(lam, prf, beta_deg, delta_deg))


def bistatic_relief(beta_deg) -> float:
    """바이스태틱 완화계수 1/cos(β/2) — 모노(β=0) 대비 v_max 가 몇 배 커지나.

    β=0 → 1.000 · β=45° → 1.082 · β=90° → 1.414. 즉 **바이스태틱이 도플러 모호에 더 관대하다**.
    (그 대신 같은 인자만큼 |f_d| 가 작아 0-도플러 가드에는 더 잘 걸린다 — 공짜가 아니다.)
    """
    return float(1.0 / max(np.cos(np.radians(float(beta_deg)) / 2.0), 1e-12))


# --------------------------------------------------------------------------- #
#  ③ 유효범위 게이트
# --------------------------------------------------------------------------- #
def mono_beta_gate(beta_deg=0.0) -> bool:
    """바이스태틱각 게이트 — 모노스태틱에서는 **항상 통과**한다(β≡0 ≤ 90°).

    ⭐ 이것이 검출 계층에서 두 기하가 갈리는 가장 큰 기하 사실 중 하나다. 바이스태틱 FS-1 은
      근거리에서 β>90° 가 되어 SBR+PO 유효범위를 벗어나고(σ≡0 문제, `rcs_sbr.py:252-255`),
      그래서 스펙 §8.6 이 그 구역을 **해칭·수치인용 금지**로 묶는다(★L=500·alt=60·φ=90° 에서
      240칸 격자 중 앞 41칸). 모노스태틱에는 그 금지구역이 **존재하지 않는다** —
      근거리 수치를 그대로 인용할 수 있다.
    """
    return bool(fss.beta_gate(beta_deg))


def mono_farfield_gate(d, drone, fc, alt, sensor=MONO_POS) -> bool:
    """원거리장 게이트 — `fss.farfield_gate(R, …)`. 모노는 min(R1,R2)=R 이라 **엄밀판정**이다.

    (바이스태틱은 d 와 min(R1,R2) 가 달라 호출부가 무엇을 넣느냐로 엄밀/느슨이 갈린다.
     ⟨src/freespace_scene.py farfield_gate docstring⟩. 모노에는 그 모호가 없다.)
    """
    return fss.farfield_gate(mono_R_of_d(d, alt, sensor), drone, fc)


# --------------------------------------------------------------------------- #
#  ④ 링크 — 레이더 방정식은 link_budget/freespace_link 호출(재구현 금지)
# --------------------------------------------------------------------------- #
def mono_echo_power_w(eirp_dbm, grx_dbi, lam, sigma_m2, R, sys_loss_db=0.0):
    """모노스태틱 에코 수신전력 [W] — `freespace_link.echo_power_w(…, R1=R, R2=R)`.

        EIRP·G_rx·λ²·σ / ((4π)³ R⁴)
    바이스태틱식에 R1=R2=R 을 넣은 것이 **곧** 모노스태틱 레이더 방정식이다. 새 식이 없다.
    """
    return fsl.echo_power_w(eirp_dbm, grx_dbi, lam, sigma_m2, R, R, sys_loss_db=sys_loss_db)


def mono_snr_rd_db(eirp, grx, lam, sigma, R, nf=5.0, eta_ref=0.0, T=0.1,
                   losses=0.0, k_mode=0.0, n0_extra=0.0, sys_loss=0.0,
                   eta_ref_is_db=True, duty_db=0.0):
    """RD 맵 출력 SNR [dB] — `freespace_link.snr_rd_db(…, R1=R, R2=R)`. 인자·규약 전부 승계.

    `n0_extra` 자리에 **자기간섭 잔류 PSD** 를 넣으면 패시브의 DPI 잔류와 정확히 같은
    자리에서 비교된다(`si_residual_psd` 참조) — 두 문제가 같은 축의 다른 점임을 코드가 보인다.
    """
    return fsl.snr_rd_db(eirp, grx, lam, sigma, R, R, nf=nf, eta_ref=eta_ref, T=T,
                         losses=losses, k_mode=k_mode, n0_extra=n0_extra, sys_loss=sys_loss,
                         eta_ref_is_db=eta_ref_is_db, duty_db=duty_db)


def mono_required_isolation_db(eirp_dbm, grx_dbi, lam, sigma_m2, R, sys_loss_db=0.0) -> float:
    """**요구 자기간섭 격리** [dB] — 잔류 SI 를 표적 에코와 같은 높이까지 눌러야 하는 양.

        required = 10log10(EIRP / P_echo(R))

    ⚠ 기준면 규약: 격리를 **EIRP 기준**으로 잡는다(송신 안테나 이득이 누설경로에도 그대로
      실린다는 보수적 가정). 실제 STAR 전단은 안테나 격리·아날로그·디지털 소거가 다른 기준면에서
      걸리므로 이 값은 상한이다 — ⟨outputs/mono_vs_passive.json open_questions⟩ 가 남긴 유보와
      **같은 규약**을 쓴다(두 산출물의 숫자가 어긋나지 않게 하려고 일부러 맞췄다).
    ★재현: EIRP 63 dBm·G_rx 10 dBi·3.5 GHz·σ = −19.74 dBsm·R=100 m → 144.06 dB
      (⟨outputs/mono_vs_passive.json L3.rows : 144.064…⟩ 와 같은 값).
    """
    lb = LinkBudget(eirp_dbm=float(eirp_dbm), rx_gain_dbi=float(grx_dbi),
                    sys_loss_db=float(sys_loss_db))
    eirp_w = 10.0 ** (float(eirp_dbm) / 10.0) * 1e-3
    p_echo = lb.echo_power_w(lam, sigma_m2, R, R)
    return float(-lin2db(p_echo / eirp_w))


def si_residual_psd(eirp_dbm, isolation_db, b_noise_hz):
    """잔류 자기간섭 PSD [W/Hz] = `EIRP·10^(−isolation/10) / B_noise`.

    **패시브의 `freespace_link.n0_dpi(P_dir, depth, B)` 와 같은 형태**다 — 다른 것은 앞의
    전력항뿐이다(패시브: 베이스라인 L 을 지나온 직접파 / 모노: 자기 송신 그 자체).
    그래서 `mono_snr_rd_db(n0_extra=si_residual_psd(...) )` 로 바로 꽂힌다.
    `isolation_db=None` 또는 inf → 0.0(이상 격리).
    """
    return fsl.n0_dpi(10.0 ** (float(eirp_dbm) / 10.0) * 1e-3, isolation_db, b_noise_hz)


def isolation_gap_vs_passive_db(lam, L, grx_dbi=10.0) -> float:
    """⭐ 모노 요구격리 − 패시브 직접파/에코비 = **20log10(4πL/λ) − G_rx**  [dB]. 표적거리 무관.

    유도: mono_req = EIRP/P_echo, passive_DNR = P_dir/P_echo 이므로 차이는 EIRP/P_dir 이고,
    `LinkBudget.direct_power_w` 에서 P_dir = EIRP·G_rx·λ²/((4π)²L²) 이라 σ·R 이 **약분된다**.
    → 모노스태틱이 더 무는 양은 정확히 "패시브 직접파가 베이스라인에서 겪는 자유공간 손실"이다.
      L→0 이면 0 으로 가므로 **패시브가 모노스태틱으로 연속 수렴**한다 — 도플러 축의 β=0 절편과
      같은 구조다(⟨outputs/mono_vs_passive.json §2 D5 axis⟩ 와 같은 닫힌형; 여기서 재현·재검한다).
    """
    return float(20.0 * np.log10(4.0 * np.pi * float(L) / float(lam)) - float(grx_dbi))


# --------------------------------------------------------------------------- #
#  ⑤ 커버리지 — 검출 ∧ 무모호
# --------------------------------------------------------------------------- #
def usable_heading_fraction(fd, prf, T, snr_psi=None, snr_th=None, M=None,
                            hard_bins=fss.DOPPLER_GUARD_HARD_BINS) -> dict:
    """**쓸 수 있는 헤딩 비율** = (검출됨) ∧ (무모호). 세 마스크를 분해해서 함께 낸다.

    왜 분해하나: 세 검열이 **서로 상관**되어 있어서 한 숫자로 뭉치면 원인을 못 읽는다.
      · blind  : |접힌 f_d| < 1.5·Δf_d      (작은 도플러 — 호버·수직교차)
      · alias  : |f_d| ≥ PRF/2               (큰 도플러 — 빠른 표적)
      · snr    : SNR(ψ) < 문턱               (자세 σ 널)
    blind 와 alias 는 |f_d| 축의 **양 끝**이라 보통 배타적이지만, PRF 가 아주 낮으면 접힘이
    큰 도플러를 가드 안으로 되돌려 **동시에 참**이 될 수 있다(★SSB 50 Hz). 그래서 교집합도 낸다.
    `snr_psi`/`snr_th` 를 안 주면 SNR 인자를 1 로 두고 도플러 두 축만 판정한다.
    """
    fd = np.asarray(fd, float)
    fb = fss.folded_doppler(fd, prf)
    g = float(hard_bins) * fss.doppler_bin_hz(T, prf, M)
    blind = np.abs(fb) < g
    alias = ~np.asarray(fss.nyquist_gate(fd, prf), bool)
    if snr_psi is None or snr_th is None:
        ok_snr = np.ones(fd.shape, bool)
    else:
        ok_snr = np.asarray(snr_psi, float) >= float(snr_th)
    usable = (~blind) & (~alias) & ok_snr
    return dict(frac_blind_hard=float(np.mean(blind)), frac_alias=float(np.mean(alias)),
                frac_snr_ok=float(np.mean(ok_snr)),
                frac_blind_and_alias=float(np.mean(blind & alias)),
                frac_unambiguous=float(np.mean((~blind) & (~alias))),
                frac_usable=float(np.mean(usable)),
                f_guard_hard_hz=g, prf_hz=float(prf),
                max_abs_fd_hz=float(np.max(np.abs(fd))) if fd.size else float("nan"),
                note="usable = detectable(not blind, SNR>=th) AND unambiguous(not aliased)")


# --------------------------------------------------------------------------- #
#  ⑥ 회귀 잠금 — "퇴화입력이 정말 모노스태틱인가" 를 저장소 안에 박아둔다
# --------------------------------------------------------------------------- #
def selfcheck_vs_freespace(n=2000, seed=17, tol=1e-9, eps_list=(1.0, 1e-1, 1e-2, 1e-3, 1e-4)) -> dict:
    """세 가지를 **깨질 수 있게** 확인한다(`fss.selfcheck_vs_repo` 와 같은 철학).

    A. 퇴화 항등식 : `mono_params`(저장소 퇴화입력) vs `mono_params_closed`(독립 닫힌형)
       — R1=R2, β=0, Rb=2R, κ=R², f_d=2v·u/λ 가 전부 일치하는가.
    B. 연속성      : 바이스태틱 `fs_params(S, S+εx̂, …)` 가 ε→0 에서 모노 값으로 **수렴**하는가
       — 모노스태틱이 별종이 아니라 바이스태틱의 L→0 극한임을 수치로 보인다.
    C. 도플러 바닥 : `nyquist_gate` 로 이분 탐색한 **접힘 시작 속도**가 `λ·PRF/4` 와 같은가
       — 링크 계층(1/R⁴)과 무관하게 바닥이 안 바뀐다는 것이 이 항목의 요지다.

    반환 dict: A/B/C 각각의 최대 상대오차와 ok 플래그.
    """
    rng = np.random.default_rng(int(seed))
    lam_pool = [C0 / f for f in (1.843e9, 3.5e9, 5.21e9)]

    # --- A. 퇴화 항등식 --------------------------------------------------- #
    worst = dict(R=0.0, beta_deg=0.0, Rb_over_2R=0.0, kappa=0.0, fd=0.0, el_deg=0.0)
    for _ in range(int(n)):
        S = np.array([0.0, 0.0, 25.0]) + rng.uniform(-50, 50, 3)
        P = rng.uniform(-3000, 3000, 3) + np.array([0.0, 0.0, 100.0])
        V = rng.uniform(-25, 25, 3)
        fc = C0 / float(rng.choice(lam_pool))
        a = mono_params(P, V, fc, sensor=S)
        b = mono_params_closed(P, V, fc, sensor=S)
        R = float(b["R_m"])
        worst["R"] = max(worst["R"], abs(float(a["R1"]) - float(a["R2"])) / R)
        worst["beta_deg"] = max(worst["beta_deg"], abs(float(a["beta"])))
        worst["Rb_over_2R"] = max(worst["Rb_over_2R"], abs(float(a["Rb_over_2R"]) - 1.0))
        worst["kappa"] = max(worst["kappa"], abs(float(a["kappa"]) - R ** 2) / R ** 2)
        worst["fd"] = max(worst["fd"], abs(float(a["fd"]) - float(b["fd"]))
                          / max(abs(float(b["fd"])), 1e-12))
        worst["el_deg"] = max(worst["el_deg"], abs(float(a["el_deg"]) - float(b["el_deg"])))
    ok_a = bool(worst["R"] <= tol and worst["Rb_over_2R"] <= tol
                and worst["kappa"] <= 1e-12 and worst["fd"] <= 1e-9)

    # --- B. L→0 연속성 ---------------------------------------------------- #
    S = np.array(MONO_POS, float)
    P = mono_target_pos(1000.0, 90.0, 60.0, S)
    V = fss.heading_velocity(37.0, 5.0).ravel()
    fc = 3.5e9
    m = mono_params(P, V, fc, sensor=S)
    conv = []
    for eps in eps_list:
        pb = fss.fs_params(S, S + np.array([float(eps), 0.0, 0.0]), P, V, fc)
        conv.append(dict(eps_m=float(eps), beta_deg=float(pb["beta"]),
                         fd_rel_err=float(abs(float(pb["fd"]) - float(m["fd"]))
                                          / max(abs(float(m["fd"])), 1e-12)),
                         Rb_rel_err=float(abs(float(pb["Rb"]) - float(m["Rb"]))
                                          / max(abs(float(m["Rb"])), 1e-12))))
    ok_b = bool(conv[-1]["fd_rel_err"] < 1e-6 and conv[-1]["beta_deg"] < 1e-3
                and all(conv[i]["fd_rel_err"] >= conv[i + 1]["fd_rel_err"] - 1e-15
                        for i in range(len(conv) - 1)))

    # --- C. 도플러 바닥(λ·PRF/4) ------------------------------------------ #
    psi = np.linspace(0.0, 360.0, 1440, endpoint=False)
    lam = C0 / 3.5e9
    rows = []
    for prf in (6.25, 12.5, 25.0, 50.0, 100.0, 200.0, 500.0, 1000.0):
        lo, hi = 1e-4, 200.0

        def _folds(v):
            fd, _ = mono_fd_of_heading(psi, 90.0, 1000.0, 60.0, v, lam, S)
            return bool(np.any(~np.asarray(fss.nyquist_gate(fd, prf), bool)))

        if _folds(lo):
            v_star = lo
        else:
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if _folds(mid):
                    hi = mid
                else:
                    lo = mid
            v_star = 0.5 * (lo + hi)
        # 이 기하의 최대 도플러는 cos(el) 만큼 줄어 있으므로 예측값도 같은 인자로 보정한다
        el = float(mono_params(mono_target_pos(1000.0, 90.0, 60.0, S),
                               (0, 0, 0), C0 / lam, S)["el_deg"])
        pred = v_max_ms(lam, prf, 0.0, el)
        rows.append(dict(prf_hz=float(prf), v_fold_onset_ms=float(v_star),
                         v_max_law_ms=float(pred),
                         rel_err=float(abs(v_star - pred) / max(pred, 1e-12))))
    ok_c = bool(max(r["rel_err"] for r in rows) < 1e-4)

    return dict(
        A_degenerate_identity=dict(n=int(n), max_dev=worst, ok=ok_a, tol=float(tol)),
        B_L_to_zero_continuity=dict(rows=conv, ok=ok_b,
                                    note="bistatic fs_params(S, S+eps) -> monostatic as eps->0"),
        C_doppler_floor=dict(rows=rows, ok=ok_c,
                             law="v_max = lam*PRF/(4 cos(beta/2) cos delta), beta=0 monostatic"),
        ok=bool(ok_a and ok_b and ok_c))


if __name__ == "__main__":                     # 간단 자기점검
    r = selfcheck_vs_freespace(n=300)
    print("selfcheck ok =", r["ok"], {k: v["ok"] for k, v in r.items() if isinstance(v, dict)})
    lam = C0 / 3.5e9
    print("v_max(50 Hz) mono = %.6f m/s ; bistatic beta=90 relief x%.3f"
          % (v_max_ms(lam, 50.0), bistatic_relief(90.0)))
    print("required isolation @100 m = %.2f dB"
          % mono_required_isolation_db(63.0, 10.0, lam, 10 ** (-19.74 / 10), 100.0))
    print("isolation gap vs passive (L=500) = %.2f dB" % isolation_gap_vs_passive_db(lam, 500.0))
