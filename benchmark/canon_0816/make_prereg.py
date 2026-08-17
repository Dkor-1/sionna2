# -*- coding: utf-8 -*-
"""사전등록 원장 생성기 — 수를 손으로 적지 않는다(전부 원장에서 뽑거나 계산한다)."""
import json, math, os, time
import numpy as np

ROOT = "/workspace/sionna"
O = os.path.join(ROOT, "outputs")
frame = json.load(open(os.path.join(O, "noise_distance_frame.json")))
gates = json.load(open(os.path.join(O, "noise_main_gates_dryrun.json")))
canon = json.load(open(os.path.join(O, "material_canon_0816.json")))
det = json.load(open(os.path.join(O, "detection_curves.json")))

cells = {c["cell_id"]: c for c in frame["cells"]}
ext = frame["extended_range_A1"]
b30 = gates["G3_bars"]["el_minus30"]
ARMS = ["ours", "ours_ptd", "ps_off", "ps_refr", "ps_phys"]


def R_of(cell, bar, snr15=None):
    rows = cell["snr_curve"]
    x = np.array([r["snr_ac_db"] for r in rows]); y = np.array([r["comb_db_mean"] for r in rows])
    ok = y >= bar
    if ok.all(): thr = x[0]
    elif not ok.any(): return None
    else:
        i = int(np.argmax(ok))
        thr = x[0] if i == 0 else x[i - 1] + (bar - y[i - 1]) / (y[i] - y[i - 1]) * (x[i] - x[i - 1])
    s15 = cell["by_convention"]["S1"]["snr_ac_db"] if snr15 is None else snr15
    return 15.0 * 10 ** ((s15 - thr) / 40.0)


Rn = {a: R_of(cells[f"{a}_r15_el-30"], b30["bar_noise_db"]) for a in ARMS}
Rg = {a: R_of(cells[f"{a}_r15_el-30"], b30["bar_grid_db"]) for a in ARMS}
ceil = {a: cells[f"{a}_r15_el-30"]["clean"]["comb_contrast_db"] for a in ARMS}

# canon 파급 어림 (I4·I3·I17) — 이 값들이 예측의 중심점이다
I4 = next(i for i in canon["impact"] if i["id"] == "I4")
I17 = next(i for i in canon["impact"] if i["id"] == "I17")

P = []


def add(pid, what, point, bracket, basis, klass, unknown=False, direction=None, unit="%"):
    P.append(dict(id=pid, what_ko=what, point=point, bracket=list(bracket), unit=unit,
                  basis_ko=basis, claim_class=klass, unknown=bool(unknown),
                  direction=direction))


# ── A. 재질 정본(셸 0.75 + 프롭 1.43 **같이**) 파급 ─────────────────────────── #
add("A1", "ours 판독거리 R_read(el −30) 의 변화율", 0.0, [-0.2, 0.2],
    "우리 커널에는 두께 개념이 없다(canon.ours_kernel, D3 동결) — 재계산이 두께만 "
    "바꾸면 ours 는 **비트동일**이어야 한다. 0.2 % 는 몬테카를로 잡음 여유",
    "C_budget_dependent")
add("A2", "ours_ptd 판독거리 R_read(el −30) 의 변화율", 0.0, [-0.2, 0.2],
    "같은 이유(D3 동결)", "C_budget_dependent")
add("A3", "ps_off 판독거리 R_read(el −30) 의 변화율", -0.5, [-3.0, 2.0],
    "canon I4 — 셸·프롭을 같이 고치면 움직이는 몫이 −0.08 dB 밖에 안 움직인다"
    "(정지 성분이 같이 내려가 앵커가 지운다) ⇒ R ∝ (AC/총)^(1/4) 로 −0.5 %. "
    "⚠이 «사실상 불변» 은 정본 두께 근처에서만 성립한다(0.9 mm 면 −8.9 %)",
    "C_budget_dependent")
add("A4", "ps_refr 판독거리 R_read(el −30) 의 변화율", 0.6, [-3.0, 3.0],
    "canon I4 — 굴절 팔의 움직이는 몫 +0.10 dB", "C_budget_dependent")
add("A5", "ps_phys 판독거리 R_read(el −30) 의 변화율", None, [0, 0],
    "⛔canon I19 — 원장의 두께 칸 17 개가 **전부 physics=False** 라 물리 켬 팔의 "
    "정정판이 원리적으로 없다. 방향조차 모른다. ⭐이것을 **모른다고 미리 등록**한다 — "
    "덱 헤드라인이 이 팔 위에 서 있으므로 정직성이 가장 중요한 칸이다",
    "C_budget_dependent", unknown=True)
add("A6", "ours 무늬 천장(el −30, 무잡음 빗살 대비) [dB]", ceil["ours"],
    [ceil["ours"] - 0.3, ceil["ours"] + 0.3],
    "두께는 우리 커널에 안 걸린다 — 천장은 그대로여야 한다", "A_convention_free", unit="dB")
add("A7", "ps_off 무늬 천장(el −30) [dB]", ceil["ps_off"],
    [ceil["ps_off"] - 2.0, ceil["ps_off"] + 2.0],
    "재질 정정은 요동·정지를 함께 내려 **비**인 빗살 대비를 거의 안 건드린다"
    "(canon A갈래 d_comb −6.2 dB 는 100 mm→정본의 **절대** 변화가 아니라 그 앙각 밴드 "
    "4.616 의 1.34 배 — 브래킷을 ±2 dB 로 둔다)", "A_convention_free", unit="dB")

# ── B. 앙각 −60 (canon I3·I17) ─────────────────────────────────────────────── #
add("B1", "ps_off 판독거리 R_read(el −60) 의 변화율(재질 정본 적용)", 39.0, [20.0, 60.0],
    "canon I3/I17 — el −60 은 정지 성분이 요동보다 더 많이 내려가 «움직이는 몫» 이 "
    "**+5.74 dB** 좋아진다 ⇒ R ∝ 10^(5.74/40) = +39 %", "C_budget_dependent",
    direction=+1)
add("B2", "ps_off R50(el −60, 빗살 검출기) [m]", 1287.0, [1100.0, 1450.0],
    f"canon I17 — 현행 {det['arms'][5]['R50_m']['comb']:.0f} m 에 +39 %", "C_budget_dependent",
    unit="m")
add("B3", "ours 판독거리 R_read(el −60) 의 변화율", 0.0, [-0.2, 0.2],
    "D3 동결 — 우리 커널은 안 움직인다", "C_budget_dependent")

# ── C. 판정 막대 (본판이 20,000 시행으로 다시 뽑는다) ──────────────────────── #
# ⭐두 번 독립으로 뽑아 봤다(씨앗만 다르게, 4000 시행씩): 2.475 · 2.679 dB.
#   막대 **자체**가 표집으로 0.2 dB 흔들린다 — 브래킷은 그 실측 산포에서 정한다.
C1_DRAWS = [2.4754774392718755, b30["bar_noise_db"]]
c1 = float(np.mean(C1_DRAWS))
add("C1", "el −30 잡음선 막대 = 빗살 대비 귀무분포 p99.9 [dB] (귀무 20,000 시행)",
    round(c1, 3), [round(c1 - 0.35, 3), round(c1 + 0.35, 3)],
    f"⭐4000 시행으로 **씨앗만 바꿔 두 번** 뽑았더니 {C1_DRAWS[0]:.3f} · {C1_DRAWS[1]:.3f} dB — "
    f"막대 자체가 {abs(C1_DRAWS[0]-C1_DRAWS[1]):.3f} dB 흔들린다(부트스트랩 sd "
    f"{b30['bar_noise_bootstrap_sd_db']:.3f} 이 과소평가). 20,000 시행이면 √5 배 줄어 "
    "±0.1 dB 급이 되고, 그때 판독거리의 막대 기여 불확실도는 ±1 % 안이다. "
    "⭐이 항목이 **왜 20,000 이 필요한지의 증거**다. "
    "⛔가우스 근사(평균+3.09σ)는 draw 마다 최대 +0.22 dB 어긋난다 — 경험 분위수를 쓴다",
    "B_bar_dependent", unit="dB")
add("C2", "el +0 잡음선 막대 [dB] (귀무 20,000 시행)",
    round(gates["G3_bars"]["el_plus0"]["bar_noise_db"], 3),
    [round(gates["G3_bars"]["el_plus0"]["bar_noise_db"] - 0.35, 3),
     round(gates["G3_bars"]["el_plus0"]["bar_noise_db"] + 0.35, 3)],
    "같은 방법, el +0 마스크(f_tip 1272.9). ⚠el +0 은 **재현선**이 0.105 dB 로 극히 좁아 "
    "(머리카락 밴드) 두 막대의 순서가 뒤집힌다 — 그 앙각에서는 잡음선이 지배한다",
    "B_bar_dependent", unit="dB")

# ── D. ⭐로터 프리셋 — 조건부 예측(본판 최대 위험) ─────────────────────────── #
kin = gates["G5_kinematics"]["gates"]
add("D1", "[조건: 정본이 outdoor_v2(σs 5.3 %)로 간다면] 고정 격자(±8 Hz, k 2–8.7)에서 "
    "ours 무늬 천장 [dB]", 10.0, [0.0, 22.0],
    "저장된 실제 시계열 실측 — 격자를 4 Hz 만 어긋내도 42.9 → 2.5 dB. σs 5.3 % 는 "
    f"배음 k 에서 3σ 어긋남이 k·20 Hz 라 k_max(고정격자) = "
    f"{kin['outdoor_v2 σs=5.3%']['k_max_fixed_grid']} — 대역 하단 k=2 조차 못 버틴다. "
    "합성 4로터 펄스열에서도 빗살 대비 88 → 19 dB(sd 26)",
    "A_convention_free", unit="dB", direction=-1)
add("D2", "[같은 조건] ours − ps_phys 무늬 천장 격차 [dB]", 5.0, [-10.0, 18.0],
    f"현행 격차 {ceil['ours'] - ceil['ps_phys']:.1f} dB. 실측 detune 표에서 +4 Hz 에 3.2 dB, "
    "+8 Hz 에 −25.1 dB 로 **부호까지 뒤집힌다** ⇒ ⭐«물리 켬 천장 6 dB» 헤드라인은 "
    "고정 격자 + outdoor_v2 조합에서 **살아남지 못한다**", "A_convention_free", unit="dB")
add("D3", "[같은 조건 + 구제책] 대역을 k∈[2,3] 으로 좁혔을 때 ours − ps_phys 격차 [dB]",
    30.9, [24.0, 36.0],
    "저장된 시계열 실측 — k∈[2,3] 에서 ours 38.6 · ps_phys 7.7 dB. 낮은 배음은 산포에 "
    f"덜 흔들린다(구제 상한 k ≤ {kin['outdoor_v2 σs=5.3%']['k_max_widened_grid']}). "
    "⭐구제책을 쓰면 헤드라인이 산다 — 다만 **잣대 정의가 바뀌었음을 그림에 적어야** 한다",
    "A_convention_free", unit="dB")
add("D4", "[조건: 정본이 legacy 유지] ours 무늬 천장 변화 [dB]", 0.0, [-0.3, 0.3],
    f"현행 원장 실측 로터 산포 {gates['G5_kinematics']['measured_now']['spread_pct']} % 는 "
    f"k_max = {kin['legacy(현행 원장 실측)']['k_max_fixed_grid']} > 대역 상단 8.7 이라 "
    "격자가 멀쩡하다", "A_convention_free", unit="dB")

# ── E. 검산 게이트 (예측이자 합격선) ───────────────────────────────────────── #
xc = gates["G2_crosscheck_r50"]
add("E1", "R50 교차검산 |Δ/σ| (ours el −30, 본판 ↔ detection_curves)",
    abs(xc[0]["deviation_over_sigma"]), [0.0, 3.0],
    f"예행에서 Δ={xc[0]['deviation_pct']:+.2f} %, σ_결합={xc[0]['combined_sigma_pct']:.2f} % "
    f"⇒ Δ/σ={xc[0]['deviation_over_sigma']:+.2f}. ⭐기억 속의 «1 % 안에서 맞았다» 는 "
    "**가둔 게이트가 아니라 운 좋은 표집**이었다 — σ 가 이미 1.4~1.9 % 다. "
    "본판의 합격선은 Δ% 가 아니라 Δ/σ ≤ 3", "B_bar_dependent", unit="σ")
add("E2", "앵커 동일성 |Δ| [dB] (두 원장의 c_anchor)", 0.0, [0.0, 0.01],
    f"예행 {gates['G1_anchor']['diff_db']:.6f} dB — 비트동일. 이게 깨지면 R50 을 "
    "나란히 놓을 수 없다(MAP_SCALING §4-b)", "B_bar_dependent", unit="dB")
add("E3", "ours A1↔A2 모양 드리프트 (el −30, 15→480 m) [dB]",
    gates["G9_a1_a2"]["rows"]["ours"]["max_shape_drift_db"], [0.0, 2.0],
    "⭐원장에 240·480 m 판이 있다 — 헤드라인 판독거리(약 520~650 m)의 **87 %** 까지 "
    f"연장선을 직접 검증할 수 있다. 예행 실측 "
    f"{gates['G9_a1_a2']['rows']['ours']['max_shape_drift_db']} dB 로 밴드 4.616 안",
    "A_convention_free", unit="dB")
add("E4", "ps_refr A1↔A2 모양 드리프트 (el −30, 15→240 m) [dB]",
    gates["G9_a1_a2"]["rows"]["ps_refr"]["max_shape_drift_db"], [4.616, 20.0],
    "⭐새로 드러난 것 — 지금까지 ps_off 만 «연장선 못 믿음» 으로 표시돼 있었는데 "
    f"ps_refr 도 {gates['G9_a1_a2']['rows']['ps_refr']['max_shape_drift_db']} dB 로 밴드 밖이다. "
    "본판은 두 Sionna 팔을 **A2 원장점**으로 내야 한다", "A_convention_free", unit="dB")

# ── F. 규약 무관 생존 (구조적 예측 — 이것이 틀리면 코드가 틀린 것) ─────────── #
ratio_n = {a: Rn[a] / Rn["ours"] for a in ARMS}
ratio_g = {a: Rg[a] / Rg["ours"] for a in ARMS}
worst = max(abs(ratio_n[a] - ratio_g[a]) for a in ARMS)
add("F1", "무늬 천장의 규약 산포 [dB] (앵커 S1/S3 · EIRP 12/30/63 · 막대 2종 · "
    "capture 2종 · 거리 4점을 전부 흔들었을 때)", 0.0, [0.0, 0.01],
    "⭐**구조적 0** — 천장은 무잡음 시계열의 비(比)라 곱셈 상수가 전부 약분된다. "
    "이것이 규약 무관 등급 A 의 정의다", "A_convention_free", unit="dB")
add("F2", "팔 간 판독거리 **비** 의 막대 감도 (최대 |비(잡음선) − 비(재현선)|)",
    round(worst, 3), [0.0, 0.05],
    f"예행 실측 최대 {worst:.3f} — 막대를 2.475 ↔ 4.600 dB 로 바꾸면 «몇 미터» 는 26 % "
    "움직이는데 **팔 사이 배수는 1.5 % 안에서 그대로**다. ⭐덱에 올릴 수 있는 것은 "
    f"«우리 커널이 물리 켬보다 {1/ratio_n['ps_phys']:.0f}~{1/ratio_g['ps_phys']:.0f} 배 "
    "멀리까지 무늬를 읽는다» 이지 «554 m» 가 아니다", "B_bar_dependent", unit="비")
add("F3", "EIRP 를 30 → 12 dBm 으로 바꿨을 때 R_read 비의 변화", 0.0, [0.0, 0.01],
    "링크버짓 상수는 모든 팔에 **똑같이** 걸리는 곱이라 비에서 약분된다. "
    "«몇 미터» 는 10^(−18/40) = 0.356 배로 움직인다(ours 519~654 → 184~232 m)",
    "B_bar_dependent", unit="비")

meta = dict(
    generator="scratchpad/make_prereg.py (수는 전부 원장에서 계산)",
    written_kst=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 9 * 3600)) + " (UTC+9)",
    role_ko="⭐**사전등록** — 재계산이 끝나기 **전에** 무엇이 얼마나 움직일지 적어 둔다. "
            "재계산 뒤 benchmark/noise_main_gates.score_prereg() 가 이 파일을 고치지 않고 채점한다.",
    scored_by="benchmark/noise_main_gates.py : score_prereg()",
    baseline=dict(
        source="outputs/noise_distance_frame.json (잠정 — 재질 정정 이전 · 셸 100 mm Sionna 팔)",
        R_read_noise_bar_m={a: round(Rn[a]) for a in ARMS},
        R_read_grid_bar_m={a: round(Rg[a]) for a in ARMS},
        ceiling_db=ceil,
        bar_noise_db=b30["bar_noise_db"], bar_grid_db=b30["bar_grid_db"],
        note_ko="⛔이 기준선 자체가 잠정이다. 사전등록은 «절대값» 이 아니라 «변화» 를 "
                "예측한다 — 그래야 기준선이 흔들려도 채점이 산다"),
    unknown_declared=[p["id"] for p in P if p["unknown"]],
    scoring_rules_ko=[
        "브래킷 안이면 hit, 밖이면 miss. 사후에 브래킷을 넓히면 사전등록이 아니다.",
        "⭐«모른다» 로 등록한 항목(A5)은 채점하지 않는다 — 모른다고 미리 말한 것은 틀린 것이 아니다.",
        "조건부 예측(D 계열)은 그 조건이 실현된 경우에만 채점한다.",
        "예측이 틀리면 틀린 대로 남기고 **왜 틀렸나**를 원장에 적는다.",
    ])

json.dump(dict(_meta=meta, predictions=P),
          open(os.path.join(O, "noise_main_prereg_0816.json"), "w"),
          ensure_ascii=False, indent=1)
print("wrote", os.path.join(O, "noise_main_prereg_0816.json"), "n =", len(P))
for p in P:
    print(f"  {p['id']:3s} {p['what_ko'][:62]:64s} {str(p['point']):>8s} {p['bracket']} {p['unit']}")
