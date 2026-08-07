# -*- coding: utf-8 -*-
"""
report16_rung_sphere_eqvol.py — ⭐ 사다리 한 단: **등가부피 구의 마이크로도플러**
================================================================================

한 줄 요약
--------------------------------------------------------------------------------
«매개변수 0 개짜리 등가부피 구» 를 기준 메쉬와 **똑같이 돌려서**, 그 구가 마이크로도플러를
얼마나 내는지 잰다. 예측은 «0» 이다. 0 이 아니면 그 크기가 이 실험 전체의 바닥이다.

무엇을 왜 재는가 (배경 — 이 실험이 존재하는 이유)
--------------------------------------------------------------------------------
지도교수의 지적은 «드론 RCS 정밀도는 연구 값어치가 없다» 이고, **우리 데이터가 그 지적을
상당 부분 뒷받침한다**. 되돌아오는 전파의 «세기» 만 놓고 보면, 드론의 부피만 같게 맞춘 구
하나가 우리가 공들여 만든 3D 형상을 이긴다(outputs/p3_validation_v2.json).

⭐ 그런데 구가 **원리적으로 못 내는 것**이 하나 있다. 구는 어느 방향에서 봐도 똑같이 생겼다.
   그래서 «방향에 따른 세기 변동» 이 정확히 0 이다. 프로펠러가 돌아서 생기는 미세한 신호
   흔들림 — 이것을 «마이크로도플러(micro-Doppler)» 라고 부른다 — 도 같은 이유로 0 이어야 한다.
   구를 회전축 위에 놓고 돌리면 **자기 자신으로 되돌아온다**(회전이 곧 대칭이다).

이 파일이 답하는 질문은 하나다:
   **그 «0» 이 정말 0 인가, 그리고 진짜 형상(메쉬)은 그 0 보다 얼마나 위에 있는가.**

⚠ 결론을 미리 정하지 않기 위해, 계산을 시작하기 **전에** 예측을 파일로 못박고(아래 PREDICTION)
   그 텍스트의 해시와 기록 시각을 산출물에 남긴다. 나중에 «맞췄다» 고 말하려면 그 해시가
   맞아야 한다. 예측을 걸지 않은 항목(⑤ 블레이드-구 사다리)은 «예측 없음» 으로 명시한다.

⭐⭐ 이 라운드의 급소 — 공정성
--------------------------------------------------------------------------------
«구는 안 돌리고 0 을 얻었다» 면 그것은 증명이 아니라 동어반복이다. 그래서 이 파일은
   · 구를 **실제로 돌린다** — 기준 메쉬와 같은 회전축·같은 rpm·같은 위상 스텝·같은 거리·
     같은 자세·같은 주파수·**같은 재질 가중**(구가 대체한 부위의 면적가중 |Γ| 를 계산해서 쓴다).
   · ⭐ **양성 대조군**을 둔다: 똑같은 구를 회전축에서 **비켜 놓고**(로터 팔 길이만큼) 같은
     코드로 돌린다. 여기서 큰 변조가 나와야 «0» 이 죽은 코드가 아니라 물리라는 것이 증명된다.
     이 대조군이 없으면 «네 계산기가 원래 변조를 못 만드는 것 아니냐» 는 반론을 못 막는다.
   · ⭐ 구에게 **최선의 기회**를 준다: 구를 블레이드가 실제로 있는 반경에 갖다 놓으면
     (고전적인 «회전하는 점 산란체» 모델) 변조가 나온다. 그러면 «매개변수 0 개» 는 더 이상
     0 개가 아니다 — 반경과 개수를 사람이 넣어 줘야 한다. 그 대가로 메쉬에 얼마나 다가가는지를
     같은 지표로 잰다. **여기에는 예측을 걸지 않았다.**

측정 팔(arm) — 전부 같은 운동학으로 돈다
--------------------------------------------------------------------------------
 · mesh          : 진짜 CAD 드론(프레임 + 실제 프로펠러 4벌). 기준.
 · sphere_eqvol  : ⭐ 기체 전체 → **등가부피 구 하나**, 회전축 위. 헤드라인.
 · sphere_offaxis: ⭐ 같은 구를 회전축에서 로터 팔 길이만큼 비켜 놓고 돌린다. **양성 대조군.**
 · sph_hub       : 진짜 프레임 + 로터마다 프로펠러 등가부피 구 하나를 **허브 축 위에**.
                   («프로펠러만 구로 바꾸면?» — 동체 DC 가 살아 있는 상태의 널.)
 · sph_blade_rg  : 진짜 프레임 + 로터마다 구 2개를, 실제 블레이드의 **산란 무게중심 반경**에.
 · sph_blade_tip : 같은 구를 **팁 반경**에. (같은 모델, 넣어 주는 반경만 다르다.)

⚠⚠ 반드시 같이 읽어야 할 한계 (report16_base 와 동일)
--------------------------------------------------------------------------------
우리 PO 커널이 믿을 만하려면 부품의 특징 폭이 0.729λ 이상이어야 한다. 프로펠러 블레이드 폭
13.78 mm 는 15.86 GHz 에서야 그 문턱을 넘는다. 즉 생산 대역 3.5 GHz 에서는
**마이크로도플러를 만드는 바로 그 부품이 우리 커널이 가장 약한 부품**이다. 그래서 두 대역을
모두 돌린다. 또한 이 커널에는 **가림(occlusion)이 없다** — 블레이드가 동체 뒤로 돌아가도 계속
센다. 그래서 «동체 대 블레이드 세기비(dc_ac_db)» 는 절대값을 인용하면 안 된다.

⛔ src/drones.py · src/drone_cad.py 는 읽기만 한다. outputs/report15_* · report0N_* 미접촉.
⛔ 숫자 손입력 금지 — 부피·등가반경·반경·위상 스텝은 전부 기하에서 **계산**한다.
⭐ 지표·규약은 report16_base 에서 **그대로 import** 한다(재구현 금지 — 그래야 비교가 성립한다).
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
sys.path.insert(0, os.path.join(ROOT, "src"))

import report16_base as B   # noqa: E402  ⭐ 규약·지표의 단일 출처

SCRATCH = os.environ.get(
    "REPORT16_RUNG_SCRATCH",
    "/tmp/claude-1015/-home-yunjung-workspace/"
    "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report16_rung_sphere")

OUT_JSON = os.path.join(ROOT, "outputs", "report16_rung_sphere_eqvol.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report16_rung_sphere_eqvol_tables.npz")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_rung_sphere_eqvol.png")
BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")

DRONE_KEYS = ("mini2", "matrice4e", "mavic4pro")
ARMS = ("mesh", "sphere_eqvol", "sphere_offaxis", "sph_hub", "sph_blade_rg", "sph_blade_tip")
SPHERE_ARMS = ("sphere_eqvol", "sph_hub")          # 회전축 위 = 물리적 변조 0 이어야 하는 팔

# --------------------------------------------------------------------------- #
#  ⭐⭐ 사전 예측 — 계산을 시작하기 **전에** 파일로 못박는다.
#     문턱값은 여기 적힌 것이 전부다. 나중에 문턱을 옮기면 해시가 깨진다.
# --------------------------------------------------------------------------- #
PREDICTION = {
    "registered_by": "benchmark/report16_rung_sphere_eqvol.py (계산 전에 기록)",
    "one_line_ko": "회전축 위의 등가부피 구는 돌려도 마이크로도플러가 0 이어야 한다.",
    "why_ko": ("구는 회전축을 중심으로 돌리면 자기 자신으로 되돌아온다(회전이 곧 대칭이다). "
               "따라서 되돌아오는 복소 신호 E(φ) 는 φ 에 무관한 상수여야 하고, 변조 성분(AC)은 "
               "이론상 정확히 0 이다. 실제로 남는 값은 «물리» 가 아니라 우리가 구를 삼각형으로 "
               "쪼개면서 생긴 **이산화 잔차** — 즉 계산기 자체의 바닥이다."),
    "P1_null_ko": ("① sphere_eqvol 과 sph_hub 의 **대역 안 AC/DC** 는 24 방위·두 대역·두 파면 "
                   "전부에서 −60 dB 이하일 것. (−40 dB 를 넘으면 예측 실패로 기록한다.)"),
    "P1_threshold_pass_db": -60.0,
    "P1_threshold_fail_db": -40.0,
    "P2_residual_is_numerical_ko": ("② 남는 잔차의 **지배 차수**는 블레이드 빗(2,4,6…)이 아니라 "
                                    "구를 쪼갠 **경도 분할 수 seg 의 정수배**(표본 수보다 크면 접힌 "
                                    "자리)에 붙어 있을 것이고, 분할을 촘촘히 하면 잔차의 자리가 "
                                    "seg 를 따라 옮겨 갈 것. 즉 형상이 만든 신호가 아니라 격자가 "
                                    "만든 신호다."),
    "P3_positive_control_ko": ("③ 같은 구를 회전축에서 비켜 놓으면(sphere_offaxis) 같은 코드에서 "
                               "**큰** 변조가 나올 것 — 대역 안 AC/DC ≥ −20 dB. 이게 안 나오면 "
                               "①의 0 은 물리가 아니라 죽은 코드이므로 이 라운드 전체가 무효다."),
    "P3_threshold_db": -20.0,
    "P4_gap_ko": ("④ 진짜 메쉬는 널보다 훨씬 위에 있을 것(대역 안 AC/DC 기준 40 dB 이상 위). "
                  "이 «여유» 가 곧 구조가 마이크로도플러에 기여하는 양이다."),
    "P4_threshold_db": 40.0,
    "P5_no_prediction_ko": ("⑤ **예측을 걸지 않은 항목**: 블레이드 반경에 구를 갖다 놓은 모델"
                            "(sph_blade_rg / sph_blade_tip)이 메쉬에 얼마나 가까워지는가. "
                            "크게 나오든 작게 나오든 그대로 적는다 — 이쪽이 크면 «형상 정밀도는 "
                            "마이크로도플러에서도 값어치가 적다» 는 뜻이고 방향을 다시 잡아야 한다."),
    "falsification_ko": ("①이 −40 dB 를 넘거나, ③이 −20 dB 에 못 미치거나, ④가 40 dB 에 못 미치면 "
                         "예측 실패다. 실패도 그대로 산출물에 남긴다."),
}


def _write_prereg():
    """예측을 **계산 전에** 파일로 떨구고 해시를 돌려준다(순서 증명).

    ⭐ 돌릴 때마다 새 파일을 남기되, **이미 있던 예측 파일의 해시와 같은지**를 검사한다.
      해시가 전부 같고 가장 이른 파일이 계산 결과 파일보다 먼저 쓰였으면, «결과를 보고
      예측을 고쳤다» 는 의심이 봉쇄된다."""
    os.makedirs(SCRATCH, exist_ok=True)
    txt = json.dumps(PREDICTION, ensure_ascii=False, sort_keys=True, indent=1)
    sha = hashlib.sha256(txt.encode()).hexdigest()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    p = os.path.join(SCRATCH, f"prereg_{stamp.replace(':', '')}.json")
    with open(p, "w") as f:
        f.write(txt)
    prev = sorted(os.path.join(SCRATCH, x) for x in os.listdir(SCRATCH)
                  if x.startswith("prereg_") and x.endswith(".json"))
    stamps = []
    for q in prev:
        h = hashlib.sha256(open(q, "rb").read()).hexdigest()
        stamps.append(dict(file=os.path.basename(q), sha256=h, same_as_current=(h == sha),
                           mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                               time.localtime(os.path.getmtime(q)))))
    first_t = min((os.path.getmtime(q) for q in prev), default=time.time())
    tab = os.path.join(SCRATCH, "tab_main.npz")
    precedes = (os.path.exists(tab) and first_t < os.path.getmtime(tab))
    src = open(os.path.abspath(__file__), "rb").read()
    return dict(prediction=PREDICTION, sha256=sha,
                first_written_at=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(first_t)),
                written_at=stamp, path=p, all_stamps=stamps,
                all_identical=bool(all(s["same_as_current"] for s in stamps)),
                first_result_file=os.path.relpath(tab, SCRATCH) if os.path.exists(tab) else None,
                first_result_written_at=(time.strftime("%Y-%m-%dT%H:%M:%S",
                                                       time.localtime(os.path.getmtime(tab)))
                                         if os.path.exists(tab) else None),
                prereg_precedes_first_result=bool(precedes),
                source_file_sha256=hashlib.sha256(src).hexdigest(),
                order_proof_ko=("예측 텍스트를 GPU 계산 전에 스크래치에 쓰고 sha256 과 시각을 "
                                "남긴다. all_identical=true 는 이번 라운드에서 남긴 모든 예측 "
                                "파일이 **한 글자도 다르지 않다**는 뜻이고, "
                                "prereg_precedes_first_result=true 는 가장 이른 예측 파일이 "
                                "첫 계산 결과보다 먼저 쓰였다는 뜻이다. 둘이 다 참이면 "
                                "«결과를 보고 예측·문턱을 고쳤다» 는 의심이 봉쇄된다."))


# =========================================================================== #
#                          기하 도구 — 전부 계산, 손입력 없음
# =========================================================================== #
def mesh_volume(m):
    """닫힌 메쉬의 부피[m³] (발산정리). 부품이 겹쳐 있으면 겹친 만큼 두 번 세어진다 — 그래서
    프레임/프로펠러 부피를 따로도 기록해 구성이 보이게 한다."""
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    return float(np.sum(np.einsum("ij,ij->i", p0, cr)) / 6.0)


def mesh_area_gamma(m, gmap):
    """메쉬의 **면적가중 평균 |Γ|** — 구가 대체한 부위의 재질을 «계산해서» 물려받기 위한 값.
    (|Γ| = 진폭 반사계수. 1 이면 완전도체, 0.25 면 플라스틱 프로펠러처럼 잘 안 되비친다.)"""
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    ar = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    g = np.array([float(gmap.get(gg, 1.0)) for gg in m.g], float)
    return float(np.sum(ar * g) / max(np.sum(ar), 1e-30)), float(np.sum(ar))


def _odd(n):
    return int(n) if int(n) % 2 == 1 else int(n) + 1


def sphere_cloud(radius, spacing, center=(0.0, 0.0, 0.0), gamma=1.0, refine=1.0):
    """구 하나를 점구름으로. seg/rings 는 요청 간격에서 **계산**한다."""
    from geom import uv_sphere
    from rcs_po import mesh_to_points
    sp = float(spacing) / float(refine)
    seg = _odd(max(9, int(math.ceil(2 * math.pi * radius / sp))))
    rings = max(3, int(math.ceil(math.pi * radius / sp)))
    m = uv_sphere(radius, center=tuple(center), seg=seg, rings=rings, group="sph")
    P, N, dA = mesh_to_points(m, sp)
    return P, N, dA * float(gamma), dict(seg=seg, rings=rings, n_tris=len(m.f),
                                         n_pts=int(len(P)), requested_spacing_m=sp,
                                         radius_m=float(radius),
                                         center_local_m=[float(c) for c in center],
                                         gamma_abs=float(gamma))


def alias_order(seg, S):
    """구를 seg 조각으로 쪼갠 격자가 «1회전 S 표본» 위에서 몇 차수로 보이는가.

    격자 잔차는 회전각에 대해 seg 주기로 반복되므로 원래 차수는 seg 의 배수다. 그런데
    표본이 S 개뿐이면 그 차수가 S/2 를 넘을 때 **접혀서**(aliasing) 다른 자리에 나타난다.
    그 자리를 계산한다 — 잔차가 «격자» 라는 주장은 이 예측값과 대 봐야 검사가 된다."""
    a = int(seg) % int(S)
    return int(min(a, int(S) - a))


def grid_orders(seg, S, jmax=6):
    """격자가 만들 수 있는 차수들 = seg 의 j 배(j=1..jmax)를 접은 것. {차수: j} 로 준다."""
    out = {}
    for j in range(1, int(jmax) + 1):
        out.setdefault(alias_order(int(seg) * j, S), j)
    return out


def is_grid_order(order, seg, S, jmax=6):
    """관측된 지배 차수가 «격자가 만든 자리» 인가. (판정, 몇 배인가) 를 돌려준다."""
    g = grid_orders(seg, S, jmax)
    return (int(order) in g), g.get(int(order))


def nn_spacing(P, n_probe=4000, seed=0):
    """점구름의 실측 최근접이웃 간격 중앙값[m] — «촘촘함» 을 팔끼리 비교하기 위한 실측치."""
    from scipy.spatial import cKDTree
    P = np.asarray(P, float)
    if len(P) < 4:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(P), size=min(n_probe, len(P)), replace=False)
    d, _ = cKDTree(P).query(P[idx], k=2)
    return float(np.median(d[:, 1]))


# =========================================================================== #
#                              팔(arm) 만들기
# =========================================================================== #
FRAME_DIV, BLADE_DIV, BLADE_N = 6.0, 11.0, 26      # report16_base 규약 그대로


def build_arm(key, arm, lam, refine=1.0):
    """팔 하나의 «정지 부품 + 회전 부품» 구성. 회전 부품은 전부 허브 로컬좌표다.

    ⭐ 모든 팔이 **같은 회전축·같은 rpm·같은 위상 격자**를 쓴다. 팔마다 다른 것은 «무엇이
      회전축 둘레에 놓여 있는가» 뿐이다."""
    from drones import (DRONES, build_frame, build_propeller, rotor_layout,
                        drone_gamma_map, build_drone)
    from rcs_po import mesh_to_points

    s = DRONES[key]
    gm = drone_gamma_map(s)
    spac_b = lam / (BLADE_DIV * refine)
    spac_f = lam / (FRAME_DIV * refine)
    R_tip = float(s.prop_dia_mm) / 2000.0
    rots = rotor_layout(s)

    frame = build_frame(s)
    prop = build_propeller(s, n=BLADE_N)
    meta = {}

    # 실제 프로펠러의 «산란 무게중심» — 구를 어디에 놓아야 공정한가를 **계산**한다.
    Pp, Np_, dAp, wp = mesh_to_points(prop, spac_b, gamma=gm)
    Wp = dAp * wp
    r_pts = np.hypot(Pp[:, 0], Pp[:, 1])
    r_cent = float(np.sum(Wp * r_pts) / max(np.sum(Wp), 1e-30))       # 진폭가중 평균 반경
    z_cent = float(np.sum(Wp * Pp[:, 2]) / max(np.sum(Wp), 1e-30))
    blade_only = r_pts >= 0.25 * R_tip
    r_cent_blade = float(np.sum(Wp[blade_only] * r_pts[blade_only]) /
                         max(np.sum(Wp[blade_only]), 1e-30)) if blade_only.any() else r_cent
    prop_vol = abs(mesh_volume(prop))
    prop_gam, prop_area = mesh_area_gamma(prop, gm)

    common = dict(prop_scatter_centroid_radius_m=r_cent,
                  prop_scatter_centroid_radius_blade_only_m=r_cent_blade,
                  prop_scatter_centroid_z_m=z_cent, prop_tip_radius_m=R_tip,
                  prop_volume_m3=prop_vol, prop_area_m2=prop_area,
                  prop_area_weighted_gamma=prop_gam)

    def frame_cloud():
        Pf, Nf, dAf, wf = mesh_to_points(frame, spac_f, gamma=gm)
        return (Pf, Nf, dAf * wf)

    # ---------------------------------------------------------------- mesh
    if arm == "mesh":
        Pm = Pp * np.array([1.0, -1.0, 1.0])       # 반대회전 로터 = 거울상 프롭 (base 규약)
        Nm = Np_ * np.array([1.0, -1.0, 1.0])
        groups = [dict(center=r["center"], base_ang=r["base_ang"], dir=r["dir"],
                       cloud=((Pp, Np_, Wp) if r["dir"] > 0 else (Pm, Nm, Wp)))
                  for r in rots]
        meta = dict(common, kind="cad_mesh", n_prop_pts=int(len(Pp)),
                    actual_spacing_m=nn_spacing(Pp), n_rotors=len(rots),
                    note_ko="진짜 CAD 프로펠러 4벌이 실제 허브 위치에서 돈다. 기준.")
        return dict(frame=frame_cloud(), groups=groups, meta=meta, spec=s)

    # ------------------------------------------------- 기체 전체 → 등가부피 구
    if arm in ("sphere_eqvol", "sphere_offaxis"):
        drone = build_drone(s)
        vol = abs(mesh_volume(drone))
        r_eq = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
        gam, area = mesh_area_gamma(drone, gm)
        arm_r = float(np.mean([math.hypot(r["center"][0], r["center"][1]) for r in rots]))
        off = (arm_r, 0.0, 0.0) if arm == "sphere_offaxis" else (0.0, 0.0, 0.0)
        P, N, W, sm = sphere_cloud(r_eq, spac_b, center=off, gamma=gam, refine=1.0)
        # 회전축은 기체 z 축(로터와 같은 축·같은 rpm·같은 위상 격자)
        groups = [dict(center=(0.0, 0.0, 0.0), base_ang=0.0, dir=1,
                       cloud=(P, N, W))]
        meta = dict(common, kind=("sphere_equal_volume_on_axis" if arm == "sphere_eqvol"
                                  else "sphere_equal_volume_off_axis_POSITIVE_CONTROL"),
                    drone_volume_m3=vol, r_equal_volume_m=r_eq,
                    drone_area_m2=area, area_weighted_gamma=gam,
                    optical_sigma_pi_r2_m2=math.pi * r_eq ** 2,
                    optical_sigma_dbsm=float(10 * math.log10(math.pi * r_eq ** 2)),
                    offset_from_axis_m=float(off[0]),
                    rotor_arm_radius_mean_m=arm_r,
                    actual_spacing_m=nn_spacing(P), **{f"sphere_{k}": v for k, v in sm.items()},
                    note_ko=("기체 전체를 등가부피 구 하나로 교체. 같은 z 축·같은 rpm·같은 위상 "
                             "격자로 **실제로 돌린다**. off-axis 판은 같은 구를 로터 팔 길이만큼 "
                             "비켜 놓은 양성 대조군 — 여기서 변조가 나와야 on-axis 의 0 이 물리다."))
        return dict(frame=None, groups=groups, meta=meta, spec=s)

    # ------------------------------------- 프레임 + 로터마다 구 (허브 축 위 / 블레이드 반경)
    if arm in ("sph_hub", "sph_blade_rg", "sph_blade_tip"):
        nb = int(s.prop_blades)
        if arm == "sph_hub":
            r_sph = (3.0 * prop_vol / (4.0 * math.pi)) ** (1.0 / 3.0)
            centers = [(0.0, 0.0, z_cent)]
            r_place = 0.0
        else:
            r_place = r_cent_blade if arm == "sph_blade_rg" else R_tip
            r_sph = (3.0 * (prop_vol / nb) / (4.0 * math.pi)) ** (1.0 / 3.0)
            centers = [(r_place * math.cos(2 * math.pi * b / nb),
                        r_place * math.sin(2 * math.pi * b / nb), z_cent) for b in range(nb)]
        Ps, Ns, Ws, sms = [], [], [], []
        for c in centers:
            P, N, W, sm = sphere_cloud(r_sph, spac_b, center=c, gamma=prop_gam, refine=1.0)
            Ps.append(P); Ns.append(N); Ws.append(W); sms.append(sm)
        P = np.vstack(Ps); N = np.vstack(Ns); W = np.concatenate(Ws)
        groups = [dict(center=r["center"], base_ang=r["base_ang"], dir=r["dir"],
                       cloud=(P, N, W)) for r in rots]
        meta = dict(common, kind=f"frame_plus_{arm}",
                    n_spheres_per_rotor=len(centers), sphere_radius_m=r_sph,
                    sphere_volume_each_m3=4.0 / 3.0 * math.pi * r_sph ** 3,
                    placement_radius_m=float(r_place),
                    placement_radius_over_tip=float(r_place / R_tip),
                    sphere_gamma_from_prop=prop_gam,
                    sphere_tess=sms[0], actual_spacing_m=nn_spacing(P),
                    note_ko=("프로펠러를 같은 부피의 구로 교체. 허브 축 위(sph_hub)면 회전대칭이라 "
                             "변조 0, 블레이드 반경에 놓으면(sph_blade_*) 고전 «회전하는 점 산란체» "
                             "가 되어 변조가 나온다 — 대신 반경과 개수를 사람이 넣어 줘야 한다."))
        return dict(frame=frame_cloud(), groups=groups, meta=meta, spec=s)

    raise ValueError(arm)


# =========================================================================== #
#                                   계산
# =========================================================================== #
def compute_tables(torch, dev, key, arm, fc, refine=1.0, n_az=None, wavefronts=("spherical", "plane")):
    """팔 하나의 위상 표 E(az, φ) 를 만든다 — report16_base 커널을 그대로 쓴다."""
    from drones import DRONES
    s = DRONES[key]
    lam = B.C0 / fc
    k_wav = 2.0 * math.pi / lam
    proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
    phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
    naz = int(n_az or B.N_AZ)
    az_list = np.arange(naz) * (360.0 / naz)
    cl = build_arm(key, arm, lam, refine=refine)
    out = {}
    for wf in wavefronts:
        T = np.zeros((naz, proto["n_phase"]), complex)
        for ia, az in enumerate(az_list):
            u, A, R_t = B.look_and_antenna(az, B.EL_DEG, B.RANGE_M)
            Ef = 0.0 + 0.0j
            if cl["frame"] is not None:
                Pf, Nf, Wf = cl["frame"]
                Ef = B.field_static(torch, dev, Pf, Nf, Wf, k_wav, A, R_t, wf)
            tot = np.full(proto["n_phase"], Ef, complex)
            for g in cl["groups"]:
                P, N, W = g["cloud"]
                tot += B.field_rotor(torch, dev, P, N, W, k_wav, A, R_t, g["center"],
                                     math.radians(float(g["base_ang"])), float(g["dir"]),
                                     phis, wf)
            T[ia] = tot
        out[wf] = T
    return out, proto, cl["meta"], az_list


def mod_depth(tab):
    """⭐ **쉬운 말 지표**: 한 바퀴 도는 동안 되돌아오는 신호가 «몇 % 흔들리나».

    정의: max|E(φ) − mean E| / |mean E|. 구는 0 이어야 한다. dB 와 ppm(백만분율)로도 준다."""
    t = np.asarray(tab, complex)
    m = t.mean()
    if abs(m) <= 0:
        return dict(rel=float("nan"), db=float("nan"), ppm=float("nan"))
    rel = float(np.max(np.abs(t - m)) / abs(m))
    return dict(rel=rel, db=float(20 * np.log10(max(rel, 1e-300))), ppm=rel * 1e6,
                amp_ptp_db=float(20 * np.log10(np.max(np.abs(t)) / max(np.min(np.abs(t)), 1e-300))))


def block(T, proto, nb):
    """표 → (방위별 요약 + 방위 0 + 변조깊이)."""
    per = [B.md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]
    md = [mod_depth(T[i]) for i in range(T.shape[0])]
    keys = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90", "dominant_order",
            "blade_comb_frac", "fd_edge_hz", "width_ratio", "dc_ac_db",
            "sigma_eq_mean_dbsm", "in_band_ac_frac", "in_band_ac_over_dc_db",
            "ac_over_floor_db", "width_ratio_10db", "width_ratio_30db")
    out = dict(per_az={kk: B.summarize([m[kk] for m in per]) for kk in keys},
               az0={kk: per[0][kk] for kk in keys},
               mod_depth_db=B.summarize([m["db"] for m in md]),
               mod_depth_ppm=B.summarize([m["ppm"] for m in md]),
               amp_ptp_db=B.summarize([m["amp_ptp_db"] for m in md]),
               interpretable_frac=float(np.mean([m["metrics_interpretable"] for m in per])),
               band_order=int(per[0]["band_order"]), n_az=int(T.shape[0]))
    return out


# =========================================================================== #
#                      게이트 — 이 파일이 base 와 같은 값을 내는가
# =========================================================================== #
def gate_vs_base(tabs):
    """⭐ mesh 팔은 report16_base 가 이미 저장해 둔 표와 **같아야** 한다.
    base 는 저장소 numpy 판(microdoppler_nearfield.phase_table)과 1e-14 수준으로 일치한 것이
    확인돼 있으므로, 여기에 맞으면 이 파일의 모든 숫자가 같은 규약 위에 있다는 뜻이다."""
    if not os.path.exists(BASE_NPZ):
        return dict(absent=True)
    z = np.load(BASE_NPZ)
    rows = {}
    for key in DRONE_KEYS:
        for wf in ("spherical", "plane"):
            bk = f"main__G_0804__{key}__mesh__{wf}"
            mk = f"main|{key}|mesh|{wf}"
            if bk not in z.files or mk not in tabs:
                continue
            a, b = z[bk], tabs[mk]
            if a.shape != b.shape:
                rows[f"{key}|{wf}"] = dict(shape_mismatch=[list(a.shape), list(b.shape)])
                continue
            num = float(np.max(np.abs(a - b)))
            den = float(np.max(np.abs(a)))
            rows[f"{key}|{wf}"] = dict(max_abs_diff=num, max_abs_ref=den,
                                       max_rel=num / max(den, 1e-300))
    rel = [v["max_rel"] for v in rows.values() if "max_rel" in v]
    return dict(rows=rows, tolerance=1e-12,
                verdict=("PASS" if rel and max(rel) < 1e-12 else
                         ("FAIL" if rel else "NO_OVERLAP")),
                max_rel=(max(rel) if rel else None),
                reference="outputs/report16_base_tables.npz (G_0804 mesh arm)",
                what_ko=("이 파일의 mesh 팔이 report16_base 가 저장한 표와 같은가. "
                         "같은 커널·같은 규약이므로 비트 수준으로 같아야 한다. "
                         "base 자체는 저장소 numpy 판과 4.8e-14 로 일치 확인됨."))


# =========================================================================== #
#            널 잔차가 «물리» 가 아니라 «격자» 임을 보이는 수렴 스캔
# =========================================================================== #
def null_convergence(torch, dev, keys=("mini2", "matrice4e"), n_az=4):
    """구를 더 촘촘히 쪼개면 잔차가 어떻게 되는가.

    잔차가 «구의 물리» 라면 격자를 바꿔도 그대로 있어야 한다. «격자가 만든 것» 이라면
    분할 수 seg 를 따라 위치가 옮겨 가고 크기도 바뀐다. 그것을 실측한다."""
    from drones import DRONES
    out = {}
    for key in keys:
        s = DRONES[key]
        rows = {}
        for refine in (0.5, 1.0, 2.0, 4.0):
            lam = B.C0 / B.FC_MAIN
            proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_MAIN)
            cl = build_arm(key, "sphere_eqvol", lam, refine=1.0)
            # refine 은 구 자체의 분할에만 적용한다(대체 대상은 그대로)
            m = cl["meta"]
            P, N, W, sm = sphere_cloud(m["r_equal_volume_m"], lam / BLADE_DIV,
                                       center=(0.0, 0.0, 0.0),
                                       gamma=m["area_weighted_gamma"], refine=refine)
            phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
            k_wav = 2.0 * math.pi / lam
            vals, doms, mds = [], [], []
            for ia in range(n_az):
                az = ia * (360.0 / n_az)
                u, A, R_t = B.look_and_antenna(az, B.EL_DEG, B.RANGE_M)
                T = B.field_rotor(torch, dev, P, N, W, k_wav, A, R_t, (0.0, 0.0, 0.0),
                                  0.0, 1.0, phis, "spherical")
                mm = B.md_metrics16(T, proto, s.prop_blades)
                vals.append(mm["in_band_ac_over_dc_db"])
                doms.append(mm["dominant_order"])
                mds.append(mod_depth(T)["db"])
            go = grid_orders(sm["seg"], proto["n_phase"])
            rows[f"refine_x{refine:g}"] = dict(
                refine=refine, seg=sm["seg"], rings=sm["rings"], n_pts=sm["n_pts"],
                in_band_ac_over_dc_db=B.summarize(vals),
                mod_depth_db=B.summarize(mds),
                dominant_order=[int(d) for d in doms],
                predicted_grid_orders={str(k): v for k, v in sorted(go.items())},
                dominant_order_is_grid=[bool(int(d) in go) for d in doms],
                grid_harmonic_j=[go.get(int(d)) for d in doms],
                n_phase=int(proto["n_phase"]))
        out[key] = rows
    out["_what_ko"] = ("구의 삼각형 분할을 0.5×~4× 로 바꿔 가며 남는 잔차를 잰다. "
                       "잔차의 지배 차수가 경도 분할 수(seg)를 따라 움직이면 그것은 «구의 물리» 가 "
                       "아니라 «우리가 구를 쪼갠 방식» 이 만든 값이다 — 즉 계산기의 바닥이다. "
                       "⚠ seg 가 위상 스텝 수보다 커지면 잔차 차수가 접혀서(aliasing) 다른 자리에 "
                       "보인다. 그 경우도 seg 로부터 예측되는 자리인지 같이 검사한다.")
    return out


def hub_refine(torch, dev, keys=DRONE_KEYS, n_az=4, refines=(1.0, 2.0, 4.0, 8.0)):
    """⭐ **사후 진단**(계산 뒤에 추가한 항목임을 명시한다).

    사전 예측 P1 이 «sph_hub» 팔의 한 구석에서 아슬아슬하게 걸렸다. 그 팔의 구는 프로펠러
    부피만큼만 크기라 아주 작고, 그래서 삼각형이 아주 성기게(경도 9~13 조각) 깔린다.
    성긴 격자는 잔차를 **낮은 차수**에 만들고, 낮은 차수는 하필 «운동학이 허용하는 대역»
    안이라 진짜 마이크로도플러인 척 보인다.

    그 설명이 맞다면 구를 더 촘촘히 쪼갤수록 잔차가 내려가야 한다. 그것을 검사한다.
    ⚠ 이 결과로 사전 문턱을 옮기지 않는다 — P1 판정은 MARGINAL 그대로 남긴다."""
    from drones import DRONES
    lam = B.C0 / B.FC_MAIN
    k_wav = 2.0 * math.pi / lam
    out = {}
    for key in keys:
        s = DRONES[key]
        proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_MAIN)
        cl = build_arm(key, "sph_hub", lam)
        m = cl["meta"]
        phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
        rows = {}
        for refine in refines:
            P, N, W, sm = sphere_cloud(m["sphere_radius_m"], lam / BLADE_DIV,
                                       center=(0.0, 0.0, m["prop_scatter_centroid_z_m"]),
                                       gamma=m["sphere_gamma_from_prop"], refine=refine)
            vals, doms, mds = [], [], []
            for ia in range(n_az):
                az = ia * (360.0 / n_az)
                u, A, R_t = B.look_and_antenna(az, B.EL_DEG, B.RANGE_M)
                Pf, Nf, Wf = cl["frame"]
                Ef = B.field_static(torch, dev, Pf, Nf, Wf, k_wav, A, R_t, "spherical")
                tot = np.full(proto["n_phase"], Ef, complex)
                for g in cl["groups"]:
                    tot += B.field_rotor(torch, dev, P, N, W, k_wav, A, R_t, g["center"],
                                         math.radians(float(g["base_ang"])), float(g["dir"]),
                                         phis, "spherical")
                mm = B.md_metrics16(tot, proto, s.prop_blades)
                vals.append(mm["in_band_ac_over_dc_db"]); doms.append(mm["dominant_order"])
                mds.append(mod_depth(tot)["db"])
            go = grid_orders(sm["seg"], proto["n_phase"])
            rows[f"refine_x{refine:g}"] = dict(
                refine=refine, seg=sm["seg"], rings=sm["rings"], n_pts=sm["n_pts"],
                in_band_ac_over_dc_db=B.summarize(vals), mod_depth_db=B.summarize(mds),
                dominant_order=[int(d) for d in doms],
                predicted_grid_orders={str(k): v for k, v in sorted(go.items())},
                dominant_order_is_grid=[bool(int(d) in go) for d in doms],
                band_order=int(math.ceil(1.5 * proto["beta"])))
        out[key] = rows
    out["_what_ko"] = ("사후 진단: 허브 구의 삼각형 분할만 1×~8× 로 촘촘히 하며 잔차를 다시 잰다. "
                       "잔차가 내려가면 그것은 «구가 만든 변조» 가 아니라 «성긴 격자» 였다는 뜻이다. "
                       "⚠ 그래도 사전 예측 P1 의 판정은 바꾸지 않는다.")
    return out


def gamma_invariance(torch, dev, key="matrice4e"):
    """⭐ «재질을 뭘로 잡느냐가 결론을 바꾸지 않는다» 를 실측으로 보인다.

    구 전체에 같은 |Γ| 를 곱하는 것은 신호에 상수를 곱하는 것과 같다. 그래서 모양 지표
    (플래시 대조비·차수 풍부도·폭·DC/AC 비)는 **정확히** 그대로여야 하고, 세기(σ)만
    20log10(Γ) 만큼 움직여야 한다. 그것을 숫자로 확인한다."""
    from drones import DRONES
    s = DRONES[key]
    lam = B.C0 / B.FC_MAIN
    proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_MAIN)
    cl = build_arm(key, "sphere_eqvol", lam)
    m = cl["meta"]
    phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
    k_wav = 2.0 * math.pi / lam
    u, A, R_t = B.look_and_antenna(0.0, B.EL_DEG, B.RANGE_M)
    res = {}
    for lab, gam in (("material_matched", m["area_weighted_gamma"]), ("PEC", 1.0)):
        P, N, W, _ = sphere_cloud(m["r_equal_volume_m"], lam / BLADE_DIV, gamma=gam)
        T = B.field_rotor(torch, dev, P, N, W, k_wav, A, R_t, (0., 0., 0.), 0.0, 1.0,
                          phis, "spherical")
        mm = B.md_metrics16(T, proto, s.prop_blades)
        res[lab] = dict(gamma=float(gam), sigma_eq_mean_dbsm=mm["sigma_eq_mean_dbsm"],
                        flash_contrast_db=mm["flash_contrast_db"],
                        dc_ac_db=mm["dc_ac_db"], n_eff_orders=mm["n_eff_orders"],
                        in_band_ac_over_dc_db=mm["in_band_ac_over_dc_db"],
                        mod_depth_db=mod_depth(T)["db"])
    a, b = res["material_matched"], res["PEC"]
    res["delta_material_minus_pec"] = {kk: a[kk] - b[kk] for kk in
                                       ("sigma_eq_mean_dbsm", "flash_contrast_db", "dc_ac_db",
                                        "n_eff_orders", "in_band_ac_over_dc_db", "mod_depth_db")}
    res["expected_sigma_delta_db"] = float(20 * math.log10(a["gamma"]))
    res["what_ko"] = ("구 전체에 같은 |Γ| 를 곱하면 신호가 상수배 될 뿐이다. 모양 지표는 그대로, "
                      "세기만 20log10Γ 만큼 움직이는 것이 맞다. 즉 «구의 마이크로도플러가 0» 은 "
                      "재질을 어떻게 잡든 성립한다.")
    return res


# =========================================================================== #
#                                  드라이버
# =========================================================================== #
def run_all(fc, tag, refine=1.0):
    """한 대역 전체를 계산한다(별도 프로세스에서 호출된다)."""
    from gpu import pick                    # ⚠ torch 보다 먼저
    picked = pick(verbose=True)
    import torch
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tabs, metas = {}, {}
    for key in DRONE_KEYS:
        for arm in ARMS:
            t0 = time.time()
            out, proto, meta, az = compute_tables(torch, dev, key, arm, fc, refine=refine)
            for wf, T in out.items():
                tabs[f"{tag}|{key}|{arm}|{wf}"] = T
            metas[f"{key}|{arm}"] = dict(meta=meta, seconds=float(time.time() - t0))
            metas[f"{key}|proto"] = proto
            print(f"  [{tag}] {key:10s} {arm:15s} n_phase={proto['n_phase']:4d} "
                  f"[{time.time()-t0:.1f}s]", flush=True)
    extras = {}
    if tag == "main":
        extras["null_convergence"] = null_convergence(torch, dev)
        extras["gamma_invariance"] = gamma_invariance(torch, dev)
        extras["hub_refine"] = hub_refine(torch, dev)
    os.makedirs(SCRATCH, exist_ok=True)
    np.savez_compressed(os.path.join(SCRATCH, f"tab_{tag}.npz"),
                        **{k.replace("|", "__"): v for k, v in tabs.items()})
    with open(os.path.join(SCRATCH, f"meta_{tag}.json"), "w") as f:
        json.dump(dict(gpu=picked, fc=fc, tag=tag, metas=metas, extras=extras,
                       az_deg=list(np.arange(B.N_AZ) * (360.0 / B.N_AZ))), f, ensure_ascii=False)
    print(f"  → {SCRATCH}/tab_{tag}.npz", flush=True)


def launch(tag, fc):
    p = os.path.join(SCRATCH, f"r16r_run_{tag}.py")
    os.makedirs(SCRATCH, exist_ok=True)
    with open(p, "w") as f:
        f.write(f"import sys\nsys.path.insert(0, {_HERE!r})\n"
                "import report16_rung_sphere_eqvol as R\n"
                "R.run_all(float(sys.argv[1]), sys.argv[2])\n")
    print(f"▶ 계산 {tag} (fc={fc/1e9:.2f} GHz)", flush=True)
    r = subprocess.run([sys.executable, p, str(fc), tag], cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"run {tag} failed ({r.returncode})")


def load(tag):
    pz = os.path.join(SCRATCH, f"tab_{tag}.npz")
    mj = os.path.join(SCRATCH, f"meta_{tag}.json")
    if not os.path.exists(pz):
        return {}, {}
    z = np.load(pz)
    return {k.replace("__", "|"): z[k] for k in z.files}, json.load(open(mj))


# --------------------------------------------------------------------------- #
#  그림 — 안의 글씨는 전부 영어(저장소 규약)
# --------------------------------------------------------------------------- #
def make_figure(J, tabs, metas, tabs_hi):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(17.5, 12.6))
    gs = GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.27,
                  left=0.055, right=0.985, top=0.905, bottom=0.055)
    fig.suptitle("Rung: micro-Doppler of the equal-volume sphere  —  "
                 "a 0-parameter sphere spun with identical kinematics (PO kernel, "
                 f"{B.FC_MAIN/1e9:.1f} GHz, el {B.EL_DEG:.0f} deg, R {B.RANGE_M:.0f} m)",
                 fontsize=13.5, y=0.968)

    key = "matrice4e"
    proto = metas["metas"][f"{key}|proto"]
    nb = 2
    COL = {"mesh": "#1b6ca8", "sphere_eqvol": "#c0392b", "sphere_offaxis": "#7f8c8d",
           "sph_hub": "#e67e22", "sph_blade_rg": "#27ae60", "sph_blade_tip": "#8e44ad"}
    LAB = {"mesh": "CAD mesh (reference)", "sphere_eqvol": "equal-volume sphere (on axis)",
           "sphere_offaxis": "same sphere, off axis (positive control)",
           "sph_hub": "prop -> sphere at hub", "sph_blade_rg": "prop -> spheres at blade radius",
           "sph_blade_tip": "prop -> spheres at tip radius"}

    # (1) 회전 한 바퀴 동안의 «흔들림» — 구는 바닥에 붙어야 한다
    ax = fig.add_subplot(gs[0, 0])
    for arm in ("sphere_offaxis", "mesh", "sph_blade_rg", "sph_hub", "sphere_eqvol"):
        k = f"main|{key}|{arm}|spherical"
        if k not in tabs:
            continue
        t = tabs[k][0]
        d = np.abs(t - t.mean()) / abs(t.mean())
        ax.plot(np.arange(len(t)) * 360.0 / len(t), np.maximum(d, 1e-9),
                color=COL[arm], lw=1.4, label=LAB[arm])
    ax.set_yscale("log"); ax.set_ylim(1e-7, 1e2)
    ax.set_xlabel("rotor phase [deg]")
    ax.set_ylabel("wobble  |E(phi) - mean| / |mean|")
    ax.set_title("(a) Wobble over one revolution, az 0 deg\n"
                 "the sphere sits 5-6 decades below the mesh", fontsize=10.5)
    ax.legend(fontsize=6.8, loc="upper right", ncol=1); ax.grid(alpha=0.3, which="both")

    # (2) 변조 깊이 막대
    ax = fig.add_subplot(gs[0, 1])
    arms = [a for a in ARMS]
    xs = np.arange(len(arms))
    w = 0.26
    for i, kk in enumerate(DRONE_KEYS):
        v = [J["arms"][kk][a]["spherical"]["mod_depth_db"]["mean"] for a in arms]
        ax.bar(xs + (i - 1) * w, v, w, label=kk, alpha=0.9)
    ax.axhline(J["prediction_test"]["P1_threshold_pass_db"], color="k", ls="--", lw=1.2)
    ax.text(0.02, J["prediction_test"]["P1_threshold_pass_db"] + 2,
            "pre-registered null threshold", fontsize=7.5, transform=ax.get_yaxis_transform())
    ax.set_xticks(xs); ax.set_xticklabels([a.replace("sphere_", "sph_") for a in arms],
                                          rotation=28, ha="right", fontsize=8)
    ax.set_ylabel("modulation depth  20log10(max|E-mean|/|mean|)  [dB]")
    ax.set_title("(b) How much the return wobbles per revolution\n(mean over 24 azimuths)",
                 fontsize=10.5)
    ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")

    # (3) 차수 스펙트럼
    ax = fig.add_subplot(gs[0, 2])
    for arm in ("mesh", "sph_blade_rg", "sph_blade_tip", "sphere_offaxis", "sphere_eqvol"):
        k = f"main|{key}|{arm}|spherical"
        if k not in tabs:
            continue
        t = tabs[k][0]
        c = np.fft.fft(t) / len(t)
        mm = np.fft.fftfreq(len(t), d=1.0 / len(t)).astype(int)
        sel = (mm >= 0)
        p = 20 * np.log10(np.maximum(np.abs(c[sel]), 1e-300) / max(abs(c[0]), 1e-300))
        ax.plot(mm[sel], p, color=COL[arm], lw=1.2, label=LAB[arm])
    ax.axvline(proto["beta"], color="k", ls=":", lw=1.2)
    ax.text(proto["beta"], -25, " beta = f_tip/f_rot", fontsize=7.5, rotation=90, va="top")
    ax.set_xlim(0, min(len(tabs[f"main|{key}|mesh|spherical"][0]) // 2, 90))
    ax.set_ylim(-200, 12)
    ax.set_xlabel("harmonic order m  (Doppler = m * f_rot)")
    ax.set_ylabel("|c_m| relative to DC [dB]")
    ax.set_title(f"(c) Line spectrum, {key}, az 0 deg", fontsize=10.5)
    ax.legend(fontsize=7.0, loc="lower right"); ax.grid(alpha=0.3)

    # (4) 널 수렴 — 격자를 촘촘히 하면 잔차가 내려간다
    ax = fig.add_subplot(gs[1, 0])
    nc = J["null_is_numerical"]["convergence"]
    for kk in DRONE_KEYS[:2]:
        if kk not in nc:
            continue
        rows = sorted((v["seg"], v["mod_depth_db"]["mean"], v["in_band_ac_over_dc_db"]["mean"])
                      for r, v in nc[kk].items() if r.startswith("refine"))
        p = ax.plot([r[0] for r in rows], [r[1] for r in rows], "o-",
                    label=f"{kk}: wobble depth")[0]
        ax.plot([r[0] for r in rows], [r[2] for r in rows], "s--", alpha=0.55,
                color=p.get_color(), label=f"{kk}: in-band AC/DC")
    hr = J.get("posthoc_marginal_diagnosis", {}).get("refinement", {})
    for kk in DRONE_KEYS[:2]:
        if kk in hr:
            rows = sorted((v["seg"], v["in_band_ac_over_dc_db"]["mean"])
                          for r, v in hr[kk].items() if r.startswith("refine"))
            ax.plot([r[0] for r in rows], [r[1] for r in rows], "^:", lw=1.2, alpha=0.8,
                    label=f"{kk}: hub sphere (post-hoc)")
    ax.set_xscale("log")
    ax.set_xlabel("sphere tessellation: longitude segments (seg)")
    ax.set_ylabel("residual [dB]")
    ax.set_title("(d) The leftover is the mesh grid, not physics\n"
                 "finer sphere -> smaller wobble", fontsize=10.5)
    ax.legend(fontsize=6.5); ax.grid(alpha=0.3, which="both")

    # (5) 지표 사다리 — 프리미티브가 못 따라오는 것
    ax = fig.add_subplot(gs[1, 1])
    mets = ("flash_contrast_db", "n_eff_orders", "width_ratio", "blade_comb_frac")
    labs = ("flash\ncontrast [dB]", "effective\norders", "width ratio\n(fd/f_tip)",
            "blade-comb\nfraction")
    # ⚠ 널 팔(구·허브구)은 지표가 «해석 불가» 로 판정되므로 여기 넣지 않는다 — 넣으면
    #   격자 잔차의 폭·풍부도를 마치 물리인 것처럼 나란히 세우게 된다.
    show = [a for a in ("mesh", "sph_blade_rg", "sph_blade_tip")
            if J["arms"][key][a]["spherical"]["interpretable_frac"] > 0.5]
    xs = np.arange(len(mets)); w = 0.8 / max(len(show), 1)
    for i, arm in enumerate(show):
        v = [J["arms"][key][arm]["spherical"]["per_az"][m]["mean"] for m in mets]
        ax.bar(xs + (i - (len(show) - 1) / 2.0) * w, v, w, color=COL[arm], label=LAB[arm],
               alpha=0.92)
    ax.axhline(1.0, color="k", ls=":", lw=1.0)
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=8)
    ax.set_title(f"(e) Metric ladder, {key} (24-azimuth mean)\n"
                 "null arms omitted: their metrics are not interpretable", fontsize=10.5)
    ax.legend(fontsize=7.0); ax.grid(alpha=0.3, axis="y")
    ax.axhline(0, color="k", lw=0.8)

    # (6) 파형 상관 (메쉬 대비)
    ax = fig.add_subplot(gs[1, 2])
    cc = J["ladder_vs_mesh"]
    arms2 = [a for a in ARMS if a != "mesh"]
    xs = np.arange(len(arms2)); w = 0.26
    for i, kk in enumerate(DRONE_KEYS):
        v = [cc[kk][a]["ac_corr_vs_mesh"]["mean"] for a in arms2]
        ax.bar(xs + (i - 1) * w, v, w, label=kk, alpha=0.9)
    ax.set_xticks(xs); ax.set_xticklabels([a.replace("sphere_", "sph_") for a in arms2],
                                          rotation=28, ha="right", fontsize=8)
    ax.set_ylabel("|correlation| of AC waveform vs CAD mesh")
    ax.set_ylim(0, 1)
    ax.set_title("(f) Does the primitive reproduce the mesh waveform?", fontsize=10.5)
    ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")

    # (7) 두 대역 비교
    ax = fig.add_subplot(gs[2, 0])
    xs = np.arange(len(ARMS)); w = 0.38
    for i, (tg, lab) in enumerate((("spherical", f"{B.FC_MAIN/1e9:.1f} GHz"),
                                   ("hi", f"{B.FC_PO_KNEE/1e9:.2f} GHz (PO knee)"))):
        v = []
        for a in ARMS:
            src = J["arms"][key][a] if tg == "spherical" else J["hi_band"]["arms"][key].get(a, {})
            v.append(src.get("spherical", {}).get("per_az", {})
                     .get("in_band_ac_over_dc_db", {}).get("mean", np.nan))
        ax.bar(xs + (i - 0.5) * w, v, w, label=lab, alpha=0.9)
    ax.set_xticks(xs); ax.set_xticklabels([a.replace("sphere_", "sph_") for a in ARMS],
                                          rotation=28, ha="right", fontsize=8)
    ax.set_ylabel("in-band AC / DC [dB]")
    ax.set_title(f"(g) Both bands agree, {key}", fontsize=10.5)
    ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")

    # (8) 레벨 대 변조 — 이 라운드의 요점
    ax = fig.add_subplot(gs[2, 1])
    lv = J["level_vs_modulation"]["p3_context"]["table"]
    off = {"sphere_vol_v2": (5, -11), "sphere_eqvol_paperbox": (5, 6),
           "ours_phantom3_mesh_v1": (5, -11), "cube_vol_v1": (5, -11),
           "box_paper": (5, -11), "box_bbox_lit": (-6, 8)}
    for name, row in lv.items():
        x, y = abs(row["level_err_db"]), row["eps_mean_db"]
        ax.scatter(x, y, s=70, zorder=3,
                   color=("#c0392b" if "sphere" in name else
                          "#1b6ca8" if "ours" in name else "#95a5a6"))
        ax.annotate(name.replace("_", " "), (x, y), fontsize=6.6,
                    xytext=off.get(name, (5, 4)), textcoords="offset points")
    ax.set_xlabel("|level error| vs measured RCS [dB]  (lower = better)")
    ax.set_ylabel("azimuth spread eps [dB]  (0 = no structure)")
    ax.set_xlim(-1, 22); ax.set_ylim(-1.6, 11.5)
    ax.set_title("(h) Why the sphere looked good: level only\n"
                 "(from outputs/p3_validation_v2.json)", fontsize=10.5)
    ax.grid(alpha=0.3)

    # (9) 요약 글상자
    ax = fig.add_subplot(gs[2, 2]); ax.axis("off")
    lines = J["figure_caption_en"]
    fs = min(8.4, 8.4 * 21.0 / max(len(lines), 1))
    ax.text(0.0, 1.06, "\n".join(lines), va="top", ha="left", fontsize=fs,
            family="DejaVu Sans", linespacing=1.36, transform=ax.transAxes)
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=135)
    plt.close(fig)
    return OUT_FIG


# =========================================================================== #
#                                    main
# =========================================================================== #
def main(skip_compute=False):
    t0 = time.time()
    prereg = _write_prereg()                       # ⭐ 계산 **전에** 예측을 못박는다
    print(f"▶ 사전 예측 기록: {prereg['written_at']} sha256={prereg['sha256'][:16]}…", flush=True)

    if not skip_compute:
        launch("main", B.FC_MAIN)
        launch("hi", B.FC_PO_KNEE)

    tabs, metas = load("main")
    tabs_hi, metas_hi = load("hi")
    if not tabs:
        raise SystemExit("계산 결과가 없다 — --skip-compute 없이 다시 돌려라.")

    from drones import DRONES
    J = dict(meta=dict(
        report="report16_rung_sphere_eqvol",
        producer="benchmark/report16_rung_sphere_eqvol.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        rung_ko="사다리 한 단 — 등가부피 구의 마이크로도플러",
        question_ko=("매개변수 0 개짜리 등가부피 구를 기준 메쉬와 **똑같이 돌리면** "
                     "마이크로도플러가 얼마나 나오는가. 예측은 0 이다."),
        base_round="benchmark/report16_base.py (규약·지표의 단일 출처)",
        inherits_ko=("규약(β·위상 스텝·PRF·거리·자세·주파수)과 지표(md_metrics16)를 "
                     "report16_base 에서 그대로 import 한다 — 재구현하지 않는다."),
        tables_npz=os.path.relpath(OUT_NPZ, ROOT)))

    J["preregistration"] = prereg
    J["protocol"] = dict(
        fc_main_hz=B.FC_MAIN, fc_po_knee_hz=B.FC_PO_KNEE, el_deg=B.EL_DEG,
        range_m=B.RANGE_M, n_az=B.N_AZ, az_step_deg=360.0 / B.N_AZ,
        wavefront_headline="spherical", wavefront_control="plane", period_deg=360.0,
        monostatic=True, frame_div=FRAME_DIV, blade_div=BLADE_DIV, blade_n=BLADE_N,
        engine="pure PO on point clouds (no occlusion, no edge diffraction, scalar |Gamma|)",
        fairness_ko={
            "같은 운동학": ("모든 팔이 **같은 회전축(기체 z)·같은 rpm(호버)·같은 위상 격자**로 "
                        "돈다. 구를 안 돌리고 0 을 얻는 것은 동어반복이므로 실제로 돌렸다."),
            "같은 재질": ("구는 자기가 대체한 부위의 **면적가중 평균 |Γ|** 를 계산해서 물려받는다. "
                       "기체 전체를 대체하면 기체의 평균, 프로펠러를 대체하면 프로펠러의 값. "
                       "그리고 이 선택이 결론을 못 바꾼다는 것을 gamma_invariance 로 실측했다."),
            "같은 거리·자세·주파수": "R=10 m 모노스태틱, el 15°, 방위 24점, 3.5 GHz + 15.86 GHz 전부 동일.",
            "부피 등가": "손입력이 아니라 발산정리로 메쉬 부피를 적분해 r_eq = (3V/4π)^(1/3) 로 **계산**했다.",
            "점밀도": "모든 팔이 같은 요청 간격(λ/11)을 쓰고, 실측 최근접이웃 간격을 팔마다 기록했다.",
        })

    # ── PO 유효성 경고 (base 와 같은 출처) ─────────────────────────────────
    try:
        knee = json.load(open(os.path.join(ROOT, "outputs",
                                           "report00_po_case.json")))["s4_limits"]
        J["po_validity_warning"] = dict(
            knee_a_over_lambda=knee["po_validity_knee_a_over_lambda"],
            blade_knee_ghz=knee["feature_knee_frequencies"]["prop_blade_13p78mm_ghz"],
            production_band_ghz=B.FC_MAIN / 1e9,
            statement_ko=("마이크로도플러를 만드는 부품(프로펠러 블레이드, 폭 13.78 mm)은 "
                          f"{knee['feature_knee_frequencies']['prop_blade_13p78mm_ghz']} GHz "
                          "에서야 PO 유효 무릎을 넘는다. 생산 대역 3.5 GHz 에서는 **커널이 가장 "
                          "약한 부품이 곧 신호원**이다. 그래서 두 대역을 모두 돌렸고, 방향이 "
                          "같은지 확인했다. ⚠ 다만 이 라운드의 헤드라인(구의 변조=0)은 "
                          "PO 정확도와 무관하다 — 회전 대칭은 어떤 산란 커널에서도 성립한다."))
    except Exception as e:                                        # pragma: no cover
        J["po_validity_warning"] = dict(error=str(e))

    J["kernel_gate"] = gate_vs_base(tabs)
    J["gpu_used"] = dict(main=metas.get("gpu"), hi=metas_hi.get("gpu") if metas_hi else None)

    # ── 팔별 지표 ─────────────────────────────────────────────────────────
    def arm_blocks(tb, mt, tag):
        res = {}
        for key in DRONE_KEYS:
            proto = mt["metas"][f"{key}|proto"]
            nb = int(DRONES[key].prop_blades)
            res[key] = {}
            for arm in ARMS:
                blk = {}
                for wf in ("spherical", "plane"):
                    k = f"{tag}|{key}|{arm}|{wf}"
                    if k in tb:
                        blk[wf] = block(tb[k], proto, nb)
                if not blk:
                    continue
                blk["geometry"] = mt["metas"][f"{key}|{arm}"]["meta"]
                blk["seconds"] = mt["metas"][f"{key}|{arm}"]["seconds"]
                res[key][arm] = blk
        return res

    J["arms"] = arm_blocks(tabs, metas, "main")
    J["protocol_per_drone"] = {k: metas["metas"][f"{k}|proto"] for k in DRONE_KEYS}
    if tabs_hi:
        J["hi_band"] = dict(fc_hz=B.FC_PO_KNEE, arms=arm_blocks(tabs_hi, metas_hi, "hi"),
                            protocol_per_drone={k: metas_hi["metas"][f"{k}|proto"]
                                                for k in DRONE_KEYS})

    # ── ⭐ 헤드라인: 널 대 메쉬 ────────────────────────────────────────────
    head = {}
    for key in DRONE_KEYS:
        row = {}
        for wf in ("spherical", "plane"):
            a = J["arms"][key]
            sph = a["sphere_eqvol"][wf]
            mesh = a["mesh"][wf]
            hub = a["sph_hub"][wf]
            off = a["sphere_offaxis"][wf]
            row[wf] = dict(
                sphere_in_band_ac_over_dc_db=sph["per_az"]["in_band_ac_over_dc_db"],
                sphere_mod_depth_db=sph["mod_depth_db"],
                sphere_mod_depth_ppm=sph["mod_depth_ppm"],
                hub_sphere_in_band_ac_over_dc_db=hub["per_az"]["in_band_ac_over_dc_db"],
                mesh_in_band_ac_over_dc_db=mesh["per_az"]["in_band_ac_over_dc_db"],
                mesh_mod_depth_db=mesh["mod_depth_db"],
                offaxis_in_band_ac_over_dc_db=off["per_az"]["in_band_ac_over_dc_db"],
                mesh_minus_sphere_db=float(mesh["per_az"]["in_band_ac_over_dc_db"]["mean"] -
                                           sph["per_az"]["in_band_ac_over_dc_db"]["mean"]),
                mesh_minus_hub_db=float(mesh["per_az"]["in_band_ac_over_dc_db"]["mean"] -
                                        hub["per_az"]["in_band_ac_over_dc_db"]["mean"]),
                offaxis_minus_sphere_db=float(off["per_az"]["in_band_ac_over_dc_db"]["mean"] -
                                              sph["per_az"]["in_band_ac_over_dc_db"]["mean"]))
        head[key] = row
    J["headline_null_vs_mesh"] = head
    J["headline_null_vs_mesh"]["_what_ko"] = (
        "«대역 안 AC/DC» = 프로펠러 팁보다 빠를 수 없는 자리(1.5β 이내)에 실린 변조 전력을 "
        "동체 세기로 나눈 것. 진짜 마이크로도플러가 있으면 크고, 회전대칭체면 0(dB 로는 −∞)이다.")

    # ── ⭐ 사다리: 프리미티브가 메쉬를 얼마나 재현하나 (예측 없음) ──────────
    ladder = {}
    for key in DRONE_KEYS:
        proto = metas["metas"][f"{key}|proto"]
        nb = int(DRONES[key].prop_blades)
        ref = tabs[f"main|{key}|mesh|spherical"]
        ladder[key] = {}
        for arm in ARMS:
            if arm == "mesh":
                continue
            T = tabs[f"main|{key}|{arm}|spherical"]
            cors = [B.ac_corr(ref[i], T[i]) for i in range(T.shape[0])]
            d = {}
            for m in ("flash_contrast_db", "n_eff_orders", "width_ratio", "dc_ac_db",
                      "in_band_ac_over_dc_db", "blade_comb_frac", "sigma_eq_mean_dbsm"):
                pa = [B.md_metrics16(ref[i], proto, nb)[m] -
                      B.md_metrics16(T[i], proto, nb)[m] for i in range(T.shape[0])]
                d[f"mesh_minus_{arm}__{m}"] = B.summarize(pa)
                d[f"sign_consistency_{m}"] = float(np.mean(np.sign(pa) == np.sign(np.mean(pa))))
            ladder[key][arm] = dict(ac_corr_vs_mesh=B.summarize(cors), paired_deltas=d)
    J["ladder_vs_mesh"] = ladder
    J["ladder_vs_mesh"]["_what_ko"] = (
        "짝지은 24방위 차이(같은 자세끼리 뺀다). ac_corr 은 «변조 파형이 메쉬와 얼마나 같은 "
        "모양인가»(1=동일), paired_deltas 는 요약 지표의 차이다. ⚠ 이 항목에는 사전 예측을 "
        "걸지 않았다 — 프리미티브가 잘 맞아도 그대로 적는다.")

    # ── 널이 «격자» 임을 보이는 증거 ──────────────────────────────────────
    J["null_is_numerical"] = dict(
        convergence=metas["extras"]["null_convergence"],
        gamma_invariance=metas["extras"]["gamma_invariance"],
        dominant_order_check={
            key: dict(
                dominant_order={wf: J["arms"][key]["sphere_eqvol"][wf]["az0"]["dominant_order"]
                                for wf in ("spherical", "plane")},
                sphere_seg=J["arms"][key]["sphere_eqvol"]["geometry"]["sphere_seg"],
                n_phase=J["protocol_per_drone"][key]["n_phase"],
                predicted_grid_orders={
                    str(o): j for o, j in sorted(grid_orders(
                        J["arms"][key]["sphere_eqvol"]["geometry"]["sphere_seg"],
                        J["protocol_per_drone"][key]["n_phase"]).items())},
                blade_comb_order=int(DRONES[key].prop_blades),
                mesh_dominant_order={wf: J["arms"][key]["mesh"][wf]["az0"]["dominant_order"]
                                     for wf in ("spherical", "plane")},
                alias_of_seg={wf: bool(is_grid_order(
                    J["arms"][key]["sphere_eqvol"][wf]["az0"]["dominant_order"],
                    J["arms"][key]["sphere_eqvol"]["geometry"]["sphere_seg"],
                    J["protocol_per_drone"][key]["n_phase"])[0])
                    for wf in ("spherical", "plane")},
                grid_harmonic_j={wf: is_grid_order(
                    J["arms"][key]["sphere_eqvol"][wf]["az0"]["dominant_order"],
                    J["arms"][key]["sphere_eqvol"]["geometry"]["sphere_seg"],
                    J["protocol_per_drone"][key]["n_phase"])[1]
                    for wf in ("spherical", "plane")})
            for key in DRONE_KEYS},
        interpretability={key: dict(
            sphere_in_band_ac_frac=J["arms"][key]["sphere_eqvol"]["spherical"]["per_az"]["in_band_ac_frac"]["mean"],
            mesh_in_band_ac_frac=J["arms"][key]["mesh"]["spherical"]["per_az"]["in_band_ac_frac"]["mean"],
            sphere_metrics_interpretable_frac=J["arms"][key]["sphere_eqvol"]["spherical"]["interpretable_frac"],
            mesh_metrics_interpretable_frac=J["arms"][key]["mesh"]["spherical"]["interpretable_frac"])
            for key in DRONE_KEYS},
        what_ko=("구에 남은 잔차가 «물리» 인지 «격자» 인지 가른다. ① 지배 차수가 구를 쪼갠 경도 "
                 "분할 수(seg)에 붙어 있는가(블레이드 빗 2,4,6… 이 아니라), ② 분할을 촘촘히 하면 "
                 "따라 움직이는가, ③ 운동학이 허용하는 대역 안에 있는가. 세 가지가 다 «격자» 를 "
                 "가리키면 그 값은 계산기의 바닥이지 신호가 아니다."))

    # ── ⚠ 구 자체가 PO 로 잴 만한 크기인가 (ka 점검) ───────────────────────
    def _ka_row(r, fc):
        ka = 2.0 * math.pi * float(r) / (B.C0 / fc)
        return dict(radius_mm=1000.0 * float(r), ka=ka,
                    regime=("optical (PO ok)" if ka >= 5 else
                            "resonance (PO marginal)" if ka >= 1 else
                            "Rayleigh (PO NOT valid for level)"))
    val = {}
    for key in DRONE_KEYS:
        g_eq = J["arms"][key]["sphere_eqvol"]["geometry"]
        g_hub = J["arms"][key]["sph_hub"]["geometry"]
        g_bl = J["arms"][key]["sph_blade_rg"]["geometry"]
        row = {}
        for band, fc in (("fc_main", B.FC_MAIN), ("fc_po_knee", B.FC_PO_KNEE)):
            row[band] = dict(
                equal_volume_sphere=_ka_row(g_eq["r_equal_volume_m"], fc),
                hub_sphere=_ka_row(g_hub["sphere_radius_m"], fc),
                blade_sphere=_ka_row(g_bl["sphere_radius_m"], fc))
        # PO 가 구를 제대로 내는지: 측정 σ 대 광학극한 πr²|Γ|²
        sig_meas = J["arms"][key]["sphere_eqvol"]["spherical"]["per_az"]["sigma_eq_mean_dbsm"]["mean"]
        sig_opt = float(10 * math.log10(math.pi * g_eq["r_equal_volume_m"] ** 2 *
                                        g_eq["area_weighted_gamma"] ** 2))
        row["po_vs_optical_fc_main"] = dict(
            sigma_po_dbsm=sig_meas, sigma_optical_dbsm=sig_opt,
            delta_db=float(sig_meas - sig_opt),
            note_ko=("PO 로 계산한 등가부피 구의 σ 를 광학극한 πr²|Γ|² 와 비교한다. "
                     "ka 가 충분히 크면 둘이 붙어야 한다 — 이 팔의 «크기» 가 정상인지 확인하는 앵커."))
        val[key] = row
    val["_what_ko"] = (
        "ka = 2πr/λ 는 «구가 파장에 비해 얼마나 큰가» 다. ka ≫ 1 이면 PO 가 잘 맞고, ka < 1 "
        "(레일리 영역)이면 PO 는 세기를 크게 틀린다. ⭐ 여기서 중요한 구분: **헤드라인(회전축 위 "
        "구의 변조 = 0)은 ka 와 무관하다** — 회전 대칭은 어떤 산란 모델에서도 성립하기 때문이다. "
        "반면 ⑤ 블레이드-구 사다리의 **절대 세기**는 ka 에 의존한다. 작은 구(반경 5~14 mm)는 "
        "3.5 GHz 에서 레일리 영역이라 그 팔의 σ 절대값은 인용하면 안 되고, 15.86 GHz 판을 함께 "
        "읽어야 한다. 변조의 **모양**(폭·빗·플래시)은 산란체가 어디서 어떻게 도는가 — 즉 "
        "운동학 — 이 정하므로 상대적으로 덜 흔들린다.")
    J["sphere_scattering_validity"] = val

    # ── 레벨 대 변조 — 이 라운드의 요점 ────────────────────────────────────
    lv = dict()
    try:
        p3 = json.load(open(os.path.join(ROOT, "outputs", "p3_validation_v2.json")))
        tbl = {k: dict(what=v["what"], level_err_db=v["level_err_db"], rms_db=v["rms_db"],
                       eps_mean_db=v["eps_mean_db"])
               for k, v in p3["controls"]["table"].items()}
        mesh_lv = tbl["ours_phantom3_mesh_v2"]
        lv["p3_context"] = dict(
            table=tbl, source="outputs/p3_validation_v2.json (controls.table)",
            read_ko=("«세기» 만 보면 구가 좋아 보인다 — 그러나 그 구는 논문이 적어 둔 상자 치수의 "
                     "부피로 만든 구(sphere_eqvol_paperbox)다. ⭐ **우리 메쉬의 실제 부피로 만든 "
                     "구(sphere_vol_v2)는 레벨 오차도 rms 도 우리 메쉬보다 나쁘다.** 즉 «매개변수 "
                     "0 개» 라는 말은 정확하지 않다 — 어떤 부피를 먹일지는 사람이 고르고, 그 선택이 "
                     "결과를 크게 바꾼다."),
            sphere_choice_matters_db=float(tbl["sphere_eqvol_paperbox"]["level_err_db"] -
                                           tbl["sphere_vol_v2"]["level_err_db"]),
            mesh_vs_sphere_our_volume=dict(
                level_err_db=dict(mesh=mesh_lv["level_err_db"],
                                  sphere_our_volume=tbl["sphere_vol_v2"]["level_err_db"]),
                rms_db=dict(mesh=mesh_lv["rms_db"], sphere_our_volume=tbl["sphere_vol_v2"]["rms_db"]),
                mesh_better_on_rms=bool(mesh_lv["rms_db"] < tbl["sphere_vol_v2"]["rms_db"])),
            azimuth_spread_eps_db=dict(
                sphere=tbl["sphere_vol_v2"]["eps_mean_db"], mesh=mesh_lv["eps_mean_db"],
                note_ko="ε=0.00 은 구가 방위에 따라 전혀 변하지 않는다는 뜻 — 여기서 구조가 죽는다."))
    except Exception as e:                                       # pragma: no cover
        lv["p3_context"] = dict(error=str(e))
    lv["this_round"] = {key: dict(
        sigma_mean_dbsm=dict(
            mesh=J["arms"][key]["mesh"]["spherical"]["per_az"]["sigma_eq_mean_dbsm"]["mean"],
            sphere=J["arms"][key]["sphere_eqvol"]["spherical"]["per_az"]["sigma_eq_mean_dbsm"]["mean"]),
        sigma_azimuth_sd_db=dict(
            mesh=J["arms"][key]["mesh"]["spherical"]["per_az"]["sigma_eq_mean_dbsm"]["sd"],
            sphere=J["arms"][key]["sphere_eqvol"]["spherical"]["per_az"]["sigma_eq_mean_dbsm"]["sd"]),
        modulation_db=dict(
            mesh=J["arms"][key]["mesh"]["spherical"]["per_az"]["in_band_ac_over_dc_db"]["mean"],
            sphere=J["arms"][key]["sphere_eqvol"]["spherical"]["per_az"]["in_band_ac_over_dc_db"]["mean"]),
        optical_sigma_pec_dbsm=J["arms"][key]["sphere_eqvol"]["geometry"]["optical_sigma_dbsm"],
        r_equal_volume_m=J["arms"][key]["sphere_eqvol"]["geometry"]["r_equal_volume_m"],
        drone_volume_l=1000.0 * J["arms"][key]["sphere_eqvol"]["geometry"]["drone_volume_m3"],
        # ⭐ 이 라운드에서 직접 잰 «무승부 대 완패» 한 쌍
        sigma_gap_db=float(abs(
            J["arms"][key]["sphere_eqvol"]["spherical"]["per_az"]["sigma_eq_mean_dbsm"]["mean"] -
            J["arms"][key]["mesh"]["spherical"]["per_az"]["sigma_eq_mean_dbsm"]["mean"])),
        modulation_gap_db=float(
            J["arms"][key]["mesh"]["spherical"]["per_az"]["in_band_ac_over_dc_db"]["mean"] -
            J["arms"][key]["sphere_eqvol"]["spherical"]["per_az"]["in_band_ac_over_dc_db"]["mean"]))
        for key in DRONE_KEYS}
    lv["headline_ko"] = (
        "⭐⭐ 같은 커널·같은 거리·같은 자세 앙상블에서 **24방위 평균 세기는 구와 메쉬가 "
        + ", ".join(f"{k} {lv['this_round'][k]['sigma_gap_db']:.2f} dB" for k in DRONE_KEYS) +
        " 안에서 붙는다** — 사실상 무승부다. 그런데 같은 표에서 방위 산포는 메쉬 "
        + ", ".join(f"{k} {lv['this_round'][k]['sigma_azimuth_sd_db']['mesh']:.1f} dB" for k in DRONE_KEYS) +
        " 대 구 ~0.0 dB 이고, 마이크로도플러는 "
        + ", ".join(f"{k} {lv['this_round'][k]['modulation_gap_db']:.0f} dB" for k in DRONE_KEYS) +
        " 차이가 난다. 즉 **평균 세기로는 무승부, 구조로는 경기가 성립하지 않는다.** "
        "이것이 지도교수 지적의 정확한 경계선이다 — 지적은 «세기» 축에서 맞고, «시간에 따른 "
        "변조» 축에서는 적용되지 않는다.")
    lv["_what_ko"] = ("한 표에 «세기» 와 «변조» 를 같이 놓는다. 구는 세기 쪽에서 싸움이 되지만 "
                      "변조 쪽에서는 경기 자체가 성립하지 않는다. "
                      "⚠ optical_sigma_pec_dbsm 은 |Γ|=1(완전도체) 기준 πr² 이고, 재질을 먹인 "
                      "값과의 대조는 sphere_scattering_validity.po_vs_optical_fc_main 에 있다.")
    J["level_vs_modulation"] = lv

    # ── ⭐⭐ 예측 채점 ─────────────────────────────────────────────────────
    pt = dict(P1_threshold_pass_db=PREDICTION["P1_threshold_pass_db"],
              P1_threshold_fail_db=PREDICTION["P1_threshold_fail_db"],
              P3_threshold_db=PREDICTION["P3_threshold_db"],
              P4_threshold_db=PREDICTION["P4_threshold_db"])
    worst_null, worst_null_where = -1e9, None
    for key in DRONE_KEYS:
        for arm in SPHERE_ARMS:
            for tagname, src in (("main", J["arms"]), ("hi", J.get("hi_band", {}).get("arms", {}))):
                if key not in src or arm not in src[key]:
                    continue
                for wf in ("spherical", "plane"):
                    if wf not in src[key][arm]:
                        continue
                    v = src[key][arm][wf]["per_az"]["in_band_ac_over_dc_db"]["max"]
                    if v > worst_null:
                        worst_null, worst_null_where = float(v), f"{tagname}|{key}|{arm}|{wf}"
    best_ctrl, best_ctrl_where = 1e9, None
    for key in DRONE_KEYS:
        v = J["arms"][key]["sphere_offaxis"]["spherical"]["per_az"]["in_band_ac_over_dc_db"]["min"]
        if v < best_ctrl:
            best_ctrl, best_ctrl_where = float(v), f"main|{key}|sphere_offaxis|spherical"
    gaps = [J["headline_null_vs_mesh"][k]["spherical"]["mesh_minus_sphere_db"] for k in DRONE_KEYS]
    pt.update(
        P1_worst_null_in_band_ac_over_dc_db=worst_null, P1_worst_at=worst_null_where,
        P1_verdict=("PASS" if worst_null <= PREDICTION["P1_threshold_pass_db"] else
                    ("FAIL" if worst_null > PREDICTION["P1_threshold_fail_db"] else "MARGINAL")),
        P2_dominant_order_is_grid=all(all(v["alias_of_seg"].values()) for v in
                                      J["null_is_numerical"]["dominant_order_check"].values()),
        P2_verdict=("PASS" if all(all(v["alias_of_seg"].values()) for v in
                                  J["null_is_numerical"]["dominant_order_check"].values())
                    else "CHECK"),
        P3_worst_control_in_band_ac_over_dc_db=best_ctrl, P3_worst_at=best_ctrl_where,
        P3_verdict="PASS" if best_ctrl >= PREDICTION["P3_threshold_db"] else "FAIL",
        P4_min_mesh_minus_sphere_db=float(min(gaps)),
        P4_verdict="PASS" if min(gaps) >= PREDICTION["P4_threshold_db"] else "FAIL",
        P5_no_prediction_registered=True)
    pt["overall"] = ("PASS" if all(pt[f"P{i}_verdict"] == "PASS" for i in (1, 3, 4))
                     else "MIXED")
    pt["read_ko"] = ("사전 예측은 계산 전에 못박혔고(preregistration.sha256), 여기서 그 문턱으로 "
                     "채점한다. P5(블레이드-구 사다리)는 예측을 걸지 않았으므로 채점 대상이 아니다.")
    J["prediction_test"] = pt

    # ── ⚠ 사후 진단 — 사전 문턱은 그대로 두고 «왜 아슬아슬했나» 만 밝힌다 ──
    if pt["P1_verdict"] != "PASS":
        hr = metas["extras"].get("hub_refine", {})
        worst_key = pt["P1_worst_at"].split("|")[1] if pt["P1_worst_at"] else None
        drop = {}
        for key, rows in hr.items():
            if key.startswith("_"):
                continue
            base_row = rows.get("refine_x1")
            fine_row = rows.get(f"refine_x{max(r['refine'] for k, r in rows.items()):g}")
            if base_row and fine_row:
                drop[key] = dict(
                    seg=[base_row["seg"], fine_row["seg"]],
                    n_pts=[base_row["n_pts"], fine_row["n_pts"]],
                    in_band_ac_over_dc_db=[base_row["in_band_ac_over_dc_db"]["mean"],
                                           fine_row["in_band_ac_over_dc_db"]["mean"]],
                    mod_depth_db=[base_row["mod_depth_db"]["mean"],
                                  fine_row["mod_depth_db"]["mean"]],
                    dropped_db=float(base_row["in_band_ac_over_dc_db"]["mean"] -
                                     fine_row["in_band_ac_over_dc_db"]["mean"]))
        J["posthoc_marginal_diagnosis"] = dict(
            label="POST-HOC (사전 예측 아님 — 계산 뒤에 추가한 진단)",
            verdict_unchanged=pt["P1_verdict"],
            threshold_not_moved=True,
            worst_arm=pt["P1_worst_at"], worst_value_db=pt["P1_worst_null_in_band_ac_over_dc_db"],
            hub_sphere_tessellation={
                key: dict(radius_mm=1000.0 * J["arms"][key]["sph_hub"]["geometry"]["sphere_radius_m"],
                          seg=J["arms"][key]["sph_hub"]["geometry"]["sphere_tess"]["seg"],
                          n_pts_per_sphere=J["arms"][key]["sph_hub"]["geometry"]["sphere_tess"]["n_pts"],
                          dominant_order=J["arms"][key]["sph_hub"]["spherical"]["az0"]["dominant_order"],
                          band_order=J["arms"][key]["sph_hub"]["spherical"]["band_order"])
                for key in DRONE_KEYS},
            refinement=hr, refinement_summary=drop,
            worst_corner_refined=metas["extras"].get("hub_refine_worst_corner", {}),
            worst_corner_drop_db=(
                float(metas["extras"]["hub_refine_worst_corner"]["refine_x1"]["worst_az_db"] -
                      metas["extras"]["hub_refine_worst_corner"]["refine_x8"]["worst_az_db"])
                if "hub_refine_worst_corner" in metas["extras"] else None),
            eqvol_sphere_for_comparison={
                key: dict(seg=J["arms"][key]["sphere_eqvol"]["geometry"]["sphere_seg"],
                          in_band_ac_over_dc_db=J["arms"][key]["sphere_eqvol"]["spherical"]["per_az"]["in_band_ac_over_dc_db"]["mean"])
                for key in DRONE_KEYS},
            explanation_ko=(
                "왜 하필 sph_hub 팔이 아슬아슬했나: 그 팔의 구는 프로펠러 **부피만큼만** 크기라 "
                "반경이 6~14 mm 밖에 안 되고, 그래서 삼각형이 경도로 9~13 조각밖에 안 깔린다. "
                "성긴 격자가 만드는 잔차는 **낮은 차수**(9~18)에 앉는데, 그 자리가 하필 "
                "«팁보다 느린» 대역 안이라 진짜 마이크로도플러인 척 계상된다. 같은 팔의 구를 "
                "더 촘촘히 쪼개면 잔차가 내려간다(refinement_summary). 반면 기체 전체를 대체한 "
                "등가부피 구는 반경이 커서 격자가 촘촘하고(경도 39~71 조각), 잔차가 대역 밖에 "
                "앉아 −85~−123 dB 로 훨씬 깊다. ⭐ 즉 −58.7 dB 는 «구가 낸 변조» 가 아니라 "
                "«우리가 아주 작은 구를 성기게 그린 값» 이다. 그래도 사전 문턱은 옮기지 않는다 — "
                "예측을 걸 때 이 사정을 몰랐던 것이 사실이고, 그것이 기록으로 남아야 한다."),
            direct_test_ko=(
                "⭐ 두루뭉술하게 넘기지 않기 위해 **문제가 된 바로 그 구석**(mavic4pro · sph_hub · "
                "평면파 · 24방위 전부)을 구 분할만 바꿔 다시 쟀다 — worst_corner_refined 참조. "
                "최악 방위의 값이 분할 8배에서 크게 내려간다면(worst_corner_drop_db) 그 값은 "
                "물리적 변조가 아니라 격자였다는 직접 증거다."),
            what_would_have_been_ko=(
                "참고로 헤드라인 팔(sphere_eqvol)만 놓고 채점하면 P1 은 전 구석에서 통과한다. "
                "그러나 사전 예측은 sph_hub 도 포함해서 걸었으므로 채점은 MARGINAL 이다."))
        # 헤드라인 팔만으로 채점하면 어땠는지도 계산해 둔다(투명성 — 판정 대체가 아니다)
        w2 = -1e9
        for key in DRONE_KEYS:
            for tagname, src in (("main", J["arms"]), ("hi", J.get("hi_band", {}).get("arms", {}))):
                if key not in src or "sphere_eqvol" not in src[key]:
                    continue
                for wf in ("spherical", "plane"):
                    if wf in src[key]["sphere_eqvol"]:
                        w2 = max(w2, src[key]["sphere_eqvol"][wf]["per_az"]["in_band_ac_over_dc_db"]["max"])
        J["posthoc_marginal_diagnosis"]["headline_arm_only_worst_db"] = float(w2)
        J["posthoc_marginal_diagnosis"]["headline_arm_only_verdict"] = (
            "PASS" if w2 <= PREDICTION["P1_threshold_pass_db"] else "MARGINAL")

    # ── 파면 대조 (구면 vs 평면) ──────────────────────────────────────────
    wfc = {}
    for key in DRONE_KEYS:
        wfc[key] = {}
        for arm in ARMS:
            a = J["arms"][key][arm]
            if "plane" not in a:
                continue
            cs = [B.ac_corr(tabs[f"main|{key}|{arm}|spherical"][i],
                            tabs[f"main|{key}|{arm}|plane"][i]) for i in range(B.N_AZ)]
            wfc[key][arm] = dict(
                ac_corr_sph_vs_plane=B.summarize(cs),
                delta_in_band_ac_over_dc_db=float(
                    a["spherical"]["per_az"]["in_band_ac_over_dc_db"]["mean"] -
                    a["plane"]["per_az"]["in_band_ac_over_dc_db"]["mean"]))
    J["wavefront_control"] = dict(
        rows=wfc, what_ko=("헤드라인은 구면파다. 평면파는 «거리 곡률이 결론을 바꾸나» 를 묻는 "
                           "대조군이다. 구의 널은 두 파면 모두에서 성립해야 한다 — 회전 대칭은 "
                           "파면과 무관하기 때문이다."),
        caveat_ko=("⚠ 널 팔(sphere_eqvol·sph_hub)의 ac_corr 은 **읽지 말 것**. 그 팔의 AC 는 "
                   "격자 잔차, 즉 잡음이라 «구면파 잡음 대 평면파 잡음» 의 상관을 잰 값이 된다 "
                   "— 낮게 나오는 것이 정상이고 아무 의미가 없다. 널에서 확인할 것은 오직 "
                   "«두 파면 모두에서 잔차가 바닥에 있는가» 뿐이고, 그 답은 예다. "
                   "ac_corr 이 뜻을 갖는 팔은 실제 변조가 있는 mesh·sph_blade_* 뿐이다."))

    # ── 기하 요약 (계산된 값들을 한 곳에) ─────────────────────────────────
    J["geometry_summary"] = {key: dict(
        drone_volume_l=1000.0 * J["arms"][key]["sphere_eqvol"]["geometry"]["drone_volume_m3"],
        r_equal_volume_mm=1000.0 * J["arms"][key]["sphere_eqvol"]["geometry"]["r_equal_volume_m"],
        drone_area_weighted_gamma=J["arms"][key]["sphere_eqvol"]["geometry"]["area_weighted_gamma"],
        prop_volume_ml=1e6 * J["arms"][key]["mesh"]["geometry"]["prop_volume_m3"],
        prop_tip_radius_mm=1000.0 * J["arms"][key]["mesh"]["geometry"]["prop_tip_radius_m"],
        prop_scatter_centroid_radius_mm=1000.0 * J["arms"][key]["mesh"]["geometry"]["prop_scatter_centroid_radius_m"],
        prop_scatter_centroid_radius_blade_only_mm=1000.0 * J["arms"][key]["mesh"]["geometry"]["prop_scatter_centroid_radius_blade_only_m"],
        blade_sphere_radius_mm=1000.0 * J["arms"][key]["sph_blade_rg"]["geometry"]["sphere_radius_m"],
        blade_sphere_placement_over_tip=J["arms"][key]["sph_blade_rg"]["geometry"]["placement_radius_over_tip"],
        rotor_arm_radius_mean_mm=1000.0 * J["arms"][key]["sphere_eqvol"]["geometry"]["rotor_arm_radius_mean_m"],
        point_spacing_actual_mm=dict(
            mesh=1000.0 * J["arms"][key]["mesh"]["geometry"]["actual_spacing_m"],
            sphere=1000.0 * J["arms"][key]["sphere_eqvol"]["geometry"]["actual_spacing_m"]))
        for key in DRONE_KEYS}
    J["geometry_summary"]["_what_ko"] = ("등가부피 반경·구 배치 반경·재질 가중은 전부 메쉬에서 "
                                         "적분해 **계산**한 값이다. 손입력 없음.")

    J["metric_definitions"] = dict(
        source="report16_base.md_metrics16 (재구현 금지 — 그대로 import)",
        mod_depth_db=("이 라운드에서 추가한 쉬운 말 지표: 한 바퀴 도는 동안 되돌아오는 신호가 "
                      "몇 % 흔들리나 = max|E(φ)−평균|/|평균|. dB 와 ppm 으로도 준다. "
                      "회전대칭체의 이론값은 0(dB 로는 −∞)."),
        in_band_ac_over_dc_db=("팁보다 빠를 수 없는 자리(|m| ≤ 1.5β)에 실린 변조 전력 ÷ 동체 전력. "
                               "이 라운드의 헤드라인 척도."),
        caveat_ko=("dc_ac_db 계열은 우리 커널에 가림이 없어서 동체가 과대 계상된다 — 팔 사이 "
                   "차이만 쓰고 절대값은 인용하지 말 것."))

    J["findings"] = _findings(J)
    J["figure_caption_en"] = _caption(J)

    # ── 그림·표 저장 ──────────────────────────────────────────────────────
    try:
        J["figures"] = dict(main=os.path.relpath(make_figure(J, tabs, metas, tabs_hi), ROOT))
    except Exception as e:                                       # pragma: no cover
        J["figures"] = dict(error=f"{type(e).__name__}: {e}")
        import traceback; traceback.print_exc()

    np.savez_compressed(OUT_NPZ, **{k.replace("|", "__"): v for k, v in tabs.items()},
                        **{("hi__" + k.replace("|", "__")): v for k, v in tabs_hi.items()})
    J["meta"]["seconds"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✔ {OUT_JSON}")
    print(f"✔ {OUT_NPZ}")
    print(f"✔ {J.get('figures', {}).get('main')}")
    for k, v in J["findings"].items():
        if k.startswith("_"):
            continue
        print(f"  · {k}: {v}")
    return J


def _findings(J):
    """산출물의 한 줄 요약들 — 숫자는 전부 위에서 계산된 값을 다시 읽어 쓴다."""
    f = {}
    pt = J["prediction_test"]
    keys = DRONE_KEYS
    pr = J["preregistration"]
    f["01_prereg"] = (f"사전 예측을 계산 전에 못박았다(sha256 {pr['sha256'][:12]}…, "
                      f"{pr['first_written_at']} — 첫 계산 결과 {pr['first_result_written_at']} "
                      f"보다 앞섬: {pr['prereg_precedes_first_result']}, 이번 라운드에서 남긴 "
                      f"예측 파일 {len(pr['all_stamps'])}개가 전부 동일: {pr['all_identical']}). "
                      f"채점 결과: {pt['overall']}.")
    f["02_null"] = ("⭐ 회전축 위의 등가부피 구는 24방위·두 대역·두 파면 어디서도 변조를 못 냈다 — "
                    "헤드라인 팔(sphere_eqvol)의 가장 큰 잔차가 "
                    + (f"{J['posthoc_marginal_diagnosis']['headline_arm_only_worst_db']:.1f} dB"
                       if "posthoc_marginal_diagnosis" in J else "n/a") +
                    ". 다만 사전 예측에는 프로펠러만 구로 바꾼 팔(sph_hub)도 포함시켰고 그쪽에서 "
                    f"{pt['P1_worst_null_in_band_ac_over_dc_db']:.1f} dB "
                    f"({pt['P1_worst_at']})가 나와 사전 문턱 {pt['P1_threshold_pass_db']:.0f} dB 를 "
                    f"살짝 넘겼다 → 예측 P1 = {pt['P1_verdict']}. **문턱은 옮기지 않았다.** "
                    "원인은 사후 진단에 적었다(아주 작은 구를 성기게 그린 격자 잔차).")
    f["03_depth"] = ("쉬운 말로: 구는 한 바퀴 도는 동안 되돌아오는 신호가 "
                     + ", ".join(f"{k} {J['arms'][k]['sphere_eqvol']['spherical']['mod_depth_ppm']['mean']:.3g} ppm"
                                 for k in keys) +
                     " 만큼만 흔들렸다(백만분율). 진짜 메쉬는 "
                     + ", ".join(f"{k} {J['arms'][k]['mesh']['spherical']['mod_depth_ppm']['mean']/1e4:.1f}%"
                                 for k in keys) + " 흔들린다.")
    f["04_control"] = ("⭐ 동어반복이 아니다: 같은 구를 회전축에서 비켜 놓자 같은 코드가 "
                       f"{pt['P3_worst_control_in_band_ac_over_dc_db']:.1f} dB 의 큰 변조를 냈다"
                       f"(예측 P3 = {pt['P3_verdict']}). 즉 «0» 은 죽은 코드가 아니라 대칭이다.")
    f["05_gap"] = (f"구조가 마이크로도플러에 기여하는 양 = 메쉬 − 구 = 최소 "
                   f"{pt['P4_min_mesh_minus_sphere_db']:.0f} dB (예측 P4 = {pt['P4_verdict']}). "
                   "RCS 절대 레벨에서는 몇 dB 다투던 것이 여기서는 «있음 대 없음» 이 된다.")
    f["06_grid"] = ("남은 잔차는 물리가 아니라 격자다: 지배 차수가 구를 쪼갠 경도 분할 수에 붙어 "
                    f"있고(P2 = {pt['P2_verdict']}), 분할을 촘촘히 하면 따라 움직인다. "
                    + (f"문제가 됐던 바로 그 구석도 분할 8배에서 "
                       f"{J['posthoc_marginal_diagnosis']['worst_corner_drop_db']:.0f} dB 내려갔다."
                       if J.get("posthoc_marginal_diagnosis", {}).get("worst_corner_drop_db") else ""))
    f["06b_level_tie"] = J["level_vs_modulation"].get("headline_ko", "")
    f["06c_sphere_anchor"] = (
        "구 팔 자체가 제대로 계산됐다는 앵커: PO 로 낸 등가부피 구의 σ 가 광학극한 πr²|Γ|² 와 "
        + ", ".join(f"{k} {J['sphere_scattering_validity'][k]['po_vs_optical_fc_main']['delta_db']:+.2f} dB"
                    for k in keys) + " 로 일치한다. 즉 «구가 변조를 못 낸다» 가 «구를 잘못 그렸다» "
        "때문일 가능성은 닫혔다.")
    # ⑤ 예측 없음 — 사다리
    lad = J["ladder_vs_mesh"]
    f["07_ladder_no_prediction"] = (
        "⚠ 예측 없음 항목: 구를 «블레이드가 있는 반경» 에 갖다 놓으면 변조가 살아난다 — "
        + ", ".join(f"{k} {J['arms'][k]['sph_blade_rg']['spherical']['per_az']['in_band_ac_over_dc_db']['mean']:.1f} dB "
                    f"(메쉬 {J['arms'][k]['mesh']['spherical']['per_az']['in_band_ac_over_dc_db']['mean']:.1f} dB)"
                    for k in keys) + ".")
    f["08_ladder_cost"] = (
        "다만 그 순간 «매개변수 0 개» 가 아니게 된다 — 반경과 블레이드 수를 사람이 넣어야 하고, "
        "그 선택이 도플러 폭을 그대로 결정한다. 폭 비(도플러 가장자리 ÷ 팁 도플러)는 "
        + ", ".join(f"{k}: CAD {J['arms'][k]['mesh']['spherical']['per_az']['width_ratio']['mean']:.2f} vs "
                    f"무게중심구 {J['arms'][k]['sph_blade_rg']['spherical']['per_az']['width_ratio']['mean']:.2f} vs "
                    f"팁구 {J['arms'][k]['sph_blade_tip']['spherical']['per_az']['width_ratio']['mean']:.2f}"
                    for k in keys) +
        " — ⭐ CAD 메쉬는 아무것도 안 알려 줘도 1.0 근처를 스스로 맞추고, 구 모델은 어느 반경을 "
        "먹이느냐에 따라 답이 왔다갔다 한다.")
    f["09_flash"] = (
        "⭐ 구 모델이 못 흉내내는 것: **플래시 대조비**(블레이드가 시선에 수직으로 설 때 튀는 "
        "정도). CAD 메쉬 대 블레이드-구 = "
        + ", ".join(f"{k} {J['arms'][k]['mesh']['spherical']['per_az']['flash_contrast_db']['mean']:.1f} "
                    f"vs {J['arms'][k]['sph_blade_rg']['spherical']['per_az']['flash_contrast_db']['mean']:.1f} dB"
                    for k in keys) +
        ". 구는 어느 방향에서 봐도 같아서 «면이 정렬되는 순간» 이 없다 — 넓적한 면이 있어야 "
        "생기는 특징이라 반경·개수를 넣어 줘도 살아나지 않는다.")
    f["10_waveform"] = (
        "파형까지 같지는 않다: 블레이드-구 모델의 변조 파형이 메쉬와 이루는 상관은 "
        + ", ".join(f"{k} {lad[k]['sph_blade_rg']['ac_corr_vs_mesh']['mean']:.2f}" for k in keys) +
        " 다(1=동일). 즉 «변조가 있냐 없냐» 만 쓰는 검출기라면 프리미티브로 충분하고, "
        "폭·플래시·정합필터 템플릿을 쓸 거면 형상이 필요하다. **이 갈림이 이 라운드의 실제 결론이다.**")
    f["11_level_context"] = J["level_vs_modulation"]["p3_context"].get("read_ko", "")
    f["12_limit"] = ("⚠ 한계: 프로펠러 블레이드(13.78 mm)는 15.86 GHz 에서야 PO 유효 무릎을 넘는다 — "
                     "생산 대역에서는 신호를 만드는 부품이 곧 커널이 가장 약한 부품이다. 두 대역을 "
                     "모두 돌려 방향이 같음을 확인했다. 다만 헤드라인(구의 변조 = 0)은 커널 정확도와 "
                     "무관하다 — 회전 대칭은 어떤 산란 모델에서도 성립한다. 가림 없음도 그대로다.")
    f["13_limit_ka"] = ("⚠ 한계 하나 더: 블레이드-구 모델의 구는 반경 5~14 mm 라 3.5 GHz 에서 "
                        "ka<1(레일리 영역)이다 — 그 팔의 **절대 세기**는 PO 로 못 믿는다. "
                        "그래서 15.86 GHz 판을 같이 실었고, ⑦~⑩ 의 결론(변조는 살아나지만 폭·플래시·"
                        "파형은 다르다)은 두 대역에서 같은 방향이다. 자세한 ka 표는 "
                        "sphere_scattering_validity 에 있다.")
    f["_ordering_ko"] = ("01~06 은 사전 예측이 걸린 항목, 07~10 은 **예측을 걸지 않은** 항목이다. "
                         "07~10 이 크게 나왔더라도 «맞췄다» 고 말하지 않는다.")
    return f


def _caption(J):
    pt = J["prediction_test"]
    k = "matrice4e"
    ph = J.get("posthoc_marginal_diagnosis", {})
    out = [
        "PRE-REGISTERED PREDICTION (hash-stamped before compute):",
        "  the equal-volume sphere, spun on its own axis,",
        "  must show ZERO micro-Doppler.",
        "",
        f"  P1 null      <= {pt['P1_threshold_pass_db']:.0f} dB : {pt['P1_verdict']}"
        f"   (worst {pt['P1_worst_null_in_band_ac_over_dc_db']:.1f} dB)",
        f"  P2 grid-only residual        : {pt['P2_verdict']}",
        f"  P3 positive control >= {pt['P3_threshold_db']:.0f} dB: {pt['P3_verdict']}"
        f"   (worst {pt['P3_worst_control_in_band_ac_over_dc_db']:.1f} dB)",
        f"  P4 mesh - sphere >= {pt['P4_threshold_db']:.0f} dB   : {pt['P4_verdict']}"
        f"   (min {pt['P4_min_mesh_minus_sphere_db']:.0f} dB)",
        "  P5 blade-radius spheres   : NO PREDICTION REGISTERED",
    ]
    if ph:
        segs = [v["seg"] for v in ph["hub_sphere_tessellation"].values()]
        out += ["",
                "P1 is MARGINAL and the threshold was NOT moved. The offender",
                f"is the tiny hub sphere (r 6-14 mm) drawn with only {min(segs)}-{max(segs)} facets",
                "around, so its grid residual lands at a low order INSIDE the",
                f"kinematic band. Headline arm alone: {ph['headline_arm_only_worst_db']:.0f} dB. Refining that",
                f"same worst corner drops it by {ph.get('worst_corner_drop_db') or 0:.0f} dB -> it was the grid."]
    out += [
        "",
        "P5 (no prediction) came out SPLIT: spheres at the blade radius DO",
        "modulate, as much as the mesh or more -- but flash contrast is",
        "~14 dB weaker, Doppler width depends on which radius you feed",
        "them (0.6 vs 1.1 against the mesh's 0.9-1.0), and the waveform",
        "correlates with the mesh only 0.2-0.7.",
        "",
        "FAIRNESS: every arm shares rotation axis, rpm, phase grid, range,",
        "aspect, band and material weighting. The sphere is really spun --",
        "a static sphere would be a tautology.",
        (f"GATE vs report16_base mesh tables: {J['kernel_gate'].get('verdict')}"
         f" (max rel {J['kernel_gate'].get('max_rel'):.1e})"
         if J["kernel_gate"].get("max_rel") is not None else "GATE: n/a"),
        "",
        f"CAVEAT: blade width 13.78 mm clears the PO knee only at "
        f"{B.FC_PO_KNEE/1e9:.2f} GHz, so",
        "both bands are run. The null itself is kernel-independent:",
        "rotational symmetry holds for any scatterer model.",
        f"Reference drone in (a),(c),(e),(g): {k}.",
    ]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compute", action="store_true")
    a = ap.parse_args()
    main(skip_compute=a.skip_compute)
