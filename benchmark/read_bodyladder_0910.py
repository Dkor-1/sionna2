#!/usr/bin/env python
"""동체 배율 사다리를 읽는다 — **이미 구워 둔 샤드만** 쓴다. GPU 를 안 쓴다.

■ 왜 이걸 만들었나
  2026-09-10 정정으로 RESUME_0909 §① 의 동체 칸이 바뀌었다. 옛 표는 0.86 한 점을
  「동체만」으로 읽었는데 그 칸은 «깊이 3 ∩ 동체 ×0.5» 로 손잡이 둘이 섞인 짝이었다.
  고친 두 점은 ×0.5 = 0.9524(82 중 80) · ×2 = 0.6809(82 중 **64**) 다.
  ⇒ 「동체 ×2 가 18 개를 바꾼다」가 **단조로운 사다리인지 한 점의 튐인지** 두 점으로는 못 가른다.

  ⭐그런데 같은 조건의 `bs` 샤드가 **다섯 개나 이미 있다**(0.4·0.5·0.6·0.8·2).
    판독기가 그중 둘만 읽고 있었을 뿐이다. ⇒ 새로 살 것이 없다. 읽기만 하면 된다.

■ 잣대는 read_0918B_0909.py 를 **그대로 가져다 쓴다**(import). 새로 만들지 않는다.
  D = E_장면 − E_빈하늘 이 중앙에서 |중앙 D|×0.5 넘게 벗어난 자세 — **상대 편차 문턱**이다.
  ⛔「문턱 없는 셈」이라 부르지 않는다(2026-09-10 정정, 근원 read_0918B_0909.py).
  안 쓰는 것은 레벨 문턱(|E| < 자세중앙×0.1)뿐이다. ⛔DEV 는 자유 파라미터다.

■ ⛔이 판독기가 답하지 않는 것
  · ⛔«왜» 에는 답하지 않는다 — 몇 개가 살아남나까지다.
  · ⛔`bs` 는 **모형 축**이지 실기 형상이 아니다(src/articulated_fast.py:126).
    비구조 산란면만 키우므로 줄이면 동체와 팔 사이에 **틈이 생긴다**.
    ⛔팔·모터·기어·다리는 안 건드린다(:145 `_keep`). 허브·프롭도 고정이다.
  · ⛔D 는 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·후보 탐색 차이가 함께 들어간다.
  · ⛔「격자 흔들림」(광선 예산 ±5 %)은 **널이 아니다** — 초기 광선은 씨앗 없는 결정적
    피보나치 격자라(sionna/rt/utils/ray_tracing.py:24-30) 확률적 널이 아예 없다.
    두 점은 신뢰구간이 아니다. 참고선으로만 쓴다.

쓰는 법 (⛔CPU 전용 · 코어를 묶는다 — 규약 17):
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" taskset -c 0-3 \
      /workspace/.venvs/py312/bin/python benchmark/read_bodyladder_0910.py
"""
from __future__ import annotations
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#: ⛔무거운 CPU 작업은 코어를 묶는다 — 셸에서 taskset 을 안 줬을 때의 안전망
try:
    if len(os.sched_getaffinity(0)) > 8:
        os.sched_setaffinity(0, set(range(4)))
except Exception:
    pass
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

import numpy as np                                          # noqa: E402
from read_0918B_0909 import load, stem, measure, DEV, EL     # noqa: E402

OUT = os.path.join(ROOT, "outputs", "read_bodyladder_0910.json")
#: 사다리 — 1.0 은 배율을 안 준 기준선이라 tail 이 빈 칸이다
LADDER = [(0.4, "_bs0.4"), (0.5, "_bs0.5"), (0.6, "_bs0.6"),
          (0.8, "_bs0.8"), (1.0, ""), (2.0, "_bs2")]
#: 참고선 — 격자를 갈았을 때의 흔들림(⛔널이 아니다)
GRID = [(3_800_000_000, "격자 3.8e9"), (4_200_000_000, "격자 4.2e9")]
BASE = 1.0


def main() -> int:
    cells, flags = {}, {}

    def take(key, scene_stem, free_stem):
        fr, ou = load(free_stem), load(scene_stem)
        if fr is None or ou is None:
            print(f"  ⛔샤드 없음: {key}", flush=True)
            return
        r = measure(fr, ou)
        if r is None:
            print(f"  ⛔자세 수가 안 맞는다: {key}", flush=True)
            return
        flags[key] = r.pop("_flag")
        r["files_scene"] = ou["files"]
        cells[key] = r

    print(f"■ 동체 배율 사다리 · 앙각 {EL:+g} · 우리 씬 땅만 · 팔 R0D0E0F1 · 4e9 · 깊이 2")
    print(f"  잣대 DEV={DEV} — 상대 편차 문턱(레벨 문턱은 안 쓴다). ⛔자유 파라미터다\n")
    for bs, tail in LADDER:
        take(f"동체 ×{bs:g}", stem(env="outdoor01_ground", tail=tail), stem(tail=tail))
    for spp, nm in GRID:
        take(nm, stem(spp=spp, env="outdoor01_ground"), stem(spp=spp))

    bkey = f"동체 ×{BASE:g}"
    if bkey not in flags:
        print("⛔기준선이 없다 — 멈춘다"); return 1
    fb = flags[bkey]
    nb = int(fb.sum())

    print(f"  기준선(동체 ×1) 사건 **{nb} 개** · 자세 {fb.size}\n")
    print(f"  {'칸':<12}{'사건':>6}{'몫 %':>8}{'남음':>7}{'잃음':>7}{'새로':>7}"
          f"{'자카드':>9}{'경로중앙':>10}")
    rows = []
    for k in list(cells):
        fa = flags[k]
        if fa.size != fb.size:
            continue
        inter = int((fa & fb).sum())
        uni = int((fa | fb).sum())
        row = {"cell": k, "n_events": int(fa.sum()),
               "share_pct": cells[k]["share_pct"],
               "kept_of_base": inter,
               "lost_from_base": int((fb & ~fa).sum()),
               "brand_new": int((~fb & fa).sum()),
               "jaccard": round(inter / max(uni, 1), 4),
               "expected_intersect_if_unrelated": round(int(fa.sum()) * nb / fa.size, 3),
               "npaths_median": cells[k].get("npaths_median"),
               "at_path_cap": cells[k].get("at_path_cap")}
        #: ⭐개수와 비율을 한 열에 놓지 않는다 — 기대 «자카드» 를 따로 낸다
        e = row["expected_intersect_if_unrelated"]
        #: ⛔이름을 2026-09-11 에 expected_ → approx_ 로 고쳤다. 기대 교집합을 비율식에 **넣은**
        #  근삿값이지 «자카드의 기댓값» 이 아니다. ⛔애초에 유의성 검정이 아니다.
        row["approx_jaccard_if_unrelated"] = round(e / max(int(fa.sum()) + nb - e, 1e-9), 5)
        rows.append(row)
        print(f"  {k:<12}{row['n_events']:>6}{row['share_pct']:>8}"
              f"{row['kept_of_base']:>7}{row['lost_from_base']:>7}{row['brand_new']:>7}"
              f"{row['jaccard']:>9.4f}{str(row['npaths_median']):>10}"
              f"{'  ⛔상한' if row['at_path_cap'] else ''}", flush=True)

    lad = [r for r in rows if r["cell"].startswith("동체")]
    lad.sort(key=lambda r: float(r["cell"].split("×")[1]))
    kept = [r["kept_of_base"] for r in lad]
    grid = [r["kept_of_base"] for r in rows if r["cell"].startswith("격자")]
    mono = all(b <= a for a, b in zip(kept, kept[1:]))

    print("\n  ── 읽기 ──")
    print(f"  사다리(작은 동체 → 큰 동체) 남은 수: {kept}")
    print(f"  격자를 갈았을 때 남은 수(참고선): {grid}")
    print(f"  단조로 줄어드나: {mono}")

    out = {"_meta": {#: ⭐관문(check_new_file_rules.py:166)이 보는 키는 «generator» 다 —
                     #  «made» 로 적어 «못 굽는 원장» 으로 걸리던 것을 고친다(2026-09-10).
                     "generator": "benchmark/read_bodyladder_0910.py",
                     "elevation_deg": EL, "arm": "R0D0E0F1", "spp": 4_000_000_000,
                     "scene": "outdoor01_ground", "depth": 2, "dev_rule": DEV,
                     "n_poses": int(fb.size), "baseline_events": nb},
           "rows": rows, "ladder_kept": kept, "grid_kept": grid,
           "monotonic_in_body_scale": bool(mono),
           "limits_ko": [
               "⛔bs 는 모형 축이다 — 비구조 산란면만 키운다(팔·모터·기어·다리 제외, "
               "허브·프롭 고정). 줄이면 동체와 팔 사이에 틈이 생긴다. 실기 형상이 아니다.",
               "⛔«격자» 두 줄은 널이 아니다 — 초기 광선은 씨앗 없는 결정적 피보나치 격자이고, "
               "같은 설정 되풀이는 자카드 1.000 이라 확률적 널이 아예 없다. 두 점은 신뢰구간이 아니다.",
               "⚠광선 예산을 바꾸면 경로 수와 경로당 가중치가 함께 움직인다"
               "(field_calculator.py:221 의 4π/samples_per_src). 단일 변수가 아니다. "
               "⛔이것을 «솔버의 결함» 으로 읽지 않는다 — 표본 수에 무관한 기댓값을 "
               "만들려고 일부러 넣은 정규화다(:211-220 주석). ⛔그렇다고 «상쇄되니 "
               "괜찮다» 도 아니다: :448 의 1/q 는 재질이 정한 표집 확률을 상쇄하는 "
               "것이지 1/samples_per_src 가 아니고, :313 이 확산에서 입체각을 2π 로 "
               "되돌려 4π/spp 를 타는 것은 첫 상호작용뿐이다. ⛔어떻게 남는지는 "
               "재 보지 않았다.",
               "⛔expected_* 는 균일·독립 추출을 가정한 참고값이다. 자세는 시각이고 "
               "로터 위상 구조가 있다 — 유의성 검정이 아니다.",
               "⛔D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·"
               "후보 탐색 차이가 함께 들어간다.",
               "⛔실기 계측 대조는 0 건이다. 이 판으로도 안 생긴다."]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n  원장 → {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
