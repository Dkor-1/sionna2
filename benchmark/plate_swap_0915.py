#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""평판 한 장으로 «입사·출사를 바꾸면 얼마나 달라지나» 를 잰다 (2026-09-15 신설).

    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/plate_swap_0915.py

왜 있나
-------
`src/rcs_sbr.py` 의 지면 갈래는 섞인 경로 둘 중 **한쪽만 재서 2 를 곱한다.** 그 옆 주석은
오랫동안 그 비대칭을 「이산화 오차다 — 격자를 촘촘히 하면 준다」고 설명했고, 근거로
**드론 메쉬 사다리** 하나를 들었다(상대차 중앙값이 λ/8 → λ/24 에서 0.3549 → 0.0576).

⛔그 설명은 2026-09-15 에 **철회**됐다. 외부 점검 메모(docs/KERNEL_OUTDOOR_REVIEW_0915.md)
가 반례를 냈고 우리가 다시 재서 확인했다 — **한 각도 쌍만 떼어 재면 격자를 아무리
촘촘히 해도 안 준다.** 이 파일이 그 반례를 상설로 둔다.

⭐이 검사가 답하는 것
  ① 정사각 평판에서 입사 0° / 출사 60° 의 «순서를 바꾼 크기 비» 가 격자를 줄일 때
     1 로 가는가, 아니면 다른 수로 수렴하는가
  ② 그 수가 **cos θ_i / cos θ_s** 인가 — 광선 격자가 û_i 에 수직이라 합이 입사
     코사인만 무게로 지는 데서 오는 값이다

⛔이 검사는 **어느 쪽이 물리적으로 옳은지 판정하지 않는다.** PO 자체가 상호적이지
  않고, 상호적인 식이 무엇을 줄지는 별도 기준해와 맞대야 안다. 여기서 재는 것은
  「우리 구현이 무엇을 하는가」까지다.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from rcs_po import _plate_mesh                                  # noqa: E402
from rcs_sbr import sbr_field_bistatic                          # noqa: E402

FC = 3.5e9
LAM = 2.998e8 / FC
PLATE_M = 0.25
#: 사다리 — 주석이 인용하던 드론 사다리와 같은 잣대로 보려고 λ/12 를 포함한다.
DIVS = (12, 24, 48, 96)
#: 각 쌍 — 첫 줄이 메모의 반례다. ⚠널 근처 쌍은 cos 비를 안 따라간다(그것도 적는다).
PAIRS = ((0, 20), (0, 40), (0, 60), (0, 70), (10, 50), (20, 60), (30, 70), (15, 45))


def outward(theta_deg: float) -> np.ndarray:
    """법선(+z)에서 theta 만큼 기운 바깥 방향 단위벡터 (xz 평면)."""
    r = np.radians(float(theta_deg))
    return np.array([np.sin(r), 0.0, np.cos(r)])


def mag(mesh, gm, ui, us, d, key) -> float:
    return abs(complex(sbr_field_bistatic(mesh, gm, FC, ui, us, spacing=d,
                                          penetrate=False, ptd=False,
                                          cache_key=key)))


def main() -> int:
    m = _plate_mesh(PLATE_M)
    #: ⛔재질 이름 'pec' 는 없다 — 완전도체는 **float 1.0**(=|Γ|)로 준다.
    gm = {g: 1.0 for g in set(np.asarray(m.g).tolist())}
    out = dict(fc_hz=FC, plate_m=PLATE_M, gamma_abs=1.0,
               note_ko="입사·출사를 바꾼 |E| 의 비. 1 로 가면 순서가 무의미하다는 뜻이다.")

    print(f"평판 {PLATE_M} m · {FC/1e9:.1f} GHz · |Γ|=1 · 관통/PTD 끔 · 삼각형 {m.n_tris()}")
    print("\n═══ ① 격자를 촘촘히 하면 비가 1 로 가는가 (입사 0° / 출사 60°) ═══")
    print(f"{'격자':>8} {'|E(0→60)|':>14} {'|E(60→0)|':>14} {'비':>10}")
    lad = []
    for div in DIVS:
        d = LAM / div
        a_ = mag(m, gm, outward(0.0), outward(60.0), d, f"p_a{div}")
        b_ = mag(m, gm, outward(60.0), outward(0.0), d, f"p_b{div}")
        r = a_ / max(b_, 1e-300)
        lad.append(dict(div=div, e_fwd=a_, e_rev=b_, ratio=r))
        print(f"λ/{div:<6} {a_:>14.6e} {b_:>14.6e} {r:>10.6f}")
    out["ladder"] = lad
    print(f"\n  ⭐가장 촘촘한 λ/{DIVS[-1]} 에서 비 {lad[-1]['ratio']:.6f} · "
          f"cos(0°)/cos(60°) = {np.cos(0)/np.cos(np.radians(60)):.6f}")
    print("  ⇒ ⛔1 로 가지 않는다. 「격자를 촘촘히 하면 준다」는 이 조건에서 성립하지 않는다.")

    print("\n═══ ② 그 비가 cos θi / cos θs 인가 (λ/96) ═══")
    d = LAM / DIVS[-1]
    print(f"{'θi':>5} {'θs':>5} {'재어 본 비':>12} {'cosθi/cosθs':>13} {'차':>10}")
    rows = []
    for ti, ts in PAIRS:
        a_ = mag(m, gm, outward(ti), outward(ts), d, f"q_a{ti}_{ts}")
        b_ = mag(m, gm, outward(ts), outward(ti), d, f"q_b{ti}_{ts}")
        r = a_ / max(b_, 1e-300)
        c = float(np.cos(np.radians(ti)) / np.cos(np.radians(ts)))
        rows.append(dict(theta_i=ti, theta_s=ts, ratio=r, cos_ratio=c, diff=r - c))
        print(f"{ti:>5} {ts:>5} {r:>12.6f} {c:>13.6f} {r - c:>+10.6f}")
    out["pairs"] = rows
    near = sum(abs(r["diff"]) < 0.06 for r in rows)
    print(f"\n  cos 비를 0.06 안쪽으로 따라간 쌍 {near}/{len(rows)}")
    print("  ⚠나머지는 위상 적분의 널 근처라 벗어난다 — cos 비가 **전부는 아니다.**")
    print("\n⛔어느 쪽이 물리적으로 옳은지는 이 검사가 답하지 않는다.")

    p = os.path.join(ROOT, "outputs", "plate_swap_0915.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n원장 → {os.path.relpath(p, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
