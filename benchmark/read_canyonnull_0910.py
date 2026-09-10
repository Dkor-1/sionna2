#!/usr/bin/env python
"""협곡의 «널» 을 읽는다 — 0922 A 묶음. ⛔이미 구운 샤드만 쓴다(GPU 안 씀).

■ 왜 필요한가
  협곡에서 「걸린 자세 목록」을 다른 손잡이와 견주려면 **아무것도 안 바꿨을 때 얼마나
  흔들리나** 를 먼저 알아야 한다. 우리 씬(outdoor01_ground)에서는 그 값이 있는데
  (RESUME_0909 §① — 82 중 80), **협곡에서는 한 번도 없었다.**
  0922 A 가 그것을 샀다: 같은 설정 되풀이(rep1·rep2)와 광선 예산 ±5 %(3.8e9·4.2e9).

■ ⛔이 판독기가 답하지 않는 것 — 이름부터 조심한다
  · ⛔**«널» 이 아니다.** 초기 광선은 씨앗 없는 결정적 피보나치 격자다
    (sionna/rt/utils/ray_tracing.py:24-30). 같은 설정 되풀이가 자카드 1.000 이면
    그것은 «수치 재현성» 이지 «표본 흔들기» 가 아니다(RESUME_0909 §②).
    ⇒ 광선 예산 쪽은 **«격자를 갈았을 때의 민감도»** 로만 부른다. 신뢰구간이 아니다.
  · ⛔광선 수를 바꾸면 경로 수와 **경로당 가중치**가 함께 움직인다
    (field_calculator.py:221 의 4π/samples_per_src). 단일 변수가 아니다.
    ⛔이것을 «솔버의 결함» 으로도 «상쇄되니 괜찮다» 로도 읽지 않는다 — 재 보지 않았다.
  · ⛔D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·후보 탐색
    차이가 함께 들어간다. 「장면이 얹은 몫」으로만 부른다.
  · ⛔expected_* 는 균일·독립 추출을 가정한 참고값이다. 자세는 시각이고 로터 위상
    구조가 있다 — 유의성 검정이 아니다.
  · ⛔실기 계측 대조는 0 건이다.

■ 잣대는 benchmark/read_0918B_0909.py 를 **그대로 가져다 쓴다**(import). 새로 만들지 않는다.

쓰는 법 (⛔CPU 전용 · 코어를 묶는다):
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/read_canyonnull_0910.py
"""
from __future__ import annotations
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    if len(os.sched_getaffinity(0)) > 8:
        os.sched_setaffinity(0, set(range(8, 12)))
except Exception:
    pass
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

import numpy as np                                    # noqa: E402
from read_0918B_0909 import measure, DEV, CAP         # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "read_canyonnull_0910.json")
MESH = "mfixbatteryi5_blperairframe"
ARM, ENV = "R0D0E0F1", "sionna:simple_street_canyon"
ENVTAG = "envsionna-simple_street_canyon"
ELS = (-30.0, -60.0)
#: (이름, spp, rep) — ⛔«널» 이라 부르지 않는다
CELLS = [("기준선 (4e9)",           4_000_000_000, 0),
         ("되풀이 1 (같은 설정)",    4_000_000_000, 1),
         ("되풀이 2 (같은 설정)",    4_000_000_000, 2),
         ("격자 3.8e9 (−5 %)",      3_800_000_000, 0),
         ("격자 4.2e9 (+5 %)",      4_200_000_000, 0)]


def stem(spp: int, rep: int, env: bool) -> str:
    """⛔elevation_sweep_md 의 이름 차례를 그대로 — rep 가 env 앞이다(:449-471)."""
    s = f"sionna_p{spp}_sw{ARM}_r15_n8192"
    if rep:
        s += f"_rep{rep}"
    if env:
        s += f"_{ENVTAG}"
    return f"{s}_{MESH}_d2"


def load(name: str, el: float):
    fs = sorted(glob.glob(f"{SHD}/{name}_el{el:+g}_*.npz"))
    if not fs:
        return None, 0
    E, I, P, D = [], [], [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"]); I.append(z["idx"])
        P.append(z["npaths"] if "npaths" in z.files else np.full(z["idx"].shape, -1))
        D.append(z["n_dup"] if "n_dup" in z.files else np.full(z["idx"].shape, -1))
    o = np.argsort(np.concatenate(I))
    return dict(E=np.concatenate(E)[o], npaths=np.concatenate(P)[o],
                n_dup=np.concatenate(D)[o], n_shards=len(fs),
                trunc=[], files=[os.path.basename(f) for f in fs]), len(fs)


def main() -> int:
    out = {"_meta": {"made": "benchmark/read_canyonnull_0910.py",
                     "scene": ENV, "arm": ARM, "range_m": 15, "depth": 2,
                     "n_poses": 8192, "dev_rule": DEV, "path_cap": CAP,
                     "what_ko": "협곡에서 «아무것도 안 바꿨을 때» 사건 목록이 얼마나 흔들리나",
                     "naming_ko": ("⛔«널» 이라 부르지 않는다 — 초기 광선은 씨앗 없는 결정적 "
                                   "피보나치 격자다. 되풀이는 «수치 재현성», 예산 변경은 "
                                   "«격자를 갈았을 때의 민감도» 다.")},
           "by_el": {}}
    for el in ELS:
        print(f"\n■ 앙각 {el:+g} · 협곡 · 팔 {ARM} · 깊이 2 · 잣대 DEV={DEV}")
        flags, cells, missing = {}, {}, []
        for nm, spp, rep in CELLS:
            sc, ns = load(stem(spp, rep, True), el)
            fr, nf = load(stem(spp, rep, False), el)
            if sc is None or fr is None or ns < 2 or nf < 2:
                missing.append(dict(cell=nm, scene_shards=ns, free_shards=nf))
                print(f"  ⏳{nm:<24} 샤드 부족 (협곡 {ns} · 빈하늘 {nf}) — 건너뛴다")
                continue
            if sc["E"].size != fr["E"].size:
                missing.append(dict(cell=nm, why="자세 수 불일치")); continue
            r = measure(fr, sc)
            if r is None:
                missing.append(dict(cell=nm, why="measure 실패")); continue
            flags[nm] = r.pop("_flag")
            r["files_scene"] = sc["files"]
            cells[nm] = r
            print(f"  {nm:<24} 사건 {r['n_static_changed']:>4} ({r['share_pct']:>5} %)"
                  f" · 경로중앙 {r.get('npaths_median')}"
                  f"{'  ⛔상한' if r.get('at_path_cap') else ''}", flush=True)
        base = "기준선 (4e9)"
        pairs = {}
        if base in flags:
            fb = flags[base]; nb = int(fb.sum())
            print(f"\n  기준선 사건 {nb} 개 — 그 중 몇 개가 살아남나")
            print(f"    {'칸':<24}{'남음':>6}{'잃음':>6}{'새로':>6}{'자카드':>9}{'기대 자카드':>12}")
            for nm, fa in flags.items():
                if fa.size != fb.size:
                    continue
                inter = int((fa & fb).sum()); uni = int((fa | fb).sum())
                na = int(fa.sum()); e = na * nb / fa.size
                pairs[nm] = dict(n_a=na, n_b=nb, n_intersect=inter,
                                 kept=inter, lost=int((fb & ~fa).sum()),
                                 brand_new=int((~fb & fa).sum()),
                                 jaccard=round(inter / max(uni, 1), 4),
                                 expected_intersect_if_unrelated=round(e, 3),
                                 expected_jaccard_if_unrelated=round(e / max(na + nb - e, 1e-9), 5))
                p = pairs[nm]
                print(f"    {nm:<24}{p['kept']:>6}{p['lost']:>6}{p['brand_new']:>6}"
                      f"{p['jaccard']:>9.4f}{p['expected_jaccard_if_unrelated']:>12.5f}")
        out["by_el"][f"{el:+g}"] = dict(cells=cells, pairs=pairs, missing=missing,
                                        baseline_events=(int(flags[base].sum())
                                                         if base in flags else None))
    out["limits_ko"] = [
        "⛔«널» 이 아니다 — 초기 광선은 씨앗 없는 결정적 피보나치 격자다"
        "(sionna/rt/utils/ray_tracing.py:24-30). 되풀이가 1.000 이면 «수치 재현성» 이고, "
        "예산 변경은 «격자를 갈았을 때의 민감도» 다. 두 점은 신뢰구간이 아니다.",
        "⛔광선 수를 바꾸면 경로 수와 경로당 가중치가 함께 움직인다"
        "(field_calculator.py:221). 단일 변수가 아니다. ⛔이것을 «솔버의 결함» 으로도 "
        "«상쇄되니 괜찮다» 로도 읽지 않는다 — 재 보지 않았다.",
        "⛔D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·후보 "
        "탐색 차이가 함께 들어간다.",
        "⛔expected_* 는 균일·독립 추출을 가정한 참고값이다 — 유의성 검정이 아니다.",
        "⛔잣대 DEV=0.5 는 자유 파라미터다. 다른 값에서 수가 달라진다.",
        "⛔실기 계측 대조는 0 건이다."]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n  원장 → {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
