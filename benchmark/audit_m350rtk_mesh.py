# -*- coding: utf-8 -*-
"""
audit_m350rtk_mesh.py — m350rtk 메쉬의 **자유도 감사 + 온전성 + 실루엣 IoU** 원장
=================================================================================

무엇을 하나
  새로 등록한 `m350rtk` 메쉬에 대해 세 가지를 한 파일에 적는다.
    1) 온전성 — 삼각형 수 · bbox 대 공표치수 · 부품별 워터타이트/법선/퇴화면
    2) 자유도 — `outputs/p3_attack.json` 의 Q3 와 **같은 분류**로 센다:
         관측으로 고정된 것 / 이 기체 전용 판단(tier A) / 빌려온 상수(tier B) / 엔진 손잡이(tier C)
       그래야 phantom3 의 자유/고정 = 15.8 과 사과 대 사과로 비교된다.
    3) 실루엣 IoU — `src/viz_mesh_photo.py` 를 이 기체만 돌려 자기복제 상한 대비 %로 적는다.
       (부분 실행이라 공용 원장 `outputs/mesh_compare_photo.json` 은 **덮어쓰지 않는다**.)

왜 손으로 센 목록인가
  자유도는 코드에서 자동으로 셀 수 없다 — "이 숫자가 이 기체 관측으로 고정됐나" 는 출처 판정이지
  구문 판정이 아니다. 그래서 항목을 **전부 나열**한다. 세는 방식에 이의가 있으면 목록을 고치면 된다.
  ⚠ 목록이 곧 주장이다. 항목 하나라도 근거가 없으면 그건 여기 constrained 에 있으면 안 된다.

실행
  cd /workspace/sionna
  SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/audit_m350rtk_mesh.py
  ... --no-iou      # IoU 정합(약 2.5 분)을 건너뛴다
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

KEY = "m350rtk"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "outputs", f"{KEY}_mesh_audit.json")


# --------------------------------------------------------------------------- #
#  1.  자유도 목록 — p3_attack.json Q3 와 같은 분류
# --------------------------------------------------------------------------- #
CONSTRAINED = [
    # --- DJI 공표 (VERIFIED) ---
    "대각 휠베이스 895 mm (DJI 제원 페이지)",
    "펼침·프롭제외 길이 810 mm (DJI)",
    "펼침·프롭제외 폭 670 mm (DJI)",
    "펼침·프롭제외 높이 430 mm (DJI)",
    "접힘·프롭포함 길이 430 mm (DJI) — p06 축척의 독립 검사에 쓰였다",
    "접힘·프롭포함 폭 420 mm (DJI) — p06 축척의 앵커",
    "로터 4 · 암 4 (QSG 콜아웃 5·6·7 + 사진 전수)",
    "블레이드 2 매/로터 (c01 2110s 1쌍 사진)",
    "질량 6.47 kg = 기체 + TB65 2개, 페이로드 없음 (사용자 매뉴얼) — 메쉬가 짓는 바로 그 구성",
    # --- 기체 고유이지만 2차출처 (등급 낮음, 그래도 이 기체의 수치다) ---
    "프로펠러 지름 533.4 mm (2110s, 소매점 표기 = SECONDARY)",
    "프로펠러 피치 10.0 in (같은 출처, SECONDARY)",
    # --- 공표값에서 **정확히 결정**되는 것 (검사가 아니다 — 아래 retraction 참조) ---
    "로터 각 38.65° — 공표 박스 810×670 과 휠베이스 895 가 (각 a, 오버행 p) 두 미지수를 "
    "**정확히** 결정한다: 895cos a + p = 810 · 895sin a + p = 670 → a = 38.65°, p = 111.0 mm. "
    "⛔ RETRACTED 2026-08-03 — 옛 판은 '두 식이 같은 p 를 돌려주는 일치가 검사다' 라고 적었으나 "
    "**거짓이다**. 두 식·두 미지수는 어떤 박스에서도 같은 p 를 항등적으로 준다(엉터리 박스 "
    "1000×500 을 넣으면 a=21.73°, 두 p 가 1e-13 mm 안에서 일치한다). 남는 검사는 (i) p=111 mm "
    "의 물리적 타당성과 (ii) 반경방향 오버행 모델이 같은 두 식을 a=39.60°, q=78 mm 로 닫는다는 "
    "사실뿐 — 즉 각도의 정직한 대역은 ±1° 다. t02 상면 스팬비도 카메라 기울기 코사인을 "
    "**적합**해서 맞춘 것이라(자유도 1 : 측정 1) 검사가 아니라 정황이다",
    # --- 이 기체 사진에서 잰 것 ---
    "동체 길이 285 mm (p06, 0.706 mm/px)",
    "동체 최대폭 175 mm (p06 184 · t05 자 실측 165 의 중앙)",
    "동체 높이 ≈198 mm — d01 의 세로 비율(동체 130 px : 다리 152 px)로 공표 총높이 430 을 "
    "나눈 값이다. 사진이 비율을, DJI 가 절대값을 준다. 코드는 200 을 쓴다(+0.9 % 반올림)",
    "상판 폭 / 최대폭 = 0.794 (p06, 축척이 약분되는 비)",
    "벨리 판 폭 / 최대폭 = 0.80 (m01 Bottom view)",
    "기수 폭 130 mm (d01 정면 실루엣)",
    "동체 중심이 암 축보다 +46 mm 위 (d01 앞/뒤 암 화면높이차 65 px 의 절반을 원근으로 환원)",
    "암 튜브 외경 22.0 mm (p06 19.1 · p07 22.5 — 축척을 공유하지 않는 두 사진)",
    "암 = 직선 카본 튜브, 상반각 0° (p07 측면, ±2°)",
    "암 재질 = 카본(직조가 p06·p07 에 보인다), 뿌리 칼라 = 플라스틱 (같은 사진)",
    "모터 포드 58 × 80 × 52 mm (p06 암끝 근접)",
    "모터 벨 지름 56 mm (p06 프롭 허브 캡 지름)",
    "착륙장치 발 트랙 366 mm (d01, 1.483 mm/px)",
    "착륙장치 벨리→발 230 mm (d01 세로비 + 공표 430)",
    "DGC2.0 마운트가 벨리 아래 82 mm 까지 내려온다 (d01)",
    "TB65 배터리 2개가 **외부 노출**로 후면 베이에 있다 (p11 후면 · d06 · m01 Rear view)",
    "배터리 블록 150 × 78 × 100 mm (m01 Rear view 의 면적비 × 위 실측 동체)",
    "메인보드 240 × 124 mm (t05, 강철 자와 같은 평면)",
    "기본 구성에 카메라가 없다 — DGC2.0 포트가 비어 있다 (외부 사진 전수)",
    "6방향 비전 + FPV 카메라의 존재와 배치면 (m01 3면도 콜아웃 1·2·3 · d01 · p08)",
]

TIER_A = {
    "등가 오버행 해(38.65°)를 반경방향 해(39.60°) 대신 채택 — 1° 폭이 그대로 불확도다": 1,
    "질량을 MTOW 9.2 kg 이 아니라 6.47 kg(무페이로드)로 잡은 선택": 1,
    "envelope 강제축을 '높이만' 으로 하는 정책": 1,
    "프롭 지름을 SECONDARY 인 채로 쓰고 p05/p06 자로 교차검증하지 않은 선택": 1,
    "평면형 보간점 8쌍(실측이 강제하는 양 끝·최대폭을 제외한 나머지)": 16,
    "_body_profiled 지수 p_up / p_dn = 5.0": 2,
    "평면형 100 % 높이 z_full = BZC − 10 mm": 1,
    "암 뿌리 칼라 구간 82→200 mm 와 폭 70→36 mm": 4,
    "암 노출 튜브 구간 190→408 mm": 2,
    "모터 상부 커버 원통(r 18 · h 22 · z 58)": 3,
    "착륙장치 A프레임 기하 — 상단 |y| 55 · 상단 x ±20 · 발 x ±105 · 스키드 길이 360 · "
    "스키드 OD 24 · 다리 단면 24×24 r11 · 고무 슬리브 OD 32 · 길이 55 · |x| 152": 9,
    "배터리 2상자의 x·z 위치": 2,
    "메인보드 두께·z, 두 번째 전원보드의 크기 3 + 위치 3": 7,
    "비전 렌즈 8개의 반경·깊이·좌표(대표 4종 × 4수)": 16,
    "DGC2.0 마운트 상자 100×92×30 과 커넥터 원통 r19 h24": 5,
    "CSM Radar · 흰 보호캡 · GNSS 안테나를 **안 짓기로** 한 결정": 3,
    "hover_rpm 2400 (C_T 사다리 전이)": 1,
    "body_frac · body_lw 를 메쉬와 같게 맞춘 것(그림 전용)": 2,
}

TIER_B = {
    "_body_profiled 법칙 자체 (n_sec 23 · loft n_pts 96 · smooth iters 2)": 3,
    "_arm_dihedral 내부 비율 (칼라 단면 0.82 · 모서리 0.30 · sweep 표본수 · quad_segs)": 5,
    "_motor_pod 회전체 프로파일 8점 = 16 + seg": 17,
    "_motor_bell 프로파일 9점 = 18 + seg": 19,
    "프로펠러 H등급 상수 (sweep_frac · root_frac · 허브 r/h · 허브 프로파일 3점 · airfoil pts · "
    "n_sec · n_pts · base_ang 12° · 회전방향 관례)": 15,
    "프로펠러 D등급 상수 (시위표를 법칙으로 씀 · TC_ROOT/TIP · CAMBER_M/P)": 5,
    "그룹→재질 배정 (존재하는 9그룹)": 9,
    "쓰인 |Γ| 실효값 6종 (plastic·carbon·metal·camera_assembly·pcb·prop_plastic)": 6,
    "셸 투과 규약 (어느 그룹이 셸인가 + τ = 1 − |Γ|²)": 2,
    "내가 고른 분해능 리터럴 (cyl seg · sweep n_pts · rounded_rect pts …)": 6,
}

#  p3_attack.json Q3 의 tier_C 와 **같은 항목**이다. 이 기체로 σ 대조를 아직 돌리지 않았지만,
#  돌리는 순간 똑같이 붙으므로 사과 대 사과를 위해 같은 개수로 센다.
TIER_C = {
    "PO/SBR 샘플링 div (커널 기본 12 ↔ 리포트 16)": 1,
    "대조 자세(고도각)의 선택": 1,
    "통계 규약(선형평균 vs dB영역평균)": 1,
    "적합 대역 구간": 1,
    "끝점 포함 여부": 1,
    "대조 상대의 선택": 1,
    "방위창 360° vs 문헌 호": 1,
    "jitter · penetrate · max_bounce · ptd · n_az · 주파수 격자": 6,
}

DECLARED_BIASES = [
    "TB65 두 팩은 실물에서 **셸 밖**인데, rcs_sbr 은 여전히 주변 'body' 그룹을 유전체 셸로 본다 "
    "→ 이 기체의 지배 금속체 앞에 없는 셸이 한 겹 생긴다. 선언만 하고 고치지 않았다.",
    "battery·pcb 그룹은 저장소의 불리언 합집합 목록에 없다(MESH_METHOD §5). 여기서는 두 배터리 "
    "상자를 8 mm 떼어 놓아 겹치지 않게 했으므로 파묻힌 면은 생기지 않는다 — 검사로 확인한다.",
    "프레임 bbox 는 771 × 626 mm 로 공표 810 × 670 보다 −4.8 % / −6.5 % 작다. 원인은 로터 스테이션 "
    "오버행을 공표값이 함의하는 111 mm 가 아니라 **사진에서 잰 포드 크기**로 지었기 때문이다. "
    "envelope 로 L/W 를 강제하면 이 차이가 사라지지만, 그건 증거가 아니라 제약이다.",
    "GNSS 안테나 2개는 별도 파트가 아니라 모터 상부 커버가 대신한다.",
    "등록된 사진이 **한 장뿐**이다(d01). IoU 한 점은 자세 한 방향의 정보이고, 다른 기체들의 "
    "2~4장짜리 값과 같은 무게로 읽으면 안 된다.",
]


def dof_block():
    a = sum(TIER_A.values())
    b = sum(TIER_B.values())
    c = sum(TIER_C.values())
    free = a + b + c
    con = len(CONSTRAINED)
    return dict(
        _rule="'자유로운 선택' = 이 메쉬의 σ 를 바꾸는데 **M350 RTK 자체의 관측으로 고정되지 "
              "않은** 수. 분류는 outputs/p3_attack.json 의 Q3 와 같다.",
        constrained_by_an_m350rtk_observation=dict(count=con, items=CONSTRAINED),
        tier_A_m350rtk_specific_decisions=dict(count=a, items=TIER_A),
        tier_B_inherited_constants_no_m350rtk_evidence=dict(count=b, items=TIER_B),
        tier_C_engine_and_comparison_knobs=dict(count=c, items=TIER_C),
        total_free=free,
        ratio_free_to_constrained=round(free / con, 2),
        comparison_phantom3=dict(
            free=205, constrained=13, ratio=15.8, source="outputs/p3_attack.json :: Q3",
            what_moved=[
                f"고정된 수 13 → {con}: P3 는 저장소에 사진이 **한 장도 없었고**, M350 은 65장 "
                "(공식 렌더 8 · 실사 21 · 분해 26 · 도해 7 · 부품 3, 그중 자가 함께 찍힌 FCC "
                "컷이 37장)이 있다. ⚠ 다만 자유도를 실제로 줄인 것은 그중 소수다 — 동체·암·"
                "포드 치수는 p06·p07·t05·d01 네 장이 거의 다 정했다.",
                "빌려온 상수 160 → %d: 전용 분기를 써서 _SHELL_SHAPE(20) · _canopy(14) · "
                "_body_folding 법칙(10) · _gimbal_hanging(21) · _gear_arch(13) · "
                "_ARM_WIDTH/_ARM_SECTION(4) · 내부 3상자 공용비율(18) 을 **하나도 타지 않는다** "
                "— 그 100개가 여기서 사라진 것이 차이의 대부분이다." % b,
                "이 기체 전용 판단은 32 → %d 로 늘었다. 전용 분기를 쓰면 상속이 줄어드는 대신 "
                "직접 정하는 수가 늘어난다 — 공짜가 아니다." % a,
            ]),
        honesty_note="constrained 목록의 항목 중 프로펠러 지름·피치는 SECONDARY(소매점) 등급이고, "
                     "배터리 블록·기수 폭·동체 중심 높이는 사진 비율에서 유도한 것이라 "
                     "±10 % 대역이 붙는다. 등급을 올려 적지 않았다.",
        declared_biases=DECLARED_BIASES,
    )


# --------------------------------------------------------------------------- #
#  2.  온전성
# --------------------------------------------------------------------------- #
def sanity_block():
    from drones import DRONES, build_frame, build_drone, build_propeller, frame_envelope_mm
    from mesh_check import check_mesh
    spec = DRONES[KEY]
    fr, dr = build_frame(spec), build_drone(spec)
    V = np.asarray(fr.v, float)
    W = np.asarray(dr.v, float)
    env = frame_envelope_mm(spec)
    ext = np.asarray(env["lwh_mm"], float)
    pub = np.array([810.0, 670.0, 430.0])
    chk = check_mesh(dr, "drone")
    from collections import Counter
    return dict(
        n_tri_frame=len(fr.f), n_tri_prop=len(build_propeller(spec).f), n_tri_drone=len(dr.f),
        n_vertices=len(dr.v),
        bbox_frame_mm=[round(float(v), 2) for v in ext],
        bbox_with_props_mm=[round(float(v), 2) for v in (W.max(0) - W.min(0)) * 1000.0],
        published_unfolded_props_excluded_mm=list(pub),
        bbox_vs_published_pct=[round(float(100.0 * (ext[i] / pub[i] - 1.0)), 2) for i in range(3)],
        wheelbase_mm=round(float(env["wheelbase_opposite_mm"]), 2),
        wheelbase_published_mm=895.0,
        envelope_fit_scale=[round(float(s), 5) for s in env["fit_scale"]],
        frame_z_range_mm=[round(float(V[:, 2].min() * 1000), 1), round(float(V[:, 2].max() * 1000), 1)],
        z_origin="모터 스테이션의 암 축",
        watertight_all_parts=bool(chk["ok"]),
        per_group={g: dict(n_faces=v["n_faces"], n_parts=v["n_parts"], watertight=v["watertight"],
                           inward_normals=v["inward_normals"], bad_winding=v["bad_winding"],
                           degenerate=v["degenerate"])
                   for g, v in chk["groups"].items()},
        group_face_counts=dict(Counter(dr.g).most_common()),
        groups_absent_on_purpose=["canopy (M350 은 등판 캐노피가 없다 — 상판이 곧 셸이다)",
                                  "accent (전방 식별색 없음)",
                                  "deck · fc (열린 프레임 전용)"],
        figure="outputs/figs/m350rtk_mesh.png",
    )


# --------------------------------------------------------------------------- #
#  3.  실루엣 IoU
# --------------------------------------------------------------------------- #
#: MESH_METHOD.md §0 이 적어 둔 다른 기체의 상한 대비 % (outputs/mesh_compare_photo.json).
PEERS = {"x500v2": (0.875, 0.957), "s1000plus": (0.754, 0.864), "matrice4e": (0.559, 0.883),
         "phantom4": (0.546, 0.920), "typhoonh480": (0.547, 0.933), "mavic4pro": (0.525, 0.917),
         "mini5pro": (0.478, 0.956)}


def iou_block():
    import viz_mesh_photo as P
    J = P.build_all(keys=[KEY], figures=True, calib=True)
    rec = J["airframes"][KEY]
    ceil = float(J["_meta"]["metric_calibration"][KEY]["recovered_iou"])
    best = float(rec["best_iou"])
    ph = rec["photos"][rec["best_index"]]
    table = {k: dict(best_iou=v[0], ceiling=v[1], pct_of_ceiling=round(100.0 * v[0] / v[1], 1))
             for k, v in PEERS.items()}
    table[KEY] = dict(best_iou=round(best, 3), ceiling=round(ceil, 3),
                      pct_of_ceiling=round(100.0 * best / ceil, 1))
    return dict(
        best_iou=round(best, 4), self_replication_ceiling=round(ceil, 4),
        pct_of_ceiling=round(100.0 * best / ceil, 1),
        photo=ph["file"], declared_aspect=ph.get("expect"), fitted=ph.get("fit"),
        metrics=ph["metrics"],
        n_photos_registered=len(rec["photos"]),
        peer_table_pct_of_ceiling=dict(sorted(table.items(),
                                              key=lambda kv: -kv[1]["pct_of_ceiling"])),
        note="상한은 그 기체 메쉬로 만든 가짜 사진을 같은 파이프라인에 넣어 잰 값이다. "
             "다른 기체 수치는 MESH_METHOD.md §0 표(= outputs/mesh_compare_photo.json)에서 옮겼다. "
             "⚠ 이 기체는 등록 사진이 한 장뿐이라 표의 다른 행들과 표본수가 다르다.",
        figure="outputs/figures/mesh_photo_m350rtk.png",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-iou", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    J = dict(_meta=dict(
        drone=KEY, name="DJI Matrice 350 RTK",
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        generator="benchmark/audit_m350rtk_mesh.py",
        purpose="새 기체 m350rtk 의 메쉬 온전성 · 자유도 · 사진 실루엣 IoU 를 한 원장에 남긴다.",
        spec_source="outputs/m350rtk_specs.json", photo_source="assets/photos/m350rtk/SOURCES.md",
        mesh_source=["src/drones.py :: DRONES['m350rtk']",
                     "src/drone_cad.py :: build_frame_cad 의 m350rtk 전용 분기"],
        cross_check=("outputs/m350rtk_layout_check.json — 독립 재검증 라운드(2026-08-03). "
                     "IoU·워터타이트·d01 세로분해는 재현됐고, 로터각의 '오버행 일치가 검사다' "
                     "주장은 항등식임이 드러나 **철회**했다(반례 포함). 이 파일의 로터각 항목 "
                     "문구는 그 결과다.")))
    J["sanity"] = sanity_block()
    J["degrees_of_freedom"] = dof_block()
    if not args.no_iou:
        J["silhouette_iou"] = iou_block()
    elif os.path.exists(OUT):
        #  --no-iou 로 다시 돌릴 때 **이미 잰 IoU 를 버리지 않는다** — 정합은 2.5분이 걸리고
        #  자유도 목록만 고치는 일이 훨씬 잦다. 잰 시각은 그대로 남으므로 낡으면 보인다.
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f)
            if "silhouette_iou" in old:
                J["silhouette_iou"] = old["silhouette_iou"]
                J["silhouette_iou"]["carried_over_from"] = old["_meta"]["generated"]
        except (OSError, ValueError):
            pass
    J["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    d = J["degrees_of_freedom"]
    print(f"[m350rtk] 원장: {OUT}")
    print(f"          삼각형 {J['sanity']['n_tri_drone']} · bbox {J['sanity']['bbox_frame_mm']} mm")
    print(f"          자유 {d['total_free']} / 고정 {d['constrained_by_an_m350rtk_observation']['count']}"
          f" = {d['ratio_free_to_constrained']}  (phantom3 는 15.8)")
    if "silhouette_iou" in J:
        s = J["silhouette_iou"]
        print(f"          IoU {s['best_iou']} / 상한 {s['self_replication_ceiling']}"
              f" = {s['pct_of_ceiling']} %")


if __name__ == "__main__":
    main()
