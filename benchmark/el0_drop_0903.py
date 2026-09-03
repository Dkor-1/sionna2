# -*- coding: utf-8 -*-
"""
el0_drop_0903.py — 덱 2 부가 말한 «0° 의 갑작스런 낙차» 를 그 팔·그 문턱에서 그대로 본다.

무엇을 쫓나
    2026-09-03 덱 슬라이드 8~9 (`Sudden drops at 0°`) 가 보인 것 —
      · 판 `sionna_p4000000000_r15_n8192_d1` (스톡 PathSolver · 깊이 1 · 자유공간) · el 0° · 15 m
      · 문턱은 그 그림의 규칙 그대로 **\\|E\\| / 중앙값 < 0.9**
        (⚠내가 낙차 조사에 쓰던 0.1 보다 훨씬 얕다 — 그래서 지금껏 안 걸렸다)
      · 대본이 남긴 약속: 「이 자세들의 원인은 아직 모른다. 다음 주까지 더 본다」

무엇을 재나
    ⓐ 낙차 자세가 **이어진 블록**인가 **고립된 점**인가
    ⓑ 블록 간격이 **날개 지나가는 박자**(PRF / f_flash)와 맞나
    ⓒ 낙차 깊이가 몇 값에 뭉치나 — (N−1)/N 자리인가
    ⓓ 같은 자리에서 «프로펠러만» 팔은 어떤가 — 덱이 견준 그 짝이다

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" ~/.venvs/py312/bin/python benchmark/el0_drop_0903.py
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "outputs", "el0_drop_0903.json")

W_ARM = "sionna_p4000000000_r15_n8192_d1"          # 덱이 쓴 «드론 전체» 팔
P_ARM = "sionna_p4000000000_partsprop_r15_n8192_d1"   # 덱이 견준 «프로펠러만» 팔
THR = 0.9                                          # ⭐덱 그림의 규칙 그대로


def load(arm: str, el: str = "+0"):
    i, e, p = [], [], []
    for f in sorted(glob.glob(os.path.join(ROOT, "outputs", "elev_sweep_shards",
                                           f"{arm}_el{el}_*.npz"))):
        z = np.load(f)
        i.append(z["idx"]); e.append(z["E"]); p.append(z["npaths"])
    if not i:
        return None
    i = np.concatenate(i); e = np.concatenate(e); p = np.concatenate(p)
    o = np.argsort(i)
    return i[o], e[o], p[o]


def blocks(idx: np.ndarray):
    if idx.size == 0:
        return []
    out, s, n = [], int(idx[0]), 1
    for a, b in zip(idx[:-1], idx[1:]):
        if b == a + 1:
            n += 1
        else:
            out.append((s, n)); s, n = int(b), 1
    out.append((s, n))
    return out


def main() -> None:
    T = json.load(open(os.path.join(ROOT, "outputs", "report07_three_engines.json"),
                       encoding="utf-8"))["_meta"]
    prf, ffl = float(T["prf_hz"]), float(T["f_flash_hz"])
    per = prf / ffl
    print(f"⭐PRF {prf:,.0f} Hz · 날개 박자 {ffl:.2f} Hz ⇒ 날개 주기 **{per:.1f} 자세**")
    print(f"⭐문턱은 덱 그림 그대로 |E|/중앙 < {THR}\n")

    rows = []
    for ko, arm in (("드론 전체", W_ARM), ("프로펠러만", P_ARM)):
        got = load(arm)
        if got is None:
            print(f"⛔{ko}: 샤드 없음 — {arm}")
            continue
        i, e, npa = got
        a = np.abs(e); med = float(np.median(a))
        bad = i[a / med < THR]
        B = blocks(bad)
        L = np.array([n for _, n in B]) if B else np.zeros(0, int)
        S = np.array([s for s, _ in B]) if B else np.zeros(0, int)
        gap = np.diff(S) if S.size > 1 else np.zeros(0)
        r = a[a / med < THR] / med

        print(f"═══ {ko} · {arm} ═══")
        print(f"  자세 {a.size} · 중앙 |E| {med:.4e} · 낙차 {bad.size} ({100*bad.size/a.size:.2f} %)")
        if bad.size:
            print(f"  블록 {len(B)} · 길이 중앙 {np.median(L):.0f} (최소 {L.min()} 최대 {L.max()}) "
                  f"· 길이1 {int(np.sum(L==1))}")
            if gap.size:
                print(f"  블록 간격 중앙 {np.median(gap):.1f}  ⭐날개 주기 대비 "
                      f"**{np.median(gap)/per:.2f} 배**")
                ph = (S % per) / per
                h, _ = np.histogram(ph, bins=10, range=(0, 1))
                print(f"  주기로 접은 시작 위상: {list(h)} · 최대칸/평균 {h.max()/(S.size/10):.2f}")
            print(f"  낙차 깊이 |E|/중앙 — 중앙 {np.median(r):.4f} · 최소 {r.min():.4f} "
                  f"· 최대 {r.max():.4f}")
            #: (N−1)/N 자리에 뭉치나
            for N in (2, 3, 4, 5, 6, 9):
                q = (N - 1) / N
                n_near = int(np.sum(np.abs(r - q) < 0.02))
                if n_near:
                    print(f"     (N−1)/N = {q:.4f} (N={N}) 둘레 ±0.02 : {n_near} 자세")
            print(f"  경로 수 — 정상 중앙 {np.median(npa[a/med >= THR]):.0f} · "
                  f"낙차 중앙 {np.median(npa[a/med < THR]):.0f}")
        rows.append(dict(case=ko, arm=arm, n_poses=int(a.size), median_abs_E=med,
                         n_drop=int(bad.size), n_blocks=len(B),
                         len_median=float(np.median(L)) if L.size else None,
                         len_max=int(L.max()) if L.size else None,
                         gap_median=float(np.median(gap)) if gap.size else None,
                         gap_over_blade_period=float(np.median(gap) / per) if gap.size else None,
                         depth_median=float(np.median(r)) if r.size else None,
                         depth_min=float(r.min()) if r.size else None,
                         drop_poses=[int(x) for x in bad[:40]]))
        print()

    json.dump({"_meta": {
        "generator": "benchmark/el0_drop_0903.py",
        "question_ko": "덱 2 부가 보인 «0° 의 갑작스런 낙차» 가 무엇인가",
        "threshold_ko": f"|E| / 중앙값 < {THR} (덱 그림 규칙 그대로)",
        "prf_hz": prf, "f_flash_hz": ffl, "blade_period_poses": round(per, 2),
        "deck_ko": "teammeeting_0903 슬라이드 8~9 · 대본이 「원인은 아직 모른다」로 남겨 둔 자리",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
