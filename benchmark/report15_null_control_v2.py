# -*- coding: utf-8 -*-
"""
report15_null_control_v2.py — ⭐⭐ **대조군 B: 널(null) 대조 — 강화판**
================================================================================

v1(`report15_null_control.py`) 은 지시받은 4 종을 전부 돌리고 gate_pass 를 냈다.
이 파일은 v1 을 **그대로 재실행**한 위에, v1 판정이 아직 열어 두고 있던 **네 개의 반론**을
막는 팔과 분석을 얹는다. 측정·통계·판정 코드는 v1/probe 에서 **import 만** 한다
(다른 코드로 재면 비교가 성립하지 않는다).

v1 이 아직 막지 못한 반론 — 그리고 이 파일이 그것을 어떻게 막는가
--------------------------------------------------------------------------------
 ⓐ "널의 산물 바닥 0.010 dB 는 **그 팔의 재추적 잡음이 원래 3배 조용해서** 작은 것 아닌가."
     실측: sphere_mini2_plastic σ=0.652 dB vs full_mini2 σ=1.831 dB.
     → **잡음정규화 바닥**을 계산한다: 널의 ptp 를 신호팔의 잡음 수준으로 환산
       (ptp × σ_signal/σ_null) 하고, ptp/σ · ptp/SE 도 나란히 둔다. 손으로 고르지 않는다.

 ⓑ "구를 z 로 돌리는 것은 **약한 널**이다 — z 회전은 uv 테셀레이션의 **대칭**이라
     φ 가 360/seg 의 배수면 메쉬가 자기 자신이 된다. 즉 z 널이 탐색하는 삼각형 상태는
     폭 360/seg 짜리 좁은 주기 안에 갇힌다."
     → ⭐ **텀블 널**: 같은 구를 z 가 아닌 축으로 굴린다(그런 주기가 없다). 구는 어떤
       회전에도 불변이므로 물리적 변조는 여전히 정확히 0 이어야 한다.
     ⚠⚠ **초안의 주장 한 건이 틀렸고, 반증을 기록으로 남긴다.** 초안은 "x축 텀블이 극점을
       조명면을 가로질러 쓸고 지나가게 한다" 고 적었는데 **거짓**이다 — 시선
       u=(cos15°,0,sin15°) 는 y 성분이 0 이고 x 회전은 x 성분을 보존하므로 ±z 극점은
       y–z 평면에 갇혀 시선에서 최소 75° 까지밖에 못 온다. 극점을 보어사이트로 통과시키는
       축은 **y**(최소 1.87°) 다 → `report15_null_control_v2_append.py` 가 y 텀블 널을
       추가하고 `tessellation_symmetry.falsified_claim` 에 이 정정을 담는다.
     ⚠ 두 번째 사실도 같이 적는다: **uv 구는 어느 축으로 굴려도 조명면 삼각형의 크기
       분포가 바뀌지 않는다**(가시 반구가 언제나 전 위도대를 포함하므로). 구 널이 흔드는
       것은 '어느 삼각형이 켜지는가' 뿐이다 — ⭐ 그래서 최종 근거는 구 널이 아니라
       **disc 널**이 지탱한다(드론과 삼각형 수·재질·꼭짓점 변위 1.3888λ 가 전부 같은데 변조 0).

 ⓒ "④(삼각형 절반)는 **점 하나**다. ptp 가 3.866 vs 3.898 dB 로 같게 나왔다는 것이
     '해상도 무관' 인지 '우연' 인지 갈리지 않는다."
     → ⭐ **사다리**(100% → 50% → 25% → 12.5%)로 늘리고, 요약통계 대신 **h(φ) 곡선 자체를
       상관**시킨다. 곡선이 같이 움직이면 해상도 무관이 확인되고, ptp 만 같고 곡선이
       어긋나면 그 일치는 우연이다.

 ⓓ "matrice4e 산물 바닥은 쟀는데 **그 기체의 신호가 없다** — 분모 없는 분자다."
     → matrice4e 로터 위상 스텝 팔을 추가해 기체별로 (바닥, 신호, 여유) 를 각각 낸다.
       ⚠ R=3 m 는 matrice4e 원거리장(2D²/λ=8.259 m) 미달이다. RT 는 구면파를 추적하므로
         계산은 유효하나 이 값을 σ(RCS) 로 환산해 인용하면 안 된다 — JSON 에 표시해 둔다.

⭐ 추가 계량: `facet_churn` — "메쉬가 **레이더가 보는 쪽에서** 실제로 얼마나 갈렸나".
   · projected_area_m2 = Σ A·(n̂·û)  (n̂·û>0 인 면만) — **물리적 투영면적**.
     널이라면 이 값이 위상에 무관해야 한다. 형상 불변의 **수치적 증거**이지 주장이 아니다.
   · n_facets_lit / max_lit_facet_area_lambda2 / centroid_shift_median_lambda
     — 같은 투영면적을 **다른 삼각형 배치로** 만들고 있다는 증거.

⛔ src/drones.py · src/drone_cad.py 는 **읽기만** 한다(v1 의 self_check 가 분절 재현을
   꼭짓점 해시로 대조한다).
⛔ 숫자 손입력 금지 — 구 반경·데시메이션 비율·요각·원거리장 거리 전부 계산해서 JSON 에 담는다.
그림 없음(순수 측정). 본문·주석·print 한국어.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#  ⭐ v1 을 import 하는 순간 report15_probe → gpu.pick() 이 돌아 여유 메모리가 가장 많은
#     카드를 잡고, 그 다음에 mitsuba/sionna 가 올라온다. 순서를 바꾸면 안 된다.
import report15_null_control as N                                        # noqa: E402
import report15_probe as P                                               # noqa: E402
from report15_null_control import (Arm, articulate, decimate_by_group,   # noqa: E402
                                   drive_metrics, mesh_metrics, run_arm,
                                   rotor_phase_vector, sphere_matched)
from report15_probe import AZ_DEG, EL_DEG, FC, LAM, RANGE_M              # noqa: E402
from drones import (DRONES, DRONE_GROUP_MAT, build_frame,                # noqa: E402
                    build_propeller, drone_colors)

OUT_JSON = N.OUT_JSON                       # outputs/report15_null_control.json
PROBE_JSON = N.PROBE_JSON


# --------------------------------------------------------------------------- #
#  ⭐ 레이더가 보는 쪽에서 잰 '메쉬 갈림' — 널이 널인 이유를 수치로 남긴다
# --------------------------------------------------------------------------- #
def facet_churn(mesh_at, phis, az=AZ_DEG, el=EL_DEG) -> dict:
    """조명면(n̂·û>0) 삼각형의 **투영면적·개수·배치**가 위상에 따라 어떻게 변하나.

    투영면적이 위상 무관인데 삼각형 배치가 크게 바뀌면 → '같은 물체를 다른 메쉬로 표현'
    = 이상적인 널. 투영면적까지 흔들리면 그 팔은 널이 아니다(형상이 실제로 바뀐 것)."""
    u = P.look_dir(az, el)
    rows, C0 = [], None
    for phi in phis:
        m = mesh_at(float(phi))
        V = np.asarray(m.v, float)
        F = np.asarray(m.f, int)
        p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        cr = np.cross(p1 - p0, p2 - p0)                 # |cr| = 2·면적, 방향 = 법선
        area2 = np.linalg.norm(cr, axis=1)
        lit = (cr @ u) > 0.0                            # 레이더 쪽을 향한 면
        proj = float(np.sum((cr @ u)[lit]) / 2.0)       # Σ A·(n̂·û)
        cen = (p0 + p1 + p2) / 3.0
        Cl = cen[lit]
        rows.append(dict(phase_deg=float(phi), n_lit=int(lit.sum()),
                         projected_area_m2=proj,
                         max_lit_facet_area_lambda2=float(area2[lit].max() / 2.0 / LAM ** 2)
                         if lit.any() else 0.0))
        if C0 is None:
            C0 = Cl
        elif Cl.size and C0.size:
            from scipy.spatial import cKDTree
            d, _ = cKDTree(C0).query(Cl)
            rows[-1]["lit_centroid_shift_median_lambda"] = float(np.median(d) / LAM)
    pa = np.array([r["projected_area_m2"] for r in rows], float)
    nl = np.array([r["n_lit"] for r in rows], float)
    sh = [r.get("lit_centroid_shift_median_lambda") for r in rows[1:]
          if r.get("lit_centroid_shift_median_lambda") is not None]
    return dict(
        per_phase=rows,
        projected_area_mean_m2=float(pa.mean()),
        projected_area_ptp_m2=float(pa.max() - pa.min()),
        projected_area_ptp_db=float(20.0 * math.log10(
            max(pa.max(), 1e-30) / max(pa.min(), 1e-30))),
        projected_area_cv=float(pa.std(ddof=1) / pa.mean()) if pa.mean() > 0 else None,
        n_lit_mean=float(nl.mean()), n_lit_ptp=float(nl.max() - nl.min()),
        lit_centroid_shift_median_lambda_max=(float(max(sh)) if sh else None),
        note_ko=("투영면적(Σ A·n̂·û)이 위상 무관이면 **물리적 표적이 안 바뀐 것**이고, "
                 "그 상태에서 조명면 삼각형 무게중심이 크게 움직였다면 **같은 물체를 다른 "
                 "삼각형 배치로** 표현한 것이다 — 이것이 널이 검사하려던 바로 그 조건이다."))


# --------------------------------------------------------------------------- #
#  추가 팔 — v1 의 10개 위에 얹는다
# --------------------------------------------------------------------------- #
def build_arms_v2(reduction_ladder=(0.75, 0.875)) -> tuple[list, dict]:
    """v1 팔 전부 + (사다리 · 텀블 구 · matrice4e 신호/구)."""
    arms, geo = N.build_arms({"full", "norotor", "disc", "half", "yaw", "sphere"},
                             reduction=0.5)

    # ── ⓒ 해상도 사다리 (mini2) ───────────────────────────────────────────── #
    spec = DRONES["mini2"]
    cols = drone_colors(spec)
    frame = build_frame(spec)
    pc, pw = build_propeller(spec), build_propeller(spec, mirror=True)
    full0 = articulate(frame, pc, pw, spec, rotor_phase_vector(spec, 0.0))
    matmap = {g: DRONE_GROUP_MAT[g][0] for g in full0.groups()}
    ladder = {}
    for red in reduction_ladder:
        fh, rep_f = decimate_by_group(frame, float(red))
        ph_, rep_p = decimate_by_group(pc, float(red))
        pwh, _ = decimate_by_group(pw, float(red))
        m0 = articulate(fh, ph_, pwh, spec, rotor_phase_vector(spec, 0.0))
        keep = float(m0.n_tris() / max(1, full0.n_tris()))
        key = f"red{int(round(red * 1000)):03d}_mini2"
        info = dict(target_reduction=float(red), tris_full=int(full0.n_tris()),
                    tris_kept=int(m0.n_tris()), kept_frac=keep,
                    frame_by_group=rep_f, prop_template=rep_p, mesh=mesh_metrics(m0))
        ladder[key] = info
        arms.append(Arm(key,
                        f"mini2 · 삼각형 {keep * 100:.1f}% 로 줄임 + 같은 로터 위상 스텝",
                        "resolution", True,
                        lambda phi, s=spec, a=fh, b=ph_, c=pwh:
                            articulate(a, b, c, s, rotor_phase_vector(s, phi)),
                        matmap, cols, extra=info))
    geo.setdefault("mini2", {})["ladder"] = ladder

    # ── ⓑ 텀블 널 — 같은 구를 **x 축**으로 굴린다 ─────────────────────────── #
    r1 = geo["mini2"]["mesh"]["r_equal_volume_m"]
    sph1, si1 = sphere_matched(r1, geo["mini2"]["mesh"]["n_tris"])
    tumble_note = ("⭐ x 축 회전. 구는 **어떤 회전에도 불변**이라 물리적 변조는 정확히 0 인데, "
                   "uv 구의 극점(면이 잘게 뭉친 특이점)이 조명면을 가로질러 쓸고 지나가 "
                   "레이더가 보는 삼각형 배치가 매 위상마다 통째로 바뀐다. z 회전 널은 띠를 "
                   "자기 위로 미끄러뜨릴 뿐이라 면의 집합이 사실상 보존된다 — 그 약점을 막는다.")
    for mat in ("plastic", "carbon"):
        arms.append(Arm(f"sphere_mini2_{mat}_tumble",
                        f"mini2 등가부피 구({mat}) · **x축 텀블**(테셀레이션 최대 교란)",
                        "null", False,
                        lambda phi, m=sph1: m.rotated("x", float(phi)),
                        {"sph": mat}, {"sph": (0.7, 0.7, 0.7)},
                        extra=dict(si1, material=mat, rotation_axis="x",
                                   note_ko=tumble_note)))
    # ── ⓓ matrice4e — 신호 팔 + 강산란 구 + 텀블 구 ───────────────────────── #
    spec2 = DRONES["matrice4e"]
    cols2 = drone_colors(spec2)
    frame2 = build_frame(spec2)
    pc2, pw2 = build_propeller(spec2), build_propeller(spec2, mirror=True)
    full2 = articulate(frame2, pc2, pw2, spec2, rotor_phase_vector(spec2, 0.0))
    matmap2 = {g: DRONE_GROUP_MAT[g][0] for g in full2.groups()}
    geo.setdefault("matrice4e", {})["mesh"] = mesh_metrics(full2)
    D2 = float(max(geo["matrice4e"]["mesh"]["span_m"]))
    geo["matrice4e"]["farfield"] = dict(
        max_span_m=D2, farfield_2D2_over_lambda_m=float(2.0 * D2 ** 2 / LAM),
        range_m=float(RANGE_M),
        in_farfield=bool(RANGE_M >= 2.0 * D2 ** 2 / LAM),
        note_ko=("⚠ R < 2D²/λ 이면 원거리장 미달이다. RT 는 구면파를 추적하므로 계산 자체는 "
                 "유효하지만 이 거리의 |h| 를 σ(RCS) 로 환산해 인용하면 안 된다. "
                 "널 대조는 **같은 거리에서 널과 신호를 비교**하는 것이므로 영향받지 않는다."))
    arms.append(Arm("full_matrice4e", "matrice4e · 로터 위상 스텝(실측 표적의 기준 신호)",
                    "signal", True,
                    lambda phi, s=spec2, a=frame2, b=pc2, c=pw2:
                        articulate(a, b, c, s, rotor_phase_vector(s, phi)),
                    matmap2, cols2, extra=geo["matrice4e"]["farfield"]))

    r2 = geo["matrice4e"]["mesh"]["r_equal_volume_m"]
    sph2, si2 = sphere_matched(r2, geo["matrice4e"]["mesh"]["n_tris"])
    geo["matrice4e"]["sphere"] = si2
    arms.append(Arm("sphere_matrice4e_carbon",
                    "matrice4e 등가부피 구(carbon, 강산란) · z 회전", "null", False,
                    lambda phi, m=sph2: m.rotated("z", float(phi)),
                    {"sph": "carbon"}, {"sph": (0.7, 0.7, 0.7)},
                    extra=dict(si2, material="carbon")))
    arms.append(Arm("sphere_matrice4e_plastic_tumble",
                    "matrice4e 등가부피 구(plastic) · **x축 텀블**", "null", False,
                    lambda phi, m=sph2: m.rotated("x", float(phi)),
                    {"sph": "plastic"}, {"sph": (0.7, 0.7, 0.7)},
                    extra=dict(si2, material="plastic", rotation_axis="x",
                               note_ko=tumble_note)))
    return arms, geo


# --------------------------------------------------------------------------- #
#  ⓐ 잡음정규화 산물 바닥 — "널이 원래 조용한 팔이라 작게 나온 것" 을 막는다
# --------------------------------------------------------------------------- #
def normalized_floor(arms_out: dict, signal_key: str) -> dict:
    """널의 ptp 를 **신호팔의 재추적 잡음 수준으로 환산**해 바닥을 다시 잡는다.

    각 팔의 재추적 σ 는 팔마다 다르다(구는 경로가 많고 균질해 원래 조용하다). 산물이
    잡음에 비례해 커진다고 보수적으로 가정하면, 널의 ptp 를 σ_signal/σ_null 배 해서
    비교해야 공정하다. 정규화 전·후를 **둘 다** 남긴다."""
    sig = (arms_out.get(signal_key) or {}).get("headline")
    if not sig:
        return dict(available=False, signal_key=signal_key)
    s_sig = sig.get("noise_floor_db")
    rows = []
    for k, v in arms_out.items():
        h = v["headline"]
        if h["role"] != "null":
            continue
        cand = [x for x in (h.get("modulation_ptp_db"), h.get("modulation_ptp_db_prop"))
                if x is not None]
        if not cand:
            continue
        ptp = float(max(cand))
        s_n = h.get("noise_floor_db")
        scale = (float(s_sig) / float(s_n)) if (s_sig and s_n and s_n > 0) else None
        rows.append(dict(arm=k, ptp_db=ptp, noise_floor_db=s_n,
                         ptp_over_own_sigma=(ptp / s_n) if (s_n and s_n > 0) else None,
                         ptp_over_own_se=h.get("ptp_over_noise_se"),
                         noise_scale_to_signal=scale,
                         ptp_rescaled_db=(ptp * scale) if scale else ptp,
                         mesh_frozen=bool(h["mesh_frozen"]),
                         vertex_shift_max_lambda=h.get("vertex_shift_max_lambda"),
                         surface_shift_max_lambda=h.get("surface_shift_max_lambda"),
                         significant=bool(h["modulation_above_noise"])))
    if not rows:
        return dict(available=False, signal_key=signal_key)
    rows.sort(key=lambda r: -(r["ptp_rescaled_db"] or 0.0))
    top = rows[0]
    raw = max(rows, key=lambda r: r["ptp_db"])
    sp = sig.get("modulation_ptp_db")
    out = dict(available=True, signal_key=signal_key,
               signal_ptp_db=sp, signal_noise_floor_db=s_sig,
               signal_ptp_over_se=sig.get("ptp_over_noise_se"),
               floor_raw_db=raw["ptp_db"], floor_raw_arm=raw["arm"],
               floor_rescaled_db=top["ptp_rescaled_db"], floor_rescaled_arm=top["arm"],
               by_arm=rows,
               note_ko=("floor_rescaled = 널 ptp × (σ_signal/σ_null). 널이 원래 조용한 팔이라 "
                        "바닥이 낮게 나온 것 아니냐는 반론을 막는 **보수적** 바닥이다."))
    if sp is not None:
        out["margin_raw_db"] = float(sp - raw["ptp_db"])
        out["margin_rescaled_db"] = float(sp - top["ptp_rescaled_db"])
        out["signal_over_floor_rescaled_ratio"] = float(
            sp / max(top["ptp_rescaled_db"], 1e-12))
    return out


# --------------------------------------------------------------------------- #
#  ⓒ h(φ) 곡선 자체를 비교 — 요약통계가 우연히 같은 것과 구별한다
# --------------------------------------------------------------------------- #
def _curve(arms_out, key, mode="prod", channel="all"):
    v = ((arms_out.get(key) or {}).get("verdict") or {}).get(f"{mode}/{channel}") or {}
    c = v.get("phase_mean_amp_db")
    return np.asarray(c, float) if (c and len(c) >= 3) else None


def curve_pair(arms_out, a, b, mode="prod", channel="all") -> dict:
    x, y = _curve(arms_out, a, mode, channel), _curve(arms_out, b, mode, channel)
    if x is None or y is None or x.shape != y.shape:
        return dict(available=False, a=a, b=b, mode=mode, channel=channel)
    xc, yc = x - x.mean(), y - y.mean()
    den = float(np.linalg.norm(xc) * np.linalg.norm(yc))
    return dict(available=True, a=a, b=b, mode=mode, channel=channel, n=int(x.size),
                pearson_r=(float(xc @ yc / den) if den > 0 else None),
                rms_diff_db=float(np.sqrt(np.mean((xc - yc) ** 2))),
                ptp_a_db=float(x.max() - x.min()), ptp_b_db=float(y.max() - y.min()),
                level_delta_db=float(y.mean() - x.mean()))


def resolution_ladder(arms_out: dict, full_key="full_mini2") -> dict:
    """④ 를 **사다리**로 답한다 — ptp 뿐 아니라 h(φ) 곡선이 유지되나."""
    rows = []
    for k, v in arms_out.items():
        h = v["headline"]
        if h["role"] not in ("signal", "resolution") or not k.endswith("mini2"):
            continue
        ex = v.get("extra") or {}
        keep = ex.get("kept_frac", 1.0 if k == full_key else None)
        pr = curve_pair(arms_out, full_key, k) if k != full_key else None
        prp = curve_pair(arms_out, full_key, k, channel="prop") if k != full_key else None
        rows.append(dict(arm=k, kept_frac=keep, n_tris=h["n_tris"],
                         level_db=h.get("level_db"),
                         noise_floor_db=h.get("noise_floor_db"),
                         modulation_ptp_db=h.get("modulation_ptp_db"),
                         modulation_ptp_db_prop=h.get("modulation_ptp_db_prop"),
                         ptp_over_noise_se=h.get("ptp_over_noise_se"),
                         significant=bool(h["modulation_above_noise"]),
                         curve_vs_full_all=pr, curve_vs_full_prop=prp))
    rows.sort(key=lambda r: -(r["kept_frac"] or 0.0))
    base = next((r for r in rows if r["arm"] == full_key), None)
    span = [r for r in rows if r["modulation_ptp_db"] is not None]
    out = dict(rows=rows, n_levels=len(rows),
               all_significant=bool(rows and all(r["significant"] for r in rows)))
    if base and span:
        pt = [r["modulation_ptp_db"] for r in span]
        lv = [r["level_db"] for r in span if r["level_db"] is not None]
        out.update(
            modulation_ptp_span_db=float(max(pt) - min(pt)),
            modulation_ptp_max_rel_change=float(
                max(abs(p - base["modulation_ptp_db"]) for p in pt)
                / max(abs(base["modulation_ptp_db"]), 1e-12)),
            level_span_db=(float(max(lv) - min(lv)) if lv else None),
            min_pearson_r_vs_full=min(
                [r["curve_vs_full_all"]["pearson_r"] for r in rows
                 if r["curve_vs_full_all"] and r["curve_vs_full_all"].get("pearson_r")
                 is not None] or [None]))
    out["note_ko"] = ("삼각형을 줄여도 ptp 와 **h(φ) 곡선 모양**이 함께 유지되면 변조는 "
                      "삼각형 배치가 만드는 톱니가 아니다. ptp 만 같고 곡선이 어긋나면 "
                      "그 일치는 우연이다 — 그래서 상관을 같이 잰다.")
    return out


def by_airframe(arms_out: dict) -> dict:
    """기체별 (신호, 널들, 바닥, 여유). ⭐ matrice4e 는 실측 표적이라 따로 낸다."""
    out = {}
    for tag, sig, nulls in (
            ("mini2", "full_mini2",
             ["norotor_mini2", "disc_mini2", "sphere_mini2_plastic", "sphere_mini2_carbon",
              "sphere_mini2_static", "sphere_mini2_plastic_tumble",
              "sphere_mini2_carbon_tumble", "sphere_mini2_plastic_ytumble",
              "sphere_mini2_carbon_ytumble"]),
            ("matrice4e", "full_matrice4e",
             ["sphere_matrice4e_plastic", "sphere_matrice4e_carbon",
              "sphere_matrice4e_plastic_tumble", "sphere_matrice4e_plastic_ytumble"])):
        sub = {k: v for k, v in arms_out.items()
               if k == sig or k in nulls}
        if sig not in sub:
            continue
        out[tag] = normalized_floor(sub, sig)
        out[tag]["nulls_present"] = [k for k in nulls if k in sub]
        out[tag]["nulls_that_signalled"] = [
            k for k in nulls if k in sub and sub[k]["headline"]["modulation_above_noise"]]
    return out


def tumble_vs_spin(arms_out: dict) -> dict:
    """ⓑ 를 명시적으로 — 텀블 널이 z 회전 널보다 **더 세게 갈았는데도** 조용한가."""
    rows = {}
    for a, b in (("sphere_mini2_plastic", "sphere_mini2_plastic_tumble"),
                 ("sphere_mini2_carbon", "sphere_mini2_carbon_tumble"),
                 ("sphere_matrice4e_plastic", "sphere_matrice4e_plastic_tumble"),
                 #  y 텀블 — 극점이 보어사이트를 실제로 통과하는 축 (append 가 채운다)
                 ("sphere_mini2_plastic", "sphere_mini2_plastic_ytumble"),
                 ("sphere_mini2_carbon", "sphere_mini2_carbon_ytumble"),
                 ("sphere_matrice4e_plastic", "sphere_matrice4e_plastic_ytumble")):
        ha = (arms_out.get(a) or {}).get("headline")
        hb = (arms_out.get(b) or {}).get("headline")
        if not ha or not hb:
            continue
        rows[f"{a}→{b}"] = dict(
            spin_ptp_db=ha.get("modulation_ptp_db"), tumble_ptp_db=hb.get("modulation_ptp_db"),
            spin_ptp_over_se=ha.get("ptp_over_noise_se"),
            tumble_ptp_over_se=hb.get("ptp_over_noise_se"),
            spin_significant=ha.get("modulation_above_noise"),
            tumble_significant=hb.get("modulation_above_noise"),
            spin_surface_shift_lambda=ha.get("surface_shift_max_lambda"),
            tumble_surface_shift_lambda=hb.get("surface_shift_max_lambda"))
    return dict(pairs=rows,
                any_tumble_signalled=bool(any(v.get("tumble_significant") for v in rows.values())),
                note_ko=("텀블은 극점을 조명면으로 끌고 와 삼각형 배치를 최대로 흔든다. "
                         "그래도 조용하면 '메쉬가 갈리는 것만으로는 변조가 생기지 않는다' 가 "
                         "z 회전보다 훨씬 강한 근거로 확정된다."))


def overall_verdict_v2(J: dict) -> dict:
    A = J["arms"]
    cmp_ = J["comparison"]
    nf = J["floor_normalized"]
    lad = J["resolution_ladder"]
    per = J["by_airframe"]
    tv = J["tumble_vs_spin"]
    ch = J.get("facet_churn", {})

    nulls_bad = sorted({k for k, v in A.items()
                        if v["headline"]["role"] == "null"
                        and v["headline"]["modulation_above_noise"]})
    pos = {k: v["headline"] for k, v in A.items() if v["headline"]["role"] == "positive"}
    sigs = {k: v["headline"] for k, v in A.items() if v["headline"]["role"] == "signal"}
    #  ⭐ 널의 투영면적이 정말 위상 무관이었나 — 널이 널이었다는 수치 증거
    null_shape_invariant = {k: v["projected_area_ptp_db"] for k, v in ch.items()
                            if (A.get(k) or {}).get("headline", {}).get("role") == "null"}
    return dict(
        positive_controls_fired=bool(pos) and all(v["modulation_above_noise"]
                                                  for v in pos.values()),
        signals_significant={k: bool(v["modulation_above_noise"]) for k, v in sigs.items()},
        all_signals_significant=bool(sigs) and all(v["modulation_above_noise"]
                                                   for v in sigs.values()),
        nulls_clean=bool(not nulls_bad), nulls_that_signalled=nulls_bad,
        n_null_arms=int(sum(1 for v in A.values() if v["headline"]["role"] == "null")),
        artifact_floor_raw_db=nf.get("floor_raw_db"),
        artifact_floor_rescaled_db=nf.get("floor_rescaled_db"),
        signal_ptp_db=nf.get("signal_ptp_db"),
        margin_rescaled_db=nf.get("margin_rescaled_db"),
        signal_over_floor_ratio=nf.get("signal_over_floor_rescaled_ratio"),
        resolution_ptp_max_rel_change=lad.get("modulation_ptp_max_rel_change"),
        resolution_min_pearson_r=lad.get("min_pearson_r_vs_full"),
        tumble_any_signalled=tv.get("any_tumble_signalled"),
        #  ⭐ 널이 조용한 것과 별개로, 신호의 변조가 '코히런트 위상 간섭' 인가
        #     (경로수·에너지 변동으로는 설명 안 되는가) — append 가 채운다.
        coherent_phase_dominates=((J.get("alternative_explanations") or {})
                                  .get("by_arm", {}).get("full_mini2/all", {})
                                  .get("coherent_phase_dominates")),
        null_projected_area_ptp_db_max=(max(null_shape_invariant.values())
                                        if null_shape_invariant else None),
        per_airframe_margin_db={k: v.get("margin_rescaled_db") for k, v in per.items()},
        gate_pass=bool(cmp_ and not nulls_bad
                       and bool(sigs) and all(v["modulation_above_noise"] for v in sigs.values())
                       and bool(pos) and all(v["modulation_above_noise"] for v in pos.values())),
        note_ko=("gate_pass = (모든 신호팔 유의) ∧ (양성대조 전부 켜짐) ∧ (널 **전부** 조용). "
                 "v1 대비 강화점: 널이 7개(텀블 포함)로 늘었고, 바닥을 신호팔 잡음으로 "
                 "정규화했으며, 해상도를 사다리로 재고 곡선상관까지 봤고, matrice4e 에 "
                 "자기 신호팔을 붙여 기체별 여유를 따로 냈다."))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=32)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--repeat", type=int, default=32)
    ap.add_argument("--spp", type=int, default=256_000_000)
    ap.add_argument("--hot", default=("full_mini2,norotor_mini2,disc_mini2,"
                                      "sphere_mini2_carbon,sphere_mini2_plastic_tumble"))
    ap.add_argument("--compare-to", default=os.path.join(
        ROOT, "outputs", "report15_null_control_run1.json"))
    ap.add_argument("--out", default=OUT_JSON, help="⛔ 기본값 외 경로는 스모크용")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    if a.quick:
        a.steps, a.seeds, a.repeat, a.spp, a.hot = 4, 2, 4, 4_000_000, ""
    out_json = a.out

    os.makedirs(N.SCRATCH, exist_ok=True)
    period = 360.0 / int(DRONES["mini2"].prop_blades)
    phis = list(np.linspace(0.0, period, int(a.steps), endpoint=False))
    seeds = tuple(range(1, a.seeds + 1))

    probe, hot_aspect = {}, None
    if os.path.exists(PROBE_JSON):
        with open(PROBE_JSON) as f:
            probe = json.load(f)
        hot_aspect = ((probe.get("airframes", {}).get("mini2", {})
                       .get("S_aspect") or {}).get("hot_aspect"))

    t0 = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_null_control_v2.py",
        supersedes="benchmark/report15_null_control.py (v1 — outputs/report15_null_control_run1.json)",
        question=("변조가 나오면 안 되는 물체에서도 변조가 나오는가 — "
                  "① 등가부피 구 회전(z·x텀블, mini2·matrice4e) ② 기체 전체 회전(양성) "
                  "③ 로터 제거 ④ 삼각형 사다리(100/50/25/12.5%)"),
        observable="h = Σ_p a_p·exp(−j2πf_c·τ_p)  (report15_probe.rt_echo 를 그대로 import)",
        measurement_code="report15_probe.{rt_echo, spread, judge, place, id_to_group}",
        fc_hz=FC, lambda_m=LAM, az_deg=AZ_DEG, el_deg=EL_DEG, range_m=RANGE_M,
        baseline_m=P.BASELINE_M, max_paths=P.MAX_PATHS, max_depth=1,
        n_phase_steps=int(a.steps), phase_period_deg=float(period),
        phases_deg=[float(x) for x in phis],
        sweep_seeds=int(a.seeds), n_repeat_noise=int(a.repeat), spp=int(a.spp),
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        materials="production per-group (DRONE_GROUP_MAT); 구는 단일재질",
        related=dict(probe="outputs/report15_probe.json", facet="outputs/facet_count.json",
                     v1="outputs/report15_null_control_run1.json"),
        v2_additions=dict(
            a_normalized_floor=("널의 재추적 σ 가 신호팔보다 3배 조용하다는 반론 → 바닥을 "
                                "σ_signal/σ_null 로 환산해 보수적으로 다시 잡는다."),
            b_tumble_null=("uv 구의 z 회전은 띠를 자기 위로 미끄러뜨릴 뿐이다 → **x축 텀블**로 "
                           "극점을 조명면에 끌고 와 삼각형 배치를 최대로 흔든다. 구는 어떤 "
                           "회전에도 불변이므로 물리적 변조는 여전히 0 이어야 한다."),
            c_resolution_ladder=("④ 를 점 하나가 아니라 100/50/25/12.5% 사다리로 재고, ptp "
                                 "뿐 아니라 **h(φ) 곡선 상관**까지 본다."),
            d_matrice4e_signal=("matrice4e 바닥에 분모가 없었다 → 그 기체의 로터 위상 스텝 "
                                "신호팔을 붙여 기체별 여유를 따로 낸다."),
            e_facet_churn=("조명면 투영면적 Σ A·(n̂·û) 이 위상 무관임을 재서 '널이 정말 같은 "
                           "물체였다' 를 주장이 아니라 수치로 남긴다.")),
        null_design=dict(
            norotor="메쉬 완전 동결 — 파이프라인 결정성만 잰다(0 이 아니면 그 뒤가 무의미).",
            disc="꼭짓점은 블레이드 팁만큼 움직이는데 면은 같은 평면 — OBJ 장부 churn 검사.",
            sphere_spin="형상 불변 + 법선 방위 회전.",
            sphere_tumble="형상 불변 + **극점이 조명면을 횡단** = 삼각형 배치 최대 교란.",
            why_all=("각 널이 서로 다른 고장모드를 막는다 — 하나로는 반론이 하나씩 남는다.")),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), arms={})

    def _save():
        with open(out_json, "w") as f:
            json.dump(J, f, ensure_ascii=False, indent=1)

    print(f"\n══ 널 대조 v2 — 위상 {a.steps} 스텝 × 시드 {a.seeds} × spp {a.spp:,} "
          f"@ az={AZ_DEG}° el={EL_DEG}° R={RANGE_M} m ══", flush=True)

    print("  self-check: 분절 재현 == drones.pose_articulated ?", flush=True)
    J["self_check"] = N.self_check(phis)
    for k, v in J["self_check"].items():
        if isinstance(v, dict):
            print(f"    {k}: all_match={v['all_match']}", flush=True)

    arms, geo = build_arms_v2()
    J["geometry"] = geo
    J["judge_null_reference"] = N.expected_null_range(int(a.steps))
    r_ = J["judge_null_reference"]
    print(f"  판정함수 기준선: 순수잡음 {a.steps} 위상 ptp 기대값 = "
          f"{r_['expected_range_over_se']:.2f}·SE (검정① 문턱 3 → "
          f"{'관대' if r_['test1_is_liberal'] else '보수적'})", flush=True)
    ff = geo["matrice4e"]["farfield"]
    print(f"  matrice4e 원거리장: 2D²/λ = {ff['farfield_2D2_over_lambda_m']:.3f} m "
          f"(D={ff['max_span_m']:.3f} m) vs R={ff['range_m']} m → "
          f"far-field={ff['in_farfield']}", flush=True)

    print("  정반사 탐침 (구 vs 평판, 3 재질) …", flush=True)
    J["specular_probe"] = N.specular_probe(geo["mini2"]["mesh"]["r_equal_volume_m"],
                                           geo["mini2"]["mesh"]["n_tris"], a.spp)
    sp_ = J["specular_probe"]
    print(f"    → 정반사 탐색기 살아있음={sp_['specular_solver_alive']}  "
          f"구의 정반사 경로 총합={sp_['sphere_specular_paths_total']}  "
          f"금속 구 경로 0={sp_['metal_sphere_empty']}", flush=True)

    #  ⭐ 메쉬 갈림(CPU) — 널이 '같은 물체' 였다는 수치 증거. GPU 안 쓴다.
    print("  facet churn (조명면 투영면적 불변성) …", flush=True)
    by_key = {x.key: x for x in arms}
    churn_keys = ["full_mini2", "disc_mini2", "sphere_mini2_plastic",
                  "sphere_mini2_plastic_tumble", "sphere_matrice4e_plastic_tumble",
                  "yaw_mini2"]
    J["facet_churn"] = {}
    for k in churn_keys:
        if k not in by_key:
            continue
        J["facet_churn"][k] = facet_churn(by_key[k].mesh_at, phis)
        c = J["facet_churn"][k]
        print(f"    {k:32s} 투영면적 {c['projected_area_mean_m2']*1e4:8.3f} cm²  "
              f"ptp {c['projected_area_ptp_db']:7.4f} dB   조명면 삼각형 "
              f"{c['n_lit_mean']:8.1f}±{c['n_lit_ptp']:.0f}   무게중심이동 "
              f"{(c['lit_centroid_shift_median_lambda_max'] or 0):.4f}λ", flush=True)
    _save()
    print(f"  팔 {len(arms)}개: " + ", ".join(x.key for x in arms), flush=True)

    for arm in arms:
        print(f"\n── {arm.key} — {arm.label_ko} "
              f"[{'변조 나와야 정상' if arm.expect else '변조 나오면 산물'}]", flush=True)
        J["arms"][arm.key] = run_arm(arm, phis, seeds, a.spp, a.repeat, AZ_DEG, EL_DEG)
        _save()

    hot_keys = [x.strip() for x in a.hot.split(",") if x.strip()]
    if hot_keys and hot_aspect:
        az_h, el_h = float(hot_aspect["az_deg"]), float(hot_aspect["el_deg"])
        J["meta"]["hot_aspect"] = dict(az_deg=az_h, el_deg=el_h,
                                       source="report15_probe.mini2.S_aspect.hot_aspect")
        J["arms_hot"] = {}
        for k in hot_keys:
            if k not in by_key:
                continue
            print(f"\n── [hot az={az_h}° el={el_h}°] {k}", flush=True)
            J["arms_hot"][k] = run_arm(by_key[k], phis, seeds, a.spp, a.repeat, az_h, el_h)
            _save()

    #  ── 분석 ──────────────────────────────────────────────────────────────── #
    J["comparison"] = N.compare(J["arms"])
    J["floor_normalized"] = normalized_floor(J["arms"], "full_mini2")
    J["resolution_ladder"] = resolution_ladder(J["arms"])
    J["by_airframe"] = by_airframe(J["arms"])
    J["tumble_vs_spin"] = tumble_vs_spin(J["arms"])
    J["curve_pairs"] = {f"{a_}|{b_}": curve_pair(J["arms"], a_, b_, channel=ch_)
                        for a_, b_, ch_ in (
                            ("full_mini2", "half_mini2", "all"),
                            ("full_mini2", "half_mini2", "prop"),
                            ("full_mini2", "red750_mini2", "all"),
                            ("full_mini2", "red875_mini2", "all"),
                            ("full_mini2", "yaw_mini2", "all"),
                            ("full_mini2", "disc_mini2", "all"),
                            ("full_mini2", "full_matrice4e", "all"))}
    J["verdict_v1_style"] = N.overall_verdict(J["comparison"], J["arms"])
    J["verdict"] = overall_verdict_v2(J)
    if J.get("arms_hot"):
        J["comparison_hot"] = N.compare(J["arms_hot"])
    if probe:
        J["probe_reference"] = {k: v.get("headline")
                                for k, v in probe.get("airframes", {}).items()}
        J["probe_reference"]["blockers_source"] = "outputs/report15_probe.json"
    if a.compare_to and os.path.exists(a.compare_to):
        J["reproducibility"] = N.reproducibility(J, a.compare_to)
        r = J["reproducibility"]
        print(f"\n  v1 재현성: 팔 {r['n_arms_compared']}개 대조, 최대 |Δ| = "
              f"{r['max_abs_delta_any']:.3e}, 판정 전부 동일 = "
              f"{r['all_verdicts_identical']}", flush=True)
    J["meta"]["seconds_total"] = float(time.time() - t0)
    _save()

    v = J["verdict"]

    def _n(x, fmt="%.4f"):
        return (fmt % x) if isinstance(x, (int, float)) else "n/a"

    print("\n" + "═" * 78)
    print(f"  신호팔 전부 유의 = {v['all_signals_significant']}   "
          f"양성대조 켜짐 = {v['positive_controls_fired']}   "
          f"널 {v['n_null_arms']}개 전부 조용 = {v['nulls_clean']}")
    print(f"  산물 바닥(원값) = {_n(v['artifact_floor_raw_db'])} dB   "
          f"(잡음정규화) = {_n(v['artifact_floor_rescaled_db'])} dB   "
          f"기준신호 = {_n(v['signal_ptp_db'])} dB   여유 = {_n(v['margin_rescaled_db'])} dB")
    print(f"  해상도 사다리: ptp 최대 상대변화 = "
          f"{(v['resolution_ptp_max_rel_change'] or 0)*100:.2f}%   "
          f"곡선 상관 최소 r = {v['resolution_min_pearson_r']}")
    print(f"  텀블 널이 울렸나 = {v['tumble_any_signalled']}   "
          f"널 투영면적 최대 ptp = {(v['null_projected_area_ptp_db_max'] or 0):.2e} dB")
    print(f"  기체별 여유 = {v['per_airframe_margin_db']}")
    print(f"  ⇒ gate_pass = {v['gate_pass']}")
    if v.get("nulls_that_signalled"):
        print(f"  ⚠ 변조를 낸 널: {v['nulls_that_signalled']}")
    print(f"\n✅ 저장 → {out_json}   ({J['meta']['seconds_total']:.0f}s)")
    return J


if __name__ == "__main__":
    main()
