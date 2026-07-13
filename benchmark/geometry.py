# -*- coding: utf-8 -*-
"""
geometry.py — (benchmark) 무반사 챔버 내부 바이스태틱 배치 (통제 기하)
======================================================================
report1~4 와 **같은 30×20×11 m 무반사 차폐시설(챔버)** 안에서 벤치마크를 돈다.
(이전 벤치마크는 실외 매크로셀 스케일 TX≈250 m 였다 → report1~4 의 챔버 테마와
 어긋났다. 여기서 챔버 스케일로 통일한다. report4 의 viz_bistatic.py 배치와 일치.)

  · 신호원(illuminator) 안테나 TX 와 패시브 수신 안테나 RX 를 챔버 양쪽 측벽에 벌려 놓고,
  · 표적 드론이 quiet zone(중앙~안쪽)을 저속(indoor, ~수 m/s) 비행한다.
  · **무반사**: 벽·천장 흡수체가 다중경로를 억제 → 클러터는 약하고 주된 방해는
    직접파(DPI). 그래서 ECA 는 사실상 '직접파 제거'가 핵심.

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

# 무반사 잔향 클러터(약함): (지연[s], 직접파대비 진폭비). 흡수체 불완전·바닥/장비 반사.
# 절대크기는 상위 하네스가 dpi_amp(직접파)로 스케일 → 여기선 '비율'만(≈ −25~−30 dB).
CH_CLUTTER_RATIO = ((8e-9, 0.05), (22e-9, 0.035), (45e-9, 0.02))

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
