# -*- coding: utf-8 -*-
"""az_falsify_plate.py — ⭐우리 커널의 «방위 둔감» 이 격자 탓인지 판정한다.

의심: rcs_sbr.sbr_field 의 면적분 격자(λ/12)가 성겨서 **거울 반사 로브**(폭 ≈ λ/D)를
뭉개는 것 아니냐. 그렇다면 방위를 돌려도 값이 안 변하는 것이 물리가 아니라 결함이다.

방법: 답을 아는 표적(직사각 완전도체 평판)으로 **커널과 같은 식**을 CPU 에서 그대로 돌린다.
  · 격자 구성은 rcs_sbr._grid_basis / _ray_grid 를 **글자 그대로** 옮겼다(GPU·mitsuba 없이).
  · 평판은 평면이라 광선-면 교차가 해석적이다 → Mitsuba 없이 같은 히트점이 나온다.
  · 커널 식:  E = Σ_hits |Γ| e^{j2k(P−ctr)·û} d²      σ = (4π/λ²)|E|²
  · 해석 PO:  E = A cosθ · sinc(k a u_x) · sinc(k b u_y)   (투영면적분의 닫힌형)
⛔GPU 안 쓴다. mitsuba·sionna.rt 를 import 하지 않는다.
"""
from __future__ import annotations
import json
import numpy as np

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC


def grid_basis(u):                       # rcs_sbr._grid_basis 와 동일
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    return e1, e2


def sbr_field_plate(a_m, b_m, u, d, pad=1.15, gamma=1.0, off=(0.0, 0.0)):
    """평판(z=0, 법선 ẑ, a×b) 에 대해 커널과 **같은 격자·같은 합**을 돈다."""
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    k = 2.0 * np.pi / LAM
    V = np.array([[+a_m / 2, +b_m / 2, 0.], [+a_m / 2, -b_m / 2, 0.],
                  [-a_m / 2, +b_m / 2, 0.], [-a_m / 2, -b_m / 2, 0.]])
    ctr = 0.5 * (V.max(0) + V.min(0))                     # = 원점
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d
    n = int(np.ceil(2 * Rout / d))
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    e1, e2 = grid_basis(u)
    O = (ctr + Rout * u)[None, :] \
        + (A.ravel() + off[0] * d)[:, None] * e1 + (B.ravel() + off[1] * d)[:, None] * e2
    # 광선 O + s(−û) 가 z=0 을 만나는 점
    if abs(u[2]) < 1e-12:
        return 0j, 0, n                                    # 평판과 평행 — 히트 없음
    s = O[:, 2] / u[2]
    P = O - s[:, None] * u[None, :]
    hit = (np.abs(P[:, 0]) <= a_m / 2) & (np.abs(P[:, 1]) <= b_m / 2) & (s > 0)
    ph = np.exp(1j * 2.0 * k * ((P[hit] - ctr) @ u))
    return complex(gamma * ph.sum()) * d * d, int(hit.sum()), n


def po_exact(a_m, b_m, u, gamma=1.0):
    """해석 PO(투영면적분 닫힌형): E = A cosθ sinc(k a u_x) sinc(k b u_y)."""
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    k = 2.0 * np.pi / LAM
    def sc(x):
        return 1.0 if abs(x) < 1e-12 else np.sin(x) / x
    return gamma * (a_m * b_m) * abs(u[2]) * sc(k * a_m * u[0]) * sc(k * b_m * u[1])


def sig(E):
    return 10 * np.log10(4 * np.pi / LAM ** 2 * abs(E) ** 2 + 1e-300)


def resonance_45():
    """⭐div=12 의 **정확히 45° 공진** — 인접 광선 위상차 2k·d·tanθ 가 tanθ=1 에서 정확히
    2k·(λ/12) = π/3 = 60° 라, 연속한 6 표본이 6 차 단위근이 되어 **정확히 상쇄**한다.
    드론의 축정렬 금속 상자면(법선 ±x̂·±ŷ)은 방위 45° 시선에서 **바로 이 각도**에 놓인다."""
    rows = []
    for name, a_m, b_m, gam in [("battery_face", 0.0676, 0.0657, 1.0),
                                ("camera_face", 0.0590, 0.0606, 0.85),
                                ("pcb_face", 0.0536, 0.0050, 0.80)]:
        rec = {"face": name, "a_m": a_m, "b_m": b_m, "gamma": gam,
               "size_lambda": [round(a_m / LAM, 3), round(b_m / LAM, 3)],
               "po_first_null_deg": round(float(np.degrees(np.arcsin(min(1.0, LAM / (2 * a_m))))), 2),
               "sweep": []}
        for az in (0, 15, 30, 40, 43, 44, 45, 46, 47, 50):
            th = np.radians(az); u = np.array([np.sin(th), 0.0, np.cos(th)])
            rec["sweep"].append(dict(
                az_deg=az, exact_dbsm=round(sig(po_exact(a_m, b_m, u, gam)), 2),
                div12_dbsm=round(sig(sbr_field_plate(a_m, b_m, u, LAM / 12, gamma=gam)[0]), 2),
                div24_dbsm=round(sig(sbr_field_plate(a_m, b_m, u, LAM / 24, gamma=gam)[0]), 2),
                div48_dbsm=round(sig(sbr_field_plate(a_m, b_m, u, LAM / 48, gamma=gam)[0]), 2),
                div12_half_cell_dither_dbsm=round(
                    sig(sbr_field_plate(a_m, b_m, u, LAM / 12, gamma=gam, off=(.5, .5))[0]), 2)))
        rows.append(rec)
    return {"phase_step_2kd_deg": round(float(np.degrees(2 * (2 * np.pi / LAM) * (LAM / 12))), 4),
            "mechanism_ko": ("2k·d = π/3 = 60°(div=12). 표면 기울기 θ 에서 인접 광선의 위상차는 "
                             "2k·d·tanθ 이고 tanθ=1(정확히 45°)이면 60° → 연속 6 표본의 합이 0 이다. "
                             "히트 수가 6 의 배수인 평판은 **통째로 사라진다**."),
            "impact_ko": ("드론 az45 판에서 battery·camera·pcb 상자면이 정확히 이 각도에 놓인다. "
                          "다만 그 면들의 참값(PO) 합은 az45 에서 ≈ −37 dBsm 이고 총합은 −23.7 dBsm "
                          "이라, 헤드라인에 미치는 몫은 ≈0.2 dB 다. **결함은 실재하나 이 판정을 "
                          "뒤집지는 않는다** — 그래도 az45 팔은 div24 나 반칸 dither 로 다시 재야 한다."),
            "faces": rows}


def run():
    out = {"_meta": {
        "generator": "benchmark/az_falsify_plate.py",
        "question_ko": "λ/12 격자가 평판의 거울 반사 로브를 그리는가 — 방위축으로 시험",
        "fc_hz": FC, "lambda_m": LAM,
        "kernel_formula": "E = sum_hits |Gamma| exp(j2k(P-ctr).u) d^2 ; sigma = 4pi/lam^2 |E|^2",
        "exact_formula": "E = A cos(th) sinc(k a u_x) sinc(k b u_y)  (projected-aperture PO)",
        "nyquist_note_ko": ("인접 광선의 위상차 = 2k d tanθ = (2π/div)·tanθ. div=12 면 "
                            "tanθ<div/2=6 → θ<80.5° 까지 표본화 조건(위상차<π)을 만족한다."),
    }, "plates": []}
    for a_m, b_m in [(0.10, 0.10), (0.05, 0.05), (0.20, 0.10), (0.30, 0.30)]:
        rec = {"a_m": a_m, "b_m": b_m, "D_over_lambda": a_m / LAM, "sweeps": {}}
        for div in (6, 12, 24, 48):
            d = LAM / div
            rows = []
            for az in np.arange(0.0, 90.1, 2.5):
                # 평판 법선은 ẑ. «방위 회전» 은 시선을 x-z 평면 안에서 눕히는 것과 같다.
                th = np.radians(az)
                u = np.array([np.sin(th), 0.0, np.cos(th)])
                E, nh, n = sbr_field_plate(a_m, b_m, u, d)
                Ex = po_exact(a_m, b_m, u)
                rows.append(dict(az_deg=float(az), n_hits=nh, n_side=n,
                                 grid_dbsm=round(sig(E), 3), exact_dbsm=round(sig(Ex), 3),
                                 err_db=round(sig(E) - sig(Ex), 3)))
            rec["sweeps"][f"div{div}"] = rows
        # 서브셀 오프셋 산포(격자 dither) — div12 에서
        d = LAM / 12
        dith = {}
        for az in (0.0, 15.0, 30.0, 45.0, 60.0):
            th = np.radians(az)
            u = np.array([np.sin(th), 0.0, np.cos(th)])
            vals = [sig(sbr_field_plate(a_m, b_m, u, d, off=(ox, oy))[0])
                    for ox in (0.0, 0.25, 0.5) for oy in (0.0, 0.25, 0.5)]
            dith[f"az{az:g}"] = dict(min=round(min(vals), 3), max=round(max(vals), 3),
                                     span_db=round(max(vals) - min(vals), 3),
                                     exact=round(sig(po_exact(a_m, b_m, u)), 3))
        rec["dither_div12"] = dith
        out["plates"].append(rec)
    out["resonance_45deg"] = resonance_45()
    with open("/workspace/sionna/outputs/az_falsify_plate.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for rec in out["plates"]:
        print(f"\n=== plate {rec['a_m']*100:.0f} x {rec['b_m']*100:.0f} cm  "
              f"(D/λ = {rec['D_over_lambda']:.2f}) ===")
        hdr = f"{'az':>5} {'exact':>9}"
        for div in (6, 12, 24, 48):
            hdr += f" | {'div'+str(div):>9} {'err':>7}"
        print(hdr)
        r12 = rec["sweeps"]["div12"]
        for i, r in enumerate(r12):
            if r["az_deg"] % 5 > 1e-9:
                continue
            line = f"{r['az_deg']:5.1f} {r['exact_dbsm']:9.2f}"
            for div in (6, 12, 24, 48):
                rr = rec["sweeps"][f"div{div}"][i]
                line += f" | {rr['grid_dbsm']:9.2f} {rr['err_db']:+7.2f}"
            print(line)
        print(" dither(div12) span:", {k: v["span_db"] for k, v in rec["dither_div12"].items()})
    print("\n✅ outputs/az_falsify_plate.json")


if __name__ == "__main__":
    run()
