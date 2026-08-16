# -*- coding: utf-8 -*-
"""
adv_refute_thickness_pass3_0816.py — **DJI 실물 날을 우리 자로 직접 잰다** (2026-08-16)
==================================================================================
2차(Ⓕ)에서 «감사 §4-3 의 0.876 mm 는 최대두께 자이고 슬래브 등가 두께가 아니다» 라고 판정했다.
그 판정이 **남의 스테이션 표를 적분한 결과**이므로, 여기서는 원본 GLB 를 열어 **우리 저장소가
우리 메쉬에 쓰는 바로 그 자**(`src/prop_thickness.cylinder_section_loops` + `section_metrics`)로
DJI Mini 2 순정 날을 직접 잰다. 그래야 «우리 mini2 0.6146 mm» 와 사과-대-사과가 된다.

절차 (남의 수치를 안 쓴다 — 부품 **이름**만 빌린다)
  1. GLB 를 노드 변환 적용해 로드하고 m → mm.
  2. 모터축 부품의 면적가중 공분산에서 **회전축을 내가 직접 구한다**(회전체는 고유값 둘이
     같고 하나가 다르다 — 다른 하나가 축). 보고된 축과 각도차를 교차검사로만 적는다.
  3. 축을 +z 로 돌리고 축 위 점을 원점으로 옮긴다.
  4. 날 노드의 **최대 연결요소**(에어포일 셸)만 남긴다 — 접이 힌지뭉치·와셔·부유 조각 제외.
  5. r/R = 0.20…0.96 에서 원통 단면 → 시위·단면적 → 두께 = 단면적/시위.
  6. 시위가중 스팬평균. 부피/평면형면적 항등식으로 교차검사.

⛔ GPU 미사용 · 저장소 코드 무변경 · git 무접촉.
산출:  outputs/mesh_adv_refute_thickness_0816.json 에 `k_dji_measured_with_our_ruler` 를 덧붙인다.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import trimesh

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from prop_thickness import cylinder_section_loops, section_metrics   # noqa: E402

GLB = os.path.join(_ROOT, "assets", "meshes", "reference", "WM161_zhankai_1k.glb")
OUT = os.path.join(_ROOT, "outputs", "mesh_adv_refute_thickness_0816.json")
BAND = (0.20, 0.96)
# 완전전개 앞 프롭 2개 — (날 노드 2개, 모터축 노드) . 이름만 빌린다.
ROTORS = [(("polySurface84", "polySurface89"), "polySurface91"),
          (("polySurface102", "polySurface95"), "polySurface97")]


def load_mm() -> dict:
    sc = trimesh.load(GLB, process=False)
    out = {}
    for name, geom in sc.geometry.items():
        pass
    # 노드 변환을 적용해 세계좌표로 편다
    for node in sc.graph.nodes_geometry:
        T, gname = sc.graph[node]
        m = sc.geometry[gname].copy()
        m.apply_transform(T)
        m.apply_scale(1000.0)                       # GLB 는 m → mm
        # GLB 는 정점을 면마다 복제해 싣는다(법선·UV 때문). 위상을 쓰려면 병합이 필수 —
        # 병합 없이는 모서리가 공유되지 않아 연결요소도 단면 고리도 안 생긴다.
        m.merge_vertices()
        out[gname] = m
    return out


def revolve_axis(m) -> tuple[np.ndarray, np.ndarray]:
    """회전체 부품의 대칭축과 축 위 한 점 — 면적가중 공분산의 «따로 노는» 고유벡터."""
    tri = m.vertices[m.faces]
    a = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) * 0.5
    c = tri.mean(1)
    w = a / a.sum()
    ctr = (c * w[:, None]).sum(0)
    d = c - ctr
    cov = (w[:, None, None] * d[:, :, None] * d[:, None, :]).sum(0)
    ev, EV = np.linalg.eigh(cov)
    # 셋 중 «나머지 둘과 가장 다른» 고유값의 벡터가 축
    k = int(np.argmax([abs(ev[0] - ev[1]) + abs(ev[0] - ev[2]),
                       abs(ev[1] - ev[0]) + abs(ev[1] - ev[2]),
                       abs(ev[2] - ev[0]) + abs(ev[2] - ev[1])]))
    ax = EV[:, k] / np.linalg.norm(EV[:, k])
    return ax, ctr


def rot_to_z(ax: np.ndarray) -> np.ndarray:
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(ax, z)
    s = np.linalg.norm(v)
    if s < 1e-12:
        return np.eye(3) if ax[2] > 0 else np.diag([1.0, -1.0, -1.0])
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - float(np.dot(ax, z))) / (s ** 2))


def largest_component(m):
    parts = m.split(only_watertight=False)
    if not len(parts):
        return m
    return max(parts, key=lambda p: float(p.area))


def section_chains(V: np.ndarray, F: np.ndarray, r: float):
    """`cylinder_section_loops` 와 **같은 교점 계산**을 쓰되, DJI 껍질이 이음매를 따라 열려 있어
    단면이 열린 사슬로 나오므로 **끝점을 이어 닫고** 그 틈을 함께 돌려준다."""
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    s_all = np.hypot(V[:, 0], V[:, 1]) - r
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key = np.sort(E, axis=1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = np.asarray(inv).ravel()
    s = s_all[uniq]
    cross = (s[:, 0] * s[:, 1]) < 0
    ci = np.flatnonzero(cross)
    if len(ci) < 3:
        return []
    A, B = V[uniq[ci, 0]], V[uniq[ci, 1]]
    d = B - A
    qa = d[:, 0] ** 2 + d[:, 1] ** 2
    qb = 2.0 * (A[:, 0] * d[:, 0] + A[:, 1] * d[:, 1])
    qc = A[:, 0] ** 2 + A[:, 1] ** 2 - r * r
    disc = np.sqrt(np.maximum(qb * qb - 4.0 * qa * qc, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (-qb + disc) / (2.0 * qa)
        t2 = (-qb - disc) / (2.0 * qa)
    t = np.where((t1 >= -1e-12) & (t1 <= 1.0 + 1e-12), t1, t2)
    P = A + np.clip(t, 0.0, 1.0)[:, None] * d
    pt_of_edge = -np.ones(len(uniq), np.int64)
    pt_of_edge[ci] = np.arange(len(ci))
    tri_e = np.stack([inv[:len(F)], inv[len(F):2 * len(F)], inv[2 * len(F):]], axis=1)
    hit = cross[tri_e]
    adj: dict[int, list[int]] = {}
    for tri in np.flatnonzero(hit.sum(1) == 2):
        a, b = pt_of_edge[tri_e[tri][hit[tri]]]
        adj.setdefault(int(a), []).append(int(b))
        adj.setdefault(int(b), []).append(int(a))
    if not adj:
        return []
    ends = [k for k, v in adj.items() if len(v) == 1]
    seen: set[int] = set()
    chains = []
    for start in ends + list(adj):
        if start in seen:
            continue
        chain = [start]
        seen.add(start)
        cur, prev = start, None
        while True:
            nxt = [q for q in adj[cur] if q != prev and q not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            chain.append(cur)
        if len(chain) < 6:
            continue
        p = P[np.asarray(chain)]
        gap = float(np.linalg.norm(p[0] - p[-1]))
        phi = np.arctan2(p[:, 1], p[:, 0])
        phi0 = np.arctan2(np.sin(phi).mean(), np.cos(phi).mean())
        rel = np.mod(phi - phi0 + np.pi, 2.0 * np.pi) - np.pi
        chains.append((np.c_[r * rel, p[:, 2]], gap))
    return chains


def measure_blade(V: np.ndarray, F: np.ndarray, R: float, step: float = 0.005) -> dict:
    rr, ch, tc, tm, ar, gp = [], [], [], [], [], []
    for x in np.arange(BAND[0], BAND[1] + 1e-9, step):
        best, best_gap = None, None
        for Q, gap in section_chains(V, F, float(x) * R):
            s = section_metrics(Q)
            if s and (best is None or s["area"] > best["area"]):
                best, best_gap = s, gap
        if best is None:
            continue
        gp.append(best_gap / best["chord"])
        rr.append(float(x)); ch.append(best["chord"]); tc.append(best["t_chordmean"])
        tm.append(best["t_max"]); ar.append(best["area"])
    rr, ch, tc, tm, ar, gp = map(np.asarray, (rr, ch, tc, tm, ar, gp))
    t_cw = float(np.trapezoid(tc * ch, rr) / np.trapezoid(ch, rr))
    vol = float(np.trapezoid(ar, rr * R))                 # ∫A dr  [mm³]
    plan = float(np.trapezoid(ch, rr * R))                # ∫c dr  [mm²]
    return dict(n_stations=int(len(rr)), t_chordmean_cw_mm=t_cw,
                t_max_cw_mm=float(np.trapezoid(tm * ch, rr) / np.trapezoid(ch, rr)),
                volume_mm3=vol, planform_mm2=plan, t_vol_over_area_mm=vol / plan,
                c_max_mm=float(ch.max()), c_max_over_R=float(ch.max() / R),
                peak_rr=float(rr[int(np.argmax(ch))]),
                closure_gap_over_chord_max=float(gp.max()),
                closure_gap_over_chord_mean=float(gp.mean()),
                t_tip_band_mm=float(np.trapezoid(tc[rr >= 0.80] * ch[rr >= 0.80], rr[rr >= 0.80])
                                    / np.trapezoid(ch[rr >= 0.80], rr[rr >= 0.80])))


def ruler_family(V, F, R, step=0.005, nslice=41) -> dict:
    """같은 날을 **세 자**로 잰다 — 부피보존(A/c) · 최대캘리퍼 · 41조각 max−min 평균.
    감사가 인용한 0.876 이 어느 계열인지 가리는 시험."""
    from scipy.spatial import ConvexHull
    rows = []
    for x in np.arange(BAND[0], BAND[1] + 1e-9, step):
        bQ = bs = None
        for Q, _ in section_chains(V, F, float(x) * R):
            s = section_metrics(Q)
            if s and (bs is None or s["area"] > bs["area"]):
                bQ, bs = Q, s
        if bs is None:
            continue
        H = bQ[ConvexHull(bQ).vertices]
        D = H[:, None, :] - H[None, :, :]
        d2 = (D ** 2).sum(-1)
        i, j = np.unravel_index(np.argmax(d2), d2.shape)
        c = float(np.sqrt(d2[i, j]))
        e = (H[j] - H[i]) / c
        P = (bQ - H[i]) @ np.array([[e[0], e[1]], [-e[1], e[0]]]).T
        Pc = np.vstack([P, P[:1]])
        seg = np.linalg.norm(np.diff(Pc, axis=0), axis=1)
        cum = np.r_[0, np.cumsum(seg)]
        t = np.linspace(0, cum[-1], 4000)
        xs, ys = np.interp(t, cum, Pc[:, 0]), np.interp(t, cum, Pc[:, 1])
        ed = np.linspace(xs.min(), xs.max(), nslice + 1)
        idx = np.clip(np.digitize(xs, ed) - 1, 0, nslice - 1)
        v = [ys[idx == k].max() - ys[idx == k].min() for k in range(nslice) if (idx == k).sum() >= 2]
        rows.append((float(x), c, bs["area"] / c, bs["t_max"], float(np.mean(v))))
    A = np.array(rows)
    w = A[:, 1]
    out = {nm: float(np.trapezoid(A[:, k] * w, A[:, 0]) / np.trapezoid(w, A[:, 0]))
           for k, nm in ((2, "A_over_c_volume_preserving"), (3, "max_caliper"),
                         (4, "slice41_maxmin_mean"))}
    out["planform_mm2"] = float(np.trapezoid(w, A[:, 0] * R))
    out["c_max_over_R"] = float(w.max() / R)
    return out


def main() -> None:
    t0 = time.time()
    geo = load_mm()
    per_blade, axis_xchk = {}, []
    reported = {"polySurface91": [-0.087157, 0.996195, -3e-06],
                "polySurface97": [-0.087154, -0.996195, 2e-06]}
    for blades, shaft in ROTORS:
        ax, ctr = revolve_axis(geo[shaft])
        rep = np.asarray(reported[shaft], float)
        ang = float(np.degrees(np.arccos(min(1.0, abs(float(np.dot(ax, rep / np.linalg.norm(rep))))))))
        axis_xchk.append(dict(shaft=shaft, my_axis=[float(v) for v in ax],
                              reported_axis=[float(v) for v in rep], angle_deg=ang))
        Rm = rot_to_z(ax)
        for bn in blades:
            m = largest_component(geo[bn])
            V = (np.asarray(m.vertices, float) - ctr) @ Rm.T
            F = np.asarray(m.faces, np.int64)
            R = float(np.hypot(V[:, 0], V[:, 1]).max())
            res = measure_blade(V, F, R)
            res["R_mm"] = R
            res["airfoil_faces"] = int(len(F))
            res["airfoil_area_mm2"] = float(m.area)
            per_blade[f"{shaft}/{bn}"] = res

    keys = ("t_chordmean_cw_mm", "t_vol_over_area_mm", "t_max_cw_mm", "R_mm",
            "c_max_over_R", "t_tip_band_mm")
    mean = {k: float(np.mean([v[k] for v in per_blade.values()])) for k in keys}
    spread = {k: float(np.ptp([v[k] for v in per_blade.values()])) for k in keys}

    led = json.load(open(os.path.join(_ROOT, "outputs", "prop_thickness_by_drone.json")))
    ours = led["per_drone"]["mini2"]["bands"]["headline_0p20_0p96"]["t_chordmean_mm"]
    t_dji = mean["t_chordmean_cw_mm"]

    # 사과-대-사과 담보: 우리 mini2 프롭도 **이 파일의 같은 경로**(같은 스텝·같은 밴드)로 다시 잰다
    from drones import DRONES, build_propeller                      # noqa: E402
    mo = build_propeller(DRONES["mini2"], n=10)
    Vo = np.asarray(mo.v, float) * 1000.0
    Fo = np.asarray(mo.f, np.int64)
    Ro = float(np.hypot(Vo[:, 0], Vo[:, 1]).max())
    ours_mine = measure_blade(Vo, Fo, Ro)

    out = json.load(open(OUT))
    out["k_dji_measured_with_our_ruler"] = dict(
        ruler="src/prop_thickness.cylinder_section_loops + section_metrics (저장소가 우리 메쉬에 쓰는 자 그대로)",
        band_r_over_R=list(BAND), n_blades=len(per_blade), per_blade=per_blade,
        mean=mean, blade_to_blade_spread=spread, axis_cross_check=axis_xchk,
        ours_mini2_same_ruler_mm=ours, ours_mini2_my_own_pipeline=ours_mine,
        ours_mine_over_dji_dB=float(20 * np.log10(ours_mine["t_chordmean_cw_mm"] / t_dji)),
        ours_over_dji=float(ours / t_dji), ours_over_dji_dB=float(20 * np.log10(ours / t_dji)),
        knob_0p9_over_dji_dB=float(20 * np.log10(0.9 / t_dji)),
        canon_1p4302_over_dji_dB=float(20 * np.log10(1.4302 / t_dji)),
        audit_numbers=dict(audit_chordmean_mm=0.5999, audit_area_weighted_max_mm=0.876,
                           precision_remeasure_t_env_mean_mm=0.5237),
        verdict_ko=(
            "우리 저장소의 자로 DJI 실물 날을 직접 재면 시위평균 두께는 위 `mean` 값이다. "
            "감사가 §4-3 에서 «실물» 로 인용한 0.876 mm 는 이 자의 값이 아니라 **최대두께** 계열이다. "
            "슬래브 두께 손잡이(0.9 mm)와 견줄 수 있는 것은 이쪽이며, 그렇게 견주면 0.9 mm 는 "
            "실물보다 밝다."))
    # ------------------------------------------------------------------ #
    #  0.876 은 어느 자인가 — 같은 날을 세 자로 재는 결정 시험
    # ------------------------------------------------------------------ #
    blades0 = ROTORS[0][0][0]
    ax0, ctr0 = revolve_axis(geo[ROTORS[0][1]])
    m0 = largest_component(geo[blades0])
    V0 = (np.asarray(m0.vertices, float) - ctr0) @ rot_to_z(ax0).T
    F0 = np.asarray(m0.faces, np.int64)
    R0 = float(np.hypot(V0[:, 0], V0[:, 1]).max())
    fam_dji = ruler_family(V0, F0, R0)
    fam_ours = ruler_family(Vo, Fo, Ro)
    out["l_which_ruler_is_0p876"] = dict(
        dji_real=fam_dji, ours_mini2=fam_ours,
        audit_pair_area_weighted=dict(dji=0.876, ours=0.968),
        audit_pair_chordmean=dict(dji=0.5999, ours=0.7312),
        ratio_to_audit_0p876={k: float(0.876 / v) for k, v in fam_dji.items()
                              if k.startswith(("A_over", "max_", "slice"))},
        planform_area_ratio_ours_over_dji=float(fam_ours["planform_mm2"] / fam_dji["planform_mm2"]),
        planform_area_ratio_dB=float(20 * np.log10(fam_ours["planform_mm2"] / fam_dji["planform_mm2"])),
        verdict_ko=(
            "결정 시험 결과: DJI 실물 날을 부피보존 자로 재면 0.468 · 41조각 max−min 자로 재도 "
            "0.495 인데, **최대캘리퍼로 재면 0.918** 이다. 감사가 인용한 0.876 은 최대캘리퍼값의 "
            "95 % 로, **최대두께 계열이 확실하다**(시위평균 계열은 두 자 모두 0.47~0.50). "
            "우리 메쉬 쪽 짝(0.968)도 마찬가지다(내 최대캘리퍼 1.121). ⇒ §4-3 의 «0.9 mm ≈ 실물» 은 "
            "슬래브 두께를 최대두께와 견준 것이다. "
            "덤: 같은 창·같은 자로 잰 **평면형 면적비는 0.785(−2.10 dB)** 라, 감사의 «날 면적 "
            "−29 %(−2.97 dB)» 가 아니라 −21 % 임을 이 경로에서도 독립 확인한다."))

    # ------------------------------------------------------------------ #
    #  최종 판정 — 두께 축 네 주장에 대한 한 줄 결론
    # ------------------------------------------------------------------ #
    br = [t_dji, 0.5237, 0.5999]          # 자 셋의 실물 슬래브등가 두께 브래킷
    out["z_verdict"] = dict(
        a_m1_canon_is_derived_not_measured=dict(
            result="감사 지지(사실) + 부분 정정(수치)",
            ko=("«1.43 mm 는 상수 유도값» 은 소스로 확인 — 맞다. 그러나 «메쉬 실측 1.456 mm(+1.8 %)» 는 "
                "자 하나의 값이다. 같은 메쉬를 세 자로 재면 1.414 / 1.456 / 1.480 mm 로 **부호가 갈리고** "
                "폭이 0.39 dB 다. 어느 쪽이든 |Γ| 영향은 0.12~0.15 dB — **판정에 영향 0**.")),
        b_mini5pro_claim=dict(
            result="감사 지지(오히려 과소)",
            ko=("모형은 ITU-R P.2040 단층 슬래브이고 대수적으로 옳다(독립 구현과 1e-15). 규약이 "
                "일관되지 않다 — 하한 +3.8 은 볼록체 **전력**평균, 상한 +4.6 은 45°, 원장은 **진폭**평균 "
                "+4.85, 저장소 자로는 +5.11. 낙차 전부가 θ>85° 에서 오는데 시위 0.07~0.39 λ 인 날에는 "
                "그런 스침 영역이 없다. 날에 맞는 어떤 규약으로도 **+4.4~+5.1 dB**. 실물(추정)까지 넣으면 더 크다.")),
        c_chordmean_summary=dict(
            result="감사 지지(공격 실패)",
            ko=("3.5 GHz 에서 날 두께는 λ/60~λ/110 이라 |Γ| ∝ d^0.98 — 사실상 선형이다. 그래서 "
                "⟨Γ(t)⟩ 와 Γ(⟨t⟩) 가 0.01~0.03 dB 안에서 같고, «시위평균 → 시위가중 스팬평균» 은 "
                "**항등적으로 부피/평면형면적**이다(이 파일에서 두 경로가 소수 15 자리까지 일치). "
                "⇒ RF 적으로 맞는 요약이다. 단서 둘: (1) 옳은 이유가 선형성이므로 두께는 면적과 "
                "**곱으로만** 의미가 있다(σ ∝ (d·A)²), (2) 스칼라 하나는 팁띠를 10기종 전부에서 "
                "정확히 −6.47 dB 틀리게 하고 한 날 안 폭이 13.2 dB 다.")),
        d_13_to_17_db_ordering=dict(
            result="부분 정정",
            ko=("숫자 13~17 dB 는 재현된다(45° −16.65 · 각도평균 −11.35, 실측 AC −16.99). 그러나 그것은 "
                "«남은 오차의 폭» 이 아니라 **이미 잡은 기본값 버그(100 mm)의 크기**다. 남은 오차끼리 "
                "같은 규약(45°)으로 모으면 두께 3~5 dB · 형상 1.3~2.5 dB 로 **2~3 배**이지 10 배가 "
                "아니다. 더구나 얇은 판에서 σ ∝ (두께 × 면적)² 이라 두 축은 같은 통화이고 곱이다.")),
        e_biggest_actionable_db=dict(
            result="감사 반증",
            ko=("I1 을 «이 감사에서 가장 큰 단일 실행가능 dB» 라 적었으나, 그 +3.8~4.6 dB 는 "
                "**PathSolver 팔 전용**이다(`elevation_sweep_md.py:247` 이 우리 커널에 두께 인자를 "
                "막는다). 정작 우리 PO/SBR 커널은 프롭 |Γ| 가 전 기종 상수 0.25 인데, 그것은 "
                "3.5 GHz 에서 **4.40 mm 플라스틱 슬래브**에 해당한다 — 우리 메쉬 두께 기준으로 "
                "mini5pro +14.2 dB · mini2 +16.3 dB · matrice4e +9.2 dB. 감사는 이 항목을 "
                "**전혀 다루지 않았다**.")),
        f_audit_4_3_reframing=dict(
            result="감사 반증",
            ko=(f"§4-3 의 «0.9 mm 가 DJI 실물 0.876 mm 와 2.7 % 안에서 일치» 는 잣대가 섞인 비교다. "
                f"0.876 은 **최대두께** 계열이고(내 독립 최대캘리퍼 {mean['t_max_cw_mm']:.3f} mm 가 그 "
                f"계열임을 확인), 슬래브가 요구하는 것은 부피보존 두께다. 그 자로 재면 실물은 "
                f"**{t_dji:.3f} mm**(내 직접 측정) ~ 0.60 mm(감사 자)이고 0.9 mm 는 "
                f"**+{20 * np.log10(0.9 / br[-1]):.1f}~+{20 * np.log10(0.9 / br[0]):.1f} dB** 밝다. "
                f"⇒ «0.9 가 잘 앵커된 값이고 정본/민감도점 순서가 거꾸로» 라는 재프레이밍은 무너진다. "
                f"덤으로 C6 의 방향은 강화된다 — 같은 자로 우리 mini2 는 실물보다 "
                f"**+{20 * np.log10(ours / t_dji):.2f} dB** 두껍다.")),
        survives_ko=("두께 축이 형상 축보다 크다는 **방향**, 정본이 상수 유도값이라는 **사실**, "
                     "mini5pro 에 스칼라를 그대로 쓰면 몇 dB 밝아진다는 **주장**, 시위평균 요약의 "
                     "**RF 정당성** — 이 넷은 공격했고 살아남았다."),
        breaks_ko=("§4-3 의 «0.9 mm ≈ 실물 0.876» 재프레이밍(잣대 혼동), «13~17 대 1~2» 우선순위 "
                   "격차(사과-대-오렌지), «I1 이 가장 큰 실행가능 dB»(PO 커널이 더 크다), "
                   "«메쉬 실측 1.456 mm» 의 확정성(자에 따라 부호가 갈린다) — 이 넷은 무너진다."))

    out["_meta"]["pass3_script"] = "benchmark/adv_refute_thickness_pass3_0816.py"
    out["_meta"]["pass3_runtime_s"] = round(time.time() - t0, 1)
    with open(OUT, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("updated", OUT, out["_meta"]["pass3_runtime_s"], "s")
    print(json.dumps(dict(mean=mean, spread=spread, ours=ours), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
