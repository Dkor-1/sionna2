# -*- coding: utf-8 -*-
"""
experiment_x410.py — **USRP X410 실증실험과 1:1 로 맞춘 시뮬레이션 설정**
==========================================================================
목적: 시뮬레이션 구도를 **실제로 만들 X410 실험과 같은 구조**로 박아, 시뮬↔실측을 대조 가능하게.

■ 프로젝트 방향 (2026-07-14 확정 — memory: sionna2-project-direction)
  · **태스크 = 디텍션**. 트래킹 아님. (조사 논문 21편 대부분이 디텍션서 멈춤; 트래킹은 배열 필요.)
  · **시뮬 = 통제 챔버(레지스트리 전 기종)** — 공정성. **실측 = 외부(outdoor), 드론 2종**(Mavic4Pro·Matrice4E).
    → 시뮬↔실측은 **환경이 1:1 아님**. STRUCTURE(바이스태틱·기준+감시·같은 파형·디텍션 체인)만 같다.
    → **외부에선 지면반사·건물 다중경로가 챔버 바닥유령보다 심각**하고, 정적 클러터가 챔버에선
      죽은 파라미터였지만(ECA 완벽) **외부+12bit ADC에선 안 죽는다**(report4 [E2] caveat가 실측서 결정적).

■ 왜 능동(active) 바이스태틱 테스트베드인가
  진짜 5G 기지국을 조명원으로 빌리면 동기·타이밍·기준신호 캡처가 까다롭다. 대신 **X410 이
  직접 후보 파형을 송신**하면(같은 클럭·완전 제어), 패시브 레이더를 **흉내내면서도** 실험이
  재현 가능해진다. "어느 파형이 드론 탐지에 유리한가" 는 X410 이 WiFi/LTE/5G 흉내 파형을
  각각 송신해 탐지성능을 재면 그대로 답이 나온다 — 우리 벤치마크의 중심 질문이다.

■ USRP X410 하드웨어 (ni.com / ettus.com 스펙, 2024)
  · **TX 4채널 + RX 4채널** (ZBX 도터보드 2장, 채널당 2)
  · 채널당 **순시대역폭 400 MHz**  → 거리분해능(바이스태틱) c/B ≈ 0.75 m (광대역이면; 모노 등가 0.37 m)
  · **1 MHz ~ 7.2 GHz** (8 GHz 까지 튜닝) → 3.5 GHz(5G n78)·2.4/5 GHz(WiFi)·1.8 GHz(LTE) 전부 커버
  · ADC **12-bit** → 동적범위 ~72 dB (★ 이게 중요하다 — 아래)

■ 4개 RX 채널을 어떻게 쓰나 (★ 트래킹 관측가능성 문제를 하드웨어가 푼다)
  report4 [E5]: **안테나 1개로는 3D 위치가 원리적으로 안 나온다**(FIM 랭크 2/3).
  X410 은 RX 4채널이므로:
    · RX0 = **기준 채널**  — 직접파(TX 가시선)를 캡처 → 패시브의 '아는 신호'
    · RX1,2,3 = **감시 배열** — 표적 방향, λ/2 간격 균일선형배열(ULA) → **각도(AoA)**
  → 각도가 생기면 (거리, 도플러, 각도)로 위치가 관측가능해진다.
    **디텍션은 감시 1채널로 충분**하고, **트래킹은 배열 3채널**이 필요하다 — 그래서 순서가 있다.

■ report4 가 준 제약을 여기서 강제한다 (실측이 실제로 겪을 것들)
  · [E2] 우리 ECA 는 **무한 동적범위**라 비현실적으로 완벽하다. 실측 X410 은 **12-bit ADC** →
    직접파(수십 dB 강함)를 양자화하면 잡음이 깔린다 → **직접파 제거가 완벽하지 않다.**
    → adc_quantize() 로 그 한계를 모델에 넣는다. 이게 시뮬↔실측 간극의 첫 번째 후보다.
  · [E1] 경험적 Pfa 는 파형마다 다르다 → passive_process.pfa_nominal_for() 로 교정해 비교.
  · [E4/E5] M 이 아니라 T_CPI 를 맞춰야 공정. detection_config 가 T_CPI 를 고정한다.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", "benchmark"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                    # noqa: E402

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  USRP X410 하드웨어 — 스펙 그대로 (지어내지 않는다)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class X410:
    """USRP X410 + ZBX 하드웨어 제약. 출처: ni.com/ettus.com 공식 스펙(2024)."""
    n_tx: int = 4
    n_rx: int = 4
    max_bw_hz: float = 400e6              # 채널당 순시대역
    f_lo_hz: float = 1e6
    f_hi_hz: float = 7.2e9               # 8 GHz 까지 튜닝 가능
    adc_bits: int = 12                   # → 동적범위 ~ 6.02*12 + 1.76 = 74 dB
    max_sample_rate_hz: float = 491.52e6

    def supports(self, carrier_hz, bw_hz) -> tuple[bool, str]:
        if not (self.f_lo_hz <= carrier_hz <= 8e9):
            return False, f"반송파 {carrier_hz/1e9:.2f} GHz 가 범위(1 MHz~8 GHz) 밖"
        if bw_hz > self.max_bw_hz:
            return False, f"대역 {bw_hz/1e6:.0f} MHz > 채널 최대 {self.max_bw_hz/1e6:.0f} MHz"
        return True, "ok"

    @property
    def dynamic_range_db(self) -> float:
        return 6.0206 * self.adc_bits + 1.76


def adc_quantize(x, bits=12, full_scale=None, rng=None):
    """**ADC 양자화** — 실측 X410 의 유한 동적범위를 모델에 넣는다 (report4 [E2] 보완).

    우리 시뮬 ECA 는 float64 라 직접파를 완벽히 지운다(비현실적). 실측은 강한 직접파를
    12-bit 로 양자화하는 순간 **양자화 잡음 바닥**이 깔려 그 아래는 못 지운다.
      full_scale : ADC 풀스케일(보통 신호 피크로 AGC). None 이면 |x| 최대의 1.05 배.
    복소 I/Q 각각 균일 양자화."""
    x = np.asarray(x, complex)
    fs = float(full_scale) if full_scale else 1.05 * np.max(np.abs(np.r_[x.real, x.imag]) + 1e-30)
    step = 2 * fs / (2 ** bits)
    q = lambda v: np.clip(np.round(v / step) * step, -fs, fs - step)
    return q(x.real) + 1j * q(x.imag)


# --------------------------------------------------------------------------- #
#  실험 기하 — 안테나 배치 (실제로 벽/테이블에 놓을 좌표)
# --------------------------------------------------------------------------- #
@dataclass
class X410Scenario:
    """X410 바이스태틱 테스트베드 기하 + 채널 배분.

    좌표계는 report1~4 챔버(30x20x11 m)와 동일하게 쓰되, **안테나 배치는 X410 실험대로**.
    작은 실험실이면 chamber 를 줄여도 구조(기준+감시배열+표적)는 그대로 전이된다."""
    hw: X410 = field(default_factory=X410)
    carrier_hz: float = 3.5e9                          # 5G n78 (X410 커버)
    tx_pos: tuple = (4.0, 2.5, 8.0)                    # 송신 혼 (한쪽 벽)
    ref_pos: tuple = (4.0, 4.0, 8.0)                   # RX0: 기준 채널 (직접파 잘 보이게 TX 근처)
    surv_center: tuple = (4.0, 17.5, 6.5)             # 감시 배열 중심 (반대쪽 벽)
    surv_axis: tuple = (0.0, 1.0, 0.0)                # 배열 축 방향 (ULA)
    n_surv: int = 3                                    # 감시 배열 소자 수 (RX1,2,3)
    target: tuple = (21.0, 10.0, 5.5)                 # 드론

    def __post_init__(self):
        # λ/2 ULA 소자 좌표 (AoA 용)
        lam = C0 / self.carrier_hz
        d = lam / 2.0
        ax = np.asarray(self.surv_axis, float); ax /= np.linalg.norm(ax)
        c = np.asarray(self.surv_center, float)
        k = np.arange(self.n_surv) - (self.n_surv - 1) / 2.0
        self.surv_elems = [tuple(c + kk * d * ax) for kk in k]
        self.elem_spacing_m = d

    def geometry(self):
        """바이스태틱 기하 요약 — 기준RX 기준(직접파)과 감시배열 중심(표적경로)."""
        tx, tgt = np.asarray(self.tx_pos), np.asarray(self.target)
        sc = np.asarray(self.surv_center)
        R1 = float(np.linalg.norm(tgt - tx))            # TX→표적
        R2 = float(np.linalg.norm(sc - tgt))            # 표적→감시
        L = float(np.linalg.norm(sc - tx))              # 직접파(TX→감시)
        return dict(R1=R1, R2=R2, L=L, Rb=R1 + R2 - L,
                    tau_ns=(R1 + R2 - L) / C0 * 1e9,
                    n_surv=self.n_surv, elem_spacing_cm=self.elem_spacing_m * 100)

    def check_waveform(self, bw_hz):
        ok, msg = self.hw.supports(self.carrier_hz, bw_hz)
        return ok, msg


# --------------------------------------------------------------------------- #
#  AoA — 감시 배열이 각도를 준다 (트래킹 관측가능성의 열쇠)
# --------------------------------------------------------------------------- #
def steering_vector(scn: X410Scenario, az_deg, el_deg=0.0):
    """감시 ULA 의 조향벡터 (방위·고각 → 소자별 위상). 실측 빔포밍/MUSIC 의 기초."""
    lam = C0 / scn.carrier_hz
    k = 2 * np.pi / lam
    u = np.array([np.cos(np.radians(el_deg)) * np.cos(np.radians(az_deg)),
                  np.cos(np.radians(el_deg)) * np.sin(np.radians(az_deg)),
                  np.sin(np.radians(el_deg))])
    e = np.array(scn.surv_elems) - np.array(scn.surv_center)
    return np.exp(1j * k * (e @ u))


def aoa_resolution_deg(scn: X410Scenario):
    """배열 각도분해능 ≈ λ/(N·d·cosθ) [rad] → deg. N 소자 λ/2 ULA."""
    N = scn.n_surv
    return float(np.degrees(0.886 * 2.0 / N))          # broadside, λ/2 간격, -3dB 폭 근사


# --------------------------------------------------------------------------- #
#  디텍션 설정 — report4 의 교정을 강제한다
# --------------------------------------------------------------------------- #
def detection_config(std: str, bw_hz, T_cpi_s=20e-3, pfa_target=1e-4):
    """디텍션 파라미터 — **report4 의 세 교정을 자동 적용**한다.
      · 명목 Pfa 를 파형별로 교정(pfa_nominal_for)
      · T_CPI 고정(M 이 아니라) → 파형 간 관측시간 공정
      · 도플러 가드(zd±1) 권고

    반환: dict(pfa_nominal, T_cpi_s, doppler_guard_width, notes)."""
    from passive_process import pfa_nominal_for
    return dict(
        std=std, bw_hz=bw_hz, T_cpi_s=T_cpi_s,
        pfa_target=pfa_target,
        pfa_nominal=pfa_nominal_for(std, pfa_target),   # [E1] 파형별 교정
        doppler_guard_width=3,                          # [E2] Hann zd±1 누설 차단
        notes="T_CPI 고정(M 아님)·파형별 Pfa 교정·도플러 가드 — report4 R1/R2/R4",
    )


def summary():
    """설정 요약을 찍는다 — 실험 설계 검토용."""
    scn = X410Scenario()
    g = scn.geometry()
    print("=" * 78)
    print("USRP X410 바이스태틱 드론탐지 테스트베드 — 시뮬↔실측 매칭 설정")
    print("=" * 78)
    print(f"하드웨어: TX {scn.hw.n_tx}ch · RX {scn.hw.n_rx}ch · 대역 ≤{scn.hw.max_bw_hz/1e6:.0f} MHz · "
          f"ADC {scn.hw.adc_bits}-bit (동적범위 {scn.hw.dynamic_range_db:.0f} dB) · "
          f"{scn.hw.f_lo_hz/1e6:.0f} MHz~{scn.hw.f_hi_hz/1e9:.1f} GHz")
    print(f"\n반송파 {scn.carrier_hz/1e9:.2f} GHz (5G n78)")
    print(f"기하: 직접파 L={g['L']:.1f} m · 표적경로 R1+R2={g['R1']+g['R2']:.1f} m · "
          f"바이스태틱 Rb={g['Rb']:.1f} m (τ={g['tau_ns']:.0f} ns)")
    print(f"\n채널 배분:")
    print(f"  RX0 = 기준(직접파)  @ {tuple(round(v,1) for v in scn.ref_pos)}")
    print(f"  RX1~{scn.n_surv} = 감시 ULA {scn.n_surv}소자, λ/2={scn.elem_spacing_m*100:.1f} cm 간격 "
          f"@ {tuple(round(v,1) for v in scn.surv_center)}")
    print(f"  → AoA 각도분해능 ≈ {aoa_resolution_deg(scn):.1f}° ({scn.n_surv}소자)")
    print(f"\n후보 파형 (X410 이 송신, 대역 검사):")
    for std, bw, fc in (("wifi", 80e6, 5.2e9), ("lte", 20e6, 1.8e9), ("nr", 100e6, 3.5e9),
                        ("nr_wide", 400e6, 3.5e9)):
        ok, msg = scn.hw.supports(fc, bw)
        dr = C0 / bw    # 바이스태틱 c/B (모노 등가는 절반)
        print(f"  {std:8s} {bw/1e6:5.0f} MHz @ {fc/1e9:.1f} GHz → ΔR {dr:5.2f} m  "
              f"[{'✅' if ok else '❌ '+msg}]")
    print(f"\n디텍션 vs 트래킹:")
    print(f"  디텍션 = 감시 1채널 + CFAR (report4 검증됨) ← 먼저")
    print(f"  트래킹 = 감시 배열 {scn.n_surv}채널 → AoA → (거리·도플러·각도)로 위치 관측가능 ← 다음")


if __name__ == "__main__":
    summary()
