#!/usr/bin/env python
"""report14 Phase 1 — Sionna RT 실외 다중경로 씬 → 클러터 공분산.

교수님 각도(환경 리얼리스틱)의 환경 절반. 무향실 대신 **내장 실외 씬**(street canyon / munich)에서
확산산란(R²+S²=1, 재질별 S; Montaner EuCAP2026 §II.D·Clutter서베이 GIT)을 켜고 PathSolver 로
TX→RX 환경 다중경로(=cold 클러터)를 추출한다. 각 경로의 지연 τ·복소진폭 a·수신각 (θ_r,φ_r)·도플러 f_D 를
얻어 **공간(AoA)×시간(도플러) 클러터 공분산** Vᶜᶜ 를 만든다 — 이게 STAP(Phase 2)의 입력이다.

⚠ 표적 밝기 σ 는 report13 SBR+PO 격자로 주입한다(few-λ 드론은 스톡 Sionna 부정확 — 우리 메모).
   여기서는 **환경만** RT 로 짓는다.

실행(스모크): PYTHONPATH=src:benchmark SIONNA2_GPU=1 python src/report14_scene.py
"""
import os
os.environ.setdefault("SIONNA2_GPU", "1")
import numpy as np                                    # noqa: E402
import sionna.rt as rt                                # noqa: E402
from sionna.rt import (load_scene, PathSolver, Transmitter, Receiver,  # noqa: E402
                       PlanarArray)

C0 = 299792458.0

# 내장 실외 씬 레지스트리
SCENES = {
    "street_canyon": rt.scene.simple_street_canyon_with_cars,
    "munich": rt.scene.munich,
    "etoile": rt.scene.etoile,
    "florence": rt.scene.florence,
}

# 재질별 산란계수 S (Montaner §II.D 'informed by empirical [13]', Clutter서베이 §IV-A2 GIT).
# R²+S²=1. 금속=거의 정반사(S 작음), 콘크리트/벽돌=거친면(S 큼).
MAT_S = {"metal": 0.10, "glass": 0.20, "concrete": 0.50, "brick": 0.55,
         "wood": 0.45, "marble": 0.30, "itu_concrete": 0.50, "itu_brick": 0.55,
         "itu_glass": 0.20, "itu_metal": 0.10}


def load_outdoor_scene(name="street_canyon", fc=3.5e9, diffuse=True, s_default=0.4):
    """실외 씬 로드 + 단일안테나 배열 + 재질별 확산산란 설정."""
    sc = load_scene(SCENES[name])
    sc.frequency = float(fc)
    sc.tx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    sc.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    if diffuse:
        for mname, mat in sc.radio_materials.items():
            key = mname.lower()
            s = next((v for k, v in MAT_S.items() if k in key), s_default)
            try:
                mat.scattering_coefficient = float(s)
            except Exception:
                pass
    return sc


def _reset_radios(sc):
    for n in list(getattr(sc, "transmitters", {}) or {}):
        sc.remove(n)
    for n in list(getattr(sc, "receivers", {}) or {}):
        sc.remove(n)


def extract_clutter_paths(sc, tx_pos, rx_pos, max_depth=3, diffuse=True,
                          drop_los=True, top_k=80):
    """TX→RX 환경 다중경로(=cold 클러터) 추출 → **전력 상위 top_k 지배경로**.

    확산산란은 수만 경로를 낳지만 대부분 −130 dB 이하로 무시가능 → 전력순 top_k 만 남긴다(공분산 tractable).
    최단지연 경로 = 직접파 → `drop_los=True` 면 뺀다(클러터만; 직접파는 ECA/레퍼런스가 따로 처리)."""
    _reset_radios(sc)
    sc.add(Transmitter("tx", position=[float(x) for x in tx_pos]))
    sc.add(Receiver("rx", position=[float(x) for x in rx_pos]))
    p = PathSolver()(scene=sc, max_depth=max_depth,
                     diffuse_reflection=diffuse, refraction=False)
    tau = np.asarray(p.tau).ravel()
    theta_r = np.asarray(p.theta_r).ravel()
    phi_r = np.asarray(p.phi_r).ravel()
    dopp = np.asarray(p.doppler).ravel()
    a = np.asarray(p.a)
    n_path = tau.shape[0]
    a_flat = a.reshape(a.shape[0], -1, n_path)
    amp = (a_flat[0] + 1j * a_flat[1]).sum(axis=0)        # 경로별 복소진폭
    valid = tau >= 0
    idx = np.where(valid)[0]
    tau, theta_r, phi_r, dopp, amp = (tau[idx], theta_r[idx], phi_r[idx],
                                      dopp[idx], amp[idx])
    if drop_los and tau.size:                             # 직접파(최단지연) 제거
        keep = np.argsort(tau)[1:]
        tau, theta_r, phi_r, dopp, amp = (tau[keep], theta_r[keep], phi_r[keep],
                                          dopp[keep], amp[keep])
    pw = np.abs(amp) ** 2
    if tau.size > top_k:                                  # 전력 상위 top_k
        sel = np.argsort(pw)[::-1][:top_k]
        tau, theta_r, phi_r, dopp, amp = (tau[sel], theta_r[sel], phi_r[sel],
                                          dopp[sel], amp[sel])
    order = np.argsort(tau)                               # 지연순 정렬(보기 좋게)
    return dict(tau=tau[order], theta_r=theta_r[order], phi_r=phi_r[order],
                doppler=dopp[order], amp=amp[order], n_path=int(tau.size),
                total_paths=int(n_path))


def _spatial_steering(theta_r, N, d_lambda=0.5):
    """N-소자 균일선형배열(ULA) 조향벡터 v(θ) ∈ C^N. θ=수신 극각(rad)."""
    n = np.arange(N)
    # 배열 축을 따른 방향여현(간단 ULA 모델, φ 무시하고 θ 사용)
    return np.exp(1j * 2 * np.pi * d_lambda * n * np.cos(theta_r))


def _temporal_steering(fd_hz, M, prf_hz):
    """M-프레임 슬로우타임 도플러 조향 d(f_D) ∈ C^M."""
    m = np.arange(M)
    return np.exp(1j * 2 * np.pi * fd_hz * m / prf_hz)


def clutter_covariance(clut, N, M, prf_hz, cnr_db=40.0, noise_var=1.0, d_lambda=0.5):
    """공간(N)×시간(M) 클러터+잡음 공분산 R ∈ C^{NM×NM} (서베이 Eq.60 공간-시간판).
       R = Σ_i p_i·(d(f_D,i)⊗v(θ_i))(·)ᴴ + σ²_n·I.
       **CNR 앵커**: RT 절대전력은 조명원·거리에 의존하므로, 경로 전력비(공간·도플러 구조)만 살리고
       총 클러터전력/잡음전력 = 10^(cnr_db/10) 로 정규화한다(서베이 setup: 클러터가 표적을 수십 dB 묻음)."""
    NM = N * M
    amp = clut["amp"]; th = clut["theta_r"]; fd = clut["doppler"]
    pw = np.abs(amp) ** 2
    pw = pw / max(pw.sum(), 1e-30) * (10 ** (cnr_db / 10.0)) * noise_var   # CNR 앵커
    R = np.zeros((NM, NM), complex)
    for i in range(clut["n_path"]):
        st = np.kron(_temporal_steering(fd[i], M, prf_hz),
                     _spatial_steering(th[i], N, d_lambda))
        R += pw[i] * np.outer(st, st.conj())
    R += noise_var * np.eye(NM)
    return R


def _self_test():
    fc = 3.5e9
    sc = load_outdoor_scene("street_canyon", fc=fc, diffuse=True)
    print(f"씬 로드: street_canyon · {len(sc.objects)} 객체 · {fc/1e9} GHz · 확산산란 ON")
    clut = extract_clutter_paths(sc, tx_pos=[-40, 0, 10], rx_pos=[40, 0, 3],
                                 max_depth=3, diffuse=True, drop_los=True, top_k=80)
    print(f"클러터 경로: 전체 {clut['total_paths']:,} → 전력상위 {clut['n_path']}개")
    print(f"  지연 [ns]: {clut['tau'].min()*1e9:.1f}~{clut['tau'].max()*1e9:.1f}")
    print(f"  수신각 θ_r [deg]: {np.degrees(clut['theta_r']).min():.1f}~{np.degrees(clut['theta_r']).max():.1f}")
    print(f"  도플러 [Hz]: {clut['doppler'].min():.2f}~{clut['doppler'].max():.2f}  (정적 씬이면 ≈0)")
    pw = np.abs(clut['amp'])**2
    print(f"  경로 전력 상대범위 [dB]: {10*np.log10(pw.max()/pw.min()):.1f} (top÷bottom)")
    N, M, prf = 4, 16, 1000.0
    R = clutter_covariance(clut, N, M, prf, cnr_db=40.0, noise_var=1.0)
    ev = np.linalg.eigvalsh(R)[::-1]
    n_clut = int(np.sum(ev > 2.0))                        # 잡음(1.0)의 2배 초과 = 클러터 고유값
    print(f"클러터 공분산 R: {R.shape} · 에르미트오차 {np.max(np.abs(R-R.conj().T)):.2e}")
    print(f"  고유값 top5 [dB]: {np.round(10*np.log10(ev[:5]),1)}")
    print(f"  클러터 랭크(고유값>2×잡음): {n_clut}/{N*M} · CNR 앵커 40 dB")
    print(f"  Brennan rule 예상 랭크 ≈ N + (M-1)·β (β=클러터 도플러기울기); 정적클러터면 공간랭크만")
    print("SELF-TEST OK")


if __name__ == "__main__":
    _self_test()
