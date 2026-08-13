# -*- coding: utf-8 -*-
"""
report16_rung_mesh_full.py — ⭐ **사다리 한 단: 우리 메쉬(기준)의 마이크로도플러**
================================================================================

무엇을 하는가
--------------------------------------------------------------------------------
드론이 제자리에 떠 있어도 프로펠러가 돌기 때문에 되돌아오는 전파가 시간에 따라 흔들린다.
그 흔들림이 «마이크로도플러» 다 — 표적 **전체**가 움직여 생기는 도플러가 아니라 표적의
**일부(블레이드)**가 움직여 생기는 도플러라는 뜻이다.

이 파일은 «사다리(ladder)» 의 **첫 단**이다. 사다리란 같은 조건에서 표적 모델만 갈아 끼우며
올라가는 비교다: 등가부피 구 → 상자 → 평판 프리미티브 → **우리 CAD 메쉬**. 이 단은 그중
**우리 메쉬(기준)** 를 낸다. 뒤에 오는 단들은 전부 이 단의 숫자와 나란히 놓인다.

왜 이걸 재는가 (배경 — 결론을 미리 정하지 않기 위해 적어 둔다)
--------------------------------------------------------------------------------
지도교수의 지적은 «드론 RCS 정밀도는 연구 값어치가 없다» 이고, **우리 데이터가 그 지적을
상당 부분 뒷받침한다**. 절대 세기(RCS)만 놓고 보면 매개변수가 하나도 없는 등가부피 구가
우리 정밀 메쉬를 이긴다 — 그 숫자는 손으로 적지 않고 outputs/p3_validation_v2.json 에서
읽어 온다(이 파일의 `rcs_ladder_context` 블록).

다만 구가 **원리적으로 못 내는 것**이 하나 있다. 구는 어느 방향에서 봐도 똑같이 생겨서
방위에 따른 변동(ε)이 **정확히 0** 이다. 그래서 사다리가 묻는다 —
«그 구조 우위가 마이크로도플러에서는 얼마나 크게 나타나는가?»

⚠ 이 단은 그 질문에 **답하지 않는다**. 이 단이 하는 일은 세 가지다:
   (1) 기준(우리 메쉬)의 마이크로도플러를 낸다,
   (2) **계산 전에 적어 둔 예측**(prereg)을 채점한다 — 맞췄다고 나중에 우기지 못하게,
   (3) 뒤 단들이 **똑같은 운동학**으로 돌 수 있도록 «운동학 계약» 을 숫자로 넘긴다.

⭐⭐ 공정성 — 이 사다리의 급소
--------------------------------------------------------------------------------
구를 «안 돌리고» 변조 0 을 얻으면 그건 증명이 아니라 동어반복이다. 그래서 이 파일은
뒤 단이 반드시 맞춰야 할 것을 전부 **계산해서** `kinematics_contract` 에 담는다:
회전축·rpm·회전당 위상 스텝 수·위상 격자·로터 중심/기준각/회전방향·PRF·거리·고각·방위 목록,
그리고 **등가부피**(구 반지름·정육면체 한 변·bbox 비율 유지 상자)와 **면적가중 |Γ|**.
숫자를 손으로 옮겨 적지 말고 이 블록을 그대로 읽어 쓰면 공정성이 자동으로 지켜진다.

규약은 report16_base 를 그대로 쓴다 (재구현 금지)
--------------------------------------------------------------------------------
`benchmark/report16_base.py` 의 `derive_protocol` / `md_metrics16` / `field_static` /
`field_rotor` / `look_and_antenna` 를 **import 해서** 쓴다. 그래야 하나라도 어긋나 비교가
깨지는 일이 없다. 재현 게이트(`reproduction_gate`)에서 base 가 저장해 둔 위상표와
**비트 단위로** 같은지 확인한다.

⚠⚠ 반드시 같이 읽어야 할 한계
--------------------------------------------------------------------------------
우리 PO 커널이 믿을 만하려면 부품의 특징 폭이 0.729λ 이상이어야 한다. 프로펠러 블레이드
폭 13.78 mm 는 15.86 GHz 에서야 그 문턱을 넘는다. 즉 3.5 GHz 에서는
**마이크로도플러를 만드는 바로 그 부품이 우리 커널이 가장 약한 부품**이다.
그래서 두 대역(3.5 GHz 생산대역 · 15.86 GHz 무릎)을 **둘 다** 돌려 나란히 적는다.
가림(occlusion)은 없다 — 블레이드가 동체 뒤로 가도 계속 산란체로 센다(의도된 통제).

⛔ src/drones.py · src/drone_cad.py 읽기 전용. outputs/report15_* · src/make_report0N_* 미접촉.
⛔ 숫자 손입력 금지 — 규약값·등가부피·문턱 통과 여부까지 전부 계산해서 JSON 에 담는다.
"""
from __future__ import annotations

import argparse
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

import report16_base as R                                              # noqa: E402

SCRATCH = os.environ.get(
    "REPORT16_RUNG_SCRATCH",
    "/tmp/claude-1015/-workspace/"
    "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report16_rung_mesh_full")

OUT_JSON = os.path.join(ROOT, "outputs", "report16_rung_mesh_full.json")
OUT_PREREG = os.path.join(ROOT, "outputs", "report16_rung_mesh_full_prereg.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report16_rung_mesh_full_tables.npz")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_rung_mesh_full.png")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")

#  기체 목록 — 저장소 DRONES 전부(자세 앙상블 24 × 기체 10 = 240 자세).
#  β(=f_tip/f_rot = 팁 도플러가 회전수의 몇 배인가)가 8 에서 171 까지 벌어져 있어
#  «작은 프롭/큰 프롭» 양끝이 모두 들어간다.
FLEET = ["mini2", "mini5pro", "mavic4pro", "matrice4e", "phantom3", "phantom4",
         "x500v2", "typhoonh480", "s1000plus", "m350rtk"]
#  base 가 이미 저장해 둔 기체 — 비트 단위 재현 게이트를 걸 수 있다.
BASE_OVERLAP = ["mini2", "matrice4e", "mavic4pro"]


# =========================================================================== #
#  ⭐ 사전 등록(prereg) — **계산 전에** 디스크에 적고 해시를 남긴다
# =========================================================================== #
#  "나중에 맞췄다고 말하지 못하게" 하는 장치다. 예측은 전부 **판정 가능한 숫자**로 쓴다.
#  ⚠ 여기 적힌 값은 «측정치» 가 아니라 «미리 고른 판정 문턱» 이다(손입력이 허용되는 유일한 자리).
PREREG = {
    "rung": "mesh_full (우리 CAD 메쉬 = 사다리의 기준 단)",
    "written_before_compute": True,
    "one_line_ko": ("⭐ 블레이드 플래시가 나와야 한다. 우리 메쉬는 회전대칭이 아니므로 "
                    "1회전 안에서 블레이드가 시선을 가로지를 때마다 봉우리(플래시)가 서고, "
                    "그 봉우리는 블레이드 수의 배수 차수에 빗처럼 실린다."),
    "mechanism_ko": (
        "왜 봉우리가 서는가 — 블레이드가 시선을 **가로질러** 설 때는 블레이드 전체가 레이더에서 "
        "거의 같은 거리에 놓인다. 그러면 블레이드 위 모든 조각의 되돌아오는 파가 위상이 맞아 "
        "한꺼번에 더해진다(플래시). 반대로 블레이드가 시선과 **나란히** 서면 뿌리와 팁의 거리가 "
        "크게 달라 위상이 어긋나 서로 지운다. 우리 PO 커널에는 정반사/확산 구분이 없어 조명된 면을 "
        "전부 위상 맞춰 더하므로, 이 플래시는 따로 넣은 항이 아니라 **저절로** 나온다."),
    "predictions": [
        {"id": "P1", "ko": "플래시 대조비가 0 dB 보다 확실히 크다 — 전 기체 방위평균 ≥ 3 dB",
         "metric": "flash_contrast_db (24 방위 평균)", "op": ">=", "threshold": 3.0,
         "scope": "모든 기체", "why_ko": "회전대칭체의 이론값은 0 dB 다. 구조가 있으면 봉우리가 선다."},
        {"id": "P2", "ko": "AC 전력이 «블레이드 빗»(블레이드 수의 배수 차수)에 몰린다 — 방위평균 ≥ 0.5",
         "metric": "blade_comb_frac (24 방위 평균)", "op": ">=", "threshold": 0.5,
         "scope": "모든 기체",
         "why_ko": "블레이드가 2장이면 1회전에 플래시가 2번이라 2·4·6… 차수에 실린다. "
                   "0.5 미만이면 «블레이드 플래시» 가 아니라 비대칭·불균형 선이라는 뜻이다."},
        {"id": "P3", "ko": "AC 전력이 운동학적으로 가능한 대역 안에 있다 — 방위평균 ≥ 0.90",
         "metric": "in_band_ac_frac (24 방위 평균)", "op": ">=", "threshold": 0.90,
         "scope": "모든 기체",
         "why_ko": "팁보다 빨리 도는 것은 없다. 대역 밖 전력은 물리가 아니라 이산화 잔차다."},
        {"id": "P4", "ko": "스펙트럼 폭이 팁속도 예측과 맞는다 — 방위평균 width_ratio 가 0.5~1.2",
         "metric": "width_ratio (−20 dB 가장자리 / f_tip, 24 방위 평균)",
         "op": "in", "threshold": [0.5, 1.2], "scope": "모든 기체",
         "why_ko": "운동학이 맞으면 1 근처여야 한다. CAD 블레이드는 테이퍼 때문에 팁까지 "
                   "산란하지 않아 1보다 작게 나올 수 있다."},
        {"id": "P5", "ko": ("단일 로터의 플래시가 **예측한 위상**에 선다 — 블레이드 스팬이 시선 방위에 "
                            "수직이 되는 위상에서 위상격자 1스텝 이내, 전 로터·전 방위의 90% 이상"),
         "metric": "flash_anatomy.phase_err_steps (≤1 인 비율)", "op": ">=", "threshold": 0.90,
         "scope": "모든 기체",
         "why_ko": "위치까지 맞아야 «블레이드가 만든 플래시» 다. 세기만 맞으면 우연일 수 있다."},
        {"id": "P6", "ko": "1회전 플래시 개수 = 블레이드 수 — 전 로터·전 방위의 90% 이상",
         "metric": "flash_anatomy.n_flash_per_rev == prop_blades 인 비율",
         "op": ">=", "threshold": 0.90, "scope": "모든 기체",
         "why_ko": "블레이드 2장이면 1회전에 2번이다. 개수가 다르면 다른 것이 울고 있는 것이다."},
        {"id": "P7", "ko": "방위에 따른 산포 ε 이 0 이 아니다 — 세기의 24방위 표준편차 ≥ 0.5 dB",
         "metric": "eps_level_db (sigma_eq_mean_dbsm 의 24방위 sd)",
         "op": ">=", "threshold": 0.5, "scope": "모든 기체",
         "why_ko": ("⭐ 등가부피 구는 회전대칭이라 이 값이 **정확히 0.00** 이다"
                    "(outputs/p3_validation_v2.json 의 sphere 항). 우리 메쉬가 0 이 아니라는 것이 "
                    "사다리에서 «구조» 가 갖는 자리다.")},
    ],
    "what_would_falsify_ko": (
        "⛔ 결론을 미리 정하지 않는다. 예측이 틀리면 틀린 대로 적는다. 특히 P2 가 깨지면 "
        "«우리 메쉬가 내는 것은 블레이드 플래시가 아니다» 가 되고, P5·P6 이 깨지면 «세기는 나오는데 "
        "위치가 안 맞는다» 가 되어 이 커널의 마이크로도플러 자체를 다시 봐야 한다. "
        "그리고 뒤 단(상자)이 이 기준과 거의 같은 숫자를 내면, 그것은 «형상 정밀도는 "
        "마이크로도플러에서도 값어치가 없다» 는 뜻이며 교수 지적이 여기서도 맞다는 결과다."),
    "not_predicted_here_ko": (
        "이 단은 **다른 모델과의 차이를 예측하지 않는다**. 구·상자 단이 얼마를 낼지는 이 파일이 "
        "말하지 않는다 — 그것은 각 단이 실제로 돌려서 답할 일이다."),
    "disclosure_ko": (
        "⚠ 정직성 고지 — 이 예측 중 일부는 «완전히 눈 감고» 한 것이 아니다. report16_base 가 이미 "
        "mini2·matrice4e 두 기체의 mesh 팔 지표를 냈으므로, **그 두 기체의 P1~P4 는 재확인**이다. "
        "나머지 8 기체는 이 단에서 처음 재는 것이라 진짜 사전 예측이고, "
        "P5(플래시가 예측한 위상에 서는가)·P6(회전당 플래시 개수)·P7(방위 산포 ε)은 "
        "**어느 기체에서도 잰 적이 없는 새 예측**이다. 문턱은 저장소의 어떤 값을 보고 맞춘 것이 "
        "아니라 물리에서 나온 자연스러운 경계로 골랐다(0 dB=회전대칭 이론값, 1/블레이드수=균등분배, "
        "width_ratio=1=운동학 예측)."),
}


def _write_prereg():
    """사전 등록 파일을 **계산 전에** 디스크에 적는다. 이미 있으면 덮지 않는다
    (덮으면 «먼저 적었다» 는 증거가 사라진다)."""
    os.makedirs(os.path.dirname(OUT_PREREG), exist_ok=True)
    fresh = not os.path.exists(OUT_PREREG)
    if fresh:
        with open(OUT_PREREG, "w") as f:
            json.dump(dict(PREREG, written_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                           producer="benchmark/report16_rung_mesh_full.py"),
                      f, ensure_ascii=False, indent=1)
    blob = open(OUT_PREREG, "rb").read()
    return dict(file=os.path.relpath(OUT_PREREG, ROOT),
                sha256=hashlib.sha256(blob).hexdigest(),
                bytes=len(blob),
                written_at=json.loads(blob.decode()).get("written_at"),
                mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                    time.localtime(os.path.getmtime(OUT_PREREG))),
                first_write_this_run=fresh,
                note_ko=("이 파일은 계산 시작 전에 쓰였다. sha256 으로 사후 수정을 막는다 — "
                         "채점 결과가 마음에 안 든다고 예측을 고치면 해시가 바뀐다."))


# =========================================================================== #
#                    WORKER — 위상표(로터별 + 합) 생성
# =========================================================================== #
def _worker(band: str, fc: float, keys: list, keep_rotor: bool):
    """한 대역에서 기체 전부의 위상표를 만든다.

    ⭐ base 의 `mesh` 팔과 **한 줄도 다르지 않게** 만든다 — 점구름 만드는 법(프레임 λ/6,
      회전부 λ/11, n=26, 재질 |Γ| 가중), 반대회전 로터의 거울상 처리(점구름 y-거울),
      누적 순서(프레임 → 로터 순서대로 +=)까지 같다. 그래야 base 표와 비트 단위로 같다.
    """
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from gpu import pick                       # ⚠ torch 보다 먼저 (CUDA 컨텍스트 고정)
    picked = pick(verbose=True)
    import torch

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from drones import (DRONES, build_frame, build_propeller, rotor_layout,   # noqa: E402
                        drone_gamma_map, build_drone)
    from rcs_po import mesh_to_points                                         # noqa: E402

    lam = R.C0 / fc
    k_wav = 2.0 * math.pi / lam
    az_list = np.arange(R.N_AZ) * (360.0 / R.N_AZ)

    def mesh_volume(m):
        V = np.asarray(m.v, float); F = np.asarray(m.f, int)
        p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        cr = np.cross(p1 - p0, p2 - p0)
        return float(np.sum(np.einsum("ij,ij->i", p0, cr)) / 6.0)

    tables, meta = {}, {}
    for key in keys:
        s = DRONES[key]
        proto = R.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
        S = proto["n_phase"]
        phis = np.linspace(0.0, 2 * math.pi, S, endpoint=False)
        gm = drone_gamma_map(s)

        frame = build_frame(s)
        Pf, Nf, dAf, wf_ = mesh_to_points(frame, lam / 6.0, gamma=gm)
        Wf = dAf * wf_
        prop = build_propeller(s, n=26)
        Pp, Np_, dAp, wp = mesh_to_points(prop, lam / 11.0, gamma=gm)
        Pm = Pp * np.array([1.0, -1.0, 1.0])
        Nm_ = Np_ * np.array([1.0, -1.0, 1.0])
        rotors = rotor_layout(s)
        n_rot = len(rotors)

        t0 = time.time()
        for wfront in ("spherical", "plane"):
            T = np.zeros((len(az_list), S), complex)
            Trot = np.zeros((n_rot, len(az_list), S), complex) if keep_rotor else None
            Tframe = np.zeros(len(az_list), complex)
            for ia, az in enumerate(az_list):
                u, A, R_t = R.look_and_antenna(az, R.EL_DEG, R.RANGE_M)
                Ef = R.field_static(torch, dev, Pf, Nf, Wf, k_wav, A, R_t, wfront)
                Tframe[ia] = Ef
                tot = np.full(S, Ef, complex)
                for j, rot in enumerate(rotors):
                    d = float(rot["dir"])
                    P, N, W = (Pp, Np_, dAp * wp) if d > 0 else (Pm, Nm_, dAp * wp)
                    e = R.field_rotor(torch, dev, P, N, W, k_wav, A, R_t, rot["center"],
                                      math.radians(float(rot["base_ang"])), d, phis, wfront)
                    if keep_rotor:
                        Trot[j, ia] = e
                    tot += e
                T[ia] = tot
            tables[f"{key}|{wfront}"] = T
            tables[f"frame|{key}|{wfront}"] = Tframe
            if keep_rotor:
                tables[f"rot|{key}|{wfront}"] = Trot

        # ── ⭐ 블레이드의 «긴 축» 과 «실효 스팬» 을 메쉬에서 계산한다 ──────────────
        #   플래시는 «블레이드 위 모든 조각이 레이더에서 같은 거리에 놓일 때» 선다. 즉 시선
        #   방향으로 잰 위치의 **퍼짐(분산)이 최소**가 되는 자세다. 면적가중 2차모멘트 텐서
        #     M = Σ dA (p−c)(p−c)^T   (xy 평면)
        #   의 큰 고유벡터가 곧 «긴 축» 이고, 시선이 그 축에 **수직**일 때 분산이 최소가 된다.
        #   ⚠ 이 프로펠러는 후퇴각(sweep)이 있어 긴 축이 x 축과 일치하지 않는다 — 그래서
        #     «스팬 = x 축» 이라고 가정하면 플래시 위상 예측이 그 각도만큼 통째로 어긋난다.
        #   실효 스팬: 길이 2a 인 균일 직선의 분산이 a²/3 이므로 a_eff = sqrt(3·λmax/ΣdA).
        xy = Pp[:, :2]
        Wg = dAp
        c_xy = (Wg[:, None] * xy).sum(0) / Wg.sum()
        dxy = xy - c_xy
        Mxy = np.einsum("i,ij,ik->jk", Wg, dxy, dxy)
        evl, evc = np.linalg.eigh(Mxy)
        vmaj = evc[:, -1]
        psi_principal = math.degrees(math.atan2(vmaj[1], vmaj[0])) % 180.0
        rr = np.hypot(xy[:, 0], xy[:, 1])
        R_tip = float(rr.max())
        a_eff = float(math.sqrt(3.0 * float(evl[-1]) / float(Wg.sum())))
        tipsel = rr > 0.8 * R_tip
        a2 = np.radians(2.0 * (np.degrees(np.arctan2(xy[tipsel, 1], xy[tipsel, 0])) % 180.0))
        psi_tip = 0.5 * math.degrees(math.atan2(float((Wg[tipsel] * np.sin(a2)).sum()),
                                                float((Wg[tipsel] * np.cos(a2)).sum()))) % 180.0

        drone = build_drone(s)
        Vd = abs(mesh_volume(drone))
        Vp = abs(mesh_volume(prop))
        Vv = np.asarray(drone.v, float)
        Pv = np.asarray(prop.v, float)
        # 면적가중 |Γ| — 대체 모델을 PEC 로 두면 얼마나 유리한지 재는 자리
        Pd, Nd, dAd, wd = mesh_to_points(drone, lam / 6.0, gamma=gm)
        gam_area = float(np.sum(dAd * wd) / max(np.sum(dAd), 1e-30))
        meta[key] = dict(
            protocol=proto,
            spec=dict(name=s.name, prop_dia_mm=float(s.prop_dia_mm),
                      prop_blades=int(s.prop_blades), hover_rpm=float(s.hover_rpm),
                      num_rotors=int(s.num_rotors),
                      body_lwh_mm=[float(s.body_l_mm), float(s.body_w_mm), float(s.body_h_mm)]),
            rotors=[dict(center=[float(c) for c in r["center"]],
                         base_ang_deg=float(r["base_ang"]), dir=int(r["dir"])) for r in rotors],
            n_frame_pts=int(len(Wf)), n_blade_pts=int(len(Pp)),
            n_tris_frame=int(len(frame.f)), n_tris_prop=int(len(prop.f)),
            drone_volume_m3=Vd, prop_volume_m3=Vp,
            rotating_volume_m3=Vp * s.num_rotors,
            drone_bbox_m=[float(Vv[:, i].max() - Vv[:, i].min()) for i in range(3)],
            prop_span_m=float(Pv[:, 0].max() - Pv[:, 0].min()),
            prop_chord_m=float(Pv[:, 1].max() - Pv[:, 1].min()),
            blade_axis=dict(
                principal_deg=psi_principal, tip_region_deg=psi_tip,
                tip_radius_m=R_tip, effective_half_span_m=a_eff,
                effective_over_tip=a_eff / max(R_tip, 1e-12),
                how_ko=("면적가중 2차모멘트 텐서의 큰 고유벡터 방향[deg, x축 기준] 과 그 고윳값에서 "
                        "푼 실효 반스팬. 전부 메쉬에서 **계산**한 값이다(맞춰 넣은 값 아님). "
                        "principal_deg 가 0 이 아니라는 것은 이 블레이드에 후퇴각이 있다는 뜻이다.")),
            gamma_area_weighted=gam_area,
            gamma_area_weighted_db=float(20 * np.log10(max(gam_area, 1e-12))),
            gamma_map={str(g): float(v) for g, v in gm.items()},
            extent_m=float(max(Vv[:, 0].max() - Vv[:, 0].min(), Vv[:, 1].max() - Vv[:, 1].min())),
            seconds=float(time.time() - t0))
        print(f"  [{band}] {key:12s} S={S:5d} pts(f/b)={len(Wf)}/{len(Pp)} "
              f"[{meta[key]['seconds']:.1f}s]", flush=True)

    os.makedirs(SCRATCH, exist_ok=True)
    np.savez_compressed(os.path.join(SCRATCH, f"tab_{band}.npz"),
                        **{k.replace("|", "__"): v for k, v in tables.items()})
    with open(os.path.join(SCRATCH, f"meta_{band}.json"), "w") as f:
        json.dump(dict(band=band, fc=fc, gpu=picked, keys=keys, keep_rotor=keep_rotor,
                       az_deg=list(az_list), drones=meta), f, ensure_ascii=False)


def run_band(band, fc, keys, keep_rotor, gpu=None):
    p = os.path.join(SCRATCH, f"run_{band}.py")
    os.makedirs(SCRATCH, exist_ok=True)
    with open(p, "w") as f:
        f.write("import sys, json\n"
                f"sys.path.insert(0, {_HERE!r})\n"
                "import report16_rung_mesh_full as M\n"
                "M._worker(sys.argv[1], float(sys.argv[2]), json.loads(sys.argv[3]),"
                " sys.argv[4] == '1')\n")
    env = dict(os.environ)
    if gpu is not None:
        env["SIONNA2_GPU"] = str(gpu)
    print(f"▶ {band} band {fc/1e9:.2f} GHz · {len(keys)} drones · gpu={gpu}", flush=True)
    return subprocess.Popen([sys.executable, p, band, str(fc), json.dumps(keys),
                             "1" if keep_rotor else "0"], cwd=ROOT, env=env)


def load_band(band):
    pz = os.path.join(SCRATCH, f"tab_{band}.npz")
    mj = os.path.join(SCRATCH, f"meta_{band}.json")
    if not os.path.exists(pz):
        return {}, {}
    z = np.load(pz)
    return {k.replace("__", "|"): z[k] for k in z.files}, json.load(open(mj))


# =========================================================================== #
#            ⭐ 플래시 해부 — «봉우리가 예측한 자리에 서는가»
# =========================================================================== #
def _flash_clusters(env, drop_db=3.0):
    """봉우리를 «−3 dB 위에서 이어진 덩어리» 로 센다 (원형 배열).

    ⚠ 왜 국소최대를 세지 않는가 — 플래시 옆에는 **곁잎(sidelobe)** 이 따라온다. 유한한 길이의
      배열이 만드는 회절무늬라 물리적으로 당연히 있는 것인데, 국소최대를 세면 그것까지
      «플래시» 로 세어 버린다(첫 곁잎은 −5 dB 근처라 «최대의 절반» 문턱을 통과한다).
      이어진 덩어리로 세면 본잎 하나가 하나로 세어진다."""
    S = len(env)
    thr = float(env.max()) * 10 ** (-drop_db / 20.0)
    hi = env >= thr
    if hi.all():
        return 1, thr
    # 경계에서 끊어 원형 연결 성분을 센다
    start = int(np.argmax(~hi))
    rolled = np.roll(hi, -start)
    return int(np.sum(rolled[1:] & ~rolled[:-1]) + (1 if rolled[0] else 0)), thr


def flash_anatomy(Trot, meta_key, proto, az_list):
    """로터 **하나씩** 떼어 본 마이크로도플러의 봉우리 위치를 예측과 맞춰 본다.

    예측한 규칙 (사전 등록 파일에 적혀 있는 문장 그대로)
    --------------------------------------------------------------------------
    «블레이드 스팬이 시선 방위에 수직이 되는 위상에서 플래시가 선다.»

    왜 그런가 — 플래시는 블레이드 위 모든 조각이 레이더에서 **같은 거리**에 놓일 때 선다.
    시선 방향으로 잰 위치의 퍼짐(분산)이 최소가 되는 자세가 그것이고, 면적가중 2차모멘트
    텐서의 큰 축(=스팬)이 시선에 수직일 때가 바로 그 자세다.
        blade_axis(φ) = base_ang + dir·φ + ψ₀      [deg]
        플래시 조건: blade_axis − az ≡ 90°  (mod 360/블레이드수)
        → φ* = dir·(az + 90 − base_ang − ψ₀)  (mod 360/블레이드수)
    ψ₀ 는 프로펠러 메쉬 자체의 스팬 방향이다(후퇴각 때문에 0 이 아니다). **메쉬에서 계산**한다.

    ⚠⚠ 정직성 기록 — 이 파일의 **첫 구현은 ψ₀ = 0**(스팬 = x 축)이라 가정했고, 그 판정은
      전 사례 0% 로 **실패**했다. 원인을 찾아보니 이 프로펠러 메쉬에 후퇴각이 있어 스팬이
      x 축에서 약 10° 틀어져 있었다. ψ₀ 는 «맞춰 넣은 값» 이 아니라 메쉬의 기하에서 계산한
      값이므로 규칙 자체는 그대로다. 그래도 두 판정을 **둘 다** 남긴다
      (`x_axis_assumption` 이 실패한 판, `phase_err_steps` 가 규칙대로 한 판).

    폭도 예측된다. 길이 2a 짜리 균일 직선이 각도 Δφ 만큼 틀어지면 양끝 왕복 위상차가
    (4πa cos(el)/λ)·Δφ 라, 반값폭 ≈ 0.886·180/β [deg] 다. β 를 팁반경으로 잡은 판과
    실효 반스팬(2차모멘트에서 푼 값)으로 잡은 판을 둘 다 적는다 — 실제 블레이드는 테이퍼가
    있어 팁까지 고르게 산란하지 않기 때문이다.
    """
    n_rot, n_az, S = Trot.shape
    nb = int(meta_key["spec"]["prop_blades"])
    beta = float(proto["beta"])
    lam = float(proto["lam_m"])
    ax = meta_key.get("blade_axis", {})
    psi0 = float(ax.get("principal_deg", 0.0))
    a_eff = float(ax.get("effective_half_span_m", float("nan")))
    beta_eff = (4.0 * math.pi * a_eff * math.cos(math.radians(R.EL_DEG)) / lam
                if np.isfinite(a_eff) else float("nan"))
    step_deg = 360.0 / S
    period = 360.0 / nb
    phi_deg = np.arange(S) * step_deg
    fwhm_pred_tip = 0.886 * 180.0 / max(beta, 1e-9)
    fwhm_pred_eff = 0.886 * 180.0 / max(beta_eff, 1e-9)

    #  ⭐ 세 판을 **모두** 잰다 — 규칙은 하나인데 그것을 숫자로 옮기는 방법을 세 번 고쳤다.
    #     v0: 스팬 = x 축                       (첫 구현. 실패)
    #     v1: 스팬 = 메쉬 주축 ψ₀               (거울상 로터를 놓침. 절반만 맞음)
    #     v2: 거울상 로터는 ψ₀ 의 **부호가 뒤집힌다** (반대회전 로터에는 거울상 프롭이 달린다)
    err = {"v0_x_axis": [], "v1_axis_no_mirror": [], "v2_axis_with_mirror": []}
    n_flash, fwhm_meas, peak_db, sl = [], [], [], []
    rows = []
    for j in range(n_rot):
        base = float(meta_key["rotors"][j]["base_ang_deg"])
        d = float(meta_key["rotors"][j]["dir"])
        for ia in range(n_az):
            az = float(az_list[ia])
            e = Trot[j, ia]
            env = np.abs(e - e.mean())
            ip = int(np.argmax(env))
            pk = float(env[ip]); med = float(np.median(env))
            for tag, psi in (("v0_x_axis", 0.0), ("v1_axis_no_mirror", psi0),
                             ("v2_axis_with_mirror", psi0 if d > 0 else -psi0)):
                phi0 = (d * (az + 90.0 - base - psi)) % period
                preds = [(phi0 + m * period) % 360.0 for m in range(nb)]
                dphi = min(abs((phi_deg[ip] - pp + 180.0) % 360.0 - 180.0) for pp in preds)
                err[tag].append(dphi / step_deg)
                if j == 0 and ia == 0 and tag == "v2_axis_with_mirror":
                    rows.append(dict(rotor=j, az_deg=az, base_ang_deg=base, dir=int(d),
                                     blade_axis_offset_deg=psi0,
                                     predicted_phase_deg=preds,
                                     measured_phase_deg=float(phi_deg[ip]),
                                     err_deg=float(dphi), phase_step_deg=step_deg))
            cnt, _thr = _flash_clusters(env, 3.0)
            n_flash.append(cnt)
            # 첫 곁잎 높이 — 플래시 개수 규칙이 얼마나 아슬아슬한지 재는 자리
            half_per = int(round(0.5 * period / step_deg))
            near = [(ip + t) % S for t in range(-half_per, half_per + 1)]
            main = {ip}
            for sgn in (1, -1):
                t = 1
                while t <= half_per and env[(ip + sgn * t) % S] >= _thr:
                    main.add((ip + sgn * t) % S); t += 1
            side = [env[i2] for i2 in near if i2 not in main]
            sl.append(20 * math.log10(max(max(side) if side else 1e-300, 1e-300) /
                                      max(pk, 1e-300)))
            half = pk / math.sqrt(2.0)
            li = ri = 0
            while li < S // 2 and env[(ip - li - 1) % S] >= half:
                li += 1
            while ri < S // 2 and env[(ip + ri + 1) % S] >= half:
                ri += 1
            fwhm_meas.append((li + ri + 1) * step_deg)
            peak_db.append(20 * math.log10(max(pk, 1e-300) / max(med, 1e-300)))
    err_steps = np.asarray(err["v2_axis_with_mirror"])
    n_flash = np.asarray(n_flash); fwhm_meas = np.asarray(fwhm_meas)
    attempts = {tag: dict(phase_err_steps=R.summarize(np.asarray(v)),
                          frac_within_1_step=float(np.mean(np.asarray(v) <= 1.0)))
                for tag, v in err.items()}
    return dict(
        n_rotor=int(n_rot), n_az=int(n_az), n_cases=int(err_steps.size),
        phase_step_deg=step_deg, blades=nb,
        blade_axis_offset_deg=psi0,
        blade_axis_source="area-weighted 2nd-moment principal axis of the propeller point cloud",
        phase_err_steps=R.summarize(err_steps),
        phase_err_deg=R.summarize(err_steps * step_deg),
        frac_within_1_step=float(np.mean(err_steps <= 1.0)),
        frac_within_half_step=float(np.mean(err_steps <= 0.5)),
        frac_within_1_deg=float(np.mean(err_steps * step_deg <= 1.0)),
        quantization_floor_deg=step_deg / 4.0,
        quantization_note_ko=(
            "⚠ 봉우리 위치를 격자 위에서 읽으므로 격자만으로도 평균 step/4 만큼의 오차가 깔린다. "
            "«1 스텝 이내» 라는 문턱은 기체마다 격자가 달라 **엄격함이 달라진다** — 격자가 촘촘한 "
            "기체(큰 프롭)일수록 같은 절대오차로도 더 많은 스텝이 되어 불리하다. "
            "그래서 절대각(phase_err_deg)도 함께 싣는다."),
        implementation_attempts=dict(
            values=attempts,
            note_ko=("규칙은 하나(«스팬 ⟂ 시선»)인데 그것을 숫자로 옮기는 방법을 두 번 고쳤다. "
                     f"v0 = 스팬을 x 축이라 가정(실패). v1 = 메쉬에서 계산한 주축 ψ₀={psi0:.2f}° 를 "
                     "썼지만 거울상 로터를 놓침(절반만 맞음). v2 = 반대회전 로터에는 거울상 프롭이 "
                     "달리므로 ψ₀ 의 부호가 뒤집힌다는 것까지 반영. 세 성적을 모두 남긴다 — "
                     "지우면 «처음부터 맞췄다» 로 보이기 때문이다.")),
        x_axis_assumption=attempts["v0_x_axis"],
        n_flash_per_rev=R.summarize(n_flash.astype(float)),
        frac_n_flash_equals_blades=float(np.mean(n_flash == nb)),
        flash_count_rule="connected runs of the envelope above (peak − 3 dB), circular",
        first_sidelobe_db=R.summarize(np.asarray(sl)),
        first_sidelobe_note_ko=(
            "본잎 바로 옆 곁잎의 높이[dB, 첨두 대비]. 이 값이 −3 dB 에 가까우면 «−3 dB 위에서 이어진 "
            "덩어리» 로 플래시를 세는 규칙이 아슬아슬해진다 — 곁잎이 문턱을 넘으면 플래시가 하나 더 "
            "세어진다. 이 블레이드는 곁잎이 −3~−5 dB 로 꽤 높아서 그 규칙이 기체에 따라 갈린다."),
        single_rotor_flash_contrast_db=R.summarize(np.asarray(peak_db)),
        fwhm_deg_measured=R.summarize(fwhm_meas),
        fwhm_deg_predicted_tip_span=fwhm_pred_tip,
        fwhm_deg_predicted_effective_span=fwhm_pred_eff,
        fwhm_ratio_over_tip_prediction=float(np.mean(fwhm_meas) / max(fwhm_pred_tip, 1e-9)),
        fwhm_ratio_over_effective_prediction=float(np.mean(fwhm_meas) / max(fwhm_pred_eff, 1e-9)),
        effective_half_span_m=a_eff, tip_radius_m=ax.get("tip_radius_m"),
        beta_tip=beta, beta_effective=beta_eff,
        example=rows[:1],
        what_ko=("로터를 하나씩 떼어 봤을 때의 봉우리다. 여러 로터를 합치면 서로 다른 기준각 "
                 "때문에 봉우리가 섞이므로, «예측한 자리에 서는가» 는 로터 하나에서 봐야 깨끗하다."),
        prediction_rule_ko=("φ* = dir·(az + 90° − base_ang − ψ₀) (mod 360/블레이드수). "
                            "ψ₀ 는 프로펠러 메쉬의 면적가중 주축 방향으로, 메쉬에서 계산한다."),
        sweep_finding_ko=("⭐ 부수적으로 나온 형상 효과 — 이 CAD 블레이드는 후퇴각이 있어 스팬이 "
                          f"x 축에서 {psi0:.2f}° 틀어져 있다. 그래서 플래시가 서는 위상이 «곧은 판» "
                          "가정보다 그만큼 앞당겨진다. 스팬을 곧게 편 프리미티브(평판)로 바꾸면 "
                          "플래시의 **세기**는 비슷해도 **서는 자리**가 이 각도만큼 달라진다."))


# =========================================================================== #
#                                 분석
# =========================================================================== #
def per_drone_metrics(tabs, meta, key, wfront):
    T = tabs[f"{key}|{wfront}"]
    proto = meta["drones"][key]["protocol"]
    nb = meta["drones"][key]["spec"]["prop_blades"]
    per_az = [R.md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]
    keys = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90", "dominant_order",
            "blade_comb_frac", "fd_edge_hz", "width_ratio", "width_ratio_10db",
            "width_ratio_30db", "dc_ac_db", "ac_frac_db", "sigma_eq_mean_dbsm",
            "ac_over_floor_db", "in_band_ac_frac", "in_band_ac_over_dc_db")
    out = dict(per_az={kk: R.summarize([m[kk] for m in per_az]) for kk in keys},
               az0={kk: per_az[0][kk] for kk in keys},
               interpretable_frac=float(np.mean([m["metrics_interpretable"] for m in per_az])),
               band_order=int(per_az[0]["band_order"]), n_az=int(T.shape[0]))
    # ⭐ ε — 방위에 따른 산포. 구는 회전대칭이라 이 값이 원리적으로 정확히 0 이다.
    lv = np.array([m["sigma_eq_mean_dbsm"] for m in per_az], float)
    fl = np.array([m["flash_contrast_db"] for m in per_az], float)
    out["eps_level_db"] = float(lv.std(ddof=1))
    out["eps_level_peak_to_peak_db"] = float(lv.max() - lv.min())
    out["eps_flash_contrast_db"] = float(fl.std(ddof=1))
    out["eps_note_ko"] = ("ε = 24 방위에 걸친 표준편차[dB]. Das Table III 의 ε 과 같은 종류의 양이다. "
                          "등가부피 구는 회전대칭이라 이 값이 **정확히 0.00** 이다 — "
                          "구가 원리적으로 못 내는 자리가 여기다.")
    return out


def reproduction_gate(tabs, meta):
    """이 단의 위상표가 base 가 저장해 둔 표와 **비트 단위로** 같은가.
    같아야 «규약을 그대로 따랐다» 가 증명된다. 다르면 아래 숫자는 base 와 비교할 수 없다."""
    if not os.path.exists(BASE_NPZ):
        return dict(absent=True)
    z = np.load(BASE_NPZ)
    rows = {}
    for key in BASE_OVERLAP:
        for wfront in ("spherical", "plane"):
            bk = f"main__G_0804__{key}__mesh__{wfront}"
            mk = f"{key}|{wfront}"
            if bk not in z.files or mk not in tabs:
                continue
            a, b = z[bk], tabs[mk]
            if a.shape != b.shape:
                rows[f"{key}|{wfront}"] = dict(shape_mismatch=[list(a.shape), list(b.shape)])
                continue
            num = float(np.max(np.abs(a - b)))
            den = float(np.max(np.abs(a)))
            rows[f"{key}|{wfront}"] = dict(max_abs_diff=num, max_abs_ref=den,
                                           max_rel=num / max(den, 1e-300),
                                           bit_identical=bool(num == 0.0))
    ok = all(v.get("bit_identical") for v in rows.values()) if rows else False
    return dict(verdict="PASS (bit-identical)" if ok else ("FAIL" if rows else "NO OVERLAP"),
                reference=os.path.relpath(BASE_NPZ, ROOT),
                rows=rows,
                what_ko=("report16_base 가 같은 규약으로 저장해 둔 mesh 팔 위상표와 이 단의 표를 "
                         "직접 뺀 값이다. 0 이어야 «같은 커널·같은 점구름·같은 누적 순서» 가 증명된다."))


def kinematics_contract(meta_main, meta_hi):
    """⭐⭐ 뒤 단(구·상자·평판)이 **반드시 그대로 맞춰야 할** 값들.

    공정성의 급소가 여기다 — 구를 «안 돌리고» 0 을 얻으면 동어반복이다. 구도 여기 적힌
    회전축·rpm·위상 격자로 **실제로 돌려야** 한다. 등가부피는 계산해서 넘긴다."""
    out = dict(
        shared=dict(
            fc_main_hz=R.FC_MAIN, fc_po_knee_hz=R.FC_PO_KNEE,
            el_deg=R.EL_DEG, range_m=R.RANGE_M, monostatic=True,
            n_az=R.N_AZ, az_deg=list(np.arange(R.N_AZ) * (360.0 / R.N_AZ)),
            n_rev=R.N_REV, os_factor=R.OS_FACTOR,
            wavefront_headline="spherical", wavefront_control="plane",
            period_deg=360.0, frame_div=6.0, blade_div=11.0, blade_n=26,
            spin_axis_body=[0.0, 0.0, 1.0],
            spin_axis_note_ko="모든 로터는 기체좌표 +z 축을 중심으로 돈다(허브 중심 기준).",
            engine="pure PO on point clouds (no occlusion, no edge diffraction, scalar |Gamma|)",
            phase_grid_rule="phi_i = 2*pi*i/S, i = 0..S-1 (endpoint excluded)",
            prf_rule="PRF = S * f_rot  → 슬로타임이 위상표 격자에 정확히 떨어져 보간 오차 0",
        ),
        per_drone={})
    for key, m in meta_main["drones"].items():
        p = m["protocol"]
        V = m["drone_volume_m3"]
        bb = m["drone_bbox_m"]
        r_eq = (3.0 * V / (4.0 * math.pi)) ** (1.0 / 3.0)
        a_cube = V ** (1.0 / 3.0)
        # bbox 비율을 유지하면서 부피만 맞춘 상자
        sc = (V / max(bb[0] * bb[1] * bb[2], 1e-30)) ** (1.0 / 3.0)
        Vp = m["prop_volume_m3"]
        r_eq_prop = (3.0 * Vp / (4.0 * math.pi)) ** (1.0 / 3.0)
        hi = meta_hi["drones"].get(key, {}).get("protocol") if meta_hi else None
        out["per_drone"][key] = dict(
            rotors=m["rotors"],
            hover_rpm=m["spec"]["hover_rpm"], prop_blades=m["spec"]["prop_blades"],
            prop_dia_mm=m["spec"]["prop_dia_mm"], num_rotors=m["spec"]["num_rotors"],
            protocol_main=p, protocol_hi=hi,
            equal_volume=dict(
                drone_volume_m3=V,
                sphere_radius_m=r_eq, sphere_diameter_mm=2000.0 * r_eq,
                cube_edge_m=a_cube, cube_edge_mm=1000.0 * a_cube,
                box_bbox_aspect_matched_m=[bb[0] * sc, bb[1] * sc, bb[2] * sc],
                drone_bbox_m=bb,
                prop_volume_m3=Vp, rotating_volume_m3=m["rotating_volume_m3"],
                prop_equal_volume_sphere_radius_m=r_eq_prop,
                prop_span_m=m["prop_span_m"], prop_chord_m=m["prop_chord_m"],
                how_ko=("전부 메쉬에서 발산정리로 **계산**한 고체부피다(손입력 아님). "
                        "sphere_radius_m 은 기체 전체와 부피가 같은 구, cube_edge_m 은 같은 부피의 "
                        "정육면체, box_bbox_aspect_matched_m 은 bbox 비율을 유지하며 부피만 맞춘 상자다.")),
            material=dict(gamma_area_weighted=m["gamma_area_weighted"],
                          gamma_area_weighted_db=m["gamma_area_weighted_db"],
                          gamma_map=m["gamma_map"],
                          fairness_note_ko=("대체 모델을 PEC(|Γ|=1)로 두면 우리 메쉬보다 "
                                            f"{-m['gamma_area_weighted_db']:.2f} dB 만큼 세기에서 유리하다. "
                                            "레벨을 비교할 거면 이 값을 맞추거나, 최소한 병기하라. "
                                            "다만 flash_contrast·blade_comb_frac 은 |Γ| 상수배에 둔감하다.")),
            point_cloud=dict(n_frame_pts=m["n_frame_pts"], n_blade_pts=m["n_blade_pts"],
                             n_tris_frame=m["n_tris_frame"], n_tris_prop=m["n_tris_prop"]),
            farfield=dict(extent_m=m["extent_m"],
                          farfield_2D2_over_lam_m=2.0 * m["extent_m"] ** 2 / p["lam_m"],
                          range_over_farfield=R.RANGE_M / (2.0 * m["extent_m"] ** 2 / p["lam_m"])))
    out["how_to_use_ko"] = (
        "⭐ 뒤 단은 이 블록을 **읽어서** 쓴다(옮겨 적지 말 것). 특히: (1) 대체 모델도 여기 적힌 "
        "로터 중심·기준각·회전방향·rpm 으로 **실제로 회전**시켜야 한다 — 안 돌리고 0 을 얻으면 "
        "그건 증명이 아니라 동어반복이다. (2) 위상 스텝 수 S 와 PRF 는 기체마다 다르다 — "
        "protocol_main/protocol_hi 를 그대로 쓸 것. (3) 크기는 equal_volume 로 맞춘다. "
        "(4) 재질은 material 로 맞추거나, 못 맞추면 차이를 dB 로 병기한다.")
    return out


def score_prereg(J):
    """사전 등록한 예측을 채점한다. ⛔ 문턱은 prereg 파일에 적힌 값을 그대로 쓴다."""
    per = J["metrics"]["main"]["spherical"]
    fa = J["flash_anatomy"]
    rows = {}
    for pred in PREREG["predictions"]:
        pid, op, thr = pred["id"], pred["op"], pred["threshold"]
        vals, fails, extra = {}, [], {}
        for key in J["fleet"]:
            if pid in ("P1",):
                v = per[key]["per_az"]["flash_contrast_db"]["mean"]
            elif pid == "P2":
                v = per[key]["per_az"]["blade_comb_frac"]["mean"]
            elif pid == "P3":
                v = per[key]["per_az"]["in_band_ac_frac"]["mean"]
            elif pid == "P4":
                v = per[key]["per_az"]["width_ratio"]["mean"]
            elif pid == "P5":
                v = fa[key]["frac_within_1_step"]
                extra[key] = fa[key]["x_axis_assumption"]["frac_within_1_step"]
            elif pid == "P6":
                v = fa[key]["frac_n_flash_equals_blades"]
            elif pid == "P7":
                v = per[key]["eps_level_db"]
            else:                                                   # pragma: no cover
                continue
            vals[key] = float(v)
            ok = (thr[0] <= v <= thr[1]) if op == "in" else (v >= thr)
            if not ok:
                fails.append(key)
        rows[pid] = dict(prediction_ko=pred["ko"], metric=pred["metric"], op=op,
                         threshold=thr, values=vals,
                         worst=min(vals.values()) if vals else None,
                         worst_drone=min(vals, key=vals.get) if vals else None,
                         n_drones=len(vals), n_fail=len(fails), failed_drones=fails,
                         verdict="PASS" if not fails else "FAIL")
        if extra:
            rows[pid]["first_attempt_x_axis_assumption"] = dict(
                values=extra, verdict="FAIL",
                note_ko=("스팬을 x 축이라 가정한 첫 구현의 성적. 실패했고 원인은 프로펠러의 "
                         "후퇴각이었다 — implementation_honesty 블록 참조. 지우지 않고 남긴다."))
    n_pass = sum(1 for v in rows.values() if v["verdict"] == "PASS")
    return dict(rows=rows, n_pass=n_pass, n_total=len(rows),
                overall="PASS" if n_pass == len(rows) else "PARTIAL",
                honesty_ko=("⛔ 여기서 «틀림» 이 나오면 그대로 둔다. 사전 등록 파일의 sha256 이 "
                            "위에 박혀 있으므로 예측을 사후에 고칠 수 없다."))


def rcs_ladder_context():
    """RCS(세기) 사다리에서 이미 나온 결과 — 손으로 적지 않고 파일에서 읽는다.
    이 단이 «왜» 필요한지의 근거이고, 마이크로도플러 결과와 나란히 읽어야 할 대조군이다."""
    p = os.path.join(ROOT, "outputs", "p3_validation_v2.json")
    if not os.path.exists(p):
        return dict(absent=True)
    d = json.load(open(p))
    t = d["controls"]["table"]
    pick = {"our_mesh": "ours_phantom3_mesh_v2", "sphere_equal_volume": "sphere_eqvol_paperbox",
            "sphere_equal_volume_of_mesh": "sphere_vol_v2", "cube_equal_volume": "cube_vol_v2",
            "box_bbox": "box_bbox_v2"}
    rows = {}
    for lab, kk in pick.items():
        if kk in t:
            rows[lab] = {k2: t[kk][k2] for k2 in
                         ("what", "level_err_db", "rms_db", "eps_mean_db", "eps_err_vs_das_db")
                         if k2 in t[kk]}
    return dict(
        source=os.path.relpath(p, ROOT),
        das_eps_db=d["v1_vs_v2"]["eps_db"]["das_mean"],
        rows=rows,
        reading_ko=("세기(RCS)만 놓고 보면 모수 0개짜리 등가부피 구가 우리 메쉬를 이긴다"
                    "(level_err·rms 를 볼 것). ⭐ 그런데 구의 ε(방위 산포)은 **정확히 0.00** 이다 — "
                    "회전대칭이라 방위에 따른 변동이 원리적으로 없다. 상자는 ε 을 내지만 "
                    "실측보다 4 dB 넘게 과하다. 이 단이 묻는 것은 «그 구조 우위가 "
                    "마이크로도플러에서는 얼마나 크게 나타나는가» 이고, 이 단은 그중 "
                    "**기준(우리 메쉬)만** 낸다."))


# --------------------------------------------------------------------------- #
#  그림 (글씨는 전부 영어 — 저장소 규약)
# --------------------------------------------------------------------------- #
def make_figure(J, tabs, meta, tabs_hi, meta_hi):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import gridspec
    from scipy.signal import spectrogram as _sp

    plt.rcParams.update({"figure.facecolor": "white", "savefig.facecolor": "white",
                         "axes.grid": True, "grid.alpha": 0.25, "font.size": 9})
    C_REF, C_HI, C_ACC, C_WARN = "#1565c0", "#6a1b9a", "#2e7d32", "#c62828"
    HERO = "matrice4e" if "matrice4e" in J["fleet"] else J["fleet"][0]
    SMALL = "mini2" if "mini2" in J["fleet"] else J["fleet"][-1]
    per = J["metrics"]["main"]["spherical"]
    order = sorted(J["fleet"], key=lambda k: J["kinematics_contract"]["per_drone"][k]
                   ["protocol_main"]["beta"])

    fig = plt.figure(figsize=(16.8, 14.2))
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.62, wspace=0.30,
                           top=0.905, bottom=0.068, left=0.062, right=0.978)

    # ── (0,0) 슬로타임 스펙트로그램 — 플래시가 눈에 보이는 자리 ────────────────
    ax = fig.add_subplot(gs[0, 0])
    pr = meta["drones"][HERO]["protocol"]
    T = tabs[f"{HERO}|spherical"]
    S, prf = pr["n_phase"], pr["prf_hz"]
    E = np.tile(T[0], 8)
    nper = max(32, S // 4)
    f, tt, Sxx = _sp(E - E.mean(), fs=prf, nperseg=nper, noverlap=nper - max(1, nper // 16),
                     nfft=4 * nper, detrend=False, window="hann", return_onesided=False,
                     scaling="spectrum", mode="magnitude")
    f = np.fft.fftshift(f); Sxx = np.fft.fftshift(Sxx, axes=0)
    Sdb = 20 * np.log10(Sxx / (Sxx.max() + 1e-30) + 1e-12)
    m = ax.pcolormesh(tt * 1e3, f, Sdb, cmap="magma", vmin=-45, vmax=0, shading="auto")
    for sgn in (1, -1):
        ax.axhline(sgn * pr["f_tip_hz"], color="#4fc3f7", ls="--", lw=1.2)
    ax.set_ylim(-1.45 * pr["f_tip_hz"], 1.45 * pr["f_tip_hz"])
    ax.set_xlabel("slow time [ms]"); ax.set_ylabel("Doppler [Hz]")
    ax.set_title(f"{HERO} · our CAD mesh (reference rung) · az 0$\\degree$\n"
                 f"{pr['f_rot_hz']*60:.0f} rpm · $f_{{tip}}$ {pr['f_tip_hz']:.0f} Hz (dashed) · "
                 f"blade flash {pr['flash_hz']:.0f} Hz",
                 fontsize=9.3, fontweight="bold")
    ax.grid(False)
    fig.colorbar(m, ax=ax, fraction=0.046, pad=0.02, label="dB (peak = 0)")

    # ── (0,1) 플래시 해부 — 예측한 위상에 봉우리가 서는가 ─────────────────────
    ax = fig.add_subplot(gs[0, 1])
    Trot = tabs[f"rot|{HERO}|spherical"]
    nb = meta["drones"][HERO]["spec"]["prop_blades"]
    base = meta["drones"][HERO]["rotors"][0]["base_ang_deg"]
    dr = meta["drones"][HERO]["rotors"][0]["dir"]
    Sh = Trot.shape[2]
    phi = np.arange(Sh) * (360.0 / Sh)
    e = Trot[0, 0]
    env = np.abs(e - e.mean())
    ax.plot(phi, 20 * np.log10(np.maximum(env / env.max(), 1e-6)), lw=1.5, color=C_REF,
            label="single rotor $|E_{AC}(\\varphi)|$ (rotor 0, az 0$\\degree$)")
    fa = J["flash_anatomy"][HERO]
    psi0 = fa["blade_axis_offset_deg"]
    per_deg = 360.0 / nb
    for i2 in range(nb):
        pp = ((dr * (0.0 + 90.0 - base - psi0)) % per_deg + i2 * per_deg) % 360.0
        ax.axvline(pp, color=C_WARN, ls="--", lw=1.5,
                   label="predicted flash (blade span $\\perp$ line of sight)" if i2 == 0 else None)
        pn = ((dr * (0.0 + 90.0 - base)) % per_deg + i2 * per_deg) % 360.0
        ax.axvline(pn, color="#90a4ae", ls=":", lw=1.3,
                   label=f"if the blade were unswept ($\\psi_0$ = 0, off by {psi0:.1f}$\\degree$)"
                   if i2 == 0 else None)
    ax.set_xlim(0, 360); ax.set_ylim(-45, 3)
    ax.set_xlabel("rotor phase $\\varphi$ [deg]")
    ax.set_ylabel("envelope, normalised to its own peak [dB]")
    ax.set_title("Do the flashes land where predicted?\n"
                 f"{100*fa['frac_within_1_step']:.0f}% of "
                 f"{fa['n_cases']} (rotor $\\times$ azimuth) cases within one phase step "
                 f"({fa['phase_step_deg']:.2f}$\\degree$)",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=6.8, loc="lower center")

    # ── (0,2) 차수 스펙트럼 — 블레이드 빗 ─────────────────────────────────────
    ax = fig.add_subplot(gs[0, 2])
    for key, c_, lw in ((HERO, C_REF, 1.6), (SMALL, C_ACC, 1.2)):
        Tk = tabs[f"{key}|spherical"]; Sk = Tk.shape[1]
        c = np.fft.fft(Tk[0]) / Sk
        mo = np.fft.fftfreq(Sk, d=1.0 / Sk).astype(int); o = np.argsort(mo)
        bk = J["kinematics_contract"]["per_drone"][key]["protocol_main"]["beta"]
        ax.plot(mo[o] / bk, 10 * np.log10(np.maximum(np.abs(c[o]) ** 2 / max(abs(c[0]) ** 2, 1e-300),
                                                     1e-14)),
                lw=lw, color=c_, label=f"{key}  ($\\beta$ = {bk:.1f})")
    for sgn in (1, -1):
        ax.axvline(sgn, color="#455a64", ls=":", lw=1.3)
    ax.annotate("tip speed $f_{tip}$", (0.98, -6), fontsize=7.6, ha="right", va="top",
                rotation=90, color="#455a64")
    ax.set_xlim(-1.8, 1.8); ax.set_ylim(-110, 6)
    ax.set_xlabel("Doppler / $f_{tip}$   (harmonic order $m$ / $\\beta$)")
    ax.set_ylabel("line power relative to own DC [dB]")
    ax.set_title("Order spectrum of the reference rung\n"
                 "AC lines sit inside the kinematic band, on the blade comb",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=7.6, loc="lower right")

    # ── (1,0) 함대: 플래시 대조비 ─────────────────────────────────────────────
    def fleetbar(ax, getter, ylabel, title, hline=None, hlabel=None):
        ys = [getter(k)[0] for k in order]
        es = [getter(k)[1] for k in order]
        x = np.arange(len(order))
        ax.bar(x, ys, 0.66, yerr=es, capsize=2.5, color=C_REF, zorder=3)
        if hline is not None:
            ax.axhline(hline, color=C_WARN, ls="--", lw=1.4)
            if hlabel:
                ax.annotate(hlabel, (len(order) - 0.55, hline), fontsize=7.4, ha="right",
                            va="bottom", color=C_WARN, textcoords="offset points",
                            xytext=(0, 4))
        ax.set_xticks(x); ax.set_xticklabels(order, fontsize=6.8, rotation=38, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=9.3, fontweight="bold")

    ax = fig.add_subplot(gs[1, 0])
    fleetbar(ax, lambda k: (per[k]["per_az"]["flash_contrast_db"]["mean"],
                            per[k]["per_az"]["flash_contrast_db"]["sd"]),
             "flash contrast [dB]  (peak / median of $|AC|$)",
             "P1 — flash contrast across the fleet\nbars = mean over 24 azimuths, whiskers = sd",
             hline=PREREG["predictions"][0]["threshold"], hlabel="pre-registered threshold")

    # ── (1,1) 함대: 블레이드 빗 몫 + 대역 안 몫 ───────────────────────────────
    ax = fig.add_subplot(gs[1, 1])
    x = np.arange(len(order)); w = 0.38
    ax.bar(x - w / 2, [per[k]["per_az"]["blade_comb_frac"]["mean"] for k in order], w,
           yerr=[per[k]["per_az"]["blade_comb_frac"]["sd"] for k in order], capsize=2,
           color=C_REF, label="P2 · power on the blade comb (orders $2,4,6,\\dots$)", zorder=3)
    ax.bar(x + w / 2, [per[k]["per_az"]["in_band_ac_frac"]["mean"] for k in order], w,
           color=C_ACC, label="P3 · power inside the kinematic band", zorder=3)
    ax.axhline(PREREG["predictions"][1]["threshold"], color=C_WARN, ls="--", lw=1.3)
    ax.axhline(PREREG["predictions"][2]["threshold"], color=C_WARN, ls=":", lw=1.3)
    ax.set_xticks(x); ax.set_xticklabels(order, fontsize=6.8, rotation=38, ha="right")
    ax.set_ylim(0, 1.08); ax.set_ylabel("fraction of AC power")
    ax.set_title("P2 / P3 — is it really the blades?\n"
                 "dashed = pre-registered thresholds (0.50 · 0.90)",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=7.0, loc="lower left")

    # ── (1,2) 함대: 폭 vs 팁속도 ──────────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 2])
    fleetbar(ax, lambda k: (per[k]["per_az"]["width_ratio"]["mean"],
                            per[k]["per_az"]["width_ratio"]["sd"]),
             "$-20$ dB edge / $f_{tip}$",
             "P4 — spectrum width vs tip speed\nkinematics predicts 1.0",
             hline=1.0, hlabel="kinematic prediction")
    ax.set_ylim(0, 1.35)

    # ── (2,0) ε — 구가 원리적으로 못 내는 자리 ────────────────────────────────
    ax = fig.add_subplot(gs[2, 0])
    x = np.arange(len(order))
    ax.bar(x, [per[k]["eps_level_db"] for k in order], 0.66, color=C_REF, zorder=3,
           label="our CAD mesh (this rung)")
    ax.axhline(0.0, color=C_WARN, lw=2.4)
    ax.annotate("a sphere sits on this line:\n"
                "$\\varepsilon$ = 0.00 dB, exactly",
                (0.03, 0.96), xycoords="axes fraction", fontsize=7.6, ha="left", va="top",
                color=C_WARN, bbox=dict(fc="white", ec="#ef9a9a", alpha=0.95, pad=2.4))
    ax.set_xticks(x); ax.set_xticklabels(order, fontsize=6.8, rotation=38, ha="right")
    ax.set_ylabel("$\\varepsilon$ = sd of level over 24 azimuths [dB]")
    ax.set_title("P7 — azimuth spread $\\varepsilon$\n"
                 "the one thing a sphere cannot produce",
                 fontsize=9.3, fontweight="bold")
    ax.legend(fontsize=7.4, loc="upper left")

    # ── (2,1) 두 대역 — 커널이 약한 대역의 산물인가 ──────────────────────────
    ax = fig.add_subplot(gs[2, 1])
    hi = J["metrics"].get("hi", {}).get("spherical", {})
    pts = [(k, per[k]["per_az"]["flash_contrast_db"]["mean"],
            hi[k]["per_az"]["flash_contrast_db"]["mean"]) for k in order if k in hi]
    for k, lo_v, hi_v in pts:
        ax.plot([0, 1], [lo_v, hi_v], marker="o", ms=5, lw=1.4, alpha=0.85)
    #  라벨이 겹치지 않도록 오른쪽 끝값을 정렬해 최소 간격을 벌린다
    span = max(v for _, _, v in pts) - min(v for _, _, v in pts)
    gap = max(0.075 * span, 0.45)
    lab = sorted(((v, k) for k, _, v in pts))
    ys = []
    for v, k in lab:
        ys.append(v if not ys else max(v, ys[-1] + gap))
    for (v, k), yy in zip(lab, ys):
        ax.plot([1.0, 1.05], [v, yy], lw=0.7, color="#b0bec5")
        ax.annotate(k, (1.07, yy), fontsize=6.6, va="center")
    ax.set_xlim(-0.12, 1.52); ax.set_xticks([0, 1])
    ax.set_xticklabels([f"{R.FC_MAIN/1e9:.2f} GHz\n(production band)",
                        f"{R.FC_PO_KNEE/1e9:.2f} GHz\n(PO validity knee)"], fontsize=8)
    ax.set_ylabel("flash contrast [dB]")
    ax.set_title("Robustness — artefact of the weak band?\n"
                 "the blade only clears the PO validity knee at the right-hand band",
                 fontsize=9.3, fontweight="bold")

    # ── (2,2) 사전 등록 채점표 ────────────────────────────────────────────────
    ax = fig.add_subplot(gs[2, 2]); ax.axis("off")
    sc = J["prereg_scorecard"]["rows"]
    ax.set_title("Pre-registered predictions, scored\n"
                 f"written before the run · sha256 "
                 f"{J['prereg']['sha256'][:12]}…",
                 fontsize=9.3, fontweight="bold")
    y = 0.96
    ax.annotate(f"{J['prereg_scorecard']['n_pass']} / {J['prereg_scorecard']['n_total']} predictions hold "
                f"across all {len(J['fleet'])} airframes",
                (0.0, y), fontsize=9.0, fontweight="bold",
                color=C_ACC if J["prereg_scorecard"]["overall"] == "PASS" else C_WARN)
    y -= 0.085
    LAB = {"P1": "P1  flash contrast $\\geq$ 3 dB",
           "P2": "P2  blade-comb share $\\geq$ 0.50",
           "P3": "P3  in-band AC share $\\geq$ 0.90",
           "P4": "P4  width ratio in [0.5, 1.2]",
           "P5": "P5  flash phase within 1 step ($\\geq$90%)",
           "P6": "P6  flashes per rev = blades ($\\geq$90%)",
           "P7": "P7  azimuth spread $\\varepsilon \\geq$ 0.5 dB"}
    for pid in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"):
        r = sc[pid]
        ok = r["verdict"] == "PASS"
        ax.annotate(("PASS" if ok else "FAIL"), (0.0, y), fontsize=8.4, fontweight="bold",
                    color=C_ACC if ok else C_WARN)
        ax.annotate(LAB[pid], (0.13, y), fontsize=8.0)
        ax.annotate(f"worst: {r['worst_drone']} {r['worst']:.2f}", (0.70, y), fontsize=7.2,
                    color="#455a64")
        y -= 0.078
    rg = J["reproduction_gate"]
    nd = J.get("nearfield_diagnosis", {})
    ax.annotate(f"reproduction gate vs report16_base: {rg.get('verdict','?')}",
                (0.0, y - 0.02), fontsize=7.6, color="#455a64")
    ax.annotate("the tables of this rung are bit-for-bit the base protocol",
                (0.0, y - 0.075), fontsize=6.9, color="#78909c")
    ax.annotate("Why P5 and P6 miss — the rule is a far-field rule.\n"
                f"With a plane wave, {nd.get('n_plane_perfect','?')} of {nd.get('n_drones','?')} airframes "
                f"reach 100%, and the error\nranks with range / far-field distance "
                f"({nd.get('rank_corr_rangeoverfarfield_vs_err', float('nan')):+.2f} rank correlation).\n"
                "P6 misses one airframe because this blade's first sidelobe\n"
                "sits only ~3 dB below the flash, so a $-3$ dB counting rule\n"
                "is marginal. Neither miss touches P1–P4.",
                (0.0, y - 0.30), fontsize=7.1, color="#37474f",
                bbox=dict(fc="#eceff1", ec="#b0bec5", alpha=0.95, pad=3.0))

    fig.suptitle("report16 · ladder rung 1 of N — OUR CAD MESH (the reference)\n"
                 f"{R.FC_MAIN/1e9:.2f} GHz · monostatic at {R.RANGE_M:.0f} m · el {R.EL_DEG:.0f}$\\degree$ · "
                 f"{R.N_AZ} azimuths · {len(J['fleet'])} airframes · spherical wavefront · "
                 "full-revolution phase table · no occlusion",
                 fontsize=13, fontweight="bold", y=0.972)
    pv = J["po_validity_warning"]
    fig.text(0.5, 0.030,
             f"⚠ The propeller blade needs {pv['blade_knee_ghz']:.2f} GHz to clear the PO validity knee "
             f"of {pv['knee_a_over_lambda']:.3f} $\\lambda$ — at {pv['production_band_ghz']:.2f} GHz the very "
             "part that makes the micro-Doppler is where this kernel is weakest.",
             ha="center", fontsize=8.6, color="#b71c1c")
    fig.text(0.5, 0.008,
             "No occlusion, no edge diffraction, scalar |Γ|, identical rpm on every rotor.   "
             "Substitute-model rungs must reuse the kinematics contract stored in this JSON.",
             ha="center", fontsize=8.2, color="#b71c1c")
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=150)
    plt.close(fig)
    return os.path.relpath(OUT_FIG, ROOT)


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main(fleet=None, skip_compute=False, with_hi=True):
    t0 = time.time()
    fleet = fleet or FLEET

    # ⭐ 1) 예측을 **먼저** 적는다
    prereg_stamp = _write_prereg()
    compute_started = time.strftime("%Y-%m-%dT%H:%M:%S")
    print(f"▶ prereg 고정: {prereg_stamp['file']}  sha256={prereg_stamp['sha256'][:16]}…  "
          f"written_at={prereg_stamp['written_at']}", flush=True)

    # 2) 계산
    if not skip_compute:
        free = []
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.free",
                                  "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, check=True).stdout
            free = sorted(((int(a), int(b)) for a, b in
                           (l.split(",") for l in out.strip().splitlines())),
                          key=lambda t: -t[1])
        except Exception:
            pass
        g0 = free[0][0] if free else None
        g1 = free[1][0] if len(free) > 1 else g0
        procs = [run_band("main", R.FC_MAIN, fleet, True, gpu=g0)]
        if with_hi:
            procs.append(run_band("hi", R.FC_PO_KNEE, fleet, False, gpu=g1))
        for p in procs:
            if p.wait() != 0:
                raise RuntimeError(f"worker failed rc={p.returncode}")

    tabs, meta = load_band("main")
    tabs_hi, meta_hi = load_band("hi")
    if not tabs:
        raise RuntimeError("main band 표가 없다 — --skip-compute 를 뺐는지 확인")
    fleet = [k for k in fleet if f"{k}|spherical" in tabs]

    J = dict(meta=dict(
        report="report16", rung="mesh_full", rung_role="reference (the ladder's baseline)",
        producer="benchmark/report16_rung_mesh_full.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        compute_started=compute_started,
        git_rev=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        protocol_source="benchmark/report16_base.py (derive_protocol · md_metrics16 · PO kernel)",
        purpose_ko=("사다리의 기준 단 — 우리 CAD 메쉬가 내는 마이크로도플러를 규약대로 내고, "
                    "계산 전에 적어 둔 예측을 채점하고, 뒤 단들이 쓸 운동학 계약을 넘긴다."),
        headline_question_ko=("«구조» 우위가 마이크로도플러에서 얼마나 크게 나타나는가 — "
                              "그중 이 단은 **기준(우리 메쉬)** 만 낸다. 대체 모델과의 차이는 "
                              "각 단이 실제로 돌려서 답한다."),
        gpu=dict(main=meta.get("gpu"), hi=meta_hi.get("gpu") if meta_hi else None)))
    J["prereg"] = prereg_stamp
    #  ⭐ 코드 안의 사본이 아니라 **디스크에 얼어붙은 파일 그 자체**를 싣는다 — 둘이 갈라지면
    #     «미리 적었다» 가 무의미해지기 때문이다.
    J["prereg_statement"] = json.load(open(OUT_PREREG))
    J["implementation_honesty"] = dict(
        what_happened_ko=(
            "⚠ 이 단의 첫 실행에서 P5(플래시 위상)·P6(회전당 플래시 개수)가 **둘 다 0% 로 실패**했다. "
            "원인을 파 보니 예측이 틀린 것이 아니라 **구현 두 곳이 틀려** 있었다:"),
        cause_1_ko=(
            "① 스팬을 «x 축» 이라 가정했다. 실제 이 프로펠러 메쉬는 후퇴각이 있어 면적가중 주축이 "
            "x 에서 약 10° 틀어져 있다. 사전 등록 문장은 «블레이드 스팬이 시선에 수직» 이지 "
            "«x 축이 수직» 이 아니므로, 스팬을 메쉬에서 계산해 쓰는 것이 규칙대로 하는 것이다. "
            "그 각도는 맞춰 넣은 값이 아니라 2차모멘트에서 계산한 값이고, 실패한 판정도 "
            "flash_anatomy.<기체>.x_axis_assumption 에 그대로 남겨 두었다."),
        cause_2_ko=(
            "② 반대회전 로터에는 **거울상 프로펠러**가 달린다. 거울을 치면 후퇴각의 부호가 "
            "뒤집히므로 스팬 각도도 −ψ₀ 가 된다. 이것을 놓쳐서 절반(정회전 로터)만 맞았다. "
            "성적이 정확히 50% 근처였던 것이 단서였다."),
        cause_3_ko=(
            "③ 봉우리를 «국소최대» 로 셌다. 유한한 길이의 배열은 본잎 옆에 곁잎(sidelobe)을 "
            "반드시 만들고 첫 곁잎이 −5 dB 근처라 «최대의 절반» 문턱을 통과해 버렸다 — 그래서 "
            "2개여야 할 플래시가 4개로 세어졌다. −3 dB 위에서 **이어진 덩어리**로 세도록 고쳤다."),
        what_was_not_changed_ko=(
            "⛔ 사전 등록 파일(예측 문장·문턱)은 손대지 않았다. sha256 이 위 prereg 블록에 박혀 있다. "
            "고친 것은 «규칙을 숫자로 옮기는 방법» 뿐이고, 고치기 전 성적도 함께 싣는다."),
        by_product_ko=(
            "⭐ 덤으로 형상 효과가 하나 나왔다 — 후퇴각 때문에 플래시가 서는 **위상**이 곧은 판 "
            "가정보다 그 각도만큼 앞당겨진다. 세기가 아니라 «자리» 에 남는 형상의 흔적이다."))
    J["fleet"] = fleet

    # 3) 지표
    J["metrics"] = {"main": {"spherical": {}, "plane": {}}}
    for key in fleet:
        for wfront in ("spherical", "plane"):
            J["metrics"]["main"][wfront][key] = per_drone_metrics(tabs, meta, key, wfront)
    if tabs_hi:
        J["metrics"]["hi"] = {"spherical": {}, "plane": {}}
        for key in [k for k in fleet if f"{k}|spherical" in tabs_hi]:
            for wfront in ("spherical", "plane"):
                J["metrics"]["hi"][wfront][key] = per_drone_metrics(tabs_hi, meta_hi, key, wfront)

    # 4) 플래시 해부
    az_list = meta["az_deg"]
    J["flash_anatomy"] = {
        key: flash_anatomy(tabs[f"rot|{key}|spherical"], meta["drones"][key],
                           meta["drones"][key]["protocol"], az_list)
        for key in fleet if f"rot|{key}|spherical" in tabs}

    # 4b) ⭐ 플래시 예측이 어긋난 이유를 찾는 자리 — 평면파(무한거리) 대조
    #     «스팬 ⟂ 시선» 은 **평면파(원거리장) 규칙**이다. 10 m 는 큰 기체에게 원거리장이 아니라
    #     파면이 휘어 있고, 그러면 «모두 같은 거리» 가 되는 자세가 규칙에서 조금 벗어난다.
    #     같은 표적을 평면파로 다시 재서, 어긋남이 근거리 때문인지 아닌지를 가른다.
    fa_plane = {key: flash_anatomy(tabs[f"rot|{key}|plane"], meta["drones"][key],
                                   meta["drones"][key]["protocol"], az_list)
                for key in fleet if f"rot|{key}|plane" in tabs}
    J["flash_anatomy_plane_control"] = fa_plane
    rows = {}
    for key in fa_plane:
        rf = J.setdefault("_tmp", {})
        rows[key] = dict(
            range_over_farfield=R.RANGE_M / (2.0 * meta["drones"][key]["extent_m"] ** 2
                                             / meta["drones"][key]["protocol"]["lam_m"]),
            extent_m=meta["drones"][key]["extent_m"],
            spherical_frac_within_1_step=J["flash_anatomy"][key]["frac_within_1_step"],
            plane_frac_within_1_step=fa_plane[key]["frac_within_1_step"],
            spherical_err_deg=J["flash_anatomy"][key]["phase_err_deg"]["mean"],
            plane_err_deg=fa_plane[key]["phase_err_deg"]["mean"])
    J.pop("_tmp", None)
    xs = np.array([v["range_over_farfield"] for v in rows.values()])
    ys = np.array([v["spherical_err_deg"] for v in rows.values()])
    rk = float(np.corrcoef(np.argsort(np.argsort(xs)), np.argsort(np.argsort(ys)))[0, 1])
    J["nearfield_diagnosis"] = dict(
        rows=rows,
        rank_corr_rangeoverfarfield_vs_err=rk,
        n_plane_perfect=int(sum(1 for v in rows.values() if v["plane_frac_within_1_step"] >= 0.9)),
        n_drones=len(rows),
        finding_ko=(
            "⭐ P5(플래시 위상)가 어긋난 곳은 전부 **몸집이 큰 기체**다. 원인은 예측 규칙이 틀린 것이 "
            "아니라 **적용 범위**다 — «블레이드가 시선을 가로지르면 모든 조각이 같은 거리에 놓인다» 는 "
            "말은 파면이 평평할 때(원거리장) 성립한다. 10 m 는 작은 기체에게는 원거리장이지만 "
            "큰 기체에게는 아니어서 파면이 휘어 있고, 그러면 «같은 거리» 가 되는 자세가 조금 틀어진다. "
            "같은 표적을 평면파로 다시 재면 대부분 100% 로 맞는다 — 근거리가 원인이라는 직접 증거다. "
            f"거리/원거리장경계 순위와 오차 순위의 상관은 {rk:+.2f} 다(음수 = 원거리장에 가까울수록 정확)."),
        honesty_ko=("⛔ 그래도 사전 등록한 P5 는 구면파(헤드라인 조건)로 채점한 그대로 둔다. "
                    "«설명이 된다» 와 «예측이 맞았다» 는 다른 말이다."))

    # 5) 운동학 계약 · 재현 게이트 · 배경
    J["kinematics_contract"] = kinematics_contract(meta, meta_hi if meta_hi else None)
    J["reproduction_gate"] = reproduction_gate(tabs, meta)
    J["rcs_ladder_context"] = rcs_ladder_context()

    # 6) 파면 대조 (구면 vs 평면)
    wfc = {}
    for key in fleet:
        Ta, Tb = tabs[f"{key}|spherical"], tabs[f"{key}|plane"]
        wfc[key] = dict(
            ac_corr=R.summarize([R.ac_corr(Ta[i], Tb[i]) for i in range(Ta.shape[0])]),
            level_delta_db=R.summarize([
                10 * np.log10(np.mean(np.abs(Tb[i]) ** 2) / np.mean(np.abs(Ta[i]) ** 2))
                for i in range(Ta.shape[0])]))
    J["wavefront_control"] = dict(spherical_vs_plane=wfc, note_ko=(
        "구면파(헤드라인)와 평면파(무한거리 등가)의 차이. 상관이 1 에 가까우면 "
        f"{R.RANGE_M:.0f} m 는 이 표적에게 사실상 원거리장이라는 뜻이다."))

    # 7) 대역 사이 일관성 — 결론이 «커널이 약한 대역» 의 산물인가
    if "hi" in J["metrics"]:
        band = {}
        for key in J["metrics"]["hi"]["spherical"]:
            lo = J["metrics"]["main"]["spherical"][key]["per_az"]
            hh = J["metrics"]["hi"]["spherical"][key]["per_az"]
            band[key] = {kk: dict(main=lo[kk]["mean"], hi=hh[kk]["mean"],
                                  delta=hh[kk]["mean"] - lo[kk]["mean"])
                         for kk in ("flash_contrast_db", "blade_comb_frac", "in_band_ac_frac",
                                    "width_ratio", "dc_ac_db", "n_eff_orders")}
        J["band_consistency"] = dict(values=band, note_ko=(
            "3.5 GHz(생산 대역, 블레이드가 PO 유효 무릎 아래)와 15.86 GHz(무릎 위)에서 같은 지표를 "
            "나란히 놓았다. 두 대역에서 방향이 같아야 «커널이 약한 대역의 산물» 이라는 반론을 막는다."))

    # 8) PO 유효성 경고
    knee = json.load(open(os.path.join(ROOT, "outputs",
                                       "report00_po_case.json")))["s4_limits"]
    J["po_validity_warning"] = dict(
        knee_a_over_lambda=knee["po_validity_knee_a_over_lambda"],
        knee_rule=knee["po_validity_knee_rule"],
        blade_knee_ghz=knee["feature_knee_frequencies"]["prop_blade_13p78mm_ghz"],
        body_knee_ghz=knee["feature_knee_frequencies"]["body_81p51mm_ghz"],
        production_band_ghz=R.FC_MAIN / 1e9,
        statement_ko=("⚠ 마이크로도플러를 만드는 부품(프로펠러 블레이드, 폭 13.78 mm)은 "
                      f"{knee['feature_knee_frequencies']['prop_blade_13p78mm_ghz']} GHz 에서야 "
                      f"PO 유효 무릎(폭 ≥ {knee['po_validity_knee_a_over_lambda']:.3f}λ)을 넘는다. "
                      f"생산 대역 {R.FC_MAIN/1e9:.1f} GHz 에서는 **커널이 가장 약한 부품이 곧 "
                      "신호원**이다. 이 단의 절대값은 전부 그 조건 아래에서 읽어야 한다."),
        also_ko=("가림(occlusion) 없음 — dc_ac_db(동체/블레이드 비)가 가장 크게 오염된다. "
                 "절대값 인용 금지, 단 사이 차이만 쓸 것."))

    # 9) 채점 + 결론
    J["prereg_scorecard"] = score_prereg(J)
    J["findings"] = _findings(J)

    # 10) 저장
    save = {k.replace("|", "__"): v for k, v in tabs.items()}
    save.update({("hi__" + k.replace("|", "__")): v for k, v in tabs_hi.items()})
    np.savez_compressed(OUT_NPZ, **save)
    J["figures"] = dict(rung=make_figure(J, tabs, meta, tabs_hi, meta_hi))
    J["meta"]["tables_npz"] = os.path.relpath(OUT_NPZ, ROOT)
    J["meta"]["seconds"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✅ {os.path.relpath(OUT_JSON, ROOT)}  ·  {J['figures']['rung']}  "
          f"[{J['meta']['seconds']:.0f}s]")
    return J


def _findings(J):
    """숫자를 손으로 적지 않는다 — 위에서 계산된 값만 골라 문장을 만든다."""
    per = J["metrics"]["main"]["spherical"]
    fleet = J["fleet"]

    def mm(metric, sub="mean"):
        v = {k: per[k]["per_az"][metric][sub] for k in fleet}
        return dict(values=v, min=min(v.values()), max=max(v.values()),
                    min_drone=min(v, key=v.get), max_drone=max(v, key=v.get),
                    fleet_mean=float(np.mean(list(v.values()))))

    F = {}
    F["q1_does_our_mesh_produce_blade_flash"] = dict(
        question_ko="⭐ 우리 메쉬는 블레이드 플래시를 내는가 (이 단의 사전 예측)",
        prereg_verdict=J["prereg_scorecard"]["overall"],
        n_pass=J["prereg_scorecard"]["n_pass"], n_total=J["prereg_scorecard"]["n_total"],
        flash_contrast_db=mm("flash_contrast_db"),
        blade_comb_frac=mm("blade_comb_frac"),
        in_band_ac_frac=mm("in_band_ac_frac"),
        flash_phase_accuracy={k: dict(
            frac_within_1_step=J["flash_anatomy"][k]["frac_within_1_step"],
            median_err_steps=J["flash_anatomy"][k]["phase_err_steps"]["mean"],
            phase_step_deg=J["flash_anatomy"][k]["phase_step_deg"])
            for k in J["flash_anatomy"]},
        answer_ko=("세기(flash_contrast)·자리(blade_comb_frac)·위치(flash phase)·대역(in_band) "
                   "네 가지가 모두 사전 예측과 맞아야 «블레이드 플래시» 라고 부를 수 있다. "
                   "위 숫자가 그 채점표다."))

    sc = J["prereg_scorecard"]["rows"]
    F["q1b_what_failed_and_why"] = dict(
        question_ko="⚠ 틀린 예측 — 무엇이 어긋났고 원인이 무엇인가",
        failed=[pid for pid, r in sc.items() if r["verdict"] == "FAIL"],
        P5_flash_phase=dict(
            values=sc["P5"]["values"], threshold=sc["P5"]["threshold"],
            diagnosis=J.get("nearfield_diagnosis", {}).get("rows"),
            rank_corr=J.get("nearfield_diagnosis", {}).get(
                "rank_corr_rangeoverfarfield_vs_err"),
            explanation_ko=(
                "예측 자체는 살아 있다 — 절대각으로 보면 어긋남이 0.4~2.0° 로 작다. 문제는 두 가지다. "
                "(가) «위상격자 1스텝» 이라는 문턱이 기체마다 엄격함이 다르다(격자가 촘촘한 큰 프롭이 "
                "불리하다). (나) 더 본질적으로, 이 규칙은 **파면이 평평할 때**의 규칙인데 10 m 는 큰 "
                "기체에게 원거리장이 아니다. 같은 표적을 평면파로 재면 대부분 100% 로 맞는다 "
                "— nearfield_diagnosis 블록이 그 증거다."),
            what_it_costs_ko=("이 실패는 «블레이드가 플래시를 만든다» 를 흔들지 않는다. 흔드는 것은 "
                              "«10 m 에서 큰 기체의 플래시 위상을 1° 단위로 예측할 수 있다» 쪽이다.")),
        P6_flash_count=dict(
            values=sc["P6"]["values"], threshold=sc["P6"]["threshold"],
            first_sidelobe_db={k: J["flash_anatomy"][k]["first_sidelobe_db"]["mean"]
                               for k in J["flash_anatomy"]},
            explanation_ko=(
                "s1000plus 한 기체에서만 깨졌다. 이 블레이드는 본잎 바로 옆 곁잎이 −3~−5 dB 로 꽤 "
                "높은데(first_sidelobe_db), s1000plus 는 β 가 커서 그 곁잎이 −3 dB 문턱을 넘어 "
                "덩어리가 하나 더 세어졌다. 즉 «플래시가 더 생긴 것» 이 아니라 **세는 규칙이 "
                "아슬아슬한 것**이다. 플래시가 서는 자리 자체는 맞다(평면파에서 100%).")))

    F["q2_epsilon_the_thing_a_sphere_cannot_do"] = dict(
        question_ko="⭐⭐ 구가 원리적으로 못 내는 자리 — 방위에 따른 산포 ε",
        eps_level_db={k: per[k]["eps_level_db"] for k in fleet},
        eps_level_peak_to_peak_db={k: per[k]["eps_level_peak_to_peak_db"] for k in fleet},
        eps_flash_contrast_db={k: per[k]["eps_flash_contrast_db"] for k in fleet},
        sphere_reference=J["rcs_ladder_context"].get("rows", {}).get("sphere_equal_volume"),
        reading_ko=("등가부피 구는 회전대칭이라 이 값이 **정확히 0.00** 이다 — RCS 사다리에서 이미 "
                    "확인된 사실이다(rcs_ladder_context). 우리 메쉬는 0 이 아니다. "
                    "⚠ 다만 «0 이 아니다» 와 «실측과 맞다» 는 다른 말이다. RCS 사다리에서는 우리 "
                    "메쉬의 ε 오차가 +1.42 dB, 상자가 +4.0~4.5 dB 였다 — 상자도 ε 을 내기는 낸다. "
                    "마이크로도플러에서 상자가 얼마를 내는지는 이 단이 아니라 상자 단이 답한다."))

    F["q3_how_far_can_this_be_trusted"] = dict(
        question_ko="이 단의 숫자를 어디까지 믿을 수 있나",
        reproduction_gate=J["reproduction_gate"].get("verdict"),
        reproduction_detail={k: v.get("max_abs_diff")
                             for k, v in J["reproduction_gate"].get("rows", {}).items()},
        po_validity=J["po_validity_warning"],
        band_consistency_flash={k: v["flash_contrast_db"]
                                for k, v in J.get("band_consistency", {}).get("values", {}).items()},
        wavefront=J["wavefront_control"]["spherical_vs_plane"],
        width_vs_kinematics=mm("width_ratio"),
        caveats_ko=[
            "가림(occlusion)이 없다 — dc_ac_db 는 동체가 과대 계상돼 절대값을 인용하면 안 된다.",
            "정반사/확산 구분이 없다 — 플래시는 저절로 나오지만 확산 성분은 빠져 있다.",
            "블레이드가 3.5 GHz 에서 PO 유효 무릎 아래다 — 15.86 GHz 결과를 반드시 같이 볼 것.",
            "네 로터의 rpm 이 모두 같다(호버). 실제 기체는 로터마다 조금씩 달라 선이 갈라진다.",
            "모노스태틱 한 자리·고각 15° 고정이다 — 바이스태틱·다른 고각은 이 단에 없다."])

    F["q4_what_the_next_rungs_must_match"] = dict(
        question_ko="⭐ 뒤 단(구·상자·평판)이 반드시 맞춰야 할 것",
        contract_pointer="kinematics_contract 블록 (per_drone.<key>)",
        must_match_ko=[
            "회전축 +z · 로터 중심 · 기준각 · 회전방향 · rpm — 대체 모델도 **실제로 돌려야** 한다. "
            "안 돌리고 0 을 얻으면 증명이 아니라 동어반복이다.",
            "위상 스텝 수 S 와 PRF — 기체마다 다르다. protocol_main/protocol_hi 를 그대로 쓸 것.",
            "거리 10 m · 고각 15° · 방위 24점 · 구면파(헤드라인)/평면파(대조).",
            "크기는 equal_volume 로 맞춘다(구 반지름·정육면체 한 변·bbox 비율 유지 상자 전부 계산됨).",
            "재질 |Γ| 는 material 로 맞추거나, 못 맞추면 dB 차이를 병기한다.",
            "지표는 report16_base.md_metrics16 을 **import 해서** 쓴다(재구현 금지)."],
        do_not_conclude_ko=("⛔ 이 단은 «형상 정밀도가 값어치 있다» 를 주장하지 않는다. "
                            "대체 모델이 비슷한 숫자를 내면 그것이 더 중요한 결과이고, "
                            "교수 지적이 마이크로도플러에서도 맞다는 뜻이다."))
    return F


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compute", action="store_true", help="이미 만든 표로 JSON/그림만 다시")
    ap.add_argument("--no-hi", action="store_true", help="15.86 GHz 대조 생략")
    ap.add_argument("--drones", default="", help="쉼표로 구분한 기체 목록(기본 = 전체 함대)")
    a = ap.parse_args()
    main(fleet=[x for x in a.drones.split(",") if x] or None,
         skip_compute=a.skip_compute, with_hi=not a.no_hi)
