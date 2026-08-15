# -*- coding: utf-8 -*-
"""az_falsify_verdict.py — «45° 돌리면 정면 에코가 25~51 dB 사라진다» 반증 종합.
GPU 안 씀. 저장 원장·샤드 + numpy PO 적분·메쉬 판독만."""
import json
import numpy as np

ROOT = "/workspace/sionna"
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
PRF, FFL, FTIP = 19700.0, 126.66666666666667, 1272.9
W = np.hanning(8192); CG = (W ** 2).sum()


def ac(k):
    x = np.asarray(Z[k]).astype(complex); return x - x.mean()


def stat(k):
    x = np.asarray(Z[k]).astype(complex); a = x - x.mean()
    P = np.abs(np.fft.fft(a * W)) ** 2 / CG
    F = np.fft.fftfreq(a.size, 1 / PRF); fa = np.abs(F)
    kh = np.round(fa / FFL); on = (kh >= 1) & (kh <= 60) & (np.abs(fa - kh * FFL) <= 4.0)
    fl = np.median(P[~on])
    d = lambda v: round(float(10 * np.log10(max(v, 1e-300))), 2)
    return dict(dc_db=d(abs(x.mean()) ** 2), ac_db=d(np.mean(np.abs(a) ** 2)),
                comb_excess_db=d(max(P[on].sum() - fl * on.sum(), 0)) - d(a.size),
                floor_db=d(fl * P.size) - d(a.size),
                above_ftip_pct=round(100 * float(P[fa >= FTIP].sum() / P.sum()), 2),
                lag1_corr=round(float(abs(np.vdot(a[:-1], a[1:])) / np.vdot(a, a).real), 4),
                n_unique=int(np.unique(x).size))


K = {"ps_off_az0_el0": "sionna_p4000000000_r15_n8192_d1/el+0",
     "ps_off_az45_el0": "sionna_p4000000000_r15_n8192_az45_d1/el+0",
     "ps_off_propsonly_az0_el0": "sionna_p4000000000_partsprop_r15_n8192_d1/el+0",
     "ps_off_noprops_az0_el0": "sionna_p4000000000_partsnoprop_r15_n8192_d1/el+0",
     "ps_on_az0_el0": "sionna_p4000000000_phys_r15_n8192_d1/el+0",
     "ps_on_az45_el0": "sionna_p4000000000_phys_r15_n8192_az45_d1/el+0",
     "ours_az0_el0": "ours_r15_n8192/el+0", "ours_az45_el0": "ours_r15_n8192_az45/el+0",
     "ours_az0_el-60": "ours_r15_n8192/el-60", "ours_az45_el-60": "ours_r15_n8192_az45/el-60"}
S = {n: stat(k) for n, k in K.items()}

FAC = json.load(open(f"{ROOT}/outputs/az_falsify_facets.json"))
PO = json.load(open(f"{ROOT}/outputs/az_falsify_po.json"))

out = {"_meta": {
    "generator": "benchmark/az_falsify_verdict.py",
    "gpu_ko": "⛔GPU 안 씀 — sionna.rt·mitsuba 임포트 없음.",
    "inputs": ["outputs/elevation_sweep_md.npz", "outputs/az_falsify_facets.json",
               "outputs/az_falsify_po.json", "outputs/switch_factorial.json",
               "outputs/grid_convergence_check.json"],
    "grid_band_db": 3.861, "f_flash_hz": FFL, "f_tip_el0_hz": FTIP, "prf_hz": PRF},
    "series_stats": S,
    "kill_1_az0_is_noise_not_signal": {
        "ko": "az0·el0 의 «움직이는 부분» 은 물리 신호가 아니라 백색 수치잡음이다.",
        "lag1_az0": S["ps_off_az0_el0"]["lag1_corr"],
        "lag1_az45": S["ps_off_az45_el0"]["lag1_corr"],
        "lag1_propsonly": S["ps_off_propsonly_az0_el0"]["lag1_corr"],
        "above_ftip_pct_az0": S["ps_off_az0_el0"]["above_ftip_pct"],
        "above_ftip_pct_az45": S["ps_off_az45_el0"]["above_ftip_pct"],
        "comb_over_floor_db_az0": round(S["ps_off_az0_el0"]["comb_excess_db"]
                                        - S["ps_off_az0_el0"]["floor_db"], 2),
        "comb_over_floor_db_az45": round(S["ps_off_az45_el0"]["comb_excess_db"]
                                         - S["ps_off_az45_el0"]["floor_db"], 2),
        "why_ko": "이웃 표본 상관 0.01 = 51 µs 만에 완전히 딴 값. 날개끝 도플러 1272.9 Hz 로는 "
                  "불가능하다(그 정도면 ~15 표본 동안 매끄러워야 한다). 게다가 전력의 86.2 % 가 "
                  "날개끝 상한 **위** 에 있다 — 드론의 어떤 점도 그보다 빨리 못 움직인다."},
    "kill_2_az45_residual_is_the_propeller": {
        "ko": "az45 에 남은 것은 «에코 부재» 가 아니라 **순수 프로펠러 에코** 다.",
        "comb_az45_full_db": S["ps_off_az45_el0"]["comb_excess_db"],
        "comb_propsonly_az0_db": S["ps_off_propsonly_az0_el0"]["comb_excess_db"],
        "gap_db": round(S["ps_off_az45_el0"]["comb_excess_db"]
                        - S["ps_off_propsonly_az0_el0"]["comb_excess_db"], 2),
        "noprops_dc_db": S["ps_off_noprops_az0_el0"]["dc_db"],
        "full_dc_db": S["ps_off_az0_el0"]["dc_db"],
        "noprops_ac_db": S["ps_off_noprops_az0_el0"]["ac_db"],
        "noprops_n_unique_over_8192": S["ps_off_noprops_az0_el0"]["n_unique"],
        "prop_buried_under_az0_floor_db": round(S["ps_off_az0_el0"]["floor_db"]
                                                - S["ps_off_propsonly_az0_el0"]["comb_excess_db"], 2)},
    "kill_3_facet_lottery": {
        "ko": "동체 57 dB 하락은 «메쉬 삼각형이 마침 시선과 정확히 마주보느냐» 로 정확히 예측된다.",
        "aligned_area_el0_az0_cm2": 69.673, "aligned_area_el0_az45_cm2": 0.097,
        "aligned_faces_el0_az0": 90, "aligned_faces_el0_az45": 2,
        "groups_el0_az0": {"battery(내부)": 32.853, "camera": 34.14, "pcb(내부)": 2.68},
        "predicted_db_from_area_squared": -57.16,
        "observed_ps_off_d_dc_db": round(S["ps_off_az45_el0"]["dc_db"] - S["ps_off_az0_el0"]["dc_db"], 2),
        "axis_aligned_area_cm2": 981.2, "total_area_cm2": 3055.9,
        "horizontal_area_in_cardinal_1deg_bins_cm2": 387.729,
        "horizontal_area_total_cm2": 548.32,
        "cross_check_ko": "el −30·−60 에는 어느 방위에도 정렬 삼각형이 0 개 — 저장소의 "
                          "switch_factorial.json zero_echo_proof 가 순수 정반사 팔(R1D0E0F0)에서 "
                          "npaths=0 · E≡0 을 기록한 것과 같은 사실이다."},
    "kill_4_po_arbiter": {
        "ko": "제3의 심판(직접 짠 평면파 PO 적분)은 el0 에서 −0.09 dB 를 준다.",
        "po_el0_d_db": PO["po_vs_observed"]["el+0"]["po_d_az45_minus_az0_db"],
        "po_el0_nonprop_d_db": PO["po_vs_observed"]["el+0"]["po_nonprop_d_db"],
        "po_el0_az_spread_db": PO["po_vs_observed"]["el+0"]["po_az_spread_db"],
        "po_el-60_az_spread_db": PO["po_vs_observed"]["el-60"]["po_az_spread_db"],
        "plate_lobe": FAC["specular_lobe_estimate"]},
    "kill_5_ours_not_insensitive": {
        "ko": "«우리 커널은 3 dB 안» 도 무조건은 아니다 — el−60 의 가만히 있는 부분은 18 dB 올랐다.",
        "ours_el-60_d_dc_db": round(S["ours_az45_el-60"]["dc_db"] - S["ours_az0_el-60"]["dc_db"], 2),
        "ours_el-60_d_ac_db": round(S["ours_az45_el-60"]["ac_db"] - S["ours_az0_el-60"]["ac_db"], 2),
        "ours_el-60_az0_dc_db": S["ours_az0_el-60"]["dc_db"],
        "ours_el0_az0_dc_db": S["ours_az0_el0"]["dc_db"],
        "why_ko": "az0·el−60 이 간섭 골(−72.03 dB, 이웃 앙각보다 18 dB 낮다)이고 az45 가 정상값이다. "
                  "PO 훑기로 재면 이 앙각의 방위 글린트 산포가 21 dB — 방위 두 점으로는 아무것도 못 잰다."},
    "verdict_ko": [
        "«45° 돌리면 PathSolver 정면 에코가 25~51 dB 사라진다» 는 성립하지 않는다.",
        "−51 dB 는 신호가 아니라 **잡음 바닥** 이 무너진 값이다(바닥 −78.9 dB, 빗살은 az0 에서 아예 측정 불가).",
        "az45 에 남은 −145 dB 는 프로펠러 에코이고, 프로펠러만 돌린 대조군과 0.73 dB 차이다.",
        "동체 57 dB 하락은 정렬 삼각형 면적비의 제곱(−57.16 dB)과 0.09 dB 안에서 같다 — 기하가 아니라 **메쉬 축정렬** 이다.",
        "물리켬 팔의 −25.4 dB 는 두 방위 다 백색(이웃상관 0.014 · 0.065)이라 잡음 대 잡음이다 — 의미 없다.",
        "«우리 커널은 방위에 둔감» 도 el−60 에서 깨진다(가만히 있는 부분 +18.05 dB).",
    ]}
json.dump(out, open(f"{ROOT}/outputs/az_falsify_verdict.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k.startswith("kill") or k == "verdict_ko"},
                 ensure_ascii=False, indent=1))
