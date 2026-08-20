# -*- coding: utf-8 -*-
"""
coverage_verify_0820.py — 최적화를 **생산이 실제로 도는 조합 전부**에서 검증한다
================================================================================

왜 필요한가 — 내 앞 검증의 결함
--------------------------------
`verify_optimization.py` 로 통과를 받았지만 **조합 하나만** 봤다:
  앙각 −30° · 팔 R1D0E0F1 · matrice4e · 자세 512.
그런데 생산은 앙각 4 점 × 팔 4 종 × 기체 4 종 × 자세 4,096 을 돈다.

⛔이것은 내가 개선 커널(test.tar)을 비판했던 **바로 그 결함**이다 —
  «`k_scan.py` 가 자세 32 개만 봐서 0.1 % 꼬리를 놓쳤고, 512 자세로 재니 180~500 배 큰
  오차가 나왔다». 나도 512 를 봤고 생산은 4,096 이다.

특히 **회절 팔(R0D1E1F1 · R1D1E1F1)을 한 번도 안 봤다.** 큐의 62 % 가 그 팔인데,
회절을 켜면 경로가 수천 개로 늘어 부동소수점 합의 순서 민감도가 훨씬 커진다.

무엇을 하나
-----------
칸마다 **옛 길 두 판 + 새 길 한 판**을 돌린다.
  · 옛↔옛  = 그 칸의 **잡음 바닥** (PathSolver 는 같은 코드로도 마지막 비트가 다르다)
  · 옛↔새  = 본 시험
판정은 **하류 잣대**(빗살 대비·리듬 몫·AC)로 한다 — σ 가 아니라 우리가 쓰는 숫자로.

⛔GPU 를 조금만 쓴다(워커 1~2). 산출: outputs/coverage_verify_0820.json
실행: python benchmark/coverage_verify_0820.py [--quick]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(HERE), "src")
for _q in (_SRC, HERE):
    if _q not in sys.path:
        sys.path.insert(0, _q)
# ⭐**자기 자신도 스레드를 못 박는다** — numpy(BLAS)만으로 64 개가 뜬다(실측 127 개였다).
try:
    from thread_guard import apply as _tg
    _tg(2, verbose=False)
except Exception:                                              # noqa: BLE001
    pass
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

PY = "/workspace/.venvs/py312/bin/python"
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "coverage_verify_0820.json")
TMP = "/tmp/cov0820"

#: ⭐생산이 실제로 도는 네 팔 — 회절 팔 둘이 큐의 62 % 다
ARMS = ["R0D0E0F1", "R1D0E0F1", "R0D1E1F1", "R1D1E1F1"]
ELS = [0, -30, -60, -90]
#: 판정선 — 판정 막대 2.68 dB 의 1/100
TOL = 0.0268


def env(gpu: str) -> dict:
    # ⚠환경변수만으로는 Dr.Jit 이 안 걸린다(없는 이름이다). 워커 본체의 thread_guard 가
    #   실제로 걸어 준다 — 여기 env 는 numpy/BLAS 용이다.
    t = "2"
    return dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, PYTHONPATH="src:benchmark",
                DRJIT_LIBOPTIX_PATH="/workspace/.venvs/optix/libnvoptix.so.1",
                LD_LIBRARY_PATH="/workspace/.venvs/optix:" + os.environ.get("LD_LIBRARY_PATH", ""),
                OMP_NUM_THREADS=t, MKL_NUM_THREADS=t, OPENBLAS_NUM_THREADS=t,
                NUMEXPR_NUM_THREADS=t, VECLIB_MAXIMUM_THREADS=t,
                DRJIT_NUM_THREADS=t, MI_NUM_THREADS=t, OMP_WAIT_POLICY="PASSIVE")


def run_cell(arm, el, drone, npose, spp, extra, tag, gpu):
    """한 칸을 돌려 샤드를 /tmp 로 옮긴다. ⭐자세 수를 칸마다 달리해 이름 충돌을 막는다."""
    args = ["--engine", "sionna", "--spp", str(spp), "--sw", arm,
            "--max-depth", "2", "--range-m", "15", "--n-poses", str(npose),
            f"--els={el}", "--shard", "0", "--nshards", "1", "--overwrite"]
    if drone != "matrice4e":
        args += ["--drone", drone]
    args += extra
    r = subprocess.run([PY, os.path.join("benchmark", "elevation_sweep_md.py")] + args,
                       cwd=ROOT, env=env(gpu), stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE)
    got = sorted(glob.glob(f"{SHD}/*_n{npose}_*.npz"))
    if not got:
        return None, (r.stderr or b"")[-300:].decode("utf-8", "replace")
    dst = os.path.join(TMP, f"{tag}.npz")
    shutil.move(got[0], dst)
    for g in glob.glob(f"{SHD}/*_n{npose}_*.npz"):
        os.remove(g)
    return dst, None


def metrics(path, el):
    import build_md_atlas as A
    E = np.load(path)["E"]
    ft = 1101.6 / np.cos(np.radians(-30.0)) * np.cos(np.radians(el))
    ffl = 126.66666666666667

    def _f(v):
        if v is None:
            return None
        return float(v[0]) if isinstance(v, (tuple, list)) else float(v)
    return dict(ac_db=float(10 * np.log10((np.abs(E - E.mean()) ** 2).mean())),
                rhythm_pct=_f(A.rhythm_share(E, ffl, ft)),
                comb_db=_f(A.comb_contrast_db(E, ffl, ft))), E


def dmet(ma, mb):
    return {k: (None if (ma[k] is None or mb[k] is None) else abs(mb[k] - ma[k]))
            for k in ma}


def _cleanup_children():
    """⭐끝날 때 **자기 자식을 반드시 거둔다** — 고아를 남기지 않는다.

    이 도구는 워커를 subprocess.run 으로만 띄우므로 정상 종료면 자식이 없다.
    다만 신호로 죽을 때를 대비해 프로세스 그룹째 정리한다(랩 서버 사고 재발 방지).
    """
    import signal as _sg
    try:
        os.killpg(os.getpgid(0), _sg.SIGTERM)
    except Exception:                                          # noqa: BLE001
        pass


def main():
    import signal as _sg

    def _bye(sig, frm):                                        # noqa: ARG001
        print(f"\n  신호 {sig} — 자식 정리 후 종료", flush=True)
        _cleanup_children()
        raise SystemExit(130)
    for _s in (_sg.SIGTERM, _sg.SIGINT):
        try:
            _sg.signal(_s, _bye)
        except Exception:                                      # noqa: BLE001
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="자세 수를 줄여 빨리 훑는다")
    ap.add_argument("--drone", default="matrice4e")
    ap.add_argument("--gpu", default="2")
    ap.add_argument("--spp", type=int, default=250_000_000)
    a = ap.parse_args()
    npose_base = 512 if a.quick else 2048
    os.makedirs(TMP, exist_ok=True)

    rows, t0 = [], time.time()
    print(f"  기체 {a.drone} · 광선 {a.spp:,} · 자세 {npose_base} · GPU {a.gpu}")
    print(f"  {'팔':10s}{'앙각':>5s}{'경로':>7s}{'잡음바닥':>11s}{'옛↔새':>11s}"
          f"{'빗살차':>10s}{'리듬차':>10s}{'AC차':>10s}  판정")
    k = 0
    for arm in ARMS:
        for el in ELS:
            k += 1
            n = npose_base + k            # 칸마다 다른 자세 수 → 파일 이름이 안 겹친다
            pa, e1 = run_cell(arm, el, a.drone, n, a.spp, [], f"a{k}", a.gpu)
            pb, e2 = run_cell(arm, el, a.drone, n, a.spp, [], f"b{k}", a.gpu)
            pc, e3 = run_cell(arm, el, a.drone, n, a.spp, ["--inmem"], f"c{k}", a.gpu)
            if not (pa and pb and pc):
                rows.append(dict(arm=arm, el=el, error=(e1 or e2 or e3)))
                print(f"  {arm:10s}{el:5d}  ⛔ 실패 {(e1 or e2 or e3)[:60]}")
                continue
            ma, Ea = metrics(pa, el)
            mb, _ = metrics(pb, el)
            mc, Ec = metrics(pc, el)
            floor = dmet(ma, mb)
            test = dmet(ma, mc)
            relf = float((np.abs(np.load(pb)["E"] - Ea) / np.maximum(np.abs(Ea), 1e-300)).max())
            relt = float((np.abs(Ec - Ea) / np.maximum(np.abs(Ea), 1e-300)).max())
            npth = int(np.load(pa)["npaths"].max())
            ok = all((test[x] is None) or (test[x] <= max(TOL, (floor[x] or 0.0) * 3))
                     for x in test) and relt <= max(relf, 1e-16) * 3
            rows.append(dict(arm=arm, el=el, n_poses=n, max_paths=npth,
                             floor_rel=relf, test_rel=relt,
                             floor_metric=floor, test_metric=test, ok=bool(ok)))
            g = lambda d, x: ("—" if d[x] is None else f"{d[x]:.6f}")   # noqa: E731
            print(f"  {arm:10s}{el:5d}{npth:7d}{relf:11.2e}{relt:11.2e}"
                  f"{g(test,'comb_db'):>10s}{g(test,'rhythm_pct'):>10s}{g(test,'ac_db'):>10s}"
                  f"  {'✅' if ok else '⛔'}")
            for p in (pa, pb, pc):
                os.remove(p)

    bad = [r for r in rows if not r.get("ok") and "error" not in r]
    err = [r for r in rows if "error" in r]
    doc = {"_meta": {
        "generator": "benchmark/coverage_verify_0820.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "최적화(--inmem)를 생산이 도는 팔·앙각 전부에서 검증 — 하류 잣대로 판정",
        "drone": a.drone, "spp": a.spp, "n_poses": npose_base,
        "tol_ko": f"잣대 {TOL} dB (판정 막대 2.68 의 1/100) 또는 그 칸의 잡음 바닥×3",
        "design_ko": "칸마다 옛×2(잡음 바닥) + 새×1(본 시험). σ 가 아니라 하류 잣대로 판정",
        "elapsed_s": round(time.time() - t0, 1)},
        "cells": rows,
        "verdict": dict(n_cells=len(rows), n_fail=len(bad), n_error=len(err),
                        pass_=bool(not bad and not err))}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\n  칸 {len(rows)} · 실패 {len(bad)} · 오류 {len(err)}")
    print(f"  ⭐{'✅ 전부 통과' if not bad and not err else '⛔ 실패 있음 — 도입 보류'}")
    print(f"  saved {OUT}")


if __name__ == "__main__":
    main()
