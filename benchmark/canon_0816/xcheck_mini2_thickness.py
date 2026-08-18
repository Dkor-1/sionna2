# -*- coding: utf-8 -*-
"""
xcheck_mini2_thickness.py — mini2 4726F 날 **두께** 독립 교차검증

앞선 xcheck_mini2_exact.py 는 «해석 단면의 점» 만 썼기 때문에 시위 방향 station 마다
점이 모자라 두께가 군데군데 비었다. 여기서는 점이 아니라 **선분**을 쓴다:

  삼각형 하나가 원통(반경 r)에 잘리면 교점이 정확히 2개 나오고 → **선분 1개**.
  그 선분들을 모으면 단면 윤곽이 «틈 없이» 덮인다.
  시위좌표 x 에서 그 x 를 가로지르는 선분들의 y 를 모두 구해
      t(x) = max y − min y
  로 두께를 낸다. 점 밀도와 무관하게 정확하다.

⭐이 경로에는 표면 표본추출·난수·띠폭이 하나도 없다.
"""
from __future__ import annotations

import json

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

GLB = "/workspace/sionna/assets/meshes/reference/WM161_zhankai_1k.glb"
REF = "/workspace/sionna/outputs/prop_measure_mini2_reference_0816.json"
NF_BLADE = (1691, 1635)
RR = np.round(np.arange(0.15, 0.9851, 0.005), 5)
NSTA = 61


def frame_of(ax):
    e1 = np.array([1.0, 0.0, 0.0])
    if abs(e1 @ ax) > 0.9:
        e1 = np.array([0.0, 1.0, 0.0])
    e1 = e1 - (e1 @ ax) * ax
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(ax, e1)


def face_segments(V, F, ctr, ax, r, e1, e2):
    """삼각형 × 원통(r) 교차 → 선분들. 반환: (M,2,2) [(호,축) 좌표]"""
    E = np.stack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=1)   # (Nf,3,2)
    A = V[E[..., 0]]
    B = V[E[..., 1]]
    dA = A - ctr
    uA = dA - (dA @ ax)[..., None] * ax
    dB = B - ctr
    uB = dB - (dB @ ax)[..., None] * ax
    v = uB - uA
    a = (v * v).sum(-1)
    b = 2.0 * (uA * v).sum(-1)
    c = (uA * uA).sum(-1) - r * r
    disc = b * b - 4 * a * c
    ok = (disc > 0) & (a > 1e-18)
    sq = np.sqrt(np.where(ok, disc, 0.0))
    pts, valid = [], []
    for sgn in (-1.0, +1.0):
        t = np.where(ok, (-b + sgn * sq) / np.where(a > 0, 2 * a, 1.0), -1.0)
        good = ok & (t >= 0.0) & (t < 1.0)     # [0,1) — 공유 정점 이중계상 방지
        pts.append(A + t[..., None] * (B - A))
        valid.append(good)
    P = np.stack(pts, axis=2)                  # (Nf,3,2,3)
    G = np.stack(valid, axis=2)                # (Nf,3,2)
    cnt = G.reshape(len(F), -1).sum(1)
    sel = np.where(cnt == 2)[0]
    if sel.size == 0:
        return np.zeros((0, 2, 2))
    Ps = P[sel].reshape(len(sel), 6, 3)
    Gs = G[sel].reshape(len(sel), 6)
    idx = np.argsort(~Gs, axis=1, kind="stable")[:, :2]
    S = np.take_along_axis(Ps, idx[..., None], axis=1)          # (M,2,3)
    d = S - ctr
    u = d @ ax
    w = d - u[..., None] * ax
    ph = np.arctan2(w @ e2, w @ e1)
    cm = np.arctan2(np.sin(ph).mean(), np.cos(ph).mean())
    dphi = (ph - cm + np.pi) % (2 * np.pi) - np.pi
    return np.stack([r * dphi, u], axis=-1)                      # (M,2,2)


def caliper(Aq):
    H = Aq[ConvexHull(Aq).vertices]
    D = H[:, None, :] - H[None, :, :]
    d2 = (D ** 2).sum(-1)
    i, j = np.unravel_index(np.argmax(d2), d2.shape)
    return float(np.sqrt(d2[i, j])), (H[i], H[j])


def envelope_from_segments(S, chord, ends, nsta=NSTA):
    """선분 집합 → 시위좌표 station 별 (상면−하면). 점 밀도 무관."""
    p0, p1 = ends
    ev = (p1 - p0) / chord
    Rm = np.array([[ev[0], ev[1]], [-ev[1], ev[0]]])
    Q = (S.reshape(-1, 2) - p0) @ Rm.T
    Q = Q.reshape(-1, 2, 2)
    x0, y0 = Q[:, 0, 0], Q[:, 0, 1]
    x1, y1 = Q[:, 1, 0], Q[:, 1, 1]
    xs = np.linspace(0.02, 0.98, nsta) * chord
    lo_x = np.minimum(x0, x1)
    hi_x = np.maximum(x0, x1)
    t_up, t_mid = [], []
    for x in xs:
        m = (lo_x <= x) & (hi_x >= x) & (hi_x > lo_x)
        if m.sum() < 2:
            t_up.append(np.nan)
            continue
        f = (x - x0[m]) / (x1[m] - x0[m])
        y = y0[m] + f * (y1[m] - y0[m])
        t_up.append(float(y.max() - y.min()))
        t_mid.append(0.5 * float(y.max() + y.min()))
    t = np.asarray(t_up, float)
    good = np.isfinite(t)
    if good.sum() < nsta * 0.8:
        return np.nan, np.nan, np.nan
    cam = np.asarray(t_mid, float)
    return float(np.nanmax(t)), float(np.nanmean(t)), float(np.nanmax(np.abs(cam)) / chord)


def main():
    scene = trimesh.load(GLB, process=False)
    blades = []
    for node in scene.graph.nodes_geometry:
        T, g = scene.graph[node]
        m = scene.geometry[g]
        if len(m.faces) not in NF_BLADE:
            continue
        w = m.copy()
        w.apply_transform(T)
        w.apply_scale(1000.0)
        w.merge_vertices()
        comps = sorted(w.split(only_watertight=False), key=lambda c: -len(c.faces))
        blades.append(dict(node=node, af=comps[0],
                           ctr=np.asarray(comps[0].vertices, float).mean(0)))
    used, rotors = set(), []
    for i in sorted(range(8), key=lambda i: blades[i]["ctr"][2]):
        if i in used:
            continue
        j = min([k for k in range(8) if k != i and k not in used],
                key=lambda k: np.linalg.norm(blades[k]["ctr"] - blades[i]["ctr"]))
        used |= {i, j}
        rotors.append((i, j))

    rows = []
    for k, (i, j) in enumerate(rotors):
        Vi = np.asarray(blades[i]["af"].vertices, float)
        Vj = np.asarray(blades[j]["af"].vertices, float)
        Vall = np.vstack([Vi, Vj])
        c0 = Vall.mean(0)
        _, _, Vt = np.linalg.svd(Vall - c0, full_matrices=False)
        ax = Vt[-1] / np.linalg.norm(Vt[-1])

        def far(V, c):
            d = V - c
            p = d - np.outer(d @ ax, ax)
            return V[np.argmax((p * p).sum(1))]
        for _ in range(6):
            ti, tj = far(Vi, c0), far(Vj, c0)
            mid = 0.5 * (ti + tj)
            c0 = c0 + (mid - c0) - ((mid - c0) @ ax) * ax
        ctr = c0
        R = float(max(np.linalg.norm((t_ - ctr) - ((t_ - ctr) @ ax) * ax)
                      for t_ in (ti, tj)))
        e1, e2 = frame_of(ax)

        for tag, bi in (("b0", i), ("b1", j)):
            m = blades[bi]["af"]
            V = np.asarray(m.vertices, float)
            F = np.asarray(m.faces, int)
            ch, tmax, tmean, cam = [], [], [], []
            for rr in RR:
                S = face_segments(V, F, ctr, ax, rr * R, e1, e2)
                if len(S) < 6:
                    ch.append(np.nan); tmax.append(np.nan)
                    tmean.append(np.nan); cam.append(np.nan)
                    continue
                Aq = S.reshape(-1, 2)
                c, ends = caliper(Aq)
                a_, b_, cm_ = envelope_from_segments(S, c, ends)
                ch.append(c); tmax.append(a_); tmean.append(b_); cam.append(cm_)
            rows.append(dict(rotor=k, blade=tag, R=R,
                             chord=np.asarray(ch), tmax=np.asarray(tmax),
                             tmean=np.asarray(tmean), cam=np.asarray(cam)))

    ref = json.load(open(REF))
    F_ = ref["F_reference_curve"]
    dep = sorted(rows, key=lambda r: -r["R"])[:4]
    CH = np.nanmean(np.vstack([r["chord"] for r in dep]), 0)
    TM = np.nanmean(np.vstack([r["tmax"] for r in dep]), 0)
    TA = np.nanmean(np.vstack([r["tmean"] for r in dep]), 0)
    CM = np.nanmean(np.vstack([r["cam"] for r in dep]), 0)

    print("=" * 84)
    print("두께 독립 교차검증 — 삼각형×원통 교차선분 (표본추출·난수·띠폭 없음)")
    print("=" * 84)
    print(" r/R |  chord[mm]        |  t_env_max[mm]           |  t_env_mean[mm]")
    print("     |  seg      ref   % |  seg     ref       %     |  seg     ref       %")
    w_c = w_max = w_mean = 0.0
    tbl = {}
    for key, row in F_["thickness_table_mm"].items():
        rr = float(key)
        kk = int(np.argmin(np.abs(RR - rr)))
        if abs(RR[kk] - rr) > 1e-6:
            continue
        dc = 100 * (CH[kk] - row["chord"]) / row["chord"]
        d1 = 100 * (TM[kk] - row["t_env_max"]) / row["t_env_max"]
        d2 = 100 * (TA[kk] - row["t_env_mean"]) / row["t_env_mean"]
        w_c = max(w_c, abs(dc)); w_max = max(w_max, abs(d1)); w_mean = max(w_mean, abs(d2))
        tbl[key] = dict(chord_seg=round(float(CH[kk]), 4),
                        t_env_max_seg=round(float(TM[kk]), 4),
                        t_env_mean_seg=round(float(TA[kk]), 4),
                        d_chord_pct=round(dc, 2), d_tmax_pct=round(d1, 2),
                        d_tmean_pct=round(d2, 2))
        print(f" {rr:.2f}| {CH[kk]:7.4f} {row['chord']:7.4f} {dc:+5.2f} |"
              f" {TM[kk]:6.4f} {row['t_env_max']:6.4f} {d1:+6.2f} |"
              f" {TA[kk]:6.4f} {row['t_env_mean']:6.4f} {d2:+6.2f}")
    print(f"\n 최대편차: chord {w_c:.2f} %  ·  t_env_max {w_max:.2f} %  ·  t_env_mean {w_mean:.2f} %")

    sel = (RR >= 0.20) & (RR <= 0.96) & np.isfinite(TA) & np.isfinite(CH)
    tbar = float(np.sum(TA[sel] * CH[sel]) / np.sum(CH[sel]))
    tmx = float(np.sum(TM[sel] * CH[sel]) / np.sum(CH[sel]))
    ref_t = ref["I_thickness_ruler_reconciliation"]["t_env_mean_T1"]
    print(f"\n 시위가중 스팬평균 (0.20~0.96R)")
    print(f"   t_env_mean : 선분 {tbar:.4f} mm  vs  기준 {ref_t:.4f} mm  "
          f"({100*(tbar-ref_t)/ref_t:+.2f} %)")
    print(f"   t_env_max  : 선분 {tmx:.4f} mm  vs  기준 헤드라인 "
          f"{ref['H_headline']['thickness']['t_env_max_span_mm']:.4f} mm (창 0.2-0.9)")
    print(f"   캠버 max/c : 선분 {float(np.nanmean(CM[sel])):.4f}  vs  기준 "
          f"{ref['C_blades'][0]['camber_over_c_mean']:.4f}")

    out = dict(rows=tbl, t_chordmean_0p20_0p96_seg=round(tbar, 4),
               t_max_chordweighted_0p20_0p96_seg=round(tmx, 4),
               ref_t_chordmean=ref_t,
               worst_pct=dict(chord=round(w_c, 2), t_env_max=round(w_max, 2),
                              t_env_mean=round(w_mean, 2)))
    p = ("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/"
         "scratchpad/xcheck_mini2_thickness.json")
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print("\n →", p)


if __name__ == "__main__":
    main()
