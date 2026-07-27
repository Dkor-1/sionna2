# -*- coding: utf-8 -*-
"""viz_report13.py — report13(자유공간 드론 검지거리) **그림 F1~F16 + matplotlib GIF R5~R8**
=================================================================================================

■ 이 모듈의 유일한 계약: **물리계산 금지, JSON 만 읽어 그림**(스펙 §9/§11).
  σ·SNR·거리·커버리지·ECA바닥은 전부 `experiment_freespace_range` / `experiment_freespace_sigma`
  / `verify_freespace` 가 이미 계산해 JSON 에 박아둔 값이다. 여기서는 **한 번도 다시 계산하지
  않는다** — freespace_link/detect/scene 의 물리함수를 import 조차 하지 않는다. 읽고 그린다.
    · outputs/report13_freespace.json   (거리·커버리지·감도·벽지도·detector_transfer)
    · outputs/report13_sigma_grid.json  (σ 격자·멀티스태틱·D/λ)
    · outputs/verify_freespace.json      (k_mode 잔차·ECA바닥·Δσ(β))

■ 규약(스펙 §11)
  · **그림 텍스트 전부 영어**(제목·축·범례·주석). **캡션만 한국어**(회색 supxlabel).
  · 저장 규약은 `viz_report2._save` 와 동일(dpi130·tight·흰배경·회색캡션)지만 **직접 복제**했다:
    viz_report2 는 import 시점에 `gpu.pick()` 을 부르는 부작용이 있는데(모듈 최상단),
    이 모듈은 순수 matplotlib(CPU)이라 GPU 를 잡으면 안 된다(스펙: SIONNA2_GPU 불필요).
    복제한 것은 4줄짜리 저장 헬퍼·로그축 포매터뿐이고 물리·렌더 커널이 아니다(규칙 3 무위반).
  · 5드론 축 순서는 **target_extent 순**(F17): mini5pro<phantom4<mavic4pro<matrice4e<s1000plus.
  · 모든 캡션은 6항 반복(스펙 §11): (a) which SNR (b) 거리축 (c) 기준채널모델
    (d) EIRP·T_CPI (e) φ=90° (f) 소거깊이. `_cap6()` 가 meta 에서 뽑아 한국어로 조립한다.

■ ⚠ JSON 이 아직 없거나 부분적일 때
  실제 산출 JSON 은 실험그룹이 나중에 만든다. 그래서 **모든 그림은 방어적으로** 키를 읽고,
  필요한 키가 없으면 **조용히 건너뛴다**(그림을 안 만들고 사유를 print). 한 그림의 결측이
  배치 전체를 죽이지 않는다. 스모크에서는 더미/부분 JSON 으로 렌더 경로만 확인한다.

■ 다음 그룹에 넘기는 데이터 요구(현재 스키마 §10 에 없어 그림이 skip 되는 것):
  · F1/R8 : `curves.cassini`(단일)·`curves.cassini_by_L`(R8 L스윕용 per-L 등감도선) 필요.
  · F3 인셋: 메쉬 실루엣(재질색)은 기하가 있어야 그린다 → **render_report13 산출물** 경로를
    JSON `stills` 에 실어 주면 인셋으로 붙인다. 없으면 막대만 그린다.
  · R6 : 실 MC RD맵 프레임은 물리라 여기서 못 만든다 → `curves.rd_frames`(|RD| 2D 목록)로
    실어 주면 애니메이션한다. 없으면 skip(날조 금지).

실행:  cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report13.py
       스모크:  --out-dir /tmp/.../fig  (outputs 오염 회피)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np                                    # noqa: E402
import matplotlib                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.patches import Patch                  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator  # noqa: E402

from vizstyle import use_korean                       # noqa: E402  (gpu 부작용 없음)
use_korean()
# 그리스문자·U+2212 규약(viz_report3/viz_radar 하우스룰): NanumGothic 에 그리스·U+2212 글리프가
#   없으므로 **그리스는 mathtext 명령**($\phi$·$\sigma$·$\Delta$…)으로, **마이너스는 ASCII 하이픈**으로
#   쓴다. mathtext 명령은 matplotlib 수식폰트로 그려져 본문 폰트(한글)와 무관하다(스모크 확인:
#   NanumGothic 유지 + mathtext 그리스 → 글리프 경고 0). fontset 은 건드리지 않는다(건드리면
#   $...$ 안의 '-' 가 U+2212 로 바뀌어 오히려 두부가 난다). 숫자눈금 음수는 axes.unicode_minus=False.

_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
DEFAULT_OUT = os.path.join(_ROOT, "outputs", "figures")
JSON_FS = os.path.join(_ROOT, "outputs", "report13_freespace.json")
JSON_SG = os.path.join(_ROOT, "outputs", "report13_sigma_grid.json")
JSON_VF = os.path.join(_ROOT, "outputs", "verify_freespace.json")

# ── 5드론 팔레트(target_extent 순, Okabe-Ito 색맹안전) ────────────────────────
DRONE_ORDER = ("mini5pro", "phantom4", "mavic4pro", "matrice4e", "s1000plus")
DRONE_COLOR = {
    "mini5pro": "#0072B2", "phantom4": "#E69F00", "mavic4pro": "#009E73",
    "matrice4e": "#CC79A7", "s1000plus": "#D55E00",
}
DRONE_LABEL = {"mini5pro": "Mini 5 Pro", "phantom4": "Phantom 4",
               "mavic4pro": "Mavic 4 Pro", "matrice4e": "Matrice 4E",
               "s1000plus": "S1000+"}

# ── 밴드/모드 색(WiFi 주황·LTE 청록·NR 파랑, 점유 G1/G2/G3 = 밝→진) ───────────
_BAND_BASE = {"W": "#ef6c00", "L": "#00897b", "G": "#1565c0"}
_BAND_NAME = {"W": "WiFi", "L": "LTE", "G": "NR"}
MODE_ORDER = ("W1", "W2", "W3", "L1", "L2", "L3", "G1", "G2", "G3")
TRIO = ("W1", "L1", "G1")                              # 헤드라인 상시 3인방


def _shade(col, f):
    """색을 f∈[0,1] 만큼 흰색쪽으로 섞는다(점유 G1 밝음 → G3 진함).
    `col` 은 hex 문자열('#rrggbb') **또는** RGB 튜플/배열 둘 다 받는다(감사: F3 가 이미 튜플색을 넘긴다)."""
    if isinstance(col, str):
        c = np.array([int(col[i:i + 2], 16) for i in (1, 3, 5)], float) / 255.0
    else:
        c = np.asarray(col, float)[:3]
    c = c * (1 - f) + np.ones(3) * f
    return tuple(c)


def mode_color(mode):
    band = mode[0].upper()
    occ = int(mode[1]) if mode[1:].isdigit() else 1
    base = _BAND_BASE.get(band, "#666666")
    return _shade(base, {1: 0.42, 2: 0.20, 3: 0.0}.get(occ, 0.2))


# --------------------------------------------------------------------------- #
#  공통 그림 유틸 — viz_report2._save 규약을 **복제**(gpu 부작용 회피, 위 docstring 참조)
# --------------------------------------------------------------------------- #
class Saver:
    def __init__(self, out_dir):
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.saved = []

    def __call__(self, fig, name, caption):
        fig.supxlabel(caption, fontsize=8.5, color="#555555", y=0.004, linespacing=1.6)
        p = os.path.join(self.out_dir, name)
        fig.savefig(p, dpi=130, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        self.saved.append(p)
        print(f"  [fig] {os.path.relpath(p, _ROOT) if p.startswith(_ROOT) else p}")
        return p


def _plain_log(ax, which="both"):
    """로그축 눈금 ASCII 평문 — NanumGothic 에 U+2212 글리프가 없어 두부글자가 되는 걸 회피
    (viz_report2._plain_log 규약 복제)."""
    def _fmt(v, _pos):
        if v <= 0:
            return ""
        if v >= 10:
            return f"{v:.0f}"
        if v >= 1:
            return f"{v:.0f}"
        return f"{v:.2f}"
    axes = ([ax.xaxis] if which == "x" else [ax.yaxis] if which == "y"
            else [ax.xaxis, ax.yaxis])
    for a in axes:
        a.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0), numticks=12))
        a.set_major_formatter(FuncFormatter(_fmt))
        a.set_minor_formatter(FuncFormatter(lambda *_: ""))


def _ascii_sci_log(ax, which="y"):
    """작은 값(예 Pfa 1e-7~1e-3) 로그축을 **ASCII 지수표기**로 — 기본 LogFormatterSciNotation 은
    $10^{-4}$ 를 mathtext 로 그려 U+2212 를 부른다(NanumGothic·mathtext 기본폰트 결측). `_plain_log`
    는 1 미만을 '0.00' 으로 뭉개므로 미소값 축에는 부적합 → `1e-04` 식으로 찍는다(감사: F13 Pfa 축)."""
    def _fmt(v, _pos):
        return f"{v:.0e}" if v > 0 else ""
    a = ax.yaxis if which == "y" else ax.xaxis
    a.set_major_locator(LogLocator(base=10, numticks=12))
    a.set_major_formatter(FuncFormatter(_fmt))
    a.set_minor_formatter(FuncFormatter(lambda *_: ""))


def _get(d, *path, default=None):
    """중첩 dict 안전조회 — 어느 단계든 없으면 default."""
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _range_cell(fs, drone, mode, view="equal_psd", ref="full_waveform_capture", N="1"):
    """ranges[drone][mode][view][ref]["by_N"][N] 안전조회."""
    return _get(fs, "ranges", drone, mode, view, ref, "by_N", str(N))


# --------------------------------------------------------------------------- #
#  캡션 6항(스펙 §11) — meta 에서 뽑아 한국어로 조립
# --------------------------------------------------------------------------- #
def _ctx(fs):
    """meta 에서 캡션·헤드라인 문맥을 뽑는다(결측이면 선언 기본값)."""
    m = fs.get("meta", {}) if isinstance(fs, dict) else {}
    lb = m.get("link_budget", {})
    cpi = m.get("cpi", {})
    return dict(
        eirp=lb.get("eirp_equal_dbm", 63.0),
        t_cpi_ms=1000.0 * float(cpi.get("T_cpi_ref_s", 0.1)),
        phi=_get(m, "geometry", "phi_headline_deg", default=90.0),
        ref_model=_get(fs, "meta", "reference_model", "canonical",
                       default="full-waveform capture"),
        pfa=_get(m, "detector", "pfa_cell", default=1e-4),
        depth="ideal (∞ dB)",
        snr="RD-output SNR (mean convention)",
    )


def _cap6(ctx, axis_desc, extra=""):
    """캡션 6항 반복(a~f) — 한국어. axis_desc 는 거리축 설명(그림마다 다름)."""
    base = (f"(a) {ctx['snr']} · (b) 거리축 {axis_desc} · (c) 기준채널={ctx['ref_model']} · "
            f"(d) EIRP {ctx['eirp']:.0f} dBm(in-burst peak)·T_CPI {ctx['t_cpi_ms']:.0f} ms · "
            f"(e) $\\phi$={ctx['phi']:.0f}° · (f) 소거깊이 {ctx['depth']}")
    return base + (("\n" + extra) if extra else "")


def _skip(name, why):
    print(f"  [skip] {name}: {why}")
    return None


# =========================================================================== #
#  F1 — 기하: 자유공간 세 거리 + Cassini
# =========================================================================== #
class R13Viz:
    """report13 그림 빌더 — JSON 을 들고 F1~F16·R5~R8 을 만든다."""

    def __init__(self, fs=None, sg=None, vf=None, out_dir=DEFAULT_OUT):
        self.fs = fs or {}
        self.sg = sg or {}
        self.vf = vf or {}
        self.ctx = _ctx(self.fs)
        self.save = Saver(out_dir)

    # ---- F1 ---------------------------------------------------------------- #
    def f1_geometry(self):
        cas = _get(self.fs, "curves", "cassini")
        ell = _get(self.fs, "curves", "rb_ellipses")
        if not cas and not ell:
            return _skip("F1_geometry", "curves.cassini/rb_ellipses 없음(producer 가 실어야 함)")
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        geo = _get(self.fs, "meta", "geometry", default={})
        L = float(geo.get("baseline_ref_m", 500.0))
        tx = np.array(geo.get("TX", [0, 0, 25]), float)
        ax.plot([tx[0]], [tx[1]], "^", ms=13, color="#c62828", label="TX (illuminator, 25 m mast)")
        ax.plot([L], [0], "v", ms=13, color="#1565c0", label="RX (passive, 3 m)")
        if isinstance(ell, dict):
            for i, (k, xy) in enumerate(ell.items()):
                xy = np.asarray(xy, float)
                ax.plot(xy[:, 0], xy[:, 1], "-", lw=0.9, color="#9e9e9e",
                        label="iso-R_b ellipse" if i == 0 else None)
        if cas:
            xy = np.asarray(cas, float)
            ax.plot(xy[:, 0], xy[:, 1], "-", lw=2.0, color="#6a1b9a", label="Cassini oval (iso-sensitivity)")
        ax.set_aspect("equal")
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
        ax.set_title("Passive bistatic geometry in free space — three ranges, one measurement")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
        ax.grid(alpha=0.25)
        return self.save(fig, "report13_geometry.png",
                         _cap6(self.ctx, "x,y [m] (R1·R2·R_b·beta)",
                               "R_b=R1+R2-L 이 RD맵 관측량, R_eq=√(R1R2) 가 분산 인용축."))

    # ---- F2 budget waterfall ---------------------------------------------- #
    def f2_budget_waterfall(self):
        modes = [m for m in MODE_ORDER
                 if _cell_budget(self.fs, m) is not None]
        if not modes:
            return _skip("F2_budget_waterfall", "ranges..budget_terms_db 없음")
        order = ["eirp", "grx", "lambda2", "sigma", "spread", "n0", "eta_ref",
                 "t_cpi", "duty", "losses", "k_mode"]
        fig, axes = plt.subplots(3, 3, figsize=(11.5, 8.2), sharex=True)
        for ax, m in zip(axes.ravel(), (list(modes) + [None] * 9)[:9]):
            if m is None:
                ax.axis("off"); continue
            bt = _cell_budget(self.fs, m)
            vals = [float(bt.get(k, 0.0)) for k in order]
            cum = np.cumsum([0.0] + vals)
            for i, (k, v) in enumerate(zip(order, vals)):
                col = "#1565c0" if v >= 0 else "#c62828"
                ax.bar(i, v, bottom=cum[i], color=col, width=0.8)
            ax.axhline(cum[-1], color="#333", lw=1.0, ls="--")
            ax.set_title(m, fontsize=10, color=mode_color(m))
            ax.set_xticks(range(len(order)))
            ax.set_xticklabels(order, rotation=90, fontsize=6.5)
            ax.grid(axis="y", alpha=0.2)
            # B(대역폭) 항이 목록에 없음을 강조
            ax.text(0.02, 0.95, "no B term", transform=ax.transAxes,
                    fontsize=7, color="#c62828", va="top")
        fig.suptitle("SNR budget at d = 1 km (bandwidth term is absent)", y=0.995)
        for ax in axes[:, 0]:
            ax.set_ylabel("cumulative [dB]")
        return self.save(fig, "report13_budget_waterfall.png",
                         _cap6(self.ctx, "예산항목(누적 dB) @ d=1 km",
                               "대역폭 B 는 SNR 항에 없다 — spread=-30log(4$\\pi$)-20logR1-20logR2."))

    # ---- F3 headline range bars ------------------------------------------- #
    def f3_range_bars(self, view="equal_psd"):
        drones = [d for d in DRONE_ORDER if _get(self.fs, "ranges", d)]
        if not drones:
            return _skip("F3_range_bars", "ranges[*] 없음")
        fig, ax = plt.subplots(figsize=(8.4, 5.4))
        nmode = len(TRIO)
        h = 0.8 / nmode
        for j, mode in enumerate(TRIO):
            ys, r50, r25, cilo, cihi = [], [], [], [], []
            for i, d in enumerate(drones):
                c = _range_cell(self.fs, d, mode, view=view)
                if not c:
                    continue
                y = i + (j - (nmode - 1) / 2) * h
                r_c50 = c.get("R90_C50_m")
                if r_c50 is None:
                    continue
                ys.append(y); r50.append(float(r_c50))
                r25.append(float(c.get("R90_C25_m", r_c50)))
                ci = c.get("R90_ci95_m", [r_c50, r_c50])
                cilo.append(float(ci[0])); cihi.append(float(ci[1]))
            if not ys:
                continue
            col = mode_color(mode)
            ax.barh(ys, r50, height=h * 0.92, color=col,
                    label=f"{mode} ({_BAND_NAME[mode[0]]})")
            # 채운 띠 [C25, C50] (더 밝게)
            for y, a, b in zip(ys, r25, r50):
                ax.barh(y, max(b - a, 0), left=a, height=h * 0.92,
                        color=_shade(col, 0.5), zorder=3)
            # CI95 캡막대 (S9: 밴드와 분리)
            r50a = np.array(r50); lo = r50a - np.array(cilo); hi = np.array(cihi) - r50a
            ax.errorbar(r50, ys, xerr=[np.abs(lo), np.abs(hi)], fmt="none",
                        ecolor="#222", elinewidth=1.0, capsize=3, zorder=4)
        ax.set_yticks(range(len(drones)))
        ax.set_yticklabels([DRONE_LABEL[d] for d in drones])
        ax.set_xlabel("Detection range R_eq [m]")
        ax.set_title("Free-space detection range, Pd 0.9 @ Pfa 1e-4 — ideal cancellation\n"
                     "(5 airframes × always-on trio)", fontsize=11)
        ax.legend(loc="lower right", fontsize=8)
        ax.grid(axis="x", alpha=0.25)
        return self.save(fig, "report13_range_bars.png",
                         _cap6(self.ctx, "R_eq [m], 막대=R90_C50 · 채운띠=[C25,C50] · 캡=CI95",
                               f"전력규약 view={view} · 밴드는 자세 커버리지, 캡막대는 MC 신뢰구간(분리)."))

    # ---- F4 coverage curves ----------------------------------------------- #
    def f4_coverage_curves(self):
        cov = _get(self.fs, "curves", "coverage_C_of_d")
        if not cov:
            return _skip("F4_coverage_curves", "curves.coverage_C_of_d 없음")
        fig, ax = plt.subplots(figsize=(8.0, 5.4))
        for d in DRONE_ORDER:
            node = cov.get(d)
            if not node:
                continue
            for mode in TRIO:
                cm = node.get(mode)
                if not cm:
                    continue
                dm = np.asarray(cm.get("d_m", []), float)
                C = np.asarray(cm.get("C", []), float)
                epd = np.asarray(cm.get("E_psi_pd", cm.get("factor_sigma", [])), float)
                if dm.size == 0:
                    continue
                ax.plot(dm, C, "-", color=DRONE_COLOR[d], lw=1.6,
                        label=DRONE_LABEL[d] if mode == "L1" else None)
                if epd.size == dm.size:
                    ax.plot(dm, epd, "--", color=DRONE_COLOR[d], lw=1.0, alpha=0.7)
        ax.axhline(0.8, color="#888", ls=":", lw=1.0)
        ax.set_xscale("log"); _plain_log(ax, "x")
        ax.set_xlabel("Midpoint horizontal range d [m]")
        ax.set_ylabel("Coverage fraction / mean Pd")
        ax.set_ylim(0, 1.02)
        ax.set_title("Detection coverage C(d) and mean Pd — fraction of headings vs heading-averaged")
        ax.plot([], [], "-", color="#444", label="C(d) [solid]")
        ax.plot([], [], "--", color="#444", label=r"E_$\psi$[Pd](d) [dashed]")
        ax.legend(loc="upper right", fontsize=7.5, ncol=2)
        ax.grid(alpha=0.25)
        return self.save(fig, "report13_coverage_curves.png",
                         _cap6(self.ctx, "d [m, log], 실선=C(d)·파선=E_$\\psi$[Pd]",
                               "단일 거리 대신 커버리지+헤딩평균 검출확률(S4)."))

    # ---- F5 sigma grid 5-panel -------------------------------------------- #
    def f5_sigma_grid(self):
        grid = _get(self.sg, "grid") or _get(self.sg, "sigma", "grid")
        if not grid:
            return _skip("F5_sigma_grid", "sigma_grid.json 의 grid 없음")
        meta = self.sg.get("meta", {})
        az = np.asarray(meta.get("az_deg", np.arange(0, 360, 3)), float)
        el = np.asarray(meta.get("el_deg", [0, -0.5, -1, -2, -3.5, -5, -8, -12, -20]), float)
        drones = [d for d in DRONE_ORDER if d in grid]
        if not drones:
            return _skip("F5_sigma_grid", "grid 에 알려진 드론 없음")
        fig, axes = plt.subplots(1, 5, figsize=(15.5, 3.6), sharey=True)
        dol = _get(self.sg, "sigma_confidence", "D_over_lambda") or {}
        im = None
        for ax, d in zip(np.atleast_1d(axes), drones):
            node = grid[d]
            # grid[d] 는 밴드중첩({band:{sigma_smooth_dbsm,az_deg,el_deg}}) — @3.5 GHz 선택.
            axz, ely = az, el
            if isinstance(node, dict):
                if "sigma_smooth_dbsm" not in node:
                    node = node.get("5G NR 3.5 GHz") or next(iter(node.values()), None)
                if isinstance(node, dict) and "sigma_smooth_dbsm" in node:
                    Z = np.asarray(node["sigma_smooth_dbsm"], float)   # (el, az)
                    axz = np.asarray(node.get("az_deg", az), float)
                    ely = np.asarray(node.get("el_deg", el), float)
                else:
                    continue
            else:
                Z = np.asarray(node, float)               # 평탄 2D 폴백
            if Z.shape[0] == axz.size and Z.shape[1] == ely.size:
                Z = Z.T
            vmax = float(np.nanmax(Z)); vmin = vmax - 25.0
            im = ax.imshow(Z, aspect="auto", origin="lower", cmap="turbo",
                           vmin=vmin, vmax=vmax,
                           extent=[axz.min(), axz.max(), ely.min(), ely.max()])
            ax.set_title(DRONE_LABEL[d], fontsize=9, color=DRONE_COLOR[d])
            ax.set_xlabel("azimuth [deg]")
        np.atleast_1d(axes)[0].set_ylabel("bisector elevation [deg]  (≤ 0)")
        if im is not None:
            fig.colorbar(im, ax=list(np.atleast_1d(axes)), shrink=0.8, label="RCS [dBsm]")
        fig.suptitle(r"RCS $\sigma$(az, el ≤ 0) — 5 airframes @3.5 GHz (looking up at the belly)", y=1.02)
        return self.save(fig, "report13_sigma_grid_5.png",
                         _cap6(self.ctx, "직교 히트맵 (x=az, y=el≤0), turbo DR25",
                               "$\\sigma$ 는 (방위,앙각) 함수 — 극좌표 아님. el>0 은 범위 밖(공중조명원)."))

    # ---- F6 sigma to range ------------------------------------------------ #
    def f6_sigma_to_range(self):
        st = _get(self.sg, "sigma", "stats") or _get(self.sg, "stats")
        if not st:
            return _skip("F6_sigma_to_range", "sigma.stats 없음")
        fig, (a0, a1) = plt.subplots(2, 1, figsize=(7.4, 6.6))
        for d in DRONE_ORDER:
            s = st.get(d) if isinstance(st, dict) else None
            if not s:
                continue
            cdf_x = np.asarray(s.get("sigma_sorted_dbsm", s.get("sigma_cdf_x", [])), float)
            cdf_y = np.asarray(s.get("cdf", np.linspace(0, 1, cdf_x.size)), float)
            if cdf_x.size:
                a0.plot(cdf_x, cdf_y, color=DRONE_COLOR[d], lw=1.4, label=DRONE_LABEL[d])
            rx = np.asarray(s.get("R_eq_sorted_m", []), float)
            ry = np.asarray(s.get("R_eq_cdf", np.linspace(0, 1, rx.size)), float)
            if rx.size:
                a1.plot(rx, ry, color=DRONE_COLOR[d], lw=1.4)
        a0.set_xlabel(r"RCS $\sigma$ [dBsm]"); a0.set_ylabel("CDF")
        a1.set_xlabel("R_eq [m]"); a1.set_ylabel("CDF")
        a0.legend(fontsize=7.5); a0.grid(alpha=0.25); a1.grid(alpha=0.25)
        fig.suptitle("From an RCS distribution to a range distribution (pipeline estimator)", y=0.98)
        return self.save(fig, "report13_sigma_to_range.png",
                         _cap6(self.ctx, "상: $\\sigma$ CDF · 하: R_eq CDF (R∝$\\sigma$^¼ 는 R_eq축에서만 정확)",
                               "파이프라인 추정량(5pt m² 평균·음의 el)로 산출한 자세밴드(S5)."))

    # ---- F7 heading footprint (polar) ------------------------------------- #
    def f7_heading_footprint(self):
        pol = _get(self.fs, "coverage", "polar")
        if not pol:
            return _skip("F7_heading_footprint", "coverage.polar 없음")
        fig = plt.figure(figsize=(7.2, 7.0))
        ax = fig.add_subplot(111, projection="polar")
        for d in DRONE_ORDER:
            node = pol.get(d, {})
            cm = node.get("L1") or (next(iter(node.values()), None) if node else None)
            if not cm:
                continue
            psi = np.radians(np.asarray(cm.get("psi_deg", []), float))
            R = np.asarray(cm.get("R90_m", []), float)
            if psi.size == 0:
                continue
            blind = np.asarray(cm.get("blind", np.zeros(psi.size)), bool)
            Rp = np.where(blind, 0.0, R)                  # 블라인드 헤딩 = r=0 함몰
            ax.plot(psi, Rp, color=DRONE_COLOR[d], lw=1.4, label=DRONE_LABEL[d])
            alias = np.asarray(cm.get("alias", np.zeros(psi.size)), bool)
            if alias.any():
                ax.scatter(psi[alias], R[alias], s=6, color=DRONE_COLOR[d],
                           marker="x", alpha=0.5)
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
        ax.set_title("Range vs target heading — aspect, Doppler blind and alias act on one axis",
                     fontsize=10, pad=18)
        ax.legend(loc="lower left", bbox_to_anchor=(-0.1, -0.1), fontsize=7.5)
        return self.save(fig, "report13_heading_footprint.png",
                         _cap6(self.ctx, "극좌표 $\\theta$=$\\psi$, r=R90 [m] (블라인드=r=0 함몰, alias=×)",
                               "자세($\\sigma$)와 도플러 하한·상한이 한 축에서 동시에 작용."))

    # ---- F8 eirp ladder --------------------------------------------------- #
    def f8_eirp_ladder(self):
        ei = _get(self.fs, "sensitivity", "eirp")
        if not ei:
            return _skip("F8_eirp_ladder", "sensitivity.eirp 없음")
        fig, ax = plt.subplots(figsize=(7.8, 5.6))
        x = np.asarray(ei.get("eirp_dbm", ei.get("grid", [])), float)
        yt = np.asarray(ei.get("R_thermal_m", ei.get("R_total_m", [])), float)
        if x.size and yt.size:
            ax.plot(x, yt, "-o", color="#1565c0", lw=1.8, ms=4,
                    label="thermal (slope ¼)")
        ya = np.asarray(ei.get("R_adc_m", []), float)
        if ya.size == x.size and ya.size:
            ax.plot(x, ya, "--", color="#6d4c41", lw=1.4, label="ADC floor (EIRP-independent)")
        # DPI 잔류 4선 (40/60/90/∞)
        dep = _get(self.fs, "sensitivity", "eca_depth_db", "R90_m") or {}
        depth_series = ei.get("R_dpi_resid_m", {}) if isinstance(ei.get("R_dpi_resid_m"), dict) else {}
        cols = {"40": "#c62828", "60": "#ef6c00", "90": "#fbc02d", "inf": "#2e7d32"}
        for k, y in depth_series.items():
            y = np.asarray(y, float)
            if y.size == x.size:
                ax.plot(x, y, ":", color=cols.get(str(k), "#999"), lw=1.5,
                        label=f"DPI residual {k} dB")
        ax.set_xscale("log"); ax.set_yscale("log")
        _plain_log(ax, "both")
        ax.set_xlabel("EIRP [dBm]"); ax.set_ylabel("Detection range [m]")
        ax.set_title("Range scales as the fourth root of illuminator power;\n"
                     "ADC & DPI-residual floors do not", fontsize=11)
        ax.legend(fontsize=7.5); ax.grid(which="both", alpha=0.2)
        return self.save(fig, "report13_eirp_ladder.png",
                         _cap6(self.ctx, "x=EIRP 20–90 dBm, y=R [log-log]",
                               "열잡음 R∝EIRP^¼(기울기¼) · ADC/DPI잔류는 EIRP 무관 바닥."))

    # ---- F9 elevation ----------------------------------------------------- #
    def f9_elevation(self):
        st = _get(self.sg, "sigma", "stats") or _get(self.sg, "stats")
        if not st:
            return _skip("F9_elevation", "sigma.stats 없음(el 축 σ)")
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        drawn = False
        for d in DRONE_ORDER:
            s = st.get(d) if isinstance(st, dict) else None
            if not s or "el_deg" not in s:
                continue
            el = np.asarray(s["el_deg"], float)
            sig = np.asarray(s.get("sigma_vs_el_dbsm", []), float)
            if el.size and sig.size == el.size:
                ax.plot(el, sig, "-o", color=DRONE_COLOR[d], lw=1.4, ms=3, label=DRONE_LABEL[d])
                drawn = True
        if not drawn:
            return _skip("F9_elevation", "stats 에 sigma_vs_el_dbsm 없음")
        el_head = _get(self.fs, "meta", "ranges_el_look_deg", default=-2.0)
        ax.axvline(el_head, color="#c62828", ls="--", lw=1.2,
                   label=f"headline el ≈ {el_head:.0f}°")
        ax.set_xlabel("bisector elevation [deg]  (0 to -20)")
        ax.set_ylabel(r"RCS $\sigma$ [dBsm]")
        ax.invert_xaxis()
        ax.set_title(r"Looking up at the belly — $\sigma$ vs (negative) bisector elevation,"
                     "\nand where the headline sits", fontsize=11)
        ax.legend(fontsize=7.5); ax.grid(alpha=0.25)
        return self.save(fig, "report13_elevation.png",
                         _cap6(self.ctx, "x=el 0…-20°, y=$\\sigma$ [dBsm]",
                               "부호는 음수(배를 본다). 헤드라인 el≈-2° 라 부호정정 효과는 근거리 한정(S8)."))

    # ---- F10 cpi walk ----------------------------------------------------- #
    def f10_cpi_walk(self):
        cpi = _get(self.fs, "sensitivity", "cpi")
        walk = _get(self.fs, "walk")
        if not cpi:
            return _skip("F10_cpi_walk", "sensitivity.cpi 없음")
        fig, ax = plt.subplots(figsize=(7.8, 5.4))
        for mode in TRIO:
            node = cpi.get(mode) if isinstance(cpi, dict) else None
            if not node:
                continue
            T = np.asarray(node.get("t_cpi_s", []), float)
            R = np.asarray(node.get("R90_m", []), float)
            if T.size and R.size == T.size:
                ax.plot(T * 1e3, R, "-o", color=mode_color(mode), lw=1.5, ms=3, label=mode)
            wall = _get(walk, mode, "T_max_s", "5") if walk else None
            if wall:
                ax.axvline(float(wall) * 1e3, color=mode_color(mode), ls="--", lw=1.0)
        ax.set_xscale("log"); ax.set_yscale("log"); _plain_log(ax, "both")
        ax.set_xlabel("T_CPI [ms]"); ax.set_ylabel("R90 [m]")
        ax.set_title("Longer CPI buys R ∝ T^(1/4) — until range-walk (narrowest wall for widest band)",
                     fontsize=10.5)
        ax.legend(fontsize=8); ax.grid(which="both", alpha=0.2)
        return self.save(fig, "report13_cpi_walk.png",
                         _cap6(self.ctx, "x=T_CPI [ms, log], y=R90 [m]",
                               "R∝T^¼ 이득이 range-walk 벽(수직파선, c/B÷v)에서 멈춘다."))

    # ---- F11 walls -------------------------------------------------------- #
    def f11_walls(self):
        base = _get(self.fs, "sensitivity", "baseline")
        if not base:
            return _skip("F11_walls", "sensitivity.baseline 없음")
        bands = [("wifi", "WiFi"), ("lte", "LTE"), ("nr", "NR")]
        fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharey=True)
        for ax, (bk, bn) in zip(axes, bands):
            node = base.get(bk) if isinstance(base, dict) else None
            if not node:
                ax.set_title(f"{bn} (no data)"); ax.axis("off"); continue
            L = np.asarray(node.get("L_m", []), float)
            for key, col, lab in (("R_thermal_m", "#1565c0", "thermal"),
                                  ("R_adc_m", "#6d4c41", "ADC (DR 74)"),
                                  ("R_dpi60_m", "#c62828", "DPI-resid 60 dB"),
                                  ("R_walk_m", "#2e7d32", "walk")):
                y = np.asarray(node.get(key, []), float)
                if y.size == L.size and L.size:
                    ax.plot(L, y, "-", color=col, lw=1.5, label=lab)
            ax.set_xscale("log"); ax.set_yscale("log"); _plain_log(ax, "both")
            ax.set_xlabel("Baseline L [m]"); ax.set_title(bn)
            ax.grid(which="both", alpha=0.2)
        axes[0].set_ylabel("Range [m]"); axes[0].legend(fontsize=7.5)
        fig.suptitle("Which wall binds? thermal / ADC / DPI-residual / walk, by band and baseline", y=1.02)
        return self.save(fig, "report13_walls.png",
                         _cap6(self.ctx, "x=L [m, log], y=R [m, log], 밴드 3패널",
                               "벽은 조건부 — 어느 하나를 헤드라인으로 세우지 않는다(dpi_residual 포함)."))

    # ---- F12 matrix ------------------------------------------------------- #
    def f12_matrix(self):
        if not _get(self.fs, "ranges"):
            return _skip("F12_matrix", "ranges 없음")
        views = [("equal_psd", "equal-PSD"), ("deploy", "deploy-EIRP")]
        fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0), sharey=True)
        im = None
        drones = [d for d in DRONE_ORDER if _get(self.fs, "ranges", d)]
        for ax, (vk, vn) in zip(axes, views):
            M = np.full((len(drones), len(MODE_ORDER)), np.nan)
            for i, d in enumerate(drones):
                for j, mode in enumerate(MODE_ORDER):
                    c = _range_cell(self.fs, d, mode, view=vk)
                    if c and c.get("R90_C50_m") is not None:
                        M[i, j] = float(c["R90_C50_m"])
            im = ax.imshow(M, aspect="auto", cmap="viridis")
            ax.set_xticks(range(len(MODE_ORDER))); ax.set_xticklabels(MODE_ORDER, fontsize=8)
            ax.set_yticks(range(len(drones)))
            ax.set_yticklabels([DRONE_LABEL[d] for d in drones])
            ax.set_title(vn)
        if im is not None:
            fig.colorbar(im, ax=list(axes), shrink=0.85, label="R90_C50 [m]")
        fig.suptitle("R90 matrix — 5 airframes × 9 modes (equal-PSD | deploy-EIRP)", y=1.01)
        return self.save(fig, "report13_matrix.png",
                         _cap6(self.ctx, "히트맵 셀=R90_C50 [m], 5기종×9모드",
                               "점유·배치 규약(F1/F2) — 유휴 5G G1 이 배치 EIRP 에서 무너진다."))

    # ---- F13 detector ----------------------------------------------------- #
    def f13_detector(self):
        dt = _get(self.fs, "detector_transfer", "S_G")
        if not dt:
            return _skip("F13_detector", "detector_transfer.S_G 없음")
        fig, (a0, a1, a2) = plt.subplots(1, 3, figsize=(14.5, 4.6))
        for mode in MODE_ORDER:
            cell = _first_dopoff(dt.get(mode))
            if not cell:
                continue
            snr = np.asarray(cell.get("snr_grid_db", []), float)
            pd = np.asarray(cell.get("Pd", []), float)
            if snr.size and pd.size == snr.size:
                a0.plot(snr, pd, "-", color=mode_color(mode), lw=1.4, label=mode)
                lo = np.asarray(cell.get("wilson_lo", []), float)
                hi = np.asarray(cell.get("wilson_hi", []), float)
                if lo.size == snr.size:
                    a0.fill_between(snr, lo, hi, color=mode_color(mode), alpha=0.12)
                mc = cell.get("marcum_cfar_snr90_db")
                if mc is not None:
                    a0.axvline(float(mc), color=mode_color(mode), ls=":", lw=0.8, alpha=0.6)
            pe = cell.get("Pfa_emp")
            if pe:
                a1.scatter([mode], [float(pe)], color=mode_color(mode), s=40)
        a0.axhline(0.9, color="#888", ls=":", lw=1.0)
        a0.set_xlabel("RD-output SNR [dB]"); a0.set_ylabel("Pd")
        a0.set_title("Measured Pd(SNR) + Wilson CI + Marcum ref", fontsize=9.5)
        a0.legend(fontsize=6.5, ncol=2); a0.grid(alpha=0.25)
        a1.axhline(float(self.ctx["pfa"]), color="#c62828", ls="--", lw=1.0, label="nominal Pfa")
        a1.set_yscale("log"); _ascii_sci_log(a1, "y"); a1.set_ylabel("empirical Pfa")
        a1.set_title("Empirical vs nominal Pfa", fontsize=9.5)
        a1.legend(fontsize=7); a1.grid(alpha=0.25)
        # (c) dopoff 별 곡선 — 헤드라인 G1 이 있으면 그것, 아니면 첫 모드
        node = dt.get("G1") or next(iter(dt.values()), None)
        dop = _get(node, "N", "1", "dopoff") if node else None
        if isinstance(dop, dict):
            for dk, cell in sorted(dop.items(), key=lambda kv: str(kv[0])):
                if not isinstance(cell, dict) or cell.get("skipped") or "Pd" not in cell:
                    continue
                snr = np.asarray(cell.get("snr_grid_db", []), float)
                pd = np.asarray(cell.get("Pd", []), float)
                if snr.size and pd.size == snr.size:
                    a2.plot(snr, pd, "-", lw=1.2, label=f"dopoff {dk}")
        a2.axhline(0.9, color="#888", ls=":", lw=1.0)
        a2.set_xlabel("RD-output SNR [dB]"); a2.set_ylabel("Pd")
        a2.set_title("Doppler-offset dependence", fontsize=9.5)
        a2.legend(fontsize=7); a2.grid(alpha=0.25)
        fig.suptitle("Measured Pd(SNR) + empirical Pfa + doppler-offset dependence", y=1.02)
        return self.save(fig, "report13_detector.png",
                         _cap6(self.ctx, "(a) Pd(SNR)+Wilson CI (b) 경험 Pfa (c) dopoff별 곡선",
                               "문턱 측정(전역 argmax 아님)·도플러 위치 의존(R3§1). Marcum 점선=CA-CFAR 인지형."))

    # ---- F14 verify ------------------------------------------------------- #
    def f14_verify(self):
        if not self.vf:
            return _skip("F14_verify", "verify_freespace.json 없음")
        fig, (a0, a1, a2) = plt.subplots(1, 3, figsize=(14.5, 4.4))
        # (a) k_mode 잔차
        cf = _get(self.vf, "checks", "closed_form_vs_measured", "resid_by_mode") or {}
        if cf:
            a0.bar(list(cf.keys()), [float(v) for v in cf.values()], color="#1565c0")
        a0.axhline(0.5, color="#c62828", ls="--", lw=1.0)
        a0.axhline(-0.5, color="#c62828", ls="--", lw=1.0)
        a0.set_ylabel("k_mode residual [dB]"); a0.set_title("Closed form vs measured", fontsize=9.5)
        a0.grid(axis="y", alpha=0.25)
        # (b) ECA 잔류 vs DNR × ridge (verify eca_ridge0_floor 요약; 상세는 producer)
        eca = _get(self.vf, "checks", "eca_ridge0_floor") or {}
        if eca:
            dnr = np.asarray(eca.get("dnr_db", [80, 100, 120]), float)
            a1.axhline(0.5, color="#888", ls=":", lw=1.0)
            a1.bar(["ridge 0\n(max p99)", "1e-6\n@120", "1e-4\n@120"],
                   [eca.get("ridge0_max_p99_db", 0), eca.get("ridge1e6_p99_at_dnr120_db", 0),
                    eca.get("ridge1e4_p99_at_dnr120_db", 0)],
                   color=["#2e7d32", "#ef6c00", "#c62828"])
        a1.set_ylabel("non-zero-doppler residual [dB]")
        a1.set_title("ECA floor (ridge = 0 canonical)", fontsize=9.5)
        a1.grid(axis="y", alpha=0.25)
        # (c) Δσ(β) 멀티스태틱 (sigma_grid.json 이 있으면 거기서, 없으면 skip 패널)
        ms = _get(self.sg, "multistatic") or {}
        beta = np.asarray(ms.get("beta_deg", []), float)
        dsig = np.asarray(ms.get("delta_sigma_mean_db", []), float)
        if beta.size and dsig.size == beta.size:
            a2.plot(beta, dsig, "-o", color="#6a1b9a", lw=1.4, ms=3)
        a2.axvline(90.0, color="#c62828", ls="--", lw=1.0)
        a2.set_xlabel(r"bistatic angle $\beta$ [deg]")
        a2.set_ylabel(r"$\Delta\sigma(\beta)$ = $\sigma_{multi}$ - $\sigma_{bisector}$ [dB]")
        a2.set_title("Bisector vs multistatic", fontsize=9.5)
        a2.grid(alpha=0.25)
        fig.suptitle("Verification — closed form vs measured, ECA floor (ridge=0), bisector vs multistatic",
                     y=1.02)
        return self.save(fig, "report13_verify.png",
                         _cap6(self.ctx, "(a) k_mode 잔차 (b) ECA 잔류 vs DNR×ridge (c) $\\Delta\\sigma$(beta)",
                               "믿는 이유와 경계 — |$\\Delta$|<0.5 dB · ridge=0 잔류≈0 · beta>90° 유효범위 밖."))

    # ---- F15 resolution vs range ------------------------------------------ #
    def f15_resolution_vs_range(self):
        wf = _get(self.fs, "waveforms")
        if not wf:
            return _skip("F15_resolution_vs_range", "waveforms 없음")
        fig, ax = plt.subplots(figsize=(7.8, 5.4))
        for mode in MODE_ORDER:
            w = wf.get(mode) if isinstance(wf, dict) else None
            if not w:
                continue
            drb = w.get("d_rb_m")
            # R90 대표값 — 임의 헤드라인 드론(mavic4pro) 우선, 없으면 첫 드론
            R = None
            for d in ("mavic4pro",) + DRONE_ORDER:
                c = _range_cell(self.fs, d, mode)
                if c and c.get("R90_C50_m") is not None:
                    R = float(c["R90_C50_m"]); break
            if drb is not None and R is not None:
                ax.scatter(float(drb), R, s=55, color=mode_color(mode), zorder=3)
                ax.annotate(mode, (float(drb), R), fontsize=7,
                            xytext=(4, 3), textcoords="offset points")
        ax.set_xscale("log"); ax.set_yscale("log"); _plain_log(ax, "both")
        ax.set_xlabel(r"Bistatic range resolution $\Delta R_b$ = c/B [m]")
        ax.set_ylabel("Detection range R90 [m]")
        ax.set_title("Bandwidth buys location, not detection")
        ax.grid(which="both", alpha=0.2)
        return self.save(fig, "report13_resolution_vs_range.png",
                         _cap6(self.ctx, "x=$\\Delta R_b$=c/B [m], y=R90 [m] (9모드)",
                               "대역폭은 위치(분해능)를 사지 검출(거리)을 사지 않는다 — report05 자유공간판."))

    # ---- F16 chamber vs freespace and ground ------------------------------ #
    def f16_chamber_vs_freespace(self):
        chm = _get(self.fs, "meta", "chamber_reference")
        if not _get(self.fs, "ranges") and not chm:
            return _skip("F16_chamber_vs_freespace", "ranges/chamber_reference 없음")
        fig, ax = plt.subplots(figsize=(8.6, 3.4))
        if chm:
            rbmax = float(chm.get("Rb_max_m", 22.0))
            ax.axvspan(1.0, rbmax, color="#bdbdbd", alpha=0.5, label=f"chamber window (≈{rbmax:.0f} m)")
        # FS-1 R90 들 (헤드라인 3인방)
        for mode in TRIO:
            for d in ("mavic4pro",) + DRONE_ORDER:
                c = _range_cell(self.fs, d, mode)
                if c and c.get("R90_C50_m") is not None:
                    ax.axvline(float(c["R90_C50_m"]), color=mode_color(mode), lw=1.6,
                               label=f"FS-1 R90 {mode}")
                    break
        # FS-3 F⁴ 밴드
        f4 = _get(self.fs, "sensitivity", "ground_2ray", "F4_db") or {}
        if f4:
            ax.text(0.98, 0.85, f"FS-3 $F^4$ band: [{f4.get('p10','?')}, {f4.get('p90','?')}] dB",
                    transform=ax.transAxes, ha="right", fontsize=8, color="#6d4c41")
        ax.set_xscale("log"); _plain_log(ax, "x")
        ax.set_xlabel("Bistatic range R_b [m]")
        ax.set_yticks([])
        ax.set_title("Where reports 01–12 sit, and what a flat ground would do")
        ax.legend(fontsize=7.5, loc="upper left", ncol=2)
        return self.save(fig, "report13_chamber_vs_freespace_and_ground.png",
                         _cap6(self.ctx, "R_b 단일 로그축: 챔버창(≈22 m) ↔ FS-1 R90 ↔ FS-3 F^4밴드",
                               "13편 중 위치 + 정직성 점검 — 자유공간은 상한이 아니다(R1)."))

    # ---------------------------------------------------------------------- #
    #  matplotlib GIF R5~R8
    # ---------------------------------------------------------------------- #
    def _gif(self, fig, update, frames, name, fps):
        from matplotlib.animation import FuncAnimation, PillowWriter
        # R5~R8 GIF 는 노트북 gif() 규약대로 renders/anim 에 둔다(out_dir 기준 상대).
        gif_dir = os.path.normpath(os.path.join(self.save.out_dir, "..", "renders", "anim"))
        os.makedirs(gif_dir, exist_ok=True)
        p = os.path.join(gif_dir, name)
        anim = FuncAnimation(fig, update, frames=frames, blit=False)
        anim.save(p, writer=PillowWriter(fps=fps))
        plt.close(fig)
        self.save.saved.append(p)
        print(f"  [gif] {os.path.relpath(p, _ROOT) if p.startswith(_ROOT) else p}")
        return p

    def r5_coverage_grow(self):
        ei = _get(self.fs, "sensitivity", "eirp")
        if not ei:
            return _skip("R5_coverage_grow", "sensitivity.eirp 없음")
        x = np.asarray(ei.get("eirp_dbm", ei.get("grid", [])), float)
        y = np.asarray(ei.get("R_total_m", ei.get("R_thermal_m", [])), float)
        if x.size == 0 or y.size != x.size:
            return _skip("R5_coverage_grow", "eirp/R 배열 불일치")
        fig, ax = plt.subplots(figsize=(6.4, 4.8))
        ax.set_xlim(0, float(np.nanmax(y)) * 1.1); ax.set_ylim(0, float(np.nanmax(y)) * 1.1)
        ax.set_xlabel("range [m]"); ax.set_ylabel("range [m]")
        circle, = ax.plot([], [], "-", color="#1565c0", lw=2)
        txt = ax.text(0.03, 0.93, "", transform=ax.transAxes, fontsize=10)
        badge = ax.text(0.03, 0.03, "", transform=ax.transAxes, fontsize=9, color="#c62828")
        wall_reached = [False]

        def upd(i):
            R = float(y[min(i, y.size - 1)])
            th = np.linspace(0, 2 * np.pi, 200)
            circle.set_data(R * np.cos(th), R * np.sin(th))
            txt.set_text(f"EIRP = {x[min(i, x.size-1)]:.0f} dBm   R = {R:.0f} m")
            ax.set_title("Coverage growth with illuminator power", fontsize=11)
            if i >= y.size - 1 and not wall_reached[0]:
                badge.set_text("DPI-limited @depth 60 dB")
            return circle, txt, badge

        return self._gif(fig, upd, min(x.size, 32), "r13_coverage_grow.gif", fps=5)

    def r6_rd_recede(self):
        frames = _get(self.fs, "curves", "rd_frames")
        if not frames:
            return _skip("R6_rd_recede", "curves.rd_frames 없음(실 MC RD맵은 물리라 여기서 못 만듦 — "
                                         "producer 가 |RD| 2D 목록을 실어야 함)")
        fig, ax = plt.subplots(figsize=(6.0, 4.2))
        Z0 = np.asarray(frames[0], float)
        im = ax.imshow(Z0, aspect="auto", cmap="turbo",
                       vmin=np.nanmax(Z0) - 45, vmax=np.nanmax(Z0))
        ax.set_xlabel("bistatic range bin"); ax.set_ylabel("doppler bin")

        def upd(i):
            Z = np.asarray(frames[min(i, len(frames) - 1)], float)
            im.set_data(Z); im.set_clim(np.nanmax(Z) - 45, np.nanmax(Z))
            ax.set_title("Range-Doppler map receding — CFAR hit vanishes", fontsize=10)
            return [im]

        return self._gif(fig, upd, len(frames), "r13_rd_recede.gif", fps=8)

    def r7_cpi_walk(self):
        cpi = _get(self.fs, "sensitivity", "cpi")
        node = (cpi or {}).get("G1") or (next(iter((cpi or {}).values()), None))
        if not node:
            return _skip("R7_cpi_walk", "sensitivity.cpi 없음")
        T = np.asarray(node.get("t_cpi_s", []), float)
        R = np.asarray(node.get("R90_m", []), float)
        if T.size == 0 or R.size != T.size:
            return _skip("R7_cpi_walk", "cpi t/R 배열 불일치")
        fig, ax = plt.subplots(figsize=(6.4, 4.4))
        ax.set_xscale("log"); ax.set_yscale("log"); _plain_log(ax, "both")
        ax.set_xlim(T.min() * 0.9, T.max() * 1.1)
        ax.set_ylim(np.nanmin(R) * 0.8, np.nanmax(R) * 1.3)
        ax.set_xlabel("T_CPI [s]"); ax.set_ylabel("R90 [m]")
        ln, = ax.plot([], [], "-o", color="#2e7d32", lw=1.6, ms=3)

        def upd(i):
            k = min(i + 1, T.size)
            ln.set_data(T[:k], R[:k])
            ax.set_title(f"Integrate longer — peak smears at the walk wall (T_CPI={T[k-1]*1e3:.0f} ms)",
                         fontsize=9.5)
            return [ln]

        return self._gif(fig, upd, T.size, "r13_cpi_walk.gif", fps=5)

    def r8_cassini_baseline(self):
        by_L = _get(self.fs, "curves", "cassini_by_L")
        if not by_L:
            return _skip("R8_cassini_baseline", "curves.cassini_by_L 없음(L 스윕 per-L 등감도선 필요)")
        Ls = sorted(by_L.keys(), key=lambda s: float(s))
        fig, ax = plt.subplots(figsize=(6.4, 5.2))
        ax.set_aspect("equal")
        line, = ax.plot([], [], "-", color="#6a1b9a", lw=2)
        txt = ax.text(0.03, 0.93, "", transform=ax.transAxes, fontsize=10)
        allxy = np.vstack([np.asarray(by_L[k], float).reshape(-1, 2) for k in Ls])
        m = np.nanmax(np.abs(allxy)) * 1.1
        ax.set_xlim(-m, m + max(float(Ls[-1]), 1)); ax.set_ylim(-m, m)
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")

        def upd(i):
            k = Ls[min(i, len(Ls) - 1)]
            xy = np.asarray(by_L[k], float)
            line.set_data(xy[:, 0], xy[:, 1])
            txt.set_text(f"L = {float(k):.0f} m")
            ax.set_title("Geometry folds coverage — Cassini single → two-lobed", fontsize=10)
            return line, txt

        return self._gif(fig, upd, len(Ls), "r13_cassini_baseline.gif", fps=8)

    # ---------------------------------------------------------------------- #
    def build_all(self):
        figs = [self.f1_geometry, self.f2_budget_waterfall, self.f3_range_bars,
                self.f4_coverage_curves, self.f5_sigma_grid, self.f6_sigma_to_range,
                self.f7_heading_footprint, self.f8_eirp_ladder, self.f9_elevation,
                self.f10_cpi_walk, self.f11_walls, self.f12_matrix, self.f13_detector,
                self.f14_verify, self.f15_resolution_vs_range, self.f16_chamber_vs_freespace,
                self.r5_coverage_grow, self.r6_rd_recede, self.r7_cpi_walk,
                self.r8_cassini_baseline]
        out = []
        for fn in figs:
            try:
                p = fn()
                if p:
                    out.append(p)
            except Exception as e:                 # 한 그림 실패가 배치를 죽이지 않는다
                print(f"  [err ] {fn.__name__}: {type(e).__name__}: {e}")
        return out


# --------------------------------------------------------------------------- #
def _cell_budget(fs, mode):
    """budget_terms_db 를 가진 ranges 셀 하나를 찾아 반환(F2 용)."""
    for d in DRONE_ORDER:
        c = _range_cell(fs, d, mode)
        if c and c.get("budget_terms_db"):
            return c["budget_terms_db"]
    return None


def _first_dopoff(node):
    """detector_transfer[mode] 에서 N=1 의 실현된 dopoff 셀 하나를 고른다(F13 용)."""
    dop = _get(node, "N", "1", "dopoff")
    if not isinstance(dop, dict):
        return None
    for k in sorted(dop, key=lambda s: abs(int(s)) if s.lstrip("-").isdigit() else 999):
        c = dop[k]
        if isinstance(c, dict) and not c.get("skipped") and "Pd" in c:
            return c
    return None


def _load(path):
    """JSON 안전 로드 — 없거나(→{}) 반쯤 써진 파일(→경고 후 {})에도 안 죽는다.
    (실험그룹이 산출 중인 파일을 읽을 때 부분쓰기와 겹칠 수 있다 — 그림 배치가 그걸로 죽으면 안 된다.)"""
    if not (path and os.path.exists(path)):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  [warn] {os.path.basename(path)} 파싱 실패({e}) — 빈 dict 로 진행")
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser(description="report13 그림 F1~F16 + GIF R5~R8 (JSON→그림)")
    ap.add_argument("--freespace", default=JSON_FS)
    ap.add_argument("--sigma", default=JSON_SG)
    ap.add_argument("--verify", default=JSON_VF)
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    v = R13Viz(fs=_load(args.freespace), sg=_load(args.sigma), vf=_load(args.verify),
               out_dir=args.out_dir)
    paths = v.build_all()
    print(f"[viz_report13] {len(paths)} 개 산출 → {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
