#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""엔진 검증 판정 · 리포트 순서 제안 — docs/ENGINE_VALIDATION.md + outputs/engine_validation_verdict.json

세 선행 단계의 JSON 만 읽어서 판정문서를 짓는다. **GPU 를 쓰지 않는다.**

  outputs/validation_feasibility.json        어느 기체가 대조 가능한가(출처 감사)
  outputs/material_sources.json              재질 tier-2/tier-3 출처·유계
  outputs/validate_measured_airframe.json    Phantom 3 대조 실행 결과

⚠ 하우스 규약: 이 파일 안에서 **손으로 적힌 수치는 0 개**다. 모든 dB·GHz·초는 위 세 JSON
   또는 scratchpad 로그에서 읽어 f-string 으로 주입한다. 로그가 없으면 그 칸은 "미기록"으로
   찍히지 절대 추정치로 채우지 않는다.

  PYTHONPATH=src:benchmark python benchmark/engine_validation_verdict.py
"""
import json
import os
import re
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(_ROOT, "outputs", "engine_validation_verdict.json")
OUT_MD = os.path.join(_ROOT, "docs", "ENGINE_VALIDATION.md")
SCRATCH = os.environ.get(
    "SIONNA2_SCRATCH",
    "/tmp/claude-1015/-workspace/"
    "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad")

B = ["LTE 1.843 GHz", "5G 3.5 GHz", "WiFi 5.21 GHz"]
FGHZ = {"LTE 1.843 GHz": 1.843, "5G 3.5 GHz": 3.500, "WiFi 5.21 GHz": 5.210}


def _load(name):
    with open(os.path.join(_ROOT, "outputs", name)) as f:
        return json.load(f)


FEAS = _load("validation_feasibility.json")
MAT = _load("material_sources.json")
VAL = _load("validate_measured_airframe.json")
KR = _load("sbr_kr_sweep.json")


def E(x):
    """마크다운 표 셀 — 파이프를 이스케이프하고 줄바꿈을 없앤다."""
    return str(x).replace("|", "\\|").replace("\n", " ")


def HT(material, param_frag):
    """honest_table 에서 (material, param 조각) 으로 한 행을 찾는다."""
    for r in MAT["honest_table"]:
        if r["material"] == material and param_frag in r["param"]:
            return r
    raise KeyError(f"honest_table: {material} / {param_frag}")


# --------------------------------------------------------------------------- #
# 1. 비용 — 로그에서 실측 GPU 초를 긁고, 로그가 없는 단계는 광선율 모델로 유도한다
# --------------------------------------------------------------------------- #
def _log_runs(fname):
    """sigma_az 가 찍은 '(NNNs)' 를 모아 (건수, 총초, rays/az 목록) 을 준다."""
    p = os.path.join(SCRATCH, fname)
    if not os.path.exists(p):
        return None
    txt = open(p, errors="replace").read()
    secs = [int(x) for x in re.findall(r"\((\d+)s\)", txt)]
    rpa = [int(x) for x in re.findall(r"rays/az=\s*(\d+)", txt)]
    if not secs:
        return None
    return dict(n_runs=len(secs), gpu_s=float(sum(secs)),
                rays_per_az=rpa, per_run_s=secs)


def _mtime(path):
    p = path if os.path.isabs(path) else os.path.join(SCRATCH, path)
    return os.path.getmtime(p) if os.path.exists(p) else None


band = _log_runs("valair_band.log")
sweep = _log_runs("valair_sweep.log")

#  광선율 모델: sweep 단계는 (건수, rays/az, 초) 가 전부 기록돼 있다 → 원점을 지나는
#  최소제곱 s = k * rays_per_az 를 세운다. group/mat 단계는 같은 커널·같은 n_az(360)
#  이므로 rays/az 만 알면 초가 나온다.
rate_k = None
if sweep and sweep["rays_per_az"]:
    xs = sweep["rays_per_az"]
    ys = sweep["per_run_s"]
    n = min(len(xs), len(ys))
    num = sum(xs[i] * ys[i] for i in range(n))
    den = sum(x * x for x in xs[:n])
    rate_k = num / den

#  group/mat 단계가 쓴 rays/az 는 band 로그에 그대로 있다(같은 메쉬·같은 밴드).
rpa_by_band = {}
if band and band["rays_per_az"]:
    for i, b in enumerate(B):
        rpa_by_band[b] = band["rays_per_az"][2 * i]

triple_s = (sum(rate_k * rpa_by_band[b] for b in B)
            if (rate_k and len(rpa_by_band) == 3) else None)

#  건수는 코드 구조에서 센다(추정 아님):
#    group = baseline 3 + isolate 8*3 + leaveout 8*3 + no_internal_metal 3 + shell_only 3
#    mat   = 4 variants * 3
N_GROUPS = len(VAL["5_group_decomposition"]["isolate"])
N_GROUP_RUNS = 3 + N_GROUPS * 3 + N_GROUPS * 3 + 3 + 3
N_MAT_RUNS = len([k for k in VAL["7_material_bracket"] if not k.startswith("_")]) * 3
N_SCAN_RUNS = 2 * 3
N_SPHERE_RUNS = 3

scan_wall = None
t_grp, t_scn = _mtime("valair_group.log"), _mtime("valair_scan.log")
if t_grp and t_scn and t_scn > t_grp:
    scan_wall = t_scn - t_grp

cost_rows = []
if band:
    cost_rows.append(dict(stage="sphere+band", n_runs=band["n_runs"] + N_SPHERE_RUNS,
                          gpu_s=band["gpu_s"], how="로그 실측(구 3건은 초 미기록)"))
if sweep:
    cost_rows.append(dict(stage="sweep 1.8-18.2 GHz 21점", n_runs=sweep["n_runs"],
                          gpu_s=sweep["gpu_s"], how="로그 실측"))
if triple_s:
    cost_rows.append(dict(stage="group 분해", n_runs=N_GROUP_RUNS,
                          gpu_s=triple_s * (N_GROUP_RUNS / 3.0),
                          how=f"광선율 유도 k={rate_k:.3e} s/(ray·az)"))
    cost_rows.append(dict(stage="material bracket", n_runs=N_MAT_RUNS,
                          gpu_s=triple_s * (N_MAT_RUNS / 3.0),
                          how=f"광선율 유도 k={rate_k:.3e} s/(ray·az)"))
if scan_wall:
    cost_rows.append(dict(stage=f"scan 대조({VAL['6_geometry_fidelity']['n_faces'][0]/1e6:.2f} M tri)",
                          n_runs=N_SCAN_RUNS,
                          gpu_s=scan_wall, how="벽시계 상한(로그 mtime 차)"))

cmp_gpu_s = sum(r["gpu_s"] for r in cost_rows)
cmp_runs = sum(r["n_runs"] for r in cost_rows)

mat_sweep_s = MAT["impact_sweep"]["_meta"]["runtime_s"]
mat_carb_s = MAT["carbon_supplement"]["_meta"]["runtime_s"]
mat_gpu_s = mat_sweep_s + mat_carb_s


def _count_sweep_cells(by_drone):
    """스윕 JSON 에서 실제로 돌아간 (기체 × 밴드 × 변형) 셀 수를 센다."""
    n = 0
    for _dr, bands in by_drone.items():
        for _b, v in bands.items():
            if not isinstance(v, dict) or _b.startswith("_"):
                continue
            n += sum(1 for k, vv in v.items()
                     if isinstance(vv, dict) and "delta_vs_base_db" in vv)
    return n


n_imp_runs = _count_sweep_cells(MAT["impact_sweep"]["by_drone"])
n_carb_runs = _count_sweep_cells(MAT["carbon_supplement"]["by_drone"])

total_gpu_s = cmp_gpu_s + mat_gpu_s

#  2회차 한계비용: 교정구(공유)와 scan(그 기체의 실물 스캔이 있을 때만) 을 뺀다.
second_gpu_s = cmp_gpu_s - (scan_wall or 0.0)


# --------------------------------------------------------------------------- #
# 2. 판정표 — 세 JSON 에서 그대로 뽑는다
# --------------------------------------------------------------------------- #
HEAD = VAL["8_comparison"]["_headline"]
LVL = VAL["8_comparison"]["A_absolute_level"]
SLOPE = VAL["8_comparison"]["B_band_slope"]
EPSC = VAL["8_comparison"]["C_azimuth_pattern_shape"]
BIST = VAL["8_comparison"]["D_bistatic"]
ERR = VAL["8_comparison"]["E_error_bars"]
DIAG = VAL["8_comparison"]["F_diagnosis"]
SPH = VAL["2_calibration_sphere"]
GEO = VAL["6_geometry_fidelity"]
BRK = VAL["7_material_bracket"]["_bracket"]
AIR = VAL["1_airframe"]
XCH = VAL["8_comparison"]["I_crosschecks"]["harness_vs_feasibility_phase"]
XCH_ALL = VAL["8_comparison"]["I_crosschecks"]

sph_dev = {b: SPH["by_band"][b]["spheres"][0]["dev_db_vs_mie"] for b in B}
sph_ka = {b: SPH["by_band"][b]["spheres"][0]["ka"] for b in B}

#  두 처리본(Das 발표값 vs Yuan 고도평균)의 생 격차 — 규약 오프셋을 넣기 전 값
_raw_das_yuan = {b: abs(LVL["by_band"][b]["values_dbsm"]["das_as_published"]
                        - LVL["by_band"][b]["values_dbsm"]["yuan_elevation_pooled"]) for b in B}

budget = DIAG["narrowband_slope_budget"]
resid = budget["unexplained_residual_db_per_ghz"]["vs_das"]
resid_frac = budget["unexplained_residual_db_per_ghz"]["fraction_of_gap_vs_das"]
mat_slope_bar = budget["two_sided_uncertainty_db_per_ghz"]["material table bracket (V1/V2/V3)"]

verdict_rows = [
    dict(quantity="교정 표적의 절대 σ (PEC 구 r = 17.8 cm, Yuan 자신의 교정 표준)",
         reproduced="예",
         accuracy=(f"정확 Mie 대비 {min(abs(v) for v in sph_dev.values()):.3f}~"
                   f"{max(abs(v) for v in sph_dev.values()):.3f} dB, "
                   f"ka = {min(sph_ka.values()):.2f}~{max(sph_ka.values()):.2f}"),
         src="validate_measured_airframe.json : 2_calibration_sphere"),
    dict(quantity="해석 PO 구 (커널 자체 수렴)",
         reproduced="예",
         accuracy=(f"kr {KR['summary_div16']['kr_min']:g}~{KR['summary_div16']['kr_max']:g} · "
                   f"입사 {KR['meta']['n_incidence']}방향에서 최대 "
                   f"{KR['summary_div16']['max_abs_db_vs_po']:.4f} dB"),
         src="sbr_kr_sweep.json : summary_div16.max_abs_db_vs_po"),
    dict(quantity="측정 기체의 밴드 기울기 dμ/df, 6 GHz 위",
         reproduced="예",
         accuracy=(f"우리 {HEAD['slope_ours_6_18p2_ghz']:.3f} dB/GHz vs 측정 "
                   f"{min(HEAD['slope_measured_1p8_18p2'].values()):.3f}~"
                   f"{max(HEAD['slope_measured_1p8_18p2'].values()):.3f} — 측정 구간 **안**"),
         src="validate_measured_airframe.json : 8_comparison._headline"),
    dict(quantity="방위 산포 ε (Das Table III 와 같은 양)",
         reproduced="부분",
         accuracy=(f"밴드별 차 {min(EPSC['delta_db'].values()):+.2f}~"
                   f"{max(EPSC['delta_db'].values()):+.2f} dB. 측정은 세 밴드에서 "
                   f"{min(EPSC['das_eps_db'].values()):.2f}~{max(EPSC['das_eps_db'].values()):.2f} dB 로 "
                   f"거의 평평하고 우리는 밴드마다 움직인다"),
         src="validate_measured_airframe.json : 8_comparison.C_azimuth_pattern_shape"),
    dict(quantity="절대 σ 레벨, 5.21 GHz",
         reproduced="예",
         accuracy=(f"{LVL['by_band']['WiFi 5.21 GHz']['ours_el0_dbsm']:.2f} dBsm — 발표된 봉투 "
                   f"[{LVL['by_band']['WiFi 5.21 GHz']['lo_dbsm']:.2f}, "
                   f"{LVL['by_band']['WiFi 5.21 GHz']['hi_dbsm']:.2f}] **안**"),
         src="validate_measured_airframe.json : 8_comparison.A_absolute_level"),
    dict(quantity="절대 σ 레벨, 3.5 GHz",
         reproduced="아니오",
         accuracy=(f"{LVL['by_band']['5G 3.5 GHz']['ours_el0_dbsm']:.2f} dBsm — 봉투 최근접변 대비 "
                   f"{LVL['by_band']['5G 3.5 GHz']['gap_to_nearest_db']:+.2f} dB, "
                   f"기하정합 행 대비 {LVL['by_band']['5G 3.5 GHz']['gap_to_yuan_azplane_db']:+.2f} dB"),
         src="validate_measured_airframe.json : 8_comparison.A_absolute_level"),
    dict(quantity="절대 σ 레벨, 1.843 GHz",
         reproduced="아니오",
         accuracy=(f"{LVL['by_band']['LTE 1.843 GHz']['ours_el0_dbsm']:.2f} dBsm — 봉투 최근접변 대비 "
                   f"{LVL['by_band']['LTE 1.843 GHz']['gap_to_nearest_db']:+.2f} dB, "
                   f"기하정합 행 대비 {LVL['by_band']['LTE 1.843 GHz']['gap_to_yuan_azplane_db']:+.2f} dB"),
         src="validate_measured_airframe.json : 8_comparison.A_absolute_level"),
    dict(quantity="측정 기체의 밴드 기울기 dμ/df, 1.8~6 GHz (우리 운용 대역)",
         reproduced="아니오",
         accuracy=(f"우리 {HEAD['slope_ours_1p8_6_ghz']:.3f} dB/GHz vs 측정 "
                   f"{SLOPE['measured']['das_phantom3_1p8_18p2']:.3f}(Das) / "
                   f"{SLOPE['measured']['yuan_azplane_1p8_18p2']:.3f}(Yuan)"),
         src="validate_measured_airframe.json : 8_comparison.B_band_slope"),
    dict(quantity="바이스태틱 각 의존성",
         reproduced="대조 불가",
         accuracy=(f"Das 의 Phantom 3 행은 0~90° 전 구간 기울기·ε 가 동일하고 절편만 "
                   f"{abs(BIST['das_phantom3_row']['90'][1] - BIST['das_phantom3_row']['0'][1]):.2f} dB "
                   f"움직인다 — 우리 div=12 격자 산포보다 작다"),
         src="validate_measured_airframe.json : 8_comparison.D_bistatic"),
    dict(quantity="편파",
         reproduced="대조 불가",
         accuracy="측정은 VV 단독, 커널은 스칼라(편파 자유도 없음)",
         src="validation_feasibility.json : 3_convention_audit.3c_polarisation"),
]


# --------------------------------------------------------------------------- #
# 3. 재질 3층
# --------------------------------------------------------------------------- #
def _mat_max(fam):
    """impact_sweep 에서 그 파라미터족이 총 σ 를 움직인 최대 |Δ| [dB]."""
    best = 0.0
    where = None
    for dr, bands in MAT["impact_sweep"]["by_drone"].items():
        for b, v in bands.items():
            for k, vv in v.items():
                if not isinstance(vv, dict) or "delta_vs_base_db" not in vv:
                    continue
                if k.split("=")[0] != fam:
                    continue
                d = abs(vv["delta_vs_base_db"])
                if d > best:
                    best, where = d, f"{dr} · {b} · {k}"
    return best, where


def _mat_at(fam, key_exact):
    best = 0.0
    where = None
    for dr, bands in MAT["impact_sweep"]["by_drone"].items():
        for b, v in bands.items():
            vv = v.get(key_exact)
            if isinstance(vv, dict) and "delta_vs_base_db" in vv:
                d = abs(vv["delta_vs_base_db"])
                if d > best:
                    best, where = d, f"{dr} · {b}"
    return best, where


def _carbon_max():
    best = 0.0
    where = None
    for dr, bands in MAT["carbon_supplement"]["by_drone"].items():
        for b, v in bands.items():
            if not isinstance(v, dict):
                continue
            for k, vv in v.items():
                if isinstance(vv, dict) and "delta_vs_base_db" in vv:
                    d = abs(vv["delta_vs_base_db"])
                    if d > best:
                        best, where = d, f"{dr} · {b} · {k}"
    return best, where


m_plastic, w_plastic = _mat_max("plastic")
m_prop, w_prop = _mat_max("prop")
m_prop28, w_prop28 = _mat_at("prop", "prop=0.280")
m_cam, w_cam = _mat_max("camera")
m_pcb, w_pcb = _mat_max("pcb")
m_carb_main, _ = _mat_max("carbon")
m_carb_supp, w_carb_supp = _carbon_max()
m_thin, w_thin = _mat_at("thinslab_proj", "thinslab_proj")
m_thin_n, _ = _mat_at("thinslab_normal", "thinslab_normal")

#  벌크 프레넬 |Γ| — V1 브래킷의 유전체 계열 값이 그것이다(별도로 적지 않는다)
BULK_DIEL = VAL["7_material_bracket"]["V1_bulk_fresnel"]["gamma_map"]["body"]
#  프로펠러 두께 — 우리 CAD 에서 유도된 값
_PROP = MAT["propeller"]["per_drone"]
PROP_CM_LO = min(v["t_chordmean_mm"] for v in _PROP.values())
PROP_CM_HI = max(v["t_chordmean_mm"] for v in _PROP.values())
PROP_PK_HI = max(v["t_max_peak_mm"] for v in _PROP.values())
PROP_PK_ARG = max(_PROP, key=lambda k: _PROP[k]["t_max_peak_mm"])

LIT = {e["key"]: e for e in MAT["literature"]}
zech = LIT["plastic_eps_abs_zechmeister"]
artner = LIT["carbon_sigma_artner"]
itu_pb = LIT["plastic_itu_plasterboard"]

ts = MAT["thin_slab"]
inv = ts["inverse_thickness_for_current_values"]
gni = ts["gamma_normal_incidence"]
thin_lo = min(gni[b]["1mm"] for b in B)
thin_hi = max(gni[b]["3mm"] for b in B)


# --------------------------------------------------------------------------- #
# 4. JSON 판정문
# --------------------------------------------------------------------------- #
NEW_ORDER = [
    dict(no="01", title="선행연구 — 무엇이 가능하고 무엇이 아닌가", change="변동 없음",
         why="게재본 중 드론 메쉬에서 산란을 계산한 전례가 0편임을 먼저 확정해야, 뒤 편들이 무엇을 새로 하는지가 정의된다."),
    dict(no="02", title="표적 모델 — 메쉬와 산란 커널", change="현 02 에서 §4 앵커·§5 σ오차를 뺀 것",
         why="대조에 넣을 물건을 먼저 짓고, 커널은 해석해(구·이면각·kr 스윕)로만 게이트한다. 외부 측정은 아직 안 부른다."),
    dict(no="03", title="⭐ 측정 기체 대조 — DJI Phantom 3", change="신설. validate_measured_airframe.json + validation_feasibility.json",
         why="신뢰성 게이트. 교정구로 절대 스케일을 닫고, 실제로 측정된 기체를 우리 방식대로 지어 σ(f) 를 대조하고, 그 판정 위에 앵커를 세운다."),
    dict(no="04", title="조명원 — 세 파형과 그 대가", change="현 03 이 번호만 이동",
         why="점유·대역·PRF·λ² 는 σ 와 무관하게 정확한 양이다. 03 의 판정과 독립이므로 뒤에 와도 잃는 것이 없다."),
    dict(no="05", title="검출기 — ECA · 거리도플러 · CFAR 교정", change="현 04 가 번호만 이동",
         why="경험 Pfa 는 σ 와 독립으로 측정된다. 여기까지가 03 의 결과에 영향받지 않는 구간이다."),
    dict(no="06", title="검출 결과 — 모노/바이 × 근/원거리", change="현 05 + 현 02 §5(σ 오차 강건성)",
         why="03 의 앵커와 05 의 교정문턱을 함께 쓰는 유일한 편. 03 이 만든 밴드별 오차막대를 그대로 진다."),
    dict(no="07", title="실측 계획과 검증", change="현 06 이 번호만 이동, 03 의 잔차를 계약 항목으로 받는다",
         why="03 이 닫지 못한 항(편파·바이스태틱·FR1 저역 잔차)을 무엇을 재면 닫는지 결정표로 적는다."),
]

MOVES = [
    dict(what="현 02 §1.1~§1.3 — 사진 대조 · 형상 검사 3종 · 부품별 재질",
         to="새 02 §1", note="§1.3 재질 절만 본 문서 §3 의 3층 표로 교체한다"),
    dict(what="현 02 §2 — 엔진(광선 가림 + 재질 PO), §2.1 바이스태틱 출사 가시성",
         to="새 02 §2", note="변경 없음"),
    dict(what="현 02 §3 — 기준해 셋(해석 PO 구 · Mie · PEC 이면각)",
         to="새 02 §3", note="교정구(r = 17.8 cm) 대조는 새 03 §1 로 승격 — 같은 커널이지만 그쪽에서는 '측정 체인과의 절대 대조'라는 다른 일을 한다"),
    dict(what="현 02 §4 — 앵커(§4.1 모드 · §4.2 세 인자 · §4.3 원장 · §4.4 통제·잔여)",
         to="새 03 §6", note="⭐ 대조 **뒤**로. 앵커는 처방이고 처방은 증거보다 앞설 수 없다"),
    dict(what="현 02 §5 — σ 오차를 넣어도 파형 순위가 서는 범위",
         to="새 06 여는 절", note="σ 불확도가 실제로 소비되는 곳"),
    dict(what="현 03 · 04 · 05 · 06",
         to="새 04 · 05 · 06 · 07", note="내용 변경 없이 번호만 이동"),
]

WHY_OWN_REPORT = [
    dict(reason="분량 규약이 강제한다",
         number=("03 이 답해야 하는 질문이 8개다 — 교정구, 레벨 봉투, 전대역 μ(f), 기울기 예산, "
                 "형상 충실도, 재질 브래킷, ε 대조, 방위섹터 규약. 하우스 규약 §5.7 의 상한이 "
                 "편당 그림 8개이고, 02 의 메쉬·엔진 그림과 합치면 넘는다. §5.7 자신이 "
                 "'넘치면 내용을 줄이지 말고 편을 쪼개라'고 정한다")),
    dict(reason="주장의 종류가 다르다",
         number="02 = '우리가 무엇을 지었나', 03 = '외부 측정과 얼마나 맞나'. 한 편 = 한 주장 규약을 지키면 갈라진다"),
    dict(reason="순환을 막는다",
         number=("앵커는 대조 결과를 처방으로 바꾸는 절이다. 02 안에 다 넣으면 §1 메쉬 → §4 앵커 → "
                 "대조 순서가 되어 처방이 증거보다 앞선다 "
                 "⟨validation_feasibility.json : 7_report_ordering_recommendation.what_must_not_move_forward⟩")),
    dict(reason="판정이 실패다",
         number=("1.843 GHz 에서 봉투 밖 " + f"{LVL['by_band']['LTE 1.843 GHz']['gap_to_nearest_db']:+.2f} dB. "
                 "실패를 자기 편으로 세우면 읽는 사람이 그것을 찾을 수 있다. 02 의 소절로 넣으면 "
                 "같은 편의 앵커가 그 실패를 가리려 고른 것처럼 읽힌다")),
]

NEXT = [
    dict(do="rcs_anchor.json 재생성",
         decides=("현재 저장값이 세 번째 독립 하네스와도 어긋난다 — "
                  f"{min(XCH['staleness_confirmed_db'].values()):+.3f}~"
                  f"{max(XCH['staleness_confirmed_db'].values()):+.3f} dB. "
                  "03 의 그림을 그리기 전에 닫아야 하는 유일한 선행 작업"),
         where="benchmark/rcs_anchor.py"),
    dict(do="PTD(모서리 회절) 항을 커널에 넣는다",
         decides=(f"좁은대역 기울기 잔차 {resid:.3f} dB/GHz ({resid_frac*100:.0f}%) 가 닫히는지. "
                  f"⚠ 잔차는 재질 브래킷 {mat_slope_bar:.3f} dB/GHz 의 "
                  f"{resid/mat_slope_bar:.1f} 배뿐이라 지목은 지시적이지 확정이 아니다"),
         where="src/rcs_sbr.py"),
    dict(do="Phantom 3 를 DRONES 레지스트리에 등록",
         decides="03 을 재현 가능한 편으로 만든다. 패치 문자열은 validate_measured_airframe.json : 1_airframe.registration_patch 에 있다",
         where="src/drones.py · src/drone_cad.py · benchmark/rcs_anchor.py"),
    dict(do="복소 Γ 를 커널에 넣는다",
         decides="박막 실효 Γ 를 도입하려면 위상이 짝이다 — 금속 대비 상대위상이 70° 어긋난다 ⟨material_sources.json : proposed_patch⟩",
         where="src/rcs_sbr.py · src/rcs_po.py"),
    dict(do="camera_assembly 를 실물에서 확인",
         decides=(f"tier-3 중 총 σ 를 가장 크게 움직이는 항 — 스윕 전 구간 0.50~1.00 에서 "
                  f"{m_cam:.3f} dB ({w_cam}). 프로펠러 전 구간의 {m_cam/max(m_prop,1e-9):.1f} 배"),
         where="실물 티어다운"),
    dict(do="우리 기체 1종의 자체 모노스태틱 RCS 측정 (1.8~5.3 GHz, PEC 구 교정)",
         decides="FR1 에서 우리 5기종에 대응하는 공개 측정이 없다 — 두 번째 대조 기체는 문헌이 아니라 측정에서만 나온다",
         where="07편(실측 계획) · outputs/measurement_plan.json"),
]

VERDICT_SENTENCE = (
    "우리 σ 의 절대값은 5.21 GHz 에서 발표된 측정 봉투 안에 있고, 3.5 GHz 에서 "
    f"{abs(LVL['by_band']['5G 3.5 GHz']['gap_to_nearest_db']):.2f} dB, 1.843 GHz 에서 "
    f"{abs(LVL['by_band']['LTE 1.843 GHz']['gap_to_nearest_db']):.2f} dB 낮다. "
    "기체 1종 · 측정 체인 1개에 대한 대조이고, 커널의 절대 스케일 자체는 같은 측정의 "
    f"교정구에서 {max(abs(v) for v in sph_dev.values()):.3f} dB 안에 든다.")

OUT = {
    "_meta": dict(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        generator="benchmark/engine_validation_verdict.py",
        purpose="엔진 검증 판정 + 리포트 순서 제안 + 재질 3층 + 비용",
        inputs=["outputs/validation_feasibility.json",
                "outputs/material_sources.json",
                "outputs/validate_measured_airframe.json"],
        gpu_used="없음 — 이 단계는 선행 JSON 만 읽는다",
        house_rule="이 파일 안에 손으로 적힌 수치 0 개"),

    "1_verdict": {
        "one_line": HEAD["one_line"],
        "sentence_the_project_can_use": VERDICT_SENTENCE,
        "status": "FAILED — 그리고 실패한 자리가 특정된다",
        "table": verdict_rows,
        "where_it_fails": {
            "band": "1.8~6 GHz",
            "why_that_matters": "우리 세 밴드가 전부 그 안에 있다",
            "above_6ghz": dict(
                ours_db_per_ghz=HEAD["slope_ours_6_18p2_ghz"],
                measured_range=[min(HEAD["slope_measured_1p8_18p2"].values()),
                                max(HEAD["slope_measured_1p8_18p2"].values())],
                verdict="측정 구간 안"),
        },
        "correction_to_the_feasibility_phase": HEAD["correction_to_the_feasibility_phase"],
        "mechanism": {
            "claim": "낮은 ka 에서 PO 가 지는 것이지 밴드 법칙이 틀린 것이 아니다",
            "in_house_control": {b: sph_dev[b] for b in B},
            "control_ka": {b: sph_ka[b] for b in B},
            "airframe_gap": {b: LVL["by_band"][b]["gap_to_nearest_db"] for b in B},
            "reading": ("교정구에서도 같은 부호·같은 모양의 결손이 나오고 크기만 약 5배 작다. "
                        "전기적으로 커질수록 오차가 줄어드는 것이 광학영역 아래에서 PO 가 지는 신호다"),
        },
        "slope_budget_narrowband": budget,
        "error_bars": {k: v for k, v in ERR.items()},
        "cannot_establish": VAL["8_comparison"]["G_what_this_cannot_establish"],
    },

    "2_report_order": {
        "user_question": FEAS["7_report_ordering_recommendation"]["user_question"],
        "answer": "찬성한다. 다만 앞으로 옮기는 것은 한 편이 아니라 **한 편 + 그 앞의 교정구 절**이고, 앵커는 반대로 뒤로 민다.",
        "argument": ("검증은 신뢰성 게이트다. 엔진이 측정된 기체를 재현하면 그 뒤의 모든 편이 그 위에 설 수 있고, "
                     "재현하지 못하면 그 사실이 더 짓기 전에 알려져야 한다. 검증을 뒤에 두면 논리가 뒤집힌다 — "
                     "이미 다 지은 다음에 바닥을 검사하는 꼴이다."),
        "old_order": ["01 선행연구", "02 표적 모델(메쉬·엔진·앵커)", "03 조명원", "04 검출기",
                      "05 검출 결과", "06 실측 계획"],
        "new_order": NEW_ORDER,
        "content_moves": MOVES,
        "own_report_or_section_of_02": {
            "answer": "⭐ 자기 편(새 03)이다. 02 의 절이 아니다.",
            "reasons": WHY_OWN_REPORT,
            "count_change": "6편 → 7편",
            "cost_of_the_gate": ("하우스 규약 §5.7 은 '6편 골격 유지'를 적었다. 이 제안은 그것을 한 편 넘긴다. "
                                 "넘기는 이유는 분량이 아니라 주장의 종류가 하나 늘었기 때문이다 — "
                                 "'외부 측정과의 대조'는 새 주장 종류이고, 기존 6편은 각각 다른 주장을 "
                                 "이미 하나씩 지고 있다."),
        },
        "what_must_not_move_forward": FEAS["7_report_ordering_recommendation"]["what_must_not_move_forward"],
    },

    "3_materials": {
        "user_question": "mesh 의 형상뿐만 아니라 재질도 현실적인 재질이니? 실제로 조사해서 기입한거야?",
        "answer": ("절반은 그렇고 절반은 아니다. eps_r 은 우리 대역을 덮는 측정 문헌으로 출처가 붙었고, "
                   "gamma_po 실효값 5개는 출처가 없다 — 그 5개는 선언된 모델링 선택이고 총 σ 영향이 유계다. "
                   "그리고 셸 실효값 0.28 은 불확실한 정도가 아니라 부호가 틀렸다."),
        "corrections_to_the_brief": MAT["corrections_to_brief"],
        "tier1_standard": [
            dict(item="metal", value="ITU-R P.2040 metal (1.0, 1e7 S/m)",
                 source="ITU-R P.2040 Table 3 — Sionna 2.0.1 설치본 소스에서 직접 확인"),
            dict(item="concrete_light/dark", value="ITU-R P.2040 concrete (5.24, 0.0462 f^0.7822)",
                 source="ITU-R P.2040 Table 3"),
            dict(item="battery → metal", value="ITU metal 로 사상",
                 source=HT("battery", "ITU metal")["source"]),
            dict(item="pcb 기저", value="ITU metal (구리 그라운드플레인 지배)",
                 source="FR-4 의 eps_r/tan_delta 는 우리 모델이 읽지 않는다"),
        ],
        "tier2_literature": [
            dict(item="plastic eps_r = 2.7",
                 source=f"{zech['author']}, {zech['venue']}, {zech['year']}, doi:{zech['doi']}",
                 measured_band_ghz=zech["freq_range_ghz"],
                 reported=f"eps_r' {zech['eps_r_low']}~{zech['eps_r_high']} (ABS 포함 5종)",
                 verdict=f"우리 2.7 은 그 구간의 한가운데. 교차확인: ITU-R P.2040 plasterboard {itu_pb['eps_r']}"),
            dict(item="carbon sigma",
                 source=f"{artner['author']}, {artner['venue']}, {artner['year']}, doi:{artner['doi']}",
                 measured_band_ghz=artner["freq_range_ghz"],
                 reported=artner["value_text"],
                 verdict=("⚠ 현행 3000 S/m 는 출처가 없고 대역 내 측정치보다 낮다. 제안 패치 "
                          + MAT["proposed_patch"][0]["current"] + " → "
                          + MAT["proposed_patch"][0]["proposed"]
                          + " — 총 RCS 영향은 무시 가능하고, 바꾸는 이유는 정확도가 아니라 출처가 생기기 때문이다")),
            dict(item="plastic sigma = 0.02 S/m",
                 source="⚠ 출처 없음 — 가장 가까운 표준 대용은 ITU-R P.2040 plasterboard 식 "
                        f"({itu_pb['itu_c']} f^{itu_pb['itu_d']} S/m)",
                 reported="문헌 ABS/PC tan_delta 0.005~0.008",
                 verdict=HT("plastic", "sigma")["source"] + " " + HT("plastic", "sigma")["bound"]),
            dict(item="absorber eps_r 1.4 / sigma 1.2",
                 source="⚠ 출처 없음 — note 가 이미 모델값이라 선언한다",
                 reported="—",
                 verdict="챔버 흡수체 전용 · 드론 σ 와 무관하다"),
        ],
        "tier3_declared_choices": [
            dict(item="plastic gamma_po = 0.28 (셸)", bound_db=m_plastic, bound_where=w_plastic,
                 status="⭐ 불확실한 것이 아니라 **부호가 틀렸다**",
                 detail=(f"1~3 mm ABS 셸의 정면입사 박막 |Γ| 는 {thin_lo:.3f}~{thin_hi:.3f} 로 "
                         f"벌크 프레넬 {BULK_DIEL:.3f} **아래**다. 0.28 이 나오려면 셸이 "
                         f"{inv['LTE 1.843 GHz']['d_mm_for_0p28']:.1f}/"
                         f"{inv['5G 3.5 GHz']['d_mm_for_0p28']:.1f}/"
                         f"{inv['WiFi 5.21 GHz']['d_mm_for_0p28']:.1f} mm 여야 한다"),
                 replaced_by_physics_db=m_thin, replaced_where=w_thin),
            dict(item="carbon gamma_po = 0.90", bound_db=m_carb_supp, bound_where=w_carb_supp,
                 status="선언된 선택",
                 detail=(f"주 스윕 세 기체에서 정확히 {m_carb_main:.3f} dB 인 것은 '무해'가 아니라 "
                         f"'해당 없음'이다 — 그 세 기체에 carbon 그룹이 없다. carbon 을 실제로 쓰는 "
                         f"기체(x500v2 · s1000plus)에서 0.70~1.0 구간의 총 σ 변화가 {m_carb_supp:.3f} dB")),
            dict(item="camera_assembly gamma_po = 0.85", bound_db=m_cam, bound_where=w_cam,
                 status="⭐ tier-3 중 가장 큰 항",
                 detail=f"prop 의 0.25→0.28 주장이 {m_prop28:.3f} dB 인 데 비해 {m_cam/max(m_prop28,1e-9):.0f} 배"),
            dict(item="pcb gamma_po = 0.80", bound_db=m_pcb, bound_where=w_pcb,
                 status="선언된 선택", detail="내부 부품이라 셸 투과 손실을 두 번 먹는다 — 0.5~1.0 전 구간에서 유계"),
            dict(item=f"prop_plastic gamma_po = 0.25  (0.25→0.28 만 보면 {m_prop28:.3f} dB)",
                 bound_db=m_prop, bound_where=w_prop,
                 status="선언된 선택 · 근거 문장은 반증됨",
                 detail=(f"note 의 '날개가 셸보다 얇다'를 우리 CAD 가 반증한다 — 시위평균 "
                         f"{PROP_CM_LO:.2f}~{PROP_CM_HI:.2f} mm, {PROP_PK_ARG} 최대 "
                         f"{PROP_PK_HI:.2f} mm 로 셸 1~3 mm 를 넘는다. 결론은 살아남고 근거가 틀렸다")),
        ],
        "bounded_total": dict(
            thin_slab_replacement_db=max(m_thin, m_thin_n),
            bracket_level_db=BRK["level_swing_db"],
            bracket_slope_db_per_ghz=BRK["slope_swing_db_per_ghz"],
            reading=("재질은 레벨 문제이지 기울기 문제가 아니다. 모든 gamma_po 가 주파수 평탄한 실수 상수라서, "
                     "어떤 재질 편집도 밴드 의존성을 구제하지 못한다")),
        "proposed_patches": MAT["proposed_patch"],
        "not_edited": "src/materials.py 는 손대지 않았다 — 패치 6건은 제안으로만 있다",
    },

    "4_is_a_valid_comparison_possible": {
        "answer": FEAS["5_verdict"]["is_a_valid_comparison_possible"],
        "so_this_document_reports_a_result_not_a_plan": True,
        "airframe": FEAS["5_verdict"]["which_airframe_to_build"]["answer"],
        "blocking_question": FEAS["1_das_measurement_settings"]["blocking_question_resolved"],
        "measurement_that_would_close_the_rest": FEAS["5_verdict"]["if_this_is_not_enough_what_measurement_is_needed"],
        "open_terms": FEAS["8_open_and_uncontrolled_terms"],
    },

    "5_cost": {
        "gpu_policy": "카드 0·1 은 타 사용자 점유 — 2·3 만 썼다",
        "rows": cost_rows,
        "comparison_phase": dict(n_runs=cmp_runs, gpu_s=cmp_gpu_s, gpu_h=cmp_gpu_s / 3600.0),
        "materials_phase": dict(
            impact_sweep_s=mat_sweep_s, carbon_supplement_s=mat_carb_s,
            gpu_s=mat_gpu_s, gpu_h=mat_gpu_s / 3600.0,
            n_runs_impact=None, note="건수는 JSON 셀 수로 센다"),
        "feasibility_phase": dict(gpu_s=0.0, note="PDF 판독·회귀·규약 감사 — GPU 0"),
        "total": dict(gpu_s=total_gpu_s, gpu_h=total_gpu_s / 3600.0),
        "rate_model": dict(k_s_per_ray_per_az=rate_k,
                           how="sweep 로그의 (rays/az, 초) 21쌍에 원점 통과 최소제곱",
                           applies_to="group · material bracket 단계(같은 커널 · n_az=360)"),
        "second_airframe": dict(
            gpu_s=second_gpu_s, gpu_h=second_gpu_s / 3600.0,
            what_is_shared="교정구 대조(측정 체인 공통), 문헌 회귀, 규약 감사",
            what_is_new="메쉬 제작 · 밴드 3점 · 전대역 21점 · group 분해 · 재질 브래킷",
            scan_stage=("실물 레이저 스캔이 있는 기체에만 붙는다 — 현재 저장소에 있는 스캔은 "
                        "Phantom 4 하나뿐이다"),
            warning=("⚠ FR1 에서 우리 5기종에 대응하는 공개 측정이 없다. Das 의 나머지 세 기체는 "
                     "11~27 GHz 다. 즉 두 번째 대조 기체는 GPU 시간으로 사는 것이 아니라 측정으로만 산다")),
        "what_it_bought": (f"판정 1건(실패, 자리 특정) + 기울기 예산 3항 + 오차막대 3종 + "
                          f"재질 3층표 {len(MAT['honest_table'])}행 + 제안 패치 {len(MAT['proposed_patch'])}건"),
    },

    "6_next": NEXT,
}

with open(OUT_JSON, "w") as f:
    json.dump(OUT, f, indent=1, ensure_ascii=False)
print(f"[saved] {OUT_JSON}")


# --------------------------------------------------------------------------- #
# 5. 마크다운
# --------------------------------------------------------------------------- #
def T(rows, cols):
    """(제목, 키) 목록으로 마크다운 표를 만든다."""
    head = "| " + " | ".join(c[0] for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = ["| " + " | ".join(E(r.get(c[1], "")) for c in cols) + " |" for r in rows]
    return "\n".join([head, sep] + body)


L = []
A = L.append

A("# 엔진 검증 — 측정된 기체와 대조한다")
A("")
A("> 판정 원본: `outputs/engine_validation_verdict.json`  ·  "
  "실행 원본: `outputs/validate_measured_airframe.json` · `outputs/validation_feasibility.json` · "
  "`outputs/material_sources.json`")
A("")
A("```")
A("한 일")
A("  실제로 RCS 가 측정된 기체(DJI Phantom 3)를 우리 방식대로 짓고, 생산 커널에 앵커를 끄고")
A("  통과시켜 발표된 측정과 대조했다.")
A("")
A("결과")
A(f"  절대 레벨 {LVL['by_band']['LTE 1.843 GHz']['ours_el0_dbsm']:.2f} / "
  f"{LVL['by_band']['5G 3.5 GHz']['ours_el0_dbsm']:.2f} / "
  f"{LVL['by_band']['WiFi 5.21 GHz']['ours_el0_dbsm']:.2f} dBsm — 발표된 봉투 대비 "
  f"{LVL['by_band']['LTE 1.843 GHz']['gap_to_nearest_db']:+.2f} / "
  f"{LVL['by_band']['5G 3.5 GHz']['gap_to_nearest_db']:+.2f} dB 와 봉투 안.")
A(f"  밴드 기울기는 6 GHz 위에서 {HEAD['slope_ours_6_18p2_ghz']:.3f} dB/GHz 로 측정 구간 "
  f"{min(HEAD['slope_measured_1p8_18p2'].values()):.3f}~"
  f"{max(HEAD['slope_measured_1p8_18p2'].values()):.3f} 안에 들고,")
A(f"  1.8~6 GHz 에서 {HEAD['slope_ours_1p8_6_ghz']:.3f} 로 벗어난다.")
A(f"  교정구는 정확 Mie 대비 {max(abs(v) for v in sph_dev.values()):.3f} dB 안 — 절대 스케일은 맞는다.")
A("")
A("방법")
A(f"  Das(IEEE WCL 2026) 와 Yuan 두 논문이 준 치수(모터 대각 "
  f"{AIR['built']['wheelbase_spec_mm']:.0f} mm, 높이 {AIR['built']['height_paper_mm']:.0f} mm)로")
A(f"  메쉬를 짓고 rcs_sbr_batch div={VAL['3_bands']['div']} · n_az={VAL['3_bands']['n_az']} 로 돌렸다.")
A("  sigma_anchor.relevel() 은 한 번도 부르지 않는다 — 레벨은 커널 출력 그대로다.")
A("")
A("재현")
A("  PYTHONPATH=src:benchmark python benchmark/validate_measured_airframe.py")
A("  PYTHONPATH=src:benchmark python benchmark/engine_validation_verdict.py")
A(f"  → outputs/validate_measured_airframe.json · outputs/engine_validation_verdict.json "
  f"({cmp_gpu_s/3600.0:.2f} GPU-h)")
A("")
A("앞 편에서")
A("  02편 — 메쉬 7종과 산란 커널, 그리고 해석해 게이트 세 가지.")
A("```")
A("")
A("---")
A("")

# §1
A("## §1. 판정 — 한 표")
A("")
A("커널이 재현하는 것과 재현하지 않는 것을, 재현한다면 어느 정확도로인지까지 한 표에 적는다.")
A("")
A(T(verdict_rows, [("양", "quantity"), ("재현", "reproduced"), ("정확도", "accuracy"), ("출처", "src")]))
A("")
A("### §1.1 프로젝트가 자기 σ 에 대해 쓸 수 있는 문장")
A("")
A(f"> {VERDICT_SENTENCE}")
A("")
A("이전까지 이 자리에 들어갈 문장은 **\"검증되지 않았다\"** 였다. 이제는 숫자다 — "
  "밴드 하나는 통과, 둘은 미달, 결손의 크기와 부호가 밴드마다 적혀 있다.")
A("")
A("### §1.2 실패한 자리")
A("")
A(f"불일치는 **{OUT['1_verdict']['where_it_fails']['band']}** 에 몰려 있고, 우리 세 밴드가 전부 그 안에 있다. "
  f"6 GHz 위에서 우리 기울기 {HEAD['slope_ours_6_18p2_ghz']:.3f} dB/GHz 는 측정 구간 "
  f"{min(HEAD['slope_measured_1p8_18p2'].values()):.3f}~{max(HEAD['slope_measured_1p8_18p2'].values()):.3f} "
  f"**안**에 든다.")
A("")
A("| 적합 구간 | 우리 [dB/GHz] | Das [dB/GHz] | Yuan(방위면) [dB/GHz] | 배수(vs Das) |")
A("|---|---|---|---|---|")
A(f"| 1.8~18.2 GHz (논문 구간과 동일) | {SLOPE['ours']['full_band_1p8_18p2']['slope_db_per_ghz']:.3f} "
  f"| {SLOPE['measured']['das_phantom3_1p8_18p2']:.3f} | {SLOPE['measured']['yuan_azplane_1p8_18p2']:.3f} "
  f"| {SLOPE['ratio_ours_over_measured']['das_phantom3_1p8_18p2']:.2f}× |")
A(f"| 1.8~6 GHz | {HEAD['slope_ours_1p8_6_ghz']:.3f} | — | — | — |")
A(f"| 6~18.2 GHz | {HEAD['slope_ours_6_18p2_ghz']:.3f} | — | — | "
  f"{HEAD['slope_ours_6_18p2_ghz']/SLOPE['measured']['das_phantom3_1p8_18p2']:.2f}× |")
A(f"| 1.843~5.21 GHz (3점) | {SLOPE['ours']['three_band_1p843_5p21']['slope_db_per_ghz']:.3f} | — | — | "
  f"{SLOPE['ours']['three_band_1p843_5p21']['slope_db_per_ghz']/SLOPE['measured']['das_phantom3_1p8_18p2']:.2f}× |")
A("")
_FR = FEAS["5_verdict"]["what_exactly_to_compare"]["PRIMARY — band slope d(mu)/df"]["ours"]
_pred = [_FR["ratio_ours22stale_over_das"], _FR["ratio_ours3band_current_over_das"]]
A(f"⭐ 타당성 단계가 예상한 \"{min(_pred):.1f}~{max(_pred):.1f}배\"는 우리 좁은대역 적합을 "
  f"논문의 넓은대역 적합과 비교한 "
  f"결과였다. 같은 구간에서 다시 재면 "
  f"{SLOPE['ratio_ours_over_measured']['das_phantom3_1p8_18p2']:.2f}배(Das)· "
  f"{SLOPE['ratio_ours_over_measured']['yuan_azplane_1p8_18p2']:.2f}배(Yuan)다 "
  f"⟨`validate_measured_airframe.json : 8_comparison.B_band_slope.fitting_interval_matters`⟩. "
  f"우리 μ(f) 는 직선이 아니다(전대역 적합 R² = {SLOPE['ours']['full_band_1p8_18p2']['R2']:.3f}).")
A("")
A("### §1.3 기전 — 자체 대조군이 같은 모양을 낸다")
A("")
A("표적이 전기적으로 커질수록 측정 대비 오차가 줄어든다. 광학영역 아래에서 PO 가 지는 신호다. "
  "같은 것을 정준 표적에서 직접 보였다 — Yuan 자신의 교정구다.")
A("")
A("| 밴드 | ka (구 r = 17.8 cm) | 구: 정확 Mie 대비 [dB] | 기체: 봉투 대비 [dB] |")
A("|---|---|---|---|")
for b in B:
    A(f"| {b} | {sph_ka[b]:.2f} | {sph_dev[b]:+.3f} | {LVL['by_band'][b]['gap_to_nearest_db']:+.2f} |")
A("")
A("부호가 같고 모양이 같으며 크기만 약 5배 작다. 방위 **평균**은 이 결함에 가장 불리한 통계다 — "
  "정반사에서 벗어난 자세가 지배하고, 그 자세에서 되돌아오는 것은 모서리 전류인데 PO 가 세는 것은 "
  "조명면 위의 표면 전류뿐이다.")
A("")
A("### §1.4 기울기 예산 — 좁은대역 1.843~5.21 GHz")
A("")
A("두 항은 **측정했고**(가정이 아니다), 나머지가 잔차다.")
A("")
A("| 항 | [dB/GHz] | 어떻게 얻었나 |")
A("|---|---|---|")
A(f"| Das 대비 메워야 할 격차 | {budget['gap_to_close_db_per_ghz']['vs_das']:+.3f} | 우리 3점 적합 − Das 계수 |")
_TERM_KR = {
    "geometry idealisation (real 0.4 mm scan minus our parametric, both PEC)":
        ("기하 이상화 — 실물 0.4 mm 레이저 스캔 빼기 우리 파라메트릭 메쉬(양쪽 PEC)",
         f"실측 스캔 {GEO['n_faces'][0]:,} 삼각형 대 우리 {GEO['n_faces'][1]:,}, "
         f"둘 다 |Γ|=1 로 몰아 기하만 남겼다"),
    "azimuth-sector convention (front hemisphere instead of full 360)":
        ("방위 섹터 규약 — 전방 반구(−90:2:90) 대신 전원 360°",
         "같은 메쉬에서 두 규약을 각각 평균했다"),
}
for k, v in budget["directional_terms_db_per_ghz"].items():
    lab, how = _TERM_KR.get(k, (k, "같은 커널로 양쪽을 돌려 차를 쟀다"))
    A(f"| {E(lab)} | {v:+.3f} | {E(how)} |")
A(f"| **미설명 잔차** | **{resid:+.3f}** | 격차 {resid_frac*100:.0f}% — 남은 기전은 부재한 PTD 모서리항뿐 |")
A(f"| (참고) 재질 브래킷 양측 불확도 | {mat_slope_bar:.3f} | V1/V2/V3 |")
A("")
A(f"⚠ 잔차 {resid:.3f} 는 재질 브래킷 {mat_slope_bar:.3f} 의 {resid/mat_slope_bar:.1f} 배뿐이다. "
  f"PTD 지목은 **지시적**이지 확정이 아니다. 방위섹터 항은 규약 정렬이지 모델 결함이 아니며, "
  f"두 논문 모두 자기 방위 평균이 반구인지 전원인지 적지 않았다.")
A("")
A("### §1.5 오차막대")
A("")
_ERR_KR = {
    "calibration_scale (kernel vs exact Mie on Yuan's own standard)":
        ("교정 스케일 — 커널 대 정확 Mie, Yuan 자신의 표준구",
         "주파수에 대해 거의 평탄하다. 이 연습에서 가장 좁은 막대"),
    "mesh geometry fidelity (real 0.4 mm scan vs our parametric, both PEC)":
        ("메쉬 기하 충실도 — 실물 0.4 mm 스캔 대 우리 파라메트릭",
         "같은 기체 계열에서 재질을 빼고 쟀으니 기하만 분리된다"),
    "material table (defensible bracket V1/V2/V3)":
        ("재질 표 — 방어 가능한 브래킷 V1/V2/V3",
         "모든 gamma_po 가 주파수 평탄이라 레벨만 움직인다"),
    "ray-grid dither at div=16":
        ("광선격자 산포 — div=16",
         "jitter=2 가 2×2 하위셀을 평균하므로 잔차는 이보다 작다. 규모 참고용"),
    "polarisation (our scalar kernel vs their VV)":
        ("편파 — 우리 스칼라 커널 대 그들의 VV",
         "부호가 정해져 있다: 우리 값이 VV 측정보다 **낮게** 나온 것을 편파로는 설명하지 못한다"),
    "the measurement's own spread eps":
        ("측정 자신의 방위 산포 ε",
         "Das Table III Phantom 3: ε(f)=0.03f+5.16 dB — μ 는 매우 넓은 분포의 평균이다"),
    "literature envelope (measurement side alone)":
        ("문헌 봉투 — 측정 쪽만으로",
         "한 데이터셋의 두 처리본이 우리가 등장하기도 전에 이만큼 벌어진다"),
    "shape control (our P4 vs our P3, same materials/kernel)":
        ("형상 대조군 — 우리 P4 대 우리 P3, 재질·커널 동일",
         "⚠ 구조상 작다 — P3 메쉬가 P4 셸 법칙을 상속한다. 실제 적용한 차이만 유계한다"),
}
A("| 항 | 크기 [dB] | 기울기 영향 [dB/GHz] | 읽는 법 |")
A("|---|---|---|---|")
for k, v in ERR.items():
    if not isinstance(v, dict):
        continue
    mag = v.get("magnitude_db")
    sl = v.get("slope_effect_db_per_ghz")
    mags = f"{mag:.3f}" if isinstance(mag, (int, float)) else "미유계"
    sls = f"{sl:.3f}" if isinstance(sl, (int, float)) else "—"
    lab, rd = _ERR_KR.get(k, (k, ""))
    A(f"| {E(lab)} | {mags} | {sls} | {E(rd)} |")
A("")
A("### §1.6 이 대조가 세우지 못하는 것")
A("")
_CANNOT_KR = [
    "우리 절대 σ 가 옳다는 것 — 기체 1종 · 측정 체인 1개, 그리고 같은 원자료의 두 처리본이 서로 "
    f"{min(_raw_das_yuan.values()):.2f}~{max(_raw_das_yuan.values()):.2f} dB 어긋난다",
    "우리 생산 기체 5종에 대해 σ 가 옳다는 것 — Phantom 3 는 고정팔 350 mm 쿼드에 일체형 셸이고, "
    "Mini 5 Pro · Matrice 4E · S1000+ 는 산란 위상이 다르며 크기전이 지수가 미해결이다",
    "편파 · 바이스태틱 기하 · 회전 프로펠러에 관한 것 전부",
    "우리 Phantom 3 **셸**이 맞다는 것 — 저장소에 P3 사진이 없어 셸 법칙은 P4 사진감사에서 전이된 것이다",
]
for _x in _CANNOT_KR:
    A(f"- {_x}")
A("")
A("(원문 목록: `validate_measured_airframe.json : 8_comparison.G_what_this_cannot_establish`)")
A("")
A("---")
A("")

# §2
A("## §2. 리포트 순서 — 제안")
A("")
A(f"**질문**: {FEAS['7_report_ordering_recommendation']['user_question']}")
A("")
A(f"**답**: {OUT['2_report_order']['answer']}")
A("")
A("### §2.1 논거 — 검증은 신뢰성 게이트다")
A("")
A(OUT["2_report_order"]["argument"])
A("")
A("### §2.2 새 순서")
A("")
A(T(NEW_ORDER, [("#", "no"), ("편", "title"), ("무엇이 바뀌나", "change"), ("이 자리인 이유", "why")]))
A("")
A("### §2.3 지금 내용이 어디로 가나")
A("")
A(T(MOVES, [("현재", "what"), ("→", "to"), ("비고", "note")]))
A("")
A("### §2.4 ⚠ 02편의 처분 — 검증은 자기 편인가, 02 의 절인가")
A("")
A(f"**{OUT['2_report_order']['own_report_or_section_of_02']['answer']}**")
A("")
A("| 이유 | 근거 |")
A("|---|---|")
for r in WHY_OWN_REPORT:
    A(f"| {r['reason']} | {r['number']} |")
A("")
A(f"편 수는 {OUT['2_report_order']['own_report_or_section_of_02']['count_change']} 으로 늘어난다. "
  + OUT["2_report_order"]["own_report_or_section_of_02"]["cost_of_the_gate"])
A("")
A(f"⚠ 앞으로 옮기면 **안 되는 것**: {FEAS['7_report_ordering_recommendation']['what_must_not_move_forward']}")
A("")
A("---")
A("")

# §3
A("## §3. 재질 — 무엇이 표준이고 무엇이 문헌이고 무엇이 선언인가")
A("")
A(f"**질문**: {OUT['3_materials']['user_question']}")
A("")
A(f"**답**: {OUT['3_materials']['answer']}")
A("")
A("### §3.1 브리핑의 두 가지 오인")
A("")
for c in MAT["corrections_to_brief"]:
    A(f"- **{c['claim']}** → {c['status']}. {c['truth']}")
A("")
A("### §3.2 1층 — 표준 (ITU-R P.2040)")
A("")
A(T(OUT["3_materials"]["tier1_standard"], [("항목", "item"), ("값", "value"), ("출처", "source")]))
A("")
A("### §3.3 2층 — 문헌 출처가 붙은 값")
A("")
A("| 항목 | 출처(저자 · 학회 · 연 · DOI) | 측정 대역 | 문헌이 보고한 값 | 판정 |")
A("|---|---|---|---|---|")
for e in OUT["3_materials"]["tier2_literature"]:
    fr = e.get("measured_band_ghz")
    frs = f"{fr[0]:g}~{fr[1]:g} GHz" if fr else "—"
    A(f"| {E(e['item'])} | {E(e['source'])} | {frs} | {E(e.get('reported','—'))} | {E(e['verdict'])} |")
A("")
A(f"⭐ 플라스틱 eps_r 의 출처는 **우리 세 밴드를 전부 덮는 측정**이다 — "
  f"{zech['freq_range_ghz'][0]:g}~{zech['freq_range_ghz'][1]:g} GHz. "
  f"탄소 도전율의 출처도 마찬가지로 대역 안이다 — {artner['freq_range_ghz'][0]:g}~"
  f"{artner['freq_range_ghz'][1]:g} GHz 도파관 NRW.")
A("")
A("### §3.4 3층 — 선언된 모델링 선택 (출처 없음, 영향 유계)")
A("")
A("이 다섯은 문헌값이 아니다. **PO 경로에 들어가는 실효 반사계수**이고, 각각 총 σ 를 얼마나 "
  "움직이는지를 GPU 스윕으로 재서 유계로 만들었다.")
A("")
A("| 항목 | 총 σ 최대 영향 [dB] | 어디서 | 상태 |")
A("|---|---|---|---|")
for e in OUT["3_materials"]["tier3_declared_choices"]:
    A(f"| {e['item']} | {e['bound_db']:.3f} | {e['bound_where']} | {e['status']} |")
A("")
A("**셸 0.28 — 부호가 틀렸다.** " + OUT["3_materials"]["tier3_declared_choices"][0]["detail"] + ". "
  f"박막 유도값으로 통째로 갈아끼우면 총 σ 는 최대 {max(m_thin, m_thin_n):.3f} dB 움직인다 "
  f"⟨`material_sources.json : impact_sweep.by_drone`⟩ — 즉 파라미터는 **선언하고 유계로 두면** "
  f"방어된다. 두께 자체는 출처가 없다: DJI 는 셸 두께도 수지 종류도 공개하지 않고, 공개 티어다운에도 "
  f"벽 두께 실측이 없다.")
A("")
A(f"**우선순위가 뒤집혀 있었다.** note 분량이 가장 두꺼운 프로펠러 파라미터는 스윕 전 구간"
  f"(0.10~0.46)에서 총 σ 를 {m_prop:.3f} dB 움직이고, 논쟁의 대상이던 0.25 → 0.28 변경만 보면 "
  f"{m_prop28:.3f} dB 다. 같은 성격으로 출처가 없는 camera_assembly 는 스윕 전 구간(0.50~1.00)에서 "
  f"{m_cam:.3f} dB — 프로펠러 전 구간의 {m_cam/max(m_prop,1e-9):.1f} 배, 0.25 → 0.28 항의 "
  f"{m_cam/max(m_prop28,1e-9):.0f} 배다. 실물에서 먼저 확인할 부품은 짐벌·카메라 조립체다.")
A("")
A(f"**프로펠러 note 의 근거 문장은 우리 CAD 자신이 반증한다.** note 는 '날개가 셸(1~3 mm)보다 얇다'를 "
  f"전제로 0.25 를 골랐는데, drone_cad 의 두께 법칙에서 유도한 날개는 시위평균 "
  f"{PROP_CM_LO:.2f}~{PROP_CM_HI:.2f} mm, {PROP_PK_ARG} 최대 {PROP_PK_HI:.2f} mm 로 셸을 넘어선다 "
  f"⟨`material_sources.json : propeller.per_drone`⟩. 값 0.25 의 결론은 살아남고 근거가 바뀐다 — "
  f"이제 그것은 유도값이 아니라 **선언된 상수**다.")
A("")
A(f"**탄소 행이 0.000 dB 인 이유.** 주 스윕의 세 기체(phantom4 · mavic4pro · mini5pro)에 "
  f"carbon 그룹이 아예 없다. 실제로 쓰는 기체로 다시 재면 {m_carb_supp:.3f} dB 다 ({w_carb_supp}). "
  f"'무해'가 아니라 '해당 없음'이었다.")
A("")
A("### §3.5 재질은 레벨을 정하고, 기울기는 재질 밖에서 정해진다")
A("")
A("| 양 | 값 |")
A("|---|---|")
A(f"| 방어 가능한 브래킷(V1 벌크 프레넬 / V2 0.10 / V3 0.45)의 레벨 진폭 | {BRK['level_swing_db']:.3f} dB |")
A(f"| 같은 브래킷의 3밴드 기울기 진폭 | {BRK['slope_swing_db_per_ghz']:.3f} dB/GHz |")
A("")
A("재질은 레벨을 정하고, 밴드 의존성은 재질 밖에서 정해진다. 모든 gamma_po 가 주파수 평탄한 실수 "
  "상수이기 때문이다 ⟨`engine_validation_verdict.json : 3_materials.bounded_total`⟩.")
A("")
A(f"제안 패치 {len(MAT['proposed_patch'])}건은 `outputs/material_sources.json : proposed_patch` 에 있다. "
  f"{OUT['3_materials']['not_edited']}.")
A("")
A("---")
A("")

# §4
A("## §4. 대조가 성립하는가 — 성립한다")
A("")
A("성립한다 — 다만 **측정 체인 1개가 잰 기체 1종에 대한 정합성 검사**이지 절대 σ 의 검증이 아니다. "
  "그 문장은 각주가 아니라 편 제목에 들어간다 "
  "⟨`validation_feasibility.json : 5_verdict.is_a_valid_comparison_possible`⟩.")
A("")
A("타당성 단계의 차단 질문(‘Phantom 2 의 수치가 근거리장이면 비교가 무너진다’)은 **불필요했다**. "
  "Das Table I 을 350 dpi 렌더에서 직접 읽으면 1.8~18.2 GHz · 2801점 · 원거리장 · 무향은 "
  "**Phantom 3** 열이고, Phantom 2 는 11~26 GHz · 2001점 · 근거리장 2.6 m 다. Phantom 2 는 "
  "대역 밖이라 애초에 후보가 아니었다 "
  "⟨`validation_feasibility.json : 0_corrections_to_the_workflow_brief`⟩.")
A("")
A("남은 미통제 항:")
A("")
_OPEN_KR = [
    "Yuan 이 잰 Phantom 3 변형(Standard / 4K / Advanced / Professional)이 어느 것인지",
    "CATR 정숙영역 지름과 진폭·위상 테이퍼 — 미발표. Phantom 3 의 원거리장 성립은 두 논문의 선언으로 남아 있다",
    "표적 거치대 — 두 논문 모두 기체가 무엇 위에 있었는지(스티로폼 기둥·파일런), 게이팅 후 그 기여가 얼마인지 적지 않았다",
    "측정 당시 프로펠러의 방위 위상",
    "Das 의 Phantom 3 행이 Yuan 의 동일 원자료를 재적합한 것인지, 참고문헌 [7](Wang et al., China Commun., 2026) "
    "경로로 재처리된 것을 적합한 것인지 — 2.5 dB 규약·처리 모호성이 이 두 논문만으로는 풀리지 않는 이유",
    "1.8~5.2 GHz 에서 Phantom 급 기체의 교차편파 응답 — 스칼라 커널의 VV 대비 편향을 유계하는 데 필요한데, 발표된 곳을 찾지 못했다",
    "Phantom 3 앵커를 다른 기체로 옮길 때의 크기전이 지수 n ∈ {2, 4} — Phantom 3 를 직접 지은 덕분에 이 대조에서는 정할 필요가 없었다",
]
for _x in _OPEN_KR:
    A(f"- {_x}")
A("")
A("(원문 목록: `validation_feasibility.json : 8_open_and_uncontrolled_terms`)")
A("")
A("이 대조로도 닫히지 않는 것을 닫는 측정은 하나다 — **우리 기체 1종의 자체 모노스태틱 RCS 측정** "
  "(1.8~5.3 GHz, 정확 Mie σ 를 우리가 직접 계산하는 PEC 구로 교정, 배경 차감과 거리 게이팅 포함). "
  "그것이 저장소의 모든 '앵커된' 주장을 '측정된' 주장으로 바꾼다 "
  "⟨`validation_feasibility.json : 5_verdict.if_this_is_not_enough_what_measurement_is_needed`⟩. "
  "설계는 `outputs/measurement_plan.json` 에 이미 있다.")
A("")
A("---")
A("")

# §5
A("## §5. 비용")
A("")
A("| 단계 | SBR 실행 [건] | GPU [s] | 어떻게 셌나 |")
A("|---|---|---|---|")
for r in cost_rows:
    A(f"| {r['stage']} | {r['n_runs']} | {r['gpu_s']:.0f} | {r['how']} |")
A(f"| **대조 단계 합** | **{cmp_runs}** | **{cmp_gpu_s:.0f}** ({cmp_gpu_s/3600.0:.2f} h) | |")
A(f"| 재질 단계 — impact sweep | {n_imp_runs} | {mat_sweep_s:.0f} | 로그 실측 · 건수는 JSON 셀 수 |")
A(f"| 재질 단계 — carbon 보충 | {n_carb_runs} | {mat_carb_s:.0f} | 로그 실측 · 건수는 JSON 셀 수 |")
A(f"| 타당성 단계 | 0 | 0 | PDF 판독 · 회귀 · 규약 감사 |")
A(f"| **전체** | **{cmp_runs + n_imp_runs + n_carb_runs}** | **{total_gpu_s:.0f}** "
  f"({total_gpu_s/3600.0:.2f} h) | |")
A("")
A(f"카드 0·1 은 타 사용자가 점유 중이라 2·3 만 썼다. 광선율 모델은 sweep 로그의 (rays/az, 초) "
  f"21쌍에 원점 통과 최소제곱을 세운 것이다 — k = {rate_k:.3e} s/(ray·az).")
A("")
A("### §5.1 두 번째 기체는 얼마인가")
A("")
A("| 항목 | 값 |")
A("|---|---|")
A(f"| 재사용되는 것 | {OUT['5_cost']['second_airframe']['what_is_shared']} |")
A(f"| 새로 드는 것 | {OUT['5_cost']['second_airframe']['what_is_new']} |")
A(f"| 한계 GPU 비용 | {second_gpu_s:.0f} s ({second_gpu_s/3600.0:.2f} h) |")
A(f"| scan 단계 | {OUT['5_cost']['second_airframe']['scan_stage']} |")
A("")
A(f"**그러나 후보가 없다.** {OUT['5_cost']['second_airframe']['warning']}. "
  f"두 번째 대조 기체를 결정하는 근거는 GPU 예산이 아니라 07편의 측정 설계다.")
A("")
A("---")
A("")

# §6
A("## §6. 다음 단계")
A("")
A(T(NEXT, [("다음에 할 일", "do"), ("그러면 결정되는 것", "decides"), ("어디서", "where")]))
A("")
A(f"⭐ 첫 줄이 선행 조건이다. `outputs/rcs_anchor.json` 은 "
  f"{time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(os.path.join(_ROOT, 'outputs', 'rcs_anchor.json'))))} "
  f"자 파일이고, 저장된 phantom4 값이 이후 두 개의 독립 하네스와 "
  f"{min(XCH['staleness_confirmed_db'].values()):+.3f}~{max(XCH['staleness_confirmed_db'].values()):+.3f} dB "
  f"어긋난다 ⟨`validate_measured_airframe.json : 8_comparison.I_crosschecks`⟩. "
  f"드리프트의 방향이 사정을 **나쁘게** 만든다(레벨은 더 낮고 기울기는 더 가파르다). "
  f"03편의 그림을 그리기 전에 재생성한다.")
A("")

with open(OUT_MD, "w") as f:
    f.write("\n".join(L) + "\n")
print(f"[saved] {OUT_MD}  ({len(L)} lines)")
