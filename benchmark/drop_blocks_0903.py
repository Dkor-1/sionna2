# -*- coding: utf-8 -*-
"""
drop_blocks_0903.py — 자유공간 낙차가 «날개가 지나가는 것» 인가.

물음
    자유공간 낙차는 **연속된 블록**이다(예: 자세 114~121 여덟 개). 실외의 고립 낙차와 다르다.
    ⛔**주기성만으로는 «물리» 와 «솔버» 가 안 갈린다**(2026-09-04 정정). 아래 15~16 행이
      적듯 **자세 번호가 곧 날개 각도**이므로, 기하가 정하는 것은 **무엇이든** — 후보 생성
      단계의 유실을 포함해 — 같은 주기로 되풀이된다. 이 저장소가 그 경우를 이미 관측했다
      (CLAUDE.md: 「드론 코퍼스에서는 자세의 기하가 대체로 정하고 병렬 순서는 경계 자세만
      가른다」). ⇒ 「솔버면 주기가 없다」를 예측할 근거가 없다.
    ⇒ 여기서는 주기·길이·위상 쏠림을 **재기만** 한다. 물리/솔버 판정은 **경로 목록
      (무엇이 빠졌나)** 으로만 한다.
    ⚠표본이 얇다 — 이 스크립트가 낸 원장은 **칸 3 개**(블록 65·60·39)다. 8,192 자세에
      블록 65 개면 평균 간격이 126 자세임을 함께 읽는다.

무엇을 재나
    · 낙차 자세를 **블록**으로 묶어 길이 분포를 낸다
    · 블록 시작 자세의 **간격** 분포를 내고, 날개 박자가 만드는 예상 주기와 견준다
    · 자세 번호를 한 바퀴로 접어(modulo) 쏠림이 있는지 본다

⭐예상 주기 — 자세는 PRF 로 표집한 시간열이다. 날개 하나가 지나가는 박자가 f_flash 면
  자세 단위 주기는 PRF / f_flash 다.

⛔판정하지 않는다 — 수를 내고 문장은 사람이 쓴다(주장 게이트 ⓑ).

쓰는 법
    CUDA_VISIBLE_DEVICES="" ~/.venvs/py312/bin/python benchmark/drop_blocks_0903.py
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "outputs", "drop_blocks_0903.json")
DEEP = 0.1


def load_cell(arm: str, el: str):
    i, e = [], []
    for f in sorted(glob.glob(os.path.join(ROOT, "outputs", "elev_sweep_shards",
                                           f"{arm}_el{el}_*.npz"))):
        z = np.load(f)
        i.append(z["idx"]); e.append(z["E"])
    if not i:
        return None, None
    i = np.concatenate(i); e = np.concatenate(e)
    o = np.argsort(i)
    return i[o], e[o]


def blocks(idx: np.ndarray) -> list[tuple[int, int]]:
    """이어진 자세 번호를 (시작, 길이) 로 묶는다."""
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
    T = json.load(open(os.path.join(ROOT, "outputs",
                                    "report07_three_engines.json"), encoding="utf-8"))["_meta"]
    prf, ffl = float(T["prf_hz"]), float(T["f_flash_hz"])
    per = prf / ffl                       # 날개 하나가 지나가는 주기 [자세]
    print(f"⭐PRF {prf:,.0f} Hz · 날개 박자 {ffl:.2f} Hz "
          f"⇒ 예상 주기 **{per:.1f} 자세**\n")

    CASES = [
        ("자유공간 회절켬", "sionna_p4000000000_swR0D1E1F1_r15_n8192_az45_"
         "mfixbatteryi5_blperairframe_d2", "-15"),
        ("자유공간 회절끔", "sionna_p4000000000_swR0D0E0F1_r15_n8192_az67.5_"
         "mfixbatteryi5_blperairframe_d2", "-45"),
        ("실외", "sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_az45_"
         "mfixbatteryi5_blperairframe_d2", "+0"),
    ]
    rows = []
    for ko, arm, el in CASES:
        i, e = load_cell(arm, el)
        if i is None:
            print(f"⛔{ko}: 샤드 없음")
            continue
        a = np.abs(e); med = float(np.median(a))
        d = i[a / med < DEEP]
        B = blocks(d)
        L = np.array([n for _, n in B])
        S = np.array([s for s, _ in B])
        gap = np.diff(S) if S.size > 1 else np.zeros(0)
        print(f"═══ {ko} · el {el} ═══")
        print(f"  자세 {a.size} · 낙차 {d.size} ({100*d.size/a.size:.2f} %) · 블록 {len(B)}")
        print(f"  블록 길이 — 중앙 {np.median(L):.0f} · 최소 {L.min()} · 최대 {L.max()} "
              f"· 길이1 블록 {int(np.sum(L == 1))}")
        if gap.size:
            print(f"  블록 간격 — 중앙 {np.median(gap):.1f} · 최소 {gap.min()} · 최대 {gap.max()}")
            print(f"  ⭐예상 주기 {per:.1f} 대비 간격 중앙 = {np.median(gap)/per:.2f} 배")
            #: 예상 주기로 접어 쏠림을 본다 — 물리면 특정 위상에 몰린다.
            ph = (S % per) / per
            h, _ = np.histogram(ph, bins=10, range=(0, 1))
            print(f"  주기로 접은 시작 위상 히스토그램(10칸): {list(h)}")
            print(f"    균일하면 {S.size/10:.1f} 씩 · 최대칸/평균 = {h.max()/(S.size/10):.2f}")
        rows.append(dict(case=ko, arm=arm, el=el, n_poses=int(a.size), n_deep=int(d.size),
                         n_blocks=len(B), len_median=float(np.median(L)),
                         len_min=int(L.min()), len_max=int(L.max()),
                         n_len1=int(np.sum(L == 1)),
                         gap_median=float(np.median(gap)) if gap.size else None,
                         expected_period_poses=round(per, 2),
                         gap_over_period=float(np.median(gap) / per) if gap.size else None))
        print()

    json.dump({"_meta": {
        "generator": "benchmark/drop_blocks_0903.py",
        "question_ko": "자유공간 낙차 블록이 날개 지나가는 박자와 맞나",
        "prf_hz": prf, "f_flash_hz": ffl, "expected_period_poses": round(per, 2),
        "deep_rule_ko": f"|E| < 중앙값 × {DEEP}",
        "reads_ko": "⛔판정은 여기 적지 않는다 — 표를 보고 사람이 쓴다(주장 게이트 ⓑ).",
    }, "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
