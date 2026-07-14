# -*- coding: utf-8 -*-
"""build_report7.py — report7 ("Sionna RT 로 본 챔버 패시브 레이더") 산출물 생성.

**GPU 필요** — report7 은 거의 전부 Sionna 다:
  씬·안테나·경로·라디오맵·드론·비행 = Sionna RT 렌더러 / 감시신호 = Sionna PHY /
  표적 σ = SBR / 절대전력 = link_budget.  (ECA·CAF·CFAR 만 passive_process.)

단계
  1) benchmark/rt_pipeline.py   — §3 실측 (RT 수렴/편향, S 스윕, 재질, 환경) → outputs/report7_rt.json
  2) src/viz_report7.py         — Sionna 렌더 + 그림 7장 + 비행 GIF
  3) src/make_notebook7.py      — report7.ipynb (수치는 1) 의 JSON 에서 읽어 주입)

실행:  python src/build_report7.py              (전체, ~4분)
       python src/build_report7.py --no-gif     (비행 GIF 생략)
       python src/build_report7.py --no-render  (렌더 재사용 — 그림 문구만 고칠 때)
"""
import argparse
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_BENCH = os.path.join(_ROOT, "benchmark")
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="Sionna 렌더 재사용")
    ap.add_argument("--no-rt", action="store_true", help="§3 실측 재사용(report7_rt.json)")
    a = ap.parse_args()
    t0 = time.time()

    RT_JSON = os.path.join(_ROOT, "outputs", "report7_rt.json")

    print("=" * 72, "\n▶ 1) §3 실측 — RT 를 표적에 겨눠 본다 (benchmark/rt_pipeline.py)\n", "=" * 72)
    if a.no_rt and os.path.exists(RT_JSON):
        print("  (기존 outputs/report7_rt.json 재사용)")
    else:
        subprocess.run([sys.executable, os.path.join(_BENCH, "rt_pipeline.py")], check=True)

    print("\n" + "=" * 72, "\n▶ 2) Sionna 렌더 + 그림\n", "=" * 72)
    import viz_report7 as V
    if not a.no_render:
        V.render_all()
    V.fig_pipeline()
    V.fig_chamber()
    V.fig_paths()
    V.fig_radiomap()
    V.fig_drones()
    V.fig_rt_limit()
    V.fig_benchmark()
    if not a.no_gif:
        V.gif_flight(reuse=a.no_render)

    print("\n" + "=" * 72, "\n▶ 3) report7.ipynb 생성\n", "=" * 72)
    subprocess.run([sys.executable, os.path.join(_HERE, "make_notebook7.py")], check=True)

    print(f"\n✅ report7 완료 ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
