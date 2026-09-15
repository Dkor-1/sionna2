#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""외부 점검 메모(0915)의 지적을 **우리 쪽에서 다시 재는** 상시 검사.

    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/remeasure_review_0915.py

왜 있나
-------
2026-09-15 외부 점검 메모(`docs/KERNEL_OUTDOOR_REVIEW_0915.md`)가 여덟 가지를 짚었다.
그중 셋은 **내가 사용자에게 보고한 숫자**를 직접 건드린다. 남의 원장을 그대로 믿지 않고
창고에서 다시 재려고 이 파일을 둔다. ⛔읽기 전용이다 — 아무것도 쓰지 않는다.

⭐이 검사가 답하는 것
  ① 반복 팔 ↔ 원본 : 배열이 같은가 · 복소 상대 L2 · RMS 레벨 차
  ② 2.0.1 ↔ 2.1.0  : RMS 레벨 차 · **공통 위상** · 위상 맞추기 전후 잔차
                      · 자세마다의 위상차 분포(0° 근처 / 180° 근처 몫)

⛔팔 이름은 **문법으로 되읽는다**(`src/arm_grammar.py`) — 즉석 정규식으로 대조군을
  지어서 낸 사고가 이 레포에 다섯 건 있다. 짝을 지을 때 **다른 꼬리표가 하나도 없는지**
  확인하고, 하나라도 다르면 그 짝은 버린다.
"""
from __future__ import annotations

import collections
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from arm_grammar import ArmNameError, parse, unparse            # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
SHARD_RE = re.compile(r"^(?P<arm>.+)_el(?P<el>[-+][\d.]+)_(?P<sh>\d+)\.npz$")


def cells() -> dict:
    """(팔, 앙각) → {조각번호: 경로}."""
    out = collections.defaultdict(dict)
    for p in sorted(os.listdir(SHD)):
        m = SHARD_RE.match(p)
        if m:
            out[(m.group("arm"), m.group("el"))][int(m.group("sh"))] = os.path.join(SHD, p)
    return out


def partners(C: dict, tag: str, value) -> list:
    """`tag` 하나만 다른 짝을 낸다. ⛔다른 꼬리표가 하나라도 다르면 버린다."""
    out = []
    for (arm, el), shd in C.items():
        try:
            f = parse(arm)
        except ArmNameError:
            continue
        if f.get(tag) != value:
            continue
        g = dict(f)
        g.pop(tag, None)
        base = unparse(g)
        if (base, el) not in C:
            continue
        fa = parse(base)
        diff = {k for k in set(fa) | set(f) if fa.get(k) != f.get(k)}
        if diff != {tag}:                       # ⛔한 축이 아니면 대조군이 아니다
            continue
        out.append((base, arm, el, C[(base, el)], shd))
    return out


def joined(shd_a: dict, shd_b: dict):
    """두 팔의 **같은 조각 번호**만 골라 이어 붙인다."""
    ks = sorted(set(shd_a) & set(shd_b))
    if not ks:
        return None, None
    A = np.concatenate([np.load(shd_a[k])["E"] for k in ks])
    B = np.concatenate([np.load(shd_b[k])["E"] for k in ks])
    return (A, B) if A.shape == B.shape else (None, None)


def rms_db(x) -> float:
    return 20.0 * np.log10(max(float(np.sqrt(np.mean(np.abs(x) ** 2))), 1e-300))


def report(C: dict, tag: str, value, title: str) -> list:
    rows = []
    P = partners(C, tag, value)
    print(f"\n═══ {title} — 짝 {len(P)} 칸 ═══")
    if not P:
        return rows
    print(f"{'환경':>16} {'앙각':>5} {'깊':>2} {'같음':>5} {'RMS 차 dB':>11} "
          f"{'공통위상°':>10} {'L2 전':>8} {'L2 후':>8} {'자세 180°':>9}")
    for base, arm, el, sa, sb in sorted(P, key=lambda t: (t[0], float(t[2]))):
        A, B = joined(sa, sb)
        if A is None:
            continue
        ip = np.vdot(A, B)
        ph = float(np.degrees(np.angle(ip)))
        l2_0 = float(np.linalg.norm(A - B) / max(np.linalg.norm(A), 1e-30))
        l2_p = float(np.linalg.norm(A * np.exp(1j * np.angle(ip)) - B)
                     / max(np.linalg.norm(A), 1e-30))
        m = (np.abs(A) > 0) & (np.abs(B) > 0)
        d = np.degrees(np.angle(B[m] / A[m])) if m.any() else np.zeros(0)
        p180 = float(np.mean(np.abs(np.abs(d) - 180) < 5) * 100) if d.size else 0.0
        f0 = parse(base)
        env = (f0.get("env") or "빈하늘")[:16]
        same = bool(np.array_equal(A, B))
        rows.append(dict(env=env, el=el, depth=f0.get("max_depth"), same=same,
                         drms=rms_db(B) - rms_db(A), phase=ph, l2_0=l2_0, l2_p=l2_p,
                         pose180=p180, arm=base))
        print(f"{env:>16} {el:>5} {str(f0.get('max_depth')):>2} "
              f"{('예' if same else '아니오'):>5} {rms_db(B) - rms_db(A):>11.6f} "
              f"{ph:>10.3f} {l2_0:>8.4f} {l2_p:>8.4f} {p180:>8.1f}%")
    return rows


def main() -> int:
    C = cells()
    print(f"창고 칸 {len(C)}")

    rep = report(C, "rep", 1, "① 반복 팔 ↔ 원본 (같은 판)")
    if rep:
        print(f"\n  배열이 완전히 같은 칸 {sum(r['same'] for r in rep)} / {len(rep)}")
        print(f"  복소 상대 L2 최대 {max(r['l2_0'] for r in rep):.4e}")
        print(f"  RMS 레벨 차 |최대| {max(abs(r['drms']) for r in rep):.6f} dB")
        print("  ⇒ ⛔「재실행하면 같다」로 읽지 않는다. 같은 것은 **레벨**이고, "
              "복소장은 매번 다르다.")

    br = report(C, "solver_build", "210", "② 2.0.1 ↔ 2.1.0 (판만 다름)")
    if br:
        fl = [r for r in br if r["pose180"] > 50]
        print(f"\n  RMS 레벨 차 범위 {min(r['drms'] for r in br):+.6f} ~ "
              f"{max(r['drms'] for r in br):+.6f} dB")
        print(f"  정확히 0 인 칸 {sum(abs(r['drms']) < 1e-12 for r in br)} / {len(br)}")
        sky = [r for r in br if r["env"] == "빈하늘"]
        print(f"  빈 하늘 {len(sky)} 칸 중 0 아닌 칸 "
              f"{sum(abs(r['drms']) >= 1e-12 for r in sky)}")
        print(f"  ⭐복소장이 **부호 반대**인 칸 {len(fl)} / {len(br)}"
              + (f" — 전부 지면을 품은 장면: "
                 f"{sorted({r['env'] for r in fl})}" if fl else ""))
        if fl:
            print(f"     그 칸들의 앙각 {sorted({r['el'] for r in fl})} · "
                  f"자세 중 180° 몫 {min(r['pose180'] for r in fl):.1f}"
                  f"~{max(r['pose180'] for r in fl):.1f}%")
            print("  ⇒ ⛔두 판의 샤드를 **결맞게 더하지 않는다**. 이름의 `_rt210` 과 "
                  "판독기의 판 검사가 그것을 막고 있다.")
            print("  ⛔원인은 아직 모른다 — 2.0.1 을 되돌려 경로별 계수를 맞대야 갈린다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
