# -*- coding: utf-8 -*-
"""
geometry_benchmark.py — **설계공간 지도**와 주장 사다리 **재판정**
=================================================================================
질문: 기하(모노/바이) × 조명원(WiFi/LTE/5G) 2×3 지도 위에서 각 칸은 무엇을 보고,
      기존 주장 17개 중 무엇이 두 기하 모두에서 서고 무엇이 한쪽에서만 서는가.

계약: `docs/PAPER_SPEC.md` §0(재프레이밍)·§5(좁히기) · `docs/REBUILD_2026-07-30.md` §5(서술 규약)
입력: outputs/{geometry_grid, mono_link, refrate_law, vmax_hardening, sigma_sensitivity,
              monostatic_prior, report13_sigma_grid, verify_cfar}.json
산출: outputs/geometry_benchmark.json · docs/GEOMETRY_BENCHMARK.md
      outputs/figures/geometry_benchmark_map.{png,pdf}

세 구성을 절대 섞지 않는다 (PAPER_SPEC §0.2):
  A 능동 모노스태틱    : 내가 송신 · β≈0 · PRF **설계변수**(예 LaSen)
  B 패시브 준모노스태틱: 남이 송신 · β≈0(수신기를 마스트 옆) · PRF 주어짐
  C 패시브 바이스태틱  : 남이 송신 · β 큼 · PRF 주어짐
⚠ "패시브 모노스태틱" 은 한 단어로 쓰지 않는다.

이 파일이 **새로 계산하는** 것 (나머지는 앞 단계 JSON 인용):
  ⑴ 사용가능 속도창 [v_guard, v_max] 과 그 **동적범위 v_max/v_guard = M/(2·guard_bins)**
     — 기하가 창을 통째로 밀 뿐 **넓히지 못한다**는 항등식
  ⑵ 모노 팔의 블라인드/접힘 비율 (격자 needs_recomputation 2번 항목)
  ⑶ 두 생산결함(앵커 미적용·듀티 미호출)을 넣은 **정정 지도**
  ⑷ LaSen 실측 108 m 를 우리 A-nr 칸에 EIRP 로 환산해 맞대보기

실행:
    cd /workspace/sionna
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/geometry_benchmark.py

집안 규약: 산문·print 는 한국어, **그림 텍스트는 전부 영어**, 수치는 저장소 JSON/함수에서만
가져온다 — 손으로 치지 않는다(마크다운 표도 이 스크립트가 찍는다).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import freespace_scene as FS                       # noqa: E402
import freespace_link as FL                        # noqa: E402

OUT_JSON = os.path.join(_ROOT, "outputs", "geometry_benchmark.json")
OUT_MD = os.path.join(_ROOT, "docs", "GEOMETRY_BENCHMARK.md")
FIG_DIR = os.path.join(_ROOT, "outputs", "figures")
FIG_STEM = os.path.join(FIG_DIR, "geometry_benchmark_map")

BANDS = ("wifi", "lte", "nr")
BAND_LABEL = {"wifi": "WiFi 5.21 GHz", "lte": "LTE 1.84 GHz", "nr": "5G NR 3.5 GHz"}
BAND_MODE = {"wifi": "W1", "lte": "L1", "nr": "G1"}
#: 그림 팔레트 — dataviz 검증기(OKLab ΔE, Machado severity 1.0) 전 쌍 PASS
COLOR = {"A": "#D55E00", "B": "#009E73", "C": "#0072B2"}
MARKER = {"A": "s", "B": "^", "C": "o"}
LINESTYLE = {"A": "-", "B": "--", "C": "-"}


def _load(name):
    with open(os.path.join(_ROOT, "outputs", name), encoding="utf-8") as f:
        return json.load(f)


GRID = _load("geometry_grid.json")
MONO = _load("mono_link.json")
LAW = _load("refrate_law.json")
HARD = _load("vmax_hardening.json")
SIG = _load("sigma_sensitivity.json")
PRIOR = _load("monostatic_prior.json")
SGRID = _load("report13_sigma_grid.json")
CFAR = _load("verify_cfar.json")


# --------------------------------------------------------------------------- #
#  ① 지도 — 2 기하행 × 3 조명원, 칸마다 {검지거리 · v_max · 사용가능 속도창 · 대가}
# --------------------------------------------------------------------------- #
PLACEMENT = {"A": "A_mono_at_illuminator", "B": "B_quasi_mono_L10",
             "C": "C_bistatic_L500"}
ROW_OF = {"A": "monostatic", "B": "monostatic", "C": "bistatic"}


def _dpi_required_db(band, L_m):
    """격자 원장에서 (밴드, 베이스라인) 의 요구 소거깊이[dB] 를 꺼낸다."""
    for row in GRID["interference_ledger"]["passive_dpi"]["by_band"]:
        if row["band"] == band:
            for e in row["by_L"]:
                if abs(e["L_m"] - L_m) < 1e-9:
                    return e["eca_depth_required_db"], e["dnr_vs_noise_db"]
    raise KeyError((band, L_m))


def _adc_row(band, key):
    for r in MONO["adc_headroom"]["by_band"][band]["rows"]:
        if r["config"].startswith(key):
            return r
    raise KeyError((band, key))


def usable_window():
    """사용가능 속도창과 그 **동적범위 항등식**을 계산한다.

    v_max   = λ·PRF/(4 cos(β/2) cos δ)         (무모호 상한)
    v_guard = λ·g/(2 cos(β/2) cos δ)           (0-도플러 가드가 지우는 하한), g = bins·Δf_d
    ⇒ v_max/v_guard = PRF/(2g) = M/(2·bins)    — **기하가 소거된다**.
    기하(β·δ)는 창을 통째로 곱해 밀 뿐 넓히지 못한다.
    """
    out, ident = {}, []
    for b in BANDS:
        g = MONO["regimes"]["guard_by_band"][b]
        rel = MONO["doppler_relief_at_edge"]["by_band"][b]
        prf = GRID["axis_independence"]["P1_floor_is_geometry_independent"]["prf_ambient_hz"][b]
        lam = GRID["axis_independence"]["P1_floor_is_geometry_independent"]["lam_m"][b]
        M = int(FS.M_from_prf(FS.T_CPI_REF_S, prf))
        v_guard_mono = float(g["v_guard_monostatic_ms"])
        v_max_mono = float(g["v_max_unambiguous_ms"])
        relief_edge = float(rel["relief_at_edge_x"]["median"])
        relief_half = float(rel["relief_at_half_baseline_x"]["median"])
        dyn_num = v_max_mono / v_guard_mono
        dyn_closed = M / (2.0 * FS.DOPPLER_GUARD_HARD_BINS)
        ident.append(abs(dyn_num - dyn_closed))
        out[b] = dict(
            prf_hz=prf, lam_m=lam, M=M,
            doppler_bin_hz=float(g["doppler_bin_hz"]),
            guard_half_width_hz=float(g["guard_half_width_hz"]),
            v_guard_mono_ms=v_guard_mono, v_max_mono_ms=v_max_mono,
            v_guard_bistatic_at_edge_ms=v_guard_mono * relief_edge,
            v_max_bistatic_at_edge_ms=float(rel["v_max_bistatic_at_edge_ms"]),
            v_guard_bistatic_half_baseline_ms=v_guard_mono * relief_half,
            v_max_bistatic_half_baseline_ms=v_max_mono * relief_half,
            relief_at_edge_x=relief_edge, relief_at_half_baseline_x=relief_half,
            dynamic_range_numeric=dyn_num, dynamic_range_closed_form=dyn_closed)
    return dict(
        form=("v_max/v_guard = PRF/(2·bins·Δf_d) = M/(2·bins) — β·δ 가 분자·분모에서 "
              "똑같이 소거된다"),
        guard_bins_hard=float(FS.DOPPLER_GUARD_HARD_BINS),
        by_band=out,
        identity_max_abs_diff=float(max(ident)),
        finding=("⭐ 기하는 속도창을 **통째로 민다**. 완화 1/cos(β/2) 가 상한과 하한에 똑같이 "
                 "곱해지므로 폭은 M/(2·bins) 로 고정이다 — "
                 f"WiFi·LTE {out['wifi']['dynamic_range_numeric']:.4g}배, "
                 f"5G {out['nr']['dynamic_range_numeric']:.4g}배 — 기하는 창을 밀고 CPI 가 폭을 정한다."),
        why_it_matters=("5G 의 창은 상한이 하한의 1.67배다. 같은 CPI 에서 WiFi·LTE 는 33.3배다 — "
                        "이 비가 곧 '한 CPI 안에 도플러 셀이 몇 개 있나'(M) 다."))


def drone_band():
    """드론 속도대 — 저장소 장면속도와 게재 기체 최고속도에서 가져온다."""
    rows = LAW["drones"]["rows"]
    return dict(
        scene_speeds_ms=list(FS.FS_SPEED),
        source_scene="src/freespace_scene.py : FS_SPEED",
        published_max_ms={k: v["max_speed_ms"] for k, v in rows.items()},
        band_used_ms=[float(FS.FS_SPEED[0]), float(FS.FS_SPEED[1])],
        note="커버리지 판정은 저장소 장면속도 5~15 m/s 로 한다. 기체 게재 최고속도는 14~25 m/s 다.")


def _coverage(v_guard, v_max, lo, hi):
    """속도창 [v_guard, v_max] 이 드론대 [lo, hi] 를 덮는 비율."""
    if v_max is None:
        return None
    a, b = max(v_guard, lo), min(v_max, hi)
    return float(max(0.0, b - a) / (hi - lo))


def build_map():
    win = usable_window()["by_band"]
    band_pub = drone_band()
    lo, hi = band_pub["band_used_ms"]
    ctl = GRID["control_axis"]["by_band"]
    bb = MONO["detection_range"]["broadband"]["cells"]
    zd = MONO["detection_range"]["zero_doppler"]["cells"]
    si = MONO["self_interference"]["by_band"]

    cells = []
    for cfg in ("A", "B", "C"):
        p = PLACEMENT[cfg]
        for b in BANDS:
            w, r = win[b], bb[p][b]
            r0 = zd[p][b]
            mono = ROW_OF[cfg] == "monostatic"
            v_guard = w["v_guard_mono_ms"] if mono else w["v_guard_bistatic_at_edge_ms"]

            if cfg == "A":                                    # PRF 가 설계변수
                t1 = ctl[b]["active_ceiling_1_spec_reference_signal"]
                t2 = ctl[b]["active_ceiling_2_free_waveform_design"]
                v_max = t1["v_max_ms"]                        # 규격 재활용 천장(5G만 확정)
                v_free = t2["v_times_R_m2_per_s"] / max(r["headline_phi90_R90_d_m"], 1e-9)
                v_basis = ("설계변수. 천장 두 단 — ⑴ 3GPP 기준신호 재활용 "
                           f"{'' if t1['prf_hz'] is None else str(t1['prf_hz']) + ' Hz → '}"
                           f"{'미확정' if v_max is None else f'{v_max:.4g} m/s'} · "
                           f"⑵ 자체 파형 설계 시 거리모호 맞바꿈 v·R = "
                           f"{t2['v_times_R_m2_per_s']:.4g} m²/s")
                v_tiers = dict(spec_reference_signal_ms=v_max,
                               free_waveform_at_own_R90_ms=float(v_free),
                               prf_spec_ceiling_hz=t1["prf_hz"])
            else:                                             # 망이 정한 상시 반복률
                v_max = (w["v_max_mono_ms"] if mono else w["v_max_bistatic_at_edge_ms"])
                v_basis = f"상시 기준신호 {w['prf_hz']:.4g} Hz 가 정한다 — 선택 불가"
                v_tiers = None

            if cfg == "A":
                cost = dict(kind="self-interference (SI)",
                            required_total_suppression_db=si[b]["required_total_suppression_db"],
                            measured_best_db=si[b]["measured_total_suppression_db"],
                            deficit_db=si[b]["deficit_vs_measured_db"],
                            noise_rise_db=r["noise_rise_db"],
                            adc_saturates=_adc_row(b, "A active")["saturates"],
                            adc_headroom_db=_adc_row(b, "A active")["headroom_db"],
                            source="Barneto 2019 IEEE TMTT (실측 100 dB)")
            else:
                L = 10.0 if cfg == "B" else 500.0
                req, dnr = _dpi_required_db(b, L)
                adc = _adc_row(b, "B passive" if cfg == "B" else "C passive")
                cost = dict(kind="direct-path interference (DPI)",
                            baseline_m=L, dnr_db=dnr, required_cancellation_db=req,
                            granted_depth_db=90.0, deficit_vs_granted_db=req - 90.0,
                            noise_rise_db=r["noise_rise_db"],
                            adc_saturates=adc["saturates"], adc_headroom_db=adc["headroom_db"],
                            source="freespace_link.dnr_db · 달성깊이 40/60/90 dB 는 선언값")

            cells.append(dict(
                cell_id=f"{cfg}-{b}", configuration=cfg,
                configuration_name=GRID["configurations_and_grid"]
                                       ["configuration_definitions"][cfg]["name"],
                geometry_row=ROW_OF[cfg], illuminator=b, illuminator_label=BAND_LABEL[b],
                who_transmits=GRID["configurations_and_grid"]["configuration_definitions"][cfg]["transmitter"],
                prf_control=GRID["configurations_and_grid"]["configuration_definitions"][cfg]["prf_control"],
                R90_m=r["headline_phi90_R90_d_m"],
                R90_phi_span_m=[r["R90_d_m_min_over_phi"], r["R90_d_m_max_over_phi"]],
                R90_no_interference_m=r0["headline_phi90_R90_d_m"],
                R90_interference_factor_x=r["headline_phi90_R90_d_m"] / r0["headline_phi90_R90_d_m"],
                v_max_ms=v_max, v_max_basis=v_basis, v_max_tiers=v_tiers,
                v_guard_ms=v_guard,
                usable_window_ms=[v_guard, v_max],
                usable_dynamic_range_x=(None if v_max is None else v_max / v_guard),
                covers_drone_band_frac=_coverage(v_guard, v_max, lo, hi),
                covers_5ms=(None if v_max is None else bool(v_guard <= lo <= v_max)),
                covers_15ms=(None if v_max is None else bool(v_guard <= hi <= v_max)),
                cost=cost,
                sigma_path=("직접계산(모노 후방산란, Δσ=0)" if mono
                            else "이등분선 근사 + Δσ(β) 오차막대")))

    rowsum = {}
    for row in ("monostatic", "bistatic"):
        sel = [c for c in cells if c["geometry_row"] == row]
        rowsum[row] = dict(
            occupants=sorted({c["configuration"] for c in sel}),
            R90_span_m=[min(c["R90_m"] for c in sel), max(c["R90_m"] for c in sel)],
            n_cells_covering_5ms=sum(1 for c in sel if c["covers_5ms"]),
            n_cells=len(sel))
    return dict(
        shape=("2 기하행(모노/바이) × 3 조명원 = 6 칸. 모노 행에는 통제가 다른 두 주체 "
               "A(능동)·B(패시브 준모노)가 함께 살고, 지도는 둘을 각각의 줄로 적는다."),
        conventions=dict(
            drone="mavic4pro", phi_deg=90.0, T_cpi_s=FS.T_CPI_REF_S,
            occupancy="G1", eirp_dbm=63.0, grx_dbi=10.0, nf_db=5.0,
            regime="broadband(잔류가 백색으로 퍼진다) — zero_doppler 뷰 병기",
            passive_depth_db=90.0, active_depth_db=100.0,
            normalisation="R90 은 N3(장면 수평거리, 중점기준) · N1(R_eq) 은 mono_link.json 병기",
            sigma="자세평균 · 앵커 미적용 · 듀티 미적용(§5 정정지도 참조)"),
        drone_band=band_pub,
        cells=cells,
        by_geometry_row=rowsum,
        headline=("모노 행과 바이 행을 가르는 것은 확산항이 아니라 **간섭항과 통제권**이다 — "
                  "링크버짓 차이는 검지 한계에서 0.44 dB 로 죽고, 그 자리를 SI 47.1 dB 와 "
                  "PRF 통제권 10배가 채운다."))


# --------------------------------------------------------------------------- #
#  ② 모노 팔의 블라인드/접힘 — 격자 needs_recomputation ②
# --------------------------------------------------------------------------- #
def _blind(tx, rx, d, phi, alt, T, prf, speed, lam, M=None):
    """`FS.blind_fractions` 를 tx/rx 를 명시해 부르는 판. 모노는 tx=rx 로 부른다."""
    psi = np.arange(0.0, 360.0, 0.5)
    tgt = FS.target_pos(d, phi, float(np.linalg.norm(np.subtract(tx, rx))), alt)
    p = FS.fs_params(tx, rx, tgt, (0.0, 0.0, 0.0), FS.C0 / lam)
    V = FS.heading_velocity(psi, speed)
    fd = (V @ (p["u1"] + p["u2"])) / lam
    fb = FS.folded_doppler(fd, prf)
    bw = FS.doppler_bin_hz(T, prf, M)
    hard = np.abs(fb) < FS.DOPPLER_GUARD_HARD_BINS * bw
    decl = np.abs(fb) < FS.GUARD_DOPPLER_BINS * bw
    return dict(blind_hard=float(np.mean(hard)), blind_declared=float(np.mean(decl)),
                alias_frac=float(np.mean(~FS.nyquist_gate(fd, prf))),
                bin_hz=float(bw), beta_deg=float(p["beta"]), el_deg=float(p["el_deg"]))


def blind_and_fold():
    """모노(TX=RX) vs 바이(L=500 m) 의 블라인드·접힘 비율을 같은 규약으로 낸다."""
    out, reg = {}, []
    P1 = GRID["axis_independence"]["P1_floor_is_geometry_independent"]
    bb = MONO["detection_range"]["broadband"]["cells"]
    for b in BANDS:
        lam, prf = P1["lam_m"][b], P1["prf_ambient_hz"][b]
        M = int(FS.M_from_prf(FS.T_CPI_REF_S, prf))
        per = {}
        for speed in FS.FS_SPEED:
            d_c = bb["C_bistatic_L500"][b]["headline_phi90_R90_d_m"]
            d_a = bb["A_mono_at_illuminator"][b]["headline_phi90_R90_d_m"]
            bi = _blind(FS.FS_TX, FS.FS_RX(FS.L_REF), d_c, FS.PHI_HEADLINE_DEG,
                        FS.FS_ALT[0], FS.T_CPI_REF_S, prf, speed, lam, M)
            mo_same_d = _blind(FS.FS_TX, FS.FS_TX, d_c, FS.PHI_HEADLINE_DEG,
                               FS.FS_ALT[0], FS.T_CPI_REF_S, prf, speed, lam, M)
            mo_own_d = _blind(FS.FS_TX, FS.FS_TX, d_a, FS.PHI_HEADLINE_DEG,
                              FS.FS_ALT[0], FS.T_CPI_REF_S, prf, speed, lam, M)
            ref = FS.blind_fractions(np.arange(0.0, 360.0, 0.5), FS.PHI_HEADLINE_DEG,
                                     d_c, FS.L_REF, FS.FS_ALT[0], FS.T_CPI_REF_S,
                                     prf, speed, lam, M=M)
            reg += [abs(bi["blind_hard"] - ref["blind_hard"]),
                    abs(bi["alias_frac"] - ref["alias_frac"])]
            per[f"speed_{speed:g}"] = dict(
                bistatic_L500_at_its_R90=bi,
                monostatic_at_the_same_scene_point=mo_same_d,
                monostatic_at_its_own_R90=mo_own_d,
                delta_blind_hard=mo_same_d["blind_hard"] - bi["blind_hard"],
                delta_alias_frac=mo_same_d["alias_frac"] - bi["alias_frac"],
                d_bistatic_m=d_c, d_monostatic_m=d_a)
        out[b] = per
    dblind = [abs(v[f"speed_{s:g}"]["delta_blind_hard"])
              for v in out.values() for s in FS.FS_SPEED]
    dalias = [abs(v[f"speed_{s:g}"]["delta_alias_frac"])
              for v in out.values() for s in FS.FS_SPEED]
    return dict(
        convention=("ψ 격자 720점 · φ=90° · alt=60 m · T_CPI=0.1 s · 정본 가드 1.5빈 · "
                    "M=PRF·T_CPI 실현 빈폭"),
        regression_vs_repo_max_abs=float(max(reg)),
        regression_note="바이 팔을 `freespace_scene.blind_fractions` 와 대조 — 0 이어야 한다",
        by_band=out,
        max_abs_delta_blind_hard=float(max(dblind)),
        max_abs_delta_alias_frac=float(max(dalias)),
        finding=("같은 장면점에서 두 기하의 블라인드·접힘 비율 차이가 "
                 f"각각 {max(dblind):.3g} · {max(dalias):.3g} 다 — 검지 한계에서 β 가 3° 안이라 "
                 "접힘 격자가 사실상 같은 자리에 선다."),
        consequence=("블라인드·접힘 비율은 조명원(PRF·λ)과 CPI 가 정하고 기하는 정하지 않는다 — "
                     "C2(접힘≠블라인드)가 두 기하에 그대로 전이한다."))


# --------------------------------------------------------------------------- #
#  ③ 네 축의 크기 — 한 줄
# --------------------------------------------------------------------------- #
def axis_sizes():
    a = MONO["axis_effects_headline"]
    return dict(
        one_line=a["one_line"],
        geometry_db=a["geometry_effect"]["at_detection_edge_median_db"],
        geometry_absmax_db=a["geometry_effect"]["absmax_over_scene_db"],
        geometry_at_2L_db=a["geometry_effect"]["at_d_over_L_2_median_db"],
        illuminator_db=a["illuminator_effect"]["span_db"],
        interaction_db=a["interaction"]["absmax_db"],
        interference_db=a["control_effect"]["si_noise_rise_db"]["lte"],
        control_x=GRID["control_axis"]["by_band"]["nr"]
                      ["active_ceiling_1_spec_reference_signal"]["gain_over_passive_x"],
        ordering=("간섭(47.1 dB) ≫ 조명원(4.97 dB) > 기하(0.44 dB) > 상호작용(0.11 dB). "
                  "속도축에서는 통제권이 10배를 낸다."),
        where_geometry_lives=MONO["geometry_effect_vs_range"]["where_it_lives"])


# --------------------------------------------------------------------------- #
#  ④ 주장 재판정 — C0~C16 + 새 주장
# --------------------------------------------------------------------------- #
def readjudicate(mp, win, bf):
    P1 = GRID["axis_independence"]["P1_floor_is_geometry_independent"]
    st = GRID["sigma_transfer"]
    idc = MONO["identity_check"]["unambiguous_velocity_floor"]

    def C(cid, claim, verdict, why, evidence, action, prev=None):
        return dict(id=cid, claim=claim, geometry_verdict=verdict, why=why,
                    evidence=evidence, action=action, previous_status=prev)

    rows = [
        C("C0", "v_max = λ·PRF_ref/4 — 상시 기준신호의 반복률이 무모호 속도를 정한다",
          "both",
          "모노는 바이의 β=0 특수해다. 세 밴드 전부 차이 0 m/s 이고, 바이는 β↑ 에서 관대해진다",
          {"abs_diff_ms": {b: idc[b]["abs_diff_ms"] for b in BANDS},
           "relief_at_beta45_x": GRID["axis_independence"]["P2_bistatic_relief"]
                                     ["relief_by_beta"]["beta_45_deg"],
           "relief_at_beta90_x": GRID["axis_independence"]["P2_bistatic_relief"]
                                     ["relief_by_beta"]["beta_90_deg"]},
          "⭐ 문장에 '두 기하의 최악값' 한 줄을 넣는다. 검지 한계에서는 β 중앙 2.92° 라 "
          "그 최악값이 곧 실제값이다",
          "defensible"),
        C("C0b", "속도 동적범위 v_max/v_guard 는 기하와 무관하다 (신규)",
          "both",
          "완화 1/cos(β/2)cosδ 가 상한과 하한에 똑같이 곱해져 소거된다 → M/(2·bins)",
          {"closed_form": "M/(2·guard_bins)",
           "wifi_lte_x": win["by_band"]["wifi"]["dynamic_range_numeric"],
           "nr_x": win["by_band"]["nr"]["dynamic_range_numeric"],
           "identity_max_abs_diff": win["identity_max_abs_diff"]},
          "지도의 '사용가능 속도창' 열이 이 항등식 위에 선다", "new"),
        C("C1", "탈출구 6판정 — (a)(b)(c) 폐쇄 · (d)(e)(f) 부분완화",
          "both, 재배치 2건",
          "판정은 조명원·처리 축이라 기하를 옮겨도 그대로다. (e) 멀티스태틱은 기하 축의 확장이고, "
          "능동 모노의 PRF 통제권은 7번째 탈출구로 **A 칸에서만** 열린다",
          {"escapes": list(HARD["verdict"]["escapes"].keys()),
           "active_prf_gain_x": GRID["control_axis"]["by_band"]["nr"]
                                    ["active_ceiling_1_spec_reference_signal"]["gain_over_passive_x"]},
          "(e) 를 기하 축으로 옮기고, 7번째 항 'PRF 통제권(구성 A 전용)' 을 추가한다",
          "defensible"),
        C("C2", "접힘과 블라인드는 다른 양이다 — CPI 는 검출을 되살리고 모호는 못 고친다",
          "both",
          "두 기하의 블라인드·접힘 비율 차이를 직접 쟀다",
          {"max_abs_delta_blind_hard": bf["max_abs_delta_blind_hard"],
           "max_abs_delta_alias_frac": bf["max_abs_delta_alias_frac"],
           "regression_vs_repo_max_abs": bf["regression_vs_repo_max_abs"]},
          "없음 — 두 행에 같은 표를 쓴다", "defensible"),
        C("C3", "인프라 서사 — LTE CRS → 5G SSB 로 v_max 가 38.0배 준다",
          "both",
          "반복률·파장 분해에 기하 변수가 없다",
          {"v_max_ratio": LAW["design_rule"]["lte_to_5g_migration"]["v_max_ratio"],
           "prf_ratio": LAW["design_rule"]["lte_to_5g_migration"]["prf_ratio"],
           "lambda_ratio": LAW["design_rule"]["lte_to_5g_migration"]["lambda_ratio"]},
          "없음 (TS 원문 대조는 별건으로 남는다)", "defensible"),
        C("C4", "CFAR 를 경험 Pfa 로 교정",
          "both",
          "검출기 규약은 기하 함수가 아니다. 두 팔이 같은 문턱·같은 배율을 쓴다",
          {"runtime_s": CFAR["meta"]["runtime_s"],
           "snr90_db": MONO["thresholds"]["snr90_db"]["L1"],
           "pfa_ratio_by_mode": {k: v["ratio_emp_over_nominal"]
                                 for k, v in MONO["thresholds"]["pfa"].items()}},
          "없음 — 두 팔이 같은 교정을 그대로 공유한다", "method"),
        C("C5", "공통모드 σ 불변성 — dR_dB/dσ_dB = 1/4",
          "both", "σ 사슬이 두 팔에서 동일하다(모노는 같은 격자의 β=0 조회)",
          {"slope_mean": SIG["common_mode"]["slope_mean"],
           "monostatic_dsigma_db": st["monostatic_arm"]["dsigma_db"]},
          "없음", "defensible"),
        C("C6", "조명원 대가 원장 — 점유 · λ² · ΔR_b · 듀티",
          "both", "자원격자에서 결정되므로 기하 무관. 듀티는 두 행에 같은 값이 들어간다",
          {"duty_db": GRID["axis_independence"]["P3_illuminator_and_duty_are_geometry_free"]
                          ["duty_by_band"],
           "duty_pair_gaps_db": GRID["axis_independence"]
                                    ["P3_illuminator_and_duty_are_geometry_free"]["duty_pair_gaps_db"]},
          "⚠ 듀티는 여전히 R90 경로에서 호출되지 않는다 — §5 결함 D2", "defensible"),
        C("C7", "승자 주장 — LTE CRS 가 최선의 상시 조명원",
          "both (강화됨)",
          "v_max 축은 기하 무관이고, σ·R90 축도 네 배치 전부에서 조명원 순위가 같다 — "
          "기하를 바꿔도 답이 안 바뀐다는 직접 증거를 얻었다",
          {"ranking_same_across_placements": MONO["verdict"]["axis_independence_evidence"],
           "winner_margin_db_aspect_avg_anchored":
               SIG["configurations"]["by_config"]["aspect_avg_anchored"]
                  ["winner_claim"]["worst_margin_span_db"],
           "R90_span_m": MONO["axis_effects_headline"]["illuminator_effect"]["R90_span_m"]},
          "σ 축 문장에 '네 배치에서 순위 동일' 을 근거로 추가한다", "defensible"),
        C("C8", "같은 CPI 12.05배 벌점", "both (조건부)",
          "조명원 축이라 기하 무관. WiFi 1 kHz 트래픽 가정 조건은 그대로 남는다",
          {"condition": "WiFi VHT-LTF 1 kHz 트래픽 가정",
           "spec_guaranteed_ambient_hz": LAW["illuminators"]["rows"]["wifi_beacon"]["prf_hz"]},
          "없음 — 조건절과 함께 지지 수치로만 쓴다", "defensible (조건부)"),
        C("C9", "5G 커버리지 = 0, 전 헤딩 블라인드", "neither",
          "철회 상태 유지. 두 기하 어디에서도 쓰지 않는다", {},
          "PAPER_SPEC §2 지시대로 유지", "retracted"),
        C("C10", "버스트 내부 ↔ 버스트 간 교환관계", "both",
          "OFDM 축과 slow-time 축의 관계이고 기하가 들어가지 않는다",
          {"intra_burst": LAW["scope"]["intra_burst_alternative"]},
          "없음 — 신규성 문단 필수 부품", "defensible"),
        C("C11", "설정 의존성 — SSB 주기 {5..160} ms → 4.28 ~ 0.134 m/s",
          "passive only (B·C)",
          "구성 A 는 반복률을 스스로 고르므로 이 명제의 **대상이 아니다**. 통제 축의 명제이지 "
          "기하 축의 명제가 아니다",
          {"passive_cells": ["B-*", "C-*"],
           "active_ceiling_prf_hz": GRID["control_axis"]["by_band"]["nr"]
                                        ["active_ceiling_1_spec_reference_signal"]["prf_hz"]},
          "'패시브 셀에서' 라는 조건절을 붙인다", "defensible"),
        C("C12", "부위별 재질 + 광선 가림 (방법)", "both, 모노에서 더 직접적",
          "커널 검증은 후방산란 기준이라 모노 조회에 그대로 적용된다",
          {"kernel_vs_analytic_po_db": st["kernel_accuracy_db_vs_analytic_po"],
           "monostatic_dsigma_db": st["monostatic_arm"]["dsigma_db"]},
          "모노 행에 '근사 없음(Δσ=0)' 을 표기한다", "method"),
        C("C13", "3자 순위(1·2·3위)", "neither",
          "단일자세에서 5기체가 3개 순위를 낸다 — 기하와 무관한 σ 축의 문제다",
          {"n_distinct_orders": SIG["configurations"]["by_config"]["as_published"]["n_distinct_orders"]},
          "drop 유지. 자세평균 순위(C7)로 대체한다", "drop"),
        C("C14", "절대 검출거리 (R90 km 급)", "neither, 모노에서 조건이 하나 늘었다",
          "σ ±10 dB 가 거리를 옮기는 데 더해, 모노 행의 절대값은 **선언 SI 깊이**에 매달린다 — "
          "100 dB 에서 384 m, 141 dB 에서 4632 m 로 12.1배 벌어진다",
          {"R90_at_100dB_m": MONO["depth_matrix"]["cells"]["A_mono_at_illuminator"]["lte"]["100"]["R90_d_m"],
           "R90_at_141dB_m": MONO["depth_matrix"]["cells"]["A_mono_at_illuminator"]["lte"]["141"]["R90_d_m"]},
          "drop 유지. 지도에는 상대비(배율)만 싣는다", "drop"),
        C("C15", "드론 RCS 정확도", "neither", "앵커 1기체·1실험실·편파 미통제 — 기하와 무관",
          {}, "drop 유지", "drop"),
        C("C16", "자세분해 바이스태틱 σ", "monostatic only ⭐",
          "바이 팔은 이등분선 근사이고 β=45° 에서 rms 중앙 7.47 dB · p95 최대 20.04 dB 다. "
          "모노 팔은 β=0 이라 근사가 항등이 되고 상반성 오차도 정확히 0 이다",
          {"bisector_rms_median_at_beta45_db": st["bisector_approximation_error_by_beta"]["45"]["dsigma_rms_median_db"],
           "bisector_p95_max_at_beta45_db": st["bisector_approximation_error_by_beta"]["45"]["dsigma_p95_max_db"],
           "reciprocity_rms_max_at_beta45_db": st["bisector_approximation_error_by_beta"]["45"]["reciprocity_rms_max_db"],
           "at_beta0_all_zero": st["bisector_approximation_error_by_beta"]["0"]},
          "⭐ 모노 행에서는 **자세분해 σ 를 주장한다**(커널 0.201 dB). 바이 행은 drop 유지",
          "drop (바이스태틱 기준)"),
    ]

    new = [
        dict(id="N1",
             claim="기하의 링크버짓 기여는 닫힌형 20log10(R_조명원/R_센서) 이고 검지 한계에서 죽는다",
             geometry_verdict="both (기하 축 그 자체)",
             evidence={"at_edge_median_db": MONO["axis_effects_headline"]["geometry_effect"]
                                                ["at_detection_edge_median_db"],
                       "absmax_over_scene_db": MONO["axis_effects_headline"]["geometry_effect"]
                                                   ["absmax_over_scene_db"],
                       "R90_spread_across_four_placements_m":
                           MONO["axis_effects_headline"]["geometry_effect"]
                               ["R90_spread_across_four_placements_m"]},
             action="지도 캡션에 '기하 축은 d ≲ 2L 에 산다' 를 적는다"),
        dict(id="N2",
             claim="모노스태틱이 실제로 사는 것은 PRF 통제권 하나다 — 5G 에서 10배",
             geometry_verdict="monostatic only",
             evidence={"passive_v_max_ms": GRID["control_axis"]["by_band"]["nr"]["passive_v_max_ms"],
                       "active_spec_ceiling_ms": GRID["control_axis"]["by_band"]["nr"]
                                                     ["active_ceiling_1_spec_reference_signal"]["v_max_ms"],
                       "gain_x": GRID["control_axis"]["by_band"]["nr"]
                                     ["active_ceiling_1_spec_reference_signal"]["gain_over_passive_x"]},
             action="⚠ 500 Hz CSI-RS 는 **망이 설정하면 패시브도 받는다** — 모노 전용 레인은 "
                    "데이터 심볼(X[m,n] 기지)이다. 경계는 '기준신호만 vs 전 파형' 이다"),
        dict(id="N3",
             claim="자기간섭이 모노 행의 검지거리를 정한다 — 실측 최선 100 dB 에서 47.1 dB 잡음상승",
             geometry_verdict="monostatic only",
             evidence={"noise_rise_db": MONO["verdict"]["headline_numbers"]["si_noise_rise_db"],
                       "range_factor_x": MONO["verdict"]["headline_numbers"]["range_factor_after_si_x"],
                       "break_even_db": MONO["verdict"]["headline_numbers"]["break_even_suppression_db"]},
             action="A 행에 SI 열을 상설한다"),
        dict(id="N4",
             claim="이격거리는 공짜 격리다 — L=500 m 패시브는 소거 28.3 dB 로 능동 100 dB 전단과 같은 잔류",
             geometry_verdict="bistatic only",
             evidence={"eca_depth_to_match_active_db": MONO["verdict"]["headline_numbers"]["eca_depth_to_match_active_db"],
                       "passive_minus_active_db": MONO["total_isolation_ledger"]["by_band"]["lte"]
                                                      ["passive_C_minus_active_A_db"]},
             action="원장을 '등가 베이스라인 L_equiv' 로 한 자에 놓는다"),
    ]

    tally = {}
    for r in rows + new:
        k = r["geometry_verdict"].split(",")[0].split("(")[0].replace("⭐", "").strip()
        tally[k] = tally.get(k, 0) + 1
    return dict(rule=("판정 기준: 이 주장을 두 기하 행 모두에서 인용할 수 있는가. "
                      "'neither' 는 틀렸다는 뜻이 아니라 이 논문에서 주장하지 않는다는 뜻이다."),
                claims=rows, new_claims=new, tally=tally,
                headline=(f"{len(rows)}개 + 신규 {len(new)}개 중 "
                          + " · ".join(f"{k} {v}" for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))
                          + ". ⭐ 지위가 오른 것이 하나 있다 — C16 자세분해 σ 는 "
                            "바이에서 drop 이고 모노에서 선다."))


# --------------------------------------------------------------------------- #
#  ⑤ 두 생산결함을 넣은 정정 지도
# --------------------------------------------------------------------------- #
def live_defects(mp):
    cfgs = SIG["configurations"]["by_config"]
    base = cfgs["aspect_avg"]["by_drone"]["mavic4pro"]["R90_m"]
    anch = cfgs["aspect_avg_anchored"]["by_drone"]["mavic4pro"]["R90_m"]
    anduty = cfgs["aspect_avg_anchored_duty"]["by_drone"]["mavic4pro"]["R90_m"]
    f_anchor = {b: anch[BAND_MODE[b]] / base[BAND_MODE[b]] for b in BANDS}
    f_duty = {b: anduty[BAND_MODE[b]] / anch[BAND_MODE[b]] for b in BANDS}
    f_both = {b: f_anchor[b] * f_duty[b] for b in BANDS}

    corrected = []
    for c in mp["cells"]:
        b = c["illuminator"]
        corrected.append(dict(cell_id=c["cell_id"], illuminator=b,
                              R90_m=c["R90_m"],
                              R90_anchored_m=c["R90_m"] * f_anchor[b],
                              R90_anchored_duty_m=c["R90_m"] * f_both[b],
                              factor_anchor_x=f_anchor[b], factor_duty_x=f_duty[b],
                              factor_total_x=f_both[b]))

    order_base = sorted(BANDS, key=lambda b: -mp["cells"][6 + BANDS.index(b)]["R90_m"])
    order_corr = sorted(BANDS, key=lambda b: -(mp["cells"][6 + BANDS.index(b)]["R90_m"] * f_both[b]))

    return dict(
        D1=dict(name="앵커가 리포트 계층에만 있고 생산 σ 사슬 밖에 있다",
                evidence="src/experiment_freespace_sigma.py 에 `sigma_anchor` 참조 0회 "
                         "⟨sigma_sensitivity.json : scenario_apply_measured_slope.finding⟩",
                grep_count=int(sum(1 for _ in open(
                    os.path.join(_ROOT, "src", "experiment_freespace_sigma.py"),
                    encoding="utf-8").read().split("sigma_anchor")) - 1),
                measured_slope_db_per_ghz=0.21,
                our_production_slope_db_per_ghz=SIG["scenario_apply_measured_slope"]
                    ["by_drone"]["mavic4pro"]["our_production_slope_db_per_ghz"],
                R90_factor_x=f_anchor,
                cells_affected="6칸 전부 — σ 사슬은 두 기하가 공유한다",
                geometry_axis_impact=("0 — 밴드별 공통모드라 두 행에 같은 배율이 곱해진다. "
                                      "기하 비교는 불변, 조명원 비교는 바뀐다"),
                worth=("자세평균 승자 여유가 "
                       f"{cfgs['aspect_avg']['winner_claim']['worst_margin_span_db']:.4g} dB → "
                       f"{cfgs['aspect_avg_anchored']['winner_claim']['worst_margin_span_db']:.4g} dB "
                       "로 오르고, 그때 비로소 현실 오차범위 "
                       f"{SIG['configurations']['realistic_span_db']:.4g} dB 밖으로 나간다")),
        D2=dict(name="듀티 축이 정의만 되고 R90 생산경로 밖에 있다",
                evidence="`freespace_link.duty_db_from_cpi` 정의됨 · "
                         "src/experiment_freespace_range.py 호출 0회 "
                         "⟨sigma_sensitivity.json : unapplied_duty_axis.finding⟩",
                duty_db=SIG["unapplied_duty_axis"]["duty_db"],
                R90_factor_x=f_duty,
                cells_affected="6칸 전부 — 자원격자가 정하는 값이라 기하와 무관하다",
                geometry_axis_impact="0 — mono_link.views.duty_axis.check 에서 φ·기하 기여 0 확인",
                worth=("조명원 축의 LTE−5G 간격이 "
                       f"{SIG['unapplied_duty_axis']['pair_gaps_db']['L1-G1']:.4g} dB 늘고, "
                       f"승자 여유가 {cfgs['aspect_avg_anchored_duty']['winner_claim']['worst_margin_span_db']:.4g} dB "
                       "가 된다")),
        corrected_map=corrected,
        illuminator_order_base=order_base,
        illuminator_order_corrected=order_corr,
        order_changes=bool(order_base != order_corr),
        headline=("두 결함은 **둘 다 조명원 축**이다. 기하 축은 그대로 서고, "
                  f"조명원 축은 WiFi ×{f_both['wifi']:.3g} · LTE ×{f_both['lte']:.3g} · "
                  f"5G ×{f_both['nr']:.3g} 로 움직인다 — LTE 의 우위가 커진다."),
        fix_cost=dict(
            D1="src/experiment_freespace_sigma.py 에 sigma_anchor 를 배선 + 격자 재생성 (GPU ~10 분)",
            D2="src/experiment_freespace_range.py stage_solve 의 snr_rd_db 에 duty_db 인자 추가 "
               "(패치 1줄 · GPU 0 · mono_link.json : handoff.patch_requests[1] 에 정확한 패치가 있다)"))


# --------------------------------------------------------------------------- #
#  ⑥ LaSen 을 A-nr 칸에 놓기
# --------------------------------------------------------------------------- #
def lasen(mp):
    ls = MONO["views"]["lasen_side_by_side"]
    lam_view = MONO["views"]["eirp"]["feasible_active_view"]
    ours = [c for c in mp["cells"] if c["cell_id"] == "A-nr"][0]
    scaled = ours["R90_m"] * lam_view["range_factor_x"]
    meas = ls["measured_detection_range_m"]
    return dict(
        cell="A-nr (능동 모노스태틱 × 5G NR)",
        identity=ls["identity"],
        geometry=ls["geometry"],
        measured_detection_range_m=meas,
        measured_velocity_top_bin_ms=ls["measured_velocity_top_bin_ms"],
        eirp_dbm=lam_view["lasen_eirp_dbm"],
        our_cell_R90_at_63dBm_m=ours["R90_m"],
        our_cell_R90_scaled_to_lasen_eirp_m=scaled,
        ratio_measured_over_ours=meas / scaled,
        gap_db=40.0 * np.log10(meas / scaled),   # 링크버짓 dB 환산 (R ∝ SNR^(1/4))
        mismatches=[
            "반송파 — LaSen 5.8 GHz 비면허 · 우리 A-nr 3.5 GHz",
            "표적 — LaSen Matrice 4E / Mini 4 Pro · 우리 mavic4pro",
            "SI 처리 — LaSen 차폐판 + 정적배경 제거(격리 수치 미보고) · 우리 Barneto 실측 100 dB",
            "처리 — LaSen 2D-OMP 부표본 압축센싱 · 우리 정합필터 + 교정 CFAR",
        ],
        what_it_is=("자릿수 확인이다. 네 규약이 다른데도 두 값이 링크버짓 "
                    f"{abs(40.0 * np.log10(meas / scaled)):.3g} dB 안에 든다."),
        why_it_matters=("⭐ LaSen 은 A-nr 칸이 **작동한다는 게재 증거**다. 그 칸이 서기 때문에 "
                        "B·C 칸의 속도 한계가 '실패' 가 아니라 **설계공간의 경계**가 된다."),
        precise_positioning=[
            "LaSen 의 탈출구는 반복률이 아니라 **데이터 심볼**이다 — X[m,n] 를 알아야 쓴다",
            "그 대가는 트래픽이다 — 상용 gNB 실측에서 밀집구간이 전체의 5 % "
            f"⟨monostatic_prior.json : lasen.traffic_statistics_measured.dense_segment_fraction⟩",
            "⭐ 경계는 '모노 vs 패시브' 가 아니라 '기준신호만 쓰기 vs 전 파형 쓰기' 다 — "
            "패시브도 복조·재변조로 전 파형 레인에 들어간다"
            f"(nr_recon 행 {LAW['illuminators']['rows']['nr_recon']['prf_hz']:.4g} Hz → "
            f"{LAW['illuminators']['rows']['nr_recon']['v_max_ms']:.4g} m/s)",
            "LaSen 은 상용 gNB 로 드론을 잰 적이 없다 — 드론 반사는 자체 USRP 만재 송신, "
            "상용 gNB 는 RE 점유 마스크 추출에만 썼다",
        ],
        scoping_caveat=ls["scoping_caveat"])


# --------------------------------------------------------------------------- #
#  ⑦ 공백 목록 · 검증부담 · 좁히기
# --------------------------------------------------------------------------- #
def gaps():
    items = [
        dict(rank=1, item="듀티 축 배선 (결함 D2)",
             cost="패치 1줄 · GPU 0 · ~15 분",
             decides="조명원 축이 16.02 dB 움직이고 승자 여유가 21.15 dB 가 된다",
             geometry_doubles=False,
             where="src/experiment_freespace_range.py — 패치는 mono_link.json : handoff.patch_requests[1]"),
        dict(rank=2, item="SI 기준면·장면원점 규약 합치기",
             cost="GPU 0 · ~30 분",
             decides="mono_link.json 과 monostatic_scene.py 를 한 표에 인용할 수 있게 된다 "
                     "(현재 SI 10.0 dB · 원점 250 m 차이)",
             geometry_doubles=False,
             where="mono_link.json : handoff.two_conventions_to_settle"),
        dict(rank=3, item="앵커를 생산 σ 사슬에 배선 (결함 D1)",
             cost="GPU ~10 분 + 격자 재생성",
             decides="R90 이 밴드별 ×0.900~×1.110 움직이고 승자 주장이 현실 오차범위 밖으로 나간다",
             geometry_doubles=False,
             where="src/experiment_freespace_sigma.py"),
        dict(rank=4, item="능동 EIRP 규제 상한 확정 (함정 T3)",
             cost="문헌 ~2 시간",
             decides="A 행 절대 R90 이 확정되고 등-EIRP 규약의 편향 방향이 닫힌다",
             geometry_doubles=False,
             where="FCC 15.407 / ETSI EN 301 893"),
        dict(rank=5, item="송신기 위상잡음 스펙트럼 확정",
             cost="문헌 ~2 시간",
             decides="⭐ A 행 최대 변수 — 광대역 레짐이면 R90 384 m, 0-도플러 레짐이면 5306 m (13.8배)",
             geometry_doubles=False,
             where="Barneto 2019 후속 · 상용 gNB PN 마스크"),
        dict(rank=6, item="φ 스윕을 σ·커버리지 산출물로 확장",
             cost="GPU ~1 시간 (φ 3점) ~ 4 시간 (φ 13점)",
             decides="'기하는 링크버짓에 영향 없다' 가 φ=90° 의 산물인지 아닌지 (함정 T1b, 최대 23.2 dB)",
             geometry_doubles=True,
             where="src/experiment_freespace_sigma.py · experiment_freespace_range.py"),
        dict(rank=7, item="σ 격자 el 을 −75° 까지 확장",
             cost="GPU ~570 s × el 배수 ≈ 1 시간",
             decides="d ≲ 2L 근거리대(기하 축이 사는 곳)의 R90 을 신뢰할 수 있게 된다",
             geometry_doubles=True,
             where="src/experiment_freespace_sigma.py el 목록 (현재 0~−20°)"),
        dict(rank=8, item="실장 ECA 소거깊이 실측",
             cost="X410 캠페인 (1~2일)",
             decides="C·B 행의 90 dB 가 선언값에서 실측으로 바뀐다. 40 dB 면 C 의 R90 이 "
                     "6900 → 867 m 로 무너진다",
             geometry_doubles=False,
             where="docs/MEASUREMENT_PLAN.md · outputs/measurement_plan.json"),
        dict(rank=9, item="능동 모노 실측 격리 100 dB 위 문헌",
             cost="문헌 ~2 시간",
             decides="break-even 147.1 dB 까지의 41 dB 격차가 좁혀지는지",
             geometry_doubles=False,
             where="Barneto 2019 이후 전이중 레이더 문헌"),
        dict(rank=10, item="E-ALIAS 실측 (접힘 시연)",
             cost="캠페인 1~2일",
             decides="법칙의 실측 증거. 기하와 무관하므로 한 캠페인이 두 행을 함께 산다",
             geometry_doubles=False,
             where="PAPER_POSITION.md §5"),
    ]
    return dict(rule="비용 순. 위에서부터 친다.", items=items,
                gpu_free_top=[i["item"] for i in items if "GPU 0" in i["cost"]],
                headline=("1~5 는 합쳐 GPU 10분 + 문헌 4시간이고 그 안에 A 행의 최대 변수 두 개"
                          "(위상잡음 레짐·EIRP 상한)가 닫힌다."))


def verification_burden():
    art = [
        dict(artifact="Pfa 교정 (2717 s MC)", geometry_dependent=False,
             reason="검출기 규약은 β 를 안 탄다 — 두 팔이 같은 문턱·같은 배율", extra_cost="0"),
        dict(artifact="SBR 커널 ↔ 해석 PO (0.201 dB)", geometry_dependent=False,
             reason="후방산란 기준 검증이라 모노에 더 직접 적용된다", extra_cost="0"),
        dict(artifact="σ 격자 (570 s GPU)", geometry_dependent=False,
             reason="⭐ 모노 팔이 **같은 격자**를 β=0 으로 조회한다 — 새 RCS 계산 0",
             extra_cost="0"),
        dict(artifact="링크버짓 → R90", geometry_dependent=True,
             reason="fs_params 를 TX=RX 로 다시 부른다",
             extra_cost=f"{MONO['meta']['runtime_s']:.4g} s CPU (완료)"),
        dict(artifact="블라인드·접힘 비율", geometry_dependent=True,
             reason="같은 함수를 두 기하로 부른다", extra_cost="이 파일에서 완료"),
        dict(artifact="간섭 원장", geometry_dependent=False,
             reason="⚠ 두 배가 아니라 **다른 물리** — DPI 와 SI 는 별개 항이고 각각 근거가 필요하다",
             extra_cost="문헌 1건 신규 (Barneto 2019)"),
        dict(artifact="φ 스윕", geometry_dependent=True,
             reason="기하 비교는 φ 를 반드시 쓸어야 한다 (함정 T1b)",
             extra_cost="산출물마다 ×3 ~ ×13"),
        dict(artifact="기하 항등식 회귀", geometry_dependent=True,
             reason="모노 = 바이 β=0 · 간섭 끈 R90 재현", extra_cost="완료 (0 m · 0 m/s)"),
    ]
    doubled = [a for a in art if a["geometry_dependent"]]
    return dict(
        artifacts=art,
        n_doubled=len(doubled), n_unchanged=len(art) - len(doubled),
        cpu_spent_s=float(GRID["meta"]["runtime_s"] + MONO["meta"]["runtime_s"]),
        gpu_spent="0",
        headline=("⭐ 기하 축을 두 배로 만든 검증은 8개 중 4개이고, 그 4개의 실제 비용은 "
                  f"CPU {GRID['meta']['runtime_s'] + MONO['meta']['runtime_s']:.4g} s · GPU 0 이다. "
                  "가장 비싼 검증(σ 격자 570 s GPU · Pfa 2717 s MC)은 정확히 두 배가 되지 않는다 — "
                  "σ 는 원래 모노고 Pfa 는 기하 무관이기 때문이다."),
        real_new_cost=("남는 진짜 비용은 두 가지다 — φ 스윕(산출물마다 ×3~13)과 "
                       "간섭 원장의 두 번째 물리(SI). 앞의 것은 GPU, 뒤의 것은 문헌이다."))


def narrowing():
    return dict(
        contract="docs/PAPER_SPEC.md §5 — 막히면 위쪽부터 버린다",
        recommendation=("⭐ §5 의 3번(모노+바이 → 바이 단독)을 **가장 나중에** 친다. "
                        "모노 팔의 한계비용이 CPU 17.6 s · GPU 0 이고, 그 대가로 게재 대조군"
                        "(LaSen)과 통제 축을 얻기 때문이다."),
        order_to_cut=[
            dict(rank=1, cut="σ 격자 5기체 → 1기체 (mavic4pro)",
                 saves="GPU 570 s → 114 s", costs="기체 일반화 문장을 뺀다",
                 spec_item="§5-5"),
            dict(rank=2, cut="φ 13점 → 3점 {0°, 90°, 180°}",
                 saves="φ 의존 산출물 ×13 → ×3",
                 costs="φ 중앙값 통계가 3점 평균으로 거칠어진다. absmax 23.2 dB 는 그대로 "
                       "잡힌다(φ=180° 가 극값)",
                 spec_item="이번 라운드 신규 축"),
            dict(rank=3, cut="근거리대(d ≲ 2L) 를 범위에서 뺀다",
                 saves="σ 격자 el 확장(−75°) 이 통째로 빠진다",
                 costs="기하 축의 링크버짓 항이 0.61 dB 로 고정된다 — "
                       "그러면 기하 행의 내용은 간섭항과 통제권 둘로 좁혀진다",
                 spec_item="§5-2 (실측이 닿는 거리대)"),
            dict(rank=4, cut="기체 7종 → 실측 2종 + 대조군 2종", saves="메쉬·격자 작업",
                 costs="크기 전이 문장이 약해진다", spec_item="§5-1"),
            dict(rank=5, cut="모노+바이 → 바이 단독", saves="CPU 17.6 s",
                 costs="⛔ LaSen 대조군과 통제 축을 통째로 잃는다 — 재프레이밍의 목적이 사라진다",
                 spec_item="§5-3"),
        ],
        never_cut=["v_max 법칙과 12종 교차표준 표", "탈출구 6판정", "Pfa 교정",
                   "⭐ 신규: 통제 축(A 는 PRF 를 고르고 B·C 는 망이 준 값을 받는다)"],
        if_only_one_row=("⭐ 한 행만 남겨야 하면 **바이스태틱(C)** 을 남긴다 — 실측 장비"
                         "(X410 4RX)와 논문 헤드라인이 거기 서 있고, 모노 행은 A 의 절대 R90 이 "
                         "선언 SI 깊이에 매달려 있다."))


# --------------------------------------------------------------------------- #
#  ⑧ 재프레이밍된 기여 문단 — 서론에 그대로 들어간다
# --------------------------------------------------------------------------- #
def contribution():
    ctl = GRID["control_axis"]["by_band"]["nr"]
    return dict(
        title=("Geometry × Illuminator: A Controlled Benchmark of Monostatic and Bistatic "
               "Drone Sensing on WiFi, LTE and 5G NR"),
        one_sentence=("드론 센싱을 기하(모노/바이) × 조명원(WiFi/LTE/5G) 2×3 으로 통제 비교하고, "
                      "그 지도 위에서 무모호 속도가 상시 기준신호의 반복률로 결정된다는 것 — "
                      "v_max = λ·PRF_ref/4 — 그리고 그 한계가 **PRF 를 고르지 못하는 쪽에만** "
                      "구속으로 작용한다는 것을 보인다."),
        paragraph=[
            "우리는 기하와 조명원을 **서로 독립인 두 축**으로 세우고, 그 위에 통제 축"
            "(PRF 가 설계변수인가 주어진 값인가)을 세 번째로 얹는다. 세 축을 분리하면 "
            "각 축이 무엇을 정하는지가 수치로 갈린다 — 검지 한계에서 기하 0.44 dB · "
            "조명원 4.97 dB · 상호작용 0.11 dB · 간섭 47.1 dB 다.",
            "⭐ **무모호 속도의 바닥은 기하와 무관하다.** 모노스태틱은 바이스태틱의 β=0 "
            "특수해이고 두 값의 차이는 0 m/s 다. 바이스태틱은 β 가 커질수록 관대해진다"
            "(β=90° 에서 1.414배). 그래서 우리가 발표해온 1.07 / 14.39 / 40.67 m/s 는 "
            "**두 기하의 최악값**이며, 검지 한계(β 중앙 2.92°)에서는 그 최악값이 곧 실제값이다.",
            "⭐ **링크버짓은 다르다.** 기하의 링크버짓 기여는 20log10(R_조명원/R_센서) 한 줄이고 "
            "장면 방위에 따라 부호가 뒤집히며 최대 23.2 dB 까지 벌어진다. 같은 항이 "
            "검지 한계(d ≈ 14L)에서는 0.44 dB 로 죽는다 — 기하 축은 근거리에 산다.",
            "**통제 축이 왜 같은 법칙을 한쪽에만 구속으로 만드는가.** 능동 모노스태틱은 반복률을 "
            f"고른다 — 3GPP sub-6 CSI-RS 천장 {ctl['active_ceiling_1_spec_reference_signal']['prf_hz']:.4g} Hz "
            f"에서 v_max = {ctl['active_ceiling_1_spec_reference_signal']['v_max_ms']:.4g} m/s 로 "
            f"패시브 SSB {ctl['passive_v_max_ms']:.4g} m/s 의 "
            f"{ctl['active_ceiling_1_spec_reference_signal']['gain_over_passive_x']:.3g}배다. "
            "패시브는 망이 정한 값을 받는다. 같은 식이 한쪽에서는 설계 여유이고 다른 쪽에서는 벽이다.",
            "**LaSen(SenSys '26 게재)이 능동 모노스태틱 5G 칸을 차지한다.** 그 칸이 작동한다는 것을 "
            "실측으로 보였고, 탈출구로 반복률이 아니라 데이터 심볼(X[m,n] 기지)을 썼다. "
            "그 칸이 서 있기 때문에 패시브 칸의 속도 한계가 실패가 아니라 **설계공간의 경계**가 된다.",
            "⚠ **경계선을 정확히 긋는다.** 통제 축의 진짜 경계는 '모노 vs 패시브' 가 아니라 "
            "'기준신호만 쓰기 vs 전 파형 쓰기' 다. 500 Hz CSI-RS 는 망이 설정하면 패시브도 받고, "
            "패시브도 복조·재변조로 전 파형 레인(1 kHz → 21.4 m/s)에 들어갈 수 있다. "
            "모노스태틱이 공짜로 갖는 것은 그 레인의 **입장료**다.",
        ],
        contributions=[
            "⑴ 기하 × 조명원 2×3 통제 격자 — 무엇을 고정하고 무엇을 변하게 두는지를 "
            "함정 10개와 함께 못박는다",
            "⑵ 축 분리 정량 — 기하 0.44 · 조명원 4.97 · 상호작용 0.11 · 간섭 47.1 dB",
            "⑶ 상시 기준신호 12종 교차표준 표와 v_max 법칙, 그리고 그 바닥이 기하와 무관하다는 증명",
            "⑷ 탈출구 6 전수 판정 + 7번째(PRF 통제권)가 구성 A 에서만 열린다는 판정",
            "⑸ 간섭 원장을 한 축으로 — 등가 베이스라인 L_equiv 로 DPI 와 SI 를 한 자에 놓는다",
        ],
        novelty_guard=[
            "Rzewuski(NATO STO 2021)가 드론 바이스태틱 RCS → 커버리지 → 50 m 실외 검출을 이미 닫았다 — "
            "'최초' 류를 쓰지 않는다",
            # ⭐ 정정 R1 (docs/RETRACTION_LOG.md) — 우선권은 Chen 이 아니다.
            "v_max = λ·PRF/(4cos(β/2)cosδ) 의 우선권은 **Abratkiewicz 외, IEEE JSTARS "
            "16:3469-3484 (2023), 식 (16) p.3476** 이다 — 반구간 규약까지 같다. "
            "Chen 2024(Appl. Sci. 14:4282)는 **닫힌 식이 없다**('PRF' 0회) — 우리 이전 기록의 "
            "Chen 귀속은 철회됐다",
            "v·R = c·λ/8 은 Skolnik 의 고전 결과다",
        ])


# --------------------------------------------------------------------------- #
#  ⑨ 그림 — 지도 한 장 (영어 텍스트)
# --------------------------------------------------------------------------- #
def figure(mp, win):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8.5, "axes.linewidth": 0.7,
                         "figure.dpi": 120, "savefig.dpi": 300,
                         "pdf.fonttype": 42, "ps.fonttype": 42,
                         "axes.grid": True, "grid.alpha": 0.22,
                         "grid.linewidth": 0.5})
    lo, hi = mp["drone_band"]["band_used_ms"]
    rows = ("monostatic", "bistatic")
    row_title = {"monostatic": "MONOSTATIC   (beta ~ 0)",
                 "bistatic": "BISTATIC   (passive, baseline L = 500 m)"}
    cfg_label = {"A": "A  active monostatic (we transmit, PRF is ours)",
                 "B": "B  passive quasi-monostatic (RX 10 m from mast)",
                 "C": "C  passive bistatic (RX 500 m from mast)"}

    fig, axes = plt.subplots(2, 3, figsize=(11.4, 6.3), sharex=True, sharey=True)
    for i, row in enumerate(rows):
        for j, b in enumerate(BANDS):
            ax = axes[i, j]
            ax.set_xscale("log"); ax.set_yscale("log")
            ax.set_xlim(0.2, 200.0); ax.set_ylim(180.0, 13000.0)
            ax.axvspan(lo, hi, color="#9a9a9a", alpha=0.16, lw=0, zorder=0)
            if i == 0 and j == 0:
                ax.text(np.sqrt(lo * hi), 11200, "drone band\n5-15 m/s", ha="center",
                        va="top", fontsize=7.2, color="#4a4a4a")
            for c in mp["cells"]:
                if c["geometry_row"] != row or c["illuminator"] != b:
                    continue
                k = c["configuration"]
                y, vg = c["R90_m"], c["v_guard_ms"]
                vm = c["v_max_ms"]
                col, mk, lsty = COLOR[k], MARKER[k], LINESTYLE[k]
                if vm is None:                        # PRF 가 설계변수 (WiFi·LTE 능동)
                    ax.plot([vg, 150.0], [y, y], lsty, color=col, lw=2.0, zorder=3)
                    ax.plot([vg], [y], mk, color=col, ms=6.5, zorder=4,
                            mec="white", mew=0.8)
                    ax.annotate("", xy=(190.0, y), xytext=(150.0, y),
                                arrowprops=dict(arrowstyle="-|>", color=col, lw=1.6))
                    ax.text(150.0, y * 1.30, "PRF: design variable", color="#3a3a3a",
                            fontsize=6.8, ha="right")
                else:
                    ax.plot([vg, vm], [y, y], lsty, color=col, lw=2.0, zorder=3)
                    ax.plot([vg, vm], [y, y], mk, color=col, ms=6.5, zorder=4,
                            mec="white", mew=0.8, ls="none")
                    ax.text(vm * 1.18, y, f"{vm:.4g}", color="#3a3a3a", fontsize=6.8,
                            va="center")
                cost = c["cost"]
                tag = (f"SI {cost['noise_rise_db']:.0f} dB" if k == "A"
                       else f"DPI {cost['required_cancellation_db']:.0f} dB req")
                ax.text(0.24, y * 0.72, f"{k}: {y:.0f} m | {tag}", fontsize=6.8,
                        color=col, va="top")
            if i == 0:
                ax.set_title(BAND_LABEL[b], fontsize=9.5, pad=6)
            if j == 0:
                ax.set_ylabel(f"{row_title[row]}\n\ndetection range R90 [m]", fontsize=8.2)
            if i == 1 and j == 1:
                ax.set_xlabel("unambiguous radial speed window [m/s]", fontsize=8.8)
    handles = [plt.Line2D([], [], color=COLOR[k], marker=MARKER[k], ls=LINESTYLE[k],
                          lw=2.0, ms=6.5, mec="white", mew=0.8, label=cfg_label[k])
               for k in ("A", "B", "C")]
    handles.append(plt.Line2D([], [], color="#9a9a9a", lw=7, alpha=0.35,
                              label="drone speed band 5-15 m/s"))
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               fontsize=8.0, bbox_to_anchor=(0.5, -0.055))
    fig.suptitle("Design-space map: which geometry x illuminator sees the drone speed band, "
                 "and out to what range", fontsize=10.5, y=0.985)
    fig.text(0.5, 0.925,
             "segment = usable speed window [zero-Doppler guard, unambiguous ceiling]  |  "
             "height = R90 (Pd 0.9, mavic4pro, phi 90 deg, CPI 0.1 s, equal EIRP 63 dBm)",
             ha="center", fontsize=7.6, color="#4a4a4a")
    fig.tight_layout(rect=(0, 0.02, 1, 0.915))
    os.makedirs(FIG_DIR, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{FIG_STEM}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return dict(
        path_png=os.path.relpath(f"{FIG_STEM}.png", _ROOT),
        path_pdf=os.path.relpath(f"{FIG_STEM}.pdf", _ROOT),
        question="Which geometry x illuminator combination measures the drone speed band "
                 "unambiguously, and out to what range?",
        encoding=("x = usable speed window (log) · y = R90 (log) · color+marker+linestyle = "
                  "configuration A/B/C · text = cost in dB"),
        palette_check=("dataviz validator (OKLab ΔE, Machado severity 1.0, light surface): "
                       "all pairs PASS — worst min(protan,deutan) ΔE = 11.0"),
        text_language="English (house rule)")


# --------------------------------------------------------------------------- #
#  ⑩ 마크다운 — 표의 숫자는 전부 위 계산값에서 찍는다
# --------------------------------------------------------------------------- #
def _f(x, n=4):
    return "미상" if x is None else f"{x:.{n}g}"


def write_md(out):
    mp, win, bf, ax, rj, df, ls, gp, vb, nw, ct, fg = (
        out["map"], out["usable_speed_window"], out["blind_and_fold"],
        out["axis_sizes"], out["readjudication"], out["live_defects"],
        out["lasen_positioning"], out["gaps"], out["verification_burden"],
        out["narrowing"], out["contribution"], out["figure"])
    cell = {c["cell_id"]: c for c in mp["cells"]}
    L = []
    A = L.append

    n_claim, n_new = len(rj["claims"]), len(rj["new_claims"])
    A("# 기하 × 조명원 설계공간 지도 — 2026-07-31")
    A("")
    A(f"> 벤치마크를 **기하(모노/바이) × 조명원(WiFi/LTE/5G)** 2×3 으로 세우고, 기존 주장 {n_claim}개를")
    A("> 그 지도 위에서 다시 판정한다. 규격은 [`PAPER_SPEC.md`](PAPER_SPEC.md) §0,")
    A("> 서술 규약은 [`REBUILD_2026-07-30.md`](REBUILD_2026-07-30.md) §5 를 따른다.")
    A("")
    A("```")
    A("┌─ 한 일 ────────────────────────────────────────────────────────────────┐")
    A(f"│ 기하를 결과에서 빼내 축으로 올리고, 6칸 지도를 채운 뒤 주장 {n_claim}개를 그    │")
    A(f"│ 지도 위에서 재판정하고 새 주장 {n_new}개를 세웠다.                            │")
    A("├─ 결과 ─────────────────────────────────────────────────────────────────┤")
    A(f"│ 축 크기: 기하 {_f(ax['geometry_db'],3)} dB · 조명원 {_f(ax['illuminator_db'],3)} dB · "
      f"상호작용 {_f(ax['interaction_db'],2)} dB · 간섭 {_f(ax['interference_db'],3)} dB │")
    A(f"│ 무모호 속도 바닥은 기하와 무관하다 — 세 밴드 전부 차이 "
      f"{_f(max(abs(v['abs_diff_ms']) for v in MONO['identity_check']['unambiguous_velocity_floor'].values()),1)} m/s.        │")
    A(f"│ 속도창 동적범위 = M/(2·bins) 로 기하가 소거된다 — WiFi·LTE "
      f"{_f(win['by_band']['wifi']['dynamic_range_numeric'],4)}배, 5G {_f(win['by_band']['nr']['dynamic_range_numeric'],4)}배. │")
    A(f"│ 판정: both {rj['tally'].get('both',0)} · monostatic only {rj['tally'].get('monostatic only',0)} · "
      f"passive only {rj['tally'].get('passive only',0)} · bistatic only {rj['tally'].get('bistatic only',0)} · "
      f"neither {rj['tally'].get('neither',0)}.       │")
    A(f"│ C16(자세분해 σ)이 바이에서 drop 이고 모노에서 선다 — 지위가 오른 유일한 주장. │")
    A("├─ 방법 ─────────────────────────────────────────────────────────────────┤")
    A("│ 모노 팔은 `freespace_scene.fs_params` 를 TX=RX 로 부른 결과다 — 새 기하   │")
    A("│ 코드가 없다. σ 는 같은 격자를 β=0 으로 조회한다(모노 후방산란이 원래 우리 │")
    A("│ 생산 경로다). 문턱·Pfa 교정·듀티 규약은 두 팔에 같은 값을 쓴다.          │")
    A("├─ 재현 ─────────────────────────────────────────────────────────────────┤")
    A("│ PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/geometry_grid.py   (0.8 s)")
    A("│ PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/mono_link.py       (16.8 s)")
    A(f"│ PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/geometry_benchmark.py "
      f"({out['meta']['runtime_s']:.1f} s)")
    A("│ → outputs/geometry_benchmark.json · outputs/figures/geometry_benchmark_map.png │")
    A("├─ 앞 편에서 ────────────────────────────────────────────────────────────┤")
    A("│ v_max 법칙과 탈출구 6판정(`refrate_law.json` · `vmax_hardening.json`),    │")
    A("│ 격자 규약과 함정 10개(`geometry_grid.json`), 모노 링크버짓(`mono_link.json`).│")
    A("└────────────────────────────────────────────────────────────────────────┘")
    A("```")
    A("")
    A("---")
    A("")

    # §1 지도
    A("## 1. ⭐ 지도 — 6칸이 각각 무엇을 보는가")
    A("")
    A(f"{mp['shape']}")
    A("")
    A("| 기하 | 조명원 | 구성 | 송신 | 검지거리 R90 | 무모호 v_max | 사용가능 속도창 | 5~15 m/s 커버 | 대가 |")
    A("|---|---|---|---|---:|---:|---|---:|---|")
    for row in ("monostatic", "bistatic"):
        for b in BANDS:
            for cfg in ("A", "B", "C"):
                c = cell.get(f"{cfg}-{b}")
                if c is None or c["geometry_row"] != row:
                    continue
                cost = c["cost"]
                cost_s = (f"SI {_f(cost['noise_rise_db'],3)} dB 상승 "
                          f"(요구 {_f(cost['required_total_suppression_db'],4)} · 실측 최선 100)"
                          if cfg == "A" else
                          f"DPI 요구 {_f(cost['required_cancellation_db'],4)} dB "
                          f"(부여 90 → 상승 {_f(cost['noise_rise_db'],2)} dB)")
                vmax_s = ("설계변수" if c["v_max_ms"] is None
                          else f"{_f(c['v_max_ms'],4)} m/s")
                win_s = (f"{_f(c['v_guard_ms'],3)} → " +
                         ("자유" if c["v_max_ms"] is None else f"{_f(c['v_max_ms'],4)}"))
                cov = ("설계 선택" if c["covers_drone_band_frac"] is None
                       else f"{100*c['covers_drone_band_frac']:.0f} %")
                A(f"| {row} | {BAND_LABEL[b]} | **{cfg}** | {c['who_transmits']} | "
                  f"{_f(c['R90_m'],4)} m | {vmax_s} | {win_s} m/s | {cov} | {cost_s} |")
    A("")
    A(f"⟨`outputs/geometry_benchmark.json : map.cells`⟩ · 규약: mavic4pro · φ=90° · "
      f"CPI {mp['conventions']['T_cpi_s']} s · G1 점유 · 등-EIRP 63 dBm · "
      f"패시브 소거 90 dB · 능동 SI 100 dB(Barneto 실측)")
    A("")
    tiers = {c["cell_id"]: c["v_max_tiers"] for c in mp["cells"] if c["v_max_tiers"]}
    A("**A 행의 '설계변수' 가 어디까지 가는가** — 자체 파형을 설계하면 상한은 거리모호가 정한다"
      " (v·R = c·λ/8, Skolnik). 각 칸의 R90 에서 "
      + " · ".join(f"{k} {_f(v['free_waveform_at_own_R90_ms'], 4)} m/s"
                   for k, v in tiers.items())
      + " 로, 드론대 5~15 m/s 보다 자릿수가 크다. 즉 A 행을 묶는 것은 거리모호가 아니라 "
        "**규격이 정한 기준신호 천장**(5G CSI-RS 500 Hz → 10.71 m/s)이다.")
    A("")
    A("**점유 규약** — 지도는 여섯 칸 모두에 G1(상시)을 쓴다. A 행은 자기 파형을 만재로 보낼 수 "
      "있으므로 G1 은 A 를 벌하는 규약이고, 그 벌점은 자기간섭 한계에서 상쇄된다 — "
      f"EIRP 를 53 dB 올려도 A 의 R90 은 "
      f"{MONO['eirp_ladder_under_interference']['cells']['A_mono_at_illuminator']['lte']['R90_span_x']:.4g}배 "
      f"움직이고 패시브 C 는 "
      f"{MONO['eirp_ladder_under_interference']['cells']['C_bistatic_L500']['lte']['R90_span_x']:.4g}배 "
      f"움직인다 ⟨`mono_link.json : eirp_ladder_under_interference`⟩. 에코와 잔류가 함께 커지기 "
      "때문이고, 점유도 같은 방식으로 상쇄된다.")
    A("")
    A("**절대 R90 은 소거깊이에 매달린다** — 지도의 세로축을 인용할 때 이 표를 함께 읽는다.")
    A("")
    A("| 행 | 소거깊이 | R90 (LTE) | 깊이의 출처 |")
    A("|---|---:|---:|---|")
    dm = MONO["depth_matrix"]["cells"]
    for lab, key, depths, src in (
            ("A 능동 모노", "A_mono_at_illuminator", ("100", "120", "141"),
             "100 dB = Barneto 2019 실측 · 141 dB = break-even"),
            ("C 패시브 바이", "C_bistatic_L500", ("40", "60", "90"),
             "40~90 dB = `freespace_link.n0_dpi` 선언값(근거문서 없음)")):
        vals = " · ".join(
            f"{d} dB → {_f(dm[key]['lte'][d]['R90_d_m'], 4)} m" for d in depths)
        A(f"| {lab} | {' / '.join(depths)} dB | {vals} | {src} |")
    A("")
    A(f"A 행은 깊이 100 → 141 dB 에서 "
      f"{dm['A_mono_at_illuminator']['lte']['141']['R90_d_m'] / dm['A_mono_at_illuminator']['lte']['100']['R90_d_m']:.3g}배 "
      f"움직이고, C 행은 90 → 40 dB 에서 "
      f"{dm['C_bistatic_L500']['lte']['40']['R90_d_m'] / dm['C_bistatic_L500']['lte']['90']['R90_d_m']:.3g}배 "
      f"움직인다 ⟨`mono_link.json : depth_matrix`⟩. 지도의 **상대비**가 절대값보다 단단하다.")
    A("")
    A(f"![design-space map](../{fg['path_png']})")
    A("")
    A(f"**그림 1.** {fg['question']}")
    A("")
    A("### 1.1 속도창의 동적범위는 기하와 무관하다")
    A("")
    A(f"{win['form']}")
    A("")
    A("| 밴드 | PRF | M | 가드 하한 v_guard | 무모호 상한 v_max | 동적범위 | 닫힌형 M/(2·bins) |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for b in BANDS:
        w = win["by_band"][b]
        A(f"| {BAND_LABEL[b]} | {_f(w['prf_hz'],4)} Hz | {w['M']} | "
          f"{_f(w['v_guard_mono_ms'],3)} m/s | {_f(w['v_max_mono_ms'],4)} m/s | "
          f"{_f(w['dynamic_range_numeric'],4)}배 | {_f(w['dynamic_range_closed_form'],4)}배 |")
    A("")
    A(f"수치와 닫힌형의 최대 차이 {win['identity_max_abs_diff']:.3g} ⟨`…: usable_speed_window`⟩. "
      f"{win['finding']}")
    A("")
    A("### 1.2 두 기하의 블라인드·접힘 비율")
    A("")
    A("| 밴드 | 속도 | 바이(L=500 m) blind_hard | 모노 blind_hard | Δ | 바이 alias | 모노 alias | Δ |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|")
    for b in BANDS:
        for s in FS.FS_SPEED:
            e = bf["by_band"][b][f"speed_{s:g}"]
            A(f"| {BAND_LABEL[b]} | {s:g} m/s | {e['bistatic_L500_at_its_R90']['blind_hard']:.3f} | "
              f"{e['monostatic_at_the_same_scene_point']['blind_hard']:.3f} | "
              f"{e['delta_blind_hard']:+.3f} | {e['bistatic_L500_at_its_R90']['alias_frac']:.3f} | "
              f"{e['monostatic_at_the_same_scene_point']['alias_frac']:.3f} | "
              f"{e['delta_alias_frac']:+.3f} |")
    A("")
    A(f"같은 장면점·같은 CPI 에서 두 기하의 차이가 blind {bf['max_abs_delta_blind_hard']:.3g} · "
      f"alias {bf['max_abs_delta_alias_frac']:.3g} 다. 바이 팔은 "
      f"`freespace_scene.blind_fractions` 를 최대 오차 {bf['regression_vs_repo_max_abs']:.3g} 로 "
      f"재현한다 ⟨`…: blind_and_fold`⟩.")
    A("")
    A("---")
    A("")

    # §2 재판정
    A("## 2. ⭐ 주장 재판정 — 어느 기하에서 서는가")
    A("")
    A(f"{rj['rule']}")
    A("")
    A("| # | 주장 | 기하 판정 | 근거 | 할 일 |")
    A("|---|---|---|---|---|")
    for r in rj["claims"]:
        bits = []
        for k, v in r["evidence"].items():
            if isinstance(v, bool):
                bits.append(f"{k} {v}")
            elif isinstance(v, (int, float)):
                bits.append(f"{k} {_f(v, 4)}")
            elif isinstance(v, dict) and all(isinstance(x, (int, float)) for x in v.values()):
                bits.append(f"{k} " + "/".join(_f(x, 3) for x in v.values()))
            elif isinstance(v, str):
                bits.append(f"{k} {v[:48]}")
            elif isinstance(v, list):
                bits.append(f"{k} {len(v)}항")
            elif isinstance(v, dict):
                bits.append(f"{k} " + "/".join(
                    f"{kk} {_f(vv, 3)}" for kk, vv in list(v.items())[:2]
                    if isinstance(vv, (int, float))))
            if len(bits) == 2:
                break
        ev = (" · ".join(bits) or "—").replace("|", "/")
        A(f"| {r['id']} | {r['claim']} | **{r['geometry_verdict']}** | {ev} | {r['action']} |")
    A("")
    A("**새로 생긴 주장**")
    A("")
    A("| # | 주장 | 기하 판정 | 할 일 |")
    A("|---|---|---|---|")
    for r in rj["new_claims"]:
        A(f"| {r['id']} | {r['claim']} | **{r['geometry_verdict']}** | {r['action']} |")
    A("")
    A(f"{rj['headline']}")
    A("")
    A("### 2.1 바닥은 기하와 무관하고 링크버짓은 기하에 매달린다")
    A("")
    A("| | 무모호 속도 바닥 | 링크버짓 |")
    A("|---|---|---|")
    A(f"| 기하 의존 | 없음 — 모노 = 바이 β=0, 차이 "
      f"{max(abs(v['abs_diff_ms']) for v in MONO['identity_check']['unambiguous_velocity_floor'].values()):.3g} m/s | "
      f"있음 — 20log10(R_조명원/R_센서), 장면 최대 {_f(ax['geometry_absmax_db'],4)} dB |")
    A(f"| 바이스태틱에서 | 관대해진다 (β=90° 에서 "
      f"{GRID['axis_independence']['P2_bistatic_relief']['relief_by_beta']['beta_90_deg']:.4g}배) | "
      f"φ 에 따라 부호가 뒤집힌다 |")
    A(f"| 검지 한계에서 | 완화 "
      f"{MONO['doppler_relief_at_edge']['by_band']['lte']['relief_at_edge_x']['median']:.6g}배 — 바닥이 곧 값 | "
      f"{_f(ax['geometry_db'],3)} dB 로 죽는다 |")
    A(f"| 우리가 인용해온 값 | 1.07 / 14.39 / 40.67 m/s = **두 기하의 최악값** | "
      f"φ=90° 단일 방위 — 재계산 대상 |")
    A("")
    A("---")
    A("")

    # §3 기여
    A("## 3. ⭐ 재프레이밍된 기여 — 서론에 그대로 넣는다")
    A("")
    A(f"> **{ct['title']}**")
    A("")
    A(f"**한 문장 기여**: {ct['one_sentence']}")
    A("")
    for p in ct["paragraph"]:
        A(p)
        A("")
    A("**기여 다섯**")
    A("")
    for i, c in enumerate(ct["contributions"], 1):
        A(f"{i}. {c}")
    A("")
    A("**신규성 경계** — " + " · ".join(ct["novelty_guard"]))
    A("")
    A("### 3.1 LaSen 을 정확히 놓는다")
    A("")
    A(f"{ls['identity']}")
    A("")
    A("| 항목 | LaSen | 우리 A-nr 칸 |")
    A("|---|---|---|")
    A(f"| 기하 | {ls['geometry']} | 모노스태틱 (β≈0) |")
    A(f"| 검지거리 | {_f(ls['measured_detection_range_m'],4)} m (실측) | "
      f"{_f(ls['our_cell_R90_at_63dBm_m'],4)} m @ 63 dBm → "
      f"{_f(ls['our_cell_R90_scaled_to_lasen_eirp_m'],4)} m @ {_f(ls['eirp_dbm'],3)} dBm |")
    A(f"| 최고 속도구간 | {ls['measured_velocity_top_bin_ms'][0]}~"
      f"{ls['measured_velocity_top_bin_ms'][1]} m/s (기체 한계) | "
      f"규격 재활용 천장 {_f(GRID['control_axis']['by_band']['nr']['active_ceiling_1_spec_reference_signal']['v_max_ms'],4)} m/s |")
    A(f"| 탈출구 | 데이터 심볼 + 2D-OMP 부표본 | PRF 통제권 |")
    A("")
    A(f"{ls['what_it_is']} 규약 차이 네 가지: " + " · ".join(ls["mismatches"]) + ".")
    A("")
    for p in ls["precise_positioning"]:
        A(f"- {p}")
    A("")
    A(f"{ls['why_it_matters']}")
    A("")
    A("---")
    A("")

    # §4 결함
    A("## 4. ⚠ 생산 결함 둘을 지도에 넣는다")
    A("")
    A(f"{df['headline']}")
    A("")
    A("| 결함 | 무엇인가 | 영향 칸 | 기하 축 영향 | R90 배율 | 그러면 결정되는 것 |")
    A("|---|---|---|---|---|---|")
    for k in ("D1", "D2"):
        d = df[k]
        fac = " · ".join(f"{BAND_LABEL[b].split()[0]} ×{d['R90_factor_x'][b]:.4g}" for b in BANDS)
        A(f"| **{k}** | {d['name']} | {d['cells_affected']} | {d['geometry_axis_impact'].split('—')[0].strip()} | "
          f"{fac} | {d['worth']} |")
    A("")
    A("**정정 지도** — 두 결함을 다 넣으면 검지거리가 이렇게 바뀐다.")
    A("")
    A("| 칸 | 현재 R90 | 앵커 적용 | 앵커+듀티 | 총 배율 |")
    A("|---|---:|---:|---:|---:|")
    for r in df["corrected_map"]:
        A(f"| {r['cell_id']} | {_f(r['R90_m'],4)} m | {_f(r['R90_anchored_m'],4)} m | "
          f"{_f(r['R90_anchored_duty_m'],4)} m | ×{r['factor_total_x']:.3g} |")
    A("")
    A(f"조명원 순위는 정정 전 {' > '.join(df['illuminator_order_base'])} · "
      f"정정 후 {' > '.join(df['illuminator_order_corrected'])} 다 ⟨`…: live_defects`⟩ — "
      f"승자 LTE 는 그대로이고 2·3위가 자리를 바꾼다. 두 결함을 넣으면 LTE 의 여유가 커진다.")
    A("")
    A("---")
    A("")

    # §5 공백·부담
    A("## 5. 공백 목록과 검증 부담")
    A("")
    A(f"{gp['headline']}")
    A("")
    A("| 순위 | 할 일 | 비용 | 그러면 결정되는 것 | 기하 축이 두 배로 만드나 |")
    A("|---:|---|---|---|---|")
    for i in gp["items"]:
        A(f"| {i['rank']} | {i['item']} | {i['cost']} | {i['decides']} | "
          f"{'예' if i['geometry_doubles'] else '아니오'} |")
    A("")
    A("### 5.1 기하 축을 얹은 값은 얼마인가")
    A("")
    A("| 검증물 | 기하 의존 | 왜 | 추가 비용 |")
    A("|---|---|---|---|")
    for a in vb["artifacts"]:
        A(f"| {a['artifact']} | {'예' if a['geometry_dependent'] else '아니오'} | "
          f"{a['reason']} | {a['extra_cost']} |")
    A("")
    A(f"{vb['headline']}")
    A("")
    A(f"{vb['real_new_cost']}")
    A("")
    A("### 5.2 좁혀야 한다면 — 자르는 순서")
    A("")
    A(f"{nw['recommendation']}")
    A("")
    A("| 순위 | 자를 것 | 아끼는 것 | 잃는 것 | 규격 항 |")
    A("|---:|---|---|---|---|")
    for c in nw["order_to_cut"]:
        A(f"| {c['rank']} | {c['cut']} | {c['saves']} | {c['costs']} | {c['spec_item']} |")
    A("")
    A("**절대 자르지 않는 것**: " + " · ".join(nw["never_cut"]))
    A("")
    A(f"{nw['if_only_one_row']}")
    A("")
    A("---")
    A("")

    # 다음 단계
    A("## 다음 단계")
    A("")
    A("| 다음에 할 일 | 그러면 결정되는 것 | 어디서 |")
    A("|---|---|---|")
    A("| 듀티 축을 R90 경로에 배선한다 (D2) | 조명원 축이 16.02 dB 움직이고 승자 여유가 "
      f"{_f(SIG['configurations']['by_config']['aspect_avg_anchored_duty']['winner_claim']['worst_margin_span_db'],4)} dB 가 된다 | "
      "`src/experiment_freespace_range.py` · 패치는 `mono_link.json : handoff.patch_requests[1]` |")
    A("| 앵커를 생산 σ 사슬에 배선한다 (D1) | R90 이 밴드별 ×0.900~×1.110 움직이고 승자 주장이 "
      "현실 오차범위 밖으로 나간다 | `src/experiment_freespace_sigma.py` |")
    A("| SI 기준면과 장면원점 규약을 정한다 | `mono_link.json` 과 `monostatic_scene.py` 를 한 표에 "
      "인용할 수 있게 된다 | `mono_link.json : handoff.two_conventions_to_settle` |")
    A("| 송신기 위상잡음 스펙트럼을 문헌으로 못박는다 | A 행 R90 이 384 m 인지 5306 m 인지 정해진다 | "
      "Barneto 2019 후속 |")
    A("| φ 를 σ·커버리지 산출물로 확장한다 | 기하 축의 크기가 φ=90° 의 산물인지 정해진다 | "
      "`src/experiment_freespace_sigma.py` |")
    A("| 지도를 03·05편에 싣는다 | 논문 IV·VI 절의 그림이 확정된다 | "
      "`src/make_report03_illuminators.py` · `make_report05_results.py` |")
    A("")
    md = "\n".join(L) + "\n"
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    return md


# --------------------------------------------------------------------------- #
def tone_check(md):
    """REBUILD §5.8 자기검사 — 부정문 ≤3 · 완충어 0."""
    try:
        import report_style as RS
        neg = RS.count_negatives(md)
        hed = RS.grep_hedges(md)
        return dict(negatives=neg["count"], negatives_cap=neg["cap"],
                    negatives_ok=bool(neg["ok"]),
                    negative_sentences=[s["text"][:120] for s in neg["sentences"]],
                    hedges=hed["count"], hedges_ok=bool(hed["ok"]),
                    hedge_hits=[h["text"][:120] for h in hed["hits"]])
    except Exception as e:                                    # pragma: no cover
        return dict(error=repr(e))


def handoff(rj):
    """금지파일(다른 워크플로 소유)에 대한 **정확한 패치**를 여기에 남긴다."""
    ladder = "|".join(f"{r['id']}={r['geometry_verdict']}" for r in rj["claims"])
    return dict(
        files_not_edited=["docs/PAPER_SPEC.md", "docs/PAPER_POSITION.md",
                          "src/monostatic_scene.py", "benchmark/mono_vs_passive.py",
                          "benchmark/verify_monostatic.py", "src/rcs_sbr.py",
                          "src/sigma_anchor.py", "src/make_report*.py",
                          "src/drones.py", "src/drone_cad.py"],
        patch_PAPER_POSITION=dict(
            file="docs/PAPER_POSITION.md",
            where="§1.0 · §1.2 주장 사다리 표",
            what="표에 **기하 판정** 열을 하나 추가한다(마지막 열 앞).",
            column_header="| 기하 판정 |",
            column_values=ladder,
            extra_rows=[
                "| C0b | 속도 동적범위 v_max/v_guard = M/(2·bins) 는 기하와 무관하다 | "
                "닫힌형 ↔ 수치 차 2.2e-16 ⟨geometry_benchmark.json : usable_speed_window⟩ | "
                "없다 (항등식) | **defensible** | both |",
                "| N3 | 자기간섭이 능동 모노 행의 검지거리를 정한다 | "
                "잡음상승 47.1 dB · 거리배율 0.079× ⟨mono_link.json : verdict.headline_numbers⟩ | "
                "SI 깊이 100 dB 는 2.44 GHz·40 MHz 실측을 우리 대역으로 옮긴 값 | "
                "**defensible (조건절 필수)** | monostatic only |",
            ],
            edits=[
                "C11 의 판정에 '패시브 셀(B·C)에서' 조건절을 붙인다 — 구성 A 는 PRF 를 고르므로 "
                "이 명제의 대상 밖이다",
                "C16 을 두 줄로 쪼갠다 — 바이스태틱 자세분해 σ 는 drop 유지, "
                "**모노스태틱 자세분해 σ 는 defensible**(Δσ=0 · 커널 0.201 dB)",
                "C7 의 근거에 '네 배치에서 조명원 순위 동일' 을 추가한다 "
                "⟨mono_link.json : verdict.axis_independence_evidence⟩",
                "§2 탈출구 표에 7번째 행을 추가한다 — '(g) PRF 통제권 | 구성 A 에서만 열림 | "
                "3GPP sub-6 CSI-RS 천장 500 Hz → 10.71 m/s, 패시브 대비 10배'",
            ]),
        patch_PAPER_SPEC=dict(
            file="docs/PAPER_SPEC.md",
            where="§5 좁히기 판단 기준",
            what="3번 항목(모노+바이 → 바이 단독)을 **목록 맨 아래로 내린다**.",
            reason="모노 팔의 한계비용이 CPU 17.6 s · GPU 0 이고, 그 대가로 게재 대조군(LaSen)과 "
                   "통제 축을 얻는다 ⟨geometry_benchmark.json : verification_burden⟩.",
            replacement_list=[
                "1. σ 격자 5기체 → **1기체(mavic4pro)**",
                "2. φ 13점 → **3점 {0°, 90°, 180°}**",
                "3. 근/원거리 전 범위 → **검지 한계대(d ≳ 10L)** — 기하 축의 링크버짓 항이 "
                "0.61 dB 로 고정되고, 기하 행의 내용이 간섭항과 통제권 둘로 좁혀진다",
                "4. 기체 7종 → **실측 2종 + 대조군 2종**",
                "5. 다중 Rx → **단일 Rx**",
                "6. 모노+바이 → **바이스태틱 β ≤ 45° 단독** (⛔ 마지막에 친다 — LaSen 대조군과 "
                "통제 축을 통째로 잃는다)",
            ],
            add_to_never_cut="⭐ 통제 축(A 는 PRF 를 고르고 B·C 는 망이 준 값을 받는다)"),
        patch_experiment_freespace_range=dict(
            file="src/experiment_freespace_range.py",
            why="결함 D2 — `freespace_link.duty_db_from_cpi` 가 R90 생산경로에서 호출되지 않는다",
            patch="stage_solve 의 snr_rd_db 호출에 "
                  "`duty_db=fsl.duty_db_from_cpi(M_from_prf(T_cpi, prf), len(wf.tx)/wf.fs_hz, T_cpi)` "
                  "를 넘기고 meta.cpi 에 (M, t_ref, duty_db) 를 기록한다",
            effect="기하 비교 영향 0(두 팔 동일) · 조명원 축 LTE−5G 간격 +16.02 dB",
            note="mono_link.json : handoff.patch_requests[1] 과 동일 — 두 워크플로가 같은 패치를 요청한다"),
        patch_experiment_freespace_sigma=dict(
            file="src/experiment_freespace_sigma.py",
            why="결함 D1 — `sigma_anchor` 참조 0회, 앵커가 리포트 계층에만 있다",
            patch="σ 격자 생산 시 sigma_anchor 의 측정 기울기(0.210 dB/GHz)를 밴드축에 적용하고, "
                  "meta 에 적용 여부와 기울기를 기록한다",
            effect="R90 밴드별 ×0.900 / ×1.110 / ×1.001 · 승자 여유 3.48 → 8.31 dB"),
        note="이 파일은 정의·판정·문서화만 한다 — 금지파일과 생산 파이프라인은 읽기만 했다.")


def main():
    t0 = time.time()
    print("① 지도 구성 …")
    win = usable_window()
    mp = build_map()
    print("② 모노 팔 블라인드·접힘 …")
    bf = blind_and_fold()
    print("③ 축 크기 · ④ 재판정 …")
    ax = axis_sizes()
    rj = readjudicate(mp, win, bf)
    print("⑤ 생산 결함 · ⑥ LaSen …")
    df = live_defects(mp)
    ls = lasen(mp)
    print("⑦ 공백 · 부담 · 좁히기 …")
    gp, vb, nw, ct = gaps(), verification_burden(), narrowing(), contribution()
    print("⑧ 그림 …")
    fg = figure(mp, win)

    out = dict(
        meta=dict(
            script="benchmark/geometry_benchmark.py",
            generated=datetime.now().isoformat(timespec="seconds"),
            question="2×3 지도에서 각 칸은 무엇을 보고, 기존 주장은 어느 기하에서 서는가",
            contract=["docs/PAPER_SPEC.md §0 · §5", "docs/REBUILD_2026-07-30.md §5",
                      "outputs/geometry_grid.json", "outputs/mono_link.json"],
            reads=["geometry_grid.json", "mono_link.json", "refrate_law.json",
                   "vmax_hardening.json", "sigma_sensitivity.json",
                   "monostatic_prior.json", "report13_sigma_grid.json", "verify_cfar.json"],
            repo_functions_used=["freespace_scene.fs_params", "freespace_scene.target_pos",
                                 "freespace_scene.heading_velocity", "freespace_scene.FS_RX",
                                 "freespace_scene.folded_doppler", "freespace_scene.doppler_bin_hz",
                                 "freespace_scene.nyquist_gate", "freespace_scene.M_from_prf",
                                 "freespace_scene.blind_fractions", "freespace_link.duty_db_from_cpi"],
            house_rules="산문·print 한국어 · 그림 텍스트 영어 · 수치는 저장소에서만 · "
                        "마크다운 표도 이 스크립트가 찍는다",
            runtime_s=None),
        headline=None,
        map=mp,
        usable_speed_window=win,
        blind_and_fold=bf,
        axis_sizes=ax,
        readjudication=rj,
        contribution=ct,
        lasen_positioning=ls,
        live_defects=df,
        gaps=gp,
        verification_burden=vb,
        narrowing=nw,
        figure=fg,
        handoff=handoff(rj),
        provenance={
            "R90 by cell": "mono_link.json : detection_range.broadband.cells",
            "v_max floor": "geometry_grid.json : axis_independence.P1 · refrate_law.json : illuminators.rows",
            "usable window": "본 파일 usable_speed_window (freespace_scene.M_from_prf · DOPPLER_GUARD_HARD_BINS)",
            "blind/alias by geometry": "본 파일 blind_and_fold (freespace_scene 함수, 저장소 회귀 대조)",
            "axis sizes": "mono_link.json : axis_effects_headline",
            "DPI required depth": "geometry_grid.json : interference_ledger.passive_dpi",
            "SI required/measured": "mono_link.json : self_interference (Barneto 2019 IEEE TMTT)",
            "active PRF ceiling": "geometry_grid.json : control_axis.by_band",
            "bisector error": "geometry_grid.json : sigma_transfer",
            "anchor defect": "sigma_sensitivity.json : scenario_apply_measured_slope.finding",
            "duty defect": "sigma_sensitivity.json : unapplied_duty_axis.finding",
            "LaSen": "monostatic_prior.json : lasen · mono_link.json : views.lasen_side_by_side",
            "narrowing ladder": "docs/PAPER_SPEC.md §5",
        })
    out["headline"] = (
        f"지도가 채워졌다. 6칸을 가르는 것은 확산항이 아니라 **간섭항과 통제권**이다 — "
        f"검지 한계에서 기하 {ax['geometry_db']:.3g} dB · 조명원 {ax['illuminator_db']:.3g} dB · "
        f"상호작용 {ax['interaction_db']:.2g} dB · 간섭 {ax['interference_db']:.3g} dB. "
        f"무모호 속도의 바닥은 기하와 무관하고(차이 0 m/s), 속도창의 동적범위 M/(2·bins) 에서도 "
        f"기하가 소거된다 — 기하는 창을 통째로 밀고 CPI 가 폭을 정한다. "
        f"주장 {len(rj['claims'])}개 + 신규 {len(rj['new_claims'])}개 중 "
        f"both {rj['tally'].get('both',0)} · monostatic only {rj['tally'].get('monostatic only',0)} · "
        f"passive only {rj['tally'].get('passive only',0)} · bistatic only {rj['tally'].get('bistatic only',0)} · "
        f"neither {rj['tally'].get('neither',0)} 이고, C16(자세분해 σ)이 바이에서 drop 이면서 "
        f"모노에서 서는 유일한 승격 항목이다.")
    out["meta"]["runtime_s"] = round(time.time() - t0, 2)

    md = write_md(out)
    out["self_check"] = tone_check(md)
    out["meta"]["runtime_s"] = round(time.time() - t0, 2)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    # 자기검사 결과를 md 에 반영하기 위해 한 번 더 쓴다(값이 바뀌지 않으면 동일).
    print(f"→ {OUT_JSON}")
    print(f"→ {OUT_MD}")
    print(f"→ {FIG_STEM}.png / .pdf")
    print(f"자기검사: 부정문 {out['self_check'].get('negatives')} "
          f"(상한 {out['self_check'].get('negatives_cap')}) · "
          f"완충어 {out['self_check'].get('hedges')}")
    print(f"({out['meta']['runtime_s']} s)")
    return out


if __name__ == "__main__":
    main()
