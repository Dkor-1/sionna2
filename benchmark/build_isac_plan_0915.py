#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Korean report notebook docs/ISAC_DETECTION_TRACKING_PLAN_0915.ipynb (ISAC detection + tracking plan).

Run
    CUDA_VISIBLE_DEVICES="" /workspace/.venvs/py312/bin/python benchmark/build_isac_plan_0915.py

Inputs (every number in the notebook is read from these ledgers through report_style.num / table_from):
    outputs/isac_plan_corpus_0915.json (+ outputs/isac_plan_corpus_spectra_0915.npz)
    outputs/isac_plan_kernel_match_0915.json (+ outputs/isac_plan_kernel_match_0915_spectra.npz)
    outputs/isac_plan_engines_0915.json
    outputs/isac_plan_detection_0915.json
    outputs/isac_plan_link_budget_0915.json
    outputs/isac_plan_waveforms_0915.json
    outputs/isac_plan_positioning_0915.json
Each ledger names its generator script in _meta.generator; rerun those first if a ledger is stale.

Outputs
    docs/ISAC_DETECTION_TRACKING_PLAN_0915.ipynb
    outputs/figures/isac_plan_0915_f<N>.png / .pdf

Scope
    Planning report. Simulation results are PathSolver or our-kernel computations in arbitrary dB (not RCS), and
    there is no comparison against RF measurements yet. Published drone RCS values appear only as other groups'
    measurements in the link budget. The prose is Korean because the user reads this report directly.
"""
from __future__ import annotations

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
if hasattr(os, "sched_setaffinity"):
    _cores = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {_cores[0]})

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")]

import numpy as np                                                    # noqa: E402

from report_style import (build_notebook, caption, from_json, header, md,  # noqa: E402
                          next_steps, table_from)
from paper_kit import paper_style, save_figure, series_style         # noqa: E402

NB = "docs/ISAC_DETECTION_TRACKING_PLAN_0915.ipynb"
FIG = "outputs/figures/isac_plan_0915_f{}"

J_CORPUS = "outputs/isac_plan_corpus_0915.json"
J_MATCH = "outputs/isac_plan_kernel_match_0915.json"
J_ENG = "outputs/isac_plan_engines_0915.json"
J_DET = "outputs/isac_plan_detection_0915.json"
J_LINK = "outputs/isac_plan_link_budget_0915.json"
J_WAVE = "outputs/isac_plan_waveforms_0915.json"
J_POS = "outputs/isac_plan_positioning_0915.json"

BR = "<!--cell-->"


def _figure_block(n: int, question: str) -> str:
    """Embed a saved PNG with a path relative to docs/ and the question caption."""
    return "\n".join([f"![figure {n}](../{FIG.format(n)}.png)", "", caption(n, question)])


# ─────────────────────────────────────────────────────────────────────────────
# Figures
# ─────────────────────────────────────────────────────────────────────────────
def fig_corpus_spectra(C) -> None:
    """Figure 1: modulation spectra at el -60 (free sky iso, ground iso, ground aimed) on one absolute dB scale."""
    z = np.load(os.path.join(ROOT, "outputs", C.get("spectra_series.npz")))
    series = {s["series_id"]: s for s in C.get("spectra_series.series")}
    f = np.asarray(z["freq_hz"], float)
    ffl = float(z["ffl_hz"])
    comb = np.asarray(z["comb_bin_mask"], bool)
    pick = [("free_sky__iso__el-60", "free sky, isotropic"),
            ("outdoor01_ground__iso__el-60", "ground scene, isotropic"),
            ("outdoor01_ground__tr38901__el-60", "ground scene, aimed 3GPP element")]
    with paper_style(width="double", aspect=0.42) as st:
        fig, ax = st.figure()
        for i, (sid, label) in enumerate(pick):
            row = int(series[sid]["npz_row"])
            y = np.asarray(z["psd_db"][row], float)
            m = np.isfinite(y) & (f > 0) & (f <= 14 * ffl)
            sty = series_style(i, marker=False)
            ax.plot(f[m] / ffl, y[m], lw=0.8, label=label, color=sty["color"], linestyle=sty["linestyle"],
                    marker="None")
        for h in range(1, 13):
            ax.axvline(h, color="#999999", lw=0.4, zorder=0)
        ax.set_xlabel("frequency / blade flash rate")
        ax.set_ylabel("power per bin [dB, arbitrary ref.]")
        ax.set_title("Pose-varying part of E, elevation -60 deg, 8192 poses")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)

        _ = comb
    save_figure(fig, os.path.join(ROOT, FIG.format(1)), close=True, caption=(
        "Power spectrum of the pose-varying part of the PathSolver field at elevation -60 deg for free sky and "
        "for the flat-ground scene with an isotropic antenna and with an aimed 3GPP element; grey lines mark "
        "the blade flash harmonics."))


def fig_contrast_by_scene(C) -> None:
    """Figure 2: blade-comb contrast against elevation for every production iso row, plus aimed rows."""
    rows = C.get("rows")
    scenes = [("free_sky", "free sky"), ("outdoor01_bldg", "buildings only"),
              ("outdoor01_ground", "ground only"), ("outdoor01", "ground + buildings"),
              ("street_canyon", "street canyon")]
    with paper_style(width="double", aspect=0.45) as st:
        fig, ax = st.figure()
        for i, (sc, label) in enumerate(scenes):
            pts = [(r["el_deg"], r["comb_contrast_db"]) for r in rows
                   if r["scene"] == sc and r["ant"] == "iso" and r["default_height"]]
            if not pts:
                continue
            x, y = zip(*sorted(pts))
            sty = series_style(i)
            ax.plot(x, y, linestyle="none", marker=sty["marker"], color=sty["color"], ms=4, label=label)
        ant = [(r["el_deg"], r["comb_contrast_db"]) for r in rows if r["ant"] != "iso" and r["scene"] != "free_sky"]
        if ant:
            x, y = zip(*ant)
            ax.plot(x, y, linestyle="none", marker="*", color="#000000", ms=9, label="ground scene, aimed element")
        ax.axhline(0.0, color="#777777", lw=0.6)
        ax.set_xlabel("elevation [deg]")
        ax.set_ylabel("blade-comb contrast [dB]")
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)

    save_figure(fig, os.path.join(ROOT, FIG.format(2)), close=True, caption=(
        "Blade-comb contrast of every production PathSolver cell against elevation, by scene, for the "
        "isotropic antenna at the default drone height, with the aimed-element cells of the ground scene."))


def fig_eca(D) -> None:
    """Figure 4: ECA retained target power against Doppler offset, measured and analytic."""
    rows = [r for r in D.get("f3_eca.rows") if r["retained_db_analytic"] is not None]
    x = [r["doppler_bin"] for r in rows]
    with paper_style(width="single", aspect=0.72) as st:
        fig, ax = st.figure()
        s0, s1 = series_style(0), series_style(1, marker=False)
        ax.plot(x, [r["retained_db_measured"] for r in rows], linestyle="none", marker=s0["marker"],
                color=s0["color"], label="ECA output")
        ax.plot(x, [r["retained_db_analytic"] for r in rows], color=s1["color"], linestyle=s1["linestyle"],
                marker="None", label="whole-CPI projection formula")
        ax.set_xlabel("target Doppler [bins]")
        ax.set_ylabel("retained power [dB]")
        ax.legend(loc="lower right", frameon=False)
    save_figure(fig, os.path.join(ROOT, FIG.format(4)), close=True, caption=(
        "Target power left after the repository's standard ECA canceller against the target Doppler offset, "
        "with the analytic whole-CPI projection loss."))


def fig_cfar(D) -> None:
    """Figure 5: false CFAR cells around one strong cell, float32 vs float64 running sums."""
    rows = D.get("f4_cfar.rows")
    x = [r["strong_cell_db"] for r in rows]
    with paper_style(width="single", aspect=0.72) as st:
        fig, ax = st.figure()
        for i, (k, label) in enumerate([("false_cells_float32", "float32 running sums"),
                                        ("false_cells_float64", "float64 running sums")]):
            s = series_style(i)
            ax.plot(x, [r[k] for r in rows], color=s["color"], linestyle=s["linestyle"], marker=s["marker"],
                    ms=4, label=label)
        ax.set_xlabel("strong cell above background [dB]")
        ax.set_ylabel("false detections")
        ax.legend(loc="upper left", frameon=False)
    save_figure(fig, os.path.join(ROOT, FIG.format(5)), close=True, caption=(
        "Number of cells the batched GPU CA-CFAR marks away from one strong cell on a unit-mean background, "
        "with running sums in float32 and in float64."))


# ─────────────────────────────────────────────────────────────────────────────
# Sections
# ─────────────────────────────────────────────────────────────────────────────
def sec_corpus(C) -> list:
    s = "summary_iso[scene={}]"
    b = []
    b.append(md(
        "## §1. 지금 시뮬레이션 자료가 보여 주는 것",
        "",
        f"대상은 PathSolver 생산 칸 {C.num('inventory.n_production_complete', fmt='{:d}', unit='개')} 이다"
        " — 매트리스 4E · 15 m · 3.5 GHz · 광선 4×10⁹ · 자세 8,192 · 확산 켬(`R0D0E0F1`).",
        f"자세마다 드론 날개가 도는 몫을 보려고 E 의 평균을 뺀 뒤 스펙트럼을 내고, 날개 반짝임 주파수의 1~12 배음"
        f" ±2 칸 평균 전력을 나머지 칸 평균 전력으로 나눈 값을 **날개 빗살 대비**라 부른다.",
        "레벨은 임의 기준의 PathSolver dB 로만 비교한다.",
        BR,
        "| 장면 | 칸 수 | 빗살 대비 최소 | 최대 | 앙각 |",
        "|---|---|---|---|---|",
        *[f"| {label} | {C.num(s.format(k) + '.n_cells', fmt='{:d}')} | "
          f"{C.num(s.format(k) + '.contrast_min_db', fmt='{:.1f}', unit='dB')} | "
          f"{C.num(s.format(k) + '.contrast_max_db', fmt='{:.1f}', unit='dB')} | "
          f"{C.num(s.format(k) + '.el_min_deg', fmt='{:.0f}')} ~ {C.num(s.format(k) + '.el_max_deg', fmt='{:.0f}', unit='°')} |"
          for k, label in [("free_sky", "빈 하늘"), ("outdoor01_bldg", "건물만"), ("outdoor01_ground", "지면만"),
                           ("outdoor01", "지면+건물"), ("street_canyon", "도심 협곡")]],
    ))
    b.append(md(_figure_block(2, "지면이 든 장면에서 날개 빗살 대비는 앙각마다 몇 dB 인가?")))
    b.append(md(
        "### 흔들어 본 손잡이",
        "",
        f"창·배음 수·칸 폭·바닥 정의를 여섯 가지로 바꿔도, 기본 높이의 지면이 든 장면 최대 대비(고립 자세 포함 값)는"
        f" {C.num('knob_sensitivity.ground_like_max_contrast_default_height_db', fmt='{:.1f}', unit='dB')},"
        f" 빈 하늘 최소 대비는 {C.num('knob_sensitivity.free_sky_min_contrast_db', fmt='{:.1f}', unit='dB')} 다.",
        f"같은 설정 반복 실행 {C.num('repeats.n_groups', fmt='{:d}', unit='묶음')} 에서 대비 차는 최대"
        f" {C.num('repeats.max_contrast_spread_db', fmt='{:.3f}', unit='dB')} 다.",
        f"드론을 지면 위 80 m 로 올린 칸은 {C.num('height.rows[scene=outdoor01_ground,el_deg=-60,env_alt_m=80,ant=iso].comb_contrast_db', fmt='{:.1f}', unit='dB')}"
        f"(앙각 −60°) 까지 오른다.",
    ))
    b.append(md(
        "### 지면이 더한 변하는 몫",
        "",
        f"같은 자세끼리 지면 장면에서 빈 하늘을 빼면, 자세에 따라 변하는 몫이 빈 하늘보다"
        f" {C.num('ground_floor.added_varying_over_free_sky_min_db', fmt='{:.1f}')}"
        f" ~ {C.num('ground_floor.added_varying_over_free_sky_max_db', fmt='{:.1f}', unit='dB')} 크다"
        f"({C.num('ground_floor.n_matched_iso_pairs', fmt='{:d}', unit='쌍')}).",
        f"그 몫의 스펙트럼 평탄도는 앙각 −60° 에서 {C.num('ground_floor.rows[scene=outdoor01_ground,el_deg=-60,build=2.1.0,depth=2].flatness', fmt='{:.3f}')}"
        f"로, 같은 길이 흰 잡음의 {C.num('ground_floor.rows[scene=outdoor01_ground,el_deg=-60,build=2.1.0,depth=2].flatness_white_ref', fmt='{:.3f}')} 와 같은 자리에 있다.",
        f"광선 수를 10⁹ 이상으로 늘려도 그 수준은 {C.num('ray_ladder.varying_min_db_at_or_above_1e9', fmt='{:.1f}')}"
        f" ~ {C.num('ray_ladder.varying_max_db_at_or_above_1e9', fmt='{:.1f}', unit='dB')} 에 머문다(앙각 −60°).",
        BR,
        "### 고립 자세",
        "",
        "**고립 자세** = 8,192 자세의 E 에서 복소 중앙값과의 거리가 그 거리 중앙값의 20 배를 넘는 자세다.",
        f"지면만 장면 {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].n_cells', fmt='{:d}', unit='칸')} 전부에 고립 자세가"
        f" {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].n_outlier_poses_min', fmt='{:d}')}"
        f" ~ {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].n_outlier_poses_max', fmt='{:d}', unit='개')} 있고,"
        f" 변하는 전력의 {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].share_min', fmt='{:.1%}')}"
        f" ~ {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].share_max', fmt='{:.1%}')} 를 쥔다.",
        f"그 자세만 복소 중앙값으로 바꾸면 대비가 {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].contrast_replaced_min_db', fmt='{:.1f}')}"
        f" ~ {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].contrast_replaced_max_db', fmt='{:.1f}', unit='dB')} 이고,"
        f" 같은 수의 무작위 자세를 바꾼 대조는 최대 {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].random_control_contrast_max_db', fmt='{:.1f}', unit='dB')} 다.",
        f"반복 실행과 Sionna 판 사이에서 같은 자세가 고립 자세로 잡힌다(Jaccard 최소 {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].cross_build_jaccard_min', fmt='{:.3f}')}).",
        "평탄도가 흰 잡음과 같은 자리라는 관찰은 흩어진 충격 몇 개로도 나오므로, 원인은 이 수로 가르지 않는다.",
        BR,
        f"도심 협곡에서는 대체한 대비가 문턱에 따라 움직인다(문턱 50 배에서 최소 {C.num('dropout.summary[scene=street_canyon,ant=iso].contrast_replaced_f50_min_max_db[0]', fmt='{:.1f}', unit='dB')}) — 그 칸들은 문턱을 함께 적어 인용한다.",
        "고립 자세에서 어느 경로가 달라지는지는 경로 목록 진단으로 확인한다(DEEP_DROP_0902 의 옛 목록은 실외 전체 장면 두 칸에서 레이다 자신의 지면 반사를 가리켰다).",
    ))
    b.append(md(_figure_block(1, "앙각 −60° 에서 빈 하늘·지면(등방)·지면(조준)의 변하는 몫 스펙트럼은 어떻게 다른가?")))
    a = "antenna_pairs.rows[scene=outdoor01_ground,el_deg={},env_alt_m={}]"
    b.append(md(
        "### 조준한 안테나 — 지금까지 도착한 칸",
        "",
        "레이다에 3GPP TR 38.901 소자 모형을 달고 드론을 향해 고정 조준했다(최대 감쇠 30 dB).",
        "",
        "| 앙각 | 드론 높이 | 등방 대비 | 조준 대비 | 비빗살 바닥 변화 |",
        "|---|---|---|---|---|",
        *[f"| {el}° | {alt} m | {C.num(a.format(el, alt) + '.contrast_iso_db', fmt='{:.1f}', unit='dB')} | "
          f"{C.num(a.format(el, alt) + '.contrast_ant_db', fmt='{:.1f}', unit='dB')} | "
          f"{C.num(a.format(el, alt) + '.noncomb_delta_db', fmt='{:+.1f}', unit='dB')} |"
          for el, alt in [(-15, 20), (-60, 20), (-60, 14.5)]],
        "",
        f"빈 하늘에서는 조준이 모든 레벨을 {C.num('antenna_pairs.rows[scene=free_sky,el_deg=-60].total_delta_db', fmt='{:.1f}', unit='dB')} 올린다"
        f"(소자 최대 이득 왕복 {C.num('antenna_pairs.code_expectation.two_way_peak_gain_db', fmt='{:.0f}', unit='dB')}).",
        BR,
        f"감쇠 상한 20·50 dB 와 조준 오차를 흔드는 칸 {C.num('antenna_pairs.n_queued_ant_cells_not_landed_active', fmt='{:d}', unit='개')} 가 아직 큐에 있다."
        " 머리기사 숫자로는 그 칸이 온 뒤에 올린다.",
        "조준 칸의 고립 자세는 기본 높이에서 0 개다 — 이 표만으로는 조준의 몫과 고립 자세의 몫을 가를 수 없고, 두 대비 차이를 안테나 효과로 읽지 않는다.",
        f"레이다를 1.5 m 에 단 조준 칸(앙각 −15°)은 고립 자세 {C.num('dropout.summary[scene=outdoor01_ground,ant=tr38901].n_outlier_poses_max', fmt='{:d}', unit='개')} 가 남는다.",
        "소자 모형은 보유 안테나 여섯 대의 실제 패턴이 아니다 — 제원을 받으면 그 패턴으로 바꿔 다시 계산한다.",
    ))
    b.append(md(
        "### 추적 쪽에서 읽을 것",
        "",
        "- 모든 칸은 제자리 비행이다 — 동체는 0 Hz 에 정지 지면과 함께 앉고, 영도플러 제거가 둘을 함께 지운다.",
        "- 자료는 거리 하나·안테나 합 하나라서 거리·각도·이동·열잡음 축이 비어 있다. 추적 정확도는 새 계산(§7)으로 얻는다.",
        f"- 창 길이를 줄이면 빈 하늘 대비가 내려간다: 앙각 −15° 에서 자세 1,024 개"
        f" {C.num('dwell.rows[scene=free_sky,ant=iso,el_deg=-15,window_poses=1024].comb_contrast_db', fmt='{:.1f}', unit='dB')},"
        f" 8,192 개 {C.num('dwell.rows[scene=free_sky,ant=iso,el_deg=-15,window_poses=8192].comb_contrast_db', fmt='{:.1f}', unit='dB')}.",
    ))
    return b


def sec_engines(E) -> list:
    b = []
    b.append(md(
        "## §3. 두 계산 도구를 추적에 쓸 때 지킬 계약",
        "",
        "### PathSolver (Sionna RT 2.1.0 의 경로 계산기)",
        "",
        f"- 설치본에서 경로 계수 배열의 축은 `[수신기, 수신 안테나, 송신기, 송신 안테나, 경로]` 이고, 합성 배열 기본값에서는 지연·각도가"
        f" `[수신기, 송신기, 경로]` 로 안테나 축 없이 나온다. 저장소의 `report15_probe.unpack` 식 평탄화는 계수의"
        f" {E.num('rt_contract.unpack_style_kept_fraction_of_coefficients', fmt='{:.0%}')} 만 남긴다 — 다중 안테나 작업에서는 축을 그대로 둔다.",
        f"- `cir()`·`cfr()` 의 기본 지연 정규화는 링크마다 최소 지연({E.num('rt_contract.normalize_delays.min_tau_ns', fmt='{:.3f}', unit='ns')})을 빼서"
        f" 공통 위상 {E.num('rt_contract.normalize_delays.phase_rotation_deg_measured', fmt='{:.2f}', unit='°')} 를 돌린다."
        " 재추적 구간을 이어 붙이는 추적용 채널은 `normalize_delays=False` 로 받는다.",
        f"- 물체 속도 2 m/s 로 낸 도플러는 {E.num('rt_doppler.doppler_hz_measured', fmt='{:.4f}', unit='Hz')},"
        f" 2v/λ 는 {E.num('rt_doppler.doppler_hz_expected_2v_over_lambda', fmt='{:.4f}', unit='Hz')} 다."
        " 한 물체에는 병진 속도 하나만 들어간다 — 회전 날개는 자세마다 장면을 다시 풀거나 조각 메쉬로 나눈다.",
        BR,
        f"- 한 번 푼 뒤 도플러로 외삽한 채널과 다시 푼 채널의 차는 판 {E.num('extrapolation.translation.distance_m', fmt='{:.3f}', unit='m')} 이동"
        f"(거리 {E.num('extrapolation.translation.range_m', fmt='{:.0f}', unit='m')}) 에서 최대 {E.num('extrapolation.translation.max_rel_diff', fmt='{:.2%}')} 다(CPU 작은 시험).",
        f"- 기울기가 {E.num('extrapolation.rotation_tilt.specular_cutoff_tilt_deg', fmt='{:.2f}', unit='°')} 를 넘으면 판의 정반사 경로가"
        f" {E.num('extrapolation.rotation_tilt.n_specular_paths_before', fmt='{:d}')} 개에서"
        f" {E.num('extrapolation.rotation_tilt.n_specular_paths_after', fmt='{:d}')} 개로 사라진다 — 외삽은 경로의 생멸을 따라가지 못하므로 재추적 지점을 둔다.",
    ))
    t = "cost.trajectory_rows[scene={},build=rt210,rate_hz={}].single_process_wall_hours"
    b.append(md(
        "### 비용 — 궤적 10 초를 자세마다 풀면",
        "",
        "| 장면 | 자세당 시간 | 1 kHz · 10 초 | 10 kHz · 10 초 |",
        "|---|---|---|---|",
        *[f"| {label} | {E.num(f'cost.rows[scene={k},build=rt210,depth=2].median_s_per_pose', fmt='{:.2f}', unit='s')} | "
          f"{E.num(t.format(k, 1000), fmt='{:.1f}', unit='h')} | {E.num(t.format(k, 10000), fmt='{:.0f}', unit='h')} |"
          for k, label in [("free_sky", "빈 하늘"), ("outdoor01_ground", "지면"),
                           ("sionna-simple_street_canyon", "도심 협곡")]],
        "",
        "시간은 카드를 나눠 쓰는 조건에서 한 프로세스가 잰 벽시계 시간이고, 자세마다 장면을 다시 짓는 시간을 포함한다.",
        f"날개 끝 도플러를 겹침 없이 담으려면 제자리 비행에서 {E.num('rotor.required_pose_rate[body_speed_mps=0].required_rate_hz', fmt='{:.0f}', unit='Hz')},"
        f" 동체 15 m/s 에서 {E.num('rotor.required_pose_rate[body_speed_mps=15].required_rate_hz', fmt='{:.0f}', unit='Hz')} 의 자세율이 든다(앙각 −15° 기준).",
    ))
    b.append(md(
        "### 우리 커널 (드론 표면 물리광학 적분)",
        "",
        f"- 한 번 부를 때 복소수 하나를 낸다. 격자를 드론을 따라 옮기면 λ/8 이동에서 위상이"
        f" {E.num('kernel.recentred_phase_deg_for_lambda_over_8_move', fmt='{:.1e}', unit='°')}, 격자를 고정하면"
        f" {E.num('kernel.frozen_grid_phase_deg', fmt='{:.3f}', unit='°')} 돈다 — 이동 위상을 쓰려면 격자를 고정한다.",
        f"- 반송파를 ±50 MHz 바꿔도 위상 폭이 {E.num('kernel.phase_vs_frequency_measured_span_deg', fmt='{:.3f}', unit='°')} 에 머문다."
        " 거리칸 정보는 출력 밖에 있다 — 지연·도플러·경로 손실은 궤적에서 따로 붙인다.",
        f"- 커널 자세당 시간 중앙값은 {E.num('cost.kernel_cost.median_s_per_pose', fmt='{:.3f}', unit='s')} 다"
        f"({E.num('cost.kernel_cost.n_shards', fmt='{:d}', unit='샤드')}, 장치 기록 없음).",
        "- 환경 메쉬는 받지 않는다: 격자가 넘긴 메쉬 전체의 상자로 잡혀 지면을 넣으면 격자점이 폭증한다"
        "(`benchmark/elevation_sweep_md.py:664-671` 주석의 계산). 평평한 지면은 거울상 법(`--ground`)으로 넣는다 — 그 갈래는 드론 직접·지면 한 번·지면 두 번 경로를 계산하고, 지면 자체의 되돌림은 PathSolver 장면에서 얻는다.",
    ))
    return b


def sec_detection(D) -> list:
    b = []
    b.append(md(
        "## §4. 탐지 코드 — 한 CPI 판정에서 추적까지",
        "",
        "지금 체인은 ECA 직접파 제거 → 거리-도플러 지도 → CA-CFAR 까지, 표적 하나의 한 CPI 판정이다.",
        "",
        "| 점검 | 잰 것 | 추적에 옮길 때 할 일 |",
        "|---|---|---|",
        f"| 배열 이득 | 조향 벡터 네 가지(참 방향·틀린 방향·영벡터·부호 교대)의 Pd 가 모두 {D.num('f1_steering.variants[name=steer_true_az].pd', fmt='{:.3f}')} | 채널별 복소 IQ 로 각도를 추정한다 |",
        f"| 거리축 | 원장의 Rb 만 바꾸면 축이 {D.num('f2_range_axis.axis_shift_m_when_meta_rb_changes', fmt='{:.0f}', unit='m')} 이동, 커널 지연 {D.num('f2_range_axis.measured_extra_lag_samples', fmt='{:d}', unit='표본')} | 참값 없이 −l_min 으로 축을 세운다 |",
        f"| ECA | 0.1 도플러 칸 표적이 {D.num('f3_eca.rows[doppler_bin=0.1].retained_db_measured', fmt='{:.1f}', unit='dB')} 남는다 | 느린 표적 전략을 따로 둔다 |",
        f"| GPU CFAR | float32 누적합에서 강한 칸 {D.num('f4_cfar.first_strong_cell_db_with_float32_false_cells', fmt='{:d}', unit='dB')} 부터 오검출 | 누적합을 float64 로 올린다 |",
        f"| 봉우리 | 표적 {D.num('f5_multi_target.n_targets', fmt='{:d}')} 개에 CFAR 칸 {D.num('f5_multi_target.cfar_mask_cells', fmt='{:d}')} 개, 돌려주는 봉우리 {D.num('f5_multi_target.peaks_returned_by_peak_detection', fmt='{:d}')} 개 | 칸을 묶어 검출 목록으로 낸다 |",
        f"| 기준 프레임 | 프레임마다 내용이 다르면 손실 {D.num('f14_reference.loss_db_max', fmt='{:.1f}')} ~ {D.num('f14_reference.loss_db_min', fmt='{:.1f}', unit='dB')} | 프레임마다 기준을 쓴다 |",
    ))
    b.append(md(
        f"기존 결과는 기준 프레임을 한 장 반복해 만든 CPI 라서 마지막 줄의 손실을 겪지 않는다(반복 프레임 대조 {D.num('f14_reference.max_abs_repeated_frame_control_db', fmt='{:.1f}', unit='dB')}).",
        f"리포트 12 의 L1 설정에서 가장 센 칸은 중앙값보다 {D.num('f4_cfar.report12_l1_check.max_cell_over_median_db', fmt='{:.1f}', unit='dB')} 위이고 float32·float64 판정 차는"
        f" {D.num('f4_cfar.report12_l1_check.mask_mismatches', fmt='{:d}', unit='칸')} 이다.",
        BR,
        _figure_block(4, "표적 도플러가 0 에 가까울 때 ECA 뒤에 남는 표적 전력은 몇 dB 인가?"),
    ))
    b.append(md(_figure_block(5, "강한 칸이 배경보다 몇 dB 위일 때 float32 누적합 CFAR 가 오검출을 내기 시작하는가?")))
    tr = "tracking_inventory.rows[component_id={}].named_definitions_matching"
    b.append(md(
        "### 추적까지 새로 짓는 것",
        "",
        "`src/`·`benchmark/` 에서 이름으로 정의된 함수·클래스를 센 결과다(문서 문자열의 언급은 뺀다).",
        "",
        "| 부품 | 이름 정의 수 | 쓸 도구 |",
        "|---|---|---|",
        f"| 칼만·EKF | {D.num(tr.format('kalman_ekf_ukf'), fmt='{:d}')} | Stone Soup (`OPENSOURCE.md` 결정) |",
        f"| 자료 연관 | {D.num(tr.format('data_association'), fmt='{:d}')} | Stone Soup GNN → JPDA |",
        f"| 게이팅 | {D.num(tr.format('gating'), fmt='{:d}')} | Stone Soup |",
        f"| CFAR 칸 묶기 | {D.num(tr.format('cfar_cell_clustering'), fmt='{:d}')} | 연결 성분 + 부분칸 보간(`passive_process._subbin` 재사용) |",
        f"| 궤적 관리 | {D.num(tr.format('track_management'), fmt='{:d}')} | Stone Soup 확정·삭제 규칙 |",
        f"| 추적 지표 | {D.num(tr.format('tracking_metrics'), fmt='{:d}')} | GOSPA·연속성 + TR 38.765 지표 |",
        "",
        "측정 모델의 야코비안은 `benchmark/verify_observability.py` 의 (거리, 도플러, 각도) 행을 옮겨 쓴다.",
    ))
    return b


def main() -> int:
    C = from_json(J_CORPUS)
    E = from_json(J_ENG)
    D = from_json(J_DET)

    os.makedirs(os.path.join(ROOT, "outputs", "figures"), exist_ok=True)
    fig_corpus_spectra(C)
    fig_contrast_by_scene(C)
    fig_eca(D)
    fig_cfar(D)

    blocks = [
        header(
            num="ISAC",
            title="드론 탐지·추적 실험 설계 — X410 한 대 · 지향성 안테나 여섯 대 · 매트리스 4E",
            did="시뮬레이션 자료·두 계산 도구의 계약·탐지 코드를 다시 계산해 점검했다(초안 — 하드웨어·파형·실험 설계 절은 이어서 싣는다).",
            results=[
                f"날개 빗살 대비는 빈 하늘 {C.num('summary_iso[scene=free_sky].contrast_min_db', fmt='{:.1f}')}"
                f" ~ {C.num('summary_iso[scene=free_sky].contrast_max_db', fmt='{:.1f}', unit='dB')},"
                f" 지면만 있는 장면 {C.num('summary_iso[scene=outdoor01_ground].contrast_min_db', fmt='{:.1f}')}"
                f" ~ {C.num('summary_iso[scene=outdoor01_ground].contrast_max_db', fmt='{:.1f}', unit='dB')} 다(등방 안테나, 고립 자세 포함).",
                f"지면만 장면의 고립 자세(약 1 %)를 복소 중앙값으로 바꾸면 대비가"
                f" {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].contrast_replaced_min_db', fmt='{:.1f}')}"
                f" ~ {C.num('dropout.summary[scene=outdoor01_ground,ant=iso].contrast_replaced_max_db', fmt='{:.1f}', unit='dB')} 다.",
                f"현재 탐지 코드는 한 CPI 단일 표적 판정까지이고, 추적 필터 이름 정의는"
                f" {D.num('tracking_inventory.rows[component_id=kalman_ekf_ukf].named_definitions_matching', fmt='{:d}', unit='개')} 다.",
                f"PathSolver 는 지면 장면에서 자세당 {E.num('cost.rows[scene=outdoor01_ground,build=rt210,depth=2].median_s_per_pose', fmt='{:.2f}', unit='s')},"
                f" 우리 커널은 {E.num('cost.kernel_cost.median_s_per_pose', fmt='{:.3f}', unit='s')} 를 쓴다.",
            ],
            method=[
                ("시뮬레이션 자료", "저장된 샤드를 직접 합쳐 대비·정지/변하는 몫·손잡이 흔들기를 다시 계산"),
                ("계산 도구", "설치된 Sionna RT 2.1.0 과 `src/rcs_sbr.py` 를 CPU 작은 시험으로 호출"),
                ("탐지 코드", "합성 입력으로 생산 함수를 불러 조향·거리축·ECA·CFAR·기준 프레임을 재현"),
                ("하드웨어·문헌", "NI·AMD 제원 문서와 다른 연구진의 측정값을 출처와 함께 원장에 기록"),
            ],
            repro=dict(cmd=["CUDA_VISIBLE_DEVICES=\"\" /workspace/.venvs/py312/bin/python benchmark/isac_plan_corpus_0915.py",
                            "CUDA_VISIBLE_DEVICES=\"\" /workspace/.venvs/py312/bin/python benchmark/isac_plan_engines_0915.py",
                            "CUDA_VISIBLE_DEVICES=\"\" /workspace/.venvs/py312/bin/python benchmark/isac_plan_detection_0915.py",
                            "CUDA_VISIBLE_DEVICES=\"\" /workspace/.venvs/py312/bin/python benchmark/build_isac_plan_0915.py"],
                       out=[J_CORPUS, J_ENG, J_DET],
                       runtime="CPU 한 코어 · 원장 각 수 초~수 분"),
        ),
    ]
    blocks += sec_corpus(C)
    blocks += sec_engines(E)
    blocks += sec_detection(D)
    blocks.append(next_steps([
        ("큐 0940·0941 의 조준 칸(감쇠 상한·조준 오차·저고도·도심 협곡)을 받아 §1 표를 다시 굽는다",
         "조준 안테나 대비가 손잡이를 흔들어도 서는지", "runners/jobs_0940_antenna.txt"),
        ("안테나 여섯 대의 대역·이득·앞뒤비를 받아 소자 모형을 실제 패턴으로 바꾼다",
         "반송파와 시뮬레이션 감쇠 상한 값", "benchmark/report15_probe.py"),
    ]))
    build_notebook(NB, blocks, strict=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
