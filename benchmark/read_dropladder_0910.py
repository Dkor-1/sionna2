#!/usr/bin/env python
"""광선 예산에 따라 «낙차» 와 «빠진 벌» 이 어떻게 움직이나 — 이미 구운 샤드만 읽는다.

■ 왜 이걸 만들었나
  2026-09-10 에 덱 6 쪽의 수(광선 40 배 · 경로 30 배 · 세 벌 그대로)를 샤드로 검산하다가,
  같은 사다리에서 **낙차 자세 수가 0 → 14 → 37 로 늘어나는 것**을 봤다. 덱은 그 축을
  「the count of copies did not move at all」로만 말한다 — 중앙 벌 수(3)는 맞지만
  **예외 자세 수는 움직인다.** 그 움직임을 원장으로 남긴다.

■ 무엇을 세나 (⛔둘은 다른 잣대다)
  · «줄<3»   — n_dup < 2 인 자세. 즉 같은 줄이 세 번 안 적힌 자세.
  · «낙차»   — |E| 가 자세 중앙값의 0.9 배 아래인 자세(덱 2 쪽이 쓰는 규칙).
  이 둘이 **같은 자세 집합인지**가 덱 3 쪽의 「낙차 자세에서 세 벌 중 하나가 빠져 있다」다.

■ ⛔이 판독기가 답하지 않는 것
  · ⛔«낙차가 광선의 산물이다» 로 읽지 않는다. 1e8 은 경로 중앙이 31 개뿐이라
    애초에 구조가 성기다 — 「적으면 안 보인다」와 「많으면 생긴다」를 이 축으로 못 가른다.
  · ⛔사다리가 있는 팔은 R0D0E0F1 하나뿐이다(다른 팔은 4e9 한 점씩). 팔을 건너 못 읽는다.
  · ⛔솔버 씨앗은 이 축에서 고정이다(elevation_sweep_md.py:893 seed=1 하드코딩).
    씨앗을 흔든 판은 40 m·el −15° 에만 있고 레벨 표준편차가 1.833 dB 다
    (outputs/raybudget_seed_ladder.json) — 이 칸에 옮겨 읽지 않는다.
  · ⛔실기 계측 대조는 0 건이다.

쓰는 법 (⛔CPU 전용 · 코어를 묶는다):
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/read_dropladder_0910.py
"""
from __future__ import annotations
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
try:
    if len(os.sched_getaffinity(0)) > 8:
        os.sched_setaffinity(0, set(range(8, 12)))
except Exception:
    pass
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

import numpy as np                                             # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "read_dropladder_0910.json")
MESH = "mfixbatteryi5_blperairframe"
EL, RNG, DEPTH, NPOSE = 0, 15, 2, 8192
DIP = 0.9                                   # 덱 2 쪽이 쓰는 낙차 규칙
ARMS = ("R0D0E0F1", "R0D1E0F1", "R0D1E1F1", "R1D0E0F1", "R1D1E1F1")
SPPS = (100_000_000, 1_000_000_000, 4_000_000_000)


def cell(arm: str, spp: int):
    """⛔n8192 와 메쉬 사이에 꼬리표가 **하나도 없는** 판만 — az·rep·bs·ps 를 섞지 않는다.

    ⚠2026-09-10 에 실제로 물렸다: 넓은 glob 으로 뽑았더니 자세가 65,536 개로 나왔다
      (같은 idx 를 쓰는 다른 판들이 겹쳐 들어왔다). 아래 이름은 **정확히** 맞춘다.
    """
    pat = (f"{SHD}/sionna_p{spp}_sw{arm}_r{RNG}_n{NPOSE}_{MESH}"
           f"_d{DEPTH}_el{EL:+g}_*.npz")
    fs = sorted(glob.glob(pat))
    if not fs:
        return None
    E, I, D, P = [], [], [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"]); I.append(z["idx"])
        D.append(z["n_dup"] if "n_dup" in z.files else np.full(z["idx"].shape, -1))
        P.append(z["npaths"] if "npaths" in z.files else np.full(z["idx"].shape, -1))
    o = np.argsort(np.concatenate(I))
    return dict(n_shards=len(fs), files=[os.path.basename(f) for f in fs],
                E=np.concatenate(E)[o], D=np.concatenate(D)[o], P=np.concatenate(P)[o])


def main() -> int:
    print(f"■ 앙각 {EL:+g} · {RNG} m · 깊이 {DEPTH} · 빈 하늘 · 자세 {NPOSE} · 낙차 규칙 {DIP}\n")
    print(f"  {'팔':<10}{'광선':>15}{'샤드':>5}{'자세':>7}{'경로중앙':>9}"
          f"{'줄<3':>6}{'낙차':>6}{'공통':>6}{'벌수중앙':>9}")
    rows = []
    for arm in ARMS:
        for spp in SPPS:
            c = cell(arm, spp)
            if c is None:
                continue
            E, D, P = c["E"], c["D"], c["P"]
            if (D < 0).all():
                continue
            a = np.abs(E); med = float(np.median(a))
            short = D < 2                       # 세 번 안 적힌 자세
            dip = (a / med) < DIP               # 덱 2 쪽 규칙
            r = dict(arm=arm, spp=spp, n_shards=c["n_shards"], n_poses=int(E.size),
                     npaths_median=(int(np.median(P[P >= 0])) if (P >= 0).any() else None),
                     n_short=int(short.sum()), n_dip=int(dip.sum()),
                     n_both=int((short & dip).sum()),
                     copies_median=int(np.median(D[D >= 0])) + 1,
                     dip_equals_short=bool(int(short.sum()) == int(dip.sum())
                                           == int((short & dip).sum())),
                     files=c["files"])
            rows.append(r)
            print(f"  {arm:<10}{spp:>15,}{r['n_shards']:>5}{r['n_poses']:>7}"
                  f"{str(r['npaths_median']):>9}{r['n_short']:>6}{r['n_dip']:>6}"
                  f"{r['n_both']:>6}{r['copies_median']:>9}"
                  f"{'  ⭐일치' if r['dip_equals_short'] else ''}", flush=True)

    lad = [r for r in rows if r["arm"] == "R0D0E0F1"]
    lad.sort(key=lambda r: r["spp"])
    print("\n  ── 읽기 ──")
    if len(lad) > 1:
        print(f"  광선 사다리(R0D0E0F1): 낙차 {[r['n_dip'] for r in lad]} "
              f"· 줄<3 {[r['n_short'] for r in lad]} · 경로중앙 {[r['npaths_median'] for r in lad]}")
        print(f"  벌 수 중앙: {[r['copies_median'] for r in lad]}  ← 덱 6 쪽의 «Still three»")
    n_eq = sum(1 for r in rows if r["dip_equals_short"])
    print(f"  «낙차 = 줄<3» 이 정확히 맞는 칸: {n_eq}/{len(rows)}")

    out = {"_meta": {"made": "benchmark/read_dropladder_0910.py",
                     "elevation_deg": EL, "range_m": RNG, "depth": DEPTH,
                     "scene": "빈 하늘", "mesh": MESH, "n_poses": NPOSE,
                     "dip_rule": DIP,
                     "dip_rule_ko": "|E| / 자세중앙값 < 0.9 — 덱 2 쪽이 쓰는 규칙",
                     "short_rule_ko": "n_dup < 2 — 같은 줄이 세 번 안 적힌 자세"},
           "rows": rows,
           "limits_ko": [
               "⛔«낙차가 광선의 산물이다» 로 읽지 않는다. 1e8 은 경로 중앙이 31 개뿐이라 "
               "구조가 애초에 성기다 — 「적으면 안 보인다」와 「많으면 생긴다」를 못 가른다.",
               "⛔사다리가 있는 팔은 R0D0E0F1 하나뿐이다. 다른 팔은 4e9 한 점씩이라 "
               "팔을 건너 읽을 수 없다.",
               "⛔솔버 씨앗은 이 축에서 고정이다(elevation_sweep_md.py:893 seed=1). "
               "씨앗을 흔든 판은 40 m·el −15° 에만 있고 레벨 표준편차 1.833 dB 다"
               "(outputs/raybudget_seed_ladder.json) — 이 칸에 옮겨 읽지 않는다.",
               "⛔광선 수를 바꾸면 경로 수와 경로당 가중치가 함께 움직인다"
               "(field_calculator.py:221 의 4π/samples_per_src). 단일 변수가 아니다. "
               "⛔이것을 «솔버의 결함» 으로도 «상쇄되니 괜찮다» 로도 읽지 않는다 — 재 보지 않았다.",
               "⛔낙차 규칙 0.9 는 자유 파라미터다. 다른 문턱에서 수가 달라진다.",
               "⛔실기 계측 대조는 0 건이다. 이 판으로도 안 생긴다."]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n  원장 → {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
