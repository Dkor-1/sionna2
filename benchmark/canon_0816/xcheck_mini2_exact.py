# -*- coding: utf-8 -*-
"""
xcheck_mini2_exact.py — mini2 4726F 날 계측 **독립 교차검증** (해석적 원통단면)

목적: benchmark/measure_prop_mini2_reference_0816.py 의 헤드라인
      (R, c_max/R, 정규화 시위곡선, 두께)이 **표본추출(몬테카를로) 때문에 생긴 값이
      아닌지** 확인한다. 여기서는 점을 하나도 뿌리지 않는다.

무엇이 다른가 (일부러 전부 다른 길)
  · 회전축   : 모터축 부품을 안 쓴다. 날 2장 점구름의 **최소분산 평면법선**(SVD)을 축으로.
  · 중심     : 축 방향 위치는 «두 날의 면적중심», 축 수직 위치는 **날끝 2개의 중점**.
               (2날은 축에 대해 180° 대칭이므로 두 날끝의 중점이 축 위에 있다)
  · 시위 c(r): **모서리–원통 교차의 해석해**. 각 삼각형 모서리에서 축거리 = r 이 되는
               t 를 이차방정식으로 풀어 교점을 얻는다. 표본·띠폭·난수가 하나도 안 들어간다.
               띠 반폭이라는 개념 자체가 없으므로 «띠가 넓어 시위를 크게 읽는» 편향이 원천 봉쇄.
  · 두께     : 같은 해석 단면에서 시위선 좌표계 상하면 차 (T1 과 같은 잣대, 다른 경로)
  · 투영면적 : 삼각형 Σ½|a⃗·n̂| 해석해 (샘플링 없음)

실행:
  /workspace/.venvs/py312/bin/python xcheck_mini2_exact.py
"""
from __future__ import annotations

import json
import os

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

GLB = "/workspace/sionna/assets/meshes/reference/WM161_zhankai_1k.glb"
REF = "/workspace/sionna/outputs/prop_measure_mini2_reference_0816.json"
NF_BLADE = (1691, 1635)
RR = np.round(np.arange(0.15, 0.9851, 0.005), 5)


def edges_of(m):
    F = np.asarray(m.faces, int)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E = np.sort(E, axis=1)
    return np.unique(E, axis=0)


def section_points(V, E, ctr, ax, r):
    """모서리–원통(반경 r) 교차의 **해석해**. 반환: (접선호, 축) 2D 점."""
    A, B = V[E[:, 0]], V[E[:, 1]]
    dA, dB = A - ctr, B - ctr
    uA = dA - np.outer(dA @ ax, ax)
    uB = dB - np.outer(dB @ ax, ax)
    v = uB - uA
    a = (v * v).sum(1)
    b = 2.0 * (uA * v).sum(1)
    c = (uA * uA).sum(1) - r * r
    disc = b * b - 4 * a * c
    ok = (disc > 0) & (a > 1e-18)
    if not ok.any():
        return np.zeros((0, 2))
    sq = np.sqrt(disc[ok])
    aa, bb = a[ok], b[ok]
    ts = [(-bb - sq) / (2 * aa), (-bb + sq) / (2 * aa)]
    P = []
    for t in ts:
        good = (t >= 0.0) & (t <= 1.0)
        if good.any():
            tt = t[good][:, None]
            P.append(A[ok][good] + tt * (B[ok][good] - A[ok][good]))
    if not P:
        return np.zeros((0, 2))
    P = np.vstack(P)
    d = P - ctr
    u = d @ ax
    w = d - np.outer(u, ax)
    e1 = np.array([1.0, 0.0, 0.0])
    if abs(e1 @ ax) > 0.9:
        e1 = np.array([0.0, 1.0, 0.0])
    e1 = e1 - (e1 @ ax) * ax
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    ph = np.arctan2(w @ e2, w @ e1)
    cm = np.arctan2(np.sin(ph).mean(), np.cos(ph).mean())
    dphi = (ph - cm + np.pi) % (2 * np.pi) - np.pi
    return np.c_[r * dphi, u]


def caliper(Aq):
    if len(Aq) < 4:
        return np.nan, None
    H = Aq[ConvexHull(Aq).vertices]
    D = H[:, None, :] - H[None, :, :]
    d2 = (D ** 2).sum(-1)
    i, j = np.unravel_index(np.argmax(d2), d2.shape)
    return float(np.sqrt(d2[i, j])), (H[i], H[j])


def envelope_thickness(Aq, chord, ends, n=61):
    p0, p1 = ends
    ev = (p1 - p0) / chord
    Rm = np.array([[ev[0], ev[1]], [-ev[1], ev[0]]])
    B = (Aq - p0) @ Rm.T
    xs = np.linspace(0.02, 0.98, n) * chord
    hw = chord / (n - 1) * 0.9
    up, lo = [], []
    for x in xs:
        s = np.abs(B[:, 0] - x) <= hw
        if s.sum() < 3:
            up.append(np.nan)
            lo.append(np.nan)
        else:
            up.append(B[s, 1].max())
            lo.append(B[s, 1].min())
    t = np.asarray(up) - np.asarray(lo)
    t = t[np.isfinite(t)]
    if t.size < 10:
        return np.nan, np.nan
    return float(t.max()), float(t.mean())


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
    assert len(blades) == 8, len(blades)

    # 날 8장 → 로터 4개: 서로 가장 가까운 짝 (허브 부품을 안 쓴다)
    used, rotors = set(), []
    order = sorted(range(8), key=lambda i: blades[i]["ctr"][2])
    for i in order:
        if i in used:
            continue
        cand = [j for j in range(8) if j != i and j not in used]
        j = min(cand, key=lambda j: np.linalg.norm(blades[j]["ctr"] - blades[i]["ctr"]))
        used |= {i, j}
        rotors.append((i, j))

    res = []
    for k, (i, j) in enumerate(rotors):
        mi, mj = blades[i]["af"], blades[j]["af"]
        Vi = np.asarray(mi.vertices, float)
        Vj = np.asarray(mj.vertices, float)
        Vall = np.vstack([Vi, Vj])

        # --- 축: 두 날 점구름의 최소분산 방향 (얇은 원판 ⇒ 법선 = 회전축) ---
        c0 = Vall.mean(0)
        _, _, Vt = np.linalg.svd(Vall - c0, full_matrices=False)
        ax = Vt[-1] / np.linalg.norm(Vt[-1])

        # --- 중심: 축수직 성분은 «두 날끝 중점», 축방향은 면적중심 ---
        def far(V, c, ax):
            d = V - c
            p = d - np.outer(d @ ax, ax)
            return V[np.argmax((p * p).sum(1))]
        for _ in range(6):
            ti, tj = far(Vi, c0, ax), far(Vj, c0, ax)
            mid = 0.5 * (ti + tj)
            c0 = c0 + (mid - c0) - ((mid - c0) @ ax) * ax
        ctr = c0
        Ri = np.linalg.norm((ti - ctr) - ((ti - ctr) @ ax) * ax)
        Rj = np.linalg.norm((tj - ctr) - ((tj - ctr) @ ax) * ax)
        R = float(max(Ri, Rj))

        # --- 해석적 원통단면으로 c(r), 두께 ---
        prof = {}
        for tag, m in (("bi", mi), ("bj", mj)):
            V = np.asarray(m.vertices, float)
            E = edges_of(m)
            ch, te_max, te_mean = [], [], []
            for rr in RR:
                Aq = section_points(V, E, ctr, ax, rr * R)
                if len(Aq) < 8:
                    ch.append(np.nan); te_max.append(np.nan); te_mean.append(np.nan)
                    continue
                c, ends = caliper(Aq)
                ch.append(c)
                a, b = envelope_thickness(Aq, c, ends)
                te_max.append(a); te_mean.append(b)
            prof[tag] = dict(chord=np.asarray(ch), tmax=np.asarray(te_max),
                             tmean=np.asarray(te_mean))

        # --- 투영 평면형 면적 (해석해) ---
        Aproj = 0.0
        for m in (mi, mj):
            V = np.asarray(m.vertices, float)
            F = np.asarray(m.faces, int)
            T = V[F]
            n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
            Aproj += float(0.5 * np.abs(n @ ax).sum())
        Aproj *= 0.5   # 상·하면이 겹치므로 실루엣 = 절반

        for tag in ("bi", "bj"):
            ch = prof[tag]["chord"]
            m_ = np.nanargmax(ch)
            res.append(dict(rotor=k, blade=tag,
                            R_mm=round(R, 4), dia_mm=round(2 * R, 4),
                            c_max_mm=round(float(ch[m_]), 4),
                            c_max_over_R=round(float(ch[m_] / R), 5),
                            peak_rr=float(RR[m_]),
                            chord=ch, tmax=prof[tag]["tmax"],
                            tmean=prof[tag]["tmean"],
                            planform_pair_mm2=round(Aproj, 3)))

    # ---------- 기준 산출물과 대조 ----------
    ref = json.load(open(REF))
    F = ref["F_reference_curve"]
    dep = sorted(res, key=lambda r: -r["R_mm"])[:4]   # 완전전개 = R 큰 4장
    print("=" * 78)
    print("독립 교차검증 — 해석적 원통단면 (표본추출 없음)")
    print("=" * 78)
    for r in res:
        print(f"  rotor{r['rotor']} {r['blade']}  R={r['R_mm']:8.4f}  "
              f"c_max={r['c_max_mm']:7.4f}  c_max/R={r['c_max_over_R']:.5f} @ {r['peak_rr']:.3f}")
    Rm = float(np.mean([r["R_mm"] for r in dep]))
    cm = float(np.mean([r["c_max_over_R"] for r in dep]))
    pk = float(np.mean([r["peak_rr"] for r in dep]))
    print(f"\n  완전전개 4장 평균: R={Rm:.4f} mm  c_max/R={cm:.5f}  peak@{pk:.3f}R")
    print(f"  기준 산출물     : R={F['R_mm']:.4f} mm  c_max/R={F['c_max_over_R']:.5f} "
          f"peak@{F['peak_at_rr']:.3f}R")
    print(f"  ⇒ ΔR = {100*(Rm-F['R_mm'])/F['R_mm']:+.4f} %   "
          f"Δ(c_max/R) = {100*(cm-F['c_max_over_R'])/F['c_max_over_R']:+.3f} %")

    # 정규화 시위곡선 대조
    print("\n  정규화 시위 c/c_max 대조 (완전전개 4장 평균)")
    print("   r/R    해석단면   기준산출물     차이%")
    CH = np.vstack([r["chord"] for r in dep])
    ch = np.nanmean(CH, axis=0)
    cn = ch / np.nanmax(ch)
    worst = 0.0
    for key, val in F["chord_norm_c_over_cmax"].items():
        rr = float(key)
        k = int(np.argmin(np.abs(RR - rr)))
        if abs(RR[k] - rr) > 1e-6 or not np.isfinite(cn[k]):
            continue
        dpct = 100 * (cn[k] - val) / val
        worst = max(worst, abs(dpct))
        print(f"   {rr:.2f}   {cn[k]:.4f}    {val:.4f}    {dpct:+6.2f}")
    print(f"  ⇒ 정규화 곡선 최대 편차 {worst:.2f} %")

    # 두께 대조
    print("\n  두께 대조 (t_env_max, 완전전개 4장 평균) [mm]")
    TM = np.nanmean(np.vstack([r["tmax"] for r in dep]), axis=0)
    TA = np.nanmean(np.vstack([r["tmean"] for r in dep]), axis=0)
    wt = 0.0
    for key, row in F["thickness_table_mm"].items():
        rr = float(key)
        k = int(np.argmin(np.abs(RR - rr)))
        if abs(RR[k] - rr) > 1e-6 or not np.isfinite(TM[k]):
            continue
        d1 = 100 * (TM[k] - row["t_env_max"]) / row["t_env_max"]
        d2 = 100 * (TA[k] - row["t_env_mean"]) / row["t_env_mean"]
        wt = max(wt, abs(d1))
        print(f"   {rr:.2f}   max {TM[k]:.4f} vs {row['t_env_max']:.4f} ({d1:+6.2f} %)   "
              f"mean {TA[k]:.4f} vs {row['t_env_mean']:.4f} ({d2:+6.2f} %)")
    print(f"  ⇒ 최대두께 최대 편차 {wt:.2f} %")

    # 시위가중 스팬평균 두께 (0.20~0.96R)
    sel = (RR >= 0.20) & (RR <= 0.96) & np.isfinite(TA) & np.isfinite(ch)
    tbar = float(np.sum(TA[sel] * ch[sel]) / np.sum(ch[sel]))
    print(f"\n  시위가중 스팬평균 두께 0.20~0.96R : 해석단면 {tbar:.4f} mm  vs  "
          f"기준 {ref['I_thickness_ruler_reconciliation']['t_env_mean_T1']:.4f} mm  "
          f"({100*(tbar-ref['I_thickness_ruler_reconciliation']['t_env_mean_T1'])/ref['I_thickness_ruler_reconciliation']['t_env_mean_T1']:+.2f} %)")

    pf = float(np.mean([r["planform_pair_mm2"] for r in dep])) / 2.0
    print(f"  날 1장 투영 평면형 면적(전체 스팬): 해석 {pf:.2f} mm²")
    print(f"  (참고) 기준 0.20~0.96R 창 참시위 적분: "
          f"{ref['I_vs_prior_audit']['blade_planform_area_true_chord_mm2']:.2f} mm²")

    out = dict(
        deployed4_R_mm=round(Rm, 4), deployed4_c_max_over_R=round(cm, 5),
        deployed4_peak_rr=round(pk, 4),
        ref_R_mm=F["R_mm"], ref_c_max_over_R=F["c_max_over_R"],
        norm_curve_max_dev_pct=round(worst, 3),
        t_env_max_max_dev_pct=round(wt, 3),
        t_chordmean_0p20_0p96=round(tbar, 4),
        per_blade=[{k: v for k, v in r.items()
                    if k not in ("chord", "tmax", "tmean")} for r in res])
    p = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/xcheck_mini2_exact.json"
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print("\n  →", p)


if __name__ == "__main__":
    main()
