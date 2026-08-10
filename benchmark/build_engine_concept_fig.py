# -*- coding: utf-8 -*-
"""
build_engine_concept_fig.py — **세 엔진이 각각 무엇을 계산하는지** 그림 한 장으로 설명한다.

왜 이 그림이 필요한가 (사용자 지적, 2026-08-11 팀미팅 준비)
------------------------------------------------------------
결과 그림(report07_f5)은 세 열을 나란히 놓는다:
    ① Sionna PathSolver   ② Ours (SBR+PO, default)   ③ Ours w/o occlusion (control)
그런데 **청중은 그 세 열이 무엇인지 모른다.** 특히
  · path solver 로 어떻게 마이크로도플러 맵이 나오는지,
  · SBR+PO 가 무엇을 쏘고 무엇을 더하는지,
  · «w/o occlusion» 이 무슨 뜻인지(= 드론 일부만 그린 게 **아니다**)
가 그림만 보고는 읽히지 않는다. 이 스크립트는 그 셋을 **도식**으로 만든다.

그림에서 읽혀야 하는 것 (열마다 «무엇을 쏘나 → 무엇을 세나 → 무엇이 빠지나»)
  ① 송신점에서 광선 표본을 뿌리고, 수신점까지 되돌아온 것만 **경로**가 된다.
     경로는 몇 개 안 된다(R=3 m 에서 자세당 중앙값 5개). h = Σ a_p·exp(−j2πf_c·τ_p).
  ② 표적에 **평면파 광선 격자**(λ/DEFAULT_DIV)를 앵커한다. **첫 히트만** 적분하므로
     가림이 공짜로 따라온다. E = Σ_hit |Γ(θ)|·e^{j2k p·û}·d².
  ③ 광선을 아예 안 쓴다. **같은 메쉬의 모든 면**을 더하고, 법선이 등진 면(n̂·û≤0)만 뺀다.
     즉 남의 뒤에 숨은 면도 그대로 셈에 들어간다 — **물리적으로 불가능한 대조군**이다.

⚠ 정직 표시(캡션): ②와 ③은 «가림» 말고도 **이산화**(광선격자 ↔ 표면 점구름)와
   **각도의존 |Γ(θ)|**(②는 켜짐, ③은 꺼짐)가 함께 다르다. 둘의 차이는 «가림만» 의 값이 아니다.

코드에서 확인한 사실 (추측 아님 — 전부 원본 파일에서 읽었다)
  · src/rcs_sbr.py       DEFAULT_DIV = 12  → 광선 격자 간격 λ/12 (3.5 GHz 에서 7.14 mm)
                         sbr_field(): first-hit + (n̂·û>1e-6), E = Σ|Γ|·gamma_shape(θ)·e^{j2k(p−ctr)·û}·d²
                         (n̂·û) obliquity 는 **없다** — 투영면 변수변환에서 상쇄된다.
  · src/rcs_po.py        po_field_dir(): E = Σ_{n̂·û>0} |Γ|·(n̂·û)·ΔA·e^{j2k p·û}. 가림 없음.
  · src/microdoppler.py  microdoppler_series(): 프롭 점구름 λ/11, 프레임 점구름 λ/6,
                         angle_gamma 기본 False (report07 호출은 안 넘긴다 → 꺼짐)
  · benchmark/report15_probe.py  place(): Tx/Rx 를 표적에서 rng·û 에 놓는다(기선 인자).
                         unpack(): a 는 패스밴드 → h = Σ a·exp(−j2πf_c·τ) 로 위상을 얹는다.
  · benchmark/report07_three_engine_maps.py  Sionna 팔: max_depth=1, los=True,
                         specular+diffuse, refraction=False, spp=1e6, 그리고 **표적과
                         상호작용한 경로만**(O != NO_OBJ) 남긴다 → 직접파(LOS)는 버린다.

수치는 실행 시점에 outputs/*.json 과 소스에서 읽는다(하드코딩 금지, 하우스 규약).
그림 안 텍스트는 전부 **영어**, 세미콜론·대시 금지.

    python benchmark/build_engine_concept_fig.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
import numpy as np                                                       # noqa: E402
from matplotlib.patches import FancyArrowPatch, Polygon                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTD = os.path.join(ROOT, "outputs", "figures")
STEM = os.path.join(OUTD, "deck0811_concept")

C0 = 299792458.0

# ─────────────────────────────────────────────────────────────────────────── #
#  1. 실행 시점 사실 수집 — JSON 원장 + 소스 상수 (하드코딩 금지)
# ─────────────────────────────────────────────────────────────────────────── #


def _grab(path, pattern, what):
    """소스 파일에서 상수 하나를 정규식으로 뽑는다. 못 찾으면 **예외**(조용한 거짓 방지)."""
    src = open(path, encoding="utf-8").read()
    m = re.search(pattern, src, re.M)
    if not m:
        raise RuntimeError(f"{os.path.relpath(path, ROOT)} 에서 {what} 를 못 찾았다 — "
                           f"소스가 바뀌었으면 이 스크립트의 정규식을 고쳐야 한다.")
    return m.group(1)


def facts():
    J3 = json.load(open(f"{ROOT}/outputs/report07_three_engines.json", encoding="utf-8"))
    JR = json.load(open(f"{ROOT}/outputs/report07_three_engine_ranges.json", encoding="utf-8"))
    R3 = JR["ranges"]["R3"]

    div = int(_grab(f"{ROOT}/src/rcs_sbr.py", r"^DEFAULT_DIV\s*=\s*(\d+)", "DEFAULT_DIV"))
    po_blade = float(_grab(f"{ROOT}/src/microdoppler.py",
                           r"spacing\s*=\s*spacing\s*or\s*lam\s*/\s*([\d.]+)",
                           "프롭 점구름 간격"))
    po_frame = float(_grab(f"{ROOT}/src/microdoppler.py",
                           r"mesh_to_points\(build_frame\(spec\),\s*lam\s*/\s*([\d.]+)",
                           "프레임 점구름 간격"))

    #  ⚠ 열 제목은 결과 그림(report07_f5)과 **글자까지 같아야** 청중이 두 그림을 잇는다.
    #    그래서 하드코딩하되 원본에 그 문자열이 실재하는지 검사한다.
    titles = ["Sionna PathSolver", "Ours (SBR+PO, default)", "Ours w/o occlusion (control)"]
    ref = open(f"{ROOT}/benchmark/build_three_engine_fig.py", encoding="utf-8").read()
    for t in titles:
        if t not in ref:
            raise RuntimeError(f"열 제목 {t!r} 이 build_three_engine_fig.py 에 없다 — "
                               f"결과 그림의 라벨이 바뀌었다. 개념도도 같이 고칠 것.")

    fc = float(J3["_meta"]["fc_hz"])
    return dict(titles=titles, fc=fc, lam=C0 / fc, div=div,
                po_blade=po_blade, po_frame=po_frame,
                spp=int(R3["spp"]), paths_med=float(R3["paths_median"]),
                paths_zero=float(R3["paths_zero_frac"]), rng=float(R3["range_m"]),
                drone=J3["_meta"]["name"])


def ray_grid_extent(lam, div):
    """SBR 광선 격자가 자세당 몇 발인가 — 실제 메쉬로 센다(GPU 불필요, 순수 numpy).

    rcs_sbr.sbr_field 와 **같은 식**: Rout = max|V−ctr|·1.15 + 3d, n = ceil(2·Rout/d), 광선 n².
    로터 위상에 따라 경계구가 조금 달라지므로 한 블레이드 주기를 훑어 (min, max) 를 준다.
    실패하면 None — 숫자를 지어내지 않는다."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "src"))
        from articulated_fast import FastPoser
        from drones import DRONES
        spec = DRONES["matrice4e"]
        fp = FastPoser(spec)
        d = lam / div
        ns, dia = [], 0.0
        for phi in np.linspace(0.0, 180.0, 7):
            V = np.asarray(fp.pose(np.full(len(fp.dirs), phi)).v, float)
            ctr = 0.5 * (V.max(0) + V.min(0))
            r = float(np.linalg.norm(V - ctr, axis=1).max())
            dia = max(dia, 2.0 * r)
            ns.append(int(np.ceil(2 * (r * 1.15 + 3 * d) / d)) ** 2)
        return min(ns), max(ns), dia
    except Exception as exc:                                  # noqa: BLE001
        print(f"  ⚠ 광선 수 계산 실패({exc}) — 그림에서 그 라벨을 뺀다.")
        return None


# ─────────────────────────────────────────────────────────────────────────── #
#  2. 도식용 기하 — 초타원(superellipse) 하나로 동체·팔·로터를 다 그린다
# ─────────────────────────────────────────────────────────────────────────── #
ANG = 10.0                                    # 조명 방향(그림 좌표계에서 오른쪽 위로)
DVEC = np.array([np.cos(np.radians(ANG)), np.sin(np.radians(ANG))])   # 전파 방향
PVEC = np.array([-DVEC[1], DVEC[0]])          # 그에 수직
UHAT = -DVEC                                  # û = 표적 → 레이더


def _rot(a_deg):
    a = np.radians(a_deg)
    return np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])


def shp(c, a, b, p=2.0, rot=0.0):
    return dict(c=np.asarray(c, float), a=float(a), b=float(b), p=float(p), rot=float(rot))


def bar(p0, p1, half_w):
    """두 점을 잇는 얇은 막대(팔·다리) — 초타원 p=4 로 만든다."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    v = p1 - p0
    return shp(0.5 * (p0 + p1), 0.5 * np.linalg.norm(v), half_w, 4.0,
               np.degrees(np.arctan2(v[1], v[0])))


def boundary(s, n=400):
    """경계점 + **바깥 법선**."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    e = 2.0 / s["p"]
    xl = s["a"] * np.sign(ct) * np.abs(ct) ** e
    yl = s["b"] * np.sign(st) * np.abs(st) ** e
    gx = np.sign(xl) * np.abs(xl / s["a"]) ** (s["p"] - 1) / s["a"]
    gy = np.sign(yl) * np.abs(yl / s["b"]) ** (s["p"] - 1) / s["b"]
    R = _rot(s["rot"])
    P = (R @ np.stack([xl, yl])).T + s["c"]
    N = (R @ np.stack([gx, gy])).T
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    return P, N


def inside(s, P):
    q = (_rot(-s["rot"]) @ (np.atleast_2d(P) - s["c"]).T).T
    return (np.abs(q[:, 0] / s["a"]) ** s["p"] + np.abs(q[:, 1] / s["b"]) ** s["p"]) <= 1.0


def entries(shapes, o, dvec, tmax=14.0, nstep=1600, t0=0.0):
    """광선이 어느 지점에서 **물체 안으로 들어가는가** — (t, shape_idx) 목록(진입 순서)."""
    ts = np.linspace(t0, tmax, nstep)
    P = np.asarray(o, float)[None, :] + ts[:, None] * np.asarray(dvec, float)[None, :]
    occ = np.full(nstep, -1, int)
    for i, s in enumerate(shapes):
        m = inside(s, P)
        occ = np.where(m & (occ < 0), i, occ)
    ins = occ >= 0
    out = []
    for i in range(1, nstep):
        if ins[i] and not ins[i - 1]:
            out.append((float(ts[i]), int(occ[i])))
    if ins[0]:
        out.insert(0, (float(ts[0]), int(occ[0])))
    return out


def shadowed(shapes, P, self_idx, eps=0.03):
    """점 P 가 **다른 부품에 가려져 있는가** — û(레이더 쪽)로 그림자광선 1발."""
    out = np.zeros(len(P), bool)
    others = [s for j, s in enumerate(shapes) if j != self_idx]
    for i, q in enumerate(P):
        out[i] = len(entries(others, q + eps * UHAT, UHAT, tmax=12.0, nstep=900)) > 0
    return out


#  도식 기체 — 실제 메쉬가 아니라 **읽히는 실루엣**이다(캡션에 도식이라고 밝힌다).
BODY = shp((6.20, 3.05), 1.05, 0.50, 4.0)
GIMB = shp((5.28, 2.53), 0.19, 0.19, 2.0)
ARM_N = bar((5.55, 2.72), (4.45, 1.80), 0.060)
ROT_N = shp((4.18, 1.62), 0.75, 0.075, 2.0, -10.0)
ARM_F = bar((7.15, 3.28), (8.40, 3.55), 0.060)
ROT_F = shp((8.88, 3.62), 0.90, 0.080, 2.0, -8.0)
SHAPES = [BODY, GIMB, ARM_N, ROT_N, ARM_F, ROT_F]
HIDDEN_IDX = {4, 5}                            # 동체 뒤에 놓인 팔·로터(대조군에서 붉게)

XLIM, YLIM = (0.15, 10.75), (0.30, 5.55)

INK = "#1b1f24"
GRAY = "#6b7480"
FILL = "#dde3e9"
EDGE = "#7a848f"
SHADOW = "#9aa4ae"
BLUE = "#1f5fbf"
GREEN = "#127a4e"
RED = "#c1121f"
ACC = [BLUE, GREEN, RED]


def draw_target(ax, lw=1.5):
    for s in SHAPES:
        P, _ = boundary(s, 300)
        ax.fill(P[:, 0], P[:, 1], facecolor=FILL, edgecolor=EDGE, lw=lw, zorder=3)


def shadow_band(ax, alpha=0.30, color=SHADOW, length=6.0):
    """동체가 만드는 그림자 띠 — 가림을 눈에 보이게 한다."""
    P, _ = boundary(BODY, 400)
    pv, dv = P @ PVEC, P @ DVEC
    lo, hi, d0 = pv.min(), pv.max(), dv.max()
    corners = [lo * PVEC + d0 * DVEC, lo * PVEC + (d0 + length) * DVEC,
               hi * PVEC + (d0 + length) * DVEC, hi * PVEC + d0 * DVEC]
    ax.add_patch(Polygon(np.array(corners), closed=True, facecolor=color, alpha=alpha,
                         edgecolor="none", zorder=1))


def frame(ax, title, color):
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#c7ced5")
        sp.set_linewidth(1.1)
    ax.set_title(title, color=color, fontweight="bold", pad=9)


# ─────────────────────────────────────────────────────────────────────────── #
#  3. 열마다 그림
# ─────────────────────────────────────────────────────────────────────────── #
def panel_sionna(ax, F):
    """송신점에서 광선 표본을 뿌리고, 표적을 거쳐 수신점까지 온 것만 경로가 된다."""
    radar = np.array([0.85, 1.95])
    draw_target(ax)

    #  버려지는 표본들 — 표적을 못 맞히고 지나간다(1e6 발의 대부분).
    base = np.degrees(np.arctan2(*(BODY["c"] - radar)[::-1]))
    for a in np.linspace(base - 26, base + 26, 46):
        v = np.array([np.cos(np.radians(a)), np.sin(np.radians(a))])
        ax.plot(*np.array([radar, radar + 11.5 * v]).T, color=BLUE, lw=0.55,
                alpha=0.13, zorder=2)

    #  살아남은 경로 — 왕복 화살표. 히트점은 실제 실루엣과의 첫 교차로 잡는다.
    aims = [ROT_N["c"] + np.array([0.42, 0.05]), GIMB["c"], BODY["c"] + np.array([-0.72, -0.30]),
            BODY["c"] + np.array([-0.55, 0.34]), ROT_N["c"] + np.array([-0.48, 0.02])]
    n_drawn = 0
    for aim in aims:
        v = aim - radar
        v = v / np.linalg.norm(v)
        ent = entries(SHAPES, radar, v, tmax=12.0)
        if not ent:
            continue
        hit = radar + ent[0][0] * v
        ax.add_patch(FancyArrowPatch(radar, hit, arrowstyle="<|-|>", mutation_scale=11,
                                     lw=1.7, color=BLUE, alpha=0.95, zorder=5,
                                     shrinkA=6, shrinkB=0))
        ax.plot(*hit, "o", ms=6.0, mfc=BLUE, mec="white", mew=1.0, zorder=6)
        n_drawn += 1

    #  레이더 아이콘
    ax.add_patch(Polygon(np.array([radar + [-0.30, -0.30], radar + [0.30, -0.30],
                                   radar + [0.0, 0.34]]), closed=True,
                         facecolor=BLUE, edgecolor="white", lw=1.2, zorder=7))
    ax.text(radar[0], radar[1] - 0.62, "Tx / Rx", ha="center", va="top", color=BLUE,
            fontweight="bold", zorder=7)

    ax.annotate(f"median {F['paths_med']:.0f} paths per pose",
                xy=(BODY["c"][0] - 1.0, BODY["c"][1] + 0.55), xytext=(3.05, 4.85),
                color=BLUE, fontweight="bold", ha="left", va="center", zorder=8,
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.4))
    ax.text(0.62, 4.85, f"{F['spp']:.0e}".replace("e+0", r"$\times 10^{") + r"}$"
            + " ray samples,", color=GRAY, ha="left", va="center")
    ax.text(0.62, 4.45, "almost all of them miss", color=GRAY, ha="left", va="center")

    ax.text(5.45, 0.72, r"$h=\sum_p a_p\,e^{-j2\pi f_c \tau_p}$", ha="center", va="center",
            color=INK, fontsize=plt.rcParams["font.size"] + 3.5, zorder=9)
    return n_drawn


def panel_sbr(ax, F):
    """평면파 광선 격자 → **첫 히트만** 적분. 가림이 공짜로 따라온다."""
    shadow_band(ax)
    draw_target(ax)

    c_p, c_d = BODY["c"] @ PVEC, BODY["c"] @ DVEC
    svals = np.linspace(c_p - 2.55, c_p + 1.75, 25)
    start_d = c_d - 5.5
    n_hit = n_block = 0
    for i, s in enumerate(svals):
        o = s * PVEC + start_d * DVEC
        ent = entries(SHAPES, o, DVEC, tmax=13.0)
        end = o + 12.4 * DVEC
        if not ent:
            ax.plot(*np.array([o, end]).T, color=GREEN, lw=0.8, alpha=0.28, zorder=2)
            continue
        hit = o + ent[0][0] * DVEC
        ax.plot(*np.array([o, hit]).T, color=GREEN, lw=1.15, alpha=0.85, zorder=4)
        ax.plot(*hit, "o", ms=5.2, mfc=GREEN, mec="white", mew=0.9, zorder=6)
        n_hit += 1
        if len(ent) > 1:                       # 첫 히트 뒤의 면들 — 셈에 안 들어간다
            far = o + ent[-1][0] * DVEC
            ax.plot(*np.array([hit, far]).T, color=GRAY, lw=0.8, alpha=0.45,
                    ls=(0, (2.0, 2.0)), zorder=4)
            for t_, _ in ent[1:]:
                q = o + t_ * DVEC
                ax.plot(*q, "x", ms=5.4, mew=1.5, color=GRAY, alpha=0.9, zorder=6)
                n_block += 1
        if i % 4 == 0:                          # 몇 발만 화살표를 붙여 방향을 보인다
            ax.add_patch(FancyArrowPatch(o, o + 0.95 * DVEC, arrowstyle="-|>",
                                         mutation_scale=10, lw=1.3, color=GREEN, zorder=5))

    wf0 = svals[0] * PVEC + (start_d - 0.18) * DVEC
    wf1 = svals[-1] * PVEC + (start_d - 0.18) * DVEC
    ax.plot(*np.array([wf0, wf1]).T, color=GREEN, lw=2.2, alpha=0.75, zorder=3)
    ax.text(0.55, 4.85, "incident plane wave", color=GREEN, fontweight="bold",
            ha="left", va="center")
    ax.text(0.55, 4.45, rf"ray grid $\lambda/{F['div']}$", color=GRAY, ha="left", va="center")

    ax.annotate("first hit only, so what lies\nbehind it drops out",
                xy=(ROT_F["c"][0] - 0.35, ROT_F["c"][1] + 0.02), xytext=(6.35, 5.02),
                color=GRAY, ha="left", va="center", zorder=8,
                arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.3))

    ax.text(5.45, 0.72,
            r"$E=\sum_{\mathrm{hits}}|\Gamma(\theta)|\;e^{\,j2k\,\mathbf{p}\cdot\hat{u}}\;d^{2}$",
            ha="center", va="center", color=INK,
            fontsize=plt.rcParams["font.size"] + 3.5, zorder=9)
    return n_hit, n_block


def panel_control(ax, F):
    """광선 없음. 같은 메쉬의 **모든 면**을 더하고, 등진 면만 뺀다."""
    shadow_band(ax, alpha=0.18)
    draw_target(ax)

    n_lit = n_hid = 0
    for idx, s in enumerate(SHAPES):
        P, N = boundary(s, 300)
        keep = np.arange(0, 300, 7)
        P, N = P[keep], N[keep]
        lit = (N @ UHAT) > 0.0
        hid = np.zeros(len(P), bool)
        if lit.any():
            hid[lit] = shadowed(SHAPES, P[lit], idx)
        vis = lit & ~hid
        blk = lit & hid
        ax.plot(P[~lit, 0], P[~lit, 1], "o", ms=3.6, mfc="none", mec=GRAY, mew=0.9,
                alpha=0.55, zorder=5)
        ax.plot(P[vis, 0], P[vis, 1], "o", ms=5.0, mfc=RED, mec="white", mew=0.8, zorder=6)
        ax.plot(P[blk, 0], P[blk, 1], "o", ms=5.6, mfc=RED, mec="white", mew=0.8, zorder=7)
        n_lit += int(vis.sum())
        n_hid += int(blk.sum())

    ax.text(0.55, 4.85, "no rays are traced", color=RED, fontweight="bold",
            ha="left", va="center")
    ax.text(0.55, 4.45, "every facet of the same mesh", color=GRAY, ha="left", va="center")
    ax.annotate("hidden facets are summed too,\nnot a partial drone",
                xy=(ROT_F["c"][0] - 0.35, ROT_F["c"][1] + 0.02), xytext=(6.20, 5.02),
                color=RED, fontweight="bold", ha="left", va="center", zorder=8,
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.4))
    ax.plot([1.05], [3.62], "o", ms=3.6, mfc="none", mec=GRAY, mew=0.9, zorder=6)
    ax.text(1.28, 3.62, r"back facing, removed", color=GRAY, ha="left", va="center")

    ax.text(5.45, 0.72,
            r"$E=\sum_{\hat{n}\cdot\hat{u}>0}|\Gamma|\,(\hat{n}\cdot\hat{u})\,"
            r"\Delta A\;e^{\,j2k\,\mathbf{p}\cdot\hat{u}}$",
            ha="center", va="center", color=INK,
            fontsize=plt.rcParams["font.size"] + 3.5, zorder=9)
    return n_lit, n_hid


# ─────────────────────────────────────────────────────────────────────────── #
#  4. 조립
# ─────────────────────────────────────────────────────────────────────────── #
def build():
    F = facts()
    rays = ray_grid_extent(F["lam"], F["div"])

    FS = 13.0
    plt.rcParams.update({
        "font.size": FS, "axes.titlesize": FS + 2.5, "font.family": "DejaVu Sans",
        "figure.dpi": 200, "savefig.dpi": 200, "text.color": INK,
        "axes.edgecolor": "#c7ced5", "mathtext.fontset": "dejavusans",
    })

    fig = plt.figure(figsize=(15.2, 6.75))
    gs = fig.add_gridspec(3, 3, height_ratios=[1.00, 0.335, 0.175],
                          hspace=0.10, wspace=0.045,
                          left=0.012, right=0.988, top=0.905, bottom=0.018)

    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]
    for ax, ttl, col in zip(axes, F["titles"], ACC):
        frame(ax, ttl, col)
    n_paths = panel_sionna(axes[0], F)
    n_hit, n_block = panel_sbr(axes[1], F)
    n_lit, n_hid = panel_control(axes[2], F)

    #  «무엇을 쏘나 / 무엇을 세나 / 무엇이 빠지나» — 열마다 세 줄
    ray_txt = (rf"plane wave on a $\lambda/{F['div']}$ ray grid"
               if rays is None else
               rf"plane wave on a $\lambda/{F['div']}$ ray grid, "
               rf"{rays[0]/1000:.0f}k to {rays[1]/1000:.0f}k rays")
    rows = [
        ["ray samples fired from the Tx",
         "the paths that reach the Rx again",
         "the surface integral over the target"],
        [ray_txt,
         "the first hit of every ray",
         "back facing and hidden facets"],
        ["nothing is fired, no ray tracing",
         "every facet of the same mesh, body and rotors",
         "back facing facets only"],
    ]
    keys = ["FIRED", "SUMMED", "LEFT OUT"]
    for i in range(3):
        ax = fig.add_subplot(gs[1, i])
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        for j, (k, v) in enumerate(zip(keys, rows[i])):
            y = 0.80 - 0.335 * j
            ax.text(0.028, y, k, color=GRAY, fontsize=FS - 2.0, fontweight="bold",
                    ha="left", va="center")
            ax.text(0.245, y, v, color=INK, fontsize=FS - 0.5, ha="left", va="center")
        ax.plot([0.02, 0.98], [0.985, 0.985], color=ACC[i], lw=2.4,
                transform=ax.transAxes, clip_on=False, solid_capstyle="butt")

    #  정직 표시 — 도식이라는 것, 그리고 열 사이에 함께 달라진 것들
    foot = fig.add_subplot(gs[2, :])
    foot.set_axis_off()
    bullets = [
        "Schematic of the three kernels, not a computed result. The airframe is a readable "
        "silhouette rather than the simulated mesh.",
        "The two right hand columns differ in more than occlusion. They also differ in "
        rf"discretisation (a $\lambda/{F['div']}$ ray grid against surface point clouds at "
        rf"$\lambda/{F['po_blade']:.0f}$ on the blades and $\lambda/{F['po_frame']:.0f}$ on the "
        r"frame) and in the angle dependent $|\Gamma(\theta)|$, which is on in the middle column "
        "and off in the control. Their gap is therefore not the price of occlusion alone.",
        f"The left column is lit by a point source at {F['rng']:.0f} m while the other two use "
        "an ideal plane wave. The middle column also lets rays through the plastic shell so that "
        "the battery and the board inside are counted.",
    ]
    y = 0.86
    for b in bullets:
        lines = textwrap.fill(b, 168).split("\n")
        foot.text(0.006, y, "•", color=GRAY, fontsize=FS - 2.0, ha="left", va="top")
        foot.text(0.020, y, "\n".join(lines), color=GRAY, fontsize=FS - 2.6,
                  ha="left", va="top", linespacing=1.42)
        y -= 0.30 * len(lines) + 0.06

    fig.suptitle("What each of the three engines actually computes",
                 fontsize=FS + 5.5, fontweight="bold", color=INK, y=0.975)

    os.makedirs(OUTD, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{STEM}.{ext}", facecolor="white", bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)

    from PIL import Image
    w, h = Image.open(f"{STEM}.png").size
    print(f"\n✅ {STEM}.png   {w}×{h} px  (aspect {w/h:.2f})")
    print(f"✅ {STEM}.pdf")
    print(f"  drone       {F['drone']}   fc {F['fc']/1e9:.2f} GHz   λ {F['lam']*100:.2f} cm")
    print(f"  SBR grid    λ/{F['div']} = {F['lam']/F['div']*1000:.2f} mm"
          + ("" if rays is None
             else f"   rays/aspect {rays[0]}~{rays[1]}   target dia {rays[2]:.3f} m"
                  f"   2D²/λ = {2*rays[2]**2/F['lam']:.1f} m"))
    print(f"  PO cloud    blades λ/{F['po_blade']:.0f}, frame λ/{F['po_frame']:.0f}")
    print(f"  Sionna      spp {F['spp']:.0e}, median {F['paths_med']:.0f} paths/pose "
          f"@ R={F['rng']:.0f} m, empty poses {F['paths_zero']:.1%}")
    print(f"  drawn       {n_paths} paths · {n_hit} first hits, {n_block} blocked · "
          f"{n_lit} lit + {n_hid} hidden facets counted in the control")


if __name__ == "__main__":
    build()
