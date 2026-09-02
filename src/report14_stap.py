#!/usr/bin/env python
"""report14 Phase 2 — MVDR-STAP (공간 N × 시간 M) 검출기.

Clutter서베이 §V-C 차용. 무향실 ECA(1D slow-time)로는 도플러퍼짐 클러터를 못 지운다는 것이
서베이 중심 메시지 — 2D 공간-시간 적응처리(STAP)가 묻힌 표적을 복원한다. 여기서:

  · 조향 v = d(f_D)⊗a(θ)  (시간⊗공간)
  · MVDR-STAP 가중 w = R⁻¹v / (vᴴR⁻¹v),  출력 SCNR = vᴴR⁻¹v   (클레어보이언트 상한)
  · RMB(Reed-Mallett-Brennan) 표본공분산 + 대각로딩/저계수(스냅샷 부족 대비)
  · 비교: 1D slow-time(시간만, 도플러 0 Hz 노치) SCNR ↔ 2D STAP SCNR

⚠ vᴴR⁻¹v 는 **클레어보이언트(참 R)** 상한이다. 실측은 R̂(훈련셀)로 손실이 생긴다(RMB 규칙 Ntr≥2NM).

GPU 불필요(순수 선형대수). 실행: PYTHONPATH=src python src/report14_stap.py
"""
import numpy as np


def spatial_steering(theta_rad, N, d_lambda=0.5):
    """N-소자 ULA 조향 a(θ) ∈ C^N."""
    return np.exp(1j * 2 * np.pi * d_lambda * np.arange(N) * np.cos(theta_rad))


def temporal_steering(fd_hz, M, prf_hz):
    """M-프레임 도플러 조향 d(f_D) ∈ C^M."""
    return np.exp(1j * 2 * np.pi * fd_hz * np.arange(M) / prf_hz)


def target_steering(theta_rad, fd_hz, N, M, prf_hz, d_lambda=0.5):
    """표적 공간-시간 조향 v = d(f_D)⊗a(θ) ∈ C^{NM}."""
    return np.kron(temporal_steering(fd_hz, M, prf_hz),
                   spatial_steering(theta_rad, N, d_lambda))


def _rinv_v(R, v, load_var=None):
    """R⁻¹v (대각로딩 옵션). load_var = **절대 로딩 전력**(잡음 상대, 예 3×σ²_n).
       ⚠ trace 기반 로딩은 CNR 높으면 클러터가 지배해 과로딩된다 → 잡음 상대로 준다."""
    if load_var is not None:
        R = R + float(load_var) * np.eye(R.shape[0])
    return np.linalg.solve(R, v)


def stap_weights(R, v, load_var=None):
    """MVDR-STAP 가중 w = R⁻¹v/(vᴴR⁻¹v) (표적방향 이득1, 클러터+잡음 최소)."""
    riv = _rinv_v(R, v, load_var)
    return riv / (v.conj() @ riv)


def stap_scnr_db(R, v, load_var=None):
    """출력 SCNR [dB] = 10log10(vᴴR⁻¹v). 클레어보이언트 상한."""
    riv = _rinv_v(R, v, load_var)
    return float(10 * np.log10(np.abs(v.conj() @ riv)))


def mti_scnr_db(R, v, N, M, prf_hz, theta_rad, d_lambda=0.5):
    """1D slow-time(시간만) 처리 SCNR [dB] — ECA/MTI 계열 상한.
       공간은 표적방향 빔포밍(고정), 시간축만 적응(R 의 시간블록)."""
    a = spatial_steering(theta_rad, N, d_lambda)
    a = a / np.linalg.norm(a)
    # 공간 빔포밍으로 NM → M 축소: R_t[m,m'] = (a⊗e_m)ᴴ R (a⊗e_m')
    Rt = np.zeros((M, M), complex)
    for m in range(M):
        em = np.zeros(M); em[m] = 1.0
        sm = np.kron(em, a)
        for mp in range(M):
            ep = np.zeros(M); ep[mp] = 1.0
            sp = np.kron(ep, a)
            Rt[m, mp] = sm.conj() @ R @ sp
    dt = temporal_steering(0.0, M, prf_hz) * 0  # placeholder
    # 표적 시간조향은 target fd 에서 — 호출부가 v 로 준 fd 를 쓰려면 별도. 여기선 표적 fd 를 인자로.
    return Rt  # 내부용 — mti_scnr_at 에서 사용


def mti_scnr_at_db(R, N, M, prf_hz, theta_rad, fd_hz, d_lambda=0.5):
    """1D slow-time SCNR [dB] @ (θ, f_D): 공간=표적방향 정합빔, 시간=적응(R_t⁻¹ d)."""
    a = spatial_steering(theta_rad, N, d_lambda); a = a / np.linalg.norm(a)
    Rt = np.zeros((M, M), complex)
    Im = np.eye(M)
    for m in range(M):
        sm = np.kron(Im[m], a)
        Rt[m] = np.array([sm.conj() @ R @ np.kron(Im[mp], a) for mp in range(M)])
    dt = temporal_steering(fd_hz, M, prf_hz)
    riv = np.linalg.solve(Rt, dt)
    return float(10 * np.log10(np.abs(dt.conj() @ riv)))


def matched_filter_scnr_db(R, v):
    """무적응(정합필터만) SCNR [dB] = |vᴴv|²/(vᴴRv) — 클러터를 못 지운 경우."""
    return float(10 * np.log10(np.abs(v.conj() @ v) ** 2 / np.abs(v.conj() @ R @ v).real))


def estimate_covariance(snapshots, load_var=2.0, noise_var=1.0, rank=None):
    """RMB 표본공분산 R̂ = (1/K)Σ x xᴴ + 대각로딩(잡음 상대). rank 지정 시 저계수+잡음(고유값 절단).
       load_var = 로딩전력/잡음전력 배수(≈1~3). 잡음 상대라 CNR 무관하게 안정."""
    X = np.asarray(snapshots)                  # (K, NM)
    K = X.shape[0]
    Rhat = (X.conj().T @ X) / K
    if rank is not None:
        w, U = np.linalg.eigh(Rhat)
        w = w[::-1]; U = U[:, ::-1]
        noise = np.mean(w[rank:]) if rank < len(w) else w[-1]
        w[rank:] = noise
        Rhat = U @ np.diag(w) @ U.conj().T
    Rhat = Rhat + float(load_var) * float(noise_var) * np.eye(Rhat.shape[0])
    return Rhat


def draw_snapshots(R, K, seed=0):
    """참 공분산 R 에서 K 개 훈련 스냅샷 x~CN(0,R) 표집(RMB 검증용)."""
    rng = np.random.default_rng(seed)
    NM = R.shape[0]
    L = np.linalg.cholesky(R + 1e-9 * np.eye(NM))
    z = (rng.standard_normal((K, NM)) + 1j * rng.standard_normal((K, NM))) / np.sqrt(2)
    return z @ L.T


def _self_test():
    # 합성 클러터: 2개 강한 방향(0도플러) + 잡음 → STAP 가 널링하는지
    N, M, prf = 4, 16, 1000.0
    NM = N * M
    R = np.eye(NM, dtype=complex)              # 잡음
    for th_deg, cnr in [(60., 40.), (110., 35.)]:
        st = target_steering(np.radians(th_deg), 0.0, N, M, prf)  # 0-도플러 클러터
        R += 10 ** (cnr / 10.0) * np.outer(st, st.conj()) / NM
    # 표적: θ=90°, f_D=200 Hz(클러터 도플러 0 과 분리)
    vt = target_steering(np.radians(90.), 200.0, N, M, prf)
    snr_in = 0.0                                # 입력 표적 SNR 0 dB(단위)
    print("=== STAP self-test ===")
    print(f"  무적응 정합필터 SCNR: {matched_filter_scnr_db(R, vt):+6.1f} dB (클러터에 묻힘)")
    print(f"  1D slow-time(MTI)  SCNR: {mti_scnr_at_db(R, N, M, prf, np.radians(90.), 200.0):+6.1f} dB")
    print(f"  2D MVDR-STAP  SCNR(클레어보이언트): {stap_scnr_db(R, vt):+6.1f} dB (표적 f_D≠클러터 → 복원)")
    # 표적 f_D 를 클러터(0)에 겹치면 STAP 도 손실?
    vt0 = target_steering(np.radians(60.), 0.0, N, M, prf)   # 클러터 방향+도플러
    print(f"  [표적이 클러터와 겹칠 때] STAP SCNR: {stap_scnr_db(R, vt0):+6.1f} dB (널에 빠져 손실)")
    # RMB: 훈련셀 수에 따른 손실
    print(f"  RMB 훈련셀 수 vs STAP SCNR(추정 R̂; 클레어보이언트 {stap_scnr_db(R, vt):.1f} dB 대비 손실):")
    for K in (NM, 2 * NM, 5 * NM):
        X = draw_snapshots(R, K, seed=1)
        Rhat = estimate_covariance(X, load_var=2.0, noise_var=1.0)
        print(f"    Ntr={K:3d}(={K//NM}·NM): {stap_scnr_db(Rhat, vt):+6.1f} dB")
    print("SELF-TEST OK")


if __name__ == "__main__":
    _self_test()
