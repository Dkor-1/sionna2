# -*- coding: utf-8 -*-
"""
report15_null_control_v2_append.py — v2 에 **자기반증 1건 + 그 반증이 부른 팔**을 덧댄다
================================================================================

⚠⚠ **내 주장이 틀렸다 — 기록으로 남긴다.**
v2 는 x축 텀블 널을 세우며 이렇게 주장했다:

    "uv 구의 극점(삼각형이 잘게 뭉친 특이점)이 **조명면을 가로질러 쓸고 지나가**
     레이더가 보는 삼각형 배치가 매 위상마다 통째로 바뀐다."

이것은 **거짓이다**. 시선은 u = (cos15°, 0, sin15°) 로 **y 성분이 0** 이다. x축 회전은
어떤 벡터의 x 성분도 바꾸지 않으므로 ±z 극점은 y–z 평면에 갇혀 **항상 시선에서 75~105°**,
즉 가장자리에만 머문다(실측 최소각 75.00°). 극점을 보어사이트로 통과시키려면 u 에 수직인
**y 축**으로 굴려야 한다(실측 최소각 1.87°).

그래서 두 가지를 한다:
  1) `sphere_*_ytumble` — 극점이 실제로 보어사이트를 통과하는 널을 추가한다.
  2) `tessellation_symmetry` — 세 축의 교란 정도를 **재서** 남긴다. 여기서 두 번째 사실이
     나온다: **uv 구는 어떤 축으로 굴려도 '조명면 삼각형 크기 분포' 가 바뀌지 않는다**
     (가시 반구가 언제나 전 위도대를 포함하므로). 즉 구 널이 흔드는 것은 '면의 크기 구성'이
     아니라 '어느 삼각형이 켜지는가' 다. 이 한계를 감추지 않고 적는다 —
     ⭐ 그래서 v2 의 최종 근거는 구 널이 아니라 **disc 널**이 지탱한다:
        disc 는 드론과 **삼각형 수·재질·꼭짓점 변위(1.3888λ)가 전부 같은데** 변조가 0 이다.

⛔ src/drones.py · src/drone_cad.py 읽기만. ⛔ 숫자 손입력 금지.
출력은 v2 와 같은 outputs/report15_null_control.json 에 **병합**한다.
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

import report15_null_control_v2 as V2                                    # noqa: E402
import report15_null_control as N                                        # noqa: E402
import report15_probe as P                                               # noqa: E402
from report15_null_control import Arm, run_arm, sphere_matched           # noqa: E402
from report15_probe import AZ_DEG, EL_DEG, LAM                           # noqa: E402
from drones import DRONES                                                # noqa: E402
from geom import uv_sphere                                               # noqa: E402
from scipy.spatial import cKDTree                                        # noqa: E402

OUT_JSON = N.OUT_JSON


def _rot(ax: str, deg: float) -> np.ndarray:
    t = math.radians(float(deg)); c, s = math.cos(t), math.sin(t)
    return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])}[ax]


def tessellation_symmetry(radius: float, seg: int, rings: int, phis,
                          az=AZ_DEG, el=EL_DEG) -> dict:
    """⭐ 세 회전축이 **테셀레이션을 얼마나 다르게 흔드는가** — 전부 계산해서 담는다.

    · z 회전은 uv 구 테셀레이션의 **대칭**이다(φ = 360/seg 의 배수에서 메쉬가 자기 자신).
      → z 널이 탐색하는 '삼각형 상태' 는 폭 360/seg 짜리 아주 좁은 주기 안에 갇힌다.
    · x·y 회전은 그런 주기가 없다 → 180° 내내 서로 다른 삼각형 집합.
    · 그러나 **어느 축이든 조명면 삼각형의 크기 분포는 바뀌지 않는다**
      (가시 반구가 언제나 전 위도대를 포함하므로). 이 한계를 명시적으로 잰다.
    """
    u = P.look_dir(az, el)
    m = uv_sphere(radius, seg=int(seg), rings=int(rings), group="sph")
    V = np.asarray(m.v, float); F = np.asarray(m.f, int)
    t0 = cKDTree(V)
    period_z = 360.0 / int(seg)
    half_facet_arc = radius * math.radians(period_z / 2.0)
    out = dict(radius_m=float(radius), seg=int(seg), rings=int(rings),
               n_tris=int(F.shape[0]),
               z_tessellation_period_deg=float(period_z),
               half_facet_arc_m=float(half_facet_arc),
               half_facet_arc_lambda=float(half_facet_arc / LAM),
               phase_step_deg=float(phis[1] - phis[0]) if len(phis) > 1 else None,
               by_axis={})
    for ax in ("z", "x", "y"):
        amax, q90, nlit, pol, srf, vtx = [], [], [], [], [], []
        for p in phis:
            Rm = _rot(ax, p); Vr = V @ Rm.T
            pole = Rm @ np.array([0.0, 0.0, 1.0])
            pol.append(math.degrees(math.acos(abs(float(np.clip(pole @ u, -1, 1))))))
            p0, p1, p2 = Vr[F[:, 0]], Vr[F[:, 1]], Vr[F[:, 2]]
            cr = np.cross(p1 - p0, p2 - p0)
            lit = (cr @ u) > 0
            A = np.linalg.norm(cr[lit], axis=1) / 2.0 / LAM ** 2
            amax.append(float(A.max())); q90.append(float(np.quantile(A, 0.90)))
            nlit.append(int(lit.sum()))
            srf.append(float(max(t0.query(Vr)[0].max(), cKDTree(Vr).query(V)[0].max())))
            vtx.append(float(np.linalg.norm(Vr - V, axis=1).max()))
        amax = np.array(amax); q90 = np.array(q90); nl = np.array(nlit, float)
        out["by_axis"][ax] = dict(
            pole_min_angle_to_boresight_deg=float(min(pol)),
            pole_crosses_boresight=bool(min(pol) < 5.0),
            lit_facet_count_mean=float(nl.mean()), lit_facet_count_ptp=float(nl.max() - nl.min()),
            lit_max_facet_area_lambda2_mean=float(amax.mean()),
            lit_max_facet_area_rel_ptp=float((amax.max() - amax.min()) / amax.mean()),
            lit_q90_facet_area_rel_ptp=float((q90.max() - q90.min()) / q90.mean()),
            surface_shift_max_lambda=float(max(srf) / LAM),
            surface_shift_over_half_facet=float(max(srf) / half_facet_arc),
            vertex_shift_max_lambda=float(max(vtx) / LAM),
            is_tessellation_symmetry=bool(ax == "z"))
    z, x, y = (out["by_axis"][k] for k in ("z", "x", "y"))
    out["falsified_claim"] = dict(
        claim=("v2 초안: 'x축 텀블은 uv 구의 극점을 조명면을 가로질러 쓸고 지나가게 한다'"),
        status="FALSE",
        why=("시선 u=(cos15°,0,sin15°) 는 y 성분이 0 이고 x 회전은 x 성분을 보존하므로 "
             "±z 극점은 y–z 평면에 갇힌다 — 시선에서 최소 "
             f"{x['pole_min_angle_to_boresight_deg']:.2f}° 까지밖에 못 온다."),
        corrected=("극점을 보어사이트로 통과시키는 축은 **y** 다 — 실측 최소각 "
                   f"{y['pole_min_angle_to_boresight_deg']:.2f}°."))
    out["second_finding"] = dict(
        statement=("⚠ uv 구는 **어느 축으로 굴려도 조명면 삼각형의 크기 분포가 바뀌지 않는다** "
                   "— 가시 반구가 언제나 전 위도대를 포함하기 때문이다."),
        evidence=dict(lit_max_facet_area_rel_ptp={k: out["by_axis"][k]["lit_max_facet_area_rel_ptp"]
                                                  for k in ("z", "x", "y")},
                      lit_q90_facet_area_rel_ptp={k: out["by_axis"][k]["lit_q90_facet_area_rel_ptp"]
                                                  for k in ("z", "x", "y")}),
        consequence=("따라서 구 널이 흔드는 것은 '면 크기 구성'이 아니라 '어느 삼각형이 켜지는가' "
                     "뿐이다(조명면 삼각형수 ptp: "
                     f"z={z['lit_facet_count_ptp']:.0f}, x={x['lit_facet_count_ptp']:.0f}, "
                     f"y={y['lit_facet_count_ptp']:.0f}). ⭐ 그래서 최종 근거는 구 널이 아니라 "
                     "**disc 널**이 지탱한다 — disc 는 드론과 삼각형 수·재질·꼭짓점 변위가 "
                     "전부 같은데도 변조가 0 이다."))
    out["z_is_weak_null"] = dict(
        reason=("z 회전은 uv 테셀레이션의 대칭이라 φ 가 360/seg 의 배수면 메쉬가 자기 자신이 된다. "
                "따라서 z 널이 탐색하는 삼각형 상태는 폭 "
                f"{period_z:.4f}° 의 좁은 주기 안에 갇히고, 표면변위가 반쪽면 호길이"
                f"({out['half_facet_arc_lambda']:.5f}λ)를 넘지 못한다 — 실측 "
                f"{z['surface_shift_max_lambda']:.5f}λ (= 반쪽면의 "
                f"{z['surface_shift_over_half_facet']:.2f}배)."),
        x_and_y_have_no_such_period=True)
    return out


def alternative_explanations(arms_out: dict) -> dict:
    """⭐ 널이 조용한 것과 **별개로**, 신호팔의 변조가 '물리' 인지 '세는 방식' 인지 가른다.

    널 대조는 "산물이 아니다" 까지만 말해 준다. 그 다음 질문은 "그럼 무엇인가" 다.
    이미 저장된 스윕 자료만으로(추가 GPU 0) 두 대안설명을 검사한다:

      (i)  **경로 수 변동설** — 위상마다 발견되는 경로 수가 달라져서 합이 커졌다 작아졌다 한다.
           랜덤 위상 코히런트 합이라면 |h| ∝ √N 이므로 경로수 ptp 가 예측하는 dB 를 계산해
           실제 ptp 와 비교한다.
      (ii) **에너지 변동설** — 위상무관 에너지 Σ|a_p|² 자체가 흔들린다.
           그렇다면 incoh_db 의 ptp 가 |h| 의 ptp 만큼 커야 한다.

    둘 다 실제 ptp 를 설명 못 하면 남는 것은 **코히런트 위상 간섭**뿐이다 — 블레이드가
    움직여 경로장이 바뀌는 것, 즉 마이크로도플러의 물리적 기작 그 자체다."""
    out = {}
    for k, v in arms_out.items():
        h = v["headline"]
        if h["role"] not in ("signal", "positive", "resolution"):
            continue
        for ch in ("all", "prop"):
            rows = v["sweep"]["by_mode"]["prod"]

            def sub(sp):
                return sp["prop"] if ch == "prop" else sp
            try:
                amp = np.array([sub(r["spread"])["amp_db_mean"] for r in rows], float)
                inc = np.array([sub(r["spread"])["incoh_db_mean"] for r in rows], float)
                npa = np.array([sub(r["spread"])["n_paths_mean"] for r in rows], float)
            except (TypeError, KeyError):
                continue
            if not (np.isfinite(amp).all() and np.isfinite(inc).all()) or npa.min() <= 0:
                continue

            def _r(x, y):
                x = x - x.mean(); y = y - y.mean()
                den = float(np.linalg.norm(x) * np.linalg.norm(y))
                return float(x @ y / den) if den > 1e-30 else None
            ptp = float(amp.max() - amp.min())
            sqrtn = float(20.0 * math.log10(math.sqrt(npa.max()) / math.sqrt(npa.min())))
            incp = float(inc.max() - inc.min())
            out[f"{k}/{ch}"] = dict(
                modulation_ptp_db=ptp,
                pathcount_ptp_frac=float((npa.max() - npa.min()) / npa.mean()),
                sqrtN_predicted_ptp_db=sqrtn,
                incoherent_energy_ptp_db=incp,
                excess_over_sqrtN=float(ptp / sqrtn) if sqrtn > 1e-9 else None,
                excess_over_incoherent=float(ptp / incp) if incp > 1e-9 else None,
                r_amp_vs_pathcount=_r(amp, npa), r_amp_vs_incoherent=_r(amp, inc),
                coherent_phase_dominates=bool(ptp > 3.0 * max(sqrtn, incp)))
    return dict(by_arm=out,
                note_ko=("|h| 의 ptp 가 √N 예측과 위상무관 에너지 ptp 를 **둘 다** 크게 넘으면, "
                         "변조는 '경로를 더 찾아서' 도 '에너지가 커져서' 도 아니고 "
                         "**코히런트 위상 간섭** 이다 — 블레이드 변위가 경로장을 바꾼 것."))


def build_ytumble_arms(geo: dict) -> list:
    """극점이 보어사이트를 통과하는 y축 텀블 널 (mini2 · matrice4e 등가부피 구)."""
    arms = []
    note = ("⭐ y축 회전 — 시선 u 에 수직인 축이라 uv 구의 극점(삼각형이 잘게 뭉친 특이점)이 "
            "실제로 **보어사이트를 통과**한다(최소각 1.87°). x축 텀블은 이것을 하지 못한다"
            "(최소각 75°) — v2 초안의 주장이 틀렸고 여기서 정정한다. 구는 어떤 회전에도 "
            "불변이므로 물리적 변조는 여전히 정확히 0 이어야 한다.")
    for tag, mats in (("mini2", ("plastic", "carbon")), ("matrice4e", ("plastic",))):
        g = geo.get(tag) or {}
        if "mesh" not in g:
            continue
        sph, si = sphere_matched(g["mesh"]["r_equal_volume_m"], g["mesh"]["n_tris"])
        for mat in mats:
            arms.append(Arm(f"sphere_{tag}_{mat}_ytumble",
                            f"{tag} 등가부피 구({mat}) · **y축 텀블**(극점이 보어사이트 통과)",
                            "null", False,
                            lambda phi, m=sph: m.rotated("y", float(phi)),
                            {"sph": mat}, {"sph": (0.7, 0.7, 0.7)},
                            extra=dict(si, material=mat, rotation_axis="y", note_ko=note)))
    return arms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=32)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--repeat", type=int, default=32)
    ap.add_argument("--spp", type=int, default=256_000_000)
    ap.add_argument("--json", default=OUT_JSON)
    a = ap.parse_args()

    with open(a.json) as f:
        J = json.load(f)
    period = 360.0 / int(DRONES["mini2"].prop_blades)
    phis = list(np.linspace(0.0, period, int(a.steps), endpoint=False))
    seeds = tuple(range(1, a.seeds + 1))
    t0 = time.time()

    #  ── ⚠ 자기반증 + 축별 교란 계량 (CPU) ─────────────────────────────────── #
    si = J["geometry"]["mini2"]["sphere"]
    J["tessellation_symmetry"] = tessellation_symmetry(
        si["radius_m"], si["seg"], si["rings"], phis)
    ts = J["tessellation_symmetry"]
    print("\n⚠ 자기반증:", ts["falsified_claim"]["status"], "—", ts["falsified_claim"]["why"],
          flush=True)
    for ax, r in ts["by_axis"].items():
        print(f"  축 {ax}: 극점-보어사이트 최소각 {r['pole_min_angle_to_boresight_deg']:6.2f}°  "
              f"조명면 삼각형수 ptp {r['lit_facet_count_ptp']:5.0f}  "
              f"면적분포 상대ptp {r['lit_max_facet_area_rel_ptp']:.2e}  "
              f"표면변위 {r['surface_shift_max_lambda']:.5f}λ", flush=True)

    #  ⭐ v2 meta 의 틀린 주장을 **정정**해 둔다 (JSON 이 거짓을 들고 다니지 않게)
    J["meta"].setdefault("corrections", {})["b_tumble_null"] = dict(
        original=J["meta"].get("v2_additions", {}).get("b_tumble_null"),
        corrected=ts["falsified_claim"]["corrected"],
        detail="tessellation_symmetry.falsified_claim 참조")
    if "v2_additions" in J["meta"]:
        J["meta"]["v2_additions"]["b_tumble_null"] = (
            "구를 z 가 아닌 축으로 굴려 테셀레이션 상태를 주기 밖으로 끌어낸다. "
            "⚠ 초안의 '극점이 조명면을 횡단' 주장은 x축에 대해 거짓이었고 y축으로 정정했다 "
            "— tessellation_symmetry.falsified_claim 참조.")

    #  ── y 텀블 팔 실행 ───────────────────────────────────────────────────── #
    arms = build_ytumble_arms(J["geometry"])
    print(f"\n  추가 팔 {len(arms)}개: " + ", ".join(x.key for x in arms), flush=True)
    for arm in arms:
        print(f"\n── {arm.key} — {arm.label_ko} [변조 나오면 산물]", flush=True)
        J["arms"][arm.key] = run_arm(arm, phis, seeds, a.spp, a.repeat, AZ_DEG, EL_DEG)
        with open(a.json, "w") as f:
            json.dump(J, f, ensure_ascii=False, indent=1)

    #  ── 병합된 팔 집합으로 분석 전부 재계산 ───────────────────────────────── #
    J["facet_churn"].update({
        k: V2.facet_churn(next(x for x in arms if x.key == k).mesh_at, phis)
        for k in [x.key for x in arms if x.key.endswith("plastic_ytumble")]})
    J["comparison"] = N.compare(J["arms"])
    J["floor_normalized"] = V2.normalized_floor(J["arms"], "full_mini2")
    J["resolution_ladder"] = V2.resolution_ladder(J["arms"])
    J["by_airframe"] = V2.by_airframe(J["arms"])
    J["tumble_vs_spin"] = V2.tumble_vs_spin(J["arms"])
    J["alternative_explanations"] = alternative_explanations(J["arms"])
    ae = (J["alternative_explanations"]["by_arm"] or {}).get("full_mini2/all")
    if ae:
        print(f"\n  대안설명 검사 [full_mini2/all]: |h| ptp={ae['modulation_ptp_db']:.3f} dB  vs "
              f"√N 예측 {ae['sqrtN_predicted_ptp_db']:.3f} dB (×{ae['excess_over_sqrtN']:.1f})  vs "
              f"위상무관 에너지 {ae['incoherent_energy_ptp_db']:.3f} dB "
              f"(×{ae['excess_over_incoherent']:.1f}) → 코히런트 위상 지배="
              f"{ae['coherent_phase_dominates']}", flush=True)
    J["verdict_v1_style"] = N.overall_verdict(J["comparison"], J["arms"])
    J["verdict"] = V2.overall_verdict_v2(J)
    J["meta"]["seconds_append"] = float(time.time() - t0)
    J["meta"]["script"] = ("benchmark/report15_null_control_v2.py "
                           "+ benchmark/report15_null_control_v2_append.py")
    with open(a.json, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)

    v = J["verdict"]
    print("\n" + "═" * 78)
    print(f"  널 {v['n_null_arms']}개 전부 조용 = {v['nulls_clean']}   "
          f"신호팔 전부 유의 = {v['all_signals_significant']}   "
          f"양성대조 = {v['positive_controls_fired']}")
    print(f"  산물 바닥(잡음정규화) = {v['artifact_floor_rescaled_db']:.4f} dB   "
          f"기준신호 = {v['signal_ptp_db']:.4f} dB   여유 = {v['margin_rescaled_db']:.4f} dB")
    print(f"  ⇒ gate_pass = {v['gate_pass']}   ({J['meta']['seconds_append']:.0f}s)")
    return J


if __name__ == "__main__":
    main()
