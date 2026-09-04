# -*- coding: utf-8 -*-
"""
el0_copies_0903.py — 0° 낙차의 «같은 줄이 적히는 횟수 N» 이 기체마다 다른가.

여기까지 갈린 것
    matrice4e · el 0° 에서 낙차 깊이가 **정확히 2/3** 이고, 경로 목록을 열어 보니
    진폭·지연·정점이 **똑같은 «정반사 → 카메라»** 항목이 **셋**이었다.
    3 × 2.298327e−04 = |E| 이므로, 셋 중 하나가 빠지면 2/3 다(**추론** — 하나가 빠진
    목록 자체는 미관측이다. 아래 ⚠ 참조).
⚠⚠**낙차를 잰 팔과 경로 목록을 덤프한 팔이 서로 다르다**(2026-09-04 확인). 위 «자세 47» 의
   목록(|E| 6.896568e−04 · 같은 줄 3 번)은 **정본 메쉬 팔**
   (`sionna_p4000000000_r15_n8192_mfixbatteryi5_blperairframe_d1_el+0`)의 것이고, 그 팔에서
   자세 47 은 **낙차가 아니다**(|E|/중앙 = 1.0000 — 세 줄이 다 있다). 2/3 로 떨어지는 것은
   **메쉬 보정 안 한 팔**(`sionna_p4000000000_r15_n8192_d1_el+0`, |E| 4.597513e−04 · 비
   0.6667)에서다. ⇒ 「깊이가 정확히 2/3」과 「같은 줄이 3 번」은 **다른 팔에서 나온 두
   사실**이고, «셋 중 하나가 빠진 목록» 은 **아직 한 번도 관측된 적이 없다**(추론이다).
   ⚠단, 「어떤 자세에서 사본 하나가 빠진다」는 결론 자체는 자세 32,768 개를 직접 세어
   따로 받쳐 뒀다(CLAUDE.md) — 여기서 고치는 것은 **이 스크립트의 근거 서술**이다.


⭐이 스크립트가 묻는 것
    기체를 바꾸면 그 **같은 줄이 적히는 횟수 N** 이 달라지나. 낙차 깊이가 (N−1)/N 자리에
    **좁게 뭉치는 칸에 한해** 깊이만으로 N 을 읽어 본다 — 솔버를 안 돌리고 디스크로 답한다.
    ⚠이 읽기가 서는 것은 **깊이 산포가 작은, 회절 끈 PathSolver 팔**뿐이다. 회절 켠 팔은
    0.764·0.571 처럼 정수 자리가 아니고, **우리 커널 팔에는 쓰지 않는다.**

무엇을 재나
    기체·팔마다 el 0° 기록에서
      · 낙차 깊이 \\|E\\|/중앙 의 **뭉치는 자리**
      · 그 자리에서 읽은 N = 1 / (1 − 깊이)
      · N 이 정수에 얼마나 가까운지 (가까우면 «적히는 횟수» 읽기가 선다)

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" ~/.venvs/py312/bin/python benchmark/el0_copies_0903.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "el0_copies_0903.json")
THR = 0.9                       # 덱 그림의 규칙


def airframe(arm: str) -> str:
    for k in ("mavic4pro", "mini5pro", "s1000plus", "matrice4e"):
        if k in arm:
            return k
    return "matrice4e(기본)"      # 꼬리표가 없으면 기본 기체다


def main() -> None:
    #: el 0 샤드를 팔별로 모은다
    by = collections.defaultdict(list)
    for f in glob.glob(os.path.join(SHD, "*_el+0_*.npz")):
        m = re.match(r"^(.+)_el\+0_\d+\.npz$", os.path.basename(f))
        if m:
            by[m.group(1)].append(f)

    rows = []
    for arm, fs in sorted(by.items()):
        i, e = [], []
        for f in sorted(fs):
            try:
                z = np.load(f)
            except Exception:
                continue
            i.append(z["idx"]); e.append(z["E"])
        if not i:
            continue
        i = np.concatenate(i); e = np.concatenate(e)
        o = np.argsort(i); a = np.abs(e[o])
        if a.size < 1000:
            continue
        med = float(np.median(a))
        if med <= 0:
            continue
        r = a / med
        d = r[r < THR]
        if d.size < 5:
            continue
        #: 깊이가 한 값에 뭉치나 — 표준편차가 작아야 «적히는 횟수» 읽기가 선다
        q1, q3 = np.percentile(d, [25, 75])
        core = d[(d >= q1 - 1e-3) & (d <= q3 + 1e-3)]
        depth = float(np.median(core))
        N = 1.0 / (1.0 - depth) if depth < 1 else float("inf")
        rows.append(dict(arm=arm, airframe=airframe(arm), n_poses=int(a.size),
                         n_drop=int(d.size), frac=round(100 * d.size / a.size, 2),
                         depth_median=round(depth, 5),
                         depth_iqr=round(float(q3 - q1), 5),
                         N_read=round(N, 3), N_round=int(round(N)),
                         N_gap=round(abs(N - round(N)), 4)))

    rows.sort(key=lambda x: (x["airframe"], -x["n_drop"]))
    print(f"⭐문턱 |E|/중앙 < {THR} (덱 그림 규칙) · el 0° 기록 {len(rows)} 팔\n")
    print(f"  {'기체':16s} {'낙차%':>6s} {'깊이(중앙)':>10s} {'IQR':>8s} "
          f"{'N=1/(1−깊이)':>12s} {'정수와 차':>9s}  팔")
    for x in rows:
        #: ⚠산포를 안 보면 «N 이 정수에 가깝다» 만으로 별이 붙는다 — 깊이가 흩어진
        #  칸(예: 우리 커널 팔 iqr 0.354)도 통과했다. 뭉침을 함께 요구한다(2026-09-04).
        flag = "⭐" if (x["N_gap"] < 0.05 and x["depth_iqr"] < 1e-4) else "  "
        print(f"{flag}{x['airframe']:16s} {x['frac']:6.2f} {x['depth_median']:10.5f} "
              f"{x['depth_iqr']:8.5f} {x['N_read']:12.3f} {x['N_gap']:9.4f}  {x['arm'][:52]}")

    print("\n═══ 기체별 모음 (정수에 가까운 것만) ═══")
    g = collections.defaultdict(list)
    for x in rows:
        if x["N_gap"] < 0.05:
            g[x["airframe"]].append(x)
    for af, xs in sorted(g.items()):
        Ns = sorted({x["N_round"] for x in xs})
        dep = [x["depth_median"] for x in xs]
        print(f"  {af:16s} 팔 {len(xs):2d} · N = {Ns} · "
              f"깊이 {min(dep):.4f}~{max(dep):.4f}")

    json.dump({"_meta": {
        "generator": "benchmark/el0_copies_0903.py",
        "question_ko": "0° 낙차의 «같은 줄이 적히는 횟수 N» 이 기체마다 다른가",
        "how_ko": "낙차 깊이 = (N−1)/N 이므로 N = 1/(1−깊이). 깊이가 한 값에 뭉칠 때만 읽는다.",
        "threshold_ko": f"|E| / 중앙값 < {THR}",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
