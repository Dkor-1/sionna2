# -*- coding: utf-8 -*-
"""
copies_id_0903.py — el 0° 에서 «같은 경로가 몇 벌» 이고, 그 벌들이 무엇인가.

여기까지
    · el 0° 낙차 깊이가 기체마다 (N−1)/N 자리에 뭉친다 — mini5pro 2 · matrice4e 3 · mavic4pro 4
    · 그리고 |E| ÷ 가장 센 |a| 가 그 N 과 **정확히 같다**(2.000 · 3.000 · 4.000)
    · ⭐한 벌의 크기가 기체와 무관하게 거의 같다(2.2836 · 2.2983 · 2.2876 e−04)

이 스크립트
    덤프한 경로 목록에서 **가장 센 경로와 사실상 같은 항목**을 모아
      · 몇 벌인지 · 물체·정점·지연이 정말 같은지 · 벌끼리 위상이 같은지
    를 적는다. 벌이 결맞음으로 더해지는지(= N 배)까지 확인한다.

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=benchmark \\
        ~/.venvs/py312/bin/python benchmark/copies_id_0903.py --dumps <dir> <dir> ...
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "outputs", "copies_id_0903.json")


def main() -> None:
    import sys
    sys.path.insert(0, HERE)
    from elephant_id_0903 import load, amp, describe

    ap = argparse.ArgumentParser()
    ap.add_argument("--dumps", nargs="+", required=True, help="덤프 디렉터리들")
    ap.add_argument("--rel", type=float, default=1e-6, help="«같다» 로 볼 상대 오차")
    a = ap.parse_args()

    rows = []
    for d in a.dumps:
        for f in sorted(glob.glob(os.path.join(d, "pose*_el*.npz"))):
            dd = load(f)
            A = amp(dd)
            if A.size == 0:
                continue
            top = float(A.max())
            same = np.where(np.abs(A - top) / top < a.rel)[0]
            E = complex(*dd["E"])
            #: 벌들이 결맞음으로 더해지나 — 복소 진폭의 위상이 같은지 본다
            ar, ai = np.asarray(dd["a_re"]), np.asarray(dd["a_im"])
            z = ar[same] + 1j * ai[same]
            ph = np.angle(z)
            ph_spread = float(np.max(ph) - np.min(ph)) if z.size > 1 else 0.0
            tau = np.asarray(dd["tau"])[same]
            name = os.path.basename(d).replace("pd_", "").replace("pathdump", "matrice4e")
            print(f"═══ {name} · {os.path.basename(f)} ═══")
            print(f"  경로 {A.size} · |E| {abs(E):.6e} · 가장 센 |a| {top:.6e}")
            print(f"  ⭐그 값과 {a.rel:g} 안에서 같은 항목: **{same.size} 벌**")
            print(f"     |E| ÷ 한 벌 = {abs(E)/top:.4f}   ·   벌 합(결맞음) = {abs(z.sum()):.6e}")
            print(f"     지연 폭 {np.ptp(tau)*1e12:.3f} ps · 위상 폭 {np.degrees(ph_spread):.4f}°")
            print(f"     정체: {describe(dd, int(same[0]))[:96]}")
            #: 벌들이 서로 다른 물체·정점인가
            V = dd["vertices"][:, same, :] if "vertices" in dd else None
            O = dd["obj"][:, same] if "obj" in dd else None
            if V is not None:
                vspread = float(np.max(np.ptp(V[0], axis=0)))
                print(f"     첫 정점 좌표 폭 {vspread*1e3:.4f} mm · "
                      f"물체 id {sorted(set(O[0].tolist())) if O is not None else '—'}")
            rows.append(dict(dump=name, file=os.path.basename(f), n_paths=int(A.size),
                             abs_E=abs(E), top_abs_a=top, n_copies=int(same.size),
                             E_over_copy=round(abs(E) / top, 4),
                             coherent_sum=abs(complex(z.sum())),
                             tau_spread_ps=float(np.ptp(tau) * 1e12),
                             phase_spread_deg=float(np.degrees(ph_spread)),
                             vertex_spread_mm=(float(np.max(np.ptp(V[0], axis=0)) * 1e3)
                                               if V is not None else None)))
            print()

    json.dump({"_meta": {
        "generator": "benchmark/copies_id_0903.py",
        "question_ko": "el 0° 에서 같은 경로가 몇 벌이고 그 벌들이 정말 같은 것인가",
        "same_rule_ko": f"가장 센 |a| 와 상대오차 {a.rel:g} 안",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
