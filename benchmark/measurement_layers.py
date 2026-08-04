"""실측 3층 설계의 **새 층**(2층 파형축·검증 3점·3층 비행검출)에 필요한 숫자편.

⚠ 이 파일은 §4 AUTO 계산표(`src/sigma_anchor.measurement_plan`)를 **대체하지 않는다**.
   §4 는 1층(σ(f) 레인지)의 원거리장·교정구·점표적·지면반사 표를 낸다.
   여기서 새로 계산하는 것은 그 표에 없는 것들뿐이다:

     1. ISM 5.8 GHz 에서의 1층 요구 (원거리장·턴테이블 각도·서브밴드 점표적)
        — §A/§C 는 1.843/3.5/5.21 GHz 만 덮는다
     2. 도플러-반송파 결합 v_max = λ·PRF/4  ⭐ **재는 게 아니라 계산하는 것**
     3. 교정구 규약차 — 앵커(Yuan)는 σ_Cal = −10 dBsm = πr² 를 썼고 우리는 정확 Mie 를 쓴다.
        이 차이는 비(ratio)에서 **소거되지 않는다**
     4. 앵커와 사과-대-사과 되는 각도 표본수 N (Yuan 은 셀당 N=91 로 분포를 적합했다)

⛔ 아무것도 측정하지 않고 GPU 도 쓰지 않는다. 순수 설계 산술이다.
산출: outputs/measurement_layers.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(HERE, "src"), os.path.join(HERE, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
OUT_JSON = os.path.join(HERE, "outputs", "measurement_layers.json")

#: 1·3층 대상 기체 (구매 확정 2종) — §4 표와 같은 모집단
PLAN_DRONES = ("matrice4e", "mini5pro")

#: 2층 반송파 — 면허 불필요한 ISM 한 곳. ⚠ 국내 허용 대역·EIRP 는 미확인(열린 질문 Q3)
ISM_FC_HZ = 5.8e9
ISM_SPAN_HZ = 150e6          # 5.725~5.875 GHz 로 잡은 설계 가정
ISM_BW_HZ = (150e6, 100e6, 80e6, 50e6, 25e6)

#: 검증 3점 = 실제 배치 신호 (수신만). 값은 저장소 정본과 같다
#:   src/experiment_freespace_range.py:90-92
REAL_THREE = (("lte", "LTE 1.843 GHz", 1.843e9, 20e6),
              ("nr", "5G NR 3.5 GHz", 3.500e9, 100e6),
              ("wifi", "WiFi 5.21 GHz", 5.210e9, 80e6))

#: v_max 격자에 쓸 반송파 — 검증 3점 + 2층 ISM
VMAX_FC_HZ = {"LTE 1.843 GHz": 1.843e9, "5G 3.5 GHz": 3.5e9,
              "WiFi 5.21 GHz": 5.21e9, "ISM 5.8 GHz": ISM_FC_HZ}


def _duty_rows():
    """저장소 정본에서 모드별 PRF·듀티를 그대로 읽는다 (숫자를 손으로 적지 않는다)."""
    import freespace_link as fl
    rows = {}
    for m in ("W1", "W2", "W3", "L1", "L2", "L3", "G1", "G2", "G3"):
        d = fl.duty_terms(m)
        rows[m] = dict(std=d["std"], occ=d["occ"], prf_hz=float(d["prf_hz"]),
                       M=int(d["M"]), T_ref_s=float(d["T_ref_s"]),
                       duty_db=float(d["duty_db"]))
    return rows


def ism_layer1_requirements():
    """1층을 ISM 5.8 GHz 에서 돌릴 때의 원거리장·각도표본·점표적 조건."""
    from drones import DRONES
    from radar_scene import target_extent, farfield_distance
    lam = C0 / ISM_FC_HZ
    out = {"fc_hz": ISM_FC_HZ, "lambda_m": lam, "span_hz": ISM_SPAN_HZ, "airframes": {}}
    for dk in PLAN_DRONES:
        s = DRONES[dk]
        D = float(target_extent(dk))
        # 방위 표본: 회전축에서 D/2 떨어진 산란점의 왕복 경로변화 D·Δφ 를
        #   λ/2 미만(나이퀴스트) 또는 λ/4 미만(권장)으로 유지한다. §A 와 같은 규약.
        nyq = float(np.degrees(lam / (2.0 * D)))
        rec = float(np.degrees(lam / (4.0 * D)))
        out["airframes"][dk] = dict(
            name=s.name, D_bbox_m=D, D_over_lambda=D / lam,
            farfield_m=float(farfield_distance(D, ISM_FC_HZ)),
            az_step_nyquist_deg=nyq, az_step_recommended_deg=rec,
            # 앵커와 같은 −90°~90° 구간에서의 표본수 (Yuan 은 2° 로 N=91 을 얻었다)
            N_over_180deg_nyquist=int(np.floor(180.0 / nyq)) + 1,
            N_over_180deg_recommended=int(np.floor(180.0 / rec)) + 1,
            N_anchor_2deg=91,
            point_target={f"B={int(b/1e6)}MHz":
                          dict(range_res_m=float(C0 / (2.0 * b)),
                               point_like=bool(C0 / (2.0 * b) > D),
                               margin_m=float(C0 / (2.0 * b) - D))
                          for b in ISM_BW_HZ})
    out["_rule"] = ("§A/§C 는 1.843/3.5/5.21 GHz 만 덮는다. 2층을 ISM 5.8 GHz 에 놓기로 "
                    "확정했으므로 같은 규약을 그 반송파에서 다시 계산한 것이다.")
    return out


def angular_sampling():
    """앵커의 2° 스텝이 우리 기체·우리 밴드에서 충분한가 — 밴드별로 갈린다.

    ⚠ 뭉뚱그리면 틀린다. "우리가 앵커보다 촘촘하다" 도 "앵커가 우리보다 촘촘하다" 도
       전 밴드에 걸쳐서는 거짓이다. 요구 Δφ 는 λ/4D 라 **저주파에서 오히려 성기다**."""
    from radar_scene import target_extent
    bands = {"LTE 1.843 GHz": 1.843e9, "5G 3.5 GHz": 3.5e9,
             "WiFi 5.21 GHz": 5.21e9, "ISM 5.8 GHz": ISM_FC_HZ}
    anchor_step = 2.0
    span = 180.0                                  # 앵커와 같은 −90°~90°
    out = {"anchor_step_deg": anchor_step, "anchor_N": 91, "span_deg": span, "by_drone": {}}
    too_coarse = []
    for dk in PLAN_DRONES:
        D = float(target_extent(dk))
        rows = {}
        for b, f in bands.items():
            lam = C0 / f
            rec = float(np.degrees(lam / (4.0 * D)))
            n = int(np.floor(span / rec)) + 1
            bad = bool(anchor_step > rec)
            rows[b] = dict(step_recommended_deg=rec, N_required=n,
                           anchor_2deg_sufficient=not bad)
            if bad:
                too_coarse.append(f"{dk} @ {b}")
        out["by_drone"][dk] = dict(D_bbox_m=D, by_band=rows)
    out["anchor_2deg_too_coarse_at"] = too_coarse
    out["N_required_range"] = [
        min(r["N_required"] for d in out["by_drone"].values() for r in d["by_band"].values()),
        max(r["N_required"] for d in out["by_drone"].values() for r in d["by_band"].values())]
    out["_rule"] = ("⭐ 앵커가 스스로 밝힌 한계(*'the chosen step size may be too large at higher "
                    "frequencies'*) 가 우리 기체에서 실제로 무는 자리를 이 표가 지목한다. "
                    "그 자리 밖에서는 2° 로 충분하고, 오히려 우리 요구가 더 성기다.")
    return out


def doppler_carrier_coupling(duty_rows):
    """⭐ 두 축(반송파·파형)의 결합 — **재는 게 아니라 계산하는 것**.

    v_max = λ·PRF/4  (무모호 반구간 규약, Abratkiewicz IEEE JSTARS 16:3469-3484 (2023) 식 (16)).
    ⚠ 우리 표는 c = 299792458 로 계산했다 (RETRACTION_LOG A6 — 어느 c 인지 밝혀야 한다).

    ⭐ 이 전달이 **정확한 것**과 **정확하지 않은 것**을 분리해서 낸다:
      정확 : 무모호 속도 상한. 순수 표본화 사실이라 λ 비로 정확히 옮겨간다
      부정확: SNR. σ(f)·안테나이득·경로손실이 전부 반송파의 함수라 λ 비로 안 옮겨간다
    """
    rows = {}
    for mode, d in duty_rows.items():
        prf = d["prf_hz"]
        rows[mode] = dict(prf_hz=prf, duty_db=d["duty_db"], std=d["std"], occ=d["occ"],
                          v_max_ms={k: float(C0 / f * prf / 4.0)
                                    for k, f in VMAX_FC_HZ.items()})
    transfer = {k: float((C0 / f) / (C0 / ISM_FC_HZ)) for k, f in VMAX_FC_HZ.items()}
    return dict(
        formula="v_max = lambda * PRF / 4   (unambiguous, half-interval convention)",
        c_used_m_per_s=C0,
        provenance=("Abratkiewicz et al., IEEE JSTARS 16:3469-3484 (2023), eq. (16) p.3476. "
                    "PRF·듀티는 freespace_link.duty_terms (3GPP/IEEE 자원격자) 에서 읽었다."),
        rows=rows,
        lambda_transfer_from_ISM58=transfer,
        exact_under_transfer="unambiguous velocity ceiling (pure sampling fact)",
        NOT_exact_under_transfer=("SNR / detection range — sigma(f), antenna gain and path loss "
                                  "are all functions of carrier and do not scale as lambda"),
        _rule=("⭐ 2층을 ISM 한 곳에서만 재는 대가는 이 표로 **계산해서** 갚는다. "
               "다른 반송파의 v_max 는 측정하지 않고 λ 비로 옮긴다. "
               "⛔ 같은 방식으로 SNR 을 옮기면 안 된다."))


def calibration_convention_gap():
    """⚠ 교정구 규약차 — 비(ratio)에서 소거되지 않는 항.

    Yuan §II-B 축자: *"A metallic sphere with a radius of 17.8 cm (RCS as sigma_Cal = -10 dBsm)"*
    → 그 값은 **광학 점근 πr²** 이다(πr² = -10.02 dBsm). 우리는 정확 Mie 를 쓴다(§1-1).
    σ_DUT = |S_DUT|²/|S_Cal|² · σ_Cal 이므로 σ_Cal 규약차는 **그대로 σ_DUT 에 곱해진다**.
    """
    from mie_pec_sphere import sphere_reference_set
    r = 0.178
    bands = dict(VMAX_FC_HZ)
    rows = {}
    for k, f in bands.items():
        ref = sphere_reference_set(r, f)
        rows[k] = dict(ka=float(ref["kr"]), mie_dbsm=float(ref["mie_dbsm"]),
                       go_pir2_dbsm=float(ref["go_dbsm"]),
                       mie_minus_pir2_db=float(ref["mie_minus_go_db"]))
    anchor_sigma_cal_dbsm = -10.0
    pir2_dbsm = float(10.0 * np.log10(np.pi * r * r))
    return dict(
        radius_m=r,
        anchor_declared_sigma_cal_dbsm=anchor_sigma_cal_dbsm,
        anchor_quote=("A metallic sphere with a radius of 17.8 cm (RCS as sigma_Cal = -10 dBsm) "
                      "is positioned at the center of the turntable"),
        anchor_quote_source=("Yuan et al., EuCAP 2025, On Experimental Analysis of Mono-Static 3D "
                             "UAV RCS for ISAC Channel Modeling, Sec. II-B, p.2 (verbatim)"),
        pir2_dbsm=pir2_dbsm,
        anchor_used_optical_pir2=bool(abs(anchor_sigma_cal_dbsm - pir2_dbsm) < 0.05),
        by_band=rows,
        our_sigma_shift_if_we_use_mie_db={k: v["mie_minus_pir2_db"] for k, v in rows.items()},
        _rule=("⭐ 우리가 정확 Mie 로 교정하면 우리 σ 는 앵커 규약 대비 이 표만큼 **위로** 뜬다. "
               "앵커와 사과-대-사과로 대조할 때는 이 항을 먼저 되돌리고 비교한다. "
               "⛔ 이 항은 σ_DUT/σ_Cal 비에서 소거되지 않는다 — 분모의 규약 그 자체다."))


def waveform_axis():
    """2층 — ISM 한 반송파에서 세 파형 **구조**. 지표는 SNR_out / E_tx."""
    import freespace_link as fl
    struct = {}
    for mode, label, b_hz in (("W1", "WiFi-like (dense OFDM burst)", 80e6),
                              ("L1", "LTE-CRS-like (comb reference, always-on)", 20e6),
                              ("G1", "5G-SSB-like (sparse burst)", 100e6)):
        d = fl.duty_terms(mode)
        struct[mode] = dict(
            label=label, repo_mode=mode, std=d["std"], occ=d["occ"],
            occupied_bw_hz=float(b_hz), prf_hz=float(d["prf_hz"]),
            M_per_cpi=int(d["M"]), T_ref_s=float(d["T_ref_s"]), duty_db=float(d["duty_db"]),
            range_res_m=float(C0 / (2.0 * b_hz)),
            v_max_at_ism_ms=float(C0 / ISM_FC_HZ * d["prf_hz"] / 4.0),
            fits_in_ism_span=bool(b_hz <= ISM_SPAN_HZ))
    return dict(
        carrier_hz=ISM_FC_HZ, span_hz=ISM_SPAN_HZ, structures=struct,
        metric="SNR_out / E_tx  (output SNR normalised by transmitted energy)",
        why_one_carrier=("면허. 2.1 GHz 야외 송신은 허가가 필요하고 '2.1 GHz 의 WiFi' 는 "
                         "세상에 없는 인공물이다. 반송파를 고정하면 파형 구조만 남는다."),
        what_this_costs=("반송파축을 잃는다. 그 대가는 (a) 검증 3점의 실제 배치신호 수신과 "
                         "(b) doppler_carrier_coupling 표의 계산으로 갚는다."),
        _warn=("⚠ 세 구조가 ISM span 안에서 **서로 다른 주파수 조각**을 차지하면 σ(f) 가 "
               "평평하지 않으므로 비(ratio) 소거가 깨진다 (§7 B11). 같은 서브밴드 중심에 "
               "겹쳐 놓는 판을 반드시 함께 잰다."))


def validation_three_points():
    """검증 — 배치된 WiFi/LTE/5G 를 **수신만**. 송신 안 하므로 면허 문제 없음."""
    import freespace_link as fl
    pts = {}
    for std, label, fc, b_hz in REAL_THREE:
        mode = {"wifi": "W1", "lte": "L1", "nr": "G1"}[std]
        d = fl.duty_terms(mode)
        pts[std] = dict(label=label, carrier_hz=float(fc), occupied_bw_hz=float(b_hz),
                        repo_mode=mode, prf_hz=float(d["prf_hz"]), duty_db=float(d["duty_db"]),
                        range_res_m=float(C0 / (2.0 * b_hz)),
                        v_max_ms=float(C0 / fc * d["prf_hz"] / 4.0),
                        transmit_required=False, licence_required=False)
    return dict(
        points=pts, receive_only=True,
        channels=("reference + surveillance = 2 channels on a common clock "
                  "(NOT 4 simultaneous channels - see RETRACTION_LOG)"),
        role=("1층(σ(f)) × 2층(파형) 의 예측을 이 3점으로 **검증**한다. "
              "3점은 교차설계의 대각선이 아니라 **독립 검사점**이다."),
        _warn=("⚠ 여기서 σ 는 **바이스태틱**이다. 1층이 낸 것은 준모노스태틱 σ 다. "
               "둘은 다른 물리량이므로 예측을 옮길 때 그 변환을 명시해야 한다 (§7 B4)."))


def flight_layer():
    """3층 — 능동 모노, 단일 밴드, Pd vs 거리."""
    return dict(
        geometry="active monostatic", carrier="single band (ISM 5.8 GHz, same as layer 2)",
        headline="Pd vs range at fixed Pfa",
        pfa_is="CFAR design value, not a measurement",
        target_state="in flight (rotors spinning) - the only layer where rotors turn",
        what_it_does_NOT_give=("절대 σ. 비행 표적은 자세·거리·속도가 동시에 변하므로 "
                               "σ 를 분리할 수 없다. σ 는 1층에서만 나온다."),
        ties_back_to=("1층의 P(sigma) 를 Swerling 틀로 넣으면 Pd(range) 가 예측된다. "
                      "3층은 그 예측의 검사다."))


#: §4 AUTO 표가 인쇄된 시점(07-30)의 D_bbox. 07-31 메쉬 개편(커밋 cba8626) 이전 값이다.
STALE_D_BBOX_M = {"matrice4e": 0.5993, "mini5pro": 0.3760}


def stale_table_drift():
    """⚠ §4 AUTO 표는 07-31 메쉬 개편 이전에 생성됐다 — 그 드리프트를 숫자로 남긴다.

    ⭐ 결론을 미리 적어둔다: 드리프트는 **안전한 쪽**이다. 옛 표의 D 가 더 커서
       원거리장 요구는 더 멀고 각도간격 요구는 더 촘촘하다. 표를 그대로 써도
       설계가 헐거워지지 않는다. 그래도 인쇄할 때는 낡음을 밝힌다."""
    from drones import DRONES                       # noqa: F401  (존재 확인)
    from radar_scene import target_extent, farfield_distance
    bands = {"LTE 1.843 GHz": 1.843e9, "5G 3.5 GHz": 3.5e9, "WiFi 5.21 GHz": 5.21e9}
    rows = {}
    conservative = True
    for dk, D_old in STALE_D_BBOX_M.items():
        D_new = float(target_extent(dk))
        by_band = {}
        for b, f in bands.items():
            lam = C0 / f
            ff_o, ff_n = float(farfield_distance(D_old, f)), float(farfield_distance(D_new, f))
            st_o = float(np.degrees(lam / (4.0 * D_old)))
            st_n = float(np.degrees(lam / (4.0 * D_new)))
            by_band[b] = dict(farfield_printed_m=ff_o, farfield_current_m=ff_n,
                              farfield_delta_m=ff_n - ff_o,
                              az_step_printed_deg=st_o, az_step_current_deg=st_n,
                              printed_is_conservative=bool(ff_o >= ff_n and st_o <= st_n))
            conservative &= by_band[b]["printed_is_conservative"]
        rows[dk] = dict(D_bbox_printed_m=D_old, D_bbox_current_m=D_new,
                        delta_mm=(D_new - D_old) * 1000.0, by_band=by_band)
    return dict(
        what="§4 AUTO 표(07-30 생성) vs 현재 메쉬(07-31 개편 이후)의 D_bbox 드리프트",
        rows=rows, printed_table_is_conservative_everywhere=bool(conservative),
        regenerate_cmd=("PYTHONPATH=src:benchmark SIONNA2_CPU=1 ~/.venvs/py312/bin/python -c "
                        "\"import sigma_anchor as S; S.write_measurement_plan()\""),
        _rule=("⛔ 이 라운드에서는 §4 를 재생성하지 않는다(보존 지시). 대신 드리프트를 여기 남긴다. "
               "§A/§C 숫자를 인쇄할 때 '07-30 생성, 07-31 메쉬 개편 이전' 을 함께 적는다."))


def gate_wide_evaluate_narrow():
    """⭐ 서브밴드 규약과 지면유령 게이팅이 서로 반대 방향을 요구하는 문제와 그 해소.

    · 점표적/대역평균 조건 : 좁은 대역을 원한다 (σ 를 검출기 대역폭으로 정의해야 하므로)
    · 지면유령 레인지게이팅: 넓은 대역을 원한다 (경로차 §D 를 분해해야 하므로)

    해소 = 앵커가 실제로 한 순서다 — **넓게 게이팅하고 좁게 평가한다.**
    Yuan §II-C: 배경차감 → 전대역 CIR 에 6차 Kaiser 창으로 레인지게이팅 →
    주파수영역 복귀 → 교정구 대비 전력비를 **주파수마다** 취한다.
    """
    from radar_scene import target_extent
    gate_b = 400e6                      # X410 순시대역 전부를 게이팅에 쓴다
    eval_b = 50e6                       # σ 를 정의할 서브밴드
    rows = {}
    for dk in PLAN_DRONES:
        D = float(target_extent(dk))
        rows[dk] = dict(
            D_bbox_m=D,
            gate_range_res_m=float(C0 / (2.0 * gate_b)),
            gate_resolves_target=bool(C0 / (2.0 * gate_b) < D),
            eval_range_res_m=float(C0 / (2.0 * eval_b)),
            eval_point_like=bool(C0 / (2.0 * eval_b) > D),
            n_subbands=int(round(gate_b / eval_b)))
    return dict(
        gate_bw_hz=gate_b, eval_bw_hz=eval_b, by_drone=rows,
        why_subband_is_not_only_about_point_targets=(
            "우리 커널이 이미 대역평균 σ 를 낸다 — rcs_po.drone_rcs_pattern_bw(key, fc, bw_hz, ...), "
            "viz_radar.BW_HZ=100e6 주석 축자 '레이더가 실제로 보는 값'. "
            "따라서 σ 의 정의 대역폭은 **검출기가 적분하는 대역폭**이어야 하고, "
            "그것이 서브밴드를 고르는 1차 이유다. 점표적 조건은 2차다."),
        binding_condition=(
            "⚠ 점표적 조건(ΔR > D)이 실제로 무는 자리는 '거리프로파일 peak 을 σ 로 읽을 때' 다. "
            "게이팅 후 주파수마다 비를 취하는 앵커식으로 읽으면 peak 법이 아니므로 그 조건은 "
            "다르게 작동한다. 어느 읽기법을 쓸지 프로토콜에 박아야 한다."),
        anchor_quote=("a 6th-order Kaiser window function, defined by a predetermined delay range, "
                      "is applied to the CIR, and the gated CIRs are then transformed back into "
                      "the frequency domain"),
        anchor_quote_source="Yuan et al., EuCAP 2025, Sec. II-C-2, p.3 (verbatim)")


def build():
    duty = _duty_rows()
    rep = dict(
        _meta=dict(
            what=("실측 3층 설계의 새 층에 필요한 숫자. §4 AUTO 계산표(1층 σ(f) 레인지)를 "
                  "대체하지 않고 보완한다."),
            generator="benchmark/measurement_layers.py",
            consumed_by="docs/MEASUREMENT_PLAN.md",
            measures_nothing=True, uses_gpu=False),
        repo_duty_table=duty,
        layer1_at_ism=ism_layer1_requirements(),
        angular_sampling=angular_sampling(),
        doppler_carrier_coupling=doppler_carrier_coupling(duty),
        calibration_convention_gap=calibration_convention_gap(),
        layer2_waveform_axis=waveform_axis(),
        validation_three_points=validation_three_points(),
        layer3_flight=flight_layer(),
        gate_wide_evaluate_narrow=gate_wide_evaluate_narrow(),
        stale_table_drift=stale_table_drift())
    with open(OUT_JSON, "w") as fh:
        json.dump(rep, fh, indent=2, ensure_ascii=False)
    return rep


if __name__ == "__main__":
    r = build()
    print("=" * 96)
    print("실측 3층 설계 — 새 층 숫자편 (측정 아님, 설계 산술만)")
    print("=" * 96)

    print("\n[1층을 ISM 5.8 GHz 에서 돌릴 때]")
    for dk, v in r["layer1_at_ism"]["airframes"].items():
        print(f"  {dk:10s} D={v['D_bbox_m']*1000:6.1f} mm  D/λ={v['D_over_lambda']:5.2f}  "
              f"원거리장 {v['farfield_m']:5.2f} m  Δφ권장 {v['az_step_recommended_deg']:.2f}° "
              f"→ N={v['N_over_180deg_recommended']} (앵커 2°: N=91)")
        for b, p in v["point_target"].items():
            print(f"      {b:11s} ΔR={p['range_res_m']:.3f} m  "
                  f"{'점표적 OK' if p['point_like'] else '⚠ 퍼짐'} (여유 {p['margin_m']:+.3f} m)")

    print("\n[각도표본 — 앵커의 2° 가 충분한가]")
    a = r["angular_sampling"]
    for dk, v in a["by_drone"].items():
        for b, row in v["by_band"].items():
            print(f"  {dk:10s} {b:16s} Δφ권장 {row['step_recommended_deg']:.2f}°  N={row['N_required']:4d}  "
                  f"앵커 2° 충분={row['anchor_2deg_sufficient']}")
    print(f"  ⚠ 2° 가 부족한 자리: {a['anchor_2deg_too_coarse_at']}  ·  N 요구범위 {a['N_required_range']}")

    print("\n[⭐ 도플러-반송파 결합 — 재는 게 아니라 계산하는 것] v_max = λ·PRF/4")
    hdr = list(VMAX_FC_HZ)
    print("  mode  PRF[Hz]  " + "  ".join(f"{h:>16s}" for h in hdr))
    for m, v in r["doppler_carrier_coupling"]["rows"].items():
        print(f"  {m:5s} {v['prf_hz']:8.2f}  " +
              "  ".join(f"{v['v_max_ms'][h]:16.3f}" for h in hdr))
    print("  λ 전달비 (ISM 5.8 GHz 기준): " +
          "  ".join(f"{k}={v:.4f}" for k, v in
                   r["doppler_carrier_coupling"]["lambda_transfer_from_ISM58"].items()))

    print("\n[⚠ 교정구 규약차 — 비에서 소거되지 않는다] r=0.178 m")
    g = r["calibration_convention_gap"]
    print(f"  앵커 선언 σ_Cal = {g['anchor_declared_sigma_cal_dbsm']:.2f} dBsm · "
          f"πr² = {g['pir2_dbsm']:.4f} dBsm · 앵커가 광학근사를 썼나 = {g['anchor_used_optical_pir2']}")
    for k, v in g["by_band"].items():
        print(f"  {k:16s} ka={v['ka']:6.2f}  Mie={v['mie_dbsm']:+7.3f} dBsm  "
              f"Mie−πr² = {v['mie_minus_pir2_db']:+.3f} dB")

    print("\n[2층 — ISM 5.8 GHz 세 파형 구조]  지표 = SNR_out / E_tx")
    for m, v in r["layer2_waveform_axis"]["structures"].items():
        print(f"  {m}  {v['label']:42s} B={v['occupied_bw_hz']/1e6:5.0f} MHz  "
              f"PRF={v['prf_hz']:7.2f} Hz  duty={v['duty_db']:+7.2f} dB  "
              f"ΔR={v['range_res_m']:.3f} m  v_max={v['v_max_at_ism_ms']:.3f} m/s")

    print("\n[검증 3점 — 수신만]")
    for s, v in r["validation_three_points"]["points"].items():
        print(f"  {s:5s} {v['label']:16s} B={v['occupied_bw_hz']/1e6:5.0f} MHz  "
              f"v_max={v['v_max_ms']:7.3f} m/s  송신필요={v['transmit_required']}")
    print("\n[⭐ 넓게 게이팅하고 좁게 평가한다]")
    g = r["gate_wide_evaluate_narrow"]
    for dk, v in g["by_drone"].items():
        print(f"  {dk:10s} 게이팅 {g['gate_bw_hz']/1e6:.0f} MHz → ΔR={v['gate_range_res_m']:.3f} m "
              f"(표적 분해 {v['gate_resolves_target']})  ·  평가 {g['eval_bw_hz']/1e6:.0f} MHz → "
              f"ΔR={v['eval_range_res_m']:.3f} m (점표적 {v['eval_point_like']}), "
              f"서브밴드 {v['n_subbands']}개")

    print("\n[⚠ §4 AUTO 표 드리프트 — 07-30 생성, 07-31 메쉬 개편 이전]")
    d = r["stale_table_drift"]
    for dk, v in d["rows"].items():
        print(f"  {dk:10s} D_bbox {v['D_bbox_printed_m']*1000:.1f} → "
              f"{v['D_bbox_current_m']*1000:.1f} mm ({v['delta_mm']:+.1f} mm)")
    print(f"  인쇄된 표가 모든 밴드에서 보수적인가 = {d['printed_table_is_conservative_everywhere']}")

    print(f"\n저장: {OUT_JSON}")
