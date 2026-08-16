# -*- coding: utf-8 -*-
"""ⓐ 반증 — «DJI 는 표준 규약대로 0.75R 을 기준으로 삼는다» 를 이 데이터로 가려낼 수 있나.

두 문장은 다르다:
  (i) «공칭 피치를 **어디서 재서 표기**하는가» = 규약(문헌: 항공 프로펠러 0.75R).
  (ii) «국소 피치가 **어디서 최대**인가» = 이 GLB 에서 잰 k(r) 의 봉우리.
감사는 (ii)로 (i)을 증명했다. (ii)가 (i)을 가려낼 만큼 뾰족한지 직접 잰다.
축은 a_tip_planform.py 와 같은 **면적가중** 추정(감사·앞 라운드의 정점 PCA 와 다른 자).
⛔ 저장소 코드 무변경. GPU 미사용.
"""
import json
import sys

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

sys.path[:0] = ["/workspace/sionna/src"]
import drone_cad as dc     # noqa: E402
import drones as dr        # noqa: E402

GLB = "/workspace/sionna/assets/meshes/reference/WM161_zhankai_1k.glb"
OUT = "/workspace/sionna/outputs/_adv2_pitch_tip_0816/g_pitch_station.json"


def area_axis(V, F):
    T = V[F]
    c = T.mean(1)
    a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    mu = (c * a[:, None]).sum(0) / a.sum()
    D = c - mu
    C = (D[:, :, None] * D[:, None, :] * a[:, None, None]).sum(0) / a.sum()
    _, U = np.linalg.eigh(C)
    ax = U[:, 0]
    return ax / np.linalg.norm(ax), mu


def caliper_angle(P):
    if len(P) < 4:
        return np.nan
    try:
        Q = P[ConvexHull(P).vertices]
    except Exception:
        Q = P
    D = Q[:, None, :] - Q[None, :, :]
    L = np.linalg.norm(D, axis=-1)
    i, j = np.unravel_index(np.argmax(L), L.shape)
    v = Q[j] - Q[i]
    return float(np.arctan2(abs(v[1]), abs(v[0])))


def k_profile(V, F, axis, centre, rr, band_mm=0.35, P_nom=2.6 * 0.0254):
    v2, f2 = trimesh.remesh.subdivide_to_size(V, F, max_edge=4e-4)
    a = axis / np.linalg.norm(axis)
    X = v2 - centre
    z = X @ a
    Xp = X - np.outer(z, a)
    r = np.linalg.norm(Xp, axis=1)
    R = float(r.max())
    e1 = np.array([1.0, 0.0, 0.0]) - a[0] * a
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    ph = np.arctan2(Xp @ e2, Xp @ e1)
    ctr = np.arctan2(np.sin(ph).mean(), np.cos(ph).mean())
    ph = (ph - ctr + np.pi) % (2 * np.pi) - np.pi
    out = {}
    for x in rr:
        r0 = x * R
        m = np.abs(r - r0) <= band_mm * 1e-3
        if m.sum() < 8:
            continue
        Pp = np.c_[r0 * ph[m], z[m] - np.median(z[m])]
        b = caliper_angle(Pp)
        out[round(float(x), 3)] = dict(beta_deg=round(float(np.degrees(b)), 3),
                                       k=round(float(2 * np.pi * r0 * np.tan(b) / P_nom), 4))
    return out, R


def main():
    S = trimesh.load(GLB)
    G = S.dump(concatenate=False)
    blades = [g for g in G if len(g.faces) in (1635, 1691)]
    hubs = [g for g in G if len(g.faces) == 1704]
    axes = []
    for h in hubs:
        ax, mu = area_axis(np.asarray(h.vertices, float), np.asarray(h.faces, np.int64))
        if ax[1] < 0:
            ax = -ax
        axes.append((ax, mu))
    rr = np.round(np.arange(0.30, 0.981, 0.05), 3)
    res = {"_meta": dict(
        glb=GLB, P_nom_in=2.6, band_mm=0.35,
        axis="허브 삼각형 면적가중 공분산 최소분산축",
        q="k(r) 봉우리가 0.75R 을 «가려낼» 만큼 뾰족한가",
        n_distinct_blade_meshes=len(set(len(b.faces) for b in blades))),
        "hub_axis_tilt_deg": [round(float(np.degrees(np.arccos(min(1, abs(a[1]))))), 3)
                              for a, _ in axes]}
    rows = []
    for b in blades:
        V, F = np.asarray(b.vertices, float), np.asarray(b.faces, np.int64)
        cb = V.mean(0)
        hi = int(np.argmin([np.linalg.norm(cb - mu) for _, mu in axes]))
        prof, R = k_profile(V, F, axes[hi][0], axes[hi][1], rr)
        rows.append(dict(faces=int(len(F)), hub=hi, R_mm=round(R * 1000, 3), prof=prof))
    res["blades"] = rows
    ks = np.array([[rw["prof"].get(float(x), {}).get("k", np.nan) for x in rr] for rw in rows])
    res["k_mean"] = {str(x): round(float(np.nanmean(ks[:, i])), 4) for i, x in enumerate(rr)}
    res["k_sd"] = {str(x): round(float(np.nanstd(ks[:, i])), 4) for i, x in enumerate(rr)}
    res["argmax_per_blade"] = [float(rr[int(np.nanargmax(row))]) for row in ks]
    km = np.array([res["k_mean"][str(x)] for x in rr])
    within2 = [float(x) for x, v in zip(rr, km) if v >= 0.98 * np.nanmax(km)]
    res["stations_within_2pct_of_max"] = within2
    # 공칭 피치 P 를 ±% 흔들면 k=1 교차점이 어디로 가나
    res["k_eq_1_station_vs_Pnom"] = {}
    for d in (-6, -4, -2, 0, 2, 4, 6):
        kk = km / (1.0 + d / 100.0)
        cross = [float(rr[i]) for i in range(1, len(kk))
                 if (kk[i - 1] - 1) * (kk[i] - 1) < 0]
        res["k_eq_1_station_vs_Pnom"][f"{d:+d}%"] = cross
    # 우리 legacy 법칙
    spec = dr.DRONES["mini2"]
    res["ours_legacy"] = dict(
        k_at={str(x): round(float(np.interp(x, dc.PITCH_RR, dc.PITCH_K)), 4)
              for x in (0.5, 0.6, 0.7, 0.75, 0.8, 0.9)},
        argmax_rr=float(np.array(dc.PITCH_RR)[int(np.argmax(dc.PITCH_K))]),
        note="k(0.5R)=1.000 은 **표 정의**다 — 기준 반경이 0.5R 이라는 말은 참이다.")
    #  ⭐ 기준 반경이 «형상» 을 바꾸나: θ(r)=atan(k(r)P/2πr) 는 k·P 의 곱만 본다.
    #     기준을 0.75R 로 옮기고 P 를 같은 비로 다시 잡으면 **형상은 한 톨도 안 바뀐다.**
    k75 = float(np.interp(0.75, dc.PITCH_RR, dc.PITCH_K))
    res["reference_station_is_bookkeeping"] = dict(
        k_legacy_at_0p75R=round(k75, 4),
        meaning=("k 를 k/1.0614 로, P 를 P×1.0614 로 같이 바꾸면 θ(r) 이 **완전히 같다**. "
                 "즉 «기준 반경» 자체는 형상이 아니라 장부다. 진짜 결함은 제조사 공칭 피치"
                 "(관례상 0.75R)를 0.5R 기준 표에 그대로 먹인 것 — 날 전체가 그 비율만큼 "
                 "과피치가 된다."),
        overpitch_pct=round(100 * (k75 - 1), 2))
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("hub tilt:", res["hub_axis_tilt_deg"], " distinct blade meshes:",
          res["_meta"]["n_distinct_blade_meshes"])
    print("k_mean:", res["k_mean"])
    print("k_sd  :", res["k_sd"])
    print("argmax per blade:", res["argmax_per_blade"])
    print("최대의 2 % 안 정거장:", within2)
    print("k=1 교차 vs P_nom:", res["k_eq_1_station_vs_Pnom"])
    print("legacy k(0.75R):", k75)


if __name__ == "__main__":
    main()
