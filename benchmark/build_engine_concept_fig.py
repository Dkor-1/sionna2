# -*- coding: utf-8 -*-
"""
build_engine_concept_fig.py — **세 엔진이 각각 무엇을 계산하는지** 그림 한 장으로 설명한다.

왜 이 그림이 필요한가 (사용자 지적, 2026-08-11 팀미팅 준비)
------------------------------------------------------------
결과 그림(report07_f5·f12)은 세 열을 나란히 놓는다:
    ① Sionna PathSolver   ② Ours (SBR+PO, default)   ③ Ours, nothing blocked (control)
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

⭐ 아래쪽 띠 — 세 열이 내는 것은 **자세당 복소수 하나**뿐이고, 그 다음 슬로타임 격자와 STFT 는
   **세 열이 완전히 같다**. 사용자가 «path solver 로 뭘 어떻게 해서 맵을 그렸냐» 고 물은 자리가
   여기다: 엔진은 한 점(복소수)만 내고, 맵은 그 점들을 시간축에 쌓아 STFT 를 돌린 결과다.

⚠ 정직 표시(캡션): ②와 ③은 «가림» 말고도 **이산화**(광선격자 ↔ 표면 점구름)와
   **각도의존 |Γ(θ)|**(②는 켜짐, ③은 꺼짐)가 함께 다르다. 둘의 차이는 «가림만» 의 값이 아니다.

코드에서 확인한 사실 (추측 아님 — 전부 원본 파일에서 읽었다)
  · src/rcs_sbr.py       DEFAULT_DIV = 12  → 광선 격자 간격 λ/12 (3.5 GHz 에서 7.14 mm)
                         sbr_field(): first-hit + (n̂·û>1e-6), E = Σ|Γ|·gamma_shape(θ)·e^{j2k(p−ctr)·û}·d²
                         (n̂·û) obliquity 는 **없다** — 투영면 변수변환에서 상쇄된다.
                         penetrate=True 가 기본이라 셸을 통과해 내부 금속을 τ=1−|Γ|² 로 가산한다.
  · src/rcs_po.py        po_field_dir(): E = Σ_{n̂·û>0} |Γ|·(n̂·û)·ΔA·e^{j2k p·û}. 가림 없음.
  · src/microdoppler.py  microdoppler_series(): 프롭 점구름 λ/11, 프레임 점구름 λ/6,
                         angle_gamma 기본 False (report07 호출은 안 넘긴다 → 꺼짐)
  · src/drones.py        build_frame() 그룹 = accent·battery·body·camera·canopy·gear·motor·pcb
                         → **대조군 점구름에도 배터리·PCB 가 들어 있다**(가림이 없으니 전액 계상).
  · benchmark/report15_probe.py  place(): Tx/Rx 를 표적에서 rng·û 에 놓는다(기선 인자).
                         unpack(): a 는 패스밴드 → h = Σ a·exp(−j2πf_c·τ) 로 위상을 얹는다.
  · benchmark/report07_three_engine_maps.py  Sionna 팔: max_depth=1, los=True,
                         specular+diffuse, **refraction=False**, spp=1e6, 그리고 **표적과
                         상호작용한 경로만**(O != NO_OBJ) 남긴다.
                         ⭐ refraction=False 라 Sionna 팔은 셸 **안쪽 배터리·PCB 에 닿지 못한다**.
  · src/md_mapstyle.py   auto_periods()=0.45 블레이드 주기, FLASH_HOP=2 — 세 열 공통 STFT 규약.

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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402

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
    titles = ["Sionna PathSolver", "Ours (SBR+PO, default)", "Ours, nothing blocked (control)"]
    ref = open(f"{ROOT}/benchmark/build_three_engine_fig.py", encoding="utf-8").read()
    for t in titles:
        if t not in ref:
            raise RuntimeError(f"열 제목 {t!r} 이 build_three_engine_fig.py 에 없다 — "
                               f"결과 그림의 라벨이 바뀌었다. 개념도도 같이 고칠 것.")

    #  ⭐ 슬로타임 → STFT 규약은 결과 그림이 쓰는 그 모듈에서 **계산해서** 가져온다.
    sys.path.insert(0, os.path.join(ROOT, "src"))
    import md_mapstyle as MS                                            # noqa: N806
    M = J3["_meta"]
    prf, ffl = float(M["prf_hz"]), float(M["f_flash_hz"])
    per = MS.auto_periods(prf, ffl)
    nper = int(round(per * prf / ffl))

    fc = float(M["fc_hz"])
    return dict(titles=titles, fc=fc, lam=C0 / fc, div=div,
                po_blade=po_blade, po_frame=po_frame,
                spp=int(R3["spp"]), paths_med=float(R3["paths_median"]),
                paths_zero=float(R3["paths_zero_frac"]), rng=float(R3["range_m"]),
                drone=M["name"], n_pose=int(M["n"]), prf=prf, f_flash=ffl,
                periods=per, nper=nper, hop=int(MS.FLASH_HOP),
                win_ms=1e3 * int(M["n"]) / prf, seg_ms=1e3 * nper / prf)


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
#  ⚠ 기체는 y ≲ 4.0 안에 둔다. 그 위(4.15~5.5)는 **글자 전용 띠**다 — 예전 판이 이 규칙을
#    안 지켜서 표제와 콜아웃이 서로 겹치고 옆 열까지 흘러나갔다.
BODY = shp((6.20, 2.95), 1.05, 0.50, 4.0)
GIMB = shp((5.28, 2.43), 0.19, 0.19, 2.0)
ARM_N = bar((5.55, 2.62), (4.45, 1.70), 0.060)
ROT_N = shp((4.18, 1.52), 0.75, 0.075, 2.0, -10.0)
ARM_F = bar((7.15, 3.18), (8.40, 3.45), 0.060)
ROT_F = shp((8.88, 3.52), 0.90, 0.080, 2.0, -8.0)
SHAPES = [BODY, GIMB, ARM_N, ROT_N, ARM_F, ROT_F]

XLIM, YLIM = (0.15, 10.75), (0.30, 5.55)
DATA_ASPECT = (XLIM[1] - XLIM[0]) / (YLIM[1] - YLIM[0])
TEXT_Y = (5.28, 4.94, 4.60)          # 글자 전용 띠의 세 줄
LEG_Y = (4.20, 3.86, 3.52)           # 범례 줄 — 기체(y≤3.45) 위, 글자띠 아래
LEFT_X = 0.45                        # 표제 왼쪽 정렬
RIGHT_X = 10.45                      # 콜아웃 오른쪽 정렬

INK = "#1b1f24"
GRAY = "#6b7480"
FILL = "#dde3e9"
EDGE = "#7a848f"
SHADOW = "#9aa4ae"
BLUE = "#1f5fbf"
GREEN = "#127a4e"
RED = "#c1121f"
ACC = [BLUE, GREEN, RED]
#  공식 뒤에 깔 흰 판 — 광선·점 위에 얹혀도 식이 읽히게 한다.
FBOX = dict(facecolor="white", alpha=0.80, edgecolor="none", pad=2.5)


def draw_target(ax, lw=1.6):
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


def head(ax, color, line1, line2, fs):
    """열마다 왼쪽 위 표제 두 줄 — 굵은 색 한 줄 + 회색 한 줄."""
    ax.text(LEFT_X, TEXT_Y[0], line1, color=color, fontweight="bold",
            ha="left", va="center", fontsize=fs, zorder=9)
    ax.text(LEFT_X, TEXT_Y[1], line2, color=GRAY, ha="left", va="center",
            fontsize=fs - 1.0, zorder=9)


def callout(ax, lines, xy, color, fs, bold=True):
    """오른쪽 위 콜아웃 — 오른쪽 정렬이라 옆 열로 흘러나갈 수 없다.

    ⚠ 화살표 꼬리는 **과녁 바로 위**에서 시작한다. 글자 오른쪽 끝에서 출발시켰더니 화살이
      기체를 가로질러 팔·로터를 덮었다(2026-08-10 첫 판)."""
    ys = TEXT_Y[:len(lines)]
    for y, s in zip(ys, lines):
        ax.text(RIGHT_X, y, s, color=color, ha="right", va="center", fontsize=fs,
                fontweight="bold" if bold else "normal", zorder=9)
    tail = (min(xy[0] + 1.30, RIGHT_X - 0.20), ys[-1] - 0.34)
    ax.add_patch(FancyArrowPatch(tail, xy, arrowstyle="-|>", mutation_scale=13, lw=1.6,
                                 color=color, zorder=9,
                                 connectionstyle="arc3,rad=0.18", shrinkA=2, shrinkB=3))


def legend_rows(ax, rows, fs, x=LEFT_X):
    """점 하나에 설명 한 줄 — 기체 위 빈 띠에 세로로 쌓는다."""
    for y, (mfc, mec, ms_, lab) in zip(LEG_Y, rows):
        ax.plot([x + 0.22], [y], "o", ms=ms_, mfc=mfc, mec=mec, mew=1.1, zorder=8)
        ax.text(x + 0.58, y, lab, color=GRAY, ha="left", va="center",
                fontsize=fs - 1.0, zorder=9)


# ─────────────────────────────────────────────────────────────────────────── #
#  3. 열마다 그림
# ─────────────────────────────────────────────────────────────────────────── #
def panel_sionna(ax, F, fs):
    """송신점에서 광선 표본을 뿌리고, 표적을 거쳐 수신점까지 온 것만 경로가 된다."""
    radar = np.array([0.85, 1.85])
    draw_target(ax)

    #  버려지는 표본들 — 표적을 못 맞히고 지나간다(1e6 발의 대부분).
    base = np.degrees(np.arctan2(*(BODY["c"] - radar)[::-1]))
    for a in np.linspace(base - 24, base + 24, 44):
        v = np.array([np.cos(np.radians(a)), np.sin(np.radians(a))])
        ax.plot(*np.array([radar, radar + 11.5 * v]).T, color=BLUE, lw=0.62,
                alpha=0.18, zorder=2)

    #  살아남은 경로 — 왕복 화살표. 히트점은 실제 실루엣과의 첫 교차로 잡는다.
    aims = [ROT_N["c"] + np.array([0.42, 0.05]), GIMB["c"], BODY["c"] + np.array([-0.72, -0.30]),
            BODY["c"] + np.array([-0.55, 0.34]), ROT_N["c"] + np.array([-0.48, 0.02])]
    hits, n_drawn = [], 0
    for aim in aims:
        v = aim - radar
        v = v / np.linalg.norm(v)
        ent = entries(SHAPES, radar, v, tmax=12.0)
        if not ent:
            continue
        hit = radar + ent[0][0] * v
        hits.append(hit)
        ax.add_patch(FancyArrowPatch(radar, hit, arrowstyle="<|-|>", mutation_scale=12,
                                     lw=1.9, color=BLUE, alpha=0.95, zorder=5,
                                     shrinkA=7, shrinkB=0))
        ax.plot(*hit, "o", ms=6.4, mfc=BLUE, mec="white", mew=1.0, zorder=6)
        n_drawn += 1

    #  레이더 아이콘
    ax.add_patch(Polygon(np.array([radar + [-0.32, -0.32], radar + [0.32, -0.32],
                                   radar + [0.0, 0.36]]), closed=True,
                         facecolor=BLUE, edgecolor="white", lw=1.2, zorder=7))
    ax.text(radar[0], radar[1] - 0.66, "Tx / Rx", ha="center", va="top", color=BLUE,
            fontweight="bold", fontsize=fs, zorder=7)

    spp_txt = f"{F['spp']:.0e}".replace("e+0", r"\times 10^{") + "}"
    head(ax, BLUE, rf"${spp_txt}$ ray samples", "almost all of them miss", fs)
    top = max(hits, key=lambda p: p[1]) if hits else BODY["c"]
    callout(ax, [f"median {F['paths_med']:.0f} paths", "come back"],
            (top[0] + 0.10, top[1] + 0.08), BLUE, fs)

    ax.text(5.45, 0.82, r"$h=\sum_p a_p\,e^{-j2\pi f_c \tau_p}$", ha="center", va="center",
            color=INK, fontsize=fs + 4.0, zorder=9, bbox=FBOX)
    return n_drawn


def panel_sbr(ax, F, fs):
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
        ax.plot(*np.array([o, hit]).T, color=GREEN, lw=1.2, alpha=0.85, zorder=4)
        ax.plot(*hit, "o", ms=5.6, mfc=GREEN, mec="white", mew=0.9, zorder=6)
        n_hit += 1
        if len(ent) > 1:                       # 첫 히트 뒤의 면들 — 셈에 안 들어간다
            far = o + ent[-1][0] * DVEC
            ax.plot(*np.array([hit, far]).T, color=GRAY, lw=0.8, alpha=0.45,
                    ls=(0, (2.0, 2.0)), zorder=4)
            for t_, _ in ent[1:]:
                q = o + t_ * DVEC
                ax.plot(*q, "x", ms=5.8, mew=1.7, color=GRAY, alpha=0.9, zorder=6)
                n_block += 1
        if i % 4 == 0:                          # 몇 발만 화살표를 붙여 방향을 보인다
            ax.add_patch(FancyArrowPatch(o, o + 0.95 * DVEC, arrowstyle="-|>",
                                         mutation_scale=11, lw=1.4, color=GREEN, zorder=5))

    wf0 = svals[0] * PVEC + (start_d - 0.18) * DVEC
    wf1 = svals[-1] * PVEC + (start_d - 0.18) * DVEC
    ax.plot(*np.array([wf0, wf1]).T, color=GREEN, lw=2.4, alpha=0.75, zorder=3)

    head(ax, GREEN, "incident plane wave", rf"ray grid $\lambda/{F['div']}$", fs)
    callout(ax, ["first hit only, so", "the far rotor", "drops out"],
            (ROT_F["c"][0] - 0.30, ROT_F["c"][1] + 0.18), GREEN, fs)
    ax.plot([LEFT_X + 0.22], [LEG_Y[0]], "o", ms=5.6, mfc=GREEN, mec="white", mew=1.1, zorder=8)
    ax.text(LEFT_X + 0.58, LEG_Y[0], "first hit, summed", color=GRAY,
            ha="left", va="center", fontsize=fs - 1.0, zorder=9)
    ax.plot([LEFT_X + 0.22], [LEG_Y[1]], "x", ms=5.8, mew=1.7, color=GRAY, zorder=8)
    ax.text(LEFT_X + 0.58, LEG_Y[1], "behind it, dropped", color=GRAY,
            ha="left", va="center", fontsize=fs - 1.0, zorder=9)

    ax.text(5.45, 0.82,
            r"$E=\sum_{\mathrm{hits}}|\Gamma(\theta)|\;e^{\,j2k\,\mathbf{p}\cdot\hat{u}}\;d^{2}$",
            ha="center", va="center", color=INK, fontsize=fs + 4.0, zorder=9, bbox=FBOX)
    return n_hit, n_block


def panel_control(ax, F, fs):
    """광선 없음. 같은 메쉬의 **모든 면**을 더하고, 등진 면만 뺀다."""
    shadow_band(ax, alpha=0.16)
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
        vis, blk = lit & ~hid, lit & hid
        ax.plot(P[~lit, 0], P[~lit, 1], "o", ms=3.8, mfc="none", mec=GRAY, mew=0.9,
                alpha=0.55, zorder=5)
        ax.plot(P[vis, 0], P[vis, 1], "o", ms=5.2, mfc=RED, mec="white", mew=0.8, zorder=6)
        #  ⭐ 가려졌는데도 셈에 들어가는 면 — 검은 테두리로 **다르게** 보이게 한다.
        ax.plot(P[blk, 0], P[blk, 1], "o", ms=6.6, mfc=RED, mec=INK, mew=1.3, zorder=7)
        n_lit += int(vis.sum())
        n_hid += int(blk.sum())

    head(ax, RED, "no rays are traced", "every facet is summed", fs)
    callout(ax, ["facets hidden", "behind the body", "are summed too"],
            (ROT_F["c"][0] - 0.30, ROT_F["c"][1] + 0.18), RED, fs)
    legend_rows(ax, [(RED, "white", 5.2, "faces the radar"),
                     (RED, INK, 6.6, "hidden, summed anyway"),
                     ("none", GRAY, 3.8, "back facing, removed")], fs)

    ax.text(5.65, 0.82,
            r"$E=\sum_{\hat{n}\cdot\hat{u}>0}|\Gamma|\,(\hat{n}\cdot\hat{u})\,"
            r"\Delta A\;e^{\,j2k\,\mathbf{p}\cdot\hat{u}}$",
            ha="center", va="center", color=INK, fontsize=fs + 4.0, zorder=9, bbox=FBOX)
    return n_lit, n_hid


# ─────────────────────────────────────────────────────────────────────────── #
#  4. 조립
# ─────────────────────────────────────────────────────────────────────────── #
def build():
    F = facts()
    rays = ray_grid_extent(F["lam"], F["div"])

    FS = 13.0
    plt.rcParams.update({
        "font.size": FS, "axes.titlesize": FS + 3.0, "font.family": "DejaVu Sans",
        "figure.dpi": 200, "savefig.dpi": 200, "text.color": INK,
        "axes.edgecolor": "#c7ced5", "mathtext.fontset": "dejavusans",
    })

    #  ⭐ 배치는 **인치로 직접** 잡는다. gridspec + aspect="equal" 로 두면 축이 칸 안에서
    #    저 혼자 줄어들어 패널과 표 사이에 빈 띠가 크게 남는다(첫 판에서 실제로 그랬다).
    FIGW, MARG, GAPW = 15.2, 0.18, 0.18
    COLW = (FIGW - 2 * MARG - 2 * GAPW) / 3.0
    H_PANEL = COLW / DATA_ASPECT
    H_SUP, H_TTL, H_FACT, H_CHAIN, H_FOOT = 0.44, 0.40, 1.30, 0.80, 1.62
    G1, G2, G3, H_BOT = 0.26, 0.10, 0.14, 0.08
    FIGH = H_SUP + H_TTL + H_PANEL + G1 + H_FACT + G2 + H_CHAIN + G3 + H_FOOT + H_BOT

    def rect(top_in, h_in, x_in=MARG, w_in=FIGW - 2 * MARG):
        """위에서부터 잰 인치 → figure 좌표 사각형."""
        return [x_in / FIGW, 1.0 - (top_in + h_in) / FIGH, w_in / FIGW, h_in / FIGH]

    fig = plt.figure(figsize=(FIGW, FIGH))
    y_panel = H_SUP + H_TTL
    y_fact = y_panel + H_PANEL + G1
    y_chain = y_fact + H_FACT + G2
    y_foot = y_chain + H_CHAIN + G3

    axes = [fig.add_axes(rect(y_panel, H_PANEL, MARG + i * (COLW + GAPW), COLW))
            for i in range(3)]
    for ax, ttl, col in zip(axes, F["titles"], ACC):
        frame(ax, ttl, col)
    n_paths = panel_sionna(axes[0], F, FS)
    n_hit, n_block = panel_sbr(axes[1], F, FS)
    n_lit, n_hid = panel_control(axes[2], F, FS)

    #  «무엇을 쏘나 / 무엇을 세나 / 무엇이 빠지나» — 열마다 세 줄
    ray_txt = (rf"plane wave on a $\lambda/{F['div']}$ ray grid"
               if rays is None else
               rf"plane wave on a $\lambda/{F['div']}$ ray grid,"
               "\n" rf"{rays[0]/1000:.0f}k to {rays[1]/1000:.0f}k rays per pose")
    rows = [
        ["ray samples fired from the Tx",
         "the paths that come back to the Rx",
         "the surface integral over the target"],
        [ray_txt,
         "the first hit of every ray",
         "back facing and hidden facets"],
        ["nothing is fired, no ray tracing",
         "every facet of the same mesh,\nbody and rotors alike",
         "back facing facets only"],
    ]
    keys = ["FIRED", "SUMMED", "LEFT OUT"]
    #  ⚠ 줄 간격은 **글줄 단위**로 잡는다(y 축 1 칸 = 한 줄). 축 높이를 인치로 알고 있으므로
    #    칸 수 = 높이/줄높이 로 두면 두 줄짜리 항목이 있어도 라벨과 값이 안 어긋난다.
    LINE_IN = (FS - 0.5) / 72.0 * 1.30
    NSLOT = H_FACT / LINE_IN
    for i in range(3):
        ax = fig.add_axes(rect(y_fact, H_FACT, MARG + i * (COLW + GAPW), COLW))
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, NSLOT)
        y = NSLOT - 0.30
        for k, v in zip(keys, rows[i]):
            lines = "\n".join(textwrap.fill(p, 46) for p in v.split("\n"))
            ax.text(0.028, y, k, color=GRAY, fontsize=FS - 2.0, fontweight="bold",
                    ha="left", va="top")
            ax.text(0.245, y, lines, color=INK, fontsize=FS - 0.5, ha="left", va="top",
                    linespacing=1.30)
            y -= 1.0 + lines.count("\n") + 0.18
        ax.plot([0.02, 0.98], [1.0, 1.0], color=ACC[i], lw=2.6,
                transform=ax.transAxes, clip_on=False, solid_capstyle="butt")

    #  ⭐ 슬로타임 사슬 — 세 열이 **똑같이** 거치는 뒷단. 여기가 «맵이 어떻게 나오나» 의 답이다.
    ch = fig.add_axes(rect(y_chain, H_CHAIN))
    ch.set_axis_off()
    ch.set_xlim(0, 1)
    ch.set_ylim(0, 1)
    ch.text(0.006, 0.95, "EVERY COLUMN THEN GOES THROUGH THE SAME SLOW TIME CHAIN",
            color=GRAY, fontweight="bold", fontsize=FS - 2.0, ha="left", va="top")
    boxes = ["one complex number\nper rotor pose",
             f"{F['n_pose']} poses on one slow time\ngrid, PRF {F['prf']/1e3:.1f} kHz "
             f"= {F['win_ms']:.0f} ms",
             f"STFT, {F['nper']} sample Hann\nsegments = {F['periods']:.2f} blade periods",
             "the micro-Doppler map,\ntime against Doppler"]
    w, cx = 0.212, [0.113, 0.371, 0.629, 0.887]
    for x, b in zip(cx, boxes):
        ch.add_patch(FancyBboxPatch((x - w / 2, 0.06), w, 0.56,
                                    boxstyle="round,pad=0.012,rounding_size=0.03",
                                    facecolor="#f2f5f8", edgecolor="#c7ced5", lw=1.1,
                                    transform=ch.transAxes, clip_on=False))
        ch.text(x, 0.34, b, ha="center", va="center", color=INK, fontsize=FS - 2.0,
                linespacing=1.35)
    for x0, x1 in zip(cx[:-1], cx[1:]):
        ch.add_patch(FancyArrowPatch((x0 + w / 2 + 0.006, 0.34), (x1 - w / 2 - 0.006, 0.34),
                                     arrowstyle="-|>", mutation_scale=15, lw=1.8,
                                     color=GRAY, transform=ch.transAxes, clip_on=False))

    #  정직 표시 — 도식이라는 것, 그리고 열 사이에 함께 달라진 것들
    foot = fig.add_axes(rect(y_foot, H_FOOT))
    foot.set_axis_off()
    bullets = [
        "Schematic of the three kernels, not a computed result. The airframe is a readable "
        "silhouette rather than the simulated mesh.",
        "The middle column and the control differ in more than occlusion. They also differ in "
        rf"discretisation, a $\lambda/{F['div']}$ ray grid against surface point clouds at "
        rf"$\lambda/{F['po_blade']:.0f}$ on the blades and $\lambda/{F['po_frame']:.0f}$ on the "
        r"frame, and in the angle dependent $|\Gamma(\theta)|$, which is on in the middle column "
        "and off in the control. Their gap is therefore not the price of occlusion alone. The "
        r"$(\hat{n}\cdot\hat{u})$ factor appears only in the control because the ray grid already "
        "samples the projected area, so both columns are the same physical optics integral.",
        f"The left column is lit by a point source at {F['rng']:.0f} m while the other two ride "
        "an ideal plane wave anchored on the target. The battery and the board sit inside the "
        "plastic shell, so the control counts them at full amplitude because it never tests "
        "occlusion, the middle column keeps them by tracing through the shell with a two way "
        "transmission factor, and the Sionna column never reaches them because refraction is off.",
    ]
    FLINE = (FS - 3.0) / 72.0 * 1.42
    foot.set_xlim(0, 1)
    foot.set_ylim(0, H_FOOT / FLINE)
    y = H_FOOT / FLINE - 0.15
    for b in bullets:
        lines = textwrap.fill(b, 190).split("\n")
        foot.text(0.004, y, "•", color=GRAY, fontsize=FS - 2.5, ha="left", va="top")
        foot.text(0.016, y, "\n".join(lines), color=GRAY, fontsize=FS - 3.0,
                  ha="left", va="top", linespacing=1.42)
        y -= len(lines) + 0.35

    fig.text(0.5, 1.0 - 0.30 / FIGH, "What each of the three engines actually computes",
             fontsize=FS + 6.0, fontweight="bold", color=INK, ha="center", va="center")

    #  ⚠ bbox_inches="tight" 를 쓰지 않는다 — 배치를 인치로 직접 잡았으므로 잘라내면
    #    설계한 여백과 종횡비가 무너진다(긴 캡션이 그림 폭을 늘린 전례도 있다).
    os.makedirs(OUTD, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{STEM}.{ext}", facecolor="white")
    plt.close(fig)

    from PIL import Image
    w_, h_ = Image.open(f"{STEM}.png").size
    print(f"\n✅ {STEM}.png   {w_}×{h_} px  (aspect {w_/h_:.2f})")
    print(f"✅ {STEM}.pdf")
    print(f"  drone       {F['drone']}   fc {F['fc']/1e9:.2f} GHz   λ {F['lam']*100:.2f} cm")
    print(f"  SBR grid    λ/{F['div']} = {F['lam']/F['div']*1000:.2f} mm"
          + ("" if rays is None
             else f"   rays/aspect {rays[0]}~{rays[1]}   target dia {rays[2]:.3f} m"
                  f"   2D²/λ = {2*rays[2]**2/F['lam']:.1f} m"))
    print(f"  PO cloud    blades λ/{F['po_blade']:.0f}, frame λ/{F['po_frame']:.0f}")
    print(f"  Sionna      spp {F['spp']:.0e}, median {F['paths_med']:.0f} paths/pose "
          f"@ R={F['rng']:.0f} m, empty poses {F['paths_zero']:.1%}")
    print(f"  slow time   {F['n_pose']} poses @ PRF {F['prf']:.0f} Hz = {F['win_ms']:.0f} ms, "
          f"STFT {F['nper']} samples = {F['periods']:.2f} blade periods "
          f"({F['seg_ms']:.2f} ms), hop {F['hop']}")
    print(f"  drawn       {n_paths} paths · {n_hit} first hits, {n_block} blocked · "
          f"{n_lit} lit + {n_hid} hidden facets counted in the control")


if __name__ == "__main__":
    build()
