# -*- coding: utf-8 -*-
"""
viz_verify_po.py — (report6) PO 커널 **검증** 그림 3장
=======================================================
docs/VERIFY_RT_VS_PO.md 에서 확정된 세 가지 사실을 그림으로 못박는다.

생성물 (outputs/figures/, report6_ 접두어)
  report6_po_diagnostic.png   : 평판은 커널을 시험하지 못한다 (구만이 시험한다)
  report6_po_convergence.png  : λ/7 은 얼마나 정확한가 (점간격 수렴)
  report6_nulls.png           : 널은 위치만 믿을 수 있다 (깊이는 인용 금지)

세 줄 요약 (모든 수치는 이 파일이 **실제로 계산해서** 그림에 찍는다 — 하드코딩 없음)
  1. 수직입사 평판은 P·û ≡ 0 이라 위상항이 통째로 사라진다. 그래서 커널에 어떤 버그를
     주입해도 σ = 4πA²/λ² 가 그대로 나온다 — **진단력 0의 항등식**이다.
     구(sphere)는 다르다: 같은 버그가 +6 dB / −30 dB 로 드러난다.
     예외 하나 — 위상 **부호반전**은 E → conj(E) 라 |E|² 가 불변이므로 *어떤* 모노스태틱
     표적으로도 σ 만 봐서는 잡을 수 없다. 위상 기울기 dφ/dR(마이크로도플러가 쓰는 양)로만 잡힌다.
  2. 점간격: 구는 λ/4 에서 이미 수렴(|Δ| ≲ 0.04 dB). 드론은 λ/7 이 λ/30 대비 계통적으로 낮다.
  3. 널: 위치는 이산화에 안정(λ/7~λ/20), 깊이는 수 dB~10 dB 요동 → **깊이 인용 금지**.

참고
  * rcs_po.py 는 **수정하지 않는다**. 버그 주입 변종은 아래 _po_field() 에 국소 복제한다
    (variant="ok" 는 rcs_po.rcs_from_points 와 동일한 식 — 회귀 기준선 역할).
  * 그림 안 텍스트는 전부 영어(프로젝트 규약). 나눔고딕에는 그리스문자(σ·λ·φ)와 ✔/✘ 가 없어
    DejaVu Sans 를 **폴백 폰트**로 덧붙인다(vizstyle.py 는 건드리지 않고 이 모듈 안에서만).
"""
from __future__ import annotations

import os
import textwrap
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt

# 나눔고딕에 없는 글리프(σ λ π φ û Δ Γ ✔ ✘ −)를 DejaVu Sans 로 폴백시킨다.
plt.rcParams["font.family"] = list(plt.rcParams["font.family"]) + ["DejaVu Sans"]

from rcs_po import mesh_to_points, dbsm, angular_smooth, C0, _plate_mesh
from geom import uv_sphere
from drones import DRONES, build_drone, drone_gamma_map, drone_label

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")

FC = 3.5e9                       # 검증 기준 주파수 (5G n78)
LAM = C0 / FC
R_SPH = 0.30                     # 검증 구 반지름 [m]  (ka ≈ 22)
A_PLATE = 0.30                   # 검증 평판 변 [m]

#  기종색 — **재질 팔레트(drones.MATERIAL_COLOR, '5색=순수재질')와 무관한 별개 팔레트**다.
#  ⭐ 2026-07-30: 5종 하드코딩 사전이라 신규 기종에서 `_COL[key]` 가 KeyError 로 죽었다.
#     이제 레지스트리 등록 순서에 색 순환을 씌운다 — 앞 5색이 옛 사전과 같아 기존 그림 색은 보존.
from drones import drone_keys as _drone_keys, drone_cycle_map as _cycle_map   # noqa: E402
_COL = _cycle_map(("#1565c0", "#2e7d32", "#ef6c00", "#000000", "#c62828",
                   "#6a1b9a", "#00838f"), _drone_keys())
_NAME = {k: drone_label(k) for k in DRONES}

_CAP_FS = 8.5                                    # 하단 회색 캡션 폰트크기(규약)


def _caption(fig, text):
    """하단 회색 캡션 — figure 폭에 맞춰 줄바꿈해서 잘리지 않게 한다.
    (fig.supxlabel 은 자동 줄바꿈을 안 해서 긴 문장이 좌우로 잘려 나간다.)"""
    ncol = int(fig.get_figwidth() * 72 / (0.50 * _CAP_FS) * 0.93)   # 대략적 문자수
    wrapped = "\n".join(textwrap.fill(p, ncol) for p in text.split("\n"))
    fig.supxlabel(wrapped, fontsize=_CAP_FS, color="0.45")


# --------------------------------------------------------------------------- #
#  0. 기준해(analytic) + 버그 주입 커널
# --------------------------------------------------------------------------- #
def sphere_po_sigma(r, fc):
    """구의 **해석적 PO** 후방산란 σ [m²] — 커널의 유일한 진짜 시금석.

    우리 이산 커널 E = Σ(n̂·û>0)(n̂·û)ΔA·e^{j2k P·û} 를 구에서 닫힌형으로 적분한 것:
        P = r n̂,  n̂·û = cosθ,  dA = r² sinθ dθ dφ,  t = cosθ,  b = 2kr
        E = 2πr² ∫₀¹ t e^{jbt} dt = 2πr²[ e^{jb}(1/(jb) + 1/b²) − 1/b² ]
        σ = (4π/λ²)|E|²
    b→∞ 에서 σ → πr² (GO 극한). 3.5 GHz·r=0.3 m 에서 GO 대비 −0.01 dB (PO 의 O(1/ka) 항).
    """
    k = 2 * np.pi * fc / C0
    b = 2 * k * r
    E = 2 * np.pi * r**2 * (np.exp(1j * b) * (1 / (1j * b) + 1 / b**2) - 1 / b**2)
    return (4 * np.pi / (C0 / fc) ** 2) * np.abs(E) ** 2


def plate_sigma(a, fc):
    """정사각 평판(변 a) 수직입사 이론 σ = 4πA²/λ²."""
    return 4 * np.pi * (a * a) ** 2 / (C0 / fc) ** 2


#: 버그 주입 변종 — (키, x축 라벨)
VARIANTS = [
    ("ok",      "(a) correct"),
    ("halfk",   "(b) phase 2k → k"),
    ("conj",    "(c) phase sign flip"),
    ("noobl",   "(d) no obliquity"),
    ("noillum", "(e) no illum. test"),
]


def _po_field(P, N, dA, fc, u, variant="ok", w=None):
    """**복소 산란장 E** — rcs_po.rcs_from_points 의 커널을 국소 복제하고 버그를 주입한다."""
    k = 2 * np.pi * fc / C0
    NU = N @ np.asarray(u, float)                   # 면법선·시선
    PU = P @ np.asarray(u, float)                   # 위상거리
    coef = {"ok": 2 * k, "halfk": k, "conj": -2 * k, "noobl": 2 * k, "noillum": 2 * k}[variant]
    obl = np.ones_like(NU) if variant == "noobl" else NU        # obliquity (n̂·û) 제거
    amp = dA if w is None else dA * w
    if variant == "noillum":                        # 조명면 판정 제거 → 뒷면까지 합산
        integ = obl * amp * np.exp(1j * coef * PU)
    else:
        integ = np.where(NU > 0, obl, 0.0) * amp * np.exp(1j * coef * PU)
    return integ.sum()


def _po_sigma(P, N, dA, fc, u, variant="ok", w=None):
    """변종 커널의 σ [m²]."""
    return (4 * np.pi / (C0 / fc) ** 2) * np.abs(_po_field(P, N, dA, fc, u, variant, w)) ** 2


def _phase_slope_ratio(P, N, dA, fc, u, variant):
    """표적을 시선방향으로 평행이동시키며 dφ/dR 를 재고 **정답 2k 로 나눈 비**를 돌려준다.
    평행이동은 모든 항에 e^{j·coef·d} 를 곱하므로 이 기울기는 커널의 **위상계수 그 자체**다.
    → 정상 +1.00 / 2k→k +0.50 / 부호반전 −1.00. 마이크로도플러(φ̇ = 2k·ṙ)가 보는 양이다."""
    k = 2 * np.pi * fc / C0
    d = np.linspace(0.0, (C0 / fc) / 8, 9)
    ph = np.unwrap([np.angle(_po_field(P + dd * np.asarray(u), N, dA, fc, u, variant)) for dd in d])
    return np.polyfit(d, ph, 1)[0] / (2 * k)


# --------------------------------------------------------------------------- #
#  공용
# --------------------------------------------------------------------------- #
def _rcs_az(P, N, dA, fc, az_deg, w=None, el_deg=0.0):
    """σ(az)[m²] — rcs_po.rcs_from_points 의 **청크판**. 점 수가 수백만이어도 메모리가 안 터진다."""
    lam = C0 / fc
    k = 2 * np.pi / lam
    az = np.radians(np.asarray(az_deg, float))
    el = np.radians(el_deg)
    U = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az),
                  np.full_like(az, np.sin(el))], axis=-1)
    amp = (dA if w is None else dA * w)[:, None]
    nchunk = max(1, int(3e7 / len(dA)))              # 복소원소 ≈3e7 이하로 유지
    out = []
    for i in range(0, len(az), nchunk):
        Uc = U[i:i + nchunk]
        NU = N @ Uc.T
        PU = P @ Uc.T
        E = (np.where(NU > 0, NU, 0.0) * amp * np.exp(1j * 2 * k * PU)).sum(axis=0)
        out.append((4 * np.pi / lam**2) * np.abs(E) ** 2)
    return np.concatenate(out)


def _mean_dbsm(sig_db):
    """dBsm 패턴의 **선형 전력 평균**을 dBsm 으로. (10**(x/10).mean() 는 우선순위 함정!)"""
    return dbsm((10.0 ** (np.asarray(sig_db) / 10.0)).mean())


def _drone_cloud(key, spacing):
    """드론 점구름 (재질 |Γ| 가중 포함)."""
    spec = DRONES[key]
    return mesh_to_points(build_drone(spec), spacing, gamma=drone_gamma_map(spec))


# --------------------------------------------------------------------------- #
#  1. report6_po_diagnostic.png — "평판은 커널을 시험하지 못한다"
# --------------------------------------------------------------------------- #
def fig_po_diagnostic(outdir=FIG):
    """커널에 버그를 주입하고 평판/구에서 각각 σ 오차를 잰다.
    평판은 전 변종 0 dB(항등식), 구는 +6/−30 dB 로 드러난다.
    부호반전만은 구의 σ 도 못 잡는다(전역 켤레) → 위상 기울기 시험을 나란히 붙인다."""
    # 평판: 법선 +z → 수직입사 û = +ẑ. 이때 모든 표면점에서 P·û ≡ 0 이다.
    Pp, Np, dAp = mesh_to_points(_plate_mesh(A_PLATE), LAM / 10)
    up = np.array([0.0, 0.0, 1.0])
    ref_p = dbsm(plate_sigma(A_PLATE, FC))
    # 구: 촘촘한 테셀레이션 + λ/12 점간격 → 이산화 오차 ≪ 버그 신호
    Ps, Ns, dAs = mesh_to_points(uv_sphere(R_SPH, seg=120, rings=60), LAM / 12)
    us = np.array([1.0, 0.0, 0.0])
    ref_s = dbsm(sphere_po_sigma(R_SPH, FC))

    keys = [v[0] for v in VARIANTS]
    err_p = np.array([dbsm(_po_sigma(Pp, Np, dAp, FC, up, v)) - ref_p for v in keys])
    err_s = np.array([dbsm(_po_sigma(Ps, Ns, dAs, FC, us, v)) - ref_s for v in keys])
    slope = np.array([_phase_slope_ratio(Ps, Ns, dAs, FC, us, v) for v in keys])
    pmax = np.abs(err_p).max()
    print(f"  [diag] plate  err = {np.array2string(err_p, precision=2)}  (max |Δ| = {pmax:.1e} dB)")
    print(f"  [diag] sphere err = {np.array2string(err_s, precision=3)}")
    print(f"  [diag] dφ/dR ÷ 2k = {np.array2string(slope, precision=3)}")

    TOL = 0.1                                        # 이산화 잡음 대역 [dB]
    fig = plt.figure(figsize=(13.6, 6.4), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[2.1, 1.0])
    ax, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    x = np.arange(len(keys))
    wbar = 0.36

    # ---- 왼쪽: σ 오차 (평판 vs 구) ----
    lo = err_s.min() - 7.0
    hi = err_s.max() + 13.0
    ax.set_ylim(lo, hi)
    ax.axhspan(-TOL, TOL, color="0.86", zorder=0)
    ax.axhline(0, color="0.35", lw=1.0, zorder=1)
    ax.bar(x - wbar / 2, err_p, wbar, color="#90a4ae", ec="#455a64", zorder=3,
           label=f"Flat plate  (a = {A_PLATE:.2f} m, normal incidence)")
    ax.bar(x + wbar / 2, err_s, wbar, color="#c62828", ec="#7f1010", zorder=3,
           label=f"Sphere  (r = {R_SPH:.2f} m, ka = {2*np.pi*R_SPH/LAM:.0f})")
    # 평판 막대는 높이가 0 이라 안 보인다 → 0 위에 납작한 마커를 얹어 "여기 있다"를 보인다
    ax.plot(x - wbar / 2, np.zeros_like(x, dtype=float), "_", ms=20, mew=3.0,
            color="#455a64", zorder=4)

    tr = ax.get_xaxis_transform()                    # x=데이터, y=축분율 → 라벨 배치 안전
    for xi, (ep, es, sl) in enumerate(zip(err_p, err_s, slope)):
        ax.annotate(f"{es:+.2f} dB", (xi + wbar / 2, es), ha="center",
                    va="bottom" if es >= 0 else "top",
                    xytext=(0, 5 if es >= 0 else -5), textcoords="offset points",
                    fontsize=10, color="#7f1010", fontweight="bold", zorder=8)
        if keys[xi] == "ok":
            mark, mcol, note = "•", "0.45", "reference\n(no bug)"
        elif abs(es) > TOL:
            mark, mcol, note = "✔", "#2e7d32", "caught by σ"
        else:
            mark, mcol, note = "✘", "#c62828", "σ is blind\n→ phase test ➜"
        ax.text(xi, 0.975, mark, transform=tr, ha="center", va="top", fontsize=16, color=mcol)
        ax.text(xi, 0.915, note, transform=tr, ha="center", va="top", fontsize=8.5, color="0.35")
    ax.annotate(f"plate: |Δσ| = {pmax:.0e} dB — machine zero,\nfor every variant  (P·û ≡ 0 kills the phase)",
                xy=(0 - wbar / 2, 0.0), xytext=(0.05, 0.38), textcoords="axes fraction",
                fontsize=9.5, color="#263238", ha="left",
                arrowprops=dict(arrowstyle="->", color="#455a64", lw=1.3),
                bbox=dict(fc="#eceff1", ec="#90a4ae", boxstyle="round,pad=0.35"))
    ax.set_xticks(x)
    ax.set_xticklabels([v[1] for v in VARIANTS], fontsize=10)
    ax.set_ylabel("RCS error vs. analytic reference  [dB]")
    ax.set_title(f"Inject a bug into the PO kernel → σ error   ({FC/1e9:.1f} GHz)", fontsize=11.5)
    ax.legend(loc="lower left", fontsize=9.5, framealpha=0.95)   # 우하단은 (d) 막대 라벨 자리
    ax.grid(axis="y", alpha=0.25)

    # ---- 오른쪽: 위상 기울기 시험 ----
    col2 = ["#2e7d32" if abs(s - 1.0) < 1e-3 else "#c62828" for s in slope]
    ax2.axhline(1.0, color="#2e7d32", lw=1.3, ls="--")
    ax2.axhline(0, color="0.5", lw=0.8)
    ax2.bar(x, slope, 0.55, color=col2, ec="0.3", zorder=3)
    for xi, s in zip(x, slope):
        ax2.annotate(f"{s:+.2f}", (xi, s), ha="center", va="bottom" if s >= 0 else "top",
                     xytext=(0, 4 if s >= 0 else -4), textcoords="offset points",
                     fontsize=10, fontweight="bold", color="0.2")
    ax2.text(0.03, 0.965, "correct = +1.00", transform=ax2.transAxes, fontsize=9.5,
             va="top", color="#2e7d32")
    ax2.text(2, -1.30, "the sign flip\nshows up HERE", ha="center", fontsize=9,
             color="#c62828", fontweight="bold")
    ax2.set_ylim(-1.62, 1.62)
    ax2.set_xticks(x)
    ax2.set_xticklabels([v[1].split(")")[0] + ")" for v in VARIANTS], fontsize=10)
    ax2.set_ylabel("range-phase slope  (dφ/dR) ÷ 2k")
    ax2.set_title("Phase test on the sphere\n(the quantity micro-Doppler reads)", fontsize=11)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("A flat plate cannot test the PO kernel — only a sphere can", fontsize=15)
    _caption(fig,
        "Left: the same five kernels are evaluated on a flat plate at normal incidence and on a PEC sphere, each against its "
        "analytic reference (plate 4πA²/λ²; sphere: the closed-form PO integral, which our discrete kernel must reproduce). "
        "At normal incidence every surface point of the plate satisfies P·û ≡ 0, so the phase factor collapses to 1 and the "
        f"plate returns 4πA²/λ² no matter what the kernel does — |Δσ| = {pmax:.0e} dB for all five variants. That is an identity, "
        f"not a test. The sphere separates them at once: dropping the round-trip factor costs {err_s[1]:+.1f} dB, removing the "
        f"obliquity factor {err_s[3]:+.1f} dB, and summing shadowed facets {err_s[4]:+.1f} dB.\n"
        "Right: variant (c) is the one bug the sphere's σ also misses — flipping the phase sign maps E → E*, and |E|² is blind "
        "to conjugation on ANY monostatic target, so no RCS test of any shape can see it. It is caught only by a phase-sensitive "
        "probe: translate the target along the line of sight and fit dφ/dR, which recovers the kernel's phase coefficient exactly "
        "(+1.00 correct, +0.50 when 2k→k, −1.00 for the sign flip). σ on a sphere plus this phase test cover all five bugs. "
        "The plate covers none of them.")

    os.makedirs(outdir, exist_ok=True)
    path = os.path.abspath(os.path.join(outdir, "report6_po_diagnostic.png"))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[viz_verify_po] {path}")
    return path


# --------------------------------------------------------------------------- #
#  2. report6_po_convergence.png — "λ/7 은 얼마나 정확한가"
# --------------------------------------------------------------------------- #
DIVS = [4, 5, 7, 10, 15, 20, 30]                     # spacing = λ/DIV


def fig_po_convergence(outdir=FIG, az_step=3.0):
    """(a) 구의 σ 오차 vs 해석적 PO, (b) 드론 전 기종 방위평균 σ 편차(λ/30 기준)."""
    # ---- (a) 구 ----
    ref_s = dbsm(sphere_po_sigma(R_SPH, FC))
    us = np.array([1.0, 0.0, 0.0])
    mesh_fix = uv_sphere(R_SPH, seg=90, rings=46)    # rcs_po.validate 와 같은 테셀레이션
    err_fix, err_tie = [], []
    for d in DIVS:
        sp = LAM / d
        # (i) 메쉬 고정 · 점간격만 변화 → 순수 '점간격' 수렴
        P, N, dA = mesh_to_points(mesh_fix, sp)
        err_fix.append(dbsm(_po_sigma(P, N, dA, FC, us)) - ref_s)
        # (ii) 테셀레이션도 spacing 에 맞춰 변화 → '표면 이산화' 전체의 수렴
        seg = int(np.ceil(2 * np.pi * R_SPH / sp))
        rings = max(4, int(np.ceil(np.pi * R_SPH / sp)))
        P, N, dA = mesh_to_points(uv_sphere(R_SPH, seg=seg, rings=rings), sp)
        err_tie.append(dbsm(_po_sigma(P, N, dA, FC, us)) - ref_s)
    err_fix, err_tie = np.array(err_fix), np.array(err_tie)
    emax = np.abs(np.r_[err_fix, err_tie]).max()
    print(f"  [conv] sphere err, fixed mesh = {np.array2string(err_fix, precision=3)}")
    print(f"  [conv] sphere err, tied mesh  = {np.array2string(err_tie, precision=3)}")

    # ---- (b) 드론 전 기종 방위평균 (DRONES 레지스트리 전수) ----
    az = np.arange(0.0, 360.0, az_step)
    dev = {}
    for key in DRONES:
        avg = []
        for d in DIVS:
            P, N, dA, w = _drone_cloud(key, LAM / d)
            avg.append(dbsm(_rcs_az(P, N, dA, FC, az, w=w).mean()))
        avg = np.array(avg)
        dev[key] = avg - avg[-1]                     # λ/30 기준 편차
        print(f"  [conv] {key:10s} az-mean(λ/30) = {avg[-1]:7.2f} dBsm   "
              f"dev(λ/7) = {dev[key][DIVS.index(7)]:+.3f} dB")
    d7 = np.array([dev[k][DIVS.index(7)] for k in DRONES])
    worst = min(DRONES, key=lambda k: dev[k][DIVS.index(7)])
    x = np.array(DIVS, float)

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.8), constrained_layout=True)

    # (a)
    ax = axes[0]
    ax.plot(x, err_tie, "o-", color="#1565c0", lw=2.0, ms=7, zorder=3,
            label="sphere re-tessellated with the spacing\n(full surface discretisation)")
    ax.plot(x, err_fix, "s--", color="#8e24aa", lw=1.6, ms=6, alpha=0.85, zorder=3,
            label="fixed 90×46 mesh, point spacing only")
    ax.axhspan(-0.05, 0.05, color="0.88", zorder=0)
    ax.axhline(0, color="0.35", lw=1.0, zorder=1)
    ax.axvline(7, color="#c62828", lw=1.4, ls="--", zorder=2)
    ax.text(7.25, 0.97, "λ/7 = project default", transform=ax.get_xaxis_transform(),
            color="#c62828", fontsize=9, va="top", ha="left")
    ax.annotate(f"{err_tie[DIVS.index(7)]:+.3f} dB @ λ/7", xy=(7, err_tie[DIVS.index(7)]),
                xytext=(11, 0.031), fontsize=9.5, color="#1565c0",
                arrowprops=dict(arrowstyle="->", color="#1565c0", lw=1.1))
    ax.set_xscale("log")
    ax.set_xticks(DIVS)
    ax.set_xticklabels([f"λ/{d}" for d in DIVS])
    ax.minorticks_off()
    ax.set_ylim(-0.058, 0.058)
    ax.set_xlabel("surface point spacing")
    ax.set_ylabel("σ error vs. analytic PO  [dB]")
    ax.set_title(f"(a) Sphere r = {R_SPH:.2f} m — already converged at λ/4  (|Δ| ≤ {emax:.02f} dB)",
                 fontsize=11.5)
    ax.legend(fontsize=8.5, loc="lower right", framealpha=0.95)
    ax.grid(alpha=0.25)
    ax.text(0.025, 0.035, "grey band = ±0.05 dB", transform=ax.transAxes,
            fontsize=8.5, color="0.5")

    # (b)
    ax = axes[1]
    for key in DRONES:
        ax.plot(x, dev[key], "o-", color=_COL[key], lw=1.9, ms=6, label=_NAME[key], zorder=3)
    ax.axhline(0, color="0.35", lw=1.0, zorder=1)
    ax.axvline(7, color="#c62828", lw=1.4, ls="--", zorder=2)
    ymin = min(dev[k].min() for k in DRONES)
    ax.set_ylim(ymin * 1.30, max(0.10, -ymin * 0.22))
    ax.text(7.25, 0.055, "λ/7 = project default", transform=ax.get_xaxis_transform(),
            color="#c62828", fontsize=9, va="bottom", ha="left")
    ax.annotate(f"{dev[worst][DIVS.index(7)]:+.2f} dB", xy=(7, dev[worst][DIVS.index(7)]),
                xytext=(-30, -30), textcoords="offset points", fontsize=9.5,
                color="#c62828", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.1))
    ax.set_xscale("log")
    ax.set_xticks(DIVS)
    ax.set_xticklabels([f"λ/{d}" for d in DIVS])
    ax.minorticks_off()
    ax.set_xlabel("surface point spacing")
    ax.set_ylabel("azimuth-mean σ, deviation from λ/30  [dB]")
    ax.set_title(f"(b) Drones — λ/7 under-reports by {abs(d7.max()):.2f}…{abs(d7.min()):.2f} dB  "
                 "(always low, monotone)", fontsize=11.5)
    ax.legend(fontsize=9, loc="lower right", ncol=2, framealpha=0.95)
    ax.grid(alpha=0.25)

    fig.suptitle("How accurate is λ/7? On the sphere: exact. On drones: a known low bias", fontsize=15)
    _caption(fig,
        f"(a) The discrete PO reproduces the closed-form sphere integral to within {emax:.02f} dB at EVERY spacing tested — "
        "including λ/4, the coarsest. A smooth convex target has no fine structure for the sampling to miss, so the sphere "
        "validates the KERNEL but says nothing about the spacing a real target needs. Both curves are shown because the two "
        "knobs differ: refining only the point spacing on a fixed 90×46 mesh (purple) leaves the facets alone, while "
        "re-tessellating with the spacing (blue) refines the surface itself — neither exceeds ±0.04 dB.\n"
        f"(b) Drones are where spacing matters. The azimuth-mean σ (az 0–360° at {az_step:.0f}°, {FC/1e9:.1f} GHz, "
        "material-weighted |Γ|) converges monotonically FROM BELOW, so λ/7 is systematically LOW — by "
        f"{abs(d7.min()):.2f} dB on {_NAME[worst]} (the largest airframe, with the most rotor and arm surface to under-sample) "
        f"and {abs(d7.max()):.2f} dB on the mildest. Same sign on every drone at every spacing: this is a bias, not noise. "
        "It is also small next to the PO model error itself (self-shadowing, multi-bounce), which no sphere can bound.")

    os.makedirs(outdir, exist_ok=True)
    path = os.path.abspath(os.path.join(outdir, "report6_po_convergence.png"))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[viz_verify_po] {path}")
    return path


# --------------------------------------------------------------------------- #
#  3. report6_nulls.png — "널은 위치만 믿을 수 있다"
# --------------------------------------------------------------------------- #
NULL_DIVS = [7, 9, 12, 16, 20]
BW = 100e6                                           # 5G n78 100 MHz
WIN_DEG = 3.0                                        # 각도창(빔폭·요 지터)


def _local_min_idx(y):
    """순환축(방위)에서의 국소최소 인덱스."""
    return np.where((y < np.roll(y, 1)) & (y < np.roll(y, -1)))[0]


def _circ_dist(a, b):
    """방위 원형 거리 [deg]."""
    return np.abs(((np.asarray(a) - np.asarray(b) + 180.0) % 360.0) - 180.0)


def fig_nulls(outdir=FIG, key="mavic4pro", az_step=0.25, n_f=9, n_null=10):
    """(a) 단일주파수/대역평균/대역+각도창 패턴, (b) 최심 널 확대,
    (c) 널 **위치**는 이산화에 안정, (d) 널 **깊이**는 요동 → 깊이 인용 금지."""
    az = np.arange(0.0, 360.0, az_step)
    spec = DRONES[key]
    mesh = build_drone(spec)
    gmap = drone_gamma_map(spec)

    # --- 이산화별 단일주파수 패턴 ---
    sig, allmin = {}, {}
    for d in NULL_DIVS:
        P, N, dA, w = mesh_to_points(mesh, LAM / d, gamma=gmap)
        sig[d] = dbsm(_rcs_az(P, N, dA, FC, az, w=w))
        allmin[d] = _local_min_idx(sig[d])           # 전체 국소최소(깊이 무관)
    s_single = sig[7]

    # --- 100 MHz 대역평균 (각 주파수에서 spacing = λ(f)/7) ---
    acc = 0.0
    for f in np.linspace(FC - BW / 2, FC + BW / 2, n_f):
        P, N, dA, w = mesh_to_points(mesh, (C0 / f) / 7.0, gamma=gmap)
        acc = acc + _rcs_az(P, N, dA, f, az, w=w)
    s_band_lin = acc / n_f
    s_band = dbsm(s_band_lin)
    s_bw = dbsm(angular_smooth(s_band_lin, WIN_DEG, az_step))

    # --- 널 통계 ---
    def top_nulls(d):
        li = allmin[d]
        return np.sort(li[np.argsort(sig[d][li])[:n_null]])
    tops = {d: top_nulls(d) for d in NULL_DIVS}
    ref = tops[7]
    ref_az = az[ref]

    # (i) 위치 안정성 — 각 spacing 의 top-10 널이, 다른 모든 spacing 의 **국소최소 집합**에서
    #     얼마나 떨어진 곳에 대응점을 갖는가. (top-10 끼리 비교하면 '순위 교체'가 위치이동으로 오독된다.)
    pos_shift = 0.0
    for d in NULL_DIVS:
        for i in tops[d]:
            for d2 in NULL_DIVS:
                pos_shift = max(pos_shift, _circ_dist(az[allmin[d2]], az[i]).min())
    # (ii) 순위 안정성 — λ/7 의 top-10 중 몇 개가 모든 spacing 의 top-10 에도 드는가
    n_common = sum(1 for a0 in ref_az
                   if all(_circ_dist(az[tops[d]], a0).min() <= 0.5 for d in NULL_DIVS))
    # (iii) 깊이 요동 — 같은 널(±0.75° 창)의 깊이를 spacing 별로 추적
    half = max(1, int(round(0.75 / az_step)))
    D = np.array([[sig[d][max(0, i - half):i + half + 1].min() for i in ref] for d in NULL_DIVS])
    swing = D.max(axis=0) - D.min(axis=0)

    m_single, m_bw = _mean_dbsm(s_single), _mean_dbsm(s_bw)
    print(f"  [nulls] deepest null : single {s_single.min():.1f} → band({BW/1e6:.0f} MHz) {s_band.min():.1f} "
          f"→ +{WIN_DEG:.0f}° window {s_bw.min():.1f} dBsm")
    print(f"  [nulls] lobe peak    : {s_single.max():.2f} → {s_bw.max():.2f} dBsm   "
          f"az-mean: {m_single:.2f} → {m_bw:.2f} dBsm")
    print(f"  [nulls] position shift ≤ {pos_shift:.2f}° ; {n_common}/{n_null} stay in the top-10 ; "
          f"depth swing {swing.min():.1f}…{swing.max():.1f} dB")

    # ---------------- 그리기 ----------------
    fig = plt.figure(figsize=(15.0, 8.8), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.22, 1.0])
    axp = fig.add_subplot(gs[0, :])
    axz = fig.add_subplot(gs[1, 0])
    axa = fig.add_subplot(gs[1, 1])
    axd = fig.add_subplot(gs[1, 2])

    # (a) 패턴 3종
    axp.plot(az, s_single, color="0.62", lw=0.8,
             label=f"single frequency ({FC/1e9:.1f} GHz, λ/7)   min {s_single.min():.1f} dBsm")
    axp.plot(az, s_band, color="#1565c0", lw=1.1,
             label=f"{BW/1e6:.0f} MHz band average ({n_f} tones)   min {s_band.min():.1f} dBsm")
    axp.plot(az, s_bw, color="#2e7d32", lw=1.9,
             label=f"band average + {WIN_DEG:.0f}° angular window   min {s_bw.min():.1f} dBsm   "
                   "← the curve our reports use")
    axp.axhline(m_bw, color="#ef6c00", lw=1.1, ls=":")
    axp.text(356, m_bw + 1.2, f"azimuth mean {m_bw:.1f} dBsm — identical for all three curves "
             f"(single freq: {m_single:.1f})", fontsize=8.5, color="#ef6c00", ha="right",
             bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.5))
    a0 = az[np.argmin(s_single)]
    axp.axvspan(a0 - 4, a0 + 4, color="#c62828", alpha=0.10, zorder=0)
    axp.text(a0, -9.6, "zoom in (b)", ha="center", va="top", fontsize=8.5,
             color="#c62828", fontweight="bold")
    axp.set_xlim(0, 360)
    axp.set_ylim(-80, -8)
    axp.set_xticks(np.arange(0, 361, 30))
    axp.set_xlabel("azimuth [deg]")
    axp.set_ylabel("σ  [dBsm]")
    axp.set_title(f"(a) {_NAME[key]} @ {FC/1e9:.1f} GHz, el = 0°   —   finite bandwidth fills the nulls; "
                  "peaks and mean do not move", fontsize=11.5)
    axp.legend(fontsize=9, loc="lower left", ncol=3, framealpha=0.95)
    axp.grid(alpha=0.22)

    # (b) 가장 깊은 널 확대 — 별도 패널(데이터 위에 얹지 않는다)
    m = (az > a0 - 4) & (az < a0 + 4)
    axz.plot(az[m], s_single[m], color="0.62", lw=1.3, label="single freq")
    axz.plot(az[m], s_band[m], color="#1565c0", lw=1.7, label=f"{BW/1e6:.0f} MHz band")
    axz.plot(az[m], s_bw[m], color="#2e7d32", lw=2.4, label=f"band + {WIN_DEG:.0f}°")
    for y, c in ((s_single.min(), "0.45"), (s_band[m].min(), "#1565c0"), (s_bw[m].min(), "#2e7d32")):
        axz.axhline(y, color=c, lw=0.8, ls=":")
        axz.text(a0 + 3.9, y + 0.7, f"{y:.1f}", color=c, fontsize=9, ha="right", fontweight="bold")
    axz.annotate("", xy=(a0 - 3.4, s_bw[m].min()), xytext=(a0 - 3.4, s_single.min()),
                 arrowprops=dict(arrowstyle="<->", color="#c62828", lw=1.6))
    axz.text(a0 - 3.2, (s_single.min() + s_bw[m].min()) / 2,
             f"+{s_bw[m].min() - s_single.min():.0f} dB\nof pure\nartefact",
             color="#c62828", fontsize=9, fontweight="bold", va="center")
    axz.set_xlim(a0 - 4, a0 + 4)
    axz.set_ylim(s_single.min() - 4, max(s_single[m].max(), s_bw[m].max()) + 2.5)
    axz.set_xlabel("azimuth [deg]")
    axz.set_ylabel("σ  [dBsm]")
    axz.set_title(f"(b) Zoom on the deepest null (az {a0:.2f}°)", fontsize=11.5)
    axz.legend(fontsize=8.5, loc="lower right", framealpha=0.95)
    axz.grid(alpha=0.22)

    # (c) 널 위치 — 이산화별 top-10
    for a_ in ref_az:
        axa.axvline(a_, color="0.86", lw=1.0, zorder=0)
    for yi, d in enumerate(NULL_DIVS):
        axa.plot(az[tops[d]], np.full(len(tops[d]), yi), "o", ms=8, zorder=3,
                 color=plt.cm.viridis(yi / (len(NULL_DIVS) - 1)), mec="0.25")
    axa.set_yticks(range(len(NULL_DIVS)))
    axa.set_yticklabels([f"λ/{d}" for d in NULL_DIVS])
    axa.set_ylim(-0.7, len(NULL_DIVS) - 0.15)
    axa.set_xlim(0, 360)
    axa.set_xticks(np.arange(0, 361, 60))
    axa.set_xlabel("azimuth of the 10 deepest nulls [deg]")
    axa.set_ylabel("surface point spacing")
    axa.set_title(f"(c) Null POSITION is stable  (shift ≤ {pos_shift:.2f}°)", fontsize=11.5)
    axa.text(0.5, 0.97, "the columns line up → trust the WHERE", transform=axa.transAxes,
             ha="center", va="top", fontsize=9.5, color="#2e7d32", fontweight="bold",
             bbox=dict(fc="#e8f5e9", ec="#2e7d32", boxstyle="round,pad=0.3"))
    axa.grid(axis="x", alpha=0.18)

    # (d) 널 깊이 — 같은 널을 이산화별로 추적
    xs = np.arange(len(NULL_DIVS))
    for j, a_ in enumerate(ref_az):
        axd.plot(xs, D[:, j], "o-", ms=5, lw=1.5, alpha=0.9,
                 color=plt.cm.plasma(j / (len(ref_az) - 1)), label=f"{a_:.2f}°")
    jmax = int(np.argmax(swing))
    axd.text(0.03, 0.05, f"worst: az {ref_az[jmax]:.2f}° swings {swing[jmax]:.1f} dB "
             f"({D[:, jmax].min():.0f} → {D[:, jmax].max():.0f} dBsm)\n"
             "the lines wander → never quote the HOW DEEP",
             transform=axd.transAxes, ha="left", va="bottom", fontsize=9, color="#c62828",
             fontweight="bold", bbox=dict(fc="#ffebee", ec="#c62828", boxstyle="round,pad=0.3"))
    axd.set_xticks(xs)
    axd.set_xticklabels([f"λ/{d}" for d in NULL_DIVS])
    axd.set_xlim(-0.3, len(NULL_DIVS) - 0.7)
    axd.set_ylim(D.min() - 8.0, D.max() + 9.0)      # 위/아래 여백 = 범례·경고문 자리
    axd.set_xlabel("surface point spacing")
    axd.set_ylabel("null depth  [dBsm]")
    axd.set_title(f"(d) Null DEPTH is not  (same 10 nulls swing {swing.min():.1f}–{swing.max():.1f} dB)",
                  fontsize=11.5)
    axd.legend(fontsize=7.5, ncol=2, loc="upper left", title="null azimuth",
               title_fontsize=7.5, framealpha=0.95)
    axd.grid(alpha=0.22)

    fig.suptitle("Trust where the nulls are — never how deep they are", fontsize=15)
    _caption(fig,
        "A single-frequency coherent PO pattern has needle-deep nulls, and they are artefacts twice over. "
        f"(a, b) A real radar never sees them: averaging over the 5G n78 {BW/1e6:.0f} MHz band lifts the deepest null "
        f"{s_single.min():.1f} → {s_band.min():.1f} dBsm, and a {WIN_DEG:.0f}° angular window (antenna beamwidth, yaw jitter, "
        f"finite sampling) lifts it to {s_bw.min():.1f} dBsm — the needle is {s_bw.min() - s_single.min():.0f} dB of pure fiction. "
        f"Lobe peaks ({s_single.max():.1f} → {s_bw.max():.1f} dBsm) and the azimuth mean ({m_single:.1f} → {m_bw:.1f} dBsm) are "
        "untouched by either average, so every headline number in these reports is safe; only the nulls move.\n"
        f"(c, d) And the code cannot resolve their depth anyway. Refining the surface sampling from λ/7 to λ/20 leaves the null "
        f"AZIMUTHS where they were (no null moves more than {pos_shift:.2f}°, i.e. one azimuth cell; {n_common}/{n_null} even keep "
        f"their rank in the deepest ten), while the DEPTHS of those same nulls wander by {swing.min():.1f}–{swing.max():.1f} dB with no "
        "sign of convergence. The reason is structural: a null's position is geometry — the path-length difference between "
        "scattering centres — but its depth is the residue of a near-cancellation, and a residue is set by the discretisation "
        "error, not by the target. Quote null positions; never quote null depths.")

    os.makedirs(outdir, exist_ok=True)
    path = os.path.abspath(os.path.join(outdir, "report6_nulls.png"))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[viz_verify_po] {path}")
    return path


# --------------------------------------------------------------------------- #
def build_all(outdir=FIG):
    """PO 검증 그림 3장 전부 생성."""
    print("== report6 · PO 검증 그림 ==")
    return [fig_po_diagnostic(outdir), fig_po_convergence(outdir), fig_nulls(outdir)]


if __name__ == "__main__":
    build_all()
