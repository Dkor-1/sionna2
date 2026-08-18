# -*- coding: utf-8 -*-
"""치수 앵커 감사 — 결과 취합 → outputs/mesh_audit_0816_scale_anchor.json"""
import json, datetime, math
import numpy as np

S = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad"
dims = json.load(open(f"{S}/dims.json"))
vis = json.load(open(f"{S}/visible_all.json"))
front = json.load(open(f"{S}/frontal.json"))
inte = json.load(open(f"{S}/internals.json"))
prop = json.load(open(f"{S}/prop_area.json"))
envf = json.load(open(f"{S}/env_forcing.json"))
dprop = json.load(open(f"{S}/dji_prop.json"))
oprop = json.load(open(f"{S}/ours_prop.json"))

LAM = 2.998e8 / 3.5e9

#  공식 제원 — 이 라운드에서 **직접 확인한 출처**만 적는다.
OFFICIAL = {
    "matrice4e": dict(unfolded_no_props_mm=(307.0, 387.5, 149.5), diagonal_mm=438.8,
                      src="enterprise.dji.com/matrice-4-series/specs + Clifton Cameras 제원 PDF (2026-08-16 재확인)"),
    "mavic4pro": dict(unfolded_no_props_mm=(328.7, 390.5, 135.2), diagonal_mm=None,
                      src="DJI Mavic 4 Pro 제원(Clifton Cameras PDF·dronexl) (2026-08-16 재확인). DJI 는 대각을 공표하지 않는다"),
    "mini5pro": dict(unfolded_no_props_mm=(181.0, 255.0, None), unfolded_with_props_mm=(304.0, 380.0, 91.0),
                     folded_no_props_mm=(157.0, 95.0, 68.0), diagonal_mm=None,
                     src="DJI Mini 5 Pro Specification PDF (fitz 원문추출, 2026-08-16): "
                         "'Folded (without propellers): 157x95x68 mm' · 'Unfolded (with propellers): 255x181x91 mm'. "
                         "304x380x91 은 리뷰 매체 다수가 쓰는 프롭포함값"),
    "phantom4": dict(unfolded_no_props_mm=(289.5, 289.5, 196.0), diagonal_mm=350.0,
                     src="레지스트리 인용(DJI Quick Start Guide v1.2) — 이번 라운드에서 원문 재확인 못함"),
    "s1000plus": dict(unfolded_no_props_mm=(1016.0, 1016.0, 380.0), diagonal_mm=1045.0,
                      src="DJI Spreading Wings S1000+ User Manual v1.4 (대각 1045·암 386 재확인, 2026-08-16)"),
    "phantom3": dict(unfolded_no_props_mm=(289.5, 289.0, 185.0), diagonal_mm=350.0, src="레지스트리 인용"),
    "typhoonh480": dict(unfolded_no_props_mm=(457.0, 520.0, 310.0), diagonal_mm=480.0, src="레지스트리 인용(Yuneec 매뉴얼 V1.2)"),
    "x500v2": dict(unfolded_no_props_mm=(None, None, None), diagonal_mm=500.0, src="docs.holybro.com (L/W/H 미공표)"),
    "m350rtk": dict(unfolded_no_props_mm=(810.0, 670.0, 430.0), diagonal_mm=895.0, src="레지스트리 인용(enterprise.dji.com)"),
    "mini2": dict(unfolded_no_props_mm=(159.0, 203.0, 56.0), diagonal_mm=213.0, src="레지스트리 인용(User Manual v1.0)"),
}

#  DJI 인텔리전트 배터리 공표 에너지 [Wh] — 부피 앵커용
BATT_WH = {
    "mini5pro": (19.52, "DJI Mini 5 Pro Intelligent Flight Battery 2788 mAh / 19.52 Wh (판매처 제원, 2026-08-16)"),
    "mavic4pro": (95.0, "DJI Mavic 4 Pro Intelligent Flight Battery 6654 mAh / 95 Wh"),
    "matrice4e": (99.5, "BPX345-6741-14.76 → 6.741 Ah x 14.76 V"),
    "phantom4": (81.32, "PH4-5350mAh-15.2V → 5.35 Ah x 15.2 V"),
    "phantom3": (68.10, "PH3 4480 mAh 15.2 V (레지스트리 앵커)"),
    "mini2": (17.32, "DJI Mini 2 Intelligent Flight Battery 2250 mAh 7.7 V"),
    "m350rtk": (263.2, "TB65 5880 mAh 44.76 V = 263.2 Wh (1개)"),
    "typhoonh480": (79.92, "Yuneec 5400 mAh 4S 14.8 V (2차 출처)"),
    "x500v2": (74.0, "4S 5000 mAh 14.8 V (킷 구성 추정)"),
}
WH_PER_L_ANCHOR = 246.0   # phantom3 실측 249.4 · matrice4e 공표 243.8 의 평균

out = {"_meta": dict(
    title="메쉬 치수 앵커 감사 (담당 렌즈: 치수·투영면적·금속부품)",
    date_kst=datetime.datetime.now().strftime("%Y-%m-%d"),
    scope_ko="10기종 전체. 전개크기·휠베이스·동체·프롭지름 대조 + 정면투영면적/금속거울면적 + "
             "프롭 형상(시위·두께·트위스트)을 DJI 자기 CAD 와 대조.",
    gpu_used=False,
    method_ko="src 를 한 줄도 고치지 않고 drones.build_frame/build_drone/build_propeller 출력만 잰다. "
              "실루엣은 0.5 mm 픽셀 래스터, 가림은 0.25 mm z-buffer. 프롭 단면은 원통단면법(저장소 규약과 동일).",
    sources_checked_2026_08_16=[
        "DJI Matrice 4 Series 제원 (307.0x387.5x149.5 mm, 대각 438.8 mm)",
        "DJI Mavic 4 Pro 제원 (328.7x390.5x135.2 mm)",
        "DJI Mini 5 Pro Specification PDF 원문 (157x95x68 folded / 255x181x91 'unfolded with propellers')",
        "DJI S1000+ User Manual v1.4 (대각 1045 mm, 암 386 mm)",
        "DJI TB65 263.2 Wh · Mavic4Pro 95 Wh · Mini5Pro 19.52 Wh",
    ])}

# ── ① 치수 대조표 ──────────────────────────────────────────────────────────
tab = {}
for k, v in dims.items():
    off = OFFICIAL[k]
    o = off["unfolded_no_props_mm"]
    built = v["frame_lwh_mm"]
    err = [None if o[i] is None else round(100 * (built[i] / o[i] - 1), 2) for i in range(3)]
    wb, ds = v["wheelbase_opposite_mm"], v["spec"]["diagonal_mm"]
    tab[k] = dict(
        official_unfolded_no_props_mm=list(o), built_frame_lwh_mm=built, frame_err_pct=err,
        official_diagonal_mm=off["diagonal_mm"], registry_diagonal_mm=ds,
        built_wheelbase_mm=wb,
        wheelbase_err_vs_official_pct=(None if off["diagonal_mm"] is None
                                       else round(100 * (wb / off["diagonal_mm"] - 1), 3)),
        prop_dia_spec_mm=v["spec"]["prop_dia_mm"], prop_dia_built_mm=v["prop_dia_built_mm"],
        prop_dia_err_pct=v["prop_dia_err_pct"],
        prop_disc_envelope_lw_mm=v["prop_disc_lw_mm"],
        min_adjacent_rotor_gap_mm=v["min_rotor_clearance_mm"],
        envelope_forced_axes=[a for a, t in zip("LWH", (v["spec"]["envelope_mm"] or (None,) * 3)) if t is not None],
        fit_scale=v["fit_scale"], source=off["src"])
out["dimension_table"] = tab

# ── ② 정면(az0/el0) 정렬면적 — 앞뒤 중복 & 가림 ────────────────────────────
al = {}
for k, v in vis.items():
    a_abs, a_fr, a_vis = v["aligned_abs_cm2"], v["aligned_front_cm2"], v["aligned_front_visible_opaqueonly_cm2"]
    al[k] = dict(
        aligned_abs_cm2=a_abs, aligned_front_only_cm2=a_fr, aligned_front_visible_cm2=a_vis,
        aligned_front_visible_all_occluders_cm2=v["aligned_front_visible_allparts_cm2"],
        double_count_ratio=round(a_abs / a_fr, 3),
        sigma_plate_dbsm=dict(as_published=v["sigma_plate_dbsm__aligned_abs_cm2"],
                              front_only=v["sigma_plate_dbsm__aligned_front_cm2"],
                              front_visible=v["sigma_plate_dbsm__aligned_front_visible_opaqueonly_cm2"]),
        overstatement_db=dict(vs_front_only=round(20 * math.log10(a_abs / a_fr), 2),
                              vs_front_visible=round(20 * math.log10(a_abs / max(a_vis, 1e-9)), 2)),
        by_group=v["by_group"])
out["frontal_aligned_area"] = al
out["frontal_silhouette_matrice4e"] = front["matrice4e"]

# ── ③ 내부 금속(배터리) 부피 앵커 ─────────────────────────────────────────
bt = {}
for k, comps in inte.items():
    if "battery" not in comps or k not in BATT_WH:
        continue
    pack = comps["battery"][0]
    wh, src = BATT_WH[k]
    whl = wh / (pack["vol_cm3"] / 1000.0)
    lin = (whl / WH_PER_L_ANCHOR) ** (1 / 3.0)
    bt[k] = dict(pack_box_mm=pack["ext_mm"], pack_vol_cm3=pack["vol_cm3"],
                 pack_front_face_cm2=pack["face_yz_cm2"],
                 published_Wh=wh, implied_Wh_per_L=round(whl, 1),
                 anchor_Wh_per_L=WH_PER_L_ANCHOR,
                 volume_oversize_factor=round(WH_PER_L_ANCHOR / whl, 3),
                 implied_linear_correction=round(lin, 4),
                 implied_face_area_err_pct=round(100 * (1 / lin ** 2 - 1), 1),
                 implied_sigma_plate_err_db=round(-40 * math.log10(lin), 2),
                 source=src,
                 boxes_all=comps["battery"])
out["battery_volume_anchor"] = dict(
    note_ko="DJI 인텔리전트 팩의 부피 에너지밀도는 phantom3 실측(249.4 Wh/L)과 matrice4e 공표치수(243.8 Wh/L) "
            "두 점이 2% 안에서 일치한다 → 246 Wh/L 를 앵커로 삼는다. x500v2·typhoonh480 은 DJI 팩이 아니라 "
            "이 앵커가 그대로 적용되지 않는다(맨 LiPo 는 더 조밀하다) — 참고로만 싣는다.",
    per_drone=bt)

# ── ④ 프롭 형상 — DJI 자기 CAD 대조 ───────────────────────────────────────
out["propeller_vs_dji_cad"] = dict(
    artifact="assets/meshes/reference/WM161_zhankai_1k.glb (DJI 제품페이지 Mini 2 공식 GLB, 블레이드 8장)",
    stale_comment_ko="src/drone_cad.py 60~70행과 benchmark/measure_reference_props.py 는 «저장소에 DJI "
                     "프로펠러 실물 기하는 하나도 없다» 고 적혀 있다. 2026-08-03 mini2 GLB 가 들어오면서 "
                     "그 문장은 거짓이 됐고, 블레이드 법칙은 그 뒤로 한 번도 DJI 프롭에 대조된 적이 없다.",
    diameter=dict(dji_cad_front_mm=117.92, dji_cad_rear_mm=118.91, dji_cad_mean_mm=118.42,
                  registry_mm=119.1, err_pct=round(100 * (118.42 / 119.1 - 1), 2)),
    blade_area=prop["mini2_blade_area_compare"],
    chord_integral=prop["chord_integral"],
    law_vs_its_own_references=prop["law_vs_reference"],
    reference_prop_peaks=prop["reference_props_peak"],
    thickness=dict(area_weighted_mean_mm=dict(dji=0.876, ours=0.968, err_pct=10.4),
                   inboard_0p175_0p5_mm=dict(dji=1.042, ours=1.240, err_pct=19.0),
                   mid_0p5_0p8_mm=dict(dji=0.847, ours=0.764, err_pct=-9.8),
                   tip_0p8_1p0_mm=dict(dji=0.604, ours=0.443, err_pct=-26.6),
                   material_knob_mm=0.9,
                   note_ko="재질 라운드가 고른 0.9 mm 는 DJI 실물의 **면적가중 평균 0.876 mm** 와 2.7% 안에서 "
                           "일치한다(독립 확증). 다만 팁 구간(r/R 0.8~1.0)은 실물 0.604·우리 메쉬 0.443 mm 라 "
                           "0.9 mm 슬래브가 그 구간을 +3.5 dB(실물 대비) / +6.1 dB(우리 메쉬 대비) 과대반사시킨다."),
    twist_rms_deg=1.86,
    caveat_ko="GLB 는 제품페이지용 시각화 CAD 다(계측 스캔 아님). 다만 레지스트리는 이미 이 GLB 를 "
              "prop_dia·prop_pitch 의 출처로 채택했다 — 같은 파일을 시위·두께에만 안 쓰는 것은 일관성 문제다.")

# ── ⑤ envelope 강제의 대가 ────────────────────────────────────────────────
out["envelope_forcing_cost"] = dict(
    note_ko="집안 규칙은 «높이만 강제»(mini5pro/mavic4pro/matrice4e/typhoonh480/phantom3/m350rtk 가 따른다). "
            "phantom4·s1000plus 두 기종만 L/W 까지 강제하고 있어 로터 원이 함께 늘어난다.",
    cases=envf,
    phantom4=dict(built_wheelbase_mm=356.92, official_mm=350.0, err_pct=1.98,
                  silhouette_front_cm2=dict(as_built=216.73, height_only=212.64, delta_pct=1.92,
                                            sigma_plate_delta_db=round(20 * math.log10(216.73 / 212.64), 2)),
                  contradiction_ko="같은 350 mm 대각·같은 9450 프롭인 phantom3 는 높이만 강제해 휠베이스가 "
                                   "정확히 350.0 mm 다. 두 팬텀이 공표된 같은 앵커에서 2% 어긋난다."),
    s1000plus=dict(built_wheelbase_mm=1043.51, official_mm=1045.0, err_pct=-0.14))

# ── ⑥ 문서-메쉬 어긋남(정본 주석이 낡음) ──────────────────────────────────
out["stale_documentation"] = [
    dict(where="src/drones.py typhoonh480 note",
         claim="«arm/motor PART dimensions are UNKNOWN … 그래서 프레임 bbox 가 465.6 x 529.9 mm, 공식 대비 +1.9%»",
         measured="arm_od_mm=12.0·motor_dia_mm=35.4 가 같은 note 뒤쪽에서 이미 설정돼 있고, 현재 프레임 bbox 는 "
                  "452.17 x 517.00 mm = 공식 457x520 대비 -1.06% / -0.58%",
         impact_ko="주석이 두 라운드 낡았다. 부호까지 반대(+1.9% → -1.1%)라 이 문장을 인용하면 결론이 뒤집힌다."),
    dict(where="src/drones.py matrice4e note (2026-07-31 로터 배치)",
         claim="«길이 2·139.45 + 27 = 305.9 ↔ 공식 307 (-0.36%)» 를 독립 검사로 제시",
         measured="그 검사는 **모터 벨 앞끝**까지만 잰다. 실제로 build_frame 이 내는 프레임 길이는 331.43 mm "
                  "(기수 최전방은 카메라/센서 포드 x=+178.46, 모터 벨 앞끝은 +152.92) = 공식 307 대비 +7.96%",
         impact_ko="공표된 '-0.36%' 는 메쉬가 내는 수치가 아니다. 독립 사진검사(자체 톱뷰 렌더, "
                   "0.63351 mm/px)로는 322.0 mm(+4.9%)라 메쉬는 사진보다도 +2.9% 길다."),
    dict(where="src/drones.py mini5pro note",
         claim="«DJI 는 Mini 5 Pro 의 언폴드(프롭 제외) L×W 를 공개하지 않는다» + «우리가 쓰던 (255,181,91) 은 틀렸다»",
         measured="DJI 공식 제원 PDF 원문에 'Unfolded (with propellers): 255x181x91 mm' 가 있다. 프롭 152.4 mm "
                  "짜리 쿼드가 폭 181 mm 안에 프롭까지 들어갈 수 없으므로 그 라벨('with propellers')이 잘못이고 "
                  "숫자 자체는 **프롭 제외 언폴드**다. 우리 프레임은 180.26 x 256.19 mm 로 그 값을 -0.41% / +0.47% "
                  "로 재현한다.",
         impact_ko="레지스트리가 '틀렸다'며 버린 값이 실은 유일한 **비순환** 외부 검사였고, 메쉬는 그 검사를 "
                   "0.5% 로 통과한다. 반대로 채택된 304x380 은 로터 배치를 유도한 바로 그 수라 순환이다."),
    dict(where="benchmark/az_falsify_ours.py _reading_ko · benchmark/az_falsify_specular.py",
         claim="«az0/el0 에서 시선에 정확히 수직인 삼각형이 106장(139 cm²)»",
         measured="선택 조건이 |n·u| ≥ cos(tol) 라 **뒷면까지 센다**. 앞면만은 69.67 cm²(정확히 1/2), "
                  "가림(금속끼리)까지 반영하면 47.15 cm², 전부 반영하면 35.23 cm².",
         impact_ko="평판상한 σ=4πA²/λ² 에서 -6.02 dB(앞면만) ~ -9.41 dB(가림반영). az45 대비 낙차(-57 dB)는 "
                   "비율이라 살아남지만, 절대치 σ_max=-4.78 dBsm 는 -10.8 ~ -14.2 dBsm 로 내려간다."),
]

json.dump(out, open("/workspace/sionna/outputs/mesh_audit_0816_scale_anchor.json", "w"),
          ensure_ascii=False, indent=1)
print("wrote /workspace/sionna/outputs/mesh_audit_0816_scale_anchor.json")
for k, v in tab.items():
    print(f"{k:12s} frame_err {v['frame_err_pct']}  wb {v['built_wheelbase_mm']:8.2f} "
          f"({v['wheelbase_err_vs_official_pct']}%)  prop {v['prop_dia_err_pct']}%")
print()
for k, v in bt.items():
    print(f"{k:12s} pack {v['pack_box_mm']} V={v['pack_vol_cm3']:7.1f} cm3  {v['implied_Wh_per_L']:6.1f} Wh/L "
          f"oversize x{v['volume_oversize_factor']:.2f}  face err {v['implied_face_area_err_pct']:+6.1f}% "
          f"→ σ {v['implied_sigma_plate_err_db']:+5.2f} dB")
