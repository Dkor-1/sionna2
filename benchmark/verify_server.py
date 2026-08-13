# -*- coding: utf-8 -*-
"""
verify_server.py — (benchmark) Sionna RT 검증 엔트리
====================================================
Sionna RT + GPU/OptiX 로 실행한다(py312 venv 에 Sionna RT 설치됨).
OptiX 미해결 환경에선 RT 부분이 명확한 가드와 함께 실패하도록 되어 있다(그게 정상 —
개발/sanity 는 AnalyticChannel, 여기는 RT 검증).

하는 일
  1) 환경 진단  : python, sionna/mitsuba/drjit, mitsuba variants, CUDA 가시성.
  2) RT CIR 추출: SionnaRTChannel.state() 1회 — 성공/실패(OptiX) 를 명확히 보고.
  3) 교차검증   : 같은 셀을 Analytic vs RT 로 → 기하 일치(ΔRb·Δfd≈0) + RT 클러터 확인.
                  (깨끗한 챔버면 RT ≈ Analytic = 교차검증 통과)
  4) RT 최소셀  : RT 백엔드로 SCR/Pd 측정 + RD맵 저장(outputs/figures/bench_rt_cell.png).

실행
  cd sionna2/benchmark
  CUDA_VISIBLE_DEVICES=2 /workspace/.venvs/py312/bin/python verify_server.py
  # (GPU 는 #2 사용이 sionna2 정책.) OptiX 미해결이면 3)에서 명확한 안내와 함께 멈춘다.
  #   해결: libnvoptix.so.1 경로 찾아 DRJIT_LIBOPTIX_PATH 지정,
  #        또는 관리자에게 NVIDIA_DRIVER_CAPABILITIES=all 로 컨테이너 재기동 요청.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "src"))
for _p in (_SRC, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                          # noqa: E402
from bistatic_scene import C0                               # noqa: E402
from waveforms import nr_downlink                           # noqa: E402
from link_budget import LinkBudget                          # noqa: E402
from channel import AnalyticChannel, SionnaRTChannel        # noqa: E402
from scenarios import radial                                # noqa: E402
from run_min_cell import run_cell                           # noqa: E402
from geometry import TX, RX, CENTER                         # noqa: E402


def diagnostics():
    print("=" * 64); print("1) 환경 진단"); print("=" * 64)
    import platform
    print("python :", platform.python_version(), "|", sys.executable)
    for m in ("numpy", "scipy", "mitsuba", "drjit", "sionna"):
        try:
            mod = __import__(m)
            print(f"  {m:10s} {getattr(mod, '__version__', '?')}")
        except Exception as e:
            print(f"  {m:10s} MISSING ({type(e).__name__})")
    try:
        import mitsuba as mi
        print("  mitsuba variants:", mi.variants())
    except Exception as e:
        print("  mitsuba variants: n/a —", e)
    print("  CUDA_VISIBLE_DEVICES =", os.environ.get("CUDA_VISIBLE_DEVICES", "(unset)"))


def compare_states(fc=1.843e9, drone="mavic4pro"):
    print("\n" + "=" * 64); print("2·3) RT CIR 추출 + RT↔Analytic 교차검증"); print("=" * 64)
    pos, vel = radial(TX, RX, CENTER, n=48); mid = len(pos) // 2
    ca = AnalyticChannel()
    # 자유공간 RT(챔버 스케일 기하, 벽 없음) → 클러터 없이 RT↔Analytic 깨끗한 교차검증.
    # (챔버 흡수체 클러터까지 보려면 with_chamber=True 로 — 무반사라 약하게 나온다.)
    cr = SionnaRTChannel(with_chamber=False)                # ← 서버 RT (OptiX 필요)
    sa = ca.state(TX, RX, pos[mid], vel[mid], fc, drone)
    print(f"  [Analytic ] Rb={sa.tau*C0:7.1f}m  fd={sa.fd:+7.1f}Hz  "
          f"σ={10*np.log10(sa.sigma_m2):6.1f}dBsm  clutter={len(sa.clutter)}")
    sr = cr.state(TX, RX, pos[mid], vel[mid], fc, drone)    # ← 여기서 RT 광선추적 실행
    print(f"  [Sionna RT] Rb={sr.tau*C0:7.1f}m  fd={sr.fd:+7.1f}Hz  "
          f"σ={10*np.log10(sr.sigma_m2):6.1f}dBsm  clutter={len(sr.clutter)}  "
          f"rt_echo_ratio={sr.rt_echo_ratio}")
    dR = abs(sr.tau - sa.tau) * C0; dfd = abs(sr.fd - sa.fd)
    print(f"  → 기하 일치 : ΔRb={dR:.3f} m,  Δfd={dfd:.3f} Hz  (≈0 이어야 정상)")
    if sr.clutter:
        print("  → RT 실측 클러터 (상대지연[ns], 직접파대비[dB]):")
        for dt, r in sr.clutter:
            print(f"       τ+{dt*1e9:6.0f} ns   {20*np.log10(max(r,1e-30)):+6.1f} dB")
    else:
        print("  → RT 클러터 없음(깨끗한 챔버/흡수체) → RT ≈ Analytic 교차검증 통과.")
    return cr


def run_rt_cell(cr, target_amp="po"):
    print("\n" + "=" * 64); print("4) RT 백엔드로 최소셀 실행 + RD맵"); print("=" * 64)
    lb = LinkBudget(eirp_dbm=12.0)          # 챔버 저출력 조명원(run_min_cell.EIRP_DBM 과 동일)
    pos, vel = radial(TX, RX, CENTER, n=48)
    wf = nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")   # run_min_cell 최소셀과 동일
    res = run_cell(wf, "mavic4pro", pos, vel, lb, channel=cr, target_amp=target_amp,
                   M=48, N=100)
    lt = res["link"]; st = res["state"]
    print(f"  [RT] 에코SNR={lt['snr_echo_db']:+.1f}dB  "
          f"SCR={res['scr_mean']:.1f}±{res['scr_std']:.1f}dB  Pd={res['pd']*100:.0f}%  "
          f"(backend={st.backend}, clutter={len(st.clutter)}, target_amp={target_amp})")

    import matplotlib
    matplotlib.use("Agg")
    import vizstyle
    vizstyle.use_korean()
    import matplotlib.pyplot as plt
    Rb, f_d, rd, st, lt, (ri, di), true_Rb = res["example"]
    rdb = 20 * np.log10(rd / rd.max() + 1e-9)
    fig, ax = plt.subplots(figsize=(8.2, 5.4), constrained_layout=True)
    im = ax.pcolormesh(Rb, f_d, rdb, cmap="turbo", vmin=-50, vmax=0, shading="auto")
    ax.plot(true_Rb, st.fd, "o", mfc="none", mec="w", ms=15, mew=1.6, label="참 표적")
    ax.set_xlabel("바이스태틱 거리 Rb [m]"); ax.set_ylabel("도플러 f_d [Hz]")
    ax.set_title(f"[Sionna RT] 최소셀 RD맵 · {wf.name} {wf.bw_hz/1e6:.0f}MHz / mavic4pro / radial\n"
                 f"에코SNR={lt['snr_echo_db']:+.1f}dB · SCR={res['scr_mean']:.1f}dB · "
                 f"Pd={res['pd']*100:.0f}%", fontsize=10.5)
    fig.colorbar(im, ax=ax, label="정규화 [dB]"); ax.legend(loc="upper right", fontsize=9)
    out = os.path.abspath(os.path.join(_HERE, "..", "outputs", "figures", "bench_rt_cell.png"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f"  RT RD맵 저장 → {os.path.relpath(out, os.path.join(_HERE, '..'))}")


if __name__ == "__main__":
    diagnostics()
    try:
        cr = compare_states()
        run_rt_cell(cr)
        print("\n✅ RT 검증 완료.")
    except (RuntimeError, NotImplementedError) as e:
        print("\n⚠️  RT 백엔드 실행 실패 (OptiX 미해결 등):")
        print(e)
        print("\n→ CUDA_VISIBLE_DEVICES=2 /workspace/.venvs/py312/bin/python verify_server.py 로 재실행")
        sys.exit(1)
