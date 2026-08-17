# -*- coding: utf-8 -*-
"""재질 정본 확정자 — 네 갈래 판정(사다리·H5굴절·각도·기체교차)을 모아 정본 원장을 낸다.
⛔GPU 0 · 저장된 원장만 읽는다 · 코드/프리셋 안 건드림."""
import json, math, os, datetime

ROOT = "/workspace/sionna"
OUT  = os.path.join(ROOT, "outputs")

def L(name): return json.load(open(os.path.join(OUT, name), encoding="utf-8"))
def lin(d):  return 10.0**(d/10.0)
def db(x):   return 10.0*math.log10(x)
def r4(x):   return round(x, 4) if isinstance(x, float) else x

lad = L("material_canon_0816_ladder.json")
h5  = L("material_canon_0816_h5_refraction.json")
ang = L("material_canon_0816_angles.json")
afr = L("material_canon_0816_airframes.json")
mv  = L("material_verdict_0816.json")
det = L("detection_curves.json")
ndf = L("noise_distance_frame.json")
cla = L("classify_airframe.json")
mdc = L("md_classify.json")

# ── 파생 계산 ①: 움직이는 몫(AC/총) — 앵커가 총 σ 를 누르므로 절대 거리는 이 비에 탄다
def ratio(ac, dc): return ac - db(lin(ac) + lin(dc))

cells_ang = ang["cells"]
def cell(k): 
    c = cells_ang[k]; return c["ac_power_db"], c["dc_power_db"]

moving_share = {}
for el, base_k, canon_k in [("el+0","base_100mm/el+0","prop1.43mm_canon/el+0"),
                            ("el-30","base_100mm/el-30","prop1.43mm_canon/el-30"),
                            ("el-60","base_100mm/el-60","prop1.43mm_canon/el-60")]:
    ab, dbase = cell(base_k); ac_, dc_ = cell(canon_k)
    rb, rc = ratio(ab, dbase), ratio(ac_, dc_)
    tb = db(lin(ab)+lin(dbase)); tc = db(lin(ac_)+lin(dc_))
    moving_share[el] = {
        "base_ac_over_total_db": r4(rb), "canon_ac_over_total_db": r4(rc),
        "d_ac_over_total_db": r4(rc-rb), "d_total_sigma_db": r4(tc-tb),
        "distance_factor": r4(10.0**((rc-rb)/40.0)),
        "distance_pct": r4(100.0*(10.0**((rc-rb)/40.0)-1.0)),
    }
d30_tot = moving_share["el-30"]["d_total_sigma_db"]
for el in moving_share:
    moving_share[el]["post_anchor_residual_db"] = r4(moving_share[el]["d_total_sigma_db"] - d30_tot)

# 사다리 전체(el −30)의 움직이는 몫
lad_arms = lad["el_minus30_ladder"]["arms"]
ladder_share = {}
r_base = ratio(lad_arms["base_100mm"]["ac_power_db"], lad_arms["base_100mm"]["dc_power_db"])
for k, v in lad_arms.items():
    r = ratio(v["ac_power_db"], v["dc_power_db"])
    ladder_share[k] = {"ac_over_total_db": r4(r), "d_vs_base_db": r4(r-r_base),
                       "distance_pct": r4(100.0*(10.0**((r-r_base)/40.0)-1.0))}

# 굴절만 팔(ps_refr 거리 인용의 근거 칸)
hc = h5["cells"]
def hcell(k): return hc[k]["ac_power_db"], hc[k]["dc_power_db"]
refr_share = {}
for label, k in [("refr_100mm","sionna_p4000000000_onlyrefr_r15_n8192/el-30"),
                 ("refr_shell0.75_prop0.9","sionna_p4000000000_onlyrefr_r15_n8192_shell0.75mm_prop0.9mm/el-30"),
                 ("refr_shell0.75_prop1.43","sionna_p4000000000_onlyrefr_r15_n8192_shell0.75mm_prop1.43mm/el-30")]:
    a, d_ = hcell(k); refr_share[label] = {"ac_db": a, "dc_db": d_, "ac_over_total_db": r4(ratio(a, d_))}
rb_r = refr_share["refr_100mm"]["ac_over_total_db"]
for k in refr_share:
    dd = refr_share[k]["ac_over_total_db"] - rb_r
    refr_share[k]["d_vs_100mm_db"] = r4(dd)
    refr_share[k]["distance_pct"] = r4(100.0*(10.0**(dd/40.0)-1.0))

# ── 파생 계산 ②: R50 브래킷 — 셸 정책에 따라 갈린다
R50 = 723.7
dAC_canon = lad["canon_1p43mm_headline"]["d_ac_power_db"]      # -13.019
AC0, DC0 = cell("base_100mm/el-30")
def r50_after(dac, ddc, ac0=AC0, dc0=DC0, R0=R50):
    r0 = ratio(ac0, dc0); r1 = ratio(ac0+dac, dc0+ddc)
    return {"d_moving_share_db": r4(r1-r0), "R_m": round(R0*10.0**((r1-r0)/40.0), 1),
            "pct": r4(100.0*(10.0**((r1-r0)/40.0)-1.0))}
# 우리 커널의 AC:DC 균형(앵커 원장 실측: AC/총 −5.6227 dB)
ours_share_db = det["arms"][0]["sigma_ac_mean_anchored_dbsm"] - det["arms"][0]["sigma_mean_anchored_dbsm"]
f_ac = lin(ours_share_db); f_dc = 1.0 - f_ac
def r50_after_ours(dac, ddc, R0=R50):
    a1 = f_ac*lin(dac); d1 = f_dc*lin(ddc)
    r1 = db(a1/(a1+d1)); r0 = db(f_ac/(f_ac+f_dc))
    return {"d_moving_share_db": r4(r1-r0), "R_m": round(R0*10.0**((r1-r0)/40.0), 1),
            "pct": r4(100.0*(10.0**((r1-r0)/40.0)-1.0))}

r50_bracket = {
  "what_ko": "R50 은 앵커 뒤 «움직이는 몫(AC/총 σ)» 위에 서고 1/R⁴ 이므로 R ∝ (AC/총)^(1/4) 이다. 그래서 정정 크기가 아니라 **셸과 프롭을 같이 고치느냐**가 답을 정한다.",
  "current_R50_m": R50, "current_band_metric_R50_m": 567.0,
  "measured_sionna_arm_shell_and_prop_together": r50_after(dAC_canon, -12.825),
  "hypothetical_prop_only_dc_unchanged_upper": r50_after(dAC_canon, 0.0),
  "ours_balance_shell_and_prop_together": r50_after_ours(dAC_canon, -12.825),
  "ours_balance_prop_only_dc_unchanged": r50_after_ours(dAC_canon, 0.0),
  "old_estimate_ko": "§4-1 #3 의 «프롭 1.43 mm 병행 → 약 475 m(−34 %)» 는 수직입사 슬래브 −7.72 dB 위에 서 있었다. 정본 실측은 −13.02 dB(유효 입사각 40.2°)라 **더 크다**.",
  "ruling_ko": "⭐«−34 %» 는 지금 상태로 다시 인용하면 안 된다. 다시 계산해야 하고, 그 계산은 반드시 **셸 정책**(같이 고치나·프롭만 고치나)을 문장에 적어야 한다.",
}

meta = {
  "generator": "scratchpad/build_material_canon.py (재질 정본 확정자)",
  "date_kst": datetime.datetime.utcnow().strftime("%Y-%m-%d") ,
  "written_at_kst": "2026-08-16 20:5x KST",
  "role_ko": "네 갈래 판정(프로펠러 두께 사다리 · H5 투과 반대항 · 각도 확장 · 기체 교차)을 모아 **앞으로 모든 실험이 쓸 재질 정본**을 확정한다",
  "gpu_used": False,
  "gpu_note_ko": "sionna.rt·mitsuba·torch 임포트 없음. 저장된 원장만 읽었다(⛔GPU 금지 준수).",
  "inputs": [
    "outputs/material_canon_0816_ladder.json", "outputs/material_canon_0816_h5_refraction.json",
    "outputs/material_canon_0816_angles.json", "outputs/material_canon_0816_airframes.json",
    "outputs/material_verdict_0816.json (08-16 오전 판)",
    "outputs/elevation_sweep_md.{json,npz} (2026-08-16 19:5x KST 병합본 — 네 갈래가 읽은 원본)",
    "outputs/detection_curves.json · noise_distance_frame.json · classify_airframe.json · md_classify.json (파급 대상의 현재 값)",
    "docs/MATERIAL_CORRECTION.md §2-1·§2-4·§4·§6·§10",
  ],
  "scope_ko": "이 정본은 **두께 축**(Sionna 팔의 셸·프로펠러)만 확정한다. 우리 커널 |Γ|=0.28 은 D3 동결 그대로이고, absorber·camera_assembly 등 다른 재질 축은 이 정본 밖이다.",
}

canon = {
  "sionna_shell_mm": {
    "value": 0.75,
    "sensitivity_axis_measured": [0.5, 0.75, 1.5],
    "sensitivity_axis_planned_not_landed": [3.0],
    "source_ko": "DJI Matrice 4T 공식 CAD 실측(TOPCOVER/BOTCOVER 벽 두께, 중앙값 0.704 mm) — MATERIAL_CORRECTION §1-5 · benchmark/measure_m4t_wall_thickness.py",
    "status_ko": "실측 정본. 세 점(0.5/0.75/1.5)이 실제로 돌았고 정지 성분(DC) 축에서 단조 + 슬래브 정합(셸 몫 s≈0.74~0.83, 잔차 ≤0.9 dB)."
  },
  "sionna_prop_mm": {
    "value_by_airframe": {"matrice4e": 1.4302, "mini5pro": 0.7955, "s1000plus": 1.9887},
    "headline_value": 1.43,
    "sensitivity_ladder_measured": [0.5, 0.9, 1.43, 2.0],
    "source_ko": "우리 메쉬 자신의 시위평균 두께(material_sources.json : propeller.per_drone.t_chordmean_mm) — 감사 원장 outputs/mesh_audit_0816_prop_geometry.json",
    "status_ko": "정본 실측 완료(matrice4e 1.43 mm 점을 직접 쟀다). mini5pro·s1000plus 의 정본 점은 **미실측**이고 사다리 보간 추정뿐이다.",
    "residual_ko": "⚠D2 규약대로 이 값은 «우리 메쉬의 두께» 이지 DJI 실물 두께가 아니다. 실물이 더 얇다는 것은 **메쉬 층 결함**으로 남고(같은 잣대로 +1.2~+1.7 dB), 재질 손잡이로는 안 닫힌다."
  },
  "ours_kernel": {
    "gamma_abs": 0.28, "thickness": None,
    "status_ko": "⭐D3 동결 유지 — 우리 커널에는 두께 개념 자체가 없어 이 축은 **구조적 N/A** 다. 그러므로 이 정본은 **오늘 우리 커널 수치를 하나도 안 바꾼다**. 바꾸는 것은 (b) 착수 뒤다.",
  },
  "planned_vs_actual_ko": "§2-3 계획 축(셸 0.75/1.5/3.0)과 실제 돈 축(셸 0.5/0.75/1.5 · 프롭 0.5/0.9/1.43/2.0)이 다르다. 정본 값은 계획대로(셸 0.75 · 프롭 1.43)이고, 민감도 축만 실제 돈 것으로 갈아 적는다.",
}

why_shell = {
  "one_paragraph_ko": (
    "껍데기(셸)를 안 건드려도 되는 이유는 «작아서» 가 아니라 **표적 축에 배선이 없어서**다. 우리가 헤드라인으로 "
    "쓰는 잣대는 전부 정지 성분(DC)을 걷어낸 뒤의 «움직이는 부분» — 확산 바닥·빗살 대비·리듬 몫·박자·맵 상관 —"
    "인데, 셸은 기체에 붙어 같이 움직이지 않는 정지 구조물이라 그 에코가 통째로 DC 로 간다. 실제로 셸만 100 mm → "
    "0.75 mm 로 얇게 하면 빗각(el −30)에서 정지 성분은 6.24 dB 내려가지만 요동은 **+0.002 dB**, 확산 바닥 −0.002 dB, "
    "빗살 +0.005 dB 이고 두 팔의 파형 상관이 **1.0000** 이다(같은 시드 짝지은 비교라 표집 요동이 소거된 «구조적 0»). "
    "정면(el 0)에서는 금속 거울이 판을 덮어 셸·프롭 둘 다 0.000 dB 다. 그래서 셸 두께는 **절대 레벨(σ)과 앵커에만** "
    "영향을 주고, 비(比)로 서는 모든 주장 — 무늬·분류·탐지 통계량 — 에는 안 들어온다. ⚠단 두 가지 단서: ⓐ 셸 단독 "
    "팔은 **matrice4e 한 기체에만** 착지했다(mini5pro·s1000plus 는 셸을 프롭과 함께 얇게 한 결합판뿐이라 분리 불가). "
    "ⓑ 절대 σ·앵커·거리를 말할 때는 셸이 오히려 **정지 성분의 대부분**이므로 «안 건드려도 된다» 가 아니다."
  ),
  "evidence": {
    "shell_only_el-30_d_ac_db": 0.002, "shell_only_el-30_d_floor_db": -0.002,
    "shell_only_el-30_d_comb_db": 0.005, "shell_only_el-30_d_dc_db": -6.24,
    "waveform_rho": 1.0, "stft_map_corr": 0.9998,
    "el0_all_metrics_db": 0.0,
  },
  "limits_ko": ["셸 단독 팔은 matrice4e 에만 있다 — 다른 두 기체의 «껍데기는 무관» 은 **판정 불가**다.",
                "굴절 켠 팔의 셸 단독 칸은 없다 — 굴절 채널에서 셸이 무관한지는 **안 쟀다**.",
                "el −90(천저)·−45·−75 에는 두께 칸이 아예 없다."],
}

protocol = {
  "dc_removal_ko": "모든 레벨 비교는 **정지 성분(DC) 제거 후**. 이 함정은 세 번 재발했다.",
  "band_by_elevation_ko": "격자 흔들림 밴드는 앙각마다 다르다 — «전 앙각 3.86» 은 정면 값이다. 아래 표를 쓴다.",
  "ac_grid_band_db_by_el": {"+0": 3.861, "-15": 1.318, "-30": 0.374, "-45": 0.091, "-60": 0.018, "-75": 0.104, "-90": 5.62},
  "floor_grid_band_db_by_el": {"+0": 6.363, "-15": 7.014, "-30": 9.295, "-45": 8.127, "-60": 5.797, "-75": 7.879},
  "comb_grid_band_db_by_el": {"+0": 0.105, "-15": 4.038, "-30": 4.616, "-45": 4.669, "-60": 4.053},
  "rhythm_grid_band_pp": 21.819, "above_ceiling_grid_band_pp": 12.5549, "beat_grid_band_hz": 0.152,
  "band_new_0816_ko": "⭐el −60 확산 바닥 밴드 5.797 dB 를 각도 갈래가 새로 냈다 — 오전 판이 빌려 쓴 «최대 9.295» 보다 좁다. el −60 채점은 새 값으로 다시 한다.",
  "hairline_band_rule_ko": "⭐밴드가 0.5 dB 보다 좁으면(el −60 요동 0.018 · el −45 0.091 · el −15 리듬 0.1 %p) 그 폭에 물리적 의미를 붙이지 않는다 — 빌려 온 시드 밴드(3sd 5.5 dB)도 함께 넘어야 «유의» 로 적는다.",
  "trim_ruling_ko": (
    "⭐**튀는 자세(이상값) 솎기 규약을 정본으로 못 박는다.** 자세열은 균일 시간 표본이라 가운데 한 자세를 "
    "**지우면** 뒤가 한 칸씩 당겨져 배음선이 번진다. 그래서 ⓐ 요동·확산 바닥·정지 성분에는 삭제·갈아끼움 어느 쪽도 "
    "안전하고(sd ≤ 0.04 dB), ⓑ **빗살 대비·리듬 몫에는 삭제를 쓰지 않는다** — 이웃 평균 **갈아끼우기**를 쓰거나 "
    "균일 재표집(반쪽·짝수/홀수)으로 검사한다."),
  "trim_evidence": {
    "random_delete_control_d_comb_sd_db": {"el-15": 2.025, "el-30": 2.255, "el-60": 0.458},
    "replace_control_max_effect_db": {"el-15": 0.095, "el-30": 0.143, "el-60": 0.012},
    "matrice4e_el-30_d_comb_db": {"raw": -6.98, "delete_k1": -3.434, "replace_k1": -6.954,
                                  "replace_k8": -6.42, "replace_k32": -5.03},
    "uniform_resample_d_comb_canon_db": [-6.31, -5.84, -6.22, -5.78],
  },
  "headline_trim_ko": "이번 정본의 헤드라인은 **원판(안 솎음)** 또는 **갈아끼움 k=1** 이다 — 두 값이 요동 축에서 0.01 dB 안에 같고, 네 갈래 어느 칸에도 튀는 자세가 없다(고립도 1.000~1.056, 문턱 2.0).",
  "comb_grid_tag_ko": "빗살 대비 **절대값**은 격자를 조일 때마다 +4.0~5.6 dB 단조 상승한다 — 절대 인용에는 항상 격자 꼬리표(λ/12)를 붙인다.",
  "slab_column_rule_ko": (
    "⭐**슬래브 예측을 인용할 때 어느 열을 쓰는지 규약으로 못 박는다.** ⓐ 정렬된 거울면(정반사·az45_el+0 같은 "
    "0.5° 안 정렬 삼각형)은 정의상 수직입사이므로 **수직입사 열**. ⓑ 빗각의 확산 표적 축(우리 헤드라인)은 "
    "**적합된 유효 입사각 열** — el −30 에서 40.2°(RMS 잔차 0.145 dB), el −60 에서 21.9°. ⛔**각도평균 열은 "
    "표적 축 인용에 쓰지 않는다**(정본에서 4.93 dB 어긋난다)."),
  "near_numeric_floor_ko": "AC/DC 가 1e-11 이하인 칸은 near_numeric_floor 로 표기하고 물리로 읽지 않는다.",
}

branches = {
  "A_프로펠러_두께_사다리": {
    "ledger": "outputs/material_canon_0816_ladder.json",
    "headline_ko": "정본 1.43 mm 에서 기본판(100 mm) 대비 **요동 −13.02 · 확산 바닥 −8.81 · 빗살 대비 −6.21 dB**(el −30). 네 두께 사다리는 완전 단조(뒤집힘 0).",
    "numbers": {"d_ac_db": {"0.5": -22.075, "0.9": -16.986, "1.43": -13.019, "2.0": -10.188},
                "d_floor_db": {"0.5": -17.396, "0.9": -12.556, "1.43": -8.810, "2.0": -6.181},
                "d_comb_db": {"0.5": -7.840, "0.9": -6.980, "1.43": -6.205, "2.0": -5.606}},
    "band_calls": {"ac": "밴드 밖(유의)", "floor": "밴드 안(판정 불가)", "comb": "밴드 밖(유의)", "rhythm": "밴드 안(판정 불가)"},
    "physics_ko": "요동 축은 프로펠러 플라스틱 평판의 두께 반사율 **그 자체**다 — 네 두께가 **유효 입사각 40.2°** 한 값에서 RMS 잔차 0.145 dB 로 닫히고, «두께로 안 줄어드는 몫» 은 −0.13 %(=0)다.",
    "caveat_ko": "⚠단조성 자체는 큰 발견이 아니다(다섯 팔의 경로수 중앙값이 1505 로 같은 «재질 계수 쓸기»). 새로 안 것은 **크기**와 **유효 입사각**이다. 확산 바닥은 «평판 반사 × 상한 위 몫» 의 합성 잣대라 유효 입사각이 64.5° 로 갈린다 — 평판 물리 대조에는 요동을 쓴다.",
  },
  "B_H5_투과_반대항": {
    "ledger": "outputs/material_canon_0816_h5_refraction.json",
    "headline_ko": "⛔**예측 반증(방향) + 기제 미측정.** 굴절 켠 팔은 «덜 어두워져야» 했는데 **더** 어두워진다(el −30, 0.9 mm 에서 −2.40 dB · 정본 1.43 mm 에서 −1.22 dB, 블록 부트스트랩 95 % 구간이 0 을 안 물린다).",
    "why_not_the_physics_ko": "두께 팔 11 개가 전부 **반사 깊이 1** 이다 — 뚫고 들어가 속 금속에 맞고 나오려면 상호작용이 두 번 필요하다. 100 mm 에서 굴절만 켜면 13 칸 중 12 칸이 어두워지고 경로 수가 13/13 에서 준다 ⇒ 깊이 1 의 굴절은 조명이 아니라 **에너지가 새는 구멍**이다.",
    "scope_ko": "게다가 굴절 팔의 두께 칸은 셸과 프롭을 **함께** 얇게 했다 — 예측은 «셸» 이야기였으므로 **셸 버전 H5 는 여전히 미측정**이다.",
    "ruling_ko": "⭐정본 판정: «투과 반대항은 없다» 로 넓혀 쓰지 않는다. 문면 채점은 **반증**, 기제는 **미측정**. 필요한 칸은 «얇은 셸 × 깊이 ≥2 × 셸만 × 굴절».",
  },
  "C_각도_확장": {
    "ledger": "outputs/material_canon_0816_angles.json",
    "headline_ko": "두께 효과는 앙각을 탄다 — 요동 축에서 −30° 가 가장 크고(−16.99 dB @0.9 mm) 그 각도 차이는 밴드 밖. 정면 0° 는 정본에서도 0.000 dB.",
    "el0_correction_ko": "⭐**정면 0° 를 «프롭이 영향 없다» 로 적으면 안 된다.** 두 팔의 잔차는 리듬 89.8 %·빗살 +48.4 dB 의 **완전한 날개 무늬**다 — 프롭 반사는 정면에도 멀쩡히 있고 두께 손잡이도 그것을 물었다. 안 보이는 이유는 그 몫이 이 칸 자신의 요동보다 **52~55 dB 아래**이고 그 요동 자체가 광선 추첨 잡음(리듬 13.06 % ≈ 백색 널 12.53 %)이기 때문이다.",
    "thin_plate_law_ko": "⭐0.9 → 1.43 mm 계단이 −30° 에서 +3.967 dB, −60° 에서 +3.966 dB (**0.001 dB 차**)로 얇은 판 법칙 20log10(1.43/0.9)=4.022 dB 와 맞는다 ⇒ 앙각 의존을 만드는 것은 얇은 판 물리가 아니라 **100 mm 기준팔**이다.",
    "comb_sign_flip_ko": "⚠빗살 대비는 −60° 에서 부호가 뒤집힌다(−15 −8.62 · −30 −6.95 · **−60 +1.65**, 밴드 안). «재질 정정이 빗살을 흐린다» 를 빗각 전부에 붙이면 틀린다.",
  },
  "D_기체_교차": {
    "ledger": "outputs/material_canon_0816_airframes.json",
    "headline_ko": "«프로펠러가 손잡이» 는 세 기체 모두 성립(날개선 −16.99 · −14.51 · −15.08 dB). 그러나 «확산 바닥이 프롭을 탄다» 는 **s1000plus 에서 반증**(−0.07 dB, 밴드 안)이고 정지 성분도 −0.15 dB 로 안 움직인다.",
    "s1000plus_ko": "s1000plus 만 스펙트럼의 **성격**이 바뀐다 — 상한 위 몫 3.60 → 51.91 %(+48.3 %p) · 파형 상관 0.698 · 맵 상관 0.7055(격자 바닥 0.6825 **바로 위**) · 리듬 여유 3.37 → 2.15 배. 가장 그럴듯한 읽기는 «큰 프롭 8 장이 넓은 카본 프레임 위를 쓸고 지나가는데 카본은 두께 손잡이가 안 건드린다» 이지만 **프롭만 대조군이 없어 추론**이다.",
    "canon_thickness_projection_db": {"matrice4e": -13.012, "mini5pro": -15.577, "s1000plus": -8.312},
    "projection_caveat_ko": "⚠matrice4e 만 정본 점을 직접 쟀다(−13.01 dB). 나머지 둘은 사다리 보간 + 그 기체의 0.9 mm 오프셋으로 만든 **추정**이다. 방향은 «날이 얇은 기체일수록 재질 정정으로 더 많이 잃는다».",
    "shell_untested_ko": "셸 단독 팔·프롭만 대조군·el 0 배선 대조군이 mini5pro·s1000plus 에 **전부 미착지**. 기체별 격자 밴드도 없어 matrice4e 밴드를 빌려 썼다.",
  },
}

adjudications = [
 {"id": "J1", "title_ko": "솎기 충돌 — 삭제 방식은 빗살·리듬에 무효",
  "conflict_ko": "기체 교차 갈래는 matrice4e 빗살 헤드라인을 삭제 솎기 값 **−3.43 dB(판정 불가)** 로 적자고 했고(«trim_flips_verdict: true»), 사다리·각도 갈래는 삭제가 잣대를 부순다고 반증했다.",
  "ruling_ko": "⭐**사다리·각도 갈래 손을 든다.** 무작위 자세를 지워도 같은 크기로 흔들리고(sd 2.26 dB), 갈아끼우기·균일 재표집에서는 −5.8~−6.95 dB 로 제자리다. ⇒ **정본 빗살 Δ(el −30, 프롭 0.9 mm) = −6.95 ~ −6.98 dB, 밴드 밖(유의).** 기체 교차 갈래의 −3.43 dB 권고는 **기각**한다.",
  "affects_ko": "material_canon_0816_airframes.json 의 d_comb_contrast_db_trim1(matrice4e) · outlier_forensics_ko 문단."},
 {"id": "J2", "title_ko": "«12~13 dB 밝게 깔림» 은 어느 잣대의 수인가",
  "conflict_ko": "§6 게이트 2 는 0.9 mm 의 **확산 바닥** −12.56 dB 로 «적중» 처리됐는데 정본 1.43 mm 의 확산 바닥은 −8.81 dB 다.",
  "ruling_ko": "⭐정본에서 12~13 dB 인 것은 **요동(−13.02 dB)** 이다. 확산 바닥은 −8.81 dB 이고 그 앙각 밴드(9.295) **안**이라 판정 불가다. ⇒ 이 수를 인용할 때는 **반드시 잣대 이름과 앙각(el −30)** 을 붙인다.",
  "affects_ko": "MATERIAL_CORRECTION §6 게이트 2 · §10-3 표."},
 {"id": "J3", "title_ko": "덱 24 장 drowned blades 의 프롭 값",
  "conflict_ko": "§4-3 은 정본 1.43 mm 의 **각도평균 슬래브 −8.08 dB** 를 넣기로 했다(«78 → 약 86 dB»).",
  "ruling_ko": "⭐실제로 잰 날개 에코 변화는 el −30 에서 **−13.02 dB** 이고, 맞는 슬래브 열은 각도평균이 아니라 **유효 입사각 40.2°**(예측 −12.71, 잔차 0.31 dB)다. ⇒ 값을 **−13.0 dB**, 문장을 «78 → 약 **91** dB» 로 고친다. 익사 간격은 계획보다 **약 4.9 dB 더 벌어진다**(결론 방향은 같고 강해진다). ⚠덱 문장이 각도 무관 서술이므로 **el −30 꼬리표**를 같이 넣거나 문장을 빗각 한정으로 좁힌다.",
  "affects_ko": "make_0818_v16.py:881 · 덱 24 장 노트 · MATERIAL_CORRECTION §4-3."},
 {"id": "J4", "title_ko": "H5 방향 진술 철회",
  "conflict_ko": "오전 판은 «정정하면 굴절 채널 레벨은 **올라가는 쪽**»(왕복 투과 −6.35 → −0.13 dB)이라고 슬래브 수학으로 적었다.",
  "ruling_ko": "⭐**철회**. 깊이 1 실측은 반대다 — 굴절 팔이 절대로도(−19.4 dB) 다 끔 대비로도(−2.4 dB) 더 어둡다. ⇒ «깊이 1 실측으로는 **내려가는 쪽** · 깊이 ≥2 는 **미측정**» 으로 교체한다. 거리 기울기(완만 감쇄)는 곱셈 이득과 무관해 그대로다.",
  "affects_ko": "material_verdict_0816.headline_impacts_ko.굴절만_거리_생존 · MATERIAL_CORRECTION §10-3 첫 줄."},
 {"id": "J5", "title_ko": "확산 바닥 헤드라인의 기체 범위",
  "conflict_ko": "«프롭 정정이 확산 바닥을 −12.6 dB 내린다» 가 기체 무관 문장처럼 쓰여 있었다.",
  "ruling_ko": "⭐**matrice4e·mini5pro 한정**으로 좁힌다. s1000plus 는 −0.07 dB(밴드 안)로 **반증**이다. 기체 무관 문장으로 쓸 수 있는 것은 «**날개선**(박자 정수배 자리)이 −14.5~−17.0 dB 내려간다» 뿐이다.",
  "affects_ko": "MATERIAL_CORRECTION §10-0 V2 · §10-3 · 모든 «확산 바닥» 인용."},
 {"id": "J6", "title_ko": "el 0 «금속 추첨» 문장의 표현",
  "conflict_ko": "오전 H3 은 «손잡이가 의도 밖 재질(금속)을 **안 잡았다**» 로 적었다.",
  "ruling_ko": "⭐절반만 맞다 — 손잡이는 정면에서도 프롭을 잡았고(잔차가 리듬 89.8 % 의 완전한 날개 무늬), 그 몫이 **52~55 dB 아래라 묻혔을 뿐**이다. ⇒ «안 잡았다» 를 «**묻혔다**» 로 바꾼다. 배선 대조군으로서의 판정(0.000 dB, 통과)은 그대로다.",
  "affects_ko": "MATERIAL_CORRECTION §10-2 H3 행 · §2-4 «방아쇠는 프롭·크기는 금속»."},
 {"id": "J7", "title_ko": "el −60 확산 바닥 밴드",
  "conflict_ko": "오전 판은 el −60 밴드가 없어 «최대 9.295» 를 빌려 썼다.",
  "ruling_ko": "⭐실제 el −60 바닥 밴드는 **5.797 dB** 다(각도 갈래가 새로 냈다). el −60 채점은 새 값으로 다시 한다 — 정본 1.43 mm 의 el −60 바닥 −11.64 dB 는 이 밴드 **밖**(유의)이다.",
  "affects_ko": "밴드 표를 쓰는 모든 채점."},
]

def imp(id_, target, files, current, direction, size, action, basis, extra=None):
    d = {"id": id_, "target_ko": target, "files": files, "current_value_ko": current,
         "direction_ko": direction, "size_estimate_ko": size, "action": action, "basis_ko": basis}
    if extra: d.update(extra)
    return d

impacts = [
 imp("I1", "⭐절대 판독거리 R50 = 724 m (빗살 잣대) · 567 m (대역 잣대) — 우리 커널 el −30",
     ["outputs/detection_curves.json", "docs/RESUME.md:119", "docs/MATERIAL_CORRECTION.md §4-1 #3"],
     "R50 723.7 m · 대역 잣대 567 m · 「−34 % → 약 475 m」 예상치",
     "오늘은 **안 바뀐다**(우리 커널은 두께가 없다·D3 동결). (b) 착수 뒤 바뀌고, 방향은 **줄어드는 쪽**.",
     ("⭐**셸 정책이 답을 정한다.** 셸·프롭을 같이 고치면 움직이는 몫이 −0.08 dB 밖에 안 움직여 R50 은 사실상 그대로(−0.5 %, 약 720 m)다 — "
      "정지 성분이 요동만큼 같이 내려가 앵커가 지워 주기 때문이다. 프롭만 고치고 셸을 100 mm 로 두면 −9.5~−11.7 dB 로 떨어져 "
      "**R50 369~418 m(−42 ~ −49 %)** 가 된다. 옛 «−34 % → 475 m» 는 수직입사 슬래브 −7.72 dB 위에 서 있었고 정본 실측은 −13.02 dB 라 **더 크다**."),
     "recompute",
     "이 원장 moving_share·r50_bracket 절에 계산이 실려 있다. 꼬리표로는 부족하다 — 숫자가 정책에 따라 두 배 갈린다.",
     {"bracket": r50_bracket}),
 imp("I2", "§4-1 #3 의 «셸만 고치면 723.7 → 약 760 m(+5 %)»",
     ["docs/MATERIAL_CORRECTION.md §4-1 #3"],
     "+5 % (약 760 m)",
     "같은 방향(늘어남), 크기가 **두 배**",
     "실측 셸 단독 0.75 mm 의 움직이는 몫은 **+1.670 dB** → **+10.1 %(약 797 m)**. 셸은 정지 성분만 지우므로 비가 오히려 좋아진다.",
     "recompute", "ladder_share.shell0.75_prop100_control (이 원장)"),
 imp("I3", "⭐앙각별 잔차 — 앵커가 el −30 한 칸에서만 뽑히는 구조",
     ["outputs/detection_curves.json", "outputs/noise_distance_frame.json", "outputs/detection_engine_angle*.json", "docs/MATERIAL_CORRECTION.md §6"],
     "sionna 앵커 σ: el+0 +56.08 dBsm · el−30 −13.98 · el−60 −1.45 dBsm / 100 m SNR 87.79 · 17.73 · 30.26 dB",
     "el 0 은 **더 밝아지고** el −60 은 **더 어두워진다** — 앙각 프로파일 자체가 바뀐다",
     ("총 σ 이동이 앙각마다 다르다(el 0 **0.00** · el −30 −12.94 · el −60 −16.50 dB). el −30 에서 앵커를 다시 잡으면 남는 잔차가 "
      "**el 0 +12.94 dB · el −60 −3.56 dB** 다 ⇒ 앵커 σ el+0 56.08 → **약 69.0 dBsm**, el−60 −1.45 → **약 −5.01 dBsm**; "
      "100 m SNR el+0 87.79 → **약 100.7 dB**, el−60 30.26 → **약 26.7 dB**. "
      "⭐그런데 «움직이는 몫» 은 반대로 el −60 에서 **+5.74 dB 좋아진다**(정지 성분이 요동보다 더 많이 내려간다) → 그 앙각의 무늬 판독거리는 **+39 %**."),
     "recompute", "moving_share 절(이 원장). §6 이 «el 0·−60 칸은 인용 불가» 라고만 적어 둔 것을 이제 **크기로** 적을 수 있다."),
 imp("I4", "잡음 틀 판독거리 — 무늬 읽히는 한계·Pd90 한계",
     ["outputs/noise_distance_frame.json (read_lines)"],
     "ours 554 / Pd90 640 m · ours_ptd 656/753 · ps_off 641/700 · ps_refr 556/620 · ps_phys 47/63 m",
     "el −30 헤드라인은 **거의 안 움직인다** — 다만 그것은 정본 두께에서만 참이다",
     ("Sionna 팔(ps_off·ps_refr·ps_phys)은 지금 **100 mm 위에서 잰 값**이다. 정본으로 고치면 움직이는 몫이 "
      "다 끔 팔 **−0.08 dB**, 굴절 팔 **+0.10 dB** 밖에 안 변한다 ⇒ **ps_off 641 → 약 638 m(−0.5 %)** · "
      "**ps_refr 556 → 약 559 m(+0.6 %)**. ⭐그러나 이것은 **두께에 매우 민감한 «사실상 불변»** 이다 — "
      "민감도 점 0.9 mm 에서는 다 끔 −1.62 dB(−8.9 %) · 굴절 **−3.83 dB(−19.8 %)** 이고 0.5 mm 에서는 다 끔 −4.67 dB(−23.6 %) 다. "
      "정지 성분이 요동만큼 같이 내려가 앵커가 지워 주는 상쇄가 **정본 두께 근처에서 우연히 가장 잘 맞는다.** "
      "ours·ours_ptd 는 오늘 안 바뀐다(D3)."),
     "recompute", "refr_share·ladder_share 절(이 원장) · H5 갈래의 굴절 팔 칸"),
 imp("I5", "⭐기체 분류 정확도 — Sionna 쪽",
     ["outputs/classify_airframe.json"],
     "sionna 총 정확도 **0.9464** (3 기체 × 7 앙각 × 336 창) · ours 1.0000",
     "**위험** — 오르내림 방향을 예측 못 한다",
     ("정정은 **클래스마다 다른 변환**이다(정본 두께 mini5pro 0.80 · matrice4e 1.43 · s1000plus 1.99 mm — 균일 이득이 아니다). "
      "게다가 s1000plus 만 스펙트럼 성격이 바뀐다(파형 상관 0.698 · 맵 상관 0.7055 · 상한 위 몫 +48.3 %p). "
      "분류기는 바로 그 특징들 위에 서 있으므로 **0.9464 는 다시 재야 하는 수**다. ⚠지금은 **못 잰다** — mini5pro·s1000plus 의 "
      "정정판이 el −30 한 칸에만 있고 분류는 7 앙각을 쓴다. ours 1.0000 은 오늘 안 바뀐다(D3)."),
     "recompute", "기체 교차 갈래 + classify_airframe 의 팔 목록(둘 다 100 mm Sionna 팔)"),
 imp("I6", "마이크로도플러 기종 분류 정확도 — 우리 커널",
     ["outputs/md_classify.json", "outputs/md_classify_verify*.json"],
     "accuracy_all **0.8785** (6 기체 · 27 특징, 특징에 dc_over_ac_db·flash_contrast_db 포함)",
     "오늘은 **안 바뀐다**(D3). (b) 뒤에는 바뀔 수 있다",
     "정지/요동 비와 빗살 대비가 특징 벡터에 직접 들어 있고 정정은 기체마다 다르게 걸리므로, (b) 착수 뒤 **다시 재야 한다**. 지금은 «우리 커널 두께 축 N/A» 꼬리표로 충분하다.",
     "tag_now_recompute_after_b", "md_classify._meta.features · canon.ours_kernel"),
 imp("I7", "거리별 탐지확률 Pd(R) 표 (15/30/60/120 m)",
     ["outputs/detection_curves.json", "outputs/noise_distance_frame.json"],
     "ours 1.00/1.00/1.00/1.00 · ps_off 1.00/1.00/1.00/0.93 · ps_phys 1.00/1.00/0.00/0.00 (el −30)",
     "el −30 은 사실상 불변, el −60 은 좋아짐",
     "el −30 움직이는 몫이 −0.08 dB(≈0.02 dB SNR)라 문턱 근처의 ps_off 120 m Pd 0.93 조차 안 흔들린다 ⇒ **꼬리표로 충분**. el −60 표를 인용할 때만 I3 대로 다시 잰다.",
     "tag", "moving_share.el-30"),
 imp("I8", "회절이 확산 바닥을 덮는다 (매몰 간격)",
     ["outputs/switch_factorial.json", "덱 25 장", "docs/MATERIAL_CORRECTION.md §4-2·§10-3"],
     "이 원장 요동 기준 간격 +10.9 dB (덱 25 는 별도 원장 +36 dB)",
     "**넓어진다** — 덮음은 어느 끝에서도 유지",
     ("정본에서 바닥이 −13.02 dB 더 내려가고 회절 자신의 두께 민감도는 0 ~ −18 dB 브래킷이므로 간격은 **+5.9 ~ +23.9 dB**. "
      "⚠오전 판이 −17 dB(0.9 mm)로 낸 «+10.9~+27.9 dB» 는 정본에서 위 값으로 바뀐다. 덱 25 의 +36 dB 는 별도 원장이라 여기서 재채점 안 한다."),
     "recompute", "ladder canon Δ요동 −13.019 · §4-2 의 쐐기면 브래킷"),
 imp("I9", "덱 24 장 «drowned blades» 78 dB / 52 dB",
     ["scratchpad/make_0818_v16.py:881", "덱 24 장 노트", "docs/MATERIAL_CORRECTION.md §4-3"],
     "노트가 셸 2 mm 값(−5.8 dB)을 프로펠러 문장에 주입 · §4-3 은 −8.08 dB(각도평균)로 고치기로 함",
     "**강해진다**",
     "정본 실측 −13.02 dB(el −30, 유효 입사각 40.2°) ⇒ «78 → 약 **91** dB». §4-3 계획(−8.08 → 86 dB)보다 **4.9 dB 더 벌어진다**. ⚠el −30 꼬리표 필수(덱 문장은 각도 무관 서술).",
     "recompute", "J3 판정"),
 imp("I10", "평판 거울 낙차 −57.3 dB(식) ↔ −57.1 dB(실측) — 덱 12·24 Q&A",
     ["outputs/az_falsify_specular.json", "docs/MATERIAL_CORRECTION.md §4-2"],
     "§4-2 는 분모(az45 canopy 플라스틱)를 각도평균 −12.66 dB 로 어둡게 해 «약 −70 dB» 로 벌어진다고 적음",
     "벌어지는 방향은 같고, **쓸 슬래브 열이 바뀐다**",
     ("⭐이 낙차의 분자·분모는 둘 다 **0.5° 안에 정렬된 거울면**이다 — 정의상 수직입사이므로 **수직입사 열(−13.25 dB)** 을 써야지 "
      "각도평균(−12.66)이나 유효 입사각(40.2°) 열이 아니다. 크기 차는 0.6 dB 로 작지만 규약을 못 박아 둔다(protocol.slab_column_rule_ko). "
      "⚠az45·el 0 칸은 두께 팔이 안 돌았다 — 여전히 **추론**이다."),
     "tag", "protocol.slab_column_rule_ko · §4-2"),
 imp("I11", "밴드 기울기 대조 · 문헌 봉투 격차 −4.43 → 약 −5.2 dB",
     ["outputs/validate_measured_airframe.json", "docs/MATERIAL_CORRECTION.md §4-1 #6·#7"],
     "phantom4 0.747→0.881 · mini5pro 0.691→0.895 dB/GHz · 봉투 격차 −4.43 dB",
     "오늘은 **안 바뀐다** — 전부 우리 커널 |Γ| 축(D3 동결)",
     "(b) 착수 뒤 한쪽 방향으로 벌어진다. 지금은 꼬리표로 충분하다. ⚠비교는 **앵커 이전** 값끼리(§4-1 #6).",
     "tag", "canon.ours_kernel"),
 imp("I12", "⭐«확산 바닥이 프롭을 탄다» 의 기체 범위",
     ["docs/MATERIAL_CORRECTION.md §10-0 V2·§10-3", "모든 «확산 바닥» 인용"],
     "기체 무관 문장처럼 쓰여 있음",
     "**좁혀야 한다**",
     "s1000plus 에서 −0.07 dB(밴드 안)로 반증됐다 ⇒ 문장을 **matrice4e·mini5pro 한정**으로 좁히고, 기체 무관으로 쓸 수 있는 것은 «날개선 −14.5~−17.0 dB» 뿐이다. 숫자는 안 바뀌고 **범위 꼬리표**가 붙는다.",
     "tag", "J5 판정"),
 imp("I13", "굴절만 팔 레벨·거리 인용의 방향 꼬리표",
     ["docs/RESUME.md 0816 §0 «완만 감쇄 생존»", "material_verdict_0816.headline_impacts_ko"],
     "«정정하면 굴절 채널은 올라가는 쪽» (슬래브 추론)",
     "**철회 — 반대 방향**",
     "깊이 1 실측은 굴절 팔이 더 어두워진다(절대 −19.4 dB · 다 끔 대비 −2.4 dB). 문장을 «깊이 1 실측으로는 내려가는 쪽 · 깊이 ≥2 는 미측정» 으로 바꾼다. 거리 **기울기**(완만 감쇄) 자체는 안 흔들린다.",
     "tag", "J4 판정"),
 imp("I14", "el −60 채점에 쓰던 확산 바닥 밴드",
     ["밴드 표를 쓰는 모든 채점", "outputs/grid_convergence_check.json"],
     "el −60 에 «최대 9.295 dB» 를 빌려 씀",
     "밴드가 **좁아진다** → 판정이 더 쉽게 «유의» 로 간다",
     "실제 el −60 바닥 밴드는 **5.797 dB**. 정본 1.43 mm 의 el −60 바닥 −11.64 dB 는 새 밴드 **밖**(2.0 배)이다. 옛 밴드로 «판정 불가» 라 적은 el −60 항목이 있으면 다시 채점한다.",
     "recompute", "J7 판정 · 각도 갈래"),
 imp("I15", "딥러닝 확장 큐가 만드는 새 칸의 재질",
     ["docs/DL_PIPELINE.md", "지금 도는 딥러닝 칸 확장 큐"],
     "elevation_sweep_md.npz 는 DL 에서 «연막 시험» 등급 — 주 학습 자산은 아님",
     "**영향 작음, 그러나 꼬리표는 필요**",
     "지금 도는 큐가 100 mm 위에서 칸을 만들면 그 칸은 «옛 재질» 이 된다. ⛔이 세션은 큐를 안 건드린다 — 다만 새로 생기는 칸에 shell_mm·prop_mm 꼬리표가 남는지 확인하고, DL 이 그 칸을 학습에 쓰게 될 때 정정판으로 갈지 먼저 정한다.",
     "tag", "DL_PIPELINE §3-4 연막 시험 상자"),
]

pattern_verdict = (
  "⭐**무늬·분류 서사는 산다 — 단 matrice4e·mini5pro 에서만이고, s1000plus 에서는 흔들린다.** "
  "(matrice4e 정본: 맵 상관 0.903 · 박자 Δ 0.04 Hz · 리듬 몫 밴드 안 · 빗살 45.8 dB(백색 0 dB 대비) — "
  "s1000plus: 파형 상관 0.698 · 맵 상관 0.7055 로 격자 바닥 0.6825 **바로 위** · 상한 위 몫 +48.3 %p.)"
)

open_ko = [
 "⭐**PathSolver 자신의 밴드를 잰 적이 없다.** 여기 쓴 격자 밴드는 전부 우리 커널(SBR+PO) λ/12↔λ/24 에서 «빌려 온» 것이고 시드 밴드도 다른 조건(el −15·40 m)에서 빌려 왔다. PathSolver 시드 복제 팔이 있어야 제대로 채점된다.",
 "⭐**셸 버전 H5 는 미측정**(굴절 × 셸만 × 깊이 ≥2). 지금 원장에는 «얇은 셸 × 깊이 1» 과 «100 mm × 깊이 3» 만 있고 교집합이 없다.",
 "⭐**정본 점이 matrice4e 하나뿐**이다 — mini5pro 0.80 · s1000plus 1.99 mm 는 안 쟀다(사다리 보간 추정).",
 "**정본 1.43 mm 의 el −15 칸이 없다** — 상한 위 몫이 +15.5 %p 튀고 박자가 움직이는 유일한 앙각을 정본으로 못 봤다. −45 · −75 · −90 에는 두께 칸이 아예 없다.",
 "**셸 단독 팔이 mini5pro·s1000plus 에 없다** — «껍데기는 무관» 의 다른 기체 판정이 여기 걸려 있다.",
 "**s1000plus 배경의 정체를 못 갈랐다**(프롭만 대조군 없음). «카본이 두께 손잡이 밖» 은 추론이다.",
 "**엔진 교차 확인이 없다** — 우리 커널에는 두께 개념이 없어 이 사다리는 PathSolver 한 엔진에서만 잰 것이다.",
 "**프롭이 어두워질 때 «날개끝 상한 위 몫» 이 왜 오르는지**(요동 40.2° ↔ 확산 바닥 64.5° 의 갈림)를 안 갈랐다.",
 "**두께 자체의 출처** — 0.5·0.9·2.0 mm 는 민감도 점이고, 정본 1.43 mm 도 «우리 메쉬의 시위평균» 이지 DJI 실물 실측이 아니다(D2 잔차 +1.2~+1.7 dB).",
 "⭐**absorber·camera_assembly 등 다른 재질 축은 이 정본 밖**이다 — camera_assembly 0.85 는 출처가 없는데 총 σ 를 최대 1.81 dB 움직여 셸(0.69 dB)보다 크다(§7 R7).",
]

doc = {
 "_meta": meta, "canon": canon, "why_shell_untouched": why_shell, "metric_protocol": protocol,
 "branch_summary": branches, "adjudications": adjudications,
 "derived_moving_share_el": moving_share,
 "derived_moving_share_ladder_el_minus30": ladder_share,
 "derived_moving_share_refraction_el_minus30": refr_share,
 "r50_bracket": r50_bracket,
 "impact": impacts,
 "pattern_and_classification_verdict_ko": pattern_verdict,
 "open_ko": open_ko,
 "do_not_write_ko": [
   "⛔«재질 정정이 확산 바닥을 −12.6 dB 내린다» 를 기체 무관으로 쓰지 마라 — s1000plus 는 −0.07 dB 다.",
   "⛔«정면에서는 프롭이 영향이 없다» — 프롭 무늬는 정면에도 완전하다. 52~55 dB 아래라 묻힌 것이다.",
   "⛔«투과 반대항은 존재하지 않는다» — 반증된 것은 예측의 **방향**이고 기제는 배선이 없어 못 쟀다.",
   "⛔삭제 솎기로 잰 Δ빗살(−3.43 등)을 인용하지 마라 — 잣대 파손 값이다.",
   "⛔«−34 % → 475 m» 를 지금 상태로 다시 쓰지 마라 — 셸 정책에 따라 −0.5 % 와 −49 % 로 갈린다.",
   "⛔각도평균 슬래브 열을 표적 축 인용에 쓰지 마라(정본에서 4.93 dB 어긋난다).",
   "⛔«재질 정정이 빗살을 흐린다» 를 빗각 전부에 붙이지 마라 — el −60 에서는 +1.6 dB(밴드 안)다.",
 ],
 "verdict_headline_ko": (
   "① **정본 확정** — Sionna 셸 0.75 mm(CAD 실측) · 프로펠러는 기체별 시위평균(matrice4e **1.43** · mini5pro 0.80 · s1000plus 1.99 mm) · "
   "우리 커널 |Γ|=0.28 은 **두께 축 구조적 N/A**(D3 동결). ② **껍데기는 표적 축에 배선이 없다** — 셸만 얇게 하면 정지 성분만 6.24 dB "
   "내려가고 요동·확산 바닥·빗살은 0.00 dB, 파형 상관 1.0000(구조적 0). 그래서 비(比)로 서는 주장은 셸 정정에 면역이고, 셸이 실제로 "
   "먹는 자리는 **절대 σ·앵커·거리**다. ③ **손잡이는 프로펠러다** — 정본 1.43 mm 에서 el −30 요동 **−13.02 dB**(유효 입사각 40.2° 평판 "
   "예측과 0.31 dB), 세 기체 날개선 −14.5~−17.0 dB. ④ **네 갈래가 뒤집은 것 셋** — H5 방향(굴절 팔은 더 어두워진다·기제는 미측정) · "
   "확산 바닥 헤드라인의 기체 범위(s1000plus 반증) · 빗살 솎기 규약(삭제 금지). ⑤ **가장 큰 파급은 R50 이다** — 셸·프롭을 같이 고치면 "
   "−0.5 %, 프롭만 고치면 −42~−49 %. 옛 «−34 %» 는 수직입사 슬래브 위에 서 있었고 다시 계산해야 한다. ⑥ **무늬·분류 서사는 산다** — "
   "matrice4e·mini5pro 에서. s1000plus 는 흔들린다."
 ),
}

path = os.path.join(OUT, "material_canon_0816.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)
print("wrote", path, os.path.getsize(path), "bytes")
print(json.dumps(moving_share, ensure_ascii=False, indent=1))
print(json.dumps(refr_share, ensure_ascii=False, indent=1))
print(json.dumps(r50_bracket["measured_sionna_arm_shell_and_prop_together"], ensure_ascii=False))
print(json.dumps(r50_bracket["hypothetical_prop_only_dc_unchanged_upper"], ensure_ascii=False))
print(json.dumps(r50_bracket["ours_balance_prop_only_dc_unchanged"], ensure_ascii=False))
print(json.dumps(ladder_share["shell0.75_prop100_control"], ensure_ascii=False))
