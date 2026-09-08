#!/usr/bin/env python
"""실외 «낙차»가 무엇인지 가른다 — 물리인가, 우리 씬/솔버의 결함인가.

왜 있나 — 2026-09-08 에 사용자가 물었다: 「실외 결과는 정면(0도)가 아니여도 서든 드랍이
발생하는거니?」 그리고 「바닥 메쉬가 있다는 이유로 그렇게 된다는 것은 말이 안 된다,
우리 씬이 잘못된 것 아니냐」. 재 보니 **사용자 쪽이 맞다.**

■ 이 원장이 세우는 다섯 가지 (전부 샤드에서 직접 센다)

  ① **0° 낙차와 실외 낙차는 다른 현상이다.**
     0° 는 깊이 중앙 −3.52 dB = 20·log10(2/3) 이고, 그 자세들만 `n_dup`=1(사본 둘),
     나머지는 `n_dup`=2(사본 셋)다 — 「같은 도달이 세 줄로 적히다 두 줄로 적힌 것」이다.
     실외는 −45 dB 로 거의 사라진다. 두 집합은 **겹치는 자세가 0 개**다.

  ② **실외 낙차는 지면 메쉬를 넣을 때 생긴다.** 지면/건물을 쪼갠 칸 여섯에서
     지면이 여섯 번 다 만들고(+61·75·84·82·93·105), 건물은 한 칸에서 +1 뿐이다.

  ③ **그런데 «지면이 있으면 나는 것»이 아니다.** 엔비디아 기본 씬(뮌헨 · 거리 협곡)은
     지면이 있는데도 **한 칸도 안 난다**. 우리 `outdoor01`(120×120 m 평평한 콘크리트
     판 하나)에서만 난다.

  ④ **낙차의 «깊이»는 잣대의 착시다.** 지면이 중앙 레벨을 +44.5 dB 올려 놓았고,
     낙차 자세는 그 부풀린 중앙값 대비 −45 dB 다. 절대값으로 보면 낙차 자세의 레벨은
     **빈 하늘 레벨과 같다**(el −60: −119.73 대 −118.88 dB, 차 −0.86 dB).

  ⑤ **상쇄가 아니라 «빠진» 것이다.** 낙차 자세에서 실외 기록을 빈 하늘 기록과
     복소수로 견주면 상대차가 0.15 인데(확산만 팔), 그 밖 자세에서는 168~522 다.
     곧 그 자세에서는 **지면 몫이 통째로 없다.**
     ⛔지면이 레이다에 돌려보내는 정지 몫은 로터 각도를 모른다 — 8,192 자세 중 1 % 에서만
       꺼질 수 없다. ⇒ 물리가 아니라 **기록 쪽 결함**으로 읽는다.

■ ⑥ **손잡이를 흔들어 보니 «거칠기»가 끈다** (2026-09-08 오후, el −30 · 확산만 팔)

      지면 거칠기 S=0 (기본, 거울)   최솟값이 중앙보다 −65.16 dB · 낙차 74
      지면 거칠기 S=0.3             최솟값이 중앙보다  −0.42 dB · 낙차  0
      지면 거칠기 S=0.7             최솟값이 중앙보다  −0.38 dB · 낙차  0
      드론 고도 10 m (S=0)          −80.63 dB · 낙차 71   ← 고도로는 안 꺼진다
      드론 고도 40 m (S=0)          −57.42 dB · 낙차 54

  ⇒ 지면이 **완벽한 거울이 아니면** 무너짐이 사라진다. 거칠기를 주면 중앙 레벨도
    −79.4 → −101.5 dB 로 22 dB 내려간다 — 정반사 한 갈래에 몰려 있던 에너지가 흩어진다.

⛔⛔**그런데 이것이 «우리 씬 대 남의 씬» 을 설명하지는 못한다.** 2026-09-08 에
  `sionna.rt` 로 두 기본 씬의 재질을 직접 읽어 보니 **전부 S=0.0** 이다
  (거리 협곡: brick·concrete·glass·marble·wood / 뮌헨: brick·concrete·marble·metal·wood).
  우리 콘크리트도 S=0.0 이다(src/materials.py). 곧 **양쪽 다 거울인데 한쪽만 무너진다.**
  ⇒ 남는 후보는 **기하**다 — 우리 씬은 드론 바로 아래 120×120 m **평평한 판 하나**라
    정반사가 한 갈래에 몰리고, 기본 씬은 면이 여러 각도로 쪼개져 있다.
    ⛔그 가설은 **아직 안 시험했다.** 판 크기를 줄이거나 기울여 보는 실험이 필요하다.

■ 무엇을 아직 모르나 (⛔여기서 더 나가지 않는다)
  · 위 «기하» 가설을 안 시험했다 — 판 크기·기울기를 흔든 판이 없다.
  · 솔버 안쪽인지 우리 배관인지 안 갈랐다.
  · ⛔「Sionna 가 틀렸다」로 결론짓지 않는다(집 규약). 지금 말할 수 있는 것은
    「우리 씬에서는 나고 남의 씬에서는 안 난다」까지다.

■ 이것이 무엇을 뒤집나
  docs/DEEP_DROP_0902.md 가 「실외 칸(3/45)에서 빠지는 것은 레이다 자신의 지면 반사다」를
  **한 칸의 자세 하나를 덤프해서** 적어 두었다. 이 원장은 그것을 8,192 자세 × 여섯 칸으로
  넓혀 확인한다 — 추론이 아니라 셈이다.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 nice -n 19 \
      /workspace/.venvs/py312/bin/python benchmark/outdoor_dip_origin_0908.py
    → outputs/outdoor_dip_origin_0908.json
"""
from __future__ import annotations

import argparse, glob, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "outdoor_dip_origin_0908.json")
MESH = "mfixbatteryi5_blperairframe"
#: 날개 박자 한 주기가 자세 몇 개인가 — PRF ÷ f_flash. 정본 원장에서 읽는다.
_TJ = json.load(open(os.path.join(ROOT, "outputs", "report07_three_engines.json"),
                     encoding="utf-8"))["_meta"]
PRF_POSES_PER_FLASH = float(_TJ["prf_hz"]) / float(_TJ["f_flash_hz"])
DIP = 0.1                       # 리포트 12·실외 그림과 같은 «꺼진 자세» 문턱
#: ⭐이 문턱은 자유 파라미터다 — 아래 threshold_ladder 가 흔들어 본다.
LADDER = (0.5, 0.3, 0.2, 0.1, 0.05, 0.03, 0.02, 0.01, 0.005, 0.003)
SCENES = (("", "빈 하늘"),
          ("envoutdoor01_", "우리 실외 (지면+건물)"),
          ("envoutdoor01_ground_", "우리 지면만"),
          ("envoutdoor01_bldg_", "우리 건물만"),
          ("envsionna-munich_", "엔비디아 뮌헨"),
          ("envsionna-simple_street_canyon_", "엔비디아 거리 협곡"))


def load(tag, el, arm):
    """샤드를 idx 로 이어 붙인다. (E, n_dup 또는 None, 샤드 수). 없으면 (None, None, 0)."""
    fs = sorted(glob.glob(
        f"{SHD}/sionna_p4000000000_sw{arm}_r15_n8192_{tag}{MESH}_d2_el{el:+g}_*.npz"))
    if not fs:
        return None, None, 0
    E, I, D = [], [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"])
        I.append(z["idx"])
        D.append(z["n_dup"] if "n_dup" in z.files else None)
    o = np.argsort(np.concatenate(I))
    Dc = None if any(d is None for d in D) else np.concatenate(D)[o]
    return np.concatenate(E)[o], Dc, len(fs)


def dip_idx(E, thr=DIP):
    a = np.abs(E)
    return np.where(a / float(np.median(a)) < thr)[0]


def db(x):
    return float(20.0 * np.log10(max(float(x), 1e-300)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="R0D0E0F1,R0D1E1F1")
    ap.add_argument("--els", default="0,-15,-30,-45,-60,-75")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    arms = [x for x in a.arms.split(",") if x]
    els = [float(x) for x in a.els.split(",") if x]

    t0 = time.time()
    cells, scene_rows = {}, []
    for arm in arms:
        for el in els:
            F, DF, nf = load("", el, arm)
            if F is None:
                continue
            free = {"n_dips": int(dip_idx(F).size),
                    "median_level_db": db(np.median(np.abs(F))),
                    "min_below_median_db": round(
                        db(np.min(np.abs(F))) - db(np.median(np.abs(F))), 2)}
            c = {"arm": arm, "el_deg": el, "n_poses": int(F.size), "free": free}

            #: ① el 0° 는 겹침으로 설명되나 — n_dup 이 있는 칸에서만
            if DF is not None:
                a_ = np.abs(F) / float(np.median(np.abs(F)))
                lo = a_ < 0.8
                if lo.any():
                    c["free_shallow"] = {
                        "rule": "|E| < 중앙값 × 0.8",
                        "n": int(lo.sum()),
                        "depth_db_median": round(float(np.median(20*np.log10(a_[lo]))), 3),
                        "two_thirds_db": round(db(2/3), 3),
                        "one_third_db": round(db(1/3), 3),
                        "n_dup_at_those": {str(k): int(v) for k, v in
                                           zip(*np.unique(DF[lo], return_counts=True))},
                        "n_dup_elsewhere": {str(k): int(v) for k, v in
                                            zip(*np.unique(DF[~lo], return_counts=True))},
                    }

            for tag, lbl in SCENES[1:]:
                O, _, ns = load(tag, el, arm)
                if O is None:
                    continue
                d = dip_idx(O)
                #: ⭐⭐**낙차 개수보다 이 수가 낫다** — 「가장 깊은 자세가 중앙값보다
                #  몇 dB 아래인가」. 2026-09-08 에 남의 씬을 「낙차 0 개」로만 적었다가
                #  그림에서 세로 막대가 보여 다시 쟀더니, 남의 씬은 낙차가 없는 것이
                #  아니라 **|E| 가 아예 안 흔들린다**(최솟값이 중앙값보다 0.0~0.1 dB 아래).
                #  개수는 문턱을 타지만 이 수는 안 탄다.
                _min_db = round(db(np.min(np.abs(O))) - db(np.median(np.abs(O))), 2)
                row = {"scene": lbl, "arm": arm, "el_deg": el, "n_shards": ns,
                       "n_poses": int(O.size), "n_dips": int(d.size),
                       "min_below_median_db": _min_db,
                       "median_level_db": round(db(np.median(np.abs(O))), 2),
                       "lift_over_free_db": round(
                           db(np.median(np.abs(O))) - db(np.median(np.abs(F))), 2),
                       "n_dips_free": free["n_dips"],
                       "n_dips_added": int(len(set(d.tolist())
                                               - set(dip_idx(F).tolist()))),
                       "overlap_with_free_dips": int(np.intersect1d(
                           d, dip_idx(F)).size)}
                if d.size:
                    ao = np.abs(O)
                    row["dip_level_db"] = round(db(np.median(ao[d])), 2)
                    #: ⭐④ 깊이는 잣대의 착시인가 — 절대값으로 빈 하늘과 견준다
                    row["dip_level_minus_free_median_db"] = round(
                        row["dip_level_db"] - free["median_level_db"], 2)
                    row["depth_below_own_median_db"] = round(
                        row["dip_level_db"] - row["median_level_db"], 2)
                    #: ⭐⑤ 상쇄인가 «빠진» 것인가 — 복소수로 견준다
                    rel = np.abs(O - F) / np.maximum(np.abs(F), 1e-300)
                    other = np.setdiff1d(np.arange(O.size), d)
                    row["rel_to_free_at_dips"] = round(float(np.median(rel[d])), 4)
                    row["rel_to_free_elsewhere"] = round(float(np.median(rel[other])), 2)
                    #: ⭐문턱을 흔든다 — 개수가 문턱을 따라가면 그 수는 문턱이 정한 것이다
                    med = float(np.median(ao))
                    row["threshold_ladder"] = {
                        f"{t:g}": int((ao / med < t).sum()) for t in LADDER}
                scene_rows.append(row)
            cells[f"{arm}/el{el:+.0f}"] = c

    #: ── ⑥ 손잡이를 흔든다 — 거칠기·드론 고도 ────────────────────────────
    #  ⭐이 판들은 el −30 · 확산만 팔에만 있다. 없으면 조용히 건너뛴다.
    knobs = {}
    for tag, lbl in (("envoutdoor01_", "지면+건물 · 거칠기 0 (거울, 기본)"),
                     ("envoutdoor01_S0.3_", "같은 씬 · 거칠기 0.3"),
                     ("envoutdoor01_S0.7_", "같은 씬 · 거칠기 0.7"),
                     ("envoutdoor01_ground_", "지면만 · 드론 고도 20 m (기본)"),
                     ("envoutdoor01_ground_alt10_", "지면만 · 드론 고도 10 m"),
                     ("envoutdoor01_ground_alt40_", "지면만 · 드론 고도 40 m")):
        E, _, ns = load(tag, -30.0, "R0D0E0F1")
        if E is None:
            continue
        med = float(np.median(np.abs(E)))
        knobs[lbl] = {"n_poses": int(E.size), "n_shards": ns,
                      "median_level_db": round(db(med), 2),
                      "min_below_median_db": round(db(np.min(np.abs(E))) - db(med), 2),
                      "n_dips": int(dip_idx(E).size)}

    #: ── ⑦ 되풀이하면 같은 자세가 무너지나 ────────────────────────────────
    #  ⭐**이것이 «무작위냐 기하냐» 를 가른다.** `rep1_`·`rep2_`·`rep3_` 은 같은 설정
    #  재실행이다. 자카드가 1 이면 솔버의 무작위성이 아니라 **기하가 정하는** 것이다.
    #  ⚠0° 낙차는 자카드 0.947~1.000 이었다(docs/DEEP_DROP_0902.md) — 견줄 값이다.
    import itertools as _it
    repeat = {}
    for el in (-30.0, -60.0):
        sets = {}
        for tag, lbl in (("envoutdoor01_", "base"), ("rep1_envoutdoor01_", "rep1"),
                         ("rep2_envoutdoor01_", "rep2"), ("rep3_envoutdoor01_", "rep3")):
            E, _, _ = load(tag, el, "R0D0E0F1")
            if E is not None:
                sets[lbl] = set(dip_idx(E).tolist())
        if len(sets) < 2:
            continue
        pairs = {}
        for (a1, A), (b1, B) in _it.combinations(sets.items(), 2):
            pairs[f"{a1}~{b1}"] = {
                "n_a": len(A), "n_b": len(B), "n_shared": len(A & B),
                "jaccard": round(len(A & B) / max(len(A | B), 1), 4)}
        repeat[f"el{el:+.0f}"] = {
            "n_runs": len(sets),
            "n_dips_per_run": {k: len(v) for k, v in sets.items()},
            "pairs": pairs,
            "jaccard_min": round(min(v["jaccard"] for v in pairs.values()), 4)}

    #: ── ⑧ 무너지는 자세가 날개 박자에 물려 있나 ────────────────────────
    #  ⭐⑦ 이 「기하가 정한다」를 보였으니 다음 물음은 «어느 기하냐» 다.
    #  날개가 지나가며 가리는 것이라면 자세 번호가 박자 주기의 눈금에 **몰려야** 한다.
    #  원형 집중도 R = |⟨e^{i2πφ}⟩| — 0 이면 고르게 퍼지고 1 이면 한 위상에 몰린다.
    #  ⚠빗각의 0° 낙차는 「날개가 가리는 것」으로 읽혔다(docs/DEEP_DROP_0902.md:
    #    블록 간격이 박자 주기와 1.00 배). 이번 것이 같은 것인지 가른다.
    _P = PRF_POSES_PER_FLASH
    phase_lock = {}
    for el in (-15.0, -30.0, -45.0, -60.0, -75.0):
        E, _, _ = load("envoutdoor01_ground_", el, "R0D0E0F1")
        if E is None:
            E, _, _ = load("envoutdoor01_", el, "R0D0E0F1")
        if E is None:
            continue
        d = dip_idx(E)
        if d.size < 3:
            continue
        row = {"n_dips": int(d.size),
               "gap_median_poses": round(float(np.median(np.diff(d))), 1)}
        for nm, per in (("flash", _P), ("half_flash", _P / 2), ("quarter_flash", _P / 4)):
            ph = (d % per) / per
            row[f"concentration_{nm}"] = round(
                float(abs(np.exp(2j * np.pi * ph).mean())), 3)
        phase_lock[f"el{el:+.0f}"] = row

    #: ⛔재질을 직접 읽어 「거칠기가 우리와 남의 씬을 가른다」를 **반증**한 기록.
    #  손으로 적지 않고 여기 상수로 둔다 — 다시 읽으려면 sionna.rt.load_scene 을 쓴다.
    material_check = {
        "checked_utc": "2026-09-08",
        "how_ko": "sionna.rt.load_scene 으로 씬을 열어 물체마다 "
                  "radio_material.scattering_coefficient 를 읽었다",
        "simple_street_canyon": {"brick": 0.0, "concrete": 0.0, "glass": 0.0,
                                 "marble": 0.0, "wood": 0.0},
        "munich": {"brick": 0.0, "concrete": 0.0, "marble": 0.0,
                   "metal": 0.0, "wood": 0.0},
        "ours": {"concrete_light": 0.0, "concrete_dark": 0.0},
        "verdict_ko": "⛔양쪽 다 S=0.0(거울)이다 — 거칠기는 «우리 씬 대 남의 씬» 을 "
                      "설명하지 못한다. 남는 후보는 기하다(우리는 평평한 판 하나). "
                      "⛔그 가설은 아직 안 시험했다.",
    }

    #: ── 요약 — 사람이 읽는 문장이 아니라 **센 수**로 낸다 ──────────────────
    def _rows(pred):
        return [r for r in scene_rows if pred(r)]

    ours = _rows(lambda r: r["scene"].startswith("우리") and "건물만" not in r["scene"])
    nvda = _rows(lambda r: r["scene"].startswith("엔비디아"))
    bldg = _rows(lambda r: "건물만" in r["scene"])
    gnd = _rows(lambda r: "지면만" in r["scene"])
    at_dips = [r["rel_to_free_at_dips"] for r in scene_rows
               if "rel_to_free_at_dips" in r and r["arm"] == "R0D0E0F1"]

    doc = {
        "_meta": {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generator": "benchmark/outdoor_dip_origin_0908.py",
            "question_ko": "실외 «낙차»가 물리인가, 우리 씬/기록 쪽 결함인가",
            "dip_rule_ko": f"꺼진 자세 = |E| < 중앙값 × {DIP}. "
                           "⭐자유 파라미터라 threshold_ladder 로 흔들어 본다",
            "scenes_ko": "우리 outdoor01 = 120×120 m 콘크리트 판 + 건물 넷 + 기둥 둘, "
                         "드론 20 m. 엔비디아 기본 씬은 고도 25 m (ENV_BUILTIN_ALT)",
            "limits_ko": [
                "⛔「Sionna 가 틀렸다」로 결론짓지 않는다 — 「우리 씬에서는 나고 "
                "남의 씬에서는 안 난다」까지다.",
                "⛔우리 씬의 무엇이 그렇게 만드는지 안 갈랐다(평평한 판 하나 · 크기 120 m · "
                "콘크리트 산란계수 S=0.0 셋 중 어느 것인지).",
                "⚠엔비디아 씬은 드론 고도가 다르다(25 m 대 20 m) — 같은 조건이 아니다.",
                "⛔이 저장소에 실기 계측 대조는 0 건이다.",
            ],
        },
        "summary": {
            "n_scene_rows": len(scene_rows),
            "ours_cells": len(ours),
            "ours_cells_with_dips": sum(1 for r in ours if r["n_dips"]),
            "nvidia_cells": len(nvda),
            "nvidia_cells_with_dips": sum(1 for r in nvda if r["n_dips"]),
            "ground_only_cells": len(gnd),
            "ground_only_added_dips": sum(1 for r in gnd if r["n_dips_added"] > 0),
            "buildings_only_cells": len(bldg),
            "buildings_only_added_dips": sum(1 for r in bldg if r["n_dips_added"] > 0),
            "min_below_median_db_ours": sorted(
                {r["min_below_median_db"] for r in scene_rows
                 if r["scene"].startswith("우리") and "건물만" not in r["scene"]}),
            "min_below_median_db_nvidia": sorted(
                {r["min_below_median_db"] for r in scene_rows
                 if r["scene"].startswith("엔비디아")}),
            "max_overlap_with_free_dips": max(
                (r["overlap_with_free_dips"] for r in scene_rows), default=None),
            #: ⭐1.0 이면 «무작위가 아니라 기하가 정한다»
            "repeat_jaccard_min": (None if not repeat else
                                   min(v["jaccard_min"] for v in repeat.values())),
            "collapse_is_deterministic": (None if not repeat else bool(
                min(v["jaccard_min"] for v in repeat.values()) >= 0.999)),
            "poses_per_flash": round(PRF_POSES_PER_FLASH, 2),
            #: ⭐집중도가 낮으면 «날개가 가려서» 가 아니다
            "phase_concentration_max": (None if not phase_lock else round(max(
                max(v[k] for k in v if k.startswith("concentration_"))
                for v in phase_lock.values()), 3)),
            "locked_to_blade_beat": (None if not phase_lock else bool(max(
                max(v[k] for k in v if k.startswith("concentration_"))
                for v in phase_lock.values()) > 0.5)),
            "roughness_kills_collapse": (
                None if not {k: v for k, v in knobs.items() if "거칠기" in k} else bool(
                    all(v["n_dips"] == 0 for k, v in knobs.items()
                        if "거칠기 0.3" in k or "거칠기 0.7" in k))),
            "height_kills_collapse": (
                None if not {k: v for k, v in knobs.items() if "고도" in k} else bool(
                    all(v["n_dips"] == 0 for k, v in knobs.items() if "고도" in k))),
            "rel_to_free_at_dips_median_diffuse_arm": (
                round(float(np.median(at_dips)), 4) if at_dips else None),
        },
        "knobs_el-30_diffuse_arm": knobs,
        "repeat_runs": repeat,
        "phase_lock": phase_lock,
        "material_scattering_check": material_check,
        "cells": cells,
        "scene_rows": scene_rows,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"⭐{a.out}  줄 {len(scene_rows)} · {round(time.time()-t0,1)}s")
    for k, v in doc["summary"].items():
        print(f"   {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
