# -*- coding: utf-8 -*-
"""
geometry.py — (benchmark) **semi-anechoic** 챔버 내부 바이스태틱 배치 (통제 기하)
======================================================================
report1~4 와 **같은 30×20×11 m 차폐시설(챔버)** 안에서 벤치마크를 돈다.
(이전 벤치마크는 실외 매크로셀 스케일 TX≈250 m 였다 → report1~4 의 챔버 테마와
 어긋났다. 여기서 챔버 스케일로 통일한다. report4 의 viz_bistatic.py 배치와 일치.)

  · 신호원(illuminator) 안테나 TX 와 패시브 수신 안테나 RX 를 챔버 양쪽 측벽에 벌려 놓고,
  · 표적 드론이 quiet zone(중앙~안쪽)을 저속(indoor, ~수 m/s) 비행한다.
  · **흡수체는 벽 4면 + 천장에만** 있고 **바닥은 반사성 콘크리트**다 → anechoic 이 아니라
    **semi-anechoic**. 방 안에서 유일하게 강한 반사면이 바닥이다(chamber.py 참조).

■ 정정 (2026-07-14) — "무반사라 클러터가 약하다"는 전제는 **틀렸다**
  예전 문구: "벽·천장 흡수체가 다중경로를 억제 → 클러터는 약하고 주된 방해는 직접파(DPI)".
  실제로는 **바닥 반사가 남아 있고, Sionna RT 가 이미 그걸 보고 있었다**:
    · RT 실측 챔버 클러터(report5 §D): 최강 −9.8 dB, 그리고 **19.3 ns 에서 −14.7 dB**.
    · 같은 값을 기하+프레넬로 독립 유도: TX→바닥→RX 는 입사각 46.0°, 여분지연 **19.3 ns**,
      V-편파(=입사면 평행, TM) 콘크리트(εr=5.24) 반사계수 |Γ|=0.255, 확산손실 −2.8 dB
      → 직접파 대비 **−14.7 dB**. RT 와 지연·진폭이 0.1 dB 내로 일치한다.
    · 아래 CH_CLUTTER_RATIO 의 가정(−26/−29/−34 dB)은 그보다 **11~16 dB 약했다.**

■ 그런데 왜 아무 수치도 안 틀렸나 — **정적 클러터는 이 하네스에서 죽은 파라미터**이기 때문
  passive_process.make_cpi 의 clutter 는 **도플러가 없는**, 지연된 기준신호의 선형결합이다.
  ECA 의 기저가 정확히 그 '지연된 기준신호들'이라, ECA 의 사영이 **진폭과 무관하게 정확히
  0 으로 지운다**. 측정(클러터 진폭 스윕):
      클러터 없음 → SCR 34.810974834437 dB
      −26 dB(기본) → 34.810974834434
      −6 dB        → 34.810974834413
      **+14 dB(직접파보다 강함!)** → 34.810974834204   ← Pd 는 전부 1.00
  즉 CH_CLUTTER_RATIO 를 어떻게 고쳐도 report4/report5 의 Pd·SCR 은 **한 자리도 안 바뀐다**.
  → report5 §D 의 "RT 와 Analytic 이 일치하므로 Analytic 으로 스윕해도 된다"는 결론은
    **클러터에 관한 한 공허하다**(어떤 클러터 모델을 넣어도 일치할 수밖에 없었다).
    기하·직접파·표적 경로에 대한 교차검증으로서는 여전히 유효하다.
  ⚠ 실제 ECA 는 이렇게 완벽하지 않다(유한 동적범위·클러터 도플러퍼짐·양자화). 그 한계는
    아직 모델에 없다 — 정적 클러터가 **정말로** 무해하다는 뜻이 아니라, **이 모델이 그걸
    검증할 능력이 없다**는 뜻이다.

■ 진짜 위협은 clutter 가 아니라 **표적 경유 바닥 유령(ghost)** 이다 → floor_ghost() 참조
  TX→표적→바닥→RX 경로는 표적과 함께 움직이므로 **도플러가 실린다** → ECA 의 영공간 밖 →
  **지워지지 않고 가짜 표적으로 남는다.** 이건 모델에 아예 없었다.

■ 챔버 스케일이 만드는 핵심 제약 — 거리분해능 = **위치정보**
  챔버 Rb 는 수~수십 m 로 작다. 거리분해능 ΔRb=c/B 와 챔버 크기의 비가 곧
  '측정된 (Rb, f_d) 가 위치정보를 주는가'를 결정한다:
    5G 100MHz  → ΔRb≈3.1 m,  샘플간격 c/fs≈2.4 m   → 표적 Rb≈22 m 를 또렷이 분리
    WiFi 80MHz → ΔRb≈4.0 m,  c/fs≈3.75 m           → 분리 가능
    LTE 20MHz  → ΔRb≈16.7 m, c/fs≈9.8 m            → 거리빈 6개 — 위치가 거칢
    LTE 10MHz  → ΔRb≈33.3 m, c/fs≈19.5 m           → 거리빈 2~3개 — 등Rb 타원 두께가
                                                      방 전체 수준 → 위치정보 사실상 없음
  ※ 측정 결과(run_matrix B): '탐지' 자체는 정적 DPI 가 도플러축에서 분리되므로 협대역도
    성공하며, kTB 잡음이 작아 SCR 은 오히려 협대역이 높다. 대역폭이 가르는 것은
    탐지가 아니라 **위치정보(거리축)와 다중표적 분리**다 — report5 의 핵심 결론.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# --- 무반사 챔버(30×20×11 m) 내부 바이스태틱 배치 -------------------------------------
#     단일 출처 = src/bistatic_scene.py (report4 와 동일 배치를 그대로 import — 드리프트 방지)
from bistatic_scene import CHAMBER, TX, RX, TGT as CENTER  # noqa: E402

C0 = 299792458.0

# indoor 통제 모션 파라미터(전 신호·드론 공통) — 챔버 안에 들어오도록 저속·짧은 궤적
SPEED = 3.0                        # 표적 속도 [m/s] (실내 저속)
SPAN = 9.0                         # 궤적 길이 [m] (±4.5 m — quiet zone 안)

# 정적 잔향 클러터: (지연[s], 직접파대비 진폭비). 절대크기는 상위 하네스가 dpi_amp 로 스케일.
#
# ⚠ 이 값은 **의도적으로 그대로 둔다** — 위 docstring 참조. ECA 가 정적 클러터를 진폭과
#   무관하게 정확히 소거하므로 이 숫자는 어떤 결과에도 영향을 주지 않는다(죽은 파라미터).
#   RT 실측(−9.8 … −20.1 dB)에 맞춰 '고치면' 물리적으로는 더 정직해지지만 **수치는 하나도
#   안 바뀌고**, 대신 "우리가 클러터를 제대로 모델링했다"는 잘못된 인상만 준다.
#   정직한 모델링은 (a) ECA 에 유한 동적범위를 넣거나 (b) floor_ghost() 를 켜는 것이다.
CH_CLUTTER_RATIO = ((8e-9, 0.05), (22e-9, 0.035), (45e-9, 0.02))

# 콘크리트 바닥 (ITU-R P.2040 concrete @ 3.5 GHz) — materials.make_material 와 같은 재질
FLOOR_EPS_R = 5.24
FLOOR_SIGMA = 0.1231                 # S/m  (= 0.0462 · f_GHz^0.7822, f=3.5)


def _fresnel_floor(theta_i, fc, pol="V"):
    """수평 콘크리트 바닥의 프레넬 반사계수 |Γ|. theta_i = 바닥 법선(z)에서 잰 입사각[rad].
    pol='V' (Sionna 시나리오의 안테나 편파) → E 가 **입사면 안**에 있으므로 평행/TM 성분."""
    eps_c = FLOOR_EPS_R - 1j * FLOOR_SIGMA / (2 * np.pi * fc * 8.8541878128e-12)
    ct = np.cos(theta_i)
    root = np.sqrt(eps_c - np.sin(theta_i) ** 2)
    g_tm = (eps_c * ct - root) / (eps_c * ct + root)      # 평행(TM) — V 편파
    g_te = (ct - root) / (ct + root)                      # 수직(TE)
    return float(abs(g_tm if pol.upper() == "V" else g_te))


def floor_ghost(tx, rx, tgt, vel, fc, pol="V"):
    """**표적 경유 바닥 유령**: TX → 표적 → 바닥 → RX 경로를 거울상(image)으로 유도한다.

    왜 중요한가: 이 경로는 표적을 거치므로 **표적과 함께 도플러가 실린다**. 정적 클러터와
    달리 ECA 의 영공간 밖이라 **지워지지 않고**, RD 맵에 진짜 표적과 다른 (Rb, f_d) 셀의
    **가짜 검출**로 나타난다. 대역폭이 넓을수록(=거리분해능이 좋을수록) 진짜와 **더 잘
    분리되어** 별개 표적으로 보인다 — 광대역의 장점이 그대로 오검출로 되돌아온다.

    반환 dict:
      tau       : 직접파 기준 상대지연 [s]      (RD 맵의 Rb = tau·c)
      fd        : 유령의 바이스태틱 도플러 [Hz] (진짜 표적과 다르다)
      amp_ratio : **진짜 표적 에코 대비** 전압 진폭비 (|Γ| · R2/R2f)
      rb_m, theta_i_deg, R2f : 진단용
    표적 RCS 는 진짜 경로와 같다고 본다(같은 표적, 시선각만 약간 다름) — 1차 근사."""
    tx, rx, tgt, vel = (np.asarray(v, float) for v in (tx, rx, tgt, vel))
    rx_img = rx.copy(); rx_img[2] = -rx_img[2]             # 바닥(z=0)에 비친 RX 의 거울상

    L = np.linalg.norm(rx - tx)                            # 직접파
    R1 = np.linalg.norm(tgt - tx)                          # TX → 표적
    R2 = np.linalg.norm(rx - tgt)                          # 표적 → RX (직접)
    R2f = np.linalg.norm(rx_img - tgt)                     # 표적 → 바닥 → RX  (거울상 = 펴진 직선)

    d = rx_img - tgt                                       # 바닥 반사점에서의 입사 기하
    theta_i = np.arctan2(np.linalg.norm(d[:2]), abs(d[2]))
    gamma = _fresnel_floor(theta_i, fc, pol)

    # 도플러 부호규약은 bistatic_scene.bistatic_params 와 동일:
    #   û1, û2 는 **표적에서 TX/RX 를 향하는** 단위벡터, f_d = v·(û1+û2)/λ  (멀어지면 <0).
    #   유령은 RX 자리에 거울상 RX' 를 넣으면 그대로 성립한다.
    lam = C0 / fc
    u1 = (tx - tgt) / max(R1, 1e-9)                        # 표적 → TX
    u2f = (rx_img - tgt) / max(R2f, 1e-9)                  # 표적 → RX'(거울상)
    fd = float(vel @ (u1 + u2f)) / lam

    return dict(tau=float((R1 + R2f - L) / C0), fd=fd,
                amp_ratio=float(gamma * (R2 / R2f)),
                rb_m=float(R1 + R2f - L), theta_i_deg=float(np.degrees(theta_i)),
                R2f=float(R2f), gamma=float(gamma))

# RD 맵 거리창 — 전 파형 공통(축 비교 가능). 챔버라 수십 m면 충분.
RB_WINDOW_M = 60.0


def chamber_window(wf, rb_window_m=RB_WINDOW_M):
    """파형 → (n_range, n_taps). 챔버 Rb 창을 파형 샘플간격으로 환산.
      n_range : RD 거리축 빈 수 = rb_window / (c/fs)
      n_taps  : ECA 제거 탭 수(직접파+근접 클러터 창). 거리창+여유, 상한 96.
    LTE 처럼 c/fs 가 크면 n_range 가 아주 작아진다(=거리 빈이 거의 없음 → 챔버서 불리)."""
    dr = C0 / wf.fs_hz                                  # 샘플당 거리 [m]
    Lf = len(wf.ref)
    n_range = int(max(2, min(Lf, rb_window_m / dr)))
    n_taps = int(min(n_range + 8, 96))
    return n_range, n_taps


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    from bistatic_scene import bistatic_params
    from waveforms import wifi_80211ac, lte_downlink, nr_downlink
    L = np.linalg.norm(np.array(TX) - np.array(RX))
    print(f"챔버 {CHAMBER}  TX={TX} RX={RX}  베이스라인 L={L:.1f}m  quiet-zone 중심={CENTER}")
    wfs = [("WiFi80", wifi_80211ac(bw_hz=80e6, carrier_hz=5.21e9)),
           ("LTE20", lte_downlink(bw_hz=20e6, carrier_hz=1.843e9)),
           ("LTE10", lte_downlink(bw_hz=10e6, carrier_hz=1.843e9)),
           ("5G100", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9))]
    for nm, wf in wfs:
        p = bistatic_params(TX, RX, CENTER, (-SPEED, 0.6 * SPEED, 0.2 * SPEED), wf.carrier_hz)
        n_range, n_taps = chamber_window(wf)
        print(f"  {nm:7s} ΔRb=c/B={C0/wf.bw_hz:5.1f}m  c/fs={C0/wf.fs_hz:5.2f}m  "
              f"Rb={p['Rb']:5.1f}m(={p['Rb']/(C0/wf.fs_hz):.1f}셀)  fd={p['fd']:+6.1f}Hz  "
              f"n_range={n_range:3d} n_taps={n_taps:3d}")
