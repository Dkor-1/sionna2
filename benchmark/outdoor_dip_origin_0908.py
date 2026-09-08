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

■ ⑨ ⭐⭐**사슬이 닫혔다 (2026-09-08)** — 지면 몫을 떼어내 봤다

  «장면을 더했을 때의 복소 신호 차» D = (실외 기록) − (빈 하늘 기록) 을 쟀다.
  ⛔**D 를 그대로 «지면 한 경로» 라 부르지 않는다**(2026-09-08 설계 검토 ⑩) — D 에는
    환경 자체 반사뿐 아니라 드론↔환경 다중반사·가림으로 바뀐 드론 경로·탐색 결과 차이도
    들어갈 수 있다. 아래 ⑩(경로 덤프)에서 **직접 목록을 견준 범위**에서만 «누락» 이라 부른다.
  셋을 쟀다:

    ① **지면 몫은 자세를 안 탄다.** 자세평균 대비 둘레 변동이 **−74.0 · −72.2 dB** 다
       (드론 자신은 −5.7 · −11.0 dB 로 크게 흔들린다). 곧 그것은 레이다가 제 지면을
       보는 **상수**이고, 로터가 어디 있든 달라질 이유가 없다.
    ② **무너진 자세에서 그 상수가 −70.0 · −61.4 dB 떨어진다.** 사라진다.
    ③ **상쇄가 아니다.** 무너진 자세에서 |실외|/|빈 하늘| 이 **1.06 · 0.97** 이다 —
       총합이 빈 하늘 값으로 **돌아간다**(상쇄라면 그 비가 훨씬 작아야 한다).
       그리고 그 자세에서 **드론 자신의 반사는 멀쩡하다**(중앙값과 0.6 dB 안).

  ⇒ **자세를 −74 dB 로 안 타는 상수가, 1 % 의 자세에서만 70 dB 떨어진다.**
    물리로는 그럴 수 없다. ⛔**기록 쪽 결함이다.**
    ⚠그리고 그것은 **되풀이된다** — 고정 씨앗 재실행 넷에서 자카드 1.0000(⑦).
      ⛔**2026-09-08 설계 검토가 이 대목을 낮췄다** — 솔버 호출은 씨앗을 고정하므로,
        같은 씨앗·같은 입력에서 집합이 같다는 것은 그 설정의 **반복 재현성**이다.
        결정적인 후보 선택·해시 처리·버퍼 순서도 같은 결과를 낸다.
        ⇒ 「기하가 정한다」로 읽지 않는다. **기하와 후보 처리의 기여는 아직 안 갈랐다.**
        가르려면 로터 자세와 씨앗을 교차하고 CPU/GPU·실행 순서를 따로 기록해야 한다.
    ⚠**검사한 원형 모멘트에서는 강한 위상 집중을 못 찾았다**(⑧, 최대 0.185).
      ⛔«날개 가림이 아니다» 로 넓히지 않는다 — 이 검사는 정해진 몇 주기의 1 차 모멘트만
        본다. 여러 위상에 나뉘어 되풀이되는 사건은 그 모멘트가 상쇄될 수 있다.
        가르려면 날개를 고정하거나 뺀 대조로 그 경로의 가시성을 봐야 한다.

■ ⑩ ⭐⭐⭐**기전이 잡혔다 (2026-09-08 밤) — 사라지는 것은 «경로 딱 하나» 다**

  경로 목록을 직접 덤프해 낙차 자세와 성한 자세를 차집합했다(work/ 아래 pathdump).

    · 우리 씬에서 **드론을 안 거치는 경로는 하나뿐**이다 — 「정반사 → env_ground」.
      성한 자세 1 개 · **낙차 자세 0 개.** 다른 것은 안 없어진다.
    · 그 하나가 곧 샤드 뺄셈으로 나오는 «정적 몫» 이다 — 크기가 일곱 자리까지 같고
      위상도 맞는다(원형집중도 R = 1.000000 · p99/p1 = 1.0006).
    · **그 경로가 무엇인지도 갈렸다** — 레이다가 **제 발밑 지면을 수직으로** 보고
      돌아오는 반사다. 닫힌식과 맞는다:

          |a| = (λ/4π) / (2h) · |Γ_콘크리트|      h = 레이다의 지면 위 높이

      실측/예측이 여섯 앙각 전부에서 **0.998** 이다
      (el 0·−15·−30·−45·−60·−75 에서 0.9982·0.9980·0.9981·0.9984·0.9976·0.9984).
      드론 고도를 10·20·40 m 로 바꾸면 2h 가 5·25·65 m 가 되고 값이 그대로 따라간다.

  ⇒ **솔버가 1 % 의 자세에서 그 한 경로를 못 찾는다.** 드론과 무관한 경로인데
    로터 각도에 따라 찾고 못 찾고가 갈린다. 되풀이해도 같은 자세다(자카드 1.0000).

■ ⛔⛔⛔ **철회 셋 (2026-09-08 밤) — 앞서 이 파일이 적은 것 중 셋이 틀렸다**

  ⛔① 「**우리 씬에서만 난다**」 — **틀렸다.** 레벨 문턱 없이 정적 몫의 변화를 세면
     엔비디아 거리 협곡에서도 같은 일이 **더 자주** 난다:

         우리 실외 el−30   74 / 8192 = 0.90 %   그때 |E| −53.30 dB   (0.1 규칙이 74 잡음)
         거리 협곡 el−30   96 / 8192 = 1.17 %   그때 |E| **+6.86 dB** (0.1 규칙이 0 잡음)
         우리 실외 el−60   84 / 8192 = 1.03 %   그때 |E| −45.35 dB   (84 잡음)
         거리 협곡 el−60  128 / 8192 = 1.56 %   그때 |E| **+1.57 dB** (0 잡음)
         뮌헨            0 / 8192

     협곡은 정적 경로가 **다섯 개**라 그중 바닥 하나가 빠지면 합이 **커진다** —
     그래서 «낙차» 잣대가 원리적으로 못 본다. 우리 씬은 정적 경로가 **하나뿐**이라
     그 하나를 잃으면 전부 잃는다. **씬이 깨진 것이 아니라 씬이 민감한 것이다.**
     ⚠뮌헨은 0 이지만 같은 조건이 아니다 — 레이다가 벽에서 0.27 m 다.

  ⛔② 「**방위 45° 이상에서는 안 난다**」 — **틀렸다.** az 45/60/75/90 에서는 정적 경로가
     **둘**(지면 + env_bldg_a 벽면)이라 지면 하나가 빠져도 |E| 가 4.7~9.5 dB 만 떨어져
     문턱을 못 넘는다. 문턱 없이 세면 az45 87 · az60 74 · az75 78 · az90 77 로
     az0/15/30 의 74/75/86 과 **같은 0.90~1.06 %** 다.

  ⛔③ 「**지면 거칠기가 무너짐을 끈다**」 — **못 잰다.** 그 칸(S=0.3·0.7)은 경로 상한에
     붙어 있다 — 경로 수 중앙이 1,984,860(99.24 %)·1,999,977(100.00 %)이고 기본 칸은
     1,894 다. 상한이 결과를 정하는 축은 접는다(집 규약).
     ⇒ 거칠기를 다시 물으려면 상한을 올려 다시 사야 한다.

■ 무엇을 아직 모르나 (⛔여기서 더 나가지 않는다)
  · **솔버가 왜 그 한 경로를 못 찾나** — 로터 각도가 드론과 무관한 경로의 탐색을
    어떻게 바꾸는지 안 갈랐다. 후보 생성기 안쪽이다.
  · 뮌헨이 0 인 까닭 — 레이다가 벽에서 0.27 m 라 기하가 아예 다르다. 같은 조건으로 못 견줬다.
  · 거칠기 축은 상한 때문에 접었다(철회 ③). 상한을 올려 다시 사야 한다.
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

    #: ── ⑪ ⭐⭐⭐**문턱을 안 쓰는 잣대** — 정적 몫이 «달라진» 자세를 센다 ────────
    #  ⛔레벨 문턱(|E| < 중앙×0.1)은 이 사건을 **원리적으로 못 본다.** 정적 경로가
    #  여럿인 씬에서는 그중 하나가 빠져도 합이 **커질** 수 있기 때문이다(거리 협곡이 그렇다).
    #  ⇒ 레벨이 아니라 **정적 몫 D = 실외 − 빈 하늘** 이 중앙에서 얼마나 벗어났나로 센다.
    #    D 는 성한 자세에서 완전한 상수라(원형집중도 1.000000) 이 잣대가 성립한다.
    branch = {}
    for el in (-30.0, -60.0):
        F, _, _ = load("", el, "R0D0E0F1")
        if F is None:
            continue
        for tag, lbl in (("envoutdoor01_", "우리 실외"),
                         ("envoutdoor01_ground_", "우리 지면만"),
                         ("envsionna-simple_street_canyon_", "거리 협곡"),
                         ("envsionna-munich_", "뮌헨")):
            E, _, _ = load(tag, el, "R0D0E0F1")
            if E is None or E.size != F.size:
                continue
            D = E - F
            med = complex(np.median(D.real), np.median(D.imag))
            #: 정적 몫이 «절반 넘게» 달라진 자세 — 한 갈래가 빠지면 이 문턱을 넉넉히 넘는다
            dev = np.abs(D - med) > 0.5 * abs(med)
            amp = np.abs(E)                       # ⛔`a` 는 argparse 이름이다 — 덮지 않는다
            _n_dip = int((amp / float(np.median(amp)) < DIP).sum())
            branch[f"{lbl}/el{el:+.0f}"] = {
                "scene": lbl, "el_deg": el, "n_poses": int(E.size),
                "n_static_changed": int(dev.sum()),
                "share_pct": round(100.0 * float(dev.mean()), 2),
                #: ⭐그때 레벨이 오르나 내리나 — 이것이 «낙차» 잣대가 보이나 마나를 정한다
                "level_at_events_db": (None if not dev.any() else round(float(
                    db(np.median(amp[dev])) - db(np.median(amp))), 2)),
                "n_caught_by_dip_rule": _n_dip,
                "dip_rule_sees_it": bool(_n_dip > 0),
            }

    #: ── ⑫ ⛔**경로 상한에 붙은 칸은 접는다** ──────────────────────────────
    #  거칠기 칸(S=0.3·0.7)이 상한에 붙어 있다 — 그 칸의 레벨·낙차를 인용하면 안 된다.
    trunc = {}
    for tag, lbl in (("envoutdoor01_", "기본 S=0.0"),
                     ("envoutdoor01_S0.3_", "거칠기 0.3"),
                     ("envoutdoor01_S0.7_", "거칠기 0.7")):
        E, _, ns = load(tag, -30.0, "R0D0E0F1")
        if E is None:
            continue
        fs = sorted(glob.glob(f"{SHD}/sionna_p4000000000_swR0D0E0F1_r15_n8192_"
                              f"{tag}{MESH}_d2_el-30_*.npz"))
        npa = []
        for f in fs:
            z = np.load(f)
            if "npaths" in z.files:
                npa.append(z["npaths"])
        if not npa:
            continue
        npa = np.concatenate(npa)
        cap = 2_000_000
        trunc[lbl] = {"npaths_median": int(np.median(npa)),
                      "npaths_max": int(npa.max()), "cap": cap,
                      "share_of_cap_pct": round(100.0 * float(np.median(npa)) / cap, 2),
                      "at_cap": bool(np.median(npa) >= 0.99 * cap)}

    #: ── ⑨ ⭐⭐**지면 몫을 떼어내 본다** — 이것이 사슬을 닫는다 ─────────────
    #  선형 중첩으로 지면 몫 = (실외 기록) − (빈 하늘 기록) 이다.
    #  ① 그 몫이 자세를 타나 — 자세평균 |⟨E⟩| 대비 둘레 변동 |E−⟨E⟩| 로 잰다.
    #  ② 무너진 자세에서 그 몫이 «0 이 되나»(사라짐) «직접파와 상쇄하나» 를 가른다.
    #     사라짐이면 |실외|/|빈 하늘| ≈ 1, 상쇄면 그 비가 ≪1 이다.
    split = {}
    for el in (-30.0, -60.0):
        F, _, _ = load("", el, "R0D0E0F1")
        G, _, _ = load("envoutdoor01_ground_", el, "R0D0E0F1")
        if F is None or G is None or F.size != G.size:
            continue
        Gc = G - F
        bad = np.abs(G) / float(np.median(np.abs(G))) < DIP
        ok = ~bad
        if not bad.any():
            continue
        v = Gc[ok]
        stat = float(np.abs(v.mean()))
        wob = float(np.median(np.abs(v - v.mean())))
        fv = F[ok]
        fstat = float(np.abs(fv.mean()))
        fwob = float(np.median(np.abs(fv - fv.mean())))
        split[f"el{el:+.0f}"] = {
            "n_dips": int(bad.sum()),
            "ground_term_static_db": round(db(stat), 2),
            "ground_term_wobble_db": round(db(wob), 2),
            #: ⭐이 값이 크게 음수면 지면 몫은 «자세를 안 타는 상수» 다
            "ground_wobble_over_static_db": round(db(wob) - db(stat), 2),
            "drone_wobble_over_static_db": round(db(fwob) - db(max(fstat, 1e-300)), 2),
            "ground_term_at_dips_db": round(db(np.median(np.abs(Gc[bad]))), 2),
            #: ⭐무너진 자세에서 지면 몫이 평소보다 몇 dB 낮나
            "ground_term_drop_at_dips_db": round(
                db(np.median(np.abs(Gc[bad]))) - db(np.median(np.abs(Gc[ok]))), 2),
            #: ⭐1 에 가까우면 «사라진» 것, ≪1 이면 «상쇄» 다
            "out_over_free_at_dips": round(
                float(np.median(np.abs(G[bad]) / np.maximum(np.abs(F[bad]), 1e-300))), 4),
            #: 드론 자신의 반사는 무너진 자세에서도 멀쩡한가
            "free_at_dips_minus_free_median_db": round(
                db(np.median(np.abs(F[bad]))) - db(np.median(np.abs(F))), 2),
        }

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
            #: ⛔이 값도 좁혀야 한다 — «우리 씬에서만» 이 아니라 «우리 씬에서는 레벨로
            #  보인다» 다. 문턱 없는 셈은 threshold_free_branch_count 에 있다.
            #: ⭐1.0 이면 «무작위가 아니라 기하가 정한다»
            "repeat_jaccard_min": (None if not repeat else
                                   min(v["jaccard_min"] for v in repeat.values())),
            "collapse_is_deterministic": (None if not repeat else bool(
                min(v["jaccard_min"] for v in repeat.values()) >= 0.999)),
            #: ⛔⛔**철회 셋** — 이 수들이 앞서 적은 결론을 뒤집는다
            "RETRACTED_ours_only": (None if not branch else bool(any(
                v["n_static_changed"] > 0 for k, v in branch.items()
                if v["scene"].startswith("거리"))) ),
            "branch_events_by_scene": {k: [v["n_static_changed"], v["share_pct"],
                                           v["level_at_events_db"],
                                           v["n_caught_by_dip_rule"]]
                                       for k, v in branch.items()},
            "RETRACTED_roughness_kills": (None if not trunc else bool(any(
                v["at_cap"] for k, v in trunc.items() if "거칠기" in k))),
            "path_cap_share_pct": {k: v["share_of_cap_pct"] for k, v in trunc.items()},
            #: ⭐⭐사슬을 닫는 세 수
            "ground_term_is_static": (None if not split else bool(all(
                v["ground_wobble_over_static_db"] < -40 for v in split.values()))),
            "ground_wobble_over_static_db": (None if not split else
                [v["ground_wobble_over_static_db"] for v in split.values()]),
            "ground_term_drop_at_dips_db": (None if not split else
                [v["ground_term_drop_at_dips_db"] for v in split.values()]),
            "vanishes_not_cancels": (None if not split else bool(all(
                0.8 < v["out_over_free_at_dips"] < 1.25 for v in split.values()))),
            "drone_own_echo_normal_at_dips": (None if not split else bool(all(
                abs(v["free_at_dips_minus_free_median_db"]) < 2.0
                for v in split.values()))),
            "poses_per_flash": round(PRF_POSES_PER_FLASH, 2),
            #: ⭐집중도가 낮으면 «날개가 가려서» 가 아니다
            "phase_concentration_max": (None if not phase_lock else round(max(
                max(v[k] for k in v if k.startswith("concentration_"))
                for v in phase_lock.values()), 3)),
            "locked_to_blade_beat": (None if not phase_lock else bool(max(
                max(v[k] for k in v if k.startswith("concentration_"))
                for v in phase_lock.values()) > 0.5)),
            #: ⛔이 값은 **철회됐다** — 거칠기 칸이 경로 상한에 붙어 있다(path_cap_check).
            #  키를 남기는 것은 옛 판과 견주기 위해서다. ⛔인용하지 마라.
            "RETRACTED_roughness_kills_collapse_do_not_cite": (
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
        "ground_term_split": split,
        "threshold_free_branch_count": branch,
        "path_cap_check": trunc,
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
