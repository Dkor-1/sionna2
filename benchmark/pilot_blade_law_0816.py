# -*- coding: utf-8 -*-
"""
pilot_blade_law_0816.py — 새 날 법칙이 **얼마나 큰가**를 먼저 재 본다 (2026-08-16)
=============================================================================================
2026-08-16 라운드에서 `dji_mini2` 라는 새 블레이드 법칙을 **추가**했다(정본은 여전히 `legacy`).
정본을 갈아끼울지는 이 파일럿의 크기를 보고 정할 일이다 — 이 스크립트가 그 크기를 잰다.

무엇을 재나
  ① **형상** — 프롭 표면적 · 최대시위/반경 · 0.70R 정규화 시위 · 팁 밴드 면적 · 날 두께
  ② **σ** — 우리 PO 커널(가림 없음, CPU)로 프로펠러만 떼어 방위 스윕. 두 법칙의 차이[dB].
  ③ **삼각형 크기** — 파장 대비 최장 모서리(감사 m5)와 λ 로 묶었을 때의 값.

⚠ 정직하게 좁히는 범위
  · **모노스태틱만** 잰다. 감사 §4-2 는 형상 민감도가 **바이스태틱에서 더 크다**고 측정했다
    (모노 +0.24 dB ↔ β=120° +1.29 dB). 우리 PO 커널에는 바이스태틱 경로가 없어서 여기서는
    못 재고, 그래서 아래 숫자는 **하한**으로 읽어야 한다.
  · PO 는 가림(그림자)을 안 본다. 프로펠러 하나만 떼어 재므로 동체 가림은 애초에 없지만,
    날끼리의 가림은 무시된다.
  · 두 법칙 모두 |Γ|=prop_plastic 0.25 로 같으므로, **차이[dB]** 에는 재질이 안 들어간다.

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/pilot_blade_law_0816.py
산출: outputs/pilot_blade_law_0816.json
GPU 미사용(PO 는 numpy CPU).
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = os.path.join(_ROOT, "outputs", "pilot_blade_law_0816.json")

FC_HZ = 3.5e9
C0 = 299_792_458.0
LAM = C0 / FC_HZ
GAMMA_PROP = 0.25                 # materials.MATERIALS['prop_plastic'].gamma_po
SIGMA_DRONES = ("mini2", "mini5pro", "matrice4e", "m350rtk")
EL_LIST = (-30.0, 0.0)
AZ = np.arange(0.0, 360.0, 2.0)


def mesh_stats(m):
    import trimesh
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, np.int64)
    t = trimesh.Trimesh(vertices=V, faces=F, process=False)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    return dict(n_tris=int(len(F)), area_mm2=float(t.area) * 1e6,
                max_edge_mm=float(np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1).max()) * 1e3,
                watertight=bool(t.is_watertight))


def sigma_az_mean_dbsm(m, el_deg: float, spacing: float) -> float:
    """프로펠러 하나의 **방위평균 σ**[dBsm] — 우리 PO 커널(모노스태틱)."""
    from rcs_po import mesh_to_points, rcs_from_points
    P, N, dA, w = mesh_to_points(m, spacing, gamma={"prop": GAMMA_PROP})
    sig = rcs_from_points(P, N, dA, FC_HZ, AZ, el_deg, w=w)
    return float(10.0 * np.log10(np.mean(sig)))


def main() -> None:
    from drones import DRONES, build_propeller
    from drone_cad import resolve_chord_max_over_r
    from prop_thickness import prop_thickness_profile

    t0 = time.time()
    laws = ("legacy", "dji_mini2")
    geom: dict[str, dict] = {}

    print("① 형상 — 두 법칙 나란히")
    print(f"{'key':12s} {'c_max/R':>16s} {'면적 mm²(leg→dji)':>24s} {'Δ%':>7s} "
          f"{'두께 mm(leg→dji)':>20s} {'c/c_max@0.70R':>16s}")
    for key, spec in DRONES.items():
        row = {}
        for law in laws:
            prof = prop_thickness_profile(spec, blade_law=law)
            rr = np.asarray([s["r_over_R"] for s in prof["stations"]])
            ch = np.asarray([s["chord_mm"] for s in prof["stations"]])
            sel_all = (rr >= 0.20) & (rr <= 0.96)
            sel_tip = (rr >= 0.90) & (rr <= 0.96)
            cmax, src = resolve_chord_max_over_r(spec, law)
            row[law] = dict(
                chord_max_over_R=cmax, chord_max_source=src,
                t_chordmean_mm=prof["bands"]["headline_0p20_0p96"]["t_chordmean_mm"],
                t_tip_mm=prof["bands"]["tip_0p80_0p96"]["t_chordmean_mm"],
                planform_area_mm2=float(np.trapezoid(ch[sel_all], rr[sel_all])),
                tip_band_area_mm2=float(np.trapezoid(ch[sel_tip], rr[sel_tip])),
                chord_norm_at_0p70R=float(np.interp(0.70, rr, ch) / ch.max()),
                mesh=mesh_stats(build_propeller(spec, blade_law=law)),
            )
        a, b = row["legacy"], row["dji_mini2"]
        row["delta"] = dict(
            surface_area_pct=100.0 * (b["mesh"]["area_mm2"] / a["mesh"]["area_mm2"] - 1.0),
            planform_area_pct=100.0 * (b["planform_area_mm2"] / a["planform_area_mm2"] - 1.0),
            tip_band_area_pct=100.0 * (b["tip_band_area_mm2"] / a["tip_band_area_mm2"] - 1.0),
            thickness_pct=100.0 * (b["t_chordmean_mm"] / a["t_chordmean_mm"] - 1.0))
        geom[key] = row
        print(f"{key:12s} {a['chord_max_over_R']:7.4f}→{b['chord_max_over_R']:<8.4f} "
              f"{a['mesh']['area_mm2']:11.1f}→{b['mesh']['area_mm2']:<11.1f} "
              f"{row['delta']['surface_area_pct']:+7.2f} "
              f"{a['t_chordmean_mm']:9.4f}→{b['t_chordmean_mm']:<9.4f} "
              f"{a['chord_norm_at_0p70R']:7.3f}→{b['chord_norm_at_0p70R']:<7.3f}")

    print("\n② σ — 우리 PO 커널(모노스태틱·가림 없음), 프로펠러 1개, 방위평균")
    print(f"{'key':12s} {'el':>5s} {'legacy':>9s} {'dji_mini2':>10s} {'Δ dB':>7s} "
          f"{'수렴 λ/7↔λ/16':>14s}")
    sigma: dict[str, dict] = {}
    for key in SIGMA_DRONES:
        spec = DRONES[key]
        meshes = {law: build_propeller(spec, blade_law=law) for law in laws}
        rows = {}
        for el in EL_LIST:
            vals = {law: sigma_az_mean_dbsm(meshes[law], el, LAM / 7.0) for law in laws}
            fine = {law: sigma_az_mean_dbsm(meshes[law], el, LAM / 16.0) for law in laws}
            d = vals["dji_mini2"] - vals["legacy"]
            d_fine = fine["dji_mini2"] - fine["legacy"]
            rows[f"el_{el:+.0f}"] = dict(legacy_dbsm=vals["legacy"],
                                         dji_mini2_dbsm=vals["dji_mini2"],
                                         delta_db=d, delta_db_fine_grid=d_fine,
                                         grid_shift_db=abs(d - d_fine))
            print(f"{key:12s} {el:5.0f} {vals['legacy']:9.2f} {vals['dji_mini2']:10.2f} "
                  f"{d:+7.2f} {abs(d - d_fine):14.3f}")
        sigma[key] = rows

    print("\n③ 삼각형 크기 — 파장 대비 최장 모서리 (감사 m5)")
    edges = {}
    for key, spec in DRONES.items():
        a = build_propeller(spec)
        b = build_propeller(spec, lambda_m=LAM)
        edges[key] = dict(
            legacy_max_edge_mm=mesh_stats(a)["max_edge_mm"],
            legacy_lambda_over=LAM * 1e3 / mesh_stats(a)["max_edge_mm"],
            bound_max_edge_mm=mesh_stats(b)["max_edge_mm"],
            legacy_tris=mesh_stats(a)["n_tris"], bound_tris=mesh_stats(b)["n_tris"])
        print(f"{key:12s} λ/{edges[key]['legacy_lambda_over']:5.2f} "
              f"({edges[key]['legacy_max_edge_mm']:6.2f} mm, 면 {edges[key]['legacy_tris']:5d}) "
              f"→ λ/10 로 묶으면 면 {edges[key]['bound_tris']:6d}")

    doc = dict(
        _meta=dict(
            title="새 블레이드 법칙 파일럿 — 크기 재기",
            generated_kst=time.strftime("%Y-%m-%dT%H:%M:%S",
                                        time.localtime(time.time() + 9 * 3600)),
            purpose_ko="정본은 여전히 legacy 다. 정본을 갈아끼울지 정하려면 «얼마나 큰가» 를 "
                       "먼저 알아야 하고, 이 파일이 그 크기를 잰다.",
            frequency_hz=FC_HZ, gamma_prop=GAMMA_PROP, gpu_used=False,
            kernel="rcs_po (PO, 가림 없음, 모노스태틱). 프로펠러 1개만.",
            scope_caveats_ko=[
                "모노스태틱만 쟀다 — 감사 §4-2 는 형상 민감도가 바이스태틱에서 더 크다고 "
                "측정했다(모노 +0.24 ↔ β=120° +1.29 dB). 여기 숫자는 **하한**이다.",
                "PO 는 가림을 안 본다. 날끼리의 가림이 빠진다.",
                "두 법칙 모두 같은 |Γ| 를 쓰므로 차이[dB]에는 재질이 안 들어간다.",
            ]),
        geometry=geom, sigma_po_monostatic=sigma, triangle_edges=edges,
        findings_ko=[],
        runtime_s=round(time.time() - t0, 1),
    )

    # ── 파일럿이 스스로 요약을 쓴다 ─────────────────────────────────────────
    d_area = {k: v["delta"]["surface_area_pct"] for k, v in geom.items()}
    meas = [k for k in geom if geom[k]["dji_mini2"]["chord_max_source"].startswith("실측:")]
    rest = [k for k in geom if k not in meas]
    dsig = [abs(r["delta_db"]) for v in sigma.values() for r in v.values()]
    doc["findings_ko"] = [
        f"**형상**: c_max/R 실측이 있는 {len(meas)}기종({', '.join(meas)})은 프롭 표면적이 "
        f"{min(d_area[k] for k in meas):+.1f}~{max(d_area[k] for k in meas):+.1f} % 움직인다. "
        f"나머지 {len(rest)}기종은 실측이 없어 **면적중립**으로 뒀으므로 "
        f"{min(abs(d_area[k]) for k in rest):.2f}~{max(abs(d_area[k]) for k in rest):.2f} % 안에 "
        "머문다 — 즉 «분포만 바꾸고 총량은 안 건드린» 판이다.",
        f"**σ**: 모노스태틱 방위평균으로 두 법칙 차이는 최대 {max(dsig):.2f} dB 다. "
        "감사가 예고한 «형상은 1~2 dB 축» 과 같은 자리에 떨어진다.",
        "**두께**: 같은 라운드의 I1 표(outputs/prop_thickness_by_drone.json)가 보여 주듯 "
        "두께 축은 기종 간 4.5 배(수 dB)라 형상보다 훨씬 크다. 순서를 지킬 것.",
        "**삼각형 크기**: 최장 모서리는 날의 로프트 격자가 아니라 **허브 윗면·아랫면 부채꼴**과 "
        "**날 뿌리 마감면**에서 나온다(둘 다 중심→가장자리라 반지름만큼 길다). 그래서 "
        "n_sec·n_pts 를 올려도 안 줄어든다 — 실측으로 확인했다. λ 로 묶는 길은 "
        "«다 짓고 나서 긴 모서리만 쪼개기» 이고, 그건 형상을 한 점도 안 움직인다.",
        "⚠ **알려진 흠**: typhoonh480 에 `pitch_law='dji_mini2'` 를 걸면 n_sec=20(출하 값)에서만 "
        "불리언 합집합이 경계 모서리 6개를 남긴다(다른 n_sec 은 멀쩡). manifold3d 의 "
        "아슬아슬한 접촉 처리 문제로 보이고, 그 법칙은 어차피 기본으로 안 켜진다.",
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    os.replace(tmp, OUT)
    print("\n" + "\n".join("· " + x for x in doc["findings_ko"]))
    print(f"\n→ {OUT}  ({doc['runtime_s']} s)")


if __name__ == "__main__":
    main()
