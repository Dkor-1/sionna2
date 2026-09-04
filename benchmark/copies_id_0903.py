# -*- coding: utf-8 -*-
"""
copies_id_0903.py — el 0° 에서 «같은 줄이 몇 번 적히나» 이고, 그 줄들이 무엇인가.

여기까지
    · el 0° 낙차 깊이가 기체마다 (N−1)/N 자리에 뭉친다 — mini5pro 2 · matrice4e 3 · mavic4pro 4
    · 그리고 |E| ÷ 가장 센 |a| 가 그 N 과 **정확히 같다**(2.000 · 3.000 · 4.000)
    · ⭐한 줄의 세기가 기체와 무관하게 거의 같다(2.2836 · 2.2983 · 2.2876 e−04)

⚠⚠**낙차를 잰 팔과 경로 목록을 덤프한 팔이 서로 다르다**(2026-09-04 확인). 위 «자세 47» 의
   목록(|E| 6.896568e−04 · 같은 줄 3 번)은 **정본 메쉬 팔**
   (`sionna_p4000000000_r15_n8192_mfixbatteryi5_blperairframe_d1_el+0`)의 것이고, 그 팔에서
   자세 47 은 **낙차가 아니다**(|E|/중앙 = 1.0000 — 세 줄이 다 있다). 2/3 로 떨어지는 것은
   **메쉬 보정 안 한 팔**(`sionna_p4000000000_r15_n8192_d1_el+0`, |E| 4.597513e−04 · 비
   0.6667)에서다. ⇒ 「깊이가 정확히 2/3」과 「같은 줄이 3 번」은 **다른 팔에서 나온 두
   사실**이고, «셋 중 하나가 빠진 목록» 은 **아직 한 번도 관측된 적이 없다**(추론이다).
   ⚠단, 「어떤 자세에서 사본 하나가 빠진다」는 결론 자체는 자세 32,768 개를 직접 세어
   따로 받쳐 뒀다(CLAUDE.md) — 여기서 고치는 것은 **이 스크립트의 근거 서술**이다.


이 스크립트
    덤프한 경로 목록에서 **가장 센 경로와 사실상 같은 항목**을 모아
      · 몇 번 적히는지 · 물체·정점·지연이 정말 같은지 · 그 줄끼리 위상이 같은지
    를 적는다. 그 줄들이 결맞음으로 더해지는지(= N 배)까지 확인한다.

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
            #: 그 줄들이 결맞음으로 더해지나 — 복소 진폭의 위상이 같은지 본다
            ar, ai = np.asarray(dd["a_re"]), np.asarray(dd["a_im"])
            z = ar[same] + 1j * ai[same]
            ph = np.angle(z)
            ph_spread = float(np.max(ph) - np.min(ph)) if z.size > 1 else 0.0
            tau = np.asarray(dd["tau"])[same]
            name = os.path.basename(d).replace("pd_", "").replace("pathdump", "matrice4e")
            print(f"═══ {name} · {os.path.basename(f)} ═══")
            print(f"  경로 {A.size} · |E| {abs(E):.6e} · 가장 센 |a| {top:.6e}")
            print(f"  ⭐그 값과 {a.rel:g} 안에서 같은 항목: **{same.size} 번**")
            print(f"     |E| ÷ 한 줄 = {abs(E)/top:.4f}   ·   줄 합(결맞음) = {abs(z.sum()):.6e}")
            print(f"     지연 폭 {np.ptp(tau)*1e12:.3f} ps · 위상 폭 {np.degrees(ph_spread):.4f}°")
            print(f"     정체: {describe(dd, int(same[0]))[:96]}")
            #: 그 줄들이 서로 다른 물체·정점인가
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
        "question_ko": "el 0° 에서 같은 줄이 몇 번 적히고 그 줄들이 정말 같은 것인가",
        "same_rule_ko": f"가장 센 |a| 와 상대오차 {a.rel:g} 안",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
