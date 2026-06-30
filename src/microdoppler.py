# -*- coding: utf-8 -*-
"""
microdoppler.py — (report3 토대) 회전 프로펠러의 **마이크로-도플러** 시그니처
=============================================================================

분절 드론 모델(drones.pose/build_frame/build_propeller)을 이용해, 표적이 정지(호버)해도
**회전하는 블레이드**가 만드는 시간변조 후방산란을 계산한다.

원리
  몸체(프레임)는 0 도플러(상수 산란장 E_frame). 각 로터의 블레이드는 ω로 회전하므로
  표면점 위치가 시간에 따라 변해 위상이 변조된다 → 슬로타임 복소장 E(t):
      E(t) = E_frame + Σ_rotor exp(j2k·c·û) · Σ_p [n̂·v>0](n̂·v)ΔA·exp(j2k·P_local·v(t))
  여기서 v(t)=Rz(−θ(t))·û 는 '블레이드를 돌리는 대신 시선을 반대로 돌린' 등가표현(벡터화).
  θ(t)=base+dir·ω·t,  ω=2π·rpm/60,  dir=±1(CW/CCW).

  스펙트로그램(STFT)으로 보면: **블레이드가 시선에 수직일 때 번쩍(blade flash)** → 주기적
  세로 줄무늬 + 팁속도까지 퍼진 도플러(±f_tip, f_tip≈2·ω·R_blade/λ·cos el).
  (스펙트로그램에선 강한 정적 몸체항을 0-도플러 클러터로 제거 — spectrogram(remove_dc=True).)

주의(현실 연결): f_tip 은 수백~수천 Hz라, **이를 모호 없이 보려면 PRF≳2·f_tip(수 kHz↑)** 필요.
  5G SSB(50Hz)·CSI-RS(200Hz)·LTE CRS(1kHz) 같은 파일럿 반복률로는 블레이드 마이크로도플러가
  접힌다 → LaSen 류가 '기준+데이터'로 샘플률을 끌어올리는 또 하나의 이유.
"""
from __future__ import annotations
import numpy as np

from drones import build_frame, build_propeller, rotor_layout
from rcs_po import mesh_to_points, po_field_dir, C0


def _look(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


def microdoppler_series(spec, fc=3.5e9, az=0.0, el=15.0, rpm=6000.0,
                        prf=20000.0, n_t=2048, spacing=None):
    """회전 블레이드의 슬로타임 복소장 E(t). 반환 (t[s], E[복소], info)."""
    lam = C0 / fc; k = 2 * np.pi / lam
    spacing = spacing or lam / 6.0
    u = _look(az, el); ux, uy, uz = u

    # 프레임(비회전) → 상수 산란장
    Pf, Nf, dAf = mesh_to_points(build_frame(spec), spacing)
    Ef = po_field_dir(Pf, Nf, dAf, fc, u)

    # 프로펠러 1개(허브 로컬) → 모든 로터가 공유, 회전만 다름
    Pp, Np_, dAp = mesh_to_points(build_propeller(spec), spacing)
    rl = rotor_layout(spec)

    t = np.arange(n_t) / prf
    omega = 2 * np.pi * rpm / 60.0
    E = np.full(n_t, Ef, complex)
    for rot in rl:
        cx, cy, cz = rot["center"]; base = np.radians(rot["base_ang"]); d = rot["dir"]
        th = base + d * omega * t                                   # (n_t,)
        # v(t) = Rz(-θ)·û  (블레이드 회전 ≡ 시선 반대회전)
        vx = ux * np.cos(th) + uy * np.sin(th)
        vy = -ux * np.sin(th) + uy * np.cos(th)
        vz = np.full_like(th, uz)
        V = np.stack([vx, vy, vz], axis=1)                          # (n_t,3)
        NU = Np_ @ V.T                                              # (Npts, n_t)
        PU = Pp @ V.T
        integ = np.where(NU > 0, NU, 0.0) * dAp[:, None] * np.exp(1j * 2 * k * PU)
        Eb = integ.sum(axis=0) * np.exp(1j * 2 * k * (cx * ux + cy * uy + cz * uz))
        E += Eb

    prop_R = spec.prop_dia_mm / 1000.0 / 2.0
    f_tip = 2.0 * (omega * prop_R) / lam * np.cos(np.radians(el))    # 최대 마이크로도플러[Hz]
    info = dict(rpm=rpm, prf=prf, fc=fc, lam=lam, az=az, el=el,
                f_tip=f_tip, flash_hz=spec.prop_blades * rpm / 60.0,
                v_tip=omega * prop_R, n_rotors=len(rl))
    return t, E, info


def spectrogram(E, prf, nperseg=256, noverlap=None, remove_dc=True):
    """복소 E(t) → (도플러축 f[Hz], 시간축 t[s], |STFT| dB). 양측(±) 도플러.
    remove_dc=True: **정적 0-도플러(몸체 프레임) 성분을 빼고** 회전 블레이드 마이크로도플러만 본다
    (패시브레이더의 '정적 클러터 제거'에 해당). E(t) 자체엔 몸체가 강한 0-도플러 상수항으로 들어 있어
    (|DC|/std(AC)≈25), 그대로 두면 블레이드 성분이 묻힌다. 평균 제거 후 detrend=False 로 STFT."""
    from scipy.signal import spectrogram as _spec
    E = np.asarray(E)
    if remove_dc:
        E = E - E.mean()                                # 정적(몸체) 0-도플러 클러터 제거
    noverlap = noverlap if noverlap is not None else nperseg - nperseg // 8
    f, tt, Sxx = _spec(E, fs=prf, nperseg=nperseg, noverlap=noverlap, detrend=False,
                       return_onesided=False, scaling="spectrum", mode="magnitude")
    f = np.fft.fftshift(f); Sxx = np.fft.fftshift(Sxx, axes=0)
    Sdb = 20 * np.log10(Sxx / (Sxx.max() + 1e-30) + 1e-12)
    return f, tt, Sdb


if __name__ == "__main__":
    from drones import DRONES
    for k in ("phantom4", "s1000plus"):
        t, E, info = microdoppler_series(DRONES[k], rpm=6000)
        print(f"{k:10s} 로터{info['n_rotors']} rpm{info['rpm']:.0f} "
              f"f_tip={info['f_tip']:.0f}Hz flash={info['flash_hz']:.0f}Hz "
              f"v_tip={info['v_tip']:.0f}m/s  |E|평균={np.abs(E).mean():.2e} 변동={np.std(np.abs(E)):.2e}")
