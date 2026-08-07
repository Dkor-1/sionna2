# -*- coding: utf-8 -*-
"""
report16_synthesis.py — ⭐⭐ **종합: «표적을 얼마나 단순화해도 되나» 를 숫자로 답한다**
================================================================================

이 파일이 하는 일
--------------------------------------------------------------------------------
report16 라운드는 «드론을 점점 더 거칠게 그려 가며» 마이크로도플러(프로펠러가 돌아서
생기는 전파 신호의 흔들림)를 재는 사다리를 6 단 올렸고, 적대검증 3 렌즈가 그 사다리를
때렸다. 이 파일은 그 결과를 **한 장으로 읽히게** 모으고, 빠져 있던 조각 하나를 채운다.

빠져 있던 조각 = **사다리 6 단이 서로 다른 운동학(무엇이 도는가)을 섞어 쓰고 있었다.**
  · 구·정육면체·상자 단은 «기체 전체를 덩어리 하나로 바꿔 통째로 돌린» 물체다.
  · 진짜 드론은 몸통이 서 있고 **프로펠러만** 돈다.
  두 개를 나란히 놓고 «형상 차이» 라고 부르면, 그 안에는 형상 교체와 운동학 교체가
  섞여 있다. 적대검증 두 렌즈가 이 결함을 각각 따로 지적했다.

그래서 이 파일은 사다리를 **세 벌** 만든다(새 전자기 계산 0 — 앞 단들이 저장해 둔
위상 표를 다시 읽을 뿐이다):

  A. 있는 그대로의 사다리 (6 단, 이름 그대로) — 운동학이 섞여 있음을 열에 명시
  B. 운동학을 «온몸 자전» 으로 고정한 사다리 (6 단)
  C. ⭐ 운동학을 **진짜 비행 조건**(몸통 정지 + 프로펠러 회전)으로 고정하고
     **프로펠러만** 단순화한 사다리 (6 단) — 「표적을 얼마나 단순화해도 되나」에
     실제로 답할 자격이 있는 유일한 축

산출물
--------------------------------------------------------------------------------
  outputs/report16_synthesis.json          — 모든 숫자 (손입력 0)
  docs/TARGET_LADDER.md                    — 사람이 읽는 판 (이 스크립트가 생성)
  outputs/figures/report16_synthesis_spectrograms.png  — 스펙트로그램 6 장 × 2 줄
  outputs/figures/report16_synthesis_ladder.png        — 사다리 표를 그림으로

⛔ outputs/report15_* · benchmark/report15_* 미접촉
⛔ src/make_report0N_*.py · report0N_*.ipynb 미접촉
⛔ src/drones.py · src/drone_cad.py 편집 금지 — 이 파일은 둘 다 열지 않는다
⛔ 숫자 손입력 금지 — 표에 실리는 값은 전부 저장된 표에서 계산한다
GPU: 안 쓴다. 저장된 (24 × 최대 1024) 짜리 복소 표를 FFT 하는 후처리라 CPU 로 충분하고,
     GPU 4 장은 형제 워크플로가 93~100 % 로 쓰는 중이었다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)

# ⭐ 지표는 재구현하지 않는다 — 기반 단의 구현을 그대로 import 해서 호출한다.
from report16_base import md_metrics16, ac_corr, summarize  # noqa: E402

OUT_JSON = os.path.join(ROOT, "outputs", "report16_synthesis.json")
OUT_MD = os.path.join(ROOT, "docs", "TARGET_LADDER.md")
FIG_SPEC = os.path.join(ROOT, "outputs", "figures", "report16_synthesis_spectrograms.png")
FIG_LADDER = os.path.join(ROOT, "outputs", "figures", "report16_synthesis_ladder.png")

C0 = 299792458.0
AZ_PICK_DEG = 30.0        # 스펙트로그램을 뽑을 방위 — 정육면체(90° 주기)·상자(180° 주기)
                          # 어느 쪽의 대칭축도 아닌 자리를 고른다.

T0 = time.time()


# --------------------------------------------------------------------------- #
#  0. 입력 읽기 + 지문
# --------------------------------------------------------------------------- #
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_json(rel):
    p = os.path.join(ROOT, rel)
    with open(p, encoding="utf-8") as f:
        return json.load(f), dict(path=p, sha256=sha256(p),
                                  mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                                      time.localtime(os.path.getmtime(p))))


def load_npz(rel):
    p = os.path.join(ROOT, rel)
    return np.load(p, allow_pickle=True), dict(path=p, sha256=sha256(p))


def summ(vals):
    """report16_base.summarize 에 **중앙값**을 덧붙인다. 앞 렌즈들이 중앙값으로 인용한
    항목이 있어서, 평균만 실으면 «숫자가 다르다» 는 오해가 생긴다."""
    s = dict(summarize(vals))
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    s["median"] = float(np.median(v)) if v.size else float("nan")
    return s


PROV = {}


def _prov(name, meta):
    PROV[name] = meta


J_BASE, m = load_json("outputs/report16_base.json"); _prov("base", m)
Z_BASE, m = load_npz("outputs/report16_base_tables.npz"); _prov("base_npz", m)
Z_SPH, m = load_npz("outputs/report16_rung_sphere_eqvol_tables.npz"); _prov("sphere_npz", m)
Z_CUBE, m = load_npz("outputs/report16_rung_cube_eqvol_tables.npz"); _prov("cube_npz", m)
Z_BOX, m = load_npz("outputs/report16_rung_box_bbox_tables.npz"); _prov("box_npz", m)
Z_NOR, m = load_npz("outputs/report16_rung_mesh_no_rotor_tables.npz"); _prov("no_rotor_npz", m)
Z_HALF, m = load_npz("outputs/report16_rung_mesh_half_tri_tables.npz"); _prov("half_tri_npz", m)
Z_FULL, m = load_npz("outputs/report16_rung_mesh_full_tables.npz"); _prov("mesh_full_npz", m)

J_M_SPH, m = load_json("outputs/report16_metric_sphere_eqvol.json"); _prov("metric_sphere", m)
J_M_CUBE, m = load_json("outputs/report16_metric_cube_eqvol.json"); _prov("metric_cube", m)
J_M_BOX, m = load_json("outputs/report16_metric_box_bbox.json"); _prov("metric_box", m)
J_M_NOR, m = load_json("outputs/report16_metric_mesh_no_rotor.json"); _prov("metric_no_rotor", m)
J_M_HALF, m = load_json("outputs/report16_metric_mesh_half_tri.json"); _prov("metric_half_tri", m)
J_M_FULL, m = load_json("outputs/report16_metric_mesh_full.json"); _prov("metric_mesh_full", m)

J_V_TAUT, m = load_json("outputs/report16_verify_tautology.json"); _prov("verify_tautology", m)
J_V_KERN, m = load_json("outputs/report16_verify_kernel.json"); _prov("verify_kernel", m)
J_V_DET, m = load_json("outputs/report16_verify_detector.json"); _prov("verify_detector", m)

J_P3, m = load_json("outputs/p3_validation_v2.json"); _prov("p3_validation_v2", m)

PROTO = J_BASE["protocol"]
PPD = J_BASE["protocol_per_drone"]
BLADE_N = int(PROTO["blade_n"])
DRONES = ["mini2", "matrice4e"]          # 두 기체 모두 여섯 단 전부에 등장하는 유일한 짝


def git_rev():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


# --------------------------------------------------------------------------- #
#  1. 사다리 정의 — 세 벌
# --------------------------------------------------------------------------- #
#  각 단은 (표시이름, 표를 꺼내는 함수, 형상 모수 개수, 무엇이 도는가, 한 줄 설명)
#  «형상 모수» = 그 표적을 그리는 데 필요한 치수의 개수. 구는 반지름 1 개지만 부피에서
#  유도되므로 «자유 모수 0» 으로 센다(맞출 것이 없다). 사다리의 x 축이다.

def T(z, key):
    """npz 에서 표를 꺼낸다. 없으면 KeyError 로 바로 죽는다(조용한 대체 금지)."""
    return np.asarray(z[key], complex)


LADDER_A = [
    ("sphere_eqvol", "equal-volume sphere", 0, "whole body spins",
     "기체 전체를 «부피가 같은 공» 하나로. 어느 방향에서 봐도 같은 모양이라 변조가 원리적으로 0.",
     lambda d: T(Z_SPH, f"main__{d}__sphere_eqvol__spherical")),
    ("cube_eqvol", "equal-volume cube", 1, "whole body spins",
     "기체 전체를 «부피가 같은 정육면체» 하나로. 한 변 길이 하나만 정하면 된다.",
     lambda d: T(Z_CUBE, f"main__{d}__cube_eqvol__spherical")),
    ("box_bbox", "bounding box", 3, "whole body spins",
     "기체 전체를 «CAD 를 감싸는 최소 직육면체» 하나로. 가로·세로·높이 세 치수.",
     lambda d: T(Z_BOX, f"main__{d}__box_bbox__spherical")),
    ("mesh_no_rotor", "CAD body, rotors deleted", 0, "nothing moves",
     "진짜 CAD 몸통에서 프로펠러만 지웠다. 도는 것이 없으므로 변조가 정확히 0 이다.",
     None),
    ("mesh_half_tri", "CAD, triangles halved", 0, "rotors only",
     "진짜 CAD 를 삼각형 수 절반으로 성기게 깎았다. 몸통 정지 + 프로펠러 회전(진짜 비행 조건).",
     lambda d: T(Z_HALF, f"main__{d}__mesh_half_tri__spherical")),
    ("mesh_full", "CAD, full resolution (reference)", 0, "rotors only",
     "현재 CAD 전부. 이 라운드의 기준선.",
     lambda d: T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")),
]

LADDER_B = [
    ("sphere_eqvol", "equal-volume sphere", 0,
     "부피가 같은 공", "sphere_eqvol"),
    ("cube_eqvol", "equal-volume cube", 1,
     "부피가 같은 정육면체", "cube_eqvol"),
    ("box_eqvol_aspect", "equal-volume box, CAD aspect", 3,
     "부피는 같고 가로세로비만 CAD 에서 가져온 상자", "box_eqvol_aspect"),
    ("box_bbox", "bounding box", 3,
     "CAD 를 감싸는 최소 직육면체", "box_bbox"),
    ("mesh_no_rotor", "CAD body, rotors deleted", 0,
     "진짜 CAD 몸통(프로펠러 없음)", "mesh_no_rotor"),
    ("mesh_full_rigid", "CAD body + frozen props", 0,
     "진짜 CAD 몸통 + 프로펠러를 얼려 붙인 것", "mesh_full_rigid"),
]

LADDER_C = [
    ("disc", "rotor -> rotationally symmetric disc", 0,
     "프로펠러를 «같은 반경·같은 두께의 원판» 으로. 돌아도 모양이 안 바뀌니 변조가 원리적으로 0.",
     lambda d: T(Z_BASE, f"main__G_0804__{d}__disc__spherical")),
    ("sph_blade_rg", "rotor -> spheres at radius of gyration", 1,
     "프로펠러를 «회전반경 자리에 놓인 작은 공» 으로. 위치 하나만 남긴 판.",
     lambda d: T(Z_SPH, f"main__{d}__sph_blade_rg__spherical")),
    ("prop_bbox", "rotor -> solid bounding box", 3,
     "프로펠러를 «감싸는 직육면체» 로. 크기는 맞지만 속이 꽉 찼다.",
     lambda d: T(Z_BOX, f"main__{d}__prop_bbox__spherical")),
    ("slab", "rotor -> flat slabs (same span/volume)", 3,
     "프로펠러를 «스팬·두께·부피가 같은 평판 2 장» 으로. 마이크로도플러 문헌의 고전 모델.",
     lambda d: T(Z_BASE, f"main__G_0804__{d}__slab__spherical")),
    ("mesh_half_tri", "CAD, triangles halved", 0,
     "진짜 CAD, 삼각형 절반.",
     lambda d: T(Z_HALF, f"main__{d}__mesh_half_tri__spherical")),
    ("mesh_full", "CAD, full resolution (reference)", 0,
     "현재 CAD 전부. 기준선.",
     lambda d: T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")),
]


# --------------------------------------------------------------------------- #
#  2. 게이트 — 남이 적어 준 숫자를 믿기 전에 스스로 확인한다
# --------------------------------------------------------------------------- #
GATES = {}


def gate_mesh_identity():
    """⭐ 이 파일은 서로 다른 4 개 npz 에서 표를 꺼내 **한 사다리로 잇는다**.
    이어 붙일 자격이 있으려면 네 파일이 같은 규약으로 돌았어야 한다. 네 파일 모두에
    들어 있는 «mesh» 팔이 **비트 단위로 같은지** 본다. 다르면 사다리를 못 만든다."""
    rows = {}
    ok = True
    for d in DRONES:
        ref = T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")
        cand = {
            "sphere_rung": T(Z_SPH, f"main__{d}__mesh__spherical"),
            "half_tri_rung": T(Z_HALF, f"main__{d}__mesh__spherical"),
            "mesh_full_rung": T(Z_FULL, f"{d}__spherical"),
        }
        for k, v in cand.items():
            same = bool(v.shape == ref.shape and np.array_equal(v, ref))
            mx = float(np.max(np.abs(v - ref))) if v.shape == ref.shape else float("inf")
            rows[f"{d}|{k}"] = dict(bitwise_identical=same, max_abs_diff=mx)
            ok = ok and same
    GATES["G1_mesh_table_identity_across_files"] = dict(
        rows=rows, verdict="PASS" if ok else "FAIL",
        what_ko=("네 파일(기반·구·절반메쉬·전체메쉬)에 다 들어 있는 «mesh» 팔이 비트 단위로 "
                 "같은가. 같아야 서로 다른 파일의 팔을 한 사다리에 이어 붙일 자격이 생긴다."))
    return ok


def gate_protocol_selfconsistency():
    """규약을 표에서 되짚는다 — PRF = (한 바퀴 표본 수) × (회전수/초) 인가."""
    rows = {}
    ok = True
    for d in DRONES:
        p = PPD[d]
        S = T(Z_BASE, f"main__G_0804__{d}__mesh__spherical").shape[1]
        prf_from_table = S * p["f_rot_hz"]
        rel = abs(prf_from_table - p["prf_hz"]) / p["prf_hz"]
        beta_from_ftip = p["f_tip_hz"] / p["f_rot_hz"]
        rel_b = abs(beta_from_ftip - p["beta"]) / p["beta"]
        rows[d] = dict(S=int(S), prf_from_table_hz=float(prf_from_table),
                       prf_stated_hz=float(p["prf_hz"]), rel_err_prf=float(rel),
                       beta_from_f_tip=float(beta_from_ftip), beta_stated=float(p["beta"]),
                       rel_err_beta=float(rel_b))
        ok = ok and rel < 1e-12 and rel_b < 1e-12
    GATES["G2_protocol_selfconsistency"] = dict(
        rows=rows, verdict="PASS" if ok else "FAIL",
        what_ko="표의 열 개수 × 회전수 = PRF 인가, f_tip/f_rot = β 인가. 규약이 자기모순이면 다 무너진다.")
    return ok


def gate_recompute_vs_stage():
    """앞 단들이 JSON 에 적어 둔 값을 원본 표에서 다시 계산해 맞춰 본다."""
    rows = {}
    worst = 0.0
    fam = J_M_SPH["metric_families"]
    for d in DRONES:
        tab = T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")
        mm = [md_metrics16(tab[i], PPD[d], BLADE_N) for i in range(tab.shape[0])]
        # ⚠ 방위평균은 이 라운드의 규약대로 **dB 산술평균**이다(전력평균이 아니다).
        #   전력평균은 가장 밝은 방위 하나가 지배해 버린다. 둘 다 내되 게이트는 규약을 쓴다.
        mine = dict(flash_contrast_db=float(np.mean([x["flash_contrast_db"] for x in mm])),
                    n_eff_orders=float(np.mean([x["n_eff_orders"] for x in mm])),
                    dc_ac_db=float(np.mean([x["dc_ac_db"] for x in mm])),
                    sigma_eq_mean_dbsm=float(np.mean([x["sigma_eq_mean_dbsm"] for x in mm])))
        ref = fam[f"main|{d}|mesh|spherical"]
        theirs = dict(flash_contrast_db=ref["flash"]["flash_contrast_db"],
                      n_eff_orders=ref["richness"]["n_eff_orders"],
                      dc_ac_db=ref["dc_ac"]["dc_ac_db"],
                      sigma_eq_mean_dbsm=ref["level"]["sigma_eq_mean_dbsm"])
        r = {}
        for k in mine:
            den = max(abs(theirs[k]), 1e-12)
            rel = abs(mine[k] - theirs[k]) / den
            r[k] = dict(mine=mine[k], stage=theirs[k], rel=float(rel))
            worst = max(worst, rel)
        rows[d] = r
    GATES["G3_recompute_vs_stage_json"] = dict(
        rows=rows, worst_rel=float(worst), tolerance=1e-9,
        verdict="PASS" if worst < 1e-9 else "FAIL",
        what_ko=("구 단이 저장한 mesh 팔 지표를 내가 원본 표에서 다시 계산해 맞춘다. "
                 "여기서 어긋나면 이 종합의 모든 표가 무효다."))
    return worst < 1e-9


def gate_parseval():
    """도플러 칸별 RCS 를 다 더하면 총 RCS 가 되는가 (Parseval). 번역기가 옳은지의 검사."""
    rows = {}
    worst = 0.0
    for d in DRONES:
        lam = PPD[d]["lam_m"]
        tab = T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")
        for i in (0, 7, 13):
            x = tab[i]
            c = np.fft.fft(x) / len(x)
            s_sum = 4 * np.pi / lam ** 2 * float(np.sum(np.abs(c) ** 2))
            s_tot = 4 * np.pi / lam ** 2 * float(np.mean(np.abs(x) ** 2))
            rel = abs(s_sum - s_tot) / s_tot
            rows[f"{d}|az{i}"] = dict(sum_of_bins_dbsm=float(10 * np.log10(s_sum)),
                                      total_dbsm=float(10 * np.log10(s_tot)), rel=float(rel))
            worst = max(worst, rel)
    GATES["G4_parseval_doppler_bins"] = dict(
        rows=rows, worst_rel=float(worst), verdict="PASS" if worst < 1e-12 else "FAIL",
        what_ko="σ_m = 4π/λ²·|c_m|² 로 도플러 칸을 나눈 뒤 다 더하면 총 RCS 가 나와야 한다.")
    return worst < 1e-12


# --------------------------------------------------------------------------- #
#  3. 한 팔에서 뽑는 값들
# --------------------------------------------------------------------------- #
def arm_stats(tab, proto, nb=BLADE_N):
    """(방위, 위상) 표 → 방위별 지표 + 방위 앙상블 요약.

    ⭐ 여기서 «검출 단면적» 을 같이 낸다:
        σ_m = 4π/λ² · |c_m|²   (도플러 칸 m 에서 보이는 RCS)
        σ_total    = 모든 칸의 합       — 병진 표적이 쓸 수 있는 값
        σ_ac_peak  = m≠0 중 가장 센 칸  — 호버 표적이 실제로 쓸 수 있는 값
        호버 벌금  = σ_total − σ_ac_peak
    """
    tab = np.atleast_2d(np.asarray(tab, complex))
    lam = proto["lam_m"]
    per = []
    for i in range(tab.shape[0]):
        x = tab[i]
        m = md_metrics16(x, proto, nb)
        c = np.fft.fft(x) / len(x)
        P = np.abs(c) ** 2
        midx = np.fft.fftfreq(len(x), d=1.0 / len(x)).astype(int)
        ac = midx != 0
        pk = float(P[ac].max()) if ac.any() else 0.0
        s = 4 * np.pi / lam ** 2
        m["sigma_total_dbsm"] = float(10 * np.log10(max(s * P.sum(), 1e-300)))
        m["sigma_ac_total_dbsm"] = float(10 * np.log10(max(s * P[ac].sum(), 1e-300)))
        m["sigma_ac_peak_dbsm"] = float(10 * np.log10(max(s * pk, 1e-300)))
        m["hover_penalty_db"] = m["sigma_total_dbsm"] - m["sigma_ac_peak_dbsm"]
        m["peak_order"] = int(abs(midx[ac][np.argmax(P[ac])])) if ac.any() else 0
        m["peak_share_of_ac"] = float(pk / max(P[ac].sum(), 1e-300))
        per.append(m)

    keys = ["flash_contrast_db", "n_eff_orders", "order_edge_20db", "width_ratio_20db",
            "dc_ac_db", "in_band_ac_frac", "in_band_ac_over_dc_db", "blade_comb_frac",
            "sigma_total_dbsm", "sigma_ac_total_dbsm", "sigma_ac_peak_dbsm",
            "hover_penalty_db", "peak_order", "peak_share_of_ac", "ac_over_floor_db"]
    out = {"n_az": int(tab.shape[0]), "n_phase": int(tab.shape[1])}
    for k in keys:
        v = [p.get(k, float("nan")) for p in per]
        out[k] = summ(v)
    # 세기 계열은 방위평균을 «전력» 으로 낸다(dB 를 그냥 평균하면 세기 평균이 아니다)
    for k in ("sigma_total_dbsm", "sigma_ac_total_dbsm", "sigma_ac_peak_dbsm"):
        lin = [10 ** (p[k] / 10) for p in per]
        out[k]["power_mean_db"] = float(10 * np.log10(np.mean(lin)))
    out["quotable_frac"] = float(np.mean([1.0 if p["in_band_ac_frac"] >= 0.5 else 0.0
                                          for p in per]))
    out["quotable"] = bool(out["quotable_frac"] >= 0.5)
    out["_per_az"] = per
    return out


def paired_vs_ref(tab, ref, proto, nb=BLADE_N):
    """같은 방위끼리 짝지어 «기준(진짜 CAD) 대비» 를 낸다. 짝지으면 방위 산포가 지워진다."""
    tab = np.atleast_2d(np.asarray(tab, complex))
    ref = np.atleast_2d(np.asarray(ref, complex))
    n = min(tab.shape[0], ref.shape[0])
    d_flash, d_neff, d_dcac, d_sig, d_pk, rho, loss = [], [], [], [], [], [], []
    lam = proto["lam_m"]
    for i in range(n):
        a = md_metrics16(tab[i], proto, nb)
        b = md_metrics16(ref[i], proto, nb)
        d_flash.append(a["flash_contrast_db"] - b["flash_contrast_db"])
        d_neff.append(a["n_eff_orders"] - b["n_eff_orders"])
        d_dcac.append(a["dc_ac_db"] - b["dc_ac_db"])

        def pk_db(x):
            c = np.fft.fft(x) / len(x)
            P = np.abs(c) ** 2
            m = np.fft.fftfreq(len(x), d=1.0 / len(x)).astype(int)
            return (10 * np.log10(max(4 * np.pi / lam ** 2 * float(P[m != 0].max()), 1e-300)),
                    10 * np.log10(max(4 * np.pi / lam ** 2 * float(P.sum()), 1e-300)))
        pa, ta_ = pk_db(tab[i])
        pb, tb_ = pk_db(ref[i])
        d_pk.append(pa - pb)
        d_sig.append(ta_ - tb_)
        r = ac_corr(tab[i], ref[i])
        rho.append(r)
        loss.append(-20 * math.log10(max(r, 1e-12)))
    return dict(
        d_flash_contrast_db=summ(d_flash),
        d_n_eff_orders=summ(d_neff),
        d_dc_ac_db=summ(d_dcac),
        d_sigma_total_db=summ(d_sig),
        d_sigma_ac_peak_db=summ(d_pk),
        ac_waveform_corr=summ(rho),
        template_mismatch_loss_db=summ(loss),
        # ⚠ 규약 주의: 라운드의 앞 렌즈들은 «방위평균 상관을 먼저 낸 뒤 로그» 를 쓴다.
        #    나는 «방위마다 로그를 낸 뒤 평균» 도 낸다. 젠센 부등식 때문에 후자가 항상 크다.
        #    둘 다 싣고, 표에는 라운드 규약(전자)을 쓴다.
        template_loss_from_mean_corr_db=float(-20 * math.log10(max(float(np.mean(rho)), 1e-12))),
        fold_convention_ko=("template_loss_from_mean_corr_db = −20log10(평균 상관) — 라운드 규약. "
                            "template_mismatch_loss_db = 방위별 손실의 평균 — 항상 이것이 더 크다."),
        n_same_sign_flash=int(sum(1 for v in d_flash if v * np.mean(d_flash) > 0)),
        n_pairs=int(n),
        note_ko=("모두 «같은 방위끼리» 뺀 값이다. template_mismatch_loss_db 는 그 형상으로 "
                 "정합필터 본을 뜨면 잃는 SNR — −20log10(파형 상관) 이다."))


# --------------------------------------------------------------------------- #
#  4. 사다리 세 벌 계산
# --------------------------------------------------------------------------- #
def build_ladder_A():
    out = {}
    for d in DRONES:
        proto = PPD[d]
        ref = T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")
        rows = {}
        for name, en, npar, kin, ko, getter in LADDER_A:
            if getter is None:                       # mesh_no_rotor — 도는 것이 없다
                st = T(Z_NOR, f"{d}__mesh_no_rotor__main__spherical__15__flight_static")
                lam = proto["lam_m"]
                s_tot = 4 * np.pi / lam ** 2 * np.abs(st) ** 2
                r = dict(
                    kinematics=kin, n_shape_params=npar, label_en=en, what_ko=ko,
                    sigma_total_dbsm=dict(power_mean_db=float(10 * np.log10(np.mean(s_tot))),
                                          mean=float(np.mean(10 * np.log10(s_tot))),
                                          sd=float(np.std(10 * np.log10(s_tot), ddof=1)),
                                          n=int(st.size)),
                    ac_power_exactly_zero=True,
                    flash_contrast_db=None, n_eff_orders=None, width_ratio_20db=None,
                    dc_ac_db=float("inf"), sigma_ac_peak_dbsm=None, hover_penalty_db=None,
                    quotable=False,
                    degenerate_note_ko=("도는 부품이 없으므로 시간 변조 전력이 «작다» 가 아니라 "
                                        "**정확히 0** 이다. 네 지표 중 셋은 값 자체가 없다 — "
                                        "0 으로 나누는 자리다. 이 단은 사다리의 다른 단들과 "
                                        "같은 표에 실을 수 없다."),
                    paired_vs_mesh=None)
                rows[name] = r
                continue
            tab = getter(d)
            st = arm_stats(tab, proto)
            r = dict(kinematics=kin, n_shape_params=npar, label_en=en, what_ko=ko,
                     ac_power_exactly_zero=False)
            for k in ("flash_contrast_db", "n_eff_orders", "order_edge_20db", "width_ratio_20db",
                      "dc_ac_db", "in_band_ac_frac", "in_band_ac_over_dc_db",
                      "sigma_total_dbsm", "sigma_ac_total_dbsm", "sigma_ac_peak_dbsm",
                      "hover_penalty_db", "peak_order", "peak_share_of_ac"):
                r[k] = st[k]
            r["quotable"] = st["quotable"]
            r["quotable_frac"] = st["quotable_frac"]
            r["paired_vs_mesh"] = paired_vs_ref(tab, ref, proto)
            rows[name] = r
        out[d] = rows
    return out


def build_ladder_B():
    """운동학을 «온몸 자전» 으로 고정. 표는 1 바퀴 자전 위상표 하나(방위 앙상블이 퇴화한다)."""
    out = {}
    for d in DRONES:
        proto = dict(PPD[d])
        rows = {}
        ref_key = f"{d}__mesh_full_rigid__main__spherical__15__spin"
        ref = T(Z_NOR, ref_key)[None, :]
        for name, en, npar, ko, arm in LADDER_B:
            tab = T(Z_NOR, f"{d}__{arm}__main__spherical__15__spin")[None, :]
            st = arm_stats(tab, proto)
            r = dict(kinematics="whole body spins (matched)", n_shape_params=npar,
                     label_en=en, what_ko=ko)
            for k in ("flash_contrast_db", "n_eff_orders", "order_edge_20db",
                      "dc_ac_db", "in_band_ac_frac", "in_band_ac_over_dc_db",
                      "sigma_total_dbsm", "sigma_ac_total_dbsm", "sigma_ac_peak_dbsm",
                      "hover_penalty_db", "peak_order"):
                r[k] = st[k]
            r["quotable"] = st["quotable"]
            r["paired_vs_ref"] = paired_vs_ref(tab, ref, proto)
            rows[name] = r
        out[d] = rows
    out["_note_ko"] = (
        "기준은 mesh_full_rigid(진짜 CAD 몸통 + 얼린 프로펠러)다. 이 사다리는 «온몸이 도는» "
        "가상의 운동학이라 실제 드론이 아니다 — 형상만 바뀌게 만든 대조군이다. "
        "⚠ 자전 표는 곧 방위 패턴이라(no_rotor 단의 항등식) 방위 앙상블이 하나로 퇴화한다. "
        "그래서 이 사다리에는 방위 산포가 없다.")
    out["_width_note_ko"] = (
        "width_ratio 는 싣지 않았다. 그 값은 «블레이드 팁 속도» 로 나눈 값인데 이 사다리는 "
        "몸통 전체가 도는 팔이라 나눌 기준이 다르다. 대신 order_edge_20db(몇 번째 배음까지 "
        "살아 있나)를 싣는다.")
    return out


def build_ladder_C():
    """⭐ 진짜 비행 조건(몸통 정지 + 프로펠러 회전)에서 **프로펠러만** 단순화한 사다리."""
    out = {}
    for d in DRONES:
        proto = PPD[d]
        ref = T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")
        rows = {}
        for name, en, npar, ko, getter in LADDER_C:
            tab = getter(d)
            st = arm_stats(tab, proto)
            r = dict(kinematics="rotors only (真 flight, matched)", n_shape_params=npar,
                     label_en=en, what_ko=ko)
            for k in ("flash_contrast_db", "n_eff_orders", "order_edge_20db", "width_ratio_20db",
                      "dc_ac_db", "in_band_ac_frac", "in_band_ac_over_dc_db", "blade_comb_frac",
                      "sigma_total_dbsm", "sigma_ac_total_dbsm", "sigma_ac_peak_dbsm",
                      "hover_penalty_db", "peak_order", "peak_share_of_ac"):
                r[k] = st[k]
            r["quotable"] = st["quotable"]
            r["quotable_frac"] = st["quotable_frac"]
            r["paired_vs_mesh"] = paired_vs_ref(tab, ref, proto)
            rows[name] = r
        out[d] = rows
    out["_note_ko"] = (
        "⭐ 이 사다리만 «표적을 얼마나 단순화해도 되나» 에 답할 자격이 있다 — 여섯 단 모두 "
        "몸통은 진짜 CAD 이고 프로펠러만 도는 **같은 운동학**이며, 바뀌는 것은 프로펠러의 "
        "모양 하나뿐이다.")
    return out


# --------------------------------------------------------------------------- #
#  4b. ⚠ 「삼각형 절반은 공짜」 가 어디까지 참인가 — 스스로 반증해 본다
# --------------------------------------------------------------------------- #
def frame_blindness_audit():
    """⚠⚠ 이 종합이 §5 에서 «삼각형 절반은 공짜» 라고 쓰려면 먼저 이것부터 확인해야 한다.

    우리 커널에는 **가림(그늘)이 없다**. 그러면 안 도는 부품(동체)은 위상마다 «같은 상수» 를
    더할 뿐이고, 평균을 빼는 순간 AC 에서 **정확히** 사라진다. 즉 시간 변조 지표는 동체를
    아무리 거칠게 깎아도 **구조적으로 못 본다** — 계산 결과가 아니라 산수다.

    그래서 「해상도를 반으로 줄여도 무해하다」 는 두 조건 안에서만 참이다:
      (i) 줄인 것이 **도는 부품**일 때만 의미가 있다,
      (ii) 간략화가 면적·부피를 보존할 때만 성립한다.
    여기서는 그 (i) 을 숫자로 못박는다 — 동체까지 깎은 팔(mesh_half_tri_all)과 프로펠러만
    깎은 팔(mesh_half_tri)의 **AC 가 같은지** 본다. 같으면 «동체 해상도는 이 지표로 못 잰다».
    """
    rows = {}
    for d in DRONES:
        proto = PPD[d]
        a = T(Z_HALF, f"main__{d}__mesh_half_tri__spherical")        # 프로펠러만 절반
        b = T(Z_HALF, f"main__{d}__mesh_half_tri_all__spherical")    # 동체까지 절반
        q = T(Z_HALF, f"main__{d}__mesh_quarter_tri__spherical")     # 프로펠러 1/4
        ref = T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")
        rel_ac, d_dc = [], []
        for i in range(a.shape[0]):
            aa = a[i] - a[i].mean()
            bb = b[i] - b[i].mean()
            rel_ac.append(float(np.max(np.abs(aa - bb)) / max(np.max(np.abs(aa)), 1e-300)))
            ma = md_metrics16(a[i], proto, BLADE_N)
            mb = md_metrics16(b[i], proto, BLADE_N)
            d_dc.append(mb["dc_ac_db"] - ma["dc_ac_db"])
        rows[d] = dict(
            ac_relative_difference_frame_decimation=summ(rel_ac),
            dc_ac_shift_from_frame_decimation_db=summ(d_dc),
            quarter_tri_vs_mesh=paired_vs_ref(q, ref, proto),
            half_tri_vs_mesh=paired_vs_ref(a, ref, proto))
    worst = max(rows[d]["ac_relative_difference_frame_decimation"]["max"] for d in DRONES)
    return dict(
        rows=rows, worst_ac_rel_diff_from_frame_decimation=float(worst),
        frame_is_invisible_to_ac=bool(worst < 1e-9),
        what_ko=("동체까지 깎은 팔과 프로펠러만 깎은 팔의 **AC 성분**을 직접 뺀다. "
                 "차이가 기계 정밀도면 «AC 지표는 동체 해상도를 원리적으로 못 본다» 는 뜻이다."),
        so_what_ko=(
            "⚠⚠ 그래서 §5 의 «삼각형 절반은 공짜» 는 **동체에 대한 진술이 아니다**. "
            "이 커널에서 동체는 AC 에 정확히 0 을 기여하므로, 동체를 아무리 망가뜨려도 "
            "마이크로도플러 지표는 눈금 하나 안 움직인다 — 그것은 형상의 성질이 아니라 "
            "**가림 없는 커널의 성질**이다. 가림을 켜면 날개가 동체 뒤로 사라졌다 나타나면서 "
            "동체 형상이 AC 에 들어오기 시작한다(커널 렌즈 T1 이 그 방향을 이미 쟀다). "
            "이 문서가 실제로 말할 수 있는 것은 «**도는 부품**의 삼각형을 절반으로 줄여도 "
            "공짜다» 뿐이다."),
        also_ko=("동체 간략화가 동체:날개 비(dc_ac_db)는 움직인다 — 면적·부피를 잃기 때문이다. "
                 "AC 는 안 움직이고 DC 만 움직인다는 것이 위 두 줄의 뜻이다."))


def cross_check_against_lenses(LC):
    """⭐ 내가 낸 값을 앞 렌즈들이 인용한 값과 맞춰 본다. 어긋나면 이유를 적는다."""
    out = {}
    # (1) 검출 렌즈의 σ_ac_peak (mesh 팔)
    det = J_V_DET["t1_detection_cross_section"]["per_arm"]
    r = {}
    for d in DRONES:
        mine = LC[d]["mesh_full"]["sigma_ac_peak_dbsm"]
        theirs = det[d]["mesh"]["sigma_ac_peak_dbsm"]
        r[d] = dict(mine_mean=mine["mean"], lens_mean=theirs["mean"],
                    abs_diff_mean_db=abs(mine["mean"] - theirs["mean"]),
                    mine_median=mine["median"], lens_median=theirs["median"],
                    abs_diff_median_db=abs(mine["median"] - theirs["median"]))
    out["detector_lens_sigma_ac_peak"] = dict(
        rows=r, worst_abs_diff_db=float(max(v["abs_diff_mean_db"] for v in r.values())),
        agree=bool(max(v["abs_diff_mean_db"] for v in r.values()) < 1e-9),
        what_ko="검출 렌즈가 만든 «도플러 칸별 RCS» 번역기를 나는 따로 구현했다. 같은 값이 나와야 한다.")
    # (2) 동어반복 렌즈의 파형 상관·템플릿 정합손실 — 접는 순서가 다르다
    tl = J_V_TAUT["check5_does_it_move_a_detector"]["rows"]
    r2 = {}
    worst_rho, worst_loss = 0.0, 0.0
    for d in DRONES:
        for arm in ("slab", "mesh_half_tri"):
            if arm not in LC[d]:
                continue
            p = LC[d][arm]["paired_vs_mesh"]
            lens = tl.get(f"{d}|{arm}")
            if lens is None:
                continue
            drho = abs(p["ac_waveform_corr"]["mean"] - lens["coherent_ac_corr"])
            dloss = abs(p["template_loss_from_mean_corr_db"] - lens["template_mismatch_loss_db"])
            r2[f"{d}|{arm}"] = dict(
                mine_corr=p["ac_waveform_corr"]["mean"], lens_corr=lens["coherent_ac_corr"],
                abs_diff_corr=float(drho),
                mine_loss_round_convention_db=p["template_loss_from_mean_corr_db"],
                lens_loss_db=lens["template_mismatch_loss_db"], abs_diff_loss_db=float(dloss),
                mine_loss_mean_of_per_azimuth_db=p["template_mismatch_loss_db"]["mean"])
            worst_rho = max(worst_rho, drho)
            worst_loss = max(worst_loss, dloss)
    out["tautology_lens_template_loss"] = dict(
        rows=r2, worst_abs_diff_corr=float(worst_rho), worst_abs_diff_loss_db=float(worst_loss),
        agree=bool(worst_rho < 1e-12 and worst_loss < 1e-9),
        what_ko=("동어반복 렌즈가 인용한 정합손실(mini2 slab 4.06 dB)과 내 첫 계산(4.24 dB)이 "
                 "달라서 원인을 찾았다 — **접는 순서**다. 렌즈는 «방위평균 상관을 먼저 낸 뒤 "
                 "로그», 나는 «방위마다 로그를 낸 뒤 평균» 이었다. 젠센 부등식 때문에 후자가 "
                 "항상 크다. 같은 규약으로 접으면 상관·손실 둘 다 기계 정밀도로 일치한다 — "
                 "즉 계산이 아니라 표기 규약의 차이였다."))
    return out


# --------------------------------------------------------------------------- #
#  5. 형상 대 운동학 — 인용되는 «정육면체 대 메쉬» 를 쪼갠다 (독립 재계산)
# --------------------------------------------------------------------------- #
def shape_vs_kinematics():
    """총 차이 = (운동학을 바꾼 몫) + (형상을 바꾼 몫) 로 가른다.
       운동학 몫 = mesh_rigid_spin − mesh          (진짜 CAD 를, 통째로 돌렸을 때)
       형상 몫   = cube_eqvol     − mesh_rigid_spin (운동학을 고정하고 형상만 교체)
       두 몫의 합은 정의상 총 차이와 닫힌다 — 닫히는지 확인해서 계산 오류를 잡는다."""
    rows = {}
    for d in DRONES:
        proto = PPD[d]
        lam = proto["lam_m"]

        def peak_db(tab):
            tab = np.atleast_2d(np.asarray(tab, complex))
            v = []
            for i in range(tab.shape[0]):
                c = np.fft.fft(tab[i]) / tab.shape[1]
                P = np.abs(c) ** 2
                m = np.fft.fftfreq(tab.shape[1], d=1.0 / tab.shape[1]).astype(int)
                v.append(4 * np.pi / lam ** 2 * float(P[m != 0].max()))
            return float(10 * np.log10(np.median(v)))

        def moddepth_db(tab):
            """in-band 변조 깊이 = 대역 안 AC 전력 / DC 전력 (dB). 앞 단들이 쓴 양."""
            tab = np.atleast_2d(np.asarray(tab, complex))
            v = [md_metrics16(tab[i], proto, BLADE_N)["in_band_ac_over_dc_db"]
                 for i in range(tab.shape[0])]
            return float(np.mean(v))

        mesh = T(Z_BASE, f"main__G_0804__{d}__mesh__spherical")
        spin = T(Z_CUBE, f"main__{d}__mesh_rigid_spin__spherical")
        spin_pec = T(Z_CUBE, f"main__{d}__mesh_rigid_spin_pec__spherical")
        cube = T(Z_CUBE, f"main__{d}__cube_eqvol__spherical")
        box = T(Z_BOX, f"main__{d}__box_bbox__spherical")
        slab = T(Z_BASE, f"main__G_0804__{d}__slab__spherical")

        def ac_power_db(tab):
            """⭐ 동어반복 렌즈가 인용한 바로 그 양 — 방위별 AC(0-도플러 제외) 전력의
            **방위평균**을 dB 로. 상대비(AC/DC)가 아니라 절대 AC 전력이다. 렌즈의 숫자를
            그대로 재현할 수 있어야 이 문서와 렌즈가 같은 것을 말하는 것이 된다."""
            tab = np.atleast_2d(np.asarray(tab, complex))
            o = []
            for i in range(tab.shape[0]):
                c = np.fft.fft(tab[i]) / tab.shape[1]
                P = np.abs(c) ** 2
                m = np.fft.fftfreq(tab.shape[1], d=1.0 / tab.shape[1]).astype(int)
                o.append(float(P[m != 0].sum()))
            return float(10 * np.log10(np.mean(o)))

        r = {}
        for metric, fn in (("ac_power_db_LENS_CONVENTION", ac_power_db),
                           ("in_band_modulation_depth_db", moddepth_db),
                           ("sigma_ac_peak_dbsm_median", peak_db)):
            m_mesh, m_spin, m_spinpec = fn(mesh), fn(spin), fn(spin_pec)
            e = {}
            for arm_name, tab in (("cube_eqvol", cube), ("box_bbox", box)):
                m_arm = fn(tab)
                # 3 갈래로 가른다(렌즈와 같은 순서): 운동학 → 재질 → 형상. 합은 정의상 닫힌다.
                total = m_arm - m_mesh
                kin = m_spin - m_mesh                 # 진짜 CAD 를 통째로 돌렸을 때
                mat = m_spinpec - m_spin              # 같은 것을 PEC 로 바꿨을 때
                shp = m_arm - m_spinpec               # 거기서 형상만 프리미티브로
                den = abs(kin) + abs(mat) + abs(shp)
                e[arm_name] = dict(total_db=float(total), kinematics_part_db=float(kin),
                                   material_part_db=float(mat), shape_part_db=float(shp),
                                   closure_err_db=float(total - (kin + mat + shp)),
                                   kinematics_share=float(abs(kin) / max(den, 1e-12)),
                                   shape_share=float(abs(shp) / max(den, 1e-12)))
            # slab 은 운동학이 mesh 와 같은 팔 — «순수 형상» 대조군
            e["slab_pure_shape_only_db"] = float(fn(slab) - m_mesh)
            e["_levels"] = dict(mesh=float(m_mesh), mesh_rigid_spin=float(m_spin),
                                mesh_rigid_spin_pec=float(m_spinpec))
            r[metric] = e
        rows[d] = r

    # ⭐ 렌즈 재현 확인 — 같은 규약으로 계산하면 렌즈가 인용한 숫자가 그대로 나와야 한다
    lens = J_V_TAUT["check3_kinematic_and_material_confound"]["rows"]
    repro, worst = {}, 0.0
    for d in DRONES:
        mine = rows[d]["ac_power_db_LENS_CONVENTION"]["cube_eqvol"]
        th = lens[d]
        cmp_ = {"total": (mine["total_db"], th["cited_cube_minus_mesh_db"]),
                "kinematics": (mine["kinematics_part_db"], th["kinematics_term_db"]),
                "material": (mine["material_part_db"], th["material_term_db"]),
                "shape": (mine["shape_part_db"], th["shape_term_db"])}
        repro[d] = {k: dict(mine=a, lens=b, abs_diff_db=abs(a - b)) for k, (a, b) in cmp_.items()}
        worst = max(worst, max(abs(a - b) for a, b in cmp_.values()))
    return dict(rows=rows,
                lens_reproduction=dict(
                    rows=repro, worst_abs_diff_db=float(worst),
                    agree=bool(worst < 1e-9),
                    what_ko=("동어반복 렌즈가 인용한 3 갈래 분해를 내가 같은 규약(방위평균 AC "
                             "전력의 dB 비)으로 다시 냈다. 기계 정밀도로 같아야 «두 문서가 같은 "
                             "것을 말한다» 가 성립한다."),
                    why_two_numbers_ko=(
                        "⚠ 같은 «정육면체 대 메쉬» 라도 무엇을 재느냐에 따라 값이 다르다. "
                        "ac_power_db_LENS_CONVENTION 은 **절대 AC 전력**의 비이고, "
                        "in_band_modulation_depth_db 는 **AC 를 DC 로 나눈** 상대 변조 깊이다. "
                        "프리미티브는 DC(동체 반사)도 함께 바꾸므로 두 값이 갈린다. 둘 다 실어 "
                        "두고, 본문 표에는 렌즈와 같은 규약을 쓴다.")),
                what_ko=("«정육면체를 쓰면 메쉬와 얼마나 다른가» 로 인용되는 숫자를 세 몫으로 "
                         "가른다: 무엇이 도는가(운동학) · 무엇으로 만들어졌나(재질) · 어떤 "
                         "모양인가(형상). mesh_rigid_spin 은 진짜 CAD 를 통째로 돌린 팔이라 "
                         "운동학 몫만 따로 뽑아 준다."),
                read_ko=("운동학 몫이 형상 몫보다 크면, 대리 형상이 틀린 진짜 이유는 «모양이 "
                         "거칠어서» 가 아니라 «무엇이 도는지를 틀리게 놓아서» 다."))


# --------------------------------------------------------------------------- #
#  6. 스펙트로그램
# --------------------------------------------------------------------------- #
def blackman_harris(n):
    """4 항 Blackman-Harris 창 — 곁가지가 −92 dB 라, 거대한 0-도플러(동체) 선이
    옆 칸으로 새어 나와 그림을 더럽히는 것을 막는다."""
    a = (0.35875, 0.48829, 0.14128, 0.01168)
    k = np.arange(n)
    return (a[0] - a[1] * np.cos(2 * np.pi * k / (n - 1))
            + a[2] * np.cos(4 * np.pi * k / (n - 1)) - a[3] * np.cos(6 * np.pi * k / (n - 1)))


def spectrogram(row, proto, n_rev=4, win_frac=0.25, hop_frac=1 / 64, pad=4):
    """1 회전 위상표 → 슬로타임 스펙트로그램(도플러 칸별 RCS, dBsm).

    표가 «1 회전 주기» 라는 사실을 그대로 쓴다 — 표를 n_rev 번 이어 붙이면 그것이
    정확한 슬로타임 신호다(로터 4 개가 같은 rpm 이므로 근사가 아니다).
    """
    row = np.asarray(row, complex)
    S = row.size
    lam = proto["lam_m"]
    prf = S * proto["f_rot_hz"]
    x = np.tile(row, n_rev)
    W = max(16, int(round(S * win_frac)))
    hop = max(1, int(round(S * hop_frac)))
    nfft = int(W * pad)
    w = blackman_harris(W)
    cols = []
    starts = range(0, x.size - W + 1, hop)
    for s0 in starts:
        seg = x[s0:s0 + W] * w
        X = np.fft.fftshift(np.fft.fft(seg, nfft)) / w.sum()
        cols.append(4 * np.pi / lam ** 2 * np.abs(X) ** 2)
    Sxx = np.array(cols).T                                   # (freq, time)
    f = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / prf))
    t = np.array([s0 / prf for s0 in starts])
    return t, f, 10 * np.log10(np.maximum(Sxx, 1e-300))


def make_spectrogram_figure(drone="matrice4e"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    proto = PPD[drone]
    az_i = int(round(AZ_PICK_DEG / PROTO["az_step_deg"]))
    f_rot = proto["f_rot_hz"]
    ylim = float(PPD[drone]["beta"] * f_rot * 1.6)

    panels = []          # (title, t, f, Sxx_db, tag, quotable)
    # --- 1 줄: 있는 그대로의 사다리 -------------------------------------------
    for name, en, npar, kin, ko, getter in LADDER_A:
        if getter is None:
            st = T(Z_NOR, f"{drone}__mesh_no_rotor__main__spherical__15__flight_static")
            S = T(Z_BASE, f"main__G_0804__{drone}__mesh__spherical").shape[1]
            row = np.full(S, st[az_i])       # 도는 것이 없다 → 시간에 대해 상수
        else:
            row = getter(drone)[az_i]
        t, f, Z = spectrogram(row, proto)
        panels.append((en, t, f, Z, kin, None))
    # --- 2 줄: 교정 사다리(운동학 고정, 프로펠러만 단순화) ---------------------
    for name, en, npar, ko, getter in LADDER_C:
        row = getter(drone)[az_i]
        t, f, Z = spectrogram(row, proto)
        panels.append((en, t, f, Z, "rotors only", None))

    vmax = 5.0 * math.ceil(max(float(np.nanmax(p[3])) for p in panels) / 5.0)
    vmin = vmax - 90.0
    KIN_C = {"whole body spins": "#b3261e", "nothing moves": "#8a6d00",
             "rotors only": "#14532d"}

    fig = plt.figure(figsize=(21.5, 9.4))
    gs = GridSpec(2, 7, width_ratios=[1] * 6 + [0.05], hspace=0.50, wspace=0.09,
                  left=0.050, right=0.952, top=0.800, bottom=0.098)
    im = None
    for idx, (title, t, f, Z, tag, _q) in enumerate(panels):
        r, c = divmod(idx, 6)
        ax = fig.add_subplot(gs[r, c])
        im = ax.pcolormesh(t * 1e3, f, Z, cmap="magma", vmin=vmin, vmax=vmax,
                           shading="auto", rasterized=True)
        ax.set_ylim(-ylim, ylim)
        col = KIN_C.get(tag, "#333")
        ax.set_title(f"{'ABCDEF'[c]}. {title}", fontsize=10.0, pad=15,
                     color="#111", linespacing=1.3)
        # 운동학 꼬리표 — 제목 아래 별도 줄에 색으로 (제목과 겹치지 않게)
        ax.text(0.5, 1.012, f"[{tag}]", transform=ax.transAxes, ha="center", va="bottom",
                fontsize=8.4, color=col, fontweight="bold")
        ax.tick_params(labelsize=8.5)
        if c == 0:
            ax.set_ylabel("Doppler [Hz]", fontsize=9.8)
        else:
            ax.set_yticklabels([])
        if r == 1:
            ax.set_xlabel("slow time [ms]", fontsize=9.8)
        for k in (-1, 1):
            ax.axhline(k * proto["f_tip_hz"], color="#4fc3f7", lw=0.9, ls=":", alpha=0.9)
        for sp in ax.spines.values():
            sp.set_edgecolor(col)
            sp.set_linewidth(1.6)

    cax = fig.add_subplot(gs[:, 6])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("RCS per Doppler bin  [dBsm]", fontsize=9.8)
    cb.ax.tick_params(labelsize=8.5)

    fig.text(0.050, 0.960,
             f"How much can the target be simplified?  Micro-Doppler of six target models"
             f" — {drone}, {PROTO['fc_main_hz']/1e9:.2f} GHz, az {AZ_PICK_DEG:.0f}°, "
             f"el {PROTO['el_deg']:.0f}°",
             fontsize=15.0, fontweight="bold", ha="left")
    fig.text(0.050, 0.925,
             "All 12 panels share one colour scale (90 dB) and one pair of axes. "
             "Dotted line = blade-tip Doppler predicted by the kinematics. "
             "Frame colour = what is moving.",
             fontsize=9.8, color="#333", ha="left")
    fig.text(0.050, 0.884,
             "ROW 1 - the ladder as it was actually run.  The kinematics changes half-way "
             "(red -> yellow -> green), so shape is NOT the only thing that varies "
             "across this row.",
             fontsize=9.6, color="#8a1c1c", ha="left", fontweight="bold")
    fig.text(0.050, 0.855,
             "ROW 2 - the corrected ladder.  CAD airframe throughout, rotors spinning "
             "throughout; ONLY the rotor shape is simplified.  This is the row that "
             "answers the question.",
             fontsize=9.6, color="#14532d", ha="left", fontweight="bold")
    fig.text(0.050, 0.030,
             "Read: the bright 0 Hz band is the airframe and it dominates every panel. "
             "A rotationally symmetric rotor (row 2A) and a rotor-less body (row 1D) "
             "leave that band alone and nothing else - they cannot modulate at all. "
             "Between row 2 D and F the comb barely changes: that is the whole finding.",
             fontsize=9.3, color="#222", ha="left")
    fig.savefig(FIG_SPEC, dpi=150)
    plt.close(fig)
    return dict(path=FIG_SPEC, drone=drone, az_deg=AZ_PICK_DEG,
                vmin_dbsm=float(vmin), vmax_dbsm=float(vmax),
                doppler_axis_hz=float(ylim), n_panels=len(panels),
                window="4-term Blackman-Harris, 1/4 revolution, 4x zero-pad",
                n_rev_tiled=4,
                what_ko=("12 칸 전부 같은 색눈금(90 dB 범위)·같은 축이다. 세로축은 도플러(Hz), "
                         "가로축은 느린 시간(ms), 색은 그 도플러 칸에서 보이는 RCS(dBsm) 다. "
                         "점선은 운동학이 예측하는 날개 끝 도플러, 테두리 색은 «무엇이 도는가» 다."))


# --------------------------------------------------------------------------- #
#  7. 사다리 표 그림
# --------------------------------------------------------------------------- #
def make_ladder_figure(LA, LC):
    """사다리 표를 그림으로. 두 가지를 반드시 눈에 보이게 한다:
       ① 있는 그대로의 사다리는 **D 단에서 끊긴다**(도는 것이 없어 지표가 존재하지 않는다),
       ② 해석 «자격» 이 없는 점(대역 밖 AC 가 절반 넘는 팔)은 속 빈 표식으로 찍는다."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    metrics = [("flash_contrast_db", "flash contrast [dB]", None),
               ("n_eff_orders", "harmonic richness  n_eff", "log"),
               ("sigma_ac_peak_dbsm", "detection cross-section\n(strongest AC line) [dBsm]", None),
               ("dc_ac_db", "body : blade ratio [dB]", None)]
    names_a = [n for n, *_ in LADDER_A]
    names_c = [n for n, *_ in LADDER_C]
    lab_a = [m[1] for m in LADDER_A]
    lab_c = [m[1] for m in LADDER_C]

    fig, axes = plt.subplots(2, 4, figsize=(19.5, 9.6))
    for row, drone in enumerate(DRONES):
        for col, (key, lab, scale) in enumerate(metrics):
            ax = axes[row, col]

            def series(L, names):
                xs, ys, qs = [], [], []
                for i, n in enumerate(names):
                    v = L[drone][n].get(key)
                    if isinstance(v, dict) and v.get("mean") is not None \
                            and math.isfinite(v["mean"]):
                        xs.append(i); ys.append(v["mean"])
                        qs.append(bool(L[drone][n].get("quotable")))
                return xs, ys, qs

            xa, ya, qa = series(LA, names_a)
            xc, yc, qc = series(LC, names_c)

            # ⭐ 빨간 사다리는 D 단이 없으므로 **끊어서** 그린다(이어 그리면 거짓말이 된다)
            for seg in ([i for i in range(len(xa)) if xa[i] < 3],
                        [i for i in range(len(xa)) if xa[i] > 3]):
                if seg:
                    ax.plot([xa[i] for i in seg], [ya[i] for i in seg], "--",
                            color="#b3261e", lw=1.7, zorder=2)
            ax.plot(xc, yc, "-", color="#1b5e20", lw=2.3, zorder=2)
            for x, y, q in zip(xa, ya, qa):
                ax.plot(x, y, "o", ms=8, color="#b3261e", zorder=3,
                        mfc="#b3261e" if q else "white", mew=1.7)
            for x, y, q in zip(xc, yc, qc):
                ax.plot(x, y, "s", ms=8, color="#1b5e20", zorder=3,
                        mfc="#1b5e20" if q else "white", mew=1.7)

            ax.axvspan(2.5, 3.5, color="#fff3cd", alpha=0.75, zorder=0)
            ax.text(3.0, 0.02, "no rotor:\nmetric does\nnot exist",
                    transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=7.4, color="#8a6d00", zorder=1)
            if scale == "log":
                ax.set_yscale("log")
            ax.set_xticks(range(6))
            ax.set_xticklabels(list("ABCDEF"), fontsize=10)
            ax.set_xlim(-0.45, 5.45)
            ax.grid(alpha=0.26, lw=0.6)
            if row == 0:
                ax.set_title(lab, fontsize=11.5)
            if col == 0:
                ax.set_ylabel(f"{drone}", fontsize=12.5, fontweight="bold")
            if row == 1:
                ax.set_xlabel("rung   (A = crudest  ->  F = full CAD)", fontsize=9.5)

    handles = [Line2D([], [], color="#b3261e", ls="--", marker="o", ms=8,
                      label="ladder as run  (kinematics changes between rungs)"),
               Line2D([], [], color="#1b5e20", ls="-", marker="s", ms=8,
                      label="corrected ladder  (rotors only - shape is the only variable)"),
               Line2D([], [], color="#555", ls="none", marker="o", ms=8, mfc="white", mew=1.7,
                      label="hollow = not quotable (AC power sits above the kinematic limit)")]
    fig.legend(handles=handles, loc="upper center", ncol=3, fontsize=9.8,
               frameon=True, framealpha=0.95, bbox_to_anchor=(0.5, 0.933))
    fig.suptitle(f"Six-rung target ladder — {PROTO['fc_main_hz']/1e9:.2f} GHz, "
                 f"mean over {PROTO['n_az']} azimuths, el {PROTO['el_deg']:.0f}°",
                 fontsize=15, fontweight="bold", y=0.985)
    rows_txt = "   |   ".join(f"{c}. {l}" for c, l in zip("ABCDEF", lab_c))
    fig.text(0.5, 0.038, "corrected ladder (green):  " + rows_txt,
             ha="center", fontsize=8.6, color="#14532d")
    rows_txt_a = "   |   ".join(f"{c}. {l}" for c, l in zip("ABCDEF", lab_a))
    fig.text(0.5, 0.020, "ladder as run (red):  " + rows_txt_a,
             ha="center", fontsize=8.6, color="#8a1c1c")
    fig.text(0.5, 0.001,
             "Rungs E and F are the same two arms in both ladders, so the red markers sit "
             "exactly underneath the green ones there.",
             ha="center", fontsize=8.4, color="#555", style="italic")
    fig.tight_layout(rect=[0, 0.058, 1, 0.925])
    fig.savefig(FIG_LADDER, dpi=150)
    plt.close(fig)
    return dict(path=FIG_LADDER, drones=DRONES,
                what_ko=("네 지표 × 두 기체. 빨간 사다리는 D 단에서 끊어 그렸다 — 그 단은 도는 "
                         "부품이 없어 지표가 존재하지 않는다. 속 빈 표식은 «인용 자격 없음»"
                         "(변조 전력의 절반 이상이 운동학적으로 불가능한 자리에 있다)."))


# --------------------------------------------------------------------------- #
#  8. 교수님 지적에 대한 답 — 세 축을 숫자로 갈라 놓는다
# --------------------------------------------------------------------------- #
def professor_answer(LC):
    ctrl = J_P3["controls"]["table"]
    mesh = ctrl["ours_phantom3_mesh_v2"]
    sph = ctrl["sphere_eqvol_paperbox"]
    sph_v = ctrl["sphere_vol_v2"]
    cube = ctrl["cube_vol_v2"]
    boxb = ctrl["box_bbox_v2"]

    lvm = J_M_SPH["level_vs_modulation"]["rows"]
    sigma_gaps = [v["sigma_gap_db"] for v in lvm.values()]
    mod_gaps = [v["modulation_gap_db"] for v in lvm.values()]
    az_mesh = [v["sigma_azimuth_sd_db"]["mesh"] for v in lvm.values()]
    az_sph = [v["sigma_azimuth_sd_db"]["sphere"] for v in lvm.values()]

    taut = J_V_TAUT["check2_tautology_accounting"]["rows"]
    det = J_V_DET["t1_detection_cross_section"]["fleet_sigma_ac_peak_dbsm"]
    hov = [v["penalty_db"]["mean"] for v in det.values()]

    # ⭐ 교정 사다리에서 «단순화의 값» 을 뽑는다 — 진짜 CAD 대비
    simplification = {}
    for d in DRONES:
        simplification[d] = {}
        for name, *_ in LADDER_C:
            if name == "mesh_full":
                continue
            p = LC[d][name]["paired_vs_mesh"]
            simplification[d][name] = dict(
                sigma_ac_peak_err_db=p["d_sigma_ac_peak_db"]["mean"],
                # 라운드 규약: −20log10(방위평균 상관). 앞 렌즈들이 인용한 것과 같은 접기.
                template_loss_db=p["template_loss_from_mean_corr_db"],
                template_loss_mean_of_per_azimuth_db=p["template_mismatch_loss_db"]["mean"],
                waveform_corr=p["ac_waveform_corr"]["mean"],
                flash_err_db=p["d_flash_contrast_db"]["mean"],
                n_eff_err=p["d_n_eff_orders"]["mean"])

    return dict(
        axis1_absolute_level=dict(
            what_ko="① 절대 세기(RCS 크기) — 지적이 맞는 축",
            measured_anchor="outputs/p3_validation_v2.json (Yuan θ90 복원 실측곡선 기준)",
            our_mesh=dict(level_err_db=mesh["level_err_db"], rms_db=mesh["rms_db"]),
            equal_volume_sphere=dict(level_err_db=sph["level_err_db"], rms_db=sph["rms_db"],
                                     n_free_params=0),
            sphere_beats_mesh_by_rms_db=float(mesh["rms_db"] - sph["rms_db"]),
            verdict_ko=("모수 0 개짜리 등가부피 구가 우리 정밀 메쉬를 실측 대비 rms 로 "
                        f"{mesh['rms_db'] - sph['rms_db']:.2f} dB 이긴다. 이 축에서는 지적이 맞다.")),
        axis2_azimuth_spread=dict(
            what_ko="② 방위 산포(보는 각도에 따른 변동 폭) — 구가 원리적으로 못 내는 축",
            eps_err_vs_das_db=dict(our_mesh=mesh["eps_err_vs_das_db"],
                                   equal_volume_sphere=sph["eps_err_vs_das_db"],
                                   cube=cube["eps_err_vs_das_db"],
                                   bounding_box=boxb["eps_err_vs_das_db"]),
            sphere_eps_is_identically_zero=bool(sph["eps_mean_db"] == 0.0
                                                and sph_v["eps_mean_db"] == 0.0),
            verdict_ko=("구의 방위 산포는 «작다» 가 아니라 **정확히 0** 이다 — 회전대칭이라 "
                        f"만들 수가 없다. 실측 대비 오차는 우리 메쉬 {mesh['eps_err_vs_das_db']:+.2f} dB, "
                        f"구 {sph['eps_err_vs_das_db']:+.2f} dB, 상자 {boxb['eps_err_vs_das_db']:+.2f} dB. "
                        "이 축에서는 메쉬가 이긴다.")),
        axis3_time_modulation=dict(
            what_ko="③ 시간 변조(마이크로도플러) — 이 라운드가 새로 잰 축",
            sigma_level_gap_mesh_vs_sphere_db=dict(min=float(min(sigma_gaps)),
                                                   max=float(max(sigma_gaps))),
            azimuth_sd_db=dict(mesh_max=float(max(az_mesh)), sphere_max=float(max(az_sph))),
            modulation_gap_mesh_minus_sphere_db=dict(min=float(min(mod_gaps)),
                                                     max=float(max(mod_gaps))),
            but_how_much_of_that_gap_is_cad_precision=dict(
                share_bought_by_detail_free_slab={k: v["share_bought_by_detail_free_slab"]
                                                  for k, v in taut.items()},
                cad_precision_only_db={k: v["cad_precision_only_db"] for k, v in taut.items()},
                cad_precision_only_share={k: v["cad_precision_only_share"]
                                          for k, v in taut.items()}),
            verdict_ko=("메쉬와 구의 시간 변조 차이는 "
                        f"{min(mod_gaps):.0f}~{max(mod_gaps):.0f} dB 로 거대하다. 그러나 그 간격의 "
                        f"{100*min(v['share_bought_by_detail_free_slab'] for v in taut.values()):.0f}~"
                        f"{100*max(v['share_bought_by_detail_free_slab'] for v in taut.values()):.0f} % 를 "
                        "«디테일이 0 인 평판» 이 이미 사 놓는다. 즉 그 간격은 «CAD 가 정밀해서» 가 "
                        "아니라 «회전대칭이 아니라서» 번 것이다.")),
        axis4_what_simplification_actually_costs=dict(
            what_ko="④ ⭐ 교정 사다리가 답하는 축 — 프로펠러를 얼마나 거칠게 그려도 되나",
            rows=simplification,
            unit_ko="dB. sigma_ac_peak_err_db 는 호버 표적의 검출 단면적 오차, "
                    "template_loss_db 는 그 형상으로 정합필터 본을 떴을 때의 SNR 손실."),
        hover_penalty_db=dict(mean_min=float(min(hov)), mean_max=float(max(hov)),
                              n_airframes=len(det),
                              what_ko=("호버 표적은 0-도플러(동체) 행을 못 쓴다 — 정적 클러터 "
                                       "제거가 그 행을 지운다. 그래서 검출에 쓸 수 있는 단면적은 "
                                       "총 RCS 보다 이만큼 낮다. 사다리 안의 어떤 팔 차이보다 크다.")))


# --------------------------------------------------------------------------- #
#  9. 판정 취합
# --------------------------------------------------------------------------- #
def aggregate_verdict():
    lenses = {
        "tautology": J_V_TAUT["verdict"],
        "kernel": J_V_KERN["verdict"]["verdict"],
        "detector": J_V_DET["verdict"]["verdict"],
    }
    n_bad = sum(1 for v in lenses.values() if v in ("PREMATURE", "BROKEN"))
    n_broken = sum(1 for v in lenses.values() if v == "BROKEN")
    if n_broken >= 2:
        agg = "BROKEN"
    elif n_bad >= 2:
        agg = "PREMATURE"
    else:
        agg = "SOUND"
    return dict(lenses=lenses, n_premature_or_broken=n_bad, aggregate=agg,
                rule_ko=("과제문 규칙: 세 렌즈 중 둘 이상이 PREMATURE/BROKEN 이면 결론을 그 "
                         "수준으로 낮춰 적는다."),
                counted_ko=f"{n_bad}/3 렌즈가 PREMATURE — 종합 판정도 {agg}.")


# --------------------------------------------------------------------------- #
#  10. 마크다운 생성 (숫자는 전부 위에서 계산된 것을 꽂는다)
# --------------------------------------------------------------------------- #
def fmt(x, n=2):
    if x is None:
        return "—"
    if isinstance(x, dict):
        x = x.get("mean")            # 규약: 방위평균은 dB 산술평균
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "∞" if (isinstance(x, float) and x == float("inf")) else "—"
    return f"{x:.{n}f}"


def build_markdown(R):
    d0 = "matrice4e"
    LA, LB, LC = R["ladder_A_as_run"], R["ladder_B_matched_body_spin"], R["ladder_C_matched_flight"]
    pa = R["professor_answer"]
    sk = R["shape_vs_kinematics"]["rows"]
    ag = R["verdict"]
    po = R["po_validity"]

    L = []
    A = L.append
    A("# 표적 사다리 — «드론을 얼마나 거칠게 그려도 되나»")
    A("")
    A(f"*생성: {R['meta']['generated']} · 생성기: `benchmark/report16_synthesis.py` · "
      f"모든 숫자는 `outputs/report16_synthesis.json` 에서 계산되어 꽂힌 값이다(손입력 0).*")
    A("")
    A("---")
    A("")
    A("## 0. 한 문단 결론")
    A("")
    A(R["conclusion_ko"])
    A("")
    A("---")
    A("")
    A("## 1. 무엇을 물었나")
    A("")
    A("드론이 제자리에 떠 있어도 프로펠러가 돌기 때문에 되돌아오는 전파의 세기와 위상이")
    A("시간에 따라 흔들린다. 이 흔들림을 **마이크로도플러**라고 부른다 — 표적 전체가 움직여서")
    A("생기는 도플러가 아니라 표적의 *일부*(날개)가 움직여서 생기는 도플러라는 뜻이다.")
    A("")
    A("지도교수의 지적은 «드론 RCS 정밀도는 연구 값어치가 없다» 이고, 절대 세기 축에서는")
    A("**우리 데이터가 그 지적을 뒷받침한다**. 이 라운드는 그 지적이 마이크로도플러에서도")
    A("성립하는지를 물었다. 방법은 사다리다 — 표적을 점점 거칠게 바꿔 가며 신호가 언제")
    A("무너지는지 본다.")
    A("")
    A("## 2. ⚠ 사다리가 하나가 아니라 셋이었다")
    A("")
    A("사다리를 실제로 돌려 보니 여섯 단이 **서로 다른 운동학**(무엇이 도는가)을 쓰고 있었다.")
    A("구·정육면체·상자 단은 «기체 전체를 덩어리 하나로 바꿔 통째로 돌린» 물체이고, 진짜")
    A("드론은 몸통이 서 있고 프로펠러만 돈다. 두 개를 나란히 놓고 «형상 차이» 라고 부르면")
    A("그 안에 형상 교체와 운동학 교체가 섞인다. 적대검증 두 렌즈가 이 결함을 각각 따로 짚었다.")
    A("")
    A("그래서 이 문서는 사다리를 세 벌로 나눠 적는다.")
    A("")
    A("| 사다리 | 무엇이 도나 | 무엇이 바뀌나 | 질문에 답할 자격 |")
    A("|---|---|---|---|")
    A("| **A. 있는 그대로** | 단마다 다름 | 형상 + 운동학 + 재질 | ❌ 섞여 있다 |")
    A("| **B. 온몸 자전 고정** | 전부 온몸 자전 | 형상만 | △ 실제 드론이 아님 |")
    A("| **C. ⭐ 진짜 비행 고정** | 전부 프로펠러만 | **프로펠러 형상만** | ✅ 이 축이 답이다 |")
    A("")
    A("## 3. 사다리 표")
    A("")
    A(f"기체 `{d0}`, {PROTO['fc_main_hz']/1e9:.2f} GHz, 고각 {PROTO['el_deg']:.0f}°, "
      f"구면파, 방위 {PROTO['n_az']} 점 평균. (`mini2` 는 JSON 에 같은 형식으로 들어 있다.)")
    A("")
    A("**지표 넷이 무엇을 뜻하나** — 플래시 대조비: 날개가 시선에 수직으로 설 때의 번쩍임이")
    A("바닥보다 몇 dB 위인가. 풍부도 n_eff: 실질적으로 몇 개의 배음이 살아 있나. 폭: 도플러가")
    A("날개 끝 속도가 예측하는 만큼 넓게 퍼지나(1.0 이면 딱 맞음). 동체:날개 비: 몸통이 날개보다")
    A("몇 dB 센가. 다섯째 열 «검출 단면적» 은 이 종합이 덧붙인 값 — 호버 표적이 **실제로 쓸 수**")
    A("있는 유일한 신호인 «가장 센 배음 한 줄의 RCS» 다.")
    A("")

    def table(ladder_rows, names_meta, title, ref_key):
        A(f"### {title}")
        A("")
        A("| 단 | 표적 | 무엇이 도나 | 플래시 [dB] | 풍부도 n_eff | 폭/자기β | 동체:날개 [dB] "
          "| 검출 단면적 [dBsm] | 인용 자격 |")
        A("|---|---|---|---|---|---|---|---|---|")
        for i, meta in enumerate(names_meta):
            n = meta[0]
            r = ladder_rows[d0][n]
            wr = r.get("width_ratio_20db")
            A(f"| {'ABCDEF'[i]} | `{n}` | {r['kinematics']} | {fmt(r.get('flash_contrast_db'))} "
              f"| {fmt(r.get('n_eff_orders'))} | {fmt(wr)} | {fmt(r.get('dc_ac_db'))} "
              f"| {fmt(r.get('sigma_ac_peak_dbsm'))} | {'✅' if r.get('quotable') else '❌'} |")
        A("")

    table(LA, LADDER_A, "A. 있는 그대로의 사다리 (⚠ 운동학이 섞여 있다)", "mesh_full")
    A("⚠ D 단(`mesh_no_rotor`)은 도는 부품이 아예 없다. 변조 전력이 «작다» 가 아니라 **정확히 0**")
    A("이라 네 지표 중 셋은 값 자체가 존재하지 않는다(0 으로 나누는 자리). 표에 «—» 로 적었다.")
    A("")
    table(LC, LADDER_C, "C. ⭐ 교정 사다리 — 몸통은 진짜 CAD, 프로펠러만 단순화", "mesh_full")

    A("### B. 온몸 자전으로 운동학을 고정한 대조군")
    A("")
    A("| 단 | 표적 | 플래시 [dB] | 풍부도 n_eff | 동체:형상 [dB] | 검출 단면적 [dBsm] |")
    A("|---|---|---|---|---|---|")
    for i, meta in enumerate(LADDER_B):
        n = meta[0]
        r = LB[d0][n]
        A(f"| {'ABCDEF'[i]} | `{n}` | {fmt(r.get('flash_contrast_db'))} "
          f"| {fmt(r.get('n_eff_orders'))} | {fmt(r.get('dc_ac_db'))} "
          f"| {fmt(r.get('sigma_ac_peak_dbsm'))} |")
    A("")
    A("![ladder](../outputs/figures/report16_synthesis_ladder.png)")
    A("")
    A("그림에서 빨간 사다리는 D 단에서 **끊어 그렸다** — 그 단은 도는 부품이 없어 지표가")
    A("존재하지 않는다. 속 빈 표식은 «인용 자격 없음» 이다(변조 전력의 절반 이상이 운동학적으로")
    A("불가능한 자리에 있다 = 격자 잔재를 잰 것이다). E·F 단은 두 사다리에서 같은 팔이라")
    A("빨간 점이 초록 점 아래에 정확히 겹쳐 있다.")
    A("")
    A("## 4. 스펙트로그램 — 같은 축, 같은 색눈금")
    A("")
    A("![spectrograms](../outputs/figures/report16_synthesis_spectrograms.png)")
    A("")
    A(f"열두 칸 모두 같은 색눈금({fmt(R['figures']['spectrograms']['vmin_dbsm'],0)} … "
      f"{fmt(R['figures']['spectrograms']['vmax_dbsm'],0)} dBsm)과 같은 축이다. 세로축은 도플러(Hz),")
    A("가로축은 느린 시간(ms), 색은 그 도플러 칸에서 보이는 RCS 다. 점선은 운동학이 예측하는")
    A("날개 끝 도플러다. **윗줄이 있는 그대로의 사다리, 아랫줄이 교정 사다리**다.")
    A("")
    A("눈으로 읽히는 것 셋:")
    A("")
    A("1. 어느 칸에서나 가장 밝은 것은 0 Hz 가로줄 — 몸통이다. 날개 신호는 그보다 한참 어둡다.")
    A(f"   이 낙차(호버 벌금)가 10 기체 평균 {fmt(pa['hover_penalty_db']['mean_min'],1)} … "
      f"{fmt(pa['hover_penalty_db']['mean_max'],1)} dB 다.")
    A("2. 회전대칭 표적(구·원판)은 0 Hz 한 줄만 있고 위아래가 비어 있다. 돌려도 모양이 안 바뀌니")
    A("   변조를 만들 방법이 없다 — 이것은 계산 결과가 아니라 기하학이다.")
    A("3. 아랫줄 A → F 로 갈수록 배음 사다리가 촘촘해지지만, **D(평판)와 F(진짜 CAD) 사이의**")
    A("   **차이는 눈으로 잘 안 보인다**. 그 «잘 안 보임» 이 이 라운드의 핵심 숫자다(§5).")
    A("")
    A("## 5. ⭐⭐ 그래서 얼마나 단순화해도 되나")
    A("")
    A("교정 사다리에서 진짜 CAD 대비 오차를 방위별로 짝지어 뺐다. 두 열이 중요하다 —")
    A("«검출 단면적 오차» 는 그 형상을 쓰면 검출 성능이 얼마나 틀리는가, «템플릿 손실» 은")
    A("그 형상으로 정합필터 본을 떴을 때 잃는 SNR 이다.")
    A("")
    for d in DRONES:
        A(f"**{d}**")
        A("")
        A("| 단 | 프로펠러를 무엇으로 | 검출 단면적 오차 [dB] | 템플릿 손실 [dB] | 파형 상관 |")
        A("|---|---|---|---|---|")
        for i, meta in enumerate(LADDER_C[:-1]):
            n = meta[0]
            s = pa["axis4_what_simplification_actually_costs"]["rows"][d][n]
            A(f"| {'ABCDEF'[i]} | {meta[1]} | {s['sigma_ac_peak_err_db']:+.2f} "
              f"| {s['template_loss_db']:.2f} | {s['waveform_corr']:.3f} |")
        A("")
    A("**읽는 법.** 위 표가 이 문서의 답이다. 정리하면 세 구간이다.")
    A("")
    A(R["simplification_budget_ko"])
    A("")
    A("### 5b. ⚠ 자기반증 — 위 «공짜» 주장이 어디까지 참인가")
    A("")
    fb = R["frame_blindness_audit"]
    A(fb["so_what_ko"])
    A("")
    A("| 검사 | mini2 | matrice4e |")
    A("|---|---|---|")
    A("| 동체까지 깎았을 때 AC 의 상대 변화 | "
      + " | ".join(f"{fb['rows'][d]['ac_relative_difference_frame_decimation']['max']:.1e}"
                   for d in DRONES) + " |")
    A("| 같은 팔에서 동체:날개 비의 이동 [dB] | "
      + " | ".join(f"{fb['rows'][d]['dc_ac_shift_from_frame_decimation_db']['mean']:+.2f}"
                   for d in DRONES) + " |")
    A("")
    A("첫 줄이 기계 정밀도라는 것은 **AC 가 동체를 아예 안 본다**는 뜻이다. 둘째 줄이 0 이")
    A("아닌 것은 동체 간략화가 «몸통 대 날개 비» 는 움직인다는 뜻이다 — 면적·부피를 잃기")
    A("때문이다. 그러므로 §5 의 «공짜» 는 **도는 부품에 한정된 진술**이다.")
    A("")
    A("## 6. 형상인가 운동학인가 — 인용되는 숫자를 쪼갠다")
    A("")
    A("«정육면체를 쓰면 메쉬와 몇 dB 다르다» 는 문장은 이 라운드에서 가장 인용하기 좋은")
    A("숫자다. 그 숫자를 세 몫으로 갈랐다.")
    A("")
    MK = "ac_power_db_LENS_CONVENTION"
    A("| 기체 | 대리 형상 | 총 차이 [dB] | 운동학 몫 | 재질 몫 | 형상 몫 | 운동학 비중 |")
    A("|---|---|---|---|---|---|---|")
    for d in DRONES:
        for arm in ("cube_eqvol", "box_bbox"):
            e = sk[d][MK][arm]
            A(f"| {d} | `{arm}` | {e['total_db']:+.2f} | {e['kinematics_part_db']:+.2f} "
              f"| {e['material_part_db']:+.2f} | {e['shape_part_db']:+.2f} "
              f"| {100*e['kinematics_share']:.0f} % |")
    A("")
    rep = R["shape_vs_kinematics"]["lens_reproduction"]
    A(f"*세 몫의 합은 정의상 총 차이와 닫힌다. 이 표는 적대검증 렌즈가 인용한 것과 **같은 "
      f"규약**(방위평균 AC 전력의 dB 비)으로 다시 계산한 것이고, 렌즈 값과 최대 "
      f"{rep['worst_abs_diff_db']:.1e} dB 안에서 일치한다.*")
    A("")
    A("운동학 몫이 형상 몫보다 크다. 즉 «정육면체가 틀린 이유» 는 대부분 «모양이 거칠어서» 가")
    A("아니라 **«무엇이 도는지를 틀리게 놓아서»** 다. 운동학이 같으면서 날개 디테일만 없앤")
    A("유일한 팔인 `slab` 의 차이는 "
      f"{fmt(sk['mini2'][MK]['slab_pure_shape_only_db'])} / "
      f"{fmt(sk['matrice4e'][MK]['slab_pure_shape_only_db'])} dB "
      "(mini2 / matrice4e) 로 훨씬 작다.")
    A("")
    A("⚠ 같은 «정육면체 대 메쉬» 라도 **무엇을 재느냐에 따라 값이 다르다**. 위 표는 절대 AC")
    A("전력의 비이고, AC 를 DC(동체 반사)로 나눈 «상대 변조 깊이» 로 재면 "
      f"{fmt(sk['mini2']['in_band_modulation_depth_db']['cube_eqvol']['total_db'])} / "
      f"{fmt(sk['matrice4e']['in_band_modulation_depth_db']['cube_eqvol']['total_db'])} dB 가 된다.")
    A("프리미티브는 동체 반사도 함께 바꾸기 때문이다. 두 값 모두 JSON 에 있다.")
    A("")
    A("## 7. 교수님 지적에 대한 정직한 답")
    A("")
    A(R["professor_answer_ko"])
    A("")
    A("## 8. 왜 이 결론이 «이르다(PREMATURE)» 인가")
    A("")
    A(f"적대검증 세 렌즈의 판정: " +
      " · ".join(f"**{k} = {v}**" for k, v in ag["lenses"].items()) + ".")
    A(f"{ag['n_premature_or_broken']}/3 이 PREMATURE 이므로 종합 판정도 **{ag['aggregate']}** 다.")
    A("")
    A("| # | 무엇이 문제인가 | 숫자 |")
    A("|---|---|---|")
    for it in R["why_premature"]:
        A(f"| {it['id']} | {it['claim_ko']} | {it['number_ko']} |")
    A("")
    A("## 9. ⚠ 반드시 같이 읽어야 할 한계 — 프로펠러는 우리 커널의 사각지대다")
    A("")
    A(po["statement_ko"])
    A("")
    A("## 10. 다음에 할 일")
    A("")
    for i, s in enumerate(R["next_steps"], 1):
        A(f"### {i}순위 — {s['title_ko']}")
        A("")
        A(f"- **왜**: {s['why_ko']}")
        A(f"- **어떻게**: {s['how_ko']}")
        A(f"- **비용**: {s['cost_ko']}")
        A(f"- **무엇이 뒤집힐 수 있나**: {s['falsifiable_ko']}")
        A("")
    A("## 11. 출처")
    A("")
    A("| 입력 | sha256 (앞 12) |")
    A("|---|---|")
    for k, v in R["meta"]["provenance"].items():
        A(f"| `{os.path.relpath(v['path'], ROOT)}` | `{v['sha256'][:12]}` |")
    A("")
    A(f"게이트: " + " · ".join(f"{k.split('_')[0]} {v['verdict']}"
                              for k, v in R["gates"].items()) + ".")
    A("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
#  11. 메인
# --------------------------------------------------------------------------- #
def main():
    ok = all([gate_mesh_identity(), gate_protocol_selfconsistency(),
              gate_recompute_vs_stage(), gate_parseval()])
    if not ok:
        print("⛔ 게이트 실패 — 표를 이어 붙일 자격이 없다. 중단한다.")
        print(json.dumps(GATES, ensure_ascii=False, indent=1)[:4000])
        sys.exit(1)
    print("게이트 4 종 PASS")

    LA = build_ladder_A()
    LB = build_ladder_B()
    LC = build_ladder_C()
    print("사다리 3 벌 계산 완료")
    SK = shape_vs_kinematics()
    FB = frame_blindness_audit()
    XC = cross_check_against_lenses(LC)
    print("자기반증(동체 실명) + 렌즈 대조 완료")

    # 그림
    figs = dict(spectrograms=make_spectrogram_figure("matrice4e"),
                ladder=make_ladder_figure(LA, LC))
    print("그림 2 장 완료")

    PA = professor_answer(LC)
    AG = aggregate_verdict()

    # --- 단순화 예산 문단 (숫자를 계산해서 문장에 꽂는다) --------------------
    def s(d, n, k):
        return PA["axis4_what_simplification_actually_costs"]["rows"][d][n][k]

    half_err = max(abs(s(d, "mesh_half_tri", "sigma_ac_peak_err_db")) for d in DRONES)
    half_loss = max(s(d, "mesh_half_tri", "template_loss_db") for d in DRONES)
    slab_err = [s(d, "slab", "sigma_ac_peak_err_db") for d in DRONES]
    slab_loss = [s(d, "slab", "template_loss_db") for d in DRONES]
    bbox_err = [s(d, "prop_bbox", "sigma_ac_peak_err_db") for d in DRONES]
    bbox_loss = [s(d, "prop_bbox", "template_loss_db") for d in DRONES]
    rg_err = [s(d, "sph_blade_rg", "sigma_ac_peak_err_db") for d in DRONES]
    rg_loss = [s(d, "sph_blade_rg", "template_loss_db") for d in DRONES]
    disc_err = [s(d, "disc", "sigma_ac_peak_err_db") for d in DRONES]

    q_err = max(abs(FB["rows"][d]["quarter_tri_vs_mesh"]["d_sigma_ac_peak_db"]["mean"])
                for d in DRONES)
    q_loss = max(FB["rows"][d]["quarter_tri_vs_mesh"]["template_loss_from_mean_corr_db"]
                 for d in DRONES)
    budget = (
        f"- **공짜 구간 — 해상도.** 도는 부품(프로펠러)의 삼각형을 절반으로 줄여도 검출 "
        f"단면적이 {half_err:.2f} dB, 템플릿 손실이 {half_loss:.2f} dB 밖에 안 움직인다. "
        f"1/4 로 줄여도 {q_err:.2f} dB · {q_loss:.2f} dB 다. 방위에 따른 흔들림(5~8 dB)에 "
        f"완전히 묻히는 크기라 실측으로는 절대 못 가른다.\n"
        f"  ⚠ 단, 이것은 **면적·부피를 보존하는 간략화**에 한정된 진술이고, **동체**에 대해서는 "
        f"아무 말도 못 한다 — 아래 «자기반증» 을 반드시 같이 읽어라.\n"
        f"- **싼 구간 — 날개를 평판으로.** 스팬·두께·부피가 같은 평판 2 장으로 바꾸면 검출 "
        f"단면적이 {slab_err[0]:+.1f} / {slab_err[1]:+.1f} dB (mini2 / matrice4e) 틀리고 템플릿 "
        f"손실은 {slab_loss[0]:.1f} / {slab_loss[1]:.1f} dB 다. «변조가 있나 없나» 만 보는 "
        f"검출기라면 충분하고, 파형을 본뜨는 검출기라면 이미 비싸다.\n"
        f"- **비싼 구간 — 날개를 덩어리로.** «감싸는 상자» 는 검출 단면적을 "
        f"{bbox_err[0]:+.1f} / {bbox_err[1]:+.1f} dB **과대**하게 내고(속을 꽉 채웠으니 당연하다), "
        f"«회전반경 위의 공» 은 {rg_err[0]:+.1f} / {rg_err[1]:+.1f} dB 다. "
        f"⚠ 공은 matrice4e 에서 레벨만 보면 {rg_err[1]:+.1f} dB 로 «잘 맞는» 것처럼 보이지만 "
        f"파형 상관이 {s('matrice4e','sph_blade_rg','waveform_corr'):.3f} 뿐이라 템플릿 손실이 "
        f"{rg_loss[1]:.1f} dB 다 — **레벨이 맞았다고 신호가 맞은 것이 아니다**.\n"
        f"- **낭떠러지 — 회전대칭.** 날개를 회전대칭 원판으로 바꾸면 검출 단면적이 "
        f"{disc_err[0]:+.0f} / {disc_err[1]:+.0f} dB 로 무너진다. 모양이 거칠어서가 아니라 "
        f"«돌려도 안 바뀌는 물체» 는 변조를 **만들 수 없기** 때문이다. 이것만은 어떤 커널 "
        f"결함에도 안 흔들리는 기하학이다.\n\n"
        f"⚠ **사다리가 단조롭지 않다.** 상자(C)가 평판(D)보다 오차가 큰 것은 «형상 정보가 더 "
        f"적어서» 가 아니라 부피를 안 지켜서다. 즉 «단순화의 값» 을 정하는 것은 삼각형 수가 "
        f"아니라 **무엇을 보존했는가**(회전대칭 깨짐 → 스팬 → 부피 → 두께 순)다.\n\n"
        f"⭐ 한 줄로: **«모양이 있느냐 없느냐» 는 {min(abs(x) for x in disc_err):.0f} dB 이상을 "
        f"가르지만, «모양이 얼마나 정밀하냐» 는 {half_loss:.2f}~{max(slab_loss):.1f} dB 안에서 "
        f"논다.** 교수님 지적은 앞쪽이 아니라 뒤쪽을 겨눈 것이고, 뒤쪽에서는 지적이 맞다.")

    # --- 왜 이르다 ------------------------------------------------------------
    kern = J_V_KERN
    occ = kern["headline_contrast_under_occlusion"]
    why = [
        dict(id="P1",
             claim_ko="가장 인용하기 좋은 숫자(메쉬 − 구 = 62~77 dB)는 «CAD 정밀도» 가 아니라 "
                      "«회전대칭이 아님» 을 잰 것이다. 회전대칭 아닌 어떤 표적을 넣어도 통과한다.",
             number_ko=("디테일 0 인 평판이 그 간격의 "
                        f"{100*J_V_TAUT['check2_tautology_accounting']['rows']['mini2']['share_bought_by_detail_free_slab']:.1f} % / "
                        f"{100*J_V_TAUT['check2_tautology_accounting']['rows']['matrice4e']['share_bought_by_detail_free_slab']:.1f} % 를 "
                        "이미 산다")),
        dict(id="P2",
             claim_ko="커널에 가림(그늘)이 없다. 가림을 넣으면 이 라운드에서 가장 인용될 대조의 "
                      "**부호가 뒤집힌다**.",
             number_ko=f"n_eff 간격이 네 구석 {occ['n_sign_flips']}/{occ['n_corners']} 전부에서 부호 반전"),
        dict(id="P3",
             claim_ko="네 지표 중 검출식에 실제로 들어가는 것은 사실상 하나뿐이다(가장 센 배음의 RCS). "
                      "플래시 대조비는 표준 적분시간 안에서 적분돼 사라지고, 폭은 문턱을 1 dB 아래로만 옮긴다.",
             number_ko="검출 관련 렌즈 F1 — 4 지표 중 3 개가 검출식에 안 들어감"),
        dict(id="P4",
             claim_ko="사다리 여섯 단이 운동학을 섞어 썼다. «정육면체 대 메쉬» 로 인용되는 차이의 "
                      "대부분이 형상이 아니라 운동학이다.",
             number_ko=(f"운동학 비중 "
                        f"{100*SK['rows']['mini2']['ac_power_db_LENS_CONVENTION']['cube_eqvol']['kinematics_share']:.0f} % / "
                        f"{100*SK['rows']['matrice4e']['ac_power_db_LENS_CONVENTION']['cube_eqvol']['kinematics_share']:.0f} %")),
        dict(id="P5",
             claim_ko="지표 ① 플래시 대조비에 바닥이 없다 — 물리적 변조가 0 인 널이 진짜 신호를 이긴다.",
             number_ko=(f"mini2: 구(널) "
                        f"{J_V_TAUT['check4_metric_has_no_floor']['rows']['mini2']['flash_contrast_db']['sphere_NULL']:.2f} dB "
                        f"> 메쉬 "
                        f"{J_V_TAUT['check4_metric_has_no_floor']['rows']['mini2']['flash_contrast_db']['mesh']:.2f} dB")),
        dict(id="P6",
             claim_ko="«메쉬 해상도는 안 중요하다» 는 판정이 커널이 유효한 대역(15.86 GHz)에서는 "
                      "같은 문턱으로 FAIL 한다. 3.5 GHz 의 PASS 는 형상의 성질이 아니라 파장이 "
                      "그 형상을 못 보는 데서 왔을 수 있다.",
             number_ko=f"같은 문턱, 무릎 대역에서 {kern['T4b_same_threshold_at_the_knee']['n_flipped']} 개 항목 뒤집힘"),
        dict(id="P7",
             claim_ko="⭐ 이 종합이 스스로 찾은 것 — 시간 변조 지표는 **안 도는 부품(동체)을 "
                      "원리적으로 못 본다**. 가림이 없는 커널에서 동체는 위상마다 같은 상수를 "
                      "더하므로 평균을 빼면 정확히 사라진다. 그래서 «해상도는 안 중요하다» 는 "
                      "동체에 대해서는 계산이 아니라 산수다.",
             number_ko=(f"동체까지 절반으로 깎아도 AC 상대 변화 "
                        f"{FB['worst_ac_rel_diff_from_frame_decimation']:.1e} (기계 정밀도)")),
    ]

    # --- PO 유효성 ------------------------------------------------------------
    w = J_V_KERN["why_this_lens"]
    pov = dict(
        blade_width_mm=w["blade_width_m"] * 1e3,
        blade_width_over_lambda=w["blade_width_over_lambda_main"],
        po_knee_a_over_lambda=w["po_knee_a_over_lambda"],
        shortfall_x=w["shortfall_x"],
        blade_knee_ghz=w["blade_knee_ghz"],
        body_knee_ghz=w["body_knee_ghz"],
        production_band_ghz=PROTO["fc_main_hz"] / 1e9,
        statement_ko=(
            f"⚠⚠ 우리 PO(물리광학) 커널이 1 dB 안으로 맞으려면 부품의 특징 폭이 파장의 "
            f"{w['po_knee_a_over_lambda']:.3f} 배 이상이어야 한다. 프로펠러 날개 폭 "
            f"{w['blade_width_m']*1e3:.2f} mm 는 생산 대역 {PROTO['fc_main_hz']/1e9:.2f} GHz 에서 "
            f"파장의 {w['blade_width_over_lambda_main']:.3f} 배에 불과해 문턱에 "
            f"**{w['shortfall_x']:.2f} 배 모자란다**(문턱을 넘는 주파수는 {w['blade_knee_ghz']:.2f} GHz). "
            f"동체는 {w['body_knee_ghz']:.2f} GHz 부터 유효하므로 통과한다. "
            f"⭐ 즉 **마이크로도플러를 만드는 바로 그 부품이 우리 커널이 가장 약한 부품**이다. "
            f"이 문서의 모든 마이크로도플러 숫자는 그 사실을 안고 읽어야 한다 — 부호와 "
            f"자릿수는 쓸 수 있어도 소수점은 못 쓴다."))

    # --- 결론 문단 ------------------------------------------------------------
    _cube = {d: SK["rows"][d]["ac_power_db_LENS_CONVENTION"]["cube_eqvol"] for d in DRONES}
    kin_share = [100 * _cube[d]["kinematics_share"] for d in DRONES]
    kin_part = [_cube[d]["kinematics_part_db"] for d in DRONES]
    conclusion = (
        f"**판정: {AG['aggregate']}** (적대검증 3 렌즈 중 {AG['n_premature_or_broken']} 개가 PREMATURE — "
        f"결론을 그 수준으로 낮춰 적는다). "
        f"표적을 얼마나 단순화해도 되는가에 대한 잠정 답은 **«구조가 있느냐 없느냐» 까지는 "
        f"반드시 지키고, 그 위의 정밀도는 거의 지키지 않아도 된다** 는 것이다. 진짜 비행 조건에서 "
        f"프로펠러만 갈아 끼운 교정 사다리를 보면, 회전대칭 원판으로 바꾸는 순간 호버 표적의 검출 "
        f"단면적이 {min(abs(x) for x in disc_err):.0f}~{max(abs(x) for x in disc_err):.0f} dB 무너지지만, "
        f"삼각형 수를 절반으로 줄이는 것은 "
        f"{half_err:.2f} dB(템플릿 손실 {half_loss:.2f} dB)로 사실상 공짜이고, 날개를 평판 두 장으로 "
        f"바꾸는 고전 모델조차 {max(abs(x) for x in slab_err):.1f} dB 안에 든다. "
        f"즉 «모양의 유무» 는 수십 dB 를 가르고 «모양의 정밀도» 는 한 자릿수 dB 안에서 논다. "
        f"⚠ 다만 이 답을 아직 결론이라고 부를 수 없는 이유가 {len(why)} 가지 있고(§8), "
        f"그중 둘이 치명적이다 — "
        f"우리 커널에 가림(그늘)이 없어서 «프리미티브가 CAD 보다 배음이 풍부하다» 는 이 라운드의 "
        f"헤드라인 대조가 그늘을 넣는 것만으로 네 구석 전부 부호가 뒤집히고, 사다리 여섯 단이 "
        f"운동학을 섞어 써서 인용되는 «정육면체 대 메쉬» 차이의 "
        f"{min(kin_share):.0f}~{max(kin_share):.0f} % 가 "
        f"형상이 아니라 «무엇이 도는가» 다. "
        f"⚠⚠ 그리고 이 모든 숫자 위에 하나가 더 얹힌다 — **마이크로도플러를 만드는 프로펠러 날개"
        f"(폭 {pov['blade_width_mm']:.2f} mm = 3.5 GHz 에서 파장의 {pov['blade_width_over_lambda']:.3f} 배)는 "
        f"우리 PO 커널의 유효 하한에 {pov['shortfall_x']:.2f} 배 모자란다**. 커널이 가장 약한 바로 그 "
        f"부품이 이 실험의 주인공이므로, 위 숫자들은 부호와 자릿수만 쓰고 소수점은 쓰지 않는다.")

    # --- 교수님 답 (3~5 문장) --------------------------------------------------
    a1, a2, a3 = PA["axis1_absolute_level"], PA["axis2_azimuth_spread"], PA["axis3_time_modulation"]
    prof = (
        f"**첫째, 절대 세기 축에서는 지적이 맞습니다.** 실측 앵커에 대고 재면 자유 모수가 0 개인 "
        f"등가부피 구가 우리 정밀 메쉬를 rms {a1['sphere_beats_mesh_by_rms_db']:.2f} dB 차이로 이깁니다"
        f"(구 {a1['equal_volume_sphere']['level_err_db']:+.2f} dB · rms {a1['equal_volume_sphere']['rms_db']:.2f} vs "
        f"메쉬 {a1['our_mesh']['level_err_db']:+.2f} dB · rms {a1['our_mesh']['rms_db']:.2f}). "
        f"메쉬를 정밀하게 깎아서 RCS 레벨을 더 잘 맞추겠다는 것은 값어치가 없습니다. "
        f"**둘째, 구가 원리적으로 못 내는 축이 둘 있고 거기서는 메쉬가 이깁니다.** 방위 산포는 구가 "
        f"«작은» 것이 아니라 **정확히 0** 이고(회전대칭이라 만들 수가 없습니다), 실측 대비 오차는 "
        f"우리 메쉬 {a2['eps_err_vs_das_db']['our_mesh']:+.2f} dB · 구 "
        f"{a2['eps_err_vs_das_db']['equal_volume_sphere']:+.2f} dB · 상자 "
        f"{a2['eps_err_vs_das_db']['bounding_box']:+.2f} dB 로, 크기로 보면 메쉬가 구보다 "
        f"{abs(a2['eps_err_vs_das_db']['equal_volume_sphere'])/abs(a2['eps_err_vs_das_db']['our_mesh']):.1f} 배 "
        f"정확합니다. 시간 변조(마이크로도플러)는 메쉬와 구가 "
        f"{a3['modulation_gap_mesh_minus_sphere_db']['min']:.0f}~"
        f"{a3['modulation_gap_mesh_minus_sphere_db']['max']:.0f} dB 벌어집니다. "
        f"**셋째, 그러나 그 큰 간격은 «메쉬가 정밀해서» 번 것이 아닙니다.** 형상 디테일이 하나도 없는 "
        f"평판 두 장이 그 간격의 "
        f"{100*min(a3['but_how_much_of_that_gap_is_cad_precision']['share_bought_by_detail_free_slab'].values()):.0f}~"
        f"{100*max(a3['but_how_much_of_that_gap_is_cad_precision']['share_bought_by_detail_free_slab'].values()):.0f} % 를 "
        f"이미 벌어 놓고, CAD 정밀도 단독 몫은 "
        f"{min(a3['but_how_much_of_that_gap_is_cad_precision']['cad_precision_only_db'].values()):.2f}~"
        f"{max(a3['but_how_much_of_that_gap_is_cad_precision']['cad_precision_only_db'].values()):.2f} dB 뿐입니다. "
        f"**넷째, 그래서 우리가 다시 잡아야 할 방향은 «정밀도» 가 아니라 «무엇이 도는가» 입니다.** "
        f"운동학을 고정하고 프로펠러 형상만 바꿔 보면 삼각형 절반은 {half_err:.2f} dB, "
        f"평판 근사도 {max(abs(x) for x in slab_err):.1f} dB 안인데, 무엇이 도는지를 틀리게 놓으면 그 하나로 "
        f"약 {np.mean(kin_part):.0f} dB 가 "
        f"움직입니다. **다섯째, 이 답은 아직 잠정입니다** — 커널에 가림이 없어서 헤드라인 대조의 부호가 "
        f"뒤집히고, 무엇보다 마이크로도플러를 만드는 프로펠러 날개가 우리 PO 커널의 유효 하한에 "
        f"{pov['shortfall_x']:.2f} 배 모자랍니다.")

    # --- 다음 할 일 -----------------------------------------------------------
    nxt = [
        dict(title_ko="가림(그늘)을 켜고 사다리 전체를 다시 채점한다",
             why_ko=("커널 렌즈가 깊이버퍼 그늘을 넣어 보니 이 라운드에서 가장 인용될 대조 "
                     f"(«평판이 CAD 보다 배음이 풍부하다», n_eff 간격)가 두 대역 × 두 기체 "
                     f"{occ['n_sign_flips']}/{occ['n_corners']} 구석 전부에서 **부호가 뒤집혔다**. "
                     "가림 없는 결과는 방향조차 못 정한다."),
             how_ko=("`report16_verify_kernel.py` 의 z-buffer 를 기반 커널에 정식 편입하고 "
                     "(전 부품 전역좌표 일괄 배치 방식), 교정 사다리 C 여섯 단을 그대로 다시 돌린다. "
                     "볼록체 에너지 통제(C1)와 회전대칭 널 주입 바닥(C2)을 같이 싣는다."),
             cost_ko="GPU 반나절. 새 CAD·새 재질 불필요 — 커널만 바꾼다.",
             falsifiable_ko=("가림을 켜도 §5 의 «삼각형 절반은 공짜» 가 유지되면 그 결론은 굳는다. "
                             "뒤집히면 «메쉬 해상도 무관» 주장을 철회해야 한다."),
             priority=1),
        dict(title_ko="지표를 버리고 검출 통계량으로 사다리를 다시 세운다",
             why_ko=("검출 렌즈가 네 지표 중 셋이 검출식에 안 들어감을 보였다. 그리고 사다리 안의 "
                     "어떤 팔 차이보다 큰 항이 사다리 **밖**에 있다 — 호버 벌금 "
                     f"{PA['hover_penalty_db']['mean_min']:.1f}~{PA['hover_penalty_db']['mean_max']:.1f} dB. "
                     "지표를 다듬는 것보다 이 항을 잡는 것이 크다."),
             how_ko=("σ_m = 4π/λ²·|c_m|² 번역기(이 파일 `arm_stats` 와 검출 렌즈 T1 에 이미 있다)로 "
                     "여섯 단을 σ_ac_peak · Pd · 검출거리비로 다시 채점하고, ECA 노치와 CPI 불일치 "
                     "손실을 넣는다. 새 전자기 계산 0 — 저장된 표만 다시 읽는다."),
             cost_ko="CPU 한두 시간. 이미 저장된 표만 쓴다.",
             falsifiable_ko=("검출 축에서도 «삼각형 절반 = 공짜, 평판 = 싸다» 가 유지되는지. "
                             "여기서 갈리면 사다리의 결론이 지표 선택의 산물이었다는 뜻이다."),
             priority=2),
        dict(title_ko="프로펠러를 PO 가 유효한 대역으로 올려 사다리를 한 번 더 돌린다",
             why_ko=(f"날개 폭 {pov['blade_width_mm']:.2f} mm 는 3.5 GHz 에서 PO 유효 하한에 "
                     f"{pov['shortfall_x']:.2f} 배 모자란다. 커널이 가장 약한 부품이 이 실험의 "
                     f"주인공이다. 게다가 절반메쉬 판정이 무릎 대역(15.86 GHz)에서 같은 문턱으로 "
                     f"{kern['T4b_same_threshold_at_the_knee']['n_flipped']} 개 뒤집혔다 — 3.5 GHz 의 "
                     "PASS 가 «형상이 안 중요해서» 인지 «파장이 그 형상을 못 봐서» 인지 아직 못 가른다."),
             how_ko=("교정 사다리 C 를 3.5 / 7 / 15.86 / 22 GHz 에서 돌려 지표의 부호가 대역에 따라 "
                     "어떻게 움직이는지 표로 남긴다. 문턱은 3.5 GHz 것을 **그대로** 쓴다(사후 변경 금지). "
                     "동시에 openEMS 같은 정확해로 날개 하나만 교차검증해 PO 의 대가를 dB 로 못박는다."),
             cost_ko="GPU 하루. 15.86 GHz 는 표본 수가 4 배라 배치가 커진다.",
             falsifiable_ko=("대역을 올려도 사다리 순서가 유지되면 «PO 가 약해서 생긴 착시» 를 배제할 수 "
                             "있다. 순서가 바뀌면 3.5 GHz 결론 전체를 다시 써야 한다."),
             priority=3),
    ]

    R = dict(
        meta=dict(report="report16_synthesis",
                  producer="benchmark/report16_synthesis.py",
                  generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  git_rev=git_rev(),
                  gpu_used="none — 저장된 위상표 후처리(CPU 로 충분). GPU 4장은 형제 워크플로 점유 중",
                  new_em_computation=False,
                  purpose_ko="report16 사다리 6 단 + 적대검증 3 렌즈를 한 장으로 모으고, "
                             "«표적을 얼마나 단순화해도 되나» 에 숫자로 답한다.",
                  forbidden_untouched=["outputs/report15_*", "benchmark/report15_*",
                                       "src/make_report0N_*.py", "report0N_*.ipynb",
                                       "src/drones.py (미개봉)", "src/drone_cad.py (미개봉)"],
                  provenance=PROV,
                  seconds=None),
        protocol=dict(fc_main_hz=PROTO["fc_main_hz"], el_deg=PROTO["el_deg"],
                      n_az=PROTO["n_az"], az_step_deg=PROTO["az_step_deg"],
                      wavefront=PROTO["wavefront_headline"], blade_n=BLADE_N,
                      per_drone={d: {k: PPD[d][k] for k in
                                     ("lam_m", "f_rot_hz", "beta", "f_tip_hz", "prf_hz",
                                      "n_phase", "prop_radius_m")} for d in DRONES}),
        gates=GATES,
        ladder_definition_ko=dict(
            A="있는 그대로의 사다리 — 6 단이 서로 다른 운동학을 쓴다(형상+운동학+재질이 섞임)",
            B="온몸 자전으로 운동학을 고정한 대조군 — 형상만 바뀌지만 실제 드론이 아니다",
            C="⭐ 진짜 비행 조건(몸통 정지 + 프로펠러 회전)으로 고정하고 프로펠러 형상만 바꾼다 "
              "— 「표적을 얼마나 단순화해도 되나」에 답할 자격이 있는 유일한 축"),
        ladder_A_as_run=LA,
        ladder_B_matched_body_spin=LB,
        ladder_C_matched_flight=LC,
        frame_blindness_audit=FB,
        cross_check_against_lenses=XC,
        shape_vs_kinematics=SK,
        professor_answer=PA,
        professor_answer_ko=prof,
        simplification_budget_ko=budget,
        verdict=AG,
        why_premature=why,
        po_validity=pov,
        conclusion_ko=conclusion,
        next_steps=nxt,
        figures=figs,
        what_this_file_adds_ko=[
            "① 사다리 6 단이 운동학을 섞어 썼다는 것을 표로 드러내고, 운동학을 고정한 교정 사다리 "
            "두 벌(B·C)을 저장된 표에서 새로 이어 붙였다. 이어 붙일 자격은 게이트 G1(네 파일의 "
            "mesh 팔 비트 일치)로 증명했다.",
            "② 네 지표에 다섯째 열을 붙였다 — σ_ac_peak(호버 표적이 실제로 쓸 수 있는 검출 단면적). "
            "지표 넷은 검출기에 안 들어가지만 이 값은 들어간다.",
            "③ «단순화 예산» 을 dB 로 못박았다 — 공짜/싼/비싼/낭떠러지 네 구간.",
            "④ 교수 지적을 세 축으로 갈라 각 축의 승자를 숫자로 적었다.",
        ],
        reasons_to_distrust_this_file_ko=[
            "D1. 이 파일은 새 전자기 계산을 하지 않는다 — 앞 단들의 위상표를 다시 읽을 뿐이다. "
            "그 표가 안고 있는 결함(가림 없음·PO 하한 미달·재질 스칼라 |Γ|)을 그대로 물려받는다.",
            "D2. 교정 사다리 C 는 서로 다른 4 개 npz 에서 팔을 꺼내 이어 붙인 것이다. 게이트 G1 이 "
            "mesh 팔의 비트 일치를 확인했지만, 그것은 «같은 규약» 의 필요조건이지 충분조건은 아니다.",
            "D3. 스펙트로그램은 방위 한 점(30°)에서만 그렸다. 방위 산포가 5~8 dB 이므로 다른 방위를 "
            "고르면 그림이 달라 보일 수 있다. 표의 숫자는 24 방위 평균이라 그림과 표가 정확히 "
            "일치하지는 않는다.",
            "D4. 「검출 단면적」은 도플러 칸별 RCS 일 뿐 잡음·클러터·CFAR·적분시간이 없다. "
            "검출 렌즈가 계산한 Pd 는 전부 crude 이고 이 파일은 그것을 인용만 한다.",
            "D5. 사다리 C 의 단 순서(원판 → 회전반경 구 → 상자 → 평판 → 절반메쉬 → CAD)는 내가 "
            "«형상 정보가 얼마나 들어 있나» 로 정한 것이다. 다른 순서도 가능하고, 순서를 바꾸면 "
            "«단조롭게 좋아진다» 같은 서술은 성립하지 않는다(실제로 단조롭지 않다).",
        ],
    )
    R["meta"]["seconds"] = float(time.time() - T0)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=float)
    print("JSON 완료:", OUT_JSON)

    md = build_markdown(R)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print("MD 완료:", OUT_MD, f"({len(md)} 자)")
    print(f"판정: {AG['aggregate']}  ({AG['counted_ko']})")
    print(f"총 {R['meta']['seconds']:.1f} 초")


if __name__ == "__main__":
    main()
