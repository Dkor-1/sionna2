# -*- coding: utf-8 -*-
"""
report16_rung_box_bbox.py — ⭐ **사다리 한 단: 경계상자(box_bbox)의 마이크로도플러**
================================================================================

무엇을 하는가
--------------------------------------------------------------------------------
드론을 통째로 **직육면체 하나**로 바꿔치기하고, 진짜 드론과 **똑같이 돌려서** 되돌아오는
전파의 시간변조(마이크로도플러)를 잰다. 여기서 «경계상자(bounding box)» 는 우리 CAD 메쉬를
빈틈없이 감싸는 가장 작은 축정렬 직육면체다. 저장소가 이미 RCS 대조군으로 쓰던 바로 그
정의(benchmark/das_fleet_box_control.py 의 `box_bbox`)를 그대로 가져온다.

왜 이걸 하나 — 배경
--------------------------------------------------------------------------------
지도교수 지적은 «드론 RCS 정밀도는 연구 값어치가 없다» 이고, 우리 절대 RCS 데이터가 그 지적을
상당 부분 뒷받침한다(모수 0개짜리 등가부피 구가 우리 메쉬를 이긴다 — outputs/p3_validation_v2.json).
다만 구는 **방위 산포 ε 이 정확히 0.00** 이다 — 어느 방향에서 봐도 같은 모양이라 방향에 따른
변동을 원리적으로 못 만든다. 상자는 ε 을 만들지만 오차가 +4.0~4.5 dB 였다.

그래서 이 사다리가 묻는 것: **그 «구조» 우위가 마이크로도플러에서는 얼마나 크게 나타나는가.**
구는 돌려도 변조가 0 이어야 하고, 상자는 변조가 나오되 그것은 «블레이드의 변조» 가 아니라
«모서리·평면의 변조» 다. 이 파일은 그 차이를 숫자로 낸다.

⚠ 결론을 미리 정하지 않는다. 상자가 진짜 메쉬와 구별이 안 되면 그것이 더 중요한 결과다
  — 교수 지적이 마이크로도플러에서도 맞다는 뜻이 되고, 우리는 방향을 다시 잡아야 한다.

⭐ 사전 예측을 **계산 전에** 파일로 박는다
--------------------------------------------------------------------------------
`--predict` 로 먼저 outputs/report16_rung_box_bbox_prediction.json 을 쓴다. 그 파일의 수정시각과
sha256 을 결과 JSON 에 같이 적어서, «나중에 맞췄다고 말하는 것» 이 불가능하게 만든다.
본 계산은 그 파일을 **읽기만** 하고 절대 덮어쓰지 않는다.

공정성 — 이 라운드의 급소
--------------------------------------------------------------------------------
· 상자도 **실제로 돌린다**. 같은 회전축(기체 요축 = 원점을 지나는 z축), 같은 rpm(로터 rpm),
  같은 위상 격자(report16_base 규약이 계산한 n_phase). 안 돌리고 0 을 얻으면 동어반복이다.
· 거리·고각·방위 격자·주파수·파면은 기준 메쉬와 **완전히 동일**하다(report16_base 규약).
· 재질: 프리미티브는 PEC(|Γ|=1) — report16_base 의 sphere 팔, das_fleet_box_control 과 같은 규약.
  ⭐ 균질체에 곱해지는 |Γ| 는 복소장 전체에 **상수 하나**를 곱할 뿐이라 변조 지표는 전부
  불변이다(σ 만 20log10|Γ| 만큼 이동). 이 사실을 코드로 실증한다(material_invariance 블록).
· 부피 등가는 **계산해서** 맞춘다: 경계상자는 정의상 부피가 같지 않으므로(채움률 기록),
  «같은 종횡비 · 같은 부피» 상자(box_aspect_voleq)와 «같은 부피 정육면체»(cube_eqvol)를
  같이 돌려 «크기» 와 «종횡비» 를 갈라 놓는다.

⚠ 이 커널의 한계 (기준 라운드와 동일, 그대로 병기한다)
--------------------------------------------------------------------------------
프로펠러 블레이드(폭 13.78 mm)는 15.86 GHz 에서야 PO 유효 무릎(폭 ≥ 0.729λ)을 넘는다 —
생산대역 3.5 GHz 에서는 **마이크로도플러를 만드는 부품이 곧 커널이 가장 약한 부품**이다.
그래서 3.5 GHz(생산)와 15.86 GHz(무릎)를 둘 다 돌린다.
⭐ 그런데 **상자는 그 약점이 없다** — 상자의 면은 어느 대역에서도 파장보다 훨씬 크다.
   즉 이번 대조는 «커널이 편한 표적(상자)» 대 «커널이 불편한 표적(진짜 블레이드)» 이다.
   이 비대칭은 상자 쪽에 유리하게 작용하므로, «상자로 충분하다» 는 결론이 나올 경우
   그 결론은 보수적이지 않다. 반대로 «메쉬가 낫다» 가 나오면 그것은 보수적인 결론이다.
가림(occlusion) 없음 — dc_ac_db 가 가장 오염된다(절대값 인용 금지, 팔 사이 차이만 사용).

⛔ 이 파일이 쓰는 산출물은 report16_rung_box_bbox_* 뿐이다.
   report15_* · report0N_* · src/drones.py · src/drone_cad.py 는 건드리지 않는다(읽기만).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import report16_base as B                                              # noqa: E402

SCRATCH = os.environ.get("REPORT16_SCRATCH",
                         "/tmp/claude-1015/-workspace/"
                         "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report16")

OUT_JSON = os.path.join(ROOT, "outputs", "report16_rung_box_bbox.json")
OUT_PRED = os.path.join(ROOT, "outputs", "report16_rung_box_bbox_prediction.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report16_rung_box_bbox_tables.npz")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_rung_box_bbox.png")
BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")

KEYS = ("mini2", "matrice4e")

#  팔 목록 — 전부 «기체 전체를 프리미티브 하나로 바꾸고 같은 위상격자로 돌린다».
#    box_bbox          : ⭐ 이 단의 주인공. CAD 메쉬의 경계상자, **실제 놓인 자리**(bbox 중심)에 둔다.
#    box_bbox_axis     : 같은 상자를 회전축 위로 올린 판 — «축이탈 흔들림» 을 분리한다.
#    box_aspect_voleq  : 같은 종횡비인데 **부피를 메쉬와 같게** 줄인 상자 — «크기» 를 분리한다.
#    cube_eqvol        : 같은 부피 정육면체(축 위) — 사전 예측이 비교 대상으로 지목한 물체.
#    box_bbox_fine     : 점구름 4배 촘촘 — «성겨서 달라 보인다» 반론 차단.
ARMS_MAIN = ("box_bbox", "box_bbox_axis", "box_aspect_voleq", "cube_eqvol",
             "box_bbox_fine", "prop_bbox")
ARMS_HI = ("box_bbox", "box_bbox_axis", "cube_eqvol", "prop_bbox")
#  위상 격자 적정성 검사: 상자는 모서리가 프롭 팁보다 바깥이라 «상자 자신의 β» 가 더 크다.
#  기준 규약 격자(프롭 β 로 정한 S)로도 충분한지, S 를 상자 β 에 맞춰 키워서 확인한다.
ARM_S2 = "box_bbox"

MET_KEYS = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90", "dominant_order",
            "blade_comb_frac", "fd_edge_hz", "width_ratio", "dc_ac_db", "ac_frac_db",
            "sigma_eq_mean_dbsm", "ac_over_floor_db", "in_band_ac_frac",
            "in_band_ac_over_dc_db", "width_ratio_10db", "width_ratio_30db")


# =========================================================================== #
#  기하 — 상자를 만드는 데 필요한 모든 수를 **메쉬에서 계산**한다 (손입력 없음)
# =========================================================================== #
def mesh_volume(m):
    """닫힌 메쉬의 부피 [m³] (발산정리)."""
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(abs(np.einsum("ij,ij->i", p0, np.cross(p1, p2)).sum()) / 6.0)


def geom_facts(key):
    """기체 하나의 «상자 사다리» 기하 사실. 계산만 하고 GPU 를 쓰지 않는다."""
    from drones import DRONES, build_drone, build_frame
    s = DRONES[key]
    m = build_drone(s)
    V = np.asarray(m.v, float)
    ext = V.max(0) - V.min(0)
    ctr = 0.5 * (V.max(0) + V.min(0))
    vol = mesh_volume(m)
    fr = build_frame(s)
    Vf = np.asarray(fr.v, float)
    ext_f = Vf.max(0) - Vf.min(0)

    bbox_vol = float(ext[0] * ext[1] * ext[2])
    cube_side = vol ** (1.0 / 3.0)
    r_eq = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
    r_corner = 0.5 * float(math.hypot(ext[0], ext[1]))          # xy 평면 최대 회전반경
    r_face_x = 0.5 * float(ext[0])
    r_face_y = 0.5 * float(ext[1])
    R_prop = float(s.prop_dia_mm) / 2000.0
    scale_voleq = (vol / bbox_vol) ** (1.0 / 3.0)               # 종횡비 유지 부피등가 배율
    off = float(math.hypot(ctr[0], ctr[1]))                     # bbox 중심의 회전축 이탈 [m]

    out = dict(
        drone=s.name, key=key,
        mesh_bbox_m=[float(x) for x in ext],
        mesh_bbox_mm=[float(1000 * x) for x in ext],
        mesh_bbox_center_m=[float(x) for x in ctr],
        mesh_bbox_center_offset_from_spin_axis_mm=1000.0 * off,
        frame_only_bbox_mm=[float(1000 * x) for x in ext_f],
        mesh_volume_m3=vol, mesh_volume_L=1000.0 * vol,
        bbox_volume_m3=bbox_vol, bbox_volume_L=1000.0 * bbox_vol,
        bbox_fill_fraction=vol / bbox_vol,
        bbox_volume_over_mesh=bbox_vol / vol,
        cube_eqvol_side_m=cube_side, cube_eqvol_side_mm=1000.0 * cube_side,
        sphere_eqvol_radius_mm=1000.0 * r_eq,
        box_aspect_voleq_scale=scale_voleq,
        box_aspect_voleq_dims_mm=[float(1000 * x * scale_voleq) for x in ext],
        aspect_xy=float(max(ext[0], ext[1]) / min(ext[0], ext[1])),
        aspect_xy_note_ko=("1.000 이면 방위 90° 대칭(정사각 단면), 1 보다 크면 90° 대칭이 깨지고 "
                           "180° 대칭만 남는다. 이 수가 «주기» 예측의 핵심이다."),
        prop_radius_m=R_prop,
        r_corner_m=r_corner, r_face_x_m=r_face_x, r_face_y_m=r_face_y,
        r_corner_over_prop_radius=r_corner / R_prop,
        r_facemax_over_prop_radius=max(r_face_x, r_face_y) / R_prop,
        spin_rpm=float(s.hover_rpm), prop_blades=int(s.prop_blades),
        num_rotors=int(s.num_rotors))
    for fc, tagf in ((B.FC_MAIN, "main"), (B.FC_PO_KNEE, "hi")):
        lam = B.C0 / fc
        pr = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
        cel = math.cos(math.radians(B.EL_DEG))
        beta_box = 4.0 * math.pi * r_corner * cel / lam
        out[f"band_{tagf}"] = dict(
            fc_hz=fc, lam_m=lam,
            beta_prop=pr["beta"], beta_box_corner=beta_box,
            beta_ratio_box_over_prop=beta_box / pr["beta"],
            n_phase_protocol=pr["n_phase"],
            n_phase_needed_for_box=int(2 ** math.ceil(
                math.log2(max(64.0, B.OS_FACTOR * beta_box)))),
            nyquist_margin_protocol_grid_vs_box=pr["n_phase"] / (2.0 * beta_box),
            f_rot_hz=pr["f_rot_hz"], f_tip_prop_hz=pr["f_tip_hz"],
            f_corner_box_hz=beta_box * pr["f_rot_hz"],
            note_ko=("β 는 «한 바퀴 도는 동안 왕복위상이 흔들리는 폭 ÷ 2» 이자 «최고 하모닉 차수» 다. "
                     "상자 모서리가 프롭 팁보다 바깥이라 상자의 β 가 더 크다 — 그래서 상자는 "
                     "프롭보다 **넓은** 도플러를 낸다."))
    return out


# =========================================================================== #
#  ⭐ 사전 예측 — 계산 전에 파일로 박는다
# =========================================================================== #
def build_prediction():
    """숫자는 전부 기하에서 **계산**해서 넣는다(손입력 금지). 결과는 아직 하나도 없다."""
    G = {k: geom_facts(k) for k in KEYS}
    P = dict(
        _what="pre-registered prediction, written BEFORE any micro-Doppler was computed",
        written_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        rung="box_bbox (axis-aligned bounding box of build_drone mesh, PEC)",
        stated_by_task_ko=("과제문이 준 사전 예측: «큐브와 비슷하되 종횡비가 달라 주기가 다르게 "
                           "나올 수 있다». 아래는 그 예측을 검사 가능한 형태로 쪼갠 것이다."),
        geometry_inputs={k: {kk: G[k][kk] for kk in
                             ("mesh_bbox_mm", "aspect_xy", "cube_eqvol_side_mm",
                              "bbox_fill_fraction", "mesh_bbox_center_offset_from_spin_axis_mm",
                              "r_corner_over_prop_radius")} for k in KEYS},
        items={})

    ar = {k: G[k]["aspect_xy"] for k in KEYS}
    P["items"]["P1_box_is_not_a_null"] = dict(
        claim_ko=("상자는 회전대칭이 아니므로 **변조가 0 이 아니다**. 등가부피 구(널 팔)보다 "
                  "in_band_ac_over_dc_db 가 압도적으로 크다."),
        test="box_bbox.in_band_ac_over_dc_db  >>  sphere.in_band_ac_over_dc_db",
        threshold_db=20.0,
        confidence="high")
    P["items"]["P2_period_180_not_90"] = dict(
        claim_ko=("⭐ 과제문 예측의 알맹이. 정육면체는 방위 90° 대칭이라 AC 선이 **4의 배수 차수**에 "
                  "선다. 경계상자는 x·y 변 길이가 달라(종횡비 "
                  f"mini2 {ar['mini2']:.3f} · matrice4e {ar['matrice4e']:.3f}) 90° 대칭이 깨지고 "
                  "**180° 대칭만** 남는다 → 4의 배수가 아닌 **짝수 차수(2,6,10…)** 가 새로 생기고 "
                  "dominant_order 가 4 → 2 로 내려간다. 즉 «주기가 다르다» 가 맞다."),
        test=("cube_eqvol: sym_corr_90 ≈ 1 이고 order_class mod4==2 몫이 작다;  "
              "box_bbox_axis: sym_corr_90 이 뚜렷이 낮고 sym_corr_180 ≈ 1, mod4==2 몫이 크다"),
        threshold=dict(cube_sym90_min=0.9, box_sym90_max=0.5, box_sym180_min=0.9),
        confidence="high")
    P["items"]["P2b_offaxis_gives_odd_orders"] = dict(
        claim_ko=("경계상자의 중심은 회전축에서 벗어나 있다(mini2 "
                  f"{G['mini2']['mesh_bbox_center_offset_from_spin_axis_mm']:.1f} mm · matrice4e "
                  f"{G['matrice4e']['mesh_bbox_center_offset_from_spin_axis_mm']:.1f} mm). "
                  "축을 벗어난 강체가 돌면 위상중심이 원을 그리므로 **홀수 차수(특히 1차)** 가 "
                  "생긴다. 축 위에 올린 box_bbox_axis 에서는 그 홀수 성분이 사라져야 한다."),
        test="odd_order_frac(box_bbox) > odd_order_frac(box_bbox_axis), 후자는 ~0",
        confidence="high")
    P["items"]["P3_width_exceeds_prop_tip"] = dict(
        claim_ko=("상자 모서리 회전반경이 프롭 반경보다 크다(mini2 "
                  f"{G['mini2']['r_corner_over_prop_radius']:.2f}× · matrice4e "
                  f"{G['matrice4e']['r_corner_over_prop_radius']:.2f}×). 도플러 폭은 회전반경에 "
                  "비례하므로 width_ratio(프롭 f_tip 기준)가 **1 을 크게 넘는다** — 상자는 "
                  "«너무 넓은» 마이크로도플러를 낸다. 상한은 모서리비 그 자체다."),
        test="1.0 < width_ratio(box_bbox) <= r_corner_over_prop_radius (오차 1차수 이내)",
        predicted_upper={k: G[k]["r_corner_over_prop_radius"] for k in KEYS},
        confidence="high")
    P["items"]["P4_in_band_gate_will_misjudge_the_box"] = dict(
        claim_ko=("⭐ 지표 자체에 대한 예측. report16_base 의 in_band 판정기는 대역을 "
                  "1.5·β(프롭 반경 기준)로 잡는다. 상자의 진짜 내용은 그보다 바깥에 있으므로 "
                  "판정기가 상자를 «해석 불가(이산화 잔차)» 로 잘못 찍을 것이다. 상자 자신의 "
                  "β(모서리 기준)로 다시 재면 in_band 가 회복돼야 한다 — 즉 이 판정기는 "
                  "«표적 반경 = 프롭 반경» 을 암묵적으로 가정하고 있다."),
        test="in_band_ac_frac(protocol gauge) < 0.5  이면서  in_band_ac_frac(own gauge) > 0.9",
        confidence="medium")
    P["items"]["P5_flash_not_smaller_than_mesh"] = dict(
        claim_ko=("상자의 평평한 옆면은 시선과 수직이 되는 순간 통짜 정반사를 낸다. 진짜 블레이드는 "
                  "비틀림·캠버·테이퍼 때문에 스팬이 동시에 정렬되지 못해 봉우리가 번진다. 따라서 "
                  "flash_contrast_db 는 상자가 CAD 메쉬보다 **작지 않을** 것이다(크거나 비슷)."),
        test="paired(box_bbox − mesh).flash_contrast_db 의 mean ≥ 0",
        confidence="low",
        why_low_ko=("메쉬 팔은 정적 프레임의 큰 DC 를 갖고 있어 flash_contrast 의 바닥(median)이 "
                    "다르게 잡힌다. 방향이 뒤집힐 여지가 있다."))
    P["items"]["P6_blade_comb_cannot_tell_them_apart"] = dict(
        claim_ko=("⚠ 함정 예고. blade_comb_frac 은 «블레이드 수의 배수 차수» 에 실린 몫인데, "
                  "블레이드가 2장이라 그 빗은 «짝수 차수» 다. 그런데 축 위의 상자도 180° 대칭이라 "
                  "짝수 차수에만 선다 → **상자의 blade_comb_frac 도 1 에 가깝게 나온다**. "
                  "즉 이 지표는 «돌아가는 상자» 와 «진짜 블레이드» 를 구별하지 못한다."),
        test="blade_comb_frac(box_bbox_axis) > 0.9  이고  |blade_comb_frac(box) − mesh| < 0.2",
        confidence="high")
    P["items"]["P7_direction_of_richness_unknown"] = dict(
        claim_ko=("⛔ 방향을 미리 정하지 않는 항목. 기준 라운드에서 «평판 프리미티브가 CAD 메쉬보다 "
                  "n_eff_orders 가 컸다»(matrice4e +3.90, 24/24 방위). 상자에서도 프리미티브가 더 "
                  "풍부할 수 있다. 어느 쪽이든 그대로 적는다 — 상자가 더 풍부하면 «형상 정밀도가 "
                  "마이크로도플러를 더해 주지 않는다» 는 뜻이고, 그것은 교수 지적을 뒷받침한다."),
        test="부호를 예측하지 않는다. paired(box − mesh).n_eff_orders 의 frac_positive 를 그대로 기록",
        confidence="none (deliberately unpredicted)")
    P["items"]["P8_kernel_comfort_asymmetry"] = dict(
        claim_ko=("상자의 면은 어느 대역에서도 파장보다 훨씬 크므로 PO 유효 무릎 위에 있다. 진짜 "
                  "블레이드는 3.5 GHz 에서 무릎 아래다. 따라서 3.5 GHz 결과는 «상자에 유리한 판» 이고, "
                  "15.86 GHz 에서 두 대역의 방향이 일치해야 형상 효과라고 부를 수 있다."),
        test="hi_band 에서 paired 차이의 부호가 main 과 같은가",
        confidence="medium")
    return P


def write_prediction(force=False):
    os.makedirs(os.path.dirname(OUT_PRED), exist_ok=True)
    if os.path.exists(OUT_PRED) and not force:
        print(f"· 사전 예측 파일이 이미 있다 — 덮어쓰지 않는다: {os.path.relpath(OUT_PRED, ROOT)}")
        return OUT_PRED
    P = build_prediction()
    with open(OUT_PRED, "w") as f:
        json.dump(P, f, ensure_ascii=False, indent=1)
    print(f"✅ 사전 예측 기록: {os.path.relpath(OUT_PRED, ROOT)}  ({P['written_at']})")
    return OUT_PRED


def prediction_stamp():
    """예측 파일의 내용해시·수정시각. 결과 JSON 에 박아 «나중 수정» 을 잡을 수 있게 한다."""
    raw = open(OUT_PRED, "rb").read()
    return dict(path=os.path.relpath(OUT_PRED, ROOT),
                sha256=hashlib.sha256(raw).hexdigest(),
                bytes=len(raw),
                mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                    time.localtime(os.path.getmtime(OUT_PRED))),
                mtime_epoch=float(os.path.getmtime(OUT_PRED)))


# =========================================================================== #
#  점구름 만들기 — 팔마다 «어떤 프리미티브를 어디에 두는가» 만 다르다
# =========================================================================== #
def arm_cloud(key, arm, fc):
    """팔 하나의 (P, N, W, meta). 전부 PEC(|Γ|=1), 전부 회전체(정적 프레임 없음).

    ⭐ 회전은 «원점을 지나는 z 축»(기체 요축) 둘레다. 상자를 실제 놓인 자리(bbox 중심)에 두면
      중심이 축에서 벗어나 있어 홀수 차수가 생긴다 — 그것도 물리다. 축 위로 올린 판을 따로
      돌려서 «축이탈 흔들림» 과 «모서리 변조» 를 갈라 놓는다."""
    from drones import DRONES, build_drone
    from geom import box as geom_box, uv_sphere
    from rcs_po import mesh_to_points

    lam = B.C0 / fc
    fine = arm.endswith("_fine")
    base_arm = arm[:-5] if fine else arm
    div = 11.0 * (4.0 if fine else 1.0)          # 회전부 규약 λ/11 (기준 라운드와 동일)
    spac = lam / div

    g = geom_facts(key)
    ext = np.asarray(g["mesh_bbox_m"], float)
    ctr = np.asarray(g["mesh_bbox_center_m"], float)

    if base_arm == "box_bbox":
        dims, center = ext, ctr
        desc = "AABB of build_drone mesh, placed where the mesh actually sits"
    elif base_arm == "box_bbox_axis":
        dims, center = ext, np.array([0.0, 0.0, ctr[2]])
        desc = "same box, recentred onto the spin axis (isolates off-axis wobble)"
    elif base_arm == "box_aspect_voleq":
        dims = ext * g["box_aspect_voleq_scale"]
        center = np.array([0.0, 0.0, ctr[2]])
        desc = "same aspect ratio, volume matched to the mesh, on axis"
    elif base_arm == "cube_eqvol":
        s3 = g["cube_eqvol_side_m"]
        dims, center = np.array([s3, s3, s3]), np.array([0.0, 0.0, ctr[2]])
        desc = "equal-volume cube, on axis"
    elif base_arm == "sphere_eqvol":
        r = g["sphere_eqvol_radius_mm"] / 1000.0
        seg = int(math.ceil(2 * math.pi * r / spac)) | 1
        rings = max(3, int(math.ceil(math.pi * r / spac)))
        m = uv_sphere(r, seg=max(9, seg), rings=rings, group="sph")
        P, N, dA = mesh_to_points(m, spac)
        return P, N, dA, np.zeros(3), dict(kind="sphere_eqvol", radius_m=r, n_tris=len(m.f))
    else:
        raise ValueError(arm)

    m = geom_box(float(dims[0]), float(dims[1]), float(dims[2]),
                 center=(float(center[0]), float(center[1]), float(center[2])), group="box")
    P, N, dA = mesh_to_points(m, spac)
    meta = dict(kind="box", dims_m=[float(x) for x in dims],
                dims_mm=[float(1000 * x) for x in dims],
                center_m=[float(x) for x in center],
                center_offset_from_axis_mm=float(1000 * math.hypot(center[0], center[1])),
                volume_m3=float(dims[0] * dims[1] * dims[2]),
                volume_over_mesh=float(dims[0] * dims[1] * dims[2]) / g["mesh_volume_m3"],
                aspect_xy=float(max(dims[0], dims[1]) / min(dims[0], dims[1])),
                r_corner_m=0.5 * float(math.hypot(dims[0], dims[1])),
                requested_spacing_m=float(spac), requested_lambda_over=float(div),
                gamma_abs=1.0, material="PEC", n_tris=len(m.f), desc=desc)
    return P, N, dA, np.zeros(3), meta


def arm_cloud_props(key, fc, fine=False):
    """⭐ 부품 단위 경계상자 — 프로펠러만 «그 프롭의 경계상자» 로 바꾸고 **정적 프레임은 남긴다**.

    왜 이 팔이 필요한가: 기체 전체를 프리미티브 하나로 바꾸면 정적 동체가 사라져 0-도플러 항이
    통째로 없어진다. 그러면 dc_ac_db 의 큰 차이가 «형상» 때문인지 «정적부 상실» 때문인지 갈리지
    않는다. 이 팔은 정적부를 그대로 두므로 그 교란이 없다 — 기준 라운드의 slab·disc 팔과
    **같은 무대**에 선다.

    slab 과의 차이: slab 은 스팬·코드를 보존하고 두께를 «부피가 같아지도록» 풀었다. 여기 상자는
    프롭 메쉬의 축정렬 경계상자를 그대로 쓴다(허브 두께까지 포함) — 더 게으른 프리미티브다."""
    from drones import DRONES, build_frame, build_propeller, rotor_layout, drone_gamma_map
    from geom import box as geom_box
    from rcs_po import mesh_to_points

    s = DRONES[key]
    lam = B.C0 / fc
    bdiv, fdiv = (11.0 * (4.0 if fine else 1.0), 6.0 * (4.0 if fine else 1.0))
    spac = lam / bdiv
    gm = drone_gamma_map(s)

    Pf, Nf, dAf, wf = mesh_to_points(build_frame(s), lam / fdiv, gamma=gm)
    prop = build_propeller(s, n=26)
    V = np.asarray(prop.v, float)
    ext = V.max(0) - V.min(0)
    ctr = 0.5 * (V.max(0) + V.min(0))
    vol_prop = abs(mesh_volume(prop))
    m = geom_box(float(ext[0]), float(ext[1]), float(ext[2]),
                 center=(float(ctr[0]), float(ctr[1]), float(ctr[2])), group="prop")
    Pp, Np_, dAp, wp = mesh_to_points(m, spac, gamma=gm)
    #  반대회전 로터는 거울상(기준 라운드와 같은 규약: 점구름을 y-거울로 뒤집는다)
    Pm = Pp * np.array([1.0, -1.0, 1.0])
    Nm_ = Np_ * np.array([1.0, -1.0, 1.0])
    meta = dict(kind="prop_bbox", dims_mm=[float(1000 * x) for x in ext],
                center_mm=[float(1000 * x) for x in ctr],
                box_volume_m3=float(ext[0] * ext[1] * ext[2]),
                prop_mesh_volume_m3=vol_prop,
                box_volume_over_prop_mesh=float(ext[0] * ext[1] * ext[2]) / max(vol_prop, 1e-30),
                requested_spacing_m=float(spac), requested_lambda_over=float(bdiv),
                material="material-weighted like the real prop (group 'prop')",
                n_tris=len(m.f),
                desc=("propeller replaced by its own AABB; static airframe kept, "
                      "so the DC term has the same origin as the CAD-mesh arm"))
    return ((Pf, Nf, dAf * wf), (Pp, Np_, dAp * wp), (Pm, Nm_, dAp * wp),
            rotor_layout(s), meta)


def nn_spacing(P, n_probe=4000, seed=0):
    """점구름의 실측 최근접이웃 간격 중앙값 [m] — «요청한 간격» 이 아니라 실제 간격을 잰다."""
    from scipy.spatial import cKDTree
    P = np.asarray(P, float)
    if len(P) < 4:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(P), size=min(n_probe, len(P)), replace=False)
    d, _ = cKDTree(P).query(P[idx], k=2)
    return float(np.median(d[:, 1]))


# =========================================================================== #
#  계산 (GPU) — report16_base 의 커널을 그대로 부른다 (재구현 금지)
# =========================================================================== #
def compute(tag, fc, arms, with_s2=True):
    from gpu import pick                       # ⚠ torch 보다 먼저 (CUDA 컨텍스트 고정)
    picked = pick(verbose=True)
    import torch
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    from drones import DRONES
    lam = B.C0 / fc
    k_wav = 2.0 * math.pi / lam
    az_list = np.arange(B.N_AZ) * (360.0 / B.N_AZ)
    tables, meta = {}, dict(tag=tag, fc=fc, gpu=picked, az_deg=list(az_list), arms={})

    for key in KEYS:
        s = DRONES[key]
        proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
        plan = [(a, proto["n_phase"]) for a in arms]
        if with_s2:
            g = geom_facts(key)
            n_need = g[f"band_{tag}"]["n_phase_needed_for_box"]
            if n_need > proto["n_phase"]:
                plan.append((ARM_S2 + "_S%d" % n_need, n_need))
        for arm, n_ph in plan:
            t0 = time.time()
            base_arm = arm.split("_S")[0] if "_S" in arm else arm
            phis = np.linspace(0.0, 2 * math.pi, n_ph, endpoint=False)

            if base_arm.startswith("prop_bbox"):
                #  부품 단위 팔 — 정적 프레임 + 회전 상자 4벌 (기준 slab·disc 팔과 같은 무대)
                fr, rc, rcm, rotors, am = arm_cloud_props(
                    key, fc, fine=base_arm.endswith("_fine"))
                am = dict(am, n_pts=int(len(rc[2])), n_frame_pts=int(len(fr[2])),
                          actual_spacing_m=nn_spacing(rc[0]), n_phase=int(n_ph))
                am["lambda_over_actual"] = float(lam / max(am["actual_spacing_m"], 1e-12))
                for wf in ("spherical", "plane"):
                    T = np.zeros((len(az_list), n_ph), complex)
                    for ia, az in enumerate(az_list):
                        u, A, R_t = B.look_and_antenna(az, B.EL_DEG, B.RANGE_M)
                        Ef = B.field_static(torch, dev, fr[0], fr[1], fr[2], k_wav, A, R_t, wf)
                        tot = np.full(n_ph, Ef, complex)
                        for rot in rotors:
                            d = float(rot["dir"])
                            P, N, W = rc if d > 0 else rcm
                            tot += B.field_rotor(torch, dev, P, N, W, k_wav, A, R_t,
                                                 rot["center"],
                                                 math.radians(float(rot["base_ang"])), d, phis, wf)
                        T[ia] = tot
                    tables[f"{tag}|{key}|{arm}|{wf}"] = T
                am["seconds"] = float(time.time() - t0)
                meta["arms"][f"{key}|{arm}"] = am
                print(f"  [{tag}] {key:10s} {arm:22s} n_phase={n_ph:5d} "
                      f"pts={am['n_frame_pts']}+4x{am['n_pts']} [{am['seconds']:.1f}s]", flush=True)
                continue

            P, N, W, center, am = arm_cloud(key, base_arm, fc)
            am = dict(am, n_pts=int(len(W)), actual_spacing_m=nn_spacing(P), n_phase=int(n_ph))
            am["lambda_over_actual"] = float(lam / max(am["actual_spacing_m"], 1e-12))
            for wf in ("spherical", "plane"):
                T = np.zeros((len(az_list), n_ph), complex)
                for ia, az in enumerate(az_list):
                    u, A, R_t = B.look_and_antenna(az, B.EL_DEG, B.RANGE_M)
                    T[ia] = B.field_rotor(torch, dev, P, N, W, k_wav, A, R_t,
                                          center, 0.0, 1.0, phis, wf)
                tables[f"{tag}|{key}|{arm}|{wf}"] = T
            am["seconds"] = float(time.time() - t0)
            meta["arms"][f"{key}|{arm}"] = am
            print(f"  [{tag}] {key:10s} {arm:22s} n_phase={n_ph:5d} pts={len(W):8d} "
                  f"[{am['seconds']:.1f}s]", flush=True)

    os.makedirs(SCRATCH, exist_ok=True)
    np.savez_compressed(os.path.join(SCRATCH, f"rung_box_{tag}.npz"),
                        **{kk.replace("|", "__"): v for kk, v in tables.items()})
    with open(os.path.join(SCRATCH, f"rung_box_{tag}_meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False)
    return tables, meta


def load_local(tag):
    pz = os.path.join(SCRATCH, f"rung_box_{tag}.npz")
    mj = os.path.join(SCRATCH, f"rung_box_{tag}_meta.json")
    if not os.path.exists(pz):
        return {}, {}
    z = np.load(pz)
    return {kk.replace("__", "|"): z[kk] for kk in z.files}, json.load(open(mj))


def load_base_tables():
    """기준 라운드가 저장한 위상 표를 **그대로** 읽는다 — 기준 팔을 다시 계산하지 않는다.
    (다시 계산하면 «기준이 바뀐 것 아니냐» 는 반론이 생긴다. 같은 배열을 쓴다.)"""
    z = np.load(BASE_NPZ)
    out = {}
    for kk in z.files:
        parts = kk.split("__")
        if parts[0] == "hi":                     # hi__hi__G_0804__key__arm__wf
            out[("hi", parts[3], parts[4], parts[5])] = z[kk]
        else:                                    # main__G_0804__key__arm__wf
            if parts[1] == "G_0804":
                out[("main", parts[2], parts[3], parts[4])] = z[kk]
    return out


# =========================================================================== #
#  지표 — report16_base.md_metrics16 을 **그대로** 쓴다 (재구현 금지)
# =========================================================================== #
def arm_metrics(T, proto, nb, proto_own=None):
    per = [B.md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]
    out = dict(per_az={kk: B.summarize([m[kk] for m in per]) for kk in MET_KEYS},
               interpretable_frac=float(np.mean([m["metrics_interpretable"] for m in per])),
               band_order=int(per[0]["band_order"]), n_az=int(T.shape[0]),
               n_phase=int(T.shape[1]))
    if proto_own is not None:
        per2 = [B.md_metrics16(T[i], proto_own, nb) for i in range(T.shape[0])]
        out["own_band_gauge"] = dict(
            per_az={kk: B.summarize([m[kk] for m in per2]) for kk in
                    ("in_band_ac_frac", "in_band_ac_over_dc_db", "width_ratio",
                     "width_ratio_10db", "width_ratio_30db")},
            interpretable_frac=float(np.mean([m["metrics_interpretable"] for m in per2])),
            band_order=int(per2[0]["band_order"]),
            what_ko=("같은 지표 함수를 쓰되 β 와 f_tip 을 «상자 자신의 모서리» 기준으로 바꿔 넣었다. "
                     "표적 반경이 프롭 반경이라는 암묵적 가정을 걷어낸 판이다."))
    return out


def symmetry_block(T):
    """방위 주기 검사 — E(φ) 와 E(φ+Δ) 의 AC 상관. 1.0 이면 그 각도가 대칭 주기다."""
    S = T.shape[1]
    rows = {}
    for div, name in ((2, "shift_180deg"), (4, "shift_90deg"), (8, "shift_45deg")):
        if S % div:
            continue
        cs = [B.ac_corr(T[i], np.roll(T[i], S // div)) for i in range(T.shape[0])]
        rows[name] = B.summarize(cs)
    rows["what_ko"] = ("한 바퀴 표를 Δ 만큼 돌려서 자기 자신과 겹쳐 본다. shift_90deg 가 1 에 "
                       "가까우면 방위 90° 대칭(정사각 단면), shift_180deg 만 1 이면 180° 대칭 "
                       "(직사각 단면·2장 블레이드)이다.")
    return rows


def order_classes(T):
    """AC 전력을 차수 종류별로 가른다 — «주기» 를 스펙트럼 쪽에서 본 판.
    홀수 / 4의 배수가 아닌 짝수(≡2 mod 4) / 4의 배수."""
    S = T.shape[1]
    m_idx = np.fft.fftfreq(S, d=1.0 / S).astype(int)
    am = np.abs(m_idx)
    cls = dict(odd=(am % 2 == 1),
               even_not_mult4=((am % 2 == 0) & (am % 4 == 2)),
               mult4=((am != 0) & (am % 4 == 0)))
    rows = {}
    dom = []
    for i in range(T.shape[0]):
        c = np.fft.fft(T[i]) / S
        P = np.abs(c) ** 2
        tot = float(P[am != 0].sum())
        for nm, msk in cls.items():
            rows.setdefault(nm, []).append(float(P[msk].sum() / max(tot, 1e-300)))
        order_pow = np.zeros(S // 2 + 1)
        np.add.at(order_pow, am[am != 0], P[am != 0] / max(tot, 1e-300))
        dom.append(int(np.argmax(order_pow)))
    out = {nm: B.summarize(v) for nm, v in rows.items()}
    out["dominant_order"] = B.summarize(dom)
    out["dominant_order_mode"] = int(np.bincount(dom).argmax())
    out["what_ko"] = ("AC 전력의 차수 분포. 정육면체(90° 대칭)는 4의 배수에만 실리고, 직사각 "
                      "상자(180° 대칭)는 ≡2 mod 4 짝수가 살아난다. 축을 벗어나면 홀수가 생긴다.")
    return out


def sym_per_az(T, div):
    """방위마다 «표를 360/div 도 돌려 자기 자신과 겹친» AC 상관."""
    S = T.shape[1]
    return np.array([B.ac_corr(T[i], np.roll(T[i], S // div)) for i in range(T.shape[0])], float)


def _diff_row(d):
    d = np.asarray(d, float)
    d = d[np.isfinite(d)]
    sd = float(d.std(ddof=1)) if d.size > 1 else 0.0
    return dict(mean=float(d.mean()), sd=sd, sem=float(sd / max(math.sqrt(d.size), 1.0)),
                frac_positive=float(np.mean(d > 0)), n=int(d.size),
                min=float(d.min()), max=float(d.max()))


def paired(Ta, Tb, proto, nb, keys):
    """같은 방위에서 두 팔의 지표를 뺀다(B − A). 자세 산포는 공통분이라 사라진다."""
    ma = [B.md_metrics16(Ta[i], proto, nb) for i in range(Ta.shape[0])]
    mb = [B.md_metrics16(Tb[i], proto, nb) for i in range(Tb.shape[0])]
    n = min(len(ma), len(mb))
    row = {}
    for kk in keys:
        if kk.startswith("sym_corr_"):
            continue
        row[kk] = _diff_row([mb[i][kk] - ma[i][kk] for i in range(n)])
    # ⭐ 방위 주기 상관 — md_metrics16 밖의 양이라 여기서 계산해 같은 방식으로 짝지어 뺀다.
    for kk, div in (("sym_corr_90deg", 4), ("sym_corr_180deg", 2)):
        if Ta.shape[1] % div or Tb.shape[1] % div:
            continue
        row[kk] = _diff_row(sym_per_az(Tb, div)[:n] - sym_per_az(Ta, div)[:n])
    return row


# =========================================================================== #
#  분석
# =========================================================================== #
PAIR_KEYS = ("flash_contrast_db", "n_eff_orders", "dc_ac_db", "in_band_ac_over_dc_db",
             "width_ratio", "blade_comb_frac", "sigma_eq_mean_dbsm",
             "sym_corr_90deg", "sym_corr_180deg")


def analyse(tabs, metas, base_tabs, J):
    from drones import DRONES
    J["geometry"] = {k: geom_facts(k) for k in KEYS}
    J["arms"] = {}
    J["reference_arms"] = {}
    J["symmetry"] = {}
    J["order_classes"] = {}
    J["paired_vs_reference"] = {}
    J["sampling_adequacy"] = {}
    J["point_density_control"] = {}
    J["wavefront_control"] = {}

    for tag, fc in (("main", B.FC_MAIN), ("hi", B.FC_PO_KNEE)):
        if tag not in tabs:
            continue
        T_all, M_all = tabs[tag], metas[tag]
        for key in KEYS:
            s = DRONES[key]
            nb = int(s.prop_blades)
            proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
            g = J["geometry"][key][f"band_{tag}"]
            proto_own = dict(proto, beta=g["beta_box_corner"], f_tip_hz=g["f_corner_box_hz"])

            # ── 새 팔 (상자 계열) ──────────────────────────────────────────
            for kk in sorted([x for x in T_all if x.startswith(f"{tag}|{key}|")]):
                _, _, arm, wf = kk.split("|")
                slot = J["arms"].setdefault(f"{tag}|{key}|{arm}", {})
                slot[wf] = arm_metrics(T_all[kk], proto, nb,
                                       proto_own=proto_own if wf == "spherical" else None)
                if wf == "spherical":
                    slot["geometry"] = M_all["arms"].get(f"{key}|{arm}", {})
                    J["symmetry"][f"{tag}|{key}|{arm}"] = symmetry_block(T_all[kk])
                    J["order_classes"][f"{tag}|{key}|{arm}"] = order_classes(T_all[kk])

            # ── 기준 팔 (기준 라운드 표를 그대로) ─────────────────────────
            for arm in ("mesh", "slab", "disc", "sphere"):
                Tb = base_tabs.get((tag, key, arm, "spherical"))
                if Tb is None:
                    continue
                J["reference_arms"][f"{tag}|{key}|{arm}"] = arm_metrics(Tb, proto, nb)
                J["symmetry"][f"{tag}|{key}|{arm}"] = symmetry_block(Tb)
                J["order_classes"][f"{tag}|{key}|{arm}"] = order_classes(Tb)

            # ── 짝지은 비교 ───────────────────────────────────────────────
            box = T_all.get(f"{tag}|{key}|box_bbox|spherical")
            boxa = T_all.get(f"{tag}|{key}|box_bbox_axis|spherical")
            cube = T_all.get(f"{tag}|{key}|cube_eqvol|spherical")
            voleq = T_all.get(f"{tag}|{key}|box_aspect_voleq|spherical")
            pbox = T_all.get(f"{tag}|{key}|prop_bbox|spherical")
            for nm, Ta, Tb in (
                    ("box_bbox - mesh", base_tabs.get((tag, key, "mesh", "spherical")), box),
                    ("box_bbox - slab", base_tabs.get((tag, key, "slab", "spherical")), box),
                    ("box_bbox - sphere", base_tabs.get((tag, key, "sphere", "spherical")), box),
                    ("box_bbox - cube_eqvol", cube, box),
                    ("box_bbox_axis - box_bbox", box, boxa),
                    ("box_bbox_axis - mesh", base_tabs.get((tag, key, "mesh", "spherical")), boxa),
                    ("cube_eqvol - mesh", base_tabs.get((tag, key, "mesh", "spherical")), cube),
                    #  ⭐ 사다리 «윗단» 대조 — 프롭만 프리미티브로 바꾼 판(정적 프레임 유지).
                    #     전신 프리미티브(상자·구)가 못 내는 것을 이미 내고 있는지 확인한다.
                    ("slab - mesh", base_tabs.get((tag, key, "mesh", "spherical")),
                     base_tabs.get((tag, key, "slab", "spherical"))),
                    ("disc - mesh", base_tabs.get((tag, key, "mesh", "spherical")),
                     base_tabs.get((tag, key, "disc", "spherical"))),
                    ("sphere - mesh", base_tabs.get((tag, key, "mesh", "spherical")),
                     base_tabs.get((tag, key, "sphere", "spherical"))),
                    #  ⭐ 정적부를 남긴 부품 단위 상자 — «정적부 상실» 교란 없이 상자성을 잰다
                    ("prop_bbox - mesh", base_tabs.get((tag, key, "mesh", "spherical")), pbox),
                    ("prop_bbox - slab", base_tabs.get((tag, key, "slab", "spherical")), pbox),
                    # ⭐ 크기를 맞춘 판 — «경계상자는 부피가 부풀려져서 이긴 것 아니냐» 를 차단한다
                    ("box_aspect_voleq - mesh", base_tabs.get((tag, key, "mesh", "spherical")), voleq),
                    ("box_aspect_voleq - slab", base_tabs.get((tag, key, "slab", "spherical")), voleq),
                    # ⭐⭐ 과제문 예측의 가장 깨끗한 검사 — 둘 다 축 위, 둘 다 부피 등가.
                    #     남은 차이는 **종횡비 하나뿐**이다.
                    ("box_aspect_voleq - cube_eqvol", cube, voleq),
                    ("box_bbox_axis - cube_eqvol", cube, boxa)):
                if Ta is None or Tb is None or Ta.shape != Tb.shape:
                    continue
                J["paired_vs_reference"][f"{tag}|{key}|{nm}"] = paired(Ta, Tb, proto, nb, PAIR_KEYS)

            # ── 위상격자 적정성 ───────────────────────────────────────────
            s2 = [x for x in T_all if x.startswith(f"{tag}|{key}|box_bbox_S") and
                  x.endswith("|spherical")]
            if s2 and box is not None:
                T2 = T_all[s2[0]]
                a = arm_metrics(box, proto, nb)["per_az"]
                b = arm_metrics(T2, proto, nb)["per_az"]
                J["sampling_adequacy"][f"{tag}|{key}"] = dict(
                    n_phase_protocol=int(box.shape[1]), n_phase_box_adequate=int(T2.shape[1]),
                    beta_prop=g["beta_prop"], beta_box_corner=g["beta_box_corner"],
                    nyquist_margin_protocol_grid_vs_box=g["nyquist_margin_protocol_grid_vs_box"],
                    delta={kk: b[kk]["mean"] - a[kk]["mean"] for kk in
                           ("flash_contrast_db", "n_eff_orders", "width_ratio", "dc_ac_db",
                            "sigma_eq_mean_dbsm", "blade_comb_frac")},
                    what_ko=("상자는 모서리가 프롭 팁보다 바깥이라 자기 β 가 더 크다. 규약 격자(프롭 "
                             "β 로 정한 S)가 상자에도 충분한지, S 를 상자 β 에 맞춰 키워 비교한다. "
                             "차이가 «재려는 팔 사이 차이» 보다 훨씬 작아야 규약을 그대로 쓸 수 있다."))

            # ── 점밀도 반론 차단 ──────────────────────────────────────────
            fineT = T_all.get(f"{tag}|{key}|box_bbox_fine|spherical")
            if fineT is not None and box is not None:
                a = arm_metrics(box, proto, nb)["per_az"]
                b = arm_metrics(fineT, proto, nb)["per_az"]
                J["point_density_control"][f"{tag}|{key}"] = dict(
                    pts_coarse=M_all["arms"][f"{key}|box_bbox"]["n_pts"],
                    pts_fine=M_all["arms"][f"{key}|box_bbox_fine"]["n_pts"],
                    spacing_coarse_m=M_all["arms"][f"{key}|box_bbox"]["actual_spacing_m"],
                    spacing_fine_m=M_all["arms"][f"{key}|box_bbox_fine"]["actual_spacing_m"],
                    delta={kk: b[kk]["mean"] - a[kk]["mean"] for kk in
                           ("flash_contrast_db", "n_eff_orders", "width_ratio", "dc_ac_db",
                            "sigma_eq_mean_dbsm", "in_band_ac_over_dc_db")},
                    what_ko="점구름을 4배 촘촘히 깔아도 지표가 안 움직이면 밀도는 원인이 아니다.")

            # ── 파면 대조 ─────────────────────────────────────────────────
            for arm in ("box_bbox", "box_bbox_axis", "cube_eqvol"):
                ka = f"{tag}|{key}|{arm}|spherical"
                kb = f"{tag}|{key}|{arm}|plane"
                if ka in T_all and kb in T_all:
                    Ta, Tb = T_all[ka], T_all[kb]
                    J["wavefront_control"][f"{tag}|{key}|{arm}"] = dict(
                        ac_corr=B.summarize([B.ac_corr(Ta[i], Tb[i]) for i in range(Ta.shape[0])]),
                        level_delta_db=B.summarize([
                            10 * np.log10(np.mean(np.abs(Tb[i]) ** 2) /
                                          np.mean(np.abs(Ta[i]) ** 2)) for i in range(Ta.shape[0])]))
    J["wavefront_control"]["note_ko"] = (
        "구면파(헤드라인) 대 평면파(무한거리 등가). 상관이 1 에 가까우면 10 m 는 이 표적에게 "
        "사실상 원거리장이라는 뜻이다.")
    J["null_was_actually_spun"] = null_spin_check(base_tabs)
    J["discriminability"] = discriminability(J)
    return J


def null_spin_check(base_tabs):
    """⭐ «구를 안 돌리고 0 을 얻으면 동어반복» — 그래서 널 팔이 **실제로 돌았는지** 확인한다.

    기준 라운드의 sphere·disc 팔은 같은 위상격자로 field_rotor 를 통과했다. 돌지 않았다면
    E(φ) 가 **비트 단위로 상수**여야 한다. 상수가 아니라 «수치바닥 수준으로 작다» 는 것이
    돌렸는데도 변조가 안 나온다는 증거다."""
    out = {}
    for key in KEYS:
        for arm in ("sphere", "disc"):
            T = base_tabs.get(("main", key, arm, "spherical"))
            if T is None:
                continue
            ac = np.abs(T - T.mean(axis=1, keepdims=True))
            out[f"{key}|{arm}"] = dict(
                exactly_constant=bool(np.all(ac == 0.0)),
                peak_ac_over_dc=float(np.max(ac) / max(np.mean(np.abs(T)), 1e-300)),
                peak_ac_over_dc_db=float(20 * np.log10(max(np.max(ac), 1e-300) /
                                                       max(np.mean(np.abs(T)), 1e-300))),
                n_phase=int(T.shape[1]))
    out["what_ko"] = (
        "널 팔(등가부피 구·회전대칭 원판)은 **실제로 돌렸다**. exactly_constant 가 false 라는 것은 "
        "위상마다 값이 다르게 계산됐다는 뜻이고 — 즉 «안 돌려서 0» 이 아니다. 그런데도 남는 "
        "변조가 peak_ac_over_dc_db 만큼(수치바닥 수준)이라는 것이 «회전대칭체는 돌려도 변조가 "
        "없다» 의 실측 증거다. 이 잔차의 출처는 물리가 아니라 점구름을 각도로 잘라 놓은 격자다 "
        "— 그래서 대역 안(|m| ≤ 1.5β)에서 재면 더 내려간다(in_band_ac_over_dc_db 참조).")
    return out


def discriminability(J):
    """⭐ 이 단의 실용적 산출물: **어떤 지표가 «돌아가는 상자» 와 «진짜 블레이드» 를 가르는가.**

    판정 잣대는 «짝지은 평균차 ÷ 진짜 메쉬의 자세 산포» 다. 1 보다 훨씬 크면 자세를 바꿔도
    안 겹친다(가른다), 1 보다 작으면 자세 하나 바꾸는 것과 같은 급이다(못 가른다)."""
    out = {}
    for key in KEYS:
        me = J["reference_arms"].get(f"main|{key}|mesh", {}).get("per_az")
        if not me:
            continue
        #  주기 상관은 md_metrics16 밖의 양이라 메쉬의 자세 산포를 symmetry 블록에서 가져온다
        sym_sd = {"sym_corr_90deg": J["symmetry"].get(f"main|{key}|mesh", {})
                  .get("shift_90deg", {}).get("sd"),
                  "sym_corr_180deg": J["symmetry"].get(f"main|{key}|mesh", {})
                  .get("shift_180deg", {}).get("sd")}
        row = {}
        for surro in ("prop_bbox", "box_bbox", "box_bbox_axis", "box_aspect_voleq",
                      "cube_eqvol", "slab", "sphere"):
            p = J["paired_vs_reference"].get(f"main|{key}|{surro} - mesh")
            if not p:
                continue
            r = {}
            for kk in PAIR_KEYS:
                if kk not in p:
                    continue
                sd = sym_sd[kk] if kk in sym_sd else me[kk]["sd"]
                r[kk] = dict(paired_mean=p[kk]["mean"], mesh_pose_sd=sd,
                             separation_in_pose_sd=(p[kk]["mean"] / sd) if (sd or 0) > 0 else None,
                             frac_positive=p[kk]["frac_positive"])
            row[surro] = r
        out[key] = row
    out["what_ko"] = (
        "«대체모델 − 진짜 메쉬» 의 짝지은 평균차를 **진짜 메쉬의 자세 산포(sd)** 로 나눈 값. "
        "|값| ≫ 1 이면 그 지표는 상자와 블레이드를 가른다. |값| ≲ 1 이면 «자세를 하나 바꾼 것» "
        "과 구별이 안 되므로 그 지표로는 못 가른다.")
    out["caveat_ko"] = (
        "⚠ dc_ac_db 는 이 잣대에서 가장 크게 나오지만 그것은 형상 때문이 아니다 — 기체 전체를 "
        "프리미티브 하나로 바꾸면 **정적 동체가 사라져** 0-도플러 항이 통째로 없어진다. 구·큐브· "
        "상자 어느 것으로 바꿔도 같은 일이 생긴다. 형상 충실도의 증거로 인용하면 안 된다.")
    out["caveat_blade_comb_ko"] = (
        "⚠⚠ blade_comb_frac 의 분리도가 수백 배로 찍히는 것은 **분모가 거의 0** 이기 때문이다"
        "(진짜 메쉬의 blade_comb 는 자세를 바꿔도 1.000 에서 꿈쩍 않는다). 게다가 그 «분리» 는 "
        "형상이 아니라 **상자를 회전축 밖에 놓은 것** 때문이다 — 축 위에 올린 box_bbox_axis 는 "
        "blade_comb 가 다시 메쉬와 같아진다. 즉 이 지표는 «축이탈» 은 잡아도 «형상» 은 못 잡는다.")
    out["caveat_sigma_ko"] = (
        "⚠ sigma_eq_mean_dbsm 은 프리미티브가 PEC(|Γ|=1) 이고 메쉬는 재질가중을 쓰므로 재질 "
        "차이가 섞여 있다. 형상 판정에서 제외한다(material_invariance 블록 참조).")
    out["identity_sym180_equals_blade_comb_ko"] = (
        "⚠ 블레이드가 2장일 때 sym_corr_180deg 와 blade_comb_frac 은 **같은 양**이다. 표를 180° "
        "돌리면 차수 m 의 계수에 (−1)^m 이 곱해지므로 상관은 |짝수몫 − 홀수몫| = |2·짝수몫 − 1| 이 "
        "되고, 2장 블레이드의 빗은 곧 짝수 차수다. 즉 sym_corr_180deg = 2·blade_comb_frac − 1 "
        "(짝수 우세일 때). 분리도가 둘이 똑같이 나오는 것은 우연이 아니라 항등식이다 — "
        "두 지표를 독립 증거로 세면 안 된다. 실제로 새로운 축은 sym_corr_90deg 뿐이다.")
    out["what_sym90_actually_measures_ko"] = (
        "⭐ sym_corr_90deg 는 표를 90° 돌려 자기 자신과 겹친 상관이다 — 즉 «회전 산란체가 4중 "
        "대칭에 가까운가» 를 잰다. 진짜 표적의 회전부는 2장 블레이드(2중 대칭)라 낮고, 단면이 "
        "거의 정사각인 상자는 높다. ⚠ 이것을 «CAD 정밀도가 필요하다» 의 증거로 바로 쓰면 안 된다 "
        "— 그러려면 사다리 윗단인 slab(프롭을 평판 2장으로 바꾼 판, 형상 디테일 0)이 이 축에서 "
        "메쉬와 **안 갈라져야** 한다. slab 행이 이 표에 같이 들어 있으니 거기서 직접 확인할 것. "
        "slab 도 갈라진다면 그 축은 «전신 프리미티브 대 회전날개» 를 가르는 것이지 «CAD 대 "
        "프리미티브» 를 가르는 것이 아니다.")
    out["null_rows_ko"] = (
        "⚠ sphere 행의 분리도가 수백으로 찍히는 것은 널 팔의 AC 가 수치바닥이라 지표가 «잡음의 "
        "모양» 을 재고 있기 때문이다 — reference_arms 의 sphere.in_band_ac_frac 이 판정 문턱 0.5 "
        "아래라 애초에 «해석 금지» 로 찍힌 팔이다. 널 행은 «지표의 0점» 을 보여 주려고 넣은 "
        "것이지 대체모델 후보가 아니다.")
    return out


def base_reproduction_gate(J):
    """⭐ 기준 라운드 표를 제대로 읽었는지 검사한다.
    같은 배열 · 같은 지표 함수이므로 report16_base.json 의 값과 **비트 수준으로** 같아야 한다.
    여기서 어긋나면 아래 대조는 전부 무효다."""
    base = json.load(open(BASE_JSON))
    rows, worst = {}, 0.0
    for key in KEYS:
        for arm in ("mesh", "slab", "disc", "sphere"):
            got = J["reference_arms"].get(f"main|{key}|{arm}")
            exp = base.get("arms", {}).get(key, {}).get(arm, {}).get("spherical", {}).get("per_az")
            if not got or not exp:
                continue
            d = {kk: abs(got["per_az"][kk]["mean"] - exp[kk]["mean"])
                 for kk in ("flash_contrast_db", "n_eff_orders", "width_ratio", "dc_ac_db")
                 if kk in exp}
            rows[f"{key}|{arm}"] = max(d.values()) if d else None
            worst = max(worst, max(d.values()) if d else 0.0)
    return dict(max_abs_diff_vs_report16_base_json=worst, per_arm=rows, tolerance=1e-9,
                verdict="PASS" if worst < 1e-9 else "FAIL",
                what_ko=("기준 라운드가 저장한 위상 표를 그대로 읽어 같은 지표 함수에 넣었으므로 "
                         "report16_base.json 의 값과 완전히 같아야 한다. 대조의 «기준선» 이 "
                         "흔들리지 않았음을 보이는 자리다."),
                base_npz=dict(path=os.path.relpath(BASE_NPZ, ROOT),
                              sha256=hashlib.sha256(open(BASE_NPZ, "rb").read()).hexdigest()[:16],
                              mtime=time.strftime("%Y-%m-%d %H:%M",
                                                  time.localtime(os.path.getmtime(BASE_NPZ)))))


def material_invariance(tabs):
    """균질 프리미티브의 |Γ| 는 복소장에 상수 하나를 곱할 뿐 — 변조 지표는 전부 불변임을 실증.
    (프리미티브를 PEC 로 두고 메쉬는 재질가중을 쓰는 것이 불공정하지 않다는 근거)"""
    from drones import DRONES
    key = KEYS[-1]
    T = tabs["main"].get(f"main|{key}|box_bbox|spherical")
    if T is None:
        return dict(absent=True)
    s = DRONES[key]
    proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_MAIN)
    from materials import gamma_po
    from drones import DRONE_GROUP_MAT
    gam = float(gamma_po(DRONE_GROUP_MAT["body"][0], B.FC_MAIN))
    a = B.md_metrics16(T[0], proto, s.prop_blades)
    b = B.md_metrics16(T[0] * gam, proto, s.prop_blades)
    return dict(drone=key, gamma_applied=gam,
                gamma_source="materials.gamma_po(DRONE_GROUP_MAT['body']) @ 3.5 GHz",
                delta={kk: b[kk] - a[kk] for kk in
                       ("flash_contrast_db", "n_eff_orders", "width_ratio", "dc_ac_db",
                        "blade_comb_frac", "in_band_ac_frac")},
                delta_sigma_db=b["sigma_eq_mean_dbsm"] - a["sigma_eq_mean_dbsm"],
                expected_sigma_shift_db=float(20 * math.log10(gam)),
                what_ko=("균질체에 |Γ| 를 곱하면 복소장 전체가 같은 배율로 커지거나 작아질 뿐이다. "
                         "그래서 변조 지표(플래시·풍부도·폭·DC/AC 비)는 **정확히 0** 만큼 움직이고 "
                         "σ 만 20log10|Γ| 만큼 이동한다. 프리미티브를 PEC 로 둔 것이 지표 비교를 "
                         "왜곡하지 않는다는 뜻이다."))


# =========================================================================== #
#  사전 예측 채점
# =========================================================================== #
def score_predictions(J):
    P = json.load(open(OUT_PRED))
    S = {}

    def A(tag, key, arm, what, gauge="per_az"):
        d = J["arms"].get(f"{tag}|{key}|{arm}", {}).get("spherical")
        if not d:
            return None
        return d[gauge][what]["mean"] if gauge == "per_az" else d["own_band_gauge"]["per_az"][what]["mean"]

    def Rf(tag, key, arm, what):
        d = J["reference_arms"].get(f"{tag}|{key}|{arm}")
        return d["per_az"][what]["mean"] if d else None

    # P1 — 상자는 널이 아니다
    r = {}
    for key in KEYS:
        b = A("main", key, "box_bbox", "in_band_ac_over_dc_db")
        sp = Rf("main", key, "sphere", "in_band_ac_over_dc_db")
        if b is None or sp is None:
            continue
        r[key] = dict(box_db=b, sphere_null_db=sp, margin_db=b - sp,
                      pass_=bool(b - sp > P["items"]["P1_box_is_not_a_null"]["threshold_db"]))
    S["P1_box_is_not_a_null"] = dict(values=r,
                                     verdict="CONFIRMED" if r and all(v["pass_"] for v in r.values())
                                     else ("REFUTED" if r else "NO DATA"))

    # P2 — 주기 90° vs 180°
    thr = P["items"]["P2_period_180_not_90"]["threshold"]
    r = {}
    for key in KEYS:
        c90 = J["symmetry"].get(f"main|{key}|cube_eqvol", {}).get("shift_90deg", {}).get("mean")
        b90 = J["symmetry"].get(f"main|{key}|box_bbox_axis", {}).get("shift_90deg", {}).get("mean")
        b180 = J["symmetry"].get(f"main|{key}|box_bbox_axis", {}).get("shift_180deg", {}).get("mean")
        oc_c = J["order_classes"].get(f"main|{key}|cube_eqvol", {})
        oc_b = J["order_classes"].get(f"main|{key}|box_bbox_axis", {})
        if None in (c90, b90, b180):
            continue
        r[key] = dict(cube_sym90=c90, box_sym90=b90, box_sym180=b180,
                      cube_even_not_mult4_frac=oc_c.get("even_not_mult4", {}).get("mean"),
                      box_even_not_mult4_frac=oc_b.get("even_not_mult4", {}).get("mean"),
                      cube_dominant_order=oc_c.get("dominant_order_mode"),
                      box_dominant_order=oc_b.get("dominant_order_mode"),
                      pass_=bool(c90 >= thr["cube_sym90_min"] and b90 <= thr["box_sym90_max"]
                                 and b180 >= thr["box_sym180_min"]))
    S["P2_period_180_not_90"] = dict(values=r,
                                     verdict="CONFIRMED" if r and all(v["pass_"] for v in r.values())
                                     else ("REFUTED" if r else "NO DATA"))

    # P2b — 축이탈 → 홀수 차수
    r = {}
    for key in KEYS:
        o1 = J["order_classes"].get(f"main|{key}|box_bbox", {}).get("odd", {}).get("mean")
        o2 = J["order_classes"].get(f"main|{key}|box_bbox_axis", {}).get("odd", {}).get("mean")
        if o1 is None or o2 is None:
            continue
        r[key] = dict(odd_frac_offaxis=o1, odd_frac_onaxis=o2,
                      offset_mm=J["geometry"][key]["mesh_bbox_center_offset_from_spin_axis_mm"],
                      pass_=bool(o1 > o2 and o2 < 0.01))
    S["P2b_offaxis_gives_odd_orders"] = dict(
        values=r, verdict="CONFIRMED" if r and all(v["pass_"] for v in r.values())
        else ("REFUTED" if r else "NO DATA"))

    # P3 — 폭이 프롭 팁을 넘는다
    r = {}
    for key in KEYS:
        w = A("main", key, "box_bbox", "width_ratio")
        up = J["geometry"][key]["r_corner_over_prop_radius"]
        q = 1.0 / J["geometry"][key]["band_main"]["beta_prop"]        # 최소 눈금(1차수)
        if w is None:
            continue
        r[key] = dict(width_ratio_vs_prop_tip=w, geometric_upper_bound=up,
                      order_quantum=q, pass_=bool(w > 1.0 and w <= up + 2 * q))
    S["P3_width_exceeds_prop_tip"] = dict(
        values=r, verdict="CONFIRMED" if r and all(v["pass_"] for v in r.values())
        else ("REFUTED" if r else "NO DATA"))

    # P4 — 판정기가 상자를 오판한다
    r = {}
    for key in KEYS:
        d = J["arms"].get(f"main|{key}|box_bbox", {}).get("spherical", {})
        if not d or "own_band_gauge" not in d:
            continue
        f1 = d["per_az"]["in_band_ac_frac"]["mean"]
        f2 = d["own_band_gauge"]["per_az"]["in_band_ac_frac"]["mean"]
        r[key] = dict(in_band_protocol_gauge=f1, in_band_own_gauge=f2,
                      interpretable_frac_protocol=d["interpretable_frac"],
                      interpretable_frac_own=d["own_band_gauge"]["interpretable_frac"],
                      pass_=bool(f1 < 0.5 and f2 > 0.9))
    S["P4_in_band_gate_will_misjudge_the_box"] = dict(
        values=r, verdict="CONFIRMED" if r and all(v["pass_"] for v in r.values())
        else ("REFUTED" if r else "NO DATA"))

    # P5 — 플래시가 메쉬보다 작지 않다
    r = {}
    for key in KEYS:
        p = J["paired_vs_reference"].get(f"main|{key}|box_bbox - mesh")
        if not p:
            continue
        r[key] = dict(paired_flash_delta=p["flash_contrast_db"],
                      pass_=bool(p["flash_contrast_db"]["mean"] >= 0.0))
    S["P5_flash_not_smaller_than_mesh"] = dict(
        values=r, verdict="CONFIRMED" if r and all(v["pass_"] for v in r.values())
        else ("REFUTED" if r else "NO DATA"))

    # P6 — 블레이드 빗이 구별을 못한다
    r = {}
    for key in KEYS:
        bc = A("main", key, "box_bbox_axis", "blade_comb_frac")
        bo = A("main", key, "box_bbox", "blade_comb_frac")
        me = Rf("main", key, "mesh", "blade_comb_frac")
        if None in (bc, bo, me):
            continue
        r[key] = dict(box_axis=bc, box_offaxis=bo, mesh=me,
                      pass_=bool(bc > 0.9 and abs(bc - me) < 0.2))
    S["P6_blade_comb_cannot_tell_them_apart"] = dict(
        values=r, verdict="CONFIRMED" if r and all(v["pass_"] for v in r.values())
        else ("REFUTED" if r else "NO DATA"))

    # P7 — 방향을 예측하지 않은 항목 (기록만)
    r = {}
    for key in KEYS:
        p = J["paired_vs_reference"].get(f"main|{key}|box_bbox - mesh")
        ph = J["paired_vs_reference"].get(f"hi|{key}|box_bbox - mesh")
        if not p:
            continue
        r[key] = dict(n_eff_orders_main=p["n_eff_orders"],
                      n_eff_orders_hi=(ph or {}).get("n_eff_orders"))
    S["P7_direction_of_richness_unknown"] = dict(values=r, verdict="RECORDED (no prediction made)")

    # P8 — 두 대역의 방향 일치
    r = {}
    for key in KEYS:
        a = J["paired_vs_reference"].get(f"main|{key}|box_bbox - mesh")
        b = J["paired_vs_reference"].get(f"hi|{key}|box_bbox - mesh")
        if not a or not b:
            continue
        common = [kk for kk in PAIR_KEYS if kk in a and kk in b]
        agree = {kk: bool(np.sign(a[kk]["mean"]) == np.sign(b[kk]["mean"])) for kk in common}
        r[key] = dict(main={kk: a[kk]["mean"] for kk in common},
                      hi={kk: b[kk]["mean"] for kk in common},
                      sign_agreement=agree,
                      n_agree=int(sum(agree.values())), n_total=len(agree))
    S["P8_kernel_comfort_asymmetry"] = dict(
        values=r, verdict="RECORDED",
        note_ko=("부호가 두 대역에서 같은 지표만 «형상 효과» 라고 부를 수 있다. "
                 "3.5 GHz 는 상자에 유리한 판이므로(상자만 PO 무릎 위) 이 검사가 필요하다."))

    S["_how_to_read_ko"] = (
        "verdict 는 예측 파일에 **미리 적힌 문턱**으로만 판정한다. REFUTED 가 나오면 그대로 둔다 — "
        "예측이 틀린 것이 결과다. 문턱을 결과에 맞춰 고치면 사전등록의 의미가 사라진다.")

    # ── ⚠ 사후 해설 (POST-HOC) — 판정을 바꾸지 않는다. 왜 틀렸는지만 적는다 ───────
    ph = dict(_warning_ko=("⚠⚠ 이 블록은 결과를 보고 쓴 **사후** 해설이다. 위의 verdict 는 "
                           "하나도 바꾸지 않았다. 사후 해설을 근거로 삼지 말 것."))
    p2 = S["P2_period_180_not_90"]["values"]
    if p2:
        ph["P2"] = dict(
            verdict_stands="REFUTED",
            what_was_right_ko=("방향은 맞았다 — 정육면체는 90° 대칭이 완벽하고(sym90 "
                               f"{min(v['cube_sym90'] for v in p2.values()):.4f} 이상), "
                               "4의 배수가 아닌 짝수 차수에 실린 몫이 사실상 0 이다"
                               f"({max(v['cube_even_not_mult4_frac'] for v in p2.values()):.1e}). "
                               "경계상자는 그 몫이 살아난다"
                               f"({min(v['box_even_not_mult4_frac'] for v in p2.values()):.3f}~"
                               f"{max(v['box_even_not_mult4_frac'] for v in p2.values()):.3f}) "
                               "— 즉 90° 대칭이 실제로 깨졌다."),
            what_was_wrong_ko=("문턱을 잘못 잡았다. «상자의 sym90 이 0.5 아래로 떨어진다» 고 적었는데 "
                               f"실제는 {min(v['box_sym90'] for v in p2.values()):.3f}~"
                               f"{max(v['box_sym90'] for v in p2.values()):.3f} 였다. 종횡비가 "
                               f"{min(J['geometry'][k]['aspect_xy'] for k in KEYS):.2f}~"
                               f"{max(J['geometry'][k]['aspect_xy'] for k in KEYS):.2f} 밖에 "
                               "안 돼서 90° 돌린 자기 자신과 여전히 꽤 닮았다. "
                               "또 «dominant_order 가 4 에서 2 로 내려간다» 도 틀렸다 — 실제 "
                               f"{ {k: v['box_dominant_order'] for k, v in p2.items()} } 였다. "
                               "상자가 크면 스펙트럼 첨두는 낮은 차수가 아니라 β 근처 고차에 선다."),
            lesson_ko=("«주기가 다르다» 는 이분법이 아니라 **정도의 문제**였다. 종횡비가 1 에서 "
                       "멀어질수록 90° 대칭이 연속적으로 무너진다."))
    p4 = S["P4_in_band_gate_will_misjudge_the_box"]["values"]
    if p4:
        ph["P4"] = dict(
            verdict_stands="REFUTED",
            what_was_wrong_ko=("판정기가 상자를 «해석 불가» 로 찍을 것이라고 적었는데, 실제 "
                               f"in_band_ac_frac 은 "
                               f"{min(v['in_band_protocol_gauge'] for v in p4.values()):.3f}~"
                               f"{max(v['in_band_protocol_gauge'] for v in p4.values()):.3f} 로 "
                               "문턱 0.5 위였다 — 판정기는 상자를 통과시킨다. 대역을 1.5β 로 "
                               "**넉넉히** 잡아 둔 덕이다."),
            what_survives_ko=("그래도 AC 전력의 20~27 % 는 프롭 기준 대역 밖에 있고, 상자 자신의 "
                              "β 로 재면 1.0000 으로 회복된다. 즉 판정기(통과/불통과)는 살아남지만 "
                              "**width_ratio 는 여전히 틀린 잣대로 재고 있다** — 분모가 프롭 팁 "
                              "속도로 고정돼 있기 때문이다. 대체표적을 넣을 때는 그 표적의 "
                              "회전반경으로 f_tip 을 다시 잡아야 한다."))
    S["_posthoc_reading_of_refutations"] = ph
    S["_prediction_file"] = prediction_stamp()
    return S


# =========================================================================== #
#  그림 (그림 안 글씨는 전부 영어 — 저장소 규약)
# =========================================================================== #
def make_figure(J, tabs, base_tabs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import gridspec

    plt.rcParams.update({"figure.facecolor": "white", "savefig.facecolor": "white",
                         "axes.grid": True, "grid.alpha": 0.25, "font.size": 8.5})
    C = dict(box_bbox="#c62828", box_bbox_axis="#ef6c00", cube_eqvol="#6a1b9a",
             mesh="#2e7d32", slab="#1565c0", sphere="#9e9e9e", disc="#00838f",
             box_aspect_voleq="#ad1457", prop_bbox="#5d4037")
    key = "matrice4e" if any(k.startswith("main|matrice4e") for k in tabs["main"]) else KEYS[0]

    def get(arm):
        t = tabs["main"].get(f"main|{key}|{arm}|spherical")
        return t if t is not None else base_tabs.get(("main", key, arm, "spherical"))

    fig = plt.figure(figsize=(15.5, 12.0))
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.28,
                           left=0.055, right=0.985, top=0.925, bottom=0.055)
    g = J["geometry"][key]
    fig.suptitle(
        f"report16 rung — bounding-box surrogate micro-Doppler   |   {g['drone']}   "
        f"|   PO, {B.FC_MAIN/1e9:.1f} GHz, R={B.RANGE_M:.0f} m, el={B.EL_DEG:.0f}$^\\circ$, "
        f"{B.N_AZ} azimuths, spherical wavefront", fontsize=12, y=0.972)

    # (a) 위상 표 파형
    ax = fig.add_subplot(gs[0, 0])
    ia = 0
    for arm in ("mesh", "prop_bbox", "box_bbox", "box_bbox_axis", "cube_eqvol", "sphere"):
        T = get(arm)
        if T is None:
            continue
        e = T[ia] - T[ia].mean()
        n = np.max(np.abs(e))
        if n <= 0:
            continue
        ph = np.arange(len(e)) * 360.0 / len(e)
        ax.plot(ph, np.abs(e) / n, lw=1.1, color=C.get(arm, "k"),
                ls=":" if arm == "sphere" else "-",
                label=arm + (" (numerical floor)" if arm == "sphere" else ""))
    ax.set_xlim(0, 360)
    ax.set_xticks([0, 90, 180, 270, 360])
    ax.set_xlabel("rotor phase [deg]")
    ax.set_ylabel("|AC field|, peak-normalised")
    ax.set_title("(a) one revolution, az = 0$^\\circ$", loc="left", fontsize=9.5)
    ax.legend(fontsize=6.6, ncol=2)

    # (b) 차수 선 스펙트럼
    ax = fig.add_subplot(gs[0, 1])
    for arm in ("mesh", "prop_bbox", "box_bbox_axis", "cube_eqvol"):
        T = get(arm)
        if T is None:
            continue
        S = T.shape[1]
        c = np.fft.fft(T[ia]) / S
        P = np.abs(c) ** 2
        m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
        sel = (m > 0) & (m <= 40)
        p = P[sel] / max(P[m != 0].sum(), 1e-300)
        ax.plot(m[sel], 10 * np.log10(np.maximum(p, 1e-14)), lw=1.0, marker="o", ms=2.4,
                color=C.get(arm, "k"), label=arm)
    ax.set_xlabel("harmonic order m  (Doppler = m$\\cdot f_{rot}$)")
    ax.set_ylabel("AC power fraction [dB]")
    ax.set_ylim(-60, 2)
    ax.set_title("(b) line spectrum — 90$^\\circ$ vs 180$^\\circ$ symmetry", loc="left", fontsize=9.5)
    ax.legend(fontsize=6.6)

    # (c) 차수 종류별 몫
    ax = fig.add_subplot(gs[0, 2])
    arms = [a for a in ("mesh", "slab", "prop_bbox", "box_bbox", "box_bbox_axis",
                        "box_aspect_voleq", "cube_eqvol", "sphere")
            if f"main|{key}|{a}" in J["order_classes"]]
    w = 0.27
    xs = np.arange(len(arms))
    for i, (cls, col, lab) in enumerate((("odd", "#8d6e63", "odd m"),
                                         ("even_not_mult4", "#1565c0", "m$\\equiv$2 (mod 4)"),
                                         ("mult4", "#c62828", "m$\\equiv$0 (mod 4)"))):
        v = [J["order_classes"][f"main|{key}|{a}"][cls]["mean"] for a in arms]
        ax.bar(xs + (i - 1) * w, v, w, color=col, label=lab)
    ax.set_xticks(xs)
    ax.set_xticklabels(arms, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("share of AC power")
    ax.set_title("(c) where the AC power sits", loc="left", fontsize=9.5)
    ax.legend(fontsize=6.6)

    # (d) 방위 주기 상관
    ax = fig.add_subplot(gs[1, 0])
    for i, (sh, col, lab) in enumerate((("shift_90deg", "#c62828", "shift 90$^\\circ$"),
                                        ("shift_180deg", "#1565c0", "shift 180$^\\circ$"))):
        v = [J["symmetry"][f"main|{key}|{a}"].get(sh, {}).get("mean", np.nan) for a in arms]
        ax.bar(xs + (i - 0.5) * 0.36, v, 0.36, color=col, label=lab)
    ax.axhline(1.0, color="k", lw=0.8, ls=":")
    ax.set_xticks(xs)
    ax.set_xticklabels(arms, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("self-correlation of AC waveform")
    ax.set_title("(d) rotational period test", loc="left", fontsize=9.5)
    ax.legend(fontsize=6.6)

    # (e) 도플러 폭
    ax = fig.add_subplot(gs[1, 1])
    labs, vals, errs, cols = [], [], [], []
    for a in arms:
        d = (J["arms"].get(f"main|{key}|{a}") or J["reference_arms"].get(f"main|{key}|{a}"))
        if not d:
            continue
        dd = d.get("spherical", d)
        labs.append(a)
        vals.append(dd["per_az"]["width_ratio"]["mean"])
        errs.append(dd["per_az"]["width_ratio"]["sd"])
        cols.append(C.get(a, "k"))
    ax.bar(np.arange(len(labs)), vals, 0.6, yerr=errs, capsize=2.5, color=cols,
           hatch=["//" if l in ("sphere", "disc") else "" for l in labs])
    ax.axhline(1.0, color="k", lw=1.0, ls="--")
    ax.axhline(g["r_corner_over_prop_radius"], color="#c62828", lw=1.0, ls=":")
    ax.text(len(labs) - 0.4, 1.02, "prop tip", fontsize=6.5, ha="right", color="k")
    ax.text(len(labs) - 0.4, g["r_corner_over_prop_radius"] * 1.02, "box corner",
            fontsize=6.5, ha="right", color="#c62828")
    ax.set_xticks(np.arange(len(labs)))
    ax.set_xticklabels(labs, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("$f_{d,edge}$ / $f_{tip,prop}$")
    ax.set_title("(e) Doppler width vs prop-tip prediction", loc="left", fontsize=9.5)
    ax.text(0.02, 0.96, "hatched = null arm (AC at numerical floor, value not physical)",
            transform=ax.transAxes, fontsize=6.2, va="top")

    # (f) 짝지은 차이 (상자 − 메쉬)
    ax = fig.add_subplot(gs[1, 2])
    pk = ("flash_contrast_db", "n_eff_orders", "blade_comb_frac", "width_ratio", "dc_ac_db")
    ys = np.arange(len(pk))
    for j, kk in enumerate(KEYS):
        p = J["paired_vs_reference"].get(f"main|{kk}|box_bbox - mesh")
        if not p:
            continue
        m = [p[x]["mean"] for x in pk]
        e = [p[x]["sem"] for x in pk]
        ax.barh(ys + (j - 0.5) * 0.36, m, 0.36, xerr=e, capsize=2,
                color=("#1565c0" if j == 0 else "#2e7d32"), label=kk)
    ax.axvline(0, color="k", lw=0.9)
    ax.set_yticks(ys)
    ax.set_yticklabels([x.replace("_db", " [dB]") for x in pk], fontsize=7)
    ax.set_xlabel("box_bbox  $-$  CAD mesh   (paired, same azimuth)")
    ax.set_title("(f) does shape detail change the metric?", loc="left", fontsize=9.5)
    ax.legend(fontsize=6.6)

    # (g) 방위 × 차수 지도 (상자)
    for col, arm in ((0, "box_bbox_axis"), (1, "mesh")):
        ax = fig.add_subplot(gs[2, col])
        T = get(arm)
        if T is None:
            continue
        S = T.shape[1]
        M = np.zeros((T.shape[0], 33))
        for i in range(T.shape[0]):
            c = np.fft.fft(T[i] - T[i].mean()) / S
            P = np.abs(c) ** 2
            m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
            for mm in range(33):
                M[i, mm] = P[np.abs(m) == mm].sum()
        M = 10 * np.log10(np.maximum(M / max(M.max(), 1e-300), 1e-6))
        im = ax.imshow(M.T, origin="lower", aspect="auto", cmap="magma", vmin=-50, vmax=0,
                       extent=[0, 360, -0.5, 32.5])
        ax.set_xlabel("azimuth [deg]")
        ax.set_ylabel("harmonic order m")
        ax.set_title(f"({'g' if col == 0 else 'h'}) {arm}: order map", loc="left", fontsize=9.5)
        fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02).set_label("dB", fontsize=7)

    # (i) 예측 채점표
    ax = fig.add_subplot(gs[2, 2])
    ax.axis("off")
    lines = ["PRE-REGISTERED PREDICTIONS (written before compute)", ""]
    for nm, v in J["prediction_score"].items():
        if nm.startswith("_"):
            continue
        lines.append(f"{v['verdict']:<28s}  {nm}")
    lines += ["", f"prediction sha256[:12] = {J['prediction_score']['_prediction_file']['sha256'][:12]}",
              f"written {J['prediction_score']['_prediction_file']['mtime']}",
              f"results {J['meta']['generated']}"]
    ax.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=7.2, family="monospace",
            transform=ax.transAxes)
    ax.set_title("(i) scorecard", loc="left", fontsize=9.5)

    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=155)
    fig.savefig(OUT_FIG.replace(".png", ".pdf"))
    plt.close(fig)
    return os.path.relpath(OUT_FIG, ROOT)


# =========================================================================== #
#  findings — 숫자는 위에서 계산된 값만 참조한다 (손입력 금지)
# =========================================================================== #
def findings(J):
    F = {}
    F["q0_what_this_rung_is"] = dict(
        ko=("기체를 통째로 경계상자 하나로 바꾸고 **같은 회전축·같은 rpm·같은 위상격자**로 "
            "실제로 돌려서 마이크로도플러를 냈다. 구는 돌려도 변조가 0 이지만 상자는 0 이 아니다 "
            "— 그 «0 이 아님» 이 진짜 블레이드의 변조와 얼마나 닮았는지가 이 단의 질문이다."),
        fairness_ko=("거리·고각·방위격자·주파수·파면·점간격 규약을 기준 메쉬와 동일하게 두었고, "
                     "기준 팔(mesh·slab·disc·sphere)은 기준 라운드가 저장한 **같은 배열**을 다시 "
                     "읽어 썼다(base_reproduction_gate 가 그 동일성을 검사한다)."))

    r = {}
    for key in KEYS:
        gg = J["geometry"][key]
        r[key] = dict(
            bbox_mm=gg["mesh_bbox_mm"], aspect_xy=gg["aspect_xy"],
            bbox_volume_over_mesh=gg["bbox_volume_over_mesh"],
            bbox_fill_fraction=gg["bbox_fill_fraction"],
            cube_eqvol_side_mm=gg["cube_eqvol_side_mm"],
            box_aspect_voleq_dims_mm=gg["box_aspect_voleq_dims_mm"],
            r_corner_over_prop_radius=gg["r_corner_over_prop_radius"])
    F["q1_geometry_ledger"] = dict(
        question_ko="상자는 진짜 기체와 얼마나 다른 물건인가 (부피 등가는 계산해서 맞췄다)",
        values=r,
        note_ko=("경계상자는 정의상 부피가 같지 않다 — 채움률이 곧 «상자가 얼마나 부풀려진 "
                 "표적인가» 다. 그래서 같은 종횡비로 부피만 메쉬에 맞춘 상자(box_aspect_voleq)와 "
                 "같은 부피 정육면체(cube_eqvol)를 같이 돌려 «크기» 와 «종횡비» 를 갈라 두었다."))

    F["q2_prediction_scorecard"] = dict(
        question_ko="계산 전에 적어 둔 예측이 맞았는가 (문턱은 예측 파일에 미리 박혀 있다)",
        verdicts={k: v["verdict"] for k, v in J["prediction_score"].items() if not k.startswith("_")},
        detail=J["prediction_score"],
        note_ko="REFUTED 도 그대로 남긴다 — 틀린 예측이 곧 결과다.")

    r = {}
    for key in KEYS:
        row = {}
        for nm in ("box_bbox - mesh", "box_bbox - slab", "box_bbox - sphere",
                   "box_bbox - cube_eqvol", "box_aspect_voleq - mesh",
                   "box_aspect_voleq - slab", "box_aspect_voleq - cube_eqvol",
                   "box_bbox_axis - cube_eqvol", "box_bbox_axis - box_bbox"):
            p = J["paired_vs_reference"].get(f"main|{key}|{nm}")
            if p:
                row[nm] = {kk: dict(mean=p[kk]["mean"], sem=p[kk]["sem"],
                                    frac_positive=p[kk]["frac_positive"]) for kk in PAIR_KEYS}
        r[key] = row
    F["q3_box_vs_real_blades"] = dict(
        question_ko="⭐⭐ 돌아가는 상자와 진짜 블레이드는 얼마나 다른가 (같은 방위끼리 짝지은 차이)",
        values=r,
        how_to_read_ko=("frac_positive 가 0.5 근처면 «자세를 바꾸면 부호가 뒤집힌다 = 차이 없음», "
                        "0 이나 1 이면 «어느 자세에서 봐도 한 방향» 이다. 평균±산포만 보면 자세 "
                        "산포가 공통분이라 차이가 묻힌다."),
        caveat_ko=("dc_ac_db 는 이 커널에 가림이 없어 가장 오염된 지표다 — 게다가 상자 팔에는 "
                   "정적 프레임이 아예 없어 DC 의 출처가 다르다. 절대값 인용 금지."))

    F["q4_metric_gauge_lesson"] = dict(
        question_ko="⭐ 지표 자체에 대해 배운 것",
        in_band_gate=dict(
            values={key: J["arms"].get(f"main|{key}|box_bbox", {}).get("spherical", {})
                    .get("own_band_gauge", {}).get("per_az", {}).get("in_band_ac_frac")
                    for key in KEYS},
            protocol_gauge={key: J["arms"].get(f"main|{key}|box_bbox", {}).get("spherical", {})
                            .get("per_az", {}).get("in_band_ac_frac") for key in KEYS},
            ko=("report16_base 의 in_band 판정기는 대역을 «프롭 반경으로 계산한 β» 의 1.5배로 "
                "잡는다. 표적이 프롭보다 큰 반경으로 돌면(상자 모서리) 진짜 물리가 대역 밖으로 "
                "나가 «해석 불가» 로 잘못 찍힌다. 판정기는 «표적 반경 = 프롭 반경» 을 암묵적으로 "
                "가정하고 있었다 — 대체 표적을 넣을 때는 그 표적의 β 로 다시 재야 한다.")),
        blade_comb=dict(
            values={key: dict(box_axis=J["arms"].get(f"main|{key}|box_bbox_axis", {})
                              .get("spherical", {}).get("per_az", {}).get("blade_comb_frac", {})
                              .get("mean"),
                              mesh=J["reference_arms"].get(f"main|{key}|mesh", {})
                              .get("per_az", {}).get("blade_comb_frac", {}).get("mean"))
                    for key in KEYS},
            ko=("blade_comb_frac 은 «블레이드 수의 배수 차수에 실린 몫» 인데 블레이드가 2장이라 "
                "그 빗은 곧 «짝수 차수» 다. 축 위의 직사각 상자도 180° 대칭이라 짝수에만 선다 → "
                "이 지표만으로는 돌아가는 상자와 진짜 블레이드를 구별할 수 없다.")))

    F["q4b_which_metric_actually_separates_them"] = dict(
        question_ko=("⭐⭐ 어떤 지표가 «돌아가는 상자» 와 «진짜 블레이드» 를 실제로 가르는가 "
                     "(짝지은 차이 ÷ 메쉬의 자세 산포)"),
        values=J["discriminability"],
        note_ko=("이 단의 실용적 산출물이다. 가르는 지표가 있으면 «형상 정밀도가 값어치가 있다» 는 "
                 "주장이 설 자리가 생기고, 없으면 교수 지적이 마이크로도플러에서도 맞다는 뜻이다. "
                 "⛔ 부피가 부풀려진 경계상자로 이겼다고 말하면 안 되므로, 부피를 메쉬에 맞춘 "
                 "box_aspect_voleq 를 나란히 놓았다."))

    #  ⭐ 헤드라인 — 숫자를 손으로 적지 않고 위 블록에서 뽑아 «몇 개가 갈라지는가» 를 센다.
    #     dc_ac_db 와 in_band_ac_over_dc_db 는 «정적 동체 상실» 이라는 구조적 교란이 있어
    #     형상 판정에서 제외한다(제외 사실을 같이 적는다).
    CONFOUNDED = ("dc_ac_db", "in_band_ac_over_dc_db", "sigma_eq_mean_dbsm")
    SEP_THR = 2.0
    hl = {}
    for key in KEYS:
        row = {}
        for surro, blk in (J["discriminability"].get(key, {}) or {}).items():
            usable = {kk: v["separation_in_pose_sd"] for kk, v in blk.items()
                      if kk not in CONFOUNDED and v["separation_in_pose_sd"] is not None}
            sep = {kk: v for kk, v in usable.items() if abs(v) >= SEP_THR}
            row[surro] = dict(
                n_metrics_scored=len(usable), n_separating=len(sep),
                separating={kk: usable[kk] for kk in sorted(sep, key=lambda x: -abs(usable[x]))},
                not_separating={kk: usable[kk] for kk in usable if abs(usable[kk]) < SEP_THR},
                volume_over_mesh=J["arms"].get(f"main|{key}|{surro}", {})
                .get("geometry", {}).get("volume_over_mesh"))
        hl[key] = row
    F["q6_headline"] = dict(
        question_ko="⭐⭐ 한 줄 결론 — 돌아가는 상자는 진짜 블레이드와 구별되는가",
        separation_threshold_in_pose_sd=SEP_THR,
        excluded_as_confounded=list(CONFOUNDED),
        excluded_why_ko=("dc_ac_db·in_band_ac_over_dc_db — 기체 전체를 프리미티브 하나로 바꾸면 "
                         "정적 동체가 사라져 0-도플러 항이 통째로 없어진다(구·큐브·상자 모두 동일). "
                         "sigma_eq_mean_dbsm — 프리미티브는 PEC, 메쉬는 재질가중이라 재질 차이가 "
                         "섞인다. 셋 다 «형상 충실도» 의 증거가 될 수 없어 세는 데서 뺀다."),
        blade_comb_caveat_ko=("⚠ blade_comb_frac 이 분리한다고 나오면 그것은 형상이 아니라 "
                              "**상자를 회전축 밖에 놓은 것** 때문이다 — box_bbox_axis 행을 보면 "
                              "다시 메쉬와 같아진다."),
        values=hl,
        aspect_only_test=dict(
            what_ko=("과제문 예측(«큐브와 비슷하되 종횡비가 달라») 의 가장 깨끗한 검사. "
                     "box_aspect_voleq 와 cube_eqvol 은 둘 다 축 위에 있고 둘 다 부피가 메쉬와 "
                     "같다 — 남은 차이는 **종횡비 하나뿐**이다."),
            values={key: J["paired_vs_reference"].get(f"main|{key}|box_aspect_voleq - cube_eqvol")
                    for key in KEYS}),
        size_matters_more_than_shape_ko=(
            "⭐ 경계상자를 그대로 쓰면 부피가 메쉬의 여러 배라 거의 모든 지표가 갈라진다. 그런데 "
            "**부피만 메쉬에 맞추면**(box_aspect_voleq) 갈라지는 지표 수가 줄어든다. 즉 «경계상자가 "
            "진짜와 다르다» 의 상당 부분은 형상이 아니라 **크기** 때문이다. 대체모델을 평가할 때 "
            "부피를 안 맞추면 결론이 부풀려진다."),
        which_primitive_matches_is_airframe_dependent_ko=(
            "⚠ 기체마다 «맞는 프리미티브» 가 다르다는 것을 그대로 적어 둔다. 부피 등가 조건에서 "
            "mini2 는 정육면체가 메쉬와 안 갈라지고 종횡비 상자는 갈라졌으며, matrice4e 는 정확히 "
            "그 반대였다(위 표의 n_separating 참조). 즉 «모수 0개짜리 프리미티브 하나가 모든 "
            "기체를 대신한다» 는 주장은 서지 않는다 — 다만 **각 기체마다** 그 기체를 대신하는 "
            "모수 0개 프리미티브가 존재한다는 것도 동시에 사실이다. 대체모델이 이기는 것은 "
            "«어느 하나로 통일해서» 가 아니라 «기체마다 골라서» 다."))

    F["q5_validity"] = dict(
        question_ko="이 결과를 어디까지 믿을 수 있나",
        base_reproduction_gate=J["base_reproduction_gate"]["verdict"],
        null_was_actually_spun=J["null_was_actually_spun"],
        sampling_adequacy=J["sampling_adequacy"],
        point_density_control=J["point_density_control"],
        wavefront_control=J["wavefront_control"],
        material_invariance=J["material_invariance"],
        po_validity=J["po_validity_warning"])
    return F


# =========================================================================== #
#  main
# =========================================================================== #
def main(skip_compute=False, no_hi=False):
    t0 = time.time()
    write_prediction()                       # ⭐ 계산보다 먼저 (이미 있으면 그대로 둔다)
    stamp = prediction_stamp()
    compute_started = time.time()

    tabs, metas = {}, {}
    if skip_compute:
        for tag in ("main", "hi"):
            T, M = load_local(tag)
            if T:
                tabs[tag], metas[tag] = T, M
    else:
        tabs["main"], metas["main"] = compute("main", B.FC_MAIN, ARMS_MAIN, with_s2=True)
        if not no_hi:
            tabs["hi"], metas["hi"] = compute("hi", B.FC_PO_KNEE, ARMS_HI, with_s2=False)

    base_tabs = load_base_tables()

    J = dict(meta=dict(
        report="report16_rung_box_bbox", producer="benchmark/report16_rung_box_bbox.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        rung_ko="사다리 한 단 — 경계상자(box_bbox)",
        model_definition_ko=("기체 CAD 메쉬(build_drone)를 감싸는 가장 작은 축정렬 직육면체, PEC. "
                             "benchmark/das_fleet_box_control.py 의 box_bbox 와 같은 정의다."),
        kinematics_ko=("기체 요축(원점을 지나는 z 축) 둘레로, 로터와 **같은 rpm**, "
                       "report16_base 규약이 계산한 **같은 위상 격자**로 실제로 돌린다."),
        question_ko=("구는 돌려도 변조가 0 이다. 상자는 0 이 아니지만 그것은 블레이드가 아니라 "
                     "모서리·평면의 변조다. 얼마나 다른가."),
        reads=[os.path.relpath(BASE_JSON, ROOT), os.path.relpath(BASE_NPZ, ROOT),
               os.path.relpath(OUT_PRED, ROOT)],
        writes_only=[os.path.relpath(p, ROOT) for p in (OUT_JSON, OUT_NPZ, OUT_FIG, OUT_PRED)],
        gpu={t: m.get("gpu") for t, m in metas.items()}))
    J["prestamp"] = dict(
        prediction=stamp,
        compute_started=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(compute_started)),
        prediction_precedes_compute=bool(stamp["mtime_epoch"] <= compute_started),
        what_ko=("사전 예측 파일의 sha256 과 수정시각. 결과보다 먼저 쓰였다는 것을 "
                 "파일시스템 시각으로 확인할 수 있다."))
    J["protocol"] = dict(
        inherited_from="benchmark/report16_base.py (프로토콜·지표 함수 전부 그대로 호출)",
        fc_main_hz=B.FC_MAIN, fc_po_knee_hz=B.FC_PO_KNEE, el_deg=B.EL_DEG, range_m=B.RANGE_M,
        n_az=B.N_AZ, az_step_deg=360.0 / B.N_AZ, os_factor=B.OS_FACTOR,
        wavefront_headline="spherical", wavefront_control="plane", period_deg=360.0,
        monostatic=True, primitive_material="PEC (|Gamma| = 1)",
        rotating_part_spacing="lambda/11 (report16_base 회전부 규약), fine arm = lambda/44",
        engine="pure PO on point clouds (no occlusion, no edge diffraction), report16_base kernel",
        arms_ko={
            "box_bbox": "메쉬 경계상자를 **실제 놓인 자리**(bbox 중심)에 두고 돌린다 — 이 단의 주인공",
            "box_bbox_axis": "같은 상자를 회전축 위로 올린 판 — 축이탈 흔들림을 분리",
            "box_aspect_voleq": "같은 종횡비 · 부피는 메쉬와 같게 — «크기» 를 분리",
            "cube_eqvol": "같은 부피 정육면체 — 사전 예측의 비교 대상",
            "box_bbox_fine": "점구름 4배 촘촘 — 밀도 반론 차단",
            "prop_bbox": ("⭐ 부품 단위 경계상자 — 프로펠러만 그 프롭의 경계상자로 바꾸고 "
                          "**정적 프레임은 남긴다**. 전신 프리미티브의 «정적부 상실» 교란이 "
                          "없어 기준 slab·disc 팔과 같은 무대에 선다"),
            "box_bbox_S<N>": "위상 격자를 상자 자신의 β 에 맞춰 키운 판 — 표본화 적정성 검사",
            "mesh/slab/disc/sphere": "기준 라운드가 저장한 **같은 배열**을 다시 읽어 쓴다(재계산 없음)"})

    J = analyse(tabs, metas, base_tabs, J)
    J["base_reproduction_gate"] = base_reproduction_gate(J)
    J["material_invariance"] = material_invariance(tabs)

    knee = json.load(open(os.path.join(ROOT, "outputs",
                                       "report00_po_case.json")))["s4_limits"]
    J["po_validity_warning"] = dict(
        knee_a_over_lambda=knee["po_validity_knee_a_over_lambda"],
        knee_rule=knee["po_validity_knee_rule"],
        blade_knee_ghz=knee["feature_knee_frequencies"]["prop_blade_13p78mm_ghz"],
        production_band_ghz=B.FC_MAIN / 1e9,
        box_smallest_feature_mm={k: min(J["geometry"][k]["mesh_bbox_mm"]) for k in KEYS},
        box_smallest_feature_over_lambda={
            k: min(J["geometry"][k]["mesh_bbox_mm"]) / 1000.0 / (B.C0 / B.FC_MAIN) for k in KEYS},
        statement_ko=(
            "마이크로도플러를 만드는 부품(프로펠러 블레이드, 폭 13.78 mm)은 "
            f"{knee['feature_knee_frequencies']['prop_blade_13p78mm_ghz']} GHz 에서야 PO 유효 "
            f"무릎(폭 ≥ {knee['po_validity_knee_a_over_lambda']:.3f}λ)을 넘는다. 생산대역 "
            f"{B.FC_MAIN/1e9:.1f} GHz 에서는 **커널이 가장 약한 부품이 곧 신호원**이다.\n"
            "⭐ 그런데 상자의 가장 작은 변조차 파장의 여러 배다 — 즉 이번 대조는 «커널이 편한 "
            "표적(상자)» 대 «커널이 불편한 표적(진짜 블레이드)» 이다. 이 비대칭은 상자에 유리하게 "
            "작용하므로, «상자로 충분하다» 는 결론은 보수적이지 않고, «메쉬가 낫다» 는 결론은 "
            "보수적이다. 그래서 15.86 GHz 를 같이 돌려 부호 일치를 확인한다."),
        occlusion_ko=("가림이 없다 — 상자 팔은 볼록체라 자기가림이 원래 없지만, 메쉬 팔은 있다. "
                      "따라서 dc_ac_db 는 상자 쪽에 유리하게 편향돼 있다. 절대값 인용 금지."))

    J["prediction_score"] = score_predictions(J)
    J["findings"] = findings(J)

    save = {}
    for tag, T in tabs.items():
        for kk, v in T.items():
            save[kk.replace("|", "__")] = v
    np.savez_compressed(OUT_NPZ, **save)
    J["meta"]["tables_npz"] = os.path.relpath(OUT_NPZ, ROOT)
    J["figures"] = dict(main=make_figure(J, tabs, base_tabs))
    J["meta"]["seconds"] = float(time.time() - t0)

    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✅ {os.path.relpath(OUT_JSON, ROOT)}  ·  {J['figures']['main']}  "
          f"[{J['meta']['seconds']:.0f}s]")
    for nm, v in J["prediction_score"].items():
        if not nm.startswith("_"):
            print(f"   {v['verdict']:<28s} {nm}")
    return J


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--predict", action="store_true", help="사전 예측만 쓰고 종료")
    ap.add_argument("--skip-compute", action="store_true", help="스크래치 표로 분석만 다시")
    ap.add_argument("--no-hi", action="store_true", help="15.86 GHz 대조 생략")
    a = ap.parse_args()
    if a.predict:
        write_prediction()
    else:
        main(skip_compute=a.skip_compute, no_hi=a.no_hi)
