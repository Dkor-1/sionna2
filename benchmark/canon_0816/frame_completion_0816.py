# -*- coding: utf-8 -*-
"""
frame_completion_0816.py — 표준 프레임 **완성표** (팔 × 핵심축, 리듬 몫·빗살 대비 매트릭스).

큐 소진·병합 직후(2026-08-16) 원장 outputs/elevation_sweep_md.{json,npz} 를 읽어,
STANDARD_FRAME 의 팔들을 핵심축(앙각·기체·방위·거리·격자·재질·부품)에 펼치고
칸마다 리듬 몫[%]·빗살 대비[dB]·요동 절대전력[dB, DC 제거]를 싣는다.
잣대 정의는 benchmark/build_md_atlas.py 의 cell_summary 를 **그대로 임포트**한다
(정의를 새로 쓰면 이미 인용된 수와 갈린다).

네 물음:
 ① PS굴절만 기체축 — 굴절만 생존이 기체 불문인가
 ② PS다끔 480 m 재실행 판정 — 이전 «덜 참» 해소 여부
 ③ ours+PTD 확장 — PTD−순정 차분이 기체·방위·거리·격자에서 0 유지인가(프린지 몫 포함)
 ④ 격자 λ/24 전앙각·λ/48 — 산포 밴드를 좁히나 넓히나

CPU 전용 — sionna.rt·mitsuba 임포트 없음. 저장된 원장만 읽는다.
"""
import json
import math
import os
import sys
import time

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
os.chdir(ROOT)

import build_md_atlas as A          # noqa: E402  — 원장·잣대 함수 재사용
from md_mapstyle import auto_periods  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "frame_completion_0816.json")
INV = json.load(open(os.path.join(ROOT, "outputs", "frame_inventory_0816.json")))

PRF = A.PRF
CELLS_AVAIL = A.discover_cells()     # arm -> [els]


def cs(arm: str, el: float) -> dict:
    """한 칸 요약 — build_md_atlas.cell_summary 그대로."""
    rt = A.arm_rates(arm)
    per = auto_periods(PRF, rt["f_flash_hz"])
    c = A.cell_summary(arm, el, rt, per)
    c["_arm"] = arm
    c["_drone"] = rt["drone"]
    return c


def slim(c: dict) -> dict:
    """매트릭스 칸 표기 — 핵심 잣대 + 읽기 깃발만."""
    flags = [k for k in ("no_return", "incomplete", "no_motion",
                         "tip_ceiling_degenerate", "beat_spiky") if c.get(k)]
    # ⭐수치 바닥 경계 표기 — no_motion 문턱(1e-12)의 100배 안이면 «바닥 부근» 딱지.
    #   정면 원거리 칸(다끔 240 m el0)이 여기 걸린다 — 잣대 수는 내되 물리로 읽지 말라는 뜻.
    acdc = c.get("ac_over_dc")
    if acdc is not None and not c.get("no_motion") and acdc < 1e-10:
        flags.append("near_numeric_floor")
    return dict(
        el=c["el_deg"],
        rhythm_share_pct=c["rhythm_share_pct"],
        rhythm_null_pct=c["rhythm_null_pct"],
        comb_contrast_db=c["comb_contrast_db"],
        moving_power_db=c["moving_power_db"],
        ac_over_dc=acdc,
        beat_hz=c["beat_hz"],
        n_missing=c["n_missing"],
        flags=flags,
    )


def pair_diff(arm_a: str, arm_b: str, el: float) -> dict:
    """b − a 차분 (PTD−순정 · div24−div12 등). 프린지 몫·AC 상관 포함.

    fringe_share_pct = 100·‖Δ_ac‖²/‖E_ac(a)‖², Δ = E_b − E_a
    (outputs/ptd_level_probe.json 과 같은 항등식의 Δ항).
    """
    Ea = A.series(arm_a, el)
    Eb = A.series(arm_b, el)
    ca, cb_ = cs(arm_a, el), cs(arm_b, el)
    Aac = Ea - Ea.mean()
    Bac = Eb - Eb.mean()
    D = Bac - Aac
    pa = float(np.mean(np.abs(Aac) ** 2))
    pd = float(np.mean(np.abs(D) ** 2))
    fringe = 100.0 * pd / pa if pa > 0 else None
    # AC 상관 (DC 제거 복소 상관 크기)
    den = math.sqrt(float(np.mean(np.abs(Aac) ** 2)) *
                    float(np.mean(np.abs(Bac) ** 2)))
    rho = float(abs(np.mean(Aac * np.conj(Bac))) / den) if den > 0 else None
    # 프린지(Δ) 자체의 리듬 몫 — ptd_level_probe 의 delta_rhythm_pct 대응
    rt = A.arm_rates(arm_a)
    ft = A.f_tip_at(rt, el)
    d_share, d_null, _, _ = A.rhythm_share(D, rt["f_flash_hz"], ft)
    out = dict(
        el=el,
        level_db_ac=None, d_rhythm_pp=None, d_comb_db=None,
        fringe_share_pct=None if fringe is None else round(fringe, 3),
        fringe_rhythm_pct=None if d_share is None else round(d_share, 1),
        rhythm_null_pct=d_null if d_null is None else round(d_null, 1),
        abs_rho_ac=None if rho is None else round(rho, 4),
    )
    if ca["moving_power_db"] is not None and cb_["moving_power_db"] is not None:
        out["level_db_ac"] = round(cb_["moving_power_db"] - ca["moving_power_db"], 3)
    if ca["rhythm_share_pct"] is not None and cb_["rhythm_share_pct"] is not None:
        out["d_rhythm_pp"] = round(cb_["rhythm_share_pct"] - ca["rhythm_share_pct"], 2)
    if ca["comb_contrast_db"] is not None and cb_["comb_contrast_db"] is not None:
        out["d_comb_db"] = round(cb_["comb_contrast_db"] - ca["comb_contrast_db"], 2)
    out["a"] = slim(ca)
    out["b"] = slim(cb_)
    return out


t0 = time.time()

# ═══════════════════════════════════════════════════════════════════════════ #
# 0. 별칭·동일데이터 검증 — onlyrefr_{기체} ≟ swR1D0E0F1_{기체}_d1 (레벨이 같았다)
# ═══════════════════════════════════════════════════════════════════════════ #
alias_checks = []
for d in ("mini5pro", "s1000plus"):
    a1 = f"sionna_p4000000000_onlyrefr_{d}_r15_n8192"
    a2 = f"sionna_p4000000000_swR1D0E0F1_{d}_r15_n8192_d1"
    for el in CELLS_AVAIL.get(a1, []):
        if el in CELLS_AVAIL.get(a2, []):
            E1, E2 = A.series(a1, el), A.series(a2, el)
            same = bool(np.array_equal(E1, E2))
            c1, c2 = cs(a1, el), cs(a2, el)
            dmp = (None if c1["moving_power_db"] is None or c2["moving_power_db"] is None
                   else round(c2["moving_power_db"] - c1["moving_power_db"], 4))
            drh = (None if c1["rhythm_share_pct"] is None or c2["rhythm_share_pct"] is None
                   else round(c2["rhythm_share_pct"] - c1["rhythm_share_pct"], 2))
            A1, A2 = E1 - E1.mean(), E2 - E2.mean()
            den = math.sqrt(float(np.mean(np.abs(A1) ** 2)) *
                            float(np.mean(np.abs(A2) ** 2)))
            rho = float(abs(np.mean(A1 * np.conj(A2))) / den) if den > 0 else None
            alias_checks.append(dict(a=a1, b=a2, el=el, bit_identical=same,
                                     d_moving_power_db=dmp, d_rhythm_pp=drh,
                                     abs_rho_ac=None if rho is None else round(rho, 6)))
alias_note_ko = ("onlyrefr_{기체} 신규 3앙각 칸과 옛 swR1D0E0F1_{기체}_d1 7앙각 칸은 "
                 "**같은 물리(R1D0E0F1·d1·spp 4e9)의 독립 재실행**이다 — 비트동일은 "
                 "아니지만(레이 표집 비결정성) 잣대는 표시 자리까지 일치한다. 아래 "
                 "d_moving_power_db·d_rhythm_pp 가 그 재실행 산포이고, 격자 산포 밴드보다 "
                 "자릿수로 작다 — 팔 사이 차이를 읽을 때의 공짜 재현성 앵커.")

# ═══════════════════════════════════════════════════════════════════════════ #
# 1. 매트릭스 — 팔 × 핵심축
# ═══════════════════════════════════════════════════════════════════════════ #
ARM_LABEL = {
    "ours": "내 커널 (SBR+PO)",
    "ours_ptd": "내 커널 + PTD (모서리 회절)",
    "ps_alloff": "PathSolver 다 끔 (R0D0E0·확산켬·d1)",
    "ps_onlyrefr": "PathSolver 굴절만 (R1D0E0·확산켬·d1)",
}

# (팔, 축) → [(engine, [els] | None=전부, extra)]
MATRIX_SPEC = {
    "ours": {
        "elevation": [("ours_r15_n8192", None, {})],
        "airframe": [("ours_mini5pro_r15_n8192", None, {"drone": "mini5pro"}),
                      ("ours_s1000plus_r15_n8192", None, {"drone": "s1000plus"})],
        "azimuth": [(f"ours_r15_n8192_az{a:g}", None, {"az": a})
                     for a in (15, 22.5, 30, 45, 60, 67.5, 75, 90)],
        "range": [(f"ours_r{r}_n8192", None, {"range_m": r})
                   for r in (30, 60, 120, 240, 480)],
        "airframe_x_range": [(f"ours_{d}_r{r}_n8192", None,
                              {"drone": d, "range_m": r})
                             for d in ("mini5pro", "s1000plus")
                             for r in (30, 60, 120)],
        "airframe_x_azimuth": [(f"ours_{d}_r15_n8192_az22.5", None,
                                {"drone": d, "az": 22.5})
                               for d in ("mini5pro", "s1000plus")],
        "grid": [("ours_r15_n8192_div24", None, {"grid_div": 24}),
                  ("ours_r15_n8192_div48", None, {"grid_div": 48})],
        "material": "N/A — 우리 커널에 두께 개념 없음(|Γ|·τ 뿐)",
    },
    "ours_ptd": {
        "elevation": [("ours_ptd_r15_n8192", None, {})],
        "airframe": [("ours_ptd_mini5pro_r15_n8192", None, {"drone": "mini5pro"}),
                      ("ours_ptd_s1000plus_r15_n8192", None, {"drone": "s1000plus"})],
        "azimuth": [("ours_ptd_r15_n8192_az22.5", None, {"az": 22.5})],
        "range": [(f"ours_ptd_r{r}_n8192", None, {"range_m": r})
                   for r in (30, 60, 120)],
        "grid": [("ours_ptd_r15_n8192_div24", None, {"grid_div": 24})],
        "material": "N/A — 우리 커널에 두께 개념 없음",
    },
    "ps_alloff": {
        "elevation": [("sionna_p4000000000_r15_n8192_d1", None, {})],
        "airframe": [("sionna_p4000000000_mini5pro_r15_n8192_d1", None,
                       {"drone": "mini5pro"}),
                      ("sionna_p4000000000_s1000plus_r15_n8192_d1", None,
                       {"drone": "s1000plus"})],
        "azimuth": [("sionna_p4000000000_r15_n8192_az22.5_d1", None, {"az": 22.5}),
                     ("sionna_p4000000000_r15_n8192_az45_d1", None, {"az": 45})],
        "range": [(f"sionna_p4000000000_r{r}_n8192_d1", None, {"range_m": r})
                   for r in (30, 60, 120, 240, 480)],
        "airframe_x_range": [(f"sionna_p4000000000_{d}_r{r}_n8192_d1", None,
                              {"drone": d, "range_m": r})
                             for d in ("mini5pro", "s1000plus")
                             for r in (30, 60, 120)],
        "grid": "N/A — λ/div PO 적분격자는 우리 커널 전용 축(PathSolver 에 대응물 없음)",
        "material": [("sionna_p4000000000_r15_n8192_shell0.5mm_d1", None,
                       {"shell_mm": 0.5}),
                      ("sionna_p4000000000_r15_n8192_shell0.75mm_d1", None,
                       {"shell_mm": 0.75}),
                      ("sionna_p4000000000_r15_n8192_shell1.5mm_d1", None,
                       {"shell_mm": 1.5}),
                      ("sionna_p4000000000_r15_n8192_shell0.75mm_prop0.9mm_d1",
                       None, {"shell_mm": 0.75, "prop_mm": 0.9})],
        "parts": [("sionna_p4000000000_partsprop_r15_n8192_d1", None,
                    {"parts": "prop"}),
                   ("sionna_p4000000000_partsnoprop_r15_n8192_d1", None,
                    {"parts": "noprop"})],
    },
    "ps_onlyrefr": {
        "elevation": [("sionna_p4000000000_onlyrefr_r15_n8192", None, {})],
        "airframe": [("sionna_p4000000000_onlyrefr_mini5pro_r15_n8192", None,
                       {"drone": "mini5pro"}),
                      ("sionna_p4000000000_onlyrefr_s1000plus_r15_n8192", None,
                       {"drone": "s1000plus"}),
                      ("sionna_p4000000000_swR1D0E0F1_mini5pro_r15_n8192_d1", None,
                       {"drone": "mini5pro", "note": "동일 물리(R1D0E0F1·d1) 7앙각판"}),
                      ("sionna_p4000000000_swR1D0E0F1_s1000plus_r15_n8192_d1", None,
                       {"drone": "s1000plus", "note": "동일 물리(R1D0E0F1·d1) 7앙각판"})],
        "azimuth": [(f"sionna_p4000000000_onlyrefr_r15_n8192_az{a:g}", None,
                      {"az": a}) for a in (22.5, 45, 67.5)],
        "range": [(f"sionna_p4000000000_onlyrefr_r{r}_n8192", None,
                    {"range_m": r}) for r in (30, 60, 120, 240)],
        "grid": "N/A — 위와 동일(우리 커널 전용 축)",
        "material": "N/A — 이번 큐 계획에 없음(두께 팔은 다끔에서만)",
        "parts": [("sionna_p4000000000_onlyrefr_partsprop_r15_n8192", None,
                    {"parts": "prop"}),
                   ("sionna_p4000000000_onlyrefr_partsnoprop_r15_n8192", None,
                    {"parts": "noprop"})],
    },
}

matrix = {}
n_cells = 0
for armk, axes in MATRIX_SPEC.items():
    matrix[armk] = {"label": ARM_LABEL[armk], "axes": {}}
    for axk, spec in axes.items():
        if isinstance(spec, str):
            matrix[armk]["axes"][axk] = {"structural_na_ko": spec}
            continue
        note = None
        if armk == "ps_alloff" and axk == "material":
            note = ("⭐셸 두께(0.5/0.75/1.5 mm ↔ 기본 100 mm)는 el −30 에서 **요동(AC)을 "
                    "0.00 dB 도 안 움직인다**(전부 −135.66 dB) — 움직이는 것은 DC(동체 "
                    "정지 성분)뿐(−137.1 → −144.2/−143.3/−141.2 dB). 반면 프롭 두께 "
                    "0.9 mm 는 AC 를 **−16.99 dB** 내린다(−135.66 → −152.65, 리듬 80.5→"
                    "75.3 %·빗살 52.0→45.0 dB — 무늬는 생존). 원장 level_db(DC 포함)로 "
                    "셸 효과를 읽으면 AC/DC 잣대 함정에 걸린다 — 재질 정정(MATERIAL_"
                    "CORRECTION.md)의 마이크로도플러 파급은 프롭 두께 항이 전부다.")
        cells = []
        for eng, els, extra in spec:
            if eng not in CELLS_AVAIL:
                continue
            use = CELLS_AVAIL[eng] if els is None else els
            for el in use:
                c = slim(cs(eng, el))
                c.update({k: v for k, v in extra.items()})
                c["engine"] = eng
                cells.append(c)
                n_cells += 1
        matrix[armk]["axes"][axk] = ({"cells": cells} if note is None
                                     else {"note_ko": note, "cells": cells})

# 별칭 두 팔 + 선배PO — 데이터 없이 각주만
matrix["ps_edgeonly"] = {
    "label": "PathSolver 모서리만",
    "alias_of": "ps_alloff",
    "note_ko": "≡ PS다끔과 비트동일(모서리 스위치는 회절 게이트 안 — 소스 게이트). "
               "재계산 없음, 표·그림에 «동일 데이터» 각주로 싣는다.",
}
matrix["ps_refr_edge"] = {
    "label": "PathSolver 굴절+모서리",
    "alias_of": "ps_onlyrefr",
    "note_ko": "≡ PS굴절만과 동일 — 별칭 표기, 재계산 없음.",
}
matrix["senior_po"] = {
    "label": "선배 커널 (jihyuck PO)",
    "note_ko": "별도 원장(outputs/jihyuck_po/ PX4 기동창 grade0-7 + "
               "bridge_cross_precise.json). 앙각×방위×거리 프레임 칸이 없는 것이 "
               "구조적 정상 — 기동창 시나리오 전용.",
}

# ═══════════════════════════════════════════════════════════════════════════ #
# ① PS굴절만 기체축 — 굴절만 생존이 기체 불문인가
# ═══════════════════════════════════════════════════════════════════════════ #
q1_cells = {}
for d, eng in [("matrice4e", "sionna_p4000000000_onlyrefr_r15_n8192"),
               ("mini5pro", "sionna_p4000000000_onlyrefr_mini5pro_r15_n8192"),
               ("s1000plus", "sionna_p4000000000_onlyrefr_s1000plus_r15_n8192")]:
    q1_cells[d] = [slim(cs(eng, el)) for el in CELLS_AVAIL[eng]]
# 동일물리 7앙각판(swR1D0E0F1_d1)도 병기
q1_full = {}
for d, eng in [("mini5pro", "sionna_p4000000000_swR1D0E0F1_mini5pro_r15_n8192_d1"),
               ("s1000plus", "sionna_p4000000000_swR1D0E0F1_s1000plus_r15_n8192_d1")]:
    q1_full[d] = [slim(cs(eng, el)) for el in CELLS_AVAIL[eng]]

# 빗각 생존 판정 — 앙각 0(정면 익사 자리) 제외, 리듬>널 여유와 빗살 대비
def survive(cells):
    ob = [c for c in cells if c["el"] < 0 and not c["flags"]]
    if not ob:
        return None
    return dict(
        n_oblique=len(ob),
        rhythm_range_pct=[min(c["rhythm_share_pct"] for c in ob),
                          max(c["rhythm_share_pct"] for c in ob)],
        rhythm_margin_over_null_pp=[
            round(min(c["rhythm_share_pct"] - c["rhythm_null_pct"] for c in ob), 1),
            round(max(c["rhythm_share_pct"] - c["rhythm_null_pct"] for c in ob), 1)],
        comb_range_db=[min(c["comb_contrast_db"] for c in ob
                           if c["comb_contrast_db"] is not None),
                       max(c["comb_contrast_db"] for c in ob
                           if c["comb_contrast_db"] is not None)],
        frontal_el0=next((dict(rhythm=c["rhythm_share_pct"],
                               comb=c["comb_contrast_db"]) for c in cells
                          if c["el"] == 0), None),
    )

q1 = dict(
    question_ko="굴절만(R1D0E0·확산켬) 생존이 기체 불문인가",
    cells=q1_cells,
    same_physics_7el_swR1D0E0F1=q1_full,
    survival=dict((d, survive(cells)) for d, cells in
                  [("matrice4e", q1_cells["matrice4e"]),
                   ("mini5pro", q1_full["mini5pro"]),
                   ("s1000plus", q1_full["s1000plus"])]),
    verdict_ko=(
        "예 — 빗각(−15°~−75°)에서 세 기체 전부 생존. 리듬 몫이 그 기체의 널을 "
        "matrice4e +44.5~+52.4 %p · mini5pro +40.6~+62.3 %p · s1000plus +7.6~+54.8 %p "
        "웃돌고, 빗살 대비도 14.1~39.3 dB(백색 ≈ 0 dB)로 전부 뚜렷하다. "
        "⚠널은 기체마다 다르다(12.5/8.7/10.8) — 리듬 몫 절대값을 기체 사이에 직접 대지 "
        "말 것. ⭐덤으로 갈린 것: **정면(0°) 익사는 기체 불문이 아니다** — "
        "matrice4e(빗살 +0.3 dB)·mini5pro(−0.8 dB)는 익사하는데 s1000plus 는 정면에서도 "
        "산다(리듬 30.3 % > 널 10.9 · 빗살 +22.0 dB). s1000plus 의 최저 칸은 −75°"
        "(리듬 18.4 %·+14.1 dB)로 여유가 얇지만 널 위다. "
        "mini5pro 의 −60° 이하 빗살 대비 None 은 결측이 아니라 대역이 좁아 정의 불가"
        "(f_tip < 3·f_flash)인 구조적 빈칸이다."),
)

# ═══════════════════════════════════════════════════════════════════════════ #
# ② PS다끔 480 m 재실행 판정 + 다끔 거리축
# ═══════════════════════════════════════════════════════════════════════════ #
q2_ladder = {}
for el in (0.0, -30.0):
    lad = []
    for r, eng in [(15, "sionna_p4000000000_r15_n8192_d1"),
                   (30, "sionna_p4000000000_r30_n8192_d1"),
                   (60, "sionna_p4000000000_r60_n8192_d1"),
                   (120, "sionna_p4000000000_r120_n8192_d1"),
                   (240, "sionna_p4000000000_r240_n8192_d1"),
                   (480, "sionna_p4000000000_r480_n8192_d1")]:
        if el in CELLS_AVAIL.get(eng, []):
            c = slim(cs(eng, el))
            c["range_m"] = r
            lad.append(c)
    q2_ladder[f"el{el:+.0f}"] = lad
q2 = dict(
    question_ko="PS다끔 480 m 재실행 — 이전 «덜 참(인용 보류)» 해소 여부 + 거리축 완성",
    ladder=q2_ladder,
    verdict_ko=(
        "부분 해소 — **샤드는 완결됐지만 480 m 두 칸 다 인용은 여전히 못 한다**, 이유가 "
        "규명됐을 뿐이다. ① el 0: 8192/8192 전 자세 경로 있음(n_missing 0)이나 "
        "AC/DC 가 배정밀도 반올림 바닥(1e-12) 아래 = no_motion — 프롭 요동이 수치 바닥 "
        "밑으로 꺼진 칸이라 잣대 자체가 없다. ② el −30: 8192 자세 전부 계산됐고 "
        "5287(64.5 %)이 경로 0 개 — 샤드 갭이 아니라 광선 4e9 로 480 m 빗각에서 표적 "
        "경유 경로가 안 잡히는 표집 희소성. «덜 참» 딱지는 «구조적 한계(둘 다 원인 확정)» "
        "로 갈아붙인다 — 재실행으로 메꿔질 성질이 아니다. "
        "⭐다끔 거리축의 인용 가능 범위는 **15~240 m** 로 확정: el −30 리듬 78.7~84.1 % · "
        "빗살 40.5~52.0 dB 완만 감쇄 생존(굴절만과 같은 모양), el 0 은 15~120 m 익사"
        "(리듬 ≈ 널 12.5 · 빗살 ≈ 0). ⚠el 0 의 240 m 리듬 92.1 %·빗살 54.0 dB 는 "
        "AC/DC ≈ 2.4e-11 — no_motion 문턱의 24배 안(near_numeric_floor)에서 잰 수라 "
        "물리로 읽지 말 것(정면 동체 요동이 거리로 줄다 바닥에 닿기 직전의 잔재. "
        "480 m 에선 바닥 아래로 꺼진다 — 같은 현상의 연속).")
)

# ═══════════════════════════════════════════════════════════════════════════ #
# ③ ours+PTD 확장 — PTD−순정 차분
# ═══════════════════════════════════════════════════════════════════════════ #
PTD_PAIRS = [
    ("elevation", "ours_r15_n8192", "ours_ptd_r15_n8192", None),
    ("airframe_mini5pro", "ours_mini5pro_r15_n8192",
     "ours_ptd_mini5pro_r15_n8192", None),
    ("airframe_s1000plus", "ours_s1000plus_r15_n8192",
     "ours_ptd_s1000plus_r15_n8192", None),
    ("azimuth_az22.5", "ours_r15_n8192_az22.5", "ours_ptd_r15_n8192_az22.5", None),
    ("range_r30", "ours_r30_n8192", "ours_ptd_r30_n8192", None),
    ("range_r60", "ours_r60_n8192", "ours_ptd_r60_n8192", None),
    ("range_r120", "ours_r120_n8192", "ours_ptd_r120_n8192", None),
    ("grid_div24", "ours_r15_n8192_div24", "ours_ptd_r15_n8192_div24", None),
]
q3_pairs = {}
for name, a, b, _ in PTD_PAIRS:
    els = sorted(set(CELLS_AVAIL.get(a, [])) & set(CELLS_AVAIL.get(b, [])),
                 reverse=True)
    q3_pairs[name] = [pair_diff(a, b, el) for el in els]

# 요약 — 확장 칸(기체·방위·거리·격자)에서의 최대 |차분|
ext = [d for k, v in q3_pairs.items() if k != "elevation" for d in v]
base = q3_pairs["elevation"]
def _mx(ds, key):
    vals = [abs(d[key]) for d in ds if d.get(key) is not None]
    return round(max(vals), 3) if vals else None
q3 = dict(
    question_ko="PTD−순정 차분이 기체·방위·거리·격자에서 0 유지인가(프린지 몫 포함)",
    pairs=q3_pairs,
    summary=dict(
        extension_cells=len(ext),
        max_abs_level_db_ac=_mx(ext, "level_db_ac"),
        max_abs_d_rhythm_pp=_mx(ext, "d_rhythm_pp"),
        max_abs_d_comb_db=_mx(ext, "d_comb_db"),
        max_fringe_share_pct=_mx(ext, "fringe_share_pct"),
        base_7el_max_abs_level_db_ac=_mx(base, "level_db_ac"),
        base_7el_max_fringe_share_pct=_mx(base, "fringe_share_pct"),
    ),
    verdict_ko=(
        "예 — 0 유지. 확장 7칸(기체 2·방위 1·거리 3·격자 1, 전부 el −30) 전부에서 "
        "PTD−순정이 요동 레벨 |Δ| ≤ 0.02 dB · 리듬 몫 |Δ| ≤ 0.1 %p · 빗살 대비 "
        "|Δ| ≤ 0.1 dB · AC 상관 ≥ 0.9999. 프린지 몫(‖Δ_ac‖²/‖E_ac‖²)도 ≤ 0.026 % — "
        "기본판 7앙각의 최대 0.478 %(el 0)보다도 작다. ptd_level_probe 의 «PTD 레벨차는 "
        "정지 성분 아티팩트, DC 빼면 0» 판정이 기체·방위·거리·격자 어느 축을 돌려도 "
        "그대로 선다. 프린지 성분 자체는 리듬을 가진다(fringe_rhythm 33~51 %, 모서리 "
        "항이 로터를 따라 도는 것과 부합)만 크기가 4자리 아래라 팔 전체 잣대를 못 "
        "움직인다. ⚠D-8 단서 유지 — 격자 λ/12 는 ptd_edges 권고(λ/20)보다 성겨 "
        "**차분(같은 격자끼리)만 공정**하고 PTD 절대값 주장은 격자 의존성을 명시할 것."),
)

# ═══════════════════════════════════════════════════════════════════════════ #
# ④ 격자 — div24 전앙각 + div48 el-15 이 산포 밴드를 좁히나 넓히나
# ═══════════════════════════════════════════════════════════════════════════ #
q4_pairs = {"div12_vs_div24": [], "div24_vs_div48": [], "div12_vs_div48": []}
for el in CELLS_AVAIL["ours_r15_n8192_div24"]:
    q4_pairs["div12_vs_div24"].append(
        pair_diff("ours_r15_n8192", "ours_r15_n8192_div24", el))
for el in CELLS_AVAIL.get("ours_r15_n8192_div48", []):
    q4_pairs["div24_vs_div48"].append(
        pair_diff("ours_r15_n8192_div24", "ours_r15_n8192_div48", el))
    q4_pairs["div12_vs_div48"].append(
        pair_diff("ours_r15_n8192", "ours_r15_n8192_div48", el))

d1224 = q4_pairs["div12_vs_div24"]
old4 = [d for d in d1224 if d["el"] in (0.0, -15.0, -30.0, -45.0)]
new3 = [d for d in d1224 if d["el"] in (-60.0, -75.0, -90.0)]
obl = [d for d in d1224 if -75.0 <= d["el"] <= -15.0]
q4 = dict(
    question_ko="격자 λ/24 전앙각·λ/48 신규분이 산포 밴드(리듬 21.8%p·AC 3.86dB)를 좁히나 넓히나",
    r16_band_reference=dict(rhythm_pp=21.8, ac_db=3.86,
                            source="outputs/grid_convergence_check.json (el 0~-45)"),
    pairs=q4_pairs,
    summary=dict(
        old4_max_abs_ac_db=_mx(old4, "level_db_ac"),
        old4_max_abs_rhythm_pp=_mx(old4, "d_rhythm_pp"),
        new3_max_abs_ac_db=_mx(new3, "level_db_ac"),
        new3_max_abs_rhythm_pp=_mx(new3, "d_rhythm_pp"),
        all7_max_abs_ac_db=_mx(d1224, "level_db_ac"),
        all7_max_abs_rhythm_pp=_mx(d1224, "d_rhythm_pp"),
        oblique_15_75_max_abs_ac_db=_mx(obl, "level_db_ac"),
        oblique_15_75_max_abs_rhythm_pp=_mx(obl, "d_rhythm_pp"),
        comb_step_db_div12_to_24=[d["d_comb_db"] for d in d1224
                                  if d["d_comb_db"] is not None],
        div48_el15_step=dict(
            d24_minus_d12=next((dict(ac=d["level_db_ac"], rhy=d["d_rhythm_pp"],
                                     comb=d["d_comb_db"], rho=d["abs_rho_ac"])
                                for d in d1224 if d["el"] == -15.0), None),
            d48_minus_d24=next((dict(ac=d["level_db_ac"], rhy=d["d_rhythm_pp"],
                                     comb=d["d_comb_db"], rho=d["abs_rho_ac"])
                                for d in q4_pairs["div24_vs_div48"]), None),
            d48_minus_d12=next((dict(ac=d["level_db_ac"], rhy=d["d_rhythm_pp"],
                                     comb=d["d_comb_db"], rho=d["abs_rho_ac"])
                                for d in q4_pairs["div12_vs_div48"]), None),
        ),
    ),
    verdict_ko=(
        "잣대·앙각에 따라 갈린다 — 한 마디 답은 없다. "
        "① **빗각(−15°~−75°)의 요동 레벨 산포는 좁아졌다**: div24−div12 가 최대 "
        "1.31 dB(−15°)이고 새로 닫힌 −60°/−75° 는 0.02~0.10 dB 로 사실상 붙는다 — "
        "R16 밴드의 3.86 dB 는 정면(0°) 값이었음이 드러났다(빗각에 3.86 을 그대로 대면 "
        "과잉 보수). ② **전체 밴드 폭은 넓어졌다**: 직하방(−90°)이 5.62 dB·ρ 0.40 으로 "
        "최악 칸 — 단 f_tip=0 퇴화 칸이라 별표를 달고 쓴다. ③ **리듬 몫 밴드 21.8 %p 는 "
        "유지**(새 앙각 최대 16.4 %p — 안 넓어짐). 그러나 λ/48 이 −15° 리듬을 "
        "−17.8 %p 움직였다 — λ/24 로 «수렴했다» 는 말은 리듬 몫에는 못 쓴다. "
        "④ **빗살 대비는 격자 축의 새 민감 잣대**: 계단마다 +4.0~+4.6 dB(12→24), "
        "+5.6 dB(24→48, −15°) 단조 상승 — 팔 사이 빗살 비교에 ≈5 dB 급 격자 단서를 "
        "새로 달아야 한다(우리↔PS 의 30~50 dB 격차 판정은 안 흔들림). "
        "⑤ **파형 자체는 수렴 방향**: −15° 에서 계단 크기 1.31→0.12 dB, ρ 0.74→0.96. "
        "⚠귀속 미해결 승계 — 격자 위상 널(--grid-shift) 팔이 이번 큐 계획에 없어 "
        "«촘촘해서» 와 «표본 원점이 달라서» 는 아직 못 가른다(docs/GRID_PHASE_NULL.md)."),
)

# ═══════════════════════════════════════════════════════════════════════════ #
# 저장
# ═══════════════════════════════════════════════════════════════════════════ #
doc = {
    "_meta": {
        "generator": "scratchpad/frame_completion_0816.py (완성표 작성자 에이전트)",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S",
                                       time.gmtime(time.time() + 9 * 3600)) + " (UTC+9)",
        "runtime_sec": None,
        "gpu_used": False,
        "ledger": "outputs/elevation_sweep_md.{json,npz} (2026-08-16 병합본)",
        "inventory": "outputs/frame_inventory_0816.json (계획 76칸, 76/76 채움·실패 0)",
        "metric_defs": "benchmark/build_md_atlas.py cell_summary 를 그대로 임포트 — "
                       "리듬 몫(상한 위 정수배 몫)·널(칸별 정확 계수)·빗살 대비(상한 아래 "
                       "on/off 전력비)·요동 절대전력(DC 제거). 정의 재작성 없음.",
        "conventions_ko": [
            "레벨(dB) 비교는 전부 정지 성분(DC) 제거 후 — moving_power_db 열만 쓴다",
            "리듬 몫은 상한 위 한정 잣대라 거리 팔에서 퇴화 — comb_contrast_db 병용",
            "격자 산포 밴드(리듬 21.8%p·AC 3.86dB) 안의 팔 사이 차이는 판정 불가로 적는다",
            "널(백색 리듬 몫)은 기체마다 다르다(matrice4e≈12.6·s1000plus≈10.8·mini5pro≈8.7)",
            "직하방(el −90)은 f_tip=0 으로 상한 잣대 퇴화 — tip_ceiling_degenerate 깃발",
        ],
    },
    "verdicts_ko": {
        "q1_onlyrefr_airframe": "생존 기체 불문(빗각) — 단 정면 익사는 기체 불문이 아니다(s1000plus 예외)",
        "q2_alloff_480m": "부분 해소 — 샤드 완결·원인 확정, 인용 보류는 유지(el0 수치바닥·el−30 경로희소)",
        "q3_ptd_diff": "0 유지 — 확장 7칸 전부 |ΔdB|≤0.02·프린지≤0.026 %",
        "q4_grid_band": "빗각 AC 밴드는 좁아지고(≤1.31 dB) 전체 폭은 −90° 가 5.62 dB 로 넓힘·리듬 21.8 %p 유지·빗살 대비에 새 격자 단서(≈5 dB)",
    },
    "alias_rerun_note_ko": alias_note_ko,
    "alias_bit_identity_checks": alias_checks,
    "completion_from_inventory": {
        "planned_cells": INV["summary"]["planned_cells"],
        "filled": INV["summary"]["filled"],
        "missing": INV["summary"]["missing"],
        "structurally_unfillable": INV["summary"]["structurally_unfillable"],
        "true_shard_gaps": INV["summary"]["true_shard_gaps"],
    },
    "matrix": matrix,
    "q1_onlyrefr_airframe": q1,
    "q2_alloff_480m": q2,
    "q3_ptd_diff": q3,
    "q4_grid_band": q4,
}
doc["_meta"]["runtime_sec"] = round(time.time() - t0, 1)
json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
print("saved", OUT, f"cells={n_cells}", f"runtime={doc['_meta']['runtime_sec']}s")
