# -*- coding: utf-8 -*-
"""build_report2.py — report2 산출물을 **한 번에** 만든다.

report2: OFDM 파형 제작 + Sionna 기본 파형과 비교 + RCS
질문: "우리가 만든 파형이 맞는가, 그리고 이 드론들은 레이더에 얼마나 밝은가?"

  1) 게이트     — 의존하는 검증들이 실제로 통과하는지 먼저 확인한다
                  (Sionna 교차검증 · SBR 해석해 검증). 여기서 깨지면 그림을 그릴 이유가 없다.
  2) 측정 + 그림 — viz_report2.build_all()  → outputs/report2_waveform_rcs.json
  3) 노트북      — make_notebook2.py 가 그 JSON 을 읽어 report2.ipynb 를 만든다

실행:  ~/.venvs/py312/bin/python src/build_report2.py
       (GPU 는 src/gpu.py 가 여유 메모리를 보고 자동 선택한다 — 하드코딩 없음)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _hdr(s):
    print("\n" + "=" * 78 + f"\n▶ {s}\n" + "=" * 78)


def main():
    t0 = time.time()

    _hdr("게이트 1/2 — Sionna PHY 교차검증 (자작 OFDM ↔ sionna.phy.ofdm.OFDMModulator)")
    import waveforms_sionna
    waveforms_sionna.nr_table()
    print()
    rows = waveforms_sionna.crosscheck()
    bad = [r for r in rows if not r.get("ok")]
    if bad:
        raise SystemExit(f"❌ 교차검증 실패: {[r['name'] for r in bad]} — "
                         "파형이 Sionna 와 어긋난다. 그림을 그릴 이유가 없다.")
    print("\n✅ 게이트 통과 — 자작 OFDM 변조기가 Sionna 와 일치한다")

    _hdr("게이트 2/2 — SBR 커널 해석해 검증 (금속구 πr² · 평판 4πA²/λ²)")
    import rcs_sbr
    res = rcs_sbr.validate(3.5e9)
    #  평판은 λ/6 에서 |오차| < 0.5 dB 여야 한다 (구는 격자위상 지터가 있어 게이트로 안 쓴다 — §4.1)
    e = abs(res.get("plate_lam/6", 99))
    if e > 0.5:
        raise SystemExit(f"❌ SBR 평판 검증 실패: {e:.2f} dB > 0.5 dB")
    print(f"\n✅ 게이트 통과 — 평판 오차 {res['plate_lam/6']:+.2f} dB (λ/6)")

    _hdr("측정 + 그림 — §1 기준신호 · §2 자원격자 · §3 Sionna 교차검증 · §4 SBR RCS")
    import viz_report2
    viz_report2.build_all()

    _hdr("report2.ipynb 생성 (측정 JSON → 노트북. 본문 숫자는 손으로 안 적는다)")
    subprocess.run([sys.executable, os.path.join(_HERE, "make_notebook2.py")], check=True)

    print(f"\n✅ report2 완료 ({time.time() - t0:.0f}s)")
    print("   report2.ipynb")
    print("   outputs/report2_waveform_rcs.json")
    print("   outputs/figures/report2_*.png")


if __name__ == "__main__":
    main()
