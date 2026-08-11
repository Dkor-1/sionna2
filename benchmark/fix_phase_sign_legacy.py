"""⭐구면파 옛 부호로 계산된 복소 시계열을 정정한다 (재계산 없이 켤레 한 번).

**왜** — 2026-08-11 에 `sbr_field(range_m=...)` 의 구면파 위상이 **거리**에 +j 를 걸고 있어
평면파 갈래(**투영**에 +j)와 정확히 반대인 것을 확정했다(`benchmark/verify_phase_sign.py`,
게이트 3/3 PASS · 5,000 m 에서 ρ = +0.99999974 로 평면파 수렴). 정정은 위상 인자의 부호를
뒤집는 것이고, 계수가 전부 실수(|Γ| 표 · 투과 τ · PTD)이므로 **총합의 켤레와 같다**.

⇒ 이미 계산된 자료는 `np.conj` 한 번으로 정확히 정정된다. **재계산이 필요 없다.**

**무엇이 바뀌나** — 도플러의 **부호**뿐이다.
  · 안 바뀜  σ = 4π/λ²|E|² · f_tip 크기 · 대역 에너지 · 플래시 박자 · 조화비 · 분류 정확도
  · 바뀜     ⊕/⊖ 스펙트럼 비대칭 · 접근 대 후퇴 · ours ↔ PathSolver 의 부호 비교

**멱등** — 파일에 `phase_sign_v2` 표식을 박는다. 이미 있으면 건드리지 않는다.
`--dry` 로 무엇이 바뀔지 먼저 볼 수 있다.

⚠**평면파로 계산된 것은 손대지 않는다.** 평면파 갈래는 처음부터 옳았다.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = "phase_sign_v2"

# ── 무엇을 고치나 ────────────────────────────────────────────────────────────
# (glob, 어떤 키를 고칠지 판정하는 함수 or None=복소 배열 전부)
#  ⭐구면파(range_m 을 준) 실행에서 나온 파일만 넣는다.
TARGETS = [
    # 앙각 스윕 — 우리 팔만 구면파(10 m). sionna 팔은 PathSolver 라 무관.
    ("outputs/elev_sweep_shards/ours_*.npz", None),
    ("outputs/elev_sweep_shards/ours_free_*.npz", None),
    ("outputs/elevation_sweep_md.npz", lambda k: k.startswith("ours")),
    # 8/11 덱 거리 그림 — deck_ours_by_range 가 range_m=R 로 냈다.
    ("outputs/deck_ours_by_range.npz", None),
    ("outputs/deck_ours_range_shards/*.npz", None),
    # 근거리장 대조 — ②구면파 계열만.
    ("outputs/nearfield_sphere_vs_plane.npz", lambda k: "sph" in k.lower()),
]


def fix_one(path: str, keysel, dry: bool) -> tuple[str, list[str]]:
    try:
        d = np.load(path, allow_pickle=True)
    except Exception as e:                                     # noqa: BLE001
        return f"열기 실패 ({e})", []
    keys = list(d.files)
    if MARK in keys:
        return "이미 정정됨 — 건너뜀", []
    hit = [k for k in keys
           if np.asarray(d[k]).dtype.kind == "c" and (keysel is None or keysel(k))]
    if not hit:
        return "복소 배열 없음 — 건너뜀", []
    if dry:
        return f"정정 예정 {len(hit)} 배열", hit
    new = {k: (np.conj(d[k]) if k in hit else d[k]) for k in keys}
    new[MARK] = np.array([1], dtype=np.int8)
    tmp = path + ".tmp.npz"
    np.savez_compressed(tmp, **new)
    os.replace(tmp, path)
    return f"정정 완료 {len(hit)} 배열", hit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="바꾸지 않고 무엇이 바뀔지만 본다")
    a = ap.parse_args()

    n_files = n_arr = 0
    for pat, keysel in TARGETS:
        paths = sorted(glob.glob(os.path.join(ROOT, pat)))
        if not paths:
            print(f"  (없음) {pat}")
            continue
        msgs: dict[str, int] = {}
        arrs = 0
        for p in paths:
            msg, hit = fix_one(p, keysel, a.dry)
            msgs[msg] = msgs.get(msg, 0) + 1
            arrs += len(hit)
            if hit and len(paths) == 1:
                print(f"      키: {hit[:8]}{' …' if len(hit) > 8 else ''}")
        summ = " · ".join(f"{v}개 {k}" for k, v in msgs.items())
        print(f"  {pat:46s} {len(paths):3d} 파일 → {summ}")
        n_files += sum(v for k, v in msgs.items() if "정정" in k and "이미" not in k)
        n_arr += arrs

    print(f"\n  ⇒ {'예정' if a.dry else '완료'}: {n_files} 파일 · {n_arr} 배열")
    if not a.dry:
        print("     표식 phase_sign_v2 를 박았으므로 다시 돌려도 두 번 적용되지 않는다.")


if __name__ == "__main__":
    sys.exit(main())
