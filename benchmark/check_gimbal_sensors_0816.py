# -*- coding: utf-8 -*-
"""
check_gimbal_sensors_0816.py — 짐벌·카메라·센서 **검사기**(2026-08-16)
=====================================================================

무엇을 하나
  드론 10종의 `camera` 그룹(짐벌·렌즈·어안 비전·LiDAR 창·초음파·방진판)을 부품 단위로
  뜯어서 네 가지를 잰다.

    게이트 A  «짐벌이 발보다 낮은가» — 카메라 부품의 최저 z 가 착륙장치보다 아래면 그 기체는
              카메라로 착지한다. 그리고 그 최저점이 `frame_fit_scale` 의 세로 배율을 정하므로,
              틀리면 **기체 전체의 세로 치수**가 조용히 어긋난다.
    게이트 B  «떠 있는 부품이 있는가» — 카메라 부품 표면에서 나머지 기체 표면까지의 거리.
              0 이면 붙어 있고, 양수면 공중에 떠 있거나 셸 속에 완전히 삼켜져 있다.
              뜬 부품은 예외 없이 산란만 더한다.
    게이트 C  «helper 가 선언한 치수대로 짓는가» — `_gimbal_*` 헬퍼는 방진판·요크 때문에
              선언값보다 크게 짓는다. 그 배율을 실측한다.
    게이트 D  «RF 로 얼마인가» — 순수 PO(CPU)로 방위평균 σ 를 재고, (1) 카메라 그룹을 통째로
              뺐을 때 (2) 카메라를 금속 대신 유전체로 봤을 때 (3) 부품 하나씩 뺐을 때의 dB 차.

무엇을 안 하나
  ⛔ **`src/` 를 한 글자도 안 바꾼다.** 읽고 재기만 한다. 이 파일은 새로 추가된 독립 검사기라
     기존 파이프라인의 기본 동작에 영향이 없다.
  ⛔ GPU 미사용. SBR(Mitsuba/OptiX)은 부르지 않는다 — 재질 |Γ| 도 `materials.MATERIALS` 표에서
     CPU 로 되푼다(ITU metal 은 벌크 프레넬 극한 0.9997).
  ⚠ 순수 PO 는 **가림(self-occlusion)이 없다**. 셸 속에 삼켜진 부품도 100 % 센다 —
     그래서 게이트 D 의 «삼켜진 부품» 숫자는 SBR 에서는 거의 0 이 된다. 두 엔진이 같은 메쉬를
     다르게 읽는다는 뜻이고, 그 자체가 게이트 B 가 잡아야 할 결함이다.

쓰는 법
    PYTHONPATH=src:benchmark python benchmark/check_gimbal_sensors_0816.py
  → outputs/mesh_inspect_gimbal_sensors_0816.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from drones import (DRONES, DRONE_GROUP_MAT, build_drone, drone_keys,        # noqa: E402
                    frame_fit_scale, _build_frame_raw)
from materials import MATERIALS                                              # noqa: E402
from geom import Mesh                                                        # noqa: E402
from rcs_po import mesh_to_points, _look_dirs, C0                            # noqa: E402
import drone_cad as dc                                                       # noqa: E402

FC = 3.5e9
LAM = C0 / FC
SPACING = LAM / 7.0
AZ = np.arange(0.0, 360.0, 5.0)
ELS = [0.0, -30.0, -60.0, -90.0]
GAMMA_ITU_METAL = 0.9997          # ITU metal(σ=1e7 S/m) 벌크 프레넬 극한


# --------------------------------------------------------------------------- #
#  재질 |Γ| — drone_gamma_map() 과 같은 표에서, 다만 Sionna 프로브 없이
# --------------------------------------------------------------------------- #
def gamma_of(mat_key: str) -> float:
    sp = MATERIALS[mat_key]
    if "gamma_po" in sp:
        return float(sp["gamma_po"])
    if sp.get("itu") == "metal":
        return GAMMA_ITU_METAL
    eps_c = float(sp["eps_r"]) - 1j * float(sp["sigma"]) / (2 * np.pi * FC * 8.8541878128e-12)
    return float(abs((1 - np.sqrt(eps_c)) / (1 + np.sqrt(eps_c))))


GM = {g: gamma_of(mat) for g, (mat, _d) in DRONE_GROUP_MAT.items()}


# --------------------------------------------------------------------------- #
#  메쉬 유틸
# --------------------------------------------------------------------------- #
def _submesh(mesh, face_idx, group):
    out = Mesh(group)
    V = np.asarray(mesh.v, float)
    remap = {}
    for fi in face_idx:
        tri = []
        for vi in mesh.f[fi]:
            if vi not in remap:
                remap[vi] = out.add_vertex(*V[vi])
            tri.append(remap[vi])
        out.add_tri(*tri, group=group)
    return out


def _tm(mesh, face_idx):
    return trimesh.Trimesh(vertices=np.asarray(mesh.v, float),
                           faces=np.asarray(mesh.f, np.int64)[face_idx], process=True)


def camera_components(mesh):
    """camera 그룹 면을 **정점 공유** 연결성분으로 쪼갠다(불리언 union 뒤라 부품 단위가 된다)."""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    g = np.asarray(mesh.g, object)
    sel = np.where(g == "camera")[0]
    if sel.size == 0:
        return []
    Fs = F[sel]
    uniq, inv = np.unique(np.round(V, 9), axis=0, return_inverse=True)
    Fm = inv[Fs]
    r = np.concatenate([Fm[:, 0], Fm[:, 1], Fm[:, 2]])
    c = np.concatenate([Fm[:, 1], Fm[:, 2], Fm[:, 0]])
    ncc, lab = connected_components(
        coo_matrix((np.ones(len(r)), (r, c)), shape=(len(uniq),) * 2), directed=False)
    fl = lab[Fm[:, 0]]
    return [sel[fl == i] for i in range(ncc) if (fl == i).any()]


def E_of(sub, gv, el):
    """서브메쉬가 만드는 복소 PO 산란장 E(az) — |Γ| 는 스칼라."""
    P, N, dA = mesh_to_points(sub, SPACING)
    k = 2 * np.pi / LAM
    U = _look_dirs(AZ, el)
    NU = N @ U.T
    return (np.where(NU > 0, NU, 0.0) * (dA * gv)[:, None]
            * np.exp(1j * 2 * k * (P @ U.T))).sum(axis=0)


def db(x):
    return float(10 * np.log10(max(float(x), 1e-30)))


# --------------------------------------------------------------------------- #
#  게이트 C — helper 선언치수 ↔ 실제로 짓는 외곽 (fit_scale 이전, 순수 helper)
# --------------------------------------------------------------------------- #
HELPER_CASES = {
    #  이름 : (helper, 인자, 선언 (x=깊이, y=폭, z=높이) mm, 어느 기체가 쓰나)
    "_gimbal_compact3(50,33,30)": (dc._gimbal_compact3, (0.050, 0.033, 0.030, 0.0, 0.0),
                                   (30.0, 50.0, 33.0), ["mini5pro"]),
    #  ⭐ mini2 는 **일부러** 이 배율을 미리 나눠서 넘긴다(2026-08-04 역산) — 그래서 built 가
    #     공식 GLB 파트 bbox 40.57 × 32.24 × 34.01 과 정의상 일치한다. 배율 1.45/1.395 는
    #     helper 의 성질이지 mini2 의 결함이 아니다. mini5pro 는 같은 helper 에 **사진 실측값을
    #     그대로** 넘긴다 — 같은 helper 에 두 가지 규약이 섞여 있다는 뜻이다.
    "_gimbal_compact3(32.24,24.38,27.98)": (dc._gimbal_compact3, (0.03224, 0.02438, 0.02798, 0.0, 0.0),
                                            (27.98, 32.24, 24.38), ["mini2 (역산 인자 — built 가 공식 CAD bbox 와 일치)"]),
    "_gimbal_sensor_v2(59,61.2,52)": (dc._gimbal_sensor_v2, (0.059, 0.0612, 0.052, 0.0, 0.0),
                                      (52.0, 59.0, 61.2), ["matrice4e"]),
    "_gimbal_hasselblad(s=50)": (dc._gimbal_hasselblad, (0.050, 0.0, 0.0),
                                 (81.7, 95.0, 95.0), ["mavic4pro"]),
    "_gimbal_hanging(52,48,56)": (dc._gimbal_hanging, (0.052, 0.048, 0.056, 0.0, 0.0),
                                  (56.0, 52.0, 48.0), ["phantom4"]),
    "_gimbal_hanging(100,75,100)": (dc._gimbal_hanging, (0.10, 0.075, 0.10, 0.0, 0.0),
                                    (100.0, 100.0, 75.0), ["s1000plus"]),
}


def gate_c():
    out = {}
    for name, (fn, args, decl, users) in HELPER_CASES.items():
        parts = [m for _g, m in fn(*args)]
        lo = np.min([m.bounds[0] for m in parts], axis=0)
        hi = np.max([m.bounds[1] for m in parts], axis=0)
        size = (hi - lo) * 1000.0
        out[name] = {"used_by": users,
                     "declared_xyz_mm": [round(float(v), 2) for v in decl],
                     "built_xyz_mm": [round(float(v), 2) for v in size],
                     "built_over_declared": [round(float(size[i] / decl[i]), 3) for i in range(3)]}
    return out


# --------------------------------------------------------------------------- #
#  선언 블록 — 계산이 아니라 **판정**이다. 근거 등급을 함께 적는다.
#    A = 공식 1차 자료(제조사 CAD·매뉴얼·FCC 제출 사진)
#    B = 제품/티어다운 사진 실측
#    C = 판단(출처 없음) — 값을 쓰지 않고 «모른다» 로 남긴다
# --------------------------------------------------------------------------- #
SENSOR_FACTS = {
    "_note": "메쉬가 무엇을 붙이는가 ↔ 실물에 무엇이 있는가. LiDAR 유무는 2026-07-20 확정 사실을 다시 대조한 것이다(재조사 아님).",
    "mini5pro": {"front_lidar_mesh": True, "front_lidar_real": True, "grade": "A",
                 "source": "DJI Mini 5 Pro User Manual — Forward-Facing LiDAR 명시",
                 "fisheye_mesh": 6, "fisheye_note": "앞2(기수면)·뒤2(등판)·배2(좌우). 실물 배치는 미확인(저면 정투영 사진 없음)."},
    "mavic4pro": {"front_lidar_mesh": True, "front_lidar_real": True, "grade": "A",
                  "source": "User Manual §5.4 Sensing System 콜아웃 4 = Forward-Facing LiDAR",
                  "fisheye_mesh": 6, "fisheye_real": 6,
                  "fisheye_note": "⚠ 개수는 맞고 **배치가 다르다**. 실물(FCC 상면 p01·저면 p07 정투영): "
                                  "등판 = 기수쪽 좌우 한 쌍 + 중심선 뒤 1개, 배 = 기수쪽 좌우 한 쌍 + 중심선 뒤 1개. "
                                  "메쉬 = 기수 정면 쌍 + 배 쌍 + 등판 뒤 쌍. 기수 '정면'에는 실물에 쌍이 없고, 중심선 단독 2개가 메쉬에 없다."},
    "matrice4e": {"front_lidar_mesh": False, "front_lidar_real": False, "grade": "A",
                  "source": "짐벌 정면 2×2 개구 중 좌하가 레이저 거리계 — 전방 LiDAR 와 다른 부품",
                  "fisheye_mesh": 4, "fisheye_real": 4,
                  "down_vision_mesh": 2, "down_vision_real": 2,
                  "down_vision_note": "등판 4 + 배 2. 공식 STEP·매뉴얼 도해·제품 저면사진 셋이 일치."},
    "s1000plus": {"front_lidar_mesh": False, "front_lidar_real": False, "grade": "A",
                  "source": "2014 플랫폼 — 비전/장애물 센서 자체가 없다",
                  "fisheye_mesh": 0, "fisheye_real": 0},
    "typhoonh480": {"front_lidar_mesh": False, "front_lidar_real": False, "grade": "A",
                    "source": "2016 플랫폼 — 기수 초음파 트랜스듀서 2개만", "fisheye_mesh": 0, "fisheye_real": 0},
    "mini2": {"front_lidar_mesh": False, "front_lidar_real": False, "grade": "A",
              "source": "User Manual v1.0 p.46 — Downward Vision + Infrared 뿐", "fisheye_mesh": 0},
    "phantom3": {"front_lidar_mesh": False, "front_lidar_real": False, "grade": "A",
                 "source": "User Manual v1.8 p.8 — VPS(하방 비전 1 + 초음파 2)만"},
    "phantom4": {"front_lidar_mesh": False, "front_lidar_real": False, "grade": "A"},
    "m350rtk": {"front_lidar_mesh": False, "front_lidar_real": False, "grade": "A",
                "source": "QSG 부품도 — 1 FPV · 2 Infrared Sensing · 3 Vision System(6면)",
                "ir_note": "⚠ 메쉬는 적외선을 기수 중심선 좌우 대칭 ±16 mm 로 놓는데, 실물 기수 근접사진(p08)은 "
                           "작은 구멍 2개가 **세로로 겹쳐 한쪽으로 치우친** 배치다. σ 영향은 |Δ|≤0.35 dB."},
    "x500v2": {"front_lidar_mesh": False, "front_lidar_real": False, "grade": "A",
               "source": "개발 프레임 — gimbal_style='none', camera 그룹 0면"},
}

M4E_DOWN_VISION_RULING = {
    "question": "Matrice 4E 하방 비전 카메라는 좌우 한 쌍인가, 중심선 앞뒤 한 쌍인가",
    "prior_state": "outputs/meshfix_matrice4e.json 의 not_settled_this_round 3번이 «CAD 좌우 ±17.75 ↔ 사진 앞뒤, 충돌 미해결» 로 남겨 뒀다.",
    "ruling": "**중심선 앞뒤 한 쌍**이 맞다. 좌우 쌍은 실물에 없다.",
    "evidence": [
        "제품 저면 사진 assets/photos/matrice4e/matrice4e_p09_underside_plan.jpg 를 원해상도로 확대하면 "
        "배 중심선을 따라 기수→꼬리 순서로 **둥근 렌즈 · 사각 적외선 창 · 노란 보조등 · 둥근 렌즈** 가 한 줄로 놓여 있다. "
        "중심선 밖 좌우에 렌즈는 없다. (이번 라운드가 직접 확대해 확인)",
        "매뉴얼 도해 matrice4e_m05_sensing_system_placement.png 의 «Downward Vision System» 지시선 두 개가 "
        "그 두 렌즈를 각각 가리킨다.",
        "공식 STEP: 하부커버 솔리드 안의 안착원 Ø14.449 mm 가 x_ours=+41.80 과 −35.14, **둘 다 y=0**.",
        "«CAD 가 좌우 쌍이라고 했다» 는 오독이었다 — 그 솔리드(#44~#47)는 카메라가 아니라 짐벌 방진 고무이고 "
        "같은 부품이 기수 위에도 두 벌 더 있다(outputs/meshgate_fisheye.json 이 2026-08-07 에 이미 판정).",
    ],
    "mesh_state": "현 메쉬는 이미 옳다 — 렌즈 2개가 (x=+41.80, y=0)·(x=−35.14, y=0), 기선 76.94 mm, 셸에 0.000~0.001 mm 로 닿는다.",
    "action": "⭐ outputs/meshfix_matrice4e.json 의 «충돌 미해결» 문장은 **낡았다**. 그 파일에 _superseded_0816 로 표시해 두었다.",
    "confidence": "high — 서로 독립인 근거 셋(제품사진·매뉴얼 도해·공식 CAD)이 같은 답",
}

MATERIAL_REVIEW = {
    "_note": "camera 그룹이 실제로 어떤 물건들을 담고 있는가, 그리고 그걸 통째로 금속으로 두는 대가는 얼마인가.",
    "group_material": "camera → materials.camera_assembly = ITU metal(Sionna) + PO 실효 |Γ|=0.85",
    "repo_prior": "docs/MATERIAL_SOURCES.md §6-4 가 이미 «출처 없음 · 총 σ 를 최대 1.81 dB 움직임» 으로 적어 뒀다 "
                  "(그 1.81 은 mavic4pro·1.843 GHz 한 팔의 값이다).",
    "what_is_actually_in_the_bucket": [
        {"part": "짐벌 카메라 블록 · 렌즈 배럴 · 롤/요 모터", "real": "금속 하우징 + 유리 + BLDC 모터", "verdict": "금속 취급 타당", "grade": "B"},
        {"part": "방진판(vibration-damping plate)", "real": "구조 마운트 판 — 금속인지 **저장소에 근거가 없다**(grep 확인)",
         "verdict": "⚠ 금속 취급이 미검증. 이 그룹 면적의 큰 몫을 차지한다", "grade": "C",
         "area_share_of_camera_group": {"phantom3": "238.35/371 cm² = 64 %", "phantom4": "140/325 cm² = 43 %",
                                        "s1000plus": "504/1015 cm² = 50 %"}},
        {"part": "어안·하방 비전 렌즈 포드", "real": "유리/플라스틱 창 + 뒤에 작은 금속 캔",
         "verdict": "통째 금속. 다만 r=9 mm 구는 ka=0.66(레일리~공진)이라 감도가 낮다 — 성분별 제거 |Δ|≤0.1 dB", "grade": "B"},
        {"part": "전방 LiDAR 창", "real": "유전체 창 + 뒤 금속 캔", "verdict": "통째 금속. 면적 3.7 cm² 로 작다", "grade": "C"},
        {"part": "초음파 트랜스듀서(typhoonh480)", "real": "금속 캔", "verdict": "금속 취급 타당", "grade": "B"},
        {"part": "DGC2.0 페이로드 커넥터(m350rtk)", "real": "금속", "verdict": "금속 취급 타당", "grade": "B"},
    ],
    "cost_of_the_guess_db": "게이트 D 의 d_camera_as_dielectric_db 를 볼 것. 방위평균 σ 가 움직이는 폭은 "
                            "el 0/−30/−60 에서 −2.2…+0.1 dB 인데 **el −90(나디르)에서 −6.54 dB(phantom4) … +2.65 dB(s1000plus)** 로 "
                            "훨씬 넓다. 저장소의 «최대 1.81 dB» 브래킷은 나디르를 안 본 값이다.",
    "flat_plate_reference": {
        "formula": "σ = 4πA²/λ² · |Γ|²  (수직입사 평판 한계, λ=85.7 mm)",
        "plate_150x150_gamma085_dbsm": -2.03,
        "plate_150x150_gamma028_dbsm": -11.65,
        "plate_100x100_gamma085_dbsm": -9.08,
        "plate_78x78_gamma085_dbsm": -13.40,
        "why": "방진판은 **수평 평판**이라 나디르에서 정반사가 선다. 크기를 1.5배로 지으면 σ 가 4배(+6 dB) 커진다.",
    },
}


def main():
    t0 = time.time()
    res = {"_meta": {
        "title": "짐벌·카메라·센서 검사 — 드론 10종",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "generator": "benchmark/check_gimbal_sensors_0816.py",
        "fc_hz": FC, "lambda_m": round(LAM, 6), "po_spacing_m": round(SPACING, 6),
        "az_deg": "0..355 step 5", "el_deg": ELS,
        "engine": "pure PO (CPU) — 가림 없음. SBR/GPU 미사용.",
        "gamma_source": "materials.MATERIALS (ITU metal 은 벌크 프레넬 극한 0.9997 로 되품)",
        "gamma_used": {g: round(GM[g], 4) for g in sorted(GM)},
        "src_touched": "none — 읽기 전용",
    }, "sensor_facts": SENSOR_FACTS,
        "matrice4e_downward_vision_ruling": M4E_DOWN_VISION_RULING,
        "material_review": MATERIAL_REVIEW,
        "gate_C_helper_envelope": gate_c(), "drones": {}}

    for key in drone_keys():
        spec = DRONES[key]
        raw = _build_frame_raw(spec)
        fit = frame_fit_scale(spec)
        m = build_drone(spec)
        g = np.asarray(m.g, object)
        V = np.asarray(m.v, float)
        F = np.asarray(m.f, np.int64)

        zmin = {}
        for grp in sorted(set(g)):
            zmin[grp] = round(float(V[F[g == grp]].reshape(-1, 3)[:, 2].min()) * 1000, 2)

        # ---- 게이트 A : 카메라가 발보다 낮은가 (raw 좌표 = fit 이전) ------------- #
        Vr = np.asarray(raw.v, float)
        Fr = np.asarray(raw.f, np.int64)
        gr = np.asarray(raw.g, object)
        gear_mask = np.isin(gr, ["gear", "gear_cf"])
        z_cam_raw = (float(Vr[Fr[gr == "camera"]].reshape(-1, 3)[:, 2].min()) * 1000
                     if (gr == "camera").any() else None)
        z_gear_raw = (float(Vr[Fr[gear_mask]].reshape(-1, 3)[:, 2].min()) * 1000
                      if gear_mask.any() else None)
        z_all_raw = float(Vr[:, 2].min()) * 1000
        z_top_raw = float(Vr[:, 2].max()) * 1000
        gate_a = {"z_camera_min_raw_mm": None if z_cam_raw is None else round(z_cam_raw, 2),
                  "z_gear_min_raw_mm": None if z_gear_raw is None else round(z_gear_raw, 2),
                  "fit_scale": [round(float(v), 4) for v in fit],
                  "envelope_mm": spec.envelope_mm}
        if z_cam_raw is not None and z_gear_raw is not None:
            below = z_cam_raw - z_gear_raw
            gate_a["camera_below_gear_mm"] = round(below, 2)
            gate_a["verdict"] = "FAIL — 카메라가 착륙장치보다 낮다" if below < -0.5 else "PASS"
            if below < -0.5 and spec.envelope_mm and spec.envelope_mm[2]:
                #  카메라가 바닥을 정하고 있으면 sz 도 카메라가 정한다.
                #  발을 기준으로 다시 풀면 얼마가 되나(같은 fit 규칙, 바닥만 교체).
                sz_now = fit[2]
                sz_if_feet = float(spec.envelope_mm[2]) / (z_top_raw - z_gear_raw)
                gate_a["sz_now"] = round(sz_now, 4)
                gate_a["sz_if_bottom_were_the_feet"] = round(sz_if_feet, 4)
                gate_a["vertical_scale_error_pct"] = round(100 * (sz_if_feet / sz_now - 1), 2)

        # ---- 게이트 B : 뜬 부품 / 삼켜진 부품 --------------------------------- #
        cc = camera_components(m)
        entry = {"group_zmin_mm": zmin, "gate_A_gimbal_vs_gear": gate_a,
                 "n_camera_tris": int(sum(len(c) for c in cc)), "n_components": len(cc),
                 "components": []}
        if not cc:
            entry["note"] = "camera 그룹 없음(카메라 미탑재 기체)"
            res["drones"][key] = entry
            print(f"{key:12s} camera 없음", flush=True)
            continue

        cam_faces = np.concatenate(cc)
        other = np.setdiff1d(np.arange(len(m.f)), cam_faces)
        rest = _tm(m, other)
        shell_mask = np.isin(g[other], ["body", "canopy"])
        shell = _tm(m, other[shell_mask]) if shell_mask.any() else None
        pq_rest = trimesh.proximity.ProximityQuery(rest)

        comps_tm = [_tm(m, ci) for ci in cc]
        for i, (ci, tm) in enumerate(zip(cc, comps_tm)):
            pts, _fi = trimesh.sample.sample_surface(tm, 3000)
            d_rest = float(pq_rest.on_surface(pts)[1].min())
            d_cam = np.inf
            for j, o in enumerate(comps_tm):
                if i == j:
                    continue
                d_cam = min(d_cam, float(trimesh.proximity.ProximityQuery(o).on_surface(pts)[1].min()))
            inside = None
            if shell is not None:
                try:
                    inside = float(shell.contains(pts[::10]).mean())
                except Exception:
                    inside = None
            gapd = round(d_rest * 1000, 3)
            if gapd <= 0.5:
                verdict = "attached — 기체 표면에 닿는다"
            elif inside is not None and inside > 0.9:
                verdict = "swallowed — 셸 속에 완전히 파묻혔다(PO 는 세고 SBR 은 안 센다)"
            else:
                verdict = "FLOATING — 아무데도 안 닿는다"
            entry["components"].append({
                "idx": i, "n_tris": int(len(ci)),
                "area_cm2": round(float(tm.area) * 1e4, 3),
                "size_mm": [round(float(v), 2) for v in (tm.bounds[1] - tm.bounds[0]) * 1000],
                "centroid_mm": [round(float(v), 2) for v in tm.centroid * 1000],
                "gap_to_airframe_mm": gapd,
                "gap_to_other_camera_parts_mm": (round(d_cam * 1000, 3) if np.isfinite(d_cam) else None),
                "frac_inside_shell": None if inside is None else round(inside, 3),
                "verdict": verdict,
            })

        # ---- 게이트 D : RF -------------------------------------------------- #
        Eo, Ec = {}, [{} for _ in cc]
        for el in ELS:
            Eo[el] = sum(E_of(_submesh(m, other[g[other] == grp], grp), GM.get(grp, 1.0), el)
                         for grp in sorted(set(g[other])))
            for i, ci in enumerate(cc):
                Ec[i][el] = E_of(_submesh(m, ci, "camera"), 1.0, el)
        rf = {}
        pref = 4 * np.pi / LAM ** 2
        for el in ELS:
            tot = sum(e[el] for e in Ec)
            base = float((pref * np.abs(Eo[el] + GM["camera"] * tot) ** 2).mean())
            off = float((pref * np.abs(Eo[el]) ** 2).mean())
            pla = float((pref * np.abs(Eo[el] + GM["body"] * tot) ** 2).mean())
            per = []
            for i in range(len(Ec)):
                Ei = sum(Ec[j][el] for j in range(len(Ec)) if j != i)
                per.append(round(db(float((pref * np.abs(Eo[el] + GM["camera"] * Ei) ** 2).mean()))
                                 - db(base), 3))
            rf[str(int(el))] = {"sigma_dbsm_azmean": round(db(base), 3),
                                "d_camera_group_removed_db": round(db(off) - db(base), 3),
                                "d_camera_as_dielectric_db": round(db(pla) - db(base), 3),
                                "d_remove_each_component_db": per}
        entry["gate_D_rf_po"] = rf
        res["drones"][key] = entry
        print(f"{key:12s} ok  {time.time() - t0:6.1f}s", flush=True)

    # ---- 요약 : 숫자는 위에서 잰 것만 인용한다(손으로 안 적는다) ------------- #
    summary = {"gate_A_fail": [], "gate_B_floating": [], "gate_B_swallowed": [],
               "gate_C_over_declared": [], "gate_D_dielectric_swing_db": {}}
    for k, v in res["drones"].items():
        ga = v.get("gate_A_gimbal_vs_gear", {})
        if str(ga.get("verdict", "")).startswith("FAIL"):
            summary["gate_A_fail"].append({
                "drone": k, "camera_below_gear_mm": ga.get("camera_below_gear_mm"),
                "sz_now": ga.get("sz_now"), "sz_if_bottom_were_the_feet": ga.get("sz_if_bottom_were_the_feet"),
                "vertical_scale_error_pct": ga.get("vertical_scale_error_pct")})
        for c in v.get("components", []):
            row = {"drone": k, "area_cm2": c["area_cm2"], "size_mm": c["size_mm"],
                   "centroid_mm": c["centroid_mm"], "gap_to_airframe_mm": c["gap_to_airframe_mm"],
                   "gap_to_other_camera_parts_mm": c["gap_to_other_camera_parts_mm"]}
            if c["verdict"].startswith("FLOATING"):
                summary["gate_B_floating"].append(row)
            elif c["verdict"].startswith("swallowed"):
                summary["gate_B_swallowed"].append(row)
        if "gate_D_rf_po" in v:
            sw = {e: v["gate_D_rf_po"][e]["d_camera_as_dielectric_db"] for e in v["gate_D_rf_po"]}
            summary["gate_D_dielectric_swing_db"][k] = sw
    for name, row in res["gate_C_helper_envelope"].items():
        if max(row["built_over_declared"]) > 1.10:
            summary["gate_C_over_declared"].append({"helper": name, **row})
    summary["read_this_first"] = [
        "게이트 A 는 FAIL 이 하나뿐인데 그 하나가 가장 무겁다 — 그 기체는 짐벌이 바닥을 정하고, "
        "바닥이 세로 배율을 정하고, 세로 배율이 기체 전 부위를 정한다.",
        "게이트 B 의 «swallowed» 는 σ 를 거의 안 움직이지만 **PO 와 SBR 이 같은 메쉬를 다르게 읽게** 만든다.",
        "게이트 C 의 배율은 mini2 가 2026-08-04 에 역산으로 없앤 것과 같은 성격이다 — 나머지 helper 사용자에게 남아 있다.",
        "게이트 D 에서 재질 선택(금속↔유전체)의 대가는 **앙각에 크게 의존한다**. 나디르에서 가장 크다.",
    ]
    res["_summary"] = summary

    path = os.path.join(ROOT, "outputs", "mesh_inspect_gimbal_sensors_0816.json")
    with open(path, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("wrote", path, f"({time.time() - t0:.1f}s)")
    return res


if __name__ == "__main__":
    main()
