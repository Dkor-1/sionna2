# -*- coding: utf-8 -*-
"""
make_report06_measurement.py — 리포트 06 「실측」 빌더  →  report06_measurement.ipynb
============================================================================================
계약서 두 장이 동시에 걸린다.
  · `docs/REBUILD_2026-07-30.md` §5 — 서술규약. 강제는 `src/report_style.py`.
  · `docs/PAPER_SPEC.md` §4 — 논문 참고자료 규격. 강제는 `src/paper_kit.py`.

이 편의 역할: **논문 VI. Validation 절의 소스**이자 다음 라운드의 계약서.
⭐ 헤드라인은 "캠페인이 검출 사슬과 파형 상대순위를 결판낸다" 다 — 순위를 뒤집는 폭
   (자세평균 flip span)이 세션 드리프트 예산 위에 있다는 것이 설계와 판정 대상의 일치다.
   교정된 절대 σ 는 §2 여섯 항목이 다음 라운드에서 만드는 **더 센 주장**으로 둔다.

이 파일이 하는 일 (한 번 실행하면 셋 다 나온다)
  ① **파생 JSON** `outputs/report06_derived.json` — 두 원본 JSON 에 흩어져 있거나 아예 값으로
     없는 설계값을 여기서 계산해 디스크에 남긴다. 손으로 친 숫자를 0개로 만들기 위한 장치다.
       · 원거리장 2D²/λ — **D 정의 세 가지**를 한 표에 모은다(정의가 섞이면 거리가 2배 틀린다)
       · 교정구 여유 — 정확 Mie σ 와 기체 예상 σ 의 차 [dB]
       · 점표적 조건 — 서브밴드 거리분해능 vs 기체 최대치수
       · 자세 각도표본 — λ/4D 권장 간격과 한 바퀴 표본수
       · 크기법칙 L²/L⁴ **차등신호** — 두 기체를 함께 재면 얼마로 갈리는가
       · 기울기 판별폭 — 우리 3밴드 기울기와 앵커 기울기가 대역 끝에서 벌리는 간격
       · 지면반사 유령의 경로차 vs 거리분해능
       · **순위 판정** — 자세평균 뒤집힘 폭 vs 세션 드리프트 예산 (판정 대상과 설계의 일치)
  ② **그림 6장** — ADC 여유 · 원거리장 · 교정구 · 크기법칙 · 기울기 · 지면반사.
     전부 `paper_kit.save_figure()` 로 **벡터 PDF + 400 dpi PNG** 동시 저장, 2단 폭 7.16 in ·
     최소 글자 8 pt · 색+마커/선종/해치 이중부호화를 저장 직전에 검사한다.
  ③ **노트북** `report06_measurement.ipynb` — 논문 대응 블록(머리) · 방어선 8행 · 방법 문단 ·
     인용 3편을 포함한다.

실행
  cd /home/yunjung/workspace/sionna2
  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py

읽는 것 (전부 저장소에 이미 있는 산출물)
  outputs/report06_measurement.json  ← benchmark/plan_measurement.py
  outputs/measurement_plan.json      ← src/sigma_anchor.py :: write_measurement_plan()
  outputs/sigma_anchor.json          ← src/sigma_anchor.py

⚠ numpy/scipy + Mie 기준해만 쓴다 — CPU 로 약 10 초.
⚠ 이 편이 담는 것은 **계산된 설계값**이다: 원거리장 · 교정구 · 서브밴드 · 각도표본 · 판정 임계.
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

from report_style import (assert_fig_text, build_notebook, code,      # noqa: E402
                          from_json, header, md, next_steps, table)
from paper_kit import (attach, cite, cite_ref, defence, figure_md,     # noqa: E402
                       methods, paper_appendix, paper_map, paper_style,
                       save_figure)

C0 = 299792458.0
FIGDIR = os.path.join(_ROOT, "outputs", "figures")
DERIVED = os.path.join(_ROOT, "outputs", "report06_derived.json")
NB_OUT = os.path.join(_ROOT, "report06_measurement.ipynb")

R6 = os.path.join(_ROOT, "outputs", "report06_measurement.json")
MP = os.path.join(_ROOT, "outputs", "measurement_plan.json")
SA = os.path.join(_ROOT, "outputs", "sigma_anchor.json")
SS = os.path.join(_ROOT, "outputs", "sigma_sensitivity.json")
#: 실측 3층 설계 — 1층 σ(f) 레인지 · 2층 ISM 파형축 · 검증 3점 · 3층 비행검출
ML = os.path.join(_ROOT, "outputs", "measurement_layers.json")

#: 세션 드리프트 예산 [dB] — 교정구를 세션 시작·끝에 재고 두 값의 차가 이 안에 든 세션만 자료로 쓴다.
#: 설계 상수라서 여기 한 곳에만 있고, 파생 JSON 을 통해 리포트로 나간다.
DRIFT_BUDGET_DB = 1.0

#: 구매 확정 2종. 순서 = 큰 것 먼저.
AIR = ("matrice4e", "mini5pro")
#: 교정 기준체 — 문헌이 실제로 쓴 두 금속구.
SPHERES = ("0.178", "0.25")
#: 서브밴드 후보 [MHz] — X410 순시대역 400 을 쪼갠다.
BW_MHZ = (400, 200, 100, 50)
#: 밴드 표시 이름 → 짧은 이름
SHORT = {"LTE 1.843 GHz": "LTE", "5G 3.5 GHz": "5G", "WiFi 5.21 GHz": "WiFi"}

#: 재보정 모드 — 생산 기준은 `slope_only` 이고, 그 모드가 옮기는 것은 **주파수 기울기 하나**다.
#: 절대 레벨은 우리 PO 출력 그대로 남는다. 레벨을 앵커에 맞추는 두 모드는 크기전이 법칙을
#: 하나 골라야 하고, 이 편은 그 두 모드를 **설계 계산에만** 쓴다(교정구 고르기 · 크기법칙 차등).
#: 이 캠페인이 사러 가는 것이 바로 그 레벨 앵커다(§2-2).
MODES = [
    ("slope_only", "주파수 기울기만", "생산 σ 원장 (02편 §4) · §4 결정표"),
    ("level_and_slope_L2", "레벨 + 기울기 (L²)", "§2-2 예상 σ — 교정구 반경·동적범위 설계"),
    ("level_and_slope_L4", "레벨 + 기울기 (L⁴)", "§4-2 크기법칙 차등신호"),
]


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# =========================================================================== #
#  ①  파생값 — 리포트가 인용할 수 있도록 디스크에 남긴다
# =========================================================================== #
def derive(verbose=True) -> dict:
    """설계값을 계산해 `outputs/report06_derived.json` 에 쓴다. 측정은 하지 않는다."""
    t0 = time.time()
    r6, mp, sa = _load(R6), _load(MP), _load(SA)
    bands = list(r6["bands"].keys())

    # ── 원거리장: D 정의 세 가지를 같은 표에 ──────────────────────────────────
    #   env  = 회전 로터 디스크까지 포함한 외접상자의 3D 대각 (가장 큼 → 채택)
    #   bbox = 프로펠러 포함 수평 최대치수 (radar_scene.target_extent)
    #   diag = 모터-모터 대각 (앵커 문헌 Das/Yuan 의 관례)
    ff_rows = []
    for dk in AIR:
        e, m = r6["farfield"][dk], mp["airframes"][dk]
        for b in bands:
            lam = r6["bands"][b]["lam_m"]
            ff_rows.append(dict(
                airframe=dk, band=SHORT[b], lam_mm=lam * 1e3,
                D_env_m=e["D_m"], R_ff_env_m=e["bands"][b]["R_ff_m"],
                D_bbox_m=m["D_bbox_m"], R_ff_bbox_m=m["by_band"][b]["farfield_m_bbox"],
                D_diag_m=m["D_diagonal_m"], R_ff_diag_m=m["by_band"][b]["farfield_m_diag"],
                spread_ratio=e["bands"][b]["R_ff_m"] / m["by_band"][b]["farfield_m_diag"]))
    worst = max(ff_rows, key=lambda r: r["R_ff_env_m"])

    # ── 교정 기준체: 정확 Mie σ 와 기체 예상 σ 의 여유 ────────────────────────
    exp = mp["expected_sigma_dbsm_from_anchor"]["by_drone"]
    cal_rows = []
    for rs in SPHERES:
        sk, mk = f"sphere_r{rs}", f"r={float(rs):.3f}m"
        for b in bands:
            mie = r6["farfield"][sk]["bands"][b]["mie_dbsm"]
            cal_rows.append(dict(
                sphere=f"r={float(rs)*100:.1f} cm", band=SHORT[b],
                ka=mp["calibration_spheres"][mk][b]["ka"], mie_dbsm=mie,
                mie_minus_go_db=mp["calibration_spheres"][mk][b]["mie_minus_go_db"],
                R_ff_m=r6["farfield"][sk]["bands"][b]["R_ff_m"],
                margin_matrice4e_db=mie - exp["matrice4e"]["L2"][b],
                margin_mini5pro_db=mie - exp["mini5pro"]["L2"][b]))
    cal_margin_min = min(min(r["margin_matrice4e_db"], r["margin_mini5pro_db"])
                         for r in cal_rows)

    # ── 점표적 조건: 서브밴드 거리분해능 c/2B 가 기체 최대치수보다 커야 한다 ──
    pt_rows = []
    for bw in BW_MHZ:
        dr = C0 / (2.0 * bw * 1e6)
        row = dict(B_MHz=bw, dR_m=dr)
        for dk in AIR:
            D = mp["airframes"][dk]["D_bbox_m"]
            row[f"{dk}_margin_m"] = dr - D
            row[f"{dk}_ok"] = "점표적" if dr > D else "⚠ 퍼짐"
        pt_rows.append(row)
    #  ⚠ 대역이 넓을수록 ΔR 이 작아 조건이 어려워진다 → 만족하는 것 중 **가장 넓은** 대역.
    bw_ok = max([r["B_MHz"] for r in pt_rows
                 if all(r[f"{d}_ok"] == "점표적" for d in AIR)], default=None)

    # ── 자세 각도표본: 권장 간격 λ/4D 와 한 바퀴 표본수 ───────────────────────
    asp_rows = []
    for dk in AIR:
        for b in bands:
            v = mp["airframes"][dk]["by_band"][b]
            step = v["az_step_recommended_deg"]
            asp_rows.append(dict(airframe=dk, band=SHORT[b],
                                 az_nyquist_deg=v["az_step_nyquist_deg"],
                                 az_recommended_deg=step,
                                 n_az_per_turn=360.0 / step,
                                 finer_than_anchor_2deg=bool(step < 2.0)))
    asp_min = min(asp_rows, key=lambda r: r["az_recommended_deg"])

    # ── 크기법칙 L²/L⁴ — 두 기체를 함께 재면 갈리는가 ─────────────────────────
    sl = {}
    for dk in AIR:
        c = sa["drones"][dk]["comparability"]
        sl[dk] = dict(size_ratio=c["size_ratio"],
                      corr_L2_db=c["size_corr_L2_db"], corr_L4_db=c["size_corr_L4_db"],
                      spread_db=c["size_corr_L4_db"] - c["size_corr_L2_db"],
                      verdict=c["verdict"],
                      mu_L2_dbsm={SHORT[b]: exp[dk]["L2"][b] for b in bands},
                      mu_L4_dbsm={SHORT[b]: exp[dk]["L4"][b] for b in bands})
    size_law = dict(
        by_airframe=sl,
        differential_db=abs(sl["matrice4e"]["spread_db"] - sl["mini5pro"]["spread_db"]),
        definition="(L4-L2)_matrice4e - (L4-L2)_mini5pro [dB]. 두 기체가 앵커보다 "
                   "각각 크고 작으므로 두 법칙의 예측이 **반대 방향**으로 갈린다.",
        uncontrolled_size_db=[u for u in sa["uncontrolled"]
                              if u["term"] == "size transfer law"][0]["size_db"])

    # ── 재보정 모드 — 어느 모드가 무엇을 옮기고, 이 편의 어느 절이 그것을 쓰나 ──
    #   ⭐ 생산 모드(slope_only)의 평균 레벨이동은 0 이다 — 절대 레벨은 우리 PO 출력이다.
    #      이 캠페인이 사러 가는 것이 그 레벨의 측정 앵커다(교정구, §2-2).
    mode_rows = []
    for mode, moves, used in MODES:
        #  slope_only 은 정의상 0 이다 — 부동소수 잔여(~1e-15)가 "-0.00" 으로 찍히지 않게 정리한다.
        d = {dk: (lambda v: 0.0 if abs(v) < 5e-3 else v)(
            float(np.mean(list(sa["drones"][dk]["modes"][mode]["delta_db"].values()))))
             for dk in AIR}
        mode_rows.append(dict(
            mode=mode + (" (생산 기본)" if mode == "slope_only" else ""),
            moves=moves, used_in=used,
            matrice4e_db=d["matrice4e"], mini5pro_db=d["mini5pro"]))
    modes = dict(
        rows=mode_rows, production_mode="slope_only",
        level_shift_production_abs_max_db=max(abs(mode_rows[0][f"{dk}_db"]) for dk in AIR),
        definition="평균 레벨이동 = 세 밴드 delta_db 의 산술평균 [dB]. slope_only 는 밴드 "
                   "비가중 평균 레벨을 축으로 회전만 시키므로 0 이고, 절대 레벨은 우리 PO "
                   "출력 그대로다. 나머지 두 모드는 크기전이 법칙으로 축까지 옮긴다.")

    # ── 기울기 판별폭 — 세션 재현성 요구치 ───────────────────────────────────
    span = float(r6["slope_discrimination"]["band_span_ghz"])
    a_anchor = float(sa["drones"][AIR[0]]["modes"]["slope_only"]["slope_anchor_db_per_ghz"])
    slope_rows = []
    for dk in AIR:
        a = sa["drones"][dk]["slope_ours_3band_db_per_ghz"]
        slope_rows.append(dict(airframe=dk, ours_db_per_ghz=a, anchor_db_per_ghz=a_anchor,
                               ratio_over_anchor=a / a_anchor, gap_db=(a - a_anchor) * span))
    slope = dict(rows=slope_rows, span_ghz=span, anchor_db_per_ghz=a_anchor,
                 gap_db_min=min(r["gap_db"] for r in slope_rows),
                 fit_note_short="세 밴드 방위평균 μ 를 f[GHz] 에 1차 적합(el=0)",
                 definition="ours = sigma_anchor.json:drones.<k>.slope_ours_3band_db_per_ghz "
                            "(세 밴드 방위평균 mu 를 f[GHz] 에 1차 적합, el=0). "
                            "gap = (ours - anchor) * span — 대역 끝에서 두 가설이 벌리는 간격 [dB]. "
                            "세션간 진폭 재현성이 이보다 나빠야 기울기 판정이 성립한다.")

    # ── 지면반사 유령: 경로차 2hH/R 이 거리분해능보다 커야 게이팅으로 뗀다 ────
    gb_rows = []
    for k, v in mp["ground_bounce"].items():
        if k.startswith("_"):
            continue
        h, H, R = (float(s.split("=")[1].rstrip("m")) for s in k.split(","))
        gb_rows.append(dict(h_m=h, H_m=H, R_m=R, path_diff_m=v,
                            sep_at_200MHz=bool(v > C0 / (2 * 200e6)),
                            sep_at_100MHz=bool(v > C0 / (2 * 100e6))))
    gb_frac200 = sum(r["sep_at_200MHz"] for r in gb_rows) / len(gb_rows)
    gb_ref_bw = 200

    # ── 순위 판정 — 이 캠페인이 결판내는 양과 그 문턱 ─────────────────────────
    #   ⭐ 논문이 주장하는 것은 세 파형의 **순위와 격차**다. 그 순위를 뒤집는 데 필요한
    #      밴드별 σ 이동폭(flip span)이 곧 캠페인의 진폭 재현성 요구치다. 세션 드리프트
    #      예산이 그 폭 아래에 있으면 캠페인 설계가 판정 대상과 맞는다.
    ss = _load(SS)
    aa, mc = ss["aspect_averaged"], ss["monte_carlo_per_band_error"]
    flip = {dk: aa["by_drone"][dk]["smallest_flip_span_db"] for dk in AIR}
    flip_k = min(flip, key=lambda k: flip[k])
    ranking = dict(
        consensus_order=aa["consensus_order"],
        all_drones_agree=aa["all_drones_agree"],
        n_drones=len(aa["orders"]),
        flip_span_db=flip,
        flip_span_min_db=flip[flip_k],
        flip_span_min_airframe=flip_k,
        single_aspect_flip_span_min_db=min(
            aa["by_drone"][dk]["single_aspect_smallest_flip_span_db"] for dk in AIR),
        drift_budget_db=DRIFT_BUDGET_DB,
        drift_margin_db=flip[flip_k] - DRIFT_BUDGET_DB,
        az_step_deg=asp_min["az_recommended_deg"],
        p_order_preserved_at_1db={
            dk: mc["by_drone"][dk]["by_sigma_e_db"]["1.0"]["p_order_preserved"]
            for dk in AIR},
        common_mode_slope_db_per_db=ss["common_mode"]["slope_mean"],
        rows=[dict(airframe=dk,
                   flip_span_aspect_avg_db=flip[dk],
                   flip_span_single_aspect_db=aa["by_drone"][dk][
                       "single_aspect_smallest_flip_span_db"],
                   drift_budget_db=DRIFT_BUDGET_DB,
                   margin_db=flip[dk] - DRIFT_BUDGET_DB,
                   p_order_at_1db=mc["by_drone"][dk]["by_sigma_e_db"]["1.0"][
                       "p_order_preserved"]) for dk in AIR],
        mc_basis="단일자세 lead 위의 몬테카를로 (benchmark/sigma_sensitivity.py:430)",
        definition="flip_span = 자세평균 σ 에서 두 파형의 R90 순서를 뒤집는 데 필요한 밴드별 "
                   "σ 이동폭 [dB] ⟨sigma_sensitivity.json : aspect_averaged.by_drone.<k>."
                   "smallest_flip_span_db⟩. margin = flip_span − drift_budget. "
                   "common_mode_slope_db_per_db = σ 를 세 밴드 공통으로 1 dB 옮길 때 "
                   "절대거리가 움직이는 dB — 순위는 그 이동에서 불변이다.")

    # ── 실측 3층 — 층마다 다른 축을 연다 (outputs/measurement_layers.json) ────
    #   1층이 σ(f) 를 내고, 2층이 파형 구조를 한 반송파에서 가르고, 3층이 비행 검출을 잰다.
    #   ⭐ 1층이 내는 것은 점별 패턴이 아니라 **분포 P(σ)** 다 — 검출확률이 그 분포의 함수다.
    ml = _load(ML)
    l2, v3, l3 = (ml["layer2_waveform_axis"], ml["validation_three_points"],
                  ml["layer3_flight"])
    ang, cal = ml["angular_sampling"], ml["calibration_convention_gap"]
    gate = ml["gate_wide_evaluate_narrow"]
    bands_l1 = " · ".join(v3["points"][k]["label"] for k in ("lte", "nr", "wifi"))
    layers = dict(
        rows=[
            dict(layer="1층 — σ(f) 레인지",
                 measures="정지 표적 · 턴테이블 방위컷 · 교정구 · 배경 코히런트 차감",
                 carrier=f"{bands_l1} (§2)",
                 product="σ(f, φ) 의 분포 P(σ)"),
            dict(layer="2층 — 파형축",
                 measures="세 파형 구조를 같은 서브밴드 중심에 겹쳐 송신",
                 carrier=f"ISM {l2['carrier_hz'] / 1e9:.1f} GHz 단일 "
                         f"(span {l2['span_hz'] / 1e6:.0f} MHz)",
                 product="SNR_out / E_tx"),
            dict(layer="3층 — 비행 검출",
                 measures="로터가 도는 비행 표적 — 로터가 도는 유일한 층",
                 carrier=f"ISM {l2['carrier_hz'] / 1e9:.1f} GHz",
                 product="고정 Pfa 에서 Pd(range)")],
        carrier_ism_ghz=l2["carrier_hz"] / 1e9,
        span_ism_mhz=l2["span_hz"] / 1e6,
        validation_points=bands_l1,
        validation_receive_only=bool(v3["receive_only"]),
        n_channels=2,
        channels=v3["channels"],
        layer3_headline=l3["headline"],
        layer3_ties_back_to=l3["ties_back_to"],
        #  ⚠ 이 값은 **bbox 정의**의 2D²/λ 다 — §2-1 이 채택한 env 정의와 섞지 않는다.
        farfield_ism_bbox_max_m=max(ml["layer1_at_ism"]["airframes"][k]["farfield_m"]
                                    for k in AIR),
        anchor_step_deg=ang["anchor_step_deg"],
        anchor_N=ang["anchor_N"],
        anchor_too_coarse_1=ang["anchor_2deg_too_coarse_at"][0],
        anchor_too_coarse_2=ang["anchor_2deg_too_coarse_at"][1],
        N_required_min=ang["N_required_range"][0],
        N_required_max=ang["N_required_range"][1],
        cal_anchor_declared_dbsm=cal["anchor_declared_sigma_cal_dbsm"],
        cal_pir2_dbsm=cal["pir2_dbsm"],
        mie_shift_min_db=min(cal["our_sigma_shift_if_we_use_mie_db"].values()),
        mie_shift_max_db=max(cal["our_sigma_shift_if_we_use_mie_db"].values()),
        gate_bw_mhz=gate["gate_bw_hz"] / 1e6,
        eval_bw_mhz=gate["eval_bw_hz"] / 1e6,
        n_subbands=gate["by_drone"][AIR[0]]["n_subbands"],
        definition="1층 = σ(f) 레인지(§2), 2층 = ISM 한 반송파의 파형축, 3층 = 비행 검출. "
                   "값은 outputs/measurement_layers.json 에서 옮기거나 단위만 바꿨다. "
                   "n_channels = 기준 1 + 감시 1 (공통 클럭, 수신전용) — 하드웨어 사양의 "
                   "4 RX 와 구별한다.")

    J = {
        "_meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "src/make_report06_measurement.py :: derive()",
            "purpose": "리포트 06 이 인용하는 **설계값**. 측정값은 하나도 없다.",
            "inputs": ["outputs/report06_measurement.json", "outputs/measurement_plan.json",
                       "outputs/sigma_anchor.json", "outputs/sigma_sensitivity.json",
                       "outputs/measurement_layers.json"],
            "paper_section": "VI. Validation",
            "definitions": {
                "R_ff": "2*D^2/lambda. D 정의 3종: env(로터 디스크 포함 외접상자 3D 대각) · "
                        "bbox(프로펠러 포함 수평 최대치수) · diag(모터-모터, 앵커 문헌 관례). "
                        "채택은 가장 보수적인 env.",
                "margin_*_db": "교정구 정확 Mie sigma - 기체 예상 sigma(L2 크기보정) [dB]. "
                               "양수면 교정구가 표적보다 밝다.",
                "dR_m": "c/(2B) — 모노스태틱 거리분해능. 점표적 조건은 dR > D_bbox.",
                "az_recommended_deg": "lambda/(4*D_bbox) [deg] — 방위 각도표본 권장 간격.",
                "gap_db": slope["definition"],
                "differential_db": size_law["definition"],
                "modes": modes["definition"],
                "path_diff_m": "2hH/R — 표적경유 지면반사와 직접 표적경로의 경로차 [m].",
                "ranking_validation": ranking["definition"],
                "layers": layers["definition"],
            },
            "runtime_s": None,
        },
        "farfield": ff_rows,
        "farfield_adopted": dict(
            D_def="env — 회전 로터 디스크를 포함한 외접상자의 3D 대각",
            R_ff_max_m=worst["R_ff_env_m"], airframe=worst["airframe"], band=worst["band"],
            spread_ratio_max=max(r["spread_ratio"] for r in ff_rows),
            why="D 정의를 모터대각으로 잡으면 요구거리가 절반 이하로 내려간다. "
                "로터는 전기적 산란체이므로 포함한다."),
        "calibration": cal_rows,
        "calibration_margin_min_db": cal_margin_min,
        "calibration_pick": dict(
            radius_m=float(SPHERES[0]), radius_cm=float(SPHERES[0]) * 100.0,
            why="세 밴드 모두 Mie−πr² 편차가 작고 앵커 문헌(Yuan)이 쓴 것과 같은 크기다."),
        "hw_span": dict(f_lo_mhz=r6["hw"]["f_lo_hz"] / 1e6,
                        f_hi_ghz=r6["hw"]["f_hi_hz"] / 1e9),
        "point_target": pt_rows,
        "point_target_max_bw_MHz": bw_ok,
        "aspect": asp_rows,
        "aspect_finest_deg": asp_min["az_recommended_deg"],
        "aspect_finest_airframe": asp_min["airframe"],
        "aspect_finest_band": asp_min["band"],
        "aspect_n_az_max": asp_min["n_az_per_turn"],
        "size_law": size_law,
        "modes": modes,
        "slope": slope,
        "ranking_validation": ranking,
        "layers": layers,
        "ground_bounce": gb_rows,
        "ground_bounce_ref_bw_MHz": gb_ref_bw,
        "ground_bounce_n_geom": len(gb_rows),
        "ground_bounce_sep_frac_200MHz": gb_frac200,
        "ground_bounce_min_m": min(r["path_diff_m"] for r in gb_rows),
        "ground_bounce_max_m": max(r["path_diff_m"] for r in gb_rows),
    }
    J["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    with open(DERIVED, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    if verbose:
        print(f"  원거리장 최대   : {worst['R_ff_env_m']:.2f} m "
              f"({worst['airframe']} · {worst['band']})")
        print(f"  교정구 최소여유 : {cal_margin_min:+.2f} dB")
        print(f"  점표적 최대대역 : {bw_ok} MHz")
        print(f"  각도표본 최소   : {asp_min['az_recommended_deg']:.2f}°")
        print(f"  크기법칙 차등   : {size_law['differential_db']:.2f} dB")
        print(f"  기울기 판별폭   : {slope['gap_db_min']:.2f} dB (최소)")
        print(f"  순위 뒤집힘 폭  : {ranking['flip_span_min_db']:.2f} dB "
              f"({ranking['flip_span_min_airframe']}) · 드리프트 여유 "
              f"{ranking['drift_margin_db']:+.2f} dB")
        print(f"  실측 3층        : 2층 반송파 {layers['carrier_ism_ghz']:.1f} GHz · "
              f"검증 3점 수신 {layers['n_channels']}채널(공통 클럭) · "
              f"교정 규약차 {layers['mie_shift_min_db']:+.2f}~"
              f"{layers['mie_shift_max_db']:+.2f} dB")
        print(f"✅ 파생값 저장 → outputs/report06_derived.json "
              f"({J['_meta']['runtime_s']} s)")
    return J


# =========================================================================== #
#  ②  그림 6장 — 게재 품질 (PAPER_SPEC §4.3)
#      · 벡터 PDF + 400 dpi PNG 동시 저장 (`save_figure`)
#      · 2단 폭 7.16 in 에서 본문 9 pt · 눈금/범례 8 pt — 축소 없이 그대로 조판된다
#      · 계열은 색 + 마커/선종/해치 **이중부호화** → 흑백 인쇄에서도 갈린다
#      · 글자는 전부 영어(하우스 규약). `save_figure` 가 저장 직전에 셋 다 검사한다.
# =========================================================================== #
def _pub(fig, name: str, paper_caption: str) -> dict:
    """게재 규격으로 저장하고 검사 결과를 찍는다. `name` 은 확장자 없는 파일 이름."""
    os.makedirs(FIGDIR, exist_ok=True)
    r = save_figure(fig, os.path.join("outputs", "figures", name),
                    dpi=400, caption=paper_caption, close=True)
    c = r.get("check", {})
    print(f"  🖼  {r['png']} + {r['pdf']}  "
          f"(min {c.get('min_font_pt')} pt · PNG {c.get('png_dpi')} dpi · "
          f"게재검사 {'통과' if c.get('ok') else c.get('violations')})")
    return r


CAP_EN = {
    "adc": ("Headroom of the 12-bit ADC dynamic range above the direct-path-to-noise "
            "ratio for the three waveforms, tightest for the LTE waveform."),
    "farfield": ("Far-field distance 2D^2/lambda for the two purchased airframes at the "
                 "three bands, under three definitions of the aperture D."),
    "calibration": ("Exact Mie cross section of candidate calibration spheres against the "
                    "expected drone level at the three bands."),
    "size_law": ("Mean cross section predicted by the L^2 and L^4 size-transfer laws for "
                 "one airframe larger and one smaller than the measurement anchor."),
    "slope": ("Frequency-slope hypotheses across the measured band span and the gap they "
              "open at the top of that span."),
    "ground": ("Target-via-ground path difference against range resolution, over antenna "
               "heights, target heights and ground ranges."),
}


def fig_adc(J):
    """12-bit ADC 동적범위가 직접파 대 잡음비 위에 얼마나 남는가."""
    r6 = _load(R6)
    dr = r6["adc"]["dynamic_range_db"]
    T = [f"Headroom of the 12-bit ADC dynamic range ({dr:.1f} dB) "
         f"above the direct-path-to-noise ratio",
         "Level [dB]", "Direct-path-to-noise ratio (DNR)",
         "Headroom to ADC full scale", "ADC full scale", "Waveform"]
    assert_fig_text(*T)
    wfs = list(r6["adc"]["per_waveform"].keys())
    dnr = [r6["adc"]["per_waveform"][w]["dnr_db"] for w in wfs]
    with paper_style(width="double", base_pt=9.0, aspect=0.36) as st:
        fig, ax = st.figure()
        y = np.arange(len(wfs), dtype=float)
        ax.barh(y, dnr, height=0.50, color=st.color(0), hatch="",
                edgecolor="black", linewidth=0.6, label=T[2])
        ax.barh(y, [dr - d for d in dnr], left=dnr, height=0.50, color=st.color(4),
                hatch="//", edgecolor="black", linewidth=0.6, label=T[3])
        ax.axvline(dr, color="black", lw=1.2, ls=(0, (5, 2)))
        ax.text(dr - 0.8, -0.62, T[4], ha="right", va="center", fontsize=8)
        for i, d in enumerate(dnr):
            ax.text(dr - 1.4, i, f"+{dr - d:.1f} dB", ha="right", va="center",
                    fontsize=8, bbox=dict(fc="white", ec="none", pad=1.2))
        ax.set_yticks(y, wfs)
        ax.set_ylim(-0.85, len(wfs) - 0.5 + 1.15)      # 위쪽 빈 띠 = 범례 자리
        ax.set_xlabel(T[1])
        ax.set_ylabel(T[5])
        ax.set_xlim(0, dr * 1.02)
        ax.set_title(T[0])
        ax.legend(loc="upper center", ncol=2)
        ax.grid(axis="y", visible=False)
    return _pub(fig, "report06_adc_headroom", CAP_EN["adc"])


def fig_farfield(J):
    """세 D 정의가 만드는 요구거리의 폭 — 정의를 섞으면 거리가 3.65배 틀린다."""
    T = ["Far-field distance 2D^2/lambda, D = envelope diagonal incl. rotor discs",
         "Required range [m]", "Band",
         "D = bbox max horizontal extent", "D = motor-to-motor diagonal",
         "Calibration sphere r = 17.8 cm", "DJI Matrice 4E", "DJI Mini 5 Pro"]
    assert_fig_text(*T)
    r6 = _load(R6)
    bands = list(r6["bands"].keys())
    xb = np.arange(len(bands), dtype=float)
    with paper_style(width="double", base_pt=9.0, aspect=0.40) as st:
        fig, ax = st.figure()
        xs_bb, ys_bb, xs_dg, ys_dg = [], [], [], []
        for i, (dk, lbl) in enumerate(zip(AIR, (T[6], T[7]))):
            rows = [r for r in J["farfield"] if r["airframe"] == dk]
            off = (i - 0.5) * 0.34
            ax.bar(xb + off, [r["R_ff_env_m"] for r in rows], width=0.30,
                   color=st.color(i), hatch=("", "//")[i], edgecolor="black",
                   linewidth=0.6, label=lbl)
            xs_bb += list(xb + off);  ys_bb += [r["R_ff_bbox_m"] for r in rows]
            xs_dg += list(xb + off);  ys_dg += [r["R_ff_diag_m"] for r in rows]
        ax.plot(xs_bb, ys_bb, linestyle="none", marker="s", ms=5, color="black",
                label=T[3])
        ax.plot(xs_dg, ys_dg, linestyle="none", marker="v", ms=6, color=st.color(5),
                label=T[4])
        sph = [r6["farfield"]["sphere_r0.178"]["bands"][b]["R_ff_m"] for b in bands]
        ax.plot(xb, sph, linestyle=(0, (4, 2)), marker="o", ms=4.5, lw=1.2,
                color=st.color(3), label=T[5])
        top = max(r["R_ff_env_m"] for r in J["farfield"])
        ax.annotate(f"{top:.1f} m", xy=(xb[-1] - 0.17, top),
                    xytext=(xb[-1] - 0.85, top * 0.90), fontsize=8,
                    arrowprops=dict(arrowstyle="->", lw=0.8))
        ax.set_xticks(xb, [SHORT[b] + f"\n{r6['bands'][b]['fc_hz']/1e9:.3g} GHz"
                           for b in bands])
        ax.set_xlabel(T[2])
        ax.set_ylabel(T[1])
        ax.set_title(T[0])
        ax.legend(ncol=2, loc="upper left")
        ax.set_ylim(0, top * 1.42)
    return _pub(fig, "report06_farfield", CAP_EN["farfield"])


def fig_calibration(J):
    """교정구 반경을 어떻게 고르나 — 정확 Mie 가 기체 예상 σ 위에 있어야 한다."""
    from mie_pec_sphere import sphere_reference_set
    T = ["Calibration sphere: exact Mie sigma against the expected drone level",
         "Sphere radius [m]", "sigma [dBsm]", "Optical limit pi*r^2",
         "Matrice 4E, expected (anchor, L^2)", "Mini 5 Pro, expected (anchor, L^2)",
         "r = 17.8 cm", "r = 25 cm"]
    assert_fig_text(*T)
    r6, mp = _load(R6), _load(MP)
    bands = list(r6["bands"].keys())
    rr = np.linspace(0.06, 0.32, 140)
    with paper_style(width="double", base_pt=9.0, aspect=0.42) as st:
        fig, ax = st.figure()
        for i, b in enumerate(bands):
            f = r6["bands"][b]["fc_hz"]
            assert_fig_text(SHORT[b])
            ax.plot(rr, [sphere_reference_set(float(x), f)["mie_dbsm"] for x in rr],
                    label=f"Mie, {SHORT[b]}", markevery=18, **st.series(i))
        ax.plot(rr, 10 * np.log10(np.pi * rr ** 2), color="black",
                linestyle=(0, (1, 1.4)), marker="", lw=1.1, label=T[3])
        exp = mp["expected_sigma_dbsm_from_anchor"]["by_drone"]
        for dk, lbl, ls in zip(AIR, (T[4], T[5]), ((0, (6, 2)), (0, (2, 2)))):
            lv = float(np.mean([exp[dk]["L2"][b] for b in bands]))
            ax.axhline(lv, color=st.color(5), ls=ls, lw=1.1)
            ax.text(0.318, lv + 0.35, lbl, fontsize=8, color=st.color(5), ha="right")
        for rs, lbl in zip(SPHERES, (T[6], T[7])):
            ax.axvline(float(rs), color="0.45", lw=0.9)
            ax.text(float(rs) - 0.004, -25.6, lbl, fontsize=8, rotation=90,
                    color="0.30", va="bottom", ha="right")
        ax.set_xlabel(T[1])
        ax.set_ylabel(T[2])
        ax.set_ylim(-26, -3)
        ax.set_title(T[0])
        ax.legend(loc="upper left", ncol=2)
    return _pub(fig, "report06_calibration", CAP_EN["calibration"])


def fig_size_law(J):
    """두 기체를 함께 재면 L² 와 L⁴ 가 반대 방향으로 갈린다."""
    T = ["L^2 versus L^4 size-transfer law, predicted from the measurement anchor\n"
         "Matrice 4E is larger than the anchor airframe, Mini 5 Pro smaller",
         "Frequency [GHz]", "mu [dBsm]", "Matrice 4E", "Mini 5 Pro",
         "Differential signature"]
    assert_fig_text(*T)
    r6 = _load(R6)
    bands = list(r6["bands"].keys())
    fg = [r6["bands"][b]["fc_hz"] / 1e9 for b in bands]
    sl = J["size_law"]["by_airframe"]
    with paper_style(width="double", base_pt=9.0, aspect=0.42) as st:
        fig, ax = st.figure()
        k = 0
        for dk, lbl in zip(AIR, (T[3], T[4])):
            for law, key in (("L^2", "mu_L2_dbsm"), ("L^4", "mu_L4_dbsm")):
                ax.plot(fg, [sl[dk][key][SHORT[b]] for b in bands],
                        label=f"{lbl} · {law}", **st.series(k))
                k += 1
            y2 = sl[dk]["mu_L2_dbsm"][SHORT[bands[-1]]]
            y4 = sl[dk]["mu_L4_dbsm"][SHORT[bands[-1]]]
            ax.annotate("", xy=(fg[-1] + 0.16, y2), xytext=(fg[-1] + 0.16, y4),
                        arrowprops=dict(arrowstyle="<->", color="black", lw=1.0))
            ax.text(fg[-1] + 0.24, 0.5 * (y2 + y4), f"{abs(y4 - y2):.2f} dB",
                    fontsize=8, va="center")
        ax.text(0.02, 0.06,
                f"{T[5]} = {J['size_law']['differential_db']:.2f} dB",
                transform=ax.transAxes, fontsize=8.5,
                bbox=dict(fc="white", ec="black", lw=0.7))
        lo = min(sl[d][k2][SHORT[b]] for d in AIR
                 for k2 in ("mu_L2_dbsm", "mu_L4_dbsm") for b in bands)
        hi = max(sl[d][k2][SHORT[b]] for d in AIR
                 for k2 in ("mu_L2_dbsm", "mu_L4_dbsm") for b in bands)
        ax.set_xlim(fg[0] - 0.3, fg[-1] + 1.45)
        ax.set_ylim(lo - 2.4, hi + 3.4)
        ax.set_xlabel(T[1])
        ax.set_ylabel(T[2])
        ax.set_title(T[0])
        ax.legend(ncol=2, loc="upper left")
    return _pub(fig, "report06_size_law", CAP_EN["size_law"])


def fig_slope(J):
    """기울기 두 가설이 대역 끝에서 벌리는 간격 = 세션 재현성 요구치."""
    T = ["Frequency-slope hypotheses across the measured band span\n"
         "Arrows give the gap the two hypotheses open at the top of the span",
         "Frequency [GHz]", "mu, referenced to the low band [dB]",
         "Measurement anchor, 0.21 dB/GHz", "SBR+PO kernel",
         "Matrice 4E", "Mini 5 Pro", ""]
    assert_fig_text(*T)
    span = J["slope"]["span_ghz"]
    f0 = float(_load(R6)["slope_discrimination"]["f_lo_ghz"])
    fg = np.linspace(f0, f0 + span, 61)
    a_anc = J["slope"]["anchor_db_per_ghz"]
    with paper_style(width="double", base_pt=9.0, aspect=0.42) as st:
        fig, ax = st.figure()
        ax.plot(fg, a_anc * (fg - f0), label=T[3], markevery=12, **st.series(0))
        for j, (r, lbl, fr) in enumerate(zip(J["slope"]["rows"], (T[5], T[6]),
                                             (0.30, 0.62)), start=1):
            ax.plot(fg, r["ours_db_per_ghz"] * (fg - f0), markevery=12,
                    label=f"{T[4]} · {lbl} ({r['ours_db_per_ghz']:.2f} dB/GHz)",
                    **st.series(j))
            ax.annotate("", xy=(fg[-1], r["ours_db_per_ghz"] * span),
                        xytext=(fg[-1], a_anc * span),
                        arrowprops=dict(arrowstyle="<->", color="black", lw=1.0))
            ax.text(fg[-1] - 0.09,
                    (fr * r["ours_db_per_ghz"] + (1 - fr) * a_anc) * span,
                    f"{r['gap_db']:.2f} dB", fontsize=8, ha="right", va="center")
        ax.set_ylim(-0.25, max(r["ours_db_per_ghz"] for r in J["slope"]["rows"])
                    * span * 1.30)
        ax.set_xlabel(T[1])
        ax.set_ylabel(T[2])
        ax.set_title(T[0])
        ax.legend(loc="upper left")
    return _pub(fig, "report06_slope", CAP_EN["slope"])


def fig_ground_bounce(J):
    """야외 지면반사 유령을 레인지게이팅으로 뗄 수 있는 기하는 어디까지인가."""
    from matplotlib.lines import Line2D
    T = ["Target-via-ground ghost: path difference against range resolution\n"
         "Colour and marker give the antenna height h, line style the target height H",
         "Ground range R [m]", "Path difference 2hH/R [m]",
         "Range resolution c/2B"]
    assert_fig_text(*T)
    rows = J["ground_bounce"]
    hs = sorted({r["h_m"] for r in rows})
    Hs = sorted({r["H_m"] for r in rows})
    marks = ("o", "s", "^", "D")
    lss = ((0, (1, 1.4)), (0, (5, 2)), "-", (0, (6, 2, 1, 2)))
    with paper_style(width="double", base_pt=9.0, aspect=0.44) as st:
        fig, ax = st.figure()
        for i, h in enumerate(hs):
            for j, H in enumerate(Hs):
                sel = sorted([r for r in rows if r["h_m"] == h and r["H_m"] == H],
                             key=lambda r: r["R_m"])
                ax.plot([r["R_m"] for r in sel], [r["path_diff_m"] for r in sel],
                        color=st.color(i), marker=marks[i], ms=4.0,
                        linestyle=lss[j], lw=1.2,
                        label=f"h={h:.1f} m, H={H:.0f} m")
        for bw in (400, 200, 100):
            dr = C0 / (2 * bw * 1e6)
            ax.axhline(dr, color="black", lw=1.0)
            ax.text(53.4, dr + 0.07, f"B={bw} MHz, {T[3]} = {dr:.2f} m",
                    fontsize=8, color="black", va="bottom", ha="right",
                    bbox=dict(fc="white", ec="none", pad=1.0))
        #  범례는 두 축을 **따로** 보여 준다 — 9줄을 6줄로 줄이고 부호화 규칙을 그대로 읽힌다.
        keys = ([Line2D([], [], color=st.color(i), marker=marks[i], linestyle="-",
                        label=f"h = {h:.1f} m") for i, h in enumerate(hs)]
                + [Line2D([], [], color="0.35", marker="", linestyle=lss[j],
                          label=f"H = {H:.0f} m") for j, H in enumerate(Hs)])
        ax.legend(handles=keys, ncol=2, loc="upper right")
        ax.set_xlabel(T[1])
        ax.set_ylabel(T[2])
        ax.set_xlim(18.5, 54)
        ax.set_ylim(0, 7.6)
        ax.set_title(T[0])
    return _pub(fig, "report06_ground_bounce", CAP_EN["ground"])


# =========================================================================== #
#  ③  노트북 블록
# =========================================================================== #
def blocks(J) -> list:
    D = from_json("outputs/report06_derived.json")
    M = from_json("outputs/report06_measurement.json")
    A = from_json("outputs/sigma_anchor.json")
    V = from_json("outputs/verify_cfar.json")
    P3 = from_json("outputs/p3_validation.json")          # 눈감기 대조 — 레벨 사전값
    S2A = from_json("outputs/s2r_attack.json")            # sim-to-real 설계 적대검증
    PW = from_json("outputs/ptd_wiring.json")             # PTD 배선 상태(02편 §6)
    B: list = []

    # ── 여는 블록 — 한 일 / 결과 / 방법 / 재현 / 앞 편에서 (§5.2) ─────────────
    #    ⭐ §4.1 논문 대응 블록은 `attach()` 로 여는 블록 **안에** 넣는다 — 셀 예산 +0.
    B.append(attach(header(
        num=6,
        title="실측 — 검출 사슬과 파형 순위를 결판내는 세션을 설계했다",
        did="보유 장비 USRP X410 로 검출 사슬과 세 파형의 상대순위를 결판내는 세션을 설계하고, "
            "시뮬 주장마다 그것을 결정하는 측정과 판정 기준을 수치로 고정했다.",
        results=[
            f"판정 대상은 파형 순위다 — 자세평균 σ 에서 기체 "
            f"{D.num('ranking_validation.n_drones', fmt='{:.0f}', unit='종')}이 같은 순위에 "
            f"합의하고, "
            f"순위를 뒤집는 폭은 최소 "
            f"{D.num('ranking_validation.flip_span_min_db', fmt='{:.2f}', unit='dB')} 다.",
            f"세션 드리프트 예산 "
            f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')} 가 그 폭 "
            f"아래에 있다 — 여유 "
            f"{D.num('ranking_validation.drift_margin_db', fmt='{:+.2f}', unit='dB')}. "
            f"설계가 판정 대상과 맞는다.",
            f"원거리장은 최대 "
            f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')}, 점표적 서브밴드는 "
            f"{D.num('point_target_max_bw_MHz', fmt='{:.0f}', unit='MHz')}, 방위 표본은 "
            f"{D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} 다 — 기체 2종 × 3밴드 전부를 "
            f"한 거리·한 규약으로 덮는다.",
            f"교정 기준체는 반경 "
            f"{D.num('calibration_pick.radius_cm', fmt='{:.1f}', unit='cm')} 정밀 PEC 구다 — "
            f"두 기체·세 밴드에서 예상 σ 보다 최소 "
            f"{D.num('calibration_margin_min_db', fmt='{:+.2f}', unit='dB')} 밝고, 이 구가 "
            f"지금 우리 PO 출력인 **절대 레벨을 측정에 앵커한다**(생산 모드의 평균 레벨이동 "
            f"{D.num('modes.level_shift_production_abs_max_db', fmt='{:.2f}', unit='dB')}).",
            f"기울기 판정 문턱은 세션간 진폭 재현성 "
            f"{D.num('slope.gap_db_min', fmt='{:.2f}', unit='dB')}, 크기법칙 판정은 두 기체의 "
            f"차등신호 {D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} 의 부호다.",
        ],
        method=[
            ("판정 대상",
             "자세평균 σ 위의 파형 순위 뒤집힘 폭을 캠페인 요구치로 삼음 — "
             "`benchmark/sigma_sensitivity.py:470`"),
            ("3층 설계",
             "1층 σ(f) 레인지(§2) · 2층 ISM "
             + D.num("layers.carrier_ism_ghz", fmt="{:.1f}", unit="GHz")
             + " 한 반송파의 파형축 · 3층 비행 검출로 나눈다 — 층마다 여는 축이 다르고 §2-6 이 "
               "그 분업과 대가를 적는다"),
            ("수신 채널",
             "검증 3점은 수신전용이고 기준 1 + 감시 1 = "
             + D.num("layers.n_channels", fmt="{:.0f}", unit="채널")
             + " 을 같은 클럭에서 쓴다 — 하드웨어 사양의 4 RX 와 구별한다"),
            ("원거리장 요구거리",
             "메쉬 외접상자(회전 로터 디스크 포함)의 3D 대각 D 를 세 밴드 λ 에 넣어 2D²/λ 로 "
             "계산 — `benchmark/plan_measurement.py`"),
            ("교정구 기준 σ",
             "정확 Mie 급수로 계산 — `benchmark/mie_pec_sphere.py:207`, `selfcheck()` 보유"),
            ("기체 예상 σ",
             "설계 계산용 예측 — Das 앵커 레벨에 크기법칙 L² · L⁴ 를 둘 다 적용 "
             "(`src/sigma_anchor.py:255`). 생산 σ 원장은 기울기만 앵커한 `slope_only` 다(§3-2)"),
            ("판정 기준",
             "시뮬의 주장마다 그것을 뒤집는 관측량을 짝지어 임계를 수치로 고정 — §4 결정표"),
            ("하드웨어 사양",
             "ni.com / ettus.com 공식 스펙 한 곳에서 인용 — `src/experiment_x410.py:61`"),
        ],
        prereq=[("02 §4", "앵커가 통제한 항과 통제되지 않은 항의 크기 원장"),
                ("03", "세 조명원(LTE · 5G · WiFi)의 대역과 점유"),
                ("04", "명목 Pfa 를 경험 Pfa 로 교정하는 절차"),
                ("05", "자유공간 탐지 결과가 서 있는 기하")],
        repro=dict(
            cmd=["PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "
                 "\"import sigma_anchor as S; S.write_measurement_plan()\"",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                 "src/make_report06_measurement.py"],
            out=["outputs/report06_measurement.json", "outputs/measurement_plan.json",
                 "outputs/report06_derived.json"],
            runtime="약 10 초 (CPU)",
            note="산문판 설계서는 `docs/MEASUREMENT_PLAN.md` 이고, 그 안의 수치표는 "
                 "`src/sigma_anchor.py:939` 가 자동 주입한다"),
    ), paper_map(
        "VI. Validation",
        claim=f"X410 야외 캠페인은 검출 사슬과 세 파형의 상대순위를 결판내며, 그 판정에 필요한 "
              f"진폭 재현성을 세션 드리프트 예산 "
              f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')} 로 "
              f"확보한다 — 자세평균 순위를 뒤집는 폭 "
              f"{D.num('ranking_validation.flip_span_min_db', fmt='{:.2f}', unit='dB')} 아래다.",
        evidence=["§4 결정표", "§3", "그림 5", "그림 6",
                  "outputs/report06_derived.json:ranking_validation.flip_span_min_db",
                  "outputs/report06_derived.json:farfield_adopted.R_ff_max_m",
                  "outputs/sigma_sensitivity.json:aspect_averaged.consensus_order",
                  "outputs/verify_cfar.json:meta.runtime_s"],
        qualifications=[
            "절대 탐지거리와 Pfa 교정은 §4 표에서 '이 캠페인 밖' 으로 표시한다 — "
            "환경 공통항과 통제 몬테카를로가 각각 정한다",
            "σ 절대레벨은 교정구가 세션 안에서 앵커한다 (§2-2). 기울기 앵커는 Das 측정이다",
        ],
        report="report06_measurement")))

    # ── §1 하드웨어 ────────────────────────────────────────────────────────
    B.append(md(
        "## §1. 하드웨어 — X410 한 대가 기준과 감시를 동시에 든다",
        "",
        "세션은 **RX0 = 기준(직접파)** 과 **RX1 = 감시** 두 채널을 **같은 클럭**에서 쓴다"
        "⟨outputs/measurement_layers.json : validation_three_points.channels⟩ — 사양의 4 RX 는 "
        "각도축을 여는 예비다.",
        "사양은 `src/experiment_x410.py:61`, 기하 배치는 `src/experiment_x410.py:100` 한 곳에 있다.",
        "",
        f"12-bit ADC 의 동적범위 "
        f"{M.num('hw.dynamic_range_db', fmt='{:.2f}', unit='dB')} 가 직접파 제거의 천장이고,",
        "직접파를 양자화한 뒤 남는 잔차를 `src/experiment_x410.py:83` 의 `adc_quantize()` 가 모델에 넣는다."))

    B.append(md(
        table(["항목", "값", "무엇을 제약하나"], [
            ["TX / RX 채널",
             M.num("hw.n_tx", fmt="{:.0f}") + " / " + M.num("hw.n_rx", fmt="{:.0f}"),
             "세션은 기준 1 + 감시 1 = "
             + D.num("layers.n_channels", fmt="{:.0f}", unit="채널") + " 을 공통 클럭에서 쓴다"],
            ["채널당 순시대역", M.num("hw.max_bw_mhz", fmt="{:.0f}", unit="MHz"),
             "거리분해능과 점표적 서브밴드(§2-3)"],
            ["주파수 범위", D.num("hw_span.f_lo_mhz", fmt="{:.0f}", unit="MHz") + " ~ "
             + D.num("hw_span.f_hi_ghz", fmt="{:.1f}", unit="GHz"), "세 밴드 전부 커버"],
            ["ADC 동적범위", M.num("hw.dynamic_range_db", fmt="{:.2f}", unit="dB"),
             "직접파 제거의 천장"],
            ["감시배열 AoA 빔폭", M.num("hw.aoa_beamwidth_deg", fmt="{:.1f}", unit="°"),
             "네 RX 를 전부 감시로 쓸 때 열리는 각도축 — 디텍션 이후의 확장축"],
            ["최대대역 바이스태틱 ΔR",
             M.num("hw.range_res_bistatic_m_at_max_bw", fmt="{:.3f}", unit="m"),
             "표적이 퍼지는 폭(§2-3)"]]),
        "",
        f"원사양 출처는 `{M.get('hw.source')}` 한 곳이다."))

    B.append(md(
        str(figure_md("outputs/figures/report06_adc_headroom.png", 1,
                      "12-bit ADC 는 직접파 대 잡음비 위에 얼마의 여유를 남기는가?",
                      paper_caption=CAP_EN["adc"], report="report06_measurement")),
        "",
        f"여유가 가장 좁은 파형은 `{M.get('adc.worst_waveform')}` 이고 "
        f"{M.num('adc.headroom_db_min', fmt='{:.1f}', unit='dB')} 다 — 점유대역이 좁아 "
        f"기준채널 이득이 높다.",
        "",
        "이 DNR 은 자유공간 시뮬 기하에서 나온 값이다⟨outputs/report06_measurement.json : "
        "adc.dnr_source⟩. 야외에서 송수신을 가깝게 놓으면 DNR 이 올라가 여유가 그만큼 줄어든다."))

    # ── §2 실행 체크리스트 ─────────────────────────────────────────────────
    B.append(md(
        "## §2. ⭐ 교정된 절대 σ 로 가는 세션 — 실행 체크리스트 6항목",
        "",
        "이 여섯 항목이 **교정된 절대 σ** 를 만드는 조건 전부다 — 기준체 · 배경차감 · 자세통제 · "
        "원거리장 · 점표적 대역 · 패턴교정. 순위 판정(§3)은 이 중 앞의 셋만 요구하고, "
        "여섯을 다 채운 세션이 다음 라운드의 더 센 주장(절대 σ)을 만든다.",
        "",
        "왼쪽은 세션에서 **하는 일**, 오른쪽은 그 일이 만족해야 하는 **수치 임계**다.",
        "",
        table(["실행 항목", "세션에서 하는 일", "수치 임계"], [
            ["교정 기준체",
             "정밀 PEC 구를 세션 **시작과 끝**에 표적과 같은 지지대·같은 위치에서 잰다",
             f"예상 σ 대비 여유 ≥ "
             f"{D.num('calibration_margin_min_db', fmt='{:+.2f}', unit='dB')} (§2-2)"],
            ["배경 차감",
             "지지대를 세운 채 표적만 치우고 배경 응답을 **복소수로** 뺀다",
             f"지면반사 경로차 > ΔR — 기하 "
             f"{D.num('ground_bounce_sep_frac_200MHz', fmt='{:.0%}')} 가 분리 (§2-5)"],
            ["자세 통제",
             "엔코더 턴테이블로 방위를 돌리고 로터를 정지시켜 블레이드 방위를 기록한다",
             f"Δφ ≤ {D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} (§2-4)"],
            ["안테나 패턴 교정",
             "교정구를 표적과 같은 자리·같은 높이에 놓아 패턴과 체인 이득을 비율로 소거한다",
             "표적/교정구 위치 동일 (§2-2)"],
            ["원거리장 거리",
             "2D²/λ 이상에서 잰다 — 교정구는 같은 자리에 놓으면 자동 만족한다",
             f"R ≥ {D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')} (§2-1)"],
            ["점표적 서브밴드",
             f"{M.num('hw.max_bw_mhz', fmt='{:.0f}', unit='MHz')} 순시대역을 쪼개 "
             f"서브밴드마다 σ 를 내고, 그 다발을 σ(f) 로 삼는다",
             f"B ≤ {D.num('point_target_max_bw_MHz', fmt='{:.0f}', unit='MHz')} (§2-3)"]]),
        "",
        "여섯 항목의 산문판 조건은 `docs/MEASUREMENT_PLAN.md` §1-1~1-6 에 있다."))

    # ── §2-1 원거리장 ──────────────────────────────────────────────────────
    B.append(md(
        "### §2-1. 원거리장 — 2D²/λ 를 두 기체 × 세 밴드로 계산했다",
        "",
        "채택한 D 는 가장 보수적인 정의다 — 회전 로터 디스크까지 포함한 외접상자의 3D 대각.",
        f"같은 기체를 모터-모터 대각으로 재정의하면 요구거리가 "
        f"{D.num('farfield_adopted.spread_ratio_max', fmt='{:.2f}')}배 짧아진다. 세 정의를 "
        f"한 표에 나란히 실어 어느 값을 쓰는지 고정한다.",
        "",
        D.table("farfield",
                [("기체", "airframe"), ("밴드", "band"), ("λ", "lam_mm"),
                 ("D_env", "D_env_m"), ("**R_ff(env)**", "R_ff_env_m"),
                 ("R_ff(bbox)", "R_ff_bbox_m"), ("R_ff(모터대각)", "R_ff_diag_m")],
                fmt={"lam_mm": "{:.0f} mm", "D_env_m": "{:.3f} m",
                     "R_ff_env_m": "{:.2f} m", "R_ff_bbox_m": "{:.2f} m",
                     "R_ff_diag_m": "{:.2f} m"})))

    B.append(md(
        str(figure_md("outputs/figures/report06_farfield.png", 2,
                      "각 기체와 밴드에서 원거리장에 들어가려면 얼마나 멀어야 하는가?",
                      paper_caption=CAP_EN["farfield"], report="report06_measurement")),
        "",
        f"세션 거리는 최대값 "
        f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')} 로 잡는다 — "
        f"그 한 거리가 두 기체 세 밴드를 전부 덮는다."))

    # ── §2-2 교정 기준체 ───────────────────────────────────────────────────
    B.append(md(
        "### §2-2. 교정 기준체 — σ 를 절대량으로 만드는 장치",
        "",
        "**정밀 PEC 구**를 쓴다. 구는 방위무관이라 정렬 오차가 σ 에 안 들어간다.",
        "",
        "기준값은 **정확 Mie** 로 쓴다 — πr² 광학 점근과의 차이는 아래 표의 `Mie−πr²` 열에 dB 로 있다.",
        "단일 출처는 `benchmark/mie_pec_sphere.py:207` 이고 자체검증 `selfcheck()` 을 갖고 있다.",
        "",
        "세션 **시작과 끝에 한 번씩** 잰다. 두 값의 차가 그 세션의 드리프트 예산이고,",
        "그 차가 목표 정확도(≤ 1 dB) 안에 들어온 세션만 자료로 쓴다.",
        "",
        f"앵커 사슬은 같은 반경의 금속구를 σ_cal "
        f"{D.num('layers.cal_anchor_declared_dbsm', fmt='{:.2f}', unit='dBsm')} 로 선언했다 — "
        f"πr² 광학값 {D.num('layers.cal_pir2_dbsm', fmt='{:.2f}', unit='dBsm')} 이다"
        f"⟨outputs/measurement_layers.json : calibration_convention_gap.anchor_quote⟩. 우리가 "
        f"정확 Mie 로 교정하면 우리 σ 는 그 규약 대비 밴드에 따라 "
        f"{D.num('layers.mie_shift_min_db', fmt='{:+.2f}')} ~ "
        f"{D.num('layers.mie_shift_max_db', fmt='{:+.2f}', unit='dB')} 위로 뜬다 — 앵커와 "
        f"사과-대-사과로 견줄 때 이 항을 먼저 되돌린다."))

    B.append(md(
        D.table("calibration",
                [("구", "sphere"), ("밴드", "band"), ("ka", "ka"),
                 ("σ_Mie", "mie_dbsm"), ("Mie−πr²", "mie_minus_go_db"),
                 ("Matrice 4E 대비 여유", "margin_matrice4e_db"),
                 ("Mini 5 Pro 대비 여유", "margin_mini5pro_db")],
                fmt={"ka": "{:.1f}", "mie_dbsm": "{:+.2f} dBsm",
                     "mie_minus_go_db": "{:+.2f} dB",
                     "margin_matrice4e_db": "{:+.2f} dB",
                     "margin_mini5pro_db": "{:+.2f} dB"})))

    B.append(md(
        str(figure_md("outputs/figures/report06_calibration.png", 3,
                      "어느 반경의 교정구가 세 밴드 모두에서 기체 예상 σ 위에 있는가?",
                      paper_caption=CAP_EN["calibration"], report="report06_measurement")),
        "",
        f"채택 반경은 {D.num('calibration_pick.radius_cm', fmt='{:.1f}', unit='cm')} 다 — "
        f"{D.get('calibration_pick.why')}",
        "",
        f"교정구가 기체보다 최소 "
        f"{D.num('calibration_margin_min_db', fmt='{:+.2f}', unit='dB')} 밝으므로 같은 이득 "
        f"설정으로 둘 다 잡히고, 그래야 두 응답의 비율이 그대로 σ 비율이 된다."))

    # ── §2-3 점표적 서브밴드 ───────────────────────────────────────────────
    B.append(md(
        "### §2-3. 점표적 서브밴드 — 순시대역을 쪼개 σ(f) 로 만든다",
        "",
        "peak |s|² 를 σ 로 쓰려면 표적이 **한 거리빈 안**에 들어와야 한다(ΔR = c/2B > D_bbox).",
        f"두 기체를 함께 만족시키는 최대 서브밴드는 "
        f"{D.num('point_target_max_bw_MHz', fmt='{:.0f}', unit='MHz')} 다. 서브밴드마다 σ 를 "
        f"내면 그 다발이 곧 σ(f) 이고, 앵커 문헌(Das §II-3c)의 절차와 같다.",
        "",
        D.table("point_target",
                [("대역 B", "B_MHz"), ("ΔR = c/2B", "dR_m"),
                 ("Matrice 4E", "matrice4e_ok"), ("여유", "matrice4e_margin_m"),
                 ("Mini 5 Pro", "mini5pro_ok"), ("여유", "mini5pro_margin_m")],
                fmt={"B_MHz": "{:.0f} MHz", "dR_m": "{:.3f} m",
                     "matrice4e_margin_m": "{:+.3f} m",
                     "mini5pro_margin_m": "{:+.3f} m"}),
        "",
        f"게이팅은 넓게, 평가는 좁게 한다 — 앵커는 6차 Kaiser 창으로 CIR 을 게이팅한 뒤 주파수축으로 "
        f"되돌리고⟨outputs/measurement_layers.json : gate_wide_evaluate_narrow.anchor_quote⟩, 우리는 "
        f"{D.num('layers.gate_bw_mhz', fmt='{:.0f}', unit='MHz')} 전대역에서 게이팅한 뒤 σ 는 "
        f"{D.num('layers.eval_bw_mhz', fmt='{:.0f}', unit='MHz')} 서브밴드 "
        f"{D.num('layers.n_subbands', fmt='{:.0f}')} 개로 평가한다."))

    # ── §2-4 자세 통제 ─────────────────────────────────────────────────────
    B.append(md(
        "### §2-4. 자세 통제 — 각도표본을 λ/4D 로 잡았다",
        "",
        "방위는 엔코더 턴테이블로 돌리고, 표본 간격은 `λ/4D` 이하로 잡는다.",
        f"가장 촘촘한 요구는 {D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} "
        f"(`{D.get('aspect_finest_airframe')}` · `{D.get('aspect_finest_band')}`)이고, "
        f"한 바퀴에 {D.num('aspect_n_az_max', fmt='{:.0f}')} 표본이다.",
        "",
        f"앵커 문헌은 밴드와 무관하게 "
        f"{D.num('layers.anchor_step_deg', fmt='{:.2f}', unit='°')} 고정(반원 "
        f"{D.num('layers.anchor_N', fmt='{:.0f}', unit='점')})을 썼고, 우리는 밴드마다 λ/4D 를 "
        f"따라간다 — 요구 표본수는 반원당 "
        f"{D.num('layers.N_required_min', fmt='{:.0f}')} ~ "
        f"{D.num('layers.N_required_max', fmt='{:.0f}')} 점이다.",
        "표의 마지막 열이 밴드별 대소를 그대로 싣는다.",
        "",
        f"앵커는 높은 주파수에서 그 고정 간격이 성기다고 스스로 적었고"
        f"⟨outputs/measurement_layers.json : angular_sampling._rule⟩, 우리 기체에서 그 자리는 "
        f"`{D.get('layers.anchor_too_coarse_1')}` 와 `{D.get('layers.anchor_too_coarse_2')}` 두 "
        f"칸이다. 나머지 칸에서는 2° 가 우리 요구보다 촘촘하다.",
        "",
        "로터는 **정지**시키고 블레이드 방위를 기록한다 — 앵커가 회전 성분을 뺐으므로 그 규약에 맞춘다."))

    B.append(md(
        D.table("aspect",
                [("기체", "airframe"), ("밴드", "band"),
                 ("Δφ 나이퀴스트", "az_nyquist_deg"), ("Δφ 권장", "az_recommended_deg"),
                 ("한 바퀴 표본수", "n_az_per_turn"),
                 ("앵커 고정 2° 보다 촘촘한가", "finer_than_anchor_2deg")],
                fmt={"az_nyquist_deg": "{:.2f}°", "az_recommended_deg": "{:.2f}°",
                     "n_az_per_turn": "{:.0f}"})))

    # ── §2-5 배경 차감과 지면반사 ──────────────────────────────────────────
    B.append(md(
        "### §2-5. 배경 차감과 지면반사 — 야외 부지를 기하로 다룬다",
        "",
        "배경 S_BG 는 **지지대를 세운 채로** 재고 **복소수로** 뺀다.",
        "표적을 경유한 지면반사는 경로차 `2hH/R` 이 서브밴드 거리분해능보다 **클 때** 레인지게이팅으로 떨어진다.",
        "",
        str(figure_md("outputs/figures/report06_ground_bounce.png", 4,
                      "어떤 야외 기하가 지면반사 유령을 표적 거리빈 밖으로 밀어내는가?",
                      paper_caption=CAP_EN["ground"], report="report06_measurement")),
        "",
        f"{D.num('ground_bounce_n_geom', fmt='{:.0f}')}개 기하 중 "
        f"{D.num('ground_bounce_ref_bw_MHz', fmt='{:.0f}', unit='MHz')} 서브밴드에서 분리되는 "
        f"비율은 {D.num('ground_bounce_sep_frac_200MHz', fmt='{:.0%}')} 다. "
        f"부지 선정은 그림 4 에서 분해능 선 위에 오는 (h, H, R) 조합으로 한다."))

    # ── §2-6 실측 3층 — 이 §2 는 1층이다 ────────────────────────────────────
    B.append(md(
        "### §2-6. 세 층 — §2 는 1층이고, 파형축과 비행검출이 그 위에 선다",
        "",
        D.table("layers.rows",
                [("층", "layer"), ("무엇을 재나", "measures"), ("반송파", "carrier"),
                 ("산출", "product")]),
        "",
        f"2층을 한 반송파에 고정하는 이유는 면허다 — 2.1 GHz 야외 송신은 허가가 필요하고 "
        f"'2.1 GHz 의 WiFi' 라는 배치신호는 세상에 존재하지 않는 인공물이다"
        f"⟨outputs/measurement_layers.json : layer2_waveform_axis.why_one_carrier⟩. 잃는 반송파축은 "
        f"수신전용 검증 3점({D.num('layers.validation_points')})의 실제 배치신호와 v_max 의 λ 비 "
        f"이전으로 갚는다 — 그 3점은 교차설계의 대각선이 아니라 독립 검사점이다.",
        "",
        f"1층이 내는 것은 점별 패턴이 아니라 **분포 P(σ)** 다 — 검출확률이 σ 분포의 함수이므로, "
        f"그 분포를 Swerling 틀에 넣어 3층의 "
        f"`{D.get('layers.layer3_headline')}` 를 예측하고 3층이 그 예측을 검사한다"
        f"⟨outputs/measurement_layers.json : layer3_flight.ties_back_to⟩. 2층·3층의 ISM 원거리장은 "
        f"bbox 정의로 최대 "
        f"{D.num('layers.farfield_ism_bbox_max_m', fmt='{:.2f}', unit='m')} 이고, §2-1 이 채택한 "
        f"세션 거리 {D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')}(env 정의) 안에 "
        f"든다."))

    # ── §3 시뮬과 실측 ─────────────────────────────────────────────────────
    B.append(md(
        "## §3. ⭐ 시뮬과 실측 — 캠페인이 결판내는 양은 순위다",
        "",
        f"자세평균 σ 에서 기체 "
        f"{D.num('ranking_validation.n_drones', fmt='{:.0f}', unit='종')}이 순위 "
        f"`{' > '.join(D.get('ranking_validation.consensus_order'))}` 에 합의하고, 그 순위를 "
        f"뒤집는 밴드별 σ 이동폭은 Matrice 4E "
        f"{D.num('ranking_validation.flip_span_db.matrice4e', fmt='{:.2f}', unit='dB')} · "
        f"Mini 5 Pro "
        f"{D.num('ranking_validation.flip_span_db.mini5pro', fmt='{:.2f}', unit='dB')} 다.",
        f"세션 드리프트 예산 "
        f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')}(§2-2)가 그 폭 "
        f"아래에 있으므로(여유 "
        f"{D.num('ranking_validation.drift_margin_db', fmt='{:+.2f}', unit='dB')}) 이 캠페인은 "
        f"**검출 사슬과 파형 순위**를 결판낸다.",
        "절대 σ 는 §2 여섯 항목을 다 채운 세션이 다음 라운드에서 만든다.",
        "",
        table(["설계상 같게 맞춘 축", "설계상 다르게 둔 축"], [
            ["바이스태틱 구조 — 기준 1 + 감시 1, 공통 클럭",
             "환경 — 시뮬은 자유공간, 실측은 지면반사·다중경로"],
            ["같은 기체 2종 (Matrice 4E · Mini 5 Pro)", "클러터 — 실측 부지의 정적 산란체"],
            ["같은 세 파형 (LTE · 5G · WiFi)", "동적범위 — 시뮬 ECA 는 float64, 실측은 12-bit"],
            ["같은 검출기 사슬 (ECA → 거리도플러 → CA-CFAR)", "자세 — 시뮬은 각도격자, 비행 중에는 자유"],
            ["σ 통계 규약 (방위 선형평균)", "링크예산 전제 — 절대 탐지거리"]])))

    B.append(md(
        "### §3-1. 앵커 원장 — 이 캠페인이 닫으러 가는 항목과 그 크기",
        "",
        A.table("uncontrolled",
                [("항목", "term"), ("상태", "status"), ("크기", "size_db")],
                fmt={"size_db": "{:+.2f} dB"}, null="미상")))

    B.append(md(
        "### §3-2. 재보정 모드 — 이 편의 어느 숫자가 어느 모드에서 오나",
        "",
        f"생산 σ 원장은 `{D.num('modes.production_mode')}` 다 — 주파수 기울기만 측정에서 받고 "
        f"**절대 레벨은 우리 PO 출력 그대로**다(평균 레벨이동 "
        f"{D.num('modes.level_shift_production_abs_max_db', fmt='{:.2f}', unit='dB')}). "
        f"레벨을 앵커에 맞추는 두 모드는 이 편의 설계 계산에만 쓴다.",
        "",
        D.table("modes.rows",
                [("모드", "mode"), ("무엇을 옮기나", "moves"),
                 ("Matrice 4E", "matrice4e_db"), ("Mini 5 Pro", "mini5pro_db"),
                 ("이 편에서 쓰는 곳", "used_in")],
                fmt={"matrice4e_db": "{:+.2f} dB", "mini5pro_db": "{:+.2f} dB"}),
        "",
        "교정구를 표적과 같은 자리에서 재는 §2-2 가 이 표의 첫 줄을 바꾼다 — "
        "레벨이 우리 계산에서 우리 측정으로 옮겨 온다."))

    B.append(md(
        table(["기체", "앵커 대비 등급", "크기비", "L² 보정", "L⁴ 보정"], [
            ["Matrice 4E", A.get("drones.matrice4e.comparability.verdict"),
             A.num("drones.matrice4e.comparability.size_ratio", fmt="{:.3f}"),
             A.num("drones.matrice4e.comparability.size_corr_L2_db", fmt="{:+.2f}", unit="dB"),
             A.num("drones.matrice4e.comparability.size_corr_L4_db", fmt="{:+.2f}", unit="dB")],
            ["Mini 5 Pro", A.get("drones.mini5pro.comparability.verdict"),
             A.num("drones.mini5pro.comparability.size_ratio", fmt="{:.3f}"),
             A.num("drones.mini5pro.comparability.size_corr_L2_db", fmt="{:+.2f}", unit="dB"),
             A.num("drones.mini5pro.comparability.size_corr_L4_db", fmt="{:+.2f}", unit="dB")]]),
        "",
        "두 기체 다 등급이 `scaled` 다 — 앵커 기체와 같은 4로터 위상이고 대각만 다르다.",
        "이 원장의 각 행이 §4 결정표 왼쪽 열과 1:1 로 붙는다."))

    # ── §4 결정표 ──────────────────────────────────────────────────────────
    B.append(md(
        "## §4. ⭐ 결정표 — 어느 측정이 어느 주장을 결판내는가",
        "",
        "네 번째 열이 **판정 범위**다 — `결판`(이 캠페인이 정한다) · `사슬 확인`(설계값과 대조한다) · "
        "`이 캠페인 밖`(다음 라운드나 통제 시뮬이 정한다). 세 번째 값을 그대로 적는 것이 이 표의 핵심이다.",
        "",
        table(["02편의 주장", "이를 결정하는 측정", "판정 기준", "판정 범위"], [
            ["자세 패턴 B1(φ) 을 SBR+PO 기하에서 계산했다",
             "턴테이블 방위컷, 로터 정지",
             f"Δφ ≤ {D.num('aspect_finest_deg', fmt='{:.2f}', unit='°')} 로 재고 로브 위치 대조 (§2-4)",
             "결판"],
            ["절대 레벨은 우리 PO 출력이다 (앵커는 기울기만 옮긴다)",
             "표적과 같은 자리에서 교정구 + 배경 코히런트 차감 — **레벨의 첫 측정 앵커**",
             f"교정구 여유 ≥ "
             f"{D.num('calibration_margin_min_db', fmt='{:+.2f}', unit='dB')}, 세션 드리프트 ≤ "
             f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')} (§2-2). "
             f"눈감기 사전값 — 고도정합 실측곡선 대비 밴드평균 "
             f"{P3.num('residual.vs_yuan_theta90_measured_curve.mean_db', fmt='{:+.2f}', unit='dB')}",
             "결판"],
            ["모서리 회절 — 1차 PTD 항이 커널에 있고 생산 기본값은 끔이다 (02)",
             "모서리가 많은 표준체(평판·이면각)를 같은 세션에서 함께 측정",
             f"위상까지 정합해 부호를 심판한다 — 평판 RMS 시험은 위상맹목이다. 켠 비용은 "
             f"{PW.num('verdict.cost_increase_pct', fmt='{:+.1f}', unit='%')} (§5)",
             "결판"],
            [f"밴드 기울기는 Das 의 "
             f"{D.num('slope.anchor_db_per_ghz', fmt='{:.3f}')} dB/GHz 로 맞췄다",
             "세 밴드를 같은 세션에서 측정",
             f"세션 재현성 < {D.num('slope.gap_db_min', fmt='{:.2f}', unit='dB')} (§4-1)",
             "결판"],
            [f"크기전이는 L² 와 L⁴ 를 괄호로 함께 싣는다 "
             f"({D.num('size_law.uncontrolled_size_db', fmt='{:.2f}', unit='dB')})",
             "두 기체를 한 캠페인에서 측정",
             f"차등 {D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} 의 부호 (§4-2)",
             "결판"],
            ["편파: VV 단일, 커널은 무편파 스칼라",
             "VV / VH / HV / HH 4조합",
             "무편파 모형과 VV 측정의 차를 dB 로 확정", "결판"]])))

    B.append(md(
        table(["03~05편의 주장", "이를 결정하는 측정", "판정 기준", "판정 범위"], [
            ["파형별 점유·대역폭 대가는 σ 와 무관하게 정확하다 (03)",
             "X410 이 같은 기하에서 세 파형을 송신",
             "측정 ΔR·모호함수가 설계값과 일치", "사슬 확인"],
            [f"파형 상대순위 `{' > '.join(D.get('ranking_validation.consensus_order'))}` (05)",
             "야외 고정기하 탐지시험 · 방위 스윕으로 자세평균",
             f"순서 일치 · 뒤집힘 폭 "
             f"{D.num('ranking_validation.flip_span_min_db', fmt='{:.2f}', unit='dB')} (§3)",
             "결판"],
            ["자유공간 절대 탐지거리 (05)",
             "환경 공통항(지면·클러터)이 정한다",
             f"σ 공통이동 1 dB 당 거리 "
             f"{D.num('ranking_validation.common_mode_slope_db_per_db', fmt='{:.2f}', unit='dB')} 이동",
             "**이 캠페인 밖**"],
            ["명목 Pfa 를 교정해야 파형 비교가 성립한다 (04)",
             "부지 배경 CPI 를 녹화해 그 부지의 경험 Pfa 를 별도로 기록",
             f"교정 자체는 통제 몬테카를로 "
             f"{V.num('meta.runtime_s', fmt='{:.0f}', unit='s')} 가 세운다",
             "**이 캠페인 밖**"],
            ["12-bit ADC 가 직접파 제거의 천장이다 (§1)",
             "직접파를 실제로 받아 ECA 잔차를 잰다",
             f"여유 {M.num('adc.headroom_db_min', fmt='{:.1f}', unit='dB')} 가 야외에 얼마나 남나",
             "사슬 확인"]])))

    B.append(md(
        "### §4-1. 기울기 — 세션 재현성이 판정의 문턱이다",
        "",
        str(figure_md("outputs/figures/report06_slope.png", 5,
                      "우리 기울기와 앵커 기울기를 가르려면 세션 재현성이 얼마나 좋아야 하는가?",
                      paper_caption=CAP_EN["slope"], report="report06_measurement")),
        "",
        f"우리 커널은 {D.num('slope.rows[0].ours_db_per_ghz', fmt='{:.3f}')} ~ "
        f"{D.num('slope.rows[1].ours_db_per_ghz', fmt='{:.3f}')} dB/GHz 이고 앵커는 "
        f"{D.num('slope.anchor_db_per_ghz', fmt='{:.3f}')} dB/GHz 다. 대역 "
        f"{D.num('slope.span_ghz', fmt='{:.3f}', unit='GHz')} 를 지나며 두 가설이 "
        f"{D.num('slope.gap_db_min', fmt='{:.2f}')} ~ "
        f"{D.num('slope.rows[1].gap_db', fmt='{:.2f}')} dB 벌어진다. 기울기의 정의는 하나로 "
        f"고정한다 — {D.num('slope.fit_note_short')}.",
        "",
        "### §4-2. 크기법칙 — 두 기체를 함께 사는 이유",
        "",
        str(figure_md("outputs/figures/report06_size_law.png", 6,
                      "두 기체를 함께 재면 L² 와 L⁴ 를 가를 수 있는가?",
                      paper_caption=CAP_EN["size_law"], report="report06_measurement")),
        "",
        f"Matrice 4E 는 앵커보다 크고(크기비 "
        f"{D.num('size_law.by_airframe.matrice4e.size_ratio', fmt='{:.3f}')}), Mini 5 Pro 는 "
        f"작다({D.num('size_law.by_airframe.mini5pro.size_ratio', fmt='{:.3f}')}). "
        f"두 법칙의 예측이 **반대 방향**으로 갈리므로 두 기체의 μ 차이가 법칙을 직접 고른다.",
        "",
        f"차등신호 {D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} 가 "
        f"두 기체를 함께 사는 이유다."))

    # ── 논문 참고자료 (PAPER_SPEC §4.2·§4.4·§4.5) — 셀 하나로 묶는다 ─────────
    B.append(paper_appendix(
        sec="§4.5",
        methods_block=methods(
            "Validation campaign design. Two airframes (DJI Matrice 4E, DJI Mini 5 Pro) are "
            "measured with a USRP X410 (4 TX / 4 RX, "
            f"{M.num('hw.max_bw_mhz', fmt='{:.0f}', unit='MHz')} instantaneous bandwidth per "
            f"channel, 12-bit ADC giving "
            f"{M.num('hw.dynamic_range_db', fmt='{:.2f}', unit='dB')} of dynamic range), each "
            "session receiving on two channels driven by a common clock, RX0 as the reference "
            "and RX1 as the surveillance channel. The campaign is organised in three layers: a "
            "static cross-section range that yields sigma(f) and its distribution over aspect, a "
            f"waveform axis measured at a single ISM carrier of "
            f"{D.num('layers.carrier_ism_ghz', fmt='{:.1f}', unit='GHz')} because outdoor "
            "transmission at the cellular carriers is licensed, and a flight-detection layer that "
            "reads Pd against range at a fixed CFAR design Pfa; the carrier axis given up in the "
            "second layer is recovered by receiving the three deployed signals "
            f"({D.get('layers.validation_points')}) and by transferring the unambiguous velocity "
            "with the wavelength ratio. The session range "
            f"is {D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')}, the largest "
            "2D^2/lambda over both airframes and all three bands with D taken as the "
            "enclosing-box diagonal including the rotor discs. Absolute level is tied to a "
            f"precision PEC sphere of radius "
            f"{D.num('calibration_pick.radius_cm', fmt='{:.1f}', unit='cm')} measured at the "
            "target position at the start and the end of every session against an exact Mie "
            f"reference, with a session drift budget of "
            f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')}; the "
            "background is recorded with the mount in place and subtracted coherently. The "
            f"capture is split into sub-bands of "
            f"{D.num('point_target_max_bw_MHz', fmt='{:.0f}', unit='MHz')} so that c/2B exceeds "
            "the airframe extent, and each sub-band yields one cross section, giving sigma(f). "
            f"Azimuth is stepped on an encoder turntable at "
            f"{D.num('aspect_finest_deg', fmt='{:.2f}', unit='deg')}, at or below lambda/4D in "
            "every band, with the rotors stopped and the blade azimuth logged. Detection reuses "
            "the simulation chain (ECA, range-Doppler, CA-CFAR) unchanged.",
            tools=["Python 3.12", "NumPy 2.5", "SciPy 1.18", "Sionna 2.0.1", "PyTorch 2.12"],
            report="report06_measurement", sec="§4.5"),
        defence_block=defence([
            (f"야외 캠페인은 검출 사슬과 세 파형의 상대순위를 결판낸다.",
             "§3 · §4 결정표 · outputs/sigma_sensitivity.json:aspect_averaged.consensus_order",
             "야외 환경이 시뮬 자유공간과 달라 비교 대상이 흐려진다.",
             f"순위를 정하는 λ²·점유·대역폭 항은 밴드 간 차이고 환경 항은 세 밴드 공통이다. "
             f"자세평균 σ 에서 기체 "
             f"{D.num('ranking_validation.n_drones', fmt='{:.0f}', unit='종')}이 같은 순위에 합의한다 "
             f"⟨outputs/sigma_sensitivity.json : aspect_averaged.all_drones_agree⟩."),
            (f"세션 드리프트 예산 "
             f"{D.num('ranking_validation.drift_budget_db', fmt='{:.2f}', unit='dB')} 가 "
             f"자세평균 뒤집힘 폭 "
             f"{D.num('ranking_validation.flip_span_min_db', fmt='{:.2f}', unit='dB')} 아래에 "
             f"있다.",
             "§3 · outputs/report06_derived.json:ranking_validation.drift_margin_db",
             f"여유 {D.num('ranking_validation.drift_margin_db', fmt='{:.2f}', unit='dB')} 는 "
             f"얇다.",
             f"좁은 쪽은 Matrice 4E 하나이고 Mini 5 Pro 는 "
             f"{D.num('ranking_validation.flip_span_db.mini5pro', fmt='{:.2f}', unit='dB')} 다. "
             f"두 기체를 함께 재어 넓은 쪽이 좁은 쪽의 판정을 받쳐 준다."),
            ("교정구를 표적 자리에서 세션 시작·끝에 재어 절대 레벨의 첫 측정 앵커를 세운다.",
             "그림 3 · outputs/report06_derived.json:calibration_margin_min_db",
             "그 여유는 앵커 절대레벨 위의 설계값이고, 앵커 절편에는 통계 규약 변환 상수가 들어 있다.",
             f"그 상수는 "
             f"{A.num('statistic_resolution.reconcile.by_kind.exponential.offset_db', fmt='{:.2f}', unit='dB')} "
             f"이고, 빼면 기체 예상 σ 가 내려가 여유가 그만큼 넓어진다. 생산 σ 는 "
             f"{D.num('modes.production_mode')} 라 기울기만 받는다."),
            ("세 밴드를 한 세션에서 재어 밴드별 σ 오차를 진폭 재현성으로 묶는다.",
             "그림 5 · outputs/report06_derived.json:slope.gap_db_min",
             f"밴드별 독립 σ 오차 1 dB 에서 단일자세 순위 보존확률이 "
             f"{D.num('ranking_validation.p_order_preserved_at_1db.matrice4e', fmt='{:.2f}')} "
             f"로 떨어진다.",
             f"그 값은 단일자세 인용의 것이다 "
             f"⟨outputs/report06_derived.json : ranking_validation.mc_basis⟩. 캠페인은 방위 "
             f"{D.num('ranking_validation.az_step_deg', fmt='{:.2f}', unit='°')} 표본으로 "
             f"자세평균 σ 를 내고, 자세평균에서 다섯 기체 순위가 일치한다."),
            (f"원거리장 거리를 "
             f"{D.num('farfield_adopted.R_ff_max_m', fmt='{:.2f}', unit='m')} 로 잡고 세 D "
             f"정의를 한 표에 함께 싣는다.",
             "그림 2 · outputs/report06_derived.json:farfield_adopted.R_ff_max_m",
             f"D 정의를 모터대각으로 바꾸면 요구거리가 "
             f"{D.num('farfield_adopted.spread_ratio_max', fmt='{:.2f}', unit='배')} 달라진다.",
             "그 비를 표에 실었고 채택은 가장 보수적인 env 다 "
             "⟨outputs/report06_derived.json : farfield_adopted.spread_ratio_max⟩."),
            ("두 기체를 한 캠페인에서 재어 크기전이 법칙을 부호 하나로 고른다.",
             "그림 6 · outputs/report06_derived.json:size_law.differential_db",
             "기체 2종은 표본이 작다.",
             f"두 기체가 앵커보다 각각 크고 작아 L² 와 L⁴ 가 반대 부호를 예측하고, 차등은 "
             f"{D.num('size_law.differential_db', fmt='{:.2f}', unit='dB')} 다."),
            ("Pfa 교정은 통제 몬테카를로가 세우고, 야외 세션은 부지 경험 Pfa 를 별도 값으로 기록한다.",
             "§4 결정표 · outputs/verify_cfar.json:meta.runtime_s",
             "야외에서 Pfa 를 통제하면 교정 주장이 더 강해진다.",
             f"CFAR 임계는 {V.num('meta.runtime_s', fmt='{:.0f}', unit='s')} 의 GPU 몬테카를로 "
             f"경험 Pfa 로 교정했다. 야외 세션은 같은 임계를 부지 잡음 위에서 재현해 사슬을 "
             f"확인한다 ⟨outputs/verify_cfar.json : chain_verify⟩."),
            (f"12-bit ADC 동적범위 "
             f"{M.num('hw.dynamic_range_db', fmt='{:.2f}', unit='dB')} 가 직접파 제거의 천장이다.",
             "그림 1 · outputs/report06_measurement.json:adc.headroom_db_min",
             "시뮬 자유공간 기하의 DNR 은 야외보다 낙관적이다.",
             f"가장 좁은 여유는 "
             f"{M.num('adc.headroom_db_min', fmt='{:.1f}', unit='dB')} 이고, 세션은 직접파를 "
             f"실제로 받아 그 여유를 측정값으로 대체한다."),
        ], sec="§4.5", report="report06_measurement"),
        citations=[
            cite_ref("das", note="Phantom 3 · Table III — 주파수 기울기 앵커(§4-1)"),
            cite_ref("rzewuski",
                     note="FDTD RCS → 패시브 커버리지 → 50 m OTA 검출. 같은 산출물의 게재 전례"),
            cite("NI / Ettus Research", "USRP X410 Specifications",
                 "National Instruments technical specification", year=2024,
                 status="tech report",
                 note="`src/experiment_x410.py:61` 이 인용한 원사양 — 4 TX/4 RX · 400 MHz · 12-bit"),
        ]))

    # ── 재현용 코드 셀 ─────────────────────────────────────────────────────
    B.append(code(
        "# 이 편의 숫자를 직접 열어보기 — 표·그림의 모든 값은 아래 JSON 에서 나온다.",
        "import json",
        "D = json.load(open('outputs/report06_derived.json'))",
        "print(json.dumps(D['_meta']['definitions'], ensure_ascii=False, indent=1))",
        "print('원거리장 채택 :', D['farfield_adopted'])",
        "print('기울기 판별폭 :', [(r['airframe'], round(r['gap_db'], 2))",
        "                          for r in D['slope']['rows']])",
        "print('생산 모드     :', D['modes']['production_mode'],",
        "      '· 평균 레벨이동', round(D['modes']['level_shift_production_abs_max_db'], 2), 'dB')",
        "print('크기법칙 차등 :', round(D['size_law']['differential_db'], 2), 'dB')",
        "print('순위 판정     :', D['ranking_validation']['consensus_order'],",
        "      '· 뒤집힘 폭', round(D['ranking_validation']['flip_span_min_db'], 2),",
        "      'dB · 드리프트 여유', round(D['ranking_validation']['drift_margin_db'], 2), 'dB')"))

    # ── 다음 단계 (§5.3) ───────────────────────────────────────────────────
    B.append(next_steps([
        ("야외 고정기하에서 세 파형을 같은 세션에 송신하고 방위 스윕으로 자세평균 순서를 잰다",
         f"파형 상대순위 "
         f"`{' > '.join(D.get('ranking_validation.consensus_order'))}` 가 실측에서 확인된다 — "
         f"판정 문턱은 뒤집힘 폭 "
         f"{D.num('ranking_validation.flip_span_min_db', fmt='{:.2f}', unit='dB')} 다",
         "06편 §3 · §4 → 05편 결과와 대조"),
        ("교정구를 표적과 같은 자리·같은 높이에서 세션 시작과 끝에 잰다",
         f"지금 우리 PO 출력인 절대 레벨이 처음으로 측정에 앵커된다 — "
         f"생산 모드의 평균 레벨이동 "
         f"{D.num('modes.level_shift_production_abs_max_db', fmt='{:.2f}', unit='dB')} 가 "
         f"측정값으로 대체된다",
         "06편 §2-2 · §3-2 → `src/sigma_anchor.py` 레벨 앵커 등록"),
        ("기체 2종을 입고하고 §2 체크리스트 6항목대로 세션을 돌린다",
         "우리 기체의 절대 σ(f, φ) 가 외부 앵커 없이 자체 측정으로 선다",
         "`outputs/measured_sigma.json` → `src/sigma_anchor.py:255` 앵커 등록"),
        ("세 밴드를 같은 세션에서 재고 세션간 진폭 재현성을 기록한다",
         f"밴드 기울기가 우리 커널 값과 앵커 "
         f"{D.num('slope.anchor_db_per_ghz', fmt='{:.3f}')} dB/GHz 중 어디에 앉는지 결정된다",
         "06편 §4-1 → 02편 §4 재기술"),
        ("두 기체를 한 캠페인에서 재고 μ 차이의 부호를 본다",
         f"크기전이 법칙 L² vs L⁴ (원장 "
         f"{D.num('size_law.uncontrolled_size_db', fmt='{:.2f}', unit='dB')})가 확정된다",
         "06편 §4-2 → `src/sigma_anchor.py` 크기법칙 고정"),
        ("VV / VH / HV / HH 4조합을 잰다",
         "무편파 스칼라 모형과 VV 측정의 차가 dB 로 확정된다",
         "`src/materials.py:171` `gamma_po()` 의 편파 확장 결정"),
        ("β ≤ 45° 안에서 송수신 분리각별 기하를 §2-1·§2-5 방식으로 계산한다",
         "바이스태틱 세션의 원거리장 거리와 게이팅 임계가 정해진다",
         "`benchmark/plan_measurement.py` 확장"),
        ("같은 세션에서 모서리가 많은 표준체(평판·이면각)를 함께 잰다",
         f"1차 PTD 항의 부호와 크기를 실측이 심판한다 — 평판 RMS 시험은 위상맹목이고, 켠 비용은 "
         f"{PW.num('verdict.cost_increase_pct', fmt='{:+.1f}', unit='%')} 다",
         "06편 §2-2 확장 · §4 결정표 → `benchmark/ptd_plate_validation.py`"),
        ("자세축과 로터위상축을 σ 생산자에 배선한 뒤 sim-to-sim ablation 을 돌린다",
         f"우리 σ 가 (σ̄, τ_decorr, 분포형) 3개 수로 환원되는지가 실측 없이 판정된다 — 태스크는 "
         f"분류가 아니라 **검출**로 고정한다(통계 RCS 와 큐브에는 로터가 없어 분류는 로터 유무를 "
         f"재는 실험이 된다)",
         "`docs/SIM2REAL_PLAN.md` → `outputs/s2r_protocol.json`"),
        ("3팔 실측 ablation 설계를 검출 태스크와 supervision 사다리로 다시 짠다",
         f"현 설계 판정 {S2A.num('verdict')} 의 근거가 닫힌다 — 자세축·로터위상축을 배선하기 "
         f"전에는 세 팔이 분포형·상관시간 두 수로 환원되어 판정이 설계로 보장된다",
         "`outputs/s2r_attack.json` → `docs/SIM2REAL_PLAN.md`"),
        ("정지 로터 세션과 별도로 회전 세션을 잡는다",
         "마이크로도플러가 앵커와의 사과-대-사과를 깨지 않고 들어온다",
         "06편 §2-4 → future work"),
    ], sec="§5."))

    return B


# =========================================================================== #
def main():
    print("── 리포트 06 빌드 ──")
    J = derive()
    fig_adc(J)
    fig_farfield(J)
    fig_calibration(J)
    fig_size_law(J)
    fig_slope(J)
    fig_ground_bounce(J)
    rep = build_notebook(NB_OUT, blocks(J), strict=True)
    print(f"✅ {os.path.relpath(NB_OUT, _ROOT)}")
    return rep


if __name__ == "__main__":
    main()
