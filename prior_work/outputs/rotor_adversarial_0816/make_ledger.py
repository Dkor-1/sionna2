# -*- coding: utf-8 -*-
"""이번 라운드 측정값을 **새 파일 하나**로 모은다(기존 원장·PRESETS 무수정).

출력: /workspace/sionna/prior_work/outputs/rotor_adversarial_0816.json
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/workspace/sionna/prior_work/outputs/rotor_adversarial_0816.json"


def med(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return float(np.median(v)) if v else None


fleet = json.load(open(f"{HERE}/fleet_rows.json"))
real, sitl = fleet["real"], fleet["sitl"]
cmp_rows = json.load(open(f"{HERE}/compare_rows.json"))["rows"]
comb = json.load(open(f"{HERE}/comb_rows.json"))
ing = json.load(open(f"{HERE}/ingredient_rows.json"))
hf = json.load(open(f"{HERE}/hf_rows.json"))
ws = json.load(open(f"{HERE}/wind_steps.json"))
ss = json.load(open(f"{HERE}/static_structure.json"))
recs = json.load(open(f"{HERE}/px4_fleet_records.json"))
pick = json.load(open(f"{HERE}/esc_pick.json"))
meta = {d["log_id"][:8]: dict(hw=d.get("sys_hw"), airframe=d.get("airframe_name"),
                              date=d.get("log_date"), dur_s=d.get("duration_s"),
                              url=f"https://review.px4.io/plot_app?log={d['log_id']}")
        for d in pick}


def pct(vals, x):
    v = np.sort(np.asarray(vals, float))
    return float(100.0 * np.searchsorted(v, x, side="right") / len(v))


veh = sorted({r["vehicle"] for r in real})
veh_ss = [med([r["sigma_s"] for r in real if r["vehicle"] == v]) for v in veh]
veh_sw = [med([r["sigma_w"] for r in real if r["vehicle"] == v]) for v in veh]

led = {
    "_meta": {
        "title": "로터 회전수 모델 적대적 검증 — 실측 코퍼스 재구축과 반증 (2026-08-16)",
        "scope_ko": "src/rotor_dynamics.py 의 OU 모델을 공개 실기 로그로 반증 시험. "
                    "코드·기존 원장·PRESETS 는 건드리지 않았다. 이 파일은 **측정값만** 담는다.",
        "cpu_only": True, "gpu_used": False,
        "interpreter": "/workspace/.venvs/py312/bin/python",
        "scripts_scratch": HERE,
        "corpus_new_ko": "PX4 Flight Review 공개 로그 2500건을 ADD_LOGGED_MSG 바이트 패턴으로 "
                         "선별(첫 768 KB Range 요청) → 70건 내려받아 pyulog 로 검증 → "
                         "esc_rpm 실측 26건(37.1 %) → 호버 창 보유 17기체 104세그먼트.",
        "false_filter_corrected_ko": "1차 필터(앞머리에 문자열 'esc_status' 존재)는 무효였다 — "
                                     "PX4 는 구독 안 한 토픽의 포맷 정의도 앞머리에 적는다. "
                                     "유효 증거는 ADD_LOGGED_MSG('A',0x41) 레코드다.",
    },
    "corpus": {
        "px4_fleet_logs_probed": 2500,
        "px4_fleet_logs_downloaded": 70,
        "px4_fleet_logs_with_real_esc_rpm": len([r for r in recs if r["ok"]]),
        "px4_fleet_vehicles_with_hover": len({r["vehicle"] for r in real if
                                              r["vehicle"] not in
                                              ("px4_s500", "dregon_cmd", "dregon_meas")}),
        "hover_segments_real": len(real),
        "hover_segments_sitl": len(sitl),
        "vehicles": {v: dict(meta.get(v, {}),
                             n_seg=len([r for r in real if r["vehicle"] == v]),
                             fs_hz=med([r["fs"] for r in real if r["vehicle"] == v]),
                             base_rpm=med([r["base_rpm"] for r in real if r["vehicle"] == v]),
                             sigma_s=med([r["sigma_s"] for r in real if r["vehicle"] == v]),
                             sigma_w_ou=med([r["sigma_w"] for r in real if r["vehicle"] == v]),
                             band_amp=med([r["amp"] for r in real if r["vehicle"] == v]),
                             pair_corr=med([r["pair_corr"] for r in real if r["vehicle"] == v]),
                             acf_tau_s=med([r["acf_tau"] for r in real if r["vehicle"] == v]))
                     for v in veh},
    },
    "F1_preset_percentiles": {
        "convention": "outputs/rotor_rpm_web_anchor.json method_note (|v|<0.3 m/s, "
                      "정적산포=창 내 로터별 평균의 로터간 std/평균, 흔들림=0.3–min(5,0.45fs) Hz "
                      "대역 rms×√2 → F-공식으로 σ_w)",
        "real_vehicles_n": len(veh),
        "sigma_s_pct": {"median": round(float(np.median(veh_ss)) * 100, 2),
                        "p25": round(float(np.percentile(veh_ss, 25)) * 100, 2),
                        "p75": round(float(np.percentile(veh_ss, 75)) * 100, 2),
                        "min": round(float(np.min(veh_ss)) * 100, 2),
                        "max": round(float(np.max(veh_ss)) * 100, 2)},
        "sigma_w_pct": {"median": round(float(np.median(veh_sw)) * 100, 2),
                        "p25": round(float(np.percentile(veh_sw, 25)) * 100, 2),
                        "p75": round(float(np.percentile(veh_sw, 75)) * 100, 2),
                        "min": round(float(np.min(veh_sw)) * 100, 2),
                        "max": round(float(np.max(veh_sw)) * 100, 2)},
        "percentile_of_presets_vehicle_weighted": {
            "outdoor_sigma_s_2.35pct": pct(veh_ss, 0.0235),
            "outdoor_sigma_w_2.45pct": pct(veh_sw, 0.0245),
            "indoor_sigma_s_0.54pct": pct(veh_ss, 0.0054),
            "indoor_sigma_w_0.65pct": pct(veh_sw, 0.0065),
            "lit_iid_sigma_s_0.99pct": pct(veh_ss, 0.0099),
            "legacy_sigma_s_0.22pct": pct(veh_ss, 0.0022)},
        "sitl_control_group_pct": {
            "sigma_s_median": round(med([r["sigma_s"] for r in sitl]) * 100, 3),
            "sigma_w_median": round(med([r["sigma_w"] for r in sitl]) * 100, 3),
            "n_vehicles": len({r["vehicle"] for r in sitl}),
            "note_ko": "PX4 SITL 6기. 실기체와 한 자릿수 차이라는 기존 결론을 새 표본이 재확인."},
        "sigma_s_window_robustness_ko": "창 5 s/20 s/60 s/전구간에서 기체별 중앙 5.62/5.65/5.69/5.73 % "
                                        "— 창 길이에 둔감하다.",
    },
    "F2_shape": {
        "acf_tau_s": {"measured_median": med([r["acf_tau"] for r in real if r["fs"] >= 9]),
                      "model_same_estimator": med([r.get("acf_exp_tau_s") for r in cmp_rows
                                                   if r["_arm"] == "outdoor"]),
                      "our_tau_ctl_s": 0.227364,
                      "px4_MPC_XY_P_median": 0.95,
                      "px4_MPC_XY_P_tau_s": 1.0526,
                      "px4_MC_ROLL_P_median": 6.5,
                      "px4_MC_ROLL_P_tau_s": 0.1538,
                      "n_logs_params_read": 26,
                      "verdict_ko": "실측 배회 시간이 우리 값의 3.6배. 크기는 **위치루프**"
                                    "(MPC_XY_P 0.95 → τ 1.05 s)와 맞고 자세루프(τ 0.15 s)와 안 맞는다. "
                                    "⚠기체별 상관은 n=8 로 유의하지 않다(r=−0.54, p=0.17) — "
                                    "«크기 일치»까지만 주장할 수 있다."},
        "power_fraction_pct_high_rate_logs": {
            "logs": [dict(tag=r["tag"], fs_hz=r["fs"], n_windows=r["n"],
                          **{k: round(r[k], 1) for k in
                             ("<0.5", "0.5-2", "2-5", "5-10", "10-20", ">20")}) for r in hf],
            "measured_median": {k: round(float(np.median([r[k] for r in hf])), 1)
                                for k in ("<0.5", "0.5-2", "2-5", "5-10", "10-20", ">20")},
            "our_ou_tau0.227": {"<0.5": 39.6, "0.5-2": 39.3, "2-5": 12.7, "5-10": 4.4,
                                "10-20": 2.2, ">20": 1.8},
            "ou_tau1.04": {"<0.5": 81.2, "0.5-2": 14.1, "2-5": 2.9, "5-10": 1.0,
                           "10-20": 0.5, ">20": 0.4},
            "verdict_ko": "OU 라는 «모양»은 맞다. τ 만 고치면 옥타브 몫이 실측과 겹친다."},
        "distribution_ko": "주변분포는 거의 가우시안이다(초과첨도 실측 +0.13 vs 모델 −0.06, "
                           "|z|의 99.9 % 분위 3.31 vs 3.11). Anderson–Darling 은 유의하지만 "
                           "꼬리 차이는 작다 — 이 축은 우리 모델의 약점이 아니다.",
    },
    "F3_rotor_structure": {
        "pair_corr_hover_fs_ge9": {
            "median": med([r["pair_corr"] for r in real if r["fs"] >= 9]),
            "per_vehicle": {v: med([r["pair_corr"] for r in real
                                    if r["vehicle"] == v and r["fs"] >= 9]) for v in veh},
            "verdict_ko": "호버·충분표집에서 로터 간 상관 중앙 ≈ 0.00 (범위 −0.24…+0.20) — "
                          "**독립 가정은 호버에서 지지된다**(적대적 검증의 반대 방향 결과)."},
        "maneuver_common_mode": {
            "px4_race_1e858ce3_pair_corr_10s_tiles": 0.934,
            "common_mode_share": 0.950,
            "note_ko": "⚠이 로그는 «과격 호버» 가 아니라 **기동 비행**이다(중앙 |v| 2.19 m/s, "
                       "|v|<0.3 m/s 창이 2 s 이상 하나도 없다). 어제 기록의 «호버» 표기는 정정 필요."},
        "per_rotor_wobble_inequality": {
            "measured_max_over_min_median": 1.47, "measured_range": [1.08, 2.98],
            "model_null_median": 1.13, "model_null_p90": 1.23,
            "verdict_ko": "실기체는 로터마다 흔들림 «크기»가 다르다(중앙 1.47배). "
                          "우리 모델은 네 로터에 같은 σ_w 를 쓴다."},
        "static_offset_structure": {
            "dominant_split_counts": {"pitch(fore-aft)": 9, "roll(left-right)": 3, "yaw": 3},
            "best_split_share_measured_median": 0.799,
            "best_split_share_iid_null_median": 0.695,
            "mannwhitney_p": 0.0335,
            "pattern_stability_cosine_median": 0.93,
            "verdict_ko": "정적 편차는 «둘 vs 둘» 트림 구조를 띠고 축은 주로 **피치(앞뒤 무게중심)** "
                          "다. 다만 독립 가우시안 귀무와의 차이는 약하다(p=0.03) — "
                          "«DREGON 0.997» 만 보고 강한 구조라고 결론내면 과장이다. "
                          "패턴은 한 비행 안에서 거의 고정(코사인 0.93).",
            "per_vehicle": ss},
        "throttle_step": {
            "n_vertical_segments": len(ws["steps"]),
            "common_rpm_swing_pct_median": round(float(np.median(
                [r["d_rpm_pct"] for r in ws["steps"]])), 1),
            "common_rpm_swing_pct_p90": round(float(np.percentile(
                [r["d_rpm_pct"] for r in ws["steps"]], 90)), 1),
            "rate_pct_per_s_median": round(float(np.median(
                [r["rate_pct_s"] for r in ws["steps"]])), 1),
            "verdict_ko": "수직 기동에서 네 로터가 **함께** 중앙 22 % 움직인다(변화율 ~5 %/s). "
                          "우리 모델은 평균 rpm 이 상수라 이 성분이 원리적으로 0 이다."},
        "wind_proxy": {
            "proxy_ko": "호버 중 기체 기울기[deg] (바람 속 위치유지 = 바람 쪽으로 기울임)",
            "n_windows": len(ws["wind"]), "pearson_r": 0.493, "pearson_p": 0.023,
            "spearman_rho": 0.544, "spearman_p": 0.011,
            "fit_ko": "흔들림[%] = 0.84 + 0.306 × 기울기[deg]",
            "verdict_ko": "«흔들림은 바람이 만든다»(Heutschi 2020·Rahman 2020)가 독립 데이터에서 "
                          "재현. ⚠기울기는 대리값이라 m/s 로 환산은 못 한다."},
    },
    "F4_microdoppler_comb": {
        "config": comb["cfg"],
        "verdict_single_rotor_ko": "로터 1개(흔들림만): 레벨을 맞추면 우리 OU 가 실측 빗살을 "
                                   "잘 재현한다(퍼짐 m=12 에서 실측 13.6 Hz vs 모델 14.1 Hz, +4 %). "
                                   "⇒ 호버에서 «모양» 오차는 작다.",
        "verdict_preset_level_ko": "생산 설정(outdoor σ_w 2.45 %)은 실측보다 퍼짐 1.8배"
                                   "(m=12: 24.3 vs 13.6 Hz), m=9 빗살 꼭대기/중앙 24 dB 낮음. "
                                   "⇒ 오차의 주범은 «모양»이 아니라 **프리셋 값**이다.",
        "verdict_quad_ko": "4로터 현실 조건(σ_s 2.35 %)에서는 흔들림의 모양·상관 구조를 아무리 "
                           "바꿔도 빗살이 거의 안 변한다(퍼짐 ≤3 %, 꼭대기 ≤3.5 dB). "
                           "**정적 산포 σ_s 가 빗살 폭을 지배한다** — 퍼짐 ≈ m·f_flash·0.866σ_s.",
        "verdict_maneuver_ko": "기동에서는 반대다: 같은 σ_w 라도 실측은 저주파에 몰려 있어 "
                               "우리 OU 보다 퍼짐이 45 % 작다(m=3: 12.1 vs 17.6 Hz).",
        "model_free_anchor_pct": {
            "in_window_rms_1.0s_median": 0.89, "in_window_rms_1.0s_range": [0.10, 1.77],
            "in_window_rms_0.25s_median": 0.40, "in_window_rms_0.25s_range": [0.08, 0.99],
            "why_ko": "빗살 퍼짐은 «창 안 상대 rms» 에만 걸린다. 이 값은 OU 가정이 필요 없다 — "
                      "프리셋을 σ_w 대신 이 값으로 못 박으면 τ 논쟁과 무관해진다.",
            "our_outdoor_equivalent_1s": 1.97},
    },
    "F5_open": [
        "표적 기체(Mavic 4 Pro · Matrice 4E)의 로터별 rpm 은 여전히 공개 어디에도 없다 — "
        "이번 함대 검색(2500건 훑음)에서도 DJI 기체는 0건이다. 자체 실측이 유일 경로.",
        "σ_s 가 큰 기체(≥8 %)에서 그 값이 진짜 트림인지 ESC 눈금 오차인지 못 가른다 — "
        "35b1d6eb 는 저/고 스로틀에서 패턴이 0.42 %p 밖에 안 변해 «고정 배수» 가설을 못 배제한다. "
        "다만 af26fde6(5.5 %p 변화)처럼 조건 의존인 기체가 더 많고, 그 기체를 빼도 중앙값은 5.6 % 다.",
        "로터 초기 위상 𝒰(0,360/blades) 는 어떤 공개 로그로도 검증할 수 없다(로그에 위상이 없다).",
        "DREGON(1 kHz MikroKopter)만 8–32 Hz 에 10 % 대 파워를 갖는다. 고속 PX4 3기는 "
        ">5 Hz 가 5 % 미만이다. 이 차이가 기체 차이인지 회전수 추정기 잡음인지 못 가른다.",
        "산란 진폭 요동·회전 1바퀴 안의 결정론적 리플은 여전히 미모델(기존 결론과 동일).",
    ],
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(led, open(OUT, "w"), ensure_ascii=False, indent=1)
print("wrote", OUT, os.path.getsize(OUT), "bytes")
