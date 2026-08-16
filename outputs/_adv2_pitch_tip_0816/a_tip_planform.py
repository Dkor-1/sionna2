# -*- coding: utf-8 -*-
"""ⓓ 반증 — «실물 프롭 팁은 뭉툭하다 → CHORD_FRAC 끝값 0.10 → 0.20» 이 맞나.

방법(감사·앞선 반증과 **다른 자**를 일부러 쓴다)
  ① 회전축: 허브 삼각형의 **면적가중 공분산** 최소분산축 (앞 라운드는 정점 PCA 였다 —
     정점 밀도 편향을 안 받는 쪽으로 바꿔 축 추정 자체를 교차검증한다).
  ② 팁 형상 잣대 두 벌 — 둘 다 «단면» 정의에 안 기댄다:
     (a) 투영 시위  c_proj(r) = r·(φ_max−φ_min)  (회전면에 그림자를 떨어뜨린 폭)
     (b) 투영 면적  A_proj(밴드) = ½·Σ|삼각형의 회전면 투영면적|  (얇은 껍질이라 상·하면 2겹)
  ③ **같은 자로 우리 날도 잰다.** 법칙 상수표를 읽어 비교하지 않는다 — 실제로 메쉬를 지어
     같은 함수에 넣는다. 끝값 0.10(legacy) · 0.20(감사 권고) · 그 사이 값들.
⛔ 저장소 코드 무변경. 대안 끝값은 이 프로세스 안에서만 리스트로 만든다. GPU 미사용.
"""
import json
import sys

import numpy as np
import trimesh

sys.path[:0] = ["/workspace/sionna/src"]
import drone_cad as dc          # noqa: E402
import drones as dr             # noqa: E402

GLB = "/workspace/sionna/assets/meshes/reference/WM161_zhankai_1k.glb"
OUT = "/workspace/sionna/outputs/_adv2_pitch_tip_0816/a_tip_planform.json"


# ─── 자(ruler) ─────────────────────────────────────────────────────────────
def area_weighted_axis(V, F):
    """삼각형 **면적가중** 공분산의 최소분산축 = 납작한 원반의 대칭축."""
    T = V[F]
    c = T.mean(1)
    a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    mu = (c * a[:, None]).sum(0) / a.sum()
    D = c - mu
    C = (D[:, :, None] * D[:, None, :] * a[:, None, None]).sum(0) / a.sum()
    w, U = np.linalg.eigh(C)
    ax = U[:, 0]
    return ax / np.linalg.norm(ax), mu


def planform(V, F, axis, centre, nbin=400, subdiv_mm=0.35):
    """한 장의 날 → (r/R 격자, 투영시위 c_proj[m], 투영면적 밀도 dA/dr) 와 R."""
    a = axis / np.linalg.norm(axis)
    # (a) 투영 시위 — 조밀 점구름의 방위 폭
    v2, f2 = trimesh.remesh.subdivide_to_size(np.asarray(V, float), np.asarray(F, np.int64),
                                              max_edge=subdiv_mm * 1e-3)
    X = v2 - centre
    z = X @ a
    Xp = X - np.outer(z, a)
    r = np.linalg.norm(Xp, axis=1)
    R = float(r.max())
    e1 = np.array([1.0, 0.0, 0.0]) - a[0] * a
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    ph = np.arctan2(Xp @ e2, Xp @ e1)
    ph = np.unwrap(np.sort(ph))              # 한 장의 날은 방위로 이어져 있다
    # 방위 원점을 날 중앙으로 옮겨 wrap 을 없앤다
    ph0 = np.arctan2(Xp @ e2, Xp @ e1)
    ctr = np.arctan2(np.sin(ph0).mean(), np.cos(ph0).mean())
    ph0 = (ph0 - ctr + np.pi) % (2 * np.pi) - np.pi
    edges = np.linspace(0.0, R, nbin + 1)
    idx = np.clip(np.digitize(r, edges) - 1, 0, nbin - 1)
    cp = np.full(nbin, np.nan)
    for b in range(nbin):
        m = idx == b
        if m.sum() >= 4:
            rm = 0.5 * (edges[b] + edges[b + 1])
            cp[b] = rm * (ph0[m].max() - ph0[m].min())
    # (b) 투영 면적 — 삼각형별. ⚠**세분한 메쉬**를 쓴다: GLB 는 1k 간략화라 팁 쪽 삼각형이
    #     커서, 원 메쉬 무게중심으로 반경빈을 나누면 면적이 한 빈에 뭉쳐 가짜 스파이크가 난다
    #     (첫 판에서 실제로 그랬다 — 0.95~0.96R 에 1.72 %, 0.96~0.98R 에 0.02 %).
    Vc = np.asarray(v2, float) - centre
    T = Vc[np.asarray(f2, np.int64)]
    Tp = T - (T @ a)[:, :, None] * a
    ar = 0.5 * np.abs(np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0]) @ a)
    rc = np.linalg.norm((T.mean(1) - (T.mean(1) @ a)[:, None] * a), axis=1)
    ib = np.clip(np.digitize(rc, edges) - 1, 0, nbin - 1)
    Ab = np.bincount(ib, weights=ar, minlength=nbin) * 0.5      # 상·하면 2겹 → ½
    rmid = 0.5 * (edges[:-1] + edges[1:])
    return rmid / R, cp, Ab, R


def band_area(rr, Ab, lo, hi):
    m = (rr >= lo) & (rr < hi)
    return float(Ab[m].sum())


def curve(rr, cp, grid):
    ok = np.isfinite(cp)
    return np.interp(grid, rr[ok], cp[ok])


# ─── 우리 날 짓기 ──────────────────────────────────────────────────────────
def our_blade(spec, chord_frac_tip=None, law="legacy", tip_refine=None, n_sec=44):
    R = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in) * 0.0254
    cmax, _ = dc.resolve_chord_max_over_r(spec, law)
    c_rr, c_fr, _ = dc.resolve_chord_profile(spec, law)
    if c_rr is None:
        c_rr, c_fr = dc.BLADE_LAWS[law]["chord_rr"], dc.BLADE_LAWS[law]["chord_frac"]
    if chord_frac_tip is not None:
        c_fr = tuple(list(c_fr)[:-1] + [float(chord_frac_tip)])
    m = dc._blade(R, root_frac=0.070, chord_max=cmax, pitch_m=P, n_sec=n_sec,
                  law=law, tip_refine=tip_refine, chord_rr=c_rr, chord_frac=c_fr)
    return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64), R, cmax


def main():
    GRID = np.array([0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.92, 0.94, 0.95, 0.96,
                     0.97, 0.98, 0.99, 0.995, 0.999])
    res = {"_meta": dict(
        what="ⓓ 팁 끝값 0.10→0.20 권고의 반증 시도 — 실물 DJI 날과 우리 날을 **같은 자**로",
        rulers=["투영 시위 r·Δφ (400 반경빈, 0.35 mm 세분)", "투영 면적 ½Σ|삼각형 투영| (400 빈)"],
        axis="허브 삼각형 면적가중 공분산 최소분산축 (정점 PCA 가 아니다)")}

    # ── 실물 DJI
    S = trimesh.load(GLB)
    geoms = S.dump(concatenate=False)
    blades = [g for g in geoms if len(g.faces) in (1635, 1691)]
    hubs = [g for g in geoms if len(g.faces) == 1704]
    axes = []
    for h in hubs:
        ax, mu = area_weighted_axis(np.asarray(h.vertices, float), np.asarray(h.faces, np.int64))
        if ax[1] < 0:
            ax = -ax
        axes.append((ax, mu))
    res["hub_axis_deg_from_world_y"] = [round(float(np.degrees(np.arccos(min(1, abs(a[1]))))), 3)
                                        for a, _ in axes]
    dji = []
    for b in blades:
        Vb, Fb = np.asarray(b.vertices, float), np.asarray(b.faces, np.int64)
        cb = Vb.mean(0)
        hi = int(np.argmin([np.linalg.norm(cb - mu) for _, mu in axes]))
        ax, mu = axes[hi]
        rr, cp, Ab, R = planform(Vb, Fb, ax, mu)
        cmaxp = float(np.nanmax(cp))
        row = dict(hub=hi, R_mm=R * 1000, c_proj_max_mm=cmaxp * 1000,
                   c_max_over_R=cmaxp / R,
                   c_norm={f"{g:.3f}": round(float(v / cmaxp), 4)
                           for g, v in zip(GRID, curve(rr, cp, GRID))},
                   A_total_mm2=float(Ab.sum()) * 1e6,
                   A_band={f"{lo:.2f}-{hi2:.2f}": round(band_area(rr, Ab, lo, hi2) * 1e6, 4)
                           for lo, hi2 in [(0.20, 0.90), (0.90, 0.95), (0.95, 0.98),
                                           (0.98, 1.00), (0.90, 1.00), (0.96, 1.00)]})
        dji.append(row)
    res["dji_blades"] = dji

    def agg(rows, key):
        return {k: [round(float(np.mean([r[key][k] for r in rows])), 4),
                    round(float(np.std([r[key][k] for r in rows])), 4)] for k in rows[0][key]}
    res["dji_mean_sd"] = dict(c_norm=agg(dji, "c_norm"), A_band=agg(dji, "A_band"),
                              R_mm=[round(float(np.mean([r["R_mm"] for r in dji])), 3),
                                    round(float(np.std([r["R_mm"] for r in dji])), 3)],
                              c_max_over_R=[round(float(np.mean([r["c_max_over_R"] for r in dji])), 4),
                                            round(float(np.std([r["c_max_over_R"] for r in dji])), 4)])

    # ── 우리 날 (mini2 스펙) — 같은 자
    spec = dr.DRONES["mini2"]
    ours = {}
    cases = [("legacy(끝값 0.10)", dict(law="legacy")),
             ("legacy+끝값 0.20", dict(law="legacy", chord_frac_tip=0.20)),
             ("dji_mini2 판(끝값 0.20·tip_refine 3)", dict(law="dji_mini2")),
             ("dji_mini2 곡선+끝값 0.10", dict(law="dji_mini2", chord_frac_tip=0.10)),
             ("dji_mini2 곡선+끝값 0.05", dict(law="dji_mini2", chord_frac_tip=0.05)),
             ("dji_mini2 곡선+끝값 0.30", dict(law="dji_mini2", chord_frac_tip=0.30))]
    ax = np.array([0.0, 0.0, 1.0])
    for name, kw in cases:
        V, F, R, cmax = our_blade(spec, **kw)
        rr, cp, Ab, Rm = planform(V, F, ax, np.zeros(3))
        cmaxp = float(np.nanmax(cp))
        ours[name] = dict(R_mm=Rm * 1000, chord_max_over_R_param=cmax,
                          c_proj_max_mm=cmaxp * 1000, c_max_over_R=cmaxp / Rm,
                          c_norm={f"{g:.3f}": round(float(v / cmaxp), 4)
                                  for g, v in zip(GRID, curve(rr, cp, GRID))},
                          A_total_mm2=float(Ab.sum()) * 1e6,
                          A_band={f"{lo:.2f}-{h2:.2f}": round(band_area(rr, Ab, lo, h2) * 1e6, 4)
                                  for lo, h2 in [(0.20, 0.90), (0.90, 0.95), (0.95, 0.98),
                                                 (0.98, 1.00), (0.90, 1.00), (0.96, 1.00)]})
    res["ours"] = ours

    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)

    # ── 화면 요약
    print("hub axis tilt from +y [deg]:", res["hub_axis_deg_from_world_y"])
    print(f"DJI R = {res['dji_mean_sd']['R_mm']} mm, c_max/R = {res['dji_mean_sd']['c_max_over_R']}")
    print("\n정규화 투영시위 c/c_max")
    hdr = "  r/R  " + "".join(f"{g:>7.3f}" for g in GRID)
    print(hdr)
    dm = res["dji_mean_sd"]["c_norm"]
    print("  DJI  " + "".join(f"{dm[f'{g:.3f}'][0]:>7.3f}" for g in GRID))
    print("  sd   " + "".join(f"{dm[f'{g:.3f}'][1]:>7.3f}" for g in GRID))
    for name in ours:
        print(f"  {name[:22]:22s}" + "".join(f"{ours[name]['c_norm'][f'{g:.3f}']:>7.3f}" for g in GRID))
    print("\n밴드 투영면적 / 전체 [%]")
    for k in res["dji_mean_sd"]["A_band"]:
        tot = float(np.mean([b["A_total_mm2"] for b in dji]))
        v = res["dji_mean_sd"]["A_band"][k][0]
        line = f"  {k:>11s}  DJI {100*v/tot:6.2f}"
        for name in ours:
            line += f" | {name[:14]:14s} {100*ours[name]['A_band'][k]/ours[name]['A_total_mm2']:6.2f}"
        print(line)


if __name__ == "__main__":
    main()
