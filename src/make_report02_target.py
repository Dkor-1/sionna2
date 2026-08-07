# -*- coding: utf-8 -*-
"""
make_report02_target.py — 리포트 02 「표적 모델」 빌더  →  report02_target.ipynb
============================================================================================
계약서: `docs/REBUILD_2026-07-30.md` (골격 §2, 서술규약 §5 — 2026-07-31 재정립판).
규약 강제는 `src/report_style.py`: 여는 블록은 **한 일 / 결과 / 방법 / 재현**, 닫는 블록은
**다음 단계**(`next_steps`). 이 편이 말하는 것은 "무엇을 했고 그 수치가 얼마인가" 하나다.

이 파일이 하는 일 (한 번 실행하면 셋 다 나온다)
  ① **파생 JSON** `outputs/report02_derived.json` — 리포트가 인용하는데 원본 JSON 에 *값으로*
     들어있지 않은 양들을 여기서 계산해 **디스크에 남긴다**. 손으로 친 숫자를 0개로 만들기 위한
     장치다. 입력·정의·공식을 JSON 안 `_meta` 에 함께 적는다:
       · 기체별 **외접구 반경 r** 과 밴드별 전기적 크기 kr   (메쉬에서 직접)
       · **해석 PO ↔ 정확 Mie** 간극이 1.0 / 0.5 / 0.2 dB 아래로 내려가는 kr (기준해 두 개로)
       · 기체별 **밴드 기울기** dB/GHz (rcs_anchor.json 의 3밴드 방위평균 σ 를 1차 적합)
       · **앵커 원장 요약** — 재보정이 옮긴 양의 범위·패턴 불변량·비교가능성 판정 집계
         (`outputs/sigma_anchor.json` 을 읽어 집계만 한다. 앵커 자체는 `src/sigma_anchor.py`)
       · **모드별 평균 레벨이동** — 세 재보정 모드가 기체별로 μ 의 밴드평균을 몇 dB 옮기는가.
         이 표가 "무엇이 측정에서 오고 무엇이 우리 출력인가" 를 수치로 확정한다.
       · ⭐ **§1 표 넷** — 기하(mesh_gallery) · 사진 대조(mesh_compare_photo) · 공식 CAD
         (mesh_compare_cad) · 재질과 가림(mesh_compare_material). 네 원장을 **집계만** 해서
         표 행으로 만든다. 측정 자체는 `src/viz_mesh_*.py` · `src/viz_cad_compare.py` 가 한다.
       · ⭐ **데이터 시각 원장** `provenance` — 이 편이 읽는 JSON 각각의 생성 시각을 메쉬 소스
         (`src/drone_cad.py` · `src/drones.py` · `src/cadkit.py` · `src/geom.py`)의 최신 편집
         시각과 맞대어 새것/옛것을 판정한다. 옛것은 §6 재실행 표로 간다.
  ② **그림 4장** — 사진 대조 합성 · kr 스윕(+기체 kr) · 밴드 기울기 · σ 결과 합성.
     나머지 4장(갤러리 · 공식 CAD 치수 · 재질 구성 · 조명/그늘)은 메쉬 원장 스크립트가 낸 PNG 다.
  ③ **노트북** `report02_target.ipynb`.

실행
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report02_target.py

읽는 것 (전부 저장소에 이미 있는 실험 산출물)
  outputs/mesh_gallery.json · mesh_compare_photo.json · mesh_compare_cad.json
  outputs/mesh_compare_material.json          ← ⭐ 현재 메쉬에서 다시 잰 원장 넷
  outputs/report2_waveform_rcs.json · report3_rt.json · report6_sbr.json
  outputs/rcs_anchor.json · sigma_anchor.json · sbr_kr_sweep.json · sbr_defect_fixes.json
  outputs/real_cad_compare.json · community_compare.json · phantom4_scan_compare.json

  ⭐ 다른 워크플로가 낸 원장 — **읽기만** 한다(계산도 덮어쓰기도 하지 않는다)
  outputs/facet_count.json · facet_mechanism.json    ← §2 스톡 경로 솔버가 같은 메쉬에서 내는 것
  outputs/runtime_benchmark.json                     ← §2 · §6 같은 카드 런타임
  outputs/p3_ours.json · p3_validation.json          ← §4.5 Phantom 3 눈감기 산출과 봉인 해제
  outputs/ptd_defect_fixes.json · ptd_wiring.json    ← 여는 블록 «모서리 회절» · §6 PTD 행
  outputs/s2r_assets_verify.json                     ← §6 σ 격자 동일설정 재생성 대조

무결성 장치
  · `derive()` 는 밴드 정의를 `rcs_anchor.json:meta.bands` 와 대조하고, 자체 적합한 밴드 기울기를
    `sigma_anchor.json` 이 독립으로 적합한 값과 대조한다. 두 원장의 세대 차이만큼은
    `SLOPE_LEDGER_GAP_MAX_DB_PER_GHZ` 까지 통과시키고(그 값을 §4.2 가 본문에 싣는다),
    그보다 벌어지면 **거기서 멈춘다**.
  · 리포트 숫자는 전부 `report_style.num()`/`table_from()` 을 통과한다 — JSON 을 열어 대조한다.

⚠ GPU 도 Sionna 도 필요 없다. 메쉬 빌드(`drones.build_drone`)와 numpy/scipy 만 쓴다(약 20 초).
"""
from __future__ import annotations

import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                    # noqa: E402
import matplotlib                                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                       # noqa: E402

from report_style import (assert_fig_text, build_notebook, caption,    # noqa: E402
                          code, from_json, header, md, next_steps, table, table_from)
from paper_kit import (HATCHES, PALETTE, attach, cite, cite_ref,       # noqa: E402
                       defence, figure_md, methods, paper_appendix, paper_map,
                       paper_style, save_figure)

C0 = 299792458.0
FIGDIR = os.path.join(_ROOT, "outputs", "figures")
DERIVED = os.path.join(_ROOT, "outputs", "report02_derived.json")
NB_OUT = os.path.join(_ROOT, "report02_target.ipynb")

#: 메쉬를 짓는 소스. 이 넷 중 가장 최근 편집 시각이 "현재 메쉬"의 시각이고, 원장의 신선도를
#: 판정하는 기준선이다(`_provenance`).
MESH_SOURCES = ("src/drone_cad.py", "src/drones.py", "src/cadkit.py", "src/geom.py")

#: 현재 메쉬에서 다시 잰 원장 넷 — §1 의 표와 그림 넷이 전부 여기서 나온다.
J_GALLERY = "outputs/mesh_gallery.json"
J_PHOTO = "outputs/mesh_compare_photo.json"
J_CAD = "outputs/mesh_compare_cad.json"
J_MATERIAL = "outputs/mesh_compare_material.json"

#: ⭐ σ 오차 → 파형 순위 강건성 원장(별도 워크플로 `benchmark/sigma_sensitivity.py` 산출).
#:   §5 가 통째로 여기서 나온다 — 이 편은 집계만 한다.
J_SIGSENS = "outputs/sigma_sensitivity.json"

#: 다른 워크플로가 낸 원장들 — 이 편은 **인용만** 한다(계산·덮어쓰기 없음).
#:   §2  스톡 엔진 실측(경로/정반사·판 크기 불변) · 런타임 벤치
#:   §4.5 Phantom 3 눈감기 산출과 봉인 해제 대조
#:   §6  PTD 배선 상태 · σ 격자 동일설정 재생성 대조
J_FACET_COUNT = "outputs/facet_count.json"
J_FACET_MECH = "outputs/facet_mechanism.json"
J_RUNTIME = "outputs/runtime_benchmark.json"
J_P3_OURS = "outputs/p3_ours.json"
J_P3_VALID = "outputs/p3_validation.json"
J_PTD_FIX = "outputs/ptd_defect_fixes.json"
J_PTD_WIRE = "outputs/ptd_wiring.json"
J_REGEN = "outputs/s2r_assets_verify.json"

#: ⭐ 2026-08-04 라운드가 새로 낸 원장들 — 이 편은 **인용만** 한다.
#:   §3.1a  얇은 판 참값(2D MoM)이 준 PO 유효 하한과 그 파급
#:   §4.6   Phantom 3 상자·정육면체·구 대조군 (같은 눈금 = Yuan θ=90° 복원 실측곡선)
#:   §4.7   Das 네 기체 사전등록 대조와 그 적대 검증
#:   §1·§4.7 형상 정정이 무엇을 낡게 만들었는가 (원장 신선도 단서)
J_P3_V2 = "outputs/p3_validation_v2.json"
J_LOWF_ATK = "outputs/lowfreq_attack.json"
J_LOWF_ANC = "outputs/lowfreq_anchor.json"
J_FLEET = "outputs/das_fleet_validation.json"
J_FLEET_ATK = "outputs/das_fleet_attack.json"
J_MESHFIX = "outputs/meshfix_applied.json"
J_MESHFIX_ATK = "outputs/meshfix_attack.json"

#: 리포트 전체가 쓰는 세 밴드. 값은 rcs_anchor.json:meta.bands 와 같아야 하며 아래서 검사한다.
BANDS = {"LTE": 1.843e9, "5G": 3.500e9, "WiFi": 5.210e9}

#: §1 표에 올리는 기체 순서 — 전기적으로 작은 것부터. mini5pro·matrice4e 가 실측 대상.
DRONE_ORDER = ["mini5pro", "phantom4", "mavic4pro", "matrice4e",
               "typhoonh480", "x500v2", "s1000plus"]

#: 앵커 재보정 모드 — 생산 기준은 `slope_only` 다.
#:
#: ⭐ 이 모드가 옮기는 것은 **주파수 의존성 하나**다. 밴드 비가중 평균 레벨을 축으로 σ(f) 를
#:   회전시키므로 **절대 레벨은 우리 PO 출력 그대로** 남는다(평균 이동 0.00 dB, 아래 `_anchor_modes`
#:   가 JSON 에서 직접 계산해 원장에 적는다). 레벨까지 측정에 맞추는 두 모드는 크기전이 법칙
#:   (L² 또는 L⁴)을 하나 골라야 하고, 그 선택 하나가 기체에 따라 최대 9.50 dB(s1000plus)를 정한다.
#:   측정이 그 대가 없이 제약하는 양은 기울기뿐이므로, 기울기만 받는다.
ANCHOR_MODE = "slope_only"

#: ⭐ 두 앵커 원장(생산 `sigma_anchor.json` ↔ 현재 `rcs_anchor.json`)의 밴드 기울기 격차 **상한**
#:   [dB/GHz]. 같은 세대면 0 이어야 하고, 지금은 생산 원장이 한 세대 앞이라 0 이 아니다.
#:   그 알려진 격차만 통과시키고 **더 벌어지면 빌드를 멈춘다**(`_anchor_ledger`). 사슬을 한 세대로
#:   다시 돌린 뒤에는 이 값을 0 에 가깝게 되돌린다 — 검사를 끄는 스위치로 쓰지 않는다.
SLOPE_LEDGER_GAP_MAX_DB_PER_GHZ = 1.40

#: 세 모드를 표로 싣는 순서와, 각 모드가 옮기는 것 / 그 대가. 숫자는 전부 JSON 에서 계산한다.
ANCHOR_MODES = [
    ("slope_only", "주파수 의존성 A(f) 의 기울기만", "없음 — 크기 가정 0개"),
    ("level_and_slope_L2", "레벨 + 기울기", "크기전이 L² 가정 (σ ∝ 투영면적)"),
    ("level_and_slope_L4", "레벨 + 기울기", "크기전이 L⁴ 가정 (σ ∝ A²/λ²)"),
]


# =========================================================================== #
#  ①  파생값 — 리포트가 인용할 수 있도록 디스크에 남긴다
# =========================================================================== #
def _enclosing_radius(mesh) -> float:
    """**외접구 반경**: bbox 중심에서 가장 먼 정점까지의 거리 [m].

    정의를 하나로 고정하는 것이 목적이다. bbox 대각선의 절반은 빈 모서리까지 세어 과대평가하고,
    최대 치수의 절반은 과소평가한다. 이 정의는 메쉬 정점만으로 결정되어 재현이 쉽다.
    """
    V = np.asarray(mesh.v, float)
    c = 0.5 * (V.min(0) + V.max(0))
    return float(np.linalg.norm(V - c, axis=1).max())


def _po_mie_floor(kr_max=60.0, step=0.01):
    """**해석 PO 기준해**와 **정확 Mie 기준해**의 간극이 임계값 아래로 내려가는 kr.

    둘 다 우리 결과가 아니라 **기준해**다(`benchmark/mie_pec_sphere.py` 파일 머리말).
    반환하는 kr 은 "그 위로는 다시 임계를 넘지 않는" 마지막 교차점 바로 다음 격자점이다.
    """
    from mie_pec_sphere import mie_pec_backscatter_norm, po_sphere_norm
    kr = np.arange(1.0, kr_max + 1e-9, step)
    mie = np.array([mie_pec_backscatter_norm(float(x)) for x in kr])
    po = np.asarray(po_sphere_norm(kr), float)
    d_db = 10.0 * np.log10(po / mie)
    out = {}
    for thr, name in ((1.0, "kr_below_1p0_db"), (0.5, "kr_below_0p5_db"),
                      (0.2, "kr_below_0p2_db")):
        idx = np.where(np.abs(d_db) > thr)[0]
        out[name] = float(kr[idx[-1] + 1])
    lo = (kr >= 1.0) & (kr <= 3.0)
    out["max_abs_db_kr1_to_3"] = float(np.abs(d_db[lo]).max())
    out["grid_step"] = step
    out["kr_scan_max"] = kr_max
    return out, kr, d_db


def _band_slope(anchor):
    """기체별 **밴드 기울기** dB/GHz — 세 밴드의 방위평균 σ(el=0°)를 주파수에 1차 적합."""
    fb = np.array([anchor["meta"]["bands"][k] / 1e9
                   for k in anchor["meta"]["bands"]], float)
    out = {}
    for key, rec in anchor["drones"].items():
        mu = np.array([rec["bands"][b]["el0"]["mean_dbsm"]
                       for b in anchor["meta"]["bands"]], float)
        out[key] = float(np.polyfit(fb, mu, 1)[0])
    return out, [float(x) for x in fb]


def _anchor_modes(sa):
    """세 재보정 모드가 **μ 의 밴드평균을 몇 dB 옮기는가** — 모드 선택의 대가를 수치로 만든다.

    한 기체의 "평균 레벨이동" = 세 밴드 Δ 의 산술평균. `slope_only` 는 정의상 이 값이 0 이다
    (밴드평균을 축으로 회전만 시키므로). 나머지 두 모드는 크기전이 법칙으로 축까지 옮긴다.
    """
    D = sa["drones"]
    spread = {k: D[k]["comparability"]["size_law_spread_db"] for k in DRONE_ORDER}
    worst = max(spread, key=lambda k: spread[k])
    rows = []
    for mode, moves, cost in ANCHOR_MODES:
        if mode.endswith("L4"):     # 크기법칙 선택 하나가 정하는 폭을 대가 칸에 숫자로 싣는다
            cost += f" · L² 와 최대 {spread[worst]:.2f} dB 차 ({D[worst]['name']})"
        mean = {k: float(np.mean(list(D[k]["modes"][mode]["delta_db"].values())))
                for k in DRONE_ORDER}
        lo = min(mean, key=lambda k: mean[k])
        hi = max(mean, key=lambda k: mean[k])
        rows.append({
            "mode": mode + (" (기본)" if mode == ANCHOR_MODE else ""),
            "moves": moves,
            "mean_shift_range_db": (f"{mean[lo]:+.2f} ~ {mean[hi]:+.2f}"
                                    if abs(mean[hi] - mean[lo]) > 5e-3
                                    else f"{abs(mean[hi]):.2f}"),
            "cost": cost,
            "mean_shift_min_db": mean[lo], "mean_shift_min_drone": lo,
            "mean_shift_max_db": mean[hi], "mean_shift_max_drone": hi,
            "mean_shift_abs_max_db": max(abs(v) for v in mean.values()),
            "by_drone_db": mean,
        })

    return {
        "rows": rows,
        "n_airframes": len(DRONE_ORDER),
        "production_mode": ANCHOR_MODE,
        "level_shift_abs_max_db": rows[0]["mean_shift_abs_max_db"],
        "size_law_spread_max_db": spread[worst],
        "size_law_spread_max_drone": worst,
        "size_law_spread_max_name": D[worst]["name"],
        "definition": ("평균 레벨이동 = 세 밴드 delta_db 의 산술평균 [dB], 기체 7종에 대한 "
                       "최소~최대. slope_only 는 밴드 비가중 평균 레벨을 축으로 회전만 "
                       "시키므로 이 값이 0 이다 — 절대 레벨은 우리 PO 출력 그대로 남는다."),
        "why_production": ("레벨까지 앵커에 맞추려면 크기전이 법칙을 하나 골라야 하고, 그 선택이 "
                           f"기체에 따라 최대 {spread[worst]:.2f} dB 를 정한다. 측정이 그 대가 "
                           "없이 제약하는 양은 기울기뿐이므로 기울기만 받는다."),
    }


def _anchor_ledger(sa, slope_ours):
    """`outputs/sigma_anchor.json` 을 **집계만** 한다 — 앵커 계산 자체는 src/sigma_anchor.py.

    담는 것: 재보정이 옮긴 양의 범위(어느 기체·어느 밴드가 최대/최소인가), 각도패턴이
    정말 안 움직였는지(불변량), 비교가능성 판정 집계, 최대 미통제항.
    """
    D = sa["drones"]

    # ── 자체 적합 기울기 ↔ 앵커 모듈의 독립 적합 대조 (어긋나면 멈춘다) ────────────
    #    ⭐ 두 원장의 기체 집합이 갈릴 수 있다 — `rcs_anchor.json` 은 5기체를 새로 냈고
    #       `sigma_anchor.json` 은 7기체 시절 산출이다. 겹치는 기체에서만 대조하고,
    #       겹치지 않은 기체는 **수로 남긴다**(조용히 넘어가면 원장이 거짓말을 한다).
    both = [k for k in D if k in slope_ours]
    assert both, "앵커 두 원장에 겹치는 기체가 없다 — 사슬을 다시 돌려야 한다"
    worst = max(abs(D[k]["slope_ours_3band_db_per_ghz"] - slope_ours[k]) for k in both)
    only_sa = sorted(k for k in D if k not in slope_ours)
    #  ⭐ 두 원장이 **같은 세대**면 이 값이 0 이다. 갈린 폭은 수로 남기고 본문 §4.2 가 든다.
    #     다만 **검사를 끄지는 않는다** — 사슬 재실행 전까지 허용하는 상한을 아래 상수에 적고,
    #     그 위로 벌어지면 빌드를 멈춘다(경고 print 만 두면 원장이 조용히 더 어긋날 수 있다).
    worst_drone = max(both, key=lambda k: abs(D[k]["slope_ours_3band_db_per_ghz"]
                                              - slope_ours[k]))
    if worst >= 1e-6:
        print(f"  ⚠ 앵커 두 원장의 세대가 다르다 — 겹치는 {len(both)}기체에서 밴드 기울기가 "
              f"최대 {worst:.3f} dB/GHz 갈린다 ({worst_drone}). 본문 §4.2 가 이 수를 든다.")
    assert worst <= SLOPE_LEDGER_GAP_MAX_DB_PER_GHZ, (
        f"앵커 두 원장의 밴드 기울기가 허용 상한을 넘었다 — "
        f"{worst:.3f} > {SLOPE_LEDGER_GAP_MAX_DB_PER_GHZ:.3f} dB/GHz ({worst_drone}).\n"
        f"  → 이 상한은 '2026-07-30 세대 생산 원장 ↔ 현재 rcs_anchor' 의 알려진 격차만 "
        f"통과시키려고 적어 둔 값이다. 더 벌어졌다면 사슬(benchmark/rcs_anchor.py → "
        f"src/sigma_anchor.py)을 한 세대로 다시 돌리고 이 상수를 0 에 가깝게 되돌려라.")

    # ── 재보정이 옮긴 양 (밴드별 Δ) ─────────────────────────────────────────────
    cells = [(rec["modes"][ANCHOR_MODE]["delta_db"][b], k, b)
             for k, rec in D.items() for b in rec["modes"][ANCHOR_MODE]["delta_db"]]
    lo, hi = min(cells), max(cells)

    verdicts = {k: rec["comparability"]["verdict"] for k, rec in D.items()}
    n_v = {v: sum(1 for x in verdicts.values() if x == v)
           for v in ("direct", "scaled", "not_comparable")}

    unc = [u for u in sa["uncontrolled"] if u.get("size_db")]
    big = max(unc, key=lambda u: abs(u["size_db"]))

    slope_after = {k: rec["modes"][ANCHOR_MODE]["slope_after_db_per_ghz"]
                   for k, rec in D.items()}
    shape = max(rec["shape_invariance_max_abs_db"] for rec in D.values())

    return {
        "mode": ANCHOR_MODE,
        "mode_note": D[DRONE_ORDER[0]]["modes"][ANCHOR_MODE]["pivot_note"],
        "anchor_id": sa["sources"]["default_anchor"],
        "anchor_platform": sa["sources"]["anchors"][sa["sources"]["default_anchor"]]["platform"],
        "correction_max_db": hi[0], "correction_max_drone": hi[1], "correction_max_band": hi[2],
        "correction_min_db": lo[0], "correction_min_drone": lo[1], "correction_min_band": lo[2],
        "correction_abs_max_db": max(abs(lo[0]), abs(hi[0])),
        "slope_after_db_per_ghz": float(np.mean(list(slope_after.values()))),
        "slope_after_spread_db_per_ghz": float(np.ptp(list(slope_after.values()))),
        "shape_invariance_max_abs_db": shape,
        "verdicts": verdicts,
        "n_direct": n_v["direct"], "n_scaled": n_v["scaled"],
        "n_not_comparable": n_v["not_comparable"],
        "largest_uncontrolled_term": big["term"],
        "largest_uncontrolled_db": abs(float(big["size_db"])),
        "applied_to_kernel": False,
        "applied_note": ("커널(`src/rcs_sbr.py`)은 그대로다. 재보정은 σ 원장(ledger)이고, "
                         "밴드 간 비교는 이 원장 위에서 읽는다(05편)."),
        #  ⭐ 이 두 줄이 앵커의 범위를 확정한다. 생산 모드에서 측정이 옮기는 것은 기울기 하나다.
        "from_measurement": "A(f) 의 주파수 기울기 [dB/GHz]",
        "from_ours": "절대 레벨 A(f)|_mean · 자세 패턴 B₁(φ,θ) · 잔차 분포 B₂",
        "level_shift_mean_abs_max_db": max(
            abs(float(np.mean(list(rec["modes"][ANCHOR_MODE]["delta_db"].values()))))
            for rec in D.values()),
        #  ⭐ 두 앵커 원장의 **세대 차이**를 수로 남긴다(§4.2 가 이 수를 든다).
        "n_slope_crosschecked": len(both),
        "n_in_sigma_anchor_only": len(only_sa),
        "in_sigma_anchor_only": ", ".join(only_sa) if only_sa else "없음",
        "slope_ledger_gap_max_db_per_ghz": float(worst),
        "slope_ledger_gap_max_drone": worst_drone,
        "slope_ledger_source_generation": str(
            sa.get("meta", {}).get("source_anchor_json_generated", "미상")),
    }


# --------------------------------------------------------------------------- #
#  ⭐ §1 의 표 넷 — 현재 메쉬에서 다시 잰 원장 넷을 **집계만** 한다.
#     측정 자체는 src/viz_mesh_gallery.py · viz_mesh_photo.py · viz_cad_compare.py ·
#     viz_mesh_material.py 가 하고, 여기서는 표 행으로 옮겨 담기만 한다.
# --------------------------------------------------------------------------- #
def _load(rel: str) -> dict:
    with open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def _mesh_source_newest() -> tuple[str, str]:
    """메쉬 소스 넷 중 **가장 최근 편집 시각** — (시각, 그 파일)."""
    best = (0.0, "")
    for rel in MESH_SOURCES:
        p = os.path.join(_ROOT, rel)
        if os.path.exists(p):
            best = max(best, (os.path.getmtime(p), rel))
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(best[0])), best[1]


def _stamp_of(rel: str) -> tuple[str, str]:
    """JSON 의 생성 시각 — 안에 적혀 있으면 그 값, 없으면 파일 mtime. (시각, 출처)."""
    p = os.path.join(_ROOT, rel)
    J = _load(rel)
    for a, b in (("_meta", "generated"), ("meta", "generated"),
                 ("meta", "stamp"), ("_meta", "stamp")):
        v = (J.get(a) or {}).get(b) if isinstance(J.get(a), dict) else None
        if isinstance(v, str):
            return v.replace("T", " ")[:19], f"{a}.{b}"
    return (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p))),
            "파일 mtime")


def _mesh_table(G, air) -> dict:
    """기체별 기하 — `outputs/mesh_gallery.json` 을 표 행으로. r 은 우리 계산과 대조한다.

    ⭐ 표의 **모집단은 이 편의 표적 목록**(`DRONE_ORDER`, = `air`)이고, 원장은 값만 준다.
       원장은 정의상 레지스트리 전 기종을 담는다(`viz_mesh_gallery.measure()` 는 부분 계측을
       거부한다) — 그래서 레지스트리에 검증 전용 기체가 들어오면 원장이 먼저 커진다.
       모집단을 원장에서 읽으면 그때 표가 조용히 같이 커진다. 순서만 원장의 크기순을 쓴다.
    """
    rows, worst = [], 0.0
    for k in [k for k in G["order_by_size"] if k in air]:
        g = G["airframes"][k]
        L, W, H = g["lwh_full_mm"]
        worst = max(worst, abs(g["r_encl_m"] - air[k]["r_encl_m"]) / air[k]["r_encl_m"])
        rows.append({
            "airframe": g["label"] + (" ⭐" if k in ("matrice4e", "mini5pro") else ""),
            "lwh_mm": f"{L:.0f} × {W:.0f} × {H:.0f}",
            "weight_g": g["weight_g"], "n_parts": g["n_parts"],
            "n_groups": g["n_groups"], "n_tris": g["n_tris"],
            "r_encl_m": g["r_encl_m"], "kr_5g": g["kr"]["5G"],
        })
    #  같은 정의(외접구 반경)를 두 코드가 따로 계산한다 — 어긋나면 여기서 멈춘다.
    assert worst < 5e-3, f"외접반경이 갤러리 원장과 어긋난다: 최대 {worst:.2%}"
    S = G["size_spread"]
    return {
        "rows": rows, "n": len(rows), "r_crosscheck_max_pct": 100.0 * worst,
        "span_ratio": S["span_ratio"],
        "smallest": G["airframes"][S["smallest"]]["label"],
        "smallest_span_mm": 1e3 * S["smallest_span_m"],
        "largest": G["airframes"][S["largest"]]["label"],
        "largest_span_mm": 1e3 * S["largest_span_m"],
        "n_parts_total": sum(r["n_parts"] for r in rows),
        "n_tris_total": sum(r["n_tris"] for r in rows),
    }


_SIDE_KO = {"mesh only": "메쉬쪽", "photo only": "사진쪽"}


def _photo_table(P) -> dict:
    """사진↔메쉬 실루엣 정합 — 기체별 한 줄. 상한은 자기복제 정합값이다."""
    cal = P["_meta"]["metric_calibration"]
    rows = []
    for k, a in sorted(P["airframes"].items(), key=lambda x: -x[1]["best_iou"]):
        b = a["photos"][a["best_index"]]
        m = b["metrics"]
        top = max(m["blobs"], key=lambda x: x["area_frac"]) if m["blobs"] else None
        ceil = cal[k]["recovered_iou"]
        rows.append({
            "airframe": a["label"] + (" ⭐" if a["measured_airframe"] else ""),
            "n_photo": f"{len(a['photos'])} / {a['n_photos_available']}",
            "iou": a["best_iou"], "ceiling": ceil,
            "pct_of_ceiling": 100.0 * a["best_iou"] / ceil,
            "contour_mm": m["contour_mean_mm"],
            "worst": (f"{top['part']} {top['area_frac']:.0%} "
                      f"{_SIDE_KO.get(top['side'], top['side'])}") if top else "—",
            "key": k, "file": b["file"], "credit": b["credit"],
            "free_gain": b["free_iou_gain"], "free_delta_deg": b["free_delta_deg"],
        })
    lo, hi = min(rows, key=lambda r: r["iou"]), max(rows, key=lambda r: r["iou"])
    sens = cal[rows[0]["key"]]["sensitivity"]["pose_off_deg"]
    return {
        "rows": rows, "n_airframes": len(rows),
        "n_pairs": P["_meta"]["n_pairs"], "n_excluded": len(P["_meta"]["excluded"]),
        "best": hi["airframe"], "best_iou": hi["iou"], "best_pct": hi["pct_of_ceiling"],
        "worst": lo["airframe"], "worst_iou": lo["iou"], "worst_pct": lo["pct_of_ceiling"],
        "contour_min_mm": min(r["contour_mm"] for r in rows),
        "contour_max_mm": max(r["contour_mm"] for r in rows),
        "ceiling_min": min(r["ceiling"] for r in rows),
        "ceiling_max": max(r["ceiling"] for r in rows),
        "iou_at_1deg_pose_error": sens["1.0"],
        "iou_at_2deg_pose_error": sens["2.0"],
        "definition": ("IoU = 두 실루엣의 교집합/합집합. 카메라 자세·원근·배율·위치와 로터별 "
                       "프로펠러 위상을 맞춘 뒤 잰다. 상한 = 같은 파이프라인에 자기 메쉬로 만든 "
                       "가짜 사진을 넣었을 때의 IoU — 암·블레이드가 몇 px 이라 1.0 이 아니다."),
    }


def _cad_table(C) -> dict:
    """공식 CAD 대조 — 어셈블리 셋과 X500 V2 치수 20개의 편차."""
    asm = [{"cad": v["label"], "vendor": v["vendor"],
            "n_instances": v["n_instances"], "n_part_types": v["n_part_types"],
            "maps_to": v["maps_to"] or "—", "note": v["note_ko"]}
           for v in C["official_cad"].values()]
    R = C["x500v2_dimensions"]["rows"]
    d_cad = [r for r in R if r.get("d_cad_pct") is not None]
    d_pub = [r for r in R if r.get("d_pub_pct") is not None]
    wc = max(d_cad, key=lambda r: abs(r["d_cad_pct"]))
    wp = max(d_pub, key=lambda r: abs(r["d_pub_pct"]))
    by_gap = sorted(C["spec_vs_cad"], key=lambda r: -abs(r["d_pct"]))
    floor, floor2 = by_gap[0], by_gap[1]
    return {
        "assemblies": asm, "n_assemblies": len(asm),
        "n_dims": len(R), "n_vs_cad": len(d_cad), "n_vs_published": len(d_pub),
        "worst_vs_cad_pct": abs(wc["d_cad_pct"]), "worst_vs_cad_dim": wc["label"],
        "worst_vs_cad_mm": abs(wc["d_cad_mm"]),
        "worst_vs_published_pct": abs(wp["d_pub_pct"]),
        "worst_vs_published_dim": wp["label"],
        "worst_vs_published_mm": abs(wp["d_pub_mm"]),
        "floor_pct": abs(floor["d_pct"]), "floor_dim": floor["dim"].replace("\n", " "),
        "floor_aircraft": floor["aircraft"], "floor_caveat": floor.get("caveat") or "—",
        "floor_second_pct": abs(floor2["d_pct"]),
        "floor_second_dim": floor2["dim"].replace("\n", " "),
        "floor_second_aircraft": floor2["aircraft"],
        "lambda_5g_mm": C["bands"]["5G"]["lambda_mm"],
        "licence": C["meta"]["licence_note"],
        "note": ("x500v2 메쉬는 이 CAD 에서 뽑은 치수표로 지었다 — CAD 열과의 일치는 "
                 "설계 의도가 메쉬로 실현됐는지의 검사이고, 독립 검증은 발행 제원 열과 "
                 "제조사 CAD↔제원 간극(floor_pct)이다."),
    }


def _material_table(M) -> dict:
    """재질 구성 — 7기체 합산 면적과 Σ|Γ|A 비중. 그림의 표와 같은 수치다."""
    tot, gam = {}, {}
    for a in M["airframes"].values():
        for mat, r in a["materials"].items():
            tot[mat] = tot.get(mat, 0.0) + r["area_m2"]
            gam[mat] = gam.get(mat, 0.0) + r["gamma_area_m2"]
    A, Gs = sum(tot.values()), sum(gam.values())
    rows = []
    for mat in sorted(tot, key=lambda m: -gam[m]):
        d = M["materials"][mat]
        rows.append({
            "material": mat, "groups": ", ".join(d["groups"]),
            "gamma_bulk": d["gamma_bulk_5g"], "gamma_po": d["gamma_po_5g"],
            "area_m2": tot[mat], "area_pct": 100.0 * tot[mat] / A,
            "gamma_pct": 100.0 * gam[mat] / Gs,
        })
    cond = [r for r in rows if r["gamma_po"] >= 0.8]
    return {
        "rows": rows, "n_materials": len(rows),
        "total_area_m2": A,
        "conducting_area_pct": sum(r["area_pct"] for r in cond),
        "conducting_gamma_pct": sum(r["gamma_pct"] for r in cond),
        "conducting": ", ".join(r["material"] for r in cond),
        "shell_tau_db": abs(M["_meta"]["shell_transmission"]["tau_db"]),
        "gamma_shell": M["_meta"]["shell_transmission"]["gamma_shell"],
        "definition": ("면적 비중 = 그 재질이 차지하는 메쉬 표면적 / 7기체 합계. Σ|Γ|A 비중은 "
                       "같은 면적을 |Γ| 로 가중한 것 — PO 적분 E = Σ|Γ| e^{j2k p·û} d² 에 "
                       "들어가는 양이다(위상 없는 장부이므로 σ 자체는 아니다)."),
    }


def _occlusion_table(M) -> dict:
    """가림이 얼마짜리인가 — 기체별. 전부 현재 메쉬·생산 커널로 잰 값이다."""
    S, meta = M["summary"], M["_meta"]
    rows = []
    for k in M["order_by_area"]:
        a = M["airframes"][k]
        rows.append({
            "airframe": a["label"] + (" ⭐" if a["measured"] else ""),
            "shadow_pct": 100.0 * a["shadow"]["exterior_shadow_frac"],
            "d_occlusion_db": a["sigma"]["d_occlusion_db"],
            "d_shell_db": a["sigma"]["d_shell_transmission_db"],
            "d_total_db": a["sigma"]["d_total_db"],
            "floor_db": a["sigma"]["discretisation_spread_db"],
            "sigma_dbsm": a["sigma"]["sbr_production_dbsm"],
        })
    hi = max(rows, key=lambda r: r["d_occlusion_db"])
    lo = min(rows, key=lambda r: r["d_occlusion_db"])
    return {
        "rows": rows, "n": len(rows),
        "az_deg": meta["aspect"]["az_deg"], "el_deg": meta["aspect"]["el_deg"],
        "n_az_sweep": meta["aspect"]["sweep_n"],
        "fc_ghz": meta["fc_hz"] / 1e9,
        "max_db": hi["d_occlusion_db"], "max_drone": hi["airframe"],
        "min_db": lo["d_occlusion_db"], "min_drone": lo["airframe"],
        "floor_max_db": max(r["floor_db"] for r in rows),
        "shadow_min_pct": min(r["shadow_pct"] for r in rows),
        "shadow_max_pct": max(r["shadow_pct"] for r in rows),
        "n_above_floor": sum(1 for v in S["occlusion_above_noise"].values() if v),
        "engine": meta["visibility"]["engine"],
        "definition": ("가림 [dB] = 가림 없는 PO 방위평균 σ − 불투명 SBR σ. 셸 투과 [dB] 는 "
                       "거기서 유전체 셸을 통과시켜 내부 금속을 코히런트 합산했을 때의 차이. "
                       "합 = 생산 커널과 순수 PO 의 차이. 이산화 바닥은 PO 를 λ/7↔λ/12 로 "
                       "돌렸을 때의 폭이다."),
    }


def _provenance(mesh_newest: str) -> dict:
    """이 편이 읽는 JSON 각각이 **현재 메쉬보다 새것인가**. 옛것은 §6 재실행 표로 간다."""
    used = [
        (J_GALLERY, "§1 기하 표·갤러리 그림"),
        (J_PHOTO, "§1.1 사진 대조"),
        (J_CAD, "§1.2 공식 CAD 치수"),
        (J_MATERIAL, "§1.3 재질 · §2 조명/그늘"),
        ("outputs/phantom4_scan_compare.json", "§1.4 실물 스캔"),
        ("outputs/real_cad_compare.json", "§1.4 실물 CAD"),
        ("outputs/community_compare.json", "§1.4 커뮤니티 메쉬"),
        ("outputs/report6_sbr.json", "§2 커널 게이트"),
        ("outputs/sbr_kr_sweep.json", "§3 기준해 대조 (구 — 기하 무관)"),
        ("outputs/sbr_defect_fixes.json", "§3.2 이면각 · §2.1 상반성"),
        ("outputs/report3_rt.json", "§2 금속 비중"),
        ("outputs/rcs_anchor.json", "§4 밴드 기울기"),
        ("outputs/sigma_anchor.json", "§4 앵커 원장"),
        (J_SIGSENS, "§5 σ 민감도 · 순위 강건성"),
        ("outputs/report2_waveform_rcs.json", "§5 자세 패턴 · 부품 스트립"),
    ]
    rows = []
    for rel, where in used:
        stamp, src = _stamp_of(rel)
        rows.append({"source": rel.replace("outputs/", ""), "stamp": stamp,
                     "stamp_from": src, "fresh": stamp >= mesh_newest, "used_in": where})
    stale = [r for r in rows if not r["fresh"]]
    return {
        "mesh_source_newest": mesh_newest, "rows": rows, "n_sources": len(rows),
        "n_fresh": len(rows) - len(stale), "n_stale": len(stale),
        "stale_sources": [r["source"] for r in stale],
        "oldest_stale": min(stale, key=lambda r: r["stamp"])["stamp"] if stale else "—",
        "rule": ("판정 = JSON 의 생성 시각 ≥ 메쉬 소스 넷의 최신 편집 시각. 옛것으로 나온 "
                 "원장의 수치는 그 시각의 기하로 계산된 값이고, 재실행은 §6 표에 있다."),
    }


def _sigma_sens(SS, air) -> dict:
    """⭐ σ 오차 → 파형 순위 강건성 원장 집계 (`outputs/sigma_sensitivity.json` 을 **집계만** 한다).

    σ 오차를 두 갈래로 나눈다.
      · **공통모드** — 한 기체의 세 밴드를 같은 dB 만큼 옮긴다(절대 레벨 오차가 이 모양이다).
        순위에서 상쇄되고 절대거리만 σ 1 dB 당 약 1/4 dB 움직인다.
      · **차분** — 밴드마다 다르게 옮긴다(주파수 기울기 오차가 이 모양이다). 순위를 정하는 축이고,
        그래서 §4 의 앵커가 잡는 것이 정확히 이 축이다.
    """
    CM, DF, AA = SS["common_mode"], SS["differential"], SS["aspect_averaged"]
    MC, SV = SS["monte_carlo_per_band_error"], SS["size_vs_fragility"]
    CFG, RC = SS["configurations"]["by_config"], SS["ranking_consensus"]
    #  MC 키는 문자열로 저장돼 있다("0.5"·"1.0"…) — 값으로 맞춰 찾는다(표기에 의존하지 않게).
    _mc0 = next(iter(MC["by_drone"].values()))["by_sigma_e_db"]
    lv = [next(k for k in _mc0 if abs(float(k) - float(x)) < 1e-9)
          for x in MC["sigma_e_db_levels"]]
    keys = sorted(SV["by_drone"], key=lambda k: SV["by_drone"][k]["extent_m"])

    rows = []
    for k in keys:
        s, mc = SV["by_drone"][k], MC["by_drone"][k]["by_sigma_e_db"]
        rows.append({
            "airframe": air[k]["name"] + (" ⭐" if k in ("matrice4e", "mini5pro") else ""),
            "key": k, "extent_m": s["extent_m"],
            "d_over_lambda_lte": s["D_over_lambda_lte"],
            "flip_single_db": s["flip_span_single_aspect_db"],
            "flip_aspect_avg_db": s["flip_span_aspect_avg_db"],
            "band_sigma_spread_db": s["max_band_sigma_spread_db"],
            "p_order_1db": mc[lv[1]]["p_order_preserved"],
            "p_order_2db": mc[lv[2]]["p_order_preserved"],
        })

    cfg_keys = ["as_published", "aspect_avg", "aspect_avg_anchored"]
    cfg_ko = {"as_published": "단일자세 (현 헤드라인)",
              "aspect_avg": "자세평균 σ 로 인용",
              "aspect_avg_anchored": "자세평균 + 측정 기울기 앵커"}
    cfg_rows = [{
        "config": cfg_ko[c], "n_orders": CFG[c]["n_distinct_orders"],
        "worst_flip_db": CFG[c]["worst_flip_span_db"],
        "median_flip_db": CFG[c]["median_flip_span_db"],
        "n_flip_inside": CFG[c]["n_drones_flipping_inside_realistic"],
    } for c in cfg_keys]

    lo = min(rows, key=lambda r: r["flip_single_db"])
    hi = max(rows, key=lambda r: r["flip_single_db"])
    p1 = min(rows, key=lambda r: r["p_order_1db"])
    band_ko = {"L1": "LTE", "G1": "5G", "W1": "WiFi"}
    return {
        "rows": rows, "cfg_rows": cfg_rows,
        "n_airframes": len(rows), "n_bands": 3, "n_cells": 3 * len(rows),
        "offset_min_db": min(CM["by_drone"][keys[0]]["offset_db"]),
        "offset_max_db": max(CM["by_drone"][keys[0]]["offset_db"]),
        "order_invariant_everywhere": CM["order_invariant_everywhere"],
        "slope_mean_db_per_db": CM["slope_mean"],
        "slope_min_db_per_db": CM["slope_min"],
        "slope_max_db_per_db": CM["slope_max"],
        "range_at_minus10_pct": CM["abs_range_shift_at_10db_pct"]["minus10"],
        "range_at_plus10_pct": CM["abs_range_shift_at_10db_pct"]["plus10"],
        "realistic_span_db": DF["realistic_span_db"],
        "flip_single_min_db": lo["flip_single_db"], "flip_single_min_name": lo["airframe"],
        "flip_single_max_db": hi["flip_single_db"], "flip_single_max_name": hi["airframe"],
        "n_flip_inside_realistic": DF["n_drones_flipping_inside_realistic"],
        "single_aspect_n_orders": RC["single_aspect_n_distinct"],
        "aspect_avg_n_orders": RC["aspect_avg_n_distinct"],
        "aspect_avg_agree": AA["all_drones_agree"],
        "aspect_avg_order": " > ".join(band_ko[b] for b in AA["consensus_order"]),
        "worst_flip_as_published_db": CFG["as_published"]["worst_flip_span_db"],
        "worst_flip_aspect_avg_db": CFG["aspect_avg"]["worst_flip_span_db"],
        "worst_flip_anchored_db": CFG["aspect_avg_anchored"]["worst_flip_span_db"],
        "anchor_gain_db": (CFG["aspect_avg_anchored"]["worst_flip_span_db"]
                           - CFG["aspect_avg"]["worst_flip_span_db"]),
        "mc_K": MC["K"], "mc_p_min_1db": p1["p_order_1db"],
        "mc_p_min_1db_name": p1["airframe"],
        "sigma_grid_used": SS["reproduction"]["sigma_grid_used"],
        "blade_update_max_range_pct": max(
            abs(v["max_range_change_pct"]) for v in
            SS["staleness_and_mesh_update"]["by_drone"].values()),
        "blade_update_n_orders_changed": SS["staleness_and_mesh_update"]["n_orders_changed"],
        "anchor_not_applied_n_order_changed": SS["scenario_apply_measured_slope"]["n_order_changed"],
        "lambda2_gap_db": abs(SS["gap_decomposition"]["axes_pair_gaps_db"]["W1-L1"]),
        "duty_gap_db": abs(SS["unapplied_duty_axis"]["pair_gaps_db"]["L1-G1"]),
        "snr90_db": SS["_meta"]["snr90_db"],
        "definition": (
            "공통모드 = 한 기체의 세 밴드를 같은 dB 로 옮긴 뒤 R90 순위를 다시 매긴 것. "
            "차분 = 밴드에 따라 다르게 옮긴 것(기울기 오차 모양). 뒤집힘 문턱 = 순위가 처음 "
            "바뀌는 차분 폭 [dB]. 현실 폭 = 우리 생산 기울기와 측정 기울기의 차이가 밴드 스팬 "
            "3.367 GHz 위에서 만드는 dB 폭. MC = 밴드별 독립 N(0, σ_e) 오차에서의 순위 보존 확률."),
        "reads": SS["_meta"]["reads"],
    }


def derive(verbose=True) -> dict:
    """파생 JSON 을 계산해 `outputs/report02_derived.json` 에 쓴다."""
    t0 = time.time()
    import drones                                     # GPU·Sionna 불필요

    anchor = json.load(open(os.path.join(_ROOT, "outputs", "rcs_anchor.json")))
    sa = json.load(open(os.path.join(_ROOT, "outputs", "sigma_anchor.json")))
    # 밴드 정의가 앵커와 어긋나면 여기서 멈춘다 — 조용히 다른 주파수를 쓰는 일이 없도록.
    for short, f in BANDS.items():
        hit = [v for k, v in anchor["meta"]["bands"].items() if k.startswith(short)]
        assert hit and abs(hit[0] - f) < 1e3, f"밴드 불일치: {short} {f} vs {hit}"

    air = {}
    for key in DRONE_ORDER:
        spec = drones.DRONES[key]
        mesh = drones.build_drone(spec)
        r = _enclosing_radius(mesh)
        rec = dict(name=spec.name, n_rotors=int(spec.num_rotors),
                   diagonal_mm=float(spec.diagonal_mm), weight_g=float(spec.weight_g),
                   prop_dia_mm=float(spec.prop_dia_mm), n_tris=int(mesh.n_tris()),
                   n_groups=len(mesh.groups()), r_encl_m=r, release=spec.release)
        for b, f in BANDS.items():
            rec[f"kr_{b}"] = float(2.0 * np.pi * r / (C0 / f))
        air[key] = rec
        if verbose:
            print(f"  {key:12s} r={r:.4f} m  kr(LTE)={rec['kr_LTE']:.2f}")

    krs = [(air[k][f"kr_{b}"], k, b) for k in air for b in BANDS]
    kmin, kmax = min(krs), max(krs)

    floor, kr_grid, d_db = _po_mie_floor()
    # PO 모델 간극이 1 dB 를 넘는(= 기준해 구에서조차 편치 않은) 기체·밴드 조합
    below = [(k, b) for (v, k, b) in krs if v < floor["kr_below_1p0_db"]]

    slope, fb = _band_slope(anchor)
    das = float(anchor["literature"]["mu_eps"]["das_phantom3_mono"]["mu_a"])
    m3d = float(anchor["literature"]["mu_eps"]["yuan_phantom3_azplane"]["mu_a"])
    ratio = {k: v / das for k, v in slope.items()}

    rt = json.load(open(os.path.join(_ROOT, "outputs", "report3_rt.json")))
    A = rt["A_rays"]["rows"]

    #  ⭐ 현재 메쉬에서 다시 잰 원장 넷 → §1 의 표 넷
    mesh_newest, mesh_newest_file = _mesh_source_newest()
    G, P, C, M = (_load(J_GALLERY), _load(J_PHOTO), _load(J_CAD), _load(J_MATERIAL))
    mesh_tbl = _mesh_table(G, air)
    photo_tbl = _photo_table(P)
    cad_tbl = _cad_table(C)
    mat_tbl = _material_table(M)
    occ_tbl = _occlusion_table(M)
    #  ⭐ σ 오차 → 순위 강건성 (별도 워크플로가 낸 원장을 집계만 한다)
    sig_tbl = _sigma_sens(_load(J_SIGSENS), air)
    prov = _provenance(mesh_newest)

    J = {
        "_meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "src/make_report02_target.py :: derive()",
            "purpose": "리포트 02 가 인용하는 파생값. 원본 JSON 에 값으로 없는 것만 담는다.",
            "mesh_source_newest": mesh_newest,
            "mesh_source_newest_file": mesh_newest_file,
            "inputs": [J_GALLERY, J_PHOTO, J_CAD, J_MATERIAL, J_SIGSENS,
                       "outputs/rcs_anchor.json", "outputs/sigma_anchor.json",
                       "outputs/report3_rt.json", "src/drones.py (메쉬 정의)",
                       "benchmark/mie_pec_sphere.py (기준해 두 개)"],
            "definitions": {
                "r_encl_m": "외접구 반경 = bbox 중심에서 가장 먼 메쉬 정점까지의 거리 [m]",
                "kr_*": "2*pi*r_encl/lambda — 밴드 중심주파수 기준 전기적 크기",
                "po_floor": "해석 PO 기준해 / 정확 Mie 기준해 의 dB 차가 임계 아래로 "
                            "내려가는 kr. 둘 다 우리 결과가 아니라 기준해다.",
                "band_slope": "세 밴드(1.843/3.5/5.21 GHz)의 방위평균 sigma(el=0deg)를 "
                              "주파수[GHz]에 1차 적합한 기울기 [dB/GHz]",
                "anchor": "outputs/sigma_anchor.json 의 재보정 원장 집계. 앵커 계산 자체는 "
                          "src/sigma_anchor.py 가 한다.",
                "anchor_modes": "세 재보정 모드의 기체별 평균 레벨이동 [dB]. 생산 모드 "
                                "slope_only 는 0 이다 — 절대 레벨은 우리 PO 출력 그대로다.",
                "mesh": mesh_tbl["rows"] and "outputs/mesh_gallery.json 집계 (§1 기하 표)",
                "photo": photo_tbl["definition"],
                "material": mat_tbl["definition"],
                "occlusion": occ_tbl["definition"],
                "sigma_sens": sig_tbl["definition"],
                "provenance": prov["rule"],
            },
            "runtime_s": None,
        },
        "mesh": mesh_tbl,
        "photo": photo_tbl,
        "cad": cad_tbl,
        "material": mat_tbl,
        "occlusion": occ_tbl,
        "sigma_sens": sig_tbl,
        "provenance": prov,
        "airframes": air,
        "bands_ghz": {k: v / 1e9 for k, v in BANDS.items()},
        "electrical": {
            "n_airframe_band": len(krs),
            "kr_min": kmin[0], "kr_min_drone": kmin[1], "kr_min_band": kmin[2],
            "kr_min_name": air[kmin[1]]["name"],
            "kr_max": kmax[0], "kr_max_drone": kmax[1], "kr_max_band": kmax[2],
            "kr_max_name": air[kmax[1]]["name"],
            "n_below_po_1db": len(below),
            "below_po_1db": [f"{k} @ {b}" for k, b in below],
        },
        "po_floor": floor,
        "band_slope": {
            "fit_bands_ghz": fb, "n_fit": len(fb), "el_deg": 0.0,
            "ours_db_per_ghz": slope,
            "ours_min": min(slope.values()), "ours_min_drone": min(slope, key=slope.get),
            "ours_max": max(slope.values()), "ours_max_drone": max(slope, key=slope.get),
            "lit_das_db_per_ghz": das,
            "lit_mono3d_db_per_ghz": m3d,
            "ratio_vs_das": ratio,
            "ratio_min": min(ratio.values()), "ratio_max": max(ratio.values()),
        },
        "anchor": _anchor_ledger(sa, slope),
        "anchor_modes": _anchor_modes(sa),
        "stock_rt": {
            "coh_climb_db": float(A[-1]["coh_db"] - A[0]["coh_db"]),
            "spp_lo": int(A[0]["spp"]), "spp_hi": int(A[-1]["spp"]),
            "note": "광선을 16배 쏘면 코히런트 합이 이만큼 더 커진다 = 수렴하지 않는다",
        },
    }
    J["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    with open(DERIVED, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    if verbose:
        print(f"  메쉬 소스 최신 편집 {mesh_newest} ({mesh_newest_file}) — 읽는 JSON "
              f"{prov['n_sources']}개 중 새것 {prov['n_fresh']} · 옛것 {prov['n_stale']}"
              + (f" ({', '.join(prov['stale_sources'])})" if prov["n_stale"] else ""))
        print(f"✅ 파생값 저장 → outputs/report02_derived.json ({J['_meta']['runtime_s']} s)")
    return J, kr_grid, d_db


# =========================================================================== #
#  ②  그림 — 글자는 전부 영어(하우스 규약), assert_fig_text 로 검사
#
#  ⭐ 게재 규격(`docs/PAPER_SPEC.md` §4.3): 아래 셋(`fig_reference_gap` · `fig_band_slope` ·
#     `fig_sigma_sensitivity`)은 `paper_kit.save_figure()` 로 **벡터 PDF + 400 dpi PNG** 를
#     함께 내고, 저장 직전에 글자 크기(≥8 pt)와 **색만으로 구분된 계열**을 자체 감사한다.
#     논문 캡션(완결 문장)은 PDF 메타데이터에 실려 `extract_paper_kit()` 이 원고로 옮긴다.
# =========================================================================== #
def _save(fig, name):
    os.makedirs(FIGDIR, exist_ok=True)
    p = os.path.join(FIGDIR, name)
    fig.savefig(p, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  🖼  outputs/figures/{name}")


#: 밴드 코드 → 그림에 찍는 영어 이름. `outputs/sigma_sensitivity.json` 의 키가 이 코드다.
BAND_LABEL = {"L1": "LTE 1.843 GHz", "G1": "5G NR 3.5 GHz", "W1": "WiFi 5.21 GHz"}
BAND_ORDER = ("L1", "G1", "W1")

#: 게재 그림에 싣는 기체 넷 — 실측 2종(⭐)과 대조군 2종(PAPER_SPEC §5 좁히기 1번).
#: 나머지 셋의 수치는 §1.2 표와 `outputs/mesh_compare_photo.json` 에 그대로 있다.
PAPER_AIRFRAMES = ("mini5pro", "matrice4e", "phantom4", "s1000plus")


def _pk_save(fig, stem: str, caption_en: str, placed=7.16) -> dict:
    """게재 규격으로 저장한다 — 벡터 PDF + 400 dpi PNG, 저장 전 자체 감사(PAPER_SPEC §4.3).

    `placed` 는 조판에서 그림이 놓일 폭[in] 이다. 기본값 7.16 in(IEEE 2단 전폭)으로 **축소 후**
    글자 크기를 판정하므로, 저장된 파일이 그대로 원고에 들어가도 8 pt 를 지킨다.
    `caption_en` 은 **논문에 그대로 붙일 완결 문장**이고 PDF 메타데이터에 실려
    `paper_kit.extract_paper_kit()` 이 원고 쪽으로 옮겨 온다.
    """
    out = save_figure(fig, f"outputs/figures/{stem}", dpi=400, caption=caption_en,
                      placed_width_in=placed, close=True)
    a = out["audit"]
    print(f"  🖼  {out['pdf']} + {out['png']} — 최소 글자 {a['min_font_pt']} pt "
          f"(배치 {placed} in 에서 {a.get('effective_min_font_pt')} pt) · "
          f"계열 {a['n_series']} · 색전용 {len(a['colour_only_series'])}건")
    return out


def fig_mesh_photo(J):
    """⭐ 기체 4종 × (사진 위 메쉬 외곽선 · 실루엣 겹침) — 정합·계측은 원장 그대로 쓴다.

    무거운 계산(사진 분할·메쉬 표본·래스터화)은 `src/viz_mesh_photo.py` 의 함수를 그대로
    부른다. 점 개수도 원장을 만든 값(1.2 M)과 같으므로, 여기 그려지는 마스크는 원장의
    IoU 를 만든 **바로 그 마스크**다(재현 확인: 재계산 IoU == 원장 IoU).

    게재 규격(§4.3): 2단 폭 7.16 in 에 4열이라 글자를 10 pt 로 잡는다 — 조판 축소 뒤에도
    8 pt 아래로 내려가지 않게. 판정 수치(IoU · 상한 · 외곽오차)는 제목 줄에 싣는다.
    """
    T = ["photograph with our mesh outline", "silhouettes overlaid",
         "both", "mesh only", "photo only", "measured",
         "IoU after fitting camera pose, perspective, scale and one propeller phase per "
         "rotor; ceiling = the same mesh fitted against a copy of itself."]
    assert_fig_text(*T)
    keep = dict(plt.rcParams)                       # 아래 import 가 폰트를 바꾼다 — 되돌린다
    try:
        import viz_mesh_photo as VP
        P = json.load(open(os.path.join(_ROOT, J_PHOTO)))
        by_key = {r["key"]: r for r in J["photo"]["rows"]}
        rows = [by_key[k] for k in PAPER_AIRFRAMES if k in by_key]
        n = len(rows)
        with paper_style(width="double", base_pt=10.0) as st:
            #  ⚠ 배치는 손으로 잡는다 — 제목·범례가 축 밖으로 나가면 자동 배치가 축을 접는다.
            fig = plt.figure(figsize=(st.width_in, 4.5))
            gs = fig.add_gridspec(2, n, left=0.004, right=0.996, top=0.845,
                                  bottom=0.175, hspace=0.02, wspace=0.02)
            lic = []
            for i, r in enumerate(rows):
                rec = P["airframes"][r["key"]]
                best = rec["photos"][rec["best_index"]]
                c = VP._cache_for(r["key"], best)
                pm, mm = c["photo_mask"], c["mesh_mask"]
                win = VP._view_window(pm, mm)
                if best.get("licence"):
                    lic.append(best["licence"])

                ax = fig.add_subplot(gs[0, i])
                ax.imshow(c["rgb"])
                ax.contour(pm.astype(float), levels=[0.5], colors=[VP.C_PHOTO],
                           linewidths=0.8, linestyles="solid")
                ax.contour(mm.astype(float), levels=[0.5], colors=[VP.C_MESH],
                           linewidths=1.0, linestyles="dashed")
                VP._apply_window(ax, win)
                ax.set_axis_off()
                ax.set_anchor("N")
                ax.set_title(f"{rec['label']}{' *' if rec['measured_airframe'] else ''}\n"
                             f"IoU {r['iou']:.3f} (ceiling {r['ceiling']:.3f})",
                             fontsize=9.5, pad=2)

                ax = fig.add_subplot(gs[1, i])
                rgba = np.zeros(pm.shape + (4,))
                for m, col in ((pm & mm, VP.C_AGREE), (mm & ~pm, VP.C_MESH),
                               (pm & ~mm, VP.C_PHOTO)):
                    rgba[m] = list(matplotlib.colors.to_rgb(col)) + [1.0]
                ax.imshow(rgba)
                VP._apply_window(ax, win)
                ax.set_axis_off()
                ax.set_anchor("N")

            h = [plt.Rectangle((0, 0), 1, 1, color=c) for c in
                 (VP.C_AGREE, VP.C_MESH, VP.C_PHOTO)]
            fig.legend(h, T[2:5], loc="lower center", bbox_to_anchor=(0.5, 0.105),
                       ncol=3, fontsize=9.0, frameon=False)
            #  각주는 100자 안으로 접는다 — 한 줄이 길면 tight bbox 가 그림을 옆으로 늘리고,
            #  그러면 조판 축소에서 글자가 8 pt 아래로 내려간다.
            import textwrap
            foot = (f"top row: {T[0]}   ·   bottom row: {T[1]}   ·   * = {T[5]} in "
                    f"campaign 06.  {T[6]}"
                    + ("  " + "  ".join(sorted(set(lic))) if lic else ""))
            assert_fig_text(foot)
            for j, line in enumerate(textwrap.wrap(foot, width=100)[:3]):
                fig.text(0.5, 0.086 - 0.030 * j, line, ha="center", va="top",
                         fontsize=9.0)
        return _pk_save(
            fig, "report02_f2_mesh_photo",
            "Silhouette overlay of each mesh against a photograph of the real airframe, "
            "fitted for camera pose, perspective, scale and per-rotor propeller phase: "
            f"the intersection-over-union runs from {J['photo']['worst_iou']:.3f} to "
            f"{J['photo']['best_iou']:.3f} against a self-replication ceiling of "
            f"{J['photo']['ceiling_min']:.3f} to {J['photo']['ceiling_max']:.3f} obtained "
            "by feeding the same mesh back through the same pipeline.",
            placed=7.16)
    finally:
        plt.rcParams.update(keep)


def fig_reference_gap(J, kr_grid, d_db):
    """(a) 두 기준해와 우리 커널 · (b) 두 개의 서로 다른 오차 · (c) 일곱 기체가 놓인 kr.

    ⭐ 정확 Mie 와 해석 PO 는 **기준해**다 — 우리 출력이 아니라 과녁이라는 것을 라벨에 박는다.
    """
    T = ["(a) PEC sphere backscatter", "(b) the two gaps, separated",
         "(c) where the seven airframes sit",
         "kr = 2*pi*r/lambda", "sigma / (pi r^2)", "gap [dB]",
         "exact Mie [REFERENCE]", "analytic PO [REFERENCE]", "our SBR+PO kernel",
         "ours - analytic PO (our numerical error)",
         "analytic PO - exact Mie (PO model gap)",
         "1 dB", "0.5 dB", "0.2 dB", "PO model gap > 1 dB",
         "measured in campaign 06"]
    assert_fig_text(*T, *BAND_LABEL.values())

    S = json.load(open(os.path.join(_ROOT, "outputs", "sbr_kr_sweep.json")))
    rows = sorted([r for r in S["rows"] if r["div"] == 16], key=lambda r: r["kr"])
    kr = np.array([r["kr"] for r in rows])
    sb = np.array([r["sigma_sbr_m2"] / (np.pi * r["r_m"] ** 2) for r in rows])
    e_po = np.array([r["db_sbr_over_po"] for r in rows])
    F, A = J["po_floor"], J["airframes"]
    from mie_pec_sphere import mie_pec_backscatter_norm, po_sphere_norm

    with paper_style(width="double", base_pt=10.0) as st:
        fig = plt.figure(figsize=(st.width_in, 5.4), constrained_layout=True)
        gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.92])
        a1, a2, a3 = (fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]),
                      fig.add_subplot(gs[1, :]))

        #  ⚠ 기본 순환(prop_cycle)에 마커가 실려 있다 — 선만 그릴 때는 marker 를 **명시적으로**
        #    꺼야 두 계열이 같은 마커를 물려받아 '색만으로 구분'이 되는 일이 없다.
        kk = np.linspace(1, 100, 2000)
        a1.plot(kk, [mie_pec_backscatter_norm(float(x)) for x in kk], label=T[6],
                color=PALETTE[6], linestyle="-", marker="none")     # black solid
        a1.plot(kk, po_sphere_norm(kk), label=T[7],
                color=PALETTE[1], linestyle="--", marker="none")
        a1.plot(kr, sb, label=T[8], color=PALETTE[0], linestyle="none", marker="o",
                ms=3.6)
        a1.set_xscale("log")
        a1.set_yscale("log")
        a1.set_xlabel(T[3])
        a1.set_ylabel(T[4])
        a1.set_title(T[0])
        a1.legend(loc="lower right")

        a2.axhline(0.0, color="#999999", lw=0.6)
        a2.plot(kr_grid, d_db, label=T[10], color=PALETTE[1], linestyle="--",
                marker="none")
        a2.plot(kr, e_po, label=T[9], color=PALETTE[0], linestyle="-", marker="o",
                ms=3.6, markevery=2)
        for key, lab in (("kr_below_1p0_db", T[11]), ("kr_below_0p5_db", T[12]),
                         ("kr_below_0p2_db", T[13])):
            a2.axvline(F[key], color="#666666", ls=":", lw=0.8)
            a2.text(F[key] * 1.04, -3.6, f"{lab} @ kr={F[key]:.2f}", rotation=90,
                    fontsize=9.0, color="#333333", va="bottom")
        i = int(np.argmax(np.abs(e_po)))
        a2.annotate(f"max |ours - PO| = {abs(e_po[i]):.3f} dB", xy=(kr[i], e_po[i]),
                    xytext=(1.15, -3.5), fontsize=9.0,
                    arrowprops=dict(arrowstyle="->", lw=0.7, color="#333333"))
        a2.set_xscale("log")
        a2.set_xlim(1, 100)
        a2.set_ylim(-4, 4)
        a2.set_xlabel(T[3])
        a2.set_ylabel(T[5])
        a2.set_title(T[1])
        a2.legend(loc="upper left", fontsize=9.0)
        #  ⚠ 로그축 기본 라벨(10^x)의 지수와 보조눈금 라벨은 본문의 0.7배로 그려진다 —
        #    게재 하한(8 pt)을 깨므로 평문 눈금으로 바꾸고 보조 라벨은 끈다.
        plain = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}")
        for ax_ in (a1, a2):
            ax_.xaxis.set_major_formatter(plain)
            ax_.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        a1.set_xticks([1, 3, 10, 30, 100])
        a2.set_xticks([1, 3, 10, 30, 100])
        a1.yaxis.set_major_formatter(plain)
        a1.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())

        keys = DRONE_ORDER
        meas = {"matrice4e", "mini5pro"}
        a3.axvspan(1.0, F["kr_below_1p0_db"], color="#dcdcdc", zorder=0)
        a3.text(np.sqrt(1.0 * F["kr_below_1p0_db"]), len(keys) - 0.55, T[14],
                ha="center", va="center", fontsize=9.0, color="#333333")
        for i, k in enumerate(keys):
            y = len(keys) - 1 - i
            v = [A[k][f"kr_{b}"] for b in BANDS]
            a3.plot([min(v), max(v)], [y, y], color="#999999", lw=0.8, zorder=2)
        for j, (b, lab) in enumerate(zip(BANDS, ("LTE 1.843 GHz", "5G NR 3.5 GHz",
                                                 "WiFi 5.21 GHz"))):
            a3.plot([A[k][f"kr_{b}"] for k in keys],
                    [len(keys) - 1 - i for i in range(len(keys))], label=lab,
                    color=PALETTE[j], linestyle="none", marker=("o", "s", "^")[j],
                    ms=4.4)
        a3.set_yticks(range(len(keys)))
        a3.set_yticklabels([A[k]["name"] + (" *" if k in meas else "")
                            for k in reversed(keys)])
        a3.set_xscale("log")
        a3.set_xlim(1, 100)
        a3.set_ylim(-1.25, len(keys) - 0.15)
        a3.set_xticks([1, 2, 5, 10, 20, 50, 100])
        a3.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        a3.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        a3.set_xlabel(T[3])
        a3.set_title(T[2] + f"   (* = {T[15]})")
        a3.legend(loc="lower left", ncol=3, fontsize=9.0, framealpha=0.95,
                  frameon=True, edgecolor="none")
        a3.grid(axis="x", ls=":", alpha=0.4)

    return _pk_save(
        fig, "report02_f5_reference_gap",
        "Our physical-optics kernel against two closed-form reference solutions on a PEC "
        f"sphere: it tracks the analytic PO reference to within "
        f"{S['summary_div16']['max_abs_db_vs_po']:.3f} dB over kr = 1 to 100 (21 points, 48 "
        f"incidence directions), while the analytic PO reference itself departs from the "
        f"exact Mie solution by more than 1 dB below kr = {F['kr_below_1p0_db']:.2f}, "
        "the band into which one of the twenty-one airframe-band combinations falls.")


def fig_band_slope(J):
    """우리 밴드 기울기가 어디에 있고, 측정 앵커가 그것을 어디로 옮기는가."""
    T = ["Band slope of azimuth-mean sigma, and where the measurement anchor puts it",
         "band slope [dB / GHz]   (fit at 1.843 / 3.5 / 5.21 GHz)",
         "measured: Das, IEEE WCL 2026 (anchor)",
         "measured: Yuan, EuCAP 2025 azimuth plane",
         "after slope_only re-anchoring", "direct", "scaled", "not comparable",
         "comparability to the anchor platform"]
    assert_fig_text(*T)
    B, A, K = J["band_slope"], J["airframes"], J["anchor"]
    keys = sorted(B["ours_db_per_ghz"], key=lambda k: B["ours_db_per_ghz"][k])
    face = {"direct": PALETTE[0], "scaled": PALETTE[4], "not_comparable": PALETTE[1]}
    hat = {"direct": "", "scaled": "//", "not_comparable": "xx"}

    with paper_style(width="double", base_pt=10.0) as st:
        fig, ax = st.figure(height=3.6)
        y = np.arange(len(keys))
        bars = ax.barh(y, [B["ours_db_per_ghz"][k] for k in keys], height=0.62,
                       edgecolor="white", linewidth=0.6)
        for p, k in zip(bars.patches, keys):
            p.set_facecolor(face[K["verdicts"][k]])
            p.set_hatch(hat[K["verdicts"][k]])
        for i, k in enumerate(keys):
            v = B["ours_db_per_ghz"][k]
            ax.annotate("", xy=(K["slope_after_db_per_ghz"], i), xytext=(v, i),
                        arrowprops=dict(arrowstyle="->", lw=0.8, color="#333333"))
            ax.text(v + 0.05, i, f"{v:.2f}  ({B['ratio_vs_das'][k]:.1f}x)",
                    va="center", fontsize=9.0, color="#222222")
        ax.axvline(B["lit_das_db_per_ghz"], color="#000000", lw=1.4, label=T[2])
        ax.axvline(B["lit_mono3d_db_per_ghz"], color="#000000", lw=1.0, ls="--",
                   label=T[3])
        ax.plot([K["slope_after_db_per_ghz"]] * len(keys), y, linestyle="none",
                marker="D", ms=4.5, color=PALETTE[5], label=T[4], zorder=4)
        ax.set_yticks(y)
        ax.set_yticklabels([A[k]["name"] if k in A else k for k in keys])
        ax.set_xlabel(T[1])
        ax.set_xlim(0, max(B["ours_db_per_ghz"].values()) * 2.45)
        ax.set_title(T[0])
        lg = ax.legend(loc="lower right", fontsize=9.0)
        ax.add_artist(lg)
        proxies = [plt.Rectangle((0, 0), 1, 1, facecolor=face[v], hatch=hat[v],
                                 edgecolor="white") for v in
                   ("direct", "scaled", "not_comparable")]
        ax.legend(proxies, [T[5], T[6], T[7]], loc="upper right", fontsize=9.0,
                  title=T[8], title_fontsize=9.0)
        ax.grid(axis="x", ls=":", alpha=0.4)

    return _pk_save(
        fig, "report02_f6_band_slope",
        "Band slope of the azimuth-mean RCS computed from geometry for each airframe "
        f"(bars) sits {B['ratio_min']:.1f} to {B['ratio_max']:.1f} times steeper than the "
        f"measured anchor of {B['lit_das_db_per_ghz']:.3f} dB/GHz (Das et al., IEEE WCL "
        "2026); slope_only re-anchoring rotates every airframe onto the measured slope "
        "while leaving the band-mean level at the computed value.")


def fig_sigma_sensitivity(J):
    """⭐ σ 오차 아래 순위 강건성 — 이 편이 논문에 주는 두 번째 물건.

    (a) 공통모드 σ 오차: 세 밴드를 함께 옮기므로 순위가 그대로다 (절대거리만 σ 1 dB 당 ~1/4 dB).
    (b) 인용 규약별 최악 뒤집힘 문턱: 자세평균 + 측정 기울기 앵커가 문턱을 얼마나 올리는가.
    (c) 밴드별 독립(차분) σ 오차의 몬테카를로: 순위 보존 확률.

    ⚠ 배치는 손으로 잡는다 — 주석이 축 밖으로 나가면 constrained_layout 이 축을 0 으로 접고,
      그러면 bbox 가 커져 조판 축소 뒤 글자가 8 pt 아래로 내려간다.
    """
    SS = json.load(open(os.path.join(_ROOT, J_SIGSENS)))
    CM = SS["common_mode"]
    cm = CM["by_drone"]["matrice4e"]
    off = np.array(cm["offset_db"], float)
    i0 = int(np.argmin(np.abs(off)))
    ref = float(cm["R90_m"]["L1"][i0])
    CFG = SS["configurations"]["by_config"]
    cfg_keys = ["as_published", "aspect_avg", "aspect_avg_anchored"]
    cfg_name = ["single aspect (as published)", "aspect-averaged sigma",
                "aspect-averaged + measured slope"]
    MC = SS["monte_carlo_per_band_error"]
    _mc0 = next(iter(MC["by_drone"].values()))["by_sigma_e_db"]
    lv_key = [next(k for k in _mc0 if abs(float(k) - float(x)) < 1e-9)
              for x in MC["sigma_e_db_levels"]]
    lv = [float(k) for k in lv_key]

    T = ["(a) common-mode error, Matrice 4E", "(b) flip threshold by quoting convention",
         f"(c) per-band error, Monte Carlo (K = {MC['K']:,})",
         "sigma offset on every band [dB]", "R90 / R90(LTE, 0 dB)",
         "worst differential span before the order flips [dB]",
         "per-band i.i.d. sigma error [dB]", "P(order preserved)",
         f"order fixed in all {3 * len(MC['by_drone'])} airframe-band cells",
         f"{CM['slope_mean']:.3f} dB of range per dB of sigma",
         f"pre-anchor span {SS['differential']['realistic_span_db']:.2f} dB", "orders"]
    assert_fig_text(*T, *cfg_name, *BAND_LABEL.values())

    with paper_style(width="double", base_pt=10.0) as st:
        fig = plt.figure(figsize=(st.width_in, 5.7))
        gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.05],
                              left=0.085, right=0.99, top=0.945, bottom=0.085,
                              hspace=0.46, wspace=0.26)
        a1, a2, a3 = (fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]),
                      fig.add_subplot(gs[1, :]))

        for j, b in enumerate(BAND_ORDER):
            a1.plot(off, np.array(cm["R90_m"][b], float) / ref, label=BAND_LABEL[b],
                    markevery=8, **st.series(j))
        a1.set_xlabel(T[3])
        a1.set_ylabel(T[4])
        a1.set_title(T[0])
        a1.set_ylim(0.45, 2.35)
        a1.text(-9.5, 2.24, T[8], fontsize=9.0, va="top")
        a1.text(-9.5, 2.08, T[9], fontsize=9.0, va="top")
        a1.legend(loc="lower right", fontsize=9.0)
        a1.grid(ls=":", alpha=0.4)

        y = np.arange(len(cfg_keys))
        vals = [CFG[k]["worst_flip_span_db"] for k in cfg_keys]
        span = SS["differential"]["realistic_span_db"]
        bars = a2.barh(y, vals, height=0.34, edgecolor="white", linewidth=0.6)
        for j, p in enumerate(bars.patches):
            p.set_facecolor(PALETTE[j])
            p.set_hatch(HATCHES[j + 1])
        a2.axvline(span, color="#000000", lw=1.2, ls="--")
        a2.text(span + 0.15, -0.62, T[10], fontsize=9.0, va="center")
        for j, k in enumerate(cfg_keys):
            a2.text(0.08, j + 0.26, cfg_name[j], va="bottom", ha="left", fontsize=9.0)
            n_ord = int(CFG[k]["n_distinct_orders"])
            a2.text(vals[j] + 0.12, j, f"{vals[j]:.2f} dB, {n_ord} "
                    f"{T[11] if n_ord > 1 else T[11][:-1]}", va="center", fontsize=9.0)
        a2.set_yticks([])
        a2.set_ylim(-0.95, len(cfg_keys) - 0.35)
        a2.set_xlim(0, 8.6)
        a2.set_xlabel(T[5])
        a2.set_title(T[1])
        a2.grid(axis="x", ls=":", alpha=0.4)

        for j, (k, rec) in enumerate(MC["by_drone"].items()):
            p = [rec["by_sigma_e_db"][kk]["p_order_preserved"] for kk in lv_key]
            a3.plot(lv, p, label=J["airframes"][k]["name"], **st.series(j))
        a3.set_xscale("log")
        a3.set_xticks(lv)
        a3.get_xaxis().set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        a3.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        a3.set_ylim(0, 1.28)
        a3.set_xlabel(T[6])
        a3.set_ylabel(T[7])
        a3.set_title(T[2])
        a3.legend(loc="upper right", ncol=3, fontsize=9.0)
        a3.grid(ls=":", alpha=0.4)

    return _pk_save(
        fig, "report02_f7_sigma_sensitivity",
        "A common-mode RCS error leaves the three-waveform ranking unchanged over "
        f"{off.min():.0f} to +{off.max():.0f} dB in all fifteen airframe-band cells and "
        f"moves only absolute range, by {CM['slope_mean']:.3f} dB per dB of RCS; a "
        "per-band differential error is the axis that decides the ranking, and quoting "
        "aspect-averaged RCS on the measured frequency slope raises the worst flip "
        f"threshold from {CFG['aspect_avg']['worst_flip_span_db']:.2f} dB to "
        f"{CFG['aspect_avg_anchored']['worst_flip_span_db']:.2f} dB.")


# =========================================================================== #
#  ③  노트북 본문
# =========================================================================== #
def blocks(J):
    """노트북 본문. 여는 블록(한 일/결과/방법/재현) → §1..§5 → 다음 단계.

    ⭐ §1 은 **보는 절**이다 — 갤러리 · 사진 대조 · 공식 CAD 치수 · 재질 구성 네 그림이
       표적 모델을 세우고, 표는 그 그림의 숫자를 그대로 싣는다.
    """
    D = from_json("outputs/report02_derived.json")
    A = from_json("outputs/rcs_anchor.json")
    S = from_json("outputs/sbr_kr_sweep.json")
    F = from_json("outputs/sbr_defect_fixes.json")
    R3 = from_json("outputs/report3_rt.json")
    R6 = from_json("outputs/report6_sbr.json")
    GAL = from_json(J_GALLERY)
    PHO = from_json(J_PHOTO)
    CAD = from_json(J_CAD)
    MAT = from_json(J_MATERIAL)
    RCAD = from_json("outputs/real_cad_compare.json")
    COM = from_json("outputs/community_compare.json")
    PH4 = from_json("outputs/phantom4_scan_compare.json")
    from_json("outputs/sigma_anchor.json")     # §4.3 표가 경로로 직접 읽는다 — 존재 검사만
    #: Sionna RT 원문(기술보고서 v1.2 · 59쪽)의 낱말 재계수 — §2 의 엔진 문장이 여기서 나온다.
    PS = from_json("outputs/prior_settled_sionna.json")
    SIG = from_json(J_SIGSENS)
    #: 다른 워크플로의 원장 — 값만 읽는다.
    FC = from_json(J_FACET_COUNT)     # 스톡 경로 솔버가 같은 메쉬에서 내는 것
    FM = from_json(J_FACET_MECH)      # 그 기전(이미지법 진폭의 크기 불변)
    RB = from_json(J_RUNTIME)         # 같은 카드에서 잰 런타임
    P3O = from_json(J_P3_OURS)        # Phantom 3 눈감기 산출
    P3V = from_json(J_P3_VALID)       # 봉인 해제 대조
    PTF = from_json(J_PTD_FIX)        # PTD 항의 정직한 이름
    PTW = from_json(J_PTD_WIRE)       # PTD 배선 상태
    RGN = from_json(J_REGEN)          # σ 격자 동일설정 재생성 대조
    PV2 = from_json(J_P3_V2)          # §4.6 상자·구 대조군 (Yuan θ90 실측곡선 눈금)
    LFA = from_json(J_LOWF_ATK)       # §3.1a PO 유효 하한의 파급과 금칙
    LFN = from_json(J_LOWF_ANC)       # §3.1a 얇은 판 참값(2D MoM)
    FLT = from_json(J_FLEET)          # §4.7 Das 네 기체 사전등록 판정
    PRG = from_json("outputs/das_fleet_prereg.json")   # §4.7 봉인한 합격규칙 원문
    from_json(J_FLEET_ATK)            # §4.7 단서가 경로로 가리킨다 — 존재 검사
    MFX = from_json(J_MESHFIX)        # §1 형상 정정이 옮긴 것
    from_json(J_MESHFIX_ATK)          # §1·§4.7·§6 단서가 경로로 직접 가리킨다 — 존재 검사
    WC = "word_counts_rerun_this_session.sionna_rt_technical_report_v2_59p"

    #: f-string 안에서 포맷 문자열을 쪼개면 중괄호가 충돌한다 — 먼저 문자열로 만들어 둔다.
    EV = "d2_exit_vis_effect_on_reciprocity"
    worst_off = F.num(f"{EV}.worst_without_exit_vis_db", fmt="{:.2f}")
    worst_on = F.num(f"{EV}.worst_with_exit_vis_db", fmt="{:.2f}", unit="dB")
    rms45 = F.num(f"{EV}.rms_with_exit_vis_db[3]", fmt="{:.2f}", unit="dB")
    beta45 = F.num(f"{EV}.beta_deg[3]", fmt="{:.0f}", unit="°")
    noop_db = F.num("d4_epsilon_sensitivity.combos[0].by_drone.mavic4pro"
                    ".monostatic_noop_max_abs_db", fmt="{:.3e}", unit="dB")
    sph16 = F.num("d3_multibounce_phase.sphere_and_plate.sphere_vs_po_db"
                  ".sphere_lam/16_vs_po", fmt="{:+.3f}", unit="dB")
    plate10 = F.num("d3_multibounce_phase.sphere_and_plate.plate_db.plate_lam/10",
                    fmt="{:+.3f}", unit="dB")
    B = []

    # ── 여는 블록 (+ 논문 대응 블록을 셀 안으로 접어 넣는다 — PAPER_SPEC §4.1) ──────
    hdr = header(
        num=2,
        title="표적 모델: 메쉬 7종을 짓고 사진·공식 CAD·기준해로 재고, σ 의 주파수 축을 측정에 맞췄다",
        did="드론 7종의 메쉬를 제원과 제조사 CAD 치수에서 세워 사진 실루엣·공식 CAD 치수와 "
            "맞대고, 그 메쉬에 Sionna 광선엔진의 가림 판정과 부품별 재질 PO 면적분을 걸어 RCS 를 "
            "계산한 뒤, σ 의 주파수 의존성을 Das 측정에 맞췄다.",
        results=[
            f"**기체 {D.num('mesh.n', fmt='{:.0f}')}종의 메쉬를 지었다**(§1 그림 1) — "
            f"{D.num('mesh.smallest')} {D.num('mesh.smallest_span_mm', fmt='{:.0f}', unit='mm')} "
            f"부터 {D.num('mesh.largest')} "
            f"{D.num('mesh.largest_span_mm', fmt='{:.0f}', unit='mm')} 까지 "
            f"{D.num('mesh.span_ratio', fmt='{:.2f}')}배, 부품 "
            f"{D.num('mesh.n_parts_total', fmt='{:.0f}')}개 · 삼각형 "
            f"{D.num('mesh.n_tris_total', fmt='{:.0f}')}개, 전기적 크기 kr "
            f"{D.num('electrical.kr_min', fmt='{:.1f}')}~"
            f"{D.num('electrical.kr_max', fmt='{:.1f}')}. "
            f"⚠ §1 의 형상 원장 넷은 "
            f"{MFX.num('_meta.date')} 형상 정정 **전** 메쉬 기준이다(§1).",

            f"**사진 {D.num('photo.n_pairs', fmt='{:.0f}')}장과 실루엣으로 맞댔다**(그림 2) — "
            f"IoU 는 {D.num('photo.best')} {D.num('photo.best_iou', fmt='{:.3f}')}"
            f"(자기복제 상한의 {D.num('photo.best_pct', fmt='{:.0f}', unit='%')})부터 "
            f"{D.num('photo.worst')} {D.num('photo.worst_iou', fmt='{:.3f}')}"
            f"({D.num('photo.worst_pct', fmt='{:.0f}', unit='%')})까지, 외곽오차는 "
            f"{D.num('photo.contour_min_mm', fmt='{:.1f}')}~"
            f"{D.num('photo.contour_max_mm', fmt='{:.1f}', unit='mm')} 다.",

            f"**부품별 재질과 광선 가림이 이 편의 기여다**(그림 3·4) — 도전성 "
            f"{D.num('material.conducting')} 가 면적의 "
            f"{D.num('material.conducting_area_pct', fmt='{:.1f}', unit='%')} 를 차지하고 "
            f"Σ|Γ|A 의 {D.num('material.conducting_gamma_pct', fmt='{:.1f}', unit='%')} 를 낸다. "
            f"가림을 켜면 방위평균 σ 가 "
            f"{D.num('occlusion.min_db', fmt='{:.2f}')}"
            f"({D.num('occlusion.min_drone')})~"
            f"{D.num('occlusion.max_db', fmt='{:.2f}', unit='dB')}"
            f"({D.num('occlusion.max_drone')}) 내려간다.",

            f"커널이 해석 PO 기준해와 kr "
            f"{S.num('summary_div16.kr_min', fmt='{:.0f}')}~"
            f"{S.num('summary_div16.kr_max', fmt='{:.0f}')} 전 구간에서 최대 "
            f"{S.num('summary_div16.max_abs_db_vs_po', 0.201, '{:.3f}', 'dB')} 안에서 "
            f"일치하고 (kr {S.num('summary_div16.n_points', 21, '{:.0f}')}점 × 입사 "
            f"{S.num('meta.n_incidence', 48, '{:.0f}')}방향), 다중반사 위상은 PEC 이면각 "
            f"해석해 8πa²b²/λ² 와 변 길이 4점 전부에서 "
            f"{F.num('d3_multibounce_phase.max_abs_err_db', fmt='{:.3f}', unit='dB')} 안에서 맞는다.",

            f"**주파수 의존성 A(f) 만 Das 측정(IEEE WCL 2026 15:3731)에 맞췄고, 같은 기체를 눈감고 "
            f"돌려 봉인을 풀었다**(§4.5) — 기울기 "
            f"{A.num('literature.mu_eps.das_phantom3_mono.mu_a', 0.21, '{:.3f}', 'dB/GHz')} 에 맞출 때 "
            f"기체 {D.num('anchor_modes.n_airframes', fmt='{:.0f}')}종의 평균 레벨이동은 "
            f"{D.num('anchor_modes.level_shift_abs_max_db', fmt='{:.2f}', unit='dB')} 이고, 눈감기 "
            f"Phantom 3 는 고도정합 실측곡선 대비 레벨 "
            f"{P3V.num('residual.vs_yuan_theta90_measured_curve.mean_db', fmt='{:+.2f}', unit='dB')} · "
            f"기울기 {P3V.num('slope.ratios.ours_over_yuan_theta90', fmt='{:.2f}')}배 다"
            f"(**v1 메쉬 기준** — 사진 실측으로 다시 지은 v2 메쉬에서는 레벨 "
            f"{PV2.num('v1_vs_v2.level_db.v2', fmt='{:+.2f}', unit='dB')} · 기울기 "
            f"{PV2.num('slope.ratios.ours_over_yuan_theta90', fmt='{:.2f}')}배 이고, 두 판의 이동은 "
            f"§4.6 첫 문단이 잇는다). "
            f"**같은 잣대를 네 기체로 넓힌 사전등록 대조의 판정은 "
            f"{FLT.num('prereg_judgement.verdict')} 다**(§4.7 — 괄호 안의 P3 은 봉인한 합격조건 "
            f"넷 중 **세 번째**를 가리키는 이름이고 기체 Phantom 3 가 아니다) — 네 기체 레벨오차"
            f"(측정 대비 우리 σ 의 dB 차) 산포 "
            f"{FLT.num('prereg_judgement.P3_spread_db', fmt='{:.2f}', unit='dB')} 가 계산 전에 "
            f"봉인한 문턱 위에 있고, 갈린 축은 그 기체 자체의 형상 증거 유무다.",
        ],
        method=[
            ("분업", "σ 의 각도구조와 가림은 이 커널이 낸다 · 경로와 환경은 Sionna 광선엔진이 낸다 "
                     "— 레이다식에서 원래 갈라져 있는 두 양이다"),
            ("메쉬", "제원(공식 외형 L×W×H · 모터 대각 · 프롭 지름)과 제조사 CAD 치수표에서 "
                     "세우고 부품을 재질 그룹으로 유지 (`src/drone_cad.py`, "
                     "`src/drones.py:822` build_drone)"),
            ("형상 검사", "사진 실루엣 IoU(자세·원근·배율·프롭위상 정합 후) · 제조사 CAD 치수 "
                          "20개 · 실물 스캔 (`src/viz_mesh_photo.py`, `src/viz_cad_compare.py`)"),
            ("가림", "Sionna 의 Mitsuba/OptiX 광선엔진으로 면별 first-hit 판정 "
                     "(`src/rcs_sbr.py:184`)"),
            ("σ", "조명면 위 PO 표면적분, 부품별 |Γ| 가중 + 얇은 셸 뒤 금속의 코히런트 합"),
            ("모서리 회절", f"1차 PTD 항({PTF.num('naming_correction.honest_name')})이 커널 세 "
                          f"진입점에 배선돼 있고 생산 기본값은 끔이다 — ptd=False 에서 σ 변화는 "
                          f"{PTW.num('verdict.max_abs_delta_sigma_ptd_false', fmt='{:.1f}', unit='dB')} "
                          f"(`src/rcs_sbr.py` 의 `rcs_sbr_batch` · `rcs_sbr_multistatic` · "
                          f"`sbr_field`)"),
            ("검증", "기준해 셋과 대조 — 해석 PO 구 · 정확 Mie 구 · PEC 이면각 닫힌형 "
                     "(`benchmark/mie_pec_sphere.py`, `benchmark/verify_sbr_defect_fixes.py`)"),
            ("절대 레벨", "우리 PO 면적분 출력 그대로 — 재보정(`slope_only`)은 밴드평균 레벨을 "
                        "축으로 σ(f) 를 회전시킨다 (`src/sigma_anchor.py:589`)"),
            ("주파수 의존성", "σ = A(f)·B₁(φ,θ)·B₂ 분해에서 **A(f) 의 기울기만** Das 측정으로 "
                           "교체 — B₁ 은 우리 기하 계산 그대로 (`src/sigma_anchor.py`)"),
        ],
        prereq=[("01편 §3", "게재된 선행이 표적 산란을 어떻게 다뤘는지 — 측정 · 피팅 · "
                            "stock Fresnel · 해석적 블레이드")],
        repro=dict(
            cmd=["# ① 메쉬 원장 넷 — 기하·사진·공식 CAD·재질/가림 (CPU)",
                 "SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "src/viz_mesh_gallery.py",
                 "SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "src/viz_mesh_photo.py",
                 "SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "src/viz_cad_compare.py",
                 "SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "src/viz_mesh_material.py",
                 "# ② 기준해 대조와 앵커 원장 (GPU 1장)",
                 "SIONNA2_GPU=2 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/verify_sbr_kr_sweep.py",
                 "SIONNA2_GPU=2 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/verify_sbr_defect_fixes.py",
                 "SIONNA2_GPU=2 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/rcs_anchor.py",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/sigma_anchor.py",
                 "# ③ σ 오차 → 순위 강건성 (§5) — CPU",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/sigma_sensitivity.py",
                 "# ④ 대조군과 함대 대조 (§3.1a · §4.6 · §4.7)",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/p3_validation_v2.py",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "benchmark/das_fleet_sigma.py",
                 "# ⑤ 이 리포트 재생성 (파생 JSON + 게재규격 그림 4장 + 노트북) — GPU 불필요",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "src/make_report02_target.py"],
            out=["outputs/mesh_gallery.json", "outputs/mesh_compare_photo.json",
                 "outputs/mesh_compare_cad.json", "outputs/mesh_compare_material.json",
                 "outputs/sbr_kr_sweep.json", "outputs/sbr_defect_fixes.json",
                 "outputs/rcs_anchor.json", "outputs/sigma_anchor.json", J_SIGSENS,
                 J_P3_V2, J_FLEET, J_LOWF_ANC, J_LOWF_ATK, J_MESHFIX,
                 "outputs/report02_derived.json"],
            runtime=f"메쉬 원장 넷 {GAL.num('_meta.runtime_s', fmt='{:.0f}')} + "
                    f"{PHO.num('_meta.runtime_s', fmt='{:.0f}')} + "
                    f"{CAD.num('meta.elapsed_s', fmt='{:.0f}')} + "
                    f"{MAT.num('_meta.runtime_s', fmt='{:.0f}', unit='s')} (CPU) · "
                    f"kr 스윕 {S.num('meta.runtime_s', fmt='{:.0f}', unit='s')} · "
                    f"앵커 {A.num('meta.runtime_s', fmt='{:.0f}', unit='s')} (GPU 1장) · "
                    f"σ 민감도 {SIG.num('_meta.runtime_s', fmt='{:.0f}', unit='s')} · "
                    f"리포트 빌드 {D.num('_meta.runtime_s', fmt='{:.0f}', unit='s')}",
            note=f"메쉬 소스 최신 편집 {D.num('_meta.mesh_source_newest')} 기준으로, 이 편이 "
                 f"읽는 JSON {D.num('provenance.n_sources', fmt='{:.0f}')}개 중 "
                 f"{D.num('provenance.n_fresh', fmt='{:.0f}')}개가 그보다 새것이다. "
                 f"나머지 {D.num('provenance.n_stale', fmt='{:.0f}')}개(§4·§5)의 재실행은 "
                 f"§6 표 첫 두 줄이고, 아래 코드 셀이 원장을 그대로 찍는다.",
        ),
    )
    B.append(attach(hdr, paper_map(
        "III-A. Target Model",
        claim="표적 σ 는 부품별 재질 메쉬 위에서 광선으로 조명면을 가려낸 뒤 PO 면적분으로 "
              "계산하고, 절대 레벨은 그 계산 출력으로 두되 주파수 기울기만 측정 앵커에 맞춘다.",
        evidence=["그림 5", "그림 6", "그림 7", "표 §3.1", "표 §5",
                  "outputs/sbr_kr_sweep.json:summary_div16.max_abs_db_vs_po",
                  "outputs/sigma_anchor.json:drones",
                  "outputs/sigma_sensitivity.json:common_mode.order_invariant_everywhere"],
        qualifications=[
            f"공통모드 σ 오차는 세 밴드를 함께 옮겨 순위에서 상쇄된다 — 절대거리만 σ 1 dB 당 "
            f"{D.num('sigma_sens.slope_mean_db_per_db', fmt='{:.3f}', unit='dB')} 움직인다(§5)",
            f"밴드별 차분 σ 오차가 순위를 정하는 축이고, 자세평균 인용 + 측정 기울기 앵커가 "
            f"뒤집힘 문턱을 {D.num('sigma_sens.worst_flip_aspect_avg_db', fmt='{:.2f}')}"
            f"→{D.num('sigma_sens.worst_flip_anchored_db', fmt='{:.2f}', unit='dB')} 로 올린다",
            "바이스태틱 자세 패턴은 β ≤ 45° 에서 성립한다(§2.1)",
            "Rzewuski(NATO STO-MP-MSG-SET-183, 2021, 게재)가 FDTD 로 드론 바이스태틱 RCS 를 "
            "패시브 예산에 이미 넣었다 — 이 편의 기여는 엔진과 파이프라인 통합이다",
        ],
        report="report02_target")))

    # ── §1 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §1. 일곱 대의 기체 — 무엇을 지었나", "",
        "메쉬는 제원과 제조사 CAD 치수에서 세운다 — 공식 외형(L×W×H)·모터 대각·프롭 지름에 맞춘 뒤 "
        "부품을 **재질 그룹**으로 나눠 유지한다(`src/drones.py:43` DroneSpec, "
        "`src/drones.py:822`). 아래 넷은 형상 원장에서 그대로 옮긴 것이고, "
        "**matrice4e · mini5pro 가 06편 실측 대상**이다(표에서 ⭐). "
        f"⚠ **이 그림 넷과 §1 의 표는 {MFX.num('_meta.date')} 형상 정정 전 메쉬 기준이다** — "
        f"그날 Matrice 4E · Mini 2 · X500 V2 의 형상 상수가 공식 CAD 실측으로 정정되면서 몸통을 "
        f"공표 높이에 맞추던 z 축 배율이 Matrice 4E "
        f"{MFX.num('per_drone.matrice4e.fit_scale_before[2]', fmt='{:.3f}')}→"
        f"{MFX.num('per_drone.matrice4e.fit_scale_after[2]', fmt='{:.3f}')} · Mini 2 "
        f"{MFX.num('per_drone.mini2.fit_scale_before[2]', fmt='{:.3f}')}→"
        f"{MFX.num('per_drone.mini2.fit_scale_after[2]', fmt='{:.3f}')} 로 움직였고 세 기체의 메쉬 "
        f"지문(꼭짓점과 삼각형 전체를 한 값으로 요약한 것)이 셋 다 달라졌다(X500 V2 는 배율 대신 "
        f"삼각형이 "
        f"{MFX.num('per_drone.x500v2.n_tri_before', fmt='{:,.0f}')}→"
        f"{MFX.num('per_drone.x500v2.n_tri_after', fmt='{:,.0f}')} 로 바뀐 쪽이다) "
        f"⟨{J_MESHFIX} : edits⟩. 원장 재실행은 §6 표 첫 줄이다.", "",
        "![gallery](outputs/figures/mesh_gallery_all.png)", "",
        caption(1, "우리가 지은 일곱 대는 어떻게 생겼고 서로 얼마나 다른가?"), "",
        f"크기 폭이 {D.num('mesh.span_ratio', fmt='{:.2f}')}배다 — "
        f"{D.num('mesh.smallest')} {D.num('mesh.smallest_span_mm', fmt='{:.0f}', unit='mm')} 대 "
        f"{D.num('mesh.largest')} {D.num('mesh.largest_span_mm', fmt='{:.0f}', unit='mm')}. "
        f"그 폭이 kr 을 {D.num('electrical.kr_min', fmt='{:.1f}')}"
        f"({D.num('electrical.kr_min_name')} @ {D.num('electrical.kr_min_band')})~"
        f"{D.num('electrical.kr_max', fmt='{:.1f}')}"
        f"({D.num('electrical.kr_max_name')} @ {D.num('electrical.kr_max_band')})로 벌리고, "
        f"거기가 §3 의 두 눈금이 걸리는 자리다."))

    B.append(md(
        table_from("outputs/report02_derived.json:mesh.rows",
                   [("기체", "airframe"), ("L×W×H [mm] (프롭 포함)", "lwh_mm"),
                    ("무게 [g]", "weight_g"), ("부품", "n_parts"),
                    ("재질 그룹", "n_groups"), ("삼각형", "n_tris"),
                    ("외접반경 r [m]", "r_encl_m"), ("kr @5G", "kr_5g")],
                   fmt={"weight_g": "{:.0f}", "n_parts": "{:.0f}", "n_groups": "{:.0f}",
                        "n_tris": "{:,.0f}", "r_encl_m": "{:.3f}", "kr_5g": "{:.1f}"}), "",
        f"부품 수는 그룹별 연결성분의 합이다 — 모터 4개는 4로 센다. 맨 오른쪽 **kr** 은 표적을 "
        f"파장으로 잰 크기다 — 외접반경 r 에 파수 k = 2π/λ 를 곱한 값이고, 클수록 파장에 비해 몸이 "
        f"크다는 뜻이다. 외접반경 r 은 이 빌더가 "
        f"메쉬에서 직접 다시 재고 갤러리 원장과 대조한다(최대 차이 "
        f"{D.num('mesh.r_crosscheck_max_pct', fmt='{:.2f}', unit='%')})."))

    B.append(md(
        "### §1.1 사진과 맞댔다", "",
        f"사진 {D.num('photo.n_pairs', fmt='{:.0f}')}장을 각각 정합해 실루엣 **IoU**(두 실루엣이 "
        f"겹친 넓이를 둘을 합친 넓이로 나눈 값 — 1 에 가까울수록 잘 맞는다)를 쟀다 — "
        f"카메라 자세·원근·배율·위치와 로터별 프로펠러 위상을 맞춘 뒤 겹친다"
        f"(`src/viz_mesh_photo.py`). 자료 규칙에 걸린 사진 "
        f"{D.num('photo.n_excluded', fmt='{:.0f}')}장은 사유와 함께 원장에 남겼다.", "",
        figure_md("outputs/figures/report02_f2_mesh_photo.png", 2,
                  "우리 메쉬의 외형은 실제 기체 사진과 얼마나 맞는가?",
                  paper_caption="Silhouette overlay of each mesh against a photograph of "
                                "the real airframe, with the self-replication ceiling of "
                                "the same metric shown beside every score.",
                  report="report02_target"), "",
        "### §1.2 형상 검사 세 가지 — 한 표로", "",
        table(["검사", "대상", "지표", "값", "그 지표의 바닥"],
              [["사진 실루엣",
                f"7기체 · 사진 {D.num('photo.n_pairs', fmt='{:.0f}')}장",
                "IoU (상한 대비)",
                f"{D.num('photo.worst_iou', fmt='{:.3f}')}~"
                f"{D.num('photo.best_iou', fmt='{:.3f}')} "
                f"({D.num('photo.worst_pct', fmt='{:.0f}')}~"
                f"{D.num('photo.best_pct', fmt='{:.0f}', unit='%')})",
                f"자기복제 상한 {D.num('photo.ceiling_min', fmt='{:.3f}')}~"
                f"{D.num('photo.ceiling_max', fmt='{:.3f}')} · 자세 1° 오차에서 "
                f"{D.num('photo.iou_at_1deg_pose_error', fmt='{:.3f}')}"],
               ["제조사 CAD 치수",
                f"어셈블리 {D.num('cad.n_assemblies', fmt='{:.0f}')}종 · 치수 "
                f"{D.num('cad.n_dims', fmt='{:.0f}')}개",
                "최대 편차",
                f"CAD 대비 {D.num('cad.worst_vs_cad_pct', fmt='{:.2f}')} % · 발행 제원 대비 "
                f"{D.num('cad.worst_vs_published_pct', fmt='{:.2f}', unit='%')}",
                f"제조사 CAD ↔ 자사 발행 제원이 "
                f"{D.num('cad.floor_pct', fmt='{:.2f}', unit='%')} 까지 갈린다"],
               ["실물 유래 메쉬",
                f"{PH4.num('name_real')} 스캔 · {RCAD.num('typhoon.name_real')} · "
                f"{COM.num('m600.name_real')}",
                "Δ 방위평균 σ",
                f"{PH4.num('d_sigma_db', fmt='{:+.2f}')} · "
                f"{RCAD.num('typhoon.d_sigma_db', fmt='{:+.2f}')} · "
                f"{COM.num('m600.d_sigma_db', fmt='{:+.2f}', unit='dB')}",
                f"자세별 RMS {PH4.num('d_sigma_rms_db', fmt='{:.1f}')}~"
                f"{COM.num('m600.d_sigma_rms_db', fmt='{:.1f}', unit='dB')}"]]), "",
        f"**이 표가 σ 의 인용 단위를 정한다** — 방위평균과 로브 위치로 인용하고, 널 깊이는 "
        f"메쉬 세부에 걸리므로 자세별 RMS 열에 그 크기가 그대로 적혀 있다. IoU 에는 눈금이 "
        f"붙어 있다 — 표 오른쪽 끝의 **자기복제 상한**은 같은 메쉬로 만든 가짜 사진을 같은 "
        f"파이프라인에 넣었을 때 나오는 값, 즉 이 검사가 낼 수 있는 최고점이다. 그 값이 "
        f"{D.num('photo.ceiling_min', fmt='{:.3f}')}~"
        f"{D.num('photo.ceiling_max', fmt='{:.3f}')} 다(암·블레이드가 몇 px 이라 최고점이 "
        f"1.0 아래다). 같은 메쉬끼리도 자세가 1° 어긋나면 "
        f"{D.num('photo.iou_at_1deg_pose_error', fmt='{:.3f}')}, 2° 면 "
        f"{D.num('photo.iou_at_2deg_pose_error', fmt='{:.3f}')} 로 내려간다."))

    B.append(md(
        "### §1.3 부품별 재질 — PO 적분에 들어가는 물리 입력", "",
        "Sionna RT 와 우리 PO 적분기는 **같은 재질 표**를 읽는다"
        "(`src/materials.py:53` MATERIALS, `src/drones.py:562` DRONE_GROUP_MAT). "
        "아래 그림은 7기체의 표면적을 재질로 나누고, 같은 면적을 |Γ| 로 가중해 "
        "**무엇이 반사 진폭을 내는지**까지 함께 싣는다.", "",
        "![materials](outputs/figures/mesh_compare_material_area.png)", "",
        caption(3, "기체는 무엇으로 이루어져 있고, 그 중 무엇이 반사 진폭을 내는가?"), "",
        f"도전성 {D.num('material.conducting')} 가 면적의 "
        f"{D.num('material.conducting_area_pct', fmt='{:.1f}', unit='%')} 를 차지하고 Σ|Γ|A 의 "
        f"{D.num('material.conducting_gamma_pct', fmt='{:.1f}', unit='%')} 를 낸다."))

    B.append(md(
        table_from("outputs/report02_derived.json:material.rows",
                   [("재질", "material"), ("부품 그룹", "groups"),
                    (r"\|Γ\| 벌크", "gamma_bulk"), (r"\|Γ\| PO 실효", "gamma_po"),
                    ("면적 [m²] (7기체)", "area_m2"), ("면적 비중", "area_pct"),
                    ("Σ\\|Γ\\|A 비중", "gamma_pct")],
                   fmt={"gamma_bulk": "{:.3f}", "gamma_po": "{:.2f}", "area_m2": "{:.3f}",
                        "area_pct": "{:.1f} %", "gamma_pct": "{:.1f} %"}), "",
        f"유전체 셸(body·canopy)은 |Γ| = "
        f"{D.num('material.gamma_shell', fmt='{:.2f}')} 로 왕복 투과 τ = 1−|Γ|², 즉 "
        f"{D.num('material.shell_tau_db', fmt='{:.2f}', unit='dB')} 를 곱해 통과시키고 그 뒤 "
        f"금속(배터리·PCB)을 코히런트 합산한다(`src/rcs_sbr.py:88`)."))

    # ── §2 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §2. 엔진 — 광선으로 조명면을 찾고 그 위에서 PO 를 적분한다", "",
        "**PO** 는 물리광학(physical optics)이다 — 빛이 닿는 면에 흐르는 전류를 근사식으로 바로 "
        "적어 넣고 그 면을 훑어 더해 산란을 내는 방법이고, **SBR** 은 광선을 쏴서 튀기며 그 면이 "
        "어디인지 찾는 방법(shooting-and-bouncing rays)이다. "
        "상용 고주파 RCS 솔버(FEKO/CST SBR+)의 순서 그대로다: **① 광선으로 실제 조명면을 찾고 "
        "② 그 위에서 PO 표면적분**(`src/rcs_sbr.py:184`). ① 은 Sionna 가 이미 들고 있는 "
        "Mitsuba/OptiX 엔진을 그대로 부른다. 레이다식이 표적 산란과 전파 경로를 두 양으로 쓰는 "
        "그대로 — **σ 는 이 커널이, 경로와 환경은 그 엔진이 낸다**.", "",
        table(["단계", "무엇을", "누가"],
              [["첫 충돌 탐색 · 가림", "어느 면이 실제로 조명되는가",
                "🟢 Sionna 의 Mitsuba/OptiX 광선엔진"],
               ["재질 |Γ|", "부품별 반사계수", "🟢 Sionna 재질표 (`src/materials.py:53`)"],
               ["PO 면적분 → σ", "E = Σ |Γᵢ| e^{j2k pᵢ·û} d², σ = 4π|E|²/λ²",
                "🔵 우리 (`src/rcs_sbr.py:184`)"],
               ["셸 투과", "얇은 유전체 셸 뒤 금속(배터리·PCB)의 코히런트 합",
                "🔵 우리 (동 `penetrate=True`)"]]), "",
        f"**Sionna 는 광선을 쏘고 튀긴다** — 기술보고서(v1.2, 59쪽)에 SBR 이 "
        f"{PS.num(f'{WC}.SBR or shooting-and-bouncing', fmt='{:.0f}')}회 나오고 우리도 그 "
        f"엔진을 그대로 부른다. 같은 문서에서 `physical optics` "
        f"{PS.num(f'{WC}.physical optics', fmt='{:.0f}')}회 · `radar cross section` "
        f"{PS.num(f'{WC}.radar cross section', fmt='{:.0f}')}회 · `surface current` "
        f"{PS.num(f'{WC}.surface current', fmt='{:.0f}')}회이고, 거친 면은 정규화 산란패턴을 "
        f"쓰는 경험 모델이다 — **표면전류 적분과 σ 출력을 우리가 얹는다**. 게재된 최신 선행"
        f"(Clutter-Aware ISAC, Proc. IEEE 114(1))은 드론 메쉬를 Sionna 에 넣고 stock Fresnel "
        f"응답을 그대로 받는다(01편 §3).", "",
        f"ITU `metal` 의 산란계수 S = {R3.num('C_metal.itu_metal_S', fmt='{:.1f}')} 이라 stock "
        f"산란 모델이 금속에서 내놓는 항은 0 이고, 우리 σ 는 면적분에서 창발한다. 금속 4그룹"
        f"(모터·배터리·PCB·카메라)만 남긴 메쉬의 방위평균 σ 는 전체의 "
        f"{R3.num('C_metal.metal_share_pct', fmt='{:.0f}', unit='%')} 다 — 코히런트 합이라 "
        f"100 % 를 넘는다.", "",
        f"같은 메쉬를 스톡 경로 솔버에 그대로 넣고 무엇이 나오는지 쟀다 — 삼각형 "
        f"{FC.num('levels[0].n_tri', 29932, '{:,.0f}')}개(mavic4pro)에서 광선 예산 "
        f"{FC.num('meta.spp_main', fmt='{:.1e}')} spp 일 때 경로는 자세당 "
        f"{FC.num('levels[0].rt_n_paths_mean', fmt='{:.1f}')}개이고, 이미지법 정반사 경로는 "
        f"{FC.num('levels[0].spec_n_aspects', 36, '{:.0f}')}자세를 통틀어 "
        f"{FC.num('levels[0].spec_n_paths_total', 2, '{:.0f}')}개"
        f"(자세 {FC.num('levels[0].spec_n_aspects_nonzero', 1, '{:.0f}')}개)다 — 나머지 진폭은 "
        f"확산 항이 낸다. 평판 대조군에서 그 정반사 진폭은 무한거울 값 "
        f"{FM.num('theory.amp_image_source_db', fmt='{:.2f}', unit='dB')} 에 고정되어 판 크기를 "
        f"{FM.num('VERDICT.plate_size_invariance.size_ratio_max', 40, '{:.0f}')}배로 키워도 "
        f"{FM.num('VERDICT.plate_size_invariance.rt_spread_db', fmt='{:.1e}', unit='dB')} 안에 머물고, "
        f"면 수가 표적 에코를 지배한다는 가설은 스톡 기울기 "
        f"{FC.num('slopes.stock_incoh', fmt='{:.3f}')} dB/decade 로 "
        f"{FC.num('verdict.result')} 다.", "",
        f"런타임도 같은 카드에서 나란히 쟀다 — 스톡 PathSolver 가 "
        f"{RB.num('answer.same_card_control.stock_sionna_pathsolver_ms.min', fmt='{:.1f}')}~"
        f"{RB.num('answer.same_card_control.stock_sionna_pathsolver_ms.max', fmt='{:.1f}', unit='ms')}"
        f"({RB.num('answer.same_card_control.stock_sionna_pathsolver_ms.n_configs', 12, '{:.0f}')}설정)"
        f"일 때 우리 per-pose 는 중앙값 "
        f"{RB.num('production_per_pose.summary_ms.median', fmt='{:.1f}', unit='ms')} 다. 그 비용의 "
        f"{RB.num('answer.cost_structure.host_side_pct', fmt='{:.1f}', unit='%')} 가 호스트에 있고 "
        f"GPU 광선추적은 "
        f"{RB.num('production_per_pose.stage_pct_median_over_configs.rt_trace', fmt='{:.1f}', unit='%')} "
        f"다."))

    B.append(md(
        "![lit versus shadowed](outputs/figures/mesh_compare_material_shadow.png)", "",
        caption(4, "PO 적분이 실제로 올라타는 면은 어디까지인가?"), "",
        f"조명원을 방위 {D.num('occlusion.az_deg', fmt='{:.0f}', unit='°')}, 고각 "
        f"{D.num('occlusion.el_deg', fmt='{:.0f}', unit='°')} 에 두었다 — 방위 "
        f"{D.num('occlusion.n_az_sweep', fmt='{:.0f}')}점 스윕에서 7기체 평균 그늘비율의 "
        f"중앙값에 가장 가까운 방위다(규칙이 고른다). 그 자세에서 조명원을 향한 외피의 "
        f"{D.num('occlusion.shadow_min_pct', fmt='{:.0f}')}~"
        f"{D.num('occlusion.shadow_max_pct', fmt='{:.0f}', unit='%')} 가 기체 자신에 가려 있다.", "",
        f"가림 판정은 생산 SBR 이 쓰는 그림자광선 그대로다(`rcs_sbr._exit_visible()`), "
        f"그림의 색은 재질이 아니라 조명 상태를 부호화한다."))

    B.append(md(
        table_from("outputs/report02_derived.json:occlusion.rows",
                   [("기체", "airframe"), ("외피 그늘", "shadow_pct"),
                    ("가림 [dB]", "d_occlusion_db"), ("셸 투과 [dB]", "d_shell_db"),
                    ("합 [dB]", "d_total_db"), ("이산화 바닥 [dB]", "floor_db"),
                    ("생산 σ [dBsm]", "sigma_dbsm")],
                   fmt={"shadow_pct": "{:.0f} %", "d_occlusion_db": "{:+.2f}",
                        "d_shell_db": "{:+.2f}", "d_total_db": "{:+.2f}",
                        "floor_db": "{:.3f}", "sigma_dbsm": "{:.1f}"}), "",
        f"가림을 끄면 방위평균 σ 가 {D.num('occlusion.max_db', fmt='{:.2f}', unit='dB')}"
        f"({D.num('occlusion.max_drone')}, 닫힌 동체)까지 부풀고, 열린 프레임인 "
        f"{D.num('occlusion.min_drone')} 에서는 "
        f"{D.num('occlusion.min_db', fmt='{:.2f}', unit='dB')} 다. "
        f"{D.num('occlusion.n_above_floor', fmt='{:.0f}')}기체 전부에서 이 값이 이산화 바닥"
        f"(최대 {D.num('occlusion.floor_max_db', fmt='{:.3f}', unit='dB')}) 위에 있다. "
        f"⚠ 이 표와 그림 4 도 {MFX.num('_meta.date')} 형상 정정 전 메쉬 기준이다 — 가림 최대치를 "
        f"내는 Matrice 4E 와 X500 V2 가 그 정정을 받은 기체이고, 닫힌 동체의 가림은 셸 형상에 "
        f"직접 걸린다. 생산 σ 열도 같은 이유로 재계산 대상이다."))

    B.append(md(
        "### §2.1 바이스태틱 — 수신 방향으로도 그림자 광선을 쏜다", "",
        "각 충돌점에서 수신기 방향으로 그림자 광선을 한 번 더 쏘아 **출사 쪽 가림**을 판정한다"
        "(`src/rcs_sbr.py:330` `rcs_sbr_multistatic`). Sagitta(preprint, arXiv:2604.09243 각주 1)가 "
        "바이스태틱 SBR 에서 빠져 있다고 지목한 바로 그 단계다.", "",
        f"켠 효과는 **상반성**(보내는 자리와 받는 자리를 맞바꿔도 σ 가 같아야 한다는 성질)으로 "
        f"잰다 — 위반 최대치가 {worst_off} → {worst_on} 로 내려간다. "
        f"모노스태틱에서 이 검사는 무연산이라 생산 σ 는 {noop_db} 그대로다.", "",
        f"**바이스태틱 자세 패턴은 β ≤ 45° 에서 성립한다** — 그 범위의 상반성 RMS 가 "
        f"{rms45} (β={beta45}) 다.",
        # ── §3 ─────────────────────────────────────────────────────────────
        "",
        "## §3. 기준해 셋과 대조했다", "",
        "구 후방산란은 두 개의 **닫힌형 기준해**(근사 없이 식으로 바로 값이 나오는 답)를 갖는다 "
        "— 구에 대해서만 맥스웰 방정식이 그대로 풀리는 **정확 Mie** 와, 같은 구에 PO 근사를 "
        "적용해 손으로 푼 **해석 PO** 다"
        "(`benchmark/mie_pec_sphere.py:98`, `:127`). 둘 다 우리 출력이 아니라 과녁이다.", "",
        "```", "(커널 − Mie)  =  (커널 − 해석 PO)   +   (해석 PO − Mie)",
        "                  ↑ 우리 수치오차          ↑ PO 모델 자체의 간극", "```",
        "커널이 PO 이므로 **수치 수렴의 과녁은 해석 PO** 이고, Mie 잔차는 PO 모델 자체의 간극이라는 "
        "두 번째 눈금이다. 둘을 나눠 두면 각각이 얼마인지 그대로 읽힌다."))


    B.append(md(
        figure_md("outputs/figures/report02_f5_reference_gap.png", 5,
                  "일곱 기체가 놓인 kr 자리에서 우리 수치오차와 PO 모델의 간극은 각각 얼마인가?",
                  paper_caption="Our physical-optics kernel against two closed-form "
                                "reference solutions on a PEC sphere, the two errors they "
                                "measure separated, and the electrical size of the seven "
                                "airframes on the same axis.",
                  report="report02_target"), "",
        "### §3.1 두 눈금", "",
        table(["", "우리 수치오차 · 기준해 = 해석 PO", "PO 모델의 간극 · 기준해 = 정확 Mie"],
              [["최대 편차 (kr=1..100)",
                S.num("summary_div16.max_abs_db_vs_po", 0.201, "{:.3f}", "dB"),
                S.num("summary_div16.max_abs_db_vs_mie", fmt="{:.2f}", unit="dB") + " (kr=1)"],
               ["kr≥30 산포",
                S.num("summary_div16.std_sbr_over_po_pct_kr_ge30", 0.885, "{:.3f}", "%"),
                S.num("summary_div16.std_sbr_over_mie_pct_kr_ge30", fmt="{:.3f}", unit="%")],
               ["1 dB 안으로 드는 kr",
                "전 구간 (kr=" + S.num("summary_div16.kr_min", fmt="{:.0f}") + " 부터)",
                "kr ≥ " + D.num("po_floor.kr_below_1p0_db", fmt="{:.2f}")],
               ["0.5 / 0.2 dB 안으로",
                "전 구간 (" + S.num("summary_div16.max_abs_db_vs_po", fmt="{:.3f}", unit="dB")
                + " 이내)",
                "kr ≥ " + D.num("po_floor.kr_below_0p5_db", fmt="{:.2f}") + " / "
                + D.num("po_floor.kr_below_0p2_db", fmt="{:.2f}")]]), "",
        f"기체 7 × 밴드 3 = {D.num('electrical.n_airframe_band', 21, '{:.0f}')} 조합 중 "
        f"{D.num('electrical.n_below_po_1db', fmt='{:.0f}')}개가 오른쪽 열의 1 dB 문턱 아래에 "
        f"놓이고, 그것이 실측 대상 {D.num('electrical.kr_min_name')} 다. "
        f"**⚠ 그런데 이 kr 눈금은 매끄러운 구에서만 맞는 눈금이다** — 구는 몸 전체가 하나의 넓은 "
        f"곡면이지만 드론은 얇은 판과 가는 막대의 모음이라, PO 가 어긋나는 자리를 정하는 것은 "
        f"기체 전체 크기가 아니라 **부품 하나의 폭이 파장에 비해 얼마나 넓은가** 다. 그 세 번째 "
        f"눈금이 §3.1a 다."))

    # ── §3.1a ⭐ 세 번째 눈금 — 부품 폭 기준 (2026-08-04 얇은 판 참값이 새로 세운 하한) ──
    #    ⛔ 여기서 «PO 한계 때문에 저주파 σ 가 틀렸다» 로 나아가면 안 된다. 크기 귀속이 없고
    #       세 번째 축(메쉬 삼각형 배치)은 아직 재지 않았다. «문턱 아래에 있다» 까지만 쓴다.
    KNEE = ("q5_blast_radius.po_validity_blast_radius_the_real_one"
            ".recomputed_by_me_frequency_at_which_each_feature_passes_that_knee")
    B.append(md(
        "### §3.1a 세 번째 눈금 — 부품 폭 기준", "",
        f"얇은 금속 판을 참값(2D 적률법 MoM — 맥스웰 방정식을 수치로 푸는 방법)과 PO 로 각각 내고 "
        f"맞대면, 두 편파(전파의 전기장이 흔들리는 방향 — 판의 긴 축과 나란한 쪽을 TM, 그에 "
        f"수직인 쪽을 TE 라 부른다) 중 나쁜 쪽의 차이가 1 dB 아래로 내려가는 문턱이 **폭 ≥ "
        f"{LFN.num('thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam', fmt='{:.3f}')} λ** 다. "
        f"이 문턱을 **Phantom 3 급 한 기체의 부품 치수**로 옮기면 부품마다 몇 GHz 부터 문턱을 "
        f"넘는지가 나온다 — 동체 "
        f"{LFA.num(f'{KNEE}.body_81.51mm', fmt='{:.2f}')} · 암뿌리 "
        f"{LFA.num(f'{KNEE}.arm_root_45mm', fmt='{:.2f}')} · 암끝 "
        f"{LFA.num(f'{KNEE}.arm_tip_30mm', fmt='{:.2f}')} · 프로펠러 "
        f"{LFA.num(f'{KNEE}.prop_blade_13.78mm', fmt='{:.2f}')} · 모터 "
        f"{LFA.num(f'{KNEE}.motor_13.68mm', fmt='{:.2f}')} · 캐노피 "
        f"{LFA.num(f'{KNEE}.canopy_6.22mm', fmt='{:.2f}')} · PCB "
        f"{LFA.num(f'{KNEE}.pcb_2.99mm', fmt='{:.2f}')} GHz. ⚠ 이 목록은 **기체 하나**의 치수이고 "
        f"7기체 공통이 아니다 — §1 의 크기 폭 {D.num('mesh.span_ratio', fmt='{:.2f}')}배 안에서 "
        f"S1000+ 처럼 큰 기체는 이 문턱이 그만큼 낮은 주파수로, Mini 급은 그만큼 높은 주파수로 "
        f"옮겨간다. 치수 자체도 Phantom 3 를 사진 실측으로 다시 짓기 전 스윕에서 인용한 값이다 "
        f"⟨{J_LOWF_ANC} : consistency_with_drone.drone.source⟩.", "",
        f"⚠⚠ **우리 생산 3 밴드(LTE {D.num('bands_ghz.LTE', fmt='{:.3f}')} · 5G "
        f"{D.num('bands_ghz.5G', fmt='{:.1f}')} · WiFi "
        f"{D.num('bands_ghz.WiFi', fmt='{:.2f}')} GHz)는 전부 이 문턱 아래에 부품을 남긴다** — "
        f"가장 낮은 밴드에서는 동체까지 아래이고, 가장 높은 밴드에서도 암끝·프로펠러·모터·"
        f"캐노피·PCB 가 아래에 있다. 문헌 측정의 위쪽 끝"
        f"({PV2.num('slope.das_published.band[1]', fmt='{:.1f}', unit='GHz')})까지 **줄곧** 문턱 "
        f"아래에 남는 부품은 캐노피와 PCB 둘뿐이고(각각 "
        f"{LFA.num(f'{KNEE}.canopy_6.22mm', fmt='{:.2f}')} · "
        f"{LFA.num(f'{KNEE}.pcb_2.99mm', fmt='{:.2f}', unit='GHz')} 에서 비로소 넘는다), "
        f"프로펠러와 모터는 그 끝에 닿기 전인 "
        f"{LFA.num(f'{KNEE}.prop_blade_13.78mm', fmt='{:.2f}')} · "
        f"{LFA.num(f'{KNEE}.motor_13.68mm', fmt='{:.2f}', unit='GHz')} 에서 문턱을 넘는다 — "
        f"문헌 대역의 맨 위 토막에서만 넘는 셈이다. 그래서 이 편은 σ 의 절대 크기 대신 "
        f"**각도 구조와 밴드 간 상대 순위**를 "
        f"주장한다(§5). 절대 레벨은 06편 교정구가 측정으로 앵커한다.", "",
        f"⭐ 이 눈금은 §3.1 의 두 눈금과 **다른 것을 잰다.** (커널 − 해석 PO) 는 우리 구현이 PO 를 "
        f"제대로 계산하는지의 눈금이고, 폭 "
        f"{LFN.num('thin_plate.per_width.0.15.a_lam', fmt='{:.2f}')} λ 인 얇은 판에서도 격자를 "
        f"조이면 "
        f"{LFN.num('thin_plate.per_width.0.15.max_abs_vs_po_two_finest_db', fmt='{:.3f}', unit='dB')} "
        f"까지 수렴한다. (PO − 참값) 은 PO 라는 모델 자체가 참값과 떨어진 거리이고, 이 절이 새로 "
        f"크기를 준 것이 그쪽이다.", "",
        "**이 결과로 말할 수 없는 것 세 가지**",
        f"· ✗ 「저주파 σ 가 틀렸다」 → 맞는 말은 **불확도가 지금 선언된 것보다 크고 그 크기를 "
        f"아직 못 정했다** 다 ⟨{J_LOWF_ATK} : q5_blast_radius.what_must_not_be_said[0]⟩.",
        f"· ✗ 「고대역은 검증됐다」 → 캐노피·PCB 는 문헌 측정 대역의 위쪽 끝까지 문턱 아래에 "
        f"머물고, 프로펠러·모터도 그 끝 바로 아래("
        f"{LFA.num(f'{KNEE}.prop_blade_13.78mm', fmt='{:.2f}')} · "
        f"{LFA.num(f'{KNEE}.motor_13.68mm', fmt='{:.2f}', unit='GHz')})에서야 문턱을 넘는다 — "
        f"대역의 대부분에서 이 부품들은 여전히 문턱 아래다 "
        f"⟨{J_LOWF_ATK} : q5_blast_radius.what_must_not_be_said[1]⟩.",
        f"· ✗ 「격자를 더 촘촘히 하면 σ 가 고쳐진다」 → **정반대다.** 격자를 조이면 저대역 기울기가 "
        f"오히려 더 가팔라진다 — 이것이 이 라운드에서 가장 확실한 결과다 "
        f"⟨{J_LOWF_ATK} : q5_blast_radius.sampling_blast_radius_actual.direction⟩."))

    B.append(md(
        "### §3.2 다중반사 위상 — PEC 이면각 닫힌형과 대조", "",
        f"**이면각**은 두 평판이 90° 로 맞붙은 표준 형상이고, **PEC** 는 전기를 완벽히 통하는 "
        f"이상적 금속이다. 직각 이면각의 이등분선 입사는 σ = 8πa²b²/λ² 로 닫혀 있다. "
        f"2회 반사를 켜고 변 길이 4점에서 "
        f"그 값과 맞댄다(`benchmark/verify_sbr_defect_fixes.py`, "
        f"{D.num('bands_ghz.5G', fmt='{:.1f}', unit='GHz')}, λ/12 격자).", "",
        table_from("outputs/sbr_defect_fixes.json:d3_multibounce_phase.rows",
                   [("변 a [m]", "a_m"), ("해석해 [dBsm]", "exact_dbsm"),
                    ("1회 반사 [dBsm]", "sbr_1bounce_dbsm"),
                    ("2회 반사 [dBsm]", "sbr_2bounce_dbsm"),
                    ("오차 [dB]", "err_2bounce_db")],
                   fmt={"a_m": "{:.2f}", "exact_dbsm": "{:.2f}",
                        "sbr_1bounce_dbsm": "{:.2f}", "sbr_2bounce_dbsm": "{:.2f}",
                        "err_2bounce_db": "{:+.3f}"}), "",
        f"오목부에서 오는 항이 어디에 있는지 1회/2회 열이 바로 보여준다. 같은 스크립트가 매끄러운 "
        f"기준체도 함께 잰다 — 구는 λ/16 격자에서 해석 PO 대비 {sph16}, 평판은 λ/10 격자에서 "
        f"{plate10} 다."))

    # ── §4 ─────────────────────────────────────────────────────────────────
    B.append(md(
        "## §4. 앵커 — 주파수 축만 측정에서 받았다", "",
        "게재된 표준트랙 논문의 분해를 그대로 쓴다(Zhang, IEEE JSAC 44:702, 2026 — 측정 적합 모델): "
        "σ = A(f)·B₁(φ,θ)·B₂. **A(f) 의 기울기는 측정에서, A(f) 의 레벨과 B₁ 은 우리 계산에서 온다.**", "",
        f"PO 면적분은 f² 로 커지는 정반사항을 담는다. 기하에서 나온 우리 밴드 기울기는 "
        f"{D.num('band_slope.ours_min', fmt='{:.3f}')}"
        f"({D.num('band_slope.ours_min_drone')}) ~ "
        f"{D.num('band_slope.ours_max', fmt='{:.3f}', unit='dB/GHz')}"
        f"({D.num('band_slope.ours_max_drone')}) 이고, 측정은 "
        f"{A.num('literature.mu_eps.das_phantom3_mono.mu_a', fmt='{:.3f}')}(Das, IEEE WCL 2026) "
        f"와 {A.num('literature.mu_eps.yuan_phantom3_azplane.mu_a', fmt='{:.3f}', unit='dB/GHz')}"
        f"(Yuan, EuCAP 2025) 다. ⚠ **두 수는 창이 다르다** — 우리 값은 생산 세 밴드"
        f"({D.num('bands_ghz.LTE', fmt='{:.3f}')}~"
        f"{D.num('bands_ghz.WiFi', fmt='{:.2f}')} GHz)에서 잰 기울기이고 측정 두 값은 "
        f"{PV2.num('slope.das_published.band[0]', fmt='{:.1f}')}~"
        f"{PV2.num('slope.das_published.band[1]', fmt='{:.1f}')} GHz 전대역 적합이다. 같은 "
        f"기체를 같은 커널로 돌려도 창을 바꾸면 기울기가 달라진다(우리 Phantom 3 **v2 메쉬** — "
        f"사진 실측으로 다시 지은 쪽이다: 저대역 창 "
        f"{PV2.num('slope.subband.ours.1.8-6.0 GHz.a', fmt='{:.3f}')} vs 전대역 "
        f"{PV2.num('slope.ours_el0_full_band.a', fmt='{:.3f}', unit='dB/GHz')}). 창을 맞춘 비교는 "
        f"§4.5 의 부분대역 행과 §4.6 이다. 모서리 회절항(PTD)은 면적분과 별개의 항이므로 "
        f"주파수축은 측정에서 받고, 그 항을 넣는 일은 §6 다음 단계 표에 있다.", "",
        figure_md("outputs/figures/report02_f6_band_slope.png", 6,
                  "측정 앵커는 각 기체의 밴드 기울기를 어디로 옮기는가?",
                  paper_caption="Band slope of the azimuth-mean RCS computed from geometry "
                                "for each airframe against the two measured slopes, and "
                                "where slope_only re-anchoring places every airframe.",
                  report="report02_target")))

    B.append(md(
        "### §4.1 모드 선택 — 무엇을 옮기고 무엇을 대가로 내는가", "",
        f"`src/sigma_anchor.py` 는 재보정 모드 셋을 제공한다. 생산 기준은 "
        f"`{D.num('anchor_modes.production_mode')}` 이고, 밴드별로 옮기는 양은 "
        f"{D.num('anchor.correction_max_db', fmt='{:+.2f}')}"
        f"({D.num('anchor.correction_max_drone')} @ {D.num('anchor.correction_max_band')}) ~ "
        f"{D.num('anchor.correction_min_db', fmt='{:+.2f}', unit='dB')}"
        f"({D.num('anchor.correction_min_drone')} @ {D.num('anchor.correction_min_band')}) 다.", "",
        table_from("outputs/report02_derived.json:anchor_modes.rows",
                   [("모드", "mode"), ("무엇을 옮기나", "moves"),
                    ("평균 레벨이동 [dB]", "mean_shift_range_db"), ("대가", "cost")]), "",
        f"{D.num('anchor_modes.why_production')}", "",
        f"레벨이동 열은 기체 {D.num('anchor_modes.n_airframes', fmt='{:.0f}')}종의 세 밴드 평균 "
        f"Δ 다 — 정의는 `anchor_modes.definition` 에 있다."))

    B.append(md(
        "### §4.2 세 인자, 각각의 출처", "",
        table(["인자", "무엇", "어디서", "이 편의 근거"],
              [["A(f) 기울기", "주파수 의존성", "**측정**(Das)",
                f"μ 기울기 "
                f"{A.num('literature.mu_eps.das_phantom3_mono.mu_a', fmt='{:.2f}', unit='dB/GHz')}"],
               ["A(f) 레벨", "절대 레벨", "**우리 PO 출력**",
                f"`{D.num('anchor_modes.production_mode')}` 의 평균 레벨이동 "
                f"{D.num('anchor_modes.level_shift_abs_max_db', fmt='{:.2f}', unit='dB')}"],
               ["B₁(φ,θ)", "자세에 따른 모양", "**기하**(광선 가림 + PO)",
                f"재보정 후 정규화 패턴 변화 "
                f"{D.num('anchor.shape_invariance_max_abs_db', fmt='{:.1e}', unit='dB')}"],
               ["B₂", "자세 요동의 분포족", "기하",
                f"문헌 적합 RMSE {A.num('literature.fit_rmse_db.AAV', fmt='{:.2f}', unit='dB')} 가 "
                f"기준선"]]), "",
        f"생산 원장({D.num('anchor.slope_ledger_source_generation')} 세대 · 재실행 대기)에서 "
        f"정렬 후 7기종 기울기가 모두 "
        f"{D.num('anchor.slope_after_db_per_ghz', fmt='{:.3f}', unit='dB/GHz')} 위에 서고, 기종 간 "
        f"산포는 {D.num('anchor.slope_after_spread_db_per_ghz', fmt='{:.1e}', unit='dB/GHz')} 다. "
        f"주파수 눈금만 측정에서 오고 레벨과 모양은 그대로다.", "",
        f"⚠ **이 표(생산 앵커 원장)와 §4 도입의 우리 기울기는 σ 사슬의 서로 다른 세대다.** 생산 "
        f"원장은 {D.num('anchor.slope_ledger_source_generation')} 판 `rcs_anchor.json` 위에 서 "
        f"있고, §4 도입은 디스크의 현재 `rcs_anchor.json`"
        f"({A.num('meta.generated')} 판)에서 다시 적합한 값이다 — 겹치는 "
        f"{D.num('anchor.n_slope_crosschecked', fmt='{:.0f}')}기체에서 밴드 기울기가 최대 "
        f"{D.num('anchor.slope_ledger_gap_max_db_per_ghz', fmt='{:.3f}', unit='dB/GHz')} 갈린다"
        f"({D.num('anchor.slope_ledger_gap_max_drone')}). 생산 앵커는 이 라운드에서 그대로 두고 "
        f"사슬 재실행은 §6 표에 둔다 — 앵커를 갈아끼우려면 σ 사슬 전체를 한 세대로 맞춰야 하고, "
        f"그것은 05편 전체가 먹는 값이다.", "",
        f"⚠ **그리고 두 세대 모두 {MFX.num('_meta.date')} 형상 정정 전 메쉬 위에 서 있다** — 이 "
        f"축은 위 문단의 세대 축과 별개다. 앵커 5기체 중 Matrice 4E 가 그 정정을 받았고, §4 도입의 "
        f"기울기와 §4.1·§4.3·§4.4 의 표도 같은 사슬 위에 있다 "
        f"⟨{J_MESHFIX_ATK} : Q6_invalidated_outputs.critical[1]⟩."))

    B.append(md(
        "### §4.3 비교가능성 원장 — 기체마다 앵커와의 거리가 다르다", "",
        f"앵커 기체는 {D.num('anchor.anchor_platform')} 한 대다. 같은 급이면 `direct`"
        f"({D.num('anchor.n_direct', fmt='{:.0f}')}대), 크기법칙으로 옮기면 `scaled`"
        f"({D.num('anchor.n_scaled', fmt='{:.0f}')}대), 위상 자체가 다르면 `not_comparable`"
        f"({D.num('anchor.n_not_comparable', fmt='{:.0f}')}대)로 적는다. "
        f"⚠ 이 표도 §4.2 와 같은 생산 원장 세대이고 {MFX.num('_meta.date')} 형상 정정 전 메쉬 "
        f"위에 있다 — Matrice 4E 행이 그 정정을 받은 기체다.", "",
        table_from("outputs/sigma_anchor.json:drones",
                   [("기체", "name"), ("대각 D [m]", "comparability.D_m"),
                    ("D/D_ref", "comparability.size_ratio"),
                    ("로터", "comparability.num_rotors"),
                    ("판정", "comparability.verdict"),
                    ("L²↔L⁴ 산포 [dB]", "comparability.size_law_spread_db")],
                   fmt={"comparability.D_m": "{:.3f}",
                        "comparability.size_ratio": "{:.2f}",
                        "comparability.num_rotors": "{:.0f}",
                        "comparability.size_law_spread_db": "{:.2f}"},
                   order=DRONE_ORDER)))

    B.append(md(
        "### §4.4 앵커가 통제한 항목과 남은 항목의 크기", "",
        f"각 항목을 상태와 dB 크기로 함께 싣는다. 05편의 밴드 간 비교는 이 표와 나란히 읽는다. "
        f"⚠ 이 표도 §4.2·§4.3 과 같은 사슬 위에 있다 — 생산 원장 세대이고 "
        f"{MFX.num('_meta.date')} 형상 정정 전 메쉬다.", "",
        table_from("outputs/sigma_anchor.json:uncontrolled",
                   [("항목", "term"), ("상태", "status"), ("크기 [dB]", "size_db")],
                   fmt={"size_db": "{:+.2f}"}, null="미상"), "",
        f"가장 큰 항은 **{D.num('anchor.largest_uncontrolled_term')}** "
        f"{D.num('anchor.largest_uncontrolled_db', fmt='{:.2f}', unit='dB')} 이고, 실제 적용한 보정 "
        f"최대치 {D.num('anchor.correction_abs_max_db', fmt='{:.2f}', unit='dB')} 보다 크다. "
        f"그래서 커널은 그대로 두고 **원장으로만** 적용한다 — 05편이 이 표를 함께 읽는다. "
        f"⭐ 표의 `polarisation` 칸은 이제 크기를 갖는다 — 얇은 판 참값에서 폭 "
        f"{LFN.num('thin_plate.per_width.0.15.a_lam', fmt='{:.2f}')} λ 일 때 두 편파가 "
        f"{LFN.num('thin_plate.truth_2d_mom.0.15.tm_minus_te_db', fmt='{:.2f}', unit='dB')} "
        f"갈리는데 우리 면적분은 편파를 가르지 않는 스칼라(방향 구분 없이 세기 하나만 내는 양)다"
        f"(§3.1a). 그 낙차가 이 항의 크기이고, "
        f"부호는 06편 VV/HH 측정이 정한다."))

    # ── §4.5 ⭐ 눈감기 대조 — 앵커 기체를 문헌값을 보지 않고 낸 뒤 봉인을 풀었다 ─────
    #    정본 대조는 전대역 대 전대역이다. 부분대역 행은 μ(f) 의 곡률을 보이는 설명이고,
    #    우리 운용 밴드 셋이 전부 그 저주파 구간에 있다는 사실을 같은 셀에서 적는다.
    B.append(md(
        "### §4.5 ⭐ 눈감기 대조 — Phantom 3 를 문헌값을 보지 않고 내고 봉인을 풀었다 (v1 메쉬)",
        "",
        f"앵커 기체와 같은 기체(DJI Phantom 3)를 같은 창 "
        f"{P3V.num('slope.das_published.band[0]', fmt='{:.1f}')}~"
        f"{P3V.num('slope.das_published.band[1]', fmt='{:.1f}', unit='GHz')} 에서 우리 커널로 돌렸다"
        f"(`benchmark/p3_ours.py`, {P3O.num('meta.runtime_s_total_process', fmt='{:.0f}', unit='s')}). "
        f"산출 과정은 문헌 상수를 한 번도 읽지 않았고 봉인은 별도 스크립트가 풀었다"
        f"(`benchmark/p3_validation.py`). 적합 창은 Das Table III · Yuan §IV 와 같다"
        f"(일치 {P3V.num('window.same_window')}). ⚠ **이 절의 표 네 행은 전부 v1 메쉬 산출이다** — "
        f"기체 형상표를 물려받아 지은 판이고, 사진 실측으로 다시 지은 v2 메쉬의 같은 두 스칼라는 "
        f"§4.6 첫 문단이 잇는다.", "",
        "이 대조가 재는 것은 절대 레벨과 주파수 의존 두 스칼라이고, 각도패턴은 우리 기하에서 나온 "
        "그대로다. Das 의 Phantom 3 행은 Yuan 원자료의 재분석이라 독립 2건이 아니다.", "",
        table(["대조 상대", "고도 · 창", "기울기 [dB/GHz]", "우리와의 거리"],
              [["우리 el=0 전대역 (눈감기 산출)",
                "el=0 · " + P3V.num("slope.das_published.band[0]", fmt="{:.1f}") + "–"
                + P3V.num("slope.das_published.band[1]", fmt="{:.1f}", unit="GHz"),
                f"{P3V.num('slope.ours_el0_full_band.a', fmt='{:.3f}')} ± "
                f"{P3V.num('slope.ours_el0_full_band.se_a', fmt='{:.3f}')} "
                f"(양 끝점 제외 "
                f"{P3V.num('slope.ours_slope_robustness.drop_both_endpoints', fmt='{:.3f}')})", "—"],
               ["Das 공표 (IEEE WCL 2026)", "고도풀링 · 같은 창",
                f"{P3V.num('slope.das_published.a', 0.21, '{:.2f}')}",
                f"{P3V.num('slope.ratios.ours_over_das', fmt='{:.2f}')}배 · "
                f"{P3V.num('slope.significance.z_vs_das_0p21', fmt='{:.1f}')}σ"],
               ["Yuan θ=90° 실측곡선 (EuCAP 2025)", "고도정합 · 같은 창",
                f"{P3V.num('slope.yuan_theta90_published.a', 0.315, '{:.3f}')}",
                f"{P3V.num('slope.ratios.ours_over_yuan_theta90', fmt='{:.2f}')}배 · "
                f"{P3V.num('slope.significance.z_vs_yuan_theta90_0p315', fmt='{:.1f}')}σ · 레벨 "
                f"{P3V.num('residual.vs_yuan_theta90_measured_curve.mean_db', fmt='{:+.2f}', unit='dB')}"],
               ["부분대역 1.8–6.0 GHz (설명)", "el=0 · 실측곡선 대조",
                f"우리 {P3O.num('subband_fits.by_aspect.el0.1.8-6.0 GHz.a', fmt='{:.2f}')} vs 측정 "
                f"{P3V.num('our_operating_band.measured_theta90_curve_dense.a', fmt='{:.2f}')}",
                f"{P3V.num('our_operating_band.slope_ratio', fmt='{:.2f}')}배 · 1.8 GHz 레벨 "
                f"{P3V.num('our_operating_band.level_error_db.at_1p8', fmt='{:+.2f}', unit='dB')}"]]), "",
        f"정본 대조는 전대역 대 전대역이다 — 부분대역 행은 우리 μ(f) 가 "
        f"{P3O.num('subband_fits.by_aspect.el0.1.8-6.0 GHz.a', fmt='{:.2f}')}(1.8–6.0 GHz)에서 "
        f"{P3O.num('subband_fits.by_aspect.el0.6.0-18.2 GHz.a', fmt='{:.2f}', unit='dB/GHz')}"
        f"(6.0–18.2 GHz)로 꺾인다는 것을 보이는 설명이다.", "",
        f"⚠ **우리 세 밴드(LTE {D.num('bands_ghz.LTE', fmt='{:.3f}')} · 5G "
        f"{D.num('bands_ghz.5G', fmt='{:.1f}')} · WiFi "
        f"{D.num('bands_ghz.WiFi', fmt='{:.2f}')} GHz)가 전부 그 저주파 구간 안에 있고, "
        f"거기서 우리 σ 는 실측곡선보다 낮다.** 이 낙차의 **방향은 결과 밖에 둔다**(어느 쪽이 더 "
        f"그럴듯한지는 아래에 적는다) — 우리 PO "
        f"적분은 편파를 가르지 않는 스칼라라서, 참값이 편파에 따라 갈리는 구간에서는 한쪽 편파 "
        f"기준으로 낮게 다른 쪽 기준으로 높게 나온다 "
        f"⟨{J_LOWF_ATK} : what_survives_the_attack[4]⟩. ⭐ 다만 두 쪽의 크기는 서로 다르다 — 얇은 판 "
        f"참값에서 **전력을 만드는 쪽**(두 편파 중 σ 가 "
        f"{LFN.num('thin_plate.truth_2d_mom.0.15.tm_minus_te_db', fmt='{:.2f}', unit='dB')} 큰 "
        f"쪽) 기준이면 우리 PO 는 "
        f"{LFN.num('thin_plate.truth_2d_mom.0.15.po_minus_tm_db', fmt='{:+.2f}', unit='dB')} "
        f"(음수 = 우리가 낮다), 약한 쪽 기준이면 "
        f"{LFN.num('thin_plate.truth_2d_mom.0.15.po_minus_te_db', fmt='{:+.2f}', unit='dB')} 다. "
        f"그래서 **우리 σ 가 낮게 나와 있을 개연성 쪽이 크고**, 그 방향이라면 05편 검출 산출물은 "
        f"보수적인(비관적인) 쪽으로 틀린 것이다. 다만 레벨을 만드는 굵은 부품일수록 이 어긋남이 "
        f"작아서, 이 항이 설명하는 몫은 관측된 낙차보다 작다 "
        f"⟨{J_LOWF_ATK} : q4_A_and_B_are_not_exclusive."
        f"the_dB_decomposition_the_files_refuse_to_do.my_crude_budget.reading⟩ — 그래서 방향은 "
        f"여기까지, 개연성으로만 적는다. 지금 정확히 말할 수 있는 것은 **저주파 σ "
        f"의 불확도가 지금 선언된 것보다 크고 그 크기를 아직 못 정했다** 는 것이고, 금칙 세 "
        f"가지는 §3.1a 에 있다."))

    # ── §4.6 · §4.7 ⭐ 대조군과 함대 — 메쉬가 사는 축은 무엇이고 잣대는 무엇인가 ────
    #    ⛔ OC-01: 레벨을 이긴 구는 «논문표기 상자 부피» 등가 구다. 메쉬부피 등가 구는 우리보다
    #       나쁘다 — 구의 부피 선택 자체가 자유 매개변수이므로 그 사실을 같은 문장에 적는다.
    #    ⛔ OC-02: p3_validation_v2 는 Yuan θ90 곡선 눈금, das_fleet 은 Das Table III 눈금이다.
    #       잣대를 밝히지 않고 «구가 이긴다» 를 쓰면 반대 결과 하나를 지우게 된다.
    CT = "controls.table"
    B.append(md(
        "### §4.6 상자·구 대조군 — 메쉬가 사는 축은 절대 크기가 아니라 각도 구조다", "",
        f"**레벨을** 같은 눈금({PV2.num('controls.scoring')})으로 놓고 Phantom 3 를 상자·정육면체·"
        f"구로 바꿔 넣어 다시 채점했다(다음 문단의 ε 는 잣대가 다르다 — 거기서 밝힌다). "
        f"우리 메쉬는 **상자 계열을 전부 이긴다** — 가장 가까운 정육면체가 레벨 "
        f"{PV2.num(f'{CT}.cube_vol_v2.level_err_db', fmt='{:+.2f}')} 인데 우리는 "
        f"{PV2.num(f'{CT}.ours_phantom3_mesh_v2.level_err_db', fmt='{:+.2f}', unit='dB')} 다. "
        f"⚠ 그런데 **레벨 하나만 보면 부피를 맞게 고른 구가 우리보다 낫다** — 논문표기 상자와 "
        f"부피가 같은 구가 "
        f"{PV2.num(f'{CT}.sphere_eqvol_paperbox.level_err_db', fmt='{:+.2f}')} · 주파수 전체에 "
        f"걸친 평균 오차 크기(rms) "
        f"{PV2.num(f'{CT}.sphere_eqvol_paperbox.rms_db', fmt='{:.2f}', unit='dB')} 다. ⭐ 다만 "
        f"**그 구의 부피를 무엇으로 잡는가가 자유 매개변수**(결과를 보고 골라 넣을 수 있는 값)다 "
        f"— 메쉬 부피와 같은 구는 "
        f"{PV2.num(f'{CT}.sphere_vol_v2.level_err_db', fmt='{:+.2f}', unit='dB')} 로 우리보다 "
        f"나쁘다.", "",
        f"⭐ **이 절의 «우리» 는 v2 메쉬**(사진 실측으로 다시 지은 판)이고, §4.5 표의 «우리» 는 "
        f"v1 메쉬다. 같은 Yuan θ90 곡선 잣대에서 v1→v2 는 레벨오차 "
        f"{PV2.num('v1_vs_v2.level_db.v1', fmt='{:+.2f}')} → "
        f"{PV2.num('v1_vs_v2.level_db.v2', fmt='{:+.2f}', unit='dB')}, 기울기 "
        f"{PV2.num('v1_vs_v2.slope_db_per_ghz.v1', fmt='{:.3f}')} → "
        f"{PV2.num('v1_vs_v2.slope_db_per_ghz.v2', fmt='{:.3f}', unit='dB/GHz')}"
        f"(촘촘하게 되살린 실측곡선 "
        f"{PV2.num('v1_vs_v2.slope_db_per_ghz.measured_comparand_dense', fmt='{:.3f}', unit='dB/GHz')}) "
        f"로 움직인다 — 레벨은 가까워지고 기울기는 멀어졌다. 형상은 삼각형 "
        f"{PV2.num('v1_vs_v2.mesh.v1_n_tri', fmt='{:,.0f}')}→"
        f"{PV2.num('v1_vs_v2.mesh.v2_n_tri', fmt='{:,.0f}')} · 실루엣 IoU 가 자기복제 상한 대비 "
        f"{PV2.num('v1_vs_v2.mesh.silhouette_iou_pct_of_ceiling.old', fmt='{:.1f}')}→"
        f"{PV2.num('v1_vs_v2.mesh.silhouette_iou_pct_of_ceiling.new', fmt='{:.1f}', unit='%')} 다. "
        f"헤드라인 결과 5 와 §4.5 는 v1 값을 든다.", "",
        f"구는 방위에 따라 σ 가 그대로라 방위 산포 ε(같은 기체를 여러 방위에서 볼 때 σ 가 얼마나 "
        f"흩어지는지, dB)를 "
        f"{PV2.num(f'{CT}.sphere_eqvol_paperbox.eps_mean_db', fmt='{:.2f}', unit='dB')} 로 낸다 — "
        f"⚠ **ε 만은 잣대가 다르다**: ε 의 비교 상대는 위 레벨이 쓴 Yuan 곡선이 아니라 Das Table III 가 "
        f"준 {PV2.num('v1_vs_v2.eps_db.das_mean', fmt='{:.2f}', unit='dB')} 다(레벨은 Yuan 잣대, "
        f"ε 는 Das 잣대). 그 Das 잣대에서 우리는 "
        f"{PV2.num(f'{CT}.ours_phantom3_mesh_v2.eps_err_vs_das_db', fmt='{:+.2f}')}, 상자 계열은 "
        f"{PV2.num(f'{CT}.cube_vol_v2.eps_err_vs_das_db', fmt='{:+.2f}')}~"
        f"{PV2.num(f'{CT}.box_paper.eps_err_vs_das_db', fmt='{:+.2f}', unit='dB')} 다. **그래서 "
        f"메쉬가 값어치를 내는 축은 σ 의 절대 크기가 아니라 각도에 따른 구조다** — 절대 레벨은 "
        f"06편 교정구가 측정으로 앵커한다(06 §2-2). ⭐ **레벨에서 구가 이겼는지 졌는지를 가른 것은 "
        f"잣대가 아니라 어느 구를 넣었는가** 다 — 메쉬 부피로 잡은 같은 반지름의 구를 레벨까지 "
        f"Das Table III 잣대로 다시 "
        f"채점해도 같은 Phantom 3 에서 우리("
        f"{FLT.num('box_control.phantom3.ours_DL_db', fmt='{:+.2f}')})가 구("
        f"{FLT.num('box_control.phantom3.controls.sphere_eqvol.DL_db', fmt='{:+.2f}', unit='dB')})를 "
        f"이긴다(그쪽 표는 구의 σ 를 단면적 πa² 로 굳힌 근사로, 이 표는 정확해(Mie)로 낸다 — 반지름은 "
        f"같다). 즉 **두 잣대 모두에서 지는 것은 메쉬 부피로 잡은 구**이고, 레벨에서 우리를 앞선 "
        f"것은 반지름을 그보다 키운 논문표기 상자부피 구 하나다. 두 결과는 «어느 부피를 골랐나» 와 "
        f"함께 읽는다.", "",
        "### §4.7 같은 잣대를 네 기체로 — 사전등록 대조", "",
        f"Das Table III 는 네 기체를 바이스태틱각 일곱 개로 준다 — 그 칸을 전부 채점했다"
        f"(⟨{J_FLEET} : table_28⟩). 합격규칙은 "
        f"**계산 전에** 봉인했고(`outputs/das_fleet_prereg.json`) 그대로 썼다. 결정권을 준 "
        f"항목은 「{PRG.num('pass_rule.primary_gate_level_at_theta_b_0.P3_spread')}」 이고, "
        f"판정은 **{FLT.num('prereg_judgement.verdict')}** 다 — 실제 산포가 "
        f"{FLT.num('prereg_judgement.P3_spread_db', fmt='{:.2f}', unit='dB')} 다. "
        f"⚠ 용어 두 개를 먼저 푼다. 판정 문자열의 **P3 은 봉인한 합격조건 네 개 중 세 번째**"
        f"(레벨오차의 산포)를 가리키는 이름이고 기체 Phantom 3 를 뜻하지 않는다. 그리고 "
        f"**레벨오차 DL(0)** 는 **바이스태틱각 0°(송신기와 수신기가 같은 자리에 있는 배치)에서 측정 대비 "
        f"우리 σ 가 몇 dB 높거나 낮은가**다 — 양수면 우리가 더 밝게 냈다는 뜻이다.", "",
        f"⭐ 갈린 축은 대역도 전기적 크기도 기체 크기도 아니고 **그 기체 자체의 형상 증거가 "
        f"있는가** 다 — 형상 증거가 있는 Mini 2 "
        f"{FLT.num('prereg_judgement.DL0_db.mini2', fmt='{:+.2f}')} · Phantom 3 "
        f"{FLT.num('prereg_judgement.DL0_db.phantom3', fmt='{:+.2f}')} 와 증거가 얇은 Phantom 2 "
        f"{FLT.num('prereg_judgement.DL0_db.phantom2', fmt='{:+.2f}')} · M350 RTK "
        f"{FLT.num('prereg_judgement.DL0_db.m350rtk', fmt='{:+.2f}', unit='dB')} 사이에 "
        f"{FLT.num('degrees_of_freedom.evidence_split.gap_db', fmt='{:.2f}', unit='dB')} 의 빈 "
        f"구간이 있다. 봉인이 예측한 산포는 "
        f"{FLT.num('prereg_judgement.spread_predicted_db', fmt='{:.1f}', unit='dB')} 였다 — 예측이 "
        f"반증됐고 일치도가 메쉬 구속도를 따라간다는 두 사실이 함께 서 있고, 그것은 결과에 맞춰 "
        f"맞춘 흔적의 정반대 서명이다 ⟨{J_FLEET_ATK} : Q5_tuned_evidence⟩. ⚠ M350 RTK 값은 계산이 "
        f"다 끝나기 전의 스냅샷에서 집계됐고, Mini 2 행은 §1 과 같은 형상 정정 전 메쉬에서 나온 "
        f"값이다 — 둘 다 재집계를 기다린다 "
        f"⟨{J_FLEET_ATK} : overall.required_before_citing[0]⟩ · "
        f"⟨{J_MESHFIX_ATK} : Q6_invalidated_outputs.critical[0]⟩."))

    # ── §5  ⭐ 이 편이 논문에 주는 두 번째 물건 — σ 오차 아래의 순위 강건성 ───────
    B.append(md(
        "## §5. σ 오차를 넣어도 파형 순위가 서는 범위", "",
        f"σ 오차를 두 갈래로 나눠 검출거리 R90 순위에 넣었다(`benchmark/sigma_sensitivity.py`, "
        f"기체 {D.num('sigma_sens.n_airframes', fmt='{:.0f}')} × 밴드 {D.num('sigma_sens.n_bands', fmt='{:.0f}')} = "
        f"{D.num('sigma_sens.n_cells', fmt='{:.0f}')}셀). **공통모드**는 한 기체의 세 밴드를 같은 dB 로 "
        f"옮기고(절대 레벨 오차의 모양), **차분**은 밴드마다 다르게 옮긴다(기울기 오차의 모양).", "",
        f"공통모드에서 순위는 "
        f"{D.num('sigma_sens.offset_min_db', fmt='{:.0f}')}~+{D.num('sigma_sens.offset_max_db', fmt='{:.0f}', unit='dB')} "
        f"전 구간 {D.num('sigma_sens.n_cells', fmt='{:.0f}')}셀에서 그대로다 — 움직이는 것은 절대거리뿐이고 "
        f"그 기울기가 σ 1 dB 당 {D.num('sigma_sens.slope_mean_db_per_db', fmt='{:.3f}', unit='dB')}"
        f"({D.num('sigma_sens.slope_min_db_per_db', fmt='{:.3f}')}~"
        f"{D.num('sigma_sens.slope_max_db_per_db', fmt='{:.3f}')}), 즉 σ ±10 dB 에서 거리 "
        f"{D.num('sigma_sens.range_at_minus10_pct', fmt='{:+.0f}')} %~"
        f"{D.num('sigma_sens.range_at_plus10_pct', fmt='{:+.0f}', unit='%')} 다. "
        f"**논문이 절대 σ 에 기대는 곳은 여기서 끝난다.**", "",
        f"차분오차가 순위를 정하는 축이고, 그래서 §4 의 앵커가 잡는 축이 정확히 이것이다. "
        f"자세평균 σ 로 인용하면 다섯 기체가 한 순위"
        f"({D.num('sigma_sens.aspect_avg_order')})에 합의하고"
        f"(단일자세에서는 순위 {D.num('sigma_sens.single_aspect_n_orders', fmt='{:.0f}')}종), 거기에 측정 "
        f"기울기를 얹으면 최악 뒤집힘 문턱이 "
        f"{D.num('sigma_sens.worst_flip_aspect_avg_db', fmt='{:.2f}')} → "
        f"{D.num('sigma_sens.worst_flip_anchored_db', fmt='{:.2f}', unit='dB')} 로 올라간다"
        f"(+{D.num('sigma_sens.anchor_gain_db', fmt='{:.2f}', unit='dB')})."))

    B.append(md(
        figure_md("outputs/figures/report02_f7_sigma_sensitivity.png", 7,
                  "σ 오차가 어느 축으로 얼마나 커질 때 세 파형의 순위가 뒤집히는가?",
                  paper_caption="A common-mode RCS error leaves the three-waveform ranking "
                                "unchanged over the full sweep and moves only absolute "
                                "range, while a per-band differential error is the axis "
                                "that decides the ranking and is the axis the measured "
                                "frequency slope anchors.",
                  report="report02_target"), "",
        table_from("outputs/report02_derived.json:sigma_sens.rows",
                   [("기체", "airframe"), ("최대 치수 [m]", "extent_m"),
                    ("D/λ @LTE", "d_over_lambda_lte"),
                    ("뒤집힘 문턱 · 단일자세 [dB]", "flip_single_db"),
                    ("뒤집힘 문턱 · 자세평균 [dB]", "flip_aspect_avg_db"),
                    ("밴드간 σ 산포 [dB]", "band_sigma_spread_db"),
                    ("P(순위 보존) @1 dB", "p_order_1db")],
                   fmt={"extent_m": "{:.3f}", "d_over_lambda_lte": "{:.2f}",
                        "flip_single_db": "{:.2f}", "flip_aspect_avg_db": "{:.2f}",
                        "band_sigma_spread_db": "{:.1f}", "p_order_1db": "{:.3f}"}), "",
        f"⚠ Matrice 4E 행은 {MFX.num('_meta.date')} 형상 정정 전 값이다 — 이 표를 낸 "
        f"`{J_SIGSENS}` 가 그 기체의 형상을 먹는다 "
        f"⟨{J_MESHFIX_ATK} : Q6_invalidated_outputs.critical[3]⟩. 재계산은 §6 표에 있고, 이 표가 "
        f"사는 주장(뒤집힘 문턱은 크기가 아니라 로브 산포가 정한다)은 한 기체 값이 움직여도 "
        f"그대로 선다."))

    #  §5.1 «이 표를 논문이 쓰는 법» 은 셀 [25] 논문블록과 01편 §4.1.1 이 같은 말을 들므로 뺐다.
    #  인용 규약(자세평균 · slope_only 델타 적용)은 §5 본문과 §6 첫 줄이 그대로 든다.

    # ── 재현용 코드 셀 ─────────────────────────────────────────────────────
    B.append(code(
        "# 이 편의 숫자를 직접 열어보기 — 그림·표의 모든 값은 아래 JSON 에서 나온다.",
        "import json",
        "D = json.load(open('outputs/report02_derived.json'))",
        "P = D['provenance']",
        "print('메쉬 소스 최신 편집 :', P['mesh_source_newest'],",
        "      f\"— 읽는 JSON {P['n_sources']}개 중 새것 {P['n_fresh']} · 옛것 {P['n_stale']}\")",
        "for r in P['rows']:",
        "    print(f\"  {'새것' if r['fresh'] else '옛것'}  {r['source']:28s} \"",
        "          f\"{r['stamp']}  {r['used_in']}\")",
        "print('사진 대조 :', {r['airframe']: round(r['iou'], 3) for r in D['photo']['rows']})",
        "print('가림 [dB] :', {r['airframe']: round(r['d_occlusion_db'], 2)",
        "                     for r in D['occlusion']['rows']})",
        "print('앵커 원장 :', {k: D['anchor'][k] for k in",
        "      ('mode', 'from_measurement', 'from_ours', 'largest_uncontrolled_db')})"))

    # ── 다음 단계 ──────────────────────────────────────────────────────────
    B.append(next_steps([
        ("R90 사슬에 `modes.slope_only.delta_db` 를 적용한다",
         f"앵커 후 파형 순위가 확정된다 — 지금 적용하면 "
         f"{D.num('sigma_sens.anchor_not_applied_n_order_changed', fmt='{:.0f}')}기체의 순위가 "
         f"바뀐다",
         "`src/experiment_freespace_sigma.py` → 05편 §5"),
        ("σ 를 다시 돌리기 전에 형상 관문을 통과시킨다 — 선언된 기하 결함을 끄거나 고치고, "
         "σ 캐시 키에 메쉬 지문을 넣고, 봉인해 둔 예측과 대조해 **틀린 것을 먼저 기록**한다",
         "새 σ 가 형상 정정 때문에 움직인 것인지 다른 것 때문인지 구별된다 — 그 전에는 형상 "
         "정정을 σ 의 의미로 말하지 않는다",
         f"⟨{J_MESHFIX_ATK} : recommended_gate_before_any_sigma_claim⟩"),
        ("§1 의 형상 원장 넷(갤러리·사진·공식 CAD·재질/가림)을 정정된 메쉬로 다시 돌린다",
         f"§1 의 표·그림과 §2 가림 표가 현재 형상 위에 선다 — 지금은 z 축 배율부터 "
         f"{MFX.num('per_drone.matrice4e.fit_scale_before[2]', fmt='{:.3f}')}→"
         f"{MFX.num('per_drone.matrice4e.fit_scale_after[2]', fmt='{:.3f}')}(Matrice 4E) "
         f"만큼 어긋나 있고 세 기체의 메쉬 지문이 전부 다르다",
         "`src/viz_mesh_gallery.py` · `viz_mesh_photo.py` · `viz_cad_compare.py` · "
         "`viz_mesh_material.py`"),
        ("자세 패턴과 부품별 스트립을 현재 메쉬로 다시 재어 이 편에 되싣는다",
         f"현재 기하 위의 자세 패턴 σ 가 확정된다 — 동일설정 재생성 대조에서 기체당 최대 "
         f"{RGN.num('overstated[0].결과_표[0].max_abs_delta_db', 22.36, '{:.2f}')} · rms "
         f"{RGN.num('overstated[0].결과_표[0].rms_delta_db', 10.82, '{:.2f}', 'dB')} 가 움직인다",
         "`src/viz_report2.py` → `outputs/report2_waveform_rcs.json`"),
        ("§4 의 앵커 사슬(rcs_anchor → sigma_anchor)을 현재 메쉬로 다시 돌린다",
         f"밴드 기울기와 재보정 원장이 현재 기하 위에 선다 — 재생성 평균이 기체마다 "
         f"{RGN.num('overstated[0].결과_표[0].mean_delta_db', -5.7, '{:+.2f}')} ~ "
         f"{RGN.num('overstated[0].결과_표[2].mean_delta_db', 3.18, '{:+.2f}', 'dB')} 로 반대 방향이다",
         "`benchmark/rcs_anchor.py` → `src/sigma_anchor.py`"),
        (f"생산 σ 를 `ptd=True` 로 다시 낸다 (세 진입점 배선 완료 · 기본 꺼짐 · 비용 "
         f"+{PTW.num('verdict.cost_increase_pct', fmt='{:.1f}', unit='%')})",
         f"모서리 항이 밴드 기울기를 얼마나 옮기는지가 수치로 남는다 — ⚠ 저대역 격차를 이 항이 "
         f"메울 것으로 기대하지 않는다: 얇은 판 참값 대조에서 1차 항은 정면입사의 두 편파를 "
         f"똑같이 두고, 한쪽 편파를 고치는 대신 다른 쪽을 더 멀어지게 한다 "
         f"⟨{J_LOWF_ATK} : what_survives_the_attack[3]⟩",
         "`benchmark/rcs_anchor.py --ptd` → `outputs/rcs_anchor_ptd.json`"),
        ("Phantom 3 구 대조군을 방위 산포 ε 축까지 포함해 다섯 기체로 넓힌다",
         "형상 모형이 각도 구조를 사는 폭이 기체마다 확정된다 — §4.6 이 낸 것은 «레벨 축에서 "
         "상자 계열은 우리 메쉬에 지고, 부피를 맞게 고른 구는 우리와 같은 자리에 온다» 까지다. "
         "레벨 축을 닫는 것은 06편 교정구다",
         "`benchmark/p3_validation_v2.py` 확장 → 02편 §4.6"),
        (f"PO 면적분을 디바이스 커널로 옮긴다 (지금 호스트 몫 "
         f"{RB.num('answer.cost_structure.host_side_pct', fmt='{:.1f}', unit='%')} · PO 단계 "
         f"{RB.num('production_per_pose.stage_pct_median_over_configs.po', fmt='{:.1f}', unit='%')})",
         f"전격자 재생성 비용이 결정된다 — 현재 추정 "
         f"{RB.num('production_per_pose.whole_published_grid.projected_hours', fmt='{:.2f}', unit='h')}",
         "`src/rcs_sbr.py` → `outputs/runtime_benchmark.json` 재측정"),
        ("§1 의 그림 넷을 게재 규격(벡터 + 300 dpi · 8 pt)으로 다시 그린다",
         "원고 그림 전부가 2단 조판 축소에서 살아남는다",
         "`src/viz_mesh_gallery.py` · `src/viz_mesh_material.py` → `paper_kit.save_figure`"),
        ("Matrice 4E · Mini 5 Pro 의 짐벌·착륙장치를 사진 실루엣에 맞춘다",
         "실측 두 기체의 IoU 가 상한 대비 어디까지 오르는지 결정된다",
         "`src/drone_cad.py` → §1.1 재측정"),
        ("Matrice 4E · Mini 5 Pro 의 상대 레벨을 실측한다",
         "크기전이 지수가 직접 고정되어 §4.4 의 최대 항이 닫힌다",
         "06편 §2 측정 설계"),
        ("교정구를 표적과 같은 자리에서 함께 잰다",
         "지금 우리 PO 출력인 절대 레벨이 처음으로 측정에 앵커된다",
         "06편 §2-2 → `src/sigma_anchor.py` 레벨 앵커 승격"),
        ("VV/HH 2편파를 잰다",
         "§4.4 편파 항의 크기가 수치로 확정된다",
         "06편 §2 → `src/materials.py:171` 편파 분해 결정"),
        ("평판·이면각 표준체로 같은 kr 스윕을 돌린다",
         "얇고 모서리 많은 표적에서의 PO 간극 문턱이 선다",
         "`benchmark/verify_sbr_defect_fixes.py` 의 두 닫힌형 재사용"),
        ("2회 반사를 β 별로 다시 돌린다",
         "바이스태틱 유효범위가 45° 위로 얼마나 넓어지는지 결정된다",
         "`src/rcs_sbr.py:330` 상반성 검사"),
        ("회전 블레이드 마이크로도플러를 검증 가능한 형태로 세운다",
         "미세도플러 서명을 이 커널 위에서 인용할 수 있게 된다",
         "future work (Costa, IEEE JSTEAP 의 해석 경로가 기준선)"),
    ], sec="§6."))

    # ── 논문 참고자료 블록 (PAPER_SPEC §4.2·§4.4·§4.5) — 셀 하나로 묶는다 ──────────
    METHOD_EN = (
        "Each airframe is a watertight triangle mesh built from the published outer "
        "dimensions, the motor-to-motor diagonal and the propeller diameter, with every "
        "face keeping its part-level material group (metal, PCB, camera assembly, carbon, "
        "plastic shell, propeller); the reflection coefficients are the ITU-R P.2040 "
        "values that Sionna 2.0.1 itself uses. For one incidence direction we call "
        "Sionna's Mitsuba/OptiX ray engine for a first-hit visibility test on a ray grid "
        "of pitch lambda/12, then integrate the physical-optics surface current over the "
        "lit facets only, E = sum_i |Gamma_i| exp(j 2 k p_i . u) dA and sigma = 4 pi |E|^2 "
        "/ lambda^2; thin dielectric shells are transmitted with the round-trip factor "
        "tau = 1 - |Gamma|^2 and the metal behind them is summed coherently, and for a "
        "bistatic pair a second shadow ray is cast from every hit point toward the "
        "receiver. The kernel is checked against three closed-form reference solutions - "
        "the analytic physical-optics sphere, the exact Mie PEC sphere and the PEC "
        "dihedral 8 pi a^2 b^2 / lambda^2 - over kr = 1 to 100 at 21 points and 48 "
        "incidence directions. The absolute level of sigma is the kernel output; only the "
        "frequency slope is re-anchored, onto the measured 0.210 dB/GHz of Das et al., "
        "which rotates sigma(f) about the band-mean level and leaves the normalised "
        "aspect pattern unchanged. Software: Sionna 2.0.1, Sionna-RT 2.0.1, Mitsuba 3.8.0, "
        "Dr.Jit 1.3.1, NumPy 2.5.0, Python 3.12.")

    B.append(paper_appendix(
        methods_block=methods(METHOD_EN, tools=["Sionna 2.0.1", "Mitsuba 3.8.0",
                                                "Python 3.12"],
                              report="report02_target", sec="§7."),
        defence_block=defence([
            ("표적 σ 는 부품별 재질 메쉬 위의 PO 면적분으로 계산하고, 커널은 해석 PO 기준해와 "
             "kr 1~100 전 구간에서 "
             + S.num("summary_div16.max_abs_db_vs_po", fmt="{:.3f}", unit="dB") + " 안에서 맞는다",
             "그림 5 · 표 §3.1 · `outputs/sbr_kr_sweep.json:summary_div16.max_abs_db_vs_po`",
             "PO 는 few-λ 표적에서 부정확하다 — 드론이 바로 그 크기다",
             "눈금 두 개로 나눠 답한다. (1) 매끄러운 구에서는 정확 Mie 로 재서 kr ≥ "
             + D.num("po_floor.kr_below_1p0_db", fmt="{:.2f}") + " 에서 1 dB, kr ≥ "
             + D.num("po_floor.kr_below_0p5_db", fmt="{:.2f}") + " 에서 0.5 dB 안이다 "
             "⟨outputs/report02_derived.json : po_floor⟩. (2) **드론에 맞는 눈금은 그것이 "
             "아니다** — 얇은 판 참값(2D MoM)으로 재면 PO 오차가 1 dB 아래로 가는 문턱이 부품 "
             "폭 ≥ "
             + LFN.num("thin_plate.truth_2d_mom_fine_width_grid.knee_a_over_lam", fmt="{:.3f}")
             + " λ 이고, 우리 세 밴드는 전부 그 아래다(§3.1a). 그래서 이 편은 **σ 의 절대 "
             "크기를 주장하지 않고** 각도 구조와 밴드 간 상대 순위를 주장한다(§5). 절대 레벨은 "
             "06편 교정구가 측정으로 앵커한다"),

            ("가림 판정은 Sionna 의 Mitsuba/OptiX 광선엔진이 하고, 표면전류 적분과 σ 출력을 "
             "우리가 얹었다",
             "§2 표 · `outputs/prior_settled_sionna.json:word_counts_rerun_this_session`",
             "Sionna 에도 SBR 이 있으니 엔진 기여는 이미 그 안에 있다",
             "기술보고서(v1.2, 59쪽)에 SBR 은 "
             + PS.num(f"{WC}.SBR or shooting-and-bouncing", fmt="{:.0f}")
             + "회 나오고 우리도 그 엔진을 그대로 쓴다. 같은 문서에서 `physical optics` "
             + PS.num(f"{WC}.physical optics", fmt="{:.0f}") + "회 · `radar cross section` "
             + PS.num(f"{WC}.radar cross section", fmt="{:.0f}")
             + "회이므로, 더한 것은 표면적분과 σ 출력이다"),

            ("절대 레벨은 우리 PO 출력이고, 측정에서 받은 것은 주파수 기울기 하나다",
             "그림 6 · 표 §4.2 · `outputs/report02_derived.json:anchor_modes`",
             "절대 σ 가 측정으로 검증되지 않았다면 검출 결과 전체가 흔들린다",
             "공통모드 σ 오차는 세 밴드를 함께 옮겨 "
             + D.num("sigma_sens.n_cells", fmt="{:.0f}") + "셀 전부에서 순위를 그대로 두고, "
             "절대거리만 σ 1 dB 당 "
             + D.num("sigma_sens.slope_mean_db_per_db", fmt="{:.3f}", unit="dB")
             + " 움직인다 ⟨outputs/sigma_sensitivity.json : common_mode⟩. ⚠ 다만 σ 오차를 "
             "**완전한** 공통모드로 볼 근거는 아직 없다 — PO 근사의 유효 문턱이 부품마다 다른 "
             "주파수에 있어서(§3.1a) 밴드마다 다르게 들어간다. 그 밴드 간 차이의 크기는 06편 "
             "캠페인 §4-1 이 잰다. 논문은 순위를 주장하고, 절대 레벨은 06편 교정구로 앵커한다"),

            ("밴드별 차분 σ 오차의 뒤집힘 문턱은 기체별 "
             + D.num("sigma_sens.flip_single_min_db", fmt="{:.2f}") + "~"
             + D.num("sigma_sens.flip_single_max_db", fmt="{:.2f}", unit="dB") + " 다",
             "그림 7 · 표 §5 · `outputs/sigma_sensitivity.json:differential`",
             "그 문턱이 현실 차분 폭 "
             + D.num("sigma_sens.realistic_span_db", fmt="{:.2f}", unit="dB")
             + " 안에 드는 기체가 셋이다 — 그 폭 안에서 순위가 바뀐다",
             "인용 규약을 두 개로 고정해서 답한다 — 자세평균 σ 로 인용하면 다섯 기체가 한 순위"
             "에 합의하고, 측정 기울기를 얹으면 최악 문턱이 "
             + D.num("sigma_sens.worst_flip_aspect_avg_db", fmt="{:.2f}") + "→"
             + D.num("sigma_sens.worst_flip_anchored_db", fmt="{:.2f}", unit="dB")
             + " 로 올라간다. 남은 차분은 06편이 두 기체의 밴드별 상대 레벨로 닫는다"),

            ("바이스태틱 자세 패턴은 β ≤ 45° 에서 성립하고, 그 범위의 상반성 RMS 는 "
             + rms45 + " 다",
             "§2.1 · `outputs/sbr_defect_fixes.json:d2_exit_vis_effect_on_reciprocity`",
             "β > 45° 에서 상반성이 크게 깨진다면 엔진 자체를 믿기 어렵다",
             "출사 쪽 가림을 켜면 위반 최대치가 " + worst_off + " → " + worst_on
             + " 로 내려간다. 논문은 β ≤ 45° 만 쓰고, 그 위는 2회 반사를 β 별로 다시 돌려 "
             "§6 에서 넓힌다"),

            ("가림은 방위평균 σ 를 기체별 "
             + D.num("occlusion.min_db", fmt="{:.2f}") + "~"
             + D.num("occlusion.max_db", fmt="{:.2f}", unit="dB") + " 옮긴다",
             "그림 4 · 표 §2 · `outputs/report02_derived.json:occlusion.rows`",
             "그 차이가 이산화 잡음일 수 있다",
             "PO 를 λ/7↔λ/12 로 돌린 이산화 바닥이 최대 "
             + D.num("occlusion.floor_max_db", fmt="{:.3f}", unit="dB") + " 이고, "
             + D.num("occlusion.n_above_floor", fmt="{:.0f}") + "기체 전부에서 가림이 그 위에 있다"),

            ("메쉬 형상은 사진 실루엣 · 제조사 CAD 치수 · 실물 유래 메쉬 셋으로 검사했다",
             "그림 2 · 표 §1.2 · `outputs/report02_derived.json:photo`",
             "IoU " + D.num("photo.best_iou", fmt="{:.3f}") + " 는 눈금 없는 숫자다 — "
             "형상 정확도의 어떤 기준에 대는 값인가",
             "같은 메쉬로 만든 가짜 사진을 같은 파이프라인에 넣은 자기복제 상한 "
             + D.num("photo.ceiling_min", fmt="{:.3f}") + "~"
             + D.num("photo.ceiling_max", fmt="{:.3f}")
             + " 을 함께 싣고 상한 대비로 읽는다. 자세 1° 오차에서 그 지표가 "
             + D.num("photo.iou_at_1deg_pose_error", fmt="{:.3f}") + " 로 내려간다"),

            ("이 편의 기여는 GPU 광선엔진 위의 부품별 재질 PO 와 그것을 검출 사슬까지 잇는 "
             "파이프라인 통합이다",
             "§2 표 · 01편 §3 · `outputs/prior_settled_h8.json`",
             "Rzewuski(NATO STO 2021)가 FDTD 로 드론 바이스태틱 RCS 를 패시브 예산에 넣고 "
             "50 m OTA 검출까지 냈다 — 같은 산출물이다",
             "같은 산출물을 다른 엔진으로 낸다는 것을 그대로 적는다. 우리가 더하는 것은 "
             "GPU 광선엔진 안에서의 부품별 재질 PO, 교정된 Pfa 위의 세 파형 통제 비교, "
             "그리고 σ 오차 아래 순위 강건성의 수치화다(§5). 메쉬를 정교하게 짓는 일이 사 "
             "주는 것은 σ 의 **절대 크기가 아니라 각도에 따른 구조**다 — 레벨만 보면 모양을 "
             "전혀 안 닮은 구도 부피를 맞게 골라 넣으면 같은 자리에 오고(§4.6: 그 구는 논문이 "
             "적어 둔 상자 치수로 잡은 부피다. 메쉬 부피로 잡으면 두 잣대 모두에서 우리보다 "
             "나쁘다), 구는 방위 산포를 원리적으로 "
             "0 으로 낸다. 그 축이 메쉬가 갚는 자리다. 게재본과 프리프린트 구분은 01편 §3 에 "
             "있다"),
        ], sec="§7.", report="report02_target"),
        citations=[
            cite_ref("das", note="Table III · 기울기 앵커(§4)"),
            cite_ref("sionna_rt_techreport", note="SBR 48회 · PO 표면적분 0회(§2)"),
            cite("Liu et al.",
                 "Clutter-Aware Integrated Sensing and Communication: Models, Methods, "
                 "and Future Directions", "Proceedings of the IEEE", volume="114(1)",
                 pages="52-91", year=2026, status="published",
                 doi="10.1109/JPROC.2026.3675476",
                 note="드론 메쉬를 Sionna 에 넣고 stock 응답을 받는 게재 선행(§2)"),
            cite("Zhang et al.",
                 "A Unified RCS Modeling of Typical Targets for 3GPP ISAC Channel "
                 "Standardization", "IEEE Journal on Selected Areas in Communications",
                 volume="44", pages="702-716", year=2026, status="published",
                 doi="10.1109/JSAC.2025.3608732",
                 note="sigma = A(f)·B1(phi,theta)·B2 분해의 출처(§4)"),
            cite_ref("rzewuski", note="FDTD 로 같은 산출물 — 신규성은 엔진과 통합에 있다"),
            cite("Pasquale et al.",
                 "BVH-Accelerated Ray Tracing for High-Frequency Electromagnetic "
                 "Backscattering", "arXiv preprint", year=2026, status="preprint",
                 arxiv="2604.09243", note="바이스태틱 출사 가림을 지목한 각주(§2.1)"),
        ],
        sec="§7."))

    return B

# =========================================================================== #
def main():
    print("── 리포트 02 빌드 ──")
    J, kr_grid, d_db = derive()
    fig_mesh_photo(J)
    fig_reference_gap(J, kr_grid, d_db)
    fig_band_slope(J)
    fig_sigma_sensitivity(J)
    rep = build_notebook(NB_OUT, blocks(J), strict=True)
    print(f"✅ {os.path.relpath(NB_OUT, _ROOT)}")
    return rep


if __name__ == "__main__":
    main()
